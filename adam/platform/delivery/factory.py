"""
Delivery Adapter Factory — creates and configures adapters by platform type.

NOTE: For StackAdapt production integration, use the consolidated adapter at
adam.integrations.stackadapt.adapter.StackAdaptAdapter (GraphQL) and the
Data Taxonomy client at adam.integrations.stackadapt.data_taxonomy_client.
The StackAdaptAdapter in dsp_adapter.py is retained for blueprint backward compat.
"""

from __future__ import annotations

import logging
from typing import Dict, Type

from adam.platform.delivery.base import BaseDeliveryAdapter
from adam.platform.delivery.audio_adapter import (
    MegaphoneAdapter,
    SpotifyAdStudioAdapter,
    TritonAdapter,
)
from adam.platform.delivery.dsp_adapter import (
    DV360Adapter,
    StackAdaptAdapter,
    TradeDeskAdapter,
)
from adam.platform.delivery.ssp_adapter import MagniteAdapter, PrebidAdapter

logger = logging.getLogger(__name__)


ADAPTER_REGISTRY: Dict[str, Type[BaseDeliveryAdapter]] = {
    # SSP
    "magnite": MagniteAdapter,
    "pubmatic": MagniteAdapter,     # PubMatic follows same pattern
    "openx": MagniteAdapter,
    "index_exchange": MagniteAdapter,
    "prebid": PrebidAdapter,

    # DSP
    "stackadapt": StackAdaptAdapter,
    "ttd": TradeDeskAdapter,
    "dv360": DV360Adapter,
    "amazon_dsp": DV360Adapter,     # Amazon DSP follows similar pattern

    # Audio
    "megaphone": MegaphoneAdapter,
    "triton": TritonAdapter,
    "spotify_ad_studio": SpotifyAdStudioAdapter,

    # CTV
    "freewheel": MagniteAdapter,    # FreeWheel follows SSP pattern
    "springserve": MagniteAdapter,

    # Retail
    "retail_media_api": StackAdaptAdapter,

    # Social
    "meta_api": DV360Adapter,
    "tiktok_api": DV360Adapter,
    "snap_api": DV360Adapter,

    # Analytics
    "analytics_dashboard": PrebidAdapter,
    "planning_api": PrebidAdapter,
    "seat_api": PrebidAdapter,
}


def create_adapter(
    adapter_type: str,
    tenant_id: str,
    namespace_prefix: str,
    config: dict,
) -> BaseDeliveryAdapter:
    """Create and configure a delivery adapter instance."""
    cls = ADAPTER_REGISTRY.get(adapter_type)
    if cls is None:
        raise ValueError(
            f"Unknown adapter type: {adapter_type}. Available: {list(ADAPTER_REGISTRY.keys())}"
        )

    adapter = cls(tenant_id=tenant_id, namespace_prefix=namespace_prefix)
    adapter.configure(config)
    logger.info(
        "Created %s delivery adapter for tenant %s (class=%s)",
        adapter_type, tenant_id, cls.__name__,
    )
    return adapter


def list_available_adapters() -> Dict[str, str]:
    return {k: v.__name__ for k, v in ADAPTER_REGISTRY.items()}
