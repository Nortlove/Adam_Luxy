"""Dashboard service layer.

Fetches live StackAdapt data (campaigns + advertiser totals) and
enriches with bilateral-cascade intelligence from Neo4j. Runs the
synchronous StackAdapt GraphQL client in a thread pool to avoid
blocking the FastAPI event loop.
"""

from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass
from typing import Any, Optional

import requests

logger = logging.getLogger(__name__)


STACKADAPT_GRAPHQL_ENDPOINT = "https://api.stackadapt.com/graphql"


@dataclass(frozen=True)
class StackAdaptCampaign:
    id: str
    name: str
    channel_type: Optional[str]
    group_name: Optional[str]
    status: Optional[str]
    impressions: int = 0
    clicks: int = 0
    conversions: int = 0
    spend_usd: float = 0.0
    ctr: float = 0.0
    cpa_usd: Optional[float] = None
    roas: Optional[float] = None


@dataclass(frozen=True)
class StackAdaptSummary:
    advertiser_name: Optional[str]
    impressions: int
    clicks: int
    conversions: int
    spend_usd: float
    ctr: float
    cpa_usd: Optional[float]
    roas: Optional[float]
    campaigns: list[StackAdaptCampaign]
    source: str  # "live" | "unavailable"
    reason: Optional[str] = None


# =============================================================================
# GraphQL query — campaigns with per-campaign stats + advertiser totals
# =============================================================================


_CAMPAIGNS_QUERY = """
{
  advertisers(first: 1) {
    nodes {
      id name
      stats {
        impressionsBigint clicksBigint conversionsBigint
        cost ctr ecpa roas
      }
    }
  }
  campaigns(first: 100) {
    nodes {
      id name channelType
      campaignGroup { name }
      campaignStatus { status }
      stats {
        impressionsBigint clicksBigint conversionsBigint
        cost ctr ecpa roas
      }
    }
  }
}
"""


_CAMPAIGNS_QUERY_FALLBACK = """
{
  advertisers(first: 1) {
    nodes {
      id name
      stats {
        impressionsBigint clicksBigint conversionsBigint
        cost ctr ecpa roas
      }
    }
  }
  campaigns(first: 100) {
    nodes {
      id name channelType
      campaignGroup { name }
      campaignStatus { status }
    }
  }
}
"""


def _api_key() -> Optional[str]:
    return os.environ.get("STACKADAPT_GRAPHQL_KEY")


def _query_sync(query: str) -> dict[str, Any]:
    key = _api_key()
    if not key:
        return {"errors": [{"message": "STACKADAPT_GRAPHQL_KEY unset"}]}
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {key}",
    }
    try:
        response = requests.post(
            STACKADAPT_GRAPHQL_ENDPOINT,
            json={"query": query},
            headers=headers,
            timeout=30,
        )
        response.raise_for_status()
        return response.json()
    except Exception as exc:  # pragma: no cover - network
        logger.warning("StackAdapt GraphQL request failed: %s", exc)
        return {"errors": [{"message": str(exc)}]}


def _parse_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _parse_float(value: Any) -> float:
    try:
        return float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _parse_optional_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if result != 0.0 else None


def _parse_campaign(node: dict[str, Any]) -> StackAdaptCampaign:
    stats = node.get("stats") or {}
    return StackAdaptCampaign(
        id=node.get("id", ""),
        name=node.get("name", "") or "",
        channel_type=node.get("channelType"),
        group_name=(node.get("campaignGroup") or {}).get("name"),
        status=(node.get("campaignStatus") or {}).get("status"),
        impressions=_parse_int(stats.get("impressionsBigint")),
        clicks=_parse_int(stats.get("clicksBigint")),
        conversions=_parse_int(stats.get("conversionsBigint")),
        spend_usd=_parse_float(stats.get("cost")),
        ctr=_parse_float(stats.get("ctr")),
        cpa_usd=_parse_optional_float(stats.get("ecpa")),
        roas=_parse_optional_float(stats.get("roas")),
    )


