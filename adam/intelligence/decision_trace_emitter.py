# =============================================================================
# Spine #6 — DecisionTrace producer (sync emit + async drain)
# Location: adam/intelligence/decision_trace_emitter.py
# =============================================================================
"""Synchronous emit + asynchronous drain for ``DecisionTrace`` records.

Closes the producer side of directive Spine #6 (lines 226, 248, 695):

    line 226: "the orchestrator emits a structured trace"
    line 248: "Hot trace cache in Redis ... Long-term archival in Neo4j"
    line 695: "Decision trace emission (Spine #6): full structured
               trace persisted to Redis (hot) and Neo4j (long-term)."

Three substrate slices already shipped (ca03336 schema, d9b4d7c Redis,
edd4ded Neo4j) gave the data contract + the two-tier storage. This
module is the producer that closes the loop: ``emit()`` is called
synchronously from the cascade hot path; ``drain_to_storage()`` is
called by an async worker (a Daily Task or sibling) to flush pending
traces into Redis + Neo4j.

WHY THE SYNC/ASYNC SPLIT
------------------------

The cascade (run_bilateral_cascade) is synchronous. Storage is async
(redis.asyncio + AsyncDriver). Coupling them directly would either
force an ``asyncio.run`` from sync context (broken if an event loop
is already running) or require a fire-and-forget create_task
(orphaned tasks, no backpressure, no failure visibility).

The mrt_producer module (adam/intelligence/mrt_producer.py) solved
the same problem the same way for MRT records: sync ``emit()`` writes
to an in-memory log; an offline path drains. We mirror its pattern
exactly so the operational story stays uniform — one log type per
record class, drained the same way.

PROPENSITY DECOMPOSITION
------------------------

The cascade selects via ε-floor-mixed argmax (handoff §1.1):
    π_TS(a) = pi_from_argmax_scores(scores)         (delta on argmax)
    p_t(a)  = epsilon_floor_mix(π_TS, ε)            (per-arm propensity)

build_trace_from_cascade reconstructs the FULL p_t distribution from
the same primitives, so the chosen arm's propensity matches the
logged p_t exactly AND each alternative carries its mathematically
correct propensity_under_TS — not a placeholder split.

This is what lets the OPE estimators (adam/intelligence/ope.py) use
the trace's alternative propensities for inverse-propensity weighting
on every served impression — the 3-5x effective sample size
multiplier the directive's Spine #6 promises (line 228).

DISCIPLINE (B3-LUXY a/b/c/d)
----------------------------

(a) Citation: directive Spine #6 lines 226, 248, 695. The sync-emit-
    plus-async-drain pattern matches mrt_producer (Boruvka 2018 §2 +
    handoff §1.10: bid path must NEVER block on logging). Propensity
    decomposition uses pi_from_argmax_scores + epsilon_floor_mix
    (handoff §1.1) so the distribution is mathematically grounded
    in the actual policy that picked the chosen arm.

(b) Tests pin: emit/drain round-trip preserves traces; capacity
    boundary evicts oldest with logged warning; thread-safe
    concurrent emit; build_trace_from_cascade computes correct
    propensities (chosen p_t matches; alternatives sum to 1-p_t);
    soft-fail when storage clients absent; cascade smoke test
    verifies trace emission on a synthetic cascade run.

(c) calibration_pending=True. The IN_MEMORY_LOG_CAPACITY default
    (10_000 traces) is conservative pre-pilot; LUXY pilot traffic
    will calibrate against actual decision rate × drain frequency.
    A14 flag: SPINE_6_DECISION_TRACE_LOG_CAPACITY_PILOT_PENDING.

(d) Honest tags — what is NOT in this slice (named successors):

    * chosen_creative_id placeholder. The cascade outputs creative
      INTELLIGENCE (mechanism + parameters), not a specific creative
      id. We use ``mechanism_proxy:{mechanism_name}`` until a typed
      creative-resolution layer ships. The placeholder pattern is
      documented in build_trace_from_cascade and round-trips through
      the schema honestly.
    * Daily drain task (e.g., Task 38) that calls drain_to_storage
      on a periodic schedule — sibling slice. The drain function
      shipped here is ready for any async worker to call.
    * Free-energy decomposition (Spine #5), epistemic-bonus (Spine
      #8), Kelly bid value (Spine #9) are schema slots — the trace
      builder doesn't populate them yet because their producers
      haven't shipped.
    * page_posture_vector / posture_class population — depends on
      page-side intelligence delivery into the cascade; partly
      covered by adam/intelligence/page_attentional_posture_substrate
      but not currently flowing into the cascade output.
"""

