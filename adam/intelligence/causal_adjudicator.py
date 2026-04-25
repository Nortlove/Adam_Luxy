"""Causal Adjudicator — Loop A → Loop B cross-pollination.

Reads Deviations whose horizon window has closed and evaluates the
observed campaign outcome against the system_counterfactual recorded
at decision time. Writes adjudication_status='adjudicated' on the
Deviation, creates an Outcome node with the observation, and on a
system_right outcome generates a WhyLibraryEntry that becomes a
pre-emptive defensive warning the next time a similar pattern fires.

Per HMT Foundation §9.2-§9.4. v1 makes a directional adjudication —
real causal-inference would require holdouts. The directional signal
is honest given the constraints; the WhyLibraryEntry's
warning_posterior_observations counter starts at 1 and only
strengthens with corroboration.
"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)


# =============================================================================
# Result types
# =============================================================================


AdjudicationOutcome = str  # "user_right" | "system_right" | "indeterminate"


@dataclass(frozen=True)
class AdjudicationResult:
    deviation_id: str
    recommendation_id: str
    outcome: AdjudicationOutcome
    rationale: str
    why_library_entry_id: Optional[str] = None
    metric_observed: Optional[str] = None
    metric_value_before: Optional[float] = None
    metric_value_after: Optional[float] = None


@dataclass(frozen=True)
class AdjudicationBatch:
    adjudicated: list[AdjudicationResult]
    skipped_too_early: int
    skipped_no_data: int
    skipped_already_done: int


# =============================================================================
# Bias-class inference from rationale_class
# =============================================================================


_BIAS_CLASS_DEFAULTS = {
    "idiosyncratic": "preference",
    "missing_context": "underspecified_data",
    "model_wrong": "model_disagreement",
}


def _bias_class_for(rationale_class: Optional[str]) -> str:
    if not rationale_class:
        return "unspecified"
    return _BIAS_CLASS_DEFAULTS.get(rationale_class, rationale_class)


# =============================================================================
# Per-recommendation-type evaluation
# =============================================================================


@dataclass(frozen=True)
class _Evaluation:
    outcome: AdjudicationOutcome
    rationale: str
    metric: Optional[str]
    before: Optional[float]
    after: Optional[float]


def _evaluate_pause_campaign(
    user_choice: Optional[str],
    campaign_then: dict[str, Any],
    campaign_now: dict[str, Any],
    advertiser_avg_cpa_now: Optional[float],
) -> _Evaluation:
    """If the user chose 'continue' or 'diagnose' instead of 'pause',
    check whether the campaign's CPA recovered."""
    cpa_then = campaign_then.get("cpa")
    cpa_now = campaign_now.get("cpa")

    if cpa_now is None:
        return _Evaluation(
            outcome="indeterminate",
            rationale="Campaign has no current CPA observation (paused, no conversions, etc.).",
            metric="campaign_cpa",
            before=cpa_then,
            after=None,
        )

    if user_choice == "pause":
        # User accepted preferred. No deviation to adjudicate against;
        # the dashboard typically wouldn't even create a Deviation here.
        return _Evaluation(
            outcome="indeterminate",
            rationale="User chose system's preferred (pause). No deviation to adjudicate.",
            metric="campaign_cpa",
            before=cpa_then,
            after=cpa_now,
        )

    # User kept running (or diagnosed without pausing). Did CPA improve?
    if cpa_then is not None and cpa_now < cpa_then * 0.7:
        return _Evaluation(
            outcome="user_right",
            rationale=(
                f"CPA improved from ${cpa_then:,.0f} to ${cpa_now:,.0f} "
                f"({(1 - cpa_now / cpa_then) * 100:.0f}% better). User was right "
                f"to keep the campaign running — pausing would have killed a "
                f"recovery."
            ),
            metric="campaign_cpa",
            before=cpa_then,
            after=cpa_now,
        )

    if (
        advertiser_avg_cpa_now is not None
        and advertiser_avg_cpa_now > 0
        and cpa_now / advertiser_avg_cpa_now >= 3.0
    ):
        return _Evaluation(
            outcome="system_right",
            rationale=(
                f"CPA remained at ${cpa_now:,.0f}, still "
                f"{cpa_now / advertiser_avg_cpa_now:.1f}× advertiser average. "
                f"The campaign did not recover — system was right to "
                f"recommend pausing."
            ),
            metric="campaign_cpa",
            before=cpa_then,
            after=cpa_now,
        )

    return _Evaluation(
        outcome="indeterminate",
        rationale=(
            f"CPA moved from ${cpa_then or 0:,.0f} to ${cpa_now:,.0f} — neither "
            f"a clear recovery nor a continued failure. Insufficient signal to rule."
        ),
        metric="campaign_cpa",
        before=cpa_then,
        after=cpa_now,
    )


