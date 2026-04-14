# =============================================================================
# ADAM Platform Configuration
# Location: adam/config/settings.py
# =============================================================================

"""
ADAM CONFIGURATION MANAGEMENT

Centralized configuration using Pydantic Settings.
All configuration is loaded from environment variables with sensible defaults.
"""

from typing import Optional, List
from pydantic import Field
from pydantic_settings import BaseSettings
from functools import lru_cache


class Neo4jSettings(BaseSettings):
    """Neo4j database configuration."""
    
    uri: str = Field(default="bolt://127.0.0.1:7687", env="NEO4J_URI")
    username: str = Field(default="neo4j", env="NEO4J_USERNAME")
    password: str = Field(default="atomofthought", env="NEO4J_PASSWORD")
    database: str = Field(default="neo4j", env="NEO4J_DATABASE")
    max_connection_pool_size: int = Field(default=50, env="NEO4J_POOL_SIZE")
    
    class Config:
        env_prefix = "NEO4J_"
        env_file = ".env"
        extra = "ignore"


class RedisSettings(BaseSettings):
    """Redis cache configuration."""
    
    host: str = Field(default="localhost", env="REDIS_HOST")
    port: int = Field(default=6379, env="REDIS_PORT")
    password: Optional[str] = Field(default=None, env="REDIS_PASSWORD")
    db: int = Field(default=0, env="REDIS_DB")
    ssl: bool = Field(default=False, env="REDIS_SSL")
    
    # Connection pool
    max_connections: int = Field(default=100, env="REDIS_MAX_CONNECTIONS")
    
    # Timeouts
    socket_timeout: float = Field(default=5.0, env="REDIS_SOCKET_TIMEOUT")
    socket_connect_timeout: float = Field(default=5.0, env="REDIS_CONNECT_TIMEOUT")
    
    @property
    def url(self) -> str:
        """Get Redis URL."""
        protocol = "rediss" if self.ssl else "redis"
        auth = f":{self.password}@" if self.password else ""
        return f"{protocol}://{auth}{self.host}:{self.port}/{self.db}"
    
    class Config:
        env_prefix = "REDIS_"


class KafkaSettings(BaseSettings):
    """Kafka event bus configuration."""
    
    bootstrap_servers: str = Field(
        default="localhost:9092",
        env="KAFKA_BOOTSTRAP_SERVERS"
    )
    security_protocol: str = Field(default="PLAINTEXT", env="KAFKA_SECURITY_PROTOCOL")
    
    # Topics
    learning_signals_topic: str = Field(
        default="adam.learning.signals",
        env="KAFKA_LEARNING_SIGNALS_TOPIC"
    )
    outcomes_topic: str = Field(
        default="adam.outcomes",
        env="KAFKA_OUTCOMES_TOPIC"
    )
    decisions_topic: str = Field(
        default="adam.decisions",
        env="KAFKA_DECISIONS_TOPIC"
    )
    
    # Consumer
    consumer_group: str = Field(default="adam-learning", env="KAFKA_CONSUMER_GROUP")
    auto_offset_reset: str = Field(default="latest", env="KAFKA_AUTO_OFFSET_RESET")
    
    class Config:
        env_prefix = "KAFKA_"


class ClaudeSettings(BaseSettings):
    """Anthropic Claude API configuration."""
    
    api_key: str = Field(default="", env="ANTHROPIC_API_KEY")
    model: str = Field(default="claude-sonnet-4-20250514", env="CLAUDE_MODEL")
    max_tokens: int = Field(default=4096, env="CLAUDE_MAX_TOKENS")
    temperature: float = Field(default=0.7, env="CLAUDE_TEMPERATURE")
    
    # Rate limiting
    requests_per_minute: int = Field(default=50, env="CLAUDE_RPM")
    tokens_per_minute: int = Field(default=100000, env="CLAUDE_TPM")
    
    # Timeout
    timeout_seconds: float = Field(default=60.0, env="CLAUDE_TIMEOUT")
    
    class Config:
        env_prefix = "CLAUDE_"


