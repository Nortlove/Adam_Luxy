# =============================================================================
# ADAM Cold Start Service
# Location: adam/user/cold_start/service.py
# =============================================================================

"""
COLD START SERVICE

Service for bootstrapping new users from minimal signals.

Capabilities:
1. Match users to Amazon archetypes
2. Use iHeart station priors for audio users
3. Use category priors for product users
4. Progressive profile enrichment
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from adam.user.cold_start.archetypes import (
    UserArchetype,
    ArchetypeMatch,
    BigFivePrior,
    AMAZON_ARCHETYPES,
)
from adam.infrastructure.redis import ADAMRedisCache
from adam.graph_reasoning.bridge import InteractionBridge

logger = logging.getLogger(__name__)


# =============================================================================
# COLD START MODELS
# =============================================================================

class ColdStartContext(BaseModel):
    """Context available for cold start."""
    
    user_id: str
    
    # Platform signals
    platform: Optional[str] = None  # "iheart", "wpp", "web"
    
    # iHeart-specific
    station_id: Optional[str] = None
    station_format: Optional[str] = None
    
    # Category signals
    category: Optional[str] = None
    product_category: Optional[str] = None
    
    # Temporal
    time_of_day: Optional[str] = None
    day_of_week: Optional[str] = None
    
    # Device/context
    device_type: Optional[str] = None
    referrer: Optional[str] = None
    
    # Any available behavioral signals
    behavioral_signals: Dict[str, Any] = Field(default_factory=dict)


class ColdStartResult(BaseModel):
    """Result of cold start initialization."""
    
    user_id: str
    
    # Archetype match
    archetype_match: Optional[ArchetypeMatch] = None
    
    # Inferred profile
    big_five: BigFivePrior
    regulatory_focus: Dict[str, float]
    construal_level: float
    mechanism_priors: Dict[str, float]
    
    # Confidence
    overall_confidence: float = Field(ge=0.0, le=1.0)
    data_tier: str = Field(default="cold_start")
    
    # Sources used
    sources_used: List[str] = Field(default_factory=list)
    
    # Timing
    initialized_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


# =============================================================================
# STATION FORMAT PRIORS (for iHeart)
# =============================================================================

STATION_FORMAT_PRIORS = {
    "CHR": {  # Contemporary Hit Radio
        "big_five": BigFivePrior(
            openness=0.55, conscientiousness=0.48,
            extraversion=0.68, agreeableness=0.55, neuroticism=0.52
        ),
        "promotion_tendency": 0.65,
        "abstract_tendency": 0.45,
    },
    "Hot_AC": {  # Hot Adult Contemporary
        "big_five": BigFivePrior(
            openness=0.52, conscientiousness=0.55,
            extraversion=0.60, agreeableness=0.58, neuroticism=0.48
        ),
        "promotion_tendency": 0.55,
        "abstract_tendency": 0.50,
    },
    "Country": {
        "big_five": BigFivePrior(
            openness=0.42, conscientiousness=0.62,
            extraversion=0.55, agreeableness=0.65, neuroticism=0.45
        ),
        "promotion_tendency": 0.45,
        "abstract_tendency": 0.35,
    },
    "Classic_Rock": {
        "big_five": BigFivePrior(
            openness=0.55, conscientiousness=0.52,
            extraversion=0.58, agreeableness=0.50, neuroticism=0.48
        ),
        "promotion_tendency": 0.50,
        "abstract_tendency": 0.45,
    },
    "News_Talk": {
        "big_five": BigFivePrior(
            openness=0.65, conscientiousness=0.68,
            extraversion=0.48, agreeableness=0.52, neuroticism=0.50
        ),
        "promotion_tendency": 0.48,
        "abstract_tendency": 0.65,
    },
    "Urban": {
        "big_five": BigFivePrior(
            openness=0.58, conscientiousness=0.48,
            extraversion=0.72, agreeableness=0.55, neuroticism=0.52
        ),
        "promotion_tendency": 0.62,
        "abstract_tendency": 0.42,
    },
}


# =============================================================================
# COLD START SERVICE
# =============================================================================

class ColdStartService:
    """
    Service for initializing cold-start users.
    """
    
    def __init__(
        self,
        cache: Optional[ADAMRedisCache] = None,
        bridge: Optional[InteractionBridge] = None,
    ):
        self.cache = cache
        self.bridge = bridge
        self.archetypes = AMAZON_ARCHETYPES
        self.station_priors = STATION_FORMAT_PRIORS
    
    async def initialize_user(
        self,
        context: ColdStartContext,
    ) -> ColdStartResult:
        """
        Initialize a cold-start user with priors.
        
        Strategy:
        1. Check for station priors (iHeart)
        2. Check for category priors
        3. Match to Amazon archetype
        4. Blend available priors
        """
        sources_used = []
        
        # Try station priors first (iHeart)
        station_prior = None
        if context.station_format:
            station_prior = self.station_priors.get(context.station_format)
            if station_prior:
                sources_used.append(f"station:{context.station_format}")
        
        # Try archetype matching
        archetype_match = await self._match_archetype(context)
        if archetype_match:
            sources_used.append(f"archetype:{archetype_match.primary_archetype.archetype_id}")
        
        # Blend priors
        result = self._blend_priors(
            context=context,
            station_prior=station_prior,
            archetype_match=archetype_match,
            sources_used=sources_used,
        )
        
        # Cache the result
        if self.cache:
            await self._cache_result(result)
        
        return result
    
    async def _match_archetype(
        self,
        context: ColdStartContext,
    ) -> Optional[ArchetypeMatch]:
        """Match user to Amazon archetypes based on available signals."""
        
        if not context.behavioral_signals and not context.category:
            return None
        
        scores = {}
        
        for arch_id, archetype in self.archetypes.items():
            score = 0.0
            
            # Category affinity matching
            if context.category:
                category_score = archetype.category_affinities.get(
                    context.category, 0.3
                )
                score += category_score * 0.4
            
            # Platform-specific matching
            if context.platform == "iheart":
                # Audio users tend toward certain archetypes
                if arch_id in ["connector", "explorer", "enthusiast"]:
                    score += 0.1
            elif context.platform == "wpp":
                # Display users distribution
                if arch_id in ["analyzer", "pragmatist"]:
                    score += 0.05
            
            # Time-based hints
            if context.time_of_day:
                if context.time_of_day in ["morning", "afternoon"] and arch_id == "achiever":
                    score += 0.05
                elif context.time_of_day in ["evening", "night"] and arch_id == "explorer":
                    score += 0.05
            
            # Normalize by population percentage (prior)
            score = score * 0.7 + archetype.population_percentage * 0.3
            scores[arch_id] = score
        
        if not scores:
            return None
        
        # Get best match
        best_id = max(scores, key=scores.get)
        best_archetype = self.archetypes[best_id]
        best_score = scores[best_id]
        
        # Get secondary matches
        sorted_scores = sorted(
            [(k, v) for k, v in scores.items() if k != best_id],
            key=lambda x: x[1],
            reverse=True,
        )[:2]
        
        # Blend Big Five
        blended = self._blend_big_five(
            [(best_archetype.big_five, best_score)] +
            [(self.archetypes[k].big_five, v) for k, v in sorted_scores]
        )
        
        return ArchetypeMatch(
            user_id=context.user_id,
            primary_archetype=best_archetype,
            primary_confidence=min(0.7, best_score),
            secondary_archetypes=sorted_scores,
            blended_big_five=blended,
            blended_mechanism_priors={
                mp.mechanism_name: mp.effectiveness
                for mp in best_archetype.mechanism_priors
            },
            matching_signals_used=[
                s for s in [context.category, context.platform, context.time_of_day]
                if s
            ],
        )
    
    def _blend_priors(
        self,
        context: ColdStartContext,
        station_prior: Optional[Dict],
        archetype_match: Optional[ArchetypeMatch],
        sources_used: List[str],
    ) -> ColdStartResult:
        """Blend available priors into final result."""
        
        # Start with default
        big_five = BigFivePrior()
        reg_focus = {"promotion": 0.5, "prevention": 0.5}
        construal = 0.5
        mechanisms = {}
        confidence = 0.3
        
        # Apply station prior (weight 0.4)
        if station_prior:
            station_bf = station_prior["big_five"]
            big_five = self._weighted_blend_bf(
                [(big_five, 0.6), (station_bf, 0.4)]
            )
            reg_focus["promotion"] = station_prior["promotion_tendency"]
            reg_focus["prevention"] = 1 - station_prior["promotion_tendency"]
            construal = station_prior["abstract_tendency"]
            confidence = max(confidence, 0.45)
        
        # Apply archetype (weight 0.5)
        if archetype_match:
            arch = archetype_match.primary_archetype
            big_five = self._weighted_blend_bf(
                [(big_five, 0.5), (arch.big_five, 0.5)]
            )
            reg_focus["promotion"] = (reg_focus["promotion"] + arch.promotion_tendency) / 2
            reg_focus["prevention"] = (reg_focus["prevention"] + arch.prevention_tendency) / 2
            construal = (construal + arch.abstract_tendency) / 2
            mechanisms = archetype_match.blended_mechanism_priors
            confidence = max(confidence, archetype_match.primary_confidence)
        
        return ColdStartResult(
            user_id=context.user_id,
            archetype_match=archetype_match,
            big_five=big_five,
            regulatory_focus=reg_focus,
            construal_level=construal,
            mechanism_priors=mechanisms,
            overall_confidence=confidence,
            sources_used=sources_used,
        )
    
    def _blend_big_five(
        self,
        priors: List[tuple],
    ) -> BigFivePrior:
        """Blend multiple Big Five priors with weights."""
        if not priors:
            return BigFivePrior()
        
        total_weight = sum(w for _, w in priors)
        if total_weight == 0:
            return priors[0][0]
        
        blended = BigFivePrior(
            openness=sum(p.openness * w for p, w in priors) / total_weight,
            conscientiousness=sum(p.conscientiousness * w for p, w in priors) / total_weight,
            extraversion=sum(p.extraversion * w for p, w in priors) / total_weight,
            agreeableness=sum(p.agreeableness * w for p, w in priors) / total_weight,
            neuroticism=sum(p.neuroticism * w for p, w in priors) / total_weight,
        )
        return blended
    
    def _weighted_blend_bf(
        self,
        priors: List[tuple],
    ) -> BigFivePrior:
        """Alias for _blend_big_five."""
        return self._blend_big_five(priors)
    
    async def _cache_result(self, result: ColdStartResult) -> None:
        """Cache cold start result."""
        if self.cache:
            key = f"cold_start:{result.user_id}"
            await self.cache.set(key, result.model_dump(), ttl=86400)
    
    async def get_cached_result(
        self,
        user_id: str,
    ) -> Optional[ColdStartResult]:
        """Get cached cold start result."""
        if not self.cache:
            return None
        
        key = f"cold_start:{user_id}"
        data = await self.cache.get(key)
        if data:
            return ColdStartResult(**data)
        return None
