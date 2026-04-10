"""
Base Connector — abstract interface all content connectors implement.

Mirrors the BaseAtom pattern from adam/atoms/core/base.py (abstract with
lifecycle methods) and uses Pydantic models matching adam's conventions.
"""

from __future__ import annotations

import abc
import asyncio
import logging
import time
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ConnectorStatus(str, Enum):
    IDLE = "idle"
    POLLING = "polling"
    PROCESSING = "processing"
    ERROR = "error"
    STOPPED = "stopped"


class ContentItem(BaseModel):
    """Raw content item retrieved from a source before NDF enrichment."""
    source_id: str
    source_type: str
    url: Optional[str] = None
    title: str = ""
    body: str = ""
    published_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    raw_payload: Optional[Dict[str, Any]] = None


class EnrichedContent(BaseModel):
    """Content item after NDF profiling and segment generation."""
    content_id: str
    tenant_id: str
    source_id: str
    title: str = ""
    url: Optional[str] = None
    ndf_profile: Dict[str, float] = Field(default_factory=dict)
    segments: List[str] = Field(default_factory=list)
    psychological_constructs: Dict[str, float] = Field(default_factory=dict)
    mechanisms_relevant: List[str] = Field(default_factory=list)
    enrichment_confidence: float = 0.0
    profiled_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ConnectorMetrics(BaseModel):
    items_polled: int = 0
    items_processed: int = 0
    items_failed: int = 0
    last_poll_at: Optional[datetime] = None
    last_error: Optional[str] = None
    avg_processing_ms: float = 0.0


