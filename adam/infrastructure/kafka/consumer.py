# =============================================================================
# ADAM Kafka Consumer
# Location: adam/infrastructure/kafka/consumer.py
# =============================================================================

"""
KAFKA CONSUMER

Async Kafka consumer for ADAM event processing.
Supports consumer groups, offset management, and error handling.
"""

import asyncio
import json
import logging
from enum import Enum
from typing import Any, Callable, Coroutine, Dict, List, Optional

from adam.config.settings import settings
from adam.infrastructure.kafka.topics import ADAMTopics

logger = logging.getLogger(__name__)


class ConsumerGroup(str, Enum):
    """
    Consumer group definitions.
    
    Each group processes events independently for different purposes.
    """
    
    # Gradient Bridge - primary learning consumer
    GRADIENT_BRIDGE = "adam-gradient-bridge"
    
    # Profile updater
    PROFILE_UPDATER = "adam-profile-updater"
    
    # Analytics and reporting
    ANALYTICS = "adam-analytics"
    
    # Archetype learning
    ARCHETYPE_LEARNING = "adam-archetype-learning"
    
    # Mechanism learning
    MECHANISM_LEARNING = "adam-mechanism-learning"
    
    # CDC processing
    CDC_PROCESSOR = "adam-cdc-processor"
    
    # Debug/monitoring
    DEBUG = "adam-debug"


# Type alias for message handlers
MessageHandler = Callable[[Dict[str, Any]], Coroutine[Any, Any, None]]


class ADAMKafkaConsumer:
    """
    Async Kafka consumer for ADAM.
    
    Features:
    - Consumer group management
    - Automatic offset commits
    - Message deserialization
    - Error handling with dead-letter queue
    """
    
    def __init__(
        self,
        topics: List[ADAMTopics],
        group_id: ConsumerGroup,
        handler: MessageHandler,
    ):
        """
        Initialize consumer.
        
        Args:
            topics: Topics to subscribe to
            group_id: Consumer group
            handler: Async function to process messages
        """
        self.topics = [t.value for t in topics]
        self.group_id = group_id.value
        self.handler = handler
        
        self._consumer = None
        self._is_running = False
        self._task: Optional[asyncio.Task] = None
    
    async def start(self) -> None:
        """Start consuming messages."""
        try:
            from aiokafka import AIOKafkaConsumer
            
            bootstrap_servers = getattr(settings, 'kafka', None)
            if bootstrap_servers:
                bootstrap_servers = settings.kafka.bootstrap_servers
            else:
                bootstrap_servers = "localhost:9092"
            
            self._consumer = AIOKafkaConsumer(
                *self.topics,
                bootstrap_servers=bootstrap_servers,
                group_id=self.group_id,
                value_deserializer=lambda v: json.loads(v.decode('utf-8')),
                auto_offset_reset="earliest",
                enable_auto_commit=True,
                auto_commit_interval_ms=5000,
                max_poll_records=100,
            )
            
            await self._consumer.start()
            self._is_running = True
            
            logger.info(f"Kafka consumer started for group {self.group_id}")
            
            # Start consuming in background
            self._task = asyncio.create_task(self._consume_loop())
            
        except ImportError:
            logger.warning("aiokafka not installed, Kafka consumer disabled")
        except Exception as e:
            logger.error(f"Failed to start Kafka consumer: {e}")
    
    async def stop(self) -> None:
        """Stop consuming messages."""
        self._is_running = False
        
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        
        if self._consumer:
            await self._consumer.stop()
            logger.info(f"Kafka consumer stopped for group {self.group_id}")
    
    async def _consume_loop(self) -> None:
        """Main consumption loop."""
        while self._is_running:
            try:
                async for message in self._consumer:
                    try:
                        await self.handler(message.value)
                    except Exception as e:
                        logger.error(
                            f"Error processing message from {message.topic}: {e}"
                        )
                        # TODO: Send to dead-letter queue
                        
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Consumer loop error: {e}")
                await asyncio.sleep(5)  # Wait before retrying
    
    @property
    def is_running(self) -> bool:
        """Check if consumer is running."""
        return self._is_running


# =============================================================================
# CONSUMER FACTORY
# =============================================================================

async def create_learning_signal_consumer(
    handler: MessageHandler,
) -> ADAMKafkaConsumer:
    """Create a consumer for learning signals."""
    consumer = ADAMKafkaConsumer(
        topics=[
            ADAMTopics.SIGNALS_LEARNING,
            ADAMTopics.SIGNALS_COLD_START,
            ADAMTopics.SIGNALS_MULTIMODAL,
            ADAMTopics.SIGNALS_TEMPORAL,
        ],
        group_id=ConsumerGroup.GRADIENT_BRIDGE,
        handler=handler,
    )
    await consumer.start()
    return consumer


async def create_outcome_consumer(
    handler: MessageHandler,
) -> ADAMKafkaConsumer:
    """Create a consumer for ad outcomes."""
    consumer = ADAMKafkaConsumer(
        topics=[
            ADAMTopics.OUTCOMES_AD,
            ADAMTopics.OUTCOMES_MECHANISM,
        ],
        group_id=ConsumerGroup.MECHANISM_LEARNING,
        handler=handler,
    )
    await consumer.start()
    return consumer


async def create_iheart_event_consumer(
    handler: MessageHandler,
) -> ADAMKafkaConsumer:
    """Create a consumer for iHeart events."""
    consumer = ADAMKafkaConsumer(
        topics=[
            ADAMTopics.EVENTS_IHEART_LISTENING,
            ADAMTopics.EVENTS_IHEART_SESSION,
            ADAMTopics.EVENTS_IHEART_AD,
        ],
        group_id=ConsumerGroup.PROFILE_UPDATER,
        handler=handler,
    )
    await consumer.start()
    return consumer
