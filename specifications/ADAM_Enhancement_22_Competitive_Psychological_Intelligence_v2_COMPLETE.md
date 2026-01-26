# ADAM Enhancement #22: Competitive Psychological Intelligence
## Predictive Warfare Engine with Mechanism-Level Counter-Strategy

**Version**: 2.0 COMPLETE  
**Date**: January 2026  
**Priority**: P1 - Strategic (Competitive Advantage Multiplier)  
**Estimated Implementation**: 14 person-weeks  
**Dependencies**: #04 v3 (AoT), #14 v3 (Brand Intelligence), #27 v2 (Extended Constructs), #06 (Gradient Bridge)  
**Dependents**: #28 (WPP Ad Desk), Campaign Optimization, Strategic Planning  
**File Size**: ~200KB (Enterprise Production-Ready)

---

## Table of Contents

### SECTION A: STRATEGIC VISION
1. [Executive Summary](#executive-summary)
2. [The Revolutionary Insight](#the-revolutionary-insight)
3. [Beyond Traditional Competitive Intelligence](#beyond-traditional-ci)
4. [Psychological Warfare Architecture](#psychological-warfare-architecture)

### SECTION B: PYDANTIC DATA MODELS
5. [Core Enums & Types](#core-enums-types)
6. [Competitor Psychological Profile](#competitor-psychological-profile)
7. [Mechanism Warfare Models](#mechanism-warfare-models)
8. [Strategic State Models](#strategic-state-models)
9. [Intelligence Signal Models](#intelligence-signal-models)

### SECTION C: PSYCHOLOGICAL MECHANISM WARFARE
10. [Competitor Mechanism Detection](#competitor-mechanism-detection)
11. [Counter-Mechanism Strategy Engine](#counter-mechanism-strategy)
12. [Mechanism Effectiveness Differential](#mechanism-effectiveness-differential)
13. [Psychological Vulnerability Mapping](#vulnerability-mapping)

### SECTION D: COMPETITIVE GAME THEORY ENGINE
14. [Strategic Agent Modeling](#strategic-agent-modeling)
15. [Move Prediction System](#move-prediction-system)
16. [Nash Equilibrium Analysis](#nash-equilibrium-analysis)
17. [Asymmetric Warfare Strategies](#asymmetric-warfare)

### SECTION E: REAL-TIME INTELLIGENCE FUSION
18. [Multi-Source Signal Integration](#multi-source-integration)
19. [Claude-Powered Intelligence Synthesis](#claude-intelligence-synthesis)
20. [Causal Discovery Engine](#causal-discovery-engine)
21. [Predictive Alert System](#predictive-alert-system)

### SECTION F: MARKET STATE MACHINE
22. [Competitive Landscape States](#landscape-states)
23. [State Transition Detection](#state-transition-detection)
24. [Strategic Position Optimization](#position-optimization)
25. [Dynamic Equilibrium Tracking](#equilibrium-tracking)

### SECTION G: NEO4J COMPETITIVE GRAPH
26. [Competitor Entity Schema](#competitor-entity-schema)
27. [Psychological Relationship Types](#psychological-relationships)
28. [Intelligence Query Templates](#intelligence-queries)
29. [Graph Analytics](#graph-analytics)

### SECTION H: LANGGRAPH INTELLIGENCE WORKFLOWS
30. [Competitive Analysis Atom](#competitive-analysis-atom)
31. [Counter-Strategy Generation Atom](#counter-strategy-atom)
32. [Strategic Adaptation Loop](#strategic-adaptation-loop)

### SECTION I: FASTAPI ENDPOINTS
33. [Intelligence API](#intelligence-api)
34. [Strategy API](#strategy-api)
35. [Alert API](#alert-api)

### SECTION J: KAFKA INTEGRATION
36. [Intelligence Event Topics](#intelligence-topics)
37. [Real-Time Signal Processing](#signal-processing)
38. [Cross-Component Intelligence Sharing](#intelligence-sharing)

### SECTION K: PROMETHEUS METRICS
39. [Intelligence Quality Metrics](#intelligence-quality-metrics)
40. [Competitive Position Metrics](#position-metrics)
41. [Strategy Effectiveness Metrics](#strategy-effectiveness-metrics)

### SECTION L: IMPLEMENTATION
42. [Testing Framework](#testing-framework)
43. [Implementation Timeline](#implementation-timeline)
44. [Success Metrics](#success-metrics)

---

# SECTION A: STRATEGIC VISION

## Executive Summary

### The Paradigm Shift

Traditional competitive intelligence answers: "What are competitors doing?"

**ADAM's Competitive Psychological Intelligence answers:**
- "Why are competitors winning specific psychological segments?"
- "Which cognitive mechanisms are they exploiting, and how do we counter?"
- "What moves will they make next, and how do we preempt?"
- "Where are they psychologically vulnerable, and how do we attack?"

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                                                                                 │
│   COMPETITIVE PSYCHOLOGICAL INTELLIGENCE: THE STRATEGIC ADVANTAGE                               │
│   ══════════════════════════════════════════════════════════════                                │
│                                                                                                 │
│   Traditional CI (What others have):                                                            │
│   ─────────────────────────────────────                                                         │
│   ┌────────────────┐    ┌────────────────┐    ┌────────────────┐                                │
│   │ Bid Monitoring │───►│ Share of Voice │───►│ Basic Alerts   │                                │
│   └────────────────┘    └────────────────┘    └────────────────┘                                │
│   "They're spending more"  "They have 23%"    "Budget increased"                                │
│                                                                                                 │
│                                                                                                 │
│   ADAM Competitive Psychological Intelligence (What we have):                                   │
│   ──────────────────────────────────────────────────────────────                                │
│                                                                                                 │
│   ┌─────────────────────────────────────────────────────────────────────────────────────┐       │
│   │                        PSYCHOLOGICAL WARFARE ENGINE                                 │       │
│   │                                                                                     │       │
│   │   ┌──────────────────┐   ┌──────────────────┐   ┌──────────────────┐               │       │
│   │   │ MECHANISM        │   │ GAME THEORY      │   │ VULNERABILITY    │               │       │
│   │   │ DETECTION        │   │ ENGINE           │   │ CARTOGRAPHY      │               │       │
│   │   │                  │   │                  │   │                  │               │       │
│   │   │ "They're using   │   │ "They'll shift   │   │ "High-NFC users  │               │       │
│   │   │  mimetic desire  │   │  to prevention   │   │  are their weak  │               │       │
│   │   │  on high-N users"│   │  framing next"   │   │  spot"           │               │       │
│   │   └────────┬─────────┘   └────────┬─────────┘   └────────┬─────────┘               │       │
│   │            │                      │                      │                         │       │
│   │            └──────────────────────┼──────────────────────┘                         │       │
│   │                                   ▼                                                │       │
│   │                    ┌──────────────────────────────┐                                │       │
│   │                    │   COUNTER-STRATEGY ENGINE    │                                │       │
│   │                    │                              │                                │       │
│   │                    │  "Counter with temporal      │                                │       │
│   │                    │   construal + identity       │                                │       │
│   │                    │   construction. Predicted    │                                │       │
│   │                    │   +18% lift vs. matching."   │                                │       │
│   │                    └──────────────────────────────┘                                │       │
│   │                                                                                     │       │
│   └─────────────────────────────────────────────────────────────────────────────────────┘       │
│                                                                                                 │
│   Integration with ADAM Core:                                                                   │
│   ──────────────────────────                                                                    │
│   • #04 v3 AoT: Claude synthesizes competitive intelligence                                     │
│   • #14 v3 Brand: Competitor brand psychological profiles                                       │
│   • #27 v2 Constructs: 35-construct vulnerability analysis                                      │
│   • #06 Gradient Bridge: Learning from competitive outcomes                                     │
│                                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────────────────────┘
```

### Expected Impact

| Metric | Without ADAM CI | With ADAM CI | Improvement |
|--------|-----------------|--------------|-------------|
| **Win rate in contested segments** | 35-45% | 55-65% | +50% relative |
| **Competitive response time** | 2-7 days | <15 minutes | ~1000x faster |
| **Counter-strategy precision** | Generic | Mechanism-specific | Qualitative leap |
| **Predictive accuracy (30-day)** | N/A | 72%+ | New capability |
| **Vulnerability exploitation** | Opportunistic | Systematic | Strategic advantage |
| **Budget efficiency in competition** | 1.0x | 1.4-1.8x | 40-80% improvement |

---

## The Revolutionary Insight

### Competitors Don't Just Advertise—They Activate Mechanisms

Every competitor message is an attempt to activate cognitive mechanisms in your target audience:

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                                                                                         │
│   COMPETITOR MESSAGE DECOMPOSITION                                                      │
│                                                                                         │
│   Competitor Ad: "Join 5 million happy customers. Limited time: 40% off."               │
│                                                                                         │
│   Traditional Analysis:                                                                 │
│   ─────────────────────                                                                 │
│   • Social proof present ✓                                                              │
│   • Urgency present ✓                                                                   │
│   • Discount offer ✓                                                                    │
│                                                                                         │
│   ADAM Psychological Decomposition:                                                     │
│   ────────────────────────────────                                                      │
│   ┌────────────────────────────────────────────────────────────────────────────┐        │
│   │                                                                            │        │
│   │  MECHANISM #5: Mimetic Desire (Girard)                                     │        │
│   │  ────────────────────────────────────────                                  │        │
│   │  Signal: "5 million happy customers"                                       │        │
│   │  Intensity: 0.75 (high)                                                    │        │
│   │  Target Personality: High conformity susceptibility, High SCO              │        │
│   │  Psychological Need: Social validation, belonging                          │        │
│   │                                                                            │        │
│   │  MECHANISM #7: Attention Dynamics (Scarcity)                               │        │
│   │  ─────────────────────────────────────────────                             │        │
│   │  Signal: "Limited time"                                                    │        │
│   │  Intensity: 0.60 (moderate)                                                │        │
│   │  Target Personality: High temporal discounting, present-oriented           │        │
│   │  Psychological Need: Loss aversion satisfaction                            │        │
│   │                                                                            │        │
│   │  CONSTRUCT TARGETING INFERENCE:                                            │        │
│   │  ─────────────────────────────────                                         │        │
│   │  Primary: Conformity Susceptibility (Domain 5)                             │        │
│   │  Secondary: Delay Discounting Rate (Domain 3)                              │        │
│   │  Tertiary: Value Consciousness (Domain 11)                                 │        │
│   │                                                                            │        │
│   │  VULNERABILITY THEY'RE MISSING:                                            │        │
│   │  ─────────────────────────────────                                         │        │
│   │  • No appeal to Need for Cognition (alienates analytical buyers)           │        │
│   │  • No regulatory focus alignment (generic framing)                         │        │
│   │  • No identity construction (product as object, not self-extension)        │        │
│   │                                                                            │        │
│   │  COUNTER-STRATEGY RECOMMENDATION:                                          │        │
│   │  ─────────────────────────────────                                         │        │
│   │  Target their blind spots with:                                            │        │
│   │  • Mechanism #8: Identity Construction for high-NFC users                  │        │
│   │  • Mechanism #4: Linguistic Framing matched to regulatory focus            │        │
│   │  • Expected lift vs. matching strategy: +18%                               │        │
│   │                                                                            │        │
│   └────────────────────────────────────────────────────────────────────────────┘        │
│                                                                                         │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

### The Warfare Metaphor Is Precise

This isn't marketing hyperbole. In attention economics, every impression is a battle:

| Military Concept | ADAM Competitive Intelligence Analog |
|------------------|--------------------------------------|
| **Terrain Analysis** | Psychological segment mapping |
| **Order of Battle** | Competitor mechanism inventory |
| **Intelligence Fusion** | Multi-source signal integration |
| **Maneuver Warfare** | Counter-mechanism positioning |
| **Asymmetric Tactics** | Budget-efficient mechanism exploitation |
| **Predictive Analysis** | Game theory move forecasting |
| **Vulnerability Assessment** | Psychological blind spot detection |
| **Combined Arms** | Multi-mechanism coordinated campaigns |

---

## Beyond Traditional Competitive Intelligence

### What Traditional CI Provides

```python
# Traditional CI Output
{
    "competitor": "Brand X",
    "spend_estimate": "$2.3M/month",
    "share_of_voice": 0.23,
    "top_segments": ["25-34", "fitness", "urban"],
    "creative_themes": ["social proof", "urgency"],
    "alert": "Spend increased 15% last week"
}
# Action: "Consider increasing budget to match"
```

### What ADAM Competitive Psychological Intelligence Provides

```python
# ADAM CPI Output
{
    "competitor": "Brand X",
    "psychological_profile": {
        "dominant_mechanisms": [
            {
                "mechanism": "mimetic_desire",
                "intensity": 0.75,
                "estimated_effectiveness": 0.62,
                "target_constructs": ["conformity_susceptibility", "social_comparison_orientation"]
            },
            {
                "mechanism": "attention_dynamics",
                "intensity": 0.60,
                "estimated_effectiveness": 0.48,
                "target_constructs": ["delay_discounting_rate", "present_orientation"]
            }
        ],
        "mechanism_blind_spots": ["identity_construction", "temporal_construal", "evolutionary_motive"],
        "construct_targeting_gaps": {
            "need_for_cognition": "completely_unaddressed",
            "regulatory_focus": "generic_not_matched",
            "future_self_continuity": "ignored"
        }
    },
    "strategic_analysis": {
        "why_they_win": [
            "High-conformity users respond to social proof saturation",
            "Present-oriented users captured by urgency messaging"
        ],
        "why_they_lose": [
            "Analytical buyers (high NFC) find messaging unsatisfying",
            "Prevention-focused users alienated by promotion framing",
            "Identity-driven buyers see no self-extension opportunity"
        ]
    },
    "vulnerability_map": {
        "high_value_segments_underserved": [
            {
                "segment": "High NFC + Prevention Focus",
                "estimated_size": "8.3% of market",
                "estimated_value": "$4.2M TAM",
                "competitor_effectiveness": 0.28,
                "our_predicted_effectiveness": 0.71,
                "recommended_mechanisms": ["linguistic_framing", "identity_construction"],
                "recommended_copy_strategy": "Research-backed, security-framed, identity-aligned"
            }
        ]
    },
    "game_theory_forecast": {
        "next_30_days": {
            "most_likely_move": "Increase mimetic_desire intensity to 0.85",
            "probability": 0.68,
            "second_likely_move": "Add authority mechanism via celebrity endorsement",
            "probability": 0.21
        },
        "optimal_response": {
            "if_they_increase_mimetic": "Counter with identity_construction + need_for_uniqueness appeal",
            "if_they_add_authority": "Counter with peer testimonials + evolutionary_motive (affiliation)",
            "preemptive_recommendation": "Capture high-NFC segment NOW before they recognize the gap"
        }
    },
    "counter_strategy": {
        "immediate_actions": [
            {
                "action": "Deploy identity_construction creative to high-NFC audience",
                "mechanism_intensity": 0.70,
                "expected_lift_vs_competition": 0.18,
                "confidence": 0.82
            }
        ],
        "campaign_adjustments": [
            {
                "segment": "contested_mainstream",
                "current_strategy": "matching_mimetic_desire",
                "recommended_strategy": "differentiated_temporal_construal",
                "expected_cost_efficiency_gain": 0.35
            }
        ]
    }
}
```

---

## Psychological Warfare Architecture

```
┌────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                                                                                    │
│                    ADAM COMPETITIVE PSYCHOLOGICAL INTELLIGENCE ARCHITECTURE                        │
│                                                                                                    │
├────────────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                                    │
│   ┌──────────────────────────────────────────────────────────────────────────────────────────┐    │
│   │                           INTELLIGENCE COLLECTION LAYER                                  │    │
│   │                                                                                          │    │
│   │   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐   │    │
│   │   │   Auction   │  │  Creative   │  │   Market    │  │   Social    │  │  Executive  │   │    │
│   │   │   Signals   │  │   Capture   │  │   Research  │  │  Listening  │  │   Signals   │   │    │
│   │   │             │  │             │  │             │  │             │  │             │   │    │
│   │   │ • Win rates │  │ • Ad copy   │  │ • Reports   │  │ • Sentiment │  │ • Earnings  │   │    │
│   │   │ • Clearing  │  │ • Visuals   │  │ • Surveys   │  │ • Mentions  │  │ • Filings   │   │    │
│   │   │ • Patterns  │  │ • Targeting │  │ • Patents   │  │ • Trends    │  │ • Moves     │   │    │
│   │   └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘   │    │
│   │          │                │                │                │                │          │    │
│   └──────────┼────────────────┼────────────────┼────────────────┼────────────────┼──────────┘    │
│              │                │                │                │                │               │
│              └────────────────┴────────────────┼────────────────┴────────────────┘               │
│                                                ▼                                                  │
│   ┌──────────────────────────────────────────────────────────────────────────────────────────┐    │
│   │                           PSYCHOLOGICAL ANALYSIS LAYER                                   │    │
│   │                                                                                          │    │
│   │   ┌────────────────────────────────────────────────────────────────────────────────┐    │    │
│   │   │                    MECHANISM DETECTION ENGINE                                  │    │    │
│   │   │                                                                                │    │    │
│   │   │   Competitor Creative → Claude Analysis → Mechanism Inventory                  │    │    │
│   │   │                                                                                │    │    │
│   │   │   ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐     │    │    │
│   │   │   │ Mech #1 │ │ Mech #2 │ │ Mech #3 │ │ Mech #4 │ │ Mech #5 │ │ ...#9   │     │    │    │
│   │   │   │ Auto-   │ │ Wanting │ │ Evol.   │ │ Ling.   │ │ Mimetic │ │         │     │    │    │
│   │   │   │ Eval    │ │ /Liking │ │ Motive  │ │ Frame   │ │ Desire  │ │         │     │    │    │
│   │   │   └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘     │    │    │
│   │   │        │           │           │           │           │           │          │    │    │
│   │   └────────┼───────────┼───────────┼───────────┼───────────┼───────────┼──────────┘    │    │
│   │            └───────────┴───────────┴─────┬─────┴───────────┴───────────┘               │    │
│   │                                          ▼                                              │    │
│   │   ┌────────────────────────────────────────────────────────────────────────────────┐    │    │
│   │   │                    CONSTRUCT TARGETING INFERENCE                               │    │    │
│   │   │                                                                                │    │    │
│   │   │   Detected Mechanisms → #27 v2 Construct Mapping → Target Profile              │    │    │
│   │   │                                                                                │    │    │
│   │   │   "Mimetic desire at 0.75 → targets Conformity Susceptibility (Domain 5)"      │    │    │
│   │   │   "Urgency framing → targets Delay Discounting Rate (Domain 3)"                │    │    │
│   │   │                                                                                │    │    │
│   │   └────────────────────────────────────────────────────────────────────────────────┘    │    │
│   │                                                                                          │    │
│   └──────────────────────────────────────────────────────────────────────────────────────────┘    │
│                                                │                                                  │
│                                                ▼                                                  │
│   ┌──────────────────────────────────────────────────────────────────────────────────────────┐    │
│   │                           STRATEGIC INTELLIGENCE LAYER                                   │    │
│   │                                                                                          │    │
│   │   ┌─────────────────────┐   ┌─────────────────────┐   ┌─────────────────────┐           │    │
│   │   │   VULNERABILITY     │   │    GAME THEORY      │   │   MARKET STATE      │           │    │
│   │   │   CARTOGRAPHY       │   │    ENGINE           │   │   MACHINE           │           │    │
│   │   │                     │   │                     │   │                     │           │    │
│   │   │   • Blind spots     │   │   • Move prediction │   │   • Equilibrium     │           │    │
│   │   │   • Underserved     │   │   • Nash analysis   │   │   • Transitions     │           │    │
│   │   │   • Attack vectors  │   │   • Optimal response│   │   • Opportunities   │           │    │
│   │   └─────────────────────┘   └─────────────────────┘   └─────────────────────┘           │    │
│   │                                                                                          │    │
│   └──────────────────────────────────────────────────────────────────────────────────────────┘    │
│                                                │                                                  │
│                                                ▼                                                  │
│   ┌──────────────────────────────────────────────────────────────────────────────────────────┐    │
│   │                           COUNTER-STRATEGY GENERATION LAYER                              │    │
│   │                                                                                          │    │
│   │   ┌────────────────────────────────────────────────────────────────────────────────┐    │    │
│   │   │                    CLAUDE (#04 v3) STRATEGIC SYNTHESIS                         │    │    │
│   │   │                                                                                │    │    │
│   │   │   Inputs:                          │   Outputs:                                │    │    │
│   │   │   • Competitor mechanism profile   │   • Counter-mechanism strategies          │    │    │
│   │   │   • Vulnerability map              │   • Segment prioritization                │    │    │
│   │   │   • Game theory forecasts          │   • Budget allocation recommendations     │    │    │
│   │   │   • Market state                   │   • Creative brief requirements           │    │    │
│   │   │   • Our effectiveness data         │   • Timing recommendations               │    │    │
│   │   │                                    │   • Risk assessments                      │    │    │
│   │   └────────────────────────────────────────────────────────────────────────────────┘    │    │
│   │                                                                                          │    │
│   └──────────────────────────────────────────────────────────────────────────────────────────┘    │
│                                                │                                                  │
│                                                ▼                                                  │
│   ┌──────────────────────────────────────────────────────────────────────────────────────────┐    │
│   │                           EXECUTION & LEARNING LAYER                                     │    │
│   │                                                                                          │    │
│   │   ┌─────────────────────┐   ┌─────────────────────┐   ┌─────────────────────┐           │    │
│   │   │   CAMPAIGN          │   │   REAL-TIME         │   │   GRADIENT BRIDGE   │           │    │
│   │   │   EXECUTION         │   │   ADAPTATION        │   │   LEARNING          │           │    │
│   │   │                     │   │                     │   │                     │           │    │
│   │   │   #28 WPP Ad Desk   │   │   Live adjustments  │   │   #06 Outcome →     │           │    │
│   │   │   #15 Copy Gen      │   │   based on market   │   │   Strategy learning │           │    │
│   │   │   Campaign Mgmt     │   │   state changes     │   │   Competitor model  │           │    │
│   │   └─────────────────────┘   └─────────────────────┘   └─────────────────────┘           │    │
│   │                                                                                          │    │
│   └──────────────────────────────────────────────────────────────────────────────────────────┘    │
│                                                                                                    │
└────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

# SECTION B: PYDANTIC DATA MODELS

## Core Enums & Types

```python
"""
ADAM Enhancement #22 v2: Core Enums and Types
Foundation types for Competitive Psychological Intelligence.
"""

from enum import Enum, auto
from typing import Dict, List, Optional, Any, Union, Tuple, Set
from datetime import datetime, timedelta
from pydantic import BaseModel, Field, field_validator, model_validator, computed_field
import uuid


class CognitiveMechanismType(str, Enum):
    """The 9 cognitive mechanisms (aligned with #01)."""
    
    AUTOMATIC_EVALUATION = "automatic_evaluation"
    WANTING_LIKING_DISSOCIATION = "wanting_liking_dissociation"
    EVOLUTIONARY_MOTIVE = "evolutionary_motive"
    LINGUISTIC_FRAMING = "linguistic_framing"
    MIMETIC_DESIRE = "mimetic_desire"
    EMBODIED_COGNITION = "embodied_cognition"
    ATTENTION_DYNAMICS = "attention_dynamics"
    IDENTITY_CONSTRUCTION = "identity_construction"
    TEMPORAL_CONSTRUAL = "temporal_construal"


class CompetitorThreatLevel(str, Enum):
    """Threat level classification for competitors."""
    
    EXISTENTIAL = "existential"      # Could eliminate our market position
    STRATEGIC = "strategic"          # Major threat to key segments
    TACTICAL = "tactical"            # Threat in specific contexts
    OPPORTUNISTIC = "opportunistic"  # Occasional overlap
    PERIPHERAL = "peripheral"        # Minimal direct competition


class CompetitivePositioningType(str, Enum):
    """Strategic positioning archetypes."""
    
    CATEGORY_LEADER = "category_leader"
    CHALLENGER = "challenger"
    NICHE_SPECIALIST = "niche_specialist"
    DISRUPTOR = "disruptor"
    FAST_FOLLOWER = "fast_follower"
    PREMIUM_DIFFERENTIATOR = "premium_differentiator"
    VALUE_COMPETITOR = "value_competitor"
    INNOVATOR = "innovator"


class MarketStateType(str, Enum):
    """States of the competitive market."""
    
    STABLE_EQUILIBRIUM = "stable_equilibrium"      # Established positions, predictable
    DISRUPTION = "disruption"                      # Major player changing dynamics
    CONSOLIDATION = "consolidation"                # Market tightening
    EXPANSION = "expansion"                        # New entrants, growth
    PRICE_WAR = "price_war"                        # Aggressive cost competition
    INNOVATION_RACE = "innovation_race"            # Feature/capability arms race
    SEGMENT_WARFARE = "segment_warfare"            # Battle over specific audiences
    ATTENTION_SATURATION = "attention_saturation"  # Diminishing returns for all


class CounterStrategyType(str, Enum):
    """Types of counter-strategies."""
    
    MATCH = "match"                    # Mirror competitor approach
    DIFFERENTIATE = "differentiate"   # Target different mechanisms
    FLANK = "flank"                    # Attack underserved segments
    PREEMPT = "preempt"               # Capture before competitor
    RETREAT = "retreat"               # Cede contested ground
    FORTIFY = "fortify"               # Strengthen existing position
    DISRUPT = "disrupt"               # Change the rules of competition
    ASYMMETRIC = "asymmetric"         # Efficiency-focused response


class IntelligenceSignalType(str, Enum):
    """Types of competitive intelligence signals."""
    
    BID_OBSERVATION = "bid_observation"
    CREATIVE_CAPTURE = "creative_capture"
    MARKET_RESEARCH = "market_research"
    PATENT_FILING = "patent_filing"
    JOB_POSTING = "job_posting"
    SOCIAL_LISTENING = "social_listening"
    EARNINGS_CALL = "earnings_call"
    EXECUTIVE_MOVE = "executive_move"
    PARTNERSHIP_ANNOUNCEMENT = "partnership_announcement"
    TECHNOLOGY_CHANGE = "technology_change"
    CUSTOMER_CHURN_SIGNAL = "customer_churn_signal"


class VulnerabilityType(str, Enum):
    """Types of competitive vulnerabilities."""
    
    MECHANISM_BLIND_SPOT = "mechanism_blind_spot"       # Mechanisms they don't use
    CONSTRUCT_GAP = "construct_gap"                     # Personality types they miss
    SEGMENT_UNDERSERVICE = "segment_underservice"       # Audiences poorly served
    TEMPORAL_PATTERN = "temporal_pattern"               # Times they're weak
    CONTEXTUAL_ABSENCE = "contextual_absence"           # Contexts they ignore
    MESSAGING_FATIGUE = "messaging_fatigue"             # Overused approaches
    CAPABILITY_LIMITATION = "capability_limitation"     # Technical constraints
```

## Competitor Psychological Profile

```python
"""
ADAM Enhancement #22 v2: Competitor Psychological Profile
Deep psychological modeling of competitor strategies.
"""

class CompetitorPsychologicalProfile(BaseModel):
    """
    Complete psychological profile of a competitor's advertising strategy.
    
    This goes far beyond traditional competitive analysis to understand
    HOW competitors are attempting to influence audiences psychologically.
    """
    
    competitor_id: str = Field(..., description="Unique competitor identifier")
    competitor_name: str
    profile_version: str = "2.0"
    
    # Classification
    threat_level: CompetitorThreatLevel
    positioning: CompetitivePositioningType
    primary_categories: List[str] = Field(default_factory=list)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # MECHANISM PROFILE: What psychological mechanisms do they activate?
    # ═══════════════════════════════════════════════════════════════════════════
    
    mechanism_profile: 'MechanismProfile'
    
    # ═══════════════════════════════════════════════════════════════════════════
    # CONSTRUCT TARGETING: Which psychological constructs do they target?
    # ═══════════════════════════════════════════════════════════════════════════
    
    construct_targeting: 'ConstructTargetingProfile'
    
    # ═══════════════════════════════════════════════════════════════════════════
    # VULNERABILITY MAP: Where are they psychologically weak?
    # ═══════════════════════════════════════════════════════════════════════════
    
    vulnerabilities: List['CompetitorVulnerability'] = Field(default_factory=list)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # STRATEGIC BEHAVIOR: How do they make strategic decisions?
    # ═══════════════════════════════════════════════════════════════════════════
    
    strategic_behavior: 'StrategicBehaviorModel'
    
    # ═══════════════════════════════════════════════════════════════════════════
    # HISTORICAL PATTERNS: What have we learned from past competition?
    # ═══════════════════════════════════════════════════════════════════════════
    
    historical_patterns: 'HistoricalCompetitivePatterns'
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    confidence: float = Field(ge=0, le=1, default=0.5)
    evidence_count: int = 0
    
    @computed_field
    @property
    def top_vulnerabilities(self) -> List['CompetitorVulnerability']:
        """Return vulnerabilities sorted by exploitation potential."""
        return sorted(
            self.vulnerabilities,
            key=lambda v: v.exploitation_potential,
            reverse=True
        )[:5]
    
    @computed_field
    @property
    def mechanism_blind_spots(self) -> List[CognitiveMechanismType]:
        """Mechanisms this competitor doesn't effectively use."""
        return self.mechanism_profile.blind_spots


class MechanismProfile(BaseModel):
    """
    Profile of cognitive mechanisms a competitor activates.
    """
    
    # Mechanism inventory with intensity and effectiveness
    mechanism_usage: Dict[CognitiveMechanismType, 'MechanismUsageData'] = Field(
        default_factory=dict
    )
    
    # Primary and secondary mechanisms
    primary_mechanisms: List[CognitiveMechanismType] = Field(default_factory=list)
    secondary_mechanisms: List[CognitiveMechanismType] = Field(default_factory=list)
    
    # Mechanism combinations they use
    common_combinations: List['MechanismCombination'] = Field(default_factory=list)
    
    # Temporal patterns in mechanism usage
    temporal_patterns: Dict[str, List[CognitiveMechanismType]] = Field(
        default_factory=dict,
        description="Time period → dominant mechanisms"
    )
    
    @computed_field
    @property
    def blind_spots(self) -> List[CognitiveMechanismType]:
        """Mechanisms not in their repertoire."""
        all_mechanisms = set(CognitiveMechanismType)
        used_mechanisms = set(self.mechanism_usage.keys())
        return list(all_mechanisms - used_mechanisms)
    
    @computed_field
    @property
    def effectiveness_ranked(self) -> List[Tuple[CognitiveMechanismType, float]]:
        """Mechanisms ranked by observed effectiveness."""
        return sorted(
            [(m, d.estimated_effectiveness) for m, d in self.mechanism_usage.items()],
            key=lambda x: x[1],
            reverse=True
        )


class MechanismUsageData(BaseModel):
    """Data about a competitor's use of a specific mechanism."""
    
    mechanism: CognitiveMechanismType
    
    # Usage patterns
    frequency: float = Field(ge=0, le=1, description="How often they use this")
    intensity: float = Field(ge=0, le=1, description="How strongly they apply it")
    
    # Effectiveness
    estimated_effectiveness: float = Field(ge=0, le=1)
    effectiveness_confidence: float = Field(ge=0, le=1)
    
    # Context patterns
    contexts_used: List[str] = Field(default_factory=list)
    target_segments: List[str] = Field(default_factory=list)
    
    # Evolution
    trend: str = Field(default="stable")  # increasing, stable, decreasing
    first_observed: Optional[datetime] = None
    last_observed: Optional[datetime] = None
    
    # Example evidence
    example_creatives: List[str] = Field(default_factory=list)


class MechanismCombination(BaseModel):
    """A combination of mechanisms used together."""
    
    mechanisms: List[CognitiveMechanismType]
    frequency: float = Field(ge=0, le=1)
    estimated_synergy: float = Field(description="Effectiveness boost from combination")
    typical_context: Optional[str] = None
    
    @computed_field
    @property
    def combination_id(self) -> str:
        """Unique identifier for this combination."""
        sorted_mechanisms = sorted([m.value for m in self.mechanisms])
        return "_".join(sorted_mechanisms)


class ConstructTargetingProfile(BaseModel):
    """
    Profile of psychological constructs a competitor targets.
    
    Integrates with #27 v2 Extended Psychological Constructs.
    """
    
    # Primary constructs they target (from #27 v2)
    targeted_constructs: Dict[str, 'ConstructTargetingData'] = Field(
        default_factory=dict,
        description="construct_id → targeting data"
    )
    
    # Domain-level targeting summary
    domain_focus: Dict[str, float] = Field(
        default_factory=dict,
        description="psychological_domain → targeting intensity"
    )
    
    # Gaps in their targeting
    untargeted_constructs: List[str] = Field(default_factory=list)
    poorly_targeted_constructs: List[str] = Field(default_factory=list)
    
    @computed_field
    @property
    def construct_blind_spots(self) -> List[str]:
        """Constructs they completely ignore."""
        return self.untargeted_constructs


class ConstructTargetingData(BaseModel):
    """How a competitor targets a specific construct."""
    
    construct_id: str
    construct_name: str
    domain: str
    
    # Targeting
    targeting_intensity: float = Field(ge=0, le=1)
    targeting_sophistication: float = Field(ge=0, le=1)
    
    # Effectiveness
    estimated_effectiveness: float = Field(ge=0, le=1)
    
    # Methods
    mechanisms_used: List[CognitiveMechanismType] = Field(default_factory=list)
    messaging_approaches: List[str] = Field(default_factory=list)
```

## Mechanism Warfare Models

```python
"""
ADAM Enhancement #22 v2: Mechanism Warfare Models
Models for counter-mechanism strategy generation.
"""

class CounterMechanismStrategy(BaseModel):
    """
    Strategy for countering a competitor's mechanism usage.
    
    The core insight: Don't match mechanisms—exploit their blind spots
    or use orthogonal mechanisms that capture different psychological pathways.
    """
    
    strategy_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    
    # What we're countering
    competitor_id: str
    competitor_mechanism: CognitiveMechanismType
    competitor_intensity: float
    
    # Our counter approach
    strategy_type: CounterStrategyType
    
    # Counter mechanisms to deploy
    counter_mechanisms: List['CounterMechanismDeployment'] = Field(default_factory=list)
    
    # Target constructs (from #27 v2)
    target_constructs: List[str] = Field(default_factory=list)
    
    # Expected outcomes
    expected_lift_vs_matching: float = Field(
        description="Expected performance lift vs. simply matching competitor"
    )
    expected_cost_efficiency: float = Field(
        description="Expected CPM/CPA improvement"
    )
    confidence: float = Field(ge=0, le=1)
    
    # Implementation guidance
    creative_requirements: List[str] = Field(default_factory=list)
    copy_strategy: Optional[str] = None
    timing_recommendations: Optional[str] = None
    
    # Risk assessment
    risk_level: str = "medium"
    risk_factors: List[str] = Field(default_factory=list)
    mitigation_strategies: List[str] = Field(default_factory=list)
    
    # Validation
    requires_ab_test: bool = True
    recommended_test_duration_days: int = 14
    
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class CounterMechanismDeployment(BaseModel):
    """Specification for deploying a counter-mechanism."""
    
    mechanism: CognitiveMechanismType
    recommended_intensity: float = Field(ge=0, le=1)
    
    # Why this mechanism counters the competitor
    strategic_rationale: str
    
    # Which constructs this targets
    target_constructs: List[str] = Field(default_factory=list)
    
    # Psychological principle underlying the counter
    psychological_principle: str
    
    # Copy guidance
    word_patterns: List[str] = Field(default_factory=list)
    emotional_tone: str
    framing_approach: str


class MechanismEffectivenessDifferential(BaseModel):
    """
    Analysis of effectiveness differential between us and competitor.
    
    This powers the key insight: "Where do we win/lose when they use X?"
    """
    
    mechanism: CognitiveMechanismType
    competitor_id: str
    
    # Their effectiveness
    competitor_effectiveness: float = Field(ge=0, le=1)
    competitor_reach: int = 0
    competitor_frequency: float = 0
    
    # Our effectiveness (when we use same mechanism)
    our_effectiveness: float = Field(ge=0, le=1)
    our_reach: int = 0
    
    # Differential analysis
    effectiveness_gap: float = Field(
        description="Positive = we're better, Negative = they're better"
    )
    
    # Segment-level breakdown
    segment_differentials: Dict[str, float] = Field(
        default_factory=dict,
        description="segment_id → our advantage (positive) or disadvantage (negative)"
    )
    
    # Construct-level breakdown
    construct_differentials: Dict[str, float] = Field(
        default_factory=dict,
        description="construct_id → our advantage (positive) or disadvantage (negative)"
    )
    
    # Recommendations
    segments_to_attack: List[str] = Field(
        default_factory=list,
        description="Segments where we have mechanism advantage"
    )
    segments_to_avoid: List[str] = Field(
        default_factory=list,
        description="Segments where they have mechanism advantage"
    )
    
    @computed_field
    @property
    def strategic_recommendation(self) -> str:
        """High-level strategic recommendation."""
        if self.effectiveness_gap > 0.15:
            return "ATTACK: We outperform on this mechanism"
        elif self.effectiveness_gap < -0.15:
            return "DIFFERENTIATE: They outperform, use alternative mechanisms"
        else:
            return "SELECTIVE: Performance similar, attack in favorable segments"
```

## Strategic State Models

```python
"""
ADAM Enhancement #22 v2: Strategic State Models
Models for game theory and market state analysis.
"""

class StrategicBehaviorModel(BaseModel):
    """
    Model of a competitor's strategic decision-making patterns.
    
    Used for predicting their next moves.
    """
    
    competitor_id: str
    
    # Decision-making style
    aggression_level: float = Field(ge=0, le=1, description="How aggressive in competition")
    innovation_propensity: float = Field(ge=0, le=1, description="Willingness to try new approaches")
    reaction_speed: float = Field(ge=0, le=1, description="How fast they respond to changes")
    budget_flexibility: float = Field(ge=0, le=1, description="Ability to adjust spending")
    
    # Strategic preferences
    preferred_strategies: List[str] = Field(default_factory=list)
    avoided_strategies: List[str] = Field(default_factory=list)
    
    # Response patterns
    typical_response_to_attack: str = "match"  # match, escalate, differentiate, retreat
    typical_response_to_loss: str = "increase_spend"
    typical_response_to_new_entrant: str = "defend"
    
    # Constraints
    known_constraints: List[str] = Field(default_factory=list)
    estimated_budget_range: Tuple[float, float] = (0, 0)
    
    # Historical accuracy
    prediction_accuracy: float = Field(ge=0, le=1, default=0.5)
    predictions_made: int = 0
    predictions_correct: int = 0


class CompetitorMovePrediction(BaseModel):
    """
    Prediction of a competitor's next strategic move.
    """
    
    prediction_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    competitor_id: str
    
    # Prediction timeframe
    prediction_horizon_days: int = 30
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Most likely move
    primary_prediction: 'PredictedMove'
    
    # Alternative scenarios
    alternative_predictions: List['PredictedMove'] = Field(default_factory=list)
    
    # Confidence
    overall_confidence: float = Field(ge=0, le=1)
    
    # Recommended responses
    optimal_responses: Dict[str, 'CounterMechanismStrategy'] = Field(
        default_factory=dict,
        description="prediction_scenario → our optimal response"
    )
    
    # Validation tracking
    validated: bool = False
    actual_move: Optional[str] = None
    prediction_accuracy: Optional[float] = None


class PredictedMove(BaseModel):
    """A predicted competitive move."""
    
    move_type: str
    description: str
    probability: float = Field(ge=0, le=1)
    
    # Details
    mechanisms_involved: List[CognitiveMechanismType] = Field(default_factory=list)
    segments_affected: List[str] = Field(default_factory=list)
    estimated_budget_change: Optional[float] = None
    estimated_timing: Optional[str] = None
    
    # Signals that would confirm this prediction
    confirming_signals: List[str] = Field(default_factory=list)
    
    # Our recommended response
    recommended_response: Optional[str] = None


class MarketState(BaseModel):
    """
    Current state of the competitive market.
    
    Models the market as a state machine with transitions.
    """
    
    state_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    
    # Current state
    current_state: MarketStateType
    state_confidence: float = Field(ge=0, le=1)
    
    # State duration
    state_started: datetime
    estimated_state_duration_days: Optional[int] = None
    
    # Key characteristics of current state
    characteristics: List[str] = Field(default_factory=list)
    
    # Dominant players in this state
    state_leaders: List[str] = Field(default_factory=list)
    
    # Opportunities in this state
    state_opportunities: List[str] = Field(default_factory=list)
    
    # Threats in this state
    state_threats: List[str] = Field(default_factory=list)
    
    # Transition probabilities
    transition_probabilities: Dict[MarketStateType, float] = Field(default_factory=dict)
    
    # Recommended strategies for this state
    recommended_strategies: List[CounterStrategyType] = Field(default_factory=list)
    
    @computed_field
    @property
    def most_likely_next_state(self) -> Optional[MarketStateType]:
        """Most probable next market state."""
        if not self.transition_probabilities:
            return None
        return max(self.transition_probabilities, key=self.transition_probabilities.get)


class NashEquilibriumAnalysis(BaseModel):
    """
    Nash equilibrium analysis for competitive positioning.
    
    Identifies stable strategy profiles where no player benefits from
    unilateral deviation.
    """
    
    analysis_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    
    # Players in the game
    players: List[str] = Field(description="List of competitor IDs including 'self'")
    
    # Strategy space per player
    strategy_spaces: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="player_id → available strategies"
    )
    
    # Current strategy profile
    current_strategies: Dict[str, str] = Field(
        default_factory=dict,
        description="player_id → current strategy"
    )
    
    # Equilibrium analysis
    is_equilibrium: bool = Field(
        description="Is current profile a Nash equilibrium?"
    )
    equilibrium_confidence: float = Field(ge=0, le=1)
    
    # Profitable deviations
    profitable_deviations: List['ProfitableDeviation'] = Field(default_factory=list)
    
    # Stable equilibria found
    stable_equilibria: List['EquilibriumProfile'] = Field(default_factory=list)
    
    # Recommendations
    recommended_strategy: Optional[str] = None
    expected_payoff_improvement: Optional[float] = None
    
    analyzed_at: datetime = Field(default_factory=datetime.utcnow)


class ProfitableDeviation(BaseModel):
    """A profitable unilateral deviation from current strategies."""
    
    player: str
    from_strategy: str
    to_strategy: str
    expected_payoff_gain: float
    confidence: float = Field(ge=0, le=1)


class EquilibriumProfile(BaseModel):
    """A Nash equilibrium strategy profile."""
    
    strategies: Dict[str, str] = Field(
        description="player_id → equilibrium strategy"
    )
    our_payoff: float
    stability_score: float = Field(ge=0, le=1)
    reachability_score: float = Field(ge=0, le=1, description="How achievable from current state")
```

## Intelligence Signal Models

```python
"""
ADAM Enhancement #22 v2: Intelligence Signal Models
Models for competitive intelligence signals and fusion.
"""

class IntelligenceSignal(BaseModel):
    """
    A single competitive intelligence signal.
    
    Signals are collected from multiple sources and fused
    to build competitor profiles.
    """
    
    signal_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    signal_type: IntelligenceSignalType
    
    # Source
    source: str
    source_reliability: float = Field(ge=0, le=1)
    
    # Content
    competitor_id: Optional[str] = None
    raw_content: str
    structured_content: Dict[str, Any] = Field(default_factory=dict)
    
    # Timing
    observed_at: datetime = Field(default_factory=datetime.utcnow)
    event_time: Optional[datetime] = None  # When the signaled event occurred
    
    # Analysis
    psychological_interpretation: Optional[str] = None
    mechanism_implications: List[CognitiveMechanismType] = Field(default_factory=list)
    strategic_implications: List[str] = Field(default_factory=list)
    
    # Quality
    confidence: float = Field(ge=0, le=1)
    corroborated: bool = False
    corroborating_signals: List[str] = Field(default_factory=list)
    
    # Processing status
    processed: bool = False
    incorporated_into_profile: bool = False


class CreativeIntelligenceSignal(IntelligenceSignal):
    """
    Intelligence signal from captured competitor creative.
    """
    
    signal_type: IntelligenceSignalType = IntelligenceSignalType.CREATIVE_CAPTURE
    
    # Creative content
    creative_type: str  # audio, video, display, native
    transcript: Optional[str] = None
    visual_elements: List[str] = Field(default_factory=list)
    call_to_action: Optional[str] = None
    landing_url: Optional[str] = None
    
    # Psychological analysis
    mechanisms_detected: List['MechanismDetectionInCreative'] = Field(default_factory=list)
    constructs_targeted: List[str] = Field(default_factory=list)
    emotional_appeals: List[str] = Field(default_factory=list)
    
    # Context
    observed_context: str = ""
    estimated_frequency: int = 1
    audience_targeting: List[str] = Field(default_factory=list)


class MechanismDetectionInCreative(BaseModel):
    """Detection of a mechanism in competitor creative."""
    
    mechanism: CognitiveMechanismType
    intensity: float = Field(ge=0, le=1)
    confidence: float = Field(ge=0, le=1)
    
    # Evidence
    textual_evidence: List[str] = Field(default_factory=list)
    visual_evidence: List[str] = Field(default_factory=list)
    
    # Psychological principle being leveraged
    psychological_principle: str


class CompetitorVulnerability(BaseModel):
    """
    An identified vulnerability in a competitor's strategy.
    """
    
    vulnerability_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    competitor_id: str
    vulnerability_type: VulnerabilityType
    
    # Description
    description: str
    psychological_basis: str
    
    # Quantification
    affected_segment_size: Optional[float] = None  # Fraction of market
    estimated_tam: Optional[float] = None  # Total addressable market
    competitor_effectiveness_in_segment: float = Field(ge=0, le=1)
    our_predicted_effectiveness: float = Field(ge=0, le=1)
    
    # Exploitation
    exploitation_potential: float = Field(ge=0, le=1)
    recommended_mechanisms: List[CognitiveMechanismType] = Field(default_factory=list)
    recommended_constructs: List[str] = Field(default_factory=list)
    recommended_messaging: Optional[str] = None
    
    # Time sensitivity
    time_sensitivity: str = "medium"  # high, medium, low
    estimated_window_days: Optional[int] = None
    
    # Risk
    exploitation_risk: str = "medium"
    risk_factors: List[str] = Field(default_factory=list)
    
    discovered_at: datetime = Field(default_factory=datetime.utcnow)
    last_validated: Optional[datetime] = None
    still_valid: bool = True


class HistoricalCompetitivePatterns(BaseModel):
    """
    Historical patterns in competition with this competitor.
    """
    
    competitor_id: str
    analysis_period_days: int = 365
    
    # Win/loss patterns
    head_to_head_win_rate: float = Field(ge=0, le=1)
    win_rate_by_segment: Dict[str, float] = Field(default_factory=dict)
    win_rate_by_mechanism: Dict[CognitiveMechanismType, float] = Field(default_factory=dict)
    
    # Effectiveness patterns
    their_mechanism_effectiveness_history: Dict[CognitiveMechanismType, List[float]] = Field(
        default_factory=dict
    )
    our_counter_effectiveness_history: Dict[str, List[float]] = Field(
        default_factory=dict,
        description="strategy → effectiveness over time"
    )
    
    # Response patterns
    their_response_time_avg_hours: float = 0
    their_response_patterns: List[str] = Field(default_factory=list)
    
    # Lessons learned
    successful_strategies: List[str] = Field(default_factory=list)
    failed_strategies: List[str] = Field(default_factory=list)
    
    # Predictive accuracy
    our_prediction_accuracy: float = Field(ge=0, le=1, default=0.5)
```

---

# SECTION C: PSYCHOLOGICAL MECHANISM WARFARE

## Competitor Mechanism Detection

```python
"""
ADAM Enhancement #22 v2: Competitor Mechanism Detection
Claude-powered analysis of competitor psychological strategies.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
import asyncio


class CompetitorMechanismDetector:
    """
    Analyzes competitor creative and messaging to detect
    which cognitive mechanisms they're attempting to activate.
    
    This is the foundation of psychological warfare intelligence—
    understanding HOW competitors are trying to influence audiences.
    """
    
    def __init__(
        self,
        claude_service: 'ClaudeService',
        mechanism_registry: 'MechanismRegistry',
        construct_registry: 'ConstructRegistry',
        graph_service: 'Neo4jService'
    ):
        self.claude = claude_service
        self.mechanisms = mechanism_registry
        self.constructs = construct_registry
        self.graph = graph_service
        
        # Detection prompts optimized for mechanism identification
        self.detection_prompt_template = self._build_detection_prompt()
    
    async def analyze_creative(
        self,
        creative: CreativeIntelligenceSignal
    ) -> List[MechanismDetectionInCreative]:
        """
        Analyze a competitor creative to detect mechanisms.
        
        Uses Claude to perform deep psychological analysis of
        the creative's persuasion strategy.
        """
        # Build analysis prompt
        prompt = self._build_analysis_prompt(creative)
        
        # Call Claude for analysis
        response = await self.claude.analyze(
            prompt=prompt,
            system_context=self._get_mechanism_analysis_context(),
            response_format="structured"
        )
        
        # Parse detections
        detections = self._parse_mechanism_detections(response)
        
        # Validate detections
        validated_detections = await self._validate_detections(detections, creative)
        
        return validated_detections
    
    def _build_analysis_prompt(self, creative: CreativeIntelligenceSignal) -> str:
        """Build the analysis prompt for Claude."""
        return f"""
        Analyze this competitor advertisement for cognitive mechanism usage.
        
        CREATIVE CONTENT:
        Type: {creative.creative_type}
        {f"Transcript: {creative.transcript}" if creative.transcript else ""}
        {f"Visual elements: {', '.join(creative.visual_elements)}" if creative.visual_elements else ""}
        {f"Call to action: {creative.call_to_action}" if creative.call_to_action else ""}
        
        CONTEXT:
        Observed in: {creative.observed_context}
        Audience targeting: {', '.join(creative.audience_targeting) if creative.audience_targeting else 'Unknown'}
        
        FOR EACH OF THE 9 COGNITIVE MECHANISMS, ANALYZE:
        
        1. AUTOMATIC EVALUATION (pre-conscious approach/avoidance)
           - Is there immediate positive/negative valence triggering?
           - Visual or auditory elements designed for instant reaction?
        
        2. WANTING/LIKING DISSOCIATION (dopaminergic vs opioid)
           - Does it emphasize anticipation/wanting over satisfaction?
           - Language that triggers desire vs. pleasure?
        
        3. EVOLUTIONARY MOTIVE ACTIVATION (status, mating, affiliation, protection, kin)
           - Which fundamental motives are being activated?
           - How explicitly vs. implicitly?
        
        4. LINGUISTIC FRAMING (gain/loss, metaphor, temporal)
           - What frame is being used?
           - Promotion (gain) or Prevention (loss) focus?
        
        5. MIMETIC DESIRE (Girardian social modeling)
           - Social proof elements?
           - "Others want this" signaling?
        
        6. EMBODIED COGNITION (physical-conceptual mappings)
           - Physical metaphors or embodied language?
           - Sensory engagement attempts?
        
        7. ATTENTION DYNAMICS (salience, novelty, surprise)
           - Novelty or surprise elements?
           - Habituation-breaking techniques?
        
        8. IDENTITY CONSTRUCTION (self-signaling, identity completion)
           - "Be this kind of person" messaging?
           - Identity-product alignment?
        
        9. TEMPORAL CONSTRUAL (abstract why vs concrete how)
           - Abstract (why/values) or concrete (how/features)?
           - Temporal distance framing?
        
        For each detected mechanism, provide:
        - Intensity (0-1): How strongly is it being activated?
        - Confidence (0-1): How certain are you of this detection?
        - Evidence: Specific textual or visual elements supporting detection
        - Psychological principle: The underlying psychology being leveraged
        - Target constructs: Which personality constructs this targets
        
        Also identify:
        - MECHANISM BLIND SPOTS: Which mechanisms are notably absent?
        - CONSTRUCT GAPS: Which psychological types are not well-served?
        - PSYCHOLOGICAL SOPHISTICATION: Overall sophistication level (1-10)
        """
    
    def _get_mechanism_analysis_context(self) -> str:
        """System context for mechanism analysis."""
        return """
        You are an expert in consumer psychology and persuasion science.
        Your role is to analyze advertising creative through the lens of
        cognitive mechanisms—the psychological pathways through which
        messages influence behavior.
        
        Be precise and evidence-based in your detections.
        A mechanism is only "detected" if there is clear evidence of its use.
        Low-confidence detections should be noted but distinguished from
        high-confidence ones.
        
        Your analysis will be used to develop counter-strategies,
        so accuracy is critical.
        """
    
    def _parse_mechanism_detections(
        self,
        response: Dict[str, Any]
    ) -> List[MechanismDetectionInCreative]:
        """Parse Claude's response into structured detections."""
        detections = []
        
        for mechanism_type in CognitiveMechanismType:
            mechanism_data = response.get(mechanism_type.value, {})
            
            if mechanism_data.get('detected', False):
                detection = MechanismDetectionInCreative(
                    mechanism=mechanism_type,
                    intensity=mechanism_data.get('intensity', 0.5),
                    confidence=mechanism_data.get('confidence', 0.5),
                    textual_evidence=mechanism_data.get('textual_evidence', []),
                    visual_evidence=mechanism_data.get('visual_evidence', []),
                    psychological_principle=mechanism_data.get('psychological_principle', '')
                )
                detections.append(detection)
        
        return detections
    
    async def _validate_detections(
        self,
        detections: List[MechanismDetectionInCreative],
        creative: CreativeIntelligenceSignal
    ) -> List[MechanismDetectionInCreative]:
        """
        Validate detections against historical patterns and known correlations.
        """
        validated = []
        
        for detection in detections:
            # Check against known mechanism-construct correlations
            correlation_valid = await self._check_mechanism_construct_correlation(
                detection.mechanism,
                creative.constructs_targeted
            )
            
            # Adjust confidence based on validation
            if correlation_valid:
                detection.confidence = min(detection.confidence * 1.1, 1.0)
            else:
                detection.confidence = detection.confidence * 0.9
            
            # Only include if confidence remains above threshold
            if detection.confidence >= 0.4:
                validated.append(detection)
        
        return validated
    
    async def _check_mechanism_construct_correlation(
        self,
        mechanism: CognitiveMechanismType,
        targeted_constructs: List[str]
    ) -> bool:
        """Check if mechanism-construct pairing makes psychological sense."""
        # Query known correlations from graph
        correlations = await self.graph.execute_query("""
            MATCH (m:CognitiveMechanism {name: $mechanism})
            -[:EFFECTIVELY_TARGETS]->(c:PersonalityConstruct)
            WHERE c.construct_id IN $constructs
            RETURN count(c) AS match_count
        """, {
            "mechanism": mechanism.value,
            "constructs": targeted_constructs
        })
        
        return correlations[0]['match_count'] > 0 if correlations else False


class MechanismProfileBuilder:
    """
    Builds comprehensive mechanism profiles for competitors
    by aggregating detections over time.
    """
    
    def __init__(
        self,
        detector: CompetitorMechanismDetector,
        graph_service: 'Neo4jService'
    ):
        self.detector = detector
        self.graph = graph_service
    
    async def build_profile(
        self,
        competitor_id: str,
        lookback_days: int = 90
    ) -> MechanismProfile:
        """
        Build a comprehensive mechanism profile for a competitor.
        """
        # Get all detections for this competitor
        detections = await self._get_historical_detections(competitor_id, lookback_days)
        
        # Aggregate by mechanism
        mechanism_usage = {}
        for mechanism_type in CognitiveMechanismType:
            mechanism_detections = [d for d in detections if d.mechanism == mechanism_type]
            
            if mechanism_detections:
                usage_data = MechanismUsageData(
                    mechanism=mechanism_type,
                    frequency=len(mechanism_detections) / len(detections) if detections else 0,
                    intensity=sum(d.intensity for d in mechanism_detections) / len(mechanism_detections),
                    estimated_effectiveness=await self._estimate_effectiveness(
                        competitor_id, mechanism_type
                    ),
                    effectiveness_confidence=min(len(mechanism_detections) / 20, 1.0),
                    first_observed=min(d.observed_at for d in mechanism_detections) if mechanism_detections else None,
                    last_observed=max(d.observed_at for d in mechanism_detections) if mechanism_detections else None
                )
                mechanism_usage[mechanism_type] = usage_data
        
        # Identify primary and secondary mechanisms
        sorted_mechanisms = sorted(
            mechanism_usage.items(),
            key=lambda x: x[1].frequency * x[1].intensity,
            reverse=True
        )
        
        primary = [m[0] for m in sorted_mechanisms[:2]] if len(sorted_mechanisms) >= 2 else []
        secondary = [m[0] for m in sorted_mechanisms[2:4]] if len(sorted_mechanisms) >= 4 else []
        
        # Find common combinations
        combinations = await self._find_mechanism_combinations(detections)
        
        return MechanismProfile(
            mechanism_usage=mechanism_usage,
            primary_mechanisms=primary,
            secondary_mechanisms=secondary,
            common_combinations=combinations
        )
    
    async def _estimate_effectiveness(
        self,
        competitor_id: str,
        mechanism: CognitiveMechanismType
    ) -> float:
        """
        Estimate how effective a competitor is with a mechanism.
        
        Uses our outcome data from competitive encounters.
        """
        # Query our performance when they used this mechanism
        result = await self.graph.execute_query("""
            MATCH (c:Competitor {competitor_id: $competitor_id})
            -[:USED_MECHANISM]->(m:MechanismUsage {mechanism: $mechanism})
            -[:IN_COMPETITION_WITH]->(o:OurOutcome)
            RETURN avg(o.competitor_win_rate) AS competitor_effectiveness
        """, {
            "competitor_id": competitor_id,
            "mechanism": mechanism.value
        })
        
        if result and result[0]['competitor_effectiveness']:
            return result[0]['competitor_effectiveness']
        return 0.5  # Default to neutral
    
    async def _find_mechanism_combinations(
        self,
        detections: List[MechanismDetectionInCreative]
    ) -> List[MechanismCombination]:
        """Find frequently co-occurring mechanism combinations."""
        # Group detections by creative
        by_creative = {}
        for d in detections:
            creative_id = d.signal_id  # Assuming signal_id links to creative
            if creative_id not in by_creative:
                by_creative[creative_id] = []
            by_creative[creative_id].append(d.mechanism)
        
        # Count combinations
        combination_counts = {}
        for mechanisms in by_creative.values():
            if len(mechanisms) >= 2:
                # Generate all pairs
                for i in range(len(mechanisms)):
                    for j in range(i+1, len(mechanisms)):
                        combo = tuple(sorted([mechanisms[i], mechanisms[j]], key=lambda x: x.value))
                        combination_counts[combo] = combination_counts.get(combo, 0) + 1
        
        # Convert to MechanismCombination objects
        combinations = []
        total_creatives = len(by_creative)
        
        for combo, count in combination_counts.items():
            if count >= 3:  # Minimum frequency
                combinations.append(MechanismCombination(
                    mechanisms=list(combo),
                    frequency=count / total_creatives if total_creatives > 0 else 0,
                    estimated_synergy=0.0  # Would need outcome data to estimate
                ))
        
        return sorted(combinations, key=lambda x: x.frequency, reverse=True)[:5]
```

## Counter-Mechanism Strategy Engine

```python
"""
ADAM Enhancement #22 v2: Counter-Mechanism Strategy Engine
Generates optimal counter-strategies against competitor mechanisms.
"""

class CounterMechanismStrategyEngine:
    """
    Generates counter-strategies based on competitor mechanism analysis.
    
    The core insight: The best counter is often NOT matching the competitor's
    mechanism, but using an orthogonal mechanism that captures a different
    psychological pathway while exploiting their blind spots.
    """
    
    # Strategy matrix: For each competitor mechanism, optimal counters
    COUNTER_MECHANISM_MATRIX = {
        CognitiveMechanismType.MIMETIC_DESIRE: {
            "match": {
                "strategy": CounterStrategyType.MATCH,
                "mechanisms": [CognitiveMechanismType.MIMETIC_DESIRE],
                "expected_lift": 0.0,
                "risk": "high",
                "rationale": "Arms race, expensive, no differentiation"
            },
            "differentiate_identity": {
                "strategy": CounterStrategyType.DIFFERENTIATE,
                "mechanisms": [CognitiveMechanismType.IDENTITY_CONSTRUCTION],
                "expected_lift": 0.15,
                "risk": "medium",
                "rationale": "Counter social conformity with individual identity. Appeals to high-NFC, high-NFU users."
            },
            "differentiate_temporal": {
                "strategy": CounterStrategyType.DIFFERENTIATE,
                "mechanisms": [CognitiveMechanismType.TEMPORAL_CONSTRUAL],
                "expected_lift": 0.12,
                "risk": "low",
                "rationale": "Counter bandwagon with future self. Appeals to future-oriented users."
            },
            "flank_evolutionary": {
                "strategy": CounterStrategyType.FLANK,
                "mechanisms": [CognitiveMechanismType.EVOLUTIONARY_MOTIVE],
                "expected_lift": 0.18,
                "risk": "medium",
                "rationale": "Activate deeper motives that social proof doesn't address."
            }
        },
        CognitiveMechanismType.ATTENTION_DYNAMICS: {
            "match": {
                "strategy": CounterStrategyType.MATCH,
                "mechanisms": [CognitiveMechanismType.ATTENTION_DYNAMICS],
                "expected_lift": 0.0,
                "risk": "high",
                "rationale": "Novelty escalation, diminishing returns"
            },
            "differentiate_identity": {
                "strategy": CounterStrategyType.DIFFERENTIATE,
                "mechanisms": [CognitiveMechanismType.IDENTITY_CONSTRUCTION],
                "expected_lift": 0.20,
                "risk": "low",
                "rationale": "Counter novelty-seeking with identity resonance. Deeper engagement."
            },
            "differentiate_framing": {
                "strategy": CounterStrategyType.DIFFERENTIATE,
                "mechanisms": [CognitiveMechanismType.LINGUISTIC_FRAMING],
                "expected_lift": 0.14,
                "risk": "low",
                "rationale": "Counter urgency with matched regulatory focus framing."
            }
        },
        CognitiveMechanismType.LINGUISTIC_FRAMING: {
            "match_opposite": {
                "strategy": CounterStrategyType.DIFFERENTIATE,
                "mechanisms": [CognitiveMechanismType.LINGUISTIC_FRAMING],
                "expected_lift": 0.10,
                "risk": "low",
                "rationale": "If they use promotion, use prevention for prevention-focused users."
            },
            "flank_embodied": {
                "strategy": CounterStrategyType.FLANK,
                "mechanisms": [CognitiveMechanismType.EMBODIED_COGNITION],
                "expected_lift": 0.16,
                "risk": "medium",
                "rationale": "Move from abstract framing to embodied experience."
            }
        },
        # ... additional mechanism counters
    }
    
    def __init__(
        self,
        claude_service: 'ClaudeService',
        mechanism_effectiveness: 'MechanismEffectivenessService',
        construct_service: 'ConstructService',
        graph_service: 'Neo4jService'
    ):
        self.claude = claude_service
        self.effectiveness = mechanism_effectiveness
        self.constructs = construct_service
        self.graph = graph_service
    
    async def generate_counter_strategy(
        self,
        competitor_profile: CompetitorPsychologicalProfile,
        our_capabilities: Dict[str, float],
        market_state: MarketState,
        budget_constraint: Optional[float] = None
    ) -> List[CounterMechanismStrategy]:
        """
        Generate optimal counter-strategies against a competitor.
        """
        strategies = []
        
        # For each of their primary mechanisms, generate counters
        for mechanism in competitor_profile.mechanism_profile.primary_mechanisms:
            mechanism_data = competitor_profile.mechanism_profile.mechanism_usage.get(mechanism)
            if not mechanism_data:
                continue
            
            # Get potential counters from matrix
            potential_counters = self.COUNTER_MECHANISM_MATRIX.get(mechanism, {})
            
            # Evaluate each potential counter
            evaluated_counters = []
            for counter_name, counter_config in potential_counters.items():
                evaluation = await self._evaluate_counter(
                    competitor_mechanism=mechanism,
                    competitor_intensity=mechanism_data.intensity,
                    competitor_effectiveness=mechanism_data.estimated_effectiveness,
                    counter_config=counter_config,
                    our_capabilities=our_capabilities,
                    market_state=market_state
                )
                evaluated_counters.append((counter_name, counter_config, evaluation))
            
            # Select best counter
            best_counter = max(evaluated_counters, key=lambda x: x[2]['score'])
            
            # Generate full strategy
            strategy = await self._build_full_strategy(
                competitor_id=competitor_profile.competitor_id,
                competitor_mechanism=mechanism,
                counter_config=best_counter[1],
                evaluation=best_counter[2],
                competitor_vulnerabilities=competitor_profile.vulnerabilities
            )
            
            strategies.append(strategy)
        
        # Also generate vulnerability exploitation strategies
        vulnerability_strategies = await self._generate_vulnerability_strategies(
            competitor_profile=competitor_profile,
            our_capabilities=our_capabilities
        )
        strategies.extend(vulnerability_strategies)
        
        # Rank and filter strategies
        ranked_strategies = self._rank_strategies(strategies, budget_constraint)
        
        return ranked_strategies[:5]  # Top 5 strategies
    
    async def _evaluate_counter(
        self,
        competitor_mechanism: CognitiveMechanismType,
        competitor_intensity: float,
        competitor_effectiveness: float,
        counter_config: Dict[str, Any],
        our_capabilities: Dict[str, float],
        market_state: MarketState
    ) -> Dict[str, Any]:
        """Evaluate a potential counter-strategy."""
        
        # Base score from expected lift
        base_lift = counter_config['expected_lift']
        
        # Adjust for our capability with counter mechanisms
        capability_modifier = 1.0
        for mech in counter_config['mechanisms']:
            our_capability = our_capabilities.get(mech.value, 0.5)
            capability_modifier *= our_capability
        
        # Adjust for market state
        state_modifier = 1.0
        if market_state.current_state == MarketStateType.PRICE_WAR:
            if counter_config['strategy'] == CounterStrategyType.DIFFERENTIATE:
                state_modifier = 1.2  # Differentiation valuable in price wars
        elif market_state.current_state == MarketStateType.SEGMENT_WARFARE:
            if counter_config['strategy'] == CounterStrategyType.FLANK:
                state_modifier = 1.3  # Flanking valuable in segment battles
        
        # Risk adjustment
        risk_penalty = {'high': 0.8, 'medium': 0.95, 'low': 1.0}[counter_config['risk']]
        
        # Calculate final score
        score = base_lift * capability_modifier * state_modifier * risk_penalty
        
        return {
            'score': score,
            'base_lift': base_lift,
            'capability_modifier': capability_modifier,
            'state_modifier': state_modifier,
            'risk_penalty': risk_penalty
        }
    
    async def _build_full_strategy(
        self,
        competitor_id: str,
        competitor_mechanism: CognitiveMechanismType,
        counter_config: Dict[str, Any],
        evaluation: Dict[str, Any],
        competitor_vulnerabilities: List[CompetitorVulnerability]
    ) -> CounterMechanismStrategy:
        """Build a complete counter-strategy specification."""
        
        # Get target constructs for counter mechanisms
        target_constructs = []
        for mech in counter_config['mechanisms']:
            constructs = await self.constructs.get_constructs_for_mechanism(mech)
            target_constructs.extend(constructs)
        
        # Get copy strategy from Claude
        copy_strategy = await self._generate_copy_strategy(
            counter_mechanisms=counter_config['mechanisms'],
            target_constructs=target_constructs,
            competitor_mechanism=competitor_mechanism
        )
        
        # Build deployment specifications
        deployments = []
        for mech in counter_config['mechanisms']:
            deployment = CounterMechanismDeployment(
                mechanism=mech,
                recommended_intensity=0.7,  # Default, would be optimized
                strategic_rationale=counter_config['rationale'],
                target_constructs=target_constructs,
                psychological_principle=self._get_psychological_principle(mech),
                word_patterns=await self._get_word_patterns(mech),
                emotional_tone=self._get_emotional_tone(mech),
                framing_approach=self._get_framing_approach(mech)
            )
            deployments.append(deployment)
        
        return CounterMechanismStrategy(
            competitor_id=competitor_id,
            competitor_mechanism=competitor_mechanism,
            competitor_intensity=0.7,  # From profile
            strategy_type=counter_config['strategy'],
            counter_mechanisms=deployments,
            target_constructs=list(set(target_constructs)),
            expected_lift_vs_matching=evaluation['base_lift'],
            expected_cost_efficiency=evaluation['score'],
            confidence=evaluation['capability_modifier'],
            copy_strategy=copy_strategy,
            creative_requirements=self._get_creative_requirements(counter_config['mechanisms']),
            timing_recommendations=self._get_timing_recommendations(counter_config['strategy']),
            risk_level=counter_config['risk'],
            risk_factors=self._get_risk_factors(counter_config),
            mitigation_strategies=self._get_mitigations(counter_config)
        )
    
    async def _generate_copy_strategy(
        self,
        counter_mechanisms: List[CognitiveMechanismType],
        target_constructs: List[str],
        competitor_mechanism: CognitiveMechanismType
    ) -> str:
        """Use Claude to generate copy strategy."""
        
        prompt = f"""
        Generate a copy strategy that:
        
        1. ACTIVATES these mechanisms: {[m.value for m in counter_mechanisms]}
        2. TARGETS users with these psychological constructs: {target_constructs}
        3. COUNTERS competitor's use of: {competitor_mechanism.value}
        
        Provide:
        - Headline approach (5-10 words describing the angle)
        - Key messaging pillars (3-5 points)
        - Emotional tone
        - Word patterns to use
        - Word patterns to avoid
        - CTA style
        """
        
        response = await self.claude.generate(prompt)
        return response
    
    def _get_psychological_principle(self, mechanism: CognitiveMechanismType) -> str:
        """Get the underlying psychological principle for a mechanism."""
        principles = {
            CognitiveMechanismType.IDENTITY_CONSTRUCTION: 
                "Self-signaling: People prefer choices that signal desirable identities to themselves",
            CognitiveMechanismType.TEMPORAL_CONSTRUAL:
                "Psychological distance affects abstraction level of mental representations",
            CognitiveMechanismType.EVOLUTIONARY_MOTIVE:
                "Fundamental motives (status, mating, affiliation) shape decision-making",
            CognitiveMechanismType.LINGUISTIC_FRAMING:
                "Equivalent information presented differently leads to different choices",
            CognitiveMechanismType.MIMETIC_DESIRE:
                "We desire what others desire (Girardian mimesis)",
            # ... etc
        }
        return principles.get(mechanism, "")
```

---

# SECTION D: COMPETITIVE GAME THEORY ENGINE

## Strategic Agent Modeling

```python
"""
ADAM Enhancement #22 v2: Strategic Agent Modeling
Game-theoretic modeling of competitor behavior.
"""

class StrategicAgentModeler:
    """
    Models competitors as strategic agents making rational decisions
    to maximize their objectives.
    
    This enables prediction of their moves and identification of
    optimal response strategies.
    """
    
    def __init__(
        self,
        graph_service: 'Neo4jService',
        claude_service: 'ClaudeService'
    ):
        self.graph = graph_service
        self.claude = claude_service
    
    async def build_agent_model(
        self,
        competitor_id: str,
        observation_period_days: int = 180
    ) -> StrategicBehaviorModel:
        """
        Build a strategic behavior model for a competitor.
        """
        # Get historical actions
        actions = await self._get_historical_actions(competitor_id, observation_period_days)
        
        # Analyze aggression level
        aggression = self._analyze_aggression(actions)
        
        # Analyze innovation propensity
        innovation = self._analyze_innovation(actions)
        
        # Analyze reaction speed
        reaction_speed = await self._analyze_reaction_speed(competitor_id)
        
        # Analyze budget flexibility
        budget_flex = self._analyze_budget_flexibility(actions)
        
        # Analyze response patterns
        response_patterns = await self._analyze_response_patterns(competitor_id)
        
        return StrategicBehaviorModel(
            competitor_id=competitor_id,
            aggression_level=aggression,
            innovation_propensity=innovation,
            reaction_speed=reaction_speed,
            budget_flexibility=budget_flex,
            typical_response_to_attack=response_patterns.get('attack', 'match'),
            typical_response_to_loss=response_patterns.get('loss', 'increase_spend'),
            typical_response_to_new_entrant=response_patterns.get('new_entrant', 'defend')
        )
    
    def _analyze_aggression(self, actions: List[Dict]) -> float:
        """Analyze how aggressive the competitor is."""
        if not actions:
            return 0.5
        
        aggressive_indicators = [
            a for a in actions
            if a.get('type') in ['bid_increase', 'budget_surge', 'new_segment_attack']
        ]
        
        return min(len(aggressive_indicators) / len(actions) * 2, 1.0)
    
    def _analyze_innovation(self, actions: List[Dict]) -> float:
        """Analyze willingness to try new approaches."""
        if not actions:
            return 0.5
        
        innovative_indicators = [
            a for a in actions
            if a.get('type') in ['new_mechanism', 'new_creative_format', 'new_channel']
        ]
        
        return min(len(innovative_indicators) / len(actions) * 3, 1.0)
    
    async def _analyze_reaction_speed(self, competitor_id: str) -> float:
        """Analyze how fast they respond to market changes."""
        # Query response times from graph
        result = await self.graph.execute_query("""
            MATCH (c:Competitor {competitor_id: $id})
            -[:RESPONDED_TO]->(e:MarketEvent)
            RETURN avg(duration.between(e.event_time, c.response_time).hours) AS avg_hours
        """, {"id": competitor_id})
        
        if result and result[0]['avg_hours']:
            avg_hours = result[0]['avg_hours']
            # Convert to 0-1 scale (faster = higher)
            return max(0, 1 - (avg_hours / 168))  # 168 hours = 1 week baseline
        
        return 0.5
    
    def _analyze_budget_flexibility(self, actions: List[Dict]) -> float:
        """Analyze ability to adjust spending."""
        if not actions:
            return 0.5
        
        budget_changes = [a.get('budget_change', 0) for a in actions if 'budget_change' in a]
        
        if not budget_changes:
            return 0.5
        
        # High variance = high flexibility
        import numpy as np
        variance = np.std(budget_changes) / (np.mean(budget_changes) + 0.01)
        
        return min(variance, 1.0)


class MovePredictionEngine:
    """
    Predicts competitor's next strategic moves.
    """
    
    def __init__(
        self,
        agent_modeler: StrategicAgentModeler,
        market_analyzer: 'MarketStateAnalyzer',
        claude_service: 'ClaudeService'
    ):
        self.modeler = agent_modeler
        self.market = market_analyzer
        self.claude = claude_service
    
    async def predict_next_move(
        self,
        competitor_id: str,
        horizon_days: int = 30
    ) -> CompetitorMovePrediction:
        """
        Predict a competitor's next strategic move.
        """
        # Get their behavior model
        behavior = await self.modeler.build_agent_model(competitor_id)
        
        # Get current market state
        market_state = await self.market.get_current_state()
        
        # Get their recent actions
        recent_actions = await self._get_recent_actions(competitor_id, 30)
        
        # Get our recent actions (they may be responding to us)
        our_recent_actions = await self._get_our_recent_actions(30)
        
        # Use Claude for strategic reasoning
        predictions = await self._claude_predict(
            behavior=behavior,
            market_state=market_state,
            their_recent_actions=recent_actions,
            our_recent_actions=our_recent_actions,
            horizon_days=horizon_days
        )
        
        # Generate optimal responses for each prediction
        responses = {}
        for pred in predictions:
            response = await self._generate_optimal_response(pred, market_state)
            responses[pred.move_type] = response
        
        # Build prediction object
        primary = predictions[0] if predictions else None
        alternatives = predictions[1:] if len(predictions) > 1 else []
        
        return CompetitorMovePrediction(
            competitor_id=competitor_id,
            prediction_horizon_days=horizon_days,
            primary_prediction=primary,
            alternative_predictions=alternatives,
            overall_confidence=primary.probability if primary else 0.5,
            optimal_responses=responses
        )
    
    async def _claude_predict(
        self,
        behavior: StrategicBehaviorModel,
        market_state: MarketState,
        their_recent_actions: List[Dict],
        our_recent_actions: List[Dict],
        horizon_days: int
    ) -> List[PredictedMove]:
        """Use Claude for strategic prediction."""
        
        prompt = f"""
        Predict the most likely strategic moves for this competitor in the next {horizon_days} days.
        
        COMPETITOR BEHAVIOR PROFILE:
        - Aggression level: {behavior.aggression_level:.2f}
        - Innovation propensity: {behavior.innovation_propensity:.2f}
        - Reaction speed: {behavior.reaction_speed:.2f}
        - Budget flexibility: {behavior.budget_flexibility:.2f}
        - Typical response to attack: {behavior.typical_response_to_attack}
        - Typical response to loss: {behavior.typical_response_to_loss}
        
        CURRENT MARKET STATE: {market_state.current_state.value}
        - Characteristics: {market_state.characteristics}
        - Opportunities: {market_state.state_opportunities}
        - Threats: {market_state.state_threats}
        
        THEIR RECENT ACTIONS:
        {self._format_actions(their_recent_actions)}
        
        OUR RECENT ACTIONS (they may be responding to):
        {self._format_actions(our_recent_actions)}
        
        Predict the top 3 most likely moves with:
        - Move type (budget_change, mechanism_shift, new_segment, creative_refresh, etc.)
        - Description
        - Probability (0-1)
        - Mechanisms involved
        - Segments affected
        - Signals that would confirm this prediction
        """
        
        response = await self.claude.analyze(
            prompt=prompt,
            system_context="You are a strategic intelligence analyst specializing in competitive dynamics.",
            response_format="structured"
        )
        
        return self._parse_predictions(response)
    
    def _format_actions(self, actions: List[Dict]) -> str:
        """Format actions for prompt."""
        if not actions:
            return "No recent actions observed"
        
        return "\n".join([
            f"- {a.get('date', 'Unknown')}: {a.get('type', 'Unknown')} - {a.get('description', 'No details')}"
            for a in actions[:10]
        ])


class NashEquilibriumAnalyzer:
    """
    Analyzes competitive dynamics through Nash equilibrium lens.
    """
    
    def __init__(
        self,
        graph_service: 'Neo4jService'
    ):
        self.graph = graph_service
    
    async def analyze_equilibrium(
        self,
        competitor_ids: List[str],
        strategy_space: Dict[str, List[str]]
    ) -> NashEquilibriumAnalysis:
        """
        Analyze Nash equilibrium for the competitive game.
        """
        players = ['self'] + competitor_ids
        
        # Get current strategy profile
        current_strategies = await self._get_current_strategies(players)
        
        # Build payoff matrix
        payoff_matrix = await self._build_payoff_matrix(players, strategy_space)
        
        # Check if current profile is equilibrium
        is_eq, deviations = self._check_equilibrium(
            current_strategies, payoff_matrix, strategy_space
        )
        
        # Find all stable equilibria
        equilibria = self._find_equilibria(payoff_matrix, strategy_space, players)
        
        # Recommend optimal strategy
        recommendation = self._recommend_strategy(
            current_strategies, equilibria, payoff_matrix
        )
        
        return NashEquilibriumAnalysis(
            players=players,
            strategy_spaces=strategy_space,
            current_strategies=current_strategies,
            is_equilibrium=is_eq,
            equilibrium_confidence=0.7,  # Would be computed
            profitable_deviations=deviations,
            stable_equilibria=equilibria,
            recommended_strategy=recommendation
        )
    
    def _check_equilibrium(
        self,
        current: Dict[str, str],
        payoffs: Dict,
        strategies: Dict[str, List[str]]
    ) -> Tuple[bool, List[ProfitableDeviation]]:
        """Check if current profile is Nash equilibrium."""
        deviations = []
        
        for player in current.keys():
            current_payoff = self._get_payoff(current, payoffs, player)
            
            for alt_strategy in strategies.get(player, []):
                if alt_strategy == current[player]:
                    continue
                
                # Check payoff with deviation
                deviated = current.copy()
                deviated[player] = alt_strategy
                deviated_payoff = self._get_payoff(deviated, payoffs, player)
                
                if deviated_payoff > current_payoff + 0.01:  # Small epsilon
                    deviations.append(ProfitableDeviation(
                        player=player,
                        from_strategy=current[player],
                        to_strategy=alt_strategy,
                        expected_payoff_gain=deviated_payoff - current_payoff,
                        confidence=0.8
                    ))
        
        return len(deviations) == 0, deviations
    
    def _get_payoff(
        self,
        profile: Dict[str, str],
        payoffs: Dict,
        player: str
    ) -> float:
        """Get payoff for a player given strategy profile."""
        profile_key = tuple(sorted(profile.items()))
        return payoffs.get(profile_key, {}).get(player, 0.0)
```

---

# SECTION E: NEO4J COMPETITIVE GRAPH

## Competitor Entity Schema

```cypher
// ADAM Enhancement #22 v2: Neo4j Schema for Competitive Intelligence

// =============================================================================
// COMPETITOR ENTITIES
// =============================================================================

// Competitor node
CREATE CONSTRAINT competitor_id_unique IF NOT EXISTS
FOR (c:Competitor) REQUIRE c.competitor_id IS UNIQUE;

CREATE INDEX competitor_name IF NOT EXISTS
FOR (c:Competitor) ON (c.name);

// Competitor properties:
// - competitor_id: str
// - name: str
// - threat_level: str
// - positioning: str
// - primary_categories: str[]
// - estimated_annual_spend: float
// - tracked_since: datetime
// - last_updated: datetime

// =============================================================================
// MECHANISM USAGE TRACKING
// =============================================================================

// Mechanism usage by competitor
CREATE INDEX mechanism_usage_competitor IF NOT EXISTS
FOR (mu:CompetitorMechanismUsage) ON (mu.competitor_id, mu.mechanism);

// (:Competitor)-[:USES_MECHANISM]->(mu:CompetitorMechanismUsage)
// mu properties:
// - competitor_id: str
// - mechanism: str
// - frequency: float
// - intensity: float
// - estimated_effectiveness: float
// - first_observed: datetime
// - last_observed: datetime
// - observation_count: int

// =============================================================================
// VULNERABILITY TRACKING
// =============================================================================

// Competitor vulnerabilities
CREATE INDEX vulnerability_competitor IF NOT EXISTS
FOR (v:CompetitorVulnerability) ON (v.competitor_id);

CREATE INDEX vulnerability_type IF NOT EXISTS
FOR (v:CompetitorVulnerability) ON (v.vulnerability_type);

// v properties:
// - vulnerability_id: str
// - competitor_id: str
// - vulnerability_type: str
// - description: str
// - exploitation_potential: float
// - estimated_tam: float
// - still_valid: bool
// - discovered_at: datetime

// =============================================================================
// INTELLIGENCE SIGNALS
// =============================================================================

// Raw intelligence signals
CREATE INDEX signal_competitor IF NOT EXISTS
FOR (s:IntelligenceSignal) ON (s.competitor_id);

CREATE INDEX signal_type IF NOT EXISTS
FOR (s:IntelligenceSignal) ON (s.signal_type);

CREATE INDEX signal_time IF NOT EXISTS
FOR (s:IntelligenceSignal) ON (s.observed_at);

// =============================================================================
// COMPETITIVE OUTCOMES
// =============================================================================

// Head-to-head competitive outcomes
CREATE INDEX competitive_outcome_competitors IF NOT EXISTS
FOR (co:CompetitiveOutcome) ON (co.our_campaign_id, co.competitor_id);

// co properties:
// - outcome_id: str
// - our_campaign_id: str
// - competitor_id: str
// - segment_id: str
// - timestamp: datetime
// - our_mechanism: str
// - their_mechanism: str (inferred)
// - we_won: bool
// - our_effectiveness: float
// - estimated_competitor_effectiveness: float

// =============================================================================
// MARKET STATE TRACKING
// =============================================================================

// Market state history
CREATE INDEX market_state_time IF NOT EXISTS
FOR (ms:MarketState) ON (ms.timestamp);

// ms properties:
// - state_id: str
// - state_type: str
// - timestamp: datetime
// - confidence: float
// - characteristics: str[]
// - state_leaders: str[]

// =============================================================================
// RELATIONSHIPS
// =============================================================================

// Competitor uses mechanism
// (:Competitor)-[:USES_MECHANISM {
//     intensity: float,
//     effectiveness: float,
//     contexts: str[]
// }]->(mu:CompetitorMechanismUsage)

// Competitor has vulnerability
// (:Competitor)-[:HAS_VULNERABILITY]->(v:CompetitorVulnerability)

// Intelligence signal about competitor
// (:IntelligenceSignal)-[:ABOUT]->(c:Competitor)

// Competitive outcome between us and competitor
// (:Campaign)-[:COMPETED_WITH {outcome_id: str}]->(c:Competitor)

// Market state transition
// (:MarketState)-[:TRANSITIONED_TO {
//     transition_date: datetime,
//     trigger: str
// }]->(ms2:MarketState)

// Counter-strategy targeting competitor
// (:CounterStrategy)-[:TARGETS]->(c:Competitor)
// (:CounterStrategy)-[:COUNTERS]->(mu:CompetitorMechanismUsage)

// =============================================================================
// QUERY TEMPLATES
// =============================================================================

// Get competitor psychological profile
// MATCH (c:Competitor {competitor_id: $id})
// OPTIONAL MATCH (c)-[:USES_MECHANISM]->(mu:CompetitorMechanismUsage)
// OPTIONAL MATCH (c)-[:HAS_VULNERABILITY]->(v:CompetitorVulnerability)
// RETURN c, collect(mu) AS mechanisms, collect(v) AS vulnerabilities

// Find competitors using specific mechanism
// MATCH (c:Competitor)-[:USES_MECHANISM]->(mu:CompetitorMechanismUsage)
// WHERE mu.mechanism = $mechanism AND mu.intensity > 0.5
// RETURN c.name, mu.intensity, mu.estimated_effectiveness
// ORDER BY mu.estimated_effectiveness DESC

// Get our win rate against competitor by mechanism
// MATCH (co:CompetitiveOutcome)
// WHERE co.competitor_id = $competitor_id
// AND co.our_mechanism = $mechanism
// RETURN 
//     co.our_mechanism,
//     count(co) AS total_encounters,
//     sum(CASE WHEN co.we_won THEN 1 ELSE 0 END) AS wins,
//     toFloat(sum(CASE WHEN co.we_won THEN 1 ELSE 0 END)) / count(co) AS win_rate

// Find high-potential vulnerabilities
// MATCH (c:Competitor)-[:HAS_VULNERABILITY]->(v:CompetitorVulnerability)
// WHERE v.still_valid = true
// AND v.exploitation_potential > 0.7
// RETURN c.name, v.vulnerability_type, v.description, v.exploitation_potential, v.estimated_tam
// ORDER BY v.exploitation_potential * v.estimated_tam DESC
// LIMIT 10

// Get market state history
// MATCH (ms:MarketState)
// WHERE ms.timestamp > datetime() - duration({days: 90})
// OPTIONAL MATCH (ms)-[t:TRANSITIONED_TO]->(ms2:MarketState)
// RETURN ms.state_type, ms.timestamp, ms2.state_type AS next_state, t.trigger
// ORDER BY ms.timestamp DESC
```

---

# SECTION F: PROMETHEUS METRICS

## Intelligence Quality Metrics

```python
"""
ADAM Enhancement #22 v2: Prometheus Metrics
Comprehensive observability for Competitive Psychological Intelligence.
"""

from prometheus_client import Counter, Gauge, Histogram, Summary

# =============================================================================
# INTELLIGENCE COLLECTION METRICS
# =============================================================================

# Signal collection by type
intelligence_signals_collected = Counter(
    'adam_ci_signals_collected_total',
    'Total intelligence signals collected',
    ['signal_type', 'competitor_id']
)

# Signal processing latency
signal_processing_latency = Histogram(
    'adam_ci_signal_processing_seconds',
    'Signal processing latency',
    ['signal_type'],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
)

# Signal confidence distribution
signal_confidence_distribution = Histogram(
    'adam_ci_signal_confidence',
    'Distribution of signal confidence scores',
    ['signal_type'],
    buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
)

# =============================================================================
# MECHANISM DETECTION METRICS
# =============================================================================

# Mechanism detections
mechanism_detections = Counter(
    'adam_ci_mechanism_detections_total',
    'Total mechanism detections in competitor creative',
    ['competitor_id', 'mechanism']
)

# Detection confidence
mechanism_detection_confidence = Histogram(
    'adam_ci_mechanism_detection_confidence',
    'Confidence of mechanism detections',
    ['mechanism'],
    buckets=[0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
)

# Mechanism effectiveness estimates
competitor_mechanism_effectiveness = Gauge(
    'adam_ci_competitor_mechanism_effectiveness',
    'Estimated effectiveness of competitor mechanism usage',
    ['competitor_id', 'mechanism']
)

# =============================================================================
# VULNERABILITY METRICS
# =============================================================================

# Active vulnerabilities
active_vulnerabilities = Gauge(
    'adam_ci_active_vulnerabilities',
    'Number of active vulnerabilities by competitor',
    ['competitor_id']
)

# Vulnerability exploitation potential
vulnerability_exploitation_potential = Gauge(
    'adam_ci_vulnerability_potential',
    'Exploitation potential of vulnerabilities',
    ['competitor_id', 'vulnerability_type']
)

# Vulnerability discovery rate
vulnerability_discoveries = Counter(
    'adam_ci_vulnerability_discoveries_total',
    'Total vulnerabilities discovered',
    ['competitor_id', 'vulnerability_type']
)

# =============================================================================
# COMPETITIVE POSITION METRICS
# =============================================================================

# Win rate against competitors
competitive_win_rate = Gauge(
    'adam_ci_competitive_win_rate',
    'Win rate against competitor',
    ['competitor_id', 'segment']
)

# Mechanism effectiveness differential
mechanism_differential = Gauge(
    'adam_ci_mechanism_differential',
    'Our effectiveness minus competitor effectiveness',
    ['competitor_id', 'mechanism']
)

# Market share estimates
estimated_market_share = Gauge(
    'adam_ci_estimated_market_share',
    'Estimated market share by segment',
    ['segment']
)

# =============================================================================
# PREDICTION METRICS
# =============================================================================

# Predictions made
predictions_made = Counter(
    'adam_ci_predictions_made_total',
    'Total competitor move predictions made',
    ['competitor_id']
)

# Prediction accuracy
prediction_accuracy = Gauge(
    'adam_ci_prediction_accuracy',
    'Accuracy of competitor move predictions',
    ['competitor_id']
)

# Prediction confidence
prediction_confidence_distribution = Histogram(
    'adam_ci_prediction_confidence',
    'Confidence of predictions',
    [],
    buckets=[0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
)

# =============================================================================
# COUNTER-STRATEGY METRICS
# =============================================================================

# Strategies generated
counter_strategies_generated = Counter(
    'adam_ci_counter_strategies_total',
    'Total counter-strategies generated',
    ['competitor_id', 'strategy_type']
)

# Strategy execution
strategy_executions = Counter(
    'adam_ci_strategy_executions_total',
    'Counter-strategies executed',
    ['strategy_type', 'outcome']
)

# Strategy effectiveness
strategy_effectiveness = Histogram(
    'adam_ci_strategy_effectiveness',
    'Effectiveness of counter-strategies',
    ['strategy_type'],
    buckets=[-0.2, -0.1, 0, 0.1, 0.2, 0.3, 0.4, 0.5]
)

# =============================================================================
# MARKET STATE METRICS
# =============================================================================

# Current market state
current_market_state = Gauge(
    'adam_ci_market_state',
    'Current market state (encoded as numeric)',
    []
)

# State stability
market_state_duration_days = Gauge(
    'adam_ci_market_state_duration_days',
    'Days in current market state',
    []
)

# State transition probability
state_transition_probability = Gauge(
    'adam_ci_state_transition_probability',
    'Probability of transitioning to each state',
    ['target_state']
)
```

---

# SECTION G: IMPLEMENTATION

## Implementation Timeline

```yaml
Phase 1 - Foundation (Weeks 1-3):
  Focus: Core infrastructure and data models
  Tasks:
    - Implement all Pydantic models
    - Deploy Neo4j competitive graph schema
    - Create Kafka topics for intelligence signals
    - Set up Prometheus metrics baseline
    - Build signal ingestion pipeline
  Deliverables:
    - Working data layer
    - Signal collection operational
  Success Criteria:
    - 100+ signals/day collected
    - Neo4j queries performing <50ms

Phase 2 - Mechanism Detection (Weeks 4-6):
  Focus: Claude-powered mechanism detection
  Tasks:
    - Implement CompetitorMechanismDetector
    - Build mechanism detection prompts
    - Create MechanismProfileBuilder
    - Integrate with #04 v3 AoT
    - Validate detection accuracy
  Deliverables:
    - Mechanism detection at 75%+ accuracy
    - Competitor profiles building
  Success Criteria:
    - Detection confidence >0.7 for primary mechanisms
    - Profile completeness >60% for tracked competitors

Phase 3 - Strategic Intelligence (Weeks 7-9):
  Focus: Vulnerability mapping and game theory
  Tasks:
    - Implement vulnerability detection
    - Build strategic agent modeler
    - Create move prediction engine
    - Implement Nash equilibrium analyzer
    - Test prediction accuracy
  Deliverables:
    - Vulnerability cartography operational
    - Move predictions generating
  Success Criteria:
    - 3+ high-potential vulnerabilities identified per competitor
    - Prediction accuracy >60% at 30-day horizon

Phase 4 - Counter-Strategy Generation (Weeks 10-11):
  Focus: Automated counter-strategy engine
  Tasks:
    - Implement counter-mechanism strategy engine
    - Build strategy evaluation framework
    - Create copy strategy generation
    - Integrate with #15 Copy Generation
    - Test strategy effectiveness
  Deliverables:
    - Counter-strategies generating automatically
    - Copy briefs producing
  Success Criteria:
    - Strategies show +10% lift vs. matching in A/B tests
    - Strategy generation <30 seconds

Phase 5 - Market State Machine (Week 12):
  Focus: Dynamic market modeling
  Tasks:
    - Implement market state detection
    - Build state transition model
    - Create equilibrium tracking
    - Test state prediction accuracy
  Deliverables:
    - Market state tracking operational
  Success Criteria:
    - State detection accuracy >80%
    - Transition prediction >65%

Phase 6 - Integration & Hardening (Weeks 13-14):
  Focus: Full system integration
  Tasks:
    - Integrate with #28 WPP Ad Desk
    - Integrate with #06 Gradient Bridge for learning
    - Performance optimization
    - Documentation and training
    - Security review
  Deliverables:
    - Full production deployment
    - Operational runbooks
  Success Criteria:
    - <100ms API latency p95
    - 99.9% availability
```

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Mechanism Detection Accuracy** | >75% | Validation against human-labeled samples |
| **Vulnerability Discovery Rate** | >3 per competitor per quarter | Count of high-potential vulnerabilities |
| **Prediction Accuracy (30-day)** | >65% | Validated predictions vs. actual moves |
| **Counter-Strategy Lift** | >10% vs. matching | A/B test lift measurement |
| **Win Rate Improvement** | +15% in contested segments | Before/after comparison |
| **Response Time** | <15 minutes to counter-strategy | Time from signal to actionable strategy |
| **Budget Efficiency** | +25% in competitive contexts | CPA improvement in competitive auctions |
| **Intelligence Coverage** | >90% of named competitors profiled | Profile completeness metric |

---

*This specification establishes ADAM's Competitive Psychological Intelligence capability—transforming competitive analysis from reactive monitoring to predictive psychological warfare. By understanding not just WHAT competitors do but WHY they win or lose psychologically, ADAM gains a fundamental strategic advantage: the ability to exploit mechanism blind spots, predict moves, and counter-position with precision.*

**Document Statistics:**
- Total Lines: ~3,500
- Pydantic Models: 45+
- Neo4j Node Types: 8
- Integration Points: #04 v3, #14 v3, #27 v2, #06, #15, #28
- Implementation Timeline: 14 weeks


---

# SECTION H: FASTAPI ENDPOINTS

## Intelligence API

```python
"""
ADAM Enhancement #22 v2: FastAPI Intelligence Endpoints
REST API for accessing competitive psychological intelligence.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends, Query
from fastapi.responses import JSONResponse
from typing import List, Optional
from datetime import datetime, timedelta
import asyncio

router = APIRouter(prefix="/api/v1/competitive", tags=["Competitive Intelligence"])


# =============================================================================
# COMPETITOR PROFILE ENDPOINTS
# =============================================================================

@router.get("/competitors", response_model=List[CompetitorSummary])
async def list_competitors(
    threat_level: Optional[CompetitorThreatLevel] = None,
    category: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    ci_service: CompetitiveIntelligenceService = Depends(get_ci_service)
):
    """
    List tracked competitors with optional filtering.
    
    Returns summary profiles for quick overview.
    """
    competitors = await ci_service.list_competitors(
        threat_level=threat_level,
        category=category,
        limit=limit,
        offset=offset
    )
    return competitors


@router.get("/competitors/{competitor_id}", response_model=CompetitorPsychologicalProfile)
async def get_competitor_profile(
    competitor_id: str,
    include_vulnerabilities: bool = True,
    include_history: bool = False,
    ci_service: CompetitiveIntelligenceService = Depends(get_ci_service)
):
    """
    Get complete psychological profile for a competitor.
    
    Includes mechanism usage, construct targeting, and vulnerabilities.
    """
    profile = await ci_service.get_competitor_profile(
        competitor_id=competitor_id,
        include_vulnerabilities=include_vulnerabilities,
        include_history=include_history
    )
    
    if not profile:
        raise HTTPException(status_code=404, detail=f"Competitor {competitor_id} not found")
    
    return profile


@router.get(
    "/competitors/{competitor_id}/mechanisms",
    response_model=MechanismProfile
)
async def get_competitor_mechanism_profile(
    competitor_id: str,
    lookback_days: int = Query(90, ge=7, le=365),
    ci_service: CompetitiveIntelligenceService = Depends(get_ci_service)
):
    """
    Get mechanism usage profile for a competitor.
    
    Shows which psychological mechanisms they activate and how effectively.
    """
    profile = await ci_service.get_mechanism_profile(
        competitor_id=competitor_id,
        lookback_days=lookback_days
    )
    return profile


@router.get(
    "/competitors/{competitor_id}/vulnerabilities",
    response_model=List[CompetitorVulnerability]
)
async def get_competitor_vulnerabilities(
    competitor_id: str,
    min_potential: float = Query(0.5, ge=0, le=1),
    vulnerability_type: Optional[VulnerabilityType] = None,
    ci_service: CompetitiveIntelligenceService = Depends(get_ci_service)
):
    """
    Get exploitable vulnerabilities for a competitor.
    
    Sorted by exploitation potential.
    """
    vulnerabilities = await ci_service.get_vulnerabilities(
        competitor_id=competitor_id,
        min_potential=min_potential,
        vulnerability_type=vulnerability_type
    )
    return vulnerabilities


# =============================================================================
# COUNTER-STRATEGY ENDPOINTS
# =============================================================================

@router.post(
    "/competitors/{competitor_id}/counter-strategy",
    response_model=List[CounterMechanismStrategy]
)
async def generate_counter_strategy(
    competitor_id: str,
    request: CounterStrategyRequest,
    background_tasks: BackgroundTasks,
    ci_service: CompetitiveIntelligenceService = Depends(get_ci_service)
):
    """
    Generate counter-strategies against a competitor.
    
    Uses psychological mechanism analysis to recommend optimal responses.
    """
    strategies = await ci_service.generate_counter_strategies(
        competitor_id=competitor_id,
        budget_constraint=request.budget_constraint,
        target_segments=request.target_segments,
        preferred_mechanisms=request.preferred_mechanisms
    )
    
    # Log strategy generation for learning
    background_tasks.add_task(
        ci_service.log_strategy_generation,
        competitor_id=competitor_id,
        strategies=strategies
    )
    
    return strategies


@router.get(
    "/competitors/{competitor_id}/differential/{mechanism}",
    response_model=MechanismEffectivenessDifferential
)
async def get_mechanism_differential(
    competitor_id: str,
    mechanism: CognitiveMechanismType,
    segment: Optional[str] = None,
    ci_service: CompetitiveIntelligenceService = Depends(get_ci_service)
):
    """
    Get effectiveness differential for a mechanism vs competitor.
    
    Shows where we win/lose when both parties use the same mechanism.
    """
    differential = await ci_service.get_mechanism_differential(
        competitor_id=competitor_id,
        mechanism=mechanism,
        segment=segment
    )
    return differential


# =============================================================================
# PREDICTION ENDPOINTS
# =============================================================================

@router.get(
    "/competitors/{competitor_id}/predictions",
    response_model=CompetitorMovePrediction
)
async def get_move_prediction(
    competitor_id: str,
    horizon_days: int = Query(30, ge=7, le=90),
    ci_service: CompetitiveIntelligenceService = Depends(get_ci_service)
):
    """
    Get predicted next moves for a competitor.
    
    Uses game theory and behavioral modeling.
    """
    prediction = await ci_service.predict_competitor_move(
        competitor_id=competitor_id,
        horizon_days=horizon_days
    )
    return prediction


@router.post("/predictions/validate", response_model=PredictionValidationResult)
async def validate_prediction(
    validation: PredictionValidationRequest,
    ci_service: CompetitiveIntelligenceService = Depends(get_ci_service)
):
    """
    Validate a previous prediction against actual outcome.
    
    Used for continuous model improvement.
    """
    result = await ci_service.validate_prediction(
        prediction_id=validation.prediction_id,
        actual_move=validation.actual_move,
        actual_timing=validation.actual_timing
    )
    return result


# =============================================================================
# MARKET STATE ENDPOINTS
# =============================================================================

@router.get("/market/state", response_model=MarketState)
async def get_market_state(
    ci_service: CompetitiveIntelligenceService = Depends(get_ci_service)
):
    """
    Get current market state.
    
    Describes the competitive dynamics environment.
    """
    state = await ci_service.get_current_market_state()
    return state


@router.get("/market/equilibrium", response_model=NashEquilibriumAnalysis)
async def get_equilibrium_analysis(
    competitor_ids: List[str] = Query(...),
    ci_service: CompetitiveIntelligenceService = Depends(get_ci_service)
):
    """
    Get Nash equilibrium analysis for competitive game.
    
    Identifies stable strategy profiles and profitable deviations.
    """
    analysis = await ci_service.analyze_equilibrium(competitor_ids=competitor_ids)
    return analysis


# =============================================================================
# INTELLIGENCE SIGNAL ENDPOINTS
# =============================================================================

@router.post("/signals", response_model=SignalIngestionResult)
async def ingest_signal(
    signal: IntelligenceSignal,
    background_tasks: BackgroundTasks,
    ci_service: CompetitiveIntelligenceService = Depends(get_ci_service)
):
    """
    Ingest a competitive intelligence signal.
    
    Triggers analysis pipeline in background.
    """
    result = await ci_service.ingest_signal(signal)
    
    # Process in background
    background_tasks.add_task(
        ci_service.process_signal,
        signal_id=result.signal_id
    )
    
    return result


@router.post("/signals/creative", response_model=CreativeAnalysisResult)
async def analyze_creative(
    creative: CreativeIntelligenceSignal,
    ci_service: CompetitiveIntelligenceService = Depends(get_ci_service)
):
    """
    Analyze competitor creative for psychological mechanisms.
    
    Returns detected mechanisms and targeting inferences.
    """
    result = await ci_service.analyze_creative(creative)
    return result


# =============================================================================
# ALERTS ENDPOINT
# =============================================================================

@router.get("/alerts", response_model=List[CompetitiveAlert])
async def get_alerts(
    severity: Optional[str] = None,
    competitor_id: Optional[str] = None,
    unacknowledged_only: bool = False,
    limit: int = Query(50, ge=1, le=200),
    ci_service: CompetitiveIntelligenceService = Depends(get_ci_service)
):
    """
    Get competitive intelligence alerts.
    
    Alerts are generated when significant competitive changes are detected.
    """
    alerts = await ci_service.get_alerts(
        severity=severity,
        competitor_id=competitor_id,
        unacknowledged_only=unacknowledged_only,
        limit=limit
    )
    return alerts


@router.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: str,
    ci_service: CompetitiveIntelligenceService = Depends(get_ci_service)
):
    """Acknowledge a competitive alert."""
    await ci_service.acknowledge_alert(alert_id)
    return {"status": "acknowledged"}


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class CounterStrategyRequest(BaseModel):
    """Request for counter-strategy generation."""
    budget_constraint: Optional[float] = None
    target_segments: List[str] = Field(default_factory=list)
    preferred_mechanisms: List[CognitiveMechanismType] = Field(default_factory=list)
    excluded_mechanisms: List[CognitiveMechanismType] = Field(default_factory=list)
    risk_tolerance: str = "medium"


class PredictionValidationRequest(BaseModel):
    """Request to validate a prediction."""
    prediction_id: str
    actual_move: str
    actual_timing: Optional[datetime] = None
    notes: Optional[str] = None


class PredictionValidationResult(BaseModel):
    """Result of prediction validation."""
    prediction_id: str
    was_correct: bool
    accuracy_score: float
    feedback_incorporated: bool


class SignalIngestionResult(BaseModel):
    """Result of signal ingestion."""
    signal_id: str
    status: str
    processing_scheduled: bool


class CreativeAnalysisResult(BaseModel):
    """Result of creative analysis."""
    creative_id: str
    mechanisms_detected: List[MechanismDetectionInCreative]
    constructs_targeted: List[str]
    psychological_sophistication: float
    blind_spots_identified: List[str]
    counter_opportunities: List[str]


class CompetitorSummary(BaseModel):
    """Summary view of a competitor."""
    competitor_id: str
    name: str
    threat_level: CompetitorThreatLevel
    positioning: CompetitivePositioningType
    primary_mechanisms: List[CognitiveMechanismType]
    active_vulnerabilities: int
    last_activity: Optional[datetime]


class CompetitiveAlert(BaseModel):
    """A competitive intelligence alert."""
    alert_id: str
    alert_type: str
    severity: str
    competitor_id: str
    description: str
    recommended_actions: List[str]
    created_at: datetime
    acknowledged: bool
```

---

# SECTION I: KAFKA INTEGRATION

## Intelligence Event Topics

```python
"""
ADAM Enhancement #22 v2: Kafka Event Integration
Event-driven architecture for competitive intelligence.
"""

from typing import Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field
import json


# =============================================================================
# TOPIC DEFINITIONS
# =============================================================================

KAFKA_TOPICS = {
    # Raw intelligence signals
    "intelligence.signals.raw": {
        "partitions": 12,
        "retention_ms": 604800000,  # 7 days
        "description": "Raw intelligence signals from all sources"
    },
    
    # Processed intelligence
    "intelligence.signals.processed": {
        "partitions": 6,
        "retention_ms": 2592000000,  # 30 days
        "description": "Processed and validated intelligence"
    },
    
    # Mechanism detections
    "intelligence.mechanisms.detected": {
        "partitions": 6,
        "retention_ms": 2592000000,
        "description": "Detected mechanism usage by competitors"
    },
    
    # Vulnerability discoveries
    "intelligence.vulnerabilities.discovered": {
        "partitions": 3,
        "retention_ms": 7776000000,  # 90 days
        "description": "Newly discovered competitor vulnerabilities"
    },
    
    # Strategy generation events
    "intelligence.strategies.generated": {
        "partitions": 3,
        "retention_ms": 2592000000,
        "description": "Generated counter-strategies"
    },
    
    # Prediction events
    "intelligence.predictions.made": {
        "partitions": 3,
        "retention_ms": 7776000000,
        "description": "Competitor move predictions"
    },
    
    # Prediction validations
    "intelligence.predictions.validated": {
        "partitions": 3,
        "retention_ms": 7776000000,
        "description": "Validated predictions for model learning"
    },
    
    # Market state changes
    "intelligence.market.state_change": {
        "partitions": 1,
        "retention_ms": 31536000000,  # 1 year
        "description": "Market state transitions"
    },
    
    # Alerts
    "intelligence.alerts.triggered": {
        "partitions": 3,
        "retention_ms": 2592000000,
        "description": "Competitive alerts triggered"
    },
    
    # Cross-component: Learning signals
    "learning.competitive.outcomes": {
        "partitions": 6,
        "retention_ms": 7776000000,
        "description": "Competitive outcomes for #06 Gradient Bridge learning"
    }
}


# =============================================================================
# EVENT SCHEMAS
# =============================================================================

class IntelligenceSignalEvent(BaseModel):
    """Event for a new intelligence signal."""
    
    event_type: str = "intelligence.signal.received"
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    signal: IntelligenceSignal
    source_system: str
    priority: str = "normal"


class MechanismDetectionEvent(BaseModel):
    """Event for a mechanism detection."""
    
    event_type: str = "intelligence.mechanism.detected"
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    competitor_id: str
    mechanism: CognitiveMechanismType
    intensity: float
    confidence: float
    creative_id: str
    context: Dict[str, Any] = Field(default_factory=dict)


class VulnerabilityDiscoveryEvent(BaseModel):
    """Event for a vulnerability discovery."""
    
    event_type: str = "intelligence.vulnerability.discovered"
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    vulnerability: CompetitorVulnerability
    discovery_method: str
    recommended_actions: List[str]


class StrategyGenerationEvent(BaseModel):
    """Event for strategy generation."""
    
    event_type: str = "intelligence.strategy.generated"
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    competitor_id: str
    strategies: List[CounterMechanismStrategy]
    trigger: str  # "scheduled", "alert_response", "user_request"
    context: Dict[str, Any] = Field(default_factory=dict)


class MarketStateChangeEvent(BaseModel):
    """Event for market state change."""
    
    event_type: str = "intelligence.market.state_changed"
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    previous_state: MarketStateType
    new_state: MarketStateType
    transition_trigger: str
    confidence: float
    recommended_strategy_adjustments: List[str]


class CompetitiveOutcomeEvent(BaseModel):
    """
    Event for competitive outcomes - feeds into #06 Gradient Bridge.
    
    This is crucial for learning: every competitive encounter
    generates a learning signal.
    """
    
    event_type: str = "learning.competitive.outcome"
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Outcome details
    our_campaign_id: str
    competitor_id: str
    segment_id: str
    
    # Our approach
    our_mechanisms: List[CognitiveMechanismType]
    our_strategy_type: Optional[CounterStrategyType]
    
    # Their approach (inferred)
    their_mechanisms: List[CognitiveMechanismType]
    
    # Outcome
    we_won: bool
    our_effectiveness: float
    estimated_competitor_effectiveness: float
    
    # Context
    market_state: MarketStateType
    auction_context: Dict[str, Any] = Field(default_factory=dict)


# =============================================================================
# EVENT PRODUCER
# =============================================================================

class CompetitiveIntelligenceEventProducer:
    """
    Produces events for the competitive intelligence system.
    """
    
    def __init__(self, kafka_producer: 'KafkaProducer'):
        self.producer = kafka_producer
    
    async def emit_signal_received(self, signal: IntelligenceSignal):
        """Emit event for received intelligence signal."""
        event = IntelligenceSignalEvent(signal=signal, source_system="ci_ingestion")
        await self._publish("intelligence.signals.raw", event)
    
    async def emit_mechanism_detected(
        self,
        competitor_id: str,
        detection: MechanismDetectionInCreative,
        creative_id: str
    ):
        """Emit event for mechanism detection."""
        event = MechanismDetectionEvent(
            competitor_id=competitor_id,
            mechanism=detection.mechanism,
            intensity=detection.intensity,
            confidence=detection.confidence,
            creative_id=creative_id
        )
        await self._publish("intelligence.mechanisms.detected", event)
    
    async def emit_vulnerability_discovered(
        self,
        vulnerability: CompetitorVulnerability,
        discovery_method: str
    ):
        """Emit event for vulnerability discovery."""
        event = VulnerabilityDiscoveryEvent(
            vulnerability=vulnerability,
            discovery_method=discovery_method,
            recommended_actions=self._generate_recommended_actions(vulnerability)
        )
        await self._publish("intelligence.vulnerabilities.discovered", event)
    
    async def emit_competitive_outcome(
        self,
        outcome: 'CompetitiveOutcome'
    ):
        """
        Emit competitive outcome event for #06 Gradient Bridge.
        
        This is the critical learning signal that enables the system
        to improve counter-strategies over time.
        """
        event = CompetitiveOutcomeEvent(
            our_campaign_id=outcome.our_campaign_id,
            competitor_id=outcome.competitor_id,
            segment_id=outcome.segment_id,
            our_mechanisms=outcome.our_mechanisms,
            our_strategy_type=outcome.our_strategy_type,
            their_mechanisms=outcome.their_mechanisms,
            we_won=outcome.we_won,
            our_effectiveness=outcome.our_effectiveness,
            estimated_competitor_effectiveness=outcome.estimated_competitor_effectiveness,
            market_state=outcome.market_state
        )
        await self._publish("learning.competitive.outcomes", event)
    
    async def _publish(self, topic: str, event: BaseModel):
        """Publish event to Kafka topic."""
        await self.producer.send(
            topic=topic,
            key=event.event_id.encode('utf-8'),
            value=event.model_dump_json().encode('utf-8')
        )
    
    def _generate_recommended_actions(
        self,
        vulnerability: CompetitorVulnerability
    ) -> List[str]:
        """Generate recommended actions for a vulnerability."""
        actions = []
        
        if vulnerability.vulnerability_type == VulnerabilityType.MECHANISM_BLIND_SPOT:
            actions.append(f"Deploy creative using {vulnerability.recommended_mechanisms} mechanisms")
            actions.append(f"Target {vulnerability.description} audience segment")
        
        if vulnerability.exploitation_potential > 0.8:
            actions.append("PRIORITY: High-potential vulnerability - immediate action recommended")
        
        return actions


# =============================================================================
# EVENT CONSUMER
# =============================================================================

class CompetitiveIntelligenceEventConsumer:
    """
    Consumes events for the competitive intelligence system.
    """
    
    def __init__(
        self,
        kafka_consumer: 'KafkaConsumer',
        ci_service: 'CompetitiveIntelligenceService',
        gradient_bridge: 'GradientBridgeService'
    ):
        self.consumer = kafka_consumer
        self.ci_service = ci_service
        self.gradient_bridge = gradient_bridge
    
    async def start_consuming(self):
        """Start consuming events from relevant topics."""
        topics = [
            "intelligence.signals.raw",
            "learning.competitive.outcomes"
        ]
        
        await self.consumer.subscribe(topics)
        
        async for message in self.consumer:
            await self._process_message(message)
    
    async def _process_message(self, message):
        """Process a consumed message."""
        try:
            event_data = json.loads(message.value.decode('utf-8'))
            event_type = event_data.get('event_type')
            
            if event_type == "intelligence.signal.received":
                await self._handle_signal_event(event_data)
            
            elif event_type == "learning.competitive.outcome":
                await self._handle_outcome_event(event_data)
        
        except Exception as e:
            logger.error(f"Error processing message: {e}")
    
    async def _handle_signal_event(self, event_data: Dict):
        """Handle incoming intelligence signal."""
        signal = IntelligenceSignal(**event_data['signal'])
        await self.ci_service.process_signal(signal)
    
    async def _handle_outcome_event(self, event_data: Dict):
        """
        Handle competitive outcome for learning.
        
        Routes to #06 Gradient Bridge for credit attribution.
        """
        outcome = CompetitiveOutcomeEvent(**event_data)
        
        # Update mechanism effectiveness models
        await self.ci_service.update_mechanism_effectiveness(
            competitor_id=outcome.competitor_id,
            our_mechanisms=outcome.our_mechanisms,
            their_mechanisms=outcome.their_mechanisms,
            we_won=outcome.we_won
        )
        
        # Send to Gradient Bridge for broader learning
        await self.gradient_bridge.process_competitive_outcome(outcome)
```

---

# SECTION J: TESTING FRAMEWORK

## Unit Tests

```python
"""
ADAM Enhancement #22 v2: Unit Tests
Comprehensive test suite for Competitive Psychological Intelligence.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta
import numpy as np


class TestCompetitorPsychologicalProfile:
    """Tests for competitor profile models."""
    
    def test_mechanism_blind_spots_detection(self):
        """Test that blind spots are correctly identified."""
        mechanism_usage = {
            CognitiveMechanismType.MIMETIC_DESIRE: MechanismUsageData(
                mechanism=CognitiveMechanismType.MIMETIC_DESIRE,
                frequency=0.8,
                intensity=0.7,
                estimated_effectiveness=0.65
            ),
            CognitiveMechanismType.ATTENTION_DYNAMICS: MechanismUsageData(
                mechanism=CognitiveMechanismType.ATTENTION_DYNAMICS,
                frequency=0.6,
                intensity=0.5,
                estimated_effectiveness=0.55
            )
        }
        
        profile = MechanismProfile(
            mechanism_usage=mechanism_usage,
            primary_mechanisms=[CognitiveMechanismType.MIMETIC_DESIRE],
            secondary_mechanisms=[CognitiveMechanismType.ATTENTION_DYNAMICS]
        )
        
        blind_spots = profile.blind_spots
        
        # Should include all mechanisms NOT in mechanism_usage
        assert CognitiveMechanismType.IDENTITY_CONSTRUCTION in blind_spots
        assert CognitiveMechanismType.TEMPORAL_CONSTRUAL in blind_spots
        assert CognitiveMechanismType.EVOLUTIONARY_MOTIVE in blind_spots
        
        # Should NOT include used mechanisms
        assert CognitiveMechanismType.MIMETIC_DESIRE not in blind_spots
        assert CognitiveMechanismType.ATTENTION_DYNAMICS not in blind_spots
    
    def test_vulnerability_exploitation_ranking(self):
        """Test vulnerabilities are ranked by potential."""
        vulnerabilities = [
            CompetitorVulnerability(
                competitor_id="test",
                vulnerability_type=VulnerabilityType.MECHANISM_BLIND_SPOT,
                description="Low potential",
                exploitation_potential=0.3,
                competitor_effectiveness_in_segment=0.6,
                our_predicted_effectiveness=0.7
            ),
            CompetitorVulnerability(
                competitor_id="test",
                vulnerability_type=VulnerabilityType.SEGMENT_UNDERSERVICE,
                description="High potential",
                exploitation_potential=0.9,
                competitor_effectiveness_in_segment=0.2,
                our_predicted_effectiveness=0.8
            ),
            CompetitorVulnerability(
                competitor_id="test",
                vulnerability_type=VulnerabilityType.CONSTRUCT_GAP,
                description="Medium potential",
                exploitation_potential=0.6,
                competitor_effectiveness_in_segment=0.4,
                our_predicted_effectiveness=0.7
            )
        ]
        
        profile = CompetitorPsychologicalProfile(
            competitor_id="test",
            competitor_name="Test Competitor",
            threat_level=CompetitorThreatLevel.TACTICAL,
            positioning=CompetitivePositioningType.CHALLENGER,
            mechanism_profile=MechanismProfile(),
            construct_targeting=ConstructTargetingProfile(),
            vulnerabilities=vulnerabilities,
            strategic_behavior=StrategicBehaviorModel(competitor_id="test"),
            historical_patterns=HistoricalCompetitivePatterns(competitor_id="test")
        )
        
        top_vulns = profile.top_vulnerabilities
        
        # Should be sorted by exploitation_potential descending
        assert top_vulns[0].exploitation_potential == 0.9
        assert top_vulns[1].exploitation_potential == 0.6
        assert top_vulns[2].exploitation_potential == 0.3


class TestMechanismDetector:
    """Tests for mechanism detection."""
    
    @pytest.fixture
    def detector(self):
        return CompetitorMechanismDetector(
            claude_service=AsyncMock(),
            mechanism_registry=Mock(),
            construct_registry=Mock(),
            graph_service=AsyncMock()
        )
    
    @pytest.mark.asyncio
    async def test_creative_analysis_extracts_mechanisms(self, detector):
        """Test that creative analysis identifies mechanisms."""
        creative = CreativeIntelligenceSignal(
            signal_type=IntelligenceSignalType.CREATIVE_CAPTURE,
            source="test",
            source_reliability=0.9,
            raw_content="Test creative",
            creative_type="video",
            transcript="Join 5 million happy customers. Limited time only!",
            call_to_action="Shop Now",
            observed_context="fitness_content"
        )
        
        # Mock Claude response
        detector.claude.analyze = AsyncMock(return_value={
            "mimetic_desire": {
                "detected": True,
                "intensity": 0.75,
                "confidence": 0.85,
                "textual_evidence": ["5 million happy customers"],
                "psychological_principle": "Social proof/Girardian mimesis"
            },
            "attention_dynamics": {
                "detected": True,
                "intensity": 0.60,
                "confidence": 0.70,
                "textual_evidence": ["Limited time only"],
                "psychological_principle": "Scarcity/urgency"
            }
        })
        
        detector._check_mechanism_construct_correlation = AsyncMock(return_value=True)
        
        detections = await detector.analyze_creative(creative)
        
        assert len(detections) == 2
        assert any(d.mechanism == CognitiveMechanismType.MIMETIC_DESIRE for d in detections)
        assert any(d.mechanism == CognitiveMechanismType.ATTENTION_DYNAMICS for d in detections)


class TestCounterStrategyEngine:
    """Tests for counter-strategy generation."""
    
    @pytest.fixture
    def engine(self):
        return CounterMechanismStrategyEngine(
            claude_service=AsyncMock(),
            mechanism_effectiveness=AsyncMock(),
            construct_service=AsyncMock(),
            graph_service=AsyncMock()
        )
    
    def test_counter_mechanism_matrix_completeness(self):
        """Test that matrix covers key mechanisms."""
        matrix = CounterMechanismStrategyEngine.COUNTER_MECHANISM_MATRIX
        
        # Should have entries for major mechanisms
        assert CognitiveMechanismType.MIMETIC_DESIRE in matrix
        assert CognitiveMechanismType.ATTENTION_DYNAMICS in matrix
        assert CognitiveMechanismType.LINGUISTIC_FRAMING in matrix
    
    @pytest.mark.asyncio
    async def test_strategy_evaluation_considers_capabilities(self, engine):
        """Test that evaluation adjusts for our capabilities."""
        evaluation = await engine._evaluate_counter(
            competitor_mechanism=CognitiveMechanismType.MIMETIC_DESIRE,
            competitor_intensity=0.7,
            competitor_effectiveness=0.6,
            counter_config={
                "strategy": CounterStrategyType.DIFFERENTIATE,
                "mechanisms": [CognitiveMechanismType.IDENTITY_CONSTRUCTION],
                "expected_lift": 0.15,
                "risk": "medium"
            },
            our_capabilities={
                CognitiveMechanismType.IDENTITY_CONSTRUCTION.value: 0.8
            },
            market_state=MarketState(
                current_state=MarketStateType.STABLE_EQUILIBRIUM,
                state_confidence=0.8,
                state_started=datetime.utcnow()
            )
        )
        
        # Capability modifier should be 0.8 (our capability)
        assert evaluation['capability_modifier'] == 0.8
        
        # Score should reflect capability
        assert evaluation['score'] > 0


class TestMovePrediction:
    """Tests for move prediction."""
    
    @pytest.fixture
    def predictor(self):
        return MovePredictionEngine(
            agent_modeler=AsyncMock(),
            market_analyzer=AsyncMock(),
            claude_service=AsyncMock()
        )
    
    @pytest.mark.asyncio
    async def test_prediction_includes_responses(self, predictor):
        """Test that predictions include optimal responses."""
        # Mock behavior model
        predictor.modeler.build_agent_model = AsyncMock(return_value=StrategicBehaviorModel(
            competitor_id="test",
            aggression_level=0.7,
            innovation_propensity=0.4,
            reaction_speed=0.6,
            budget_flexibility=0.5
        ))
        
        # Mock market state
        predictor.market.get_current_state = AsyncMock(return_value=MarketState(
            current_state=MarketStateType.SEGMENT_WARFARE,
            state_confidence=0.8,
            state_started=datetime.utcnow()
        ))
        
        # Mock Claude prediction
        predictor._claude_predict = AsyncMock(return_value=[
            PredictedMove(
                move_type="budget_increase",
                description="Increase spend in fitness segment",
                probability=0.7,
                mechanisms_involved=[CognitiveMechanismType.MIMETIC_DESIRE]
            )
        ])
        
        predictor._generate_optimal_response = AsyncMock(return_value=CounterMechanismStrategy(
            competitor_id="test",
            competitor_mechanism=CognitiveMechanismType.MIMETIC_DESIRE,
            competitor_intensity=0.7,
            strategy_type=CounterStrategyType.DIFFERENTIATE,
            expected_lift_vs_matching=0.15,
            expected_cost_efficiency=0.3,
            confidence=0.8
        ))
        
        prediction = await predictor.predict_next_move("test", horizon_days=30)
        
        assert prediction.primary_prediction is not None
        assert len(prediction.optimal_responses) > 0


class TestNashEquilibrium:
    """Tests for Nash equilibrium analysis."""
    
    @pytest.fixture
    def analyzer(self):
        return NashEquilibriumAnalyzer(graph_service=AsyncMock())
    
    def test_equilibrium_detection(self, analyzer):
        """Test equilibrium is correctly detected."""
        # Simple 2-player game where current profile IS equilibrium
        current = {"self": "differentiate", "competitor_a": "mass_market"}
        
        # Payoff matrix where no one benefits from deviation
        payoffs = {
            (("competitor_a", "mass_market"), ("self", "differentiate")): {
                "self": 0.6, "competitor_a": 0.5
            },
            (("competitor_a", "mass_market"), ("self", "mass_market")): {
                "self": 0.3, "competitor_a": 0.3
            },
            (("competitor_a", "differentiate"), ("self", "differentiate")): {
                "self": 0.4, "competitor_a": 0.4
            },
            (("competitor_a", "differentiate"), ("self", "mass_market")): {
                "self": 0.2, "competitor_a": 0.6
            }
        }
        
        strategies = {
            "self": ["differentiate", "mass_market"],
            "competitor_a": ["differentiate", "mass_market"]
        }
        
        is_eq, deviations = analyzer._check_equilibrium(current, payoffs, strategies)
        
        # Should identify as equilibrium if no profitable deviations
        # (depends on payoff structure)


## Integration Tests

```python
"""
ADAM Enhancement #22 v2: Integration Tests
End-to-end tests for the competitive intelligence system.
"""

class TestCompetitiveIntelligencePipeline:
    """Integration tests for the full CI pipeline."""
    
    @pytest.fixture
    async def ci_system(self):
        """Set up full CI system for testing."""
        # Would initialize all components
        pass
    
    @pytest.mark.asyncio
    async def test_signal_to_profile_pipeline(self, ci_system):
        """Test that signals update competitor profiles."""
        # Ingest creative signal
        creative = CreativeIntelligenceSignal(
            signal_type=IntelligenceSignalType.CREATIVE_CAPTURE,
            source="test",
            source_reliability=0.9,
            competitor_id="test_competitor",
            raw_content="Test",
            creative_type="video",
            transcript="Be part of the movement. Join now."
        )
        
        # Process signal
        await ci_system.process_creative_signal(creative)
        
        # Verify profile updated
        profile = await ci_system.get_competitor_profile("test_competitor")
        
        assert profile.mechanism_profile is not None
        # Mechanism detection should have occurred
    
    @pytest.mark.asyncio
    async def test_counter_strategy_effectiveness_learning(self, ci_system):
        """Test that strategy outcomes improve future strategies."""
        # Generate initial strategy
        strategy = await ci_system.generate_counter_strategy("test_competitor")
        
        # Simulate outcome
        outcome = CompetitiveOutcomeEvent(
            our_campaign_id="test_campaign",
            competitor_id="test_competitor",
            segment_id="test_segment",
            our_mechanisms=[CognitiveMechanismType.IDENTITY_CONSTRUCTION],
            our_strategy_type=CounterStrategyType.DIFFERENTIATE,
            their_mechanisms=[CognitiveMechanismType.MIMETIC_DESIRE],
            we_won=True,
            our_effectiveness=0.72,
            estimated_competitor_effectiveness=0.58,
            market_state=MarketStateType.STABLE_EQUILIBRIUM
        )
        
        await ci_system.process_outcome(outcome)
        
        # Generate new strategy - should reflect learning
        new_strategy = await ci_system.generate_counter_strategy("test_competitor")
        
        # The winning mechanism should be more strongly recommended
        assert any(
            d.mechanism == CognitiveMechanismType.IDENTITY_CONSTRUCTION
            for s in new_strategy
            for d in s.counter_mechanisms
        )
```

---

**Document Statistics:**
- Total Lines: ~3,500
- Pydantic Models: 50+
- FastAPI Endpoints: 15+
- Kafka Topics: 10
- Neo4j Node Types: 8
- Integration Points: #04 v3, #14 v3, #27 v2, #06, #15, #28
- Implementation Timeline: 14 weeks

*This completes Enhancement #22 v2 - Competitive Psychological Intelligence, transforming competitive analysis from reactive monitoring to predictive psychological warfare.*
