# =============================================================================
# ADAM Monitoring API Router
# Location: adam/api/monitoring/router.py
# =============================================================================

"""
MONITORING API ROUTER

FastAPI endpoints for monitoring and observability.

Endpoints:
- GET /api/v1/monitoring/health - System health
- GET /api/v1/monitoring/drift - Drift status
- GET /api/v1/monitoring/alerts - Active alerts
- POST /api/v1/monitoring/alerts/{id}/acknowledge - Acknowledge alert
- POST /api/v1/monitoring/alerts/{id}/resolve - Resolve alert
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from adam.core.container import get_container, ADAMContainer
from adam.monitoring.health_service import (
    HealthMonitoringService,
    HealthStatus,
    SystemHealth,
)
from adam.monitoring.drift_detection import (
    DriftDetectionService,
    DriftSnapshot,
    DriftSeverity,
)
from adam.monitoring.alerting import AlertingService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/monitoring", tags=["monitoring"])


# =============================================================================
# RESPONSE MODELS
# =============================================================================

class HealthResponse(BaseModel):
    """System health response."""
    
    status: str
    health_score: float = Field(ge=0.0, le=1.0)
    
    healthy_count: int = Field(ge=0)
    degraded_count: int = Field(ge=0)
    unhealthy_count: int = Field(ge=0)
    
    components: Dict[str, Any] = Field(default_factory=dict)
    issues: List[str] = Field(default_factory=list)
    
    checked_at: str


class DriftResponse(BaseModel):
    """Drift status response."""
    
    overall_health: float = Field(ge=0.0, le=1.0)
    has_critical_drift: bool
    
    active_alerts_count: int = Field(ge=0)
    alerts_by_severity: Dict[str, int] = Field(default_factory=dict)
    
    source_health: Dict[str, Any] = Field(default_factory=dict)
    construct_health: Dict[str, Any] = Field(default_factory=dict)


class AlertResponse(BaseModel):
    """Alert response."""
    
    alert_id: str
    drift_type: str
    severity: str
    status: str
    
    component: str
    description: str
    recommendations: List[str]
    
    detected_at: str
    resolved_at: Optional[str] = None


class AlertSummaryResponse(BaseModel):
    """Alert summary response."""
    
    total_alerts: int = Field(ge=0)
    active_alerts: int = Field(ge=0)
    
    by_severity: Dict[str, int] = Field(default_factory=dict)
    
    alerts: List[AlertResponse]


class AcknowledgeRequest(BaseModel):
    """Acknowledge alert request."""
    
    acknowledged_by: str


class ResolveRequest(BaseModel):
    """Resolve alert request."""
    
    resolution_note: str
    false_positive: bool = Field(default=False)


# =============================================================================
# SINGLETON SERVICES
# =============================================================================

_health_service: Optional[HealthMonitoringService] = None
_drift_engine: Optional[DriftDetectionService] = None
_alerting_service: Optional[AlertingService] = None


def get_health_service(
    container: ADAMContainer = Depends(get_container),
) -> HealthMonitoringService:
    """Get or create health service."""
    global _health_service
    if _health_service is None:
        _health_service = HealthMonitoringService(container)
    return _health_service


def get_drift_engine() -> DriftDetectionService:
    """Get or create drift engine."""
    global _drift_engine
    if _drift_engine is None:
        _drift_engine = DriftDetectionService()
    return _drift_engine


def get_alerting_service() -> AlertingService:
    """Get or create alerting service."""
    global _alerting_service
    if _alerting_service is None:
        _alerting_service = AlertingService()
    return _alerting_service


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.get("/health", response_model=HealthResponse)
async def get_system_health(
    health_service: HealthMonitoringService = Depends(get_health_service),
) -> HealthResponse:
    """
    Get current system health status.
    
    Runs health checks on all components and returns aggregated status.
    """
    health = await health_service.check_all()
    
    return HealthResponse(
        status=health.status.value,
        health_score=health.health_score,
        healthy_count=health.healthy_count,
        degraded_count=health.degraded_count,
        unhealthy_count=health.unhealthy_count,
        components={
            name: {
                "status": comp.status.value,
                "latency_ms": comp.latency_ms,
                "type": comp.component_type.value,
            }
            for name, comp in health.components.items()
        },
        issues=health.issues,
        checked_at=health.checked_at.isoformat(),
    )


@router.get("/health/{component}")
async def get_component_health(
    component: str,
    health_service: HealthMonitoringService = Depends(get_health_service),
) -> Dict[str, Any]:
    """Get health of a specific component."""
    comp_health = health_service.get_component_health(component)
    
    if not comp_health:
        raise HTTPException(status_code=404, detail=f"Component not found: {component}")
    
    return {
        "component": comp_health.component_name,
        "status": comp_health.status.value,
        "type": comp_health.component_type.value,
        "latency_ms": comp_health.latency_ms,
        "error_rate": comp_health.error_rate,
        "dependencies": comp_health.dependencies,
        "last_check": comp_health.last_check.isoformat(),
    }


@router.get("/drift", response_model=DriftResponse)
async def get_drift_status(
    drift_engine: DriftDetectionService = Depends(get_drift_engine),
) -> DriftResponse:
    """
    Get current drift detection status.
    
    Returns overview of drift across all dimensions.
    """
    snapshot = drift_engine.generate_snapshot()
    
    alerts_by_severity = {}
    for alert in snapshot.active_alerts:
        sev = alert.severity.value
        alerts_by_severity[sev] = alerts_by_severity.get(sev, 0) + 1
    
    return DriftResponse(
        overall_health=snapshot.overall_health,
        has_critical_drift=snapshot.has_critical_drift,
        active_alerts_count=len(snapshot.active_alerts),
        alerts_by_severity=alerts_by_severity,
        source_health={
            name: health.model_dump()
            for name, health in snapshot.source_health.items()
        },
        construct_health={
            name: health.model_dump()
            for name, health in snapshot.construct_health.items()
        },
    )


@router.get("/alerts", response_model=AlertSummaryResponse)
async def get_alerts(
    alerting_service: AlertingService = Depends(get_alerting_service),
) -> AlertSummaryResponse:
    """
    Get all active alerts.
    """
    summary = alerting_service.get_alert_summary()
    active = alerting_service.get_active_alerts()
    
    return AlertSummaryResponse(
        total_alerts=summary["total_alerts"],
        active_alerts=summary["active_alerts"],
        by_severity=summary["by_severity"],
        alerts=[
            AlertResponse(
                alert_id=a.alert_id,
                drift_type=a.drift_type.value,
                severity=a.severity.value,
                status=a.status.value,
                component=a.component,
                description=a.description,
                recommendations=a.recommendations,
                detected_at=a.detected_at.isoformat(),
                resolved_at=a.resolved_at.isoformat() if a.resolved_at else None,
            )
            for a in active
        ],
    )


@router.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: str,
    request: AcknowledgeRequest,
    alerting_service: AlertingService = Depends(get_alerting_service),
) -> Dict[str, Any]:
    """Acknowledge an alert."""
    success = await alerting_service.acknowledge_alert(
        alert_id, request.acknowledged_by
    )
    
    if not success:
        raise HTTPException(status_code=404, detail=f"Alert not found: {alert_id}")
    
    return {"alert_id": alert_id, "acknowledged": True}


@router.post("/alerts/{alert_id}/resolve")
async def resolve_alert(
    alert_id: str,
    request: ResolveRequest,
    alerting_service: AlertingService = Depends(get_alerting_service),
) -> Dict[str, Any]:
    """Resolve an alert."""
    success = await alerting_service.resolve_alert(
        alert_id,
        request.resolution_note,
        request.false_positive,
    )
    
    if not success:
        raise HTTPException(status_code=404, detail=f"Alert not found: {alert_id}")
    
    return {
        "alert_id": alert_id,
        "resolved": True,
        "false_positive": request.false_positive,
    }


@router.get("/metrics/summary")
async def get_metrics_summary() -> Dict[str, Any]:
    """Get summary of key metrics."""
    from adam.monitoring.learning_metrics import metrics_exporter
    
    # Would extract key gauges/counters
    return {
        "status": "ok",
        "metrics_available": True,
        "prometheus_endpoint": "/metrics",
    }
