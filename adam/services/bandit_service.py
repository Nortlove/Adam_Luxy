# =============================================================================
# ADAM Bandit Service
# Location: adam/services/bandit_service.py
# =============================================================================

"""
BANDIT SERVICE

Implements Thompson Sampling for exploration-exploitation in mechanism selection.

Key Psycholinguistic Insight:
- We don't always know which mechanism will work best for a given context
- Pure exploitation (always use best-known) misses learning opportunities
- Pure exploration (random) wastes many opportunities
- Thompson Sampling balances this optimally using Bayesian updates

This service:
1. Maintains Beta distributions for each mechanism-context pair
2. Samples from posteriors to select mechanisms
3. Updates based on observed outcomes
4. Enables continuous learning about mechanism effectiveness
"""

import logging
import random
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
import math

from neo4j import AsyncDriver

logger = logging.getLogger(__name__)


# =============================================================================
# MODELS
# =============================================================================

@dataclass
class BetaDistribution:
    """
    Beta distribution for Bayesian bandit.
    
    Alpha: successes + 1
    Beta: failures + 1
    
    Mean = alpha / (alpha + beta)
    """
    
    alpha: float = 1.0  # Prior: 1 success
    beta: float = 1.0  # Prior: 1 failure
    
    @property
    def mean(self) -> float:
        """Expected value."""
        return self.alpha / (self.alpha + self.beta)
    
    @property
    def variance(self) -> float:
        """Uncertainty measure."""
        ab = self.alpha + self.beta
        return (self.alpha * self.beta) / (ab * ab * (ab + 1))
    
    @property
    def samples(self) -> int:
        """Total samples observed."""
        return int(self.alpha + self.beta - 2)  # Subtract priors
    
    def sample(self) -> float:
        """Sample from the distribution."""
        return random.betavariate(self.alpha, self.beta)
    
    def update(self, reward: float) -> None:
        """Update based on observed reward (0-1 scale)."""
        # Treat reward as probability of success
        if reward >= 0.5:
            self.alpha += reward
        else:
            self.beta += (1.0 - reward)


@dataclass
class ArmState:
    """State for one arm (mechanism-context pair)."""
    
    arm_id: str
    mechanism_id: str
    context_key: str  # e.g., "archetype:value_conscious_pragmatist"
    
    distribution: BetaDistribution = field(default_factory=BetaDistribution)
    
    # Metadata
    last_selected: Optional[str] = None
    times_selected: int = 0


@dataclass
class BanditDecision:
    """Result of bandit selection."""
    
    selected_arm_id: str
    mechanism_id: str
    sampled_value: float  # The Thompson sample that won
    expected_value: float  # Mean of the distribution
    uncertainty: float  # Variance of the distribution
    exploration_factor: float  # How much exploration influenced this


# =============================================================================
# SERVICE
# =============================================================================

