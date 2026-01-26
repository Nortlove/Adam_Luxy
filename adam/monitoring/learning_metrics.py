# =============================================================================
# ADAM Learning Metrics Exporter
# Location: adam/monitoring/learning_metrics.py
# =============================================================================

"""
LEARNING METRICS EXPORTER

This module exports learning metrics to Prometheus for monitoring.
It provides real-time observability into:
1. Component health
2. Prediction accuracy
3. Signal flow
4. Emergence detection
5. Learning velocity
"""

from typing import Dict, Optional, Any
from prometheus_client import (
    Counter, Gauge, Histogram, Summary,
    CollectorRegistry, generate_latest, CONTENT_TYPE_LATEST,
)
import logging

logger = logging.getLogger(__name__)


# =============================================================================
# METRIC DEFINITIONS
# =============================================================================

# Create a custom registry
ADAM_REGISTRY = CollectorRegistry()

# -----------------------------------------------------------------------------
# OUTCOME METRICS
# -----------------------------------------------------------------------------

OUTCOMES_PROCESSED = Counter(
    name='adam_learning_outcomes_total',
    documentation='Total outcomes processed by learning system',
    labelnames=['component', 'outcome_type'],
    registry=ADAM_REGISTRY,
)

PREDICTIONS_MADE = Counter(
    name='adam_learning_predictions_total',
    documentation='Total predictions made',
    labelnames=['component'],
    registry=ADAM_REGISTRY,
)

PREDICTIONS_CORRECT = Counter(
    name='adam_learning_predictions_correct_total',
    documentation='Total correct predictions',
    labelnames=['component'],
    registry=ADAM_REGISTRY,
)

PREDICTION_ACCURACY = Gauge(
    name='adam_learning_prediction_accuracy',
    documentation='Current prediction accuracy (0-1)',
    labelnames=['component'],
    registry=ADAM_REGISTRY,
)

PREDICTION_ERROR = Histogram(
    name='adam_learning_prediction_error',
    documentation='Distribution of prediction errors',
    labelnames=['component'],
    buckets=[0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.4, 0.5, 0.75, 1.0],
    registry=ADAM_REGISTRY,
)

# -----------------------------------------------------------------------------
# SIGNAL METRICS
# -----------------------------------------------------------------------------

SIGNALS_EMITTED = Counter(
    name='adam_learning_signals_emitted_total',
    documentation='Total learning signals emitted',
    labelnames=['component', 'signal_type'],
    registry=ADAM_REGISTRY,
)

SIGNALS_CONSUMED = Counter(
    name='adam_learning_signals_consumed_total',
    documentation='Total learning signals consumed',
    labelnames=['component', 'signal_type'],
    registry=ADAM_REGISTRY,
)

SIGNAL_LATENCY = Histogram(
    name='adam_learning_signal_latency_seconds',
    documentation='Time to route learning signal',
    labelnames=['signal_type'],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0],
    registry=ADAM_REGISTRY,
)

# -----------------------------------------------------------------------------
# COMPONENT HEALTH METRICS
# -----------------------------------------------------------------------------

COMPONENT_HEALTH = Gauge(
    name='adam_learning_component_health',
    documentation='Component health status (1=healthy, 0=unhealthy)',
    labelnames=['component'],
    registry=ADAM_REGISTRY,
)

COMPONENT_LAST_UPDATE = Gauge(
    name='adam_learning_component_last_update_timestamp',
    documentation='Timestamp of last learning update',
    labelnames=['component'],
    registry=ADAM_REGISTRY,
)

# -----------------------------------------------------------------------------
# QUALITY DIMENSION METRICS
# -----------------------------------------------------------------------------

QUALITY_EFFECTIVENESS = Gauge(
    name='adam_learning_quality_effectiveness',
    documentation='Learning effectiveness score (0-1)',
    labelnames=['component'],
    registry=ADAM_REGISTRY,
)

QUALITY_EFFICIENCY = Gauge(
    name='adam_learning_quality_efficiency',
    documentation='Learning efficiency score (0-1)',
    labelnames=['component'],
    registry=ADAM_REGISTRY,
)

QUALITY_COHERENCE = Gauge(
    name='adam_learning_quality_coherence',
    documentation='Learning coherence score (0-1)',
    labelnames=['component'],
    registry=ADAM_REGISTRY,
)

QUALITY_FRESHNESS = Gauge(
    name='adam_learning_quality_freshness',
    documentation='Learning freshness score (0-1)',
    labelnames=['component'],
    registry=ADAM_REGISTRY,
)

QUALITY_COMPLETENESS = Gauge(
    name='adam_learning_quality_completeness',
    documentation='Learning completeness score (0-1)',
    labelnames=['component'],
    registry=ADAM_REGISTRY,
)

QUALITY_SYNERGY = Gauge(
    name='adam_learning_quality_synergy',
    documentation='Learning synergy score (0-1)',
    labelnames=['component'],
    registry=ADAM_REGISTRY,
)

QUALITY_OVERALL = Gauge(
    name='adam_learning_quality_overall',
    documentation='Overall learning quality score (0-100)',
    registry=ADAM_REGISTRY,
)

# -----------------------------------------------------------------------------
# ARCHETYPE METRICS
# -----------------------------------------------------------------------------

ARCHETYPE_USAGE = Counter(
    name='adam_learning_archetype_usage_total',
    documentation='Total times archetype was used',
    labelnames=['archetype'],
    registry=ADAM_REGISTRY,
)

ARCHETYPE_EFFECTIVENESS = Gauge(
    name='adam_learning_archetype_effectiveness',
    documentation='Archetype effectiveness score (0-1)',
    labelnames=['archetype'],
    registry=ADAM_REGISTRY,
)

# -----------------------------------------------------------------------------
# MODALITY METRICS
# -----------------------------------------------------------------------------

MODALITY_WEIGHT = Gauge(
    name='adam_learning_modality_weight',
    documentation='Current learned modality weight',
    labelnames=['modality'],
    registry=ADAM_REGISTRY,
)

MODALITY_ACCURACY = Gauge(
    name='adam_learning_modality_accuracy',
    documentation='Modality prediction accuracy',
    labelnames=['modality'],
    registry=ADAM_REGISTRY,
)

# -----------------------------------------------------------------------------
# FEATURE METRICS
# -----------------------------------------------------------------------------

FEATURES_TRACKED = Gauge(
    name='adam_learning_features_tracked',
    documentation='Number of features being tracked',
    registry=ADAM_REGISTRY,
)

FEATURES_PRUNED = Counter(
    name='adam_learning_features_pruned_total',
    documentation='Total features pruned for ineffectiveness',
    registry=ADAM_REGISTRY,
)

FEATURE_IMPORTANCE = Gauge(
    name='adam_learning_feature_importance',
    documentation='Learned feature importance',
    labelnames=['feature_name', 'category'],
    registry=ADAM_REGISTRY,
)

# -----------------------------------------------------------------------------
# TEMPORAL METRICS
# -----------------------------------------------------------------------------

TIMING_CONVERSIONS = Counter(
    name='adam_learning_timing_conversions_total',
    documentation='Conversions by timing slot',
    labelnames=['hour', 'day'],
    registry=ADAM_REGISTRY,
)

TIMING_IMPRESSIONS = Counter(
    name='adam_learning_timing_impressions_total',
    documentation='Impressions by timing slot',
    labelnames=['hour', 'day'],
    registry=ADAM_REGISTRY,
)

TIMING_LIFT = Gauge(
    name='adam_learning_timing_lift',
    documentation='Conversion lift vs baseline for timing slot',
    labelnames=['hour', 'day'],
    registry=ADAM_REGISTRY,
)

# -----------------------------------------------------------------------------
# EMERGENCE METRICS
# -----------------------------------------------------------------------------

DISCOVERIES_MADE = Counter(
    name='adam_learning_discoveries_total',
    documentation='Total emergent discoveries made',
    labelnames=['emergence_type', 'confidence'],
    registry=ADAM_REGISTRY,
)

ACTIVE_DISCOVERIES = Gauge(
    name='adam_learning_active_discoveries',
    documentation='Number of active validated discoveries',
    labelnames=['emergence_type'],
    registry=ADAM_REGISTRY,
)

# -----------------------------------------------------------------------------
# VERIFICATION METRICS
# -----------------------------------------------------------------------------

