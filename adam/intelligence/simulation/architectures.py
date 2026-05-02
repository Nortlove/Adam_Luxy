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

import math
import random
from collections import defaultdict
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable, Tuple

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


# =============================================================================
# Architecture B — trilateral cascade only (per directive line 1161)
# =============================================================================


class TrilateralCascadeOnly:
    """Architecture B — Spine #4 trilateral cascade scoring without
    interaction tensor.

    Per directive Appendix A line 1161 ("trilateral cascade only
    (Spine #4)"). The architecture scores each (user, mechanism)
    pair using:

        score(u, m) = w_user · ratehat(u, m) + w_cohort · ratehat(c(u), m)

    where:
      * ratehat(u, m) is the user × mechanism Laplace-smoothed
        running conversion rate (Beta(1,1) prior baked in).
      * ratehat(c(u), m) is the cohort × mechanism rate for the
        user's cohort. The cohort signal is the Spine #4 "context-
        conditioning" surrogate in the simulation (cohort_id stands
        in for page-attentional-posture / archetype context).
      * w_user + w_cohort = 1; default 0.5 / 0.5.

    The architecture has NO per-(user × cohort × mechanism)
    interaction term — that's Architecture C's differentiator
    (Spine #1's δ_iac). The additive composition is the "trilateral
    cascade only" scope boundary per the wrap-out scope guard.

    Cold-start: any (cohort, mechanism) cell with zero observations
    forces exploration on that cell for the cohort's next impression.
    Once the cohort has touched every mechanism at least once,
    selection switches to ε-greedy over the additive score.

    Selection is ε-greedy with default ε=0.10 — same exploration
    rate as Architecture A so the comparison isolates SCORING
    sophistication, not exploration policy.
    """

    name: str = "B_trilateral_cascade_only"

    def __init__(
        self,
        *,
        epsilon: float = 0.10,
        w_user: float = 0.5,
        w_cohort: float = 0.5,
        seed: int = 0,
    ):
        self.epsilon = float(epsilon)
        if w_user + w_cohort <= 0:
            raise ValueError("w_user + w_cohort must be positive")
        total = w_user + w_cohort
        self.w_user = float(w_user) / total
        self.w_cohort = float(w_cohort) / total
        self._rng = random.Random(int(seed))
        self._mechanisms: List[str] = []
        self._user_cohort: Dict[str, int] = {}
        self._user_mech_n: Dict[tuple, int] = defaultdict(int)
        self._user_mech_conv: Dict[tuple, int] = defaultdict(int)
        self._cohort_mech_n: Dict[tuple, int] = defaultdict(int)
        self._cohort_mech_conv: Dict[tuple, int] = defaultdict(int)

    def configure(self, population: SyntheticPopulation) -> None:
        self._mechanisms = list(population.mechanisms)
        self._user_cohort = {
            u.user_id: u.cohort_id for u in population.users
        }
        # Reset accumulator state — single instance can be re-used.
        self._user_mech_n = defaultdict(int)
        self._user_mech_conv = defaultdict(int)
        self._cohort_mech_n = defaultdict(int)
        self._cohort_mech_conv = defaultdict(int)

    def _user_mech_rate(self, user_id: str, mechanism: str) -> float:
        """Laplace-smoothed user × mechanism rate."""
        key = (user_id, mechanism)
        return (
            (1 + self._user_mech_conv[key])
            / float(2 + self._user_mech_n[key])
        )

    def _cohort_mech_rate(self, cohort_id: int, mechanism: str) -> float:
        """Laplace-smoothed cohort × mechanism rate."""
        key = (cohort_id, mechanism)
        return (
            (1 + self._cohort_mech_conv[key])
            / float(2 + self._cohort_mech_n[key])
        )

    def _trilateral_score(
        self, user_id: str, mechanism: str,
    ) -> float:
        """Trilateral additive score: user signal + cohort signal.
        NO (user × cohort × mechanism) interaction term — that's
        Architecture C."""
        cohort = self._user_cohort.get(user_id, -1)
        return (
            self.w_user * self._user_mech_rate(user_id, mechanism)
            + self.w_cohort * self._cohort_mech_rate(cohort, mechanism)
        )

    def select_mechanism(self, impression: Impression) -> str:
        if not self._mechanisms:
            raise RuntimeError(
                "TrilateralCascadeOnly.select_mechanism called "
                "before configure()"
            )

        cohort = self._user_cohort.get(impression.user_id, -1)
        # Cold-start: cohort × mechanism cell with zero observations
        # forces exploration. After every mechanism has been touched
        # for this cohort at least once, switch to ε-greedy.
        cohort_untried = [
            m for m in self._mechanisms
            if self._cohort_mech_n[(cohort, m)] == 0
        ]
        if cohort_untried:
            return self._rng.choice(cohort_untried)

        if self._rng.random() < self.epsilon:
            return self._rng.choice(self._mechanisms)

        best_m = self._mechanisms[0]
        best_v = self._trilateral_score(impression.user_id, best_m)
        for m in self._mechanisms[1:]:
            v = self._trilateral_score(impression.user_id, m)
            if v > best_v:
                best_v = v
                best_m = m
        return best_m

    def record_outcome(self, outcome: Outcome) -> None:
        m = outcome.mechanism_sent
        u = outcome.user_id
        c = self._user_cohort.get(u, -1)
        self._user_mech_n[(u, m)] += 1
        self._cohort_mech_n[(c, m)] += 1
        if outcome.converted:
            self._user_mech_conv[(u, m)] += 1
            self._cohort_mech_conv[(c, m)] += 1


