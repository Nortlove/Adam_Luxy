"""
Bidstream Connector — ingests real-time bid requests from DSP/SSP partners.

ARCHITECTURE NOTE (March 2026):
    For StackAdapt integration, INFORMATIV operates as a data partner, not a
    bidstream processor. StackAdapt handles RTB internally. Our integration
    uses the Data Taxonomy API (Layer 1), Creative Intelligence API (Layer 2),
    and Pixel API webhook (Layer 3). See adam.integrations.stackadapt.

    This connector remains for potential future SSP/exchange integrations where
    INFORMATIV would process bid requests directly.

Used by: DSP-TGT, EXC-DAT Blueprints.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, List

from adam.platform.connectors.base import BaseConnector, ContentItem, EnrichedContent

logger = logging.getLogger(__name__)


class BidstreamConnector(BaseConnector):
    """
    Real-time bidstream enrichment connector.

    Unlike polling connectors, this processes individual bid requests
    synchronously with strict latency budgets (< 100ms fast, < 200ms full).

    Config:
        max_latency_ms: enrichment latency budget (default 100)
        mode: "fast" or "full" (default "fast")
        enrich_user_agent: parse UA for device/browser signals (default True)
        enrich_geo: resolve IP to geo signals (default True)
    """

    def __init__(self, tenant_id: str, namespace_prefix: str):
        super().__init__("bidstream", tenant_id, namespace_prefix)
        self._max_latency_ms: int = 100
        self._mode: str = "fast"
        self._dsp_pipeline = None  # Injected DSPEnrichmentPipeline
        self._neo4j_driver = None
        self._redis_client = None

    def configure(self, config: Dict[str, Any]) -> None:
        self._max_latency_ms = config.get("max_latency_ms", 100)
        self._mode = config.get("mode", "fast")
        self._neo4j_driver = config.get("neo4j_driver")
        self._redis_client = config.get("redis_client")
        self._config = config

    def set_dsp_pipeline(self, pipeline) -> None:
        """Inject the DSPEnrichmentPipeline from the Blueprint."""
        self._dsp_pipeline = pipeline

    async def poll(self) -> List[ContentItem]:
        """Bidstream is push-based — poll returns empty."""
        return []

    async def enrich_bid_request(self, bid_request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a single bid request through the ADAM DSP pipeline.
        This is the hot path — must complete within _max_latency_ms.
        """
        start = time.perf_counter()

        request_id = bid_request.get("id", hashlib.md5(
            json.dumps(bid_request, sort_keys=True, default=str).encode()
        ).hexdigest()[:16])

        result: Dict[str, Any] = {
            "request_id": request_id,
            "tenant_id": self.tenant_id,
            "enriched_at": datetime.now(timezone.utc).isoformat(),
        }

        if self._dsp_pipeline:
            try:
                from adam.dsp.models import ImpressionContext, DeviceType

                raw_dt = str(bid_request.get("device", {}).get("devicetype", ""))
                dt_map = {"1": DeviceType.MOBILE, "2": DeviceType.DESKTOP,
                          "3": DeviceType.CONNECTED_TV, "4": DeviceType.TABLET,
                          "5": DeviceType.WEARABLE}
                device = dt_map.get(raw_dt, DeviceType.DESKTOP)

                now = datetime.now(timezone.utc)
                ctx = ImpressionContext(
                    timestamp=now.timestamp(),
                    day_of_week=now.weekday(),
                    local_hour=now.hour,
                    page_url=bid_request.get("site", {}).get("page", ""),
                    device_type=device,
                )

                enrichment = self._dsp_pipeline.enrich_impression(
                    ctx=ctx,
                    ad_category=bid_request.get("imp", [{}])[0].get("tagid", ""),
                    mode=self._mode,
                )
                result["enrichment"] = enrichment
                result["mode"] = self._mode
            except Exception as e:
                logger.warning("DSP enrichment failed for %s: %s", request_id, e)
                result["error"] = str(e)
                result["fallback"] = True
        else:
            item = ContentItem(
                source_id=request_id,
                source_type="bidstream",
                url=bid_request.get("site", {}).get("page", ""),
                title=bid_request.get("site", {}).get("name", ""),
                body="",
            )
            enriched = await self.process(item)
            result["ndf_profile"] = enriched.ndf_profile
            result["segments"] = enriched.segments
            result["fallback"] = True

        elapsed_ms = (time.perf_counter() - start) * 1000
        result["latency_ms"] = round(elapsed_ms, 2)
        self.metrics.items_processed += 1
        self._update_processing_avg(elapsed_ms)

        if elapsed_ms > self._max_latency_ms:
            logger.warning(
                "[%s] Bid enrichment exceeded budget: %.1fms > %dms",
                self.tenant_id, elapsed_ms, self._max_latency_ms,
            )

        return result

    async def store_enriched(self, enriched: EnrichedContent) -> None:
        """Bidstream enrichment is ephemeral — no persistent storage by default."""
        pass