class LearningSettings(BaseSettings):
    """Learning system configuration."""
    
    # Signal routing
    signal_batch_size: int = Field(default=100, env="LEARNING_SIGNAL_BATCH_SIZE")
    signal_flush_interval_ms: int = Field(default=1000, env="LEARNING_SIGNAL_FLUSH_MS")
    
    # Outcome processing
    outcome_ttl_days: int = Field(default=30, env="LEARNING_OUTCOME_TTL_DAYS")
    
    # Cold start
    cold_to_developing_threshold: int = Field(default=3, env="COLD_TO_DEVELOPING_THRESHOLD")
    developing_to_established_threshold: int = Field(default=10, env="DEVELOPING_TO_ESTABLISHED_THRESHOLD")
    established_to_full_threshold: int = Field(default=25, env="ESTABLISHED_TO_FULL_THRESHOLD")
    
    # Multimodal fusion
    modality_weight_learning_rate: float = Field(default=0.05, env="MODALITY_LEARNING_RATE")
    
    # Feature store
    feature_pruning_threshold: float = Field(default=0.5, env="FEATURE_PRUNE_THRESHOLD")
    feature_min_samples: int = Field(default=50, env="FEATURE_MIN_SAMPLES")
    
    # Emergence detection
    emergence_pattern_min_samples: int = Field(default=20, env="EMERGENCE_MIN_SAMPLES")
    emergence_effect_size_threshold: float = Field(default=0.1, env="EMERGENCE_EFFECT_THRESHOLD")
    
    # Verification
    verification_failure_threshold: float = Field(default=0.15, env="VERIFICATION_FAILURE_THRESHOLD")
    prompt_adjustment_cooldown_days: int = Field(default=7, env="PROMPT_ADJUST_COOLDOWN_DAYS")
    
    class Config:
        env_prefix = "LEARNING_"


class MetricsSettings(BaseSettings):
    """Metrics and monitoring configuration."""
    
    enabled: bool = Field(default=True, env="METRICS_ENABLED")
    port: int = Field(default=9090, env="METRICS_PORT")
    
    # Prometheus
    prometheus_pushgateway: Optional[str] = Field(
        default=None,
        env="PROMETHEUS_PUSHGATEWAY"
    )
    
    # Histogram buckets
    latency_buckets: List[float] = Field(
        default=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
        env="METRICS_LATENCY_BUCKETS"
    )
    
    class Config:
        env_prefix = "METRICS_"


class StackAdaptSettings(BaseSettings):
    """StackAdapt integration configuration."""

    webhook_secret: str = Field(default="", env="STACKADAPT_WEBHOOK_SECRET")

    class Config:
        env_prefix = "STACKADAPT_"


class APISettings(BaseSettings):
    """API server configuration."""

    host: str = Field(default="0.0.0.0", env="API_HOST")
    port: int = Field(default=8000, env="API_PORT")
    
    # CORS
    cors_origins: List[str] = Field(
        default=[
            "http://localhost:3000", "http://localhost:8080",
            "https://luxyride.com", "https://www.luxyride.com",
        ],
        env="CORS_ORIGINS"
    )
    
    # Rate limiting
    rate_limit_per_minute: int = Field(default=1000, env="RATE_LIMIT_PER_MINUTE")
    
    # Authentication
    api_key_header: str = Field(default="X-API-Key", env="API_KEY_HEADER")
    api_keys: str = Field(
        default="",
        validation_alias="ADAM_API_KEYS",
        description="Comma-separated list of valid API keys. Empty = auth disabled.",
    )

    # Docs
    docs_enabled: bool = Field(default=True, env="DOCS_ENABLED")

    @property
    def api_key_set(self) -> set:
        """Parse comma-separated API keys into a set for O(1) lookup."""
        if not self.api_keys:
            return set()
        return {k.strip() for k in self.api_keys.split(",") if k.strip()}
    
    class Config:
        env_prefix = "API_"


