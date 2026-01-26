# =============================================================================
# ADAM Kafka Infrastructure
# Location: adam/infrastructure/kafka/__init__.py
# =============================================================================

"""
KAFKA EVENT STREAMING INFRASTRUCTURE

ADAM's event bus for learning signals, outcomes, and platform events.

Topic Domains:
- adam.signals.* - Learning signals from components
- adam.outcomes.* - Ad/decision outcomes
- adam.events.* - Platform events (sessions, decisions)
- adam.cdc.* - Change data capture from Neo4j

All topics use Avro schemas for type safety and evolution.
"""

from adam.infrastructure.kafka.producer import (
    ADAMKafkaProducer,
    get_kafka_producer,
)
from adam.infrastructure.kafka.consumer import (
    ADAMKafkaConsumer,
    ConsumerGroup,
)
from adam.infrastructure.kafka.topics import (
    ADAMTopics,
    TopicConfig,
)
from adam.infrastructure.kafka.events import (
    LearningSignalEvent,
    AdOutcomeEvent,
    SessionEvent,
    DecisionEvent,
)

__all__ = [
    # Producer
    "ADAMKafkaProducer",
    "get_kafka_producer",
    # Consumer
    "ADAMKafkaConsumer",
    "ConsumerGroup",
    # Topics
    "ADAMTopics",
    "TopicConfig",
    # Events
    "LearningSignalEvent",
    "AdOutcomeEvent",
    "SessionEvent",
    "DecisionEvent",
]
