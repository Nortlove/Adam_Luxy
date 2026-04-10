"""
StackAdapt Data Taxonomy API Client
=====================================

Verified against docs.stackadapt.com/data-partner (March 2026).

Endpoint: https://api.stackadapt.com/data-partner/graphql
Auth:     Bearer token in Authorization header
Rate:     10 requests per second

Mutations:
    createAudienceMetadata — register new segment
    updateAudienceMetadata — update existing segment

Data transfer: actual audience membership data goes via direct S3 integration.
This client handles the metadata/taxonomy layer only.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_ENDPOINT = "https://api.stackadapt.com/data-partner/graphql"
_PROVIDER_SOURCE = "INFORMATIV"


@dataclass
class AudienceMetadata:
    """Metadata for a single audience segment in StackAdapt's catalogue."""

    segment_id: str
    name: str
    internal_price: float
    description: str = ""
    account_ids: Optional[List[int]] = None


@dataclass
class TaxonomyPushResult:
    """Result of pushing a batch of segments to StackAdapt."""

    total: int = 0
    created: int = 0
    updated: int = 0
    failed: int = 0
    errors: List[Dict[str, Any]] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []


class DataTaxonomyClient:
    """
    Client for StackAdapt's Data Taxonomy API.

    Usage:
        client = DataTaxonomyClient(api_key="your_bearer_token")
        result = await client.push_taxonomy(segments)
    """

    def __init__(
        self,
        api_key: str = "",
        endpoint: str = _ENDPOINT,
        provider_source: str = _PROVIDER_SOURCE,
        dry_run: bool = False,
    ):
        self._api_key = api_key
        self._endpoint = endpoint
        self._provider_source = provider_source
        self._dry_run = dry_run
        self._rate_limit_delay = 0.11  # 10 req/s => 100ms between requests + buffer

    async def create_audience(self, meta: AudienceMetadata) -> Dict[str, Any]:
        """Create a new audience segment in StackAdapt."""
        mutation = """
        mutation {
            createAudienceMetadata(input: {
                segmentId: "%s",
                name: "%s",
                providerSource: "%s",
                internalPrice: %.2f,
                description: "%s"%s
            }) {
                success
                userErrors {
                    message
                    path
                }
            }
        }
        """ % (
            meta.segment_id,
            meta.name.replace('"', '\\"'),
            self._provider_source,
            meta.internal_price,
            meta.description.replace('"', '\\"')[:500],
            f', accountIds: {meta.account_ids}' if meta.account_ids else "",
        )

        return await self._execute(mutation)

    async def update_audience(self, meta: AudienceMetadata) -> Dict[str, Any]:
        """Update an existing audience segment in StackAdapt."""
        parts = [f'segmentId: "{meta.segment_id}"']
        if meta.name:
            parts.append(f'name: "{meta.name.replace(chr(34), chr(92) + chr(34))}"')
        if meta.internal_price > 0:
            parts.append(f'internalPrice: {meta.internal_price:.2f}')
        if meta.description:
            parts.append(f'description: "{meta.description.replace(chr(34), chr(92) + chr(34))[:500]}"')
        if meta.account_ids:
            parts.append(f'appendAccountIds: {meta.account_ids}')

        mutation = """
        mutation {
            updateAudienceMetadata(input: {
                %s
            }) {
                success
                userErrors {
                    message
                    path
                }
            }
        }
        """ % ",\n                ".join(parts)

        return await self._execute(mutation)

    async def push_taxonomy(
        self,
        segments: List[AudienceMetadata],
        update_existing: bool = True,
    ) -> TaxonomyPushResult:
        """
        Push a full taxonomy of segments to StackAdapt.

        Tries createAudienceMetadata first; if segment exists and
        update_existing=True, falls back to updateAudienceMetadata.
        """
        result = TaxonomyPushResult(total=len(segments))

        for i, seg in enumerate(segments):
            if i > 0:
                import asyncio
                await asyncio.sleep(self._rate_limit_delay)

            try:
                resp = await self.create_audience(seg)
                data = resp.get("data", {}).get("createAudienceMetadata", {})

                if data.get("success"):
                    result.created += 1
                else:
                    errors = data.get("userErrors", [])
                    already_exists = any("already exists" in (e.get("message", "") or "") for e in errors)
                    if already_exists and update_existing:
                        update_resp = await self.update_audience(seg)
                        update_data = update_resp.get("data", {}).get("updateAudienceMetadata", {})
                        if update_data.get("success"):
                            result.updated += 1
                        else:
                            result.failed += 1
                            result.errors.append({
                                "segment_id": seg.segment_id,
                                "operation": "update",
                                "errors": update_data.get("userErrors", []),
                            })
                    else:
                        result.failed += 1
                        result.errors.append({
                            "segment_id": seg.segment_id,
                            "operation": "create",
                            "errors": errors,
                        })
            except Exception as e:
                result.failed += 1
                result.errors.append({
                    "segment_id": seg.segment_id,
                    "operation": "create",
                    "error": str(e),
                })

            if (i + 1) % 50 == 0:
                logger.info(
                    "Taxonomy push progress: %d/%d (created=%d, updated=%d, failed=%d)",
                    i + 1, len(segments), result.created, result.updated, result.failed,
                )

        logger.info(
            "Taxonomy push complete: %d total, %d created, %d updated, %d failed",
            result.total, result.created, result.updated, result.failed,
        )
        return result

    async def _execute(self, query: str) -> Dict[str, Any]:
        """Execute a GraphQL query against the Data Taxonomy API."""
        if self._dry_run:
            logger.info("[DRY RUN] Would execute: %s", query[:200])
            return {"data": {"createAudienceMetadata": {"success": True, "userErrors": []}}}

        if not self._api_key:
            raise ValueError(
                "StackAdapt Data Taxonomy API key not configured. "
                "Contact StackAdapt to obtain a bearer token."
            )

        try:
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self._endpoint,
                    json={"query": query},
                    headers={
                        "Authorization": f"Bearer {self._api_key}",
                        "Content-Type": "application/json",
                    },
                    timeout=30.0,
                )
                response.raise_for_status()
                return response.json()
        except ImportError:
            logger.error("httpx required for StackAdapt API. Install: pip install httpx")
            raise
        except Exception as e:
            logger.error("StackAdapt Data Taxonomy API error: %s", e)
            raise


