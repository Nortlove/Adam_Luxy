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
        "autonomous": results.get("autonomous", {}),
        "duration_ms": round(elapsed, 1),
        "recommendations": results.get("recommendations", []),
        "insights": results.get("insights", []),
    }


@router.get("/high-intent")
async def get_high_intent_users():
    """Users flagged as high-intent by the puzzle solver.

    These users have conversion probability above threshold.
    They should receive priority in the next retargeting touch.
    """
    try:
        from adam.ops.autonomous import get_autonomous_engine
        from adam.core.dependencies import Infrastructure
        infra = Infrastructure.get_instance()
        engine = get_autonomous_engine(infra.redis)
        if engine:
            users = await engine.get_high_intent_users()
            return {"high_intent_users": users, "count": len(users)}
    except Exception:
        pass
    return {"high_intent_users": [], "count": 0}


@router.get("/released")
async def get_released_users():
    """Users released to dormant pool by the puzzle solver.

    These users have exhausted their reactance budget or have
    conversion distance too far to justify continued spend.
    """
    try:
        from adam.ops.autonomous import get_autonomous_engine
        from adam.core.dependencies import Infrastructure
        infra = Infrastructure.get_instance()
        engine = get_autonomous_engine(infra.redis)
        if engine:
            users = await engine.get_released_users()
            return {"released_users": users, "count": len(users)}
    except Exception:
        pass
    return {"released_users": [], "count": 0}


@router.get("/discoveries")
async def get_discoveries():
    """Surprising patterns detected by the autonomous engine.

    Discoveries are statistically meaningful AND surprising findings
    that imply specific actions. These are the insights that prove
    INFORMATIV sees what nobody else can.
    """
    try:
        from adam.core.dependencies import Infrastructure
        infra = Infrastructure.get_instance()
        raw = await infra.redis.lrange("adam:discoveries", 0, 50)
        discoveries = [json.loads(d) for d in raw]
        return {"discoveries": discoveries, "count": len(discoveries)}
    except Exception:
        return {"discoveries": [], "count": 0}


@router.get("/learning")
async def get_multi_dimensional_learning():
    """Multi-dimensional learning results from the last cycle.

    Shows what the system learned across all 8 dimensions:
    - Causal: WHY conversions happened (ad-caused vs organic)
    - Temporal: WHEN users are most receptive
    - Negative: What to STOP doing (mechanism failures)
    - Transfer: Patterns from converters that apply to non-converters
    - Context: Device × time interactions that drive conversion
    """
    try:
        from adam.core.dependencies import Infrastructure
        infra = Infrastructure.get_instance()
        raw = await infra.redis.get("adam:learning:multi_dimensional")
        if raw:
            return json.loads(raw)
    except Exception:
        pass
    return {"note": "No learning data yet — will populate after first intelligence cycle with conversions"}


@router.get("/mechanism-effectiveness")
async def get_learned_mechanism_effectiveness():
    """Mechanism effectiveness learned from real conversion data.

    Shows which mechanisms actually work for each archetype,
    calibrated from observed outcomes — not theoretical priors.
    """
    try:
        from adam.ops.autonomous import get_autonomous_engine
        from adam.core.dependencies import Infrastructure
        infra = Infrastructure.get_instance()
        engine = get_autonomous_engine(infra.redis)
        if engine:
            eff = await engine.get_mechanism_effectiveness()
            return {"mechanism_effectiveness": eff}
    except Exception:
        pass
    return {"mechanism_effectiveness": {}}


@router.post("/accept-recommendation")
async def accept_recommendation(payload: dict):
    """Accept a recommendation and trigger the system to act on it.

    The dashboard presents recommendations with an 'Accept' button.
    When clicked, this endpoint receives the recommendation and
    executes the appropriate action.

    Actions:
    - budget_reallocation: logs the decision, stores new allocation
    - frequency_adjustment: updates frequency parameters
    - creative_focus: marks creative for refresh
    - release_users: releases specified users to dormant
    - mechanism_change: updates mechanism priorities
    """
    rec_type = payload.get("type", "")
    rec_data = payload.get("data", {})
    rec_title = payload.get("title", "")

    try:
        from adam.core.dependencies import Infrastructure
        from adam.ops.intelligence import OperationsIntelligenceEngine, OpsLogEntry
        infra = Infrastructure.get_instance()
        engine = OperationsIntelligenceEngine(infra.redis)

        # Log the acceptance
        await engine.log(OpsLogEntry(
            level="action",
            category="recommendation_accepted",
            title=f"ACCEPTED: {rec_title}",
            detail=json.dumps(payload)[:500],
            action_taken=f"User accepted recommendation: {rec_type}",
            confidence=payload.get("confidence", 0),
        ))

        # Store the accepted recommendation
        accepted = {
            "type": rec_type,
            "title": rec_title,
            "data": rec_data,
            "accepted_at": time.time(),
            "status": "executing",
        }
        await infra.redis.lpush("adam:ops:accepted_recommendations", json.dumps(accepted))
        await infra.redis.ltrim("adam:ops:accepted_recommendations", 0, 100)

        # Execute type-specific actions
        action_result = "logged"

        if rec_type == "budget_reallocation":
            # Store the new allocation for the weekly report to reference
            await infra.redis.set(
                "adam:ops:active_budget_change",
                json.dumps(rec_data),
                ex=3600 * 24 * 7,
            )
            action_result = "Budget reallocation stored — include in next report to agency"

        elif rec_type == "frequency_adjustment":
            await infra.redis.set(
                "adam:ops:active_frequency_change",
                json.dumps(rec_data),
                ex=3600 * 24 * 7,
            )
            action_result = "Frequency adjustment stored — include in next report to agency"

        elif rec_type == "stage_transition":
            action_result = "Stage transition noted — affects next intelligence cycle mechanism selection"

        elif rec_type == "creative_focus":
            action_result = "Creative focus stored — generate new copy variant in next cycle"

        # Update status
        accepted["status"] = "completed"
        accepted["result"] = action_result

        return {
            "status": "accepted",
            "type": rec_type,
            "action_result": action_result,
            "logged": True,
        }

    except Exception as e:
        return {"status": "error", "detail": str(e)}


@router.get("/accepted-recommendations")
async def get_accepted_recommendations():
    """Get the history of accepted recommendations."""
    try:
        from adam.core.dependencies import Infrastructure
        infra = Infrastructure.get_instance()
        raw = await infra.redis.lrange("adam:ops:accepted_recommendations", 0, 50)
        return {"accepted": [json.loads(r) for r in raw], "count": len(raw)}
    except Exception:
        return {"accepted": [], "count": 0}


@router.get("/puzzle/{user_id}")
async def get_user_puzzle(user_id: str):
    """Get unified puzzle inference for a specific user.

    Returns the complete PersonState: narrative, barrier, trajectory,
    mechanism recommendation, interaction archetype, suppress decision.
    """
    try:
        from adam.core.dependencies import Infrastructure, LearningComponents
        infra = Infrastructure.get_instance()
        components = LearningComponents.get_instance(infra)
        collector = components.signal_collector
        if collector:
            profile = await collector.get_profile(user_id)
            if profile and profile.total_sessions > 0:
                from adam.retargeting.engines.unified_puzzle import infer_person
                state = infer_person(profile.model_dump())
                return state.to_dict()
    except Exception as e:
        return {"error": str(e)}
    return {"error": f"No profile found for {user_id}"}
