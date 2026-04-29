# =============================================================================
# ADAM Multi-Horizon Adjudication (task #27)
# Location: adam/intelligence/multi_horizon_adjudication.py
# =============================================================================

"""
MULTI-HORIZON ADJUDICATION — short-horizon vs long-horizon outcome
tracking per HMT foundation §9.5

The pilot's primary endpoint is conversion-rate at impression time.
But Foundation §7 rule 11 names the failure mode: short-horizon CPA
wins can hide long-horizon brand damage. ADAM may "succeed" by
metric while creating exactly the optimization-toward-pressure-tactics
outcome the platform exists to refute.

This substrate tracks outcomes at MULTIPLE TIME HORIZONS so the
adjudicator can flag "won short-horizon, losing long-horizon"
patterns:

  - Day 7 — early-engagement signal (return-visit, repeat-impression
    activity)
  - Day 30 — typical retention horizon for corporate-travel
    bookings
  - Day 60 — long-horizon brand-equity proxy

Each (decision_id, conversion_event) cohort is tracked. When the
horizon passes, the per-cohort return-rate is observable. Comparison
across treatment arms surfaces multi-horizon patterns.

WHAT THIS LANDS

The substrate. Pixel-event ingestion (`record_return_visit`),
horizon-window classification, and the adjudication function that
flags multi-horizon discordance. The actual pixel install is
external — when LUXY's pixel fires return-visit events, they flow
through this substrate.

WHAT THIS DOES NOT LAND

  - The pixel itself (LUXY web team installs)
  - The webhook routing pixel events into record_return_visit
    (depends on the pixel's actual payload shape; trivial wiring
    once the shape is known)
  - The dashboard widget showing horizon-conditional rates
    (consumes this substrate via agency_dashboard aggregator)

DESIGN

Pure substrate: cohort accumulator + horizon-window classification +
adjudication function. No I/O. Tests use synthetic timestamps to
simulate cohort progression through the horizons.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# =============================================================================
# HORIZON CONSTANTS
# =============================================================================


class HorizonWindow(str, Enum):
    """Pre-defined horizon windows for multi-horizon adjudication.

    Day-counts match HMT §9.5 + corporate-travel typical retention
    cycle. A14: HORIZON_WINDOW_DAYS_PILOT_PENDING — pilot data may
    indicate shorter or longer horizons fit LUXY's customer cycle
    better.
    """

    DAY_7 = "day_7"
    DAY_30 = "day_30"
    DAY_60 = "day_60"


HORIZON_DAYS: Dict[HorizonWindow, int] = {
    HorizonWindow.DAY_7: 7,
    HorizonWindow.DAY_30: 30,
    HorizonWindow.DAY_60: 60,
}


# =============================================================================
# COHORT RECORD
# =============================================================================


@dataclass
class ConversionCohort:
    """One conversion's multi-horizon tracking record.

    Created at conversion time. Mutates as return_visit events arrive
    over the horizons. Read-only after Day-60.
    """

    decision_id: str
    user_id: Optional[str]
    treatment_arm: str  # "bilateral" | "control" — drives diagonal analysis
    archetype: Optional[str]
    converted_at: datetime
    return_visit_count_d7: int = 0
    return_visit_count_d30: int = 0
    return_visit_count_d60: int = 0
    last_return_visit_at: Optional[datetime] = None

    def days_since_conversion(self, now: datetime) -> int:
        """Days elapsed since this cohort's conversion."""
        delta = now - self.converted_at
        return delta.days

    def is_horizon_complete(
        self, horizon: HorizonWindow, now: datetime,
    ) -> bool:
        """True iff the horizon's window has elapsed."""
        return self.days_since_conversion(now) >= HORIZON_DAYS[horizon]

    def returned_within(
        self, horizon: HorizonWindow,
    ) -> bool:
        """True iff at least one return visit landed within the horizon
        window."""
        return self._count_for_horizon(horizon) > 0

    def _count_for_horizon(self, horizon: HorizonWindow) -> int:
        if horizon == HorizonWindow.DAY_7:
            return self.return_visit_count_d7
        if horizon == HorizonWindow.DAY_30:
            return self.return_visit_count_d30
        if horizon == HorizonWindow.DAY_60:
            return self.return_visit_count_d60
        raise ValueError(f"Unknown horizon: {horizon}")


# =============================================================================
# ACCUMULATOR
# =============================================================================


