# =============================================================================
# ADAM iHeart Platform Integration
# =============================================================================

"""
iHeart Ad Network Integration

ADAM's primary learning interface with 175M+ audio listeners.

Key flows:
1. INBOUND: Listening patterns → psychological signals → profile enrichment
2. OUTBOUND: User profile → mechanism selection → ad decision → audio creative

Components:
- models/: Data models for stations, content, sessions, decisions
- services/: Content analysis, station learning, ad decision
- api/: FastAPI endpoints for iHeart integration
"""

from adam.platform.iheart.models.station import (
    Station,
    StationFormat,
    StationPsychProfile,
    STATION_FORMAT_PROFILES,
)
from adam.platform.iheart.models.content import (
    Track,
    Artist,
    AudioFeatures,
    Podcast,
    PodcastEpisode,
    Genre,
)
from adam.platform.iheart.models.session import (
    ListeningSession,
    ListeningEvent,
    ListeningEventType,
)
from adam.platform.iheart.models.advertising import (
    AdDecision,
    AdCreative,
    Campaign,
    AdOutcome,
    AdOutcomeType,
)
from adam.platform.iheart.service import iHeartAdService

__all__ = [
    # Service
    "iHeartAdService",
    # Station
    "Station",
    "StationFormat",
    "StationPsychProfile",
    "STATION_FORMAT_PROFILES",
    # Content
    "Track",
    "Artist",
    "AudioFeatures",
    "Podcast",
    "PodcastEpisode",
    "Genre",
    # Session
    "ListeningSession",
    "ListeningEvent",
    "ListeningEventType",
    # Advertising
    "AdDecision",
    "AdCreative",
    "Campaign",
    "AdOutcome",
    "AdOutcomeType",
]
