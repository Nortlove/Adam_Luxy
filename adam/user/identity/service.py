# =============================================================================
# ADAM Identity Resolution Service
# Location: adam/user/identity/service.py
# =============================================================================

"""
IDENTITY RESOLUTION SERVICE

Resolve and link user identities across platforms.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from adam.user.identity.models import (
    IdentityType,
    MatchMethod,
    PlatformIdentity,
    IdentityMatch,
    UnifiedIdentity,
)
from adam.infrastructure.redis import ADAMRedisCache
from adam.graph_reasoning.bridge import InteractionBridge

logger = logging.getLogger(__name__)


class IdentityResolutionService:
    """
    Service for cross-platform identity resolution.
    
    Supported identity types:
    - UID 2.0
    - RampID
    - iHeart IDs
    - WPP IDs
    - Device IDs
    - Hashed emails
    """
    
    def __init__(
        self,
        cache: Optional[ADAMRedisCache] = None,
        bridge: Optional[InteractionBridge] = None,
    ):
        self.cache = cache
        self.bridge = bridge
        
        # In-memory identity graph (production: use Neo4j)
        self._identity_map: Dict[str, UnifiedIdentity] = {}
        self._reverse_map: Dict[str, str] = {}  # platform_id -> adam_id
    
    async def resolve_identity(
        self,
        platform: str,
        identity_type: IdentityType,
        identity_value: str,
    ) -> UnifiedIdentity:
        """
        Resolve or create a unified identity.
        
        If identity exists, returns existing unified identity.
        If new, creates new unified identity with ADAM ID.
        """
        
        # Check reverse map for existing match
        key = f"{platform}:{identity_type.value}:{identity_value}"
        
        if key in self._reverse_map:
            adam_id = self._reverse_map[key]
            return self._identity_map[adam_id]
        
        # Check cache
        if self.cache:
            cached = await self.cache.get(f"identity:{key}")
            if cached:
                return UnifiedIdentity(**cached)
        
        # Create new unified identity
        adam_id = f"adam_{uuid4().hex[:16]}"
        
        platform_identity = PlatformIdentity(
            platform=platform,
            identity_type=identity_type,
            identity_value=identity_value,
        )
        
        unified = UnifiedIdentity(
            adam_id=adam_id,
            platform_ids={platform: platform_identity},
        )
        
        # Store
        self._identity_map[adam_id] = unified
        self._reverse_map[key] = adam_id
        
        # Cache
        if self.cache:
            await self.cache.set(f"identity:{key}", unified.model_dump(), ttl=86400)
        
        return unified
    
    async def link_identities(
        self,
        identity1: PlatformIdentity,
        identity2: PlatformIdentity,
        match_method: MatchMethod = MatchMethod.DETERMINISTIC,
        confidence: float = 0.9,
    ) -> UnifiedIdentity:
        """
        Link two platform identities together.
        """
        
        # Resolve both identities
        unified1 = await self.resolve_identity(
            identity1.platform,
            identity1.identity_type,
            identity1.identity_value,
        )
        
        key2 = f"{identity2.platform}:{identity2.identity_type.value}:{identity2.identity_value}"
        
        # Check if identity2 already linked elsewhere
        if key2 in self._reverse_map:
            adam_id2 = self._reverse_map[key2]
            if adam_id2 != unified1.adam_id:
                # Merge identities
                unified1 = await self._merge_identities(
                    unified1.adam_id, adam_id2
                )
        
        # Add identity2 to unified1
        unified1.add_identity(identity2)
        
        # Create match record
        match = IdentityMatch(
            match_id=f"match_{uuid4().hex[:8]}",
            source_identity=identity1,
            target_identity=identity2,
            match_method=match_method,
            match_confidence=confidence,
        )
        unified1.matches.append(match)
        
        # Update maps
        self._identity_map[unified1.adam_id] = unified1
        self._reverse_map[key2] = unified1.adam_id
        
        return unified1
    
    async def _merge_identities(
        self,
        adam_id1: str,
        adam_id2: str,
    ) -> UnifiedIdentity:
        """Merge two unified identities."""
        
        unified1 = self._identity_map.get(adam_id1)
        unified2 = self._identity_map.get(adam_id2)
        
        if not unified1 or not unified2:
            return unified1 or unified2 or UnifiedIdentity(adam_id=adam_id1)
        
        # Merge platform_ids from unified2 into unified1
        for platform, identity in unified2.platform_ids.items():
            if platform not in unified1.platform_ids:
                unified1.add_identity(identity)
        
        # Merge matches
        unified1.matches.extend(unified2.matches)
        
        # Update reverse map
        for platform, identity in unified2.platform_ids.items():
            key = f"{platform}:{identity.identity_type.value}:{identity.identity_value}"
            self._reverse_map[key] = adam_id1
        
        # Remove unified2
        del self._identity_map[adam_id2]
        
        return unified1
    
    async def get_identity_by_adam_id(
        self,
        adam_id: str,
    ) -> Optional[UnifiedIdentity]:
        """Get unified identity by ADAM ID."""
        return self._identity_map.get(adam_id)
    
    async def get_identity_by_platform(
        self,
        platform: str,
        identity_value: str,
        identity_type: IdentityType = IdentityType.FIRST_PARTY,
    ) -> Optional[UnifiedIdentity]:
        """Get unified identity by platform ID."""
        key = f"{platform}:{identity_type.value}:{identity_value}"
        
        if key in self._reverse_map:
            adam_id = self._reverse_map[key]
            return self._identity_map.get(adam_id)
        
        return None
    
    async def get_cross_platform_ids(
        self,
        adam_id: str,
    ) -> Dict[str, str]:
        """Get all platform IDs for a unified identity."""
        unified = self._identity_map.get(adam_id)
        if not unified:
            return {}
        
        return {
            platform: identity.identity_value
            for platform, identity in unified.platform_ids.items()
        }
