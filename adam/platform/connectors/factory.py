"""
Connector Factory — creates and configures connectors by type.

Each Blueprint specifies which connectors it needs; this factory
instantiates the right implementation.
"""

from __future__ import annotations

import logging
from typing import Dict, Type

from adam.platform.connectors.base import BaseConnector
from adam.platform.connectors.bidstream_connector import BidstreamConnector
from adam.platform.connectors.product_feed_connector import ProductFeedConnector
from adam.platform.connectors.rss_connector import RSSConnector
from adam.platform.connectors.s3_audio_connector import S3AudioConnector
from adam.platform.connectors.webhook_connector import WebhookConnector

logger = logging.getLogger(__name__)

CONNECTOR_REGISTRY: Dict[str, Type[BaseConnector]] = {
    "rss": RSSConnector,
    "sitemap": RSSConnector,  # Sitemap uses RSS connector with sitemap URL
    "cms_webhook": WebhookConnector,
    "webhook": WebhookConnector,
    "s3_audio": S3AudioConnector,
    "transcript_db": S3AudioConnector,  # Transcript DB connector uses S3 with transcript suffix
    "bidstream": BidstreamConnector,
    "audience_feed": BidstreamConnector,
    "exchange_feed": BidstreamConnector,
    "product_feed": ProductFeedConnector,
    "purchase_feed": ProductFeedConnector,
    "brand_feed": ProductFeedConnector,
    "creative_api": WebhookConnector,
    "asset_feed": WebhookConnector,
    "social_api": WebhookConnector,
    "content_api": WebhookConnector,
    "acr_feed": WebhookConnector,
    "real_time_content": WebhookConnector,
    "media_plan_feed": WebhookConnector,
}


def create_connector(
    connector_type: str,
    tenant_id: str,
    namespace_prefix: str,
    config: dict,
) -> BaseConnector:
    """Create and configure a connector instance."""
    cls = CONNECTOR_REGISTRY.get(connector_type)
    if cls is None:
        raise ValueError(f"Unknown connector type: {connector_type}. Available: {list(CONNECTOR_REGISTRY.keys())}")

    connector = cls(tenant_id=tenant_id, namespace_prefix=namespace_prefix)
    connector.configure(config)
    logger.info(
        "Created %s connector for tenant %s (class=%s)",
        connector_type, tenant_id, cls.__name__,
    )
    return connector


def list_available_connectors() -> Dict[str, str]:
    """Returns mapping of connector_type → class name."""
    return {k: v.__name__ for k, v in CONNECTOR_REGISTRY.items()}