from __future__ import annotations

import logging
import threading
from collections import deque
from typing import Any, Deque, List, Optional, Tuple

from adam.intelligence.decision_trace import (
    AlternativeCandidate,
    DecisionTrace,
    build_decision_trace,
)
from adam.intelligence.decision_trace_neo4j import archive_trace_to_neo4j
from adam.intelligence.decision_trace_store import store_trace
from adam.intelligence.mrt_logging import (
    EPSILON_FLOOR,
    epsilon_floor_mix,
    pi_from_argmax_scores,
)

logger = logging.getLogger(__name__)


# A14 SPINE_6_DECISION_TRACE_LOG_CAPACITY_PILOT_PENDING
IN_MEMORY_LOG_CAPACITY: int = 10_000

# Per directive line 226: "evaluates ~3-5 alternative pairs."
# We carry up to this many alternatives in each trace; tests pin.
DEFAULT_MAX_ALTERNATIVES: int = 5

# Honest tag — placeholder creative id derived from chosen mechanism.
# Tests verify the prefix is preserved across round-trip.
_CREATIVE_PROXY_PREFIX: str = "mechanism_proxy:"


# =============================================================================
# In-memory log
# =============================================================================


class InMemoryDecisionTraceLog:
    """Thread-safe bounded log of pending decision traces.

    Mirrors ``mrt_logging.InMemoryDecisionLog``'s discipline:
      * append-only from sync emit
      * pop oldest from async drain
      * bounded capacity — deque(maxlen=IN_MEMORY_LOG_CAPACITY) evicts
        oldest under pressure with a logged warning
      * thread-safe via simple lock (the bid path's emit cost is one
        lock acquire, well within the directive's hot-path budget)
    """

    def __init__(self, capacity: int = IN_MEMORY_LOG_CAPACITY) -> None:
        self._items: Deque[DecisionTrace] = deque(maxlen=capacity)
        self._lock = threading.Lock()
        self._evictions: int = 0

    def emit(self, trace: DecisionTrace) -> None:
        with self._lock:
            if len(self._items) >= self._items.maxlen:  # type: ignore[arg-type]
                self._evictions += 1
                if self._evictions == 1 or self._evictions % 1000 == 0:
                    logger.warning(
                        "DecisionTrace log at capacity (%d); oldest "
                        "trace evicted (total evictions=%d). "
                        "Drain frequency may need to increase.",
                        self._items.maxlen, self._evictions,
                    )
            self._items.append(trace)

    def drain(self, max_items: int = 1000) -> List[DecisionTrace]:
        """Pop up to max_items oldest traces. Empty list if log is empty."""
        with self._lock:
            n = min(int(max_items), len(self._items))
            out = [self._items.popleft() for _ in range(n)]
            return out

    def __len__(self) -> int:
        with self._lock:
            return len(self._items)

    @property
    def evictions(self) -> int:
        return self._evictions


# =============================================================================
# Module singleton (mirrors mrt_producer's pattern)
# =============================================================================


_LOG_LOCK = threading.Lock()
_LOG: Optional[InMemoryDecisionTraceLog] = None


def get_log() -> InMemoryDecisionTraceLog:
    """Return the process-singleton ``InMemoryDecisionTraceLog``.

    Lazy initialized on first call. Thread-safe.
    """
    global _LOG
    if _LOG is not None:
        return _LOG
    with _LOG_LOCK:
        if _LOG is None:
            _LOG = InMemoryDecisionTraceLog()
            logger.info(
                "DecisionTrace emitter: in-memory log initialized "
                "(capacity=%d)", IN_MEMORY_LOG_CAPACITY,
            )
    return _LOG


def emit(trace: DecisionTrace) -> None:
    """Synchronous emit — soft-fails on any exception per handoff §1.10.

    The bid path must NEVER block on logging. Wrap every line in
    try/except; on failure log and continue. If the entire log
    singleton is broken (catastrophic), the trace is dropped and the
    cascade still returns its result.
    """
    try:
        get_log().emit(trace)
    except Exception as exc:
        logger.warning("DecisionTrace emit failed: %s", exc)