class TTLSettings(BaseSettings):
    """
    Centralized TTL (Time-To-Live) configuration.
    
    All cache TTLs and expiration times should be configured here
    rather than hardcoded throughout the codebase.
    """
    
    # Cache TTLs (seconds)
    user_profile_ttl: int = Field(default=3600, env="TTL_USER_PROFILE")  # 1 hour
    mechanism_history_ttl: int = Field(default=1800, env="TTL_MECHANISM_HISTORY")  # 30 min
    decision_cache_ttl: int = Field(default=300, env="TTL_DECISION_CACHE")  # 5 min
    feature_ttl: int = Field(default=3600, env="TTL_FEATURES")  # 1 hour
    
    # Blackboard zone TTLs (seconds)
    zone1_context_ttl: int = Field(default=60, env="TTL_ZONE1")  # 1 min
    zone2_reasoning_ttl: int = Field(default=300, env="TTL_ZONE2")  # 5 min
    zone3_synthesis_ttl: int = Field(default=300, env="TTL_ZONE3")  # 5 min
    zone4_decision_ttl: int = Field(default=3600, env="TTL_ZONE4")  # 1 hour
    zone5_learning_ttl: int = Field(default=86400, env="TTL_ZONE5")  # 24 hours
    
    # Attribution and outcomes TTLs
    attribution_ttl: int = Field(default=86400, env="TTL_ATTRIBUTION")  # 24 hours
    outcome_ttl: int = Field(default=604800, env="TTL_OUTCOME")  # 7 days
    validity_report_ttl: int = Field(default=7776000, env="TTL_VALIDITY_REPORT")  # 90 days
    
    # Cold start TTLs
    cold_start_ttl: int = Field(default=86400, env="TTL_COLD_START")  # 24 hours
    archetype_match_ttl: int = Field(default=86400, env="TTL_ARCHETYPE")  # 24 hours
    
    # Signal TTLs
    signal_buffer_ttl: int = Field(default=86400, env="TTL_SIGNAL_BUFFER")  # 24 hours
    signal_window_ttl: int = Field(default=1800, env="TTL_SIGNAL_WINDOW")  # 30 min
    
    # Embedding TTLs
    embedding_ttl: int = Field(default=86400, env="TTL_EMBEDDING")  # 24 hours
    
    # Privacy TTLs
    consent_ttl: int = Field(default=31536000, env="TTL_CONSENT")  # 1 year
    audit_log_ttl: int = Field(default=7776000, env="TTL_AUDIT_LOG")  # 90 days
    
    # Identity TTLs
    identity_ttl: int = Field(default=86400, env="TTL_IDENTITY")  # 24 hours
    unified_profile_ttl: int = Field(default=86400, env="TTL_UNIFIED_PROFILE")  # 24 hours
    
    class Config:
        env_prefix = "TTL_"


class ThresholdSettings(BaseSettings):
    """
    Centralized threshold configuration.
    
    All numerical thresholds for decisions, algorithms, and quality
    checks should be configured here.
    """
    
    # Circuit breaker thresholds
    circuit_failure_threshold: int = Field(default=5, env="THRESHOLD_CIRCUIT_FAILURES")
    circuit_recovery_timeout: float = Field(default=30.0, env="THRESHOLD_CIRCUIT_RECOVERY")
    circuit_half_open_max: int = Field(default=3, env="THRESHOLD_CIRCUIT_HALF_OPEN")
    
    # Latency thresholds (ms)
    fast_path_max_latency: int = Field(default=50, env="THRESHOLD_FAST_PATH_LATENCY")
    standard_path_max_latency: int = Field(default=100, env="THRESHOLD_STANDARD_LATENCY")
    reasoning_path_max_latency: int = Field(default=500, env="THRESHOLD_REASONING_LATENCY")
    exploration_path_max_latency: int = Field(default=100, env="THRESHOLD_EXPLORE_LATENCY")
    
    # Confidence thresholds
    high_confidence: float = Field(default=0.8, env="THRESHOLD_HIGH_CONFIDENCE")
    medium_confidence: float = Field(default=0.6, env="THRESHOLD_MEDIUM_CONFIDENCE")
    low_confidence: float = Field(default=0.4, env="THRESHOLD_LOW_CONFIDENCE")
    min_confidence: float = Field(default=0.3, env="THRESHOLD_MIN_CONFIDENCE")
    
    # Conflict thresholds
    conflict_major_threshold: float = Field(default=0.6, env="THRESHOLD_CONFLICT_MAJOR")
    conflict_moderate_threshold: float = Field(default=0.4, env="THRESHOLD_CONFLICT_MODERATE")
    conflict_trait_difference: float = Field(default=0.2, env="THRESHOLD_CONFLICT_TRAIT_DIFF")
    
    # Validity thresholds
    validity_pass_threshold: float = Field(default=0.7, env="THRESHOLD_VALIDITY_PASS")
    validity_warning_threshold: float = Field(default=0.5, env="THRESHOLD_VALIDITY_WARNING")
    cronbach_alpha_threshold: float = Field(default=0.7, env="THRESHOLD_CRONBACH_ALPHA")
    
    # Data richness thresholds
    cold_start_max_interactions: int = Field(default=0, env="THRESHOLD_COLD_START")
    sparse_max_interactions: int = Field(default=10, env="THRESHOLD_SPARSE")
    moderate_max_interactions: int = Field(default=50, env="THRESHOLD_MODERATE")
    
    # Mechanism effectiveness thresholds
    mechanism_success_min_trials: int = Field(default=5, env="THRESHOLD_MECH_MIN_TRIALS")
    mechanism_strong_evidence_trials: int = Field(default=50, env="THRESHOLD_MECH_STRONG")
    
    # Cache thresholds
    cache_warm_min_items: int = Field(default=10, env="THRESHOLD_CACHE_WARM_MIN")
    l1_cache_max_size: int = Field(default=1000, env="THRESHOLD_L1_CACHE_SIZE")
    
    # Signal thresholds
    signal_buffer_max_size: int = Field(default=1000, env="THRESHOLD_SIGNAL_BUFFER")
    signal_window_min_signals: int = Field(default=50, env="THRESHOLD_SIGNAL_WINDOW_MIN")
    
    # Embedding thresholds
    similarity_threshold: float = Field(default=0.7, env="THRESHOLD_SIMILARITY")
    
    # Recency weight parameters
    recency_half_life_hours: float = Field(default=24.0, env="THRESHOLD_RECENCY_HALF_LIFE")
    recency_min_weight: float = Field(default=0.3, env="THRESHOLD_RECENCY_MIN_WEIGHT")

    # Retargeting suppression thresholds
    retargeting_max_touches: int = Field(default=7, env="THRESHOLD_RETARGET_MAX_TOUCHES")
    retargeting_max_duration_days: int = Field(default=21, env="THRESHOLD_RETARGET_MAX_DAYS")
    retargeting_ctr_floor: float = Field(default=0.0003, env="THRESHOLD_RETARGET_CTR_FLOOR")
    retargeting_reactance_ceiling: float = Field(default=0.85, env="THRESHOLD_RETARGET_REACTANCE")
    retargeting_min_hours_between: int = Field(default=12, env="THRESHOLD_RETARGET_MIN_HOURS")
    retargeting_confrontation_suppress_days: int = Field(default=14, env="THRESHOLD_RETARGET_CONFRONT_DAYS")
    retargeting_pause_after_ctr_drop_hours: int = Field(default=72, env="THRESHOLD_RETARGET_CTR_PAUSE")
    
    class Config:
        env_prefix = "THRESHOLD_"


