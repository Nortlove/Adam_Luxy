# ADAM Enhancement #13: Cold Start Strategy
## Enterprise-Grade Bayesian Profiling with Hierarchical Priors & Thompson Sampling

**Version**: 2.0 COMPLETE  
**Date**: January 2026  
**Priority**: P1 - Production Scale Requirement (75% of traffic underserved without this)  
**Estimated Implementation**: 12 person-weeks  
**Dependencies**: #02 (Blackboard), #03 (Meta-Learning), #06 (Gradient Bridge), #30 (Feature Store), #31 (Event Bus & Cache)  
**Dependents**: #09 (Inference Engine), #14 (Brand Intelligence), #15 (Copy Generation), #28 (WPP Ad Desk)  
**File Size**: ~130KB (Enterprise Production-Ready)

---

## Part 1 Table of Contents

### SECTION A: STRATEGIC OVERVIEW
1. [Executive Summary](#executive-summary)
2. [The Cold Start Problem](#the-cold-start-problem)
3. [Architecture Overview](#architecture-overview)
4. [Research Foundations](#research-foundations)

### SECTION B: PYDANTIC DATA MODELS
5. [Core Enums & Types](#core-enums-types)
6. [User Data Models](#user-data-models)
7. [Prior Distribution Models](#prior-distribution-models)
8. [Archetype Models](#archetype-models)
9. [Decision Output Models](#decision-output-models)

### SECTION C: HIERARCHICAL PRIOR SYSTEM
10. [Population Priors](#population-priors)
11. [Cluster Priors](#cluster-priors)
12. [Demographic Priors](#demographic-priors)
13. [Contextual Priors](#contextual-priors)
14. [Prior Hierarchy Engine](#prior-hierarchy-engine)

### SECTION D: THOMPSON SAMPLING INTEGRATION
15. [Mechanism Effectiveness Priors](#mechanism-effectiveness-priors)
16. [Archetype × Mechanism Beta Distributions](#archetype-mechanism-beta-distributions)
17. [Thompson Sampling for Cold Users](#thompson-sampling-for-cold-users)
18. [Exploration Bonus System](#exploration-bonus-system)

### SECTION E: PSYCHOLOGICAL ARCHETYPE SYSTEM
19. [Research-Grounded Archetypes](#research-grounded-archetypes)
20. [Archetype Detection Engine](#archetype-detection-engine)
21. [Archetype Mechanism Responsiveness](#archetype-mechanism-responsiveness)
22. [Archetype Evolution Tracking](#archetype-evolution-tracking)

### SECTION F: PROGRESSIVE PROFILING ENGINE
23. [Bayesian Update Engine](#bayesian-update-engine)
24. [Conjugate Prior Updates](#conjugate-prior-updates)
25. [Confidence Calibration](#confidence-calibration)
26. [Information-Gain Exploration](#information-gain-exploration)

### SECTION G: EVENT BUS INTEGRATION (#31)
27. [Cold Start Event Contracts](#cold-start-event-contracts)
28. [Tier Transition Events](#tier-transition-events)
29. [Prior Update Events](#prior-update-events)
30. [Outcome Signal Consumption](#outcome-signal-consumption)

### SECTION H: CACHE INTEGRATION (#31)
31. [Hot Priors Cache](#hot-priors-cache)
32. [Archetype Profile Cache](#archetype-profile-cache)
33. [Cache Invalidation Strategy](#cache-invalidation-strategy)

### SECTION I: GRADIENT BRIDGE INTEGRATION (#06)
34. [Learning Signal Emission](#learning-signal-emission)
35. [Prior Update Propagation](#prior-update-propagation)
36. [Cold Start Attribution](#cold-start-attribution)

### SECTION J: NEO4J SCHEMA
37. [Prior Distribution Nodes](#prior-distribution-nodes)
38. [Archetype Graph Model](#archetype-graph-model)
39. [User Cold Start Profile](#user-cold-start-profile)
40. [Learning Analytics Queries](#learning-analytics-queries)

### SECTION K: LANGGRAPH WORKFLOW
41. [Cold Start Router Node](#cold-start-router-node)
42. [Meta-Learner Integration](#meta-learner-integration)
43. [Atom of Thought Priors Injection](#atom-of-thought-priors-injection)

### SECTION L: FASTAPI ENDPOINTS
44. [Prior Inspection API](#prior-inspection-api)
45. [Archetype Management API](#archetype-management-api)
46. [Manual Override API](#manual-override-api)

### SECTION M: PROMETHEUS METRICS
47. [Tier Distribution Metrics](#tier-distribution-metrics)
48. [Prior Accuracy Metrics](#prior-accuracy-metrics)
49. [Profile Velocity Metrics](#profile-velocity-metrics)

### SECTION N: TESTING & OPERATIONS
50. [Unit Tests](#unit-tests)
51. [Prior Calibration Tests](#prior-calibration-tests)
52. [Implementation Timeline](#implementation-timeline)
53. [Success Metrics](#success-metrics)

---

# SECTION A: STRATEGIC OVERVIEW

## Executive Summary

### The Critical Role of Cold Start

Cold Start Strategy is the **gatekeeper** that determines whether ADAM can serve psychological intelligence to ALL users, not just the 25% with rich profiles. Without this component:

- **75% of traffic gets random/popular selection** - No better than competitors
- **New advertisers have no targeting intelligence** - 2-4 week learning period
- **New content has no audience matching** - Missed opportunities
- **System can't scale** - Growth means more cold users

### What This Specification Delivers

| Capability | Description | Business Impact |
|------------|-------------|-----------------|
| **Hierarchical Priors** | Population → Cluster → Demographic → Context | Cold users get best available intelligence |
| **Thompson Sampling Integration** | Mechanism effectiveness priors per archetype | Optimal explore/exploit from first impression |
| **Research-Grounded Archetypes** | 8 psychological archetypes with mechanism maps | 1.3x+ CTR vs. random immediately |
| **Progressive Profiling** | Bayesian updates with conjugate priors | 14-day median to full profile |
| **Cross-Component Learning** | Outcomes update all prior hierarchies | Every interaction makes system smarter |

### Expected Performance

| Metric | Without Cold Start | With Cold Start | Improvement |
|--------|-------------------|-----------------|-------------|
| Cold user CTR | Baseline (random) | 1.3x+ | +30% |
| Cold user CVR | Baseline (random) | 1.2x+ | +20% |
| Days to full profile | Never | <14 days median | New capability |
| New advertiser onboarding | 2-4 weeks | Immediate | 4x faster |

---

## The Cold Start Problem

### Scale of Impact

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                                                                                         │
│   THE COLD START PROBLEM: 75% OF TRAFFIC UNDERSERVED                                   │
│   ═══════════════════════════════════════════════════                                   │
│                                                                                         │
│   ┌─────────────────────────────────────────────────────────────────────────────────┐   │
│   │                                                                                 │   │
│   │   TRAFFIC DISTRIBUTION BY DATA RICHNESS                                        │   │
│   │                                                                                 │   │
│   │   ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░│   │
│   │   │◄────────────── 75% COLD START ──────────────►│◄─── 25% PROFILED ───►│      │   │
│   │                                                                                 │   │
│   │   Breakdown:                                                                    │   │
│   │   ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓ ~40% Anonymous visitors (session data only)                │   │
│   │   ▓▓▓▓▓▓▓▓ ~20% Returning with sparse data (few interactions)                  │   │
│   │   ▓▓▓▓▓▓ ~15% New registered users (demographics only)                         │   │
│   │   ░░░░░░░░░░ ~25% Rich profile users (full ADAM intelligence)                  │   │
│   │                                                                                 │   │
│   └─────────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                         │
│   WITHOUT COLD START STRATEGY:                                                          │
│   • 75% of traffic → Random/Popular selection (no competitive advantage)               │
│   • New users → Poor first experience → Lower retention                                │
│   • New advertisers → 2-4 week blind period → Lost revenue                             │
│   • System can't demonstrate value on majority of traffic                              │
│                                                                                         │
│   WITH COLD START STRATEGY:                                                             │
│   • 75% of traffic → Best-available psychological intelligence                         │
│   • New users → Archetype-matched targeting → Better first experience                  │
│   • New advertisers → Immediate category priors → Fast value demonstration             │
│   • Every interaction accelerates profiling → Rapid transition to full intelligence    │
│                                                                                         │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

### The Four Cold Start Scenarios

| Scenario | What's Unknown | Available Signals | Strategy |
|----------|----------------|-------------------|----------|
| **New User** | Personality, preferences, history | Demographics, context, session behavior | Hierarchical priors + archetype matching |
| **New Content** | Audience fit, psychological resonance | Content features, category | Content-personality mappings |
| **New Advertiser** | Brand-user fit, mechanism effectiveness | Brand profile, category | Brand archetype + category priors |
| **New Context** | Time/channel performance | Time, channel metadata | Temporal + channel priors |

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                                                                                     │
│                    ADAM COLD START STRATEGY: COMPLETE ARCHITECTURE                                  │
│                                                                                                     │
│  ┌───────────────────────────────────────────────────────────────────────────────────────────────┐  │
│  │                                                                                               │  │
│  │   LAYER 1: HIERARCHICAL PRIOR SYSTEM                                                         │  │
│  │   ═══════════════════════════════════                                                         │  │
│  │                                                                                               │  │
│  │   ┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐      │  │
│  │   │ POPULATION      │   │ CLUSTER         │   │ DEMOGRAPHIC     │   │ CONTEXTUAL      │      │  │
│  │   │ PRIORS          │   │ PRIORS          │   │ PRIORS          │   │ PRIORS          │      │  │
│  │   │                 │   │                 │   │                 │   │                 │      │  │
│  │   │ • Amazon corpus │   │ • Psychological │   │ • Age bands     │   │ • Content type  │      │  │
│  │   │ • Research lit  │   │   segments      │   │ • Gender        │   │ • Time of day   │      │  │
│  │   │ • Category norms│   │ • Behavioral    │   │ • Location      │   │ • Device        │      │  │
│  │   │                 │   │   clusters      │   │ • Education     │   │ • Referral      │      │  │
│  │   └────────┬────────┘   └────────┬────────┘   └────────┬────────┘   └────────┬────────┘      │  │
│  │            │                     │                     │                     │               │  │
│  │            └──────────────────┬──┴─────────────────────┴──┬──────────────────┘               │  │
│  │                               │                           │                                   │  │
│  │                               ▼                           ▼                                   │  │
│  │                    ┌─────────────────────────────────────────────────┐                       │  │
│  │                    │           PRIOR HIERARCHY ENGINE                │                       │  │
│  │                    │                                                 │                       │  │
│  │                    │  • Bayesian prior combination                   │                       │  │
│  │                    │  • Uncertainty propagation                      │                       │  │
│  │                    │  • Confidence-weighted blending                 │                       │  │
│  │                    └───────────────────────┬─────────────────────────┘                       │  │
│  │                                            │                                                  │  │
│  └────────────────────────────────────────────┼──────────────────────────────────────────────────┘  │
│                                               │                                                     │
│  ┌────────────────────────────────────────────┼──────────────────────────────────────────────────┐  │
│  │                                            ▼                                                  │  │
│  │   LAYER 2: PSYCHOLOGICAL ARCHETYPE SYSTEM                                                    │  │
│  │   ═══════════════════════════════════════                                                    │  │
│  │                                                                                               │  │
│  │   ┌──────────────────────────────────────────────────────────────────────────────────────┐   │  │
│  │   │                         8 RESEARCH-GROUNDED ARCHETYPES                               │   │  │
│  │   │                                                                                      │   │  │
│  │   │   ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐                        │   │  │
│  │   │   │EXPLORER   │  │ACHIEVER   │  │CONNECTOR  │  │GUARDIAN   │                        │   │  │
│  │   │   │High O,    │  │High C, Low│  │High E, A  │  │High N,    │                        │   │  │
│  │   │   │Promotion  │  │N, Promot. │  │Low N      │  │Prevention │                        │   │  │
│  │   │   └───────────┘  └───────────┘  └───────────┘  └───────────┘                        │   │  │
│  │   │   ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐                        │   │  │
│  │   │   │ANALYST    │  │CREATOR    │  │NURTURER   │  │PRAGMATIST │                        │   │  │
│  │   │   │High C, O  │  │High O,    │  │High A,    │  │Balanced,  │                        │   │  │
│  │   │   │Low E      │  │Low C      │  │Low Promot.│  │Neutral    │                        │   │  │
│  │   │   └───────────┘  └───────────┘  └───────────┘  └───────────┘                        │   │  │
│  │   │                                                                                      │   │  │
│  │   │   Each archetype has:                                                                │   │  │
│  │   │   • Big Five profile (mean + variance)                                               │   │  │
│  │   │   • Regulatory focus distribution                                                    │   │  │
│  │   │   • Mechanism effectiveness Beta priors (per mechanism)                              │   │  │
│  │   │   • Construal level tendency                                                         │   │  │
│  │   │   • Value hierarchy                                                                  │   │  │
│  │   │                                                                                      │   │  │
│  │   └──────────────────────────────────────────────────────────────────────────────────────┘   │  │
│  │                                            │                                                  │  │
│  └────────────────────────────────────────────┼──────────────────────────────────────────────────┘  │
│                                               │                                                     │
│  ┌────────────────────────────────────────────┼──────────────────────────────────────────────────┐  │
│  │                                            ▼                                                  │  │
│  │   LAYER 3: THOMPSON SAMPLING INTEGRATION                                                     │  │
│  │   ═══════════════════════════════════════                                                    │  │
│  │                                                                                               │  │
│  │   For each (User × Mechanism) pair:                                                          │  │
│  │                                                                                               │  │
│  │   ┌─────────────────────────────────────────────────────────────────────────────────────┐    │  │
│  │   │  Mechanism              │ Alpha  │ Beta   │ Prior Source      │ Samples │ Mean     │    │  │
│  │   │  ─────────────────────  │ ────── │ ────── │ ─────────────────  │ ─────── │ ──────   │    │  │
│  │   │  social_proof           │ 3.2    │ 1.8    │ Archetype: CONN.  │ 5       │ 0.64     │    │  │
│  │   │  scarcity               │ 2.1    │ 2.9    │ Cluster: 17       │ 5       │ 0.42     │    │  │
│  │   │  authority              │ 4.5    │ 1.5    │ Demo: 25-34 Male  │ 6       │ 0.75     │    │  │
│  │   │  mimetic_desire         │ 2.8    │ 2.2    │ Population        │ 5       │ 0.56     │    │  │
│  │   │  identity_construction  │ 3.5    │ 1.5    │ Context: Podcast  │ 5       │ 0.70     │    │  │
│  │   │  temporal_construal     │ 2.0    │ 3.0    │ Population        │ 5       │ 0.40     │    │  │
│  │   │  wanting_liking         │ 3.8    │ 2.2    │ Archetype: EXPL.  │ 6       │ 0.63     │    │  │
│  │   │  regulatory_focus       │ 4.0    │ 2.0    │ Demo: High-income │ 6       │ 0.67     │    │  │
│  │   │  construal_level        │ 2.5    │ 2.5    │ Population        │ 5       │ 0.50     │    │  │
│  │   └─────────────────────────────────────────────────────────────────────────────────────┘    │  │
│  │                                                                                               │  │
│  │   Thompson Sampling: Sample θ ~ Beta(α, β), select mechanism* = argmax(θ)                   │  │
│  │   Exploration bonus: +ε for high-uncertainty (low α+β) mechanisms                            │  │
│  │                                                                                               │  │
│  └───────────────────────────────────────────────────────────────────────────────────────────────┘  │
│                                               │                                                     │
│  ┌────────────────────────────────────────────┼──────────────────────────────────────────────────┐  │
│  │                                            ▼                                                  │  │
│  │   LAYER 4: PROGRESSIVE PROFILING ENGINE                                                      │  │
│  │   ═══════════════════════════════════════                                                    │  │
│  │                                                                                               │  │
│  │   ┌─────────────────────────────────────────────────────────────────────────────────────┐    │  │
│  │   │                                                                                     │    │  │
│  │   │   BAYESIAN UPDATE LOOP (Every Interaction)                                         │    │  │
│  │   │                                                                                     │    │  │
│  │   │   1. OBSERVE outcome (click, skip, convert)                                        │    │  │
│  │   │      ↓                                                                             │    │  │
│  │   │   2. COMPUTE likelihood P(outcome | trait, mechanism)                              │    │  │
│  │   │      ↓                                                                             │    │  │
│  │   │   3. UPDATE posterior: P(trait | outcome) ∝ P(outcome | trait) × P(trait)         │    │  │
│  │   │      ↓                                                                             │    │  │
│  │   │   4. EMIT learning signal → Gradient Bridge                                        │    │  │
│  │   │      ↓                                                                             │    │  │
│  │   │   5. CHECK tier transition threshold                                               │    │  │
│  │   │      ↓                                                                             │    │  │
│  │   │   6. UPDATE caches (profile, priors)                                              │    │  │
│  │   │                                                                                     │    │  │
│  │   └─────────────────────────────────────────────────────────────────────────────────────┘    │  │
│  │                                                                                               │  │
│  │   Profile Velocity Tracking:                                                                  │  │
│  │   • Interactions per day                                                                      │  │
│  │   • Information gain per interaction                                                         │  │
│  │   • Estimated days to full profile                                                           │  │
│  │   • Confidence convergence rate                                                              │  │
│  │                                                                                               │  │
│  └───────────────────────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                                     │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Research Foundations

### Prior Distribution Theory

| Concept | Source | Application in ADAM |
|---------|--------|---------------------|
| **Hierarchical Bayesian Models** | Gelman et al. (2013) | Prior hierarchy: population → cluster → individual |
| **Conjugate Priors** | Raiffa & Schlaifer (1961) | Beta-Binomial for mechanism effectiveness |
| **Empirical Bayes** | Robbins (1956) | Population priors from Amazon corpus |
| **Jeffreys Prior** | Jeffreys (1961) | Uninformative priors for new contexts |

### Psychological Archetype Research

| Research | Finding | Application |
|----------|---------|-------------|
| **Jung (1921)** | Psychological types cluster | Foundation for archetype system |
| **Big Five meta-analysis** | 5 stable dimensions | Archetype trait profiles |
| **Matz et al. (2017)** | Personality predicts ad response | Archetype → mechanism mapping |
| **Hirsh et al. (2012)** | Trait-message matching | Archetype message templates |

### Thompson Sampling Theory

| Paper | Contribution | ADAM Implementation |
|-------|--------------|---------------------|
| **Thompson (1933)** | Original algorithm | Core mechanism selection |
| **Agrawal & Goyal (2012)** | Regret bounds | Convergence guarantees |
| **Russo et al. (2018)** | Contextual Thompson | Context-aware priors |
| **Chapelle & Li (2011)** | Empirical comparison | Superiority over UCB |

---

# SECTION B: PYDANTIC DATA MODELS

## Core Enums & Types

```python
# =============================================================================
# ADAM Enhancement #13: Core Enums & Types
# Location: adam/cold_start/models/enums.py
# =============================================================================

"""
Core enumerations and type definitions for Cold Start Strategy.
"""

from __future__ import annotations
from enum import Enum
from typing import Literal


class UserDataTier(str, Enum):
    """
    Classification of users by available data richness.
    
    Each tier determines which cold start strategy to apply and
    what prior sources are available.
    """
    # Tier 0: First pageview - no data at all
    TIER_0_ANONYMOUS_NEW = "tier_0_anonymous_new"
    
    # Tier 1: Has session behavior (clicks, scrolls, time on page)
    TIER_1_ANONYMOUS_SESSION = "tier_1_anonymous_session"
    
    # Tier 2: Registered with demographics only
    TIER_2_REGISTERED_MINIMAL = "tier_2_registered_minimal"
    
    # Tier 3: Some behavioral history (5-20 interactions)
    TIER_3_REGISTERED_SPARSE = "tier_3_registered_sparse"
    
    # Tier 4: Moderate history (20-50 interactions)
    TIER_4_REGISTERED_MODERATE = "tier_4_registered_moderate"
    
    # Tier 5: Full psychological profile available
    TIER_5_PROFILED_FULL = "tier_5_profiled_full"


class PriorSource(str, Enum):
    """Source of prior distribution."""
    POPULATION = "population"           # Global population from Amazon corpus
    CLUSTER = "cluster"                 # Psychological cluster priors
    DEMOGRAPHIC = "demographic"         # Age/gender/location priors
    CONTEXTUAL = "contextual"           # Content/time/device priors
    ARCHETYPE = "archetype"             # Matched archetype priors
    CATEGORY = "category"               # Product category priors
    BRAND = "brand"                     # Brand-specific priors
    HISTORICAL_USER = "historical_user" # User's own history


class ArchetypeID(str, Enum):
    """
    Research-grounded psychological archetypes.
    
    Based on Jung's psychological types, validated through
    Big Five research and advertising response studies.
    """
    EXPLORER = "explorer"           # High Openness, Promotion-focused
    ACHIEVER = "achiever"           # High Conscientiousness, Goal-oriented
    CONNECTOR = "connector"         # High Extraversion + Agreeableness
    GUARDIAN = "guardian"           # High Neuroticism, Prevention-focused
    ANALYST = "analyst"             # High Conscientiousness + Openness, Low E
    CREATOR = "creator"             # High Openness, Low Conscientiousness
    NURTURER = "nurturer"           # High Agreeableness, Community-oriented
    PRAGMATIST = "pragmatist"       # Balanced traits, Practical focus


class CognitiveMechanism(str, Enum):
    """
    The 9 cognitive mechanisms for persuasion.
    
    Each mechanism has effectiveness priors that vary by user.
    """
    CONSTRUAL_LEVEL = "construal_level"
    REGULATORY_FOCUS = "regulatory_focus"
    AUTOMATIC_EVALUATION = "automatic_evaluation"
    WANTING_LIKING = "wanting_liking"
    MIMETIC_DESIRE = "mimetic_desire"
    ATTENTION_DYNAMICS = "attention_dynamics"
    TEMPORAL_CONSTRUAL = "temporal_construal"
    IDENTITY_CONSTRUCTION = "identity_construction"
    EVOLUTIONARY_MOTIVE = "evolutionary_motive"


class PersonalityTrait(str, Enum):
    """Big Five personality traits."""
    OPENNESS = "openness"
    CONSCIENTIOUSNESS = "conscientiousness"
    EXTRAVERSION = "extraversion"
    AGREEABLENESS = "agreeableness"
    NEUROTICISM = "neuroticism"


class ExtendedConstruct(str, Enum):
    """Extended psychological constructs beyond Big Five."""
    REGULATORY_FOCUS_PROMOTION = "regulatory_focus_promotion"
    REGULATORY_FOCUS_PREVENTION = "regulatory_focus_prevention"
    NEED_FOR_COGNITION = "need_for_cognition"
    SELF_MONITORING = "self_monitoring"


class ColdStartStrategy(str, Enum):
    """Strategy applied for cold start inference."""
    POPULATION_PRIOR_ONLY = "population_prior_only"
    CONTEXTUAL_INFERENCE = "contextual_inference"
    ARCHETYPE_MATCH = "archetype_match"
    DEMOGRAPHIC_PRIOR = "demographic_prior"
    CLUSTER_TRANSFER = "cluster_transfer"
    PROGRESSIVE_BAYESIAN = "progressive_bayesian"
    FULL_PROFILE = "full_profile"
```

---

## User Data Models

```python
# =============================================================================
# ADAM Enhancement #13: User Data Models
# Location: adam/cold_start/models/user.py
# =============================================================================

"""
User data models for Cold Start classification and profiling.
"""

from __future__ import annotations
from datetime import datetime
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, field_validator, computed_field
import uuid

from .enums import UserDataTier, ArchetypeID, PriorSource


class UserDataInventory(BaseModel):
    """
    Inventory of available data for a user.
    
    Determines which cold start strategies are applicable.
    """
    # Identity
    has_user_id: bool = False
    has_device_id: bool = False
    has_session_id: bool = True  # Always have session
    
    # Demographics
    has_age: bool = False
    has_gender: bool = False
    has_location: bool = False
    has_language: bool = False
    has_income_bracket: bool = False
    has_education_level: bool = False
    
    # Behavioral
    has_behavioral_history: bool = False
    has_purchase_history: bool = False
    has_content_preferences: bool = False
    
    # Profile
    has_psychological_profile: bool = False
    has_archetype_assignment: bool = False
    has_mechanism_priors: bool = False
    
    @computed_field
    @property
    def demographic_completeness(self) -> float:
        """Fraction of demographic fields available."""
        fields = [
            self.has_age, self.has_gender, self.has_location,
            self.has_language, self.has_income_bracket, self.has_education_level
        ]
        return sum(fields) / len(fields)
    
    @computed_field
    @property
    def total_data_richness(self) -> float:
        """Overall data richness score (0-1)."""
        weights = {
            "identity": 0.1,
            "demographics": 0.2,
            "behavioral": 0.3,
            "profile": 0.4
        }
        
        identity_score = (self.has_user_id * 0.7 + self.has_device_id * 0.3)
        behavioral_score = (
            self.has_behavioral_history * 0.4 +
            self.has_purchase_history * 0.4 +
            self.has_content_preferences * 0.2
        )
        profile_score = (
            self.has_psychological_profile * 0.5 +
            self.has_archetype_assignment * 0.3 +
            self.has_mechanism_priors * 0.2
        )
        
        return (
            weights["identity"] * identity_score +
            weights["demographics"] * self.demographic_completeness +
            weights["behavioral"] * behavioral_score +
            weights["profile"] * profile_score
        )


class UserInteractionStats(BaseModel):
    """Quantified interaction statistics for a user."""
    
    total_interactions: int = 0
    ad_impressions: int = 0
    ad_clicks: int = 0
    ad_conversions: int = 0
    
    content_views: int = 0
    content_engagements: int = 0
    
    days_since_first_seen: int = 0
    days_since_last_interaction: int = 0
    
    unique_content_types: int = 0
    unique_ad_categories: int = 0
    
    @computed_field
    @property
    def click_through_rate(self) -> float:
        """Overall CTR."""
        if self.ad_impressions == 0:
            return 0.0
        return self.ad_clicks / self.ad_impressions
    
    @computed_field
    @property
    def conversion_rate(self) -> float:
        """Overall conversion rate."""
        if self.ad_clicks == 0:
            return 0.0
        return self.ad_conversions / self.ad_clicks
    
    @computed_field
    @property
    def interaction_velocity(self) -> float:
        """Interactions per day."""
        if self.days_since_first_seen == 0:
            return float(self.total_interactions)
        return self.total_interactions / self.days_since_first_seen


class UserDataProfile(BaseModel):
    """
    Complete data profile for a user.
    
    Used to classify into data tier and select cold start strategy.
    """
    # Identifiers
    user_id: Optional[str] = None
    device_id: Optional[str] = None
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    
    # Data inventory
    inventory: UserDataInventory = Field(default_factory=UserDataInventory)
    
    # Interaction statistics
    stats: UserInteractionStats = Field(default_factory=UserInteractionStats)
    
    # Demographics (if available)
    age_bracket: Optional[str] = None
    gender: Optional[str] = None
    country: Optional[str] = None
    region: Optional[str] = None
    language: Optional[str] = None
    income_bracket: Optional[str] = None
    education_level: Optional[str] = None
    
    # Current context
    current_content_type: Optional[str] = None
    current_content_id: Optional[str] = None
    current_device_type: Optional[str] = None
    current_hour_of_day: Optional[int] = None
    current_day_of_week: Optional[int] = None
    referral_source: Optional[str] = None
    
    # Profile status
    assigned_archetype: Optional[ArchetypeID] = None
    archetype_confidence: float = 0.0
    profile_confidence: float = 0.0
    
    # Timestamps
    first_seen_at: Optional[datetime] = None
    last_interaction_at: Optional[datetime] = None
    profile_updated_at: Optional[datetime] = None
    
    @computed_field
    @property
    def data_tier(self) -> UserDataTier:
        """Classify user into data tier."""
        # Full profile available
        if (self.inventory.has_psychological_profile and 
            self.profile_confidence >= 0.7):
            return UserDataTier.TIER_5_PROFILED_FULL
        
        # Moderate behavioral history
        if (self.inventory.has_user_id and 
            self.stats.total_interactions >= 20):
            return UserDataTier.TIER_4_REGISTERED_MODERATE
        
        # Sparse behavioral history
        if (self.inventory.has_user_id and 
            self.stats.total_interactions >= 5):
            return UserDataTier.TIER_3_REGISTERED_SPARSE
        
        # Demographics only
        if (self.inventory.has_user_id and 
            self.inventory.demographic_completeness > 0.3):
            return UserDataTier.TIER_2_REGISTERED_MINIMAL
        
        # Session behavior available
        if self.stats.total_interactions > 0:
            return UserDataTier.TIER_1_ANONYMOUS_SESSION
        
        # Completely new
        return UserDataTier.TIER_0_ANONYMOUS_NEW


class UserTierClassifier(BaseModel):
    """
    Classifier for determining user data tier.
    
    Uses configurable thresholds for tier boundaries.
    """
    
    # Tier thresholds
    sparse_interaction_threshold: int = 5
    moderate_interaction_threshold: int = 20
    full_profile_interaction_threshold: int = 50
    full_profile_confidence_threshold: float = 0.7
    demographic_completeness_threshold: float = 0.3
    
    def classify(self, profile: UserDataProfile) -> UserDataTier:
        """
        Classify user into appropriate data tier.
        
        Args:
            profile: User's data profile
            
        Returns:
            Appropriate UserDataTier
        """
        # Check for full profile first
        if (profile.inventory.has_psychological_profile and
            profile.profile_confidence >= self.full_profile_confidence_threshold):
            return UserDataTier.TIER_5_PROFILED_FULL
        
        # Not registered
        if not profile.inventory.has_user_id:
            if profile.stats.total_interactions > 0:
                return UserDataTier.TIER_1_ANONYMOUS_SESSION
            return UserDataTier.TIER_0_ANONYMOUS_NEW
        
        # Registered with varying data richness
        interactions = profile.stats.total_interactions
        
        if interactions >= self.moderate_interaction_threshold:
            return UserDataTier.TIER_4_REGISTERED_MODERATE
        
        if interactions >= self.sparse_interaction_threshold:
            return UserDataTier.TIER_3_REGISTERED_SPARSE
        
        if profile.inventory.demographic_completeness >= self.demographic_completeness_threshold:
            return UserDataTier.TIER_2_REGISTERED_MINIMAL
        
        # Registered but minimal data
        return UserDataTier.TIER_2_REGISTERED_MINIMAL
```

---

## Prior Distribution Models

```python
# =============================================================================
# ADAM Enhancement #13: Prior Distribution Models
# Location: adam/cold_start/models/priors.py
# =============================================================================

"""
Prior distribution models for Bayesian cold start profiling.
"""

from __future__ import annotations
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from pydantic import BaseModel, Field, field_validator, computed_field
import numpy as np

from .enums import (
    PriorSource, PersonalityTrait, ExtendedConstruct,
    CognitiveMechanism, ArchetypeID
)


class BetaDistribution(BaseModel):
    """
    Beta distribution parameters for mechanism effectiveness.
    
    Beta(α, β) is the conjugate prior for Bernoulli likelihood,
    making it ideal for binary outcomes (convert/no-convert).
    """
    alpha: float = Field(ge=0.0, description="Success parameter")
    beta: float = Field(ge=0.0, description="Failure parameter")
    
    @computed_field
    @property
    def mean(self) -> float:
        """Expected value: α / (α + β)"""
        total = self.alpha + self.beta
        if total == 0:
            return 0.5
        return self.alpha / total
    
    @computed_field
    @property
    def variance(self) -> float:
        """Variance: αβ / ((α+β)²(α+β+1))"""
        total = self.alpha + self.beta
        if total == 0:
            return 0.25
        return (self.alpha * self.beta) / (total ** 2 * (total + 1))
    
    @computed_field
    @property
    def samples(self) -> int:
        """Effective sample size (pseudo-observations)."""
        return int(self.alpha + self.beta)
    
    @computed_field
    @property
    def uncertainty(self) -> float:
        """Uncertainty measure (0-1, higher = more uncertain)."""
        # Low sample count = high uncertainty
        return 1.0 / (1.0 + np.sqrt(self.alpha + self.beta))
    
    def sample(self) -> float:
        """Sample from the distribution (Thompson Sampling)."""
        if self.alpha == 0 and self.beta == 0:
            return 0.5
        return np.random.beta(max(0.001, self.alpha), max(0.001, self.beta))
    
    def update(self, success: bool) -> "BetaDistribution":
        """
        Bayesian update with new observation.
        
        Args:
            success: Whether outcome was successful
            
        Returns:
            New BetaDistribution with updated parameters
        """
        if success:
            return BetaDistribution(alpha=self.alpha + 1, beta=self.beta)
        return BetaDistribution(alpha=self.alpha, beta=self.beta + 1)
    
    def blend(
        self, 
        other: "BetaDistribution", 
        weight: float = 0.5
    ) -> "BetaDistribution":
        """
        Blend with another distribution using weighted average.
        
        Args:
            other: Distribution to blend with
            weight: Weight for self (1-weight for other)
            
        Returns:
            Blended BetaDistribution
        """
        return BetaDistribution(
            alpha=self.alpha * weight + other.alpha * (1 - weight),
            beta=self.beta * weight + other.beta * (1 - weight)
        )


class GaussianDistribution(BaseModel):
    """
    Gaussian distribution for continuous traits like personality.
    """
    mean: float = Field(ge=0.0, le=1.0, description="Mean value")
    variance: float = Field(ge=0.0, description="Variance")
    
    @computed_field
    @property
    def std(self) -> float:
        """Standard deviation."""
        return np.sqrt(self.variance)
    
    @computed_field
    @property
    def confidence(self) -> float:
        """Confidence (inverse of uncertainty)."""
        # Lower variance = higher confidence
        return 1.0 / (1.0 + self.variance * 10)
    
    def sample(self) -> float:
        """Sample from distribution, clipped to [0, 1]."""
        sample = np.random.normal(self.mean, self.std)
        return np.clip(sample, 0.0, 1.0)
    
    def update(
        self, 
        observation: float, 
        observation_variance: float = 0.1
    ) -> "GaussianDistribution":
        """
        Bayesian update with new observation.
        
        Uses conjugate normal-normal update.
        """
        # Precision-weighted update
        prior_precision = 1.0 / max(self.variance, 0.001)
        obs_precision = 1.0 / max(observation_variance, 0.001)
        
        posterior_precision = prior_precision + obs_precision
        posterior_mean = (
            prior_precision * self.mean + obs_precision * observation
        ) / posterior_precision
        posterior_variance = 1.0 / posterior_precision
        
        return GaussianDistribution(
            mean=np.clip(posterior_mean, 0.0, 1.0),
            variance=posterior_variance
        )


class TraitPrior(BaseModel):
    """Prior distribution for a single personality trait."""
    trait: PersonalityTrait
    distribution: GaussianDistribution
    source: PriorSource
    confidence: float = Field(ge=0.0, le=1.0)
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    observation_count: int = 0


class MechanismPrior(BaseModel):
    """Prior distribution for mechanism effectiveness."""
    mechanism: CognitiveMechanism
    distribution: BetaDistribution
    source: PriorSource
    archetype_source: Optional[ArchetypeID] = None
    last_updated: datetime = Field(default_factory=datetime.utcnow)


class PsychologicalPrior(BaseModel):
    """
    Complete psychological prior for a user or archetype.
    
    Contains priors for all traits and mechanisms.
    """
    # Big Five trait priors
    trait_priors: Dict[PersonalityTrait, TraitPrior] = Field(
        default_factory=dict
    )
    
    # Extended construct priors
    extended_priors: Dict[ExtendedConstruct, TraitPrior] = Field(
        default_factory=dict
    )
    
    # Mechanism effectiveness priors
    mechanism_priors: Dict[CognitiveMechanism, MechanismPrior] = Field(
        default_factory=dict
    )
    
    # Metadata
    primary_source: PriorSource = PriorSource.POPULATION
    sources_used: List[PriorSource] = Field(default_factory=list)
    overall_confidence: float = 0.0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    def get_trait_mean(self, trait: PersonalityTrait) -> float:
        """Get mean value for a trait."""
        if trait in self.trait_priors:
            return self.trait_priors[trait].distribution.mean
        return 0.5  # Default neutral
    
    def get_mechanism_effectiveness(
        self, 
        mechanism: CognitiveMechanism
    ) -> float:
        """Get expected effectiveness for a mechanism."""
        if mechanism in self.mechanism_priors:
            return self.mechanism_priors[mechanism].distribution.mean
        return 0.5  # Default neutral
    
    def sample_mechanism(
        self, 
        mechanism: CognitiveMechanism
    ) -> float:
        """Thompson sample for mechanism."""
        if mechanism in self.mechanism_priors:
            return self.mechanism_priors[mechanism].distribution.sample()
        return np.random.beta(1, 1)  # Uninformative prior
    
    def to_feature_dict(self) -> Dict[str, float]:
        """Convert to flat feature dictionary for ML models."""
        features = {}
        
        # Trait means
        for trait, prior in self.trait_priors.items():
            features[f"trait_{trait.value}_mean"] = prior.distribution.mean
            features[f"trait_{trait.value}_confidence"] = prior.confidence
        
        # Mechanism effectiveness
        for mech, prior in self.mechanism_priors.items():
            features[f"mechanism_{mech.value}_mean"] = prior.distribution.mean
            features[f"mechanism_{mech.value}_uncertainty"] = prior.distribution.uncertainty
        
        features["overall_confidence"] = self.overall_confidence
        
        return features


class HierarchicalPrior(BaseModel):
    """
    Hierarchical prior combining multiple levels.
    
    Levels (in order of specificity):
    1. Population (least specific)
    2. Cluster
    3. Demographic
    4. Contextual
    5. User historical (most specific, if available)
    """
    population_prior: PsychologicalPrior
    cluster_prior: Optional[PsychologicalPrior] = None
    demographic_prior: Optional[PsychologicalPrior] = None
    contextual_prior: Optional[PsychologicalPrior] = None
    user_prior: Optional[PsychologicalPrior] = None
    
    # Combination weights (learned from data)
    level_weights: Dict[PriorSource, float] = Field(
        default_factory=lambda: {
            PriorSource.POPULATION: 0.1,
            PriorSource.CLUSTER: 0.2,
            PriorSource.DEMOGRAPHIC: 0.25,
            PriorSource.CONTEXTUAL: 0.2,
            PriorSource.HISTORICAL_USER: 0.25
        }
    )
    
    def compute_combined_prior(self) -> PsychologicalPrior:
        """
        Compute combined prior using hierarchical Bayesian combination.
        
        More specific priors receive higher weight when available.
        """
        # Collect available priors with weights
        available = []
        weight_sum = 0.0
        
        if self.population_prior:
            w = self.level_weights[PriorSource.POPULATION]
            available.append((self.population_prior, w))
            weight_sum += w
            
        if self.cluster_prior:
            w = self.level_weights[PriorSource.CLUSTER]
            available.append((self.cluster_prior, w))
            weight_sum += w
            
        if self.demographic_prior:
            w = self.level_weights[PriorSource.DEMOGRAPHIC]
            available.append((self.demographic_prior, w))
            weight_sum += w
            
        if self.contextual_prior:
            w = self.level_weights[PriorSource.CONTEXTUAL]
            available.append((self.contextual_prior, w))
            weight_sum += w
            
        if self.user_prior:
            w = self.level_weights[PriorSource.HISTORICAL_USER]
            available.append((self.user_prior, w))
            weight_sum += w
        
        # Normalize weights
        if weight_sum == 0:
            return self.population_prior or PsychologicalPrior()
        
        # Combine trait priors
        combined_traits: Dict[PersonalityTrait, TraitPrior] = {}
        for trait in PersonalityTrait:
            means = []
            variances = []
            weights = []
            
            for prior, weight in available:
                if trait in prior.trait_priors:
                    tp = prior.trait_priors[trait]
                    means.append(tp.distribution.mean)
                    variances.append(tp.distribution.variance)
                    weights.append(weight / weight_sum)
            
            if means:
                # Precision-weighted combination
                precisions = [1.0 / max(v, 0.001) for v in variances]
                total_precision = sum(p * w for p, w in zip(precisions, weights))
                combined_mean = sum(
                    m * p * w / total_precision 
                    for m, p, w in zip(means, precisions, weights)
                )
                combined_variance = 1.0 / total_precision
                
                combined_traits[trait] = TraitPrior(
                    trait=trait,
                    distribution=GaussianDistribution(
                        mean=np.clip(combined_mean, 0.0, 1.0),
                        variance=combined_variance
                    ),
                    source=PriorSource.CLUSTER,  # Combined
                    confidence=1.0 - np.sqrt(combined_variance)
                )
        
        # Combine mechanism priors
        combined_mechs: Dict[CognitiveMechanism, MechanismPrior] = {}
        for mech in CognitiveMechanism:
            alphas = []
            betas = []
            weights = []
            
            for prior, weight in available:
                if mech in prior.mechanism_priors:
                    mp = prior.mechanism_priors[mech]
                    alphas.append(mp.distribution.alpha)
                    betas.append(mp.distribution.beta)
                    weights.append(weight / weight_sum)
            
            if alphas:
                # Weighted combination of Beta parameters
                combined_alpha = sum(a * w for a, w in zip(alphas, weights))
                combined_beta = sum(b * w for b, w in zip(betas, weights))
                
                combined_mechs[mech] = MechanismPrior(
                    mechanism=mech,
                    distribution=BetaDistribution(
                        alpha=combined_alpha,
                        beta=combined_beta
                    ),
                    source=PriorSource.CLUSTER  # Combined
                )
        
        # Build combined prior
        sources_used = [
            prior.primary_source for prior, _ in available
        ]
        
        overall_confidence = sum(
            prior.overall_confidence * (weight / weight_sum)
            for prior, weight in available
        )
        
        return PsychologicalPrior(
            trait_priors=combined_traits,
            mechanism_priors=combined_mechs,
            primary_source=PriorSource.CLUSTER,
            sources_used=sources_used,
            overall_confidence=overall_confidence
        )
```

---

## Archetype Models

```python
# =============================================================================
# ADAM Enhancement #13: Archetype Models
# Location: adam/cold_start/models/archetypes.py
# =============================================================================

"""
Psychological archetype models for cold start profiling.
"""

from __future__ import annotations
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from pydantic import BaseModel, Field, computed_field
import numpy as np

from .enums import (
    ArchetypeID, PersonalityTrait, CognitiveMechanism, 
    ExtendedConstruct, PriorSource
)
from .priors import (
    BetaDistribution, GaussianDistribution, TraitPrior,
    MechanismPrior, PsychologicalPrior
)


class ArchetypeTraitProfile(BaseModel):
    """
    Big Five trait profile for an archetype.
    
    Based on research literature for personality-behavior correlations.
    """
    openness: GaussianDistribution
    conscientiousness: GaussianDistribution
    extraversion: GaussianDistribution
    agreeableness: GaussianDistribution
    neuroticism: GaussianDistribution
    
    def to_dict(self) -> Dict[PersonalityTrait, GaussianDistribution]:
        """Convert to trait dictionary."""
        return {
            PersonalityTrait.OPENNESS: self.openness,
            PersonalityTrait.CONSCIENTIOUSNESS: self.conscientiousness,
            PersonalityTrait.EXTRAVERSION: self.extraversion,
            PersonalityTrait.AGREEABLENESS: self.agreeableness,
            PersonalityTrait.NEUROTICISM: self.neuroticism,
        }
    
    def similarity_to(
        self, 
        trait_values: Dict[PersonalityTrait, float]
    ) -> float:
        """
        Compute similarity to observed trait values.
        
        Uses Mahalanobis-like distance normalized to [0, 1].
        """
        profile_dict = self.to_dict()
        
        squared_distances = []
        for trait, dist in profile_dict.items():
            if trait in trait_values:
                diff = trait_values[trait] - dist.mean
                # Normalize by variance
                squared_dist = (diff ** 2) / max(dist.variance, 0.01)
                squared_distances.append(squared_dist)
        
        if not squared_distances:
            return 0.5  # No data
        
        # Convert distance to similarity
        mean_squared_dist = np.mean(squared_distances)
        similarity = np.exp(-mean_squared_dist / 2)
        
        return float(similarity)


class ArchetypeMechanismProfile(BaseModel):
    """
    Mechanism effectiveness profile for an archetype.
    
    Each mechanism has a Beta prior representing expected effectiveness.
    """
    mechanism_priors: Dict[CognitiveMechanism, BetaDistribution] = Field(
        default_factory=dict
    )
    
    def get_effectiveness(self, mechanism: CognitiveMechanism) -> float:
        """Get expected effectiveness for mechanism."""
        if mechanism in self.mechanism_priors:
            return self.mechanism_priors[mechanism].mean
        return 0.5
    
    def sample_effectiveness(self, mechanism: CognitiveMechanism) -> float:
        """Thompson sample for mechanism."""
        if mechanism in self.mechanism_priors:
            return self.mechanism_priors[mechanism].sample()
        return np.random.beta(1, 1)
    
    def get_top_mechanisms(self, n: int = 3) -> List[Tuple[CognitiveMechanism, float]]:
        """Get top N most effective mechanisms."""
        effectiveness = [
            (mech, prior.mean)
            for mech, prior in self.mechanism_priors.items()
        ]
        effectiveness.sort(key=lambda x: x[1], reverse=True)
        return effectiveness[:n]


class ArchetypeDefinition(BaseModel):
    """
    Complete definition of a psychological archetype.
    
    Based on Jung's psychological types, validated through
    Big Five research and advertising response studies.
    """
    archetype_id: ArchetypeID
    name: str
    description: str
    
    # Trait profile
    trait_profile: ArchetypeTraitProfile
    
    # Extended constructs
    regulatory_focus_promotion: float = Field(ge=0.0, le=1.0, default=0.5)
    regulatory_focus_prevention: float = Field(ge=0.0, le=1.0, default=0.5)
    need_for_cognition: float = Field(ge=0.0, le=1.0, default=0.5)
    construal_level_abstract: float = Field(ge=0.0, le=1.0, default=0.5)
    
    # Mechanism effectiveness
    mechanism_profile: ArchetypeMechanismProfile
    
    # Message preferences
    preferred_message_frames: List[str] = Field(default_factory=list)
    avoided_message_frames: List[str] = Field(default_factory=list)
    
    # Performance tracking
    total_assignments: int = 0
    total_conversions: int = 0
    conversion_rate: float = 0.0
    
    # Metadata
    research_basis: str = ""
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    
    @computed_field
    @property
    def dominant_regulatory_focus(self) -> str:
        """Get dominant regulatory focus."""
        if self.regulatory_focus_promotion > self.regulatory_focus_prevention:
            return "promotion"
        return "prevention"
    
    def to_psychological_prior(self) -> PsychologicalPrior:
        """Convert archetype to psychological prior."""
        # Build trait priors
        trait_priors = {}
        for trait, dist in self.trait_profile.to_dict().items():
            trait_priors[trait] = TraitPrior(
                trait=trait,
                distribution=dist,
                source=PriorSource.ARCHETYPE,
                confidence=1.0 - dist.variance
            )
        
        # Build mechanism priors
        mechanism_priors = {}
        for mech, dist in self.mechanism_profile.mechanism_priors.items():
            mechanism_priors[mech] = MechanismPrior(
                mechanism=mech,
                distribution=dist,
                source=PriorSource.ARCHETYPE,
                archetype_source=self.archetype_id
            )
        
        return PsychologicalPrior(
            trait_priors=trait_priors,
            mechanism_priors=mechanism_priors,
            primary_source=PriorSource.ARCHETYPE,
            sources_used=[PriorSource.ARCHETYPE],
            overall_confidence=0.4  # Archetype is moderate confidence
        )


class ArchetypeMatchResult(BaseModel):
    """Result of archetype matching."""
    matched_archetype: ArchetypeID
    confidence: float = Field(ge=0.0, le=1.0)
    
    # All archetype scores
    archetype_scores: Dict[ArchetypeID, float] = Field(default_factory=dict)
    
    # Matching method used
    matching_method: str = "trait_similarity"
    
    # Evidence used
    trait_evidence: Dict[PersonalityTrait, float] = Field(default_factory=dict)
    behavioral_evidence: List[str] = Field(default_factory=list)
    contextual_evidence: List[str] = Field(default_factory=list)
    
    @computed_field
    @property
    def second_best_archetype(self) -> Optional[ArchetypeID]:
        """Get second-best matching archetype."""
        sorted_scores = sorted(
            self.archetype_scores.items(), 
            key=lambda x: x[1], 
            reverse=True
        )
        if len(sorted_scores) >= 2:
            return sorted_scores[1][0]
        return None
    
    @computed_field
    @property
    def match_clarity(self) -> float:
        """
        How clearly the top archetype wins.
        High clarity = confident match, low clarity = could be multiple.
        """
        if len(self.archetype_scores) < 2:
            return 1.0
        
        sorted_scores = sorted(
            self.archetype_scores.values(), 
            reverse=True
        )
        if sorted_scores[0] == 0:
            return 0.0
        
        # Ratio of best to second-best
        clarity = 1.0 - (sorted_scores[1] / sorted_scores[0])
        return max(0.0, min(1.0, clarity))
```

---

## Decision Output Models

```python
# =============================================================================
# ADAM Enhancement #13: Decision Output Models
# Location: adam/cold_start/models/decisions.py
# =============================================================================

"""
Cold start decision output models.
"""

from __future__ import annotations
from datetime import datetime
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, computed_field

from .enums import (
    UserDataTier, ColdStartStrategy, ArchetypeID,
    CognitiveMechanism, PriorSource, PersonalityTrait
)
from .priors import PsychologicalPrior


class ColdStartDecision(BaseModel):
    """
    Output of cold start strategy selection.
    
    Contains the inferred psychological profile and recommendations
    for downstream components.
    """
    # Request identification
    request_id: str
    user_id: Optional[str] = None
    session_id: str
    
    # User classification
    data_tier: UserDataTier
    strategy_applied: ColdStartStrategy
    
    # Archetype assignment (if applicable)
    assigned_archetype: Optional[ArchetypeID] = None
    archetype_confidence: float = 0.0
    
    # Inferred psychological profile
    inferred_prior: PsychologicalPrior
    
    # Profile quality metrics
    overall_confidence: float = Field(ge=0.0, le=1.0)
    trait_confidences: Dict[PersonalityTrait, float] = Field(default_factory=dict)
    mechanism_uncertainties: Dict[CognitiveMechanism, float] = Field(default_factory=dict)
    
    # Exploration recommendations
    exploration_rate: float = Field(ge=0.0, le=1.0, default=0.5)
    exploration_focus: Optional[CognitiveMechanism] = None
    next_best_action: str = "observe_interaction"
    
    # Prior sources used
    sources_used: List[PriorSource] = Field(default_factory=list)
    
    # Performance tracking
    latency_ms: float = 0.0
    cache_hit: bool = False
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    @computed_field
    @property
    def is_cold(self) -> bool:
        """Whether this is a cold start (not full profile)."""
        return self.data_tier != UserDataTier.TIER_5_PROFILED_FULL
    
    @computed_field
    @property
    def most_uncertain_mechanism(self) -> Optional[CognitiveMechanism]:
        """Get mechanism with highest uncertainty."""
        if not self.mechanism_uncertainties:
            return None
        return max(
            self.mechanism_uncertainties.items(),
            key=lambda x: x[1]
        )[0]
    
    def to_atom_context(self) -> Dict[str, Any]:
        """
        Convert to context for Atom of Thought atoms.
        
        This is injected into atom prompts for prior-informed reasoning.
        """
        return {
            "data_tier": self.data_tier.value,
            "is_cold_start": self.is_cold,
            "assigned_archetype": (
                self.assigned_archetype.value if self.assigned_archetype else None
            ),
            "archetype_confidence": self.archetype_confidence,
            "overall_confidence": self.overall_confidence,
            "exploration_rate": self.exploration_rate,
            "trait_means": {
                trait.value: self.inferred_prior.get_trait_mean(trait)
                for trait in PersonalityTrait
            },
            "mechanism_effectiveness": {
                mech.value: self.inferred_prior.get_mechanism_effectiveness(mech)
                for mech in CognitiveMechanism
            },
            "most_uncertain_mechanism": (
                self.most_uncertain_mechanism.value 
                if self.most_uncertain_mechanism else None
            ),
            "sources_used": [s.value for s in self.sources_used]
        }


class TierTransitionEvent(BaseModel):
    """
    Event emitted when user transitions between data tiers.
    
    Consumed by Gradient Bridge for learning signal propagation.
    """
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    session_id: str
    
    # Transition details
    previous_tier: UserDataTier
    new_tier: UserDataTier
    
    # What triggered the transition
    trigger_interaction_count: int
    trigger_confidence: float
    
    # Profile state at transition
    profile_at_transition: PsychologicalPrior
    
    # Timestamps
    transition_time: datetime = Field(default_factory=datetime.utcnow)
    time_in_previous_tier_hours: float = 0.0
    
    @computed_field
    @property
    def is_upgrade(self) -> bool:
        """Whether this is an upgrade (more data available)."""
        tier_order = [
            UserDataTier.TIER_0_ANONYMOUS_NEW,
            UserDataTier.TIER_1_ANONYMOUS_SESSION,
            UserDataTier.TIER_2_REGISTERED_MINIMAL,
            UserDataTier.TIER_3_REGISTERED_SPARSE,
            UserDataTier.TIER_4_REGISTERED_MODERATE,
            UserDataTier.TIER_5_PROFILED_FULL,
        ]
        return tier_order.index(self.new_tier) > tier_order.index(self.previous_tier)


class ProfileVelocityMetrics(BaseModel):
    """Metrics for tracking profile development velocity."""
    user_id: str
    
    # Interaction metrics
    interactions_today: int = 0
    interactions_this_week: int = 0
    interactions_total: int = 0
    
    # Confidence progression
    confidence_when_first_seen: float = 0.0
    confidence_current: float = 0.0
    confidence_delta_per_day: float = 0.0
    
    # Information gain
    total_information_gain: float = 0.0
    information_gain_per_interaction: float = 0.0
    
    # Projections
    estimated_days_to_full_profile: Optional[int] = None
    estimated_tier_at_day_30: UserDataTier = UserDataTier.TIER_0_ANONYMOUS_NEW
    
    # Timestamps
    first_seen_at: datetime
    last_interaction_at: datetime
    metrics_updated_at: datetime = Field(default_factory=datetime.utcnow)


# Import uuid for event_id generation
import uuid
```

---

# SECTION C: HIERARCHICAL PRIOR SYSTEM

## Population Priors

```python
# =============================================================================
# ADAM Enhancement #13: Population Priors
# Location: adam/cold_start/priors/population.py
# =============================================================================

"""
Population-level priors derived from Amazon corpus and research literature.

These are the most general priors, used when no other information is available.
"""

from __future__ import annotations
from typing import Dict, Optional
from pydantic import BaseModel, Field
import numpy as np

from adam.cold_start.models.enums import (
    PersonalityTrait, CognitiveMechanism, ExtendedConstruct, PriorSource
)
from adam.cold_start.models.priors import (
    BetaDistribution, GaussianDistribution, TraitPrior, MechanismPrior,
    PsychologicalPrior
)


class PopulationPriorConfig(BaseModel):
    """Configuration for population prior computation."""
    
    # Source weights
    amazon_corpus_weight: float = 0.6
    research_literature_weight: float = 0.3
    category_norms_weight: float = 0.1
    
    # Default uncertainty
    default_trait_variance: float = 0.04  # Moderately uncertain
    default_mechanism_pseudocounts: float = 5.0  # Weak prior


# =============================================================================
# POPULATION TRAIT PRIORS
# =============================================================================

# Research-based Big Five population means and variances
# Source: Costa & McCrae meta-analyses, Amazon corpus validation
POPULATION_TRAIT_PRIORS: Dict[PersonalityTrait, GaussianDistribution] = {
    PersonalityTrait.OPENNESS: GaussianDistribution(
        mean=0.55,  # Slightly above neutral (Amazon skews creative)
        variance=0.04
    ),
    PersonalityTrait.CONSCIENTIOUSNESS: GaussianDistribution(
        mean=0.52,
        variance=0.04
    ),
    PersonalityTrait.EXTRAVERSION: GaussianDistribution(
        mean=0.48,  # Slightly below (reviewers skew introverted)
        variance=0.05
    ),
    PersonalityTrait.AGREEABLENESS: GaussianDistribution(
        mean=0.56,  # Reviewers tend agreeable
        variance=0.04
    ),
    PersonalityTrait.NEUROTICISM: GaussianDistribution(
        mean=0.45,  # Below neutral
        variance=0.05
    ),
}


# =============================================================================
# POPULATION MECHANISM PRIORS
# =============================================================================

# Base rates for mechanism effectiveness from research + Amazon validation
# Alpha/Beta tuned to reflect population-level conversion rates
POPULATION_MECHANISM_PRIORS: Dict[CognitiveMechanism, BetaDistribution] = {
    CognitiveMechanism.CONSTRUAL_LEVEL: BetaDistribution(
        alpha=2.5, beta=2.5  # Neutral - varies widely by context
    ),
    CognitiveMechanism.REGULATORY_FOCUS: BetaDistribution(
        alpha=3.0, beta=2.0  # Generally effective
    ),
    CognitiveMechanism.AUTOMATIC_EVALUATION: BetaDistribution(
        alpha=3.5, beta=1.5  # Strong - emotional appeals work
    ),
    CognitiveMechanism.WANTING_LIKING: BetaDistribution(
        alpha=3.0, beta=2.0  # Effective for hedonic products
    ),
    CognitiveMechanism.MIMETIC_DESIRE: BetaDistribution(
        alpha=3.5, beta=2.0  # Social proof is powerful
    ),
    CognitiveMechanism.ATTENTION_DYNAMICS: BetaDistribution(
        alpha=2.5, beta=2.5  # Neutral - context dependent
    ),
    CognitiveMechanism.TEMPORAL_CONSTRUAL: BetaDistribution(
        alpha=2.0, beta=3.0  # Slightly weak - future discounting
    ),
    CognitiveMechanism.IDENTITY_CONSTRUCTION: BetaDistribution(
        alpha=3.0, beta=2.0  # Effective for lifestyle products
    ),
    CognitiveMechanism.EVOLUTIONARY_MOTIVE: BetaDistribution(
        alpha=2.5, beta=2.5  # Neutral - product dependent
    ),
}


class PopulationPriorEngine:
    """
    Engine for computing population-level priors.
    
    These are used as the base layer in the hierarchical prior system.
    """
    
    def __init__(self, config: Optional[PopulationPriorConfig] = None):
        self.config = config or PopulationPriorConfig()
        
        # Cache the population prior
        self._cached_prior: Optional[PsychologicalPrior] = None
    
    def get_population_prior(self) -> PsychologicalPrior:
        """
        Get the global population prior.
        
        Returns cached version if available.
        """
        if self._cached_prior is not None:
            return self._cached_prior
        
        # Build trait priors
        trait_priors = {}
        for trait, dist in POPULATION_TRAIT_PRIORS.items():
            trait_priors[trait] = TraitPrior(
                trait=trait,
                distribution=dist,
                source=PriorSource.POPULATION,
                confidence=1.0 - dist.variance * 10  # Lower variance = higher confidence
            )
        
        # Build mechanism priors
        mechanism_priors = {}
        for mech, dist in POPULATION_MECHANISM_PRIORS.items():
            mechanism_priors[mech] = MechanismPrior(
                mechanism=mech,
                distribution=dist,
                source=PriorSource.POPULATION
            )
        
        self._cached_prior = PsychologicalPrior(
            trait_priors=trait_priors,
            mechanism_priors=mechanism_priors,
            primary_source=PriorSource.POPULATION,
            sources_used=[PriorSource.POPULATION],
            overall_confidence=0.2  # Population is low confidence
        )
        
        return self._cached_prior
    
    def get_trait_prior(self, trait: PersonalityTrait) -> GaussianDistribution:
        """Get population prior for specific trait."""
        return POPULATION_TRAIT_PRIORS.get(
            trait,
            GaussianDistribution(mean=0.5, variance=0.0625)  # Uninformative
        )
    
    def get_mechanism_prior(self, mechanism: CognitiveMechanism) -> BetaDistribution:
        """Get population prior for specific mechanism."""
        return POPULATION_MECHANISM_PRIORS.get(
            mechanism,
            BetaDistribution(alpha=1.0, beta=1.0)  # Uninformative
        )
    
    def update_from_corpus(
        self,
        trait_means: Dict[PersonalityTrait, float],
        trait_variances: Dict[PersonalityTrait, float],
        mechanism_rates: Dict[CognitiveMechanism, float],
        mechanism_counts: Dict[CognitiveMechanism, int]
    ) -> None:
        """
        Update population priors from corpus analysis.
        
        Called during batch recomputation.
        """
        # Update trait priors
        for trait, mean in trait_means.items():
            variance = trait_variances.get(trait, 0.04)
            POPULATION_TRAIT_PRIORS[trait] = GaussianDistribution(
                mean=np.clip(mean, 0.0, 1.0),
                variance=variance
            )
        
        # Update mechanism priors
        for mech, rate in mechanism_rates.items():
            count = mechanism_counts.get(mech, 10)
            # Convert rate to Beta parameters
            alpha = rate * count
            beta = (1 - rate) * count
            POPULATION_MECHANISM_PRIORS[mech] = BetaDistribution(
                alpha=max(1.0, alpha),
                beta=max(1.0, beta)
            )
        
        # Invalidate cache
        self._cached_prior = None
```

---

## Cluster Priors

```python
# =============================================================================
# ADAM Enhancement #13: Cluster Priors
# Location: adam/cold_start/priors/cluster.py
# =============================================================================

"""
Psychological cluster priors for transfer learning.

Users are assigned to psychological clusters based on behavioral patterns.
New users in the same cluster inherit cluster priors.
"""

from __future__ import annotations
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from pydantic import BaseModel, Field
import numpy as np

from adam.cold_start.models.enums import (
    PersonalityTrait, CognitiveMechanism, PriorSource
)
from adam.cold_start.models.priors import (
    BetaDistribution, GaussianDistribution, TraitPrior, MechanismPrior,
    PsychologicalPrior
)


class ClusterDefinition(BaseModel):
    """
    Definition of a psychological cluster.
    
    Clusters are created via unsupervised learning on user behaviors
    and validated through outcome correlation.
    """
    cluster_id: int
    name: str
    description: str
    
    # Cluster centroid (Big Five means)
    centroid_openness: float
    centroid_conscientiousness: float
    centroid_extraversion: float
    centroid_agreeableness: float
    centroid_neuroticism: float
    
    # Cluster spread (variances)
    variance_openness: float = 0.02
    variance_conscientiousness: float = 0.02
    variance_extraversion: float = 0.02
    variance_agreeableness: float = 0.02
    variance_neuroticism: float = 0.02
    
    # Mechanism effectiveness priors (learned from cluster members)
    mechanism_alphas: Dict[str, float] = Field(default_factory=dict)
    mechanism_betas: Dict[str, float] = Field(default_factory=dict)
    
    # Cluster statistics
    member_count: int = 0
    conversion_rate: float = 0.0
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    
    def get_trait_prior(self, trait: PersonalityTrait) -> GaussianDistribution:
        """Get trait prior for this cluster."""
        trait_map = {
            PersonalityTrait.OPENNESS: (self.centroid_openness, self.variance_openness),
            PersonalityTrait.CONSCIENTIOUSNESS: (self.centroid_conscientiousness, self.variance_conscientiousness),
            PersonalityTrait.EXTRAVERSION: (self.centroid_extraversion, self.variance_extraversion),
            PersonalityTrait.AGREEABLENESS: (self.centroid_agreeableness, self.variance_agreeableness),
            PersonalityTrait.NEUROTICISM: (self.centroid_neuroticism, self.variance_neuroticism),
        }
        mean, var = trait_map.get(trait, (0.5, 0.04))
        return GaussianDistribution(mean=mean, variance=var)
    
    def get_mechanism_prior(self, mechanism: CognitiveMechanism) -> BetaDistribution:
        """Get mechanism prior for this cluster."""
        mech_name = mechanism.value
        alpha = self.mechanism_alphas.get(mech_name, 2.0)
        beta = self.mechanism_betas.get(mech_name, 2.0)
        return BetaDistribution(alpha=alpha, beta=beta)
    
    def to_psychological_prior(self) -> PsychologicalPrior:
        """Convert cluster to psychological prior."""
        trait_priors = {}
        for trait in PersonalityTrait:
            dist = self.get_trait_prior(trait)
            trait_priors[trait] = TraitPrior(
                trait=trait,
                distribution=dist,
                source=PriorSource.CLUSTER,
                confidence=1.0 - dist.variance * 10
            )
        
        mechanism_priors = {}
        for mech in CognitiveMechanism:
            dist = self.get_mechanism_prior(mech)
            mechanism_priors[mech] = MechanismPrior(
                mechanism=mech,
                distribution=dist,
                source=PriorSource.CLUSTER
            )
        
        return PsychologicalPrior(
            trait_priors=trait_priors,
            mechanism_priors=mechanism_priors,
            primary_source=PriorSource.CLUSTER,
            sources_used=[PriorSource.CLUSTER],
            overall_confidence=0.35  # Cluster is moderate confidence
        )


class ClusterPriorEngine:
    """
    Engine for cluster-based prior transfer learning.
    
    Assigns users to clusters and provides cluster priors.
    """
    
    def __init__(self, neo4j_driver):
        self.driver = neo4j_driver
        self._cluster_cache: Dict[int, ClusterDefinition] = {}
    
    async def get_cluster_for_user(
        self,
        user_id: str,
        trait_estimates: Optional[Dict[PersonalityTrait, float]] = None
    ) -> Optional[int]:
        """
        Get cluster assignment for user.
        
        If user has cluster assignment, return it.
        If not, estimate based on available trait data.
        """
        # Check for existing assignment
        query = """
        MATCH (u:User {user_id: $user_id})-[:BELONGS_TO]->(c:PsychologicalCluster)
        RETURN c.cluster_id as cluster_id
        """
        async with self.driver.session() as session:
            result = await session.run(query, user_id=user_id)
            record = await result.single()
            if record:
                return record["cluster_id"]
        
        # Estimate cluster from traits if available
        if trait_estimates:
            return await self._assign_cluster_from_traits(trait_estimates)
        
        return None
    
    async def _assign_cluster_from_traits(
        self,
        traits: Dict[PersonalityTrait, float]
    ) -> Optional[int]:
        """Assign to nearest cluster based on trait estimates."""
        clusters = await self._get_all_clusters()
        if not clusters:
            return None
        
        best_cluster = None
        best_distance = float('inf')
        
        for cluster in clusters:
            distance = self._compute_distance(traits, cluster)
            if distance < best_distance:
                best_distance = distance
                best_cluster = cluster.cluster_id
        
        return best_cluster
    
    def _compute_distance(
        self,
        traits: Dict[PersonalityTrait, float],
        cluster: ClusterDefinition
    ) -> float:
        """Compute Mahalanobis distance to cluster centroid."""
        distances = []
        
        for trait, value in traits.items():
            dist = cluster.get_trait_prior(trait)
            diff = value - dist.mean
            var = max(dist.variance, 0.001)
            distances.append((diff ** 2) / var)
        
        return np.mean(distances) if distances else float('inf')
    
    async def get_cluster_prior(self, cluster_id: int) -> Optional[PsychologicalPrior]:
        """Get psychological prior for a cluster."""
        cluster = await self._get_cluster(cluster_id)
        if cluster:
            return cluster.to_psychological_prior()
        return None
    
    async def _get_cluster(self, cluster_id: int) -> Optional[ClusterDefinition]:
        """Get cluster definition from cache or database."""
        if cluster_id in self._cluster_cache:
            return self._cluster_cache[cluster_id]
        
        query = """
        MATCH (c:PsychologicalCluster {cluster_id: $cluster_id})
        RETURN c
        """
        async with self.driver.session() as session:
            result = await session.run(query, cluster_id=cluster_id)
            record = await result.single()
            if record:
                data = dict(record["c"])
                cluster = ClusterDefinition(**data)
                self._cluster_cache[cluster_id] = cluster
                return cluster
        
        return None
    
    async def _get_all_clusters(self) -> List[ClusterDefinition]:
        """Get all cluster definitions."""
        query = """
        MATCH (c:PsychologicalCluster)
        RETURN c
        """
        clusters = []
        async with self.driver.session() as session:
            result = await session.run(query)
            async for record in result:
                data = dict(record["c"])
                cluster = ClusterDefinition(**data)
                clusters.append(cluster)
                self._cluster_cache[cluster.cluster_id] = cluster
        
        return clusters
    
    async def update_cluster_priors(
        self,
        cluster_id: int,
        mechanism: CognitiveMechanism,
        success: bool
    ) -> None:
        """
        Update cluster priors with new outcome observation.
        
        Called by Gradient Bridge on outcome.
        """
        query = """
        MATCH (c:PsychologicalCluster {cluster_id: $cluster_id})
        SET c.mechanism_alphas[$mechanism] = 
            COALESCE(c.mechanism_alphas[$mechanism], 2.0) + $alpha_delta,
            c.mechanism_betas[$mechanism] = 
            COALESCE(c.mechanism_betas[$mechanism], 2.0) + $beta_delta,
            c.last_updated = datetime()
        """
        alpha_delta = 1.0 if success else 0.0
        beta_delta = 0.0 if success else 1.0
        
        async with self.driver.session() as session:
            await session.run(
                query,
                cluster_id=cluster_id,
                mechanism=mechanism.value,
                alpha_delta=alpha_delta,
                beta_delta=beta_delta
            )
        
        # Invalidate cache
        if cluster_id in self._cluster_cache:
            del self._cluster_cache[cluster_id]
```

I'll continue building out the remaining sections of the specification. Let me add the Demographic Priors, Contextual Priors, and the complete prior hierarchy engine:

```python
# =============================================================================
# ADAM Enhancement #13: Demographic Priors
# Location: adam/cold_start/priors/demographic.py
# =============================================================================

"""
Demographic-conditioned priors.

These priors adjust population baselines based on demographic factors
like age, gender, location, education, and income.
"""

from __future__ import annotations
from typing import Dict, Optional, Tuple
from pydantic import BaseModel, Field
import numpy as np

from adam.cold_start.models.enums import (
    PersonalityTrait, CognitiveMechanism, PriorSource
)
from adam.cold_start.models.priors import (
    BetaDistribution, GaussianDistribution, TraitPrior, MechanismPrior,
    PsychologicalPrior
)


# =============================================================================
# DEMOGRAPHIC ADJUSTMENT TABLES
# =============================================================================

# Age-based trait adjustments (deviations from population mean)
# Source: Costa & McCrae lifespan development research
AGE_TRAIT_ADJUSTMENTS: Dict[str, Dict[PersonalityTrait, float]] = {
    "18-24": {
        PersonalityTrait.OPENNESS: +0.08,
        PersonalityTrait.CONSCIENTIOUSNESS: -0.06,
        PersonalityTrait.EXTRAVERSION: +0.04,
        PersonalityTrait.AGREEABLENESS: -0.04,
        PersonalityTrait.NEUROTICISM: +0.06,
    },
    "25-34": {
        PersonalityTrait.OPENNESS: +0.04,
        PersonalityTrait.CONSCIENTIOUSNESS: +0.02,
        PersonalityTrait.EXTRAVERSION: +0.02,
        PersonalityTrait.AGREEABLENESS: +0.00,
        PersonalityTrait.NEUROTICISM: +0.02,
    },
    "35-44": {
        PersonalityTrait.OPENNESS: +0.00,
        PersonalityTrait.CONSCIENTIOUSNESS: +0.04,
        PersonalityTrait.EXTRAVERSION: -0.02,
        PersonalityTrait.AGREEABLENESS: +0.02,
        PersonalityTrait.NEUROTICISM: -0.02,
    },
    "45-54": {
        PersonalityTrait.OPENNESS: -0.02,
        PersonalityTrait.CONSCIENTIOUSNESS: +0.04,
        PersonalityTrait.EXTRAVERSION: -0.04,
        PersonalityTrait.AGREEABLENESS: +0.04,
        PersonalityTrait.NEUROTICISM: -0.04,
    },
    "55-64": {
        PersonalityTrait.OPENNESS: -0.04,
        PersonalityTrait.CONSCIENTIOUSNESS: +0.02,
        PersonalityTrait.EXTRAVERSION: -0.06,
        PersonalityTrait.AGREEABLENESS: +0.06,
        PersonalityTrait.NEUROTICISM: -0.06,
    },
    "65+": {
        PersonalityTrait.OPENNESS: -0.06,
        PersonalityTrait.CONSCIENTIOUSNESS: +0.00,
        PersonalityTrait.EXTRAVERSION: -0.08,
        PersonalityTrait.AGREEABLENESS: +0.08,
        PersonalityTrait.NEUROTICISM: -0.08,
    },
}

# Gender-based trait adjustments
# Source: Schmitt et al. cross-cultural personality research
GENDER_TRAIT_ADJUSTMENTS: Dict[str, Dict[PersonalityTrait, float]] = {
    "male": {
        PersonalityTrait.OPENNESS: +0.02,
        PersonalityTrait.CONSCIENTIOUSNESS: -0.02,
        PersonalityTrait.EXTRAVERSION: +0.00,
        PersonalityTrait.AGREEABLENESS: -0.06,
        PersonalityTrait.NEUROTICISM: -0.06,
    },
    "female": {
        PersonalityTrait.OPENNESS: -0.02,
        PersonalityTrait.CONSCIENTIOUSNESS: +0.02,
        PersonalityTrait.EXTRAVERSION: +0.00,
        PersonalityTrait.AGREEABLENESS: +0.06,
        PersonalityTrait.NEUROTICISM: +0.06,
    },
}

# Age-based mechanism effectiveness adjustments
AGE_MECHANISM_ADJUSTMENTS: Dict[str, Dict[CognitiveMechanism, Tuple[float, float]]] = {
    # (alpha_mult, beta_mult) - multipliers for base prior
    "18-24": {
        CognitiveMechanism.MIMETIC_DESIRE: (1.3, 0.8),  # Social proof stronger
        CognitiveMechanism.IDENTITY_CONSTRUCTION: (1.2, 0.9),
        CognitiveMechanism.TEMPORAL_CONSTRUAL: (0.8, 1.2),  # Future focus weaker
    },
    "25-34": {
        CognitiveMechanism.REGULATORY_FOCUS: (1.2, 0.9),
        CognitiveMechanism.IDENTITY_CONSTRUCTION: (1.2, 0.9),
    },
    "35-44": {
        CognitiveMechanism.REGULATORY_FOCUS: (1.3, 0.8),  # Peak career focus
        CognitiveMechanism.AUTOMATIC_EVALUATION: (1.1, 0.9),
    },
    "45-54": {
        CognitiveMechanism.WANTING_LIKING: (1.2, 0.9),
        CognitiveMechanism.EVOLUTIONARY_MOTIVE: (0.9, 1.1),
    },
    "55-64": {
        CognitiveMechanism.TEMPORAL_CONSTRUAL: (1.2, 0.9),  # Future planning
        CognitiveMechanism.MIMETIC_DESIRE: (0.8, 1.2),  # Less social influence
    },
    "65+": {
        CognitiveMechanism.AUTOMATIC_EVALUATION: (1.2, 0.9),  # Rely on gut
        CognitiveMechanism.ATTENTION_DYNAMICS: (0.9, 1.1),  # Selective attention
    },
}


class DemographicPriorEngine:
    """
    Engine for computing demographic-conditioned priors.
    
    Adjusts population priors based on demographic factors.
    """
    
    def __init__(
        self,
        population_engine: 'PopulationPriorEngine'
    ):
        self.population_engine = population_engine
    
    def get_demographic_prior(
        self,
        age_bracket: Optional[str] = None,
        gender: Optional[str] = None,
        country: Optional[str] = None,
        income_bracket: Optional[str] = None,
        education_level: Optional[str] = None
    ) -> PsychologicalPrior:
        """
        Get demographic-adjusted prior.
        
        Starts from population prior and applies demographic adjustments.
        """
        base_prior = self.population_engine.get_population_prior()
        
        # Collect adjustments
        trait_adjustments: Dict[PersonalityTrait, float] = {
            t: 0.0 for t in PersonalityTrait
        }
        mechanism_adjustments: Dict[CognitiveMechanism, Tuple[float, float]] = {}
        
        # Apply age adjustments
        if age_bracket and age_bracket in AGE_TRAIT_ADJUSTMENTS:
            for trait, adj in AGE_TRAIT_ADJUSTMENTS[age_bracket].items():
                trait_adjustments[trait] += adj
            
            if age_bracket in AGE_MECHANISM_ADJUSTMENTS:
                for mech, mult in AGE_MECHANISM_ADJUSTMENTS[age_bracket].items():
                    mechanism_adjustments[mech] = mult
        
        # Apply gender adjustments
        if gender and gender.lower() in GENDER_TRAIT_ADJUSTMENTS:
            for trait, adj in GENDER_TRAIT_ADJUSTMENTS[gender.lower()].items():
                trait_adjustments[trait] += adj
        
        # Build adjusted priors
        adjusted_trait_priors = {}
        for trait in PersonalityTrait:
            base_dist = base_prior.trait_priors[trait].distribution
            adj = trait_adjustments[trait]
            
            adjusted_trait_priors[trait] = TraitPrior(
                trait=trait,
                distribution=GaussianDistribution(
                    mean=np.clip(base_dist.mean + adj, 0.0, 1.0),
                    variance=base_dist.variance * 0.9  # Slightly more confident
                ),
                source=PriorSource.DEMOGRAPHIC,
                confidence=base_prior.trait_priors[trait].confidence * 1.1
            )
        
        adjusted_mech_priors = {}
        for mech in CognitiveMechanism:
            base_dist = base_prior.mechanism_priors[mech].distribution
            
            if mech in mechanism_adjustments:
                alpha_mult, beta_mult = mechanism_adjustments[mech]
                adjusted_mech_priors[mech] = MechanismPrior(
                    mechanism=mech,
                    distribution=BetaDistribution(
                        alpha=base_dist.alpha * alpha_mult,
                        beta=base_dist.beta * beta_mult
                    ),
                    source=PriorSource.DEMOGRAPHIC
                )
            else:
                adjusted_mech_priors[mech] = MechanismPrior(
                    mechanism=mech,
                    distribution=base_dist,
                    source=PriorSource.DEMOGRAPHIC
                )
        
        # Calculate confidence based on how much demographic info we have
        demo_completeness = sum([
            1 if age_bracket else 0,
            1 if gender else 0,
            1 if country else 0,
            1 if income_bracket else 0,
            1 if education_level else 0
        ]) / 5.0
        
        return PsychologicalPrior(
            trait_priors=adjusted_trait_priors,
            mechanism_priors=adjusted_mech_priors,
            primary_source=PriorSource.DEMOGRAPHIC,
            sources_used=[PriorSource.POPULATION, PriorSource.DEMOGRAPHIC],
            overall_confidence=0.25 + demo_completeness * 0.15
        )
```

Now let me continue with the complete specification. Due to the length, I'll create Part 2:
