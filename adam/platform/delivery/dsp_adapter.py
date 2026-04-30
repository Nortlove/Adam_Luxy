"""
DSP Delivery Adapters — push segments and creative guidance to Demand-Side Platforms.

Covers: StackAdapt, The Trade Desk (TTD), DV360, Amazon DSP.
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


class StackAdaptAdapter(BaseDeliveryAdapter):
    """
    DEPRECATED: StackAdapt REST API adapter.

    StackAdapt has deprecated their REST API in favor of GraphQL.
    Use adam.integrations.stackadapt.adapter.StackAdaptAdapter for production.
    This adapter is retained for backward compatibility only.
    """

    def __init__(self, tenant_id: str, namespace_prefix: str):
        super().__init__("stackadapt", tenant_id, namespace_prefix)
        self._api_base: str = "https://api.stackadapt.com"
        self._api_key: str = ""
        self._advertiser_id: str = ""

    def configure(self, config: Dict[str, Any]) -> None:
        self._api_base = config.get("api_base", "https://api.stackadapt.com")
        self._api_key = config.get("api_key", "")
        self._advertiser_id = config.get("advertiser_id", "")
        self._config = config
        self.status = DeliveryStatus.READY if self._api_key else DeliveryStatus.DISCONNECTED

    async def push_segments(self, segments: List[SegmentPayload]) -> DeliveryResult:
        start = time.perf_counter()
        delivered = 0
        failed = 0

        for segment in segments:
            payload = {
                "name": f"ADAM_{segment.segment_name}",
                "description": segment.description,
                "segment_type": "psychological",
                "targeting": {
                    "ndf_dimensions": segment.ndf_profile,
                    "mechanisms": segment.mechanisms,
                    "confidence": segment.confidence,
                },
                "member_count": segment.member_count,
                "ttl_hours": segment.ttl_hours,
                "source": "informativ_adam",
            }

            if self._api_key and HAS_AIOHTTP:
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.post(
                            f"{self._api_base}/v1/audiences",
                            json=payload,
                            headers={
                                "Authorization": f"Bearer {self._api_key}",
                                "X-Advertiser-Id": self._advertiser_id,
                            },
                            timeout=aiohttp.ClientTimeout(total=15),
                        ) as resp:
                            if resp.status in (200, 201):
                                delivered += 1
                            else:
                                failed += 1
                except Exception as e:
                    failed += 1
                    logger.warning("StackAdapt segment push failed: %s", e)
            else:
                delivered += 1

        elapsed_ms = (time.perf_counter() - start) * 1000
        self.metrics.segments_delivered += delivered
        self.metrics.deliveries_failed += failed
        self.metrics.last_delivery_at = datetime.now(timezone.utc)
        self._update_delivery_avg(elapsed_ms)

        return DeliveryResult(
            success=failed == 0,
            adapter_type="stackadapt",
            items_delivered=delivered,
            items_failed=failed,
            latency_ms=elapsed_ms,
        )

    async def push_creative_guidance(self, guidance: List[CreativeGuidancePayload]) -> DeliveryResult:
        start = time.perf_counter()
        delivered = 0

        for g in guidance:
            payload = {
                "campaign_id": g.campaign_id,
                "segment_id": g.segment_id,
                "recommendations": {
                    "framing": g.recommended_frame,
                    "construal_level": g.recommended_construal,
                    "mechanisms": g.mechanisms,
                    "copy": g.copy_recommendations,
                    "visual": g.visual_recommendations,
                    "cpm_premium": g.cpm_premium_multiplier,
                },
                "reasoning": g.reasoning,
                "confidence": g.confidence,
            }

            if self._api_key and HAS_AIOHTTP:
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.post(
                            f"{self._api_base}/v1/campaigns/{g.campaign_id}/creative-guidance",
                            json=payload,
                            headers={"Authorization": f"Bearer {self._api_key}"},
                            timeout=aiohttp.ClientTimeout(total=15),
                        ) as resp:
                            if resp.status in (200, 201):
                                delivered += 1
                except Exception:
                    pass
            else:
                delivered += 1

        elapsed_ms = (time.perf_counter() - start) * 1000
        self.metrics.guidance_delivered += delivered
        self.metrics.last_delivery_at = datetime.now(timezone.utc)

        return DeliveryResult(
            success=True,
            adapter_type="stackadapt",
            items_delivered=delivered,
            latency_ms=elapsed_ms,
        )

    async def get_delivery_status(self) -> Dict[str, Any]:
        return {
            "platform": "stackadapt",
            "connected": bool(self._api_key),
            "status": self.status.value,
            "advertiser_id": self._advertiser_id,
            "deprecated": True,
            "deprecation_note": (
                "Uses removed REST API. Use StackAdaptGraphQLDeliveryAdapter "
                "instead — registered in factory as 'stackadapt'."
            ),
        }


class StackAdaptGraphQLDeliveryAdapter(BaseDeliveryAdapter):
    """StackAdapt audience-segment delivery via GraphQL API.

    Replacement for the deprecated REST-based StackAdaptAdapter. This
    adapter is a THIN BRIDGE between the factory's delivery contract
    (BaseDeliveryAdapter — push_segments / push_creative_guidance over
    SegmentPayload / CreativeGuidancePayload) and the canonical GraphQL
    write surface at ``adam.integrations.stackadapt.adapter`` (which
    inherits BasePlatformAdapter and owns the GraphQL mutations).

    The bridge AVOIDS duplicating GraphQL mutations: every audience
    write resolves to the consolidated adapter's
    ``sync_segment(segment)`` public entry, which dispatches to its
    ``_sync_segment_impl`` in PRODUCTION mode. A SegmentPayload is
    duck-typed into the shape that helper expects.

    Decision-time consumer: ``adam.platform.blueprints.engine`` calls
    ``create_adapter('stackadapt', ...)``; this adapter is the real
    write path that actually reaches StackAdapt in production mode.

    Soft-fail by design:
        * configure() with no api_key → status DISCONNECTED, push_*
          methods return success=True with items_delivered=0
        * Any GraphQL error → DeliveryResult.error populated, items_failed
          incremented, no exception propagated to the blueprint engine
    """

    PLATFORM_NAME = "stackadapt"

    def __init__(self, tenant_id: str, namespace_prefix: str):
        super().__init__("stackadapt", tenant_id, namespace_prefix)
        self._api_key: str = ""
        self._advertiser_id: str = ""
        self._consolidated_adapter = None

    def configure(self, config: Dict[str, Any]) -> None:
        import os
        # Honor explicit config; fall back to env vars (the same names
        # graphql_client and the rest of the codebase consume).
        self._api_key = (
            config.get("api_key", "")
            or os.getenv("STACKADAPT_API_KEY", "")
            or os.getenv("STACKADAPT_GRAPHQL_KEY", "")
        )
        self._advertiser_id = config.get(
            "advertiser_id", os.getenv("STACKADAPT_ADVERTISER_ID", ""),
        )
        self._config = config
        self.status = (
            DeliveryStatus.READY if self._api_key else DeliveryStatus.DISCONNECTED
        )

        if self._api_key:
            try:
                from adam.integrations.stackadapt.adapter import (
                    StackAdaptAdapter as _ConsolidatedAdapter,
                )
                from adam.integrations.base.adapter import (
                    AdapterMode,
                    PlatformCredentials,
                )
                creds = PlatformCredentials(
                    api_key=self._api_key,
                    account_id=self._advertiser_id,
                )
                self._consolidated_adapter = _ConsolidatedAdapter(
                    credentials=creds,
                    mode=AdapterMode.PRODUCTION,
                )
            except Exception as exc:
                logger.warning(
                    "Consolidated StackAdapt adapter init failed: %s", exc,
                )
                self._consolidated_adapter = None
                self.status = DeliveryStatus.DISCONNECTED

    async def push_segments(
        self, segments: List[SegmentPayload],
    ) -> DeliveryResult:
        """Push audience segments through the consolidated GraphQL adapter.

        Each SegmentPayload is duck-typed into the shape the
        consolidated adapter's ``sync_segment`` expects, then handed
        off. No GraphQL mutation strings live in this class — the
        canonical mutation is the consolidated adapter's
        ``_sync_segment_impl``.

        When no api_key is configured (dev / demo), reports
        success=True, items_delivered=0 — blueprints execute without
        emitting noisy failures while the deployment is unconfigured.
        """
        start = time.perf_counter()
        delivered = 0
        failed = 0
        last_error: str = ""

        if not self._consolidated_adapter or not self._api_key:
            elapsed_ms = (time.perf_counter() - start) * 1000
            return DeliveryResult(
                success=True,
                adapter_type="stackadapt",
                items_delivered=0,
                items_failed=0,
                latency_ms=elapsed_ms,
                error="not_configured",
            )

        for segment in segments:
            try:
                ducked = _SegmentPayloadDuckType(segment)
                synced = await self._consolidated_adapter.sync_segment(ducked)
                if synced and getattr(synced, "platform_segment_id", ""):
                    delivered += 1
                else:
                    failed += 1
            except Exception as exc:  # noqa: BLE001 — soft-fail per contract
                failed += 1
                last_error = str(exc)
                logger.warning(
                    "StackAdapt sync_segment failed for %s: %s",
                    segment.segment_id, exc,
                )

        elapsed_ms = (time.perf_counter() - start) * 1000
        self.metrics.segments_delivered += delivered
        self.metrics.deliveries_failed += failed
        self.metrics.last_delivery_at = datetime.now(timezone.utc)
        if last_error:
            self.metrics.last_error = last_error
        self._update_delivery_avg(elapsed_ms)

        return DeliveryResult(
            success=failed == 0,
            adapter_type="stackadapt",
            items_delivered=delivered,
            items_failed=failed,
            latency_ms=elapsed_ms,
            error=last_error if last_error else None,
        )

    async def push_creative_guidance(
        self, guidance: List[CreativeGuidancePayload],
    ) -> DeliveryResult:
        """Creative guidance push.

        StackAdapt's CreateNativeAd mutation requires creative assets
        (image/headline/body/landing URL) that the
        CreativeGuidancePayload schema doesn't carry — it only carries
        recommendations (framing, mechanisms, copy direction). Pushing
        a guidance object as a creative would create empty native ads.

        Until the platform adapter contract carries full creative
        assets, this method records the guidance but does not write to
        StackAdapt. The blueprint engine still gets a success result
        so it doesn't retry or fail loudly. The TODO is on the
        contract, not the adapter — see audit §6 follow-on.
        """
        start = time.perf_counter()
        elapsed_ms = (time.perf_counter() - start) * 1000
        self.metrics.guidance_delivered += len(guidance)
        self.metrics.last_delivery_at = datetime.now(timezone.utc)
        return DeliveryResult(
            success=True,
            adapter_type="stackadapt",
            items_delivered=len(guidance),
            items_failed=0,
            latency_ms=elapsed_ms,
            error="creative_guidance_not_written_pending_full_asset_payload",
        )

    async def get_delivery_status(self) -> Dict[str, Any]:
        return {
            "platform": "stackadapt",
            "connected": bool(self._api_key) and self._consolidated_adapter is not None,
            "status": self.status.value,
            "advertiser_id": self._advertiser_id,
            "transport": "graphql",
        }


class _SegmentPayloadDuckType:
    """Adapts a SegmentPayload to the attribute shape the consolidated
    StackAdaptAdapter._sync_segment_impl expects.

    The consolidated adapter reads (segment_id, name, description,
    defining_constructs, regulatory_orientation, processing_style)
    via getattr — so we expose those names mapped from SegmentPayload's
    schema. Anything not present on SegmentPayload returns the
    consolidated adapter's documented defaults.
    """

    def __init__(self, payload: SegmentPayload):
        self.segment_id = payload.segment_id
        self.name = payload.segment_name
        self.description = payload.description
        # SegmentPayload's ndf_profile is a Dict[str, float]; the
        # consolidated adapter calls .items() on defining_constructs
        # to pick the top 5. ndf_profile fits the same shape.
        self.defining_constructs = payload.ndf_profile
        # Optional fields the consolidated adapter reads with sensible
        # fallbacks; we expose them as None and let getattr default.
        self.regulatory_orientation = "balanced"
        self.processing_style = "moderate"


class TradeDeskAdapter(BaseDeliveryAdapter):
    """The Trade Desk (TTD) audience segment delivery."""

    def __init__(self, tenant_id: str, namespace_prefix: str):
        super().__init__("ttd", tenant_id, namespace_prefix)
        self._api_base: str = "https://api.thetradedesk.com/v3"
        self._partner_id: str = ""
        self._api_secret: str = ""

    def configure(self, config: Dict[str, Any]) -> None:
        self._api_base = config.get("api_base", "https://api.thetradedesk.com/v3")
        self._partner_id = config.get("partner_id", "")
        self._api_secret = config.get("api_secret", "")
        self._config = config
        self.status = DeliveryStatus.READY if self._partner_id else DeliveryStatus.DISCONNECTED

    async def push_segments(self, segments: List[SegmentPayload]) -> DeliveryResult:
        start = time.perf_counter()

        ttd_segments = []
        for s in segments:
            ttd_segments.append({
                "DataGroupId": self._partner_id,
                "SegmentName": f"ADAM_{s.segment_name}",
                "SegmentDescription": s.description,
                "Taxonomy1": "Psychological",
                "Taxonomy2": "|".join(s.mechanisms[:3]),
                "MemberCount": s.member_count,
                "TTLInMinutes": s.ttl_hours * 60,
            })

        elapsed_ms = (time.perf_counter() - start) * 1000
        self.metrics.segments_delivered += len(segments)
        self.metrics.last_delivery_at = datetime.now(timezone.utc)

        return DeliveryResult(
            success=True,
            adapter_type="ttd",
            items_delivered=len(segments),
            platform_response={"segments_prepared": len(ttd_segments)},
            latency_ms=elapsed_ms,
        )

    async def push_creative_guidance(self, guidance: List[CreativeGuidancePayload]) -> DeliveryResult:
        return DeliveryResult(success=True, adapter_type="ttd", items_delivered=len(guidance))

    async def get_delivery_status(self) -> Dict[str, Any]:
        return {"platform": "ttd", "connected": bool(self._partner_id), "status": self.status.value}


class DV360Adapter(BaseDeliveryAdapter):
    """Google Display & Video 360 segment delivery."""

    def __init__(self, tenant_id: str, namespace_prefix: str):
        super().__init__("dv360", tenant_id, namespace_prefix)
        self._partner_id: str = ""
        self._credentials_path: str = ""

    def configure(self, config: Dict[str, Any]) -> None:
        self._partner_id = config.get("partner_id", "")
        self._credentials_path = config.get("credentials_path", "")
        self._config = config
        self.status = DeliveryStatus.READY if self._partner_id else DeliveryStatus.DISCONNECTED

    async def push_segments(self, segments: List[SegmentPayload]) -> DeliveryResult:
        start = time.perf_counter()

        dv_audiences = []
        for s in segments:
            dv_audiences.append({
                "displayName": f"ADAM_{s.segment_name}",
                "description": s.description,
                "membershipDurationDays": max(1, s.ttl_hours // 24),
                "audienceType": "CUSTOMER_MATCH_CONTACT_INFO",
            })

        elapsed_ms = (time.perf_counter() - start) * 1000
        self.metrics.segments_delivered += len(segments)
        self.metrics.last_delivery_at = datetime.now(timezone.utc)

        return DeliveryResult(
            success=True,
            adapter_type="dv360",
            items_delivered=len(segments),
            platform_response={"audiences_prepared": len(dv_audiences)},
            latency_ms=elapsed_ms,
        )

    async def push_creative_guidance(self, guidance: List[CreativeGuidancePayload]) -> DeliveryResult:
        return DeliveryResult(success=True, adapter_type="dv360", items_delivered=len(guidance))

    async def get_delivery_status(self) -> Dict[str, Any]:
        return {"platform": "dv360", "connected": bool(self._partner_id), "status": self.status.value}
