# =============================================================================
# ADAM Mechanism Merging Service
# Location: adam/platform/shared/mechanism_merging.py
# =============================================================================

"""
MECHANISM MERGING SERVICE

Merge mechanism effectiveness across platforms using Bayesian combination.
"""

import logging
import math
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from adam.platform.shared.models import (
    Platform,
    PlatformMechanismEffectiveness,
    UnifiedMechanismEffectiveness,
    MechanismMergeResult,
)
from adam.infrastructure.redis import ADAMRedisCache

logger = logging.getLogger(__name__)


class MechanismMergingService:
    """
    Service for merging mechanism effectiveness across platforms.
    
    Uses Bayesian combination of Beta distributions to merge
    mechanism posteriors from multiple platforms.
    
    Key insight: Each platform provides independent observations
    that should be combined, not averaged.
    """
    
    # Platform reliability weights (affects prior strength)
    PLATFORM_RELIABILITY = {
        Platform.IHEART: 0.95,  # Audio engagement is reliable
        Platform.WPP: 0.90,     # Display metrics well-calibrated
        Platform.AMAZON: 0.85,  # Reviews are less action-oriented
    }
    
    def __init__(
        self,
        cache: Optional[ADAMRedisCache] = None,
    ):
        self.cache = cache
        
        # In-memory storage (production: Neo4j)
        self._mechanism_store: Dict[str, Dict[str, UnifiedMechanismEffectiveness]] = {}
    
    async def merge_mechanisms(
        self,
        adam_id: str,
        platform: Platform,
        mechanisms: Dict[str, PlatformMechanismEffectiveness],
    ) -> List[MechanismMergeResult]:
        """
        Merge mechanism effectiveness from a platform.
        """
        
        results = []
        
        for mech_id, platform_mech in mechanisms.items():
            result = await self._merge_single_mechanism(
                adam_id, mech_id, platform, platform_mech
            )
            results.append(result)
        
        return results
    
    async def _merge_single_mechanism(
        self,
        adam_id: str,
        mechanism_id: str,
        platform: Platform,
        platform_mech: PlatformMechanismEffectiveness,
    ) -> MechanismMergeResult:
        """
        Merge a single mechanism using Bayesian Beta combination.
        
        The key insight: Beta distributions are conjugate priors.
        If we have Beta(a1, b1) from platform 1 and Beta(a2, b2) from platform 2,
        and they represent independent observations, we can combine them as:
        
        Combined = Beta(a1 + a2 - 1, b1 + b2 - 1)
        
        (Subtracting 1 to avoid double-counting the prior)
        """
        
        # Get existing unified mechanism
        user_mechs = self._mechanism_store.get(adam_id, {})
        existing = user_mechs.get(mechanism_id)
        
        # Apply platform reliability as discount
        reliability = self.PLATFORM_RELIABILITY.get(platform, 0.8)
        discounted_alpha = 1 + (platform_mech.alpha - 1) * reliability
        discounted_beta = 1 + (platform_mech.beta - 1) * reliability
        
        if existing:
            # Bayesian combination
            new_alpha = existing.alpha + discounted_alpha - 1
            new_beta = existing.beta + discounted_beta - 1
            
            # Merge context modulations (weighted average)
            merged_modulations = self._merge_context_modulations(
                existing.context_modulations,
                platform_mech.context_modulations,
                existing_weight=0.6,
                new_weight=0.4,
            )
            
            # Update platform contributions
            platform_contributions = existing.platform_contributions.copy()
            platform_contributions[platform.value] = platform_mech.observation_count
            
        else:
            # First observation for this mechanism
            new_alpha = discounted_alpha
            new_beta = discounted_beta
            merged_modulations = platform_mech.context_modulations.copy()
            platform_contributions = {platform.value: platform_mech.observation_count}
        
        # Create unified mechanism
        unified = UnifiedMechanismEffectiveness(
            mechanism_id=mechanism_id,
            alpha=new_alpha,
            beta=new_beta,
            platform_contributions=platform_contributions,
            context_modulations=merged_modulations,
        )
        
        # Store
        if adam_id not in self._mechanism_store:
            self._mechanism_store[adam_id] = {}
        self._mechanism_store[adam_id][mechanism_id] = unified
        
        # Cache
        if self.cache:
            await self.cache.set(
                f"mechanism:{adam_id}:{mechanism_id}",
                unified.model_dump(),
                ttl=86400,
            )
        
        return MechanismMergeResult(
            mechanism_id=mechanism_id,
            unified=unified,
            platform_inputs={platform.value: platform_mech},
            merge_method="bayesian_beta_combination",
            merge_confidence=self._calculate_confidence(unified),
        )
    
    def _merge_context_modulations(
        self,
        existing: Dict[str, float],
        new: Dict[str, float],
        existing_weight: float,
        new_weight: float,
    ) -> Dict[str, float]:
        """Merge context modulations with weights."""
        
        merged = {}
        all_keys = set(existing.keys()) | set(new.keys())
        
        for key in all_keys:
            existing_val = existing.get(key, 0.0)
            new_val = new.get(key, 0.0)
            
            if key in existing and key in new:
                merged[key] = (
                    existing_val * existing_weight + 
                    new_val * new_weight
                )
            elif key in existing:
                merged[key] = existing_val
            else:
                merged[key] = new_val
        
        return merged
    
    def _calculate_confidence(
        self,
        unified: UnifiedMechanismEffectiveness,
    ) -> float:
        """Calculate confidence based on observation count."""
        total_obs = unified.alpha + unified.beta - 2  # Subtract priors
        
        # Saturating confidence (reaches 0.9 at ~100 observations)
        return min(0.95, 0.3 + 0.6 * (1 - math.exp(-total_obs / 50)))
    
    async def get_unified_mechanisms(
        self,
        adam_id: str,
    ) -> Dict[str, UnifiedMechanismEffectiveness]:
        """Get all unified mechanisms for a user."""
        
        if adam_id in self._mechanism_store:
            return self._mechanism_store[adam_id]
        
        return {}
    
    async def get_mechanism_ranking(
        self,
        adam_id: str,
        context: Optional[Dict[str, str]] = None,
    ) -> List[tuple]:
        """
        Get mechanisms ranked by effectiveness.
        
        Returns list of (mechanism_id, score) tuples.
        """
        
        mechanisms = await self.get_unified_mechanisms(adam_id)
        
        ranked = []
        for mech_id, mech in mechanisms.items():
            score = mech.success_rate
            
            # Apply context modulations
            if context:
                for ctx_key, ctx_value in context.items():
                    mod_key = f"{ctx_key}:{ctx_value}"
                    if mod_key in mech.context_modulations:
                        score *= (1 + mech.context_modulations[mod_key])
            
            ranked.append((mech_id, score))
        
        ranked.sort(key=lambda x: x[1], reverse=True)
        return ranked
