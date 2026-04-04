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
            # CASCADE & INTELLIGENCE PREFETCH METRICS
            # -----------------------------------------------------------------

            # Cascade level reached per request
            self.cascade_level_reached = Counter(
                "adam_cascade_level_reached_total",
                "Cascade level reached per request",
                ["level"],
            )

            # Edge count per L3 query
            self.cascade_edge_count = Histogram(
                "adam_cascade_edge_count",
                "Number of BRAND_CONVERTED edges found at L3",
                buckets=[0, 5, 10, 25, 50, 100, 250, 500, 1000],
            )

            # Intelligence prefetch latency
            self.prefetch_latency = Histogram(
                "adam_intelligence_prefetch_latency_seconds",
                "Intelligence prefetch total latency",
                buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5],
            )

            # Intelligence sources populated per request
            self.prefetch_sources = Histogram(
                "adam_intelligence_prefetch_sources",
                "Number of intelligence sources populated by prefetch",
                buckets=[0, 1, 2, 3, 4, 5, 6, 7],
            )

            # Intelligence level in API responses
            self.intelligence_level = Counter(
                "adam_intelligence_level_total",
                "Intelligence level in API responses",
                ["level"],
            )

            # Prefetch empty (0 sources) — operator alert trigger
            self.prefetch_empty_total = Counter(
                "adam_prefetch_empty_total",
                "Requests where prefetch returned 0 intelligence sources",
            )

            # Per-source success tracking
            self.prefetch_source_success = Counter(
                "adam_prefetch_source_success_total",
                "Successful intelligence source fetches",
                ["source"],
            )

            # Per-source failure tracking (timeout, circuit, error)
            self.prefetch_source_failure = Counter(
                "adam_prefetch_source_failure_total",
                "Failed intelligence source fetches",
                ["source", "reason"],  # reason: timeout, circuit_open, error
            )

            # -----------------------------------------------------------------
            # MECHANISM SELECTION & POSTERIOR METRICS
            # -----------------------------------------------------------------

            # Which mechanisms are being selected (cascade output)
            self.mechanism_selected_total = Counter(
                "adam_mechanism_selected_total",
                "Mechanisms selected by cascade",
                ["mechanism"],
            )

            # Thompson posterior mean by mechanism (system-level learning state)
            self.posterior_mean = Gauge(
                "adam_posterior_mean",
                "Current Thompson posterior mean by mechanism",
                ["mechanism"],
            )

            # -----------------------------------------------------------------
            # LATENCY BUDGET & CIRCUIT BREAKER METRICS
            # -----------------------------------------------------------------

            # Budget utilization (what % of 120ms was used)
            self.budget_utilization = Histogram(
                "adam_budget_utilization_ratio",
                "Fraction of latency budget consumed per request",
                buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.5, 2.0],
            )

            # Circuit breaker state (0=closed, 1=half_open, 2=open)
            self.circuit_breaker_state = Gauge(
                "adam_circuit_breaker_state",
                "Current circuit breaker state (0=closed, 1=half_open, 2=open)",
                ["service"],
            )

            # -----------------------------------------------------------------
            # PAGE INTELLIGENCE CRAWL METRICS
            # -----------------------------------------------------------------

            # Page crawl totals
            self.page_crawl_total = Counter(
                "adam_page_crawl_total",
                "Total page crawl attempts",
                ["strategy", "pass_type"],
            )

            # Page crawl failures
            self.page_crawl_failures_total = Counter(
                "adam_page_crawl_failures_total",
                "Total page crawl failures",
                ["strategy", "error_type"],
            )

            # Page cache hit tiers
            self.page_cache_hits_total = Counter(
                "adam_page_cache_hits_total",
                "Page intelligence cache hits by tier",
                ["tier"],  # exact, domain, miss
            )

            # Page profile staleness
            self.page_profile_staleness_hours = Histogram(
                "adam_page_profile_staleness_hours",
                "Age of page profiles when served",
                buckets=[1, 6, 12, 24, 48, 72, 168],
            )

            # Page profile confidence
            self.page_profile_confidence = Histogram(
                "adam_page_profile_confidence",
                "Confidence of served page profiles",
                buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
            )

            # Total indexed pages
            self.page_indexed_total = Gauge(
                "adam_page_indexed_total",
                "Total number of indexed page profiles",
            )

            # Page outcome learning events
            self.page_outcome_learning_total = Counter(
                "adam_page_outcome_learning_total",
                "Page-conditioned outcome learning events",
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
            
            # -----------------------------------------------------------------
            # NONCONSCIOUS SIGNAL INTELLIGENCE (Enhancement #34)
            # -----------------------------------------------------------------

            self.signal_sessions_ingested = Counter(
                "adam_signal_sessions_ingested_total",
                "Telemetry sessions ingested by NonconsciousSignalCollector",
                ["referral_type"],  # ad_click, organic, direct
            )

            self.signal_processing_depth = Histogram(
                "adam_signal_processing_depth",
                "Processing depth weight distribution across impressions",
                buckets=[0.05, 0.10, 0.30, 0.50, 0.80, 1.00],
            )

            self.signal_reactance_detections = Counter(
                "adam_signal_reactance_detections_total",
                "Individual reactance onset detections (Signal 6)",
            )

            self.signal_barrier_overrides = Counter(
                "adam_signal_barrier_overrides_total",
                "Self-reported barrier overrides of algorithmic diagnosis (Signal 2)",
                ["self_reported_barrier", "algorithmic_barrier"],
            )

            self.signal_organic_stage = Counter(
                "adam_signal_organic_stage_total",
                "Organic return stage classifications (Signal 3)",
                ["stage"],  # evaluating_externally, evaluating_with_interest, intending
            )

            self.signal_frustration_score = Histogram(
                "adam_signal_frustration_score",
                "Frustration scores across bilateral edges",
                buckets=[0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8],
            )

            self.linucb_selections = Counter(
                "adam_linucb_selections_total",
                "Neural-LinUCB mechanism selections",
                ["mechanism", "agreed_with_thompson"],
            )

            self.linucb_latency = Histogram(
                "adam_linucb_latency_seconds",
                "Neural-LinUCB selection latency",
                buckets=[0.001, 0.005, 0.010, 0.025, 0.050],
            )

            self.pca_conversion_score = Histogram(
                "adam_pca_conversion_score",
                "PCA-based fast conversion score (PC1, r=-0.849)",
                buckets=[0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
            )

            self._initialized = True
            logger.info("ADAM Prometheus metrics initialized (incl. Enhancement #34 signals)")
            
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
    
    def record_page_crawl(
        self,
        strategy: str,
        pass_type: str = "fast_nlp",
    ) -> None:
        """Record a page crawl attempt."""
        if not self._initialized:
            return
        self.page_crawl_total.labels(
            strategy=strategy,
            pass_type=pass_type,
        ).inc()

    def record_page_crawl_failure(
        self,
        strategy: str,
        error_type: str = "fetch_failed",
    ) -> None:
        """Record a page crawl failure."""
        if not self._initialized:
            return
        self.page_crawl_failures_total.labels(
            strategy=strategy,
            error_type=error_type,
        ).inc()

    def record_page_cache_hit(self, tier: str) -> None:
        """Record a page cache hit by tier (exact, domain, miss)."""
        if not self._initialized:
            return
        self.page_cache_hits_total.labels(tier=tier).inc()

    def record_page_profile_served(
        self,
        staleness_hours: float,
        confidence: float,
    ) -> None:
        """Record when a page profile is served."""
        if not self._initialized:
            return
        self.page_profile_staleness_hours.observe(staleness_hours)
        self.page_profile_confidence.observe(confidence)

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
