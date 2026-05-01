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

import json
import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

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
        """Get performance data using the live `campaignDelivery` field.

        Per live schema (2026-04-29): the original top-level
        `campaignPerformance` field DOES NOT EXIST. The current
        equivalent is `campaignDelivery(dataType, date, filterBy,
        granularity)` returning `CampaignDeliveryPayload`.

        This method is a substrate stub returning empty until the
        CampaignDeliveryPayload schema is introspected and the query
        is rewritten. Callers must not assume non-empty results yet.
        """
        logger.warning(
            "get_campaign_performance called but query is pending live "
            "campaignDelivery schema rewrite; returning empty list"
        )
        return []

    async def get_conversion_events(
        self,
        start_date: str = "",
        end_date: str = "",
    ) -> List[Dict]:
        """Get conversion events via the live `conversionPath` connection.

        Per live schema (2026-04-29): the original top-level
        `conversions` field DOES NOT EXIST. The current equivalent is
        `conversionPath(after, before, filterBy, first, last)`
        returning `ConversionPathRecordsConnection`.

        Substrate stub pending ConversionPathRecord schema introspection.
        """
        logger.warning(
            "get_conversion_events called but query is pending live "
            "conversionPath schema rewrite; returning empty list"
        )
        return []

    async def get_domain_performance(
        self,
        campaign_id: str,
        start_date: str = "",
        end_date: str = "",
    ) -> List[Dict]:
        """Get per-domain performance via the live `adDelivery` field.

        Per live schema (2026-04-29): the original top-level
        `domainPerformance` field DOES NOT EXIST. The current
        equivalent is `adDelivery(dataType, date, filterBy,
        granularity)` returning `AdDeliveryPayload` with a domain
        breakdown attribute.

        Substrate stub pending AdDeliveryPayload schema introspection.
        """
        logger.warning(
            "get_domain_performance called but query is pending live "
            "adDelivery schema rewrite; returning empty list"
        )
        return []

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
