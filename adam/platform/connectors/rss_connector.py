"""
RSS/Atom Feed Connector — ingests publisher content from RSS/Atom feeds.

Used by: PUB-ENR, AUD-LST, PUB-YLD Blueprints.
"""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from xml.etree import ElementTree

from adam.platform.connectors.base import BaseConnector, ContentItem, EnrichedContent

logger = logging.getLogger(__name__)

try:
    import aiohttp
    HAS_AIOHTTP = True
except ImportError:
    HAS_AIOHTTP = False


class RSSConnector(BaseConnector):
    """
    Polls RSS/Atom feeds for new content items.

    Config:
        feed_urls: list of RSS/Atom feed URLs
        poll_interval_seconds: how often to check (default 300)
        max_items_per_poll: cap per feed (default 50)
    """

    def __init__(self, tenant_id: str, namespace_prefix: str):
        super().__init__("rss", tenant_id, namespace_prefix)
        self._feed_urls: List[str] = []
        self._seen_ids: set = set()
        self._max_items_per_poll: int = 50
        self._neo4j_driver = None
        self._redis_client = None

    def configure(self, config: Dict[str, Any]) -> None:
        self._feed_urls = config.get("feed_urls", [])
        self._poll_interval_seconds = config.get("poll_interval_seconds", 300)
        self._max_items_per_poll = config.get("max_items_per_poll", 50)
        self._neo4j_driver = config.get("neo4j_driver")
        self._redis_client = config.get("redis_client")
        self._config = config

    async def poll(self) -> List[ContentItem]:
        if not HAS_AIOHTTP:
            logger.warning("aiohttp not installed — RSS connector cannot poll")
            return []

        items: List[ContentItem] = []
        async with aiohttp.ClientSession() as session:
            for url in self._feed_urls:
                try:
                    feed_items = await self._fetch_feed(session, url)
                    items.extend(feed_items)
                except Exception as e:
                    logger.warning("Failed to fetch feed %s: %s", url, e)

        new_items = [i for i in items if i.source_id not in self._seen_ids]
        for i in new_items:
            self._seen_ids.add(i.source_id)

        return new_items[:self._max_items_per_poll]

    async def store_enriched(self, enriched: EnrichedContent) -> None:
        if self._neo4j_driver:
            async with self._neo4j_driver.session() as session:
                await session.run(
                    """
                    MERGE (c:TenantContent {content_id: $content_id})
                    SET c.tenant_id = $tenant_id,
                        c.title = $title,
                        c.url = $url,
                        c.source_type = 'rss',
                        c.enrichment_confidence = $confidence,
                        c.profiled_at = datetime(),
                        c.approach_avoidance = $aa,
                        c.temporal_horizon = $th,
                        c.social_calibration = $sc,
                        c.uncertainty_tolerance = $ut,
                        c.status_sensitivity = $ss,
                        c.cognitive_engagement = $ce,
                        c.arousal_seeking = $as_val
                    """,
                    content_id=enriched.content_id,
                    tenant_id=enriched.tenant_id,
                    title=enriched.title,
                    url=enriched.url or "",
                    confidence=enriched.enrichment_confidence,
                    aa=enriched.ndf_profile.get("approach_avoidance", 0.5),
                    th=enriched.ndf_profile.get("temporal_horizon", 0.5),
                    sc=enriched.ndf_profile.get("social_calibration", 0.5),
                    ut=enriched.ndf_profile.get("uncertainty_tolerance", 0.5),
                    ss=enriched.ndf_profile.get("status_sensitivity", 0.5),
                    ce=enriched.ndf_profile.get("cognitive_engagement", 0.5),
                    as_val=enriched.ndf_profile.get("arousal_seeking", 0.5),
                )

        if self._redis_client:
            import json
            cache_key = f"{self.namespace_prefix}:profile:{enriched.source_id}"
            await self._redis_client.set(
                cache_key,
                json.dumps(enriched.model_dump(mode="json"), default=str),
                ex=3600,
            )

    async def _fetch_feed(self, session, url: str) -> List[ContentItem]:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
            if resp.status != 200:
                return []
            text = await resp.text()

        root = ElementTree.fromstring(text)
        items = []

        # RSS 2.0
        for item_el in root.iter("item"):
            title = self._text(item_el, "title")
            link = self._text(item_el, "link")
            desc = self._text(item_el, "description")
            pub_date = self._text(item_el, "pubDate")
            guid = self._text(item_el, "guid") or link or title

            source_id = hashlib.md5(guid.encode()).hexdigest()[:16]
            items.append(ContentItem(
                source_id=source_id,
                source_type="rss",
                url=link,
                title=title,
                body=desc,
                published_at=self._parse_date(pub_date),
                metadata={"feed_url": url, "guid": guid},
            ))

        # Atom
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        for entry in root.findall("atom:entry", ns):
            title = self._text(entry, "atom:title", ns)
            link_el = entry.find("atom:link", ns)
            link = link_el.get("href", "") if link_el is not None else ""
            content_el = entry.find("atom:content", ns) or entry.find("atom:summary", ns)
            body = content_el.text if content_el is not None and content_el.text else ""
            entry_id = self._text(entry, "atom:id", ns) or link or title

            source_id = hashlib.md5(entry_id.encode()).hexdigest()[:16]
            items.append(ContentItem(
                source_id=source_id,
                source_type="atom",
                url=link,
                title=title,
                body=body,
                metadata={"feed_url": url, "entry_id": entry_id},
            ))

        return items

    @staticmethod
    def _text(el, tag: str, ns: Optional[Dict] = None) -> str:
        child = el.find(tag, ns) if ns else el.find(tag)
        return child.text.strip() if child is not None and child.text else ""

    @staticmethod
    def _parse_date(date_str: str) -> Optional[datetime]:
        if not date_str:
            return None
        try:
            from email.utils import parsedate_to_datetime
            return parsedate_to_datetime(date_str)
        except Exception:
            return None
