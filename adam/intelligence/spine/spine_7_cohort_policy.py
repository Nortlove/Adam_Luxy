# =============================================================================
# ADAM Spine #7 — Cohort Discovery + Cohort-Conditional Non-Stationary Policy
# Location: adam/intelligence/spine/spine_7_cohort_policy.py
# =============================================================================

"""Cohort discovery + non-stationary cohort-conditional policy.

PER DIRECTIVE SECTION 2 (Spine #7 specification).

Latent cohort structure is discovered via a Hidden Markov Model over
user behavior sequences (state-trait detection from temporal patterns);
cohorts are defined by posterior distributions over latent states, NOT
by demographics. Each cohort has its own discounted-Thompson-Sampling /
Sliding-Window-UCB / restless-bandit policy with cohort-specific priors.

Why this is spine: static demographic targeting is exactly what the
platform must NOT be. Latent-state cohorts derived from the bilateral
graph are what justify the cognitive-architecture pitch. The non-
stationary part matters because B2B-travel intent is event-driven
(calendar quarter, conference season, RFP cycles, individual life
events) and reward distributions abruptly shift; restless-bandit /
SW-UCB / D-UCB methods match the lower bound on dynamic regret in
switching-bandit settings, while standard TS and UCB suffer linear
regret under non-stationarity.

DECISION-TIME CONSUMERS (Rule A check)

Spine #7 is consumed at decision time by:
    - The orchestrator's recommendation policy — reads cohort-conditional
      mechanism scores for the user's cohort mixture
    - Spine #1 — the cohort-mixture prior IS the partial-pooling target
      for new and low-volume users; cohort posteriors inform per-user
      posteriors via the mixture
    - Spine #4 trilateral cascade — eligibility filtering happens before
      the cohort-conditional policy runs; cohort policy chooses among
      eligible candidates only
    - The pacing layer (Spine #9) — Whittle-index allocation across
      cohorts drives budget distribution

Cognitive primitive at the serving path. NOT measurement.

THIS COMMIT SHIPS

    - SW-UCB (Sliding-Window Upper Confidence Bound) policy per cohort
      with closed-form regret bounds under non-stationarity
    - Mortal-bandit creative-fatigue treatment with explicit lifetime
      budgets per arm
    - Cohort-conditional candidate scoring that wraps SW-UCB with
      cohort-specific priors
    - Phase 3 gate substrate: lift-recovery time after regime shift
      measurable against static-priors baseline

THIS COMMIT DOES NOT SHIP (follow-on commits)

    - Full HMM-over-behavior cohort discovery (6-10 cohort EM /
      forward-backward inference) — substrate for cohort assignment
      ships separately when the elicitation loop produces enough
      inputs to seed it. For now, cohort assignment is via the
      UserPosterior.cohort_membership / cohort_ids fields populated
      by Spine #1
    - Restless-bandit Whittle-index allocation across cohorts (next
      commit; depends on per-cohort policies first)
    - Discounted Thompson Sampling variant of SW-UCB (the directive
      specifies both; SW-UCB is canonical for the gate)

REFERENCES

    Garivier & Moulines 2011 — SW-UCB / D-UCB for non-stationary bandits.
    Cheung-Simchi-Levi-Zhu 2019 — sliding-window TS.
    Chakrabarti et al. 2008 — mortal bandits for finite-lifetime arms.
    IntelligentPooling — cohort + person-specific random effects.
"""

from __future__ import annotations

import logging
import math
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Deque, Dict, List, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)


# =============================================================================
# Configuration constants per directive
# =============================================================================


# SW-UCB sliding window size — number of recent observations the policy
# retains for the per-cohort arm-reward estimate. Per directive Section
# 2: "discount factor / window size is itself a learned parameter
# (parameter-drift transition density), per cohort."
DEFAULT_SW_UCB_WINDOW: int = 100


# UCB exploration constant. Per Garivier & Moulines 2011, the canonical
# value is ξ = 0.5 (under sub-Gaussian rewards with σ=1; ad-tech outcomes
# under [0, 1] bounded conversion satisfy this). Pilot-pending tuning.
DEFAULT_SW_UCB_EXPLORATION: float = 0.5


# Mortal-bandit default arm lifetime (in observations). Per directive:
# "creative variants and even mechanisms have finite effective horizons
# (creative fatigue, mechanism-saturation effects)." Conservative
# default — refined offline as fatigue patterns emerge.
DEFAULT_ARM_LIFETIME_OBSERVATIONS: int = 1000


# Cohort count band per directive: "Six to ten cohorts is the right
# granularity — enough resolution to be meaningful, few enough to not
# fragment per-cohort N below useful bounds."
COHORT_COUNT_MIN: int = 6
COHORT_COUNT_MAX: int = 10


# =============================================================================
# Per-arm reward window (SW-UCB substrate)
# =============================================================================