class BanditService:
    """
    Thompson Sampling Bandit for mechanism selection.
    
    Provides:
    - Optimal exploration-exploitation balance
    - Bayesian updates from outcomes
    - Context-aware arm selection
    - Persistence to Neo4j for cross-session learning
    
    Key integration points:
    - Called by mechanism selection nodes in workflow
    - Updated by learning loop when outcomes observed
    - Persists learned distributions to graph
    """
    
    def __init__(
        self,
        neo4j_driver: Optional[AsyncDriver] = None,
        exploration_bonus: float = 0.1,
    ):
        self.driver = neo4j_driver
        self.exploration_bonus = exploration_bonus
        
        # In-memory arm states
        self.arms: Dict[str, ArmState] = {}
        
        # Mechanism catalog
        self.mechanisms = [
            "social_proof",
            "scarcity",
            "authority",
            "reciprocity",
            "commitment",
            "liking",
            "storytelling",
            "fear_appeal",
            "humor",
            "nostalgia",
            "curiosity_gap",
            "cognitive_ease",
            "emotional_contagion",
            "identity_appeal",
            "loss_aversion",
            "value_proposition",
            "exclusivity",
            "urgency",
        ]
        
        logger.info(f"BanditService initialized with {len(self.mechanisms)} mechanisms")
    
    async def select_mechanism(
        self,
        context: Dict[str, Any],
        available_mechanisms: Optional[List[str]] = None,
        n_select: int = 1,
    ) -> List[BanditDecision]:
        """
        Select mechanism(s) using Thompson Sampling.
        
        Context should include:
        - archetype_id: customer archetype
        - brand_id: brand being advertised
        - category_id: product category
        - user_id: specific user (optional)
        
        Returns the top n_select mechanisms with their sampled values.
        """
        
        if available_mechanisms is None:
            available_mechanisms = self.mechanisms
        
        # Build context key
        context_key = self._build_context_key(context)
        
        # Ensure arms exist for this context
        arms = await self._get_or_create_arms(context_key, available_mechanisms)
        
        # Thompson Sampling: sample from each arm's distribution
        samples = []
        for arm in arms:
            sampled = arm.distribution.sample()
            
            # Add exploration bonus for under-sampled arms
            if arm.distribution.samples < 10:
                sampled += self.exploration_bonus * (10 - arm.distribution.samples) / 10
            
            exploration_factor = max(0, (10 - arm.distribution.samples) / 10)
            
            samples.append((
                arm,
                sampled,
                arm.distribution.mean,
                arm.distribution.variance,
                exploration_factor,
            ))
        
        # Sort by sampled value (highest first)
        samples.sort(key=lambda x: x[1], reverse=True)
        
        # Select top n
        decisions = []
        for arm, sampled, mean, var, exp in samples[:n_select]:
            arm.times_selected += 1
            
            decisions.append(BanditDecision(
                selected_arm_id=arm.arm_id,
                mechanism_id=arm.mechanism_id,
                sampled_value=sampled,
                expected_value=mean,
                uncertainty=var,
                exploration_factor=exp,
            ))
        
        return decisions
    
    async def update(
        self,
        context: Dict[str, Any],
        mechanism_id: str,
        reward: float,
    ) -> None:
        """
        Update arm distribution based on observed outcome.
        
        Reward should be 0-1 scale:
        - 1.0 = perfect outcome
        - 0.5 = neutral
        - 0.0 = negative outcome
        """
        
        context_key = self._build_context_key(context)
        arm_id = f"{context_key}::{mechanism_id}"
        
        if arm_id not in self.arms:
            # Create arm if doesn't exist
            self.arms[arm_id] = ArmState(
                arm_id=arm_id,
                mechanism_id=mechanism_id,
                context_key=context_key,
            )
        
        arm = self.arms[arm_id]
        arm.distribution.update(reward)
        
        logger.debug(
            f"Updated arm {arm_id}: reward={reward:.3f}, "
            f"new_mean={arm.distribution.mean:.3f}, "
            f"samples={arm.distribution.samples}"
        )
        
        # Persist to graph
        if self.driver:
            await self._persist_arm(arm)
    
    async def _get_or_create_arms(
        self,
        context_key: str,
        mechanisms: List[str],
    ) -> List[ArmState]:
        """Get or create arms for context-mechanism pairs."""
        
        arms = []
        for mech in mechanisms:
            arm_id = f"{context_key}::{mech}"
            
            if arm_id not in self.arms:
                # Try to load from graph
                if self.driver:
                    loaded = await self._load_arm_from_graph(arm_id)
                    if loaded:
                        self.arms[arm_id] = loaded
                
                # Create new if still not exists
                if arm_id not in self.arms:
                    self.arms[arm_id] = ArmState(
                        arm_id=arm_id,
                        mechanism_id=mech,
                        context_key=context_key,
                    )
            
            arms.append(self.arms[arm_id])
        
        return arms
    
    def _build_context_key(self, context: Dict[str, Any]) -> str:
        """Build context key from context dict."""
        
        parts = []
        
        if context.get("archetype_id"):
            parts.append(f"arch:{context['archetype_id']}")
        if context.get("category_id"):
            parts.append(f"cat:{context['category_id']}")
        if context.get("brand_id"):
            parts.append(f"brand:{context['brand_id']}")
        
        if not parts:
            return "global"
        
        return "|".join(sorted(parts))
    
    async def _load_arm_from_graph(self, arm_id: str) -> Optional[ArmState]:
        """Load arm state from Neo4j."""
        
        try:
            async with self.driver.session() as session:
                result = await session.run(
                    """
                    MATCH (a:BanditArm {arm_id: $arm_id})
                    RETURN a
                    """,
                    arm_id=arm_id
                )
                
                record = await result.single()
                if not record:
                    return None
                
                arm_data = record["a"]
                
                return ArmState(
                    arm_id=arm_id,
                    mechanism_id=arm_data.get("mechanism_id", "unknown"),
                    context_key=arm_data.get("context_key", "unknown"),
                    distribution=BetaDistribution(
                        alpha=arm_data.get("alpha", 1.0),
                        beta=arm_data.get("beta", 1.0),
                    ),
                    times_selected=arm_data.get("times_selected", 0),
                )
                
        except Exception as e:
            logger.debug(f"Could not load arm from graph: {e}")
            return None
    
    async def _persist_arm(self, arm: ArmState) -> None:
        """Persist arm state to Neo4j."""
        
        try:
            async with self.driver.session() as session:
                await session.run(
                    """
                    MERGE (a:BanditArm {arm_id: $arm_id})
                    SET a.mechanism_id = $mechanism_id,
                        a.context_key = $context_key,
                        a.alpha = $alpha,
                        a.beta = $beta,
                        a.times_selected = $times_selected,
                        a.mean = $mean,
                        a.last_updated = datetime()
                    """,
                    arm_id=arm.arm_id,
                    mechanism_id=arm.mechanism_id,
                    context_key=arm.context_key,
                    alpha=arm.distribution.alpha,
                    beta=arm.distribution.beta,
                    times_selected=arm.times_selected,
                    mean=arm.distribution.mean,
                )
        except Exception as e:
            logger.error(f"Error persisting arm to graph: {e}")
    
    async def get_all_arm_stats(
        self,
        context_key: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get statistics for all arms (for debugging/monitoring)."""
        
        stats = []
        for arm in self.arms.values():
            if context_key and arm.context_key != context_key:
                continue
            
            stats.append({
                "arm_id": arm.arm_id,
                "mechanism_id": arm.mechanism_id,
                "context_key": arm.context_key,
                "mean": arm.distribution.mean,
                "variance": arm.distribution.variance,
                "samples": arm.distribution.samples,
                "times_selected": arm.times_selected,
            })
        
        # Sort by mean descending
        stats.sort(key=lambda x: x["mean"], reverse=True)
        return stats


# =============================================================================
# SINGLETON
# =============================================================================

_service: Optional[BanditService] = None


def get_bandit_service(
    neo4j_driver: Optional[AsyncDriver] = None,
) -> BanditService:
    """Get or create the bandit service singleton."""
    global _service
    
    if _service is None:
        _service = BanditService(neo4j_driver=neo4j_driver)
    
    return _service
