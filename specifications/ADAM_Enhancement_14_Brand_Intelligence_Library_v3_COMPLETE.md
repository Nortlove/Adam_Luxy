# ADAM Enhancement #14: Brand Intelligence Library
## Enterprise-Grade Psychological Brand Profiling with Cross-Component Learning

**Version**: 3.0 COMPLETE  
**Date**: January 2026  
**Priority**: P1 - Critical Integration Hub  
**Estimated Implementation**: 12 person-weeks  
**Dependencies**: #06 (Gradient Bridge), #13 (Cold Start), #21 (Embeddings), #29 (Platform Infrastructure), #30 (Feature Store), #31 (Event Bus & Cache)  
**Dependents**: #15 (Copy Generation), #18 (Explanation), #28 (WPP Ad Desk)  
**File Size**: ~170KB (Enterprise Production-Ready)

---

## Table of Contents

### SECTION A: STRATEGIC OVERVIEW
1. [Executive Summary](#1-executive-summary)
2. [The Brand Cold Start Problem](#2-the-brand-cold-start-problem)
3. [Architecture Overview](#3-architecture-overview)
4. [Cross-Component Learning Flow](#4-cross-component-learning-flow)
5. [Research Foundations](#5-research-foundations)

### SECTION B: CORE DATA MODELS
6. [Configuration Models](#6-configuration-models)
7. [Brand Profile Models](#7-brand-profile-models)
8. [Customer Archetype Models](#8-customer-archetype-models)
9. [Competitor Intelligence Models](#9-competitor-intelligence-models)
10. [Brand-User Match Models](#10-brand-user-match-models)
11. [Learning Signal Models](#11-learning-signal-models)

### SECTION C: CATEGORY TAXONOMY & ARCHETYPES
12. [Hierarchical Category System](#12-hierarchical-category-system)
13. [Category Psychological Priors](#13-category-psychological-priors)
14. [Pre-Built Category Archetypes](#14-pre-built-category-archetypes)
15. [Archetype Management Service](#15-archetype-management-service)

### SECTION D: DATA INGESTION PIPELINE
16. [Amazon Review Connector](#16-amazon-review-connector)
17. [Web Research Engine](#17-web-research-engine)
18. [Psycholinguistic Analyzer](#18-psycholinguistic-analyzer)
19. [Social Listening Integration](#19-social-listening-integration)
20. [Advertiser Intake Pipeline](#20-advertiser-intake-pipeline)

### SECTION E: PROFILE GENERATION ENGINE
21. [Claude Synthesis Service](#21-claude-synthesis-service)
22. [Profile Construction Pipeline](#22-profile-construction-pipeline)
23. [Confidence Scoring System](#23-confidence-scoring-system)
24. [Profile Refresh Strategy](#24-profile-refresh-strategy)

### SECTION F: BRAND-USER MATCHING ENGINE
25. [Multi-Dimensional Matcher](#25-multi-dimensional-matcher)
26. [Mechanism Recommendation Engine](#26-mechanism-recommendation-engine)
27. [Frame Selection Algorithm](#27-frame-selection-algorithm)
28. [Real-Time Match Scoring](#28-real-time-match-scoring)

### SECTION G: MECHANISM EFFECTIVENESS TRACKING
29. [Brand-Mechanism Performance Model](#29-brand-mechanism-performance-model)
30. [Effectiveness Update Engine](#30-effectiveness-update-engine)
31. [Bayesian Brand Learning](#31-bayesian-brand-learning)
32. [Cross-Brand Transfer Learning](#32-cross-brand-transfer-learning)

### SECTION H: EVENT BUS INTEGRATION (#31)
33. [Brand Intelligence Events](#33-brand-intelligence-events)
34. [Kafka Topic Definitions](#34-kafka-topic-definitions)
35. [Event Producers](#35-event-producers)
36. [Event Consumers](#36-event-consumers)

### SECTION I: CACHE INTEGRATION (#31)
37. [Multi-Level Cache Strategy](#37-multi-level-cache-strategy)
38. [Brand Profile Cache](#38-brand-profile-cache)
39. [Match Score Cache](#39-match-score-cache)
40. [Cache Invalidation Triggers](#40-cache-invalidation-triggers)

### SECTION J: FEATURE STORE INTEGRATION (#30)
41. [Brand Feature Definitions](#41-brand-feature-definitions)
42. [Online Store Integration](#42-online-store-integration)
43. [Feature Freshness Management](#43-feature-freshness-management)

### SECTION K: GRADIENT BRIDGE INTEGRATION (#06)
44. [Learning Signal Emission](#44-learning-signal-emission)
45. [Outcome Signal Consumption](#45-outcome-signal-consumption)
46. [Credit Attribution for Brands](#46-credit-attribution-for-brands)
47. [Empirical Prior Integration](#47-empirical-prior-integration)

### SECTION L: NEO4J SCHEMA
48. [Brand Intelligence Graph Model](#48-brand-intelligence-graph-model)
49. [Learning Relationships](#49-learning-relationships)
50. [Analytics Queries](#50-analytics-queries)
51. [Graph Constraints & Indexes](#51-graph-constraints-indexes)

### SECTION M: LANGGRAPH WORKFLOW NODES
52. [Brand Profile Loader Node](#52-brand-profile-loader-node)
53. [Brand-User Matcher Node](#53-brand-user-matcher-node)
54. [Mechanism Recommender Node](#54-mechanism-recommender-node)
55. [Workflow Integration](#55-workflow-integration)

### SECTION N: FASTAPI SERVICE
56. [Brand Profile Endpoints](#56-brand-profile-endpoints)
57. [Matching Endpoints](#57-matching-endpoints)
58. [Analytics Endpoints](#58-analytics-endpoints)
59. [Admin Endpoints](#59-admin-endpoints)

### SECTION O: PROMETHEUS METRICS
60. [Profile Metrics](#60-profile-metrics)
61. [Matching Metrics](#61-matching-metrics)
62. [Learning Metrics](#62-learning-metrics)
63. [Cache Metrics](#63-cache-metrics)

### SECTION P: TESTING & OPERATIONS
64. [Unit Tests](#64-unit-tests)
65. [Integration Tests](#65-integration-tests)
66. [Performance Tests](#66-performance-tests)
67. [Implementation Timeline](#67-implementation-timeline)
68. [Success Metrics](#68-success-metrics)

---

# SECTION A: STRATEGIC OVERVIEW

## 1. Executive Summary

### What Brand Intelligence Does

Enhancement #14 transforms advertiser onboarding from a cold-start problem into an immediate psychological intelligence capability. The system automatically extracts brand psychological profiles from multiple data sources, matches brands to user segments using validated psychological constructs, and **continuously learns** which brand-mechanism combinations drive conversions.

```
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│                                                                                             │
│   BRAND INTELLIGENCE: THE BRIDGE BETWEEN ADVERTISER AND AUDIENCE                           │
│   ══════════════════════════════════════════════════════════════                           │
│                                                                                             │
│   ┌─────────────────────┐                              ┌─────────────────────┐             │
│   │                     │                              │                     │             │
│   │   ADVERTISER        │                              │   USER PROFILE      │             │
│   │   "Nike"            │                              │   (from #13)        │             │
│   │                     │                              │                     │             │
│   │   • Brand assets    │                              │   • Big Five        │             │
│   │   • Amazon reviews  │                              │   • Reg Focus       │             │
│   │   • Category        │                              │   • Journey State   │             │
│   │                     │                              │   • Data Tier       │             │
│   └──────────┬──────────┘                              └──────────┬──────────┘             │
│              │                                                    │                        │
│              ▼                                                    ▼                        │
│   ┌─────────────────────────────────────────────────────────────────────────────┐         │
│   │                                                                             │         │
│   │                        BRAND INTELLIGENCE ENGINE                            │         │
│   │                                                                             │         │
│   │   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐   │         │
│   │   │   PROFILE   │   │  ARCHETYPE  │   │  MECHANISM  │   │   MATCH     │   │         │
│   │   │   ENGINE    │──▶│   LIBRARY   │──▶│   MAPPER    │──▶│   SCORER    │   │         │
│   │   └─────────────┘   └─────────────┘   └─────────────┘   └─────────────┘   │         │
│   │                                                                             │         │
│   └─────────────────────────────────────┬───────────────────────────────────────┘         │
│                                         │                                                  │
│                                         ▼                                                  │
│   ┌─────────────────────────────────────────────────────────────────────────────┐         │
│   │                                                                             │         │
│   │   OUTPUT: BrandUserMatchResult                                              │         │
│   │   • overall_match_score: 0.82                                               │         │
│   │   • recommended_mechanisms: [IDENTITY_CONSTRUCTION, MIMETIC_DESIRE]         │         │
│   │   • recommended_frame: "promotion_gain"                                     │         │
│   │   • brand_voice: {pace: "fast", energy: "high", warmth: "warm"}            │         │
│   │   • mechanism_effectiveness: {IDENTITY: 0.78, MIMETIC: 0.72, ...}          │         │
│   │                                                                             │         │
│   └─────────────────────────────────────────────────────────────────────────────┘         │
│                                                                                             │
│   THE LEARNING LOOP (via Gradient Bridge #06):                                             │
│   ───────────────────────────────────────────                                              │
│   Match Result → Ad Served → Conversion → Credit Attribution →                             │
│   → Brand-Mechanism Effectiveness Update → Better Match Scores                             │
│                                                                                             │
└─────────────────────────────────────────────────────────────────────────────────────────────┘
```

### Key Capabilities

| Capability | Description | Business Impact |
|------------|-------------|-----------------|
| **Automated Brand Profiling** | Extract psychological profile from brand assets, reviews, web data | <4 hour onboarding |
| **Psychological Matching** | Multi-dimensional brand-user alignment scoring | Precision targeting |
| **Mechanism Recommendation** | Which of 9 mechanisms work best for this brand-user pair | +15-25% lift |
| **Continuous Learning** | Bayesian updating of brand effectiveness from outcomes | Improving over time |
| **Real-Time Serving** | <5ms match scoring via Feature Store integration | Production-ready |
| **Cross-Brand Transfer** | Similar brands share learning for faster cold-start resolution | Category intelligence |

### Expected Impact

| Metric | Without Brand Intel | With Brand Intel | Improvement |
|--------|---------------------|------------------|-------------|
| Time to first effective campaign | 2-4 weeks | <24 hours | 14-28x faster |
| First-campaign CTR vs mature | 0.5-0.6x | >0.85x | +40-70% |
| Mechanism selection accuracy | Random (11%) | >65% | 6x improvement |
| Brand-user match latency | N/A | <5ms | Production-ready |
| Learning convergence | Per-brand siloed | Cross-brand transfer | Category intelligence |

---

## 2. The Brand Cold Start Problem

### The Problem Statement

Every new advertiser on ADAM is a cold-start problem. Without understanding the brand's psychological identity, ADAM cannot:
- Match the brand to psychologically compatible users
- Select effective cognitive mechanisms
- Generate brand-voice-aligned copy
- Make data-driven optimization decisions

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                                                                                         │
│   THE BRAND COLD START PROBLEM                                                          │
│   ════════════════════════════                                                          │
│                                                                                         │
│   Day 1 Without Brand Intelligence:                                                     │
│   ─────────────────────────────────                                                     │
│                                                                                         │
│   New Advertiser → ??? → Generic Targeting → Poor Results → Wasted Budget              │
│                                                                                         │
│   • No psychological profile                                                            │
│   • No archetype targeting                                                              │
│   • No mechanism guidance                                                               │
│   • No voice parameters for copy                                                        │
│   • Must learn from scratch (2-4 weeks)                                                 │
│                                                                                         │
│   Day 1 With Brand Intelligence:                                                        │
│   ──────────────────────────────                                                        │
│                                                                                         │
│   New Advertiser → Profile Engine → Psychological Targeting → Strong Results           │
│                                                                                         │
│   • Regulatory focus: PROMOTION (confidence: 0.78)                                      │
│   • Brand personality: High excitement, high competence                                 │
│   • Target archetypes: "Achievement Seekers", "Status Signallers"                      │
│   • Effective mechanisms: IDENTITY_CONSTRUCTION, WANTING_LIKING                        │
│   • Voice: Fast pace, high energy, aspirational                                        │
│   • Effective from first impression                                                     │
│                                                                                         │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

### Data Sources for Profile Generation

| Source | Data Type | Contribution | Availability |
|--------|-----------|--------------|--------------|
| **Amazon Reviews** | Customer language about brand products | Personality markers, value signals, regulatory focus | 1.2B+ reviews |
| **Advertiser Intake** | Self-reported brand identity | Voice parameters, constraints, target audience | Optional |
| **Web Research** | Website, social media, news | Positioning, messaging tone, brand values | Automated |
| **Category Priors** | Historical patterns by category | Baseline psychological profile | Always available |
| **Cross-Brand Transfer** | Similar brands' learning | Mechanism effectiveness priors | When available |

### The Solution Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                                                                                         │
│   BRAND INTELLIGENCE SOLVES COLD START                                                  │
│   ════════════════════════════════════                                                  │
│                                                                                         │
│   1. PROFILE GENERATION (Batch - Hours)                                                 │
│   ───────────────────────────────────────                                               │
│                                                                                         │
│   ┌───────────┐   ┌───────────┐   ┌───────────┐   ┌───────────┐                        │
│   │  Amazon   │   │   Web     │   │ Advertiser│   │ Category  │                        │
│   │  Reviews  │   │ Research  │   │  Intake   │   │  Priors   │                        │
│   └─────┬─────┘   └─────┬─────┘   └─────┬─────┘   └─────┬─────┘                        │
│         │               │               │               │                               │
│         └───────────────┴───────────────┴───────────────┘                               │
│                                   │                                                     │
│                                   ▼                                                     │
│                     ┌─────────────────────────┐                                         │
│                     │   CLAUDE SYNTHESIS      │                                         │
│                     │   Psychological Profile │                                         │
│                     └───────────┬─────────────┘                                         │
│                                 │                                                       │
│                                 ▼                                                       │
│                     ┌─────────────────────────┐                                         │
│                     │   NEO4J GRAPH           │                                         │
│                     │   Brand Node + Edges    │                                         │
│                     └───────────┬─────────────┘                                         │
│                                 │                                                       │
│   2. FEATURE SERVING (Real-Time - <5ms)        │                                        │
│   ──────────────────────────────────────────   │                                        │
│                                 │              │                                        │
│                     ┌───────────▼─────────────┐                                         │
│                     │   FEATURE STORE (#30)   │                                         │
│                     │   Brand Profile Vector  │                                         │
│                     └───────────┬─────────────┘                                         │
│                                 │                                                       │
│                     ┌───────────▼─────────────┐                                         │
│                     │   REDIS CACHE (#31)     │                                         │
│                     │   Hot Brand Profiles    │                                         │
│                     └─────────────────────────┘                                         │
│                                                                                         │
│   3. CONTINUOUS LEARNING (Background - Minutes)                                         │
│   ─────────────────────────────────────────────                                         │
│                                                                                         │
│   Conversion Event → Gradient Bridge (#06) → Brand-Mechanism Update →                  │
│   → Cache Invalidation → Updated Match Scores                                          │
│                                                                                         │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Architecture Overview

### Three-Tier Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                                                                                         │
│                        BRAND INTELLIGENCE THREE-TIER ARCHITECTURE                       │
│                                                                                         │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                         │
│   TIER 1: BATCH INTELLIGENCE (Hours)                                                    │
│   ══════════════════════════════════                                                    │
│                                                                                         │
│   ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐                     │
│   │  Profile         │  │  Archetype       │  │  Competitive     │                     │
│   │  Generation      │  │  Mapping         │  │  Analysis        │                     │
│   │                  │  │                  │  │                  │                     │
│   │  • Amazon data   │  │  • Category fit  │  │  • Positioning   │                     │
│   │  • Web research  │  │  • User segments │  │  • Whitespace    │                     │
│   │  • Claude synth  │  │  • Fit scores    │  │  • Gaps          │                     │
│   └────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘                     │
│            │                     │                     │                               │
│            └─────────────────────┴─────────────────────┘                               │
│                                  │                                                      │
│                                  ▼                                                      │
│                    ┌──────────────────────────┐                                         │
│                    │      NEO4J GRAPH         │                                         │
│                    │  Brand + Archetype +     │                                         │
│                    │  Mechanism Nodes         │                                         │
│                    └────────────┬─────────────┘                                         │
│                                 │                                                       │
├─────────────────────────────────┼───────────────────────────────────────────────────────┤
│                                 │                                                       │
│   TIER 2: REAL-TIME SERVING (<5ms)                                                      │
│   ════════════════════════════════                                                      │
│                                 │                                                       │
│                    ┌────────────▼─────────────┐                                         │
│                    │    FEATURE STORE (#30)   │                                         │
│                    │    Brand Feature Groups  │                                         │
│                    └────────────┬─────────────┘                                         │
│                                 │                                                       │
│          ┌──────────────────────┼──────────────────────┐                               │
│          │                      │                      │                               │
│          ▼                      ▼                      ▼                               │
│   ┌──────────────┐    ┌──────────────┐    ┌──────────────┐                             │
│   │ L1: Process  │    │ L2: Redis    │    │ L3: Feature  │                             │
│   │ Memory       │    │ Cluster      │    │ Store        │                             │
│   │ (~1ms)       │    │ (~2ms)       │    │ (~5ms)       │                             │
│   └──────────────┘    └──────────────┘    └──────────────┘                             │
│                                                                                         │
│   Services:                                                                             │
│   ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐                     │
│   │  Profile         │  │  Match           │  │  Mechanism       │                     │
│   │  Loader          │  │  Scorer          │  │  Recommender     │                     │
│   └──────────────────┘  └──────────────────┘  └──────────────────┘                     │
│                                                                                         │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                         │
│   TIER 3: LEARNING LOOP (Background - Minutes)                                          │
│   ════════════════════════════════════════════                                          │
│                                                                                         │
│   ┌──────────────────────────────────────────────────────────────────────────────┐     │
│   │                                                                              │     │
│   │   KAFKA EVENT BUS (#31)                                                      │     │
│   │                                                                              │     │
│   │   Topics:                                                                    │     │
│   │   • adam.brands.profile_created                                              │     │
│   │   • adam.brands.match_computed                                               │     │
│   │   • adam.brands.mechanism_used                                               │     │
│   │   • adam.signals.conversion                                                  │     │
│   │                                                                              │     │
│   └────────────────────────────────────┬─────────────────────────────────────────┘     │
│                                        │                                               │
│                                        ▼                                               │
│   ┌──────────────────────────────────────────────────────────────────────────────┐     │
│   │                                                                              │     │
│   │   GRADIENT BRIDGE (#06)                                                      │     │
│   │                                                                              │     │
│   │   • Credit attribution to brand-mechanism pairs                              │     │
│   │   • Bayesian effectiveness updates                                           │     │
│   │   • Cross-brand transfer learning                                            │     │
│   │   • Cache invalidation triggers                                              │     │
│   │                                                                              │     │
│   └──────────────────────────────────────────────────────────────────────────────┘     │
│                                                                                         │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

### Component Integration Map

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                                                                                         │
│   BRAND INTELLIGENCE INTEGRATION MAP                                                    │
│   ══════════════════════════════════                                                    │
│                                                                                         │
│                          ┌─────────────────────┐                                        │
│                          │                     │                                        │
│                          │   #14 BRAND         │                                        │
│                          │   INTELLIGENCE      │                                        │
│                          │                     │                                        │
│                          └──────────┬──────────┘                                        │
│                                     │                                                   │
│         ┌───────────────────────────┼───────────────────────────┐                      │
│         │                           │                           │                      │
│         ▼                           ▼                           ▼                      │
│   ┌───────────────┐         ┌───────────────┐         ┌───────────────┐               │
│   │               │         │               │         │               │               │
│   │ #15 COPY      │         │ #28 WPP       │         │ #18 EXPLAIN   │               │
│   │ GENERATION    │         │ AD DESK       │         │ ENGINE        │               │
│   │               │         │               │         │               │               │
│   │ Consumes:     │         │ Consumes:     │         │ Consumes:     │               │
│   │ • BrandVoice  │         │ • Archetypes  │         │ • Brand match │               │
│   │ • Constraints │         │ • Personality │         │ • Why this    │               │
│   │ • Mechanisms  │         │ • Mechanisms  │         │   brand-user  │               │
│   │               │         │               │         │   pairing     │               │
│   └───────────────┘         └───────────────┘         └───────────────┘               │
│                                                                                         │
│   UPSTREAM DEPENDENCIES:                                                                │
│   ─────────────────────                                                                 │
│                                                                                         │
│   ┌───────────────┐   ┌───────────────┐   ┌───────────────┐   ┌───────────────┐       │
│   │ #13 COLD      │   │ #21 EMBED     │   │ #30 FEATURE   │   │ #31 EVENT     │       │
│   │ START         │   │ DINGS         │   │ STORE         │   │ BUS/CACHE     │       │
│   │               │   │               │   │               │   │               │       │
│   │ Provides:     │   │ Provides:     │   │ Provides:     │   │ Provides:     │       │
│   │ User profiles │   │ Brand vectors │   │ Real-time     │   │ Learning      │       │
│   │ for matching  │   │ for similarity│   │ serving       │   │ infrastructure│       │
│   └───────────────┘   └───────────────┘   └───────────────┘   └───────────────┘       │
│                                                                                         │
│   LEARNING CONNECTION:                                                                  │
│   ───────────────────                                                                   │
│                                                                                         │
│   ┌───────────────────────────────────────────────────────────────────────────────┐    │
│   │                                                                               │    │
│   │   #06 GRADIENT BRIDGE                                                         │    │
│   │                                                                               │    │
│   │   Brand Intelligence ←→ Gradient Bridge Signals:                              │    │
│   │                                                                               │    │
│   │   EMITS:                              CONSUMES:                               │    │
│   │   • BrandMatchSignal                  • ConversionOutcome                     │    │
│   │   • MechanismUsedSignal               • CreditAttribution                     │    │
│   │   • ProfileCreatedSignal              • EmpiricalPrior                        │    │
│   │                                                                               │    │
│   └───────────────────────────────────────────────────────────────────────────────┘    │
│                                                                                         │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Cross-Component Learning Flow

### How Brand Intelligence Learns

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                                                                                         │
│   BRAND INTELLIGENCE LEARNING LOOP                                                      │
│   ════════════════════════════════                                                      │
│                                                                                         │
│   1. MATCH COMPUTED                                                                     │
│   ─────────────────                                                                     │
│                                                                                         │
│   ┌─────────────────┐                                                                   │
│   │  Brand-User     │                                                                   │
│   │  Match Request  │                                                                   │
│   └────────┬────────┘                                                                   │
│            │                                                                            │
│            ▼                                                                            │
│   ┌─────────────────────────────────────────────────────────────┐                      │
│   │                                                             │                      │
│   │   Brand Intelligence Engine                                 │                      │
│   │                                                             │                      │
│   │   Input:                                                    │                      │
│   │   • brand_id: "nike_001"                                    │                      │
│   │   • user_id: "usr_12345"                                    │                      │
│   │   • user_profile: {openness: 0.72, promotion_focus: 0.8}   │                      │
│   │                                                             │                      │
│   │   Output:                                                   │                      │
│   │   • match_score: 0.82                                       │                      │
│   │   • recommended_mechanisms: [IDENTITY, MIMETIC]             │                      │
│   │   • mechanism_priors: {IDENTITY: 0.78, MIMETIC: 0.65}      │                      │
│   │                                                             │                      │
│   └───────────────────────┬─────────────────────────────────────┘                      │
│                           │                                                             │
│                           ▼                                                             │
│   2. EMIT LEARNING SIGNAL                                                               │
│   ───────────────────────                                                               │
│                                                                                         │
│   ┌─────────────────────────────────────────────────────────────┐                      │
│   │                                                             │                      │
│   │   BrandMatchSignal (→ Kafka)                                │                      │
│   │                                                             │                      │
│   │   {                                                         │                      │
│   │     "signal_type": "brand_match",                           │                      │
│   │     "decision_id": "dec_789",                               │                      │
│   │     "brand_id": "nike_001",                                 │                      │
│   │     "user_id": "usr_12345",                                 │                      │
│   │     "match_score": 0.82,                                    │                      │
│   │     "mechanisms_recommended": ["IDENTITY", "MIMETIC"],      │                      │
│   │     "mechanism_priors": {"IDENTITY": 0.78, "MIMETIC": 0.65},│                      │
│   │     "awaiting_outcome": true                                │                      │
│   │   }                                                         │                      │
│   │                                                             │                      │
│   └───────────────────────┬─────────────────────────────────────┘                      │
│                           │                                                             │
│                           ▼                                                             │
│   3. AD SERVED + CONVERSION                                                             │
│   ─────────────────────────                                                             │
│                                                                                         │
│   [Ad served using IDENTITY mechanism] → [User converts]                               │
│                                                                                         │
│                           │                                                             │
│                           ▼                                                             │
│   4. OUTCOME SIGNAL                                                                     │
│   ─────────────────                                                                     │
│                                                                                         │
│   ┌─────────────────────────────────────────────────────────────┐                      │
│   │                                                             │                      │
│   │   ConversionOutcome (from #06)                              │                      │
│   │                                                             │                      │
│   │   {                                                         │                      │
│   │     "decision_id": "dec_789",                               │                      │
│   │     "outcome_type": "conversion",                           │                      │
│   │     "outcome_value": 1.0,                                   │                      │
│   │     "mechanism_used": "IDENTITY_CONSTRUCTION",              │                      │
│   │     "attribution": {                                        │                      │
│   │       "brand_match_contribution": 0.25,                     │                      │
│   │       "mechanism_contribution": 0.35,                       │                      │
│   │       "copy_contribution": 0.40                             │                      │
│   │     }                                                       │                      │
│   │   }                                                         │                      │
│   │                                                             │                      │
│   └───────────────────────┬─────────────────────────────────────┘                      │
│                           │                                                             │
│                           ▼                                                             │
│   5. BAYESIAN UPDATE                                                                    │
│   ─────────────────                                                                     │
│                                                                                         │
│   ┌─────────────────────────────────────────────────────────────┐                      │
│   │                                                             │                      │
│   │   Brand-Mechanism Effectiveness Update                      │                      │
│   │                                                             │                      │
│   │   BEFORE:                                                   │                      │
│   │   (nike_001)-[:MECHANISM_EFFECTIVENESS {                    │                      │
│   │     mechanism: "IDENTITY_CONSTRUCTION",                     │                      │
│   │     alpha: 12, beta: 8, mean: 0.60                          │                      │
│   │   }]->(IDENTITY)                                            │                      │
│   │                                                             │                      │
│   │   UPDATE: Outcome = 1.0, Credit = 0.25                      │                      │
│   │   alpha_new = 12 + 0.25 = 12.25                             │                      │
│   │   beta unchanged (success)                                  │                      │
│   │                                                             │                      │
│   │   AFTER:                                                    │                      │
│   │   (nike_001)-[:MECHANISM_EFFECTIVENESS {                    │                      │
│   │     mechanism: "IDENTITY_CONSTRUCTION",                     │                      │
│   │     alpha: 12.25, beta: 8, mean: 0.605                      │                      │
│   │   }]->(IDENTITY)                                            │                      │
│   │                                                             │                      │
│   └───────────────────────┬─────────────────────────────────────┘                      │
│                           │                                                             │
│                           ▼                                                             │
│   6. CACHE INVALIDATION                                                                 │
│   ─────────────────────                                                                 │
│                                                                                         │
│   ┌─────────────────────────────────────────────────────────────┐                      │
│   │                                                             │                      │
│   │   Invalidate:                                               │                      │
│   │   • brand:profile:nike_001                                  │                      │
│   │   • brand:mechanism_priors:nike_001                         │                      │
│   │                                                             │                      │
│   │   Next request uses updated priors!                         │                      │
│   │                                                             │                      │
│   └─────────────────────────────────────────────────────────────┘                      │
│                                                                                         │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 5. Research Foundations

### Brand Psychology Research

| Theory | Source | Application in ADAM |
|--------|--------|---------------------|
| **Aaker's Brand Personality** | Aaker, J. (1997) "Dimensions of Brand Personality" | 5-dimension brand personality scoring |
| **Regulatory Focus Theory** | Higgins, E.T. (1997) | Brand promotion/prevention orientation |
| **Construal Level Theory** | Trope & Liberman (2010) | Abstract vs. concrete brand messaging |
| **Schwartz Values** | Schwartz, S.H. (1992) | Brand value hierarchy extraction |
| **Consumer-Brand Congruence** | Sirgy, M.J. (1982) | Personality-brand matching algorithms |

### Mechanism Effectiveness Research

| Mechanism | Research | Brand Application |
|-----------|----------|-------------------|
| **Identity Construction** | Belk (1988) "Possessions and Extended Self" | Status brands, luxury, lifestyle |
| **Mimetic Desire** | Girard (1961) | Social proof, influencer brands |
| **Wanting-Liking Dissociation** | Berridge & Robinson (2016) | Premium brands, hedonic products |
| **Temporal Construal** | Trope & Liberman (2003) | Long-term value brands vs. immediate gratification |
| **Automatic Evaluation** | Fazio et al. (1986) | Brand familiarity, rapid assessment |

### Transfer Learning Research

| Approach | Source | Application |
|----------|--------|-------------|
| **Category-Based Transfer** | Pan & Yang (2010) "Survey on Transfer Learning" | New brands learn from category peers |
| **Multi-Armed Bandit Transfer** | Bastani et al. (2021) | Thompson Sampling with shared priors |
| **Hierarchical Bayesian** | Gelman et al. (2013) | Category → Brand → Mechanism hierarchy |

---

# SECTION B: CORE DATA MODELS

## 6. Configuration Models

```python
# =============================================================================
# ADAM Enhancement #14: Configuration Models
# Location: adam/brand_intelligence/config.py
# =============================================================================

"""
Configuration models for Brand Intelligence system.
Centralized configuration with environment variable support.
"""

from __future__ import annotations
from pydantic import BaseSettings, Field, validator
from typing import List, Optional, Dict
from enum import Enum


class Environment(str, Enum):
    """Deployment environment."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class BrandIntelligenceConfig(BaseSettings):
    """
    Complete configuration for Brand Intelligence system.
    
    All settings can be overridden via environment variables
    with ADAM_BRAND_INTEL_ prefix.
    """
    
    # ==========================================================================
    # ENVIRONMENT
    # ==========================================================================
    environment: Environment = Field(
        default=Environment.DEVELOPMENT,
        description="Deployment environment"
    )
    
    # ==========================================================================
    # DATA COLLECTION
    # ==========================================================================
    amazon_review_limit: int = Field(
        default=2000,
        ge=100,
        le=10000,
        description="Maximum reviews to analyze per brand"
    )
    amazon_api_timeout_seconds: float = Field(
        default=30.0,
        description="Timeout for Amazon API calls"
    )
    amazon_batch_size: int = Field(
        default=100,
        description="Reviews per batch"
    )
    
    web_research_depth: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Pages to analyze per web source"
    )
    web_research_timeout_seconds: float = Field(
        default=60.0,
        description="Total timeout for web research"
    )
    
    social_platforms: List[str] = Field(
        default=["twitter", "linkedin", "instagram", "facebook"],
        description="Social platforms to analyze"
    )
    
    # ==========================================================================
    # CLAUDE CONFIGURATION
    # ==========================================================================
    claude_model: str = Field(
        default="claude-sonnet-4-20250514",
        description="Claude model for synthesis"
    )
    claude_max_tokens: int = Field(
        default=4000,
        description="Max tokens for Claude response"
    )
    claude_timeout_seconds: float = Field(
        default=60.0,
        description="Timeout for Claude API calls"
    )
    
    # ==========================================================================
    # EMBEDDING CONFIGURATION
    # ==========================================================================
    embedding_model: str = Field(
        default="text-embedding-3-small",
        description="Embedding model for brand vectors"
    )
    embedding_dimension: int = Field(
        default=384,
        description="Embedding vector dimension"
    )
    
    # ==========================================================================
    # CACHING CONFIGURATION
    # ==========================================================================
    redis_host: str = Field(default="localhost")
    redis_port: int = Field(default=6379)
    redis_password: Optional[str] = Field(default=None)
    redis_db: int = Field(default=0)
    
    profile_cache_ttl_seconds: int = Field(
        default=604800,  # 7 days
        description="TTL for brand profile cache"
    )
    match_cache_ttl_seconds: int = Field(
        default=3600,  # 1 hour
        description="TTL for match score cache"
    )
    mechanism_cache_ttl_seconds: int = Field(
        default=300,  # 5 minutes
        description="TTL for mechanism effectiveness cache"
    )
    
    # ==========================================================================
    # FEATURE STORE CONFIGURATION
    # ==========================================================================
    feature_store_host: str = Field(default="localhost")
    feature_store_port: int = Field(default=8080)
    feature_freshness_max_age_seconds: int = Field(
        default=3600,
        description="Max age before feature refresh triggered"
    )
    
    # ==========================================================================
    # NEO4J CONFIGURATION
    # ==========================================================================
    neo4j_uri: str = Field(default="bolt://localhost:7687")
    neo4j_user: str = Field(default="neo4j")
    neo4j_password: str = Field(default="password")
    neo4j_database: str = Field(default="adam")
    
    # ==========================================================================
    # KAFKA CONFIGURATION
    # ==========================================================================
    kafka_bootstrap_servers: str = Field(default="localhost:9092")
    kafka_consumer_group: str = Field(default="brand-intelligence-consumer")
    kafka_producer_acks: str = Field(default="all")
    
    # ==========================================================================
    # PROFILE GENERATION
    # ==========================================================================
    min_reviews_for_confidence: int = Field(
        default=50,
        description="Minimum reviews for high confidence"
    )
    auto_refresh_days: int = Field(
        default=30,
        description="Days before auto profile refresh"
    )
    significant_change_threshold: float = Field(
        default=0.15,
        ge=0.0,
        le=1.0,
        description="Change threshold triggering profile update"
    )
    
    # ==========================================================================
    # MATCHING CONFIGURATION
    # ==========================================================================
    min_match_confidence: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Minimum confidence for match results"
    )
    default_mechanism_count: int = Field(
        default=3,
        ge=1,
        le=9,
        description="Default mechanisms to recommend"
    )
    
    # ==========================================================================
    # LEARNING CONFIGURATION
    # ==========================================================================
    bayesian_prior_alpha: float = Field(
        default=1.0,
        description="Default alpha for Beta prior"
    )
    bayesian_prior_beta: float = Field(
        default=1.0,
        description="Default beta for Beta prior"
    )
    learning_rate: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Learning rate for effectiveness updates"
    )
    transfer_learning_weight: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Weight for cross-brand transfer learning"
    )
    
    # ==========================================================================
    # OBSERVABILITY
    # ==========================================================================
    metrics_prefix: str = Field(default="adam_brand_intel")
    enable_tracing: bool = Field(default=True)
    log_level: str = Field(default="INFO")
    
    @validator("claude_model")
    def validate_claude_model(cls, v):
        allowed = ["claude-sonnet-4-20250514", "claude-opus-4-20250514"]
        if v not in allowed:
            raise ValueError(f"claude_model must be one of {allowed}")
        return v
    
    class Config:
        env_prefix = "ADAM_BRAND_INTEL_"
        case_sensitive = False


# =============================================================================
# MATCHING WEIGHT CONFIGURATION
# =============================================================================

class MatchingWeights(BaseSettings):
    """
    Configurable weights for brand-user matching components.
    """
    personality: float = Field(default=0.25, ge=0.0, le=1.0)
    regulatory_focus: float = Field(default=0.20, ge=0.0, le=1.0)
    construal_level: float = Field(default=0.15, ge=0.0, le=1.0)
    values: float = Field(default=0.15, ge=0.0, le=1.0)
    archetype: float = Field(default=0.10, ge=0.0, le=1.0)
    mechanism_history: float = Field(default=0.15, ge=0.0, le=1.0)
    
    @validator("mechanism_history")
    def validate_weights_sum(cls, v, values):
        total = sum([
            values.get("personality", 0),
            values.get("regulatory_focus", 0),
            values.get("construal_level", 0),
            values.get("values", 0),
            values.get("archetype", 0),
            v
        ])
        if abs(total - 1.0) > 0.01:
            raise ValueError(f"Weights must sum to 1.0, got {total}")
        return v
    
    class Config:
        env_prefix = "ADAM_BRAND_MATCH_WEIGHT_"
```

---

## 7. Brand Profile Models

```python
# =============================================================================
# ADAM Enhancement #14: Brand Profile Models
# Location: adam/brand_intelligence/models/brand_profile.py
# =============================================================================

"""
Pydantic models for brand psychological profiles.

These models capture the complete psychological characterization of a brand,
enabling personality-based targeting and mechanism selection.
"""

from __future__ import annotations
from pydantic import BaseModel, Field, validator
from typing import Dict, List, Optional, Literal, Any
from datetime import datetime
from enum import Enum
from uuid import uuid4
import numpy as np


# =============================================================================
# ENUMS
# =============================================================================

class RegulatoryFocus(str, Enum):
    """Brand regulatory orientation from Higgins (1997)."""
    PROMOTION = "promotion"    # Gains, aspirations, advancement
    PREVENTION = "prevention"  # Safety, security, avoiding loss
    BALANCED = "balanced"      # Equal promotion/prevention


class ConstrualLevel(str, Enum):
    """Brand communication abstraction level from Trope & Liberman."""
    ABSTRACT = "abstract"    # Why-focused, vision, values
    CONCRETE = "concrete"    # How-focused, features, specifics
    MIXED = "mixed"          # Context-dependent


class SchwartzValue(str, Enum):
    """Schwartz universal human values."""
    POWER = "power"
    ACHIEVEMENT = "achievement"
    HEDONISM = "hedonism"
    STIMULATION = "stimulation"
    SELF_DIRECTION = "self_direction"
    UNIVERSALISM = "universalism"
    BENEVOLENCE = "benevolence"
    TRADITION = "tradition"
    CONFORMITY = "conformity"
    SECURITY = "security"


class BrandDataSource(str, Enum):
    """Sources of brand profile data."""
    AMAZON_REVIEWS = "amazon_reviews"
    ADVERTISER_INTAKE = "advertiser_intake"
    WEB_RESEARCH = "web_research"
    SOCIAL_LISTENING = "social_listening"
    CATEGORY_PRIORS = "category_priors"
    CROSS_BRAND_TRANSFER = "cross_brand_transfer"


# =============================================================================
# PERSONALITY MODELS
# =============================================================================

class AakerBrandPersonality(BaseModel):
    """
    Aaker's (1997) brand personality dimensions.
    
    These dimensions describe how consumers perceive the brand
    as if it were a person.
    """
    sincerity: float = Field(
        ge=0, le=1, default=0.5,
        description="Honest, wholesome, cheerful, down-to-earth"
    )
    excitement: float = Field(
        ge=0, le=1, default=0.5,
        description="Daring, spirited, imaginative, up-to-date"
    )
    competence: float = Field(
        ge=0, le=1, default=0.5,
        description="Reliable, intelligent, successful"
    )
    sophistication: float = Field(
        ge=0, le=1, default=0.5,
        description="Upper class, charming, glamorous"
    )
    ruggedness: float = Field(
        ge=0, le=1, default=0.5,
        description="Outdoorsy, tough, masculine"
    )
    
    def to_vector(self) -> np.ndarray:
        """Convert to numpy vector for similarity calculations."""
        return np.array([
            self.sincerity, self.excitement, self.competence,
            self.sophistication, self.ruggedness
        ])
    
    @classmethod
    def from_vector(cls, vec: np.ndarray) -> "AakerBrandPersonality":
        """Create from numpy vector."""
        return cls(
            sincerity=float(vec[0]),
            excitement=float(vec[1]),
            competence=float(vec[2]),
            sophistication=float(vec[3]),
            ruggedness=float(vec[4])
        )
    
    def dominant_trait(self) -> str:
        """Return the dominant personality trait."""
        traits = {
            "sincerity": self.sincerity,
            "excitement": self.excitement,
            "competence": self.competence,
            "sophistication": self.sophistication,
            "ruggedness": self.ruggedness
        }
        return max(traits, key=traits.get)


class BrandBigFive(BaseModel):
    """
    Big Five personality dimensions the brand embodies.
    
    Maps to user Big Five for congruence matching.
    """
    openness: float = Field(
        ge=0, le=1, default=0.5,
        description="Creative, innovative, unconventional"
    )
    conscientiousness: float = Field(
        ge=0, le=1, default=0.5,
        description="Organized, dependable, disciplined"
    )
    extraversion: float = Field(
        ge=0, le=1, default=0.5,
        description="Outgoing, energetic, talkative"
    )
    agreeableness: float = Field(
        ge=0, le=1, default=0.5,
        description="Friendly, compassionate, cooperative"
    )
    emotional_stability: float = Field(
        ge=0, le=1, default=0.5,
        description="Calm, secure, confident (inverse of neuroticism)"
    )
    
    def to_vector(self) -> np.ndarray:
        """Convert to numpy vector."""
        return np.array([
            self.openness, self.conscientiousness, self.extraversion,
            self.agreeableness, self.emotional_stability
        ])
    
    def to_user_compatible_vector(self) -> np.ndarray:
        """
        Convert to vector compatible with user profiles.
        
        User profiles use neuroticism (inverse of emotional_stability).
        """
        return np.array([
            self.openness, self.conscientiousness, self.extraversion,
            self.agreeableness, 1.0 - self.emotional_stability  # Convert to neuroticism
        ])


# =============================================================================
# VOICE PARAMETERS
# =============================================================================

class VoiceParameters(BaseModel):
    """
    Brand voice characteristics for copy generation.
    
    These parameters drive Enhancement #15 Copy Generation to
    produce brand-consistent messaging.
    """
    # Delivery
    pace: Literal["fast", "medium", "slow"] = Field(
        default="medium",
        description="Speaking/reading pace feel"
    )
    energy: Literal["high", "medium", "calm"] = Field(
        default="medium",
        description="Energy level in messaging"
    )
    formality: Literal["casual", "professional", "authoritative"] = Field(
        default="professional",
        description="Formality level"
    )
    warmth: Literal["warm", "neutral", "distant"] = Field(
        default="neutral",
        description="Emotional warmth"
    )
    humor: Literal["playful", "subtle", "none"] = Field(
        default="none",
        description="Humor usage"
    )
    
    # Linguistic parameters
    avg_sentence_length: Literal["short", "medium", "long"] = Field(
        default="medium",
        description="Preferred sentence length"
    )
    vocabulary_level: Literal["simple", "moderate", "sophisticated"] = Field(
        default="moderate",
        description="Vocabulary complexity"
    )
    use_contractions: bool = Field(
        default=True,
        description="Whether to use contractions"
    )
    use_questions: bool = Field(
        default=True,
        description="Whether to include rhetorical questions"
    )
    use_imperatives: bool = Field(
        default=True,
        description="Whether to use command forms"
    )
    
    # Audio-specific (for iHeart integration)
    audio_pacing_wpm: int = Field(
        default=150,
        ge=100,
        le=200,
        description="Words per minute for audio"
    )
    pause_frequency: Literal["minimal", "moderate", "frequent"] = Field(
        default="moderate",
        description="Pause frequency in audio"
    )


# =============================================================================
# MESSAGING CONSTRAINTS
# =============================================================================

class MessagingConstraints(BaseModel):
    """
    Brand-safe guardrails for ad generation.
    
    These constraints ensure copy generation respects brand guidelines.
    """
    # Content allowances
    allowed_frames: List[str] = Field(
        default_factory=list,
        description="Allowed persuasion frames (e.g., 'gain', 'social_proof')"
    )
    allowed_mechanisms: List[str] = Field(
        default_factory=list,
        description="Allowed cognitive mechanisms"
    )
    
    # Prohibitions
    prohibited_content: List[str] = Field(
        default_factory=list,
        description="Prohibited content types or themes"
    )
    prohibited_words: List[str] = Field(
        default_factory=list,
        description="Prohibited specific words"
    )
    
    # Requirements
    required_elements: List[str] = Field(
        default_factory=list,
        description="Required elements (e.g., 'trademark', 'disclaimer')"
    )
    
    # Competitor handling
    competitor_mentions: Literal["allowed", "indirect", "prohibited"] = Field(
        default="prohibited",
        description="How to handle competitor mentions"
    )
    
    # Claims level
    claims_level: Literal["aggressive", "moderate", "conservative"] = Field(
        default="moderate",
        description="Aggressiveness of marketing claims"
    )
    
    # Emotional boundaries
    max_urgency: float = Field(
        default=0.7, ge=0, le=1,
        description="Maximum urgency level in messaging"
    )
    max_fear_appeal: float = Field(
        default=0.3, ge=0, le=1,
        description="Maximum fear appeal level"
    )
    max_scarcity_appeal: float = Field(
        default=0.5, ge=0, le=1,
        description="Maximum scarcity messaging"
    )
    min_positivity: float = Field(
        default=0.4, ge=0, le=1,
        description="Minimum positive tone"
    )


# =============================================================================
# MAIN BRAND PROFILE
# =============================================================================

class BrandPsychologicalProfile(BaseModel):
    """
    Complete psychological characterization of a brand.
    
    This is the central data structure for Brand Intelligence,
    containing all psychological dimensions needed for targeting.
    """
    
    # ==========================================================================
    # IDENTIFIERS
    # ==========================================================================
    brand_id: str = Field(
        default_factory=lambda: f"brand_{uuid4().hex[:12]}",
        description="Unique brand identifier"
    )
    brand_name: str = Field(
        description="Human-readable brand name"
    )
    advertiser_id: Optional[str] = Field(
        default=None,
        description="Parent advertiser ID"
    )
    
    # ==========================================================================
    # CATEGORIZATION
    # ==========================================================================
    category: str = Field(
        description="Primary category ID"
    )
    sub_categories: List[str] = Field(
        default_factory=list,
        description="Sub-category IDs"
    )
    
    # ==========================================================================
    # CORE PSYCHOLOGICAL IDENTITY
    # ==========================================================================
    regulatory_focus: RegulatoryFocus = Field(
        default=RegulatoryFocus.BALANCED,
        description="Promotion vs prevention orientation"
    )
    regulatory_confidence: float = Field(
        default=0.5, ge=0, le=1,
        description="Confidence in regulatory focus assessment"
    )
    
    construal_tendency: ConstrualLevel = Field(
        default=ConstrualLevel.MIXED,
        description="Abstract vs concrete messaging tendency"
    )
    construal_confidence: float = Field(
        default=0.5, ge=0, le=1,
        description="Confidence in construal assessment"
    )
    
    # ==========================================================================
    # PERSONALITY DIMENSIONS
    # ==========================================================================
    aaker_personality: AakerBrandPersonality = Field(
        default_factory=AakerBrandPersonality,
        description="Aaker brand personality dimensions"
    )
    
    big_five: BrandBigFive = Field(
        default_factory=BrandBigFive,
        description="Big Five personality the brand embodies"
    )
    
    # ==========================================================================
    # VALUE HIERARCHY
    # ==========================================================================
    value_hierarchy: List[SchwartzValue] = Field(
        default_factory=list,
        description="Ordered list of brand values (most important first)"
    )
    value_scores: Dict[str, float] = Field(
        default_factory=dict,
        description="Score for each Schwartz value (0-1)"
    )
    
    # ==========================================================================
    # COMMUNICATION PARAMETERS
    # ==========================================================================
    voice: VoiceParameters = Field(
        default_factory=VoiceParameters,
        description="Brand voice characteristics"
    )
    
    constraints: MessagingConstraints = Field(
        default_factory=MessagingConstraints,
        description="Messaging constraints and guardrails"
    )
    
    # ==========================================================================
    # TARGETING GUIDANCE
    # ==========================================================================
    ideal_customer_summary: str = Field(
        default="",
        description="Natural language description of ideal customer"
    )
    target_archetypes: List[str] = Field(
        default_factory=list,
        description="Archetype IDs this brand targets"
    )
    
    # Mechanism guidance
    preferred_mechanisms: List[str] = Field(
        default_factory=list,
        description="Cognitive mechanisms that work well for this brand"
    )
    avoid_mechanisms: List[str] = Field(
        default_factory=list,
        description="Mechanisms to avoid"
    )
    
    # ==========================================================================
    # EMBEDDINGS
    # ==========================================================================
    embedding: Optional[List[float]] = Field(
        default=None,
        description="Brand embedding vector for similarity search"
    )
    
    # ==========================================================================
    # QUALITY METRICS
    # ==========================================================================
    confidence_score: float = Field(
        default=0.5, ge=0, le=1,
        description="Overall profile confidence"
    )
    data_completeness: float = Field(
        default=0.0, ge=0, le=1,
        description="Percentage of fields populated"
    )
    data_sources: List[BrandDataSource] = Field(
        default_factory=list,
        description="Sources used to build profile"
    )
    
    # ==========================================================================
    # METADATA
    # ==========================================================================
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Profile creation timestamp"
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Last update timestamp"
    )
    last_refresh_at: Optional[datetime] = Field(
        default=None,
        description="Last full refresh timestamp"
    )
    version: int = Field(
        default=1,
        description="Profile version number"
    )
    
    # ==========================================================================
    # LEARNING STATISTICS
    # ==========================================================================
    total_impressions: int = Field(
        default=0,
        description="Total ad impressions for this brand"
    )
    total_conversions: int = Field(
        default=0,
        description="Total conversions attributed"
    )
    learning_velocity: float = Field(
        default=0.0,
        description="Rate of learning (updates per day)"
    )
    
    # ==========================================================================
    # METHODS
    # ==========================================================================
    
    def to_matching_vector(self) -> np.ndarray:
        """
        Convert to vector for brand-user matching.
        
        Returns:
            12-dimensional vector combining personality and orientation.
        """
        return np.concatenate([
            self.aaker_personality.to_vector(),        # 5 dims
            self.big_five.to_vector(),                 # 5 dims
            [1.0 if self.regulatory_focus == RegulatoryFocus.PROMOTION else 0.0],  # 1 dim
            [1.0 if self.construal_tendency == ConstrualLevel.ABSTRACT else 0.0]   # 1 dim
        ])
    
    def to_feature_dict(self) -> Dict[str, Any]:
        """
        Convert to feature dictionary for Feature Store.
        
        Returns:
            Flat dictionary suitable for feature serving.
        """
        return {
            # Identity
            "brand_id": self.brand_id,
            "brand_name": self.brand_name,
            "category": self.category,
            
            # Regulatory focus
            "regulatory_focus": self.regulatory_focus.value,
            "regulatory_confidence": self.regulatory_confidence,
            "is_promotion_focused": 1.0 if self.regulatory_focus == RegulatoryFocus.PROMOTION else 0.0,
            
            # Construal
            "construal_tendency": self.construal_tendency.value,
            "construal_confidence": self.construal_confidence,
            "is_abstract": 1.0 if self.construal_tendency == ConstrualLevel.ABSTRACT else 0.0,
            
            # Aaker
            "aaker_sincerity": self.aaker_personality.sincerity,
            "aaker_excitement": self.aaker_personality.excitement,
            "aaker_competence": self.aaker_personality.competence,
            "aaker_sophistication": self.aaker_personality.sophistication,
            "aaker_ruggedness": self.aaker_personality.ruggedness,
            
            # Big Five
            "brand_openness": self.big_five.openness,
            "brand_conscientiousness": self.big_five.conscientiousness,
            "brand_extraversion": self.big_five.extraversion,
            "brand_agreeableness": self.big_five.agreeableness,
            "brand_emotional_stability": self.big_five.emotional_stability,
            
            # Voice
            "voice_pace": self.voice.pace,
            "voice_energy": self.voice.energy,
            "voice_formality": self.voice.formality,
            "voice_warmth": self.voice.warmth,
            
            # Quality
            "confidence_score": self.confidence_score,
            "data_completeness": self.data_completeness,
            
            # Stats
            "total_impressions": self.total_impressions,
            "total_conversions": self.total_conversions,
            
            # Embedding
            "embedding": self.embedding or []
        }
    
    def compute_data_completeness(self) -> float:
        """Calculate data completeness score."""
        total_fields = 15  # Core fields we care about
        populated = 0
        
        if self.regulatory_confidence > 0.5:
            populated += 1
        if self.construal_confidence > 0.5:
            populated += 1
        if self.aaker_personality.dominant_trait():
            populated += 1
        if len(self.value_hierarchy) >= 3:
            populated += 1
        if self.ideal_customer_summary:
            populated += 1
        if len(self.target_archetypes) > 0:
            populated += 1
        if len(self.preferred_mechanisms) > 0:
            populated += 1
        if self.embedding:
            populated += 1
        if len(self.data_sources) >= 2:
            populated += 1
        if self.voice.pace != "medium":  # Non-default voice
            populated += 1
        if len(self.constraints.allowed_frames) > 0:
            populated += 1
        if self.total_impressions > 0:
            populated += 1
        # Big Five personality
        b5_vec = self.big_five.to_vector()
        if not np.allclose(b5_vec, 0.5):  # Non-default
            populated += 3  # Count as 3 fields
        
        return min(1.0, populated / total_fields)
    
    class Config:
        use_enum_values = False  # Keep enums as enums
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            np.ndarray: lambda v: v.tolist()
        }
```

---

## 8. Customer Archetype Models

```python
# =============================================================================
# ADAM Enhancement #14: Customer Archetype Models
# Location: adam/brand_intelligence/models/archetype.py
# =============================================================================

"""
Customer archetype models for psychological segmentation.

Archetypes represent distinct psychological profiles within a category,
enabling precise targeting based on validated personality clusters.
"""

from __future__ import annotations
from pydantic import BaseModel, Field, validator
from typing import Dict, List, Optional, Literal
from datetime import datetime
from uuid import uuid4
import numpy as np


class DecisionStyle(str, Enum):
    """How the archetype makes purchase decisions."""
    DELIBERATE = "deliberate"      # Careful research, comparison
    IMPULSIVE = "impulsive"        # Quick, emotion-driven
    SOCIAL = "social"              # Influenced by others
    HABITUAL = "habitual"          # Routine, brand loyal
    ANALYTICAL = "analytical"      # Data-driven, feature-focused


class CustomerArchetype(BaseModel):
    """
    Psychological profile of a customer segment.
    
    Archetypes are pre-computed from Amazon review analysis and
    represent distinct psychological clusters within a category.
    """
    
    # ==========================================================================
    # IDENTIFIERS
    # ==========================================================================
    archetype_id: str = Field(
        default_factory=lambda: f"arch_{uuid4().hex[:12]}",
        description="Unique archetype identifier"
    )
    archetype_name: str = Field(
        description="Human-readable archetype name"
    )
    category: str = Field(
        description="Category this archetype belongs to"
    )
    brand_id: Optional[str] = Field(
        default=None,
        description="Brand ID if brand-specific archetype"
    )
    
    # ==========================================================================
    # PSYCHOLOGICAL PROFILE
    # ==========================================================================
    big_five: Dict[str, float] = Field(
        description="Big Five personality scores (0-1)"
    )
    
    regulatory_focus: Literal["promotion", "prevention"] = Field(
        description="Dominant regulatory focus"
    )
    
    construal_preference: Literal["abstract", "concrete"] = Field(
        description="Preferred construal level"
    )
    
    primary_motivations: List[str] = Field(
        default_factory=list,
        description="Core motivations driving purchase"
    )
    
    # ==========================================================================
    # BEHAVIORAL CHARACTERISTICS
    # ==========================================================================
    decision_style: DecisionStyle = Field(
        description="How this archetype makes decisions"
    )
    
    price_sensitivity: float = Field(
        ge=0, le=1,
        description="Sensitivity to price (0=insensitive, 1=very sensitive)"
    )
    
    brand_loyalty_tendency: float = Field(
        ge=0, le=1,
        description="Tendency toward brand loyalty"
    )
    
    information_seeking: float = Field(
        ge=0, le=1,
        description="How much research before purchase"
    )
    
    social_influence: float = Field(
        default=0.5, ge=0, le=1,
        description="Susceptibility to social proof"
    )
    
    risk_tolerance: float = Field(
        default=0.5, ge=0, le=1,
        description="Willingness to try new/unknown"
    )
    
    # ==========================================================================
    # MESSAGING APPROACH
    # ==========================================================================
    effective_appeals: List[str] = Field(
        default_factory=list,
        description="Appeals that resonate (e.g., 'status', 'value', 'innovation')"
    )
    
    effective_frames: List[str] = Field(
        default_factory=list,
        description="Effective framing approaches"
    )
    
    effective_mechanisms: List[str] = Field(
        default_factory=list,
        description="Cognitive mechanisms that work"
    )
    
    messaging_tone: str = Field(
        description="Preferred messaging tone"
    )
    
    cta_preferences: List[str] = Field(
        default_factory=list,
        description="Preferred call-to-action styles"
    )
    
    # ==========================================================================
    # SEGMENT SIZE
    # ==========================================================================
    estimated_population_pct: float = Field(
        ge=0, le=1,
        description="Percentage of category population"
    )
    
    estimated_value_pct: float = Field(
        ge=0, le=1,
        description="Percentage of category revenue"
    )
    
    # ==========================================================================
    # BRAND FIT
    # ==========================================================================
    brand_fit_score: float = Field(
        default=0.0, ge=0, le=1,
        description="Computed fit with associated brand"
    )
    
    # ==========================================================================
    # METADATA
    # ==========================================================================
    created_at: datetime = Field(
        default_factory=datetime.utcnow
    )
    source: Literal["category_library", "brand_specific", "learned"] = Field(
        default="category_library"
    )
    sample_size: int = Field(
        default=0,
        description="Number of users/reviews used to define"
    )
    
    # ==========================================================================
    # METHODS
    # ==========================================================================
    
    def to_vector(self) -> np.ndarray:
        """
        Convert to vector for matching calculations.
        
        Returns:
            8-dimensional vector for archetype similarity.
        """
        return np.array([
            self.big_five.get("openness", 0.5),
            self.big_five.get("conscientiousness", 0.5),
            self.big_five.get("extraversion", 0.5),
            self.big_five.get("agreeableness", 0.5),
            1 - self.big_five.get("neuroticism", 0.5),  # Convert to stability
            1.0 if self.regulatory_focus == "promotion" else 0.0,
            self.price_sensitivity,
            self.information_seeking
        ])
    
    def match_user(self, user_profile: Dict[str, float]) -> float:
        """
        Compute match score with a user profile.
        
        Args:
            user_profile: User's psychological profile from Cold Start (#13)
            
        Returns:
            Match score between 0 and 1.
        """
        archetype_vec = self.to_vector()
        
        user_vec = np.array([
            user_profile.get("openness", 0.5),
            user_profile.get("conscientiousness", 0.5),
            user_profile.get("extraversion", 0.5),
            user_profile.get("agreeableness", 0.5),
            1 - user_profile.get("neuroticism", 0.5),
            user_profile.get("regulatory_focus_promotion", 0.5),
            user_profile.get("price_sensitivity", 0.5),
            user_profile.get("information_seeking", 0.5)
        ])
        
        # Cosine similarity
        norm_a = np.linalg.norm(archetype_vec)
        norm_b = np.linalg.norm(user_vec)
        
        if norm_a == 0 or norm_b == 0:
            return 0.5
        
        similarity = np.dot(archetype_vec, user_vec) / (norm_a * norm_b)
        
        # Convert from [-1, 1] to [0, 1]
        return (similarity + 1) / 2


class ArchetypeMatchResult(BaseModel):
    """Result of matching a user to archetypes."""


---

## 9. Competitor Intelligence Models

```python
# =============================================================================
# ADAM Enhancement #14: Competitor Intelligence Models
# Location: adam/brand_intelligence/models/competitor.py
# =============================================================================

"""
Competitor analysis models for psychological positioning.
"""

from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Literal
from datetime import datetime
from uuid import uuid4


class CompetitorProfile(BaseModel):
    """Psychological positioning of a competitor."""
    
    competitor_id: str = Field(default_factory=lambda: f"comp_{uuid4().hex[:12]}")
    competitor_name: str
    category: str
    
    regulatory_focus: Literal["promotion", "prevention", "balanced"]
    construal_tendency: Literal["abstract", "concrete", "mixed"]
    
    primary_appeals: List[str] = Field(default_factory=list)
    common_frames: List[str] = Field(default_factory=list)
    tone_profile: Dict[str, float] = Field(default_factory=dict)
    personality_vector: List[float] = Field(default_factory=list)
    
    perceived_tier: Literal["premium", "mid-market", "value", "niche"]
    key_differentiators: List[str] = Field(default_factory=list)
    
    position_x: float = Field(default=0.0)
    position_y: float = Field(default=0.0)
    
    underserved_segments: List[str] = Field(default_factory=list)
    messaging_gaps: List[str] = Field(default_factory=list)
    
    last_analyzed: datetime = Field(default_factory=datetime.utcnow)
    data_quality: float = Field(default=0.5, ge=0, le=1)


class CompetitiveLandscape(BaseModel):
    """Complete competitive landscape for a brand."""
    
    brand_id: str
    category: str
    competitors: List[CompetitorProfile] = Field(default_factory=list)
    
    brand_position_x: float
    brand_position_y: float
    
    whitespace_opportunities: List[Dict[str, Any]] = Field(default_factory=list)
    positioning_recommendations: List[str] = Field(default_factory=list)
    differentiation_score: float = Field(ge=0, le=1)
    
    analyzed_at: datetime = Field(default_factory=datetime.utcnow)
```

---

## 10. Brand-User Match Models

```python
# =============================================================================
# ADAM Enhancement #14: Brand-User Match Models
# Location: adam/brand_intelligence/models/match.py
# =============================================================================

"""
Models for brand-user psychological matching results.
"""

from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import datetime
from uuid import uuid4


class MechanismRecommendation(BaseModel):
    """Recommended cognitive mechanism with effectiveness score."""
    
    mechanism_id: str
    mechanism_name: str
    effectiveness_score: float = Field(ge=0, le=1)
    confidence: float = Field(ge=0, le=1)
    
    alpha: float
    beta: float
    sample_size: int
    rationale: str = ""


class FrameRecommendation(BaseModel):
    """Recommended message framing."""
    
    frame_type: str
    frame_name: str
    fit_score: float = Field(ge=0, le=1)
    example_phrasing: str = ""


class BrandUserMatchResult(BaseModel):
    """Complete result of matching a brand profile to a user profile."""
    
    match_id: str = Field(default_factory=lambda: f"match_{uuid4().hex[:12]}")
    brand_id: str
    user_id: str
    request_id: Optional[str] = None
    
    # Match scores
    overall_match_score: float = Field(ge=0, le=1)
    personality_alignment: float = Field(ge=0, le=1)
    regulatory_fit: float = Field(ge=0, le=1)
    construal_fit: float = Field(ge=0, le=1)
    value_alignment: float = Field(ge=0, le=1)
    archetype_fit: float = Field(ge=0, le=1)
    mechanism_history_score: float = Field(default=0.5, ge=0, le=1)
    
    # Recommendations
    recommended_archetype: str
    recommended_archetype_name: str
    archetype_match_score: float = Field(ge=0, le=1)
    
    recommended_mechanisms: List[MechanismRecommendation] = Field(default_factory=list)
    recommended_frame: str
    frame_recommendations: List[FrameRecommendation] = Field(default_factory=list)
    recommended_tone: str
    recommended_appeals: List[str] = Field(default_factory=list)
    
    brand_voice: Optional[Dict[str, Any]] = None
    messaging_constraints: Optional[Dict[str, Any]] = None
    
    # Confidence
    match_confidence: float = Field(ge=0, le=1)
    brand_profile_confidence: float = Field(ge=0, le=1)
    user_profile_confidence: float = Field(ge=0, le=1)
    data_tier: int = Field(ge=0, le=5)
    
    # Metadata
    computed_at: datetime = Field(default_factory=datetime.utcnow)
    computation_time_ms: float = 0.0
    cache_hit: bool = False
    awaiting_outcome: bool = True
    
    @property
    def top_mechanism(self) -> Optional[str]:
        if self.recommended_mechanisms:
            return self.recommended_mechanisms[0].mechanism_id
        return None
    
    @property
    def mechanism_priors(self) -> Dict[str, float]:
        return {m.mechanism_id: m.effectiveness_score for m in self.recommended_mechanisms}
    
    def to_learning_signal(self) -> Dict[str, Any]:
        return {
            "signal_type": "brand_match",
            "match_id": self.match_id,
            "brand_id": self.brand_id,
            "user_id": self.user_id,
            "match_score": self.overall_match_score,
            "mechanisms_recommended": [m.mechanism_id for m in self.recommended_mechanisms],
            "mechanism_priors": self.mechanism_priors,
            "confidence": self.match_confidence,
            "data_tier": self.data_tier,
            "timestamp": self.computed_at.isoformat()
        }
```

---

## 11. Learning Signal Models

```python
# =============================================================================
# ADAM Enhancement #14: Learning Signal Models
# Location: adam/brand_intelligence/models/learning.py
# =============================================================================

"""
Learning signal models for cross-component communication with Gradient Bridge (#06).
"""

from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum
from uuid import uuid4
import numpy as np


class BrandLearningSignalType(str, Enum):
    PROFILE_CREATED = "brand_profile_created"
    PROFILE_UPDATED = "brand_profile_updated"
    MATCH_COMPUTED = "brand_match_computed"
    MECHANISM_RECOMMENDED = "brand_mechanism_recommended"
    CONVERSION_OUTCOME = "conversion_outcome"
    MECHANISM_EFFECTIVENESS = "mechanism_effectiveness"
    CREDIT_ATTRIBUTION = "credit_attribution"


class BrandMechanismPrior(BaseModel):
    """Bayesian prior for brand-mechanism effectiveness using Beta distribution."""
    
    brand_id: str
    mechanism_id: str
    alpha: float = Field(default=1.0, ge=0)
    beta: float = Field(default=1.0, ge=0)
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    update_count: int = 0
    
    @property
    def mean(self) -> float:
        return self.alpha / (self.alpha + self.beta)
    
    @property
    def variance(self) -> float:
        a, b = self.alpha, self.beta
        return (a * b) / ((a + b) ** 2 * (a + b + 1))
    
    @property
    def confidence(self) -> float:
        sample_size = self.alpha + self.beta - 2
        return min(1.0, sample_size / 100)
    
    @property
    def sample_size(self) -> int:
        return int(self.alpha + self.beta - 2)
    
    def update(self, outcome: float, credit: float = 1.0) -> "BrandMechanismPrior":
        """Bayesian update with observed outcome."""
        if outcome > 0.5:
            new_alpha = self.alpha + credit * outcome
            new_beta = self.beta
        else:
            new_alpha = self.alpha
            new_beta = self.beta + credit * (1 - outcome)
        
        return BrandMechanismPrior(
            brand_id=self.brand_id,
            mechanism_id=self.mechanism_id,
            alpha=new_alpha,
            beta=new_beta,
            update_count=self.update_count + 1
        )
    
    def sample(self) -> float:
        """Thompson Sampling: draw from posterior."""
        return np.random.beta(self.alpha, self.beta)


class BrandLearningState(BaseModel):
    """Complete learning state for a brand."""
    
    brand_id: str
    mechanism_priors: Dict[str, BrandMechanismPrior] = Field(default_factory=dict)
    
    total_impressions: int = 0
    total_conversions: int = 0
    total_learning_signals: int = 0
    
    signals_last_24h: int = 0
    signals_last_7d: int = 0
    
    best_mechanism: Optional[str] = None
    best_mechanism_effectiveness: float = 0.0
    category_prior_weight: float = 0.3
    
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    
    def get_mechanism_effectiveness(self, mechanism_id: str) -> float:
        if mechanism_id in self.mechanism_priors:
            return self.mechanism_priors[mechanism_id].mean
        return 0.5
    
    def get_mechanism_confidence(self, mechanism_id: str) -> float:
        if mechanism_id in self.mechanism_priors:
            return self.mechanism_priors[mechanism_id].confidence
        return 0.0
    
    def update_best_mechanism(self):
        if not self.mechanism_priors:
            return
        best = max(self.mechanism_priors.items(), key=lambda x: x[1].mean)
        self.best_mechanism = best[0]
        self.best_mechanism_effectiveness = best[1].mean
```

---

# SECTION C: CATEGORY TAXONOMY & ARCHETYPES

## 12. Hierarchical Category System

```python
# =============================================================================
# ADAM Enhancement #14: Category Taxonomy
# Location: adam/brand_intelligence/taxonomy/categories.py
# =============================================================================

"""
Hierarchical category system with psychological priors.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class CategoryPriors:
    """Psychological priors for a category."""
    
    category_id: str
    category_name: str
    parent_category: Optional[str]
    
    promotion_tendency: float
    abstract_tendency: float
    involvement_level: float
    decision_time_days: Tuple[float, float]
    
    primary_values: List[str]
    archetype_weights: Dict[str, float] = field(default_factory=dict)
    mechanism_priors: Dict[str, float] = field(default_factory=dict)


class CategoryTaxonomy:
    """Complete category taxonomy with psychological priors."""
    
    DEFAULT_MECHANISM_PRIORS = {
        "CONSTRUAL_LEVEL_DYNAMICS": 0.5,
        "REGULATORY_FOCUS": 0.5,
        "AUTOMATIC_EVALUATION": 0.5,
        "WANTING_LIKING_DISSOCIATION": 0.5,
        "MIMETIC_DESIRE": 0.5,
        "ATTENTION_DYNAMICS": 0.5,
        "TEMPORAL_CONSTRUAL": 0.5,
        "IDENTITY_CONSTRUCTION": 0.5,
        "EVOLUTIONARY_ADAPTATIONS": 0.5,
    }
    
    TAXONOMY: Dict[str, CategoryPriors] = {
        "consumer_goods": CategoryPriors(
            category_id="cat_001",
            category_name="Consumer Goods",
            parent_category=None,
            promotion_tendency=0.55,
            abstract_tendency=0.45,
            involvement_level=0.4,
            decision_time_days=(0.1, 7),
            primary_values=["hedonism", "stimulation"],
            mechanism_priors={
                "AUTOMATIC_EVALUATION": 0.65,
                "WANTING_LIKING_DISSOCIATION": 0.6,
                "MIMETIC_DESIRE": 0.55,
            }
        ),
        "financial_services": CategoryPriors(
            category_id="cat_002",
            category_name="Financial Services",
            parent_category=None,
            promotion_tendency=0.45,
            abstract_tendency=0.6,
            involvement_level=0.85,
            decision_time_days=(7, 90),
            primary_values=["security", "achievement", "power"],
            mechanism_priors={
                "REGULATORY_FOCUS": 0.75,
                "TEMPORAL_CONSTRUAL": 0.7,
                "CONSTRUAL_LEVEL_DYNAMICS": 0.65,
            }
        ),
        "technology": CategoryPriors(
            category_id="cat_003",
            category_name="Technology",
            parent_category=None,
            promotion_tendency=0.65,
            abstract_tendency=0.55,
            involvement_level=0.6,
            decision_time_days=(1, 30),
            primary_values=["achievement", "stimulation", "self_direction"],
            mechanism_priors={
                "IDENTITY_CONSTRUCTION": 0.7,
                "ATTENTION_DYNAMICS": 0.65,
                "CONSTRUAL_LEVEL_DYNAMICS": 0.6,
            }
        ),
        "healthcare": CategoryPriors(
            category_id="cat_004",
            category_name="Healthcare",
            parent_category=None,
            promotion_tendency=0.35,
            abstract_tendency=0.4,
            involvement_level=0.9,
            decision_time_days=(1, 60),
            primary_values=["security", "benevolence"],
            mechanism_priors={
                "REGULATORY_FOCUS": 0.8,
                "EVOLUTIONARY_ADAPTATIONS": 0.75,
                "TEMPORAL_CONSTRUAL": 0.6,
            }
        ),
        "automotive": CategoryPriors(
            category_id="cat_005",
            category_name="Automotive",
            parent_category=None,
            promotion_tendency=0.5,
            abstract_tendency=0.5,
            involvement_level=0.95,
            decision_time_days=(30, 180),
            primary_values=["power", "security", "stimulation"],
            mechanism_priors={
                "IDENTITY_CONSTRUCTION": 0.75,
                "REGULATORY_FOCUS": 0.65,
                "WANTING_LIKING_DISSOCIATION": 0.6,
            }
        ),
        "luxury": CategoryPriors(
            category_id="cat_009",
            category_name="Luxury",
            parent_category=None,
            promotion_tendency=0.75,
            abstract_tendency=0.7,
            involvement_level=0.85,
            decision_time_days=(7, 90),
            primary_values=["power", "hedonism", "achievement"],
            mechanism_priors={
                "IDENTITY_CONSTRUCTION": 0.85,
                "MIMETIC_DESIRE": 0.8,
                "WANTING_LIKING_DISSOCIATION": 0.75,
            }
        ),
        "consumer_electronics": CategoryPriors(
            category_id="cat_101",
            category_name="Consumer Electronics",
            parent_category="consumer_goods",
            promotion_tendency=0.65,
            abstract_tendency=0.5,
            involvement_level=0.55,
            decision_time_days=(1, 14),
            primary_values=["achievement", "stimulation"],
            mechanism_priors={
                "IDENTITY_CONSTRUCTION": 0.7,
                "ATTENTION_DYNAMICS": 0.65,
                "MIMETIC_DESIRE": 0.6,
            }
        ),
    }
    
    def get_category(self, category_id: str) -> Optional[CategoryPriors]:
        if category_id in self.TAXONOMY:
            return self.TAXONOMY[category_id]
        for cat in self.TAXONOMY.values():
            if cat.category_name.lower() == category_id.lower():
                return cat
        return None
    
    def get_inherited_mechanism_priors(self, category_id: str) -> Dict[str, float]:
        priors = self.DEFAULT_MECHANISM_PRIORS.copy()
        cat = self.get_category(category_id)
        if cat:
            priors.update(cat.mechanism_priors)
        return priors
```

---

# SECTION H: EVENT BUS INTEGRATION (#31)

## 33. Brand Intelligence Events

```python
# =============================================================================
# ADAM Enhancement #14: Event Bus Integration
# Location: adam/brand_intelligence/events/definitions.py
# =============================================================================

"""
Kafka event definitions for Brand Intelligence cross-component learning.
"""

from pydantic import BaseModel, Field
from typing import Dict, List, Optional
from datetime import datetime
from enum import Enum
from uuid import uuid4


class BrandEventType(str, Enum):
    PROFILE_CREATED = "brand.profile.created"
    PROFILE_UPDATED = "brand.profile.updated"
    MATCH_COMPUTED = "brand.match.computed"
    MECHANISM_USED = "brand.mechanism.used"
    EFFECTIVENESS_UPDATED = "brand.effectiveness.updated"
    CACHE_INVALIDATED = "brand.cache.invalidated"


# Kafka Topic Definitions
BRAND_INTELLIGENCE_TOPICS = {
    "adam.brands.profiles": {
        "partitions": 12,
        "replication_factor": 3,
        "retention_ms": 604800000,
        "event_types": [BrandEventType.PROFILE_CREATED, BrandEventType.PROFILE_UPDATED]
    },
    "adam.brands.matches": {
        "partitions": 24,
        "replication_factor": 3,
        "retention_ms": 172800000,
        "event_types": [BrandEventType.MATCH_COMPUTED]
    },
    "adam.brands.learning": {
        "partitions": 12,
        "replication_factor": 3,
        "retention_ms": 604800000,
        "event_types": [BrandEventType.MECHANISM_USED, BrandEventType.EFFECTIVENESS_UPDATED]
    },
}


class BrandMatchEvent(BaseModel):
    """Event for brand-user match computation."""
    
    event_type: BrandEventType = BrandEventType.MATCH_COMPUTED
    event_id: str = Field(default_factory=lambda: f"evt_{uuid4().hex[:12]}")
    
    match_id: str
    decision_id: Optional[str] = None
    brand_id: str
    user_id: str
    
    overall_match_score: float
    mechanisms_recommended: List[str]
    mechanism_priors: Dict[str, float]
    recommended_frame: str
    
    match_confidence: float
    user_data_tier: int
    awaiting_outcome: bool = True
    
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class MechanismUsedEvent(BaseModel):
    """Event when a mechanism is used for ad delivery."""
    
    event_type: BrandEventType = BrandEventType.MECHANISM_USED
    event_id: str = Field(default_factory=lambda: f"evt_{uuid4().hex[:12]}")
    
    decision_id: str
    brand_id: str
    user_id: str
    ad_id: str
    
    mechanism_id: str
    mechanism_prior: float
    frame_used: str
    match_score: float
    
    mechanisms_not_used: List[str] = Field(default_factory=list)
    awaiting_outcome: bool = True
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class BrandIntelligenceEventProducer:
    """Kafka producer for Brand Intelligence events."""
    
    def __init__(self, kafka_producer, metrics_client):
        self.producer = kafka_producer
        self.metrics = metrics_client
    
    async def emit_match_computed(self, match_result, decision_id: Optional[str] = None):
        event = BrandMatchEvent(
            match_id=match_result.match_id,
            decision_id=decision_id,
            brand_id=match_result.brand_id,
            user_id=match_result.user_id,
            overall_match_score=match_result.overall_match_score,
            mechanisms_recommended=[m.mechanism_id for m in match_result.recommended_mechanisms],
            mechanism_priors=match_result.mechanism_priors,
            recommended_frame=match_result.recommended_frame,
            match_confidence=match_result.match_confidence,
            user_data_tier=match_result.data_tier
        )
        
        await self.producer.send(
            topic="adam.brands.matches",
            key=match_result.brand_id,
            value=event.dict()
        )
        self.metrics.increment("brand_intel_events_emitted", {"event_type": "match_computed"})
```

---

# SECTION I: CACHE INTEGRATION (#31)

## 37. Multi-Level Cache Strategy

```python
# =============================================================================
# ADAM Enhancement #14: Cache Integration
# Location: adam/brand_intelligence/cache/strategy.py
# =============================================================================

"""
Multi-level cache strategy for <5ms brand profile and match retrieval.
L1 (process memory) → L2 (Redis) → L3 (Feature Store)
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Any
import json
import redis.asyncio as redis


@dataclass
class CacheConfig:
    l1_max_size: int = 1000
    l1_ttl_seconds: int = 60
    l2_profile_ttl_seconds: int = 86400
    l2_match_ttl_seconds: int = 300
    profile_prefix: str = "brand:profile:"
    match_prefix: str = "brand:match:"
    mechanism_prefix: str = "brand:mechanism:"


class L1MemoryCache:
    """In-process LRU cache with ~1ms latency."""
    
    def __init__(self, max_size: int = 1000, default_ttl: int = 60):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: Dict[str, Dict] = {}
        self._access_order: List[str] = []
    
    def get(self, key: str) -> Optional[Any]:
        entry = self._cache.get(key)
        if entry is None:
            return None
        if (datetime.utcnow() - entry["created"]).total_seconds() > entry["ttl"]:
            self._evict(key)
            return None
        if key in self._access_order:
            self._access_order.remove(key)
        self._access_order.append(key)
        return entry["value"]
    
    def set(self, key: str, value: Any, ttl: int = None):
        while len(self._cache) >= self.max_size:
            oldest = self._access_order.pop(0)
            self._evict(oldest)
        self._cache[key] = {"value": value, "created": datetime.utcnow(), "ttl": ttl or self.default_ttl}
        self._access_order.append(key)
    
    def _evict(self, key: str):
        self._cache.pop(key, None)
        if key in self._access_order:
            self._access_order.remove(key)
    
    def invalidate_prefix(self, prefix: str):
        for key in [k for k in self._cache if k.startswith(prefix)]:
            self._evict(key)


class BrandCacheCoordinator:
    """Coordinates multi-level caching for Brand Intelligence."""
    
    def __init__(self, config: CacheConfig, redis_client: redis.Redis, feature_store, metrics):
        self.config = config
        self.l1 = L1MemoryCache(config.l1_max_size, config.l1_ttl_seconds)
        self.redis = redis_client
        self.feature_store = feature_store
        self.metrics = metrics
    
    async def get_brand_profile(self, brand_id: str) -> Optional[Dict]:
        key = f"{self.config.profile_prefix}{brand_id}"
        
        # L1 check
        result = self.l1.get(key)
        if result:
            self.metrics.increment("brand_cache_hit", {"level": "l1"})
            return result
        
        # L2 check
        data = await self.redis.get(key)
        if data:
            result = json.loads(data)
            self.metrics.increment("brand_cache_hit", {"level": "l2"})
            self.l1.set(key, result)
            return result
        
        # L3 check (Feature Store)
        result = await self.feature_store.get_brand_features(brand_id)
        if result:
            self.metrics.increment("brand_cache_hit", {"level": "l3"})
            await self.redis.setex(key, self.config.l2_profile_ttl_seconds, json.dumps(result, default=str))
            self.l1.set(key, result)
            return result
        
        self.metrics.increment("brand_cache_miss")
        return None
    
    async def set_brand_profile(self, brand_id: str, profile: Dict):
        key = f"{self.config.profile_prefix}{brand_id}"
        self.l1.set(key, profile)
        await self.redis.setex(key, self.config.l2_profile_ttl_seconds, json.dumps(profile, default=str))
        await self.feature_store.set_brand_features(brand_id, profile)
    
    async def invalidate_for_brand(self, brand_id: str):
        self.l1.invalidate_prefix(f"{self.config.profile_prefix}{brand_id}")
        self.l1.invalidate_prefix(f"{self.config.match_prefix}{brand_id}")
        self.l1.invalidate_prefix(f"{self.config.mechanism_prefix}{brand_id}")
        
        for pattern in [f"{self.config.profile_prefix}{brand_id}*", f"{self.config.match_prefix}{brand_id}:*"]:
            cursor = 0
            while True:
                cursor, keys = await self.redis.scan(cursor, match=pattern, count=100)
                if keys:
                    await self.redis.delete(*keys)
                if cursor == 0:
                    break
        
        self.metrics.increment("brand_cache_invalidations", {"brand_id": brand_id})
```

---

# SECTION K: GRADIENT BRIDGE INTEGRATION (#06)

## 44. Learning Signal Emission

```python
# =============================================================================
# ADAM Enhancement #14: Gradient Bridge Integration
# Location: adam/brand_intelligence/learning/gradient_bridge.py
# =============================================================================

"""
Integration with Gradient Bridge (#06) for cross-component learning.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from pydantic import BaseModel, Field

from ..models.learning import BrandMechanismPrior


class BrandLearningSignal(BaseModel):
    """Learning signal emitted to Gradient Bridge."""
    
    signal_type: str = "brand_intelligence"
    signal_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    decision_id: str
    brand_id: str
    user_id: str
    
    match_score: float
    mechanism_recommended: str
    mechanism_prior: float
    frame_recommended: str
    
    alternative_mechanisms: List[str] = Field(default_factory=list)
    alternative_priors: Dict[str, float] = Field(default_factory=dict)
    
    match_confidence: float
    brand_profile_confidence: float
    user_profile_confidence: float
    
    awaiting_outcome: bool = True


class GradientBridgeConnector:
    """Connector to Gradient Bridge for learning signal exchange."""
    
    def __init__(self, gradient_bridge_client, event_producer, cache_coordinator, neo4j_driver, metrics):
        self.bridge = gradient_bridge_client
        self.producer = event_producer
        self.cache = cache_coordinator
        self.neo4j = neo4j_driver
        self.metrics = metrics
    
    async def emit_match_signal(self, match_result, decision_id: str) -> str:
        """Emit learning signal for a brand-user match decision."""
        signal = BrandLearningSignal(
            signal_id=f"brand_sig_{match_result.match_id}",
            decision_id=decision_id,
            brand_id=match_result.brand_id,
            user_id=match_result.user_id,
            match_score=match_result.overall_match_score,
            mechanism_recommended=match_result.top_mechanism or "",
            mechanism_prior=match_result.mechanism_priors.get(match_result.top_mechanism, 0.5) if match_result.top_mechanism else 0.5,
            frame_recommended=match_result.recommended_frame,
            match_confidence=match_result.match_confidence,
            brand_profile_confidence=match_result.brand_profile_confidence,
            user_profile_confidence=match_result.user_profile_confidence
        )
        
        await self.bridge.register_learning_signal(signal.dict())
        await self.producer.emit_match_computed(match_result, decision_id)
        self.metrics.increment("brand_learning_signals_emitted")
        
        return signal.signal_id
    
    async def process_outcome(self, decision_id: str, outcome_type: str, outcome_value: float, credit_attribution: Dict[str, float]):
        """Process outcome signal from Gradient Bridge."""
        match_context = await self._get_match_context(decision_id)
        if not match_context:
            return
        
        brand_id = match_context["brand_id"]
        mechanism_id = match_context["mechanism_used"]
        brand_credit = credit_attribution.get("brand_intelligence", 0.0)
        mechanism_credit = credit_attribution.get("mechanism", 0.0)
        
        await self._update_mechanism_effectiveness(
            brand_id=brand_id,
            mechanism_id=mechanism_id,
            outcome_value=outcome_value,
            credit=brand_credit + mechanism_credit,
            decision_id=decision_id
        )
        
        await self.cache.invalidate_for_brand(brand_id)
        self.metrics.increment("brand_outcomes_processed", {"outcome_type": outcome_type})
    
    async def get_empirical_priors(self, brand_id: str) -> Dict[str, BrandMechanismPrior]:
        """Get empirical mechanism priors from learning history."""
        query = """
        MATCH (b:Brand {brand_id: $brand_id})-[eff:MECHANISM_EFFECTIVENESS]->(m:CognitiveMechanism)
        RETURN m.mechanism_id as mechanism_id, eff.alpha as alpha, eff.beta as beta
        """
        async with self.neo4j.session() as session:
            result = await session.run(query, {"brand_id": brand_id})
            records = await result.data()
        
        return {
            r["mechanism_id"]: BrandMechanismPrior(
                brand_id=brand_id,
                mechanism_id=r["mechanism_id"],
                alpha=r["alpha"],
                beta=r["beta"]
            )
            for r in records
        }
    
    async def _update_mechanism_effectiveness(self, brand_id: str, mechanism_id: str, outcome_value: float, credit: float, decision_id: str):
        """Update mechanism effectiveness with Bayesian update."""
        priors = await self.get_empirical_priors(brand_id)
        current = priors.get(mechanism_id, BrandMechanismPrior(brand_id=brand_id, mechanism_id=mechanism_id))
        updated = current.update(outcome_value, credit)
        
        query = """
        MATCH (b:Brand {brand_id: $brand_id})
        MERGE (m:CognitiveMechanism {mechanism_id: $mechanism_id})
        MERGE (b)-[eff:MECHANISM_EFFECTIVENESS]->(m)
        SET eff.alpha = $alpha, eff.beta = $beta, eff.mean = $mean, eff.last_updated = datetime()
        """
        async with self.neo4j.session() as session:
            await session.run(query, {
                "brand_id": brand_id,
                "mechanism_id": mechanism_id,
                "alpha": updated.alpha,
                "beta": updated.beta,
                "mean": updated.mean
            })
    
    async def _get_match_context(self, decision_id: str) -> Optional[Dict]:
        query = """
        MATCH (d:Decision {decision_id: $decision_id})-[:USED_BRAND_MATCH]->(bm:BrandMatch)
        RETURN bm.brand_id as brand_id, bm.mechanism_used as mechanism_used
        """
        async with self.neo4j.session() as session:
            result = await session.run(query, {"decision_id": decision_id})
            record = await result.single()
        return dict(record) if record else None
```

---

# SECTION L: NEO4J SCHEMA

## 48. Brand Intelligence Graph Model

```cypher
// =============================================================================
// ADAM Enhancement #14: Neo4j Schema
// =============================================================================

// CONSTRAINTS
CREATE CONSTRAINT brand_id_unique IF NOT EXISTS FOR (b:Brand) REQUIRE b.brand_id IS UNIQUE;
CREATE CONSTRAINT archetype_id_unique IF NOT EXISTS FOR (a:CustomerArchetype) REQUIRE a.archetype_id IS UNIQUE;
CREATE CONSTRAINT mechanism_id_unique IF NOT EXISTS FOR (m:CognitiveMechanism) REQUIRE m.mechanism_id IS UNIQUE;

// INDEXES
CREATE INDEX brand_category_idx IF NOT EXISTS FOR (b:Brand) ON (b.category);
CREATE INDEX brand_confidence_idx IF NOT EXISTS FOR (b:Brand) ON (b.confidence_score);

CREATE VECTOR INDEX brand_embedding_idx IF NOT EXISTS
FOR (b:Brand) ON (b.embedding)
OPTIONS {indexConfig: {`vector.dimensions`: 384, `vector.similarity_function`: 'cosine'}};

// KEY RELATIONSHIPS:
// (b:Brand)-[:TARGETS {fit_score, priority}]->(a:CustomerArchetype)
// (b:Brand)-[:MECHANISM_EFFECTIVENESS {alpha, beta, mean, sample_size, last_updated}]->(m:CognitiveMechanism)
// (b:Brand)-[:IN_CATEGORY {is_primary}]->(cat:Category)
// (d:Decision)-[:USED_BRAND_MATCH {match_id, match_score, mechanism_used}]->(b:Brand)

// INITIAL DATA: 9 COGNITIVE MECHANISMS
MERGE (m1:CognitiveMechanism {mechanism_id: "CONSTRUAL_LEVEL_DYNAMICS"})
SET m1.mechanism_name = "Construal Level Dynamics";

MERGE (m2:CognitiveMechanism {mechanism_id: "REGULATORY_FOCUS"})
SET m2.mechanism_name = "Regulatory Focus";

MERGE (m3:CognitiveMechanism {mechanism_id: "AUTOMATIC_EVALUATION"})
SET m3.mechanism_name = "Automatic Evaluation";

MERGE (m4:CognitiveMechanism {mechanism_id: "WANTING_LIKING_DISSOCIATION"})
SET m4.mechanism_name = "Wanting-Liking Dissociation";

MERGE (m5:CognitiveMechanism {mechanism_id: "MIMETIC_DESIRE"})
SET m5.mechanism_name = "Mimetic Desire";

MERGE (m6:CognitiveMechanism {mechanism_id: "ATTENTION_DYNAMICS"})
SET m6.mechanism_name = "Attention Dynamics";

MERGE (m7:CognitiveMechanism {mechanism_id: "TEMPORAL_CONSTRUAL"})
SET m7.mechanism_name = "Temporal Construal";

MERGE (m8:CognitiveMechanism {mechanism_id: "IDENTITY_CONSTRUCTION"})
SET m8.mechanism_name = "Identity Construction";

MERGE (m9:CognitiveMechanism {mechanism_id: "EVOLUTIONARY_ADAPTATIONS"})
SET m9.mechanism_name = "Evolutionary Adaptations";
```

---

# SECTION N: FASTAPI SERVICE

## 56. Brand Profile Endpoints

```python
# =============================================================================
# ADAM Enhancement #14: FastAPI Service
# Location: adam/brand_intelligence/api/service.py
# =============================================================================

"""
FastAPI service for Brand Intelligence REST endpoints.
"""

from fastapi import FastAPI, HTTPException, Depends, Query, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import datetime

app = FastAPI(title="ADAM Brand Intelligence API", version="3.0.0")


class AdvertiserIntakeRequest(BaseModel):
    brand_name: str
    category: str
    sub_categories: List[str] = Field(default_factory=list)
    target_audience: Optional[str] = None
    brand_values: List[str] = Field(default_factory=list)
    voice_pace: Optional[str] = None
    voice_energy: Optional[str] = None
    prohibited_content: List[str] = Field(default_factory=list)


class MatchRequest(BaseModel):
    brand_id: str
    user_id: str
    user_profile: Dict[str, Any]
    decision_id: Optional[str] = None
    mechanism_count: int = Field(default=3, ge=1, le=9)
    include_voice: bool = True


class MatchResponse(BaseModel):
    match_id: str
    brand_id: str
    user_id: str
    overall_match_score: float
    personality_alignment: float
    regulatory_fit: float
    construal_fit: float
    recommended_archetype: str
    recommended_mechanisms: List[Dict[str, Any]]
    recommended_frame: str
    recommended_tone: str
    recommended_appeals: List[str]
    brand_voice: Optional[Dict[str, str]] = None
    match_confidence: float
    computation_time_ms: float


@app.post("/v1/brands")
async def create_brand_profile(intake: AdvertiserIntakeRequest, background_tasks: BackgroundTasks):
    """Create a new brand psychological profile."""
    # Implementation: triggers profile generation pipeline
    pass


@app.get("/v1/brands/{brand_id}")
async def get_brand_profile(brand_id: str):
    """Get brand psychological profile by ID."""
    pass


@app.post("/v1/brands/{brand_id}/refresh")
async def refresh_brand_profile(brand_id: str, background_tasks: BackgroundTasks):
    """Trigger full profile refresh from all data sources."""
    pass


@app.post("/v1/match", response_model=MatchResponse)
async def compute_match(request: MatchRequest):
    """
    Compute brand-user match score with recommendations.
    Primary endpoint consumed by ADAM inference engine.
    """
    import time
    start = time.perf_counter()
    
    # Implementation: compute match using Brand Intelligence engine
    # Returns mechanism recommendations, frame selection, voice parameters
    
    computation_time = (time.perf_counter() - start) * 1000
    pass


@app.post("/v1/match/batch")
async def compute_batch_match(brand_id: str, user_profiles: List[Dict[str, Any]]):
    """Batch compute matches for multiple users."""
    pass


@app.get("/v1/brands/{brand_id}/analytics")
async def get_brand_analytics(brand_id: str):
    """Get brand performance analytics including mechanism effectiveness."""
    pass


@app.get("/v1/brands/{brand_id}/mechanisms")
async def get_mechanism_effectiveness(brand_id: str):
    """Get mechanism effectiveness priors for a brand."""
    pass


@app.get("/v1/categories")
async def list_categories():
    """List all supported categories with psychological priors."""
    pass


@app.get("/v1/categories/{category_id}/archetypes")
async def get_category_archetypes(category_id: str):
    """Get customer archetypes for a category."""
    pass


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "brand-intelligence", "version": "3.0.0"}
```

---

# SECTION O: PROMETHEUS METRICS

## 60. Profile Metrics

```python
# =============================================================================
# ADAM Enhancement #14: Prometheus Metrics
# Location: adam/brand_intelligence/metrics/prometheus.py
# =============================================================================

"""
Prometheus metrics for Brand Intelligence observability.
"""

from prometheus_client import Counter, Histogram, Gauge


# PROFILE METRICS
PROFILE_CREATED = Counter("adam_brand_intel_profiles_created_total", "Total brand profiles created", ["category"])
PROFILE_GENERATION_DURATION = Histogram(
    "adam_brand_intel_profile_generation_seconds", "Time to generate brand profile",
    ["category"], buckets=[0.5, 1, 2, 5, 10, 30, 60, 120, 300]
)
PROFILE_CONFIDENCE = Histogram(
    "adam_brand_intel_profile_confidence", "Distribution of profile confidence scores",
    ["category"], buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
)

# MATCHING METRICS
MATCH_REQUESTS = Counter("adam_brand_intel_match_requests_total", "Total match requests", ["brand_category"])
MATCH_DURATION = Histogram(
    "adam_brand_intel_match_duration_ms", "Time to compute brand-user match",
    ["cache_hit"], buckets=[1, 2, 3, 5, 10, 20, 50, 100, 200]
)
MATCH_SCORE_DISTRIBUTION = Histogram(
    "adam_brand_intel_match_score", "Distribution of match scores",
    ["brand_category"], buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
)
MECHANISM_RECOMMENDATIONS = Counter(
    "adam_brand_intel_mechanism_recommendations_total", "Mechanisms recommended",
    ["mechanism_id", "brand_category"]
)

# LEARNING METRICS
LEARNING_SIGNALS_EMITTED = Counter("adam_brand_intel_learning_signals_emitted_total", "Learning signals emitted", ["signal_type"])
LEARNING_SIGNALS_CONSUMED = Counter("adam_brand_intel_learning_signals_consumed_total", "Learning signals consumed", ["signal_type"])
MECHANISM_EFFECTIVENESS_UPDATES = Counter(
    "adam_brand_intel_mechanism_effectiveness_updates_total", "Mechanism effectiveness updates",
    ["mechanism_id", "outcome_type"]
)
MECHANISM_EFFECTIVENESS_VALUE = Gauge(
    "adam_brand_intel_mechanism_effectiveness", "Current mechanism effectiveness",
    ["brand_id", "mechanism_id"]
)

# CACHE METRICS
CACHE_HITS = Counter("adam_brand_intel_cache_hits_total", "Cache hits", ["cache_type", "level"])
CACHE_MISSES = Counter("adam_brand_intel_cache_misses_total", "Cache misses", ["cache_type"])
CACHE_INVALIDATIONS = Counter("adam_brand_intel_cache_invalidations_total", "Cache invalidations", ["reason"])


class BrandIntelMetrics:
    """Centralized metrics collector."""
    
    def record_profile_created(self, category: str):
        PROFILE_CREATED.labels(category=category).inc()
    
    def record_match_duration(self, duration_ms: float, cache_hit: bool):
        MATCH_DURATION.labels(cache_hit=str(cache_hit).lower()).observe(duration_ms)
    
    def record_match_score(self, brand_category: str, score: float):
        MATCH_SCORE_DISTRIBUTION.labels(brand_category=brand_category).observe(score)
    
    def record_mechanism_recommendation(self, mechanism_id: str, brand_category: str):
        MECHANISM_RECOMMENDATIONS.labels(mechanism_id=mechanism_id, brand_category=brand_category).inc()
    
    def record_cache_hit(self, cache_type: str, level: str):
        CACHE_HITS.labels(cache_type=cache_type, level=level).inc()
    
    def record_cache_miss(self, cache_type: str):
        CACHE_MISSES.labels(cache_type=cache_type).inc()
    
    def set_mechanism_effectiveness(self, brand_id: str, mechanism_id: str, effectiveness: float):
        MECHANISM_EFFECTIVENESS_VALUE.labels(brand_id=brand_id, mechanism_id=mechanism_id).set(effectiveness)
```

---

# SECTION P: TESTING & OPERATIONS

## 67. Implementation Timeline

```yaml
# =============================================================================
# ADAM Enhancement #14: Implementation Timeline
# =============================================================================

implementation_timeline:
  total_duration: "12 weeks"
  team_size: "2-3 engineers"
  
  phases:
    phase_1_foundation:
      duration: "Weeks 1-3"
      focus: "Data models, Neo4j schema, configuration"
      deliverables:
        - "Pydantic data models"
        - "Neo4j schema with constraints and indexes"
        - "Category taxonomy (16+ categories)"
        - "Pre-built archetype library"
      success_criteria:
        - "All models pass validation tests"
        - "Neo4j queries < 50ms"
    
    phase_2_profile_engine:
      duration: "Weeks 4-6"
      focus: "Profile generation, data ingestion, Claude synthesis"
      deliverables:
        - "Amazon review connector"
        - "Psycholinguistic analyzer"
        - "Claude synthesis pipeline"
        - "Confidence scoring system"
      success_criteria:
        - "Profile generation < 5 minutes"
        - "95% profiles pass validation"
    
    phase_3_matching:
      duration: "Weeks 7-8"
      focus: "Brand-user matching, mechanism recommendations"
      deliverables:
        - "Multi-dimensional matcher"
        - "Mechanism recommendation engine"
        - "Frame selection algorithm"
      success_criteria:
        - "Match computation < 5ms (cached)"
        - "Match computation < 50ms (uncached)"
    
    phase_4_integration:
      duration: "Weeks 9-10"
      focus: "Event Bus, Cache, Feature Store, Gradient Bridge"
      deliverables:
        - "Kafka event producers/consumers"
        - "Multi-level cache (L1→L2→L3)"
        - "Gradient Bridge connector"
      success_criteria:
        - "Events flow end-to-end"
        - "Cache hit rate > 80%"
    
    phase_5_api_observability:
      duration: "Weeks 11-12"
      focus: "FastAPI service, Prometheus metrics"
      deliverables:
        - "Complete FastAPI service"
        - "Prometheus metrics"
        - "Grafana dashboards"
      success_criteria:
        - "API response times meet SLAs"
        - "All critical metrics tracked"

success_metrics:
  profile_quality:
    - metric: "Profile confidence score"
      target: "> 0.7 average"
    - metric: "Profile generation time"
      target: "< 5 minutes P95"
  
  matching_performance:
    - metric: "Match latency (cached)"
      target: "< 5ms P99"
    - metric: "Cache hit rate"
      target: "> 80%"
  
  learning_effectiveness:
    - metric: "Mechanism prediction accuracy"
      target: "> 65%"
    - metric: "Learning signal latency"
      target: "< 100ms"
  
  business_impact:
    - metric: "First-campaign CTR vs mature"
      target: "> 0.85x"
    - metric: "Time to effective targeting"
      target: "< 24 hours"
    - metric: "Brand onboarding time"
      target: "< 4 hours"

risks_and_mitigations:
  - risk: "Amazon API rate limiting"
    mitigation: "Exponential backoff, batch requests, aggressive caching"
  
  - risk: "Claude synthesis quality variance"
    mitigation: "Structured prompts, validation layer, confidence scoring"
  
  - risk: "Cache invalidation storms"
    mitigation: "Staggered invalidation, rate limiting, circuit breakers"
```

---

# INTEGRATION SUMMARY

## Cross-Component Connections

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│   BRAND INTELLIGENCE (#14) INTEGRATION MAP                                  │
│                                                                             │
│   UPSTREAM (Consumes From):                                                 │
│   ─────────────────────────                                                 │
│   #13 Cold Start     → User profiles for matching                          │
│   #21 Embeddings     → Brand vectors for similarity                        │
│   #30 Feature Store  → Real-time feature serving                           │
│   #31 Event Bus      → Outcome events for learning                         │
│                                                                             │
│   DOWNSTREAM (Provides To):                                                 │
│   ────────────────────────                                                  │
│   #15 Copy Generation → BrandVoice, MessagingConstraints, Mechanisms       │
│   #18 Explanation    → Brand match reasoning                               │
│   #28 WPP Ad Desk    → Brand archetypes, personality vectors               │
│                                                                             │
│   LEARNING LOOP (via #06 Gradient Bridge):                                  │
│   ─────────────────────────────────────────                                 │
│   Brand Match → Ad Served → Conversion → Credit Attribution →              │
│   → Mechanism Effectiveness Update → Cache Invalidation →                   │
│   → Next Request Uses Updated Priors                                        │
│                                                                             │
│   KEY LEARNING RELATIONSHIPS (Neo4j):                                       │
│   ──────────────────────────────────                                        │
│   (Brand)-[:MECHANISM_EFFECTIVENESS {alpha, beta, mean}]->(Mechanism)      │
│   (Decision)-[:USED_BRAND_MATCH {match_score, mechanism_used}]->(Brand)    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

*Enhancement #14 Complete (v3.0). Enterprise-grade Brand Intelligence Library with full cross-component learning integration, <5ms real-time serving via multi-level cache, comprehensive observability, and 12-week implementation roadmap.*

**Specification Size**: ~165KB  
**Components**: 68 sections across 16 major areas  
**Integration Points**: #06, #13, #15, #18, #21, #28, #30, #31  
**Target Latency**: <5ms cached, <50ms uncached  
**Learning**: Bayesian mechanism effectiveness with cross-brand transfer

---

# SECTION M: LANGGRAPH WORKFLOW NODES

## 52. Brand Profile Loader Node

```python
# =============================================================================
# ADAM Enhancement #14: LangGraph Workflow Nodes
# Location: adam/brand_intelligence/workflow/nodes.py
# =============================================================================

"""
LangGraph workflow nodes for Brand Intelligence.

These nodes integrate Brand Intelligence into the main ADAM decision workflow,
enabling brand profile loading, matching, and mechanism recommendation
as part of the orchestrated decision process.
"""

from __future__ import annotations
from typing import Dict, List, Optional, Any, TypedDict
from datetime import datetime
from langgraph.graph import StateGraph, END
from pydantic import BaseModel, Field

from ..models.brand_profile import BrandPsychologicalProfile
from ..models.match import BrandUserMatchResult, MechanismRecommendation
from ..cache.strategy import BrandCacheCoordinator
from ..learning.gradient_bridge import GradientBridgeConnector


# =============================================================================
# WORKFLOW STATE
# =============================================================================

class BrandIntelligenceState(TypedDict):
    """State passed through Brand Intelligence workflow nodes."""
    
    # Input
    brand_id: str
    user_id: str
    user_profile: Dict[str, Any]
    decision_id: str
    ad_ids: List[str]
    
    # Loaded data
    brand_profile: Optional[Dict[str, Any]]
    brand_profile_loaded: bool
    brand_profile_confidence: float
    
    # Match results
    match_result: Optional[Dict[str, Any]]
    match_computed: bool
    overall_match_score: float
    
    # Recommendations
    recommended_mechanisms: List[str]
    mechanism_priors: Dict[str, float]
    recommended_frame: str
    recommended_tone: str
    brand_voice: Dict[str, str]
    messaging_constraints: Dict[str, Any]
    
    # Learning
    learning_signal_emitted: bool
    
    # Errors
    errors: List[str]


# =============================================================================
# BRAND PROFILE LOADER NODE
# =============================================================================

class BrandProfileLoaderNode:
    """
    LangGraph node that loads brand psychological profile.
    
    This node is the entry point for Brand Intelligence in the workflow.
    It retrieves cached profiles or falls back to Feature Store/Neo4j.
    """
    
    def __init__(
        self,
        cache_coordinator: BrandCacheCoordinator,
        profile_service: 'BrandProfileService',
        metrics: 'BrandIntelMetrics'
    ):
        self.cache = cache_coordinator
        self.profile_service = profile_service
        self.metrics = metrics
    
    async def __call__(self, state: BrandIntelligenceState) -> BrandIntelligenceState:
        """
        Load brand profile for the workflow.
        
        Args:
            state: Current workflow state with brand_id
            
        Returns:
            Updated state with brand_profile loaded
        """
        brand_id = state["brand_id"]
        
        try:
            # Try cache first (L1 → L2 → L3)
            profile_dict = await self.cache.get_brand_profile(brand_id)
            
            if profile_dict is None:
                # Load from primary storage
                profile = await self.profile_service.get_profile(brand_id)
                if profile is None:
                    state["errors"].append(f"Brand profile not found: {brand_id}")
                    state["brand_profile_loaded"] = False
                    return state
                
                profile_dict = profile.to_feature_dict()
                
                # Populate cache
                await self.cache.set_brand_profile(brand_id, profile_dict)
            
            state["brand_profile"] = profile_dict
            state["brand_profile_loaded"] = True
            state["brand_profile_confidence"] = profile_dict.get("confidence_score", 0.5)
            
            # Extract voice and constraints for downstream
            state["brand_voice"] = {
                "pace": profile_dict.get("voice_pace", "medium"),
                "energy": profile_dict.get("voice_energy", "medium"),
                "formality": profile_dict.get("voice_formality", "professional"),
                "warmth": profile_dict.get("voice_warmth", "neutral"),
            }
            
            self.metrics.record_cache_hit("profile", "loaded")
            
        except Exception as e:
            state["errors"].append(f"Failed to load brand profile: {str(e)}")
            state["brand_profile_loaded"] = False
        
        return state


# =============================================================================
# BRAND-USER MATCHER NODE
# =============================================================================

class BrandUserMatcherNode:
    """
    LangGraph node that computes brand-user psychological match.
    
    This node calculates multi-dimensional alignment between the
    loaded brand profile and the user profile from Cold Start (#13).
    """
    
    def __init__(
        self,
        match_service: 'BrandMatchService',
        cache_coordinator: BrandCacheCoordinator,
        metrics: 'BrandIntelMetrics'
    ):
        self.match_service = match_service
        self.cache = cache_coordinator
        self.metrics = metrics
    
    async def __call__(self, state: BrandIntelligenceState) -> BrandIntelligenceState:
        """
        Compute brand-user match score.
        
        Args:
            state: Current workflow state with brand_profile and user_profile
            
        Returns:
            Updated state with match_result
        """
        if not state.get("brand_profile_loaded"):
            state["errors"].append("Cannot compute match: brand profile not loaded")
            state["match_computed"] = False
            return state
        
        brand_id = state["brand_id"]
        user_id = state["user_id"]
        
        try:
            # Check match cache first
            cached_match = await self.cache.get_match_score(brand_id, user_id)
            
            if cached_match:
                state["match_result"] = cached_match
                state["match_computed"] = True
                state["overall_match_score"] = cached_match["overall_match_score"]
                self.metrics.record_match_duration(1.0, cache_hit=True)
            else:
                # Compute fresh match
                import time
                start = time.perf_counter()
                
                match_result = await self.match_service.compute_match(
                    brand_id=brand_id,
                    user_id=user_id,
                    user_profile=state["user_profile"],
                    mechanism_count=3,
                    include_voice=True,
                    include_constraints=True,
                    decision_id=state.get("decision_id")
                )
                
                duration_ms = (time.perf_counter() - start) * 1000
                
                # Cache the result
                match_dict = match_result.dict()
                await self.cache.set_match_score(brand_id, user_id, match_dict)
                
                state["match_result"] = match_dict
                state["match_computed"] = True
                state["overall_match_score"] = match_result.overall_match_score
                
                self.metrics.record_match_duration(duration_ms, cache_hit=False)
                self.metrics.record_match_score(
                    state["brand_profile"].get("category", "unknown"),
                    match_result.overall_match_score
                )
            
        except Exception as e:
            state["errors"].append(f"Failed to compute match: {str(e)}")
            state["match_computed"] = False
        
        return state


# =============================================================================
# MECHANISM RECOMMENDER NODE
# =============================================================================

class MechanismRecommenderNode:
    """
    LangGraph node that recommends cognitive mechanisms for the brand-user pair.
    
    This node uses empirical priors from Gradient Bridge (#06) combined with
    brand profile data to select optimal mechanisms.
    """
    
    def __init__(
        self,
        gradient_bridge: GradientBridgeConnector,
        cache_coordinator: BrandCacheCoordinator,
        metrics: 'BrandIntelMetrics'
    ):
        self.bridge = gradient_bridge
        self.cache = cache_coordinator
        self.metrics = metrics
    
    async def __call__(self, state: BrandIntelligenceState) -> BrandIntelligenceState:
        """
        Recommend mechanisms based on brand-user match and empirical priors.
        
        Args:
            state: Current workflow state with match_result
            
        Returns:
            Updated state with mechanism recommendations
        """
        if not state.get("match_computed"):
            state["errors"].append("Cannot recommend mechanisms: match not computed")
            return state
        
        brand_id = state["brand_id"]
        match_result = state["match_result"]
        
        try:
            # Get empirical priors from learning history
            priors = await self.bridge.get_empirical_priors(brand_id)
            
            # Extract recommendations from match result
            mechanisms = match_result.get("recommended_mechanisms", [])
            
            if mechanisms:
                # Use match result recommendations (already sorted by effectiveness)
                state["recommended_mechanisms"] = [m["mechanism_id"] for m in mechanisms[:3]]
                state["mechanism_priors"] = {
                    m["mechanism_id"]: m["effectiveness_score"]
                    for m in mechanisms
                }
            else:
                # Fall back to empirical priors
                sorted_priors = sorted(
                    priors.items(),
                    key=lambda x: x[1].mean,
                    reverse=True
                )
                state["recommended_mechanisms"] = [p[0] for p in sorted_priors[:3]]
                state["mechanism_priors"] = {
                    p[0]: p[1].mean for p in sorted_priors
                }
            
            # Extract frame and tone
            state["recommended_frame"] = match_result.get("recommended_frame", "balanced")
            state["recommended_tone"] = match_result.get("recommended_tone", "neutral")
            
            # Record metrics
            for mech in state["recommended_mechanisms"]:
                self.metrics.record_mechanism_recommendation(
                    mech,
                    state["brand_profile"].get("category", "unknown")
                )
            
        except Exception as e:
            state["errors"].append(f"Failed to recommend mechanisms: {str(e)}")
            # Provide fallback recommendations
            state["recommended_mechanisms"] = [
                "REGULATORY_FOCUS",
                "IDENTITY_CONSTRUCTION",
                "AUTOMATIC_EVALUATION"
            ]
            state["mechanism_priors"] = {m: 0.5 for m in state["recommended_mechanisms"]}
        
        return state


# =============================================================================
# LEARNING SIGNAL EMITTER NODE
# =============================================================================

class LearningSignalEmitterNode:
    """
    LangGraph node that emits learning signals to Gradient Bridge.
    
    This node is called after recommendations are made, emitting signals
    that will be correlated with outcomes for continuous learning.
    """
    
    def __init__(
        self,
        gradient_bridge: GradientBridgeConnector,
        metrics: 'BrandIntelMetrics'
    ):
        self.bridge = gradient_bridge
        self.metrics = metrics
    
    async def __call__(self, state: BrandIntelligenceState) -> BrandIntelligenceState:
        """
        Emit learning signal for the brand-user match.
        
        Args:
            state: Current workflow state with complete recommendations
            
        Returns:
            Updated state with learning_signal_emitted flag
        """
        if not state.get("match_computed"):
            state["learning_signal_emitted"] = False
            return state
        
        try:
            # Create match result object for signal emission
            from ..models.match import BrandUserMatchResult
            
            match_result = BrandUserMatchResult(
                match_id=state["match_result"].get("match_id", ""),
                brand_id=state["brand_id"],
                user_id=state["user_id"],
                overall_match_score=state["overall_match_score"],
                personality_alignment=state["match_result"].get("personality_alignment", 0.5),
                regulatory_fit=state["match_result"].get("regulatory_fit", 0.5),
                construal_fit=state["match_result"].get("construal_fit", 0.5),
                value_alignment=state["match_result"].get("value_alignment", 0.5),
                archetype_fit=state["match_result"].get("archetype_fit", 0.5),
                recommended_archetype=state["match_result"].get("recommended_archetype", ""),
                recommended_archetype_name=state["match_result"].get("recommended_archetype_name", ""),
                recommended_frame=state["recommended_frame"],
                recommended_tone=state["recommended_tone"],
                match_confidence=state["match_result"].get("match_confidence", 0.5),
                brand_profile_confidence=state["brand_profile_confidence"],
                user_profile_confidence=state["match_result"].get("user_profile_confidence", 0.5),
                data_tier=state["match_result"].get("data_tier", 0)
            )
            
            # Emit to Gradient Bridge
            signal_id = await self.bridge.emit_match_signal(
                match_result=match_result,
                decision_id=state.get("decision_id", "")
            )
            
            state["learning_signal_emitted"] = True
            self.metrics.record_learning_signal_emitted("brand_match")
            
        except Exception as e:
            state["errors"].append(f"Failed to emit learning signal: {str(e)}")
            state["learning_signal_emitted"] = False
        
        return state


# =============================================================================
# WORKFLOW GRAPH CONSTRUCTION
# =============================================================================

def create_brand_intelligence_workflow(
    cache_coordinator: BrandCacheCoordinator,
    profile_service: 'BrandProfileService',
    match_service: 'BrandMatchService',
    gradient_bridge: GradientBridgeConnector,
    metrics: 'BrandIntelMetrics'
) -> StateGraph:
    """
    Create the Brand Intelligence LangGraph workflow.
    
    Workflow:
    1. Load brand profile (with caching)
    2. Compute brand-user match
    3. Recommend mechanisms based on match + empirical priors
    4. Emit learning signal to Gradient Bridge
    
    Returns:
        Compiled LangGraph workflow
    """
    
    # Initialize nodes
    profile_loader = BrandProfileLoaderNode(cache_coordinator, profile_service, metrics)
    matcher = BrandUserMatcherNode(match_service, cache_coordinator, metrics)
    recommender = MechanismRecommenderNode(gradient_bridge, cache_coordinator, metrics)
    signal_emitter = LearningSignalEmitterNode(gradient_bridge, metrics)
    
    # Build graph
    workflow = StateGraph(BrandIntelligenceState)
    
    # Add nodes
    workflow.add_node("load_brand_profile", profile_loader)
    workflow.add_node("compute_match", matcher)
    workflow.add_node("recommend_mechanisms", recommender)
    workflow.add_node("emit_learning_signal", signal_emitter)
    
    # Define edges
    workflow.set_entry_point("load_brand_profile")
    
    workflow.add_edge("load_brand_profile", "compute_match")
    workflow.add_edge("compute_match", "recommend_mechanisms")
    workflow.add_edge("recommend_mechanisms", "emit_learning_signal")
    workflow.add_edge("emit_learning_signal", END)
    
    # Compile
    return workflow.compile()


# =============================================================================
# INTEGRATION WITH MAIN ADAM WORKFLOW
# =============================================================================

class BrandIntelligenceSubgraph:
    """
    Brand Intelligence as a subgraph in the main ADAM workflow.
    
    This allows Brand Intelligence to be invoked as a single node
    in the larger orchestration while encapsulating the full workflow.
    """
    
    def __init__(self, workflow: StateGraph):
        self.workflow = workflow
    
    async def __call__(self, adam_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute Brand Intelligence workflow within ADAM state.
        
        Args:
            adam_state: Main ADAM workflow state containing:
                - brand_id
                - user_id  
                - user_profile (from Cold Start #13)
                - decision_id
                
        Returns:
            Updated ADAM state with Brand Intelligence outputs:
                - brand_match_score
                - recommended_mechanisms
                - mechanism_priors
                - brand_voice (for Copy Generation #15)
                - messaging_constraints (for Copy Generation #15)
        """
        # Initialize Brand Intelligence state
        bi_state: BrandIntelligenceState = {
            "brand_id": adam_state.get("brand_id", ""),
            "user_id": adam_state.get("user_id", ""),
            "user_profile": adam_state.get("user_profile", {}),
            "decision_id": adam_state.get("decision_id", ""),
            "ad_ids": adam_state.get("ad_ids", []),
            "brand_profile": None,
            "brand_profile_loaded": False,
            "brand_profile_confidence": 0.0,
            "match_result": None,
            "match_computed": False,
            "overall_match_score": 0.0,
            "recommended_mechanisms": [],
            "mechanism_priors": {},
            "recommended_frame": "balanced",
            "recommended_tone": "neutral",
            "brand_voice": {},
            "messaging_constraints": {},
            "learning_signal_emitted": False,
            "errors": [],
        }
        
        # Execute workflow
        final_state = await self.workflow.ainvoke(bi_state)
        
        # Merge results back into ADAM state
        adam_state["brand_match_score"] = final_state["overall_match_score"]
        adam_state["recommended_mechanisms"] = final_state["recommended_mechanisms"]
        adam_state["mechanism_priors"] = final_state["mechanism_priors"]
        adam_state["recommended_frame"] = final_state["recommended_frame"]
        adam_state["recommended_tone"] = final_state["recommended_tone"]
        adam_state["brand_voice"] = final_state["brand_voice"]
        adam_state["messaging_constraints"] = final_state["messaging_constraints"]
        adam_state["brand_intel_errors"] = final_state["errors"]
        
        return adam_state
```

## 55. Workflow Integration Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│   BRAND INTELLIGENCE LANGGRAPH WORKFLOW                                     │
│   ═════════════════════════════════════                                     │
│                                                                             │
│   Input State:                                                              │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │ brand_id: "nike_001"                                                │  │
│   │ user_id: "usr_12345"                                                │  │
│   │ user_profile: {openness: 0.72, promotion_focus: 0.8, ...}          │  │
│   │ decision_id: "dec_789"                                              │  │
│   └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│                              ▼                                              │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │  1. LOAD_BRAND_PROFILE                                              │  │
│   │     ├─ Check L1 Memory Cache (~1ms)                                 │  │
│   │     ├─ Check L2 Redis Cache (~2ms)                                  │  │
│   │     ├─ Check L3 Feature Store (~5ms)                                │  │
│   │     └─ Load from Neo4j (fallback)                                   │  │
│   │                                                                     │  │
│   │  Output: brand_profile, brand_voice, brand_profile_confidence       │  │
│   └─────────────────────────────────────────────────────────────────────┘  │
│                              ▼                                              │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │  2. COMPUTE_MATCH                                                   │  │
│   │     ├─ Personality alignment (Big Five cosine similarity)           │  │
│   │     ├─ Regulatory focus fit (promotion/prevention)                  │  │
│   │     ├─ Construal level fit (abstract/concrete)                      │  │
│   │     ├─ Value alignment (Schwartz values)                            │  │
│   │     └─ Archetype fit (best matching archetype)                      │  │
│   │                                                                     │  │
│   │  Output: match_result, overall_match_score                          │  │
│   └─────────────────────────────────────────────────────────────────────┘  │
│                              ▼                                              │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │  3. RECOMMEND_MECHANISMS                                            │  │
│   │     ├─ Get empirical priors from Gradient Bridge (#06)              │  │
│   │     ├─ Combine with match-based recommendations                     │  │
│   │     ├─ Select top 3 mechanisms by expected effectiveness            │  │
│   │     └─ Determine frame and tone                                     │  │
│   │                                                                     │  │
│   │  Output: recommended_mechanisms, mechanism_priors, frame, tone      │  │
│   └─────────────────────────────────────────────────────────────────────┘  │
│                              ▼                                              │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │  4. EMIT_LEARNING_SIGNAL                                            │  │
│   │     ├─ Create BrandLearningSignal                                   │  │
│   │     ├─ Emit to Gradient Bridge (#06)                                │  │
│   │     └─ Publish to Kafka (adam.brands.matches)                       │  │
│   │                                                                     │  │
│   │  Output: learning_signal_emitted = True                             │  │
│   └─────────────────────────────────────────────────────────────────────┘  │
│                              ▼                                              │
│   Output State (merged into ADAM workflow):                                 │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │ brand_match_score: 0.82                                             │  │
│   │ recommended_mechanisms: ["IDENTITY_CONSTRUCTION", "MIMETIC_DESIRE"] │  │
│   │ mechanism_priors: {"IDENTITY": 0.78, "MIMETIC": 0.72, ...}         │  │
│   │ recommended_frame: "promotion_gain"                                 │  │
│   │ brand_voice: {pace: "fast", energy: "high", warmth: "warm"}        │  │
│   │ messaging_constraints: {max_urgency: 0.7, prohibited: [...]}       │  │
│   └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│   → Consumed by Copy Generation (#15) for brand-voice-aligned ads          │
│   → Consumed by WPP Ad Desk (#28) for product-inventory matching           │
│   → Consumed by Explanation Engine (#18) for decision reasoning            │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```
