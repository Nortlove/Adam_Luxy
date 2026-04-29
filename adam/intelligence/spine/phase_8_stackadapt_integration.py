# =============================================================================
# ADAM Phase 8 — StackAdapt Integration Hardening Substrate
# Location: adam/intelligence/spine/phase_8_stackadapt_integration.py
# =============================================================================

"""StackAdapt integration hardening substrate.

PER DIRECTIVE SECTION 9 PHASE 8.

Per directive: "StackAdapt GraphQL write-API integration; audience push
pipeline; creative upload pipeline; daily reporting pull; Pixel API for
inbound conversions; sapid round-trip end-to-end monitoring; holdout-
discipline single-function deterministic-hash implementation."

Substrate items (this module):
    - Deterministic-hash holdout assignment (5-10% untouched stratum)
    - Sapid round-trip monitoring (counter + rate + degradation alerts)
    - Identity-stability decay under simulated cookie attrition

Operational items (deferred to production deploy):
    - StackAdapt GraphQL write-API client (needs API access)
    - Audience push pipeline (consumes cohort_id → audience_id mapping)
    - Creative upload pipeline (createCreativeByURL with metadata)
    - Daily reporting pull (GraphQL query against reporting endpoint)

PHASE 8 RED-CRITERION GATE (per directive Section 9 Phase 8)

    "Round-trip rate on synthetic-flow test ≥98%. Identity-stability
    weight degrades smoothly under simulated cookie attrition. RED
    if signal channel is fragile under realistic operational
    conditions."

DECISION-TIME CONSUMERS (Rule A check)

  - Holdout assignment runs at every bid request — decision-time gate
    that determines whether the user is in treatment or holdout
  - Sapid round-trip monitor reads at outcome arrival time
  - Identity-stability decay updates UserPosterior.identity_stability
    which Spine #1 consumes for partial-pooling weight at decision time

Cognitive primitive at the serving path. NOT measurement.

REFERENCES

    Per directive Section 3.7: sapid round-trip is "the only deterministic
    linkage between served impression and downstream observation; treat
    it as sacred."

    Deterministic-hash holdout: standard practice in digital experimentation
    (Aharon Bar-Lev, "A/B Testing Patterns"; LinkedIn engineering blog
    posts on stable-bucketing).
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field, field_validator

logger = logging.getLogger(__name__)


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


# =============================================================================
# Configuration constants per directive
# =============================================================================


# Per directive Section 9 Phase 8: "5-10% of bid-eligible traffic,
# untouched." Default 10% holdout (1 user in 10 routed to control).
DEFAULT_HOLDOUT_FRACTION: float = 0.10


# Per directive Section 9 Phase 8 RED criteria: round-trip rate ≥ 98%.
DEFAULT_ROUND_TRIP_TARGET: float = 0.98


# Identity-stability decay constants. Per directive Section 3.4:
# "Identity-stability weight is itself a learned object: how often does
# this user's identity persist across sessions?"
DEFAULT_COOKIE_ATTRITION_PER_DAY: float = 0.02   # 2%/day baseline
IDENTITY_STABILITY_FLOOR: float = 0.0            # never below 0


# =============================================================================
# Deterministic-hash holdout assignment (per directive)
# =============================================================================


# Salt for the hash. Per directive: "single-function deterministic-hash
# implementation." Salt prevents adversarial collision with the
# StackAdapt user_id namespace; fixed across the pilot for stability.
_HOLDOUT_HASH_SALT: str = "adam_luxy_pilot_v1"


def assign_holdout(
    user_id: str,
    *,
    holdout_fraction: float = DEFAULT_HOLDOUT_FRACTION,
    salt: str = _HOLDOUT_HASH_SALT,
) -> bool:
    """Deterministic-hash assignment to (treatment, holdout).

    Returns True iff user is in HOLDOUT (untouched stratum).

    Per directive Section 9 Phase 8: "Holdout-discipline single-function
    deterministic-hash implementation (5–10% of bid-eligible traffic,
    untouched)." Same user_id always produces same assignment (stable
    bucketing); aggregate proportion converges to holdout_fraction.

    Hash: SHA-256 of (salt + user_id) → mod 1_000_000 → divided by 1M
    → in [0, 1). User in holdout iff this fraction < holdout_fraction.

    Args:
        user_id: stable identifier (StackAdapt user_id, ramp_id, etc.)
        holdout_fraction: target holdout proportion in (0, 1)
        salt: hash salt; default fixed for pilot stability

    Raises ValueError on invalid holdout_fraction or empty user_id.
    """
    if not user_id or not user_id.strip():
        raise ValueError("user_id must be non-empty")
    if not 0.0 < holdout_fraction < 1.0:
        raise ValueError(
            f"holdout_fraction must be in (0, 1); got {holdout_fraction}"
        )

    raw = (salt + ":" + user_id).encode("utf-8")
    digest = hashlib.sha256(raw).hexdigest()
    bucket = int(digest, 16) % 1_000_000
    fraction = bucket / 1_000_000.0
    return fraction < holdout_fraction


def estimate_holdout_proportion(
    user_ids: List[str],
    *,
    holdout_fraction: float = DEFAULT_HOLDOUT_FRACTION,
    salt: str = _HOLDOUT_HASH_SALT,
) -> float:
    """Estimate the empirical holdout proportion across a set of user_ids.

    Used by the integration test to verify the hash distributes
    correctly. For a uniform stable hash, empirical proportion converges
    to holdout_fraction as N grows.
    """
    if not user_ids:
        return 0.0
    in_holdout = sum(
        1 for uid in user_ids
        if assign_holdout(uid, holdout_fraction=holdout_fraction, salt=salt)
    )
    return in_holdout / len(user_ids)


# =============================================================================
# Sapid round-trip monitor (per directive Section 3.7)
# =============================================================================


@dataclass
class SapidRoundTripMonitor:
    """Tracks sapid round-trip success rate.

    Per directive Section 3.7: "Round-trip rate is monitored as a load-
    bearing operational metric (target: ≥98% of conversions back-linked
    to served impressions)."

    Increment counters at:
        - bid time (every served impression registers a sapid)
        - outcome time (every pixel event with a known sapid → success;
          unknown sapid → failure)

    Reports rate. Phase 8 RED gate: rate ≥ 0.98.
    """

    n_sapids_registered: int = 0
    n_sapids_resolved: int = 0
    n_sapids_unresolved: int = 0  # incoming pixel event with unknown sapid

    def record_registration(self) -> None:
        """Called by orchestrator at decision time."""
        self.n_sapids_registered += 1

    def record_resolution(self, resolved: bool) -> None:
        """Called by Spine #11 build_outcome_event when an incoming
        RawPixelEvent's sapid is looked up. resolved=True iff the
        sapid was found in the registry."""
        if resolved:
            self.n_sapids_resolved += 1
        else:
            self.n_sapids_unresolved += 1

    def round_trip_rate(self) -> float:
        """Return the round-trip rate: resolved / (resolved + unresolved).

        Returns 0.0 when no events received yet (no rate to compute).
        """
        total_events = self.n_sapids_resolved + self.n_sapids_unresolved
        if total_events == 0:
            return 0.0
        return self.n_sapids_resolved / total_events

    def meets_phase_8_target(
        self, target: float = DEFAULT_ROUND_TRIP_TARGET,
    ) -> bool:
        """Return True iff round_trip_rate ≥ target (default 0.98)."""
        return self.round_trip_rate() >= target

    def reset(self) -> None:
        """Test-only: clear all counters."""
        self.n_sapids_registered = 0
        self.n_sapids_resolved = 0
        self.n_sapids_unresolved = 0


# Default singleton (production replaces with persistent counter).
_default_monitor = SapidRoundTripMonitor()


def get_default_monitor() -> SapidRoundTripMonitor:
    return _default_monitor


def reset_default_monitor() -> None:
    """Test-only."""
    _default_monitor.reset()


# =============================================================================
# Identity-stability decay under cookie attrition
# =============================================================================


def decay_identity_stability(
    current_stability: float,
    days_since_last_seen: float,
    *,
    attrition_per_day: float = DEFAULT_COOKIE_ATTRITION_PER_DAY,
) -> float:
    """Decay identity-stability weight by simulated cookie attrition.

    Per directive Section 3.4: "Identity-stability weight is itself a
    learned object: how often does this user's identity persist across
    sessions? This degrades smoothly under privacy-conscious deployment."

    Decay model: stability_new = stability_old · (1 - attrition_per_day)
    ^ days_since_last_seen

    Floored at 0.0; capped at the input value (decay never increases
    stability — that's a learning event, not decay).

    Args:
        current_stability: current identity-stability ∈ [0, 1]
        days_since_last_seen: time since last observation in days
        attrition_per_day: per-day attrition fraction (default 2%)

    Returns decayed identity_stability weight.

    Raises ValueError on out-of-range inputs.
    """
    if not 0.0 <= current_stability <= 1.0:
        raise ValueError(
            f"current_stability must be in [0, 1]; got {current_stability}"
        )
    if days_since_last_seen < 0:
        raise ValueError(
            f"days_since_last_seen must be non-negative; got {days_since_last_seen}"
        )
    if not 0.0 <= attrition_per_day < 1.0:
        raise ValueError(
            f"attrition_per_day must be in [0, 1); got {attrition_per_day}"
        )

    decay_factor = (1.0 - attrition_per_day) ** days_since_last_seen
    decayed = current_stability * decay_factor
    return max(IDENTITY_STABILITY_FLOOR, decayed)


# =============================================================================
# Pydantic models for partner-facing surfacing
# =============================================================================


class HoldoutAssignmentRecord(BaseModel):
    """Record of a holdout assignment for partner audit.

    Stamped on the DecisionTrace (Spine #6) so the partner can inspect
    "this user was in holdout — system did NOT bid; control assignment
    was deterministic via stable hash."
    """

    model_config = ConfigDict(extra="forbid")

    user_id: str
    is_holdout: bool
    holdout_fraction_target: float
    salt_version: str = _HOLDOUT_HASH_SALT
    assigned_at: datetime = Field(default_factory=_now_utc)


class StackAdaptIntegrationStatus(BaseModel):
    """Aggregate health snapshot for the StackAdapt integration.

    Read by the partner dashboard at refresh time. Indicates
    operational health of the signal channel + holdout integrity.
    """

    model_config = ConfigDict(extra="forbid")

    sapid_round_trip_rate: float
    meets_round_trip_target: bool
    n_sapids_resolved: int
    n_sapids_unresolved: int
    holdout_fraction_observed: float = 0.0
    holdout_target: float = DEFAULT_HOLDOUT_FRACTION
    snapshot_at: datetime = Field(default_factory=_now_utc)

    @field_validator("sapid_round_trip_rate")
    @classmethod
    def _validate_rate(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError(f"sapid_round_trip_rate must be in [0, 1]; got {v}")
        return v


def build_status_snapshot(
    monitor: Optional[SapidRoundTripMonitor] = None,
    *,
    holdout_fraction_observed: float = 0.0,
    target: float = DEFAULT_ROUND_TRIP_TARGET,
) -> StackAdaptIntegrationStatus:
    """Build an integration status snapshot from the current monitor."""
    m = monitor or _default_monitor
    return StackAdaptIntegrationStatus(
        sapid_round_trip_rate=m.round_trip_rate(),
        meets_round_trip_target=m.meets_phase_8_target(target=target),
        n_sapids_resolved=m.n_sapids_resolved,
        n_sapids_unresolved=m.n_sapids_unresolved,
        holdout_fraction_observed=holdout_fraction_observed,
        holdout_target=DEFAULT_HOLDOUT_FRACTION,
    )


__all__ = [
    "DEFAULT_COOKIE_ATTRITION_PER_DAY",
    "DEFAULT_HOLDOUT_FRACTION",
    "DEFAULT_ROUND_TRIP_TARGET",
    "HoldoutAssignmentRecord",
    "IDENTITY_STABILITY_FLOOR",
    "SapidRoundTripMonitor",
    "StackAdaptIntegrationStatus",
    "assign_holdout",
    "build_status_snapshot",
    "decay_identity_stability",
    "estimate_holdout_proportion",
    "get_default_monitor",
    "reset_default_monitor",
]
