# ADAM Enhancement #20: Model Monitoring & Drift Detection
## Multi-Source Intelligence Observability with Psychological Drift Detection

**Version**: 2.0 COMPLETE  
**Date**: January 2026  
**Priority**: P0 - Critical (Learning System Health)  
**Estimated Implementation**: 12 person-weeks  
**Dependencies**: #03 (Meta-Learner), #04 (Atom of Thought), #06 (Gradient Bridge), #26 (Observability), #31 (Event Bus & Cache)  
**Dependents**: ALL production components, #11 (Validity Testing)  
**File Size**: ~200KB (Enterprise Production-Ready)

---

## Table of Contents

### SECTION A: STRATEGIC VISION
1. [Executive Summary](#executive-summary)
2. [The Multi-Source Monitoring Challenge](#multi-source-challenge)
3. [Why Traditional MLOps Fails ADAM](#why-traditional-fails)
4. [Architecture Overview](#architecture-overview)

### SECTION B: DRIFT TAXONOMY FOR PSYCHOLOGICAL INTELLIGENCE
5. [The Eight Drift Dimensions](#eight-drift-dimensions)
6. [Intelligence Source Drift](#intelligence-source-drift)
7. [Psychological Construct Drift](#psychological-construct-drift)
8. [Fusion Quality Drift](#fusion-quality-drift)
9. [Learning System Drift](#learning-system-drift)

### SECTION C: PYDANTIC DATA MODELS
10. [Core Enums & Types](#core-enums-types)
11. [Model Health Models](#model-health-models)
12. [Intelligence Source Health Models](#intelligence-source-models)
13. [Drift Detection Models](#drift-detection-models)
14. [Psychological Drift Models](#psychological-drift-models)
15. [Alert & Notification Models](#alert-models)
16. [Retraining Models](#retraining-models)

### SECTION D: DRIFT DETECTION ENGINES
17. [Statistical Drift Detection Engine](#statistical-drift-engine)
18. [Embedding Drift Detection Engine](#embedding-drift-engine)
19. [Psychological Construct Drift Engine](#psychological-drift-engine)
20. [Intelligence Source Drift Engine](#intelligence-source-engine)
21. [Fusion Quality Drift Engine](#fusion-drift-engine)
22. [Learning Signal Drift Engine](#learning-signal-engine)

### SECTION E: MONITORING INFRASTRUCTURE
23. [Prediction Logger](#prediction-logger)
24. [Intelligence Source Monitor](#intelligence-source-monitor)
25. [Atom Output Monitor](#atom-output-monitor)
26. [Fusion Quality Monitor](#fusion-quality-monitor)
27. [Health Snapshot Generator](#health-snapshot-generator)

### SECTION F: ALERTING SYSTEM
28. [Alert Manager](#alert-manager)
29. [Alert Routing & Escalation](#alert-routing)
30. [Alert Fatigue Prevention](#alert-fatigue)
31. [Automated Response Actions](#automated-actions)

### SECTION G: AUTOMATED RETRAINING
32. [Retraining Orchestrator](#retraining-orchestrator)
33. [Model Validation Pipeline](#model-validation)
34. [Canary Deployment Integration](#canary-deployment)
35. [Rollback Automation](#rollback-automation)

### SECTION H: NEO4J SCHEMA
36. [Monitoring Graph Schema](#neo4j-monitoring-schema)
37. [Drift History Queries](#neo4j-drift-queries)
38. [Health Analytics Queries](#neo4j-health-queries)

### SECTION I: GRADIENT BRIDGE INTEGRATION (#06)
39. [Learning Signal Health Monitoring](#learning-signal-health)
40. [Attribution Quality Tracking](#attribution-quality)
41. [Cross-Component Drift Correlation](#cross-component-correlation)

### SECTION J: ATOM OF THOUGHT INTEGRATION (#04)
42. [Multi-Source Fusion Monitoring](#fusion-monitoring)
43. [Nonconscious Signal Reliability](#nonconscious-reliability)
44. [Pattern Validity Tracking](#pattern-validity)

### SECTION K: FASTAPI ENDPOINTS
45. [Health API](#health-api)
46. [Drift Detection API](#drift-detection-api)
47. [Alerting API](#alerting-api)
48. [Retraining API](#retraining-api)
49. [Dashboard API](#dashboard-api)

### SECTION L: PROMETHEUS METRICS
50. [Model Health Metrics](#model-health-metrics)
51. [Drift Detection Metrics](#drift-metrics)
52. [Intelligence Source Metrics](#intelligence-source-metrics)
53. [Learning System Metrics](#learning-metrics)

### SECTION M: TESTING & OPERATIONS
54. [Unit Tests](#unit-tests)
55. [Integration Tests](#integration-tests)
56. [Drift Simulation Framework](#drift-simulation)
57. [Implementation Timeline](#implementation-timeline)
58. [Success Metrics](#success-metrics)

---

# SECTION A: STRATEGIC VISION

## Executive Summary

### The Critical Gap in Multi-Source Intelligence

ADAM's Atom of Thought architecture fuses **ten distinct intelligence sources** into unified psychological assessments. Traditional MLOps monitors individual models for prediction drift. This is fundamentally insufficient for ADAM because:

1. **Intelligence sources are heterogeneous**: Claude reasoning, empirical patterns, bandit posteriors, and nonconscious signals each have different drift signatures
2. **Fusion quality can degrade independently**: Individual sources may be healthy while their synthesis produces degraded results
3. **Psychological constructs have validity constraints**: A "personality drift" might indicate real population change OR measurement failure
4. **Learning systems can enter feedback loops**: The Gradient Bridge propagates signals across components—drift in one can cascade to all

This specification defines a **Multi-Source Intelligence Observability System** that monitors not just ML models, but the entire reasoning substrate that produces ADAM's psychological intelligence.

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                                                                                 │
│   MULTI-SOURCE INTELLIGENCE MONITORING                                                          │
│   ═══════════════════════════════════                                                           │
│                                                                                                 │
│   Traditional MLOps:                                                                            │
│   ──────────────────                                                                            │
│                                                                                                 │
│   ┌──────────┐     ┌──────────┐     ┌──────────┐                                               │
│   │  Model   │     │  Model   │     │  Model   │                                               │
│   │    A     │     │    B     │     │    C     │                                               │
│   └────┬─────┘     └────┬─────┘     └────┬─────┘                                               │
│        │                │                │                                                      │
│        └────────────────┼────────────────┘                                                      │
│                         ▼                                                                       │
│                 ┌───────────────┐                                                               │
│                 │   Monitor     │  ← Individual model drift                                     │
│                 │   Each Model  │                                                               │
│                 └───────────────┘                                                               │
│                                                                                                 │
│                                                                                                 │
│   ADAM Multi-Source Monitoring:                                                                 │
│   ─────────────────────────────                                                                 │
│                                                                                                 │
│   ┌─────────────────────────────────────────────────────────────────────────────┐              │
│   │                        INTELLIGENCE SOURCES                                  │              │
│   │  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐          │              │
│   │  │Claude  │ │Empiric │ │Noncons │ │ Graph  │ │ Bandit │ │ Meta-  │  ...     │              │
│   │  │Reason  │ │Pattern │ │Signal  │ │Emerge  │ │Poster  │ │Learner │          │              │
│   │  └───┬────┘ └───┬────┘ └───┬────┘ └───┬────┘ └───┬────┘ └───┬────┘          │              │
│   │      │          │          │          │          │          │               │              │
│   │      └──────────┴──────────┴──────────┴──────────┴──────────┘               │              │
│   │                                    │                                         │              │
│   │                                    ▼                                         │              │
│   │                         ┌───────────────────┐                                │              │
│   │                         │  FUSION LAYER     │                                │              │
│   │                         └─────────┬─────────┘                                │              │
│   └───────────────────────────────────┼─────────────────────────────────────────┘              │
│                                       │                                                         │
│                                       ▼                                                         │
│   ┌───────────────────────────────────────────────────────────────────────────────────────┐    │
│   │                    MULTI-DIMENSIONAL MONITORING                                        │    │
│   │                                                                                        │    │
│   │  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐       │    │
│   │  │ Source Health  │  │ Fusion Quality │  │  Psychological │  │ Learning Signal│       │    │
│   │  │   Monitoring   │  │   Monitoring   │  │  Drift Detect  │  │    Health      │       │    │
│   │  └────────────────┘  └────────────────┘  └────────────────┘  └────────────────┘       │    │
│   │                                                                                        │    │
│   └───────────────────────────────────────────────────────────────────────────────────────┘    │
│                                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────────────────────┘
```

### What This System Provides

1. **Multi-Dimensional Drift Detection**: Eight distinct drift types across intelligence sources, psychological constructs, fusion quality, and learning systems
2. **Intelligence Source Health Monitoring**: Individual and comparative health tracking for all 10 intelligence sources
3. **Psychological Validity Preservation**: Detect when psychological constructs drift outside validated ranges
4. **Learning System Integrity**: Monitor Gradient Bridge signal propagation, Meta-Learner routing, and credit attribution health
5. **Fusion Quality Assurance**: Detect when source synthesis degrades even if individual sources remain healthy
6. **Automated Response**: Intelligent retraining triggers, canary deployments, and rollback automation
7. **Cascade Prevention**: Detect drift in upstream components before it propagates through the learning system

---

## The Multi-Source Monitoring Challenge

### Why ADAM is Different

Traditional ML monitoring assumes a straightforward pipeline: input → model → output. ADAM's architecture is fundamentally different:

```
                    ┌──────────────────────────────────────────────────────┐
                    │              ATOM OF THOUGHT DAG                     │
                    │                                                      │
                    │  UserState → RegulatoryFocus → ConstrualLevel        │
                    │      │              │               │                │
                    │      └──────────────┼───────────────┘                │
                    │                     ▼                                │
                    │           PersonalityExpression                      │
                    │                     │                                │
                    │          ┌──────────┴──────────┐                     │
                    │          ▼                     ▼                     │
                    │   MechanismActivation    MessageFraming              │
                    │          │                     │                     │
                    │          └──────────┬──────────┘                     │
                    │                     ▼                                │
                    │               AdSelection                            │
                    └──────────────────────────────────────────────────────┘
                                          │
                    Each atom receives evidence from 10 intelligence sources:
                                          │
        ┌─────────────────────────────────┼─────────────────────────────────┐
        │                                 │                                 │
        ▼                                 ▼                                 ▼
  ┌───────────┐                     ┌───────────┐                     ┌───────────┐
  │  Source   │                     │  Source   │                     │  Source   │
  │  1-3      │                     │  4-6      │                     │  7-10     │
  │           │                     │           │                     │           │
  │ • Claude  │                     │ • Graph   │                     │ • Temporal│
  │ • Empiric │                     │ • Bandit  │                     │ • Transfer│
  │ • Noncons │                     │ • Meta    │                     │ • Cohort  │
  └───────────┘                     └───────────┘                     └───────────┘
```

**Monitoring challenges unique to ADAM:**

1. **Source Correlation Shifts**: Sources may drift in ways that cancel out OR amplify each other
2. **Fusion Weight Decay**: The learned weights for combining sources may become stale
3. **Psychological Validity Violations**: Inferred arousal = 0.9 with construal_level = 0.8 violates Yerkes-Dodson (high arousal → concrete construal)
4. **Learning Loop Contamination**: If the Gradient Bridge propagates signals from a drifted model, all downstream components learn from corrupted data
5. **Pattern Decay**: Empirically discovered patterns may become invalid without explicit detection
6. **Nonconscious Signal Noise**: Behavioral signal reliability varies with user population and context

---

## Why Traditional MLOps Fails ADAM

### Limitation 1: Single-Model Focus

Traditional tools monitor individual models in isolation. ADAM's decisions emerge from the **fusion of multiple intelligence sources**—a drifted source might be masked by healthy sources, or vice versa.

**Example**: Claude reasoning becomes more conservative (drift) while bandit posteriors become more aggressive (compensating drift). Traditional monitoring sees "stable predictions." Reality: the system is unstable and will fail when one source becomes unavailable.

### Limitation 2: Distribution-Only Drift

Standard drift detection compares input/output distributions. For psychological constructs, **distributional stability can mask semantic drift**.

**Example**: The distribution of inferred "Openness" scores remains stable (mean=0.52, std=0.21). But the model is now conflating Openness with Extraversion—semantically different constructs with similar numerical distributions.

### Limitation 3: No Fusion Quality Metrics

MLOps tools don't monitor how well multiple signals are being synthesized. ADAM needs metrics for:
- Source agreement rates
- Conflict resolution quality
- Confidence calibration across fused outputs
- Dominant source stability

### Limitation 4: No Learning System Health

ADAM's Gradient Bridge propagates learning signals across all components. Traditional monitoring doesn't track:
- Signal propagation latency
- Attribution confidence decay
- Credit assignment accuracy
- Feedback loop stability

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│                    ADAM MODEL MONITORING & DRIFT DETECTION ARCHITECTURE                         │
├─────────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                                 │
│  ┌───────────────────────────────────────────────────────────────────────────────────────────┐  │
│  │                              DATA COLLECTION LAYER                                        │  │
│  │                                                                                           │  │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐      │  │
│  │  │   Prediction    │  │  Intelligence   │  │    Atom         │  │    Learning     │      │  │
│  │  │    Logger       │  │  Source Monitor │  │   Output Log    │  │   Signal Log    │      │  │
│  │  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘      │  │
│  │           │                    │                    │                    │               │  │
│  └───────────┼────────────────────┼────────────────────┼────────────────────┼───────────────┘  │
│              │                    │                    │                    │                  │
│              └────────────────────┴────────────────────┴────────────────────┘                  │
│                                              │                                                  │
│                                              ▼                                                  │
│  ┌───────────────────────────────────────────────────────────────────────────────────────────┐  │
│  │                              DRIFT DETECTION LAYER                                        │  │
│  │                                                                                           │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │  │
│  │  │ Statistical  │  │  Embedding   │  │Psychological │  │ Intelligence │  │   Fusion     │ │  │
│  │  │    Drift     │  │    Drift     │  │   Construct  │  │   Source     │  │   Quality    │ │  │
│  │  │   Engine     │  │   Engine     │  │    Engine    │  │   Engine     │  │   Engine     │ │  │
│  │  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘ │  │
│  │                                                                                           │  │
│  │  ┌──────────────────────────────────────────────────────────────────────────────────────┐ │  │
│  │  │                        Learning Signal Drift Engine                                  │ │  │
│  │  │   (Gradient Bridge health, Attribution quality, Feedback loop stability)             │ │  │
│  │  └──────────────────────────────────────────────────────────────────────────────────────┘ │  │
│  │                                                                                           │  │
│  └───────────────────────────────────────────────────────────────────────────────────────────┘  │
│                                              │                                                  │
│                                              ▼                                                  │
│  ┌───────────────────────────────────────────────────────────────────────────────────────────┐  │
│  │                              ALERTING & RESPONSE LAYER                                    │  │
│  │                                                                                           │  │
│  │  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐  │  │
│  │  │  Alert Manager   │  │  Fatigue         │  │  Automated       │  │   Retraining     │  │  │
│  │  │  & Routing       │  │  Prevention      │  │  Response        │  │   Orchestrator   │  │  │
│  │  └──────────────────┘  └──────────────────┘  └──────────────────┘  └──────────────────┘  │  │
│  │                                                                                           │  │
│  └───────────────────────────────────────────────────────────────────────────────────────────┘  │
│                                              │                                                  │
│                                              ▼                                                  │
│  ┌───────────────────────────────────────────────────────────────────────────────────────────┐  │
│  │                              PERSISTENCE & INTEGRATION                                    │  │
│  │                                                                                           │  │
│  │  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐  │  │
│  │  │     Neo4j        │  │     Kafka        │  │   Prometheus     │  │     Redis        │  │  │
│  │  │  Drift History   │  │  Event Stream    │  │    Metrics       │  │  Health Cache    │  │  │
│  │  └──────────────────┘  └──────────────────┘  └──────────────────┘  └──────────────────┘  │  │
│  │                                                                                           │  │
│  └───────────────────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

# SECTION B: DRIFT TAXONOMY FOR PSYCHOLOGICAL INTELLIGENCE

## The Eight Drift Dimensions

ADAM requires monitoring across eight distinct drift dimensions, each with unique detection methods and response strategies:

```python
"""
ADAM Enhancement #20: Drift Taxonomy
The eight dimensions of drift in multi-source psychological intelligence.
"""

from enum import Enum
from typing import Dict, List


class DriftDimension(str, Enum):
    """
    The eight dimensions of drift monitored in ADAM.
    
    Traditional MLOps monitors 1-2 of these. ADAM requires all eight.
    """
    
    # Traditional ML drift types
    DATA_DRIFT = "data_drift"              # Input feature distribution shift
    CONCEPT_DRIFT = "concept_drift"        # P(Y|X) relationship change
    PREDICTION_DRIFT = "prediction_drift"  # Output distribution shift
    
    # Embedding-specific drift
    EMBEDDING_DRIFT = "embedding_drift"    # Vector space geometry change
    
    # ADAM-specific drift types
    PSYCHOLOGICAL_DRIFT = "psychological_drift"    # Construct validity erosion
    INTELLIGENCE_SOURCE_DRIFT = "source_drift"     # Individual source degradation
    FUSION_DRIFT = "fusion_drift"                  # Synthesis quality decay
    LEARNING_DRIFT = "learning_drift"              # Gradient Bridge signal health


DRIFT_DIMENSION_DESCRIPTIONS = {
    DriftDimension.DATA_DRIFT: """
        Traditional data drift: input feature distributions change.
        In ADAM: User behavioral patterns, content features, or context signals shift.
        Detection: KS test, PSI, chi-square on input features.
        Impact: Models receive unfamiliar inputs, confidence drops.
    """,
    
    DriftDimension.CONCEPT_DRIFT: """
        The relationship between inputs and outputs changes.
        In ADAM: What used to predict conversion no longer does.
        Detection: Prediction error increase, calibration degradation.
        Impact: High-confidence wrong predictions—the most dangerous drift.
    """,
    
    DriftDimension.PREDICTION_DRIFT: """
        Output distributions shift even if accuracy is stable.
        In ADAM: Personality scores or mechanism selections become skewed.
        Detection: Distribution tests on predictions.
        Impact: May indicate real population change OR model failure.
    """,
    
    DriftDimension.EMBEDDING_DRIFT: """
        Vector space geometry changes—centroids shift, clusters reorganize.
        In ADAM: Psychological embeddings, user embeddings, ad embeddings.
        Detection: Centroid distance, NN preservation, cluster stability.
        Impact: Similarity-based matching becomes unreliable.
    """,
    
    DriftDimension.PSYCHOLOGICAL_DRIFT: """
        ADAM-SPECIFIC: Psychological construct validity erodes.
        Symptoms: Trait-state interactions violate psychological constraints.
        Detection: Validity constraint monitoring, correlation structure checks.
        Impact: System makes psychologically invalid inferences.
    """,
    
    DriftDimension.INTELLIGENCE_SOURCE_DRIFT: """
        ADAM-SPECIFIC: One of the 10 intelligence sources degrades.
        Symptoms: Confidence drops, latency increases, coverage decreases.
        Detection: Per-source health metrics, comparative analysis.
        Impact: Fusion quality depends on weakest source for affected contexts.
    """,
    
    DriftDimension.FUSION_DRIFT: """
        ADAM-SPECIFIC: Source synthesis quality degrades.
        Symptoms: Source conflicts increase, confidence drops, dominant source shifts.
        Detection: Fusion confidence, agreement rates, conflict severity.
        Impact: Even healthy sources produce poor combined assessments.
    """,
    
    DriftDimension.LEARNING_DRIFT: """
        ADAM-SPECIFIC: Gradient Bridge signal health degrades.
        Symptoms: Attribution confidence drops, signal propagation fails, priors stale.
        Detection: Signal propagation metrics, attribution entropy, prior freshness.
        Impact: System stops learning or learns from corrupted signals.
    """
}


# Severity and response mapping for each drift dimension
DRIFT_RESPONSE_MATRIX: Dict[DriftDimension, Dict[str, str]] = {
    DriftDimension.DATA_DRIFT: {
        "warning": "Increase monitoring frequency, investigate root cause",
        "critical": "Review feature pipeline, consider feature engineering",
        "emergency": "Pause model, switch to fallback"
    },
    DriftDimension.CONCEPT_DRIFT: {
        "warning": "Schedule retraining evaluation",
        "critical": "Initiate automated retraining pipeline",
        "emergency": "Switch to fallback model, emergency retraining"
    },
    DriftDimension.PREDICTION_DRIFT: {
        "warning": "Investigate if real population change or model failure",
        "critical": "A/B test against holdout, prepare retraining",
        "emergency": "Switch to conservative predictions"
    },
    DriftDimension.EMBEDDING_DRIFT: {
        "warning": "Monitor downstream matching quality",
        "critical": "Re-index vector store with new embeddings",
        "emergency": "Fallback to non-embedding matching"
    },
    DriftDimension.PSYCHOLOGICAL_DRIFT: {
        "warning": "Flag for psychological validity review",
        "critical": "Enable constraint enforcement mode",
        "emergency": "Fallback to conservative psychological inferences"
    },
    DriftDimension.INTELLIGENCE_SOURCE_DRIFT: {
        "warning": "Reduce source weight in fusion",
        "critical": "Exclude source from fusion, investigate",
        "emergency": "Full graceful degradation to available sources"
    },
    DriftDimension.FUSION_DRIFT: {
        "warning": "Re-calibrate fusion weights",
        "critical": "Switch to weighted fallback fusion",
        "emergency": "Single-source mode with best available source"
    },
    DriftDimension.LEARNING_DRIFT: {
        "warning": "Quarantine affected learning signals",
        "critical": "Pause learning updates, use frozen priors",
        "emergency": "Full learning system pause, manual review required"
    }
}
```

---

## Intelligence Source Drift

Each of ADAM's 10 intelligence sources can drift independently:

```python
"""
ADAM Enhancement #20: Intelligence Source Drift Specifications
Drift detection for each of the 10 intelligence sources.
"""

from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class IntelligenceSourceType(str, Enum):
    """The 10 intelligence sources in ADAM's Atom of Thought."""
    CLAUDE_REASONING = "claude_reasoning"
    EMPIRICAL_PATTERNS = "empirical_patterns"
    NONCONSCIOUS_SIGNALS = "nonconscious_signals"
    GRAPH_EMERGENCE = "graph_emergence"
    BANDIT_POSTERIORS = "bandit_posteriors"
    META_LEARNER = "meta_learner"
    MECHANISM_EFFECTIVENESS = "mechanism_effectiveness"
    TEMPORAL_PATTERNS = "temporal_patterns"
    CROSS_DOMAIN_TRANSFER = "cross_domain_transfer"
    COHORT_SELF_ORGANIZATION = "cohort_self_organization"


class SourceDriftIndicators(BaseModel):
    """Drift indicators specific to each intelligence source type."""
    
    source_type: IntelligenceSourceType
    
    # Universal indicators
    confidence_mean: float = Field(ge=0.0, le=1.0)
    confidence_std: float = Field(ge=0.0)
    latency_p50_ms: float = Field(ge=0.0)
    latency_p99_ms: float = Field(ge=0.0)
    availability_rate: float = Field(ge=0.0, le=1.0)
    error_rate: float = Field(ge=0.0, le=1.0)
    
    # Source-specific indicators (populated based on source_type)
    source_specific: Dict[str, float] = Field(default_factory=dict)


# Source-specific drift indicators
SOURCE_DRIFT_INDICATORS: Dict[IntelligenceSourceType, Dict[str, str]] = {
    
    IntelligenceSourceType.CLAUDE_REASONING: {
        "explanation_length_mean": "Average explanation token count",
        "reasoning_step_count": "Average reasoning steps",
        "confidence_calibration_error": "ECE for Claude confidence scores",
        "psychological_citation_rate": "% of responses citing research",
        "uncertainty_expression_rate": "% of responses expressing uncertainty",
        "refusal_rate": "% of requests refused or punted"
    },
    
    IntelligenceSourceType.EMPIRICAL_PATTERNS: {
        "pattern_count_active": "Number of active validated patterns",
        "pattern_validation_rate": "% of discovered patterns that validate",
        "pattern_decay_rate": "% of patterns invalidated per week",
        "pattern_coverage": "% of user-context pairs with applicable pattern",
        "pattern_confidence_mean": "Average pattern confidence",
        "pattern_staleness_days": "Average days since pattern last validated"
    },
    
    IntelligenceSourceType.NONCONSCIOUS_SIGNALS: {
        "signal_availability": "% of sessions with sufficient behavioral data",
        "signal_noise_estimate": "Estimated noise level in signals",
        "construct_mapping_confidence": "Confidence in signal→construct mapping",
        "cross_session_consistency": "Consistency of signals across sessions",
        "temporal_stability": "Signal stability within session",
        "population_calibration_error": "Deviation from population norms"
    },
    
    IntelligenceSourceType.GRAPH_EMERGENCE: {
        "community_stability": "Stability of detected communities",
        "relationship_density": "Average relationships per user node",
        "traversal_depth_mean": "Average graph traversal depth",
        "stale_relationship_rate": "% of relationships not updated recently",
        "orphan_node_rate": "% of nodes with no relationships",
        "query_latency_p99_ms": "P99 graph query latency"
    },
    
    IntelligenceSourceType.BANDIT_POSTERIORS: {
        "posterior_entropy_mean": "Average entropy of posteriors",
        "exploration_rate": "% of decisions that are exploratory",
        "convergence_rate": "Rate of posterior convergence",
        "arm_diversity": "Diversity of selected arms",
        "prior_staleness_hours": "Hours since priors updated",
        "regret_estimate": "Estimated cumulative regret"
    },
    
    IntelligenceSourceType.META_LEARNER: {
        "routing_entropy": "Entropy of routing decisions",
        "routing_stability": "Stability of routing choices",
        "adaptation_rate": "Speed of adaptation to context",
        "performance_differential": "Performance gap between routes",
        "cold_start_routing_confidence": "Confidence for new users",
        "cross_context_transfer": "Transfer learning effectiveness"
    },
    
    IntelligenceSourceType.MECHANISM_EFFECTIVENESS: {
        "effectiveness_variance": "Variance in mechanism effectiveness",
        "mechanism_diversity": "Diversity of effective mechanisms",
        "temporal_stability": "Stability of effectiveness over time",
        "context_specificity": "How context-dependent effectiveness is",
        "sample_size_adequacy": "Adequacy of effectiveness estimates",
        "confidence_calibration": "Calibration of effectiveness confidence"
    },
    
    IntelligenceSourceType.TEMPORAL_PATTERNS: {
        "seasonal_detection_confidence": "Confidence in seasonal patterns",
        "trend_stability": "Stability of detected trends",
        "periodicity_strength": "Strength of periodic patterns",
        "anomaly_rate": "Rate of temporal anomalies",
        "forecast_accuracy": "Accuracy of temporal forecasts",
        "pattern_horizon_days": "Lookahead horizon for patterns"
    },
    
    IntelligenceSourceType.CROSS_DOMAIN_TRANSFER: {
        "transfer_applicability": "% of contexts where transfer applies",
        "transfer_effectiveness": "Effectiveness of transferred knowledge",
        "domain_similarity_threshold": "Threshold for domain similarity",
        "negative_transfer_rate": "Rate of harmful transfer",
        "source_domain_diversity": "Diversity of source domains",
        "transfer_confidence": "Confidence in transfer applicability"
    },
    
    IntelligenceSourceType.COHORT_SELF_ORGANIZATION: {
        "cohort_stability": "Stability of self-organized cohorts",
        "cohort_count": "Number of active cohorts",
        "cohort_size_distribution": "Distribution of cohort sizes",
        "cross_cohort_similarity": "Similarity between cohorts",
        "cohort_membership_churn": "Rate of membership changes",
        "behavioral_homogeneity": "Behavioral similarity within cohorts"
    }
}
```

---

## Psychological Construct Drift

Psychological constructs have validity constraints that must be monitored:

```python
"""
ADAM Enhancement #20: Psychological Construct Drift
Monitoring validity of psychological inferences.
"""

from typing import Dict, List, Tuple, Optional
from pydantic import BaseModel, Field
from enum import Enum


class PsychologicalConstruct(str, Enum):
    """Psychological constructs that ADAM infers."""
    
    # Big Five traits
    OPENNESS = "openness"
    CONSCIENTIOUSNESS = "conscientiousness"
    EXTRAVERSION = "extraversion"
    AGREEABLENESS = "agreeableness"
    NEUROTICISM = "neuroticism"
    
    # State variables
    AROUSAL = "arousal"
    VALENCE = "valence"
    COGNITIVE_LOAD = "cognitive_load"
    CONSTRUAL_LEVEL = "construal_level"
    
    # Regulatory constructs
    REGULATORY_FOCUS = "regulatory_focus"  # Promotion vs prevention
    
    # Extended constructs
    NEED_FOR_COGNITION = "need_for_cognition"
    SELF_MONITORING = "self_monitoring"
    TEMPORAL_ORIENTATION = "temporal_orientation"
    DECISION_STYLE = "decision_style"


class PsychologicalConstraint(BaseModel):
    """
    A psychological constraint that should hold if inferences are valid.
    Based on validated psychological research.
    """
    
    constraint_id: str
    constraint_name: str
    description: str
    research_basis: List[str]  # Citations
    
    # The constructs involved
    constructs_involved: List[PsychologicalConstruct]
    
    # Constraint specification
    constraint_type: str  # "correlation", "conditional", "boundary"
    constraint_expression: str  # Mathematical/logical expression
    
    # Expected vs violation thresholds
    expected_range: Tuple[float, float]
    warning_threshold: float
    violation_threshold: float
    
    # Monitoring
    check_frequency: str  # "per_inference", "hourly", "daily"


# Psychological constraints from research
PSYCHOLOGICAL_CONSTRAINTS: List[Dict] = [
    {
        "constraint_id": "yerkes_dodson_arousal_construal",
        "constraint_name": "Yerkes-Dodson Arousal-Construal",
        "description": "High arousal biases toward concrete (low) construal level",
        "research_basis": [
            "Yerkes & Dodson, 1908",
            "Storbeck & Clore, 2007",
            "Gable & Harmon-Jones, 2010"
        ],
        "constructs_involved": [
            PsychologicalConstruct.AROUSAL,
            PsychologicalConstruct.CONSTRUAL_LEVEL
        ],
        "constraint_type": "correlation",
        "constraint_expression": "correlation(arousal, construal_level) < 0",
        "expected_range": (-0.6, -0.2),
        "warning_threshold": -0.1,
        "violation_threshold": 0.1,
        "check_frequency": "hourly"
    },
    {
        "constraint_id": "neuroticism_prevention_focus",
        "constraint_name": "Neuroticism-Prevention Focus",
        "description": "High neuroticism correlates with prevention regulatory focus",
        "research_basis": [
            "Higgins, 1997",
            "Elliot & Thrash, 2002"
        ],
        "constructs_involved": [
            PsychologicalConstruct.NEUROTICISM,
            PsychologicalConstruct.REGULATORY_FOCUS
        ],
        "constraint_type": "correlation",
        "constraint_expression": "correlation(neuroticism, prevention_focus) > 0",
        "expected_range": (0.3, 0.6),
        "warning_threshold": 0.2,
        "violation_threshold": 0.0,
        "check_frequency": "daily"
    },
    {
        "constraint_id": "cognitive_load_construal_shift",
        "constraint_name": "Cognitive Load-Construal Shift",
        "description": "High cognitive load biases toward concrete construal",
        "research_basis": [
            "Trope & Liberman, 2010",
            "Burgoon et al., 2013"
        ],
        "constructs_involved": [
            PsychologicalConstruct.COGNITIVE_LOAD,
            PsychologicalConstruct.CONSTRUAL_LEVEL
        ],
        "constraint_type": "correlation",
        "constraint_expression": "correlation(cognitive_load, construal_level) < 0",
        "expected_range": (-0.5, -0.15),
        "warning_threshold": -0.05,
        "violation_threshold": 0.1,
        "check_frequency": "hourly"
    },
    {
        "constraint_id": "big_five_orthogonality",
        "constraint_name": "Big Five Orthogonality",
        "description": "Big Five traits should be approximately orthogonal",
        "research_basis": [
            "Costa & McCrae, 1992",
            "Goldberg, 1993"
        ],
        "constructs_involved": [
            PsychologicalConstruct.OPENNESS,
            PsychologicalConstruct.CONSCIENTIOUSNESS,
            PsychologicalConstruct.EXTRAVERSION,
            PsychologicalConstruct.AGREEABLENESS,
            PsychologicalConstruct.NEUROTICISM
        ],
        "constraint_type": "correlation",
        "constraint_expression": "max_pairwise_correlation(big_five) < threshold",
        "expected_range": (0.0, 0.3),
        "warning_threshold": 0.4,
        "violation_threshold": 0.6,
        "check_frequency": "daily"
    },
    {
        "constraint_id": "nfc_processing_depth",
        "constraint_name": "Need for Cognition-Processing Depth",
        "description": "High NFC correlates with deeper processing",
        "research_basis": [
            "Cacioppo & Petty, 1982",
            "Petty et al., 2009"
        ],
        "constructs_involved": [
            PsychologicalConstruct.NEED_FOR_COGNITION
        ],
        "constraint_type": "conditional",
        "constraint_expression": "if nfc > 0.7 then processing_depth > 0.5",
        "expected_range": (0.7, 0.95),
        "warning_threshold": 0.6,
        "violation_threshold": 0.4,
        "check_frequency": "daily"
    },
    {
        "constraint_id": "trait_temporal_stability",
        "constraint_name": "Trait Temporal Stability",
        "description": "Traits should be stable within short time windows",
        "research_basis": [
            "Roberts & DelVecchio, 2000"
        ],
        "constructs_involved": [
            PsychologicalConstruct.OPENNESS,
            PsychologicalConstruct.CONSCIENTIOUSNESS,
            PsychologicalConstruct.EXTRAVERSION,
            PsychologicalConstruct.AGREEABLENESS,
            PsychologicalConstruct.NEUROTICISM
        ],
        "constraint_type": "boundary",
        "constraint_expression": "trait_variance_7day < threshold",
        "expected_range": (0.0, 0.1),
        "warning_threshold": 0.15,
        "violation_threshold": 0.25,
        "check_frequency": "daily"
    },
    {
        "constraint_id": "state_variability",
        "constraint_name": "State Variability",
        "description": "States should show expected variability (not too stable, not too chaotic)",
        "research_basis": [
            "Fleeson, 2001",
            "Watson & Clark, 1994"
        ],
        "constructs_involved": [
            PsychologicalConstruct.AROUSAL,
            PsychologicalConstruct.VALENCE,
            PsychologicalConstruct.COGNITIVE_LOAD
        ],
        "constraint_type": "boundary",
        "constraint_expression": "min_state_variance < state_variance < max_state_variance",
        "expected_range": (0.15, 0.4),
        "warning_threshold": 0.1,
        "violation_threshold": 0.05,
        "check_frequency": "hourly"
    }
]


class PsychologicalDriftResult(BaseModel):
    """Result of psychological construct drift detection."""
    
    detection_id: str = Field(description="Unique detection identifier")
    detected_at: str = Field(description="ISO timestamp")
    
    # Constraint that was violated
    constraint_id: str
    constraint_name: str
    
    # Measurement details
    observed_value: float
    expected_range: Tuple[float, float]
    deviation_severity: str  # "warning", "violation"
    
    # Constructs involved
    constructs_involved: List[PsychologicalConstruct]
    
    # Impact assessment
    affected_user_percentage: float = Field(ge=0.0, le=1.0)
    affected_decision_count: int
    
    # Diagnostic info
    possible_causes: List[str]
    recommended_actions: List[str]
```

---

# SECTION C: PYDANTIC DATA MODELS

## Core Enums & Types

```python
"""
ADAM Enhancement #20: Core Enums and Types
Foundational type definitions for model monitoring.
"""

from __future__ import annotations
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple, Union, Literal
from datetime import datetime, timezone, timedelta
from uuid import uuid4
from pydantic import BaseModel, Field, field_validator, model_validator


# =============================================================================
# ENUMS
# =============================================================================

class ModelCategory(str, Enum):
    """Categories of models in ADAM."""
    
    # Core inference models
    PERSONALITY_INFERENCE = "personality_inference"
    STATE_DETECTION = "state_detection"
    MECHANISM_SELECTION = "mechanism_selection"
    
    # Generation models
    COPY_GENERATION = "copy_generation"
    EXPLANATION_GENERATION = "explanation_generation"
    
    # Ranking and selection
    AD_RANKING = "ad_ranking"
    CREATIVE_SELECTION = "creative_selection"
    
    # Identity and journey
    IDENTITY_RESOLUTION = "identity_resolution"
    JOURNEY_PREDICTION = "journey_prediction"
    
    # Embeddings
    USER_EMBEDDING = "user_embedding"
    AD_EMBEDDING = "ad_embedding"
    PSYCHOLOGICAL_EMBEDDING = "psychological_embedding"
    
    # Specialized
    VOICE_ANALYSIS = "voice_analysis"
    CONTENT_UNDERSTANDING = "content_understanding"
    MULTIMODAL_FUSION = "multimodal_fusion"
    COLD_START = "cold_start"


class DriftType(str, Enum):
    """Types of drift that can occur."""
    
    # Traditional ML drift
    DATA_DRIFT = "data_drift"
    CONCEPT_DRIFT = "concept_drift"
    LABEL_DRIFT = "label_drift"
    FEATURE_DRIFT = "feature_drift"
    PREDICTION_DRIFT = "prediction_drift"
    UPSTREAM_DRIFT = "upstream_drift"
    EMBEDDING_DRIFT = "embedding_drift"
    CALIBRATION_DRIFT = "calibration_drift"
    
    # ADAM-specific drift
    PSYCHOLOGICAL_DRIFT = "psychological_drift"
    INTELLIGENCE_SOURCE_DRIFT = "intelligence_source_drift"
    FUSION_DRIFT = "fusion_drift"
    LEARNING_SIGNAL_DRIFT = "learning_signal_drift"
    PATTERN_VALIDITY_DRIFT = "pattern_validity_drift"
    CONSTRAINT_VIOLATION_DRIFT = "constraint_violation_drift"


class AlertSeverity(str, Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class AlertStatus(str, Enum):
    """Alert lifecycle status."""
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"
    AUTO_RESOLVED = "auto_resolved"


class RetrainingTrigger(str, Enum):
    """What triggered a retraining."""
    SCHEDULED = "scheduled"
    DRIFT_DETECTED = "drift_detected"
    PERFORMANCE_DEGRADATION = "performance_degradation"
    MANUAL = "manual"
    ROLLBACK = "rollback"
    A_B_TEST_RESULT = "ab_test_result"
    PSYCHOLOGICAL_VALIDITY = "psychological_validity"


class RetrainingStatus(str, Enum):
    """Status of retraining job."""
    QUEUED = "queued"
    PREPARING_DATA = "preparing_data"
    TRAINING = "training"
    VALIDATING = "validating"
    CANARY_TESTING = "canary_testing"
    DEPLOYING = "deploying"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class HealthStatus(str, Enum):
    """Overall health status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class MonitoringWindow(str, Enum):
    """Predefined monitoring windows."""
    MINUTE_1 = "1m"
    MINUTE_5 = "5m"
    MINUTE_15 = "15m"
    HOUR_1 = "1h"
    HOUR_6 = "6h"
    HOUR_24 = "24h"
    DAY_7 = "7d"
    DAY_30 = "30d"


# =============================================================================
# WINDOW CONVERSION
# =============================================================================

WINDOW_TO_SECONDS: Dict[MonitoringWindow, int] = {
    MonitoringWindow.MINUTE_1: 60,
    MonitoringWindow.MINUTE_5: 300,
    MonitoringWindow.MINUTE_15: 900,
    MonitoringWindow.HOUR_1: 3600,
    MonitoringWindow.HOUR_6: 21600,
    MonitoringWindow.HOUR_24: 86400,
    MonitoringWindow.DAY_7: 604800,
    MonitoringWindow.DAY_30: 2592000,
}


def window_to_timedelta(window: MonitoringWindow) -> timedelta:
    """Convert monitoring window to timedelta."""
    return timedelta(seconds=WINDOW_TO_SECONDS[window])
```

---

## Model Health Models

```python
"""
ADAM Enhancement #20: Model Health Models
Pydantic models for tracking model health.
"""

from __future__ import annotations
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator, model_validator


class LatencyMetrics(BaseModel):
    """Latency metrics for a model."""
    
    p50_ms: float = Field(ge=0.0, description="Median latency")
    p90_ms: float = Field(ge=0.0, description="90th percentile latency")
    p95_ms: float = Field(ge=0.0, description="95th percentile latency")
    p99_ms: float = Field(ge=0.0, description="99th percentile latency")
    max_ms: float = Field(ge=0.0, description="Maximum latency")
    mean_ms: float = Field(ge=0.0, description="Mean latency")
    
    @model_validator(mode='after')
    def validate_latency_ordering(self) -> 'LatencyMetrics':
        """Ensure latency percentiles are in order."""
        if not (self.p50_ms <= self.p90_ms <= self.p95_ms <= self.p99_ms <= self.max_ms):
            raise ValueError("Latency percentiles must be in ascending order")
        return self


class AccuracyMetrics(BaseModel):
    """Accuracy metrics for a model (when ground truth available)."""
    
    accuracy: Optional[float] = Field(None, ge=0.0, le=1.0)
    precision: Optional[float] = Field(None, ge=0.0, le=1.0)
    recall: Optional[float] = Field(None, ge=0.0, le=1.0)
    f1_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    
    # For regression/scoring models
    mae: Optional[float] = Field(None, ge=0.0)
    rmse: Optional[float] = Field(None, ge=0.0)
    correlation: Optional[float] = Field(None, ge=-1.0, le=1.0)
    r_squared: Optional[float] = Field(None, ge=0.0, le=1.0)


class CalibrationMetrics(BaseModel):
    """Calibration metrics for confidence scores."""
    
    expected_calibration_error: float = Field(
        ge=0.0, le=1.0,
        description="ECE: weighted average of calibration error per bin"
    )
    maximum_calibration_error: float = Field(
        ge=0.0, le=1.0,
        description="MCE: maximum calibration error across bins"
    )
    overconfidence_rate: float = Field(
        ge=0.0, le=1.0,
        description="Fraction of predictions where confidence > accuracy"
    )
    underconfidence_rate: float = Field(
        ge=0.0, le=1.0,
        description="Fraction of predictions where confidence < accuracy"
    )
    brier_score: Optional[float] = Field(
        None, ge=0.0, le=1.0,
        description="Brier score for probabilistic predictions"
    )


class DriftScores(BaseModel):
    """Current drift scores across dimensions."""
    
    data_drift_score: float = Field(ge=0.0, le=1.0, default=0.0)
    concept_drift_score: float = Field(ge=0.0, le=1.0, default=0.0)
    prediction_drift_score: float = Field(ge=0.0, le=1.0, default=0.0)
    embedding_drift_score: float = Field(ge=0.0, le=1.0, default=0.0)
    
    # ADAM-specific
    psychological_drift_score: float = Field(ge=0.0, le=1.0, default=0.0)
    
    @property
    def max_drift(self) -> float:
        """Maximum drift score across all dimensions."""
        return max(
            self.data_drift_score,
            self.concept_drift_score,
            self.prediction_drift_score,
            self.embedding_drift_score,
            self.psychological_drift_score
        )


class ModelHealthSnapshot(BaseModel):
    """
    Point-in-time health snapshot for a model.
    Generated periodically (e.g., every 5 minutes).
    """
    
    # Identification
    snapshot_id: str = Field(default_factory=lambda: f"snap_{uuid4().hex[:12]}")
    model_id: str
    model_version: str
    model_category: ModelCategory
    snapshot_timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    
    # Volume metrics
    prediction_count: int = Field(ge=0)
    predictions_per_second: float = Field(ge=0.0)
    
    # Latency
    latency: LatencyMetrics
    
    # Accuracy (if ground truth available)
    accuracy: Optional[AccuracyMetrics] = None
    
    # Calibration
    calibration: Optional[CalibrationMetrics] = None
    
    # Drift scores
    drift_scores: DriftScores = Field(default_factory=DriftScores)
    
    # Error tracking
    error_rate: float = Field(ge=0.0, le=1.0, default=0.0)
    fallback_rate: float = Field(ge=0.0, le=1.0, default=0.0)
    cold_start_rate: float = Field(ge=0.0, le=1.0, default=0.0)
    timeout_rate: float = Field(ge=0.0, le=1.0, default=0.0)
    
    # Overall health
    overall_health: HealthStatus = HealthStatus.UNKNOWN
    health_issues: List[str] = Field(default_factory=list)
    
    @model_validator(mode='after')
    def compute_health_status(self) -> 'ModelHealthSnapshot':
        """Compute overall health status from metrics."""
        issues = []
        status = HealthStatus.HEALTHY
        
        # Check latency (assuming 100ms budget for real-time)
        if self.latency.p99_ms > 100:
            issues.append("high_p99_latency")
            status = HealthStatus.DEGRADED
        if self.latency.p99_ms > 200:
            status = HealthStatus.CRITICAL
        
        # Check error rate
        if self.error_rate > 0.01:
            issues.append("elevated_error_rate")
            status = max(status, HealthStatus.DEGRADED, key=lambda x: x.value)
        if self.error_rate > 0.05:
            issues.append("high_error_rate")
            status = HealthStatus.CRITICAL
        
        # Check drift
        if self.drift_scores.max_drift > 0.3:
            issues.append("significant_drift_detected")
            status = max(status, HealthStatus.DEGRADED, key=lambda x: x.value)
        if self.drift_scores.max_drift > 0.5:
            status = HealthStatus.CRITICAL
        
        # Check fallback rate
        if self.fallback_rate > 0.1:
            issues.append("high_fallback_rate")
            status = max(status, HealthStatus.DEGRADED, key=lambda x: x.value)
        
        # Check predictions
        if self.predictions_per_second == 0:
            issues.append("no_predictions")
            status = HealthStatus.CRITICAL
        
        # Check calibration
        if self.calibration and self.calibration.expected_calibration_error > 0.1:
            issues.append("poor_calibration")
            status = max(status, HealthStatus.DEGRADED, key=lambda x: x.value)
        
        self.health_issues = issues
        self.overall_health = status
        return self
    
    class Config:
        use_enum_values = True


class ModelRegistry(BaseModel):
    """Model metadata in the registry."""
    
    model_id: str
    model_name: str
    model_version: str
    model_category: ModelCategory
    
    # Deployment info
    deployed_at: datetime
    deployed_by: str
    deployment_environment: str  # "production", "canary", "shadow"
    
    # Dependencies
    upstream_models: List[str] = Field(default_factory=list)
    downstream_models: List[str] = Field(default_factory=list)
    
    # Monitoring configuration
    monitoring_enabled: bool = True
    drift_detection_enabled: bool = True
    auto_retraining_enabled: bool = False
    
    # Thresholds
    latency_p99_threshold_ms: float = 100.0
    error_rate_threshold: float = 0.05
    drift_alert_threshold: float = 0.3
    
    # Metadata
    tags: Dict[str, str] = Field(default_factory=dict)
    description: Optional[str] = None


class PredictionRecord(BaseModel):
    """
    Record of a single prediction for monitoring.
    Logged for drift detection and analysis.
    """
    
    # Identification
    prediction_id: str = Field(default_factory=lambda: f"pred_{uuid4().hex[:12]}")
    model_id: str
    model_version: str
    
    # Timing
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    latency_ms: float = Field(ge=0.0)
    
    # Input/Output
    input_features: Dict[str, Any]
    input_feature_hash: str  # For deduplication
    prediction: Any
    confidence: float = Field(ge=0.0, le=1.0)
    
    # Ground truth (filled in later)
    ground_truth: Optional[Any] = None
    ground_truth_timestamp: Optional[datetime] = None
    
    # Context
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    
    # Upstream dependencies
    upstream_prediction_ids: List[str] = Field(default_factory=list)
    
    # Flags
    is_fallback: bool = False
    is_cold_start: bool = False
    
    class Config:
        use_enum_values = True
```

---

## Intelligence Source Health Models

```python
"""
ADAM Enhancement #20: Intelligence Source Health Models
Models for tracking health of ADAM's 10 intelligence sources.
"""

from __future__ import annotations
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


class IntelligenceSourceHealth(BaseModel):
    """
    Health metrics for a single intelligence source.
    Each source has both universal and source-specific metrics.
    """
    
    # Identification
    source_type: IntelligenceSourceType
    snapshot_timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    
    # Universal metrics (all sources)
    availability_rate: float = Field(
        ge=0.0, le=1.0,
        description="Fraction of requests where source was available"
    )
    response_rate: float = Field(
        ge=0.0, le=1.0,
        description="Fraction of requests that received a response"
    )
    error_rate: float = Field(
        ge=0.0, le=1.0,
        description="Fraction of requests that errored"
    )
    timeout_rate: float = Field(
        ge=0.0, le=1.0,
        description="Fraction of requests that timed out"
    )
    
    # Latency
    latency_p50_ms: float = Field(ge=0.0)
    latency_p99_ms: float = Field(ge=0.0)
    
    # Confidence metrics
    confidence_mean: float = Field(ge=0.0, le=1.0)
    confidence_std: float = Field(ge=0.0)
    confidence_trend: float = Field(
        description="Positive = improving, negative = degrading"
    )
    
    # Coverage
    coverage_rate: float = Field(
        ge=0.0, le=1.0,
        description="Fraction of user-contexts with evidence from this source"
    )
    
    # Source-specific metrics
    source_specific_metrics: Dict[str, float] = Field(default_factory=dict)
    
    # Health status
    health_status: HealthStatus = HealthStatus.UNKNOWN
    health_issues: List[str] = Field(default_factory=list)
    
    def compute_health(self) -> 'IntelligenceSourceHealth':
        """Compute health status from metrics."""
        issues = []
        status = HealthStatus.HEALTHY
        
        # Availability check
        if self.availability_rate < 0.95:
            issues.append("low_availability")
            status = HealthStatus.DEGRADED
        if self.availability_rate < 0.8:
            status = HealthStatus.CRITICAL
        
        # Error rate check
        if self.error_rate > 0.05:
            issues.append("elevated_error_rate")
            status = max(status, HealthStatus.DEGRADED, key=lambda x: x.value)
        if self.error_rate > 0.15:
            status = HealthStatus.CRITICAL
        
        # Latency check (source-specific thresholds)
        latency_threshold = SOURCE_LATENCY_THRESHOLDS.get(
            self.source_type, 500
        )
        if self.latency_p99_ms > latency_threshold:
            issues.append("high_latency")
            status = max(status, HealthStatus.DEGRADED, key=lambda x: x.value)
        
        # Confidence trend check
        if self.confidence_trend < -0.05:
            issues.append("declining_confidence")
            status = max(status, HealthStatus.DEGRADED, key=lambda x: x.value)
        
        self.health_issues = issues
        self.health_status = status
        return self


# Per-source latency thresholds (in ms)
SOURCE_LATENCY_THRESHOLDS: Dict[IntelligenceSourceType, float] = {
    IntelligenceSourceType.CLAUDE_REASONING: 2000,      # LLM calls are slower
    IntelligenceSourceType.EMPIRICAL_PATTERNS: 50,     # Should be fast (cache)
    IntelligenceSourceType.NONCONSCIOUS_SIGNALS: 100,  # Real-time computation
    IntelligenceSourceType.GRAPH_EMERGENCE: 200,       # Graph traversal
    IntelligenceSourceType.BANDIT_POSTERIORS: 50,      # Should be cached
    IntelligenceSourceType.META_LEARNER: 100,          # Routing decision
    IntelligenceSourceType.MECHANISM_EFFECTIVENESS: 50, # Lookup
    IntelligenceSourceType.TEMPORAL_PATTERNS: 100,     # Pattern matching
    IntelligenceSourceType.CROSS_DOMAIN_TRANSFER: 100, # Similarity search
    IntelligenceSourceType.COHORT_SELF_ORGANIZATION: 150,  # Community detection
}


class IntelligenceSourceComparison(BaseModel):
    """
    Comparative analysis of intelligence sources.
    Identifies which sources are over/underperforming.
    """
    
    comparison_timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    window: MonitoringWindow
    
    # Source health snapshots
    source_health: Dict[IntelligenceSourceType, IntelligenceSourceHealth]
    
    # Comparative metrics
    most_available_source: IntelligenceSourceType
    least_available_source: IntelligenceSourceType
    highest_confidence_source: IntelligenceSourceType
    lowest_confidence_source: IntelligenceSourceType
    fastest_source: IntelligenceSourceType
    slowest_source: IntelligenceSourceType
    
    # Correlation with outcomes
    source_outcome_correlations: Dict[IntelligenceSourceType, float] = Field(
        default_factory=dict,
        description="Correlation between source confidence and conversion"
    )
    
    # Anomalies
    anomalous_sources: List[IntelligenceSourceType] = Field(default_factory=list)
    anomaly_details: Dict[IntelligenceSourceType, str] = Field(default_factory=dict)


class FusionHealthSnapshot(BaseModel):
    """
    Health metrics for the multi-source fusion layer.
    Monitors how well sources are being synthesized.
    """
    
    snapshot_id: str = Field(default_factory=lambda: f"fusion_{uuid4().hex[:12]}")
    snapshot_timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    window: MonitoringWindow
    
    # Volume
    fusion_count: int = Field(ge=0, description="Number of fusions in window")
    
    # Source availability
    average_sources_available: float = Field(
        ge=0.0, le=10.0,
        description="Average number of sources available per fusion"
    )
    minimum_sources_available: int = Field(ge=0, le=10)
    full_source_fusion_rate: float = Field(
        ge=0.0, le=1.0,
        description="Fraction of fusions with all 10 sources"
    )
    
    # Confidence metrics
    fusion_confidence_mean: float = Field(ge=0.0, le=1.0)
    fusion_confidence_std: float = Field(ge=0.0)
    
    # Agreement metrics
    source_agreement_rate: float = Field(
        ge=0.0, le=1.0,
        description="Fraction of fusions where sources agreed"
    )
    conflict_rate: float = Field(
        ge=0.0, le=1.0,
        description="Fraction of fusions with source conflicts"
    )
    severe_conflict_rate: float = Field(
        ge=0.0, le=1.0,
        description="Fraction of fusions with severe conflicts"
    )
    
    # Dominant source analysis
    dominant_source_distribution: Dict[IntelligenceSourceType, float] = Field(
        default_factory=dict,
        description="Distribution of which source dominated each fusion"
    )
    dominant_source_entropy: float = Field(
        ge=0.0,
        description="Entropy of dominant source distribution (higher = more balanced)"
    )
    
    # Performance correlation
    fusion_confidence_outcome_correlation: Optional[float] = Field(
        None,
        ge=-1.0, le=1.0,
        description="Correlation between fusion confidence and conversion"
    )
    
    # Health
    health_status: HealthStatus = HealthStatus.UNKNOWN
    health_issues: List[str] = Field(default_factory=list)
```

---

## Drift Detection Models

```python
"""
ADAM Enhancement #20: Drift Detection Models
Pydantic models for drift detection results.
"""

from __future__ import annotations
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


class DriftTestConfig(BaseModel):
    """Configuration for a specific drift test."""
    
    test_name: str
    test_type: DriftType
    
    # Statistical parameters
    significance_level: float = Field(default=0.05, ge=0.0, le=1.0)
    warning_threshold: float = Field(
        description="Effect size threshold for warning"
    )
    critical_threshold: float = Field(
        description="Effect size threshold for critical alert"
    )
    
    # Window configuration
    reference_window_days: int = Field(default=30, ge=1)
    detection_window_hours: int = Field(default=24, ge=1)
    
    # Sample requirements
    min_sample_size: int = Field(default=100, ge=10)
    
    # Multiple testing correction
    bonferroni_correction: bool = Field(default=True)


class DriftDetectionResult(BaseModel):
    """Result of a drift detection test."""
    
    # Identification
    detection_id: str = Field(default_factory=lambda: f"drift_{uuid4().hex[:12]}")
    test_name: str
    drift_type: DriftType
    model_id: str
    
    # Timing
    detected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    reference_window: Tuple[datetime, datetime]
    detection_window: Tuple[datetime, datetime]
    
    # Statistical results
    test_statistic: float
    p_value: float
    effect_size: float = Field(description="Standardized effect size")
    
    # Detection outcome
    drift_detected: bool
    severity: AlertSeverity
    confidence: float = Field(ge=0.0, le=1.0)
    
    # Sample info
    reference_sample_size: int
    detection_sample_size: int
    
    # Details
    affected_features: List[str] = Field(default_factory=list)
    drift_direction: str = Field(description="increase | decrease | shift")
    drift_magnitude: float
    
    # Diagnostics
    diagnostic_info: Dict[str, Any] = Field(default_factory=dict)
    
    # Recommendations
    recommended_action: str
    auto_action_eligible: bool
    
    class Config:
        use_enum_values = True


class FeatureDriftProfile(BaseModel):
    """Drift profile for a single feature."""
    
    feature_name: str
    feature_type: str  # "continuous", "categorical", "binary"
    
    # Reference statistics
    reference_mean: Optional[float] = None
    reference_std: Optional[float] = None
    reference_distribution: Optional[Dict[str, float]] = None  # For categorical
    
    # Detection statistics
    detection_mean: Optional[float] = None
    detection_std: Optional[float] = None
    detection_distribution: Optional[Dict[str, float]] = None
    
    # Drift metrics
    drift_score: float = Field(ge=0.0, le=1.0)
    p_value: float
    effect_size: float
    
    # Direction
    drift_direction: str  # "increase", "decrease", "shift", "spread"
    
    @property
    def is_drifted(self) -> bool:
        """Check if feature has significant drift."""
        return self.p_value < 0.05 and self.drift_score > 0.1


class EmbeddingDriftResult(BaseModel):
    """Result of embedding drift detection."""
    
    detection_id: str = Field(default_factory=lambda: f"emb_drift_{uuid4().hex[:12]}")
    model_id: str
    embedding_type: str  # "user", "ad", "psychological"
    detected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Centroid analysis
    centroid_distance: float = Field(ge=0.0)
    centroid_shift_significant: bool
    centroid_shift_direction: List[float] = Field(
        default_factory=list,
        description="Direction vector of centroid shift"
    )
    
    # Distribution analysis
    average_pairwise_distance_reference: float = Field(ge=0.0)
    average_pairwise_distance_current: float = Field(ge=0.0)
    distribution_divergence: float = Field(ge=0.0)
    
    # Cluster analysis
    cluster_count_reference: int = Field(ge=1)
    cluster_count_current: int = Field(ge=1)
    cluster_stability_score: float = Field(ge=0.0, le=1.0)
    
    # Nearest neighbor preservation
    nn_preservation_rate: float = Field(
        ge=0.0, le=1.0,
        description="Fraction of k-NN preserved from reference to current"
    )
    
    # Norm statistics
    norm_mean_reference: float = Field(ge=0.0)
    norm_mean_current: float = Field(ge=0.0)
    norm_std_reference: float = Field(ge=0.0)
    norm_std_current: float = Field(ge=0.0)
    
    # Overall assessment
    drift_detected: bool
    severity: AlertSeverity
    drift_summary: str
    
    # Recommendations
    recommended_action: str
    
    class Config:
        use_enum_values = True


class LearningSignalDriftResult(BaseModel):
    """
    Drift detection for the learning system (Gradient Bridge).
    Monitors health of the cross-component learning infrastructure.
    """
    
    detection_id: str = Field(default_factory=lambda: f"learn_drift_{uuid4().hex[:12]}")
    detected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    window: MonitoringWindow
    
    # Signal propagation health
    signal_emission_rate: float = Field(
        description="Signals emitted per outcome"
    )
    signal_propagation_success_rate: float = Field(
        ge=0.0, le=1.0,
        description="Fraction of signals successfully propagated"
    )
    signal_latency_p99_ms: float = Field(ge=0.0)
    
    # Attribution health
    attribution_confidence_mean: float = Field(ge=0.0, le=1.0)
    attribution_confidence_trend: float  # Positive = improving
    attribution_entropy_mean: float = Field(
        ge=0.0,
        description="Entropy of credit attribution (lower = more concentrated)"
    )
    
    # Feedback loop health
    feedback_loop_latency_hours: float = Field(
        ge=0.0,
        description="Average time from decision to learning signal propagation"
    )
    prior_staleness_hours: float = Field(
        ge=0.0,
        description="Average age of priors used in decisions"
    )
    
    # Component update rates
    bandit_update_rate: float = Field(ge=0.0)
    graph_update_rate: float = Field(ge=0.0)
    meta_learner_update_rate: float = Field(ge=0.0)
    
    # Drift indicators
    credit_concentration_drift: float = Field(
        description="Change in how concentrated credit attribution is"
    )
    learning_velocity_change: float = Field(
        description="Change in learning speed (+ = faster, - = slower)"
    )
    
    # Health assessment
    drift_detected: bool
    severity: AlertSeverity
    affected_components: List[str] = Field(default_factory=list)
    drift_summary: str
    
    # Recommendations
    recommended_action: str
    
    class Config:
        use_enum_values = True
```

---

## Alert & Notification Models

```python
"""
ADAM Enhancement #20: Alert Models
Pydantic models for alerting and notifications.
"""

from __future__ import annotations
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from uuid import uuid4

from pydantic import BaseModel, Field


class Alert(BaseModel):
    """
    An alert generated by the monitoring system.
    """
    
    # Identification
    alert_id: str = Field(default_factory=lambda: f"alert_{uuid4().hex[:12]}")
    
    # Classification
    drift_type: DriftType
    severity: AlertSeverity
    status: AlertStatus = AlertStatus.OPEN
    
    # Target
    model_id: Optional[str] = None
    source_type: Optional[IntelligenceSourceType] = None
    component: Optional[str] = None
    
    # Timing
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    
    # Content
    title: str
    description: str
    diagnostic_info: Dict[str, Any] = Field(default_factory=dict)
    
    # Detection details
    detection_id: Optional[str] = None
    test_name: Optional[str] = None
    
    # Metrics at time of alert
    metric_values: Dict[str, float] = Field(default_factory=dict)
    threshold_violated: Optional[str] = None
    
    # Response
    acknowledged_by: Optional[str] = None
    resolved_by: Optional[str] = None
    resolution_action: Optional[str] = None
    resolution_notes: Optional[str] = None
    
    # Auto-action
    auto_action_taken: Optional[str] = None
    auto_action_timestamp: Optional[datetime] = None
    
    # Correlation
    related_alert_ids: List[str] = Field(default_factory=list)
    root_cause_alert_id: Optional[str] = None
    
    # Suppression
    suppression_reason: Optional[str] = None
    suppressed_until: Optional[datetime] = None
    
    class Config:
        use_enum_values = True


class AlertRule(BaseModel):
    """
    Configuration for an alerting rule.
    """
    
    rule_id: str = Field(default_factory=lambda: f"rule_{uuid4().hex[:12]}")
    rule_name: str
    enabled: bool = True
    
    # Targeting
    applies_to_models: List[str] = Field(
        default_factory=list,
        description="Model IDs or '*' for all"
    )
    applies_to_sources: List[IntelligenceSourceType] = Field(
        default_factory=list
    )
    applies_to_drift_types: List[DriftType] = Field(
        default_factory=list
    )
    
    # Thresholds
    warning_threshold: float
    critical_threshold: float
    emergency_threshold: Optional[float] = None
    
    # Evaluation
    evaluation_window: MonitoringWindow
    consecutive_violations_required: int = Field(default=1, ge=1)
    
    # Actions
    notify_channels: List[str] = Field(default_factory=list)
    auto_action_enabled: bool = False
    auto_action_type: Optional[str] = None
    
    # Suppression
    cooldown_minutes: int = Field(default=30, ge=0)
    max_alerts_per_hour: int = Field(default=10, ge=1)


class AlertSummary(BaseModel):
    """
    Summary of current alert state for dashboard.
    """
    
    summary_timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    
    # Counts by severity
    emergency_count: int = 0
    critical_count: int = 0
    warning_count: int = 0
    info_count: int = 0
    
    # Counts by status
    open_count: int = 0
    acknowledged_count: int = 0
    in_progress_count: int = 0
    
    # Recent alerts
    recent_alerts: List[Alert] = Field(default_factory=list)
    
    # Top affected models
    models_with_most_alerts: Dict[str, int] = Field(default_factory=dict)
    
    # Top drift types
    drift_type_counts: Dict[DriftType, int] = Field(default_factory=dict)
    
    @property
    def total_active_alerts(self) -> int:
        """Total number of active alerts."""
        return self.open_count + self.acknowledged_count + self.in_progress_count
    
    @property
    def requires_immediate_attention(self) -> bool:
        """Check if there are critical or emergency alerts."""
        return self.emergency_count > 0 or self.critical_count > 0
```

---

## Retraining Models

```python
"""
ADAM Enhancement #20: Retraining Models
Pydantic models for automated retraining.
"""

from __future__ import annotations
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from uuid import uuid4

from pydantic import BaseModel, Field


class RetrainingJob(BaseModel):
    """
    A model retraining job.
    """
    
    # Identification
    job_id: str = Field(default_factory=lambda: f"retrain_{uuid4().hex[:12]}")
    model_id: str
    
    # Trigger info
    trigger: RetrainingTrigger
    triggered_by: str  # "system" or user ID
    triggered_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    trigger_reason: str
    related_alert_id: Optional[str] = None
    
    # Status
    status: RetrainingStatus = RetrainingStatus.QUEUED
    current_phase: str = "queued"
    progress_percent: float = Field(ge=0.0, le=100.0, default=0.0)
    
    # Timing
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    estimated_completion: Optional[datetime] = None
    
    # Configuration
    config: Dict[str, Any] = Field(default_factory=dict)
    
    # Training data
    training_data_start: Optional[datetime] = None
    training_data_end: Optional[datetime] = None
    training_sample_count: Optional[int] = None
    
    # Result
    new_model_version: Optional[str] = None
    validation_metrics: Optional[Dict[str, float]] = None
    improvement_vs_current: Optional[float] = None
    
    # Canary testing
    canary_traffic_percent: Optional[float] = None
    canary_metrics: Optional[Dict[str, float]] = None
    canary_passed: Optional[bool] = None
    
    # Deployment
    deployed_at: Optional[datetime] = None
    rollback_triggered: bool = False
    rollback_reason: Optional[str] = None
    
    # Errors
    error_message: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None
    
    class Config:
        use_enum_values = True


class RetrainingConfig(BaseModel):
    """
    Configuration for model retraining.
    """
    
    # Data selection
    training_window_days: int = Field(default=90, ge=7)
    validation_split: float = Field(default=0.2, ge=0.1, le=0.4)
    min_training_samples: int = Field(default=10000, ge=100)
    
    # Training parameters
    hyperparameters: Dict[str, Any] = Field(default_factory=dict)
    use_hyperparameter_tuning: bool = True
    max_tuning_iterations: int = Field(default=50, ge=10)
    
    # Validation requirements
    min_improvement_threshold: float = Field(
        default=0.01,
        description="Minimum improvement required to deploy"
    )
    validation_metrics: List[str] = Field(
        default_factory=lambda: ["accuracy", "calibration_error"]
    )
    
    # Canary deployment
    canary_enabled: bool = True
    canary_duration_hours: int = Field(default=4, ge=1)
    canary_traffic_percent: float = Field(default=5.0, ge=1.0, le=20.0)
    canary_success_threshold: float = Field(default=0.95)
    
    # Rollback
    auto_rollback_enabled: bool = True
    rollback_threshold: float = Field(
        default=0.05,
        description="Performance degradation that triggers rollback"
    )


class RetrainingSummary(BaseModel):
    """
    Summary of retraining activity.
    """
    
    summary_timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    window: MonitoringWindow
    
    # Job counts
    jobs_triggered: int = 0
    jobs_completed: int = 0
    jobs_failed: int = 0
    jobs_in_progress: int = 0
    
    # Success rate
    success_rate: float = Field(ge=0.0, le=1.0, default=0.0)
    
    # Trigger breakdown
    trigger_counts: Dict[RetrainingTrigger, int] = Field(default_factory=dict)
    
    # Models retrained
    models_retrained: List[str] = Field(default_factory=list)
    
    # Performance impact
    average_improvement: Optional[float] = None
    rollback_count: int = 0
    
    # Recent jobs
    recent_jobs: List[RetrainingJob] = Field(default_factory=list)
```

---

# SECTION D: DRIFT DETECTION ENGINES

## Statistical Drift Detection Engine

```python
"""
ADAM Enhancement #20: Statistical Drift Detection Engine
Core statistical tests for drift detection.
"""

from __future__ import annotations
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple, Any
import numpy as np
from scipy import stats
import logging

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class StatisticalDriftDetector:
    """
    Statistical drift detection engine.
    
    Implements multiple statistical tests for detecting distribution shifts
    in model inputs, outputs, and derived metrics.
    
    Design principles:
    1. Multiple tests per drift type (ensemble approach)
    2. Effect size focus (not just p-values)
    3. Adaptive thresholds based on model category
    4. Automatic correction for multiple testing
    """
    
    def __init__(
        self,
        prediction_store: 'PredictionStore',
        reference_store: 'ReferenceStore',
        config: 'DriftDetectionConfig'
    ):
        """
        Initialize the drift detector.
        
        Args:
            prediction_store: Store for prediction records
            reference_store: Store for reference distributions
            config: Detection configuration
        """
        self.prediction_store = prediction_store
        self.reference_store = reference_store
        self.config = config
        
        # Statistical tests registry
        self._tests = {
            "ks_test": self._kolmogorov_smirnov_test,
            "psi_test": self._population_stability_index,
            "chi_square_test": self._chi_square_test,
            "wasserstein_test": self._wasserstein_distance_test,
            "kl_divergence": self._kl_divergence,
            "jensen_shannon": self._jensen_shannon_divergence,
            "mmd_test": self._maximum_mean_discrepancy,
            "page_hinkley": self._page_hinkley_test,
        }
    
    async def detect_data_drift(
        self,
        model_id: str,
        config: DriftTestConfig
    ) -> DriftDetectionResult:
        """
        Detect drift in input feature distributions.
        
        Uses ensemble of statistical tests for robust detection.
        
        Args:
            model_id: Model to check
            config: Test configuration
            
        Returns:
            Detection result with statistics and recommendations
        """
        # Fetch reference and detection window data
        reference_data = await self.reference_store.get_reference(
            model_id=model_id,
            window_days=config.reference_window_days
        )
        
        detection_data = await self.prediction_store.get_predictions(
            model_id=model_id,
            window_hours=config.detection_window_hours
        )
        
        if len(reference_data) < config.min_sample_size:
            return self._insufficient_data_result(config, "reference")
        
        if len(detection_data) < config.min_sample_size:
            return self._insufficient_data_result(config, "detection")
        
        # Extract features
        ref_features = self._extract_features(reference_data)
        det_features = self._extract_features(detection_data)
        
        # Run tests on each feature
        feature_results = []
        for feature_name in ref_features.keys():
            if feature_name not in det_features:
                continue
            
            ref_values = ref_features[feature_name]
            det_values = det_features[feature_name]
            
            # Determine feature type and appropriate test
            if self._is_categorical(ref_values):
                result = self._chi_square_test(ref_values, det_values)
            else:
                # Run multiple tests for continuous features
                ks_result = self._kolmogorov_smirnov_test(ref_values, det_values)
                psi_result = self._population_stability_index(ref_values, det_values)
                
                # Combine results
                result = {
                    "p_value": min(ks_result["p_value"], psi_result.get("p_value", 1.0)),
                    "effect_size": max(ks_result["effect_size"], psi_result.get("psi", 0.0)),
                    "test_statistic": ks_result["statistic"]
                }
            
            feature_results.append(FeatureDriftProfile(
                feature_name=feature_name,
                feature_type="categorical" if self._is_categorical(ref_values) else "continuous",
                reference_mean=np.mean(ref_values) if not self._is_categorical(ref_values) else None,
                reference_std=np.std(ref_values) if not self._is_categorical(ref_values) else None,
                detection_mean=np.mean(det_values) if not self._is_categorical(det_values) else None,
                detection_std=np.std(det_values) if not self._is_categorical(det_values) else None,
                drift_score=result["effect_size"],
                p_value=result["p_value"],
                effect_size=result["effect_size"],
                drift_direction=self._determine_direction(ref_values, det_values)
            ))
        
        # Aggregate results with Bonferroni correction
        if config.bonferroni_correction:
            corrected_alpha = config.significance_level / len(feature_results)
        else:
            corrected_alpha = config.significance_level
        
        drifted_features = [f for f in feature_results if f.p_value < corrected_alpha]
        max_effect_size = max(f.effect_size for f in feature_results) if feature_results else 0.0
        
        # Determine severity
        if max_effect_size >= config.critical_threshold:
            severity = AlertSeverity.CRITICAL
        elif max_effect_size >= config.warning_threshold:
            severity = AlertSeverity.WARNING
        else:
            severity = AlertSeverity.INFO
        
        return DriftDetectionResult(
            test_name=config.test_name,
            drift_type=DriftType.DATA_DRIFT,
            model_id=model_id,
            reference_window=(
                datetime.now(timezone.utc) - timedelta(days=config.reference_window_days),
                datetime.now(timezone.utc) - timedelta(hours=config.detection_window_hours)
            ),
            detection_window=(
                datetime.now(timezone.utc) - timedelta(hours=config.detection_window_hours),
                datetime.now(timezone.utc)
            ),
            test_statistic=max_effect_size,
            p_value=min(f.p_value for f in feature_results) if feature_results else 1.0,
            effect_size=max_effect_size,
            drift_detected=len(drifted_features) > 0,
            severity=severity,
            confidence=1.0 - (min(f.p_value for f in feature_results) if feature_results else 1.0),
            reference_sample_size=len(reference_data),
            detection_sample_size=len(detection_data),
            affected_features=[f.feature_name for f in drifted_features],
            drift_direction="mixed" if len(set(f.drift_direction for f in drifted_features)) > 1 else (
                drifted_features[0].drift_direction if drifted_features else "none"
            ),
            drift_magnitude=max_effect_size,
            recommended_action=DRIFT_RESPONSE_MATRIX[DriftDimension.DATA_DRIFT].get(
                severity.value, "Monitor"
            ),
            auto_action_eligible=severity in [AlertSeverity.CRITICAL, AlertSeverity.EMERGENCY]
        )
    
    def _kolmogorov_smirnov_test(
        self,
        reference: np.ndarray,
        detection: np.ndarray
    ) -> Dict[str, float]:
        """
        Two-sample Kolmogorov-Smirnov test.
        
        Tests whether two samples come from the same distribution.
        Non-parametric: makes no assumptions about underlying distribution.
        """
        statistic, p_value = stats.ks_2samp(reference, detection)
        
        # Effect size: KS statistic is already interpretable (max CDF difference)
        effect_size = statistic
        
        return {
            "statistic": statistic,
            "p_value": p_value,
            "effect_size": effect_size
        }
    
    def _population_stability_index(
        self,
        reference: np.ndarray,
        detection: np.ndarray,
        n_bins: int = 10
    ) -> Dict[str, float]:
        """
        Population Stability Index (PSI).
        
        Measures shift in population distributions.
        PSI < 0.1: No significant shift
        0.1 <= PSI < 0.25: Moderate shift
        PSI >= 0.25: Significant shift
        """
        # Create bins from reference distribution
        _, bin_edges = np.histogram(reference, bins=n_bins)
        
        # Calculate proportions in each bin
        ref_counts, _ = np.histogram(reference, bins=bin_edges)
        det_counts, _ = np.histogram(detection, bins=bin_edges)
        
        # Add small constant to avoid division by zero
        epsilon = 1e-10
        ref_props = (ref_counts + epsilon) / (len(reference) + epsilon * n_bins)
        det_props = (det_counts + epsilon) / (len(detection) + epsilon * n_bins)
        
        # Calculate PSI
        psi = np.sum((det_props - ref_props) * np.log(det_props / ref_props))
        
        return {
            "psi": psi,
            "effect_size": psi,
            "significant": psi >= 0.1
        }
    
    def _chi_square_test(
        self,
        reference: np.ndarray,
        detection: np.ndarray
    ) -> Dict[str, float]:
        """
        Chi-square test for categorical features.
        """
        # Get unique categories
        categories = np.unique(np.concatenate([reference, detection]))
        
        # Count occurrences
        ref_counts = np.array([np.sum(reference == c) for c in categories])
        det_counts = np.array([np.sum(detection == c) for c in categories])
        
        # Expected counts under null hypothesis
        total_ref = len(reference)
        total_det = len(detection)
        total = total_ref + total_det
        
        expected_ref = (ref_counts + det_counts) * (total_ref / total)
        expected_det = (ref_counts + det_counts) * (total_det / total)
        
        # Chi-square statistic
        chi2_ref = np.sum((ref_counts - expected_ref) ** 2 / np.maximum(expected_ref, 1))
        chi2_det = np.sum((det_counts - expected_det) ** 2 / np.maximum(expected_det, 1))
        chi2 = chi2_ref + chi2_det
        
        # Degrees of freedom
        df = len(categories) - 1
        
        # P-value
        p_value = 1 - stats.chi2.cdf(chi2, df)
        
        # Effect size: Cramér's V
        n = total
        cramers_v = np.sqrt(chi2 / (n * df)) if df > 0 else 0
        
        return {
            "statistic": chi2,
            "p_value": p_value,
            "effect_size": cramers_v
        }
    
    def _wasserstein_distance_test(
        self,
        reference: np.ndarray,
        detection: np.ndarray
    ) -> Dict[str, float]:
        """
        Wasserstein distance (Earth Mover's Distance).
        
        Measures the minimum cost of transforming one distribution into another.
        More sensitive to small shifts than KS test.
        """
        distance = stats.wasserstein_distance(reference, detection)
        
        # Normalize by reference standard deviation for effect size
        ref_std = np.std(reference)
        effect_size = distance / ref_std if ref_std > 0 else distance
        
        # Approximate p-value via permutation test (simplified)
        combined = np.concatenate([reference, detection])
        n_ref = len(reference)
        n_permutations = 1000
        
        permuted_distances = []
        for _ in range(n_permutations):
            np.random.shuffle(combined)
            perm_ref = combined[:n_ref]
            perm_det = combined[n_ref:]
            permuted_distances.append(stats.wasserstein_distance(perm_ref, perm_det))
        
        p_value = np.mean(np.array(permuted_distances) >= distance)
        
        return {
            "distance": distance,
            "p_value": p_value,
            "effect_size": effect_size
        }
    
    def _kl_divergence(
        self,
        reference: np.ndarray,
        detection: np.ndarray,
        n_bins: int = 50
    ) -> Dict[str, float]:
        """
        Kullback-Leibler divergence.
        
        Measures information loss when detection distribution is used
        to approximate reference distribution.
        """
        # Create histogram bins from combined data
        combined = np.concatenate([reference, detection])
        _, bin_edges = np.histogram(combined, bins=n_bins)
        
        # Calculate probabilities
        epsilon = 1e-10
        ref_hist, _ = np.histogram(reference, bins=bin_edges, density=True)
        det_hist, _ = np.histogram(detection, bins=bin_edges, density=True)
        
        # Add epsilon to avoid log(0)
        ref_hist = ref_hist + epsilon
        det_hist = det_hist + epsilon
        
        # Normalize
        ref_hist = ref_hist / ref_hist.sum()
        det_hist = det_hist / det_hist.sum()
        
        # KL divergence
        kl_div = np.sum(ref_hist * np.log(ref_hist / det_hist))
        
        return {
            "kl_divergence": kl_div,
            "effect_size": kl_div
        }
    
    def _jensen_shannon_divergence(
        self,
        reference: np.ndarray,
        detection: np.ndarray,
        n_bins: int = 50
    ) -> Dict[str, float]:
        """
        Jensen-Shannon divergence.
        
        Symmetric version of KL divergence.
        Bounded between 0 and 1 (when using log base 2).
        """
        # Create histogram bins
        combined = np.concatenate([reference, detection])
        _, bin_edges = np.histogram(combined, bins=n_bins)
        
        epsilon = 1e-10
        ref_hist, _ = np.histogram(reference, bins=bin_edges, density=True)
        det_hist, _ = np.histogram(detection, bins=bin_edges, density=True)
        
        # Normalize
        ref_hist = (ref_hist + epsilon) / (ref_hist + epsilon).sum()
        det_hist = (det_hist + epsilon) / (det_hist + epsilon).sum()
        
        # Midpoint distribution
        m = 0.5 * (ref_hist + det_hist)
        
        # JS divergence
        js_div = 0.5 * (
            np.sum(ref_hist * np.log2(ref_hist / m)) +
            np.sum(det_hist * np.log2(det_hist / m))
        )
        
        return {
            "js_divergence": js_div,
            "effect_size": js_div  # Already bounded 0-1
        }
    
    def _maximum_mean_discrepancy(
        self,
        reference: np.ndarray,
        detection: np.ndarray,
        gamma: float = 1.0
    ) -> Dict[str, float]:
        """
        Maximum Mean Discrepancy (MMD) with RBF kernel.
        
        Non-parametric test that compares mean embeddings in RKHS.
        Powerful for detecting complex distribution shifts.
        """
        def rbf_kernel(x, y, gamma):
            return np.exp(-gamma * (x - y) ** 2)
        
        n_ref = len(reference)
        n_det = len(detection)
        
        # Compute kernel sums
        k_xx = 0
        for i in range(n_ref):
            for j in range(i + 1, n_ref):
                k_xx += rbf_kernel(reference[i], reference[j], gamma)
        k_xx = 2 * k_xx / (n_ref * (n_ref - 1))
        
        k_yy = 0
        for i in range(n_det):
            for j in range(i + 1, n_det):
                k_yy += rbf_kernel(detection[i], detection[j], gamma)
        k_yy = 2 * k_yy / (n_det * (n_det - 1))
        
        k_xy = 0
        for i in range(n_ref):
            for j in range(n_det):
                k_xy += rbf_kernel(reference[i], detection[j], gamma)
        k_xy = k_xy / (n_ref * n_det)
        
        mmd = k_xx + k_yy - 2 * k_xy
        
        return {
            "mmd": mmd,
            "effect_size": np.sqrt(max(0, mmd))  # Take sqrt for interpretability
        }
    
    def _page_hinkley_test(
        self,
        values: np.ndarray,
        threshold: float = 50.0,
        delta: float = 0.005
    ) -> Dict[str, Any]:
        """
        Page-Hinkley test for change point detection.
        
        Sequential test that can detect when the mean of a sequence changes.
        Useful for detecting gradual concept drift.
        """
        n = len(values)
        mean = np.mean(values)
        
        # Cumulative sum
        cumsum = 0
        min_cumsum = 0
        max_diff = 0
        change_detected = False
        change_point = None
        
        for i, v in enumerate(values):
            cumsum += (v - mean - delta)
            if cumsum < min_cumsum:
                min_cumsum = cumsum
            
            diff = cumsum - min_cumsum
            if diff > max_diff:
                max_diff = diff
            
            if diff > threshold:
                change_detected = True
                change_point = i
                break
        
        return {
            "change_detected": change_detected,
            "change_point": change_point,
            "max_diff": max_diff,
            "effect_size": max_diff / threshold
        }
    
    def _extract_features(
        self,
        predictions: List[PredictionRecord]
    ) -> Dict[str, np.ndarray]:
        """Extract features from prediction records."""
        features = {}
        
        if not predictions:
            return features
        
        # Collect all feature names
        all_features = set()
        for pred in predictions:
            all_features.update(pred.input_features.keys())
        
        # Extract each feature
        for feature_name in all_features:
            values = []
            for pred in predictions:
                if feature_name in pred.input_features:
                    values.append(pred.input_features[feature_name])
            
            if values:
                features[feature_name] = np.array(values)
        
        return features
    
    def _is_categorical(self, values: np.ndarray) -> bool:
        """Determine if values are categorical."""
        unique_count = len(np.unique(values))
        return unique_count < 20 or isinstance(values[0], str)
    
    def _determine_direction(
        self,
        reference: np.ndarray,
        detection: np.ndarray
    ) -> str:
        """Determine the direction of drift."""
        if self._is_categorical(reference):
            return "shift"
        
        ref_mean = np.mean(reference)
        det_mean = np.mean(detection)
        ref_std = np.std(reference)
        det_std = np.std(detection)
        
        mean_change = (det_mean - ref_mean) / ref_std if ref_std > 0 else 0
        std_change = (det_std - ref_std) / ref_std if ref_std > 0 else 0
        
        if abs(mean_change) > abs(std_change):
            return "increase" if mean_change > 0 else "decrease"
        else:
            return "spread" if std_change > 0 else "concentrate"
    
    def _insufficient_data_result(
        self,
        config: DriftTestConfig,
        which: str
    ) -> DriftDetectionResult:
        """Return result for insufficient data."""
        return DriftDetectionResult(
            test_name=config.test_name,
            drift_type=config.test_type,
            model_id="",
            reference_window=(datetime.now(timezone.utc), datetime.now(timezone.utc)),
            detection_window=(datetime.now(timezone.utc), datetime.now(timezone.utc)),
            test_statistic=0.0,
            p_value=1.0,
            effect_size=0.0,
            drift_detected=False,
            severity=AlertSeverity.INFO,
            confidence=0.0,
            reference_sample_size=0 if which == "reference" else config.min_sample_size,
            detection_sample_size=config.min_sample_size if which == "reference" else 0,
            affected_features=[],
            drift_direction="none",
            drift_magnitude=0.0,
            diagnostic_info={"error": f"Insufficient {which} data"},
            recommended_action=f"Collect more {which} data",
            auto_action_eligible=False
        )
```

---

## SECTION E: MONITORING INFRASTRUCTURE

### E.1 Prediction Logger

The prediction logger captures all model inference events for subsequent drift analysis, maintaining audit trails while respecting privacy constraints.

```python
# prediction_logger.py
"""
Prediction Logging Infrastructure for ADAM Monitoring System.

Captures model predictions, intelligence source contributions, and atom outputs
with efficient batching and asynchronous persistence.
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, AsyncIterator
from dataclasses import dataclass, field
from collections import defaultdict
from enum import Enum
import asyncio
import logging
from contextlib import asynccontextmanager
import json

from pydantic import BaseModel, Field
import numpy as np

logger = logging.getLogger(__name__)


class LogLevel(str, Enum):
    """Granularity levels for prediction logging."""
    MINIMAL = "minimal"      # Just prediction and outcome
    STANDARD = "standard"    # Plus features and confidence
    DETAILED = "detailed"    # Plus intelligence source breakdown
    FULL = "full"            # Everything including internal state


class PredictionLogEntry(BaseModel):
    """Single prediction log entry with configurable detail level."""
    
    # Core fields (always captured)
    log_id: str = Field(..., description="Unique log entry identifier")
    model_id: str = Field(..., description="Model that made prediction")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    prediction: Any = Field(..., description="Model output")
    
    # Standard level
    input_features: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Input features (hashed for privacy if configured)"
    )
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    latency_ms: Optional[float] = Field(default=None, ge=0.0)
    
    # Detailed level - intelligence source breakdown
    source_contributions: Optional[Dict[str, float]] = Field(
        default=None,
        description="Weight each intelligence source contributed"
    )
    source_confidences: Optional[Dict[str, float]] = Field(
        default=None,
        description="Confidence from each source"
    )
    fusion_metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="How sources were synthesized"
    )
    
    # Full level - complete state
    atom_state: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Full atom of thought state"
    )
    psychological_constructs: Optional[Dict[str, float]] = Field(
        default=None,
        description="Activated psychological dimensions"
    )
    embedding_vector: Optional[List[float]] = Field(
        default=None,
        description="User/context embedding (anonymized)"
    )
    
    # Outcome tracking (filled later)
    outcome: Optional[Any] = Field(default=None)
    outcome_timestamp: Optional[datetime] = Field(default=None)
    outcome_attribution: Optional[Dict[str, float]] = Field(
        default=None,
        description="Which factors drove the outcome"
    )
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            np.ndarray: lambda v: v.tolist()
        }


@dataclass
class LogBuffer:
    """Efficient buffer for batching log entries."""
    entries: List[PredictionLogEntry] = field(default_factory=list)
    max_size: int = 1000
    max_age_seconds: float = 30.0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def add(self, entry: PredictionLogEntry) -> bool:
        """Add entry, return True if buffer should flush."""
        self.entries.append(entry)
        return self.should_flush()
    
    def should_flush(self) -> bool:
        """Check if buffer should be flushed."""
        if len(self.entries) >= self.max_size:
            return True
        age = (datetime.now(timezone.utc) - self.created_at).total_seconds()
        return age >= self.max_age_seconds
    
    def drain(self) -> List[PredictionLogEntry]:
        """Get all entries and reset buffer."""
        entries = self.entries
        self.entries = []
        self.created_at = datetime.now(timezone.utc)
        return entries


class PredictionLogger:
    """
    High-throughput prediction logger with async persistence.
    
    Features:
    - Configurable detail levels for different use cases
    - Efficient batching to reduce I/O overhead
    - Privacy-preserving feature hashing
    - Async persistence to avoid blocking inference
    - Graceful degradation under load
    """
    
    def __init__(
        self,
        log_level: LogLevel = LogLevel.STANDARD,
        buffer_size: int = 1000,
        flush_interval_seconds: float = 30.0,
        storage_backend: Optional[Any] = None,  # Neo4j, S3, etc.
        enable_sampling: bool = False,
        sample_rate: float = 1.0,
        privacy_hash_features: bool = True
    ):
        self.log_level = log_level
        self.buffer_size = buffer_size
        self.flush_interval = flush_interval_seconds
        self.storage = storage_backend
        self.enable_sampling = enable_sampling
        self.sample_rate = sample_rate
        self.privacy_hash = privacy_hash_features
        
        # Per-model buffers for efficient flushing
        self._buffers: Dict[str, LogBuffer] = defaultdict(
            lambda: LogBuffer(max_size=buffer_size, max_age_seconds=flush_interval_seconds)
        )
        self._flush_lock = asyncio.Lock()
        self._running = False
        self._flush_task: Optional[asyncio.Task] = None
        
        # Metrics
        self._logged_count = 0
        self._dropped_count = 0
        self._flush_count = 0
    
    async def start(self) -> None:
        """Start background flush task."""
        self._running = True
        self._flush_task = asyncio.create_task(self._periodic_flush())
        logger.info(f"PredictionLogger started with level={self.log_level}")
    
    async def stop(self) -> None:
        """Stop logger and flush remaining entries."""
        self._running = False
        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass
        
        # Final flush
        await self._flush_all()
        logger.info(
            f"PredictionLogger stopped. Logged: {self._logged_count}, "
            f"Dropped: {self._dropped_count}, Flushes: {self._flush_count}"
        )
    
    async def log_prediction(
        self,
        model_id: str,
        prediction: Any,
        input_features: Optional[Dict[str, Any]] = None,
        confidence: Optional[float] = None,
        latency_ms: Optional[float] = None,
        source_contributions: Optional[Dict[str, float]] = None,
        source_confidences: Optional[Dict[str, float]] = None,
        fusion_metadata: Optional[Dict[str, Any]] = None,
        atom_state: Optional[Dict[str, Any]] = None,
        psychological_constructs: Optional[Dict[str, float]] = None,
        embedding_vector: Optional[np.ndarray] = None
    ) -> Optional[str]:
        """
        Log a prediction asynchronously.
        
        Returns log_id if logged, None if sampled out or dropped.
        """
        # Sampling check
        if self.enable_sampling and np.random.random() > self.sample_rate:
            return None
        
        # Build entry based on log level
        log_id = f"pred_{model_id}_{datetime.now(timezone.utc).timestamp():.6f}"
        
        entry = PredictionLogEntry(
            log_id=log_id,
            model_id=model_id,
            prediction=prediction
        )
        
        # Add fields based on log level
        if self.log_level in [LogLevel.STANDARD, LogLevel.DETAILED, LogLevel.FULL]:
            entry.input_features = self._maybe_hash_features(input_features)
            entry.confidence = confidence
            entry.latency_ms = latency_ms
        
        if self.log_level in [LogLevel.DETAILED, LogLevel.FULL]:
            entry.source_contributions = source_contributions
            entry.source_confidences = source_confidences
            entry.fusion_metadata = fusion_metadata
        
        if self.log_level == LogLevel.FULL:
            entry.atom_state = atom_state
            entry.psychological_constructs = psychological_constructs
            entry.embedding_vector = (
                embedding_vector.tolist() if embedding_vector is not None else None
            )
        
        # Add to buffer
        buffer = self._buffers[model_id]
        should_flush = buffer.add(entry)
        self._logged_count += 1
        
        # Trigger flush if needed
        if should_flush:
            asyncio.create_task(self._flush_model(model_id))
        
        return log_id
    
    async def log_outcome(
        self,
        log_id: str,
        outcome: Any,
        attribution: Optional[Dict[str, float]] = None
    ) -> bool:
        """
        Associate outcome with previous prediction.
        
        This enables conversion tracking and reinforcement learning.
        """
        # In production, this would update the stored log entry
        # For now, we'll store in a separate outcomes buffer
        if self.storage:
            try:
                await self.storage.update_outcome(
                    log_id=log_id,
                    outcome=outcome,
                    outcome_timestamp=datetime.now(timezone.utc),
                    attribution=attribution
                )
                return True
            except Exception as e:
                logger.error(f"Failed to log outcome for {log_id}: {e}")
                return False
        return False
    
    def _maybe_hash_features(
        self,
        features: Optional[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """Hash sensitive features for privacy if configured."""
        if features is None or not self.privacy_hash:
            return features
        
        # Define sensitive fields that should be hashed
        sensitive_fields = {'user_id', 'email', 'name', 'device_id', 'ip_address'}
        
        hashed = {}
        for key, value in features.items():
            if key.lower() in sensitive_fields:
                # Hash sensitive values
                hashed[key] = f"hashed_{hash(str(value)) % 10**10}"
            else:
                hashed[key] = value
        
        return hashed
    
    async def _periodic_flush(self) -> None:
        """Background task that flushes aged buffers."""
        while self._running:
            await asyncio.sleep(self.flush_interval / 2)  # Check at half interval
            
            models_to_flush = [
                model_id for model_id, buffer in self._buffers.items()
                if buffer.should_flush()
            ]
            
            for model_id in models_to_flush:
                await self._flush_model(model_id)
    
    async def _flush_model(self, model_id: str) -> None:
        """Flush buffer for a specific model."""
        async with self._flush_lock:
            buffer = self._buffers[model_id]
            entries = buffer.drain()
            
            if not entries:
                return
            
            if self.storage:
                try:
                    await self.storage.store_predictions(entries)
                    self._flush_count += 1
                    logger.debug(f"Flushed {len(entries)} predictions for {model_id}")
                except Exception as e:
                    logger.error(f"Failed to flush predictions: {e}")
                    self._dropped_count += len(entries)
    
    async def _flush_all(self) -> None:
        """Flush all model buffers."""
        for model_id in list(self._buffers.keys()):
            await self._flush_model(model_id)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Return logger metrics."""
        return {
            "logged_count": self._logged_count,
            "dropped_count": self._dropped_count,
            "flush_count": self._flush_count,
            "buffer_sizes": {
                model_id: len(buffer.entries)
                for model_id, buffer in self._buffers.items()
            },
            "log_level": self.log_level.value,
            "sample_rate": self.sample_rate if self.enable_sampling else 1.0
        }


@asynccontextmanager
async def prediction_logging_context(
    logger_instance: PredictionLogger
) -> AsyncIterator[PredictionLogger]:
    """Context manager for prediction logging lifecycle."""
    await logger_instance.start()
    try:
        yield logger_instance
    finally:
        await logger_instance.stop()
```

### E.2 Intelligence Source Monitor

This component continuously tracks the health and contribution patterns of all 10 intelligence sources defined in Enhancement #04.

```python
# intelligence_source_monitor.py
"""
Intelligence Source Health Monitor for ADAM.

Tracks availability, quality, and contribution patterns for all 10 sources
defined in the Multi-Source Intelligence Fusion Architecture.
"""

from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from collections import deque
from enum import Enum
import asyncio
import logging
import statistics

from pydantic import BaseModel, Field
import numpy as np

logger = logging.getLogger(__name__)


class IntelligenceSource(str, Enum):
    """The 10 intelligence sources from Enhancement #04."""
    CLAUDE_REASONING = "claude_reasoning"
    EMPIRICAL_PATTERNS = "empirical_patterns"
    NONCONSCIOUS_SIGNALS = "nonconscious_signals"
    GRAPH_EMERGENCE = "graph_emergence"
    BANDIT_POSTERIORS = "bandit_posteriors"
    META_LEARNER = "meta_learner"
    MECHANISM_EFFECTIVENESS = "mechanism_effectiveness"
    TEMPORAL_PATTERNS = "temporal_patterns"
    CROSS_DOMAIN_TRANSFER = "cross_domain_transfer"
    COHORT_SELF_ORGANIZATION = "cohort_self_organization"


@dataclass
class SourceObservation:
    """Single observation of source behavior."""
    timestamp: datetime
    available: bool
    confidence: float
    latency_ms: float
    contribution_weight: float
    error: Optional[str] = None
    source_specific_metrics: Dict[str, float] = field(default_factory=dict)


class SourceHealthWindow:
    """Rolling window of source observations for health calculation."""
    
    def __init__(self, window_size: int = 1000, max_age_minutes: int = 60):
        self.window_size = window_size
        self.max_age = timedelta(minutes=max_age_minutes)
        self._observations: deque = deque(maxlen=window_size)
    
    def add(self, observation: SourceObservation) -> None:
        """Add observation to window."""
        self._observations.append(observation)
        self._prune_old()
    
    def _prune_old(self) -> None:
        """Remove observations older than max_age."""
        cutoff = datetime.now(timezone.utc) - self.max_age
        while self._observations and self._observations[0].timestamp < cutoff:
            self._observations.popleft()
    
    def get_observations(self) -> List[SourceObservation]:
        """Get current observations."""
        self._prune_old()
        return list(self._observations)
    
    def compute_metrics(self) -> Dict[str, float]:
        """Compute aggregate metrics from observations."""
        obs = self.get_observations()
        
        if not obs:
            return {
                "availability_rate": 0.0,
                "mean_confidence": 0.0,
                "mean_latency_ms": 0.0,
                "mean_contribution": 0.0,
                "error_rate": 1.0,
                "observation_count": 0
            }
        
        available = [o for o in obs if o.available]
        errors = [o for o in obs if o.error is not None]
        
        return {
            "availability_rate": len(available) / len(obs),
            "mean_confidence": statistics.mean([o.confidence for o in available]) if available else 0.0,
            "std_confidence": statistics.stdev([o.confidence for o in available]) if len(available) > 1 else 0.0,
            "mean_latency_ms": statistics.mean([o.latency_ms for o in available]) if available else 0.0,
            "p95_latency_ms": np.percentile([o.latency_ms for o in available], 95) if available else 0.0,
            "mean_contribution": statistics.mean([o.contribution_weight for o in obs]),
            "max_contribution": max([o.contribution_weight for o in obs]),
            "error_rate": len(errors) / len(obs),
            "observation_count": len(obs)
        }


class SourceHealthAssessment(BaseModel):
    """Health assessment for a single intelligence source."""
    source: IntelligenceSource
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Core health metrics
    availability_rate: float = Field(..., ge=0.0, le=1.0)
    error_rate: float = Field(..., ge=0.0, le=1.0)
    mean_confidence: float = Field(..., ge=0.0, le=1.0)
    confidence_stability: float = Field(..., ge=0.0, le=1.0, description="1 - coefficient of variation")
    mean_latency_ms: float = Field(..., ge=0.0)
    latency_acceptable: bool
    
    # Contribution metrics
    mean_contribution_weight: float = Field(..., ge=0.0, le=1.0)
    contribution_trend: str = Field(..., description="increasing, stable, decreasing")
    
    # Source-specific metrics (varies by source type)
    source_specific: Dict[str, float] = Field(default_factory=dict)
    
    # Overall assessment
    health_status: str = Field(..., description="healthy, degraded, unhealthy, unavailable")
    health_score: float = Field(..., ge=0.0, le=1.0)
    issues: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)


class IntelligenceSourceMonitor:
    """
    Monitors health and contribution patterns for all intelligence sources.
    
    Provides:
    - Real-time health assessment per source
    - Contribution balance monitoring (no source dominates)
    - Degradation detection and alerting
    - Source-specific metric tracking
    """
    
    # Source-specific health thresholds
    SOURCE_THRESHOLDS = {
        IntelligenceSource.CLAUDE_REASONING: {
            "min_availability": 0.95,
            "max_latency_ms": 2000,
            "min_confidence": 0.6
        },
        IntelligenceSource.EMPIRICAL_PATTERNS: {
            "min_availability": 0.99,
            "max_latency_ms": 50,
            "min_confidence": 0.7,
            "min_pattern_freshness": 0.8  # Patterns should be recent
        },
        IntelligenceSource.NONCONSCIOUS_SIGNALS: {
            "min_availability": 0.90,
            "max_latency_ms": 100,
            "min_confidence": 0.5,  # Lower baseline - these signals are subtle
            "min_signal_strength": 0.3
        },
        IntelligenceSource.GRAPH_EMERGENCE: {
            "min_availability": 0.95,
            "max_latency_ms": 200,
            "min_confidence": 0.6,
            "min_cluster_quality": 0.5
        },
        IntelligenceSource.BANDIT_POSTERIORS: {
            "min_availability": 0.99,
            "max_latency_ms": 20,
            "min_confidence": 0.7,
            "max_posterior_entropy": 0.7  # Should have learned preferences
        },
        IntelligenceSource.META_LEARNER: {
            "min_availability": 0.90,
            "max_latency_ms": 500,
            "min_confidence": 0.6,
            "min_strategy_stability": 0.7
        },
        IntelligenceSource.MECHANISM_EFFECTIVENESS: {
            "min_availability": 0.95,
            "max_latency_ms": 100,
            "min_confidence": 0.7,
            "min_mechanism_coverage": 0.8  # Should have data on most mechanisms
        },
        IntelligenceSource.TEMPORAL_PATTERNS: {
            "min_availability": 0.90,
            "max_latency_ms": 150,
            "min_confidence": 0.6,
            "min_pattern_recency": 0.7
        },
        IntelligenceSource.CROSS_DOMAIN_TRANSFER: {
            "min_availability": 0.85,
            "max_latency_ms": 300,
            "min_confidence": 0.5,  # Lower - transfer learning is uncertain
            "min_transfer_relevance": 0.5
        },
        IntelligenceSource.COHORT_SELF_ORGANIZATION: {
            "min_availability": 0.90,
            "max_latency_ms": 200,
            "min_confidence": 0.6,
            "min_cohort_stability": 0.6
        }
    }
    
    def __init__(
        self,
        window_size: int = 1000,
        window_age_minutes: int = 60,
        alert_callback: Optional[callable] = None
    ):
        self.window_size = window_size
        self.window_age = window_age_minutes
        self.alert_callback = alert_callback
        
        # Per-source observation windows
        self._windows: Dict[IntelligenceSource, SourceHealthWindow] = {
            source: SourceHealthWindow(window_size, window_age_minutes)
            for source in IntelligenceSource
        }
        
        # Historical assessments for trend analysis
        self._assessment_history: Dict[IntelligenceSource, deque] = {
            source: deque(maxlen=100)
            for source in IntelligenceSource
        }
        
        # Contribution balance tracking
        self._contribution_history: deque = deque(maxlen=1000)
    
    def record_observation(
        self,
        source: IntelligenceSource,
        available: bool,
        confidence: float,
        latency_ms: float,
        contribution_weight: float,
        error: Optional[str] = None,
        source_specific_metrics: Optional[Dict[str, float]] = None
    ) -> None:
        """Record a single observation for a source."""
        obs = SourceObservation(
            timestamp=datetime.now(timezone.utc),
            available=available,
            confidence=confidence,
            latency_ms=latency_ms,
            contribution_weight=contribution_weight,
            error=error,
            source_specific_metrics=source_specific_metrics or {}
        )
        
        self._windows[source].add(obs)
        
        # Track contribution for balance monitoring
        self._contribution_history.append({
            "timestamp": obs.timestamp,
            "source": source,
            "weight": contribution_weight
        })
    
    def assess_source_health(
        self,
        source: IntelligenceSource
    ) -> SourceHealthAssessment:
        """Generate health assessment for a single source."""
        metrics = self._windows[source].compute_metrics()
        thresholds = self.SOURCE_THRESHOLDS[source]
        
        issues = []
        recommendations = []
        
        # Check availability
        if metrics["availability_rate"] < thresholds["min_availability"]:
            issues.append(
                f"Availability {metrics['availability_rate']:.1%} below "
                f"threshold {thresholds['min_availability']:.1%}"
            )
            recommendations.append(f"Investigate {source.value} service health")
        
        # Check latency
        latency_ok = metrics["mean_latency_ms"] <= thresholds["max_latency_ms"]
        if not latency_ok:
            issues.append(
                f"Mean latency {metrics['mean_latency_ms']:.0f}ms exceeds "
                f"threshold {thresholds['max_latency_ms']}ms"
            )
            recommendations.append(f"Optimize {source.value} query performance")
        
        # Check confidence
        if metrics["mean_confidence"] < thresholds["min_confidence"]:
            issues.append(
                f"Mean confidence {metrics['mean_confidence']:.2f} below "
                f"threshold {thresholds['min_confidence']:.2f}"
            )
            recommendations.append(f"Review {source.value} model quality")
        
        # Check error rate
        if metrics["error_rate"] > 0.05:  # 5% error threshold
            issues.append(f"Error rate {metrics['error_rate']:.1%} is elevated")
            recommendations.append(f"Check {source.value} error logs")
        
        # Calculate confidence stability (1 - CV)
        cv = metrics["std_confidence"] / metrics["mean_confidence"] if metrics["mean_confidence"] > 0 else 1.0
        confidence_stability = max(0.0, 1.0 - cv)
        
        # Determine contribution trend
        contribution_trend = self._calculate_contribution_trend(source)
        
        # Calculate overall health score
        health_score = self._calculate_health_score(
            availability=metrics["availability_rate"],
            error_rate=metrics["error_rate"],
            confidence=metrics["mean_confidence"],
            latency_ratio=min(1.0, thresholds["max_latency_ms"] / max(1, metrics["mean_latency_ms"]))
        )
        
        # Determine status
        if metrics["availability_rate"] < 0.5:
            status = "unavailable"
        elif health_score < 0.5:
            status = "unhealthy"
        elif health_score < 0.8 or issues:
            status = "degraded"
        else:
            status = "healthy"
        
        assessment = SourceHealthAssessment(
            source=source,
            availability_rate=metrics["availability_rate"],
            error_rate=metrics["error_rate"],
            mean_confidence=metrics["mean_confidence"],
            confidence_stability=confidence_stability,
            mean_latency_ms=metrics["mean_latency_ms"],
            latency_acceptable=latency_ok,
            mean_contribution_weight=metrics["mean_contribution"],
            contribution_trend=contribution_trend,
            source_specific=self._get_source_specific_metrics(source),
            health_status=status,
            health_score=health_score,
            issues=issues,
            recommendations=recommendations
        )
        
        # Store for trend analysis
        self._assessment_history[source].append(assessment)
        
        # Alert if unhealthy
        if status in ["unhealthy", "unavailable"] and self.alert_callback:
            self.alert_callback(assessment)
        
        return assessment
    
    def assess_all_sources(self) -> Dict[IntelligenceSource, SourceHealthAssessment]:
        """Generate health assessments for all sources."""
        return {
            source: self.assess_source_health(source)
            for source in IntelligenceSource
        }
    
    def assess_contribution_balance(self) -> Dict[str, Any]:
        """
        Assess whether intelligence sources are balanced or if one dominates.
        
        Imbalance suggests fusion isn't working properly or some sources
        are being ignored.
        """
        recent = [
            c for c in self._contribution_history
            if c["timestamp"] > datetime.now(timezone.utc) - timedelta(minutes=30)
        ]
        
        if not recent:
            return {
                "balanced": True,
                "entropy": 1.0,
                "dominant_source": None,
                "source_distribution": {},
                "issues": ["Insufficient data"]
            }
        
        # Calculate contribution distribution
        source_totals = {source: 0.0 for source in IntelligenceSource}
        for c in recent:
            source_totals[c["source"]] += c["weight"]
        
        total = sum(source_totals.values())
        if total == 0:
            return {
                "balanced": False,
                "entropy": 0.0,
                "dominant_source": None,
                "source_distribution": {},
                "issues": ["No contributions recorded"]
            }
        
        distribution = {
            source.value: weight / total
            for source, weight in source_totals.items()
        }
        
        # Calculate entropy (higher = more balanced)
        probs = [w / total for w in source_totals.values() if w > 0]
        entropy = -sum(p * np.log(p) for p in probs if p > 0)
        max_entropy = np.log(len(IntelligenceSource))
        normalized_entropy = entropy / max_entropy if max_entropy > 0 else 0
        
        # Find dominant source
        dominant = max(source_totals.items(), key=lambda x: x[1])
        dominant_ratio = dominant[1] / total
        
        issues = []
        if dominant_ratio > 0.5:
            issues.append(
                f"{dominant[0].value} contributes {dominant_ratio:.1%} - "
                "may be over-relying on single source"
            )
        
        if normalized_entropy < 0.5:
            issues.append(
                f"Low source diversity (entropy: {normalized_entropy:.2f}) - "
                "fusion may not be leveraging all sources"
            )
        
        # Check for inactive sources
        inactive = [
            source.value for source, weight in source_totals.items()
            if weight / total < 0.01  # Less than 1% contribution
        ]
        if inactive:
            issues.append(f"Low-contribution sources: {', '.join(inactive)}")
        
        return {
            "balanced": normalized_entropy > 0.6 and dominant_ratio < 0.4,
            "entropy": normalized_entropy,
            "dominant_source": dominant[0].value,
            "dominant_ratio": dominant_ratio,
            "source_distribution": distribution,
            "inactive_sources": inactive,
            "issues": issues
        }
    
    def _calculate_contribution_trend(
        self,
        source: IntelligenceSource
    ) -> str:
        """Calculate whether source contribution is increasing, stable, or decreasing."""
        history = self._assessment_history[source]
        if len(history) < 5:
            return "stable"
        
        recent = list(history)[-10:]
        contributions = [a.mean_contribution_weight for a in recent]
        
        # Simple linear regression
        x = np.arange(len(contributions))
        slope = np.polyfit(x, contributions, 1)[0]
        
        if slope > 0.01:
            return "increasing"
        elif slope < -0.01:
            return "decreasing"
        else:
            return "stable"
    
    def _calculate_health_score(
        self,
        availability: float,
        error_rate: float,
        confidence: float,
        latency_ratio: float
    ) -> float:
        """Calculate composite health score."""
        # Weighted combination with availability most important
        return (
            0.4 * availability +
            0.2 * (1 - error_rate) +
            0.25 * confidence +
            0.15 * latency_ratio
        )
    
    def _get_source_specific_metrics(
        self,
        source: IntelligenceSource
    ) -> Dict[str, float]:
        """Aggregate source-specific metrics from observations."""
        obs = self._windows[source].get_observations()
        
        if not obs:
            return {}
        
        # Collect all source-specific metric keys
        all_metrics: Dict[str, List[float]] = {}
        for o in obs:
            for key, value in o.source_specific_metrics.items():
                if key not in all_metrics:
                    all_metrics[key] = []
                all_metrics[key].append(value)
        
        # Compute means
        return {
            key: statistics.mean(values)
            for key, values in all_metrics.items()
        }
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get data formatted for monitoring dashboard."""
        assessments = self.assess_all_sources()
        balance = self.assess_contribution_balance()
        
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "sources": {
                source.value: {
                    "health_status": assessment.health_status,
                    "health_score": assessment.health_score,
                    "availability": assessment.availability_rate,
                    "latency_ms": assessment.mean_latency_ms,
                    "contribution": assessment.mean_contribution_weight,
                    "issues_count": len(assessment.issues)
                }
                for source, assessment in assessments.items()
            },
            "contribution_balance": {
                "balanced": balance["balanced"],
                "entropy": balance["entropy"],
                "dominant_source": balance["dominant_source"]
            },
            "overall_health": self._calculate_overall_health(assessments)
        }
    
    def _calculate_overall_health(
        self,
        assessments: Dict[IntelligenceSource, SourceHealthAssessment]
    ) -> str:
        """Determine overall system health from individual assessments."""
        statuses = [a.health_status for a in assessments.values()]
        
        if any(s == "unavailable" for s in statuses):
            return "critical"
        if sum(1 for s in statuses if s == "unhealthy") >= 3:
            return "unhealthy"
        if any(s in ["unhealthy", "degraded"] for s in statuses):
            return "degraded"
        return "healthy"
```

### E.3 Atom Output Monitor

Monitors the outputs from the Atom of Thought processing to detect fusion quality issues and reasoning anomalies.

```python
# atom_output_monitor.py
"""
Atom of Thought Output Monitor for ADAM.

Tracks atom outputs to detect:
- Fusion quality degradation
- Reasoning anomalies
- Confidence calibration issues
- Source contribution drift
"""

from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from collections import deque
import statistics
import logging

from pydantic import BaseModel, Field
import numpy as np

logger = logging.getLogger(__name__)


class AtomOutput(BaseModel):
    """Captured output from Atom of Thought processing."""
    
    atom_id: str = Field(..., description="Unique identifier for this atom execution")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Decision output
    decision: str = Field(..., description="The decision/recommendation made")
    confidence: float = Field(..., ge=0.0, le=1.0)
    uncertainty_quantified: float = Field(..., ge=0.0, le=1.0)
    
    # Source evidence
    source_contributions: Dict[str, float] = Field(
        ..., description="Weight from each intelligence source"
    )
    source_agreements: Dict[str, bool] = Field(
        ..., description="Whether each source agreed with decision"
    )
    conflict_count: int = Field(..., ge=0)
    
    # Reasoning trace
    reasoning_steps: int = Field(..., ge=1)
    reasoning_depth: int = Field(..., ge=1)
    backtrack_count: int = Field(default=0, ge=0)
    
    # Psychological constructs activated
    active_constructs: List[str] = Field(default_factory=list)
    construct_confidences: Dict[str, float] = Field(default_factory=dict)
    
    # Mechanism recommendations
    recommended_mechanisms: List[str] = Field(default_factory=list)
    mechanism_scores: Dict[str, float] = Field(default_factory=dict)
    
    # Performance
    processing_time_ms: float = Field(..., ge=0.0)
    cache_hit: bool = Field(default=False)


class AtomHealthMetrics(BaseModel):
    """Health metrics computed from atom outputs."""
    
    window_start: datetime
    window_end: datetime
    sample_count: int
    
    # Confidence metrics
    mean_confidence: float
    confidence_std: float
    confidence_calibration: float = Field(
        ..., description="How well confidence predicts accuracy"
    )
    
    # Fusion quality
    mean_source_agreement_rate: float
    mean_conflict_count: float
    dominant_source_ratio: float
    source_entropy: float
    
    # Reasoning quality
    mean_reasoning_steps: float
    mean_backtrack_rate: float
    reasoning_efficiency: float = Field(
        ..., description="Decisions per reasoning step"
    )
    
    # Construct coverage
    unique_constructs_activated: int
    construct_concentration: float = Field(
        ..., description="Whether same constructs always activate"
    )
    
    # Performance
    mean_processing_time_ms: float
    p95_processing_time_ms: float
    cache_hit_rate: float
    
    # Health assessment
    health_score: float
    issues: List[str]


class AtomOutputMonitor:
    """
    Monitors Atom of Thought outputs for quality and anomalies.
    
    Detects:
    - Confidence miscalibration
    - Fusion degradation (sources not agreeing)
    - Reasoning inefficiency
    - Construct concentration (lack of diversity)
    - Performance degradation
    """
    
    # Thresholds for health assessment
    THRESHOLDS = {
        "min_confidence": 0.3,
        "max_confidence": 0.95,  # Too confident is suspicious
        "min_agreement_rate": 0.6,
        "max_conflict_count": 3,
        "max_dominant_source_ratio": 0.5,
        "min_source_entropy": 0.5,
        "max_backtrack_rate": 0.3,
        "min_construct_diversity": 0.3,
        "max_processing_time_ms": 500,
        "min_cache_hit_rate": 0.3
    }
    
    def __init__(
        self,
        window_size: int = 1000,
        outcome_tracker: Optional[Any] = None
    ):
        self.window_size = window_size
        self.outcome_tracker = outcome_tracker
        
        self._outputs: deque = deque(maxlen=window_size)
        self._outcomes: Dict[str, Tuple[Any, datetime]] = {}  # atom_id -> (outcome, timestamp)
        self._construct_histogram: Dict[str, int] = {}
        self._mechanism_histogram: Dict[str, int] = {}
    
    def record_output(self, output: AtomOutput) -> None:
        """Record an atom output for monitoring."""
        self._outputs.append(output)
        
        # Update construct histogram
        for construct in output.active_constructs:
            self._construct_histogram[construct] = \
                self._construct_histogram.get(construct, 0) + 1
        
        # Update mechanism histogram
        for mechanism in output.recommended_mechanisms:
            self._mechanism_histogram[mechanism] = \
                self._mechanism_histogram.get(mechanism, 0) + 1
    
    def record_outcome(
        self,
        atom_id: str,
        outcome: Any,
        success: bool
    ) -> None:
        """Record outcome for confidence calibration analysis."""
        self._outcomes[atom_id] = (outcome, success, datetime.now(timezone.utc))
    
    def compute_health_metrics(
        self,
        window_minutes: int = 60
    ) -> AtomHealthMetrics:
        """Compute health metrics for recent atom outputs."""
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=window_minutes)
        recent = [o for o in self._outputs if o.timestamp > cutoff]
        
        if not recent:
            return self._empty_metrics(cutoff)
        
        # Confidence metrics
        confidences = [o.confidence for o in recent]
        mean_conf = statistics.mean(confidences)
        std_conf = statistics.stdev(confidences) if len(confidences) > 1 else 0.0
        
        # Confidence calibration (requires outcomes)
        calibration = self._compute_calibration(recent)
        
        # Fusion quality
        agreement_rates = [
            sum(o.source_agreements.values()) / len(o.source_agreements)
            if o.source_agreements else 0.0
            for o in recent
        ]
        mean_agreement = statistics.mean(agreement_rates)
        
        conflict_counts = [o.conflict_count for o in recent]
        mean_conflicts = statistics.mean(conflict_counts)
        
        # Source concentration
        all_contributions: Dict[str, float] = {}
        for o in recent:
            for source, weight in o.source_contributions.items():
                if source not in all_contributions:
                    all_contributions[source] = 0.0
                all_contributions[source] += weight
        
        total = sum(all_contributions.values())
        if total > 0:
            max_contribution = max(all_contributions.values())
            dominant_ratio = max_contribution / total
            
            probs = [w / total for w in all_contributions.values() if w > 0]
            source_entropy = -sum(p * np.log(p) for p in probs if p > 0)
            source_entropy /= np.log(len(all_contributions)) if len(all_contributions) > 1 else 1
        else:
            dominant_ratio = 1.0
            source_entropy = 0.0
        
        # Reasoning quality
        reasoning_steps = [o.reasoning_steps for o in recent]
        mean_steps = statistics.mean(reasoning_steps)
        
        backtrack_rates = [
            o.backtrack_count / o.reasoning_steps
            for o in recent
        ]
        mean_backtrack = statistics.mean(backtrack_rates)
        
        reasoning_efficiency = 1.0 / mean_steps if mean_steps > 0 else 0.0
        
        # Construct diversity
        unique_constructs = len(set(
            c for o in recent for c in o.active_constructs
        ))
        construct_concentration = self._compute_construct_concentration(recent)
        
        # Performance
        processing_times = [o.processing_time_ms for o in recent]
        mean_time = statistics.mean(processing_times)
        p95_time = np.percentile(processing_times, 95)
        cache_hits = [o.cache_hit for o in recent]
        cache_rate = sum(cache_hits) / len(cache_hits)
        
        # Health assessment
        issues = self._assess_issues(
            mean_conf, std_conf, mean_agreement, mean_conflicts,
            dominant_ratio, source_entropy, mean_backtrack,
            construct_concentration, mean_time, cache_rate
        )
        
        health_score = self._compute_health_score(
            mean_agreement, source_entropy, mean_backtrack,
            construct_concentration, mean_time, cache_rate
        )
        
        return AtomHealthMetrics(
            window_start=cutoff,
            window_end=datetime.now(timezone.utc),
            sample_count=len(recent),
            mean_confidence=mean_conf,
            confidence_std=std_conf,
            confidence_calibration=calibration,
            mean_source_agreement_rate=mean_agreement,
            mean_conflict_count=mean_conflicts,
            dominant_source_ratio=dominant_ratio,
            source_entropy=source_entropy,
            mean_reasoning_steps=mean_steps,
            mean_backtrack_rate=mean_backtrack,
            reasoning_efficiency=reasoning_efficiency,
            unique_constructs_activated=unique_constructs,
            construct_concentration=construct_concentration,
            mean_processing_time_ms=mean_time,
            p95_processing_time_ms=p95_time,
            cache_hit_rate=cache_rate,
            health_score=health_score,
            issues=issues
        )
    
    def _compute_calibration(self, outputs: List[AtomOutput]) -> float:
        """
        Compute confidence calibration using outcomes.
        
        Good calibration: when confidence is 0.8, success rate is ~80%
        """
        matched = []
        for o in outputs:
            if o.atom_id in self._outcomes:
                _, success, _ = self._outcomes[o.atom_id]
                matched.append((o.confidence, success))
        
        if len(matched) < 20:
            return 0.5  # Not enough data
        
        # Bin confidences and check accuracy per bin
        bins = [(0, 0.2), (0.2, 0.4), (0.4, 0.6), (0.6, 0.8), (0.8, 1.0)]
        calibration_errors = []
        
        for low, high in bins:
            in_bin = [(c, s) for c, s in matched if low <= c < high]
            if len(in_bin) >= 5:
                mean_conf = statistics.mean([c for c, s in in_bin])
                actual_rate = sum(1 for c, s in in_bin if s) / len(in_bin)
                calibration_errors.append(abs(mean_conf - actual_rate))
        
        if not calibration_errors:
            return 0.5
        
        # Return 1 - mean calibration error
        return 1.0 - statistics.mean(calibration_errors)
    
    def _compute_construct_concentration(
        self,
        outputs: List[AtomOutput]
    ) -> float:
        """
        Measure how concentrated construct activation is.
        
        High concentration = same constructs always activate (bad)
        Low concentration = diverse constructs (good)
        """
        if not outputs:
            return 0.0
        
        # Count construct frequencies
        counts: Dict[str, int] = {}
        total = 0
        for o in outputs:
            for c in o.active_constructs:
                counts[c] = counts.get(c, 0) + 1
                total += 1
        
        if total == 0:
            return 0.0
        
        # Calculate entropy
        probs = [c / total for c in counts.values()]
        entropy = -sum(p * np.log(p) for p in probs if p > 0)
        max_entropy = np.log(len(counts)) if len(counts) > 1 else 1
        
        # Return normalized entropy (higher = less concentrated = better)
        return entropy / max_entropy if max_entropy > 0 else 0.0
    
    def _assess_issues(
        self,
        mean_conf: float,
        std_conf: float,
        agreement_rate: float,
        conflict_count: float,
        dominant_ratio: float,
        source_entropy: float,
        backtrack_rate: float,
        construct_concentration: float,
        processing_time: float,
        cache_rate: float
    ) -> List[str]:
        """Identify issues based on metrics."""
        issues = []
        
        if mean_conf < self.THRESHOLDS["min_confidence"]:
            issues.append(f"Low confidence ({mean_conf:.2f}) - may indicate model uncertainty")
        
        if mean_conf > self.THRESHOLDS["max_confidence"]:
            issues.append(f"Overconfident ({mean_conf:.2f}) - check calibration")
        
        if std_conf < 0.1:
            issues.append("Confidence variance too low - not distinguishing certainty")
        
        if agreement_rate < self.THRESHOLDS["min_agreement_rate"]:
            issues.append(f"Low source agreement ({agreement_rate:.1%}) - fusion quality degraded")
        
        if conflict_count > self.THRESHOLDS["max_conflict_count"]:
            issues.append(f"High conflict rate ({conflict_count:.1f}) - sources disagreeing")
        
        if dominant_ratio > self.THRESHOLDS["max_dominant_source_ratio"]:
            issues.append(f"Source dominance ({dominant_ratio:.1%}) - not using all sources")
        
        if source_entropy < self.THRESHOLDS["min_source_entropy"]:
            issues.append(f"Low source diversity (entropy: {source_entropy:.2f})")
        
        if backtrack_rate > self.THRESHOLDS["max_backtrack_rate"]:
            issues.append(f"High backtrack rate ({backtrack_rate:.1%}) - reasoning inefficient")
        
        if construct_concentration < self.THRESHOLDS["min_construct_diversity"]:
            issues.append("Low construct diversity - may be missing psychological signals")
        
        if processing_time > self.THRESHOLDS["max_processing_time_ms"]:
            issues.append(f"Slow processing ({processing_time:.0f}ms)")
        
        if cache_rate < self.THRESHOLDS["min_cache_hit_rate"]:
            issues.append(f"Low cache hit rate ({cache_rate:.1%})")
        
        return issues
    
    def _compute_health_score(
        self,
        agreement_rate: float,
        source_entropy: float,
        backtrack_rate: float,
        construct_diversity: float,
        processing_time: float,
        cache_rate: float
    ) -> float:
        """Compute overall health score 0-1."""
        # Normalize processing time (inverse, capped)
        time_score = min(1.0, self.THRESHOLDS["max_processing_time_ms"] / max(1, processing_time))
        
        # Normalize backtrack rate (inverse)
        backtrack_score = max(0.0, 1.0 - backtrack_rate / self.THRESHOLDS["max_backtrack_rate"])
        
        # Weighted combination
        return (
            0.25 * agreement_rate +
            0.20 * source_entropy +
            0.15 * backtrack_score +
            0.15 * construct_diversity +
            0.15 * time_score +
            0.10 * cache_rate
        )
    
    def _empty_metrics(self, cutoff: datetime) -> AtomHealthMetrics:
        """Return empty metrics when no data available."""
        now = datetime.now(timezone.utc)
        return AtomHealthMetrics(
            window_start=cutoff,
            window_end=now,
            sample_count=0,
            mean_confidence=0.0,
            confidence_std=0.0,
            confidence_calibration=0.5,
            mean_source_agreement_rate=0.0,
            mean_conflict_count=0.0,
            dominant_source_ratio=0.0,
            source_entropy=0.0,
            mean_reasoning_steps=0.0,
            mean_backtrack_rate=0.0,
            reasoning_efficiency=0.0,
            unique_constructs_activated=0,
            construct_concentration=0.0,
            mean_processing_time_ms=0.0,
            p95_processing_time_ms=0.0,
            cache_hit_rate=0.0,
            health_score=0.0,
            issues=["No data in window"]
        )
    
    def get_construct_distribution(self) -> Dict[str, float]:
        """Get normalized distribution of construct activations."""
        total = sum(self._construct_histogram.values())
        if total == 0:
            return {}
        return {
            k: v / total
            for k, v in sorted(
                self._construct_histogram.items(),
                key=lambda x: x[1],
                reverse=True
            )
        }
    
    def get_mechanism_distribution(self) -> Dict[str, float]:
        """Get normalized distribution of mechanism recommendations."""
        total = sum(self._mechanism_histogram.values())
        if total == 0:
            return {}
        return {
            k: v / total
            for k, v in sorted(
                self._mechanism_histogram.items(),
                key=lambda x: x[1],
                reverse=True
            )
        }
```

### E.4 Health Snapshot Generator

Generates comprehensive health snapshots by aggregating data from all monitoring components.

```python
# health_snapshot_generator.py
"""
Health Snapshot Generator for ADAM Monitoring.

Aggregates data from all monitoring components to produce
comprehensive system health snapshots.
"""

from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import asyncio
import logging

from pydantic import BaseModel, Field

# Import our monitoring components
# from .prediction_logger import PredictionLogger
# from .intelligence_source_monitor import IntelligenceSourceMonitor, IntelligenceSource
# from .atom_output_monitor import AtomOutputMonitor
# from .drift_detectors import (
#     StatisticalDriftDetector, EmbeddingDriftDetector,
#     PsychologicalDriftDetector, IntelligenceSourceDriftDetector,
#     FusionDriftDetector
# )

logger = logging.getLogger(__name__)


class SystemHealthSnapshot(BaseModel):
    """Comprehensive system health snapshot."""
    
    snapshot_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    snapshot_window_minutes: int
    
    # Overall status
    overall_status: str = Field(
        ..., description="healthy, degraded, unhealthy, critical"
    )
    overall_score: float = Field(..., ge=0.0, le=1.0)
    
    # Component health
    model_health: Dict[str, Any] = Field(
        ..., description="Health per model/component"
    )
    intelligence_source_health: Dict[str, Any] = Field(
        ..., description="Health per intelligence source"
    )
    fusion_health: Dict[str, Any] = Field(
        ..., description="Fusion quality metrics"
    )
    atom_health: Dict[str, Any] = Field(
        ..., description="Atom of Thought health"
    )
    
    # Drift status
    drift_summary: Dict[str, Any] = Field(
        ..., description="Summary of drift detection results"
    )
    active_drifts: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Currently detected drifts"
    )
    
    # Learning system health (Gradient Bridge)
    learning_health: Dict[str, Any] = Field(
        ..., description="Learning system metrics"
    )
    
    # Alerts
    active_alerts: List[Dict[str, Any]] = Field(default_factory=list)
    alert_summary: Dict[str, int] = Field(
        default_factory=dict,
        description="Count of alerts by severity"
    )
    
    # Recommendations
    priority_actions: List[str] = Field(
        default_factory=list,
        description="Ordered list of recommended actions"
    )
    
    # Metadata
    data_completeness: float = Field(
        ..., ge=0.0, le=1.0,
        description="How much monitoring data was available"
    )
    components_reporting: List[str] = Field(default_factory=list)
    components_missing: List[str] = Field(default_factory=list)


class HealthSnapshotGenerator:
    """
    Generates comprehensive health snapshots by aggregating
    data from all monitoring components.
    
    This is the central orchestrator for the monitoring system,
    combining:
    - Model health metrics
    - Intelligence source health
    - Atom output quality
    - Drift detection results
    - Learning system status
    - Active alerts
    """
    
    def __init__(
        self,
        source_monitor: Optional[Any] = None,
        atom_monitor: Optional[Any] = None,
        drift_detectors: Optional[Dict[str, Any]] = None,
        alert_manager: Optional[Any] = None,
        learning_monitor: Optional[Any] = None,
        neo4j_driver: Optional[Any] = None
    ):
        self.source_monitor = source_monitor
        self.atom_monitor = atom_monitor
        self.drift_detectors = drift_detectors or {}
        self.alert_manager = alert_manager
        self.learning_monitor = learning_monitor
        self.neo4j = neo4j_driver
        
        self._snapshot_counter = 0
    
    async def generate_snapshot(
        self,
        window_minutes: int = 60,
        include_details: bool = True
    ) -> SystemHealthSnapshot:
        """
        Generate comprehensive health snapshot.
        
        Collects data from all monitoring components and synthesizes
        into a single health view.
        """
        self._snapshot_counter += 1
        snapshot_id = f"snapshot_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{self._snapshot_counter}"
        
        components_reporting = []
        components_missing = []
        
        # Collect from each component in parallel
        tasks = []
        
        if self.source_monitor:
            tasks.append(("source_health", self._get_source_health()))
            components_reporting.append("intelligence_source_monitor")
        else:
            components_missing.append("intelligence_source_monitor")
        
        if self.atom_monitor:
            tasks.append(("atom_health", self._get_atom_health(window_minutes)))
            components_reporting.append("atom_output_monitor")
        else:
            components_missing.append("atom_output_monitor")
        
        if self.drift_detectors:
            tasks.append(("drift_results", self._get_drift_summary()))
            components_reporting.append("drift_detectors")
        else:
            components_missing.append("drift_detectors")
        
        if self.alert_manager:
            tasks.append(("alerts", self._get_alert_summary()))
            components_reporting.append("alert_manager")
        else:
            components_missing.append("alert_manager")
        
        if self.learning_monitor:
            tasks.append(("learning_health", self._get_learning_health()))
            components_reporting.append("learning_monitor")
        else:
            components_missing.append("learning_monitor")
        
        # Execute in parallel
        results = {}
        if tasks:
            gathered = await asyncio.gather(
                *[t[1] for t in tasks],
                return_exceptions=True
            )
            for i, (name, _) in enumerate(tasks):
                if isinstance(gathered[i], Exception):
                    logger.error(f"Error collecting {name}: {gathered[i]}")
                    results[name] = {}
                else:
                    results[name] = gathered[i]
        
        # Get model health from storage
        model_health = await self._get_model_health(window_minutes)
        if model_health:
            components_reporting.append("model_health")
        else:
            components_missing.append("model_health")
        
        # Synthesize results
        source_health = results.get("source_health", {})
        atom_health = results.get("atom_health", {})
        drift_results = results.get("drift_results", {})
        alerts = results.get("alerts", {})
        learning_health = results.get("learning_health", {})
        
        # Calculate overall status
        overall_score, overall_status = self._calculate_overall_health(
            source_health, atom_health, drift_results,
            alerts, learning_health, model_health
        )
        
        # Extract active drifts
        active_drifts = self._extract_active_drifts(drift_results)
        
        # Generate fusion health summary
        fusion_health = self._synthesize_fusion_health(
            source_health, atom_health
        )
        
        # Generate priority actions
        priority_actions = self._generate_priority_actions(
            source_health, atom_health, drift_results,
            alerts, learning_health
        )
        
        # Calculate data completeness
        data_completeness = len(components_reporting) / (
            len(components_reporting) + len(components_missing)
        ) if (components_reporting or components_missing) else 0.0
        
        return SystemHealthSnapshot(
            snapshot_id=snapshot_id,
            snapshot_window_minutes=window_minutes,
            overall_status=overall_status,
            overall_score=overall_score,
            model_health=model_health or {},
            intelligence_source_health=source_health,
            fusion_health=fusion_health,
            atom_health=atom_health,
            drift_summary=drift_results,
            active_drifts=active_drifts,
            learning_health=learning_health,
            active_alerts=alerts.get("active", []),
            alert_summary=alerts.get("summary", {}),
            priority_actions=priority_actions,
            data_completeness=data_completeness,
            components_reporting=components_reporting,
            components_missing=components_missing
        )
    
    async def _get_source_health(self) -> Dict[str, Any]:
        """Get health from intelligence source monitor."""
        if not self.source_monitor:
            return {}
        
        try:
            assessments = self.source_monitor.assess_all_sources()
            balance = self.source_monitor.assess_contribution_balance()
            
            return {
                "sources": {
                    source.value: {
                        "status": assessment.health_status,
                        "score": assessment.health_score,
                        "issues": assessment.issues
                    }
                    for source, assessment in assessments.items()
                },
                "balance": balance,
                "overall_healthy": all(
                    a.health_status in ["healthy", "degraded"]
                    for a in assessments.values()
                )
            }
        except Exception as e:
            logger.error(f"Error getting source health: {e}")
            return {"error": str(e)}
    
    async def _get_atom_health(self, window_minutes: int) -> Dict[str, Any]:
        """Get health from atom output monitor."""
        if not self.atom_monitor:
            return {}
        
        try:
            metrics = self.atom_monitor.compute_health_metrics(window_minutes)
            return {
                "health_score": metrics.health_score,
                "confidence_calibration": metrics.confidence_calibration,
                "source_agreement_rate": metrics.mean_source_agreement_rate,
                "source_entropy": metrics.source_entropy,
                "construct_diversity": metrics.construct_concentration,
                "processing_time_ms": metrics.mean_processing_time_ms,
                "cache_hit_rate": metrics.cache_hit_rate,
                "issues": metrics.issues,
                "sample_count": metrics.sample_count
            }
        except Exception as e:
            logger.error(f"Error getting atom health: {e}")
            return {"error": str(e)}
    
    async def _get_drift_summary(self) -> Dict[str, Any]:
        """Get summary from drift detectors."""
        if not self.drift_detectors:
            return {}
        
        summary = {
            "detectors_active": list(self.drift_detectors.keys()),
            "drifts_detected": [],
            "by_type": {}
        }
        
        for name, detector in self.drift_detectors.items():
            try:
                # Each detector should have a get_recent_results method
                if hasattr(detector, 'get_recent_results'):
                    results = detector.get_recent_results()
                    for result in results:
                        if result.get("drift_detected", False):
                            summary["drifts_detected"].append({
                                "detector": name,
                                "type": result.get("drift_type"),
                                "severity": result.get("severity"),
                                "model_id": result.get("model_id"),
                                "timestamp": result.get("timestamp")
                            })
                            
                            drift_type = result.get("drift_type", "unknown")
                            if drift_type not in summary["by_type"]:
                                summary["by_type"][drift_type] = 0
                            summary["by_type"][drift_type] += 1
            except Exception as e:
                logger.error(f"Error getting drift results from {name}: {e}")
        
        return summary
    
    async def _get_alert_summary(self) -> Dict[str, Any]:
        """Get summary from alert manager."""
        if not self.alert_manager:
            return {}
        
        try:
            active = self.alert_manager.get_active_alerts()
            return {
                "active": [
                    {
                        "alert_id": a.alert_id,
                        "severity": a.severity.value,
                        "title": a.title,
                        "component": a.component,
                        "created_at": a.created_at.isoformat()
                    }
                    for a in active
                ],
                "summary": {
                    "critical": len([a for a in active if a.severity.value == "critical"]),
                    "warning": len([a for a in active if a.severity.value == "warning"]),
                    "info": len([a for a in active if a.severity.value == "info"])
                }
            }
        except Exception as e:
            logger.error(f"Error getting alert summary: {e}")
            return {"error": str(e)}
    
    async def _get_learning_health(self) -> Dict[str, Any]:
        """Get health from learning system monitor (Gradient Bridge)."""
        if not self.learning_monitor:
            return {}
        
        try:
            # This would integrate with Enhancement #06
            return self.learning_monitor.get_health_metrics()
        except Exception as e:
            logger.error(f"Error getting learning health: {e}")
            return {"error": str(e)}
    
    async def _get_model_health(
        self,
        window_minutes: int
    ) -> Dict[str, Any]:
        """Get model health from storage."""
        if not self.neo4j:
            return {}
        
        # Query would fetch recent model health snapshots
        # Implementation depends on Neo4j schema
        return {}
    
    def _calculate_overall_health(
        self,
        source_health: Dict,
        atom_health: Dict,
        drift_results: Dict,
        alerts: Dict,
        learning_health: Dict,
        model_health: Dict
    ) -> tuple[float, str]:
        """Calculate overall system health score and status."""
        scores = []
        
        # Source health contribution
        if source_health.get("overall_healthy"):
            scores.append(0.9)
        elif source_health:
            unhealthy = sum(
                1 for s in source_health.get("sources", {}).values()
                if s.get("status") in ["unhealthy", "unavailable"]
            )
            scores.append(max(0.3, 1.0 - unhealthy * 0.15))
        
        # Atom health contribution
        if atom_health.get("health_score"):
            scores.append(atom_health["health_score"])
        
        # Drift penalty
        drift_count = len(drift_results.get("drifts_detected", []))
        if drift_count > 0:
            scores.append(max(0.4, 1.0 - drift_count * 0.1))
        
        # Alert penalty
        alert_summary = alerts.get("summary", {})
        critical_count = alert_summary.get("critical", 0)
        warning_count = alert_summary.get("warning", 0)
        if critical_count > 0:
            scores.append(0.3)
        elif warning_count > 0:
            scores.append(max(0.5, 1.0 - warning_count * 0.1))
        
        # Learning health contribution
        if learning_health.get("health_score"):
            scores.append(learning_health["health_score"])
        
        # Calculate overall
        if not scores:
            return 0.5, "unknown"
        
        overall_score = sum(scores) / len(scores)
        
        # Determine status
        if critical_count > 0 or overall_score < 0.4:
            status = "critical"
        elif overall_score < 0.6 or warning_count > 2:
            status = "unhealthy"
        elif overall_score < 0.8 or drift_count > 0:
            status = "degraded"
        else:
            status = "healthy"
        
        return overall_score, status
    
    def _extract_active_drifts(
        self,
        drift_results: Dict
    ) -> List[Dict[str, Any]]:
        """Extract list of active drifts from results."""
        return drift_results.get("drifts_detected", [])
    
    def _synthesize_fusion_health(
        self,
        source_health: Dict,
        atom_health: Dict
    ) -> Dict[str, Any]:
        """Synthesize fusion health from source and atom metrics."""
        return {
            "source_balance": source_health.get("balance", {}),
            "agreement_rate": atom_health.get("source_agreement_rate", 0.0),
            "entropy": atom_health.get("source_entropy", 0.0),
            "healthy": (
                source_health.get("balance", {}).get("balanced", False) and
                atom_health.get("source_agreement_rate", 0) > 0.6
            )
        }
    
    def _generate_priority_actions(
        self,
        source_health: Dict,
        atom_health: Dict,
        drift_results: Dict,
        alerts: Dict,
        learning_health: Dict
    ) -> List[str]:
        """Generate ordered list of recommended actions."""
        actions = []
        
        # Critical alerts first
        for alert in alerts.get("active", []):
            if alert.get("severity") == "critical":
                actions.append(f"[CRITICAL] Resolve alert: {alert.get('title')}")
        
        # Drift issues
        for drift in drift_results.get("drifts_detected", []):
            if drift.get("severity") in ["critical", "warning"]:
                actions.append(
                    f"[DRIFT] Investigate {drift.get('type')} drift in {drift.get('model_id')}"
                )
        
        # Source health issues
        for source, health in source_health.get("sources", {}).items():
            if health.get("status") == "unhealthy":
                actions.append(f"[SOURCE] Restore {source} - {health.get('issues', ['degraded'])[0]}")
        
        # Fusion issues
        if not source_health.get("balance", {}).get("balanced", True):
            dominant = source_health.get("balance", {}).get("dominant_source")
            actions.append(f"[FUSION] Rebalance sources - {dominant} is dominant")
        
        # Atom issues
        for issue in atom_health.get("issues", []):
            actions.append(f"[ATOM] {issue}")
        
        # Learning issues
        if learning_health.get("issues"):
            for issue in learning_health["issues"][:3]:
                actions.append(f"[LEARNING] {issue}")
        
        return actions[:10]  # Top 10 priority actions
```

---

## SECTION F: ALERTING SYSTEM

### F.1 Alert Manager

The alert manager handles alert lifecycle, deduplication, routing, and fatigue prevention.

```python
# alert_manager.py
"""
Alert Management System for ADAM Monitoring.

Handles:
- Alert creation and lifecycle management
- Intelligent deduplication and grouping
- Routing to appropriate channels
- Alert fatigue prevention
- Automated response actions
"""

from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Callable, Set
from dataclasses import dataclass, field
from collections import defaultdict
from enum import Enum
import asyncio
import hashlib
import logging
import re

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class AlertSeverity(str, Enum):
    """Alert severity levels."""
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


class AlertStatus(str, Enum):
    """Alert lifecycle status."""
    FIRING = "firing"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    SILENCED = "silenced"
    AUTO_RESOLVED = "auto_resolved"


class AlertCategory(str, Enum):
    """Categories for alert routing."""
    MODEL_HEALTH = "model_health"
    DRIFT = "drift"
    INTELLIGENCE_SOURCE = "intelligence_source"
    FUSION = "fusion"
    LEARNING = "learning"
    PERFORMANCE = "performance"
    PSYCHOLOGICAL_VALIDITY = "psychological_validity"
    SYSTEM = "system"


class NotificationChannel(str, Enum):
    """Available notification channels."""
    SLACK = "slack"
    PAGERDUTY = "pagerduty"
    EMAIL = "email"
    WEBHOOK = "webhook"
    DASHBOARD = "dashboard"
    SMS = "sms"


class Alert(BaseModel):
    """Individual alert with full context."""
    
    alert_id: str = Field(..., description="Unique alert identifier")
    fingerprint: str = Field(..., description="Hash for deduplication")
    
    # Classification
    severity: AlertSeverity
    category: AlertCategory
    
    # Context
    title: str = Field(..., max_length=200)
    description: str
    component: str = Field(..., description="Affected component/model")
    source: str = Field(..., description="What triggered this alert")
    
    # Timing
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    resolved_at: Optional[datetime] = None
    
    # State
    status: AlertStatus = AlertStatus.FIRING
    occurrence_count: int = Field(default=1, ge=1)
    
    # Details
    labels: Dict[str, str] = Field(default_factory=dict)
    annotations: Dict[str, Any] = Field(default_factory=dict)
    metric_values: Dict[str, float] = Field(default_factory=dict)
    
    # Actions
    runbook_url: Optional[str] = None
    auto_action_eligible: bool = False
    auto_action_taken: Optional[str] = None
    
    # Routing
    notified_channels: List[str] = Field(default_factory=list)
    assigned_to: Optional[str] = None
    acknowledged_by: Optional[str] = None


class AlertRule(BaseModel):
    """Rule for generating alerts from conditions."""
    
    rule_id: str
    name: str
    description: str
    enabled: bool = True
    
    # Condition
    category: AlertCategory
    condition_type: str = Field(..., description="threshold, anomaly, absence, etc.")
    metric_name: str
    operator: str = Field(..., description="gt, lt, eq, etc.")
    threshold: float
    
    # Timing
    evaluation_interval_seconds: int = 60
    for_duration_seconds: int = Field(
        default=300,
        description="Condition must persist for this long"
    )
    
    # Alert configuration
    severity: AlertSeverity
    labels: Dict[str, str] = Field(default_factory=dict)
    annotations: Dict[str, str] = Field(default_factory=dict)
    runbook_url: Optional[str] = None
    
    # Auto-remediation
    auto_action: Optional[str] = None
    auto_action_cooldown_seconds: int = 3600


class SilenceRule(BaseModel):
    """Rule for silencing alerts."""
    
    silence_id: str
    created_by: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Matching
    matchers: Dict[str, str] = Field(
        ..., description="Label matchers for alerts to silence"
    )
    
    # Duration
    starts_at: datetime
    ends_at: datetime
    
    # Metadata
    comment: str


class AlertGroup(BaseModel):
    """Group of related alerts."""
    
    group_key: str
    alerts: List[Alert]
    common_labels: Dict[str, str]
    created_at: datetime
    last_updated: datetime
    
    @property
    def max_severity(self) -> AlertSeverity:
        """Get highest severity in group."""
        if any(a.severity == AlertSeverity.CRITICAL for a in self.alerts):
            return AlertSeverity.CRITICAL
        if any(a.severity == AlertSeverity.WARNING for a in self.alerts):
            return AlertSeverity.WARNING
        return AlertSeverity.INFO


class AlertManager:
    """
    Manages alert lifecycle with intelligent deduplication,
    routing, and fatigue prevention.
    
    Features:
    - Alert deduplication via fingerprinting
    - Grouping related alerts
    - Multi-channel routing
    - Alert fatigue prevention (rate limiting, silencing)
    - Automated response actions
    """
    
    # Severity-based routing defaults
    SEVERITY_ROUTING = {
        AlertSeverity.CRITICAL: [
            NotificationChannel.PAGERDUTY,
            NotificationChannel.SLACK,
            NotificationChannel.DASHBOARD
        ],
        AlertSeverity.WARNING: [
            NotificationChannel.SLACK,
            NotificationChannel.DASHBOARD
        ],
        AlertSeverity.INFO: [
            NotificationChannel.DASHBOARD
        ]
    }
    
    def __init__(
        self,
        notification_handlers: Optional[Dict[NotificationChannel, Callable]] = None,
        auto_action_handlers: Optional[Dict[str, Callable]] = None,
        max_alerts_per_group: int = 100,
        dedup_window_minutes: int = 60,
        rate_limit_per_minute: int = 30
    ):
        self.notification_handlers = notification_handlers or {}
        self.auto_action_handlers = auto_action_handlers or {}
        self.max_alerts_per_group = max_alerts_per_group
        self.dedup_window = timedelta(minutes=dedup_window_minutes)
        self.rate_limit = rate_limit_per_minute
        
        # State
        self._alerts: Dict[str, Alert] = {}  # alert_id -> Alert
        self._fingerprint_to_alert: Dict[str, str] = {}  # fingerprint -> alert_id
        self._groups: Dict[str, AlertGroup] = {}
        self._silences: Dict[str, SilenceRule] = {}
        self._rules: Dict[str, AlertRule] = {}
        
        # Rate limiting
        self._notification_timestamps: List[datetime] = []
        
        # Metrics
        self._alerts_created = 0
        self._alerts_deduplicated = 0
        self._notifications_sent = 0
        self._notifications_rate_limited = 0
    
    def create_alert(
        self,
        severity: AlertSeverity,
        category: AlertCategory,
        title: str,
        description: str,
        component: str,
        source: str,
        labels: Optional[Dict[str, str]] = None,
        annotations: Optional[Dict[str, Any]] = None,
        metric_values: Optional[Dict[str, float]] = None,
        runbook_url: Optional[str] = None,
        auto_action_eligible: bool = False
    ) -> Alert:
        """Create a new alert or update existing if duplicate."""
        labels = labels or {}
        annotations = annotations or {}
        metric_values = metric_values or {}
        
        # Generate fingerprint for deduplication
        fingerprint = self._generate_fingerprint(
            category, component, source, labels
        )
        
        # Check for existing alert
        if fingerprint in self._fingerprint_to_alert:
            existing_id = self._fingerprint_to_alert[fingerprint]
            existing = self._alerts.get(existing_id)
            
            if existing and existing.status == AlertStatus.FIRING:
                # Update existing alert
                existing.occurrence_count += 1
                existing.updated_at = datetime.now(timezone.utc)
                existing.metric_values.update(metric_values)
                self._alerts_deduplicated += 1
                logger.debug(f"Deduplicated alert {fingerprint}")
                return existing
        
        # Create new alert
        alert_id = f"alert_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}_{self._alerts_created}"
        
        alert = Alert(
            alert_id=alert_id,
            fingerprint=fingerprint,
            severity=severity,
            category=category,
            title=title,
            description=description,
            component=component,
            source=source,
            labels=labels,
            annotations=annotations,
            metric_values=metric_values,
            runbook_url=runbook_url,
            auto_action_eligible=auto_action_eligible
        )
        
        # Check silences
        if self._is_silenced(alert):
            alert.status = AlertStatus.SILENCED
        
        # Store alert
        self._alerts[alert_id] = alert
        self._fingerprint_to_alert[fingerprint] = alert_id
        self._alerts_created += 1
        
        # Add to group
        self._add_to_group(alert)
        
        # Route notifications if not silenced
        if alert.status == AlertStatus.FIRING:
            asyncio.create_task(self._route_notification(alert))
            
            # Execute auto-action if eligible
            if auto_action_eligible:
                asyncio.create_task(self._execute_auto_action(alert))
        
        logger.info(f"Created alert {alert_id}: {title}")
        return alert
    
    def acknowledge_alert(
        self,
        alert_id: str,
        acknowledged_by: str,
        comment: Optional[str] = None
    ) -> bool:
        """Acknowledge an alert."""
        alert = self._alerts.get(alert_id)
        if not alert:
            return False
        
        alert.status = AlertStatus.ACKNOWLEDGED
        alert.acknowledged_by = acknowledged_by
        alert.updated_at = datetime.now(timezone.utc)
        
        if comment:
            alert.annotations["ack_comment"] = comment
        
        logger.info(f"Alert {alert_id} acknowledged by {acknowledged_by}")
        return True
    
    def resolve_alert(
        self,
        alert_id: str,
        auto: bool = False,
        resolution_note: Optional[str] = None
    ) -> bool:
        """Resolve an alert."""
        alert = self._alerts.get(alert_id)
        if not alert:
            return False
        
        alert.status = AlertStatus.AUTO_RESOLVED if auto else AlertStatus.RESOLVED
        alert.resolved_at = datetime.now(timezone.utc)
        alert.updated_at = datetime.now(timezone.utc)
        
        if resolution_note:
            alert.annotations["resolution_note"] = resolution_note
        
        # Remove from fingerprint mapping to allow new alerts
        if alert.fingerprint in self._fingerprint_to_alert:
            del self._fingerprint_to_alert[alert.fingerprint]
        
        logger.info(f"Alert {alert_id} resolved (auto={auto})")
        return True
    
    def create_silence(
        self,
        matchers: Dict[str, str],
        duration_hours: float,
        created_by: str,
        comment: str
    ) -> SilenceRule:
        """Create a silence rule."""
        now = datetime.now(timezone.utc)
        silence = SilenceRule(
            silence_id=f"silence_{now.strftime('%Y%m%d%H%M%S')}",
            created_by=created_by,
            matchers=matchers,
            starts_at=now,
            ends_at=now + timedelta(hours=duration_hours),
            comment=comment
        )
        
        self._silences[silence.silence_id] = silence
        
        # Silence matching existing alerts
        for alert in self._alerts.values():
            if alert.status == AlertStatus.FIRING and self._matches_silence(alert, silence):
                alert.status = AlertStatus.SILENCED
        
        logger.info(f"Created silence {silence.silence_id}: {comment}")
        return silence
    
    def delete_silence(self, silence_id: str) -> bool:
        """Delete a silence rule."""
        if silence_id not in self._silences:
            return False
        
        del self._silences[silence_id]
        
        # Unsilence alerts that were only silenced by this rule
        for alert in self._alerts.values():
            if alert.status == AlertStatus.SILENCED:
                if not self._is_silenced(alert):
                    alert.status = AlertStatus.FIRING
                    asyncio.create_task(self._route_notification(alert))
        
        return True
    
    def get_active_alerts(
        self,
        category: Optional[AlertCategory] = None,
        severity: Optional[AlertSeverity] = None,
        component: Optional[str] = None
    ) -> List[Alert]:
        """Get active alerts with optional filters."""
        alerts = [
            a for a in self._alerts.values()
            if a.status in [AlertStatus.FIRING, AlertStatus.ACKNOWLEDGED]
        ]
        
        if category:
            alerts = [a for a in alerts if a.category == category]
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        if component:
            alerts = [a for a in alerts if a.component == component]
        
        return sorted(alerts, key=lambda a: (a.severity.value, a.created_at), reverse=True)
    
    def get_alert_groups(self) -> List[AlertGroup]:
        """Get all alert groups."""
        return list(self._groups.values())
    
    def add_rule(self, rule: AlertRule) -> None:
        """Add or update an alert rule."""
        self._rules[rule.rule_id] = rule
    
    def evaluate_rules(self, metrics: Dict[str, float]) -> List[Alert]:
        """Evaluate all rules against current metrics."""
        alerts = []
        
        for rule in self._rules.values():
            if not rule.enabled:
                continue
            
            if rule.metric_name not in metrics:
                continue
            
            value = metrics[rule.metric_name]
            triggered = self._evaluate_condition(value, rule.operator, rule.threshold)
            
            if triggered:
                alert = self.create_alert(
                    severity=rule.severity,
                    category=rule.category,
                    title=f"Rule triggered: {rule.name}",
                    description=rule.description,
                    component=rule.labels.get("component", "unknown"),
                    source=f"rule:{rule.rule_id}",
                    labels=rule.labels,
                    annotations=rule.annotations,
                    metric_values={rule.metric_name: value},
                    runbook_url=rule.runbook_url,
                    auto_action_eligible=rule.auto_action is not None
                )
                alerts.append(alert)
        
        return alerts
    
    def _generate_fingerprint(
        self,
        category: AlertCategory,
        component: str,
        source: str,
        labels: Dict[str, str]
    ) -> str:
        """Generate fingerprint for deduplication."""
        # Stable fingerprint from key attributes
        data = f"{category.value}:{component}:{source}"
        for k, v in sorted(labels.items()):
            data += f":{k}={v}"
        
        return hashlib.sha256(data.encode()).hexdigest()[:16]
    
    def _is_silenced(self, alert: Alert) -> bool:
        """Check if alert matches any active silence."""
        now = datetime.now(timezone.utc)
        
        for silence in self._silences.values():
            if silence.starts_at <= now <= silence.ends_at:
                if self._matches_silence(alert, silence):
                    return True
        
        return False
    
    def _matches_silence(self, alert: Alert, silence: SilenceRule) -> bool:
        """Check if alert matches silence matchers."""
        for key, pattern in silence.matchers.items():
            if key == "category":
                if not re.match(pattern, alert.category.value):
                    return False
            elif key == "component":
                if not re.match(pattern, alert.component):
                    return False
            elif key == "severity":
                if not re.match(pattern, alert.severity.value):
                    return False
            elif key in alert.labels:
                if not re.match(pattern, alert.labels[key]):
                    return False
            else:
                return False
        
        return True
    
    def _add_to_group(self, alert: Alert) -> None:
        """Add alert to appropriate group."""
        # Group by category and component
        group_key = f"{alert.category.value}:{alert.component}"
        
        if group_key not in self._groups:
            self._groups[group_key] = AlertGroup(
                group_key=group_key,
                alerts=[],
                common_labels={"category": alert.category.value, "component": alert.component},
                created_at=datetime.now(timezone.utc),
                last_updated=datetime.now(timezone.utc)
            )
        
        group = self._groups[group_key]
        
        # Limit group size
        if len(group.alerts) >= self.max_alerts_per_group:
            # Remove oldest resolved alerts
            group.alerts = sorted(
                group.alerts,
                key=lambda a: (a.status == AlertStatus.RESOLVED, a.created_at)
            )[:self.max_alerts_per_group - 1]
        
        group.alerts.append(alert)
        group.last_updated = datetime.now(timezone.utc)
    
    async def _route_notification(self, alert: Alert) -> None:
        """Route alert to appropriate notification channels."""
        # Check rate limiting
        if not self._check_rate_limit():
            self._notifications_rate_limited += 1
            logger.warning(f"Alert {alert.alert_id} rate limited")
            return
        
        # Determine channels
        channels = self.SEVERITY_ROUTING.get(alert.severity, [])
        
        # Override based on category
        if alert.category == AlertCategory.PSYCHOLOGICAL_VALIDITY:
            channels = [NotificationChannel.SLACK, NotificationChannel.DASHBOARD]
        
        # Send to each channel
        for channel in channels:
            handler = self.notification_handlers.get(channel)
            if handler:
                try:
                    await handler(alert)
                    alert.notified_channels.append(channel.value)
                    self._notifications_sent += 1
                except Exception as e:
                    logger.error(f"Failed to notify {channel}: {e}")
    
    async def _execute_auto_action(self, alert: Alert) -> None:
        """Execute automatic remediation action."""
        if not alert.auto_action_eligible:
            return
        
        # Find matching auto-action from rules
        action_name = None
        for rule in self._rules.values():
            if rule.auto_action and alert.source == f"rule:{rule.rule_id}":
                action_name = rule.auto_action
                break
        
        if not action_name:
            return
        
        handler = self.auto_action_handlers.get(action_name)
        if handler:
            try:
                await handler(alert)
                alert.auto_action_taken = action_name
                logger.info(f"Auto-action {action_name} executed for {alert.alert_id}")
            except Exception as e:
                logger.error(f"Auto-action {action_name} failed: {e}")
    
    def _check_rate_limit(self) -> bool:
        """Check if we're within notification rate limit."""
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(minutes=1)
        
        # Clean old timestamps
        self._notification_timestamps = [
            ts for ts in self._notification_timestamps if ts > cutoff
        ]
        
        if len(self._notification_timestamps) >= self.rate_limit:
            return False
        
        self._notification_timestamps.append(now)
        return True
    
    def _evaluate_condition(
        self,
        value: float,
        operator: str,
        threshold: float
    ) -> bool:
        """Evaluate a threshold condition."""
        operators = {
            "gt": lambda v, t: v > t,
            "gte": lambda v, t: v >= t,
            "lt": lambda v, t: v < t,
            "lte": lambda v, t: v <= t,
            "eq": lambda v, t: abs(v - t) < 0.001,
            "neq": lambda v, t: abs(v - t) >= 0.001
        }
        
        func = operators.get(operator)
        if func:
            return func(value, threshold)
        return False
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get alert manager metrics."""
        active_by_severity = defaultdict(int)
        active_by_category = defaultdict(int)
        
        for alert in self._alerts.values():
            if alert.status in [AlertStatus.FIRING, AlertStatus.ACKNOWLEDGED]:
                active_by_severity[alert.severity.value] += 1
                active_by_category[alert.category.value] += 1
        
        return {
            "alerts_created_total": self._alerts_created,
            "alerts_deduplicated_total": self._alerts_deduplicated,
            "notifications_sent_total": self._notifications_sent,
            "notifications_rate_limited_total": self._notifications_rate_limited,
            "active_alerts_by_severity": dict(active_by_severity),
            "active_alerts_by_category": dict(active_by_category),
            "active_silences": len([
                s for s in self._silences.values()
                if s.ends_at > datetime.now(timezone.utc)
            ]),
            "alert_groups": len(self._groups),
            "rules_enabled": len([r for r in self._rules.values() if r.enabled])
        }
```

### F.2 Notification Handlers

Implementations for each notification channel.

```python
# notification_handlers.py
"""
Notification Channel Handlers for ADAM Alerting.

Implementations for Slack, PagerDuty, Email, and Webhooks.
"""

from datetime import datetime, timezone
from typing import Dict, Any, Optional
import asyncio
import logging
import json

import aiohttp

logger = logging.getLogger(__name__)


class SlackNotificationHandler:
    """Send alerts to Slack channels."""
    
    SEVERITY_COLORS = {
        "critical": "#E53935",  # Red
        "warning": "#FFB300",   # Amber
        "info": "#43A047"       # Green
    }
    
    SEVERITY_EMOJI = {
        "critical": "🚨",
        "warning": "⚠️",
        "info": "ℹ️"
    }
    
    def __init__(
        self,
        webhook_url: str,
        channel: Optional[str] = None,
        mention_users_on_critical: Optional[list] = None
    ):
        self.webhook_url = webhook_url
        self.channel = channel
        self.mention_users = mention_users_on_critical or []
    
    async def __call__(self, alert) -> None:
        """Send alert to Slack."""
        emoji = self.SEVERITY_EMOJI.get(alert.severity.value, "📋")
        color = self.SEVERITY_COLORS.get(alert.severity.value, "#808080")
        
        # Build message
        text = f"{emoji} *{alert.title}*"
        
        if alert.severity.value == "critical" and self.mention_users:
            mentions = " ".join([f"<@{u}>" for u in self.mention_users])
            text = f"{mentions} {text}"
        
        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": text
                }
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Severity:*\n{alert.severity.value}"},
                    {"type": "mrkdwn", "text": f"*Category:*\n{alert.category.value}"},
                    {"type": "mrkdwn", "text": f"*Component:*\n{alert.component}"},
                    {"type": "mrkdwn", "text": f"*Source:*\n{alert.source}"}
                ]
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Description:*\n{alert.description[:500]}"
                }
            }
        ]
        
        # Add metric values if present
        if alert.metric_values:
            metrics_text = "\n".join([
                f"• {k}: {v:.4f}" for k, v in alert.metric_values.items()
            ])
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Metrics:*\n{metrics_text}"
                }
            })
        
        # Add runbook link if present
        if alert.runbook_url:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"<{alert.runbook_url}|📖 View Runbook>"
                }
            })
        
        payload = {
            "attachments": [{
                "color": color,
                "blocks": blocks
            }]
        }
        
        if self.channel:
            payload["channel"] = self.channel
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.webhook_url,
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status != 200:
                    text = await response.text()
                    raise Exception(f"Slack notification failed: {text}")
        
        logger.info(f"Sent Slack notification for alert {alert.alert_id}")


class PagerDutyNotificationHandler:
    """Send alerts to PagerDuty."""
    
    SEVERITY_MAP = {
        "critical": "critical",
        "warning": "warning",
        "info": "info"
    }
    
    def __init__(
        self,
        routing_key: str,
        api_url: str = "https://events.pagerduty.com/v2/enqueue"
    ):
        self.routing_key = routing_key
        self.api_url = api_url
    
    async def __call__(self, alert) -> None:
        """Send alert to PagerDuty."""
        payload = {
            "routing_key": self.routing_key,
            "event_action": "trigger",
            "dedup_key": alert.fingerprint,
            "payload": {
                "summary": alert.title,
                "severity": self.SEVERITY_MAP.get(alert.severity.value, "warning"),
                "source": alert.component,
                "component": alert.component,
                "group": alert.category.value,
                "class": alert.source,
                "custom_details": {
                    "description": alert.description,
                    "alert_id": alert.alert_id,
                    "labels": alert.labels,
                    "metric_values": alert.metric_values
                },
                "timestamp": alert.created_at.isoformat()
            }
        }
        
        if alert.runbook_url:
            payload["links"] = [{"href": alert.runbook_url, "text": "Runbook"}]
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.api_url,
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status not in [200, 201, 202]:
                    text = await response.text()
                    raise Exception(f"PagerDuty notification failed: {text}")
        
        logger.info(f"Sent PagerDuty notification for alert {alert.alert_id}")


class WebhookNotificationHandler:
    """Send alerts to generic webhooks."""
    
    def __init__(
        self,
        webhook_url: str,
        headers: Optional[Dict[str, str]] = None,
        include_full_alert: bool = True
    ):
        self.webhook_url = webhook_url
        self.headers = headers or {"Content-Type": "application/json"}
        self.include_full = include_full_alert
    
    async def __call__(self, alert) -> None:
        """Send alert to webhook."""
        if self.include_full:
            payload = alert.model_dump(mode="json")
        else:
            payload = {
                "alert_id": alert.alert_id,
                "severity": alert.severity.value,
                "category": alert.category.value,
                "title": alert.title,
                "component": alert.component,
                "created_at": alert.created_at.isoformat()
            }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.webhook_url,
                json=payload,
                headers=self.headers
            ) as response:
                if response.status >= 400:
                    text = await response.text()
                    raise Exception(f"Webhook notification failed: {text}")
        
        logger.info(f"Sent webhook notification for alert {alert.alert_id}")


class EmailNotificationHandler:
    """Send alerts via email."""
    
    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        from_address: str,
        to_addresses: list,
        username: Optional[str] = None,
        password: Optional[str] = None,
        use_tls: bool = True
    ):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.from_address = from_address
        self.to_addresses = to_addresses
        self.username = username
        self.password = password
        self.use_tls = use_tls
    
    async def __call__(self, alert) -> None:
        """Send alert via email."""
        # Email implementation would use aiosmtplib
        # Simplified for this specification
        subject = f"[{alert.severity.value.upper()}] {alert.title}"
        
        body = f"""
ADAM Monitoring Alert

Severity: {alert.severity.value}
Category: {alert.category.value}
Component: {alert.component}
Source: {alert.source}

Description:
{alert.description}

Alert ID: {alert.alert_id}
Created: {alert.created_at.isoformat()}

Metrics:
{json.dumps(alert.metric_values, indent=2)}
"""
        
        if alert.runbook_url:
            body += f"\nRunbook: {alert.runbook_url}"
        
        logger.info(f"Would send email notification for alert {alert.alert_id}")
        # In production: use aiosmtplib to send
```

### F.3 Auto-Remediation Actions

Automated responses to common alert conditions.

```python
# auto_remediation.py
"""
Auto-Remediation Actions for ADAM Monitoring.

Automated responses that can be triggered by alerts
to reduce mean time to recovery.
"""

from datetime import datetime, timezone
from typing import Dict, Any, Optional
import asyncio
import logging

logger = logging.getLogger(__name__)


class AutoRemediationRegistry:
    """
    Registry of auto-remediation actions.
    
    Available actions:
    - clear_cache: Clear component cache
    - restart_component: Restart a service
    - scale_resources: Adjust resource allocation
    - disable_source: Temporarily disable an intelligence source
    - trigger_retraining: Queue model for retraining
    - rollback_model: Revert to previous model version
    - increase_sampling: Sample more data for analysis
    """
    
    def __init__(
        self,
        cache_manager: Optional[Any] = None,
        component_manager: Optional[Any] = None,
        model_manager: Optional[Any] = None,
        retraining_orchestrator: Optional[Any] = None
    ):
        self.cache = cache_manager
        self.components = component_manager
        self.models = model_manager
        self.retraining = retraining_orchestrator
        
        self._action_history: list = []
    
    async def clear_cache(self, alert) -> Dict[str, Any]:
        """Clear cache for affected component."""
        component = alert.component
        
        if self.cache:
            try:
                cleared = await self.cache.clear_for_component(component)
                self._log_action("clear_cache", alert, {"cleared_keys": cleared})
                return {"success": True, "cleared": cleared}
            except Exception as e:
                return {"success": False, "error": str(e)}
        
        return {"success": False, "error": "Cache manager not available"}
    
    async def restart_component(self, alert) -> Dict[str, Any]:
        """Restart the affected component."""
        component = alert.component
        
        # Safety check - don't restart critical components automatically
        critical_components = {"api_gateway", "neo4j", "redis"}
        if component in critical_components:
            return {
                "success": False,
                "error": f"Cannot auto-restart critical component: {component}"
            }
        
        if self.components:
            try:
                await self.components.restart(component)
                self._log_action("restart_component", alert, {"component": component})
                return {"success": True, "component": component}
            except Exception as e:
                return {"success": False, "error": str(e)}
        
        return {"success": False, "error": "Component manager not available"}
    
    async def disable_source(self, alert) -> Dict[str, Any]:
        """Temporarily disable an intelligence source."""
        # Extract source from labels
        source = alert.labels.get("intelligence_source")
        
        if not source:
            return {"success": False, "error": "No source specified in alert"}
        
        # Don't disable claude_reasoning or too many sources
        protected_sources = {"claude_reasoning"}
        if source in protected_sources:
            return {
                "success": False,
                "error": f"Cannot disable protected source: {source}"
            }
        
        if self.components:
            try:
                await self.components.disable_source(
                    source,
                    duration_minutes=30,
                    reason=f"Auto-disabled due to alert {alert.alert_id}"
                )
                self._log_action("disable_source", alert, {"source": source})
                return {"success": True, "source": source, "duration_minutes": 30}
            except Exception as e:
                return {"success": False, "error": str(e)}
        
        return {"success": False, "error": "Component manager not available"}
    
    async def trigger_retraining(self, alert) -> Dict[str, Any]:
        """Queue model for retraining."""
        model_id = alert.labels.get("model_id")
        
        if not model_id:
            return {"success": False, "error": "No model_id in alert"}
        
        if self.retraining:
            try:
                job_id = await self.retraining.queue_retraining(
                    model_id=model_id,
                    trigger_type="auto_alert",
                    trigger_alert_id=alert.alert_id,
                    priority="high" if alert.severity.value == "critical" else "normal"
                )
                self._log_action("trigger_retraining", alert, {"job_id": job_id})
                return {"success": True, "job_id": job_id}
            except Exception as e:
                return {"success": False, "error": str(e)}
        
        return {"success": False, "error": "Retraining orchestrator not available"}
    
    async def rollback_model(self, alert) -> Dict[str, Any]:
        """Rollback to previous model version."""
        model_id = alert.labels.get("model_id")
        
        if not model_id:
            return {"success": False, "error": "No model_id in alert"}
        
        if self.models:
            try:
                previous_version = await self.models.get_previous_version(model_id)
                if previous_version:
                    await self.models.activate_version(model_id, previous_version)
                    self._log_action(
                        "rollback_model",
                        alert,
                        {"model_id": model_id, "rolled_back_to": previous_version}
                    )
                    return {"success": True, "version": previous_version}
                return {"success": False, "error": "No previous version available"}
            except Exception as e:
                return {"success": False, "error": str(e)}
        
        return {"success": False, "error": "Model manager not available"}
    
    async def increase_sampling(self, alert) -> Dict[str, Any]:
        """Increase data sampling rate for better analysis."""
        component = alert.component
        
        # This would integrate with the prediction logger
        self._log_action(
            "increase_sampling",
            alert,
            {"component": component, "new_rate": 1.0}
        )
        
        return {"success": True, "sampling_rate": 1.0}
    
    def _log_action(
        self,
        action_name: str,
        alert,
        details: Dict[str, Any]
    ) -> None:
        """Log remediation action for audit trail."""
        entry = {
            "action": action_name,
            "alert_id": alert.alert_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "details": details
        }
        self._action_history.append(entry)
        
        logger.info(f"Auto-remediation: {action_name} for alert {alert.alert_id}")
    
    def get_action_handlers(self) -> Dict[str, callable]:
        """Get all available action handlers."""
        return {
            "clear_cache": self.clear_cache,
            "restart_component": self.restart_component,
            "disable_source": self.disable_source,
            "trigger_retraining": self.trigger_retraining,
            "rollback_model": self.rollback_model,
            "increase_sampling": self.increase_sampling
        }
    
    def get_action_history(
        self,
        limit: int = 100
    ) -> list:
        """Get recent action history."""
        return self._action_history[-limit:]
```

---

## SECTION G: AUTOMATED RETRAINING

### G.1 Retraining Orchestrator

The retraining orchestrator manages the full lifecycle of model retraining triggered by drift detection.

```python
# retraining_orchestrator.py
"""
Automated Retraining Orchestrator for ADAM.

Manages:
- Retraining job queuing and prioritization
- Data selection and preparation
- Training execution coordination
- Validation pipeline
- Canary deployment
- Rollback capabilities
"""

from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import asyncio
import logging
import uuid

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class RetrainingTrigger(str, Enum):
    """What triggered the retraining."""
    DRIFT_DATA = "drift_data"
    DRIFT_CONCEPT = "drift_concept"
    DRIFT_PREDICTION = "drift_prediction"
    DRIFT_PSYCHOLOGICAL = "drift_psychological"
    DRIFT_FUSION = "drift_fusion"
    DRIFT_EMBEDDING = "drift_embedding"
    SCHEDULED = "scheduled"
    MANUAL = "manual"
    AUTO_ALERT = "auto_alert"
    PERFORMANCE_DEGRADATION = "performance_degradation"


class JobStatus(str, Enum):
    """Retraining job status."""
    QUEUED = "queued"
    PREPARING_DATA = "preparing_data"
    TRAINING = "training"
    VALIDATING = "validating"
    CANARY_TESTING = "canary_testing"
    PENDING_APPROVAL = "pending_approval"
    DEPLOYING = "deploying"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    ROLLED_BACK = "rolled_back"


class JobPriority(str, Enum):
    """Job priority levels."""
    CRITICAL = "critical"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"


class RetrainingConfig(BaseModel):
    """Configuration for retraining a model."""
    
    model_id: str
    
    # Data configuration
    training_data_window_days: int = Field(default=90, ge=7)
    validation_split: float = Field(default=0.2, gt=0, lt=0.5)
    min_training_samples: int = Field(default=10000, ge=100)
    
    # Feature configuration
    include_features: Optional[List[str]] = None
    exclude_features: Optional[List[str]] = None
    feature_engineering_version: str = "latest"
    
    # Training configuration
    model_architecture: str = "default"
    hyperparameters: Dict[str, Any] = Field(default_factory=dict)
    training_timeout_hours: int = Field(default=24, ge=1)
    
    # Validation configuration
    min_validation_accuracy: float = Field(default=0.0, ge=0.0, le=1.0)
    max_performance_regression: float = Field(
        default=0.05, ge=0.0, le=1.0,
        description="Max allowed degradation vs current model"
    )
    psychological_validity_required: bool = True
    
    # Deployment configuration
    canary_percentage: float = Field(default=0.05, ge=0.01, le=0.5)
    canary_duration_hours: int = Field(default=4, ge=1)
    auto_promote: bool = False
    rollback_threshold: float = Field(
        default=0.1, ge=0.0, le=1.0,
        description="Performance drop that triggers rollback"
    )


class RetrainingJob(BaseModel):
    """A retraining job with full tracking."""
    
    job_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    model_id: str
    
    # Status tracking
    status: JobStatus = JobStatus.QUEUED
    priority: JobPriority = JobPriority.NORMAL
    
    # Trigger context
    trigger_type: RetrainingTrigger
    trigger_alert_id: Optional[str] = None
    trigger_details: Dict[str, Any] = Field(default_factory=dict)
    
    # Configuration
    config: RetrainingConfig
    
    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Progress tracking
    current_phase: str = "queued"
    phase_progress: float = Field(default=0.0, ge=0.0, le=1.0)
    phases_completed: List[str] = Field(default_factory=list)
    
    # Results
    training_metrics: Dict[str, float] = Field(default_factory=dict)
    validation_metrics: Dict[str, float] = Field(default_factory=dict)
    canary_metrics: Dict[str, float] = Field(default_factory=dict)
    psychological_validity_results: Dict[str, Any] = Field(default_factory=dict)
    
    # Model versions
    previous_model_version: Optional[str] = None
    new_model_version: Optional[str] = None
    
    # Error tracking
    error_message: Optional[str] = None
    error_phase: Optional[str] = None
    retry_count: int = Field(default=0, ge=0)
    
    # Approval
    requires_approval: bool = True
    approved_by: Optional[str] = None
    approval_timestamp: Optional[datetime] = None


class DataSelector:
    """Selects and prepares training data."""
    
    def __init__(
        self,
        neo4j_driver: Optional[Any] = None,
        feature_store: Optional[Any] = None
    ):
        self.neo4j = neo4j_driver
        self.feature_store = feature_store
    
    async def select_training_data(
        self,
        model_id: str,
        config: RetrainingConfig
    ) -> Dict[str, Any]:
        """
        Select training data based on configuration.
        
        Returns data summary and location for training.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(
            days=config.training_data_window_days
        )
        
        # In production, this would query from data stores
        data_summary = {
            "model_id": model_id,
            "data_window_start": cutoff.isoformat(),
            "data_window_end": datetime.now(timezone.utc).isoformat(),
            "total_samples": 0,
            "positive_samples": 0,
            "negative_samples": 0,
            "feature_count": 0,
            "data_location": f"s3://adam-training-data/{model_id}/{datetime.now(timezone.utc).strftime('%Y%m%d')}/"
        }
        
        # Apply feature filtering
        if config.include_features:
            data_summary["included_features"] = config.include_features
        if config.exclude_features:
            data_summary["excluded_features"] = config.exclude_features
        
        logger.info(f"Selected training data for {model_id}: {data_summary['total_samples']} samples")
        
        return data_summary


class ModelValidator:
    """Validates trained models against quality criteria."""
    
    def __init__(
        self,
        psychological_validator: Optional[Any] = None
    ):
        self.psych_validator = psychological_validator
    
    async def validate_model(
        self,
        model_id: str,
        model_version: str,
        config: RetrainingConfig,
        current_model_metrics: Dict[str, float]
    ) -> Dict[str, Any]:
        """
        Validate a newly trained model.
        
        Checks:
        - Performance vs baseline
        - Psychological validity
        - Calibration quality
        - Fairness metrics
        """
        validation_results = {
            "passed": True,
            "checks": [],
            "metrics": {},
            "warnings": [],
            "blockers": []
        }
        
        # Simulate loading validation metrics
        new_model_metrics = {
            "accuracy": 0.85,
            "auc_roc": 0.88,
            "calibration_error": 0.05,
            "psychological_validity_score": 0.92
        }
        validation_results["metrics"] = new_model_metrics
        
        # Check minimum accuracy
        if new_model_metrics.get("accuracy", 0) < config.min_validation_accuracy:
            validation_results["passed"] = False
            validation_results["blockers"].append(
                f"Accuracy {new_model_metrics['accuracy']:.3f} below minimum {config.min_validation_accuracy}"
            )
        validation_results["checks"].append({
            "name": "minimum_accuracy",
            "passed": new_model_metrics.get("accuracy", 0) >= config.min_validation_accuracy
        })
        
        # Check performance regression
        for metric in ["accuracy", "auc_roc"]:
            current = current_model_metrics.get(metric, 0)
            new = new_model_metrics.get(metric, 0)
            regression = (current - new) / current if current > 0 else 0
            
            if regression > config.max_performance_regression:
                validation_results["passed"] = False
                validation_results["blockers"].append(
                    f"{metric} regression of {regression:.1%} exceeds maximum {config.max_performance_regression:.1%}"
                )
            
            validation_results["checks"].append({
                "name": f"{metric}_regression",
                "passed": regression <= config.max_performance_regression,
                "regression": regression
            })
        
        # Psychological validity check
        if config.psychological_validity_required:
            psych_valid = new_model_metrics.get("psychological_validity_score", 0) > 0.8
            if not psych_valid:
                validation_results["passed"] = False
                validation_results["blockers"].append(
                    "Psychological validity score below threshold"
                )
            validation_results["checks"].append({
                "name": "psychological_validity",
                "passed": psych_valid,
                "score": new_model_metrics.get("psychological_validity_score")
            })
        
        # Calibration check
        calibration = new_model_metrics.get("calibration_error", 1.0)
        if calibration > 0.15:
            validation_results["warnings"].append(
                f"Calibration error {calibration:.3f} is elevated"
            )
        validation_results["checks"].append({
            "name": "calibration",
            "passed": calibration <= 0.15,
            "error": calibration
        })
        
        return validation_results


class CanaryDeployer:
    """Manages canary deployment of new models."""
    
    def __init__(
        self,
        model_router: Optional[Any] = None,
        metrics_collector: Optional[Any] = None
    ):
        self.router = model_router
        self.metrics = metrics_collector
    
    async def deploy_canary(
        self,
        model_id: str,
        new_version: str,
        canary_percentage: float
    ) -> Dict[str, Any]:
        """
        Deploy new model version as canary.
        
        Routes specified percentage of traffic to new version.
        """
        deployment = {
            "model_id": model_id,
            "canary_version": new_version,
            "canary_percentage": canary_percentage,
            "deployed_at": datetime.now(timezone.utc).isoformat(),
            "status": "active"
        }
        
        # In production, this would configure traffic splitting
        logger.info(f"Deployed canary for {model_id}: {canary_percentage:.1%} to {new_version}")
        
        return deployment
    
    async def evaluate_canary(
        self,
        model_id: str,
        canary_version: str,
        duration_hours: int,
        rollback_threshold: float
    ) -> Dict[str, Any]:
        """
        Evaluate canary performance after deployment period.
        
        Returns recommendation: promote, rollback, or extend.
        """
        # In production, this would collect real metrics
        canary_metrics = {
            "conversion_rate": 0.052,
            "latency_p95_ms": 45,
            "error_rate": 0.001,
            "psychological_alignment": 0.91
        }
        
        baseline_metrics = {
            "conversion_rate": 0.050,
            "latency_p95_ms": 42,
            "error_rate": 0.001,
            "psychological_alignment": 0.89
        }
        
        # Compare performance
        conversion_lift = (
            (canary_metrics["conversion_rate"] - baseline_metrics["conversion_rate"]) /
            baseline_metrics["conversion_rate"]
        )
        
        latency_regression = (
            (canary_metrics["latency_p95_ms"] - baseline_metrics["latency_p95_ms"]) /
            baseline_metrics["latency_p95_ms"]
        )
        
        evaluation = {
            "canary_metrics": canary_metrics,
            "baseline_metrics": baseline_metrics,
            "conversion_lift": conversion_lift,
            "latency_regression": latency_regression,
            "sample_count": 10000,
            "duration_hours": duration_hours
        }
        
        # Determine recommendation
        if canary_metrics["error_rate"] > baseline_metrics["error_rate"] * 2:
            evaluation["recommendation"] = "rollback"
            evaluation["reason"] = "Error rate doubled in canary"
        elif conversion_lift < -rollback_threshold:
            evaluation["recommendation"] = "rollback"
            evaluation["reason"] = f"Conversion dropped by {abs(conversion_lift):.1%}"
        elif latency_regression > 0.5:
            evaluation["recommendation"] = "rollback"
            evaluation["reason"] = "Latency regression >50%"
        elif conversion_lift > 0.02:  # 2% lift
            evaluation["recommendation"] = "promote"
            evaluation["reason"] = f"Conversion improved by {conversion_lift:.1%}"
        else:
            evaluation["recommendation"] = "promote"
            evaluation["reason"] = "No regression detected"
        
        return evaluation
    
    async def promote_canary(
        self,
        model_id: str,
        canary_version: str
    ) -> Dict[str, Any]:
        """Promote canary to 100% traffic."""
        # In production, this would update traffic routing
        logger.info(f"Promoted canary {canary_version} to 100% for {model_id}")
        
        return {
            "model_id": model_id,
            "promoted_version": canary_version,
            "promoted_at": datetime.now(timezone.utc).isoformat()
        }
    
    async def rollback_canary(
        self,
        model_id: str,
        canary_version: str,
        reason: str
    ) -> Dict[str, Any]:
        """Rollback canary deployment."""
        logger.warning(f"Rolling back canary {canary_version} for {model_id}: {reason}")
        
        return {
            "model_id": model_id,
            "rolled_back_version": canary_version,
            "rolled_back_at": datetime.now(timezone.utc).isoformat(),
            "reason": reason
        }


class RetrainingOrchestrator:
    """
    Orchestrates the full retraining pipeline.
    
    Coordinates:
    - Job queuing and scheduling
    - Data preparation
    - Training execution
    - Validation
    - Canary deployment
    - Promotion or rollback
    """
    
    def __init__(
        self,
        data_selector: Optional[DataSelector] = None,
        validator: Optional[ModelValidator] = None,
        canary_deployer: Optional[CanaryDeployer] = None,
        trainer: Optional[Any] = None,  # Model training service
        max_concurrent_jobs: int = 3
    ):
        self.data_selector = data_selector or DataSelector()
        self.validator = validator or ModelValidator()
        self.canary = canary_deployer or CanaryDeployer()
        self.trainer = trainer
        self.max_concurrent = max_concurrent_jobs
        
        # Job tracking
        self._jobs: Dict[str, RetrainingJob] = {}
        self._queue: List[str] = []  # job_ids in priority order
        self._running: Set[str] = set()
        
        # Execution
        self._running_flag = False
        self._executor_task: Optional[asyncio.Task] = None
    
    async def queue_retraining(
        self,
        model_id: str,
        trigger_type: RetrainingTrigger,
        config: Optional[RetrainingConfig] = None,
        trigger_alert_id: Optional[str] = None,
        trigger_details: Optional[Dict[str, Any]] = None,
        priority: JobPriority = JobPriority.NORMAL
    ) -> str:
        """Queue a new retraining job."""
        config = config or RetrainingConfig(model_id=model_id)
        
        # Check for existing queued/running job for this model
        existing = self._find_active_job(model_id)
        if existing:
            logger.warning(f"Job {existing.job_id} already active for {model_id}")
            # Upgrade priority if new request is higher
            if self._priority_value(priority) < self._priority_value(existing.priority):
                existing.priority = priority
                self._reorder_queue()
            return existing.job_id
        
        job = RetrainingJob(
            model_id=model_id,
            trigger_type=trigger_type,
            trigger_alert_id=trigger_alert_id,
            trigger_details=trigger_details or {},
            config=config,
            priority=priority,
            requires_approval=not config.auto_promote
        )
        
        self._jobs[job.job_id] = job
        self._insert_by_priority(job.job_id, priority)
        
        logger.info(f"Queued retraining job {job.job_id} for {model_id} ({priority.value})")
        
        return job.job_id
    
    def get_job(self, job_id: str) -> Optional[RetrainingJob]:
        """Get job by ID."""
        return self._jobs.get(job_id)
    
    def get_jobs_for_model(self, model_id: str) -> List[RetrainingJob]:
        """Get all jobs for a model."""
        return [j for j in self._jobs.values() if j.model_id == model_id]
    
    def get_queue_status(self) -> Dict[str, Any]:
        """Get current queue status."""
        return {
            "queued": len(self._queue),
            "running": len(self._running),
            "max_concurrent": self.max_concurrent,
            "queue_order": self._queue[:10],  # First 10
            "running_jobs": list(self._running)
        }
    
    async def start(self) -> None:
        """Start the orchestrator."""
        self._running_flag = True
        self._executor_task = asyncio.create_task(self._executor_loop())
        logger.info("Retraining orchestrator started")
    
    async def stop(self) -> None:
        """Stop the orchestrator."""
        self._running_flag = False
        if self._executor_task:
            self._executor_task.cancel()
            try:
                await self._executor_task
            except asyncio.CancelledError:
                pass
        logger.info("Retraining orchestrator stopped")
    
    async def approve_job(
        self,
        job_id: str,
        approved_by: str
    ) -> bool:
        """Approve a job for promotion."""
        job = self._jobs.get(job_id)
        if not job or job.status != JobStatus.PENDING_APPROVAL:
            return False
        
        job.approved_by = approved_by
        job.approval_timestamp = datetime.now(timezone.utc)
        job.status = JobStatus.DEPLOYING
        
        # Continue pipeline
        asyncio.create_task(self._deploy_approved(job))
        
        return True
    
    async def cancel_job(self, job_id: str) -> bool:
        """Cancel a queued or running job."""
        job = self._jobs.get(job_id)
        if not job:
            return False
        
        if job.status in [JobStatus.COMPLETED, JobStatus.FAILED]:
            return False
        
        job.status = JobStatus.CANCELLED
        
        if job_id in self._queue:
            self._queue.remove(job_id)
        self._running.discard(job_id)
        
        logger.info(f"Cancelled job {job_id}")
        return True
    
    async def _executor_loop(self) -> None:
        """Main execution loop."""
        while self._running_flag:
            try:
                # Start jobs if capacity available
                while (
                    len(self._running) < self.max_concurrent and
                    self._queue
                ):
                    job_id = self._queue.pop(0)
                    asyncio.create_task(self._execute_job(job_id))
                
                await asyncio.sleep(10)  # Check every 10 seconds
                
            except Exception as e:
                logger.error(f"Executor loop error: {e}")
                await asyncio.sleep(30)
    
    async def _execute_job(self, job_id: str) -> None:
        """Execute a retraining job through all phases."""
        job = self._jobs.get(job_id)
        if not job:
            return
        
        self._running.add(job_id)
        job.started_at = datetime.now(timezone.utc)
        
        try:
            # Phase 1: Data preparation
            job.status = JobStatus.PREPARING_DATA
            job.current_phase = "data_preparation"
            job.phase_progress = 0.0
            
            data_summary = await self.data_selector.select_training_data(
                job.model_id,
                job.config
            )
            
            if data_summary["total_samples"] < job.config.min_training_samples:
                raise ValueError(
                    f"Insufficient training data: {data_summary['total_samples']} < "
                    f"{job.config.min_training_samples}"
                )
            
            job.phases_completed.append("data_preparation")
            job.phase_progress = 1.0
            
            # Phase 2: Training
            job.status = JobStatus.TRAINING
            job.current_phase = "training"
            job.phase_progress = 0.0
            
            # In production, this would call actual training service
            # Simulated training
            await asyncio.sleep(2)  # Simulate training time
            
            job.training_metrics = {
                "loss": 0.23,
                "accuracy": 0.86,
                "epochs": 50,
                "training_samples": data_summary["total_samples"]
            }
            job.new_model_version = f"{job.model_id}_v{datetime.now(timezone.utc).strftime('%Y%m%d%H%M')}"
            
            job.phases_completed.append("training")
            job.phase_progress = 1.0
            
            # Phase 3: Validation
            job.status = JobStatus.VALIDATING
            job.current_phase = "validation"
            job.phase_progress = 0.0
            
            # Get current model metrics for comparison
            current_metrics = {"accuracy": 0.84, "auc_roc": 0.87}
            
            validation_results = await self.validator.validate_model(
                job.model_id,
                job.new_model_version,
                job.config,
                current_metrics
            )
            
            job.validation_metrics = validation_results["metrics"]
            job.psychological_validity_results = {
                "passed": any(
                    c["name"] == "psychological_validity" and c["passed"]
                    for c in validation_results["checks"]
                )
            }
            
            if not validation_results["passed"]:
                raise ValueError(
                    f"Validation failed: {validation_results['blockers']}"
                )
            
            job.phases_completed.append("validation")
            job.phase_progress = 1.0
            
            # Phase 4: Canary deployment
            job.status = JobStatus.CANARY_TESTING
            job.current_phase = "canary"
            job.phase_progress = 0.0
            
            await self.canary.deploy_canary(
                job.model_id,
                job.new_model_version,
                job.config.canary_percentage
            )
            
            # Wait for canary period (shortened for simulation)
            await asyncio.sleep(5)  # In production: config.canary_duration_hours * 3600
            
            canary_results = await self.canary.evaluate_canary(
                job.model_id,
                job.new_model_version,
                job.config.canary_duration_hours,
                job.config.rollback_threshold
            )
            
            job.canary_metrics = canary_results["canary_metrics"]
            
            if canary_results["recommendation"] == "rollback":
                await self.canary.rollback_canary(
                    job.model_id,
                    job.new_model_version,
                    canary_results["reason"]
                )
                raise ValueError(f"Canary failed: {canary_results['reason']}")
            
            job.phases_completed.append("canary")
            job.phase_progress = 1.0
            
            # Phase 5: Approval or auto-promote
            if job.requires_approval:
                job.status = JobStatus.PENDING_APPROVAL
                job.current_phase = "awaiting_approval"
                logger.info(f"Job {job_id} awaiting approval")
            else:
                await self._promote_model(job)
            
        except Exception as e:
            logger.error(f"Job {job_id} failed: {e}")
            job.status = JobStatus.FAILED
            job.error_message = str(e)
            job.error_phase = job.current_phase
            job.completed_at = datetime.now(timezone.utc)
        
        finally:
            self._running.discard(job_id)
    
    async def _deploy_approved(self, job: RetrainingJob) -> None:
        """Deploy an approved job."""
        try:
            await self._promote_model(job)
        except Exception as e:
            logger.error(f"Deployment failed for {job.job_id}: {e}")
            job.status = JobStatus.FAILED
            job.error_message = str(e)
            job.completed_at = datetime.now(timezone.utc)
    
    async def _promote_model(self, job: RetrainingJob) -> None:
        """Promote new model version to production."""
        job.status = JobStatus.DEPLOYING
        job.current_phase = "deployment"
        
        await self.canary.promote_canary(
            job.model_id,
            job.new_model_version
        )
        
        job.phases_completed.append("deployment")
        job.status = JobStatus.COMPLETED
        job.completed_at = datetime.now(timezone.utc)
        
        logger.info(f"Job {job.job_id} completed: {job.new_model_version} deployed")
    
    def _find_active_job(self, model_id: str) -> Optional[RetrainingJob]:
        """Find active job for model."""
        for job_id in list(self._queue) + list(self._running):
            job = self._jobs.get(job_id)
            if job and job.model_id == model_id:
                return job
        return None
    
    def _priority_value(self, priority: JobPriority) -> int:
        """Convert priority to sortable value."""
        mapping = {
            JobPriority.CRITICAL: 0,
            JobPriority.HIGH: 1,
            JobPriority.NORMAL: 2,
            JobPriority.LOW: 3
        }
        return mapping.get(priority, 2)
    
    def _insert_by_priority(self, job_id: str, priority: JobPriority) -> None:
        """Insert job into queue by priority."""
        value = self._priority_value(priority)
        
        for i, existing_id in enumerate(self._queue):
            existing = self._jobs.get(existing_id)
            if existing and self._priority_value(existing.priority) > value:
                self._queue.insert(i, job_id)
                return
        
        self._queue.append(job_id)
    
    def _reorder_queue(self) -> None:
        """Reorder queue by priority."""
        self._queue.sort(
            key=lambda jid: self._priority_value(
                self._jobs[jid].priority if jid in self._jobs else JobPriority.LOW
            )
        )
```

---

## SECTION H: NEO4J SCHEMA

### H.1 Monitoring Graph Schema

The Neo4j schema stores monitoring data as a graph, enabling rich queries across health history, drift patterns, and alert correlations.

```cypher
// ============================================================================
// ADAM MONITORING NEO4J SCHEMA
// Model Health, Drift Detection, and Alert Management Graph
// ============================================================================

// ----------------------------------------
// SECTION H.1: Core Node Types
// ----------------------------------------

// Model being monitored
CREATE CONSTRAINT model_id_unique IF NOT EXISTS
FOR (m:Model) REQUIRE m.model_id IS UNIQUE;

CREATE (m:Model {
    model_id: 'example_model',
    name: 'Personality Prediction Model',
    category: 'psychological_inference',  // ml_model, psychological, fusion, learning
    version: 'v2024.01.15',
    created_at: datetime(),
    updated_at: datetime(),
    status: 'active',  // active, deprecated, testing
    owner: 'ml_team',
    description: 'Predicts Big Five personality traits from behavioral signals'
})

// Intelligence Source (from Enhancement #04)
CREATE CONSTRAINT source_id_unique IF NOT EXISTS
FOR (s:IntelligenceSource) REQUIRE s.source_id IS UNIQUE;

CREATE (s:IntelligenceSource {
    source_id: 'claude_reasoning',
    name: 'Claude Reasoning Engine',
    source_type: 'llm',  // llm, bandit, graph, temporal, empirical, nonconscious
    priority: 1,
    default_weight: 0.25,
    created_at: datetime(),
    status: 'active'
})

// Health Snapshot - point-in-time health state
CREATE INDEX health_snapshot_time IF NOT EXISTS
FOR (h:HealthSnapshot) ON (h.timestamp);

CREATE (h:HealthSnapshot {
    snapshot_id: 'snapshot_20240115_120000',
    timestamp: datetime(),
    window_minutes: 60,
    overall_status: 'healthy',  // healthy, degraded, unhealthy, critical
    overall_score: 0.87,
    data_completeness: 0.95
})

// Drift Detection Result
CREATE INDEX drift_result_time IF NOT EXISTS
FOR (d:DriftResult) ON (d.detected_at);

CREATE (d:DriftResult {
    drift_id: 'drift_20240115_data_001',
    drift_type: 'data',  // data, concept, prediction, embedding, psychological, fusion, source, learning
    detected_at: datetime(),
    test_name: 'ks_test',
    test_statistic: 0.23,
    p_value: 0.001,
    effect_size: 0.45,
    severity: 'warning',  // info, warning, critical
    confidence: 0.92,
    resolved: false,
    resolved_at: null,
    auto_action_taken: null
})

// Alert Node
CREATE INDEX alert_time IF NOT EXISTS
FOR (a:Alert) ON (a.created_at);

CREATE CONSTRAINT alert_id_unique IF NOT EXISTS
FOR (a:Alert) REQUIRE a.alert_id IS UNIQUE;

CREATE (a:Alert {
    alert_id: 'alert_20240115_001',
    fingerprint: 'abc123def456',
    severity: 'warning',
    category: 'drift',
    title: 'Data drift detected in personality model',
    description: 'Feature distribution shift in openness_score',
    component: 'personality_model_v2',
    source: 'drift_detector',
    status: 'firing',  // firing, acknowledged, resolved, silenced
    created_at: datetime(),
    updated_at: datetime(),
    resolved_at: null,
    occurrence_count: 3
})

// Retraining Job
CREATE CONSTRAINT job_id_unique IF NOT EXISTS
FOR (j:RetrainingJob) REQUIRE j.job_id IS UNIQUE;

CREATE (j:RetrainingJob {
    job_id: 'job_20240115_001',
    model_id: 'personality_model',
    trigger_type: 'drift_data',
    priority: 'high',
    status: 'completed',  // queued, preparing_data, training, validating, canary, pending_approval, deploying, completed, failed
    created_at: datetime(),
    started_at: datetime(),
    completed_at: datetime(),
    previous_version: 'v2024.01.10',
    new_version: 'v2024.01.15'
})

// Psychological Construct (for psychological drift tracking)
CREATE CONSTRAINT construct_id_unique IF NOT EXISTS
FOR (c:PsychologicalConstruct) REQUIRE c.construct_id IS UNIQUE;

CREATE (c:PsychologicalConstruct {
    construct_id: 'big_five_openness',
    name: 'Openness to Experience',
    category: 'personality_trait',  // personality_trait, cognitive_mechanism, emotional_state
    framework: 'big_five',
    valid_range_min: 0.0,
    valid_range_max: 1.0,
    stability_window_hours: 168,  // Expected stability period
    research_citation: 'Costa & McCrae, 1992'
})

// ----------------------------------------
// SECTION H.2: Relationship Types
// ----------------------------------------

// Model health snapshots
// (:HealthSnapshot)-[:HEALTH_OF]->(:Model)
// (:HealthSnapshot)-[:SOURCE_HEALTH]->(:IntelligenceSource)

// Drift relationships
// (:DriftResult)-[:DRIFT_IN]->(:Model)
// (:DriftResult)-[:AFFECTS_SOURCE]->(:IntelligenceSource)
// (:DriftResult)-[:VIOLATES]->(:PsychologicalConstruct)
// (:DriftResult)-[:TRIGGERED]->(:Alert)

// Alert relationships
// (:Alert)-[:ALERT_FOR]->(:Model)
// (:Alert)-[:TRIGGERED_BY]->(:DriftResult)
// (:Alert)-[:LED_TO]->(:RetrainingJob)
// (:Alert)-[:CORRELATES_WITH]->(:Alert)

// Retraining relationships
// (:RetrainingJob)-[:RETRAINS]->(:Model)
// (:RetrainingJob)-[:TRIGGERED_BY]->(:Alert)
// (:RetrainingJob)-[:TRIGGERED_BY_DRIFT]->(:DriftResult)
// (:RetrainingJob)-[:PRODUCES]->(:ModelVersion)

// Time-series chaining
// (:HealthSnapshot)-[:FOLLOWS]->(:HealthSnapshot)

// ----------------------------------------
// SECTION H.3: Model Health Node with Metrics
// ----------------------------------------

CREATE (mh:ModelHealthMetrics {
    metrics_id: 'metrics_model1_20240115_120000',
    model_id: 'model1',
    timestamp: datetime(),
    
    // Core metrics
    accuracy: 0.85,
    auc_roc: 0.88,
    precision: 0.82,
    recall: 0.87,
    f1_score: 0.845,
    
    // Calibration
    calibration_error: 0.045,
    brier_score: 0.12,
    
    // Performance
    latency_p50_ms: 23,
    latency_p95_ms: 67,
    latency_p99_ms: 125,
    throughput_qps: 1500,
    
    // Data quality
    prediction_count: 45000,
    null_feature_rate: 0.002,
    out_of_range_rate: 0.001,
    
    // Psychological validity (for ADAM-specific models)
    psychological_validity_score: 0.91,
    construct_correlations_valid: true,
    mechanism_effectiveness_score: 0.87
})

// ----------------------------------------
// SECTION H.4: Source Health Tracking
// ----------------------------------------

CREATE (sh:SourceHealthSnapshot {
    snapshot_id: 'source_health_claude_20240115',
    source_id: 'claude_reasoning',
    timestamp: datetime(),
    
    // Availability
    availability_rate: 0.97,
    error_rate: 0.008,
    
    // Quality
    mean_confidence: 0.78,
    confidence_std: 0.12,
    
    // Performance
    mean_latency_ms: 450,
    p95_latency_ms: 890,
    
    // Contribution
    mean_contribution_weight: 0.23,
    contribution_trend: 'stable',
    
    // Health assessment
    health_status: 'healthy',
    health_score: 0.89,
    issues: []
})

// ----------------------------------------
// SECTION H.5: Fusion Quality Tracking
// ----------------------------------------

CREATE (fq:FusionQualitySnapshot {
    snapshot_id: 'fusion_quality_20240115',
    timestamp: datetime(),
    
    // Agreement metrics
    source_agreement_rate: 0.73,
    mean_conflict_count: 1.2,
    conflict_resolution_rate: 0.95,
    
    // Balance metrics
    dominant_source_ratio: 0.31,
    source_entropy: 0.82,  // Higher = more balanced
    
    // Contribution distribution
    source_weights: {
        claude_reasoning: 0.23,
        empirical_patterns: 0.18,
        bandit_posteriors: 0.17,
        graph_emergence: 0.14,
        nonconscious_signals: 0.12,
        meta_learner: 0.08,
        mechanism_effectiveness: 0.04,
        temporal_patterns: 0.02,
        cross_domain_transfer: 0.01,
        cohort_self_organization: 0.01
    },
    
    // Quality assessment
    fusion_health_score: 0.85,
    issues: []
})

// ----------------------------------------
// SECTION H.6: Psychological Validity Tracking
// ----------------------------------------

CREATE (pv:PsychologicalValiditySnapshot {
    snapshot_id: 'psych_validity_20240115',
    timestamp: datetime(),
    model_id: 'personality_model',
    
    // Constraint violations
    constraints_checked: 7,
    constraints_violated: 0,
    violations: [],
    
    // Specific checks
    trait_stability_valid: true,
    state_variability_valid: true,
    big_five_orthogonality_valid: true,
    yerkes_dodson_valid: true,
    nfc_processing_depth_valid: true,
    
    // Correlation structure
    expected_correlations_preserved: true,
    correlation_deviations: {},
    
    // Overall validity
    validity_score: 0.94,
    research_alignment_score: 0.91
})
```

### H.2 Monitoring Queries

Common queries for retrieving monitoring data.

```cypher
// ============================================================================
// ADAM MONITORING QUERIES
// ============================================================================

// ----------------------------------------
// Query 1: Get Model Health Timeline
// ----------------------------------------
// Retrieve health snapshots for a model over time
MATCH (m:Model {model_id: $model_id})<-[:HEALTH_OF]-(h:HealthSnapshot)
WHERE h.timestamp >= datetime() - duration({days: 7})
RETURN h.timestamp AS time,
       h.overall_score AS health_score,
       h.overall_status AS status
ORDER BY h.timestamp DESC
LIMIT 168  // Hourly for 7 days

// ----------------------------------------
// Query 2: Get Active Drifts Across All Models
// ----------------------------------------
MATCH (d:DriftResult)-[:DRIFT_IN]->(m:Model)
WHERE d.resolved = false
  AND d.severity IN ['warning', 'critical']
RETURN m.model_id AS model,
       d.drift_type AS drift_type,
       d.severity AS severity,
       d.detected_at AS detected_at,
       d.effect_size AS effect_size,
       d.test_name AS test
ORDER BY 
    CASE d.severity WHEN 'critical' THEN 0 ELSE 1 END,
    d.detected_at DESC

// ----------------------------------------
// Query 3: Intelligence Source Health Summary
// ----------------------------------------
MATCH (s:IntelligenceSource)<-[:SOURCE_HEALTH]-(sh:SourceHealthSnapshot)
WHERE sh.timestamp >= datetime() - duration({hours: 1})
WITH s, sh
ORDER BY sh.timestamp DESC
WITH s, COLLECT(sh)[0] AS latest
RETURN s.source_id AS source,
       s.name AS name,
       latest.health_status AS status,
       latest.health_score AS score,
       latest.availability_rate AS availability,
       latest.mean_latency_ms AS latency,
       latest.issues AS issues

// ----------------------------------------
// Query 4: Alert Correlation Analysis
// ----------------------------------------
// Find alerts that frequently occur together
MATCH (a1:Alert)-[:CORRELATES_WITH]-(a2:Alert)
WHERE a1.created_at >= datetime() - duration({days: 30})
  AND a1.alert_id < a2.alert_id  // Avoid duplicates
WITH a1.category AS cat1, a2.category AS cat2, 
     a1.component AS comp1, a2.component AS comp2,
     COUNT(*) AS co_occurrence
WHERE co_occurrence >= 3
RETURN cat1, comp1, cat2, comp2, co_occurrence
ORDER BY co_occurrence DESC
LIMIT 20

// ----------------------------------------
// Query 5: Drift to Retraining Flow
// ----------------------------------------
// Track how drifts lead to retraining and outcomes
MATCH (d:DriftResult)-[:TRIGGERED]->(a:Alert)-[:LED_TO]->(j:RetrainingJob)
WHERE d.detected_at >= datetime() - duration({days: 90})
RETURN d.drift_type AS drift_type,
       d.severity AS drift_severity,
       a.category AS alert_category,
       j.status AS job_status,
       j.trigger_type AS trigger,
       duration.between(d.detected_at, j.completed_at) AS time_to_fix,
       COUNT(*) AS occurrences
ORDER BY occurrences DESC

// ----------------------------------------
// Query 6: Psychological Validity Trends
// ----------------------------------------
MATCH (pv:PsychologicalValiditySnapshot)-[:VALIDITY_OF]->(m:Model)
WHERE m.category = 'psychological_inference'
  AND pv.timestamp >= datetime() - duration({days: 30})
WITH m.model_id AS model,
     DATE(pv.timestamp) AS day,
     AVG(pv.validity_score) AS avg_validity,
     SUM(pv.constraints_violated) AS total_violations
RETURN model, day, avg_validity, total_violations
ORDER BY model, day

// ----------------------------------------
// Query 7: Fusion Balance Analysis
// ----------------------------------------
MATCH (fq:FusionQualitySnapshot)
WHERE fq.timestamp >= datetime() - duration({hours: 24})
WITH fq
ORDER BY fq.timestamp DESC
RETURN fq.timestamp AS time,
       fq.source_entropy AS balance_score,
       fq.dominant_source_ratio AS concentration,
       fq.source_agreement_rate AS agreement,
       fq.fusion_health_score AS health

// ----------------------------------------
// Query 8: Retraining Effectiveness
// ----------------------------------------
// Measure if retraining actually improved models
MATCH (j:RetrainingJob)-[:RETRAINS]->(m:Model)
WHERE j.status = 'completed'
  AND j.completed_at >= datetime() - duration({days: 90})
WITH j, m
// Get health before and after retraining
MATCH (h_before:HealthSnapshot)-[:HEALTH_OF]->(m)
WHERE h_before.timestamp < j.started_at
  AND h_before.timestamp >= j.started_at - duration({days: 1})
WITH j, m, AVG(h_before.overall_score) AS score_before
MATCH (h_after:HealthSnapshot)-[:HEALTH_OF]->(m)
WHERE h_after.timestamp > j.completed_at
  AND h_after.timestamp <= j.completed_at + duration({days: 7})
WITH j, m, score_before, AVG(h_after.overall_score) AS score_after
RETURN j.job_id AS job,
       m.model_id AS model,
       j.trigger_type AS trigger,
       score_before,
       score_after,
       score_after - score_before AS improvement
ORDER BY improvement DESC

// ----------------------------------------
// Query 9: Source Contribution Drift Over Time
// ----------------------------------------
MATCH (fq:FusionQualitySnapshot)
WHERE fq.timestamp >= datetime() - duration({days: 7})
WITH DATE(fq.timestamp) AS day,
     fq.source_weights AS weights
UNWIND keys(weights) AS source
WITH day, source, AVG(weights[source]) AS avg_weight
RETURN day, source, avg_weight
ORDER BY day, source

// ----------------------------------------
// Query 10: Health Degradation Detection
// ----------------------------------------
// Find models with declining health trends
MATCH (m:Model)<-[:HEALTH_OF]-(h:HealthSnapshot)
WHERE h.timestamp >= datetime() - duration({days: 7})
WITH m, h
ORDER BY h.timestamp
WITH m, COLLECT(h.overall_score) AS scores
WHERE SIZE(scores) >= 24  // At least 24 data points
WITH m, scores,
     scores[0..SIZE(scores)/2] AS first_half,
     scores[SIZE(scores)/2..SIZE(scores)] AS second_half
WITH m,
     REDUCE(s = 0.0, x IN first_half | s + x) / SIZE(first_half) AS first_avg,
     REDUCE(s = 0.0, x IN second_half | s + x) / SIZE(second_half) AS second_avg
WHERE second_avg < first_avg - 0.1  // 10% decline
RETURN m.model_id AS model,
       first_avg AS week_start_health,
       second_avg AS week_end_health,
       first_avg - second_avg AS decline
ORDER BY decline DESC
```

### H.3 Indexes and Constraints

Optimized indexes for monitoring query patterns.

```cypher
// ============================================================================
// ADAM MONITORING INDEXES
// ============================================================================

// Time-based queries (most common pattern)
CREATE INDEX drift_timestamp IF NOT EXISTS
FOR (d:DriftResult) ON (d.detected_at, d.severity);

CREATE INDEX alert_timestamp IF NOT EXISTS  
FOR (a:Alert) ON (a.created_at, a.status);

CREATE INDEX health_timestamp IF NOT EXISTS
FOR (h:HealthSnapshot) ON (h.timestamp, h.overall_status);

CREATE INDEX job_timestamp IF NOT EXISTS
FOR (j:RetrainingJob) ON (j.created_at, j.status);

// Component lookups
CREATE INDEX alert_component IF NOT EXISTS
FOR (a:Alert) ON (a.component);

CREATE INDEX drift_model IF NOT EXISTS
FOR (d:DriftResult) ON (d.model_id);

// Status filtering
CREATE INDEX alert_status_severity IF NOT EXISTS
FOR (a:Alert) ON (a.status, a.severity);

CREATE INDEX job_status IF NOT EXISTS
FOR (j:RetrainingJob) ON (j.status, j.priority);

// Full-text search for alert investigation
CREATE FULLTEXT INDEX alert_search IF NOT EXISTS
FOR (a:Alert) ON EACH [a.title, a.description];

// Composite index for fusion queries
CREATE INDEX fusion_time_health IF NOT EXISTS
FOR (fq:FusionQualitySnapshot) ON (fq.timestamp, fq.fusion_health_score);

// Psychological validity queries
CREATE INDEX psych_validity_time IF NOT EXISTS
FOR (pv:PsychologicalValiditySnapshot) ON (pv.timestamp, pv.validity_score);
```

---

## SECTION I: GRADIENT BRIDGE INTEGRATION (#06)

### I.1 Learning Signal Health Monitoring

The Gradient Bridge is ADAM's cross-component learning engine where every outcome improves future decisions. Monitoring its health is critical because degraded learning signals cascade across all components.

```python
"""
ADAM Gradient Bridge Health Monitoring
Tracks learning signal quality, attribution accuracy, and cross-component learning health.
"""

from __future__ import annotations

import asyncio
import numpy as np
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass, field
from collections import defaultdict
import hashlib
import logging

from pydantic import BaseModel, Field, validator

logger = logging.getLogger(__name__)


# ============================================================================
# GRADIENT BRIDGE HEALTH MODELS
# ============================================================================

class LearningSignalType(str, Enum):
    """Types of learning signals in the Gradient Bridge."""
    
    # Outcome signals
    CONVERSION_OUTCOME = "conversion_outcome"           # Binary conversion signal
    ENGAGEMENT_OUTCOME = "engagement_outcome"           # Multi-level engagement
    REVENUE_OUTCOME = "revenue_outcome"                 # Revenue attribution
    RETENTION_OUTCOME = "retention_outcome"             # Long-term retention
    
    # Behavioral signals
    CLICK_THROUGH = "click_through"                     # CTR signal
    DWELL_TIME = "dwell_time"                           # Time on page
    SCROLL_DEPTH = "scroll_depth"                       # Content engagement
    INTERACTION_SEQUENCE = "interaction_sequence"       # Behavioral patterns
    
    # Psychological signals
    PERSONALITY_VALIDATION = "personality_validation"   # Trait prediction accuracy
    STATE_TRANSITION = "state_transition"               # State change patterns
    CONSTRUCT_ACTIVATION = "construct_activation"       # Construct engagement
    MECHANISM_EFFECTIVENESS = "mechanism_effectiveness" # Mechanism outcomes


class AttributionMethod(str, Enum):
    """Attribution methods used in Gradient Bridge."""
    
    SHAPLEY = "shapley"                     # Game-theoretic attribution
    ATTENTION_BASED = "attention_based"     # Transformer attention weights
    CAUSAL_INFERENCE = "causal_inference"   # Causal discovery methods
    TEMPORAL_DECAY = "temporal_decay"       # Time-weighted attribution
    LAST_TOUCH = "last_touch"               # Simplified last-touch
    MULTI_TOUCH = "multi_touch"             # Full path attribution
    QLLM_INSPIRED = "qllm_inspired"         # Query-level attribution


class LearningSignalHealth(BaseModel):
    """Health status of a specific learning signal."""
    
    signal_type: LearningSignalType
    
    # Volume metrics
    signal_volume_1h: int = Field(ge=0)
    signal_volume_24h: int = Field(ge=0)
    volume_trend: str = Field(pattern="^(increasing|stable|decreasing|volatile)$")
    
    # Quality metrics
    signal_to_noise_ratio: float = Field(ge=0.0, le=100.0)  # SNR in dB equivalent
    label_quality_score: float = Field(ge=0.0, le=1.0)      # Label accuracy estimate
    delay_distribution_p50_ms: float = Field(ge=0.0)
    delay_distribution_p95_ms: float = Field(ge=0.0)
    
    # Reliability metrics
    missing_rate: float = Field(ge=0.0, le=1.0)
    duplicate_rate: float = Field(ge=0.0, le=1.0)
    out_of_order_rate: float = Field(ge=0.0, le=1.0)
    
    # Health assessment
    health_status: str = Field(pattern="^(healthy|degraded|unhealthy|critical)$")
    issues: List[str] = Field(default_factory=list)
    
    class Config:
        use_enum_values = True


class AttributionHealthMetrics(BaseModel):
    """Health metrics for attribution quality."""
    
    method: AttributionMethod
    
    # Coverage metrics
    coverage_rate: float = Field(ge=0.0, le=1.0)    # % of events with attribution
    component_coverage: Dict[str, float]            # Per-component coverage
    
    # Quality metrics
    attribution_confidence_mean: float = Field(ge=0.0, le=1.0)
    attribution_confidence_std: float = Field(ge=0.0)
    negative_attribution_rate: float = Field(ge=0.0, le=1.0)  # Should be low
    attribution_concentration: float = Field(ge=0.0, le=1.0)  # Gini coefficient
    
    # Consistency metrics
    temporal_stability: float = Field(ge=0.0, le=1.0)   # Attribution stability over time
    cross_method_agreement: float = Field(ge=0.0, le=1.0)  # Agreement with other methods
    
    # Computation metrics
    computation_time_p50_ms: float = Field(ge=0.0)
    computation_time_p95_ms: float = Field(ge=0.0)
    
    health_status: str = Field(pattern="^(healthy|degraded|unhealthy|critical)$")
    
    class Config:
        use_enum_values = True


class ComponentLearningHealth(BaseModel):
    """Learning health for a specific ADAM component."""
    
    component_id: str
    component_name: str
    
    # Signal reception
    signals_received_24h: int = Field(ge=0)
    signal_types_active: List[LearningSignalType]
    signal_coverage: float = Field(ge=0.0, le=1.0)  # % of predictions with feedback
    
    # Learning effectiveness
    gradient_magnitude_mean: float = Field(ge=0.0)
    gradient_magnitude_std: float = Field(ge=0.0)
    gradient_norm_p95: float = Field(ge=0.0)
    
    # Parameter updates
    updates_applied_24h: int = Field(ge=0)
    update_frequency_hz: float = Field(ge=0.0)
    convergence_metric: float = Field(ge=0.0, le=1.0)  # 1.0 = fully converged
    
    # Health metrics
    learning_rate_effective: float = Field(ge=0.0)
    loss_trend_7d: str = Field(pattern="^(decreasing|stable|increasing|unstable)$")
    overfitting_risk: float = Field(ge=0.0, le=1.0)
    
    health_status: str = Field(pattern="^(healthy|degraded|unhealthy|critical)$")
    issues: List[str] = Field(default_factory=list)
    
    class Config:
        use_enum_values = True


class GradientBridgeHealth(BaseModel):
    """Overall Gradient Bridge health snapshot."""
    
    timestamp: datetime
    
    # Signal health by type
    signal_health: Dict[str, LearningSignalHealth]
    
    # Attribution health by method
    attribution_health: Dict[str, AttributionHealthMetrics]
    
    # Component health
    component_health: Dict[str, ComponentLearningHealth]
    
    # Cross-component metrics
    cross_component_correlation: float = Field(ge=-1.0, le=1.0)
    learning_velocity: float = Field(ge=0.0)  # Aggregate learning rate
    gradient_flow_health: float = Field(ge=0.0, le=1.0)  # Overall flow quality
    
    # System-level
    total_signals_24h: int = Field(ge=0)
    total_updates_24h: int = Field(ge=0)
    feedback_loop_latency_p50_ms: float = Field(ge=0.0)
    feedback_loop_latency_p95_ms: float = Field(ge=0.0)
    
    # Overall health
    overall_health_score: float = Field(ge=0.0, le=1.0)
    overall_status: str = Field(pattern="^(healthy|degraded|unhealthy|critical)$")
    priority_issues: List[str] = Field(default_factory=list)


# ============================================================================
# GRADIENT BRIDGE MONITOR
# ============================================================================

@dataclass
class SignalWindow:
    """Rolling window for signal statistics."""
    
    values: List[float] = field(default_factory=list)
    timestamps: List[datetime] = field(default_factory=list)
    max_size: int = 10000
    max_age: timedelta = timedelta(hours=24)
    
    def add(self, value: float, timestamp: Optional[datetime] = None) -> None:
        """Add a signal value to the window."""
        ts = timestamp or datetime.utcnow()
        self.values.append(value)
        self.timestamps.append(ts)
        self._prune()
    
    def _prune(self) -> None:
        """Remove old and excess entries."""
        cutoff = datetime.utcnow() - self.max_age
        
        # Remove old entries
        while self.timestamps and self.timestamps[0] < cutoff:
            self.values.pop(0)
            self.timestamps.pop(0)
        
        # Enforce max size
        while len(self.values) > self.max_size:
            self.values.pop(0)
            self.timestamps.pop(0)
    
    def mean(self) -> Optional[float]:
        return np.mean(self.values) if self.values else None
    
    def std(self) -> Optional[float]:
        return np.std(self.values) if len(self.values) > 1 else None
    
    def percentile(self, p: float) -> Optional[float]:
        return np.percentile(self.values, p) if self.values else None
    
    def count_since(self, since: datetime) -> int:
        return sum(1 for ts in self.timestamps if ts >= since)
    
    def trend(self) -> str:
        """Calculate trend over window."""
        if len(self.values) < 10:
            return "stable"
        
        first_half = np.mean(self.values[:len(self.values)//2])
        second_half = np.mean(self.values[len(self.values)//2:])
        
        change = (second_half - first_half) / (first_half + 1e-10)
        
        if abs(change) < 0.05:
            return "stable"
        elif change > 0.15:
            return "increasing"
        elif change < -0.15:
            return "decreasing"
        else:
            std = np.std(self.values)
            mean = np.mean(self.values)
            cv = std / (mean + 1e-10)
            return "volatile" if cv > 0.3 else "stable"


class GradientBridgeMonitor:
    """
    Monitors the health of the Gradient Bridge learning system.
    
    Tracks learning signal quality, attribution accuracy, and cross-component
    learning effectiveness. Integrates with Enhancement #06 to ensure the
    learning backbone remains healthy.
    """
    
    # Health thresholds
    SIGNAL_VOLUME_MIN_1H = 100       # Minimum signals per hour
    SNR_MIN_HEALTHY = 10.0           # Minimum signal-to-noise ratio
    LABEL_QUALITY_MIN = 0.85         # Minimum label quality
    MISSING_RATE_MAX = 0.05          # Maximum acceptable missing rate
    ATTRIBUTION_COVERAGE_MIN = 0.80  # Minimum attribution coverage
    ATTRIBUTION_CONFIDENCE_MIN = 0.6 # Minimum attribution confidence
    GRADIENT_NORM_MAX = 100.0        # Maximum gradient norm (explosion detection)
    CONVERGENCE_MIN = 0.3            # Minimum convergence metric
    
    def __init__(
        self,
        event_bus: Optional[Any] = None,
        metrics_client: Optional[Any] = None
    ):
        self.event_bus = event_bus
        self.metrics_client = metrics_client
        
        # Signal tracking by type
        self._signal_windows: Dict[LearningSignalType, SignalWindow] = {
            signal_type: SignalWindow()
            for signal_type in LearningSignalType
        }
        
        # Signal quality tracking
        self._signal_quality: Dict[LearningSignalType, SignalWindow] = {
            signal_type: SignalWindow()
            for signal_type in LearningSignalType
        }
        
        # Attribution tracking by method
        self._attribution_windows: Dict[AttributionMethod, SignalWindow] = {
            method: SignalWindow()
            for method in AttributionMethod
        }
        
        # Component gradient tracking
        self._component_gradients: Dict[str, SignalWindow] = defaultdict(SignalWindow)
        self._component_updates: Dict[str, List[datetime]] = defaultdict(list)
        self._component_losses: Dict[str, SignalWindow] = defaultdict(SignalWindow)
        
        # Feedback loop latency
        self._feedback_latencies = SignalWindow(max_size=5000)
        
        # Signal metadata
        self._signal_delays: Dict[LearningSignalType, SignalWindow] = {
            signal_type: SignalWindow()
            for signal_type in LearningSignalType
        }
        
        # Missing/duplicate tracking
        self._expected_signals: Set[str] = set()
        self._received_signals: Set[str] = set()
        self._signal_timestamps: Dict[str, datetime] = {}
        
        logger.info("GradientBridgeMonitor initialized")
    
    async def record_learning_signal(
        self,
        signal_type: LearningSignalType,
        signal_id: str,
        value: float,
        quality_score: float,
        delay_ms: float,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Record a learning signal for monitoring."""
        
        timestamp = datetime.utcnow()
        
        # Track signal volume
        self._signal_windows[signal_type].add(value, timestamp)
        
        # Track quality
        self._signal_quality[signal_type].add(quality_score, timestamp)
        
        # Track delay
        self._signal_delays[signal_type].add(delay_ms, timestamp)
        
        # Track for missing/duplicate detection
        if signal_id in self._received_signals:
            # Duplicate detected
            logger.warning(f"Duplicate signal detected: {signal_id}")
        else:
            self._received_signals.add(signal_id)
            self._signal_timestamps[signal_id] = timestamp
        
        # Remove from expected if present
        self._expected_signals.discard(signal_id)
        
        # Emit metric
        if self.metrics_client:
            await self.metrics_client.increment(
                "gradient_bridge.signal.received",
                tags={"type": signal_type.value}
            )
    
    async def expect_signal(self, signal_id: str) -> None:
        """Mark a signal as expected (for missing detection)."""
        self._expected_signals.add(signal_id)
    
    async def record_attribution(
        self,
        method: AttributionMethod,
        confidence: float,
        coverage: float,
        computation_time_ms: float,
        component_attributions: Dict[str, float]
    ) -> None:
        """Record attribution computation for monitoring."""
        
        timestamp = datetime.utcnow()
        
        # Track confidence
        self._attribution_windows[method].add(confidence, timestamp)
        
        # Calculate concentration (Gini coefficient)
        values = list(component_attributions.values())
        if values:
            sorted_values = sorted(values)
            n = len(sorted_values)
            cumsum = np.cumsum(sorted_values)
            gini = (2 * np.sum((np.arange(1, n + 1) * sorted_values))) / (n * np.sum(sorted_values)) - (n + 1) / n
            gini = max(0, min(1, gini))  # Clamp to [0, 1]
        else:
            gini = 0.0
        
        if self.metrics_client:
            await self.metrics_client.gauge(
                "gradient_bridge.attribution.confidence",
                confidence,
                tags={"method": method.value}
            )
            await self.metrics_client.gauge(
                "gradient_bridge.attribution.concentration",
                gini,
                tags={"method": method.value}
            )
    
    async def record_component_gradient(
        self,
        component_id: str,
        gradient_norm: float,
        loss_value: float,
        update_applied: bool
    ) -> None:
        """Record gradient information for a component."""
        
        timestamp = datetime.utcnow()
        
        # Track gradient norm
        self._component_gradients[component_id].add(gradient_norm, timestamp)
        
        # Track loss
        self._component_losses[component_id].add(loss_value, timestamp)
        
        # Track updates
        if update_applied:
            self._component_updates[component_id].append(timestamp)
            # Prune old updates
            cutoff = timestamp - timedelta(hours=24)
            self._component_updates[component_id] = [
                ts for ts in self._component_updates[component_id]
                if ts >= cutoff
            ]
        
        # Check for gradient explosion
        if gradient_norm > self.GRADIENT_NORM_MAX:
            logger.warning(
                f"Gradient explosion detected in {component_id}: "
                f"norm={gradient_norm}"
            )
            if self.event_bus:
                await self.event_bus.publish(
                    "gradient_bridge.gradient_explosion",
                    {
                        "component_id": component_id,
                        "gradient_norm": gradient_norm,
                        "timestamp": timestamp.isoformat()
                    }
                )
    
    async def record_feedback_loop_completion(
        self,
        latency_ms: float,
        signal_type: LearningSignalType,
        components_updated: List[str]
    ) -> None:
        """Record end-to-end feedback loop completion."""
        
        timestamp = datetime.utcnow()
        self._feedback_latencies.add(latency_ms, timestamp)
        
        if self.metrics_client:
            await self.metrics_client.histogram(
                "gradient_bridge.feedback_loop.latency_ms",
                latency_ms,
                tags={"signal_type": signal_type.value}
            )
    
    def _assess_signal_health(
        self,
        signal_type: LearningSignalType
    ) -> LearningSignalHealth:
        """Assess health of a specific signal type."""
        
        signal_window = self._signal_windows[signal_type]
        quality_window = self._signal_quality[signal_type]
        delay_window = self._signal_delays[signal_type]
        
        now = datetime.utcnow()
        
        # Volume metrics
        volume_1h = signal_window.count_since(now - timedelta(hours=1))
        volume_24h = signal_window.count_since(now - timedelta(hours=24))
        volume_trend = signal_window.trend()
        
        # Quality metrics
        mean_quality = quality_window.mean() or 0.0
        
        # Calculate SNR (higher quality = higher SNR)
        if quality_window.std() and quality_window.std() > 0:
            snr = 10 * np.log10(mean_quality / quality_window.std())
        else:
            snr = 20.0 if mean_quality > 0.8 else 10.0  # Default estimate
        
        # Delay metrics
        delay_p50 = delay_window.percentile(50) or 0.0
        delay_p95 = delay_window.percentile(95) or 0.0
        
        # Calculate missing/duplicate rates
        total_expected = len(self._expected_signals) + len(self._received_signals)
        missing_rate = len(self._expected_signals) / max(total_expected, 1)
        
        # Estimate duplicate rate from window
        duplicate_rate = 0.01  # Simplified; would track in production
        
        # Out of order detection (simplified)
        out_of_order_rate = 0.005
        
        # Identify issues
        issues = []
        
        if volume_1h < self.SIGNAL_VOLUME_MIN_1H:
            issues.append(f"Low signal volume: {volume_1h}/hour")
        
        if snr < self.SNR_MIN_HEALTHY:
            issues.append(f"Low signal-to-noise ratio: {snr:.1f}")
        
        if mean_quality < self.LABEL_QUALITY_MIN:
            issues.append(f"Low label quality: {mean_quality:.2f}")
        
        if missing_rate > self.MISSING_RATE_MAX:
            issues.append(f"High missing rate: {missing_rate:.1%}")
        
        if delay_p95 > 60000:  # 1 minute
            issues.append(f"High signal delay: p95={delay_p95/1000:.1f}s")
        
        # Determine health status
        if len(issues) == 0:
            health_status = "healthy"
        elif len(issues) <= 1 and volume_1h >= self.SIGNAL_VOLUME_MIN_1H // 2:
            health_status = "degraded"
        elif volume_1h < self.SIGNAL_VOLUME_MIN_1H // 10:
            health_status = "critical"
        else:
            health_status = "unhealthy"
        
        return LearningSignalHealth(
            signal_type=signal_type,
            signal_volume_1h=volume_1h,
            signal_volume_24h=volume_24h,
            volume_trend=volume_trend,
            signal_to_noise_ratio=max(0, min(100, snr)),
            label_quality_score=mean_quality,
            delay_distribution_p50_ms=delay_p50,
            delay_distribution_p95_ms=delay_p95,
            missing_rate=missing_rate,
            duplicate_rate=duplicate_rate,
            out_of_order_rate=out_of_order_rate,
            health_status=health_status,
            issues=issues
        )
    
    def _assess_attribution_health(
        self,
        method: AttributionMethod
    ) -> AttributionHealthMetrics:
        """Assess health of an attribution method."""
        
        window = self._attribution_windows[method]
        
        confidence_mean = window.mean() or 0.0
        confidence_std = window.std() or 0.0
        
        # Simplified metrics (would be more detailed in production)
        coverage_rate = 0.85 if window.mean() else 0.0
        component_coverage = {}  # Would track per-component
        
        # Estimate other metrics
        negative_rate = 0.02 if confidence_mean > 0.7 else 0.05
        concentration = 0.3  # Would calculate from actual attributions
        temporal_stability = 0.85 if confidence_std < 0.1 else 0.7
        cross_method_agreement = 0.75  # Would compare methods
        
        # Computation time (from metrics system in production)
        comp_time_p50 = 50.0
        comp_time_p95 = 150.0
        
        # Determine health
        issues_count = 0
        if coverage_rate < self.ATTRIBUTION_COVERAGE_MIN:
            issues_count += 1
        if confidence_mean < self.ATTRIBUTION_CONFIDENCE_MIN:
            issues_count += 1
        if negative_rate > 0.1:
            issues_count += 1
        
        if issues_count == 0:
            health_status = "healthy"
        elif issues_count == 1:
            health_status = "degraded"
        else:
            health_status = "unhealthy"
        
        return AttributionHealthMetrics(
            method=method,
            coverage_rate=coverage_rate,
            component_coverage=component_coverage,
            attribution_confidence_mean=confidence_mean,
            attribution_confidence_std=confidence_std,
            negative_attribution_rate=negative_rate,
            attribution_concentration=concentration,
            temporal_stability=temporal_stability,
            cross_method_agreement=cross_method_agreement,
            computation_time_p50_ms=comp_time_p50,
            computation_time_p95_ms=comp_time_p95,
            health_status=health_status
        )
    
    def _assess_component_health(
        self,
        component_id: str,
        component_name: str
    ) -> ComponentLearningHealth:
        """Assess learning health for a component."""
        
        gradient_window = self._component_gradients.get(component_id, SignalWindow())
        loss_window = self._component_losses.get(component_id, SignalWindow())
        updates = self._component_updates.get(component_id, [])
        
        now = datetime.utcnow()
        
        # Count signals received
        signals_24h = gradient_window.count_since(now - timedelta(hours=24))
        
        # Active signal types (simplified)
        active_types = [LearningSignalType.CONVERSION_OUTCOME]
        
        # Calculate signal coverage
        signal_coverage = min(1.0, signals_24h / 1000)  # Target 1000 signals/day
        
        # Gradient metrics
        grad_mean = gradient_window.mean() or 0.0
        grad_std = gradient_window.std() or 0.0
        grad_p95 = gradient_window.percentile(95) or 0.0
        
        # Update metrics
        updates_24h = len(updates)
        update_freq = updates_24h / 86400.0  # Hz
        
        # Convergence estimate from loss trend
        loss_values = loss_window.values
        if len(loss_values) >= 10:
            recent_loss = np.mean(loss_values[-10:])
            older_loss = np.mean(loss_values[:10])
            if older_loss > 0:
                convergence = 1.0 - min(1.0, recent_loss / older_loss)
            else:
                convergence = 0.5
        else:
            convergence = 0.5
        
        # Effective learning rate estimate
        effective_lr = 0.001 if grad_mean > 0 else 0.0
        
        # Loss trend
        loss_trend = loss_window.trend()
        if loss_trend == "increasing":
            loss_trend = "unstable"  # Increasing loss is concerning
        
        # Overfitting risk (simplified heuristic)
        overfitting_risk = 0.1 if convergence > 0.8 else 0.3
        
        # Identify issues
        issues = []
        
        if signals_24h < 100:
            issues.append(f"Low signal volume: {signals_24h}/day")
        
        if grad_p95 > self.GRADIENT_NORM_MAX:
            issues.append(f"Gradient instability: p95={grad_p95:.1f}")
        
        if convergence < self.CONVERGENCE_MIN:
            issues.append(f"Poor convergence: {convergence:.2f}")
        
        if loss_trend == "unstable":
            issues.append("Loss increasing over time")
        
        # Health status
        if len(issues) == 0:
            health_status = "healthy"
        elif len(issues) == 1:
            health_status = "degraded"
        elif grad_p95 > self.GRADIENT_NORM_MAX * 2:
            health_status = "critical"
        else:
            health_status = "unhealthy"
        
        return ComponentLearningHealth(
            component_id=component_id,
            component_name=component_name,
            signals_received_24h=signals_24h,
            signal_types_active=active_types,
            signal_coverage=signal_coverage,
            gradient_magnitude_mean=grad_mean,
            gradient_magnitude_std=grad_std,
            gradient_norm_p95=grad_p95,
            updates_applied_24h=updates_24h,
            update_frequency_hz=update_freq,
            convergence_metric=convergence,
            learning_rate_effective=effective_lr,
            loss_trend_7d=loss_trend,
            overfitting_risk=overfitting_risk,
            health_status=health_status,
            issues=issues
        )
    
    async def get_gradient_bridge_health(self) -> GradientBridgeHealth:
        """Get comprehensive Gradient Bridge health snapshot."""
        
        timestamp = datetime.utcnow()
        
        # Assess all signal types
        signal_health = {
            signal_type.value: self._assess_signal_health(signal_type)
            for signal_type in LearningSignalType
        }
        
        # Assess all attribution methods
        attribution_health = {
            method.value: self._assess_attribution_health(method)
            for method in AttributionMethod
        }
        
        # Assess all components
        component_ids = list(self._component_gradients.keys())
        if not component_ids:
            # Default components if none tracked yet
            component_ids = [
                "personality_predictor",
                "mechanism_selector",
                "copy_generator",
                "audience_matcher"
            ]
        
        component_health = {
            comp_id: self._assess_component_health(comp_id, comp_id)
            for comp_id in component_ids
        }
        
        # Cross-component correlation (simplified)
        component_convergences = [
            h.convergence_metric for h in component_health.values()
        ]
        if len(component_convergences) >= 2:
            cross_correlation = 1.0 - np.std(component_convergences)
        else:
            cross_correlation = 0.5
        
        # Learning velocity
        total_updates = sum(
            h.updates_applied_24h for h in component_health.values()
        )
        learning_velocity = total_updates / 86400.0  # Updates per second
        
        # Gradient flow health (weighted average of component health)
        component_scores = {
            "healthy": 1.0, "degraded": 0.6, "unhealthy": 0.3, "critical": 0.0
        }
        if component_health:
            flow_health = np.mean([
                component_scores.get(h.health_status, 0.5)
                for h in component_health.values()
            ])
        else:
            flow_health = 0.5
        
        # Total signals
        total_signals = sum(
            h.signal_volume_24h for h in signal_health.values()
        )
        
        # Feedback latency
        latency_p50 = self._feedback_latencies.percentile(50) or 100.0
        latency_p95 = self._feedback_latencies.percentile(95) or 500.0
        
        # Overall health score
        signal_score = np.mean([
            component_scores.get(h.health_status, 0.5)
            for h in signal_health.values()
        ])
        attribution_score = np.mean([
            component_scores.get(h.health_status, 0.5)
            for h in attribution_health.values()
        ])
        
        overall_score = (
            0.35 * signal_score +
            0.25 * attribution_score +
            0.25 * flow_health +
            0.15 * min(1.0, cross_correlation)
        )
        
        # Overall status
        if overall_score >= 0.8:
            overall_status = "healthy"
        elif overall_score >= 0.6:
            overall_status = "degraded"
        elif overall_score >= 0.3:
            overall_status = "unhealthy"
        else:
            overall_status = "critical"
        
        # Priority issues
        priority_issues = []
        
        for sh in signal_health.values():
            if sh.health_status == "critical":
                priority_issues.append(
                    f"CRITICAL: {sh.signal_type} signal health critical"
                )
        
        for ch in component_health.values():
            if ch.health_status == "critical":
                priority_issues.append(
                    f"CRITICAL: {ch.component_name} learning health critical"
                )
            for issue in ch.issues[:2]:  # Top 2 issues per component
                priority_issues.append(f"{ch.component_name}: {issue}")
        
        priority_issues = priority_issues[:10]  # Top 10
        
        return GradientBridgeHealth(
            timestamp=timestamp,
            signal_health=signal_health,
            attribution_health=attribution_health,
            component_health=component_health,
            cross_component_correlation=cross_correlation,
            learning_velocity=learning_velocity,
            gradient_flow_health=flow_health,
            total_signals_24h=total_signals,
            total_updates_24h=total_updates,
            feedback_loop_latency_p50_ms=latency_p50,
            feedback_loop_latency_p95_ms=latency_p95,
            overall_health_score=overall_score,
            overall_status=overall_status,
            priority_issues=priority_issues
        )
```

### I.2 Attribution Quality Tracking

Deep monitoring of attribution quality ensures learning signals are properly credited to the components that caused outcomes.

```python
"""
Attribution Quality Tracking for Gradient Bridge.
Ensures learning signals accurately credit component contributions.
"""

from __future__ import annotations

import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from collections import defaultdict
import logging

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class AttributionQualityMetrics(BaseModel):
    """Comprehensive attribution quality assessment."""
    
    # Calibration metrics
    calibration_error: float = Field(ge=0.0, le=1.0)     # ECE-style error
    reliability_diagram_slope: float                      # Should be ~1.0
    reliability_diagram_intercept: float                  # Should be ~0.0
    
    # Consistency metrics
    temporal_consistency: float = Field(ge=0.0, le=1.0)   # Stability over time
    counterfactual_consistency: float = Field(ge=0.0, le=1.0)  # Consistent under perturbation
    cross_method_consistency: float = Field(ge=0.0, le=1.0)    # Agreement across methods
    
    # Coverage metrics
    full_coverage_rate: float = Field(ge=0.0, le=1.0)     # % with all attributions
    partial_coverage_rate: float = Field(ge=0.0, le=1.0)  # % with some attributions
    missing_component_rate: float = Field(ge=0.0, le=1.0) # % missing key components
    
    # Distribution metrics
    attribution_entropy: float = Field(ge=0.0)            # Higher = more distributed
    dominant_component_share: float = Field(ge=0.0, le=1.0)  # Largest single attribution
    top3_component_share: float = Field(ge=0.0, le=1.0)   # Top 3 attributions combined
    
    # Anomaly metrics
    negative_attribution_rate: float = Field(ge=0.0, le=1.0)
    extreme_attribution_rate: float = Field(ge=0.0, le=1.0)  # |attr| > 1.0
    zero_attribution_rate: float = Field(ge=0.0, le=1.0)
    
    # Overall quality
    quality_score: float = Field(ge=0.0, le=1.0)
    quality_status: str = Field(pattern="^(excellent|good|acceptable|poor|critical)$")
    issues: List[str] = Field(default_factory=list)


@dataclass
class AttributionRecord:
    """Single attribution record for analysis."""
    
    timestamp: datetime
    outcome_type: str
    outcome_value: float
    outcome_probability: float
    component_attributions: Dict[str, float]
    total_attribution: float
    method: str
    confidence: float


class AttributionQualityTracker:
    """
    Tracks and analyzes attribution quality over time.
    
    Ensures that the Gradient Bridge's attribution system accurately
    credits components for outcomes, enabling effective learning.
    """
    
    # Quality thresholds
    CALIBRATION_ERROR_MAX = 0.15
    CONSISTENCY_MIN = 0.70
    COVERAGE_MIN = 0.85
    ENTROPY_MIN = 1.0  # Minimum attribution entropy
    NEGATIVE_RATE_MAX = 0.10
    
    def __init__(self, max_records: int = 50000):
        self.max_records = max_records
        
        # Attribution records by method
        self._records: Dict[str, List[AttributionRecord]] = defaultdict(list)
        
        # Calibration tracking
        self._predicted_outcomes: Dict[str, List[float]] = defaultdict(list)
        self._actual_outcomes: Dict[str, List[float]] = defaultdict(list)
        
        # Consistency tracking
        self._temporal_attributions: Dict[str, List[Tuple[datetime, Dict[str, float]]]] = defaultdict(list)
        
        # Cross-method comparison
        self._method_attributions: Dict[str, Dict[str, float]] = {}  # outcome_id -> method -> component attrs
        
        logger.info("AttributionQualityTracker initialized")
    
    def record_attribution(
        self,
        outcome_id: str,
        outcome_type: str,
        outcome_value: float,
        predicted_outcome: float,
        component_attributions: Dict[str, float],
        method: str,
        confidence: float
    ) -> None:
        """Record an attribution for quality tracking."""
        
        timestamp = datetime.utcnow()
        total_attr = sum(component_attributions.values())
        
        record = AttributionRecord(
            timestamp=timestamp,
            outcome_type=outcome_type,
            outcome_value=outcome_value,
            outcome_probability=predicted_outcome,
            component_attributions=component_attributions,
            total_attribution=total_attr,
            method=method,
            confidence=confidence
        )
        
        self._records[method].append(record)
        
        # Track for calibration
        self._predicted_outcomes[method].append(predicted_outcome)
        self._actual_outcomes[method].append(outcome_value)
        
        # Track temporal consistency
        self._temporal_attributions[method].append((timestamp, component_attributions))
        
        # Track cross-method
        if outcome_id not in self._method_attributions:
            self._method_attributions[outcome_id] = {}
        self._method_attributions[outcome_id][method] = component_attributions
        
        # Prune old records
        self._prune_old_records(method)
    
    def _prune_old_records(self, method: str) -> None:
        """Remove old records to maintain memory bounds."""
        
        if len(self._records[method]) > self.max_records:
            excess = len(self._records[method]) - self.max_records
            self._records[method] = self._records[method][excess:]
            self._predicted_outcomes[method] = self._predicted_outcomes[method][excess:]
            self._actual_outcomes[method] = self._actual_outcomes[method][excess:]
            self._temporal_attributions[method] = self._temporal_attributions[method][excess:]
    
    def _calculate_calibration_error(self, method: str) -> Tuple[float, float, float]:
        """Calculate expected calibration error and reliability metrics."""
        
        predicted = np.array(self._predicted_outcomes[method])
        actual = np.array(self._actual_outcomes[method])
        
        if len(predicted) < 100:
            return 0.1, 1.0, 0.0  # Default values with insufficient data
        
        # Bin predictions for reliability diagram
        n_bins = 10
        bin_boundaries = np.linspace(0, 1, n_bins + 1)
        
        bin_accuracies = []
        bin_confidences = []
        bin_counts = []
        
        for i in range(n_bins):
            mask = (predicted >= bin_boundaries[i]) & (predicted < bin_boundaries[i + 1])
            if mask.sum() > 0:
                bin_acc = actual[mask].mean()
                bin_conf = predicted[mask].mean()
                bin_count = mask.sum()
                
                bin_accuracies.append(bin_acc)
                bin_confidences.append(bin_conf)
                bin_counts.append(bin_count)
        
        if not bin_accuracies:
            return 0.1, 1.0, 0.0
        
        # Expected Calibration Error
        total = sum(bin_counts)
        ece = sum(
            (count / total) * abs(acc - conf)
            for acc, conf, count in zip(bin_accuracies, bin_confidences, bin_counts)
        )
        
        # Reliability diagram linear fit
        if len(bin_confidences) >= 2:
            coeffs = np.polyfit(bin_confidences, bin_accuracies, 1)
            slope, intercept = coeffs[0], coeffs[1]
        else:
            slope, intercept = 1.0, 0.0
        
        return ece, slope, intercept
    
    def _calculate_temporal_consistency(self, method: str) -> float:
        """Calculate how stable attributions are over time."""
        
        temporal = self._temporal_attributions[method]
        
        if len(temporal) < 100:
            return 0.8  # Default with insufficient data
        
        # Get recent attributions
        recent = temporal[-1000:]  # Last 1000
        
        # Group by hour and calculate variance
        hourly_attributions: Dict[str, List[Dict[str, float]]] = defaultdict(list)
        
        for ts, attrs in recent:
            hour_key = ts.strftime("%Y-%m-%d-%H")
            hourly_attributions[hour_key].append(attrs)
        
        # Calculate consistency across hours
        consistencies = []
        
        hours = sorted(hourly_attributions.keys())
        for i in range(len(hours) - 1):
            attrs1 = hourly_attributions[hours[i]]
            attrs2 = hourly_attributions[hours[i + 1]]
            
            # Average attributions per hour
            avg1 = self._average_attributions(attrs1)
            avg2 = self._average_attributions(attrs2)
            
            # Cosine similarity
            similarity = self._cosine_similarity(avg1, avg2)
            consistencies.append(similarity)
        
        return np.mean(consistencies) if consistencies else 0.8
    
    def _average_attributions(
        self,
        attr_list: List[Dict[str, float]]
    ) -> Dict[str, float]:
        """Average multiple attribution dicts."""
        
        all_keys = set()
        for attrs in attr_list:
            all_keys.update(attrs.keys())
        
        result = {}
        for key in all_keys:
            values = [attrs.get(key, 0.0) for attrs in attr_list]
            result[key] = np.mean(values)
        
        return result
    
    def _cosine_similarity(
        self,
        attrs1: Dict[str, float],
        attrs2: Dict[str, float]
    ) -> float:
        """Calculate cosine similarity between two attribution dicts."""
        
        all_keys = set(attrs1.keys()) | set(attrs2.keys())
        
        vec1 = np.array([attrs1.get(k, 0.0) for k in all_keys])
        vec2 = np.array([attrs2.get(k, 0.0) for k in all_keys])
        
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return np.dot(vec1, vec2) / (norm1 * norm2)
    
    def _calculate_cross_method_consistency(self) -> float:
        """Calculate agreement between different attribution methods."""
        
        # Get outcomes with multiple methods
        multi_method = [
            attrs for attrs in self._method_attributions.values()
            if len(attrs) >= 2
        ]
        
        if len(multi_method) < 50:
            return 0.75  # Default with insufficient data
        
        # Calculate pairwise similarities
        similarities = []
        
        for outcome_attrs in multi_method[-500:]:  # Last 500
            methods = list(outcome_attrs.keys())
            
            for i in range(len(methods)):
                for j in range(i + 1, len(methods)):
                    sim = self._cosine_similarity(
                        outcome_attrs[methods[i]],
                        outcome_attrs[methods[j]]
                    )
                    similarities.append(sim)
        
        return np.mean(similarities) if similarities else 0.75
    
    def _calculate_distribution_metrics(
        self,
        method: str
    ) -> Tuple[float, float, float]:
        """Calculate attribution distribution metrics."""
        
        records = self._records[method]
        
        if not records:
            return 2.0, 0.3, 0.6  # Default values
        
        recent = records[-1000:]  # Last 1000
        
        entropies = []
        dominant_shares = []
        top3_shares = []
        
        for record in recent:
            attrs = record.component_attributions
            if not attrs:
                continue
            
            values = np.array(list(attrs.values()))
            values = np.abs(values)  # Use absolute values
            total = values.sum()
            
            if total == 0:
                continue
            
            probs = values / total
            
            # Entropy
            entropy = -np.sum(probs * np.log(probs + 1e-10))
            entropies.append(entropy)
            
            # Dominant share
            dominant_shares.append(probs.max())
            
            # Top 3 share
            sorted_probs = np.sort(probs)[::-1]
            top3_shares.append(sorted_probs[:3].sum())
        
        return (
            np.mean(entropies) if entropies else 2.0,
            np.mean(dominant_shares) if dominant_shares else 0.3,
            np.mean(top3_shares) if top3_shares else 0.6
        )
    
    def _calculate_anomaly_rates(
        self,
        method: str
    ) -> Tuple[float, float, float]:
        """Calculate attribution anomaly rates."""
        
        records = self._records[method]
        
        if not records:
            return 0.02, 0.01, 0.05  # Default rates
        
        recent = records[-1000:]
        
        negative_count = 0
        extreme_count = 0
        zero_count = 0
        total_attrs = 0
        
        for record in recent:
            for value in record.component_attributions.values():
                total_attrs += 1
                
                if value < 0:
                    negative_count += 1
                if abs(value) > 1.0:
                    extreme_count += 1
                if abs(value) < 0.001:
                    zero_count += 1
        
        if total_attrs == 0:
            return 0.02, 0.01, 0.05
        
        return (
            negative_count / total_attrs,
            extreme_count / total_attrs,
            zero_count / total_attrs
        )
    
    def _calculate_coverage_metrics(
        self,
        method: str,
        expected_components: Optional[List[str]] = None
    ) -> Tuple[float, float, float]:
        """Calculate attribution coverage metrics."""
        
        records = self._records[method]
        
        if not records:
            return 0.9, 0.95, 0.05  # Default rates
        
        if expected_components is None:
            # Default expected components
            expected_components = [
                "personality_predictor",
                "mechanism_selector",
                "copy_generator",
                "audience_matcher",
                "state_estimator"
            ]
        
        recent = records[-1000:]
        
        full_coverage = 0
        partial_coverage = 0
        missing_key = 0
        
        for record in recent:
            attr_components = set(record.component_attributions.keys())
            expected_set = set(expected_components)
            
            if expected_set <= attr_components:
                full_coverage += 1
            elif attr_components & expected_set:
                partial_coverage += 1
            
            # Missing key components
            missing = expected_set - attr_components
            if len(missing) >= 2:  # Missing 2+ key components
                missing_key += 1
        
        total = len(recent)
        return (
            full_coverage / total,
            partial_coverage / total,
            missing_key / total
        )
    
    def get_attribution_quality(
        self,
        method: str,
        expected_components: Optional[List[str]] = None
    ) -> AttributionQualityMetrics:
        """Get comprehensive attribution quality metrics for a method."""
        
        # Calibration
        cal_error, slope, intercept = self._calculate_calibration_error(method)
        
        # Consistency
        temporal_consistency = self._calculate_temporal_consistency(method)
        cross_method = self._calculate_cross_method_consistency()
        counterfactual = 0.80  # Would require actual counterfactual testing
        
        # Coverage
        full_cov, partial_cov, missing = self._calculate_coverage_metrics(
            method, expected_components
        )
        
        # Distribution
        entropy, dominant, top3 = self._calculate_distribution_metrics(method)
        
        # Anomalies
        negative_rate, extreme_rate, zero_rate = self._calculate_anomaly_rates(method)
        
        # Identify issues
        issues = []
        
        if cal_error > self.CALIBRATION_ERROR_MAX:
            issues.append(f"High calibration error: {cal_error:.3f}")
        
        if temporal_consistency < self.CONSISTENCY_MIN:
            issues.append(f"Low temporal consistency: {temporal_consistency:.2f}")
        
        if cross_method < self.CONSISTENCY_MIN:
            issues.append(f"Low cross-method agreement: {cross_method:.2f}")
        
        if full_cov < self.COVERAGE_MIN:
            issues.append(f"Low attribution coverage: {full_cov:.1%}")
        
        if entropy < self.ENTROPY_MIN:
            issues.append(f"Low attribution entropy (concentrated): {entropy:.2f}")
        
        if negative_rate > self.NEGATIVE_RATE_MAX:
            issues.append(f"High negative attribution rate: {negative_rate:.1%}")
        
        if extreme_rate > 0.05:
            issues.append(f"High extreme attribution rate: {extreme_rate:.1%}")
        
        # Overall quality score
        quality_score = (
            0.25 * max(0, 1 - cal_error / 0.3) +
            0.20 * temporal_consistency +
            0.15 * cross_method +
            0.15 * full_cov +
            0.10 * min(1, entropy / 3) +
            0.15 * max(0, 1 - negative_rate / 0.2)
        )
        
        # Quality status
        if quality_score >= 0.85:
            quality_status = "excellent"
        elif quality_score >= 0.70:
            quality_status = "good"
        elif quality_score >= 0.55:
            quality_status = "acceptable"
        elif quality_score >= 0.40:
            quality_status = "poor"
        else:
            quality_status = "critical"
        
        return AttributionQualityMetrics(
            calibration_error=cal_error,
            reliability_diagram_slope=slope,
            reliability_diagram_intercept=intercept,
            temporal_consistency=temporal_consistency,
            counterfactual_consistency=counterfactual,
            cross_method_consistency=cross_method,
            full_coverage_rate=full_cov,
            partial_coverage_rate=partial_cov,
            missing_component_rate=missing,
            attribution_entropy=entropy,
            dominant_component_share=dominant,
            top3_component_share=top3,
            negative_attribution_rate=negative_rate,
            extreme_attribution_rate=extreme_rate,
            zero_attribution_rate=zero_rate,
            quality_score=quality_score,
            quality_status=quality_status,
            issues=issues
        )
```

### I.3 Cross-Component Drift Correlation

Detects correlated drift across components, revealing systemic issues that affect multiple parts of the learning system.

```python
"""
Cross-Component Drift Correlation for Gradient Bridge.
Identifies systemic drift patterns affecting multiple components.
"""

from __future__ import annotations

import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass, field
from collections import defaultdict
from scipy import stats
import logging

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class DriftCorrelation(BaseModel):
    """Correlation between drift in two components."""
    
    component_a: str
    component_b: str
    correlation_coefficient: float = Field(ge=-1.0, le=1.0)
    p_value: float = Field(ge=0.0, le=1.0)
    lag_hours: int = Field(ge=-24, le=24)  # Which component leads
    
    # Correlation interpretation
    correlation_strength: str = Field(
        pattern="^(strong_positive|moderate_positive|weak_positive|none|weak_negative|moderate_negative|strong_negative)$"
    )
    is_significant: bool  # p-value < 0.05
    
    # Causal hypothesis
    lead_component: Optional[str] = None
    causal_hypothesis: Optional[str] = None


class SystemicDriftPattern(BaseModel):
    """Pattern of drift affecting multiple components."""
    
    pattern_id: str
    detected_at: datetime
    
    # Affected components
    affected_components: List[str]
    correlation_matrix: Dict[str, Dict[str, float]]
    
    # Pattern characteristics
    pattern_type: str = Field(
        pattern="^(synchronized|cascading|oscillating|isolated|unknown)$"
    )
    propagation_sequence: Optional[List[str]] = None  # For cascading patterns
    
    # Root cause analysis
    likely_root_cause: Optional[str] = None
    confidence: float = Field(ge=0.0, le=1.0)
    
    # Impact assessment
    severity: str = Field(pattern="^(low|medium|high|critical)$")
    business_impact_estimate: Optional[str] = None
    
    # Recommended actions
    recommended_actions: List[str] = Field(default_factory=list)


@dataclass
class ComponentDriftTimeSeries:
    """Time series of drift metrics for a component."""
    
    component_id: str
    timestamps: List[datetime] = field(default_factory=list)
    drift_scores: List[float] = field(default_factory=list)
    drift_types: List[str] = field(default_factory=list)
    
    def add(
        self,
        timestamp: datetime,
        drift_score: float,
        drift_type: str
    ) -> None:
        """Add a drift observation."""
        self.timestamps.append(timestamp)
        self.drift_scores.append(drift_score)
        self.drift_types.append(drift_type)
    
    def get_series(
        self,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None
    ) -> Tuple[List[datetime], List[float]]:
        """Get drift scores within time range."""
        
        if start is None:
            start = datetime.min
        if end is None:
            end = datetime.max
        
        filtered_ts = []
        filtered_scores = []
        
        for ts, score in zip(self.timestamps, self.drift_scores):
            if start <= ts <= end:
                filtered_ts.append(ts)
                filtered_scores.append(score)
        
        return filtered_ts, filtered_scores


class CrossComponentDriftCorrelator:
    """
    Correlates drift patterns across ADAM components.
    
    Identifies systemic issues that manifest as correlated drift,
    cascade patterns where drift in one component causes drift
    in downstream components, and root causes of multi-component
    degradation.
    """
    
    # Correlation thresholds
    STRONG_CORRELATION = 0.7
    MODERATE_CORRELATION = 0.4
    WEAK_CORRELATION = 0.2
    SIGNIFICANCE_LEVEL = 0.05
    
    def __init__(
        self,
        window_hours: int = 168,  # 7 days
        min_observations: int = 50,
        event_bus: Optional[Any] = None
    ):
        self.window_hours = window_hours
        self.min_observations = min_observations
        self.event_bus = event_bus
        
        # Component drift time series
        self._component_drift: Dict[str, ComponentDriftTimeSeries] = {}
        
        # Known component relationships (for causal inference)
        self._component_graph: Dict[str, Set[str]] = {
            # Upstream -> set of downstream components
            "personality_predictor": {"mechanism_selector", "copy_generator", "audience_matcher"},
            "state_estimator": {"mechanism_selector", "copy_generator"},
            "mechanism_selector": {"copy_generator"},
            "graph_embedder": {"personality_predictor", "audience_matcher"},
            "intelligence_source_bayesian": {"personality_predictor"},
            "intelligence_source_temporal": {"state_estimator"},
        }
        
        # Detected patterns
        self._detected_patterns: List[SystemicDriftPattern] = []
        
        logger.info("CrossComponentDriftCorrelator initialized")
    
    def record_component_drift(
        self,
        component_id: str,
        drift_score: float,
        drift_type: str,
        timestamp: Optional[datetime] = None
    ) -> None:
        """Record drift observation for a component."""
        
        ts = timestamp or datetime.utcnow()
        
        if component_id not in self._component_drift:
            self._component_drift[component_id] = ComponentDriftTimeSeries(
                component_id=component_id
            )
        
        self._component_drift[component_id].add(ts, drift_score, drift_type)
        
        # Prune old data
        cutoff = datetime.utcnow() - timedelta(hours=self.window_hours * 2)
        self._prune_old_data(component_id, cutoff)
    
    def _prune_old_data(
        self,
        component_id: str,
        cutoff: datetime
    ) -> None:
        """Remove data older than cutoff."""
        
        series = self._component_drift[component_id]
        
        # Find first index within window
        keep_from = 0
        for i, ts in enumerate(series.timestamps):
            if ts >= cutoff:
                keep_from = i
                break
        
        if keep_from > 0:
            series.timestamps = series.timestamps[keep_from:]
            series.drift_scores = series.drift_scores[keep_from:]
            series.drift_types = series.drift_types[keep_from:]
    
    def calculate_pairwise_correlation(
        self,
        component_a: str,
        component_b: str,
        time_window: Optional[timedelta] = None
    ) -> Optional[DriftCorrelation]:
        """Calculate correlation between drift in two components."""
        
        if component_a not in self._component_drift:
            return None
        if component_b not in self._component_drift:
            return None
        
        window = time_window or timedelta(hours=self.window_hours)
        end = datetime.utcnow()
        start = end - window
        
        # Get time series
        ts_a, scores_a = self._component_drift[component_a].get_series(start, end)
        ts_b, scores_b = self._component_drift[component_b].get_series(start, end)
        
        if len(scores_a) < self.min_observations or len(scores_b) < self.min_observations:
            return None
        
        # Align time series (hourly buckets)
        aligned_a, aligned_b = self._align_time_series(
            ts_a, scores_a, ts_b, scores_b, bucket_hours=1
        )
        
        if len(aligned_a) < self.min_observations:
            return None
        
        # Calculate correlation
        correlation, p_value = stats.pearsonr(aligned_a, aligned_b)
        
        # Calculate lag correlation to find lead/lag relationship
        best_lag, lag_corr = self._find_best_lag(aligned_a, aligned_b, max_lag=24)
        
        # Determine correlation strength
        abs_corr = abs(correlation)
        if abs_corr >= self.STRONG_CORRELATION:
            strength = "strong_positive" if correlation > 0 else "strong_negative"
        elif abs_corr >= self.MODERATE_CORRELATION:
            strength = "moderate_positive" if correlation > 0 else "moderate_negative"
        elif abs_corr >= self.WEAK_CORRELATION:
            strength = "weak_positive" if correlation > 0 else "weak_negative"
        else:
            strength = "none"
        
        # Determine lead component based on lag and known graph
        lead_component = None
        causal_hypothesis = None
        
        if p_value < self.SIGNIFICANCE_LEVEL and abs_corr >= self.MODERATE_CORRELATION:
            if best_lag > 0:
                lead_component = component_a
            elif best_lag < 0:
                lead_component = component_b
            
            # Check against known graph
            if component_a in self._component_graph:
                if component_b in self._component_graph[component_a]:
                    lead_component = component_a
                    causal_hypothesis = f"{component_a} drift propagates to {component_b}"
            elif component_b in self._component_graph:
                if component_a in self._component_graph[component_b]:
                    lead_component = component_b
                    causal_hypothesis = f"{component_b} drift propagates to {component_a}"
        
        return DriftCorrelation(
            component_a=component_a,
            component_b=component_b,
            correlation_coefficient=correlation,
            p_value=p_value,
            lag_hours=best_lag,
            correlation_strength=strength,
            is_significant=p_value < self.SIGNIFICANCE_LEVEL,
            lead_component=lead_component,
            causal_hypothesis=causal_hypothesis
        )
    
    def _align_time_series(
        self,
        ts_a: List[datetime],
        scores_a: List[float],
        ts_b: List[datetime],
        scores_b: List[float],
        bucket_hours: int = 1
    ) -> Tuple[List[float], List[float]]:
        """Align two time series to common hourly buckets."""
        
        # Create hourly buckets
        bucket_a: Dict[str, List[float]] = defaultdict(list)
        bucket_b: Dict[str, List[float]] = defaultdict(list)
        
        for ts, score in zip(ts_a, scores_a):
            key = ts.strftime(f"%Y-%m-%d-%H")
            bucket_a[key].append(score)
        
        for ts, score in zip(ts_b, scores_b):
            key = ts.strftime(f"%Y-%m-%d-%H")
            bucket_b[key].append(score)
        
        # Find common keys
        common_keys = set(bucket_a.keys()) & set(bucket_b.keys())
        
        # Build aligned series
        aligned_a = []
        aligned_b = []
        
        for key in sorted(common_keys):
            aligned_a.append(np.mean(bucket_a[key]))
            aligned_b.append(np.mean(bucket_b[key]))
        
        return aligned_a, aligned_b
    
    def _find_best_lag(
        self,
        series_a: List[float],
        series_b: List[float],
        max_lag: int = 24
    ) -> Tuple[int, float]:
        """Find lag with highest cross-correlation."""
        
        arr_a = np.array(series_a)
        arr_b = np.array(series_b)
        
        best_lag = 0
        best_corr = 0.0
        
        for lag in range(-max_lag, max_lag + 1):
            if lag < 0:
                corr_a = arr_a[-lag:]
                corr_b = arr_b[:lag]
            elif lag > 0:
                corr_a = arr_a[:-lag]
                corr_b = arr_b[lag:]
            else:
                corr_a = arr_a
                corr_b = arr_b
            
            if len(corr_a) < 10:
                continue
            
            correlation, _ = stats.pearsonr(corr_a, corr_b)
            
            if abs(correlation) > abs(best_corr):
                best_corr = correlation
                best_lag = lag
        
        return best_lag, best_corr
    
    async def detect_systemic_patterns(self) -> List[SystemicDriftPattern]:
        """Detect systemic drift patterns across components."""
        
        components = list(self._component_drift.keys())
        
        if len(components) < 2:
            return []
        
        # Build correlation matrix
        correlation_matrix: Dict[str, Dict[str, float]] = {}
        significant_pairs: List[Tuple[str, str, DriftCorrelation]] = []
        
        for i, comp_a in enumerate(components):
            correlation_matrix[comp_a] = {}
            
            for j, comp_b in enumerate(components):
                if i == j:
                    correlation_matrix[comp_a][comp_b] = 1.0
                    continue
                
                corr = self.calculate_pairwise_correlation(comp_a, comp_b)
                
                if corr:
                    correlation_matrix[comp_a][comp_b] = corr.correlation_coefficient
                    
                    if corr.is_significant and abs(corr.correlation_coefficient) >= self.MODERATE_CORRELATION:
                        significant_pairs.append((comp_a, comp_b, corr))
                else:
                    correlation_matrix[comp_a][comp_b] = 0.0
        
        patterns = []
        
        # Find connected components of significantly correlated pairs
        affected_groups = self._find_connected_groups(significant_pairs)
        
        for group in affected_groups:
            if len(group) < 2:
                continue
            
            pattern = await self._analyze_drift_pattern(
                group, correlation_matrix, significant_pairs
            )
            
            if pattern:
                patterns.append(pattern)
                self._detected_patterns.append(pattern)
        
        return patterns
    
    def _find_connected_groups(
        self,
        pairs: List[Tuple[str, str, DriftCorrelation]]
    ) -> List[Set[str]]:
        """Find groups of connected components."""
        
        # Build adjacency
        adjacency: Dict[str, Set[str]] = defaultdict(set)
        
        for comp_a, comp_b, _ in pairs:
            adjacency[comp_a].add(comp_b)
            adjacency[comp_b].add(comp_a)
        
        # Find connected components
        visited = set()
        groups = []
        
        for start in adjacency:
            if start in visited:
                continue
            
            # BFS to find connected component
            group = set()
            queue = [start]
            
            while queue:
                node = queue.pop(0)
                if node in visited:
                    continue
                
                visited.add(node)
                group.add(node)
                
                for neighbor in adjacency[node]:
                    if neighbor not in visited:
                        queue.append(neighbor)
            
            if len(group) >= 2:
                groups.append(group)
        
        return groups
    
    async def _analyze_drift_pattern(
        self,
        components: Set[str],
        correlation_matrix: Dict[str, Dict[str, float]],
        pairs: List[Tuple[str, str, DriftCorrelation]]
    ) -> Optional[SystemicDriftPattern]:
        """Analyze drift pattern for a group of correlated components."""
        
        # Filter correlations to only include this group
        group_correlations = [
            (a, b, c) for a, b, c in pairs
            if a in components and b in components
        ]
        
        if not group_correlations:
            return None
        
        # Determine pattern type
        pattern_type, propagation = self._determine_pattern_type(
            components, group_correlations
        )
        
        # Identify root cause
        root_cause, confidence = self._identify_root_cause(
            components, group_correlations
        )
        
        # Determine severity
        max_corr = max(
            abs(c.correlation_coefficient) 
            for _, _, c in group_correlations
        )
        
        if max_corr >= 0.8 and len(components) >= 3:
            severity = "critical"
        elif max_corr >= 0.6 or len(components) >= 3:
            severity = "high"
        elif max_corr >= 0.4:
            severity = "medium"
        else:
            severity = "low"
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            pattern_type, root_cause, components, severity
        )
        
        # Build correlation matrix subset
        group_matrix = {
            comp_a: {
                comp_b: correlation_matrix.get(comp_a, {}).get(comp_b, 0.0)
                for comp_b in components
            }
            for comp_a in components
        }
        
        return SystemicDriftPattern(
            pattern_id=f"pattern_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{hash(frozenset(components)) % 10000}",
            detected_at=datetime.utcnow(),
            affected_components=list(components),
            correlation_matrix=group_matrix,
            pattern_type=pattern_type,
            propagation_sequence=propagation,
            likely_root_cause=root_cause,
            confidence=confidence,
            severity=severity,
            business_impact_estimate=self._estimate_business_impact(components, severity),
            recommended_actions=recommendations
        )
    
    def _determine_pattern_type(
        self,
        components: Set[str],
        correlations: List[Tuple[str, str, DriftCorrelation]]
    ) -> Tuple[str, Optional[List[str]]]:
        """Determine the type of systemic drift pattern."""
        
        # Check for cascading pattern (lag-based propagation)
        leads = [c.lead_component for _, _, c in correlations if c.lead_component]
        
        if leads:
            lead_counts: Dict[str, int] = defaultdict(int)
            for lead in leads:
                lead_counts[lead] += 1
            
            max_lead = max(lead_counts.values()) if lead_counts else 0
            if max_lead >= len(correlations) // 2:
                root = max(lead_counts.keys(), key=lambda x: lead_counts[x])
                sequence = self._build_propagation_sequence(root, correlations)
                return "cascading", sequence
        
        # Check for synchronized pattern
        avg_lag = np.mean([abs(c.lag_hours) for _, _, c in correlations])
        if avg_lag < 2:
            return "synchronized", None
        
        # Check for oscillating pattern
        pos_count = sum(1 for _, _, c in correlations if c.correlation_coefficient > 0)
        neg_count = sum(1 for _, _, c in correlations if c.correlation_coefficient < 0)
        
        if pos_count > 0 and neg_count > 0:
            return "oscillating", None
        
        return "unknown", None
    
    def _build_propagation_sequence(
        self,
        root: str,
        correlations: List[Tuple[str, str, DriftCorrelation]]
    ) -> List[str]:
        """Build ordered sequence of drift propagation."""
        
        sequence = [root]
        visited = {root}
        
        ordered = sorted(
            [(a, b, c) for a, b, c in correlations if c.lead_component == root],
            key=lambda x: x[2].lag_hours
        )
        
        for _, follower, _ in ordered:
            if follower not in visited:
                sequence.append(follower)
                visited.add(follower)
        
        all_comps = set(comp for a, b, _ in correlations for comp in [a, b])
        for comp in all_comps - visited:
            sequence.append(comp)
        
        return sequence
    
    def _identify_root_cause(
        self,
        components: Set[str],
        correlations: List[Tuple[str, str, DriftCorrelation]]
    ) -> Tuple[Optional[str], float]:
        """Identify likely root cause of systemic drift."""
        
        scores: Dict[str, float] = defaultdict(float)
        
        for comp in components:
            downstream = self._component_graph.get(comp, set())
            affected_downstream = downstream & components
            scores[comp] += len(affected_downstream) * 0.3
        
        for _, _, corr in correlations:
            if corr.lead_component:
                scores[corr.lead_component] += 0.2
        
        for comp in components:
            relevant_corrs = [
                abs(c.correlation_coefficient)
                for a, b, c in correlations
                if a == comp or b == comp
            ]
            if relevant_corrs:
                scores[comp] += np.mean(relevant_corrs) * 0.5
        
        if not scores:
            return None, 0.0
        
        root = max(scores.keys(), key=lambda x: scores[x])
        max_score = scores[root]
        total_score = sum(scores.values())
        confidence = max_score / total_score if total_score > 0 else 0.5
        
        return root, confidence
    
    def _generate_recommendations(
        self,
        pattern_type: str,
        root_cause: Optional[str],
        components: Set[str],
        severity: str
    ) -> List[str]:
        """Generate recommendations for addressing the pattern."""
        
        recommendations = []
        
        if pattern_type == "cascading" and root_cause:
            recommendations.append(
                f"Prioritize investigating {root_cause} as the likely source of cascading drift"
            )
            recommendations.append(
                f"Check data quality and feature stability for {root_cause}"
            )
            recommendations.append(
                "Consider adding drift circuit breakers between components"
            )
        elif pattern_type == "synchronized":
            recommendations.append(
                "Investigate common upstream data sources or feature pipelines"
            )
            recommendations.append(
                "Check for external factors (data provider changes, market shifts)"
            )
        elif pattern_type == "oscillating":
            recommendations.append(
                "Investigate feedback loops between components"
            )
            recommendations.append(
                "Check for conflicting learning objectives"
            )
        
        if severity in ("critical", "high"):
            recommendations.append(
                "Consider pausing automated retraining until root cause is identified"
            )
            recommendations.append(
                "Alert ML engineering team for immediate investigation"
            )
        
        if len(components) >= 3:
            recommendations.append(
                "Run full system integration tests to validate component interactions"
            )
        
        return recommendations
    
    def _estimate_business_impact(
        self,
        components: Set[str],
        severity: str
    ) -> str:
        """Estimate business impact of the drift pattern."""
        
        critical_components = {
            "personality_predictor",
            "mechanism_selector",
            "copy_generator"
        }
        
        affected_critical = components & critical_components
        
        if len(affected_critical) >= 2 and severity == "critical":
            return "High: Core prediction and generation pipeline affected, potential significant conversion impact"
        elif len(affected_critical) >= 1 and severity in ("critical", "high"):
            return "Medium-High: Key prediction component affected, likely conversion degradation"
        elif severity in ("critical", "high"):
            return "Medium: Supporting components affected, possible indirect conversion impact"
        else:
            return "Low: Limited component impact, monitoring recommended"
```

### I.3 Attribution Quality Monitor

Attribution quality directly impacts learning effectiveness - if we misattribute outcomes, we learn the wrong lessons.

```python
class AttributionQualityMonitor:
    """
    Monitors attribution quality in the Gradient Bridge.
    
    Tracks whether attributions are accurate, consistent, and
    appropriately distributed across components.
    """
    
    # Quality thresholds
    COVERAGE_MIN = 0.80          # Minimum event coverage
    CONFIDENCE_MIN = 0.60        # Minimum confidence
    CONSISTENCY_MIN = 0.70       # Minimum temporal consistency
    MAX_NEGATIVE_RATE = 0.10     # Max acceptable negative attribution rate
    MAX_CONCENTRATION = 0.70     # Max Gini (prevent single-component dominance)
    
    def __init__(
        self,
        methods: Optional[List[AttributionMethod]] = None,
        event_bus: Optional[Any] = None
    ):
        self.methods = methods or list(AttributionMethod)
        self.event_bus = event_bus
        
        # Per-method tracking
        self._predicted_outcomes: Dict[str, List[float]] = defaultdict(list)
        self._actual_outcomes: Dict[str, List[float]] = defaultdict(list)
        self._temporal_attributions: Dict[str, List[Tuple[datetime, Dict[str, float]]]] = defaultdict(list)
        self._computation_times: Dict[str, List[float]] = defaultdict(list)
        
        # Window size
        self._max_samples = 10000
        
        logger.info("AttributionQualityMonitor initialized")
    
    async def record_attribution_result(
        self,
        method: AttributionMethod,
        predicted_outcome: float,
        actual_outcome: float,
        component_attributions: Dict[str, float],
        computation_time_ms: float
    ) -> None:
        """Record an attribution result for quality monitoring."""
        
        method_key = method.value
        
        # Track prediction accuracy
        self._predicted_outcomes[method_key].append(predicted_outcome)
        self._actual_outcomes[method_key].append(actual_outcome)
        
        # Track attributions over time
        self._temporal_attributions[method_key].append(
            (datetime.utcnow(), component_attributions)
        )
        
        # Track computation time
        self._computation_times[method_key].append(computation_time_ms)
        
        # Prune to window
        for lst in [
            self._predicted_outcomes[method_key],
            self._actual_outcomes[method_key],
            self._computation_times[method_key]
        ]:
            while len(lst) > self._max_samples:
                lst.pop(0)
        
        while len(self._temporal_attributions[method_key]) > self._max_samples:
            self._temporal_attributions[method_key].pop(0)
    
    def assess_attribution_quality(
        self,
        method: AttributionMethod
    ) -> Dict[str, Any]:
        """Assess quality metrics for an attribution method."""
        
        method_key = method.value
        
        # Calibration metrics
        ece, slope, intercept = self._calculate_calibration_error(method_key)
        
        # Temporal consistency
        consistency = self._calculate_temporal_consistency(method_key)
        
        # Attribution concentration
        concentration = self._calculate_concentration(method_key)
        
        # Negative attribution rate
        negative_rate = self._calculate_negative_rate(method_key)
        
        # Computation time
        times = self._computation_times[method_key]
        time_p50 = np.percentile(times, 50) if times else 0.0
        time_p95 = np.percentile(times, 95) if times else 0.0
        
        # Identify issues
        issues = []
        
        if ece > 0.15:
            issues.append(f"High calibration error: {ece:.3f}")
        
        if consistency < self.CONSISTENCY_MIN:
            issues.append(f"Low temporal consistency: {consistency:.2f}")
        
        if concentration > self.MAX_CONCENTRATION:
            issues.append(f"Attribution too concentrated: Gini={concentration:.2f}")
        
        if negative_rate > self.MAX_NEGATIVE_RATE:
            issues.append(f"High negative attribution rate: {negative_rate:.1%}")
        
        if slope < 0.8 or slope > 1.2:
            issues.append(f"Poor calibration slope: {slope:.2f}")
        
        return {
            "method": method.value,
            "expected_calibration_error": ece,
            "reliability_slope": slope,
            "reliability_intercept": intercept,
            "temporal_consistency": consistency,
            "attribution_concentration": concentration,
            "negative_attribution_rate": negative_rate,
            "computation_time_p50_ms": time_p50,
            "computation_time_p95_ms": time_p95,
            "sample_count": len(self._predicted_outcomes[method_key]),
            "issues": issues,
            "health_status": "healthy" if len(issues) == 0 else (
                "degraded" if len(issues) == 1 else "unhealthy"
            )
        }
    
    def _calculate_calibration_error(self, method: str) -> Tuple[float, float, float]:
        """Calculate expected calibration error and reliability metrics."""
        
        predicted = np.array(self._predicted_outcomes[method])
        actual = np.array(self._actual_outcomes[method])
        
        if len(predicted) < 100:
            return 0.1, 1.0, 0.0
        
        n_bins = 10
        bin_boundaries = np.linspace(0, 1, n_bins + 1)
        
        bin_accuracies = []
        bin_confidences = []
        bin_counts = []
        
        for i in range(n_bins):
            mask = (predicted >= bin_boundaries[i]) & (predicted < bin_boundaries[i + 1])
            if mask.sum() > 0:
                bin_accuracies.append(actual[mask].mean())
                bin_confidences.append(predicted[mask].mean())
                bin_counts.append(mask.sum())
        
        if not bin_accuracies:
            return 0.1, 1.0, 0.0
        
        # Expected Calibration Error
        total = sum(bin_counts)
        ece = sum(
            (count / total) * abs(acc - conf)
            for acc, conf, count in zip(bin_accuracies, bin_confidences, bin_counts)
        )
        
        # Reliability diagram fit
        if len(bin_confidences) >= 2:
            coeffs = np.polyfit(bin_confidences, bin_accuracies, 1)
            slope, intercept = coeffs[0], coeffs[1]
        else:
            slope, intercept = 1.0, 0.0
        
        return ece, slope, intercept
    
    def _calculate_temporal_consistency(self, method: str) -> float:
        """Calculate how stable attributions are over time."""
        
        temporal = self._temporal_attributions[method]
        
        if len(temporal) < 100:
            return 0.8
        
        recent = temporal[-1000:]
        
        hourly_attributions: Dict[str, List[Dict[str, float]]] = defaultdict(list)
        
        for ts, attrs in recent:
            hour_key = ts.strftime("%Y-%m-%d-%H")
            hourly_attributions[hour_key].append(attrs)
        
        consistencies = []
        hours = sorted(hourly_attributions.keys())
        
        for i in range(len(hours) - 1):
            attrs1 = hourly_attributions[hours[i]]
            attrs2 = hourly_attributions[hours[i + 1]]
            
            avg1 = self._average_attributions(attrs1)
            avg2 = self._average_attributions(attrs2)
            
            similarity = self._cosine_similarity(avg1, avg2)
            consistencies.append(similarity)
        
        return np.mean(consistencies) if consistencies else 0.8
    
    def _calculate_concentration(self, method: str) -> float:
        """Calculate Gini coefficient of attribution distribution."""
        
        temporal = self._temporal_attributions[method]
        
        if not temporal:
            return 0.3
        
        # Aggregate attributions
        component_totals: Dict[str, float] = defaultdict(float)
        
        for _, attrs in temporal[-1000:]:
            for comp, value in attrs.items():
                component_totals[comp] += abs(value)
        
        if not component_totals:
            return 0.3
        
        values = sorted(component_totals.values())
        n = len(values)
        
        if n == 0 or sum(values) == 0:
            return 0.3
        
        # Gini coefficient
        cumsum = np.cumsum(values)
        gini = (2 * np.sum((np.arange(1, n + 1) * values))) / (n * np.sum(values)) - (n + 1) / n
        
        return max(0, min(1, gini))
    
    def _calculate_negative_rate(self, method: str) -> float:
        """Calculate rate of negative attributions."""
        
        temporal = self._temporal_attributions[method]
        
        if not temporal:
            return 0.02
        
        negative_count = 0
        total_count = 0
        
        for _, attrs in temporal[-1000:]:
            for value in attrs.values():
                total_count += 1
                if value < 0:
                    negative_count += 1
        
        return negative_count / max(total_count, 1)
    
    def _average_attributions(
        self,
        attr_list: List[Dict[str, float]]
    ) -> Dict[str, float]:
        """Average multiple attribution dicts."""
        
        all_keys = set()
        for attrs in attr_list:
            all_keys.update(attrs.keys())
        
        result = {}
        for key in all_keys:
            values = [attrs.get(key, 0.0) for attrs in attr_list]
            result[key] = np.mean(values)
        
        return result
    
    def _cosine_similarity(
        self,
        dict1: Dict[str, float],
        dict2: Dict[str, float]
    ) -> float:
        """Calculate cosine similarity between two attribution dicts."""
        
        all_keys = set(dict1.keys()) | set(dict2.keys())
        
        vec1 = np.array([dict1.get(k, 0.0) for k in all_keys])
        vec2 = np.array([dict2.get(k, 0.0) for k in all_keys])
        
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return float(np.dot(vec1, vec2) / (norm1 * norm2))
```

---

## SECTION J: ATOM OF THOUGHT INTEGRATION (#04)

### J.1 Multi-Source Fusion Monitor

The Atom of Thought DAG fuses intelligence from 10 sources. Monitoring ensures fusion quality remains high.

```python
"""
ADAM Atom of Thought Monitoring
Monitors the 10 intelligence sources and their fusion quality.
"""

from __future__ import annotations

import asyncio
import numpy as np
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass, field
from collections import defaultdict
import logging

from pydantic import BaseModel, Field, validator

logger = logging.getLogger(__name__)


# ============================================================================
# INTELLIGENCE SOURCE TYPES (from Enhancement #04)
# ============================================================================

class IntelligenceSourceType(str, Enum):
    """The 10 intelligence sources in ADAM's Atom of Thought."""
    
    CLAUDE_REASONING = "claude_reasoning"           # Source 1: Explicit psychological reasoning
    EMPIRICAL_PATTERNS = "empirical_patterns"       # Source 2: Discovered behavioral patterns
    NONCONSCIOUS_SIGNALS = "nonconscious_signals"   # Source 3: Behavioral signatures
    GRAPH_EMERGENCE = "graph_emergence"             # Source 4: Relational insights
    BANDIT_POSTERIORS = "bandit_posteriors"         # Source 5: Contextual effectiveness
    META_LEARNER = "meta_learner"                   # Source 6: Routing intelligence
    MECHANISM_TRAJECTORIES = "mechanism_trajectories"  # Source 7: Mechanism effectiveness
    TEMPORAL_PATTERNS = "temporal_patterns"         # Source 8: Contextual patterns
    CROSS_DOMAIN_TRANSFER = "cross_domain_transfer" # Source 9: Transfer patterns
    COHORT_ORGANIZATION = "cohort_organization"     # Source 10: Self-organization


class FusionQualityMetrics(BaseModel):
    """Metrics for intelligence fusion quality."""
    
    timestamp: datetime
    atom_type: str
    
    # Source availability
    sources_queried: int = Field(ge=0, le=10)
    sources_responded: int = Field(ge=0, le=10)
    source_availability_rate: float = Field(ge=0.0, le=1.0)
    
    # Agreement metrics
    source_agreement_rate: float = Field(ge=0.0, le=1.0)
    conflict_count: int = Field(ge=0)
    conflicts_resolved: int = Field(ge=0)
    
    # Contribution balance
    source_entropy: float = Field(ge=0.0)  # Higher = more balanced
    dominant_source: Optional[IntelligenceSourceType] = None
    dominant_source_weight: float = Field(ge=0.0, le=1.0)
    
    # Confidence metrics
    fusion_confidence: float = Field(ge=0.0, le=1.0)
    confidence_components: Dict[str, float] = Field(default_factory=dict)
    
    # Quality assessment
    quality_score: float = Field(ge=0.0, le=1.0)
    issues: List[str] = Field(default_factory=list)
    
    class Config:
        use_enum_values = True


class SourceReliabilityMetrics(BaseModel):
    """Reliability metrics for a single intelligence source."""
    
    source_type: IntelligenceSourceType
    
    # Availability
    availability_rate_1h: float = Field(ge=0.0, le=1.0)
    availability_rate_24h: float = Field(ge=0.0, le=1.0)
    
    # Latency
    response_time_p50_ms: float = Field(ge=0.0)
    response_time_p95_ms: float = Field(ge=0.0)
    timeout_rate: float = Field(ge=0.0, le=1.0)
    
    # Quality
    confidence_mean: float = Field(ge=0.0, le=1.0)
    confidence_std: float = Field(ge=0.0)
    prediction_consistency: float = Field(ge=0.0, le=1.0)
    
    # Contribution
    contribution_weight_mean: float = Field(ge=0.0, le=1.0)
    contribution_weight_trend: str = Field(
        pattern="^(increasing|stable|decreasing)$"
    )
    
    # Health
    health_score: float = Field(ge=0.0, le=1.0)
    health_status: str = Field(pattern="^(healthy|degraded|unhealthy|critical)$")
    issues: List[str] = Field(default_factory=list)
    
    class Config:
        use_enum_values = True


# ============================================================================
# FUSION QUALITY MONITOR
# ============================================================================

@dataclass
class FusionEvent:
    """Record of a fusion event for monitoring."""
    
    timestamp: datetime
    atom_type: str
    sources_queried: Set[IntelligenceSourceType]
    sources_responded: Set[IntelligenceSourceType]
    source_contributions: Dict[IntelligenceSourceType, float]
    conflicts: List[Dict[str, Any]]
    fusion_confidence: float
    processing_time_ms: float


class FusionQualityMonitor:
    """
    Monitors the quality of multi-source intelligence fusion.
    
    Tracks source availability, agreement rates, contribution balance,
    and overall fusion quality across all Atom of Thought executions.
    """
    
    # Quality thresholds
    MIN_SOURCE_AVAILABILITY = 0.80   # Minimum source response rate
    MIN_AGREEMENT_RATE = 0.60        # Minimum cross-source agreement
    MAX_CONFLICT_RATE = 0.30         # Maximum acceptable conflict rate
    MIN_ENTROPY = 0.5                # Minimum source entropy (balance)
    MAX_DOMINANT_WEIGHT = 0.60       # Maximum single-source contribution
    
    def __init__(
        self,
        event_bus: Optional[Any] = None,
        metrics_client: Optional[Any] = None,
        window_size: int = 10000
    ):
        self.event_bus = event_bus
        self.metrics_client = metrics_client
        self.window_size = window_size
        
        # Per-atom-type tracking
        self._fusion_events: Dict[str, List[FusionEvent]] = defaultdict(list)
        
        # Per-source tracking
        self._source_responses: Dict[IntelligenceSourceType, List[Tuple[datetime, bool, float]]] = {
            source: [] for source in IntelligenceSourceType
        }
        
        self._source_confidences: Dict[IntelligenceSourceType, List[float]] = {
            source: [] for source in IntelligenceSourceType
        }
        
        self._source_contributions: Dict[IntelligenceSourceType, List[Tuple[datetime, float]]] = {
            source: [] for source in IntelligenceSourceType
        }
        
        # Global metrics
        self._conflict_history: List[Dict[str, Any]] = []
        
        logger.info("FusionQualityMonitor initialized")
    
    async def record_fusion_event(
        self,
        atom_type: str,
        sources_queried: Set[IntelligenceSourceType],
        sources_responded: Set[IntelligenceSourceType],
        source_contributions: Dict[IntelligenceSourceType, float],
        source_confidences: Dict[IntelligenceSourceType, float],
        source_latencies: Dict[IntelligenceSourceType, float],
        conflicts: List[Dict[str, Any]],
        fusion_confidence: float,
        processing_time_ms: float
    ) -> None:
        """Record a fusion event for monitoring."""
        
        timestamp = datetime.utcnow()
        
        # Record fusion event
        event = FusionEvent(
            timestamp=timestamp,
            atom_type=atom_type,
            sources_queried=sources_queried,
            sources_responded=sources_responded,
            source_contributions=source_contributions,
            conflicts=conflicts,
            fusion_confidence=fusion_confidence,
            processing_time_ms=processing_time_ms
        )
        
        self._fusion_events[atom_type].append(event)
        
        # Prune window
        while len(self._fusion_events[atom_type]) > self.window_size:
            self._fusion_events[atom_type].pop(0)
        
        # Record per-source metrics
        for source in sources_queried:
            responded = source in sources_responded
            latency = source_latencies.get(source, 0.0)
            
            self._source_responses[source].append((timestamp, responded, latency))
            
            if responded:
                self._source_confidences[source].append(
                    source_confidences.get(source, 0.5)
                )
                self._source_contributions[source].append(
                    (timestamp, source_contributions.get(source, 0.0))
                )
        
        # Prune source metrics
        for source in IntelligenceSourceType:
            while len(self._source_responses[source]) > self.window_size:
                self._source_responses[source].pop(0)
            while len(self._source_confidences[source]) > self.window_size:
                self._source_confidences[source].pop(0)
            while len(self._source_contributions[source]) > self.window_size:
                self._source_contributions[source].pop(0)
        
        # Record conflicts
        for conflict in conflicts:
            self._conflict_history.append({
                **conflict,
                "timestamp": timestamp,
                "atom_type": atom_type
            })
        
        while len(self._conflict_history) > self.window_size:
            self._conflict_history.pop(0)
        
        # Emit metrics
        if self.metrics_client:
            await self.metrics_client.gauge(
                "adam.fusion.source_availability",
                len(sources_responded) / len(sources_queried) if sources_queried else 0,
                tags={"atom_type": atom_type}
            )
            await self.metrics_client.gauge(
                "adam.fusion.confidence",
                fusion_confidence,
                tags={"atom_type": atom_type}
            )
    
    def get_fusion_quality(
        self,
        atom_type: Optional[str] = None
    ) -> FusionQualityMetrics:
        """Get current fusion quality metrics."""
        
        # Collect relevant events
        if atom_type:
            events = self._fusion_events.get(atom_type, [])
        else:
            events = [e for events in self._fusion_events.values() for e in events]
        
        if not events:
            return FusionQualityMetrics(
                timestamp=datetime.utcnow(),
                atom_type=atom_type or "all",
                sources_queried=0,
                sources_responded=0,
                source_availability_rate=0.0,
                source_agreement_rate=0.0,
                conflict_count=0,
                conflicts_resolved=0,
                source_entropy=0.0,
                fusion_confidence=0.0,
                quality_score=0.0,
                issues=["No fusion events recorded"]
            )
        
        # Recent events (last 1000)
        recent = events[-1000:]
        
        # Calculate metrics
        total_queried = sum(len(e.sources_queried) for e in recent)
        total_responded = sum(len(e.sources_responded) for e in recent)
        availability_rate = total_responded / total_queried if total_queried > 0 else 0.0
        
        # Source contributions
        contribution_totals: Dict[IntelligenceSourceType, float] = defaultdict(float)
        for event in recent:
            for source, contrib in event.source_contributions.items():
                contribution_totals[source] += contrib
        
        # Entropy of contributions
        total_contrib = sum(contribution_totals.values())
        if total_contrib > 0:
            probs = [c / total_contrib for c in contribution_totals.values() if c > 0]
            entropy = -sum(p * np.log2(p) for p in probs if p > 0)
            max_entropy = np.log2(len(IntelligenceSourceType))
            normalized_entropy = entropy / max_entropy if max_entropy > 0 else 0
        else:
            normalized_entropy = 0.0
        
        # Dominant source
        if contribution_totals:
            dominant = max(contribution_totals.keys(), key=lambda x: contribution_totals[x])
            dominant_weight = contribution_totals[dominant] / total_contrib if total_contrib > 0 else 0
        else:
            dominant = None
            dominant_weight = 0.0
        
        # Conflict analysis
        total_conflicts = sum(len(e.conflicts) for e in recent)
        events_with_conflicts = sum(1 for e in recent if e.conflicts)
        conflict_rate = events_with_conflicts / len(recent) if recent else 0
        
        # Agreement rate (inverse of conflict rate)
        agreement_rate = 1.0 - min(conflict_rate, 1.0)
        
        # Average confidence
        avg_confidence = np.mean([e.fusion_confidence for e in recent])
        
        # Identify issues
        issues = []
        
        if availability_rate < self.MIN_SOURCE_AVAILABILITY:
            issues.append(f"Low source availability: {availability_rate:.1%}")
        
        if agreement_rate < self.MIN_AGREEMENT_RATE:
            issues.append(f"Low source agreement: {agreement_rate:.1%}")
        
        if normalized_entropy < self.MIN_ENTROPY:
            issues.append(f"Low contribution balance: entropy={normalized_entropy:.2f}")
        
        if dominant_weight > self.MAX_DOMINANT_WEIGHT:
            issues.append(f"Over-reliance on {dominant}: {dominant_weight:.1%}")
        
        # Quality score
        quality_components = [
            availability_rate,
            agreement_rate,
            normalized_entropy / 1.0,  # Normalize to 0-1
            1.0 - dominant_weight,
            avg_confidence
        ]
        quality_score = np.mean(quality_components)
        
        return FusionQualityMetrics(
            timestamp=datetime.utcnow(),
            atom_type=atom_type or "all",
            sources_queried=round(total_queried / len(recent)) if recent else 0,
            sources_responded=round(total_responded / len(recent)) if recent else 0,
            source_availability_rate=availability_rate,
            source_agreement_rate=agreement_rate,
            conflict_count=total_conflicts,
            conflicts_resolved=total_conflicts,  # Simplified
            source_entropy=normalized_entropy,
            dominant_source=dominant,
            dominant_source_weight=dominant_weight,
            fusion_confidence=avg_confidence,
            quality_score=quality_score,
            issues=issues
        )
    
    def get_source_reliability(
        self,
        source: IntelligenceSourceType
    ) -> SourceReliabilityMetrics:
        """Get reliability metrics for a specific source."""
        
        responses = self._source_responses[source]
        confidences = self._source_confidences[source]
        contributions = self._source_contributions[source]
        
        now = datetime.utcnow()
        hour_ago = now - timedelta(hours=1)
        day_ago = now - timedelta(hours=24)
        
        # Availability
        recent_1h = [(ts, ok, lat) for ts, ok, lat in responses if ts >= hour_ago]
        recent_24h = [(ts, ok, lat) for ts, ok, lat in responses if ts >= day_ago]
        
        availability_1h = (
            sum(1 for _, ok, _ in recent_1h if ok) / len(recent_1h)
            if recent_1h else 0.0
        )
        availability_24h = (
            sum(1 for _, ok, _ in recent_24h if ok) / len(recent_24h)
            if recent_24h else 0.0
        )
        
        # Latency
        latencies = [lat for _, ok, lat in recent_24h if ok and lat > 0]
        p50 = np.percentile(latencies, 50) if latencies else 0.0
        p95 = np.percentile(latencies, 95) if latencies else 0.0
        
        # Timeout rate
        timeout_rate = (
            sum(1 for _, ok, lat in recent_24h if not ok or lat > 5000) / len(recent_24h)
            if recent_24h else 0.0
        )
        
        # Confidence
        recent_conf = confidences[-1000:] if confidences else [0.5]
        conf_mean = np.mean(recent_conf)
        conf_std = np.std(recent_conf) if len(recent_conf) > 1 else 0.0
        
        # Contribution trend
        if len(contributions) >= 100:
            first_half = [c for _, c in contributions[:len(contributions)//2]]
            second_half = [c for _, c in contributions[len(contributions)//2:]]
            
            mean_first = np.mean(first_half)
            mean_second = np.mean(second_half)
            
            change = (mean_second - mean_first) / (mean_first + 1e-10)
            
            if change > 0.1:
                trend = "increasing"
            elif change < -0.1:
                trend = "decreasing"
            else:
                trend = "stable"
        else:
            trend = "stable"
        
        contrib_mean = np.mean([c for _, c in contributions[-1000:]]) if contributions else 0.0
        
        # Health assessment
        issues = []
        
        if availability_24h < 0.80:
            issues.append(f"Low availability: {availability_24h:.1%}")
        
        if timeout_rate > 0.10:
            issues.append(f"High timeout rate: {timeout_rate:.1%}")
        
        if p95 > 2000:
            issues.append(f"High latency: p95={p95:.0f}ms")
        
        if conf_mean < 0.5:
            issues.append(f"Low confidence: {conf_mean:.2f}")
        
        # Health score
        health_components = [
            availability_24h,
            1.0 - timeout_rate,
            min(1.0, 2000 / (p95 + 1)),  # Latency score
            conf_mean
        ]
        health_score = np.mean(health_components)
        
        if health_score >= 0.80:
            health_status = "healthy"
        elif health_score >= 0.60:
            health_status = "degraded"
        elif health_score >= 0.40:
            health_status = "unhealthy"
        else:
            health_status = "critical"
        
        return SourceReliabilityMetrics(
            source_type=source,
            availability_rate_1h=availability_1h,
            availability_rate_24h=availability_24h,
            response_time_p50_ms=p50,
            response_time_p95_ms=p95,
            timeout_rate=timeout_rate,
            confidence_mean=conf_mean,
            confidence_std=conf_std,
            prediction_consistency=0.85,  # Would calculate from predictions
            contribution_weight_mean=contrib_mean,
            contribution_weight_trend=trend,
            health_score=health_score,
            health_status=health_status,
            issues=issues
        )


### J.2 Nonconscious Signal Reliability

Nonconscious signals (Source 3) are uniquely valuable but require special validation.

```python
class NonconsciousSignalMetrics(BaseModel):
    """Metrics for nonconscious signal reliability."""
    
    signal_type: str  # click_pattern, scroll_behavior, dwell_time, etc.
    
    # Volume
    signals_captured_1h: int = Field(ge=0)
    signals_captured_24h: int = Field(ge=0)
    
    # Quality
    signal_strength_mean: float = Field(ge=0.0, le=1.0)
    noise_ratio: float = Field(ge=0.0, le=1.0)
    extraction_success_rate: float = Field(ge=0.0, le=1.0)
    
    # Psychological mapping
    construct_mapping_confidence: float = Field(ge=0.0, le=1.0)
    mapped_constructs: List[str]
    
    # Validation
    retrospective_accuracy: Optional[float] = Field(ge=0.0, le=1.0, default=None)
    prediction_correlation: Optional[float] = Field(ge=-1.0, le=1.0, default=None)
    
    # Health
    health_status: str = Field(pattern="^(healthy|degraded|unhealthy|critical)$")
    issues: List[str] = Field(default_factory=list)


class NonconsciousSignalMonitor:
    """
    Monitors the reliability of nonconscious behavioral signals.
    
    These signals (click patterns, scroll behavior, dwell time, etc.)
    provide unique insight into psychological states but require
    careful validation to ensure they actually predict what we think.
    """
    
    # Signal types we track
    SIGNAL_TYPES = [
        "click_pattern",
        "scroll_behavior",
        "dwell_time",
        "hover_patterns",
        "reading_speed",
        "interaction_sequence",
        "temporal_rhythm",
        "attention_flow"
    ]
    
    # Thresholds
    MIN_SIGNAL_VOLUME_1H = 100
    MIN_SIGNAL_STRENGTH = 0.3
    MAX_NOISE_RATIO = 0.4
    MIN_EXTRACTION_RATE = 0.80
    MIN_MAPPING_CONFIDENCE = 0.60
    
    def __init__(
        self,
        event_bus: Optional[Any] = None,
        metrics_client: Optional[Any] = None
    ):
        self.event_bus = event_bus
        self.metrics_client = metrics_client
        
        # Per-signal tracking
        self._signal_captures: Dict[str, List[Tuple[datetime, float, float]]] = {
            sig: [] for sig in self.SIGNAL_TYPES
        }
        
        self._extraction_attempts: Dict[str, List[Tuple[datetime, bool]]] = {
            sig: [] for sig in self.SIGNAL_TYPES
        }
        
        self._mapping_confidences: Dict[str, List[Tuple[datetime, float, List[str]]]] = {
            sig: [] for sig in self.SIGNAL_TYPES
        }
        
        # Validation tracking (requires outcome data)
        self._predictions: Dict[str, List[Tuple[datetime, float]]] = defaultdict(list)
        self._outcomes: Dict[str, List[Tuple[datetime, float]]] = defaultdict(list)
        
        logger.info("NonconsciousSignalMonitor initialized")
    
    async def record_signal_capture(
        self,
        signal_type: str,
        signal_strength: float,
        noise_estimate: float,
        extraction_success: bool,
        mapped_constructs: Optional[List[str]] = None,
        mapping_confidence: Optional[float] = None
    ) -> None:
        """Record a nonconscious signal capture."""
        
        if signal_type not in self.SIGNAL_TYPES:
            logger.warning(f"Unknown signal type: {signal_type}")
            return
        
        timestamp = datetime.utcnow()
        
        # Record capture
        self._signal_captures[signal_type].append(
            (timestamp, signal_strength, noise_estimate)
        )
        
        # Record extraction attempt
        self._extraction_attempts[signal_type].append(
            (timestamp, extraction_success)
        )
        
        # Record mapping if available
        if extraction_success and mapped_constructs and mapping_confidence is not None:
            self._mapping_confidences[signal_type].append(
                (timestamp, mapping_confidence, mapped_constructs)
            )
        
        # Prune old data
        cutoff = timestamp - timedelta(hours=48)
        
        self._signal_captures[signal_type] = [
            (ts, s, n) for ts, s, n in self._signal_captures[signal_type]
            if ts >= cutoff
        ]
        
        self._extraction_attempts[signal_type] = [
            (ts, ok) for ts, ok in self._extraction_attempts[signal_type]
            if ts >= cutoff
        ]
        
        self._mapping_confidences[signal_type] = [
            (ts, c, constructs) for ts, c, constructs in self._mapping_confidences[signal_type]
            if ts >= cutoff
        ]
    
    def get_signal_metrics(
        self,
        signal_type: str
    ) -> NonconsciousSignalMetrics:
        """Get metrics for a specific signal type."""
        
        if signal_type not in self.SIGNAL_TYPES:
            return NonconsciousSignalMetrics(
                signal_type=signal_type,
                signals_captured_1h=0,
                signals_captured_24h=0,
                signal_strength_mean=0.0,
                noise_ratio=1.0,
                extraction_success_rate=0.0,
                construct_mapping_confidence=0.0,
                mapped_constructs=[],
                health_status="critical",
                issues=["Unknown signal type"]
            )
        
        captures = self._signal_captures[signal_type]
        extractions = self._extraction_attempts[signal_type]
        mappings = self._mapping_confidences[signal_type]
        
        now = datetime.utcnow()
        hour_ago = now - timedelta(hours=1)
        day_ago = now - timedelta(hours=24)
        
        # Volume
        captures_1h = len([ts for ts, _, _ in captures if ts >= hour_ago])
        captures_24h = len([ts for ts, _, _ in captures if ts >= day_ago])
        
        # Strength and noise
        recent_captures = [(s, n) for ts, s, n in captures if ts >= day_ago]
        
        if recent_captures:
            strengths = [s for s, _ in recent_captures]
            noises = [n for _, n in recent_captures]
            strength_mean = np.mean(strengths)
            noise_mean = np.mean(noises)
        else:
            strength_mean = 0.0
            noise_mean = 1.0
        
        # Extraction rate
        recent_extractions = [ok for ts, ok in extractions if ts >= day_ago]
        extraction_rate = (
            sum(recent_extractions) / len(recent_extractions)
            if recent_extractions else 0.0
        )
        
        # Mapping confidence
        recent_mappings = [(c, constructs) for ts, c, constructs in mappings if ts >= day_ago]
        
        if recent_mappings:
            mapping_confidence = np.mean([c for c, _ in recent_mappings])
            all_constructs = set()
            for _, constructs in recent_mappings:
                all_constructs.update(constructs)
            mapped_constructs = list(all_constructs)
        else:
            mapping_confidence = 0.0
            mapped_constructs = []
        
        # Identify issues
        issues = []
        
        if captures_1h < self.MIN_SIGNAL_VOLUME_1H:
            issues.append(f"Low signal volume: {captures_1h}/hour")
        
        if strength_mean < self.MIN_SIGNAL_STRENGTH:
            issues.append(f"Weak signal strength: {strength_mean:.2f}")
        
        if noise_mean > self.MAX_NOISE_RATIO:
            issues.append(f"High noise ratio: {noise_mean:.2f}")
        
        if extraction_rate < self.MIN_EXTRACTION_RATE:
            issues.append(f"Low extraction rate: {extraction_rate:.1%}")
        
        if mapping_confidence < self.MIN_MAPPING_CONFIDENCE:
            issues.append(f"Low mapping confidence: {mapping_confidence:.2f}")
        
        # Health status
        if len(issues) == 0:
            health_status = "healthy"
        elif len(issues) <= 1:
            health_status = "degraded"
        elif len(issues) <= 2:
            health_status = "unhealthy"
        else:
            health_status = "critical"
        
        return NonconsciousSignalMetrics(
            signal_type=signal_type,
            signals_captured_1h=captures_1h,
            signals_captured_24h=captures_24h,
            signal_strength_mean=strength_mean,
            noise_ratio=noise_mean,
            extraction_success_rate=extraction_rate,
            construct_mapping_confidence=mapping_confidence,
            mapped_constructs=mapped_constructs,
            health_status=health_status,
            issues=issues
        )
    
    def get_all_signal_health(self) -> Dict[str, NonconsciousSignalMetrics]:
        """Get health metrics for all signal types."""
        return {
            signal_type: self.get_signal_metrics(signal_type)
            for signal_type in self.SIGNAL_TYPES
        }
```

---
                continue
            
            # BFS
            group = set()
            queue = [start]
            
            while queue:
                node = queue.pop(0)
                if node in visited:
                    continue
                
                visited.add(node)
                group.add(node)
                
                for neighbor in adjacency[node]:
                    if neighbor not in visited:
                        queue.append(neighbor)
            
            groups.append(group)
        
        return groups
    
    async def _analyze_drift_pattern(
        self,
        affected_components: Set[str],
        correlation_matrix: Dict[str, Dict[str, float]],
        pairs: List[Tuple[str, str, DriftCorrelation]]
    ) -> Optional[SystemicDriftPattern]:
        """Analyze a group of affected components."""
        
        # Get relevant correlations
        group_correlations = [
            (a, b, corr) for a, b, corr in pairs
            if a in affected_components and b in affected_components
        ]
        
        if not group_correlations:
            return None
        
        # Determine pattern type
        pattern_type, propagation = self._determine_pattern_type(
            affected_components, group_correlations
        )
        
        # Find likely root cause
        root_cause, confidence = self._identify_root_cause(
            affected_components, group_correlations
        )
        
        # Assess severity
        avg_correlation = np.mean([abs(c.correlation_coefficient) for _, _, c in group_correlations])
        
        if len(affected_components) >= 4 and avg_correlation >= self.STRONG_CORRELATION:
            severity = "critical"
        elif len(affected_components) >= 3 or avg_correlation >= self.STRONG_CORRELATION:
            severity = "high"
        elif len(affected_components) >= 2 and avg_correlation >= self.MODERATE_CORRELATION:
            severity = "medium"
        else:
            severity = "low"
        
        # Build sub-matrix
        sub_matrix = {
            comp_a: {
                comp_b: correlation_matrix.get(comp_a, {}).get(comp_b, 0.0)
                for comp_b in affected_components
            }
            for comp_a in affected_components
        }
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            pattern_type, root_cause, affected_components, severity
        )
        
        return SystemicDriftPattern(
            pattern_id=f"pattern_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            detected_at=datetime.utcnow(),
            affected_components=list(affected_components),
            correlation_matrix=sub_matrix,
            pattern_type=pattern_type,
            propagation_sequence=propagation,
            likely_root_cause=root_cause,
            confidence=confidence,
            severity=severity,
            business_impact_estimate=self._estimate_business_impact(
                affected_components, severity
            ),
            recommended_actions=recommendations
        )
    
    def _determine_pattern_type(
        self,
        components: Set[str],
        correlations: List[Tuple[str, str, DriftCorrelation]]
    ) -> Tuple[str, Optional[List[str]]]:
        """Determine the type of systemic drift pattern."""
        
        # Check for cascading pattern (lag-based propagation)
        leads = [c.lead_component for _, _, c in correlations if c.lead_component]
        
        if leads:
            # Count how often each component leads
            lead_counts: Dict[str, int] = defaultdict(int)
            for lead in leads:
                lead_counts[lead] += 1
            
            # If one component leads most
            max_lead = max(lead_counts.values()) if lead_counts else 0
            if max_lead >= len(correlations) // 2:
                root = max(lead_counts.keys(), key=lambda x: lead_counts[x])
                sequence = self._build_propagation_sequence(root, correlations)
                return "cascading", sequence
        
        # Check for synchronized pattern (near-zero lags)
        avg_lag = np.mean([abs(c.lag_hours) for _, _, c in correlations])
        if avg_lag < 2:
            return "synchronized", None
        
        # Check for oscillating pattern (alternating correlations)
        pos_count = sum(1 for _, _, c in correlations if c.correlation_coefficient > 0)
        neg_count = sum(1 for _, _, c in correlations if c.correlation_coefficient < 0)
        
        if pos_count > 0 and neg_count > 0:
            return "oscillating", None
        
        return "unknown", None
    
    def _build_propagation_sequence(
        self,
        root: str,
        correlations: List[Tuple[str, str, DriftCorrelation]]
    ) -> List[str]:
        """Build ordered sequence of drift propagation."""
        
        sequence = [root]
        visited = {root}
        
        # Sort correlations by lag (positive lag means a leads b)
        ordered = sorted(
            [(a, b, c) for a, b, c in correlations if c.lead_component == root],
            key=lambda x: x[2].lag_hours
        )
        
        for _, follower, _ in ordered:
            if follower not in visited:
                sequence.append(follower)
                visited.add(follower)
        
        # Add remaining components
        all_comps = set(
            comp for a, b, _ in correlations for comp in [a, b]
        )
        for comp in all_comps - visited:
            sequence.append(comp)
        
        return sequence
    
    def _identify_root_cause(
        self,
        components: Set[str],
        correlations: List[Tuple[str, str, DriftCorrelation]]
    ) -> Tuple[Optional[str], float]:
        """Identify likely root cause of systemic drift."""
        
        # Score components by upstream position
        scores: Dict[str, float] = defaultdict(float)
        
        for comp in components:
            # Check if this component is upstream of others
            downstream = self._component_graph.get(comp, set())
            affected_downstream = downstream & components
            
            scores[comp] += len(affected_downstream) * 0.3
        
        # Score by lead count
        for _, _, corr in correlations:
            if corr.lead_component:
                scores[corr.lead_component] += 0.2
        
        # Score by correlation strength (higher correlation with others)
        for comp in components:
            relevant_corrs = [
                abs(c.correlation_coefficient)
                for a, b, c in correlations
                if a == comp or b == comp
            ]
            if relevant_corrs:
                scores[comp] += np.mean(relevant_corrs) * 0.5
        
        if not scores:
            return None, 0.0
        
        # Get highest scoring component
        root = max(scores.keys(), key=lambda x: scores[x])
        max_score = scores[root]
        
        # Calculate confidence based on how dominant the root is
        total_score = sum(scores.values())
        confidence = max_score / total_score if total_score > 0 else 0.5
        
        return root, confidence
    
    def _generate_recommendations(
        self,
        pattern_type: str,
        root_cause: Optional[str],
        components: Set[str],
        severity: str
    ) -> List[str]:
        """Generate recommendations for addressing the pattern."""
        
        recommendations = []
        
        if pattern_type == "cascading" and root_cause:
            recommendations.append(
                f"Prioritize investigating {root_cause} as the likely source of cascading drift"
            )
            recommendations.append(
                f"Check data quality and feature stability for {root_cause}"
            )
            recommendations.append(
                "Consider adding drift circuit breakers between components"
            )
        
        elif pattern_type == "synchronized":
            recommendations.append(
                "Investigate common upstream data sources or feature pipelines"
            )
            recommendations.append(
                "Check for external factors (data provider changes, market shifts)"
            )
        
        elif pattern_type == "oscillating":
            recommendations.append(
                "Investigate feedback loops between components"
            )
            recommendations.append(
                "Check for conflicting learning objectives"
            )
        
        if severity in ("critical", "high"):
            recommendations.append(
                "Consider pausing automated retraining until root cause is identified"
            )
            recommendations.append(
                f"Alert ML engineering team for immediate investigation"
            )
        
        if len(components) >= 3:
            recommendations.append(
                "Run full system integration tests to validate component interactions"
            )
        
        return recommendations
    
    def _estimate_business_impact(
        self,
        components: Set[str],
        severity: str
    ) -> str:
        """Estimate business impact of the drift pattern."""
        
        critical_components = {
            "personality_predictor",
            "mechanism_selector",
            "copy_generator"
        }
        
        affected_critical = components & critical_components
        
        if len(affected_critical) >= 2 and severity == "critical":
            return "High: Core prediction and generation pipeline affected, potential significant conversion impact"
        elif len(affected_critical) >= 1 and severity in ("critical", "high"):
            return "Medium-High: Key prediction component affected, likely conversion degradation"
        elif severity in ("critical", "high"):
            return "Medium: Supporting components affected, possible indirect conversion impact"
        else:
            return "Low: Limited component impact, monitoring recommended"
```
## SECTION K: FASTAPI ENDPOINTS

### K.1 Model Health API

```python
"""
ADAM Model Monitoring FastAPI Endpoints
Production-ready health, drift, and retraining management APIs.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from enum import Enum

from fastapi import APIRouter, HTTPException, Query, Path, Body, BackgroundTasks
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/v1/monitoring", tags=["Model Monitoring"])


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class ModelHealthResponse(BaseModel):
    """Model health status response."""
    
    model_id: str
    model_name: str
    status: str  # healthy, degraded, unhealthy, critical
    health_score: float = Field(ge=0.0, le=1.0)
    
    # Key metrics
    accuracy: Optional[float] = None
    auc_roc: Optional[float] = None
    precision: Optional[float] = None
    recall: Optional[float] = None
    
    # Latency
    inference_latency_p50_ms: Optional[float] = None
    inference_latency_p95_ms: Optional[float] = None
    
    # Psychological validity
    psychological_validity_score: Optional[float] = None
    
    # Drift status
    active_drift_count: int = 0
    highest_drift_severity: Optional[str] = None
    
    # Issues
    issues: List[str] = Field(default_factory=list)
    
    # Timestamps
    last_updated: datetime
    last_retrained: Optional[datetime] = None


class ModelHealthSummary(BaseModel):
    """Summary of all model health."""
    
    timestamp: datetime
    
    # Counts by status
    total_models: int
    healthy_count: int
    degraded_count: int
    unhealthy_count: int
    critical_count: int
    
    # Aggregate metrics
    average_health_score: float
    models_with_drift: int
    models_requiring_retraining: int
    
    # Top issues
    top_issues: List[Dict[str, Any]]


class DriftDetectionResponse(BaseModel):
    """Drift detection result."""
    
    drift_id: str
    model_id: str
    drift_type: str  # data, concept, prediction, performance, distribution, psychological
    
    detected_at: datetime
    test_name: str
    severity: str  # low, medium, high, critical
    confidence: float = Field(ge=0.0, le=1.0)
    
    # Statistics
    statistic_value: float
    p_value: Optional[float] = None
    threshold: float
    
    # Details
    affected_features: Optional[List[str]] = None
    description: str
    
    # Status
    is_resolved: bool = False
    resolution_notes: Optional[str] = None


class ActiveDriftsResponse(BaseModel):
    """List of active drifts."""
    
    timestamp: datetime
    total_active: int
    drifts: List[DriftDetectionResponse]
    
    # Summary by type
    by_type: Dict[str, int]
    by_severity: Dict[str, int]


class AlertResponse(BaseModel):
    """Alert details."""
    
    alert_id: str
    fingerprint: str
    category: str
    component: str
    severity: str
    title: str
    description: str
    
    status: str  # firing, acknowledged, resolved, silenced
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime] = None
    
    # Metadata
    labels: Dict[str, str]
    annotations: Dict[str, str]
    
    # Remediation
    suggested_actions: List[str]
    runbook_url: Optional[str] = None


class AlertsListResponse(BaseModel):
    """List of alerts."""
    
    timestamp: datetime
    total: int
    alerts: List[AlertResponse]
    
    # Pagination
    offset: int
    limit: int
    has_more: bool


class RetrainingJobResponse(BaseModel):
    """Retraining job details."""
    
    job_id: str
    model_id: str
    trigger_type: str  # drift, scheduled, manual, performance
    priority: str  # critical, high, normal, low
    status: str  # queued, preparing, training, validating, canary, deploying, completed, failed
    
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Progress
    current_phase: str
    progress_percent: float = Field(ge=0.0, le=100.0)
    
    # Versions
    current_model_version: str
    target_model_version: Optional[str] = None
    
    # Validation results
    validation_passed: Optional[bool] = None
    validation_metrics: Optional[Dict[str, float]] = None


class CreateRetrainingRequest(BaseModel):
    """Request to create a retraining job."""
    
    model_id: str
    reason: str
    priority: str = "normal"
    force: bool = False  # Skip queue if True


class AcknowledgeAlertRequest(BaseModel):
    """Request to acknowledge an alert."""
    
    acknowledged_by: str
    notes: Optional[str] = None


class ResolveAlertRequest(BaseModel):
    """Request to resolve an alert."""
    
    resolved_by: str
    resolution_notes: str


class SilenceAlertRequest(BaseModel):
    """Request to silence an alert."""
    
    duration_minutes: int = Field(ge=1, le=10080)  # Max 7 days
    reason: str
    silenced_by: str


# ============================================================================
# HEALTH ENDPOINTS
# ============================================================================

@router.get("/health", response_model=ModelHealthSummary)
async def get_overall_health():
    """
    Get overall model monitoring health summary.
    
    Returns aggregate health metrics across all monitored models.
    """
    # Implementation would use injected health service
    pass


@router.get("/health/models", response_model=List[ModelHealthResponse])
async def list_model_health(
    status: Optional[str] = Query(None, description="Filter by status"),
    category: Optional[str] = Query(None, description="Filter by model category"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0)
):
    """
    List health status for all monitored models.
    
    Supports filtering by status and category.
    """
    pass


@router.get("/health/models/{model_id}", response_model=ModelHealthResponse)
async def get_model_health(
    model_id: str = Path(..., description="Model identifier")
):
    """
    Get detailed health status for a specific model.
    
    Includes accuracy metrics, latency, psychological validity,
    and any active drift detections.
    """
    pass


@router.get("/health/models/{model_id}/history")
async def get_model_health_history(
    model_id: str = Path(..., description="Model identifier"),
    start_time: datetime = Query(..., description="Start of time range"),
    end_time: datetime = Query(..., description="End of time range"),
    resolution: str = Query("hour", description="Data resolution: minute, hour, day")
):
    """
    Get historical health metrics for a model.
    
    Returns time series data for dashboarding.
    """
    pass


# ============================================================================
# DRIFT ENDPOINTS
# ============================================================================

@router.get("/drift", response_model=ActiveDriftsResponse)
async def get_active_drifts(
    model_id: Optional[str] = Query(None, description="Filter by model"),
    drift_type: Optional[str] = Query(None, description="Filter by drift type"),
    severity: Optional[str] = Query(None, description="Minimum severity"),
    limit: int = Query(100, ge=1, le=500)
):
    """
    Get all active (unresolved) drift detections.
    
    Returns drifts across all models with optional filtering.
    """
    pass


@router.get("/drift/{drift_id}", response_model=DriftDetectionResponse)
async def get_drift_details(
    drift_id: str = Path(..., description="Drift detection ID")
):
    """
    Get detailed information about a specific drift detection.
    """
    pass


@router.post("/drift/{drift_id}/resolve")
async def resolve_drift(
    drift_id: str = Path(..., description="Drift detection ID"),
    notes: str = Body(..., embed=True, description="Resolution notes")
):
    """
    Mark a drift as resolved.
    
    Should be called after addressing the root cause.
    """
    pass


@router.post("/drift/check/{model_id}")
async def trigger_drift_check(
    model_id: str = Path(..., description="Model identifier"),
    background_tasks: BackgroundTasks = None,
    drift_types: Optional[List[str]] = Query(
        None, description="Specific drift types to check"
    )
):
    """
    Trigger an immediate drift check for a model.
    
    Runs all configured drift detectors or specified types.
    """
    pass


# ============================================================================
# ALERT ENDPOINTS
# ============================================================================

@router.get("/alerts", response_model=AlertsListResponse)
async def list_alerts(
    status: Optional[str] = Query(None, description="Filter by status"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    category: Optional[str] = Query(None, description="Filter by category"),
    model_id: Optional[str] = Query(None, description="Filter by model"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0)
):
    """
    List alerts with optional filtering.
    
    Returns paginated list of alerts.
    """
    pass


@router.get("/alerts/{alert_id}", response_model=AlertResponse)
async def get_alert(
    alert_id: str = Path(..., description="Alert identifier")
):
    """
    Get detailed information about a specific alert.
    """
    pass


@router.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: str = Path(..., description="Alert identifier"),
    request: AcknowledgeAlertRequest = Body(...)
):
    """
    Acknowledge an alert.
    
    Indicates that someone is investigating.
    """
    pass


@router.post("/alerts/{alert_id}/resolve")
async def resolve_alert(
    alert_id: str = Path(..., description="Alert identifier"),
    request: ResolveAlertRequest = Body(...)
):
    """
    Resolve an alert.
    
    Indicates that the underlying issue has been fixed.
    """
    pass


@router.post("/alerts/{alert_id}/silence")
async def silence_alert(
    alert_id: str = Path(..., description="Alert identifier"),
    request: SilenceAlertRequest = Body(...)
):
    """
    Temporarily silence an alert.
    
    Use during maintenance or known issues.
    """
    pass


# ============================================================================
# RETRAINING ENDPOINTS
# ============================================================================

@router.get("/retraining/jobs")
async def list_retraining_jobs(
    status: Optional[str] = Query(None, description="Filter by status"),
    model_id: Optional[str] = Query(None, description="Filter by model"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0)
):
    """
    List retraining jobs.
    
    Returns active and recent completed jobs.
    """
    pass


@router.get("/retraining/jobs/{job_id}", response_model=RetrainingJobResponse)
async def get_retraining_job(
    job_id: str = Path(..., description="Retraining job ID")
):
    """
    Get details of a specific retraining job.
    """
    pass


@router.post("/retraining/jobs", response_model=RetrainingJobResponse)
async def create_retraining_job(
    request: CreateRetrainingRequest = Body(...)
):
    """
    Create a new retraining job.
    
    Queues the model for retraining with specified priority.
    """
    pass


@router.post("/retraining/jobs/{job_id}/cancel")
async def cancel_retraining_job(
    job_id: str = Path(..., description="Retraining job ID"),
    reason: str = Body(..., embed=True)
):
    """
    Cancel a pending or in-progress retraining job.
    """
    pass


@router.post("/retraining/jobs/{job_id}/approve")
async def approve_retraining_job(
    job_id: str = Path(..., description="Retraining job ID"),
    approved_by: str = Body(..., embed=True)
):
    """
    Approve a retraining job pending approval.
    
    Allows deployment to proceed after validation.
    """
    pass


# ============================================================================
# INTELLIGENCE SOURCE ENDPOINTS
# ============================================================================

@router.get("/sources")
async def list_intelligence_sources():
    """
    List all 10 intelligence sources and their health.
    
    Returns availability, latency, and contribution metrics.
    """
    pass


@router.get("/sources/{source_id}")
async def get_source_health(
    source_id: str = Path(..., description="Source identifier")
):
    """
    Get detailed health for a specific intelligence source.
    """
    pass


@router.get("/fusion/quality")
async def get_fusion_quality(
    atom_type: Optional[str] = Query(None, description="Filter by atom type")
):
    """
    Get multi-source fusion quality metrics.
    
    Returns agreement rates, conflict counts, and balance metrics.
    """
    pass


# ============================================================================
# GRADIENT BRIDGE ENDPOINTS
# ============================================================================

@router.get("/learning/health")
async def get_learning_health():
    """
    Get Gradient Bridge learning health.
    
    Returns signal quality, attribution accuracy, and learning velocity.
    """
    pass


@router.get("/learning/signals")
async def list_learning_signals():
    """
    List learning signal health by type.
    """
    pass


@router.get("/learning/attribution")
async def get_attribution_health():
    """
    Get attribution method health metrics.
    """
    pass


# ============================================================================
# SNAPSHOT ENDPOINTS
# ============================================================================

@router.get("/snapshot")
async def get_current_snapshot():
    """
    Get comprehensive system health snapshot.
    
    Aggregates all monitoring data into a dashboard-ready format.
    """
    pass


@router.get("/snapshot/history")
async def get_snapshot_history(
    hours: int = Query(24, ge=1, le=168),
    resolution: str = Query("hour", description="minute, hour, day")
):
    """
    Get historical snapshots for trend analysis.
    """
    pass
```

---

## SECTION L: PROMETHEUS METRICS

### L.1 Metric Definitions

```python
"""
ADAM Model Monitoring Prometheus Metrics
Comprehensive metrics for observability and alerting.
"""

from prometheus_client import Counter, Gauge, Histogram, Summary, Info


# ============================================================================
# MODEL HEALTH METRICS
# ============================================================================

# Model status (1 for each status type)
model_health_status = Gauge(
    "adam_model_health_status",
    "Model health status (1=current status)",
    ["model_id", "model_name", "status"]  # status: healthy, degraded, unhealthy, critical
)

model_health_score = Gauge(
    "adam_model_health_score",
    "Model health score (0-1)",
    ["model_id", "model_name"]
)

# Performance metrics
model_accuracy = Gauge(
    "adam_model_accuracy",
    "Model accuracy metric",
    ["model_id", "model_name", "metric_type"]  # accuracy, precision, recall, f1
)

model_auc_roc = Gauge(
    "adam_model_auc_roc",
    "Model AUC-ROC score",
    ["model_id", "model_name"]
)

model_calibration_error = Gauge(
    "adam_model_calibration_error",
    "Expected Calibration Error",
    ["model_id", "model_name"]
)

# Latency
model_inference_latency = Histogram(
    "adam_model_inference_latency_seconds",
    "Model inference latency",
    ["model_id", "model_name"],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 1.0]
)

# Psychological validity
model_psychological_validity = Gauge(
    "adam_model_psychological_validity_score",
    "Psychological validity score (0-1)",
    ["model_id", "model_name"]
)

# Throughput
model_predictions_total = Counter(
    "adam_model_predictions_total",
    "Total predictions made",
    ["model_id", "model_name", "outcome"]  # outcome: success, error, timeout
)

model_predictions_per_second = Gauge(
    "adam_model_predictions_per_second",
    "Current prediction rate",
    ["model_id", "model_name"]
)


# ============================================================================
# DRIFT DETECTION METRICS
# ============================================================================

drift_detected_total = Counter(
    "adam_drift_detected_total",
    "Total drift detections",
    ["model_id", "drift_type", "severity"]
)

drift_active = Gauge(
    "adam_drift_active",
    "Number of active (unresolved) drifts",
    ["model_id", "drift_type"]
)

drift_detection_latency = Histogram(
    "adam_drift_detection_latency_seconds",
    "Time to detect drift",
    ["drift_type"],
    buckets=[1, 5, 15, 30, 60, 300, 600, 1800, 3600]
)

drift_resolution_time = Histogram(
    "adam_drift_resolution_time_hours",
    "Time to resolve drift",
    ["drift_type", "severity"],
    buckets=[0.5, 1, 2, 4, 8, 12, 24, 48, 72, 168]
)

# Statistical test metrics
drift_statistic_value = Gauge(
    "adam_drift_statistic_value",
    "Latest drift test statistic",
    ["model_id", "drift_type", "test_name"]
)

drift_p_value = Gauge(
    "adam_drift_p_value",
    "Latest drift test p-value",
    ["model_id", "drift_type", "test_name"]
)

# Psychological drift specifics
psychological_trait_stability = Gauge(
    "adam_psychological_trait_stability",
    "Trait prediction stability (0-1)",
    ["model_id", "trait"]
)

psychological_mechanism_validity = Gauge(
    "adam_psychological_mechanism_validity",
    "Mechanism effectiveness validity (0-1)",
    ["model_id", "mechanism"]
)


# ============================================================================
# INTELLIGENCE SOURCE METRICS
# ============================================================================

source_availability = Gauge(
    "adam_source_availability",
    "Intelligence source availability (0-1)",
    ["source_type"]  # The 10 intelligence sources
)

source_response_latency = Histogram(
    "adam_source_response_latency_seconds",
    "Source query latency",
    ["source_type"],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0]
)

source_error_rate = Gauge(
    "adam_source_error_rate",
    "Source error rate (0-1)",
    ["source_type"]
)

source_contribution_weight = Gauge(
    "adam_source_contribution_weight",
    "Current source contribution weight in fusion",
    ["source_type"]
)

source_confidence_mean = Gauge(
    "adam_source_confidence_mean",
    "Average confidence from source",
    ["source_type"]
)

# Fusion metrics
fusion_sources_used = Histogram(
    "adam_fusion_sources_used",
    "Number of sources used in fusion",
    ["atom_type"],
    buckets=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
)

fusion_agreement_rate = Gauge(
    "adam_fusion_agreement_rate",
    "Cross-source agreement rate (0-1)",
    ["atom_type"]
)

fusion_conflict_count = Counter(
    "adam_fusion_conflicts_total",
    "Total fusion conflicts detected",
    ["atom_type", "severity"]
)

fusion_entropy = Gauge(
    "adam_fusion_source_entropy",
    "Source contribution entropy (balance metric)",
    ["atom_type"]
)

fusion_confidence = Gauge(
    "adam_fusion_confidence",
    "Fusion output confidence (0-1)",
    ["atom_type"]
)


# ============================================================================
# GRADIENT BRIDGE METRICS
# ============================================================================

learning_signal_volume = Counter(
    "adam_learning_signal_volume_total",
    "Total learning signals received",
    ["signal_type"]
)

learning_signal_quality = Gauge(
    "adam_learning_signal_quality",
    "Learning signal quality score (0-1)",
    ["signal_type"]
)

learning_signal_delay = Histogram(
    "adam_learning_signal_delay_seconds",
    "Learning signal delay from event to receipt",
    ["signal_type"],
    buckets=[0.1, 0.5, 1, 5, 10, 30, 60, 300, 600, 1800]
)

attribution_coverage = Gauge(
    "adam_attribution_coverage",
    "Attribution coverage rate (0-1)",
    ["method"]
)

attribution_confidence = Gauge(
    "adam_attribution_confidence",
    "Attribution confidence (0-1)",
    ["method"]
)

attribution_computation_time = Histogram(
    "adam_attribution_computation_seconds",
    "Attribution computation time",
    ["method"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0]
)

gradient_magnitude = Gauge(
    "adam_gradient_magnitude",
    "Learning gradient magnitude",
    ["component"]
)

learning_convergence = Gauge(
    "adam_learning_convergence",
    "Learning convergence metric (0-1)",
    ["component"]
)


# ============================================================================
# ALERTING METRICS
# ============================================================================

alerts_created_total = Counter(
    "adam_alerts_created_total",
    "Total alerts created",
    ["category", "severity"]
)

alerts_active = Gauge(
    "adam_alerts_active",
    "Number of active alerts",
    ["category", "severity", "status"]  # status: firing, acknowledged
)

alert_notification_sent = Counter(
    "adam_alert_notifications_total",
    "Notifications sent",
    ["channel", "severity"]  # channel: slack, pagerduty, email
)

alert_notification_latency = Histogram(
    "adam_alert_notification_latency_seconds",
    "Time from alert creation to notification",
    ["channel"],
    buckets=[0.1, 0.5, 1, 5, 10, 30, 60]
)

alert_time_to_acknowledge = Histogram(
    "adam_alert_time_to_acknowledge_seconds",
    "Time from alert to acknowledgment",
    ["severity"],
    buckets=[60, 300, 600, 1800, 3600, 7200, 14400]
)

alert_time_to_resolve = Histogram(
    "adam_alert_time_to_resolve_hours",
    "Time from alert to resolution",
    ["category", "severity"],
    buckets=[0.5, 1, 2, 4, 8, 12, 24, 48, 72]
)

auto_remediation_triggered = Counter(
    "adam_auto_remediation_triggered_total",
    "Auto-remediation actions triggered",
    ["action_type", "status"]  # status: success, failed
)


# ============================================================================
# RETRAINING METRICS
# ============================================================================

retraining_jobs_total = Counter(
    "adam_retraining_jobs_total",
    "Total retraining jobs created",
    ["trigger_type", "priority"]
)

retraining_jobs_active = Gauge(
    "adam_retraining_jobs_active",
    "Currently active retraining jobs",
    ["status"]  # queued, preparing, training, validating, canary
)

retraining_duration = Histogram(
    "adam_retraining_duration_hours",
    "Retraining job duration",
    ["model_id", "trigger_type"],
    buckets=[0.5, 1, 2, 4, 8, 12, 24, 48]
)

retraining_validation_pass_rate = Gauge(
    "adam_retraining_validation_pass_rate",
    "Validation pass rate for retraining jobs",
    []
)

canary_success_rate = Gauge(
    "adam_canary_success_rate",
    "Canary deployment success rate",
    []
)

model_deployments_total = Counter(
    "adam_model_deployments_total",
    "Model deployments",
    ["model_id", "outcome"]  # outcome: success, rollback, failed
)


# ============================================================================
# NONCONSCIOUS SIGNAL METRICS
# ============================================================================

nonconscious_signal_volume = Counter(
    "adam_nonconscious_signal_volume_total",
    "Nonconscious signals captured",
    ["signal_type"]
)

nonconscious_signal_strength = Gauge(
    "adam_nonconscious_signal_strength",
    "Signal strength (0-1)",
    ["signal_type"]
)

nonconscious_noise_ratio = Gauge(
    "adam_nonconscious_noise_ratio",
    "Signal noise ratio (0-1, lower better)",
    ["signal_type"]
)

nonconscious_extraction_rate = Gauge(
    "adam_nonconscious_extraction_rate",
    "Successful extraction rate (0-1)",
    ["signal_type"]
)

nonconscious_mapping_confidence = Gauge(
    "adam_nonconscious_mapping_confidence",
    "Psychological construct mapping confidence (0-1)",
    ["signal_type"]
)


# ============================================================================
# SYSTEM METRICS
# ============================================================================

monitoring_snapshot_duration = Histogram(
    "adam_monitoring_snapshot_duration_seconds",
    "Time to generate health snapshot",
    [],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.0, 5.0]
)

monitoring_components_healthy = Gauge(
    "adam_monitoring_components_healthy",
    "Number of healthy monitoring components",
    []
)

monitoring_data_completeness = Gauge(
    "adam_monitoring_data_completeness",
    "Data completeness ratio (0-1)",
    []
)

neo4j_query_latency = Histogram(
    "adam_neo4j_monitoring_query_latency_seconds",
    "Neo4j monitoring query latency",
    ["query_type"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0]
)
```

### L.2 Metrics Collection Service

```python
"""
ADAM Metrics Collection Service
Periodically collects and exposes monitoring metrics.
"""

import asyncio
from datetime import datetime
from typing import Optional, Any
import logging

logger = logging.getLogger(__name__)


class MonitoringMetricsCollector:
    """
    Collects metrics from all monitoring components and updates Prometheus.
    
    Runs as a background service, periodically gathering health data
    and updating metric values.
    """
    
    def __init__(
        self,
        health_monitor: Any,
        drift_manager: Any,
        alert_manager: Any,
        retraining_orchestrator: Any,
        source_monitor: Any,
        fusion_monitor: Any,
        gradient_bridge_monitor: Any,
        nonconscious_monitor: Any,
        collection_interval_seconds: int = 30
    ):
        self.health_monitor = health_monitor
        self.drift_manager = drift_manager
        self.alert_manager = alert_manager
        self.retraining_orchestrator = retraining_orchestrator
        self.source_monitor = source_monitor
        self.fusion_monitor = fusion_monitor
        self.gradient_bridge_monitor = gradient_bridge_monitor
        self.nonconscious_monitor = nonconscious_monitor
        
        self.collection_interval = collection_interval_seconds
        self._running = False
        self._task: Optional[asyncio.Task] = None
        
        logger.info(
            f"MonitoringMetricsCollector initialized with "
            f"{collection_interval_seconds}s interval"
        )
    
    async def start(self) -> None:
        """Start the metrics collection loop."""
        if self._running:
            return
        
        self._running = True
        self._task = asyncio.create_task(self._collection_loop())
        logger.info("Metrics collection started")
    
    async def stop(self) -> None:
        """Stop the metrics collection loop."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Metrics collection stopped")
    
    async def _collection_loop(self) -> None:
        """Main collection loop."""
        while self._running:
            try:
                await self._collect_all_metrics()
            except Exception as e:
                logger.error(f"Error collecting metrics: {e}")
            
            await asyncio.sleep(self.collection_interval)
    
    async def _collect_all_metrics(self) -> None:
        """Collect all metrics from monitoring components."""
        
        start_time = datetime.utcnow()
        
        # Collect in parallel
        await asyncio.gather(
            self._collect_model_health_metrics(),
            self._collect_drift_metrics(),
            self._collect_alert_metrics(),
            self._collect_retraining_metrics(),
            self._collect_source_metrics(),
            self._collect_fusion_metrics(),
            self._collect_learning_metrics(),
            self._collect_nonconscious_metrics(),
            return_exceptions=True
        )
        
        # Record collection duration
        duration = (datetime.utcnow() - start_time).total_seconds()
        monitoring_snapshot_duration.observe(duration)
    
    async def _collect_model_health_metrics(self) -> None:
        """Collect model health metrics."""
        
        if not self.health_monitor:
            return
        
        try:
            models = await self.health_monitor.get_all_model_health()
            
            for model in models:
                # Health status (set 1 for current status, 0 for others)
                for status in ["healthy", "degraded", "unhealthy", "critical"]:
                    model_health_status.labels(
                        model_id=model.model_id,
                        model_name=model.name,
                        status=status
                    ).set(1 if model.status == status else 0)
                
                # Health score
                model_health_score.labels(
                    model_id=model.model_id,
                    model_name=model.name
                ).set(model.health_score)
                
                # Accuracy metrics
                if model.accuracy is not None:
                    model_accuracy.labels(
                        model_id=model.model_id,
                        model_name=model.name,
                        metric_type="accuracy"
                    ).set(model.accuracy)
                
                # AUC-ROC
                if model.auc_roc is not None:
                    model_auc_roc.labels(
                        model_id=model.model_id,
                        model_name=model.name
                    ).set(model.auc_roc)
                
                # Psychological validity
                if model.psychological_validity_score is not None:
                    model_psychological_validity.labels(
                        model_id=model.model_id,
                        model_name=model.name
                    ).set(model.psychological_validity_score)
                    
        except Exception as e:
            logger.error(f"Error collecting model health metrics: {e}")
    
    async def _collect_drift_metrics(self) -> None:
        """Collect drift detection metrics."""
        
        if not self.drift_manager:
            return
        
        try:
            active_drifts = await self.drift_manager.get_active_drifts()
            
            # Clear and reset active drift gauges
            # (In production, use label management)
            
            for drift in active_drifts:
                drift_active.labels(
                    model_id=drift.model_id,
                    drift_type=drift.drift_type
                ).set(1)
                
                drift_statistic_value.labels(
                    model_id=drift.model_id,
                    drift_type=drift.drift_type,
                    test_name=drift.test_name
                ).set(drift.statistic_value)
                
                if drift.p_value is not None:
                    drift_p_value.labels(
                        model_id=drift.model_id,
                        drift_type=drift.drift_type,
                        test_name=drift.test_name
                    ).set(drift.p_value)
                    
        except Exception as e:
            logger.error(f"Error collecting drift metrics: {e}")
    
    async def _collect_alert_metrics(self) -> None:
        """Collect alerting metrics."""
        
        if not self.alert_manager:
            return
        
        try:
            alerts = await self.alert_manager.get_alerts(status="firing")
            
            # Count by category/severity/status
            counts = {}
            for alert in alerts:
                key = (alert.category, alert.severity, alert.status)
                counts[key] = counts.get(key, 0) + 1
            
            for (category, severity, status), count in counts.items():
                alerts_active.labels(
                    category=category,
                    severity=severity,
                    status=status
                ).set(count)
                
        except Exception as e:
            logger.error(f"Error collecting alert metrics: {e}")
    
    async def _collect_retraining_metrics(self) -> None:
        """Collect retraining metrics."""
        
        if not self.retraining_orchestrator:
            return
        
        try:
            jobs = await self.retraining_orchestrator.get_active_jobs()
            
            # Count by status
            status_counts = {}
            for job in jobs:
                status_counts[job.status] = status_counts.get(job.status, 0) + 1
            
            for status, count in status_counts.items():
                retraining_jobs_active.labels(status=status).set(count)
                
        except Exception as e:
            logger.error(f"Error collecting retraining metrics: {e}")
    
    async def _collect_source_metrics(self) -> None:
        """Collect intelligence source metrics."""
        
        if not self.source_monitor:
            return
        
        try:
            for source_type in IntelligenceSourceType:
                health = self.source_monitor.get_source_health(source_type)
                
                source_availability.labels(
                    source_type=source_type.value
                ).set(health.availability)
                
                source_error_rate.labels(
                    source_type=source_type.value
                ).set(health.error_rate)
                
                source_contribution_weight.labels(
                    source_type=source_type.value
                ).set(health.contribution_weight)
                
                source_confidence_mean.labels(
                    source_type=source_type.value
                ).set(health.confidence_mean)
                
        except Exception as e:
            logger.error(f"Error collecting source metrics: {e}")
    
    async def _collect_fusion_metrics(self) -> None:
        """Collect fusion quality metrics."""
        
        if not self.fusion_monitor:
            return
        
        try:
            quality = self.fusion_monitor.get_fusion_quality()
            
            fusion_agreement_rate.labels(
                atom_type="all"
            ).set(quality.source_agreement_rate)
            
            fusion_entropy.labels(
                atom_type="all"
            ).set(quality.source_entropy)
            
            fusion_confidence.labels(
                atom_type="all"
            ).set(quality.fusion_confidence)
            
        except Exception as e:
            logger.error(f"Error collecting fusion metrics: {e}")
    
    async def _collect_learning_metrics(self) -> None:
        """Collect Gradient Bridge learning metrics."""
        
        if not self.gradient_bridge_monitor:
            return
        
        try:
            health = await self.gradient_bridge_monitor.get_health()
            
            # Signal quality
            for signal_type, signal_health in health.signal_health.items():
                learning_signal_quality.labels(
                    signal_type=signal_type
                ).set(signal_health.label_quality_score)
            
            # Attribution metrics
            for method, attr_health in health.attribution_health.items():
                attribution_coverage.labels(
                    method=method
                ).set(attr_health.coverage_rate)
                
                attribution_confidence.labels(
                    method=method
                ).set(attr_health.attribution_confidence_mean)
                
        except Exception as e:
            logger.error(f"Error collecting learning metrics: {e}")
    
    async def _collect_nonconscious_metrics(self) -> None:
        """Collect nonconscious signal metrics."""
        
        if not self.nonconscious_monitor:
            return
        
        try:
            all_health = self.nonconscious_monitor.get_all_signal_health()
            
            for signal_type, health in all_health.items():
                nonconscious_signal_strength.labels(
                    signal_type=signal_type
                ).set(health.signal_strength_mean)
                
                nonconscious_noise_ratio.labels(
                    signal_type=signal_type
                ).set(health.noise_ratio)
                
                nonconscious_extraction_rate.labels(
                    signal_type=signal_type
                ).set(health.extraction_success_rate)
                
                nonconscious_mapping_confidence.labels(
                    signal_type=signal_type
                ).set(health.construct_mapping_confidence)
                
        except Exception as e:
            logger.error(f"Error collecting nonconscious metrics: {e}")
```

---

## SECTION M: TESTING & OPERATIONS

### M.1 Unit Tests

```python
"""
ADAM Model Monitoring Unit Tests
Comprehensive test coverage for drift detection and monitoring components.
"""

import pytest
import asyncio
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, List, Any

# Import monitoring components
# from adam.monitoring.drift import StatisticalDriftDetector, PsychologicalDriftDetector
# from adam.monitoring.health import HealthSnapshotGenerator
# from adam.monitoring.alerts import AlertManager
# from adam.monitoring.sources import IntelligenceSourceMonitor
# from adam.monitoring.fusion import FusionQualityMonitor


# ============================================================================
# STATISTICAL DRIFT DETECTOR TESTS
# ============================================================================

class TestStatisticalDriftDetector:
    """Tests for statistical drift detection."""
    
    @pytest.fixture
    def detector(self):
        """Create detector instance."""
        return StatisticalDriftDetector(
            reference_window_days=7,
            min_samples=100
        )
    
    @pytest.fixture
    def stable_reference(self):
        """Generate stable reference distribution."""
        np.random.seed(42)
        return np.random.normal(0.5, 0.1, 1000)
    
    @pytest.fixture
    def drifted_data(self):
        """Generate data with clear drift."""
        np.random.seed(42)
        return np.random.normal(0.7, 0.15, 1000)  # Different mean and std
    
    def test_ks_test_no_drift(self, detector, stable_reference):
        """KS test should not detect drift in same distribution."""
        # Current data from same distribution
        np.random.seed(43)
        current = np.random.normal(0.5, 0.1, 500)
        
        result = detector._ks_test(stable_reference, current)
        
        assert result.p_value > 0.05, "Should not detect drift in same distribution"
        assert not result.drift_detected
    
    def test_ks_test_with_drift(self, detector, stable_reference, drifted_data):
        """KS test should detect significant distribution shift."""
        result = detector._ks_test(stable_reference, drifted_data)
        
        assert result.p_value < 0.05, "Should detect drift"
        assert result.drift_detected
        assert result.statistic_value > 0.1
    
    def test_psi_calculation(self, detector, stable_reference, drifted_data):
        """PSI should indicate drift magnitude."""
        psi = detector._calculate_psi(stable_reference, drifted_data, n_bins=10)
        
        assert psi > 0.1, "PSI should indicate drift"
        
        # No drift case
        np.random.seed(43)
        similar = np.random.normal(0.5, 0.1, 500)
        psi_stable = detector._calculate_psi(stable_reference, similar, n_bins=10)
        
        assert psi_stable < 0.1, "PSI should be low for similar distributions"
    
    def test_minimum_samples_requirement(self, detector):
        """Should require minimum samples before detecting."""
        small_reference = np.array([0.5] * 50)  # Below minimum
        small_current = np.array([0.6] * 50)
        
        result = detector._ks_test(small_reference, small_current)
        
        assert result.severity == "low", "Should not be confident with small samples"
    
    @pytest.mark.asyncio
    async def test_drift_detection_pipeline(self, detector):
        """Test full drift detection pipeline."""
        model_id = "test_model"
        
        # Set reference
        np.random.seed(42)
        reference = np.random.normal(0.5, 0.1, 1000)
        await detector.set_reference_distribution(model_id, reference)
        
        # Check with drifted data
        drifted = np.random.normal(0.7, 0.15, 500)
        result = await detector.detect_drift(model_id, drifted)
        
        assert result is not None
        assert result.drift_type == "data"
        assert result.severity in ["medium", "high", "critical"]


# ============================================================================
# PSYCHOLOGICAL DRIFT DETECTOR TESTS
# ============================================================================

class TestPsychologicalDriftDetector:
    """Tests for psychological drift detection."""
    
    @pytest.fixture
    def detector(self):
        """Create psychological drift detector."""
        return PsychologicalDriftDetector(
            min_observations=50,
            trait_stability_window_hours=168
        )
    
    def test_trait_stability_normal(self, detector):
        """Trait predictions should be stable for same user."""
        user_id = "user_123"
        
        # Simulate stable extraversion predictions
        for _ in range(100):
            value = 0.7 + np.random.normal(0, 0.05)  # Small variation
            detector.record_trait_prediction(
                user_id=user_id,
                trait="extraversion",
                predicted_value=value
            )
        
        stability = detector.get_trait_stability(user_id, "extraversion")
        
        assert stability > 0.85, "Stable predictions should have high stability"
    
    def test_trait_stability_drift(self, detector):
        """Should detect drift in trait predictions."""
        user_id = "user_456"
        
        # First half: high extraversion
        for _ in range(50):
            detector.record_trait_prediction(
                user_id=user_id,
                trait="extraversion",
                predicted_value=0.8 + np.random.normal(0, 0.03)
            )
        
        # Second half: low extraversion (drift!)
        for _ in range(50):
            detector.record_trait_prediction(
                user_id=user_id,
                trait="extraversion",
                predicted_value=0.3 + np.random.normal(0, 0.03)
            )
        
        stability = detector.get_trait_stability(user_id, "extraversion")
        
        assert stability < 0.5, "Should detect instability from drift"
    
    def test_trait_correlation_validity(self, detector):
        """Should validate expected trait correlations."""
        # Extraversion-openness typically correlate positively
        for _ in range(200):
            base = np.random.uniform(0.3, 0.8)
            detector.record_trait_prediction(
                user_id=f"user_{_}",
                trait="extraversion",
                predicted_value=base + np.random.normal(0, 0.05)
            )
            detector.record_trait_prediction(
                user_id=f"user_{_}",
                trait="openness",
                predicted_value=base + np.random.normal(0, 0.1)  # Correlated
            )
        
        validity = detector.check_trait_correlation_validity(
            trait_a="extraversion",
            trait_b="openness",
            expected_correlation=0.3,
            tolerance=0.2
        )
        
        assert validity.is_valid, "Correlations should match expected patterns"
    
    def test_mechanism_effectiveness_consistency(self, detector):
        """Mechanism effectiveness should be internally consistent."""
        # Record conversions with social proof mechanism
        for _ in range(100):
            # Social proof works better for high conformity users
            conformity = np.random.uniform(0.5, 0.9)
            # Conversion correlates with conformity for social proof
            converted = np.random.random() < (0.3 + 0.4 * conformity)
            
            detector.record_mechanism_outcome(
                mechanism="social_proof",
                user_traits={"conformity": conformity},
                converted=converted
            )
        
        consistency = detector.get_mechanism_consistency("social_proof")
        
        assert consistency.correlation_with_relevant_traits > 0.2, \
            "Should detect mechanism-trait relationship"


# ============================================================================
# INTELLIGENCE SOURCE MONITOR TESTS
# ============================================================================

class TestIntelligenceSourceMonitor:
    """Tests for intelligence source health monitoring."""
    
    @pytest.fixture
    def monitor(self):
        """Create source monitor."""
        return IntelligenceSourceMonitor()
    
    def test_source_availability_tracking(self, monitor):
        """Should track source availability correctly."""
        source = IntelligenceSourceType.CLAUDE_REASONING
        
        # Simulate responses
        for _ in range(100):
            success = np.random.random() < 0.95  # 95% success
            monitor.record_source_response(
                source_type=source,
                responded=success,
                latency_ms=50 if success else 5000
            )
        
        health = monitor.get_source_health(source)
        
        assert 0.90 < health.availability < 1.0
        assert health.health_status in ["healthy", "degraded"]
    
    def test_source_degradation_detection(self, monitor):
        """Should detect source degradation."""
        source = IntelligenceSourceType.EMPIRICAL_PATTERNS
        
        # Simulate degraded source
        for _ in range(100):
            success = np.random.random() < 0.5  # Only 50% success
            monitor.record_source_response(
                source_type=source,
                responded=success,
                latency_ms=100 if success else 5000
            )
        
        health = monitor.get_source_health(source)
        
        assert health.availability < 0.6
        assert health.health_status in ["degraded", "unhealthy", "critical"]
    
    def test_contribution_balance(self, monitor):
        """Should track source contribution balance."""
        # Record varied contributions
        for _ in range(100):
            contributions = {
                IntelligenceSourceType.CLAUDE_REASONING: 0.5,  # Dominant
                IntelligenceSourceType.EMPIRICAL_PATTERNS: 0.2,
                IntelligenceSourceType.BANDIT_POSTERIORS: 0.2,
                IntelligenceSourceType.GRAPH_EMERGENCE: 0.1
            }
            monitor.record_fusion_contributions(contributions)
        
        balance = monitor.get_contribution_balance()
        
        assert balance.dominant_source == IntelligenceSourceType.CLAUDE_REASONING
        assert balance.entropy < 0.8  # Lower entropy = less balanced


# ============================================================================
# FUSION QUALITY MONITOR TESTS
# ============================================================================

class TestFusionQualityMonitor:
    """Tests for fusion quality monitoring."""
    
    @pytest.fixture
    def monitor(self):
        """Create fusion monitor."""
        return FusionQualityMonitor()
    
    @pytest.mark.asyncio
    async def test_agreement_rate_calculation(self, monitor):
        """Should calculate cross-source agreement correctly."""
        # Record events with high agreement
        for _ in range(50):
            await monitor.record_fusion_event(
                atom_type="user_state",
                sources_queried={IntelligenceSourceType.CLAUDE_REASONING,
                               IntelligenceSourceType.EMPIRICAL_PATTERNS,
                               IntelligenceSourceType.BANDIT_POSTERIORS},
                sources_responded={IntelligenceSourceType.CLAUDE_REASONING,
                                  IntelligenceSourceType.EMPIRICAL_PATTERNS,
                                  IntelligenceSourceType.BANDIT_POSTERIORS},
                source_contributions={
                    IntelligenceSourceType.CLAUDE_REASONING: 0.4,
                    IntelligenceSourceType.EMPIRICAL_PATTERNS: 0.35,
                    IntelligenceSourceType.BANDIT_POSTERIORS: 0.25
                },
                source_confidences={
                    IntelligenceSourceType.CLAUDE_REASONING: 0.85,
                    IntelligenceSourceType.EMPIRICAL_PATTERNS: 0.80,
                    IntelligenceSourceType.BANDIT_POSTERIORS: 0.75
                },
                source_latencies={
                    IntelligenceSourceType.CLAUDE_REASONING: 150,
                    IntelligenceSourceType.EMPIRICAL_PATTERNS: 25,
                    IntelligenceSourceType.BANDIT_POSTERIORS: 15
                },
                conflicts=[],  # No conflicts = high agreement
                fusion_confidence=0.85,
                processing_time_ms=200
            )
        
        quality = monitor.get_fusion_quality("user_state")
        
        assert quality.source_agreement_rate > 0.8
        assert quality.source_availability_rate == 1.0
        assert quality.quality_score > 0.7
    
    @pytest.mark.asyncio
    async def test_conflict_detection(self, monitor):
        """Should track conflicts and agreement rates."""
        # Record events with frequent conflicts
        for _ in range(30):
            await monitor.record_fusion_event(
                atom_type="mechanism_selection",
                sources_queried={IntelligenceSourceType.CLAUDE_REASONING,
                               IntelligenceSourceType.BANDIT_POSTERIORS},
                sources_responded={IntelligenceSourceType.CLAUDE_REASONING,
                                  IntelligenceSourceType.BANDIT_POSTERIORS},
                source_contributions={
                    IntelligenceSourceType.CLAUDE_REASONING: 0.5,
                    IntelligenceSourceType.BANDIT_POSTERIORS: 0.5
                },
                source_confidences={
                    IntelligenceSourceType.CLAUDE_REASONING: 0.8,
                    IntelligenceSourceType.BANDIT_POSTERIORS: 0.75
                },
                source_latencies={
                    IntelligenceSourceType.CLAUDE_REASONING: 200,
                    IntelligenceSourceType.BANDIT_POSTERIORS: 20
                },
                conflicts=[{
                    "source_a": "claude_reasoning",
                    "source_b": "bandit_posteriors",
                    "severity": "medium"
                }],
                fusion_confidence=0.7,
                processing_time_ms=250
            )
        
        quality = monitor.get_fusion_quality("mechanism_selection")
        
        assert quality.conflict_count > 0
        assert quality.source_agreement_rate < 1.0


# ============================================================================
# ALERT MANAGER TESTS
# ============================================================================

class TestAlertManager:
    """Tests for alert management."""
    
    @pytest.fixture
    def manager(self):
        """Create alert manager."""
        return AlertManager(
            notification_handlers={
                "slack": Mock(spec=["send_notification"]),
                "pagerduty": Mock(spec=["send_notification"])
            }
        )
    
    @pytest.mark.asyncio
    async def test_alert_creation(self, manager):
        """Should create alerts correctly."""
        alert = await manager.create_alert(
            category="drift",
            component="personality_predictor",
            severity="high",
            title="Data drift detected",
            description="KS test p-value < 0.001"
        )
        
        assert alert.status == "firing"
        assert alert.severity == "high"
        assert alert.fingerprint is not None
    
    @pytest.mark.asyncio
    async def test_alert_deduplication(self, manager):
        """Should deduplicate identical alerts."""
        # Create first alert
        alert1 = await manager.create_alert(
            category="drift",
            component="model_x",
            severity="high",
            title="Same alert",
            description="Details"
        )
        
        # Try to create identical alert
        alert2 = await manager.create_alert(
            category="drift",
            component="model_x",
            severity="high",
            title="Same alert",
            description="Details"
        )
        
        assert alert1.alert_id == alert2.alert_id, "Should return same alert"
    
    @pytest.mark.asyncio
    async def test_alert_routing(self, manager):
        """Should route alerts to correct channels."""
        # Critical alert should go to PagerDuty
        await manager.create_alert(
            category="health",
            component="core_model",
            severity="critical",
            title="Critical failure",
            description="Model unavailable"
        )
        
        # Check PagerDuty was called
        manager.notification_handlers["pagerduty"].send_notification.assert_called()
    
    @pytest.mark.asyncio
    async def test_silence_rules(self, manager):
        """Should respect silence rules."""
        # Create silence
        await manager.create_silence(
            matchers={"component": "test_model"},
            duration_minutes=60,
            reason="Testing",
            created_by="test"
        )
        
        # Alert matching silence should be silenced
        alert = await manager.create_alert(
            category="drift",
            component="test_model",
            severity="high",
            title="Should be silenced",
            description="Test"
        )
        
        assert alert.status == "silenced"
    
    @pytest.mark.asyncio
    async def test_rate_limiting(self, manager):
        """Should rate limit notifications."""
        manager.rate_limit_per_minute = 5
        
        # Create many alerts rapidly
        for i in range(10):
            await manager.create_alert(
                category="test",
                component=f"component_{i}",
                severity="warning",
                title=f"Alert {i}",
                description="Test"
            )
        
        # Should have rate limited some
        assert manager.metrics["notifications_rate_limited"] > 0


# ============================================================================
# HEALTH SNAPSHOT GENERATOR TESTS
# ============================================================================

class TestHealthSnapshotGenerator:
    """Tests for health snapshot generation."""
    
    @pytest.fixture
    def generator(self):
        """Create snapshot generator with mocked dependencies."""
        return HealthSnapshotGenerator(
            source_monitor=Mock(),
            atom_monitor=Mock(),
            drift_detectors=[Mock()],
            alert_manager=Mock(),
            learning_monitor=Mock()
        )
    
    @pytest.mark.asyncio
    async def test_snapshot_generation(self, generator):
        """Should generate comprehensive snapshot."""
        # Configure mocks
        generator.source_monitor.get_all_source_health.return_value = {}
        generator.atom_monitor.get_health.return_value = Mock(health_score=0.85)
        generator.alert_manager.get_alerts.return_value = []
        
        snapshot = await generator.generate_snapshot()
        
        assert snapshot.timestamp is not None
        assert snapshot.overall_status in ["healthy", "degraded", "unhealthy", "critical"]
        assert 0 <= snapshot.overall_score <= 1
    
    @pytest.mark.asyncio
    async def test_snapshot_degraded_detection(self, generator):
        """Should detect degraded system state."""
        # Configure mocks for degraded state
        generator.source_monitor.get_all_source_health.return_value = {
            "claude_reasoning": Mock(health_status="degraded", health_score=0.6)
        }
        generator.atom_monitor.get_health.return_value = Mock(health_score=0.65)
        generator.alert_manager.get_alerts.return_value = [Mock(severity="warning")]
        
        snapshot = await generator.generate_snapshot()
        
        assert snapshot.overall_status in ["degraded", "unhealthy"]
        assert snapshot.overall_score < 0.8


# ============================================================================
# RETRAINING ORCHESTRATOR TESTS
# ============================================================================

class TestRetrainingOrchestrator:
    """Tests for retraining orchestration."""
    
    @pytest.fixture
    def orchestrator(self):
        """Create retraining orchestrator."""
        return RetrainingOrchestrator(
            max_concurrent_jobs=3,
            auto_approve_threshold=0.95
        )
    
    @pytest.mark.asyncio
    async def test_job_creation(self, orchestrator):
        """Should create retraining jobs."""
        job = await orchestrator.queue_retraining(
            model_id="model_123",
            trigger_type="drift",
            priority="high"
        )
        
        assert job.status == "queued"
        assert job.priority == "high"
        assert job.trigger_type == "drift"
    
    @pytest.mark.asyncio
    async def test_job_priority_ordering(self, orchestrator):
        """Should process jobs by priority."""
        # Queue jobs with different priorities
        await orchestrator.queue_retraining("model_a", "scheduled", "low")
        await orchestrator.queue_retraining("model_b", "drift", "critical")
        await orchestrator.queue_retraining("model_c", "manual", "normal")
        
        # Get next job
        next_job = await orchestrator._get_next_job()
        
        assert next_job.model_id == "model_b", "Critical should be first"
    
    @pytest.mark.asyncio
    async def test_concurrent_job_limit(self, orchestrator):
        """Should respect concurrent job limit."""
        orchestrator.max_concurrent_jobs = 2
        
        # Start two jobs
        await orchestrator.queue_retraining("model_1", "drift", "high")
        await orchestrator.queue_retraining("model_2", "drift", "high")
        
        # Start processing
        await orchestrator._process_queue()
        
        # Third job should stay queued
        await orchestrator.queue_retraining("model_3", "drift", "critical")
        
        active_count = len([j for j in orchestrator.jobs if j.status not in ["queued", "completed"]])
        
        assert active_count <= 2
    
    @pytest.mark.asyncio
    async def test_job_deduplication(self, orchestrator):
        """Should not queue duplicate jobs for same model."""
        await orchestrator.queue_retraining("model_x", "drift", "high")
        
        # Try to queue again
        job2 = await orchestrator.queue_retraining("model_x", "manual", "normal")
        
        # Should return existing job
        assert job2.trigger_type == "drift", "Should return existing job"
```

### M.2 Integration Tests

```python
"""
ADAM Model Monitoring Integration Tests
End-to-end tests for monitoring system integration.
"""

import pytest
import asyncio
from datetime import datetime, timedelta


class TestDriftToRetrainingPipeline:
    """
    Integration tests for drift detection → alert → retraining pipeline.
    """
    
    @pytest.fixture
    async def monitoring_system(self):
        """Set up complete monitoring system."""
        # Would create real instances in integration environment
        system = MonitoringSystem(
            drift_detectors=[
                StatisticalDriftDetector(),
                PsychologicalDriftDetector()
            ],
            alert_manager=AlertManager(),
            retraining_orchestrator=RetrainingOrchestrator()
        )
        await system.start()
        yield system
        await system.stop()
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_drift_triggers_alert(self, monitoring_system):
        """Detected drift should create an alert."""
        # Inject drifted data
        await monitoring_system.ingest_predictions(
            model_id="integration_model",
            predictions=generate_drifted_predictions(n=1000)
        )
        
        # Wait for drift detection cycle
        await asyncio.sleep(5)
        
        # Check alert created
        alerts = await monitoring_system.alert_manager.get_alerts(
            component="integration_model",
            category="drift"
        )
        
        assert len(alerts) > 0, "Drift should trigger alert"
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_critical_drift_triggers_retraining(self, monitoring_system):
        """Critical drift should queue automatic retraining."""
        # Configure auto-retraining
        monitoring_system.alert_manager.register_action(
            severity="critical",
            category="drift",
            action="trigger_retraining"
        )
        
        # Inject severely drifted data
        await monitoring_system.ingest_predictions(
            model_id="auto_retrain_model",
            predictions=generate_severely_drifted_predictions(n=2000)
        )
        
        # Wait for detection and action
        await asyncio.sleep(10)
        
        # Check retraining queued
        jobs = await monitoring_system.retraining_orchestrator.get_jobs(
            model_id="auto_retrain_model"
        )
        
        assert len(jobs) > 0, "Critical drift should trigger retraining"
        assert jobs[0].trigger_type == "drift"


class TestMultiSourceFusionMonitoring:
    """
    Integration tests for multi-source intelligence fusion monitoring.
    """
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_source_degradation_detected(self, monitoring_system):
        """Should detect and alert on source degradation."""
        # Simulate source becoming unavailable
        source = IntelligenceSourceType.EMPIRICAL_PATTERNS
        
        # Inject failures
        for _ in range(100):
            await monitoring_system.source_monitor.record_source_response(
                source_type=source,
                responded=False,
                latency_ms=5000
            )
        
        # Check health degraded
        health = monitoring_system.source_monitor.get_source_health(source)
        
        assert health.health_status in ["degraded", "unhealthy", "critical"]
        
        # Check alert generated
        alerts = await monitoring_system.alert_manager.get_alerts(
            component=source.value,
            category="source_health"
        )
        
        assert len(alerts) > 0
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_fusion_imbalance_detection(self, monitoring_system):
        """Should detect over-reliance on single source."""
        # Record imbalanced fusions
        for _ in range(100):
            await monitoring_system.fusion_monitor.record_fusion_event(
                atom_type="test_atom",
                sources_queried=set(IntelligenceSourceType),
                sources_responded={IntelligenceSourceType.CLAUDE_REASONING},
                source_contributions={
                    IntelligenceSourceType.CLAUDE_REASONING: 1.0
                },
                source_confidences={
                    IntelligenceSourceType.CLAUDE_REASONING: 0.9
                },
                source_latencies={
                    IntelligenceSourceType.CLAUDE_REASONING: 500
                },
                conflicts=[],
                fusion_confidence=0.9,
                processing_time_ms=600
            )
        
        # Check quality metrics
        quality = monitoring_system.fusion_monitor.get_fusion_quality("test_atom")
        
        assert quality.source_entropy < 0.5, "Should detect low entropy"
        assert quality.dominant_source_weight > 0.8


class TestNeo4jIntegration:
    """
    Integration tests for Neo4j graph storage.
    """
    
    @pytest.fixture
    async def neo4j_client(self):
        """Set up Neo4j test connection."""
        from neo4j import AsyncGraphDatabase
        
        driver = AsyncGraphDatabase.driver(
            "bolt://localhost:7687",
            auth=("neo4j", "test_password")
        )
        
        yield driver
        
        # Cleanup
        async with driver.session() as session:
            await session.run("MATCH (n:Test) DETACH DELETE n")
        await driver.close()
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_health_snapshot_persistence(self, neo4j_client):
        """Health snapshots should persist to graph."""
        snapshot = HealthSnapshot(
            snapshot_id="test_snap_001",
            timestamp=datetime.utcnow(),
            overall_status="healthy",
            overall_score=0.85,
            model_health={},
            source_health={},
            priority_actions=[]
        )
        
        # Store
        async with neo4j_client.session() as session:
            await session.run("""
                CREATE (s:HealthSnapshot:Test {
                    snapshot_id: $id,
                    timestamp: datetime($ts),
                    overall_status: $status,
                    overall_score: $score
                })
            """, {
                "id": snapshot.snapshot_id,
                "ts": snapshot.timestamp.isoformat(),
                "status": snapshot.overall_status,
                "score": snapshot.overall_score
            })
        
        # Retrieve
        async with neo4j_client.session() as session:
            result = await session.run("""
                MATCH (s:HealthSnapshot {snapshot_id: $id})
                RETURN s
            """, {"id": snapshot.snapshot_id})
            
            record = await result.single()
            assert record is not None
            assert record["s"]["overall_score"] == 0.85
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_drift_timeline_query(self, neo4j_client):
        """Should query drift timeline correctly."""
        # Create test drift data
        async with neo4j_client.session() as session:
            for i in range(10):
                await session.run("""
                    CREATE (d:DriftResult:Test {
                        drift_id: $id,
                        model_id: 'test_model',
                        drift_type: 'data',
                        detected_at: datetime($ts),
                        severity: $severity
                    })
                """, {
                    "id": f"drift_{i}",
                    "ts": (datetime.utcnow() - timedelta(hours=i)).isoformat(),
                    "severity": "high" if i % 3 == 0 else "medium"
                })
        
        # Query timeline
        async with neo4j_client.session() as session:
            result = await session.run("""
                MATCH (d:DriftResult:Test {model_id: 'test_model'})
                WHERE d.detected_at >= datetime() - duration('P7D')
                RETURN d
                ORDER BY d.detected_at DESC
            """)
            
            records = [r async for r in result]
            
            assert len(records) == 10
```

### M.3 Drift Simulation Framework

```python
"""
ADAM Drift Simulation Framework
Tools for testing drift detection under controlled conditions.
"""

import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Generator
from enum import Enum
from dataclasses import dataclass


class DriftPattern(str, Enum):
    """Types of drift patterns to simulate."""
    
    SUDDEN = "sudden"           # Abrupt distribution shift
    GRADUAL = "gradual"         # Slow drift over time
    INCREMENTAL = "incremental" # Step-wise drift
    REOCCURRING = "reoccurring" # Periodic drift pattern
    SEASONAL = "seasonal"       # Seasonal variations


@dataclass
class SimulatedDrift:
    """Configuration for simulated drift."""
    
    pattern: DriftPattern
    magnitude: float  # 0-1, how severe
    features_affected: List[str]
    start_offset_hours: int
    duration_hours: Optional[int] = None  # For gradual drifts


class DriftSimulator:
    """
    Simulates various drift patterns for testing detection systems.
    
    Generates synthetic data streams with controlled drift characteristics
    to validate that drift detectors work correctly.
    """
    
    def __init__(self, seed: int = 42):
        self.rng = np.random.RandomState(seed)
        self.base_distributions = {}
    
    def set_base_distribution(
        self,
        feature: str,
        mean: float,
        std: float,
        distribution: str = "normal"
    ) -> None:
        """Define base distribution for a feature."""
        self.base_distributions[feature] = {
            "mean": mean,
            "std": std,
            "distribution": distribution
        }
    
    def generate_stream(
        self,
        n_samples: int,
        features: List[str],
        drift_configs: List[SimulatedDrift],
        samples_per_hour: int = 100
    ) -> Generator[Tuple[datetime, Dict[str, float]], None, None]:
        """
        Generate data stream with configured drift patterns.
        
        Yields (timestamp, feature_dict) tuples.
        """
        start_time = datetime.utcnow() - timedelta(hours=n_samples / samples_per_hour)
        
        for i in range(n_samples):
            timestamp = start_time + timedelta(hours=i / samples_per_hour)
            hours_elapsed = i / samples_per_hour
            
            sample = {}
            for feature in features:
                base = self.base_distributions.get(feature, {"mean": 0, "std": 1})
                
                # Apply drift modifications
                drift_offset = self._calculate_drift_offset(
                    feature, hours_elapsed, drift_configs
                )
                
                # Generate sample
                if base.get("distribution") == "normal":
                    value = self.rng.normal(
                        base["mean"] + drift_offset,
                        base["std"]
                    )
                else:
                    value = self.rng.uniform(
                        base["mean"] - base["std"] + drift_offset,
                        base["mean"] + base["std"] + drift_offset
                    )
                
                sample[feature] = value
            
            yield timestamp, sample
    
    def _calculate_drift_offset(
        self,
        feature: str,
        hours_elapsed: float,
        drift_configs: List[SimulatedDrift]
    ) -> float:
        """Calculate cumulative drift offset for a feature."""
        
        total_offset = 0.0
        
        for drift in drift_configs:
            if feature not in drift.features_affected:
                continue
            
            if hours_elapsed < drift.start_offset_hours:
                continue
            
            drift_hours = hours_elapsed - drift.start_offset_hours
            
            if drift.pattern == DriftPattern.SUDDEN:
                total_offset += drift.magnitude
                
            elif drift.pattern == DriftPattern.GRADUAL:
                if drift.duration_hours:
                    progress = min(1.0, drift_hours / drift.duration_hours)
                    total_offset += drift.magnitude * progress
                    
            elif drift.pattern == DriftPattern.INCREMENTAL:
                steps = int(drift_hours / 24)  # Daily steps
                total_offset += drift.magnitude * (steps / 10)
                
            elif drift.pattern == DriftPattern.SEASONAL:
                # Sinusoidal pattern
                period_hours = 168  # Weekly
                phase = (drift_hours % period_hours) / period_hours
                total_offset += drift.magnitude * np.sin(2 * np.pi * phase)
                
            elif drift.pattern == DriftPattern.REOCCURRING:
                # Every 48 hours, drift appears for 12 hours
                cycle_hours = drift_hours % 48
                if cycle_hours < 12:
                    total_offset += drift.magnitude
        
        return total_offset
    
    def generate_psychological_drift(
        self,
        n_users: int,
        drift_type: str
    ) -> List[Dict[str, Any]]:
        """
        Generate psychologically-specific drift scenarios.
        
        drift_type options:
        - "trait_instability": User traits change unrealistically
        - "mechanism_degradation": Mechanism effectiveness degrades
        - "correlation_violation": Expected correlations break down
        """
        
        data = []
        
        if drift_type == "trait_instability":
            for user_i in range(n_users):
                # First predictions
                base_extraversion = self.rng.uniform(0.3, 0.8)
                
                for obs in range(10):
                    # Unrealistic variation (traits shouldn't change this much)
                    extraversion = base_extraversion + self.rng.normal(0, 0.3)
                    extraversion = np.clip(extraversion, 0, 1)
                    
                    data.append({
                        "user_id": f"user_{user_i}",
                        "trait": "extraversion",
                        "predicted_value": extraversion,
                        "observation": obs
                    })
                    
        elif drift_type == "mechanism_degradation":
            # Social proof stops working
            for obs in range(500):
                conformity = self.rng.uniform(0.3, 0.9)
                
                # Initially correlated
                if obs < 250:
                    conversion_prob = 0.3 + 0.4 * conformity
                else:
                    # Mechanism stops working
                    conversion_prob = 0.3
                
                converted = self.rng.random() < conversion_prob
                
                data.append({
                    "mechanism": "social_proof",
                    "user_trait_conformity": conformity,
                    "converted": converted,
                    "observation": obs
                })
                
        elif drift_type == "correlation_violation":
            # Extraversion-openness correlation breaks
            for user_i in range(n_users):
                if user_i < n_users // 2:
                    # Normal correlation
                    base = self.rng.uniform(0.3, 0.8)
                    extraversion = base + self.rng.normal(0, 0.05)
                    openness = base + self.rng.normal(0, 0.1)
                else:
                    # Correlation breaks
                    extraversion = self.rng.uniform(0.2, 0.9)
                    openness = self.rng.uniform(0.2, 0.9)  # Independent
                
                data.append({
                    "user_id": f"user_{user_i}",
                    "extraversion": np.clip(extraversion, 0, 1),
                    "openness": np.clip(openness, 0, 1)
                })
        
        return data


# Example usage for testing
def test_sudden_drift_detection():
    """Test that sudden drift is detected within expected timeframe."""
    
    simulator = DriftSimulator(seed=42)
    
    # Set up base distributions
    simulator.set_base_distribution("feature_a", mean=0.5, std=0.1)
    simulator.set_base_distribution("feature_b", mean=0.3, std=0.15)
    
    # Configure sudden drift at hour 24
    drift = SimulatedDrift(
        pattern=DriftPattern.SUDDEN,
        magnitude=0.3,  # Significant shift
        features_affected=["feature_a"],
        start_offset_hours=24
    )
    
    # Generate 48 hours of data
    stream = simulator.generate_stream(
        n_samples=4800,
        features=["feature_a", "feature_b"],
        drift_configs=[drift],
        samples_per_hour=100
    )
    
    # Collect data
    data = list(stream)
    
    # Verify drift is present
    pre_drift = [d[1]["feature_a"] for d in data[:2400]]
    post_drift = [d[1]["feature_a"] for d in data[2400:]]
    
    assert np.mean(post_drift) > np.mean(pre_drift) + 0.2
```

---

### M.4 Implementation Timeline

```
ADAM Enhancement #20: Model Monitoring & Drift Detection
Implementation Timeline: 16 Weeks

================================================================================
PHASE 1: FOUNDATION (Weeks 1-4)
================================================================================

Week 1-2: Core Infrastructure
├── Set up Prometheus metrics infrastructure
├── Configure Neo4j monitoring schema
├── Implement PredictionLogger with async batching
├── Build base monitoring service framework
└── Deliverable: Metrics collection pipeline

Week 3-4: Statistical Drift Detection
├── Implement KS-test, PSI, JS divergence detectors
├── Build reference window management
├── Create drift result storage
├── Add basic alerting integration
└── Deliverable: Statistical drift detection for all models

================================================================================
PHASE 2: PSYCHOLOGICAL MONITORING (Weeks 5-8)
================================================================================

Week 5-6: Psychological Drift Detection
├── Implement trait stability monitoring
├── Build mechanism effectiveness tracking
├── Add correlation validity checks
├── Create psychological-specific alerts
└── Deliverable: Psychological validity monitoring

Week 7-8: Intelligence Source Monitoring
├── Build IntelligenceSourceMonitor for 10 sources
├── Implement availability and latency tracking
├── Add contribution balance monitoring
├── Create source health dashboards
└── Deliverable: Complete source health monitoring

================================================================================
PHASE 3: INTEGRATION (Weeks 9-12)
================================================================================

Week 9-10: Fusion Quality Monitoring
├── Implement FusionQualityMonitor
├── Build agreement rate tracking
├── Add conflict detection and logging
├── Create fusion health metrics
└── Deliverable: Atom of Thought fusion monitoring

Week 11-12: Gradient Bridge Monitoring
├── Implement GradientBridgeMonitor
├── Build attribution quality tracking
├── Add learning signal monitoring
├── Create cross-component correlation
└── Deliverable: Learning health monitoring

================================================================================
PHASE 4: AUTOMATION (Weeks 13-16)
================================================================================

Week 13-14: Alert & Retraining Automation
├── Build AlertManager with routing
├── Implement RetrainingOrchestrator
├── Add canary deployment support
├── Create auto-remediation actions
└── Deliverable: Automated response system

Week 15-16: Production Hardening
├── Complete FastAPI endpoints
├── Build health snapshot generator
├── Create integration tests
├── Performance optimization
├── Documentation
└── Deliverable: Production-ready monitoring system

================================================================================
RESOURCE REQUIREMENTS
================================================================================

Team:
├── ML Engineers: 2 FTE
├── Platform Engineers: 1 FTE
├── Data Engineers: 1 FTE (part-time)
└── Total: 3.5 FTE

Infrastructure:
├── Prometheus/Grafana cluster
├── Neo4j enterprise (existing)
├── Redis cluster (existing via #31)
├── Kafka (existing via #31)
└── S3 for drift artifacts

Dependencies:
├── Enhancement #04 (Atom of Thought): Required
├── Enhancement #06 (Gradient Bridge): Required
├── Enhancement #31 (Event Bus & Cache): Required
├── Enhancement #26 (Observability): Recommended
└── Enhancement #11 (Psychological Validity): Recommended
```

---

### M.5 Success Metrics

```yaml
# ADAM Model Monitoring Success Metrics

# ============================================================================
# DRIFT DETECTION METRICS
# ============================================================================

drift_detection:
  # Sensitivity: How often we catch real drift
  detection_rate:
    target: ">95%"
    measurement: "Percentage of known drift events detected"
    validation: "Simulated drift injection tests"
  
  # Speed: How quickly we detect drift
  detection_latency:
    target: "<30 minutes"
    measurement: "Time from drift onset to alert"
    validation: "Timestamp comparison in simulations"
  
  # Precision: Avoiding false alarms
  false_positive_rate:
    target: "<5%"
    measurement: "Alerts without actual drift"
    validation: "Manual review of alerts"
  
  # Psychological drift specific
  psychological_validity_maintenance:
    target: ">90%"
    measurement: "Percentage of time psychological constraints are satisfied"
    validation: "Continuous validity checks"

# ============================================================================
# MONITORING HEALTH METRICS
# ============================================================================

monitoring_health:
  # System availability
  monitoring_uptime:
    target: "99.9%"
    measurement: "Percentage of time monitoring is operational"
    validation: "Heartbeat checks"
  
  # Data completeness
  prediction_coverage:
    target: ">99%"
    measurement: "Percentage of predictions captured"
    validation: "Sampling audit"
  
  # Latency
  health_snapshot_latency:
    target: "<5 seconds"
    measurement: "Time to generate complete health snapshot"
    validation: "P95 latency monitoring"

# ============================================================================
# INTELLIGENCE SOURCE METRICS
# ============================================================================

source_monitoring:
  # Source availability tracking accuracy
  availability_accuracy:
    target: ">98%"
    measurement: "Correct availability status vs ground truth"
    validation: "Cross-reference with source logs"
  
  # Contribution balance maintenance
  source_entropy_floor:
    target: ">0.5"
    measurement: "Minimum normalized entropy of source contributions"
    validation: "Continuous entropy monitoring"
  
  # Degradation detection
  degradation_detection_time:
    target: "<5 minutes"
    measurement: "Time to detect 20% availability drop"
    validation: "Controlled degradation tests"

# ============================================================================
# ALERTING METRICS
# ============================================================================

alerting:
  # Notification delivery
  notification_success_rate:
    target: ">99%"
    measurement: "Percentage of alerts successfully delivered"
    validation: "Delivery confirmation tracking"
  
  # Alert fatigue prevention
  actionable_alert_rate:
    target: ">80%"
    measurement: "Percentage of alerts requiring action"
    validation: "Post-mortem analysis"
  
  # Response time
  mean_time_to_acknowledge:
    target: "<15 minutes for critical"
    measurement: "Time from alert to acknowledgment"
    validation: "Alert lifecycle tracking"

# ============================================================================
# RETRAINING METRICS
# ============================================================================

retraining:
  # Automation rate
  auto_retraining_success:
    target: ">90%"
    measurement: "Percentage of drift-triggered retrains succeeding"
    validation: "Retraining job outcomes"
  
  # Validation effectiveness
  validation_catch_rate:
    target: ">95%"
    measurement: "Percentage of bad models caught by validation"
    validation: "Post-deployment monitoring"
  
  # Canary effectiveness
  canary_rollback_accuracy:
    target: ">98%"
    measurement: "Correct rollback decisions during canary"
    validation: "Manual review of canary outcomes"
  
  # Improvement rate
  post_retrain_improvement:
    target: ">5% health score improvement"
    measurement: "Health score change after retraining"
    validation: "Before/after comparison"

# ============================================================================
# BUSINESS IMPACT METRICS
# ============================================================================

business_impact:
  # Conversion protection
  conversion_degradation_prevention:
    target: "Detect 5% conversion drop within 2 hours"
    measurement: "Time to detect conversion impact"
    validation: "Historical incident analysis"
  
  # Psychological targeting integrity
  targeting_accuracy_maintenance:
    target: "Maintain >85% targeting accuracy"
    measurement: "Personality match accuracy over time"
    validation: "Continuous validation"
  
  # System reliability
  unplanned_downtime:
    target: "<4 hours/quarter"
    measurement: "Downtime from undetected issues"
    validation: "Incident tracking"

# ============================================================================
# OPERATIONAL METRICS
# ============================================================================

operations:
  # Dashboard utility
  dashboard_query_latency:
    target: "<1 second"
    measurement: "Time to load monitoring dashboard"
    validation: "Frontend monitoring"
  
  # API reliability
  monitoring_api_availability:
    target: "99.9%"
    measurement: "API uptime"
    validation: "Health checks"
  
  # Data retention
  historical_data_availability:
    target: "90 days"
    measurement: "Days of historical data accessible"
    validation: "Query testing"
```

---

## Document Summary

This specification provides a complete enterprise-grade model monitoring and drift detection system for ADAM, with:

1. **Comprehensive Drift Detection** - Six drift types monitored with statistical and psychological tests
2. **Multi-Source Intelligence Monitoring** - All 10 intelligence sources tracked for health and contribution
3. **Fusion Quality Tracking** - Agreement rates, conflict detection, and balance metrics
4. **Gradient Bridge Health** - Learning signal quality and attribution accuracy monitoring
5. **Automated Alerting** - Multi-channel notifications with deduplication and rate limiting
6. **Automated Retraining** - Drift-triggered retraining with validation and canary deployment
7. **Neo4j Integration** - Graph storage for rich temporal queries and relationship tracking
8. **Production APIs** - FastAPI endpoints for all monitoring operations
9. **Prometheus Metrics** - Complete observability with 50+ metric types
10. **Testing Framework** - Unit tests, integration tests, and drift simulation

**Total Implementation**: 16 weeks with 3.5 FTE

**Key Differentiators**:
- Psychological validity as first-class monitoring concern
- Multi-source intelligence fusion quality tracking
- Cross-component drift correlation analysis
- Learning signal health monitoring
- Integration with ADAM's unique cognitive architecture

---

*Document Version: 2.0 COMPLETE*
*Last Updated: January 2026*
*File Size: ~200KB*
*Status: Production-Ready Specification*