VERIFICATIONS_PERFORMED = Counter(
    name='adam_learning_verifications_total',
    documentation='Total verifications performed',
    labelnames=['verification_type', 'passed'],
    registry=ADAM_REGISTRY,
)

PROMPT_ADJUSTMENTS = Counter(
    name='adam_learning_prompt_adjustments_total',
    documentation='Total prompt adjustments made',
    labelnames=['atom_name', 'adjustment_type'],
    registry=ADAM_REGISTRY,
)

PROMPT_ADJUSTMENT_EFFECTIVENESS = Gauge(
    name='adam_learning_prompt_adjustment_effectiveness',
    documentation='Effectiveness of prompt adjustments (0-1)',
    labelnames=['atom_name'],
    registry=ADAM_REGISTRY,
)

# -----------------------------------------------------------------------------
# COLD START METRICS
# -----------------------------------------------------------------------------

TIER_DISTRIBUTION = Gauge(
    name='adam_learning_user_tier_count',
    documentation='Number of users in each tier',
    labelnames=['tier'],
    registry=ADAM_REGISTRY,
)

TIER_TRANSITIONS = Counter(
    name='adam_learning_tier_transitions_total',
    documentation='Total tier transitions',
    labelnames=['from_tier', 'to_tier'],
    registry=ADAM_REGISTRY,
)

INFERENCE_ACCURACY_BY_TIER = Gauge(
    name='adam_learning_inference_accuracy_by_tier',
    documentation='Personality inference accuracy by tier',
    labelnames=['tier'],
    registry=ADAM_REGISTRY,
)


# =============================================================================
# METRICS UPDATER
# =============================================================================

