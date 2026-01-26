# =============================================================================
# ADAM Embedding Monitoring Dashboard
# Location: adam/embeddings/monitoring.py
# =============================================================================

"""
EMBEDDING MONITORING DASHBOARD

Comprehensive monitoring for the embedding infrastructure.

Metrics:
- Generation performance (latency, throughput, errors)
- Storage utilization (vector counts, index stats)
- Search performance (query latency, recall estimates)
- Model health (drift detection, quality tracking)
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from enum import Enum

from pydantic import BaseModel, Field
from prometheus_client import Counter, Gauge, Histogram, generate_latest, CONTENT_TYPE_LATEST

logger = logging.getLogger(__name__)


# =============================================================================
# PROMETHEUS METRICS (Additional)
# =============================================================================

# Embedding quality metrics
EMBEDDING_QUALITY_SCORE = Gauge(
    "adam_embedding_quality_score",
    "Embedding quality score",
    ["model", "dimension"],
)

EMBEDDING_DRIFT_SCORE = Gauge(
    "adam_embedding_drift_score",
    "Embedding distribution drift score",
    ["model", "namespace"],
)

# Search quality metrics
SEARCH_RECALL_ESTIMATE = Gauge(
    "adam_search_recall_estimate",
    "Estimated search recall",
    ["namespace", "index_type"],
)

SEARCH_LATENCY_P99 = Gauge(
    "adam_search_latency_p99_seconds",
    "P99 search latency",
    ["namespace"],
)

# Resource metrics
VECTOR_STORE_MEMORY = Gauge(
    "adam_vector_store_memory_bytes",
    "Vector store memory usage",
    ["backend"],
)

INDEX_BUILD_TIME = Gauge(
    "adam_index_build_time_seconds",
    "Last index build time",
    ["namespace", "index_type"],
)


# =============================================================================
# MONITORING MODELS
# =============================================================================

class HealthStatus(str, Enum):
    """Health status levels."""
    
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class ComponentHealth(BaseModel):
    """Health status of a component."""
    
    name: str
    status: HealthStatus = HealthStatus.UNKNOWN
    message: str = ""
    last_check: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    metrics: Dict[str, Any] = Field(default_factory=dict)


class GeneratorMetrics(BaseModel):
    """Metrics for embedding generator."""
    
    # Request metrics
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    
    # Latency
    avg_latency_ms: float = 0.0
    p50_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    p99_latency_ms: float = 0.0
    
    # Throughput
    requests_per_second: float = 0.0
    embeddings_per_second: float = 0.0
    
    # Token usage
    total_tokens: int = 0
    avg_tokens_per_request: float = 0.0
    
    # Cache
    cache_hit_rate: float = 0.0
    cache_size: int = 0
    
    # By provider
    provider_breakdown: Dict[str, Dict[str, Any]] = Field(default_factory=dict)


class StoreMetrics(BaseModel):
    """Metrics for vector store."""
    
    # Counts
    total_vectors: int = 0
    vectors_by_namespace: Dict[str, int] = Field(default_factory=dict)
    vectors_by_type: Dict[str, int] = Field(default_factory=dict)
    
    # Storage
    estimated_memory_bytes: int = 0
    disk_usage_bytes: int = 0
    
    # Index
    index_type: str = ""
    index_trained: bool = False
    index_build_time_seconds: float = 0.0
    
    # Operations
    stores_per_second: float = 0.0
    searches_per_second: float = 0.0


class SearchMetrics(BaseModel):
    """Metrics for search operations."""
    
    # Latency
    avg_latency_ms: float = 0.0
    p50_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    p99_latency_ms: float = 0.0
    
    # Quality
    estimated_recall: float = 0.0
    avg_results_returned: float = 0.0
    
    # Throughput
    queries_per_second: float = 0.0


class QualityMetrics(BaseModel):
    """Quality metrics for embeddings."""
    
    # Similarity distribution
    avg_intra_similarity: float = 0.0  # Within same type
    avg_inter_similarity: float = 0.0  # Across types
    separation_ratio: float = 0.0  # Intra/Inter
    
    # Drift
    drift_detected: bool = False
    drift_score: float = 0.0
    reference_timestamp: Optional[datetime] = None
    
    # Consistency
    model_version: str = ""
    dimension_consistency: bool = True


class DashboardSnapshot(BaseModel):
    """Complete dashboard snapshot."""
    
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    
    # Health
    overall_health: HealthStatus = HealthStatus.UNKNOWN
    component_health: List[ComponentHealth] = Field(default_factory=list)
    
    # Metrics
    generator: GeneratorMetrics = Field(default_factory=GeneratorMetrics)
    store: StoreMetrics = Field(default_factory=StoreMetrics)
    search: SearchMetrics = Field(default_factory=SearchMetrics)
    quality: QualityMetrics = Field(default_factory=QualityMetrics)
    
    # Alerts
    active_alerts: List[str] = Field(default_factory=list)


# =============================================================================
# MONITORING SERVICE
# =============================================================================

class EmbeddingMonitor:
    """
    Monitoring service for embedding infrastructure.
    
    Collects metrics, detects anomalies, and provides health status.
    """
    
    def __init__(
        self,
        generator=None,  # EmbeddingGenerator
        store=None,  # VectorStore
        check_interval_seconds: int = 60,
    ):
        self.generator = generator
        self.store = store
        self.check_interval = check_interval_seconds
        
        # History for drift detection
        self._embedding_history: List[Dict[str, Any]] = []
        self._latency_history: List[float] = []
        self._error_history: List[datetime] = []
        
        # Thresholds
        self._latency_threshold_ms = 500.0
        self._error_rate_threshold = 0.05
        self._drift_threshold = 0.3
        
        # Running
        self._running = False
        self._task = None
    
    async def start(self) -> None:
        """Start background monitoring."""
        if self._running:
            return
        
        self._running = True
        self._task = asyncio.create_task(self._monitoring_loop())
        logger.info("Embedding monitor started")
    
    async def stop(self) -> None:
        """Stop background monitoring."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Embedding monitor stopped")
    
    async def _monitoring_loop(self) -> None:
        """Background monitoring loop."""
        while self._running:
            try:
                await self._collect_metrics()
                await asyncio.sleep(self.check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Monitoring error: {e}")
                await asyncio.sleep(self.check_interval)
    
    async def _collect_metrics(self) -> None:
        """Collect and update metrics."""
        # Update Prometheus gauges
        if self.store:
            try:
                total = await self.store.count()
                # Update per-namespace counts would require iteration
            except Exception as e:
                logger.debug(f"Failed to collect store metrics: {e}")
    
    async def get_dashboard(self) -> DashboardSnapshot:
        """Get current dashboard snapshot."""
        snapshot = DashboardSnapshot()
        
        # Collect health
        snapshot.component_health = await self._check_component_health()
        snapshot.overall_health = self._compute_overall_health(
            snapshot.component_health
        )
        
        # Collect metrics
        snapshot.generator = await self._collect_generator_metrics()
        snapshot.store = await self._collect_store_metrics()
        snapshot.search = await self._collect_search_metrics()
        snapshot.quality = await self._collect_quality_metrics()
        
        # Check for alerts
        snapshot.active_alerts = self._check_alerts(snapshot)
        
        return snapshot
    
    async def _check_component_health(self) -> List[ComponentHealth]:
        """Check health of all components."""
        health_checks = []
        
        # Generator health
        gen_health = ComponentHealth(name="generator")
        if self.generator:
            try:
                # Quick test embed
                test_result = await asyncio.wait_for(
                    self.generator.embed_text("health check"),
                    timeout=5.0,
                )
                if test_result and len(test_result) > 0:
                    gen_health.status = HealthStatus.HEALTHY
                    gen_health.message = "Generator responding normally"
                else:
                    gen_health.status = HealthStatus.DEGRADED
                    gen_health.message = "Generator returned empty result"
            except asyncio.TimeoutError:
                gen_health.status = HealthStatus.DEGRADED
                gen_health.message = "Generator timeout"
            except Exception as e:
                gen_health.status = HealthStatus.UNHEALTHY
                gen_health.message = f"Generator error: {e}"
        else:
            gen_health.status = HealthStatus.UNKNOWN
            gen_health.message = "Generator not configured"
        health_checks.append(gen_health)
        
        # Store health
        store_health = ComponentHealth(name="store")
        if self.store:
            try:
                count = await self.store.count()
                store_health.status = HealthStatus.HEALTHY
                store_health.message = f"Store accessible, {count} vectors"
                store_health.metrics = {"vector_count": count}
            except Exception as e:
                store_health.status = HealthStatus.UNHEALTHY
                store_health.message = f"Store error: {e}"
        else:
            store_health.status = HealthStatus.UNKNOWN
            store_health.message = "Store not configured"
        health_checks.append(store_health)
        
        return health_checks
    
    def _compute_overall_health(
        self,
        components: List[ComponentHealth],
    ) -> HealthStatus:
        """Compute overall health from components."""
        if not components:
            return HealthStatus.UNKNOWN
        
        statuses = [c.status for c in components]
        
        if all(s == HealthStatus.HEALTHY for s in statuses):
            return HealthStatus.HEALTHY
        elif any(s == HealthStatus.UNHEALTHY for s in statuses):
            return HealthStatus.UNHEALTHY
        elif any(s == HealthStatus.DEGRADED for s in statuses):
            return HealthStatus.DEGRADED
        else:
            return HealthStatus.UNKNOWN
    
    async def _collect_generator_metrics(self) -> GeneratorMetrics:
        """Collect generator metrics."""
        metrics = GeneratorMetrics()
        
        if self.generator:
            cache_stats = self.generator.cache_stats
            metrics.cache_hit_rate = cache_stats.get("hit_rate", 0.0)
            metrics.cache_size = cache_stats.get("size", 0)
        
        return metrics
    
    async def _collect_store_metrics(self) -> StoreMetrics:
        """Collect store metrics."""
        metrics = StoreMetrics()
        
        if self.store:
            try:
                metrics.total_vectors = await self.store.count()
                metrics.index_type = self.store.backend_name
            except Exception as e:
                logger.debug(f"Failed to collect store metrics: {e}")
        
        return metrics
    
    async def _collect_search_metrics(self) -> SearchMetrics:
        """Collect search metrics."""
        metrics = SearchMetrics()
        
        # Would compute from _latency_history
        if self._latency_history:
            sorted_latencies = sorted(self._latency_history)
            n = len(sorted_latencies)
            
            metrics.avg_latency_ms = sum(sorted_latencies) / n
            metrics.p50_latency_ms = sorted_latencies[int(n * 0.5)]
            metrics.p95_latency_ms = sorted_latencies[int(n * 0.95)]
            metrics.p99_latency_ms = sorted_latencies[int(n * 0.99)]
        
        return metrics
    
    async def _collect_quality_metrics(self) -> QualityMetrics:
        """Collect quality metrics."""
        metrics = QualityMetrics()
        
        # Drift detection would compare current embeddings to reference
        metrics.drift_detected = False
        metrics.drift_score = 0.0
        
        return metrics
    
    def _check_alerts(self, snapshot: DashboardSnapshot) -> List[str]:
        """Check for alert conditions."""
        alerts = []
        
        # High latency
        if snapshot.search.p99_latency_ms > self._latency_threshold_ms:
            alerts.append(
                f"High search latency: P99 = {snapshot.search.p99_latency_ms:.0f}ms"
            )
        
        # Low cache hit rate
        if snapshot.generator.cache_hit_rate < 0.5 and snapshot.generator.total_requests > 100:
            alerts.append(
                f"Low cache hit rate: {snapshot.generator.cache_hit_rate:.1%}"
            )
        
        # Drift detected
        if snapshot.quality.drift_detected:
            alerts.append(
                f"Embedding drift detected: score = {snapshot.quality.drift_score:.3f}"
            )
        
        # Component unhealthy
        for component in snapshot.component_health:
            if component.status == HealthStatus.UNHEALTHY:
                alerts.append(f"Component unhealthy: {component.name}")
        
        return alerts
    
    def record_latency(self, latency_ms: float) -> None:
        """Record a latency observation."""
        self._latency_history.append(latency_ms)
        
        # Keep last 1000 observations
        if len(self._latency_history) > 1000:
            self._latency_history = self._latency_history[-1000:]
    
    def record_error(self) -> None:
        """Record an error."""
        self._error_history.append(datetime.now(timezone.utc))
        
        # Keep last hour
        cutoff = datetime.now(timezone.utc) - timedelta(hours=1)
        self._error_history = [
            e for e in self._error_history if e > cutoff
        ]


# =============================================================================
# DASHBOARD API ENDPOINTS
# =============================================================================

def create_dashboard_routes(monitor: EmbeddingMonitor):
    """
    Create FastAPI routes for the monitoring dashboard.
    
    Usage:
        from fastapi import FastAPI
        
        app = FastAPI()
        monitor = EmbeddingMonitor(generator, store)
        dashboard_router = create_dashboard_routes(monitor)
        app.include_router(dashboard_router, prefix="/api/embeddings/monitor")
    """
    from fastapi import APIRouter, Response
    
    router = APIRouter(tags=["embedding-monitoring"])
    
    @router.get("/health")
    async def health():
        """Get embedding infrastructure health."""
        dashboard = await monitor.get_dashboard()
        return {
            "status": dashboard.overall_health.value,
            "components": [
                {
                    "name": c.name,
                    "status": c.status.value,
                    "message": c.message,
                }
                for c in dashboard.component_health
            ],
        }
    
    @router.get("/dashboard")
    async def dashboard():
        """Get complete dashboard snapshot."""
        return await monitor.get_dashboard()
    
    @router.get("/metrics")
    async def metrics():
        """Get Prometheus metrics."""
        return Response(
            content=generate_latest(),
            media_type=CONTENT_TYPE_LATEST,
        )
    
    @router.get("/alerts")
    async def alerts():
        """Get active alerts."""
        dashboard = await monitor.get_dashboard()
        return {
            "alerts": dashboard.active_alerts,
            "count": len(dashboard.active_alerts),
        }
    
    @router.get("/generator")
    async def generator_metrics():
        """Get generator metrics."""
        dashboard = await monitor.get_dashboard()
        return dashboard.generator
    
    @router.get("/store")
    async def store_metrics():
        """Get store metrics."""
        dashboard = await monitor.get_dashboard()
        return dashboard.store
    
    @router.get("/search")
    async def search_metrics():
        """Get search metrics."""
        dashboard = await monitor.get_dashboard()
        return dashboard.search
    
    @router.get("/quality")
    async def quality_metrics():
        """Get quality metrics."""
        dashboard = await monitor.get_dashboard()
        return dashboard.quality
    
    return router
