# =============================================================================
# ADAM API: Media Preference Collection
# Location: adam/api/behavioral/media_router.py
# =============================================================================

"""
MEDIA PREFERENCE COLLECTION API

FastAPI router for collecting and processing media preferences.

Media preferences predict personality traits:
- Music → Big Five (especially Openness, r=0.30-0.44)
- Podcasts → Morbid curiosity, need for cognition
- Books → Cognitive style
- Film/TV → Personality and sensation seeking

Endpoints:
- POST /music/preferences - Submit music preferences
- POST /podcast/preferences - Submit podcast preferences
- POST /book/preferences - Submit book preferences
- POST /film-tv/preferences - Submit film/TV preferences
- POST /profile/complete - Submit complete media profile
- GET /profile/{user_id} - Get user's media profile
- GET /profile/{user_id}/personality - Get inferred personality from media
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, Field
import logging

from adam.behavioral_analytics.models.media_preferences import (
    MusicGenre,
    PodcastGenre,
    BookGenre,
    FilmTVGenre,
    ListeningFrequency,
    MusicPreference,
    PodcastPreference,
    BookPreference,
    FilmTVPreference,
    MediaConsumptionProfile,
)
from adam.behavioral_analytics.engine import get_behavioral_analytics_engine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/behavioral/media", tags=["behavioral", "media"])


# =============================================================================
# REQUEST MODELS
# =============================================================================

class MusicPreferenceRequest(BaseModel):
    """Music preference submission."""
    user_id: str
    genres: List[str]  # Genre names or IDs
    listening_frequency: str = "weekly"
    listening_hours_per_week: float = 5.0
    
    # Optional platform connection
    spotify_user_id: Optional[str] = None
    apple_music_connected: bool = False


class PodcastPreferenceRequest(BaseModel):
    """Podcast preference submission."""
    user_id: str
    genres: List[str]
    listening_frequency: str = "weekly"
    average_episode_completion: float = Field(ge=0.0, le=1.0, default=0.7)
    
    # Specific preferences
    favorite_shows: List[str] = Field(default_factory=list)


class BookPreferenceRequest(BaseModel):
    """Book preference submission."""
    user_id: str
    genres: List[str]
    fiction_preference: float = Field(ge=0.0, le=1.0, default=0.5)
    books_per_year: int = Field(ge=0, default=0)
    
    # Specific preferences
    favorite_authors: List[str] = Field(default_factory=list)


class FilmTVPreferenceRequest(BaseModel):
    """Film/TV preference submission."""
    user_id: str
    genres: List[str]
    hours_per_week: float = 10.0
    binge_watching_frequency: float = Field(ge=0.0, le=1.0, default=0.3)
    
    # Platform info
    streaming_services: List[str] = Field(default_factory=list)


class CompleteMediaProfileRequest(BaseModel):
    """Complete media consumption profile."""
    user_id: str
    
    # All media types
    music_genres: List[str] = Field(default_factory=list)
    podcast_genres: List[str] = Field(default_factory=list)
    book_genres: List[str] = Field(default_factory=list)
    film_tv_genres: List[str] = Field(default_factory=list)
    
    # Consumption patterns
    music_hours_weekly: float = 5.0
    podcast_hours_weekly: float = 3.0
    book_pages_weekly: int = 50
    video_hours_weekly: float = 10.0


# =============================================================================
# USER PROFILE STORAGE
# =============================================================================

# In-memory storage (production would use database)
_user_profiles: Dict[str, MediaConsumptionProfile] = {}


def get_or_create_profile(user_id: str) -> MediaConsumptionProfile:
    """Get or create media profile for user."""
    if user_id not in _user_profiles:
        _user_profiles[user_id] = MediaConsumptionProfile(user_id=user_id)
    return _user_profiles[user_id]


def parse_music_genres(genre_names: List[str]) -> List[MusicGenre]:
    """Parse genre names to MusicGenre enum."""
    genres = []
    for name in genre_names:
        try:
            genres.append(MusicGenre(name.lower().replace(" ", "_")))
        except ValueError:
            # Try fuzzy matching
            for genre in MusicGenre:
                if name.lower() in genre.value:
                    genres.append(genre)
                    break
    return genres


def parse_podcast_genres(genre_names: List[str]) -> List[PodcastGenre]:
    """Parse genre names to PodcastGenre enum."""
    genres = []
    for name in genre_names:
        try:
            genres.append(PodcastGenre(name.lower().replace(" ", "_")))
        except ValueError:
            for genre in PodcastGenre:
                if name.lower() in genre.value:
                    genres.append(genre)
                    break
    return genres


def parse_book_genres(genre_names: List[str]) -> List[BookGenre]:
    """Parse genre names to BookGenre enum."""
    genres = []
    for name in genre_names:
        try:
            genres.append(BookGenre(name.lower().replace(" ", "_")))
        except ValueError:
            for genre in BookGenre:
                if name.lower() in genre.value:
                    genres.append(genre)
                    break
    return genres


def parse_film_genres(genre_names: List[str]) -> List[FilmTVGenre]:
    """Parse genre names to FilmTVGenre enum."""
    genres = []
    for name in genre_names:
        try:
            genres.append(FilmTVGenre(name.lower().replace(" ", "_")))
        except ValueError:
            for genre in FilmTVGenre:
                if name.lower() in genre.value:
                    genres.append(genre)
                    break
    return genres


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.post("/music/preferences")
async def submit_music_preferences(
    request: MusicPreferenceRequest,
) -> Dict[str, Any]:
    """
    Submit music preferences.
    
    Music preferences are strong predictors of Openness to Experience.
    The MUSIC model dimensions are derived from genre preferences.
    """
    profile = get_or_create_profile(request.user_id)
    
    # Parse genres
    genres = parse_music_genres(request.genres)
    
    # Create/update music preference
    music_pref = MusicPreference(
        genres=genres,
        listening_frequency=ListeningFrequency(request.listening_frequency.lower()),
        listening_hours_per_week=request.listening_hours_per_week,
        spotify_connected=bool(request.spotify_user_id),
        apple_music_connected=request.apple_music_connected,
        genre_diversity=len(set(genres)) / max(len(genres), 1) if genres else 0.5,
    )
    
    # Derive MUSIC dimensions
    music_pref.derive_music_dimensions()
    
    profile.music = music_pref
    profile.derive_personality_indicators()
    
    logger.info(
        f"Updated music preferences for {request.user_id}: "
        f"{len(genres)} genres, "
        f"dominant={music_pref.music_dimensions.get_dominant_dimension()}"
    )
    
    return {
        "user_id": request.user_id,
        "genres_parsed": len(genres),
        "music_dimensions": {
            "mellow": music_pref.music_dimensions.mellow,
            "unpretentious": music_pref.music_dimensions.unpretentious,
            "sophisticated": music_pref.music_dimensions.sophisticated,
            "intense": music_pref.music_dimensions.intense,
            "contemporary": music_pref.music_dimensions.contemporary,
        },
        "dominant_dimension": music_pref.music_dimensions.get_dominant_dimension(),
    }


@router.post("/podcast/preferences")
async def submit_podcast_preferences(
    request: PodcastPreferenceRequest,
) -> Dict[str, Any]:
    """
    Submit podcast preferences.
    
    Podcast preferences indicate:
    - True crime → Morbid curiosity (sr=0.51)
    - News/politics → Social belonging need
    - Educational → Need for cognition
    """
    profile = get_or_create_profile(request.user_id)
    
    genres = parse_podcast_genres(request.genres)
    
    podcast_pref = PodcastPreference(
        genres=genres,
        listening_frequency=ListeningFrequency(request.listening_frequency.lower()),
        average_episode_completion=request.average_episode_completion,
    )
    
    podcast_pref.derive_engagement_scores()
    
    profile.podcasts = podcast_pref
    profile.derive_personality_indicators()
    
    logger.info(
        f"Updated podcast preferences for {request.user_id}: "
        f"{len(genres)} genres"
    )
    
    return {
        "user_id": request.user_id,
        "genres_parsed": len(genres),
        "true_crime_engagement": podcast_pref.true_crime_engagement,
        "news_politics_engagement": podcast_pref.news_politics_engagement,
        "educational_engagement": podcast_pref.educational_engagement,
        "morbid_curiosity_indicator": profile.morbid_curiosity_indicator,
    }


@router.post("/book/preferences")
async def submit_book_preferences(
    request: BookPreferenceRequest,
) -> Dict[str, Any]:
    """
    Submit book preferences.
    
    Reading patterns indicate cognitive style and Openness.
    """
    profile = get_or_create_profile(request.user_id)
    
    genres = parse_book_genres(request.genres)
    
    book_pref = BookPreference(
        genres=genres,
        fiction_preference=request.fiction_preference,
        books_per_year=request.books_per_year,
        genre_diversity=len(set(genres)) / max(len(genres), 1) if genres else 0.5,
    )
    
    profile.books = book_pref
    profile.derive_personality_indicators()
    
    return {
        "user_id": request.user_id,
        "genres_parsed": len(genres),
        "fiction_preference": request.fiction_preference,
        "reading_volume": min(1.0, request.books_per_year / 20),
    }


@router.post("/film-tv/preferences")
async def submit_film_tv_preferences(
    request: FilmTVPreferenceRequest,
) -> Dict[str, Any]:
    """
    Submit film/TV preferences.
    
    Film preferences indicate:
    - Horror → Sensation seeking
    - Documentary → Openness
    - Reality TV → Social comparison tendency
    """
    profile = get_or_create_profile(request.user_id)
    
    genres = parse_film_genres(request.genres)
    
    film_pref = FilmTVPreference(
        genres=genres,
        hours_per_week=request.hours_per_week,
        binge_watching_frequency=request.binge_watching_frequency,
    )
    
    film_pref.derive_preference_scores()
    
    profile.film_tv = film_pref
    profile.derive_personality_indicators()
    
    return {
        "user_id": request.user_id,
        "genres_parsed": len(genres),
        "horror_preference": film_pref.horror_preference,
        "documentary_preference": film_pref.documentary_preference,
        "reality_tv_preference": film_pref.reality_tv_preference,
    }


@router.post("/profile/complete")
async def submit_complete_profile(
    request: CompleteMediaProfileRequest,
    background_tasks: BackgroundTasks,
) -> Dict[str, Any]:
    """
    Submit complete media consumption profile.
    
    All media preferences at once for comprehensive personality inference.
    """
    profile = get_or_create_profile(request.user_id)
    
    # Music
    if request.music_genres:
        music_genres = parse_music_genres(request.music_genres)
        music_pref = MusicPreference(
            genres=music_genres,
            listening_hours_per_week=request.music_hours_weekly,
        )
        music_pref.derive_music_dimensions()
        profile.music = music_pref
    
    # Podcasts
    if request.podcast_genres:
        podcast_genres = parse_podcast_genres(request.podcast_genres)
        podcast_pref = PodcastPreference(genres=podcast_genres)
        podcast_pref.derive_engagement_scores()
        profile.podcasts = podcast_pref
    
    # Books
    if request.book_genres:
        book_genres = parse_book_genres(request.book_genres)
        profile.books = BookPreference(
            genres=book_genres,
            books_per_year=int(request.book_pages_weekly * 52 / 300),  # ~300 pages/book
        )
    
    # Film/TV
    if request.film_tv_genres:
        film_genres = parse_film_genres(request.film_tv_genres)
        film_pref = FilmTVPreference(
            genres=film_genres,
            hours_per_week=request.video_hours_weekly,
        )
        film_pref.derive_preference_scores()
        profile.film_tv = film_pref
    
    # Derive personality
    profile.derive_personality_indicators()
    
    logger.info(
        f"Complete media profile for {request.user_id}: "
        f"{len(profile.domains_available)} domains, "
        f"confidence={profile.overall_confidence:.2f}"
    )
    
    return {
        "user_id": request.user_id,
        "domains_available": profile.domains_available,
        "personality_indicators": {
            "openness": profile.openness_indicator,
            "extraversion": profile.extraversion_indicator,
            "neuroticism": profile.neuroticism_indicator,
            "morbid_curiosity": profile.morbid_curiosity_indicator,
            "need_for_cognition": profile.need_for_cognition_indicator,
        },
        "overall_confidence": profile.overall_confidence,
    }


@router.get("/profile/{user_id}")
async def get_media_profile(user_id: str) -> Dict[str, Any]:
    """Get user's complete media consumption profile."""
    if user_id not in _user_profiles:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    profile = _user_profiles[user_id]
    return profile.to_dict()