class S3AudienceSync:
    """
    Manages audience membership data transfer to StackAdapt via S3.

    StackAdapt uses direct S3 integration for actual audience data
    (hashed emails, device IDs, etc.). The Data Taxonomy API handles
    metadata only; this class handles the data payload.
    """

    def __init__(
        self,
        bucket_name: str = "",
        prefix: str = "informativ/audiences/",
        aws_region: str = "us-east-1",
    ):
        self._bucket = bucket_name
        self._prefix = prefix
        self._region = aws_region

    async def sync_segment_data(
        self,
        segment_id: str,
        member_identifiers: List[str],
        identifier_type: str = "hashed_email",
    ) -> Dict[str, Any]:
        """
        Upload segment membership data to the shared S3 bucket.

        Args:
            segment_id: INFORMATIV segment ID
            member_identifiers: List of hashed identifiers
            identifier_type: "hashed_email", "device_id", "maid"
        """
        if not self._bucket:
            logger.warning("S3 bucket not configured for audience sync")
            return {"status": "skipped", "reason": "no_bucket_configured"}

        import json
        from datetime import datetime, timezone

        key = f"{self._prefix}{segment_id}/{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.jsonl"

        lines = []
        for identifier in member_identifiers:
            lines.append(json.dumps({
                "segment_id": segment_id,
                "identifier": identifier,
                "identifier_type": identifier_type,
                "provider": "INFORMATIV",
            }))
        payload = "\n".join(lines)

        try:
            import boto3
            s3 = boto3.client("s3", region_name=self._region)
            s3.put_object(
                Bucket=self._bucket,
                Key=key,
                Body=payload.encode("utf-8"),
                ContentType="application/jsonl",
            )
            return {
                "status": "uploaded",
                "bucket": self._bucket,
                "key": key,
                "members": len(member_identifiers),
            }
        except ImportError:
            logger.error("boto3 required for S3 sync. Install: pip install boto3")
            return {"status": "error", "reason": "boto3_not_installed"}
        except Exception as e:
            logger.error("S3 upload failed: %s", e)
            return {"status": "error", "reason": str(e)}
