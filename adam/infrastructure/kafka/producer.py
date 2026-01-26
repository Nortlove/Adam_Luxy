# =============================================================================
# ADAM Kafka Producer
# Location: adam/infrastructure/kafka/producer.py
# =============================================================================

"""
KAFKA PRODUCER

Async Kafka producer for ADAM event publishing.
Supports batching, compression, and delivery guarantees.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from adam.config.settings import settings
from adam.infrastructure.kafka.topics import ADAMTopics
from adam.infrastructure.kafka.events import ADAMEvent

logger = logging.getLogger(__name__)


# Global producer instance
_producer: Optional["ADAMKafkaProducer"] = None


async def get_kafka_producer() -> Optional["ADAMKafkaProducer"]:
    """Get or create the global Kafka producer."""
    global _producer
    
    if _producer is None:
        _producer = ADAMKafkaProducer()
        await _producer.start()
    
    return _producer


class ADAMKafkaProducer:
    """
    Async Kafka producer for ADAM.
    
    Features:
    - Automatic JSON serialization
    - Event type routing
    - Delivery confirmation
    - Metrics integration
    """
    
    def __init__(self):
        self._producer = None
        self._is_connected = False
        self._metrics_enabled = True
    
    @property
    def is_connected(self) -> bool:
        """Check if producer is connected."""
        return self._is_connected
    
    async def start(self) -> None:
        """Start the Kafka producer."""
        try:
            # Import aiokafka here to make it optional
            from aiokafka import AIOKafkaProducer
            
            bootstrap_servers = getattr(settings, 'kafka', None)
            if bootstrap_servers:
                bootstrap_servers = settings.kafka.bootstrap_servers
            else:
                bootstrap_servers = "localhost:9092"
            
            self._producer = AIOKafkaProducer(
                bootstrap_servers=bootstrap_servers,
                value_serializer=lambda v: json.dumps(v, default=str).encode('utf-8'),
                key_serializer=lambda k: k.encode('utf-8') if k else None,
                compression_type="gzip",
                acks="all",  # Wait for all replicas
                enable_idempotence=True,
                max_batch_size=32768,  # 32KB batches
                linger_ms=10,  # Wait up to 10ms for batching
            )
            
            await self._producer.start()
            self._is_connected = True
            logger.info("Kafka producer started")
            
        except ImportError:
            logger.warning("aiokafka not installed, Kafka producer disabled")
            self._is_connected = False
        except Exception as e:
            logger.error(f"Failed to start Kafka producer: {e}")
            self._is_connected = False
    
    async def stop(self) -> None:
        """Stop the Kafka producer."""
        if self._producer:
            await self._producer.stop()
            self._is_connected = False
            logger.info("Kafka producer stopped")
    
    async def send(
        self,
        topic: ADAMTopics,
        value: Dict[str, Any],
        key: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> bool:
        """
        Send a message to a Kafka topic.
        
        Args:
            topic: Target topic
            value: Message value (will be JSON serialized)
            key: Optional message key for partitioning
            headers: Optional message headers
            
        Returns:
            True if message was sent successfully
        """
        if not self._is_connected or not self._producer:
            logger.warning(f"Kafka not connected, dropping message to {topic}")
            return False
        
        try:
            # Convert headers to Kafka format
            kafka_headers = None
            if headers:
                kafka_headers = [
                    (k, v.encode('utf-8')) for k, v in headers.items()
                ]
            
            await self._producer.send_and_wait(
                topic=topic.value,
                value=value,
                key=key,
                headers=kafka_headers,
            )
            
            logger.debug(f"Sent message to {topic.value}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send message to {topic}: {e}")
            return False
    
    async def send_event(
        self,
        topic: ADAMTopics,
        event: ADAMEvent,
        key: Optional[str] = None,
    ) -> bool:
        """
        Send an ADAM event to a Kafka topic.
        
        Args:
            topic: Target topic
            event: ADAM event to send
            key: Optional message key (defaults to event.user_id if available)
            
        Returns:
            True if event was sent successfully
        """
        # Use user_id as key for partitioning if available
        if key is None and hasattr(event, 'user_id') and event.user_id:
            key = event.user_id
        
        headers = {
            "event_type": event.event_type,
            "source": event.source,
            "version": event.version,
        }
        
        if event.trace_id:
            headers["trace_id"] = event.trace_id
        
        return await self.send(
            topic=topic,
            value=event.to_kafka_value(),
            key=key,
            headers=headers,
        )
    
    async def send_batch(
        self,
        topic: ADAMTopics,
        events: List[ADAMEvent],
    ) -> int:
        """
        Send a batch of events.
        
        Args:
            topic: Target topic
            events: List of events to send
            
        Returns:
            Number of events successfully sent
        """
        if not events:
            return 0
        
        sent = 0
        for event in events:
            if await self.send_event(topic, event):
                sent += 1
        
        return sent
    
    # -------------------------------------------------------------------------
    # CONVENIENCE METHODS
    # -------------------------------------------------------------------------
    
    async def emit_learning_signal(
        self,
        signal_type: str,
        signal_name: str,
        signal_value: float,
        user_id: Optional[str] = None,
        decision_id: Optional[str] = None,
        component_id: str = "adam",
        confidence: float = 0.8,
        metadata: Optional[Dict] = None,
    ) -> bool:
        """
        Emit a learning signal to the Gradient Bridge.
        
        Args:
            signal_type: Type of signal (cold_start, multimodal, etc.)
            signal_name: Name of the signal
            signal_value: Signal value (-1 to 1)
            user_id: Optional user ID
            decision_id: Optional decision ID
            component_id: Component emitting the signal
            confidence: Signal confidence
            metadata: Additional metadata
            
        Returns:
            True if signal was emitted successfully
        """
        from adam.infrastructure.kafka.events import LearningSignalEvent, SignalType
        
        try:
            sig_type = SignalType(signal_type)
        except ValueError:
            sig_type = SignalType.MECHANISM_EFFECTIVENESS
        
        event = LearningSignalEvent(
            signal_type=sig_type,
            component_id=component_id,
            user_id=user_id,
            decision_id=decision_id,
            signal_name=signal_name,
            signal_value=signal_value,
            signal_confidence=confidence,
            metadata=metadata or {},
        )
        
        return await self.send_event(ADAMTopics.SIGNALS_LEARNING, event)
    
    async def emit_ad_outcome(
        self,
        decision_id: str,
        user_id: str,
        campaign_id: str,
        creative_id: str,
        outcome_type: str,
        outcome_value: float,
        mechanisms_applied: Optional[List[str]] = None,
        session_id: Optional[str] = None,
    ) -> bool:
        """
        Emit an ad outcome event.
        
        Args:
            decision_id: Decision ID
            user_id: User ID
            campaign_id: Campaign ID
            creative_id: Creative ID
            outcome_type: Type of outcome
            outcome_value: Outcome value (0-1)
            mechanisms_applied: Mechanisms that were applied
            session_id: Optional session ID
            
        Returns:
            True if outcome was emitted successfully
        """
        from adam.infrastructure.kafka.events import AdOutcomeEvent, AdOutcomeType
        
        try:
            out_type = AdOutcomeType(outcome_type)
        except ValueError:
            out_type = AdOutcomeType.LISTEN_PARTIAL
        
        event = AdOutcomeEvent(
            decision_id=decision_id,
            user_id=user_id,
            session_id=session_id,
            campaign_id=campaign_id,
            creative_id=creative_id,
            outcome_type=out_type,
            outcome_value=outcome_value,
            mechanisms_applied=mechanisms_applied or [],
        )
        
        return await self.send_event(ADAMTopics.OUTCOMES_AD, event)
