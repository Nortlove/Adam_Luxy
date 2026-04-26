"""Dashboard service layer.

Fetches live StackAdapt data (campaigns + advertiser totals) and
enriches with bilateral-cascade intelligence from Neo4j. Runs the
synchronous StackAdapt GraphQL client in a thread pool to avoid
blocking the FastAPI event loop.

Also hosts the recommendation generator that produces structured
AI recommendations with full Confident/Uncertain/Possibly-Wrong
decomposition per HMT Foundation §7.1.
"""

from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import requests

from adam.api.dashboard.models import (
    ConfidentClaim,
    DeviationContext,
    PossiblyWrongClaim,
    RecommendationAlternative,
    RecommendationDetail,
    UncertainClaim,
    UncertaintyBreakdown,
)

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
# GraphQL query — campaigns with per-campaign metrics + advertiser totals
#
# Per-campaign metrics moved from `Campaign.stats` (removed) to the top-level
# `campaignDelivery` resolver in StackAdapt's current schema. The primary
# query joins three resolvers:
#
#   - advertisers(first:1).nodes[0].stats — lifetime advertiser totals,
#     consumed by the analytics summary (unchanged shape).
#   - campaigns(first:100).nodes — full campaign list (id, name, status,
#     group, channel). One row per campaign regardless of activity.
#   - campaignDelivery(dataType:TABLE, granularity:TOTAL, date:{from,to})
#     .records.nodes — windowed per-campaign metrics. One row per campaign
#     WITH activity in the date window. Campaigns without activity get
#     zero metrics in _parse_summary, which is semantically correct for
#     threshold generators ("did this campaign trip a threshold this
#     window?" — silent on inactive campaigns is the right answer).
#
# `campaignDelivery` is a UNION returning either CampaignDeliveryOutcome
# (with records) or Progress (async-pending placeholder). Both cases are
# handled non-destructively in _parse_summary — a Progress response logs
# at info and continues with zero per-campaign metrics, which the
# threshold generators correctly read as "no signal."
# =============================================================================


_CAMPAIGNS_QUERY = """
query CampaignsAndDelivery($from: ISO8601Date!, $to: ISO8601Date!) {
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
  campaignDelivery(
    dataType: TABLE,
    granularity: TOTAL,
    date: { from: $from, to: $to }
  ) {
    __typename
    ... on CampaignDeliveryOutcome {
      records {
        nodes {
          campaign { id }
          metrics {
            impressionsBigint clicksBigint conversionsBigint
            cost ctr ecpa roas
          }
        }
      }
    }
    ... on Progress { _ }
  }
}
"""


# Fallback query — drops campaignDelivery entirely. Used when the primary
# query errors (e.g. schema drift on campaignDelivery in the future). Returns
# advertiser totals + campaign list with no per-campaign metrics; threshold
# generators correctly produce no signal on the zero metrics.
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


# Threshold generators evaluate "act now" signals (high CPA, zero conversion
# at meaningful spend, persistently low CTR). A 30-day rolling window
# smooths daily noise without diluting the signal so much that recent bad
# spend gets averaged out by older good spend. Matches StackAdapt UI's
# default reporting horizon.
_DELIVERY_WINDOW_DAYS = 30


def _campaign_window() -> tuple[str, str]:
    """30-day rolling window ending today (UTC). Returns (from, to) ISO dates."""
    today = datetime.now(timezone.utc).date()
    from_date = today - timedelta(days=_DELIVERY_WINDOW_DAYS)
    return from_date.isoformat(), today.isoformat()


def _api_key() -> Optional[str]:
    return os.environ.get("STACKADAPT_GRAPHQL_KEY")


