# =============================================================================
# ADAM Kafka Topics Configuration
# Location: adam/infrastructure/kafka/topics.py
# =============================================================================

"""
KAFKA TOPIC DEFINITIONS

All ADAM Kafka topics with configurations optimized for:
- Learning signal propagation
- Outcome event streaming
- Real-time session tracking

Topic Naming Convention: adam.{domain}.{entity}
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional


@dataclass
class TopicConfig:
    """Kafka topic configuration."""
    
    name: str
    partitions: int = 6
    replication_factor: int = 3
    retention_ms: int = 604800000  # 7 days default
    cleanup_policy: str = "delete"  # or "compact"
    
    # ADAM-specific
    description: str = ""
    schema_name: Optional[str] = None
    
    def to_dict(self) -> Dict:
        """Convert to dict for topic creation."""
        return {
            "name": self.name,
            "num_partitions": self.partitions,
            "replication_factor": self.replication_factor,
            "config": {
                "retention.ms": str(self.retention_ms),
                "cleanup.policy": self.cleanup_policy,
            }
        }


class ADAMTopics(str, Enum):
    """
    ADAM Kafka topic names.
    
    Organized by domain:
    - SIGNALS: Learning signals from all components
    - OUTCOMES: Ad and decision outcomes
    - EVENTS: Platform events (sessions, decisions)
    - CDC: Change data capture
    """
    
    # -------------------------------------------------------------------------
    # LEARNING SIGNALS
    # -------------------------------------------------------------------------
    
    # Aggregated learning signals from all components
    SIGNALS_LEARNING = "adam.signals.learning"
    
    # Component-specific signal topics
    SIGNALS_COLD_START = "adam.signals.cold_start"
    SIGNALS_MULTIMODAL = "adam.signals.multimodal"
    SIGNALS_TEMPORAL = "adam.signals.temporal"
    SIGNALS_VERIFICATION = "adam.signals.verification"
    SIGNALS_EMERGENCE = "adam.signals.emergence"
    SIGNALS_FEATURE_STORE = "adam.signals.feature_store"
    
    # -------------------------------------------------------------------------
    # OUTCOMES
    # -------------------------------------------------------------------------
    
    # Ad decision outcomes
    OUTCOMES_AD = "adam.outcomes.ad"
    
    # Mechanism effectiveness
    OUTCOMES_MECHANISM = "adam.outcomes.mechanism"
    
    # Profile update outcomes
    OUTCOMES_PROFILE = "adam.outcomes.profile"
    
    # -------------------------------------------------------------------------
    # PLATFORM EVENTS
    # -------------------------------------------------------------------------
    
    # iHeart listening events
    EVENTS_IHEART_LISTENING = "adam.events.iheart.listening"
    EVENTS_IHEART_SESSION = "adam.events.iheart.session"
    EVENTS_IHEART_AD = "adam.events.iheart.ad"
    
    # Decision events
    EVENTS_DECISION = "adam.events.decision"
    EVENTS_DECISION_REASONING = "adam.events.decision.reasoning"
    
    # Profile events
    EVENTS_PROFILE_UPDATE = "adam.events.profile.update"
    
    # -------------------------------------------------------------------------
    # CHANGE DATA CAPTURE
    # -------------------------------------------------------------------------
    
    # Neo4j CDC for graph updates
    CDC_USER_PROFILE = "adam.cdc.user_profile"
    CDC_MECHANISM = "adam.cdc.mechanism"
    CDC_DECISION = "adam.cdc.decision"


# Topic configurations
TOPIC_CONFIGS: Dict[ADAMTopics, TopicConfig] = {
    # Learning signals - high throughput
    ADAMTopics.SIGNALS_LEARNING: TopicConfig(
        name=ADAMTopics.SIGNALS_LEARNING.value,
        partitions=12,
        retention_ms=86400000,  # 1 day
        description="Aggregated learning signals from all ADAM components",
        schema_name="LearningSignal",
    ),
    ADAMTopics.SIGNALS_COLD_START: TopicConfig(
        name=ADAMTopics.SIGNALS_COLD_START.value,
        partitions=6,
        retention_ms=86400000,
        description="Cold start learning signals",
        schema_name="ColdStartSignal",
    ),
    
    # Outcomes - medium throughput, longer retention
    ADAMTopics.OUTCOMES_AD: TopicConfig(
        name=ADAMTopics.OUTCOMES_AD.value,
        partitions=12,
        retention_ms=604800000,  # 7 days
        description="Ad decision outcomes for learning",
        schema_name="AdOutcome",
    ),
    ADAMTopics.OUTCOMES_MECHANISM: TopicConfig(
        name=ADAMTopics.OUTCOMES_MECHANISM.value,
        partitions=6,
        retention_ms=604800000,
        description="Mechanism effectiveness outcomes",
        schema_name="MechanismOutcome",
    ),
    
    # iHeart events - high throughput
    ADAMTopics.EVENTS_IHEART_LISTENING: TopicConfig(
        name=ADAMTopics.EVENTS_IHEART_LISTENING.value,
        partitions=24,  # High volume
        retention_ms=86400000,
        description="iHeart listening events",
        schema_name="ListeningEvent",
    ),
    ADAMTopics.EVENTS_IHEART_SESSION: TopicConfig(
        name=ADAMTopics.EVENTS_IHEART_SESSION.value,
        partitions=12,
        retention_ms=172800000,  # 2 days
        description="iHeart session events",
        schema_name="SessionEvent",
    ),
    ADAMTopics.EVENTS_IHEART_AD: TopicConfig(
        name=ADAMTopics.EVENTS_IHEART_AD.value,
        partitions=12,
        retention_ms=604800000,
        description="iHeart ad events",
        schema_name="AdEvent",
    ),
    
    # Decision events
    ADAMTopics.EVENTS_DECISION: TopicConfig(
        name=ADAMTopics.EVENTS_DECISION.value,
        partitions=12,
        retention_ms=604800000,
        description="ADAM decision events",
        schema_name="DecisionEvent",
    ),
    ADAMTopics.EVENTS_DECISION_REASONING: TopicConfig(
        name=ADAMTopics.EVENTS_DECISION_REASONING.value,
        partitions=6,
        retention_ms=604800000,
        description="Decision reasoning for explainability",
        schema_name="DecisionReasoning",
    ),
    
    # CDC - compacted for latest state
    ADAMTopics.CDC_USER_PROFILE: TopicConfig(
        name=ADAMTopics.CDC_USER_PROFILE.value,
        partitions=12,
        cleanup_policy="compact",
        retention_ms=-1,  # Keep forever (compacted)
        description="User profile CDC from Neo4j",
        schema_name="UserProfileCDC",
    ),
    ADAMTopics.CDC_MECHANISM: TopicConfig(
        name=ADAMTopics.CDC_MECHANISM.value,
        partitions=3,
        cleanup_policy="compact",
        retention_ms=-1,
        description="Mechanism state CDC from Neo4j",
        schema_name="MechanismCDC",
    ),
}


def get_topic_config(topic: ADAMTopics) -> TopicConfig:
    """Get configuration for a topic."""
    return TOPIC_CONFIGS.get(topic, TopicConfig(name=topic.value))
