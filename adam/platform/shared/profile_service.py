# =============================================================================
# ADAM Cross-Platform Profile Service
# Location: adam/platform/shared/profile_service.py
# =============================================================================

"""
CROSS-PLATFORM PROFILE SERVICE

Merge and manage unified user profiles across platforms.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from adam.platform.shared.models import (
    Platform,
    DataQuality,
    ConflictResolution,
    PlatformBigFive,
    UnifiedBigFive,
    PlatformContribution,
    UnifiedUserProfile,
    ProfileMergeResult,
)
from adam.user.identity import IdentityResolutionService
from adam.infrastructure.redis import ADAMRedisCache
from adam.config.settings import get_settings

logger = logging.getLogger(__name__)


class CrossPlatformProfileService:
    """
    Service for managing unified user profiles across platforms.
    
    Responsibilities:
    1. Merge Big Five profiles from multiple platforms
    2. Resolve conflicts when platforms disagree
    3. Weight contributions by data quality and recency
    4. Maintain audit trail of merges
    """
    
    def __init__(
        self,
        identity_service: Optional["IdentityResolutionService"] = None,
        cache: Optional[ADAMRedisCache] = None,
    ):
        self.identity_service = identity_service
        self.cache = cache
        self._settings = get_settings()
        
        # Platform weights from configuration
        self.PLATFORM_WEIGHTS = {
            Platform.AMAZON: self._settings.weights.amazon_weight,
            Platform.IHEART: self._settings.weights.iheart_weight,
            Platform.WPP: self._settings.weights.wpp_weight,
        }
        
        # Quality weights from configuration
        self.QUALITY_WEIGHTS = {
            DataQuality.VERIFIED: self._settings.weights.verified_quality_weight,
            DataQuality.OBSERVED: self._settings.weights.observed_quality_weight,
            DataQuality.INFERRED: self._settings.weights.inferred_quality_weight,
            DataQuality.PRIOR: self._settings.weights.prior_quality_weight,
        }
        
        # In-memory profile store (production: Neo4j)
        self._profiles: Dict[str, UnifiedUserProfile] = {}
    
    
    async def get_or_create_unified_profile(
        self,
        adam_id: str,
    ) -> UnifiedUserProfile:
        """Get or create unified profile for ADAM ID."""
        
        if adam_id in self._profiles:
            return self._profiles[adam_id]
        
        # Check cache
        if self.cache:
            cached = await self.cache.get(f"unified_profile:{adam_id}")
            if cached:
                profile = UnifiedUserProfile(**cached)
                self._profiles[adam_id] = profile
                return profile
        
        # Create new with defaults
        profile = UnifiedUserProfile(
            adam_id=adam_id,
            big_five=UnifiedBigFive(
                openness=0.5,
                conscientiousness=0.5,
                extraversion=0.5,
                agreeableness=0.5,
                neuroticism=0.5,
                confidence=0.3,
            ),
        )
        
        self._profiles[adam_id] = profile
        return profile
    
    async def add_platform_contribution(
        self,
        adam_id: str,
        platform: Platform,
        big_five: PlatformBigFive,
    ) -> ProfileMergeResult:
        """
        Add or update a platform's contribution to the unified profile.
        """
        
        profile = await self.get_or_create_unified_profile(adam_id)
        
        # Add/update platform contribution
        contribution = profile.contributions.get(platform.value)
        if not contribution:
            contribution = PlatformContribution(
                platform=platform,
                first_seen=datetime.now(timezone.utc),
            )
        
        contribution.big_five = big_five
        contribution.overall_confidence = big_five.confidence
        contribution.data_quality = big_five.quality
        contribution.total_observations = big_five.observation_count
        contribution.last_active = datetime.now(timezone.utc)
        
        profile.contributions[platform.value] = contribution
        
        # Add platform ID if we have identity service
        if self.identity_service:
            # Would look up platform ID here
            pass
        
        # Merge profiles
        result = await self._merge_contributions(profile)
        
        # Cache
        if self.cache:
            await self.cache.set(
                f"unified_profile:{adam_id}",
                profile.model_dump(),
                ttl=86400,
            )
        
        return result
    
    async def _merge_contributions(
        self,
        profile: UnifiedUserProfile,
    ) -> ProfileMergeResult:
        """
        Merge all platform contributions into unified profile.
        """
        
        contributions = list(profile.contributions.values())
        if not contributions:
            return ProfileMergeResult(
                adam_id=profile.adam_id,
                unified_profile=profile,
                platforms_merged=[],
                merge_confidence=0.3,
            )
        
        # Collect Big Five values with weights
        trait_values = {
            "openness": [],
            "conscientiousness": [],
            "extraversion": [],
            "agreeableness": [],
            "neuroticism": [],
        }
        
        conflicts = []
        platforms_used = []
        
        for contrib in contributions:
            if not contrib.big_five:
                continue
            
            platform = contrib.platform
            platforms_used.append(platform)
            bf = contrib.big_five
            
            # Calculate weight
            platform_weight = self.PLATFORM_WEIGHTS.get(platform, 0.3)
            quality_weight = self.QUALITY_WEIGHTS.get(bf.quality, 0.5)
            recency_weight = self._calculate_recency_weight(bf.last_updated)
            
            total_weight = platform_weight * quality_weight * recency_weight * bf.confidence
            
            for trait in trait_values:
                value = getattr(bf, trait)
                trait_values[trait].append((value, total_weight, platform))
        
        # Merge each trait and detect conflicts
        merged_values = {}
        total_confidence = 0.0
        
        for trait, values in trait_values.items():
            if not values:
                merged_values[trait] = 0.5
                continue
            
            # Check for conflicts (>0.2 difference with high confidence)
            max_val = max(v for v, _, _ in values)
            min_val = min(v for v, _, _ in values)
            
            if max_val - min_val > 0.2 and len(values) > 1:
                conflicts.append({
                    "trait": trait,
                    "values": [(p.value, v) for v, _, p in values],
                    "difference": max_val - min_val,
                })
            
            # Weighted average
            total_weight = sum(w for _, w, _ in values)
            if total_weight > 0:
                merged_values[trait] = sum(v * w for v, w, _ in values) / total_weight
                total_confidence += total_weight
            else:
                merged_values[trait] = sum(v for v, _, _ in values) / len(values)
        
        # Update profile
        profile.big_five = UnifiedBigFive(
            openness=merged_values["openness"],
            conscientiousness=merged_values["conscientiousness"],
            extraversion=merged_values["extraversion"],
            agreeableness=merged_values["agreeableness"],
            neuroticism=merged_values["neuroticism"],
            confidence=min(0.95, total_confidence / 5),
            contributing_platforms=platforms_used,
            resolution_method=ConflictResolution.WEIGHTED,
        )
        
        profile.overall_confidence = profile.big_five.confidence
        profile.total_observations = sum(
            c.total_observations for c in contributions
        )
        profile.active_conflicts = [c["trait"] for c in conflicts]
        profile.updated_at = datetime.now(timezone.utc)
        
        return ProfileMergeResult(
            adam_id=profile.adam_id,
            unified_profile=profile,
            platforms_merged=platforms_used,
            conflicts_detected=len(conflicts),
            conflicts_resolved=len(conflicts),  # All resolved via weighting
            conflict_details=conflicts,
            merge_confidence=profile.big_five.confidence,
        )
    
    def _calculate_recency_weight(
        self,
        last_updated: datetime,
    ) -> float:
        """Calculate weight based on recency (exponential decay)."""
        if not last_updated:
            return 0.5
        
        now = datetime.now(timezone.utc)
        if last_updated.tzinfo is None:
            last_updated = last_updated.replace(tzinfo=timezone.utc)
        
        age_hours = (now - last_updated).total_seconds() / 3600
        
        # Half-life and minimum from configuration
        half_life = self._settings.thresholds.recency_half_life_hours
        min_weight = self._settings.thresholds.recency_min_weight
        decay = 0.5 ** (age_hours / half_life)
        
        return max(min_weight, decay)
    
    async def get_profile_for_platform(
        self,
        adam_id: str,
        platform: Platform,
    ) -> Dict[str, Any]:
        """
        Get unified profile adapted for a specific platform.
        
        May apply platform-specific transformations.
        """
        
        profile = await self.get_or_create_unified_profile(adam_id)
        
        # Platform-specific adaptations
        result = {
            "adam_id": adam_id,
            "big_five": profile.big_five.model_dump(),
            "mechanisms": {
                mech_id: mech.model_dump()
                for mech_id, mech in profile.mechanisms.items()
            },
            "promotion_tendency": profile.promotion_tendency,
            "prevention_tendency": profile.prevention_tendency,
            "construal_level": profile.construal_level,
            "confidence": profile.overall_confidence,
        }
        
        # Add platform-specific data if available
        if platform.value in profile.platform_ids:
            result["platform_user_id"] = profile.platform_ids[platform.value]
        
        if platform.value in profile.contributions:
            contrib = profile.contributions[platform.value]
            result["platform_observations"] = contrib.total_observations
            result["platform_last_active"] = contrib.last_active
        
        return result