class LatencyBudgetSettings(BaseSettings):
    """
    Request-scoped latency budget configuration.

    Controls how the 120ms SLA budget is distributed across components.
    Each component gets a max allocation; if it finishes early, the
    slack flows to the next component.
    """

    # Total request budget (ms)
    total_budget_ms: float = Field(default=120.0, env="LATENCY_TOTAL_MS")

    # Reserved for serialization/response overhead
    reserve_ms: float = Field(default=10.0, env="LATENCY_RESERVE_MS")

    # Per-component max allocations (ms)
    prefetch_budget_ms: float = Field(default=40.0, env="LATENCY_PREFETCH_MS")
    cascade_budget_ms: float = Field(default=60.0, env="LATENCY_CASCADE_MS")
    dag_budget_ms: float = Field(default=80.0, env="LATENCY_DAG_MS")

    # Per-fetch timeout within prefetch (ms)
    per_fetch_timeout_ms: float = Field(default=8000.0, env="LATENCY_PER_FETCH_MS")

    class Config:
        env_prefix = "LATENCY_"


class InformationValueSettings(BaseSettings):
    """
    Information Value Bidding configuration.

    Controls the Bayesian Optimal Experiment Design parameters
    for psychological information value bidding.
    """

    # Scaling factor: maps variance reduction to dollar-denominated bid premiums
    # Calibrated so a new buyer's raw premium ≈ base_cpm (hitting 100% cap)
    accuracy_to_lift_factor: float = Field(default=5.0, env="IV_ACCURACY_TO_LIFT_FACTOR")

    # Maximum bid premium as percentage of base CPM (100% = bid up to 2x)
    max_bid_premium_pct: float = Field(default=100.0, env="IV_MAX_BID_PREMIUM_PCT")

    # Buyer lifetime assumptions
    default_session_frequency: float = Field(default=2.5, env="IV_SESSION_FREQUENCY")
    default_lifetime_days: float = Field(default=90.0, env="IV_LIFETIME_DAYS")
    discount_rate: float = Field(default=0.05, env="IV_DISCOUNT_RATE")

    # Default CPM floor
    default_base_cpm: float = Field(default=3.50, env="IV_DEFAULT_BASE_CPM")

    # Exploration priority thresholds
    critical_interaction_threshold: int = Field(default=2, env="IV_CRITICAL_THRESHOLD")
    high_interaction_threshold: int = Field(default=5, env="IV_HIGH_THRESHOLD")
    medium_confidence_threshold: float = Field(default=0.5, env="IV_MEDIUM_CONFIDENCE")
    low_confidence_threshold: float = Field(default=0.8, env="IV_LOW_CONFIDENCE")

    # Default prior: Beta(alpha, beta) for new buyers
    default_prior_alpha: float = Field(default=2.0, env="IV_DEFAULT_ALPHA")
    default_prior_beta: float = Field(default=2.0, env="IV_DEFAULT_BETA")

    class Config:
        env_prefix = "IV_"


