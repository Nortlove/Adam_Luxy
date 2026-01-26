# =============================================================================
# ADAM Health Check Router
# Location: adam/api/health/router.py
# =============================================================================

"""
HEALTH CHECK ENDPOINTS

Kubernetes-compatible health check endpoints with detailed
component status for ADAM platform monitoring.
"""

import asyncio
import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel, Field

from adam.core.dependencies import get_infrastructure, Infrastructure

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/health", tags=["health"])


# =============================================================================
# HEALTH STATUS MODELS
# =============================================================================

class HealthStatus(str, Enum):
    """Component health status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class ComponentHealth(BaseModel):
    """Health status of a single component."""
    name: str
    status: HealthStatus
    latency_ms: Optional[float] = None
    message: Optional[str] = None
    last_check: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class LivenessResponse(BaseModel):
    """Liveness probe response."""
    status: str = "ok"
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ReadinessResponse(BaseModel):
    """Readiness probe response."""
    status: HealthStatus
    ready: bool
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class DetailedHealthResponse(BaseModel):
    """Detailed health status response."""
    status: HealthStatus
    components: List[ComponentHealth]
    version: str = "1.0.0"
    environment: str = "development"
    uptime_seconds: float
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AlertInfo(BaseModel):
    """Active alert information."""
    name: str
    severity: str
    description: str
    value: float
    threshold: float
    duration_seconds: float
    runbook_url: Optional[str] = None


class EnhancedHealthResponse(BaseModel):
    """Enhanced health response with alerts and learning loop status."""
    status: str
    is_healthy: bool
    uptime_seconds: float
    components: Dict[str, Dict]
    active_alerts: List[AlertInfo]
    alert_summary: Dict[str, int]
    learning_loop: Optional[Dict] = None
    key_metrics: Dict[str, float]
    issues: List[str]
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# Track startup time for uptime calculation
_startup_time: Optional[datetime] = None


def set_startup_time() -> None:
    """Set the application startup time."""
    global _startup_time
    _startup_time = datetime.now(timezone.utc)


def get_uptime_seconds() -> float:
    """Get application uptime in seconds."""
    if _startup_time is None:
        return 0.0
    return (datetime.now(timezone.utc) - _startup_time).total_seconds()


# =============================================================================
# HEALTH CHECK FUNCTIONS
# =============================================================================

async def check_neo4j(infra: Infrastructure) -> ComponentHealth:
    """Check Neo4j connectivity."""
    start = datetime.now(timezone.utc)
    try:
        async with infra.neo4j.session() as session:
            result = await session.run("RETURN 1 as n")
            await result.consume()
        
        latency = (datetime.now(timezone.utc) - start).total_seconds() * 1000
        return ComponentHealth(
            name="neo4j",
            status=HealthStatus.HEALTHY,
            latency_ms=latency,
            message="Connected"
        )
    except Exception as e:
        latency = (datetime.now(timezone.utc) - start).total_seconds() * 1000
        logger.error(f"Neo4j health check failed: {e}")
        return ComponentHealth(
            name="neo4j",
            status=HealthStatus.UNHEALTHY,
            latency_ms=latency,
            message=str(e)
        )


async def check_redis(infra: Infrastructure) -> ComponentHealth:
    """Check Redis connectivity."""
    start = datetime.now(timezone.utc)
    try:
        await infra.redis.ping()
        
        latency = (datetime.now(timezone.utc) - start).total_seconds() * 1000
        return ComponentHealth(
            name="redis",
            status=HealthStatus.HEALTHY,
            latency_ms=latency,
            message="Connected"
        )
    except Exception as e:
        latency = (datetime.now(timezone.utc) - start).total_seconds() * 1000
        logger.error(f"Redis health check failed: {e}")
        return ComponentHealth(
            name="redis",
            status=HealthStatus.UNHEALTHY,
            latency_ms=latency,
            message=str(e)
        )


async def check_kafka() -> ComponentHealth:
    """Check Kafka connectivity."""
    start = datetime.now(timezone.utc)
    try:
        # Import here to avoid circular imports and optional dependency
        from adam.infrastructure.kafka import get_kafka_producer
        
        producer = await get_kafka_producer()
        if producer and producer.is_connected:
            latency = (datetime.now(timezone.utc) - start).total_seconds() * 1000
            return ComponentHealth(
                name="kafka",
                status=HealthStatus.HEALTHY,
                latency_ms=latency,
                message="Connected"
            )
        else:
            latency = (datetime.now(timezone.utc) - start).total_seconds() * 1000
            return ComponentHealth(
                name="kafka",
                status=HealthStatus.DEGRADED,
                latency_ms=latency,
                message="Producer not connected"
            )
    except ImportError:
        # Kafka not configured
        return ComponentHealth(
            name="kafka",
            status=HealthStatus.UNKNOWN,
            message="Kafka not configured"
        )
    except Exception as e:
        latency = (datetime.now(timezone.utc) - start).total_seconds() * 1000
        logger.error(f"Kafka health check failed: {e}")
        return ComponentHealth(
            name="kafka",
            status=HealthStatus.UNHEALTHY,
            latency_ms=latency,
            message=str(e)
        )


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.get("/live", response_model=LivenessResponse)
async def liveness_probe() -> LivenessResponse:
    """
    Liveness probe endpoint.
    
    Returns 200 if the application is running.
    Used by Kubernetes to determine if the pod should be restarted.
    """
    return LivenessResponse()


@router.get("/ready", response_model=ReadinessResponse)
async def readiness_probe(
    response: Response,
    infra: Infrastructure = Depends(get_infrastructure)
) -> ReadinessResponse:
    """
    Readiness probe endpoint.
    
    Returns 200 if the application can accept traffic.
    Checks critical dependencies (Neo4j, Redis).
    """
    try:
        # Check critical components
        neo4j_health, redis_health = await asyncio.gather(
            check_neo4j(infra),
            check_redis(infra),
            return_exceptions=True
        )
        
        # Process results
        components = []
        for health in [neo4j_health, redis_health]:
            if isinstance(health, Exception):
                components.append(ComponentHealth(
                    name="unknown",
                    status=HealthStatus.UNHEALTHY,
                    message=str(health)
                ))
            else:
                components.append(health)
        
        # Determine overall status
        all_healthy = all(c.status == HealthStatus.HEALTHY for c in components)
        any_unhealthy = any(c.status == HealthStatus.UNHEALTHY for c in components)
        
        if all_healthy:
            status = HealthStatus.HEALTHY
            ready = True
        elif any_unhealthy:
            status = HealthStatus.UNHEALTHY
            ready = False
            response.status_code = 503
        else:
            status = HealthStatus.DEGRADED
            ready = True  # Degraded but can still serve
        
        return ReadinessResponse(status=status, ready=ready)
        
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        response.status_code = 503
        return ReadinessResponse(status=HealthStatus.UNHEALTHY, ready=False)


@router.get("/status", response_model=DetailedHealthResponse)
async def detailed_health_status(
    infra: Infrastructure = Depends(get_infrastructure)
) -> DetailedHealthResponse:
    """
    Detailed health status endpoint.
    
    Returns comprehensive health information about all components.
    Used for debugging and monitoring dashboards.
    """
    # Check all components in parallel
    neo4j_health, redis_health, kafka_health = await asyncio.gather(
        check_neo4j(infra),
        check_redis(infra),
        check_kafka(),
        return_exceptions=True
    )
    
    components = []
    for health in [neo4j_health, redis_health, kafka_health]:
        if isinstance(health, Exception):
            components.append(ComponentHealth(
                name="unknown",
                status=HealthStatus.UNHEALTHY,
                message=str(health)
            ))
        else:
            components.append(health)
    
    # Determine overall status
    statuses = [c.status for c in components if c.status != HealthStatus.UNKNOWN]
    if all(s == HealthStatus.HEALTHY for s in statuses):
        overall = HealthStatus.HEALTHY
    elif any(s == HealthStatus.UNHEALTHY for s in statuses):
        overall = HealthStatus.UNHEALTHY
    else:
        overall = HealthStatus.DEGRADED
    
    return DetailedHealthResponse(
        status=overall,
        components=components,
        uptime_seconds=get_uptime_seconds()
    )


# =============================================================================
# ENHANCED HEALTH ENDPOINTS
# =============================================================================

@router.get("/detailed", response_model=EnhancedHealthResponse)
async def enhanced_health_status() -> EnhancedHealthResponse:
    """
    Enhanced health status with alerts and monitoring data.
    
    Returns:
    - Component health
    - Active alerts
    - Learning loop status
    - Key metrics
    - Issues list
    
    Use this endpoint for:
    - Monitoring dashboards
    - Incident response
    - System health verification
    """
    try:
        from adam.monitoring.system_health import get_system_health_aggregator
        
        aggregator = get_system_health_aggregator()
        report = await aggregator.generate_report()
        
        # Convert alerts to AlertInfo
        alerts = []
        for alert_dict in report.active_alerts:
            alerts.append(AlertInfo(
                name=alert_dict.get("name", "unknown"),
                severity=alert_dict.get("severity", "unknown"),
                description=alert_dict.get("description", ""),
                value=alert_dict.get("last_value", 0.0),
                threshold=alert_dict.get("threshold", 0.0) if "threshold" in alert_dict else 0.0,
                duration_seconds=alert_dict.get("duration_seconds", 0.0),
                runbook_url=alert_dict.get("runbook_url"),
            ))
        
        # Alert summary
        alert_summary = {
            "critical": len([a for a in alerts if a.severity == "critical"]),
            "warning": len([a for a in alerts if a.severity == "warning"]),
            "info": len([a for a in alerts if a.severity == "info"]),
            "total": len(alerts),
        }
        
        return EnhancedHealthResponse(
            status=report.status.value,
            is_healthy=report.is_healthy,
            uptime_seconds=report.uptime_seconds,
            components={
                name: {
                    "status": c.status.value,
                    "dependencies": c.dependencies,
                    "issues": c.issues,
                }
                for name, c in report.components.items()
            },
            active_alerts=alerts,
            alert_summary=alert_summary,
            learning_loop=report.learning_loop_health,
            key_metrics=report.key_metrics,
            issues=report.issues,
        )
        
    except ImportError:
        # Monitoring module not available
        return EnhancedHealthResponse(
            status="unknown",
            is_healthy=True,
            uptime_seconds=get_uptime_seconds(),
            components={},
            active_alerts=[],
            alert_summary={"critical": 0, "warning": 0, "info": 0, "total": 0},
            learning_loop=None,
            key_metrics={},
            issues=["Monitoring module not available"],
        )
    except Exception as e:
        logger.error(f"Enhanced health check failed: {e}")
        return EnhancedHealthResponse(
            status="error",
            is_healthy=False,
            uptime_seconds=get_uptime_seconds(),
            components={},
            active_alerts=[],
            alert_summary={"critical": 0, "warning": 0, "info": 0, "total": 0},
            learning_loop=None,
            key_metrics={},
            issues=[f"Health check error: {str(e)}"],
        )


@router.get("/alerts")
async def get_active_alerts() -> Dict:
    """
    Get currently active alerts.
    
    Returns all firing alerts with severity and details.
    """
    try:
        from adam.infrastructure.alerting import get_alert_manager
        
        manager = get_alert_manager()
        summary = manager.get_alert_summary()
        
        return {
            "status": "ok",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **summary,
        }
        
    except ImportError:
        return {
            "status": "unavailable",
            "message": "Alerting module not available",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "total_active": 0,
            "alerts": [],
        }
    except Exception as e:
        logger.error(f"Failed to get alerts: {e}")
        return {
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "total_active": 0,
            "alerts": [],
        }


@router.get("/learning-loop")
async def get_learning_loop_health() -> Dict:
    """
    Get learning loop health status.
    
    Returns:
    - Decision/outcome counts
    - Attribution rate
    - Pending outcomes
    - Issues
    """
    try:
        from adam.monitoring.learning_loop_monitor import get_learning_loop_monitor
        
        monitor = get_learning_loop_monitor()
        health = monitor.get_health()
        
        return {
            "status": "ok",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **health.to_dict(),
            "statistics": monitor.get_statistics(),
        }
        
    except ImportError:
        return {
            "status": "unavailable",
            "message": "Learning loop monitor not available",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        logger.error(f"Failed to get learning loop health: {e}")
        return {
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


@router.get("/metrics-summary")
async def get_metrics_summary() -> Dict:
    """
    Get summary of key metrics for dashboards.
    
    Returns aggregated metrics suitable for monitoring dashboards.
    """
    metrics = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "uptime_seconds": get_uptime_seconds(),
    }
    
    try:
        from prometheus_client import REGISTRY
        
        for metric in REGISTRY.collect():
            if metric.name.startswith("adam_"):
                for sample in metric.samples:
                    # Only include gauges and counters, not histograms
                    if not sample.name.endswith(("_bucket", "_sum", "_count")):
                        key = sample.name
                        if sample.labels:
                            key = f"{key}_{list(sample.labels.values())[0]}"
                        metrics[key] = sample.value
                        
    except Exception as e:
        logger.debug(f"Could not collect metrics: {e}")
        metrics["error"] = str(e)
    
    return metrics
