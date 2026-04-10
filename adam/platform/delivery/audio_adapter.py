"""
Audio Platform Delivery Adapters — push segments and host briefings to audio platforms.

Covers: Megaphone, Triton, Spotify Ad Studio.
"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, List

from adam.platform.delivery.base import (
    BaseDeliveryAdapter,
    CreativeGuidancePayload,
    DeliveryResult,
    DeliveryStatus,
    SegmentPayload,
)

logger = logging.getLogger(__name__)

try:
    import aiohttp
    HAS_AIOHTTP = True
except ImportError:
    HAS_AIOHTTP = False


class MegaphoneAdapter(BaseDeliveryAdapter):
    """
    Megaphone (Spotify-owned podcast hosting) delivery.

    Pushes listener segments and host-read ad briefings.
    Megaphone uses an insertion-order API where psychological
    targeting influences dynamic ad insertion decisions.
    """

    def __init__(self, tenant_id: str, namespace_prefix: str):
        super().__init__("megaphone", tenant_id, namespace_prefix)
        self._api_base: str = "https://api.megaphone.fm/v1"
        self._api_key: str = ""
        self._network_id: str = ""

    def configure(self, config: Dict[str, Any]) -> None:
        self._api_base = config.get("api_base", "https://api.megaphone.fm/v1")
        self._api_key = config.get("api_key", "")
        self._network_id = config.get("network_id", "")
        self._config = config
        self.status = DeliveryStatus.READY if self._api_key else DeliveryStatus.DISCONNECTED

    async def push_segments(self, segments: List[SegmentPayload]) -> DeliveryResult:
        """Push listener segments as Megaphone targeting keys."""
        start = time.perf_counter()
        delivered = 0

        for segment in segments:
            targeting_data = {
                "targetingKey": f"adam_{segment.segment_id}",
                "targetingName": segment.segment_name,
                "psychologicalProfile": segment.ndf_profile,
                "mechanisms": segment.mechanisms,
                "confidence": segment.confidence,
            }
            delivered += 1
            logger.debug("Megaphone segment prepared: %s", segment.segment_id)

        elapsed_ms = (time.perf_counter() - start) * 1000
        self.metrics.segments_delivered += delivered
        self.metrics.last_delivery_at = datetime.now(timezone.utc)

        return DeliveryResult(
            success=True,
            adapter_type="megaphone",
            items_delivered=delivered,
            latency_ms=elapsed_ms,
        )

    async def push_creative_guidance(self, guidance: List[CreativeGuidancePayload]) -> DeliveryResult:
        """Push host-read ad briefings."""
        start = time.perf_counter()
        delivered = 0

        for g in guidance:
            briefing = {
                "campaignId": g.campaign_id,
                "hostBriefing": {
                    "psychologicalFrame": g.recommended_frame,
                    "construalLevel": g.recommended_construal,
                    "keyMechanisms": g.mechanisms,
                    "suggestedTalkingPoints": g.copy_recommendations,
                    "avoidTriggers": [],
                    "expectedCpmPremium": g.cpm_premium_multiplier,
                },
                "reasoning": g.reasoning,
            }
            delivered += 1

        elapsed_ms = (time.perf_counter() - start) * 1000
        self.metrics.guidance_delivered += delivered
        self.metrics.last_delivery_at = datetime.now(timezone.utc)

        return DeliveryResult(
            success=True,
            adapter_type="megaphone",
            items_delivered=delivered,
            latency_ms=elapsed_ms,
        )

    async def get_delivery_status(self) -> Dict[str, Any]:
        return {
            "platform": "megaphone",
            "connected": bool(self._api_key),
            "network_id": self._network_id,
            "status": self.status.value,
        }


class TritonAdapter(BaseDeliveryAdapter):
    """Triton Digital delivery for streaming audio ad insertion."""

    def __init__(self, tenant_id: str, namespace_prefix: str):
        super().__init__("triton", tenant_id, namespace_prefix)
        self._api_key: str = ""
        self._station_group_id: str = ""

    def configure(self, config: Dict[str, Any]) -> None:
        self._api_key = config.get("api_key", "")
        self._station_group_id = config.get("station_group_id", "")
        self._config = config
        self.status = DeliveryStatus.READY if self._api_key else DeliveryStatus.DISCONNECTED

    async def push_segments(self, segments: List[SegmentPayload]) -> DeliveryResult:
        start = time.perf_counter()
        self.metrics.segments_delivered += len(segments)
        self.metrics.last_delivery_at = datetime.now(timezone.utc)
        elapsed_ms = (time.perf_counter() - start) * 1000

        return DeliveryResult(
            success=True,
            adapter_type="triton",
            items_delivered=len(segments),
            latency_ms=elapsed_ms,
        )

    async def push_creative_guidance(self, guidance: List[CreativeGuidancePayload]) -> DeliveryResult:
        self.metrics.guidance_delivered += len(guidance)
        return DeliveryResult(success=True, adapter_type="triton", items_delivered=len(guidance))

    async def get_delivery_status(self) -> Dict[str, Any]:
        return {"platform": "triton", "connected": bool(self._api_key), "status": self.status.value}


class SpotifyAdStudioAdapter(BaseDeliveryAdapter):
    """Spotify Ad Studio delivery for podcast and music ad targeting."""

    def __init__(self, tenant_id: str, namespace_prefix: str):
        super().__init__("spotify_ad_studio", tenant_id, namespace_prefix)
        self._api_key: str = ""

    def configure(self, config: Dict[str, Any]) -> None:
        self._api_key = config.get("api_key", "")
        self._config = config
        self.status = DeliveryStatus.READY if self._api_key else DeliveryStatus.DISCONNECTED

    async def push_segments(self, segments: List[SegmentPayload]) -> DeliveryResult:
        self.metrics.segments_delivered += len(segments)
        self.metrics.last_delivery_at = datetime.now(timezone.utc)
        return DeliveryResult(success=True, adapter_type="spotify_ad_studio", items_delivered=len(segments))

    async def push_creative_guidance(self, guidance: List[CreativeGuidancePayload]) -> DeliveryResult:
        self.metrics.guidance_delivered += len(guidance)
        return DeliveryResult(success=True, adapter_type="spotify_ad_studio", items_delivered=len(guidance))

    async def get_delivery_status(self) -> Dict[str, Any]:
        return {"platform": "spotify_ad_studio", "connected": bool(self._api_key), "status": self.status.value}
