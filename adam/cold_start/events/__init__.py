# =============================================================================
# ADAM Enhancement #13: Events Package
# Location: adam/cold_start/events/__init__.py
# =============================================================================

"""
Cold Start Event System

Event types:
- DecisionMadeEvent: Cold start decision was made
- TierTransitionEvent: User moved between tiers
- PriorUpdateEvent: Prior was updated from outcome
- ArchetypeAssignmentEvent: User assigned to archetype
- ExplorationActionEvent: Thompson Sampling exploration
- OutcomeReceivedEvent: Outcome received for learning
"""

from .contracts import (
    ColdStartEventType,
    ColdStartEvent,
    DecisionMadeEvent,
    TierTransitionEvent,
    PriorUpdateEvent,
    ArchetypeAssignmentEvent,
    ExplorationActionEvent,
    OutcomeReceivedEvent,
    ColdStartEventPublisher,
    get_event_publisher,
)

__all__ = [
    "ColdStartEventType",
    "ColdStartEvent",
    "DecisionMadeEvent",
    "TierTransitionEvent",
    "PriorUpdateEvent",
    "ArchetypeAssignmentEvent",
    "ExplorationActionEvent",
    "OutcomeReceivedEvent",
    "ColdStartEventPublisher",
    "get_event_publisher",
]