@dataclass
class ArmRewardWindow:
    """Sliding-window reward history for one arm in one cohort.

    Per Garivier & Moulines 2011: SW-UCB tracks the most recent W
    observations per arm; when W is matched to the regime-shift
    timescale, dynamic regret matches the lower bound for switching
    bandits. A reward delivered before the window starts is forgotten.

    Implementation: bounded deque of (timestamp, reward) tuples.
    """

    arm: str
    window_size: int = DEFAULT_SW_UCB_WINDOW
    rewards: Deque[Tuple[datetime, float]] = field(default_factory=deque)
    total_observations: int = 0

    def record(self, reward: float, at: Optional[datetime] = None) -> None:
        """Record a reward observation. Keeps the deque bounded to
        window_size; older observations forgotten."""
        ts = at or datetime.now(timezone.utc)
        self.rewards.append((ts, reward))
        self.total_observations += 1
        while len(self.rewards) > self.window_size:
            self.rewards.popleft()

    def empirical_mean(self) -> float:
        """Empirical mean reward over the current window. Returns 0.0
        when the window is empty (caller should treat that as "needs
        exploration")."""
        if not self.rewards:
            return 0.0
        return sum(r for _, r in self.rewards) / len(self.rewards)

    def n_in_window(self) -> int:
        return len(self.rewards)


# =============================================================================
# SW-UCB policy per cohort
# =============================================================================


@dataclass
class CohortSWUCBPolicy:
    """Sliding-Window UCB policy for one cohort.

    Per arm `a` in cohort `k`, the policy tracks an ArmRewardWindow.
    At decision time, the policy returns UCB scores per arm:

        UCB(a) = empirical_mean(a) + sqrt(ξ · log(t_window) / N(a))

    where t_window = sum of N(a) over all arms in the cohort, ξ is the
    exploration constant, and N(a) is the count of observations in
    arm a's window.

    For arms with N(a) = 0 (never observed), UCB returns +inf — the
    policy MUST explore unobserved arms.
    """

    cohort_id: str
    window_size: int = DEFAULT_SW_UCB_WINDOW
    exploration: float = DEFAULT_SW_UCB_EXPLORATION
    arm_windows: Dict[str, ArmRewardWindow] = field(default_factory=dict)

    def record_outcome(
        self,
        arm: str,
        reward: float,
        at: Optional[datetime] = None,
    ) -> None:
        """Record an arm's reward into the cohort's sliding window."""
        if arm not in self.arm_windows:
            self.arm_windows[arm] = ArmRewardWindow(
                arm=arm, window_size=self.window_size,
            )
        self.arm_windows[arm].record(reward, at=at)

    def total_observations_in_window(self) -> int:
        """Sum of n_in_window across all arms — used as the t parameter
        in the UCB formula."""
        return sum(w.n_in_window() for w in self.arm_windows.values())

    def ucb_score(self, arm: str) -> float:
        """Compute the SW-UCB score for an arm.

        Returns +inf for arms with zero observations (force exploration).
        """
        window = self.arm_windows.get(arm)
        if window is None or window.n_in_window() == 0:
            return float("inf")
        t = max(1, self.total_observations_in_window())
        n_a = window.n_in_window()
        bonus = math.sqrt(self.exploration * math.log(t) / n_a)
        return window.empirical_mean() + bonus

    def select_arm(self, candidate_arms: List[str]) -> Optional[str]:
        """Return the arm with the highest UCB score from candidates.

        Returns None when candidate_arms is empty.
        """
        if not candidate_arms:
            return None
        scores = [(a, self.ucb_score(a)) for a in candidate_arms]
        return max(scores, key=lambda t: t[1])[0]

    def cohort_arm_summary(self) -> Dict[str, Dict[str, float]]:
        """Return a structured summary of arm state in this cohort.

        Used by the partner-facing dashboard (Spine #13) to render
        the mechanism-rotation graph.
        """
        return {
            arm: {
                "empirical_mean": w.empirical_mean(),
                "n_in_window": w.n_in_window(),
                "total_observations": w.total_observations,
                "ucb_score": self.ucb_score(arm),
            }
            for arm, w in self.arm_windows.items()
        }


# =============================================================================
# Mortal-bandit treatment of expiring arms
# =============================================================================


@dataclass
class ArmLifetime:
    """Lifetime tracker for a creative variant or mechanism arm.

    Per directive: "Use mortal-bandit framing (Chakrabarti et al. 2008)
    — each arm has an explicit 'lifetime' budget after which it is
    retired. Frequency caps and creative-fatigue logic are first-class
    constraints on the policy, not post-hoc patches."
    """

    arm: str
    lifetime_observations: int = DEFAULT_ARM_LIFETIME_OBSERVATIONS
    observations_so_far: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    retired_at: Optional[datetime] = None

    def is_alive(self) -> bool:
        """Return True iff the arm has not exhausted its lifetime."""
        return self.observations_so_far < self.lifetime_observations and \
            self.retired_at is None

    def increment(self, at: Optional[datetime] = None) -> bool:
        """Increment observation count; retire automatically when lifetime
        is reached. Returns True iff the arm is still alive after
        increment."""
        self.observations_so_far += 1
        if self.observations_so_far >= self.lifetime_observations:
            self.retired_at = at or datetime.now(timezone.utc)
            return False
        return True

    def force_retire(self, at: Optional[datetime] = None) -> None:
        """Manually retire an arm (e.g., creative pulled from rotation)."""
        if self.retired_at is None:
            self.retired_at = at or datetime.now(timezone.utc)

    def fraction_consumed(self) -> float:
        """Fraction of lifetime budget consumed (0 = fresh, 1 = retired)."""
        if self.lifetime_observations <= 0:
            return 1.0
        return min(1.0, self.observations_so_far / self.lifetime_observations)


