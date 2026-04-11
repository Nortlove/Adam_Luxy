# =============================================================================
# Operations Intelligence API Router
# Location: adam/ops/router.py
# =============================================================================

"""
API endpoints for the Operations Intelligence system.

GET /api/v1/ops/dashboard          — Complete system status
GET /api/v1/ops/recommendations    — Generated recommendations
GET /api/v1/ops/log                — Decision audit trail
GET /api/v1/ops/alerts             — Active alerts
POST /api/v1/ops/run-cycle         — Trigger intelligence cycle manually
"""

import logging
import time
from typing import Optional

from fastapi import APIRouter, HTTPException

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/ops",
    tags=["operations-intelligence"],
)


def _get_engine():
    """Get the operations intelligence engine."""
    from adam.ops.intelligence import get_ops_engine
    engine = get_ops_engine()
    if engine is None:
        # Try to create one on the fly
        try:
            from adam.core.dependencies import Infrastructure
            from adam.ops.intelligence import OperationsIntelligenceEngine
            infra = Infrastructure.get_instance()
            return OperationsIntelligenceEngine(infra.redis)
        except Exception:
            raise HTTPException(503, "Operations engine not initialized")
    return engine


@router.get("/dashboard")
async def get_dashboard():
    """Complete operations dashboard.

    Returns real-time system status including:
    - Telemetry flow (sessions tracked, organic ratio)
    - Profile counts and archetype distribution
    - Conversion data
    - Barrier distribution
    - Active alerts
    - Recent recommendations
    """
    engine = _get_engine()
    return await engine.build_dashboard()


@router.get("/recommendations")
async def get_recommendations(limit: int = 20):
    """Get generated recommendations.

    Each recommendation includes:
    - Type (budget_reallocation, frequency_adjustment, creative_focus, etc.)
    - Archetype affected
    - Severity (high, medium, low)
    - Specific recommendation text
    - Data that led to the recommendation
    - Confidence score
    """
    engine = _get_engine()
    recs = await engine.get_recommendations(limit=limit)
    return {"recommendations": recs, "count": len(recs)}


@router.get("/log")
async def get_ops_log(limit: int = 50):
    """Decision audit trail.

    Every system decision, recommendation, alert, and insight
    with timestamp, reasoning, and supporting data.
    """
    engine = _get_engine()
    log = await engine.get_log(limit=limit)
    return {"log": log, "count": len(log)}


@router.get("/alerts")
async def get_alerts(limit: int = 20):
    """Active alerts.

    Severity levels:
    - critical: System down or data flow stopped
    - high: Reactance detected, significant performance change
    - warning: Approaching thresholds
    - info: Notable patterns
    """
    engine = _get_engine()
    alerts = await engine.get_alerts(limit=limit)
    return {"alerts": alerts, "count": len(alerts)}


@router.post("/run-cycle")
async def trigger_intelligence_cycle():
    """Manually trigger an intelligence analysis cycle.

    Normally runs hourly. Use this to force an immediate analysis.
    Returns the cycle results including all recommendations generated.
    """
    engine = _get_engine()
    start = time.monotonic()
    results = await engine.run_intelligence_cycle()
    elapsed = (time.monotonic() - start) * 1000

    return {
        "status": "completed",
        "recommendations_generated": len(results.get("recommendations", [])),
        "alerts_fired": len(results.get("alerts", [])),
        "insights_discovered": len(results.get("insights", [])),
        "duration_ms": round(elapsed, 1),
        "recommendations": results.get("recommendations", []),
        "insights": results.get("insights", []),
    }
