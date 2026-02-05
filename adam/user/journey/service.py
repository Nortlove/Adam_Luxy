# =============================================================================
# ADAM Journey Tracking Service
# Location: adam/user/journey/service.py
# =============================================================================

"""
JOURNEY TRACKING SERVICE

Track and predict user journey states.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
from uuid import uuid4

from adam.user.journey.models import (
    JourneyStage,
    DecisionUrgency,
    JourneyState,
    JourneyTransition,
    UserJourney,
)
from adam.infrastructure.redis import ADAMRedisCache

logger = logging.getLogger(__name__)


# =============================================================================
# STAGE TRANSITION MATRIX
# =============================================================================

# Valid transitions and their typical triggers
VALID_TRANSITIONS = {
    JourneyStage.UNAWARE: [JourneyStage.AWARE],
    JourneyStage.AWARE: [JourneyStage.CONSIDERING, JourneyStage.UNAWARE],
    JourneyStage.CONSIDERING: [
        JourneyStage.RESEARCHING, JourneyStage.AWARE, JourneyStage.READY_TO_BUY
    ],
    JourneyStage.RESEARCHING: [
        JourneyStage.COMPARING, JourneyStage.CONSIDERING, JourneyStage.READY_TO_BUY
    ],
    JourneyStage.COMPARING: [
        JourneyStage.READY_TO_BUY, JourneyStage.DECIDING, JourneyStage.RESEARCHING
    ],
    JourneyStage.READY_TO_BUY: [
        JourneyStage.DECIDING, JourneyStage.PURCHASING, JourneyStage.COMPARING
    ],
    JourneyStage.DECIDING: [
        JourneyStage.PURCHASING, JourneyStage.COMPARING
    ],
    JourneyStage.PURCHASING: [JourneyStage.PURCHASED],
    JourneyStage.PURCHASED: [JourneyStage.USING],
    JourneyStage.USING: [JourneyStage.EVALUATING, JourneyStage.CHURNING],
    JourneyStage.EVALUATING: [JourneyStage.ADVOCATING, JourneyStage.CHURNING],
    JourneyStage.ADVOCATING: [JourneyStage.CHURNING],
    JourneyStage.CHURNING: [JourneyStage.AWARE],  # Re-engagement
}

# Signals that trigger stage transitions
TRANSITION_SIGNALS = {
    ("product_view", JourneyStage.UNAWARE): JourneyStage.AWARE,
    ("product_view", JourneyStage.AWARE): JourneyStage.CONSIDERING,
    ("category_browse", JourneyStage.CONSIDERING): JourneyStage.RESEARCHING,
    ("compare_products", JourneyStage.RESEARCHING): JourneyStage.COMPARING,
    ("add_to_cart", JourneyStage.COMPARING): JourneyStage.READY_TO_BUY,
    ("checkout_start", JourneyStage.READY_TO_BUY): JourneyStage.DECIDING,
    ("purchase_complete", JourneyStage.DECIDING): JourneyStage.PURCHASED,
    ("product_use", JourneyStage.PURCHASED): JourneyStage.USING,
    ("review_submitted", JourneyStage.USING): JourneyStage.ADVOCATING,
    ("no_activity_30d", JourneyStage.USING): JourneyStage.CHURNING,
}


# =============================================================================
# SERVICE
# =============================================================================

class JourneyTrackingService:
    """
    Service for tracking user journey states.
    """
    
    def __init__(
        self,
        cache: Optional[ADAMRedisCache] = None,
    ):
        self.cache = cache
        
        # In-memory journey storage (production: use Neo4j)
        self._journeys: Dict[str, UserJourney] = {}
    
    async def get_journey(
        self,
        user_id: str,
        category: str,
    ) -> Optional[UserJourney]:
        """Get user journey for a category."""
        key = f"{user_id}:{category}"
        
        if key in self._journeys:
            return self._journeys[key]
        
        # Check cache
        if self.cache:
            cached = await self.cache.get(f"journey:{key}")
            if cached:
                journey = UserJourney(**cached)
                self._journeys[key] = journey
                return journey
        
        return None
    
    async def get_or_create_journey(
        self,
        user_id: str,
        category: str,
    ) -> UserJourney:
        """Get or create a user journey."""
        existing = await self.get_journey(user_id, category)
        if existing:
            return existing
        
        # Create new journey at UNAWARE stage
        state = JourneyState(
            user_id=user_id,
            category=category,
            stage=JourneyStage.UNAWARE,
        )
        
        journey = UserJourney(
            user_id=user_id,
            category=category,
            current_state=state,
        )
        
        key = f"{user_id}:{category}"
        self._journeys[key] = journey
        
        return journey
    
    async def process_signal(
        self,
        user_id: str,
        category: str,
        signal_type: str,
        signal_data: Optional[Dict[str, Any]] = None,
    ) -> UserJourney:
        """
        Process a behavioral signal and update journey.
        """
        journey = await self.get_or_create_journey(user_id, category)
        current_stage = journey.current_state.stage
        
        # Check for transition
        transition_key = (signal_type, current_stage)
        new_stage = TRANSITION_SIGNALS.get(transition_key)
        
        if new_stage and new_stage in VALID_TRANSITIONS.get(current_stage, []):
            # Create transition
            transition = JourneyTransition(
                transition_id=f"trans_{uuid4().hex[:8]}",
                user_id=user_id,
                category=category,
                from_stage=current_stage,
                to_stage=new_stage,
                trigger_signal=signal_type,
                trigger_confidence=0.7,
                context=signal_data or {},
                time_in_previous_stage=datetime.now(timezone.utc) - journey.current_state.entered_stage_at,
            )
            
            # Update state
            journey.current_state.stage = new_stage
            journey.current_state.stage_confidence = 0.7
            journey.current_state.entered_stage_at = datetime.now(timezone.utc)
            
            # Record transition
            journey.transitions.append(transition)
            
            logger.info(
                f"Journey transition: {user_id}/{category} "
                f"{current_stage.value} -> {new_stage.value}"
            )
        
        # Update touchpoints
        journey.total_touchpoints += 1
        journey.current_state.touchpoint_count += 1
        journey.current_state.last_interaction = datetime.now(timezone.utc)
        journey.current_state.last_interaction_type = signal_type
        journey.updated_at = datetime.now(timezone.utc)
        
        # Detect urgency
        journey.current_state.urgency = self._detect_urgency(
            journey, signal_type, signal_data
        )
        
        # Predict next stage
        journey.predicted_next_stage = self._predict_next_stage(journey)
        
        # Cache
        if self.cache:
            key = f"{user_id}:{category}"
            await self.cache.set(
                f"journey:{key}",
                journey.model_dump(),
                ttl=86400 * 7,  # 7 days
            )
        
        return journey
    
    def _detect_urgency(
        self,
        journey: UserJourney,
        signal_type: str,
        signal_data: Optional[Dict[str, Any]],
    ) -> DecisionUrgency:
        """Detect decision urgency from signals."""
        
        # High urgency signals
        if signal_type in ["checkout_start", "add_to_cart"]:
            return DecisionUrgency.TODAY
        
        if signal_type == "compare_products":
            return DecisionUrgency.THIS_WEEK
        
        # Check for urgency keywords in context
        if signal_data:
            text = str(signal_data.get("query", "")).lower()
            if any(w in text for w in ["urgent", "now", "today", "asap"]):
                return DecisionUrgency.IMMEDIATE
            if any(w in text for w in ["soon", "this week"]):
                return DecisionUrgency.THIS_WEEK
        
        # Stage-based defaults
        stage_urgency = {
            JourneyStage.READY_TO_BUY: DecisionUrgency.TODAY,
            JourneyStage.DECIDING: DecisionUrgency.TODAY,
            JourneyStage.COMPARING: DecisionUrgency.THIS_WEEK,
            JourneyStage.RESEARCHING: DecisionUrgency.PLANNING,
        }
        
        return stage_urgency.get(
            journey.current_state.stage,
            DecisionUrgency.PASSIVE,
        )
    
    def _predict_next_stage(
        self,
        journey: UserJourney,
    ) -> Optional[JourneyStage]:
        """Predict most likely next stage."""
        current = journey.current_state.stage
        valid_next = VALID_TRANSITIONS.get(current, [])
        
        if not valid_next:
            return None
        
        # Simple heuristic: forward progression most likely
        forward_stages = [
            JourneyStage.AWARE,
            JourneyStage.CONSIDERING,
            JourneyStage.RESEARCHING,
            JourneyStage.COMPARING,
            JourneyStage.READY_TO_BUY,
            JourneyStage.DECIDING,
            JourneyStage.PURCHASING,
            JourneyStage.PURCHASED,
        ]
        
        current_idx = forward_stages.index(current) if current in forward_stages else -1
        
        for stage in valid_next:
            if stage in forward_stages:
                stage_idx = forward_stages.index(stage)
                if stage_idx > current_idx:
                    return stage
        
        return valid_next[0] if valid_next else None
    
    async def get_stage_distribution(
        self,
        category: str,
    ) -> Dict[str, int]:
        """Get distribution of users across stages for a category."""
        distribution = {stage.value: 0 for stage in JourneyStage}
        
        for key, journey in self._journeys.items():
            if journey.category == category:
                distribution[journey.current_state.stage.value] += 1
        
        return distribution


# =============================================================================
# SINGLETON
# =============================================================================

_service: Optional["JourneyTrackingService"] = None


def get_journey_tracking_service() -> "JourneyTrackingService":
    """Get or create the journey tracking service singleton."""
    global _service
    
    if _service is None:
        _service = JourneyTrackingService()
    
    return _service
