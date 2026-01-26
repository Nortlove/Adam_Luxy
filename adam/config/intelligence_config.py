# =============================================================================
# ADAM Configuration: Intelligence Engine Configuration
# Location: adam/config/intelligence_config.py
# =============================================================================

"""
INTELLIGENCE ENGINE CONFIGURATION

Centralized configuration for all emergent intelligence components.

Environment Variables:
- Feature flags for gradual rollout
- Engine-specific parameters
- Prometheus metrics configuration
"""

import os
from dataclasses import dataclass, field
from typing import Optional


# =============================================================================
# FEATURE FLAGS
# =============================================================================

@dataclass
class FeatureFlags:
    """Feature flags for gradual rollout of new capabilities."""
    
    # Neural Thompson Sampling
    use_neural_thompson: bool = field(
        default_factory=lambda: os.getenv("ADAM_USE_NEURAL_THOMPSON", "true").lower() == "true"
    )
    
    # Predictive Processing (curiosity-driven selection)
    use_predictive_processing: bool = field(
        default_factory=lambda: os.getenv("ADAM_USE_PREDICTIVE_PROCESSING", "true").lower() == "true"
    )
    
    # Emergence Engine (novel construct discovery)
    use_emergence_engine: bool = field(
        default_factory=lambda: os.getenv("ADAM_USE_EMERGENCE_ENGINE", "true").lower() == "true"
    )
    
    # Causal Discovery
    use_causal_discovery: bool = field(
        default_factory=lambda: os.getenv("ADAM_USE_CAUSAL_DISCOVERY", "false").lower() == "true"
    )
    
    # Streaming Synthesis
    use_streaming_synthesis: bool = field(
        default_factory=lambda: os.getenv("ADAM_USE_STREAMING_SYNTHESIS", "true").lower() == "true"
    )
    
    # GDS Algorithms
    use_gds_algorithms: bool = field(
        default_factory=lambda: os.getenv("ADAM_USE_GDS_ALGORITHMS", "true").lower() == "true"
    )
    
    # Circuit Breakers
    use_circuit_breakers: bool = field(
        default_factory=lambda: os.getenv("ADAM_USE_CIRCUIT_BREAKERS", "true").lower() == "true"
    )


# =============================================================================
# ENGINE CONFIGURATIONS
# =============================================================================

@dataclass
class NeuralThompsonConfig:
    """Configuration for Neural Thompson Sampling."""
    
    context_dim: int = field(
        default_factory=lambda: int(os.getenv("ADAM_NEURAL_THOMPSON_CONTEXT_DIM", "32"))
    )
    hidden_dim: int = field(
        default_factory=lambda: int(os.getenv("ADAM_NEURAL_THOMPSON_HIDDEN_DIM", "64"))
    )
    num_heads: int = field(
        default_factory=lambda: int(os.getenv("ADAM_NEURAL_THOMPSON_NUM_HEADS", "5"))
    )
    learning_rate: float = field(
        default_factory=lambda: float(os.getenv("ADAM_NEURAL_THOMPSON_LR", "0.01"))
    )
    exploration_bonus_base: float = field(
        default_factory=lambda: float(os.getenv("ADAM_NEURAL_THOMPSON_EXPLORATION", "0.1"))
    )


@dataclass
class EmergenceEngineConfig:
    """Configuration for Emergence Engine."""
    
    residual_threshold: float = field(
        default_factory=lambda: float(os.getenv("ADAM_EMERGENCE_RESIDUAL_THRESHOLD", "0.3"))
    )
    min_samples_for_cluster: int = field(
        default_factory=lambda: int(os.getenv("ADAM_EMERGENCE_MIN_SAMPLES", "50"))
    )
    min_predictive_lift: float = field(
        default_factory=lambda: float(os.getenv("ADAM_EMERGENCE_MIN_LIFT", "0.05"))
    )
    promotion_confidence_threshold: float = field(
        default_factory=lambda: float(os.getenv("ADAM_EMERGENCE_PROMOTION_CONFIDENCE", "0.8"))
    )


@dataclass
class PredictiveProcessingConfig:
    """Configuration for Predictive Processing."""
    
    prediction_error_threshold: float = field(
        default_factory=lambda: float(os.getenv("ADAM_PP_ERROR_THRESHOLD", "0.2"))
    )
    curiosity_weight: float = field(
        default_factory=lambda: float(os.getenv("ADAM_PP_CURIOSITY_WEIGHT", "0.3"))
    )
    pragmatic_weight: float = field(
        default_factory=lambda: float(os.getenv("ADAM_PP_PRAGMATIC_WEIGHT", "0.7"))
    )


@dataclass
class StreamingSynthesisConfig:
    """Configuration for Streaming Synthesis."""
    
    early_exit_confidence: float = field(
        default_factory=lambda: float(os.getenv("ADAM_STREAMING_EARLY_EXIT", "0.85"))
    )
    max_wait_ms: float = field(
        default_factory=lambda: float(os.getenv("ADAM_STREAMING_MAX_WAIT_MS", "2000"))
    )
    min_contexts_for_synthesis: int = field(
        default_factory=lambda: int(os.getenv("ADAM_STREAMING_MIN_CONTEXTS", "3"))
    )


