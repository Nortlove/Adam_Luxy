# =============================================================================
# ADAM Event Bus
# Location: adam/core/learning/event_bus.py
# =============================================================================

"""
EVENT BUS IMPLEMENTATIONS

Provides event bus implementations for learning signal routing.

Primary implementation uses Kafka for distributed signal propagation.
Fallback to in-memory for local development and testing.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Set
from dataclasses import dataclass, field
from collections import defaultdict
import uuid

logger = logging.getLogger(__name__)


# =============================================================================
# EVENT BUS INTERFACE
# =============================================================================

@dataclass
class Event:
    """
    An event in the event bus.
    
    Events can carry any payload and are routed to subscribed handlers
    based on their topic.
    """
    
    event_id: str = field(default_factory=lambda: f"evt_{uuid.uuid4().hex[:12]}")
    topic: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    source: str = ""
    
    # For helpful-vote weighted signals (supporting data philosophy)
    confidence: float = 1.0
    weight: float = 1.0  # Can be set based on helpful_vote influence


class EventBusInterface:
    """Base interface for event bus implementations."""
    
    async def publish(self, topic: str, event: Event) -> bool:
        """Publish an event to a topic."""
        raise NotImplementedError
    
    async def subscribe(self, topic: str, handler: Callable) -> str:
        """Subscribe to a topic. Returns subscription ID."""
        raise NotImplementedError
    
    async def unsubscribe(self, subscription_id: str) -> bool:
        """Unsubscribe from a topic."""
        raise NotImplementedError
    
    async def close(self) -> None:
        """Clean shutdown."""
        raise NotImplementedError


# =============================================================================
# IN-MEMORY EVENT BUS (Local/Testing)
# =============================================================================

class InMemoryEventBus(EventBusInterface):
    """
    In-memory event bus for local development and testing.
    
    Features:
    - Async event handling
    - Topic-based routing
    - Multiple subscribers per topic
    - No external dependencies
    
    Note: Events are not persisted. For production, use Kafka-backed bus.
    """
    
    # Maximum queue depth — prevents OOM under sustained load.
    # 10K events × ~1KB each ≈ 10MB. If the queue fills, new events
    # are dropped with a warning rather than blocking the caller.
    _MAX_QUEUE_SIZE = 10_000

    def __init__(self):
        self._subscriptions: Dict[str, Dict[str, Callable]] = defaultdict(dict)
        self._pending_events: asyncio.Queue = asyncio.Queue(maxsize=self._MAX_QUEUE_SIZE)
        self._running = False
        self._processor_task: Optional[asyncio.Task] = None

        # Metrics
        self._events_published = 0
        self._events_delivered = 0
        self._events_dropped = 0

        logger.info("InMemoryEventBus initialized (max_queue=%d)", self._MAX_QUEUE_SIZE)
    
    async def start(self) -> None:
        """Start the event processor."""
        if self._running:
            return
        
        self._running = True
        self._processor_task = asyncio.create_task(self._process_events())
        logger.info("InMemoryEventBus started")
    
    async def publish(self, topic: str, event: Event) -> bool:
        """
        Publish an event to a topic.

        Events are queued and processed asynchronously. If the queue is
        full (backpressure), the event is dropped with a warning rather
        than blocking the caller — the hot path must never block on
        learning signal delivery.
        """
        if not event.topic:
            event.topic = topic

        try:
            self._pending_events.put_nowait(event)
            self._events_published += 1
            logger.debug(f"Event {event.event_id} published to topic '{topic}'")
            return True
        except asyncio.QueueFull:
            self._events_dropped += 1
            if self._events_dropped % 100 == 1:
                logger.warning(
                    "EventBus queue full (%d): dropping event %s on topic '%s'. "
                    "Total dropped: %d. Processing may be too slow.",
                    self._MAX_QUEUE_SIZE, event.event_id, topic,
                    self._events_dropped,
                )
            return False
    
    async def subscribe(
        self, 
        topic: str, 
        handler: Callable[[Event], Any]
    ) -> str:
        """
        Subscribe to a topic.
        
        Handler will be called for each event on the topic.
        Returns subscription ID for later unsubscription.
        """
        subscription_id = f"sub_{uuid.uuid4().hex[:8]}"
        self._subscriptions[topic][subscription_id] = handler
        
        logger.debug(f"Subscription {subscription_id} added to topic '{topic}'")
        return subscription_id
    
    async def unsubscribe(self, subscription_id: str) -> bool:
        """Unsubscribe from a topic."""
        for topic, subs in self._subscriptions.items():
            if subscription_id in subs:
                del subs[subscription_id]
                logger.debug(f"Subscription {subscription_id} removed from topic '{topic}'")
                return True
        return False
    
    async def _process_events(self) -> None:
        """Background task to process events."""
        while self._running:
            try:
                # Wait for event with timeout
                try:
                    event = await asyncio.wait_for(
                        self._pending_events.get(),
                        timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue
                
                # Get handlers for this topic
                handlers = self._subscriptions.get(event.topic, {})
                
                if not handlers:
                    self._events_dropped += 1
                    logger.debug(f"No handlers for topic '{event.topic}', event dropped")
                    continue
                
                # Call all handlers
                for sub_id, handler in handlers.items():
                    try:
                        result = handler(event)
                        if asyncio.iscoroutine(result):
                            await result
                        self._events_delivered += 1
                    except Exception as e:
                        logger.error(f"Handler {sub_id} failed for event {event.event_id}: {e}")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Event processor error: {e}")
    
    async def close(self) -> None:
        """Clean shutdown."""
        self._running = False
        if self._processor_task:
            self._processor_task.cancel()
            try:
                await self._processor_task
            except asyncio.CancelledError:
                pass
        
        logger.info(
            f"InMemoryEventBus closed. "
            f"Published: {self._events_published}, "
            f"Delivered: {self._events_delivered}, "
            f"Dropped: {self._events_dropped}"
        )
    
    async def stop(self) -> None:
        """Alias for close() for compatibility."""
        await self.close()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get event bus statistics."""
        return {
            "events_published": self._events_published,
            "events_delivered": self._events_delivered,
            "events_dropped": self._events_dropped,
            "pending_events": self._pending_events.qsize(),
            "active_topics": len(self._subscriptions),
            "total_subscriptions": sum(len(s) for s in self._subscriptions.values()),
        }


