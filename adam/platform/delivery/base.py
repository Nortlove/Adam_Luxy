"""
Base Delivery Adapter — abstract interface all delivery adapters implement.

Mirrors BaseConnector pattern and ADAM's service conventions.
"""

from __future__ import annotations

import abc
import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class DeliveryStatus(str, Enum):
    READY = "ready"
    DELIVERING = "delivering"
    ERROR = "error"
    RATE_LIMITED = "rate_limited"
    DISCONNECTED = "disconnected"


class SegmentPayload(BaseModel):
    """Psychological segment data to push to delivery platform."""
    segment_id: str
    segment_name: str
    description: str = ""
    ndf_profile: Dict[str, float] = Field(default_factory=dict)
    member_count: int = 0
    mechanisms: List[str] = Field(default_factory=list)
    iab_taxonomy_ids: List[str] = Field(default_factory=list)
    confidence: float = 0.0
    tenant_id: str = ""
    ttl_hours: int = 24


class CreativeGuidancePayload(BaseModel):
    """Creative recommendation data to push to delivery platform."""
    campaign_id: str
    segment_id: str
    recommended_frame: str = "gain"
    recommended_construal: str = "concrete"
    mechanisms: List[Dict[str, Any]] = Field(default_factory=list)
    copy_recommendations: List[str] = Field(default_factory=list)
    visual_recommendations: List[str] = Field(default_factory=list)
    cpm_premium_multiplier: float = 1.0
    reasoning: str = ""
    confidence: float = 0.0


class DeliveryResult(BaseModel):
    """Result from a delivery attempt."""
    success: bool
    adapter_type: str
    items_delivered: int = 0
    items_failed: int = 0
    platform_response: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    latency_ms: float = 0.0
    delivered_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class DeliveryMetrics(BaseModel):
    segments_delivered: int = 0
    guidance_delivered: int = 0
    deliveries_failed: int = 0
    last_delivery_at: Optional[datetime] = None
    last_error: Optional[str] = None
    avg_delivery_ms: float = 0.0


class BaseDeliveryAdapter(abc.ABC):
    """
    Abstract delivery adapter interface.

    Subclasses implement platform-specific delivery logic:
      - configure(config) — validate credentials and connection
      - push_segments(segments) — bulk segment upload
      - push_creative_guidance(guidance) — creative recommendation delivery
      - get_delivery_status() — platform health check
    """

    def __init__(self, adapter_type: str, tenant_id: str, namespace_prefix: str):
        self.adapter_type = adapter_type
        self.tenant_id = tenant_id
        self.namespace_prefix = namespace_prefix
        self.status = DeliveryStatus.DISCONNECTED
        self.metrics = DeliveryMetrics()
        self._config: Dict[str, Any] = {}

    @abc.abstractmethod
    def configure(self, config: Dict[str, Any]) -> None:
        """Validate and store adapter-specific configuration (API keys, endpoints)."""
        ...

    @abc.abstractmethod
    async def push_segments(self, segments: List[SegmentPayload]) -> DeliveryResult:
        """Push enriched segments to the delivery platform."""
        ...

    @abc.abstractmethod
    async def push_creative_guidance(self, guidance: List[CreativeGuidancePayload]) -> DeliveryResult:
        """Push creative recommendations to the delivery platform."""
        ...

    @abc.abstractmethod
    async def get_delivery_status(self) -> Dict[str, Any]:
        """Check connectivity and health of the delivery platform."""
        ...

    async def deliver(self, segments: List[SegmentPayload], guidance: Optional[List[CreativeGuidancePayload]] = None) -> DeliveryResult:
        """Combined delivery: segments + optional creative guidance."""
        seg_result = await self.push_segments(segments)

        if guidance:
            guide_result = await self.push_creative_guidance(guidance)
            seg_result.items_delivered += guide_result.items_delivered
            seg_result.items_failed += guide_result.items_failed

        return seg_result

    def get_health(self) -> Dict[str, Any]:
        return {
            "adapter_type": self.adapter_type,
            "tenant_id": self.tenant_id,
            "status": self.status.value,
            "metrics": self.metrics.model_dump(),
        }

    def _update_delivery_avg(self, elapsed_ms: float) -> None:
        n = self.metrics.segments_delivered + self.metrics.guidance_delivered + 1
        self.metrics.avg_delivery_ms = (
            self.metrics.avg_delivery_ms * (n - 1) + elapsed_ms
        ) / n
