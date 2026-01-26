# =============================================================================
# ADAM Infrastructure
# =============================================================================

"""
Infrastructure components for ADAM platform.

This module provides core infrastructure services:
- Neo4j graph database connectivity and migrations
- Redis caching layer with ADAM key conventions
- Kafka event streaming for learning signals
- Prometheus metrics for psychological intelligence observability
"""

from adam.infrastructure.redis import ADAMRedisCache, CacheKeyBuilder, CacheDomain
from adam.infrastructure.kafka import (
    ADAMKafkaProducer,
    get_kafka_producer,
    ADAMTopics,
    LearningSignalEvent,
    AdOutcomeEvent,
)
from adam.infrastructure.prometheus import ADAMMetrics, get_metrics

__all__ = [
    # Redis
    "ADAMRedisCache",
    "CacheKeyBuilder",
    "CacheDomain",
    # Kafka
    "ADAMKafkaProducer",
    "get_kafka_producer",
    "ADAMTopics",
    "LearningSignalEvent",
    "AdOutcomeEvent",
    # Prometheus
    "ADAMMetrics",
    "get_metrics",
]