class MultiHorizonAdjudicator:
    """Tracks cohorts + computes per-arm return rates at each horizon.

    Production wiring:
      1. OutcomeHandler.process_outcome creates a ConversionCohort
         when outcome_type=conversion.
      2. LUXY pixel events for return visits route to
         record_return_visit(user_id, visited_at) which finds the
         user's cohorts and increments the appropriate horizon counter.
      3. At reporting time, compute_horizon_return_rates(now) gives
         per-arm rates at each horizon.
    """

    def __init__(self) -> None:
        self._cohorts_by_id: Dict[str, ConversionCohort] = {}
        self._cohorts_by_user: Dict[str, List[ConversionCohort]] = {}

    # ---- registration ----

    def register_conversion(
        self,
        decision_id: str,
        treatment_arm: str,
        converted_at: datetime,
        *,
        user_id: Optional[str] = None,
        archetype: Optional[str] = None,
    ) -> ConversionCohort:
        """Register a conversion for multi-horizon tracking.

        Idempotent on decision_id — re-registering returns the existing
        cohort (subsequent calls don't reset counters).
        """
        if decision_id in self._cohorts_by_id:
            return self._cohorts_by_id[decision_id]
        cohort = ConversionCohort(
            decision_id=decision_id,
            user_id=user_id,
            treatment_arm=treatment_arm,
            archetype=archetype,
            converted_at=converted_at,
        )
        self._cohorts_by_id[decision_id] = cohort
        if user_id:
            self._cohorts_by_user.setdefault(user_id, []).append(cohort)
        return cohort

    def record_return_visit(
        self,
        user_id: str,
        visited_at: datetime,
    ) -> int:
        """Record a return-visit event for a user.

        Updates all of the user's tracked cohorts: increments the
        horizon-specific counter for any cohort whose horizon window
        the visit falls within.

        Returns the number of cohort-counters that were incremented.
        Zero when the user has no tracked cohorts or all cohort
        horizons have already passed.
        """
        cohorts = self._cohorts_by_user.get(user_id, [])
        if not cohorts:
            return 0

        n_updated = 0
        for cohort in cohorts:
            days_after = (visited_at - cohort.converted_at).days
            if days_after < 0:
                continue  # visit before conversion — ignore
            if days_after <= HORIZON_DAYS[HorizonWindow.DAY_7]:
                cohort.return_visit_count_d7 += 1
                n_updated += 1
            if days_after <= HORIZON_DAYS[HorizonWindow.DAY_30]:
                cohort.return_visit_count_d30 += 1
                n_updated += 1
            if days_after <= HORIZON_DAYS[HorizonWindow.DAY_60]:
                cohort.return_visit_count_d60 += 1
                n_updated += 1
            if cohort.last_return_visit_at is None or visited_at > cohort.last_return_visit_at:
                cohort.last_return_visit_at = visited_at
        return n_updated

    # ---- queries ----

    def get_cohort(self, decision_id: str) -> Optional[ConversionCohort]:
        return self._cohorts_by_id.get(decision_id)

    def all_cohorts(self) -> List[ConversionCohort]:
        return list(self._cohorts_by_id.values())

    # ---- horizon-conditional rates ----

    def compute_horizon_return_rates(
        self,
        now: datetime,
    ) -> Dict[Tuple[str, HorizonWindow], Dict[str, Any]]:
        """Compute per-(arm, horizon) return rates.

        Only includes cohorts whose horizon window has fully elapsed
        as of `now` — prevents biased "early returners only" rates.

        Returns:
            dict mapping (treatment_arm, horizon) → {
                "n_cohorts": int,
                "n_returned": int,
                "return_rate": float,
            }
        """
        result: Dict[Tuple[str, HorizonWindow], Dict[str, Any]] = {}

        for horizon in HorizonWindow:
            # Group eligible cohorts by treatment_arm
            by_arm: Dict[str, Tuple[int, int]] = {}  # arm → (n_cohorts, n_returned)
            for cohort in self._cohorts_by_id.values():
                if not cohort.is_horizon_complete(horizon, now):
                    continue
                arm = cohort.treatment_arm
                n_cohorts, n_returned = by_arm.get(arm, (0, 0))
                n_cohorts += 1
                if cohort.returned_within(horizon):
                    n_returned += 1
                by_arm[arm] = (n_cohorts, n_returned)

            for arm, (n_cohorts, n_returned) in by_arm.items():
                rate = n_returned / n_cohorts if n_cohorts else 0.0
                result[(arm, horizon)] = {
                    "n_cohorts": n_cohorts,
                    "n_returned": n_returned,
                    "return_rate": rate,
                }
        return result

    # ---- ADJUDICATION — the load-bearing function ----

    def adjudicate(
        self,
        now: datetime,
        *,
        treatment_arm: str = "bilateral",
        control_arm: str = "control",
        min_cohorts_per_arm: int = 30,
    ) -> Dict[str, Any]:
        """The adjudication test for multi-horizon discordance.

        Foundation §7 rule 11 + HMT §9.5 specifies: a treatment arm
        that wins on short horizon but loses on long horizon is
        producing exactly the optimization-toward-pressure-tactics
        outcome the platform exists to refute.

        This function computes the differential between arms at each
        horizon and returns:

        - per-horizon arm rates
        - per-horizon absolute lift (treatment - control)
        - "discordance_detected": True iff treatment beats control on
          the EARLIEST horizon but loses on the LATEST horizon (with
          sufficient sample size at both)
        - interpretive_note templated from the data

        At pilot N, the discordance signal is what catches the
        ethical-failure mode. Adjudicator runs at flight close;
        result feeds the pre-registered analysis plan's secondary
        endpoint #3.
        """
        rates = self.compute_horizon_return_rates(now)

        per_horizon: Dict[str, Dict[str, Any]] = {}
        for horizon in HorizonWindow:
            t_data = rates.get((treatment_arm, horizon))
            c_data = rates.get((control_arm, horizon))
            entry: Dict[str, Any] = {
                "horizon": horizon.value,
                "treatment_n": t_data["n_cohorts"] if t_data else 0,
                "treatment_return_rate": t_data["return_rate"] if t_data else None,
                "control_n": c_data["n_cohorts"] if c_data else 0,
                "control_return_rate": c_data["return_rate"] if c_data else None,
                "absolute_lift": None,
                "sufficient_n": False,
            }
            if t_data and c_data:
                entry["absolute_lift"] = (
                    t_data["return_rate"] - c_data["return_rate"]
                )
                entry["sufficient_n"] = (
                    t_data["n_cohorts"] >= min_cohorts_per_arm
                    and c_data["n_cohorts"] >= min_cohorts_per_arm
                )
            per_horizon[horizon.value] = entry

        # Discordance test — earliest vs latest horizon with sufficient N
        d7 = per_horizon[HorizonWindow.DAY_7.value]
        d60 = per_horizon[HorizonWindow.DAY_60.value]

        discordance_detected = False
        discordance_note = ""

        if d7["sufficient_n"] and d60["sufficient_n"]:
            # Treatment won early AND lost late → discordance
            won_early = d7["absolute_lift"] is not None and d7["absolute_lift"] > 0
            lost_late = d60["absolute_lift"] is not None and d60["absolute_lift"] < 0
            if won_early and lost_late:
                discordance_detected = True
                discordance_note = (
                    f"DISCORDANCE: treatment beat control at Day 7 "
                    f"(lift={d7['absolute_lift']:+.4f}) but LOSES at "
                    f"Day 60 (lift={d60['absolute_lift']:+.4f}). "
                    f"This is the Foundation §7 rule 11 failure mode — "
                    f"short-horizon win hides long-horizon damage."
                )
            elif won_early and d60["absolute_lift"] is not None and d60["absolute_lift"] > 0:
                discordance_note = (
                    "Aligned: treatment wins at both Day 7 and Day 60 "
                    "horizons — no multi-horizon discordance."
                )
            elif (
                d7["absolute_lift"] is not None
                and d7["absolute_lift"] < 0
                and d60["absolute_lift"] is not None
                and d60["absolute_lift"] < 0
            ):
                discordance_note = (
                    "Aligned negative: treatment loses at both horizons. "
                    "No multi-horizon discordance, but the primary "
                    "result is unfavorable."
                )
            else:
                discordance_note = (
                    "Mixed signal: directionality varies by horizon "
                    "without clean discordance. Investigate per-archetype."
                )
        else:
            discordance_note = (
                f"Insufficient cohorts per arm at Day 7 (t={d7['treatment_n']}, "
                f"c={d7['control_n']}) or Day 60 (t={d60['treatment_n']}, "
                f"c={d60['control_n']}); minimum {min_cohorts_per_arm} per arm "
                f"required for discordance test."
            )

        return {
            "per_horizon": per_horizon,
            "discordance_detected": discordance_detected,
            "discordance_note": discordance_note,
            "min_cohorts_per_arm": min_cohorts_per_arm,
            "evaluated_at": now.isoformat(),
        }

    def reset(self) -> None:
        """Test-only — clear all state."""
        self._cohorts_by_id.clear()
        self._cohorts_by_user.clear()


# =============================================================================
# Singleton
# =============================================================================


_adjudicator: Optional[MultiHorizonAdjudicator] = None


def get_multi_horizon_adjudicator() -> MultiHorizonAdjudicator:
    global _adjudicator
    if _adjudicator is None:
        _adjudicator = MultiHorizonAdjudicator()
    return _adjudicator


def reset_multi_horizon_adjudicator() -> None:
    """Test-only — clear the singleton."""
    global _adjudicator
    _adjudicator = None


__all__ = [
    "ConversionCohort",
    "HORIZON_DAYS",
    "HorizonWindow",
    "MultiHorizonAdjudicator",
    "get_multi_horizon_adjudicator",
    "reset_multi_horizon_adjudicator",
]
