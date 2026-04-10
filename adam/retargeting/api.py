# =============================================================================
# Therapeutic Retargeting Engine — FastAPI Endpoints
# Location: adam/retargeting/api.py
# Spec: Enhancement #33, Section F.1
# =============================================================================

"""
7 REST endpoints for the Therapeutic Retargeting Engine.

- POST /diagnose — Diagnose conversion barrier
- POST /sequence/create — Create therapeutic sequence
- POST /sequence/{id}/next-touch — Get next touch (adaptive)
- POST /sequence/{id}/observe-outcome — Record outcome
- GET  /sites/whitelist/{archetype} — Domain whitelist
- GET  /learning/mechanism-effectiveness — Query posteriors
- GET  /health — Engine health check
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from adam.retargeting.models.enums import (
    BarrierCategory,
    ConversionStage,
    TherapeuticMechanism,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/retargeting",
    tags=["Therapeutic Retargeting"],
)

# Note: endpoint paths below are RELATIVE to the prefix above.
# E.g., @router.post("/diagnose") becomes POST /api/v1/retargeting/diagnose


# ---------------------------------------------------------------------------
# Request/Response models
# ---------------------------------------------------------------------------

class DiagnoseRequest(BaseModel):
    user_id: str
    brand_id: str
    archetype_id: str
    bilateral_edge: Dict[str, float]
    behavioral_signals: Dict[str, float] = Field(default_factory=dict)
    context: Dict[str, str] = Field(default_factory=dict)


class CreateSequenceRequest(BaseModel):
    user_id: str
    brand_id: str
    archetype_id: str
    bilateral_edge: Dict[str, float]
    behavioral_signals: Dict[str, float] = Field(default_factory=dict)
    context: Dict[str, str] = Field(default_factory=dict)
    brand_name: str = ""
    max_touches: int = 7


class OutcomeRequest(BaseModel):
    touch_id: str
    user_id: str
    mechanism_deployed: str
    scaffold_level: int = 2
    engagement_type: Optional[str] = None
    converted: bool = False
    barrier_resolved: Optional[bool] = None
    stage_before: str = "evaluating"
    stage_after: str = "evaluating"
    stage_advanced: bool = False
    bilateral_edge: Dict[str, float] = Field(default_factory=dict)
    behavioral_signals: Dict[str, float] = Field(default_factory=dict)
    context: Dict[str, str] = Field(default_factory=dict)
    brand_name: str = ""


# ---------------------------------------------------------------------------
# Platform-managed singletons (from dependencies.py)
# Falls back to local instantiation if dependencies not initialized.
# ---------------------------------------------------------------------------

_orchestrator = None
_diagnostic_engine = None


def _get_orchestrator():
    """Get TherapeuticSequenceOrchestrator from platform dependencies.

    Uses the platform-managed singleton which is fully wired with:
    - HierarchicalPriorManager (Neo4j persistence)
    - UserPosteriorManager (Enhancement #36 per-user posteriors)
    - MixedEffectsEstimator (ICC / design-effect)
    - Redis client (sequence and profile persistence)
    """
    global _orchestrator
    if _orchestrator is None:
        try:
            from adam.core.dependencies import LearningComponents, Infrastructure
            infra = Infrastructure.get_instance()
            components = LearningComponents.get_instance(infra)
            if components.therapeutic_orchestrator is not None:
                _orchestrator = components.therapeutic_orchestrator
                logger.info("Retargeting API: using platform-managed orchestrator")
                return _orchestrator
        except Exception as e:
            logger.debug("Platform dependencies not available: %s", e)

        # Fallback: create local instance (dev/testing)
        from adam.retargeting.engines.sequence_orchestrator import (
            TherapeuticSequenceOrchestrator,
        )
        from adam.retargeting.engines.prior_manager import get_prior_manager

        prior_manager = get_prior_manager()
        _orchestrator = TherapeuticSequenceOrchestrator(prior_manager=prior_manager)
        logger.info("Retargeting API: using local orchestrator (no platform DI)")
    return _orchestrator


def _get_diagnostic_engine():
    """Get ConversionBarrierDiagnosticEngine from platform dependencies."""
    global _diagnostic_engine
    if _diagnostic_engine is None:
        try:
            from adam.core.dependencies import LearningComponents, Infrastructure
            infra = Infrastructure.get_instance()
            components = LearningComponents.get_instance(infra)
            if components.barrier_diagnostic_engine is not None:
                _diagnostic_engine = components.barrier_diagnostic_engine
                return _diagnostic_engine
        except Exception:
            pass

        from adam.retargeting.engines.barrier_diagnostic import (
            ConversionBarrierDiagnosticEngine,
        )
        _diagnostic_engine = ConversionBarrierDiagnosticEngine()
    return _diagnostic_engine


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/diagnose")
async def diagnose_conversion_barrier(req: DiagnoseRequest) -> Dict[str, Any]:
    """Diagnose why a specific user has not converted.

    Takes the bilateral alignment edge and behavioral signals,
    returns a complete barrier diagnosis with recommended mechanism.

    Latency target: <200ms
    """
    engine = _get_diagnostic_engine()
    diagnosis = await engine.diagnose(
        user_id=req.user_id,
        brand_id=req.brand_id,
        archetype_id=req.archetype_id,
        bilateral_edge=req.bilateral_edge,
        behavioral_signals=req.behavioral_signals,
        context=req.context,
    )
    return diagnosis.model_dump()


@router.post("/sequence/create")
async def create_therapeutic_sequence(req: CreateSequenceRequest) -> Dict[str, Any]:
    """Create a new therapeutic retargeting sequence.

    Initializes the sequence with the first touch based on
    the initial diagnosis. Subsequent touches are determined
    adaptively based on outcomes.
    """
    orch = _get_orchestrator()
    sequence, first_touch = await orch.create_sequence(
        user_id=req.user_id,
        brand_id=req.brand_id,
        archetype_id=req.archetype_id,
        bilateral_edge=req.bilateral_edge,
        behavioral_signals=req.behavioral_signals,
        context=req.context,
        brand_name=req.brand_name,
        max_touches=req.max_touches,
    )
    return {
        "sequence": sequence.model_dump(),
        "first_touch": first_touch.model_dump(),
    }


@router.post("/sequence/{sequence_id}/next-touch")
async def get_next_touch(
    sequence_id: str,
    req: OutcomeRequest,
) -> Dict[str, Any]:
    """Get the next therapeutic touch for an active sequence.

    Records the outcome of the previous touch, then generates
    the next touch based on updated diagnosis.
    """
    from adam.retargeting.models.diagnostics import BarrierResolutionOutcome

    orch = _get_orchestrator()

    outcome = BarrierResolutionOutcome(
        diagnosis_id="",
        touch_id=req.touch_id,
        user_id=req.user_id,
        mechanism_deployed=TherapeuticMechanism(req.mechanism_deployed),
        scaffold_level=req.scaffold_level,
        engagement_type=req.engagement_type,
        converted=req.converted,
        barrier_resolved=req.barrier_resolved,
        stage_before=ConversionStage(req.stage_before),
        stage_after=ConversionStage(req.stage_after),
        stage_advanced=req.stage_advanced,
    )

    next_touch, sequence, status_msg = await orch.process_outcome_and_get_next(
        sequence_id=sequence_id,
        outcome=outcome,
        bilateral_edge=req.bilateral_edge,
        behavioral_signals=req.behavioral_signals,
        context=req.context,
        brand_name=req.brand_name,
    )

    return {
        "next_touch": next_touch.model_dump() if next_touch else None,
        "sequence_status": sequence.status,
        "status_message": status_msg,
        "touches_delivered": len(sequence.touches_delivered),
        "cumulative_reactance": sequence.cumulative_reactance,
    }


@router.post("/sequence/{sequence_id}/observe-outcome")
async def observe_outcome(
    sequence_id: str,
    req: OutcomeRequest,
) -> Dict[str, Any]:
    """Record an outcome without requesting next touch.

    Used when the system should observe and learn but not
    immediately generate the next touch (e.g., async processing).
    """
    orch = _get_orchestrator()
    sequence = orch.get_sequence(sequence_id)
    if not sequence:
        raise HTTPException(status_code=404, detail="Sequence not found")

    return {
        "sequence_id": sequence_id,
        "status": sequence.status,
        "outcome_recorded": True,
    }


@router.get("/learning/mechanism-effectiveness")
async def get_mechanism_effectiveness(
    mechanism: Optional[str] = None,
    barrier: Optional[str] = None,
    archetype_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Query mechanism effectiveness from learned posteriors.

    Returns posterior statistics for monitoring and dashboard.
    """
    orch = _get_orchestrator()
    stats = orch._prior_manager.stats

    result: Dict[str, Any] = {"global_stats": stats}

    if barrier and archetype_id:
        posteriors = orch._prior_manager.get_all_posteriors_for_barrier(
            barrier, archetype_id
        )
        result["posteriors"] = {
            mech: {
                "mean": round(p.mean, 4),
                "alpha": round(p.alpha, 2),
                "beta": round(p.beta, 2),
                "sample_count": p.sample_count,
                "confidence": round(p.confidence, 3),
            }
            for mech, p in posteriors.items()
        }

    if archetype_id:
        prevalence = orch._prior_manager.get_barrier_prevalence(archetype_id)
        result["barrier_prevalence"] = {
            k: round(v, 4) for k, v in prevalence.items() if v > 0
        }

    return result


@router.get("/user/{user_id}/profile")
async def get_user_profile(
    user_id: str,
    brand_id: str = "",
    archetype_id: str = "",
) -> Dict[str, Any]:
    """Get a user's within-subject posterior profile (Enhancement #36).

    Returns per-mechanism posteriors, trajectory analysis, variance
    components, and mechanism rankings for a specific user. Essential
    for pilot observability and debugging personalization quality.

    Latency target: <50ms (L1 cache hit)
    """
    try:
        from adam.core.dependencies import LearningComponents, Infrastructure
        infra = Infrastructure.get_instance()
        components = LearningComponents.get_instance(infra)
        user_mgr = components.user_posterior_manager

        if user_mgr is None:
            raise HTTPException(
                status_code=503,
                detail="UserPosteriorManager not initialized",
            )

        profile = user_mgr.get_user_profile(
            user_id=user_id,
            brand_id=brand_id,
            archetype_id=archetype_id,
        )

        # Build response with mechanism rankings and trajectory
        mechanism_summary = {}
        for mech_name, posterior in profile.mechanism_posteriors.items():
            mech_data = {
                "alpha": round(posterior.alpha, 2),
                "beta": round(posterior.beta, 2),
                "mean": round(posterior.alpha / (posterior.alpha + posterior.beta), 4),
                "sample_count": posterior.sample_count,
                "success_count": posterior.success_count,
                "outcomes": posterior.outcomes[-10:],  # Last 10 outcomes
            }
            mechanism_summary[mech_name] = mech_data

        # Run trajectory analysis if enough data
        trajectory_results = {}
        if profile.mechanism_posteriors:
            from adam.retargeting.engines.repeated_measures import TrajectoryAnalyzer
            analyzer = TrajectoryAnalyzer()
            all_outcomes = []
            all_mechs = []
            for mech_name, posterior in profile.mechanism_posteriors.items():
                all_outcomes.extend(posterior.outcomes)
                all_mechs.extend([mech_name] * len(posterior.outcomes))
            if len(all_outcomes) >= 3:
                traj = analyzer.analyze(
                    outcomes=all_outcomes,
                    mechanisms=all_mechs,
                    user_id=user_id,
                )
                trajectory_results = {
                    "classification": traj.trajectory_type,
                    "linear_trend": round(traj.linear_trend, 4) if traj.linear_trend else None,
                    "quadratic_trend": round(traj.quadratic_trend, 4) if traj.quadratic_trend else None,
                    "changepoint_position": traj.changepoint_position if hasattr(traj, 'changepoint_position') else None,
                    "ar1_correlation": round(traj.ar1_correlation, 4) if traj.ar1_correlation else None,
                }

        # Mechanism rankings by posterior mean
        rankings = sorted(
            mechanism_summary.items(),
            key=lambda x: x[1]["mean"],
            reverse=True,
        )

        total_touches = sum(m["sample_count"] for m in mechanism_summary.values())

        return {
            "user_id": user_id,
            "brand_id": brand_id,
            "total_touches": total_touches,
            "mechanisms_tried": len(mechanism_summary),
            "mechanism_posteriors": mechanism_summary,
            "mechanism_rankings": [
                {"mechanism": name, "mean": data["mean"], "n": data["sample_count"]}
                for name, data in rankings
            ],
            "trajectory": trajectory_results or None,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def retargeting_health() -> Dict[str, Any]:
    """Health check for the retargeting engine."""
    try:
        orch = _get_orchestrator()
        stats = orch._prior_manager.stats

        # Include within-subject stats if available
        user_mgr_stats = {}
        try:
            from adam.core.dependencies import LearningComponents, Infrastructure
            infra = Infrastructure.get_instance()
            components = LearningComponents.get_instance(infra)
            if components.user_posterior_manager is not None:
                user_mgr = components.user_posterior_manager
                user_mgr_stats = {
                    "users_tracked": len(user_mgr._profiles),
                    "l1_cache_capacity": f"{len(user_mgr._profiles)}/{user_mgr._profiles.maxlen if hasattr(user_mgr._profiles, 'maxlen') else 'unlimited'}",
                }
                if components.mixed_effects_estimator is not None:
                    me = components.mixed_effects_estimator
                    if hasattr(me, 'icc') and me.icc is not None:
                        user_mgr_stats["icc"] = round(me.icc, 4)
                        user_mgr_stats["design_effect"] = round(me.design_effect, 4)
        except Exception:
            pass

        return {
            "status": "healthy",
            "engine": "therapeutic_retargeting",
            "version": "36.0",
            "prior_stats": stats,
            "active_sequences": len(orch._sequences),
            "within_subject": user_mgr_stats or None,
        }
    except Exception as e:
        return {
            "status": "degraded",
            "error": str(e),
        }
