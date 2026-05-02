# =============================================================================
# Phase 9 simulation — config schema
# Location: adam/intelligence/simulation/config.py
# =============================================================================
"""SimulationConfig + canonical grid values per directive Appendix A
lines 1150-1157.

Every variable below uses the directive's exact enumerated values so
the full-factorial / LHS sweeps reproduce the named architecture
comparisons exactly.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Tuple


# =============================================================================
# Directive Appendix A grid values — frozen
# =============================================================================


# User base CTR (per directive line 1151).
CTR_GRID: Tuple[float, ...] = (0.0005, 0.0015, 0.005)  # 0.05%, 0.15%, 0.5%


# Conversion rate given click (per directive line 1152).
CONVERSION_RATE_GRID: Tuple[float, ...] = (0.005, 0.02, 0.05)


# Per-user impression rate per WEEK (per directive line 1157).
IMPRESSION_RATE_GRID: Tuple[int, ...] = (2, 7, 20)


# Audience size per cohort (per directive line 1156).
AUDIENCE_SIZE_GRID: Tuple[int, ...] = (500, 2_000, 10_000)


class InteractionStrength(str, Enum):
    """True trait × state × context interaction strength
    (per directive line 1153)."""
    NONE = "none"
    WEAK = "weak"
    MODERATE = "moderate"
    STRONG = "strong"


class CohortSeparation(str, Enum):
    """Cohort separation regime (per directive line 1154)."""
    INDISTINGUISHABLE = "indistinguishable"
    WEAKLY_SEPARABLE = "weakly_separable"
    STRONGLY_SEPARABLE = "strongly_separable"


class NonStationarityRegime(str, Enum):
    """Non-stationarity regime (per directive line 1155)."""
    STATIONARY = "stationary"
    SLOW_DRIFT = "slow_drift"
    ABRUPT_SWITCHING = "abrupt_switching"


# Horizons in weeks (per directive line 1166).
HORIZON_WEEKS_GRID: Tuple[int, ...] = (2, 4, 6)


@dataclass(frozen=True)
class SimulationConfig:
    """One cell in the Appendix A simulation sweep.

    All seven variables from the directive are first-class slots.
    Construction is type-safe; consumers should validate against the
    canonical grids when building a sweep.
    """

    user_base_ctr: float
    conversion_rate_given_click: float
    interaction_strength: InteractionStrength
    cohort_separation: CohortSeparation
    non_stationarity: NonStationarityRegime
    audience_size_per_cohort: int
    impression_rate_per_user_per_week: int
    horizon_weeks: int = 2  # default to the smaller of the 5-arch × 2-horizon
                            # subset named in the wrap-out hard-stop criterion.
    n_cohorts: int = 4      # default cohort count for synthetic population.
    n_mechanisms: int = 5   # default mechanism action space.
    seed: int = 0           # determinism for reproducible runs.


def is_canonical_value(*, attr: str, value: object) -> bool:
    """True iff the value is one of the canonical grid values for the
    named SimulationConfig attribute. Used by sweep builders to
    validate inputs against the directive's enumerated grids."""
    if attr == "user_base_ctr":
        return value in CTR_GRID
    if attr == "conversion_rate_given_click":
        return value in CONVERSION_RATE_GRID
    if attr == "impression_rate_per_user_per_week":
        return value in IMPRESSION_RATE_GRID
    if attr == "audience_size_per_cohort":
        return value in AUDIENCE_SIZE_GRID
    if attr == "horizon_weeks":
        return value in HORIZON_WEEKS_GRID
    if attr == "interaction_strength":
        return isinstance(value, InteractionStrength) or (
            isinstance(value, str)
            and value in {e.value for e in InteractionStrength}
        )
    if attr == "cohort_separation":
        return isinstance(value, CohortSeparation) or (
            isinstance(value, str)
            and value in {e.value for e in CohortSeparation}
        )
    if attr == "non_stationarity":
        return isinstance(value, NonStationarityRegime) or (
            isinstance(value, str)
            and value in {e.value for e in NonStationarityRegime}
        )
    return False
