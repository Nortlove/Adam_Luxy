# =============================================================================
# Slice 35 — StackAdapt shadow-mode bidder wire
# Location: adam/api/stackadapt/shadow_bidder.py
# =============================================================================
"""Shadow-mode bidder wire that consumes ``recommended_bid_value``
end-to-end through the StackAdapt service path.

Per the 2026-05-02 wrap-out greenlight:

  * Shadow mode — NO live bid writes.
  * Verify recommended_bid_value arrives intact.
  * Propensity-logged.
  * Round-trips through DecisionTrace.
  * Consumes via ``v3_interfaces.get_active_bid_composer()`` —
    when v3 Phase 1 work-stream 1.D registers an H∞-wrapped Kelly
    composer, this wire automatically consumes the wrapped value
    with zero changes.

Two reasons this lands during Phase A wrap-out per the greenlight:

  1. Criterion (ii) recovery path: if the 5-class head's first
     classifier underperforms the AUC threshold after the 20-URL
     bootstrap, round 2 active learning needs LIVE shadow-mode bid
     streams to sample uncertainty from. Building the wire now
     means round 2 can start the moment round 1 underperforms,
     with no infrastructure delay.

  2. v3 Phase 1 work-stream 1.D seam: building the wire under
     Phase A discipline (no live writes, full DecisionTrace
     round-trip) gives 1.D a clean substrate to wrap.
     Building it during 1.D itself means wire interface and
     H∞ wrapper are designed simultaneously — exactly the
     interface-instability problem Slice 24 caught for Slice
     7 / Slice 12 / washout.

DESIGN — WHY THE WIRE IS A CONSUMER, NOT A PRODUCER

The cascade ALREADY computes ``recommended_bid_value`` via
``v3_interfaces.get_active_bid_composer().compose_chosen()`` (Slice
24's seam). The shadow wire's job is to CONSUME that value (from
the service response or directly from the cascade output) and
write a propensity-logged shadow-bid record. The wire does NOT
re-compute the bid — that would duplicate logic + introduce
registry-state-divergence risk.

For the registry-honor regression test, the wire captures the
ACTIVE BidComposer's ``.name`` at submission time. When v3
1.D registers ``HInfWrappedKelly``, the shadow record carries
``bid_composer_name="hinf_wrapped_kelly"``. When the default
``KellyDefault`` is active, the record carries
``"kelly_default"``. The name field is the auditable proof
that the registry-dispatch invariant holds end-to-end.

THE PRIMITIVE

  * ``ShadowBidRecord`` — Pydantic model: decision_id +
    recommended_bid_value + ts_propensity + chosen_mechanism +
    posture_class + archetype + bid_composer_name + submitted_at_ts.
  * ``submit_shadow_bid(...)`` — async; persists the record via
    ``MERGE (b:ShadowBid {decision_id: $decision_id})`` per the
    same Cypher discipline as Slice 5's :ConversionEdge writer.
    Soft-fails on driver missing / Cypher exception.
  * ``ShadowBidSubmitResult`` — frozen dataclass: written /
    skipped flags + reason + composer_name_observed.

DISCIPLINE (B3-LUXY a/b/c/d)
----------------------------

(a) Citations: 2026-05-02 wrap-out greenlight (criterion ii recovery
    path + v3 Phase 1 work-stream 1.D seam). Slice 24 BidComposer
    registry (the substrate this wire respects). Slice 7 Kelly bid
    surface (the value this wire consumes). The :ShadowBid Cypher
    pattern matches Slice 5's :ConversionEdge writer + Slice 6's
    :AdOutcome writer (idempotent MERGE on deterministic id, scalar
    properties + timestamp, soft-fail on driver missing).

(b) Tests pin: submission writes :ShadowBid via correct Cypher;
    idempotent MERGE on decision_id; missing driver → soft-fail to
    skipped; driver exception → soft-fail to skipped + WARNING;
    bid_composer_name captured from registry at submission time;
    sentinel BidComposer registration → sentinel.name lands in
    record (regression net for registry-honor invariant);
    ShadowBidRecord round-trips through Pydantic.

(c) calibration_pending=False — pure wire substrate; no pilot-data-
    dependent constants.

(d) Honest tags — what is NOT in this slice (named successors):

    * Live bid write (StackAdapt OpenRTB / GraphQL bid-write path).
      Shadow mode by design — v3 Phase 1's bidder-promotion gate
      decides when to flip to live.
    * Bidder-side message envelope formatter (the structured
      payload that would go to StackAdapt's bidder when shadow
      → live). v0.1 ships the shadow log; the live envelope is
      v3 Phase 1.D's concern.
    * Real-time aggregation of shadow bids → bid-rate / spend-
      pacing surface for the partner dashboard. Sibling slice.
    * Shadow → live A/B promotion gate (BOIN-style — same
      structure as policy_gate sibling slice).
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)


# =============================================================================
# Schema
# =============================================================================


SHADOW_BID_NODE_LABEL: str = "ShadowBid"


class ShadowBidRecord(BaseModel):
    """One shadow-mode bid record — what would have been sent to the
    bidder under live mode."""

    model_config = ConfigDict(extra="forbid")

    decision_id: str
    recommended_bid_value: float
    ts_propensity: float = Field(ge=0.0, le=1.0)
    chosen_mechanism: str
    posture_class: Optional[str] = None
    archetype: str = ""
    bid_composer_name: str = "unknown"
    submitted_at_ts: float = Field(default_factory=time.time)
    user_id: str = ""


@dataclass(frozen=True)
class ShadowBidSubmitResult:
    """Outcome of one submit_shadow_bid attempt."""

    written: bool
    skipped: bool
    reason: str
    composer_name_observed: str
    decision_id: str


# =============================================================================
# Cypher
# =============================================================================


_PERSIST_SHADOW_BID_CYPHER: str = (
    f"MERGE (b:{SHADOW_BID_NODE_LABEL} "
    "{decision_id: $decision_id}) "
    "SET b.recommended_bid_value = $recommended_bid_value, "
    "    b.ts_propensity = $ts_propensity, "
    "    b.chosen_mechanism = $chosen_mechanism, "
    "    b.posture_class = $posture_class, "
    "    b.archetype = $archetype, "
    "    b.bid_composer_name = $bid_composer_name, "
    "    b.submitted_at_ts = $submitted_at_ts, "
    "    b.user_id = $user_id"
)


_LOAD_SHADOW_BID_CYPHER: str = (
    f"MATCH (b:{SHADOW_BID_NODE_LABEL} "
    "{decision_id: $decision_id}) "
    "RETURN b"
)


# =============================================================================
# Wire — submit_shadow_bid
# =============================================================================


def _capture_active_composer_name() -> str:
    """Read the active BidComposer's name from the v3 registry.
    The .name attribute is conventional on registered composers
    (KellyDefault, future HInfWrappedKelly, sentinels). Falls back
    to type name when .name is absent."""
    try:
        from adam.intelligence.v3_interfaces import (
            get_active_bid_composer,
        )
        composer = get_active_bid_composer()
        return str(getattr(composer, "name", type(composer).__name__))
    except Exception:
        return "unknown"


async def submit_shadow_bid(
    *,
    decision_id: str,
    recommended_bid_value: float,
    ts_propensity: float,
    chosen_mechanism: str,
    posture_class: Optional[str] = None,
    archetype: str = "",
    user_id: str = "",
    driver: Optional[Any] = None,
    submitted_at_ts: Optional[float] = None,
) -> ShadowBidSubmitResult:
    """Submit a shadow bid for the just-completed cascade decision.

    Args:
        decision_id: cascade decision id (idempotency key — re-runs
            update the existing record via MERGE).
        recommended_bid_value: the float from the cascade's
            BidComposer.compose_chosen() output.
        ts_propensity: the cascade's logged propensity for the
            chosen action (per Boruvka 2018 §2). Required for
            valid OPE downstream.
        chosen_mechanism: which mechanism the cascade picked.
        posture_class / archetype / user_id: context fields for
            audit.
        driver: async Neo4j driver. None → skipped.
        submitted_at_ts: override the timestamp (test seam).

    Returns:
        ``ShadowBidSubmitResult``. Soft-fail discipline: never
        propagates exceptions — the bid path NEVER blocks on
        shadow-logging.

    Idempotency: MERGE on decision_id. Re-runs update scalar
    properties; no duplicate :ShadowBid nodes.
    """
    composer_name = _capture_active_composer_name()

    if not decision_id:
        return ShadowBidSubmitResult(
            written=False,
            skipped=True,
            reason="no_decision_id",
            composer_name_observed=composer_name,
            decision_id="",
        )

    if driver is None:
        return ShadowBidSubmitResult(
            written=False,
            skipped=True,
            reason="no_driver",
            composer_name_observed=composer_name,
            decision_id=decision_id,
        )

    ts = submitted_at_ts if submitted_at_ts is not None else time.time()
    params: Dict[str, Any] = {
        "decision_id": decision_id,
        "recommended_bid_value": float(recommended_bid_value),
        "ts_propensity": float(max(0.0, min(1.0, ts_propensity))),
        "chosen_mechanism": str(chosen_mechanism or ""),
        "posture_class": posture_class,
        "archetype": str(archetype or ""),
        "bid_composer_name": composer_name,
        "submitted_at_ts": float(ts),
        "user_id": str(user_id or ""),
    }

    try:
        async with driver.session() as session:
            await session.run(_PERSIST_SHADOW_BID_CYPHER, **params)
    except Exception as exc:
        logger.warning(
            "submit_shadow_bid: write failed for decision_id=%s: %s",
            decision_id, exc,
        )
        return ShadowBidSubmitResult(
            written=False,
            skipped=False,
            reason="neo4j_exception",
            composer_name_observed=composer_name,
            decision_id=decision_id,
        )

    return ShadowBidSubmitResult(
        written=True,
        skipped=False,
        reason="written",
        composer_name_observed=composer_name,
        decision_id=decision_id,
    )


def submit_shadow_bid_sync(
    *,
    decision_id: str,
    recommended_bid_value: float,
    ts_propensity: float,
    chosen_mechanism: str,
    posture_class: Optional[str] = None,
    archetype: str = "",
    user_id: str = "",
    driver: Optional[Any] = None,
    submitted_at_ts: Optional[float] = None,
) -> ShadowBidSubmitResult:
    """Synchronous sibling of ``submit_shadow_bid`` for the sync
    StackAdapt service hot path.

    Uses the sync ``GraphDatabase`` driver (the one
    ``graph_cache._get_driver()`` returns). Same contract as
    ``submit_shadow_bid``: idempotent MERGE on decision_id;
    soft-fail on driver missing / Cypher exception.

    Pattern matches Slice C's ``lookup_creative_by_metadata_sync``
    — the cascade is sync; sync sibling uses the same sync driver.
    """
    composer_name = _capture_active_composer_name()

    if not decision_id:
        return ShadowBidSubmitResult(
            written=False,
            skipped=True,
            reason="no_decision_id",
            composer_name_observed=composer_name,
            decision_id="",
        )

    if driver is None:
        return ShadowBidSubmitResult(
            written=False,
            skipped=True,
            reason="no_driver",
            composer_name_observed=composer_name,
            decision_id=decision_id,
        )

    ts = submitted_at_ts if submitted_at_ts is not None else time.time()
    params: Dict[str, Any] = {
        "decision_id": decision_id,
        "recommended_bid_value": float(recommended_bid_value),
        "ts_propensity": float(max(0.0, min(1.0, ts_propensity))),
        "chosen_mechanism": str(chosen_mechanism or ""),
        "posture_class": posture_class,
        "archetype": str(archetype or ""),
        "bid_composer_name": composer_name,
        "submitted_at_ts": float(ts),
        "user_id": str(user_id or ""),
    }

    try:
        with driver.session() as session:
            session.run(_PERSIST_SHADOW_BID_CYPHER, **params)
    except Exception as exc:
        logger.warning(
            "submit_shadow_bid_sync: write failed for "
            "decision_id=%s: %s",
            decision_id, exc,
        )
        return ShadowBidSubmitResult(
            written=False,
            skipped=False,
            reason="neo4j_exception",
            composer_name_observed=composer_name,
            decision_id=decision_id,
        )

    return ShadowBidSubmitResult(
        written=True,
        skipped=False,
        reason="written",
        composer_name_observed=composer_name,
        decision_id=decision_id,
    )


async def load_shadow_bid(
    *, decision_id: str, driver: Optional[Any],
) -> Optional[ShadowBidRecord]:
    """Read a persisted shadow-bid record by decision_id. Returns
    None when driver missing / no match / exception."""
    if driver is None or not decision_id:
        return None
    try:
        async with driver.session() as session:
            result = await session.run(
                _LOAD_SHADOW_BID_CYPHER, decision_id=decision_id,
            )
            record = await result.single()
    except Exception as exc:
        logger.warning(
            "load_shadow_bid failed for decision_id=%s: %s",
            decision_id, exc,
        )
        return None
    if record is None:
        return None
    node = record.get("b") if hasattr(record, "get") else None
    if node is None:
        return None
    try:
        return ShadowBidRecord(
            decision_id=str(node.get("decision_id") or ""),
            recommended_bid_value=float(
                node.get("recommended_bid_value") or 0.0,
            ),
            ts_propensity=float(node.get("ts_propensity") or 0.0),
            chosen_mechanism=str(node.get("chosen_mechanism") or ""),
            posture_class=node.get("posture_class"),
            archetype=str(node.get("archetype") or ""),
            bid_composer_name=str(
                node.get("bid_composer_name") or "unknown",
            ),
            submitted_at_ts=float(node.get("submitted_at_ts") or 0.0),
            user_id=str(node.get("user_id") or ""),
        )
    except Exception as exc:
        logger.warning("ShadowBidRecord parse failed: %s", exc)
        return None