class IntelligenceAPISettings(BaseSettings):
    """
    Universal Intelligence API configuration.

    Externalizes all thresholds used in the Universal Intelligence API
    router so they can be tuned per deployment without code changes.
    """

    # Channel openness thresholds
    channel_closed: float = Field(default=0.3, env="INTEL_CHANNEL_CLOSED")
    channel_narrow: float = Field(default=0.45, env="INTEL_CHANNEL_NARROW")

    # Mindset inference thresholds
    mindset_high: float = Field(default=0.65, env="INTEL_MINDSET_HIGH")
    mindset_low: float = Field(default=0.35, env="INTEL_MINDSET_LOW")

    # Evidence depth thresholds (edge counts)
    evidence_weak_min: int = Field(default=3, env="INTEL_EVIDENCE_WEAK_MIN")
    evidence_moderate: int = Field(default=20, env="INTEL_EVIDENCE_MOD")
    evidence_strong: int = Field(default=50, env="INTEL_EVIDENCE_STRONG")
    evidence_very_strong: int = Field(default=100, env="INTEL_EVIDENCE_VSTRONG")

    # CPM scaling
    cpm_floor: float = Field(default=0.5, env="INTEL_CPM_FLOOR")
    cpm_scale: float = Field(default=1.5, env="INTEL_CPM_SCALE")
    cpm_vertical_adj: float = Field(default=0.4, env="INTEL_CPM_VERT_ADJ")

    # Confidence scoring
    confidence_floor: float = Field(default=0.3, env="INTEL_CONF_FLOOR")
    confidence_cap: float = Field(default=0.9, env="INTEL_CONF_CAP")
    confidence_edge_norm: int = Field(default=500, env="INTEL_CONF_EDGE_NORM")

    # Blend weights (graph vs content profiler)
    graph_weight: float = Field(default=0.65, env="INTEL_GRAPH_WEIGHT")
    profiler_weight: float = Field(default=0.35, env="INTEL_PROFILER_WEIGHT")

    # Segment strength thresholds
    segment_strong: float = Field(default=0.7, env="INTEL_SEG_STRONG")
    segment_growth: float = Field(default=0.4, env="INTEL_SEG_GROWTH")

    # L3 bilateral threshold (minimum edges for L3 classification)
    l3_min_edges: int = Field(default=50, env="INTEL_L3_MIN_EDGES")

    # Minimum edges for category environment query
    category_min_edges: int = Field(default=5, env="INTEL_CATEGORY_MIN_EDGES")

    # Mindset sub-thresholds (uncertainty, social calibration in compound rules)
    mindset_uncertainty_high: float = Field(default=0.6, env="INTEL_MINDSET_UNCERT_HIGH")
    mindset_uncertainty_low: float = Field(default=0.4, env="INTEL_MINDSET_UNCERT_LOW")
    mindset_social_high: float = Field(default=0.6, env="INTEL_MINDSET_SOCIAL_HIGH")

    # Confidence formula internals
    confidence_base: float = Field(default=0.4, env="INTEL_CONF_BASE")
    confidence_edge_divisor: int = Field(default=1000, env="INTEL_CONF_EDGE_DIVISOR")

    # Channel openness formula weights
    channel_ce_weight: float = Field(default=0.3, env="INTEL_CHANNEL_CE_WEIGHT")
    channel_ar_weight: float = Field(default=0.2, env="INTEL_CHANNEL_AR_WEIGHT")
    channel_aa_weight: float = Field(default=0.3, env="INTEL_CHANNEL_AA_WEIGHT")
    channel_de_weight: float = Field(default=0.2, env="INTEL_CHANNEL_DE_WEIGHT")

    # Competitive environment variance thresholds
    comp_env_high_variance: float = Field(default=0.2, env="INTEL_COMP_HIGH_VAR")
    comp_env_low_variance: float = Field(default=0.08, env="INTEL_COMP_LOW_VAR")

    # Gradient minimum thresholds
    gradient_magnitude_min: float = Field(default=0.01, env="INTEL_GRADIENT_MAG_MIN")
    gradient_gap_meaningful: float = Field(default=0.05, env="INTEL_GRADIENT_GAP_MIN")

    # Construct activation
    construct_activation_min: float = Field(default=0.1, env="INTEL_CONSTRUCT_ACT_MIN")

    # Synergy classification thresholds
    synergy_amplify_threshold: float = Field(default=1.05, env="INTEL_SYNERGY_AMPLIFY")
    synergy_antagonize_threshold: float = Field(default=0.95, env="INTEL_SYNERGY_ANTAG")
    synergy_bonus_factor: float = Field(default=0.3, env="INTEL_SYNERGY_BONUS")

    # Fallback mechanism scoring
    fallback_mech_base: float = Field(default=0.8, env="INTEL_FALLBACK_MECH_BASE")
    fallback_mech_decrement: float = Field(default=0.1, env="INTEL_FALLBACK_MECH_DEC")

    # Brand creative direction thresholds
    arousal_high_threshold: float = Field(default=0.6, env="INTEL_AROUSAL_HIGH")

    class Config:
        env_prefix = "INTEL_"


