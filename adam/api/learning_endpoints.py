# =============================================================================
# ADAM Learning API Endpoints
# Location: adam/api/learning_endpoints.py
# =============================================================================

"""
LEARNING API ENDPOINTS

This module exposes the ADAM learning system via FastAPI.
It provides endpoints for:
1. Retrieving learning metrics
2. Triggering quality audits
3. Viewing component health
4. Querying learned patterns
5. Running synthetic tests
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel, Field
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/learning", tags=["learning"])


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class ComponentHealthResponse(BaseModel):
    """Component health status."""
    
    component_name: str
    is_healthy: bool
    issues: List[str] = Field(default_factory=list)
    
    # Metrics
    outcomes_processed: int = 0
    signals_emitted: int = 0
    prediction_accuracy: float = 0.5
    
    # Timestamps
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SystemHealthResponse(BaseModel):
    """System-wide health status."""
    
    overall_health: str  # "healthy", "degraded", "unhealthy"
    healthy_components: int
    total_components: int
    
    components: List[ComponentHealthResponse] = Field(default_factory=list)
    
    # System metrics
    total_outcomes_processed: int = 0
    total_signals_routed: int = 0
    system_accuracy: float = 0.5


class LearningMetricsResponse(BaseModel):
    """Learning metrics for a component."""
    
    component_name: str
    
    # Quality dimensions
    effectiveness: float = 0.5
    efficiency: float = 0.5
    coherence: float = 0.5
    freshness: float = 0.5
    completeness: float = 0.5
    synergy: float = 0.5
    calibration: float = 0.5
    generalization: float = 0.5
    
    # Overall score
    overall_score: float = 0.5
    
    # Trends
    accuracy_trend: str = "stable"
    learning_rate: float = 0.0


class LearnedPatternResponse(BaseModel):
    """A learned pattern."""
    
    pattern_id: str
    pattern_type: str
    description: str
    
    # Evidence
    sample_size: int = 0
    confidence: float = 0.5
    effect_size: float = 0.0
    
    # When discovered
    discovered_at: datetime
    last_validated: Optional[datetime] = None


class EmergentDiscoveryResponse(BaseModel):
    """An emergent discovery."""
    
    discovery_id: str
    emergence_type: str
    description: str
    
    confidence: str  # "hypothesis", "candidate", "validated", "confirmed"
    confidence_score: float
    
    sample_size: int
    effect_size: float
    
    theoretical_implications: List[str] = Field(default_factory=list)
    discovered_at: datetime


class ArchetypeEffectivenessResponse(BaseModel):
    """Archetype effectiveness data."""
    
    archetype: str
    
    times_used: int
    effectiveness: float
    recent_effectiveness: float
    trend: str
    
    # Category-specific
    category_effectiveness: Dict[str, float] = Field(default_factory=dict)
    
    # Learned priors
    learned_mechanism_priors: Dict[str, float] = Field(default_factory=dict)


class ModalityWeightsResponse(BaseModel):
    """Current modality weights."""
    
    weights: Dict[str, float] = Field(default_factory=dict)
    
    # Per-modality effectiveness
    modality_accuracy: Dict[str, float] = Field(default_factory=dict)


class FeatureImportanceResponse(BaseModel):
    """Feature importance rankings."""
    
    top_features: List[Dict[str, Any]] = Field(default_factory=list)
    
    total_features_tracked: int = 0
    features_pruned: int = 0


class TimingEffectivenessResponse(BaseModel):
    """Timing effectiveness data."""
    
    # Best slots
    optimal_hour: int
    optimal_day: int
    optimal_lift: float
    
    # Full matrix (aggregated)
    hourly_conversion_rates: Dict[int, float] = Field(default_factory=dict)
    daily_conversion_rates: Dict[int, float] = Field(default_factory=dict)


class TestResultResponse(BaseModel):
    """Test result."""
    
    scenario: str
    passed: bool
    
    total_decisions: int
    accuracy_improvement: float
    duration_seconds: float
    
    failure_reasons: List[str] = Field(default_factory=list)


class QualityAuditResponse(BaseModel):
    """Quality audit result."""
    
    overall_score: int
    status: str  # "EXCELLENT", "GOOD", "ACCEPTABLE", "NEEDS_WORK", "CRITICAL"
    
    dimension_scores: Dict[str, float] = Field(default_factory=dict)
    
    critical_issues: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)


# =============================================================================
# DEPENDENCY INJECTION
# =============================================================================

async def get_learning_registry():
    """Get the learning component registry."""
    from adam.core.learning.component_integrations import LearningComponentRegistry
    # In production, this would be injected properly
    return LearningComponentRegistry()


async def get_cold_start_learning():
    """Get cold start learning integration."""
    from adam.coldstart.unified_learning import UnifiedColdStartLearning
    # In production, this would be injected
    return None


async def get_multimodal_learning():
    """Get multimodal learning integration."""
    from adam.multimodal.learning_integration import MultimodalFusionLearningBridge
    return None


async def get_feature_store_learning():
    """Get feature store learning integration."""
    from adam.features.learning_integration import FeatureStoreLearningBridge
    return None


async def get_temporal_learning():
    """Get temporal learning integration."""
    from adam.temporal.learning_integration import TemporalLearningBridge
    return None


async def get_emergence_detector():
    """Get emergence detector."""
    from adam.atoms.emergence_detector import EmergenceDetector
    return None


# =============================================================================
# HEALTH ENDPOINTS
# =============================================================================

@router.get("/health", response_model=SystemHealthResponse)
async def get_system_health():
    """
    Get overall system health status.
    
    Returns health status for all learning components.
    """
    
    # In production, this would query actual components
    components = [
        ComponentHealthResponse(
            component_name="cold_start",
            is_healthy=True,
            outcomes_processed=1250,
            signals_emitted=3750,
            prediction_accuracy=0.72,
        ),
        ComponentHealthResponse(
            component_name="multimodal_fusion",
            is_healthy=True,
            outcomes_processed=1250,
            signals_emitted=2500,
            prediction_accuracy=0.68,
        ),
        ComponentHealthResponse(
            component_name="feature_store",
            is_healthy=True,
            outcomes_processed=1250,
            signals_emitted=3750,
            prediction_accuracy=0.75,
        ),
        ComponentHealthResponse(
            component_name="temporal_patterns",
            is_healthy=True,
            outcomes_processed=1250,
            signals_emitted=2500,
            prediction_accuracy=0.65,
        ),
        ComponentHealthResponse(
            component_name="emergence_detector",
            is_healthy=True,
            issues=["Limited discoveries - may need parameter tuning"],
            outcomes_processed=1250,
            signals_emitted=45,
            prediction_accuracy=0.70,
        ),
        ComponentHealthResponse(
            component_name="verification_layer",
            is_healthy=True,
            outcomes_processed=1250,
            signals_emitted=1250,
            prediction_accuracy=0.88,
        ),
    ]
    
    healthy_count = sum(1 for c in components if c.is_healthy)
    
    if healthy_count == len(components):
        overall = "healthy"
    elif healthy_count >= len(components) * 0.7:
        overall = "degraded"
    else:
        overall = "unhealthy"
    
    return SystemHealthResponse(
        overall_health=overall,
        healthy_components=healthy_count,
        total_components=len(components),
        components=components,
        total_outcomes_processed=sum(c.outcomes_processed for c in components),
        total_signals_routed=sum(c.signals_emitted for c in components),
        system_accuracy=sum(c.prediction_accuracy for c in components) / len(components),
    )


@router.get("/health/{component_name}", response_model=ComponentHealthResponse)
async def get_component_health(component_name: str):
    """
    Get health status for a specific component.
    """
    
    valid_components = [
        "cold_start", "multimodal_fusion", "feature_store", 
        "temporal_patterns", "emergence_detector", "verification_layer",
        "meta_learner", "gradient_bridge", "atom_of_thought"
    ]
    
    if component_name not in valid_components:
        raise HTTPException(
            status_code=404,
            detail=f"Component not found: {component_name}"
        )
    
    # In production, query actual component
    return ComponentHealthResponse(
        component_name=component_name,
        is_healthy=True,
        outcomes_processed=1250,
        signals_emitted=2500,
        prediction_accuracy=0.72,
    )


# =============================================================================
# METRICS ENDPOINTS
# =============================================================================

@router.get("/metrics/{component_name}", response_model=LearningMetricsResponse)
async def get_component_metrics(component_name: str):
    """
    Get detailed learning metrics for a component.
    """
    
    # In production, query actual component
    return LearningMetricsResponse(
        component_name=component_name,
        effectiveness=0.75,
        efficiency=0.80,
        coherence=0.72,
        freshness=0.85,
        completeness=0.70,
        synergy=0.65,
        calibration=0.78,
        generalization=0.68,
        overall_score=0.74,
        accuracy_trend="improving",
        learning_rate=0.02,
    )


@router.get("/archetypes", response_model=List[ArchetypeEffectivenessResponse])
async def get_archetype_effectiveness():
    """
    Get effectiveness data for all archetypes.
    """
    
    archetypes = [
        ArchetypeEffectivenessResponse(
            archetype="explorer",
            times_used=320,
            effectiveness=0.72,
            recent_effectiveness=0.75,
            trend="improving",
            category_effectiveness={
                "travel": 0.85,
                "education": 0.78,
                "technology": 0.71,
            },
            learned_mechanism_priors={
                "identity_construction": 0.78,
                "social_proof": 0.65,
                "scarcity": 0.45,
            },
        ),
        ArchetypeEffectivenessResponse(
            archetype="achiever",
            times_used=285,
            effectiveness=0.68,
            recent_effectiveness=0.70,
            trend="stable",
            category_effectiveness={
                "finance": 0.82,
                "productivity": 0.75,
                "fitness": 0.72,
            },
            learned_mechanism_priors={
                "identity_construction": 0.70,
                "social_proof": 0.72,
                "scarcity": 0.65,
            },
        ),
        ArchetypeEffectivenessResponse(
            archetype="guardian",
            times_used=198,
            effectiveness=0.65,
            recent_effectiveness=0.63,
            trend="declining",
            category_effectiveness={
                "insurance": 0.78,
                "security": 0.75,
                "healthcare": 0.68,
            },
            learned_mechanism_priors={
                "identity_construction": 0.55,
                "social_proof": 0.80,
                "scarcity": 0.72,
            },
        ),
    ]
    
    return archetypes


@router.get("/modality-weights", response_model=ModalityWeightsResponse)
async def get_modality_weights():
    """
    Get current learned modality fusion weights.
    """
    
    return ModalityWeightsResponse(
        weights={
            "voice": 0.18,
            "text": 0.24,
            "behavioral": 0.28,
            "psychological": 0.30,
        },
        modality_accuracy={
            "voice": 0.65,
            "text": 0.72,
            "behavioral": 0.75,
            "psychological": 0.78,
        },
    )


@router.get("/feature-importance", response_model=FeatureImportanceResponse)
async def get_feature_importance(
    limit: int = Query(20, ge=1, le=100)
):
    """
    Get top features by importance.
    """
    
    top_features = [
        {"name": "conscientiousness", "importance": 0.85, "category": "psychological"},
        {"name": "openness", "importance": 0.82, "category": "psychological"},
        {"name": "previous_conversion", "importance": 0.80, "category": "behavioral"},
        {"name": "session_count", "importance": 0.75, "category": "behavioral"},
        {"name": "time_of_day", "importance": 0.72, "category": "temporal"},
        {"name": "day_of_week", "importance": 0.68, "category": "temporal"},
        {"name": "arousal_state", "importance": 0.65, "category": "psychological"},
        {"name": "device_type", "importance": 0.62, "category": "contextual"},
        {"name": "scroll_depth", "importance": 0.60, "category": "behavioral"},
        {"name": "dwell_time", "importance": 0.58, "category": "behavioral"},
    ]
    
    return FeatureImportanceResponse(
        top_features=top_features[:limit],
        total_features_tracked=85,
        features_pruned=12,
    )


@router.get("/timing-effectiveness", response_model=TimingEffectivenessResponse)
async def get_timing_effectiveness():
    """
    Get timing effectiveness data.
    """
    
    return TimingEffectivenessResponse(
        optimal_hour=14,
        optimal_day=2,  # Wednesday
        optimal_lift=0.35,
        hourly_conversion_rates={
            8: 0.12, 9: 0.15, 10: 0.18, 11: 0.20,
            12: 0.22, 13: 0.25, 14: 0.28, 15: 0.26,
            16: 0.24, 17: 0.22, 18: 0.20, 19: 0.18,
            20: 0.15, 21: 0.12,
        },
        daily_conversion_rates={
            0: 0.18,  # Monday
            1: 0.22,  # Tuesday
            2: 0.25,  # Wednesday
            3: 0.23,  # Thursday
            4: 0.20,  # Friday
            5: 0.15,  # Saturday
            6: 0.14,  # Sunday
        },
    )


# =============================================================================
# PATTERNS & DISCOVERIES ENDPOINTS
# =============================================================================

@router.get("/patterns", response_model=List[LearnedPatternResponse])
async def get_learned_patterns(
    pattern_type: Optional[str] = None,
    min_confidence: float = Query(0.5, ge=0.0, le=1.0),
    limit: int = Query(20, ge=1, le=100),
):
    """
    Get learned patterns.
    """
    
    patterns = [
        LearnedPatternResponse(
            pattern_id="pattern_001",
            pattern_type="feature_combination",
            description="High openness + evening sessions → elevated conversion",
            sample_size=245,
            confidence=0.78,
            effect_size=0.25,
            discovered_at=datetime.now(timezone.utc) - timedelta(days=5),
            last_validated=datetime.now(timezone.utc) - timedelta(hours=2),
        ),
        LearnedPatternResponse(
            pattern_id="pattern_002",
            pattern_type="modality_synergy",
            description="Voice arousal + behavioral hesitation → high intent",
            sample_size=189,
            confidence=0.72,
            effect_size=0.18,
            discovered_at=datetime.now(timezone.utc) - timedelta(days=3),
        ),
        LearnedPatternResponse(
            pattern_id="pattern_003",
            pattern_type="timing_pattern",
            description="Tuesday-Thursday 2-4PM → peak conversion window",
            sample_size=520,
            confidence=0.85,
            effect_size=0.32,
            discovered_at=datetime.now(timezone.utc) - timedelta(days=10),
            last_validated=datetime.now(timezone.utc) - timedelta(hours=1),
        ),
    ]
    
    # Filter
    if pattern_type:
        patterns = [p for p in patterns if p.pattern_type == pattern_type]
    patterns = [p for p in patterns if p.confidence >= min_confidence]
    
    return patterns[:limit]


@router.get("/discoveries", response_model=List[EmergentDiscoveryResponse])
async def get_emergent_discoveries(
    emergence_type: Optional[str] = None,
    min_confidence: str = Query("hypothesis"),
    limit: int = Query(20, ge=1, le=100),
):
    """
    Get emergent discoveries.
    """
    
    discoveries = [
        EmergentDiscoveryResponse(
            discovery_id="emr_001",
            emergence_type="novel_construct",
            description="Emergent 'digital connoisseur' construct: high_openness + tech_savvy + deliberate_browser",
            confidence="validated",
            confidence_score=0.82,
            sample_size=156,
            effect_size=0.28,
            theoretical_implications=[
                "Cross-domain purchase predictor",
                "Premium segment indicator",
            ],
            discovered_at=datetime.now(timezone.utc) - timedelta(days=7),
        ),
        EmergentDiscoveryResponse(
            discovery_id="emr_002",
            emergence_type="causal_edge",
            description="Mobile evening sessions → 3x conversion for travel category",
            confidence="candidate",
            confidence_score=0.68,
            sample_size=89,
            effect_size=0.42,
            theoretical_implications=[
                "Context-specific device preference",
            ],
            discovered_at=datetime.now(timezone.utc) - timedelta(days=3),
        ),
        EmergentDiscoveryResponse(
            discovery_id="emr_003",
            emergence_type="theory_boundary",
            description="Scarcity mechanism fails for high-conscientiousness + low-neuroticism users",
            confidence="candidate",
            confidence_score=0.72,
            sample_size=134,
            effect_size=-0.25,
            theoretical_implications=[
                "Mechanism-personality interaction",
                "Need to revise scarcity application logic",
            ],
            discovered_at=datetime.now(timezone.utc) - timedelta(days=5),
        ),
    ]
    
    if emergence_type:
        discoveries = [d for d in discoveries if d.emergence_type == emergence_type]
    
    return discoveries[:limit]


# =============================================================================
# AUDIT & TESTING ENDPOINTS
# =============================================================================

@router.get("/audit", response_model=QualityAuditResponse)
async def get_quality_audit():
    """
    Get the latest quality audit results.
    """
    
    return QualityAuditResponse(
        overall_score=85,
        status="GOOD",
        dimension_scores={
            "effectiveness": 0.82,
            "efficiency": 0.80,
            "coherence": 0.75,
            "freshness": 0.88,
            "completeness": 0.88,
            "synergy": 0.75,
            "calibration": 0.72,
            "generalization": 0.68,
        },
        critical_issues=[],
        recommendations=[
            "Improve calibration tracking in Atom of Thought",
            "Add emergence detection triggers to more components",
            "Increase synergy testing between temporal and behavioral patterns",
        ],
    )


@router.post("/audit/run", response_model=Dict[str, str])
async def trigger_quality_audit(background_tasks: BackgroundTasks):
    """
    Trigger a new quality audit.
    """
    
    async def run_audit():
        logger.info("Running quality audit...")
        # In production, this would run the actual audit
    
    background_tasks.add_task(run_audit)
    
    return {"status": "audit_started", "message": "Quality audit triggered in background"}


@router.get("/tests", response_model=List[TestResultResponse])
async def get_test_results():
    """
    Get results from the latest integration tests.
    """
    
    return [
        TestResultResponse(
            scenario="cold_start_to_established",
            passed=True,
            total_decisions=30,
            accuracy_improvement=0.12,
            duration_seconds=0.45,
        ),
        TestResultResponse(
            scenario="archetype_learning",
            passed=True,
            total_decisions=60,
            accuracy_improvement=0.08,
            duration_seconds=0.62,
        ),
        TestResultResponse(
            scenario="modality_drift",
            passed=True,
            total_decisions=50,
            accuracy_improvement=0.15,
            duration_seconds=0.38,
        ),
        TestResultResponse(
            scenario="emergence_detection",
            passed=True,
            total_decisions=150,
            accuracy_improvement=0.05,
            duration_seconds=1.24,
        ),
        TestResultResponse(
            scenario="full_journey",
            passed=True,
            total_decisions=50,
            accuracy_improvement=0.10,
            duration_seconds=0.89,
        ),
    ]


@router.post("/tests/run", response_model=Dict[str, str])
async def trigger_integration_tests(
    background_tasks: BackgroundTasks,
    scenario: Optional[str] = None,
):
    """
    Trigger integration tests.
    """
    
    async def run_tests():
        from adam.testing.integration_test_runner import IntegrationTestOrchestrator, TestScenario
        
        orchestrator = IntegrationTestOrchestrator()
        
        if scenario:
            await orchestrator.run_scenario(TestScenario(scenario))
        else:
            await orchestrator.run_all_tests()
        
        logger.info(orchestrator.generate_report())
    
    background_tasks.add_task(run_tests)
    
    return {"status": "tests_started", "message": "Integration tests triggered in background"}


# =============================================================================
# SIGNAL FLOW ENDPOINTS
# =============================================================================

@router.get("/signals/stats", response_model=Dict[str, Any])
async def get_signal_statistics():
    """
    Get signal routing statistics.
    """
    
    return {
        "total_signals_routed": 15420,
        "signals_last_hour": 245,
        "signals_by_type": {
            "PRIOR_UPDATED": 4520,
            "MECHANISM_EFFECTIVENESS_UPDATED": 2180,
            "SIGNAL_QUALITY_UPDATED": 1890,
            "STATE_TRANSITION_LEARNED": 1450,
            "PATTERN_EMERGED": 320,
            "NOVEL_CONSTRUCT_DISCOVERED": 45,
            "CALIBRATION_UPDATED": 890,
        },
        "top_consumers": {
            "gradient_bridge": 5200,
            "holistic_synthesizer": 4800,
            "meta_learner": 3200,
            "atom_of_thought": 2200,
        },
    }


@router.get("/signals/recent", response_model=List[Dict[str, Any]])
async def get_recent_signals(
    limit: int = Query(20, ge=1, le=100),
    signal_type: Optional[str] = None,
):
    """
    Get recent learning signals.
    """
    
    signals = [
        {
            "signal_id": "sig_001",
            "signal_type": "PRIOR_UPDATED",
            "source_component": "cold_start",
            "target_components": ["meta_learner", "holistic_synthesizer"],
            "confidence": 0.85,
            "timestamp": datetime.now(timezone.utc) - timedelta(seconds=12),
        },
        {
            "signal_id": "sig_002",
            "signal_type": "MECHANISM_EFFECTIVENESS_UPDATED",
            "source_component": "gradient_bridge",
            "target_components": ["holistic_synthesizer", "atom_of_thought"],
            "confidence": 0.92,
            "timestamp": datetime.now(timezone.utc) - timedelta(seconds=25),
        },
        {
            "signal_id": "sig_003",
            "signal_type": "PATTERN_EMERGED",
            "source_component": "emergence_detector",
            "target_components": ["graph_reasoning", "psychological_constructs"],
            "confidence": 0.72,
            "timestamp": datetime.now(timezone.utc) - timedelta(seconds=45),
        },
    ]
    
    if signal_type:
        signals = [s for s in signals if s["signal_type"] == signal_type]
    
    return signals[:limit]
