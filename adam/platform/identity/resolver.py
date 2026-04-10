"""
Identity Resolution — pluggable modules for user identity resolution.

ADAM's strongest mode is contextual-only (no user ID needed at all),
but these modules add deterministic/probabilistic identity when available.

Resolution hierarchy:
  1. Deterministic (UID2, first-party) — exact match
  2. Probabilistic (household IP, device graph) — statistical inference
  3. Contextual (ADAM NDF + content psychology) — always available, no ID needed
"""

from __future__ import annotations

import abc
import hashlib
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class IdentityResolution(BaseModel):
    """Result of identity resolution."""
    resolution_type: str
    confidence: float = 0.0
    user_id: Optional[str] = None
    household_id: Optional[str] = None
    device_id: Optional[str] = None
    publisher_id: Optional[str] = None
    uid2_token: Optional[str] = None
    ndf_profile: Optional[Dict[str, float]] = None
    segments: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @property
    def has_deterministic_id(self) -> bool:
        return self.resolution_type in ("uid2", "first_party") and self.confidence > 0.9

    @property
    def has_probabilistic_id(self) -> bool:
        return self.resolution_type == "household" and self.confidence > 0.5

    @property
    def is_contextual_only(self) -> bool:
        return self.resolution_type == "contextual"


class BaseIdentityResolver(abc.ABC):
    """Abstract identity resolver interface."""

    def __init__(self, resolver_type: str):
        self.resolver_type = resolver_type

    @abc.abstractmethod
    async def resolve(self, signals: Dict[str, Any]) -> Optional[IdentityResolution]:
        ...

    @abc.abstractmethod
    def can_resolve(self, signals: Dict[str, Any]) -> bool:
        ...


class ContextualResolver(BaseIdentityResolver):
    """
    ADAM's most powerful resolver — requires NO user identity.

    Uses content psychology, temporal context, device signals, and the
    full 441-construct NDF model to build a psychological profile.
    This is ADAM's core competitive advantage: while competitors need
    identity to target, ADAM targets psychology.
    """

    def __init__(self, content_profiler=None):
        super().__init__("contextual")
        self._profiler = content_profiler

    def can_resolve(self, signals: Dict[str, Any]) -> bool:
        return True  # Always available

    async def resolve(self, signals: Dict[str, Any]) -> Optional[IdentityResolution]:
        ndf_profile = {}
        segments = []

        if self._profiler:
            try:
                profile_result = await self._profiler.profile(
                    title=signals.get("page_title", ""),
                    body=signals.get("page_content", ""),
                    metadata=signals,
                )
                ndf_profile = profile_result.get("ndf_profile", {})
                segments = profile_result.get("segments", [])
            except Exception as e:
                logger.debug("Content profiling failed: %s", e)

        if not ndf_profile:
            ndf_profile = self._infer_from_context(signals)

        return IdentityResolution(
            resolution_type="contextual",
            confidence=0.7 if ndf_profile else 0.3,
            ndf_profile=ndf_profile,
            segments=segments,
            metadata={
                "source": "contextual_ndf",
                "device_type": signals.get("device_type", "unknown"),
                "hour_of_day": signals.get("hour_of_day"),
                "content_category": signals.get("content_category", ""),
            },
        )

    def _infer_from_context(self, signals: Dict[str, Any]) -> Dict[str, float]:
        hour = signals.get("hour_of_day", 12)
        device = signals.get("device_type", "desktop")

        cognitive_engagement = 0.6 if device == "desktop" else 0.4
        if 9 <= hour <= 17:
            cognitive_engagement += 0.1
        elif hour >= 22 or hour < 6:
            cognitive_engagement -= 0.1

        arousal = 0.6 if 8 <= hour <= 20 else 0.4

        return {
            "approach_avoidance": 0.55,
            "temporal_horizon": 0.5,
            "social_calibration": 0.5,
            "uncertainty_tolerance": 0.5,
            "status_sensitivity": 0.5,
            "cognitive_engagement": max(0.1, min(1.0, cognitive_engagement)),
            "arousal_seeking": max(0.1, min(1.0, arousal)),
        }