def _parse_summary(payload: dict[str, Any]) -> StackAdaptSummary:
    data = payload.get("data") or {}
    advertisers_nodes = (data.get("advertisers") or {}).get("nodes") or []
    campaigns_nodes = (data.get("campaigns") or {}).get("nodes") or []

    advertiser_name: Optional[str] = None
    adv_impressions = 0
    adv_clicks = 0
    adv_conversions = 0
    adv_spend = 0.0
    adv_ctr = 0.0
    adv_cpa: Optional[float] = None
    adv_roas: Optional[float] = None

    if advertisers_nodes:
        adv = advertisers_nodes[0]
        advertiser_name = adv.get("name")
        stats = adv.get("stats") or {}
        adv_impressions = _parse_int(stats.get("impressionsBigint"))
        adv_clicks = _parse_int(stats.get("clicksBigint"))
        adv_conversions = _parse_int(stats.get("conversionsBigint"))
        adv_spend = _parse_float(stats.get("cost"))
        adv_ctr = _parse_float(stats.get("ctr"))
        adv_cpa = _parse_optional_float(stats.get("ecpa"))
        adv_roas = _parse_optional_float(stats.get("roas"))

    campaigns = [_parse_campaign(node) for node in campaigns_nodes]

    return StackAdaptSummary(
        advertiser_name=advertiser_name,
        impressions=adv_impressions,
        clicks=adv_clicks,
        conversions=adv_conversions,
        spend_usd=adv_spend,
        ctr=adv_ctr,
        cpa_usd=adv_cpa,
        roas=adv_roas,
        campaigns=campaigns,
        source="live",
    )


async def fetch_stackadapt_summary() -> StackAdaptSummary:
    """Fetch live advertiser + campaigns summary from StackAdapt.

    Returns a summary with `source="unavailable"` and a `reason`
    string when StackAdapt is unreachable or unauthenticated — the
    dashboard should still render a sensible empty state rather than
    failing the entire request.
    """
    if not _api_key():
        return StackAdaptSummary(
            advertiser_name=None,
            impressions=0, clicks=0, conversions=0,
            spend_usd=0.0, ctr=0.0, cpa_usd=None, roas=None,
            campaigns=[],
            source="unavailable",
            reason="STACKADAPT_GRAPHQL_KEY not configured",
        )

    payload = await asyncio.to_thread(_query_sync, _CAMPAIGNS_QUERY)

    if payload.get("errors"):
        error_msg = str(payload["errors"][0].get("message", "unknown error"))
        # If the primary query failed (e.g. stats field unsupported),
        # retry without per-campaign stats so we at least get the list.
        logger.info(
            "StackAdapt primary query errored, retrying without campaign stats: %s",
            error_msg,
        )
        payload = await asyncio.to_thread(_query_sync, _CAMPAIGNS_QUERY_FALLBACK)

    if payload.get("errors"):
        return StackAdaptSummary(
            advertiser_name=None,
            impressions=0, clicks=0, conversions=0,
            spend_usd=0.0, ctr=0.0, cpa_usd=None, roas=None,
            campaigns=[],
            source="unavailable",
            reason=str(payload["errors"][0].get("message", "unknown error")),
        )

    return _parse_summary(payload)


# =============================================================================
# Neo4j enrichment — bilateral cascade intelligence
# =============================================================================


@dataclass(frozen=True)
class GraphIntelligence:
    brand_converted_edges: int
    archetypes: int
    source: str  # "live" | "unavailable"


async def fetch_graph_intelligence() -> GraphIntelligence:
    """Pull a lightweight snapshot of bilateral-cascade state from Neo4j."""

    try:
        from adam.infrastructure.neo4j.client import get_neo4j_client

        client = get_neo4j_client()
        if not client.is_connected:
            return GraphIntelligence(
                brand_converted_edges=0, archetypes=0, source="unavailable",
            )

        async with await client.session() as session:
            edges_result = await session.run(
                "MATCH ()-[r:BRAND_CONVERTED]->() RETURN count(r) AS n"
            )
            edges_record = await edges_result.single()
            edges = int(edges_record["n"]) if edges_record else 0

            archetypes_result = await session.run(
                "MATCH (a:Archetype) RETURN count(a) AS n"
            )
            archetypes_record = await archetypes_result.single()
            archetypes = int(archetypes_record["n"]) if archetypes_record else 0

        return GraphIntelligence(
            brand_converted_edges=edges,
            archetypes=archetypes,
            source="live",
        )
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("fetch_graph_intelligence failed: %s", exc)
        return GraphIntelligence(
            brand_converted_edges=0, archetypes=0, source="unavailable",
        )