class BaseConnector(abc.ABC):
    """
    Abstract connector interface.

    Subclasses implement:
      - configure(config) — validate and store connection parameters
      - poll() — fetch new content items from source
      - transform(item) — optional pre-processing before NDF
      - store_enriched(enriched) — persist to graph/Redis

    The base class provides:
      - process(item) — NDF enrichment pipeline (shared across all connectors)
      - run_cycle() — poll → transform → process → store loop
      - start()/stop() — background polling lifecycle
    """

    def __init__(self, connector_type: str, tenant_id: str, namespace_prefix: str):
        self.connector_type = connector_type
        self.tenant_id = tenant_id
        self.namespace_prefix = namespace_prefix
        self.status = ConnectorStatus.IDLE
        self.metrics = ConnectorMetrics()
        self._config: Dict[str, Any] = {}
        self._poll_interval_seconds: int = 300
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._profiler = None  # Set by Blueprint during wiring

    # ── Configuration ─────────────────────────────────────────────────────

    @abc.abstractmethod
    def configure(self, config: Dict[str, Any]) -> None:
        """Validate and store connector-specific configuration."""
        ...

    def set_profiler(self, profiler) -> None:
        """Inject the NDF profiler (ContentProfiler component from Blueprint)."""
        self._profiler = profiler

    # ── Content Retrieval ─────────────────────────────────────────────────

    @abc.abstractmethod
    async def poll(self) -> List[ContentItem]:
        """Fetch new content items from the external source."""
        ...

    async def transform(self, item: ContentItem) -> ContentItem:
        """Optional pre-processing hook. Default: passthrough."""
        return item

    # ── NDF Enrichment (shared) ───────────────────────────────────────────

    async def process(self, item: ContentItem) -> EnrichedContent:
        """
        Run the ADAM NDF profiling pipeline on a content item.

        This is the shared intelligence layer — every connector benefits from the
        same 441-construct, 27-dimension psychological analysis.
        """
        start = time.perf_counter()

        ndf_profile: Dict[str, float] = {}
        segments: List[str] = []
        constructs: Dict[str, float] = {}
        mechanisms: List[str] = []
        confidence = 0.0

        if self._profiler:
            try:
                result = await self._profiler.profile(item.title, item.body, item.metadata)
                ndf_profile = result.get("ndf_profile", {})
                segments = result.get("segments", [])
                constructs = result.get("constructs", {})
                mechanisms = result.get("mechanisms", [])
                confidence = result.get("confidence", 0.0)
            except Exception as e:
                logger.warning("NDF profiling failed for %s: %s", item.source_id, e)
        else:
            ndf_profile = self._heuristic_ndf(item)
            confidence = 0.3

        elapsed_ms = (time.perf_counter() - start) * 1000
        self._update_processing_avg(elapsed_ms)

        return EnrichedContent(
            content_id=f"{self.tenant_id}:{item.source_id}",
            tenant_id=self.tenant_id,
            source_id=item.source_id,
            title=item.title,
            url=item.url,
            ndf_profile=ndf_profile,
            segments=segments,
            psychological_constructs=constructs,
            mechanisms_relevant=mechanisms,
            enrichment_confidence=confidence,
            metadata={**item.metadata, "processing_ms": elapsed_ms},
        )

    # ── Storage ───────────────────────────────────────────────────────────

    @abc.abstractmethod
    async def store_enriched(self, enriched: EnrichedContent) -> None:
        """Persist enriched content to Neo4j/Redis within tenant namespace."""
        ...

    # ── Lifecycle ─────────────────────────────────────────────────────────

    async def run_cycle(self) -> int:
        """Execute one poll → transform → process → store cycle. Returns items processed."""
        self.status = ConnectorStatus.POLLING
        try:
            items = await self.poll()
            self.metrics.items_polled += len(items)
            self.metrics.last_poll_at = datetime.now(timezone.utc)
        except Exception as e:
            self.status = ConnectorStatus.ERROR
            self.metrics.last_error = str(e)
            logger.error("[%s/%s] Poll failed: %s", self.tenant_id, self.connector_type, e)
            return 0

        self.status = ConnectorStatus.PROCESSING
        processed = 0
        for item in items:
            try:
                transformed = await self.transform(item)
                enriched = await self.process(transformed)
                await self.store_enriched(enriched)
                self.metrics.items_processed += 1
                processed += 1
            except Exception as e:
                self.metrics.items_failed += 1
                self.metrics.last_error = str(e)
                logger.warning(
                    "[%s/%s] Failed to process item %s: %s",
                    self.tenant_id, self.connector_type, item.source_id, e,
                )

        self.status = ConnectorStatus.IDLE
        return processed

    async def start(self) -> None:
        """Start background polling loop."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._poll_loop())
        logger.info("[%s/%s] Connector started (interval=%ds)", self.tenant_id, self.connector_type, self._poll_interval_seconds)

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self.status = ConnectorStatus.STOPPED
        logger.info("[%s/%s] Connector stopped", self.tenant_id, self.connector_type)

    async def _poll_loop(self) -> None:
        while self._running:
            try:
                await self.run_cycle()
            except Exception as e:
                logger.error("[%s/%s] Cycle error: %s", self.tenant_id, self.connector_type, e)
            await asyncio.sleep(self._poll_interval_seconds)

    # ── Helpers ───────────────────────────────────────────────────────────

    def _heuristic_ndf(self, item: ContentItem) -> Dict[str, float]:
        """Fallback NDF estimation from text keywords when profiler unavailable."""
        text = f"{item.title} {item.body}".lower()
        return {
            "approach_avoidance": 0.6 if "benefit" in text or "gain" in text else 0.4,
            "temporal_horizon": 0.7 if "future" in text or "plan" in text else 0.3,
            "social_calibration": 0.6 if "review" in text or "people" in text else 0.4,
            "uncertainty_tolerance": 0.5,
            "status_sensitivity": 0.6 if "premium" in text or "exclusive" in text else 0.4,
            "cognitive_engagement": 0.6 if len(text) > 500 else 0.4,
            "arousal_seeking": 0.6 if "exciting" in text or "new" in text else 0.4,
        }

    def _update_processing_avg(self, elapsed_ms: float) -> None:
        n = self.metrics.items_processed + 1
        self.metrics.avg_processing_ms = (
            self.metrics.avg_processing_ms * (n - 1) + elapsed_ms
        ) / n

    def get_health(self) -> Dict[str, Any]:
        return {
            "connector_type": self.connector_type,
            "tenant_id": self.tenant_id,
            "status": self.status.value,
            "metrics": self.metrics.model_dump(),
        }
