# =============================================================================
# ADAM Brand Intelligence Service
# Location: adam/output/brand_intelligence/service.py
# =============================================================================

"""
BRAND INTELLIGENCE SERVICE

Match brands to users based on psychological compatibility.
"""

import logging
import math
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from adam.output.brand_intelligence.models import (
    BrandPersonality,
    BrandVoice,
    BrandProfile,
    BrandUserMatch,
)
from adam.infrastructure.redis import ADAMRedisCache
from adam.graph_reasoning.bridge import InteractionBridge

logger = logging.getLogger(__name__)


# =============================================================================
# PERSONALITY → BRAND MAPPING
# =============================================================================

# Big Five to Aaker Brand Personality mappings
# Based on research correlations
BIG_FIVE_TO_BRAND = {
    "openness": {
        "excitement": 0.45,
        "sophistication": 0.35,
    },
    "conscientiousness": {
        "competence": 0.50,
        "sincerity": 0.25,
    },
    "extraversion": {
        "excitement": 0.40,
        "ruggedness": 0.20,
    },
    "agreeableness": {
        "sincerity": 0.55,
        "sophistication": -0.15,
    },
    "neuroticism": {
        "sincerity": 0.20,
        "competence": -0.10,
    },
}


# =============================================================================
# SERVICE
# =============================================================================

