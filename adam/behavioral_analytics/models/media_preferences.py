# =============================================================================
# ADAM Behavioral Analytics: Media Preference Models
# Location: adam/behavioral_analytics/models/media_preferences.py
# =============================================================================

"""
MEDIA PREFERENCE MODELS

Models for capturing media consumption preferences that predict personality
and psychological traits.

Research Foundation:
- Music preferences predict Big Five personality (r=0.30-0.44 for Openness)
- Podcast preferences correlate with morbid curiosity and personality
- Book genres predict cognitive styles and values
- Film/TV preferences reflect personality and need states

The MUSIC Model (Rentfrow et al.):
- Mellow: Romantic, slow, quiet, sad (Jazz, R&B, Soul)
- Unpretentious: Uncomplicated, relaxing, acoustic (Country, Folk)
- Sophisticated: Complex, dynamic, intelligent (Classical, World)
- Intense: Distorted, loud, aggressive (Metal, Punk, Rock)
- Contemporary: Rhythmic, percussive, electronic (EDM, Hip-Hop, Pop)

These preferences are used as implicit signals for:
- Personality inference (especially Openness, Extraversion)
- Cognitive style estimation
- Identity construction mechanism activation
- Content-based targeting
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field
import uuid


# =============================================================================
# ENUMS
# =============================================================================

class MusicGenre(str, Enum):
    """Music genre categories aligned with MUSIC model."""
    # Mellow
    JAZZ = "jazz"
    RNB = "rnb"
    SOUL = "soul"
    SOFT_ROCK = "soft_rock"
    ACOUSTIC = "acoustic"
    
    # Unpretentious
    COUNTRY = "country"
    FOLK = "folk"
    BLUEGRASS = "bluegrass"
    RELIGIOUS = "religious"
    
    # Sophisticated
    CLASSICAL = "classical"
    OPERA = "opera"
    WORLD = "world"
    AVANT_GARDE = "avant_garde"
    
    # Intense
    METAL = "metal"
    PUNK = "punk"
    HARD_ROCK = "hard_rock"
    ALTERNATIVE = "alternative"
    
    # Contemporary
    EDM = "edm"
    HIP_HOP = "hip_hop"
    POP = "pop"
    RAP = "rap"
    DANCE = "dance"
    
    # Other
    INDIE = "indie"
    ROCK = "rock"
    OTHER = "other"


class PodcastGenre(str, Enum):
    """Podcast genre categories."""
    TRUE_CRIME = "true_crime"
    COMEDY = "comedy"
    NEWS_POLITICS = "news_politics"
    EDUCATIONAL = "educational"
    BUSINESS = "business"
    HEALTH_WELLNESS = "health_wellness"
    SPORTS = "sports"
    TECHNOLOGY = "technology"
    SOCIETY_CULTURE = "society_culture"
    STORYTELLING = "storytelling"
    INTERVIEW = "interview"
    SCIENCE = "science"
    HISTORY = "history"
    SELF_HELP = "self_help"
    OTHER = "other"


class BookGenre(str, Enum):
    """Book genre categories."""
    FICTION = "fiction"
    NON_FICTION = "non_fiction"
    MYSTERY_THRILLER = "mystery_thriller"
    SCIENCE_FICTION = "science_fiction"
    FANTASY = "fantasy"
    ROMANCE = "romance"
    BIOGRAPHY = "biography"
    SELF_HELP = "self_help"
    BUSINESS = "business"
    HISTORY = "history"
    SCIENCE = "science"
    PHILOSOPHY = "philosophy"
    POETRY = "poetry"
    OTHER = "other"


class FilmTVGenre(str, Enum):
    """Film and TV genre categories."""
    ACTION = "action"
    COMEDY = "comedy"
    DRAMA = "drama"
    HORROR = "horror"
    THRILLER = "thriller"
    SCIENCE_FICTION = "science_fiction"
    FANTASY = "fantasy"
    ROMANCE = "romance"
    DOCUMENTARY = "documentary"
    REALITY_TV = "reality_tv"
    ANIMATION = "animation"
    TRUE_CRIME = "true_crime"
    NEWS = "news"
    OTHER = "other"


class ListeningFrequency(str, Enum):
    """Frequency of media consumption."""
    DAILY = "daily"
    SEVERAL_TIMES_WEEK = "several_times_week"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    RARELY = "rarely"


# =============================================================================
# MUSIC PREFERENCES
# =============================================================================

class MUSICDimensions(BaseModel):
    """
    MUSIC model dimensions for music preferences.
    
    Based on Rentfrow, Goldberg, & Levitin (2011).
    Each dimension is 0-1 scale.
    """
    # Mellow: Romantic, slow, quiet, sad
    # Associated with: high Agreeableness, low Extraversion
    mellow: float = Field(
        default=0.5, ge=0.0, le=1.0,
        description="Preference for romantic, slow, quiet music"
    )
    
    # Unpretentious: Uncomplicated, relaxing, acoustic
    # Associated with: high Agreeableness, high Conscientiousness
    unpretentious: float = Field(
        default=0.5, ge=0.0, le=1.0,
        description="Preference for uncomplicated, relaxing music"
    )
    
    # Sophisticated: Complex, dynamic, intelligent
    # Associated with: high Openness (r=0.30-0.44)
    sophisticated: float = Field(
        default=0.5, ge=0.0, le=1.0,
        description="Preference for complex, intelligent music"
    )
    
    # Intense: Distorted, loud, aggressive
    # Associated with: high Openness, low Agreeableness
    intense: float = Field(
        default=0.5, ge=0.0, le=1.0,
        description="Preference for loud, aggressive music"
    )
    
    # Contemporary: Rhythmic, percussive, electronic
    # Associated with: high Extraversion
    contemporary: float = Field(
        default=0.5, ge=0.0, le=1.0,
        description="Preference for rhythmic, electronic music"
    )
    
    def get_dominant_dimension(self) -> str:
        """Get the most dominant MUSIC dimension."""
        dimensions = {
            "mellow": self.mellow,
            "unpretentious": self.unpretentious,
            "sophisticated": self.sophisticated,
            "intense": self.intense,
            "contemporary": self.contemporary,
        }
        return max(dimensions, key=dimensions.get)


class MusicPreference(BaseModel):
    """
    Music preference profile.
    
    Used to infer personality traits, especially Openness to Experience.
    """
    preference_id: str = Field(default_factory=lambda: f"mus_{uuid.uuid4().hex[:12]}")
    
    # Preferred genres
    genres: List[MusicGenre] = Field(default_factory=list)
    
    # MUSIC model dimensions (derived from genres or self-reported)
    music_dimensions: MUSICDimensions = Field(default_factory=MUSICDimensions)
    
    # Listening patterns
    listening_frequency: ListeningFrequency = ListeningFrequency.WEEKLY
    listening_hours_per_week: float = 5.0
    
    # Platform data (if available)
    spotify_connected: bool = False
    apple_music_connected: bool = False
    
    # Diversity metrics
    genre_diversity: float = Field(
        default=0.5, ge=0.0, le=1.0,
        description="Diversity of genre preferences"
    )
    
    # Temporal patterns
    peak_listening_hours: List[int] = Field(default_factory=list)
    
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    
    def derive_music_dimensions(self) -> None:
        """
        Derive MUSIC dimensions from genre preferences.
        
        Maps genres to MUSIC model dimensions.
        """
        genre_to_music = {
            # Mellow
            MusicGenre.JAZZ: {"mellow": 0.8, "sophisticated": 0.6},
            MusicGenre.RNB: {"mellow": 0.7, "contemporary": 0.5},
            MusicGenre.SOUL: {"mellow": 0.8, "unpretentious": 0.4},
            MusicGenre.SOFT_ROCK: {"mellow": 0.6, "unpretentious": 0.5},
            MusicGenre.ACOUSTIC: {"mellow": 0.7, "unpretentious": 0.6},
            # Unpretentious
            MusicGenre.COUNTRY: {"unpretentious": 0.9, "mellow": 0.4},
            MusicGenre.FOLK: {"unpretentious": 0.8, "sophisticated": 0.4},
            MusicGenre.BLUEGRASS: {"unpretentious": 0.8, "mellow": 0.3},
            MusicGenre.RELIGIOUS: {"unpretentious": 0.7, "mellow": 0.5},
            # Sophisticated
            MusicGenre.CLASSICAL: {"sophisticated": 0.9, "mellow": 0.5},
            MusicGenre.OPERA: {"sophisticated": 0.9, "intense": 0.4},
            MusicGenre.WORLD: {"sophisticated": 0.8, "contemporary": 0.3},
            MusicGenre.AVANT_GARDE: {"sophisticated": 0.9, "intense": 0.5},
            # Intense
            MusicGenre.METAL: {"intense": 0.9, "sophisticated": 0.3},
            MusicGenre.PUNK: {"intense": 0.8, "contemporary": 0.4},
            MusicGenre.HARD_ROCK: {"intense": 0.8, "mellow": 0.1},
            MusicGenre.ALTERNATIVE: {"intense": 0.6, "sophisticated": 0.5},
            # Contemporary
            MusicGenre.EDM: {"contemporary": 0.9, "intense": 0.5},
            MusicGenre.HIP_HOP: {"contemporary": 0.8, "intense": 0.4},
            MusicGenre.POP: {"contemporary": 0.8, "mellow": 0.4},
            MusicGenre.RAP: {"contemporary": 0.8, "intense": 0.5},
            MusicGenre.DANCE: {"contemporary": 0.9, "mellow": 0.2},
            # Other
            MusicGenre.INDIE: {"sophisticated": 0.6, "intense": 0.4},
            MusicGenre.ROCK: {"intense": 0.6, "contemporary": 0.4},
        }
        
        dimension_totals = {
            "mellow": 0.0,
            "unpretentious": 0.0,
            "sophisticated": 0.0,
            "intense": 0.0,
            "contemporary": 0.0,
        }
        
        for genre in self.genres:
            if genre in genre_to_music:
                for dim, value in genre_to_music[genre].items():
                    dimension_totals[dim] += value
        
        if self.genres:
            count = len(self.genres)
            self.music_dimensions = MUSICDimensions(
                mellow=min(1.0, dimension_totals["mellow"] / count),
                unpretentious=min(1.0, dimension_totals["unpretentious"] / count),
                sophisticated=min(1.0, dimension_totals["sophisticated"] / count),
                intense=min(1.0, dimension_totals["intense"] / count),
                contemporary=min(1.0, dimension_totals["contemporary"] / count),
            )


# =============================================================================
# PODCAST PREFERENCES
# =============================================================================

class PodcastPreference(BaseModel):
    """
    Podcast preference profile.
    
    Research:
    - True crime correlates with morbid curiosity (sr=0.51)
    - News/politics correlates with need for cognition
    - Comedy correlates with Extraversion
    """
    preference_id: str = Field(default_factory=lambda: f"pod_{uuid.uuid4().hex[:12]}")
    
    # Preferred genres
    genres: List[PodcastGenre] = Field(default_factory=list)
    
    # Listening patterns
    listening_frequency: ListeningFrequency = ListeningFrequency.WEEKLY
    average_episode_completion: float = Field(
        default=0.7, ge=0.0, le=1.0,
        description="Average percentage of episodes completed"
    )
    
    # Genre-specific metrics
    true_crime_engagement: float = Field(
        default=0.0, ge=0.0, le=1.0,
        description="Engagement with true crime content (morbid curiosity indicator)"
    )
    news_politics_engagement: float = Field(
        default=0.0, ge=0.0, le=1.0,
        description="Engagement with news/politics (social belonging need)"
    )
    educational_engagement: float = Field(
        default=0.0, ge=0.0, le=1.0,
        description="Engagement with educational content (need for cognition)"
    )
    
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    
    def derive_engagement_scores(self) -> None:
        """Derive engagement scores from genre preferences."""
        if PodcastGenre.TRUE_CRIME in self.genres:
            # Base score from having the genre
            self.true_crime_engagement = 0.7
            # Boost if it's the primary genre
            if self.genres and self.genres[0] == PodcastGenre.TRUE_CRIME:
                self.true_crime_engagement = 0.9
        
        if PodcastGenre.NEWS_POLITICS in self.genres:
            self.news_politics_engagement = 0.7
            if self.genres and self.genres[0] == PodcastGenre.NEWS_POLITICS:
                self.news_politics_engagement = 0.9
        
        educational_genres = {PodcastGenre.EDUCATIONAL, PodcastGenre.SCIENCE, PodcastGenre.HISTORY}
        if educational_genres.intersection(set(self.genres)):
            self.educational_engagement = 0.7
            if self.genres and self.genres[0] in educational_genres:
                self.educational_engagement = 0.9


# =============================================================================
# BOOK PREFERENCES
# =============================================================================

class BookPreference(BaseModel):
    """
    Book/reading preference profile.
    
    Research:
    - Fiction vs non-fiction indicates cognitive style
    - Genre diversity correlates with Openness
    """
    preference_id: str = Field(default_factory=lambda: f"book_{uuid.uuid4().hex[:12]}")
    
    # Preferred genres
    genres: List[BookGenre] = Field(default_factory=list)
    
    # Reading patterns
    fiction_preference: float = Field(
        default=0.5, ge=0.0, le=1.0,
        description="0=non-fiction only, 1=fiction only"
    )
    books_per_year: int = 0
    
    # Genre diversity
    genre_diversity: float = Field(default=0.5, ge=0.0, le=1.0)
    
    last_updated: datetime = Field(default_factory=datetime.utcnow)


# =============================================================================
# FILM/TV PREFERENCES
# =============================================================================

class FilmTVPreference(BaseModel):
    """
    Film and TV preference profile.
    
    Research:
    - Horror preference indicates sensation seeking
    - Documentary preference indicates Openness
    - Reality TV indicates social comparison tendencies
    """
    preference_id: str = Field(default_factory=lambda: f"ftv_{uuid.uuid4().hex[:12]}")
    
    # Preferred genres
    genres: List[FilmTVGenre] = Field(default_factory=list)
    
    # Viewing patterns
    hours_per_week: float = 10.0
    binge_watching_frequency: float = Field(
        default=0.3, ge=0.0, le=1.0,
        description="How often they binge-watch"
    )
    
    # Genre-specific indicators
    horror_preference: float = Field(
        default=0.0, ge=0.0, le=1.0,
        description="Horror engagement (sensation seeking indicator)"
    )
    documentary_preference: float = Field(
        default=0.0, ge=0.0, le=1.0,
        description="Documentary engagement (Openness indicator)"
    )
    reality_tv_preference: float = Field(
        default=0.0, ge=0.0, le=1.0,
        description="Reality TV engagement (mimetic/social comparison)"
    )
    
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    
    def derive_preference_scores(self) -> None:
        """Derive preference scores from genres."""
        if FilmTVGenre.HORROR in self.genres:
            self.horror_preference = 0.7
            if self.genres and self.genres[0] == FilmTVGenre.HORROR:
                self.horror_preference = 0.9
        
        if FilmTVGenre.DOCUMENTARY in self.genres:
            self.documentary_preference = 0.7
            if self.genres and self.genres[0] == FilmTVGenre.DOCUMENTARY:
                self.documentary_preference = 0.9
        
        if FilmTVGenre.REALITY_TV in self.genres:
            self.reality_tv_preference = 0.7
            if self.genres and self.genres[0] == FilmTVGenre.REALITY_TV:
                self.reality_tv_preference = 0.9


# =============================================================================
# UNIFIED MEDIA CONSUMPTION PROFILE
# =============================================================================

class MediaConsumptionProfile(BaseModel):
    """
    Unified media consumption profile.
    
    Combines all media preferences into a single profile for
    personality inference and mechanism mapping.
    
    This is the media domain equivalent of BehavioralSession.
    """
    profile_id: str = Field(default_factory=lambda: f"mcp_{uuid.uuid4().hex[:12]}")
    user_id: Optional[str] = None
    
    # Individual preference profiles
    music: Optional[MusicPreference] = None
    podcasts: Optional[PodcastPreference] = None
    books: Optional[BookPreference] = None
    film_tv: Optional[FilmTVPreference] = None
    
    # Aggregated personality indicators
    # These are derived from all media preferences combined
    openness_indicator: float = Field(
        default=0.5, ge=0.0, le=1.0,
        description="Aggregated Openness signal from media"
    )
    extraversion_indicator: float = Field(
        default=0.5, ge=0.0, le=1.0,
        description="Aggregated Extraversion signal from media"
    )
    neuroticism_indicator: float = Field(
        default=0.5, ge=0.0, le=1.0,
        description="Aggregated Neuroticism signal from media"
    )
    morbid_curiosity_indicator: float = Field(
        default=0.0, ge=0.0, le=1.0,
        description="Morbid curiosity from true crime consumption"
    )
    need_for_cognition_indicator: float = Field(
        default=0.5, ge=0.0, le=1.0,
        description="Need for cognition from educational content"
    )
    
    # Profile completeness
    domains_available: List[str] = Field(default_factory=list)
    overall_confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    
    def derive_personality_indicators(self) -> None:
        """
        Derive personality indicators from all media preferences.
        
        Research-validated mappings:
        - Sophisticated music → Openness (r=0.30-0.44)
        - Contemporary music → Extraversion
        - True crime → Morbid curiosity (sr=0.51)
        - Documentary → Openness, Need for Cognition
        """
        signals = []
        weights = []
        
        # From music
        if self.music:
            self.domains_available.append("music")
            
            # Openness from sophisticated + intense music
            openness_signal = (
                self.music.music_dimensions.sophisticated * 0.44 +
                self.music.music_dimensions.intense * 0.20
            ) / 0.64  # Normalize by max weight
            signals.append(("openness", openness_signal, 0.44))
            
            # Extraversion from contemporary music
            extraversion_signal = self.music.music_dimensions.contemporary
            signals.append(("extraversion", extraversion_signal, 0.30))
        
        # From podcasts
        if self.podcasts:
            self.domains_available.append("podcasts")
            
            # Morbid curiosity from true crime
            self.morbid_curiosity_indicator = self.podcasts.true_crime_engagement * 0.51
            
            # Need for cognition from educational
            nfc_signal = self.podcasts.educational_engagement
            signals.append(("need_for_cognition", nfc_signal, 0.40))
        
        # From film/TV
        if self.film_tv:
            self.domains_available.append("film_tv")
            
            # Openness from documentaries
            if self.film_tv.documentary_preference > 0:
                signals.append(("openness", self.film_tv.documentary_preference, 0.30))
            
            # Neuroticism from horror (sensation seeking is inverse)
            if self.film_tv.horror_preference > 0:
                signals.append(("neuroticism", 1 - self.film_tv.horror_preference, 0.25))
        
        # From books
        if self.books:
            self.domains_available.append("books")
            
            # Openness from reading volume and diversity
            if self.books.books_per_year > 0:
                reading_signal = min(1.0, self.books.books_per_year / 20)  # 20 books = max
                signals.append(("openness", reading_signal, 0.35))
        
        # Aggregate signals by trait
        trait_signals: Dict[str, List[tuple]] = {}
        for trait, value, weight in signals:
            if trait not in trait_signals:
                trait_signals[trait] = []
            trait_signals[trait].append((value, weight))
        
        # Calculate weighted averages
        for trait, signal_list in trait_signals.items():
            total_weight = sum(w for _, w in signal_list)
            if total_weight > 0:
                weighted_value = sum(v * w for v, w in signal_list) / total_weight
                
                if trait == "openness":
                    self.openness_indicator = weighted_value
                elif trait == "extraversion":
                    self.extraversion_indicator = weighted_value
                elif trait == "neuroticism":
                    self.neuroticism_indicator = weighted_value
                elif trait == "need_for_cognition":
                    self.need_for_cognition_indicator = weighted_value
        
        # Calculate confidence based on domains available
        self.overall_confidence = min(0.9, len(self.domains_available) * 0.2 + 0.3)
    
    def to_features(self) -> Dict[str, float]:
        """
        Convert media profile to features compatible with BehavioralSession.
        
        These features can be merged into the main feature extraction pipeline.
        """
        features = {}
        
        # Music features
        if self.music:
            features["music_mellow"] = self.music.music_dimensions.mellow
            features["music_unpretentious"] = self.music.music_dimensions.unpretentious
            features["music_sophisticated"] = self.music.music_dimensions.sophisticated
            features["music_intense"] = self.music.music_dimensions.intense
            features["music_contemporary"] = self.music.music_dimensions.contemporary
            features["music_genre_diversity"] = self.music.genre_diversity
            features["music_hours_weekly"] = min(1.0, self.music.listening_hours_per_week / 40)
        
        # Podcast features
        if self.podcasts:
            features["podcast_true_crime"] = self.podcasts.true_crime_engagement
            features["podcast_news_politics"] = self.podcasts.news_politics_engagement
            features["podcast_educational"] = self.podcasts.educational_engagement
            features["podcast_completion_rate"] = self.podcasts.average_episode_completion
        
        # Film/TV features
        if self.film_tv:
            features["film_horror"] = self.film_tv.horror_preference
            features["film_documentary"] = self.film_tv.documentary_preference
            features["film_reality_tv"] = self.film_tv.reality_tv_preference
            features["film_binge_frequency"] = self.film_tv.binge_watching_frequency
        
        # Books features
        if self.books:
            features["book_fiction_preference"] = self.books.fiction_preference
            features["book_genre_diversity"] = self.books.genre_diversity
            features["book_volume"] = min(1.0, self.books.books_per_year / 20)
        
        # Aggregated personality indicators
        features["media_openness_indicator"] = self.openness_indicator
        features["media_extraversion_indicator"] = self.extraversion_indicator
        features["media_neuroticism_indicator"] = self.neuroticism_indicator
        features["media_morbid_curiosity"] = self.morbid_curiosity_indicator
        features["media_need_for_cognition"] = self.need_for_cognition_indicator
        
        return features
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "profile_id": self.profile_id,
            "user_id": self.user_id,
            "domains_available": self.domains_available,
            "personality_indicators": {
                "openness": self.openness_indicator,
                "extraversion": self.extraversion_indicator,
                "neuroticism": self.neuroticism_indicator,
                "morbid_curiosity": self.morbid_curiosity_indicator,
                "need_for_cognition": self.need_for_cognition_indicator,
            },
            "overall_confidence": self.overall_confidence,
            "features": self.to_features(),
        }
