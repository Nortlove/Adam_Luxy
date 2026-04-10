"""
Webhook/CMS Connector — receives content via push (webhook POST).

Used by: PUB-ENR, PUB-YLD Blueprints.
Instead of polling, this connector exposes a FastAPI endpoint that the
publisher's CMS calls when new content is published.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List

from adam.platform.connectors.base import BaseConnector, ContentItem, EnrichedContent

logger = logging.getLogger(__name__)


class WebhookConnector(BaseConnector):
    """
    Push-based connector: receives content items via HTTP POST.

    Config:
        webhook_secret: HMAC-SHA256 secret for payload verification
        auto_process: whether to NDF-profile inline (default True)
    """

    def __init__(self, tenant_id: str, namespace_prefix: str):
        super().__init__("webhook", tenant_id, namespace_prefix)
        self._webhook_secret: str = ""
        self._auto_process: bool = True
        self._queue: List[ContentItem] = []
        self._neo4j_driver = None
        self._redis_client = None

    def configure(self, config: Dict[str, Any]) -> None:
        self._webhook_secret = config.get("webhook_secret", "")
        self._auto_process = config.get("auto_process", True)
        self._neo4j_driver = config.get("neo4j_driver")
        self._redis_client = config.get("redis_client")
        self._config = config

    async def poll(self) -> List[ContentItem]:
        """For webhook, poll drains the internal push queue."""
        items = list(self._queue)
        self._queue.clear()
        return items

    async def receive(self, payload: Dict[str, Any], signature: str = "") -> EnrichedContent:
        """
        Called by the webhook HTTP endpoint when the CMS pushes content.
        Returns the enriched content synchronously if auto_process is True.
        """
        if self._webhook_secret and signature:
            expected = hmac.new(
                self._webhook_secret.encode(),
                json.dumps(payload, sort_keys=True).encode(),
                hashlib.sha256,
            ).hexdigest()
            if not hmac.compare_digest(expected, signature):
                raise ValueError("Invalid webhook signature")

        item = ContentItem(
            source_id=payload.get("id", hashlib.md5(
                json.dumps(payload, sort_keys=True).encode()
            ).hexdigest()[:16]),
            source_type="webhook",
            url=payload.get("url", ""),
            title=payload.get("title", ""),
            body=payload.get("body", payload.get("content", "")),
            published_at=datetime.now(timezone.utc),
            metadata=payload.get("metadata", {}),
            raw_payload=payload,
        )

        if self._auto_process:
            transformed = await self.transform(item)
            enriched = await self.process(transformed)
            await self.store_enriched(enriched)
            self.metrics.items_polled += 1
            self.metrics.items_processed += 1
            return enriched
        else:
            self._queue.append(item)
            self.metrics.items_polled += 1
            return EnrichedContent(
                content_id=f"{self.tenant_id}:{item.source_id}",
                tenant_id=self.tenant_id,
                source_id=item.source_id,
                title=item.title,
                metadata={"queued": True},
            )

    async def store_enriched(self, enriched: EnrichedContent) -> None:
        if self._neo4j_driver:
            async with self._neo4j_driver.session() as session:
                await session.run(
                    """
                    MERGE (c:TenantContent {content_id: $content_id})
                    SET c.tenant_id = $tenant_id,
                        c.title = $title,
                        c.url = $url,
                        c.source_type = 'webhook',
                        c.enrichment_confidence = $confidence,
                        c.profiled_at = datetime()
                    WITH c
                    UNWIND keys($ndf) AS dim
                    SET c[dim] = $ndf[dim]
                    """,
                    content_id=enriched.content_id,
                    tenant_id=enriched.tenant_id,
                    title=enriched.title,
                    url=enriched.url or "",
                    confidence=enriched.enrichment_confidence,
                    ndf=enriched.ndf_profile,
                )

        if self._redis_client:
            cache_key = f"{self.namespace_prefix}:profile:{enriched.source_id}"
            await self._redis_client.set(
                cache_key,
                json.dumps(enriched.model_dump(mode="json"), default=str),
                ex=3600,
            )