class CascadeSettings(BaseSettings):
    """
    Bilateral Cascade Engine configuration.

    Externalizes all thresholds from the 5-level bilateral cascade
    (bilateral_cascade.py) so they can be tuned per deployment.
    """

    # --- Framing / Construal / Tone thresholds ---
    framing_promotion_threshold: float = Field(
        default=0.6, env="CASCADE_FRAMING_PROMO",
        description="regulatory_fit above this → gain framing",
    )
    framing_prevention_threshold: float = Field(
        default=0.4, env="CASCADE_FRAMING_PREVENT",
        description="regulatory_fit below this → loss framing",
    )
    construal_abstract_threshold: float = Field(
        default=0.6, env="CASCADE_CONSTRUAL_ABSTRACT",
    )
    construal_concrete_threshold: float = Field(
        default=0.4, env="CASCADE_CONSTRUAL_CONCRETE",
    )
    tone_emotion_threshold: float = Field(
        default=0.6, env="CASCADE_TONE_EMOTION",
        description="emotional_resonance above this → warm/urgent tone",
    )
    tone_personality_threshold: float = Field(
        default=0.6, env="CASCADE_TONE_PERSONALITY",
        description="personality_align above this → warm/authoritative tone",
    )

    # --- Urgency derivation weights ---
    urgency_concreteness_weight: float = Field(default=0.3, env="CASCADE_URGENCY_CONCRETE_W")
    urgency_emotional_weight: float = Field(default=0.7, env="CASCADE_URGENCY_EMOTION_W")

    # --- Social proof density weights ---
    social_proof_personality_weight: float = Field(default=0.6, env="CASCADE_SP_PERS_W")
    social_proof_value_weight: float = Field(default=0.4, env="CASCADE_SP_VAL_W")
    social_proof_value_discount: float = Field(default=0.5, env="CASCADE_SP_VAL_DISC")

    # --- Emotional intensity weights ---
    emotional_intensity_emotion_weight: float = Field(default=0.7, env="CASCADE_EI_EMOTION_W")
    emotional_intensity_evo_weight: float = Field(default=0.3, env="CASCADE_EI_EVO_W")

    # --- Lift estimation (Matz et al. 2017) ---
    matz_conversion_lift_pct: float = Field(
        default=54.0, env="CASCADE_MATZ_CONV_LIFT",
        description="Max conversion lift from personality-matched ads (Matz 2017)",
    )
    matz_ctr_lift_pct: float = Field(
        default=40.0, env="CASCADE_MATZ_CTR_LIFT",
        description="Max CTR lift from personality-matched ads (Matz 2017)",
    )
    lift_full_evidence_edges: int = Field(
        default=100, env="CASCADE_LIFT_FULL_EDGES",
        description="Edge count at which full evidence factor is achieved",
    )
    lift_min_confidence_factor: float = Field(
        default=0.5, env="CASCADE_LIFT_MIN_CONF",
    )

    # --- Level 1 defaults ---
    l1_confidence: float = Field(default=0.3, env="CASCADE_L1_CONF")
    l1_ctr_lift: float = Field(default=15.0, env="CASCADE_L1_CTR_LIFT")
    l1_conversion_lift: float = Field(default=20.0, env="CASCADE_L1_CONV_LIFT")
    l1_social_proof_density_primary: float = Field(default=0.8, env="CASCADE_L1_SP_PRIMARY")
    l1_social_proof_density_other: float = Field(default=0.5, env="CASCADE_L1_SP_OTHER")
    l1_emotional_intensity: float = Field(default=0.5, env="CASCADE_L1_EI")

    # --- Level 2 thresholds ---
    l2_category_max_blend: float = Field(
        default=0.8, env="CASCADE_L2_CAT_BLEND",
        description="Max blending weight for category-specific priors",
    )
    l2_cross_category_max_blend: float = Field(
        default=0.5, env="CASCADE_L2_XCAT_BLEND",
        description="Max blending weight for cross-category transfer",
    )
    l2_observation_divisor: float = Field(
        default=100.0, env="CASCADE_L2_OBS_DIVISOR",
    )
    l2_max_confidence: float = Field(default=0.6, env="CASCADE_L2_MAX_CONF")

    # --- Level 3 thresholds ---
    l3_min_edge_count: int = Field(
        default=10, env="CASCADE_L3_MIN_EDGES",
        description="Minimum bilateral edges for L3 activation",
    )
    l3_edge_prior_blend: float = Field(
        default=0.7, env="CASCADE_L3_EDGE_BLEND",
        description="Edge weight in edge vs prior blend (0.7 = 70% edge, 30% prior)",
    )
    l3_ad_primary_boost: float = Field(
        default=1.1, env="CASCADE_L3_AD_PRIMARY_BOOST",
        description="Multiplier for ad-endorsed primary mechanism",
    )
    l3_ad_secondary_boost: float = Field(
        default=1.05, env="CASCADE_L3_AD_SECONDARY_BOOST",
    )
    l3_confidence_edge_norm: float = Field(
        default=50.0, env="CASCADE_L3_CONF_EDGE_NORM",
        description="Edge count normalizer for confidence computation",
    )

    # --- Level 4 thresholds ---
    l4_signal_differentiation: float = Field(
        default=0.1, env="CASCADE_L4_SIGNAL_DIFF",
        description="Min difference for framing/construal signal override",
    )
    l4_confidence_increment: float = Field(
        default=0.1, env="CASCADE_L4_CONF_INCREMENT",
    )

    # --- Context modulation ---
    late_night_urgency_multiplier: float = Field(default=0.8, env="CASCADE_LATE_URGENCY")
    morning_urgency_multiplier: float = Field(default=1.15, env="CASCADE_MORNING_URGENCY")
    late_night_start_hour: int = Field(default=21, env="CASCADE_LATE_START_HOUR")
    late_night_end_hour: int = Field(default=5, env="CASCADE_LATE_END_HOUR")
    page_confidence_floor: float = Field(default=0.3, env="CASCADE_PAGE_CONF_FLOOR")
    page_open_channel_boost: float = Field(default=1.2, env="CASCADE_PAGE_OPEN_BOOST")
    page_closed_channel_dampen: float = Field(default=0.5, env="CASCADE_PAGE_CLOSED_DAMP")
    need_mechanism_boost_max: float = Field(
        default=0.15, env="CASCADE_NEED_MECH_BOOST",
        description="Max boost per activated need (e.g. 0.15 = +15%)",
    )
    low_bandwidth_threshold: float = Field(default=0.3, env="CASCADE_LOW_BANDWIDTH")
    publisher_authority_threshold: float = Field(default=0.7, env="CASCADE_PUB_AUTH_THRESH")
    publisher_authority_boost: float = Field(default=1.15, env="CASCADE_PUB_AUTH_BOOST")

    # --- Category deviation ---
    category_deviation_weight: float = Field(
        default=0.5, env="CASCADE_CATEGORY_DEVIATION_WEIGHT",
        description="Weight applied to category deviation when adjusting mechanism scores",
    )

    # --- Similar category transfer ---
    l2_similar_category_max_blend: float = Field(
        default=0.3, env="CASCADE_L2_SIMILAR_CAT_BLEND",
        description="Max blend weight when borrowing from similar categories",
    )

    # --- Synergy check ---
    learned_synergy_min_bonus: float = Field(
        default=0.05, env="CASCADE_SYNERGY_MIN_BONUS",
        description="Min interaction bonus for learned synergy override",
    )

    # --- Graph priors ---
    graph_prior_min_sample_size: int = Field(
        default=5, env="CASCADE_GRAPH_PRIOR_MIN_SAMPLES",
    )

    # --- Gradient field thresholds ---
    gradient_min_edges: int = Field(
        default=30, env="CASCADE_GRADIENT_MIN_EDGES",
        description="Minimum edges for valid gradient field",
    )
    gradient_min_r_squared: float = Field(
        default=0.05, env="CASCADE_GRADIENT_MIN_R2",
    )

    # --- Cache TTLs (seconds) ---
    decision_cache_ttl: int = Field(
        default=172800, env="CASCADE_DECISION_TTL",
        description="Decision context TTL (48 hours)",
    )
    decision_cache_max_size: int = Field(
        default=50000, env="CASCADE_DECISION_MAX_SIZE",
    )
    category_cache_ttl: float = Field(
        default=900.0, env="CASCADE_CATEGORY_CACHE_TTL",
        description="BayesianPrior category cache TTL (15 min)",
    )
    product_cache_ttl: float = Field(
        default=3600.0, env="CASCADE_PRODUCT_CACHE_TTL",
        description="Product profile cache TTL (1 hour)",
    )
    dedup_max_size: int = Field(
        default=10000, env="CASCADE_DEDUP_MAX_SIZE",
        description="Max event ID deduplication buffer",
    )

    # --- Attribution ---
    primary_mechanism_credit: float = Field(
        default=0.6, env="CASCADE_PRIMARY_MECH_CREDIT",
        description="Credit share for the primary mechanism used",
    )
    outcome_success_threshold: float = Field(
        default=0.5, env="CASCADE_OUTCOME_SUCCESS",
        description="outcome_value above this → conversion successful",
    )

    class Config:
        env_prefix = "CASCADE_"


