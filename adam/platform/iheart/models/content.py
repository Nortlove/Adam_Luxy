# =============================================================================
# ADAM iHeart Content Models
# Location: adam/platform/iheart/models/content.py
# =============================================================================

"""
CONTENT MODELS

Audio content entities: tracks, artists, podcasts, episodes.

Key psychological signals from content:
- Track audio features (energy, valence) → arousal/mood state
- Genre preferences → personality correlates
- Lyrics content → emotional/topical exposure
- Podcast topics → interests, values
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


# =============================================================================
# GENRE MODEL
# =============================================================================

class Genre(BaseModel):
    """
    Music or podcast genre with psychological correlates.
    
    Genres carry psychological priors - jazz listeners differ
    from country listeners in predictable ways.
    """
    
    genre_id: str = Field(default_factory=lambda: f"genre_{uuid4().hex[:12]}")
    name: str
    parent_genre_id: Optional[str] = None
    
    # Psychological correlates (Big Five)
    openness_correlation: float = Field(default=0.0, ge=-1.0, le=1.0)
    conscientiousness_correlation: float = Field(default=0.0, ge=-1.0, le=1.0)
    extraversion_correlation: float = Field(default=0.0, ge=-1.0, le=1.0)
    agreeableness_correlation: float = Field(default=0.0, ge=-1.0, le=1.0)
    neuroticism_correlation: float = Field(default=0.0, ge=-1.0, le=1.0)
    
    # Content characteristics
    typical_energy: float = Field(default=0.5, ge=0.0, le=1.0)
    typical_valence: float = Field(default=0.5, ge=0.0, le=1.0)
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# =============================================================================
# AUDIO FEATURES MODEL (Spotify-style)
# =============================================================================

class AudioFeatures(BaseModel):
    """
    Audio features for a track (Spotify Audio Features style).
    
    These map to psychological states:
    - High energy + high valence → arousal, promotion focus
    - Low energy + low valence → calm, prevention focus
    - High tempo → urgency, action orientation
    """
    
    # Core features (0.0 - 1.0 normalized)
    energy: float = Field(ge=0.0, le=1.0, description="Intensity and activity")
    valence: float = Field(ge=0.0, le=1.0, description="Musical positiveness")
    danceability: float = Field(ge=0.0, le=1.0, description="Danceability")
    acousticness: float = Field(ge=0.0, le=1.0, description="Acoustic quality")
    instrumentalness: float = Field(ge=0.0, le=1.0, description="Vocal absence")
    liveness: float = Field(ge=0.0, le=1.0, description="Live performance presence")
    speechiness: float = Field(ge=0.0, le=1.0, description="Spoken word presence")
    
    # Non-normalized features
    tempo: float = Field(ge=0.0, description="BPM")
    loudness: float = Field(description="Average loudness in dB")
    key: int = Field(ge=0, le=11, description="Pitch class (0=C, 1=C#, ...)")
    mode: int = Field(ge=0, le=1, description="0=minor, 1=major")
    time_signature: int = Field(ge=1, le=7, default=4)
    duration_ms: int = Field(ge=0, description="Track duration in ms")
    
    # Psychological mappings (computed)
    arousal_score: float = Field(default=0.5, ge=0.0, le=1.0)
    pleasure_score: float = Field(default=0.5, ge=0.0, le=1.0)
    
    def compute_psychological_scores(self) -> None:
        """Compute arousal and pleasure from audio features."""
        # Arousal = f(energy, tempo, loudness)
        tempo_norm = min(1.0, self.tempo / 180.0)  # Normalize to 0-1
        loudness_norm = min(1.0, max(0.0, (self.loudness + 60) / 60))  # -60dB to 0dB
        self.arousal_score = (self.energy * 0.5 + tempo_norm * 0.3 + loudness_norm * 0.2)
        
        # Pleasure = f(valence, mode, danceability)
        mode_boost = 0.1 if self.mode == 1 else -0.1
        self.pleasure_score = min(1.0, max(0.0, self.valence * 0.6 + self.danceability * 0.3 + mode_boost))


# =============================================================================
# ARTIST MODEL
# =============================================================================

class Artist(BaseModel):
    """
    Music artist with learned psychological profile.
    
    Artists carry personality signals - fans of certain artists
    share psychological characteristics.
    """
    
    artist_id: str = Field(..., description="Unique artist identifier")
    name: str
    
    # Spotify/iHeart identifiers
    spotify_id: Optional[str] = None
    iheart_id: Optional[str] = None
    
    # Bio and metadata
    bio: Optional[str] = None
    genres: List[str] = Field(default_factory=list)
    popularity: int = Field(default=0, ge=0, le=100)
    
    # Aggregate audio features of discography
    avg_energy: float = Field(default=0.5, ge=0.0, le=1.0)
    avg_valence: float = Field(default=0.5, ge=0.0, le=1.0)
    avg_tempo: float = Field(default=120.0, ge=0.0)
    
    # Psychological profile of fan base (ADAM-derived)
    fan_openness_mean: float = Field(default=0.5, ge=0.0, le=1.0)
    fan_conscientiousness_mean: float = Field(default=0.5, ge=0.0, le=1.0)
    fan_extraversion_mean: float = Field(default=0.5, ge=0.0, le=1.0)
    fan_agreeableness_mean: float = Field(default=0.5, ge=0.0, le=1.0)
    fan_neuroticism_mean: float = Field(default=0.5, ge=0.0, le=1.0)
    
    # Embedding for similarity search
    personality_embedding: List[float] = Field(default_factory=list)
    
    # Statistics
    follower_count: int = Field(default=0, ge=0)
    monthly_listeners: int = Field(default=0, ge=0)
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# =============================================================================
# TRACK MODEL
# =============================================================================

class Track(BaseModel):
    """
    A music track with audio features and metadata.
    
    Tracks are the atomic content unit for music.
    Audio features map to psychological states.
    Lyrics carry emotional/topical signals.
    """
    
    track_id: str = Field(..., description="Unique track identifier")
    
    # Identifiers
    isrc: Optional[str] = Field(None, description="International Standard Recording Code")
    spotify_id: Optional[str] = None
    iheart_id: Optional[str] = None
    
    # Metadata
    title: str
    artist_id: str
    artist_name: str
    album: Optional[str] = None
    album_id: Optional[str] = None
    release_date: Optional[datetime] = None
    
    # Audio features
    audio_features: Optional[AudioFeatures] = None
    audio_embedding: List[float] = Field(default_factory=list)
    
    # Lyrics (for content matching and emotional analysis)
    has_lyrics: bool = Field(default=False)
    lyrics_preview: Optional[str] = None  # First ~200 chars
    lyrics_embedding: List[float] = Field(default_factory=list)
    
    # Emotional content from lyrics
    lyrics_valence: Optional[float] = Field(None, ge=0.0, le=1.0)
    lyrics_arousal: Optional[float] = Field(None, ge=0.0, le=1.0)
    lyrics_topics: List[str] = Field(default_factory=list)
    
    # Genre classification
    primary_genre: Optional[str] = None
    genres: List[str] = Field(default_factory=list)
    
    # Popularity and usage
    popularity: int = Field(default=0, ge=0, le=100)
    play_count: int = Field(default=0, ge=0)
    skip_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    completion_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    
    # Content flags
    explicit: bool = Field(default=False)
    duration_ms: int = Field(default=0, ge=0)
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# =============================================================================
# PODCAST MODELS
# =============================================================================

class Podcast(BaseModel):
    """
    A podcast show.
    
    Podcasts carry strong topical/interest signals.
    Listeners self-select into content that reflects
    their values, interests, and psychological profile.
    """
    
    podcast_id: str = Field(..., description="Unique podcast identifier")
    
    # Metadata
    title: str
    description: Optional[str] = None
    publisher: Optional[str] = None
    
    # Classification
    category: Optional[str] = None
    topics: List[str] = Field(default_factory=list)
    language: str = Field(default="en")
    
    # Psychological profile of listener base
    listener_openness_mean: float = Field(default=0.5, ge=0.0, le=1.0)
    listener_conscientiousness_mean: float = Field(default=0.5, ge=0.0, le=1.0)
    listener_extraversion_mean: float = Field(default=0.5, ge=0.0, le=1.0)
    listener_agreeableness_mean: float = Field(default=0.5, ge=0.0, le=1.0)
    listener_neuroticism_mean: float = Field(default=0.5, ge=0.0, le=1.0)
    
    # Topic embedding for similarity
    topic_embedding: List[float] = Field(default_factory=list)
    
    # Statistics
    subscriber_count: int = Field(default=0, ge=0)
    episode_count: int = Field(default=0, ge=0)
    avg_episode_duration_min: float = Field(default=0.0, ge=0.0)
    avg_completion_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    
    # Content characteristics
    explicit: bool = Field(default=False)
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PodcastEpisode(BaseModel):
    """
    A podcast episode.
    
    Episodes carry specific topical signals.
    Transcript analysis reveals emotional content and topics.
    """
    
    episode_id: str = Field(..., description="Unique episode identifier")
    podcast_id: str
    
    # Metadata
    title: str
    description: Optional[str] = None
    published_at: Optional[datetime] = None
    duration_ms: int = Field(default=0, ge=0)
    
    # Content analysis
    topics: List[str] = Field(default_factory=list)
    entities_mentioned: List[str] = Field(default_factory=list)
    
    # Transcript (for content matching)
    has_transcript: bool = Field(default=False)
    transcript_preview: Optional[str] = None  # First ~500 chars
    
    # Emotional content from transcript
    transcript_valence: Optional[float] = Field(None, ge=0.0, le=1.0)
    transcript_arousal: Optional[float] = Field(None, ge=0.0, le=1.0)
    
    # Statistics
    play_count: int = Field(default=0, ge=0)
    completion_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    
    # Content flags
    explicit: bool = Field(default=False)
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
