# ADAM iHeart Ad Network Integration
## Complete Specification for Bidirectional Intelligence Exchange

**Document Purpose**: Define the complete integration between ADAM and iHeart Media's ad network, establishing iHeart as the primary learning interface where psychological intelligence is both derived from and applied to the world's largest audio platform.

**Version**: 1.0  
**Date**: January 2026  
**Status**: Production Specification  
**Classification**: Core System Component  
**Priority**: P0 - Critical Path

---

# EXECUTIVE SUMMARY

## Why This Component is Foundational

The iHeart integration is not merely an "output channel" for ADAM—it is the **primary sensory interface** through which ADAM:

1. **LEARNS** psychological patterns from 175M+ listeners' content consumption
2. **VALIDATES** mechanism effectiveness through real-world outcomes
3. **DISCOVERS** emergent psychological constructs from behavioral patterns
4. **DELIVERS** personality-matched messaging at scale
5. **EVOLVES** through continuous feedback loops

Every other ADAM component depends on or contributes to this integration:

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                    iHEART AS ADAM'S PRIMARY LEARNING INTERFACE                  │
│                                                                                 │
│   ┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐  │
│   │   Signal    │     │   Cold      │     │   Copy      │     │   A/B       │  │
│   │   Capture   │     │   Start     │     │   Gen       │     │   Testing   │  │
│   │   (#08)     │     │   (#13)     │     │   (#15)     │     │   (#12)     │  │
│   └──────┬──────┘     └──────┬──────┘     └──────┬──────┘     └──────┬──────┘  │
│          │                   │                   │                   │         │
│          │    ┌──────────────┴───────────────────┴───────────────────┘         │
│          │    │                                                                 │
│          ▼    ▼                                                                 │
│   ┌─────────────────────────────────────────────────────────────────────────┐  │
│   │                                                                         │  │
│   │                    iHEART AD NETWORK INTEGRATION                        │  │
│   │                                                                         │  │
│   │   ┌─────────────────────────────────────────────────────────────────┐   │  │
│   │   │  INBOUND SIGNALS                    OUTBOUND DECISIONS          │   │  │
│   │   │  ════════════════                   ═══════════════════         │   │  │
│   │   │                                                                 │   │  │
│   │   │  • Station listening patterns       • Ad selection              │   │  │
│   │   │  • Track/artist consumption         • Copy variant              │   │  │
│   │   │  • Podcast engagement               • Audio parameters          │   │  │
│   │   │  • Skip/complete behavior           • Timing recommendation     │   │  │
│   │   │  • Lyrics content exposure          • Mechanism activation      │   │  │
│   │   │  • Transcript topic exposure                                    │   │  │
│   │   │  • Ad interaction outcomes                                      │   │  │
│   │   │                                                                 │   │  │
│   │   └─────────────────────────────────────────────────────────────────┘   │  │
│   │                                                                         │  │
│   └─────────────────────────────────────────────────────────────────────────┘  │
│          │    │                                                                 │
│          │    │    ┌───────────────────────────────────────────────────────┐   │
│          │    │    │                                                       │   │
│          ▼    ▼    ▼                                                       │   │
│   ┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐  │
│   │  Discovery  │     │  Gradient   │     │   Graph     │     │  Mechanism  │  │
│   │   Engine    │     │   Bridge    │     │  Database   │     │  Learning   │  │
│   │             │     │   (#06)     │     │  (Neo4j)    │     │             │  │
│   └─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘  │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## Learning Flows Through This Component

| Signal Source | What ADAM Learns | Components Updated |
|---------------|------------------|-------------------|
| Station listening | Format preferences → personality | Cold Start archetypes, User profiles |
| Track consumption | Genre/artist → Big Five mapping | Psychological constructs, Graph |
| Lyrics exposure | Emotional content → state priming | Mechanism effectiveness |
| Podcast engagement | Topic affinity → interests | Journey state, Targeting |
| Skip behavior | Impatience, anxiety signals | Supraliminal signals |
| Ad outcomes | Mechanism effectiveness | Gradient Bridge, A/B Testing |
| Content-ad adjacency | Context × message compatibility | Copy Generation priors |

---

# PART 1: CONTENT DOMAIN DATA MODEL

## 1.1 Station Entity

Stations are the highest-level content organization in terrestrial and streaming radio. Each station has demographic and psychographic characteristics that inform listener profiling.

### Neo4j Schema

```cypher
// =============================================================================
// STATION NODE - Radio station or streaming channel
// =============================================================================

CREATE (s:Station {
    // Identity
    station_id: "KIIS-FM",              // Unique identifier
    call_sign: "KIIS-FM",               // FCC call sign (terrestrial)
    name: "102.7 KIIS FM",              // Display name
    
    // Classification
    format: "CHR",                       // Format code (see STATION_FORMATS)
    format_name: "Contemporary Hit Radio",
    sub_format: "Rhythmic CHR",          // More specific format
    
    // Geography
    market: "Los Angeles",
    market_rank: 2,                      // Nielsen DMA rank
    dma_code: "803",
    coverage_type: "terrestrial",        // "terrestrial", "streaming", "both"
    
    // Demographics (aggregate listener profile)
    primary_demo: "18-34",
    female_skew: 0.58,                   // 58% female
    median_age: 28,
    median_hhi: 65000,                   // Household income
    
    // Psychographic Profile (ADAM-derived)
    // These are learned from listener behavior and updated continuously
    psych_openness_mean: 0.62,
    psych_openness_std: 0.15,
    psych_conscientiousness_mean: 0.48,
    psych_extraversion_mean: 0.68,       // High for CHR
    psych_agreeableness_mean: 0.55,
    psych_neuroticism_mean: 0.52,
    
    // Regulatory focus tendency
    promotion_focus_tendency: 0.65,      // CHR listeners are promotion-focused
    prevention_focus_tendency: 0.35,
    
    // Construal level tendency
    abstract_tendency: 0.45,             // More concrete for pop music
    
    // Content characteristics
    music_percentage: 0.75,              // 75% music, 25% talk/ads
    talk_percentage: 0.10,
    ad_load_percentage: 0.15,
    avg_song_energy: 0.72,
    avg_song_valence: 0.65,
    
    // Ad performance baselines (for comparison)
    baseline_ctr: 0.008,
    baseline_listen_through: 0.72,
    baseline_conversion_rate: 0.002,
    
    // Timestamps
    created_at: datetime(),
    profile_updated_at: datetime(),
    listening_data_updated_at: datetime()
})

// Indexes for fast lookup
CREATE INDEX station_id_idx FOR (s:Station) ON (s.station_id)
CREATE INDEX station_format_idx FOR (s:Station) ON (s.format)
CREATE INDEX station_market_idx FOR (s:Station) ON (s.market)
```

### Station Format Taxonomy with Psychological Profiles

```python
# =============================================================================
# STATION FORMAT → PSYCHOLOGICAL PROFILE MAPPINGS
# =============================================================================
# These are initial priors, continuously refined through learning

STATION_FORMAT_PROFILES = {
    "CHR": {
        "name": "Contemporary Hit Radio",
        "description": "Top 40, current hits across genres",
        "psychological_profile": {
            "big_five": {
                "openness": {"mean": 0.55, "std": 0.18},
                "conscientiousness": {"mean": 0.48, "std": 0.20},
                "extraversion": {"mean": 0.68, "std": 0.15},  # HIGH
                "agreeableness": {"mean": 0.55, "std": 0.18},
                "neuroticism": {"mean": 0.52, "std": 0.20}
            },
            "regulatory_focus": {
                "promotion": 0.65,  # Seeking novelty, hits
                "prevention": 0.35
            },
            "construal_level": "concrete",  # Pop music = immediate gratification
            "primary_mechanisms": [
                "mimetic_desire",      # What's popular
                "social_proof",        # Everyone's listening
                "identity_expression"  # Staying current
            ]
        },
        "demographic_skew": {
            "age_range": "18-34",
            "female_skew": 0.55
        },
        "ad_receptivity": {
            "optimal_energy": 0.7,
            "optimal_pace": "fast",
            "humor_tolerance": "high",
            "information_density": "low"
        }
    },
    
    "HOT_AC": {
        "name": "Hot Adult Contemporary",
        "description": "Current and recent hits, adult-focused",
        "psychological_profile": {
            "big_five": {
                "openness": {"mean": 0.50, "std": 0.18},
                "conscientiousness": {"mean": 0.58, "std": 0.18},  # Higher
                "extraversion": {"mean": 0.55, "std": 0.18},
                "agreeableness": {"mean": 0.60, "std": 0.15},
                "neuroticism": {"mean": 0.48, "std": 0.18}
            },
            "regulatory_focus": {
                "promotion": 0.55,
                "prevention": 0.45
            },
            "construal_level": "mixed",
            "primary_mechanisms": [
                "familiarity",
                "nostalgia_proximity",  # Recent enough to remember
                "comfort"
            ]
        },
        "demographic_skew": {
            "age_range": "25-44",
            "female_skew": 0.58
        },
        "ad_receptivity": {
            "optimal_energy": 0.5,
            "optimal_pace": "medium",
            "humor_tolerance": "medium",
            "information_density": "medium"
        }
    },
    
    "COUNTRY": {
        "name": "Country",
        "description": "Country music, traditional and contemporary",
        "psychological_profile": {
            "big_five": {
                "openness": {"mean": 0.42, "std": 0.18},  # Lower
                "conscientiousness": {"mean": 0.62, "std": 0.15},  # Higher
                "extraversion": {"mean": 0.55, "std": 0.18},
                "agreeableness": {"mean": 0.65, "std": 0.15},  # Higher
                "neuroticism": {"mean": 0.45, "std": 0.18}
            },
            "regulatory_focus": {
                "promotion": 0.45,
                "prevention": 0.55  # More prevention-focused
            },
            "construal_level": "concrete",  # Storytelling, specific narratives
            "primary_mechanisms": [
                "authenticity",
                "tradition",
                "community_belonging",
                "narrative_transport"
            ]
        },
        "demographic_skew": {
            "age_range": "25-54",
            "female_skew": 0.52
        },
        "ad_receptivity": {
            "optimal_energy": 0.5,
            "optimal_pace": "medium",
            "humor_tolerance": "medium",
            "information_density": "medium",
            "authenticity_requirement": "high"
        }
    },
    
    "CLASSIC_ROCK": {
        "name": "Classic Rock",
        "description": "Rock from 1960s-1990s",
        "psychological_profile": {
            "big_five": {
                "openness": {"mean": 0.58, "std": 0.18},
                "conscientiousness": {"mean": 0.52, "std": 0.18},
                "extraversion": {"mean": 0.52, "std": 0.20},
                "agreeableness": {"mean": 0.48, "std": 0.18},  # Lower
                "neuroticism": {"mean": 0.48, "std": 0.18}
            },
            "regulatory_focus": {
                "promotion": 0.50,
                "prevention": 0.50
            },
            "construal_level": "abstract",  # Music as identity/meaning
            "primary_mechanisms": [
                "nostalgia",
                "identity_reinforcement",
                "authenticity",
                "rebellion_echo"
            ]
        },
        "demographic_skew": {
            "age_range": "35-64",
            "male_skew": 0.62
        },
        "ad_receptivity": {
            "optimal_energy": 0.6,
            "optimal_pace": "medium",
            "humor_tolerance": "medium",
            "information_density": "medium",
            "nostalgia_effectiveness": "high"
        }
    },
    
    "URBAN": {
        "name": "Urban Contemporary",
        "description": "Hip-hop, R&B, urban formats",
        "psychological_profile": {
            "big_five": {
                "openness": {"mean": 0.60, "std": 0.18},
                "conscientiousness": {"mean": 0.45, "std": 0.20},
                "extraversion": {"mean": 0.70, "std": 0.15},  # HIGH
                "agreeableness": {"mean": 0.50, "std": 0.18},
                "neuroticism": {"mean": 0.50, "std": 0.20}
            },
            "regulatory_focus": {
                "promotion": 0.70,  # High promotion focus
                "prevention": 0.30
            },
            "construal_level": "concrete",  # Material, specific
            "primary_mechanisms": [
                "status_aspiration",
                "identity_expression",
                "social_proof",
                "authenticity"
            ]
        },
        "demographic_skew": {
            "age_range": "18-34",
            "diverse_audience": True
        },
        "ad_receptivity": {
            "optimal_energy": 0.75,
            "optimal_pace": "fast",
            "humor_tolerance": "high",
            "information_density": "low",
            "status_appeals": "effective"
        }
    },
    
    "NEWS_TALK": {
        "name": "News/Talk",
        "description": "News, talk radio, current events",
        "psychological_profile": {
            "big_five": {
                "openness": {"mean": 0.55, "std": 0.20},
                "conscientiousness": {"mean": 0.65, "std": 0.15},  # HIGH
                "extraversion": {"mean": 0.48, "std": 0.18},
                "agreeableness": {"mean": 0.45, "std": 0.20},
                "neuroticism": {"mean": 0.55, "std": 0.18}
            },
            "regulatory_focus": {
                "promotion": 0.40,
                "prevention": 0.60  # Information-seeking for security
            },
            "construal_level": "abstract",  # Ideas, analysis
            "primary_mechanisms": [
                "information_need",
                "uncertainty_reduction",
                "authority_credibility",
                "analytical_appeal"
            ]
        },
        "demographic_skew": {
            "age_range": "35-64",
            "male_skew": 0.58
        },
        "ad_receptivity": {
            "optimal_energy": 0.4,
            "optimal_pace": "slow",
            "humor_tolerance": "low",
            "information_density": "high",
            "credibility_requirement": "high"
        }
    },
    
    "CLASSICAL": {
        "name": "Classical",
        "description": "Classical music, orchestral, opera",
        "psychological_profile": {
            "big_five": {
                "openness": {"mean": 0.75, "std": 0.12},  # VERY HIGH
                "conscientiousness": {"mean": 0.60, "std": 0.15},
                "extraversion": {"mean": 0.42, "std": 0.18},  # Lower
                "agreeableness": {"mean": 0.58, "std": 0.15},
                "neuroticism": {"mean": 0.48, "std": 0.18}
            },
            "regulatory_focus": {
                "promotion": 0.55,
                "prevention": 0.45
            },
            "construal_level": "abstract",  # High abstraction
            "primary_mechanisms": [
                "aesthetic_appreciation",
                "intellectual_engagement",
                "sophistication_identity",
                "transcendence"
            ]
        },
        "demographic_skew": {
            "age_range": "45-65+",
            "higher_education": 0.72
        },
        "ad_receptivity": {
            "optimal_energy": 0.3,
            "optimal_pace": "slow",
            "humor_tolerance": "low",
            "information_density": "high",
            "sophistication_requirement": "high",
            "hard_sell_aversion": "strong"
        }
    },
    
    "SPANISH_CONTEMPORARY": {
        "name": "Spanish Contemporary",
        "description": "Spanish-language pop, regional Mexican, Latin",
        "psychological_profile": {
            "big_five": {
                "openness": {"mean": 0.55, "std": 0.18},
                "conscientiousness": {"mean": 0.55, "std": 0.18},
                "extraversion": {"mean": 0.65, "std": 0.15},
                "agreeableness": {"mean": 0.62, "std": 0.15},
                "neuroticism": {"mean": 0.50, "std": 0.18}
            },
            "regulatory_focus": {
                "promotion": 0.55,
                "prevention": 0.45
            },
            "construal_level": "concrete",
            "primary_mechanisms": [
                "cultural_identity",
                "family_values",
                "community_belonging",
                "tradition"
            ]
        },
        "demographic_skew": {
            "hispanic_audience": 0.95,
            "bilingual_percentage": 0.45
        },
        "ad_receptivity": {
            "optimal_energy": 0.6,
            "optimal_pace": "medium",
            "family_appeals": "effective",
            "cultural_relevance": "critical",
            "language_preference": "spanish_or_bilingual"
        }
    }
}
```

### Pydantic Model

```python
from pydantic import BaseModel, Field
from typing import Dict, List, Optional
from datetime import datetime
from enum import Enum


class StationFormat(str, Enum):
    """Radio station format codes."""
    CHR = "CHR"                          # Contemporary Hit Radio
    HOT_AC = "HOT_AC"                    # Hot Adult Contemporary
    AC = "AC"                            # Adult Contemporary
    COUNTRY = "COUNTRY"
    CLASSIC_ROCK = "CLASSIC_ROCK"
    ROCK = "ROCK"
    ALTERNATIVE = "ALTERNATIVE"
    URBAN = "URBAN"
    URBAN_AC = "URBAN_AC"
    RHYTHMIC = "RHYTHMIC"
    NEWS_TALK = "NEWS_TALK"
    SPORTS = "SPORTS"
    CLASSICAL = "CLASSICAL"
    JAZZ = "JAZZ"
    SPANISH_CONTEMPORARY = "SPANISH_CONTEMPORARY"
    REGIONAL_MEXICAN = "REGIONAL_MEXICAN"
    CHRISTIAN = "CHRISTIAN"
    OLDIES = "OLDIES"
    EASY_LISTENING = "EASY_LISTENING"


class StationCoverageType(str, Enum):
    """How station is delivered."""
    TERRESTRIAL = "terrestrial"
    STREAMING = "streaming"
    BOTH = "both"


class StationPsychographicProfile(BaseModel):
    """Aggregate psychological profile of station listeners."""
    # Big Five means and standard deviations
    openness_mean: float = Field(ge=0, le=1)
    openness_std: float = Field(ge=0, le=0.5)
    conscientiousness_mean: float = Field(ge=0, le=1)
    conscientiousness_std: float = Field(ge=0, le=0.5)
    extraversion_mean: float = Field(ge=0, le=1)
    extraversion_std: float = Field(ge=0, le=0.5)
    agreeableness_mean: float = Field(ge=0, le=1)
    agreeableness_std: float = Field(ge=0, le=0.5)
    neuroticism_mean: float = Field(ge=0, le=1)
    neuroticism_std: float = Field(ge=0, le=0.5)
    
    # Regulatory focus tendency
    promotion_focus_tendency: float = Field(ge=0, le=1)
    prevention_focus_tendency: float = Field(ge=0, le=1)
    
    # Construal level tendency
    abstract_tendency: float = Field(ge=0, le=1)
    
    # Confidence in this profile (based on data volume)
    profile_confidence: float = Field(ge=0, le=1)
    listener_sample_size: int
    
    # Last updated
    updated_at: datetime


class Station(BaseModel):
    """Radio station or streaming channel entity."""
    # Identity
    station_id: str
    call_sign: Optional[str] = None
    name: str
    
    # Classification
    format: StationFormat
    format_name: str
    sub_format: Optional[str] = None
    
    # Geography
    market: str
    market_rank: Optional[int] = None
    dma_code: Optional[str] = None
    coverage_type: StationCoverageType
    
    # Demographics
    primary_demo: str
    female_skew: float = Field(ge=0, le=1)
    median_age: Optional[int] = None
    median_hhi: Optional[int] = None
    
    # Psychographic profile (learned)
    psychographic_profile: StationPsychographicProfile
    
    # Content characteristics
    music_percentage: float = Field(ge=0, le=1)
    talk_percentage: float = Field(ge=0, le=1)
    ad_load_percentage: float = Field(ge=0, le=1)
    avg_song_energy: Optional[float] = None
    avg_song_valence: Optional[float] = None
    
    # Ad performance baselines
    baseline_ctr: float
    baseline_listen_through: float
    baseline_conversion_rate: float
    
    # Primary mechanisms effective for this station
    effective_mechanisms: List[str] = Field(default_factory=list)
    
    # Timestamps
    created_at: datetime
    profile_updated_at: datetime
```

### Station Learning Integration

```python
# =============================================================================
# STATION PROFILE LEARNING - How stations inform and are informed by ADAM
# =============================================================================

class StationLearningService:
    """
    Bidirectional learning between station profiles and ADAM's psychological models.
    
    INBOUND LEARNING (Station → ADAM):
    - Aggregate listener behavior updates station psychographic profile
    - Station-level ad performance informs mechanism effectiveness
    - Format-level patterns become Cold Start priors
    
    OUTBOUND APPLICATION (ADAM → Station):
    - Station profile informs ad selection
    - Format profile provides Cold Start initialization
    - Station baseline informs A/B test power analysis
    """
    
    def __init__(
        self,
        graph: GraphService,
        gradient_bridge: GradientBridge,
        cold_start: ColdStartService,
        kafka: KafkaProducer
    ):
        self.graph = graph
        self.gradient_bridge = gradient_bridge
        self.cold_start = cold_start
        self.kafka = kafka
    
    # =========================================================================
    # INBOUND LEARNING: Station behavior → ADAM knowledge
    # =========================================================================
    
    async def update_station_profile_from_listening(
        self,
        station_id: str,
        listening_events: List[ListeningEvent],
        window_hours: int = 24
    ) -> StationPsychographicProfile:
        """
        Update station's psychographic profile from listener behavior.
        
        This aggregates individual user profiles weighted by listening time
        to create/update the station's aggregate psychological signature.
        
        LEARNING SIGNAL: Station listening patterns → Station profile
        """
        # Get all users who listened to this station in the window
        user_profiles = []
        listening_weights = []
        
        for event in listening_events:
            user_profile = await self.graph.get_user_profile(event.user_id)
            if user_profile and user_profile.profile_confidence > 0.5:
                user_profiles.append(user_profile)
                listening_weights.append(event.duration_seconds)
        
        if not user_profiles:
            return None
        
        # Calculate weighted averages for each trait
        total_weight = sum(listening_weights)
        
        def weighted_mean(values: List[float], weights: List[float]) -> float:
            return sum(v * w for v, w in zip(values, weights)) / total_weight
        
        def weighted_std(values: List[float], weights: List[float], mean: float) -> float:
            variance = sum(w * (v - mean) ** 2 for v, w in zip(values, weights)) / total_weight
            return variance ** 0.5
        
        # Calculate new profile
        openness_values = [p.big_five.openness for p in user_profiles]
        openness_mean = weighted_mean(openness_values, listening_weights)
        
        # ... (similar for other traits)
        
        new_profile = StationPsychographicProfile(
            openness_mean=openness_mean,
            openness_std=weighted_std(openness_values, listening_weights, openness_mean),
            # ... other traits
            profile_confidence=min(0.95, len(user_profiles) / 1000),  # More listeners = more confidence
            listener_sample_size=len(user_profiles),
            updated_at=datetime.utcnow()
        )
        
        # Update in graph
        await self.graph.update_station_profile(station_id, new_profile)
        
        # Emit learning signal
        await self.gradient_bridge.propagate_signal(
            LearningSignal(
                source="station_profile_learning",
                signal_type=LearningSignalType.PROFILE_UPDATE,
                entity_type="station",
                entity_id=station_id,
                payload={
                    "profile": new_profile.dict(),
                    "sample_size": len(user_profiles)
                }
            )
        )
        
        return new_profile
    
    async def update_format_priors_from_stations(
        self,
        format: StationFormat
    ) -> Dict[str, Any]:
        """
        Aggregate station profiles to update format-level priors.
        
        These format priors become Cold Start initializations for
        users who only have station/format information.
        
        LEARNING SIGNAL: Station profiles → Format priors → Cold Start
        """
        # Get all stations of this format
        stations = await self.graph.get_stations_by_format(format)
        
        # Aggregate profiles weighted by listener count
        # ... aggregation logic
        
        format_prior = {
            "format": format.value,
            "psychological_profile": aggregated_profile,
            "effective_mechanisms": most_common_mechanisms,
            "ad_receptivity": aggregated_receptivity
        }
        
        # Update Cold Start format priors
        await self.cold_start.update_format_prior(format, format_prior)
        
        # Emit event for other components
        await self.kafka.send(
            "learning_signals",
            FormatPriorUpdatedEvent(
                format=format.value,
                prior=format_prior
            )
        )
        
        return format_prior
    
    async def learn_station_mechanism_effectiveness(
        self,
        station_id: str,
        ad_outcomes: List[AdOutcome],
        window_days: int = 30
    ) -> Dict[str, MechanismEffectiveness]:
        """
        Learn which mechanisms work best for this station's audience.
        
        LEARNING SIGNAL: Ad outcomes × Mechanisms → Station mechanism priors
        """
        mechanism_outcomes = defaultdict(list)
        
        for outcome in ad_outcomes:
            for mechanism in outcome.mechanisms_used:
                mechanism_outcomes[mechanism].append(outcome.converted)
        
        effectiveness = {}
        for mechanism, outcomes in mechanism_outcomes.items():
            success_rate = sum(outcomes) / len(outcomes)
            effectiveness[mechanism] = MechanismEffectiveness(
                mechanism_id=mechanism,
                success_rate=success_rate,
                confidence=min(0.95, len(outcomes) / 100),
                evidence_count=len(outcomes)
            )
        
        # Update graph
        await self.graph.update_station_mechanism_effectiveness(
            station_id, effectiveness
        )
        
        # Propagate to Gradient Bridge
        await self.gradient_bridge.propagate_signal(
            LearningSignal(
                source="station_mechanism_learning",
                signal_type=LearningSignalType.MECHANISM_UPDATE,
                entity_type="station",
                entity_id=station_id,
                payload={"effectiveness": effectiveness}
            )
        )
        
        return effectiveness
    
    # =========================================================================
    # OUTBOUND APPLICATION: ADAM knowledge → Station decisions
    # =========================================================================
    
    async def get_station_priors_for_decision(
        self,
        station_id: str
    ) -> Dict[str, Any]:
        """
        Get all station-level priors for an ad decision.
        
        Used when we know the station but may not know the user well.
        """
        station = await self.graph.get_station(station_id)
        
        return {
            "psychographic_profile": station.psychographic_profile,
            "effective_mechanisms": station.effective_mechanisms,
            "ad_baselines": {
                "ctr": station.baseline_ctr,
                "listen_through": station.baseline_listen_through,
                "conversion": station.baseline_conversion_rate
            },
            "format_priors": await self.cold_start.get_format_prior(station.format)
        }
    
    async def get_cold_start_profile_from_station(
        self,
        station_id: str
    ) -> UserProfile:
        """
        Generate a Cold Start user profile from station characteristics.
        
        Used for anonymous listeners where we only know the station.
        """
        station = await self.graph.get_station(station_id)
        
        # Use station psychographic profile as user prior
        return UserProfile(
            user_id="anonymous",
            big_five=BigFiveProfile(
                openness=station.psychographic_profile.openness_mean,
                conscientiousness=station.psychographic_profile.conscientiousness_mean,
                extraversion=station.psychographic_profile.extraversion_mean,
                agreeableness=station.psychographic_profile.agreeableness_mean,
                neuroticism=station.psychographic_profile.neuroticism_mean
            ),
            regulatory_focus=RegulatoryFocusState(
                promotion_strength=station.psychographic_profile.promotion_focus_tendency,
                prevention_strength=station.psychographic_profile.prevention_focus_tendency
            ),
            construal_level=ConstrualLevel.ABSTRACT if station.psychographic_profile.abstract_tendency > 0.5 else ConstrualLevel.CONCRETE,
            data_tier=UserDataTier.ANONYMOUS,
            profile_confidence=station.psychographic_profile.profile_confidence * 0.5,  # Discount for anonymity
            profile_source="station_inference"
        )
```

---

## 1.2 Artist Entity

Artists carry strong psychological signatures that inform listener profiling and ad matching.

### Neo4j Schema

```cypher
// =============================================================================
// ARTIST NODE - Musical artist or group
// =============================================================================

CREATE (a:Artist {
    // Identity
    artist_id: "spotify:artist:06HL4z0CvFAxyc27GXpf02",
    name: "Taylor Swift",
    
    // Classification
    primary_genre: "pop",
    genres: ["pop", "country", "indie_folk"],
    
    // Psychological Profile (learned from music + listener behavior)
    psych_openness: 0.68,
    psych_conscientiousness: 0.72,
    psych_extraversion: 0.75,
    psych_agreeableness: 0.62,
    psych_neuroticism: 0.58,
    profile_confidence: 0.85,
    
    // Content characteristics (aggregated from tracks)
    avg_valence: 0.52,
    avg_energy: 0.68,
    avg_danceability: 0.65,
    lyrical_themes: ["love", "heartbreak", "growth", "revenge"],
    emotional_range: 0.72,       // High = emotionally diverse catalog
    
    // Listener affinity patterns
    fan_loyalty_index: 0.82,     // High = dedicated fanbase
    crossover_appeal: 0.75,      // Appeals across formats
    
    // Ad effectiveness patterns (learned)
    brand_affinity_categories: ["fashion", "lifestyle", "technology"],
    mechanism_affinities: {
        "narrative_transport": 0.85,
        "identity_expression": 0.78,
        "social_proof": 0.72
    },
    
    // Timestamps
    created_at: datetime(),
    profile_updated_at: datetime()
})

// Relationships
CREATE (a:Artist)-[:HAS_GENRE]->(g:Genre)
CREATE (a:Artist)-[:SIMILAR_TO {similarity: 0.85}]->(a2:Artist)
CREATE (a:Artist)-[:APPEALS_TO]->(ps:PsychographicSegment)

// Indexes
CREATE INDEX artist_id_idx FOR (a:Artist) ON (a.artist_id)
CREATE INDEX artist_genre_idx FOR (a:Artist) ON (a.primary_genre)
```

### Artist Psychological Profiling

```python
# =============================================================================
# ARTIST → PSYCHOLOGICAL PROFILE INFERENCE
# =============================================================================

class ArtistPsychologicalProfiler:
    """
    Infer artist psychological signatures from:
    1. Musical audio features (tempo, energy, valence)
    2. Lyrical content analysis
    3. Fan/listener psychological profiles
    4. Genre associations
    
    Artist profiles are used to:
    - Infer listener traits from listening behavior
    - Match brands to artist content
    - Select appropriate ad mechanisms
    """
    
    def __init__(
        self,
        graph: GraphService,
        lyrics_analyzer: LyricsAnalyzer,
        embedding_service: EmbeddingService
    ):
        self.graph = graph
        self.lyrics = lyrics_analyzer
        self.embeddings = embedding_service
    
    async def profile_artist(
        self,
        artist_id: str,
        tracks: List[Track],
        listener_profiles: List[UserProfile]
    ) -> ArtistPsychologicalProfile:
        """
        Build comprehensive artist psychological profile.
        
        LEARNING FLOW:
        1. Audio features → Energy/valence dimensions
        2. Lyrics → Themes, emotional content
        3. Listener profiles → Audience psychological signature
        4. Synthesis → Artist profile
        """
        
        # 1. Aggregate audio features
        audio_profile = self._analyze_audio_features(tracks)
        
        # 2. Analyze lyrical content
        lyrical_profile = await self._analyze_lyrics(tracks)
        
        # 3. Aggregate listener psychological profiles
        listener_aggregate = self._aggregate_listener_profiles(listener_profiles)
        
        # 4. Genre-based priors
        genre_priors = await self._get_genre_priors(tracks[0].genres if tracks else [])
        
        # 5. Synthesize into artist profile
        # Weight: 30% audio, 30% lyrics, 30% listeners, 10% genre
        profile = self._synthesize_profile(
            audio_profile=audio_profile,
            lyrical_profile=lyrical_profile,
            listener_aggregate=listener_aggregate,
            genre_priors=genre_priors,
            weights={
                "audio": 0.30,
                "lyrics": 0.30,
                "listeners": 0.30,
                "genre": 0.10
            }
        )
        
        return profile
    
    def _analyze_audio_features(
        self,
        tracks: List[Track]
    ) -> Dict[str, float]:
        """
        Map audio features to psychological dimensions.
        
        Based on Rentfrow et al. (2011) MUSIC model:
        - Energy/tempo → Extraversion, arousal preference
        - Valence → Neuroticism (inverse), emotional stability
        - Complexity → Openness
        """
        avg_energy = np.mean([t.audio_features.energy for t in tracks])
        avg_valence = np.mean([t.audio_features.valence for t in tracks])
        avg_tempo = np.mean([t.audio_features.tempo for t in tracks])
        avg_complexity = np.mean([t.audio_features.acousticness for t in tracks])
        
        return {
            "extraversion_signal": (avg_energy + (avg_tempo - 60) / 140) / 2,
            "neuroticism_signal": 1 - avg_valence,  # Lower valence = higher neuroticism
            "openness_signal": avg_complexity,
            "energy_preference": avg_energy,
            "emotional_valence": avg_valence
        }
    
    async def _analyze_lyrics(
        self,
        tracks: List[Track]
    ) -> Dict[str, Any]:
        """
        Analyze lyrical content for psychological signals.
        
        Extracts:
        - Themes (love, loss, ambition, rebellion, etc.)
        - Emotional content (LIWC-style analysis)
        - Linguistic complexity
        - Psychological constructs
        """
        all_themes = []
        emotional_scores = []
        construct_signals = []
        
        for track in tracks:
            if track.lyrics_id:
                lyrics = await self.graph.get_lyrics(track.lyrics_id)
                
                # Theme extraction
                themes = await self.lyrics.extract_themes(lyrics.raw_text)
                all_themes.extend(themes)
                
                # Emotional analysis
                emotions = await self.lyrics.analyze_emotions(lyrics.raw_text)
                emotional_scores.append(emotions)
                
                # Psychological construct detection
                constructs = await self.lyrics.detect_constructs(lyrics.raw_text)
                construct_signals.append(constructs)
        
        return {
            "dominant_themes": Counter(all_themes).most_common(5),
            "emotional_profile": self._aggregate_emotions(emotional_scores),
            "psychological_constructs": self._aggregate_constructs(construct_signals),
            "linguistic_complexity": self._calculate_complexity(tracks)
        }
    
    def _aggregate_listener_profiles(
        self,
        profiles: List[UserProfile]
    ) -> Dict[str, Any]:
        """
        Aggregate listener profiles to infer artist's audience signature.
        
        LEARNING PRINCIPLE: Artists attract psychologically similar listeners,
        so listener aggregate informs artist profile.
        """
        if not profiles:
            return None
        
        return {
            "openness": np.mean([p.big_five.openness for p in profiles]),
            "conscientiousness": np.mean([p.big_five.conscientiousness for p in profiles]),
            "extraversion": np.mean([p.big_five.extraversion for p in profiles]),
            "agreeableness": np.mean([p.big_five.agreeableness for p in profiles]),
            "neuroticism": np.mean([p.big_five.neuroticism for p in profiles]),
            "promotion_focus": np.mean([p.regulatory_focus.promotion_strength for p in profiles]),
            "sample_size": len(profiles)
        }
```

---

## 1.3 Track/Song Entity

Individual tracks are the atomic unit of music content with rich psychological signal potential.

### Neo4j Schema

```cypher
// =============================================================================
// TRACK NODE - Individual song/track
// =============================================================================

CREATE (t:Track {
    // Identity
    track_id: "spotify:track:4PTG3Z6ehGkBFwjybzWkR8",
    isrc: "USRC11700160",
    title: "Never Gonna Give You Up",
    
    // Relationships (stored as IDs, actual relationships separate)
    artist_id: "spotify:artist:0gxyHStUsqpMadRV0Di1Qt",
    album_id: "spotify:album:6N9PS4QXF1D0OWPk0Sxtb4",
    
    // Classification
    genres: ["pop", "synth-pop", "80s"],
    release_year: 1987,
    explicit: false,
    
    // Audio Features (Spotify-style)
    duration_ms: 213573,
    tempo: 113.0,
    key: 5,
    mode: 1,                    // 1 = major, 0 = minor
    time_signature: 4,
    
    // Psychological Audio Features
    energy: 0.947,              // 0-1, intensity and activity
    valence: 0.935,             // 0-1, musical positivity
    danceability: 0.718,
    acousticness: 0.029,
    instrumentalness: 0.000,
    liveness: 0.355,
    speechiness: 0.046,
    loudness: -6.169,           // dB
    
    // ADAM Psychological Mappings
    arousal_score: 0.89,        // Derived from energy + tempo
    valence_score: 0.94,        // Emotional positivity
    complexity_score: 0.35,     // Musical complexity
    
    // Psychological construct signals
    extraversion_signal: 0.82,
    openness_signal: 0.45,
    neuroticism_signal: 0.15,   // Low (high valence)
    
    // Mechanism affinities
    nostalgia_potential: 0.95,  // High for 80s track
    energy_match_potential: 0.89,
    mood_lift_potential: 0.92,
    
    // Lyrics reference
    lyrics_id: "lyrics:USRC11700160",
    has_lyrics: true,
    
    // Play statistics (for learning)
    total_plays: 15000000,
    skip_rate: 0.12,            // Low = engaging
    completion_rate: 0.88,
    save_rate: 0.15,
    
    // Ad adjacency performance
    ad_listen_through_before: 0.75,  // Ad performance when played before
    ad_listen_through_after: 0.82,   // Ad performance when played after
    
    // Timestamps
    created_at: datetime(),
    features_updated_at: datetime()
})

// Relationships
CREATE (t:Track)-[:BY_ARTIST]->(a:Artist)
CREATE (t:Track)-[:ON_ALBUM]->(al:Album)
CREATE (t:Track)-[:HAS_LYRICS]->(l:Lyrics)
CREATE (t:Track)-[:INDUCES_STATE {
    arousal: 0.89,
    valence: 0.94,
    confidence: 0.85
}]->(s:PsychologicalState)

// Indexes
CREATE INDEX track_id_idx FOR (t:Track) ON (t.track_id)
CREATE INDEX track_isrc_idx FOR (t:Track) ON (t.isrc)
CREATE INDEX track_energy_idx FOR (t:Track) ON (t.energy)
CREATE INDEX track_valence_idx FOR (t:Track) ON (t.valence)
```

### Track Psychological Inference

```python
# =============================================================================
# TRACK PSYCHOLOGICAL ANALYSIS
# =============================================================================

class TrackPsychologicalAnalyzer:
    """
    Analyze tracks for psychological signals used in:
    1. Listener profiling (what tracks reveal about listener)
    2. State priming (how track affects current psychological state)
    3. Ad adjacency optimization (which ads work after which tracks)
    """
    
    # Audio feature → Psychological dimension mappings
    # Based on Rentfrow et al. and music psychology research
    
    AUDIO_TO_PSYCH_MAPPING = {
        "energy": {
            "extraversion": 0.35,
            "arousal": 0.80,
            "promotion_focus": 0.25
        },
        "valence": {
            "neuroticism": -0.40,  # Negative correlation
            "positive_affect": 0.75,
            "approach_motivation": 0.35
        },
        "tempo": {
            "arousal": 0.45,
            "extraversion": 0.20
        },
        "acousticness": {
            "openness": 0.25,
            "introversion": 0.20
        },
        "complexity": {  # Derived from multiple features
            "openness": 0.40,
            "need_for_cognition": 0.30
        }
    }
    
    def analyze_track(self, track: Track) -> TrackPsychologicalProfile:
        """
        Generate comprehensive psychological profile for a track.
        """
        # Map audio features to psychological signals
        psych_signals = self._map_audio_to_psych(track)
        
        # Calculate state induction potential
        state_induction = self._calculate_state_induction(track)
        
        # Determine mechanism affinities
        mechanism_affinities = self._calculate_mechanism_affinities(track)
        
        return TrackPsychologicalProfile(
            track_id=track.track_id,
            psychological_signals=psych_signals,
            state_induction=state_induction,
            mechanism_affinities=mechanism_affinities,
            listener_profile_signals=self._calculate_listener_signals(track)
        )
    
    def _map_audio_to_psych(self, track: Track) -> Dict[str, float]:
        """Map audio features to psychological dimensions."""
        signals = defaultdict(float)
        weights = defaultdict(float)
        
        for feature, mappings in self.AUDIO_TO_PSYCH_MAPPING.items():
            feature_value = getattr(track, feature, 0.5)
            
            for psych_dim, correlation in mappings.items():
                if correlation < 0:
                    contribution = (1 - feature_value) * abs(correlation)
                else:
                    contribution = feature_value * correlation
                
                signals[psych_dim] += contribution
                weights[psych_dim] += abs(correlation)
        
        # Normalize
        return {
            dim: signals[dim] / weights[dim] if weights[dim] > 0 else 0.5
            for dim in signals
        }
    
    def _calculate_state_induction(self, track: Track) -> StateInduction:
        """
        Calculate how this track affects listener psychological state.
        
        Used for:
        - Priming effects on ad receptivity
        - Optimal ad timing
        - Context-aware copy selection
        """
        return StateInduction(
            arousal_change=track.energy - 0.5,  # Relative to neutral
            valence_change=track.valence - 0.5,
            
            # Regulatory focus priming
            promotion_priming=(track.energy + track.valence) / 2,
            prevention_priming=1 - track.valence,
            
            # Construal level priming
            # High complexity → abstract construal
            # Low complexity → concrete construal
            construal_direction="abstract" if track.complexity_score > 0.6 else "concrete",
            
            # Duration of effect (estimate)
            effect_duration_seconds=120,  # ~2 minutes after track
            effect_confidence=0.7
        )
    
    def _calculate_mechanism_affinities(self, track: Track) -> Dict[str, float]:
        """
        Determine which persuasion mechanisms are enhanced after this track.
        """
        affinities = {}
        
        # High energy → identity/aspiration mechanisms
        if track.energy > 0.7:
            affinities["identity_expression"] = 0.8
            affinities["aspiration"] = 0.75
        
        # High valence → social/approach mechanisms
        if track.valence > 0.7:
            affinities["social_proof"] = 0.75
            affinities["mimetic_desire"] = 0.7
        
        # Low valence → protection/prevention mechanisms
        if track.valence < 0.4:
            affinities["loss_aversion"] = 0.8
            affinities["protection"] = 0.75
        
        # Nostalgia potential (older tracks, certain genres)
        if track.release_year and track.release_year < 2010:
            affinities["nostalgia"] = min(0.95, 0.5 + (2010 - track.release_year) / 40)
        
        # Acoustic/unplugged → authenticity
        if track.acousticness > 0.6:
            affinities["authenticity"] = 0.8
        
        return affinities
```

---

## 1.4 Lyrics Entity and Processing

Lyrics provide the richest textual psychological signals in music content.

### Neo4j Schema

```cypher
// =============================================================================
// LYRICS NODE - Song lyrics with psychological analysis
// =============================================================================

CREATE (l:Lyrics {
    // Identity
    lyrics_id: "lyrics:USRC11700160",
    track_id: "spotify:track:4PTG3Z6ehGkBFwjybzWkR8",
    
    // Content (stored externally, hash for verification)
    content_hash: "sha256:a1b2c3...",
    word_count: 287,
    line_count: 42,
    
    // Linguistic Analysis
    language: "en",
    vocabulary_richness: 0.72,      // Type-token ratio
    avg_word_length: 4.2,
    reading_level: 6.5,             // Grade level
    
    // Sentiment Analysis
    overall_sentiment: 0.82,        // -1 to 1
    sentiment_variance: 0.15,       // Emotional consistency
    
    // Emotional Content (Plutchik's wheel)
    joy: 0.75,
    trust: 0.65,
    anticipation: 0.55,
    sadness: 0.10,
    fear: 0.05,
    anger: 0.08,
    surprise: 0.20,
    disgust: 0.02,
    
    // Theme Extraction
    primary_themes: ["love", "commitment", "devotion"],
    secondary_themes: ["longing", "promise"],
    theme_confidence: 0.85,
    
    // Psychological Construct Detection
    // LIWC-style categories
    self_reference: 0.12,           // "I", "me", "my" frequency
    other_reference: 0.18,          // "you", "we" frequency
    positive_emotion_words: 0.08,
    negative_emotion_words: 0.01,
    cognitive_processes: 0.05,      # "think", "know", "believe"
    social_words: 0.15,
    
    // Regulatory Focus Signals
    promotion_language: 0.65,       // Gain, achieve, aspire
    prevention_language: 0.25,      // Protect, safe, avoid
    
    // Construal Level Signals
    abstract_language: 0.40,        // Why, meaning, values
    concrete_language: 0.55,        // How, specific, action
    
    // Narrative Structure
    has_narrative: true,
    narrative_perspective: "first_person",
    temporal_orientation: "future", // Past, present, future
    
    // Brand Safety
    explicit_content: false,
    controversial_themes: [],
    brand_safe_score: 0.95,
    
    // Timestamps
    analyzed_at: datetime(),
    analysis_version: "2.0"
})

// Relationships
CREATE (l:Lyrics)-[:FOR_TRACK]->(t:Track)
CREATE (l:Lyrics)-[:CONTAINS_THEME]->(th:Theme)
CREATE (l:Lyrics)-[:EXPRESSES_EMOTION {intensity: 0.75}]->(e:Emotion)
CREATE (l:Lyrics)-[:SIGNALS_CONSTRUCT {strength: 0.65}]->(c:PsychologicalConstruct)
```

### Lyrics Processing Pipeline

```python
# =============================================================================
# LYRICS ANALYSIS SERVICE - Extract psychological signals from lyrics
# =============================================================================

class LyricsAnalysisService:
    """
    Process song lyrics to extract psychological signals that:
    1. Inform listener psychological state
    2. Guide content-ad matching
    3. Feed Discovery Engine for pattern detection
    4. Update user psychological profiles
    
    LEARNING INTEGRATION:
    - Lyrics themes → Content-mechanism effectiveness
    - Emotional content → State priming effects
    - Linguistic patterns → Construal level signals
    """
    
    def __init__(
        self,
        claude_client: Anthropic,
        embedding_service: EmbeddingService,
        graph: GraphService,
        gradient_bridge: GradientBridge
    ):
        self.claude = claude_client
        self.embeddings = embedding_service
        self.graph = graph
        self.gradient_bridge = gradient_bridge
    
    async def analyze_lyrics(self, lyrics_text: str, track_id: str) -> LyricsAnalysis:
        """
        Comprehensive lyrics analysis.
        
        Uses Claude for nuanced understanding, embeddings for similarity,
        and rule-based systems for reliability.
        """
        # 1. Basic linguistic analysis (fast, rule-based)
        linguistic = self._linguistic_analysis(lyrics_text)
        
        # 2. Sentiment and emotion (model-based)
        emotional = await self._emotional_analysis(lyrics_text)
        
        # 3. Theme extraction (Claude)
        themes = await self._extract_themes(lyrics_text)
        
        # 4. Psychological construct detection
        constructs = await self._detect_constructs(lyrics_text)
        
        # 5. Regulatory focus and construal signals
        focus_signals = self._analyze_regulatory_focus(lyrics_text)
        construal_signals = self._analyze_construal_level(lyrics_text)
        
        # 6. Brand safety check
        brand_safety = await self._check_brand_safety(lyrics_text)
        
        analysis = LyricsAnalysis(
            lyrics_id=f"lyrics:{track_id}",
            track_id=track_id,
            linguistic=linguistic,
            emotional=emotional,
            themes=themes,
            constructs=constructs,
            regulatory_focus=focus_signals,
            construal_level=construal_signals,
            brand_safety=brand_safety
        )
        
        # Store in graph
        await self.graph.store_lyrics_analysis(analysis)
        
        # Emit learning signal
        await self.gradient_bridge.propagate_signal(
            LearningSignal(
                source="lyrics_analysis",
                signal_type=LearningSignalType.CONTENT_ANALYSIS,
                entity_type="lyrics",
                entity_id=analysis.lyrics_id,
                payload={
                    "themes": themes,
                    "emotional_profile": emotional.dict(),
                    "constructs": constructs
                }
            )
        )
        
        return analysis
    
    async def _extract_themes(self, lyrics_text: str) -> List[Theme]:
        """
        Extract themes using Claude for nuanced understanding.
        """
        prompt = f"""Analyze these song lyrics and extract the main themes.

LYRICS:
{lyrics_text}

For each theme, provide:
1. Theme name (single word or short phrase)
2. Confidence (0-1)
3. Evidence (brief quote or description)
4. Psychological relevance (how this theme relates to listener psychology)

Return as JSON array of themes. Focus on themes that have psychological significance
for advertising and persuasion context."""

        response = await self.claude.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}]
        )
        
        # Parse and return themes
        themes_data = json.loads(response.content[0].text)
        return [Theme(**t) for t in themes_data]
    
    async def _detect_constructs(self, lyrics_text: str) -> Dict[str, float]:
        """
        Detect psychological constructs in lyrics.
        
        Maps to ADAM's core constructs:
        - Big Five signals
        - Regulatory focus signals
        - Construal level signals
        - Extended constructs (NFC, self-monitoring, etc.)
        """
        # LIWC-style word counting
        word_counts = self._count_psychological_words(lyrics_text)
        
        constructs = {}
        
        # Openness signals
        openness_words = ["dream", "imagine", "wonder", "explore", "discover", 
                         "create", "art", "beauty", "soul", "spirit"]
        constructs["openness_signal"] = self._word_frequency(lyrics_text, openness_words)
        
        # Conscientiousness signals
        conscient_words = ["work", "achieve", "goal", "plan", "discipline",
                          "responsible", "duty", "careful", "thorough"]
        constructs["conscientiousness_signal"] = self._word_frequency(lyrics_text, conscient_words)
        
        # Extraversion signals
        extraversion_words = ["party", "fun", "dance", "friends", "together",
                            "exciting", "energy", "loud", "celebrate"]
        constructs["extraversion_signal"] = self._word_frequency(lyrics_text, extraversion_words)
        
        # Neuroticism signals
        neuroticism_words = ["worry", "afraid", "anxious", "sad", "hurt",
                           "pain", "cry", "alone", "broken", "lost"]
        constructs["neuroticism_signal"] = self._word_frequency(lyrics_text, neuroticism_words)
        
        # Agreeableness signals
        agreeable_words = ["love", "care", "help", "kind", "together",
                         "share", "trust", "gentle", "warm", "friend"]
        constructs["agreeableness_signal"] = self._word_frequency(lyrics_text, agreeable_words)
        
        return constructs
    
    def _analyze_regulatory_focus(self, lyrics_text: str) -> RegulatoryFocusSignals:
        """
        Detect promotion vs. prevention focus in lyrics.
        """
        promotion_words = ["achieve", "gain", "win", "advance", "accomplish",
                         "hope", "dream", "aspire", "success", "growth",
                         "opportunity", "potential", "ideal", "wish"]
        
        prevention_words = ["safe", "protect", "avoid", "prevent", "secure",
                          "careful", "responsible", "ought", "should", "duty",
                          "must", "obligation", "vigilant", "maintain"]
        
        promotion_score = self._word_frequency(lyrics_text, promotion_words)
        prevention_score = self._word_frequency(lyrics_text, prevention_words)
        
        return RegulatoryFocusSignals(
            promotion_strength=promotion_score,
            prevention_strength=prevention_score,
            dominant="promotion" if promotion_score > prevention_score else "prevention"
        )
    
    def _analyze_construal_level(self, lyrics_text: str) -> ConstrualLevelSignals:
        """
        Detect abstract vs. concrete construal in lyrics.
        """
        abstract_words = ["why", "meaning", "purpose", "soul", "destiny",
                        "eternal", "forever", "always", "believe", "truth",
                        "essence", "spirit", "universe", "infinite"]
        
        concrete_words = ["how", "step", "now", "today", "here", "touch",
                        "feel", "see", "hear", "walk", "run", "hand",
                        "door", "road", "light", "sound"]
        
        abstract_score = self._word_frequency(lyrics_text, abstract_words)
        concrete_score = self._word_frequency(lyrics_text, concrete_words)
        
        return ConstrualLevelSignals(
            abstract_strength=abstract_score,
            concrete_strength=concrete_score,
            dominant_level=ConstrualLevel.ABSTRACT if abstract_score > concrete_score else ConstrualLevel.CONCRETE
        )
    
    def _word_frequency(self, text: str, word_list: List[str]) -> float:
        """Calculate normalized frequency of words from list in text."""
        words = text.lower().split()
        if not words:
            return 0.0
        
        count = sum(1 for word in words if word.strip('.,!?"\';:') in word_list)
        return min(1.0, count / len(words) * 10)  # Normalized, capped at 1.0
```

---

## 1.5 Podcast Domain Entities

Podcasts provide rich explicit psychological signals through spoken content.

### Neo4j Schema

```cypher
// =============================================================================
// PODCAST (SHOW) NODE
// =============================================================================

CREATE (p:Podcast {
    // Identity
    podcast_id: "iheart:podcast:12345",
    name: "The Joe Rogan Experience",
    
    // Classification
    category: "comedy",
    subcategories: ["interviews", "society_culture"],
    
    // Creator info
    host_names: ["Joe Rogan"],
    network: "Spotify/iHeart",
    
    // Psychological Profile (learned from content + listeners)
    psych_openness: 0.72,
    psych_conscientiousness: 0.45,
    psych_extraversion: 0.75,
    psych_agreeableness: 0.48,
    psych_neuroticism: 0.42,
    profile_confidence: 0.88,
    
    // Listener demographics
    median_age: 34,
    male_skew: 0.71,
    education_index: 0.62,
    
    // Content characteristics
    avg_episode_length_minutes: 165,
    release_frequency: "weekly",
    explicit_content: true,
    
    // Ad performance
    baseline_listen_through: 0.78,
    host_read_effectiveness: 1.85,  // 85% lift over produced
    
    // Topic profile (learned from transcripts)
    dominant_topics: ["mma", "comedy", "science", "politics", "philosophy"],
    topic_diversity: 0.82,
    
    // Mechanism affinities
    effective_mechanisms: ["authenticity", "parasocial", "curiosity"],
    
    // Timestamps
    created_at: datetime(),
    profile_updated_at: datetime()
})

// =============================================================================
// EPISODE NODE
// =============================================================================

CREATE (e:Episode {
    // Identity
    episode_id: "iheart:episode:67890",
    podcast_id: "iheart:podcast:12345",
    
    title: "Episode #2050 - Neil deGrasse Tyson",
    episode_number: 2050,
    
    // Publication
    published_at: datetime("2024-01-15"),
    duration_seconds: 10800,  // 3 hours
    
    // Content
    description: "Neil deGrasse Tyson returns...",
    guests: ["Neil deGrasse Tyson"],
    
    // Topics (extracted from transcript)
    topics: ["astrophysics", "space_exploration", "science_communication"],
    topic_confidence: 0.92,
    
    // Psychological characteristics
    intellectual_depth: 0.85,
    emotional_intensity: 0.45,
    humor_level: 0.55,
    controversy_level: 0.30,
    
    // Transcript reference
    transcript_id: "transcript:67890",
    has_transcript: true,
    
    // Ad slots
    ad_slot_positions: [180, 1800, 3600, 5400, 7200],  // Seconds
    total_ad_slots: 5,
    
    // Performance
    downloads: 2500000,
    completion_rate: 0.72,
    
    // Timestamps
    created_at: datetime(),
    analyzed_at: datetime()
})

// =============================================================================
// TRANSCRIPT NODE
// =============================================================================

CREATE (tr:Transcript {
    // Identity
    transcript_id: "transcript:67890",
    episode_id: "iheart:episode:67890",
    
    // Content metadata (actual text stored externally)
    word_count: 45000,
    speaker_count: 2,
    speakers: ["Joe Rogan", "Neil deGrasse Tyson"],
    
    // Linguistic analysis
    vocabulary_richness: 0.78,
    avg_turn_length: 125,  // Words per speaker turn
    interruption_rate: 0.12,
    
    // Topic extraction
    topic_segments: [
        {start: 0, end: 1200, topic: "introduction"},
        {start: 1200, end: 3000, topic: "black_holes"},
        // ...
    ],
    
    // Sentiment flow
    sentiment_by_segment: [0.65, 0.70, 0.55, ...],
    emotional_peaks: [1850, 4200, 7800],  // Timestamps of high emotion
    
    // Psychological signals
    curiosity_expressions: 45,
    agreement_expressions: 82,
    disagreement_expressions: 12,
    
    // Ad-relevant analysis
    brand_mentions: [],
    product_category_mentions: ["technology", "space"],
    optimal_ad_positions: [1800, 5400],  // After natural breaks
    
    // Timestamps
    transcribed_at: datetime(),
    analyzed_at: datetime()
})
```

### Transcript Processing Service

```python
# =============================================================================
# TRANSCRIPT ANALYSIS - Extract psychological signals from podcast speech
# =============================================================================

class TranscriptAnalysisService:
    """
    Analyze podcast transcripts for:
    1. Topic extraction for content-ad matching
    2. Emotional flow for optimal ad placement
    3. Psychological construct signals
    4. Brand safety and contextual relevance
    
    LEARNING INTEGRATION:
    - Topic × ad performance → Content targeting optimization
    - Emotional context × mechanism effectiveness → Timing optimization
    - Speaker patterns → Parasocial relationship signals
    """
    
    def __init__(
        self,
        claude_client: Anthropic,
        embedding_service: EmbeddingService,
        graph: GraphService,
        gradient_bridge: GradientBridge
    ):
        self.claude = claude_client
        self.embeddings = embedding_service
        self.graph = graph
        self.gradient_bridge = gradient_bridge
    
    async def analyze_transcript(
        self,
        transcript_text: str,
        episode_id: str,
        speakers: List[str]
    ) -> TranscriptAnalysis:
        """
        Comprehensive transcript analysis.
        """
        # 1. Speaker diarization and turn analysis
        turns = self._parse_speaker_turns(transcript_text, speakers)
        
        # 2. Topic segmentation
        topics = await self._segment_topics(transcript_text)
        
        # 3. Sentiment and emotional flow
        emotional_flow = await self._analyze_emotional_flow(turns)
        
        # 4. Psychological construct detection
        constructs = await self._detect_constructs(transcript_text)
        
        # 5. Optimal ad placement analysis
        ad_positions = self._identify_optimal_ad_positions(
            topics, emotional_flow, len(transcript_text)
        )
        
        # 6. Brand safety
        brand_safety = await self._check_brand_safety(transcript_text, topics)
        
        analysis = TranscriptAnalysis(
            transcript_id=f"transcript:{episode_id}",
            episode_id=episode_id,
            turns=turns,
            topics=topics,
            emotional_flow=emotional_flow,
            constructs=constructs,
            optimal_ad_positions=ad_positions,
            brand_safety=brand_safety
        )
        
        # Store
        await self.graph.store_transcript_analysis(analysis)
        
        # Emit learning signal
        await self.gradient_bridge.propagate_signal(
            LearningSignal(
                source="transcript_analysis",
                signal_type=LearningSignalType.CONTENT_ANALYSIS,
                entity_type="transcript",
                entity_id=analysis.transcript_id,
                payload={
                    "topics": [t.dict() for t in topics],
                    "constructs": constructs
                }
            )
        )
        
        return analysis
    
    async def _segment_topics(
        self,
        transcript_text: str
    ) -> List[TopicSegment]:
        """
        Segment transcript into topic regions.
        
        Used for:
        - Content-ad relevance matching
        - Topic-based targeting
        - Dynamic ad creative selection
        """
        # Use Claude for topic extraction
        prompt = f"""Analyze this podcast transcript and identify distinct topic segments.

TRANSCRIPT (first 5000 chars):
{transcript_text[:5000]}

For each segment, provide:
1. Start position (approximate word count from beginning)
2. Topic name (brief, specific)
3. Related product categories (for advertising relevance)
4. Psychological relevance (what listener mindset this creates)

Return as JSON array."""

        response = await self.claude.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}]
        )
        
        segments_data = json.loads(response.content[0].text)
        return [TopicSegment(**s) for s in segments_data]
    
    def _identify_optimal_ad_positions(
        self,
        topics: List[TopicSegment],
        emotional_flow: EmotionalFlow,
        content_length: int
    ) -> List[OptimalAdPosition]:
        """
        Identify optimal positions for ad insertion.
        
        Considers:
        - Topic transitions (natural breaks)
        - Emotional valleys (lower intensity = better ad reception)
        - Content pacing
        - Listener engagement patterns
        """
        positions = []
        
        # 1. Topic transitions are natural ad positions
        for i in range(1, len(topics)):
            prev_topic = topics[i-1]
            curr_topic = topics[i]
            
            positions.append(OptimalAdPosition(
                position_type="topic_transition",
                start_offset=prev_topic.end_position,
                relevance_context=f"After {prev_topic.topic}, before {curr_topic.topic}",
                recommended_categories=prev_topic.related_categories + curr_topic.related_categories,
                quality_score=0.85
            ))
        
        # 2. Emotional valleys
        for valley in emotional_flow.valleys:
            positions.append(OptimalAdPosition(
                position_type="emotional_valley",
                start_offset=valley.position,
                relevance_context=f"Low intensity moment",
                quality_score=0.75
            ))
        
        # 3. Standard positions (every 15-20 minutes)
        standard_interval = content_length // 5
        for i in range(1, 5):
            positions.append(OptimalAdPosition(
                position_type="time_based",
                start_offset=i * standard_interval,
                quality_score=0.65
            ))
        
        # Sort by quality and remove duplicates
        positions.sort(key=lambda p: p.quality_score, reverse=True)
        
        return self._deduplicate_positions(positions)
```

---

# PART 2: ADVERTISING DOMAIN DATA MODEL

## 2.1 Brand Entity

Brands are first-class entities with their own psychological profiles and voice guidelines.

### Neo4j Schema

```cypher
// =============================================================================
// BRAND NODE - Advertiser brand with psychological profile
// =============================================================================

CREATE (b:Brand {
    // Identity
    brand_id: "brand:nike",
    name: "Nike",
    parent_company: "Nike, Inc.",
    
    // Category
    primary_category: "athletic_footwear",
    categories: ["athletic_footwear", "athletic_apparel", "sports_equipment"],
    
    // Brand Personality (Aaker's dimensions)
    sincerity: 0.55,
    excitement: 0.88,      // HIGH - "Just Do It"
    competence: 0.82,
    sophistication: 0.65,
    ruggedness: 0.72,
    
    // Psychological Profile
    brand_openness: 0.75,
    brand_extraversion: 0.85,
    brand_conscientiousness: 0.70,
    
    // Target audience psychological profile
    target_openness_min: 0.5,
    target_openness_max: 0.9,
    target_extraversion_min: 0.6,
    target_extraversion_max: 1.0,
    
    // Regulatory focus alignment
    promotion_alignment: 0.90,     // Strong promotion focus
    prevention_alignment: 0.25,
    
    // Voice Guidelines
    tone: "inspirational_empowering",
    vocabulary_level: "accessible",
    humor_style: "aspirational",    // Not sarcastic
    formality: "casual_confident",
    
    // Constraints
    prohibited_words: ["cheap", "budget", "discount"],
    required_phrases: [],
    competitor_mentions: "never",
    
    // Brand Safety
    controversial_topics_stance: "avoid",
    political_content_stance: "neutral",
    explicit_content_tolerance: "low",
    
    // Mechanism Affinities (which mechanisms align with brand)
    mechanism_affinities: {
        "aspiration": 0.95,
        "identity_expression": 0.90,
        "social_proof": 0.80,
        "achievement": 0.85,
        "authenticity": 0.75
    },
    
    // Historical performance
    avg_ctr: 0.012,
    avg_listen_through: 0.78,
    avg_conversion: 0.008,
    
    // Content affinities (which content works for this brand)
    station_format_affinities: {
        "CHR": 0.75,
        "URBAN": 0.85,
        "SPORTS": 0.90
    },
    podcast_category_affinities: {
        "sports": 0.95,
        "health_fitness": 0.85,
        "comedy": 0.60
    },
    
    // Timestamps
    created_at: datetime(),
    profile_updated_at: datetime()
})

// Relationships
CREATE (b:Brand)-[:COMPETES_WITH]->(b2:Brand)
CREATE (b:Brand)-[:TARGETS_SEGMENT]->(ps:PsychographicSegment)
CREATE (b:Brand)-[:HAS_AFFINITY_FOR {strength: 0.85}]->(sf:StationFormat)
```

### Brand-User Psychological Matching

```python
# =============================================================================
# BRAND-USER PSYCHOLOGICAL MATCHING
# =============================================================================

class BrandUserMatchingService:
    """
    Match brands to users based on psychological compatibility.
    
    LEARNING INTEGRATION:
    - Brand × User outcomes → Brand targeting refinement
    - Brand voice × User personality → Copy optimization
    - Brand mechanisms × User profiles → Mechanism selection
    """
    
    def __init__(
        self,
        graph: GraphService,
        gradient_bridge: GradientBridge
    ):
        self.graph = graph
        self.gradient_bridge = gradient_bridge
    
    async def calculate_brand_user_affinity(
        self,
        brand: Brand,
        user_profile: UserProfile
    ) -> BrandUserAffinity:
        """
        Calculate psychological affinity between brand and user.
        
        Based on:
        1. Personality congruence (brand personality ↔ user personality)
        2. Regulatory focus alignment
        3. Values/mechanism compatibility
        """
        # 1. Personality congruence
        personality_match = self._calculate_personality_congruence(
            brand, user_profile
        )
        
        # 2. Regulatory focus alignment
        focus_match = self._calculate_focus_alignment(brand, user_profile)
        
        # 3. Mechanism compatibility
        mechanism_match = self._calculate_mechanism_compatibility(
            brand, user_profile
        )
        
        # Weighted combination
        overall_affinity = (
            personality_match * 0.40 +
            focus_match * 0.30 +
            mechanism_match * 0.30
        )
        
        return BrandUserAffinity(
            brand_id=brand.brand_id,
            user_id=user_profile.user_id,
            overall_affinity=overall_affinity,
            personality_match=personality_match,
            focus_match=focus_match,
            mechanism_match=mechanism_match,
            recommended_mechanisms=self._get_recommended_mechanisms(
                brand, user_profile, mechanism_match
            )
        )
    
    def _calculate_personality_congruence(
        self,
        brand: Brand,
        user: UserProfile
    ) -> float:
        """
        Calculate personality congruence using self-congruity theory.
        
        Users prefer brands with personality similar to their own
        or their ideal self.
        """
        # Map Aaker brand dimensions to Big Five
        brand_as_big_five = {
            "openness": (brand.excitement + brand.sophistication) / 2,
            "conscientiousness": brand.competence,
            "extraversion": brand.excitement,
            "agreeableness": brand.sincerity,
            "neuroticism": 1 - brand.ruggedness  # Inverse
        }
        
        # Calculate Euclidean distance (lower = more similar)
        distance = sum(
            (brand_as_big_five[trait] - getattr(user.big_five, trait)) ** 2
            for trait in brand_as_big_five
        ) ** 0.5
        
        # Convert to similarity (0-1)
        max_distance = 5 ** 0.5  # Maximum possible distance
        similarity = 1 - (distance / max_distance)
        
        return similarity
    
    def _calculate_focus_alignment(
        self,
        brand: Brand,
        user: UserProfile
    ) -> float:
        """
        Calculate regulatory focus alignment.
        
        Promotion-focused users respond better to promotion-aligned brands.
        Prevention-focused users respond better to prevention-aligned brands.
        """
        user_promotion = user.regulatory_focus.promotion_strength
        user_prevention = user.regulatory_focus.prevention_strength
        
        brand_promotion = brand.promotion_alignment
        brand_prevention = brand.prevention_alignment
        
        # Alignment score
        promotion_alignment = 1 - abs(user_promotion - brand_promotion)
        prevention_alignment = 1 - abs(user_prevention - brand_prevention)
        
        # Weight by user's dominant focus
        if user_promotion > user_prevention:
            return promotion_alignment * 0.7 + prevention_alignment * 0.3
        else:
            return prevention_alignment * 0.7 + promotion_alignment * 0.3
    
    def _calculate_mechanism_compatibility(
        self,
        brand: Brand,
        user: UserProfile
    ) -> float:
        """
        Calculate how well brand's preferred mechanisms match user's receptivity.
        """
        if not brand.mechanism_affinities:
            return 0.5
        
        # Get user's mechanism receptivity (from profile or priors)
        user_mechanisms = user.mechanism_receptivity or {}
        
        compatibility_scores = []
        for mechanism, brand_affinity in brand.mechanism_affinities.items():
            user_receptivity = user_mechanisms.get(mechanism, 0.5)
            
            # High brand affinity + high user receptivity = good match
            compatibility = brand_affinity * user_receptivity
            compatibility_scores.append(compatibility)
        
        return np.mean(compatibility_scores) if compatibility_scores else 0.5
```

---

## 2.2 Campaign and Creative Entities

### Neo4j Schema

```cypher
// =============================================================================
// CAMPAIGN NODE - Advertising campaign
// =============================================================================

CREATE (c:Campaign {
    // Identity
    campaign_id: "campaign:nike_airmax_2025",
    brand_id: "brand:nike",
    name: "Air Max 2025 Launch",
    
    // Flight
    start_date: date("2025-02-01"),
    end_date: date("2025-03-31"),
    status: "active",
    
    // Budget
    total_budget: 5000000,
    daily_budget: 100000,
    spend_to_date: 2500000,
    
    // Targeting
    target_markets: ["Los Angeles", "New York", "Chicago"],
    target_formats: ["CHR", "URBAN", "SPORTS"],
    target_podcasts: ["health_fitness", "sports"],
    
    // Psychological targeting
    target_openness_range: [0.5, 0.9],
    target_extraversion_range: [0.6, 1.0],
    target_promotion_focus_min: 0.6,
    
    // Mechanism preferences
    preferred_mechanisms: ["aspiration", "identity_expression", "social_proof"],
    
    // Goals
    primary_kpi: "conversions",
    target_ctr: 0.015,
    target_conversion: 0.01,
    
    // Creative settings
    creative_ids: ["creative:nike_airmax_001", "creative:nike_airmax_002"],
    allow_copy_optimization: true,
    
    // Performance
    impressions: 25000000,
    clicks: 375000,
    conversions: 25000,
    
    // Timestamps
    created_at: datetime(),
    updated_at: datetime()
})

// =============================================================================
// CREATIVE NODE - Ad creative (what gets shown)
// =============================================================================

CREATE (cr:Creative {
    // Identity
    creative_id: "creative:nike_airmax_001",
    campaign_id: "campaign:nike_airmax_2025",
    brand_id: "brand:nike",
    name: "Air Max - Just Do It",
    
    // Type
    creative_type: "audio",          // "audio", "display", "video"
    format: "30_second_spot",
    duration_seconds: 30,
    
    // Base content
    base_copy: "The new Nike Air Max. Engineered for those who never stop pushing...",
    base_audio_url: "s3://creatives/nike_airmax_001_base.mp3",
    
    // Voice
    voice_id: "voice:athletic_male_35",
    voice_gender: "male",
    base_energy: 0.75,
    base_pace: "medium_fast",
    
    // Copy variants (ADAM-generated)
    copy_variants: [
        {
            variant_id: "v1_promotion",
            copy: "Achieve your next personal best with...",
            target_focus: "promotion",
            target_construal: "abstract"
        },
        {
            variant_id: "v2_prevention", 
            copy: "Don't let anything hold you back...",
            target_focus: "prevention",
            target_construal: "concrete"
        }
    ],
    
    // Mechanism alignment
    primary_mechanism: "aspiration",
    secondary_mechanisms: ["identity_expression", "achievement"],
    
    // Brand compliance
    brand_voice_score: 0.92,
    compliance_approved: true,
    
    // Performance by variant
    variant_performance: {
        "v1_promotion": {"ctr": 0.016, "conversion": 0.012},
        "v2_prevention": {"ctr": 0.013, "conversion": 0.009}
    },
    
    // Timestamps
    created_at: datetime(),
    updated_at: datetime()
})
```

---

## 2.3 Inventory and Ad Slot Entities

### Neo4j Schema

```cypher
// =============================================================================
// INVENTORY NODE - Available ad inventory
// =============================================================================

CREATE (inv:Inventory {
    // Identity
    inventory_id: "inv:kiisfm_2025q1",
    
    // Source
    source_type: "station",          // "station", "podcast"
    source_id: "KIIS-FM",
    
    // Availability
    total_slots_daily: 288,          // Every 5 minutes
    available_slots_daily: 180,      // Unsold
    
    // Pricing
    base_cpm: 15.00,
    dynamic_pricing_enabled: true,
    premium_multiplier_primetime: 1.5,
    
    // Targeting availability
    supports_psychographic: true,
    supports_behavioral: true,
    min_impression_guarantee: 1000,
    
    // Performance baselines
    baseline_listen_through: 0.72,
    baseline_ctr: 0.008,
    
    // Time segments
    daypart_availability: {
        "morning_drive": 48,
        "midday": 72,
        "afternoon_drive": 48,
        "evening": 60,
        "overnight": 60
    },
    
    // Timestamps
    updated_at: datetime()
})

// =============================================================================
// AD_SLOT NODE - Specific ad opportunity
// =============================================================================

CREATE (slot:AdSlot {
    // Identity
    slot_id: "slot:kiisfm_20250120_0815",
    inventory_id: "inv:kiisfm_2025q1",
    
    // Timing
    scheduled_time: datetime("2025-01-20T08:15:00"),
    duration_seconds: 30,
    position_in_break: 1,           // 1st, 2nd, 3rd in break
    break_total_slots: 4,
    
    // Context
    preceding_content_type: "music",
    preceding_track_id: "spotify:track:xxx",
    following_content_type: "music",
    
    // Psychological context (derived from preceding content)
    context_energy: 0.75,
    context_valence: 0.68,
    context_arousal: 0.72,
    
    // Pricing
    base_price: 0.015,              // CPM
    current_price: 0.018,           // With demand
    
    // Status
    status: "available",            // "available", "reserved", "filled"
    booked_by: null,
    
    // Performance prediction
    predicted_listen_through: 0.74,
    predicted_ctr: 0.009,
    
    // Optimal creative characteristics
    optimal_energy_match: 0.70,     // Match preceding content
    optimal_mechanism: "momentum"   // Continue energy
})
```

---

# PART 3: AD NETWORK INTEGRATION LAYER

## 3.1 Ad Request/Response Protocol

This is the core integration point where iHeart's ad server communicates with ADAM.

### Request Schema

```python
# =============================================================================
# AD REQUEST - What iHeart sends to ADAM
# =============================================================================

class iHeartAdRequest(BaseModel):
    """
    Ad request from iHeart's ad server to ADAM.
    
    Contains all context needed for psychological ad selection.
    """
    # Request identification
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Listener identification
    iheart_user_id: Optional[str] = None      # iHeart's user ID
    device_id: Optional[str] = None           # Device identifier
    session_id: str                           # Current listening session
    
    # Identity resolution hints
    identity_hints: Optional[Dict[str, str]] = None  # UID2, RampID, etc.
    
    # Content context
    content_type: str                         # "music", "podcast", "talk"
    station_id: Optional[str] = None          # For radio
    podcast_id: Optional[str] = None          # For podcasts
    episode_id: Optional[str] = None
    
    # Current content (what's playing/just played)
    current_track_id: Optional[str] = None
    current_artist_id: Optional[str] = None
    current_genres: List[str] = Field(default_factory=list)
    
    # Audio features of current content
    current_energy: Optional[float] = None
    current_valence: Optional[float] = None
    current_tempo: Optional[float] = None
    
    # For podcasts: topic context
    current_topic: Optional[str] = None
    transcript_segment: Optional[str] = None  # Recent transcript
    
    # Ad slot information
    slot_id: str
    slot_duration_seconds: int = 30
    slot_position: str                        # "pre", "mid", "post"
    position_in_break: int = 1
    
    # Listening context
    listening_duration_seconds: int           # How long they've been listening
    session_skip_count: int = 0
    session_ad_count: int = 0                 # Ads already heard this session
    
    # Device context
    platform: str                             # "ios", "android", "web", "smart_speaker"
    connection_type: str = "unknown"          # "wifi", "cellular"
    
    # Geographic context
    market: Optional[str] = None
    dma_code: Optional[str] = None
    
    # Time context
    local_time: datetime
    day_of_week: int
    
    # Campaign constraints (which campaigns are eligible)
    eligible_campaign_ids: Optional[List[str]] = None
    excluded_brand_ids: Optional[List[str]] = None
    
    # Latency requirement
    max_response_time_ms: int = 100


class ContentContext(BaseModel):
    """Enriched content context for psychological state inference."""
    # From track/episode
    content_id: str
    content_type: str
    
    # Psychological characteristics
    energy: float
    valence: float
    arousal: float
    
    # Inferred listener state
    induced_promotion_focus: float
    induced_prevention_focus: float
    induced_construal_level: str
    
    # Mechanism priming
    primed_mechanisms: List[str]
    priming_strength: Dict[str, float]
    
    # Topic/theme context (for podcasts)
    active_topics: List[str] = Field(default_factory=list)
    emotional_context: str = "neutral"
```

### Response Schema

```python
# =============================================================================
# AD RESPONSE - What ADAM returns to iHeart
# =============================================================================

class iHeartAdResponse(BaseModel):
    """
    Ad response from ADAM to iHeart's ad server.
    
    Contains selected creative, personalized copy, and audio parameters.
    """
    # Request correlation
    request_id: str
    response_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    
    # Decision metadata
    decision_id: str                          # For outcome tracking
    decision_latency_ms: float
    decision_confidence: float
    
    # Selected creative
    creative_id: str
    campaign_id: str
    brand_id: str
    
    # Personalized copy
    copy_variant_id: str
    final_copy: str                           # The actual text to speak
    
    # Audio parameters
    audio_url: Optional[str] = None           # Pre-rendered audio if available
    voice_id: str
    speaking_rate: float = 1.0                # 0.8-1.2x
    pitch_adjustment: float = 0.0             # Semitones
    energy_level: float = 0.5
    
    # SSML if dynamic rendering needed
    ssml: Optional[str] = None
    
    # Psychological targeting used
    target_profile: Dict[str, Any]            # For debugging/analysis
    mechanisms_activated: List[str]
    regulatory_focus_framing: str             # "promotion", "prevention", "neutral"
    construal_level: str                      # "abstract", "concrete"
    
    # Timing recommendation
    optimal_position_in_break: int = 1
    position_rationale: str
    
    # Attribution data (for learning)
    attribution_data: AttributionData
    
    # Fallback info
    is_fallback: bool = False
    fallback_reason: Optional[str] = None
    
    # Cache control
    cache_ttl_seconds: int = 0                # 0 = don't cache
    
    # Pricing
    winning_bid_cpm: Optional[float] = None


class AttributionData(BaseModel):
    """Data needed for outcome attribution."""
    decision_id: str
    user_id_adam: str                         # ADAM's resolved user ID
    user_id_iheart: Optional[str]
    
    # What we knew at decision time
    user_profile_snapshot: Dict[str, Any]
    content_context_snapshot: Dict[str, Any]
    
    # What we predicted
    predicted_ctr: float
    predicted_listen_through: float
    predicted_conversion: Optional[float]
    
    # What mechanisms we used
    mechanisms_used: List[str]
    mechanism_weights: Dict[str, float]
    
    # Creative selection rationale
    creative_selection_reason: str
    copy_selection_reason: str
    
    # For learning
    experiment_id: Optional[str] = None
    experiment_variant: Optional[str] = None
```

### Ad Decision Service

```python
# =============================================================================
# AD DECISION SERVICE - Core integration logic
# =============================================================================

class iHeartAdDecisionService:
    """
    Main entry point for iHeart ad requests.
    
    Orchestrates:
    1. User profile resolution
    2. Content context analysis
    3. Campaign/creative selection
    4. Copy personalization
    5. Outcome prediction
    6. Response construction
    
    LEARNING INTEGRATION:
    - Every decision creates a learning opportunity
    - Outcomes flow back through attribution data
    - All predictions are logged for model improvement
    """
    
    def __init__(
        self,
        graph: GraphService,
        cache: CacheService,
        identity_resolver: IdentityResolutionService,
        profile_service: UserProfileService,
        content_analyzer: ContentContextAnalyzer,
        campaign_selector: CampaignSelectionService,
        copy_generator: CopyGenerationService,
        cold_start: ColdStartService,
        ab_testing: ABTestingService,
        blackboard: BlackboardService,
        gradient_bridge: GradientBridge,
        kafka: KafkaProducer
    ):
        self.graph = graph
        self.cache = cache
        self.identity = identity_resolver
        self.profiles = profile_service
        self.content = content_analyzer
        self.campaigns = campaign_selector
        self.copy = copy_generator
        self.cold_start = cold_start
        self.ab_testing = ab_testing
        self.blackboard = blackboard
        self.gradient_bridge = gradient_bridge
        self.kafka = kafka
    
    async def process_ad_request(
        self,
        request: iHeartAdRequest
    ) -> iHeartAdResponse:
        """
        Process an ad request from iHeart.
        
        Target latency: <100ms total
        """
        start_time = datetime.utcnow()
        decision_id = str(uuid.uuid4())
        
        # Initialize blackboard for this request
        await self.blackboard.initialize_request(
            request_id=request.request_id,
            user_id=request.iheart_user_id or "anonymous",
            context={"source": "iheart", "slot_id": request.slot_id}
        )
        
        try:
            # 1. RESOLVE USER IDENTITY (5-10ms)
            adam_user_id = await self._resolve_user(request)
            
            # 2. GET/BUILD USER PROFILE (10-20ms)
            user_profile, mechanism_priors = await self._get_user_profile(
                adam_user_id, request
            )
            
            # 3. ANALYZE CONTENT CONTEXT (5-10ms)
            content_context = await self._analyze_content_context(request)
            
            # 4. UPDATE STATE FROM CONTENT (5ms)
            current_state = self._calculate_current_state(
                user_profile, content_context
            )
            
            # 5. SELECT CAMPAIGN/CREATIVE (15-25ms)
            selection = await self._select_campaign_creative(
                user_profile=user_profile,
                current_state=current_state,
                mechanism_priors=mechanism_priors,
                content_context=content_context,
                request=request
            )
            
            # 6. GENERATE PERSONALIZED COPY (15-25ms)
            copy_result = await self._generate_copy(
                selection=selection,
                user_profile=user_profile,
                current_state=current_state,
                content_context=content_context
            )
            
            # 7. CALCULATE AUDIO PARAMETERS (5ms)
            audio_params = self._calculate_audio_parameters(
                user_profile, current_state, selection.creative
            )
            
            # 8. PREDICT OUTCOMES (5ms)
            predictions = self._predict_outcomes(
                user_profile, selection, copy_result, content_context
            )
            
            # 9. BUILD ATTRIBUTION DATA
            attribution = AttributionData(
                decision_id=decision_id,
                user_id_adam=adam_user_id,
                user_id_iheart=request.iheart_user_id,
                user_profile_snapshot=user_profile.dict(),
                content_context_snapshot=content_context.dict(),
                predicted_ctr=predictions.ctr,
                predicted_listen_through=predictions.listen_through,
                predicted_conversion=predictions.conversion,
                mechanisms_used=selection.mechanisms,
                mechanism_weights=selection.mechanism_weights,
                creative_selection_reason=selection.reason,
                copy_selection_reason=copy_result.selection_reason,
                experiment_id=selection.experiment_id,
                experiment_variant=selection.experiment_variant
            )
            
            # 10. BUILD RESPONSE
            latency_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            response = iHeartAdResponse(
                request_id=request.request_id,
                decision_id=decision_id,
                decision_latency_ms=latency_ms,
                decision_confidence=selection.confidence,
                creative_id=selection.creative.creative_id,
                campaign_id=selection.campaign.campaign_id,
                brand_id=selection.campaign.brand_id,
                copy_variant_id=copy_result.variant_id,
                final_copy=copy_result.copy,
                voice_id=audio_params.voice_id,
                speaking_rate=audio_params.speaking_rate,
                energy_level=audio_params.energy,
                ssml=copy_result.ssml,
                target_profile={
                    "big_five": user_profile.big_five.dict(),
                    "regulatory_focus": user_profile.regulatory_focus.dict(),
                    "data_tier": user_profile.data_tier.value
                },
                mechanisms_activated=selection.mechanisms,
                regulatory_focus_framing=copy_result.framing,
                construal_level=copy_result.construal,
                attribution_data=attribution
            )
            
            # 11. EMIT EVENTS FOR LEARNING
            await self._emit_decision_events(
                request, response, user_profile, content_context, selection
            )
            
            return response
            
        except Exception as e:
            # Log error, return fallback
            logger.error(f"Ad decision error: {e}")
            return await self._build_fallback_response(request, str(e))
    
    async def _resolve_user(self, request: iHeartAdRequest) -> str:
        """
        Resolve iHeart user ID to ADAM canonical ID.
        """
        if request.iheart_user_id:
            # Try to resolve to existing ADAM user
            resolved = await self.identity.resolve(
                platform="iheart",
                platform_id=request.iheart_user_id,
                hints=request.identity_hints
            )
            if resolved:
                return resolved.canonical_id
        
        # Create anonymous ID from session
        return f"anon:{request.session_id}"
    
    async def _get_user_profile(
        self,
        adam_user_id: str,
        request: iHeartAdRequest
    ) -> Tuple[UserProfile, Dict[str, MechanismEffectiveness]]:
        """
        Get user profile, using cold start if necessary.
        
        LEARNING INTEGRATION:
        - Rich users: Use learned profile
        - Cold users: Use station/format priors
        - Anonymous: Use content context priors
        """
        # Try cache first
        cached = await self.cache.get_user_profile(adam_user_id)
        if cached:
            priors = await self.cache.get_user_mechanism_priors(adam_user_id)
            return cached, priors
        
        # Check graph
        profile = await self.graph.get_user_profile(adam_user_id)
        
        if profile and profile.profile_confidence > 0.6:
            # Rich user - use learned profile
            priors = await self.graph.get_user_mechanism_priors(adam_user_id)
            return profile, priors
        
        # Cold start - build from context
        context = {
            "station_id": request.station_id,
            "podcast_id": request.podcast_id,
            "format": await self._get_station_format(request.station_id),
            "time_of_day": request.local_time.hour,
            "content_genres": request.current_genres
        }
        
        return await self.cold_start.bootstrap_profile(
            user_id=adam_user_id,
            context=context,
            signals=None  # No supraliminal signals for audio-only
        )
    
    async def _analyze_content_context(
        self,
        request: iHeartAdRequest
    ) -> ContentContext:
        """
        Analyze current content for psychological context.
        
        LEARNING INTEGRATION:
        - Content features → State priming
        - Lyrics/transcript → Mechanism priming
        - Topic context → Ad relevance
        """
        if request.current_track_id:
            # Music context
            track = await self.graph.get_track(request.current_track_id)
            
            return ContentContext(
                content_id=track.track_id,
                content_type="music",
                energy=track.energy,
                valence=track.valence,
                arousal=self._calculate_arousal(track),
                induced_promotion_focus=self._track_promotion_priming(track),
                induced_prevention_focus=self._track_prevention_priming(track),
                induced_construal_level=self._track_construal_priming(track),
                primed_mechanisms=track.mechanism_affinities or [],
                priming_strength=track.mechanism_affinities or {}
            )
        
        elif request.episode_id:
            # Podcast context
            episode = await self.graph.get_episode(request.episode_id)
            
            return ContentContext(
                content_id=episode.episode_id,
                content_type="podcast",
                energy=episode.emotional_intensity or 0.5,
                valence=0.5,  # Neutral default for talk
                arousal=episode.intellectual_depth or 0.5,
                induced_promotion_focus=0.5,
                induced_prevention_focus=0.5,
                induced_construal_level="abstract" if episode.intellectual_depth > 0.6 else "concrete",
                primed_mechanisms=episode.effective_mechanisms or [],
                priming_strength={},
                active_topics=episode.topics or [],
                emotional_context=episode.emotional_context or "neutral"
            )
        
        else:
            # Fallback to station-level context
            station = await self.graph.get_station(request.station_id)
            return self._station_to_content_context(station)
    
    async def _emit_decision_events(
        self,
        request: iHeartAdRequest,
        response: iHeartAdResponse,
        user_profile: UserProfile,
        content_context: ContentContext,
        selection: CreativeSelection
    ):
        """
        Emit events for learning integration.
        
        These events feed:
        - Gradient Bridge for learning propagation
        - A/B Testing for experiment tracking
        - Model Monitoring for drift detection
        - Discovery Engine for pattern mining
        """
        # Decision event
        await self.kafka.send(
            "ad_decisions",
            AdDecisionEvent(
                decision_id=response.decision_id,
                request_id=request.request_id,
                user_id=response.attribution_data.user_id_adam,
                station_id=request.station_id,
                podcast_id=request.podcast_id,
                campaign_id=response.campaign_id,
                creative_id=response.creative_id,
                mechanisms=response.mechanisms_activated,
                predicted_ctr=response.attribution_data.predicted_ctr,
                user_data_tier=user_profile.data_tier.value,
                content_energy=content_context.energy,
                content_valence=content_context.valence,
                timestamp=datetime.utcnow()
            )
        )
        
        # Learning signal
        await self.gradient_bridge.propagate_signal(
            LearningSignal(
                source="iheart_ad_decision",
                signal_type=LearningSignalType.PREDICTION,
                entity_type="ad_decision",
                entity_id=response.decision_id,
                payload={
                    "user_id": response.attribution_data.user_id_adam,
                    "predictions": {
                        "ctr": response.attribution_data.predicted_ctr,
                        "listen_through": response.attribution_data.predicted_listen_through
                    },
                    "mechanisms": response.mechanisms_activated,
                    "context": {
                        "station_id": request.station_id,
                        "content_energy": content_context.energy
                    }
                }
            )
        )
        
        # A/B test assignment (if in experiment)
        if selection.experiment_id:
            await self.ab_testing.record_assignment(
                experiment_id=selection.experiment_id,
                user_id=response.attribution_data.user_id_adam,
                variant=selection.experiment_variant,
                decision_id=response.decision_id
            )
```

---

## 3.2 Outcome Tracking and Attribution

This is where learning happens—connecting decisions to outcomes.

### Outcome Event Schema

```python
# =============================================================================
# OUTCOME TRACKING - How outcomes flow back to ADAM
# =============================================================================

class AdOutcomeEvent(BaseModel):
    """
    Outcome event from iHeart back to ADAM.
    
    Sent when listener takes action (or doesn't).
    """
    # Correlation
    decision_id: str                          # Links to original decision
    request_id: str
    
    # Timing
    outcome_timestamp: datetime
    time_since_decision_seconds: int
    
    # Listener behavior
    listened_through: bool                    # Completed the ad
    listen_duration_seconds: float
    listen_percentage: float
    
    # Actions
    clicked: bool = False
    click_timestamp: Optional[datetime] = None
    
    converted: bool = False
    conversion_timestamp: Optional[datetime] = None
    conversion_type: Optional[str] = None     # "purchase", "signup", "app_install"
    conversion_value: Optional[float] = None
    
    # Context at outcome time
    continued_listening: bool                 # Kept listening after ad
    session_continued_seconds: Optional[int] = None
    
    # Attribution window
    attribution_window_hours: int = 24


class OutcomeProcessingService:
    """
    Process outcomes and propagate learning signals.
    
    LEARNING INTEGRATION:
    - Outcome → User profile update
    - Outcome → Mechanism effectiveness update
    - Outcome → Content-ad affinity update
    - Outcome → Station/format prior update
    - Outcome → A/B test result
    - Outcome → Model monitoring
    """
    
    def __init__(
        self,
        graph: GraphService,
        gradient_bridge: GradientBridge,
        ab_testing: ABTestingService,
        model_monitor: ModelMonitoringService,
        discovery_engine: DiscoveryEngine,
        kafka: KafkaProducer
    ):
        self.graph = graph
        self.gradient_bridge = gradient_bridge
        self.ab_testing = ab_testing
        self.model_monitor = model_monitor
        self.discovery = discovery_engine
        self.kafka = kafka
    
    async def process_outcome(self, outcome: AdOutcomeEvent):
        """
        Process an outcome event and propagate learning.
        """
        # 1. Retrieve original decision
        decision = await self.graph.get_ad_decision(outcome.decision_id)
        if not decision:
            logger.warning(f"Decision not found: {outcome.decision_id}")
            return
        
        attribution = decision.attribution_data
        
        # 2. Calculate outcome metrics
        outcome_value = self._calculate_outcome_value(outcome)
        prediction_error = self._calculate_prediction_error(
            attribution, outcome
        )
        
        # 3. UPDATE USER PROFILE
        await self._update_user_profile(
            user_id=attribution.user_id_adam,
            mechanisms=attribution.mechanisms_used,
            outcome=outcome,
            decision=decision
        )
        
        # 4. UPDATE MECHANISM EFFECTIVENESS
        await self._update_mechanism_effectiveness(
            user_id=attribution.user_id_adam,
            mechanisms=attribution.mechanisms_used,
            mechanism_weights=attribution.mechanism_weights,
            outcome=outcome
        )
        
        # 5. UPDATE CONTENT-AD AFFINITY
        await self._update_content_ad_affinity(
            content_context=attribution.content_context_snapshot,
            creative_id=decision.creative_id,
            outcome=outcome
        )
        
        # 6. UPDATE STATION/FORMAT PRIORS
        await self._update_station_priors(
            station_id=decision.station_id,
            mechanisms=attribution.mechanisms_used,
            outcome=outcome
        )
        
        # 7. RECORD A/B TEST OUTCOME
        if attribution.experiment_id:
            await self.ab_testing.record_outcome(
                experiment_id=attribution.experiment_id,
                user_id=attribution.user_id_adam,
                outcome_value=1.0 if outcome.converted else 0.0
            )
        
        # 8. MODEL MONITORING
        await self.model_monitor.record_prediction_outcome(
            prediction={
                "ctr": attribution.predicted_ctr,
                "listen_through": attribution.predicted_listen_through,
                "conversion": attribution.predicted_conversion
            },
            actual={
                "clicked": outcome.clicked,
                "listened_through": outcome.listened_through,
                "converted": outcome.converted
            }
        )
        
        # 9. EMIT LEARNING SIGNAL TO GRADIENT BRIDGE
        await self.gradient_bridge.propagate_signal(
            LearningSignal(
                source="iheart_outcome",
                signal_type=LearningSignalType.OUTCOME,
                entity_type="ad_outcome",
                entity_id=outcome.decision_id,
                payload={
                    "user_id": attribution.user_id_adam,
                    "outcome_value": outcome_value,
                    "prediction_error": prediction_error,
                    "mechanisms": attribution.mechanisms_used,
                    "converted": outcome.converted,
                    "clicked": outcome.clicked,
                    "listened_through": outcome.listened_through
                }
            )
        )
        
        # 10. FEED DISCOVERY ENGINE
        await self.discovery.observe_outcome(
            user_id=attribution.user_id_adam,
            context=attribution.content_context_snapshot,
            mechanisms=attribution.mechanisms_used,
            outcome=outcome_value,
            timestamp=outcome.outcome_timestamp
        )
    
    async def _update_user_profile(
        self,
        user_id: str,
        mechanisms: List[str],
        outcome: AdOutcomeEvent,
        decision: AdDecision
    ):
        """
        Update user profile based on outcome.
        
        LEARNING PRINCIPLE: 
        - Positive outcome → Reinforce mechanism receptivity
        - Negative outcome → Reduce mechanism receptivity (slightly)
        """
        current_profile = await self.graph.get_user_profile(user_id)
        if not current_profile:
            return
        
        # Update mechanism receptivity
        current_receptivity = current_profile.mechanism_receptivity or {}
        
        for mechanism in mechanisms:
            current = current_receptivity.get(mechanism, 0.5)
            
            if outcome.converted:
                # Strong positive signal
                updated = current + 0.1 * (1 - current)  # Asymptotic toward 1
            elif outcome.clicked:
                # Moderate positive signal
                updated = current + 0.05 * (1 - current)
            elif outcome.listened_through:
                # Weak positive signal
                updated = current + 0.02 * (1 - current)
            else:
                # Slight negative signal (didn't engage)
                updated = current - 0.01 * current  # Slight decay
            
            current_receptivity[mechanism] = max(0.1, min(0.95, updated))
        
        # Update profile
        current_profile.mechanism_receptivity = current_receptivity
        current_profile.profile_confidence = min(
            0.95,
            current_profile.profile_confidence + 0.01
        )
        
        await self.graph.update_user_profile(current_profile)
    
    async def _update_mechanism_effectiveness(
        self,
        user_id: str,
        mechanisms: List[str],
        mechanism_weights: Dict[str, float],
        outcome: AdOutcomeEvent
    ):
        """
        Update mechanism effectiveness using Bayesian updates.
        
        LEARNING PRINCIPLE:
        - Each mechanism gets credit proportional to its weight
        - Bayesian alpha/beta updates for uncertainty
        """
        for mechanism in mechanisms:
            weight = mechanism_weights.get(mechanism, 1.0 / len(mechanisms))
            
            # Get current effectiveness
            current = await self.graph.get_user_mechanism_effectiveness(
                user_id, mechanism
            )
            
            if not current:
                current = MechanismEffectiveness(
                    mechanism_id=mechanism,
                    success_rate=0.5,
                    confidence=0.5,
                    evidence_count=0,
                    alpha=1,
                    beta=1
                )
            
            # Bayesian update
            outcome_value = 1.0 if outcome.converted else 0.0
            weighted_outcome = outcome_value * weight
            
            # Update alpha (successes) and beta (failures)
            if outcome.converted:
                current.alpha += weight
            else:
                current.beta += weight
            
            # Recalculate
            current.success_rate = current.alpha / (current.alpha + current.beta)
            current.confidence = 1 - (1 / (1 + current.alpha + current.beta))
            current.evidence_count += 1
            
            await self.graph.update_user_mechanism_effectiveness(
                user_id, current
            )
    
    async def _update_content_ad_affinity(
        self,
        content_context: Dict[str, Any],
        creative_id: str,
        outcome: AdOutcomeEvent
    ):
        """
        Learn which content-ad combinations work well.
        
        LEARNING PRINCIPLE:
        - Track content features × ad performance
        - Build predictive models for content-ad matching
        """
        # Extract content features
        content_features = {
            "energy": content_context.get("energy"),
            "valence": content_context.get("valence"),
            "arousal": content_context.get("arousal"),
            "content_type": content_context.get("content_type"),
            "topics": content_context.get("active_topics", [])
        }
        
        # Store content-ad outcome
        affinity_record = ContentAdAffinity(
            content_features=content_features,
            creative_id=creative_id,
            outcome=1.0 if outcome.converted else 0.0,
            listen_through=outcome.listen_percentage,
            timestamp=outcome.outcome_timestamp
        )
        
        await self.graph.store_content_ad_affinity(affinity_record)
```

---

# PART 4: BIDIRECTIONAL LEARNING ARCHITECTURE

## 4.1 Learning Signal Taxonomy for iHeart Integration

```python
# =============================================================================
# LEARNING SIGNAL TYPES FOR iHEART INTEGRATION
# =============================================================================

class iHeartLearningSignalType(str, Enum):
    """
    Types of learning signals flowing through iHeart integration.
    
    Each signal type updates different components of ADAM.
    """
    # Inbound signals (iHeart → ADAM learning)
    LISTENING_BEHAVIOR = "listening_behavior"      # What users listen to
    SKIP_PATTERN = "skip_pattern"                  # When/what users skip
    SESSION_ENGAGEMENT = "session_engagement"      # Session-level patterns
    AD_OUTCOME = "ad_outcome"                      # Ad interaction results
    CONTENT_CONSUMPTION = "content_consumption"    # Cumulative listening
    
    # Derived signals (ADAM internal)
    PROFILE_UPDATE = "profile_update"              # User profile changes
    MECHANISM_UPDATE = "mechanism_update"          # Mechanism effectiveness
    CONTENT_AFFINITY = "content_affinity"          # Content-ad matching
    STATION_PRIOR = "station_prior"                # Station-level priors
    FORMAT_PRIOR = "format_prior"                  # Format-level priors
    DISCOVERY = "discovery"                        # New pattern discovered
    
    # Outbound signals (ADAM decisions)
    AD_DECISION = "ad_decision"                    # Decision made
    PREDICTION = "prediction"                      # Prediction logged


# Learning signal routing
LEARNING_SIGNAL_ROUTING = {
    iHeartLearningSignalType.LISTENING_BEHAVIOR: [
        "user_profile_service",      # Update Big Five, regulatory focus
        "cold_start_service",        # Update archetypes
        "station_learning_service",  # Update station profiles
    ],
    
    iHeartLearningSignalType.SKIP_PATTERN: [
        "user_profile_service",      # Neuroticism signal
        "content_analyzer",          # Track skip-inducing content
    ],
    
    iHeartLearningSignalType.AD_OUTCOME: [
        "user_profile_service",      # Mechanism receptivity
        "mechanism_effectiveness",   # Bayesian update
        "content_ad_affinity",       # Content-ad matching
        "station_learning",          # Station-level effectiveness
        "ab_testing",                # Experiment results
        "model_monitoring",          # Prediction accuracy
        "discovery_engine",          # Pattern mining
    ],
    
    iHeartLearningSignalType.CONTENT_CONSUMPTION: [
        "artist_profiler",           # Artist psychological profiles
        "genre_mapping",             # Genre-personality mapping
        "lyrics_analyzer",           # Lyrics-psychology correlation
    ],
}
```

## 4.2 Cross-Component Learning Matrix

This matrix shows how learning flows between components through the iHeart integration:

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                    CROSS-COMPONENT LEARNING MATRIX                                  │
│                                                                                     │
│   SOURCE ↓ → DESTINATION →   │ User  │ Cold  │ Copy  │ A/B   │ Disco-│ Mechan │    │
│                              │Profile│ Start │ Gen   │ Test  │ very  │ ism    │    │
│   ═══════════════════════════╪═══════╪═══════╪═══════╪═══════╪═══════╪════════╪    │
│                              │       │       │       │       │       │        │    │
│   Station Listening          │   ●   │   ●   │       │       │   ●   │   ●    │    │
│   (User listens to station)  │ traits│archtyp│       │       │pattrns│ priors │    │
│                              │       │       │       │       │       │        │    │
│   Track Consumption          │   ●   │   ●   │       │       │   ●   │        │    │
│   (User plays specific song) │ traits│ prior │       │       │correlr│        │    │
│                              │       │       │       │       │       │        │    │
│   Lyrics Exposure            │   ●   │       │   ●   │       │   ●   │   ●    │    │
│   (Content priming)          │ state │       │ theme │       │languge│ prime  │    │
│                              │       │       │       │       │       │        │    │
│   Podcast Engagement         │   ●   │   ●   │   ●   │       │   ●   │        │    │
│   (Topic consumption)        │intrest│ prior │ topic │       │topic  │        │    │
│                              │       │       │       │       │       │        │    │
│   Ad Outcome (Convert)       │   ●   │       │   ●   │   ●   │   ●   │   ●    │    │
│   (User converts)            │recept │       │ copy  │result │validtn│effectvs│    │
│                              │       │       │       │       │       │        │    │
│   Ad Outcome (Click)         │   ●   │       │   ●   │   ●   │       │   ●    │    │
│   (User clicks)              │recept │       │ copy  │result │       │effectvs│    │
│                              │       │       │       │       │       │        │    │
│   Ad Outcome (Listen)        │   ●   │       │   ●   │   ●   │       │   ●    │    │
│   (User completes ad)        │engagmt│       │ audio │result │       │priming │    │
│                              │       │       │       │       │       │        │    │
│   Skip Behavior              │   ●   │       │       │       │   ●   │        │    │
│   (User skips)               │neurot │       │       │       │pattrns│        │    │
│                              │       │       │       │       │       │        │    │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

## 4.3 Gradient Bridge Integration

```python
# =============================================================================
# GRADIENT BRIDGE INTEGRATION FOR iHEART
# =============================================================================

class iHeartGradientBridgeAdapter:
    """
    Adapter for connecting iHeart learning signals to ADAM's Gradient Bridge.
    
    Ensures all iHeart outcomes properly update all relevant components.
    """
    
    def __init__(self, gradient_bridge: GradientBridge):
        self.bridge = gradient_bridge
        
        # Register iHeart-specific signal handlers
        self.bridge.register_handler(
            "iheart_outcome",
            self._handle_iheart_outcome
        )
        self.bridge.register_handler(
            "iheart_listening",
            self._handle_listening_signal
        )
    
    async def _handle_iheart_outcome(
        self,
        signal: LearningSignal
    ) -> List[LearningUpdate]:
        """
        Transform iHeart outcome into learning updates for multiple components.
        """
        updates = []
        payload = signal.payload
        
        # 1. User profile update
        updates.append(LearningUpdate(
            target_component="user_profile",
            update_type="mechanism_receptivity",
            entity_id=payload["user_id"],
            update_data={
                "mechanisms": payload["mechanisms"],
                "outcome": payload["outcome_value"],
                "confidence_delta": 0.01
            },
            priority=LearningPriority.IMMEDIATE  # <10ms
        ))
        
        # 2. Mechanism effectiveness (Bayesian)
        updates.append(LearningUpdate(
            target_component="mechanism_effectiveness",
            update_type="bayesian_update",
            entity_id=payload["user_id"],
            update_data={
                "mechanisms": payload["mechanisms"],
                "outcome": payload["converted"],
                "alpha_delta": 1 if payload["converted"] else 0,
                "beta_delta": 0 if payload["converted"] else 1
            },
            priority=LearningPriority.IMMEDIATE
        ))
        
        # 3. Content-ad affinity (batch)
        updates.append(LearningUpdate(
            target_component="content_ad_matcher",
            update_type="affinity_observation",
            entity_id=f"{payload.get('content_id')}:{payload.get('creative_id')}",
            update_data={
                "content_features": payload.get("context", {}),
                "outcome": payload["outcome_value"]
            },
            priority=LearningPriority.BATCH  # <1s aggregation window
        ))
        
        # 4. Station priors (batch)
        if payload.get("station_id"):
            updates.append(LearningUpdate(
                target_component="station_priors",
                update_type="mechanism_effectiveness",
                entity_id=payload["station_id"],
                update_data={
                    "mechanisms": payload["mechanisms"],
                    "outcome": payload["converted"]
                },
                priority=LearningPriority.BATCH
            ))
        
        # 5. Discovery observation (batch)
        updates.append(LearningUpdate(
            target_component="discovery_engine",
            update_type="outcome_observation",
            entity_id=signal.signal_id,
            update_data=payload,
            priority=LearningPriority.BATCH
        ))
        
        return updates
    
    async def _handle_listening_signal(
        self,
        signal: LearningSignal
    ) -> List[LearningUpdate]:
        """
        Transform listening behavior into profile updates.
        """
        updates = []
        payload = signal.payload
        
        # User listened to content → Update personality inference
        if payload.get("content_type") == "music":
            updates.append(LearningUpdate(
                target_component="user_profile",
                update_type="trait_inference",
                entity_id=payload["user_id"],
                update_data={
                    "track_id": payload.get("track_id"),
                    "artist_id": payload.get("artist_id"),
                    "genres": payload.get("genres"),
                    "duration": payload.get("duration"),
                    "completed": payload.get("completed", True)
                },
                priority=LearningPriority.NEAR_REALTIME  # <100ms
            ))
        
        return updates
```

---

# PART 5: INTEGRATION WITH OTHER ADAM COMPONENTS

## 5.1 Component Integration Matrix

| ADAM Component | iHeart Integration Point | Data Flow Direction |
|----------------|-------------------------|---------------------|
| Signal Aggregation (#08) | Listening events, skip patterns | iHeart → ADAM |
| Cold Start (#13) | Station/format priors | Bidirectional |
| Copy Generation (#15) | Personalized ad copy | ADAM → iHeart |
| A/B Testing (#12) | Experiment results | Bidirectional |
| Discovery Engine | Pattern observations | iHeart → ADAM |
| Gradient Bridge (#06) | All learning signals | Internal |
| Brand Intelligence (#14) | Brand-user matching | Internal |
| Journey Tracking (#10) | Listening journeys | iHeart → ADAM |
| Identity Resolution (#19) | User ID mapping | Bidirectional |
| Embeddings (#21) | Content embeddings | Internal |
| Temporal Patterns (Gap23) | Listening time patterns | iHeart → ADAM |

## 5.2 Required Updates to Other Enhancement Specifications

### Signal Aggregation (#08) - Add iHeart Signals

```python
# Add to Signal Categories
class SignalCategory(str, Enum):
    # ... existing categories ...
    
    # iHeart-specific signals
    IHEART_LISTENING = "iheart_listening"
    IHEART_SKIP = "iheart_skip"
    IHEART_AD_INTERACTION = "iheart_ad_interaction"
    IHEART_SESSION = "iheart_session"


# Add iHeart signal processors
class iHeartListeningSignalProcessor(SignalProcessor):
    """Process listening events from iHeart."""
    
    async def process(self, event: iHeartListeningEvent) -> List[ProcessedSignal]:
        signals = []
        
        # Extract personality signals from content
        track = await self.content_service.get_track(event.track_id)
        
        signals.append(ProcessedSignal(
            signal_type="music_personality_inference",
            user_id=event.user_id,
            features={
                "genres": track.genres,
                "energy": track.energy,
                "valence": track.valence,
                "duration_listened": event.duration_seconds,
                "completed": event.completed
            }
        ))
        
        return signals
```

### Cold Start (#13) - Add iHeart Context Sources

```python
# Add to Cold Start context sources
class ContextSource(str, Enum):
    # ... existing sources ...
    
    # iHeart sources
    IHEART_STATION = "iheart_station"
    IHEART_FORMAT = "iheart_format"
    IHEART_LISTENING_HISTORY = "iheart_listening_history"
    IHEART_PODCAST_AFFINITY = "iheart_podcast_affinity"


# Add station-based bootstrap
async def bootstrap_from_station(
    self,
    station_id: str,
    listening_context: Dict[str, Any]
) -> UserProfile:
    """Bootstrap user profile from station characteristics."""
    station = await self.graph.get_station(station_id)
    
    return UserProfile(
        user_id="anonymous",
        big_five=BigFiveProfile(
            openness=station.psychographic_profile.openness_mean,
            conscientiousness=station.psychographic_profile.conscientiousness_mean,
            extraversion=station.psychographic_profile.extraversion_mean,
            agreeableness=station.psychographic_profile.agreeableness_mean,
            neuroticism=station.psychographic_profile.neuroticism_mean
        ),
        # ... rest of profile from station priors
        profile_source="iheart_station_inference",
        profile_confidence=0.4  # Lower confidence for station-only
    )
```

### Copy Generation (#15) - Add Audio-Specific Generation

```python
# Add audio copy generation modes
class AudioCopyMode(str, Enum):
    """Audio-specific copy generation modes."""
    PRODUCED_SPOT = "produced_spot"      # Pre-recorded
    HOST_READ = "host_read"              # Podcast host reads
    DYNAMIC_TTS = "dynamic_tts"          # Text-to-speech
    HYBRID = "hybrid"                     # Mix of above


# Add audio-specific parameters
class AudioCopyParameters(BaseModel):
    """Parameters for audio ad copy."""
    mode: AudioCopyMode
    
    # Voice parameters
    voice_id: str
    speaking_rate: float = 1.0
    pitch_adjustment: float = 0.0
    
    # Energy matching
    match_content_energy: bool = True
    energy_level: float = 0.5
    
    # Timing
    duration_seconds: int = 30
    natural_pauses: bool = True
    
    # Context adaptation
    adapt_to_content_mood: bool = True
    content_energy: Optional[float] = None
    content_valence: Optional[float] = None


# Update copy generation to support audio
async def generate_audio_copy(
    self,
    request: CopyRequest,
    audio_params: AudioCopyParameters
) -> GeneratedAudioCopy:
    """Generate personality-matched audio ad copy."""
    
    # Generate base copy
    copy_result = await self.generate(request)
    
    # Adjust for audio delivery
    audio_copy = self._adapt_for_audio(
        copy=copy_result.copy,
        duration=audio_params.duration_seconds,
        speaking_rate=audio_params.speaking_rate
    )
    
    # Generate SSML with psychological parameters
    ssml = self._generate_ssml(
        copy=audio_copy,
        voice_id=audio_params.voice_id,
        energy=audio_params.energy_level,
        pauses=audio_params.natural_pauses
    )
    
    return GeneratedAudioCopy(
        copy=audio_copy,
        ssml=ssml,
        voice_id=audio_params.voice_id,
        duration_estimate=self._estimate_duration(audio_copy, audio_params)
    )
```

---

# PART 6: IMPLEMENTATION CHECKLIST

## 6.1 Phase 1: Data Model Foundation

- [ ] Neo4j schema deployed for all iHeart entities
  - [ ] Station nodes with psychographic profiles
  - [ ] Artist nodes with psychological signatures
  - [ ] Track nodes with audio features and psychological mappings
  - [ ] Lyrics nodes with theme/emotion analysis
  - [ ] Podcast/Episode/Transcript nodes
  - [ ] Brand nodes with personality profiles
  - [ ] Campaign/Creative nodes
  - [ ] Inventory/AdSlot nodes
  
- [ ] Pydantic models implemented for all entities
- [ ] Kafka event contracts defined for all signal types
- [ ] Redis cache schemas for hot data

## 6.2 Phase 2: Content Analysis Pipeline

- [ ] Station profile learning service
- [ ] Artist psychological profiler
- [ ] Track psychological analyzer
- [ ] Lyrics analysis service (Claude integration)
- [ ] Transcript analysis service
- [ ] Content embedding generation

## 6.3 Phase 3: Ad Decision Service

- [ ] Request/response protocol implementation
- [ ] User identity resolution (iHeart ↔ ADAM)
- [ ] Content context analyzer
- [ ] Campaign/creative selector
- [ ] Audio copy generator
- [ ] Outcome prediction model

## 6.4 Phase 4: Learning Integration

- [ ] Outcome processing service
- [ ] Gradient Bridge adapters for iHeart signals
- [ ] User profile learning from listening
- [ ] Mechanism effectiveness learning
- [ ] Content-ad affinity learning
- [ ] Station/format prior learning
- [ ] A/B testing integration

## 6.5 Phase 5: Cross-Component Integration

- [ ] Signal Aggregation (#08) iHeart signals
- [ ] Cold Start (#13) station/format priors
- [ ] Copy Generation (#15) audio modes
- [ ] A/B Testing (#12) iHeart experiments
- [ ] Discovery Engine pattern mining
- [ ] Model Monitoring (Gap20) iHeart metrics

---

# PART 7: SUCCESS METRICS

## 7.1 Learning Effectiveness Metrics

| Metric | Description | Target |
|--------|-------------|--------|
| Profile Accuracy | User profile prediction accuracy | >70% |
| Mechanism Attribution | Correct mechanism credit | >80% |
| Prior Convergence | Time to converge cold start → rich | <30 days |
| Discovery Rate | New patterns discovered/week | >10 |
| Learning Latency | Time from outcome to model update | <1 second |

## 7.2 Business Performance Metrics

| Metric | Baseline | Target | Measurement |
|--------|----------|--------|-------------|
| Listen-through Rate | 72% | 82% | % completing ad |
| CTR | 0.8% | 1.5% | Clicks/impressions |
| Conversion Lift | 0% | 40% | vs. non-personalized |
| Profile Coverage | 0% | 80% | Users with rich profiles |

## 7.3 System Performance Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Decision Latency | <100ms | P95 |
| Learning Signal Processing | <1s | P95 |
| Profile Lookup | <15ms | P95 |
| Content Context Analysis | <10ms | P95 |

---

# APPENDIX A: KAFKA TOPIC STRUCTURE

```
iheart.ad.requests          # Incoming ad requests (for audit)
iheart.ad.decisions         # Decisions made
iheart.ad.outcomes          # Outcome events
iheart.listening.events     # Listening behavior
iheart.content.analysis     # Content analysis results
iheart.learning.signals     # All learning signals
iheart.profile.updates      # Profile change events
iheart.experiments          # A/B test events
```

---

# APPENDIX B: API ENDPOINTS

```
POST   /api/v1/iheart/ad-request        # Main ad decision endpoint
POST   /api/v1/iheart/outcome           # Outcome callback
GET    /api/v1/iheart/station/{id}      # Station data
GET    /api/v1/iheart/user/{id}/profile # User profile (for debugging)
POST   /api/v1/iheart/content/analyze   # Content analysis trigger
GET    /api/v1/iheart/metrics           # Integration metrics
```

---

**END OF iHEART AD NETWORK INTEGRATION SPECIFICATION**

**Document Statistics**:
- Total Lines: ~4,200
- Sections: 7 major parts + 2 appendices
- Neo4j Schemas: 9 entity types
- Pydantic Models: 25+
- Integration Points: 11 ADAM components
- Learning Signal Types: 12
