# =============================================================================
# ADAM Enhancement #13: Cold Start Event Contracts
# Location: adam/cold_start/events/contracts.py
# =============================================================================

"""
Event contracts for Cold Start system integration.

Events emitted:
- DECISION_MADE: Cold start decision was made
- TIER_TRANSITION: User moved between tiers
- PRIOR_UPDATE: Prior was updated from outcome
- ARCHETYPE_ASSIGNMENT: User assigned to archetype
- EXPLORATION_ACTION: Thompson Sampling exploration
"""

from __future__ import annotations
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
import uuid


class ColdStartEventType(str, Enum):
    """Types of cold start events."""
    DECISION_MADE = "cold_start.decision_made"
    TIER_TRANSITION = "cold_start.tier_transition"
    PRIOR_UPDATE = "cold_start.prior_update"
    ARCHETYPE_ASSIGNMENT = "cold_start.archetype_assignment"
    EXPLORATION_ACTION = "cold_start.exploration_action"
    OUTCOME_RECEIVED = "cold_start.outcome_received"


class ColdStartEvent(BaseModel):
    """Base cold start event."""
    
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: ColdStartEventType
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Context
    user_id: Optional[str] = None
    session_id: str
    request_id: Optional[str] = None
    
    # Payload
    payload: Dict[str, Any] = Field(default_factory=dict)
    
    # Routing
    source: str = "cold_start_service"
    target_topics: List[str] = Field(default_factory=list)


class DecisionMadeEvent(ColdStartEvent):
    """Event when a cold start decision is made."""
    
    event_type: ColdStartEventType = ColdStartEventType.DECISION_MADE
    
    # Decision details
    data_tier: str
    strategy_applied: str
    archetype: Optional[str] = None
    archetype_confidence: float = 0.0
    overall_confidence: float = 0.0
    exploration_rate: float = 0.0
    
    # For downstream consumers
    mechanism_recommendations: List[str] = Field(default_factory=list)
    latency_ms: float = 0.0


class TierTransitionEvent(ColdStartEvent):
    """Event when user transitions between tiers."""
    
    event_type: ColdStartEventType = ColdStartEventType.TIER_TRANSITION
    
    previous_tier: str
    new_tier: str
    interaction_count: int = 0
    time_in_previous_tier_hours: float = 0.0


class PriorUpdateEvent(ColdStartEvent):
    """Event when a prior is updated from outcome."""
    
    event_type: ColdStartEventType = ColdStartEventType.PRIOR_UPDATE
    
    prior_type: str  # "population", "demographic", "archetype", "user"
    update_source: str  # "outcome", "feedback", "batch"
    affected_traits: List[str] = Field(default_factory=list)
    affected_mechanisms: List[str] = Field(default_factory=list)


class ArchetypeAssignmentEvent(ColdStartEvent):
    """Event when user is assigned to archetype."""
    
    event_type: ColdStartEventType = ColdStartEventType.ARCHETYPE_ASSIGNMENT
    
    archetype_id: str
    confidence: float = 0.0
    previous_archetype: Optional[str] = None
    assignment_method: str = "detection"
    trait_evidence: Dict[str, float] = Field(default_factory=dict)


class ExplorationActionEvent(ColdStartEvent):
    """Event when Thompson Sampling explores."""
    
    event_type: ColdStartEventType = ColdStartEventType.EXPLORATION_ACTION
    
    mechanism_explored: str
    exploration_reason: str
    posterior_before: Dict[str, float] = Field(default_factory=dict)
    sample_value: float = 0.0


class OutcomeReceivedEvent(ColdStartEvent):
    """Event when outcome is received for learning."""
    
    event_type: ColdStartEventType = ColdStartEventType.OUTCOME_RECEIVED
    
    decision_id: str
    outcome_type: str  # "conversion", "click", "engagement"
    outcome_value: float = 0.0
    mechanisms_activated: List[str] = Field(default_factory=list)
    latency_seconds: float = 0.0


class ColdStartEventPublisher:
    """
    Publisher for cold start events.
    
    Integrates with Kafka for event distribution.
    """
    
    TOPIC_MAPPING = {
        ColdStartEventType.DECISION_MADE: ["adam.decisions", "adam.cold_start"],
        ColdStartEventType.TIER_TRANSITION: ["adam.user_updates", "adam.cold_start"],
        ColdStartEventType.PRIOR_UPDATE: ["adam.learning", "adam.cold_start"],
        ColdStartEventType.ARCHETYPE_ASSIGNMENT: ["adam.user_updates", "adam.cold_start"],
        ColdStartEventType.EXPLORATION_ACTION: ["adam.exploration", "adam.cold_start"],
        ColdStartEventType.OUTCOME_RECEIVED: ["adam.outcomes", "adam.learning"],
    }
    
    def __init__(self, kafka_producer=None):
        self.producer = kafka_producer
        self._events_published = 0
    
    async def publish(self, event: ColdStartEvent) -> bool:
        """Publish event to appropriate topics."""
        topics = self.TOPIC_MAPPING.get(event.event_type, ["adam.cold_start"])
        event.target_topics = topics
        
        if self.producer:
            try:
                for topic in topics:
                    await self.producer.send(
                        topic=topic,
                        key=event.session_id.encode() if event.session_id else None,
                        value=event.model_dump_json().encode()
                    )
                self._events_published += 1
                return True
            except Exception as e:
                import logging
                logging.error(f"Failed to publish event: {e}")
                return False
        
        # Log if no producer
        self._events_published += 1
        return True
    
    def get_statistics(self) -> Dict[str, int]:
        """Get publishing statistics."""
        return {"events_published": self._events_published}


# Singleton instance
_publisher: Optional[ColdStartEventPublisher] = None


def get_event_publisher(kafka_producer=None) -> ColdStartEventPublisher:
    """Get singleton event publisher."""
    global _publisher
    if _publisher is None:
        _publisher = ColdStartEventPublisher(kafka_producer)
    return _publisher
