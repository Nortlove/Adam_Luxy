# =============================================================================
# Repeated Measures / Within-Subject Experimental Design — Core Engine
# Location: adam/retargeting/engines/repeated_measures.py
# Enhancement #36
# =============================================================================

"""
Core engine for within-subject repeated measures analysis.

Four components (built across sessions 36-1 through 36-6):

1. UserPosteriorManager (36-1): Per-user mechanism posteriors with
   L1 memory + L2 Redis + cold-start from population posteriors.

2. MixedEffectsEstimator (36-3): Online method-of-moments variance
   decomposition. O(1) per update. ICC + design-effect weights.

3. WithinSubjectDesigner (36-4): Balanced incomplete block design
   for each user's sequence. Power-aware exploration allocation.

4. TrajectoryAnalyzer (36-6): Online OLS trend/curvature, AR(1),
   changepoint detection, trajectory classification.

The fundamental insight: 7 observations from 1 person are fundamentally
different from 1 observation each from 7 people. The former are correlated
within-subject measurements. By modeling that correlation, we get 2-4x
more statistical power AND can answer "what works for THIS person" —
something no between-subjects design can do.
"""

import json
import logging
import math
import threading
import time
from collections import OrderedDict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from adam.retargeting.engines.prior_manager import (
    HierarchicalPriorManager,
    BarrierConditionedPosterior,
)
from adam.retargeting.models.within_subject import (
    MechanismContrast,
    TrajectoryAnalysis,
    UserMechanismPosterior,
    UserPosteriorProfile,
    VarianceComponents,
    WithinSubjectDesign,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# User Posterior Manager (Session 36-1)
# ---------------------------------------------------------------------------

# Trust threshold: how many user-level observations before user posteriors
# start overriding population posteriors in blending.
USER_TRUST_THRESHOLD = 3

# Maximum user profiles in L1 memory cache
MAX_L1_PROFILES = 50_000

# Redis key prefix and TTL for user profiles
REDIS_KEY_PREFIX = "adam:retargeting:user_profile"
REDIS_TTL_SECONDS = 30 * 24 * 3600  # 30 days


class UserPosteriorManager:
    """Manages per-user mechanism posteriors for within-subject analysis.

    Storage hierarchy:
    - L1: In-memory OrderedDict (LRU eviction at MAX_L1_PROFILES)
    - L2: Redis (30-day TTL, JSON serialization)
    - L3: Neo4j (permanent, debounced writes — added in session 36-10)

    Cold-start: When a user has no profile, creates one from the
    population-level posteriors via HierarchicalPriorManager. This means
    a new user inherits the best available evidence from corpus → category
    → brand → campaign, then specializes as touches arrive.
    """

    def __init__(
        self,
        prior_manager: Optional[HierarchicalPriorManager] = None,
        redis_client=None,
    ):
        self._prior_manager = prior_manager or HierarchicalPriorManager()
        self._redis = redis_client

        # L1: LRU cache of user profiles
        self._profiles: OrderedDict[str, UserPosteriorProfile] = OrderedDict()
        self._lock = threading.RLock()

        # Mixed-effects estimator (added in session 36-3)
        self._mixed_effects: Optional["MixedEffectsEstimator"] = None

    def set_mixed_effects(self, estimator: "MixedEffectsEstimator") -> None:
        """Wire the mixed-effects estimator after construction."""
        self._mixed_effects = estimator

    # -----------------------------------------------------------------
    # Profile retrieval
    # -----------------------------------------------------------------

    def get_user_profile(
        self,
        user_id: str,
        brand_id: str,
        archetype_id: str = "",
        context: Optional[Dict[str, str]] = None,
    ) -> UserPosteriorProfile:
        """Get or create a user's posterior profile.

        Lookup order: L1 memory → L2 Redis → cold-start from population.
        Latency target: <5ms for L1 hit, <15ms for Redis hit.
        """
        cache_key = f"{user_id}:{brand_id}"

        # L1: memory cache
        with self._lock:
            if cache_key in self._profiles:
                # Move to end (most recently used)
                self._profiles.move_to_end(cache_key)
                return self._profiles[cache_key]

        # L2: Redis
        profile = self._load_from_redis(cache_key)
        if profile is not None:
            self._store_l1(cache_key, profile)
            return profile

        # Cold start: create from population posteriors
        profile = self._cold_start(user_id, brand_id, archetype_id, context)
        self._store_l1(cache_key, profile)
        self._store_to_redis(cache_key, profile)
        return profile

    # -----------------------------------------------------------------
    # Posterior updates
    # -----------------------------------------------------------------

    def update_user_posterior(
        self,
        user_id: str,
        brand_id: str,
        mechanism: str,
        barrier: str,
        archetype_id: str,
        reward: float,
        touch_position: int,
        context: Optional[Dict[str, str]] = None,
        page_cluster: str = "",
    ) -> UserPosteriorProfile:
        """Update user-level posteriors after a touch outcome.

        This is the core learning method. It:
        1. Gets or creates the user profile
        2. Updates the per-mechanism Beta posterior
        3. Updates aggregate tracking (total, mean, outcomes list)
        4. Recomputes trajectory (linear trend, curvature)
        5. Recomputes AR(1) autocorrelation
        6. Updates the mixed-effects estimator (if available)
        7. Returns the design-effect weight for population-level updates
        8. Optionally tracks mechanism×page_cluster posteriors for
           user×page interaction learning (Enhancement #36 integration)

        Returns the updated profile (also stored in cache).
        """
        profile = self.get_user_profile(user_id, brand_id, archetype_id, context)

        # 1. Get or create per-mechanism posterior
        if mechanism not in profile.mechanism_posteriors:
            # Initialize from population posterior for this mechanism
            pop_posterior = self._prior_manager.get_effective_posterior(
                mechanism=mechanism,
                barrier=barrier,
                archetype=archetype_id,
                context=context,
            )
            profile.mechanism_posteriors[mechanism] = UserMechanismPosterior(
                user_id=user_id,
                mechanism=mechanism,
                barrier=barrier,
                alpha=pop_posterior.alpha,
                beta=pop_posterior.beta,
            )

        # 2. Update mechanism posterior
        mech_posterior = profile.mechanism_posteriors[mechanism]
        mech_posterior.update(reward)

        # 2b. Track mechanism × page_cluster interaction (if page context available)
        # This lets the system learn "user_X responds to proof on analytical pages
        # but not on emotional pages" — the highest-value personalization signal.
        if page_cluster:
            page_key = f"{mechanism}:{page_cluster}"
            if page_key not in profile.page_mechanism_posteriors:
                # Initialize from the mechanism-level posterior
                profile.page_mechanism_posteriors[page_key] = UserMechanismPosterior(
                    user_id=user_id,
                    mechanism=mechanism,
                    barrier=barrier,
                    alpha=mech_posterior.alpha,
                    beta=mech_posterior.beta,
                )
            profile.page_mechanism_posteriors[page_key].update(reward)

        # 3. Update aggregate tracking
        profile.total_touches_observed += 1
        profile.total_reward_sum += reward
        profile.all_outcomes.append(reward)
        profile.all_mechanisms.append(mechanism)
        if len(profile.all_outcomes) > 50:
            profile.all_outcomes = profile.all_outcomes[-50:]
            profile.all_mechanisms = profile.all_mechanisms[-50:]

        # 4. Recompute trajectory
        profile.update_trajectory()

        # 5. Recompute AR(1)
        profile.update_ar1()

        # 6. Update random intercept (exponentially weighted deviation from population)
        self._update_random_effects(profile, mechanism, reward, context)

        # 7. Update mixed-effects estimator
        if self._mixed_effects is not None:
            vc = self._mixed_effects.update(user_id, mechanism, reward)
            profile.variance_components = vc

        # 8. Update timestamps
        profile.updated_at = datetime.now(timezone.utc)

        # Store updated profile
        cache_key = f"{user_id}:{brand_id}"
        self._store_l1(cache_key, profile)
        # Debounced Redis write (every 3rd update to reduce writes)
        if profile.total_touches_observed % 3 == 0 or reward > 0.5:
            self._store_to_redis(cache_key, profile)

        return profile

    def get_user_mechanism_posterior(
        self,
        user_id: str,
        brand_id: str,
        mechanism: str,
        barrier: str,
        archetype_id: str,
        context: Optional[Dict[str, str]] = None,
    ) -> BarrierConditionedPosterior:
        """Get blended user+population posterior for Thompson Sampling.

        Blends user-level evidence with population-level evidence:
        - user_weight = min(1.0, user_obs / USER_TRUST_THRESHOLD)
        - effective = user_weight * user_posterior + (1 - user_weight) * population

        With 3+ user observations, user-level starts dominating.
        This means personalized mechanism selection after just 3 touches.
        """
        profile = self.get_user_profile(user_id, brand_id, archetype_id, context)

        # Population posterior (blended across hierarchy levels)
        pop_posterior = self._prior_manager.get_effective_posterior(
            mechanism=mechanism,
            barrier=barrier,
            archetype=archetype_id,
            context=context,
        )

        # User posterior (may not exist if mechanism not yet tried)
        user_posterior = profile.mechanism_posteriors.get(mechanism)

        if user_posterior is None or user_posterior.sample_count == 0:
            # No user data — use population only
            return pop_posterior

        # Blend based on user evidence strength
        user_weight = min(1.0, user_posterior.sample_count / USER_TRUST_THRESHOLD)

        blended_alpha = (
            user_weight * user_posterior.alpha
            + (1 - user_weight) * pop_posterior.alpha
        )
        blended_beta = (
            user_weight * user_posterior.beta
            + (1 - user_weight) * pop_posterior.beta
        )

        return BarrierConditionedPosterior(
            mechanism=mechanism,
            barrier=barrier,
            archetype=archetype_id,
            level="user",  # type: ignore[arg-type]
            alpha=blended_alpha,
            beta=blended_beta,
            context_key=f"user:{user_id}",
        )

    def get_within_user_contrasts(
        self,
        user_id: str,
        brand_id: str,
    ) -> List[MechanismContrast]:
        """Compute all pairwise within-user mechanism contrasts.

        For each pair of mechanisms this user has tried, compute the
        paired effect estimate and its standard error. This is the
        core within-subject statistical comparison.
        """
        profile = self.get_user_profile(user_id, brand_id)
        posteriors = profile.mechanism_posteriors

        if len(posteriors) < 2:
            return []

        contrasts = []
        mechanisms = list(posteriors.keys())

        for i in range(len(mechanisms)):
            for j in range(i + 1, len(mechanisms)):
                m_a = mechanisms[i]
                m_b = mechanisms[j]
                p_a = posteriors[m_a]
                p_b = posteriors[m_b]

                if p_a.sample_count < 1 or p_b.sample_count < 1:
                    continue

                # Effect estimate: difference in posterior means
                effect = p_a.mean - p_b.mean

                # SE of difference: sqrt(var_a/n_a + var_b/n_b)
                # Adjusted for within-user correlation
                rho = profile.within_user_correlation
                var_a = p_a.variance
                var_b = p_b.variance
                se = math.sqrt(
                    var_a + var_b - 2 * rho * math.sqrt(var_a * var_b)
                )
                se = max(se, 1e-6)

                contrasts.append(
                    MechanismContrast(
                        mechanism_a=m_a,
                        mechanism_b=m_b,
                        effect_estimate=effect,
                        effect_se=se,
                        observations_a=p_a.sample_count,
                        observations_b=p_b.sample_count,
                    )
                )

        return contrasts

    # -----------------------------------------------------------------
    # Cold start
    # -----------------------------------------------------------------

    def _cold_start(
        self,
        user_id: str,
        brand_id: str,
        archetype_id: str,
        context: Optional[Dict[str, str]] = None,
    ) -> UserPosteriorProfile:
        """Create a new user profile from population posteriors.

        The user starts with the population's best estimates. As they
        receive touches, their profile specializes to their individual
        response pattern.
        """
        logger.debug(
            "Cold-starting user profile: user=%s brand=%s archetype=%s",
            user_id, brand_id, archetype_id,
        )

        profile = UserPosteriorProfile(
            user_id=user_id,
            brand_id=brand_id,
            archetype_id=archetype_id,
        )

        # If mixed-effects estimator has variance components, use them
        if self._mixed_effects is not None:
            profile.variance_components = self._mixed_effects.get_variance_components()

        return profile

    # -----------------------------------------------------------------
    # Random effects update
    # -----------------------------------------------------------------

    def _update_random_effects(
        self,
        profile: UserPosteriorProfile,
        mechanism: str,
        reward: float,
        context: Optional[Dict[str, str]] = None,
    ) -> None:
        """Update random intercept and mechanism slopes.

        Uses exponentially weighted moving average with learning rate
        that decreases as observations accumulate (stabilizes estimate).

        random_intercept = user_mean - population_mean
        mechanism_slope[m] = user_mean_for_m - user_mean - population_mean_for_m + population_mean
        """
        n = profile.total_touches_observed
        if n < 2:
            return

        # Learning rate: decreases from 0.5 to 0.1 as observations grow
        lr = max(0.1, 0.5 / math.sqrt(n))

        # Population mean (from corpus prior — rough approximation)
        pop_mean = 0.5  # Default uninformative
        pop_posterior = self._prior_manager.get_effective_posterior(
            mechanism=mechanism,
            barrier="",
            archetype=profile.archetype_id,
            context=context,
        )
        pop_mean = pop_posterior.mean

        # Random intercept: user_mean - population_mean
        user_mean = profile.user_mean_reward
        target_intercept = user_mean - pop_mean
        profile.random_intercept = (
            (1 - lr) * profile.random_intercept + lr * target_intercept
        )

        # Mechanism slope: user's mechanism mean vs what we'd expect
        mech_posterior = profile.mechanism_posteriors.get(mechanism)
        if mech_posterior and mech_posterior.sample_count >= 2:
            user_mech_mean = mech_posterior.mean
            # Expected = population_mechanism_mean + user_intercept
            expected = pop_mean + profile.random_intercept
            slope = user_mech_mean - expected
            profile.mechanism_slopes[mechanism] = (
                (1 - lr) * profile.mechanism_slopes.get(mechanism, 0.0) + lr * slope
            )

    # -----------------------------------------------------------------
    # Storage helpers
    # -----------------------------------------------------------------

    def _store_l1(self, cache_key: str, profile: UserPosteriorProfile) -> None:
        """Store in L1 memory cache with LRU eviction."""
        with self._lock:
            self._profiles[cache_key] = profile
            self._profiles.move_to_end(cache_key)
            # Evict oldest if over capacity
            while len(self._profiles) > MAX_L1_PROFILES:
                evicted_key, evicted_profile = self._profiles.popitem(last=False)
                # Persist evicted profile to Redis before discarding
                self._store_to_redis(evicted_key, evicted_profile)

    def _load_from_redis(self, cache_key: str) -> Optional[UserPosteriorProfile]:
        """Load user profile from Redis L2 cache."""
        if self._redis is None:
            return None
        try:
            redis_key = f"{REDIS_KEY_PREFIX}:{cache_key}"
            data = self._redis.get(redis_key)
            if data is None:
                return None
            return UserPosteriorProfile.model_validate_json(data)
        except Exception as e:
            logger.debug("Redis load failed for %s: %s", cache_key, e)
            return None

    def _store_to_redis(self, cache_key: str, profile: UserPosteriorProfile) -> None:
        """Store user profile to Redis L2 cache."""
        if self._redis is None:
            return
        try:
            redis_key = f"{REDIS_KEY_PREFIX}:{cache_key}"
            data = profile.model_dump_json()
            self._redis.setex(redis_key, REDIS_TTL_SECONDS, data)
        except Exception as e:
            logger.debug("Redis store failed for %s: %s", cache_key, e)

    # -----------------------------------------------------------------
    # Observability
    # -----------------------------------------------------------------

    def stats(self) -> Dict[str, Any]:
        """Return manager statistics for monitoring."""
        with self._lock:
            n_profiles = len(self._profiles)
            if n_profiles == 0:
                return {
                    "l1_profiles": 0,
                    "avg_touches": 0.0,
                    "avg_mechanisms_tried": 0.0,
                }
            total_touches = sum(
                p.total_touches_observed for p in self._profiles.values()
            )
            total_mechs = sum(
                p.mechanisms_tried for p in self._profiles.values()
            )
            return {
                "l1_profiles": n_profiles,
                "avg_touches": round(total_touches / n_profiles, 1),
                "avg_mechanisms_tried": round(total_mechs / n_profiles, 1),
                "l1_capacity_pct": round(100 * n_profiles / MAX_L1_PROFILES, 1),
            }


# ---------------------------------------------------------------------------
# Mixed-Effects Estimator (Session 36-3 — skeleton here, full impl later)
# ---------------------------------------------------------------------------


class _RunningStats:
    """O(1) online mean and variance tracker (Welford's algorithm)."""

    __slots__ = ("n", "mean", "m2")

    def __init__(self) -> None:
        self.n = 0
        self.mean = 0.0
        self.m2 = 0.0  # Sum of squared deviations

    def update(self, value: float) -> None:
        self.n += 1
        delta = value - self.mean
        self.mean += delta / self.n
        delta2 = value - self.mean
        self.m2 += delta * delta2

    @property
    def variance(self) -> float:
        if self.n < 2:
            return 0.0
        return self.m2 / (self.n - 1)


class MixedEffectsEstimator:
    """Online method-of-moments variance component estimator.

    Maintains running sufficient statistics for O(1) per-update
    estimation of between-user and within-user variance components.

    Model (conceptually):
        Y_ij = mu + beta_m[mechanism_j] + u_i + u_im + e_ij

    Where:
        u_i ~ N(0, sigma^2_u)      — random intercept per user
        u_im ~ N(0, sigma^2_um)    — random slope per user x mechanism
        e_ij ~ N(0, sigma^2_e)     — within-user residual

    Estimation via ANOVA-style method of moments:
        sigma^2_e = mean(within-user variances)
        sigma^2_u = var(user means) - sigma^2_e / mean(n_per_user)
        sigma^2_um = var(user-mechanism means) - sigma^2_e / mean(n_per_cell)

    This is less efficient than full REML but runs in O(1) per update
    with <5ms latency, which is critical for real-time retargeting.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()

        # Grand running stats
        self._grand = _RunningStats()

        # Per-user running stats
        self._user_stats: Dict[str, _RunningStats] = {}

        # Per-mechanism running stats
        self._mechanism_stats: Dict[str, _RunningStats] = {}

        # Per (user, mechanism) running stats
        self._user_mechanism_stats: Dict[Tuple[str, str], _RunningStats] = {}

        # Cached variance components (recomputed periodically)
        self._cached_vc = VarianceComponents()
        self._updates_since_recompute = 0
        _RECOMPUTE_EVERY = 10  # Recompute variance components every N updates

    def update(self, user_id: str, mechanism: str, reward: float) -> VarianceComponents:
        """Record an observation and return updated variance components.

        O(1) per update. Recomputes full variance decomposition every
        10 updates to amortize cost.
        """
        with self._lock:
            # Update all running statistics
            self._grand.update(reward)

            if user_id not in self._user_stats:
                self._user_stats[user_id] = _RunningStats()
            self._user_stats[user_id].update(reward)

            if mechanism not in self._mechanism_stats:
                self._mechanism_stats[mechanism] = _RunningStats()
            self._mechanism_stats[mechanism].update(reward)

            key = (user_id, mechanism)
            if key not in self._user_mechanism_stats:
                self._user_mechanism_stats[key] = _RunningStats()
            self._user_mechanism_stats[key].update(reward)

            self._updates_since_recompute += 1
            if self._updates_since_recompute >= 10:
                self._recompute_variance_components()
                self._updates_since_recompute = 0

            return self._cached_vc

    def get_variance_components(self) -> VarianceComponents:
        """Return current variance component estimates."""
        with self._lock:
            return self._cached_vc

    def get_design_effect_weight(self, user_id: str) -> float:
        """Get the design-effect weight for one more observation from this user."""
        with self._lock:
            user_stats = self._user_stats.get(user_id)
            n = user_stats.n if user_stats else 0
            return self._cached_vc.design_effect_weight(n)

    def get_random_effects(
        self, user_id: str,
    ) -> Tuple[float, Dict[str, float]]:
        """Extract random intercept and slopes for a user.

        random_intercept = user_mean - grand_mean
        random_slope[m] = user_mech_mean - user_mean - mech_mean + grand_mean
        """
        with self._lock:
            user_stats = self._user_stats.get(user_id)
            if user_stats is None or user_stats.n == 0:
                return 0.0, {}

            grand_mean = self._grand.mean
            user_mean = user_stats.mean
            intercept = user_mean - grand_mean

            slopes: Dict[str, float] = {}
            for (uid, mech), um_stats in self._user_mechanism_stats.items():
                if uid != user_id or um_stats.n == 0:
                    continue
                mech_stats = self._mechanism_stats.get(mech)
                mech_mean = mech_stats.mean if mech_stats else grand_mean
                # Random slope = cell_mean - row_mean - col_mean + grand_mean
                slopes[mech] = um_stats.mean - user_mean - mech_mean + grand_mean

            return intercept, slopes

    def _recompute_variance_components(self) -> None:
        """Full variance decomposition via method of moments.

        Called every 10 updates. Must be called under self._lock.
        """
        n_users = len(self._user_stats)
        if n_users < 2:
            return  # Not enough data

        # sigma^2_e: mean of within-user variances
        within_vars = []
        user_ns = []
        for stats in self._user_stats.values():
            if stats.n >= 2:
                within_vars.append(stats.variance)
                user_ns.append(stats.n)

        if not within_vars:
            return

        sigma2_e = float(np.mean(within_vars))

        # sigma^2_u: variance of user means - sigma^2_e / mean(n_per_user)
        user_means = [s.mean for s in self._user_stats.values() if s.n >= 1]
        if len(user_means) < 2:
            return

        var_user_means = float(np.var(user_means, ddof=1))
        mean_n = float(np.mean(user_ns)) if user_ns else 1.0
        sigma2_u = max(0.0, var_user_means - sigma2_e / mean_n)

        # sigma^2_um: variance of user-mechanism cell means
        um_means = [
            s.mean for s in self._user_mechanism_stats.values() if s.n >= 1
        ]
        um_ns = [
            s.n for s in self._user_mechanism_stats.values() if s.n >= 1
        ]
        sigma2_um = 0.0
        if len(um_means) >= 2 and um_ns:
            var_um = float(np.var(um_means, ddof=1))
            mean_um_n = float(np.mean(um_ns))
            sigma2_um = max(0.0, var_um - sigma2_e / mean_um_n - sigma2_u)

        self._cached_vc = VarianceComponents(
            between_user_variance=sigma2_u,
            within_user_variance=sigma2_e,
            mechanism_interaction_variance=sigma2_um,
        )

    def stats(self) -> Dict[str, Any]:
        """Observability: current estimator state."""
        with self._lock:
            return {
                "total_observations": self._grand.n,
                "n_users": len(self._user_stats),
                "n_mechanisms": len(self._mechanism_stats),
                "n_cells": len(self._user_mechanism_stats),
                "icc": round(self._cached_vc.icc, 3),
                "between_user_var": round(self._cached_vc.between_user_variance, 4),
                "within_user_var": round(self._cached_vc.within_user_variance, 4),
                "mechanism_interaction_var": round(
                    self._cached_vc.mechanism_interaction_variance, 4
                ),
                "personalization_signal": round(
                    self._cached_vc.personalization_signal, 3
                ),
            }


# ---------------------------------------------------------------------------
# Within-Subject Experimental Designer (Session 36-4)
# ---------------------------------------------------------------------------


class WithinSubjectDesigner:
    """Designs balanced incomplete block experiments for user sequences.

    Instead of treating each user's 7-touch sequence as a pure optimization
    funnel, this structures it as a designed experiment that tests 2-3
    mechanisms per user. This enables within-subject paired comparisons
    with dramatically higher statistical power than between-subjects designs.

    Default allocation for 7 touches:
    - Touches 1-2: exploit (best-known mechanism for this barrier)
    - Touch 3: explore (second-best, creates first within-user contrast)
    - Touches 4-5: exploit (may switch primary if exploration was better)
    - Touch 6: explore (third mechanism if uncertainty remains, else exploit)
    - Touch 7: exploit (close sequence with best-known)

    The designer adapts based on:
    - Population uncertainty (which mechanisms need more data?)
    - User-level posteriors (what's already known about this user?)
    - Power calculations (do we have enough data to rank mechanisms?)
    - Barrier constraints (only mechanisms that address the barrier)
    """

    # Minimum power threshold to declare exploration complete
    POWER_THRESHOLD = 0.80
    # Effect size we're trying to detect (d=0.3 is a small-medium effect)
    TARGET_EFFECT_SIZE = 0.3
    # Default exploration slots in a 7-touch sequence
    DEFAULT_EXPLORATION_SLOTS = [3, 6]
    DEFAULT_EXPLOITATION_SLOTS = [1, 2, 4, 5, 7]

    def __init__(
        self,
        prior_manager: Optional[HierarchicalPriorManager] = None,
    ):
        self._prior_manager = prior_manager or HierarchicalPriorManager()

    def design_sequence(
        self,
        user_id: str,
        sequence_id: str,
        archetype_id: str,
        barrier: str,
        max_touches: int = 7,
        user_profile: Optional[UserPosteriorProfile] = None,
        context: Optional[Dict[str, str]] = None,
    ) -> WithinSubjectDesign:
        """Create within-subject experimental design for a new sequence.

        This is called at sequence creation time. It determines:
        1. Which touch positions are for exploration vs exploitation
        2. Which mechanisms to compare for this user
        3. Power estimates for detecting within-user effects

        The design adapts to sequence length:
        - 3 touches: positions [1] exploit, [2] explore, [3] exploit
        - 5 touches: positions [1,2,4] exploit, [3] explore, [5] exploit
        - 7 touches: positions [1,2,4,5,7] exploit, [3,6] explore
        """
        # Scale exploration slots to sequence length
        if max_touches <= 3:
            exploration_slots = [2]
            exploitation_slots = [i for i in range(1, max_touches + 1) if i != 2]
        elif max_touches <= 5:
            exploration_slots = [3]
            exploitation_slots = [i for i in range(1, max_touches + 1) if i != 3]
        else:
            exploration_slots = list(self.DEFAULT_EXPLORATION_SLOTS)
            exploitation_slots = [
                i for i in range(1, max_touches + 1)
                if i not in exploration_slots
            ]

        # Get population posteriors for candidate mechanisms
        population_posteriors = self._prior_manager.get_all_posteriors_for_barrier(
            barrier=barrier,
            archetype=archetype_id,
            context=context,
        )

        # Rank mechanisms by posterior mean
        ranked = sorted(
            population_posteriors.items(),
            key=lambda kv: kv[1].mean,
            reverse=True,
        )

        # Plan contrasts: compare top mechanism vs 2nd and 3rd
        planned_contrasts = []
        if len(ranked) >= 2:
            planned_contrasts.append(
                MechanismContrast(
                    mechanism_a=ranked[0][0],
                    mechanism_b=ranked[1][0],
                    barrier=barrier,
                )
            )
        if len(ranked) >= 3 and len(exploration_slots) >= 2:
            planned_contrasts.append(
                MechanismContrast(
                    mechanism_a=ranked[0][0],
                    mechanism_b=ranked[2][0],
                    barrier=barrier,
                )
            )

        # Compute initial power estimates (before any data)
        power_estimates = {}
        for mech, posterior in population_posteriors.items():
            # With 0 observations, power is 0
            power_estimates[mech] = 0.0

        # If user has prior data, check if exploration is already sufficient
        exploration_complete = False
        mechanisms_tested = []
        if user_profile and user_profile.total_touches_observed >= 5:
            contrasts = self._compute_existing_power(user_profile, barrier)
            if contrasts and all(
                c.power_to_detect(self.TARGET_EFFECT_SIZE) >= self.POWER_THRESHOLD
                for c in contrasts
            ):
                exploration_complete = True
            mechanisms_tested = list(user_profile.mechanism_posteriors.keys())

        return WithinSubjectDesign(
            user_id=user_id,
            sequence_id=sequence_id,
            design_type="balanced_incomplete_block",
            exploration_slots=exploration_slots,
            exploitation_slots=exploitation_slots,
            planned_contrasts=planned_contrasts,
            power_estimates=power_estimates,
            exploration_complete=exploration_complete,
            mechanisms_tested=mechanisms_tested,
        )

    def select_exploration_mechanism(
        self,
        user_profile: UserPosteriorProfile,
        barrier: str,
        archetype_id: str,
        context: Optional[Dict[str, str]] = None,
    ) -> Optional[str]:
        """Select mechanism for an exploration slot.

        Chooses the mechanism with highest information value among candidates
        not yet tried by this user (or tried fewest times). Prioritizes
        mechanisms with high population posterior variance (uncertain).

        Returns mechanism name, or None if all candidates tried sufficiently.
        """
        from adam.constants import BARRIER_MECHANISM_CANDIDATES

        candidates = BARRIER_MECHANISM_CANDIDATES.get(barrier, [])
        if not candidates:
            return None

        # Get population posteriors
        population_posteriors = self._prior_manager.get_all_posteriors_for_barrier(
            barrier=barrier,
            archetype=archetype_id,
            context=context,
        )

        # Score candidates by exploration value
        scored: List[Tuple[str, float]] = []
        for mech in candidates:
            user_post = user_profile.mechanism_posteriors.get(mech)
            pop_post = population_posteriors.get(mech)

            # Information value = posterior_variance * (1 / (1 + n_user_obs))
            # High variance + few user observations = high exploration value
            user_obs = user_post.sample_count if user_post else 0
            pop_var = pop_post.variance if pop_post else 0.25

            # Strong preference for untried mechanisms
            if user_obs == 0:
                info_value = pop_var * 10.0  # 10x bonus for never-tried
            else:
                info_value = pop_var / (1.0 + user_obs)

            scored.append((mech, info_value))

        if not scored:
            return None

        # Select highest information value
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[0][0]

    def should_continue_exploring(
        self,
        user_profile: UserPosteriorProfile,
        remaining_touches: int,
        barrier: str = "",
    ) -> bool:
        """Check if more exploration touches would be valuable.

        Returns False if we already have power > 0.80 to rank this user's
        top mechanism, meaning further exploration has low information value.
        """
        if remaining_touches <= 1:
            return False  # Last touch should always exploit

        if user_profile.mechanisms_tried < 2:
            return True  # Need at least 2 mechanisms for any contrast

        contrasts = self._compute_existing_power(user_profile, barrier)
        if not contrasts:
            return True

        # Check if we have sufficient power for the top contrast
        top_contrast = max(contrasts, key=lambda c: abs(c.effect_estimate))
        power = top_contrast.power_to_detect(
            self.TARGET_EFFECT_SIZE,
            correlation=max(0.0, user_profile.within_user_correlation),
        )
        return power < self.POWER_THRESHOLD

    def _compute_existing_power(
        self,
        user_profile: UserPosteriorProfile,
        barrier: str,
    ) -> List[MechanismContrast]:
        """Compute within-user contrasts from existing data."""
        posteriors = user_profile.mechanism_posteriors
        if len(posteriors) < 2:
            return []

        contrasts = []
        mechanisms = list(posteriors.keys())
        rho = max(0.0, user_profile.within_user_correlation)

        for i in range(len(mechanisms)):
            for j in range(i + 1, len(mechanisms)):
                p_a = posteriors[mechanisms[i]]
                p_b = posteriors[mechanisms[j]]
                if p_a.sample_count < 1 or p_b.sample_count < 1:
                    continue

                contrast = MechanismContrast(
                    mechanism_a=mechanisms[i],
                    mechanism_b=mechanisms[j],
                    barrier=barrier,
                    effect_estimate=p_a.mean - p_b.mean,
                    effect_se=max(
                        1e-6,
                        math.sqrt(p_a.variance + p_b.variance - 2 * rho * math.sqrt(p_a.variance * p_b.variance)),
                    ),
                    observations_a=p_a.sample_count,
                    observations_b=p_b.sample_count,
                )
                contrasts.append(contrast)

        return contrasts


# ---------------------------------------------------------------------------
# Trajectory Analyzer (Session 36-6)
# ---------------------------------------------------------------------------


class TrajectoryAnalyzer:
    """Analyzes within-user engagement trajectories across touches.

    Classifies the shape of engagement over time:
    - warming: monotonically increasing (mechanism working, trust building)
    - cooling: monotonically decreasing (reactance building, fatigue)
    - inverted_u: initial increase then decrease (habituation, ceiling effect)
    - step_change: sudden shift at a specific touch (breakthrough or rupture)
    - flat: no detectable trend (random variation around mean)

    Uses online OLS with 3 coefficients (intercept, linear, quadratic)
    for trajectory classification. Changepoint detection via maximum
    likelihood ratio for single-changepoint model.
    """

    # Minimum touches to attempt trajectory analysis
    MIN_TOUCHES = 3
    # R^2 threshold for classification confidence
    R2_THRESHOLD = 0.25

    def analyze(
        self,
        outcomes: List[float],
        mechanisms: List[str],
        user_id: str = "",
        sequence_id: str = "",
    ) -> TrajectoryAnalysis:
        """Classify the engagement trajectory from an outcome sequence.

        Args:
            outcomes: Ordered outcome scores (one per touch)
            mechanisms: Ordered mechanism names (one per touch)
            user_id: For tracking
            sequence_id: For tracking

        Returns:
            TrajectoryAnalysis with trend, curvature, changepoint, and type.
        """
        result = TrajectoryAnalysis(
            user_id=user_id,
            sequence_id=sequence_id,
            touch_outcomes=list(outcomes),
            touch_mechanisms=list(mechanisms),
        )

        n = len(outcomes)
        if n < self.MIN_TOUCHES:
            result.trajectory_type = "insufficient_data"
            return result

        y = np.array(outcomes, dtype=np.float64)
        x = np.arange(n, dtype=np.float64)
        x_c = x - x.mean()

        # Fit linear model
        X_lin = np.column_stack([np.ones(n), x_c])
        try:
            coeffs_lin, residuals_lin, _, _ = np.linalg.lstsq(X_lin, y, rcond=None)
        except np.linalg.LinAlgError:
            result.trajectory_type = "flat"
            return result

        result.linear_trend = float(coeffs_lin[1])

        # Fit quadratic model (if n >= 4)
        if n >= 4:
            X_quad = np.column_stack([np.ones(n), x_c, x_c ** 2])
            try:
                coeffs_quad, _, _, _ = np.linalg.lstsq(X_quad, y, rcond=None)
                result.quadratic_trend = float(coeffs_quad[2])
            except np.linalg.LinAlgError:
                pass

        # R^2 for classification confidence
        ss_total = float(np.sum((y - y.mean()) ** 2))
        if ss_total > 1e-10:
            y_pred = X_lin @ coeffs_lin
            ss_res = float(np.sum((y - y_pred) ** 2))
            r2 = 1.0 - ss_res / ss_total
            result.classification_confidence = max(0.0, min(1.0, r2))
        else:
            result.classification_confidence = 0.0

        # AR(1) coefficient
        if n >= 3:
            y_var = y.var()
            if y_var > 1e-10:
                y_mean = y.mean()
                lag1_cov = np.mean((y[1:] - y_mean) * (y[:-1] - y_mean))
                result.ar1_coefficient = float(np.clip(lag1_cov / y_var, -0.99, 0.99))

        # Changepoint detection (maximum likelihood ratio, single changepoint)
        changepoint, cp_score = self._detect_changepoint(y)
        if changepoint is not None and cp_score > 0.3:
            result.changepoint_position = int(changepoint)
            if changepoint < len(mechanisms):
                result.changepoint_mechanism = mechanisms[changepoint]

        # Classify trajectory type
        result.trajectory_type = self._classify(result)

        # Set turning point
        if result.trajectory_type == "inverted_u" and result.quadratic_trend < 0:
            # Vertex of parabola: x = -b/(2c) (in centered coordinates)
            if abs(result.quadratic_trend) > 1e-10:
                vertex = -result.linear_trend / (2 * result.quadratic_trend)
                tp = int(round(vertex + x.mean()))
                tp = max(0, min(n - 1, tp))
                result.turning_point_touch = tp
                if tp < len(mechanisms):
                    result.turning_point_mechanism = mechanisms[tp]
        elif result.trajectory_type == "step_change" and result.changepoint_position is not None:
            result.turning_point_touch = result.changepoint_position
            result.turning_point_mechanism = result.changepoint_mechanism

        return result

    def _detect_changepoint(
        self, y: np.ndarray
    ) -> Tuple[Optional[int], float]:
        """Detect single changepoint via maximum likelihood ratio.

        Tests every possible split point and returns the one with
        maximum reduction in total residual variance.
        """
        n = len(y)
        if n < 4:
            return None, 0.0

        total_var = y.var()
        if total_var < 1e-10:
            return None, 0.0

        best_cp = None
        best_score = 0.0

        for cp in range(2, n - 1):
            left_var = y[:cp].var() if cp >= 2 else 0.0
            right_var = y[cp:].var() if (n - cp) >= 2 else 0.0
            pooled_var = (cp * left_var + (n - cp) * right_var) / n
            score = 1.0 - pooled_var / total_var

            if score > best_score:
                best_score = score
                best_cp = cp

        return best_cp, best_score

    def _classify(self, analysis: TrajectoryAnalysis) -> str:
        """Classify trajectory based on trend estimates."""
        lin = analysis.linear_trend
        quad = analysis.quadratic_trend
        conf = analysis.classification_confidence
        cp = analysis.changepoint_position

        # Need minimum confidence for non-flat classification
        if conf < self.R2_THRESHOLD:
            return "flat"

        # Step change takes priority if strong changepoint detected
        if cp is not None:
            # Check if outcomes before and after changepoint differ significantly
            before = analysis.touch_outcomes[:cp]
            after = analysis.touch_outcomes[cp:]
            if before and after:
                diff = abs(np.mean(after) - np.mean(before))
                if diff > 0.15:
                    return "step_change"

        # Inverted-U: positive linear + negative quadratic
        if lin > 0.02 and quad < -0.005:
            return "inverted_u"

        # Warming: positive linear trend
        if lin > 0.02:
            return "warming"

        # Cooling: negative linear trend
        if lin < -0.02:
            return "cooling"

        return "flat"