@router.get("/profile/{user_id}/personality")
async def get_personality_from_media(user_id: str) -> Dict[str, Any]:
    """
    Get inferred personality traits from media preferences.
    
    Returns Big Five indicators derived from all media preferences.
    """
    if user_id not in _user_profiles:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    profile = _user_profiles[user_id]
    profile.derive_personality_indicators()
    
    return {
        "user_id": user_id,
        "personality_indicators": {
            "openness": {
                "value": profile.openness_indicator,
                "confidence": profile.overall_confidence,
                "sources": profile.domains_available,
            },
            "extraversion": {
                "value": profile.extraversion_indicator,
                "confidence": profile.overall_confidence * 0.8,  # Less confident
            },
            "neuroticism": {
                "value": profile.neuroticism_indicator,
                "confidence": profile.overall_confidence * 0.6,  # Least confident
            },
        },
        "derived_traits": {
            "morbid_curiosity": profile.morbid_curiosity_indicator,
            "need_for_cognition": profile.need_for_cognition_indicator,
        },
        "domains_used": profile.domains_available,
        "overall_confidence": profile.overall_confidence,
    }


@router.get("/profile/{user_id}/features")
async def get_media_features(user_id: str) -> Dict[str, float]:
    """
    Get media features compatible with behavioral session.
    
    These features can be merged into the main feature extraction
    pipeline for mechanism inference.
    """
    if user_id not in _user_profiles:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    profile = _user_profiles[user_id]
    return profile.to_features()
