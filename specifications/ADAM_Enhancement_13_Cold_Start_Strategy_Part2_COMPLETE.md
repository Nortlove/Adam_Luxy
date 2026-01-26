# ADAM Enhancement #13: Cold Start Strategy - PART 2
## Enterprise-Grade Bayesian Profiling with Hierarchical Priors & Thompson Sampling

**Version**: 2.0 COMPLETE (Part 2 of 2)  
**Date**: January 2026  
**Continuation From**: ADAM_Enhancement_13_Cold_Start_Strategy_COMPLETE.md (Part 1)  
**Priority**: P1 - Production Scale Requirement (75% of traffic underserved without this)  
**Dependencies**: #02 (Blackboard), #03 (Meta-Learning), #06 (Gradient Bridge), #30 (Feature Store), #31 (Event Bus & Cache)  
**Dependents**: #09 (Inference Engine), #14 (Brand Intelligence), #15 (Copy Generation), #28 (WPP Ad Desk)

---

## Part 2 Table of Contents

### SECTION C (CONTINUED): HIERARCHICAL PRIOR SYSTEM
13. [Contextual Priors](#contextual-priors)
14. [Prior Hierarchy Engine](#prior-hierarchy-engine)

### SECTION D: THOMPSON SAMPLING INTEGRATION
15. [Mechanism Effectiveness Priors](#mechanism-effectiveness-priors)
16. [Archetype Ã— Mechanism Beta Distributions](#archetype-mechanism-beta-distributions)
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

# SECTION C (CONTINUED): HIERARCHICAL PRIOR SYSTEM

## Contextual Priors

```python
# =============================================================================
# ADAM Enhancement #13: Contextual Priors
# Location: adam/cold_start/priors/contextual.py
# =============================================================================

"""
Contextual priors based on time, device, content, and session signals.

These priors capture situational factors that influence psychological states
independent of stable personality traits.
"""

from __future__ import annotations
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, time as dt_time, timezone
from enum import Enum
from pydantic import BaseModel, Field
import numpy as np
import math

from adam.cold_start.models.enums import (
    PersonalityTrait, CognitiveMechanism, ExtendedConstruct, PriorSource
)
from adam.cold_start.models.priors import (
    BetaDistribution, GaussianDistribution, TraitPrior, MechanismPrior,
    PsychologicalPrior
)


# =============================================================================
# CONTEXTUAL SIGNAL TYPES
# =============================================================================

class TimeOfDay(str, Enum):
    """Time of day buckets for contextual inference."""
    EARLY_MORNING = "early_morning"      # 5am-8am
    MORNING = "morning"                   # 8am-12pm
    AFTERNOON = "afternoon"               # 12pm-5pm
    EVENING = "evening"                   # 5pm-9pm
    LATE_NIGHT = "late_night"            # 9pm-5am


class DayType(str, Enum):
    """Day type for contextual inference."""
    WEEKDAY = "weekday"
    WEEKEND = "weekend"
    HOLIDAY = "holiday"


class DeviceType(str, Enum):
    """Device categories."""
    MOBILE = "mobile"
    TABLET = "tablet"
    DESKTOP = "desktop"
    SMART_TV = "smart_tv"
    SMART_SPEAKER = "smart_speaker"


class ContentCategory(str, Enum):
    """High-level content categories."""
    NEWS = "news"
    ENTERTAINMENT = "entertainment"
    SPORTS = "sports"
    FINANCE = "finance"
    HEALTH = "health"
    SHOPPING = "shopping"
    SOCIAL = "social"
    GAMING = "gaming"
    EDUCATION = "education"
    PRODUCTIVITY = "productivity"


class SessionIntent(str, Enum):
    """Inferred session intent from behavior."""
    BROWSING = "browsing"          # Low engagement, exploratory
    RESEARCHING = "researching"    # Deep engagement, comparing
    BUYING = "buying"              # Cart activity, checkout intent
    ENTERTAINING = "entertaining"  # Media consumption
    WORKING = "working"            # Productivity signals


# =============================================================================
# CONTEXTUAL SIGNAL DATA MODELS
# =============================================================================

class TemporalContext(BaseModel):
    """Temporal context signals."""
    timestamp: datetime
    time_of_day: TimeOfDay
    day_type: DayType
    local_hour: int = Field(ge=0, le=23)
    days_since_last_visit: Optional[int] = None
    session_duration_seconds: Optional[int] = None
    
    @classmethod
    def from_timestamp(
        cls,
        ts: datetime,
        is_holiday: bool = False,
        last_visit: Optional[datetime] = None,
        session_start: Optional[datetime] = None
    ) -> 'TemporalContext':
        """Create temporal context from timestamp."""
        local_hour = ts.hour
        
        # Determine time of day
        if 5 <= local_hour < 8:
            time_of_day = TimeOfDay.EARLY_MORNING
        elif 8 <= local_hour < 12:
            time_of_day = TimeOfDay.MORNING
        elif 12 <= local_hour < 17:
            time_of_day = TimeOfDay.AFTERNOON
        elif 17 <= local_hour < 21:
            time_of_day = TimeOfDay.EVENING
        else:
            time_of_day = TimeOfDay.LATE_NIGHT
        
        # Determine day type
        if is_holiday:
            day_type = DayType.HOLIDAY
        elif ts.weekday() >= 5:
            day_type = DayType.WEEKEND
        else:
            day_type = DayType.WEEKDAY
        
        # Calculate days since last visit
        days_since = None
        if last_visit:
            days_since = (ts.date() - last_visit.date()).days
        
        # Calculate session duration
        session_duration = None
        if session_start:
            session_duration = int((ts - session_start).total_seconds())
        
        return cls(
            timestamp=ts,
            time_of_day=time_of_day,
            day_type=day_type,
            local_hour=local_hour,
            days_since_last_visit=days_since,
            session_duration_seconds=session_duration
        )


class DeviceContext(BaseModel):
    """Device and platform context."""
    device_type: DeviceType
    os: Optional[str] = None
    browser: Optional[str] = None
    screen_width: Optional[int] = None
    screen_height: Optional[int] = None
    is_app: bool = False
    is_known_device: bool = False
    
    @property
    def is_mobile(self) -> bool:
        return self.device_type in {DeviceType.MOBILE, DeviceType.TABLET}
    
    @property
    def is_audio_primary(self) -> bool:
        return self.device_type in {DeviceType.SMART_SPEAKER}


class ContentContext(BaseModel):
    """Content consumption context."""
    category: ContentCategory
    subcategory: Optional[str] = None
    content_id: Optional[str] = None
    content_sentiment: Optional[float] = None  # -1 to 1
    content_complexity: Optional[float] = None  # 0 to 1
    ad_placement: Optional[str] = None  # pre-roll, mid-roll, banner, etc.


class SessionBehaviorContext(BaseModel):
    """Session behavior signals."""
    intent: SessionIntent
    pages_viewed: int = 0
    time_on_site_seconds: int = 0
    scroll_depth_avg: float = 0.0  # 0-1
    click_rate: float = 0.0  # clicks per page
    bounce_probability: float = 0.0
    cart_value: Optional[float] = None
    search_queries: List[str] = Field(default_factory=list)
    
    @property
    def engagement_score(self) -> float:
        """Compute engagement score from signals."""
        # Weighted combination of engagement indicators
        page_score = min(1.0, self.pages_viewed / 10)
        time_score = min(1.0, self.time_on_site_seconds / 300)
        scroll_score = self.scroll_depth_avg
        click_score = min(1.0, self.click_rate * 2)
        
        return (page_score * 0.25 + time_score * 0.3 + 
                scroll_score * 0.25 + click_score * 0.2)


class ContextualSignals(BaseModel):
    """Complete contextual signals for prior computation."""
    temporal: TemporalContext
    device: DeviceContext
    content: Optional[ContentContext] = None
    session_behavior: Optional[SessionBehaviorContext] = None
    
    # Additional signals
    referrer_domain: Optional[str] = None
    utm_source: Optional[str] = None
    utm_campaign: Optional[str] = None
    geo_country: Optional[str] = None
    geo_region: Optional[str] = None
    language: str = "en"


# =============================================================================
# CONTEXTUAL ADJUSTMENT MAPPINGS
# =============================================================================

# Time-of-day psychological state adjustments
# Research: Circadian rhythms affect cognitive processing, arousal, mood
TIME_OF_DAY_STATE_ADJUSTMENTS: Dict[TimeOfDay, Dict[str, float]] = {
    TimeOfDay.EARLY_MORNING: {
        "arousal": -0.15,           # Lower energy
        "construal_level": +0.1,    # More abstract thinking
        "processing_fluency": -0.05,
        "approach_avoidance": 0.0,
        "prevention_focus": +0.1,   # More cautious
    },
    TimeOfDay.MORNING: {
        "arousal": +0.1,
        "construal_level": +0.05,
        "processing_fluency": +0.1,  # Peak cognitive function
        "approach_avoidance": +0.05,
        "promotion_focus": +0.1,
    },
    TimeOfDay.AFTERNOON: {
        "arousal": -0.05,            # Post-lunch dip
        "construal_level": -0.05,
        "processing_fluency": 0.0,
        "approach_avoidance": 0.0,
    },
    TimeOfDay.EVENING: {
        "arousal": +0.05,
        "construal_level": -0.1,     # More concrete
        "processing_fluency": -0.05,
        "approach_avoidance": +0.1,  # More approach-oriented
        "hedonic_motivation": +0.15,
    },
    TimeOfDay.LATE_NIGHT: {
        "arousal": -0.1,
        "construal_level": -0.15,
        "processing_fluency": -0.15,
        "impulse_susceptibility": +0.2,
        "prevention_focus": -0.15,
    },
}

# Device type psychological implications
DEVICE_TYPE_ADJUSTMENTS: Dict[DeviceType, Dict[str, float]] = {
    DeviceType.MOBILE: {
        "processing_fluency": -0.1,   # Smaller screen = harder processing
        "construal_level": -0.1,      # More concrete/immediate
        "impulse_susceptibility": +0.15,
        "attention_span": -0.2,
    },
    DeviceType.TABLET: {
        "processing_fluency": 0.0,
        "construal_level": -0.05,
        "hedonic_motivation": +0.1,  # Often leisure device
    },
    DeviceType.DESKTOP: {
        "processing_fluency": +0.1,
        "construal_level": +0.1,
        "task_orientation": +0.15,
        "attention_span": +0.1,
    },
    DeviceType.SMART_TV: {
        "hedonic_motivation": +0.2,
        "social_context": +0.1,
        "attention_span": +0.15,
        "passive_consumption": +0.2,
    },
    DeviceType.SMART_SPEAKER: {
        "processing_fluency": -0.2,   # Audio-only
        "attention_span": -0.15,
        "multitasking": +0.3,
    },
}

# Content category â†’ mechanism effectiveness adjustments
CONTENT_MECHANISM_ADJUSTMENTS: Dict[ContentCategory, Dict[CognitiveMechanism, Tuple[float, float]]] = {
    ContentCategory.NEWS: {
        CognitiveMechanism.REGULATORY_FOCUS: (1.3, 0.8),  # Prevention focus active
        CognitiveMechanism.CONSTRUAL_LEVEL: (1.2, 0.9),   # Abstract thinking
        CognitiveMechanism.TEMPORAL_CONSTRUAL: (1.2, 0.9),
    },
    ContentCategory.ENTERTAINMENT: {
        CognitiveMechanism.WANTING_LIKING: (1.4, 0.7),    # Hedonic processing
        CognitiveMechanism.MIMETIC_DESIRE: (1.3, 0.8),   # Social influence
        CognitiveMechanism.IDENTITY_CONSTRUCTION: (1.2, 0.9),
    },
    ContentCategory.SPORTS: {
        CognitiveMechanism.MIMETIC_DESIRE: (1.4, 0.7),   # Strong social influence
        CognitiveMechanism.IDENTITY_CONSTRUCTION: (1.3, 0.8),
        CognitiveMechanism.EVOLUTIONARY_MOTIVE: (1.2, 0.9),
    },
    ContentCategory.FINANCE: {
        CognitiveMechanism.REGULATORY_FOCUS: (1.4, 0.7),
        CognitiveMechanism.TEMPORAL_CONSTRUAL: (1.3, 0.8),
        CognitiveMechanism.CONSTRUAL_LEVEL: (1.3, 0.8),
    },
    ContentCategory.SHOPPING: {
        CognitiveMechanism.WANTING_LIKING: (1.3, 0.8),
        CognitiveMechanism.AUTOMATIC_EVALUATION: (1.3, 0.8),
        CognitiveMechanism.MIMETIC_DESIRE: (1.2, 0.9),
    },
    ContentCategory.HEALTH: {
        CognitiveMechanism.REGULATORY_FOCUS: (1.3, 0.8),  # Prevention focus
        CognitiveMechanism.EVOLUTIONARY_MOTIVE: (1.2, 0.9),
        CognitiveMechanism.TEMPORAL_CONSTRUAL: (1.2, 0.9),
    },
    ContentCategory.GAMING: {
        CognitiveMechanism.WANTING_LIKING: (1.3, 0.8),
        CognitiveMechanism.IDENTITY_CONSTRUCTION: (1.3, 0.8),
        CognitiveMechanism.MIMETIC_DESIRE: (1.2, 0.9),
    },
    ContentCategory.EDUCATION: {
        CognitiveMechanism.CONSTRUAL_LEVEL: (1.3, 0.8),  # Abstract processing
        CognitiveMechanism.REGULATORY_FOCUS: (1.2, 0.9),  # Promotion focus
        CognitiveMechanism.ATTENTION_DYNAMICS: (1.2, 0.9),
    },
    ContentCategory.PRODUCTIVITY: {
        CognitiveMechanism.REGULATORY_FOCUS: (1.4, 0.7),
        CognitiveMechanism.TEMPORAL_CONSTRUAL: (1.3, 0.8),
        CognitiveMechanism.CONSTRUAL_LEVEL: (1.2, 0.9),
    },
    ContentCategory.SOCIAL: {
        CognitiveMechanism.MIMETIC_DESIRE: (1.5, 0.6),   # Strongest social influence
        CognitiveMechanism.IDENTITY_CONSTRUCTION: (1.4, 0.7),
        CognitiveMechanism.AUTOMATIC_EVALUATION: (1.2, 0.9),
    },
}

# Session intent â†’ mechanism adjustments
SESSION_INTENT_ADJUSTMENTS: Dict[SessionIntent, Dict[CognitiveMechanism, Tuple[float, float]]] = {
    SessionIntent.BROWSING: {
        CognitiveMechanism.ATTENTION_DYNAMICS: (1.3, 0.8),
        CognitiveMechanism.AUTOMATIC_EVALUATION: (1.2, 0.9),
    },
    SessionIntent.RESEARCHING: {
        CognitiveMechanism.CONSTRUAL_LEVEL: (1.3, 0.8),  # Analytical mode
        CognitiveMechanism.REGULATORY_FOCUS: (1.2, 0.9),
        CognitiveMechanism.TEMPORAL_CONSTRUAL: (1.2, 0.9),
    },
    SessionIntent.BUYING: {
        CognitiveMechanism.WANTING_LIKING: (1.4, 0.7),
        CognitiveMechanism.AUTOMATIC_EVALUATION: (1.3, 0.8),
        CognitiveMechanism.MIMETIC_DESIRE: (1.2, 0.9),
    },
    SessionIntent.ENTERTAINING: {
        CognitiveMechanism.WANTING_LIKING: (1.4, 0.7),
        CognitiveMechanism.MIMETIC_DESIRE: (1.3, 0.8),
    },
    SessionIntent.WORKING: {
        CognitiveMechanism.REGULATORY_FOCUS: (1.4, 0.7),  # Goal-oriented
        CognitiveMechanism.CONSTRUAL_LEVEL: (1.2, 0.9),
        CognitiveMechanism.ATTENTION_DYNAMICS: (1.2, 0.9),
    },
}


class ContextualPriorEngine:
    """
    Engine for computing context-conditioned priors.
    
    Adjusts priors based on situational factors like time, device,
    content, and session behavior.
    """
    
    def __init__(
        self,
        population_engine: 'PopulationPriorEngine',
        demographic_engine: Optional['DemographicPriorEngine'] = None
    ):
        self.population_engine = population_engine
        self.demographic_engine = demographic_engine
    
    def get_contextual_prior(
        self,
        signals: ContextualSignals,
        base_prior: Optional[PsychologicalPrior] = None
    ) -> PsychologicalPrior:
        """
        Compute context-adjusted prior from signals.
        
        Args:
            signals: Contextual signals (time, device, content, session)
            base_prior: Optional base prior to adjust (default: population)
            
        Returns:
            Context-adjusted psychological prior
        """
        # Start from base prior
        if base_prior is None:
            base_prior = self.population_engine.get_population_prior()
        
        # Collect mechanism adjustments
        mechanism_adjustments: Dict[CognitiveMechanism, List[Tuple[float, float]]] = {
            m: [] for m in CognitiveMechanism
        }
        
        # Apply content category adjustments
        if signals.content and signals.content.category in CONTENT_MECHANISM_ADJUSTMENTS:
            for mech, adj in CONTENT_MECHANISM_ADJUSTMENTS[signals.content.category].items():
                mechanism_adjustments[mech].append(adj)
        
        # Apply session intent adjustments
        if signals.session_behavior and signals.session_behavior.intent in SESSION_INTENT_ADJUSTMENTS:
            for mech, adj in SESSION_INTENT_ADJUSTMENTS[signals.session_behavior.intent].items():
                mechanism_adjustments[mech].append(adj)
        
        # Compute state adjustments
        state_adjustments = self._compute_state_adjustments(signals)
        
        # Build adjusted mechanism priors
        adjusted_mech_priors = {}
        for mech in CognitiveMechanism:
            base_dist = base_prior.mechanism_priors[mech].distribution
            adjustments = mechanism_adjustments[mech]
            
            if adjustments:
                # Combine multiple adjustments multiplicatively
                alpha_mult = np.prod([a[0] for a in adjustments])
                beta_mult = np.prod([a[1] for a in adjustments])
                
                adjusted_mech_priors[mech] = MechanismPrior(
                    mechanism=mech,
                    distribution=BetaDistribution(
                        alpha=base_dist.alpha * alpha_mult,
                        beta=base_dist.beta * beta_mult
                    ),
                    source=PriorSource.CONTEXTUAL
                )
            else:
                adjusted_mech_priors[mech] = MechanismPrior(
                    mechanism=mech,
                    distribution=base_dist,
                    source=PriorSource.CONTEXTUAL
                )
        
        # Calculate context richness for confidence
        context_richness = self._calculate_context_richness(signals)
        
        return PsychologicalPrior(
            trait_priors=base_prior.trait_priors,  # Traits not context-dependent
            mechanism_priors=adjusted_mech_priors,
            state_adjustments=state_adjustments,
            primary_source=PriorSource.CONTEXTUAL,
            sources_used=base_prior.sources_used + [PriorSource.CONTEXTUAL],
            overall_confidence=base_prior.overall_confidence * (1 + context_richness * 0.15)
        )
    
    def _compute_state_adjustments(
        self,
        signals: ContextualSignals
    ) -> Dict[str, float]:
        """Compute psychological state adjustments from context."""
        adjustments: Dict[str, float] = {}
        
        # Time-of-day adjustments
        if signals.temporal.time_of_day in TIME_OF_DAY_STATE_ADJUSTMENTS:
            for state, adj in TIME_OF_DAY_STATE_ADJUSTMENTS[signals.temporal.time_of_day].items():
                adjustments[state] = adjustments.get(state, 0) + adj
        
        # Device adjustments
        if signals.device.device_type in DEVICE_TYPE_ADJUSTMENTS:
            for state, adj in DEVICE_TYPE_ADJUSTMENTS[signals.device.device_type].items():
                adjustments[state] = adjustments.get(state, 0) + adj
        
        # Session engagement adjustments
        if signals.session_behavior:
            engagement = signals.session_behavior.engagement_score
            # High engagement increases attention and approach motivation
            adjustments["attention_span"] = adjustments.get("attention_span", 0) + (engagement - 0.5) * 0.2
            adjustments["approach_avoidance"] = adjustments.get("approach_avoidance", 0) + (engagement - 0.5) * 0.15
        
        # Clip all adjustments to reasonable range
        for state in adjustments:
            adjustments[state] = np.clip(adjustments[state], -0.4, 0.4)
        
        return adjustments
    
    def _calculate_context_richness(self, signals: ContextualSignals) -> float:
        """Calculate how much context information we have."""
        richness = 0.0
        
        # Always have temporal
        richness += 0.2
        
        # Device info
        richness += 0.15
        if signals.device.is_known_device:
            richness += 0.1
        
        # Content info
        if signals.content:
            richness += 0.2
            if signals.content.content_sentiment is not None:
                richness += 0.1
        
        # Session behavior
        if signals.session_behavior:
            richness += 0.15
            if signals.session_behavior.engagement_score > 0:
                richness += 0.1
        
        return min(1.0, richness)
```

---

## Prior Hierarchy Engine

```python
# =============================================================================
# ADAM Enhancement #13: Prior Hierarchy Engine
# Location: adam/cold_start/priors/hierarchy.py
# =============================================================================

"""
Prior Hierarchy Engine - Combines all prior sources into optimal prior.

Implements Bayesian model averaging across prior sources with
learned weights based on historical predictive accuracy.
"""

from __future__ import annotations
from typing import Dict, List, Optional, Any, Tuple, Set
from datetime import datetime, timezone
from enum import Enum
from pydantic import BaseModel, Field, computed_field
import numpy as np
from collections import defaultdict
import asyncio
import logging

from adam.cold_start.models.enums import (
    UserDataTier, PersonalityTrait, CognitiveMechanism, 
    ExtendedConstruct, PriorSource, PsychologicalArchetype
)
from adam.cold_start.models.priors import (
    BetaDistribution, GaussianDistribution, TraitPrior, MechanismPrior,
    PsychologicalPrior
)
from adam.cold_start.models.user import ColdStartUserProfile
from adam.cold_start.priors.population import PopulationPriorEngine
from adam.cold_start.priors.cluster import ClusterPriorEngine, ClusterDefinition
from adam.cold_start.priors.demographic import DemographicPriorEngine
from adam.cold_start.priors.contextual import ContextualPriorEngine, ContextualSignals

logger = logging.getLogger(__name__)


# =============================================================================
# PRIOR WEIGHTING CONFIGURATION
# =============================================================================

class PriorWeightingStrategy(str, Enum):
    """Strategy for combining multiple prior sources."""
    EQUAL = "equal"                    # Simple average
    HIERARCHICAL = "hierarchical"      # Use most specific available
    BAYESIAN_MODEL_AVG = "bayesian_model_avg"  # Weighted by predictive accuracy
    CONFIDENCE_WEIGHTED = "confidence_weighted"  # Weight by source confidence


class PriorHierarchyConfig(BaseModel):
    """Configuration for prior hierarchy engine."""
    
    # Weighting strategy
    strategy: PriorWeightingStrategy = PriorWeightingStrategy.BAYESIAN_MODEL_AVG
    
    # Default weights per source (used for initial bootstrapping)
    default_weights: Dict[PriorSource, float] = Field(default_factory=lambda: {
        PriorSource.POPULATION: 0.10,
        PriorSource.CLUSTER: 0.20,
        PriorSource.DEMOGRAPHIC: 0.20,
        PriorSource.CONTEXTUAL: 0.25,
        PriorSource.ARCHETYPE: 0.25,
    })
    
    # Weight learning rate for Bayesian model averaging
    weight_learning_rate: float = 0.1
    
    # Minimum weight for any source (prevent collapse)
    min_source_weight: float = 0.05
    
    # Whether to use softmax normalization
    softmax_temperature: float = 1.0
    
    # Cache TTL for computed priors
    cache_ttl_seconds: int = 300


class PriorSourceWeight(BaseModel):
    """Learned weight for a prior source."""
    source: PriorSource
    weight: float = 0.2
    accuracy_sum: float = 0.0  # Sum of accuracy scores
    count: int = 0  # Number of observations
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    @computed_field
    @property
    def empirical_accuracy(self) -> Optional[float]:
        """Compute empirical accuracy if we have observations."""
        if self.count == 0:
            return None
        return self.accuracy_sum / self.count


class CombinedPrior(BaseModel):
    """Result of combining multiple prior sources."""
    final_prior: PsychologicalPrior
    source_contributions: Dict[PriorSource, float]
    dominant_source: PriorSource
    overall_confidence: float
    sources_available: List[PriorSource]
    sources_used: List[PriorSource]
    computation_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# =============================================================================
# PRIOR HIERARCHY ENGINE
# =============================================================================

class PriorHierarchyEngine:
    """
    Master engine for computing optimal priors from all available sources.
    
    Implements:
    1. Hierarchical prior lookup (population â†’ cluster â†’ demographic â†’ contextual)
    2. Bayesian model averaging across sources
    3. Online learning of source weights from outcomes
    4. Caching and invalidation
    """
    
    def __init__(
        self,
        config: Optional[PriorHierarchyConfig] = None,
        population_engine: Optional[PopulationPriorEngine] = None,
        cluster_engine: Optional[ClusterPriorEngine] = None,
        demographic_engine: Optional[DemographicPriorEngine] = None,
        contextual_engine: Optional[ContextualPriorEngine] = None,
    ):
        self.config = config or PriorHierarchyConfig()
        
        # Initialize engines
        self.population_engine = population_engine or PopulationPriorEngine()
        self.cluster_engine = cluster_engine
        self.demographic_engine = demographic_engine or DemographicPriorEngine(
            self.population_engine
        )
        self.contextual_engine = contextual_engine or ContextualPriorEngine(
            self.population_engine,
            self.demographic_engine
        )
        
        # Initialize source weights
        self.source_weights: Dict[PriorSource, PriorSourceWeight] = {
            source: PriorSourceWeight(source=source, weight=weight)
            for source, weight in self.config.default_weights.items()
        }
        
        # Cache for computed priors
        self._prior_cache: Dict[str, Tuple[CombinedPrior, datetime]] = {}
    
    async def get_optimal_prior(
        self,
        user_profile: ColdStartUserProfile,
        context: Optional[ContextualSignals] = None,
        archetype: Optional[PsychologicalArchetype] = None,
        force_refresh: bool = False
    ) -> CombinedPrior:
        """
        Compute optimal prior for a user given all available information.
        
        Args:
            user_profile: User's cold start profile with tier and demographics
            context: Optional contextual signals (time, device, content)
            archetype: Optional detected archetype
            force_refresh: Bypass cache if True
            
        Returns:
            Combined prior with source attribution
        """
        # Check cache
        cache_key = self._compute_cache_key(user_profile, context, archetype)
        if not force_refresh and cache_key in self._prior_cache:
            cached, timestamp = self._prior_cache[cache_key]
            age = (datetime.now(timezone.utc) - timestamp).total_seconds()
            if age < self.config.cache_ttl_seconds:
                return cached
        
        # Collect priors from all available sources
        available_priors: Dict[PriorSource, PsychologicalPrior] = {}
        
        # 1. Population prior (always available)
        available_priors[PriorSource.POPULATION] = self.population_engine.get_population_prior()
        
        # 2. Demographic prior (if we have demographics)
        if user_profile.has_demographics:
            available_priors[PriorSource.DEMOGRAPHIC] = self.demographic_engine.get_demographic_prior(
                age_bracket=user_profile.age_bracket,
                gender=user_profile.gender,
                country=user_profile.country,
                income_bracket=user_profile.income_bracket,
                education_level=user_profile.education_level
            )
        
        # 3. Cluster prior (if user assigned to cluster)
        if user_profile.cluster_id is not None and self.cluster_engine:
            cluster_prior = await self.cluster_engine.get_cluster_prior(
                user_profile.cluster_id
            )
            if cluster_prior:
                available_priors[PriorSource.CLUSTER] = cluster_prior
        
        # 4. Contextual prior (if we have context)
        if context:
            base_prior = available_priors.get(
                PriorSource.DEMOGRAPHIC,
                available_priors[PriorSource.POPULATION]
            )
            available_priors[PriorSource.CONTEXTUAL] = self.contextual_engine.get_contextual_prior(
                signals=context,
                base_prior=base_prior
            )
        
        # 5. Archetype prior (if archetype detected)
        if archetype and hasattr(self, 'archetype_engine') and self.archetype_engine:
            archetype_prior = self.archetype_engine.get_archetype_prior(archetype)
            if archetype_prior:
                available_priors[PriorSource.ARCHETYPE] = archetype_prior
        
        # Combine priors based on strategy
        combined = self._combine_priors(
            available_priors,
            user_profile.data_tier
        )
        
        # Cache result
        self._prior_cache[cache_key] = (combined, datetime.now(timezone.utc))
        
        return combined
    
    def _combine_priors(
        self,
        priors: Dict[PriorSource, PsychologicalPrior],
        tier: UserDataTier
    ) -> CombinedPrior:
        """Combine multiple priors into optimal prior."""
        if self.config.strategy == PriorWeightingStrategy.HIERARCHICAL:
            return self._combine_hierarchical(priors, tier)
        elif self.config.strategy == PriorWeightingStrategy.BAYESIAN_MODEL_AVG:
            return self._combine_bayesian_model_avg(priors, tier)
        elif self.config.strategy == PriorWeightingStrategy.CONFIDENCE_WEIGHTED:
            return self._combine_confidence_weighted(priors, tier)
        else:
            return self._combine_equal(priors, tier)
    
    def _combine_hierarchical(
        self,
        priors: Dict[PriorSource, PsychologicalPrior],
        tier: UserDataTier
    ) -> CombinedPrior:
        """Use most specific prior available."""
        # Priority order (most specific first)
        priority = [
            PriorSource.ARCHETYPE,
            PriorSource.CONTEXTUAL,
            PriorSource.CLUSTER,
            PriorSource.DEMOGRAPHIC,
            PriorSource.POPULATION,
        ]
        
        dominant_source = PriorSource.POPULATION
        for source in priority:
            if source in priors:
                dominant_source = source
                break
        
        final_prior = priors[dominant_source]
        
        return CombinedPrior(
            final_prior=final_prior,
            source_contributions={dominant_source: 1.0},
            dominant_source=dominant_source,
            overall_confidence=final_prior.overall_confidence,
            sources_available=list(priors.keys()),
            sources_used=[dominant_source]
        )
    
    def _combine_bayesian_model_avg(
        self,
        priors: Dict[PriorSource, PsychologicalPrior],
        tier: UserDataTier
    ) -> CombinedPrior:
        """Combine priors using Bayesian model averaging."""
        # Get normalized weights for available sources
        available_sources = list(priors.keys())
        weights = np.array([
            self.source_weights[s].weight for s in available_sources
        ])
        
        # Apply softmax normalization
        weights = self._softmax(weights, self.config.softmax_temperature)
        
        # Create contribution mapping
        contributions = {s: w for s, w in zip(available_sources, weights)}
        
        # Combine trait priors (weighted average of Gaussian means/variances)
        combined_trait_priors = self._combine_trait_priors(priors, contributions)
        
        # Combine mechanism priors (weighted average of Beta parameters)
        combined_mechanism_priors = self._combine_mechanism_priors(priors, contributions)
        
        # Combine state adjustments
        combined_state_adjustments = self._combine_state_adjustments(priors, contributions)
        
        # Find dominant source
        dominant_source = max(contributions.keys(), key=lambda s: contributions[s])
        
        # Calculate overall confidence
        overall_confidence = sum(
            priors[s].overall_confidence * w
            for s, w in contributions.items()
        )
        
        final_prior = PsychologicalPrior(
            trait_priors=combined_trait_priors,
            mechanism_priors=combined_mechanism_priors,
            state_adjustments=combined_state_adjustments,
            primary_source=dominant_source,
            sources_used=available_sources,
            overall_confidence=overall_confidence
        )
        
        return CombinedPrior(
            final_prior=final_prior,
            source_contributions=contributions,
            dominant_source=dominant_source,
            overall_confidence=overall_confidence,
            sources_available=available_sources,
            sources_used=available_sources
        )
    
    def _combine_confidence_weighted(
        self,
        priors: Dict[PriorSource, PsychologicalPrior],
        tier: UserDataTier
    ) -> CombinedPrior:
        """Weight sources by their stated confidence."""
        total_confidence = sum(p.overall_confidence for p in priors.values())
        
        if total_confidence == 0:
            # Fall back to equal weighting
            return self._combine_equal(priors, tier)
        
        contributions = {
            source: prior.overall_confidence / total_confidence
            for source, prior in priors.items()
        }
        
        return self._build_combined_prior(priors, contributions)
    
    def _combine_equal(
        self,
        priors: Dict[PriorSource, PsychologicalPrior],
        tier: UserDataTier
    ) -> CombinedPrior:
        """Equal weighting across all sources."""
        n = len(priors)
        contributions = {source: 1.0 / n for source in priors.keys()}
        return self._build_combined_prior(priors, contributions)
    
    def _build_combined_prior(
        self,
        priors: Dict[PriorSource, PsychologicalPrior],
        contributions: Dict[PriorSource, float]
    ) -> CombinedPrior:
        """Build combined prior from contributions."""
        combined_trait_priors = self._combine_trait_priors(priors, contributions)
        combined_mechanism_priors = self._combine_mechanism_priors(priors, contributions)
        combined_state_adjustments = self._combine_state_adjustments(priors, contributions)
        
        dominant_source = max(contributions.keys(), key=lambda s: contributions[s])
        overall_confidence = sum(
            priors[s].overall_confidence * w for s, w in contributions.items()
        )
        
        final_prior = PsychologicalPrior(
            trait_priors=combined_trait_priors,
            mechanism_priors=combined_mechanism_priors,
            state_adjustments=combined_state_adjustments,
            primary_source=dominant_source,
            sources_used=list(priors.keys()),
            overall_confidence=overall_confidence
        )
        
        return CombinedPrior(
            final_prior=final_prior,
            source_contributions=contributions,
            dominant_source=dominant_source,
            overall_confidence=overall_confidence,
            sources_available=list(priors.keys()),
            sources_used=list(priors.keys())
        )
    
    def _combine_trait_priors(
        self,
        priors: Dict[PriorSource, PsychologicalPrior],
        contributions: Dict[PriorSource, float]
    ) -> Dict[PersonalityTrait, TraitPrior]:
        """Combine trait priors using weighted average of Gaussians."""
        combined = {}
        
        for trait in PersonalityTrait:
            # Collect means and variances with weights
            means = []
            variances = []
            weights = []
            
            for source, prior in priors.items():
                if trait in prior.trait_priors:
                    trait_prior = prior.trait_priors[trait]
                    means.append(trait_prior.distribution.mean)
                    variances.append(trait_prior.distribution.variance)
                    weights.append(contributions[source])
            
            if not means:
                # Default uninformative prior
                combined[trait] = TraitPrior(
                    trait=trait,
                    distribution=GaussianDistribution(mean=0.5, variance=0.0625),
                    source=PriorSource.POPULATION,
                    confidence=0.0
                )
                continue
            
            # Normalize weights
            weights = np.array(weights)
            weights = weights / weights.sum()
            
            # Weighted average of Gaussians
            combined_mean = np.average(means, weights=weights)
            combined_variance = np.average(variances, weights=weights)
            
            # Reduce variance when combining (more information)
            combined_variance *= 0.9
            
            combined[trait] = TraitPrior(
                trait=trait,
                distribution=GaussianDistribution(
                    mean=float(combined_mean),
                    variance=float(combined_variance)
                ),
                source=PriorSource.COMBINED,
                confidence=float(np.max(weights))
            )
        
        return combined
    
    def _combine_mechanism_priors(
        self,
        priors: Dict[PriorSource, PsychologicalPrior],
        contributions: Dict[PriorSource, float]
    ) -> Dict[CognitiveMechanism, MechanismPrior]:
        """Combine mechanism priors using weighted average of Betas."""
        combined = {}
        
        for mech in CognitiveMechanism:
            # Collect alphas and betas with weights
            alphas = []
            betas = []
            weights = []
            
            for source, prior in priors.items():
                if mech in prior.mechanism_priors:
                    mech_prior = prior.mechanism_priors[mech]
                    alphas.append(mech_prior.distribution.alpha)
                    betas.append(mech_prior.distribution.beta)
                    weights.append(contributions[source])
            
            if not alphas:
                # Default uninformative prior
                combined[mech] = MechanismPrior(
                    mechanism=mech,
                    distribution=BetaDistribution(alpha=1.0, beta=1.0),
                    source=PriorSource.POPULATION
                )
                continue
            
            # Normalize weights
            weights = np.array(weights)
            weights = weights / weights.sum()
            
            # Weighted average of Beta parameters
            combined_alpha = float(np.average(alphas, weights=weights))
            combined_beta = float(np.average(betas, weights=weights))
            
            combined[mech] = MechanismPrior(
                mechanism=mech,
                distribution=BetaDistribution(
                    alpha=combined_alpha,
                    beta=combined_beta
                ),
                source=PriorSource.COMBINED
            )
        
        return combined
    
    def _combine_state_adjustments(
        self,
        priors: Dict[PriorSource, PsychologicalPrior],
        contributions: Dict[PriorSource, float]
    ) -> Dict[str, float]:
        """Combine state adjustments using weighted average."""
        all_states: Set[str] = set()
        for prior in priors.values():
            if prior.state_adjustments:
                all_states.update(prior.state_adjustments.keys())
        
        combined = {}
        for state in all_states:
            values = []
            weights = []
            
            for source, prior in priors.items():
                if prior.state_adjustments and state in prior.state_adjustments:
                    values.append(prior.state_adjustments[state])
                    weights.append(contributions[source])
            
            if values:
                weights = np.array(weights)
                weights = weights / weights.sum()
                combined[state] = float(np.average(values, weights=weights))
        
        return combined
    
    def update_source_weights(
        self,
        source: PriorSource,
        predicted_mean: float,
        actual_outcome: bool,
        mechanism: CognitiveMechanism
    ) -> None:
        """
        Update source weights based on prediction accuracy.
        
        Called by Gradient Bridge when outcomes are observed.
        
        Args:
            source: The prior source being evaluated
            predicted_mean: The predicted success probability
            actual_outcome: Whether conversion actually occurred
            mechanism: The mechanism that was used
        """
        if source not in self.source_weights:
            return
        
        # Calculate prediction accuracy (Brier score component)
        outcome_val = 1.0 if actual_outcome else 0.0
        accuracy = 1.0 - (predicted_mean - outcome_val) ** 2
        
        # Update running accuracy estimate
        weight_obj = self.source_weights[source]
        weight_obj.accuracy_sum += accuracy
        weight_obj.count += 1
        weight_obj.last_updated = datetime.now(timezone.utc)
        
        # Update weight using exponential smoothing
        if weight_obj.empirical_accuracy is not None:
            target_weight = weight_obj.empirical_accuracy
            weight_obj.weight = (
                weight_obj.weight * (1 - self.config.weight_learning_rate) +
                target_weight * self.config.weight_learning_rate
            )
            
            # Enforce minimum weight
            weight_obj.weight = max(
                self.config.min_source_weight,
                weight_obj.weight
            )
        
        # Renormalize all weights
        self._renormalize_weights()
    
    def _renormalize_weights(self) -> None:
        """Renormalize weights to sum to 1."""
        total = sum(w.weight for w in self.source_weights.values())
        for w in self.source_weights.values():
            w.weight = w.weight / total
    
    def _softmax(self, x: np.ndarray, temperature: float = 1.0) -> np.ndarray:
        """Apply softmax normalization."""
        x = x / temperature
        exp_x = np.exp(x - np.max(x))  # Numerical stability
        return exp_x / exp_x.sum()
    
    def _compute_cache_key(
        self,
        user_profile: ColdStartUserProfile,
        context: Optional[ContextualSignals],
        archetype: Optional[PsychologicalArchetype]
    ) -> str:
        """Compute cache key for prior lookup."""
        key_parts = [
            user_profile.user_id,
            user_profile.data_tier.value,
            str(user_profile.cluster_id or "none"),
            user_profile.age_bracket or "none",
            user_profile.gender or "none",
        ]
        
        if context:
            key_parts.extend([
                context.temporal.time_of_day.value,
                context.device.device_type.value,
                context.content.category.value if context.content else "none",
            ])
        
        if archetype:
            key_parts.append(archetype.value)
        
        return ":".join(key_parts)
    
    def clear_cache(self, user_id: Optional[str] = None) -> int:
        """Clear cached priors."""
        if user_id:
            # Clear specific user
            keys_to_remove = [k for k in self._prior_cache.keys() if k.startswith(user_id)]
            for k in keys_to_remove:
                del self._prior_cache[k]
            return len(keys_to_remove)
        else:
            # Clear all
            count = len(self._prior_cache)
            self._prior_cache.clear()
            return count
    
    def get_weight_summary(self) -> Dict[str, Any]:
        """Get summary of current source weights."""
        return {
            source.value: {
                "weight": w.weight,
                "empirical_accuracy": w.empirical_accuracy,
                "observation_count": w.count,
                "last_updated": w.last_updated.isoformat()
            }
            for source, w in self.source_weights.items()
        }
```

---

# SECTION D: THOMPSON SAMPLING INTEGRATION

## Mechanism Effectiveness Priors

```python
# =============================================================================
# ADAM Enhancement #13: Mechanism Effectiveness Priors
# Location: adam/cold_start/thompson/mechanism_priors.py
# =============================================================================

"""
Mechanism Effectiveness Priors for Thompson Sampling.

Tracks Beta distributions for each cognitive mechanism's conversion rate
with hierarchical structure: global â†’ archetype â†’ user-level.
"""

from __future__ import annotations
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone
from pydantic import BaseModel, Field, computed_field
import numpy as np
from scipy import stats
import logging

from adam.cold_start.models.enums import (
    CognitiveMechanism, PsychologicalArchetype, PriorSource, UserDataTier
)
from adam.cold_start.models.priors import BetaDistribution

logger = logging.getLogger(__name__)


# =============================================================================
# MECHANISM EFFECTIVENESS CONFIGURATION
# =============================================================================

class MechanismEffectivenessConfig(BaseModel):
    """Configuration for mechanism effectiveness tracking."""
    
    # Prior pseudo-counts (how informative the prior is)
    default_alpha: float = 2.0
    default_beta: float = 2.0
    
    # Learning parameters
    learning_rate: float = 1.0  # How fast to update (1.0 = full Bayesian)
    
    # Exploration parameters
    exploration_bonus: float = 0.1
    uncertainty_bonus_scale: float = 0.5
    
    # Minimum observations before trusting user-level
    min_user_observations: int = 5
    min_archetype_observations: int = 50
    
    # Maximum pseudo-counts (prevents over-confidence)
    max_pseudo_counts: float = 100.0


# =============================================================================
# MECHANISM EFFECTIVENESS MODELS
# =============================================================================

class MechanismEffectiveness(BaseModel):
    """Effectiveness tracking for a single mechanism."""
    mechanism: CognitiveMechanism
    
    # Beta distribution parameters
    alpha: float = 2.0
    beta: float = 2.0
    
    # Observation counts
    successes: int = 0
    failures: int = 0
    
    # Metadata
    last_success_at: Optional[datetime] = None
    last_failure_at: Optional[datetime] = None
    last_updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    @computed_field
    @property
    def total_observations(self) -> int:
        return self.successes + self.failures
    
    @computed_field
    @property
    def mean(self) -> float:
        """Expected effectiveness (posterior mean)."""
        return self.alpha / (self.alpha + self.beta)
    
    @computed_field
    @property
    def variance(self) -> float:
        """Uncertainty in effectiveness (posterior variance)."""
        a, b = self.alpha, self.beta
        return (a * b) / ((a + b) ** 2 * (a + b + 1))
    
    @computed_field
    @property
    def std(self) -> float:
        """Standard deviation."""
        return np.sqrt(self.variance)
    
    @computed_field
    @property
    def confidence_interval_95(self) -> Tuple[float, float]:
        """95% credible interval."""
        return (
            stats.beta.ppf(0.025, self.alpha, self.beta),
            stats.beta.ppf(0.975, self.alpha, self.beta)
        )
    
    def sample(self) -> float:
        """Sample from posterior (for Thompson Sampling)."""
        return np.random.beta(self.alpha, self.beta)
    
    def update(self, success: bool, weight: float = 1.0) -> None:
        """Update posterior with new observation."""
        now = datetime.now(timezone.utc)
        
        if success:
            self.alpha += weight
            self.successes += 1
            self.last_success_at = now
        else:
            self.beta += weight
            self.failures += 1
            self.last_failure_at = now
        
        self.last_updated_at = now


class MechanismEffectivenessSet(BaseModel):
    """Complete set of mechanism effectiveness for an entity (user/archetype/global)."""
    entity_id: str
    entity_type: str  # "global", "archetype", "user"
    
    mechanisms: Dict[CognitiveMechanism, MechanismEffectiveness] = Field(
        default_factory=lambda: {
            m: MechanismEffectiveness(mechanism=m)
            for m in CognitiveMechanism
        }
    )
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    def get_effectiveness(self, mechanism: CognitiveMechanism) -> MechanismEffectiveness:
        """Get effectiveness for a mechanism."""
        if mechanism not in self.mechanisms:
            self.mechanisms[mechanism] = MechanismEffectiveness(mechanism=mechanism)
        return self.mechanisms[mechanism]
    
    def update(
        self,
        mechanism: CognitiveMechanism,
        success: bool,
        weight: float = 1.0
    ) -> None:
        """Update mechanism effectiveness."""
        self.get_effectiveness(mechanism).update(success, weight)
        self.last_updated_at = datetime.now(timezone.utc)
    
    def get_all_means(self) -> Dict[CognitiveMechanism, float]:
        """Get mean effectiveness for all mechanisms."""
        return {m: eff.mean for m, eff in self.mechanisms.items()}
    
    def get_all_samples(self) -> Dict[CognitiveMechanism, float]:
        """Sample from all mechanisms (for Thompson Sampling)."""
        return {m: eff.sample() for m, eff in self.mechanisms.items()}


# =============================================================================
# GLOBAL MECHANISM PRIORS
# =============================================================================

# Global priors based on research and Amazon corpus validation
GLOBAL_MECHANISM_PRIORS: Dict[CognitiveMechanism, Tuple[float, float]] = {
    # (alpha, beta) tuned from conversion rate research
    CognitiveMechanism.CONSTRUAL_LEVEL: (3.0, 3.0),      # Neutral, context-dependent
    CognitiveMechanism.REGULATORY_FOCUS: (4.0, 2.5),    # Generally effective
    CognitiveMechanism.AUTOMATIC_EVALUATION: (4.5, 2.0),# Strong - emotions work
    CognitiveMechanism.WANTING_LIKING: (4.0, 2.5),      # Good for hedonic products
    CognitiveMechanism.MIMETIC_DESIRE: (5.0, 2.0),      # Very strong - social proof
    CognitiveMechanism.ATTENTION_DYNAMICS: (3.0, 3.0),  # Neutral
    CognitiveMechanism.TEMPORAL_CONSTRUAL: (2.5, 3.5),  # Slightly weak - discounting
    CognitiveMechanism.IDENTITY_CONSTRUCTION: (4.0, 2.5),# Good for lifestyle
    CognitiveMechanism.EVOLUTIONARY_MOTIVE: (3.5, 3.0), # Moderate
}


class MechanismPriorManager:
    """
    Manages hierarchical mechanism effectiveness priors.
    
    Hierarchy: Global â†’ Archetype â†’ User
    """
    
    def __init__(
        self,
        config: Optional[MechanismEffectivenessConfig] = None
    ):
        self.config = config or MechanismEffectivenessConfig()
        
        # Global priors (shared across all users)
        self.global_priors = self._initialize_global_priors()
        
        # Archetype-level priors
        self.archetype_priors: Dict[PsychologicalArchetype, MechanismEffectivenessSet] = {}
        
        # User-level priors (typically loaded from cache/DB)
        self.user_priors: Dict[str, MechanismEffectivenessSet] = {}
    
    def _initialize_global_priors(self) -> MechanismEffectivenessSet:
        """Initialize global priors from research."""
        global_set = MechanismEffectivenessSet(
            entity_id="global",
            entity_type="global"
        )
        
        for mech, (alpha, beta) in GLOBAL_MECHANISM_PRIORS.items():
            global_set.mechanisms[mech] = MechanismEffectiveness(
                mechanism=mech,
                alpha=alpha,
                beta=beta
            )
        
        return global_set
    
    def get_prior_for_user(
        self,
        user_id: str,
        archetype: Optional[PsychologicalArchetype] = None,
        tier: UserDataTier = UserDataTier.TIER_0_ANONYMOUS_NEW
    ) -> MechanismEffectivenessSet:
        """
        Get mechanism priors for a user, combining hierarchically.
        
        Args:
            user_id: User identifier
            archetype: Detected archetype (if any)
            tier: User's data tier
            
        Returns:
            Combined mechanism effectiveness set
        """
        # Start with global priors
        combined = MechanismEffectivenessSet(
            entity_id=user_id,
            entity_type="user"
        )
        
        for mech in CognitiveMechanism:
            # Global level
            global_eff = self.global_priors.get_effectiveness(mech)
            alpha = global_eff.alpha
            beta = global_eff.beta
            
            # Archetype level (if available and has enough observations)
            if archetype and archetype in self.archetype_priors:
                arch_eff = self.archetype_priors[archetype].get_effectiveness(mech)
                if arch_eff.total_observations >= self.config.min_archetype_observations:
                    # Weight archetype contribution
                    arch_weight = min(1.0, arch_eff.total_observations / 200)
                    alpha = alpha * (1 - arch_weight) + arch_eff.alpha * arch_weight
                    beta = beta * (1 - arch_weight) + arch_eff.beta * arch_weight
            
            # User level (if available and has enough observations)
            if user_id in self.user_priors:
                user_eff = self.user_priors[user_id].get_effectiveness(mech)
                if user_eff.total_observations >= self.config.min_user_observations:
                    # Weight user contribution more heavily
                    user_weight = min(0.7, user_eff.total_observations / 30)
                    alpha = alpha * (1 - user_weight) + user_eff.alpha * user_weight
                    beta = beta * (1 - user_weight) + user_eff.beta * user_weight
            
            # Cap pseudo-counts to prevent over-confidence
            total = alpha + beta
            if total > self.config.max_pseudo_counts:
                scale = self.config.max_pseudo_counts / total
                alpha *= scale
                beta *= scale
            
            combined.mechanisms[mech] = MechanismEffectiveness(
                mechanism=mech,
                alpha=alpha,
                beta=beta
            )
        
        return combined
    
    def update_from_outcome(
        self,
        user_id: str,
        mechanism: CognitiveMechanism,
        success: bool,
        archetype: Optional[PsychologicalArchetype] = None
    ) -> None:
        """
        Update priors from observed outcome.
        
        Updates all levels: global, archetype (if known), and user.
        """
        weight = self.config.learning_rate
        
        # Update global (with decay)
        self.global_priors.update(mechanism, success, weight * 0.1)
        
        # Update archetype if known
        if archetype:
            if archetype not in self.archetype_priors:
                self.archetype_priors[archetype] = MechanismEffectivenessSet(
                    entity_id=archetype.value,
                    entity_type="archetype"
                )
            self.archetype_priors[archetype].update(mechanism, success, weight * 0.5)
        
        # Update user
        if user_id not in self.user_priors:
            self.user_priors[user_id] = MechanismEffectivenessSet(
                entity_id=user_id,
                entity_type="user"
            )
        self.user_priors[user_id].update(mechanism, success, weight)
    
    def get_exploration_scores(
        self,
        user_id: str,
        archetype: Optional[PsychologicalArchetype] = None
    ) -> Dict[CognitiveMechanism, float]:
        """
        Get exploration bonus scores for each mechanism.
        
        Higher scores for mechanisms with high uncertainty (low observations).
        """
        prior_set = self.get_prior_for_user(user_id, archetype)
        
        scores = {}
        for mech, eff in prior_set.mechanisms.items():
            # Uncertainty bonus based on variance
            uncertainty = eff.std
            
            # Exploration bonus for under-observed mechanisms
            observation_penalty = min(1.0, eff.total_observations / 20)
            exploration = 1.0 - observation_penalty
            
            scores[mech] = (
                self.config.exploration_bonus * exploration +
                self.config.uncertainty_bonus_scale * uncertainty
            )
        
        return scores
```

---

## Archetype Ã— Mechanism Beta Distributions

```python
# =============================================================================
# ADAM Enhancement #13: Archetype Ã— Mechanism Beta Distributions
# Location: adam/cold_start/thompson/archetype_mechanism.py
# =============================================================================

"""
Archetype Ã— Mechanism cross-product for personalized Thompson Sampling.

Each archetype has learned effectiveness distributions for each mechanism.
"""

from __future__ import annotations
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone
from pydantic import BaseModel, Field, computed_field
import numpy as np
from scipy import stats
import logging

from adam.cold_start.models.enums import CognitiveMechanism, PsychologicalArchetype
from adam.cold_start.models.priors import BetaDistribution

logger = logging.getLogger(__name__)


# =============================================================================
# ARCHETYPE Ã— MECHANISM PRIORS
# =============================================================================

# Research-grounded archetype-mechanism affinities
# Source: Matz et al. (2017), Hirsh et al. (2012), consumer psychology literature
# Format: (alpha, beta) for Beta distribution

ARCHETYPE_MECHANISM_PRIORS: Dict[PsychologicalArchetype, Dict[CognitiveMechanism, Tuple[float, float]]] = {
    PsychologicalArchetype.ACHIEVEMENT_DRIVEN: {
        CognitiveMechanism.REGULATORY_FOCUS: (6.0, 2.0),      # Strong promotion focus
        CognitiveMechanism.IDENTITY_CONSTRUCTION: (5.0, 2.5), # Self-improvement messaging
        CognitiveMechanism.TEMPORAL_CONSTRUAL: (4.5, 2.5),    # Future-oriented
        CognitiveMechanism.MIMETIC_DESIRE: (4.0, 3.0),        # Status signaling
        CognitiveMechanism.CONSTRUAL_LEVEL: (4.0, 3.0),       # Abstract goals
        CognitiveMechanism.AUTOMATIC_EVALUATION: (3.5, 3.0),
        CognitiveMechanism.WANTING_LIKING: (3.5, 3.0),
        CognitiveMechanism.ATTENTION_DYNAMICS: (3.0, 3.0),
        CognitiveMechanism.EVOLUTIONARY_MOTIVE: (3.0, 3.5),
    },
    PsychologicalArchetype.NOVELTY_SEEKER: {
        CognitiveMechanism.AUTOMATIC_EVALUATION: (5.5, 2.0),  # Emotional variety
        CognitiveMechanism.WANTING_LIKING: (5.0, 2.5),        # Hedonic seeking
        CognitiveMechanism.IDENTITY_CONSTRUCTION: (5.0, 2.5), # Self-expression
        CognitiveMechanism.ATTENTION_DYNAMICS: (4.5, 2.5),    # Novelty attention
        CognitiveMechanism.MIMETIC_DESIRE: (4.0, 3.0),        # Trendsetting
        CognitiveMechanism.CONSTRUAL_LEVEL: (3.5, 3.0),
        CognitiveMechanism.REGULATORY_FOCUS: (3.0, 3.5),
        CognitiveMechanism.TEMPORAL_CONSTRUAL: (3.0, 3.5),
        CognitiveMechanism.EVOLUTIONARY_MOTIVE: (3.5, 3.0),
    },
    PsychologicalArchetype.SOCIAL_CONNECTOR: {
        CognitiveMechanism.MIMETIC_DESIRE: (6.5, 1.5),        # Extremely social
        CognitiveMechanism.IDENTITY_CONSTRUCTION: (5.0, 2.0), # Social identity
        CognitiveMechanism.AUTOMATIC_EVALUATION: (4.5, 2.5),  # Emotional appeal
        CognitiveMechanism.WANTING_LIKING: (4.0, 3.0),
        CognitiveMechanism.EVOLUTIONARY_MOTIVE: (4.0, 3.0),   # Mate attraction
        CognitiveMechanism.ATTENTION_DYNAMICS: (3.5, 3.0),
        CognitiveMechanism.CONSTRUAL_LEVEL: (3.0, 3.5),
        CognitiveMechanism.REGULATORY_FOCUS: (3.0, 3.5),
        CognitiveMechanism.TEMPORAL_CONSTRUAL: (2.5, 4.0),
    },
    PsychologicalArchetype.SECURITY_FOCUSED: {
        CognitiveMechanism.REGULATORY_FOCUS: (6.0, 2.0),      # Strong prevention focus
        CognitiveMechanism.TEMPORAL_CONSTRUAL: (5.5, 2.0),    # Future planning
        CognitiveMechanism.CONSTRUAL_LEVEL: (4.5, 2.5),       # Concrete details
        CognitiveMechanism.AUTOMATIC_EVALUATION: (4.0, 3.0),  # Trust/fear emotions
        CognitiveMechanism.IDENTITY_CONSTRUCTION: (3.5, 3.0),
        CognitiveMechanism.MIMETIC_DESIRE: (3.0, 4.0),        # Less socially driven
        CognitiveMechanism.WANTING_LIKING: (3.0, 4.0),
        CognitiveMechanism.ATTENTION_DYNAMICS: (3.0, 3.5),
        CognitiveMechanism.EVOLUTIONARY_MOTIVE: (3.5, 3.0),
    },
    PsychologicalArchetype.HARMONY_SEEKER: {
        CognitiveMechanism.AUTOMATIC_EVALUATION: (5.0, 2.0),  # Emotional harmony
        CognitiveMechanism.MIMETIC_DESIRE: (4.5, 2.5),        # Social conformity
        CognitiveMechanism.WANTING_LIKING: (4.5, 2.5),        # Hedonic comfort
        CognitiveMechanism.IDENTITY_CONSTRUCTION: (4.0, 3.0),
        CognitiveMechanism.REGULATORY_FOCUS: (3.5, 3.5),      # Balanced focus
        CognitiveMechanism.CONSTRUAL_LEVEL: (3.0, 3.5),
        CognitiveMechanism.ATTENTION_DYNAMICS: (3.0, 3.5),
        CognitiveMechanism.TEMPORAL_CONSTRUAL: (3.0, 3.5),
        CognitiveMechanism.EVOLUTIONARY_MOTIVE: (3.5, 3.0),
    },
    PsychologicalArchetype.ANALYTICAL_THINKER: {
        CognitiveMechanism.CONSTRUAL_LEVEL: (5.5, 2.0),       # Abstract reasoning
        CognitiveMechanism.REGULATORY_FOCUS: (5.0, 2.5),      # Goal-oriented
        CognitiveMechanism.TEMPORAL_CONSTRUAL: (4.5, 2.5),    # Future planning
        CognitiveMechanism.ATTENTION_DYNAMICS: (4.0, 3.0),    # Focused attention
        CognitiveMechanism.IDENTITY_CONSTRUCTION: (3.5, 3.0),
        CognitiveMechanism.AUTOMATIC_EVALUATION: (2.5, 4.0),  # Less emotional
        CognitiveMechanism.WANTING_LIKING: (2.5, 4.0),
        CognitiveMechanism.MIMETIC_DESIRE: (2.5, 4.0),        # Less social
        CognitiveMechanism.EVOLUTIONARY_MOTIVE: (3.0, 3.5),
    },
    PsychologicalArchetype.SPONTANEOUS_EXPERIENCER: {
        CognitiveMechanism.AUTOMATIC_EVALUATION: (6.0, 1.5),  # Impulse-driven
        CognitiveMechanism.WANTING_LIKING: (5.5, 2.0),        # Immediate pleasure
        CognitiveMechanism.ATTENTION_DYNAMICS: (5.0, 2.5),    # Novelty attention
        CognitiveMechanism.MIMETIC_DESIRE: (4.0, 3.0),
        CognitiveMechanism.IDENTITY_CONSTRUCTION: (4.0, 3.0),
        CognitiveMechanism.EVOLUTIONARY_MOTIVE: (4.0, 3.0),
        CognitiveMechanism.CONSTRUAL_LEVEL: (2.5, 4.0),       # Concrete
        CognitiveMechanism.REGULATORY_FOCUS: (2.5, 4.0),      # Low self-regulation
        CognitiveMechanism.TEMPORAL_CONSTRUAL: (2.0, 5.0),    # Present-focused
    },
    PsychologicalArchetype.TRADITIONALIST: {
        CognitiveMechanism.REGULATORY_FOCUS: (5.5, 2.0),      # Prevention focus
        CognitiveMechanism.MIMETIC_DESIRE: (5.0, 2.5),        # Social norms
        CognitiveMechanism.IDENTITY_CONSTRUCTION: (4.5, 2.5), # Group identity
        CognitiveMechanism.TEMPORAL_CONSTRUAL: (4.0, 3.0),    # Past/tradition
        CognitiveMechanism.CONSTRUAL_LEVEL: (3.5, 3.5),       # Concrete values
        CognitiveMechanism.AUTOMATIC_EVALUATION: (4.0, 3.0),
        CognitiveMechanism.WANTING_LIKING: (3.0, 4.0),
        CognitiveMechanism.ATTENTION_DYNAMICS: (3.0, 3.5),
        CognitiveMechanism.EVOLUTIONARY_MOTIVE: (3.5, 3.0),
    },
}


class ArchetypeMechanismMatrix:
    """
    Matrix of archetype Ã— mechanism effectiveness distributions.
    
    Provides Thompson Sampling priors for each archetype.
    """
    
    def __init__(self):
        # Initialize from research priors
        self.matrix: Dict[PsychologicalArchetype, Dict[CognitiveMechanism, BetaDistribution]] = {}
        
        for archetype, mechanisms in ARCHETYPE_MECHANISM_PRIORS.items():
            self.matrix[archetype] = {}
            for mechanism, (alpha, beta) in mechanisms.items():
                self.matrix[archetype][mechanism] = BetaDistribution(
                    alpha=alpha,
                    beta=beta
                )
    
    def get_distribution(
        self,
        archetype: PsychologicalArchetype,
        mechanism: CognitiveMechanism
    ) -> BetaDistribution:
        """Get Beta distribution for archetype-mechanism pair."""
        if archetype not in self.matrix:
            # Default to neutral
            return BetaDistribution(alpha=2.0, beta=2.0)
        
        if mechanism not in self.matrix[archetype]:
            return BetaDistribution(alpha=2.0, beta=2.0)
        
        return self.matrix[archetype][mechanism]
    
    def sample_effectiveness(
        self,
        archetype: PsychologicalArchetype,
        mechanism: CognitiveMechanism
    ) -> float:
        """Sample effectiveness from posterior."""
        dist = self.get_distribution(archetype, mechanism)
        return np.random.beta(dist.alpha, dist.beta)
    
    def get_mean_effectiveness(
        self,
        archetype: PsychologicalArchetype,
        mechanism: CognitiveMechanism
    ) -> float:
        """Get expected effectiveness (posterior mean)."""
        dist = self.get_distribution(archetype, mechanism)
        return dist.mean
    
    def get_top_mechanisms(
        self,
        archetype: PsychologicalArchetype,
        n: int = 3
    ) -> List[Tuple[CognitiveMechanism, float]]:
        """Get top N mechanisms by expected effectiveness for archetype."""
        if archetype not in self.matrix:
            return []
        
        mechanism_means = [
            (mech, dist.mean)
            for mech, dist in self.matrix[archetype].items()
        ]
        
        mechanism_means.sort(key=lambda x: x[1], reverse=True)
        return mechanism_means[:n]
    
    def update(
        self,
        archetype: PsychologicalArchetype,
        mechanism: CognitiveMechanism,
        success: bool,
        weight: float = 1.0
    ) -> None:
        """Update distribution from outcome observation."""
        if archetype not in self.matrix:
            self.matrix[archetype] = {}
        
        if mechanism not in self.matrix[archetype]:
            self.matrix[archetype][mechanism] = BetaDistribution(alpha=2.0, beta=2.0)
        
        dist = self.matrix[archetype][mechanism]
        if success:
            self.matrix[archetype][mechanism] = BetaDistribution(
                alpha=dist.alpha + weight,
                beta=dist.beta
            )
        else:
            self.matrix[archetype][mechanism] = BetaDistribution(
                alpha=dist.alpha,
                beta=dist.beta + weight
            )
    
    def get_archetype_summary(
        self,
        archetype: PsychologicalArchetype
    ) -> Dict[str, Any]:
        """Get summary statistics for an archetype."""
        if archetype not in self.matrix:
            return {"error": "Archetype not found"}
        
        return {
            "archetype": archetype.value,
            "mechanisms": {
                mech.value: {
                    "mean": dist.mean,
                    "variance": dist.variance,
                    "alpha": dist.alpha,
                    "beta": dist.beta
                }
                for mech, dist in self.matrix[archetype].items()
            },
            "top_mechanisms": [
                {"mechanism": m.value, "mean": mean}
                for m, mean in self.get_top_mechanisms(archetype, 3)
            ]
        }
```

---

## Thompson Sampling for Cold Users

```python
# =============================================================================
# ADAM Enhancement #13: Thompson Sampling for Cold Users
# Location: adam/cold_start/thompson/sampler.py
# =============================================================================

"""
Thompson Sampling implementation for cold start mechanism selection.

Optimal exploration-exploitation balance for users with limited data.
"""

from __future__ import annotations
from typing import Dict, List, Optional, Any, Tuple, Set
from datetime import datetime, timezone
from pydantic import BaseModel, Field, computed_field
import numpy as np
from scipy import stats
import logging

from adam.cold_start.models.enums import (
    CognitiveMechanism, PsychologicalArchetype, UserDataTier, PriorSource
)
from adam.cold_start.models.priors import BetaDistribution, PsychologicalPrior
from adam.cold_start.thompson.mechanism_priors import (
    MechanismPriorManager, MechanismEffectivenessSet
)
from adam.cold_start.thompson.archetype_mechanism import ArchetypeMechanismMatrix

logger = logging.getLogger(__name__)


# =============================================================================
# THOMPSON SAMPLING CONFIGURATION
# =============================================================================

class ThompsonSamplingConfig(BaseModel):
    """Configuration for Thompson Sampling."""
    
    # Selection strategy
    n_samples: int = 1000  # Samples per mechanism for Monte Carlo
    
    # Exploration parameters
    exploration_coefficient: float = 0.1
    uncertainty_weight: float = 0.3
    
    # Cold user specific
    cold_exploration_boost: float = 0.2  # Extra exploration for cold users
    
    # Mechanism subset selection
    max_mechanisms_to_consider: int = 5  # Focus on top mechanisms
    
    # Diversity parameters
    diversity_penalty: float = 0.1  # Penalize recently used mechanisms
    recent_window_hours: int = 24


class MechanismSelection(BaseModel):
    """Result of Thompson Sampling mechanism selection."""
    selected_mechanism: CognitiveMechanism
    
    # Sampling details
    sampled_value: float
    expected_value: float
    uncertainty: float
    
    # Exploration info
    exploration_bonus: float
    is_exploration: bool
    
    # Ranking
    rank: int
    all_samples: Dict[CognitiveMechanism, float] = Field(default_factory=dict)
    
    # Source info
    prior_source: PriorSource
    archetype_used: Optional[PsychologicalArchetype] = None
    
    # Metadata
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    @computed_field
    @property
    def confidence(self) -> float:
        """Confidence in selection (inverse of uncertainty)."""
        return 1.0 / (1.0 + self.uncertainty)


class MultiMechanismSelection(BaseModel):
    """Selection of multiple mechanisms for messaging."""
    primary: MechanismSelection
    secondary: Optional[MechanismSelection] = None
    tertiary: Optional[MechanismSelection] = None
    
    # Combined strategy
    primary_weight: float = 0.6
    secondary_weight: float = 0.3
    tertiary_weight: float = 0.1


# =============================================================================
# THOMPSON SAMPLER
# =============================================================================

class ColdStartThompsonSampler:
    """
    Thompson Sampling for cold start mechanism selection.
    
    Implements:
    1. Hierarchical priors (global â†’ archetype â†’ user)
    2. Exploration bonuses for uncertain mechanisms
    3. Diversity penalties for over-used mechanisms
    4. Contextual adjustments
    """
    
    def __init__(
        self,
        config: Optional[ThompsonSamplingConfig] = None,
        mechanism_manager: Optional[MechanismPriorManager] = None,
        archetype_matrix: Optional[ArchetypeMechanismMatrix] = None
    ):
        self.config = config or ThompsonSamplingConfig()
        self.mechanism_manager = mechanism_manager or MechanismPriorManager()
        self.archetype_matrix = archetype_matrix or ArchetypeMechanismMatrix()
        
        # Track recent selections for diversity
        self._recent_selections: Dict[str, List[Tuple[CognitiveMechanism, datetime]]] = {}
    
    def select_mechanism(
        self,
        user_id: str,
        tier: UserDataTier,
        archetype: Optional[PsychologicalArchetype] = None,
        combined_prior: Optional[PsychologicalPrior] = None,
        eligible_mechanisms: Optional[Set[CognitiveMechanism]] = None,
        context_adjustments: Optional[Dict[CognitiveMechanism, float]] = None
    ) -> MechanismSelection:
        """
        Select optimal mechanism using Thompson Sampling.
        
        Args:
            user_id: User identifier
            tier: User's data tier
            archetype: Detected archetype (if any)
            combined_prior: Combined prior from hierarchy engine
            eligible_mechanisms: Subset of mechanisms to consider
            context_adjustments: Context-based adjustments to effectiveness
            
        Returns:
            MechanismSelection with selected mechanism and details
        """
        # Determine eligible mechanisms
        if eligible_mechanisms is None:
            eligible_mechanisms = set(CognitiveMechanism)
        
        # Get effectiveness priors
        effectiveness_set = self.mechanism_manager.get_prior_for_user(
            user_id, archetype, tier
        )
        
        # Get exploration scores
        exploration_scores = self.mechanism_manager.get_exploration_scores(
            user_id, archetype
        )
        
        # Get diversity penalties
        diversity_penalties = self._get_diversity_penalties(user_id)
        
        # Sample from each mechanism's posterior
        samples: Dict[CognitiveMechanism, float] = {}
        details: Dict[CognitiveMechanism, Dict[str, float]] = {}
        
        for mech in eligible_mechanisms:
            eff = effectiveness_set.get_effectiveness(mech)
            
            # Base Thompson sample
            base_sample = eff.sample()
            
            # Apply context adjustments
            if context_adjustments and mech in context_adjustments:
                base_sample *= (1.0 + context_adjustments[mech])
            
            # Apply exploration bonus
            exploration_bonus = exploration_scores.get(mech, 0)
            
            # Apply cold user exploration boost
            if tier in {UserDataTier.TIER_0_ANONYMOUS_NEW, UserDataTier.TIER_1_ANONYMOUS_SESSION}:
                exploration_bonus += self.config.cold_exploration_boost
            
            # Apply diversity penalty
            diversity_penalty = diversity_penalties.get(mech, 0)
            
            # Final adjusted sample
            adjusted_sample = (
                base_sample * (1 + self.config.uncertainty_weight * eff.std) +
                self.config.exploration_coefficient * exploration_bonus -
                self.config.diversity_penalty * diversity_penalty
            )
            
            samples[mech] = adjusted_sample
            details[mech] = {
                "base_sample": base_sample,
                "mean": eff.mean,
                "std": eff.std,
                "exploration_bonus": exploration_bonus,
                "diversity_penalty": diversity_penalty,
                "adjusted_sample": adjusted_sample
            }
        
        # Select mechanism with highest adjusted sample
        selected_mech = max(samples.keys(), key=lambda m: samples[m])
        selected_details = details[selected_mech]
        
        # Determine if this is exploration (selected despite lower mean)
        mean_ranking = sorted(
            eligible_mechanisms,
            key=lambda m: effectiveness_set.get_effectiveness(m).mean,
            reverse=True
        )
        is_exploration = selected_mech not in mean_ranking[:3]
        
        # Compute rank
        sorted_mechs = sorted(samples.keys(), key=lambda m: samples[m], reverse=True)
        rank = sorted_mechs.index(selected_mech) + 1
        
        # Track selection for diversity
        self._record_selection(user_id, selected_mech)
        
        return MechanismSelection(
            selected_mechanism=selected_mech,
            sampled_value=selected_details["adjusted_sample"],
            expected_value=selected_details["mean"],
            uncertainty=selected_details["std"],
            exploration_bonus=selected_details["exploration_bonus"],
            is_exploration=is_exploration,
            rank=rank,
            all_samples={m: samples[m] for m in sorted_mechs[:5]},  # Top 5
            prior_source=PriorSource.ARCHETYPE if archetype else PriorSource.POPULATION,
            archetype_used=archetype
        )
    
    def select_multiple_mechanisms(
        self,
        user_id: str,
        tier: UserDataTier,
        archetype: Optional[PsychologicalArchetype] = None,
        n_mechanisms: int = 3
    ) -> MultiMechanismSelection:
        """
        Select multiple mechanisms for composite messaging.
        
        Returns primary, secondary, and optionally tertiary mechanisms.
        """
        # Get all mechanism samples
        effectiveness_set = self.mechanism_manager.get_prior_for_user(
            user_id, archetype, tier
        )
        
        samples: Dict[CognitiveMechanism, float] = {}
        for mech in CognitiveMechanism:
            eff = effectiveness_set.get_effectiveness(mech)
            samples[mech] = eff.sample()
        
        # Sort by sampled value
        sorted_mechs = sorted(samples.keys(), key=lambda m: samples[m], reverse=True)
        
        # Select top N
        selections = []
        for i, mech in enumerate(sorted_mechs[:n_mechanisms]):
            eff = effectiveness_set.get_effectiveness(mech)
            
            selection = MechanismSelection(
                selected_mechanism=mech,
                sampled_value=samples[mech],
                expected_value=eff.mean,
                uncertainty=eff.std,
                exploration_bonus=0.0,
                is_exploration=(i > 0),  # Non-primary are exploratory
                rank=i + 1,
                all_samples=dict(list(sorted(samples.items(), key=lambda x: x[1], reverse=True))[:5]),
                prior_source=PriorSource.ARCHETYPE if archetype else PriorSource.POPULATION,
                archetype_used=archetype
            )
            selections.append(selection)
        
        return MultiMechanismSelection(
            primary=selections[0],
            secondary=selections[1] if len(selections) > 1 else None,
            tertiary=selections[2] if len(selections) > 2 else None
        )
    
    def _get_diversity_penalties(
        self,
        user_id: str
    ) -> Dict[CognitiveMechanism, float]:
        """Get penalties for recently used mechanisms."""
        penalties = {m: 0.0 for m in CognitiveMechanism}
        
        if user_id not in self._recent_selections:
            return penalties
        
        now = datetime.now(timezone.utc)
        window = self.config.recent_window_hours * 3600
        
        recent = [
            (mech, ts) for mech, ts in self._recent_selections[user_id]
            if (now - ts).total_seconds() < window
        ]
        
        # Count recent selections per mechanism
        for mech, ts in recent:
            # Decay penalty over time
            age_hours = (now - ts).total_seconds() / 3600
            decay = 1.0 - (age_hours / self.config.recent_window_hours)
            penalties[mech] += decay
        
        return penalties
    
    def _record_selection(
        self,
        user_id: str,
        mechanism: CognitiveMechanism
    ) -> None:
        """Record mechanism selection for diversity tracking."""
        if user_id not in self._recent_selections:
            self._recent_selections[user_id] = []
        
        self._recent_selections[user_id].append((
            mechanism,
            datetime.now(timezone.utc)
        ))
        
        # Trim old entries
        cutoff = datetime.now(timezone.utc)
        self._recent_selections[user_id] = [
            (m, ts) for m, ts in self._recent_selections[user_id]
            if (cutoff - ts).total_seconds() < self.config.recent_window_hours * 3600
        ]
    
    def update_from_outcome(
        self,
        user_id: str,
        mechanism: CognitiveMechanism,
        success: bool,
        archetype: Optional[PsychologicalArchetype] = None
    ) -> None:
        """Update priors from outcome."""
        self.mechanism_manager.update_from_outcome(
            user_id, mechanism, success, archetype
        )
        
        if archetype:
            self.archetype_matrix.update(archetype, mechanism, success)
```

---

## Exploration Bonus System

```python
# =============================================================================
# ADAM Enhancement #13: Exploration Bonus System
# Location: adam/cold_start/thompson/exploration.py
# =============================================================================

"""
Exploration Bonus System for optimal learning in cold start scenarios.

Implements information-theoretic exploration bonuses to accelerate
profile development while minimizing regret.
"""

from __future__ import annotations
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone, timedelta
from pydantic import BaseModel, Field, computed_field
import numpy as np
from scipy import stats
import math
import logging

from adam.cold_start.models.enums import (
    CognitiveMechanism, PsychologicalArchetype, UserDataTier
)
from adam.cold_start.models.priors import BetaDistribution

logger = logging.getLogger(__name__)


# =============================================================================
# EXPLORATION CONFIGURATION
# =============================================================================

class ExplorationConfig(BaseModel):
    """Configuration for exploration bonus system."""
    
    # UCB-style exploration
    ucb_coefficient: float = 2.0  # Controls exploration vs exploitation
    
    # Information gain parameters
    entropy_weight: float = 0.3
    kl_divergence_weight: float = 0.2
    
    # Tier-specific exploration rates
    tier_exploration_rates: Dict[str, float] = Field(default_factory=lambda: {
        "tier_0_anonymous_new": 0.4,
        "tier_1_anonymous_session": 0.35,
        "tier_2_registered_minimal": 0.3,
        "tier_3_registered_sparse": 0.2,
        "tier_4_registered_moderate": 0.1,
        "tier_5_profiled_full": 0.05,
    })
    
    # Time-based decay
    exploration_decay_days: float = 14.0  # Days for exploration to decay
    min_exploration_rate: float = 0.05
    
    # Regret bounds
    target_regret_rate: float = 0.1  # Acceptable regret rate


class ExplorationBonus(BaseModel):
    """Exploration bonus calculation result."""
    mechanism: CognitiveMechanism
    
    # Component bonuses
    ucb_bonus: float = 0.0
    entropy_bonus: float = 0.0
    information_gain_bonus: float = 0.0
    tier_bonus: float = 0.0
    recency_bonus: float = 0.0
    
    # Final bonus
    total_bonus: float = 0.0
    
    # Metadata
    observations: int = 0
    days_since_first_seen: Optional[float] = None


# =============================================================================
# EXPLORATION BONUS CALCULATOR
# =============================================================================

class ExplorationBonusCalculator:
    """
    Calculates exploration bonuses for mechanism selection.
    
    Implements multiple exploration strategies:
    1. UCB (Upper Confidence Bound)
    2. Information gain (entropy reduction)
    3. Tier-based exploration rates
    4. Time-decay exploration
    """
    
    def __init__(self, config: Optional[ExplorationConfig] = None):
        self.config = config or ExplorationConfig()
    
    def calculate_bonus(
        self,
        mechanism: CognitiveMechanism,
        prior: BetaDistribution,
        tier: UserDataTier,
        total_selections: int,
        mechanism_selections: int,
        first_seen: Optional[datetime] = None,
        last_selected: Optional[datetime] = None
    ) -> ExplorationBonus:
        """
        Calculate total exploration bonus for a mechanism.
        
        Args:
            mechanism: The mechanism to evaluate
            prior: Current Beta prior for the mechanism
            tier: User's data tier
            total_selections: Total mechanism selections for user
            mechanism_selections: Times this mechanism was selected
            first_seen: When user was first seen
            last_selected: When mechanism was last selected
        """
        bonus = ExplorationBonus(
            mechanism=mechanism,
            observations=mechanism_selections
        )
        
        # 1. UCB bonus (explore uncertain mechanisms)
        bonus.ucb_bonus = self._compute_ucb_bonus(
            prior, total_selections, mechanism_selections
        )
        
        # 2. Entropy bonus (explore high-variance mechanisms)
        bonus.entropy_bonus = self._compute_entropy_bonus(prior)
        
        # 3. Information gain bonus (explore where we learn most)
        bonus.information_gain_bonus = self._compute_information_gain_bonus(
            prior, mechanism_selections
        )
        
        # 4. Tier-based bonus (explore more for cold users)
        bonus.tier_bonus = self._compute_tier_bonus(tier)
        
        # 5. Recency bonus (explore mechanisms not recently used)
        bonus.recency_bonus = self._compute_recency_bonus(last_selected)
        
        # Calculate days since first seen
        if first_seen:
            bonus.days_since_first_seen = (
                datetime.now(timezone.utc) - first_seen
            ).total_seconds() / 86400
        
        # Combine bonuses (weighted sum)
        bonus.total_bonus = (
            bonus.ucb_bonus * 0.3 +
            bonus.entropy_bonus * self.config.entropy_weight +
            bonus.information_gain_bonus * self.config.kl_divergence_weight +
            bonus.tier_bonus * 0.3 +
            bonus.recency_bonus * 0.1
        )
        
        # Apply time decay
        if bonus.days_since_first_seen is not None:
            decay = self._compute_time_decay(bonus.days_since_first_seen)
            bonus.total_bonus *= decay
        
        return bonus
    
    def _compute_ucb_bonus(
        self,
        prior: BetaDistribution,
        total_selections: int,
        mechanism_selections: int
    ) -> float:
        """
        Compute UCB (Upper Confidence Bound) bonus.
        
        UCB bonus = c * sqrt(ln(n) / n_i)
        """
        if total_selections == 0:
            return self.config.ucb_coefficient
        
        if mechanism_selections == 0:
            return self.config.ucb_coefficient * 2  # Never tried = high bonus
        
        return self.config.ucb_coefficient * math.sqrt(
            math.log(total_selections + 1) / mechanism_selections
        )
    
    def _compute_entropy_bonus(self, prior: BetaDistribution) -> float:
        """
        Compute entropy bonus (explore high-variance mechanisms).
        
        Higher entropy = more uncertainty = more to learn.
        """
        # Beta distribution entropy
        a, b = prior.alpha, prior.beta
        
        # Numerical approximation of Beta entropy
        entropy = (
            math.lgamma(a) + math.lgamma(b) - math.lgamma(a + b) -
            (a - 1) * (stats.digamma(a) - stats.digamma(a + b)) -
            (b - 1) * (stats.digamma(b) - stats.digamma(a + b))
        )
        
        # Normalize to [0, 1] range (max entropy is ~1.4 for Beta(1,1))
        normalized_entropy = min(1.0, entropy / 1.4)
        
        return normalized_entropy
    
    def _compute_information_gain_bonus(
        self,
        prior: BetaDistribution,
        observations: int
    ) -> float:
        """
        Compute expected information gain from one more observation.
        
        Based on KL divergence between prior and expected posterior.
        """
        a, b = prior.alpha, prior.beta
        p = a / (a + b)  # Current mean
        
        # Expected posterior after success
        post_success_mean = (a + 1) / (a + b + 1)
        
        # Expected posterior after failure
        post_failure_mean = a / (a + b + 1)
        
        # Expected KL divergence (weighted by outcome probabilities)
        expected_change = abs(post_success_mean - p) * p + abs(post_failure_mean - p) * (1 - p)
        
        # Decay with observations (diminishing returns)
        decay = 1.0 / (1.0 + observations / 10)
        
        return expected_change * decay
    
    def _compute_tier_bonus(self, tier: UserDataTier) -> float:
        """Get tier-specific exploration bonus."""
        return self.config.tier_exploration_rates.get(
            tier.value,
            self.config.min_exploration_rate
        )
    
    def _compute_recency_bonus(
        self,
        last_selected: Optional[datetime]
    ) -> float:
        """Compute bonus for mechanisms not recently selected."""
        if last_selected is None:
            return 0.5  # Never selected = moderate bonus
        
        hours_since = (datetime.now(timezone.utc) - last_selected).total_seconds() / 3600
        
        # Bonus increases with time since last selection
        # Saturates at ~1.0 after 7 days
        return min(1.0, hours_since / 168)
    
    def _compute_time_decay(self, days_since_first_seen: float) -> float:
        """
        Compute exploration decay over time.
        
        Exploration decreases as we learn more about the user.
        """
        decay = math.exp(-days_since_first_seen / self.config.exploration_decay_days)
        return max(self.config.min_exploration_rate, decay)
    
    def compute_all_bonuses(
        self,
        priors: Dict[CognitiveMechanism, BetaDistribution],
        tier: UserDataTier,
        total_selections: int,
        mechanism_selections: Dict[CognitiveMechanism, int],
        first_seen: Optional[datetime] = None,
        last_selections: Optional[Dict[CognitiveMechanism, datetime]] = None
    ) -> Dict[CognitiveMechanism, ExplorationBonus]:
        """Compute exploration bonuses for all mechanisms."""
        return {
            mech: self.calculate_bonus(
                mechanism=mech,
                prior=priors.get(mech, BetaDistribution(alpha=1.0, beta=1.0)),
                tier=tier,
                total_selections=total_selections,
                mechanism_selections=mechanism_selections.get(mech, 0),
                first_seen=first_seen,
                last_selected=last_selections.get(mech) if last_selections else None
            )
            for mech in CognitiveMechanism
        }
    
    def should_explore(
        self,
        tier: UserDataTier,
        exploration_bonus: float,
        best_expected_value: float
    ) -> bool:
        """
        Determine if we should explore (vs exploit).
        
        Uses epsilon-greedy with adaptive epsilon based on tier and bonus.
        """
        # Base exploration rate from tier
        base_rate = self.config.tier_exploration_rates.get(
            tier.value,
            self.config.min_exploration_rate
        )
        
        # Adjust by exploration bonus
        adjusted_rate = min(0.5, base_rate + exploration_bonus * 0.1)
        
        # Random exploration decision
        return np.random.random() < adjusted_rate
```

---

# SECTION E: PSYCHOLOGICAL ARCHETYPE SYSTEM

## Research-Grounded Archetypes

```python
# =============================================================================
# ADAM Enhancement #13: Research-Grounded Archetypes
# Location: adam/cold_start/archetypes/definitions.py
# =============================================================================

"""
Psychological Archetype Definitions based on academic research.

Archetypes are grounded in:
- Big Five personality research (Costa & McCrae)
- Consumer psychology (Matz et al., 2017)
- Decision-making research (Kahneman, Tversky)
- Regulatory Focus Theory (Higgins)
"""

from __future__ import annotations
from typing import Dict, List, Optional, Any, Tuple
from pydantic import BaseModel, Field, computed_field
from enum import Enum
import numpy as np

from adam.cold_start.models.enums import (
    PersonalityTrait, CognitiveMechanism, ExtendedConstruct, PsychologicalArchetype
)
from adam.cold_start.models.priors import GaussianDistribution


# =============================================================================
# ARCHETYPE TRAIT PROFILES
# =============================================================================

class ArchetypeTraitProfile(BaseModel):
    """Big Five trait profile for an archetype."""
    openness: GaussianDistribution
    conscientiousness: GaussianDistribution
    extraversion: GaussianDistribution
    agreeableness: GaussianDistribution
    neuroticism: GaussianDistribution
    
    def to_dict(self) -> Dict[PersonalityTrait, GaussianDistribution]:
        return {
            PersonalityTrait.OPENNESS: self.openness,
            PersonalityTrait.CONSCIENTIOUSNESS: self.conscientiousness,
            PersonalityTrait.EXTRAVERSION: self.extraversion,
            PersonalityTrait.AGREEABLENESS: self.agreeableness,
            PersonalityTrait.NEUROTICISM: self.neuroticism,
        }
    
    def to_vector(self) -> np.ndarray:
        """Convert to mean vector."""
        return np.array([
            self.openness.mean,
            self.conscientiousness.mean,
            self.extraversion.mean,
            self.agreeableness.mean,
            self.neuroticism.mean
        ])


class ArchetypeDefinition(BaseModel):
    """Complete archetype definition with psychological profile."""
    archetype: PsychologicalArchetype
    name: str
    description: str
    
    # Big Five profile
    trait_profile: ArchetypeTraitProfile
    
    # Primary psychological characteristics
    regulatory_focus: str  # "promotion", "prevention", "balanced"
    construal_level: str  # "abstract", "concrete", "balanced"
    temporal_orientation: str  # "past", "present", "future"
    
    # Decision-making style
    decision_style: str  # "analytical", "intuitive", "spontaneous"
    risk_tolerance: str  # "high", "moderate", "low"
    
    # Social orientation
    social_influence_susceptibility: str  # "high", "moderate", "low"
    identity_salience: str  # "high", "moderate", "low"
    
    # Top mechanisms (ranked by effectiveness)
    primary_mechanisms: List[CognitiveMechanism]
    secondary_mechanisms: List[CognitiveMechanism]
    avoid_mechanisms: List[CognitiveMechanism]
    
    # Message framing preferences
    message_tone: str  # "emotional", "rational", "aspirational", "practical"
    message_length: str  # "brief", "detailed", "moderate"
    social_proof_weight: str  # "high", "moderate", "low"
    
    # Research citations
    research_basis: List[str] = Field(default_factory=list)


# =============================================================================
# ARCHETYPE DEFINITIONS
# =============================================================================

ARCHETYPE_DEFINITIONS: Dict[PsychologicalArchetype, ArchetypeDefinition] = {
    
    PsychologicalArchetype.ACHIEVEMENT_DRIVEN: ArchetypeDefinition(
        archetype=PsychologicalArchetype.ACHIEVEMENT_DRIVEN,
        name="Achievement-Driven",
        description="Goal-oriented individuals motivated by success, status, and self-improvement. "
                   "Respond to messaging about advancement, efficiency, and competitive advantage.",
        trait_profile=ArchetypeTraitProfile(
            openness=GaussianDistribution(mean=0.60, variance=0.02),
            conscientiousness=GaussianDistribution(mean=0.75, variance=0.02),
            extraversion=GaussianDistribution(mean=0.55, variance=0.03),
            agreeableness=GaussianDistribution(mean=0.45, variance=0.03),
            neuroticism=GaussianDistribution(mean=0.45, variance=0.03),
        ),
        regulatory_focus="promotion",
        construal_level="abstract",
        temporal_orientation="future",
        decision_style="analytical",
        risk_tolerance="moderate",
        social_influence_susceptibility="moderate",
        identity_salience="high",
        primary_mechanisms=[
            CognitiveMechanism.REGULATORY_FOCUS,
            CognitiveMechanism.IDENTITY_CONSTRUCTION,
            CognitiveMechanism.TEMPORAL_CONSTRUAL,
        ],
        secondary_mechanisms=[
            CognitiveMechanism.MIMETIC_DESIRE,
            CognitiveMechanism.CONSTRUAL_LEVEL,
        ],
        avoid_mechanisms=[
            CognitiveMechanism.WANTING_LIKING,  # Too hedonic
        ],
        message_tone="aspirational",
        message_length="moderate",
        social_proof_weight="moderate",
        research_basis=[
            "McClelland (1961) - Achievement motivation",
            "Higgins (1997) - Promotion focus",
            "Matz et al. (2017) - High-C personality messaging",
        ]
    ),
    
    PsychologicalArchetype.NOVELTY_SEEKER: ArchetypeDefinition(
        archetype=PsychologicalArchetype.NOVELTY_SEEKER,
        name="Novelty Seeker",
        description="Experience-oriented individuals drawn to new, unique, and creative offerings. "
                   "Respond to messaging about innovation, uniqueness, and sensory experiences.",
        trait_profile=ArchetypeTraitProfile(
            openness=GaussianDistribution(mean=0.80, variance=0.02),
            conscientiousness=GaussianDistribution(mean=0.45, variance=0.03),
            extraversion=GaussianDistribution(mean=0.65, variance=0.03),
            agreeableness=GaussianDistribution(mean=0.55, variance=0.03),
            neuroticism=GaussianDistribution(mean=0.50, variance=0.03),
        ),
        regulatory_focus="promotion",
        construal_level="concrete",
        temporal_orientation="present",
        decision_style="intuitive",
        risk_tolerance="high",
        social_influence_susceptibility="moderate",
        identity_salience="high",
        primary_mechanisms=[
            CognitiveMechanism.AUTOMATIC_EVALUATION,
            CognitiveMechanism.WANTING_LIKING,
            CognitiveMechanism.IDENTITY_CONSTRUCTION,
        ],
        secondary_mechanisms=[
            CognitiveMechanism.ATTENTION_DYNAMICS,
            CognitiveMechanism.MIMETIC_DESIRE,
        ],
        avoid_mechanisms=[
            CognitiveMechanism.TEMPORAL_CONSTRUAL,  # Too future-focused
        ],
        message_tone="emotional",
        message_length="brief",
        social_proof_weight="moderate",
        research_basis=[
            "Zuckerman (1994) - Sensation seeking",
            "Hirsh et al. (2012) - High-O personality messaging",
            "Matz et al. (2017) - Openness and ad response",
        ]
    ),
    
    PsychologicalArchetype.SOCIAL_CONNECTOR: ArchetypeDefinition(
        archetype=PsychologicalArchetype.SOCIAL_CONNECTOR,
        name="Social Connector",
        description="Relationship-oriented individuals motivated by social bonds and belonging. "
                   "Respond strongly to social proof, community, and interpersonal messaging.",
        trait_profile=ArchetypeTraitProfile(
            openness=GaussianDistribution(mean=0.55, variance=0.03),
            conscientiousness=GaussianDistribution(mean=0.50, variance=0.03),
            extraversion=GaussianDistribution(mean=0.75, variance=0.02),
            agreeableness=GaussianDistribution(mean=0.70, variance=0.02),
            neuroticism=GaussianDistribution(mean=0.50, variance=0.03),
        ),
        regulatory_focus="promotion",
        construal_level="concrete",
        temporal_orientation="present",
        decision_style="intuitive",
        risk_tolerance="moderate",
        social_influence_susceptibility="high",
        identity_salience="high",
        primary_mechanisms=[
            CognitiveMechanism.MIMETIC_DESIRE,
            CognitiveMechanism.IDENTITY_CONSTRUCTION,
            CognitiveMechanism.AUTOMATIC_EVALUATION,
        ],
        secondary_mechanisms=[
            CognitiveMechanism.WANTING_LIKING,
            CognitiveMechanism.EVOLUTIONARY_MOTIVE,
        ],
        avoid_mechanisms=[
            CognitiveMechanism.CONSTRUAL_LEVEL,  # Too abstract
        ],
        message_tone="emotional",
        message_length="moderate",
        social_proof_weight="high",
        research_basis=[
            "Cialdini (2001) - Social proof",
            "Baumeister & Leary (1995) - Need to belong",
            "Matz et al. (2017) - High-E personality messaging",
        ]
    ),
    
    PsychologicalArchetype.SECURITY_FOCUSED: ArchetypeDefinition(
        archetype=PsychologicalArchetype.SECURITY_FOCUSED,
        name="Security-Focused",
        description="Safety-oriented individuals motivated by stability, protection, and risk avoidance. "
                   "Respond to messaging about reliability, guarantees, and worst-case prevention.",
        trait_profile=ArchetypeTraitProfile(
            openness=GaussianDistribution(mean=0.40, variance=0.03),
            conscientiousness=GaussianDistribution(mean=0.70, variance=0.02),
            extraversion=GaussianDistribution(mean=0.40, variance=0.03),
            agreeableness=GaussianDistribution(mean=0.55, variance=0.03),
            neuroticism=GaussianDistribution(mean=0.65, variance=0.02),
        ),
        regulatory_focus="prevention",
        construal_level="concrete",
        temporal_orientation="future",
        decision_style="analytical",
        risk_tolerance="low",
        social_influence_susceptibility="low",
        identity_salience="moderate",
        primary_mechanisms=[
            CognitiveMechanism.REGULATORY_FOCUS,
            CognitiveMechanism.TEMPORAL_CONSTRUAL,
            CognitiveMechanism.CONSTRUAL_LEVEL,
        ],
        secondary_mechanisms=[
            CognitiveMechanism.AUTOMATIC_EVALUATION,
            CognitiveMechanism.ATTENTION_DYNAMICS,
        ],
        avoid_mechanisms=[
            CognitiveMechanism.WANTING_LIKING,  # Too hedonic
            CognitiveMechanism.MIMETIC_DESIRE,  # Not socially driven
        ],
        message_tone="practical",
        message_length="detailed",
        social_proof_weight="low",
        research_basis=[
            "Higgins (1997) - Prevention focus",
            "Schwartz (1992) - Security values",
            "Matz et al. (2017) - High-N personality messaging",
        ]
    ),
    
    PsychologicalArchetype.HARMONY_SEEKER: ArchetypeDefinition(
        archetype=PsychologicalArchetype.HARMONY_SEEKER,
        name="Harmony Seeker",
        description="Balance-oriented individuals seeking comfort, peace, and positive relationships. "
                   "Respond to warm, reassuring messaging about comfort and well-being.",
        trait_profile=ArchetypeTraitProfile(
            openness=GaussianDistribution(mean=0.50, variance=0.03),
            conscientiousness=GaussianDistribution(mean=0.55, variance=0.03),
            extraversion=GaussianDistribution(mean=0.50, variance=0.03),
            agreeableness=GaussianDistribution(mean=0.75, variance=0.02),
            neuroticism=GaussianDistribution(mean=0.55, variance=0.03),
        ),
        regulatory_focus="balanced",
        construal_level="concrete",
        temporal_orientation="present",
        decision_style="intuitive",
        risk_tolerance="low",
        social_influence_susceptibility="moderate",
        identity_salience="moderate",
        primary_mechanisms=[
            CognitiveMechanism.AUTOMATIC_EVALUATION,
            CognitiveMechanism.MIMETIC_DESIRE,
            CognitiveMechanism.WANTING_LIKING,
        ],
        secondary_mechanisms=[
            CognitiveMechanism.IDENTITY_CONSTRUCTION,
            CognitiveMechanism.REGULATORY_FOCUS,
        ],
        avoid_mechanisms=[
            CognitiveMechanism.CONSTRUAL_LEVEL,  # Too analytical
        ],
        message_tone="emotional",
        message_length="moderate",
        social_proof_weight="moderate",
        research_basis=[
            "Schwartz (1992) - Benevolence values",
            "Costa & McCrae (1992) - High-A profiles",
            "Matz et al. (2017) - High-A personality messaging",
        ]
    ),
    
    PsychologicalArchetype.ANALYTICAL_THINKER: ArchetypeDefinition(
        archetype=PsychologicalArchetype.ANALYTICAL_THINKER,
        name="Analytical Thinker",
        description="Reason-oriented individuals who process information systematically. "
                   "Respond to logical, data-driven messaging with clear evidence.",
        trait_profile=ArchetypeTraitProfile(
            openness=GaussianDistribution(mean=0.65, variance=0.03),
            conscientiousness=GaussianDistribution(mean=0.70, variance=0.02),
            extraversion=GaussianDistribution(mean=0.35, variance=0.03),
            agreeableness=GaussianDistribution(mean=0.45, variance=0.03),
            neuroticism=GaussianDistribution(mean=0.40, variance=0.03),
        ),
        regulatory_focus="balanced",
        construal_level="abstract",
        temporal_orientation="future",
        decision_style="analytical",
        risk_tolerance="moderate",
        social_influence_susceptibility="low",
        identity_salience="moderate",
        primary_mechanisms=[
            CognitiveMechanism.CONSTRUAL_LEVEL,
            CognitiveMechanism.REGULATORY_FOCUS,
            CognitiveMechanism.TEMPORAL_CONSTRUAL,
        ],
        secondary_mechanisms=[
            CognitiveMechanism.ATTENTION_DYNAMICS,
            CognitiveMechanism.IDENTITY_CONSTRUCTION,
        ],
        avoid_mechanisms=[
            CognitiveMechanism.AUTOMATIC_EVALUATION,  # Too emotional
            CognitiveMechanism.MIMETIC_DESIRE,  # Not socially driven
        ],
        message_tone="rational",
        message_length="detailed",
        social_proof_weight="low",
        research_basis=[
            "Cacioppo & Petty (1982) - Need for cognition",
            "Epstein (1994) - Rational thinking style",
            "Hirsh et al. (2012) - Rational messaging",
        ]
    ),
    
    PsychologicalArchetype.SPONTANEOUS_EXPERIENCER: ArchetypeDefinition(
        archetype=PsychologicalArchetype.SPONTANEOUS_EXPERIENCER,
        name="Spontaneous Experiencer",
        description="Impulse-driven individuals who make quick, emotion-based decisions. "
                   "Respond to immediate, exciting, limited-time messaging.",
        trait_profile=ArchetypeTraitProfile(
            openness=GaussianDistribution(mean=0.65, variance=0.03),
            conscientiousness=GaussianDistribution(mean=0.35, variance=0.03),
            extraversion=GaussianDistribution(mean=0.70, variance=0.02),
            agreeableness=GaussianDistribution(mean=0.55, variance=0.03),
            neuroticism=GaussianDistribution(mean=0.55, variance=0.03),
        ),
        regulatory_focus="promotion",
        construal_level="concrete",
        temporal_orientation="present",
        decision_style="spontaneous",
        risk_tolerance="high",
        social_influence_susceptibility="high",
        identity_salience="moderate",
        primary_mechanisms=[
            CognitiveMechanism.AUTOMATIC_EVALUATION,
            CognitiveMechanism.WANTING_LIKING,
            CognitiveMechanism.ATTENTION_DYNAMICS,
        ],
        secondary_mechanisms=[
            CognitiveMechanism.MIMETIC_DESIRE,
            CognitiveMechanism.IDENTITY_CONSTRUCTION,
        ],
        avoid_mechanisms=[
            CognitiveMechanism.TEMPORAL_CONSTRUAL,  # Too future-focused
            CognitiveMechanism.CONSTRUAL_LEVEL,  # Too analytical
        ],
        message_tone="emotional",
        message_length="brief",
        social_proof_weight="high",
        research_basis=[
            "Rook (1987) - Impulse buying",
            "Baumeister (2002) - Self-control failure",
            "Matz et al. (2017) - Low-C personality messaging",
        ]
    ),
    
    PsychologicalArchetype.TRADITIONALIST: ArchetypeDefinition(
        archetype=PsychologicalArchetype.TRADITIONALIST,
        name="Traditionalist",
        description="Convention-oriented individuals who value established norms and traditions. "
                   "Respond to messaging about heritage, reliability, and social norms.",
        trait_profile=ArchetypeTraitProfile(
            openness=GaussianDistribution(mean=0.35, variance=0.03),
            conscientiousness=GaussianDistribution(mean=0.65, variance=0.03),
            extraversion=GaussianDistribution(mean=0.45, variance=0.03),
            agreeableness=GaussianDistribution(mean=0.60, variance=0.03),
            neuroticism=GaussianDistribution(mean=0.50, variance=0.03),
        ),
        regulatory_focus="prevention",
        construal_level="concrete",
        temporal_orientation="past",
        decision_style="analytical",
        risk_tolerance="low",
        social_influence_susceptibility="high",
        identity_salience="high",
        primary_mechanisms=[
            CognitiveMechanism.REGULATORY_FOCUS,
            CognitiveMechanism.MIMETIC_DESIRE,
            CognitiveMechanism.IDENTITY_CONSTRUCTION,
        ],
        secondary_mechanisms=[
            CognitiveMechanism.TEMPORAL_CONSTRUAL,
            CognitiveMechanism.AUTOMATIC_EVALUATION,
        ],
        avoid_mechanisms=[
            CognitiveMechanism.WANTING_LIKING,  # Too hedonic
        ],
        message_tone="practical",
        message_length="moderate",
        social_proof_weight="high",
        research_basis=[
            "Schwartz (1992) - Tradition values",
            "Costa & McCrae (1992) - Low-O profiles",
            "Hirsh et al. (2012) - Tradition messaging",
        ]
    ),
}


def get_archetype_definition(
    archetype: PsychologicalArchetype
) -> ArchetypeDefinition:
    """Get definition for an archetype."""
    return ARCHETYPE_DEFINITIONS.get(
        archetype,
        ARCHETYPE_DEFINITIONS[PsychologicalArchetype.HARMONY_SEEKER]  # Default
    )


def get_all_archetypes() -> List[ArchetypeDefinition]:
    """Get all archetype definitions."""
    return list(ARCHETYPE_DEFINITIONS.values())
```

---

## Archetype Detection Engine

```python
# =============================================================================
# ADAM Enhancement #13: Archetype Detection Engine
# Location: adam/cold_start/archetypes/detection.py
# =============================================================================

"""
Archetype Detection Engine for rapid psychological profiling.

Detects psychological archetypes from minimal signals using:
1. Behavioral pattern matching
2. Content preference inference
3. Demographic priors
4. Probabilistic classification
"""

from __future__ import annotations
from typing import Dict, List, Optional, Any, Tuple, Set
from datetime import datetime, timezone
from pydantic import BaseModel, Field, computed_field
import numpy as np
from scipy.spatial.distance import cosine
from scipy.special import softmax
import logging

from adam.cold_start.models.enums import (
    PersonalityTrait, CognitiveMechanism, PsychologicalArchetype, UserDataTier
)
from adam.cold_start.models.priors import GaussianDistribution
from adam.cold_start.archetypes.definitions import (
    ARCHETYPE_DEFINITIONS, ArchetypeDefinition, get_archetype_definition
)
from adam.cold_start.priors.contextual import (
    ContextualSignals, ContentCategory, SessionIntent, DeviceType
)

logger = logging.getLogger(__name__)


# =============================================================================
# DETECTION CONFIGURATION
# =============================================================================

class ArchetypeDetectionConfig(BaseModel):
    """Configuration for archetype detection."""
    
    # Confidence thresholds
    min_confidence_threshold: float = 0.3  # Minimum to assign archetype
    high_confidence_threshold: float = 0.7  # High confidence assignment
    
    # Detection parameters
    trait_weight: float = 0.4  # Weight for trait-based matching
    behavior_weight: float = 0.35  # Weight for behavioral signals
    content_weight: float = 0.25  # Weight for content preferences
    
    # Smoothing
    temperature: float = 1.5  # Softmax temperature (higher = more uniform)
    
    # Update parameters
    archetype_stability_window: int = 7  # Days before re-evaluating
    min_signals_for_detection: int = 3  # Minimum signals needed


class ArchetypeDetectionResult(BaseModel):
    """Result of archetype detection."""
    detected_archetype: Optional[PsychologicalArchetype] = None
    confidence: float = 0.0
    
    # All archetype probabilities
    probabilities: Dict[PsychologicalArchetype, float] = Field(default_factory=dict)
    
    # Top candidates
    top_candidates: List[Tuple[PsychologicalArchetype, float]] = Field(default_factory=list)
    
    # Evidence breakdown
    trait_evidence: Dict[PsychologicalArchetype, float] = Field(default_factory=dict)
    behavior_evidence: Dict[PsychologicalArchetype, float] = Field(default_factory=dict)
    content_evidence: Dict[PsychologicalArchetype, float] = Field(default_factory=dict)
    
    # Metadata
    signals_used: int = 0
    detection_method: str = "unknown"
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    @computed_field
    @property
    def is_confident(self) -> bool:
        return self.confidence >= 0.5
    
    @computed_field
    @property
    def is_highly_confident(self) -> bool:
        return self.confidence >= 0.7


# =============================================================================
# BEHAVIORAL SIGNAL MAPPINGS
# =============================================================================

# Content category â†’ archetype affinity
CONTENT_ARCHETYPE_AFFINITY: Dict[ContentCategory, Dict[PsychologicalArchetype, float]] = {
    ContentCategory.NEWS: {
        PsychologicalArchetype.ANALYTICAL_THINKER: 0.8,
        PsychologicalArchetype.SECURITY_FOCUSED: 0.7,
        PsychologicalArchetype.ACHIEVEMENT_DRIVEN: 0.5,
    },
    ContentCategory.ENTERTAINMENT: {
        PsychologicalArchetype.SPONTANEOUS_EXPERIENCER: 0.8,
        PsychologicalArchetype.NOVELTY_SEEKER: 0.7,
        PsychologicalArchetype.SOCIAL_CONNECTOR: 0.6,
        PsychologicalArchetype.HARMONY_SEEKER: 0.5,
    },
    ContentCategory.SPORTS: {
        PsychologicalArchetype.SOCIAL_CONNECTOR: 0.8,
        PsychologicalArchetype.ACHIEVEMENT_DRIVEN: 0.6,
        PsychologicalArchetype.TRADITIONALIST: 0.5,
    },
    ContentCategory.FINANCE: {
        PsychologicalArchetype.SECURITY_FOCUSED: 0.8,
        PsychologicalArchetype.ANALYTICAL_THINKER: 0.8,
        PsychologicalArchetype.ACHIEVEMENT_DRIVEN: 0.6,
    },
    ContentCategory.HEALTH: {
        PsychologicalArchetype.SECURITY_FOCUSED: 0.7,
        PsychologicalArchetype.HARMONY_SEEKER: 0.6,
        PsychologicalArchetype.ANALYTICAL_THINKER: 0.5,
    },
    ContentCategory.SHOPPING: {
        PsychologicalArchetype.SPONTANEOUS_EXPERIENCER: 0.7,
        PsychologicalArchetype.NOVELTY_SEEKER: 0.6,
        PsychologicalArchetype.SOCIAL_CONNECTOR: 0.5,
    },
    ContentCategory.SOCIAL: {
        PsychologicalArchetype.SOCIAL_CONNECTOR: 0.9,
        PsychologicalArchetype.SPONTANEOUS_EXPERIENCER: 0.6,
        PsychologicalArchetype.HARMONY_SEEKER: 0.5,
    },
    ContentCategory.GAMING: {
        PsychologicalArchetype.NOVELTY_SEEKER: 0.8,
        PsychologicalArchetype.SPONTANEOUS_EXPERIENCER: 0.7,
        PsychologicalArchetype.ACHIEVEMENT_DRIVEN: 0.5,
    },
    ContentCategory.EDUCATION: {
        PsychologicalArchetype.ANALYTICAL_THINKER: 0.8,
        PsychologicalArchetype.ACHIEVEMENT_DRIVEN: 0.7,
        PsychologicalArchetype.NOVELTY_SEEKER: 0.5,
    },
    ContentCategory.PRODUCTIVITY: {
        PsychologicalArchetype.ACHIEVEMENT_DRIVEN: 0.9,
        PsychologicalArchetype.ANALYTICAL_THINKER: 0.7,
        PsychologicalArchetype.SECURITY_FOCUSED: 0.5,
    },
}

# Session intent â†’ archetype affinity
SESSION_ARCHETYPE_AFFINITY: Dict[SessionIntent, Dict[PsychologicalArchetype, float]] = {
    SessionIntent.BROWSING: {
        PsychologicalArchetype.NOVELTY_SEEKER: 0.6,
        PsychologicalArchetype.SPONTANEOUS_EXPERIENCER: 0.6,
    },
    SessionIntent.RESEARCHING: {
        PsychologicalArchetype.ANALYTICAL_THINKER: 0.8,
        PsychologicalArchetype.SECURITY_FOCUSED: 0.6,
        PsychologicalArchetype.ACHIEVEMENT_DRIVEN: 0.5,
    },
    SessionIntent.BUYING: {
        PsychologicalArchetype.SPONTANEOUS_EXPERIENCER: 0.7,
        PsychologicalArchetype.ACHIEVEMENT_DRIVEN: 0.5,
    },
    SessionIntent.ENTERTAINING: {
        PsychologicalArchetype.HARMONY_SEEKER: 0.7,
        PsychologicalArchetype.SOCIAL_CONNECTOR: 0.6,
        PsychologicalArchetype.SPONTANEOUS_EXPERIENCER: 0.5,
    },
    SessionIntent.WORKING: {
        PsychologicalArchetype.ACHIEVEMENT_DRIVEN: 0.8,
        PsychologicalArchetype.ANALYTICAL_THINKER: 0.7,
    },
}


class ArchetypeDetectionEngine:
    """
    Engine for detecting psychological archetypes from available signals.
    """
    
    def __init__(self, config: Optional[ArchetypeDetectionConfig] = None):
        self.config = config or ArchetypeDetectionConfig()
        
        # Pre-compute archetype trait vectors for fast matching
        self._archetype_vectors: Dict[PsychologicalArchetype, np.ndarray] = {}
        for archetype, definition in ARCHETYPE_DEFINITIONS.items():
            self._archetype_vectors[archetype] = definition.trait_profile.to_vector()
    
    def detect_archetype(
        self,
        trait_estimates: Optional[Dict[PersonalityTrait, float]] = None,
        context: Optional[ContextualSignals] = None,
        content_history: Optional[List[ContentCategory]] = None,
        behavior_signals: Optional[Dict[str, Any]] = None
    ) -> ArchetypeDetectionResult:
        """
        Detect most likely archetype from available signals.
        """
        result = ArchetypeDetectionResult(detection_method="multi_signal")
        
        # Initialize uniform priors
        archetype_scores: Dict[PsychologicalArchetype, float] = {
            arch: 0.0 for arch in PsychologicalArchetype
        }
        
        signals_used = 0
        
        # 1. Trait-based evidence
        if trait_estimates:
            trait_evidence = self._compute_trait_evidence(trait_estimates)
            result.trait_evidence = trait_evidence
            for arch, score in trait_evidence.items():
                archetype_scores[arch] += score * self.config.trait_weight
            signals_used += 1
        
        # 2. Content-based evidence
        if context and context.content:
            content_evidence = self._compute_content_evidence(context.content.category)
            result.content_evidence = content_evidence
            for arch, score in content_evidence.items():
                archetype_scores[arch] += score * self.config.content_weight
            signals_used += 1
        
        # Content history
        if content_history:
            history_evidence = self._compute_content_history_evidence(content_history)
            for arch, score in history_evidence.items():
                archetype_scores[arch] += score * self.config.content_weight * 0.5
            signals_used += 1
        
        # 3. Behavior-based evidence
        if context and context.session_behavior:
            behavior_evidence = self._compute_behavior_evidence(context.session_behavior.intent)
            result.behavior_evidence = behavior_evidence
            for arch, score in behavior_evidence.items():
                archetype_scores[arch] += score * self.config.behavior_weight
            signals_used += 1
        
        if behavior_signals:
            custom_evidence = self._compute_custom_behavior_evidence(behavior_signals)
            for arch, score in custom_evidence.items():
                archetype_scores[arch] += score * self.config.behavior_weight * 0.5
            signals_used += 1
        
        result.signals_used = signals_used
        
        # Check minimum signals
        if signals_used < self.config.min_signals_for_detection:
            result.detection_method = "insufficient_signals"
            return result
        
        # Convert to probabilities using softmax
        scores_array = np.array([archetype_scores[arch] for arch in PsychologicalArchetype])
        probs_array = softmax(scores_array / self.config.temperature)
        
        result.probabilities = {
            arch: float(prob)
            for arch, prob in zip(PsychologicalArchetype, probs_array)
        }
        
        # Get top candidates
        sorted_archetypes = sorted(
            result.probabilities.items(),
            key=lambda x: x[1],
            reverse=True
        )
        result.top_candidates = sorted_archetypes[:3]
        
        # Determine detected archetype
        best_archetype, best_prob = sorted_archetypes[0]
        
        if best_prob >= self.config.min_confidence_threshold:
            result.detected_archetype = best_archetype
            result.confidence = best_prob
        else:
            result.confidence = best_prob
        
        return result
    
    def _compute_trait_evidence(
        self,
        trait_estimates: Dict[PersonalityTrait, float]
    ) -> Dict[PsychologicalArchetype, float]:
        """Compute archetype evidence from trait estimates."""
        # Convert trait estimates to vector
        user_vector = np.array([
            trait_estimates.get(PersonalityTrait.OPENNESS, 0.5),
            trait_estimates.get(PersonalityTrait.CONSCIENTIOUSNESS, 0.5),
            trait_estimates.get(PersonalityTrait.EXTRAVERSION, 0.5),
            trait_estimates.get(PersonalityTrait.AGREEABLENESS, 0.5),
            trait_estimates.get(PersonalityTrait.NEUROTICISM, 0.5),
        ])
        
        evidence = {}
        for archetype, arch_vector in self._archetype_vectors.items():
            # Cosine similarity (1 - cosine distance)
            similarity = 1 - cosine(user_vector, arch_vector)
            evidence[archetype] = max(0, similarity)
        
        return evidence
    
    def _compute_content_evidence(
        self,
        category: ContentCategory
    ) -> Dict[PsychologicalArchetype, float]:
        """Compute archetype evidence from content category."""
        evidence = {arch: 0.0 for arch in PsychologicalArchetype}
        
        if category in CONTENT_ARCHETYPE_AFFINITY:
            for arch, affinity in CONTENT_ARCHETYPE_AFFINITY[category].items():
                evidence[arch] = affinity
        
        return evidence
    
    def _compute_content_history_evidence(
        self,
        history: List[ContentCategory]
    ) -> Dict[PsychologicalArchetype, float]:
        """Compute archetype evidence from content history."""
        evidence = {arch: 0.0 for arch in PsychologicalArchetype}
        
        if not history:
            return evidence
        
        # Count category occurrences
        category_counts: Dict[ContentCategory, int] = {}
        for cat in history:
            category_counts[cat] = category_counts.get(cat, 0) + 1
        
        # Aggregate evidence
        for cat, count in category_counts.items():
            weight = min(1.0, count / 5)  # Cap at 5 observations
            if cat in CONTENT_ARCHETYPE_AFFINITY:
                for arch, affinity in CONTENT_ARCHETYPE_AFFINITY[cat].items():
                    evidence[arch] += affinity * weight
        
        # Normalize
        max_ev = max(evidence.values()) if evidence.values() else 1.0
        if max_ev > 0:
            evidence = {k: v / max_ev for k, v in evidence.items()}
        
        return evidence
    
    def _compute_behavior_evidence(
        self,
        intent: SessionIntent
    ) -> Dict[PsychologicalArchetype, float]:
        """Compute archetype evidence from session intent."""
        evidence = {arch: 0.0 for arch in PsychologicalArchetype}
        
        if intent in SESSION_ARCHETYPE_AFFINITY:
            for arch, affinity in SESSION_ARCHETYPE_AFFINITY[intent].items():
                evidence[arch] = affinity
        
        return evidence
    
    def _compute_custom_behavior_evidence(
        self,
        signals: Dict[str, Any]
    ) -> Dict[PsychologicalArchetype, float]:
        """Compute archetype evidence from custom behavior signals."""
        evidence = {arch: 0.0 for arch in PsychologicalArchetype}
        
        # High engagement â†’ Achievement or Analytical
        engagement = signals.get("engagement_score", 0.5)
        if engagement > 0.7:
            evidence[PsychologicalArchetype.ACHIEVEMENT_DRIVEN] += 0.3
            evidence[PsychologicalArchetype.ANALYTICAL_THINKER] += 0.2
        
        # Quick decisions â†’ Spontaneous
        decision_speed = signals.get("decision_speed", 0.5)
        if decision_speed > 0.7:
            evidence[PsychologicalArchetype.SPONTANEOUS_EXPERIENCER] += 0.4
        elif decision_speed < 0.3:
            evidence[PsychologicalArchetype.ANALYTICAL_THINKER] += 0.3
            evidence[PsychologicalArchetype.SECURITY_FOCUSED] += 0.2
        
        # Social sharing â†’ Social Connector
        social_activity = signals.get("social_sharing", 0.0)
        if social_activity > 0.5:
            evidence[PsychologicalArchetype.SOCIAL_CONNECTOR] += 0.4
        
        # Price sensitivity â†’ Security-Focused
        price_sensitivity = signals.get("price_sensitivity", 0.5)
        if price_sensitivity > 0.7:
            evidence[PsychologicalArchetype.SECURITY_FOCUSED] += 0.3
            evidence[PsychologicalArchetype.TRADITIONALIST] += 0.2
        
        return evidence


# =============================================================================
# ARCHETYPE MECHANISM RESPONSIVENESS
# =============================================================================

class ArchetypeMechanismResponsiveness:
    """
    Maps archetype to mechanism effectiveness predictions.
    """
    
    def __init__(self):
        # Pre-compute from definitions
        self._responsiveness_map: Dict[
            PsychologicalArchetype, Dict[CognitiveMechanism, float]
        ] = {}
        
        for archetype, definition in ARCHETYPE_DEFINITIONS.items():
            self._responsiveness_map[archetype] = {}
            
            # Primary mechanisms: high responsiveness
            for mech in definition.primary_mechanisms:
                self._responsiveness_map[archetype][mech] = 0.8
            
            # Secondary mechanisms: moderate responsiveness
            for mech in definition.secondary_mechanisms:
                self._responsiveness_map[archetype][mech] = 0.6
            
            # Avoid mechanisms: low responsiveness
            for mech in definition.avoid_mechanisms:
                self._responsiveness_map[archetype][mech] = 0.3
            
            # Fill in remaining with neutral
            for mech in CognitiveMechanism:
                if mech not in self._responsiveness_map[archetype]:
                    self._responsiveness_map[archetype][mech] = 0.5
    
    def get_responsiveness(
        self,
        archetype: PsychologicalArchetype,
        mechanism: CognitiveMechanism
    ) -> float:
        """Get expected responsiveness for archetype-mechanism pair."""
        if archetype not in self._responsiveness_map:
            return 0.5
        return self._responsiveness_map[archetype].get(mechanism, 0.5)
    
    def get_all_responsiveness(
        self,
        archetype: PsychologicalArchetype
    ) -> Dict[CognitiveMechanism, float]:
        """Get all mechanism responsiveness for an archetype."""
        if archetype not in self._responsiveness_map:
            return {m: 0.5 for m in CognitiveMechanism}
        return self._responsiveness_map[archetype].copy()
    
    def get_top_mechanisms(
        self,
        archetype: PsychologicalArchetype,
        n: int = 3
    ) -> List[Tuple[CognitiveMechanism, float]]:
        """Get top N mechanisms for an archetype."""
        responsiveness = self.get_all_responsiveness(archetype)
        sorted_mechs = sorted(
            responsiveness.items(),
            key=lambda x: x[1],
            reverse=True
        )
        return sorted_mechs[:n]


# =============================================================================
# ARCHETYPE EVOLUTION TRACKING
# =============================================================================

class ArchetypeEvolutionEvent(BaseModel):
    """Event tracking archetype assignment change."""
    user_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    previous_archetype: Optional[PsychologicalArchetype] = None
    new_archetype: PsychologicalArchetype
    
    previous_confidence: float = 0.0
    new_confidence: float = 0.0
    
    trigger: str  # "new_detection", "confidence_increase", "profile_update"
    signals_used: int = 0


class ArchetypeEvolutionTracker:
    """
    Tracks archetype assignments over time.
    
    Monitors:
    - Archetype stability
    - Confidence progression
    - Evolution patterns
    """
    
    def __init__(self, stability_window_days: int = 7):
        self.stability_window_days = stability_window_days
        
        # In-memory tracking (would be backed by Neo4j in production)
        self._user_archetypes: Dict[str, List[ArchetypeEvolutionEvent]] = {}
    
    def record_detection(
        self,
        user_id: str,
        detection_result: ArchetypeDetectionResult
    ) -> Optional[ArchetypeEvolutionEvent]:
        """
        Record archetype detection and determine if assignment changed.
        """
        if detection_result.detected_archetype is None:
            return None
        
        # Get current assignment
        current = self.get_current_archetype(user_id)
        
        # Determine if this is a change
        if current is None:
            # First detection
            event = ArchetypeEvolutionEvent(
                user_id=user_id,
                previous_archetype=None,
                new_archetype=detection_result.detected_archetype,
                previous_confidence=0.0,
                new_confidence=detection_result.confidence,
                trigger="new_detection",
                signals_used=detection_result.signals_used
            )
        elif current.archetype != detection_result.detected_archetype:
            # Archetype changed
            event = ArchetypeEvolutionEvent(
                user_id=user_id,
                previous_archetype=current.archetype,
                new_archetype=detection_result.detected_archetype,
                previous_confidence=current.confidence,
                new_confidence=detection_result.confidence,
                trigger="archetype_change",
                signals_used=detection_result.signals_used
            )
        elif detection_result.confidence > current.confidence + 0.1:
            # Confidence increased significantly
            event = ArchetypeEvolutionEvent(
                user_id=user_id,
                previous_archetype=current.archetype,
                new_archetype=detection_result.detected_archetype,
                previous_confidence=current.confidence,
                new_confidence=detection_result.confidence,
                trigger="confidence_increase",
                signals_used=detection_result.signals_used
            )
        else:
            # No significant change
            return None
        
        # Record event
        if user_id not in self._user_archetypes:
            self._user_archetypes[user_id] = []
        self._user_archetypes[user_id].append(event)
        
        return event
    
    def get_current_archetype(
        self,
        user_id: str
    ) -> Optional[ArchetypeEvolutionEvent]:
        """Get current archetype assignment for user."""
        if user_id not in self._user_archetypes:
            return None
        
        events = self._user_archetypes[user_id]
        if not events:
            return None
        
        return events[-1]
    
    def get_archetype_stability(
        self,
        user_id: str
    ) -> float:
        """
        Calculate archetype stability score.
        
        Returns 0-1 where 1 means archetype has been stable.
        """
        if user_id not in self._user_archetypes:
            return 0.0
        
        events = self._user_archetypes[user_id]
        if len(events) <= 1:
            return 1.0 if events else 0.0
        
        # Count archetype changes
        changes = sum(
            1 for i in range(1, len(events))
            if events[i].new_archetype != events[i-1].new_archetype
        )
        
        # Stability decreases with more changes
        stability = 1.0 / (1.0 + changes)
        
        return stability
    
    def get_evolution_history(
        self,
        user_id: str,
        limit: int = 10
    ) -> List[ArchetypeEvolutionEvent]:
        """Get archetype evolution history for user."""
        if user_id not in self._user_archetypes:
            return []
        
        return self._user_archetypes[user_id][-limit:]
```

---

# SECTION F: PROGRESSIVE PROFILING ENGINE

## Bayesian Update Engine

```python
# =============================================================================
# ADAM Enhancement #13: Bayesian Update Engine
# Location: adam/cold_start/profiling/bayesian_engine.py
# =============================================================================

"""
Bayesian Update Engine for progressive profile development.

Implements efficient conjugate prior updates for personality traits
and mechanism effectiveness tracking.
"""

from __future__ import annotations
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone
from pydantic import BaseModel, Field, computed_field
import numpy as np
from scipy import stats
import math
import logging

from adam.cold_start.models.enums import (
    PersonalityTrait, CognitiveMechanism, UserDataTier, PriorSource
)
from adam.cold_start.models.priors import (
    BetaDistribution, GaussianDistribution, PsychologicalPrior
)

logger = logging.getLogger(__name__)


# =============================================================================
# BAYESIAN UPDATE MODELS
# =============================================================================

class BayesianUpdateConfig(BaseModel):
    """Configuration for Bayesian updates."""
    
    # Learning rates
    trait_learning_rate: float = 1.0  # Full Bayesian for traits
    mechanism_learning_rate: float = 1.0  # Full Bayesian for mechanisms
    
    # Update weighting
    recency_decay: float = 0.95  # Decay for older observations
    confidence_threshold: float = 0.8  # Stop updating at high confidence
    
    # Prior strength
    prior_pseudo_samples: float = 5.0  # Effective samples in prior
    
    # Variance floor
    min_variance: float = 0.001  # Prevent over-confidence


class TraitUpdateResult(BaseModel):
    """Result of trait Bayesian update."""
    trait: PersonalityTrait
    
    # Prior
    prior_mean: float
    prior_variance: float
    
    # Observation
    observation: float
    observation_confidence: float
    
    # Posterior
    posterior_mean: float
    posterior_variance: float
    
    # Change
    mean_delta: float
    variance_delta: float
    
    # Metadata
    effective_samples: float
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class MechanismUpdateResult(BaseModel):
    """Result of mechanism Bayesian update."""
    mechanism: CognitiveMechanism
    
    # Prior
    prior_alpha: float
    prior_beta: float
    prior_mean: float
    
    # Observation
    success: bool
    weight: float = 1.0
    
    # Posterior
    posterior_alpha: float
    posterior_beta: float
    posterior_mean: float
    
    # Change
    mean_delta: float
    
    # Metadata
    total_observations: int
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ProfileUpdateResult(BaseModel):
    """Complete profile update result."""
    user_id: str
    
    trait_updates: List[TraitUpdateResult] = Field(default_factory=list)
    mechanism_updates: List[MechanismUpdateResult] = Field(default_factory=list)
    
    # Overall profile change
    total_information_gain: float = 0.0
    confidence_delta: float = 0.0
    
    # Tier transition
    previous_tier: UserDataTier = UserDataTier.TIER_0_ANONYMOUS_NEW
    new_tier: UserDataTier = UserDataTier.TIER_0_ANONYMOUS_NEW
    tier_changed: bool = False
    
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# =============================================================================
# BAYESIAN UPDATE ENGINE
# =============================================================================

class BayesianUpdateEngine:
    """
    Engine for performing Bayesian updates on user profiles.
    
    Implements:
    1. Conjugate prior updates (Gaussian-Gaussian for traits, Beta-Binomial for mechanisms)
    2. Information gain tracking
    3. Confidence calibration
    4. Tier progression logic
    """
    
    def __init__(self, config: Optional[BayesianUpdateConfig] = None):
        self.config = config or BayesianUpdateConfig()
    
    # =========================================================================
    # TRAIT UPDATES (Gaussian-Gaussian Conjugate)
    # =========================================================================
    
    def update_trait(
        self,
        prior: GaussianDistribution,
        observation: float,
        observation_variance: float
    ) -> Tuple[GaussianDistribution, TraitUpdateResult]:
        """
        Update trait estimate using Gaussian-Gaussian conjugate update.
        
        Args:
            prior: Current prior distribution
            observation: Observed trait value (0-1)
            observation_variance: Uncertainty in observation
            
        Returns:
            (posterior distribution, update details)
        """
        # Precision-weighted update
        prior_precision = 1.0 / prior.variance
        obs_precision = 1.0 / observation_variance
        
        posterior_precision = prior_precision + obs_precision
        posterior_variance = 1.0 / posterior_precision
        
        posterior_mean = (
            prior_precision * prior.mean + obs_precision * observation
        ) / posterior_precision
        
        # Enforce variance floor
        posterior_variance = max(posterior_variance, self.config.min_variance)
        
        # Clip mean to valid range
        posterior_mean = np.clip(posterior_mean, 0.0, 1.0)
        
        posterior = GaussianDistribution(
            mean=float(posterior_mean),
            variance=float(posterior_variance)
        )
        
        # Create result
        result = TraitUpdateResult(
            trait=PersonalityTrait.OPENNESS,  # Will be set by caller
            prior_mean=prior.mean,
            prior_variance=prior.variance,
            observation=observation,
            observation_confidence=1.0 / observation_variance,
            posterior_mean=posterior.mean,
            posterior_variance=posterior.variance,
            mean_delta=posterior.mean - prior.mean,
            variance_delta=posterior.variance - prior.variance,
            effective_samples=prior_precision + obs_precision
        )
        
        return posterior, result
    
    def update_all_traits(
        self,
        priors: Dict[PersonalityTrait, GaussianDistribution],
        observations: Dict[PersonalityTrait, Tuple[float, float]]  # (value, variance)
    ) -> Tuple[Dict[PersonalityTrait, GaussianDistribution], List[TraitUpdateResult]]:
        """
        Update all traits with observations.
        """
        posteriors = {}
        results = []
        
        for trait in PersonalityTrait:
            if trait in observations:
                obs_value, obs_variance = observations[trait]
                prior = priors.get(trait, GaussianDistribution(mean=0.5, variance=0.0625))
                
                posterior, result = self.update_trait(prior, obs_value, obs_variance)
                result.trait = trait
                
                posteriors[trait] = posterior
                results.append(result)
            elif trait in priors:
                posteriors[trait] = priors[trait]
        
        return posteriors, results
    
    # =========================================================================
    # MECHANISM UPDATES (Beta-Binomial Conjugate)
    # =========================================================================
    
    def update_mechanism(
        self,
        prior: BetaDistribution,
        success: bool,
        weight: float = 1.0
    ) -> Tuple[BetaDistribution, MechanismUpdateResult]:
        """
        Update mechanism effectiveness using Beta-Binomial conjugate update.
        
        Args:
            prior: Current Beta prior
            success: Whether the mechanism led to conversion
            weight: Update weight (for decay or importance)
            
        Returns:
            (posterior distribution, update details)
        """
        weighted_update = weight * self.config.mechanism_learning_rate
        
        if success:
            posterior_alpha = prior.alpha + weighted_update
            posterior_beta = prior.beta
        else:
            posterior_alpha = prior.alpha
            posterior_beta = prior.beta + weighted_update
        
        posterior = BetaDistribution(
            alpha=posterior_alpha,
            beta=posterior_beta
        )
        
        result = MechanismUpdateResult(
            mechanism=CognitiveMechanism.CONSTRUAL_LEVEL,  # Will be set by caller
            prior_alpha=prior.alpha,
            prior_beta=prior.beta,
            prior_mean=prior.mean,
            success=success,
            weight=weight,
            posterior_alpha=posterior.alpha,
            posterior_beta=posterior.beta,
            posterior_mean=posterior.mean,
            mean_delta=posterior.mean - prior.mean,
            total_observations=int(posterior.alpha + posterior.beta - 2)
        )
        
        return posterior, result
    
    def update_all_mechanisms(
        self,
        priors: Dict[CognitiveMechanism, BetaDistribution],
        outcomes: Dict[CognitiveMechanism, Tuple[bool, float]]  # (success, weight)
    ) -> Tuple[Dict[CognitiveMechanism, BetaDistribution], List[MechanismUpdateResult]]:
        """
        Update all mechanisms with outcomes.
        """
        posteriors = {}
        results = []
        
        for mech in CognitiveMechanism:
            if mech in outcomes:
                success, weight = outcomes[mech]
                prior = priors.get(mech, BetaDistribution(alpha=1.0, beta=1.0))
                
                posterior, result = self.update_mechanism(prior, success, weight)
                result.mechanism = mech
                
                posteriors[mech] = posterior
                results.append(result)
            elif mech in priors:
                posteriors[mech] = priors[mech]
        
        return posteriors, results
    
    # =========================================================================
    # INFORMATION GAIN
    # =========================================================================
    
    def compute_information_gain(
        self,
        prior: GaussianDistribution,
        posterior: GaussianDistribution
    ) -> float:
        """
        Compute KL divergence between prior and posterior (information gain).
        """
        # KL divergence for Gaussians
        kl = (
            math.log(math.sqrt(prior.variance) / math.sqrt(posterior.variance)) +
            (posterior.variance + (posterior.mean - prior.mean) ** 2) / (2 * prior.variance) -
            0.5
        )
        return max(0, kl)
    
    def compute_total_information_gain(
        self,
        trait_results: List[TraitUpdateResult],
        mechanism_results: List[MechanismUpdateResult]
    ) -> float:
        """
        Compute total information gain from all updates.
        """
        total = 0.0
        
        # Trait information gain
        for result in trait_results:
            prior = GaussianDistribution(mean=result.prior_mean, variance=result.prior_variance)
            posterior = GaussianDistribution(mean=result.posterior_mean, variance=result.posterior_variance)
            total += self.compute_information_gain(prior, posterior)
        
        # Mechanism information gain (approximation for Beta distributions)
        for result in mechanism_results:
            # Use variance reduction as proxy for information gain
            prior_var = (result.prior_alpha * result.prior_beta) / (
                (result.prior_alpha + result.prior_beta) ** 2 *
                (result.prior_alpha + result.prior_beta + 1)
            )
            posterior_var = (result.posterior_alpha * result.posterior_beta) / (
                (result.posterior_alpha + result.posterior_beta) ** 2 *
                (result.posterior_alpha + result.posterior_beta + 1)
            )
            if prior_var > 0:
                total += max(0, (prior_var - posterior_var) / prior_var)
        
        return total


# =============================================================================
# CONFIDENCE CALIBRATION
# =============================================================================

class ConfidenceCalibrator:
    """
    Calibrates profile confidence based on observations and accuracy.
    """
    
    def __init__(self, target_calibration: float = 0.1):
        """
        Args:
            target_calibration: Target calibration error (lower is better)
        """
        self.target_calibration = target_calibration
        
        # Calibration tracking
        self._predictions: List[Tuple[float, bool]] = []
    
    def compute_profile_confidence(
        self,
        trait_variances: Dict[PersonalityTrait, float],
        mechanism_variances: Dict[CognitiveMechanism, float],
        observation_count: int
    ) -> float:
        """
        Compute overall profile confidence.
        """
        # Average trait confidence (inverse of variance)
        trait_confidences = [1.0 / (1.0 + v * 10) for v in trait_variances.values()]
        avg_trait_conf = np.mean(trait_confidences) if trait_confidences else 0.5
        
        # Average mechanism confidence
        mech_confidences = [1.0 / (1.0 + v * 10) for v in mechanism_variances.values()]
        avg_mech_conf = np.mean(mech_confidences) if mech_confidences else 0.5
        
        # Observation-based confidence
        obs_conf = min(1.0, observation_count / 50)
        
        # Weighted combination
        overall = avg_trait_conf * 0.4 + avg_mech_conf * 0.3 + obs_conf * 0.3
        
        return float(overall)
    
    def record_prediction(self, confidence: float, correct: bool) -> None:
        """Record prediction for calibration tracking."""
        self._predictions.append((confidence, correct))
        
        # Keep last 1000
        if len(self._predictions) > 1000:
            self._predictions = self._predictions[-1000:]
    
    def get_calibration_error(self) -> float:
        """
        Compute Expected Calibration Error (ECE).
        """
        if len(self._predictions) < 10:
            return 0.5  # Unknown
        
        # Bin predictions by confidence
        n_bins = 10
        bins = [[] for _ in range(n_bins)]
        
        for conf, correct in self._predictions:
            bin_idx = min(int(conf * n_bins), n_bins - 1)
            bins[bin_idx].append((conf, 1.0 if correct else 0.0))
        
        # Compute ECE
        ece = 0.0
        total = len(self._predictions)
        
        for bin_predictions in bins:
            if not bin_predictions:
                continue
            
            avg_conf = np.mean([p[0] for p in bin_predictions])
            avg_acc = np.mean([p[1] for p in bin_predictions])
            bin_size = len(bin_predictions)
            
            ece += (bin_size / total) * abs(avg_acc - avg_conf)
        
        return ece


# =============================================================================
# INFORMATION-GAIN EXPLORATION
# =============================================================================

class InformationGainExplorer:
    """
    Selects actions that maximize expected information gain.
    """
    
    def __init__(self, exploration_rate: float = 0.2):
        self.exploration_rate = exploration_rate
    
    def compute_expected_info_gain(
        self,
        prior: BetaDistribution
    ) -> float:
        """
        Compute expected information gain from observing this mechanism.
        """
        a, b = prior.alpha, prior.beta
        p = a / (a + b)  # Current mean
        
        # Expected posterior after success/failure
        post_success = BetaDistribution(alpha=a+1, beta=b)
        post_failure = BetaDistribution(alpha=a, beta=b+1)
        
        # KL divergences
        kl_success = self._beta_kl(prior, post_success)
        kl_failure = self._beta_kl(prior, post_failure)
        
        # Expected info gain (weighted by outcome probabilities)
        expected_gain = p * kl_success + (1 - p) * kl_failure
        
        return expected_gain
    
    def _beta_kl(self, p: BetaDistribution, q: BetaDistribution) -> float:
        """Compute KL divergence between two Beta distributions."""
        from scipy.special import digamma, gammaln
        
        kl = (
            gammaln(p.alpha + p.beta) - gammaln(p.alpha) - gammaln(p.beta) -
            (gammaln(q.alpha + q.beta) - gammaln(q.alpha) - gammaln(q.beta)) +
            (p.alpha - q.alpha) * digamma(p.alpha) +
            (p.beta - q.beta) * digamma(p.beta) +
            (q.alpha - p.alpha + q.beta - p.beta) * digamma(p.alpha + p.beta)
        )
        return max(0, kl)
    
    def rank_mechanisms_by_info_gain(
        self,
        priors: Dict[CognitiveMechanism, BetaDistribution]
    ) -> List[Tuple[CognitiveMechanism, float]]:
        """
        Rank mechanisms by expected information gain.
        """
        gains = [
            (mech, self.compute_expected_info_gain(prior))
            for mech, prior in priors.items()
        ]
        
        gains.sort(key=lambda x: x[1], reverse=True)
        return gains
    
    def should_explore(
        self,
        best_expected_value: float,
        best_info_gain: float,
        tier: UserDataTier
    ) -> bool:
        """
        Decide whether to explore (maximize learning) vs exploit (maximize reward).
        """
        # Higher exploration for cold users
        tier_bonus = {
            UserDataTier.TIER_0_ANONYMOUS_NEW: 0.3,
            UserDataTier.TIER_1_ANONYMOUS_SESSION: 0.2,
            UserDataTier.TIER_2_REGISTERED_MINIMAL: 0.15,
            UserDataTier.TIER_3_REGISTERED_SPARSE: 0.1,
            UserDataTier.TIER_4_REGISTERED_MODERATE: 0.05,
            UserDataTier.TIER_5_PROFILED_FULL: 0.0,
        }.get(tier, 0.1)
        
        explore_prob = self.exploration_rate + tier_bonus
        
        # Also factor in info gain magnitude
        if best_info_gain > 0.5:
            explore_prob += 0.1
        
        return np.random.random() < explore_prob
```

This completes Section E foundations. Due to length, I'll continue with the remaining sections.