class PlatformWeightSettings(BaseSettings):
    """
    Platform-specific weight configuration.
    
    Weights for cross-platform profile merging and signal aggregation.
    """
    
    # Platform weights for profile merging (should sum to ~1.0)
    amazon_weight: float = Field(default=0.25, env="WEIGHT_AMAZON")
    iheart_weight: float = Field(default=0.40, env="WEIGHT_IHEART")
    wpp_weight: float = Field(default=0.35, env="WEIGHT_WPP")
    
    # Data quality weights
    verified_quality_weight: float = Field(default=1.0, env="WEIGHT_QUALITY_VERIFIED")
    observed_quality_weight: float = Field(default=0.8, env="WEIGHT_QUALITY_OBSERVED")
    inferred_quality_weight: float = Field(default=0.5, env="WEIGHT_QUALITY_INFERRED")
    prior_quality_weight: float = Field(default=0.3, env="WEIGHT_QUALITY_PRIOR")
    
    # Modality weights for multimodal fusion
    audio_modality_weight: float = Field(default=0.25, env="WEIGHT_MODALITY_AUDIO")
    visual_modality_weight: float = Field(default=0.20, env="WEIGHT_MODALITY_VISUAL")
    text_modality_weight: float = Field(default=0.25, env="WEIGHT_MODALITY_TEXT")
    behavioral_modality_weight: float = Field(default=0.25, env="WEIGHT_MODALITY_BEHAVIORAL")
    contextual_modality_weight: float = Field(default=0.05, env="WEIGHT_MODALITY_CONTEXTUAL")
    
    class Config:
        env_prefix = "WEIGHT_"


