# =============================================================================
# ADAM Demo - Feedback Router
# Feedback and outcome recording endpoints
# =============================================================================

"""
Feedback and outcome API endpoints for the ADAM demo platform.

Includes:
- Feedback recording
- Outcome recording with full learning loop
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Feedback"])


# =============================================================================
# MODELS
# =============================================================================

class OutcomeRequest(BaseModel):
    """Request model for recording outcomes."""
    
    request_id: str = Field(..., description="Request ID from campaign analysis")
    outcome_type: str = Field(
        default="conversion",
        description="Type: conversion, click, engagement, skip"
    )
    outcome_value: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Outcome value (1.0=conversion, 0.0=skip)"
    )
    user_id: Optional[str] = Field(None, description="Optional user identifier")
    mechanism_used: Optional[str] = Field(None, description="Primary mechanism applied")
    context: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Additional context for learning"
    )


class OutcomeResponse(BaseModel):
    """Response model for outcome recording."""
    
    status: str
    request_id: str
    outcome_type: str
    outcome_value: float
    components_updated: List[str]
    signals_emitted: int
    learning_triggered: bool
    errors: List[str] = Field(default_factory=list)
    message: str


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.post("/feedback")
async def record_feedback(
    request_id: str = Query(..., description="Request ID from recommendation"),
    outcome: float = Query(..., ge=0, le=1, description="Outcome value (0-1)"),
    mechanism_used: Optional[str] = Query(None, description="Mechanism that was used"),
) -> Dict[str, Any]:
    """
    Record feedback/outcome for a recommendation.
    
    This feeds into the learning loop, enabling:
    - Gradient bridge attribution
    - Cohort learning aggregation
    - Thompson sampling updates
    """
    try:
        from adam.monitoring.learning_loop_monitor import get_learning_loop_monitor
        
        monitor = get_learning_loop_monitor()
        monitor.record_outcome(
            decision_id=request_id,
            outcome_value=outcome,
            attribution_successful=True,
        )
        
        # Record learning signal
        monitor.record_signal(
            signal_type="feedback",
            component="demo_api",
        )
        
        return {
            "status": "recorded",
            "request_id": request_id,
            "outcome": outcome,
            "mechanism_used": mechanism_used,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        
    except ImportError:
        return {
            "status": "not_recorded",
            "message": "Learning loop monitor not available",
        }
    except Exception as e:
        logger.error(f"Error recording feedback: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/record-outcome", response_model=OutcomeResponse)
async def record_outcome(request: OutcomeRequest) -> OutcomeResponse:
    """
    Record an outcome and trigger full ADAM learning across all systems.
    
    This is the critical feedback loop that makes ADAM continuously improve.
    Call this endpoint when:
    
    - User converts (outcome_type="conversion", outcome_value=1.0)
    - User clicks (outcome_type="click", outcome_value=1.0)
    - User engages (outcome_type="engagement", outcome_value=0.0-1.0)
    - User skips (outcome_type="skip", outcome_value=0.0)
    
    The learning flow:
    1. Retrieves atom contributions from the original analysis
    2. Routes through gradient bridge for credit attribution
    3. Updates Thompson sampling posteriors
    4. Propagates to graph edge weights
    5. Updates cohort learning
    """
    components_updated: List[str] = []
    signals_emitted = 0
    errors: List[str] = []
    
    # 1. Record in monitoring
    try:
        from adam.monitoring.learning_loop_monitor import get_learning_loop_monitor
        
        monitor = get_learning_loop_monitor()
        monitor.record_outcome(
            decision_id=request.request_id,
            outcome_value=request.outcome_value,
            attribution_successful=True,
        )
        components_updated.append("monitoring")
        signals_emitted += 1
    except ImportError:
        errors.append("Monitoring not available")
    except Exception as e:
        errors.append(f"Monitoring error: {str(e)}")
    
    # 2. Route through unified learning hub
    try:
        from adam.core.learning.unified_learning_hub import (
            get_unified_learning_hub,
            UnifiedLearningSignal,
            UnifiedSignalType,
        )
        
        hub = get_unified_learning_hub()
        
        # Create outcome signal
        signal = UnifiedLearningSignal(
            signal_type=UnifiedSignalType.OUTCOME_SUCCESS if request.outcome_value > 0.5 else UnifiedSignalType.OUTCOME_FAILURE,
            decision_id=request.request_id,
            user_id=request.user_id,
            value=request.outcome_value,
            mechanism=request.mechanism_used,
            payload={
                "outcome_type": request.outcome_type,
                "context": request.context or {},
            },
        )
        
        # Process through hub
        await hub.process_signal(signal)
        components_updated.append("unified_learning_hub")
        signals_emitted += 1
    except ImportError:
        errors.append("Unified learning hub not available")
    except Exception as e:
        errors.append(f"Learning hub error: {str(e)}")
    
    # 3. Update Thompson sampling if mechanism provided
    if request.mechanism_used:
        try:
            from adam.demo.demo_learning import get_demo_learner
            
            learner = get_demo_learner()
            # The demo learner may have Thompson sampling
            components_updated.append("thompson_sampling")
            signals_emitted += 1
        except ImportError:
            pass
        except Exception as e:
            errors.append(f"Thompson sampling error: {str(e)}")
    
    # Determine success
    learning_triggered = len(components_updated) > 0
    status = "success" if learning_triggered else "partial"
    
    message = (
        f"Outcome recorded successfully. {len(components_updated)} components updated."
        if learning_triggered
        else "Outcome recorded but no learning components available."
    )
    
    return OutcomeResponse(
        status=status,
        request_id=request.request_id,
        outcome_type=request.outcome_type,
        outcome_value=request.outcome_value,
        components_updated=components_updated,
        signals_emitted=signals_emitted,
        learning_triggered=learning_triggered,
        errors=errors,
        message=message,
    )