def _query_sync(
    query: str,
    variables: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    key = _api_key()
    if not key:
        return {"errors": [{"message": "STACKADAPT_GRAPHQL_KEY unset"}]}
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {key}",
    }
    body: dict[str, Any] = {"query": query}
    if variables is not None:
        body["variables"] = variables
    try:
        response = requests.post(
            STACKADAPT_GRAPHQL_ENDPOINT,
            json=body,
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


def _parse_campaign(
    node: dict[str, Any],
    metrics: Optional[dict[str, Any]] = None,
) -> StackAdaptCampaign:
    metrics = metrics or {}
    return StackAdaptCampaign(
        id=node.get("id", ""),
        name=node.get("name", "") or "",
        channel_type=node.get("channelType"),
        group_name=(node.get("campaignGroup") or {}).get("name"),
        status=(node.get("campaignStatus") or {}).get("status"),
        impressions=_parse_int(metrics.get("impressionsBigint")),
        clicks=_parse_int(metrics.get("clicksBigint")),
        conversions=_parse_int(metrics.get("conversionsBigint")),
        spend_usd=_parse_float(metrics.get("cost")),
        ctr=_parse_float(metrics.get("ctr")),
        cpa_usd=_parse_optional_float(metrics.get("ecpa")),
        roas=_parse_optional_float(metrics.get("roas")),
    )


def _delivery_metrics_by_campaign_id(
    payload_data: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    """Build campaign_id → metrics map from a campaignDelivery payload.

    Handles three response shapes non-destructively:
      - CampaignDeliveryOutcome with records → populated map.
      - Progress (async pending) → empty map + info log; the next call
        cycle typically resolves to records.
      - Missing (e.g. fallback query) → empty map.

    Empty map is the correct degraded state — campaigns receive zero
    metrics, threshold generators silently produce no signal, the UI
    renders the live-source empty state.
    """
    delivery = payload_data.get("campaignDelivery") or {}
    typename = delivery.get("__typename")
    by_id: dict[str, dict[str, Any]] = {}

    if typename == "CampaignDeliveryOutcome":
        records_nodes = (delivery.get("records") or {}).get("nodes") or []
        for record in records_nodes:
            campaign_ref = record.get("campaign") or {}
            cid = campaign_ref.get("id")
            if not cid:
                continue
            by_id[str(cid)] = record.get("metrics") or {}
    elif typename == "Progress":
        logger.info(
            "campaignDelivery returned Progress (async pending); "
            "per-campaign metrics will be zero this cycle"
        )

    return by_id


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

    delivery_by_id = _delivery_metrics_by_campaign_id(data)
    campaigns = [
        _parse_campaign(node, delivery_by_id.get(str(node.get("id", ""))))
        for node in campaigns_nodes
    ]

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

    from_date, to_date = _campaign_window()
    primary_variables = {"from": from_date, "to": to_date}
    payload = await asyncio.to_thread(
        _query_sync, _CAMPAIGNS_QUERY, primary_variables,
    )

    if payload.get("errors"):
        error_msg = str(payload["errors"][0].get("message", "unknown error"))
        # If the primary query failed (e.g. campaignDelivery schema drift),
        # retry without per-campaign metrics so we at least get the list.
        logger.info(
            "StackAdapt primary query errored, retrying without campaign delivery: %s",
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


# =============================================================================
# Recommendation generation
# =============================================================================


# Thresholds are deliberately conservative — these are the signals strong
# enough that they warrant surfacing to the human partner as a proposal.
# Tighter thresholds come from data-driven category priors once the
# analytics loop (Loop A) has accumulated enough observations.
_CPA_MULTIPLIER_FOR_PAUSE = 3.0      # CPA > 3x advertiser average → pause
_ZERO_CONVERSION_SPEND_USD = 1_000.0  # spend threshold where zero-conv matters
_MIN_IMPRESSIONS_FOR_CTR_CALL = 1_000  # below this, CTR is too noisy to act on
_LOW_CTR_THRESHOLD = 0.001           # 0.1% — well below typical display norms


def _today_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d")


def _deterministic_id(campaign_id: str, rec_type: str) -> str:
    return f"rec:{campaign_id}:{rec_type}:{_today_stamp()}"


def _advertiser_average_cpa(summary: StackAdaptSummary) -> Optional[float]:
    if summary.conversions <= 0:
        return None
    return summary.spend_usd / summary.conversions


def _campaign_cpa(c: StackAdaptCampaign) -> Optional[float]:
    if c.conversions <= 0:
        return None
    return c.spend_usd / c.conversions


def _generate_high_cpa_recommendation(
    c: StackAdaptCampaign, advertiser_avg_cpa: float, now: datetime,
) -> Optional[RecommendationDetail]:
    """When a single campaign's CPA is a multiple of the advertiser
    average, propose pausing it.
    """
    campaign_cpa = _campaign_cpa(c)
    if campaign_cpa is None:
        return None
    if campaign_cpa < advertiser_avg_cpa * _CPA_MULTIPLIER_FOR_PAUSE:
        return None

    ratio = campaign_cpa / advertiser_avg_cpa

    # A14: THRESHOLD_GENERATORS_AS_FALLBACK — correlational rule-based
    # generator with hand-composed evidence. Tagged source="threshold" so
    # the UI can render at lower priority than DCIL directives and the
    # audit can trace decisions back to the correlational path. Retires
    # when DCIL produces ≥1 directive per active campaign per week
    # sustained for two weeks.
    return RecommendationDetail(
        id=_deterministic_id(c.id, "pause_campaign_high_cpa"),
        source="threshold",
        type="pause_campaign",
        title=f"Pause '{c.name}' — CPA {ratio:.1f}× advertiser average",
        summary=(
            f"This campaign's CPA of ${campaign_cpa:,.0f} is {ratio:.1f}× the "
            f"advertiser's overall CPA of ${advertiser_avg_cpa:,.0f}. "
            f"Redirecting the spend is likely to improve blended efficiency "
            f"unless there is strategic reason to keep this campaign running."
        ),
        campaign_id=c.id,
        campaign_name=c.name,
        preferred_choice="pause",
        alternatives=[
            RecommendationAlternative(
                id="pause",
                label="Pause the campaign",
                description=(
                    "Stop delivery. Redirect spend to campaigns running at or "
                    "below advertiser-average CPA."
                ),
                predicted_outcome=(
                    f"Blended CPA improves ~{((ratio - 1) / ratio) * 100:.0f}% "
                    f"if the freed spend performs at advertiser average."
                ),
            ),
            RecommendationAlternative(
                id="continue",
                label="Keep running",
                description=(
                    "Leave the campaign active. Appropriate if the campaign is "
                    "serving a strategic purpose (brand-building, awareness, "
                    "testing new creative) whose value isn't captured by CPA."
                ),
                predicted_outcome=(
                    f"Continued spend at ${campaign_cpa:,.0f} CPA until a "
                    f"change in creative or audience moves the needle."
                ),
            ),
            RecommendationAlternative(
                id="diagnose",
                label="Pause + diagnostic review",
                description=(
                    "Pause the campaign but schedule a bilateral-cascade "
                    "diagnostic to identify whether the issue is audience fit, "
                    "mechanism selection, or creative quality — then relaunch "
                    "with the corrected configuration."
                ),
                predicted_outcome=(
                    "Short-term spend stops; relaunch timing depends on the "
                    "diagnostic but typically 3–7 days."
                ),
            ),
        ],
        evidence=UncertaintyBreakdown(
            confident=[
                ConfidentClaim(
                    claim=(
                        f"Campaign CPA is ${campaign_cpa:,.0f} — observed, "
                        f"not predicted."
                    ),
                    sources=[
                        "StackAdapt campaign stats (live)",
                        f"{c.conversions:,} conversions / ${c.spend_usd:,.0f} spend",
                    ],
                    strength=1.0,
                ),
                ConfidentClaim(
                    claim=(
                        f"Advertiser average CPA is ${advertiser_avg_cpa:,.0f}."
                    ),
                    sources=["StackAdapt advertiser stats (live)"],
                    strength=1.0,
                ),
                ConfidentClaim(
                    claim=(
                        f"Pausing this single campaign frees "
                        f"${c.spend_usd:,.0f} of spend for redistribution."
                    ),
                    sources=["StackAdapt spend figures"],
                    strength=1.0,
                ),
            ],
            uncertain=[
                UncertainClaim(
                    claim=(
                        "Whether the underperformance is driven by creative, "
                        "audience mismatch, mechanism selection, or channel."
                    ),
                    missing=(
                        "Per-archetype breakdown of this campaign's "
                        "performance and mechanism-level conversion data."
                    ),
                    would_reduce=(
                        "Running the bilateral-cascade diagnostic over the "
                        "campaign's audience segments."
                    ),
                ),
                UncertainClaim(
                    claim=(
                        "How the freed spend would perform if redirected."
                    ),
                    missing=(
                        "Incrementality test on the destination campaigns."
                    ),
                    would_reduce=(
                        "A geo-holdout on the campaigns we plan to scale into."
                    ),
                ),
            ],
            possibly_wrong=[
                PossiblyWrongClaim(
                    claim=(
                        "Pause improves blended efficiency. It may not if the "
                        "campaign is serving awareness or retargeting that "
                        "supports conversions credited elsewhere."
                    ),
                    conflicting_signal=(
                        "No attribution data here — we're looking at direct "
                        "CPA only. A high-funnel campaign often carries a "
                        "worse CPA but drives downstream conversions."
                    ),
                    alternative=(
                        "Attribute conversions across the full path before "
                        "declaring this campaign wasteful."
                    ),
                ),
            ],
        ),
        expected_horizon_class="days",
        status="pending",
        created_at=now,
    )


def _generate_zero_conversion_recommendation(
    c: StackAdaptCampaign, now: datetime,
) -> Optional[RecommendationDetail]:
    """When a campaign has significant spend but zero conversions."""
    if c.conversions > 0:
        return None
    if c.spend_usd < _ZERO_CONVERSION_SPEND_USD:
        return None

    # A14: THRESHOLD_GENERATORS_AS_FALLBACK (see header on the high-CPA
    # generator above for the full retirement contract).
    return RecommendationDetail(
        id=_deterministic_id(c.id, "zero_conversions"),
        source="threshold",
        type="mechanism_shift",
        title=f"'{c.name}' — ${c.spend_usd:,.0f} spent, 0 conversions",
        summary=(
            f"The campaign has consumed ${c.spend_usd:,.0f} without a single "
            f"tracked conversion. This is above the ${_ZERO_CONVERSION_SPEND_USD:,.0f} "
            f"threshold where continued operation without any conversion signal "
            f"becomes a strong indicator that something structural is wrong — "
            f"pixel, audience, creative, or mechanism."
        ),
        campaign_id=c.id,
        campaign_name=c.name,
        preferred_choice="diagnose_and_shift",
        alternatives=[
            RecommendationAlternative(
                id="diagnose_and_shift",
                label="Pause + diagnostic + mechanism shift",
                description=(
                    "Pause delivery. Verify the conversion pixel fires. Run "
                    "the bilateral-cascade diagnostic. Restart with a shifted "
                    "mechanism (archetype and persuasion technique) aligned "
                    "to the diagnostic output."
                ),
                predicted_outcome=(
                    "If the issue is pixel/tracking: conversion reporting "
                    "resumes. If the issue is fit: mechanism-shift typically "
                    "moves CVR from zero to category benchmark within 7–14 "
                    "days."
                ),
            ),
            RecommendationAlternative(
                id="pause_only",
                label="Pause with no further action",
                description=(
                    "Stop delivery and cut losses. Use when the campaign "
                    "purpose no longer applies."
                ),
            ),
            RecommendationAlternative(
                id="continue",
                label="Keep running",
                description=(
                    "Leave active. Only appropriate if spend is a deliberate "
                    "test cost and the learning value exceeds the loss."
                ),
            ),
        ],
        evidence=UncertaintyBreakdown(
            confident=[
                ConfidentClaim(
                    claim=(
                        f"Spend to date: ${c.spend_usd:,.0f} across "
                        f"{c.impressions:,} impressions and {c.clicks:,} clicks."
                    ),
                    sources=["StackAdapt campaign stats (live)"],
                    strength=1.0,
                ),
                ConfidentClaim(
                    claim="Tracked conversions: 0.",
                    sources=["StackAdapt campaign stats (live)"],
                    strength=1.0,
                ),
            ],
            uncertain=[
                UncertainClaim(
                    claim=(
                        "Whether conversions are actually not happening, or "
                        "the pixel is misconfigured and not firing."
                    ),
                    missing="Independent conversion signal (CRM export, server-side postback).",
                    would_reduce=(
                        "Reconciliation against CRM or internal analytics."
                    ),
                ),
                UncertainClaim(
                    claim=(
                        "Which dimension of the mechanism (archetype, "
                        "persuasion technique, context) is causing the "
                        "misalignment."
                    ),
                    missing=(
                        "Bilateral-cascade diagnostic across the campaign's "
                        "audience segments."
                    ),
                    would_reduce=(
                        "Per-segment decomposition of the buyer-side "
                        "construct activations vs. brand-side copy."
                    ),
                ),
            ],
            possibly_wrong=[
                PossiblyWrongClaim(
                    claim=(
                        "Mechanism shift will resolve the issue. It won't if "
                        "the fundamental issue is tracking/pixel."
                    ),
                    conflicting_signal=(
                        "Click rate is non-zero, suggesting the campaign is "
                        "at least getting attention — so pure audience "
                        "misalignment is less likely than mechanism fit."
                    ),
                    alternative=(
                        "Start by verifying the conversion pixel fires "
                        "end-to-end before shifting mechanism."
                    ),
                ),
            ],
        ),
        expected_horizon_class="weeks",
        status="pending",
        created_at=now,
    )


def _generate_low_ctr_recommendation(
    c: StackAdaptCampaign, now: datetime,
) -> Optional[RecommendationDetail]:
    """When a campaign's CTR is below 0.1% with meaningful volume."""
    if c.impressions < _MIN_IMPRESSIONS_FOR_CTR_CALL:
        return None
    if c.ctr >= _LOW_CTR_THRESHOLD:
        return None

    # A14: THRESHOLD_GENERATORS_AS_FALLBACK (see header on the high-CPA
    # generator for the full retirement contract).
    return RecommendationDetail(
        id=_deterministic_id(c.id, "low_ctr"),
        source="threshold",
        type="creative_rotate",
        title=f"'{c.name}' — CTR {c.ctr * 100:.3f}% (low)",
        summary=(
            f"CTR of {c.ctr * 100:.3f}% across {c.impressions:,} impressions is "
            f"below the 0.1% floor where psychologically-targeted display "
            f"typically runs. This is usually a creative-fit issue — the copy "
            f"is not landing as a goal-fulfillment stimulus for the audience "
            f"being reached."
        ),
        campaign_id=c.id,
        campaign_name=c.name,
        preferred_choice="rotate_creative",
        alternatives=[
            RecommendationAlternative(
                id="rotate_creative",
                label="Rotate creative to archetype-matched variants",
                description=(
                    "Refresh creative to variants that match the campaign's "
                    "archetype — copy and visual that serves as a "
                    "goal-fulfillment stimulus rather than a persuasion "
                    "argument."
                ),
                predicted_outcome=(
                    "CTR typically moves 2–5× when copy aligns with the "
                    "activated archetype, based on bilateral-cascade "
                    "observations in similar categories."
                ),
            ),
            RecommendationAlternative(
                id="audience_narrow",
                label="Narrow the audience",
                description=(
                    "Keep the creative but tighten targeting to the "
                    "archetypes with the strongest bilateral alignment for "
                    "this brand."
                ),
            ),
            RecommendationAlternative(
                id="both",
                label="Rotate creative + narrow audience",
                description=(
                    "Do both simultaneously. Fastest movement, but "
                    "confounded — you won't be able to attribute the "
                    "improvement to either change individually."
                ),
            ),
        ],
        evidence=UncertaintyBreakdown(
            confident=[
                ConfidentClaim(
                    claim=(
                        f"CTR is {c.ctr * 100:.3f}% ({c.clicks:,} clicks / "
                        f"{c.impressions:,} impressions)."
                    ),
                    sources=["StackAdapt campaign stats (live)"],
                    strength=1.0,
                ),
                ConfidentClaim(
                    claim=(
                        "Impression volume is sufficient for the CTR "
                        "estimate to be stable."
                    ),
                    sources=[f"n = {c.impressions:,} impressions"],
                    strength=min(1.0, c.impressions / 10_000.0),
                ),
            ],
            uncertain=[
                UncertainClaim(
                    claim=(
                        "Whether the creative, the audience, or the "
                        "mechanism is the primary driver."
                    ),
                    missing=(
                        "Per-archetype CTR breakdown within this campaign."
                    ),
                    would_reduce=(
                        "Splitting the campaign by archetype and looking at "
                        "CTR per segment."
                    ),
                ),
            ],
            possibly_wrong=[
                PossiblyWrongClaim(
                    claim=(
                        "Rotating creative will fix this. It won't if the "
                        "fundamental issue is that the audience being reached "
                        "does not include the archetypes the brand serves."
                    ),
                    conflicting_signal=(
                        "If CTR is low across every archetype, creative "
                        "rotation alone won't recover the campaign."
                    ),
                    alternative=(
                        "Check per-archetype CTR before committing to "
                        "creative as the lever. If every archetype is low, "
                        "the issue is audience fit, not copy."
                    ),
                ),
            ],
        ),
        expected_horizon_class="days",
        status="pending",
        created_at=now,
    )


# =============================================================================
# DCIL → recommendation loader
#
# The directive store (`dcil_directives` in PostgreSQL via the admin db pool)
# is the inferential / theory-grounded source of system-proposed changes. We
# load pending directives (status="proposed") and project each onto the
# recommendation contract so the operator sees ONE queue regardless of source.
#
# Mapping discipline:
#   - Structural fields (i_squared, expected_lift_pct, current/proposed
#     value, rollback_conditions) are carried through as first-class fields
#     on RecommendationDetail and ALSO surfaced as ConfidentClaims so the
#     existing UncertaintyPanel renders them. The claim text labels the
#     value (e.g. "i² = 23%"); it does not interpret it. Interpretation is
#     antipattern A4.
#   - Each rollback_condition becomes a PossiblyWrongClaim — these are
#     literally "the proposal is wrong if this condition fires", so they
#     map structurally onto the possibly_wrong slot.
#   - directive.rationale and directive.bilateral_evidence are upstream-
#     authored strings (A4 drift in directive_generator.py — to be
#     retired at source post-pilot, NOT papered over here). We carry them
#     through unchanged on RecommendationDetail.directive_rationale /
#     .directive_bilateral_evidence with explicit attribution. The UI
#     renders them in a separate "directive narrative — generator-
#     authored" section so they cannot be mistaken for derived views of
#     atom state.
# =============================================================================


# Map DirectiveType.value (the string stored in `dcil_directives.directive_type`)
# onto the dashboard's RecommendationType literal. Unknown DCIL types fall back
# to "other" rather than failing — DCIL evolves faster than the dashboard
# literal, and an unknown-type directive should still be visible to the
# operator. Unknown types should be added to RecommendationType when they
# stabilize.
_DCIL_TYPE_TO_RECOMMENDATION_TYPE: dict[str, str] = {
    "budget_reallocation": "budget_shift",
    "mechanism_rotation": "mechanism_shift",
    "creative_swap": "creative_rotate",
    "pause_resume": "pause_campaign",
    "domain_targeting": "audience_expand",
    "geo_targeting": "audience_expand",
    "dayparting": "other",
    "frequency_cap": "other",
}


def _format_value(value: Any) -> str:
    """Render a current/proposed value for display in a claim. Structural —
    no interpretation. Numbers get thousands separators, dicts get JSON-ish
    rendering, strings pass through.
    """
    if value is None:
        return "—"
    if isinstance(value, (int, float)):
        return f"{value:,}" if isinstance(value, int) else f"{value:,.4g}"
    if isinstance(value, dict):
        return ", ".join(f"{k}={_format_value(v)}" for k, v in value.items())
    if isinstance(value, (list, tuple)):
        return "[" + ", ".join(_format_value(v) for v in value) + "]"
    return str(value)


def _dcil_directive_to_recommendation(
    directive: dict[str, Any], campaign_name: Optional[str], now: datetime,
) -> RecommendationDetail:
    """Project a `dcil_directives` row onto RecommendationDetail.

    The directive row comes from the same shape the admin router's
    `_directive_to_response` expects. We deserialize JSON-stored fields
    (`current_value`, `proposed_value`, `rollback_conditions`,
    `bilateral_evidence`) defensively because the underlying storage may
    be string-JSON (asyncpg) or already-parsed (sqlite fallback).
    """
    import json as _json

    def _maybe_parse(v: Any) -> Any:
        if isinstance(v, str):
            try:
                return _json.loads(v)
            except (ValueError, TypeError):
                return v
        return v

    directive_id = str(directive["id"])
    directive_type = directive.get("directive_type") or "other"
    parameter = directive.get("parameter")
    current_value = _maybe_parse(directive.get("current_value"))
    proposed_value = _maybe_parse(directive.get("proposed_value"))
    rationale = directive.get("rationale")
    bilateral_evidence = directive.get("bilateral_evidence")
    i_squared = directive.get("i_squared")
    if i_squared is not None:
        i_squared = float(i_squared)
    confidence = directive.get("confidence")
    if confidence is not None:
        confidence = float(confidence)
    expected_lift_pct = directive.get("expected_lift_pct")
    if expected_lift_pct is not None:
        expected_lift_pct = float(expected_lift_pct)
    rollback_raw = directive.get("rollback_conditions") or []
    rollback_parsed = _maybe_parse(rollback_raw) or []
    rollback_conditions = [str(r) for r in rollback_parsed if r]

    rec_type = _DCIL_TYPE_TO_RECOMMENDATION_TYPE.get(
        directive_type.lower() if isinstance(directive_type, str) else "",
        "other",
    )

    # Title and summary derive from STRUCTURAL diff, not from the rationale
    # string. The operator sees what is changing, not the generator's narrative.
    title_campaign = f"'{campaign_name}'" if campaign_name else f"campaign {directive.get('campaign_id', '?')}"
    if parameter and current_value is not None and proposed_value is not None:
        title = (
            f"{rec_type.replace('_', ' ')} on {title_campaign}: "
            f"{parameter} {_format_value(current_value)} → "
            f"{_format_value(proposed_value)}"
        )
    elif parameter and proposed_value is not None:
        title = (
            f"{rec_type.replace('_', ' ')} on {title_campaign}: "
            f"set {parameter} = {_format_value(proposed_value)}"
        )
    else:
        title = f"{rec_type.replace('_', ' ')} on {title_campaign}"

    if expected_lift_pct is not None:
        summary_text = (
            f"DCIL directive proposes {parameter or 'a parameter change'} "
            f"with expected lift {expected_lift_pct:+.1f}%. "
            f"i² = {i_squared:.0f}%." if i_squared is not None
            else (
                f"DCIL directive proposes {parameter or 'a parameter change'} "
                f"with expected lift {expected_lift_pct:+.1f}%."
            )
        )
    else:
        summary_text = (
            f"DCIL directive proposes {parameter or 'a parameter change'} "
            f"on this campaign. Review the structural fields and approve, "
            f"block, or modify."
        )

    # Confident claims = structural facts the generator emitted as numbers.
    # Each is a label for a value; not interpretation. Interpretation lives
    # in the directive narrative section (A4-attributed).
    confident: list[ConfidentClaim] = []
    if parameter and current_value is not None and proposed_value is not None:
        confident.append(
            ConfidentClaim(
                claim=(
                    f"{parameter}: "
                    f"{_format_value(current_value)} → "
                    f"{_format_value(proposed_value)}"
                ),
                sources=["dcil_directives.current_value, dcil_directives.proposed_value"],
                strength=1.0,
            )
        )
    if i_squared is not None:
        confident.append(
            ConfidentClaim(
                claim=f"i² = {i_squared:.0f}%",
                sources=["DCIL meta-analytic estimator (DerSimonian-Laird)"],
                strength=1.0,
            )
        )
    if expected_lift_pct is not None:
        confident.append(
            ConfidentClaim(
                claim=f"expected lift = {expected_lift_pct:+.1f}%",
                sources=["DCIL effect-size estimator"],
                strength=1.0,
            )
        )
    if confidence is not None:
        confident.append(
            ConfidentClaim(
                claim=f"generator confidence = {confidence:.2f}",
                sources=["DCIL hypothesis posterior"],
                strength=1.0,
            )
        )

    # Possibly-wrong claims = rollback_conditions, structurally. Each is
    # literally a forward statement of when the proposal would be wrong.
    possibly_wrong: list[PossiblyWrongClaim] = [
        PossiblyWrongClaim(
            claim=f"This proposal is wrong if: {condition}",
            conflicting_signal=(
                "Forward rollback condition — adjudicated at horizon expiry."
            ),
            alternative=(
                f"Roll back to {parameter} = {_format_value(current_value)}"
                if parameter and current_value is not None
                else "Roll back to current configuration"
            ),
        )
        for condition in rollback_conditions
    ]

    # Uncertain claims surface the upstream-A4 status of the generator
    # narrative explicitly. The operator should know that bilateral_evidence
    # and rationale are author-strings, not derived views of atom state.
    uncertain: list[UncertainClaim] = []
    if bilateral_evidence or rationale:
        uncertain.append(
            UncertainClaim(
                claim=(
                    "Generator narrative is author-string; structured "
                    "evidence trace not yet emitted at the source."
                ),
                missing=(
                    "directive_generator.py emits free-text bilateral_evidence "
                    "and rationale rather than structured evidence trace. "
                    "Tracked as upstream A4 drift to retire post-pilot."
                ),
                would_reduce=(
                    "Refactor directive_generator.py to emit structured "
                    "evidence (atom activations, edge IDs, link posteriors) "
                    "in place of authored summary strings."
                ),
            )
        )

    alternatives = [
        RecommendationAlternative(
            id="approve",
            label="Approve the directive",
            description=(
                f"Set {parameter} = {_format_value(proposed_value)}."
                if parameter and proposed_value is not None
                else "Apply the proposed change as defined by the directive."
            ),
            predicted_outcome=(
                f"Expected lift {expected_lift_pct:+.1f}%."
                if expected_lift_pct is not None else None
            ),
        ),
        RecommendationAlternative(
            id="block",
            label="Block the directive",
            description=(
                "Reject the proposed change. Records the rejection as a "
                "deviation; adjudicated at horizon expiry to update theory."
            ),
            predicted_outcome=(
                f"Current {parameter} = {_format_value(current_value)} maintained."
                if parameter and current_value is not None
                else "Current configuration preserved."
            ),
        ),
        RecommendationAlternative(
            id="modify",
            label="Modify and approve",
            description=(
                "Apply a different value than DCIL proposed. Captures your "
                "alternative as a hypothesis tested against the realized "
                "outcome."
            ),
        ),
    ]

    created_at_raw = directive.get("created_at")
    if isinstance(created_at_raw, datetime):
        created_at = created_at_raw
    else:
        try:
            created_at = datetime.fromisoformat(str(created_at_raw).replace("Z", "+00:00"))
        except (ValueError, TypeError):
            created_at = now

    return RecommendationDetail(
        id=f"dcil:{directive_id}",
        source="dcil",
        directive_id=directive_id,
        type=rec_type,  # type: ignore[arg-type]
        title=title,
        summary=summary_text,
        campaign_id=str(directive.get("campaign_id") or ""),
        campaign_name=campaign_name,
        preferred_choice="approve",
        alternatives=alternatives,
        evidence=UncertaintyBreakdown(
            confident=confident,
            uncertain=uncertain,
            possibly_wrong=possibly_wrong,
        ),
        expected_horizon_class="days",
        status="pending",
        created_at=created_at,
        parameter=parameter,
        current_value=current_value,
        proposed_value=proposed_value,
        i_squared=i_squared,
        expected_lift_pct=expected_lift_pct,
        generator_confidence=confidence,
        rollback_conditions=rollback_conditions,
        directive_rationale=rationale,
        directive_bilateral_evidence=bilateral_evidence,
    )


async def _load_dcil_directives(
    campaign_id_to_name: dict[str, str], now: datetime,
) -> list[RecommendationDetail]:
    """Load pending DCIL directives and project to RecommendationDetail.

    Returns an empty list if the admin db pool is unreachable or no
    directives are proposed. The dashboard endpoint must remain functional
    even when the directive store is empty (e.g., DCIL has not yet run for
    this campaign).
    """
    try:
        from adam.api.admin.db import get_db
        db = get_db()
        rows = await db.fetch_all(
            "SELECT * FROM dcil_directives WHERE status = 'proposed' "
            "ORDER BY created_at DESC"
        )
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("DCIL directive load failed: %s", exc)
        return []

    recs: list[RecommendationDetail] = []
    for row in rows:
        try:
            campaign_id = str(row.get("campaign_id") or "")
            campaign_name = campaign_id_to_name.get(campaign_id)
            recs.append(
                _dcil_directive_to_recommendation(dict(row), campaign_name, now)
            )
        except Exception as exc:
            logger.warning(
                "Skipping DCIL directive %s: mapping failed: %s",
                row.get("id"), exc,
            )
            continue
    return recs


async def generate_recommendations(
    user_id: str,
) -> tuple[list[RecommendationDetail], str, Optional[str]]:
    """Produce structured recommendations from the inferential learning loop.

    Sources, in priority order:
      1. DCIL directives (status="proposed") — theory-grounded, structural.
      2. Threshold generators — A14 fallback (THRESHOLD_GENERATORS_AS_FALLBACK)
         applied only to campaigns that DCIL has NOT proposed for. This is
         the Pinker override discipline: when memory (DCIL's reinforced
         theory chain on a specific campaign) has produced a directive, the
         productive rule layer (correlational thresholds) defers.

    Returns (recommendations, source, source_note). source is "live" |
    "unavailable" reflecting the StackAdapt connection state. DCIL
    recommendations may still surface even when StackAdapt is unavailable
    if directives exist on prior campaigns.
    """
    summary = await fetch_stackadapt_summary()
    now = datetime.now(timezone.utc)

    campaign_id_to_name = {c.id: c.name for c in summary.campaigns}
    dcil_recs = await _load_dcil_directives(campaign_id_to_name, now)
    dcil_campaign_ids = {r.campaign_id for r in dcil_recs if r.campaign_id}

    # Loop B: ready horizon adjudications. Independent source — they're
    # judgments on past operator deviations, not new proposals — so the
    # Pinker override on threshold doesn't apply here. They merge into
    # the queue alongside DCIL.
    horizon_recs = await _load_horizon_adjudications(user_id, now)

    # Threshold path is gated by StackAdapt availability — it has no DB
    # to read from. DCIL path is independent of StackAdapt.
    threshold_recs: list[RecommendationDetail] = []
    if summary.source == "live":
        advertiser_avg_cpa = _advertiser_average_cpa(summary)
        for campaign in summary.campaigns:
            # Pinker override: skip threshold generators for campaigns
            # where DCIL has already proposed. The directive carries the
            # full inferential chain; the threshold evidence panel would
            # be redundant noise.
            if campaign.id in dcil_campaign_ids:
                continue

            if advertiser_avg_cpa is not None:
                rec = _generate_high_cpa_recommendation(
                    campaign, advertiser_avg_cpa, now,
                )
                if rec is not None:
                    threshold_recs.append(rec)

            rec = _generate_zero_conversion_recommendation(campaign, now)
            if rec is not None:
                threshold_recs.append(rec)

            rec = _generate_low_ctr_recommendation(campaign, now)
            if rec is not None:
                threshold_recs.append(rec)

    recommendations = dcil_recs + horizon_recs + threshold_recs
    recommendations.sort(key=lambda r: r.created_at, reverse=True)

    if not recommendations:
        if summary.source != "live":
            return [], "unavailable", summary.reason
        return (
            recommendations, "live",
            f"No pending directives, ready horizons, or threshold "
            f"signals across {len(summary.campaigns)} live StackAdapt "
            f"campaign(s).",
        )

    note = (
        f"{len(dcil_recs)} DCIL directive(s) + {len(horizon_recs)} "
        f"horizon adjudication(s) + {len(threshold_recs)} threshold "
        f"signal(s) across {len(summary.campaigns)} live StackAdapt "
        f"campaign(s)."
    )
    return recommendations, "live", note


# =============================================================================
# Horizon-adjudication loader (Slice D1)
#
# Loop B closes when a deviation's horizon window expires and the operator
# adjudicates whether the system was right, the operator was right, or the
# evidence is indeterminate. Today that surface lives only in the
# `(app)/learning/` Adjudication Horizons tab — separate from the
# recommendations queue where DCIL directives live. Pilot-week strategy
# (validated 2026-04-25): consolidate both onto the recommendations queue
# so the operator's attention budget covers everything actionable in one
# place. Single-surface attention, single-place selection signal — both
# the multi-lens pass (PK/PD undosing, bioinformatics merge-upstream,
# Pinker dual-mechanism, Dawkins selection-at-decision-point, receptor-
# ligand binding-requires-presence) converge on this.
#
# We read directly from Neo4j the same way `/deviations/horizons` does in
# the router, joining the Deviation to its original Recommendation snapshot.
# A horizon is "ready" when (now - created_at) >= window_days_for_horizon_class
# AND the deviation's adjudication_status is still 'pending'.
# =============================================================================


# Mirrors _HORIZON_TO_DAYS in the router. Single source of truth would be
# nicer; pilot-week ships duplicated to keep the slice minimal and avoid
# touching the router for a constants reshuffle. Tracked in commit message.
_HORIZON_TO_DAYS: dict[str, float] = {
    "hours": 1.0,
    "days": 7.0,
    "weeks": 14.0,
    "months": 60.0,
}


def _horizon_deviation_to_recommendation(
    record: dict[str, Any], now: datetime,
) -> RecommendationDetail:
    """Project a (Deviation, Recommendation) pair onto RecommendationDetail.

    Loop B horizon adjudications carry the original recommendation's
    snapshot (preserved at decide-time on the Recommendation node) plus
    the deviation's system_choice / user_choice / stated_rationale. The
    operator's task on this surface is JUDGMENT (system_right /
    user_right / indeterminate), not authorship of a new proposal.

    Title and summary are derived from structural state: the original
    recommendation title, the time elapsed, and the choice diff. No
    interpretive prose composed by the rendering layer (orientation A4).
    """
    deviation = record["deviation"]
    rec = record["original_recommendation"]

    deviation_id = str(deviation["id"])
    horizon_class = deviation.get("horizon_class") or "days"

    created_at_raw = deviation.get("created_at")
    if isinstance(created_at_raw, datetime):
        deviation_created_at = created_at_raw
    elif hasattr(created_at_raw, "to_native"):
        deviation_created_at = created_at_raw.to_native()
    else:
        try:
            deviation_created_at = datetime.fromisoformat(
                str(created_at_raw).replace("Z", "+00:00")
            )
        except (ValueError, TypeError):
            deviation_created_at = now

    window_days = _HORIZON_TO_DAYS.get(horizon_class, 7.0)
    days_elapsed = max(
        0.0, (now - deviation_created_at).total_seconds() / 86_400.0
    )

    system_choice = deviation.get("system_choice") or "—"
    user_choice = deviation.get("user_choice")
    stated_rationale = deviation.get("stated_rationale")

    # Original recommendation snapshot fields are stored on the Neo4j
    # Recommendation node. They reflect the recommendation AT DECIDE
    # TIME — not regenerated. This is correct: adjudication evaluates
    # the decision the operator actually made, not the current state.
    original_title = rec.get("title") if rec else None
    original_summary = rec.get("summary") if rec else None
    original_type = rec.get("type") if rec else "other"
    campaign_id = rec.get("campaign_id") if rec else None
    campaign_name = rec.get("campaign_name") if rec else None

    title = (
        f"Adjudicate: {original_title}" if original_title
        else f"Adjudicate deviation {deviation_id[-8:]}"
    )
    # Summary is structural state: horizon class + elapsed time + the
    # choice diff. No exhortation, no interpretation of what the
    # adjudication will do — that lives on the alternatives'
    # predicted_outcome where it can be cited against
    # causal_adjudicator.py.
    summary = (
        f"Horizon expired ({horizon_class}, {days_elapsed:.1f} days "
        f"elapsed). System recommended '{system_choice}'; operator "
        f"chose '{user_choice or '—'}'."
    )

    # Alternatives map onto the three adjudication outcomes the
    # causal_adjudicator records (causal_adjudicator.py:585-638). The
    # decide handler in slice D2 routes accept/modify onto these via
    # chosen_alternative; for D1 (this commit) the decide handler is
    # NOT yet wired — surface only.
    #
    # predicted_outcome strings reference the actual structural writes
    # the adjudicator performs per verdict, not interpretation. Cited:
    #   - All verdicts: Deviation.adjudication_status='adjudicated',
    #     adjudication_outcome=verdict, plus a new Outcome node
    #     (causal_adjudicator.py:587-632).
    #   - WhyLibraryEntry created ONLY on system_right
    #     (causal_adjudicator.py:635-638).
    alternatives = [
        RecommendationAlternative(
            id="system_right",
            label="System was right",
            description=(
                f"Records that the system's '{system_choice}' "
                f"matched the realized outcome better than the "
                f"operator's deviation."
            ),
            predicted_outcome=(
                "Outcome node created (attributed_to='system_choice'). "
                "A WhyLibraryEntry is generated for defensive reasoning. "
                "Deviation marked adjudicated."
            ),
        ),
        RecommendationAlternative(
            id="user_right",
            label="Operator was right",
            description=(
                f"Records that the operator's "
                f"'{user_choice or 'deviation'}' matched the realized "
                f"outcome better than the system's choice."
            ),
            predicted_outcome=(
                "Outcome node created (attributed_to='user_choice'). "
                "No WhyLibraryEntry generated for user_right. Deviation "
                "marked adjudicated."
            ),
        ),
        RecommendationAlternative(
            id="indeterminate",
            label="Evidence inconclusive",
            description=(
                "Records that available realized data does not support "
                "a confident verdict either way."
            ),
            predicted_outcome=(
                "Outcome node created (attributed_to='confounded'). "
                "No WhyLibraryEntry generated. Deviation marked "
                "adjudicated; re-opening requires a new deviation."
            ),
        ),
    ]

    confident: list[ConfidentClaim] = [
        ConfidentClaim(
            claim=f"Deviation horizon: {horizon_class}",
            sources=[f"Deviation node {deviation_id}"],
            strength=1.0,
        ),
        ConfidentClaim(
            claim=f"Time elapsed: {days_elapsed:.1f} days",
            sources=[f"Deviation.created_at"],
            strength=1.0,
        ),
        ConfidentClaim(
            claim=f"System choice: {system_choice}",
            sources=["Deviation.system_choice (snapshot at decide time)"],
            strength=1.0,
        ),
    ]
    if user_choice:
        confident.append(
            ConfidentClaim(
                claim=f"Operator choice: {user_choice}",
                sources=["Deviation.user_choice"],
                strength=1.0,
            )
        )

    uncertain: list[UncertainClaim] = []
    if stated_rationale:
        # Operator-authored rationale at decide time. Not interpretation;
        # it's the operator's own recorded hypothesis to test.
        uncertain.append(
            UncertainClaim(
                claim=(
                    f"Operator's stated rationale at decide time: "
                    f"\"{stated_rationale}\""
                ),
                missing=(
                    "The realized outcome metrics that would confirm or "
                    "refute the rationale."
                ),
                would_reduce=(
                    "Adjudicating now consumes the available realized "
                    "outcome and writes the verdict to theory."
                ),
            )
        )

    return RecommendationDetail(
        id=f"horizon:{deviation_id}",
        source="horizon_adjudication",
        type=original_type,  # type: ignore[arg-type]
        title=title,
        summary=summary,
        campaign_id=campaign_id,
        campaign_name=campaign_name,
        # Default verdict on a click-through "accept" is INDETERMINATE — the
        # epistemically humble pick. Setting "system_right" here would bias
        # the operator toward agreeing with the system on the absent-thought
        # path. The operator must explicitly pick system_right or user_right
        # via "modify"; default-accept stays indeterminate.
        preferred_choice="indeterminate",
        alternatives=alternatives,
        evidence=UncertaintyBreakdown(
            confident=confident,
            uncertain=uncertain,
            possibly_wrong=[],
        ),
        expected_horizon_class=horizon_class,  # type: ignore[arg-type]
        status="pending",
        # created_at on the queue card reflects when the horizon became
        # ready (= deviation_created_at + window_days), not when the
        # deviation itself was logged. Operators see the urgency.
        created_at=deviation_created_at + timedelta(days=window_days),
        # Structural deviation state — the UI renders a DeviationContext
        # panel from this field (slice D3), parallel to how DCIL recs
        # render DirectiveSubstance from their structural fields.
        deviation_context=DeviationContext(
            deviation_id=deviation_id,
            system_choice=system_choice,
            user_choice=user_choice,
            days_elapsed=days_elapsed,
            horizon_window_days=window_days,
            horizon_class=horizon_class,
            stated_rationale=stated_rationale,
            rationale_class=deviation.get("rationale_class"),
        ),
    )


async def _load_horizon_adjudications(
    user_id: str, now: datetime,
) -> list[RecommendationDetail]:
    """Load READY horizon adjudications and project to RecommendationDetail.

    A horizon is READY when:
      - the deviation's adjudication_status is 'pending'
      - the elapsed time since deviation.created_at meets or exceeds the
        window for its horizon_class

    The query joins each Deviation to its original Recommendation snapshot
    (the audit-trail node created by the decide handler) so the surface
    can render the system_choice / user_choice / title context.
    Deviations whose original Recommendation node is missing fall back to
    a degraded title; they are NOT silently dropped — that would hide
    real adjudications-needed from the operator.
    """
    try:
        from adam.infrastructure.neo4j.client import get_neo4j_client
        client = get_neo4j_client()
        if not client.is_connected:
            return []
    except Exception as exc:
        logger.warning("Neo4j unavailable for horizon adjudications: %s", exc)
        return []

    recs: list[RecommendationDetail] = []
    try:
        async with await client.session() as session:
            result = await session.run(
                """
                MATCH (u:DialogueUser {id: $user_id})-[:DEVIATED]->(d:Deviation)
                WHERE d.adjudication_status = 'pending'
                OPTIONAL MATCH (d)-[:FROM]->(r:Recommendation)
                RETURN d, r
                ORDER BY d.created_at ASC
                """,
                user_id=user_id,
            )
            async for record in result:
                d_node = record["d"]
                r_node = record["r"]

                # Compute readiness in Python so we can use the same
                # _HORIZON_TO_DAYS mapping the router uses; keeps the
                # readiness rule single-sourced even if the Cypher query
                # later moves window logic into the database.
                horizon_class = d_node.get("horizon_class") or "days"
                window_days = _HORIZON_TO_DAYS.get(horizon_class, 7.0)
                created_at = d_node["created_at"]
                if hasattr(created_at, "to_native"):
                    created_at = created_at.to_native()
                elif isinstance(created_at, str):
                    try:
                        created_at = datetime.fromisoformat(
                            created_at.replace("Z", "+00:00")
                        )
                    except ValueError:
                        continue
                elapsed = (now - created_at).total_seconds() / 86_400.0
                if elapsed < window_days:
                    continue

                deviation_dict = dict(d_node)
                deviation_dict["created_at"] = created_at
                rec_dict = dict(r_node) if r_node else None
                try:
                    recs.append(
                        _horizon_deviation_to_recommendation(
                            {
                                "deviation": deviation_dict,
                                "original_recommendation": rec_dict,
                            },
                            now,
                        )
                    )
                except Exception as exc:
                    logger.warning(
                        "Skipping horizon for deviation %s: mapping failed: %s",
                        d_node.get("id"), exc,
                    )
                    continue
    except Exception as exc:
        logger.warning("horizon adjudication load failed: %s", exc)
        return []

    return recs


async def route_dcil_directive_decision(
    directive_id: str,
    decision_kind: str,
    review_notes: Optional[str],
    user_id: str,
) -> str:
    """Apply a dashboard decide event onto the DCIL directive lifecycle.

    Slice A2 of the unified-decision-gate work: when the operator decides
    on a source="dcil" recommendation, the directive's row in
    `dcil_directives` is updated to reflect the operator's choice so the
    DCIL pipeline picks up only directives that have been reviewed.
    Without this, approving in the dashboard UI would persist the
    UserDecision in Neo4j but the directive would stay "proposed" forever
    and never execute — the loop would not close.

    Mapping rationale (DecisionKind → directive status):
      - "accept"  → "approved"
        The operator endorses the directive as-proposed. DCIL pipeline
        executes it on the next run within the safety rails.
      - "reject"  → "blocked"
        The operator rejects the proposal outright. The directive will
        not execute; the deviation captured upstream by
        `decide_recommendation` adjudicates at horizon expiry.
      - "modify"  → "blocked"
        The operator wants a different value than DCIL proposed. The
        directive itself is blocked; the deviation record captures the
        operator's chosen alternative as the hypothesis tested at
        horizon expiry. DCIL may regenerate a refined directive based on
        the realized outcome.

    The SQL here intentionally mirrors the admin endpoints
    (`approve_directive`, `block_directive` in
    adam/api/admin/routers/campaign_router.py) so the directive lifecycle
    state is identical regardless of which surface the operator decides
    from. We do not call the admin endpoints over HTTP — that would
    introduce an internal hop and double-auth. Same db pool, same SQL,
    same fields written. Honest unification at the data layer.
    """
    from datetime import datetime as _dt, timezone as _tz

    if decision_kind == "accept":
        new_status = "approved"
    elif decision_kind in ("reject", "modify"):
        new_status = "blocked"
    else:
        raise ValueError(
            f"Unknown decision_kind {decision_kind!r}; expected accept/modify/reject"
        )

    notes = review_notes
    if not notes:
        notes = f"{new_status} via dashboard decide ({decision_kind})"

    try:
        from adam.api.admin.db import get_db
        db = get_db()
        now = str(_dt.now(_tz.utc))
        await db.execute(
            "UPDATE dcil_directives SET status = $1, reviewed_by = $2, "
            "reviewed_at = $3, review_notes = $4, updated_at = $5 WHERE id = $6",
            new_status, user_id, now, notes, now, directive_id,
        )
    except Exception as exc:
        logger.exception(
            "DCIL directive lifecycle write failed for directive_id=%s "
            "decision=%s: %s",
            directive_id, decision_kind, exc,
        )
        raise

    return new_status


async def get_recommendation_by_id(
    user_id: str, recommendation_id: str,
) -> Optional[RecommendationDetail]:
    """Resolve a single recommendation for detail view.

    For source="dcil" recommendations (id prefix "dcil:"), reads the
    directive directly so the detail view reflects the current row state
    rather than a stale snapshot. For source="threshold" recommendations,
    regenerates from live StackAdapt metrics so the detail page reflects
    the current numbers.
    """
    if recommendation_id.startswith("dcil:"):
        directive_id = recommendation_id[len("dcil:"):]
        try:
            from adam.api.admin.db import get_db
            db = get_db()
            row = await db.fetch_one(
                "SELECT d.*, c.name AS _campaign_name FROM dcil_directives d "
                "LEFT JOIN campaigns c ON c.id = d.campaign_id "
                "WHERE d.id = $1",
                directive_id,
            )
        except Exception as exc:
            logger.warning("DCIL directive lookup failed for %s: %s", directive_id, exc)
            return None
        if not row:
            return None
        row_dict = dict(row)
        campaign_name = row_dict.pop("_campaign_name", None)
        return _dcil_directive_to_recommendation(
            row_dict, campaign_name, datetime.now(timezone.utc),
        )

    if recommendation_id.startswith("horizon:"):
        deviation_id = recommendation_id[len("horizon:"):]
        try:
            from adam.infrastructure.neo4j.client import get_neo4j_client
            client = get_neo4j_client()
            if not client.is_connected:
                return None
            async with await client.session() as session:
                result = await session.run(
                    """
                    MATCH (d:Deviation {id: $deviation_id})
                    OPTIONAL MATCH (d)-[:FROM]->(r:Recommendation)
                    RETURN d, r
                    """,
                    deviation_id=deviation_id,
                )
                record = await result.single()
        except Exception as exc:
            logger.warning("Horizon adjudication lookup failed for %s: %s",
                           deviation_id, exc)
            return None
        if not record:
            return None
        d_node = record["d"]
        r_node = record["r"]
        # Detail view does NOT re-check readiness — operator may want to
        # inspect a horizon that's already adjudicated, or one that's
        # not quite ready, by ID. List view enforces readiness; detail
        # view honors the lookup.
        deviation_dict = dict(d_node)
        created_at = deviation_dict.get("created_at")
        if hasattr(created_at, "to_native"):
            deviation_dict["created_at"] = created_at.to_native()
        rec_dict = dict(r_node) if r_node else None
        return _horizon_deviation_to_recommendation(
            {
                "deviation": deviation_dict,
                "original_recommendation": rec_dict,
            },
            datetime.now(timezone.utc),
        )

    recommendations, _source, _note = await generate_recommendations(user_id)
    for rec in recommendations:
        if rec.id == recommendation_id:
            return rec
    return None