def reset_for_tests(
    log: Optional[InMemoryDecisionTraceLog] = None,
) -> None:
    """Swap in a controlled log for tests. Without arg, fresh log."""
    global _LOG
    with _LOG_LOCK:
        _LOG = log if log is not None else InMemoryDecisionTraceLog()


# =============================================================================
# Cascade-output → DecisionTrace builder
# =============================================================================


def build_trace_from_cascade(
    *,
    decision_id: str,
    user_id: str,
    archetype: str,
    category: Optional[str],
    cascade_result: Any,                # CreativeIntelligence (duck-typed)
    chosen_mechanism: str,
    p_t: float,
    epsilon: float = EPSILON_FLOOR,
    bid_request_id: Optional[str] = None,
    page_posture_vector: Optional[List[float]] = None,
    posture_class: Optional[str] = None,
    posture_confidence: Optional[float] = None,
    max_alternatives: int = DEFAULT_MAX_ALTERNATIVES,
    confidence_snapshot: Optional[dict] = None,
    bong_posterior: Any = None,
    page_url: Optional[str] = None,
) -> DecisionTrace:
    """Build a ``DecisionTrace`` from a cascade output.

    The cascade produces ``CreativeIntelligence`` with
    ``mechanism_scores: Dict[str, float]``. We reconstruct the full
    propensity distribution via ``pi_from_argmax_scores`` +
    ``epsilon_floor_mix`` so the chosen arm's propensity_under_TS
    matches the logged p_t exactly AND each alternative carries its
    mathematically correct propensity.

    chosen_creative_id is a placeholder (``mechanism_proxy:{mech}``)
    until a typed creative-resolution layer ships — the cascade picks
    a mechanism with creative parameters, not a specific creative id.
    Documented honest tag.

    confidence_snapshot, when provided, is merged into the trace's
    ``user_posterior_snapshot`` dict. Conventional keys consumed by
    ``defensive_reasoning_renderer._render_confidence`` are
    ``point_estimate`` / ``ci_lower_90`` / ``ci_upper_90``. The
    canonical producer is
    ``adam.intelligence.confidence_snapshot.compute_confidence_snapshot``.
    Empty / None → no merge; archetype presence marker is preserved.

    bong_posterior, when provided alongside posture_class, triggers the
    bid composer (``adam.intelligence.bid_composer``) to populate
    AlternativeCandidate.{fluency_score, mechanism_compatibility_score,
    epistemic_bonus, bid_value} per the directive's dual-control bid
    formulation (lines 273-313 + Phase 4 lines 1011-1024). When either
    is None, the slots stay None and the renderer correctly omits them.
    """
    scores = getattr(cascade_result, "mechanism_scores", {}) or {}
    chosen_score = float(scores.get(chosen_mechanism, 0.0))

    # Reconstruct full p_t distribution over all arms.
    if scores:
        try:
            pi_ts = pi_from_argmax_scores(scores)
            p_t_dist = epsilon_floor_mix(pi_ts, epsilon=epsilon)
        except Exception as exc:
            logger.debug(
                "build_trace_from_cascade: propensity reconstruction "
                "failed (%s); falling back to chosen p_t only.", exc,
            )
            p_t_dist = {chosen_mechanism: float(p_t)}
    else:
        p_t_dist = {chosen_mechanism: float(p_t)}

    # Top alternatives by score, excluding chosen, capped at max_alternatives
    other_scored = [
        (m, float(s)) for m, s in scores.items() if m != chosen_mechanism
    ]
    other_scored.sort(key=lambda x: x[1], reverse=True)
    alternatives = [
        AlternativeCandidate(
            creative_id=f"{_CREATIVE_PROXY_PREFIX}{m}",
            mechanism=m,
            posterior_score=s,
            propensity_under_TS=float(p_t_dist.get(m, 0.0)),
        )
        for m, s in other_scored[:max_alternatives]
    ]

    # Per-archetype context snapshot — minimal until a richer
    # snapshot helper ships (sibling slice).
    user_posterior_snapshot: dict = {}
    if archetype:
        user_posterior_snapshot["archetype"] = 1.0  # presence marker

    # Confidence snapshot — merge ci_lower_90 / ci_upper_90 /
    # point_estimate when the producer (confidence_snapshot.
    # compute_confidence_snapshot) supplied them. Absent keys leave
    # the renderer in status="not_available" by design.
    if confidence_snapshot:
        for key, value in confidence_snapshot.items():
            try:
                user_posterior_snapshot[key] = float(value)
            except (TypeError, ValueError):
                continue

    # Bid composer — populate AlternativeCandidate.{fluency_score,
    # mechanism_compatibility_score, epistemic_bonus, bid_value} +
    # trace-level bid_value. Composes Spine #8 + Spine #9 + Phase 2
    # at decision time (directive lines 273-313 + 1011-1024). Each
    # leg is gated: if bong_posterior is None or posture_class missing,
    # the slots stay None and the renderer omits them. Soft-fail by
    # design — bid path must NEVER block on logging (handoff §1.10).
    chosen_bid_value: Optional[float] = None
    if bong_posterior is not None and posture_class:
        try:
            from adam.intelligence.bid_composer import (
                compose_alternatives,
                compose_chosen_bid_value,
            )
            alternatives = compose_alternatives(
                alternatives,
                posture=posture_class,
                bong_posterior=bong_posterior,
            )
            chosen_bid_value = compose_chosen_bid_value(
                chosen_mechanism=chosen_mechanism,
                chosen_score=chosen_score,
                posture=posture_class,
                bong_posterior=bong_posterior,
            )
        except Exception as exc:
            logger.debug("bid_composer skipped: %s", exc)

    return build_decision_trace(
        decision_id=decision_id,
        user_id=user_id,
        bid_request_id=bid_request_id,
        chosen_creative_id=f"{_CREATIVE_PROXY_PREFIX}{chosen_mechanism}",
        chosen_mechanism=chosen_mechanism,
        chosen_score=chosen_score,
        alternatives=alternatives,
        user_posterior_snapshot=user_posterior_snapshot,
        page_posture_vector=page_posture_vector,
        posture_class=posture_class,
        posture_confidence=posture_confidence,
        bid_value=chosen_bid_value,
        page_url=page_url,
    )


