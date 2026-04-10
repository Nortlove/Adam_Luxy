"""
ADAM Delivery Adapter Library

Pluggable modules that push enriched segments and creative guidance
to downstream SSP/DSP platforms.

Each adapter implements the BaseDeliveryAdapter interface:
  - configure(config) → validate credentials
  - push_segments(segments) → deliver to platform
  - push_creative_guidance(guidance) → deliver creative recommendations
  - get_status() → delivery health
"""

from adam.platform.delivery.base import (
    BaseDeliveryAdapter,
    DeliveryResult,
    DeliveryStatus,
    SegmentPayload,
    CreativeGuidancePayload,
)

__all__ = [
    "BaseDeliveryAdapter",
    "DeliveryResult",
    "DeliveryStatus",
    "SegmentPayload",
    "CreativeGuidancePayload",
]
