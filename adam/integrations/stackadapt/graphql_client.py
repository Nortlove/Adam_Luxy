# =============================================================================
# StackAdapt GraphQL API Client
# Location: adam/integrations/stackadapt/graphql_client.py
# =============================================================================

"""
Client for the StackAdapt GraphQL API.

Used by intelligence reporting (campaign performance pulls) AND the
push paths (audience sync, creative upload, pixel creation, webhook
configuration).

Requires: STACKADAPT_API_KEY or STACKADAPT_GRAPHQL_KEY env var.
Endpoint: https://api.stackadapt.com/graphql (override via
STACKADAPT_GRAPHQL_ENDPOINT).

Authentication: Bearer token in Authorization header.

LIVE-SCHEMA UPDATE (2026-04-29)

Schema introspection against production showed the original queries
were written against a stale schema. Corrections:

  campaigns: returns CampaignConnection (paginated; edges/node pattern),
    NOT a flat list. The argument is `first/after`, NOT `advertiserId`.
  campaignPerformance: NOT a top-level field. Use `campaignDelivery`
    (returns CampaignDeliveryPayload) or `campaignInsight` (returns
    CampaignInsightPayload).
  conversions: NOT a top-level field. Use `conversionPath` (returns
    ConversionPathRecordsConnection).
  domainPerformance: NOT a top-level field. Use `adDelivery` filtered
    by domain attribute, or `campaignInsight` with attribute breakdown.

This module's `get_campaigns` is fixed; the other three reads are
flagged with explicit raise-or-return-stub behavior pending schema
rework.
"""

import asyncio
import json
import logging
import os
import random
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import httpx

logger = logging.getLogger(__name__)

GRAPHQL_ENDPOINT = os.getenv(
    "STACKADAPT_GRAPHQL_ENDPOINT",
    "https://api.stackadapt.com/graphql",
)
# Read either STACKADAPT_API_KEY (older paths) or STACKADAPT_GRAPHQL_KEY
# (newer paths). Both consume the same production token.
API_KEY = os.getenv("STACKADAPT_API_KEY") or os.getenv(
    "STACKADAPT_GRAPHQL_KEY", ""
)


