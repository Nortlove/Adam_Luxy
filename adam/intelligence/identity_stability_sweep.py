# =============================================================================
# Identity-stability collapse sweep — Slice 16
# Location: adam/intelligence/identity_stability_sweep.py
# =============================================================================
"""Per-user identity-stability sweep — RED criterion #4 producer.

Closes the named sibling tag from
``task_42_launch_gate_runner.py:43-46``:

    "Identity-stability collapse counter producer wire. The
     snapshot's record_identity_collapse method exists; the
     user-posterior maintenance sweep that calls it is a sibling
     slice (named in red_criteria_snapshot (d))."

Per directive Section 9 Phase 10 line 1131-1138 RED criterion #4
("Per-user posterior pathologies — identity-stability weight collapse
for >30% of touches"):

    n_collapsed / n_active > RED_IDENTITY_STABILITY_COLLAPSE_FRACTION_MAX
    → launch gate triggers RED

The check function ``check_posterior_pathology`` (in
``phase_10_launch_sequence.py``) consumes the producer counters; this
slice is the producer that surveys active buyers and increments
``record_user_active`` + ``record_identity_collapse`` based on
decayed identity_stability per user.

THE PRIMITIVE

  * ``IDENTITY_STABILITY_COLLAPSE_THRESHOLD`` — 0.05 default. Below
    this, a user's identity is treated as collapsed (cookie attrited
    enough that we can no longer reliably link new touches to prior
    posteriors). Calibration_pending — pilot-data-derived.
  * ``IDENTITY_STABILITY_DEFAULT_INITIAL`` — 1.0. The starting
    stability assumed when a user is first observed. Can be lowered
    for privacy-conscious deployment per directive Section 3.4.
  * ``IDENTITY_STABILITY_LOOKBACK_DAYS`` — 30. Active = at least one
    touch within this window. Older users are not counted in
    n_active (they're treated as already attrited from the panel).
  * ``compute_decayed_stability(days_since_last_seen, ...)`` — calls
    ``decay_identity_stability`` from phase_8 with default params.
  * ``IdentityStabilitySweepResult`` — frozen dataclass:
    n_active / n_collapsed / collapse_fraction / details.
  * ``sweep_active_buyers(decision_cache, ...)`` — iterates the
    in-process buyers, computes per-user days-since-last-touch,
    counts active + collapsed, increments snapshot counters,
    returns the result.

DISCIPLINE (B3-LUXY a/b/c/d)

(a) Citations: directive Section 9 Phase 10 lines 1131-1138 (RED
    criterion #4); task_42_launch_gate_runner.py:43-46 (named
    sibling tag); directive Section 3.4 (identity-stability as
    learned object). Decay primitive from
    ``phase_8_stackadapt_integration.decay_identity_stability``
    (already shipped). Snapshot accumulator surfaces from
    ``red_criteria_snapshot.record_identity_collapse`` +
    ``record_user_active`` (already shipped — this slice is the
    producer that finally calls them).

(b) Tests pin: empty cache → n_active=0 + n_collapsed=0;
    fresh-touch buyer (Δ=0) → not collapsed; old buyer (Δ=200d
    with default 2%/day decay) → collapsed; lookback filter
    excludes Δ > IDENTITY_STABILITY_LOOKBACK_DAYS;
    snapshot counters incremented; soft-fail when no decision_cache;
    IdentityStabilitySweepResult frozen; primitive is pure
    (no global mutation in unit tests when accumulator passed in).

(c) calibration_pending=True. Default threshold (0.05),
    initial stability (1.0), lookback (30 days) — all conservative
    pre-pilot values. LUXY pilot data (Task 36 nightly HMC
    reconcile + actual cookie-attrition curve) will calibrate.
    A14 flag: PHASE_10_IDENTITY_STABILITY_THRESHOLD_PILOT_PENDING.

(d) Honest tags — what is NOT in this slice (named successors):

    * Persistent per-user identity_stability storage. v0.1
      decays from a default starting point per active buyer
      based on days-since-last-touch in decision_cache.
      A first-class :User.identity_stability scalar (with
      learned-update-on-touch semantics) is sibling slice —
      requires a Neo4j schema migration + UserPosteriorProfile
      field addition.
    * Multi-pod sweep. The in-process decision_cache is per-
      process; multi-pod deploy needs the Redis-backed touch
      registry already named in within_subject_eligibility.py
      honest tag (d) for the eligibility filter. Same sibling
      slice serves both consumers.
    * Active learning of attrition_per_day per user / cohort.
      v0.1 uses a fixed 2%/day. Pilot-derived per-user attrition
      curves are sibling.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from adam.intelligence.spine.phase_8_stackadapt_integration import (
    DEFAULT_COOKIE_ATTRITION_PER_DAY,
    decay_identity_stability,
)

logger = logging.getLogger(__name__)


# A14 PHASE_10_IDENTITY_STABILITY_THRESHOLD_PILOT_PENDING
IDENTITY_STABILITY_COLLAPSE_THRESHOLD: float = 0.05
IDENTITY_STABILITY_DEFAULT_INITIAL: float = 1.0
IDENTITY_STABILITY_LOOKBACK_DAYS: float = 30.0


@dataclass(frozen=True)
class IdentityStabilitySweepResult:
    """Outcome of one identity-stability sweep run.

    ``n_active``: count of buyers within the lookback window.
    ``n_collapsed``: subset of n_active whose decayed stability is
        below COLLAPSE_THRESHOLD.
    ``collapse_fraction``: n_collapsed / n_active (0 when n_active=0).
    ``per_buyer``: optional per-buyer (id, days_since, stability,
        collapsed) tuples — populated only when sweep is called with
        ``include_per_buyer=True`` (test / debug path).
    """

    n_active: int = 0
    n_collapsed: int = 0
    collapse_fraction: float = 0.0
    per_buyer: List[Tuple[str, float, float, bool]] = field(
        default_factory=list,
    )


def compute_decayed_stability(
    days_since_last_seen: float,
    *,
    initial_stability: float = IDENTITY_STABILITY_DEFAULT_INITIAL,
    attrition_per_day: float = DEFAULT_COOKIE_ATTRITION_PER_DAY,
) -> float:
    """Compute the user's current identity_stability via decay.

    v0.1 starts every user at ``initial_stability=1.0`` and decays
    linearly with days-since-last-touch. Persistent per-user storage
    of identity_stability (so we don't reset to 1.0 on every sweep)
    is a sibling slice.
    """
    return decay_identity_stability(
        current_stability=initial_stability,
        days_since_last_seen=max(0.0, float(days_since_last_seen)),
        attrition_per_day=attrition_per_day,
    )


def is_identity_collapsed(
    stability: float,
    *,
    threshold: float = IDENTITY_STABILITY_COLLAPSE_THRESHOLD,
) -> bool:
    """True iff stability < threshold (collapse condition)."""
    return float(stability) < float(threshold)


def _iter_recent_buyers(
    decision_cache: Any,
    *,
    lookback_days: float,
) -> List[Tuple[str, float]]:
    """Walk the decision_cache LRU; return ``[(buyer_id, days_since)]``
    for buyers with at least one touch within the lookback window.

    Multiple touches per buyer → uses the most recent timestamp.
    Anonymous buyers (empty buyer_id) are excluded from the active
    count (they're not addressable per-user).
    """
    if decision_cache is None:
        return []
    store = getattr(decision_cache, "_store", None)
    if store is None:
        return []

    now = time.time()
    cutoff = now - (lookback_days * 86400.0)

    # buyer_id → most recent created_at
    latest: Dict[str, float] = {}
    for ctx in store.values():
        bid = getattr(ctx, "buyer_id", "") or ""
        if not bid:
            continue
        ts = float(getattr(ctx, "created_at", 0.0) or 0.0)
        if ts < cutoff:
            continue
        prev = latest.get(bid)
        if prev is None or ts > prev:
            latest[bid] = ts

    return [
        (bid, max(0.0, (now - ts) / 86400.0))
        for bid, ts in latest.items()
    ]


def sweep_active_buyers(
    decision_cache: Any,
    *,
    snapshot: Optional[Any] = None,
    lookback_days: float = IDENTITY_STABILITY_LOOKBACK_DAYS,
    threshold: float = IDENTITY_STABILITY_COLLAPSE_THRESHOLD,
    initial_stability: float = IDENTITY_STABILITY_DEFAULT_INITIAL,
    attrition_per_day: float = DEFAULT_COOKIE_ATTRITION_PER_DAY,
    include_per_buyer: bool = False,
) -> IdentityStabilitySweepResult:
    """Survey active buyers, count collapsed, increment snapshot.

    Args:
        decision_cache: in-process DecisionCache instance; iterates
            ``_store`` for the per-buyer recent-touch timestamps.
            None / missing _store → returns empty result.
        snapshot: optional ``RedCriteriaSnapshot`` instance. When
            provided, ``record_user_active(n_active)`` and
            ``record_identity_collapse(n_collapsed)`` are called.
            None → counters not incremented (test / dry-run path).
        lookback_days: only count buyers with a touch within this
            many days. Default 30. Older buyers are treated as
            already attrited from the panel.
        threshold: stability < threshold → collapsed.
        initial_stability: starting stability per buyer (v0.1 default
            1.0 — every observed buyer starts stable).
        attrition_per_day: per-day attrition rate.
        include_per_buyer: when True, populate per_buyer in result
            (test/debug path; default False keeps result lightweight).

    Returns:
        IdentityStabilitySweepResult.
    """
    buyers = _iter_recent_buyers(
        decision_cache, lookback_days=lookback_days,
    )
    n_active = len(buyers)
    n_collapsed = 0
    per_buyer: List[Tuple[str, float, float, bool]] = []

    for bid, days_since in buyers:
        stability = compute_decayed_stability(
            days_since,
            initial_stability=initial_stability,
            attrition_per_day=attrition_per_day,
        )
        collapsed = is_identity_collapsed(stability, threshold=threshold)
        if collapsed:
            n_collapsed += 1
        if include_per_buyer:
            per_buyer.append((bid, days_since, stability, collapsed))

    if snapshot is not None and n_active > 0:
        try:
            snapshot.record_user_active(n_active)
            if n_collapsed > 0:
                snapshot.record_identity_collapse(n_collapsed)
        except Exception as exc:
            logger.warning(
                "identity_stability_sweep: snapshot increment failed: %s",
                exc,
            )

    fraction = (n_collapsed / n_active) if n_active > 0 else 0.0

    return IdentityStabilitySweepResult(
        n_active=n_active,
        n_collapsed=n_collapsed,
        collapse_fraction=fraction,
        per_buyer=per_buyer,
    )
