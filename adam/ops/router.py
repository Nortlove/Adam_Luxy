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

        # Generate specific StackAdapt campaign instructions
        from adam.ops.campaign_actions import generate_campaign_action
        campaign_action = generate_campaign_action(payload)

        # Store the accepted recommendation with campaign action details
        accepted = {
            "type": rec_type,
            "title": rec_title,
            "data": rec_data,
            "accepted_at": time.time(),
            "status": "accepted",
            "campaign_action": campaign_action,
        }
        await infra.redis.lpush("adam:ops:accepted_recommendations", json.dumps(accepted))
        await infra.redis.ltrim("adam:ops:accepted_recommendations", 0, 100)

        # Store active changes for the system to track impact
        change_key = f"adam:ops:active_change:{rec_type}:{int(time.time())}"
        await infra.redis.set(change_key, json.dumps({
            "type": rec_type,
            "action": campaign_action,
            "accepted_at": time.time(),
            "measuring_until": time.time() + 7 * 86400,  # 7-day measurement window
        }), ex=3600 * 24 * 14)

        return {
            "status": "accepted",
            "type": rec_type,
            "agency_instructions": campaign_action.get("agency_instructions", ""),
            "stackadapt_changes": campaign_action.get("stackadapt_changes", []),
            "expected_impact": campaign_action.get("expected_impact", ""),
            "measurement_plan": campaign_action.get("measurement_plan", ""),
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


@router.get("/daily-report")
async def get_daily_report():
    """Generate the daily action report.

    Summarizes all pending recommendations with specific StackAdapt
    instructions, plus the history of accepted actions and their
    measurement status.
    """
    try:
        from adam.ops.campaign_actions import generate_daily_action_report
        from adam.core.dependencies import Infrastructure
        infra = Infrastructure.get_instance()

        # Get recommendations
        recs_raw = await infra.redis.lrange("adam:ops:recommendations", 0, 20)
        recs = [json.loads(r) for r in recs_raw]

        # Get accepted
        acc_raw = await infra.redis.lrange("adam:ops:accepted_recommendations", 0, 20)
        accepted = [json.loads(a) for a in acc_raw]

        report = generate_daily_action_report(recs, accepted)
        return {"report": report, "recommendations": len(recs), "accepted": len(accepted)}
    except Exception as e:
        return {"error": str(e)}


@router.get("/intelligence-report")
async def get_intelligence_report(period_hours: int = 48):
    """Generate the every-other-day intelligence report.

    Returns prioritized StackAdapt actions based on observed data.
    Each action is a specific instruction: what to change, in which
    campaign, why, and what we expect to happen.

    Args:
        period_hours: Lookback window (default 48 = every other day)
    """
    try:
        from adam.core.dependencies import Infrastructure
        from adam.ops.intelligence_report import (
            generate_intelligence_report,
            format_report_markdown,
        )
        infra = Infrastructure.get_instance()
        report = await generate_intelligence_report(infra.redis, period_hours)
        markdown = format_report_markdown(report)

        return {
            "report_id": report.report_id,
            "period": report.period_label,
            "total_impressions": report.total_impressions,
            "total_conversions": report.total_conversions,
            "actions_count": len(report.actions),
            "actions": [
                {
                    "priority": a.priority,
                    "category": a.category,
                    "campaign": a.campaign,
                    "action": a.action,
                    "rationale": a.rationale,
                    "expected_impact": a.expected_impact,
                    "confidence": a.confidence,
                }
                for a in report.actions
            ],
            "domain_performance": report.domain_performance,
            "archetype_performance": report.archetype_performance,
            "suppression_candidates_count": len(report.suppression_candidates),
            "markdown_report": markdown,
        }
    except Exception as e:
        return {"error": str(e)}


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
