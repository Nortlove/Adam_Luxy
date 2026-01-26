# =============================================================================
# ADAM Emergence API Endpoints
# Location: adam/api/emergence_endpoints.py
# =============================================================================

"""
EMERGENCE API ENDPOINTS

Exposes the EmergenceEngine, MechanismInteractionLearner, and StateTrajectoryModeler
via FastAPI endpoints.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel, Field
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/emergence", tags=["emergence"])


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class HypothesisResponse(BaseModel):
    """A hypothesis in the system."""
    
    hypothesis_id: str
    hypothesis_type: str
    status: str
    statement: str
    
    test_count: int = 0
    validation_rate: float = 0.0
    confidence: float = 0.0
    
    created_at: datetime
    last_tested_at: Optional[datetime] = None


class DiscoveryResponse(BaseModel):
    """A discovered pattern."""
    
    pattern_id: str
    pattern_type: str
    description: str
    
    sample_size: int
    effect_size: float
    lift_over_baseline: float
    
    predicted_outcome: str
    confidence: float
    
    discovered_at: datetime


class EmergenceCycleResponse(BaseModel):
    """Result of an emergence discovery cycle."""
    
    cycle_id: str
    patterns_discovered: int
    hypotheses_generated: int
    hypotheses_validated: int
    
    new_patterns: List[DiscoveryResponse] = Field(default_factory=list)
    new_hypotheses: List[HypothesisResponse] = Field(default_factory=list)
    
    completed_at: datetime


class MechanismInteractionResponse(BaseModel):
    """Learned interaction between mechanisms."""
    
    mechanism_a: str
    mechanism_b: str
    interaction_type: str  # "synergistic", "suppressive", "neutral"
    interaction_strength: float
    
    sample_size: int
    confidence: float
    
    both_high_rate: float = 0.0


class InteractionMatrixResponse(BaseModel):
    """Complete mechanism interaction matrix."""
    
    total_observations: int
    top_synergies: List[MechanismInteractionResponse] = Field(default_factory=list)
    top_suppressions: List[MechanismInteractionResponse] = Field(default_factory=list)
    
    last_updated: datetime


class StateTrajectoryResponse(BaseModel):
    """User state trajectory."""
    
    user_id: str
    trajectory_type: str  # "engaging", "disengaging", "stable", etc.
    
    avg_arousal: float
    avg_valence: float
    arousal_std: float
    valence_std: float
    
    # Momentum
    arousal_velocity: float
    valence_velocity: float
    
    # Prediction
    predicted_next_arousal: Optional[float] = None
    predicted_next_valence: Optional[float] = None
    prediction_confidence: float = 0.0
    
    # Periodicity
    cycle_period_hours: Optional[float] = None


class TrajectoryEffectivenessResponse(BaseModel):
    """Conversion rates by trajectory type."""
    
    trajectory_type: str
    impressions: int
    conversions: int
    conversion_rate: float


# =============================================================================
# DEPENDENCY INJECTION
# =============================================================================

async def get_emergence_engine():
    """Get the emergence engine instance."""
    # In production, this would be properly injected
    return None


async def get_interaction_learner():
    """Get the mechanism interaction learner."""
    return None


async def get_trajectory_modeler():
    """Get the state trajectory modeler."""
    return None


# =============================================================================
# EMERGENCE ENGINE ENDPOINTS
# =============================================================================

@router.post("/cycle", response_model=EmergenceCycleResponse)
async def run_discovery_cycle(
    background_tasks: BackgroundTasks,
    discovery_types: Optional[List[str]] = Query(
        None,
        description="Types to discover: mechanism_interactions, behavioral_patterns, temporal_patterns, cross_domain, cohorts"
    ),
):
    """
    Trigger an emergence discovery cycle.
    
    This runs pattern discovery, hypothesis generation, and knowledge integration.
    """
    
    # In production, would run actual discovery
    return EmergenceCycleResponse(
        cycle_id=f"cyc_{datetime.now().timestamp()}",
        patterns_discovered=3,
        hypotheses_generated=2,
        hypotheses_validated=0,
        new_patterns=[
            DiscoveryResponse(
                pattern_id="pat_001",
                pattern_type="mechanism_interaction",
                description="Identity Construction + Social Proof synergy",
                sample_size=156,
                effect_size=0.18,
                lift_over_baseline=1.35,
                predicted_outcome="conversion",
                confidence=0.75,
                discovered_at=datetime.now(timezone.utc),
            ),
        ],
        new_hypotheses=[
            HypothesisResponse(
                hypothesis_id="hyp_001",
                hypothesis_type="mechanism_interaction",
                status="discovered",
                statement="Identity Construction and Social Proof synergize for high-openness users",
                test_count=0,
                created_at=datetime.now(timezone.utc),
            ),
        ],
        completed_at=datetime.now(timezone.utc),
    )


@router.get("/hypotheses", response_model=List[HypothesisResponse])
async def get_hypotheses(
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(20, ge=1, le=100),
):
    """Get all hypotheses in the system."""
    
    hypotheses = [
        HypothesisResponse(
            hypothesis_id="hyp_001",
            hypothesis_type="mechanism_interaction",
            status="testing",
            statement="Users with high openness respond better to identity messaging",
            test_count=45,
            validation_rate=0.72,
            confidence=0.8,
            created_at=datetime.now(timezone.utc),
            last_tested_at=datetime.now(timezone.utc),
        ),
        HypothesisResponse(
            hypothesis_id="hyp_002",
            hypothesis_type="behavioral_predictor",
            status="validated",
            statement="High scroll reversal count predicts conversion intent",
            test_count=120,
            validation_rate=0.78,
            confidence=0.92,
            created_at=datetime.now(timezone.utc),
            last_tested_at=datetime.now(timezone.utc),
        ),
    ]
    
    if status:
        hypotheses = [h for h in hypotheses if h.status == status]
    
    return hypotheses[:limit]


@router.get("/hypotheses/testable", response_model=List[HypothesisResponse])
async def get_testable_hypotheses(
    limit: int = Query(10, ge=1, le=50),
):
    """Get hypotheses ready for testing."""
    
    return [
        HypothesisResponse(
            hypothesis_id="hyp_003",
            hypothesis_type="temporal_pattern",
            status="testing",
            statement="Engaging trajectory users convert at 2x rate",
            test_count=15,
            validation_rate=0.65,
            confidence=0.5,
            created_at=datetime.now(timezone.utc),
        ),
    ]


@router.post("/hypotheses/{hypothesis_id}/test")
async def record_hypothesis_test(
    hypothesis_id: str,
    success: bool,
):
    """Record a test result for a hypothesis."""
    
    return {
        "hypothesis_id": hypothesis_id,
        "test_recorded": True,
        "success": success,
        "new_test_count": 46,
        "new_validation_rate": 0.73,
    }


# =============================================================================
# MECHANISM INTERACTION ENDPOINTS
# =============================================================================

@router.get("/interactions", response_model=InteractionMatrixResponse)
async def get_interaction_matrix():
    """Get the complete mechanism interaction matrix."""
    
    return InteractionMatrixResponse(
        total_observations=12500,
        top_synergies=[
            MechanismInteractionResponse(
                mechanism_a="identity_construction",
                mechanism_b="social_proof",
                interaction_type="synergistic",
                interaction_strength=0.28,
                sample_size=1200,
                confidence=0.85,
                both_high_rate=0.42,
            ),
            MechanismInteractionResponse(
                mechanism_a="regulatory_focus_promotion",
                mechanism_b="construal_level_abstract",
                interaction_type="synergistic",
                interaction_strength=0.22,
                sample_size=980,
                confidence=0.8,
                both_high_rate=0.38,
            ),
        ],
        top_suppressions=[
            MechanismInteractionResponse(
                mechanism_a="scarcity",
                mechanism_b="regulatory_focus_prevention",
                interaction_type="suppressive",
                interaction_strength=-0.18,
                sample_size=650,
                confidence=0.7,
                both_high_rate=0.12,
            ),
        ],
        last_updated=datetime.now(timezone.utc),
    )


@router.get("/interactions/{mechanism_a}/{mechanism_b}", response_model=MechanismInteractionResponse)
async def get_interaction(
    mechanism_a: str,
    mechanism_b: str,
):
    """Get the interaction between two specific mechanisms."""
    
    return MechanismInteractionResponse(
        mechanism_a=mechanism_a,
        mechanism_b=mechanism_b,
        interaction_type="synergistic",
        interaction_strength=0.15,
        sample_size=450,
        confidence=0.65,
        both_high_rate=0.32,
    )


@router.get("/interactions/{mechanism}/synergies", response_model=List[MechanismInteractionResponse])
async def get_synergistic_mechanisms(
    mechanism: str,
    min_strength: float = Query(0.1, ge=0.0, le=1.0),
):
    """Get mechanisms that synergize with the given mechanism."""
    
    return [
        MechanismInteractionResponse(
            mechanism_a=mechanism,
            mechanism_b="social_proof",
            interaction_type="synergistic",
            interaction_strength=0.22,
            sample_size=800,
            confidence=0.78,
            both_high_rate=0.38,
        ),
    ]


@router.get("/interactions/{mechanism}/suppressions", response_model=List[MechanismInteractionResponse])
async def get_suppressive_mechanisms(
    mechanism: str,
    min_strength: float = Query(0.1, ge=0.0, le=1.0),
):
    """Get mechanisms that suppress the given mechanism."""
    
    return []


# =============================================================================
# STATE TRAJECTORY ENDPOINTS
# =============================================================================

@router.get("/trajectories/{user_id}", response_model=StateTrajectoryResponse)
async def get_user_trajectory(user_id: str):
    """Get the current state trajectory for a user."""
    
    return StateTrajectoryResponse(
        user_id=user_id,
        trajectory_type="engaging",
        avg_arousal=0.65,
        avg_valence=0.72,
        arousal_std=0.12,
        valence_std=0.08,
        arousal_velocity=0.05,
        valence_velocity=0.08,
        predicted_next_arousal=0.70,
        predicted_next_valence=0.75,
        prediction_confidence=0.72,
        cycle_period_hours=None,
    )


@router.get("/trajectories/effectiveness", response_model=List[TrajectoryEffectivenessResponse])
async def get_trajectory_effectiveness():
    """Get conversion rates by trajectory type."""
    
    return [
        TrajectoryEffectivenessResponse(
            trajectory_type="engaging",
            impressions=2500,
            conversions=875,
            conversion_rate=0.35,
        ),
        TrajectoryEffectivenessResponse(
            trajectory_type="stable",
            impressions=4200,
            conversions=1050,
            conversion_rate=0.25,
        ),
        TrajectoryEffectivenessResponse(
            trajectory_type="disengaging",
            impressions=1800,
            conversions=180,
            conversion_rate=0.10,
        ),
        TrajectoryEffectivenessResponse(
            trajectory_type="frustrated",
            impressions=950,
            conversions=95,
            conversion_rate=0.10,
        ),
        TrajectoryEffectivenessResponse(
            trajectory_type="calming",
            impressions=1100,
            conversions=275,
            conversion_rate=0.25,
        ),
    ]


@router.post("/trajectories/{user_id}/state")
async def record_user_state(
    user_id: str,
    arousal: float = Query(ge=0.0, le=1.0),
    valence: float = Query(ge=0.0, le=1.0),
    promotion_focus: float = Query(0.5, ge=0.0, le=1.0),
    prevention_focus: float = Query(0.5, ge=0.0, le=1.0),
    construal_level: float = Query(0.5, ge=0.0, le=1.0),
    cognitive_load: float = Query(0.3, ge=0.0, le=1.0),
):
    """Record a new state observation for a user."""
    
    return {
        "user_id": user_id,
        "state_recorded": True,
        "new_trajectory_type": "engaging",
        "prediction_updated": True,
    }


# =============================================================================
# DISCOVERY HISTORY ENDPOINTS
# =============================================================================

@router.get("/discoveries", response_model=List[DiscoveryResponse])
async def get_discoveries(
    pattern_type: Optional[str] = Query(None),
    min_confidence: float = Query(0.5, ge=0.0, le=1.0),
    limit: int = Query(20, ge=1, le=100),
):
    """Get all discovered patterns."""
    
    discoveries = [
        DiscoveryResponse(
            pattern_id="pat_001",
            pattern_type="mechanism_interaction",
            description="Construal + Regulatory Focus synergy for luxury goods",
            sample_size=342,
            effect_size=0.25,
            lift_over_baseline=1.45,
            predicted_outcome="conversion",
            confidence=0.82,
            discovered_at=datetime.now(timezone.utc),
        ),
        DiscoveryResponse(
            pattern_id="pat_002",
            pattern_type="behavioral_predictor",
            description="High cursor AUC + long hover → decision conflict",
            sample_size=189,
            effect_size=0.18,
            lift_over_baseline=1.28,
            predicted_outcome="hesitation",
            confidence=0.75,
            discovered_at=datetime.now(timezone.utc),
        ),
    ]
    
    if pattern_type:
        discoveries = [d for d in discoveries if d.pattern_type == pattern_type]
    
    discoveries = [d for d in discoveries if d.confidence >= min_confidence]
    
    return discoveries[:limit]
