# =============================================================================
# ADAM iHeart Station Models
# Location: adam/platform/iheart/models/station.py
# =============================================================================

"""
STATION MODELS

Radio stations are the highest-level content organization in iHeart.
Each station has demographic and psychographic characteristics that
inform listener profiling.

Key insight: Station format is a strong prior for personality.
CHR listeners tend to be high extraversion, while Classical
listeners tend to be high openness.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


# =============================================================================
# STATION FORMAT ENUM
# =============================================================================

class StationFormat(str, Enum):
    """Radio station formats with psychological implications."""
    
    CHR = "CHR"                     # Contemporary Hit Radio
    HOT_AC = "Hot_AC"               # Hot Adult Contemporary
    AC = "AC"                       # Adult Contemporary
    COUNTRY = "Country"
    ROCK = "Rock"
    CLASSIC_ROCK = "Classic_Rock"
    ALTERNATIVE = "Alternative"
    URBAN = "Urban"
    URBAN_AC = "Urban_AC"
    RHYTHMIC_CHR = "Rhythmic_CHR"
    CLASSICAL = "Classical"
    JAZZ = "Jazz"
    NEWS_TALK = "News_Talk"
    SPORTS = "Sports"
    SPANISH = "Spanish"
    RELIGIOUS = "Religious"
    OLDIES = "Oldies"
    CLASSIC_HITS = "Classic_Hits"
    AAA = "AAA"                     # Adult Album Alternative
    PODCAST = "Podcast"             # Podcast-only channel


# =============================================================================
# PSYCHOGRAPHIC PROFILE
# =============================================================================

class BigFiveDistribution(BaseModel):
    """Big Five distribution for a population (station listeners)."""
    
    mean: float = Field(ge=0.0, le=1.0)
    std: float = Field(ge=0.0, le=0.5, default=0.15)


class StationPsychProfile(BaseModel):
    """
    Psychographic profile for a station's listener base.
    
    This is learned from actual listener behavior and updated continuously.
    Initial values come from format-level priors.
    """
    
    # Big Five distributions
    openness: BigFiveDistribution
    conscientiousness: BigFiveDistribution
    extraversion: BigFiveDistribution
    agreeableness: BigFiveDistribution
    neuroticism: BigFiveDistribution
    
    # Regulatory focus
    promotion_tendency: float = Field(ge=0.0, le=1.0)
    prevention_tendency: float = Field(ge=0.0, le=1.0)
    
    # Construal level
    abstract_tendency: float = Field(ge=0.0, le=1.0, default=0.5)
    
    # Primary psychological mechanisms for this audience
    primary_mechanisms: List[str] = Field(default_factory=list)
    
    # Sample basis
    listener_sample_size: int = Field(default=0, ge=0)
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    
    # Timestamps
    computed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# =============================================================================
# STATION MODEL
# =============================================================================

class Station(BaseModel):
    """
    A radio station or streaming channel.
    
    Stations are the primary content aggregation unit in iHeart.
    They carry format-level psychological priors that inform
    cold-start and profile enrichment.
    """
    
    # Identity
    station_id: str = Field(..., description="Unique identifier")
    call_sign: Optional[str] = Field(None, description="FCC call sign (terrestrial)")
    name: str = Field(..., description="Display name")
    
    # Classification
    format: StationFormat
    format_name: str = Field(..., description="Human-readable format name")
    sub_format: Optional[str] = Field(None, description="More specific format")
    
    # Geography
    market: Optional[str] = None
    market_rank: Optional[int] = Field(None, ge=1)
    dma_code: Optional[str] = None
    coverage_type: str = Field(default="streaming")  # "terrestrial", "streaming", "both"
    
    # Demographics
    primary_demo: Optional[str] = None
    female_skew: float = Field(default=0.5, ge=0.0, le=1.0)
    median_age: Optional[int] = Field(None, ge=0)
    median_hhi: Optional[int] = Field(None, ge=0)  # Household income
    
    # Psychographic profile (ADAM-derived)
    psychographic_profile: Optional[StationPsychProfile] = None
    psychographic_embedding: List[float] = Field(default_factory=list)
    
    # Content characteristics
    music_percentage: float = Field(default=0.75, ge=0.0, le=1.0)
    talk_percentage: float = Field(default=0.10, ge=0.0, le=1.0)
    ad_load_percentage: float = Field(default=0.15, ge=0.0, le=1.0)
    avg_song_energy: float = Field(default=0.5, ge=0.0, le=1.0)
    avg_song_valence: float = Field(default=0.5, ge=0.0, le=1.0)
    
    # Ad performance baselines
    baseline_ctr: float = Field(default=0.008, ge=0.0, le=1.0)
    baseline_listen_through: float = Field(default=0.72, ge=0.0, le=1.0)
    baseline_conversion_rate: float = Field(default=0.002, ge=0.0, le=1.0)
    
    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    profile_updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    listening_data_updated_at: Optional[datetime] = None


# =============================================================================
# FORMAT → PSYCHOLOGICAL PROFILE MAPPINGS
# =============================================================================

# These are initial priors, continuously refined through learning

STATION_FORMAT_PROFILES: Dict[StationFormat, StationPsychProfile] = {
    StationFormat.CHR: StationPsychProfile(
        openness=BigFiveDistribution(mean=0.55, std=0.18),
        conscientiousness=BigFiveDistribution(mean=0.48, std=0.20),
        extraversion=BigFiveDistribution(mean=0.68, std=0.15),  # HIGH
        agreeableness=BigFiveDistribution(mean=0.55, std=0.18),
        neuroticism=BigFiveDistribution(mean=0.52, std=0.20),
        promotion_tendency=0.65,
        prevention_tendency=0.35,
        abstract_tendency=0.45,
        primary_mechanisms=["mimetic_desire", "attention_dynamics", "identity_construction"],
    ),
    
    StationFormat.COUNTRY: StationPsychProfile(
        openness=BigFiveDistribution(mean=0.45, std=0.18),
        conscientiousness=BigFiveDistribution(mean=0.58, std=0.18),  # HIGH
        extraversion=BigFiveDistribution(mean=0.55, std=0.18),
        agreeableness=BigFiveDistribution(mean=0.62, std=0.15),  # HIGH
        neuroticism=BigFiveDistribution(mean=0.48, std=0.20),
        promotion_tendency=0.45,
        prevention_tendency=0.55,
        abstract_tendency=0.50,
        primary_mechanisms=["identity_construction", "evolutionary_motive_activation", "temporal_construal"],
    ),
    
    StationFormat.ROCK: StationPsychProfile(
        openness=BigFiveDistribution(mean=0.58, std=0.18),
        conscientiousness=BigFiveDistribution(mean=0.48, std=0.20),
        extraversion=BigFiveDistribution(mean=0.55, std=0.20),
        agreeableness=BigFiveDistribution(mean=0.45, std=0.18),
        neuroticism=BigFiveDistribution(mean=0.52, std=0.18),
        promotion_tendency=0.55,
        prevention_tendency=0.45,
        abstract_tendency=0.48,
        primary_mechanisms=["identity_construction", "automatic_evaluation", "evolutionary_motive_activation"],
    ),
    
    StationFormat.CLASSICAL: StationPsychProfile(
        openness=BigFiveDistribution(mean=0.72, std=0.15),  # VERY HIGH
        conscientiousness=BigFiveDistribution(mean=0.62, std=0.15),
        extraversion=BigFiveDistribution(mean=0.42, std=0.18),  # LOW
        agreeableness=BigFiveDistribution(mean=0.58, std=0.15),
        neuroticism=BigFiveDistribution(mean=0.45, std=0.18),
        promotion_tendency=0.45,
        prevention_tendency=0.55,
        abstract_tendency=0.68,  # HIGH abstract
        primary_mechanisms=["temporal_construal", "embodied_cognition", "attention_dynamics"],
    ),
    
    StationFormat.NEWS_TALK: StationPsychProfile(
        openness=BigFiveDistribution(mean=0.58, std=0.20),
        conscientiousness=BigFiveDistribution(mean=0.58, std=0.18),
        extraversion=BigFiveDistribution(mean=0.52, std=0.20),
        agreeableness=BigFiveDistribution(mean=0.48, std=0.20),
        neuroticism=BigFiveDistribution(mean=0.55, std=0.18),
        promotion_tendency=0.42,
        prevention_tendency=0.58,  # Prevention-focused
        abstract_tendency=0.62,
        primary_mechanisms=["linguistic_framing", "evolutionary_motive_activation", "automatic_evaluation"],
    ),
    
    StationFormat.URBAN: StationPsychProfile(
        openness=BigFiveDistribution(mean=0.58, std=0.18),
        conscientiousness=BigFiveDistribution(mean=0.50, std=0.20),
        extraversion=BigFiveDistribution(mean=0.65, std=0.15),  # HIGH
        agreeableness=BigFiveDistribution(mean=0.52, std=0.18),
        neuroticism=BigFiveDistribution(mean=0.52, std=0.18),
        promotion_tendency=0.62,
        prevention_tendency=0.38,
        abstract_tendency=0.45,
        primary_mechanisms=["mimetic_desire", "identity_construction", "wanting_liking_dissociation"],
    ),
    
    StationFormat.ALTERNATIVE: StationPsychProfile(
        openness=BigFiveDistribution(mean=0.68, std=0.15),  # HIGH
        conscientiousness=BigFiveDistribution(mean=0.48, std=0.20),
        extraversion=BigFiveDistribution(mean=0.52, std=0.20),
        agreeableness=BigFiveDistribution(mean=0.52, std=0.18),
        neuroticism=BigFiveDistribution(mean=0.55, std=0.18),
        promotion_tendency=0.58,
        prevention_tendency=0.42,
        abstract_tendency=0.55,
        primary_mechanisms=["identity_construction", "attention_dynamics", "automatic_evaluation"],
    ),
    
    StationFormat.JAZZ: StationPsychProfile(
        openness=BigFiveDistribution(mean=0.70, std=0.15),  # VERY HIGH
        conscientiousness=BigFiveDistribution(mean=0.55, std=0.18),
        extraversion=BigFiveDistribution(mean=0.48, std=0.20),
        agreeableness=BigFiveDistribution(mean=0.58, std=0.15),
        neuroticism=BigFiveDistribution(mean=0.45, std=0.18),
        promotion_tendency=0.48,
        prevention_tendency=0.52,
        abstract_tendency=0.65,
        primary_mechanisms=["embodied_cognition", "attention_dynamics", "temporal_construal"],
    ),
    
    StationFormat.SPORTS: StationPsychProfile(
        openness=BigFiveDistribution(mean=0.48, std=0.20),
        conscientiousness=BigFiveDistribution(mean=0.52, std=0.18),
        extraversion=BigFiveDistribution(mean=0.62, std=0.15),  # HIGH
        agreeableness=BigFiveDistribution(mean=0.52, std=0.18),
        neuroticism=BigFiveDistribution(mean=0.55, std=0.18),
        promotion_tendency=0.55,
        prevention_tendency=0.45,
        abstract_tendency=0.42,
        primary_mechanisms=["mimetic_desire", "evolutionary_motive_activation", "identity_construction"],
    ),
}


def get_format_profile(format: StationFormat) -> StationPsychProfile:
    """Get the default psychographic profile for a station format."""
    return STATION_FORMAT_PROFILES.get(format, StationPsychProfile(
        openness=BigFiveDistribution(mean=0.5, std=0.18),
        conscientiousness=BigFiveDistribution(mean=0.5, std=0.18),
        extraversion=BigFiveDistribution(mean=0.5, std=0.18),
        agreeableness=BigFiveDistribution(mean=0.5, std=0.18),
        neuroticism=BigFiveDistribution(mean=0.5, std=0.18),
        promotion_tendency=0.5,
        prevention_tendency=0.5,
        primary_mechanisms=["attention_dynamics", "automatic_evaluation"],
    ))
