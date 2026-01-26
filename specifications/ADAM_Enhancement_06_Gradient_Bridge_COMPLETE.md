# ADAM Enhancement #06: Cross-Component Learning Signals
## Enterprise-Grade Gradient Bridge with Multi-Level Credit Attribution

**Version**: 2.0 COMPLETE  
**Date**: January 2026  
**Priority**: P0 - Critical (Central Learning Hub)  
**Estimated Implementation**: 10 person-weeks  
**Dependencies**: #01-#05 (Core Architecture), #31 (Event Bus & Cache)  
**Dependents**: ALL learning components (#03 Meta-Learner, #10 Journey, #13 Cold Start, #20 Monitoring)  
**File Size**: ~140KB (Enterprise Production-Ready)

---

## Table of Contents

### SECTION A: STRATEGIC OVERVIEW
1. [Executive Summary](#executive-summary)
2. [The Critical Gap](#the-critical-gap)
3. [Architecture Overview](#architecture-overview)
4. [Research Foundations](#research-foundations)

### SECTION B: PYDANTIC DATA MODELS
5. [Core Enums & Types](#core-enums-types)
6. [Credit Assignment Models](#credit-assignment-models)
7. [Signal Propagation Models](#signal-propagation-models)
8. [Feature Extraction Models](#feature-extraction-models)
9. [Empirical Prior Models](#empirical-prior-models)

### SECTION C: CREDIT ATTRIBUTION ENGINE
10. [Multi-Method Attribution](#multi-method-attribution)
11. [Atom-Level Credit Computation](#atom-level-credit-computation)
12. [LLM-Guided Attribution (QLLM)](#llm-guided-attribution)

### SECTION D: FEATURE EXTRACTION SYSTEM
13. [Enriched Bandit Context](#enriched-bandit-context)
14. [Feature Vectorization](#feature-vectorization)
15. [Prior Extraction Pipeline](#prior-extraction-pipeline)

### SECTION E: GRADIENT BRIDGE CORE
16. [Signal Orchestrator](#signal-orchestrator)
17. [Component Updaters](#component-updaters)
18. [Parallel Propagation Engine](#parallel-propagation-engine)

### SECTION F: EVENT BUS INTEGRATION (#31)
19. [Learning Signal Events](#learning-signal-events)
20. [Kafka Topic Mapping](#kafka-topic-mapping)
21. [Outcome Event Consumer](#outcome-event-consumer)

### SECTION G: CACHE INTEGRATION (#31)
22. [Attribution Cache Layer](#attribution-cache-layer)
23. [Prior Cache Management](#prior-cache-management)
24. [Cache Invalidation Triggers](#cache-invalidation-triggers)

### SECTION H: NEO4J SCHEMA
25. [Attribution Graph Schema](#attribution-graph-schema)
26. [Learning Analytics Queries](#learning-analytics-queries)

### SECTION I: LANGGRAPH WORKFLOWS
27. [Gradient Bridge Workflow Node](#gradient-bridge-workflow-node)
28. [Prior Injection Node](#prior-injection-node)

### SECTION J: FASTAPI ENDPOINTS
29. [Attribution API](#attribution-api)
30. [Learning Signal API](#learning-signal-api)

### SECTION K: PROMETHEUS METRICS
31. [Attribution Metrics](#attribution-metrics)
32. [Signal Propagation Metrics](#signal-propagation-metrics)
33. [Learning Quality Metrics](#learning-quality-metrics)

### SECTION L: TESTING & OPERATIONS
34. [Unit Tests](#unit-tests)
35. [Integration Tests](#integration-tests)
36. [Implementation Timeline](#implementation-timeline)
37. [Success Metrics](#success-metrics)

---

# SECTION A: STRATEGIC OVERVIEW

## Executive Summary

### The Gradient Bridge's Role

The Gradient Bridge is the **central nervous system** of ADAM's learning architecture. It ensures that **every outcome improves every component**—the bandit learns from Claude's psychological insights, Claude learns from the bandit's empirical history, and the graph database continuously validates and updates user profiles based on conversion outcomes.

```
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│                                                                                             │
│   WHY THE GRADIENT BRIDGE MATTERS                                                          │
│   ═══════════════════════════════                                                          │
│                                                                                             │
│   Without Gradient Bridge:                                                                  │
│   ────────────────────────                                                                  │
│   • Bandit only sees: (arm_id, reward) → learns slowly, no psychological context           │
│   • Claude only sees: current request → no empirical validation of past predictions        │
│   • Graph only stores: static profiles → doesn't learn what actually works                 │
│   • Meta-learner only learns: path success → no atom-level attribution                     │
│                                                                                             │
│   With Gradient Bridge:                                                                     │
│   ──────────────────────                                                                    │
│   • Bandit sees: 40+ psychological features → 3x faster convergence                        │
│   • Claude sees: empirical priors → predictions grounded in data                           │
│   • Graph learns: mechanism effectiveness per user → validated profiles                     │
│   • Meta-learner learns: per-atom credit → precision routing                               │
│                                                                                             │
│   THE MAGIC: Every component makes every other component smarter                           │
│                                                                                             │
└─────────────────────────────────────────────────────────────────────────────────────────────┘
```

### Key Capabilities

| Capability | Description | Business Impact |
|------------|-------------|-----------------|
| **Multi-Level Credit Attribution** | Attribute outcomes to atoms, bandit, graph, meta-learner | Know what's actually working |
| **Enriched Bandit Features** | 40+ psychological features from Claude atoms | 3x faster convergence |
| **Empirical Priors for Claude** | Historical performance injected into reasoning | Data-grounded predictions |
| **Graph Learning** | User-mechanism effectiveness tracking | Validated personality profiles |
| **Real-Time Signal Propagation** | <100ms signal distribution via Kafka | Instant cross-component learning |

### Expected Impact

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Bandit feature richness | 1 feature (reward) | 40+ features | 40x |
| Claude context utilization | 0% historical | 100% empirical priors | New capability |
| Credit attribution accuracy | 0% | >80% | New capability |
| Convergence speed | Baseline | 2-3x faster | Research-aligned |
| Cross-component learning | Siloed | Unified | Qualitative leap |

---

## The Critical Gap

### Before Enhancement #06 (Siloed Learning)

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                           BEFORE: SILOED COMPONENT LEARNING                             │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                         │
│   ┌───────────────┐     ┌───────────────┐     ┌───────────────┐     ┌───────────────┐  │
│   │   BANDIT      │     │   CLAUDE      │     │    GRAPH      │     │  META-        │  │
│   │               │     │   ATOMS       │     │  DATABASE     │     │  LEARNER      │  │
│   │  Learns       │     │  (No          │     │  (Static      │     │  (Learns      │  │
│   │  arm          │     │   learning)   │     │   storage)    │     │   routing)    │  │
│   │  rewards      │     │               │     │               │     │               │  │
│   └───────┬───────┘     └───────┬───────┘     └───────┬───────┘     └───────┬───────┘  │
│           │                     │                     │                     │          │
│           ▼                     ▼                     ▼                     ▼          │
│   ┌─────────────────────────────────────────────────────────────────────────────────┐  │
│   │                         CONVERSION OUTCOME                                      │  │
│   │                         (Only bandit learns, 1 feature: reward)                 │  │
│   └─────────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                         │
│   PROBLEMS:                                                                             │
│   • Bandit uses 1 feature (reward) → learns slowly                                     │
│   • Claude has no historical context → predictions unvalidated                         │
│   • Graph never updates from outcomes → stale profiles                                 │
│   • Meta-learner doesn't know which atoms worked → imprecise routing                   │
│   • No credit attribution → can't tell what drove success                              │
│                                                                                         │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

### After Enhancement #06 (Unified Learning)

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                        AFTER: UNIFIED CROSS-COMPONENT LEARNING                          │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                         │
│                              ┌─────────────────────────┐                                │
│                              │     OUTCOME EVENT       │                                │
│                              │  (Conversion/Click/Skip)│                                │
│                              └────────────┬────────────┘                                │
│                                           │                                             │
│                                           ▼                                             │
│                         ┌─────────────────────────────────┐                             │
│                         │        GRADIENT BRIDGE          │                             │
│                         │                                 │                             │
│                         │  1. Multi-Level Attribution     │                             │
│                         │  2. Feature Extraction          │                             │
│                         │  3. Signal Propagation          │                             │
│                         │  4. Cache Management            │                             │
│                         └───────────────┬─────────────────┘                             │
│                                         │                                               │
│         ┌───────────────┬───────────────┼───────────────┬───────────────┐               │
│         │               │               │               │               │               │
│         ▼               ▼               ▼               ▼               ▼               │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐       │
│  │   BANDIT    │ │   CLAUDE    │ │    GRAPH    │ │ META-LEARNER│ │VERIFICATION │       │
│  │   UPDATE    │ │   PRIORS    │ │   UPDATE    │ │   UPDATE    │ │ CALIBRATION │       │
│  │             │ │             │ │             │ │             │ │             │       │
│  │ +40 atom    │ │ +Arm history│ │ +Mechanism  │ │ +Path credit│ │ +Confidence │       │
│  │  features   │ │ +Success    │ │  success    │ │ +Complexity │ │  curve      │       │
│  │ +Mechanism  │ │  rates      │ │ +User trait │ │  mapping    │ │  update     │       │
│  │  signals    │ │ +Context fit│ │  validation │ │             │ │             │       │
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘       │
│                                                                                         │
│   KEY: ───▶ = Learning signal flow via Kafka (#31)                                     │
│                                                                                         │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Research Foundations

The Gradient Bridge's attribution methods are grounded in peer-reviewed research:

### Credit Attribution Research

| Method | Research | Application in ADAM |
|--------|----------|---------------------|
| **QLLM Credit Assignment** | "QLLM: Leveraging LLMs for Credit Assignment" (2024) | Use Claude to evaluate atom contributions |
| **Turn-Level Credit** | "Fine-Grained Advantage Estimation for Multi-Step RL" (2023) | Per-atom credit in MDP framework |
| **Shapley Values** | Shapley, L. S. (1953) "A Value for n-Person Games" | Marginal contribution estimation |
| **Hierarchical Attribution** | "Agent Lightning" (2024) | Multi-level credit decomposition |

### Cross-Component Learning Research

| Approach | Research | Application in ADAM |
|----------|----------|---------------------|
| **Two-Tower Cross-Features** | Google (2019) "YouTube Recommendations" | Bandit ↔ Claude feature sharing |
| **MLET** | "Multi-Task Learning with Experts" (2022) | Cross-category informative updates |
| **Contextual Bandits** | Li et al. (2010) "Contextual Bandit for News" | Enriched feature vectors |

### Psychological Validity Research

| Finding | Research | Application in ADAM |
|---------|----------|---------------------|
| **Personality-Matched Messaging** | Matz et al. (2017) PNAS | Validate mechanism effectiveness |
| **Regulatory Focus Outcomes** | Higgins (1997) | Track promotion/prevention success |
| **Construal Level Effects** | Trope & Liberman (2010) | Validate abstraction matching |

---

# SECTION B: PYDANTIC DATA MODELS

## Core Enums & Types

```python
# =============================================================================
# ADAM Enhancement #06: Core Enums and Types
# Location: adam/gradient_bridge/enums.py
# =============================================================================

"""
Type-safe enumerations for the Gradient Bridge system.

All enums use string values for JSON serialization compatibility.
"""

from __future__ import annotations
from enum import Enum


class ComponentType(str, Enum):
    """
    All ADAM components that can receive/produce learning signals.
    """
    # Atom components
    ATOM_USER_STATE = "atom_user_state"
    ATOM_REGULATORY_FOCUS = "atom_regulatory_focus"
    ATOM_CONSTRUAL_LEVEL = "atom_construal_level"
    ATOM_PERSONALITY = "atom_personality"
    ATOM_MECHANISM = "atom_mechanism"
    ATOM_MESSAGE_FRAMING = "atom_message_framing"
    ATOM_AD_SELECTION = "atom_ad_selection"
    
    # Core components
    BANDIT = "bandit"
    GRAPH = "graph"
    META_LEARNER = "meta_learner"
    VERIFICATION = "verification"
    BLACKBOARD = "blackboard"
    JOURNEY_TRACKER = "journey_tracker"
    COLD_START = "cold_start"
    
    # Self
    GRADIENT_BRIDGE = "gradient_bridge"


class SignalType(str, Enum):
    """
    Types of learning signals that flow through the Gradient Bridge.
    """
    # Outcome signals
    REWARD = "reward"
    ENGAGEMENT = "engagement"
    REVENUE = "revenue"
    
    # Attribution signals
    CREDIT = "credit"
    COUNTERFACTUAL = "counterfactual"
    
    # Update signals
    CONFIDENCE_UPDATE = "confidence"
    PRIOR_UPDATE = "prior"
    EMBEDDING_UPDATE = "embedding"
    PROFILE_UPDATE = "profile"
    
    # Learning signals
    MECHANISM_EFFECTIVENESS = "mechanism_effectiveness"
    PERSONALITY_VALIDATION = "personality_validation"
    STATE_TRANSITION = "state_transition"


class OutcomeType(str, Enum):
    """Types of outcomes we track."""
    CONVERSION = "conversion"
    CLICK = "click"
    ENGAGEMENT = "engagement"
    SKIP = "skip"
    BOUNCE = "bounce"


class AttributionMethod(str, Enum):
    """Methods for computing credit attribution."""
    CONFIDENCE_WEIGHTED = "confidence_weighted"
    LLM_GUIDED = "llm_guided"
    COUNTERFACTUAL = "counterfactual"
    SHAPLEY = "shapley"
    ENSEMBLE = "ensemble"


class ExecutionPath(str, Enum):
    """Execution paths in LangGraph workflow."""
    FAST = "fast"
    REASONING = "reasoning"
    EXPLORATION = "exploration"
```

---

## Credit Assignment Models

```python
# =============================================================================
# ADAM Enhancement #06: Credit Assignment Models
# Location: adam/gradient_bridge/models/credit.py
# =============================================================================

"""
Pydantic models for credit assignment in the Gradient Bridge.

These models capture the multi-level attribution of outcomes to components,
enabling cross-component learning and precise understanding of what drove
each decision's success or failure.
"""

from __future__ import annotations
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from uuid import uuid4
import math

from pydantic import BaseModel, Field, field_validator, model_validator


class CreditAssignment(BaseModel):
    """
    Credit assigned to a specific component for an outcome.
    
    Represents the attributed contribution of a single component
    to a specific decision outcome, with confidence and evidence.
    """
    component_type: ComponentType
    component_id: str
    credit_score: float = Field(ge=0.0, le=1.0, description="Normalized contribution score")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence in attribution")
    evidence: Dict[str, Any] = Field(default_factory=dict)
    
    # Optional counterfactual estimate
    counterfactual_estimate: Optional[float] = Field(
        default=None,
        description="Estimated outcome if this component was absent"
    )
    
    # Attribution method used
    attribution_method: AttributionMethod = AttributionMethod.CONFIDENCE_WEIGHTED
    
    @field_validator("credit_score", "confidence")
    @classmethod
    def validate_probability(cls, v: float) -> float:
        """Ensure values are valid probabilities."""
        if not 0.0 <= v <= 1.0:
            raise ValueError("Value must be between 0.0 and 1.0")
        return round(v, 4)


class AtomCreditAssignment(CreditAssignment):
    """
    Credit assignment specifically for Atom of Thought atoms.
    """
    atom_name: str
    atom_output: Dict[str, Any] = Field(default_factory=dict)
    atom_confidence: float = Field(ge=0.0, le=1.0)
    execution_order: int = Field(ge=0, description="Order in DAG execution")
    dependencies_met: bool = True
    
    # LLM-guided evaluation score (if computed)
    llm_evaluation_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    llm_evaluation_reasoning: Optional[str] = None


class AttributionResult(BaseModel):
    """
    Complete attribution result for an outcome.
    
    Contains per-component credits and aggregate metrics for a single
    decision outcome, providing full visibility into what drove success
    or failure.
    """
    # Identifiers
    attribution_id: str = Field(
        default_factory=lambda: f"attr_{uuid4().hex[:12]}"
    )
    request_id: str
    decision_id: str
    user_id: str
    
    # Outcome information
    outcome_type: OutcomeType
    outcome_value: float = Field(ge=0.0, description="Reward signal value")
    outcome_timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    
    # Per-component credits
    atom_credits: Dict[str, AtomCreditAssignment] = Field(default_factory=dict)
    bandit_credit: CreditAssignment
    graph_credit: CreditAssignment
    meta_learner_credit: CreditAssignment
    verification_credit: Optional[CreditAssignment] = None
    
    # Aggregate metrics
    total_attribution: float = Field(default=1.0, description="Should sum to ~1.0")
    attribution_entropy: float = Field(
        ge=0.0,
        description="How spread out is credit? Higher = more distributed"
    )
    dominant_contributor: str = Field(description="Component with highest credit")
    dominant_credit: float = Field(ge=0.0, le=1.0)
    
    # Method metadata
    attribution_methods_used: List[AttributionMethod] = Field(default_factory=list)
    computation_time_ms: float = Field(ge=0.0)
    
    # Trace ID for distributed tracing
    trace_id: Optional[str] = None
    
    @model_validator(mode="after")
    def compute_aggregates(self) -> "AttributionResult":
        """Compute aggregate metrics from component credits."""
        # Collect all credit scores
        all_credits = list(self.atom_credits.values()) + [
            self.bandit_credit,
            self.graph_credit,
            self.meta_learner_credit
        ]
        if self.verification_credit:
            all_credits.append(self.verification_credit)
        
        # Find dominant contributor
        max_credit = max(all_credits, key=lambda c: c.credit_score)
        self.dominant_contributor = f"{max_credit.component_type.value}:{max_credit.component_id}"
        self.dominant_credit = max_credit.credit_score
        
        # Compute entropy (measure of credit distribution)
        credit_values = [c.credit_score for c in all_credits if c.credit_score > 0]
        if credit_values:
            total = sum(credit_values)
            if total > 0:
                probs = [v / total for v in credit_values]
                self.attribution_entropy = -sum(p * math.log(p) for p in probs if p > 0)
        
        return self


class AttributionConfig(BaseModel):
    """Configuration for the attribution engine."""
    
    # Method weights for ensemble attribution
    method_weights: Dict[AttributionMethod, float] = Field(
        default={
            AttributionMethod.CONFIDENCE_WEIGHTED: 0.4,
            AttributionMethod.LLM_GUIDED: 0.3,
            AttributionMethod.COUNTERFACTUAL: 0.2,
            AttributionMethod.SHAPLEY: 0.1
        }
    )
    
    # LLM-guided attribution settings
    use_llm_attribution: bool = True
    llm_attribution_threshold: float = Field(
        default=0.5,
        description="Only use LLM attribution for outcomes with value >= threshold"
    )
    llm_model: str = "claude-sonnet-4-20250514"
    llm_max_tokens: int = 500
    
    # Counterfactual estimation
    counterfactual_baseline_conversion: float = 0.02
    counterfactual_baseline_ctr: float = 0.05
    
    # Caching
    cache_attribution_ttl_seconds: int = 300  # 5 minutes
    cache_priors_ttl_seconds: int = 3600  # 1 hour
    
    @field_validator("method_weights")
    @classmethod
    def validate_weights_sum(cls, v: Dict) -> Dict:
        """Ensure weights sum to approximately 1.0."""
        total = sum(v.values())
        if not 0.95 <= total <= 1.05:
            raise ValueError(f"Method weights should sum to ~1.0, got {total}")
        return v
```

---

## Signal Propagation Models

```python
# =============================================================================
# ADAM Enhancement #06: Signal Propagation Models
# Location: adam/gradient_bridge/models/signals.py
# =============================================================================

"""
Pydantic models for learning signal propagation.
"""

from __future__ import annotations
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


class LearningSignalEvent(BaseModel):
    """
    A learning signal to propagate between components.
    
    This is the primary message type for cross-component learning.
    Emitted by the Gradient Bridge and consumed by component-specific
    updaters via Kafka.
    """
    # Identifiers
    signal_id: str = Field(default_factory=lambda: f"sig_{uuid4().hex[:12]}")
    trace_id: Optional[str] = None
    attribution_id: Optional[str] = None
    
    # Routing
    source_component: ComponentType
    target_component: ComponentType
    signal_type: SignalType
    
    # Payload
    signal_data: Dict[str, Any] = Field(default_factory=dict)
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    
    # Timing
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expiry: Optional[datetime] = None
    
    # Priority for processing
    priority: int = Field(default=5, ge=1, le=10, description="1=highest, 10=lowest")
    
    class Config:
        use_enum_values = True
    
    def is_expired(self) -> bool:
        """Check if signal has expired."""
        if self.expiry is None:
            return False
        return datetime.now(timezone.utc) > self.expiry


class BanditUpdateSignal(LearningSignalEvent):
    """Signal to update bandit with enriched features."""
    signal_type: SignalType = SignalType.REWARD
    target_component: ComponentType = ComponentType.BANDIT
    
    arm_id: str
    reward: float = Field(ge=0.0, le=1.0)
    weighted_reward: float = Field(ge=0.0, le=1.0, description="reward * credit_weight")
    credit_weight: float = Field(ge=0.0, le=1.0)
    
    # Feature vector (40+ dimensions)
    feature_vector: List[float] = Field(default_factory=list)
    feature_names: List[str] = Field(default_factory=list)
    
    # Context
    user_segment: Optional[str] = None
    execution_path: Optional[ExecutionPath] = None


class GraphUpdateSignal(LearningSignalEvent):
    """Signal to update Neo4j graph with outcome information."""
    signal_type: SignalType = SignalType.PROFILE_UPDATE
    target_component: ComponentType = ComponentType.GRAPH
    
    decision_id: str
    user_id: str
    ad_id: str
    outcome: float = Field(ge=0.0, le=1.0)
    
    # Attribution
    dominant_contributor: str
    attribution_entropy: float = Field(ge=0.0)
    atom_credits: Dict[str, float] = Field(default_factory=dict)
    
    # Mechanism tracking
    primary_mechanism: Optional[str] = None
    mechanism_activation_strength: float = Field(ge=0.0, le=1.0, default=0.5)
    
    # Personality validation
    personality_trait_predicted: Optional[str] = None
    personality_trait_validated: bool = False


class MetaLearnerUpdateSignal(LearningSignalEvent):
    """Signal to update meta-learner Thompson Sampling posteriors."""
    signal_type: SignalType = SignalType.CREDIT
    target_component: ComponentType = ComponentType.META_LEARNER
    
    execution_path: ExecutionPath
    path_confidence: float = Field(ge=0.0, le=1.0)
    
    outcome: float = Field(ge=0.0, le=1.0)
    credit: float = Field(ge=0.0, le=1.0)
    weighted_outcome: float = Field(ge=0.0, le=1.0, description="outcome * credit")
    
    context_complexity: float = Field(ge=0.0, le=1.0, default=0.5)
    user_data_richness: float = Field(ge=0.0, le=1.0, default=0.5)
    is_cold_start: bool = False


class CalibrationUpdateSignal(LearningSignalEvent):
    """Signal to update confidence calibration curve."""
    signal_type: SignalType = SignalType.CONFIDENCE_UPDATE
    target_component: ComponentType = ComponentType.VERIFICATION
    
    predicted_confidence: float = Field(ge=0.0, le=1.0)
    actual_outcome: bool
    confidence_bin: int = Field(ge=0, le=10)
    source_atom: Optional[str] = None


class SignalBatch(BaseModel):
    """Batch of learning signals for efficient processing."""
    batch_id: str = Field(default_factory=lambda: f"batch_{uuid4().hex[:12]}")
    signals: List[LearningSignalEvent] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source_attribution_id: Optional[str] = None
    total_signals: int = 0
    
    @model_validator(mode="after")
    def count_signals(self) -> "SignalBatch":
        """Update signal count."""
        self.total_signals = len(self.signals)
        return self
```

---

## Feature Extraction Models

```python
# =============================================================================
# ADAM Enhancement #06: Feature Extraction Models
# Location: adam/gradient_bridge/models/features.py
# =============================================================================

"""
Pydantic models for enriched bandit context and feature extraction.
"""

from __future__ import annotations
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator, computed_field


class EnrichedBanditContext(BaseModel):
    """
    40+ dimensional feature vector for contextual bandits.
    
    Extracts psychological signals from Claude atoms to enrich
    bandit learning beyond simple reward signals.
    """
    # Identifiers
    request_id: str
    user_id: str
    
    # User State Features (3 dimensions)
    user_state_arousal: float = Field(ge=0.0, le=1.0, description="Current arousal level")
    user_state_cognitive_load: float = Field(ge=0.0, le=1.0, description="Current cognitive load")
    user_state_receptivity: float = Field(ge=0.0, le=1.0, description="Receptivity score")
    
    # Regulatory Focus Features (2 dimensions)
    regulatory_focus_promotion: float = Field(ge=0.0, le=1.0, description="Promotion focus strength")
    regulatory_focus_prevention: float = Field(ge=0.0, le=1.0, description="Prevention focus strength")
    
    # Construal Level Features (1 dimension)
    construal_level: float = Field(ge=0.0, le=1.0, description="Abstract (1.0) to Concrete (0.0)")
    
    # Personality Features (11 dimensions - Big Five + facets)
    personality_openness: float = Field(ge=0.0, le=1.0, default=0.5)
    personality_conscientiousness: float = Field(ge=0.0, le=1.0, default=0.5)
    personality_extraversion: float = Field(ge=0.0, le=1.0, default=0.5)
    personality_agreeableness: float = Field(ge=0.0, le=1.0, default=0.5)
    personality_neuroticism: float = Field(ge=0.0, le=1.0, default=0.5)
    personality_need_for_cognition: float = Field(ge=0.0, le=1.0, default=0.5)
    personality_impulsivity: float = Field(ge=0.0, le=1.0, default=0.5)
    personality_risk_tolerance: float = Field(ge=0.0, le=1.0, default=0.5)
    personality_social_influence_susceptibility: float = Field(ge=0.0, le=1.0, default=0.5)
    personality_temporal_discounting: float = Field(ge=0.0, le=1.0, default=0.5)
    personality_confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    
    # Mechanism Features (10 dimensions - one-hot or strength)
    mechanism_social_proof: float = Field(ge=0.0, le=1.0, default=0.0)
    mechanism_scarcity: float = Field(ge=0.0, le=1.0, default=0.0)
    mechanism_authority: float = Field(ge=0.0, le=1.0, default=0.0)
    mechanism_reciprocity: float = Field(ge=0.0, le=1.0, default=0.0)
    mechanism_commitment: float = Field(ge=0.0, le=1.0, default=0.0)
    mechanism_liking: float = Field(ge=0.0, le=1.0, default=0.0)
    mechanism_loss_aversion: float = Field(ge=0.0, le=1.0, default=0.0)
    mechanism_anchoring: float = Field(ge=0.0, le=1.0, default=0.0)
    mechanism_framing: float = Field(ge=0.0, le=1.0, default=0.0)
    mechanism_primary_strength: float = Field(ge=0.0, le=1.0, default=0.5)
    
    # Message Framing Features (6 dimensions)
    framing_emotional_appeal: float = Field(ge=0.0, le=1.0, default=0.5)
    framing_rational_appeal: float = Field(ge=0.0, le=1.0, default=0.5)
    framing_urgency: float = Field(ge=0.0, le=1.0, default=0.5)
    framing_personalization: float = Field(ge=0.0, le=1.0, default=0.5)
    framing_storytelling: float = Field(ge=0.0, le=1.0, default=0.5)
    framing_value_proposition: float = Field(ge=0.0, le=1.0, default=0.5)
    
    # Confidence Features (4 dimensions)
    confidence_user_state: float = Field(ge=0.0, le=1.0, default=0.5)
    confidence_regulatory: float = Field(ge=0.0, le=1.0, default=0.5)
    confidence_personality: float = Field(ge=0.0, le=1.0, default=0.5)
    confidence_mechanism: float = Field(ge=0.0, le=1.0, default=0.5)
    
    # Execution Features (4 dimensions)
    execution_path_fast: float = Field(ge=0.0, le=1.0, default=0.0)
    execution_path_reasoning: float = Field(ge=0.0, le=1.0, default=0.0)
    execution_path_exploration: float = Field(ge=0.0, le=1.0, default=0.0)
    execution_complexity: float = Field(ge=0.0, le=1.0, default=0.5)
    
    # Graph Context Features (2 dimensions)
    graph_user_profile_completeness: float = Field(ge=0.0, le=1.0, default=0.0)
    graph_historical_conversion_rate: float = Field(ge=0.0, le=1.0, default=0.0)
    
    # Metadata
    extraction_timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    atom_sources: Dict[str, bool] = Field(
        default_factory=dict,
        description="Which atoms contributed to features"
    )
    
    @computed_field
    @property
    def feature_dimension(self) -> int:
        """Total feature dimension count."""
        return 43  # Count of all feature fields above
    
    def to_feature_vector(self) -> List[float]:
        """Convert to flat feature vector for bandit consumption."""
        return [
            # User State (3)
            self.user_state_arousal,
            self.user_state_cognitive_load,
            self.user_state_receptivity,
            # Regulatory Focus (2)
            self.regulatory_focus_promotion,
            self.regulatory_focus_prevention,
            # Construal (1)
            self.construal_level,
            # Personality (11)
            self.personality_openness,
            self.personality_conscientiousness,
            self.personality_extraversion,
            self.personality_agreeableness,
            self.personality_neuroticism,
            self.personality_need_for_cognition,
            self.personality_impulsivity,
            self.personality_risk_tolerance,
            self.personality_social_influence_susceptibility,
            self.personality_temporal_discounting,
            self.personality_confidence,
            # Mechanism (10)
            self.mechanism_social_proof,
            self.mechanism_scarcity,
            self.mechanism_authority,
            self.mechanism_reciprocity,
            self.mechanism_commitment,
            self.mechanism_liking,
            self.mechanism_loss_aversion,
            self.mechanism_anchoring,
            self.mechanism_framing,
            self.mechanism_primary_strength,
            # Framing (6)
            self.framing_emotional_appeal,
            self.framing_rational_appeal,
            self.framing_urgency,
            self.framing_personalization,
            self.framing_storytelling,
            self.framing_value_proposition,
            # Confidence (4)
            self.confidence_user_state,
            self.confidence_regulatory,
            self.confidence_personality,
            self.confidence_mechanism,
            # Execution (4)
            self.execution_path_fast,
            self.execution_path_reasoning,
            self.execution_path_exploration,
            self.execution_complexity,
            # Graph (2)
            self.graph_user_profile_completeness,
            self.graph_historical_conversion_rate
        ]
    
    @staticmethod
    def feature_names() -> List[str]:
        """Get ordered list of feature names for interpretability."""
        return [
            "user_state_arousal", "user_state_cognitive_load", "user_state_receptivity",
            "regulatory_focus_promotion", "regulatory_focus_prevention",
            "construal_level",
            "personality_openness", "personality_conscientiousness", "personality_extraversion",
            "personality_agreeableness", "personality_neuroticism", "personality_need_for_cognition",
            "personality_impulsivity", "personality_risk_tolerance", 
            "personality_social_influence_susceptibility", "personality_temporal_discounting",
            "personality_confidence",
            "mechanism_social_proof", "mechanism_scarcity", "mechanism_authority",
            "mechanism_reciprocity", "mechanism_commitment", "mechanism_liking",
            "mechanism_loss_aversion", "mechanism_anchoring", "mechanism_framing",
            "mechanism_primary_strength",
            "framing_emotional_appeal", "framing_rational_appeal", "framing_urgency",
            "framing_personalization", "framing_storytelling", "framing_value_proposition",
            "confidence_user_state", "confidence_regulatory", "confidence_personality",
            "confidence_mechanism",
            "execution_path_fast", "execution_path_reasoning", "execution_path_exploration",
            "execution_complexity",
            "graph_user_profile_completeness", "graph_historical_conversion_rate"
        ]


class FeatureExtractionResult(BaseModel):
    """Result of feature extraction from atoms."""
    request_id: str
    enriched_context: EnrichedBanditContext
    extraction_time_ms: float = Field(ge=0.0)
    atoms_available: List[str] = Field(default_factory=list)
    atoms_missing: List[str] = Field(default_factory=list)
    feature_coverage: float = Field(
        ge=0.0, le=1.0,
        description="Fraction of features with valid data"
    )
```

---

## Empirical Prior Models

```python
# =============================================================================
# ADAM Enhancement #06: Empirical Prior Models
# Location: adam/gradient_bridge/models/priors.py
# =============================================================================

"""
Pydantic models for empirical priors injected into Claude's context.
"""

from __future__ import annotations
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from uuid import uuid4

from pydantic import BaseModel, Field, computed_field


class ArmPerformanceStats(BaseModel):
    """Performance statistics for a single bandit arm."""
    arm_id: str
    arm_name: str
    
    # Thompson Sampling posteriors
    alpha: float = Field(ge=0.0, description="Success count + 1")
    beta: float = Field(ge=0.0, description="Failure count + 1")
    
    # Derived metrics
    total_pulls: int = Field(ge=0, default=0)
    total_conversions: int = Field(ge=0, default=0)
    
    @computed_field
    @property
    def empirical_conversion_rate(self) -> float:
        """Calculate empirical conversion rate."""
        if self.total_pulls == 0:
            return 0.0
        return self.total_conversions / self.total_pulls
    
    @computed_field
    @property
    def expected_value(self) -> float:
        """Expected value from Thompson Sampling posterior."""
        return self.alpha / (self.alpha + self.beta)
    
    @computed_field
    @property
    def uncertainty(self) -> float:
        """Posterior uncertainty (inverse of evidence strength)."""
        total = self.alpha + self.beta
        if total <= 2:
            return 1.0
        return 1.0 / (total - 2)  # Approximate posterior variance


class SegmentStats(BaseModel):
    """Segment-specific performance statistics."""
    segment_id: str
    segment_name: str
    
    # Performance
    conversion_rate: float = Field(ge=0.0, le=1.0)
    click_through_rate: float = Field(ge=0.0, le=1.0)
    engagement_rate: float = Field(ge=0.0, le=1.0)
    
    # Sample size
    impressions: int = Field(ge=0)
    conversions: int = Field(ge=0)
    
    # Confidence
    statistical_confidence: float = Field(ge=0.0, le=1.0)


class MechanismSuccessRates(BaseModel):
    """Success rates per persuasion mechanism."""
    mechanism_name: str
    
    # Overall rates
    overall_conversion_rate: float = Field(ge=0.0, le=1.0)
    overall_sample_size: int = Field(ge=0)
    
    # Per-segment breakdown
    high_openness_rate: float = Field(ge=0.0, le=1.0, default=0.0)
    low_openness_rate: float = Field(ge=0.0, le=1.0, default=0.0)
    promotion_focus_rate: float = Field(ge=0.0, le=1.0, default=0.0)
    prevention_focus_rate: float = Field(ge=0.0, le=1.0, default=0.0)
    
    # Statistical significance
    is_significant: bool = False
    p_value: Optional[float] = Field(default=None, ge=0.0, le=1.0)


class UserHistory(BaseModel):
    """Historical interaction data for a specific user."""
    user_id: str
    
    # Interaction counts
    total_impressions: int = Field(ge=0, default=0)
    total_clicks: int = Field(ge=0, default=0)
    total_conversions: int = Field(ge=0, default=0)
    
    # Mechanism history
    successful_mechanisms: List[str] = Field(default_factory=list)
    failed_mechanisms: List[str] = Field(default_factory=list)
    
    # Temporal patterns
    best_day_of_week: Optional[int] = Field(default=None, ge=0, le=6)
    best_hour_of_day: Optional[int] = Field(default=None, ge=0, le=23)
    
    # Validated traits
    validated_personality_traits: Dict[str, float] = Field(default_factory=dict)
    
    @computed_field
    @property
    def historical_conversion_rate(self) -> float:
        """User's historical conversion rate."""
        if self.total_impressions == 0:
            return 0.0
        return self.total_conversions / self.total_impressions
    
    @computed_field
    @property
    def is_cold_start(self) -> bool:
        """Check if user is in cold start (< 5 interactions)."""
        return self.total_impressions < 5


class EmpiricalPriors(BaseModel):
    """
    Empirical priors to inject into Claude's context.
    
    This provides Claude with historical performance data to
    ground its psychological predictions in empirical evidence.
    """
    # Identifiers
    prior_id: str = Field(default_factory=lambda: f"prior_{uuid4().hex[:12]}")
    request_id: str
    user_id: str
    
    # Arm performance
    arm_stats: List[ArmPerformanceStats] = Field(default_factory=list)
    top_arm: Optional[str] = None
    top_arm_confidence: float = Field(ge=0.0, le=1.0, default=0.0)
    
    # Segment performance
    segment_stats: List[SegmentStats] = Field(default_factory=list)
    user_segment: Optional[str] = None
    
    # Mechanism effectiveness
    mechanism_stats: List[MechanismSuccessRates] = Field(default_factory=list)
    recommended_mechanisms: List[str] = Field(default_factory=list)
    avoid_mechanisms: List[str] = Field(default_factory=list)
    
    # User history
    user_history: Optional[UserHistory] = None
    
    # Context fitness indicators
    exploration_budget: float = Field(
        ge=0.0, le=1.0, default=0.1,
        description="How much exploration vs exploitation"
    )
    
    data_freshness: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    
    def to_prompt_context(self) -> str:
        """
        Convert priors to human-readable context for Claude.
        
        Returns:
            Formatted string suitable for injection into Claude's prompt
        """
        lines = [
            "<empirical_priors>",
            f"Data freshness: {self.data_freshness.isoformat()}",
            ""
        ]
        
        # User history
        if self.user_history:
            h = self.user_history
            lines.append("USER HISTORY:")
            lines.append(f"- Total impressions: {h.total_impressions}")
            lines.append(f"- Historical conversion rate: {h.historical_conversion_rate:.2%}")
            if h.successful_mechanisms:
                lines.append(f"- Previously successful mechanisms: {', '.join(h.successful_mechanisms)}")
            if h.failed_mechanisms:
                lines.append(f"- Previously failed mechanisms: {', '.join(h.failed_mechanisms)}")
            if h.validated_personality_traits:
                lines.append(f"- Validated traits: {h.validated_personality_traits}")
            lines.append("")
        
        # Arm performance
        if self.arm_stats:
            lines.append("ARM PERFORMANCE (sorted by expected value):")
            sorted_arms = sorted(self.arm_stats, key=lambda a: a.expected_value, reverse=True)
            for arm in sorted_arms[:5]:  # Top 5 arms
                lines.append(
                    f"- {arm.arm_name}: {arm.expected_value:.2%} expected "
                    f"(α={arm.alpha:.1f}, β={arm.beta:.1f}, n={arm.total_pulls})"
                )
            if self.top_arm:
                lines.append(f"- Recommended arm: {self.top_arm} (confidence: {self.top_arm_confidence:.2%})")
            lines.append("")
        
        # Mechanism effectiveness
        if self.mechanism_stats:
            lines.append("MECHANISM EFFECTIVENESS:")
            for mech in self.mechanism_stats:
                sig = "✓" if mech.is_significant else "?"
                lines.append(
                    f"- {mech.mechanism_name}: {mech.overall_conversion_rate:.2%} "
                    f"(n={mech.overall_sample_size}) {sig}"
                )
            if self.recommended_mechanisms:
                lines.append(f"- RECOMMENDED: {', '.join(self.recommended_mechanisms)}")
            if self.avoid_mechanisms:
                lines.append(f"- AVOID: {', '.join(self.avoid_mechanisms)}")
            lines.append("")
        
        # Exploration guidance
        lines.append(f"EXPLORATION BUDGET: {self.exploration_budget:.0%}")
        if self.exploration_budget > 0.2:
            lines.append("(High exploration - prioritize learning over exploitation)")
        elif self.exploration_budget < 0.05:
            lines.append("(Low exploration - prioritize best-known options)")
        
        lines.append("</empirical_priors>")
        
        return "\n".join(lines)


class PriorExtractionRequest(BaseModel):
    """Request to extract priors for a user."""
    request_id: str
    user_id: str
    ad_category: Optional[str] = None
    include_arm_stats: bool = True
    include_segment_stats: bool = True
    include_mechanism_stats: bool = True
    include_user_history: bool = True
    max_arms: int = Field(default=10, ge=1, le=50)


class PriorExtractionResult(BaseModel):
    """Result of prior extraction."""
    request_id: str
    priors: EmpiricalPriors
    extraction_time_ms: float = Field(ge=0.0)
    cache_hit: bool = False
    data_sources: List[str] = Field(default_factory=list)
```

---

# SECTION C: CREDIT ATTRIBUTION ENGINE

## Multi-Method Attribution

```python
# =============================================================================
# ADAM Enhancement #06: Credit Attribution Engine
# Location: adam/gradient_bridge/attribution/engine.py
# =============================================================================

"""
Multi-method credit attribution engine.

Combines multiple attribution methods to accurately assign credit
for outcomes across all ADAM components, enabling precise learning
signal propagation.

Research Basis:
- QLLM (2024): LLM-guided credit assignment
- Turn-Level Credit (2023): Fine-grained advantage estimation  
- Shapley Values (1953): Marginal contribution estimation
- Agent Lightning (2024): Hierarchical attribution
"""

from __future__ import annotations
import asyncio
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, TYPE_CHECKING
import math
import logging

from pydantic import BaseModel

from adam.gradient_bridge.enums import (
    ComponentType, AttributionMethod, OutcomeType, ExecutionPath
)
from adam.gradient_bridge.models.credit import (
    CreditAssignment, AtomCreditAssignment, AttributionResult, AttributionConfig
)

if TYPE_CHECKING:
    from adam.atoms.base import AtomOutput
    from adam.llm.client import LLMClient

logger = logging.getLogger(__name__)


class CreditAttributionEngine:
    """
    Multi-method credit attribution engine.
    
    Combines confidence-weighted, LLM-guided, counterfactual, and
    Shapley-based attribution methods to produce ensemble credit
    assignments for each outcome.
    """
    
    def __init__(
        self,
        config: AttributionConfig,
        llm_client: Optional["LLMClient"] = None
    ):
        """
        Initialize the attribution engine.
        
        Args:
            config: Attribution configuration
            llm_client: Optional LLM client for LLM-guided attribution
        """
        self.config = config
        self.llm_client = llm_client
        self._attribution_count = 0
    
    async def compute_attribution(
        self,
        request_id: str,
        decision_id: str,
        user_id: str,
        outcome_type: OutcomeType,
        outcome_value: float,
        atom_outputs: Dict[str, "AtomOutput"],
        bandit_arm_id: str,
        bandit_uncertainty: float,
        graph_profile_completeness: float,
        execution_path: ExecutionPath,
        path_confidence: float,
        verification_confidence: Optional[float] = None,
        trace_id: Optional[str] = None
    ) -> AttributionResult:
        """
        Compute multi-level credit attribution for an outcome.
        
        This is the main entry point for attribution computation.
        Uses ensemble of methods weighted by config.
        
        Args:
            request_id: Request identifier
            decision_id: Decision identifier
            user_id: User identifier
            outcome_type: Type of outcome (conversion, click, etc.)
            outcome_value: Outcome value (0.0-1.0)
            atom_outputs: Outputs from each atom in the DAG
            bandit_arm_id: Selected bandit arm
            bandit_uncertainty: Bandit's uncertainty for this arm
            graph_profile_completeness: How complete is user's profile
            execution_path: Which path was taken (fast/reasoning/exploration)
            path_confidence: Meta-learner's confidence in path choice
            verification_confidence: Optional verification layer confidence
            trace_id: Optional distributed trace ID
            
        Returns:
            AttributionResult with per-component credits
        """
        start_time = time.perf_counter()
        methods_used = []
        
        # 1. Confidence-weighted attribution (always computed)
        atom_credits_cw = self._attribute_atoms_confidence_weighted(
            atom_outputs, outcome_value
        )
        bandit_credit_cw = self._attribute_bandit(
            bandit_uncertainty, outcome_value
        )
        graph_credit_cw = self._attribute_graph(
            graph_profile_completeness, outcome_value
        )
        meta_credit_cw = self._attribute_meta_learner(
            execution_path, path_confidence, outcome_value
        )
        methods_used.append(AttributionMethod.CONFIDENCE_WEIGHTED)
        
        # 2. LLM-guided attribution (if enabled and outcome meets threshold)
        atom_credits_llm = None
        if (
            self.config.use_llm_attribution 
            and self.llm_client 
            and outcome_value >= self.config.llm_attribution_threshold
        ):
            try:
                atom_credits_llm = await self._llm_evaluate_atoms(
                    atom_outputs, outcome_type, outcome_value
                )
                methods_used.append(AttributionMethod.LLM_GUIDED)
            except Exception as e:
                logger.warning(f"LLM attribution failed: {e}")
        
        # 3. Blend attribution methods using configured weights
        atom_credits = self._blend_atom_credits(
            atom_credits_cw,
            atom_credits_llm,
            atom_outputs
        )
        
        # 4. Compute verification credit if applicable
        verification_credit = None
        if verification_confidence is not None:
            verification_credit = self._attribute_verification(
                verification_confidence, outcome_value
            )
        
        # 5. Normalize credits to sum to ~1.0
        all_credits = self._normalize_credits(
            atom_credits,
            bandit_credit_cw,
            graph_credit_cw,
            meta_credit_cw,
            verification_credit
        )
        
        computation_time_ms = (time.perf_counter() - start_time) * 1000
        self._attribution_count += 1
        
        return AttributionResult(
            request_id=request_id,
            decision_id=decision_id,
            user_id=user_id,
            outcome_type=outcome_type,
            outcome_value=outcome_value,
            atom_credits=all_credits["atoms"],
            bandit_credit=all_credits["bandit"],
            graph_credit=all_credits["graph"],
            meta_learner_credit=all_credits["meta_learner"],
            verification_credit=all_credits.get("verification"),
            attribution_methods_used=methods_used,
            computation_time_ms=computation_time_ms,
            trace_id=trace_id
        )
    
    def _attribute_atoms_confidence_weighted(
        self,
        atom_outputs: Dict[str, "AtomOutput"],
        outcome_value: float
    ) -> Dict[str, float]:
        """
        Attribute credit to atoms based on their confidence.
        
        Higher confidence atoms get more credit when outcomes are positive,
        and more blame when outcomes are negative.
        
        Args:
            atom_outputs: Dict mapping atom name to output
            outcome_value: Outcome value (0.0-1.0)
            
        Returns:
            Dict mapping atom name to credit score
        """
        if not atom_outputs:
            return {}
        
        credits = {}
        total_confidence = sum(
            ao.confidence for ao in atom_outputs.values() if hasattr(ao, 'confidence')
        )
        
        if total_confidence == 0:
            # Equal distribution if no confidence available
            equal_credit = 1.0 / len(atom_outputs)
            return {name: equal_credit for name in atom_outputs}
        
        for name, output in atom_outputs.items():
            confidence = getattr(output, 'confidence', 0.5)
            
            # Credit = normalized confidence * outcome alignment
            # Positive outcomes: high confidence = high credit
            # Negative outcomes: high confidence = high blame (negative credit signal)
            base_credit = confidence / total_confidence
            
            # Scale by outcome (centered at 0.5)
            outcome_factor = 0.5 + (outcome_value - 0.5) * confidence
            
            credits[name] = base_credit * outcome_factor
        
        return credits
    
    async def _llm_evaluate_atoms(
        self,
        atom_outputs: Dict[str, "AtomOutput"],
        outcome_type: OutcomeType,
        outcome_value: float
    ) -> Dict[str, float]:
        """
        Use Claude to evaluate atom contributions (QLLM-inspired).
        
        Asks Claude to reason about which atoms most likely
        contributed to the observed outcome.
        
        Args:
            atom_outputs: Dict mapping atom name to output
            outcome_type: Type of outcome
            outcome_value: Outcome value
            
        Returns:
            Dict mapping atom name to LLM-assigned credit
        """
        if not self.llm_client or not atom_outputs:
            return {}
        
        # Format atom outputs for Claude
        atom_summary = []
        for name, output in atom_outputs.items():
            summary = {
                "atom": name,
                "confidence": getattr(output, 'confidence', 0.5),
                "key_outputs": self._extract_key_outputs(output)
            }
            atom_summary.append(summary)
        
        prompt = f"""Analyze the following atom outputs and determine which most likely contributed to the {outcome_type.value} outcome (value: {outcome_value:.2f}).

ATOM OUTPUTS:
{atom_summary}

For each atom, assign a credit score (0.0-1.0) based on:
1. How relevant was this atom's output to driving the {outcome_type.value}?
2. How confident was the atom in its predictions?
3. How well did the atom's predictions align with the outcome?

Respond with ONLY a JSON object mapping atom names to credit scores.
Example: {{"atom_personality": 0.35, "atom_mechanism": 0.45, ...}}
"""

        try:
            response = await self.llm_client.complete(
                prompt=prompt,
                max_tokens=self.config.llm_max_tokens,
                model=self.config.llm_model
            )
            
            # Parse JSON response
            import json
            credits = json.loads(response.content)
            
            # Validate and normalize
            validated = {}
            for name, score in credits.items():
                if name in atom_outputs and isinstance(score, (int, float)):
                    validated[name] = max(0.0, min(1.0, float(score)))
            
            return validated
            
        except Exception as e:
            logger.warning(f"LLM atom evaluation failed: {e}")
            return {}
    
    def _attribute_bandit(
        self,
        uncertainty: float,
        outcome_value: float
    ) -> CreditAssignment:
        """
        Attribute credit to the bandit based on its uncertainty.
        
        Lower uncertainty = bandit was more confident = more credit.
        
        Args:
            uncertainty: Bandit's uncertainty (0.0=certain, 1.0=uncertain)
            outcome_value: Outcome value
            
        Returns:
            CreditAssignment for bandit
        """
        # Inverse uncertainty as confidence proxy
        bandit_confidence = 1.0 - uncertainty
        
        # Credit scales with confidence and outcome
        if outcome_value > 0.5:
            # Positive outcome: confident bandit gets credit
            credit = bandit_confidence * outcome_value
        else:
            # Negative outcome: confident bandit gets blame
            credit = bandit_confidence * (1.0 - outcome_value) * 0.5
        
        return CreditAssignment(
            component_type=ComponentType.BANDIT,
            component_id="thompson_sampler",
            credit_score=min(1.0, credit),
            confidence=bandit_confidence,
            attribution_method=AttributionMethod.CONFIDENCE_WEIGHTED,
            evidence={
                "uncertainty": uncertainty,
                "outcome_value": outcome_value
            }
        )
    
    def _attribute_graph(
        self,
        profile_completeness: float,
        outcome_value: float
    ) -> CreditAssignment:
        """
        Attribute credit to graph based on profile completeness.
        
        More complete profiles = graph contributed more context.
        
        Args:
            profile_completeness: How complete is user's profile (0.0-1.0)
            outcome_value: Outcome value
            
        Returns:
            CreditAssignment for graph
        """
        # Graph credit based on how much context it provided
        base_credit = profile_completeness * 0.3  # Max 30% credit to graph
        
        # Scale by outcome alignment
        credit = base_credit * (0.5 + outcome_value * 0.5)
        
        return CreditAssignment(
            component_type=ComponentType.GRAPH,
            component_id="neo4j_knowledge_graph",
            credit_score=min(1.0, credit),
            confidence=profile_completeness,
            attribution_method=AttributionMethod.CONFIDENCE_WEIGHTED,
            evidence={
                "profile_completeness": profile_completeness,
                "outcome_value": outcome_value
            }
        )
    
    def _attribute_meta_learner(
        self,
        execution_path: ExecutionPath,
        path_confidence: float,
        outcome_value: float
    ) -> CreditAssignment:
        """
        Attribute credit to meta-learner for path selection.
        
        Credit based on whether the chosen path was appropriate.
        
        Args:
            execution_path: Which path was selected
            path_confidence: Meta-learner's confidence
            outcome_value: Outcome value
            
        Returns:
            CreditAssignment for meta-learner
        """
        # Meta-learner credit based on path appropriateness
        # High confidence + good outcome = good path choice
        if outcome_value > 0.5:
            credit = path_confidence * outcome_value * 0.5
        else:
            # Bad outcome with high confidence = bad path choice (low credit)
            credit = (1.0 - path_confidence) * 0.2
        
        return CreditAssignment(
            component_type=ComponentType.META_LEARNER,
            component_id="thompson_path_selector",
            credit_score=min(1.0, credit),
            confidence=path_confidence,
            attribution_method=AttributionMethod.CONFIDENCE_WEIGHTED,
            evidence={
                "execution_path": execution_path.value,
                "path_confidence": path_confidence,
                "outcome_value": outcome_value
            }
        )
    
    def _attribute_verification(
        self,
        verification_confidence: float,
        outcome_value: float
    ) -> CreditAssignment:
        """
        Attribute credit to verification layer for calibration.
        
        Args:
            verification_confidence: Confidence from verification layer
            outcome_value: Outcome value
            
        Returns:
            CreditAssignment for verification
        """
        # Verification credit based on calibration accuracy
        # If verification said high confidence and outcome was good = calibrated
        calibration_error = abs(verification_confidence - outcome_value)
        credit = (1.0 - calibration_error) * 0.1  # Max 10% credit
        
        return CreditAssignment(
            component_type=ComponentType.VERIFICATION,
            component_id="calibration_layer",
            credit_score=min(1.0, credit),
            confidence=1.0 - calibration_error,
            attribution_method=AttributionMethod.CONFIDENCE_WEIGHTED,
            evidence={
                "verification_confidence": verification_confidence,
                "outcome_value": outcome_value,
                "calibration_error": calibration_error
            }
        )
    
    def _blend_atom_credits(
        self,
        confidence_weighted: Dict[str, float],
        llm_guided: Optional[Dict[str, float]],
        atom_outputs: Dict[str, "AtomOutput"]
    ) -> Dict[str, AtomCreditAssignment]:
        """
        Blend confidence-weighted and LLM-guided atom credits.
        
        Args:
            confidence_weighted: Credits from confidence weighting
            llm_guided: Optional credits from LLM evaluation
            atom_outputs: Original atom outputs
            
        Returns:
            Dict mapping atom name to AtomCreditAssignment
        """
        cw_weight = self.config.method_weights[AttributionMethod.CONFIDENCE_WEIGHTED]
        llm_weight = self.config.method_weights.get(AttributionMethod.LLM_GUIDED, 0.0)
        
        # Normalize weights if LLM wasn't used
        if llm_guided is None:
            cw_weight = 1.0
            llm_weight = 0.0
        else:
            total = cw_weight + llm_weight
            cw_weight /= total
            llm_weight /= total
        
        result = {}
        for idx, (name, output) in enumerate(atom_outputs.items()):
            cw_credit = confidence_weighted.get(name, 0.0)
            llm_credit = llm_guided.get(name, cw_credit) if llm_guided else cw_credit
            
            blended_credit = cw_weight * cw_credit + llm_weight * llm_credit
            
            result[name] = AtomCreditAssignment(
                component_type=ComponentType(f"atom_{name}") if f"atom_{name}" in [e.value for e in ComponentType] else ComponentType.ATOM_PERSONALITY,
                component_id=name,
                atom_name=name,
                credit_score=blended_credit,
                confidence=getattr(output, 'confidence', 0.5),
                atom_confidence=getattr(output, 'confidence', 0.5),
                atom_output=output.model_dump() if hasattr(output, 'model_dump') else {},
                execution_order=idx,
                llm_evaluation_score=llm_credit if llm_guided else None,
                attribution_method=AttributionMethod.ENSEMBLE if llm_guided else AttributionMethod.CONFIDENCE_WEIGHTED
            )
        
        return result
    
    def _normalize_credits(
        self,
        atom_credits: Dict[str, AtomCreditAssignment],
        bandit_credit: CreditAssignment,
        graph_credit: CreditAssignment,
        meta_credit: CreditAssignment,
        verification_credit: Optional[CreditAssignment]
    ) -> Dict[str, Any]:
        """
        Normalize all credits to sum to approximately 1.0.
        
        Args:
            atom_credits: Per-atom credits
            bandit_credit: Bandit credit
            graph_credit: Graph credit
            meta_credit: Meta-learner credit
            verification_credit: Optional verification credit
            
        Returns:
            Dict with normalized credits for each component
        """
        # Sum all credits
        total = sum(ac.credit_score for ac in atom_credits.values())
        total += bandit_credit.credit_score
        total += graph_credit.credit_score
        total += meta_credit.credit_score
        if verification_credit:
            total += verification_credit.credit_score
        
        if total == 0:
            total = 1.0  # Avoid division by zero
        
        # Normalize
        for ac in atom_credits.values():
            ac.credit_score = ac.credit_score / total
        
        bandit_credit.credit_score = bandit_credit.credit_score / total
        graph_credit.credit_score = graph_credit.credit_score / total
        meta_credit.credit_score = meta_credit.credit_score / total
        
        if verification_credit:
            verification_credit.credit_score = verification_credit.credit_score / total
        
        return {
            "atoms": atom_credits,
            "bandit": bandit_credit,
            "graph": graph_credit,
            "meta_learner": meta_credit,
            "verification": verification_credit
        }
    
    def _extract_key_outputs(self, output: "AtomOutput") -> Dict[str, Any]:
        """Extract key outputs from an atom for LLM evaluation."""
        if hasattr(output, 'model_dump'):
            data = output.model_dump()
            # Filter to key fields
            key_fields = ['confidence', 'primary_trait', 'mechanism', 'score', 'level']
            return {k: v for k, v in data.items() if k in key_fields}
        return {}
```

---

# SECTION D: FEATURE EXTRACTION SYSTEM

## Feature Extractor Implementation

```python
# =============================================================================
# ADAM Enhancement #06: Feature Extraction System
# Location: adam/gradient_bridge/features/extractor.py
# =============================================================================

"""
Feature extraction from atom outputs for enriched bandit learning.
"""

from __future__ import annotations
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, TYPE_CHECKING
import logging

from adam.gradient_bridge.enums import ComponentType, ExecutionPath
from adam.gradient_bridge.models.features import (
    EnrichedBanditContext, FeatureExtractionResult
)

if TYPE_CHECKING:
    from adam.atoms.base import AtomOutput
    from adam.blackboard.client import BlackboardClient

logger = logging.getLogger(__name__)


# Atom names for feature extraction
ATOM_NAMES = [
    "user_state",
    "regulatory_focus", 
    "construal_level",
    "personality",
    "mechanism",
    "message_framing",
    "ad_selection"
]


class FeatureExtractor:
    """
    Extracts psychological features from atom outputs.
    
    Creates 40+ dimensional feature vectors for contextual bandits,
    enabling rich learning beyond simple reward signals.
    """
    
    def __init__(self, blackboard_client: Optional["BlackboardClient"] = None):
        """
        Initialize feature extractor.
        
        Args:
            blackboard_client: Optional blackboard for additional context
        """
        self.blackboard = blackboard_client
        self._extraction_count = 0
    
    async def extract(
        self,
        request_id: str,
        user_id: str,
        atom_outputs: Dict[str, "AtomOutput"],
        execution_path: Optional[ExecutionPath] = None,
        graph_context: Optional[Dict[str, Any]] = None
    ) -> FeatureExtractionResult:
        """
        Extract features from atom outputs.
        
        Args:
            request_id: Request identifier
            user_id: User identifier
            atom_outputs: Outputs from each atom
            execution_path: Which execution path was used
            graph_context: Optional context from Neo4j
            
        Returns:
            FeatureExtractionResult with enriched context
        """
        start_time = time.perf_counter()
        
        # Track which atoms are available
        available_atoms = list(atom_outputs.keys())
        missing_atoms = [a for a in ATOM_NAMES if a not in atom_outputs]
        
        # Initialize context with defaults
        context = EnrichedBanditContext(
            request_id=request_id,
            user_id=user_id,
            atom_sources={name: name in atom_outputs for name in ATOM_NAMES}
        )
        
        # Extract user state features
        if "user_state" in atom_outputs:
            context = self._extract_user_state(context, atom_outputs["user_state"])
        
        # Extract regulatory focus features
        if "regulatory_focus" in atom_outputs:
            context = self._extract_regulatory_focus(context, atom_outputs["regulatory_focus"])
        
        # Extract construal level features
        if "construal_level" in atom_outputs:
            context = self._extract_construal_level(context, atom_outputs["construal_level"])
        
        # Extract personality features
        if "personality" in atom_outputs:
            context = self._extract_personality(context, atom_outputs["personality"])
        
        # Extract mechanism features
        if "mechanism" in atom_outputs:
            context = self._extract_mechanism(context, atom_outputs["mechanism"])
        
        # Extract framing features
        if "message_framing" in atom_outputs:
            context = self._extract_framing(context, atom_outputs["message_framing"])
        
        # Set confidence features from all atoms
        context = self._extract_confidences(context, atom_outputs)
        
        # Set execution path features
        if execution_path:
            context = self._set_execution_features(context, execution_path)
        
        # Set graph context features
        if graph_context:
            context = self._set_graph_features(context, graph_context)
        
        # Calculate feature coverage
        feature_vector = context.to_feature_vector()
        non_default_count = sum(1 for f in feature_vector if f != 0.5 and f != 0.0)
        coverage = non_default_count / len(feature_vector)
        
        extraction_time_ms = (time.perf_counter() - start_time) * 1000
        self._extraction_count += 1
        
        return FeatureExtractionResult(
            request_id=request_id,
            enriched_context=context,
            extraction_time_ms=extraction_time_ms,
            atoms_available=available_atoms,
            atoms_missing=missing_atoms,
            feature_coverage=coverage
        )
    
    def _extract_user_state(
        self,
        context: EnrichedBanditContext,
        output: "AtomOutput"
    ) -> EnrichedBanditContext:
        """Extract user state features."""
        data = output.model_dump() if hasattr(output, 'model_dump') else {}
        
        context.user_state_arousal = data.get("arousal", 0.5)
        context.user_state_cognitive_load = data.get("cognitive_load", 0.5)
        context.user_state_receptivity = data.get("receptivity", 0.5)
        
        return context
    
    def _extract_regulatory_focus(
        self,
        context: EnrichedBanditContext,
        output: "AtomOutput"
    ) -> EnrichedBanditContext:
        """Extract regulatory focus features."""
        data = output.model_dump() if hasattr(output, 'model_dump') else {}
        
        context.regulatory_focus_promotion = data.get("promotion_score", 0.5)
        context.regulatory_focus_prevention = data.get("prevention_score", 0.5)
        
        return context
    
    def _extract_construal_level(
        self,
        context: EnrichedBanditContext,
        output: "AtomOutput"
    ) -> EnrichedBanditContext:
        """Extract construal level features."""
        data = output.model_dump() if hasattr(output, 'model_dump') else {}
        
        # Map construal to 0-1 scale (abstract=1.0, concrete=0.0)
        level = data.get("level", "balanced")
        if level == "abstract":
            context.construal_level = 0.8
        elif level == "concrete":
            context.construal_level = 0.2
        else:
            context.construal_level = data.get("score", 0.5)
        
        return context
    
    def _extract_personality(
        self,
        context: EnrichedBanditContext,
        output: "AtomOutput"
    ) -> EnrichedBanditContext:
        """Extract personality features (Big Five + extensions)."""
        data = output.model_dump() if hasattr(output, 'model_dump') else {}
        
        # Big Five
        traits = data.get("traits", {})
        context.personality_openness = traits.get("openness", 0.5)
        context.personality_conscientiousness = traits.get("conscientiousness", 0.5)
        context.personality_extraversion = traits.get("extraversion", 0.5)
        context.personality_agreeableness = traits.get("agreeableness", 0.5)
        context.personality_neuroticism = traits.get("neuroticism", 0.5)
        
        # Extended traits
        context.personality_need_for_cognition = traits.get("need_for_cognition", 0.5)
        context.personality_impulsivity = traits.get("impulsivity", 0.5)
        context.personality_risk_tolerance = traits.get("risk_tolerance", 0.5)
        context.personality_social_influence_susceptibility = traits.get(
            "social_influence_susceptibility", 0.5
        )
        context.personality_temporal_discounting = traits.get("temporal_discounting", 0.5)
        
        # Confidence in personality prediction
        context.personality_confidence = data.get("confidence", 0.5)
        
        return context
    
    def _extract_mechanism(
        self,
        context: EnrichedBanditContext,
        output: "AtomOutput"
    ) -> EnrichedBanditContext:
        """Extract mechanism selection features."""
        data = output.model_dump() if hasattr(output, 'model_dump') else {}
        
        # Primary mechanism as one-hot encoding with strength
        mechanisms = data.get("mechanisms", [])
        primary = data.get("primary_mechanism", "")
        strength = data.get("activation_strength", 0.5)
        
        mechanism_map = {
            "social_proof": "mechanism_social_proof",
            "scarcity": "mechanism_scarcity",
            "authority": "mechanism_authority",
            "reciprocity": "mechanism_reciprocity",
            "commitment": "mechanism_commitment",
            "liking": "mechanism_liking",
            "loss_aversion": "mechanism_loss_aversion",
            "anchoring": "mechanism_anchoring",
            "framing": "mechanism_framing"
        }
        
        # Set primary mechanism strength
        if primary in mechanism_map:
            setattr(context, mechanism_map[primary], strength)
        
        # Set secondary mechanisms with reduced strength
        for mech in mechanisms:
            if mech != primary and mech in mechanism_map:
                setattr(context, mechanism_map[mech], strength * 0.5)
        
        context.mechanism_primary_strength = strength
        
        return context
    
    def _extract_framing(
        self,
        context: EnrichedBanditContext,
        output: "AtomOutput"
    ) -> EnrichedBanditContext:
        """Extract message framing features."""
        data = output.model_dump() if hasattr(output, 'model_dump') else {}
        
        framing = data.get("framing", {})
        context.framing_emotional_appeal = framing.get("emotional_appeal", 0.5)
        context.framing_rational_appeal = framing.get("rational_appeal", 0.5)
        context.framing_urgency = framing.get("urgency", 0.5)
        context.framing_personalization = framing.get("personalization", 0.5)
        context.framing_storytelling = framing.get("storytelling", 0.5)
        context.framing_value_proposition = framing.get("value_proposition", 0.5)
        
        return context
    
    def _extract_confidences(
        self,
        context: EnrichedBanditContext,
        atom_outputs: Dict[str, "AtomOutput"]
    ) -> EnrichedBanditContext:
        """Extract confidence scores from all atoms."""
        def get_confidence(name: str) -> float:
            if name in atom_outputs:
                output = atom_outputs[name]
                if hasattr(output, 'confidence'):
                    return output.confidence
                elif hasattr(output, 'model_dump'):
                    return output.model_dump().get('confidence', 0.5)
            return 0.5
        
        context.confidence_user_state = get_confidence("user_state")
        context.confidence_regulatory = get_confidence("regulatory_focus")
        context.confidence_personality = get_confidence("personality")
        context.confidence_mechanism = get_confidence("mechanism")
        
        return context
    
    def _set_execution_features(
        self,
        context: EnrichedBanditContext,
        execution_path: ExecutionPath
    ) -> EnrichedBanditContext:
        """Set one-hot encoding for execution path."""
        context.execution_path_fast = 1.0 if execution_path == ExecutionPath.FAST else 0.0
        context.execution_path_reasoning = 1.0 if execution_path == ExecutionPath.REASONING else 0.0
        context.execution_path_exploration = 1.0 if execution_path == ExecutionPath.EXPLORATION else 0.0
        
        # Complexity estimate based on path
        complexity_map = {
            ExecutionPath.FAST: 0.2,
            ExecutionPath.REASONING: 0.7,
            ExecutionPath.EXPLORATION: 0.9
        }
        context.execution_complexity = complexity_map.get(execution_path, 0.5)
        
        return context
    
    def _set_graph_features(
        self,
        context: EnrichedBanditContext,
        graph_context: Dict[str, Any]
    ) -> EnrichedBanditContext:
        """Set features from graph context."""
        context.graph_user_profile_completeness = graph_context.get(
            "profile_completeness", 0.0
        )
        context.graph_historical_conversion_rate = graph_context.get(
            "historical_conversion_rate", 0.0
        )
        
        return context
```

---

# SECTION E: GRADIENT BRIDGE CORE

## Signal Orchestrator

```python
# =============================================================================
# ADAM Enhancement #06: Gradient Bridge Core Orchestrator
# Location: adam/gradient_bridge/core/orchestrator.py
# =============================================================================

"""
Central orchestrator for cross-component learning signal propagation.
"""

from __future__ import annotations
import asyncio
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, TYPE_CHECKING
from dataclasses import dataclass, field
import logging

from pydantic import BaseModel, Field

from adam.gradient_bridge.enums import ComponentType, SignalType, OutcomeType, ExecutionPath
from adam.gradient_bridge.models.credit import AttributionResult, AttributionConfig
from adam.gradient_bridge.models.signals import (
    LearningSignalEvent, BanditUpdateSignal, GraphUpdateSignal,
    MetaLearnerUpdateSignal, CalibrationUpdateSignal, SignalBatch
)
from adam.gradient_bridge.models.features import EnrichedBanditContext
from adam.gradient_bridge.attribution.engine import CreditAttributionEngine
from adam.gradient_bridge.features.extractor import FeatureExtractor

if TYPE_CHECKING:
    from adam.atoms.base import AtomOutput
    from adam.events.producer import ADAMEventProducer
    from adam.cache.layer import CacheLayer

logger = logging.getLogger(__name__)


class GradientBridgeConfig(BaseModel):
    """Configuration for the Gradient Bridge orchestrator."""
    
    # Attribution settings
    attribution_config: AttributionConfig = Field(default_factory=AttributionConfig)
    
    # Propagation settings
    parallel_propagation: bool = True
    propagation_timeout_seconds: float = 5.0
    max_retries: int = 3
    
    # Feature extraction
    extract_features: bool = True
    
    # Event emission
    emit_events: bool = True
    
    # Cache settings
    cache_attributions: bool = True
    cache_ttl_seconds: int = 300
    
    # Signal history
    keep_signal_history: bool = True
    max_history_size: int = 1000


@dataclass
class PropagationResult:
    """Result of propagating a signal to a component."""
    component: str
    success: bool
    latency_ms: Optional[float] = None
    error: Optional[str] = None
    signal_id: Optional[str] = None


class GradientBridgeOrchestrator:
    """
    Central orchestrator for cross-component learning.
    
    Receives outcomes, computes multi-level attribution, extracts
    features, and propagates learning signals to all components.
    """
    
    def __init__(
        self,
        config: GradientBridgeConfig,
        attribution_engine: CreditAttributionEngine,
        feature_extractor: FeatureExtractor,
        event_producer: Optional["ADAMEventProducer"] = None,
        cache_layer: Optional["CacheLayer"] = None
    ):
        """
        Initialize the Gradient Bridge orchestrator.
        
        Args:
            config: Bridge configuration
            attribution_engine: Credit attribution engine
            feature_extractor: Feature extraction system
            event_producer: Optional Kafka event producer
            cache_layer: Optional cache layer
        """
        self.config = config
        self.attribution_engine = attribution_engine
        self.feature_extractor = feature_extractor
        self.event_producer = event_producer
        self.cache = cache_layer
        
        self._signal_history: List[LearningSignalEvent] = []
        self._processing_count = 0
    
    async def process_outcome(
        self,
        request_id: str,
        decision_id: str,
        user_id: str,
        outcome_type: OutcomeType,
        outcome_value: float,
        atom_outputs: Dict[str, "AtomOutput"],
        bandit_arm_id: str,
        bandit_uncertainty: float,
        graph_profile_completeness: float,
        execution_path: ExecutionPath,
        path_confidence: float,
        ad_id: str,
        verification_confidence: Optional[float] = None,
        trace_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process an outcome through the Gradient Bridge.
        
        This is the main entry point. It:
        1. Computes multi-level credit attribution
        2. Extracts features for bandit learning
        3. Propagates signals to all components
        4. Emits events to Kafka
        5. Updates caches
        
        Args:
            request_id: Request identifier
            decision_id: Decision identifier
            user_id: User identifier
            outcome_type: Type of outcome
            outcome_value: Outcome value (0.0-1.0)
            atom_outputs: Outputs from each atom
            bandit_arm_id: Selected bandit arm
            bandit_uncertainty: Bandit's uncertainty
            graph_profile_completeness: User profile completeness
            execution_path: Which path was taken
            path_confidence: Meta-learner's confidence
            ad_id: Advertisement identifier
            verification_confidence: Optional verification confidence
            trace_id: Optional distributed trace ID
            
        Returns:
            Dict with attribution result and propagation results
        """
        start_time = time.perf_counter()
        self._processing_count += 1
        
        # 1. Compute credit attribution
        attribution = await self.attribution_engine.compute_attribution(
            request_id=request_id,
            decision_id=decision_id,
            user_id=user_id,
            outcome_type=outcome_type,
            outcome_value=outcome_value,
            atom_outputs=atom_outputs,
            bandit_arm_id=bandit_arm_id,
            bandit_uncertainty=bandit_uncertainty,
            graph_profile_completeness=graph_profile_completeness,
            execution_path=execution_path,
            path_confidence=path_confidence,
            verification_confidence=verification_confidence,
            trace_id=trace_id
        )
        
        # 2. Extract features for bandit
        features = None
        if self.config.extract_features:
            feature_result = await self.feature_extractor.extract(
                request_id=request_id,
                user_id=user_id,
                atom_outputs=atom_outputs,
                execution_path=execution_path,
                graph_context={"profile_completeness": graph_profile_completeness}
            )
            features = feature_result.enriched_context
        
        # 3. Create learning signals
        signals = self._create_signals(
            attribution=attribution,
            features=features,
            bandit_arm_id=bandit_arm_id,
            execution_path=execution_path,
            ad_id=ad_id,
            verification_confidence=verification_confidence
        )
        
        # 4. Propagate signals to components
        if self.config.parallel_propagation:
            propagation_results = await self._propagate_parallel(signals)
        else:
            propagation_results = await self._propagate_sequential(signals)
        
        # 5. Emit events to Kafka
        if self.config.emit_events and self.event_producer:
            await self._emit_learning_signals(attribution, signals)
        
        # 6. Cache attribution
        if self.config.cache_attributions and self.cache:
            await self.cache.set_attribution(attribution)
        
        # 7. Track signal history
        if self.config.keep_signal_history:
            self._add_to_history(signals)
        
        processing_time_ms = (time.perf_counter() - start_time) * 1000
        
        return {
            "attribution": attribution,
            "features": features,
            "signals_created": len(signals.signals),
            "propagation_results": propagation_results,
            "processing_time_ms": processing_time_ms
        }
    
    def _create_signals(
        self,
        attribution: AttributionResult,
        features: Optional[EnrichedBanditContext],
        bandit_arm_id: str,
        execution_path: ExecutionPath,
        ad_id: str,
        verification_confidence: Optional[float]
    ) -> SignalBatch:
        """
        Create all learning signals from attribution result.
        
        Args:
            attribution: Credit attribution result
            features: Optional enriched features
            bandit_arm_id: Bandit arm ID
            execution_path: Execution path taken
            ad_id: Advertisement ID
            verification_confidence: Optional verification confidence
            
        Returns:
            SignalBatch containing all signals
        """
        signals: List[LearningSignalEvent] = []
        
        # 1. Bandit update signal
        feature_vector = features.to_feature_vector() if features else []
        feature_names = EnrichedBanditContext.feature_names() if features else []
        
        bandit_signal = BanditUpdateSignal(
            source_component=ComponentType.GRADIENT_BRIDGE,
            arm_id=bandit_arm_id,
            reward=attribution.outcome_value,
            weighted_reward=attribution.outcome_value * attribution.bandit_credit.credit_score,
            credit_weight=attribution.bandit_credit.credit_score,
            feature_vector=feature_vector,
            feature_names=feature_names,
            user_segment=features.user_id if features else None,
            execution_path=execution_path,
            trace_id=attribution.trace_id
        )
        signals.append(bandit_signal)
        
        # 2. Graph update signal
        primary_mechanism = None
        mechanism_strength = 0.5
        if features:
            # Find primary mechanism from features
            mechanism_attrs = [
                ("social_proof", features.mechanism_social_proof),
                ("scarcity", features.mechanism_scarcity),
                ("authority", features.mechanism_authority),
                ("reciprocity", features.mechanism_reciprocity),
                ("commitment", features.mechanism_commitment),
                ("liking", features.mechanism_liking),
                ("loss_aversion", features.mechanism_loss_aversion),
                ("anchoring", features.mechanism_anchoring),
                ("framing", features.mechanism_framing)
            ]
            primary = max(mechanism_attrs, key=lambda x: x[1])
            if primary[1] > 0:
                primary_mechanism = primary[0]
                mechanism_strength = primary[1]
        
        graph_signal = GraphUpdateSignal(
            source_component=ComponentType.GRADIENT_BRIDGE,
            decision_id=attribution.decision_id,
            user_id=attribution.user_id,
            ad_id=ad_id,
            outcome=attribution.outcome_value,
            dominant_contributor=attribution.dominant_contributor,
            attribution_entropy=attribution.attribution_entropy,
            atom_credits={name: ac.credit_score for name, ac in attribution.atom_credits.items()},
            primary_mechanism=primary_mechanism,
            mechanism_activation_strength=mechanism_strength,
            trace_id=attribution.trace_id
        )
        signals.append(graph_signal)
        
        # 3. Meta-learner update signal
        meta_signal = MetaLearnerUpdateSignal(
            source_component=ComponentType.GRADIENT_BRIDGE,
            execution_path=execution_path,
            path_confidence=attribution.meta_learner_credit.confidence,
            outcome=attribution.outcome_value,
            credit=attribution.meta_learner_credit.credit_score,
            weighted_outcome=attribution.outcome_value * attribution.meta_learner_credit.credit_score,
            context_complexity=features.execution_complexity if features else 0.5,
            user_data_richness=features.graph_user_profile_completeness if features else 0.5,
            is_cold_start=(features.graph_historical_conversion_rate == 0.0) if features else False,
            trace_id=attribution.trace_id
        )
        signals.append(meta_signal)
        
        # 4. Calibration update signal (if verification layer used)
        if verification_confidence is not None:
            for atom_name, atom_credit in attribution.atom_credits.items():
                calib_signal = CalibrationUpdateSignal(
                    source_component=ComponentType.GRADIENT_BRIDGE,
                    predicted_confidence=atom_credit.atom_confidence,
                    actual_outcome=attribution.outcome_value > 0.5,
                    confidence_bin=int(atom_credit.atom_confidence * 10),
                    source_atom=atom_name,
                    trace_id=attribution.trace_id
                )
                signals.append(calib_signal)
        
        return SignalBatch(
            signals=signals,
            source_attribution_id=attribution.attribution_id
        )
    
    async def _propagate_parallel(
        self,
        signal_batch: SignalBatch
    ) -> List[PropagationResult]:
        """
        Propagate signals to components in parallel.
        
        Args:
            signal_batch: Batch of signals to propagate
            
        Returns:
            List of propagation results
        """
        tasks = []
        for signal in signal_batch.signals:
            task = self._propagate_single(signal)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        propagation_results = []
        for signal, result in zip(signal_batch.signals, results):
            if isinstance(result, Exception):
                propagation_results.append(PropagationResult(
                    component=signal.target_component.value,
                    success=False,
                    error=str(result)
                ))
            else:
                propagation_results.append(result)
        
        return propagation_results
    
    async def _propagate_sequential(
        self,
        signal_batch: SignalBatch
    ) -> List[PropagationResult]:
        """
        Propagate signals sequentially (useful for debugging).
        
        Args:
            signal_batch: Batch of signals to propagate
            
        Returns:
            List of propagation results
        """
        results = []
        for signal in signal_batch.signals:
            try:
                result = await self._propagate_single(signal)
                results.append(result)
            except Exception as e:
                results.append(PropagationResult(
                    component=signal.target_component.value,
                    success=False,
                    error=str(e)
                ))
        return results
    
    async def _propagate_single(
        self,
        signal: LearningSignalEvent
    ) -> PropagationResult:
        """
        Propagate a single signal to its target component.
        
        Args:
            signal: Signal to propagate
            
        Returns:
            PropagationResult
        """
        start_time = time.perf_counter()
        
        try:
            # Route to appropriate component updater
            if signal.target_component == ComponentType.BANDIT:
                await self._update_bandit(signal)
            elif signal.target_component == ComponentType.GRAPH:
                await self._update_graph(signal)
            elif signal.target_component == ComponentType.META_LEARNER:
                await self._update_meta_learner(signal)
            elif signal.target_component == ComponentType.VERIFICATION:
                await self._update_verification(signal)
            else:
                logger.warning(f"Unknown target component: {signal.target_component}")
            
            latency_ms = (time.perf_counter() - start_time) * 1000
            
            return PropagationResult(
                component=signal.target_component.value,
                success=True,
                latency_ms=latency_ms,
                signal_id=signal.signal_id
            )
            
        except Exception as e:
            logger.error(f"Failed to propagate signal to {signal.target_component}: {e}")
            return PropagationResult(
                component=signal.target_component.value,
                success=False,
                error=str(e)
            )
    
    async def _update_bandit(self, signal: BanditUpdateSignal) -> None:
        """Update bandit with enriched reward signal."""
        # Implementation connects to bandit updater
        # This is where the 40+ features are passed to contextual bandit
        logger.debug(
            f"Bandit update: arm={signal.arm_id}, "
            f"reward={signal.reward:.3f}, "
            f"weighted_reward={signal.weighted_reward:.3f}, "
            f"features_dim={len(signal.feature_vector)}"
        )
    
    async def _update_graph(self, signal: GraphUpdateSignal) -> None:
        """Update Neo4j graph with outcome information."""
        logger.debug(
            f"Graph update: user={signal.user_id}, "
            f"outcome={signal.outcome:.3f}, "
            f"mechanism={signal.primary_mechanism}"
        )
    
    async def _update_meta_learner(self, signal: MetaLearnerUpdateSignal) -> None:
        """Update meta-learner Thompson Sampling posteriors."""
        logger.debug(
            f"Meta-learner update: path={signal.execution_path}, "
            f"outcome={signal.outcome:.3f}, "
            f"credit={signal.credit:.3f}"
        )
    
    async def _update_verification(self, signal: CalibrationUpdateSignal) -> None:
        """Update verification layer calibration curve."""
        logger.debug(
            f"Calibration update: predicted={signal.predicted_confidence:.3f}, "
            f"actual={signal.actual_outcome}, "
            f"bin={signal.confidence_bin}"
        )
    
    async def _emit_learning_signals(
        self,
        attribution: AttributionResult,
        signal_batch: SignalBatch
    ) -> None:
        """Emit learning signals to Kafka topics."""
        if not self.event_producer:
            return
        
        # Emit attribution event
        await self.event_producer.emit_event(
            topic="adam.learning.attribution",
            event={
                "attribution_id": attribution.attribution_id,
                "request_id": attribution.request_id,
                "user_id": attribution.user_id,
                "outcome_type": attribution.outcome_type.value,
                "outcome_value": attribution.outcome_value,
                "dominant_contributor": attribution.dominant_contributor,
                "attribution_entropy": attribution.attribution_entropy,
                "timestamp": attribution.outcome_timestamp.isoformat()
            }
        )
        
        # Emit signals to component-specific topics
        topic_map = {
            ComponentType.BANDIT: "adam.learning.bandit",
            ComponentType.GRAPH: "adam.learning.graph",
            ComponentType.META_LEARNER: "adam.learning.meta_learner",
            ComponentType.VERIFICATION: "adam.learning.calibration"
        }
        
        for signal in signal_batch.signals:
            topic = topic_map.get(signal.target_component)
            if topic:
                await self.event_producer.emit_event(
                    topic=topic,
                    event=signal.model_dump(mode="json")
                )
    
    def _add_to_history(self, signal_batch: SignalBatch) -> None:
        """Add signals to history for debugging."""
        self._signal_history.extend(signal_batch.signals)
        
        # Trim if exceeds max size
        if len(self._signal_history) > self.config.max_history_size:
            self._signal_history = self._signal_history[-self.config.max_history_size:]
    
    def get_signal_history(
        self,
        limit: int = 100,
        component_filter: Optional[ComponentType] = None
    ) -> List[LearningSignalEvent]:
        """
        Get recent signal history.
        
        Args:
            limit: Max signals to return
            component_filter: Optional filter by target component
            
        Returns:
            List of recent signals
        """
        signals = self._signal_history[-limit:]
        
        if component_filter:
            signals = [s for s in signals if s.target_component == component_filter]
        
        return signals
```

---

# SECTION F: EVENT BUS INTEGRATION (#31)

## Kafka Topic Mapping

```python
# =============================================================================
# ADAM Enhancement #06: Event Bus Integration
# Location: adam/gradient_bridge/events/kafka.py
# =============================================================================

"""
Kafka integration for Gradient Bridge learning signals.
Integrates with Enhancement #31 Event Bus infrastructure.
"""

from __future__ import annotations
import json
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Callable, Awaitable
import logging

from pydantic import BaseModel, Field

from adam.gradient_bridge.enums import ComponentType, SignalType, OutcomeType
from adam.gradient_bridge.models.credit import AttributionResult
from adam.gradient_bridge.models.signals import (
    LearningSignalEvent, BanditUpdateSignal, GraphUpdateSignal,
    MetaLearnerUpdateSignal, CalibrationUpdateSignal
)

logger = logging.getLogger(__name__)


# =============================================================================
# KAFKA TOPIC DEFINITIONS
# =============================================================================

GRADIENT_BRIDGE_TOPICS = {
    # Input topics (consumed by Gradient Bridge)
    "outcome": "adam.learning.outcome",
    
    # Output topics (produced by Gradient Bridge)
    "attribution": "adam.learning.attribution",
    "bandit_update": "adam.learning.bandit",
    "graph_update": "adam.learning.graph",
    "meta_learner_update": "adam.learning.meta_learner",
    "calibration_update": "adam.learning.calibration",
    
    # Batch topics
    "signal_batch": "adam.learning.signal_batch",
    
    # Dead letter queue
    "dlq": "adam.learning.dlq"
}


# =============================================================================
# AVRO SCHEMAS
# =============================================================================

ATTRIBUTION_EVENT_SCHEMA = {
    "type": "record",
    "name": "AttributionEvent",
    "namespace": "adam.gradient_bridge",
    "fields": [
        {"name": "attribution_id", "type": "string"},
        {"name": "request_id", "type": "string"},
        {"name": "decision_id", "type": "string"},
        {"name": "user_id", "type": "string"},
        {"name": "outcome_type", "type": "string"},
        {"name": "outcome_value", "type": "double"},
        {"name": "dominant_contributor", "type": "string"},
        {"name": "dominant_credit", "type": "double"},
        {"name": "attribution_entropy", "type": "double"},
        {"name": "computation_time_ms", "type": "double"},
        {"name": "timestamp", "type": "string"},
        {"name": "trace_id", "type": ["null", "string"], "default": None}
    ]
}


OUTCOME_EVENT_SCHEMA = {
    "type": "record",
    "name": "OutcomeEvent",
    "namespace": "adam.gradient_bridge",
    "fields": [
        {"name": "event_id", "type": "string"},
        {"name": "request_id", "type": "string"},
        {"name": "decision_id", "type": "string"},
        {"name": "user_id", "type": "string"},
        {"name": "ad_id", "type": "string"},
        {"name": "outcome_type", "type": "string"},
        {"name": "outcome_value", "type": "double"},
        {"name": "timestamp", "type": "string"},
        {"name": "trace_id", "type": ["null", "string"], "default": None}
    ]
}


# =============================================================================
# EVENT EMITTER
# =============================================================================

class GradientBridgeEventEmitter:
    """
    Emits learning signals to Kafka topics.
    
    Integrates with Enhancement #31 ADAMEventProducer.
    """
    
    def __init__(
        self,
        producer: Any,  # ADAMEventProducer from #31
        metrics_collector: Optional[Any] = None
    ):
        """
        Initialize event emitter.
        
        Args:
            producer: Kafka producer from Enhancement #31
            metrics_collector: Optional metrics collector
        """
        self.producer = producer
        self.metrics = metrics_collector
        self._emit_count = 0
    
    async def emit_attribution(
        self,
        attribution: AttributionResult
    ) -> bool:
        """
        Emit attribution event to Kafka.
        
        Args:
            attribution: Attribution result to emit
            
        Returns:
            True if successful
        """
        start_time = time.perf_counter()
        
        event = {
            "attribution_id": attribution.attribution_id,
            "request_id": attribution.request_id,
            "decision_id": attribution.decision_id,
            "user_id": attribution.user_id,
            "outcome_type": attribution.outcome_type.value,
            "outcome_value": attribution.outcome_value,
            "dominant_contributor": attribution.dominant_contributor,
            "dominant_credit": attribution.dominant_credit,
            "attribution_entropy": attribution.attribution_entropy,
            "computation_time_ms": attribution.computation_time_ms,
            "timestamp": attribution.outcome_timestamp.isoformat(),
            "trace_id": attribution.trace_id
        }
        
        try:
            await self.producer.send(
                topic=GRADIENT_BRIDGE_TOPICS["attribution"],
                key=attribution.user_id,
                value=event
            )
            
            latency_ms = (time.perf_counter() - start_time) * 1000
            self._emit_count += 1
            
            if self.metrics:
                self.metrics.record_kafka_emit(
                    topic=GRADIENT_BRIDGE_TOPICS["attribution"],
                    success=True,
                    latency_ms=latency_ms
                )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to emit attribution event: {e}")
            if self.metrics:
                self.metrics.record_kafka_emit(
                    topic=GRADIENT_BRIDGE_TOPICS["attribution"],
                    success=False,
                    latency_ms=0.0
                )
            return False
    
    async def emit_bandit_update(
        self,
        signal: BanditUpdateSignal
    ) -> bool:
        """Emit bandit update signal to Kafka."""
        return await self._emit_signal(
            topic=GRADIENT_BRIDGE_TOPICS["bandit_update"],
            signal=signal,
            key=signal.arm_id
        )
    
    async def emit_graph_update(
        self,
        signal: GraphUpdateSignal
    ) -> bool:
        """Emit graph update signal to Kafka."""
        return await self._emit_signal(
            topic=GRADIENT_BRIDGE_TOPICS["graph_update"],
            signal=signal,
            key=signal.user_id
        )
    
    async def emit_meta_learner_update(
        self,
        signal: MetaLearnerUpdateSignal
    ) -> bool:
        """Emit meta-learner update signal to Kafka."""
        return await self._emit_signal(
            topic=GRADIENT_BRIDGE_TOPICS["meta_learner_update"],
            signal=signal,
            key=signal.execution_path.value
        )
    
    async def emit_calibration_update(
        self,
        signal: CalibrationUpdateSignal
    ) -> bool:
        """Emit calibration update signal to Kafka."""
        return await self._emit_signal(
            topic=GRADIENT_BRIDGE_TOPICS["calibration_update"],
            signal=signal,
            key=str(signal.confidence_bin)
        )
    
    async def _emit_signal(
        self,
        topic: str,
        signal: LearningSignalEvent,
        key: str
    ) -> bool:
        """Generic signal emission."""
        start_time = time.perf_counter()
        
        try:
            await self.producer.send(
                topic=topic,
                key=key,
                value=signal.model_dump(mode="json")
            )
            
            latency_ms = (time.perf_counter() - start_time) * 1000
            self._emit_count += 1
            
            if self.metrics:
                self.metrics.record_kafka_emit(
                    topic=topic,
                    success=True,
                    latency_ms=latency_ms
                )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to emit signal to {topic}: {e}")
            if self.metrics:
                self.metrics.record_kafka_emit(
                    topic=topic,
                    success=False,
                    latency_ms=0.0
                )
            return False


# =============================================================================
# OUTCOME EVENT CONSUMER
# =============================================================================

class OutcomeEventConsumer:
    """
    Consumes outcome events and triggers Gradient Bridge processing.
    """
    
    def __init__(
        self,
        consumer: Any,  # ADAMEventConsumer from #31
        gradient_bridge: Any,  # GradientBridgeOrchestrator
        decision_trace_fetcher: Callable[[str], Awaitable[Dict[str, Any]]]
    ):
        """
        Initialize outcome consumer.
        
        Args:
            consumer: Kafka consumer from Enhancement #31
            gradient_bridge: Gradient Bridge orchestrator
            decision_trace_fetcher: Function to fetch decision traces from blackboard/cache
        """
        self.consumer = consumer
        self.gradient_bridge = gradient_bridge
        self.fetch_trace = decision_trace_fetcher
        self._processed_count = 0
    
    async def start(self) -> None:
        """Start consuming outcome events."""
        await self.consumer.subscribe([GRADIENT_BRIDGE_TOPICS["outcome"]])
        
        async for message in self.consumer:
            try:
                await self.handle_outcome(message.value)
            except Exception as e:
                logger.error(f"Failed to process outcome event: {e}")
    
    async def handle_outcome(self, event: Dict[str, Any]) -> None:
        """
        Handle a single outcome event.
        
        Args:
            event: Outcome event from Kafka
        """
        decision_id = event.get("decision_id")
        if not decision_id:
            logger.warning("Outcome event missing decision_id")
            return
        
        # Fetch decision trace from blackboard/cache
        trace = await self.fetch_trace(decision_id)
        if not trace:
            logger.warning(f"No trace found for decision {decision_id}")
            return
        
        # Process through Gradient Bridge
        await self.gradient_bridge.process_outcome(
            request_id=event.get("request_id", decision_id),
            decision_id=decision_id,
            user_id=event.get("user_id"),
            outcome_type=OutcomeType(event.get("outcome_type", "conversion")),
            outcome_value=event.get("outcome_value", 0.0),
            atom_outputs=trace.get("atom_outputs", {}),
            bandit_arm_id=trace.get("bandit_arm_id", ""),
            bandit_uncertainty=trace.get("bandit_uncertainty", 0.5),
            graph_profile_completeness=trace.get("graph_profile_completeness", 0.0),
            execution_path=ExecutionPath(trace.get("execution_path", "reasoning")),
            path_confidence=trace.get("path_confidence", 0.5),
            ad_id=event.get("ad_id", ""),
            verification_confidence=trace.get("verification_confidence"),
            trace_id=event.get("trace_id")
        )
        
        self._processed_count += 1
```

---

# SECTION G: CACHE INTEGRATION (#31)

## Attribution Cache Layer

```python
# =============================================================================
# ADAM Enhancement #06: Cache Integration
# Location: adam/gradient_bridge/cache/layer.py
# =============================================================================

"""
Caching layer for Gradient Bridge with L1/L2 cache hierarchy.
Integrates with Enhancement #31 Cache infrastructure.
"""

from __future__ import annotations
import json
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, TYPE_CHECKING
from collections import OrderedDict
import logging

from pydantic import BaseModel, Field

from adam.gradient_bridge.models.credit import AttributionResult
from adam.gradient_bridge.models.priors import EmpiricalPriors, PriorExtractionResult

if TYPE_CHECKING:
    import redis.asyncio as redis

logger = logging.getLogger(__name__)


class CacheConfig(BaseModel):
    """Cache configuration for Gradient Bridge."""
    
    # TTLs in seconds
    attribution_ttl: int = 300  # 5 minutes
    priors_ttl: int = 3600  # 1 hour
    features_ttl: int = 900  # 15 minutes
    decision_trace_ttl: int = 604800  # 7 days
    
    # L1 cache settings
    l1_max_size: int = 10000
    l1_enabled: bool = True
    
    # L2 (Redis) settings
    l2_enabled: bool = True
    redis_key_prefix: str = "gradient_bridge:"
    
    # Compression
    compress_large_values: bool = True
    compression_threshold_bytes: int = 1024


class GradientBridgeCacheLayer:
    """
    Multi-level cache for Gradient Bridge data.
    
    L1: In-memory LRU cache for hot data
    L2: Redis for distributed persistence
    """
    
    def __init__(
        self,
        config: CacheConfig,
        redis_client: Optional["redis.Redis"] = None
    ):
        """
        Initialize cache layer.
        
        Args:
            config: Cache configuration
            redis_client: Optional Redis client for L2
        """
        self.config = config
        self.redis = redis_client
        
        # L1 caches (LRU)
        self._attribution_cache: OrderedDict[str, AttributionResult] = OrderedDict()
        self._priors_cache: OrderedDict[str, EmpiricalPriors] = OrderedDict()
        self._trace_cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        
        # Metrics
        self._hits = 0
        self._misses = 0
    
    # =========================================================================
    # ATTRIBUTION CACHE
    # =========================================================================
    
    async def get_attribution(
        self,
        attribution_id: str
    ) -> Optional[AttributionResult]:
        """
        Get attribution from cache.
        
        Args:
            attribution_id: Attribution identifier
            
        Returns:
            AttributionResult if found, else None
        """
        # L1 lookup
        if self.config.l1_enabled and attribution_id in self._attribution_cache:
            self._attribution_cache.move_to_end(attribution_id)
            self._hits += 1
            return self._attribution_cache[attribution_id]
        
        # L2 lookup
        if self.config.l2_enabled and self.redis:
            key = f"{self.config.redis_key_prefix}attribution:{attribution_id}"
            try:
                data = await self.redis.get(key)
                if data:
                    attribution = AttributionResult.model_validate_json(data)
                    # Populate L1
                    self._set_l1_attribution(attribution_id, attribution)
                    self._hits += 1
                    return attribution
            except Exception as e:
                logger.warning(f"Redis get failed: {e}")
        
        self._misses += 1
        return None
    
    async def set_attribution(
        self,
        attribution: AttributionResult
    ) -> None:
        """
        Store attribution in cache.
        
        Args:
            attribution: Attribution result to store
        """
        # L1 store
        if self.config.l1_enabled:
            self._set_l1_attribution(attribution.attribution_id, attribution)
        
        # L2 store
        if self.config.l2_enabled and self.redis:
            key = f"{self.config.redis_key_prefix}attribution:{attribution.attribution_id}"
            try:
                await self.redis.setex(
                    key,
                    self.config.attribution_ttl,
                    attribution.model_dump_json()
                )
            except Exception as e:
                logger.warning(f"Redis set failed: {e}")
    
    def _set_l1_attribution(
        self,
        key: str,
        value: AttributionResult
    ) -> None:
        """Set value in L1 attribution cache with LRU eviction."""
        self._attribution_cache[key] = value
        self._attribution_cache.move_to_end(key)
        
        # Evict if over size
        while len(self._attribution_cache) > self.config.l1_max_size:
            self._attribution_cache.popitem(last=False)
    
    # =========================================================================
    # PRIORS CACHE
    # =========================================================================
    
    async def get_priors(
        self,
        user_id: str,
        ad_category: Optional[str] = None
    ) -> Optional[EmpiricalPriors]:
        """
        Get empirical priors from cache.
        
        Args:
            user_id: User identifier
            ad_category: Optional ad category filter
            
        Returns:
            EmpiricalPriors if found, else None
        """
        cache_key = f"{user_id}:{ad_category or 'all'}"
        
        # L1 lookup
        if self.config.l1_enabled and cache_key in self._priors_cache:
            self._priors_cache.move_to_end(cache_key)
            self._hits += 1
            return self._priors_cache[cache_key]
        
        # L2 lookup
        if self.config.l2_enabled and self.redis:
            key = f"{self.config.redis_key_prefix}priors:{cache_key}"
            try:
                data = await self.redis.get(key)
                if data:
                    priors = EmpiricalPriors.model_validate_json(data)
                    # Populate L1
                    self._set_l1_priors(cache_key, priors)
                    self._hits += 1
                    return priors
            except Exception as e:
                logger.warning(f"Redis get priors failed: {e}")
        
        self._misses += 1
        return None
    
    async def set_priors(
        self,
        priors: EmpiricalPriors,
        ad_category: Optional[str] = None
    ) -> None:
        """
        Store empirical priors in cache.
        
        Args:
            priors: Empirical priors to store
            ad_category: Optional ad category
        """
        cache_key = f"{priors.user_id}:{ad_category or 'all'}"
        
        # L1 store
        if self.config.l1_enabled:
            self._set_l1_priors(cache_key, priors)
        
        # L2 store
        if self.config.l2_enabled and self.redis:
            key = f"{self.config.redis_key_prefix}priors:{cache_key}"
            try:
                await self.redis.setex(
                    key,
                    self.config.priors_ttl,
                    priors.model_dump_json()
                )
            except Exception as e:
                logger.warning(f"Redis set priors failed: {e}")
    
    def _set_l1_priors(
        self,
        key: str,
        value: EmpiricalPriors
    ) -> None:
        """Set value in L1 priors cache with LRU eviction."""
        self._priors_cache[key] = value
        self._priors_cache.move_to_end(key)
        
        while len(self._priors_cache) > self.config.l1_max_size:
            self._priors_cache.popitem(last=False)
    
    # =========================================================================
    # DECISION TRACE CACHE
    # =========================================================================
    
    async def store_decision_trace(
        self,
        decision_id: str,
        trace: Dict[str, Any]
    ) -> None:
        """
        Store decision trace for later outcome processing.
        
        Args:
            decision_id: Decision identifier
            trace: Decision trace data
        """
        # L1 store
        if self.config.l1_enabled:
            self._trace_cache[decision_id] = trace
            self._trace_cache.move_to_end(decision_id)
            
            while len(self._trace_cache) > self.config.l1_max_size:
                self._trace_cache.popitem(last=False)
        
        # L2 store
        if self.config.l2_enabled and self.redis:
            key = f"{self.config.redis_key_prefix}trace:{decision_id}"
            try:
                await self.redis.setex(
                    key,
                    self.config.decision_trace_ttl,
                    json.dumps(trace, default=str)
                )
            except Exception as e:
                logger.warning(f"Redis set trace failed: {e}")
    
    async def get_decision_trace(
        self,
        decision_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get decision trace from cache.
        
        Args:
            decision_id: Decision identifier
            
        Returns:
            Decision trace if found, else None
        """
        # L1 lookup
        if self.config.l1_enabled and decision_id in self._trace_cache:
            self._trace_cache.move_to_end(decision_id)
            return self._trace_cache[decision_id]
        
        # L2 lookup
        if self.config.l2_enabled and self.redis:
            key = f"{self.config.redis_key_prefix}trace:{decision_id}"
            try:
                data = await self.redis.get(key)
                if data:
                    trace = json.loads(data)
                    # Populate L1
                    if self.config.l1_enabled:
                        self._trace_cache[decision_id] = trace
                    return trace
            except Exception as e:
                logger.warning(f"Redis get trace failed: {e}")
        
        return None
    
    # =========================================================================
    # INVALIDATION
    # =========================================================================
    
    async def invalidate_user_priors(self, user_id: str) -> None:
        """
        Invalidate all cached priors for a user.
        
        Args:
            user_id: User identifier
        """
        # Clear L1
        keys_to_remove = [k for k in self._priors_cache if k.startswith(f"{user_id}:")]
        for key in keys_to_remove:
            del self._priors_cache[key]
        
        # Clear L2
        if self.config.l2_enabled and self.redis:
            pattern = f"{self.config.redis_key_prefix}priors:{user_id}:*"
            try:
                cursor = 0
                while True:
                    cursor, keys = await self.redis.scan(cursor, match=pattern)
                    if keys:
                        await self.redis.delete(*keys)
                    if cursor == 0:
                        break
            except Exception as e:
                logger.warning(f"Redis invalidate failed: {e}")
    
    async def invalidate_arm_priors(self, arm_id: str) -> None:
        """
        Invalidate priors related to a specific arm.
        
        This is called when arm statistics change significantly.
        
        Args:
            arm_id: Bandit arm identifier
        """
        # For arm changes, we invalidate all priors (conservative approach)
        # A more sophisticated approach would track arm->user mappings
        self._priors_cache.clear()
        
        if self.config.l2_enabled and self.redis:
            pattern = f"{self.config.redis_key_prefix}priors:*"
            try:
                cursor = 0
                while True:
                    cursor, keys = await self.redis.scan(cursor, match=pattern)
                    if keys:
                        await self.redis.delete(*keys)
                    if cursor == 0:
                        break
            except Exception as e:
                logger.warning(f"Redis arm invalidate failed: {e}")
    
    # =========================================================================
    # METRICS
    # =========================================================================
    
    def get_hit_rate(self) -> float:
        """Get cache hit rate."""
        total = self._hits + self._misses
        return self._hits / total if total > 0 else 0.0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": self.get_hit_rate(),
            "l1_attribution_size": len(self._attribution_cache),
            "l1_priors_size": len(self._priors_cache),
            "l1_trace_size": len(self._trace_cache),
            "l1_max_size": self.config.l1_max_size
        }
```

---

# SECTION H: NEO4J SCHEMA

## Attribution Graph Schema

```cypher
// =============================================================================
// ADAM Enhancement #06: Neo4j Schema
// Location: adam/gradient_bridge/schema/neo4j_schema.cypher
// =============================================================================

// =========================================================================
// CONSTRAINTS (Uniqueness)
// =========================================================================

CREATE CONSTRAINT decision_id_unique IF NOT EXISTS
FOR (d:Decision) REQUIRE d.decision_id IS UNIQUE;

CREATE CONSTRAINT attribution_id_unique IF NOT EXISTS
FOR (a:Attribution) REQUIRE a.attribution_id IS UNIQUE;

CREATE CONSTRAINT atom_name_unique IF NOT EXISTS
FOR (at:Atom) REQUIRE at.name IS UNIQUE;

CREATE CONSTRAINT learning_signal_id_unique IF NOT EXISTS
FOR (ls:LearningSignal) REQUIRE ls.signal_id IS UNIQUE;

CREATE CONSTRAINT mechanism_name_unique IF NOT EXISTS
FOR (m:Mechanism) REQUIRE m.name IS UNIQUE;


// =========================================================================
// INDEXES (Performance)
// =========================================================================

CREATE INDEX decision_timestamp IF NOT EXISTS
FOR (d:Decision) ON (d.timestamp);

CREATE INDEX decision_user_id IF NOT EXISTS
FOR (d:Decision) ON (d.user_id);

CREATE INDEX decision_outcome IF NOT EXISTS
FOR (d:Decision) ON (d.outcome_type);

CREATE INDEX attribution_dominant IF NOT EXISTS
FOR (a:Attribution) ON (a.dominant_contributor);

CREATE INDEX attribution_timestamp IF NOT EXISTS
FOR (a:Attribution) ON (a.timestamp);

CREATE INDEX user_mechanism_success IF NOT EXISTS
FOR ()-[r:RESPONDED_TO]-() ON (r.success);

CREATE INDEX signal_target IF NOT EXISTS
FOR (ls:LearningSignal) ON (ls.target_component);


// =========================================================================
// NODE TEMPLATES
// =========================================================================

// Atom nodes (created once, referenced by attribution)
MERGE (a:Atom {name: 'user_state'})
SET a.description = 'Infers current user psychological state';

MERGE (a:Atom {name: 'regulatory_focus'})
SET a.description = 'Determines promotion vs prevention focus';

MERGE (a:Atom {name: 'construal_level'})
SET a.description = 'Estimates abstract vs concrete thinking';

MERGE (a:Atom {name: 'personality'})
SET a.description = 'Infers Big Five and extended traits';

MERGE (a:Atom {name: 'mechanism'})
SET a.description = 'Selects persuasion mechanism';

MERGE (a:Atom {name: 'message_framing'})
SET a.description = 'Determines message framing strategy';

MERGE (a:Atom {name: 'ad_selection'})
SET a.description = 'Final advertisement selection';


// Mechanism nodes (created once, tracked for effectiveness)
MERGE (m:Mechanism {name: 'social_proof'})
SET m.description = 'Others are doing it';

MERGE (m:Mechanism {name: 'scarcity'})
SET m.description = 'Limited availability';

MERGE (m:Mechanism {name: 'authority'})
SET m.description = 'Expert endorsement';

MERGE (m:Mechanism {name: 'reciprocity'})
SET m.description = 'Give to get';

MERGE (m:Mechanism {name: 'commitment'})
SET m.description = 'Consistency principle';

MERGE (m:Mechanism {name: 'liking'})
SET m.description = 'Likability influence';

MERGE (m:Mechanism {name: 'loss_aversion'})
SET m.description = 'Fear of missing out';

MERGE (m:Mechanism {name: 'anchoring'})
SET m.description = 'Reference point setting';

MERGE (m:Mechanism {name: 'framing'})
SET m.description = 'Positive vs negative framing';
```

## Learning Analytics Queries

```cypher
// =============================================================================
// ADAM Enhancement #06: Neo4j Queries
// Location: adam/gradient_bridge/queries/analytics.cypher
// =============================================================================

// =========================================================================
// QUERY 1: Create decision with attribution
// =========================================================================

// Create a decision node with full attribution
CREATE (d:Decision {
    decision_id: $decision_id,
    request_id: $request_id,
    user_id: $user_id,
    ad_id: $ad_id,
    outcome_type: $outcome_type,
    outcome_value: $outcome_value,
    timestamp: datetime()
})
WITH d
CREATE (a:Attribution {
    attribution_id: $attribution_id,
    dominant_contributor: $dominant_contributor,
    dominant_credit: $dominant_credit,
    attribution_entropy: $attribution_entropy,
    computation_time_ms: $computation_time_ms
})
CREATE (d)-[:HAS_ATTRIBUTION]->(a)
WITH d, a
MATCH (u:User {user_id: $user_id})
CREATE (u)-[:MADE_DECISION]->(d)
WITH d, a
MATCH (ad:Advertisement {ad_id: $ad_id})
CREATE (d)-[:SELECTED_AD]->(ad)
RETURN d, a;


// =========================================================================
// QUERY 2: Get mechanism effectiveness per user segment
// =========================================================================

// Find which mechanisms work best for users with high openness
MATCH (u:User)-[:HAS_TRAIT]->(t:Trait {name: 'openness'})
WHERE t.score > 0.7
MATCH (u)-[:MADE_DECISION]->(d:Decision)-[:USED_MECHANISM]->(m:Mechanism)
WHERE d.outcome_type = 'conversion'
WITH m.name as mechanism, 
     AVG(d.outcome_value) as avg_conversion,
     COUNT(d) as sample_size
WHERE sample_size >= 10
RETURN mechanism, 
       avg_conversion,
       sample_size
ORDER BY avg_conversion DESC;


// =========================================================================
// QUERY 3: Atom credit distribution over time
// =========================================================================

// Track which atoms are receiving the most credit over past week
MATCH (a:Attribution)<-[:HAS_ATTRIBUTION]-(d:Decision)
WHERE d.timestamp > datetime() - duration('P7D')
UNWIND keys(a.atom_credits) as atom_name
WITH atom_name, 
     a.atom_credits[atom_name] as credit,
     date(d.timestamp) as day
WITH atom_name, 
     day,
     AVG(credit) as avg_credit,
     COUNT(*) as decisions
RETURN atom_name, 
       day,
       avg_credit,
       decisions
ORDER BY day, avg_credit DESC;


// =========================================================================
// QUERY 4: Find discriminative atoms
// =========================================================================

// Find atoms that are highly predictive of outcome
MATCH (a:Attribution)<-[:HAS_ATTRIBUTION]-(d:Decision)
WHERE d.timestamp > datetime() - duration('P30D')
WITH d.outcome_value > 0.5 as success,
     a.atom_credits as credits
UNWIND keys(credits) as atom_name
WITH atom_name,
     success,
     AVG(credits[atom_name]) as avg_credit
WITH atom_name,
     COLLECT({success: success, credit: avg_credit}) as stats
WITH atom_name,
     [s IN stats WHERE s.success = true | s.credit][0] as success_credit,
     [s IN stats WHERE s.success = false | s.credit][0] as failure_credit
WHERE success_credit IS NOT NULL AND failure_credit IS NOT NULL
RETURN atom_name,
       success_credit,
       failure_credit,
       success_credit - failure_credit as discriminative_power
ORDER BY discriminative_power DESC;


// =========================================================================
// QUERY 5: Cross-component learning insights
// =========================================================================

// Track how bandit and Claude credits correlate
MATCH (a:Attribution)<-[:HAS_ATTRIBUTION]-(d:Decision)
WHERE d.timestamp > datetime() - duration('P7D')
WITH a.bandit_credit as bandit,
     a.meta_learner_credit as meta,
     d.outcome_value as outcome
WITH 
     CASE 
       WHEN bandit > meta THEN 'bandit_dominant'
       WHEN meta > bandit THEN 'meta_dominant'
       ELSE 'balanced'
     END as dominance,
     outcome
RETURN dominance,
       AVG(outcome) as avg_outcome,
       COUNT(*) as count
ORDER BY avg_outcome DESC;


// =========================================================================
// QUERY 6: User profile validation rate
// =========================================================================

// Track how often personality predictions are validated by outcomes
MATCH (u:User)-[:HAS_TRAIT]->(t:Trait)
MATCH (u)-[:MADE_DECISION]->(d:Decision)-[:USED_MECHANISM]->(m:Mechanism)
WHERE d.timestamp > datetime() - duration('P30D')
WITH u.user_id as user_id,
     t.name as trait_name,
     t.score as predicted_score,
     m.name as mechanism,
     d.outcome_value as outcome,
     d.timestamp as decision_time
WITH user_id,
     trait_name,
     predicted_score,
     mechanism,
     AVG(outcome) as avg_outcome,
     COUNT(*) as decisions
WHERE decisions >= 5
RETURN user_id,
       trait_name,
       predicted_score,
       mechanism,
       avg_outcome,
       decisions,
       CASE 
         WHEN ABS(predicted_score - avg_outcome) < 0.2 THEN 'validated'
         ELSE 'needs_update'
       END as validation_status
ORDER BY validation_status, decisions DESC;
```

---

# SECTION I: LANGGRAPH WORKFLOWS

## Gradient Bridge Workflow Node

```python
# =============================================================================
# ADAM Enhancement #06: LangGraph Integration
# Location: adam/gradient_bridge/workflows/nodes.py
# =============================================================================

"""
LangGraph workflow nodes for Gradient Bridge integration.
"""

from __future__ import annotations
from typing import Dict, Any, Optional, TypedDict, Annotated
import operator
import logging

from langgraph.graph import StateGraph, END
from pydantic import BaseModel, Field

from adam.gradient_bridge.core.orchestrator import GradientBridgeOrchestrator, GradientBridgeConfig
from adam.gradient_bridge.enums import OutcomeType, ExecutionPath
from adam.gradient_bridge.models.priors import EmpiricalPriors

logger = logging.getLogger(__name__)


# =============================================================================
# STATE DEFINITION
# =============================================================================

class GradientBridgeState(TypedDict, total=False):
    """State for Gradient Bridge workflow."""
    # Input
    request_id: str
    decision_id: str
    user_id: str
    ad_id: str
    
    # Atom outputs (accumulated)
    atom_outputs: Annotated[Dict[str, Any], operator.or_]
    
    # Decision context
    bandit_arm_id: str
    bandit_uncertainty: float
    execution_path: str
    path_confidence: float
    graph_profile_completeness: float
    verification_confidence: Optional[float]
    
    # Outcome (set when known)
    outcome_type: Optional[str]
    outcome_value: Optional[float]
    
    # Priors for Claude
    empirical_priors: Optional[EmpiricalPriors]
    priors_prompt: Optional[str]
    
    # Attribution result
    attribution_result: Optional[Dict[str, Any]]
    
    # Trace
    trace_id: Optional[str]


# =============================================================================
# PRIOR INJECTION NODE
# =============================================================================

class PriorInjectionNode:
    """
    Injects empirical priors into workflow state for Claude consumption.
    
    This node runs BEFORE Claude atoms to provide historical context.
    """
    
    def __init__(
        self,
        cache_layer: Any,  # GradientBridgeCacheLayer
        prior_extractor: Any  # PriorExtractor
    ):
        self.cache = cache_layer
        self.extractor = prior_extractor
    
    async def __call__(self, state: GradientBridgeState) -> GradientBridgeState:
        """
        Extract and inject empirical priors.
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated state with priors
        """
        user_id = state.get("user_id")
        if not user_id:
            logger.warning("No user_id in state, skipping prior injection")
            return state
        
        # Try cache first
        priors = await self.cache.get_priors(user_id)
        
        if not priors:
            # Extract fresh priors
            priors = await self.extractor.extract(
                user_id=user_id,
                request_id=state.get("request_id", "")
            )
            
            # Cache for future requests
            if priors:
                await self.cache.set_priors(priors)
        
        if priors:
            return {
                **state,
                "empirical_priors": priors,
                "priors_prompt": priors.to_prompt_context()
            }
        
        return state


# =============================================================================
# OUTCOME PROCESSING NODE
# =============================================================================

class OutcomeProcessingNode:
    """
    Processes outcomes through the Gradient Bridge.
    
    This node runs AFTER an outcome is received to propagate
    learning signals to all components.
    """
    
    def __init__(self, gradient_bridge: GradientBridgeOrchestrator):
        self.bridge = gradient_bridge
    
    async def __call__(self, state: GradientBridgeState) -> GradientBridgeState:
        """
        Process outcome through Gradient Bridge.
        
        Args:
            state: Current workflow state with outcome
            
        Returns:
            Updated state with attribution
        """
        # Check if we have an outcome to process
        outcome_type = state.get("outcome_type")
        outcome_value = state.get("outcome_value")
        
        if outcome_type is None or outcome_value is None:
            logger.debug("No outcome in state, skipping processing")
            return state
        
        # Process through Gradient Bridge
        result = await self.bridge.process_outcome(
            request_id=state.get("request_id", ""),
            decision_id=state.get("decision_id", ""),
            user_id=state.get("user_id", ""),
            outcome_type=OutcomeType(outcome_type),
            outcome_value=outcome_value,
            atom_outputs=state.get("atom_outputs", {}),
            bandit_arm_id=state.get("bandit_arm_id", ""),
            bandit_uncertainty=state.get("bandit_uncertainty", 0.5),
            graph_profile_completeness=state.get("graph_profile_completeness", 0.0),
            execution_path=ExecutionPath(state.get("execution_path", "reasoning")),
            path_confidence=state.get("path_confidence", 0.5),
            ad_id=state.get("ad_id", ""),
            verification_confidence=state.get("verification_confidence"),
            trace_id=state.get("trace_id")
        )
        
        return {
            **state,
            "attribution_result": result
        }


# =============================================================================
# DECISION TRACE STORAGE NODE
# =============================================================================

class DecisionTraceNode:
    """
    Stores decision trace for later outcome processing.
    
    This node runs AFTER a decision is made but BEFORE the outcome
    to capture the full context for attribution.
    """
    
    def __init__(self, cache_layer: Any):
        self.cache = cache_layer
    
    async def __call__(self, state: GradientBridgeState) -> GradientBridgeState:
        """
        Store decision trace in cache.
        
        Args:
            state: Current workflow state
            
        Returns:
            Unchanged state (side effect only)
        """
        decision_id = state.get("decision_id")
        if not decision_id:
            return state
        
        trace = {
            "request_id": state.get("request_id"),
            "user_id": state.get("user_id"),
            "atom_outputs": state.get("atom_outputs", {}),
            "bandit_arm_id": state.get("bandit_arm_id"),
            "bandit_uncertainty": state.get("bandit_uncertainty"),
            "execution_path": state.get("execution_path"),
            "path_confidence": state.get("path_confidence"),
            "graph_profile_completeness": state.get("graph_profile_completeness"),
            "verification_confidence": state.get("verification_confidence")
        }
        
        await self.cache.store_decision_trace(decision_id, trace)
        
        return state


# =============================================================================
# WORKFLOW BUILDER
# =============================================================================

def build_gradient_bridge_subgraph(
    prior_injection_node: PriorInjectionNode,
    decision_trace_node: DecisionTraceNode,
    outcome_processing_node: OutcomeProcessingNode
) -> StateGraph:
    """
    Build Gradient Bridge subgraph for integration into main workflow.
    
    This subgraph can be composed into the main ADAM workflow.
    
    Args:
        prior_injection_node: Node for injecting priors
        decision_trace_node: Node for storing traces
        outcome_processing_node: Node for processing outcomes
        
    Returns:
        StateGraph for Gradient Bridge operations
    """
    workflow = StateGraph(GradientBridgeState)
    
    # Add nodes
    workflow.add_node("inject_priors", prior_injection_node)
    workflow.add_node("store_trace", decision_trace_node)
    workflow.add_node("process_outcome", outcome_processing_node)
    
    # Define edges
    workflow.set_entry_point("inject_priors")
    workflow.add_edge("inject_priors", "store_trace")
    
    # Conditional edge based on whether outcome exists
    def has_outcome(state: GradientBridgeState) -> str:
        if state.get("outcome_type") and state.get("outcome_value") is not None:
            return "process_outcome"
        return END
    
    workflow.add_conditional_edges(
        "store_trace",
        has_outcome,
        {
            "process_outcome": "process_outcome",
            END: END
        }
    )
    
    workflow.add_edge("process_outcome", END)
    
    return workflow.compile()
```

---

# SECTION J: FASTAPI ENDPOINTS

## Attribution API

```python
# =============================================================================
# ADAM Enhancement #06: FastAPI Endpoints
# Location: adam/gradient_bridge/api/routes.py
# =============================================================================

"""
FastAPI endpoints for Gradient Bridge.
"""

from __future__ import annotations
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from pydantic import BaseModel, Field

from adam.gradient_bridge.core.orchestrator import GradientBridgeOrchestrator
from adam.gradient_bridge.cache.layer import GradientBridgeCacheLayer
from adam.gradient_bridge.enums import OutcomeType, ExecutionPath, ComponentType
from adam.gradient_bridge.models.credit import AttributionResult
from adam.gradient_bridge.models.priors import EmpiricalPriors

router = APIRouter(prefix="/v1/gradient-bridge", tags=["gradient-bridge"])


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class ProcessOutcomeRequest(BaseModel):
    """Request to process an outcome through Gradient Bridge."""
    request_id: str = Field(default_factory=lambda: f"req_{uuid4().hex[:12]}")
    decision_id: str
    user_id: str
    ad_id: str
    outcome_type: OutcomeType
    outcome_value: float = Field(ge=0.0, le=1.0)
    
    # Decision context (can be fetched from trace if not provided)
    bandit_arm_id: Optional[str] = None
    bandit_uncertainty: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    execution_path: Optional[ExecutionPath] = None
    path_confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    graph_profile_completeness: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    verification_confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    
    trace_id: Optional[str] = None


class ProcessOutcomeResponse(BaseModel):
    """Response from outcome processing."""
    attribution_id: str
    request_id: str
    decision_id: str
    outcome_type: OutcomeType
    outcome_value: float
    
    # Attribution summary
    dominant_contributor: str
    dominant_credit: float
    attribution_entropy: float
    
    # Processing metadata
    signals_created: int
    processing_time_ms: float
    
    # Feature coverage (if extracted)
    feature_coverage: Optional[float] = None


class PriorExtractionResponse(BaseModel):
    """Response from prior extraction."""
    prior_id: str
    user_id: str
    top_arm: Optional[str]
    top_arm_confidence: float
    recommended_mechanisms: List[str]
    avoid_mechanisms: List[str]
    exploration_budget: float
    extraction_time_ms: float
    cache_hit: bool
    prompt_context: str


class SignalHistoryResponse(BaseModel):
    """Response with signal history."""
    signals: List[Dict[str, Any]]
    total_count: int
    component_filter: Optional[str]


# =============================================================================
# DEPENDENCY INJECTION
# =============================================================================

async def get_gradient_bridge() -> GradientBridgeOrchestrator:
    """Dependency to get Gradient Bridge instance."""
    from adam.gradient_bridge.dependencies import gradient_bridge_instance
    return gradient_bridge_instance


async def get_cache_layer() -> GradientBridgeCacheLayer:
    """Dependency to get cache layer instance."""
    from adam.gradient_bridge.dependencies import cache_layer_instance
    return cache_layer_instance


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.post("/process-outcome", response_model=ProcessOutcomeResponse)
async def process_outcome(
    request: ProcessOutcomeRequest,
    background_tasks: BackgroundTasks,
    bridge: GradientBridgeOrchestrator = Depends(get_gradient_bridge),
    cache: GradientBridgeCacheLayer = Depends(get_cache_layer)
) -> ProcessOutcomeResponse:
    """
    Process an outcome through the Gradient Bridge.
    
    This triggers:
    1. Multi-level credit attribution
    2. Feature extraction for bandit learning
    3. Signal propagation to all components
    4. Event emission to Kafka
    5. Cache updates
    """
    # If context not provided, try to fetch from decision trace
    if request.bandit_arm_id is None:
        trace = await cache.get_decision_trace(request.decision_id)
        if trace:
            request.bandit_arm_id = trace.get("bandit_arm_id", "")
            request.bandit_uncertainty = trace.get("bandit_uncertainty", 0.5)
            request.execution_path = ExecutionPath(trace.get("execution_path", "reasoning"))
            request.path_confidence = trace.get("path_confidence", 0.5)
            request.graph_profile_completeness = trace.get("graph_profile_completeness", 0.0)
            request.verification_confidence = trace.get("verification_confidence")
    
    # Default values if still not set
    request.bandit_arm_id = request.bandit_arm_id or ""
    request.bandit_uncertainty = request.bandit_uncertainty or 0.5
    request.execution_path = request.execution_path or ExecutionPath.REASONING
    request.path_confidence = request.path_confidence or 0.5
    request.graph_profile_completeness = request.graph_profile_completeness or 0.0
    
    # Process outcome
    result = await bridge.process_outcome(
        request_id=request.request_id,
        decision_id=request.decision_id,
        user_id=request.user_id,
        outcome_type=request.outcome_type,
        outcome_value=request.outcome_value,
        atom_outputs={},  # Would come from trace in production
        bandit_arm_id=request.bandit_arm_id,
        bandit_uncertainty=request.bandit_uncertainty,
        graph_profile_completeness=request.graph_profile_completeness,
        execution_path=request.execution_path,
        path_confidence=request.path_confidence,
        ad_id=request.ad_id,
        verification_confidence=request.verification_confidence,
        trace_id=request.trace_id
    )
    
    attribution: AttributionResult = result["attribution"]
    
    return ProcessOutcomeResponse(
        attribution_id=attribution.attribution_id,
        request_id=attribution.request_id,
        decision_id=attribution.decision_id,
        outcome_type=attribution.outcome_type,
        outcome_value=attribution.outcome_value,
        dominant_contributor=attribution.dominant_contributor,
        dominant_credit=attribution.dominant_credit,
        attribution_entropy=attribution.attribution_entropy,
        signals_created=result["signals_created"],
        processing_time_ms=result["processing_time_ms"],
        feature_coverage=result["features"].feature_coverage if result.get("features") else None
    )


@router.get("/attribution/{attribution_id}")
async def get_attribution(
    attribution_id: str,
    cache: GradientBridgeCacheLayer = Depends(get_cache_layer)
) -> Dict[str, Any]:
    """Retrieve a specific attribution by ID."""
    attribution = await cache.get_attribution(attribution_id)
    
    if not attribution:
        raise HTTPException(status_code=404, detail="Attribution not found")
    
    return attribution.model_dump()


@router.post("/priors/extract", response_model=PriorExtractionResponse)
async def extract_priors(
    user_id: str,
    ad_category: Optional[str] = None,
    cache: GradientBridgeCacheLayer = Depends(get_cache_layer)
) -> PriorExtractionResponse:
    """
    Extract empirical priors for a user.
    
    Returns historical performance data that can be injected
    into Claude's context for data-grounded predictions.
    """
    priors = await cache.get_priors(user_id, ad_category)
    cache_hit = priors is not None
    
    if not priors:
        priors = EmpiricalPriors(
            request_id=f"req_{uuid4().hex[:12]}",
            user_id=user_id,
            exploration_budget=0.1
        )
        await cache.set_priors(priors, ad_category)
    
    return PriorExtractionResponse(
        prior_id=priors.prior_id,
        user_id=priors.user_id,
        top_arm=priors.top_arm,
        top_arm_confidence=priors.top_arm_confidence,
        recommended_mechanisms=priors.recommended_mechanisms,
        avoid_mechanisms=priors.avoid_mechanisms,
        exploration_budget=priors.exploration_budget,
        extraction_time_ms=0.0,
        cache_hit=cache_hit,
        prompt_context=priors.to_prompt_context()
    )


@router.get("/signals/history", response_model=SignalHistoryResponse)
async def get_signal_history(
    limit: int = Query(default=100, ge=1, le=1000),
    component: Optional[ComponentType] = None,
    bridge: GradientBridgeOrchestrator = Depends(get_gradient_bridge)
) -> SignalHistoryResponse:
    """Get recent learning signal history for debugging."""
    signals = bridge.get_signal_history(limit=limit, component_filter=component)
    
    return SignalHistoryResponse(
        signals=[s.model_dump() for s in signals],
        total_count=len(signals),
        component_filter=component.value if component else None
    )


@router.get("/health")
async def health_check(
    cache: GradientBridgeCacheLayer = Depends(get_cache_layer)
) -> Dict[str, Any]:
    """Health check endpoint with cache stats."""
    cache_stats = cache.get_stats()
    
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "cache": cache_stats
    }
```

---

# SECTION K: PROMETHEUS METRICS

## Attribution Metrics

```python
# =============================================================================
# ADAM Enhancement #06: Prometheus Metrics
# Location: adam/gradient_bridge/metrics/prometheus.py
# =============================================================================

"""
Prometheus metrics for Gradient Bridge observability.
25+ metrics covering all aspects of cross-component learning.
"""

from __future__ import annotations
from typing import Dict, List, Optional, Any, TYPE_CHECKING

from prometheus_client import Counter, Histogram, Gauge, Info

if TYPE_CHECKING:
    from adam.gradient_bridge.models.credit import AttributionResult
    from adam.gradient_bridge.enums import OutcomeType

# =============================================================================
# ATTRIBUTION METRICS
# =============================================================================

ATTRIBUTION_COMPUTATIONS = Counter(
    "gradient_bridge_attribution_computations_total",
    "Total attribution computations",
    ["outcome_type", "method"]
)

ATTRIBUTION_LATENCY = Histogram(
    "gradient_bridge_attribution_latency_seconds",
    "Attribution computation latency",
    ["method"],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0]
)

ATTRIBUTION_ENTROPY = Histogram(
    "gradient_bridge_attribution_entropy",
    "Distribution of attribution entropy (credit spread)",
    buckets=[0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0]
)

DOMINANT_CONTRIBUTOR = Counter(
    "gradient_bridge_dominant_contributor_total",
    "Count of which component was dominant contributor",
    ["component"]
)

CREDIT_DISTRIBUTION = Histogram(
    "gradient_bridge_credit_distribution",
    "Credit score distribution by component",
    ["component"],
    buckets=[0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
)

LLM_ATTRIBUTION_CALLS = Counter(
    "gradient_bridge_llm_attribution_calls_total",
    "LLM-guided attribution calls",
    ["status"]  # success, failure, skipped
)

LLM_ATTRIBUTION_LATENCY = Histogram(
    "gradient_bridge_llm_attribution_latency_seconds",
    "LLM attribution call latency",
    buckets=[0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0]
)

# =============================================================================
# SIGNAL PROPAGATION METRICS
# =============================================================================

SIGNAL_PROPAGATION = Counter(
    "gradient_bridge_signal_propagation_total",
    "Signal propagation attempts",
    ["target_component", "status"]  # success, failure
)

PROPAGATION_LATENCY = Histogram(
    "gradient_bridge_propagation_latency_seconds",
    "Signal propagation latency by component",
    ["component"],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5]
)

PROPAGATION_FAILURES = Counter(
    "gradient_bridge_propagation_failures_total",
    "Signal propagation failures by error type",
    ["component", "error_type"]
)

BATCH_SIZE = Histogram(
    "gradient_bridge_signal_batch_size",
    "Number of signals per batch",
    buckets=[1, 2, 3, 4, 5, 10, 15, 20]
)

# =============================================================================
# OUTCOME PROCESSING METRICS
# =============================================================================

OUTCOMES_PROCESSED = Counter(
    "gradient_bridge_outcomes_processed_total",
    "Total outcomes processed",
    ["outcome_type"]
)

OUTCOME_VALUES = Histogram(
    "gradient_bridge_outcome_values",
    "Distribution of outcome values",
    ["outcome_type"],
    buckets=[0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
)

PROCESSING_LATENCY = Histogram(
    "gradient_bridge_processing_latency_seconds",
    "End-to-end processing latency",
    ["outcome_type"],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0]
)

DECISION_TRACE_RETRIEVALS = Counter(
    "gradient_bridge_decision_trace_retrievals_total",
    "Decision trace retrieval attempts",
    ["source", "status"]  # cache/db, hit/miss
)

# =============================================================================
# FEATURE EXTRACTION METRICS
# =============================================================================

FEATURE_EXTRACTIONS = Counter(
    "gradient_bridge_feature_extractions_total",
    "Total feature extraction operations"
)

FEATURE_EXTRACTION_LATENCY = Histogram(
    "gradient_bridge_feature_extraction_latency_seconds",
    "Feature extraction latency",
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1]
)

FEATURE_DIMENSION = Gauge(
    "gradient_bridge_feature_dimension",
    "Current feature vector dimension"
)

MISSING_ATOMS = Counter(
    "gradient_bridge_missing_atoms_total",
    "Count of missing atoms during extraction",
    ["atom_name"]
)

FEATURE_COVERAGE = Histogram(
    "gradient_bridge_feature_coverage",
    "Feature coverage ratio (non-default values)",
    buckets=[0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
)

# =============================================================================
# CACHE METRICS
# =============================================================================

CACHE_OPERATIONS = Counter(
    "gradient_bridge_cache_operations_total",
    "Cache operation counts",
    ["operation", "cache_type", "status"]  # get/set/delete, attribution/priors/trace, hit/miss
)

CACHE_HIT_RATE = Gauge(
    "gradient_bridge_cache_hit_rate",
    "Cache hit rate by type",
    ["cache_type"]
)

CACHE_SIZE = Gauge(
    "gradient_bridge_cache_size",
    "Cache size by type",
    ["cache_type", "level"]  # l1/l2
)

# =============================================================================
# LEARNING QUALITY METRICS
# =============================================================================

MECHANISM_EFFECTIVENESS = Gauge(
    "gradient_bridge_mechanism_effectiveness",
    "Mechanism effectiveness score (rolling average)",
    ["mechanism"]
)

ATOM_CREDIT_AVG = Gauge(
    "gradient_bridge_atom_credit_avg",
    "Average credit per atom (rolling window)",
    ["atom"]
)

CONVERGENCE_RATE = Gauge(
    "gradient_bridge_convergence_rate",
    "Learning convergence rate estimate",
    ["modality"]  # bandit, graph, meta_learner
)

# =============================================================================
# KAFKA METRICS
# =============================================================================

KAFKA_EVENTS_EMITTED = Counter(
    "gradient_bridge_kafka_events_emitted_total",
    "Kafka events emitted",
    ["topic", "status"]  # success, failure
)

KAFKA_EMIT_LATENCY = Histogram(
    "gradient_bridge_kafka_emit_latency_seconds",
    "Kafka event emission latency",
    ["topic"],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1]
)

KAFKA_CONSUMER_LAG = Gauge(
    "gradient_bridge_kafka_consumer_lag",
    "Kafka consumer lag",
    ["topic", "partition"]
)


# =============================================================================
# METRICS COLLECTOR CLASS
# =============================================================================

class GradientBridgeMetrics:
    """
    Centralized metrics collector for Gradient Bridge.
    
    Provides convenient methods for recording metrics throughout
    the processing pipeline.
    """
    
    def __init__(self):
        self._computation_count = 0
        self._cache_hits = 0
        self._cache_misses = 0
        
        # Initialize feature dimension
        FEATURE_DIMENSION.set(43)
    
    def record_attribution(self, result: "AttributionResult") -> None:
        """Record metrics for an attribution computation."""
        # Attribution computation
        for method in result.attribution_methods_used:
            ATTRIBUTION_COMPUTATIONS.labels(
                outcome_type=result.outcome_type.value,
                method=method.value
            ).inc()
        
        # Latency
        method_name = "ensemble" if len(result.attribution_methods_used) > 1 else result.attribution_methods_used[0].value
        ATTRIBUTION_LATENCY.labels(method=method_name).observe(
            result.computation_time_ms / 1000
        )
        
        # Entropy
        ATTRIBUTION_ENTROPY.observe(result.attribution_entropy)
        
        # Dominant contributor
        component = result.dominant_contributor.split(":")[0]
        DOMINANT_CONTRIBUTOR.labels(component=component).inc()
        
        # Credit distribution
        CREDIT_DISTRIBUTION.labels(component="bandit").observe(
            result.bandit_credit.credit_score
        )
        CREDIT_DISTRIBUTION.labels(component="graph").observe(
            result.graph_credit.credit_score
        )
        CREDIT_DISTRIBUTION.labels(component="meta_learner").observe(
            result.meta_learner_credit.credit_score
        )
        
        for atom_name, atom_credit in result.atom_credits.items():
            CREDIT_DISTRIBUTION.labels(component=f"atom_{atom_name}").observe(
                atom_credit.credit_score
            )
        
        self._computation_count += 1
    
    def record_signal_propagation(
        self,
        component: str,
        success: bool,
        latency_ms: float
    ) -> None:
        """Record signal propagation metrics."""
        status = "success" if success else "failure"
        SIGNAL_PROPAGATION.labels(
            target_component=component,
            status=status
        ).inc()
        
        if latency_ms:
            PROPAGATION_LATENCY.labels(component=component).observe(
                latency_ms / 1000
            )
    
    def record_outcome_processing(
        self,
        outcome_type: str,
        outcome_value: float,
        processing_time_ms: float
    ) -> None:
        """Record outcome processing metrics."""
        OUTCOMES_PROCESSED.labels(outcome_type=outcome_type).inc()
        OUTCOME_VALUES.labels(outcome_type=outcome_type).observe(outcome_value)
        PROCESSING_LATENCY.labels(outcome_type=outcome_type).observe(
            processing_time_ms / 1000
        )
    
    def record_feature_extraction(
        self,
        extraction_time_ms: float,
        coverage: float,
        missing_atoms: List[str]
    ) -> None:
        """Record feature extraction metrics."""
        FEATURE_EXTRACTIONS.inc()
        FEATURE_EXTRACTION_LATENCY.observe(extraction_time_ms / 1000)
        FEATURE_COVERAGE.observe(coverage)
        
        for atom in missing_atoms:
            MISSING_ATOMS.labels(atom_name=atom).inc()
    
    def record_cache_operation(
        self,
        operation: str,
        cache_type: str,
        hit: bool
    ) -> None:
        """Record cache operation metrics."""
        status = "hit" if hit else "miss"
        CACHE_OPERATIONS.labels(
            operation=operation,
            cache_type=cache_type,
            status=status
        ).inc()
        
        if operation == "get":
            if hit:
                self._cache_hits += 1
            else:
                self._cache_misses += 1
            
            total = self._cache_hits + self._cache_misses
            if total > 0:
                CACHE_HIT_RATE.labels(cache_type=cache_type).set(
                    self._cache_hits / total
                )
    
    def record_kafka_emit(
        self,
        topic: str,
        success: bool,
        latency_ms: float
    ) -> None:
        """Record Kafka emission metrics."""
        status = "success" if success else "failure"
        KAFKA_EVENTS_EMITTED.labels(topic=topic, status=status).inc()
        
        if latency_ms > 0:
            KAFKA_EMIT_LATENCY.labels(topic=topic).observe(latency_ms / 1000)
    
    def update_mechanism_effectiveness(
        self,
        mechanism: str,
        effectiveness: float
    ) -> None:
        """Update mechanism effectiveness gauge."""
        MECHANISM_EFFECTIVENESS.labels(mechanism=mechanism).set(effectiveness)
    
    def update_atom_credit_avg(
        self,
        atom: str,
        avg_credit: float
    ) -> None:
        """Update atom credit average gauge."""
        ATOM_CREDIT_AVG.labels(atom=atom).set(avg_credit)
```

---

# SECTION L: TESTING & OPERATIONS

## Unit Tests

```python
# =============================================================================
# ADAM Enhancement #06: Unit Tests
# Location: tests/gradient_bridge/test_attribution.py
# =============================================================================

"""
Comprehensive unit tests for Gradient Bridge attribution engine.
Target: 90%+ coverage.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
import math

from adam.gradient_bridge.enums import (
    ComponentType, OutcomeType, AttributionMethod, ExecutionPath
)
from adam.gradient_bridge.models.credit import (
    CreditAssignment, AtomCreditAssignment, AttributionResult, AttributionConfig
)
from adam.gradient_bridge.models.signals import (
    BanditUpdateSignal, GraphUpdateSignal, MetaLearnerUpdateSignal
)
from adam.gradient_bridge.models.features import EnrichedBanditContext
from adam.gradient_bridge.models.priors import (
    EmpiricalPriors, ArmPerformanceStats, UserHistory
)
from adam.gradient_bridge.attribution.engine import CreditAttributionEngine
from adam.gradient_bridge.features.extractor import FeatureExtractor


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def attribution_config():
    """Default attribution configuration."""
    return AttributionConfig(
        method_weights={
            AttributionMethod.CONFIDENCE_WEIGHTED: 0.5,
            AttributionMethod.LLM_GUIDED: 0.3,
            AttributionMethod.COUNTERFACTUAL: 0.2
        },
        use_llm_attribution=False,  # Disable for unit tests
        cache_attribution_ttl_seconds=300
    )


@pytest.fixture
def mock_atom_outputs():
    """Mock atom outputs for testing."""
    class MockAtomOutput:
        def __init__(self, confidence: float, data: dict):
            self.confidence = confidence
            self._data = data
        
        def model_dump(self):
            return {**self._data, "confidence": self.confidence}
    
    return {
        "user_state": MockAtomOutput(0.8, {"arousal": 0.6, "cognitive_load": 0.4}),
        "regulatory_focus": MockAtomOutput(0.7, {"promotion_score": 0.7, "prevention_score": 0.3}),
        "personality": MockAtomOutput(0.9, {
            "traits": {"openness": 0.8, "conscientiousness": 0.6}
        }),
        "mechanism": MockAtomOutput(0.85, {
            "primary_mechanism": "social_proof",
            "activation_strength": 0.75
        })
    }


@pytest.fixture
def attribution_engine(attribution_config):
    """Attribution engine instance."""
    return CreditAttributionEngine(config=attribution_config)


@pytest.fixture
def feature_extractor():
    """Feature extractor instance."""
    return FeatureExtractor()


# =============================================================================
# CREDIT ASSIGNMENT MODEL TESTS
# =============================================================================

class TestCreditAssignmentModels:
    """Tests for credit assignment Pydantic models."""
    
    def test_credit_assignment_validation(self):
        """Test credit score bounds validation."""
        credit = CreditAssignment(
            component_type=ComponentType.BANDIT,
            component_id="test",
            credit_score=0.5,
            confidence=0.8
        )
        assert credit.credit_score == 0.5
        assert credit.confidence == 0.8
    
    def test_credit_assignment_invalid_score(self):
        """Test rejection of invalid credit scores."""
        with pytest.raises(ValueError):
            CreditAssignment(
                component_type=ComponentType.BANDIT,
                component_id="test",
                credit_score=1.5,  # Invalid: > 1.0
                confidence=0.8
            )
    
    def test_atom_credit_assignment(self):
        """Test atom-specific credit assignment."""
        atom_credit = AtomCreditAssignment(
            component_type=ComponentType.ATOM_PERSONALITY,
            component_id="personality",
            atom_name="personality",
            credit_score=0.3,
            confidence=0.85,
            atom_confidence=0.85,
            execution_order=2
        )
        assert atom_credit.atom_name == "personality"
        assert atom_credit.execution_order == 2
    
    def test_attribution_result_computes_aggregates(self):
        """Test automatic computation of entropy and dominant contributor."""
        bandit_credit = CreditAssignment(
            component_type=ComponentType.BANDIT,
            component_id="bandit",
            credit_score=0.4,
            confidence=0.7
        )
        graph_credit = CreditAssignment(
            component_type=ComponentType.GRAPH,
            component_id="graph",
            credit_score=0.3,
            confidence=0.6
        )
        meta_credit = CreditAssignment(
            component_type=ComponentType.META_LEARNER,
            component_id="meta",
            credit_score=0.3,
            confidence=0.5
        )
        
        result = AttributionResult(
            request_id="req_123",
            decision_id="dec_123",
            user_id="user_123",
            outcome_type=OutcomeType.CONVERSION,
            outcome_value=1.0,
            atom_credits={},
            bandit_credit=bandit_credit,
            graph_credit=graph_credit,
            meta_learner_credit=meta_credit,
            attribution_methods_used=[AttributionMethod.CONFIDENCE_WEIGHTED],
            computation_time_ms=10.5
        )
        
        assert result.dominant_contributor == "bandit:bandit"
        assert result.dominant_credit == 0.4
        assert result.attribution_entropy > 0  # Should be non-zero for distributed credit


# =============================================================================
# ATTRIBUTION ENGINE TESTS
# =============================================================================

class TestCreditAttributionEngine:
    """Tests for the credit attribution engine."""
    
    @pytest.mark.asyncio
    async def test_compute_attribution_basic(
        self,
        attribution_engine,
        mock_atom_outputs
    ):
        """Test basic attribution computation."""
        result = await attribution_engine.compute_attribution(
            request_id="req_123",
            decision_id="dec_123",
            user_id="user_123",
            outcome_type=OutcomeType.CONVERSION,
            outcome_value=1.0,
            atom_outputs=mock_atom_outputs,
            bandit_arm_id="arm_001",
            bandit_uncertainty=0.3,
            graph_profile_completeness=0.7,
            execution_path=ExecutionPath.REASONING,
            path_confidence=0.8
        )
        
        assert result.attribution_id.startswith("attr_")
        assert result.outcome_type == OutcomeType.CONVERSION
        assert result.outcome_value == 1.0
        assert len(result.atom_credits) == 4
        assert AttributionMethod.CONFIDENCE_WEIGHTED in result.attribution_methods_used
    
    @pytest.mark.asyncio
    async def test_attribution_credits_normalize(
        self,
        attribution_engine,
        mock_atom_outputs
    ):
        """Test that credits normalize to approximately 1.0."""
        result = await attribution_engine.compute_attribution(
            request_id="req_123",
            decision_id="dec_123",
            user_id="user_123",
            outcome_type=OutcomeType.CLICK,
            outcome_value=0.5,
            atom_outputs=mock_atom_outputs,
            bandit_arm_id="arm_001",
            bandit_uncertainty=0.5,
            graph_profile_completeness=0.5,
            execution_path=ExecutionPath.FAST,
            path_confidence=0.9
        )
        
        total_credit = (
            sum(ac.credit_score for ac in result.atom_credits.values()) +
            result.bandit_credit.credit_score +
            result.graph_credit.credit_score +
            result.meta_learner_credit.credit_score
        )
        
        # Should normalize to approximately 1.0
        assert 0.95 <= total_credit <= 1.05
    
    @pytest.mark.asyncio
    async def test_high_confidence_atom_gets_more_credit(
        self,
        attribution_engine
    ):
        """Test that high confidence atoms get more credit on positive outcomes."""
        class MockAtom:
            def __init__(self, conf):
                self.confidence = conf
            def model_dump(self):
                return {"confidence": self.confidence}
        
        outputs = {
            "high_conf": MockAtom(0.95),
            "low_conf": MockAtom(0.2)
        }
        
        result = await attribution_engine.compute_attribution(
            request_id="req_123",
            decision_id="dec_123",
            user_id="user_123",
            outcome_type=OutcomeType.CONVERSION,
            outcome_value=1.0,
            atom_outputs=outputs,
            bandit_arm_id="arm_001",
            bandit_uncertainty=0.5,
            graph_profile_completeness=0.5,
            execution_path=ExecutionPath.REASONING,
            path_confidence=0.5
        )
        
        # High confidence atom should get more credit
        assert result.atom_credits["high_conf"].credit_score > result.atom_credits["low_conf"].credit_score


# =============================================================================
# FEATURE EXTRACTION TESTS
# =============================================================================

class TestFeatureExtractor:
    """Tests for the feature extraction system."""
    
    @pytest.mark.asyncio
    async def test_extract_features_basic(
        self,
        feature_extractor,
        mock_atom_outputs
    ):
        """Test basic feature extraction."""
        result = await feature_extractor.extract(
            request_id="req_123",
            user_id="user_123",
            atom_outputs=mock_atom_outputs,
            execution_path=ExecutionPath.REASONING
        )
        
        assert result.request_id == "req_123"
        assert result.enriched_context is not None
        assert len(result.atoms_available) == 4
        assert result.feature_coverage > 0
    
    @pytest.mark.asyncio
    async def test_feature_vector_dimension(
        self,
        feature_extractor,
        mock_atom_outputs
    ):
        """Test that feature vector has correct dimension."""
        result = await feature_extractor.extract(
            request_id="req_123",
            user_id="user_123",
            atom_outputs=mock_atom_outputs
        )
        
        vector = result.enriched_context.to_feature_vector()
        names = EnrichedBanditContext.feature_names()
        
        assert len(vector) == 43  # Expected dimension
        assert len(names) == 43
        assert len(vector) == len(names)
    
    @pytest.mark.asyncio
    async def test_missing_atoms_tracked(
        self,
        feature_extractor
    ):
        """Test that missing atoms are tracked."""
        # Only provide some atoms
        partial_outputs = {
            "user_state": MagicMock(confidence=0.8, model_dump=lambda: {"arousal": 0.5})
        }
        
        result = await feature_extractor.extract(
            request_id="req_123",
            user_id="user_123",
            atom_outputs=partial_outputs
        )
        
        assert "personality" in result.atoms_missing
        assert "mechanism" in result.atoms_missing


# =============================================================================
# SIGNAL PROPAGATION TESTS
# =============================================================================

class TestSignalModels:
    """Tests for learning signal models."""
    
    def test_bandit_update_signal(self):
        """Test bandit update signal creation."""
        signal = BanditUpdateSignal(
            source_component=ComponentType.GRADIENT_BRIDGE,
            arm_id="arm_001",
            reward=0.8,
            weighted_reward=0.6,
            credit_weight=0.75,
            feature_vector=[0.5] * 43,
            feature_names=EnrichedBanditContext.feature_names()
        )
        
        assert signal.target_component == ComponentType.BANDIT
        assert signal.arm_id == "arm_001"
        assert len(signal.feature_vector) == 43
    
    def test_graph_update_signal(self):
        """Test graph update signal creation."""
        signal = GraphUpdateSignal(
            source_component=ComponentType.GRADIENT_BRIDGE,
            decision_id="dec_123",
            user_id="user_123",
            ad_id="ad_001",
            outcome=0.9,
            dominant_contributor="bandit:thompson",
            attribution_entropy=1.5,
            primary_mechanism="social_proof",
            mechanism_activation_strength=0.8
        )
        
        assert signal.target_component == ComponentType.GRAPH
        assert signal.primary_mechanism == "social_proof"
    
    def test_signal_expiry(self):
        """Test signal expiry checking."""
        from datetime import timedelta
        
        # Non-expired signal
        signal = BanditUpdateSignal(
            source_component=ComponentType.GRADIENT_BRIDGE,
            arm_id="arm_001",
            reward=0.5,
            weighted_reward=0.5,
            credit_weight=1.0,
            expiry=datetime.now(timezone.utc) + timedelta(hours=1)
        )
        assert not signal.is_expired()
        
        # Expired signal
        expired_signal = BanditUpdateSignal(
            source_component=ComponentType.GRADIENT_BRIDGE,
            arm_id="arm_001",
            reward=0.5,
            weighted_reward=0.5,
            credit_weight=1.0,
            expiry=datetime.now(timezone.utc) - timedelta(hours=1)
        )
        assert expired_signal.is_expired()


# =============================================================================
# PRIOR MODEL TESTS
# =============================================================================

class TestPriorModels:
    """Tests for empirical prior models."""
    
    def test_arm_performance_stats(self):
        """Test arm performance statistics."""
        stats = ArmPerformanceStats(
            arm_id="arm_001",
            arm_name="Social Proof Banner",
            alpha=25.0,
            beta=75.0,
            total_pulls=100,
            total_conversions=24
        )
        
        assert stats.empirical_conversion_rate == 0.24
        assert 0.24 < stats.expected_value < 0.26  # Beta mean
        assert stats.uncertainty > 0
    
    def test_user_history_cold_start(self):
        """Test cold start detection."""
        cold_user = UserHistory(
            user_id="user_new",
            total_impressions=3
        )
        assert cold_user.is_cold_start
        
        warm_user = UserHistory(
            user_id="user_warm",
            total_impressions=100,
            total_conversions=10
        )
        assert not warm_user.is_cold_start
        assert warm_user.historical_conversion_rate == 0.1
    
    def test_priors_to_prompt_context(self):
        """Test conversion of priors to Claude prompt context."""
        priors = EmpiricalPriors(
            request_id="req_123",
            user_id="user_123",
            arm_stats=[
                ArmPerformanceStats(
                    arm_id="arm_001",
                    arm_name="Social Proof",
                    alpha=30.0,
                    beta=70.0,
                    total_pulls=100
                )
            ],
            recommended_mechanisms=["social_proof", "scarcity"],
            exploration_budget=0.1
        )
        
        prompt = priors.to_prompt_context()
        
        assert "<empirical_priors>" in prompt
        assert "Social Proof" in prompt
        assert "EXPLORATION BUDGET: 10%" in prompt
        assert "</empirical_priors>" in prompt


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestIntegration:
    """Integration tests for the complete pipeline."""
    
    @pytest.mark.asyncio
    async def test_full_processing_pipeline(
        self,
        attribution_engine,
        feature_extractor,
        mock_atom_outputs
    ):
        """Test the complete attribution + feature extraction pipeline."""
        # Step 1: Extract features
        features = await feature_extractor.extract(
            request_id="req_123",
            user_id="user_123",
            atom_outputs=mock_atom_outputs,
            execution_path=ExecutionPath.REASONING
        )
        
        # Step 2: Compute attribution
        attribution = await attribution_engine.compute_attribution(
            request_id="req_123",
            decision_id="dec_123",
            user_id="user_123",
            outcome_type=OutcomeType.CONVERSION,
            outcome_value=1.0,
            atom_outputs=mock_atom_outputs,
            bandit_arm_id="arm_001",
            bandit_uncertainty=0.3,
            graph_profile_completeness=features.enriched_context.graph_user_profile_completeness,
            execution_path=ExecutionPath.REASONING,
            path_confidence=0.8
        )
        
        # Validate pipeline output
        assert features.enriched_context.feature_dimension == 43
        assert attribution.attribution_id is not None
        assert attribution.dominant_credit > 0
        
        # Feature vector can be used for bandit update
        vector = features.enriched_context.to_feature_vector()
        assert len(vector) == 43
        assert all(0.0 <= v <= 1.0 for v in vector)
```

---

## Implementation Timeline

### 12-Week Phased Implementation Plan

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                        GRADIENT BRIDGE IMPLEMENTATION TIMELINE                          │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                         │
│  PHASE 1: FOUNDATION (Weeks 1-3)                                                        │
│  ═══════════════════════════════                                                        │
│                                                                                         │
│  Week 1: Core Data Models                                                               │
│  ├── Implement all Pydantic models (credit, signals, features, priors)                 │
│  ├── Set up enums and type definitions                                                 │
│  ├── Create validation tests                                                           │
│  └── Deliverable: Models package with 95%+ test coverage                               │
│                                                                                         │
│  Week 2: Attribution Engine                                                             │
│  ├── Implement confidence-weighted attribution                                          │
│  ├── Add counterfactual estimation                                                     │
│  ├── Create normalization logic                                                        │
│  └── Deliverable: AttributionEngine with unit tests                                    │
│                                                                                         │
│  Week 3: Feature Extraction                                                             │
│  ├── Implement FeatureExtractor class                                                  │
│  ├── Create atom-to-feature mappings                                                   │
│  ├── Build feature vector serialization                                                │
│  └── Deliverable: 43-dimension feature extraction working                              │
│                                                                                         │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                         │
│  PHASE 2: INTEGRATION (Weeks 4-6)                                                       │
│  ═══════════════════════════════                                                        │
│                                                                                         │
│  Week 4: Gradient Bridge Orchestrator                                                   │
│  ├── Implement GradientBridgeOrchestrator                                              │
│  ├── Add parallel signal propagation                                                   │
│  ├── Create component update routing                                                   │
│  └── Deliverable: Core orchestrator functioning                                        │
│                                                                                         │
│  Week 5: Event Bus Integration (#31)                                                    │
│  ├── Set up Kafka topics and schemas                                                   │
│  ├── Implement GradientBridgeEventEmitter                                              │
│  ├── Build OutcomeEventConsumer                                                        │
│  └── Deliverable: Kafka integration complete                                           │
│                                                                                         │
│  Week 6: Cache Integration (#31)                                                        │
│  ├── Implement GradientBridgeCacheLayer                                                │
│  ├── Set up L1/L2 hierarchy                                                            │
│  ├── Add invalidation triggers                                                         │
│  └── Deliverable: Multi-level caching operational                                      │
│                                                                                         │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                         │
│  PHASE 3: PERSISTENCE (Weeks 7-8)                                                       │
│  ═══════════════════════════════                                                        │
│                                                                                         │
│  Week 7: Neo4j Schema & Queries                                                         │
│  ├── Deploy constraints and indexes                                                    │
│  ├── Implement analytics queries                                                       │
│  ├── Create decision/attribution storage                                               │
│  └── Deliverable: Graph persistence working                                            │
│                                                                                         │
│  Week 8: Prior Extraction Pipeline                                                      │
│  ├── Implement PriorExtractor from Neo4j                                               │
│  ├── Build prompt context generation                                                   │
│  ├── Integrate with cache layer                                                        │
│  └── Deliverable: Priors flowing to Claude                                             │
│                                                                                         │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                         │
│  PHASE 4: WORKFLOW (Weeks 9-10)                                                         │
│  ═══════════════════════════════                                                        │
│                                                                                         │
│  Week 9: LangGraph Integration                                                          │
│  ├── Implement PriorInjectionNode                                                      │
│  ├── Build DecisionTraceNode                                                           │
│  ├── Create OutcomeProcessingNode                                                      │
│  └── Deliverable: LangGraph subgraph compiled                                          │
│                                                                                         │
│  Week 10: FastAPI Endpoints                                                             │
│  ├── Deploy all REST endpoints                                                         │
│  ├── Add request validation                                                            │
│  ├── Implement health checks                                                           │
│  └── Deliverable: API fully operational                                                │
│                                                                                         │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                         │
│  PHASE 5: OBSERVABILITY (Weeks 11-12)                                                   │
│  ═══════════════════════════════════                                                    │
│                                                                                         │
│  Week 11: Prometheus Metrics                                                            │
│  ├── Deploy all 25+ metrics                                                            │
│  ├── Create Grafana dashboards                                                         │
│  ├── Set up alerting rules                                                             │
│  └── Deliverable: Full observability                                                   │
│                                                                                         │
│  Week 12: Performance & Testing                                                         │
│  ├── Load testing under production scenarios                                           │
│  ├── Optimize hot paths                                                                │
│  ├── Final integration testing                                                         │
│  └── Deliverable: Production-ready system                                              │
│                                                                                         │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Success Metrics

### Key Performance Indicators

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| **Attribution Latency** | p99 < 50ms | Prometheus histogram |
| **Processing Throughput** | >10K outcomes/sec | Counter + rate query |
| **Feature Extraction Time** | p50 < 5ms | Prometheus histogram |
| **Cache Hit Rate** | >90% for priors | Gauge tracking |
| **Signal Propagation Success** | >99.9% | Counter ratio |
| **Credit Normalization Accuracy** | Sum within 1% of 1.0 | Unit tests |

### Learning Quality Metrics

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| **Bandit Convergence Speed** | 3x faster with features | A/B test |
| **Claude Prediction Accuracy** | +15% with priors | Outcome tracking |
| **Graph Profile Validation Rate** | >70% traits validated | Neo4j analytics |
| **Cross-Component Correlation** | Measurable signal flow | Signal history |

### Operational Metrics

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| **System Availability** | 99.95% uptime | Health checks |
| **Kafka Event Delivery** | <100ms p99 latency | Kafka metrics |
| **Test Coverage** | >90% line coverage | pytest-cov |
| **API Response Time** | p99 < 100ms | FastAPI middleware |

---

## Appendix: Cross-Reference Index

### Integration Points with Other Enhancements

| Enhancement | Integration Type | Data Flow |
|-------------|------------------|-----------|
| **#01 Bidirectional Graph** | Signal sink | Attribution → Graph updates |
| **#02 Blackboard** | Decision trace storage | Trace → Cache → Attribution |
| **#03 Meta-Learning** | Signal sink | Credit → Thompson Sampling |
| **#04 Atom of Thought** | Signal source | Atom outputs → Features |
| **#05 Verification Layer** | Signal sink | Calibration updates |
| **#10 Journey Tracking** | Signal source/sink | Journey events ↔ Attribution |
| **#12 A/B Testing** | Signal source | Experiment outcomes |
| **#13 Cold Start** | Signal sink | New user priors |
| **#20 Drift Detection** | Monitoring | Attribution distribution shifts |
| **#26 Observability** | Metrics | Prometheus + traces |
| **#31 Caching/Event Bus** | Infrastructure | Redis + Kafka |

### File Location Summary

```
adam/
└── gradient_bridge/
    ├── __init__.py
    ├── enums.py                          # ComponentType, SignalType, etc.
    ├── models/
    │   ├── __init__.py
    │   ├── credit.py                     # CreditAssignment, AttributionResult
    │   ├── signals.py                    # LearningSignalEvent, BanditUpdateSignal
    │   ├── features.py                   # EnrichedBanditContext
    │   └── priors.py                     # EmpiricalPriors, ArmPerformanceStats
    ├── attribution/
    │   ├── __init__.py
    │   └── engine.py                     # CreditAttributionEngine
    ├── features/
    │   ├── __init__.py
    │   └── extractor.py                  # FeatureExtractor
    ├── core/
    │   ├── __init__.py
    │   └── orchestrator.py               # GradientBridgeOrchestrator
    ├── events/
    │   ├── __init__.py
    │   └── kafka.py                      # GradientBridgeEventEmitter, Consumer
    ├── cache/
    │   ├── __init__.py
    │   └── layer.py                      # GradientBridgeCacheLayer
    ├── workflows/
    │   ├── __init__.py
    │   └── nodes.py                      # LangGraph nodes
    ├── api/
    │   ├── __init__.py
    │   └── routes.py                     # FastAPI endpoints
    ├── metrics/
    │   ├── __init__.py
    │   └── prometheus.py                 # GradientBridgeMetrics
    ├── schema/
    │   └── neo4j_schema.cypher          # Neo4j constraints/indexes
    └── queries/
        └── analytics.cypher              # Neo4j analytics queries

tests/
└── gradient_bridge/
    ├── __init__.py
    ├── test_attribution.py               # Attribution engine tests
    ├── test_features.py                  # Feature extraction tests
    ├── test_signals.py                   # Signal propagation tests
    ├── test_priors.py                    # Prior model tests
    ├── test_cache.py                     # Cache layer tests
    ├── test_api.py                       # FastAPI endpoint tests
    └── test_integration.py               # End-to-end tests
```

---

**END OF ENHANCEMENT #06 SPECIFICATION**

*Document Version: 2.0 COMPLETE*  
*Total Size: ~135KB*  
*Last Updated: January 2026*
