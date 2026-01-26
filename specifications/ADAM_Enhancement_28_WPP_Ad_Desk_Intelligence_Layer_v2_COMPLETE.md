# ADAM Enhancement #28: WPP Ad Desk Intelligence Layer
## Enterprise-Grade Programmatic Intelligence Integration - VERSION 2.0 COMPLETE

**Version**: 2.0 COMPLETE (Deep Structure Integration)  
**Date**: January 2026  
**Priority**: P0 - Strategic Platform Extension  
**Estimated Implementation**: 28 person-weeks  
**Dependencies**: #02 (Blackboard), #06 (Gradient Bridge), #10 (Journey Tracking), #14 (Brand Intelligence), #15 (Copy Generation), #19 (Identity Resolution)  
**Dependents**: All downstream campaign execution, WPP Open integration  
**File Size**: ~180KB (Enterprise Production-Ready with Deep Architecture)

---

## Table of Contents

### SECTION A: STRATEGIC OVERVIEW
1. [Executive Summary](#executive-summary)
2. [The Strategic Frame](#the-strategic-frame)
3. [Three Core Products Overview](#three-core-products-overview)

### SECTION B: PRODUCT 1 - PRODUCT-TO-INVENTORY MATCH
4. [Product 1 Architecture](#product-1-architecture)
5. [Product Knowledge Graph Deep Model](#product-knowledge-graph-deep-model)
6. [Customer Psychological Segment Engine](#customer-psychological-segment-engine)
7. [Amazon Review Analysis Pipeline](#amazon-review-analysis-pipeline)
8. [Web Intelligence Augmentation](#web-intelligence-augmentation)
9. [Inventory Knowledge Graph](#inventory-knowledge-graph)
10. [Product-to-Inventory Matching Algorithm](#product-to-inventory-matching-algorithm)
11. [Deployment Intelligence Generation](#deployment-intelligence-generation)

### SECTION C: PRODUCT 2 - SEQUENTIAL PERSUASION
12. [Product 2 Architecture](#product-2-architecture)
13. [Journey State Model](#journey-state-model)
14. [Sequence Step Configuration](#sequence-step-configuration)
15. [Sequence Templates Library](#sequence-templates-library)
16. [Real-Time Sequence Orchestration](#real-time-sequence-orchestration)

### SECTION D: PRODUCT 3 - SUPPLY-PATH OPTIMIZATION
17. [Product 3 Architecture](#product-3-architecture)
18. [Supply Path Graph Model](#supply-path-graph-model)
19. [Supply Path Scoring Engine](#supply-path-scoring-engine)
20. [Portfolio Optimization](#portfolio-optimization)

### SECTION E: INTEGRATION & INFRASTRUCTURE
21. [Three-Product Integration Flow](#three-product-integration-flow)
22. [Unified Learning Loop](#unified-learning-loop)
23. [Neo4j Schema - Complete Graph Model](#neo4j-schema-complete)
24. [FastAPI Endpoints](#fastapi-endpoints)
25. [LangGraph Orchestration Workflows](#langgraph-orchestration)
26. [WPP Adapter Layer](#wpp-adapter-layer)

### SECTION F: DEPLOYMENT & OPERATIONS
27. [Implementation Timeline](#implementation-timeline)
28. [Success Metrics](#success-metrics)
29. [Testing Strategy](#testing-strategy)
30. [Monitoring & Observability](#monitoring-observability)

---

# SECTION A: STRATEGIC OVERVIEW

## Executive Summary

### The Strategic Imperative

WPP Media (formerly GroupM) manages **$60+ billion** in annual media investment across 80+ markets. They are aggressively investing £300m/year in WPP Open to achieve platform-level economics. However, they face a fundamental challenge: **the gap between identity verification and conversion intelligence**.

ADAM's Enhancement #28 bridges this gap through **three core intelligence products** designed for immediate commercial impact:

| Product | Primary Value | Commercial Justification |
|---------|---------------|-------------------------|
| **Product-to-Inventory Match** | Eliminate wasted spend | Less waste = immediate ROI |
| **Sequential Persuasion** | Higher conversion rates | Lift justifies premium fees |
| **Supply-Path Optimization** | Cost efficiency + quality | Savings fund platform fee |

### What Makes This Different

This is NOT another "audience targeting" platform. ADAM's Ad Desk provides:

1. **Psychological Intelligence, Not Demographics** — We don't match "women 25-34" to inventory. We match "high-conscientiousness, prevention-focused, quality-obsessed researchers" to psychological contexts where they're receptive.

2. **Graph-Based Journey Orchestration** — We don't "rotate 3 creatives." We model transitions and paths through decision states, selecting inventory based on where users ARE in their psychological journey.

3. **Supply-Path Quality Graphs** — We don't just buy "Publisher X." We find the optimal path to Publisher X (SSP → Exchange → Publisher) that maximizes quality × efficiency.

### The Amazon Foundation

Our core differentiation stems from **Amazon's 1.2B+ verified purchase reviews**:
- Every customer's language tied to actual purchase behavior
- Cross-category behavior patterns by customer ID
- Psycholinguistic analysis revealing personality, values, motivations
- This creates the only dataset where **verified purchase** meets **unstructured language expression** at scale

### Business Impact Projections

| Capability | Current State | With ADAM Ad Desk | Lift |
|------------|--------------|-------------------|------|
| Cold Start Waste | 15-25% of first 2 weeks | 5-10% | **50-60% reduction** |
| Inventory Match | Demographics-based | Psychological alignment | **2-3x relevance** |
| Sequential Conversion | Generic frequency caps | Journey-state orchestration | **40-50% lift** |
| Supply-Path Efficiency | Manual curation | Graph-optimized | **15-25% cost reduction** |
| Attribution Confidence | MMM + last-touch | Mechanism-level causal | **Dramatically improved** |

---

## The Strategic Frame

### Why These Three Products

An "ad desk" buyer cares about three things:

1. **Reduce wasted spend immediately** — Every dollar spent without conversion is failure
2. **Unlock premium supply/performance** — Access what competitors can't reliably get
3. **Create measurable lift** — Justify platform fees with provable ROI

Our three products directly address these:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    VALUE ALIGNMENT MATRIX                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   BUYER NEED                    │ ADAM PRODUCT                │ HOW IT HELPS│
│   ─────────────────────────────────────────────────────────────────────────│
│                                                                             │
│   "Stop wasting my budget       │ Product-to-Inventory Match │ Target only │
│    on non-converters"           │                            │ people who  │
│                                 │                            │ actually buy│
│   ─────────────────────────────────────────────────────────────────────────│
│                                                                             │
│   "Get better performance       │ Sequential Persuasion      │ Right message│
│    from my campaigns"           │                            │ right stage  │
│                                 │                            │ right context│
│   ─────────────────────────────────────────────────────────────────────────│
│                                                                             │
│   "Reduce CPMs without          │ Supply-Path Optimization   │ Best path to │
│    sacrificing quality"         │                            │ same inventory│
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Competitive Positioning

| Platform | Inventory Intelligence | Psychological Targeting | Sequential Orchestration | Graph Optimization |
|----------|----------------------|------------------------|-------------------------|-------------------|
| **The Trade Desk** | UID2 identity, Koa AI | Behavioral correlations | Basic frequency caps | None |
| **Google DV360** | Cross-channel reach | Demo + interest | Limited sequencing | None |
| **Meta** | Walled garden | Behavioral + engagement | Advantage+ auto | None |
| **Amazon DSP** | Purchase signals | Retail intent | Post-purchase only | None |
| **ADAM Ad Desk** | **Full supply graph** | **Psychological mechanisms** | **Journey-state aware** | **Neo4j-powered** |

---

## Three Core Products Overview

### Product 1: Product-to-Inventory Match

**The Cleanest Wedge for Market Entry**

Customer uploads product feed → ADAM builds rich Product Knowledge Graph with psychological segments → System maps to Inventory Graph → Output is actionable buying intelligence.

**Key Innovation**: We analyze Amazon reviews + web discussions to build deep psychological profiles of who buys this product and WHY, then match those profiles to inventory where they're psychologically receptive.

**Outputs**:
- Recommended PMPs/Curated Deals
- Recommended Contextual Segments  
- Recommended Audiences (modeled/lookalikes)
- Recommended Exclusions (brand safety + wasted adjacency)
- Complete Deployment Plan (timing, messaging, budget allocation)

### Product 2: Sequential Persuasion

**Where Graph AI Meaningfully Outperforms**

Instead of "run 3 creatives and rotate," we do:
- Creative A on DISCOVERY contexts (high openness, exploration)
- Creative B on CONSIDERATION contexts (comparison, analytical)
- Creative C on CONVERSION contexts (decision-ready, approach active)

**Key Innovation**: We model **transitions and paths**, not just buckets. The graph captures transition probabilities, mechanism enhancers, and inventory preferences per journey state.

### Product 3: Supply-Path Optimization

**Very Monetizable for Trading Desks**

Graph AI represents the full supply chain:
- SSP → Exchange → Reseller → Publisher → Placement → Performance
- Latency, viewability, fraud risk, bid shading effects
- Carbon/attention metrics where available

**Key Innovation**: Multiple paths to the same placement have different quality. Graph reveals which SSPs and routes deliver best quality × efficiency.

**Output**: 15-25% CPM savings + quality improvement sold as "quality + efficiency."

---

# SECTION B: PRODUCT 1 - PRODUCT-TO-INVENTORY MATCH

## Product 1 Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                    PRODUCT-TO-INVENTORY MATCH PIPELINE                              │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                     │
│   INPUTS                                                                            │
│   ──────                                                                            │
│   ┌──────────────────┐                                                              │
│   │ Product Feed     │  Customer uploads: SKUs, descriptions, prices, images       │
│   │ or Brief         │  Or: Product brief with category, positioning, audience     │
│   └────────┬─────────┘                                                              │
│            │                                                                        │
│            ▼                                                                        │
│   ┌──────────────────────────────────────────────────────────────────────────────┐ │
│   │                     PRODUCT KNOWLEDGE GRAPH ENGINE                            │ │
│   │                                                                               │ │
│   │  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐             │ │
│   │  │ Attribute  │  │ Customer   │  │ Competitor │  │ Compliance │             │ │
│   │  │ Extraction │  │ Psychology │  │ Analysis   │  │ Constraints│             │ │
│   │  └────────────┘  └────────────┘  └────────────┘  └────────────┘             │ │
│   │                         │                                                    │ │
│   │                         ▼                                                    │ │
│   │              ┌─────────────────────────┐                                     │ │
│   │              │ PSYCHOLOGICAL SEGMENTS  │                                     │ │
│   │              │ Who buys this? Why?     │                                     │ │
│   │              │ What states? What needs?│                                     │ │
│   │              └─────────────────────────┘                                     │ │
│   └──────────────────────────────────────────────────────────────────────────────┘ │
│                                    │                                                │
│                                    ▼                                                │
│   ┌──────────────────────────────────────────────────────────────────────────────┐ │
│   │                      INVENTORY KNOWLEDGE GRAPH                                │ │
│   │                                                                               │ │
│   │  Publishers │ Placements │ Content Topics │ Audio Genres │ Device/Time       │ │
│   │  Supply Paths │ PMPs │ Contextual Segments │ Audiences │ Exclusions          │ │
│   └──────────────────────────────────────────────────────────────────────────────┘ │
│                                    │                                                │
│                                    ▼                                                │
│   OUTPUTS                                                                           │
│   ───────                                                                           │
│   ┌────────────────┐ ┌────────────────┐ ┌────────────────┐ ┌────────────────┐     │
│   │ Recommended    │ │ Contextual     │ │ Modeled        │ │ Exclusions     │     │
│   │ PMPs/Deals     │ │ Segments       │ │ Audiences      │ │ (Safety+Waste) │     │
│   └────────────────┘ └────────────────┘ └────────────────┘ └────────────────┘     │
│                                                                                     │
│   ┌────────────────────────────────────────────────────────────────────────────┐   │
│   │ DEPLOYMENT INTELLIGENCE: Exact inventory allocations, timing, messaging    │   │
│   └────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                     │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Product Knowledge Graph Deep Model

### Core Data Models

```python
# =============================================================================
# ADAM Enhancement #28 v2.0: Product Knowledge Graph Models
# Location: adam/ad_desk/models/product.py
# =============================================================================

"""
Product Knowledge Graph - Deep Model Architecture

These models represent products not as SKUs but as psychological entities
with resonance profiles, customer segments, and mechanism effectiveness.
"""

from __future__ import annotations
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum
from uuid import uuid4
from pydantic import BaseModel, Field


# =============================================================================
# CATEGORY & CLASSIFICATION ENUMS
# =============================================================================

class ProductCategory(str, Enum):
    """
    Primary product categories with psychological implications.
    
    Categories are organized by:
    1. Involvement level (cognitive effort required)
    2. Processing mode (analytical vs. emotional)
    3. Social signaling (identity expression level)
    """
    # HIGH INVOLVEMENT - Analytical Processing
    ELECTRONICS = "electronics"
    AUTOMOTIVE = "automotive"
    FINANCIAL_SERVICES = "financial_services"
    REAL_ESTATE = "real_estate"
    HEALTHCARE = "healthcare"
    INSURANCE = "insurance"
    EDUCATION = "education"
    TECHNOLOGY_B2B = "technology_b2b"
    
    # MEDIUM INVOLVEMENT - Mixed Processing
    FASHION = "fashion"
    HOME_GOODS = "home_goods"
    TRAVEL = "travel"
    TECHNOLOGY_CONSUMER = "technology_consumer"
    TELECOM = "telecom"
    
    # LOW INVOLVEMENT - Heuristic Processing
    CPG_FOOD = "cpg_food"
    CPG_BEVERAGE = "cpg_beverage"
    CPG_PERSONAL_CARE = "cpg_personal_care"
    CPG_HOUSEHOLD = "cpg_household"
    ENTERTAINMENT = "entertainment"
    QSR = "qsr"  # Quick Service Restaurant
    
    # STATUS/IDENTITY - Social Processing
    LUXURY = "luxury"
    SPORTS_EQUIPMENT = "sports_equipment"
    HOBBIES = "hobbies"


class PriceTier(str, Enum):
    """
    Price tier with psychological implications.
    
    Each tier suggests different psychological approaches:
    - BUDGET: Loss aversion, promotion-focused messaging
    - VALUE: Quality/price balance, rational appeal
    - MAINSTREAM: Social proof, broad belonging
    - PREMIUM: Quality signaling, aspiration
    - LUXURY: Exclusivity, identity expression
    """
    BUDGET = "budget"           # <$20 - impulse-friendly, low risk
    VALUE = "value"             # $20-$100 - considered but accessible
    MAINSTREAM = "mainstream"   # $100-$500 - significant consideration
    PREMIUM = "premium"         # $500-$2000 - high involvement
    LUXURY = "luxury"           # $2000+ - status/identity driven
    ULTRA_LUXURY = "ultra_luxury"  # $10000+ - connoisseurship


class UseOccasion(str, Enum):
    """Use occasions that trigger purchase consideration."""
    DAILY_ROUTINE = "daily_routine"
    PROBLEM_SOLVING = "problem_solving"
    SPECIAL_OCCASION = "special_occasion"
    GIFT_GIVING = "gift_giving"
    SELF_REWARD = "self_reward"
    PLANNED_PURCHASE = "planned_purchase"
    IMPULSE = "impulse"
    EXPLORATION = "exploration"
    SOCIAL_ACTIVITY = "social_activity"
    PROFESSIONAL = "professional"
    SEASONAL = "seasonal"
    LIFE_TRANSITION = "life_transition"  # New home, new baby, etc.


# =============================================================================
# PSYCHOLOGICAL PROFILE MODELS
# =============================================================================

class PsychologicalResonance(BaseModel):
    """
    Psychological resonance profile for a product.
    
    Captures: What psychological traits does this product appeal to?
    Which mechanisms work best? What states are optimal?
    
    This transforms products from "things to sell" into
    "psychological opportunity surfaces."
    """
    # Big Five Trait Affinities (which personality types buy this)
    openness_affinity: float = Field(default=0.5, ge=0.0, le=1.0)
    conscientiousness_affinity: float = Field(default=0.5, ge=0.0, le=1.0)
    extraversion_affinity: float = Field(default=0.5, ge=0.0, le=1.0)
    agreeableness_affinity: float = Field(default=0.5, ge=0.0, le=1.0)
    neuroticism_affinity: float = Field(default=0.5, ge=0.0, le=1.0)
    
    # Regulatory Focus Alignment
    promotion_alignment: float = Field(default=0.5, ge=0.0, le=1.0)
    # High = gains, aspirations, growth messaging
    prevention_alignment: float = Field(default=0.5, ge=0.0, le=1.0)
    # High = safety, security, loss-avoidance messaging
    
    # Mechanism Effectiveness Rankings (Cialdini + extensions)
    social_proof_effectiveness: float = Field(default=0.5, ge=0.0, le=1.0)
    scarcity_effectiveness: float = Field(default=0.5, ge=0.0, le=1.0)
    authority_effectiveness: float = Field(default=0.5, ge=0.0, le=1.0)
    reciprocity_effectiveness: float = Field(default=0.5, ge=0.0, le=1.0)
    commitment_effectiveness: float = Field(default=0.5, ge=0.0, le=1.0)
    liking_effectiveness: float = Field(default=0.5, ge=0.0, le=1.0)
    
    # Optimal States for Purchase
    optimal_arousal_level: float = Field(default=0.5, ge=0.0, le=1.0)
    # 0=calm deliberation, 1=high arousal/excitement
    
    optimal_construal_level: float = Field(default=0.5, ge=0.0, le=1.0)
    # 0=concrete "how" focus, 1=abstract "why" focus
    
    decision_proximity_sweet_spot: str = "consideration"
    # "discovery", "consideration", "intent", "conversion"
    
    # Confidence Metrics
    profile_confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    evidence_count: int = Field(default=0, ge=0)
    last_updated: datetime = Field(default_factory=datetime.utcnow)


class CustomerPsychologicalSegment(BaseModel):
    """
    A psychological segment of customers for a product.
    
    Derived from:
    1. Amazon review language analysis (1.2B+ reviews)
    2. Web-scraped customer discussions (Reddit, forums, social)
    3. Psycholinguistic inference via Claude
    
    This answers: "Who are these people psychologically?"
    
    Key insight: This is NOT demographic segmentation.
    "High-conscientiousness, prevention-focused, quality-obsessed researchers"
    is VERY different from "Men 25-54 with HHI $100K+"
    """
    segment_id: str = Field(default_factory=lambda: str(uuid4()))
    segment_name: str  # Human-readable: "Quality-Obsessed Researchers"
    
    # Size and Confidence
    estimated_percentage: float = Field(ge=0.0, le=1.0)
    # Percentage of customer base in this segment
    evidence_count: int = Field(ge=0)
    # Number of reviews/discussions analyzed
    confidence_score: float = Field(ge=0.0, le=1.0)
    # Confidence in segment definition
    
    # =========================================================================
    # BIG FIVE PERSONALITY PROFILE
    # =========================================================================
    openness: float = Field(ge=0.0, le=1.0)
    # Curiosity, creativity, openness to experience
    # High: Tries new brands, values innovation, early adopter
    # Low: Brand loyal, prefers familiar, skeptical of new
    
    conscientiousness: float = Field(ge=0.0, le=1.0)
    # Organization, dependability, self-discipline
    # High: Researches thoroughly, reads reviews, plans purchases
    # Low: Impulse buyer, convenience-driven, less research
    
    extraversion: float = Field(ge=0.0, le=1.0)
    # Sociability, assertiveness, positive emotionality
    # High: Social proof matters, shares purchases, word-of-mouth
    # Low: Private buyer, less influenced by social, intrinsic motivation
    
    agreeableness: float = Field(ge=0.0, le=1.0)
    # Cooperation, trust, prosociality
    # High: Values brand ethics, community, sustainability
    # Low: Transactional, price-focused, less brand loyalty
    
    neuroticism: float = Field(ge=0.0, le=1.0)
    # Emotional instability, anxiety, negative affect
    # High: Risk-averse, needs reassurance, warranty-focused
    # Low: Confident buyer, less need for guarantees
    
    # =========================================================================
    # REGULATORY FOCUS
    # =========================================================================
    promotion_focus: float = Field(ge=0.0, le=1.0)
    # Approach motivation - gains, aspirations, achievements
    # High: "Get ahead" "Unlock potential" "Best in class"
    
    prevention_focus: float = Field(ge=0.0, le=1.0)
    # Avoidance motivation - safety, security, loss prevention
    # High: "Don't miss out" "Protect yourself" "Avoid problems"
    
    # =========================================================================
    # VALUES (Schwartz Values Framework)
    # =========================================================================
    primary_values: List[str] = Field(default_factory=list)
    # From: self_direction, stimulation, hedonism, achievement,
    # power, security, conformity, tradition, benevolence, universalism
    
    # =========================================================================
    # PURCHASE MOTIVATIONS
    # =========================================================================
    primary_motivations: List[str] = Field(default_factory=list)
    # What drives purchase:
    # "quality_assurance", "status_signaling", "problem_solving",
    # "social_belonging", "self_expression", "deal_hunting",
    # "convenience", "innovation_seeking", "risk_reduction"
    
    # =========================================================================
    # LANGUAGE PATTERNS
    # =========================================================================
    linguistic_markers: Dict[str, float] = Field(default_factory=dict)
    # Detected language patterns and their strength:
    # "analytical_language": 0.8  - uses logic, cause/effect
    # "certainty_words": 0.7     - "definitely", "absolutely"
    # "social_words": 0.3        - "we", "together", references
    # "emotional_intensity": 0.6 - strength of affect
    # "cognitive_complexity": 0.7 - sentence structure, vocabulary
    
    resonant_phrases: List[str] = Field(default_factory=list)
    # Exact phrases that resonate with this segment:
    # "built to last", "tested by experts", "worth the investment"
    
    aversive_phrases: List[str] = Field(default_factory=list)
    # Phrases that repel this segment:
    # "cheap", "basic", "just okay", "budget option"
    
    # =========================================================================
    # MECHANISM EFFECTIVENESS
    # =========================================================================
    mechanism_effectiveness: Dict[str, float] = Field(default_factory=dict)
    # How effective each persuasion mechanism is for this segment:
    # "social_proof": 0.9   - "10,000 5-star reviews"
    # "scarcity": 0.3       - "Only 3 left!" (doesn't work on researchers)
    # "authority": 0.8      - "Expert recommended"
    # "reciprocity": 0.5    - "Free gift with purchase"
    # "commitment": 0.7     - "Start with free trial"
    # "liking": 0.4         - Brand personality, aesthetics
    
    # =========================================================================
    # CROSS-CATEGORY INTERESTS
    # =========================================================================
    correlated_categories: List[str] = Field(default_factory=list)
    # What else do these customers buy?
    # "outdoor_gear", "premium_cookware", "financial_planning"
    # This enables cross-sell and lookalike expansion
    
    # =========================================================================
    # TEMPORAL PATTERNS
    # =========================================================================
    purchase_timing: Dict[str, float] = Field(default_factory=dict)
    # When they're most likely to convert:
    # "morning": 0.3, "evening": 0.5, "weekend": 0.7
    # "payday": 0.8, "holiday_season": 0.6
    
    # =========================================================================
    # MEDIA CONSUMPTION
    # =========================================================================
    likely_content_preferences: List[str] = Field(default_factory=list)
    # What media they consume (maps to inventory selection):
    # "documentary", "news_analysis", "educational_podcast",
    # "review_sites", "comparison_content"
    
    # =========================================================================
    # METADATA
    # =========================================================================
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    source_data: Dict[str, Any] = Field(default_factory=dict)
    # What data was used to build this segment


# =============================================================================
# PRODUCT NODE MODEL
# =============================================================================

class ProductKnowledgeNode(BaseModel):
    """
    Complete product representation for graph storage.
    
    This is NOT just a product feed row—it's a rich node
    capturing psychological purchase dynamics.
    """
    # =========================================================================
    # IDENTITY
    # =========================================================================
    product_id: str
    advertiser_id: str
    product_name: str
    product_description: str
    product_url: Optional[str] = None
    image_urls: List[str] = Field(default_factory=list)
    
    # =========================================================================
    # CATEGORIZATION
    # =========================================================================
    category: ProductCategory
    subcategories: List[str] = Field(default_factory=list)
    
    # =========================================================================
    # PRICING
    # =========================================================================
    price: float
    price_tier: PriceTier
    msrp: Optional[float] = None
    discount_percentage: Optional[float] = None
    
    # =========================================================================
    # USE CONTEXT
    # =========================================================================
    primary_use_occasions: List[UseOccasion] = Field(default_factory=list)
    consumption_frequency: str = "occasional"
    # "daily", "weekly", "monthly", "occasional", "rare", "one_time"
    
    # =========================================================================
    # PSYCHOLOGICAL PROFILE (DERIVED)
    # =========================================================================
    psychological_resonance: Optional[PsychologicalResonance] = None
    customer_segments: List[CustomerPsychologicalSegment] = Field(default_factory=list)
    
    # =========================================================================
    # COMPETITIVE CONTEXT
    # =========================================================================
    competitor_products: List[str] = Field(default_factory=list)
    competitive_positioning: str = ""
    # "premium_leader", "value_challenger", "niche_specialist", "mass_market"
    
    # =========================================================================
    # COMPLIANCE
    # =========================================================================
    compliance_constraints: List['ComplianceConstraint'] = Field(default_factory=list)
    
    # =========================================================================
    # EMBEDDINGS
    # =========================================================================
    attribute_embedding: List[float] = Field(default_factory=list)
    # 64-dim vector for product attribute similarity
    psychological_embedding: List[float] = Field(default_factory=list)
    # 64-dim vector for psychological profile similarity
    
    # =========================================================================
    # METADATA
    # =========================================================================
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_segment_refresh: Optional[datetime] = None


class ComplianceConstraint(BaseModel):
    """Compliance constraints that affect inventory selection."""
    constraint_type: str
    # "age_restricted", "geo_restricted", "category_blocked",
    # "brand_safety_required", "regulated_claims"
    constraint_value: str
    constraint_reason: str
    enforcement_level: str = "required"
    # "required", "recommended", "optional"


class ProductFeed(BaseModel):
    """Batch product feed for ingestion."""
    advertiser_id: str
    products: List[ProductKnowledgeNode]
    feed_timestamp: datetime = Field(default_factory=datetime.utcnow)
    feed_version: str = "2.0"
    replace_existing: bool = False
    # If True, delete products not in this feed
```

---

## Customer Psychological Segment Engine

This is the core differentiator—building deep psychological profiles from Amazon reviews + web intelligence.

```python
# =============================================================================
# ADAM Enhancement #28 v2.0: Customer Psychological Segment Engine
# Location: adam/ad_desk/segment_engine.py
# =============================================================================

"""
Customer Psychological Segment Engine

The secret sauce: Transform Amazon review language into actionable
psychological segments that predict advertising response.

Key insight from Matz et al. (PNAS, 2017):
- Psychological targeting based on personality can increase CTR by 40%
- Language patterns reveal stable personality traits
- These traits predict advertising response

We apply this at scale using Amazon's 1.2B+ verified purchase reviews.
"""

from __future__ import annotations
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from uuid import uuid4
import numpy as np
from neo4j import AsyncDriver

from adam.ad_desk.models.product import (
    ProductKnowledgeNode, CustomerPsychologicalSegment, PsychologicalResonance
)
from adam.llm.claude_client import ClaudeClient

logger = logging.getLogger(__name__)


class CustomerSegmentEngine:
    """
    Builds psychological segments from Amazon reviews and web intelligence.
    
    Pipeline:
    1. Gather relevant reviews for product/category
    2. Extract linguistic features (without LIWC—using Claude)
    3. Cluster by linguistic patterns
    4. Generate psychological profiles per cluster
    5. Validate against psychological literature
    6. Store segments in Neo4j linked to product
    """
    
    def __init__(
        self,
        neo4j_driver: AsyncDriver,
        claude_client: ClaudeClient,
        amazon_corpus: 'AmazonCorpusClient',
        database: str = "neo4j"
    ):
        self.neo4j = neo4j_driver
        self.claude = claude_client
        self.amazon = amazon_corpus
        self.database = database
    
    async def build_segments_for_product(
        self,
        product: ProductKnowledgeNode,
        min_reviews: int = 100,
        max_segments: int = 5
    ) -> List[CustomerPsychologicalSegment]:
        """
        Build psychological segments for a product from Amazon data.
        
        This is the main entry point for segment generation.
        """
        logger.info(f"Building segments for product: {product.product_id}")
        
        # Step 1: Gather relevant reviews
        reviews = await self._gather_relevant_reviews(product, min_reviews)
        logger.info(f"Gathered {len(reviews)} reviews")
        
        if len(reviews) < min_reviews:
            logger.warning(f"Insufficient reviews ({len(reviews)}), using category defaults")
            return await self._generate_category_default_segments(product)
        
        # Step 2: Extract linguistic features
        linguistic_features = await self._extract_linguistic_features(reviews)
        
        # Step 3: Cluster reviews by linguistic patterns
        clusters = self._cluster_by_linguistics(linguistic_features, max_segments)
        logger.info(f"Created {len(clusters)} clusters")
        
        # Step 4: Generate psychological profiles per cluster
        segments = []
        for cluster_id, cluster_reviews in clusters.items():
            segment = await self._generate_segment_from_cluster(
                cluster_id, cluster_reviews, product
            )
            segments.append(segment)
        
        # Step 5: Validate and refine
        validated_segments = await self._validate_segments(segments, product)
        
        # Step 6: Store in Neo4j
        await self._store_segments(product.product_id, validated_segments)
        
        return validated_segments
    
    async def _gather_relevant_reviews(
        self,
        product: ProductKnowledgeNode,
        min_reviews: int
    ) -> List[Dict[str, Any]]:
        """
        Gather reviews from Amazon corpus for product/category/brand.
        
        Strategy:
        1. Exact product match (if available)
        2. Same brand, same category
        3. Same category, similar price tier
        4. Related categories
        """
        reviews = []
        
        # Try exact product first
        if product.product_name:
            exact_reviews = await self.amazon.get_reviews_by_product_name(
                product.product_name, limit=min_reviews
            )
            reviews.extend(exact_reviews)
        
        if len(reviews) < min_reviews:
            # Expand to category + brand
            category_reviews = await self.amazon.get_reviews_by_category(
                category=product.category.value,
                price_tier=product.price_tier.value,
                limit=min_reviews - len(reviews)
            )
            reviews.extend(category_reviews)
        
        if len(reviews) < min_reviews:
            # Expand to related categories
            related_categories = self._get_related_categories(product.category)
            for related in related_categories:
                if len(reviews) >= min_reviews:
                    break
                related_reviews = await self.amazon.get_reviews_by_category(
                    category=related,
                    limit=(min_reviews - len(reviews)) // len(related_categories)
                )
                reviews.extend(related_reviews)
        
        return reviews
    
    async def _extract_linguistic_features(
        self,
        reviews: List[Dict[str, Any]]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Extract psycholinguistic features from review text.
        
        KEY INSIGHT: We do NOT use LIWC dictionary counting.
        Claude provides superior contextual understanding.
        
        Features extracted:
        - Analytical language (cause/effect, logic markers)
        - Emotional language (valence, intensity)
        - Social orientation (we/us, social references)
        - Certainty level (definitely, maybe, etc.)
        - Cognitive complexity (sentence structure, vocabulary)
        - Self-reference (I/me/my frequency)
        - Specificity (concrete details vs abstractions)
        - Temporal focus (past/present/future orientation)
        """
        features = {}
        
        # Process in batches for efficiency
        batch_size = 20
        for i in range(0, len(reviews), batch_size):
            batch = reviews[i:i + batch_size]
            batch_features = await self._extract_features_batch(batch)
            features.update(batch_features)
        
        return features
    
    async def _extract_features_batch(
        self,
        reviews: List[Dict[str, Any]]
    ) -> Dict[str, Dict[str, Any]]:
        """Extract linguistic features for a batch of reviews using Claude."""
        
        # Prepare review texts for analysis
        review_texts = []
        for review in reviews:
            review_texts.append({
                "id": review.get("review_id", str(uuid4())),
                "text": review.get("review_text", "")[:1000],  # Truncate for efficiency
                "rating": review.get("rating", 0),
                "verified": review.get("verified_purchase", False)
            })
        
        # Claude prompt for linguistic analysis
        prompt = f"""
        Analyze the following product reviews for psycholinguistic features.
        
        For each review, extract these features on a 0-1 scale:
        
        1. analytical_language: Use of logical reasoning, cause-effect statements
        2. emotional_intensity: Strength of emotional expression
        3. positive_emotion: Ratio of positive to negative sentiment
        4. social_orientation: References to others, social context
        5. certainty_level: Use of definitive vs hedging language
        6. cognitive_complexity: Vocabulary sophistication, sentence structure
        7. self_reference: Focus on personal experience (I/me/my)
        8. specificity: Concrete details vs abstract generalizations
        9. temporal_focus: -1 to 1 scale (past to future orientation)
        10. achievement_focus: References to goals, success, improvement
        11. risk_awareness: Mentions of concerns, problems, risks
        
        Reviews:
        {review_texts}
        
        Return JSON array with review_id and all features.
        """
        
        response = await self.claude.generate(prompt, response_format="json")
        
        # Parse into features dict
        features = {}
        for item in response:
            features[item["review_id"]] = {
                "text": next((r["text"] for r in review_texts if r["id"] == item["review_id"]), ""),
                **{k: v for k, v in item.items() if k != "review_id"}
            }
        
        return features
    
    def _cluster_by_linguistics(
        self,
        features: Dict[str, Dict[str, Any]],
        max_clusters: int
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Cluster reviews by linguistic feature similarity.
        
        Uses embedding-based clustering for better semantic grouping
        than simple feature-based k-means.
        """
        from sklearn.cluster import KMeans
        
        # Build feature vectors
        feature_keys = [
            "analytical_language", "emotional_intensity", "positive_emotion",
            "social_orientation", "certainty_level", "cognitive_complexity",
            "self_reference", "specificity", "achievement_focus", "risk_awareness"
        ]
        
        vectors = []
        review_ids = []
        for review_id, feat in features.items():
            vector = [feat.get(k, 0.5) for k in feature_keys]
            vectors.append(vector)
            review_ids.append(review_id)
        
        # Determine optimal cluster count
        n_clusters = min(max_clusters, max(2, len(vectors) // 25))
        
        # K-means clustering
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        labels = kmeans.fit_predict(np.array(vectors))
        
        # Group by cluster
        clusters = {}
        for i, label in enumerate(labels):
            cluster_key = f"cluster_{label}"
            if cluster_key not in clusters:
                clusters[cluster_key] = []
            clusters[cluster_key].append({
                "review_id": review_ids[i],
                **features[review_ids[i]]
            })
        
        return clusters
    
    async def _generate_segment_from_cluster(
        self,
        cluster_id: str,
        reviews: List[Dict[str, Any]],
        product: ProductKnowledgeNode
    ) -> CustomerPsychologicalSegment:
        """
        Use Claude to generate a full psychological profile from a review cluster.
        
        This is where the magic happens—Claude synthesizes linguistic
        patterns into coherent psychological profiles.
        """
        # Sample reviews for Claude (limit for context window)
        sample_reviews = reviews[:30] if len(reviews) > 30 else reviews
        
        # Prepare review summary
        review_summary = "\n".join([
            f"- {r.get('text', '')[:300]}..."
            for r in sample_reviews[:15]
        ])
        
        # Calculate aggregate feature scores
        feature_means = {}
        for key in ["analytical_language", "emotional_intensity", "social_orientation",
                    "certainty_level", "cognitive_complexity", "risk_awareness"]:
            values = [r.get(key, 0.5) for r in reviews if key in r]
            feature_means[key] = np.mean(values) if values else 0.5
        
        prompt = f"""
        Analyze these Amazon reviews for {product.product_name} ({product.category.value})
        to create a psychological customer segment profile.
        
        Aggregate linguistic features for this cluster:
        {feature_means}
        
        Sample reviews from this cluster:
        {review_summary}
        
        Based on the language patterns, provide a detailed psychological profile:
        
        1. SEGMENT NAME: A memorable descriptor (e.g., "Quality-Obsessed Researchers")
        
        2. BIG FIVE PERSONALITY TRAITS (0.0-1.0 scores with brief reasoning):
           - Openness to experience:
           - Conscientiousness:
           - Extraversion:
           - Agreeableness:
           - Neuroticism:
        
        3. REGULATORY FOCUS (0.0-1.0):
           - Promotion focus (gains, aspirations):
           - Prevention focus (safety, avoiding losses):
        
        4. PRIMARY VALUES (from: self-direction, stimulation, hedonism, achievement,
           power, security, conformity, tradition, benevolence, universalism):
        
        5. PURCHASE MOTIVATIONS (what drove these customers):
        
        6. RESONANT PHRASES (exact phrases that would appeal):
        
        7. AVERSIVE PHRASES (exact phrases to avoid):
        
        8. MECHANISM EFFECTIVENESS (0.0-1.0 for each):
           - Social proof ("10,000 5-star reviews"):
           - Scarcity ("Only 3 left"):
           - Authority ("Expert recommended"):
           - Reciprocity ("Free gift with purchase"):
           - Commitment ("Start with trial"):
           - Liking (Brand personality, aesthetics):
        
        9. CROSS-CATEGORY INTERESTS (what else might they buy):
        
        10. MEDIA PREFERENCES (what content contexts they likely consume):
        
        Respond in JSON format with all fields.
        """
        
        response = await self.claude.generate(prompt, response_format="json")
        
        # Parse into segment model
        segment = CustomerPsychologicalSegment(
            segment_id=str(uuid4()),
            segment_name=response.get("segment_name", f"Segment {cluster_id}"),
            estimated_percentage=len(reviews) / 100,  # Will be normalized later
            evidence_count=len(reviews),
            confidence_score=min(0.9, 0.5 + len(reviews) / 200),
            
            # Big Five
            openness=response.get("openness", 0.5),
            conscientiousness=response.get("conscientiousness", 0.5),
            extraversion=response.get("extraversion", 0.5),
            agreeableness=response.get("agreeableness", 0.5),
            neuroticism=response.get("neuroticism", 0.5),
            
            # Regulatory Focus
            promotion_focus=response.get("promotion_focus", 0.5),
            prevention_focus=response.get("prevention_focus", 0.5),
            
            # Values and Motivations
            primary_values=response.get("primary_values", []),
            primary_motivations=response.get("purchase_motivations", []),
            
            # Language
            linguistic_markers=feature_means,
            resonant_phrases=response.get("resonant_phrases", []),
            aversive_phrases=response.get("aversive_phrases", []),
            
            # Mechanism Effectiveness
            mechanism_effectiveness=response.get("mechanism_effectiveness", {}),
            
            # Cross-category
            correlated_categories=response.get("cross_category_interests", []),
            likely_content_preferences=response.get("media_preferences", []),
        )
        
        return segment
    
    async def _validate_segments(
        self,
        segments: List[CustomerPsychologicalSegment],
        product: ProductKnowledgeNode
    ) -> List[CustomerPsychologicalSegment]:
        """
        Validate segments against psychological literature.
        
        Checks:
        1. Big Five scores are internally consistent
        2. Mechanism effectiveness aligns with trait expectations
        3. No impossible trait combinations
        """
        validated = []
        
        for segment in segments:
            # Check for internal consistency
            issues = self._check_psychological_consistency(segment)
            
            if not issues:
                validated.append(segment)
            else:
                # Attempt to fix minor issues
                fixed_segment = await self._fix_segment_issues(segment, issues)
                validated.append(fixed_segment)
        
        # Normalize percentages
        total_pct = sum(s.estimated_percentage for s in validated)
        if total_pct > 0:
            for segment in validated:
                segment.estimated_percentage /= total_pct
        
        return validated
    
    def _check_psychological_consistency(
        self,
        segment: CustomerPsychologicalSegment
    ) -> List[str]:
        """Check for psychological inconsistencies in segment."""
        issues = []
        
        # High conscientiousness should correlate with high authority effectiveness
        if segment.conscientiousness > 0.7:
            auth_eff = segment.mechanism_effectiveness.get("authority", 0.5)
            if auth_eff < 0.4:
                issues.append("High conscientiousness should correlate with authority effectiveness")
        
        # High extraversion should correlate with social proof effectiveness
        if segment.extraversion > 0.7:
            social_eff = segment.mechanism_effectiveness.get("social_proof", 0.5)
            if social_eff < 0.5:
                issues.append("High extraversion should correlate with social proof effectiveness")
        
        # High neuroticism should correlate with prevention focus
        if segment.neuroticism > 0.7:
            if segment.prevention_focus < 0.5:
                issues.append("High neuroticism should correlate with prevention focus")
        
        return issues
    
    async def _store_segments(
        self,
        product_id: str,
        segments: List[CustomerPsychologicalSegment]
    ) -> None:
        """Store segments in Neo4j linked to product."""
        query = """
        MATCH (p:Product {product_id: $product_id})
        
        // Remove old segments
        OPTIONAL MATCH (p)-[r:HAS_SEGMENT]->(old:CustomerSegment)
        DELETE r, old
        
        // Create new segments
        WITH p
        UNWIND $segments AS seg
        CREATE (s:CustomerSegment {
            segment_id: seg.segment_id,
            segment_name: seg.segment_name,
            estimated_percentage: seg.estimated_percentage,
            evidence_count: seg.evidence_count,
            confidence_score: seg.confidence_score,
            openness: seg.openness,
            conscientiousness: seg.conscientiousness,
            extraversion: seg.extraversion,
            agreeableness: seg.agreeableness,
            neuroticism: seg.neuroticism,
            promotion_focus: seg.promotion_focus,
            prevention_focus: seg.prevention_focus,
            primary_values: seg.primary_values,
            primary_motivations: seg.primary_motivations,
            resonant_phrases: seg.resonant_phrases,
            aversive_phrases: seg.aversive_phrases,
            mechanism_effectiveness: seg.mechanism_effectiveness,
            correlated_categories: seg.correlated_categories,
            likely_content_preferences: seg.likely_content_preferences,
            created_at: datetime()
        })
        CREATE (p)-[:HAS_SEGMENT]->(s)
        
        RETURN count(s) AS created
        """
        
        async with self.neo4j.session(database=self.database) as session:
            await session.run(
                query,
                product_id=product_id,
                segments=[s.model_dump() for s in segments]
            )
```

This continues with the Web Intelligence Augmentation, Inventory Graph, and Matching Algorithm...

---

## Amazon Review Analysis Pipeline

```python
# =============================================================================
# ADAM Enhancement #28 v2.0: Amazon Review Analysis Pipeline
# Location: adam/ad_desk/amazon_pipeline.py
# =============================================================================

"""
Amazon Review Analysis Pipeline

Interfaces with the Amazon review corpus to extract reviews
for product/category analysis.

The Amazon corpus is our foundational data asset:
- 1.2B+ verified purchase reviews
- Complete product taxonomy
- Cross-category purchase patterns by customer ID
- Books data as psychographic bridge

This is the only dataset where VERIFIED PURCHASE BEHAVIOR
is directly coupled with UNSTRUCTURED LANGUAGE EXPRESSION at scale.
"""

from __future__ import annotations
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from neo4j import AsyncDriver

logger = logging.getLogger(__name__)


class AmazonCorpusClient:
    """
    Client for accessing the Amazon review corpus.
    
    Data structure in Neo4j:
    - (:AmazonProduct {asin, title, category, subcategory, brand, price})
    - (:AmazonReview {review_id, rating, text, verified_purchase, date})
    - (:AmazonCustomer {customer_id})  # Hashed for privacy
    - (:AmazonProduct)-[:HAS_REVIEW]->(:AmazonReview)
    - (:AmazonCustomer)-[:WROTE]->(:AmazonReview)
    - (:AmazonCustomer)-[:PURCHASED]->(:AmazonProduct)
    """
    
    def __init__(
        self,
        neo4j_driver: AsyncDriver,
        database: str = "amazon_corpus"
    ):
        self.driver = neo4j_driver
        self.database = database
    
    async def get_reviews_by_product_name(
        self,
        product_name: str,
        limit: int = 500
    ) -> List[Dict[str, Any]]:
        """Get reviews for products matching name (fuzzy match)."""
        query = """
        CALL db.index.fulltext.queryNodes("product_titles", $search_term)
        YIELD node AS product, score
        WHERE score > 0.5
        
        MATCH (product)-[:HAS_REVIEW]->(review:AmazonReview)
        WHERE review.verified_purchase = true
        
        RETURN {
            review_id: review.review_id,
            review_text: review.text,
            rating: review.rating,
            verified_purchase: review.verified_purchase,
            product_asin: product.asin,
            product_title: product.title,
            product_category: product.category,
            review_date: review.date
        } AS review
        ORDER BY review.date DESC
        LIMIT $limit
        """
        
        async with self.driver.session(database=self.database) as session:
            result = await session.run(
                query,
                search_term=product_name,
                limit=limit
            )
            records = await result.data()
            return [r["review"] for r in records]
    
    async def get_reviews_by_category(
        self,
        category: str,
        price_tier: Optional[str] = None,
        limit: int = 500
    ) -> List[Dict[str, Any]]:
        """Get reviews for products in a category."""
        
        # Map our categories to Amazon categories
        category_mapping = {
            "electronics": ["Electronics", "Computers", "Cell Phones"],
            "automotive": ["Automotive", "Automotive Parts"],
            "cpg_food": ["Grocery", "Food"],
            "cpg_beauty": ["Beauty", "Personal Care"],
            "home_goods": ["Home & Kitchen", "Furniture"],
            "fashion": ["Clothing", "Shoes", "Accessories"],
            "luxury": ["Luxury Beauty", "Luxury Stores"],
            # ... more mappings
        }
        
        amazon_categories = category_mapping.get(category, [category])
        
        # Price tier filters
        price_filters = {
            "budget": "product.price < 20",
            "value": "product.price >= 20 AND product.price < 100",
            "mainstream": "product.price >= 100 AND product.price < 500",
            "premium": "product.price >= 500 AND product.price < 2000",
            "luxury": "product.price >= 2000",
        }
        
        price_clause = price_filters.get(price_tier, "true")
        
        query = f"""
        MATCH (product:AmazonProduct)-[:HAS_REVIEW]->(review:AmazonReview)
        WHERE product.category IN $categories
        AND review.verified_purchase = true
        AND {price_clause}
        
        RETURN {{
            review_id: review.review_id,
            review_text: review.text,
            rating: review.rating,
            verified_purchase: review.verified_purchase,
            product_asin: product.asin,
            product_title: product.title,
            product_category: product.category,
            product_price: product.price,
            review_date: review.date
        }} AS review
        ORDER BY review.date DESC
        LIMIT $limit
        """
        
        async with self.driver.session(database=self.database) as session:
            result = await session.run(
                query,
                categories=amazon_categories,
                limit=limit
            )
            records = await result.data()
            return [r["review"] for r in records]
    
    async def get_cross_category_patterns(
        self,
        customer_segment_reviews: List[str]
    ) -> Dict[str, float]:
        """
        Analyze what other categories segment customers purchase.
        
        This enables cross-sell recommendations and lookalike expansion.
        """
        query = """
        // Find customers who wrote these reviews
        MATCH (review:AmazonReview)<-[:WROTE]-(customer:AmazonCustomer)
        WHERE review.review_id IN $review_ids
        
        // Find other products they purchased
        MATCH (customer)-[:PURCHASED]->(other_product:AmazonProduct)
        WHERE other_product.asin NOT IN [r.product_asin | r IN $review_ids]
        
        // Aggregate by category
        WITH other_product.category AS category, count(*) AS purchase_count
        
        RETURN category, purchase_count
        ORDER BY purchase_count DESC
        LIMIT 20
        """
        
        async with self.driver.session(database=self.database) as session:
            result = await session.run(query, review_ids=customer_segment_reviews)
            records = await result.data()
            
            total = sum(r["purchase_count"] for r in records)
            return {
                r["category"]: r["purchase_count"] / total
                for r in records
            }
```

---

## Web Intelligence Augmentation

```python
# =============================================================================
# ADAM Enhancement #28 v2.0: Web Intelligence Augmentation
# Location: adam/ad_desk/web_intelligence.py
# =============================================================================

"""
Web Intelligence Augmentation

Beyond Amazon reviews, we scrape web discussions to enrich profiles.

Sources:
- Reddit discussions (product-specific, category subreddits)
- Forum discussions (hobbyist, professional)
- Social media sentiment (Twitter/X, Instagram)
- Review aggregators (Trustpilot, G2 for B2B)

This captures:
- How people TALK about buying this product
- What alternatives they consider
- What triggers final purchase decision
- Post-purchase sentiment evolution
"""

from __future__ import annotations
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from adam.llm.claude_client import ClaudeClient

logger = logging.getLogger(__name__)


class WebIntelligenceAugmenter:
    """
    Augments product psychological profiles with web-scraped intelligence.
    """
    
    def __init__(self, claude_client: ClaudeClient):
        self.claude = claude_client
    
    async def augment_product_intelligence(
        self,
        product: 'ProductKnowledgeNode',
        segments: List['CustomerPsychologicalSegment']
    ) -> Dict[str, Any]:
        """
        Use Claude's web search to gather additional intelligence.
        """
        logger.info(f"Augmenting intelligence for: {product.product_name}")
        
        # Generate search queries
        queries = self._generate_search_queries(product)
        
        # Use Claude to search and synthesize
        web_insights = await self._gather_web_intelligence(product, queries)
        
        # Enrich segments with web-derived insights
        enriched_segments = await self._enrich_segments(segments, web_insights)
        
        # Extract competitive intelligence
        competitive_intel = await self._extract_competitive_intelligence(
            product, web_insights
        )
        
        return {
            "enriched_segments": enriched_segments,
            "competitive_intelligence": competitive_intel,
            "purchase_triggers": web_insights.get("purchase_triggers", []),
            "objection_patterns": web_insights.get("objections", []),
            "comparison_set": web_insights.get("alternatives", []),
            "sentiment_evolution": web_insights.get("sentiment_over_time", {}),
        }
    
    def _generate_search_queries(
        self,
        product: 'ProductKnowledgeNode'
    ) -> List[str]:
        """Generate targeted search queries for web research."""
        queries = [
            f"reddit {product.product_name} review",
            f"reddit {product.category.value} recommendations",
            f"why I bought {product.product_name}",
            f"{product.product_name} vs alternatives",
            f"{product.product_name} worth it",
            f"best {product.category.value} 2024 2025",
            f"{product.product_name} regret OR love",
            f"{product.product_name} buyer personality",
        ]
        
        # Add subcategory-specific queries
        for subcat in product.subcategories[:2]:
            queries.append(f"reddit best {subcat}")
        
        return queries
    
    async def _gather_web_intelligence(
        self,
        product: 'ProductKnowledgeNode',
        queries: List[str]
    ) -> Dict[str, Any]:
        """Use Claude to search and synthesize web intelligence."""
        
        prompt = f"""
        Research the following product and its customers using web search:
        
        Product: {product.product_name}
        Category: {product.category.value}
        Price: ${product.price}
        Description: {product.product_description[:500]}
        
        Search queries to investigate:
        {queries}
        
        For each query, find relevant discussions and extract:
        
        1. PURCHASE TRIGGERS: What specific events or thoughts trigger people
           to consider buying this product? (e.g., "my old one broke",
           "saw a friend using it", "read an article about X")
        
        2. DECISION FACTORS: What factors matter most in the decision?
           (Quality, price, brand, reviews, features, etc.)
        
        3. OBJECTIONS: What hesitations or concerns do people express
           before buying? What almost stopped them?
        
        4. ALTERNATIVES CONSIDERED: What other products do people compare
           this to? What makes them choose this over alternatives?
        
        5. PERSONALITY SIGNALS: What personality traits are evident in
           the language people use when discussing this product?
        
        6. POST-PURCHASE SENTIMENT: Are buyers generally satisfied?
           What do they love? What do they regret?
        
        7. WORD-OF-MOUTH PATTERNS: How do people describe this to others?
           What phrases do they use?
        
        Return structured JSON with these findings.
        """
        
        response = await self.claude.generate_with_search(
            prompt,
            response_format="json"
        )
        
        return response
    
    async def _enrich_segments(
        self,
        segments: List['CustomerPsychologicalSegment'],
        web_insights: Dict[str, Any]
    ) -> List['CustomerPsychologicalSegment']:
        """Enrich segments with web-derived insights."""
        
        # Extract common phrases from web discussions
        web_phrases = web_insights.get("resonant_language", [])
        web_objections = web_insights.get("objections", [])
        
        for segment in segments:
            # Add web-derived resonant phrases
            existing_phrases = set(segment.resonant_phrases)
            for phrase in web_phrases:
                if self._phrase_matches_segment(phrase, segment):
                    existing_phrases.add(phrase)
            segment.resonant_phrases = list(existing_phrases)
            
            # Add objection-handling needs
            segment.source_data["web_objections"] = [
                obj for obj in web_objections
                if self._objection_relevant_to_segment(obj, segment)
            ]
        
        return segments
    
    async def _extract_competitive_intelligence(
        self,
        product: 'ProductKnowledgeNode',
        web_insights: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Extract competitive positioning intelligence."""
        
        alternatives = web_insights.get("alternatives", [])
        
        return {
            "direct_competitors": alternatives[:5],
            "competitive_positioning": self._determine_positioning(
                product, alternatives
            ),
            "unique_selling_points": web_insights.get("usps", []),
            "vulnerability_areas": web_insights.get("weaknesses", []),
            "whitespace_opportunities": web_insights.get("unmet_needs", []),
        }
    
    def _phrase_matches_segment(
        self,
        phrase: str,
        segment: 'CustomerPsychologicalSegment'
    ) -> bool:
        """Check if a phrase matches segment psychological profile."""
        # High conscientiousness responds to quality/reliability language
        if segment.conscientiousness > 0.7:
            quality_words = ["quality", "reliable", "durable", "tested", "proven"]
            if any(w in phrase.lower() for w in quality_words):
                return True
        
        # High extraversion responds to social language
        if segment.extraversion > 0.7:
            social_words = ["popular", "everyone", "trending", "recommended"]
            if any(w in phrase.lower() for w in social_words):
                return True
        
        return False
```

---

## Inventory Knowledge Graph

```python
# =============================================================================
# ADAM Enhancement #28 v2.0: Inventory Knowledge Graph
# Location: adam/ad_desk/models/inventory.py
# =============================================================================

"""
Inventory Knowledge Graph Models

Transforms inventory from "impressions" into "psychological opportunities."

Key insight: Inventory has psychological context.
- Where you see an ad affects how you process it
- Content context induces psychological states
- Placement quality affects attention and processing depth
"""

from __future__ import annotations
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum
from uuid import uuid4
from pydantic import BaseModel, Field


class InventoryType(str, Enum):
    """Inventory types with psychological context implications."""
    # Display
    DISPLAY_STANDARD = "display_standard"      # Banner ads - low attention
    DISPLAY_NATIVE = "display_native"          # Native ads - higher engagement
    DISPLAY_RICH_MEDIA = "display_rich_media"  # Interactive - active processing
    
    # Video
    VIDEO_PREROLL = "video_preroll"           # Before content - captive audience
    VIDEO_MIDROLL = "video_midroll"           # During content - engaged state
    VIDEO_OUTSTREAM = "video_outstream"       # In-feed - interruptive
    
    # Connected TV
    CTV_STREAMING = "ctv_streaming"           # Lean-back, high attention
    
    # Audio
    AUDIO_STREAMING = "audio_streaming"       # Music services - passive
    AUDIO_PODCAST = "audio_podcast"           # Podcasts - engaged, trusting
    AUDIO_TERRESTRIAL = "audio_terrestrial"   # Radio - habitual, broad
    
    # Out of Home
    DOOH = "dooh"                             # Digital billboards - fleeting
    
    # Social
    SOCIAL_FEED = "social_feed"               # In-feed - scroll state
    SOCIAL_STORIES = "social_stories"         # Stories - lean-forward, fast
    
    # Commerce
    RETAIL_MEDIA = "retail_media"             # At point of purchase
    SEARCH = "search"                         # Intent-driven


class ContentContext(str, Enum):
    """Content context that maps to psychological states."""
    # News
    NEWS_HARD = "news_hard"           # Politics, conflict - high arousal, analytical
    NEWS_SOFT = "news_soft"           # Lifestyle, human interest - moderate arousal
    
    # Entertainment
    ENTERTAINMENT_COMEDY = "entertainment_comedy"     # Comedy - positive affect, low guard
    ENTERTAINMENT_DRAMA = "entertainment_drama"       # Drama - emotional engagement
    ENTERTAINMENT_ACTION = "entertainment_action"     # Action - high arousal
    
    # Sports
    SPORTS_LIVE = "sports_live"               # Live sports - excitement, social
    SPORTS_HIGHLIGHTS = "sports_highlights"   # Highlights - positive anticipation
    
    # Music
    MUSIC_DISCOVERY = "music_discovery"       # Exploring - openness high
    MUSIC_AMBIENT = "music_ambient"           # Background - low attention
    MUSIC_WORKOUT = "music_workout"           # Exercise - high arousal
    
    # Podcasts
    PODCAST_NEWS = "podcast_news"             # News pods - informed, analytical
    PODCAST_COMEDY = "podcast_comedy"         # Comedy pods - positive, relaxed
    PODCAST_EDUCATIONAL = "podcast_educational"  # Learning - open, curious
    PODCAST_TRUE_CRIME = "podcast_true_crime" # True crime - engaged, curious
    PODCAST_BUSINESS = "podcast_business"     # Business - professional, ambitious
    
    # Lifestyle
    LIFESTYLE_FITNESS = "lifestyle_fitness"   # Fitness - aspirational, motivated
    LIFESTYLE_COOKING = "lifestyle_cooking"   # Cooking - practical, engaged
    LIFESTYLE_TRAVEL = "lifestyle_travel"     # Travel - dreaming, aspirational
    
    # Other
    GAMING = "gaming"                         # Gaming - immersed, competitive
    SHOPPING = "shopping"                     # Shopping content - purchase mode


class PublisherNode(BaseModel):
    """
    Publisher representation with psychological context.
    """
    publisher_id: str
    publisher_name: str
    domain: str
    
    # Quality Metrics
    brand_safety_score: float = Field(default=0.8, ge=0.0, le=1.0)
    viewability_average: float = Field(default=0.6, ge=0.0, le=1.0)
    fraud_risk_score: float = Field(default=0.1, ge=0.0, le=1.0)
    attention_score: float = Field(default=0.5, ge=0.0, le=1.0)
    
    # Psychological Profile of Audience
    audience_psychological_profile: Optional['PsychologicalResonance'] = None
    dominant_traits: Dict[str, float] = Field(default_factory=dict)
    # e.g., {"openness": 0.7, "conscientiousness": 0.6}
    
    # Content Context
    primary_content_contexts: List[ContentContext] = Field(default_factory=list)
    
    # State Induction (what states does this publisher's content induce?)
    typical_user_state: Dict[str, Any] = Field(default_factory=dict)
    # {"arousal": 0.6, "construal": "analytical", "attention_depth": "focused"}
    
    # Placements
    placements: List['PlacementNode'] = Field(default_factory=list)
    
    # Embeddings
    audience_embedding: List[float] = Field(default_factory=list)
    content_embedding: List[float] = Field(default_factory=list)


class PlacementNode(BaseModel):
    """Individual placement within a publisher."""
    placement_id: str
    publisher_id: str
    placement_name: str
    inventory_type: InventoryType
    
    # Size/Format
    dimensions: Optional[str] = None  # "300x250", "728x90"
    video_duration_seconds: Optional[int] = None
    
    # Quality
    viewability_rate: float = Field(default=0.6, ge=0.0, le=1.0)
    completion_rate: Optional[float] = None  # For video/audio
    
    # Pricing
    floor_cpm: float = Field(default=1.0, ge=0.0)
    avg_clearing_cpm: float = Field(default=2.0, ge=0.0)
    
    # Performance History
    historical_ctr: float = Field(default=0.005, ge=0.0)
    historical_cvr: float = Field(default=0.01, ge=0.0)
    
    # Psychological Context
    attention_quality: str = "standard"  # low, standard, high, premium
    engagement_depth: str = "passive"    # passive, light, active, immersive
    
    # Content Context
    primary_contexts: List[ContentContext] = Field(default_factory=list)
    
    # Deal Access
    deal_types_available: List[str] = Field(default_factory=list)
    # ["open_exchange", "pmp", "preferred_deal", "pg"]


class InventoryOpportunity(BaseModel):
    """
    A real-time inventory opportunity for bidding.
    
    This is what we receive at bid time and must make decisions on.
    """
    opportunity_id: str
    timestamp: datetime
    
    # Inventory Details
    publisher_id: str
    placement_id: str
    inventory_type: InventoryType
    
    # Context
    content_context: ContentContext
    content_url: Optional[str] = None
    content_keywords: List[str] = Field(default_factory=list)
    
    # User Signals (if available)
    user_id_hashed: Optional[str] = None
    user_segments: List[str] = Field(default_factory=list)
    
    # Quality
    viewability_prediction: float = Field(ge=0.0, le=1.0)
    attention_score: float = Field(ge=0.0, le=1.0)
    
    # Pricing
    floor_cpm: float
    
    # Psychological Context (enriched by ADAM)
    psychological_context: Optional[Dict[str, Any]] = None
```

---

## Product-to-Inventory Matching Algorithm

```python
# =============================================================================
# ADAM Enhancement #28 v2.0: Product-to-Inventory Matching
# Location: adam/ad_desk/matcher.py
# =============================================================================

"""
Product-to-Inventory Matching Engine

The core matching algorithm that connects:
- Product psychological segments
- Inventory psychological contexts

Key insight: We don't match demographics to content.
We match psychological profiles to psychological contexts.
"""

from __future__ import annotations
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from uuid import uuid4
import numpy as np
from neo4j import AsyncDriver

from adam.ad_desk.models.product import (
    ProductKnowledgeNode, CustomerPsychologicalSegment, PsychologicalResonance
)
from adam.ad_desk.models.inventory import (
    PublisherNode, PlacementNode, InventoryType, ContentContext
)

logger = logging.getLogger(__name__)


class ProductToInventoryMatcher:
    """
    Core matching engine for Product-to-Inventory recommendations.
    
    Takes:
    - Product Knowledge Graph (product + psychological segments)
    - Inventory Knowledge Graph (publishers + audiences + contexts)
    
    Returns:
    - Recommended PMPs/Curated Deals
    - Recommended Contextual Segments
    - Recommended Audiences
    - Recommended Exclusions
    - Complete Deployment Plan
    """
    
    def __init__(
        self,
        neo4j_driver: AsyncDriver,
        blackboard: Optional[Any] = None,
        gradient_bridge: Optional[Any] = None,
        database: str = "neo4j"
    ):
        self.neo4j = neo4j_driver
        self.blackboard = blackboard
        self.gradient_bridge = gradient_bridge
        self.database = database
    
    async def generate_recommendations(
        self,
        product_id: str,
        budget_usd: float,
        campaign_duration_days: int,
        campaign_objectives: List[str]
    ) -> 'InventoryRecommendation':
        """
        Generate complete inventory recommendations for a product.
        
        This is the main entry point for the matching engine.
        """
        logger.info(f"Generating recommendations for product: {product_id}")
        
        # Load product with full context
        product = await self._load_product_full_context(product_id)
        if not product:
            raise ValueError(f"Product not found: {product_id}")
        
        # Get psychological segments
        segments = product.customer_segments
        if not segments:
            logger.warning("No segments found, using category defaults")
            segments = await self._generate_category_default_segments(product)
        
        # Initialize recommendation
        recommendation = InventoryRecommendation(
            product_id=product_id,
            generated_at=datetime.utcnow(),
        )
        
        # 1. MATCH SEGMENTS TO DEALS/PMPS
        recommendation.recommended_deals = await self._match_segments_to_deals(
            segments, product, budget_usd
        )
        
        # 2. GENERATE CONTEXTUAL SEGMENT RECOMMENDATIONS
        recommendation.contextual_segments = await self._generate_contextual_recommendations(
            segments, product
        )
        
        # 3. GENERATE AUDIENCE RECOMMENDATIONS
        recommendation.audiences = await self._generate_audience_recommendations(
            segments, product
        )
        
        # 4. GENERATE EXCLUSIONS (Brand Safety + Wasted Adjacency)
        recommendation.exclusions = await self._generate_exclusions(
            product, segments
        )
        
        # 5. GENERATE DEPLOYMENT PLAN
        recommendation.deployment_plan = await self._generate_deployment_plan(
            product, segments, recommendation, budget_usd, campaign_duration_days
        )
        
        # Calculate overall confidence
        recommendation.overall_confidence = self._calculate_recommendation_confidence(
            recommendation
        )
        
        # Emit learning signal
        if self.gradient_bridge:
            await self._emit_recommendation_signal(recommendation)
        
        return recommendation
    
    async def _match_segments_to_deals(
        self,
        segments: List[CustomerPsychologicalSegment],
        product: ProductKnowledgeNode,
        budget_usd: float
    ) -> List['DealRecommendation']:
        """
        Match psychological segments to specific PMPs and deals.
        
        The key insight: We're not matching demographics to content.
        We're matching psychological profiles to psychological contexts.
        """
        recommendations = []
        
        for segment in segments:
            # Find publishers whose audience profile aligns with segment
            matching_publishers = await self._find_aligned_publishers(segment, product)
            
            for publisher, alignment_score in matching_publishers:
                # Find best deals for this publisher
                deals = await self._get_publisher_deals(publisher.publisher_id)
                
                for deal in deals:
                    # Score the deal opportunity
                    deal_score = self._score_deal_opportunity(
                        segment, publisher, deal, alignment_score
                    )
                    
                    recommendations.append(DealRecommendation(
                        deal_id=deal.get("deal_id"),
                        deal_name=deal.get("deal_name"),
                        publisher_id=publisher.publisher_id,
                        publisher_name=publisher.publisher_name,
                        deal_type=deal.get("deal_type"),
                        target_segment=segment.segment_name,
                        psychological_alignment_score=alignment_score,
                        deal_quality_score=deal_score,
                        expected_lift=self._estimate_lift(alignment_score),
                        recommended_budget_allocation=self._allocate_budget(
                            alignment_score, segment.estimated_percentage, budget_usd
                        ),
                        rationale=self._generate_deal_rationale(
                            segment, publisher, alignment_score
                        ),
                        floor_cpm=deal.get("floor_cpm", 2.0),
                        expected_cpm=deal.get("expected_cpm", 3.0),
                    ))
        
        # Sort by combined score and deduplicate
        recommendations.sort(
            key=lambda x: x.psychological_alignment_score * x.deal_quality_score,
            reverse=True
        )
        
        # Return top recommendations
        return self._deduplicate_recommendations(recommendations)[:25]
    
    async def _find_aligned_publishers(
        self,
        segment: CustomerPsychologicalSegment,
        product: ProductKnowledgeNode
    ) -> List[Tuple[PublisherNode, float]]:
        """
        Find publishers whose audience aligns psychologically with segment.
        """
        # Query for publishers with psychological profiles
        query = """
        MATCH (pub:Publisher)
        WHERE pub.audience_psychological_profile IS NOT NULL
        
        // Get psychological profile
        WITH pub, pub.audience_psychological_profile AS profile
        
        // Calculate trait alignment
        WITH pub, profile,
             abs($segment_openness - profile.openness_affinity) AS openness_diff,
             abs($segment_conscientiousness - profile.conscientiousness_affinity) AS consc_diff,
             abs($segment_extraversion - profile.extraversion_affinity) AS extra_diff,
             abs($segment_agreeableness - profile.agreeableness_affinity) AS agree_diff,
             abs($segment_neuroticism - profile.neuroticism_affinity) AS neuro_diff
        
        // Calculate overall alignment (lower diff = better alignment)
        WITH pub, profile,
             1 - (openness_diff + consc_diff + extra_diff + agree_diff + neuro_diff) / 5 AS trait_alignment
        
        WHERE trait_alignment > 0.5
        
        RETURN pub, trait_alignment
        ORDER BY trait_alignment DESC
        LIMIT 50
        """
        
        async with self.neo4j.session(database=self.database) as session:
            result = await session.run(
                query,
                segment_openness=segment.openness,
                segment_conscientiousness=segment.conscientiousness,
                segment_extraversion=segment.extraversion,
                segment_agreeableness=segment.agreeableness,
                segment_neuroticism=segment.neuroticism,
            )
            records = await result.data()
            
            aligned = []
            for record in records:
                pub_data = dict(record["pub"])
                publisher = PublisherNode(**pub_data)
                alignment = record["trait_alignment"]
                aligned.append((publisher, alignment))
            
            return aligned
    
    def _calculate_psychological_alignment(
        self,
        segment: CustomerPsychologicalSegment,
        audience_profile: PsychologicalResonance
    ) -> float:
        """
        Calculate how well a customer segment aligns with an audience.
        
        Higher alignment = higher expected conversion.
        """
        # Trait alignment (weighted)
        trait_alignment = (
            (1 - abs(segment.openness - audience_profile.openness_affinity)) * 0.2 +
            (1 - abs(segment.conscientiousness - audience_profile.conscientiousness_affinity)) * 0.2 +
            (1 - abs(segment.extraversion - audience_profile.extraversion_affinity)) * 0.2 +
            (1 - abs(segment.agreeableness - audience_profile.agreeableness_affinity)) * 0.2 +
            (1 - abs(segment.neuroticism - audience_profile.neuroticism_affinity)) * 0.2
        )
        
        # Regulatory focus alignment
        reg_alignment = (
            segment.promotion_focus * audience_profile.promotion_alignment +
            segment.prevention_focus * audience_profile.prevention_alignment
        )
        
        # Mechanism alignment
        mech_keys = ["social_proof", "scarcity", "authority", "reciprocity", "commitment", "liking"]
        mech_alignment = 0.0
        mech_count = 0
        
        for mech in mech_keys:
            segment_eff = segment.mechanism_effectiveness.get(mech, 0.5)
            audience_eff = getattr(audience_profile, f"{mech}_effectiveness", 0.5)
            mech_alignment += segment_eff * audience_eff
            mech_count += 1
        
        mech_alignment = mech_alignment / mech_count if mech_count > 0 else 0.5
        
        # Combined score (weighted)
        total_alignment = (
            trait_alignment * 0.4 +
            reg_alignment * 0.3 +
            mech_alignment * 0.3
        )
        
        return round(total_alignment, 3)
    
    def _estimate_lift(self, alignment_score: float) -> float:
        """
        Estimate conversion lift based on psychological alignment.
        
        Based on Matz et al. (PNAS, 2017):
        - 40% lift with perfect personality matching
        - Apply 0.62 calibration factor for real-world conditions
        """
        base_lift = 0.40  # 40% potential lift
        calibration = 0.62  # Real-world adjustment
        
        expected_lift = base_lift * calibration * alignment_score
        return round(expected_lift, 3)


# =============================================================================
# RECOMMENDATION OUTPUT MODELS
# =============================================================================

class DealRecommendation(BaseModel):
    """A recommended PMP or deal."""
    deal_id: str
    deal_name: str
    publisher_id: str
    publisher_name: str
    deal_type: str  # "pmp", "preferred_deal", "pg", "open_exchange"
    target_segment: str
    psychological_alignment_score: float = Field(ge=0.0, le=1.0)
    deal_quality_score: float = Field(ge=0.0, le=1.0)
    expected_lift: float = Field(ge=0.0)
    recommended_budget_allocation: float = Field(ge=0.0)
    rationale: str
    floor_cpm: float
    expected_cpm: float


class ContextualSegmentRecommendation(BaseModel):
    """A recommended contextual segment."""
    segment_name: str
    segment_definition: Dict[str, Any]
    target_psychological_segment: str
    alignment_score: float = Field(ge=0.0, le=1.0)
    recommended_budget_allocation: float = Field(ge=0.0)
    rationale: str


class AudienceRecommendation(BaseModel):
    """A recommended audience segment."""
    audience_type: str  # "first_party", "modeled", "lookalike", "third_party"
    audience_name: str
    audience_definition: Dict[str, Any]
    target_psychological_segment: str
    expected_overlap: float = Field(ge=0.0, le=1.0)
    recommended_budget_allocation: float = Field(ge=0.0)
    rationale: str


class ExclusionRecommendation(BaseModel):
    """Recommended exclusions."""
    brand_safety_exclusions: List[str]
    wasted_adjacency_exclusions: List[str]
    competitive_exclusions: List[str]
    exclusion_rationale: Dict[str, str]


class DeploymentPlan(BaseModel):
    """Complete deployment plan for the campaign."""
    segment_plans: List['SegmentDeploymentPlan'] = Field(default_factory=list)
    total_budget: float
    duration_days: int
    recommended_daily_spend: float
    expected_total_lift: float
    launch_sequence: List[str] = Field(default_factory=list)
    learning_period_days: int = 7
    optimization_triggers: List[str] = Field(default_factory=list)


class SegmentDeploymentPlan(BaseModel):
    """Deployment plan for a single psychological segment."""
    segment_id: str
    segment_name: str
    budget_allocation_usd: float
    budget_percentage: float
    optimal_dayparts: List[str]
    optimal_days_of_week: List[str]
    messaging_strategy: 'MessagingStrategy'
    recommended_inventory_types: List[str]
    recommended_deals: List[str]
    recommended_frequency_cap: int
    pacing_strategy: str


class MessagingStrategy(BaseModel):
    """Messaging strategy for a segment."""
    primary_mechanism: str
    secondary_mechanisms: List[str] = Field(default_factory=list)
    resonant_phrases: List[str] = Field(default_factory=list)
    avoid_phrases: List[str] = Field(default_factory=list)
    tone: str
    urgency_level: str
    headline_guidance: str = ""
    body_copy_themes: List[str] = Field(default_factory=list)
    cta_style: str = ""


class InventoryRecommendation(BaseModel):
    """Complete inventory recommendation output."""
    product_id: str
    generated_at: datetime
    
    # Recommendations
    recommended_deals: List[DealRecommendation] = Field(default_factory=list)
    contextual_segments: List[ContextualSegmentRecommendation] = Field(default_factory=list)
    audiences: List[AudienceRecommendation] = Field(default_factory=list)
    exclusions: Optional[ExclusionRecommendation] = None
    
    # Deployment Plan
    deployment_plan: Optional[DeploymentPlan] = None
    
    # Confidence
    overall_confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    expected_lift_vs_baseline: float = Field(default=0.0, ge=0.0)
```

---

# SECTION C: PRODUCT 2 - SEQUENTIAL PERSUASION

## Product 2 Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                     SEQUENTIAL PERSUASION: GRAPH-BASED JOURNEYS                     │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                     │
│   TRADITIONAL APPROACH (Flat)              ADAM APPROACH (Graph)                    │
│   ─────────────────────────────            ─────────────────────                    │
│                                                                                     │
│   Creative A ─┬─► User                     ┌──────────────────────────────────┐    │
│   Creative B ─┤   (rotate)                 │      USER DECISION GRAPH         │    │
│   Creative C ─┘                            │                                  │    │
│                                            │   ┌─────────┐                    │    │
│   Problems:                                │   │DISCOVERY│ ← Creative A       │    │
│   • No state awareness                     │   │(explore)│   (liking)         │    │
│   • No journey context                     │   └────┬────┘                    │    │
│   • Wasted frequency                       │        │ engagement              │    │
│   • No mechanism sequencing                │        ▼                         │    │
│                                            │   ┌─────────────┐                │    │
│                                            │   │CONSIDERATION│ ← Creative B   │    │
│                                            │   │ (compare)   │   (social proof)│   │
│                                            │   └──────┬──────┘                │    │
│                                            │          │ intent signal         │    │
│                                            │          ▼                       │    │
│                                            │   ┌──────────┐                   │    │
│                                            │   │CONVERSION │ ← Creative C     │    │
│                                            │   │ (decide)  │   (scarcity)     │    │
│                                            │   └──────────┘                   │    │
│                                            │                                  │    │
│                                            │   Inventory selected per state   │    │
│                                            │   Mechanism sequenced optimally  │    │
│                                            │   Transitions trigger advances   │    │
│                                            └──────────────────────────────────┘    │
│                                                                                     │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

## Journey State Model

```python
# =============================================================================
# ADAM Enhancement #28 v2.0: Sequential Persuasion - Journey Model
# Location: adam/ad_desk/models/journey.py
# =============================================================================

"""
Journey State Model for Sequential Persuasion

Key insight: These are NOT funnel stages.
They're psychological states that users transition between (sometimes non-linearly).

The graph captures:
- Transition probabilities between states
- Mechanism enhancers per transition
- Inventory preferences per state
- User-specific journey positions
"""

from __future__ import annotations
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum
from uuid import uuid4
from pydantic import BaseModel, Field


class JourneyState(str, Enum):
    """
    Psychological states in the purchase decision graph.
    """
    UNAWARE = "unaware"           # Not yet exposed to category need
    DISCOVERY = "discovery"       # High openness, exploration mode
    CONSIDERATION = "consideration"  # Analytical, comparison mode
    INTENT = "intent"            # Approach motivation activated
    CONVERSION = "conversion"    # Decision-ready, action mode
    POST_PURCHASE = "post_purchase"  # Evaluation, satisfaction mode
    ADVOCACY = "advocacy"        # Social sharing, recommendation mode


class JourneyTransition(BaseModel):
    """
    Represents a transition between journey states.
    
    In the graph, this is an edge connecting two state nodes.
    """
    transition_id: str = Field(default_factory=lambda: str(uuid4()))
    from_state: JourneyState
    to_state: JourneyState
    
    # Transition Triggers
    trigger_type: str  # "impression", "engagement", "time", "external_signal"
    trigger_threshold: float
    
    # Base Probability
    base_transition_probability: float = Field(ge=0.0, le=1.0)
    
    # Mechanism Enhancers (multipliers)
    mechanism_enhancers: Dict[str, float] = Field(default_factory=dict)
    # e.g., {"social_proof": 1.3, "scarcity": 1.5}
    
    # Inventory Enhancers (multipliers)
    inventory_enhancers: Dict[str, float] = Field(default_factory=dict)
    # e.g., {"video_preroll": 1.2, "native_display": 1.1}
    
    # Timing
    min_time_in_state_hours: int = 0
    optimal_time_in_state_hours: int = 24
    max_time_in_state_hours: int = 168  # 1 week
    
    # Learning
    observed_transitions: int = 0
    success_rate: float = Field(default=0.5, ge=0.0, le=1.0)


class UserJourneyPosition(BaseModel):
    """
    A user's current position in the decision graph.
    """
    user_id: str
    product_id: str
    sequence_id: str
    
    # Current State
    current_state: JourneyState
    current_step_position: int = 0
    entered_state_at: datetime
    
    # History
    state_history: List[Dict[str, Any]] = Field(default_factory=list)
    # [{state, entered_at, exited_at, impressions, engagements}]
    
    # Exposure Tracking
    total_impressions: int = 0
    impressions_in_current_state: int = 0
    last_impression_at: Optional[datetime] = None
    
    # Engagement Tracking
    total_engagements: int = 0
    engagement_depth: float = 0.0  # 0-1 aggregate
    
    # Transition Readiness
    transition_probability: float = Field(ge=0.0, le=1.0)
    recommended_next_state: Optional[JourneyState] = None
    
    # Personalization (what works for this user)
    effective_mechanisms: List[str] = Field(default_factory=list)
    ineffective_mechanisms: List[str] = Field(default_factory=list)


class SequenceStep(BaseModel):
    """
    A single step in a persuasion sequence.
    
    Each step is designed for a specific journey state
    with state-appropriate inventory and messaging.
    """
    step_id: str = Field(default_factory=lambda: str(uuid4()))
    sequence_position: int = Field(ge=0)
    
    # Target State
    target_journey_state: JourneyState
    
    # Creative Strategy
    creative_strategy: 'CreativeStrategy'
    
    # Inventory Selection
    inventory_config: 'StepInventoryConfig'
    
    # Timing
    timing_config: 'StepTimingConfig'
    
    # Transition
    advance_config: 'StepAdvanceConfig'
    
    # Learning
    is_learning: bool = True
    exploration_rate: float = 0.2


class CreativeStrategy(BaseModel):
    """Creative strategy for a sequence step."""
    primary_mechanism: str
    # e.g., "liking" for discovery, "social_proof" for consideration
    secondary_mechanisms: List[str] = Field(default_factory=list)
    
    tone: str
    # "inspirational", "informational", "analytical", "urgent"
    
    content_focus: str
    # "brand_story", "product_benefits", "social_proof", "offer_details"
    
    cta_style: str
    # "soft" (learn more), "medium" (see options), "hard" (buy now)
    
    headline_templates: List[str] = Field(default_factory=list)
    resonant_phrases: List[str] = Field(default_factory=list)
    avoid_phrases: List[str] = Field(default_factory=list)


class StepInventoryConfig(BaseModel):
    """Inventory configuration for a sequence step."""
    preferred_types: List[str] = Field(default_factory=list)
    preferred_contexts: List[str] = Field(default_factory=list)
    minimum_attention_score: float = Field(default=0.3, ge=0.0, le=1.0)
    minimum_viewability: float = Field(default=0.5, ge=0.0, le=1.0)
    excluded_contexts: List[str] = Field(default_factory=list)


class StepTimingConfig(BaseModel):
    """Timing configuration for a sequence step."""
    min_gap_hours: int = 0
    optimal_gap_hours: int = 24
    max_gap_hours: int = 168
    preferred_dayparts: List[str] = Field(default_factory=list)
    preferred_days: List[str] = Field(default_factory=list)
    max_frequency: int = 3
    min_frequency: int = 1


class StepAdvanceConfig(BaseModel):
    """Configuration for advancing to next step."""
    trigger_type: str = "impression_count"
    # "impression_count", "engagement", "time_elapsed", "conversion_signal"
    trigger_threshold: float = 2.0
    max_time_in_step_hours: int = 72
    fallback_behavior: str = "advance"  # "advance", "skip_to_end", "restart"


class PersuasionSequence(BaseModel):
    """
    Complete persuasion sequence for a product.
    
    This is NOT a simple "frequency cap and rotate" approach.
    It's a psychologically-informed journey through decision states.
    """
    sequence_id: str = Field(default_factory=lambda: str(uuid4()))
    product_id: str
    
    # Steps
    steps: List[SequenceStep] = Field(default_factory=list)
    
    # Overall Configuration
    total_duration_days: int = Field(default=30, ge=1)
    total_frequency_cap: int = Field(default=15, ge=1)
    
    # Learning
    is_learning: bool = True
    exploration_rate: float = 0.2
    
    # Performance
    users_in_sequence: int = 0
    completion_rate: float = 0.0
    conversion_rate: float = 0.0
    
    # Versioning
    version: int = 1
    parent_sequence_id: Optional[str] = None
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
```

---

## Sequence Templates Library

```python
# =============================================================================
# ADAM Enhancement #28 v2.0: Sequence Templates
# Location: adam/ad_desk/sequence_templates.py
# =============================================================================

"""
Sequence Template Library

Pre-built sequence templates based on product characteristics.

Key insight: Different products require different journey structures.
- High-involvement: Longer sequences, more consideration steps
- Low-involvement: Quick path to conversion
- Brand building: Focus on reach and recall, not direct response
"""

from typing import List
from adam.ad_desk.models.journey import (
    SequenceStep, JourneyState, CreativeStrategy,
    StepInventoryConfig, StepTimingConfig, StepAdvanceConfig
)


class SequenceTemplates:
    """Pre-built sequence templates."""
    
    @staticmethod
    def high_involvement_sequence() -> List[SequenceStep]:
        """
        For high-involvement purchases: electronics, automotive, financial services
        
        Longer sequence, more analytical content, multiple touchpoints.
        """
        return [
            # Step 1: DISCOVERY
            SequenceStep(
                sequence_position=0,
                target_journey_state=JourneyState.DISCOVERY,
                creative_strategy=CreativeStrategy(
                    primary_mechanism="liking",
                    secondary_mechanisms=["authority"],
                    tone="inspirational",
                    content_focus="brand_story",
                    cta_style="soft",
                    headline_templates=[
                        "Discover what's possible with {product}",
                        "See why experts choose {brand}",
                    ],
                ),
                inventory_config=StepInventoryConfig(
                    preferred_types=["video_preroll", "video_outstream", "ctv_streaming"],
                    preferred_contexts=["entertainment", "lifestyle"],
                    minimum_attention_score=0.5,
                ),
                timing_config=StepTimingConfig(
                    max_frequency=2,
                    preferred_dayparts=["evening_relax", "weekend"],
                ),
                advance_config=StepAdvanceConfig(
                    trigger_type="engagement",
                    trigger_threshold=0.3,
                    max_time_in_step_hours=48,
                ),
            ),
            
            # Step 2: CONSIDERATION
            SequenceStep(
                sequence_position=1,
                target_journey_state=JourneyState.CONSIDERATION,
                creative_strategy=CreativeStrategy(
                    primary_mechanism="social_proof",
                    secondary_mechanisms=["authority", "commitment"],
                    tone="informational",
                    content_focus="product_benefits",
                    cta_style="medium",
                    headline_templates=[
                        "Why 10,000+ customers chose {product}",
                        "Compare {product} features",
                    ],
                ),
                inventory_config=StepInventoryConfig(
                    preferred_types=["display_native", "video_preroll"],
                    preferred_contexts=["news_soft", "technology", "reviews"],
                    minimum_attention_score=0.4,
                ),
                timing_config=StepTimingConfig(
                    min_gap_hours=12,
                    optimal_gap_hours=36,
                    max_frequency=4,
                ),
                advance_config=StepAdvanceConfig(
                    trigger_type="impression_count",
                    trigger_threshold=3,
                    max_time_in_step_hours=96,
                ),
            ),
            
            # Step 3: INTENT
            SequenceStep(
                sequence_position=2,
                target_journey_state=JourneyState.INTENT,
                creative_strategy=CreativeStrategy(
                    primary_mechanism="commitment",
                    secondary_mechanisms=["reciprocity", "scarcity"],
                    tone="analytical",
                    content_focus="offer_details",
                    cta_style="medium",
                    headline_templates=[
                        "Your {product} is waiting",
                        "Exclusive offer for interested buyers",
                    ],
                ),
                inventory_config=StepInventoryConfig(
                    preferred_types=["display_standard", "display_native", "search"],
                    preferred_contexts=["shopping", "reviews", "comparison"],
                    minimum_attention_score=0.3,
                ),
                timing_config=StepTimingConfig(
                    min_gap_hours=24,
                    optimal_gap_hours=48,
                    max_frequency=3,
                ),
                advance_config=StepAdvanceConfig(
                    trigger_type="engagement",
                    trigger_threshold=0.5,
                    max_time_in_step_hours=72,
                ),
            ),
            
            # Step 4: CONVERSION
            SequenceStep(
                sequence_position=3,
                target_journey_state=JourneyState.CONVERSION,
                creative_strategy=CreativeStrategy(
                    primary_mechanism="scarcity",
                    secondary_mechanisms=["social_proof", "authority"],
                    tone="urgent",
                    content_focus="urgency",
                    cta_style="hard",
                    headline_templates=[
                        "Last chance: Your exclusive offer expires soon",
                        "Complete your purchase today",
                    ],
                ),
                inventory_config=StepInventoryConfig(
                    preferred_types=["display_standard", "retail_media", "search"],
                    preferred_contexts=["shopping", "comparison"],
                    minimum_attention_score=0.2,
                ),
                timing_config=StepTimingConfig(
                    min_gap_hours=12,
                    optimal_gap_hours=24,
                    max_frequency=5,
                ),
                advance_config=StepAdvanceConfig(
                    trigger_type="conversion_signal",
                    trigger_threshold=1.0,
                    max_time_in_step_hours=48,
                ),
            ),
        ]
    
    @staticmethod
    def low_involvement_sequence() -> List[SequenceStep]:
        """
        For low-involvement purchases: CPG, entertainment, impulse.
        
        Shorter sequence, emotional content, quick conversion path.
        """
        return [
            # Step 1: DISCOVERY + INTEREST (combined)
            SequenceStep(
                sequence_position=0,
                target_journey_state=JourneyState.DISCOVERY,
                creative_strategy=CreativeStrategy(
                    primary_mechanism="liking",
                    secondary_mechanisms=["social_proof"],
                    tone="fun",
                    content_focus="brand_story",
                    cta_style="soft",
                ),
                inventory_config=StepInventoryConfig(
                    preferred_types=["social_feed", "social_stories", "video_outstream"],
                    preferred_contexts=["entertainment_comedy", "music", "lifestyle"],
                    minimum_attention_score=0.3,
                ),
                timing_config=StepTimingConfig(
                    max_frequency=2,
                ),
                advance_config=StepAdvanceConfig(
                    trigger_type="impression_count",
                    trigger_threshold=1,
                    max_time_in_step_hours=24,
                ),
            ),
            
            # Step 2: CONVERSION (quick close)
            SequenceStep(
                sequence_position=1,
                target_journey_state=JourneyState.CONVERSION,
                creative_strategy=CreativeStrategy(
                    primary_mechanism="scarcity",
                    secondary_mechanisms=["reciprocity"],
                    tone="urgent",
                    content_focus="offer_details",
                    cta_style="hard",
                ),
                inventory_config=StepInventoryConfig(
                    preferred_types=["display_standard", "retail_media"],
                    preferred_contexts=["shopping"],
                ),
                timing_config=StepTimingConfig(
                    min_gap_hours=2,
                    max_frequency=3,
                ),
                advance_config=StepAdvanceConfig(
                    trigger_type="conversion_signal",
                    trigger_threshold=1.0,
                    max_time_in_step_hours=24,
                ),
            ),
        ]
    
    @staticmethod
    def brand_building_sequence() -> List[SequenceStep]:
        """
        For brand awareness objectives (no direct conversion goal).
        
        Focus on reach, frequency, and brand recall.
        """
        return [
            # Step 1: AWARENESS
            SequenceStep(
                sequence_position=0,
                target_journey_state=JourneyState.DISCOVERY,
                creative_strategy=CreativeStrategy(
                    primary_mechanism="liking",
                    secondary_mechanisms=["authority"],
                    tone="inspirational",
                    content_focus="brand_story",
                    cta_style="soft",
                ),
                inventory_config=StepInventoryConfig(
                    preferred_types=["video_preroll", "ctv_streaming", "audio_streaming"],
                    preferred_contexts=["entertainment", "sports", "music"],
                    minimum_attention_score=0.6,
                ),
                timing_config=StepTimingConfig(
                    max_frequency=3,
                ),
                advance_config=StepAdvanceConfig(
                    trigger_type="time_elapsed",
                    trigger_threshold=72,  # 3 days
                ),
            ),
            
            # Step 2: REINFORCEMENT
            SequenceStep(
                sequence_position=1,
                target_journey_state=JourneyState.CONSIDERATION,
                creative_strategy=CreativeStrategy(
                    primary_mechanism="social_proof",
                    tone="informational",
                    content_focus="product_benefits",
                    cta_style="medium",
                ),
                inventory_config=StepInventoryConfig(
                    preferred_types=["video_midroll", "display_native", "audio_podcast"],
                    minimum_attention_score=0.5,
                ),
                timing_config=StepTimingConfig(
                    min_gap_hours=72,
                    max_frequency=4,
                ),
                advance_config=StepAdvanceConfig(
                    trigger_type="time_elapsed",
                    trigger_threshold=168,  # 7 days
                ),
            ),
        ]
```

---

## Sequential Persuasion Engine

```python
# =============================================================================
# ADAM Enhancement #28 v2.0: Sequential Persuasion Engine
# Location: adam/ad_desk/sequential_persuasion.py
# =============================================================================

"""
Sequential Persuasion Engine

Core engine for executing sequential persuasion campaigns.

Key responsibilities:
1. Track user journey positions in the graph
2. Select appropriate sequence step for each impression
3. Choose inventory based on journey state
4. Advance users through sequence based on triggers
5. Learn optimal sequences from outcomes
"""

from __future__ import annotations
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from uuid import uuid4
from neo4j import AsyncDriver

from adam.ad_desk.models.journey import (
    PersuasionSequence, SequenceStep, UserJourneyPosition, JourneyState
)
from adam.ad_desk.models.inventory import InventoryOpportunity

logger = logging.getLogger(__name__)


class SequentialPersuasionEngine:
    """
    Core engine for sequential persuasion execution.
    """
    
    def __init__(
        self,
        neo4j_driver: AsyncDriver,
        blackboard: Optional[Any] = None,
        gradient_bridge: Optional[Any] = None,
        journey_tracker: Optional[Any] = None,  # From Enhancement #10
        copy_generator: Optional[Any] = None,   # From Enhancement #15
        database: str = "neo4j"
    ):
        self.neo4j = neo4j_driver
        self.blackboard = blackboard
        self.gradient_bridge = gradient_bridge
        self.journey_tracker = journey_tracker
        self.copy_generator = copy_generator
        self.database = database
    
    async def get_impression_decision(
        self,
        user_id: str,
        sequence_id: str,
        available_inventory: List[InventoryOpportunity],
        timestamp: Optional[datetime] = None
    ) -> 'ImpressionDecision':
        """
        Decide what to show a user for their next impression.
        
        This is the real-time decision point called at bid time.
        """
        timestamp = timestamp or datetime.utcnow()
        
        # 1. Get user's current position
        position = await self._get_user_position(user_id, sequence_id)
        if not position:
            # New user - initialize at first step
            position = await self._initialize_user_position(
                user_id, sequence_id, timestamp
            )
        
        # 2. Get sequence
        sequence = await self._get_sequence(sequence_id)
        if not sequence:
            return ImpressionDecision(should_bid=False, reason="sequence_not_found")
        
        # 3. Evaluate if user should advance to next step
        current_step, should_advance = await self._evaluate_advancement(
            position, sequence, timestamp
        )
        
        if should_advance:
            current_step = await self._advance_user(position, sequence, timestamp)
        
        if current_step is None:
            return ImpressionDecision(should_bid=False, reason="sequence_complete")
        
        # 4. Filter inventory for current step
        valid_inventory = self._filter_inventory_for_step(
            available_inventory, current_step
        )
        
        if not valid_inventory:
            return ImpressionDecision(should_bid=False, reason="no_suitable_inventory")
        
        # 5. Select best inventory
        selected = await self._select_best_inventory(
            valid_inventory, current_step, position
        )
        
        # 6. Generate creative guidance
        creative_guidance = await self._generate_creative_guidance(
            current_step, position
        )
        
        # 7. Record decision
        await self._record_impression_decision(
            user_id, sequence_id, current_step.step_id, selected, timestamp
        )
        
        return ImpressionDecision(
            should_bid=True,
            selected_inventory=selected,
            bid_modifier=self._calculate_bid_modifier(current_step, position),
            creative_guidance=creative_guidance,
            current_step_position=current_step.sequence_position,
            journey_state=current_step.target_journey_state,
        )
    
    async def _evaluate_advancement(
        self,
        position: UserJourneyPosition,
        sequence: PersuasionSequence,
        timestamp: datetime
    ) -> Tuple[Optional[SequenceStep], bool]:
        """Evaluate if user should advance to next step."""
        
        current_step_idx = position.current_step_position
        if current_step_idx >= len(sequence.steps):
            return None, False
        
        current_step = sequence.steps[current_step_idx]
        advance_config = current_step.advance_config
        
        should_advance = False
        
        # Check trigger conditions
        if advance_config.trigger_type == "impression_count":
            if position.impressions_in_current_state >= advance_config.trigger_threshold:
                should_advance = True
        
        elif advance_config.trigger_type == "engagement":
            if position.engagement_depth >= advance_config.trigger_threshold:
                should_advance = True
        
        elif advance_config.trigger_type == "time_elapsed":
            hours_in_state = (timestamp - position.entered_state_at).total_seconds() / 3600
            if hours_in_state >= advance_config.trigger_threshold:
                should_advance = True
        
        # Check max time fallback
        hours_in_state = (timestamp - position.entered_state_at).total_seconds() / 3600
        if hours_in_state >= advance_config.max_time_in_step_hours:
            should_advance = True
        
        return current_step, should_advance
    
    def _filter_inventory_for_step(
        self,
        available: List[InventoryOpportunity],
        step: SequenceStep
    ) -> List[InventoryOpportunity]:
        """Filter inventory appropriate for this step."""
        
        config = step.inventory_config
        filtered = []
        
        for inv in available:
            # Check inventory type
            if config.preferred_types:
                if inv.inventory_type.value not in config.preferred_types:
                    continue
            
            # Check excluded contexts
            if config.excluded_contexts:
                if inv.content_context.value in config.excluded_contexts:
                    continue
            
            # Check attention score
            if inv.attention_score < config.minimum_attention_score:
                continue
            
            # Check viewability
            if inv.viewability_prediction < config.minimum_viewability:
                continue
            
            filtered.append(inv)
        
        return filtered
    
    async def _generate_creative_guidance(
        self,
        step: SequenceStep,
        position: UserJourneyPosition
    ) -> Dict[str, Any]:
        """Generate creative guidance for this impression."""
        
        strategy = step.creative_strategy
        
        guidance = {
            "primary_mechanism": strategy.primary_mechanism,
            "secondary_mechanisms": strategy.secondary_mechanisms,
            "tone": strategy.tone,
            "cta_style": strategy.cta_style,
            "headline_templates": strategy.headline_templates,
            "resonant_phrases": strategy.resonant_phrases,
            "avoid_phrases": strategy.avoid_phrases,
        }
        
        # Personalize based on user history
        if position.effective_mechanisms:
            # Boost mechanisms that worked for this user
            guidance["user_effective_mechanisms"] = position.effective_mechanisms
        
        # Use copy generator if available
        if self.copy_generator:
            guidance["generated_copy"] = await self.copy_generator.generate(
                mechanism=strategy.primary_mechanism,
                tone=strategy.tone,
                templates=strategy.headline_templates,
            )
        
        return guidance
    
    async def record_outcome(
        self,
        user_id: str,
        sequence_id: str,
        outcome_type: str,
        outcome_value: float,
        attributed_step: int,
        timestamp: Optional[datetime] = None
    ) -> None:
        """
        Record outcome and update sequence learnings.
        """
        timestamp = timestamp or datetime.utcnow()
        
        # Update sequence performance
        await self._update_sequence_metrics(
            sequence_id, attributed_step, outcome_type, outcome_value
        )
        
        # Update user position
        if outcome_type == "conversion":
            await self._mark_user_converted(user_id, sequence_id, timestamp)
        elif outcome_type == "engagement":
            await self._update_user_engagement(
                user_id, sequence_id, outcome_value, timestamp
            )
        
        # Emit learning signal
        if self.gradient_bridge:
            await self.gradient_bridge.emit({
                "source_component": "sequential_persuasion",
                "source_entity_type": "sequence_outcome",
                "signal_type": "sequence_performance",
                "signal_data": {
                    "sequence_id": sequence_id,
                    "user_id": user_id,
                    "outcome_type": outcome_type,
                    "outcome_value": str(outcome_value),
                    "attributed_step": str(attributed_step),
                },
                "target_components": ["meta_learner", "copy_generation"],
            })


class ImpressionDecision(BaseModel):
    """Decision output for an impression opportunity."""
    should_bid: bool
    reason: Optional[str] = None
    selected_inventory: Optional[InventoryOpportunity] = None
    bid_modifier: float = 1.0
    creative_guidance: Dict[str, Any] = Field(default_factory=dict)
    current_step_position: int = 0
    journey_state: Optional[JourneyState] = None
```

This continues with Supply-Path Optimization and Integration sections...

---

# SECTION D: PRODUCT 3 - SUPPLY-PATH OPTIMIZATION

## Product 3 Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                      SUPPLY-PATH OPTIMIZATION GRAPH                                 │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                     │
│   DSP                                                                               │
│    │                                                                                │
│    ├──► SSP-A ──► Publisher-1 ──► Placement-1 (Premium, 75% viewability, 20% take) │
│    │      └──► Exchange-X ──► Reseller ──► Publisher-1 (Same placement, 40% take)  │
│    │                                                                                │
│    ├──► SSP-B ──► Publisher-1 ──► Placement-1 (Different path, different quality)  │
│    │                                                                                │
│    └──► SSP-C ──► Publisher-2 ──► Placement-2 (Alternative, similar audience)      │
│                                                                                     │
│   KEY INSIGHT: Multiple paths to same placement have different quality/cost         │
│                                                                                     │
│   GRAPH REVEALS:                                                                    │
│   • Best path to each publisher (lowest take rate, highest quality)                │
│   • Reseller chains that add cost without value                                     │
│   • SSPs with better clearing prices                                                │
│   • Quality variance by path                                                        │
│   • Carbon footprint differences                                                    │
│                                                                                     │
│   OUTPUT: Curated supply paths that maximize Quality × Efficiency                   │
│                                                                                     │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

## Supply Path Graph Model

```python
# =============================================================================
# ADAM Enhancement #28 v2.0: Supply Path Models
# Location: adam/ad_desk/models/supply_path.py
# =============================================================================

"""
Supply Path Graph Models

Represents the complete supply chain from DSP to placement.

Key insight: Not all paths to the same placement are equal.
Graph structure reveals which SSPs and routes deliver best value.
"""

from __future__ import annotations
from datetime import datetime
from typing import Dict, List, Optional, Any
from uuid import uuid4
from pydantic import BaseModel, Field


class SupplyPathNode(BaseModel):
    """
    Complete supply path from DSP to placement.
    
    Graph representation:
    (DSP)-[:HAS_ACCESS]->(SSP)-[:ROUTES_THROUGH]->(Exchange)
         -[:ROUTES_THROUGH]->(Reseller)-[:REACHES]->(Publisher)
         -[:OFFERS]->(Placement)
    """
    path_id: str = Field(default_factory=lambda: str(uuid4()))
    
    # Chain Definition
    dsp_id: str
    ssp_id: str
    ssp_name: str
    exchange_id: Optional[str] = None
    exchange_name: Optional[str] = None
    reseller_chain: List[str] = Field(default_factory=list)
    publisher_id: str
    publisher_name: str
    placement_id: str
    placement_name: str
    
    # =========================================================================
    # QUALITY METRICS
    # =========================================================================
    quality_score: float = Field(default=0.5, ge=0.0, le=1.0)
    
    viewability_rate: float = Field(default=0.6, ge=0.0, le=1.0)
    # Measured viewability for this specific path
    
    fraud_risk: float = Field(default=0.1, ge=0.0, le=1.0)
    # Accumulated fraud risk across path
    
    brand_safety_score: float = Field(default=0.8, ge=0.0, le=1.0)
    # Publisher + context brand safety
    
    attention_score: float = Field(default=0.5, ge=0.0, le=1.0)
    # Expected attention quality
    
    # =========================================================================
    # EFFICIENCY METRICS
    # =========================================================================
    efficiency_score: float = Field(default=0.5, ge=0.0, le=1.0)
    
    total_take_rate: float = Field(default=0.3, ge=0.0, le=1.0)
    # Sum of all intermediary margins
    
    latency_ms: float = Field(default=100.0, ge=0.0)
    # End-to-end latency
    
    clearing_efficiency: float = Field(default=0.5, ge=0.0, le=1.0)
    # Win rate × value ratio
    
    bid_shading_risk: float = Field(default=0.2, ge=0.0, le=1.0)
    # Risk of aggressive bid shading
    
    auction_density: float = Field(default=0.5, ge=0.0, le=1.0)
    # Competition level in auctions
    
    # =========================================================================
    # PRICING
    # =========================================================================
    floor_cpm: float = Field(default=1.0, ge=0.0)
    avg_clearing_cpm: float = Field(default=2.0, ge=0.0)
    price_variance: float = Field(default=0.3, ge=0.0)
    # Price consistency (lower = more predictable)
    
    # =========================================================================
    # DEAL TYPES
    # =========================================================================
    deal_types_available: List[str] = Field(default_factory=list)
    # ["open_exchange", "pmp", "preferred_deal", "pg"]
    
    # =========================================================================
    # SUSTAINABILITY
    # =========================================================================
    carbon_score: Optional[float] = None
    # Lower = better (if available)
    
    # =========================================================================
    # PERFORMANCE HISTORY
    # =========================================================================
    historical_performance: Dict[str, float] = Field(default_factory=dict)
    # {"ctr": 0.01, "cvr": 0.02, "attention_time_seconds": 3.5}
    
    impression_count: int = 0
    outcome_count: int = 0
    confidence_score: float = Field(default=0.5, ge=0.0, le=1.0)
    
    # =========================================================================
    # METADATA
    # =========================================================================
    last_updated: datetime = Field(default_factory=datetime.utcnow)


class PathScore(BaseModel):
    """Detailed score breakdown for a supply path."""
    path_id: str
    
    # Quality breakdown
    quality_score: float = Field(ge=0.0, le=1.0)
    quality_components: Dict[str, float] = Field(default_factory=dict)
    # {"viewability": 0.8, "fraud_avoidance": 0.9, "brand_safety": 0.85, "attention": 0.7}
    
    # Efficiency breakdown
    efficiency_score: float = Field(ge=0.0, le=1.0)
    efficiency_components: Dict[str, float] = Field(default_factory=dict)
    # {"take_rate_savings": 0.7, "latency": 0.9, "clearing_value": 0.6, "directness": 0.8}
    
    # Combined
    total_score: float = Field(ge=0.0, le=1.0)
    
    # Confidence
    confidence: float = Field(ge=0.0, le=1.0)


class OptimizedPath(BaseModel):
    """A path in the optimized portfolio with budget allocation."""
    path: SupplyPathNode
    score: PathScore
    
    # Allocation
    allocated_budget: float = Field(ge=0.0)
    allocation_percentage: float = Field(ge=0.0, le=1.0)
    expected_impressions: int = Field(ge=0)
    
    # Expected outcomes
    expected_viewable_impressions: int = Field(ge=0)
    expected_ctr: float = Field(ge=0.0)
    expected_cvr: float = Field(ge=0.0)


class SupplyPathRecommendation(BaseModel):
    """Complete supply path optimization output."""
    product_id: str
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Recommended paths
    recommended_paths: List[OptimizedPath] = Field(default_factory=list)
    
    # Deal recommendations
    deal_recommendations: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Expected outcomes
    expected_savings_percentage: float = Field(ge=0.0)
    expected_quality_improvement_percentage: float = Field(ge=0.0)
    expected_effective_cpm: float = Field(ge=0.0)
    
    # Summary
    summary: str = ""
```

---

## Supply Path Optimization Engine

```python
# =============================================================================
# ADAM Enhancement #28 v2.0: Supply Path Optimizer
# Location: adam/ad_desk/supply_path_optimizer.py
# =============================================================================

"""
Supply Path Optimization Engine

Uses graph traversal to find optimal paths from DSP to inventory,
balancing quality, cost, and psychological fit.

Key insight: Multiple paths to same placement have different quality/cost.
Graph reveals which SSPs and routes deliver best Quality × Efficiency.
"""

from __future__ import annotations
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from uuid import uuid4
import numpy as np
from neo4j import AsyncDriver

from adam.ad_desk.models.supply_path import (
    SupplyPathNode, PathScore, OptimizedPath, SupplyPathRecommendation
)

logger = logging.getLogger(__name__)


class SupplyPathOptimizer:
    """
    Optimizes supply path selection using graph-based scoring.
    """
    
    def __init__(
        self,
        neo4j_driver: AsyncDriver,
        blackboard: Optional[Any] = None,
        gradient_bridge: Optional[Any] = None,
        database: str = "neo4j"
    ):
        self.neo4j = neo4j_driver
        self.blackboard = blackboard
        self.gradient_bridge = gradient_bridge
        self.database = database
    
    async def optimize_for_campaign(
        self,
        product_id: str,
        target_publishers: List[str],
        budget_usd: float,
        quality_threshold: float = 0.6,
        efficiency_threshold: float = 0.5
    ) -> SupplyPathRecommendation:
        """
        Find optimal supply paths for reaching target publishers.
        
        Returns curated paths that maximize Quality × Efficiency.
        """
        logger.info(f"Optimizing supply paths for {len(target_publishers)} publishers")
        
        # 1. Get all paths to target publishers
        all_paths = await self._get_all_paths(target_publishers)
        logger.info(f"Found {len(all_paths)} total paths")
        
        # 2. Score each path
        scored_paths = []
        for path in all_paths:
            score = self._score_path(path, quality_threshold, efficiency_threshold)
            if score.total_score > 0:
                scored_paths.append((path, score))
        
        logger.info(f"{len(scored_paths)} paths passed thresholds")
        
        # 3. Deduplicate (keep best path to each placement)
        deduplicated = self._deduplicate_by_placement(scored_paths)
        logger.info(f"{len(deduplicated)} unique placement paths")
        
        # 4. Optimize portfolio allocation
        portfolio = self._optimize_portfolio(deduplicated, budget_usd)
        
        # 5. Generate deal recommendations
        deal_recs = await self._generate_deal_recommendations(portfolio)
        
        # 6. Calculate expected outcomes
        savings = self._calculate_expected_savings(portfolio, budget_usd)
        quality_improvement = self._calculate_quality_improvement(portfolio)
        
        return SupplyPathRecommendation(
            product_id=product_id,
            recommended_paths=portfolio,
            deal_recommendations=deal_recs,
            expected_savings_percentage=savings,
            expected_quality_improvement_percentage=quality_improvement,
            expected_effective_cpm=self._calculate_effective_cpm(portfolio),
            summary=self._generate_summary(portfolio, savings, quality_improvement),
        )
    
    async def _get_all_paths(
        self,
        publisher_ids: List[str]
    ) -> List[SupplyPathNode]:
        """Query graph for all paths to target publishers."""
        
        query = """
        // Find all paths from DSP to target publishers
        MATCH path = (dsp:DSP)-[:HAS_ACCESS]->(ssp:SSP)
                     -[:ROUTES_THROUGH|REACHES*1..3]->(pub:Publisher)
                     -[:OFFERS]->(placement:Placement)
        WHERE pub.publisher_id IN $publisher_ids
        
        // Extract path components
        WITH path, dsp, ssp, pub, placement,
             [node IN nodes(path) WHERE node:Exchange] AS exchanges,
             [node IN nodes(path) WHERE node:Reseller] AS resellers,
             [rel IN relationships(path)] AS rels
        
        // Calculate accumulated metrics
        WITH dsp, ssp, pub, placement, exchanges, resellers,
             REDUCE(risk = 0.0, r IN rels | risk + COALESCE(r.fraud_risk, 0.0)) AS total_fraud,
             REDUCE(take = 0.0, r IN rels | take + COALESCE(r.take_rate, 0.0)) AS total_take,
             REDUCE(lat = 0.0, r IN rels | lat + COALESCE(r.latency_ms, 0.0)) AS total_latency
        
        RETURN {
            path_id: ssp.ssp_id + '-' + pub.publisher_id + '-' + placement.placement_id,
            dsp_id: dsp.dsp_id,
            ssp_id: ssp.ssp_id,
            ssp_name: ssp.name,
            exchange_id: CASE WHEN size(exchanges) > 0 THEN exchanges[0].exchange_id ELSE null END,
            exchange_name: CASE WHEN size(exchanges) > 0 THEN exchanges[0].name ELSE null END,
            reseller_chain: [r IN resellers | r.reseller_id],
            publisher_id: pub.publisher_id,
            publisher_name: pub.name,
            placement_id: placement.placement_id,
            placement_name: placement.name,
            
            // Quality
            viewability_rate: placement.viewability_rate,
            fraud_risk: total_fraud,
            brand_safety_score: pub.brand_safety_score,
            attention_score: placement.attention_score,
            
            // Efficiency
            total_take_rate: total_take,
            latency_ms: total_latency,
            auction_density: ssp.auction_density,
            bid_shading_risk: ssp.bid_shading_risk,
            
            // Pricing
            floor_cpm: placement.floor_cpm,
            avg_clearing_cpm: placement.avg_clearing_cpm,
            
            // Deals
            deal_types_available: placement.deal_types,
            
            // History
            impression_count: placement.impression_count,
            historical_ctr: placement.historical_ctr,
            historical_cvr: placement.historical_cvr
            
        } AS path_data
        """
        
        async with self.neo4j.session(database=self.database) as session:
            result = await session.run(query, publisher_ids=publisher_ids)
            records = await result.data()
            
            paths = []
            for record in records:
                data = record["path_data"]
                path = SupplyPathNode(
                    path_id=data["path_id"],
                    dsp_id=data["dsp_id"],
                    ssp_id=data["ssp_id"],
                    ssp_name=data.get("ssp_name", ""),
                    exchange_id=data.get("exchange_id"),
                    exchange_name=data.get("exchange_name"),
                    reseller_chain=data.get("reseller_chain", []),
                    publisher_id=data["publisher_id"],
                    publisher_name=data.get("publisher_name", ""),
                    placement_id=data["placement_id"],
                    placement_name=data.get("placement_name", ""),
                    viewability_rate=data.get("viewability_rate", 0.6),
                    fraud_risk=min(1.0, data.get("fraud_risk", 0.1)),
                    brand_safety_score=data.get("brand_safety_score", 0.8),
                    attention_score=data.get("attention_score", 0.5),
                    total_take_rate=min(1.0, data.get("total_take_rate", 0.3)),
                    latency_ms=data.get("latency_ms", 100),
                    auction_density=data.get("auction_density", 0.5),
                    bid_shading_risk=data.get("bid_shading_risk", 0.2),
                    floor_cpm=data.get("floor_cpm", 1.0),
                    avg_clearing_cpm=data.get("avg_clearing_cpm", 2.0),
                    deal_types_available=data.get("deal_types_available", []),
                    impression_count=data.get("impression_count", 0),
                    historical_performance={
                        "ctr": data.get("historical_ctr", 0.005),
                        "cvr": data.get("historical_cvr", 0.01),
                    },
                )
                paths.append(path)
            
            return paths
    
    def _score_path(
        self,
        path: SupplyPathNode,
        quality_threshold: float,
        efficiency_threshold: float
    ) -> PathScore:
        """Score a supply path on quality and efficiency."""
        
        # Quality components (weighted)
        quality_components = {
            "viewability": path.viewability_rate * 0.30,
            "fraud_avoidance": (1 - path.fraud_risk) * 0.25,
            "brand_safety": path.brand_safety_score * 0.25,
            "attention": path.attention_score * 0.20,
        }
        quality_score = sum(quality_components.values())
        
        # Efficiency components (weighted)
        efficiency_components = {
            "take_rate_savings": (1 - path.total_take_rate) * 0.35,
            "latency": max(0, 1 - (path.latency_ms / 500)) * 0.15,
            "clearing_value": min(1.0, path.floor_cpm / max(0.01, path.avg_clearing_cpm)) * 0.25,
            "directness": (1 - len(path.reseller_chain) * 0.15) * 0.25,
        }
        efficiency_score = sum(efficiency_components.values())
        
        # Combined score (only if both pass thresholds)
        if quality_score < quality_threshold or efficiency_score < efficiency_threshold:
            total_score = 0.0
        else:
            total_score = quality_score * 0.6 + efficiency_score * 0.4
        
        # Confidence based on data volume
        confidence = min(0.95, 0.3 + (path.impression_count / 10000))
        
        return PathScore(
            path_id=path.path_id,
            quality_score=round(quality_score, 3),
            quality_components=quality_components,
            efficiency_score=round(efficiency_score, 3),
            efficiency_components=efficiency_components,
            total_score=round(total_score, 3),
            confidence=round(confidence, 3),
        )
    
    def _deduplicate_by_placement(
        self,
        scored_paths: List[Tuple[SupplyPathNode, PathScore]]
    ) -> List[Tuple[SupplyPathNode, PathScore]]:
        """Keep only best path to each placement."""
        
        best_by_placement = {}
        
        for path, score in scored_paths:
            key = f"{path.publisher_id}:{path.placement_id}"
            
            if key not in best_by_placement:
                best_by_placement[key] = (path, score)
            elif score.total_score > best_by_placement[key][1].total_score:
                best_by_placement[key] = (path, score)
        
        return list(best_by_placement.values())
    
    def _optimize_portfolio(
        self,
        paths: List[Tuple[SupplyPathNode, PathScore]],
        budget_usd: float
    ) -> List[OptimizedPath]:
        """Optimize budget allocation across paths."""
        
        # Sort by score
        sorted_paths = sorted(paths, key=lambda x: x[1].total_score, reverse=True)
        
        if not sorted_paths:
            return []
        
        # Calculate score-weighted allocation
        total_score = sum(p[1].total_score for p in sorted_paths)
        
        portfolio = []
        remaining_budget = budget_usd
        
        for path, score in sorted_paths:
            if remaining_budget <= 0:
                break
            
            # Score-weighted allocation with cap
            fair_share = (score.total_score / total_score) * budget_usd
            # Cap at 1.5x fair share for diversification
            allocation = min(fair_share * 1.5, remaining_budget)
            
            if allocation > 0:
                expected_impressions = int(allocation / path.avg_clearing_cpm * 1000)
                
                portfolio.append(OptimizedPath(
                    path=path,
                    score=score,
                    allocated_budget=round(allocation, 2),
                    allocation_percentage=round(allocation / budget_usd, 3),
                    expected_impressions=expected_impressions,
                    expected_viewable_impressions=int(expected_impressions * path.viewability_rate),
                    expected_ctr=path.historical_performance.get("ctr", 0.005),
                    expected_cvr=path.historical_performance.get("cvr", 0.01),
                ))
                
                remaining_budget -= allocation
        
        return portfolio
    
    def _calculate_expected_savings(
        self,
        portfolio: List[OptimizedPath],
        budget_usd: float
    ) -> float:
        """
        Calculate expected savings vs unoptimized buying.
        
        Baseline assumptions:
        - 30% average take rate
        - 10% fraud
        - 60% viewability
        """
        # Baseline effective spend
        baseline_effective = budget_usd * 0.70 * 0.90 * 0.60  # ~37.8% effective
        
        # Optimized effective spend
        optimized_effective = sum(
            op.allocated_budget *
            (1 - op.path.total_take_rate) *
            (1 - op.path.fraud_risk) *
            op.path.viewability_rate
            for op in portfolio
        )
        
        if baseline_effective <= 0:
            return 0.0
        
        improvement = (optimized_effective - baseline_effective) / baseline_effective
        return round(max(0, improvement) * 100, 1)
    
    def _calculate_quality_improvement(
        self,
        portfolio: List[OptimizedPath]
    ) -> float:
        """Calculate quality improvement vs baseline."""
        
        if not portfolio:
            return 0.0
        
        # Baseline quality assumptions
        baseline_viewability = 0.60
        baseline_attention = 0.50
        
        # Portfolio weighted averages
        total_budget = sum(op.allocated_budget for op in portfolio)
        if total_budget <= 0:
            return 0.0
        
        weighted_viewability = sum(
            op.path.viewability_rate * op.allocated_budget
            for op in portfolio
        ) / total_budget
        
        weighted_attention = sum(
            op.path.attention_score * op.allocated_budget
            for op in portfolio
        ) / total_budget
        
        viewability_improvement = (weighted_viewability - baseline_viewability) / baseline_viewability
        attention_improvement = (weighted_attention - baseline_attention) / baseline_attention
        
        combined_improvement = (viewability_improvement + attention_improvement) / 2
        return round(max(0, combined_improvement) * 100, 1)
    
    def _calculate_effective_cpm(self, portfolio: List[OptimizedPath]) -> float:
        """Calculate effective CPM for portfolio."""
        
        total_impressions = sum(op.expected_impressions for op in portfolio)
        total_budget = sum(op.allocated_budget for op in portfolio)
        
        if total_impressions <= 0:
            return 0.0
        
        return round((total_budget / total_impressions) * 1000, 2)
    
    def _generate_summary(
        self,
        portfolio: List[OptimizedPath],
        savings: float,
        quality_improvement: float
    ) -> str:
        """Generate human-readable summary."""
        
        if not portfolio:
            return "No paths met quality and efficiency thresholds."
        
        return (
            f"Optimized {len(portfolio)} supply paths. "
            f"Expected savings: {savings}%. "
            f"Quality improvement: {quality_improvement}%. "
            f"Top path: {portfolio[0].path.publisher_name} via {portfolio[0].path.ssp_name} "
            f"(score: {portfolio[0].score.total_score:.2f})."
        )
```

---

# SECTION E: INTEGRATION & INFRASTRUCTURE

## Three-Product Integration Flow

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                    THREE-PRODUCT INTEGRATION FLOW                                   │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                     │
│   ADVERTISER INPUT                                                                  │
│   ────────────────                                                                  │
│   Product Feed / Brief                                                              │
│       │                                                                             │
│       ▼                                                                             │
│   ┌─────────────────────────────────────────────────────────────────────┐          │
│   │           PRODUCT 1: PRODUCT-TO-INVENTORY MATCH                     │          │
│   │                                                                      │          │
│   │  Product Graph ──► Customer Segments ──► Inventory Match            │          │
│   │                                                                      │          │
│   │  OUTPUTS:                                                            │          │
│   │  • Psychological Segments (who buys, why)                           │          │
│   │  • Matched Publishers/Placements                                     │          │
│   │  • Deployment Plan (timing, messaging, allocation)                   │          │
│   └─────────────────────────────┬───────────────────────────────────────┘          │
│                                 │                                                   │
│                 ┌───────────────┼───────────────┐                                   │
│                 │               │               │                                   │
│                 ▼               ▼               ▼                                   │
│   ┌─────────────────────────────────────────────────────────────────────┐          │
│   │           PRODUCT 2: SEQUENTIAL PERSUASION                          │          │
│   │                                                                      │          │
│   │  Takes: Segments + Matched Inventory                                │          │
│   │                                                                      │          │
│   │  BUILDS:                                                             │          │
│   │  • Sequence per Segment (discovery → consideration → conversion)    │          │
│   │  • Step-specific inventory selection                                │          │
│   │  • Step-specific creative guidance                                  │          │
│   │                                                                      │          │
│   │  OUTPUTS:                                                            │          │
│   │  • Persuasion Sequences                                             │          │
│   │  • Real-time orchestration rules                                    │          │
│   └─────────────────────────────┬───────────────────────────────────────┘          │
│                                 │                                                   │
│                                 ▼                                                   │
│   ┌─────────────────────────────────────────────────────────────────────┐          │
│   │           PRODUCT 3: SUPPLY-PATH OPTIMIZATION                       │          │
│   │                                                                      │          │
│   │  Takes: Matched Publishers + Sequence Inventory Needs               │          │
│   │                                                                      │          │
│   │  OPTIMIZES:                                                          │          │
│   │  • Best path to each publisher/placement                            │          │
│   │  • Deal selection (PMP vs open vs PG)                               │          │
│   │  • Budget allocation across paths                                    │          │
│   │                                                                      │          │
│   │  OUTPUTS:                                                            │          │
│   │  • Curated supply paths                                             │          │
│   │  • Expected savings                                                 │          │
│   └─────────────────────────────────────────────────────────────────────┘          │
│                                                                                     │
│   FINAL OUTPUT TO BUYER                                                            │
│   ─────────────────────                                                             │
│   ┌───────────────────────────────────────────────────────────────────────────────┐│
│   │ • Complete buying plan with psychological targeting                           ││
│   │ • Sequence orchestration rules for DSP integration                           ││
│   │ • Curated supply paths with expected savings                                  ││
│   │ • Measurement design for proving ROI                                          ││
│   └───────────────────────────────────────────────────────────────────────────────┘│
│                                                                                     │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Unified Learning Loop

```python
# =============================================================================
# ADAM Enhancement #28 v2.0: Unified Learning Loop
# Location: adam/ad_desk/learning_loop.py
# =============================================================================

"""
Unified Learning Loop

Every outcome improves all three products:
- Product Match learns which segments convert
- Sequential Persuasion learns optimal sequences
- Supply Path learns which paths deliver

The Gradient Bridge propagates signals across components.
"""

from __future__ import annotations
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from neo4j import AsyncDriver

logger = logging.getLogger(__name__)


class UnifiedLearningLoop:
    """
    Unified learning loop across all three Ad Desk products.
    """
    
    def __init__(
        self,
        neo4j_driver: AsyncDriver,
        gradient_bridge: 'GradientBridge',
        database: str = "neo4j"
    ):
        self.neo4j = neo4j_driver
        self.gradient_bridge = gradient_bridge
        self.database = database
    
    async def process_campaign_outcome(
        self,
        outcome: 'CampaignOutcome'
    ) -> None:
        """
        Process a campaign outcome and update all systems.
        """
        logger.info(f"Processing outcome for campaign: {outcome.campaign_id}")
        
        # 1. Update Product Match learnings
        await self._update_segment_effectiveness(outcome)
        
        # 2. Update Sequential Persuasion learnings
        await self._update_sequence_effectiveness(outcome)
        
        # 3. Update Supply Path learnings
        await self._update_path_effectiveness(outcome)
        
        # 4. Emit cross-component learning signals
        await self._emit_learning_signals(outcome)
    
    async def _update_segment_effectiveness(
        self,
        outcome: 'CampaignOutcome'
    ) -> None:
        """Update psychological segment effectiveness priors."""
        
        query = """
        MATCH (seg:CustomerSegment {segment_id: $segment_id})
        
        // Update performance metrics
        SET seg.total_impressions = COALESCE(seg.total_impressions, 0) + $impressions,
            seg.total_conversions = COALESCE(seg.total_conversions, 0) + $conversions,
            seg.conversion_rate = (COALESCE(seg.total_conversions, 0) + $conversions) / 
                                  (COALESCE(seg.total_impressions, 0) + $impressions),
            seg.confidence_score = CASE 
                WHEN COALESCE(seg.total_impressions, 0) + $impressions > 1000 THEN 0.9
                WHEN COALESCE(seg.total_impressions, 0) + $impressions > 100 THEN 0.7
                ELSE 0.5 END,
            seg.last_updated = datetime()
        
        // Update mechanism effectiveness if attribution available
        WITH seg
        UNWIND $mechanism_attribution AS mech
        SET seg.mechanism_effectiveness = apoc.map.setKey(
            COALESCE(seg.mechanism_effectiveness, {}),
            mech.mechanism,
            (COALESCE(seg.mechanism_effectiveness[mech.mechanism], 0.5) * 0.9 + 
             mech.effectiveness * 0.1)
        )
        
        RETURN seg
        """
        
        async with self.neo4j.session(database=self.database) as session:
            await session.run(
                query,
                segment_id=outcome.segment_id,
                impressions=outcome.impressions,
                conversions=outcome.conversions,
                mechanism_attribution=outcome.mechanism_attribution or []
            )
    
    async def _update_sequence_effectiveness(
        self,
        outcome: 'CampaignOutcome'
    ) -> None:
        """Update sequence and step effectiveness."""
        
        if not outcome.sequence_id:
            return
        
        query = """
        MATCH (seq:PersuasionSequence {sequence_id: $sequence_id})
        
        SET seq.users_in_sequence = COALESCE(seq.users_in_sequence, 0) + $user_count,
            seq.completion_rate = ($completions / ($user_count + 0.001)),
            seq.conversion_rate = ($conversions / ($user_count + 0.001)),
            seq.updated_at = datetime()
        
        // Update step-level metrics
        WITH seq
        UNWIND $step_outcomes AS step_data
        MATCH (seq)-[:HAS_STEP]->(step:SequenceStep {sequence_position: step_data.position})
        SET step.impressions = COALESCE(step.impressions, 0) + step_data.impressions,
            step.engagements = COALESCE(step.engagements, 0) + step_data.engagements,
            step.advancements = COALESCE(step.advancements, 0) + step_data.advancements
        
        RETURN seq
        """
        
        async with self.neo4j.session(database=self.database) as session:
            await session.run(
                query,
                sequence_id=outcome.sequence_id,
                user_count=outcome.unique_users,
                completions=outcome.sequence_completions,
                conversions=outcome.conversions,
                step_outcomes=outcome.step_outcomes or []
            )
    
    async def _update_path_effectiveness(
        self,
        outcome: 'CampaignOutcome'
    ) -> None:
        """Update supply path quality and efficiency scores."""
        
        if not outcome.path_performance:
            return
        
        query = """
        UNWIND $path_data AS pd
        MATCH (sp:SupplyPath {path_id: pd.path_id})
        
        SET sp.impression_count = COALESCE(sp.impression_count, 0) + pd.impressions,
            sp.outcome_count = COALESCE(sp.outcome_count, 0) + pd.conversions,
            sp.historical_ctr = (COALESCE(sp.historical_ctr, 0.005) * 0.9 + 
                                pd.ctr * 0.1),
            sp.historical_cvr = (COALESCE(sp.historical_cvr, 0.01) * 0.9 + 
                                pd.cvr * 0.1),
            sp.viewability_rate = (COALESCE(sp.viewability_rate, 0.6) * 0.9 + 
                                  pd.viewability * 0.1),
            sp.confidence_score = CASE 
                WHEN COALESCE(sp.impression_count, 0) + pd.impressions > 10000 THEN 0.95
                WHEN COALESCE(sp.impression_count, 0) + pd.impressions > 1000 THEN 0.8
                ELSE 0.6 END,
            sp.last_updated = datetime()
        
        RETURN sp
        """
        
        async with self.neo4j.session(database=self.database) as session:
            await session.run(query, path_data=outcome.path_performance)
    
    async def _emit_learning_signals(
        self,
        outcome: 'CampaignOutcome'
    ) -> None:
        """Emit learning signals via Gradient Bridge."""
        
        signals = [
            # Signal for psychological segment refinement
            {
                "source_component": "ad_desk",
                "source_entity_type": "segment_outcome",
                "signal_type": "segment_performance",
                "signal_data": {
                    "segment_id": outcome.segment_id,
                    "conversion_rate": str(outcome.conversions / max(1, outcome.impressions)),
                    "mechanism_attribution": outcome.mechanism_attribution,
                },
                "target_components": ["product_graph", "meta_learner"],
                "confidence": 0.8,
            },
            
            # Signal for sequence optimization
            {
                "source_component": "ad_desk",
                "source_entity_type": "sequence_outcome",
                "signal_type": "sequence_performance",
                "signal_data": {
                    "sequence_id": outcome.sequence_id,
                    "completion_rate": str(outcome.sequence_completions / max(1, outcome.unique_users)),
                    "step_outcomes": outcome.step_outcomes,
                },
                "target_components": ["sequential_persuasion", "copy_generation"],
                "confidence": 0.7,
            },
            
            # Signal for supply path learning
            {
                "source_component": "ad_desk",
                "source_entity_type": "path_outcome",
                "signal_type": "path_performance",
                "signal_data": {
                    "path_ids": [p["path_id"] for p in outcome.path_performance or []],
                    "path_metrics": outcome.path_performance,
                },
                "target_components": ["supply_path_optimizer", "inventory_graph"],
                "confidence": 0.75,
            },
        ]
        
        for signal in signals:
            if signal["signal_data"].get("segment_id") or signal["signal_data"].get("sequence_id"):
                await self.gradient_bridge.emit(signal)


class CampaignOutcome(BaseModel):
    """Campaign outcome for learning."""
    campaign_id: str
    product_id: str
    
    # Segment data
    segment_id: str
    
    # Volume
    impressions: int
    unique_users: int
    conversions: int
    
    # Sequence data
    sequence_id: Optional[str] = None
    sequence_completions: int = 0
    step_outcomes: Optional[List[Dict[str, Any]]] = None
    
    # Path data
    path_performance: Optional[List[Dict[str, Any]]] = None
    
    # Attribution
    mechanism_attribution: Optional[List[Dict[str, Any]]] = None
    
    # Timing
    timestamp: datetime = Field(default_factory=datetime.utcnow)
```

---

## Neo4j Schema - Complete Graph Model

```python
# =============================================================================
# ADAM Enhancement #28 v2.0: Neo4j Schema
# Location: adam/ad_desk/schema.py
# =============================================================================

"""
Complete Neo4j Schema for Ad Desk Intelligence Layer

This schema supports all three core products:
1. Product-to-Inventory Match (Product, Segment, Publisher, Placement)
2. Sequential Persuasion (Sequence, Step, UserPosition, Journey)
3. Supply-Path Optimization (SupplyPath, SSP, Exchange, Reseller)
"""

NEO4J_SCHEMA = """
// =============================================================================
// CONSTRAINTS
// =============================================================================

// Products
CREATE CONSTRAINT product_id IF NOT EXISTS FOR (p:Product) REQUIRE p.product_id IS UNIQUE;
CREATE CONSTRAINT advertiser_id IF NOT EXISTS FOR (a:Advertiser) REQUIRE a.advertiser_id IS UNIQUE;

// Segments
CREATE CONSTRAINT segment_id IF NOT EXISTS FOR (s:CustomerSegment) REQUIRE s.segment_id IS UNIQUE;

// Inventory
CREATE CONSTRAINT publisher_id IF NOT EXISTS FOR (p:Publisher) REQUIRE p.publisher_id IS UNIQUE;
CREATE CONSTRAINT placement_id IF NOT EXISTS FOR (p:Placement) REQUIRE p.placement_id IS UNIQUE;

// Sequences
CREATE CONSTRAINT sequence_id IF NOT EXISTS FOR (s:PersuasionSequence) REQUIRE s.sequence_id IS UNIQUE;
CREATE CONSTRAINT step_id IF NOT EXISTS FOR (s:SequenceStep) REQUIRE s.step_id IS UNIQUE;
CREATE CONSTRAINT user_position_id IF NOT EXISTS FOR (u:UserJourneyPosition) REQUIRE u.user_id IS UNIQUE;

// Supply Paths
CREATE CONSTRAINT path_id IF NOT EXISTS FOR (sp:SupplyPath) REQUIRE sp.path_id IS UNIQUE;
CREATE CONSTRAINT ssp_id IF NOT EXISTS FOR (s:SSP) REQUIRE s.ssp_id IS UNIQUE;
CREATE CONSTRAINT exchange_id IF NOT EXISTS FOR (e:Exchange) REQUIRE e.exchange_id IS UNIQUE;
CREATE CONSTRAINT reseller_id IF NOT EXISTS FOR (r:Reseller) REQUIRE r.reseller_id IS UNIQUE;
CREATE CONSTRAINT dsp_id IF NOT EXISTS FOR (d:DSP) REQUIRE d.dsp_id IS UNIQUE;

// =============================================================================
// INDEXES
// =============================================================================

// Product indexes
CREATE INDEX product_category IF NOT EXISTS FOR (p:Product) ON (p.category);
CREATE INDEX product_price_tier IF NOT EXISTS FOR (p:Product) ON (p.price_tier);
CREATE INDEX product_advertiser IF NOT EXISTS FOR (p:Product) ON (p.advertiser_id);

// Segment indexes
CREATE INDEX segment_confidence IF NOT EXISTS FOR (s:CustomerSegment) ON (s.confidence_score);
CREATE INDEX segment_product IF NOT EXISTS FOR (s:CustomerSegment) ON (s.product_id);

// Publisher indexes
CREATE INDEX publisher_brand_safety IF NOT EXISTS FOR (p:Publisher) ON (p.brand_safety_score);
CREATE INDEX publisher_viewability IF NOT EXISTS FOR (p:Publisher) ON (p.viewability_average);

// Sequence indexes
CREATE INDEX sequence_product IF NOT EXISTS FOR (s:PersuasionSequence) ON (s.product_id);
CREATE INDEX sequence_learning IF NOT EXISTS FOR (s:PersuasionSequence) ON (s.is_learning);

// User position indexes
CREATE INDEX user_sequence IF NOT EXISTS FOR (u:UserJourneyPosition) ON (u.sequence_id);
CREATE INDEX user_state IF NOT EXISTS FOR (u:UserJourneyPosition) ON (u.current_state);

// Supply path indexes
CREATE INDEX path_quality IF NOT EXISTS FOR (sp:SupplyPath) ON (sp.quality_score);
CREATE INDEX path_efficiency IF NOT EXISTS FOR (sp:SupplyPath) ON (sp.efficiency_score);
CREATE INDEX path_publisher IF NOT EXISTS FOR (sp:SupplyPath) ON (sp.publisher_id);

// =============================================================================
// VECTOR INDEXES (for similarity search)
// =============================================================================

// Product psychological embeddings
CREATE VECTOR INDEX product_psych_embedding IF NOT EXISTS
FOR (p:Product)
ON p.psychological_embedding
OPTIONS {indexConfig: {
    `vector.dimensions`: 64,
    `vector.similarity_function`: 'cosine'
}};

// Publisher audience embeddings
CREATE VECTOR INDEX publisher_audience_embedding IF NOT EXISTS
FOR (p:Publisher)
ON p.audience_embedding
OPTIONS {indexConfig: {
    `vector.dimensions`: 64,
    `vector.similarity_function`: 'cosine'
}};

// =============================================================================
// FULL-TEXT INDEXES
// =============================================================================

// Product search
CREATE FULLTEXT INDEX product_search IF NOT EXISTS
FOR (p:Product)
ON EACH [p.product_name, p.product_description];

// Publisher search
CREATE FULLTEXT INDEX publisher_search IF NOT EXISTS
FOR (p:Publisher)
ON EACH [p.publisher_name, p.domain];
"""

# Relationship patterns
GRAPH_RELATIONSHIPS = """
// Product Domain
(:Advertiser)-[:OWNS]->(:Product)
(:Product)-[:HAS_SEGMENT]->(:CustomerSegment)
(:Product)-[:IN_CATEGORY]->(:ProductCategory)
(:Product)-[:COMPETES_WITH]->(:Product)
(:Product)-[:HAS_CONSTRAINT]->(:ComplianceConstraint)

// Inventory Domain
(:Publisher)-[:OFFERS]->(:Placement)
(:Publisher)-[:HAS_AUDIENCE_PROFILE]->(:PsychologicalProfile)
(:Placement)-[:HAS_CONTEXT]->(:ContentContext)

// Matching Domain
(:CustomerSegment)-[:ALIGNS_WITH {score: float}]->(:Publisher)
(:Product)-[:RECOMMENDED_FOR]->(:Placement)

// Sequence Domain
(:Product)-[:HAS_SEQUENCE]->(:PersuasionSequence)
(:PersuasionSequence)-[:HAS_STEP {position: int}]->(:SequenceStep)
(:SequenceStep)-[:TARGETS_STATE]->(:JourneyState)
(:SequenceStep)-[:PREFERS_INVENTORY]->(:InventoryType)
(:User)-[:IN_SEQUENCE]->(:UserJourneyPosition)
(:UserJourneyPosition)-[:AT_STEP]->(:SequenceStep)

// Supply Path Domain
(:DSP)-[:HAS_ACCESS]->(:SSP)
(:SSP)-[:ROUTES_THROUGH]->(:Exchange)
(:Exchange)-[:ROUTES_THROUGH]->(:Reseller)
(:SSP)-[:REACHES]->(:Publisher)
(:Exchange)-[:REACHES]->(:Publisher)
(:Reseller)-[:REACHES]->(:Publisher)
(:Publisher)-[:OFFERS]->(:Placement)

// Learning Domain
(:SupplyPath)-[:DELIVERS {quality: float, efficiency: float}]->(:Placement)
(:CustomerSegment)-[:CONVERTS_VIA {rate: float}]->(:SequenceStep)
(:SequenceStep)-[:TRANSITIONS_TO {probability: float}]->(:SequenceStep)
"""
```

---

## FastAPI Endpoints

```python
# =============================================================================
# ADAM Enhancement #28 v2.0: FastAPI Endpoints
# Location: adam/ad_desk/api.py
# =============================================================================

"""
FastAPI REST API for Ad Desk Intelligence Layer.

Endpoints organized by product:
- /products/* - Product Knowledge Graph
- /segments/* - Customer Psychological Segments
- /inventory/* - Inventory Knowledge Graph
- /match/* - Product-to-Inventory Matching
- /sequences/* - Sequential Persuasion
- /supply-paths/* - Supply Path Optimization
- /campaigns/* - Campaign Management & Learning
"""

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
from datetime import datetime

app = FastAPI(
    title="ADAM Ad Desk Intelligence API",
    description="Psychological intelligence for programmatic advertising",
    version="2.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# PRODUCT ENDPOINTS
# =============================================================================

@app.post("/api/v2/products/ingest", tags=["Products"])
async def ingest_product_feed(
    feed: ProductFeed,
    background_tasks: BackgroundTasks,
    service: ProductKnowledgeGraphService = Depends(get_product_service)
):
    """
    Ingest a product feed and build psychological profiles.
    
    Triggers async segment generation for each product.
    """
    result = await service.ingest_product_feed(feed)
    
    # Trigger async segment building
    for product in feed.products:
        background_tasks.add_task(
            service.build_segments_for_product,
            product.product_id
        )
    
    return {
        "status": "success",
        "products_created": result["created"],
        "products_updated": result["updated"],
        "segment_building": "triggered",
    }


@app.get("/api/v2/products/{product_id}", tags=["Products"])
async def get_product(
    product_id: str,
    include_segments: bool = True,
    service: ProductKnowledgeGraphService = Depends(get_product_service)
):
    """Get product with optional psychological segments."""
    product = await service.get_product_full_context(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    if not include_segments:
        product.customer_segments = []
    
    return product


@app.get("/api/v2/products/{product_id}/segments", tags=["Products"])
async def get_product_segments(
    product_id: str,
    service: ProductKnowledgeGraphService = Depends(get_product_service)
):
    """Get psychological segments for a product."""
    segments = await service.get_product_segments(product_id)
    return {"product_id": product_id, "segments": segments}


# =============================================================================
# MATCHING ENDPOINTS
# =============================================================================

@app.post("/api/v2/match/recommendations", tags=["Matching"])
async def generate_inventory_recommendations(
    request: MatchRequest,
    service: ProductToInventoryMatcher = Depends(get_matcher_service)
):
    """
    Generate complete inventory recommendations for a product.
    
    Returns:
    - Recommended PMPs/Deals
    - Contextual Segments
    - Audiences
    - Exclusions
    - Deployment Plan
    """
    recommendation = await service.generate_recommendations(
        product_id=request.product_id,
        budget_usd=request.budget_usd,
        campaign_duration_days=request.campaign_duration_days,
        campaign_objectives=request.campaign_objectives
    )
    
    return recommendation


# =============================================================================
# SEQUENCE ENDPOINTS
# =============================================================================

@app.post("/api/v2/sequences/create", tags=["Sequences"])
async def create_persuasion_sequence(
    request: SequenceCreateRequest,
    service: SequentialPersuasionEngine = Depends(get_sequence_service)
):
    """Create a new persuasion sequence for a product."""
    sequence = await service.create_sequence(
        product_id=request.product_id,
        template_type=request.template_type,
        custom_steps=request.custom_steps
    )
    return sequence


@app.post("/api/v2/sequences/impression-decision", tags=["Sequences"])
async def get_impression_decision(
    request: ImpressionDecisionRequest,
    service: SequentialPersuasionEngine = Depends(get_sequence_service)
):
    """
    Real-time decision endpoint for impression opportunities.
    
    Called at bid time to determine:
    - Should we bid?
    - What inventory to select?
    - What creative guidance to provide?
    """
    decision = await service.get_impression_decision(
        user_id=request.user_id,
        sequence_id=request.sequence_id,
        available_inventory=request.available_inventory,
        timestamp=request.timestamp or datetime.utcnow()
    )
    return decision


# =============================================================================
# SUPPLY PATH ENDPOINTS
# =============================================================================

@app.post("/api/v2/supply-paths/optimize", tags=["Supply Paths"])
async def optimize_supply_paths(
    request: SupplyPathOptimizeRequest,
    service: SupplyPathOptimizer = Depends(get_supply_path_service)
):
    """
    Optimize supply paths for a campaign.
    
    Returns curated paths that maximize Quality × Efficiency.
    """
    recommendation = await service.optimize_for_campaign(
        product_id=request.product_id,
        target_publishers=request.target_publishers,
        budget_usd=request.budget_usd,
        quality_threshold=request.quality_threshold,
        efficiency_threshold=request.efficiency_threshold
    )
    return recommendation


# =============================================================================
# LEARNING ENDPOINTS
# =============================================================================

@app.post("/api/v2/campaigns/outcome", tags=["Learning"])
async def record_campaign_outcome(
    outcome: CampaignOutcome,
    service: UnifiedLearningLoop = Depends(get_learning_service)
):
    """
    Record campaign outcome for system learning.
    
    Updates:
    - Segment effectiveness priors
    - Sequence performance metrics
    - Supply path quality scores
    """
    await service.process_campaign_outcome(outcome)
    return {"status": "success", "message": "Outcome recorded and learning triggered"}


# =============================================================================
# HEALTH & METADATA
# =============================================================================

@app.get("/api/v2/health", tags=["System"])
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": "2.0.0",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/api/v2/metadata/categories", tags=["System"])
async def get_supported_categories():
    """Get supported product categories."""
    return {"categories": [c.value for c in ProductCategory]}


@app.get("/api/v2/metadata/mechanisms", tags=["System"])
async def get_supported_mechanisms():
    """Get supported persuasion mechanisms."""
    return {
        "mechanisms": [
            "social_proof", "scarcity", "authority",
            "reciprocity", "commitment", "liking"
        ]
    }
```

---

# SECTION F: DEPLOYMENT & OPERATIONS

## Implementation Timeline

### Phase 1: Foundation (Weeks 1-4)

| Week | Focus | Deliverables |
|------|-------|--------------|
| 1 | Core Models | All Pydantic models, enums, type definitions |
| 1 | Neo4j Schema | Constraints, indexes, vector indexes |
| 2 | Product Graph | ProductKnowledgeGraphService |
| 2 | Segment Engine | CustomerSegmentEngine with Claude integration |
| 3 | Amazon Pipeline | AmazonCorpusClient, review extraction |
| 3 | Web Intelligence | WebIntelligenceAugmenter |
| 4 | Inventory Graph | InventoryKnowledgeGraphService |
| 4 | Integration Tests | Full Product Graph tests |

### Phase 2: Core Products (Weeks 5-10)

| Week | Focus | Deliverables |
|------|-------|--------------|
| 5 | Product-Inventory Matcher | Matching algorithms, scoring |
| 5 | Psychological Alignment | Trait/mechanism alignment |
| 6 | Deployment Planning | Budget allocation, timing, messaging |
| 6 | Sequential Persuasion Engine | Core engine implementation |
| 7 | Sequence Templates | All template types |
| 7 | Journey Tracking | User position management |
| 8 | Supply Path Optimizer | Path scoring, optimization |
| 8 | Portfolio Allocation | Budget optimization |
| 9-10 | Integration | All three products working together |

### Phase 3: Infrastructure (Weeks 11-16)

| Week | Focus | Deliverables |
|------|-------|--------------|
| 11 | FastAPI Endpoints | All REST endpoints |
| 11 | Authentication | API keys, rate limiting |
| 12 | LangGraph Workflows | Orchestration flows |
| 12 | ADAM Integration | Blackboard, Gradient Bridge |
| 13 | Learning Loop | Outcome processing |
| 13 | Gradient Signals | Cross-component propagation |
| 14 | WPP Adapter | Format translation |
| 14 | Error Handling | Recovery, fallbacks |
| 15-16 | Testing | Full test coverage |

### Phase 4: Deployment (Weeks 17-20)

| Week | Focus | Deliverables |
|------|-------|--------------|
| 17 | Staging Deployment | All services in staging |
| 17 | Performance Testing | Load tests, latency |
| 18 | WPP UAT | User acceptance testing |
| 18 | Documentation | API docs, guides |
| 19 | Production Deploy | Full rollout |
| 20 | Monitoring | Dashboards, alerts |

### Phase 5: Enhancement (Weeks 21-28)

| Week | Focus | Deliverables |
|------|-------|--------------|
| 21-22 | Journey Tracker Integration | Deep #10 integration |
| 23-24 | Copy Generation Integration | #15 creative guidance |
| 25-26 | Explanation Generation | #18 recommendation explanations |
| 27-28 | Optimization | Performance tuning |

---

## Success Metrics

### Product 1: Product-to-Inventory Match

| Metric | Target | Measurement |
|--------|--------|-------------|
| Segment Generation Quality | >0.7 confidence | Claude evaluation |
| Segment Accuracy | >70% align with converters | Post-campaign |
| Inventory Match Relevance | >0.6 alignment score | Algorithm scoring |
| Cold Start Waste Reduction | 40-60% less waste | A/B vs control |
| Time to Recommendation | <5 seconds | API latency |

### Product 2: Sequential Persuasion

| Metric | Target | Measurement |
|--------|--------|-------------|
| Sequence Completion Rate | >40% reach final step | User tracking |
| Conversion Lift vs Rotate | 30-50% improvement | A/B test |
| State Transition Accuracy | >60% advance correctly | Event analysis |
| Journey Attribution | >0.7 confidence | Attribution model |
| Real-time Decision Latency | <50ms | API latency |

### Product 3: Supply-Path Optimization

| Metric | Target | Measurement |
|--------|--------|-------------|
| CPM Savings | 15-25% vs unoptimized | Price comparison |
| Quality Improvement | >20% viewability lift | Third-party |
| Fraud Reduction | >50% less invalid traffic | Fraud detection |
| Path Coverage | >90% target publishers | Graph completeness |

### Business Impact

| Metric | Target | Calculation |
|--------|--------|-------------|
| WPP Platform Savings | $50M+ annually | Cold start waste × spend |
| Advertiser ROI | 30% improvement | Lift × AOV |
| ADAM Platform Revenue | $10M+ ARR | Licensing + usage |

---

## Revision History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | January 2026 | Initial specification |
| 2.0 | January 2026 | Deep structure integration with three core products |

---

**END OF ENHANCEMENT #28 v2.0: WPP AD DESK INTELLIGENCE LAYER**
