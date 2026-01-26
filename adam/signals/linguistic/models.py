# =============================================================================
# ADAM Linguistic Signal Models
# Location: adam/signals/linguistic/models.py
# =============================================================================

"""
LINGUISTIC SIGNAL DATA MODELS

Pydantic models for linguistic analysis outputs.

Research Foundation:
- Pennebaker & King (1999): LIWC and personality
- Yarkoni (2010): Big Five and blog language
- Tausczik & Pennebaker (2010): LIWC psychological implications
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


# =============================================================================
# ENUMS
# =============================================================================

class LinguisticSignalType(str, Enum):
    """Types of linguistic signals extracted."""
    
    PERSONALITY = "personality"           # Big Five indicators
    REGULATORY_FOCUS = "regulatory_focus" # Promotion/prevention
    EMOTION = "emotion"                   # Valence/arousal
    COGNITION = "cognition"               # Complexity/style
    TEMPORAL = "temporal"                 # Past/present/future
    SOCIAL = "social"                     # Social reference patterns


class ProcessingState(str, Enum):
    """Cognitive processing state indicators."""
    
    ANALYTICAL = "analytical"     # Careful, systematic
    INTUITIVE = "intuitive"       # Fast, heuristic
    EMOTIONAL = "emotional"       # Affect-driven
    MIXED = "mixed"               # No clear dominance


# =============================================================================
# FEATURE MODELS
# =============================================================================

class LinguisticFeatures(BaseModel):
    """
    LIWC-style linguistic features extracted from text.
    
    Categories follow established psycholinguistic research.
    """
    
    # Word counts
    word_count: int = 0
    sentence_count: int = 0
    words_per_sentence: float = 0.0
    
    # Lexical sophistication
    word_length_avg: float = 0.0
    long_words_ratio: float = 0.0  # Words > 6 chars
    unique_words_ratio: float = 0.0  # Type-token ratio
    
    # Pronoun usage (psychological indicators)
    first_person_singular: float = 0.0  # I, me, my
    first_person_plural: float = 0.0    # We, us, our
    second_person: float = 0.0          # You, your
    third_person: float = 0.0           # He, she, they
    
    # Temporal markers
    past_focus: float = 0.0
    present_focus: float = 0.0
    future_focus: float = 0.0
    
    # Emotional content
    positive_emotion: float = 0.0
    negative_emotion: float = 0.0
    anxiety: float = 0.0
    anger: float = 0.0
    sadness: float = 0.0
    
    # Cognitive processes
    insight: float = 0.0      # Think, know, consider
    causation: float = 0.0    # Because, effect, hence
    discrepancy: float = 0.0  # Should, would, could
    tentative: float = 0.0    # Maybe, perhaps, guess
    certainty: float = 0.0    # Always, never, definitely
    
    # Social content
    social: float = 0.0       # Friend, talk, share
    family: float = 0.0
    friends: float = 0.0
    
    # Regulatory focus indicators
    achievement: float = 0.0  # Win, success, goal (promotion)
    risk: float = 0.0         # Danger, loss, fail (prevention)
    
    # Structural markers
    articles: float = 0.0     # The, a, an
    prepositions: float = 0.0
    conjunctions: float = 0.0
    negations: float = 0.0
    
    # Quality markers
    swear_words: float = 0.0
    filler_words: float = 0.0  # Like, um, uh
    
    # Metadata
    extraction_confidence: float = Field(default=0.8, ge=0.0, le=1.0)


class EmotionalValence(BaseModel):
    """Emotional content analysis."""
    
    valence: float = Field(default=0.0, ge=-1.0, le=1.0)  # Negative to positive
    arousal: float = Field(default=0.5, ge=0.0, le=1.0)   # Low to high activation
    dominance: float = Field(default=0.5, ge=0.0, le=1.0) # Submissive to dominant
    
    primary_emotion: Optional[str] = None
    emotion_intensity: float = 0.0
    
    confidence: float = Field(default=0.7, ge=0.0, le=1.0)


class TemporalMarkers(BaseModel):
    """Temporal orientation from text."""
    
    past_orientation: float = Field(default=0.33, ge=0.0, le=1.0)
    present_orientation: float = Field(default=0.34, ge=0.0, le=1.0)
    future_orientation: float = Field(default=0.33, ge=0.0, le=1.0)
    
    planning_language: float = 0.0      # Will, going to, plan
    reflection_language: float = 0.0    # Was, used to, back when
    immediacy_language: float = 0.0     # Now, right now, immediately
    
    dominant_orientation: str = "present"
    confidence: float = 0.7


# =============================================================================
# PROFILE MODELS
# =============================================================================

class InferredBigFive(BaseModel):
    """Big Five personality inferred from text."""
    
    openness: float = Field(default=0.5, ge=0.0, le=1.0)
    conscientiousness: float = Field(default=0.5, ge=0.0, le=1.0)
    extraversion: float = Field(default=0.5, ge=0.0, le=1.0)
    agreeableness: float = Field(default=0.5, ge=0.0, le=1.0)
    neuroticism: float = Field(default=0.5, ge=0.0, le=1.0)
    
    # Confidence per trait (linguistic signals have varying reliability)
    openness_confidence: float = 0.6
    conscientiousness_confidence: float = 0.5
    extraversion_confidence: float = 0.7
    agreeableness_confidence: float = 0.6
    neuroticism_confidence: float = 0.6
    
    overall_confidence: float = 0.6


class RegulatoryFocusSignal(BaseModel):
    """Regulatory focus inferred from language."""
    
    promotion_focus: float = Field(default=0.5, ge=0.0, le=1.0)
    prevention_focus: float = Field(default=0.5, ge=0.0, le=1.0)
    
    promotion_markers: List[str] = Field(default_factory=list)
    prevention_markers: List[str] = Field(default_factory=list)
    
    dominant_focus: str = "balanced"
    confidence: float = 0.65


class TextPsychologyProfile(BaseModel):
    """
    Complete psychological profile inferred from text.
    
    Combines all linguistic signals into actionable intelligence.
    """
    
    profile_id: str = Field(default_factory=lambda: f"txt_{uuid4().hex[:12]}")
    
    # Source
    source_text_hash: str = ""
    word_count: int = 0
    
    # Core profiles
    big_five: InferredBigFive = Field(default_factory=InferredBigFive)
    regulatory_focus: RegulatoryFocusSignal = Field(default_factory=RegulatoryFocusSignal)
    emotional_state: EmotionalValence = Field(default_factory=EmotionalValence)
    temporal_orientation: TemporalMarkers = Field(default_factory=TemporalMarkers)
    
    # Processing state
    processing_state: ProcessingState = ProcessingState.MIXED
    cognitive_complexity: float = 0.5  # Simple to complex language
    
    # Raw features for debugging
    raw_features: Optional[LinguisticFeatures] = None
    
    # Persuasion implications
    recommended_construal: str = "concrete"  # or "abstract"
    recommended_framing: str = "balanced"    # "gain", "loss", "balanced"
    
    # Confidence
    overall_confidence: float = 0.65
    
    # Metadata
    extracted_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# =============================================================================
# SIGNAL MODELS
# =============================================================================

class LinguisticSignal(BaseModel):
    """
    A linguistic signal for the learning system.
    
    Emitted when text is analyzed for psychological content.
    """
    
    signal_id: str = Field(default_factory=lambda: f"ling_{uuid4().hex[:12]}")
    signal_type: LinguisticSignalType
    
    # Source
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    source_type: str = "text"  # text, review, transcript
    
    # Profile
    profile: TextPsychologyProfile
    
    # Confidence
    confidence: float = Field(default=0.65, ge=0.0, le=1.0)
    
    # Learning
    affects_profile: bool = True
    profile_update_weight: float = 0.3  # How much to weight this signal
    
    # Metadata
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