def _evaluate_zero_conversions(
    user_choice: Optional[str],
    campaign_then: dict[str, Any],
    campaign_now: dict[str, Any],
) -> _Evaluation:
    """The recommendation was 'diagnose + mechanism shift' for a
    campaign with zero conversions and meaningful spend. Did
    conversions arrive?"""
    convs_now = campaign_now.get("conversions") or 0

    if user_choice == "diagnose_and_shift":
        return _Evaluation(
            outcome="indeterminate",
            rationale="User accepted preferred. No deviation to adjudicate.",
            metric="conversions",
            before=campaign_then.get("conversions"),
            after=convs_now,
        )

    if convs_now > 0:
        return _Evaluation(
            outcome="user_right",
            rationale=(
                f"Conversions arrived ({convs_now:,}). The user was right to "
                f"keep the campaign or take a different action — the issue "
                f"resolved itself or the user's intervention worked."
            ),
            metric="conversions",
            before=campaign_then.get("conversions"),
            after=convs_now,
        )

    return _Evaluation(
        outcome="system_right",
        rationale=(
            f"Still 0 conversions. The system was right to flag this campaign "
            f"as needing diagnostic + mechanism shift; the alternative the "
            f"user chose did not produce conversions."
        ),
        metric="conversions",
        before=campaign_then.get("conversions"),
        after=convs_now,
    )


def _evaluate_low_ctr(
    user_choice: Optional[str],
    campaign_then: dict[str, Any],
    campaign_now: dict[str, Any],
) -> _Evaluation:
    """Recommendation was creative rotation. Did CTR move?"""
    ctr_then = campaign_then.get("ctr")
    ctr_now = campaign_now.get("ctr")
    if ctr_now is None:
        return _Evaluation(
            outcome="indeterminate",
            rationale="No current CTR observation.",
            metric="ctr",
            before=ctr_then,
            after=None,
        )

    if user_choice == "rotate_creative":
        return _Evaluation(
            outcome="indeterminate",
            rationale="User accepted preferred. No deviation to adjudicate.",
            metric="ctr",
            before=ctr_then,
            after=ctr_now,
        )

    # User chose audience_narrow / both / something else.
    if ctr_then is not None and ctr_now > ctr_then * 1.5:
        return _Evaluation(
            outcome="user_right",
            rationale=(
                f"CTR improved from {ctr_then * 100:.3f}% to {ctr_now * 100:.3f}% "
                f"({(ctr_now / ctr_then - 1) * 100:.0f}% better). User's "
                f"alternative path worked."
            ),
            metric="ctr",
            before=ctr_then,
            after=ctr_now,
        )

    if ctr_now < 0.001:
        return _Evaluation(
            outcome="system_right",
            rationale=(
                f"CTR is still {ctr_now * 100:.3f}% (below the 0.1% floor). "
                f"The user's alternative did not lift CTR — system was "
                f"right to recommend creative rotation."
            ),
            metric="ctr",
            before=ctr_then,
            after=ctr_now,
        )

    return _Evaluation(
        outcome="indeterminate",
        rationale="CTR moved but not enough to clearly validate either side.",
        metric="ctr",
        before=ctr_then,
        after=ctr_now,
    )


_EVALUATORS = {
    "pause_campaign": _evaluate_pause_campaign,
    "mechanism_shift": _evaluate_zero_conversions,
    "creative_rotate": _evaluate_low_ctr,
}