# =============================================================================
# Architecture C — trilateral + interaction model (per directive line 1162)
# Architecture D — full proposed stack (per directive line 1163)
# =============================================================================


class TrilateralWithInteraction:
    """Architecture C — Spine #4 trilateral cascade + Spine #1's
    δ_iac interaction tensor.

    Per directive Appendix A line 1162 ("trilateral + interaction
    model (Spine #4 + Spine #1's δ_iac)") + directive Section 2
    likelihood lines 466-477:

        η_iat = θ_i + β_a + γ_c + δ_iac + drift_t + carryover_t

    where δ_iac is the per-(individual i, action a, context c)
    interaction cell. Architecture C's differentiator over B: B
    uses a FIXED additive weight between user and cohort signals;
    C uses Bayesian shrinkage so the per-(user, mechanism) cell
    signal (the interaction proxy) earns more weight as data
    accumulates.

    Shrinkage formula:
        weight_user(u, m) = n_user(u, m) / (n_user(u, m) + κ)
        score_C(u, m) = weight_user × ratehat(u, m)
                      + (1 - weight_user) × ratehat(c(u), m)

    where κ is the shrinkage hyperparameter (default 20). This is
    the partial-pooling formalization of the interaction tensor in
    additive bandits: when n_user → 0 the score collapses to the
    cohort prior (B-like at cold-start); when n_user → ∞ the score
    captures the per-(user, mechanism) cell fully (the interaction
    captured at high-data limit).

    The architecture has NO carryover correction (Architecture D's
    differentiator) and NO counterfactual logging (Architecture E's
    differentiator).
    """

    name: str = "C_trilateral_plus_interaction"

    def __init__(
        self,
        *,
        epsilon: float = 0.10,
        shrinkage_kappa: float = 20.0,
        seed: int = 0,
    ):
        if shrinkage_kappa <= 0:
            raise ValueError("shrinkage_kappa must be positive")
        self.epsilon = float(epsilon)
        self.shrinkage_kappa = float(shrinkage_kappa)
        self._rng = random.Random(int(seed))
        self._mechanisms: List[str] = []
        self._user_cohort: Dict[str, int] = {}
        self._user_mech_n: Dict[tuple, int] = defaultdict(int)
        self._user_mech_conv: Dict[tuple, int] = defaultdict(int)
        self._cohort_mech_n: Dict[tuple, int] = defaultdict(int)
        self._cohort_mech_conv: Dict[tuple, int] = defaultdict(int)

    def configure(self, population: SyntheticPopulation) -> None:
        self._mechanisms = list(population.mechanisms)
        self._user_cohort = {
            u.user_id: u.cohort_id for u in population.users
        }
        self._user_mech_n = defaultdict(int)
        self._user_mech_conv = defaultdict(int)
        self._cohort_mech_n = defaultdict(int)
        self._cohort_mech_conv = defaultdict(int)

    def _user_mech_rate(self, user_id: str, mechanism: str) -> float:
        key = (user_id, mechanism)
        return (
            (1 + self._user_mech_conv[key])
            / float(2 + self._user_mech_n[key])
        )

    def _cohort_mech_rate(self, cohort_id: int, mechanism: str) -> float:
        key = (cohort_id, mechanism)
        return (
            (1 + self._cohort_mech_conv[key])
            / float(2 + self._cohort_mech_n[key])
        )

    def shrinkage_weight(self, user_id: str, mechanism: str) -> float:
        """Bayesian shrinkage weight on the per-(user, mechanism)
        cell. Public for diagnostic surfaces + tests."""
        n_user = self._user_mech_n[(user_id, mechanism)]
        return float(n_user) / (float(n_user) + self.shrinkage_kappa)

    def _interaction_score(self, user_id: str, mechanism: str) -> float:
        """Shrinkage-weighted user × mechanism interaction signal."""
        cohort = self._user_cohort.get(user_id, -1)
        weight_user = self.shrinkage_weight(user_id, mechanism)
        return (
            weight_user * self._user_mech_rate(user_id, mechanism)
            + (1.0 - weight_user)
            * self._cohort_mech_rate(cohort, mechanism)
        )

    def select_mechanism(self, impression: Impression) -> str:
        if not self._mechanisms:
            raise RuntimeError(
                "TrilateralWithInteraction.select_mechanism called "
                "before configure()"
            )

        cohort = self._user_cohort.get(impression.user_id, -1)
        cohort_untried = [
            m for m in self._mechanisms
            if self._cohort_mech_n[(cohort, m)] == 0
        ]
        if cohort_untried:
            return self._rng.choice(cohort_untried)

        if self._rng.random() < self.epsilon:
            return self._rng.choice(self._mechanisms)

        best_m = self._mechanisms[0]
        best_v = self._interaction_score(impression.user_id, best_m)
        for m in self._mechanisms[1:]:
            v = self._interaction_score(impression.user_id, m)
            if v > best_v:
                best_v = v
                best_m = m
        return best_m

    def record_outcome(self, outcome: Outcome) -> None:
        m = outcome.mechanism_sent
        u = outcome.user_id
        c = self._user_cohort.get(u, -1)
        self._user_mech_n[(u, m)] += 1
        self._cohort_mech_n[(c, m)] += 1
        if outcome.converted:
            self._user_mech_conv[(u, m)] += 1
            self._cohort_mech_conv[(c, m)] += 1


