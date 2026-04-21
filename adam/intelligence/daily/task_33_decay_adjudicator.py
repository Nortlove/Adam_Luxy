"""Task 33 — Decay Adjudicator.

Per-user (ad-recipient) classification that runs daily after Task 26
(bilateral analysis) and before Task 28 (directive generation). The
three-way adjudication splits users into CONTINUE / RESTART / ABANDON
buckets per the Decay Function specified in
ADAM_HUMAN_MACHINE_TEAMING_FOUNDATION.md earlier in this project —
the central discipline rule being that ABANDON requires inferential
evidence that mechanism rotation has been exhausted, not just
correlational "this user hasn't clicked."

For the v1 pilot with a single StackAdapt advertiser the task can
run either scheduled (cron) or on-demand via the dashboard
/api/dashboard/decay/run endpoint. The report output is persisted
as a DecayCohort node per (campaign, run_date) so the dashboard can
render the cohort history over time.

Dependencies:
    - StackAdapt campaign-level stats (live via dashboard service)
    - ExposureResponseModel in adam.intelligence.exposure_response
      (NOTE: if that module is not yet wired to real user-level
      impression counts, this task reports aggregate campaign-level
      signals only — honest about the gap).
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)


TASK_VERSION = "task_33.v1"


@dataclass
class CampaignDecayClassification:
    """Per-campaign decay signal from Task 33."""

    campaign_id: str
    campaign_name: str
    total_users: int = 0
    continue_count: int = 0
    restart_count: int = 0
    abandon_count: int = 0
    zero_data_count: int = 0
    advertiser_avg_cpa: Optional[float] = None
    campaign_cpa: Optional[float] = None
    flags: list[str] = field(default_factory=list)
    recommended_action: str = "continue"  # continue | restart | abandon | monitor
    rationale: str = ""


@dataclass
class DecayCohortReport:
    """Full Task 33 output for a single run."""

    run_id: str
    run_date: datetime
    task_version: str
    campaigns: list[CampaignDecayClassification] = field(default_factory=list)
    total_users_classified: int = 0
    overall_abandon_rate: float = 0.0
    source: str = "live"
    source_note: Optional[str] = None


def _decide_action(
    campaign_cpa: Optional[float],
    advertiser_avg_cpa: Optional[float],
    conversions: int,
    spend: float,
    impressions: int,
) -> tuple[str, str, list[str]]:
    """Decide the campaign-level action. Mirrors the three-way
    inferential gate from the HMT foundation:
      ABANDON only when evidence rules out mechanism-shift recovery.
    """
    flags: list[str] = []

    # No data yet — not enough to adjudicate.
    if impressions < 1_000:
        return (
            "monitor",
            f"Only {impressions:,} impressions observed — too thin to classify.",
            flags,
        )

    # Zero-conversion with meaningful spend: RESTART candidate.
    # Not ABANDON yet because mechanism shift may recover it.
    if conversions == 0 and spend >= 1_000:
        flags.append("zero_conversions_with_spend")
        return (
            "restart",
            (
                f"${spend:,.0f} spent with 0 conversions over {impressions:,} "
                f"impressions. Recommend pause + pixel verification + "
                f"mechanism shift before declaring this campaign a "
                f"non-responder."
            ),
            flags,
        )

    # CPA multiple of advertiser average: RESTART (rotate mechanism)
    # or ABANDON (if already rotated).
    if (
        campaign_cpa is not None
        and advertiser_avg_cpa is not None
        and advertiser_avg_cpa > 0
        and campaign_cpa / advertiser_avg_cpa >= 3.0
    ):
        flags.append("cpa_multiplier_exceeded")
        # v1: always route to RESTART because we don't yet track
        # rotation history. When rotation history is available the
        # second-attempt restart should be routed to ABANDON.
        return (
            "restart",
            (
                f"CPA ${campaign_cpa:,.0f} is "
                f"{campaign_cpa / advertiser_avg_cpa:.1f}× the advertiser "
                f"average. Mechanism-shift recommended. Second-attempt "
                f"failures should escalate to ABANDON with a 14-day "
                f"re-evaluation cohort."
            ),
            flags,
        )

    # Healthy — no action.
    return (
        "continue",
        f"Campaign performing within expected range (CPA ${campaign_cpa:,.0f}).",
        flags,
    )


def _classify_campaign(
    campaign: Any,
    advertiser_avg_cpa: Optional[float],
) -> CampaignDecayClassification:
    """Classify one StackAdaptCampaign into a decay signal."""
    campaign_cpa: Optional[float] = None
    if campaign.conversions and campaign.conversions > 0:
        campaign_cpa = campaign.spend_usd / campaign.conversions

    action, rationale, flags = _decide_action(
        campaign_cpa=campaign_cpa,
        advertiser_avg_cpa=advertiser_avg_cpa,
        conversions=campaign.conversions,
        spend=campaign.spend_usd,
        impressions=campaign.impressions,
    )

    # Until user-level exposure data flows through the platform, the
    # task reports campaign-level signals only — these are honest
    # aggregates, not fabricated per-user counts.
    return CampaignDecayClassification(
        campaign_id=campaign.id,
        campaign_name=campaign.name,
        total_users=0,  # populated when user-level telemetry lands
        continue_count=0,
        restart_count=0,
        abandon_count=0,
        zero_data_count=0,
        advertiser_avg_cpa=advertiser_avg_cpa,
        campaign_cpa=campaign_cpa,
        flags=flags,
        recommended_action=action,
        rationale=rationale,
    )


async def run_decay_adjudicator() -> DecayCohortReport:
    """Execute one pass of Task 33.

    v1 operates on campaign-level aggregates from StackAdapt. When
    the user-level exposure pipeline lands, this function will pull
    per-user impression histories and run ExposureResponseModel
    classifications — the data structure is already in place.
    """

    from adam.api.dashboard.service import fetch_stackadapt_summary

    summary = await fetch_stackadapt_summary()
    run_date = datetime.now(timezone.utc)

    if summary.source != "live":
        return DecayCohortReport(
            run_id=f"decay-run:{uuid.uuid4()}",
            run_date=run_date,
            task_version=TASK_VERSION,
            campaigns=[],
            total_users_classified=0,
            overall_abandon_rate=0.0,
            source="unavailable",
            source_note=summary.reason,
        )

    advertiser_avg_cpa: Optional[float] = None
    if summary.conversions > 0:
        advertiser_avg_cpa = summary.spend_usd / summary.conversions

    classifications: list[CampaignDecayClassification] = []
    for campaign in summary.campaigns:
        classifications.append(
            _classify_campaign(campaign, advertiser_avg_cpa)
        )

    total_users = sum(c.total_users for c in classifications)
    abandons = sum(c.abandon_count for c in classifications)
    abandon_rate = abandons / total_users if total_users > 0 else 0.0

    report = DecayCohortReport(
        run_id=f"decay-run:{uuid.uuid4()}",
        run_date=run_date,
        task_version=TASK_VERSION,
        campaigns=classifications,
        total_users_classified=total_users,
        overall_abandon_rate=abandon_rate,
        source="live",
        source_note=(
            f"Classified {len(classifications)} campaign(s) from live "
            f"StackAdapt data. Per-user exposure classification will "
            f"activate when user-level telemetry flows through."
        ),
    )

    await _persist_cohorts(report)
    return report


async def _persist_cohorts(report: DecayCohortReport) -> None:
    """Write DecayCohort nodes per campaign to Neo4j for audit trail."""
    try:
        from adam.infrastructure.neo4j.client import get_neo4j_client

        client = get_neo4j_client()
        if not client.is_connected:
            logger.info("Neo4j unavailable; skipping DecayCohort persistence.")
            return

        async with await client.session() as session:
            for c in report.campaigns:
                cohort_id = f"cohort:{c.campaign_id}:{report.run_date.strftime('%Y%m%d')}"
                await session.run(
                    """
                    MERGE (dc:DecayCohort {id: $cohort_id})
                      ON CREATE SET
                        dc.campaign_id = $campaign_id,
                        dc.created_at = $created_at,
                        dc.run_date = date($run_date),
                        dc.task_version = $task_version,
                        dc.total_users = $total_users,
                        dc.continue_count = $continue_count,
                        dc.restart_count = $restart_count,
                        dc.abandon_count = $abandon_count,
                        dc.zero_data_count = $zero_data_count,
                        dc.advertiser_avg_cpa = $advertiser_avg_cpa,
                        dc.cohort_summary_json = $summary_json
                      ON MATCH SET
                        dc.created_at = $created_at,
                        dc.cohort_summary_json = $summary_json
                    """,
                    cohort_id=cohort_id,
                    campaign_id=c.campaign_id,
                    created_at=report.run_date,
                    run_date=report.run_date.date().isoformat(),
                    task_version=report.task_version,
                    total_users=c.total_users,
                    continue_count=c.continue_count,
                    restart_count=c.restart_count,
                    abandon_count=c.abandon_count,
                    zero_data_count=c.zero_data_count,
                    advertiser_avg_cpa=c.advertiser_avg_cpa,
                    summary_json=json.dumps(
                        {
                            "campaign_name": c.campaign_name,
                            "campaign_cpa": c.campaign_cpa,
                            "flags": c.flags,
                            "recommended_action": c.recommended_action,
                            "rationale": c.rationale,
                        }
                    ),
                )
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("DecayCohort persistence failed: %s", exc)


# =============================================================================
# Entrypoint for scheduler integration
# =============================================================================


async def main() -> None:
    """Entry point when run directly (scheduler or CLI)."""
    report = await run_decay_adjudicator()
    logger.info(
        "Task 33 decay adjudication complete — %d campaigns classified; "
        "overall abandon rate %.3f",
        len(report.campaigns),
        report.overall_abandon_rate,
    )


if __name__ == "__main__":  # pragma: no cover
    asyncio.run(main())
