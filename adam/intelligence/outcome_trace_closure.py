# =============================================================================
# Outcome → DecisionTrace closure writer — Spine #6 closure loop
# Location: adam/intelligence/outcome_trace_closure.py
# =============================================================================
"""Write the (:ConversionEdge)-[:RESOLVED]->(:DecisionTrace) closure
in Neo4j when an outcome arrives.

Closes audit Tier 1 #4 (closure loop): outcomes were never linked
back to their originating DecisionTrace. The honest tag in
``adam/intelligence/decision_trace_neo4j.py:78-80`` named this
exact slice as the missing successor:

    "(:ConversionEdge) -[:RESOLVED]-> (:DecisionTrace) edge —
     written by the OutcomeHandler when an impression resolves to
     a conversion. Its own slice (depends on outcome event path)."

Per directive line 248: "Long-term archival in Neo4j as
``DecisionTrace`` nodes linked to the ``User``, the
``ConversionEdge`` (when the impression resolves), and the
``Mechanism``." This module writes the ConversionEdge node + the
RESOLVED edge so that:

  * The DR renderer's "what happened to this impression" provenance
    layer can answer the question.
  * The OPE post-outcome update (sibling Slice 6) can join the
    served propensity to the resolved reward.
  * Cypher queries "for this user, what fraction of their served
    impressions resolved" become first-class.

WHY THIS EXISTS
---------------

Without this writer, the directive's "every served impression
contributes to evaluating every arm" multiplier (line 244) cannot
fire: OPE estimators need the joined (decision, outcome) pair, and
that join lives nowhere — the decision side persists via Slice 17d
(Spine #5 dual-eval emission) but the outcome side never closes.

THE PRIMITIVE
-------------

  * ``CONVERSION_EDGE_NODE_LABEL = "ConversionEdge"`` — directive's
    canonical name (line 248). Distinct from the existing :Outcome
    label used by causal_adjudicator (which serves the deviation /
    recommendation flow); the two label namespaces don't collide.
  * ``RESOLVED_REL = "RESOLVED"`` — per directive's exact wording.
  * ``write_outcome_trace_closure(decision_id, outcome_type,
    outcome_value, ...)`` — async writer. Idempotent (MERGE on
    conversion_edge_id derived from decision_id).
  * ``ConversionEdgeWriteResult`` — frozen dataclass: written /
    skipped flags + reason.

DISCIPLINE (B3-LUXY a/b/c/d)
----------------------------

(a) Citations: directive Section 3 line 248 (long-term archival
    schema); directive Section 5.2 Step 8 line 709 ("Decision-trace
    closure: link the trace to the outcome"); audit 2026-05-01
    Tier 1 #4. The :Outcome / :Deviation pattern in
    ``causal_adjudicator.py`` is the schema-style precedent (idempotent
    MERGE on id, scalar properties + timestamp, single relationship
    edge).

(b) Tests pin: writer issues the expected Cypher; idempotent re-run
    on same decision_id; missing driver → soft-fail to skipped;
    driver exception → soft-fail to skipped + warn; conversion_edge_id
    deterministic from decision_id (replays produce same node);
    outcome_type / outcome_value preserved on the node;
    timestamp populated; ConversionEdgeWriteResult is frozen.

(c) calibration_pending=False — schema is declarative, no
    pilot-data-dependent constants.

(d) Honest tags — what is NOT in this slice (named successors):

    * Buyer attribution edge (``(b:User)-[:GENERATED]->(c:ConversionEdge)``)
      — SHIPPED in Slice 15 (2026-05-02 handoff). The writer now
      accepts ``user_id`` and OPTIONAL-MERGEs ``(u:User)-[:GENERATED]
      ->(c:ConversionEdge)`` when the outcome handler supplies it.
      Empty user_id → User edge skipped (anonymous outcomes).
    * (:ConversionEdge)-[:VIA_MECHANISM]->(:Mechanism) edge — SHIPPED
      in Slice 15. The writer now accepts ``chosen_mechanism`` and
      OPTIONAL-MERGEs ``(c:ConversionEdge)-[:VIA_MECHANISM]->(m:
      Mechanism)`` when supplied. Empty chosen_mechanism → Mechanism
      edge skipped.
    * Outcome-driven update of DecisionTrace.resolved_at_ts +
      outcome_type fields (would mutate the trace; for v0.1 the
      ConversionEdge node carries the resolution data and the
      DecisionTrace stays immutable per emission contract). Sibling
      slice if mutation discipline allows.
    * Cypher index migration on :ConversionEdge(decision_id) —
      operational migration; should run before this writer hits
      scale (LUXY pre-pilot N is small enough that scan-cost is
      negligible).
"""