# =============================================================================
# Async drain — flush pending traces to Redis + Neo4j
# =============================================================================


async def drain_to_storage(
    redis_client: Optional[Any] = None,
    neo4j_driver: Optional[Any] = None,
    max_items: int = 1000,
) -> Tuple[int, int, int]:
    """Drain pending traces and write to Redis + Neo4j in parallel paths.

    Args:
        redis_client: async Redis client; None → skip Redis writes.
        neo4j_driver: async Neo4j driver; None → skip Neo4j writes.
        max_items: cap on traces drained per call. Bounds drain cost
            and lets the worker yield to other tasks between batches.

    Returns:
        ``(n_drained, n_redis_ok, n_neo4j_ok)`` — counts of traces
        drained, successfully written to Redis, and successfully
        written to Neo4j. Per-trace failures are logged and counted
        as zero contributions but do not abort the batch.

    Soft-fail discipline: any storage exception is caught + logged;
    the function never raises. Drained traces that fail to write are
    not requeued — the worker is expected to call drain again if
    more traces accumulate. Per-trace loss visibility is via the
    return counts (caller compares n_drained vs n_redis_ok / n_neo4j_ok).
    """
    items = get_log().drain(max_items=max_items)
    if not items:
        return (0, 0, 0)

    n_redis_ok = 0
    n_neo4j_ok = 0
    for trace in items:
        if redis_client is not None:
            try:
                if await store_trace(trace, redis_client):
                    n_redis_ok += 1
            except Exception as exc:
                logger.warning(
                    "drain_to_storage Redis write failed for "
                    "decision_id=%s: %s", trace.decision_id, exc,
                )
        if neo4j_driver is not None:
            try:
                if await archive_trace_to_neo4j(trace, neo4j_driver):
                    n_neo4j_ok += 1
            except Exception as exc:
                logger.warning(
                    "drain_to_storage Neo4j archive failed for "
                    "decision_id=%s: %s", trace.decision_id, exc,
                )

    return (len(items), n_redis_ok, n_neo4j_ok)
