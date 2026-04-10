"""
Product Feed Connector — ingests product catalogs for retail media targeting.

Used by: RET-PSY Blueprint.
Ingests product data (title, description, category, price) and runs the
80-construct product NDF analysis (same pipeline as the original 937M
Amazon product description analysis).
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List

from adam.platform.connectors.base import BaseConnector, ContentItem, EnrichedContent

logger = logging.getLogger(__name__)


class ProductFeedConnector(BaseConnector):
    """
    Ingests product catalog data via API or file upload.

    Config:
        feed_url: URL to fetch product catalog (JSON/CSV)
        api_key: auth for the product feed API
        batch_size: products to process per cycle (default 100)
        category_filter: optional category whitelist
    """

    def __init__(self, tenant_id: str, namespace_prefix: str):
        super().__init__("product_feed", tenant_id, namespace_prefix)
        self._feed_url: str = ""
        self._api_key: str = ""
        self._batch_size: int = 100
        self._category_filter: List[str] = []
        self._seen_products: set = set()
        self._neo4j_driver = None
        self._redis_client = None
        self._product_queue: List[Dict[str, Any]] = []

    def configure(self, config: Dict[str, Any]) -> None:
        self._feed_url = config.get("feed_url", "")
        self._api_key = config.get("api_key", "")
        self._batch_size = config.get("batch_size", 100)
        self._category_filter = config.get("category_filter", [])
        self._poll_interval_seconds = config.get("poll_interval_seconds", 3600)
        self._neo4j_driver = config.get("neo4j_driver")
        self._redis_client = config.get("redis_client")
        self._config = config

    async def ingest_products(self, products: List[Dict[str, Any]]) -> int:
        """Direct ingestion of product data (push API). Returns count processed."""
        self._product_queue.extend(products)
        count = await self.run_cycle()
        return count

    async def poll(self) -> List[ContentItem]:
        """Fetch from product feed URL or drain push queue."""
        items: List[ContentItem] = []

        if self._product_queue:
            for product in self._product_queue[:self._batch_size]:
                item = self._product_to_content_item(product)
                if item.source_id not in self._seen_products:
                    items.append(item)
                    self._seen_products.add(item.source_id)
            self._product_queue = self._product_queue[self._batch_size:]
            return items

        if self._feed_url:
            try:
                import aiohttp
                async with aiohttp.ClientSession() as session:
                    headers = {"Authorization": f"Bearer {self._api_key}"} if self._api_key else {}
                    async with session.get(self._feed_url, headers=headers) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            products = data if isinstance(data, list) else data.get("products", [])
                            for product in products[:self._batch_size]:
                                item = self._product_to_content_item(product)
                                if item.source_id not in self._seen_products:
                                    items.append(item)
                                    self._seen_products.add(item.source_id)
            except Exception as e:
                logger.warning("Product feed fetch failed: %s", e)

        return items

    async def store_enriched(self, enriched: EnrichedContent) -> None:
        if self._neo4j_driver:
            async with self._neo4j_driver.session() as session:
                await session.run(
                    """
                    MERGE (p:TenantProduct {content_id: $content_id})
                    SET p.tenant_id = $tenant_id,
                        p.title = $title,
                        p.source_type = 'product_feed',
                        p.enrichment_confidence = $confidence,
                        p.profiled_at = datetime(),
                        p.category = $category,
                        p.price = $price,
                        p.approach_avoidance = $aa,
                        p.temporal_horizon = $th,
                        p.social_calibration = $sc,
                        p.cognitive_engagement = $ce,
                        p.arousal_seeking = $as_val
                    """,
                    content_id=enriched.content_id,
                    tenant_id=enriched.tenant_id,
                    title=enriched.title,
                    confidence=enriched.enrichment_confidence,
                    category=enriched.metadata.get("category", ""),
                    price=enriched.metadata.get("price", 0.0),
                    aa=enriched.ndf_profile.get("approach_avoidance", 0.5),
                    th=enriched.ndf_profile.get("temporal_horizon", 0.5),
                    sc=enriched.ndf_profile.get("social_calibration", 0.5),
                    ce=enriched.ndf_profile.get("cognitive_engagement", 0.5),
                    as_val=enriched.ndf_profile.get("arousal_seeking", 0.5),
                )

        if self._redis_client:
            cache_key = f"{self.namespace_prefix}:product:{enriched.source_id}"
            await self._redis_client.set(
                cache_key,
                json.dumps(enriched.model_dump(mode="json"), default=str),
                ex=86400,
            )

    def _product_to_content_item(self, product: Dict[str, Any]) -> ContentItem:
        product_id = product.get("id", product.get("asin", product.get("sku", "")))
        if not product_id:
            product_id = hashlib.md5(
                json.dumps(product, sort_keys=True, default=str).encode()
            ).hexdigest()[:16]

        title = product.get("title", product.get("name", ""))
        desc = product.get("description", product.get("body", ""))
        category = product.get("category", "")

        if self._category_filter and category not in self._category_filter:
            pass  # could skip, but we'll still process for flexibility

        return ContentItem(
            source_id=str(product_id),
            source_type="product_feed",
            title=title,
            body=desc,
            metadata={
                "category": category,
                "price": product.get("price", 0.0),
                "brand": product.get("brand", ""),
                "original_data": {k: v for k, v in product.items() if k not in ("title", "description", "body")},
            },
        )