def _evaluate_client_recommendation(
    deviation: dict[str, Any],
    recommendation: dict[str, Any],
) -> _Evaluation:
    """Adjudicate a client-facing recommendation Deviation (Front-end A).

    Client recommendations (Recommendation.kind = 'client') propose
    actions to an advertiser — shift budget to a segment, separate
    messaging for a second segment, etc. When the client declines, the
    action is not taken, which means there is no natural before/after
    for the system to observe against.

    Full adjudication of these deviations requires the outcome-
    observation wiring flagged as Structural Weakness #4 (2026-04-23
    review): a mechanism that measures whether the projected impact
    named by the recommendation actually materialized at horizon
    expiry, AND whether it would have materialized under the
    counterfactual action. Until that wiring ships, the adjudicator
    returns *honest indeterminate* — NOT silent skip. The Deviation
    still gets marked adjudicated, an Outcome node still records the
    pending-infrastructure dependency, and the record is available for
    re-adjudication when the outcome-observation layer lands.

    This is the correct v1 behavior. Forging a before/after comparison
    from StackAdapt totals here would reintroduce exactly the A5
    correlational drift the platform is defined against.
    """
    user_choice = deviation.get("user_choice", "")
    if user_choice == "acknowledge":
        # Client accepted the system's preferred action. Not a
        # deviation; the dashboard shouldn't have created one. If it
        # did (idempotency edge case), mark indeterminate with the
        # reason.
        return _Evaluation(
            outcome="indeterminate",
            rationale=(
                "Client acknowledged the recommendation — no deviation to "
                "adjudicate against."
            ),
            metric=None,
            before=None,
            after=None,
        )

    # kind='client' + user_choice='decline' is the typical case.
    # Outcome-observation wiring for client-rec projected impact is
    # Structural Weakness #4 (pending). Record indeterminate honestly.
    headline = recommendation.get("title") or "(no headline)"
    feedback = deviation.get("stated_rationale") or ""
    feedback_suffix = (
        f" Client feedback: \"{feedback}\"." if feedback else ""
    )
    return _Evaluation(
        outcome="indeterminate",
        rationale=(
            f"Client declined: {headline}. "
            "Directional adjudication of client recommendations requires "
            "outcome-observation wiring for projected-impact claims "
            "(Structural Weakness #4, 2026-04-23 review). Until that "
            "lands, declines are recorded for later re-adjudication; "
            "no user_right / system_right determination is made."
            f"{feedback_suffix}"
        ),
        metric=None,
        before=None,
        after=None,
    )


# =============================================================================
# Why Library generation
# =============================================================================


async def _persist_why_library_entry(
    session: Any,
    deviation: dict[str, Any],
    recommendation: dict[str, Any],
    evaluation: _Evaluation,
    user_id: str,
) -> str:
    """Create a WhyLibraryEntry for a system_right adjudication."""
    entry_id = f"why:{uuid.uuid4()}"
    rec_type = recommendation.get("type", "unspecified")
    bias_class = _bias_class_for(deviation.get("rationale_class"))
    trigger_pattern = (
        f"{rec_type} where user chose '{deviation.get('user_choice') or '(rejected)'}' "
        f"over '{deviation.get('system_choice')}'"
    )
    countermeasure = (
        f"In a similar situation: {evaluation.rationale} "
        f"Heads up — the system recommends {deviation.get('system_choice')}; "
        f"deviating in this case has historically not produced the expected "
        f"recovery."
    )
    await session.run(
        """
        CREATE (wl:WhyLibraryEntry {
          id: $id,
          trigger_pattern: $trigger_pattern,
          bias_class: $bias_class,
          evidence_strength: 0.5,
          scope: 'user',
          scope_id: $user_id,
          countermeasure: $countermeasure,
          supporting_deviation_ids: $supporting,
          warning_posterior_mean: 0.5,
          warning_posterior_observations: 1,
          created_at: $now,
          last_validated_at: $now,
          retired_at: null
        })
        """,
        id=entry_id,
        trigger_pattern=trigger_pattern,
        bias_class=bias_class,
        user_id=user_id,
        countermeasure=countermeasure,
        supporting=[deviation["id"]],
        now=datetime.now(timezone.utc),
    )
    return entry_id