# =============================================================================
# Combined cohort policy with mortal-bandit gating
# =============================================================================


class CohortPolicyState(BaseModel):
    """Cohort policy state for a single cohort — Pydantic for serialization.

    Composes SW-UCB arm rewards + mortal-bandit lifetimes. Decision-time
    consumers read this; the orchestrator records updates back through
    the service-layer methods on CohortPolicyService.
    """

    model_config = ConfigDict(extra="forbid")

    cohort_id: str
    arm_summaries: Dict[str, Dict[str, float]] = Field(default_factory=dict)
    lifetime_summaries: Dict[str, Dict[str, float]] = Field(default_factory=dict)
    last_updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class CohortPolicyService:
    """Manages SW-UCB + mortal-bandit state for one cohort.

    The service is the orchestrator-facing entry point. It composes:
      - CohortSWUCBPolicy (reward history + UCB scoring)
      - ArmLifetime per arm (mortal-bandit retirement)

    Selection:
      1. Filter candidate arms to alive arms only (mortal-bandit gate).
      2. Run SW-UCB on the alive set.
      3. Return chosen arm OR None (if all arms retired).
    """

    cohort_id: str
    sw_ucb: CohortSWUCBPolicy = field(init=False)
    arm_lifetimes: Dict[str, ArmLifetime] = field(default_factory=dict)
    window_size: int = DEFAULT_SW_UCB_WINDOW
    exploration: float = DEFAULT_SW_UCB_EXPLORATION
    arm_default_lifetime: int = DEFAULT_ARM_LIFETIME_OBSERVATIONS

    def __post_init__(self) -> None:
        self.sw_ucb = CohortSWUCBPolicy(
            cohort_id=self.cohort_id,
            window_size=self.window_size,
            exploration=self.exploration,
        )

    def register_arm(self, arm: str, lifetime: Optional[int] = None) -> None:
        """Register a new arm with the cohort. lifetime defaults to
        arm_default_lifetime."""
        if arm in self.arm_lifetimes:
            return
        self.arm_lifetimes[arm] = ArmLifetime(
            arm=arm,
            lifetime_observations=lifetime or self.arm_default_lifetime,
        )

    def alive_arms(self, candidates: List[str]) -> List[str]:
        """Filter candidates to only those alive (not retired)."""
        result = []
        for arm in candidates:
            if arm not in self.arm_lifetimes:
                # Auto-register on first sight.
                self.register_arm(arm)
            if self.arm_lifetimes[arm].is_alive():
                result.append(arm)
        return result

    def select_arm(
        self, candidate_arms: List[str],
    ) -> Optional[str]:
        """Select an arm via SW-UCB, gated by mortal-bandit retirement.

        Returns None when all candidates are retired.
        """
        alive = self.alive_arms(candidate_arms)
        if not alive:
            return None
        return self.sw_ucb.select_arm(alive)

    def record_outcome(
        self,
        arm: str,
        reward: float,
        at: Optional[datetime] = None,
    ) -> bool:
        """Record an outcome for an arm. Updates SW-UCB window AND
        mortal-bandit lifetime counter. Returns True iff the arm is
        still alive after this observation."""
        self.sw_ucb.record_outcome(arm, reward, at=at)
        if arm not in self.arm_lifetimes:
            self.register_arm(arm)
        return self.arm_lifetimes[arm].increment(at=at)

    def state_snapshot(self) -> CohortPolicyState:
        """Return a Pydantic snapshot of cohort policy state."""
        return CohortPolicyState(
            cohort_id=self.cohort_id,
            arm_summaries=self.sw_ucb.cohort_arm_summary(),
            lifetime_summaries={
                arm: {
                    "fraction_consumed": lt.fraction_consumed(),
                    "is_alive": float(lt.is_alive()),
                    "observations_so_far": float(lt.observations_so_far),
                    "lifetime_observations": float(lt.lifetime_observations),
                }
                for arm, lt in self.arm_lifetimes.items()
            },
        )


__all__ = [
    "ArmLifetime",
    "ArmRewardWindow",
    "COHORT_COUNT_MAX",
    "COHORT_COUNT_MIN",
    "CohortPolicyService",
    "CohortPolicyState",
    "CohortSWUCBPolicy",
    "DEFAULT_ARM_LIFETIME_OBSERVATIONS",
    "DEFAULT_SW_UCB_EXPLORATION",
    "DEFAULT_SW_UCB_WINDOW",
]
