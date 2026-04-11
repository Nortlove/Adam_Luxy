# =============================================================================
# StackAdapt GraphQL API Client
# Location: adam/integrations/stackadapt/graphql_client.py
# =============================================================================

"""
Client for pulling campaign reporting data from StackAdapt's GraphQL API.

Used by the weekly intelligence report generator to pull campaign
performance data programmatically instead of relying on CSV exports.

Requires: STACKADAPT_API_KEY environment variable.

StackAdapt GraphQL endpoint: https://api.stackadapt.com/graphql
Authentication: Bearer token in Authorization header.
"""

import json
import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

GRAPHQL_ENDPOINT = "https://api.stackadapt.com/graphql"
API_KEY = os.getenv("STACKADAPT_API_KEY", "")


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

    async def get_campaigns(self, advertiser_id: str = "") -> List[Dict]:
        """Get all campaigns for the advertiser."""
        query = """
        query GetCampaigns($advertiserId: ID) {
            campaigns(advertiserId: $advertiserId) {
                id
                name
                status
                budget {
                    daily
                    total
                }
                schedule {
                    startDate
                    endDate
                }
                stats {
                    impressions
                    clicks
                    conversions
                    spend
                    ctr
                    cvr
                    cpm
                    cpc
                }
            }
        }
        """
        variables = {}
        if advertiser_id:
            variables["advertiserId"] = advertiser_id

        result = await self._query(query, variables)
        return result.get("campaigns", [])

    async def get_campaign_performance(
        self,
        campaign_ids: List[str] = None,
        start_date: str = "",
        end_date: str = "",
    ) -> List[Dict]:
        """Get performance data for specific campaigns."""
        if not start_date:
            start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        if not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d")

        query = """
        query GetPerformance($startDate: String!, $endDate: String!) {
            campaignPerformance(startDate: $startDate, endDate: $endDate) {
                campaignId
                campaignName
                date
                impressions
                clicks
                conversions
                spend
                ctr
                cvr
                viewThroughConversions
                clickThroughConversions
            }
        }
        """
        variables = {
            "startDate": start_date,
            "endDate": end_date,
        }

        result = await self._query(query, variables)
        return result.get("campaignPerformance", [])

    async def get_conversion_events(
        self,
        start_date: str = "",
        end_date: str = "",
    ) -> List[Dict]:
        """Get conversion event data."""
        if not start_date:
            start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        if not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d")

        query = """
        query GetConversions($startDate: String!, $endDate: String!) {
            conversions(startDate: $startDate, endDate: $endDate) {
                id
                campaignId
                timestamp
                conversionType
                revenue
                attributionType
                touchpoints {
                    campaignId
                    creativeId
                    domain
                    deviceType
                    timestamp
                }
            }
        }
        """
        variables = {"startDate": start_date, "endDate": end_date}
        result = await self._query(query, variables)
        return result.get("conversions", [])

    async def get_domain_performance(
        self,
        campaign_id: str,
        start_date: str = "",
        end_date: str = "",
    ) -> List[Dict]:
        """Get per-domain performance for a campaign."""
        if not start_date:
            start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        if not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d")

        query = """
        query GetDomainPerformance($campaignId: ID!, $startDate: String!, $endDate: String!) {
            domainPerformance(campaignId: $campaignId, startDate: $startDate, endDate: $endDate) {
                domain
                impressions
                clicks
                conversions
                spend
                ctr
                cvr
            }
        }
        """
        variables = {
            "campaignId": campaign_id,
            "startDate": start_date,
            "endDate": end_date,
        }
        result = await self._query(query, variables)
        return result.get("domainPerformance", [])

    @property
    def is_configured(self) -> bool:
        return bool(self._api_key)


def get_stackadapt_client(api_key: str = "") -> StackAdaptGraphQLClient:
    """Get a StackAdapt GraphQL client."""
    return StackAdaptGraphQLClient(api_key=api_key)