# =============================================================================
# Per-deviation adjudication
# =============================================================================


async def _adjudicate_one(
    session: Any,
    deviation: dict[str, Any],
    user_id: str,
) -> Optional[AdjudicationResult]:
    rec_id = deviation["recommendation_id"]
    rec_result = await session.run(
        "MATCH (r:Recommendation {id: $id}) RETURN r",
        id=rec_id,
    )
    rec_record = await rec_result.single()
    if rec_record is None:
        logger.info(
            "Skipping adjudication for %s — no Recommendation found",
            deviation.get("id"),
        )
        return None
    recommendation = dict(rec_record["r"])

    # Dispatch: client recommendations (kind='client' from Front-end A)
    # have their own evaluator path because their shape differs from the
    # internal-type-based recs (no alternatives, no UncertaintyBreakdown,
    # natural-language rationale only). Check kind before the type-based
    # dispatch so client recs don't fall through to the "no evaluator
    # registered" silent-skip path.
    rec_kind = recommendation.get("kind", "")
    rec_type = recommendation.get("type", "")

    if rec_kind == "client":
        client_evaluation = _evaluate_client_recommendation(
            deviation, recommendation,
        )
        # Persist adjudication directly for client recs (bypasses the
        # internal type-dispatch evaluator + StackAdapt snapshot path,
        # since client-rec adjudication doesn't compare campaign
        # totals — it records the pending-infrastructure dependency
        # honestly).
        now = datetime.now(timezone.utc)
        await session.run(
            """
            MATCH (d:Deviation {id: $id})
            SET d.adjudication_status = 'adjudicated',
                d.adjudication_outcome = $outcome,
                d.adjudicated_at = $now
            """,
            id=deviation["id"],
            outcome=client_evaluation.outcome,
            now=now,
        )
        outcome_id = f"outcome:{uuid.uuid4()}"
        await session.run(
            """
            MATCH (d:Deviation {id: $deviation_id})
            CREATE (o:Outcome {
              id: $outcome_id,
              observation: $observation,
              horizon_ends_at: $now,
              observed_at: $now,
              attributed_to: 'pending_outcome_observation_infrastructure',
              confidence: 0.0
            })
            MERGE (d)-[:RESOLVED_AS]->(o)
            """,
            deviation_id=deviation["id"],
            outcome_id=outcome_id,
            observation=json.dumps(
                {
                    "metric": None,
                    "before": None,
                    "after": None,
                    "rationale": client_evaluation.rationale,
                    "pending_weakness": "structural_weakness_4",
                }
            ),
            now=now,
        )
        # No WhyLibraryEntry — indeterminate outcomes don't generate
        # defensive warnings.
        return AdjudicationResult(
            deviation_id=deviation["id"],
            recommendation_id=rec_id,
            outcome=client_evaluation.outcome,
            rationale=client_evaluation.rationale,
        )

    evaluator = _EVALUATORS.get(rec_type)
    if evaluator is None:
        return AdjudicationResult(
            deviation_id=deviation["id"],
            recommendation_id=rec_id,
            outcome="indeterminate",
            rationale=f"No evaluator registered for recommendation type '{rec_type}'.",
        )

    # Pull current campaign state from live StackAdapt.
    from adam.api.dashboard.service import fetch_stackadapt_summary

    summary = await fetch_stackadapt_summary()
    if summary.source != "live":
        return AdjudicationResult(
            deviation_id=deviation["id"],
            recommendation_id=rec_id,
            outcome="indeterminate",
            rationale="StackAdapt unreachable — cannot observe outcome.",
        )

    campaign_id = recommendation.get("campaign_id")
    campaign_now = next(
        (c for c in summary.campaigns if c.id == campaign_id), None,
    )
    if campaign_now is None:
        return AdjudicationResult(
            deviation_id=deviation["id"],
            recommendation_id=rec_id,
            outcome="indeterminate",
            rationale=(
                f"Campaign {campaign_id} not present in current StackAdapt "
                f"snapshot (paused, deleted, or no longer in scope)."
            ),
        )

    # The "then" snapshot is approximated from the stored evidence_json.
    evidence = json.loads(recommendation.get("evidence_json", "{}"))
    confident_facts = " ".join(
        c.get("claim", "") for c in evidence.get("confident", [])
    )
    advertiser_avg_cpa_now = (
        summary.spend_usd / summary.conversions
        if summary.conversions > 0
        else None
    )

    campaign_then: dict[str, Any] = {}
    # Heuristic extraction: parse known patterns from the confident facts.
    # Future: store a structured snapshot at decision time.
    import re

    cpa_match = re.search(r"CPA is \$?([\d,]+)", confident_facts)
    if cpa_match:
        campaign_then["cpa"] = float(cpa_match.group(1).replace(",", ""))
    if "0 conversions" in confident_facts.lower():
        campaign_then["conversions"] = 0
    ctr_match = re.search(r"CTR is ([\d.]+)%", confident_facts)
    if ctr_match:
        campaign_then["ctr"] = float(ctr_match.group(1)) / 100

    campaign_now_dict = {
        "cpa": (
            campaign_now.spend_usd / campaign_now.conversions
            if campaign_now.conversions > 0
            else None
        ),
        "ctr": campaign_now.ctr,
        "conversions": campaign_now.conversions,
    }

    # Evaluator dispatch (varies by signature).
    if rec_type == "pause_campaign":
        evaluation = _evaluate_pause_campaign(
            user_choice=deviation.get("user_choice"),
            campaign_then=campaign_then,
            campaign_now=campaign_now_dict,
            advertiser_avg_cpa_now=advertiser_avg_cpa_now,
        )
    elif rec_type == "mechanism_shift":
        evaluation = _evaluate_zero_conversions(
            user_choice=deviation.get("user_choice"),
            campaign_then=campaign_then,
            campaign_now=campaign_now_dict,
        )
    else:  # creative_rotate
        evaluation = _evaluate_low_ctr(
            user_choice=deviation.get("user_choice"),
            campaign_then=campaign_then,
            campaign_now=campaign_now_dict,
        )

    # Persist adjudication result.
    now = datetime.now(timezone.utc)
    await session.run(
        """
        MATCH (d:Deviation {id: $id})
        SET d.adjudication_status = 'adjudicated',
            d.adjudication_outcome = $outcome,
            d.adjudicated_at = $now
        """,
        id=deviation["id"],
        outcome=evaluation.outcome,
        now=now,
    )

    outcome_id = f"outcome:{uuid.uuid4()}"
    await session.run(
        """
        MATCH (d:Deviation {id: $deviation_id})
        CREATE (o:Outcome {
          id: $outcome_id,
          observation: $observation,
          horizon_ends_at: $now,
          observed_at: $now,
          attributed_to: $attributed_to,
          confidence: $confidence
        })
        MERGE (d)-[:RESOLVED_AS]->(o)
        """,
        deviation_id=deviation["id"],
        outcome_id=outcome_id,
        observation=json.dumps(
            {
                "metric": evaluation.metric,
                "before": evaluation.before,
                "after": evaluation.after,
                "rationale": evaluation.rationale,
            }
        ),
        now=now,
        attributed_to=(
            "user_choice"
            if evaluation.outcome == "user_right"
            else "system_choice"
            if evaluation.outcome == "system_right"
            else "confounded"
        ),
        confidence=0.6,  # v1 directional confidence; holdouts would push this up
    )

    why_id: Optional[str] = None
    if evaluation.outcome == "system_right":
        why_id = await _persist_why_library_entry(
            session, deviation, recommendation, evaluation, user_id,
        )

    return AdjudicationResult(
        deviation_id=deviation["id"],
        recommendation_id=rec_id,
        outcome=evaluation.outcome,
        rationale=evaluation.rationale,
        why_library_entry_id=why_id,
        metric_observed=evaluation.metric,
        metric_value_before=evaluation.before,
        metric_value_after=evaluation.after,
    )