from __future__ import annotations

import hashlib
import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


# =============================================================================
# Schema constants (per directive line 248)
# =============================================================================

CONVERSION_EDGE_NODE_LABEL: str = "ConversionEdge"
DECISION_TRACE_NODE_LABEL: str = "DecisionTrace"
USER_NODE_LABEL: str = "User"
MECHANISM_NODE_LABEL: str = "Mechanism"
RESOLVED_REL: str = "RESOLVED"
GENERATED_REL: str = "GENERATED"
VIA_MECHANISM_REL: str = "VIA_MECHANISM"


# =============================================================================
# Result
# =============================================================================


@dataclass(frozen=True)
class ConversionEdgeWriteResult:
    """Outcome of a closure write attempt.

    ``written``: True iff the Cypher MERGE+edge succeeded.
    ``conversion_edge_id``: the deterministic id we computed (always
        populated for traceability — caller can correlate logs even
        when written=False).
    ``skipped``: True when the writer short-circuited (e.g., no
        driver, no decision_id). Distinct from written=False with
        an exception (which is a real failure).
    ``reason``: short label for diagnostic / dashboard surfaces.
        Examples: "written", "no_driver", "no_decision_id",
        "neo4j_exception", "trace_not_found".
    """

    written: bool
    conversion_edge_id: str
    skipped: bool
    reason: str


# =============================================================================
# Deterministic id
# =============================================================================


def conversion_edge_id_for(decision_id: str) -> str:
    """Deterministic id for a ConversionEdge given the decision it resolves.

    1:1 with decision_id by design — a decision can resolve to AT MOST
    one ConversionEdge. The hash form is stable across processes /
    restarts and short enough for log lines / Cypher params.
    """
    h = hashlib.sha256(decision_id.encode("utf-8")).hexdigest()[:16]
    return f"ce:{h}"


# =============================================================================
# Cypher
# =============================================================================


_CLOSURE_CYPHER: str = (
    f"MERGE (c:{CONVERSION_EDGE_NODE_LABEL} "
    "{conversion_edge_id: $conversion_edge_id}) "
    "SET c.decision_id = $decision_id, "
    "    c.outcome_type = $outcome_type, "
    "    c.outcome_value = $outcome_value, "
    "    c.observed_at_ts = $observed_at_ts, "
    "    c.signed_reward = $signed_reward "
    "WITH c "
    f"MATCH (d:{DECISION_TRACE_NODE_LABEL} "
    "{decision_id: $decision_id}) "
    f"MERGE (c)-[:{RESOLVED_REL}]->(d) "
    "RETURN c.conversion_edge_id AS id"
)


# Slice 15: User attribution + VIA_MECHANISM. Run AFTER the base
# closure so the ConversionEdge node already exists. We use OPTIONAL
# MATCH on the conversion edge to be defensive — if the base writer
# soft-failed (no driver / exception), this Cypher is a no-op.
_USER_ATTRIBUTION_CYPHER: str = (
    f"MATCH (c:{CONVERSION_EDGE_NODE_LABEL} "
    "{conversion_edge_id: $conversion_edge_id}) "
    f"MERGE (u:{USER_NODE_LABEL} {{user_id: $user_id}}) "
    f"MERGE (u)-[:{GENERATED_REL}]->(c)"
)

_VIA_MECHANISM_CYPHER: str = (
    f"MATCH (c:{CONVERSION_EDGE_NODE_LABEL} "
    "{conversion_edge_id: $conversion_edge_id}) "
    f"MERGE (m:{MECHANISM_NODE_LABEL} {{name: $mechanism_name}}) "
    f"MERGE (c)-[:{VIA_MECHANISM_REL}]->(m)"
)


# =============================================================================
# Writer
# =============================================================================


