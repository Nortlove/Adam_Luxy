#!/usr/bin/env python3
"""
EVENT BUS
=========

Re-exports event bus from core learning module for convenience.

Phase 5: Learning Loop Completion
"""

# Re-export from core learning event bus
from adam.core.learning.event_bus import (
    Event,
    EventBusInterface,
    InMemoryEventBus,
    get_event_bus as get_event_bus_async,  # Async version
    reset_event_bus,
)

# Synchronous getter for non-async contexts
_sync_bus = None

def get_event_bus_sync():
    """Get event bus synchronously (creates InMemoryEventBus)."""
    global _sync_bus
    if _sync_bus is None:
        _sync_bus = InMemoryEventBus()
    return _sync_bus

# Default to async getter
get_event_bus = get_event_bus_async

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Set
from enum import Enum

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    """Event types in ADAM system."""
    
    # Learning events
    OUTCOME_RECORDED = "outcome.recorded"
    LEARNING_SIGNAL = "learning.signal"
    CREDIT_ATTRIBUTED = "credit.attributed"
    
    # Decision events
    DECISION_MADE = "decision.made"
    MECHANISM_SELECTED = "mechanism.selected"
    
    # Model events
    MODEL_UPDATED = "model.updated"
    BANDIT_REWARD = "bandit.reward"
    
    # Graph events
    GRAPH_UPDATED = "graph.updated"
    EDGE_STRENGTHENED = "edge.strengthened"


@dataclass
class Event:
    """An event in the system."""
    
    event_type: EventType
    payload: Dict[str, Any]
    source: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    event_id: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.event_type.value,
            "payload": self.payload,
            "source": self.source,
            "timestamp": self.timestamp.isoformat(),
            "event_id": self.event_id,
        }


EventHandler = Callable[[Event], None]
AsyncEventHandler = Callable[[Event], Any]


class EventBus:
    """
    In-memory event bus with async support.
    
    Enables decoupled communication between ADAM components
    without requiring external infrastructure.
    """
    
    def __init__(self):
        self._handlers: Dict[EventType, List[AsyncEventHandler]] = defaultdict(list)
        self._event_count = 0
        self._event_history: List[Event] = []
        self._history_limit = 1000
        self._running = True
    
    def subscribe(
        self,
        event_type: EventType,
        handler: AsyncEventHandler,
    ) -> None:
        """Subscribe to an event type."""
        self._handlers[event_type].append(handler)
        logger.debug(f"Subscribed handler to {event_type.value}")
    
    def unsubscribe(
        self,
        event_type: EventType,
        handler: AsyncEventHandler,
    ) -> None:
        """Unsubscribe from an event type."""
        if handler in self._handlers[event_type]:
            self._handlers[event_type].remove(handler)
    
    async def publish(self, event: Event) -> int:
        """
        Publish an event to all subscribers.
        
        Returns number of handlers notified.
        """
        if not self._running:
            return 0
        
        # Assign ID if not set
        if not event.event_id:
            self._event_count += 1
            event.event_id = f"evt_{self._event_count}"
        
        # Store in history
        self._event_history.append(event)
        if len(self._event_history) > self._history_limit:
            self._event_history = self._event_history[-self._history_limit:]
        
        # Notify handlers
        handlers = self._handlers.get(event.event_type, [])
        notified = 0
        
        for handler in handlers:
            try:
                result = handler(event)
                if asyncio.iscoroutine(result):
                    await result
                notified += 1
            except Exception as e:
                logger.error(f"Event handler error for {event.event_type.value}: {e}")
        
        logger.debug(f"Published {event.event_type.value} to {notified} handlers")
        return notified
    
    async def emit(
        self,
        event_type: EventType,
        payload: Dict[str, Any],
        source: str = "",
    ) -> int:
        """Convenience method to create and publish an event."""
        event = Event(
            event_type=event_type,
            payload=payload,
            source=source,
        )
        return await self.publish(event)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get event bus statistics."""
        return {
            "total_events": self._event_count,
            "history_size": len(self._event_history),
            "subscriptions": {
                event_type.value: len(handlers)
                for event_type, handlers in self._handlers.items()
                if handlers
            },
        }
    
    def shutdown(self) -> None:
        """Shutdown the event bus."""
        self._running = False
        self._handlers.clear()


# =============================================================================
# SINGLETON
# =============================================================================

_event_bus: Optional[EventBus] = None


def get_event_bus() -> EventBus:
    """Get singleton event bus."""
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
    return _event_bus


# =============================================================================
# HELPERS FOR LEARNING LOOP
# =============================================================================

async def emit_outcome_event(
    decision_id: str,
    outcome_type: str,
    outcome_value: float,
    signals_generated: int = 0,
) -> None:
    """Emit an outcome event to the bus."""
    bus = get_event_bus()
    await bus.emit(
        EventType.OUTCOME_RECORDED,
        payload={
            "decision_id": decision_id,
            "outcome_type": outcome_type,
            "outcome_value": outcome_value,
            "signals_generated": signals_generated,
        },
        source="gradient_bridge",
    )


async def emit_learning_signal(
    signal_type: str,
    component: str,
    value: float,
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    """Emit a learning signal event."""
    bus = get_event_bus()
    await bus.emit(
        EventType.LEARNING_SIGNAL,
        payload={
            "signal_type": signal_type,
            "component": component,
            "value": value,
            "metadata": metadata or {},
        },
        source=component,
    )
