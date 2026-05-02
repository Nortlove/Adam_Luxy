# =============================================================================
# Phase 9 simulation — synthetic world (impressions + outcomes)
# Location: adam/intelligence/simulation/world.py
# =============================================================================
"""Stochastic world that simulates impressions + outcomes for the
SimulationConfig.

The world is the ground-truth environment: given a (user, mechanism,
context) tuple from the architecture under test, the world samples a
binary outcome (clicked-and-converted) using the user's TRUE per-
mechanism efficacy plus the configured non-stationarity regime.

Architectures only see ``(user_id, mechanism_sent, outcome)`` tuples;
they do NOT see the true efficacy. The lift each architecture earns
over the baseline is its measured value.

NON-STATIONARITY

  * STATIONARY: efficacy is constant.
  * SLOW_DRIFT: efficacy drifts linearly over the horizon
    (multiplicative AR(1) random walk with small step variance).
  * ABRUPT_SWITCHING: efficacy jumps at a fixed midpoint of the
    horizon (cohort-fingerprint shuffles).

CARRYOVER (TRUE generative process)

When the user has a recent prior touch on the same mechanism, the
world reduces the next-touch efficacy by ρ × prior_residual_effect ×
exp(-Δ/τ). This is the TRUE carryover Architecture C+ tries to
estimate.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from adam.intelligence.simulation.config import (
    NonStationarityRegime,
    SimulationConfig,
)
from adam.intelligence.simulation.population import (
    SyntheticPopulation,
    SyntheticUser,
)


@dataclass(frozen=True)
class Impression:
    """One simulated impression — what the world delivers to the
    architecture under test."""

    impression_id: str
    user_id: str
    week: int
    hour_of_horizon: float


@dataclass(frozen=True)
class Outcome:
    """One simulated outcome — what the world reports back after the
    architecture chose a mechanism."""

    impression_id: str
    user_id: str
    week: int
    hour_of_horizon: float
    mechanism_sent: str
    converted: bool


# =============================================================================
# World
# =============================================================================


# Carryover decay constant (hours) for the world's true generative
# process. Matches the order of magnitude of mechanism washout half-
# lives (~24-72h); chosen as 24h for the simplest stable curve.
_TRUE_CARRYOVER_TAU_HOURS: float = 24.0


class SyntheticWorld:
    """Ground-truth world over the SyntheticPopulation."""

    def __init__(self, population: SyntheticPopulation):
        self.population = population
        self.config = population.config
        self._rng = random.Random(int(self.config.seed) + 7919)
        # Per-user history: (week, hour, mechanism, converted)
        self._touch_history: Dict[
            str, List[Tuple[int, float, str, bool]]
        ] = {}
        # Switching fingerprint (used by ABRUPT_SWITCHING).
        self._post_switch_offsets: Dict[
            int, Dict[str, float]
        ] = {}
        if self.config.non_stationarity == (
            NonStationarityRegime.ABRUPT_SWITCHING
        ):
            self._build_post_switch_fingerprints()

    def _build_post_switch_fingerprints(self) -> None:
        for c in range(self.population.n_cohorts):
            self._post_switch_offsets[c] = {
                m: self._rng.gauss(0.0, 1.0)
                for m in self.population.mechanisms
            }

    def _drift_factor(self, week: int) -> float:
        """Drift multiplier applied uniformly across mechanisms.
        Exact formula by regime:
          - STATIONARY → 1.0
          - SLOW_DRIFT → 1 + 0.02 * week (≤ ±10% over 6 weeks)
          - ABRUPT_SWITCHING → 1.0 (handled via post-switch offsets)
        """
        if self.config.non_stationarity == NonStationarityRegime.SLOW_DRIFT:
            return 1.0 + 0.02 * float(week)
        return 1.0

    def _post_switch_efficacy(
        self, user: SyntheticUser, mechanism: str,
    ) -> float:
        """ABRUPT_SWITCHING: at the midpoint of the horizon, the
        cohort fingerprints shuffle. Efficacy = baseline × (1 +
        post_switch_offset)."""
        baseline = (
            self.config.user_base_ctr
            * self.config.conversion_rate_given_click
        )
        offset = self._post_switch_offsets.get(
            user.cohort_id, {},
        ).get(mechanism, 0.0)
        eff = baseline * (1.0 + offset)
        return max(1e-4, min(0.5, eff))

    def true_efficacy(
        self, user: SyntheticUser, mechanism: str, week: int,
    ) -> float:
        """Resolve TRUE per-touch efficacy at this (user, mech, week)."""
        if (
            self.config.non_stationarity ==
            NonStationarityRegime.ABRUPT_SWITCHING
            and week >= max(1, self.config.horizon_weeks // 2)
        ):
            return self._post_switch_efficacy(user, mechanism)

        eff = user.true_mechanism_efficacy.get(mechanism, 0.0)
        eff = eff * self._drift_factor(week)
        return max(1e-4, min(0.5, eff))

    def _compute_carryover_residual(
        self, user: SyntheticUser, mechanism: str,
        week: int, hour_of_horizon: float,
    ) -> float:
        """Apply true carryover for the same-mechanism prior touch."""
        history = self._touch_history.get(user.user_id, [])
        if not history:
            return 0.0
        # Most-recent touch on the SAME mechanism.
        for w, h, m, _converted in reversed(history):
            if m == mechanism:
                # Hours since.
                delta_h = (week - w) * 168.0 + (hour_of_horizon - h)
                if delta_h <= 0:
                    return 0.0
                decay = math.exp(-delta_h / _TRUE_CARRYOVER_TAU_HOURS)
                # ρ × prior_efficacy × decay (negative residual = lower
                # next-touch efficacy because the user has just been
                # primed).
                prior_eff = user.true_mechanism_efficacy.get(
                    mechanism, 0.0,
                )
                return user.true_carryover_rho * prior_eff * decay
        return 0.0

    def stream_impressions(self) -> List[Impression]:
        """Generate the full impression stream for the configured
        horizon. Each user gets ``impression_rate_per_user_per_week
        × horizon_weeks`` impressions, distributed roughly evenly
        across the horizon hours."""
        impressions: List[Impression] = []
        total_hours = self.config.horizon_weeks * 168.0
        ix = 0
        for user in self.population.users:
            n_impressions = (
                self.config.impression_rate_per_user_per_week
                * self.config.horizon_weeks
            )
            # Spread impressions roughly uniformly over the horizon.
            for k in range(n_impressions):
                # Jittered uniform spacing.
                base_hour = (k + 0.5) * total_hours / max(1, n_impressions)
                jitter = self._rng.uniform(-2.0, 2.0)
                hour = max(0.0, min(total_hours - 0.001, base_hour + jitter))
                week = int(hour // 168.0)
                impressions.append(Impression(
                    impression_id=f"imp-{ix:09d}",
                    user_id=user.user_id,
                    week=week,
                    hour_of_horizon=hour,
                ))
                ix += 1
        # Shuffle so architectures don't see all of one user's
        # impressions in a row (more realistic + necessary for
        # online-learning architectures).
        self._rng.shuffle(impressions)
        # Re-sort by hour_of_horizon so the stream is monotonic in
        # time (architectures expect time-ordered impressions).
        impressions.sort(key=lambda x: x.hour_of_horizon)
        return impressions

    def deliver_outcome(
        self,
        impression: Impression,
        mechanism_sent: str,
    ) -> Outcome:
        """Architecture chose ``mechanism_sent``; world samples the
        outcome from the TRUE efficacy + carryover residual."""
        user = next(
            (u for u in self.population.users if u.user_id == impression.user_id),
            None,
        )
        if user is None:
            converted = False
        else:
            true_eff = self.true_efficacy(
                user, mechanism_sent, impression.week,
            )
            residual = self._compute_carryover_residual(
                user, mechanism_sent,
                impression.week, impression.hour_of_horizon,
            )
            # Subtract residual (positive ρ + recent same-mech touch
            # → reduced next-touch efficacy because the user is
            # already primed). Clipped at 0.
            effective_eff = max(0.0, true_eff - max(0.0, residual))
            converted = self._rng.random() < effective_eff
            self._touch_history.setdefault(user.user_id, []).append(
                (impression.week, impression.hour_of_horizon,
                 mechanism_sent, converted),
            )
            # Bound history to last 100 touches per user (memory).
            if len(self._touch_history[user.user_id]) > 100:
                self._touch_history[user.user_id] = (
                    self._touch_history[user.user_id][-100:]
                )
        return Outcome(
            impression_id=impression.impression_id,
            user_id=impression.user_id,
            week=impression.week,
            hour_of_horizon=impression.hour_of_horizon,
            mechanism_sent=mechanism_sent,
            converted=converted,
        )
