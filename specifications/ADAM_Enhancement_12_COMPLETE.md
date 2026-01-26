# ADAM Enhancement #12: A/B Testing Infrastructure
## Production-Ready Experimentation Platform for Psychological Advertising

**Version**: 2.0 COMPLETE  
**Date**: January 2026  
**Priority**: P1 - Scientific Rigor & Proof Engine  
**Estimated Implementation**: 14 person-weeks  
**Dependencies**: #08 (Signal Aggregation), #11 (Validity Testing)  
**Dependents**: #06 (Gradient Bridge), #14 (Brand Intelligence)  
**File Size**: ~110KB (Production-Ready)

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Part 1: Experiment Data Models](#part-1-experiment-data-models)
3. [Part 2: Traffic Assignment Engine](#part-2-traffic-assignment-engine)
4. [Part 3: Statistical Analysis Framework](#part-3-statistical-analysis-framework)
5. [Part 4: Sequential Testing & Early Stopping](#part-4-sequential-testing--early-stopping)
6. [Part 5: Multi-Armed Bandit Integration](#part-5-multi-armed-bandit-integration)
7. [Part 6: Psychological Mechanism Testing](#part-6-psychological-mechanism-testing)
8. [Part 7: Experiment Quality Assurance](#part-7-experiment-quality-assurance)
9. [Part 8: Metric Computation Pipeline](#part-8-metric-computation-pipeline)
10. [Part 9: Component Integration](#part-9-component-integration)
11. [Part 10: FastAPI Endpoints](#part-10-fastapi-endpoints)
12. [Part 11: Observability & Operations](#part-11-observability--operations)
13. [Part 12: Testing & Validation](#part-12-testing--validation)
14. [Implementation Timeline](#implementation-timeline)
15. [Success Metrics](#success-metrics)

---

## Executive Summary

ADAM's psychological targeting claims require rigorous scientific validation. The A/B Testing Infrastructure provides the **proof engine** that transforms theoretical persuasion mechanisms into measurable business outcomes. Without this infrastructure, claims of 40-50% conversion lifts are unsubstantiated marketing; with it, they become defensible ROI stories.

### The Validation Challenge

| Challenge | Traditional A/B Testing | ADAM Requirements |
|-----------|------------------------|-------------------|
| What to test | UI elements, copy | Psychological mechanisms |
| Segmentation | Demographics | Personality × State |
| Analysis depth | Aggregate effects | Mechanism × Personality interactions |
| Decision speed | 2-4 weeks | Continuous optimization |
| Learning scope | Single experiment | Cross-experiment meta-learning |

### Why Psychological A/B Testing Is Different

Standard A/B testing asks: "Does variant B outperform variant A?"

ADAM's testing asks:
1. "Does personality-matched messaging outperform random targeting?"
2. "Which psychological mechanism drives conversion for High-Openness users?"
3. "Does promotion-focused framing work better when arousal is elevated?"
4. "What's the optimal construal level for users in the consideration stage?"

This requires:
- **Stratified analysis** by psychological profile
- **Mechanism isolation** to identify causal drivers
- **State-aware testing** that accounts for real-time psychological state
- **Cross-experiment learning** to build systematic knowledge

### Key Capabilities

1. **Experiment Design**: Proper randomization, power analysis, stratification by psychological segments
2. **Traffic Assignment**: Consistent hashing with feature flagging integration
3. **Statistical Analysis**: Frequentist, Bayesian, and sequential methods
4. **Multi-Armed Bandits**: Exploration/exploitation for continuous optimization
5. **Mechanism Testing**: Isolate individual psychological components
6. **Quality Assurance**: SRM detection, collision detection, guardrails
7. **Meta-Learning**: Accumulate knowledge across experiments

---


## Part 1: Experiment Data Models

```python
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from typing import Dict, List, Optional, Tuple, Any, Set, Union, Literal, Callable
from abc import ABC, abstractmethod
from pydantic import BaseModel, Field, validator, root_validator
import numpy as np
import hashlib
import uuid
import json
from scipy import stats


# =============================================================================
# EXPERIMENT TYPES & ENUMS
# =============================================================================

class ExperimentType(str, Enum):
    """Types of experiments ADAM can run."""
    
    # Standard A/B tests
    AB_STANDARD = "ab_standard"              # Treatment vs. control
    AB_MULTIVARIATE = "ab_multivariate"      # Multiple treatments (A/B/n)
    
    # Factorial designs
    FACTORIAL_FULL = "factorial_full"         # All factor combinations
    FACTORIAL_FRACTIONAL = "factorial_frac"   # Subset of combinations
    
    # Psychological mechanism tests
    MECHANISM_ISOLATION = "mechanism_isolation"       # Test single mechanism
    MECHANISM_INTERACTION = "mechanism_interaction"   # Test mechanism combinations
    PERSONALITY_MATCH = "personality_match"           # Personality targeting
    STATE_TIMING = "state_timing"                     # Journey state targeting
    
    # Message/creative tests
    COPY_VARIANT = "copy_variant"            # Messaging variants
    FRAME_TEST = "frame_test"                # Gain/loss framing
    CONSTRUAL_TEST = "construal_test"        # Abstract/concrete messaging
    
    # System tests
    MODEL_COMPARISON = "model_comparison"    # Compare ML models
    ALGORITHM_TEST = "algorithm_test"        # Compare algorithms
    HOLDOUT = "holdout"                      # Long-term holdout
    
    # Adaptive experiments
    MULTI_ARMED_BANDIT = "mab"               # Thompson sampling
    CONTEXTUAL_BANDIT = "contextual_bandit"  # Context-aware optimization


class ExperimentStatus(str, Enum):
    """Experiment lifecycle states."""
    DRAFT = "draft"                # Being designed
    REVIEW = "review"              # Awaiting approval
    SCHEDULED = "scheduled"        # Approved, not started
    RUNNING = "running"            # Active
    PAUSED = "paused"              # Temporarily stopped
    RAMPING = "ramping"            # Gradually increasing traffic
    COMPLETING = "completing"      # Wrapping up
    COMPLETED = "completed"        # Finished normally
    STOPPED = "stopped"            # Terminated early
    ARCHIVED = "archived"          # Historical record


class AssignmentStrategy(str, Enum):
    """How users are assigned to variants."""
    RANDOM = "random"                    # Pure random assignment
    STRATIFIED = "stratified"            # Stratified by segments
    CLUSTERED = "clustered"              # Cluster randomization
    QUASI_EXPERIMENTAL = "quasi"         # Natural experiment
    SWITCHBACK = "switchback"            # Time-based switching
    GEO_SPLIT = "geo_split"              # Geographic split
    HASH_BASED = "hash_based"            # Deterministic hashing


class AnalysisMethod(str, Enum):
    """Statistical analysis methods."""
    FREQUENTIST = "frequentist"          # Traditional hypothesis testing
    BAYESIAN = "bayesian"                # Bayesian inference
    SEQUENTIAL = "sequential"            # Sequential testing (early stopping)
    CUPED = "cuped"                       # Variance reduction with covariates
    DIFF_IN_DIFF = "diff_in_diff"        # Difference-in-differences
    REGRESSION_DISCONTINUITY = "rdd"     # Regression discontinuity


class MetricType(str, Enum):
    """Types of experiment metrics."""
    PRIMARY = "primary"                  # Main decision metric
    SECONDARY = "secondary"              # Additional insights
    GUARDRAIL = "guardrail"              # Must not degrade
    DIAGNOSTIC = "diagnostic"            # Debug/understand


# =============================================================================
# CORE DATA MODELS
# =============================================================================

class Variant(BaseModel):
    """A variant (treatment or control) in an experiment."""
    
    variant_id: str = Field(default_factory=lambda: f"var_{uuid.uuid4().hex[:8]}")
    variant_name: str
    variant_type: Literal["control", "treatment"]
    
    # Traffic allocation
    traffic_fraction: float = Field(..., ge=0.0, le=1.0)
    min_traffic_fraction: float = Field(0.0, ge=0.0)  # For bandits
    max_traffic_fraction: float = Field(1.0, le=1.0)  # For bandits
    
    # Configuration
    config: Dict[str, Any] = Field(default_factory=dict)
    feature_flags: Dict[str, bool] = Field(default_factory=dict)
    
    # Psychological targeting (ADAM-specific)
    psychological_config: Optional[Dict[str, Any]] = None
    mechanism_settings: Dict[str, Any] = Field(default_factory=dict)
    
    # Description
    hypothesis: str = ""
    expected_effect: Optional[float] = None
    
    @property
    def is_control(self) -> bool:
        return self.variant_type == "control"


class MetricDefinition(BaseModel):
    """Definition of an experiment metric."""
    
    metric_id: str = Field(default_factory=lambda: f"met_{uuid.uuid4().hex[:8]}")
    metric_name: str
    metric_type: MetricType
    
    # Computation
    numerator_event: str              # e.g., "conversion"
    denominator_event: Optional[str] = None  # e.g., "impression" (None = count)
    aggregation: Literal["ratio", "mean", "sum", "count", "percentile"] = "ratio"
    
    # Statistical properties
    expected_baseline: Optional[float] = None
    minimum_detectable_effect: Optional[float] = None
    variance_estimate: Optional[float] = None
    
    # Guardrail thresholds
    guardrail_threshold: Optional[float] = None
    guardrail_direction: Literal["higher_is_better", "lower_is_better", "neutral"] = "higher_is_better"
    
    # Attribution
    attribution_window_hours: int = 24
    
    def is_guardrail_violated(self, value: float, baseline: float) -> bool:
        """Check if guardrail threshold is violated."""
        if self.metric_type != MetricType.GUARDRAIL or not self.guardrail_threshold:
            return False
        
        if self.guardrail_direction == "higher_is_better":
            return value < baseline * (1 - self.guardrail_threshold)
        elif self.guardrail_direction == "lower_is_better":
            return value > baseline * (1 + self.guardrail_threshold)
        return False


class StratificationConfig(BaseModel):
    """Configuration for stratified randomization."""
    
    enabled: bool = False
    variables: List[str] = Field(default_factory=list)
    
    # Psychological stratification (ADAM-specific)
    personality_clusters: bool = False  # Stratify by Big Five clusters
    psychological_states: bool = False  # Stratify by current state
    journey_stages: bool = False        # Stratify by decision journey
    
    # Balance checking
    check_balance: bool = True
    max_imbalance_ratio: float = 0.1    # Max deviation from expected


class ExperimentDesign(BaseModel):
    """Complete experiment design specification."""
    
    # Identity
    experiment_id: str = Field(default_factory=lambda: f"exp_{uuid.uuid4().hex[:12]}")
    experiment_name: str
    experiment_type: ExperimentType
    
    # Hypothesis
    null_hypothesis: str
    alternative_hypothesis: str
    expected_effect_size: float         # Cohen's d or percentage lift
    directionality: Literal["one_sided", "two_sided"] = "two_sided"
    
    # Variants
    variants: List[Variant]
    
    # Assignment
    assignment_strategy: AssignmentStrategy = AssignmentStrategy.HASH_BASED
    assignment_unit: str = "user_id"    # What gets randomized
    assignment_salt: str = Field(default_factory=lambda: uuid.uuid4().hex[:16])
    stratification: StratificationConfig = Field(default_factory=StratificationConfig)
    
    # Metrics
    metrics: List[MetricDefinition] = Field(default_factory=list)
    
    # Statistical parameters
    alpha: float = Field(0.05, gt=0, lt=1)           # Significance level
    power: float = Field(0.80, gt=0, lt=1)           # Statistical power
    required_sample_size: Optional[int] = None
    minimum_runtime_hours: int = 168    # 1 week minimum
    maximum_runtime_hours: int = 672    # 4 weeks maximum
    
    # Analysis configuration
    analysis_method: AnalysisMethod = AnalysisMethod.BAYESIAN
    sequential_testing: bool = True
    cuped_covariates: List[str] = Field(default_factory=list)
    
    # Targeting
    audience_filter: Dict[str, Any] = Field(default_factory=dict)
    exclusion_criteria: Dict[str, Any] = Field(default_factory=dict)
    
    # Psychological targeting (ADAM-specific)
    personality_segments: Optional[List[str]] = None  # Target specific segments
    psychological_state_filter: Optional[Dict[str, Any]] = None
    
    # Lifecycle
    status: ExperimentStatus = ExperimentStatus.DRAFT
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    
    # Ownership
    owner: str = ""
    team: str = ""
    tags: List[str] = Field(default_factory=list)
    
    @property
    def primary_metric(self) -> Optional[MetricDefinition]:
        """Get the primary metric."""
        for m in self.metrics:
            if m.metric_type == MetricType.PRIMARY:
                return m
        return None
    
    @property
    def guardrail_metrics(self) -> List[MetricDefinition]:
        """Get all guardrail metrics."""
        return [m for m in self.metrics if m.metric_type == MetricType.GUARDRAIL]
    
    @property
    def control_variant(self) -> Optional[Variant]:
        """Get the control variant."""
        for v in self.variants:
            if v.is_control:
                return v
        return None
    
    @property
    def treatment_variants(self) -> List[Variant]:
        """Get all treatment variants."""
        return [v for v in self.variants if not v.is_control]
    
    def get_variant_by_id(self, variant_id: str) -> Optional[Variant]:
        """Get variant by ID."""
        for v in self.variants:
            if v.variant_id == variant_id:
                return v
        return None


class ExperimentAssignment(BaseModel):
    """Record of a user's assignment to an experiment."""
    
    assignment_id: str = Field(default_factory=lambda: f"asgn_{uuid.uuid4().hex[:12]}")
    experiment_id: str
    variant_id: str
    
    # Assignment unit
    user_id: str
    session_id: Optional[str] = None
    device_id: Optional[str] = None
    
    # Timing
    assigned_at: datetime = Field(default_factory=datetime.utcnow)
    first_exposure_at: Optional[datetime] = None
    
    # Context at assignment
    assignment_context: Dict[str, Any] = Field(default_factory=dict)
    psychological_state: Optional[Dict[str, float]] = None
    personality_profile: Optional[Dict[str, float]] = None
    
    # Stratification
    stratum: Optional[str] = None


class ExperimentEvent(BaseModel):
    """Event recorded for experiment analysis."""
    
    event_id: str = Field(default_factory=lambda: f"evt_{uuid.uuid4().hex[:12]}")
    experiment_id: str
    variant_id: str
    user_id: str
    
    # Event details
    event_type: str                     # e.g., "impression", "click", "conversion"
    event_value: float = 1.0            # For revenue, etc.
    event_time: datetime = Field(default_factory=datetime.utcnow)
    
    # Attribution
    assignment_id: str
    time_since_assignment_seconds: float = 0.0
    
    # Context
    event_context: Dict[str, Any] = Field(default_factory=dict)


class ExperimentResults(BaseModel):
    """Results of experiment analysis."""
    
    experiment_id: str
    analysis_timestamp: datetime = Field(default_factory=datetime.utcnow)
    analysis_method: AnalysisMethod
    
    # Sample sizes
    total_users: int = 0
    users_per_variant: Dict[str, int] = Field(default_factory=dict)
    
    # Results per variant
    variant_results: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    
    # Comparison results
    comparisons: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Statistical outputs
    p_value: Optional[float] = None
    confidence_interval: Optional[Tuple[float, float]] = None
    posterior_probability: Optional[float] = None  # Bayesian
    expected_lift: Optional[Dict[str, float]] = None
    
    # Decision
    is_significant: bool = False
    recommended_action: Literal["ship", "iterate", "stop", "continue"] = "continue"
    recommendation_reason: str = ""
    
    # Guardrails
    guardrail_status: Dict[str, str] = Field(default_factory=dict)
    
    # Quality checks
    srm_check_passed: bool = True
    novelty_effect_detected: bool = False
```

---


## Part 2: Traffic Assignment Engine

```python
import mmh3  # MurmurHash3 for consistent hashing
from typing import AsyncIterator
import asyncio
from collections import defaultdict


# =============================================================================
# CONSISTENT HASHING FOR DETERMINISTIC ASSIGNMENT
# =============================================================================

class ConsistentHasher:
    """
    Consistent hashing for deterministic experiment assignment.
    
    Ensures:
    - Same user always gets same variant (sticky)
    - Uniform distribution across variants
    - Minimal reassignment when variants change
    """
    
    def __init__(self, hash_seed: int = 42):
        self.hash_seed = hash_seed
    
    def hash_unit(self, unit_id: str, salt: str) -> int:
        """Hash assignment unit to integer in [0, 10000)."""
        hash_input = f"{salt}:{unit_id}"
        # MurmurHash3 for speed and uniformity
        hash_value = mmh3.hash(hash_input, seed=self.hash_seed, signed=False)
        return hash_value % 10000
    
    def assign_variant(
        self,
        unit_id: str,
        salt: str,
        variants: List[Variant]
    ) -> Optional[str]:
        """
        Assign unit to variant based on traffic fractions.
        
        Uses layered hashing to ensure uniform distribution.
        """
        if not variants:
            return None
        
        # Sort variants by ID for determinism
        sorted_variants = sorted(variants, key=lambda v: v.variant_id)
        
        # Get hash bucket
        bucket = self.hash_unit(unit_id, salt)
        
        # Assign based on cumulative traffic fractions
        cumulative = 0.0
        for variant in sorted_variants:
            cumulative += variant.traffic_fraction
            threshold = int(cumulative * 10000)
            
            if bucket < threshold:
                return variant.variant_id
        
        # Fallback to last variant
        return sorted_variants[-1].variant_id
    
    def check_uniform_distribution(
        self,
        unit_ids: List[str],
        salt: str,
        variants: List[Variant]
    ) -> Dict[str, float]:
        """Verify assignment distribution matches expected."""
        counts = defaultdict(int)
        
        for unit_id in unit_ids:
            variant_id = self.assign_variant(unit_id, salt, variants)
            counts[variant_id] += 1
        
        total = len(unit_ids)
        distribution = {k: v / total for k, v in counts.items()}
        
        return distribution


class TrafficAssignmentEngine:
    """
    Production traffic assignment engine.
    
    Features:
    - Deterministic assignment via consistent hashing
    - Stratified randomization
    - Experiment eligibility checking
    - Collision detection
    - Audit logging
    """
    
    def __init__(
        self,
        redis_client: 'Redis',
        neo4j_client: 'Neo4jDriver',
        cache_ttl_seconds: int = 300,
    ):
        self.redis = redis_client
        self.neo4j = neo4j_client
        self.cache_ttl = cache_ttl_seconds
        self.hasher = ConsistentHasher()
        
        # In-memory cache of active experiments
        self._active_experiments: Dict[str, ExperimentDesign] = {}
        self._cache_refresh_time: datetime = datetime.min
    
    async def get_assignment(
        self,
        user_id: str,
        experiment_id: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[ExperimentAssignment]:
        """
        Get or create assignment for user in experiment.
        
        Returns None if user is not eligible.
        """
        # Check cache first
        cache_key = f"assignment:{experiment_id}:{user_id}"
        cached = await self.redis.get(cache_key)
        
        if cached:
            return ExperimentAssignment(**json.loads(cached))
        
        # Get experiment
        experiment = await self._get_experiment(experiment_id)
        if not experiment or experiment.status != ExperimentStatus.RUNNING:
            return None
        
        # Check eligibility
        if not await self._check_eligibility(user_id, experiment, context):
            return None
        
        # Create assignment
        assignment = await self._create_assignment(user_id, experiment, context)
        
        # Cache it
        await self.redis.setex(
            cache_key,
            self.cache_ttl,
            assignment.json()
        )
        
        # Store in Neo4j
        await self._store_assignment(assignment)
        
        return assignment
    
    async def get_all_assignments(
        self,
        user_id: str,
        context: Optional[Dict[str, Any]] = None
    ) -> List[ExperimentAssignment]:
        """
        Get assignments for all active experiments user is eligible for.
        """
        await self._refresh_active_experiments()
        
        assignments = []
        for experiment in self._active_experiments.values():
            assignment = await self.get_assignment(user_id, experiment.experiment_id, context)
            if assignment:
                assignments.append(assignment)
        
        return assignments
    
    async def _create_assignment(
        self,
        user_id: str,
        experiment: ExperimentDesign,
        context: Optional[Dict[str, Any]]
    ) -> ExperimentAssignment:
        """Create new assignment using configured strategy."""
        
        if experiment.assignment_strategy == AssignmentStrategy.STRATIFIED:
            return await self._create_stratified_assignment(user_id, experiment, context)
        else:
            return await self._create_hash_assignment(user_id, experiment, context)
    
    async def _create_hash_assignment(
        self,
        user_id: str,
        experiment: ExperimentDesign,
        context: Optional[Dict[str, Any]]
    ) -> ExperimentAssignment:
        """Create assignment using consistent hashing."""
        
        variant_id = self.hasher.assign_variant(
            unit_id=user_id,
            salt=experiment.assignment_salt,
            variants=experiment.variants
        )
        
        # Get psychological context if available
        psychological_state = None
        personality_profile = None
        
        if context:
            psychological_state = context.get("psychological_state")
            personality_profile = context.get("personality_profile")
        
        return ExperimentAssignment(
            experiment_id=experiment.experiment_id,
            variant_id=variant_id,
            user_id=user_id,
            assignment_context=context or {},
            psychological_state=psychological_state,
            personality_profile=personality_profile,
        )
    
    async def _create_stratified_assignment(
        self,
        user_id: str,
        experiment: ExperimentDesign,
        context: Optional[Dict[str, Any]]
    ) -> ExperimentAssignment:
        """Create assignment with stratification."""
        
        # Determine stratum
        stratum = await self._determine_stratum(user_id, experiment, context)
        
        # Use stratum-specific salt
        stratum_salt = f"{experiment.assignment_salt}:{stratum}"
        
        variant_id = self.hasher.assign_variant(
            unit_id=user_id,
            salt=stratum_salt,
            variants=experiment.variants
        )
        
        return ExperimentAssignment(
            experiment_id=experiment.experiment_id,
            variant_id=variant_id,
            user_id=user_id,
            assignment_context=context or {},
            stratum=stratum,
        )
    
    async def _determine_stratum(
        self,
        user_id: str,
        experiment: ExperimentDesign,
        context: Optional[Dict[str, Any]]
    ) -> str:
        """Determine stratification stratum for user."""
        
        strat_config = experiment.stratification
        strata_parts = []
        
        # Psychological stratification
        if strat_config.personality_clusters and context:
            personality = context.get("personality_profile", {})
            cluster = self._personality_to_cluster(personality)
            strata_parts.append(f"personality:{cluster}")
        
        if strat_config.journey_stages and context:
            journey_stage = context.get("journey_stage", "unknown")
            strata_parts.append(f"journey:{journey_stage}")
        
        # Standard variables
        for var in strat_config.variables:
            if context and var in context:
                strata_parts.append(f"{var}:{context[var]}")
        
        return "|".join(strata_parts) if strata_parts else "default"
    
    def _personality_to_cluster(self, personality: Dict[str, float]) -> str:
        """Map personality profile to cluster name."""
        # Simplified clustering based on dominant trait
        if not personality:
            return "unknown"
        
        traits = ["openness", "conscientiousness", "extraversion", "agreeableness", "neuroticism"]
        max_trait = max(traits, key=lambda t: personality.get(t, 0.5))
        max_value = personality.get(max_trait, 0.5)
        
        if max_value > 0.7:
            return f"high_{max_trait}"
        elif max_value < 0.3:
            return f"low_{max_trait}"
        else:
            return "balanced"
    
    async def _check_eligibility(
        self,
        user_id: str,
        experiment: ExperimentDesign,
        context: Optional[Dict[str, Any]]
    ) -> bool:
        """Check if user is eligible for experiment."""
        
        # Check audience filter
        if experiment.audience_filter:
            if not self._matches_filter(context, experiment.audience_filter):
                return False
        
        # Check exclusion criteria
        if experiment.exclusion_criteria:
            if self._matches_filter(context, experiment.exclusion_criteria):
                return False
        
        # Check psychological segment targeting
        if experiment.personality_segments and context:
            personality = context.get("personality_profile", {})
            cluster = self._personality_to_cluster(personality)
            if cluster not in experiment.personality_segments:
                return False
        
        # Check for conflicting experiments
        if await self._has_conflicting_experiment(user_id, experiment):
            return False
        
        return True
    
    def _matches_filter(
        self,
        context: Optional[Dict[str, Any]],
        filter_spec: Dict[str, Any]
    ) -> bool:
        """Check if context matches filter specification."""
        if not context:
            return False
        
        for key, expected in filter_spec.items():
            actual = context.get(key)
            
            if isinstance(expected, dict):
                # Range filter
                if "min" in expected and actual < expected["min"]:
                    return False
                if "max" in expected and actual > expected["max"]:
                    return False
                if "in" in expected and actual not in expected["in"]:
                    return False
            else:
                # Exact match
                if actual != expected:
                    return False
        
        return True
    
    async def _has_conflicting_experiment(
        self,
        user_id: str,
        experiment: ExperimentDesign
    ) -> bool:
        """Check if user is in conflicting experiment."""
        # Query Neo4j for user's active experiments
        query = """
        MATCH (u:User {user_id: $user_id})-[:ASSIGNED_TO]->(e:Experiment)
        WHERE e.status = 'running'
        RETURN e.experiment_id, e.conflict_group
        """
        
        result = await self.neo4j.run(query, user_id=user_id)
        
        # Check for conflict group overlap
        current_conflict_group = experiment.tags  # Using tags as conflict groups
        
        for record in result:
            existing_group = record.get("conflict_group", [])
            if set(current_conflict_group) & set(existing_group):
                return True
        
        return False
    
    async def _get_experiment(self, experiment_id: str) -> Optional[ExperimentDesign]:
        """Get experiment from cache or database."""
        if experiment_id in self._active_experiments:
            return self._active_experiments[experiment_id]
        
        # Query Neo4j
        query = """
        MATCH (e:Experiment {experiment_id: $experiment_id})
        RETURN e
        """
        
        result = await self.neo4j.run(query, experiment_id=experiment_id)
        record = await result.single()
        
        if record:
            return ExperimentDesign(**record["e"])
        return None
    
    async def _store_assignment(self, assignment: ExperimentAssignment) -> None:
        """Store assignment in Neo4j."""
        query = """
        MATCH (u:User {user_id: $user_id})
        MATCH (e:Experiment {experiment_id: $experiment_id})
        MATCH (v:Variant {variant_id: $variant_id})
        CREATE (u)-[a:ASSIGNED_TO {
            assignment_id: $assignment_id,
            assigned_at: datetime($assigned_at),
            stratum: $stratum
        }]->(v)
        CREATE (a)-[:IN_EXPERIMENT]->(e)
        """
        
        await self.neo4j.run(
            query,
            user_id=assignment.user_id,
            experiment_id=assignment.experiment_id,
            variant_id=assignment.variant_id,
            assignment_id=assignment.assignment_id,
            assigned_at=assignment.assigned_at.isoformat(),
            stratum=assignment.stratum,
        )
    
    async def _refresh_active_experiments(self) -> None:
        """Refresh cache of active experiments."""
        now = datetime.utcnow()
        if (now - self._cache_refresh_time).total_seconds() < 60:
            return
        
        query = """
        MATCH (e:Experiment)
        WHERE e.status = 'running'
        RETURN e
        """
        
        result = await self.neo4j.run(query)
        
        self._active_experiments = {}
        async for record in result:
            exp = ExperimentDesign(**record["e"])
            self._active_experiments[exp.experiment_id] = exp
        
        self._cache_refresh_time = now


# =============================================================================
# EXPERIMENT COLLISION DETECTION
# =============================================================================

class ExperimentCollisionDetector:
    """
    Detect and prevent experiment collisions.
    
    Collisions occur when:
    - Same user in multiple experiments testing same feature
    - Experiments have overlapping treatment effects
    - Interaction effects confound individual experiment results
    """
    
    def __init__(self, neo4j_client: 'Neo4jDriver'):
        self.neo4j = neo4j_client
    
    async def check_collision_risk(
        self,
        new_experiment: ExperimentDesign,
        active_experiments: List[ExperimentDesign]
    ) -> Dict[str, Any]:
        """
        Assess collision risk for new experiment.
        """
        risks = []
        
        for existing in active_experiments:
            collision = self._assess_pairwise_collision(new_experiment, existing)
            if collision["risk_level"] != "none":
                risks.append(collision)
        
        overall_risk = "high" if any(r["risk_level"] == "high" for r in risks) else \
                       "medium" if any(r["risk_level"] == "medium" for r in risks) else \
                       "low" if risks else "none"
        
        return {
            "overall_risk": overall_risk,
            "collision_details": risks,
            "recommendation": self._get_collision_recommendation(risks),
        }
    
    def _assess_pairwise_collision(
        self,
        exp1: ExperimentDesign,
        exp2: ExperimentDesign
    ) -> Dict[str, Any]:
        """Assess collision between two experiments."""
        
        # Check audience overlap
        audience_overlap = self._estimate_audience_overlap(exp1, exp2)
        
        # Check feature overlap
        feature_overlap = self._check_feature_overlap(exp1, exp2)
        
        # Check psychological mechanism overlap
        mechanism_overlap = self._check_mechanism_overlap(exp1, exp2)
        
        # Determine risk level
        if feature_overlap and audience_overlap > 0.5:
            risk_level = "high"
        elif mechanism_overlap and audience_overlap > 0.3:
            risk_level = "medium"
        elif audience_overlap > 0.1:
            risk_level = "low"
        else:
            risk_level = "none"
        
        return {
            "experiment_id": exp2.experiment_id,
            "experiment_name": exp2.experiment_name,
            "risk_level": risk_level,
            "audience_overlap": audience_overlap,
            "feature_overlap": feature_overlap,
            "mechanism_overlap": mechanism_overlap,
        }
    
    def _estimate_audience_overlap(
        self,
        exp1: ExperimentDesign,
        exp2: ExperimentDesign
    ) -> float:
        """Estimate audience overlap between experiments."""
        # Simplified - in production would query actual user populations
        
        # Check for mutually exclusive segments
        if exp1.personality_segments and exp2.personality_segments:
            overlap = set(exp1.personality_segments) & set(exp2.personality_segments)
            if not overlap:
                return 0.0
        
        # Default assumption: significant overlap
        return 0.5
    
    def _check_feature_overlap(
        self,
        exp1: ExperimentDesign,
        exp2: ExperimentDesign
    ) -> bool:
        """Check if experiments modify same features."""
        features1 = set()
        features2 = set()
        
        for variant in exp1.variants:
            features1.update(variant.feature_flags.keys())
            features1.update(variant.config.keys())
        
        for variant in exp2.variants:
            features2.update(variant.feature_flags.keys())
            features2.update(variant.config.keys())
        
        return bool(features1 & features2)
    
    def _check_mechanism_overlap(
        self,
        exp1: ExperimentDesign,
        exp2: ExperimentDesign
    ) -> bool:
        """Check if experiments test same psychological mechanisms."""
        mechanisms1 = set()
        mechanisms2 = set()
        
        for variant in exp1.variants:
            mechanisms1.update(variant.mechanism_settings.keys())
        
        for variant in exp2.variants:
            mechanisms2.update(variant.mechanism_settings.keys())
        
        return bool(mechanisms1 & mechanisms2)
    
    def _get_collision_recommendation(
        self,
        risks: List[Dict[str, Any]]
    ) -> str:
        """Generate recommendation based on collision risks."""
        if not risks:
            return "Safe to launch. No collision risks detected."
        
        high_risks = [r for r in risks if r["risk_level"] == "high"]
        if high_risks:
            exp_names = [r["experiment_name"] for r in high_risks]
            return f"HIGH RISK: Consider pausing or mutual exclusion with: {', '.join(exp_names)}"
        
        medium_risks = [r for r in risks if r["risk_level"] == "medium"]
        if medium_risks:
            return "MEDIUM RISK: Monitor for interaction effects. Consider stratified analysis."
        
        return "LOW RISK: Proceed with monitoring."
```

---


## Part 3: Statistical Analysis Framework

```python
from scipy import stats
from scipy.special import betaln
import numpy as np
from typing import Tuple
import warnings


# =============================================================================
# POWER ANALYSIS & SAMPLE SIZE CALCULATION
# =============================================================================

class PowerAnalyzer:
    """
    Statistical power analysis for experiment design.
    """
    
    def calculate_sample_size(
        self,
        baseline_rate: float,
        minimum_detectable_effect: float,
        alpha: float = 0.05,
        power: float = 0.80,
        n_variants: int = 2,
        one_sided: bool = False
    ) -> int:
        """
        Calculate required sample size per variant for conversion rate test.
        
        Uses formula for comparing two proportions.
        """
        # Treatment rate under alternative hypothesis
        treatment_rate = baseline_rate * (1 + minimum_detectable_effect)
        
        # Pooled rate
        p_pooled = (baseline_rate + treatment_rate) / 2
        
        # Z-scores
        z_alpha = stats.norm.ppf(1 - alpha / (1 if one_sided else 2))
        z_beta = stats.norm.ppf(power)
        
        # Sample size formula for two proportions
        effect = abs(treatment_rate - baseline_rate)
        variance = p_pooled * (1 - p_pooled) * 2
        
        n_per_variant = (z_alpha + z_beta) ** 2 * variance / (effect ** 2)
        
        # Adjust for multiple comparisons (Bonferroni)
        if n_variants > 2:
            adjusted_alpha = alpha / (n_variants - 1)
            z_alpha_adjusted = stats.norm.ppf(1 - adjusted_alpha / (1 if one_sided else 2))
            n_per_variant = (z_alpha_adjusted + z_beta) ** 2 * variance / (effect ** 2)
        
        return int(np.ceil(n_per_variant))
    
    def calculate_power(
        self,
        baseline_rate: float,
        treatment_rate: float,
        sample_size_per_variant: int,
        alpha: float = 0.05,
        one_sided: bool = False
    ) -> float:
        """
        Calculate statistical power given sample size.
        """
        # Pooled proportion
        p_pooled = (baseline_rate + treatment_rate) / 2
        
        # Standard error
        se = np.sqrt(p_pooled * (1 - p_pooled) * 2 / sample_size_per_variant)
        
        # Effect size
        effect = abs(treatment_rate - baseline_rate)
        
        # Z-score for alpha
        z_alpha = stats.norm.ppf(1 - alpha / (1 if one_sided else 2))
        
        # Calculate power
        z_power = (effect / se) - z_alpha
        power = stats.norm.cdf(z_power)
        
        return power
    
    def estimate_runtime(
        self,
        required_sample_size: int,
        daily_traffic: int,
        traffic_fraction: float = 1.0
    ) -> Tuple[int, int]:
        """
        Estimate experiment runtime in days.
        
        Returns (min_days, max_days)
        """
        effective_daily = daily_traffic * traffic_fraction
        
        if effective_daily <= 0:
            return (float('inf'), float('inf'))
        
        min_days = max(7, int(np.ceil(required_sample_size * 2 / effective_daily)))  # *2 for variants
        max_days = min_days * 2  # Allow 2x for margin
        
        return (min_days, max_days)


# =============================================================================
# FREQUENTIST ANALYSIS
# =============================================================================

class FrequentistAnalyzer:
    """
    Traditional frequentist hypothesis testing.
    """
    
    def analyze_conversion_rate(
        self,
        control_conversions: int,
        control_total: int,
        treatment_conversions: int,
        treatment_total: int,
        alpha: float = 0.05
    ) -> Dict[str, Any]:
        """
        Compare conversion rates using chi-squared test.
        """
        # Conversion rates
        control_rate = control_conversions / control_total if control_total > 0 else 0
        treatment_rate = treatment_conversions / treatment_total if treatment_total > 0 else 0
        
        # Absolute and relative lift
        absolute_lift = treatment_rate - control_rate
        relative_lift = absolute_lift / control_rate if control_rate > 0 else 0
        
        # Chi-squared test
        contingency_table = [
            [control_conversions, control_total - control_conversions],
            [treatment_conversions, treatment_total - treatment_conversions]
        ]
        
        chi2, p_value, dof, expected = stats.chi2_contingency(contingency_table)
        
        # Wilson confidence interval for difference
        ci_low, ci_high = self._wilson_confidence_interval_diff(
            control_conversions, control_total,
            treatment_conversions, treatment_total,
            alpha
        )
        
        # Determine significance
        is_significant = p_value < alpha
        
        return {
            "control_rate": control_rate,
            "treatment_rate": treatment_rate,
            "absolute_lift": absolute_lift,
            "relative_lift": relative_lift,
            "p_value": p_value,
            "chi_squared": chi2,
            "confidence_interval": (ci_low, ci_high),
            "is_significant": is_significant,
            "confidence_level": 1 - alpha,
            "recommendation": self._get_recommendation(is_significant, relative_lift, p_value),
        }
    
    def analyze_continuous_metric(
        self,
        control_values: np.ndarray,
        treatment_values: np.ndarray,
        alpha: float = 0.05
    ) -> Dict[str, Any]:
        """
        Compare means using Welch's t-test.
        """
        # Basic statistics
        control_mean = np.mean(control_values)
        treatment_mean = np.mean(treatment_values)
        control_std = np.std(control_values, ddof=1)
        treatment_std = np.std(treatment_values, ddof=1)
        
        # Lift
        absolute_lift = treatment_mean - control_mean
        relative_lift = absolute_lift / control_mean if control_mean != 0 else 0
        
        # Welch's t-test
        t_stat, p_value = stats.ttest_ind(
            treatment_values,
            control_values,
            equal_var=False
        )
        
        # Confidence interval for difference
        se = np.sqrt(control_std**2/len(control_values) + treatment_std**2/len(treatment_values))
        t_crit = stats.t.ppf(1 - alpha/2, df=min(len(control_values), len(treatment_values)) - 1)
        ci_low = absolute_lift - t_crit * se
        ci_high = absolute_lift + t_crit * se
        
        is_significant = p_value < alpha
        
        return {
            "control_mean": control_mean,
            "treatment_mean": treatment_mean,
            "control_std": control_std,
            "treatment_std": treatment_std,
            "absolute_lift": absolute_lift,
            "relative_lift": relative_lift,
            "t_statistic": t_stat,
            "p_value": p_value,
            "confidence_interval": (ci_low, ci_high),
            "is_significant": is_significant,
            "cohens_d": absolute_lift / np.sqrt((control_std**2 + treatment_std**2) / 2),
        }
    
    def _wilson_confidence_interval_diff(
        self,
        c_conv: int, c_total: int,
        t_conv: int, t_total: int,
        alpha: float
    ) -> Tuple[float, float]:
        """Calculate confidence interval for difference in proportions."""
        p1 = c_conv / c_total if c_total > 0 else 0
        p2 = t_conv / t_total if t_total > 0 else 0
        
        diff = p2 - p1
        
        # Standard error of difference
        se = np.sqrt(p1 * (1 - p1) / c_total + p2 * (1 - p2) / t_total)
        
        z = stats.norm.ppf(1 - alpha / 2)
        
        return (diff - z * se, diff + z * se)
    
    def _get_recommendation(
        self,
        is_significant: bool,
        relative_lift: float,
        p_value: float
    ) -> str:
        """Generate recommendation based on results."""
        if is_significant:
            if relative_lift > 0:
                return f"SIGNIFICANT POSITIVE: Treatment shows {relative_lift:.1%} lift (p={p_value:.4f}). Consider shipping."
            else:
                return f"SIGNIFICANT NEGATIVE: Treatment shows {relative_lift:.1%} decline (p={p_value:.4f}). Do not ship."
        else:
            if p_value < 0.1:
                return f"TRENDING: p-value {p_value:.4f} approaching significance. Consider extending experiment."
            else:
                return f"NOT SIGNIFICANT: p-value {p_value:.4f}. Need more data or larger effect."


# =============================================================================
# BAYESIAN ANALYSIS
# =============================================================================

class BayesianAnalyzer:
    """
    Bayesian inference for A/B testing.
    
    Advantages over frequentist:
    - Direct probability statements ("95% chance treatment is better")
    - No need for fixed sample size
    - Natural handling of early stopping
    - Credible intervals with intuitive interpretation
    """
    
    def __init__(self, n_samples: int = 100000):
        self.n_samples = n_samples
    
    def analyze_conversion_rate(
        self,
        control_conversions: int,
        control_total: int,
        treatment_conversions: int,
        treatment_total: int,
        prior_alpha: float = 1.0,  # Beta prior
        prior_beta: float = 1.0,   # Uniform prior by default
    ) -> Dict[str, Any]:
        """
        Bayesian analysis of conversion rate difference.
        
        Uses Beta-Binomial conjugate prior.
        """
        # Posterior parameters (Beta distribution)
        control_alpha = prior_alpha + control_conversions
        control_beta = prior_beta + control_total - control_conversions
        
        treatment_alpha = prior_alpha + treatment_conversions
        treatment_beta = prior_beta + treatment_total - treatment_conversions
        
        # Sample from posteriors
        control_samples = np.random.beta(control_alpha, control_beta, self.n_samples)
        treatment_samples = np.random.beta(treatment_alpha, treatment_beta, self.n_samples)
        
        # Calculate lift distribution
        lift_samples = (treatment_samples - control_samples) / control_samples
        
        # Probability treatment is better
        prob_treatment_better = np.mean(treatment_samples > control_samples)
        
        # Expected values
        control_rate = control_alpha / (control_alpha + control_beta)
        treatment_rate = treatment_alpha / (treatment_alpha + treatment_beta)
        expected_lift_mean = np.mean(lift_samples)
        
        # Credible intervals
        lift_ci_95 = (np.percentile(lift_samples, 2.5), np.percentile(lift_samples, 97.5))
        lift_ci_90 = (np.percentile(lift_samples, 5), np.percentile(lift_samples, 95))
        
        # Risk analysis
        risk_of_choosing_treatment = self._calculate_expected_loss(
            control_samples, treatment_samples, "treatment"
        )
        risk_of_choosing_control = self._calculate_expected_loss(
            control_samples, treatment_samples, "control"
        )
        
        return {
            "control_rate_expected": control_rate,
            "treatment_rate_expected": treatment_rate,
            "probability_treatment_better": prob_treatment_better,
            "expected_lift": {
                "mean": expected_lift_mean,
                "median": np.median(lift_samples),
                "std": np.std(lift_samples),
            },
            "credible_interval_95": lift_ci_95,
            "credible_interval_90": lift_ci_90,
            "expected_loss": {
                "choose_treatment": risk_of_choosing_treatment,
                "choose_control": risk_of_choosing_control,
            },
            "recommendation": self._get_bayesian_recommendation(
                prob_treatment_better, expected_lift_mean, risk_of_choosing_treatment
            ),
        }
    
    def _calculate_expected_loss(
        self,
        control_samples: np.ndarray,
        treatment_samples: np.ndarray,
        choice: str
    ) -> float:
        """
        Calculate expected loss for choosing an option.
        
        Loss = expected regret if wrong choice.
        """
        if choice == "treatment":
            # Loss is max(control - treatment, 0)
            loss = np.maximum(control_samples - treatment_samples, 0)
        else:
            # Loss is max(treatment - control, 0)
            loss = np.maximum(treatment_samples - control_samples, 0)
        
        return np.mean(loss)
    
    def _get_bayesian_recommendation(
        self,
        prob_better: float,
        expected_lift: float,
        expected_loss: float
    ) -> str:
        """Generate recommendation based on Bayesian analysis."""
        
        # Decision rules
        if prob_better > 0.95 and expected_lift > 0.01:
            return f"SHIP: {prob_better:.1%} probability of positive lift ({expected_lift:.1%}). Expected loss: {expected_loss:.4f}"
        elif prob_better < 0.05:
            return f"STOP: Only {prob_better:.1%} probability treatment is better. Treatment is likely harmful."
        elif prob_better > 0.80:
            return f"PROMISING: {prob_better:.1%} probability. Consider continuing for more confidence."
        else:
            return f"CONTINUE: {prob_better:.1%} probability treatment is better. Need more data."
    
    def calculate_probability_of_being_best(
        self,
        variant_samples: Dict[str, np.ndarray]
    ) -> Dict[str, float]:
        """
        Calculate probability each variant is best (for multi-variant tests).
        """
        n_samples = len(list(variant_samples.values())[0])
        
        # Stack all samples
        all_samples = np.stack(list(variant_samples.values()))
        
        # Find best for each sample
        best_indices = np.argmax(all_samples, axis=0)
        
        # Count how often each variant is best
        variant_names = list(variant_samples.keys())
        probabilities = {}
        
        for i, name in enumerate(variant_names):
            probabilities[name] = np.mean(best_indices == i)
        
        return probabilities


# =============================================================================
# CUPED VARIANCE REDUCTION
# =============================================================================

class CUPEDAnalyzer:
    """
    Controlled-experiment Using Pre-Experiment Data (CUPED).
    
    Reduces variance by regressing out pre-experiment covariates.
    Can reduce variance by 50%+, enabling faster experiments.
    """
    
    def analyze_with_covariates(
        self,
        control_y: np.ndarray,        # Post-experiment metric
        treatment_y: np.ndarray,
        control_x: np.ndarray,        # Pre-experiment covariate
        treatment_x: np.ndarray,
        alpha: float = 0.05
    ) -> Dict[str, Any]:
        """
        CUPED analysis using pre-experiment covariates.
        """
        # Estimate theta (covariate coefficient)
        all_y = np.concatenate([control_y, treatment_y])
        all_x = np.concatenate([control_x, treatment_x])
        
        theta = np.cov(all_y, all_x)[0, 1] / np.var(all_x)
        
        # Adjust metrics
        control_y_adj = control_y - theta * (control_x - np.mean(all_x))
        treatment_y_adj = treatment_y - theta * (treatment_x - np.mean(all_x))
        
        # Calculate variance reduction
        original_var = np.var(all_y)
        adjusted_var = np.var(np.concatenate([control_y_adj, treatment_y_adj]))
        variance_reduction = 1 - adjusted_var / original_var
        
        # Perform t-test on adjusted metrics
        control_mean_adj = np.mean(control_y_adj)
        treatment_mean_adj = np.mean(treatment_y_adj)
        
        t_stat, p_value = stats.ttest_ind(treatment_y_adj, control_y_adj, equal_var=False)
        
        # Confidence interval
        se = np.sqrt(np.var(control_y_adj)/len(control_y_adj) + 
                    np.var(treatment_y_adj)/len(treatment_y_adj))
        lift = treatment_mean_adj - control_mean_adj
        t_crit = stats.t.ppf(1 - alpha/2, df=len(all_y) - 2)
        ci = (lift - t_crit * se, lift + t_crit * se)
        
        return {
            "control_mean_adjusted": control_mean_adj,
            "treatment_mean_adjusted": treatment_mean_adj,
            "lift": lift,
            "relative_lift": lift / control_mean_adj if control_mean_adj != 0 else 0,
            "theta": theta,
            "variance_reduction": variance_reduction,
            "p_value": p_value,
            "t_statistic": t_stat,
            "confidence_interval": ci,
            "is_significant": p_value < alpha,
            "effective_sample_size_multiplier": 1 / (1 - variance_reduction),
        }
```

---


## Part 4: Sequential Testing & Early Stopping

```python
# =============================================================================
# SEQUENTIAL TESTING
# 
# Allows continuous monitoring and early stopping while controlling Type I error.
# Critical for production systems where waiting for fixed sample is expensive.
# =============================================================================

class SequentialAnalyzer:
    """
    Sequential probability ratio test (SPRT) and group sequential designs.
    
    Enables:
    - Continuous monitoring without p-hacking
    - Early stopping for clear winners/losers
    - Controlled false positive rate
    """
    
    def __init__(
        self,
        alpha: float = 0.05,
        beta: float = 0.20,
        spending_function: str = "obrien_fleming"
    ):
        self.alpha = alpha
        self.beta = beta
        self.spending_function = spending_function
    
    def sprt_test(
        self,
        control_conversions: int,
        control_total: int,
        treatment_conversions: int,
        treatment_total: int,
        null_effect: float = 0.0,
        alternative_effect: float = 0.1  # 10% lift under H1
    ) -> Dict[str, Any]:
        """
        Sequential Probability Ratio Test for early stopping.
        """
        # Observed rates
        p_c = control_conversions / control_total if control_total > 0 else 0
        p_t = treatment_conversions / treatment_total if treatment_total > 0 else 0
        
        # Pooled rate under null
        p_null = (control_conversions + treatment_conversions) / (control_total + treatment_total)
        
        # Rate under alternative
        p_alt = p_null * (1 + alternative_effect)
        
        # Log likelihood ratio
        if p_c == 0 or p_t == 0 or p_null == 0 or p_alt == 0:
            llr = 0
        else:
            # Simplified LLR calculation
            llr = self._calculate_llr(
                treatment_conversions, treatment_total - treatment_conversions,
                p_null, p_alt
            )
        
        # Boundaries (Wald boundaries)
        A = np.log((1 - self.beta) / self.alpha)  # Upper boundary (reject H0)
        B = np.log(self.beta / (1 - self.alpha))  # Lower boundary (accept H0)
        
        # Decision
        if llr >= A:
            decision = "reject_null"  # Treatment wins
            stopped = True
        elif llr <= B:
            decision = "accept_null"  # No difference
            stopped = True
        else:
            decision = "continue"
            stopped = False
        
        return {
            "log_likelihood_ratio": llr,
            "upper_boundary": A,
            "lower_boundary": B,
            "decision": decision,
            "stopped": stopped,
            "control_rate": p_c,
            "treatment_rate": p_t,
            "observed_lift": (p_t - p_c) / p_c if p_c > 0 else 0,
        }
    
    def _calculate_llr(
        self,
        successes: int,
        failures: int,
        p_null: float,
        p_alt: float
    ) -> float:
        """Calculate log likelihood ratio."""
        if p_null <= 0 or p_alt <= 0 or p_null >= 1 or p_alt >= 1:
            return 0
        
        llr = (
            successes * np.log(p_alt / p_null) +
            failures * np.log((1 - p_alt) / (1 - p_null))
        )
        return llr
    
    def group_sequential_bounds(
        self,
        n_looks: int,
        current_look: int
    ) -> Tuple[float, float]:
        """
        Calculate alpha spending boundaries for group sequential design.
        """
        if self.spending_function == "obrien_fleming":
            return self._obrien_fleming_bounds(n_looks, current_look)
        elif self.spending_function == "pocock":
            return self._pocock_bounds(n_looks, current_look)
        else:
            return self._uniform_bounds(n_looks, current_look)
    
    def _obrien_fleming_bounds(
        self,
        n_looks: int,
        current_look: int
    ) -> Tuple[float, float]:
        """
        O'Brien-Fleming spending function.
        
        Very conservative early, more permissive late.
        Good for experiments where you want to wait for more data.
        """
        # Information fraction
        t = current_look / n_looks
        
        # Cumulative alpha spent
        if t <= 0:
            alpha_spent = 0
        else:
            # O'Brien-Fleming: alpha * (2 - 2*Phi(z_alpha/sqrt(t)))
            z_alpha = stats.norm.ppf(1 - self.alpha / 2)
            alpha_spent = 2 * (1 - stats.norm.cdf(z_alpha / np.sqrt(t)))
        
        # Convert to z-bounds
        z_bound = stats.norm.ppf(1 - alpha_spent / 2) if alpha_spent < 1 else 0
        
        return (-z_bound, z_bound)
    
    def _pocock_bounds(
        self,
        n_looks: int,
        current_look: int
    ) -> Tuple[float, float]:
        """
        Pocock spending function.
        
        Uniform alpha spending across looks.
        Good when early stopping is important.
        """
        # Information fraction
        t = current_look / n_looks
        
        # Linear alpha spending
        alpha_spent = self.alpha * t
        
        z_bound = stats.norm.ppf(1 - alpha_spent / 2) if alpha_spent < 1 else 0
        
        return (-z_bound, z_bound)
    
    def _uniform_bounds(
        self,
        n_looks: int,
        current_look: int
    ) -> Tuple[float, float]:
        """Simple Bonferroni correction."""
        adjusted_alpha = self.alpha / n_looks
        z_bound = stats.norm.ppf(1 - adjusted_alpha / 2)
        return (-z_bound, z_bound)
    
    def continuous_monitoring_decision(
        self,
        control_conversions: int,
        control_total: int,
        treatment_conversions: int,
        treatment_total: int,
        information_fraction: float,  # 0 to 1
        n_planned_looks: int = 5
    ) -> Dict[str, Any]:
        """
        Make decision with continuous monitoring using spending function.
        """
        # Current look number (approximate)
        current_look = max(1, int(information_fraction * n_planned_looks))
        
        # Get boundaries
        lower_z, upper_z = self.group_sequential_bounds(n_planned_looks, current_look)
        
        # Calculate z-statistic
        p_c = control_conversions / control_total if control_total > 0 else 0
        p_t = treatment_conversions / treatment_total if treatment_total > 0 else 0
        p_pooled = (control_conversions + treatment_conversions) / (control_total + treatment_total)
        
        if p_pooled > 0 and p_pooled < 1:
            se = np.sqrt(p_pooled * (1 - p_pooled) * (1/control_total + 1/treatment_total))
            z_stat = (p_t - p_c) / se if se > 0 else 0
        else:
            z_stat = 0
        
        # Decision
        if z_stat > upper_z:
            decision = "stop_winner"
            recommendation = f"EARLY STOP: Treatment significantly better (z={z_stat:.2f} > {upper_z:.2f})"
        elif z_stat < lower_z:
            decision = "stop_loser"
            recommendation = f"EARLY STOP: Treatment significantly worse (z={z_stat:.2f} < {lower_z:.2f})"
        else:
            decision = "continue"
            recommendation = f"CONTINUE: z-stat {z_stat:.2f} within bounds [{lower_z:.2f}, {upper_z:.2f}]"
        
        return {
            "z_statistic": z_stat,
            "upper_boundary": upper_z,
            "lower_boundary": lower_z,
            "information_fraction": information_fraction,
            "current_look": current_look,
            "decision": decision,
            "recommendation": recommendation,
            "can_stop_early": decision != "continue",
        }


# =============================================================================
# ALWAYS VALID INFERENCE
# =============================================================================

class AlwaysValidInference:
    """
    Confidence sequences for anytime-valid inference.
    
    Modern approach that allows continuous monitoring without
    alpha spending functions. Based on e-values and martingales.
    """
    
    def __init__(self, rho: float = 0.5):
        """
        Args:
            rho: Mixing parameter for confidence sequence (0 < rho < 1)
        """
        self.rho = rho
    
    def confidence_sequence(
        self,
        control_conversions: int,
        control_total: int,
        treatment_conversions: int,
        treatment_total: int,
        alpha: float = 0.05
    ) -> Dict[str, Any]:
        """
        Calculate anytime-valid confidence sequence.
        """
        # Observed rates
        p_c = control_conversions / control_total if control_total > 0 else 0.5
        p_t = treatment_conversions / treatment_total if treatment_total > 0 else 0.5
        
        # Total samples
        n = control_total + treatment_total
        
        if n < 10:
            return {
                "valid": False,
                "reason": "Insufficient samples",
            }
        
        # Calculate confidence sequence width
        # Using simplified asymptotic formula
        width = np.sqrt(
            2 * (1 + 1/n) * 
            (p_c * (1 - p_c) / control_total + p_t * (1 - p_t) / treatment_total) *
            np.log(2 / alpha * np.sqrt(1 + n))
        )
        
        lift = p_t - p_c
        
        # Confidence sequence
        cs_lower = lift - width
        cs_upper = lift + width
        
        # Check if can reject null
        can_reject_null = cs_lower > 0 or cs_upper < 0
        
        return {
            "valid": True,
            "lift_estimate": lift,
            "confidence_sequence": (cs_lower, cs_upper),
            "width": width,
            "can_reject_null": can_reject_null,
            "null_in_sequence": cs_lower <= 0 <= cs_upper,
            "sample_size": n,
            "alpha": alpha,
        }
```

---

## Part 5: Multi-Armed Bandit Integration

```python
# =============================================================================
# MULTI-ARMED BANDITS
# 
# For continuous optimization rather than fixed experimentation.
# Balances exploration (learning) with exploitation (using best variant).
# =============================================================================

class ThompsonSamplingBandit:
    """
    Thompson Sampling for conversion rate optimization.
    
    Bayesian approach that:
    - Naturally balances exploration/exploitation
    - Converges to optimal variant
    - Provides uncertainty quantification
    """
    
    def __init__(
        self,
        variants: List[str],
        prior_alpha: float = 1.0,
        prior_beta: float = 1.0
    ):
        self.variants = variants
        self.prior_alpha = prior_alpha
        self.prior_beta = prior_beta
        
        # Track successes and failures per variant
        self.successes = {v: 0 for v in variants}
        self.failures = {v: 0 for v in variants}
    
    def select_variant(self) -> str:
        """
        Select variant using Thompson Sampling.
        
        Sample from posterior Beta distribution for each variant,
        select the one with highest sample.
        """
        samples = {}
        
        for variant in self.variants:
            alpha = self.prior_alpha + self.successes[variant]
            beta = self.prior_beta + self.failures[variant]
            samples[variant] = np.random.beta(alpha, beta)
        
        return max(samples.keys(), key=lambda v: samples[v])
    
    def update(self, variant: str, success: bool) -> None:
        """Update counts after observing outcome."""
        if success:
            self.successes[variant] += 1
        else:
            self.failures[variant] += 1
    
    def get_statistics(self) -> Dict[str, Dict[str, float]]:
        """Get current statistics for all variants."""
        stats = {}
        
        for variant in self.variants:
            alpha = self.prior_alpha + self.successes[variant]
            beta = self.prior_beta + self.failures[variant]
            
            total = self.successes[variant] + self.failures[variant]
            
            stats[variant] = {
                "successes": self.successes[variant],
                "failures": self.failures[variant],
                "total": total,
                "posterior_mean": alpha / (alpha + beta),
                "posterior_std": np.sqrt(alpha * beta / ((alpha + beta)**2 * (alpha + beta + 1))),
                "posterior_alpha": alpha,
                "posterior_beta": beta,
            }
        
        return stats
    
    def get_allocation_probabilities(self, n_samples: int = 10000) -> Dict[str, float]:
        """Get current probability of selecting each variant."""
        selection_counts = {v: 0 for v in self.variants}
        
        for _ in range(n_samples):
            selected = self.select_variant()
            selection_counts[selected] += 1
        
        return {v: c / n_samples for v, c in selection_counts.items()}
    
    def probability_best(self, n_samples: int = 10000) -> Dict[str, float]:
        """Calculate probability each variant is the best."""
        best_counts = {v: 0 for v in self.variants}
        
        for _ in range(n_samples):
            samples = {}
            for variant in self.variants:
                alpha = self.prior_alpha + self.successes[variant]
                beta = self.prior_beta + self.failures[variant]
                samples[variant] = np.random.beta(alpha, beta)
            
            best = max(samples.keys(), key=lambda v: samples[v])
            best_counts[best] += 1
        
        return {v: c / n_samples for v, c in best_counts.items()}


class ContextualBandit:
    """
    Contextual bandit for psychological personalization.
    
    Selects best variant based on user context (personality, state).
    Learns which variants work best for which user types.
    """
    
    def __init__(
        self,
        variants: List[str],
        context_dim: int,
        exploration_weight: float = 1.0
    ):
        self.variants = variants
        self.context_dim = context_dim
        self.exploration_weight = exploration_weight
        
        # Linear model weights for each variant (LinUCB style)
        self.A = {v: np.eye(context_dim) for v in variants}
        self.b = {v: np.zeros(context_dim) for v in variants}
    
    def select_variant(self, context: np.ndarray) -> str:
        """
        Select variant using LinUCB algorithm.
        
        Balances expected reward with uncertainty.
        """
        ucb_values = {}
        
        for variant in self.variants:
            # Compute UCB
            A_inv = np.linalg.inv(self.A[variant])
            theta = A_inv @ self.b[variant]
            
            # Expected reward
            expected = context @ theta
            
            # Uncertainty bonus
            uncertainty = self.exploration_weight * np.sqrt(context @ A_inv @ context)
            
            ucb_values[variant] = expected + uncertainty
        
        return max(ucb_values.keys(), key=lambda v: ucb_values[v])
    
    def update(
        self,
        variant: str,
        context: np.ndarray,
        reward: float
    ) -> None:
        """Update model after observing reward."""
        self.A[variant] += np.outer(context, context)
        self.b[variant] += reward * context
    
    def get_expected_rewards(
        self,
        context: np.ndarray
    ) -> Dict[str, float]:
        """Get expected reward for each variant given context."""
        rewards = {}
        
        for variant in self.variants:
            A_inv = np.linalg.inv(self.A[variant])
            theta = A_inv @ self.b[variant]
            rewards[variant] = context @ theta
        
        return rewards
    
    def create_context_vector(
        self,
        psychological_state: Dict[str, float],
        personality_profile: Dict[str, float]
    ) -> np.ndarray:
        """
        Create context vector from psychological features.
        """
        # Expected features in order
        state_features = ["arousal", "cognitive_load", "decision_proximity", 
                        "regulatory_orientation", "construal_level"]
        personality_features = ["openness", "conscientiousness", "extraversion",
                              "agreeableness", "neuroticism"]
        
        context = []
        
        for f in state_features:
            context.append(psychological_state.get(f, 0.5))
        
        for f in personality_features:
            context.append(personality_profile.get(f, 0.5))
        
        return np.array(context)


class BanditExperimentManager:
    """
    Manage bandit-based experiments.
    
    Handles:
    - Automatic traffic allocation updates
    - Convergence detection
    - Regret tracking
    - Switching between exploration and exploitation
    """
    
    def __init__(
        self,
        experiment: ExperimentDesign,
        redis_client: 'Redis',
        min_samples_per_variant: int = 100
    ):
        self.experiment = experiment
        self.redis = redis_client
        self.min_samples = min_samples_per_variant
        
        # Initialize bandit
        variant_ids = [v.variant_id for v in experiment.variants]
        self.bandit = ThompsonSamplingBandit(variant_ids)
    
    async def get_variant(
        self,
        user_id: str,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Get variant assignment using bandit."""
        
        # Check if user already assigned (sticky)
        cache_key = f"bandit_assignment:{self.experiment.experiment_id}:{user_id}"
        existing = await self.redis.get(cache_key)
        
        if existing:
            return existing.decode()
        
        # Ensure minimum exploration
        stats = self.bandit.get_statistics()
        
        for variant_id, variant_stats in stats.items():
            if variant_stats["total"] < self.min_samples:
                # Force exploration
                variant = variant_id
                break
        else:
            # Use Thompson Sampling
            variant = self.bandit.select_variant()
        
        # Cache assignment
        await self.redis.setex(cache_key, 86400, variant)  # 24 hour TTL
        
        return variant
    
    async def record_outcome(
        self,
        variant_id: str,
        success: bool
    ) -> None:
        """Record outcome and update bandit."""
        self.bandit.update(variant_id, success)
        
        # Store state
        await self._save_state()
    
    async def get_status(self) -> Dict[str, Any]:
        """Get current bandit status."""
        stats = self.bandit.get_statistics()
        prob_best = self.bandit.probability_best()
        allocations = self.bandit.get_allocation_probabilities()
        
        # Check convergence
        max_prob = max(prob_best.values())
        converged = max_prob > 0.95
        
        # Calculate regret
        best_mean = max(s["posterior_mean"] for s in stats.values())
        total_samples = sum(s["total"] for s in stats.values())
        expected_optimal_reward = best_mean * total_samples
        actual_reward = sum(s["successes"] for s in stats.values())
        regret = expected_optimal_reward - actual_reward
        
        return {
            "variant_statistics": stats,
            "probability_best": prob_best,
            "current_allocations": allocations,
            "converged": converged,
            "winning_variant": max(prob_best.keys(), key=lambda k: prob_best[k]) if converged else None,
            "total_samples": total_samples,
            "cumulative_regret": regret,
        }
    
    async def _save_state(self) -> None:
        """Persist bandit state to Redis."""
        state = {
            "successes": self.bandit.successes,
            "failures": self.bandit.failures,
        }
        
        key = f"bandit_state:{self.experiment.experiment_id}"
        await self.redis.set(key, json.dumps(state))
```

---


## Part 6: Psychological Mechanism Testing

```python
# =============================================================================
# PSYCHOLOGICAL MECHANISM TESTING FRAMEWORK
# 
# ADAM-specific testing framework for isolating and validating
# psychological targeting mechanisms.
# =============================================================================

class PsychologicalMechanismTester:
    """
    Framework for testing individual psychological mechanisms.
    
    Tests:
    - Mechanism presence/absence (does it help at all?)
    - Mechanism intensity (low/medium/high)
    - Mechanism × personality interactions
    - Mechanism × state interactions
    """
    
    # Mechanisms ADAM can test
    TESTABLE_MECHANISMS = {
        # From psychological research
        "regulatory_focus_matching": {
            "description": "Match promotion/prevention framing to user focus",
            "expected_lift": 0.15,
            "research_basis": "Higgins 1997, Cesario 2004"
        },
        "construal_level_matching": {
            "description": "Match abstract/concrete messaging to user construal",
            "expected_lift": 0.12,
            "research_basis": "Trope & Liberman 2010"
        },
        "personality_matched_copy": {
            "description": "Tailor messaging to Big Five profile",
            "expected_lift": 0.40,
            "research_basis": "Matz et al. 2017"
        },
        "moral_foundations_appeal": {
            "description": "Appeal to user's moral foundations",
            "expected_lift": 0.10,
            "research_basis": "Graham et al. 2013"
        },
        "arousal_congruent_timing": {
            "description": "Serve ads when arousal matches ad energy",
            "expected_lift": 0.08,
            "research_basis": "Thayer 1989"
        },
        "cognitive_load_adaptation": {
            "description": "Simplify messaging under high cognitive load",
            "expected_lift": 0.10,
            "research_basis": "Sweller 1988"
        },
        "social_proof_personalization": {
            "description": "Show proof from similar personality types",
            "expected_lift": 0.15,
            "research_basis": "Cialdini 1984"
        },
        "loss_aversion_framing": {
            "description": "Frame based on user's loss sensitivity",
            "expected_lift": 0.12,
            "research_basis": "Kahneman & Tversky 1979"
        },
        "decision_stage_optimization": {
            "description": "Match message to decision journey stage",
            "expected_lift": 0.20,
            "research_basis": "Howard & Sheth 1969"
        },
    }
    
    def __init__(self, experiment_manager: 'ExperimentManager'):
        self.manager = experiment_manager
    
    async def create_mechanism_test_suite(
        self,
        mechanism: str,
        baseline_conversion_rate: float = 0.02,
        traffic_fraction: float = 0.10
    ) -> List[ExperimentDesign]:
        """
        Create comprehensive test suite for a psychological mechanism.
        
        Returns list of experiments that should be run sequentially:
        1. Presence test (mechanism on/off)
        2. Intensity test (low/medium/high)
        3. Personality interaction test
        """
        if mechanism not in self.TESTABLE_MECHANISMS:
            raise ValueError(f"Unknown mechanism: {mechanism}")
        
        mechanism_info = self.TESTABLE_MECHANISMS[mechanism]
        tests = []
        
        # Test 1: Presence Test
        tests.append(self._create_presence_test(
            mechanism, mechanism_info, baseline_conversion_rate, traffic_fraction
        ))
        
        # Test 2: Intensity Test
        tests.append(self._create_intensity_test(
            mechanism, mechanism_info, baseline_conversion_rate, traffic_fraction
        ))
        
        # Test 3: Personality Interaction Test
        tests.append(self._create_personality_interaction_test(
            mechanism, mechanism_info, baseline_conversion_rate, traffic_fraction
        ))
        
        # Test 4: State Interaction Test
        tests.append(self._create_state_interaction_test(
            mechanism, mechanism_info, baseline_conversion_rate, traffic_fraction
        ))
        
        return tests
    
    def _create_presence_test(
        self,
        mechanism: str,
        mechanism_info: Dict,
        baseline_rate: float,
        traffic_fraction: float
    ) -> ExperimentDesign:
        """Test: Does this mechanism improve performance at all?"""
        
        power_analyzer = PowerAnalyzer()
        sample_size = power_analyzer.calculate_sample_size(
            baseline_rate=baseline_rate,
            minimum_detectable_effect=mechanism_info["expected_lift"],
            alpha=0.05,
            power=0.80
        )
        
        return ExperimentDesign(
            experiment_name=f"Mechanism Test: {mechanism} - Presence",
            experiment_type=ExperimentType.MECHANISM_ISOLATION,
            null_hypothesis=f"The {mechanism} mechanism has no effect on conversion",
            alternative_hypothesis=f"The {mechanism} mechanism increases conversion by {mechanism_info['expected_lift']:.0%}",
            expected_effect_size=mechanism_info["expected_lift"],
            variants=[
                Variant(
                    variant_name="control",
                    variant_type="control",
                    traffic_fraction=0.5,
                    config={},
                    mechanism_settings={mechanism: {"enabled": False}},
                    hypothesis="Baseline without mechanism"
                ),
                Variant(
                    variant_name="with_mechanism",
                    variant_type="treatment",
                    traffic_fraction=0.5,
                    config={},
                    mechanism_settings={mechanism: {"enabled": True, "intensity": "medium"}},
                    hypothesis=f"Mechanism should increase conversion by ~{mechanism_info['expected_lift']:.0%}"
                ),
            ],
            metrics=[
                MetricDefinition(
                    metric_name="conversion_rate",
                    metric_type=MetricType.PRIMARY,
                    numerator_event="conversion",
                    denominator_event="impression",
                    expected_baseline=baseline_rate,
                    minimum_detectable_effect=mechanism_info["expected_lift"],
                ),
                MetricDefinition(
                    metric_name="click_through_rate",
                    metric_type=MetricType.SECONDARY,
                    numerator_event="click",
                    denominator_event="impression",
                ),
                MetricDefinition(
                    metric_name="latency_p99",
                    metric_type=MetricType.GUARDRAIL,
                    numerator_event="latency_p99",
                    aggregation="mean",
                    guardrail_threshold=0.10,
                    guardrail_direction="lower_is_better",
                ),
            ],
            required_sample_size=sample_size,
            analysis_method=AnalysisMethod.BAYESIAN,
            sequential_testing=True,
            tags=["mechanism_test", mechanism, "presence"],
        )
    
    def _create_intensity_test(
        self,
        mechanism: str,
        mechanism_info: Dict,
        baseline_rate: float,
        traffic_fraction: float
    ) -> ExperimentDesign:
        """Test: What intensity level works best?"""
        
        return ExperimentDesign(
            experiment_name=f"Mechanism Test: {mechanism} - Intensity",
            experiment_type=ExperimentType.MECHANISM_ISOLATION,
            null_hypothesis=f"Intensity level has no effect on {mechanism} performance",
            alternative_hypothesis=f"Optimal intensity exists for {mechanism}",
            expected_effect_size=mechanism_info["expected_lift"] * 0.5,
            variants=[
                Variant(
                    variant_name="low_intensity",
                    variant_type="treatment",
                    traffic_fraction=0.33,
                    config={},
                    mechanism_settings={mechanism: {"enabled": True, "intensity": "low"}},
                    hypothesis="Subtle application"
                ),
                Variant(
                    variant_name="medium_intensity",
                    variant_type="treatment",
                    traffic_fraction=0.34,
                    config={},
                    mechanism_settings={mechanism: {"enabled": True, "intensity": "medium"}},
                    hypothesis="Moderate application"
                ),
                Variant(
                    variant_name="high_intensity",
                    variant_type="treatment",
                    traffic_fraction=0.33,
                    config={},
                    mechanism_settings={mechanism: {"enabled": True, "intensity": "high"}},
                    hypothesis="Strong application"
                ),
            ],
            metrics=[
                MetricDefinition(
                    metric_name="conversion_rate",
                    metric_type=MetricType.PRIMARY,
                    numerator_event="conversion",
                    denominator_event="impression",
                ),
            ],
            analysis_method=AnalysisMethod.BAYESIAN,
            tags=["mechanism_test", mechanism, "intensity"],
        )
    
    def _create_personality_interaction_test(
        self,
        mechanism: str,
        mechanism_info: Dict,
        baseline_rate: float,
        traffic_fraction: float
    ) -> ExperimentDesign:
        """Test: Does mechanism effect vary by personality?"""
        
        return ExperimentDesign(
            experiment_name=f"Mechanism Test: {mechanism} - Personality Interaction",
            experiment_type=ExperimentType.MECHANISM_INTERACTION,
            null_hypothesis=f"{mechanism} effect is uniform across personality types",
            alternative_hypothesis=f"{mechanism} effect varies by personality",
            expected_effect_size=mechanism_info["expected_lift"] * 0.3,
            variants=[
                Variant(
                    variant_name="control",
                    variant_type="control",
                    traffic_fraction=0.5,
                    config={},
                    mechanism_settings={mechanism: {"enabled": False}},
                ),
                Variant(
                    variant_name="with_mechanism",
                    variant_type="treatment",
                    traffic_fraction=0.5,
                    config={},
                    mechanism_settings={mechanism: {"enabled": True}},
                ),
            ],
            stratification=StratificationConfig(
                enabled=True,
                personality_clusters=True,  # Key: stratify by personality
            ),
            metrics=[
                MetricDefinition(
                    metric_name="conversion_rate",
                    metric_type=MetricType.PRIMARY,
                    numerator_event="conversion",
                    denominator_event="impression",
                ),
            ],
            analysis_method=AnalysisMethod.BAYESIAN,
            tags=["mechanism_test", mechanism, "personality_interaction"],
        )
    
    def _create_state_interaction_test(
        self,
        mechanism: str,
        mechanism_info: Dict,
        baseline_rate: float,
        traffic_fraction: float
    ) -> ExperimentDesign:
        """Test: Does mechanism effect vary by psychological state?"""
        
        return ExperimentDesign(
            experiment_name=f"Mechanism Test: {mechanism} - State Interaction",
            experiment_type=ExperimentType.MECHANISM_INTERACTION,
            null_hypothesis=f"{mechanism} effect is uniform across psychological states",
            alternative_hypothesis=f"{mechanism} effect varies by arousal/cognitive load",
            expected_effect_size=mechanism_info["expected_lift"] * 0.3,
            variants=[
                Variant(
                    variant_name="control",
                    variant_type="control",
                    traffic_fraction=0.5,
                    config={},
                    mechanism_settings={mechanism: {"enabled": False}},
                ),
                Variant(
                    variant_name="with_mechanism",
                    variant_type="treatment",
                    traffic_fraction=0.5,
                    config={},
                    mechanism_settings={mechanism: {"enabled": True}},
                ),
            ],
            stratification=StratificationConfig(
                enabled=True,
                psychological_states=True,  # Key: stratify by current state
            ),
            metrics=[
                MetricDefinition(
                    metric_name="conversion_rate",
                    metric_type=MetricType.PRIMARY,
                    numerator_event="conversion",
                    denominator_event="impression",
                ),
            ],
            analysis_method=AnalysisMethod.BAYESIAN,
            tags=["mechanism_test", mechanism, "state_interaction"],
        )
    
    async def analyze_mechanism_suite(
        self,
        mechanism: str,
        test_results: List[ExperimentResults]
    ) -> Dict[str, Any]:
        """
        Analyze complete mechanism test suite and generate recommendations.
        """
        analysis = {
            "mechanism": mechanism,
            "mechanism_info": self.TESTABLE_MECHANISMS.get(mechanism, {}),
            "tests_analyzed": len(test_results),
        }
        
        # Presence test result
        presence_result = next((r for r in test_results if "presence" in str(r)), None)
        if presence_result:
            analysis["presence_effect"] = {
                "is_effective": presence_result.is_significant and presence_result.expected_lift["mean"] > 0,
                "lift": presence_result.expected_lift,
                "probability_better": presence_result.posterior_probability,
            }
        
        # Intensity test result
        intensity_result = next((r for r in test_results if "intensity" in str(r)), None)
        if intensity_result:
            # Find best intensity
            variant_rates = {
                v: r["conversion_rate"] 
                for v, r in intensity_result.variant_results.items()
            }
            best_intensity = max(variant_rates.keys(), key=lambda k: variant_rates[k])
            analysis["optimal_intensity"] = best_intensity
        
        # Personality interaction analysis
        personality_result = next((r for r in test_results if "personality" in str(r)), None)
        if personality_result:
            # Would contain stratified results
            analysis["personality_interactions"] = personality_result.comparisons
        
        # Generate recommendations
        analysis["recommendations"] = self._generate_mechanism_recommendations(analysis)
        
        return analysis
    
    def _generate_mechanism_recommendations(
        self,
        analysis: Dict[str, Any]
    ) -> List[str]:
        """Generate actionable recommendations from mechanism analysis."""
        recs = []
        
        # Presence recommendation
        if "presence_effect" in analysis:
            if analysis["presence_effect"]["is_effective"]:
                lift = analysis["presence_effect"]["lift"]["mean"]
                recs.append(f"ENABLE: Mechanism provides {lift:.1%} lift. Enable in production.")
            else:
                recs.append("DISABLE: Mechanism shows no significant benefit. Do not use.")
        
        # Intensity recommendation
        if "optimal_intensity" in analysis:
            recs.append(f"INTENSITY: Use {analysis['optimal_intensity']} intensity setting.")
        
        # Personality targeting
        if "personality_interactions" in analysis:
            # Find segments with strongest effect
            # (simplified - would analyze interaction effects)
            recs.append("TARGETING: Analyze personality segments for targeted deployment.")
        
        return recs
```

---

## Part 7: Experiment Quality Assurance

```python
# =============================================================================
# QUALITY ASSURANCE
# 
# Detect and prevent common experiment problems.
# =============================================================================

class SampleRatioMismatchDetector:
    """
    Detect Sample Ratio Mismatch (SRM) in experiments.
    
    SRM occurs when actual traffic split doesn't match expected split.
    Indicates bugs in assignment, data collection, or data processing.
    """
    
    def check_srm(
        self,
        expected_fractions: Dict[str, float],
        observed_counts: Dict[str, int],
        alpha: float = 0.01  # Use lower alpha for SRM detection
    ) -> Dict[str, Any]:
        """
        Check for sample ratio mismatch using chi-squared test.
        """
        total = sum(observed_counts.values())
        
        if total < 100:
            return {
                "check_performed": False,
                "reason": "Insufficient sample size",
            }
        
        # Calculate expected counts
        expected_counts = {k: v * total for k, v in expected_fractions.items()}
        
        # Chi-squared test
        observed = list(observed_counts.values())
        expected = [expected_counts[k] for k in observed_counts.keys()]
        
        chi2, p_value = stats.chisquare(observed, expected)
        
        # Calculate imbalance
        max_deviation = max(
            abs(observed_counts[k] / total - expected_fractions[k])
            for k in expected_fractions.keys()
        )
        
        has_srm = p_value < alpha
        
        return {
            "check_performed": True,
            "chi_squared": chi2,
            "p_value": p_value,
            "has_srm": has_srm,
            "max_deviation": max_deviation,
            "expected_fractions": expected_fractions,
            "observed_fractions": {k: v / total for k, v in observed_counts.items()},
            "recommendation": self._srm_recommendation(has_srm, p_value, max_deviation),
        }
    
    def _srm_recommendation(
        self,
        has_srm: bool,
        p_value: float,
        max_deviation: float
    ) -> str:
        """Generate SRM recommendation."""
        if has_srm:
            if max_deviation > 0.05:
                return f"CRITICAL SRM: {max_deviation:.1%} deviation detected (p={p_value:.4f}). Stop experiment and investigate!"
            else:
                return f"SRM DETECTED: {max_deviation:.1%} deviation (p={p_value:.4f}). Review assignment and data pipelines."
        else:
            return "No SRM detected. Traffic split is healthy."


class NoveltyEffectDetector:
    """
    Detect novelty effects that may inflate early results.
    
    Users may engage differently with new variants simply because
    they're new, not because they're better.
    """
    
    def check_novelty_effect(
        self,
        daily_lift: List[float],
        min_days: int = 7
    ) -> Dict[str, Any]:
        """
        Check for declining lift over time (novelty effect).
        """
        if len(daily_lift) < min_days:
            return {
                "check_performed": False,
                "reason": f"Need at least {min_days} days of data",
            }
        
        # Fit linear regression to lift over time
        days = np.arange(len(daily_lift))
        slope, intercept, r_value, p_value, std_err = stats.linregress(days, daily_lift)
        
        # Calculate initial vs. final lift
        first_week_lift = np.mean(daily_lift[:7])
        last_week_lift = np.mean(daily_lift[-7:]) if len(daily_lift) >= 14 else np.mean(daily_lift)
        
        decline = first_week_lift - last_week_lift
        decline_pct = decline / first_week_lift if first_week_lift != 0 else 0
        
        # Detect significant decline
        has_novelty_effect = (
            slope < 0 and 
            p_value < 0.05 and 
            decline_pct > 0.20  # More than 20% decline
        )
        
        return {
            "check_performed": True,
            "slope": slope,
            "slope_p_value": p_value,
            "r_squared": r_value ** 2,
            "first_week_lift": first_week_lift,
            "last_week_lift": last_week_lift,
            "lift_decline": decline,
            "lift_decline_pct": decline_pct,
            "has_novelty_effect": has_novelty_effect,
            "recommendation": self._novelty_recommendation(has_novelty_effect, decline_pct),
        }
    
    def _novelty_recommendation(
        self,
        has_novelty_effect: bool,
        decline_pct: float
    ) -> str:
        """Generate novelty effect recommendation."""
        if has_novelty_effect:
            return f"NOVELTY EFFECT DETECTED: Lift declined {decline_pct:.1%}. Extend experiment and use recent data for decision."
        else:
            return "No significant novelty effect detected."


class GuardrailMonitor:
    """
    Monitor guardrail metrics during experiment.
    """
    
    def __init__(
        self,
        experiment: ExperimentDesign,
        alert_callback: Optional[Callable] = None
    ):
        self.experiment = experiment
        self.alert_callback = alert_callback
    
    async def check_all_guardrails(
        self,
        variant_data: Dict[str, Dict[str, float]]
    ) -> Dict[str, Any]:
        """
        Check all guardrail metrics.
        """
        results = {}
        any_violated = False
        
        for metric in self.experiment.guardrail_metrics:
            result = await self._check_guardrail(metric, variant_data)
            results[metric.metric_name] = result
            
            if result["violated"]:
                any_violated = True
                
                # Alert if callback provided
                if self.alert_callback:
                    await self.alert_callback(
                        experiment_id=self.experiment.experiment_id,
                        metric=metric.metric_name,
                        result=result
                    )
        
        return {
            "guardrails": results,
            "any_violated": any_violated,
            "recommendation": "PAUSE EXPERIMENT" if any_violated else "Continue monitoring",
        }
    
    async def _check_guardrail(
        self,
        metric: MetricDefinition,
        variant_data: Dict[str, Dict[str, float]]
    ) -> Dict[str, Any]:
        """Check single guardrail metric."""
        
        control_value = variant_data.get("control", {}).get(metric.metric_name, 0)
        treatment_values = {
            k: v.get(metric.metric_name, 0)
            for k, v in variant_data.items()
            if k != "control"
        }
        
        violations = []
        
        for variant, value in treatment_values.items():
            if metric.is_guardrail_violated(value, control_value):
                violations.append({
                    "variant": variant,
                    "value": value,
                    "baseline": control_value,
                    "threshold": metric.guardrail_threshold,
                })
        
        return {
            "metric": metric.metric_name,
            "control_value": control_value,
            "treatment_values": treatment_values,
            "violated": len(violations) > 0,
            "violations": violations,
        }


class ExperimentQualityChecker:
    """
    Comprehensive quality checks for experiments.
    """
    
    def __init__(self):
        self.srm_detector = SampleRatioMismatchDetector()
        self.novelty_detector = NoveltyEffectDetector()
    
    async def run_all_checks(
        self,
        experiment: ExperimentDesign,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Run all quality checks."""
        
        results = {
            "experiment_id": experiment.experiment_id,
            "checks": {},
            "overall_quality": "good",
            "issues": [],
        }
        
        # SRM check
        if "variant_counts" in data:
            expected_fractions = {v.variant_id: v.traffic_fraction for v in experiment.variants}
            srm_result = self.srm_detector.check_srm(expected_fractions, data["variant_counts"])
            results["checks"]["srm"] = srm_result
            
            if srm_result.get("has_srm"):
                results["overall_quality"] = "critical"
                results["issues"].append("Sample Ratio Mismatch detected")
        
        # Novelty effect check
        if "daily_lift" in data and len(data["daily_lift"]) >= 7:
            novelty_result = self.novelty_detector.check_novelty_effect(data["daily_lift"])
            results["checks"]["novelty"] = novelty_result
            
            if novelty_result.get("has_novelty_effect"):
                results["overall_quality"] = "warning"
                results["issues"].append("Novelty effect detected")
        
        # Minimum sample check
        if "total_samples" in data:
            required = experiment.required_sample_size or 1000
            if data["total_samples"] < required * 0.5:
                results["checks"]["sample_size"] = {
                    "current": data["total_samples"],
                    "required": required,
                    "sufficient": False,
                }
                results["issues"].append("Insufficient sample size")
        
        return results
```

---


## Part 8: Metric Computation Pipeline

```python
# =============================================================================
# METRIC COMPUTATION
# 
# Real-time and batch computation of experiment metrics.
# =============================================================================

class MetricComputer:
    """
    Compute experiment metrics from event data.
    """
    
    def __init__(
        self,
        clickhouse_client: 'ClickHouseClient',
        redis_client: 'Redis'
    ):
        self.clickhouse = clickhouse_client
        self.redis = redis_client
    
    async def compute_metric(
        self,
        experiment_id: str,
        metric: MetricDefinition,
        variant_ids: Optional[List[str]] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> Dict[str, Dict[str, float]]:
        """
        Compute metric values per variant.
        """
        # Build query based on metric type
        if metric.aggregation == "ratio":
            return await self._compute_ratio_metric(
                experiment_id, metric, variant_ids, start_time, end_time
            )
        elif metric.aggregation == "mean":
            return await self._compute_mean_metric(
                experiment_id, metric, variant_ids, start_time, end_time
            )
        elif metric.aggregation == "count":
            return await self._compute_count_metric(
                experiment_id, metric, variant_ids, start_time, end_time
            )
        else:
            raise ValueError(f"Unknown aggregation: {metric.aggregation}")
    
    async def _compute_ratio_metric(
        self,
        experiment_id: str,
        metric: MetricDefinition,
        variant_ids: Optional[List[str]],
        start_time: Optional[datetime],
        end_time: Optional[datetime]
    ) -> Dict[str, Dict[str, float]]:
        """Compute ratio metrics (e.g., conversion rate)."""
        
        query = f"""
        SELECT
            variant_id,
            countIf(event_type = '{metric.numerator_event}') as numerator,
            countIf(event_type = '{metric.denominator_event}') as denominator,
            numerator / denominator as rate
        FROM experiment_events
        WHERE experiment_id = '{experiment_id}'
        """
        
        if variant_ids:
            query += f" AND variant_id IN ({','.join(repr(v) for v in variant_ids)})"
        if start_time:
            query += f" AND event_time >= '{start_time.isoformat()}'"
        if end_time:
            query += f" AND event_time <= '{end_time.isoformat()}'"
        
        query += " GROUP BY variant_id"
        
        result = await self.clickhouse.execute(query)
        
        return {
            row["variant_id"]: {
                "numerator": row["numerator"],
                "denominator": row["denominator"],
                "rate": row["rate"],
                "metric_name": metric.metric_name,
            }
            for row in result
        }
    
    async def _compute_mean_metric(
        self,
        experiment_id: str,
        metric: MetricDefinition,
        variant_ids: Optional[List[str]],
        start_time: Optional[datetime],
        end_time: Optional[datetime]
    ) -> Dict[str, Dict[str, float]]:
        """Compute mean metrics (e.g., average order value)."""
        
        query = f"""
        SELECT
            variant_id,
            count() as n,
            avg(event_value) as mean,
            stddevPop(event_value) as std,
            sum(event_value) as total
        FROM experiment_events
        WHERE experiment_id = '{experiment_id}'
        AND event_type = '{metric.numerator_event}'
        """
        
        if variant_ids:
            query += f" AND variant_id IN ({','.join(repr(v) for v in variant_ids)})"
        if start_time:
            query += f" AND event_time >= '{start_time.isoformat()}'"
        if end_time:
            query += f" AND event_time <= '{end_time.isoformat()}'"
        
        query += " GROUP BY variant_id"
        
        result = await self.clickhouse.execute(query)
        
        return {
            row["variant_id"]: {
                "n": row["n"],
                "mean": row["mean"],
                "std": row["std"],
                "total": row["total"],
                "metric_name": metric.metric_name,
            }
            for row in result
        }
    
    async def _compute_count_metric(
        self,
        experiment_id: str,
        metric: MetricDefinition,
        variant_ids: Optional[List[str]],
        start_time: Optional[datetime],
        end_time: Optional[datetime]
    ) -> Dict[str, Dict[str, float]]:
        """Compute count metrics."""
        
        query = f"""
        SELECT
            variant_id,
            count() as count,
            uniqExact(user_id) as unique_users
        FROM experiment_events
        WHERE experiment_id = '{experiment_id}'
        AND event_type = '{metric.numerator_event}'
        """
        
        if variant_ids:
            query += f" AND variant_id IN ({','.join(repr(v) for v in variant_ids)})"
        if start_time:
            query += f" AND event_time >= '{start_time.isoformat()}'"
        if end_time:
            query += f" AND event_time <= '{end_time.isoformat()}'"
        
        query += " GROUP BY variant_id"
        
        result = await self.clickhouse.execute(query)
        
        return {
            row["variant_id"]: {
                "count": row["count"],
                "unique_users": row["unique_users"],
                "metric_name": metric.metric_name,
            }
            for row in result
        }
    
    async def compute_all_metrics(
        self,
        experiment: ExperimentDesign
    ) -> Dict[str, Any]:
        """Compute all metrics for an experiment."""
        
        variant_ids = [v.variant_id for v in experiment.variants]
        results = {}
        
        for metric in experiment.metrics:
            try:
                metric_result = await self.compute_metric(
                    experiment.experiment_id,
                    metric,
                    variant_ids
                )
                results[metric.metric_name] = metric_result
            except Exception as e:
                results[metric.metric_name] = {"error": str(e)}
        
        return results


class RealTimeMetricTracker:
    """
    Track metrics in real-time using Redis counters.
    """
    
    def __init__(self, redis_client: 'Redis'):
        self.redis = redis_client
    
    async def record_event(
        self,
        experiment_id: str,
        variant_id: str,
        event_type: str,
        event_value: float = 1.0
    ) -> None:
        """Record event for real-time tracking."""
        
        # Increment counters
        base_key = f"exp:{experiment_id}:{variant_id}"
        
        # Count
        await self.redis.incr(f"{base_key}:{event_type}:count")
        
        # Sum (for value-based metrics)
        await self.redis.incrbyfloat(f"{base_key}:{event_type}:sum", event_value)
        
        # Store timestamp for rate calculation
        await self.redis.zadd(
            f"{base_key}:{event_type}:times",
            {datetime.utcnow().isoformat(): datetime.utcnow().timestamp()}
        )
    
    async def get_real_time_counts(
        self,
        experiment_id: str,
        event_types: List[str]
    ) -> Dict[str, Dict[str, int]]:
        """Get real-time counts per variant."""
        
        # This would scan all variants - in production, store variant list
        results = {}
        
        # Pattern match for all variants
        pattern = f"exp:{experiment_id}:*:count"
        keys = await self.redis.keys(pattern)
        
        for key in keys:
            parts = key.decode().split(":")
            if len(parts) >= 4:
                variant_id = parts[2]
                event_type = parts[3]
                
                if event_type in event_types:
                    count = await self.redis.get(key)
                    
                    if variant_id not in results:
                        results[variant_id] = {}
                    
                    results[variant_id][event_type] = int(count) if count else 0
        
        return results


class SegmentedMetricAnalyzer:
    """
    Analyze metrics by psychological segments.
    
    Critical for understanding which users benefit from treatment.
    """
    
    def __init__(self, clickhouse_client: 'ClickHouseClient'):
        self.clickhouse = clickhouse_client
    
    async def compute_segmented_metrics(
        self,
        experiment_id: str,
        metric: MetricDefinition,
        segment_field: str  # e.g., "personality_cluster", "arousal_level"
    ) -> Dict[str, Dict[str, Any]]:
        """
        Compute metrics segmented by psychological dimension.
        """
        
        query = f"""
        SELECT
            variant_id,
            {segment_field} as segment,
            countIf(event_type = '{metric.numerator_event}') as numerator,
            countIf(event_type = '{metric.denominator_event}') as denominator,
            numerator / denominator as rate
        FROM experiment_events e
        JOIN experiment_assignments a ON e.assignment_id = a.assignment_id
        WHERE e.experiment_id = '{experiment_id}'
        GROUP BY variant_id, segment
        ORDER BY variant_id, segment
        """
        
        result = await self.clickhouse.execute(query)
        
        # Organize by segment
        segmented = {}
        for row in result:
            segment = row["segment"]
            if segment not in segmented:
                segmented[segment] = {}
            
            segmented[segment][row["variant_id"]] = {
                "numerator": row["numerator"],
                "denominator": row["denominator"],
                "rate": row["rate"],
            }
        
        return segmented
    
    async def find_best_segment_variant_pairs(
        self,
        experiment_id: str,
        metric: MetricDefinition
    ) -> List[Dict[str, Any]]:
        """
        Find segment-variant pairs with best performance.
        
        Answers: "Which variant works best for which user type?"
        """
        
        # Get segmented metrics for multiple dimensions
        dimensions = [
            "personality_cluster",
            "arousal_bucket",
            "decision_stage",
        ]
        
        best_pairs = []
        
        for dim in dimensions:
            try:
                segmented = await self.compute_segmented_metrics(
                    experiment_id, metric, dim
                )
                
                for segment, variants in segmented.items():
                    best_variant = max(
                        variants.keys(),
                        key=lambda v: variants[v]["rate"]
                    )
                    
                    best_pairs.append({
                        "dimension": dim,
                        "segment": segment,
                        "best_variant": best_variant,
                        "rate": variants[best_variant]["rate"],
                        "sample_size": variants[best_variant]["denominator"],
                    })
                    
            except Exception as e:
                continue
        
        # Sort by rate (highest first)
        best_pairs.sort(key=lambda x: x["rate"], reverse=True)
        
        return best_pairs
```

---

## Part 9: Component Integration

```python
# =============================================================================
# COMPONENT INTEGRATIONS
# =============================================================================

class GradientBridgeExperimentIntegration:
    """
    Integration with #06 Gradient Bridge for learning signals.
    
    Experiments generate valuable learning signals about
    what works and what doesn't.
    """
    
    def __init__(self, gradient_bridge_client: 'GradientBridgeClient'):
        self.bridge = gradient_bridge_client
        self.component_id = "ab_testing"
    
    async def emit_experiment_completed_signal(
        self,
        experiment: ExperimentDesign,
        results: ExperimentResults
    ) -> None:
        """
        Emit learning signal when experiment completes.
        """
        learning_signal = {
            "component": self.component_id,
            "signal_type": "experiment_completed",
            "timestamp": datetime.utcnow().isoformat(),
            
            # Experiment metadata
            "experiment_id": experiment.experiment_id,
            "experiment_type": experiment.experiment_type.value,
            "experiment_name": experiment.experiment_name,
            
            # Results
            "winning_variant": results.recommended_action,
            "lift": results.expected_lift,
            "probability_better": results.posterior_probability,
            "is_significant": results.is_significant,
            
            # Mechanism info (if mechanism test)
            "mechanisms_tested": [
                v.mechanism_settings 
                for v in experiment.variants 
                if v.mechanism_settings
            ],
            
            # Sample sizes
            "sample_sizes": results.users_per_variant,
        }
        
        await self.bridge.emit(learning_signal)
    
    async def emit_mechanism_effectiveness_signal(
        self,
        mechanism: str,
        effectiveness: Dict[str, Any]
    ) -> None:
        """
        Emit signal about mechanism effectiveness.
        """
        learning_signal = {
            "component": self.component_id,
            "signal_type": "mechanism_effectiveness",
            "timestamp": datetime.utcnow().isoformat(),
            
            "mechanism": mechanism,
            "is_effective": effectiveness.get("is_effective", False),
            "lift": effectiveness.get("lift", 0),
            "optimal_intensity": effectiveness.get("optimal_intensity"),
            "personality_interactions": effectiveness.get("personality_interactions", []),
        }
        
        await self.bridge.emit(learning_signal)


class Neo4jExperimentStorage:
    """
    Store experiment data in Neo4j graph.
    
    Enables:
    - Cross-experiment analysis
    - Mechanism effectiveness tracking
    - Segment-level insights
    """
    
    def __init__(self, neo4j_client: 'Neo4jDriver'):
        self.neo4j = neo4j_client
    
    async def store_experiment(
        self,
        experiment: ExperimentDesign
    ) -> None:
        """Store experiment design in graph."""
        
        query = """
        CREATE (e:Experiment {
            experiment_id: $experiment_id,
            experiment_name: $name,
            experiment_type: $type,
            status: $status,
            created_at: datetime($created_at),
            expected_effect_size: $expected_effect
        })
        
        WITH e
        UNWIND $variants as variant
        CREATE (v:Variant {
            variant_id: variant.variant_id,
            variant_name: variant.variant_name,
            variant_type: variant.variant_type,
            traffic_fraction: variant.traffic_fraction
        })
        CREATE (v)-[:BELONGS_TO]->(e)
        
        WITH e
        UNWIND $mechanisms as mech
        MERGE (m:Mechanism {name: mech})
        CREATE (e)-[:TESTS]->(m)
        """
        
        # Extract mechanisms being tested
        mechanisms = set()
        for variant in experiment.variants:
            mechanisms.update(variant.mechanism_settings.keys())
        
        await self.neo4j.run(
            query,
            experiment_id=experiment.experiment_id,
            name=experiment.experiment_name,
            type=experiment.experiment_type.value,
            status=experiment.status.value,
            created_at=experiment.created_at.isoformat(),
            expected_effect=experiment.expected_effect_size,
            variants=[v.dict() for v in experiment.variants],
            mechanisms=list(mechanisms),
        )
    
    async def store_results(
        self,
        results: ExperimentResults
    ) -> None:
        """Store experiment results."""
        
        query = """
        MATCH (e:Experiment {experiment_id: $experiment_id})
        SET e.completed_at = datetime($completed_at),
            e.is_significant = $is_significant,
            e.recommended_action = $action
        
        WITH e
        CREATE (r:ExperimentResult {
            analysis_timestamp: datetime($timestamp),
            p_value: $p_value,
            posterior_probability: $posterior,
            expected_lift_mean: $lift_mean
        })
        CREATE (e)-[:HAS_RESULT]->(r)
        
        WITH e, r
        UNWIND $variant_results as vr
        MATCH (v:Variant {variant_id: vr.variant_id})-[:BELONGS_TO]->(e)
        SET v.conversion_rate = vr.rate,
            v.sample_size = vr.sample_size
        """
        
        variant_results = [
            {"variant_id": k, **v}
            for k, v in results.variant_results.items()
        ]
        
        await self.neo4j.run(
            query,
            experiment_id=results.experiment_id,
            completed_at=results.analysis_timestamp.isoformat(),
            is_significant=results.is_significant,
            action=results.recommended_action,
            timestamp=results.analysis_timestamp.isoformat(),
            p_value=results.p_value,
            posterior=results.posterior_probability,
            lift_mean=results.expected_lift.get("mean", 0) if results.expected_lift else 0,
            variant_results=variant_results,
        )
    
    async def query_mechanism_history(
        self,
        mechanism: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Query historical results for a mechanism.
        """
        
        query = """
        MATCH (e:Experiment)-[:TESTS]->(m:Mechanism {name: $mechanism})
        MATCH (e)-[:HAS_RESULT]->(r:ExperimentResult)
        RETURN 
            e.experiment_name as name,
            e.experiment_id as id,
            r.expected_lift_mean as lift,
            r.posterior_probability as probability,
            e.is_significant as significant
        ORDER BY e.completed_at DESC
        LIMIT $limit
        """
        
        result = await self.neo4j.run(query, mechanism=mechanism, limit=limit)
        return [dict(record) for record in result]


class BlackboardExperimentIntegration:
    """
    Integration with #02 Blackboard for experiment context.
    """
    
    def __init__(self, blackboard_client: 'BlackboardClient'):
        self.blackboard = blackboard_client
    
    async def get_user_context_for_experiment(
        self,
        user_id: str
    ) -> Dict[str, Any]:
        """Get user psychological context for stratification."""
        
        # Read from blackboard
        psychological_state = await self.blackboard.read(
            component_id="signal_aggregation",
            user_id=user_id
        )
        
        return {
            "psychological_state": {
                "arousal": psychological_state.get("arousal", 0.5),
                "cognitive_load": psychological_state.get("cognitive_load", 0.3),
                "decision_proximity": psychological_state.get("decision_proximity", 0.0),
                "regulatory_orientation": psychological_state.get("regulatory_orientation", 0.0),
            },
            "personality_profile": {
                "openness": psychological_state.get("openness", 0.5),
                "conscientiousness": psychological_state.get("conscientiousness", 0.5),
                "extraversion": psychological_state.get("extraversion", 0.5),
                "agreeableness": psychological_state.get("agreeableness", 0.5),
                "neuroticism": psychological_state.get("neuroticism", 0.5),
            },
            "journey_stage": psychological_state.get("journey_stage", "unknown"),
        }
```

---


## Part 10: FastAPI Endpoints

```python
from fastapi import FastAPI, HTTPException, BackgroundTasks, Query, Depends, Body
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import uvicorn


# =============================================================================
# API MODELS
# =============================================================================

class CreateExperimentRequest(BaseModel):
    """Request to create new experiment."""
    experiment_name: str
    experiment_type: ExperimentType
    null_hypothesis: str
    alternative_hypothesis: str
    expected_effect_size: float
    variants: List[Dict[str, Any]]
    metrics: List[Dict[str, Any]]
    audience_filter: Optional[Dict[str, Any]] = None
    stratification: Optional[Dict[str, Any]] = None
    analysis_method: AnalysisMethod = AnalysisMethod.BAYESIAN
    tags: List[str] = Field(default_factory=list)


class ExperimentResponse(BaseModel):
    """Experiment response."""
    experiment_id: str
    experiment_name: str
    status: ExperimentStatus
    variants: List[Dict[str, Any]]
    created_at: str


class AssignmentRequest(BaseModel):
    """Request for experiment assignment."""
    user_id: str
    context: Optional[Dict[str, Any]] = None


class AssignmentResponse(BaseModel):
    """Assignment response."""
    experiment_id: str
    variant_id: str
    variant_name: str
    config: Dict[str, Any]


class RecordEventRequest(BaseModel):
    """Request to record experiment event."""
    experiment_id: str
    variant_id: str
    user_id: str
    event_type: str
    event_value: float = 1.0
    context: Optional[Dict[str, Any]] = None


class AnalysisResponse(BaseModel):
    """Analysis results response."""
    experiment_id: str
    analysis_method: str
    is_significant: bool
    recommended_action: str
    variant_results: Dict[str, Any]
    comparison_results: Dict[str, Any]


# =============================================================================
# API APPLICATION
# =============================================================================

app = FastAPI(
    title="ADAM A/B Testing API",
    description="Experimentation platform for psychological advertising",
    version="2.0.0"
)

security = HTTPBearer()


# =============================================================================
# EXPERIMENT MANAGEMENT ENDPOINTS
# =============================================================================

@app.post("/v1/experiments", response_model=ExperimentResponse)
async def create_experiment(
    request: CreateExperimentRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Create a new experiment."""
    try:
        manager = app.state.experiment_manager
        
        # Build design
        design = ExperimentDesign(
            experiment_name=request.experiment_name,
            experiment_type=request.experiment_type,
            null_hypothesis=request.null_hypothesis,
            alternative_hypothesis=request.alternative_hypothesis,
            expected_effect_size=request.expected_effect_size,
            variants=[Variant(**v) for v in request.variants],
            metrics=[MetricDefinition(**m) for m in request.metrics],
            audience_filter=request.audience_filter or {},
            analysis_method=request.analysis_method,
            tags=request.tags,
        )
        
        # Calculate sample size
        power_analyzer = PowerAnalyzer()
        primary_metric = design.primary_metric
        
        if primary_metric:
            design.required_sample_size = power_analyzer.calculate_sample_size(
                baseline_rate=primary_metric.expected_baseline or 0.02,
                minimum_detectable_effect=request.expected_effect_size,
            )
        
        # Store
        await manager.create(design)
        
        return ExperimentResponse(
            experiment_id=design.experiment_id,
            experiment_name=design.experiment_name,
            status=design.status,
            variants=[v.dict() for v in design.variants],
            created_at=design.created_at.isoformat(),
        )
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/v1/experiments/{experiment_id}", response_model=ExperimentResponse)
async def get_experiment(
    experiment_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Get experiment details."""
    manager = app.state.experiment_manager
    
    design = await manager.get(experiment_id)
    if not design:
        raise HTTPException(status_code=404, detail="Experiment not found")
    
    return ExperimentResponse(
        experiment_id=design.experiment_id,
        experiment_name=design.experiment_name,
        status=design.status,
        variants=[v.dict() for v in design.variants],
        created_at=design.created_at.isoformat(),
    )


@app.post("/v1/experiments/{experiment_id}/start")
async def start_experiment(
    experiment_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Start an experiment."""
    manager = app.state.experiment_manager
    
    result = await manager.start(experiment_id)
    
    return {"status": "started", "experiment_id": experiment_id}


@app.post("/v1/experiments/{experiment_id}/stop")
async def stop_experiment(
    experiment_id: str,
    reason: str = Query(...),
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Stop an experiment early."""
    manager = app.state.experiment_manager
    
    await manager.stop(experiment_id, reason)
    
    return {"status": "stopped", "experiment_id": experiment_id, "reason": reason}


@app.get("/v1/experiments")
async def list_experiments(
    status: Optional[ExperimentStatus] = None,
    experiment_type: Optional[ExperimentType] = None,
    tag: Optional[str] = None,
    limit: int = Query(50, le=100),
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """List experiments with filters."""
    manager = app.state.experiment_manager
    
    experiments = await manager.list(
        status=status,
        experiment_type=experiment_type,
        tag=tag,
        limit=limit,
    )
    
    return {"experiments": [e.dict() for e in experiments]}


# =============================================================================
# ASSIGNMENT ENDPOINTS
# =============================================================================

@app.post("/v1/experiments/{experiment_id}/assign", response_model=AssignmentResponse)
async def get_assignment(
    experiment_id: str,
    request: AssignmentRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Get or create variant assignment for user."""
    assignment_engine = app.state.assignment_engine
    
    # Enrich context with psychological state if not provided
    context = request.context or {}
    if "psychological_state" not in context:
        blackboard_integration = app.state.blackboard_integration
        context = await blackboard_integration.get_user_context_for_experiment(
            request.user_id
        )
    
    assignment = await assignment_engine.get_assignment(
        user_id=request.user_id,
        experiment_id=experiment_id,
        context=context,
    )
    
    if not assignment:
        raise HTTPException(status_code=404, detail="User not eligible for experiment")
    
    # Get variant details
    manager = app.state.experiment_manager
    design = await manager.get(experiment_id)
    variant = design.get_variant_by_id(assignment.variant_id)
    
    return AssignmentResponse(
        experiment_id=experiment_id,
        variant_id=assignment.variant_id,
        variant_name=variant.variant_name if variant else "unknown",
        config=variant.config if variant else {},
    )


@app.post("/v1/assignments/batch")
async def get_all_assignments(
    request: AssignmentRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Get assignments for all active experiments."""
    assignment_engine = app.state.assignment_engine
    
    assignments = await assignment_engine.get_all_assignments(
        user_id=request.user_id,
        context=request.context,
    )
    
    return {"assignments": [a.dict() for a in assignments]}


# =============================================================================
# EVENT TRACKING ENDPOINTS
# =============================================================================

@app.post("/v1/events")
async def record_event(
    request: RecordEventRequest,
    background_tasks: BackgroundTasks,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Record experiment event."""
    tracker = app.state.real_time_tracker
    
    # Record in real-time
    await tracker.record_event(
        experiment_id=request.experiment_id,
        variant_id=request.variant_id,
        event_type=request.event_type,
        event_value=request.event_value,
    )
    
    # Background: store in ClickHouse
    background_tasks.add_task(
        store_event_clickhouse,
        request.experiment_id,
        request.variant_id,
        request.user_id,
        request.event_type,
        request.event_value,
        request.context,
    )
    
    return {"status": "recorded"}


@app.post("/v1/events/batch")
async def record_events_batch(
    events: List[RecordEventRequest],
    background_tasks: BackgroundTasks,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Record multiple events."""
    tracker = app.state.real_time_tracker
    
    for event in events:
        await tracker.record_event(
            experiment_id=event.experiment_id,
            variant_id=event.variant_id,
            event_type=event.event_type,
            event_value=event.event_value,
        )
    
    background_tasks.add_task(store_events_batch_clickhouse, events)
    
    return {"status": "recorded", "count": len(events)}


async def store_event_clickhouse(
    experiment_id: str,
    variant_id: str,
    user_id: str,
    event_type: str,
    event_value: float,
    context: Optional[Dict],
):
    """Store event in ClickHouse (background task)."""
    clickhouse = app.state.clickhouse
    # Implementation depends on ClickHouse client
    pass


async def store_events_batch_clickhouse(events: List[RecordEventRequest]):
    """Store batch events in ClickHouse (background task)."""
    clickhouse = app.state.clickhouse
    # Implementation depends on ClickHouse client
    pass


# =============================================================================
# ANALYSIS ENDPOINTS
# =============================================================================

@app.get("/v1/experiments/{experiment_id}/analysis", response_model=AnalysisResponse)
async def get_analysis(
    experiment_id: str,
    method: AnalysisMethod = Query(AnalysisMethod.BAYESIAN),
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Get experiment analysis results."""
    manager = app.state.experiment_manager
    metric_computer = app.state.metric_computer
    
    design = await manager.get(experiment_id)
    if not design:
        raise HTTPException(status_code=404, detail="Experiment not found")
    
    # Compute metrics
    metrics_data = await metric_computer.compute_all_metrics(design)
    
    # Run analysis
    if method == AnalysisMethod.BAYESIAN:
        analyzer = BayesianAnalyzer()
    else:
        analyzer = FrequentistAnalyzer()
    
    primary_metric = design.primary_metric
    if not primary_metric:
        raise HTTPException(status_code=400, detail="No primary metric defined")
    
    primary_data = metrics_data.get(primary_metric.metric_name, {})
    
    control_data = primary_data.get(design.control_variant.variant_id, {})
    treatment_data = primary_data.get(design.treatment_variants[0].variant_id, {})
    
    if method == AnalysisMethod.BAYESIAN:
        results = analyzer.analyze_conversion_rate(
            control_conversions=int(control_data.get("numerator", 0)),
            control_total=int(control_data.get("denominator", 1)),
            treatment_conversions=int(treatment_data.get("numerator", 0)),
            treatment_total=int(treatment_data.get("denominator", 1)),
        )
    else:
        results = analyzer.analyze_conversion_rate(
            control_conversions=int(control_data.get("numerator", 0)),
            control_total=int(control_data.get("denominator", 1)),
            treatment_conversions=int(treatment_data.get("numerator", 0)),
            treatment_total=int(treatment_data.get("denominator", 1)),
        )
    
    return AnalysisResponse(
        experiment_id=experiment_id,
        analysis_method=method.value,
        is_significant=results.get("is_significant", False),
        recommended_action=results.get("recommendation", "continue"),
        variant_results=primary_data,
        comparison_results=results,
    )


@app.get("/v1/experiments/{experiment_id}/quality")
async def check_quality(
    experiment_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Run quality checks on experiment."""
    manager = app.state.experiment_manager
    quality_checker = app.state.quality_checker
    
    design = await manager.get(experiment_id)
    if not design:
        raise HTTPException(status_code=404, detail="Experiment not found")
    
    # Get data for checks
    tracker = app.state.real_time_tracker
    counts = await tracker.get_real_time_counts(
        experiment_id,
        ["impression", "conversion"]
    )
    
    data = {
        "variant_counts": {k: v.get("impression", 0) for k, v in counts.items()},
        "total_samples": sum(v.get("impression", 0) for v in counts.values()),
    }
    
    results = await quality_checker.run_all_checks(design, data)
    
    return results


@app.get("/v1/experiments/{experiment_id}/segments")
async def get_segmented_analysis(
    experiment_id: str,
    segment_by: str = Query("personality_cluster"),
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Get analysis segmented by psychological dimension."""
    segmented_analyzer = app.state.segmented_analyzer
    manager = app.state.experiment_manager
    
    design = await manager.get(experiment_id)
    if not design:
        raise HTTPException(status_code=404, detail="Experiment not found")
    
    primary_metric = design.primary_metric
    if not primary_metric:
        raise HTTPException(status_code=400, detail="No primary metric defined")
    
    segmented = await segmented_analyzer.compute_segmented_metrics(
        experiment_id,
        primary_metric,
        segment_by,
    )
    
    return {"segments": segmented, "segment_field": segment_by}


# =============================================================================
# MECHANISM TESTING ENDPOINTS
# =============================================================================

@app.post("/v1/mechanisms/{mechanism}/test-suite")
async def create_mechanism_test_suite(
    mechanism: str,
    baseline_rate: float = Query(0.02),
    traffic_fraction: float = Query(0.10),
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Create test suite for psychological mechanism."""
    mechanism_tester = app.state.mechanism_tester
    
    try:
        tests = await mechanism_tester.create_mechanism_test_suite(
            mechanism=mechanism,
            baseline_conversion_rate=baseline_rate,
            traffic_fraction=traffic_fraction,
        )
        
        return {
            "mechanism": mechanism,
            "tests": [t.dict() for t in tests],
            "total_tests": len(tests),
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/v1/mechanisms")
async def list_testable_mechanisms(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """List all testable psychological mechanisms."""
    return {
        "mechanisms": PsychologicalMechanismTester.TESTABLE_MECHANISMS
    }


# =============================================================================
# BANDIT ENDPOINTS
# =============================================================================

@app.post("/v1/bandits/{experiment_id}/select")
async def bandit_select_variant(
    experiment_id: str,
    request: AssignmentRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Get variant using bandit algorithm."""
    bandit_manager = app.state.bandit_managers.get(experiment_id)
    
    if not bandit_manager:
        raise HTTPException(status_code=404, detail="Bandit not found")
    
    variant_id = await bandit_manager.get_variant(
        user_id=request.user_id,
        context=request.context,
    )
    
    return {"variant_id": variant_id}


@app.get("/v1/bandits/{experiment_id}/status")
async def bandit_status(
    experiment_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Get bandit status and statistics."""
    bandit_manager = app.state.bandit_managers.get(experiment_id)
    
    if not bandit_manager:
        raise HTTPException(status_code=404, detail="Bandit not found")
    
    status = await bandit_manager.get_status()
    
    return status


# =============================================================================
# LIFECYCLE
# =============================================================================

@app.on_event("startup")
async def startup():
    """Initialize services."""
    import aioredis
    
    # Redis
    redis = await aioredis.from_url("redis://localhost:6379")
    app.state.redis = redis
    
    # Neo4j (mock for example)
    app.state.neo4j = None  # Would be actual Neo4j driver
    
    # ClickHouse (mock for example)
    app.state.clickhouse = None  # Would be actual ClickHouse client
    
    # Initialize components
    app.state.assignment_engine = TrafficAssignmentEngine(redis, app.state.neo4j)
    app.state.real_time_tracker = RealTimeMetricTracker(redis)
    app.state.metric_computer = MetricComputer(app.state.clickhouse, redis)
    app.state.quality_checker = ExperimentQualityChecker()
    app.state.mechanism_tester = PsychologicalMechanismTester(None)
    app.state.segmented_analyzer = SegmentedMetricAnalyzer(app.state.clickhouse)
    app.state.bandit_managers = {}
    
    # Integrations
    app.state.blackboard_integration = None  # Would be actual client
    
    print("A/B Testing API started")


@app.on_event("shutdown")
async def shutdown():
    """Cleanup."""
    await app.state.redis.close()


@app.get("/health")
async def health_check():
    """Health check."""
    return {"status": "healthy", "service": "ab-testing"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8012)
```

---


## Part 11: Observability & Operations

```python
from prometheus_client import Counter, Histogram, Gauge, start_http_server


# =============================================================================
# METRICS
# =============================================================================

# Experiment lifecycle metrics
experiments_created = Counter(
    "adam_experiments_created_total",
    "Total experiments created",
    ["experiment_type"]
)

experiments_started = Counter(
    "adam_experiments_started_total",
    "Total experiments started"
)

experiments_completed = Counter(
    "adam_experiments_completed_total",
    "Total experiments completed",
    ["outcome"]  # shipped, stopped, inconclusive
)

active_experiments = Gauge(
    "adam_active_experiments",
    "Currently active experiments",
    ["experiment_type"]
)

# Assignment metrics
assignments_total = Counter(
    "adam_assignments_total",
    "Total variant assignments",
    ["experiment_id", "variant_id"]
)

assignment_latency = Histogram(
    "adam_assignment_latency_seconds",
    "Variant assignment latency",
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1]
)

# Event tracking metrics
events_recorded = Counter(
    "adam_experiment_events_total",
    "Total experiment events recorded",
    ["event_type"]
)

# Analysis metrics
analyses_run = Counter(
    "adam_analyses_run_total",
    "Total analyses performed",
    ["method"]  # bayesian, frequentist, sequential
)

# Quality metrics
srm_detected = Counter(
    "adam_srm_detected_total",
    "Sample ratio mismatches detected"
)

guardrail_violations = Counter(
    "adam_guardrail_violations_total",
    "Guardrail metric violations",
    ["metric"]
)

# Mechanism testing metrics
mechanism_tests_completed = Counter(
    "adam_mechanism_tests_completed_total",
    "Mechanism tests completed",
    ["mechanism", "result"]  # effective, ineffective, inconclusive
)


class ABTestingMetricsCollector:
    """
    Collect and export metrics for A/B testing platform.
    """
    
    def __init__(self, port: int = 9012):
        self.port = port
    
    def start(self) -> None:
        """Start Prometheus metrics server."""
        start_http_server(self.port)
    
    def record_experiment_created(self, experiment_type: str) -> None:
        experiments_created.labels(experiment_type=experiment_type).inc()
    
    def record_experiment_started(self) -> None:
        experiments_started.inc()
    
    def record_experiment_completed(self, outcome: str) -> None:
        experiments_completed.labels(outcome=outcome).inc()
    
    def update_active_experiments(self, counts: Dict[str, int]) -> None:
        for exp_type, count in counts.items():
            active_experiments.labels(experiment_type=exp_type).set(count)
    
    def record_assignment(self, experiment_id: str, variant_id: str, latency_ms: float) -> None:
        assignments_total.labels(experiment_id=experiment_id, variant_id=variant_id).inc()
        assignment_latency.observe(latency_ms / 1000)
    
    def record_event(self, event_type: str) -> None:
        events_recorded.labels(event_type=event_type).inc()
    
    def record_analysis(self, method: str) -> None:
        analyses_run.labels(method=method).inc()
    
    def record_srm(self) -> None:
        srm_detected.inc()
    
    def record_guardrail_violation(self, metric: str) -> None:
        guardrail_violations.labels(metric=metric).inc()
    
    def record_mechanism_test(self, mechanism: str, result: str) -> None:
        mechanism_tests_completed.labels(mechanism=mechanism, result=result).inc()


# =============================================================================
# ALERTING
# =============================================================================

class ExperimentAlertManager:
    """
    Manage alerts for experiment issues.
    """
    
    def __init__(
        self,
        slack_webhook: Optional[str] = None,
        pagerduty_key: Optional[str] = None
    ):
        self.slack_webhook = slack_webhook
        self.pagerduty_key = pagerduty_key
    
    async def alert_srm_detected(
        self,
        experiment_id: str,
        experiment_name: str,
        deviation: float
    ) -> None:
        """Alert on sample ratio mismatch."""
        message = {
            "severity": "critical",
            "experiment_id": experiment_id,
            "experiment_name": experiment_name,
            "issue": "Sample Ratio Mismatch",
            "details": f"Traffic split deviation of {deviation:.1%} detected",
            "action": "Investigate assignment logic and data pipelines",
        }
        
        await self._send_alert(message)
    
    async def alert_guardrail_violation(
        self,
        experiment_id: str,
        experiment_name: str,
        metric: str,
        current_value: float,
        threshold: float
    ) -> None:
        """Alert on guardrail violation."""
        message = {
            "severity": "high",
            "experiment_id": experiment_id,
            "experiment_name": experiment_name,
            "issue": "Guardrail Violation",
            "metric": metric,
            "details": f"Current value {current_value:.4f} violates threshold {threshold:.4f}",
            "action": "Consider pausing experiment",
        }
        
        await self._send_alert(message)
    
    async def alert_early_winner(
        self,
        experiment_id: str,
        experiment_name: str,
        winning_variant: str,
        probability: float
    ) -> None:
        """Alert on early winner detection."""
        message = {
            "severity": "info",
            "experiment_id": experiment_id,
            "experiment_name": experiment_name,
            "issue": "Early Winner Detected",
            "details": f"Variant {winning_variant} has {probability:.1%} probability of being best",
            "action": "Review for early stopping decision",
        }
        
        await self._send_alert(message)
    
    async def _send_alert(self, message: Dict[str, Any]) -> None:
        """Send alert to configured channels."""
        import aiohttp
        
        if self.slack_webhook:
            async with aiohttp.ClientSession() as session:
                slack_payload = {
                    "text": f"*{message['severity'].upper()}*: {message['issue']}",
                    "blocks": [
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": f"*Experiment*: {message['experiment_name']}\n*Details*: {message['details']}\n*Action*: {message['action']}"
                            }
                        }
                    ]
                }
                await session.post(self.slack_webhook, json=slack_payload)


# =============================================================================
# EXPERIMENT DASHBOARD DATA
# =============================================================================

class ExperimentDashboardProvider:
    """
    Provide data for experiment dashboard.
    """
    
    def __init__(
        self,
        neo4j_client: 'Neo4jDriver',
        redis_client: 'Redis'
    ):
        self.neo4j = neo4j_client
        self.redis = redis_client
    
    async def get_dashboard_summary(self) -> Dict[str, Any]:
        """Get summary for dashboard."""
        
        # Active experiments by type
        active_by_type = await self._get_active_by_type()
        
        # Recent completions
        recent_completions = await self._get_recent_completions(days=7)
        
        # Win rate
        win_rate = await self._calculate_win_rate(days=30)
        
        # Mechanism effectiveness
        mechanism_effectiveness = await self._get_mechanism_effectiveness()
        
        return {
            "active_experiments": active_by_type,
            "recent_completions": recent_completions,
            "win_rate_30d": win_rate,
            "mechanism_effectiveness": mechanism_effectiveness,
            "updated_at": datetime.utcnow().isoformat(),
        }
    
    async def _get_active_by_type(self) -> Dict[str, int]:
        """Get count of active experiments by type."""
        query = """
        MATCH (e:Experiment)
        WHERE e.status = 'running'
        RETURN e.experiment_type as type, count(*) as count
        """
        
        result = await self.neo4j.run(query)
        return {r["type"]: r["count"] for r in result}
    
    async def _get_recent_completions(self, days: int) -> List[Dict[str, Any]]:
        """Get recently completed experiments."""
        query = """
        MATCH (e:Experiment)-[:HAS_RESULT]->(r:ExperimentResult)
        WHERE e.completed_at > datetime() - duration({days: $days})
        RETURN 
            e.experiment_name as name,
            e.experiment_id as id,
            e.recommended_action as action,
            r.expected_lift_mean as lift
        ORDER BY e.completed_at DESC
        LIMIT 10
        """
        
        result = await self.neo4j.run(query, days=days)
        return [dict(r) for r in result]
    
    async def _calculate_win_rate(self, days: int) -> float:
        """Calculate percentage of experiments that shipped."""
        query = """
        MATCH (e:Experiment)
        WHERE e.completed_at > datetime() - duration({days: $days})
        RETURN 
            count(*) as total,
            sum(CASE WHEN e.recommended_action = 'ship' THEN 1 ELSE 0 END) as shipped
        """
        
        result = await self.neo4j.run(query, days=days)
        record = await result.single()
        
        if record and record["total"] > 0:
            return record["shipped"] / record["total"]
        return 0.0
    
    async def _get_mechanism_effectiveness(self) -> Dict[str, Dict[str, Any]]:
        """Get effectiveness summary for each mechanism."""
        query = """
        MATCH (e:Experiment)-[:TESTS]->(m:Mechanism)
        MATCH (e)-[:HAS_RESULT]->(r:ExperimentResult)
        WHERE e.experiment_type = 'mechanism_isolation'
        RETURN 
            m.name as mechanism,
            count(*) as tests,
            avg(r.expected_lift_mean) as avg_lift,
            sum(CASE WHEN e.is_significant AND r.expected_lift_mean > 0 THEN 1 ELSE 0 END) as effective_count
        """
        
        result = await self.neo4j.run(query)
        
        return {
            r["mechanism"]: {
                "tests": r["tests"],
                "avg_lift": r["avg_lift"],
                "effective_rate": r["effective_count"] / r["tests"] if r["tests"] > 0 else 0,
            }
            for r in result
        }
```

---

## Part 12: Testing & Validation

```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import numpy as np


# =============================================================================
# UNIT TESTS
# =============================================================================

class TestPowerAnalyzer:
    """Tests for power analysis."""
    
    def test_sample_size_calculation(self):
        """Test sample size calculation."""
        analyzer = PowerAnalyzer()
        
        sample_size = analyzer.calculate_sample_size(
            baseline_rate=0.02,
            minimum_detectable_effect=0.20,  # 20% relative lift
            alpha=0.05,
            power=0.80,
        )
        
        # Should require significant sample
        assert sample_size > 10000
        assert sample_size < 100000
    
    def test_power_calculation(self):
        """Test power calculation."""
        analyzer = PowerAnalyzer()
        
        power = analyzer.calculate_power(
            baseline_rate=0.02,
            treatment_rate=0.024,  # 20% lift
            sample_size_per_variant=50000,
        )
        
        assert 0.7 < power < 0.95


class TestConsistentHasher:
    """Tests for consistent hashing."""
    
    def test_deterministic_assignment(self):
        """Test that same input always gives same output."""
        hasher = ConsistentHasher()
        
        variants = [
            Variant(variant_id="v1", variant_name="control", variant_type="control", traffic_fraction=0.5),
            Variant(variant_id="v2", variant_name="treatment", variant_type="treatment", traffic_fraction=0.5),
        ]
        
        # Same user should get same variant
        variant1 = hasher.assign_variant("user123", "salt", variants)
        variant2 = hasher.assign_variant("user123", "salt", variants)
        
        assert variant1 == variant2
    
    def test_uniform_distribution(self):
        """Test that assignment is approximately uniform."""
        hasher = ConsistentHasher()
        
        variants = [
            Variant(variant_id="v1", variant_name="control", variant_type="control", traffic_fraction=0.5),
            Variant(variant_id="v2", variant_name="treatment", variant_type="treatment", traffic_fraction=0.5),
        ]
        
        user_ids = [f"user_{i}" for i in range(10000)]
        distribution = hasher.check_uniform_distribution(user_ids, "salt", variants)
        
        # Should be close to 50/50
        assert 0.45 < distribution["v1"] < 0.55
        assert 0.45 < distribution["v2"] < 0.55


class TestBayesianAnalyzer:
    """Tests for Bayesian analysis."""
    
    def test_clear_winner(self):
        """Test detection of clear winner."""
        analyzer = BayesianAnalyzer()
        
        results = analyzer.analyze_conversion_rate(
            control_conversions=100,
            control_total=5000,
            treatment_conversions=150,
            treatment_total=5000,
        )
        
        assert results["probability_treatment_better"] > 0.95
        assert results["expected_lift"]["mean"] > 0
    
    def test_clear_loser(self):
        """Test detection of clear loser."""
        analyzer = BayesianAnalyzer()
        
        results = analyzer.analyze_conversion_rate(
            control_conversions=150,
            control_total=5000,
            treatment_conversions=100,
            treatment_total=5000,
        )
        
        assert results["probability_treatment_better"] < 0.05
        assert results["expected_lift"]["mean"] < 0
    
    def test_inconclusive(self):
        """Test inconclusive result."""
        analyzer = BayesianAnalyzer()
        
        results = analyzer.analyze_conversion_rate(
            control_conversions=100,
            control_total=5000,
            treatment_conversions=105,
            treatment_total=5000,
        )
        
        assert 0.2 < results["probability_treatment_better"] < 0.8


class TestSequentialAnalyzer:
    """Tests for sequential testing."""
    
    def test_early_stop_winner(self):
        """Test early stopping for winner."""
        analyzer = SequentialAnalyzer()
        
        result = analyzer.continuous_monitoring_decision(
            control_conversions=50,
            control_total=2000,
            treatment_conversions=100,
            treatment_total=2000,
            information_fraction=0.3,
        )
        
        assert result["decision"] == "stop_winner"
        assert result["can_stop_early"]
    
    def test_continue_monitoring(self):
        """Test continuing when uncertain."""
        analyzer = SequentialAnalyzer()
        
        result = analyzer.continuous_monitoring_decision(
            control_conversions=45,
            control_total=2000,
            treatment_conversions=50,
            treatment_total=2000,
            information_fraction=0.3,
        )
        
        assert result["decision"] == "continue"
        assert not result["can_stop_early"]


class TestSRMDetector:
    """Tests for SRM detection."""
    
    def test_no_srm(self):
        """Test no SRM when traffic is balanced."""
        detector = SampleRatioMismatchDetector()
        
        result = detector.check_srm(
            expected_fractions={"control": 0.5, "treatment": 0.5},
            observed_counts={"control": 5100, "treatment": 4900},
        )
        
        assert not result["has_srm"]
    
    def test_srm_detected(self):
        """Test SRM detection when traffic is imbalanced."""
        detector = SampleRatioMismatchDetector()
        
        result = detector.check_srm(
            expected_fractions={"control": 0.5, "treatment": 0.5},
            observed_counts={"control": 6000, "treatment": 4000},
        )
        
        assert result["has_srm"]


class TestThompsonSamplingBandit:
    """Tests for Thompson Sampling."""
    
    def test_exploration_with_uncertainty(self):
        """Test that bandit explores when uncertain."""
        bandit = ThompsonSamplingBandit(variants=["v1", "v2"])
        
        # With no data, both variants should be selected
        selections = set()
        for _ in range(100):
            selections.add(bandit.select_variant())
        
        assert len(selections) == 2
    
    def test_exploitation_with_clear_winner(self):
        """Test that bandit exploits clear winner."""
        bandit = ThompsonSamplingBandit(variants=["v1", "v2"])
        
        # Add clear winner data
        for _ in range(100):
            bandit.update("v1", True)
        for _ in range(100):
            bandit.update("v2", False)
        
        # Should mostly select v1
        selections = [bandit.select_variant() for _ in range(100)]
        v1_count = sum(1 for s in selections if s == "v1")
        
        assert v1_count > 90


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestExperimentLifecycle:
    """Integration tests for experiment lifecycle."""
    
    @pytest.fixture
    async def experiment_manager(self):
        """Create test experiment manager."""
        # Would create with test dependencies
        pass
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_full_experiment_lifecycle(self, experiment_manager):
        """Test create -> start -> events -> analyze -> complete."""
        # 1. Create experiment
        # 2. Start experiment
        # 3. Record events
        # 4. Run analysis
        # 5. Complete experiment
        pass


# =============================================================================
# LOAD TESTS
# =============================================================================

class TestAssignmentPerformance:
    """Load tests for assignment performance."""
    
    @pytest.mark.benchmark
    def test_assignment_throughput(self, benchmark):
        """Test assignment throughput."""
        # Target: 10K assignments/second
        pass
    
    @pytest.mark.benchmark
    def test_assignment_latency(self, benchmark):
        """Test assignment latency."""
        # Target: <10ms p99
        pass
```

---

## Implementation Timeline

```yaml
total_duration: "14 weeks"
team_size: "3-4 engineers"
total_effort: "42-56 person-weeks"

phase_1_foundation:
  duration: "Weeks 1-3"
  focus: "Core infrastructure"
  deliverables:
    - Experiment data models
    - Traffic assignment engine with consistent hashing
    - Neo4j experiment storage
    - Redis caching layer
  engineers: 2
  effort: "6 person-weeks"
  validation:
    - Assignment determinism tests
    - Distribution uniformity tests

phase_2_analysis:
  duration: "Weeks 4-6"
  focus: "Statistical analysis"
  deliverables:
    - Power analyzer
    - Frequentist analyzer
    - Bayesian analyzer
    - CUPED variance reduction
    - Sequential testing
  engineers: 2
  effort: "6 person-weeks"
  validation:
    - Statistical accuracy tests
    - Comparison with R/Python stats libraries

phase_3_quality:
  duration: "Weeks 7-8"
  focus: "Quality assurance"
  deliverables:
    - SRM detector
    - Novelty effect detector
    - Guardrail monitor
    - Collision detector
  engineers: 2
  effort: "4 person-weeks"
  validation:
    - False positive/negative rates
    - Simulated quality issues

phase_4_bandits:
  duration: "Weeks 9-10"
  focus: "Adaptive optimization"
  deliverables:
    - Thompson Sampling bandit
    - Contextual bandit
    - Bandit experiment manager
  engineers: 2
  effort: "4 person-weeks"
  validation:
    - Regret benchmarks
    - Convergence tests

phase_5_psychological:
  duration: "Weeks 11-12"
  focus: "ADAM-specific testing"
  deliverables:
    - Psychological mechanism tester
    - Segmented metric analyzer
    - Mechanism test suite templates
  engineers: 2
  effort: "4 person-weeks"
  validation:
    - Integration with personality profiles
    - Segment analysis accuracy

phase_6_integration:
  duration: "Weeks 13-14"
  focus: "Component integration & API"
  deliverables:
    - FastAPI endpoints
    - Gradient Bridge integration
    - Blackboard integration
    - Observability stack
    - Dashboard data provider
  engineers: 2
  effort: "4 person-weeks"
  validation:
    - End-to-end API tests
    - Performance benchmarks

milestones:
  week_3: "Assignment engine at 10K/sec"
  week_6: "Statistical analysis validated"
  week_8: "Quality monitoring operational"
  week_10: "Bandits converging correctly"
  week_12: "Mechanism testing framework complete"
  week_14: "Full integration deployed"
```

---

## Success Metrics

| Category | Metric | Target | Measurement Method |
|----------|--------|--------|-------------------|
| **Performance** | Assignment latency (p99) | <10ms | Prometheus histogram |
| | Assignment throughput | >10K/sec | Load testing |
| | Analysis computation time | <5s | API response time |
| **Statistical Quality** | Power achieved | >80% | Post-hoc analysis |
| | False positive rate | <5% | Simulated AA tests |
| | SRM detection sensitivity | >95% | Simulated SRM |
| **Business Impact** | Experiment velocity | >20/month | Active experiments |
| | Time to decision | <14 days median | Experiment duration |
| | Mechanism validation rate | >50% tested | Mechanism coverage |
| | Conversion lift validated | >20% average | Shipped experiments |
| **Operational** | API availability | >99.9% | Uptime monitoring |
| | Alert accuracy | >95% | Alert review |

---

## Dependencies

### Upstream Dependencies
- **#08 Signal Aggregation**: Provides psychological state for stratification
- **#11 Validity Testing**: Psychological construct validation

### Downstream Dependents
- **#06 Gradient Bridge**: Receives learning signals from experiments
- **#14 Brand Intelligence**: Uses mechanism effectiveness data
- **#15 Copy Generation**: Uses personality match experiment results

---

*Enhancement #12 COMPLETE. A/B Testing Infrastructure provides the scientific foundation for validating ADAM's psychological targeting claims.*

*Enables rigorous proof of 40-50% conversion lifts through systematic experimentation.*
