# =============================================================================
# Therapeutic Retargeting Engine — Hierarchical Prior Manager
# Location: adam/retargeting/engines/prior_manager.py
# =============================================================================

"""
5-Level Hierarchical Bayesian Prior Manager.

Manages Thompson Sampling posteriors for mechanism effectiveness conditioned
on (mechanism, barrier, archetype) at five levels of granularity:

    Corpus Prior (all campaigns ever)
        ↓ inherits
    Category Prior (luxury transportation, beauty, etc.)
        ↓ inherits
    Brand Prior (LUXY Ride specifically)
        ↓ inherits
    Campaign Prior (LUXY Ride March 2026 launch)
        ↓ inherits
    Sequence Prior (this specific user's retargeting sequence)

Each level inherits from above but can override with local evidence. This
means a new brand launching on ADAM cold-starts from the best available
corpus/category evidence — not flat Beta(2,2) priors.

This is a PLATFORM PRIMITIVE — used by:
- Retargeting engine: per-touch mechanism selection
- Bilateral cascade: first-touch barrier-aware mechanism selection
- Outcome handler: multi-level posterior updates
- Dashboard: mechanism effectiveness reporting at any level
"""

import logging
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from adam.retargeting.research_priors import RESEARCH_EFFECT_SIZES

logger = logging.getLogger(__name__)


class PriorLevel(str, Enum):
    """Hierarchy levels from broadest to most specific."""
    CORPUS = "corpus"         # All campaigns ever
    CATEGORY = "category"     # e.g., luxury_transportation, beauty
    BRAND = "brand"           # e.g., LUXY Ride
    CAMPAIGN = "campaign"     # e.g., LUXY Ride March 2026 launch
    USER = "user"             # Per-user posteriors (Enhancement #36: repeated measures)
    SEQUENCE = "sequence"     # This specific user's retargeting sequence


# Minimum observations before a level's posterior is trusted over its parent
_MIN_OBSERVATIONS_TO_TRUST = {
    PriorLevel.CORPUS: 0,      # Always trusted (root)
    PriorLevel.CATEGORY: 20,   # Need 20 observations to override corpus
    PriorLevel.BRAND: 10,      # Need 10 to override category
    PriorLevel.CAMPAIGN: 5,    # Need 5 to override brand
    PriorLevel.USER: 3,        # Need 3 to override campaign (within-subject)
    PriorLevel.SEQUENCE: 3,    # Need 3 to override user
}

# Population levels that receive design-effect discounted weights.
# User and sequence levels get FULL weight (they ARE this user's data).
# Population levels get discounted weight because same-user observations
# are correlated (Enhancement #36: repeated measures).
_POPULATION_LEVELS = {
    PriorLevel.CORPUS,
    PriorLevel.CATEGORY,
    PriorLevel.BRAND,
    PriorLevel.CAMPAIGN,
}

# Blend weight when a level has enough data to partially override parent
# Computed as: min(1.0, local_observations / trust_threshold)
# So at exactly the threshold, it's a 50/50 blend; above, local dominates.


@dataclass
class BarrierConditionedPosterior:
    """Beta(alpha, beta) posterior for a (mechanism, barrier, archetype) triple.

    Follows the same pattern as ModalityPosterior in adam/meta_learner/models.py
    but keyed by the retargeting-specific triple and aware of its position
    in the 5-level hierarchy.
    """

    mechanism: str
    barrier: str
    archetype: str
    level: PriorLevel

    # Beta distribution parameters
    alpha: float = 2.0  # Weak prior
    beta: float = 2.0

    # Tracking
    sample_count: int = 0
    success_count: int = 0
    last_updated: float = field(default_factory=time.time)

    # Context key (for storage: "corpus", "luxury_transportation", "lux_luxy_ride", etc.)
    context_key: str = ""

    @property
    def mean(self) -> float:
        """Posterior mean: E[Beta(a,b)] = a / (a+b)"""
        return self.alpha / (self.alpha + self.beta)

    @property
    def variance(self) -> float:
        """Posterior variance."""
        a, b = self.alpha, self.beta
        return (a * b) / ((a + b) ** 2 * (a + b + 1))

    @property
    def confidence(self) -> float:
        """Confidence measure: inverse of variance, normalized to [0, 1]."""
        return min(1.0, 1.0 / (1.0 + self.variance * 100))

    def sample(self) -> float:
        """Thompson Sampling: draw from Beta(alpha, beta) posterior."""
        return float(np.random.beta(self.alpha, self.beta))

    def update(self, reward: float, weight: float = 1.0) -> None:
        """Bayesian update: success -> alpha += weight, failure -> beta += weight."""
        self.alpha += reward * weight
        self.beta += (1.0 - reward) * weight
        self.sample_count += 1
        if reward > 0.5:
            self.success_count += 1
        self.last_updated = time.time()