# =============================================================================
# KAFKA-BACKED EVENT BUS (Production)
# =============================================================================

class KafkaEventBus(EventBusInterface):
    """
    Kafka-backed event bus for production use.
    
    Uses Kafka for:
    - Distributed signal propagation
    - Persistence and replay
    - Horizontal scaling
    
    Requires Kafka infrastructure to be running.
    """
    
    def __init__(self, bootstrap_servers: str = "localhost:9092"):
        self.bootstrap_servers = bootstrap_servers
        self._producer = None
        self._consumers: Dict[str, Any] = {}
        self._initialized = False
        
        logger.info(f"KafkaEventBus initialized with servers: {bootstrap_servers}")
    
    async def _ensure_initialized(self) -> None:
        """Lazy initialization of Kafka producer."""
        if self._initialized:
            return
        
        try:
            from adam.infrastructure.kafka import get_kafka_producer
            self._producer = await get_kafka_producer()
            self._initialized = True
            logger.info("Kafka producer initialized")
        except Exception as e:
            logger.warning(f"Kafka initialization failed, falling back to in-memory: {e}")
            raise
    
    async def publish(self, topic: str, event: Event) -> bool:
        """Publish event to Kafka topic."""
        try:
            await self._ensure_initialized()
            
            if self._producer:
                await self._producer.send(
                    topic,
                    value=event.payload,
                    key=event.event_id,
                )
                return True
        except Exception as e:
            logger.error(f"Failed to publish to Kafka: {e}")
        return False
    
    async def subscribe(self, topic: str, handler: Callable) -> str:
        """Subscribe to Kafka topic."""
        # Note: Full Kafka consumer implementation would go here
        # For now, this is a placeholder that should be expanded
        subscription_id = f"kafka_sub_{uuid.uuid4().hex[:8]}"
        self._consumers[subscription_id] = {
            "topic": topic,
            "handler": handler,
        }
        logger.info(f"Kafka subscription {subscription_id} created for topic '{topic}'")
        return subscription_id
    
    async def unsubscribe(self, subscription_id: str) -> bool:
        """Unsubscribe from Kafka topic."""
        if subscription_id in self._consumers:
            del self._consumers[subscription_id]
            return True
        return False
    
    async def close(self) -> None:
        """Clean shutdown."""
        if self._producer:
            await self._producer.stop()
        logger.info("KafkaEventBus closed")
    
    async def stop(self) -> None:
        """Alias for close() for compatibility."""
        await self.close()


# =============================================================================
# FACTORY FUNCTION
# =============================================================================

_event_bus: Optional[EventBusInterface] = None


async def get_event_bus(use_kafka: bool = False) -> EventBusInterface:
    """
    Get or create the event bus singleton.
    
    Args:
        use_kafka: If True, use Kafka-backed bus. Otherwise, in-memory.
        
    Returns:
        EventBusInterface implementation
    """
    global _event_bus
    
    if _event_bus is not None:
        return _event_bus
    
    if use_kafka:
        try:
            _event_bus = KafkaEventBus()
            await _event_bus._ensure_initialized()
        except Exception as e:
            logger.warning(f"Kafka event bus failed, using in-memory: {e}")
            _event_bus = InMemoryEventBus()
    else:
        _event_bus = InMemoryEventBus()
    
    # Start processing for in-memory bus
    if isinstance(_event_bus, InMemoryEventBus):
        await _event_bus.start()
    
    return _event_bus


async def reset_event_bus() -> None:
    """Reset the event bus (for testing)."""
    global _event_bus
    if _event_bus:
        await _event_bus.close()
        _event_bus = None