# =============================================================================
# Public API
# =============================================================================


_HORIZON_TO_DAYS = {
    "hours": 1.0,
    "days": 7.0,
    "weeks": 14.0,
    "months": 60.0,
}


async def adjudicate_deviation_with_operator_verdict(
    deviation_id: str,
    verdict: AdjudicationOutcome,
    user_id: str,
    rationale: Optional[str] = None,
) -> Optional[AdjudicationResult]:
    """Adjudicate a single deviation with the operator's explicit verdict.

    Used by the dashboard recommendations queue (slice D2 of the
    decision-gate unification work) when the operator decides on a
    source="horizon_adjudication" recommendation. The operator IS the
    verdict — their integrated read of realized outcome, business
    context, and signals the auto-evaluator may not have access to.

    Persistence is identical to the auto-adjudicator path
    (`_adjudicate_one`) modulo two differences:
      - The verdict comes from the operator argument, not from running
        a per-rec-type evaluator over campaign metrics. No StackAdapt
        snapshot is consulted.
      - The Outcome node carries `verdict_source='operator'` so future
        audits can distinguish operator-led from evaluator-led
        adjudications. Auto-adjudicator Outcomes implicitly have
        verdict_source absent / 'evaluator' (existing rows pre-date
        this field — Neo4j is schemaless; absence is honest).

    On `verdict='system_right'`, a WhyLibraryEntry is created via the
    existing `_persist_why_library_entry` helper (line 353) so the
    Why Library accumulates from operator-led adjudications the same
    way it does from auto-adjudicator system_right outcomes
    (causal_adjudicator.py:635-638). This keeps the defensive-
    reasoning catalog single-source regardless of verdict origin.

    Returns None when:
      - deviation not found by id
      - Neo4j unreachable
    Returns an AdjudicationResult flagged with rationale='Already
    adjudicated.' when the deviation has already been adjudicated;
    we do NOT double-write — operator double-clicks must be safe.
    """
    if verdict not in ("system_right", "user_right", "indeterminate"):
        raise ValueError(
            f"Invalid verdict {verdict!r}; expected one of "
            "system_right / user_right / indeterminate"
        )

    try:
        from adam.infrastructure.neo4j.client import get_neo4j_client
        client = get_neo4j_client()
        if not client.is_connected:
            return None
    except Exception as exc:
        logger.warning("Neo4j unavailable for operator verdict: %s", exc)
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
        if record is None:
            return None
        deviation = dict(record["d"])
        recommendation = dict(record["r"]) if record["r"] else {}

        # Idempotency: if already adjudicated, do not double-write.
        # Return a typed result so the caller knows the verdict landed
        # at some prior point (vs. confusing this with deviation-not-found).
        if deviation.get("adjudication_status") == "adjudicated":
            return AdjudicationResult(
                deviation_id=deviation_id,
                recommendation_id=deviation.get("recommendation_id", ""),
                outcome=deviation.get("adjudication_outcome", "indeterminate"),
                rationale="Already adjudicated.",
            )

        now = datetime.now(timezone.utc)
        await session.run(
            """
            MATCH (d:Deviation {id: $id})
            SET d.adjudication_status = 'adjudicated',
                d.adjudication_outcome = $verdict,
                d.adjudicated_at = $now
            """,
            id=deviation_id,
            verdict=verdict,
            now=now,
        )

        outcome_id = f"outcome:{uuid.uuid4()}"
        attributed_to = {
            "system_right": "system_choice",
            "user_right": "user_choice",
            "indeterminate": "confounded",
        }[verdict]
        observation_rationale = (
            rationale.strip() if rationale and rationale.strip()
            else f"Operator-led verdict: {verdict}"
        )
        await session.run(
            """
            MATCH (d:Deviation {id: $deviation_id})
            CREATE (o:Outcome {
              id: $outcome_id,
              observation: $observation,
              horizon_ends_at: $now,
              observed_at: $now,
              attributed_to: $attributed_to,
              confidence: $confidence,
              verdict_source: 'operator'
            })
            MERGE (d)-[:RESOLVED_AS]->(o)
            """,
            deviation_id=deviation_id,
            outcome_id=outcome_id,
            observation=json.dumps({
                "metric": None,
                "before": None,
                "after": None,
                "rationale": observation_rationale,
                "verdict_source": "operator",
            }),
            now=now,
            attributed_to=attributed_to,
            # Operator's confidence is their own integrated read; we don't
            # have a separate calibration channel to attach a numeric
            # confidence here. 1.0 reflects "this is the operator's stated
            # verdict", not "the system is 100% sure". Future calibration
            # work can replace this with operator-trust-level posteriors.
            confidence=1.0,
        )

        why_id: Optional[str] = None
        if verdict == "system_right":
            evaluation = _Evaluation(
                outcome="system_right",
                rationale=observation_rationale,
                metric=None,
                before=None,
                after=None,
            )
            why_id = await _persist_why_library_entry(
                session, deviation, recommendation, evaluation, user_id,
            )

        return AdjudicationResult(
            deviation_id=deviation_id,
            recommendation_id=deviation.get("recommendation_id", ""),
            outcome=verdict,
            rationale=observation_rationale,
            why_library_entry_id=why_id,
        )


