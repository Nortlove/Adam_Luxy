# =============================================================================
# ADAM Behavioral Analytics: Models
# =============================================================================

"""
Unified model exports for the behavioral analytics system.

This module exports all Pydantic models for:
- Mobile behavioral events (touch, swipe, scroll, sensors)
- Desktop behavioral events (cursor, keystroke)
- Media preferences (music, podcasts, books, film/TV)
- Cognitive mechanism models
- Knowledge and hypothesis models
"""

# Events - Mobile and Desktop
from adam.behavioral_analytics.models.events import (
    # Enums
    EventType,
    SignalDomain,
    CursorTrajectoryType,
    SwipeDirection,
    DeviceType,
    SessionPhase,
    OutcomeType,
    # Explicit events
    PageViewEvent,
    ClickEvent,
    CartEvent,
    PurchaseEvent,
    AdEvent,
    # Mobile implicit events
    TouchEvent,
    SwipeEvent,
    ScrollEvent,
    SensorSample,
    HesitationEvent,
    RageClickEvent,
    # Desktop implicit events
    CursorMoveEvent,
    CursorTrajectoryEvent,
    CursorHoverEvent,
    KeystrokeEvent,
    KeystrokeSequence,
    DesktopScrollEvent,
    # Session
    BehavioralSession,
    BehavioralOutcome,
)

# Knowledge
from adam.behavioral_analytics.models.knowledge import (
    BehavioralKnowledge,
    BehavioralHypothesis,
    KnowledgeValidationEvent,
    KnowledgeTier,
)

# Mechanisms
from adam.behavioral_analytics.models.mechanisms import (
    CognitiveMechanism,
    SignalSource,
    MechanismPolarity,
    MechanismEvidence,
    MechanismState,
    UserMechanismProfile,
    MECHANISM_SIGNAL_MAP,
    MECHANISM_POLARITY,
    # New models for Bayesian learning and discovery
    MechanismEffectiveness,
    MechanismActivation,
    MechanismInteraction,
    SupraliminalSignalProfile,
    BehavioralDiscovery,
)

# Advertising Knowledge
from adam.behavioral_analytics.models.advertising_knowledge import (
    # Enums
    PredictorCategory,
    AdElement,
    OutcomeMetric as AdOutcomeMetric,
    EffectType as AdEffectType,
    RobustnessTier,
    InteractionType,
    # Models
    AdvertisingResearchSource,
    AdvertisingKnowledge,
    AdvertisingInteraction,
    MessageFrameRecommendation,
    CreativeElementRecommendation,
    EffectivenessPrediction,
    PersonalityAdKnowledge,
    StateBasedKnowledge,
    MessageAppealKnowledge,
)

# Media Preferences
from adam.behavioral_analytics.models.media_preferences import (
    # Enums
    MusicGenre,
    PodcastGenre,
    BookGenre,
    FilmTVGenre,
    ListeningFrequency,
    # Music
    MUSICDimensions,
    MusicPreference,
    # Other media
    PodcastPreference,
    BookPreference,
    FilmTVPreference,
    # Unified profile
    MediaConsumptionProfile,
)

__all__ = [
    # Events - Enums
    "EventType",
    "SignalDomain",
    "CursorTrajectoryType",
    "SwipeDirection",
    "DeviceType",
    "SessionPhase",
    "OutcomeType",
    # Events - Explicit
    "PageViewEvent",
    "ClickEvent",
    "CartEvent",
    "PurchaseEvent",
    "AdEvent",
    # Events - Mobile
    "TouchEvent",
    "SwipeEvent",
    "ScrollEvent",
    "SensorSample",
    "HesitationEvent",
    "RageClickEvent",
    # Events - Desktop
    "CursorMoveEvent",
    "CursorTrajectoryEvent",
    "CursorHoverEvent",
    "KeystrokeEvent",
    "KeystrokeSequence",
    "DesktopScrollEvent",
    # Session
    "BehavioralSession",
    "BehavioralOutcome",
    # Knowledge
    "BehavioralKnowledge",
    "BehavioralHypothesis",
    "KnowledgeValidationEvent",
    "KnowledgeTier",
    # Mechanisms
    "CognitiveMechanism",
    "SignalSource",
    "MechanismPolarity",
    "MechanismEvidence",
    "MechanismState",
    "UserMechanismProfile",
    "MECHANISM_SIGNAL_MAP",
    "MECHANISM_POLARITY",
    # Mechanisms - Bayesian Learning
    "MechanismEffectiveness",
    "MechanismActivation",
    "MechanismInteraction",
    # Mechanisms - Desktop/Supraliminal
    "SupraliminalSignalProfile",
    # Discovery
    "BehavioralDiscovery",
    # Media - Enums
    "MusicGenre",
    "PodcastGenre",
    "BookGenre",
    "FilmTVGenre",
    "ListeningFrequency",
    # Media - Music
    "MUSICDimensions",
    "MusicPreference",
    # Media - Other
    "PodcastPreference",
    "BookPreference",
    "FilmTVPreference",
    # Media - Unified
    "MediaConsumptionProfile",
    # Advertising Knowledge - Enums
    "PredictorCategory",
    "AdElement",
    "AdOutcomeMetric",
    "AdEffectType",
    "RobustnessTier",
    "InteractionType",
    # Advertising Knowledge - Models
    "AdvertisingResearchSource",
    "AdvertisingKnowledge",
    "AdvertisingInteraction",
    "MessageFrameRecommendation",
    "CreativeElementRecommendation",
    "EffectivenessPrediction",
    "PersonalityAdKnowledge",
    "StateBasedKnowledge",
    "MessageAppealKnowledge",
]
