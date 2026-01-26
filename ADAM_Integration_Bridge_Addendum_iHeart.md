# ADAM Integration Bridge Addendum: iHeart Cross-Component Requirements
## Explicit Changes Required to All ADAM Components for iHeart Integration

**Document Purpose**: This addendum to the Integration Bridge explicitly specifies every change required to existing ADAM enhancement specifications to fully support the iHeart Ad Network Integration. Use this as a checklist during implementation to ensure nothing is missed.

**Version**: 1.0  
**Date**: January 2026  
**Related Document**: ADAM_iHeart_Ad_Network_Integration_COMPLETE.md

---

# CRITICAL IMPLEMENTATION NOTE

The iHeart integration is not a standalone component—it touches nearly every ADAM subsystem. This document provides the explicit modifications required to each enhancement specification to enable full bidirectional learning with iHeart.

**Implementation Order**: Complete iHeart data model FIRST, then apply these modifications to each component in dependency order.

---

# COMPONENT MODIFICATION MATRIX

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                    MODIFICATION REQUIREMENTS BY COMPONENT                       │
│                                                                                 │
│  Component                    │ Modification Scope │ Priority │ Complexity    │
│  ═════════════════════════════╪════════════════════╪══════════╪═══════════════│
│  Signal Aggregation (#08)     │ Add signal types   │ P0       │ Medium        │
│  Cold Start (#13)             │ Add context sources│ P0       │ Medium        │
│  Copy Generation (#15)        │ Add audio modes    │ P0       │ High          │
│  Gradient Bridge (#06)        │ Add signal handlers│ P0       │ Medium        │
│  Neo4j Schema                 │ Add entity types   │ P0       │ High          │
│  Kafka Events                 │ Add event types    │ P0       │ Medium        │
│  A/B Testing (#12)            │ Add iHeart events  │ P1       │ Low           │
│  Identity Resolution (#19)    │ Add iHeart IDs     │ P1       │ Medium        │
│  Brand Intelligence (#14)     │ Add audio matching │ P1       │ Medium        │
│  Journey Tracking (#10)       │ Add listening paths│ P1       │ Medium        │
│  Discovery Engine             │ Add content signals│ P1       │ Low           │
│  Embeddings (#21)             │ Add audio/lyrics   │ P1       │ Medium        │
│  Temporal Patterns (Gap23)    │ Add listening time │ P2       │ Low           │
│  Model Monitoring (Gap20)     │ Add iHeart metrics │ P2       │ Low           │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

# PART 1: SIGNAL AGGREGATION (#08) MODIFICATIONS

## 1.1 New Signal Categories

**Add to `SignalCategory` enum:**

```python
class SignalCategory(str, Enum):
    # ... existing categories ...
    
    # iHeart Audio Platform Signals
    AUDIO_LISTENING = "audio_listening"           # Track/podcast consumption
    AUDIO_SKIP = "audio_skip"                     # Skip behavior
    AUDIO_COMPLETION = "audio_completion"         # Content completion
    AD_LISTEN_THROUGH = "ad_listen_through"       # Ad completion
    AD_INTERACTION = "ad_interaction"             # Click/conversion
    SESSION_BEHAVIOR = "session_behavior"         # Session-level patterns
    CONTENT_CONTEXT = "content_context"           # What's playing
```

## 1.2 New Signal Processors

**Add to Signal Processors:**

```python
# Add to /processors/iheart_processors.py

class iHeartListeningProcessor(SignalProcessor):
    """
    Process listening events from iHeart.
    
    Transforms raw listening data into psychological signals.
    """
    category = SignalCategory.AUDIO_LISTENING
    
    async def process(self, raw_signal: RawSignal) -> List[ProcessedSignal]:
        event = raw_signal.raw_value
        
        signals = []
        
        # 1. Music preference signal (for personality inference)
        if event.get("content_type") == "music":
            signals.append(ProcessedSignal(
                signal_id=f"{raw_signal.signal_id}_music_pref",
                user_id=raw_signal.user_id,
                signal_type="music_preference",
                category=SignalCategory.AUDIO_LISTENING,
                features={
                    "track_id": event.get("track_id"),
                    "artist_id": event.get("artist_id"),
                    "genres": event.get("genres", []),
                    "energy": event.get("energy"),
                    "valence": event.get("valence"),
                    "duration_seconds": event.get("duration_seconds"),
                    "completed": event.get("completed", True)
                },
                timestamp=raw_signal.timestamp,
                confidence=0.8 if event.get("completed") else 0.5
            ))
        
        # 2. Podcast preference signal
        elif event.get("content_type") == "podcast":
            signals.append(ProcessedSignal(
                signal_id=f"{raw_signal.signal_id}_podcast_pref",
                user_id=raw_signal.user_id,
                signal_type="podcast_preference",
                category=SignalCategory.AUDIO_LISTENING,
                features={
                    "podcast_id": event.get("podcast_id"),
                    "episode_id": event.get("episode_id"),
                    "category": event.get("category"),
                    "topics": event.get("topics", []),
                    "duration_seconds": event.get("duration_seconds"),
                    "completion_percentage": event.get("completion_percentage")
                },
                timestamp=raw_signal.timestamp,
                confidence=0.8
            ))
        
        # 3. Station preference signal
        if event.get("station_id"):
            signals.append(ProcessedSignal(
                signal_id=f"{raw_signal.signal_id}_station_pref",
                user_id=raw_signal.user_id,
                signal_type="station_preference",
                category=SignalCategory.AUDIO_LISTENING,
                features={
                    "station_id": event.get("station_id"),
                    "format": event.get("format"),
                    "listening_duration": event.get("duration_seconds")
                },
                timestamp=raw_signal.timestamp,
                confidence=0.7
            ))
        
        return signals


class iHeartSkipProcessor(SignalProcessor):
    """
    Process skip events for psychological inference.
    
    Skip patterns correlate with:
    - Neuroticism (high skip rate)
    - Impatience/arousal state
    - Content mismatch
    """
    category = SignalCategory.AUDIO_SKIP
    
    async def process(self, raw_signal: RawSignal) -> List[ProcessedSignal]:
        event = raw_signal.raw_value
        
        return [ProcessedSignal(
            signal_id=f"{raw_signal.signal_id}_skip",
            user_id=raw_signal.user_id,
            signal_type="skip_behavior",
            category=SignalCategory.AUDIO_SKIP,
            features={
                "content_id": event.get("content_id"),
                "content_type": event.get("content_type"),
                "skip_position_seconds": event.get("skip_position"),
                "skip_position_percentage": event.get("skip_percentage"),
                "consecutive_skips": event.get("consecutive_skips", 1),
                "session_skip_count": event.get("session_skip_count"),
                "content_energy": event.get("content_energy"),
                "content_valence": event.get("content_valence")
            },
            timestamp=raw_signal.timestamp,
            confidence=0.9  # High confidence in behavioral signal
        )]


class iHeartAdInteractionProcessor(SignalProcessor):
    """
    Process ad interaction events for learning.
    """
    category = SignalCategory.AD_INTERACTION
    
    async def process(self, raw_signal: RawSignal) -> List[ProcessedSignal]:
        event = raw_signal.raw_value
        
        return [ProcessedSignal(
            signal_id=f"{raw_signal.signal_id}_ad",
            user_id=raw_signal.user_id,
            signal_type="ad_interaction",
            category=SignalCategory.AD_INTERACTION,
            features={
                "decision_id": event.get("decision_id"),
                "creative_id": event.get("creative_id"),
                "campaign_id": event.get("campaign_id"),
                "listened_through": event.get("listened_through"),
                "listen_percentage": event.get("listen_percentage"),
                "clicked": event.get("clicked", False),
                "converted": event.get("converted", False),
                "mechanisms_used": event.get("mechanisms_used", [])
            },
            timestamp=raw_signal.timestamp,
            confidence=1.0  # Definitive behavioral outcome
        )]
```

## 1.3 Flink Pipeline Additions

**Add to Flink job configuration:**

```python
# Add iHeart sources to Flink pipeline
IHEART_KAFKA_SOURCES = {
    "iheart.listening.events": {
        "processor": iHeartListeningProcessor,
        "parallelism": 8,
        "watermark_interval_ms": 1000
    },
    "iheart.skip.events": {
        "processor": iHeartSkipProcessor,
        "parallelism": 4,
        "watermark_interval_ms": 500
    },
    "iheart.ad.outcomes": {
        "processor": iHeartAdInteractionProcessor,
        "parallelism": 4,
        "watermark_interval_ms": 1000
    }
}
```

---

# PART 2: COLD START (#13) MODIFICATIONS

## 2.1 New Context Sources

**Add to `ContextSource` enum:**

```python
class ContextSource(str, Enum):
    # ... existing sources ...
    
    # iHeart Context Sources
    IHEART_STATION = "iheart_station"
    IHEART_FORMAT = "iheart_format"
    IHEART_LISTENING_HISTORY = "iheart_listening_history"
    IHEART_PODCAST_CATEGORY = "iheart_podcast_category"
    IHEART_ARTIST_AFFINITY = "iheart_artist_affinity"
```

## 2.2 Station-Based Bootstrap

**Add to ColdStartService:**

```python
async def bootstrap_from_iheart_context(
    self,
    user_id: Optional[str],
    iheart_context: Dict[str, Any]
) -> Tuple[UserProfile, Dict[str, MechanismEffectiveness]]:
    """
    Bootstrap profile from iHeart listening context.
    
    Uses hierarchical priors:
    1. Station format → Base psychological profile
    2. Recent listening → Refinement
    3. Time of day → State adjustment
    """
    
    # Get station-level priors
    station_id = iheart_context.get("station_id")
    if station_id:
        station = await self.graph.get_station(station_id)
        
        # Use station psychographic profile as prior
        base_profile = UserProfile(
            user_id=user_id or "anonymous",
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
            construal_level=(
                ConstrualLevel.ABSTRACT 
                if station.psychographic_profile.abstract_tendency > 0.5 
                else ConstrualLevel.CONCRETE
            ),
            data_tier=UserDataTier.ANONYMOUS if not user_id else UserDataTier.IDENTIFIED,
            profile_confidence=0.4,  # Lower for station-only
            profile_source="iheart_station"
        )
        
        # Get mechanism priors from station
        mechanism_priors = await self.graph.get_station_mechanism_effectiveness(station_id)
        
        return base_profile, mechanism_priors
    
    # Fall back to format-level priors
    format_code = iheart_context.get("format")
    if format_code:
        format_prior = await self.get_format_prior(format_code)
        return self._build_profile_from_format(format_prior)
    
    # Ultimate fallback: population priors
    return await self._contextual_inference(iheart_context)


async def update_format_priors_from_iheart(
    self,
    format_code: str,
    station_profiles: List[StationPsychographicProfile]
) -> Dict[str, Any]:
    """
    Update format-level priors from aggregated station data.
    
    Called periodically to refresh format archetypes.
    """
    if not station_profiles:
        return None
    
    # Aggregate profiles
    aggregated = {
        "openness": np.mean([p.openness_mean for p in station_profiles]),
        "conscientiousness": np.mean([p.conscientiousness_mean for p in station_profiles]),
        "extraversion": np.mean([p.extraversion_mean for p in station_profiles]),
        "agreeableness": np.mean([p.agreeableness_mean for p in station_profiles]),
        "neuroticism": np.mean([p.neuroticism_mean for p in station_profiles]),
        "promotion_focus": np.mean([p.promotion_focus_tendency for p in station_profiles]),
        "prevention_focus": np.mean([p.prevention_focus_tendency for p in station_profiles]),
    }
    
    # Store as format prior
    format_prior = FormatPrior(
        format_code=format_code,
        psychological_profile=aggregated,
        sample_size=len(station_profiles),
        updated_at=datetime.utcnow()
    )
    
    await self.cache.set_format_prior(format_code, format_prior)
    
    return format_prior.dict()
```

## 2.3 Archetype Updates

**Add iHeart-derived archetypes to archetype initialization:**

```python
# Add to archetype definitions
IHEART_DERIVED_ARCHETYPES = {
    "chr_listener": {
        "name": "Contemporary Hit Radio Listener",
        "description": "Pop music enthusiast, socially engaged, trend-following",
        "source": "iheart_format:CHR",
        "big_five_centroid": BigFiveProfile(
            openness=0.55, conscientiousness=0.48, extraversion=0.68,
            agreeableness=0.55, neuroticism=0.52
        ),
        "regulatory_focus_tendency": "promotion",
        "mechanism_priors": {
            "mimetic_desire": MechanismEffectiveness(mechanism_id="mimetic_desire", success_rate=0.72),
            "social_proof": MechanismEffectiveness(mechanism_id="social_proof", success_rate=0.68),
            "identity_expression": MechanismEffectiveness(mechanism_id="identity_expression", success_rate=0.65)
        }
    },
    "country_listener": {
        "name": "Country Music Listener",
        "description": "Values tradition, authenticity, community",
        "source": "iheart_format:COUNTRY",
        "big_five_centroid": BigFiveProfile(
            openness=0.42, conscientiousness=0.62, extraversion=0.55,
            agreeableness=0.65, neuroticism=0.45
        ),
        "regulatory_focus_tendency": "prevention",
        "mechanism_priors": {
            "authenticity": MechanismEffectiveness(mechanism_id="authenticity", success_rate=0.75),
            "tradition": MechanismEffectiveness(mechanism_id="tradition", success_rate=0.70),
            "community_belonging": MechanismEffectiveness(mechanism_id="community_belonging", success_rate=0.68)
        }
    },
    # ... additional archetypes for each format
}
```

---

# PART 3: COPY GENERATION (#15) MODIFICATIONS

## 3.1 Audio Copy Mode

**Add AudioCopyMode enum and parameters:**

```python
class AudioCopyMode(str, Enum):
    """Audio delivery modes for copy generation."""
    PRODUCED_SPOT = "produced_spot"      # Pre-recorded
    HOST_READ = "host_read"              # Podcast host reads live
    DYNAMIC_TTS = "dynamic_tts"          # Text-to-speech render
    HYBRID = "hybrid"                     # Mix of pre-recorded + dynamic


class AudioCopyRequest(CopyRequest):
    """Extended copy request for audio delivery."""
    # ... inherit from CopyRequest ...
    
    # Audio-specific fields
    audio_mode: AudioCopyMode = AudioCopyMode.DYNAMIC_TTS
    duration_seconds: int = 30
    voice_id: Optional[str] = None
    
    # Content context (for energy matching)
    preceding_content_energy: Optional[float] = None
    preceding_content_valence: Optional[float] = None
    
    # Environment
    is_podcast: bool = False
    podcast_category: Optional[str] = None
    host_name: Optional[str] = None  # For host-read
    
    # Timing
    position_in_break: int = 1
    break_total_slots: int = 4


class AudioParameters(BaseModel):
    """Generated audio parameters for TTS rendering."""
    voice_id: str
    speaking_rate: float = 1.0        # 0.8-1.2
    pitch_adjustment: float = 0.0     # Semitones
    energy_level: float = 0.5
    warmth: float = 0.5
    
    # Prosody markers
    emphasis_words: List[str] = Field(default_factory=list)
    pause_positions: List[int] = Field(default_factory=list)  # Word indices
    
    # SSML output
    ssml: str


class GeneratedAudioCopy(GeneratedCopy):
    """Generated copy with audio-specific parameters."""
    # ... inherit from GeneratedCopy ...
    
    # Audio specifics
    audio_params: AudioParameters
    estimated_duration_seconds: float
    
    # For host-read
    host_read_instructions: Optional[str] = None
```

## 3.2 Audio Copy Generation Logic

**Add to CopyGenerationService:**

```python
async def generate_audio_copy(
    self,
    request: AudioCopyRequest
) -> GeneratedAudioCopy:
    """
    Generate personality-matched audio ad copy.
    
    Considers:
    - Personality-based messaging (inherited)
    - Content energy matching
    - Audio pacing for personality
    - SSML generation
    """
    # 1. Generate base copy (personality-matched)
    base_copy = await self.generate(request)
    
    # 2. Adapt copy length for audio duration
    adapted_copy = self._adapt_for_duration(
        copy=base_copy.copy,
        target_duration=request.duration_seconds,
        speaking_rate=self._get_personality_speaking_rate(request.user_profile)
    )
    
    # 3. Calculate audio parameters
    audio_params = self._calculate_audio_params(
        user_profile=request.user_profile,
        content_energy=request.preceding_content_energy,
        content_valence=request.preceding_content_valence,
        mechanisms=base_copy.mechanisms_addressed
    )
    
    # 4. Select voice
    voice_id = request.voice_id or self._select_voice(
        user_profile=request.user_profile,
        brand=request.brand_id
    )
    audio_params.voice_id = voice_id
    
    # 5. Generate SSML
    ssml = self._generate_ssml(
        copy=adapted_copy,
        params=audio_params,
        user_profile=request.user_profile
    )
    audio_params.ssml = ssml
    
    # 6. Generate host-read instructions if needed
    host_instructions = None
    if request.audio_mode == AudioCopyMode.HOST_READ:
        host_instructions = self._generate_host_instructions(
            copy=adapted_copy,
            host_name=request.host_name,
            podcast_category=request.podcast_category,
            user_profile=request.user_profile
        )
    
    return GeneratedAudioCopy(
        **base_copy.dict(),
        copy=adapted_copy,
        audio_params=audio_params,
        estimated_duration_seconds=self._estimate_duration(
            adapted_copy, audio_params.speaking_rate
        ),
        host_read_instructions=host_instructions
    )


def _calculate_audio_params(
    self,
    user_profile: UserProfile,
    content_energy: Optional[float],
    content_valence: Optional[float],
    mechanisms: List[str]
) -> AudioParameters:
    """
    Calculate audio delivery parameters based on psychology.
    """
    params = AudioParameters(voice_id="")  # Will be set later
    
    # Base on personality
    big_five = user_profile.big_five
    
    # Speaking rate
    # High conscientiousness → slower, more deliberate
    # High extraversion → faster, more energetic
    base_rate = 1.0
    if big_five.conscientiousness > 0.7:
        base_rate -= 0.1
    if big_five.extraversion > 0.7:
        base_rate += 0.1
    if big_five.neuroticism > 0.7:
        base_rate -= 0.05  # Slower for anxious users
    
    # Match content energy (±20% adjustment)
    if content_energy is not None:
        energy_adjustment = (content_energy - 0.5) * 0.2
        base_rate += energy_adjustment
    
    params.speaking_rate = max(0.8, min(1.2, base_rate))
    
    # Energy level
    if content_energy is not None:
        # Match content energy with personality adjustment
        params.energy_level = content_energy * 0.7 + big_five.extraversion * 0.3
    else:
        params.energy_level = big_five.extraversion * 0.5 + 0.25
    
    # Warmth
    params.warmth = big_five.agreeableness * 0.6 + 0.2
    if big_five.neuroticism > 0.6:
        params.warmth += 0.1  # More warmth for anxious users
    
    return params


def _generate_ssml(
    self,
    copy: str,
    params: AudioParameters,
    user_profile: UserProfile
) -> str:
    """
    Generate SSML with psychological optimization.
    """
    # Convert speaking rate to SSML rate
    rate_percent = int(params.speaking_rate * 100)
    
    # Build SSML
    ssml = f'<speak>'
    ssml += f'<prosody rate="{rate_percent}%">'
    
    # Split into sentences for natural pauses
    sentences = copy.split('. ')
    
    for i, sentence in enumerate(sentences):
        # Add emphasis to key words based on mechanisms
        emphasized_sentence = self._add_emphasis(sentence, params.emphasis_words)
        ssml += emphasized_sentence
        
        # Add pause between sentences
        if i < len(sentences) - 1:
            pause_ms = 300 if user_profile.big_five.conscientiousness > 0.6 else 200
            ssml += f'<break time="{pause_ms}ms"/>. '
    
    ssml += '</prosody>'
    ssml += '</speak>'
    
    return ssml
```

---

# PART 4: GRADIENT BRIDGE (#06) MODIFICATIONS

## 4.1 iHeart Signal Handlers

**Add to GradientBridge signal handlers:**

```python
# Register iHeart-specific handlers
class GradientBridge:
    def __init__(self, ...):
        # ... existing init ...
        
        # Register iHeart handlers
        self.register_handler("iheart_listening", self._handle_listening_signal)
        self.register_handler("iheart_outcome", self._handle_outcome_signal)
        self.register_handler("iheart_content_analysis", self._handle_content_signal)
    
    async def _handle_listening_signal(
        self,
        signal: LearningSignal
    ) -> List[LearningUpdate]:
        """
        Transform listening behavior into profile updates.
        
        Listening → Personality inference → Profile update
        """
        updates = []
        payload = signal.payload
        
        # Music listening → Big Five inference
        if payload.get("content_type") == "music":
            # Extract genre → personality mappings
            genres = payload.get("genres", [])
            
            trait_signals = self._genres_to_traits(genres)
            
            updates.append(LearningUpdate(
                target_component="user_profile",
                update_type="trait_inference",
                entity_id=payload["user_id"],
                update_data={
                    "trait_signals": trait_signals,
                    "signal_source": "music_listening",
                    "confidence": 0.6,
                    "decay_weight": 0.95  # Recent listening weighted more
                },
                priority=LearningPriority.NEAR_REALTIME
            ))
        
        # Podcast listening → Interest/construct inference
        elif payload.get("content_type") == "podcast":
            updates.append(LearningUpdate(
                target_component="user_profile",
                update_type="interest_inference",
                entity_id=payload["user_id"],
                update_data={
                    "topics": payload.get("topics", []),
                    "category": payload.get("category"),
                    "completion_rate": payload.get("completion_percentage", 1.0),
                    "signal_source": "podcast_listening"
                },
                priority=LearningPriority.NEAR_REALTIME
            ))
        
        # Station listening → Format preference
        if payload.get("station_id"):
            updates.append(LearningUpdate(
                target_component="cold_start",
                update_type="format_affinity",
                entity_id=payload["user_id"],
                update_data={
                    "station_id": payload["station_id"],
                    "format": payload.get("format"),
                    "duration": payload.get("duration_seconds")
                },
                priority=LearningPriority.BATCH
            ))
        
        return updates
    
    async def _handle_outcome_signal(
        self,
        signal: LearningSignal
    ) -> List[LearningUpdate]:
        """
        Process ad outcome and route to all learning consumers.
        """
        updates = []
        payload = signal.payload
        
        # 1. User mechanism effectiveness (immediate)
        updates.append(LearningUpdate(
            target_component="mechanism_effectiveness",
            update_type="bayesian_update",
            entity_id=payload["user_id"],
            update_data={
                "mechanisms": payload["mechanisms"],
                "outcome": payload["converted"],
                "weights": payload.get("mechanism_weights", {})
            },
            priority=LearningPriority.IMMEDIATE
        ))
        
        # 2. User profile receptivity (immediate)
        updates.append(LearningUpdate(
            target_component="user_profile",
            update_type="mechanism_receptivity",
            entity_id=payload["user_id"],
            update_data={
                "mechanisms": payload["mechanisms"],
                "outcome_value": 1.0 if payload["converted"] else (
                    0.5 if payload["clicked"] else (
                        0.3 if payload["listened_through"] else 0.1
                    )
                )
            },
            priority=LearningPriority.IMMEDIATE
        ))
        
        # 3. Content-ad affinity (batch)
        updates.append(LearningUpdate(
            target_component="content_ad_matcher",
            update_type="affinity_observation",
            entity_id=f"{payload.get('content_id')}:{payload.get('creative_id')}",
            update_data={
                "content_features": payload.get("content_context", {}),
                "outcome": 1.0 if payload["converted"] else 0.0
            },
            priority=LearningPriority.BATCH
        ))
        
        # 4. Station priors (batch)
        if payload.get("station_id"):
            updates.append(LearningUpdate(
                target_component="station_learning",
                update_type="mechanism_effectiveness",
                entity_id=payload["station_id"],
                update_data={
                    "mechanisms": payload["mechanisms"],
                    "outcome": payload["converted"]
                },
                priority=LearningPriority.BATCH
            ))
        
        # 5. Discovery engine observation (batch)
        updates.append(LearningUpdate(
            target_component="discovery_engine",
            update_type="outcome_observation",
            entity_id=signal.signal_id,
            update_data=payload,
            priority=LearningPriority.BATCH
        ))
        
        # 6. Model monitoring (batch)
        updates.append(LearningUpdate(
            target_component="model_monitoring",
            update_type="prediction_vs_actual",
            entity_id=payload.get("decision_id"),
            update_data={
                "predictions": payload.get("predictions", {}),
                "actuals": {
                    "clicked": payload.get("clicked"),
                    "converted": payload.get("converted"),
                    "listened_through": payload.get("listened_through")
                }
            },
            priority=LearningPriority.BATCH
        ))
        
        return updates
    
    def _genres_to_traits(self, genres: List[str]) -> Dict[str, float]:
        """
        Map music genres to Big Five trait signals.
        
        Based on Rentfrow & Gosling MUSIC model.
        """
        trait_signals = {
            "openness": 0,
            "conscientiousness": 0,
            "extraversion": 0,
            "agreeableness": 0,
            "neuroticism": 0
        }
        
        # Genre → Trait mappings (simplified)
        GENRE_TRAITS = {
            "classical": {"openness": 0.44, "conscientiousness": 0.1},
            "jazz": {"openness": 0.40, "extraversion": -0.1},
            "rock": {"openness": 0.18, "agreeableness": -0.15},
            "pop": {"extraversion": 0.20, "openness": 0.10},
            "hip-hop": {"extraversion": 0.25, "openness": 0.15},
            "country": {"agreeableness": 0.20, "conscientiousness": 0.15},
            "electronic": {"openness": 0.25, "extraversion": 0.20},
            # ... more mappings
        }
        
        for genre in genres:
            genre_lower = genre.lower()
            if genre_lower in GENRE_TRAITS:
                for trait, contribution in GENRE_TRAITS[genre_lower].items():
                    trait_signals[trait] += contribution
        
        # Normalize by genre count
        if genres:
            for trait in trait_signals:
                trait_signals[trait] /= len(genres)
        
        return trait_signals
```

---

# PART 5: NEO4J SCHEMA ADDITIONS

**Add these node types to the Neo4j schema (from ADAM_EMERGENT_INTELLIGENCE_ARCHITECTURE.md):**

```cypher
// =============================================================================
// iHEART CONTENT DOMAIN
// =============================================================================

// Station Node
CREATE CONSTRAINT station_id_unique IF NOT EXISTS
FOR (s:Station) REQUIRE s.station_id IS UNIQUE;

CREATE INDEX station_format_idx IF NOT EXISTS
FOR (s:Station) ON (s.format);

CREATE INDEX station_market_idx IF NOT EXISTS
FOR (s:Station) ON (s.market);


// Artist Node
CREATE CONSTRAINT artist_id_unique IF NOT EXISTS
FOR (a:Artist) REQUIRE a.artist_id IS UNIQUE;

CREATE INDEX artist_genre_idx IF NOT EXISTS
FOR (a:Artist) ON (a.primary_genre);


// Track Node
CREATE CONSTRAINT track_id_unique IF NOT EXISTS
FOR (t:Track) REQUIRE t.track_id IS UNIQUE;

CREATE INDEX track_energy_idx IF NOT EXISTS
FOR (t:Track) ON (t.energy);

CREATE INDEX track_valence_idx IF NOT EXISTS
FOR (t:Track) ON (t.valence);


// Lyrics Node
CREATE CONSTRAINT lyrics_id_unique IF NOT EXISTS
FOR (l:Lyrics) REQUIRE l.lyrics_id IS UNIQUE;


// Podcast Node
CREATE CONSTRAINT podcast_id_unique IF NOT EXISTS
FOR (p:Podcast) REQUIRE p.podcast_id IS UNIQUE;

CREATE INDEX podcast_category_idx IF NOT EXISTS
FOR (p:Podcast) ON (p.category);


// Episode Node
CREATE CONSTRAINT episode_id_unique IF NOT EXISTS
FOR (e:Episode) REQUIRE e.episode_id IS UNIQUE;


// Transcript Node
CREATE CONSTRAINT transcript_id_unique IF NOT EXISTS
FOR (tr:Transcript) REQUIRE tr.transcript_id IS UNIQUE;


// =============================================================================
// iHEART ADVERTISING DOMAIN
// =============================================================================

// Brand Node
CREATE CONSTRAINT brand_id_unique IF NOT EXISTS
FOR (b:Brand) REQUIRE b.brand_id IS UNIQUE;


// Campaign Node
CREATE CONSTRAINT campaign_id_unique IF NOT EXISTS
FOR (c:Campaign) REQUIRE c.campaign_id IS UNIQUE;


// Creative Node
CREATE CONSTRAINT creative_id_unique IF NOT EXISTS
FOR (cr:Creative) REQUIRE cr.creative_id IS UNIQUE;


// AdDecision Node (for learning)
CREATE CONSTRAINT decision_id_unique IF NOT EXISTS
FOR (d:AdDecision) REQUIRE d.decision_id IS UNIQUE;

CREATE INDEX decision_user_idx IF NOT EXISTS
FOR (d:AdDecision) ON (d.user_id);

CREATE INDEX decision_time_idx IF NOT EXISTS
FOR (d:AdDecision) ON (d.timestamp);


// =============================================================================
// iHEART RELATIONSHIPS
// =============================================================================

// Station relationships
// (u:User)-[:LISTENS_TO {duration: int, first_listen: datetime}]->(s:Station)
// (s:Station)-[:HAS_FORMAT]->(f:StationFormat)
// (s:Station)-[:IN_MARKET]->(m:Market)

// Content relationships
// (t:Track)-[:BY_ARTIST]->(a:Artist)
// (t:Track)-[:HAS_LYRICS]->(l:Lyrics)
// (l:Lyrics)-[:EXPRESSES_THEME]->(th:Theme)
// (p:Podcast)-[:HAS_EPISODE]->(e:Episode)
// (e:Episode)-[:HAS_TRANSCRIPT]->(tr:Transcript)

// Ad relationships
// (b:Brand)-[:RUNS_CAMPAIGN]->(c:Campaign)
// (c:Campaign)-[:HAS_CREATIVE]->(cr:Creative)
// (u:User)-[:EXPOSED_TO {decision_id: str, timestamp: datetime}]->(cr:Creative)
// (d:AdDecision)-[:USED_MECHANISM]->(m:CognitiveMechanism)

// Learning relationships
// (s:Station)-[:HAS_MECHANISM_EFFECTIVENESS {success_rate: float}]->(m:CognitiveMechanism)
// (t:Track)-[:PRIMES_MECHANISM {strength: float}]->(m:CognitiveMechanism)
```

---

# PART 6: KAFKA EVENT ADDITIONS

**Add these event types to Kafka contracts:**

```python
# =============================================================================
# iHEART KAFKA EVENTS
# =============================================================================

# Topic: iheart.listening.events
class iHeartListeningEvent(ADAMEvent):
    event_type: str = "iheart.listening"
    
    user_id: str
    session_id: str
    content_type: str  # "music", "podcast", "talk"
    content_id: str
    station_id: Optional[str]
    
    # For music
    track_id: Optional[str]
    artist_id: Optional[str]
    genres: List[str] = Field(default_factory=list)
    energy: Optional[float]
    valence: Optional[float]
    
    # For podcasts
    podcast_id: Optional[str]
    episode_id: Optional[str]
    category: Optional[str]
    topics: List[str] = Field(default_factory=list)
    
    # Engagement
    duration_seconds: int
    completed: bool
    completion_percentage: Optional[float]


# Topic: iheart.ad.requests
class iHeartAdRequestEvent(ADAMEvent):
    event_type: str = "iheart.ad.request"
    
    request_id: str
    user_id: Optional[str]
    session_id: str
    station_id: Optional[str]
    podcast_id: Optional[str]
    slot_id: str
    
    # Context
    content_energy: Optional[float]
    content_valence: Optional[float]
    current_topic: Optional[str]


# Topic: iheart.ad.decisions
class iHeartAdDecisionEvent(ADAMEvent):
    event_type: str = "iheart.ad.decision"
    
    decision_id: str
    request_id: str
    user_id: str
    
    # Selection
    campaign_id: str
    creative_id: str
    copy_variant_id: str
    
    # Targeting
    mechanisms_used: List[str]
    regulatory_focus: str
    construal_level: str
    
    # Predictions
    predicted_listen_through: float
    predicted_ctr: float
    predicted_conversion: Optional[float]
    
    # Context
    station_id: Optional[str]
    content_energy: Optional[float]
    user_data_tier: str


# Topic: iheart.ad.outcomes
class iHeartAdOutcomeEvent(ADAMEvent):
    event_type: str = "iheart.ad.outcome"
    
    decision_id: str
    user_id: str
    
    # Outcomes
    listened_through: bool
    listen_percentage: float
    clicked: bool
    converted: bool
    conversion_type: Optional[str]
    conversion_value: Optional[float]
    
    # Timing
    time_since_decision_seconds: int
```

---

# PART 7: IDENTITY RESOLUTION (#19) ADDITIONS

**Add iHeart ID integration:**

```python
# Add to IdentityPlatform enum
class IdentityPlatform(str, Enum):
    # ... existing platforms ...
    
    IHEART = "iheart"
    IHEART_DEVICE = "iheart_device"


# Add iHeart resolver
class iHeartIdentityResolver(PlatformResolver):
    """Resolve iHeart user IDs to ADAM canonical IDs."""
    
    platform = IdentityPlatform.IHEART
    
    async def resolve(
        self,
        platform_id: str,
        hints: Optional[Dict[str, str]] = None
    ) -> Optional[ResolvedIdentity]:
        # Check deterministic match first
        existing = await self.graph.find_user_by_platform_id(
            platform=self.platform,
            platform_id=platform_id
        )
        
        if existing:
            return existing
        
        # Try hints (UID2, RampID, etc.)
        if hints:
            for hint_platform, hint_id in hints.items():
                matched = await self._try_hint_match(hint_platform, hint_id)
                if matched:
                    # Link iHeart ID to matched identity
                    await self.graph.link_platform_id(
                        canonical_id=matched.canonical_id,
                        platform=self.platform,
                        platform_id=platform_id
                    )
                    return matched
        
        # No match - return None (will create new or use anonymous)
        return None
```

---

# PART 8: IMPLEMENTATION VALIDATION CHECKLIST

Use this checklist to verify all cross-component changes are implemented:

## Signal Aggregation (#08)
- [ ] Added AUDIO_LISTENING signal category
- [ ] Added AUDIO_SKIP signal category
- [ ] Added AD_LISTEN_THROUGH signal category
- [ ] Added AD_INTERACTION signal category
- [ ] Implemented iHeartListeningProcessor
- [ ] Implemented iHeartSkipProcessor
- [ ] Implemented iHeartAdInteractionProcessor
- [ ] Added iHeart Kafka sources to Flink config

## Cold Start (#13)
- [ ] Added IHEART_STATION context source
- [ ] Added IHEART_FORMAT context source
- [ ] Added IHEART_LISTENING_HISTORY context source
- [ ] Implemented bootstrap_from_iheart_context()
- [ ] Implemented update_format_priors_from_iheart()
- [ ] Added iHeart-derived archetypes

## Copy Generation (#15)
- [ ] Added AudioCopyMode enum
- [ ] Added AudioCopyRequest model
- [ ] Added AudioParameters model
- [ ] Added GeneratedAudioCopy model
- [ ] Implemented generate_audio_copy()
- [ ] Implemented _calculate_audio_params()
- [ ] Implemented _generate_ssml()
- [ ] Implemented voice selection logic

## Gradient Bridge (#06)
- [ ] Registered iheart_listening handler
- [ ] Registered iheart_outcome handler
- [ ] Registered iheart_content_analysis handler
- [ ] Implemented _handle_listening_signal()
- [ ] Implemented _handle_outcome_signal()
- [ ] Implemented _genres_to_traits()

## Neo4j Schema
- [ ] Created Station node type
- [ ] Created Artist node type
- [ ] Created Track node type
- [ ] Created Lyrics node type
- [ ] Created Podcast node type
- [ ] Created Episode node type
- [ ] Created Transcript node type
- [ ] Created Brand node type
- [ ] Created Campaign node type
- [ ] Created Creative node type
- [ ] Created AdDecision node type
- [ ] Created all indexes
- [ ] Created all relationships

## Kafka Events
- [ ] Added iHeartListeningEvent
- [ ] Added iHeartAdRequestEvent
- [ ] Added iHeartAdDecisionEvent
- [ ] Added iHeartAdOutcomeEvent
- [ ] Configured all topics

## Identity Resolution (#19)
- [ ] Added IHEART platform
- [ ] Implemented iHeartIdentityResolver

---

**END OF INTEGRATION BRIDGE ADDENDUM**

This document ensures that all cross-component changes required for iHeart integration are explicitly tracked and implemented.