class Settings(BaseSettings):
    """Main settings class combining all configuration."""
    
    # Environment
    environment: str = Field(default="development", env="ENVIRONMENT")
    debug: bool = Field(default=False, env="DEBUG")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    # Application
    app_name: str = Field(default="ADAM Platform", env="APP_NAME")
    app_version: str = Field(default="1.0.0", env="APP_VERSION")
    
    # Component settings
    neo4j: Neo4jSettings = Field(default_factory=Neo4jSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    kafka: KafkaSettings = Field(default_factory=KafkaSettings)
    claude: ClaudeSettings = Field(default_factory=ClaudeSettings)
    learning: LearningSettings = Field(default_factory=LearningSettings)
    metrics: MetricsSettings = Field(default_factory=MetricsSettings)
    api: APISettings = Field(default_factory=APISettings)
    ttl: TTLSettings = Field(default_factory=TTLSettings)
    thresholds: ThresholdSettings = Field(default_factory=ThresholdSettings)
    weights: PlatformWeightSettings = Field(default_factory=PlatformWeightSettings)
    information_value: InformationValueSettings = Field(default_factory=InformationValueSettings)
    stackadapt: StackAdaptSettings = Field(default_factory=StackAdaptSettings)
    intelligence: IntelligenceAPISettings = Field(default_factory=IntelligenceAPISettings)
    cascade: CascadeSettings = Field(default_factory=CascadeSettings)
    latency_budget: LatencyBudgetSettings = Field(default_factory=LatencyBudgetSettings)

    @property
    def is_production(self) -> bool:
        return self.environment == "production"
    
    @property
    def is_development(self) -> bool:
        return self.environment == "development"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Convenience accessor
settings = get_settings()