# =============================================================================
# Architecture D — full proposed stack (per directive line 1163)
# =============================================================================


class FullProposedStack:
    """Architecture D — Spines #1, #2, #4, #5, #7 composed.

    Per directive Appendix A line 1163. Differentiators over C:

      * Spine #1 full-Bayesian: Thompson Sampling on Beta(α, β)
        posteriors instead of ε-greedy on point estimates.
      * Spine #2: AR(1) carryover correction at decision time —
        score - ρ × posterior_mean(m_prev) × exp(-Δ/τ) when a
        same-mechanism touch occurred within τ.

    Spine #4 trilateral cascade scoring is inherited (shrinkage-
    weighted Beta mixing on user × mechanism + cohort × mechanism).

    Spine #5 free-energy and Spine #7 cohort-discovery are
    intentionally limited in v0.1:
      * Spine #5: synthetic world doesn't expose page-attentional-
        posture features rich enough for free-energy. Honest tag —
        sibling slice would augment the SyntheticWorld with posture
        features and add the F(a) modulation.
      * Spine #7: architecture uses ground-truth cohort_id (Spine
        #7's cohort DISCOVERY is operationally blocked on Loop B
        per the wrap-out handoff). Discovery upgrade is sibling.

    Architecture E adds Spine #6 counterfactual logging on top of D.
    """

    name: str = "D_full_proposed_stack"

    def __init__(
        self,
        *,
        shrinkage_kappa: float = 20.0,
        carryover_rho: float = 0.30,
        carryover_tau_hours: float = 24.0,
        seed: int = 0,
    ):
        if shrinkage_kappa <= 0:
            raise ValueError("shrinkage_kappa must be positive")
        if carryover_tau_hours <= 0:
            raise ValueError("carryover_tau_hours must be positive")
        self.shrinkage_kappa = float(shrinkage_kappa)
        self.carryover_rho = float(carryover_rho)
        self.carryover_tau_hours = float(carryover_tau_hours)
        self._rng = random.Random(int(seed))
        self._mechanisms: List[str] = []
        self._user_cohort: Dict[str, int] = {}
        self._user_mech_n: Dict[tuple, int] = defaultdict(int)
        self._user_mech_conv: Dict[tuple, int] = defaultdict(int)
        self._cohort_mech_n: Dict[tuple, int] = defaultdict(int)
        self._cohort_mech_conv: Dict[tuple, int] = defaultdict(int)
        self._touch_history: Dict[str, List[Tuple[int, float, str]]] = (
            defaultdict(list)
        )

    def configure(self, population: SyntheticPopulation) -> None:
        self._mechanisms = list(population.mechanisms)
        self._user_cohort = {
            u.user_id: u.cohort_id for u in population.users
        }
        self._user_mech_n = defaultdict(int)
        self._user_mech_conv = defaultdict(int)
        self._cohort_mech_n = defaultdict(int)
        self._cohort_mech_conv = defaultdict(int)
        self._touch_history = defaultdict(list)

    def _user_alpha_beta(
        self, user_id: str, mechanism: str,
    ) -> Tuple[float, float]:
        """Beta(α, β) for the user × mechanism cell. Flat Beta(1, 1)
        prior + Laplace counts."""
        key = (user_id, mechanism)
        n = self._user_mech_n[key]
        c = self._user_mech_conv[key]
        return (1.0 + c, 1.0 + (n - c))

    def _cohort_alpha_beta(
        self, cohort_id: int, mechanism: str,
    ) -> Tuple[float, float]:
        key = (cohort_id, mechanism)
        n = self._cohort_mech_n[key]
        c = self._cohort_mech_conv[key]
        return (1.0 + c, 1.0 + (n - c))

    def shrinkage_weight(self, user_id: str, mechanism: str) -> float:
        n_user = self._user_mech_n[(user_id, mechanism)]
        return float(n_user) / (float(n_user) + self.shrinkage_kappa)

    def _user_posterior_mean(
        self, user_id: str, mechanism: str,
    ) -> float:
        a, b = self._user_alpha_beta(user_id, mechanism)
        return a / (a + b)

    def carryover_penalty(
        self,
        user_id: str,
        mechanism: str,
        week: int,
        hour_of_horizon: float,
    ) -> float:
        """Spine #2 AR(1) carryover correction. Returns the residual
        effect from the most recent same-mechanism touch — caller
        SUBTRACTS from the candidate's score."""
        history = self._touch_history.get(user_id, [])
        if not history:
            return 0.0
        for w, h, m_prev in reversed(history):
            if m_prev != mechanism:
                continue
            delta_h = (week - w) * 168.0 + (hour_of_horizon - h)
            if delta_h <= 0:
                return 0.0
            decay = math.exp(-delta_h / self.carryover_tau_hours)
            prior_eff = self._user_posterior_mean(user_id, mechanism)
            return self.carryover_rho * prior_eff * decay
        return 0.0

    def _thompson_sample_score(
        self,
        user_id: str,
        mechanism: str,
        week: int,
        hour_of_horizon: float,
    ) -> float:
        """Thompson Sampling on the shrinkage-weighted Beta mix +
        Spine #2 carryover correction."""
        cohort = self._user_cohort.get(user_id, -1)
        weight_user = self.shrinkage_weight(user_id, mechanism)

        a_user, b_user = self._user_alpha_beta(user_id, mechanism)
        a_coh, b_coh = self._cohort_alpha_beta(cohort, mechanism)
        a_mix = weight_user * a_user + (1.0 - weight_user) * a_coh
        b_mix = weight_user * b_user + (1.0 - weight_user) * b_coh
        sample = self._rng.betavariate(max(a_mix, 1e-6), max(b_mix, 1e-6))

        penalty = self.carryover_penalty(
            user_id, mechanism, week, hour_of_horizon,
        )
        return sample - penalty

    def select_mechanism(self, impression: Impression) -> str:
        if not self._mechanisms:
            raise RuntimeError(
                "FullProposedStack.select_mechanism called before "
                "configure()"
            )

        cohort = self._user_cohort.get(impression.user_id, -1)
        cohort_untried = [
            m for m in self._mechanisms
            if self._cohort_mech_n[(cohort, m)] == 0
        ]
        if cohort_untried:
            return self._rng.choice(cohort_untried)

        best_m = self._mechanisms[0]
        best_v = self._thompson_sample_score(
            impression.user_id, best_m,
            impression.week, impression.hour_of_horizon,
        )
        for m in self._mechanisms[1:]:
            v = self._thompson_sample_score(
                impression.user_id, m,
                impression.week, impression.hour_of_horizon,
            )
            if v > best_v:
                best_v = v
                best_m = m
        return best_m

    def record_outcome(self, outcome: Outcome) -> None:
        m = outcome.mechanism_sent
        u = outcome.user_id
        c = self._user_cohort.get(u, -1)
        self._user_mech_n[(u, m)] += 1
        self._cohort_mech_n[(c, m)] += 1
        if outcome.converted:
            self._user_mech_conv[(u, m)] += 1
            self._cohort_mech_conv[(c, m)] += 1
        self._touch_history[u].append(
            (outcome.week, outcome.hour_of_horizon, m),
        )
        if len(self._touch_history[u]) > 100:
            self._touch_history[u] = self._touch_history[u][-100:]