@dataclass
class CircuitBreakerConfig:
    """Configuration for Circuit Breakers."""
    
    neo4j_failure_threshold: int = field(
        default_factory=lambda: int(os.getenv("ADAM_CB_NEO4J_FAILURES", "3"))
    )
    redis_failure_threshold: int = field(
        default_factory=lambda: int(os.getenv("ADAM_CB_REDIS_FAILURES", "5"))
    )
    kafka_failure_threshold: int = field(
        default_factory=lambda: int(os.getenv("ADAM_CB_KAFKA_FAILURES", "5"))
    )
    llm_failure_threshold: int = field(
        default_factory=lambda: int(os.getenv("ADAM_CB_LLM_FAILURES", "2"))
    )
    recovery_timeout_seconds: float = field(
        default_factory=lambda: float(os.getenv("ADAM_CB_RECOVERY_TIMEOUT", "30"))
    )


# =============================================================================
# MASTER CONFIGURATION
# =============================================================================

@dataclass
class IntelligenceConfig:
    """Master configuration for all intelligence components."""
    
    feature_flags: FeatureFlags = field(default_factory=FeatureFlags)
    neural_thompson: NeuralThompsonConfig = field(default_factory=NeuralThompsonConfig)
    emergence: EmergenceEngineConfig = field(default_factory=EmergenceEngineConfig)
    predictive_processing: PredictiveProcessingConfig = field(default_factory=PredictiveProcessingConfig)
    streaming_synthesis: StreamingSynthesisConfig = field(default_factory=StreamingSynthesisConfig)
    circuit_breaker: CircuitBreakerConfig = field(default_factory=CircuitBreakerConfig)


# Singleton
_config: Optional[IntelligenceConfig] = None


def get_intelligence_config() -> IntelligenceConfig:
    """Get singleton intelligence configuration."""
    global _config
    if _config is None:
        _config = IntelligenceConfig()
    return _config


# =============================================================================
# PROMETHEUS METRICS
# =============================================================================

# Note: These are metric definitions. Actual Prometheus client integration
# would use prometheus_client library.

METRICS_DEFINITIONS = {
    # Neural Thompson Sampling
    "adam_neural_thompson_selections_total": {
        "type": "counter",
        "description": "Total modality selections by Neural Thompson",
        "labels": ["modality", "path"],
    },
    "adam_neural_thompson_uncertainty": {
        "type": "histogram",
        "description": "Uncertainty distribution of Neural Thompson selections",
        "buckets": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
    },
    "adam_neural_thompson_calibration": {
        "type": "gauge",
        "description": "Calibration score of Neural Thompson (1.0 = perfect)",
    },
    
    # Emergence Engine
    "adam_emergence_anomalies_total": {
        "type": "counter",
        "description": "Total anomalies detected by Emergence Engine",
    },
    "adam_emergence_constructs_discovered": {
        "type": "counter",
        "description": "Constructs discovered by status",
        "labels": ["status"],  # candidate, validated, promoted
    },
    "adam_emergence_predictive_lift": {
        "type": "histogram",
        "description": "Predictive lift of discovered constructs",
        "buckets": [0.01, 0.05, 0.1, 0.15, 0.2, 0.3, 0.5],
    },
    
    # Predictive Processing
    "adam_predictive_curiosity_score": {
        "type": "histogram",
        "description": "Distribution of curiosity scores",
        "buckets": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
    },
    "adam_predictive_belief_uncertainty": {
        "type": "gauge",
        "description": "Average belief uncertainty across users",
    },
    "adam_predictive_surprise_rate": {
        "type": "gauge",
        "description": "Rate of surprising predictions",
    },
    
    # Streaming Synthesis
    "adam_streaming_early_exits_total": {
        "type": "counter",
        "description": "Total early exits from streaming synthesis",
    },
    "adam_streaming_latency_ms": {
        "type": "histogram",
        "description": "Latency of streaming synthesis in ms",
        "buckets": [100, 200, 500, 1000, 1500, 2000, 3000],
    },
    "adam_streaming_contexts_used": {
        "type": "histogram",
        "description": "Number of contexts used before decision",
        "buckets": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
    },
    
    # Circuit Breakers
    "adam_circuit_breaker_state": {
        "type": "gauge",
        "description": "Circuit breaker state (0=closed, 1=half-open, 2=open)",
        "labels": ["service"],
    },
    "adam_circuit_breaker_failures_total": {
        "type": "counter",
        "description": "Total failures per circuit breaker",
        "labels": ["service"],
    },
    "adam_circuit_breaker_rejections_total": {
        "type": "counter",
        "description": "Total rejections due to open circuit",
        "labels": ["service"],
    },
    
    # Causal Discovery
    "adam_causal_edges_discovered": {
        "type": "gauge",
        "description": "Number of causal edges in the graph",
    },
    "adam_causal_effects_estimated": {
        "type": "counter",
        "description": "Total causal effect estimations performed",
    },
    "adam_causal_ate_distribution": {
        "type": "histogram",
        "description": "Distribution of Average Treatment Effects",
        "buckets": [-0.5, -0.3, -0.1, 0.0, 0.1, 0.3, 0.5],
    },
    
    # GDS Algorithms
    "adam_gds_pagerank_runs": {
        "type": "counter",
        "description": "Total PageRank algorithm runs",
    },
    "adam_gds_community_count": {
        "type": "gauge",
        "description": "Number of communities detected",
    },
    "adam_gds_embeddings_generated": {
        "type": "counter",
        "description": "Total node embeddings generated",
    },
}


def get_metrics_definitions() -> dict:
    """Get Prometheus metrics definitions."""
    return METRICS_DEFINITIONS