class BrandIntelligenceService:
    """
    Service for brand-user psychological matching.
    """
    
    def __init__(
        self,
        cache: Optional[ADAMRedisCache] = None,
        bridge: Optional[InteractionBridge] = None,
    ):
        self.cache = cache
        self.bridge = bridge
        
        # Brand profiles (production: from Neo4j)
        self._brands: Dict[str, BrandProfile] = {}
    
    async def register_brand(
        self,
        profile: BrandProfile,
    ) -> None:
        """Register a brand profile."""
        self._brands[profile.brand_id] = profile
        
        if self.cache:
            await self.cache.set(
                f"brand:{profile.brand_id}",
                profile.model_dump(),
                ttl=86400,
            )
    
    async def get_brand(
        self,
        brand_id: str,
    ) -> Optional[BrandProfile]:
        """Get brand profile."""
        if brand_id in self._brands:
            return self._brands[brand_id]
        
        if self.cache:
            cached = await self.cache.get(f"brand:{brand_id}")
            if cached:
                profile = BrandProfile(**cached)
                self._brands[brand_id] = profile
                return profile
        
        return None
    
    async def match_user_to_brand(
        self,
        brand_id: str,
        user_profile: Dict[str, Any],
    ) -> BrandUserMatch:
        """
        Match a user to a brand.
        
        Args:
            brand_id: Brand to match against
            user_profile: User psychological profile with Big Five, etc.
        
        Returns:
            BrandUserMatch with compatibility scores
        """
        brand = await self.get_brand(brand_id)
        if not brand:
            return BrandUserMatch(
                brand_id=brand_id,
                user_id=user_profile.get("user_id", "unknown"),
                personality_match=0.5,
                voice_fit=0.5,
                mechanism_alignment=0.5,
                overall_match=0.5,
                match_confidence=0.3,
            )
        
        # Compute personality match
        personality_match = self._compute_personality_match(
            brand, user_profile
        )
        
        # Compute voice fit
        voice_fit = self._compute_voice_fit(brand, user_profile)
        
        # Compute mechanism alignment
        mechanism_alignment = self._compute_mechanism_alignment(
            brand, user_profile
        )
        
        # Overall match (weighted)
        overall = (
            personality_match * 0.40 +
            voice_fit * 0.30 +
            mechanism_alignment * 0.30
        )
        
        # Recommend mechanisms
        recommended_mechanisms = self._recommend_mechanisms(
            brand, user_profile
        )
        
        # Recommend tone
        recommended_tone = self._recommend_tone(brand, user_profile)
        
        return BrandUserMatch(
            brand_id=brand_id,
            user_id=user_profile.get("user_id", "unknown"),
            personality_match=personality_match,
            voice_fit=voice_fit,
            mechanism_alignment=mechanism_alignment,
            overall_match=overall,
            match_confidence=0.6,
            recommended_mechanisms=recommended_mechanisms,
            recommended_tone=recommended_tone,
        )
    
    def _compute_personality_match(
        self,
        brand: BrandProfile,
        user: Dict[str, Any],
    ) -> float:
        """
        Compute personality compatibility.
        
        Maps user Big Five to expected brand personality preferences.
        """
        # Get user Big Five
        user_o = user.get("openness", 0.5)
        user_c = user.get("conscientiousness", 0.5)
        user_e = user.get("extraversion", 0.5)
        user_a = user.get("agreeableness", 0.5)
        user_n = user.get("neuroticism", 0.5)
        
        # Compare to brand targets
        target_diff = (
            abs(user_o - brand.target_openness) +
            abs(user_c - brand.target_conscientiousness) +
            abs(user_e - brand.target_extraversion) +
            abs(user_a - brand.target_agreeableness) +
            abs(user_n - brand.target_neuroticism)
        ) / 5
        
        personality_match = 1 - target_diff
        
        # Also check brand personality resonance
        # High openness users prefer exciting/sophisticated brands
        brand_resonance = 0.5
        if user_o > 0.6:
            brand_resonance += (brand.personality.excitement - 0.5) * 0.3
            brand_resonance += (brand.personality.sophistication - 0.5) * 0.2
        if user_a > 0.6:
            brand_resonance += (brand.personality.sincerity - 0.5) * 0.4
        if user_c > 0.6:
            brand_resonance += (brand.personality.competence - 0.5) * 0.3
        
        return (personality_match + min(1, max(0, brand_resonance))) / 2
    
    def _compute_voice_fit(
        self,
        brand: BrandProfile,
        user: Dict[str, Any],
    ) -> float:
        """Compute voice/tone compatibility."""
        
        # Map user traits to preferred voice
        user_e = user.get("extraversion", 0.5)
        user_o = user.get("openness", 0.5)
        user_n = user.get("neuroticism", 0.5)
        
        # High extraversion → energetic voice
        energy_fit = 1 - abs(user_e - brand.voice.energy)
        
        # Low neuroticism → can handle informal
        formality_preference = 0.5 + (user_n - 0.5) * 0.3
        formality_fit = 1 - abs(formality_preference - brand.voice.formality)
        
        return (energy_fit + formality_fit) / 2
    
    def _compute_mechanism_alignment(
        self,
        brand: BrandProfile,
        user: Dict[str, Any],
    ) -> float:
        """Compute mechanism compatibility."""
        
        user_mechanisms = user.get("effective_mechanisms", {})
        if not user_mechanisms:
            return 0.5
        
        # Check if brand's preferred mechanisms work for user
        alignment = 0.5
        for mechanism in brand.preferred_mechanisms:
            if mechanism in user_mechanisms:
                alignment += user_mechanisms[mechanism] * 0.1
        
        # Penalize if user needs mechanisms brand forbids
        for mechanism in brand.forbidden_mechanisms:
            if mechanism in user_mechanisms and user_mechanisms[mechanism] > 0.6:
                alignment -= 0.1
        
        return min(1.0, max(0.0, alignment))
    
    def _recommend_mechanisms(
        self,
        brand: BrandProfile,
        user: Dict[str, Any],
    ) -> List[str]:
        """Recommend mechanisms for brand-user pair."""
        
        user_mechanisms = user.get("effective_mechanisms", {})
        
        # Start with brand preferences
        candidates = brand.preferred_mechanisms.copy()
        
        # Add user effective mechanisms not forbidden by brand
        for mechanism, effectiveness in user_mechanisms.items():
            if (mechanism not in brand.forbidden_mechanisms and 
                mechanism not in candidates and
                effectiveness > 0.5):
                candidates.append(mechanism)
        
        # Limit to top 3
        return candidates[:3]
    
    def _recommend_tone(
        self,
        brand: BrandProfile,
        user: Dict[str, Any],
    ) -> str:
        """Recommend tone for brand-user pair."""
        
        user_e = user.get("extraversion", 0.5)
        user_a = user.get("agreeableness", 0.5)
        
        # Start with brand tone
        base_tone = brand.voice.tone
        
        # Modify based on user
        if user_e > 0.7 and base_tone == "neutral":
            return "energetic"
        if user_a > 0.7 and base_tone == "neutral":
            return "warm"
        if user_e < 0.4:
            return "calm"
        
        return base_tone
    
    async def get_best_brands(
        self,
        user_profile: Dict[str, Any],
        category: Optional[str] = None,
        limit: int = 5,
    ) -> List[BrandUserMatch]:
        """Get best matching brands for a user."""
        
        matches = []
        
        for brand_id, brand in self._brands.items():
            if category and brand.primary_category != category:
                if category not in brand.secondary_categories:
                    continue
            
            match = await self.match_user_to_brand(brand_id, user_profile)
            matches.append(match)
        
        # Sort by overall match
        matches.sort(key=lambda m: m.overall_match, reverse=True)
        
        return matches[:limit]