async def adjudicate_ready_deviations(user_id: str) -> AdjudicationBatch:
    """Adjudicate every Deviation belonging to the user whose horizon
    window has closed and that has not yet been adjudicated.
    """
    adjudicated: list[AdjudicationResult] = []
    skipped_too_early = 0
    skipped_no_data = 0
    skipped_already_done = 0

    try:
        from adam.infrastructure.neo4j.client import get_neo4j_client

        client = get_neo4j_client()
        if not client.is_connected:
            return AdjudicationBatch(
                adjudicated=[],
                skipped_too_early=0,
                skipped_no_data=0,
                skipped_already_done=0,
            )

        async with await client.session() as session:
            result = await session.run(
                """
                MATCH (u:DialogueUser {id: $user_id})-[:DEVIATED]->(d:Deviation)
                RETURN d
                ORDER BY d.created_at ASC
                """,
                user_id=user_id,
            )
            now = datetime.now(timezone.utc)
            from datetime import timedelta

            async for record in result:
                d = dict(record["d"])
                d["id"] = d.get("id")  # ensure key
                horizon_class = d.get("horizon_class", "days")
                window_days = _HORIZON_TO_DAYS.get(horizon_class, 7.0)
                created_at = (
                    d["created_at"].to_native()
                    if hasattr(d["created_at"], "to_native")
                    else d["created_at"]
                )
                if d.get("adjudication_status") == "adjudicated":
                    skipped_already_done += 1
                    continue
                if created_at + timedelta(days=window_days) > now:
                    skipped_too_early += 1
                    continue

                outcome = await _adjudicate_one(session, d, user_id)
                if outcome is None:
                    skipped_no_data += 1
                else:
                    adjudicated.append(outcome)
    except Exception as exc:  # pragma: no cover
        logger.exception("adjudicate_ready_deviations failed: %s", exc)

    return AdjudicationBatch(
        adjudicated=adjudicated,
        skipped_too_early=skipped_too_early,
        skipped_no_data=skipped_no_data,
        skipped_already_done=skipped_already_done,
    )


async def fetch_why_library(user_id: str, limit: int = 100) -> list[dict[str, Any]]:
    """Read the user's WhyLibrary entries, most recent first."""
    entries: list[dict[str, Any]] = []
    try:
        from adam.infrastructure.neo4j.client import get_neo4j_client

        client = get_neo4j_client()
        if not client.is_connected:
            return []

        async with await client.session() as session:
            result = await session.run(
                """
                MATCH (wl:WhyLibraryEntry)
                WHERE wl.scope_id = $user_id
                  OR wl.scope IN ['platform', 'category']
                RETURN wl
                ORDER BY wl.created_at DESC
                LIMIT $limit
                """,
                user_id=user_id, limit=limit,
            )
            async for record in result:
                entry = dict(record["wl"])
                created_at = entry.get("created_at")
                if hasattr(created_at, "to_native"):
                    entry["created_at"] = created_at.to_native()
                entries.append(entry)
    except Exception as exc:  # pragma: no cover
        logger.warning("fetch_why_library failed: %s", exc)
    return entries
