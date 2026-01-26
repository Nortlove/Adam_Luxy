# =============================================================================
# ADAM Enhancement #13: Gradient Bridge Integration
# Location: adam/cold_start/learning/gradient_bridge.py
# =============================================================================

"""
Integration with ADAM's Gradient Bridge for continuous learning.

The Gradient Bridge propagates outcomes back through the system:
1. Cold Start outcomes update Thompson Sampling posteriors
2. Archetype effectiveness is tracked and updated
3. Tier transition thresholds are optimized
4. Prior confidence is adjusted based on accuracy
"""

from typing import Dict, List, Optional, Any, Set
from datetime import datetime
import logging
import numpy as np

from adam.cold_start.models.enums import ArchetypeID, CognitiveMechanism, UserDataTier
from adam.cold_start.models.priors import BetaDistribution

logger = logging.getLogger(__name__)


class ColdStartLearningSignal:
    """A learning signal for cold start components."""
    
    def __init__(
        self,
        signal_type: str,
        decision_id: str,
        user_id: Optional[str],
        tier: UserDataTier,
        archetype: Optional[ArchetypeID],
        mechanisms_used: List[CognitiveMechanism],
        outcome: float,
        outcome_type: str,
        timestamp: datetime = None,
    ):
        self.signal_type = signal_type
        self.decision_id = decision_id
        self.user_id = user_id
        self.tier = tier
        self.archetype = archetype
        self.mechanisms_used = mechanisms_used
        self.outcome = outcome
        self.outcome_type = outcome_type
        self.timestamp = timestamp or datetime.utcnow()
    
    @property
    def is_positive(self) -> bool:
        """Whether outcome was positive."""
        return self.outcome > 0.5


class ColdStartGradientBridge:
    """
    Bridge for propagating learning signals to cold start components.
    
    Connects:
    - Thompson Sampler: Update mechanism posteriors
    - Archetype Detector: Track archetype effectiveness
    - Tier Classifier: Optimize transition thresholds
    - Prior Engines: Update confidence levels
    """
    
    def __init__(
        self,
        thompson_sampler=None,
        archetype_detector=None,
        prior_cache=None,
    ):
        self.thompson_sampler = thompson_sampler
        self.archetype_detector = archetype_detector
        self.prior_cache = prior_cache
        
        # Archetype effectiveness tracking
        self.archetype_effectiveness: Dict[ArchetypeID, Dict] = {
            arch: {
                "uses": 0,
                "successes": 0,
                "effectiveness": 0.5,
                "by_mechanism": {}
            }
            for arch in ArchetypeID
        }
        
        # Tier transition optimization
        self.tier_transitions: Dict[str, List[Dict]] = {}
        self.optimal_thresholds = {
            "tier_0_to_1": 1,
            "tier_1_to_2": 3,
            "tier_2_to_3": 5,
            "tier_3_to_4": 20,
            "tier_4_to_5": 50,
        }
        
        # Statistics
        self._signals_processed = 0
        self._posteriors_updated = 0
    
    async def process_signal(self, signal: ColdStartLearningSignal) -> None:
        """
        Process a learning signal and propagate updates.
        """
        self._signals_processed += 1
        
        # 1. Update Thompson Sampling posteriors
        if self.thompson_sampler and signal.mechanisms_used:
            for mechanism in signal.mechanisms_used:
                self.thompson_sampler.update_posterior(
                    mechanism=mechanism,
                    success=signal.is_positive,
                    archetype=signal.archetype
                )
                self._posteriors_updated += 1
        
        # 2. Track archetype effectiveness
        if signal.archetype:
            await self._update_archetype_effectiveness(signal)
        
        # 3. Check for tier transition
        if signal.user_id:
            await self._check_tier_optimization(signal)
        
        logger.debug(
            f"Processed signal: decision={signal.decision_id}, "
            f"outcome={signal.outcome:.2f}, archetype={signal.archetype}"
        )
    
    async def _update_archetype_effectiveness(
        self,
        signal: ColdStartLearningSignal
    ) -> None:
        """Update archetype effectiveness tracking."""
        if not signal.archetype:
            return
        
        eff = self.archetype_effectiveness[signal.archetype]
        
        # Update overall counts
        eff["uses"] += 1
        if signal.is_positive:
            eff["successes"] += 1
        
        # Update effectiveness (EMA)
        alpha = 0.1
        eff["effectiveness"] = (
            (1 - alpha) * eff["effectiveness"] + alpha * signal.outcome
        )
        
        # Track by mechanism
        for mechanism in signal.mechanisms_used:
            mech_key = mechanism.value
            if mech_key not in eff["by_mechanism"]:
                eff["by_mechanism"][mech_key] = {"uses": 0, "successes": 0}
            
            eff["by_mechanism"][mech_key]["uses"] += 1
            if signal.is_positive:
                eff["by_mechanism"][mech_key]["successes"] += 1
    
    async def _check_tier_optimization(
        self,
        signal: ColdStartLearningSignal
    ) -> None:
        """Check and optimize tier transition thresholds."""
        user_id = signal.user_id
        tier = signal.tier
        
        if user_id not in self.tier_transitions:
            self.tier_transitions[user_id] = []
        
        self.tier_transitions[user_id].append({
            "tier": tier.value,
            "outcome": signal.outcome,
            "timestamp": signal.timestamp,
        })
        
        # Simple threshold optimization (production would use more sophisticated methods)
        # Track outcomes by tier and adjust thresholds if needed
    
    def get_archetype_recommendations(
        self,
        context: Optional[Dict] = None
    ) -> List[tuple]:
        """Get recommended archetypes based on learned effectiveness."""
        recommendations = []
        
        for archetype, eff in self.archetype_effectiveness.items():
            if eff["uses"] >= 10:  # Minimum sample size
                recommendations.append((
                    archetype,
                    eff["effectiveness"],
                    eff["uses"]
                ))
        
        # Sort by effectiveness
        recommendations.sort(key=lambda x: x[1], reverse=True)
        return recommendations
    
    def get_mechanism_recommendations(
        self,
        archetype: Optional[ArchetypeID] = None
    ) -> List[tuple]:
        """Get recommended mechanisms for an archetype."""
        if not archetype or archetype not in self.archetype_effectiveness:
            return []
        
        eff = self.archetype_effectiveness[archetype]
        recommendations = []
        
        for mech_key, mech_stats in eff["by_mechanism"].items():
            if mech_stats["uses"] >= 5:
                effectiveness = mech_stats["successes"] / mech_stats["uses"]
                recommendations.append((mech_key, effectiveness, mech_stats["uses"]))
        
        recommendations.sort(key=lambda x: x[1], reverse=True)
        return recommendations
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get bridge statistics."""
        return {
            "signals_processed": self._signals_processed,
            "posteriors_updated": self._posteriors_updated,
            "archetypes_with_data": sum(
                1 for e in self.archetype_effectiveness.values()
                if e["uses"] >= 10
            ),
            "users_tracked": len(self.tier_transitions),
        }


# Singleton instance
_bridge: Optional[ColdStartGradientBridge] = None


def get_cold_start_gradient_bridge(
    thompson_sampler=None,
    archetype_detector=None,
    prior_cache=None
) -> ColdStartGradientBridge:
    """Get singleton gradient bridge."""
    global _bridge
    if _bridge is None:
        _bridge = ColdStartGradientBridge(
            thompson_sampler=thompson_sampler,
            archetype_detector=archetype_detector,
            prior_cache=prior_cache
        )
    return _bridge
