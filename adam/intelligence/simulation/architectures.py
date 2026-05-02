# =============================================================================
# Phase 9 simulation — architectures under test
# Location: adam/intelligence/simulation/architectures.py
# =============================================================================
"""Architecture Protocol + Architecture A baseline.

Per directive Appendix A lines 1159-1164 the simulation compares 5
architectures:

  A: marginal additive scoring (baseline) — this slice
  B: trilateral cascade only (Spine #4) — sibling slice
  C: trilateral + interaction model (Spine #4 + #1's δ_iac) — sibling
  D: full proposed stack (Spines #1, #2, #4, #5, #7) — sibling
  E: D + counterfactual logging (D + Spine #6) — sibling

Each architecture sees the impression stream + (impression, mechanism,
outcome) feedback. The base interface is intentionally minimal so v3
Phase 1 wrappers can register additional architectures without
touching the runner.
"""

from __future__ import annotations

import random
from collections import defaultdict
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

from adam.intelligence.simulation.population import (
    SyntheticPopulation,
    SyntheticUser,
)
from adam.intelligence.simulation.world import (
    Impression,
    Outcome,
)


@runtime_checkable
class Architecture(Protocol):
    """One architecture under test.

    Lifecycle:
      1. ``configure(population)`` — once, before the impression stream.
      2. ``select_mechanism(impression) -> str`` — once per impression
         (online).
      3. ``record_outcome(outcome)`` — once per impression after the
         world reports the outcome.

    The architecture is responsible for any internal posterior /
    bandit / cascade state. It MAY use the population's mechanisms list
    but it MUST NOT inspect ``population.users[i].true_mechanism_efficacy``
    (the simulation enforces this by contract; tests verify).
    """

    name: str

    def configure(self, population: SyntheticPopulation) -> None: ...

    def select_mechanism(self, impression: Impression) -> str: ...

    def record_outcome(self, outcome: Outcome) -> None: ...


# =============================================================================
# Architecture A — marginal additive baseline (per directive line 1160)
# =============================================================================


class MarginalAdditiveBaseline:
    """Architecture A — marginal additive scoring.

    Per directive line 1160 ("marginal additive scoring (baseline)").
    The architecture maintains:
      * A per-mechanism running mean conversion rate (no per-user
        personalization).
      * Selection: epsilon-greedy with ε = 0.1 over the per-mechanism
        means; cold-start uniform.

    No cascade, no per-user posterior, no carryover model. This is the
    deliberately impoverished baseline against which Architectures
    B-E demonstrate marginal contribution.
    """

    name: str = "A_marginal_additive"

    def __init__(self, *, epsilon: float = 0.10, seed: int = 0):
        self.epsilon = float(epsilon)
        self._rng = random.Random(int(seed))
        self._mechanisms: List[str] = []
        self._mech_n: Dict[str, int] = defaultdict(int)
        self._mech_conversions: Dict[str, int] = defaultdict(int)

    def configure(self, population: SyntheticPopulation) -> None:
        self._mechanisms = list(population.mechanisms)
        # Reset state at configure time so a single instance can be
        # re-used across simulation cells without leakage.
        self._mech_n = defaultdict(int)
        self._mech_conversions = defaultdict(int)

    def _mean_conversion(self, mechanism: str) -> float:
        n = self._mech_n[mechanism]
        if n == 0:
            return 0.0
        return self._mech_conversions[mechanism] / float(n)

    def select_mechanism(self, impression: Impression) -> str:
        if not self._mechanisms:
            raise RuntimeError(
                "MarginalAdditiveBaseline.select_mechanism called "
                "before configure()"
            )
        # Cold-start (any mechanism untried) — pick uniformly to
        # establish initial estimates.
        untried = [
            m for m in self._mechanisms if self._mech_n[m] == 0
        ]
        if untried:
            return self._rng.choice(untried)

        # ε-greedy
        if self._rng.random() < self.epsilon:
            return self._rng.choice(self._mechanisms)

        best_m = self._mechanisms[0]
        best_v = self._mean_conversion(best_m)
        for m in self._mechanisms[1:]:
            v = self._mean_conversion(m)
            if v > best_v:
                best_v = v
                best_m = m
        return best_m

    def record_outcome(self, outcome: Outcome) -> None:
        self._mech_n[outcome.mechanism_sent] += 1
        if outcome.converted:
            self._mech_conversions[outcome.mechanism_sent] += 1
