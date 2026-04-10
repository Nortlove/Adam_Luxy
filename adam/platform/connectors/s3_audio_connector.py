"""
S3 Audio Connector — ingests audio content (podcasts, radio segments) from S3.

Used by: AUD-LST Blueprint.
Fetches audio metadata and optional transcripts from an S3 bucket,
then profiles the content via NDF.
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List

from adam.platform.connectors.base import BaseConnector, ContentItem, EnrichedContent

logger = logging.getLogger(__name__)

try:
    import aioboto3
    HAS_BOTO = True
except ImportError:
    HAS_BOTO = False


class S3AudioConnector(BaseConnector):
    """
    Polls an S3 bucket for new audio files + sidecar metadata JSON.

    Config:
        bucket_name: S3 bucket
        prefix: key prefix (e.g., "podcasts/")
        region: AWS region
        transcript_suffix: suffix for transcript files (default ".transcript.json")
        poll_interval_seconds: default 600
    """

    def __init__(self, tenant_id: str, namespace_prefix: str):
        super().__init__("s3_audio", tenant_id, namespace_prefix)
        self._bucket: str = ""
        self._prefix: str = ""
        self._region: str = "us-east-1"
        self._transcript_suffix: str = ".transcript.json"
        self._seen_keys: set = set()
        self._neo4j_driver = None
        self._redis_client = None

    def configure(self, config: Dict[str, Any]) -> None:
        self._bucket = config.get("bucket_name", "")
        self._prefix = config.get("prefix", "")
        self._region = config.get("region", "us-east-1")
        self._transcript_suffix = config.get("transcript_suffix", ".transcript.json")
        self._poll_interval_seconds = config.get("poll_interval_seconds", 600)
        self._neo4j_driver = config.get("neo4j_driver")
        self._redis_client = config.get("redis_client")
        self._config = config

    async def poll(self) -> List[ContentItem]:
        if not HAS_BOTO:
            logger.warning("aioboto3 not installed — S3 audio connector cannot poll")
            return []

        items: List[ContentItem] = []
        session = aioboto3.Session()
        async with session.client("s3", region_name=self._region) as s3:
            paginator = s3.get_paginator("list_objects_v2")
            async for page in paginator.paginate(Bucket=self._bucket, Prefix=self._prefix):
                for obj in page.get("Contents", []):
                    key = obj["Key"]
                    if key in self._seen_keys:
                        continue
                    if key.endswith(self._transcript_suffix):
                        continue
                    if not any(key.endswith(ext) for ext in (".mp3", ".m4a", ".wav", ".ogg", ".json")):
                        continue

                    self._seen_keys.add(key)

                    title = key.split("/")[-1].rsplit(".", 1)[0]
                    body = ""
                    transcript_key = key.rsplit(".", 1)[0] + self._transcript_suffix
                    try:
                        resp = await s3.get_object(Bucket=self._bucket, Key=transcript_key)
                        transcript_data = json.loads(await resp["Body"].read())
                        body = transcript_data.get("text", transcript_data.get("transcript", ""))
                    except Exception:
                        pass

                    source_id = hashlib.md5(key.encode()).hexdigest()[:16]
                    items.append(ContentItem(
                        source_id=source_id,
                        source_type="s3_audio",
                        url=f"s3://{self._bucket}/{key}",
                        title=title,
                        body=body,
                        published_at=obj.get("LastModified"),
                        metadata={"s3_key": key, "size_bytes": obj.get("Size", 0)},
                    ))

        return items

    async def store_enriched(self, enriched: EnrichedContent) -> None:
        if self._neo4j_driver:
            async with self._neo4j_driver.session() as session:
                await session.run(
                    """
                    MERGE (c:TenantContent {content_id: $content_id})
                    SET c.tenant_id = $tenant_id,
                        c.title = $title,
                        c.url = $url,
                        c.source_type = 's3_audio',
                        c.enrichment_confidence = $confidence,
                        c.profiled_at = datetime(),
                        c.approach_avoidance = $aa,
                        c.temporal_horizon = $th,
                        c.social_calibration = $sc,
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
                    ce=enriched.ndf_profile.get("cognitive_engagement", 0.5),
                    as_val=enriched.ndf_profile.get("arousal_seeking", 0.5),
                )

        if self._redis_client:
            cache_key = f"{self.namespace_prefix}:profile:{enriched.source_id}"
            await self._redis_client.set(
                cache_key,
                json.dumps(enriched.model_dump(mode="json"), default=str),
                ex=3600,
            )