class HierarchicalPriorManager:
    """Manages the 5-level Bayesian prior hierarchy.

    For any (mechanism, barrier, archetype) query, this manager:
    1. Looks up posteriors at all available levels
    2. Blends them based on local evidence strength
    3. Returns an effective posterior for Thompson Sampling

    For outcome updates, this manager:
    1. Updates the posterior at EVERY level simultaneously
    2. Each level gets the same reward signal
    3. Over time, specific levels accumulate enough data to specialize

    Storage: In-memory dict for hot path, Neo4j for persistence.
    Keyed by: (mechanism, barrier, archetype, level, context_key)
    """

    # Debounced persistence thresholds
    _PERSIST_EVERY_N_UPDATES = 100
    _PERSIST_EVERY_SECONDS = 60.0

    def __init__(self, neo4j_driver=None):
        self._driver = neo4j_driver
        # In-memory cache: (mechanism, barrier, archetype, level, context_key) -> posterior
        self._posteriors: Dict[Tuple[str, str, str, str, str], BarrierConditionedPosterior] = {}
        # Thread-safe reentrant lock for concurrent read/write safety.
        # RLock allows get_all_posteriors_for_barrier to call get_effective_posterior
        # (both acquire the lock) without deadlocking.
        self._lock = threading.RLock()
        # Debounced persistence: track updates since last persist
        self._updates_since_persist = 0
        self._last_persist_time = time.time()
        self._persist_pending = False

    def get_effective_posterior(
        self,
        mechanism: str,
        barrier: str,
        archetype: str,
        context: Optional[Dict[str, str]] = None,
    ) -> BarrierConditionedPosterior:
        """Get the blended effective posterior for a (mechanism, barrier, archetype) triple.

        Walks the hierarchy from sequence -> campaign -> brand -> category -> corpus,
        blending based on local evidence strength. Returns a synthetic posterior
        representing the best available estimate.

        Thread-safe: acquires self._lock to prevent torn reads during concurrent
        update_all_levels calls.

        Args:
            mechanism: TherapeuticMechanism value
            barrier: BarrierCategory value
            archetype: Archetype ID
            context: Optional dict with keys: category, brand_id, campaign_id, sequence_id
        """
        context = context or {}

        # Walk hierarchy from BROADEST (corpus) to MOST SPECIFIC (sequence).
        # Each level with sufficient data progressively overrides the parent.
        # Most specific level with enough observations dominates.
        # Enhancement #36: USER level between CAMPAIGN and SEQUENCE for
        # within-subject repeated measures personalization.
        levels_and_keys = [
            (PriorLevel.CORPUS, "corpus"),
            (PriorLevel.CATEGORY, context.get("category", "")),
            (PriorLevel.BRAND, context.get("brand_id", "")),
            (PriorLevel.CAMPAIGN, context.get("campaign_id", "")),
            (PriorLevel.USER, context.get("user_id", "")),
            (PriorLevel.SEQUENCE, context.get("sequence_id", "")),
        ]

        with self._lock:
            effective_alpha = 2.0  # Default weak prior
            effective_beta = 2.0
            found_any = False

            for level, ctx_key in levels_and_keys:  # corpus → sequence order
                if not ctx_key:
                    continue

                posterior = self._get_posterior(mechanism, barrier, archetype, level, ctx_key)
                if posterior is None:
                    continue

                found_any = True
                threshold = _MIN_OBSERVATIONS_TO_TRUST[level]

                if threshold == 0 or posterior.sample_count >= threshold:
                    # This level has enough data — blend with parent estimate.
                    # local_weight increases with observations: at threshold it's
                    # 50/50, above threshold the local level dominates.
                    local_weight = min(
                        1.0, posterior.sample_count / max(threshold, 1)
                    )
                    effective_alpha = (
                        local_weight * posterior.alpha
                        + (1.0 - local_weight) * effective_alpha
                    )
                    effective_beta = (
                        local_weight * posterior.beta
                        + (1.0 - local_weight) * effective_beta
                    )
                # If not enough data at this level, parent estimate carries forward

            # If nothing found at any level, initialize from research priors
            if not found_any:
                effective_alpha, effective_beta = self._research_prior(mechanism, barrier)

        return BarrierConditionedPosterior(
            mechanism=mechanism,
            barrier=barrier,
            archetype=archetype,
            level=PriorLevel.CORPUS,  # Effective = blended
            alpha=effective_alpha,
            beta=effective_beta,
            context_key="effective",
        )

    def update_all_levels(
        self,
        mechanism: str,
        barrier: str,
        archetype: str,
        reward: float,
        context: Optional[Dict[str, str]] = None,
        weight: float = 1.0,
        design_effect_weight: Optional[float] = None,
    ) -> int:
        """Update posteriors at ALL hierarchy levels simultaneously.

        This is the key to both system-level and campaign-level learning:
        a single LUXY Ride conversion updates the sequence, campaign, brand,
        category, AND corpus posteriors.

        Enhancement #36 (repeated measures): When design_effect_weight is
        provided, population levels (corpus, category, brand, campaign) get
        discounted weight because same-user observations are correlated.
        User and sequence levels get full weight (they ARE this user's data).

        Without design-effect correction, 7 touches from 1 user look like
        7 independent observations to the population posteriors — inflating
        sample size and making posteriors overconfident. With correction,
        those 7 touches contribute ~2.7 effective observations (at ICC=0.4).

        Args:
            mechanism: TherapeuticMechanism value
            barrier: BarrierCategory value
            archetype: Archetype ID
            reward: 0.0 (failure) to 1.0 (success)
            context: Dict with category, brand_id, campaign_id, user_id, sequence_id
            weight: Signal weight (e.g., from helpful_vote_weight)
            design_effect_weight: ICC-based discount for population levels (0.0-1.0).
                If None, all levels get full weight (backward compatible).

        Returns:
            Number of levels updated
        """
        context = context or {}
        updated = 0

        levels_and_keys = [
            (PriorLevel.CORPUS, "corpus"),
            (PriorLevel.CATEGORY, context.get("category", "")),
            (PriorLevel.BRAND, context.get("brand_id", "")),
            (PriorLevel.CAMPAIGN, context.get("campaign_id", "")),
            (PriorLevel.USER, context.get("user_id", "")),
            (PriorLevel.SEQUENCE, context.get("sequence_id", "")),
        ]

        with self._lock:
            for level, ctx_key in levels_and_keys:
                if not ctx_key:
                    continue

                # Apply design-effect discount to population levels only.
                # User and sequence levels get full weight — this IS their data.
                effective_weight = weight
                if (
                    design_effect_weight is not None
                    and level in _POPULATION_LEVELS
                ):
                    effective_weight = weight * design_effect_weight

                posterior = self._get_or_create_posterior(
                    mechanism, barrier, archetype, level, ctx_key
                )
                posterior.update(reward, effective_weight)
                updated += 1

        if updated > 0:
            self._updates_since_persist += updated
            logger.debug(
                "Updated %d levels: mech=%s barrier=%s arch=%s reward=%.2f",
                updated, mechanism, barrier, archetype, reward,
            )

            # Check if debounced persistence threshold reached
            elapsed = time.time() - self._last_persist_time
            if (
                self._updates_since_persist >= self._PERSIST_EVERY_N_UPDATES
                or elapsed >= self._PERSIST_EVERY_SECONDS
            ) and not self._persist_pending:
                self._persist_pending = True
                self._schedule_persist()

        return updated

    def _schedule_persist(self) -> None:
        """Schedule an async persist without blocking the update path."""
        import asyncio
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._debounced_persist())
        except RuntimeError:
            # No running event loop — persist will happen on next opportunity
            self._persist_pending = False

    async def _debounced_persist(self) -> None:
        """Persist to Neo4j and reset counters."""
        try:
            count = await self.persist_to_neo4j()
            if count > 0:
                logger.info(
                    "Debounced persist: wrote %d posteriors after %d updates",
                    count, self._updates_since_persist,
                )
        except Exception as e:
            logger.warning("Debounced persist failed: %s", e)
        finally:
            self._updates_since_persist = 0
            self._last_persist_time = time.time()
            self._persist_pending = False

    def get_all_posteriors_for_barrier(
        self,
        barrier: str,
        archetype: str,
        context: Optional[Dict[str, str]] = None,
    ) -> Dict[str, BarrierConditionedPosterior]:
        """Get effective posteriors for ALL mechanisms that can address a barrier.

        Used by BayesianMechanismSelector to run Thompson Sampling across
        all candidate mechanisms for a given barrier.

        Thread-safe: acquires self._lock (reentrant) so the entire batch of
        get_effective_posterior calls sees a consistent snapshot.

        Returns:
            {mechanism_name: effective_posterior}
        """
        from adam.constants import BARRIER_MECHANISM_CANDIDATES

        candidates = BARRIER_MECHANISM_CANDIDATES.get(barrier, [])
        result = {}

        with self._lock:
            for mechanism in candidates:
                result[mechanism] = self.get_effective_posterior(
                    mechanism, barrier, archetype, context
                )

        return result

    def get_barrier_prevalence(
        self,
        archetype: str,
        context: Optional[Dict[str, str]] = None,
    ) -> Dict[str, float]:
        """Get prevalence of each barrier type for an archetype.

        Used by the bilateral cascade to inform first-touch mechanism selection:
        "For Careful Trusters in luxury transportation, trust_deficit is
        diagnosed 45% of the time — lead with evidence_proof."

        Thread-safe: acquires self._lock to read consistent posterior counts.

        Returns:
            {barrier_name: prevalence_estimate}
        """
        # Aggregate from stored posteriors — count how many observations
        # each barrier has at the most specific available level
        from adam.constants import BARRIER_CATEGORIES

        with self._lock:
            totals: Dict[str, int] = {}
            for barrier in BARRIER_CATEGORIES:
                total = 0
                # Sum observations across all mechanisms for this barrier
                for key, posterior in self._posteriors.items():
                    mech, bar, arch, level, ctx = key
                    if bar == barrier and arch == archetype:
                        total += posterior.sample_count
                totals[barrier] = total

        grand_total = max(sum(totals.values()), 1)
        return {b: count / grand_total for b, count in totals.items()}

    # --- Internal ---

    def _get_posterior(
        self,
        mechanism: str,
        barrier: str,
        archetype: str,
        level: PriorLevel,
        context_key: str,
    ) -> Optional[BarrierConditionedPosterior]:
        """Lookup from in-memory cache."""
        key = (mechanism, barrier, archetype, level.value, context_key)
        return self._posteriors.get(key)

    def _get_or_create_posterior(
        self,
        mechanism: str,
        barrier: str,
        archetype: str,
        level: PriorLevel,
        context_key: str,
    ) -> BarrierConditionedPosterior:
        """Get existing or create with research-seeded prior."""
        key = (mechanism, barrier, archetype, level.value, context_key)
        posterior = self._posteriors.get(key)
        if posterior is None:
            alpha, beta = self._research_prior(mechanism, barrier)
            posterior = BarrierConditionedPosterior(
                mechanism=mechanism,
                barrier=barrier,
                archetype=archetype,
                level=level,
                alpha=alpha,
                beta=beta,
                context_key=context_key,
            )
            self._posteriors[key] = posterior
        return posterior

    def _research_prior(
        self,
        mechanism: str,
        barrier: str,
    ) -> Tuple[float, float]:
        """Initialize Beta(alpha, beta) from research effect sizes.

        Higher calibrated effect size -> higher alpha relative to beta,
        expressing prior belief that this mechanism is effective.

        Uses the CALIBRATED effect sizes (not published) from research_priors.py.
        """
        # Map mechanisms to their research evidence
        mechanism_evidence = {
            "evidence_proof": "computer_scaffolding_between_subjects",
            "narrative_transportation": "transportation_affective",
            "social_proof_matched": "self_efficacy_performance",
            "autonomy_restoration": "autonomy_support_intrinsic_motivation",
            "construal_shift": "construal_fit_advertising",
            "ownership_reactivation": "peck_shu_ownership",
            "implementation_intention": "implementation_intentions",
            "micro_commitment": "foot_in_door",
            "dissonance_activation": "dissonance_artifact_corrected",
            "loss_framing": "peck_shu_ownership",
            "anxiety_resolution": "rupture_repair_outcome",
            "frustration_control": "computer_scaffolding_between_subjects",
            "novelty_disruption": "mere_exposure_overall",
            "vivid_scenario": "narrative_behavior_change",
            "price_anchor": "construal_fit_advertising",
            "claude_argument": "llm_persuasion_debate",
        }

        evidence_key = mechanism_evidence.get(mechanism)
        if not evidence_key or evidence_key not in RESEARCH_EFFECT_SIZES:
            return 2.0, 2.0  # Weak uniform prior

        entry = RESEARCH_EFFECT_SIZES[evidence_key]

        # Extract calibrated effect size (prefer calibrated, then published, then raw)
        d = (
            entry.get("calibrated_d")
            or entry.get("d")
            or entry.get("calibrated_g")
            or entry.get("g")
        )
        r = entry.get("r")

        if d is not None:
            # Convert d to probability via normal CDF approximation
            # P(success) ≈ Φ(d/√2) for d around 0-1
            prob = min(0.85, max(0.15, 0.5 + 0.2 * d))
        elif r is not None:
            prob = min(0.85, max(0.15, 0.5 + 0.3 * abs(r)))
        else:
            prob = 0.5

        # Convert to Beta parameters with total strength of 4 (weak prior)
        # Beta(a, b) where a + b = 4 and a/(a+b) = prob
        total = 4.0
        alpha = prob * total
        beta = (1.0 - prob) * total

        return round(alpha, 2), round(beta, 2)

    # --- Persistence ---

    async def load_from_neo4j(self) -> int:
        """Load all MechanismPrior nodes from Neo4j into memory.

        Called at startup to warm the cache. Returns count loaded.
        """
        if not self._driver:
            return 0

        try:
            async with self._driver.session() as session:
                result = await session.run(
                    "MATCH (mp:MechanismPrior) RETURN mp"
                )
                count = 0
                async for record in result:
                    mp = record["mp"]
                    key = (
                        mp["mechanism"],
                        mp["barrier_category"],
                        mp["archetype_id"],
                        mp.get("level", "corpus"),
                        mp.get("context_key", "corpus"),
                    )
                    self._posteriors[key] = BarrierConditionedPosterior(
                        mechanism=mp["mechanism"],
                        barrier=mp["barrier_category"],
                        archetype=mp["archetype_id"],
                        level=PriorLevel(mp.get("level", "corpus")),
                        alpha=mp["alpha"],
                        beta=mp["beta"],
                        sample_count=mp.get("sample_count", 0),
                        success_count=mp.get("success_count", 0),
                        context_key=mp.get("context_key", "corpus"),
                    )
                    count += 1
                logger.info("Loaded %d mechanism priors from Neo4j", count)
                return count
        except Exception as e:
            logger.warning("Failed to load priors from Neo4j: %s", e)
            return 0

    async def persist_to_neo4j(self) -> int:
        """Persist all in-memory posteriors to Neo4j.

        Called periodically or at shutdown. Returns count persisted.
        """
        if not self._driver:
            return 0

        count = 0
        try:
            async with self._driver.session() as session:
                for key, posterior in self._posteriors.items():
                    mechanism, barrier, archetype, level, ctx_key = key
                    await session.run(
                        """
                        MERGE (mp:MechanismPrior {
                            mechanism: $mechanism,
                            barrier_category: $barrier,
                            archetype_id: $archetype,
                            level: $level,
                            context_key: $context_key
                        })
                        SET mp.alpha = $alpha,
                            mp.beta = $beta,
                            mp.sample_count = $sample_count,
                            mp.success_count = $success_count,
                            mp.last_updated = datetime()
                        """,
                        mechanism=mechanism,
                        barrier=barrier,
                        archetype=archetype,
                        level=level,
                        context_key=ctx_key,
                        alpha=posterior.alpha,
                        beta=posterior.beta,
                        sample_count=posterior.sample_count,
                        success_count=posterior.success_count,
                    )
                    count += 1
            logger.info("Persisted %d mechanism priors to Neo4j", count)
        except Exception as e:
            logger.warning("Failed to persist priors to Neo4j: %s", e)
        return count

    @property
    def stats(self) -> Dict[str, Any]:
        """Summary statistics for monitoring."""
        total = len(self._posteriors)
        by_level = {}
        for key, p in self._posteriors.items():
            level = key[3]
            by_level[level] = by_level.get(level, 0) + 1

        total_observations = sum(p.sample_count for p in self._posteriors.values())
        return {
            "total_posteriors": total,
            "by_level": by_level,
            "total_observations": total_observations,
            "updates_since_persist": self._updates_since_persist,
        }


# =============================================================================
# SINGLETON
# =============================================================================

_prior_manager_instance: Optional[HierarchicalPriorManager] = None


def get_prior_manager(neo4j_driver=None) -> HierarchicalPriorManager:
    """Get or create the singleton HierarchicalPriorManager.

    On first call, if a neo4j_driver is provided, the manager is initialized
    with persistence. Subsequent calls return the same instance (driver
    argument is ignored after initialization).
    """
    global _prior_manager_instance
    if _prior_manager_instance is None:
        _prior_manager_instance = HierarchicalPriorManager(neo4j_driver=neo4j_driver)
        logger.info("HierarchicalPriorManager singleton created")
    return _prior_manager_instance
