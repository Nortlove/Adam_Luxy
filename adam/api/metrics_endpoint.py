# =============================================================================
# ADAM Prometheus Metrics Endpoint
# Location: adam/api/metrics_endpoint.py
# =============================================================================

"""
PROMETHEUS METRICS ENDPOINT

This module exposes /metrics endpoint for Prometheus scraping.
"""

from fastapi import APIRouter, Response
from adam.monitoring.learning_metrics import metrics_exporter

router = APIRouter(tags=["metrics"])


@router.get("/metrics")
async def get_metrics():
    """
    Prometheus metrics endpoint.
    
    Returns all ADAM learning metrics in Prometheus format.
    """
    
    return Response(
        content=metrics_exporter.get_metrics(),
        media_type=metrics_exporter.get_content_type(),
    )


@router.get("/metrics/health")
async def metrics_health():
    """
    Health check for metrics system.
    """
    
    return {
        "status": "healthy",
        "metrics_available": True,
    }
