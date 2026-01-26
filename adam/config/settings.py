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


class APISettings(BaseSettings):
    """API server configuration."""
    
    host: str = Field(default="0.0.0.0", env="API_HOST")
    port: int = Field(default=8000, env="API_PORT")
    
    # CORS
    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8080"],
        env="CORS_ORIGINS"
    )
    
    # Rate limiting
    rate_limit_per_minute: int = Field(default=1000, env="RATE_LIMIT_PER_MINUTE")
    
    # Authentication
    api_key_header: str = Field(default="X-API-Key", env="API_KEY_HEADER")
    
    # Docs
    docs_enabled: bool = Field(default=True, env="DOCS_ENABLED")
    
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
    
    class Config:
        env_prefix = "THRESHOLD_"


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


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Convenience accessor
settings = get_settings()
