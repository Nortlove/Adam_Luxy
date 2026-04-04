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


@router.get("/metrics/information-value")
async def information_value_metrics():
    """Information value system observability metrics."""
    try:
        from adam.intelligence.information_value import iv_metrics
        return iv_metrics.summary()
    except ImportError:
        return {"error": "information_value module not available"}
