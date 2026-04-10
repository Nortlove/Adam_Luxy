"""
ADAM Review Intelligence System
===============================

The Cookie-Less Psychological Intelligence Infrastructure

This system extracts, models, and serves psychological intelligence from review data
to power targeting across the advertising ecosystem:

- DSP Layer (StackAdapt): Helps demand-side deliver better outcomes
- SSP Layer (iHeart): Makes supply inventory more valuable through better targeting  
- Agency Layer (WPP): Embeds intelligence across multiple touchpoints

Each dataset has its own:
1. EXTRACTOR - Pulls psychological signals specific to that data source
2. MODELER - Creates structured intelligence models
3. INTEGRATOR - Feeds the three machines (Graph, LangGraph, AoT)

The Cookie Crisis Solution:
- No tracking required - inference from content and context
- Privacy-first - works with anonymized/aggregated data
- First-party friendly - enhances publisher/platform data
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum


class DataSource(str, Enum):
    """All supported review data sources."""
    AMAZON = "amazon"
    GOOGLE_LOCAL = "google_local"
    YELP = "yelp"
    TWITTER_MENTAL_HEALTH = "twitter_mental_health"
    STEAM_GAMING = "steam_gaming"
    SEPHORA_BEAUTY = "sephora_beauty"
    MOVIELENS_GENOME = "movielens_genome"
    PODCAST = "podcast"
    AIRLINE = "airline"
    AUTOMOTIVE = "automotive"
    ROTTEN_TOMATOES = "rotten_tomatoes"
    HOTEL = "hotel"
    RESTAURANT = "restaurant"
    BH_PHOTO = "bh_photo"
    TRUSTPILOT = "trustpilot"
    NETFLIX = "netflix"


class IntelligenceLayer(str, Enum):
    """Which ecosystem layer this intelligence serves."""
    DSP = "dsp"  # Demand-side platforms (StackAdapt, The Trade Desk)
    SSP = "ssp"  # Supply-side platforms (iHeart, Spotify)
    AGENCY = "agency"  # Agencies (WPP, Publicis, Omnicom)
    ALL = "all"  # Universal intelligence


@dataclass
class PsychologicalSignal:
    """A single psychological signal extracted from review data."""
    signal_type: str  # e.g., "archetype", "mechanism_receptivity", "emotional_state"
    signal_name: str  # e.g., "achiever", "social_proof", "anxious"
    confidence: float  # 0.0 to 1.0
    source: DataSource
    context: Dict[str, Any]  # Additional context (location, category, etc.)
    
    # Which layers can use this signal
    applicable_layers: List[IntelligenceLayer]
    
    # How to use in each machine
    graph_node_type: Optional[str] = None
    graph_edge_type: Optional[str] = None
    langgraph_prior_key: Optional[str] = None
    atom_injection_target: Optional[str] = None


@dataclass
class AudienceSegment:
    """A targetable audience segment derived from review intelligence."""
    segment_id: str
    segment_name: str
    description: str
    
    # Psychological profile
    archetypes: Dict[str, float]  # archetype -> strength
    mechanisms: Dict[str, float]  # mechanism -> receptivity
    emotional_baseline: Dict[str, float]  # emotion -> typical level
    
    # Targeting criteria
    geographic_affinity: Optional[Dict[str, float]] = None  # location -> affinity
    category_affinity: Optional[Dict[str, float]] = None  # category -> affinity
    temporal_patterns: Optional[Dict[str, float]] = None  # time_slot -> activity
    
    # Business value
    estimated_reach: Optional[int] = None
    conversion_propensity: Optional[float] = None
    
    # Source attribution
    primary_source: DataSource
    supporting_sources: List[DataSource]


@dataclass
class ContextualSignal:
    """A contextual signal for cookie-less targeting."""
    signal_id: str
    
    # What context this describes
    context_type: str  # "page_content", "app_category", "audio_format", "location"
    context_value: str  # The actual context
    
    # Psychological mapping
    archetype_affinity: Dict[str, float]
    mechanism_effectiveness: Dict[str, float]
    emotional_resonance: Dict[str, float]
    
    # Source and confidence
    source: DataSource
    confidence: float
    sample_size: int  # How many reviews inform this


# Export key components
__all__ = [
    "DataSource",
    "IntelligenceLayer", 
    "PsychologicalSignal",
    "AudienceSegment",
    "ContextualSignal",
]