async def write_outcome_trace_closure(
    decision_id: str,
    outcome_type: str,
    outcome_value: float,
    *,
    signed_reward: Optional[float] = None,
    neo4j_client: Optional[Any] = None,
    observed_at_ts: Optional[float] = None,
    user_id: Optional[str] = None,
    chosen_mechanism: Optional[str] = None,
) -> ConversionEdgeWriteResult:
    """Write the (:ConversionEdge)-[:RESOLVED]->(:DecisionTrace) closure.

    Args:
        decision_id: id of the originating cascade decision (the same
            decision_id Spine #6 emits onto DecisionTrace).
        outcome_type: outcome class string (per Spine #11 vocabulary).
        outcome_value: 0-1 outcome strength.
        signed_reward: signed-reward (positive/negative direction +
            magnitude per Foundation rule 11). Optional — when None,
            the property is left at 0.0 on the node and a sibling slice
            can backfill if needed.
        neo4j_client: ``Neo4jClient`` (defaults to singleton via
            ``get_neo4j_client()``). When the client is unavailable or
            not connected, soft-fail to skipped.
        observed_at_ts: outcome observation timestamp (epoch seconds).
            Defaults to now.

    Returns:
        ``ConversionEdgeWriteResult``. Soft-fail discipline: writer
        never raises into the caller — the outcome processing path
        must NEVER block on logging.

    Idempotency: MERGE on conversion_edge_id (= deterministic
    SHA-256 of decision_id) means re-runs update scalar properties
    without duplicating nodes. The (:ConversionEdge)-[:RESOLVED]->(:
    DecisionTrace) edge is also MERGE'd, so re-runs are no-ops on
    the relationship.

    Trace-not-found semantic: when no :DecisionTrace node exists
    yet for this decision_id (Task 38 hot-cache drain may not have
    run, or the decision was made on a different process), the
    ConversionEdge is still written but the :RESOLVED edge cannot
    be created. We log INFO and return reason="trace_not_found".
    The conversion_edge_id is stable so a sibling slice / re-run
    after the trace lands can complete the join.
    """
    edge_id = conversion_edge_id_for(decision_id)

    if not decision_id:
        return ConversionEdgeWriteResult(
            written=False,
            conversion_edge_id=edge_id,
            skipped=True,
            reason="no_decision_id",
        )

    # Resolve client
    client = neo4j_client
    if client is None:
        try:
            from adam.infrastructure.neo4j.client import get_neo4j_client
            client = get_neo4j_client()
        except Exception as exc:
            logger.debug(
                "outcome_trace_closure: client import failed: %s", exc,
            )
            return ConversionEdgeWriteResult(
                written=False,
                conversion_edge_id=edge_id,
                skipped=True,
                reason="no_driver",
            )

    if client is None or not getattr(client, "is_connected", False):
        return ConversionEdgeWriteResult(
            written=False,
            conversion_edge_id=edge_id,
            skipped=True,
            reason="no_driver",
        )

    ts = observed_at_ts if observed_at_ts is not None else time.time()

    params: Dict[str, Any] = {
        "conversion_edge_id": edge_id,
        "decision_id": decision_id,
        "outcome_type": outcome_type,
        "outcome_value": float(outcome_value),
        "observed_at_ts": float(ts),
        "signed_reward": (
            float(signed_reward) if signed_reward is not None else 0.0
        ),
    }

    closure_reason = "written"
    try:
        async with await client.session() as session:
            result = await session.run(_CLOSURE_CYPHER, **params)
            record = await result.single()
            if record is None:
                # MERGE created the ConversionEdge node but the
                # subsequent MATCH on :DecisionTrace returned no
                # rows → trace not yet archived. Edge node still
                # written for backfill on the resolved-by-replay
                # path. Honest signal in reason.
                closure_reason = "trace_not_found"

            # Slice 15 — User attribution + VIA_MECHANISM.
            # OPTIONAL extras: only fire when the caller supplied the
            # corresponding identifiers. Each is independently soft-
            # failed (a User-edge failure must not block Mechanism-edge
            # write or vice versa).
            if user_id:
                try:
                    await session.run(
                        _USER_ATTRIBUTION_CYPHER,
                        conversion_edge_id=edge_id,
                        user_id=user_id,
                    )
                except Exception as user_exc:
                    logger.warning(
                        "outcome_trace_closure: user attribution edge "
                        "failed for decision_id=%s user_id=%s: %s",
                        decision_id, user_id, user_exc,
                    )
            if chosen_mechanism:
                try:
                    await session.run(
                        _VIA_MECHANISM_CYPHER,
                        conversion_edge_id=edge_id,
                        mechanism_name=chosen_mechanism,
                    )
                except Exception as mech_exc:
                    logger.warning(
                        "outcome_trace_closure: VIA_MECHANISM edge "
                        "failed for decision_id=%s mechanism=%s: %s",
                        decision_id, chosen_mechanism, mech_exc,
                    )
    except Exception as exc:
        logger.warning(
            "outcome_trace_closure: write failed for decision_id=%s: %s",
            decision_id, exc,
        )
        return ConversionEdgeWriteResult(
            written=False,
            conversion_edge_id=edge_id,
            skipped=False,
            reason="neo4j_exception",
        )

    return ConversionEdgeWriteResult(
        written=True,
        conversion_edge_id=edge_id,
        skipped=False,
        reason=closure_reason,
    )