class StackAdaptGraphQLClient:
    """Client for StackAdapt's GraphQL API."""

    def __init__(self, api_key: str = ""):
        self._api_key = api_key or API_KEY
        self._client = httpx.AsyncClient(
            timeout=30.0,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
        )

    async def _query(self, query: str, variables: Dict = None) -> Dict:
        """Execute a GraphQL query."""
        if not self._api_key:
            logger.warning("No StackAdapt API key configured")
            return {"error": "No API key"}

        payload = {"query": query}
        if variables:
            payload["variables"] = variables

        try:
            resp = await self._client.post(GRAPHQL_ENDPOINT, json=payload)
            resp.raise_for_status()
            data = resp.json()
            if "errors" in data:
                logger.warning("GraphQL errors: %s", data["errors"])
            return data.get("data", data)
        except Exception as e:
            logger.error("GraphQL query failed: %s", e)
            return {"error": str(e)}

    async def _query_with_retry(
        self,
        query: str,
        variables: Dict = None,
        max_attempts: int = 7,
        base_delay_ms: int = 500,
        max_delay_ms: int = 60_000,
    ) -> Dict:
        """Wrap _query with full-jitter exponential backoff on rate-limit
        envelopes (HTTP 429 or message containing 'rate limit' / 'too many').

        Slice S0: substrate for the multi-source URL extraction CLI per
        the amended directive §B (and reused by S4 ingestion). Pattern
        per Marc Brooker / AWS architecture blog: full jitter over the
        capped exponential interval.

        Args:
            query: GraphQL query string.
            variables: Variable bindings.
            max_attempts: Hard cap on retries (default 7 per directive §1.3).
            base_delay_ms: Base delay (default 500ms per directive §1.3).
            max_delay_ms: Cap (default 60000ms = 60s per directive §1.3).

        Returns:
            Same shape as `_query`. On rate-limit-exhausted: returns
            {"error": "RATE_LIMIT_EXHAUSTED", "attempts": <n>}. On
            non-rate-limit error from `_query`: returns immediately
            (single attempt, original error preserved).
        """
        attempt = 0
        last_error: Optional[str] = None
        while attempt < max_attempts:
            result = await self._query(query, variables)
            if not isinstance(result, dict) or not result.get("error"):
                return result

            err = str(result.get("error") or "").lower()
            is_rate_limit = (
                "429" in err
                or "rate limit" in err
                or "too many" in err
                or "throttl" in err
            )
            if not is_rate_limit:
                return result

            last_error = str(result.get("error"))
            attempt += 1
            if attempt >= max_attempts:
                break
            cap_ms = min(max_delay_ms, base_delay_ms * (2 ** attempt))
            delay_ms = random.uniform(0, cap_ms)
            logger.warning(
                "rate-limit envelope (attempt %d/%d); backing off %.0fms",
                attempt, max_attempts, delay_ms,
            )
            await asyncio.sleep(delay_ms / 1000.0)

        return {
            "error": "RATE_LIMIT_EXHAUSTED",
            "attempts": attempt,
            "last_error": last_error,
        }

    async def get_conversion_paths_page(
        self,
        filter_by: Dict[str, Any],
        first: int = 200,
        after: Optional[str] = None,
    ) -> Tuple[List[Dict], Dict[str, Any]]:
        """Single-page cursor-paginated read of `conversionPath`.

        Slice S0 Source 1. Returns (nodes, pageInfo) where pageInfo has
        {hasNextPage, endCursor}; caller iterates with after=endCursor
        until hasNextPage is False.

        Schema realities (introspected 2026-05-04, two corrections from
        directive's Q3 spec):
            * Q3 named `touchpoints[]` with per-touch `url, domain, sapid`
              — DOES NOT EXIST on the live schema. ConversionPathRecords
              has no touchpoints array.
            * Q3 named `conversionId, conversionTimestamp, revenueUsd` as
              top-level fields — DO NOT EXIST. Conversion data is nested
              under `conversionStats { conversionUrl conversionTime ... }`
              which is the only URL field on the entire path subtree.

        What we get per record (live):
            * id (path identifier)
            * domain (first-impression publisher host)
            * lastDomain (last-impression publisher host)
            * impressionCount, clickCount
            * firstImpressionTime, lastImpressionTime
            * conversionStats.conversionUrl  ← THE URL field
            * conversionStats.conversionTime, .device
            * ad { id, name, clickUrl } (LUXY click destination, not publisher)
            * campaign { id, name }

        Filter shape (ConversionPathFilters input fields):
            campaignIds: [ID], trackerIds: [ID],
            startTime: ISO8601DateTime, endTime: ISO8601DateTime.
            (No advertiser filter at this layer — caller must pre-fetch
            LUXY campaign IDs via get_campaigns(filter_by={"advertiserIds":[...]}).
        """
        query = """
        query ConversionPathPage(
            $first: Int!,
            $after: String,
            $filterBy: ConversionPathFilters
        ) {
            conversionPath(first: $first, after: $after, filterBy: $filterBy) {
                pageInfo { hasNextPage endCursor }
                totalCount
                nodes {
                    id
                    domain
                    lastDomain
                    impressionCount
                    clickCount
                    firstImpressionTime
                    lastImpressionTime
                    conversionStats {
                        conversionUrl
                        conversionTime
                        device
                    }
                    ad { id name clickUrl }
                    campaign { id name }
                }
            }
        }
        """
        variables: Dict[str, Any] = {"first": first, "filterBy": filter_by}
        if after:
            variables["after"] = after

        result = await self._query_with_retry(query, variables)
        if isinstance(result, dict) and result.get("error"):
            return [], {"hasNextPage": False, "endCursor": None,
                        "error": result.get("error")}
        conn = (result or {}).get("conversionPath") or {}
        nodes = conn.get("nodes") or []
        page_info = conn.get("pageInfo") or {
            "hasNextPage": False, "endCursor": None,
        }
        return [n for n in nodes if n], page_info

    async def get_campaign_page_context_page(
        self,
        advertiser_id: str,
        date_from: str,
        date_to: str,
        first: int = 200,
        after: Optional[str] = None,
        max_progress_polls: int = 24,
        progress_poll_seconds: float = 5.0,
    ) -> Tuple[List[Dict], Dict[str, Any]]:
        """Single-page cursor-paginated read of `campaignPageContext`.

        Slice S0 Source 3 (REFRAMED). The directive's original Source 3
        spec named `adDelivery` with `groupBy: DOMAIN` — but the live
        schema does NOT support either: AdDeliveryRecord has no domain
        field, and `groupBy` is not an arg on Query.adDelivery. The
        live-schema URL-bearing population-level surface is
        `campaignPageContext` (verified 2026-05-04: returns
        CampaignPageContextRecord with `url: String` field — exactly
        what we want for unbiased URL discovery).

        Returns (nodes, pageInfo). UNION resolution:
            campaignPageContext returns CampaignPageContextPayload UNION
            { CampaignPageContextOutcome | Progress }.

            * If Outcome: extract records.{nodes, pageInfo}.
            * If Progress (only `_` field exposed; no jobId): poll the
              same query after `progress_poll_seconds`, up to
              `max_progress_polls` retries. The `_` schema indicates the
              server is computing and re-querying retrieves Outcome once
              ready. (Not async-jobId; just transient async signal.)

        Filter shape (CampaignFilters input — verified 2026-05-04):
            advertiserIds: [ID], ids: [ID], campaignGroupIds: [ID],
            archived: Boolean, endDateAfter: ISO8601Date,
            startDateBefore: ISO8601Date, states, types, subTypes,
            nameOrIdContains: String.
        Date shape (DateRangeInput): { from, to } (NOT startDate/endDate).
        Default poll budget: 24 retries × 5s = 120s for the async
        compute to complete on a 365d window.
        """
        query = """
        query CampaignPageContextPage(
            $first: Int!,
            $after: String,
            $date: DateRangeInput!,
            $filterBy: CampaignFilters!
        ) {
            campaignPageContext(date: $date, filterBy: $filterBy) {
                __typename
                ... on CampaignPageContextOutcome {
                    records(first: $first, after: $after) {
                        pageInfo { hasNextPage endCursor }
                        nodes { url campaign { id name } }
                    }
                }
                ... on Progress { _ }
            }
        }
        """
        variables: Dict[str, Any] = {
            "first": first,
            "date": {"from": date_from, "to": date_to},
            "filterBy": {"advertiserIds": [advertiser_id]},
        }
        if after:
            variables["after"] = after

        polls = 0
        while polls <= max_progress_polls:
            result = await self._query_with_retry(query, variables)
            if isinstance(result, dict) and result.get("error"):
                return [], {"hasNextPage": False, "endCursor": None,
                            "error": result.get("error")}
            payload = (result or {}).get("campaignPageContext") or {}
            tname = payload.get("__typename")
            if tname == "Progress":
                polls += 1
                if polls > max_progress_polls:
                    return [], {"hasNextPage": False, "endCursor": None,
                                "error": "PROGRESS_TIMEOUT"}
                logger.info(
                    "campaignPageContext returned Progress; re-polling "
                    "in %.1fs (%d/%d)",
                    progress_poll_seconds, polls, max_progress_polls,
                )
                await asyncio.sleep(progress_poll_seconds)
                continue
            # Outcome path
            records = payload.get("records") or {}
            nodes = records.get("nodes") or []
            page_info = records.get("pageInfo") or {
                "hasNextPage": False, "endCursor": None,
            }
            return [n for n in nodes if n], page_info

        return [], {"hasNextPage": False, "endCursor": None,
                    "error": "PROGRESS_TIMEOUT_UNREACHABLE"}

    async def _mutate(self, mutation: str, variables: Dict = None) -> Dict:
        """Execute a GraphQL mutation. Same transport contract as
        ``_query`` — Bearer token, JSON body, captured errors.

        Slice 13: substrate for Phase 8 write paths
        (createCreativeByURL, createAudience, addUsersToAudience,
        Pixel API). The transport is identical to queries; this
        method is named separately for legibility / audit clarity at
        the call site (read vs write distinction matters for ops).

        Returns the same shape as ``_query``: ``data`` dict on
        success, ``{"error": ...}`` on missing key / network failure.
        GraphQL-level errors (data["errors"]) are logged as WARNING
        and the data payload is still returned — caller checks for
        the operation's ``errors`` field per StackAdapt's mutation
        response convention.
        """
        if not self._api_key:
            logger.warning("No StackAdapt API key configured")
            return {"error": "No API key"}

        payload = {"query": mutation}
        if variables:
            payload["variables"] = variables

        try:
            resp = await self._client.post(GRAPHQL_ENDPOINT, json=payload)
            resp.raise_for_status()
            data = resp.json()
            if "errors" in data:
                logger.warning("GraphQL mutation errors: %s", data["errors"])
            return data.get("data", data)
        except Exception as e:
            logger.error("GraphQL mutation failed: %s", e)
            return {"error": str(e)}

    async def get_campaigns(
        self,
        first: int = 100,
        after: Optional[str] = None,
        filter_by: Optional[Dict[str, Any]] = None,
    ) -> List[Dict]:
        """Get campaigns via the CampaignConnection paginated query.

        Per live schema (introspected 2026-04-29):
            campaigns(after, before, filterBy, first, last, sortBy)
              -> CampaignConnection (edges/node pattern)

        Returns a list of campaign nodes (not Connection edges); the
        caller doesn't need to know about pagination wrapping. To page
        through all campaigns, the caller iterates with `after = last
        endCursor` until `pageInfo.hasNextPage` is false.

        For the simpler "all campaigns up to N" case, pass `first=N`
        and one call returns up to N campaigns.

        Args:
            first: max campaigns to return in this page
            after: cursor for pagination (page through with this)
            filter_by: optional filter dict (StackAdapt's CampaignFilter
                shape; varies by what we're filtering on)
        """
        query = """
        query GetCampaigns($first: Int, $after: String, $filterBy: CampaignFilters) {
            campaigns(first: $first, after: $after, filterBy: $filterBy) {
                edges {
                    node {
                        id
                        name
                        isArchived
                        isDraft
                        goalType
                    }
                }
                pageInfo {
                    hasNextPage
                    endCursor
                }
            }
        }
        """
        variables: Dict[str, Any] = {"first": first}
        if after:
            variables["after"] = after
        if filter_by:
            variables["filterBy"] = filter_by

        result = await self._query(query, variables)
        connection = result.get("campaigns") or {}
        edges = connection.get("edges") or []
        return [e["node"] for e in edges if e.get("node")]

    async def get_campaign(self, campaign_id: str) -> Dict[str, Any]:
        """Get a single campaign by ID with directive-relevant fields.

        Per live schema: `campaign(id) -> Campaign`.

        Returns the campaign with id + name + lifecycle flags + status
        + channel + flight scheduling (CampaignFlight uses startTime /
        endTime, NOT startDate/endDate) + frequency-cap config + pacing
        subtree (Total type with flightPacing nested fields). Returns
        {} when campaign not found.
        """
        query = """
        query GetCampaign($id: ID!) {
            campaign(id: $id) {
                id
                name
                isArchived
                isDraft
                goalType
                campaignStatus { state status }
                channelType
                tacticType
                createdAt
                updatedAt
                freqCapLimit
                freqCapExpiry
                freqMinThreshold
                freqMinExpiry
                currentFlight {
                    id
                    name
                    startTime
                    paceAheadPercent
                    secondaryGoalType
                    secondaryGoalValue
                    viewabilityGoal
                    partingTimeZone
                }
                pacing {
                    flightPacing {
                        overallPacing
                        calculatedPacePercent
                        lifetimeBudget
                        totalProjectedSpend
                    }
                    dailySpendNeeded { dailySpendNeeded }
                    projectedDailySpend {
                        projectedDailySpend
                        currentPacePercentVar
                    }
                }
            }
        }
        """
        result = await self._query(query, {"id": campaign_id})
        return result.get("campaign") or {}

    async def get_campaign_performance(
        self,
        campaign_ids: List[str] = None,
        start_date: str = "",
        end_date: str = "",
    ) -> List[Dict]:
        """Get performance data via the live `campaignDelivery` field.

        Slice 16: replaces the empty-stub with an actual GraphQL query
        against the campaignDelivery field (per live-schema notes
        2026-04-29). Honest tag: the exact field selection is
        best-guess against StackAdapt's CampaignDeliveryPayload
        shape; introspect_query_field("campaignDelivery") validates
        before pilot launch. A14 flag:
        STACKADAPT_REPORTING_SCHEMA_PILOT_PENDING.

        Args:
            campaign_ids: optional list of campaign IDs to filter to.
            start_date / end_date: ISO-8601 date strings (YYYY-MM-DD).
                When both empty, returns the last 30 days.

        Returns:
            List of per-campaign performance dicts with impressions,
            clicks, conversions, spend, ctr, cpa. Empty list when API
            error / no data.
        """
        query = """
        query CampaignDelivery(
            $filterBy: CampaignDeliveryFilters,
            $granularity: GranularityEnum,
        ) {
            campaignDelivery(
                dataType: PERFORMANCE,
                filterBy: $filterBy,
                granularity: $granularity,
            ) {
                rows {
                    campaignId
                    date
                    impressions
                    clicks
                    conversions
                    spend
                    ctr
                    cpa
                }
            }
        }
        """
        filter_by: Dict[str, Any] = {}
        if campaign_ids:
            filter_by["campaignIds"] = list(campaign_ids)
        if start_date:
            filter_by["startDate"] = start_date
        if end_date:
            filter_by["endDate"] = end_date

        variables: Dict[str, Any] = {
            "granularity": "DAILY",
        }
        if filter_by:
            variables["filterBy"] = filter_by

        result = await self._query(query, variables)
        payload = result.get("campaignDelivery") or {}
        rows = payload.get("rows") or []
        return [r for r in rows if r]

    async def get_conversion_events(
        self,
        start_date: str = "",
        end_date: str = "",
        *,
        first: int = 100,
        after: Optional[str] = None,
    ) -> List[Dict]:
        """Get conversion events via the live `conversionPath` connection.

        Slice 16: replaces the empty-stub with an actual paginated
        GraphQL query against conversionPath. Honest tag: field
        selection on ConversionPathRecord is best-guess; validate
        with introspect_type("ConversionPathRecord") before pilot.

        The conversionPath connection feeds the sapid round-trip
        verification: paired with our DecisionTrace via the sapid
        macro, every conversion event should resolve to a known
        decision_id.

        Args:
            start_date / end_date: ISO-8601 date strings.
            first: max records per page.
            after: pagination cursor.

        Returns:
            List of conversion-event dicts with sapid, conversion_at,
            campaign_id, ad_id, conversion_value. Empty on error.
        """
        query = """
        query ConversionPath(
            $first: Int,
            $after: String,
            $filterBy: ConversionPathFilters,
        ) {
            conversionPath(
                first: $first,
                after: $after,
                filterBy: $filterBy,
            ) {
                edges {
                    node {
                        id
                        sapid
                        conversionAt
                        campaignId
                        adId
                        conversionValue
                        conversionType
                    }
                }
                pageInfo {
                    hasNextPage
                    endCursor
                }
            }
        }
        """
        filter_by: Dict[str, Any] = {}
        if start_date:
            filter_by["startDate"] = start_date
        if end_date:
            filter_by["endDate"] = end_date

        variables: Dict[str, Any] = {"first": first}
        if after:
            variables["after"] = after
        if filter_by:
            variables["filterBy"] = filter_by

        result = await self._query(query, variables)
        connection = result.get("conversionPath") or {}
        edges = connection.get("edges") or []
        return [e["node"] for e in edges if e.get("node")]

    async def get_domain_performance(
        self,
        campaign_id: str,
        start_date: str = "",
        end_date: str = "",
    ) -> List[Dict]:
        """Get per-domain performance via the live `adDelivery` field.

        Slice 16: replaces the empty-stub with an actual GraphQL query
        against adDelivery with a domain breakdown attribute. Honest
        tag: AdDeliveryPayload's domain field shape is best-guess;
        introspect_type("AdDeliveryPayload") validates.

        Args:
            campaign_id: required — scope the breakdown.
            start_date / end_date: ISO-8601.

        Returns:
            List of per-domain dicts with domain, impressions, clicks,
            conversions, spend, ctr, viewability. Empty on error /
            no data.
        """
        if not campaign_id:
            return []

        query = """
        query AdDelivery(
            $filterBy: AdDeliveryFilters,
        ) {
            adDelivery(
                dataType: PERFORMANCE,
                filterBy: $filterBy,
                granularity: AGGREGATE,
                groupBy: DOMAIN,
            ) {
                rows {
                    domain
                    impressions
                    clicks
                    conversions
                    spend
                    ctr
                    viewability
                }
            }
        }
        """
        filter_by: Dict[str, Any] = {"campaignId": campaign_id}
        if start_date:
            filter_by["startDate"] = start_date
        if end_date:
            filter_by["endDate"] = end_date

        result = await self._query(query, {"filterBy": filter_by})
        payload = result.get("adDelivery") or {}
        rows = payload.get("rows") or []
        return [r for r in rows if r]

    # =========================================================================
    # Slice 14 — list ads (read counterpart to create_creative_by_url)
    # =========================================================================

    async def list_ads(
        self,
        *,
        first: int = 50,
        after: Optional[str] = None,
    ) -> Dict[str, Any]:
        """List ads in the account via the ``ads(first, after)`` query.

        Per StackAdapt's live schema (introspected 2026-05-02): the
        top-level ``ads`` field returns ``AdConnection`` with
        ``pageInfo`` + ``nodes`` of ``Ad``. ``Ad.userMetadata`` is the
        free-form JSON slot that holds operator-set metadata.

        This is the read counterpart of ``create_creative_by_url``,
        used by Slice 14's manifest reconciliation: surveys the
        existing account inventory and persists ``:UploadedCreative``
        records so Slice C's lookup can resolve real creatives.

        Returns:
            ``{"nodes": [...], "pageInfo": {"hasNextPage": bool,
              "endCursor": str | None}}``. On error: empty dict
            (caller treats as "no results"; exception logged).

        Honest tag — Ad.userMetadata vs createCreativeByURL.description
        ------------------------------------------------------------------
        ``create_creative_by_url`` writes operator metadata into the
        creative's ``description`` slot. ``Ad.userMetadata`` is a
        separate JSON slot — what gets read here may NOT be what the
        upload mutation wrote. The reconciliation slice flags this
        discrepancy and persists records with metadata=None where the
        userMetadata slot is empty.
        """
        query = """
        query ListAds($first: Int, $after: String) {
          ads(first: $first, after: $after) {
            pageInfo { hasNextPage endCursor }
            nodes {
              id
              name
              brandname
              channelType
              clickUrl
              creativeSize
              creativeStatus { status }
              isArchived
              isDraft
              isRejected
              paused
              userMetadata
            }
          }
        }
        """
        variables: Dict[str, Any] = {"first": first}
        if after:
            variables["after"] = after
        try:
            result = await self._query(query, variables)
        except Exception as exc:
            logger.warning("list_ads failed: %s", exc)
            return {}
        return (result or {}).get("ads") or {}

    # =========================================================================
    # Slice 13 — Write mutations (Phase 8 substrate)
    # =========================================================================

    async def create_creative_by_url(
        self,
        landing_page_url: str,
        name: str,
        *,
        advertiser_id: Optional[str] = None,
        mechanism: Optional[str] = None,
        primary_metaphor: Optional[str] = None,
        posture_class: Optional[str] = None,
        creative_type: str = "banner",
    ) -> Dict[str, Any]:
        """Upload a creative via createCreativeByURL with metadata tags.

        Per directive Phase 8 line 1099 + Section 6.4: "Upload to
        StackAdapt with mechanism + metaphor + posture metadata so the
        partner-side trace later reads back what was deployed."

        Mechanism / metaphor / posture are passed through the
        creative's `description` or tags field as a structured JSON
        blob — StackAdapt's createCreativeByURL accepts free-form
        descriptive metadata, and our DecisionTrace consumers parse
        it back. The exact field name (description vs metadata vs
        tag list) depends on the live mutation schema; v0.1 stores
        the metadata blob in the `description` slot.

        Args:
            landing_page_url: target URL for the creative click; must
                include the {SA_POSTBACK_ID} macro for sapid round-
                trip per directive line 553.
            name: human-readable creative name.
            advertiser_id: optional advertiser scoping.
            mechanism: canonical or cohort-side mechanism name.
            primary_metaphor: LUXY metaphor frame (CONTAINMENT, etc.).
            posture_class: target posture (POSTURE_BLEND / VIGILANCE /
                NEUTRAL).
            creative_type: 'banner' | 'native' | 'video'. Default banner.

        Returns the mutation response data dict. Errors land on
        ``data["createCreativeByURL"]["errors"]`` per StackAdapt
        convention; caller checks that.

        Honest tag — schema uncertainty
        --------------------------------
        The exact mutation field shape (input type name, metadata slot
        name) depends on StackAdapt's live mutation schema. v0.1 uses
        a best-guess shape; introspect_mutation_field() validates
        against the live schema. If the live mutation requires a
        different shape, this method's mutation string needs a 1-line
        update.
        """
        # Encode our metadata as a JSON blob in the description slot.
        # Cleaner than splitting across multiple StackAdapt fields when
        # the live schema's metadata shape is uncertain.
        metadata = {
            "mechanism": mechanism,
            "primary_metaphor": primary_metaphor,
            "posture_class": posture_class,
        }
        # Strip None values so the blob is small and round-trips cleanly.
        metadata_clean = {k: v for k, v in metadata.items() if v is not None}
        description = json.dumps({"adam_metadata": metadata_clean})

        mutation = """
        mutation CreateCreativeByURL($input: CreateCreativeByURLInput!) {
            createCreativeByURL(input: $input) {
                creative {
                    id
                    name
                    description
                    creativeType
                    landingPageUrl
                }
                errors {
                    field
                    message
                }
            }
        }
        """
        input_obj: Dict[str, Any] = {
            "name": name,
            "landingPageUrl": landing_page_url,
            "creativeType": creative_type,
            "description": description,
        }
        if advertiser_id:
            input_obj["advertiserId"] = advertiser_id

        result = await self._mutate(mutation, {"input": input_obj})
        return result.get("createCreativeByURL") or result

    async def create_audience(
        self,
        name: str,
        *,
        advertiser_id: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a StackAdapt audience.

        Per directive line 542: "Audience segment pushes via GraphQL
        API. Each cohort is a StackAdapt audience; users move between
        audiences as cohort posteriors update."

        Returns the mutation response data dict. The created audience
        carries an ``id`` that ``add_users_to_audience`` consumes.
        """
        mutation = """
        mutation CreateAudience($input: CreateAudienceInput!) {
            createAudience(input: $input) {
                audience {
                    id
                    name
                    description
                }
                errors {
                    field
                    message
                }
            }
        }
        """
        input_obj: Dict[str, Any] = {"name": name}
        if description:
            input_obj["description"] = description
        if advertiser_id:
            input_obj["advertiserId"] = advertiser_id

        result = await self._mutate(mutation, {"input": input_obj})
        return result.get("createAudience") or result

    async def add_users_to_audience(
        self,
        audience_id: str,
        user_ids: List[str],
    ) -> Dict[str, Any]:
        """Add user IDs to a StackAdapt audience.

        Per directive line 542-543: "users move between audiences as
        cohort posteriors update." This is the membership-update
        primitive.

        Args:
            audience_id: StackAdapt audience id from create_audience.
            user_ids: list of StackAdapt user_ids (postback ids /
                ramp_ids depending on the integration mode).

        Returns the mutation response. Empty user_ids → no-op.
        """
        if not user_ids:
            return {"audience": {"id": audience_id}, "errors": []}

        mutation = """
        mutation AddUsersToAudience($input: AddUsersToAudienceInput!) {
            addUsersToAudience(input: $input) {
                audience {
                    id
                    name
                }
                errors {
                    field
                    message
                }
            }
        }
        """
        result = await self._mutate(
            mutation,
            {"input": {"audienceId": audience_id, "userIds": list(user_ids)}},
        )
        return result.get("addUsersToAudience") or result

    async def introspect_mutation_field(
        self, field_name: str,
    ) -> Dict[str, Any]:
        """Introspect a top-level Mutation field's args + return type.

        Mirror of introspect_query_field — discovers the live schema
        for a mutation. Use to validate v0.1 mutation strings against
        production before pilot launch.
        """
        query = """
        query InspectMutationField {
            __schema {
                mutationType {
                    fields {
                        name
                        args { name type { name kind ofType { name } } }
                        type { name kind ofType { name kind } }
                    }
                }
            }
        }
        """
        result = await self._query(query)
        fields = (
            (result.get("__schema") or {})
            .get("mutationType", {})
            .get("fields") or []
        )
        for f in fields:
            if f.get("name") == field_name:
                return f
        return {}

    async def introspect_query_field(self, field_name: str) -> Dict[str, Any]:
        """Introspect a top-level Query field's args + return type.

        Used to debug stale queries against the live schema. Pass the
        Query field name (e.g. 'campaigns', 'campaignDelivery').
        """
        query = """
        query InspectQueryField {
            __schema {
                queryType {
                    fields {
                        name
                        args { name type { name kind ofType { name } } }
                        type { name kind ofType { name kind } }
                    }
                }
            }
        }
        """
        result = await self._query(query)
        fields = (result.get("__schema") or {}).get("queryType", {}).get("fields") or []
        for f in fields:
            if f.get("name") == field_name:
                return f
        return {}

    async def introspect_type(self, type_name: str) -> Dict[str, Any]:
        """Introspect a GraphQL type by name.

        Returns the type's fields list. Used to discover the shape of
        Payload / Connection types named in query/mutation signatures.
        """
        query = """
        query InspectType($name: String!) {
            __type(name: $name) {
                name
                kind
                fields {
                    name
                    type { name kind ofType { name kind } }
                }
            }
        }
        """
        result = await self._query(query, {"name": type_name})
        return result.get("__type") or {}

    @property
    def is_configured(self) -> bool:
        return bool(self._api_key)


def get_stackadapt_client(api_key: str = "") -> StackAdaptGraphQLClient:
    """Get a StackAdapt GraphQL client."""
    return StackAdaptGraphQLClient(api_key=api_key)
