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
