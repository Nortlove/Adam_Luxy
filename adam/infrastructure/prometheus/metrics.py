# =============================================================================
# ADAM Prometheus Metrics
# Location: adam/infrastructure/prometheus/metrics.py
# =============================================================================

"""
ADAM PROMETHEUS METRICS

Custom metrics for psychological intelligence observability.
These metrics track both technical performance and psychological effectiveness.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Global metrics instance
_metrics: Optional["ADAMMetrics"] = None


def get_metrics() -> "ADAMMetrics":
    """Get or create the global metrics instance."""
    global _metrics
    if _metrics is None:
        _metrics = ADAMMetrics()
    return _metrics


class ADAMMetrics:
    """
    ADAM Prometheus metrics collector.
    
    Provides metrics for:
    - Decision latency and throughput
    - Mechanism effectiveness
    - Profile updates
    - Learning signals
    - Infrastructure health
    """
    
    def __init__(self):
        self._initialized = False
        self._init_metrics()
    
    def _init_metrics(self) -> None:
        """Initialize all Prometheus metrics."""
        try:
            from prometheus_client import Counter, Histogram, Gauge, Summary
            
            # -----------------------------------------------------------------
            # DECISION METRICS
            # -----------------------------------------------------------------
            
            # Decision latency
            self.decision_latency = Histogram(
                "adam_decision_latency_seconds",
                "Time to make an ad decision",
                ["decision_type", "mechanism"],
                buckets=[0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
            )
            
            # Decision count
            self.decisions_total = Counter(
                "adam_decisions_total",
                "Total number of ad decisions",
                ["decision_type", "outcome", "station_format"],
            )
            
            # Decision confidence
            self.decision_confidence = Histogram(
                "adam_decision_confidence",
                "Confidence in ad decisions",
                ["decision_type", "mechanism"],
                buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
            )
            
            # Active decisions in flight
            self.decisions_in_flight = Gauge(
                "adam_decisions_in_flight",
                "Number of decisions currently being processed",
            )
            
            # -----------------------------------------------------------------
            # MECHANISM METRICS
            # -----------------------------------------------------------------
            
            # Mechanism activation count
            self.mechanism_activations = Counter(
                "adam_mechanism_activations_total",
                "Total mechanism activations",
                ["mechanism_id", "mechanism_name"],
            )
            
            # Mechanism effectiveness
            self.mechanism_effectiveness = Histogram(
                "adam_mechanism_effectiveness",
                "Observed mechanism effectiveness",
                ["mechanism_id", "mechanism_name", "context"],
                buckets=[0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
            )
            
            # Mechanism selection rate
            self.mechanism_selection_rate = Gauge(
                "adam_mechanism_selection_rate",
                "Rate at which each mechanism is selected",
                ["mechanism_id", "mechanism_name"],
            )
            
            # -----------------------------------------------------------------
            # PROFILE METRICS
            # -----------------------------------------------------------------
            
            # Profile lookups
            self.profile_lookups = Counter(
                "adam_profile_lookups_total",
                "Total profile lookups",
                ["cache_hit", "source"],
            )
            
            # Profile update latency
            self.profile_update_latency = Histogram(
                "adam_profile_update_latency_seconds",
                "Time to update a user profile",
                ["update_type"],
                buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0],
            )
            
            # Profile updates
            self.profile_updates = Counter(
                "adam_profile_updates_total",
                "Total profile updates",
                ["update_type", "source"],
            )
            
            # Big Five distribution (for monitoring drift)
            self.big_five_distribution = Histogram(
                "adam_big_five_distribution",
                "Distribution of Big Five values across users",
                ["trait"],
                buckets=[0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
            )
            
            # -----------------------------------------------------------------
            # LEARNING METRICS
            # -----------------------------------------------------------------
            
            # Learning signals emitted
            self.learning_signals = Counter(
                "adam_learning_signals_total",
                "Total learning signals emitted",
                ["signal_type", "component"],
            )
            
            # Signal processing latency
            self.signal_processing_latency = Histogram(
                "adam_signal_processing_latency_seconds",
                "Time to process a learning signal",
                ["signal_type"],
                buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5],
            )
            
            # Learning rate (gradient updates)
            self.learning_rate = Gauge(
                "adam_learning_rate",
                "Current learning rate for each component",
                ["component"],
            )
            
            # -----------------------------------------------------------------
            # INFERENCE METRICS
            # -----------------------------------------------------------------
            
            # Inference latency by component
            self.inference_latency = Histogram(
                "adam_inference_latency_seconds",
                "Inference latency by component",
                ["component", "operation"],
                buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0],
            )
            
            # Cache hit rate
            self.cache_hit_rate = Gauge(
                "adam_cache_hit_rate",
                "Cache hit rate by domain",
                ["domain"],
            )
            
            # -----------------------------------------------------------------
            # META-LEARNER METRICS
            # -----------------------------------------------------------------
            
            # Modality selection count
            self.meta_learner_selections = Counter(
                "adam_meta_learner_selections_total",
                "Total modality selections",
                ["modality", "path"],
            )
            
            # Modality selection latency
            self.meta_learner_latency = Histogram(
                "adam_meta_learner_latency_seconds",
                "Meta-learner routing latency",
                buckets=[0.001, 0.005, 0.01, 0.025, 0.05],
            )
            
            # Posterior updates
            self.meta_learner_updates = Counter(
                "adam_meta_learner_updates_total",
                "Total posterior updates",
                ["modality", "reward_bin"],
            )
            
            # Exploration count
            self.meta_learner_explorations = Counter(
                "adam_meta_learner_explorations_total",
                "Total exploration decisions",
            )
            
            # Posterior mean by modality
            self.meta_learner_posterior_mean = Gauge(
                "adam_meta_learner_posterior_mean",
                "Current posterior mean by modality",
                ["modality"],
            )
            
            # -----------------------------------------------------------------
            # INFRASTRUCTURE METRICS
            # -----------------------------------------------------------------
            
            # Neo4j query latency
            self.neo4j_latency = Histogram(
                "adam_neo4j_query_latency_seconds",
                "Neo4j query latency",
                ["query_type"],
                buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5],
            )
            
            # Redis latency
            self.redis_latency = Histogram(
                "adam_redis_latency_seconds",
                "Redis operation latency",
                ["operation"],
                buckets=[0.0001, 0.0005, 0.001, 0.005, 0.01, 0.025, 0.05],
            )
            
            # Kafka message latency
            self.kafka_latency = Histogram(
                "adam_kafka_latency_seconds",
                "Kafka publish latency",
                ["topic"],
                buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1],
            )
            
            # -----------------------------------------------------------------
            # PLATFORM METRICS
            # -----------------------------------------------------------------
            
            # iHeart sessions
            self.iheart_sessions = Gauge(
                "adam_iheart_active_sessions",
                "Number of active iHeart sessions",
            )
            
            # iHeart events processed
            self.iheart_events = Counter(
                "adam_iheart_events_total",
                "Total iHeart events processed",
                ["event_type"],
            )
            
            # Ad outcomes
            self.ad_outcomes = Counter(
                "adam_ad_outcomes_total",
                "Total ad outcomes by type",
                ["outcome_type", "station_format"],
            )
            
            # Click-through rate (recent window)
            self.click_through_rate = Gauge(
                "adam_click_through_rate",
                "Recent click-through rate",
                ["station_format"],
            )
            
            self._initialized = True
            logger.info("ADAM Prometheus metrics initialized")
            
        except ImportError:
            logger.warning("prometheus_client not installed, metrics disabled")
            self._initialized = False
    
    # -------------------------------------------------------------------------
    # CONVENIENCE METHODS
    # -------------------------------------------------------------------------
    
    def record_decision(
        self,
        decision_type: str,
        latency_seconds: float,
        mechanism: str,
        confidence: float,
        outcome: str = "pending",
        station_format: str = "unknown",
    ) -> None:
        """Record a decision with all associated metrics."""
        if not self._initialized:
            return
        
        self.decision_latency.labels(
            decision_type=decision_type,
            mechanism=mechanism,
        ).observe(latency_seconds)
        
        self.decisions_total.labels(
            decision_type=decision_type,
            outcome=outcome,
            station_format=station_format,
        ).inc()
        
        self.decision_confidence.labels(
            decision_type=decision_type,
            mechanism=mechanism,
        ).observe(confidence)
    
    def record_mechanism_activation(
        self,
        mechanism_id: str,
        mechanism_name: str,
        effectiveness: Optional[float] = None,
        context: str = "default",
    ) -> None:
        """Record a mechanism activation."""
        if not self._initialized:
            return
        
        self.mechanism_activations.labels(
            mechanism_id=mechanism_id,
            mechanism_name=mechanism_name,
        ).inc()
        
        if effectiveness is not None:
            self.mechanism_effectiveness.labels(
                mechanism_id=mechanism_id,
                mechanism_name=mechanism_name,
                context=context,
            ).observe(effectiveness)
    
    def record_profile_lookup(
        self,
        cache_hit: bool,
        source: str = "redis",
    ) -> None:
        """Record a profile lookup."""
        if not self._initialized:
            return
        
        self.profile_lookups.labels(
            cache_hit=str(cache_hit).lower(),
            source=source,
        ).inc()
    
    def record_profile_update(
        self,
        update_type: str,
        latency_seconds: float,
        source: str = "learning",
    ) -> None:
        """Record a profile update."""
        if not self._initialized:
            return
        
        self.profile_updates.labels(
            update_type=update_type,
            source=source,
        ).inc()
        
        self.profile_update_latency.labels(
            update_type=update_type,
        ).observe(latency_seconds)
    
    def record_learning_signal(
        self,
        signal_type: str,
        component: str,
        processing_latency: Optional[float] = None,
    ) -> None:
        """Record a learning signal."""
        if not self._initialized:
            return
        
        self.learning_signals.labels(
            signal_type=signal_type,
            component=component,
        ).inc()
        
        if processing_latency is not None:
            self.signal_processing_latency.labels(
                signal_type=signal_type,
            ).observe(processing_latency)
    
    def record_inference(
        self,
        component: str,
        operation: str,
        latency_seconds: float,
    ) -> None:
        """Record inference latency."""
        if not self._initialized:
            return
        
        self.inference_latency.labels(
            component=component,
            operation=operation,
        ).observe(latency_seconds)
    
    def record_ad_outcome(
        self,
        outcome_type: str,
        station_format: str = "unknown",
    ) -> None:
        """Record an ad outcome."""
        if not self._initialized:
            return
        
        self.ad_outcomes.labels(
            outcome_type=outcome_type,
            station_format=station_format,
        ).inc()