class FirstPartyResolver(BaseIdentityResolver):
    """
    Publisher First-Party ID resolver.
    Maps publisher-assigned IDs to ADAM profiles.
    """

    def __init__(self, redis_client=None):
        super().__init__("first_party")
        self._redis = redis_client

    def can_resolve(self, signals: Dict[str, Any]) -> bool:
        return bool(signals.get("publisher_user_id") or signals.get("fpi"))

    async def resolve(self, signals: Dict[str, Any]) -> Optional[IdentityResolution]:
        pub_id = signals.get("publisher_user_id") or signals.get("fpi")
        if not pub_id:
            return None

        hashed_id = hashlib.sha256(pub_id.encode()).hexdigest()[:16]
        profile = None

        if self._redis:
            import json
            cached = await self._redis.get(f"identity:fpi:{hashed_id}")
            if cached:
                profile = json.loads(cached) if isinstance(cached, (str, bytes)) else cached

        return IdentityResolution(
            resolution_type="first_party",
            confidence=0.95,
            publisher_id=hashed_id,
            ndf_profile=profile.get("ndf_profile") if profile else None,
            segments=profile.get("segments", []) if profile else [],
            metadata={"publisher_id_hash": hashed_id},
        )


class UID2Resolver(BaseIdentityResolver):
    """
    Unified ID 2.0 / EUID resolver.
    Maps UID2 tokens to ADAM profiles.
    """

    def __init__(self, redis_client=None, uid2_api_key: str = ""):
        super().__init__("uid2")
        self._redis = redis_client
        self._api_key = uid2_api_key

    def can_resolve(self, signals: Dict[str, Any]) -> bool:
        return bool(signals.get("uid2_token") or signals.get("euid_token"))

    async def resolve(self, signals: Dict[str, Any]) -> Optional[IdentityResolution]:
        token = signals.get("uid2_token") or signals.get("euid_token")
        if not token:
            return None

        token_hash = hashlib.sha256(token.encode()).hexdigest()[:16]

        return IdentityResolution(
            resolution_type="uid2",
            confidence=0.98,
            uid2_token=token_hash,
            user_id=token_hash,
            metadata={"uid2_resolved": True},
        )


class HouseholdResolver(BaseIdentityResolver):
    """
    IP-based household inference.
    Groups users by IP address into household-level profiles.
    """

    def __init__(self, redis_client=None):
        super().__init__("household")
        self._redis = redis_client

    def can_resolve(self, signals: Dict[str, Any]) -> bool:
        return bool(signals.get("ip_address"))

    async def resolve(self, signals: Dict[str, Any]) -> Optional[IdentityResolution]:
        ip = signals.get("ip_address")
        if not ip:
            return None

        ip_hash = hashlib.sha256(ip.encode()).hexdigest()[:12]
        household_id = f"hh_{ip_hash}"

        return IdentityResolution(
            resolution_type="household",
            confidence=0.6,
            household_id=household_id,
            metadata={
                "ip_hash": ip_hash,
                "inferred": True,
            },
        )


RESOLVER_REGISTRY = {
    "contextual": ContextualResolver,
    "first_party": FirstPartyResolver,
    "uid2": UID2Resolver,
    "household": HouseholdResolver,
}


async def resolve_identity(
    signals: Dict[str, Any],
    resolvers: Optional[List[BaseIdentityResolver]] = None,
) -> IdentityResolution:
    """
    Run identity resolution through the hierarchy:
    deterministic → probabilistic → contextual.

    Always returns a resolution (contextual is the fallback).
    """
    if resolvers is None:
        resolvers = [
            UID2Resolver(),
            FirstPartyResolver(),
            HouseholdResolver(),
            ContextualResolver(),
        ]

    for resolver in resolvers:
        if resolver.can_resolve(signals):
            try:
                result = await resolver.resolve(signals)
                if result and result.confidence > 0.3:
                    return result
            except Exception as e:
                logger.debug("Resolver %s failed: %s", resolver.resolver_type, e)

    return IdentityResolution(
        resolution_type="contextual",
        confidence=0.3,
        metadata={"fallback": True},
    )