class LearningMetricsExporter:
    """
    Exports learning metrics to Prometheus.
    
    This class collects metrics from all learning components
    and exposes them for scraping.
    """
    
    def __init__(self):
        self.registry = ADAM_REGISTRY
    
    def record_outcome(
        self,
        component: str,
        outcome_type: str,
        prediction: float,
        actual: float,
    ):
        """Record an outcome for a component."""
        
        OUTCOMES_PROCESSED.labels(
            component=component,
            outcome_type=outcome_type,
        ).inc()
        
        PREDICTIONS_MADE.labels(component=component).inc()
        
        error = abs(prediction - actual)
        was_correct = error < 0.3
        
        if was_correct:
            PREDICTIONS_CORRECT.labels(component=component).inc()
        
        PREDICTION_ERROR.labels(component=component).observe(error)
    
    def update_accuracy(self, component: str, accuracy: float):
        """Update prediction accuracy for a component."""
        PREDICTION_ACCURACY.labels(component=component).set(accuracy)
    
    def record_signal(
        self,
        source_component: str,
        signal_type: str,
        target_components: list,
        latency_seconds: float,
    ):
        """Record a learning signal."""
        
        SIGNALS_EMITTED.labels(
            component=source_component,
            signal_type=signal_type,
        ).inc()
        
        for target in target_components:
            SIGNALS_CONSUMED.labels(
                component=target,
                signal_type=signal_type,
            ).inc()
        
        SIGNAL_LATENCY.labels(signal_type=signal_type).observe(latency_seconds)
    
    def update_component_health(self, component: str, is_healthy: bool):
        """Update component health status."""
        COMPONENT_HEALTH.labels(component=component).set(1 if is_healthy else 0)
    
    def update_component_timestamp(self, component: str, timestamp: float):
        """Update component last update timestamp."""
        COMPONENT_LAST_UPDATE.labels(component=component).set(timestamp)
    
    def update_quality_dimensions(
        self,
        component: str,
        effectiveness: float,
        efficiency: float,
        coherence: float,
        freshness: float,
        completeness: float,
        synergy: float,
    ):
        """Update quality dimension scores for a component."""
        
        QUALITY_EFFECTIVENESS.labels(component=component).set(effectiveness)
        QUALITY_EFFICIENCY.labels(component=component).set(efficiency)
        QUALITY_COHERENCE.labels(component=component).set(coherence)
        QUALITY_FRESHNESS.labels(component=component).set(freshness)
        QUALITY_COMPLETENESS.labels(component=component).set(completeness)
        QUALITY_SYNERGY.labels(component=component).set(synergy)
    
    def update_overall_quality(self, score: float):
        """Update overall quality score."""
        QUALITY_OVERALL.set(score)
    
    def record_archetype_usage(self, archetype: str, effectiveness: float):
        """Record archetype usage and effectiveness."""
        ARCHETYPE_USAGE.labels(archetype=archetype).inc()
        ARCHETYPE_EFFECTIVENESS.labels(archetype=archetype).set(effectiveness)
    
    def update_modality_metrics(
        self,
        weights: Dict[str, float],
        accuracies: Dict[str, float],
    ):
        """Update modality metrics."""
        
        for modality, weight in weights.items():
            MODALITY_WEIGHT.labels(modality=modality).set(weight)
        
        for modality, accuracy in accuracies.items():
            MODALITY_ACCURACY.labels(modality=modality).set(accuracy)
    
    def update_feature_metrics(
        self,
        total_tracked: int,
        top_features: list,
    ):
        """Update feature store metrics."""
        
        FEATURES_TRACKED.set(total_tracked)
        
        for feature in top_features:
            FEATURE_IMPORTANCE.labels(
                feature_name=feature["name"],
                category=feature.get("category", "unknown"),
            ).set(feature["importance"])
    
    def record_feature_pruned(self):
        """Record a feature being pruned."""
        FEATURES_PRUNED.inc()
    
    def record_timing_outcome(
        self,
        hour: int,
        day: int,
        converted: bool,
        lift: float,
    ):
        """Record timing outcome."""
        
        TIMING_IMPRESSIONS.labels(hour=str(hour), day=str(day)).inc()
        
        if converted:
            TIMING_CONVERSIONS.labels(hour=str(hour), day=str(day)).inc()
        
        TIMING_LIFT.labels(hour=str(hour), day=str(day)).set(lift)
    
    def record_discovery(
        self,
        emergence_type: str,
        confidence: str,
    ):
        """Record an emergent discovery."""
        
        DISCOVERIES_MADE.labels(
            emergence_type=emergence_type,
            confidence=confidence,
        ).inc()
    
    def update_active_discoveries(self, by_type: Dict[str, int]):
        """Update active discovery counts."""
        
        for emergence_type, count in by_type.items():
            ACTIVE_DISCOVERIES.labels(emergence_type=emergence_type).set(count)
    
    def record_verification(
        self,
        verification_type: str,
        passed: bool,
    ):
        """Record a verification result."""
        
        VERIFICATIONS_PERFORMED.labels(
            verification_type=verification_type,
            passed=str(passed).lower(),
        ).inc()
    
    def record_prompt_adjustment(
        self,
        atom_name: str,
        adjustment_type: str,
        effectiveness: Optional[float] = None,
    ):
        """Record a prompt adjustment."""
        
        PROMPT_ADJUSTMENTS.labels(
            atom_name=atom_name,
            adjustment_type=adjustment_type,
        ).inc()
        
        if effectiveness is not None:
            PROMPT_ADJUSTMENT_EFFECTIVENESS.labels(
                atom_name=atom_name,
            ).set(effectiveness)
    
    def update_tier_distribution(self, distribution: Dict[str, int]):
        """Update user tier distribution."""
        
        for tier, count in distribution.items():
            TIER_DISTRIBUTION.labels(tier=tier).set(count)
    
    def record_tier_transition(self, from_tier: str, to_tier: str):
        """Record a tier transition."""
        
        TIER_TRANSITIONS.labels(
            from_tier=from_tier,
            to_tier=to_tier,
        ).inc()
    
    def update_inference_accuracy(self, by_tier: Dict[str, float]):
        """Update inference accuracy by tier."""
        
        for tier, accuracy in by_tier.items():
            INFERENCE_ACCURACY_BY_TIER.labels(tier=tier).set(accuracy)
    
    def get_metrics(self) -> bytes:
        """Get metrics in Prometheus format."""
        return generate_latest(self.registry)
    
    def get_content_type(self) -> str:
        """Get Prometheus content type."""
        return CONTENT_TYPE_LATEST


# Singleton instance
metrics_exporter = LearningMetricsExporter()
