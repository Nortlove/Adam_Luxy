# =============================================================================
# AdOutcome writer — populates the M4-schema OPE loader's input
# Location: adam/intelligence/ad_outcome_persist.py
# =============================================================================
"""Write the :AdOutcome node + :DecisionContext-[:HAD_OUTCOME]->:AdOutcome
edge that ``ope.load_ope_samples_from_neo4j`` reads.

Closes audit Tier 1 #5 (data-side): the OPE loader at
``adam/intelligence/ope.py:469`` has the read-side query
(``MATCH (dc:DecisionContext)-[:HAD_OUTCOME]->(o:AdOutcome)``) but
no production code writes the outcome side. ``decision_cache.
_async_persist_to_neo4j`` MERGE's :DecisionContext on every cascade
decision, so the decision side is populated. The outcome side is
the missing producer.

Slice 5 already wrote :ConversionEdge for the DR provenance layer.
This slice writes :AdOutcome / :HAD_OUTCOME for the OPE pipeline.
The two writers serve different consumers and use different node
labels — the schemas don't collide:

    Slice 5: (:ConversionEdge)-[:RESOLVED]->(:DecisionTrace)
             — DR renderer "what happened to this impression" + Spine
             #6 propensity-trace closure
    Slice 6: (:DecisionContext)-[:HAD_OUTCOME]->(:AdOutcome)
             — OPE estimators (IPS/DR/SNIPS) consume the
             (propensity, action, reward) join

WHY THIS EXISTS
---------------

Without :AdOutcome rows, ``ope.load_ope_samples_from_neo4j`` returns
empty list, and the directive's "every served impression contributes
to evaluating every arm via inverse-propensity-weighted off-policy
estimation" multiplier (line 244, ~3-5x effective sample size at
no marginal infrastructure cost) cannot fire. This is the data-side
producer for Spine #6's off-policy evaluator (directive line 710
Step 9).

THE PRIMITIVE
-------------

  * ``write_ad_outcome(decision_id, outcome_type, outcome_value, ...)``
    — async writer. Idempotent (MERGE on outcome_id derived from
    decision_id).
  * ``AdOutcomeWriteResult`` — frozen dataclass: written / skipped
    flags + reason.

DISCIPLINE (B3-LUXY a/b/c/d)
----------------------------

(a) Citations: directive Section 5.2 Step 9 line 710 ("Off-policy
    evaluator update"); ope.py:469 (loader's expected schema);
    existing :AdOutcome MERGE pattern in ``gradient_bridge/service.py:
    974-988`` (the dead-code precedent that establishes the schema
    we're now actually writing); audit 2026-05-01 Tier 1 #5.

(b) Tests pin: writer issues expected Cypher; idempotent re-run on
    same decision_id; missing driver → soft-fail to skipped;
    driver exception → soft-fail to skipped + warn; outcome_id
    deterministic from decision_id; outcome_type / outcome_value /
    observed_at preserved on the node; HAD_OUTCOME edge MERGE'd;
    AdOutcomeWriteResult is frozen; query references both
    DecisionContext and AdOutcome labels.

(c) calibration_pending=False — schema is declarative, mirrors the
    M4 schema the OPE loader already expects.

(d) Honest tags — what is NOT in this slice (named successors):

    * Outcome-keyed Cypher index migration on :AdOutcome(outcome_id) —
      operational migration; should run before scale.
    * Per-cohort outcome aggregation (depends on Spine #7 cohort
      discovery, BLOCKED on Loop B).
    * Cross-day :AdOutcome roll-up that matches the OPE daily
      estimator task's lookback window — sibling slice handled in
      the OPE task itself (it queries within window).
    * Schema-merge with Slice 5's :ConversionEdge — currently the
      two writers persist parallel rows (one for OPE, one for DR).
      A unified schema is a sibling slice once both consumers are
      stable enough to commit to one shape.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


# =============================================================================
# Schema constants (mirror ope.py:469 loader expectations)
# =============================================================================

DECISION_CONTEXT_NODE_LABEL: str = "DecisionContext"
AD_OUTCOME_NODE_LABEL: str = "AdOutcome"
HAD_OUTCOME_REL: str = "HAD_OUTCOME"


# =============================================================================
# Result
# =============================================================================


@dataclass(frozen=True)
class AdOutcomeWriteResult:
    """Outcome of an AdOutcome write attempt.

    ``written``: True iff Cypher MERGE+edge succeeded.
    ``outcome_id``: deterministic id (decision_id + '_outcome').
    ``skipped``: True when the writer short-circuited (no driver,
        no decision_id). Distinct from written=False with exception.
    ``reason``: short label. Examples: "written", "no_driver",
        "no_decision_id", "neo4j_exception", "context_not_found".
    """

    written: bool
    outcome_id: str
    skipped: bool
    reason: str


# =============================================================================
# Deterministic id
# =============================================================================


def outcome_id_for(decision_id: str) -> str:
    """Deterministic id matching the gradient_bridge precedent.

    Format: ``{decision_id}_outcome`` — matches the existing schema
    in gradient_bridge/service.py:977 so future consolidation (if
    that writer is ever resurrected) sees the same ids.
    """
    return f"{decision_id}_outcome"


# =============================================================================
# Cypher
# =============================================================================


_AD_OUTCOME_CYPHER: str = (
    f"MATCH (dc:{DECISION_CONTEXT_NODE_LABEL} "
    "{decision_id: $decision_id}) "
    f"MERGE (o:{AD_OUTCOME_NODE_LABEL} {{outcome_id: $outcome_id}}) "
    "SET o.outcome_type = $outcome_type, "
    "    o.outcome_value = $outcome_value, "
    "    o.observed_at_ts = $observed_at_ts, "
    "    o.signed_reward = $signed_reward "
    f"MERGE (dc)-[:{HAD_OUTCOME_REL}]->(o) "
    "RETURN o.outcome_id AS id"
)


# =============================================================================
# Writer
# =============================================================================


async def write_ad_outcome(
    decision_id: str,
    outcome_type: str,
    outcome_value: float,
    *,
    signed_reward: Optional[float] = None,
    neo4j_client: Optional[Any] = None,
    observed_at_ts: Optional[float] = None,
) -> AdOutcomeWriteResult:
    """Write the :AdOutcome node + :HAD_OUTCOME edge for OPE.

    Args:
        decision_id: id of the originating cascade decision.
        outcome_type: outcome class string (Spine #11 vocabulary).
        outcome_value: 0-1 outcome strength — directly consumed by
            ope.OPESample.reward.
        signed_reward: signed-reward (positive/negative direction +
            magnitude per Foundation rule 11). Optional — defaults
            to 0.0 on the node when absent.
        neo4j_client: ``Neo4jClient`` (defaults to singleton).
        observed_at_ts: outcome observation timestamp (epoch seconds).
            Defaults to now.

    Returns:
        ``AdOutcomeWriteResult``. Soft-fail discipline: writer never
        raises; outcome processing must NEVER block on logging.

    Idempotency: MERGE on outcome_id (deterministic from decision_id).
    Re-runs update scalar properties; HAD_OUTCOME edge MERGE'd so
    re-runs are no-ops on the relationship.

    Context-not-found semantic: when no :DecisionContext node exists
    for this decision_id (race condition with decision_cache async
    write, or decision was made on a different process and didn't
    persist), the entire write is skipped. Returns
    reason="context_not_found". Replay after the context lands will
    succeed.
    """
    oid = outcome_id_for(decision_id)

    if not decision_id:
        return AdOutcomeWriteResult(
            written=False,
            outcome_id=oid,
            skipped=True,
            reason="no_decision_id",
        )

    client = neo4j_client
    if client is None:
        try:
            from adam.infrastructure.neo4j.client import get_neo4j_client
            client = get_neo4j_client()
        except Exception as exc:
            logger.debug(
                "ad_outcome_persist: client import failed: %s", exc,
            )
            return AdOutcomeWriteResult(
                written=False,
                outcome_id=oid,
                skipped=True,
                reason="no_driver",
            )

    if client is None or not getattr(client, "is_connected", False):
        return AdOutcomeWriteResult(
            written=False,
            outcome_id=oid,
            skipped=True,
            reason="no_driver",
        )

    ts = observed_at_ts if observed_at_ts is not None else time.time()

    params: Dict[str, Any] = {
        "decision_id": decision_id,
        "outcome_id": oid,
        "outcome_type": outcome_type,
        "outcome_value": float(outcome_value),
        "observed_at_ts": float(ts),
        "signed_reward": (
            float(signed_reward) if signed_reward is not None else 0.0
        ),
    }

    try:
        async with await client.session() as session:
            result = await session.run(_AD_OUTCOME_CYPHER, **params)
            record = await result.single()
            if record is None:
                # MATCH on :DecisionContext returned no rows → context
                # not yet persisted. Honest signal — replay after the
                # decision_cache async write lands.
                return AdOutcomeWriteResult(
                    written=False,
                    outcome_id=oid,
                    skipped=False,
                    reason="context_not_found",
                )
    except Exception as exc:
        logger.warning(
            "ad_outcome_persist: write failed for decision_id=%s: %s",
            decision_id, exc,
        )
        return AdOutcomeWriteResult(
            written=False,
            outcome_id=oid,
            skipped=False,
            reason="neo4j_exception",
        )

    return AdOutcomeWriteResult(
        written=True,
        outcome_id=oid,
        skipped=False,
        reason="written",
    )
