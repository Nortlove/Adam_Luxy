# =============================================================================
# ADAM Behavioral Analytics: Advertising Knowledge Models
# Location: adam/behavioral_analytics/models/advertising_knowledge.py
# =============================================================================

"""
ADVERTISING KNOWLEDGE MODELS

Models for representing research-validated consumer psychology and advertising
effectiveness knowledge from 25 years of peer-reviewed research.

This knowledge enables:
- Personality-based ad targeting (Big Five → ad response)
- Psychological state-aware messaging (regulatory focus, construal level)
- Message appeal optimization (fear, humor, narrative)
- Visual design optimization (color, whitespace, models)
- Media platform selection
- Interaction effect application (moderators)

Research Synthesis: 1999-2025
Key Meta-Analyses: Eisend & Tarrahi (2016), Tannenbaum et al. (2015),
Van Laer et al. (2014), Knoll & Matthes (2017)
"""

from typing import List, Dict, Optional, Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field
import uuid


# =============================================================================
# ENUMS
# =============================================================================

class PredictorCategory(str, Enum):
    """Category of the predictor variable."""
    PERSONALITY = "personality"           # Big Five, Dark Triad
    PSYCHOLOGICAL_STATE = "state"         # Mood, regulatory focus, construal
    INDIVIDUAL_DIFFERENCE = "individual"  # NFC, maximizing, impulsivity
    DEMOGRAPHICS = "demographics"         # Age, gender
    CULTURE = "culture"                   # Cultural values
    CONTEXT = "context"                   # Situation, environment


class AdElement(str, Enum):
    """Advertising element affected by the predictor."""
    APPEAL_TYPE = "appeal_type"           # Fear, humor, emotional
    MESSAGE_FRAME = "message_frame"       # Gain vs loss
    LANGUAGE_STYLE = "language_style"     # Concrete vs abstract
    CELEBRITY = "celebrity"               # Endorser characteristics
    VISUAL_DESIGN = "visual_design"       # Color, whitespace, imagery
    NARRATIVE = "narrative"               # Story structure
    MEDIA_PLATFORM = "media_platform"     # TV, social, native
    AD_FORMAT = "ad_format"               # Video length, placement
    CREATIVE_EXECUTION = "creative"       # Overall execution


class OutcomeMetric(str, Enum):
    """Advertising outcome metric."""
    AD_ATTITUDE = "ad_attitude"           # Aad
    BRAND_ATTITUDE = "brand_attitude"     # Ab
    PURCHASE_INTENT = "purchase_intent"   # PI
    BRAND_RECALL = "brand_recall"         # Memory
    AD_RECALL = "ad_recall"               # Ad memory
    CLICK_THROUGH = "ctr"                 # CTR
    CONVERSION = "conversion"             # CVR
    ENGAGEMENT = "engagement"             # Social engagement
    SOURCE_CREDIBILITY = "credibility"    # Perceived credibility
    PERSUASION = "persuasion"             # Attitude/behavior change


class EffectType(str, Enum):
    """Type of effect size metric."""
    CORRELATION = "correlation"           # Pearson r
    COHENS_D = "cohens_d"                # Cohen's d
    BETA = "beta"                         # Regression coefficient
    ODDS_RATIO = "odds_ratio"             # Odds ratio
    PERCENTAGE = "percentage"             # Percentage change
    META_R = "meta_r"                     # Meta-analytic correlation


class RobustnessTier(int, Enum):
    """Robustness tier based on evidence quality."""
    TIER_1_META_ANALYZED = 1              # Meta-analyzed, highest confidence
    TIER_2_REPLICATED = 2                 # Multiple replications
    TIER_3_SINGLE_STUDY = 3               # Single well-powered study


class InteractionType(str, Enum):
    """Type of interaction effect."""
    AMPLIFIES = "amplifies"               # Moderator strengthens effect
    ATTENUATES = "attenuates"             # Moderator weakens effect
    REVERSES = "reverses"                 # Moderator flips direction
    ENABLES = "enables"                   # Effect only occurs with moderator
    BOUNDARY = "boundary"                 # Moderator defines boundary condition


# =============================================================================
# RESEARCH SOURCE
# =============================================================================

class AdvertisingResearchSource(BaseModel):
    """A research study source for advertising knowledge."""
    
    source_id: str
    authors: str
    year: int
    title: str
    journal: Optional[str] = None
    
    # Study characteristics
    study_type: str = "experiment"  # experiment, meta-analysis, survey
    sample_size: Optional[int] = None
    num_studies: Optional[int] = None  # For meta-analyses
    num_effect_sizes: Optional[int] = None
    
    key_finding: str
    effect_reported: Optional[float] = None
    effect_type: Optional[str] = None


# =============================================================================
# ADVERTISING KNOWLEDGE
# =============================================================================

class AdvertisingKnowledge(BaseModel):
    """
    Research-validated advertising effectiveness knowledge.
    
    Represents a validated relationship between a psychological predictor
    (trait, state, or context) and advertising response, with effect size
    and implementation guidance.
    """
    
    knowledge_id: str = Field(
        default_factory=lambda: f"ak_{uuid.uuid4().hex[:12]}"
    )
    
    # Predictor (what predicts the outcome)
    predictor_category: PredictorCategory
    predictor_name: str  # e.g., "extraversion", "regulatory_focus"
    predictor_value: Optional[str] = None  # e.g., "high", "promotion"
    predictor_description: str = ""
    
    # Advertising element affected
    ad_element: AdElement
    element_specification: str  # e.g., "gain_frame", "social_appeal"
    element_description: str = ""
    
    # Outcome
    outcome_metric: OutcomeMetric
    outcome_direction: str  # "positive", "negative"
    outcome_description: str = ""
    
    # Effect metrics
    effect_size: float
    effect_type: EffectType
    confidence_interval_lower: Optional[float] = None
    confidence_interval_upper: Optional[float] = None
    p_value: Optional[float] = None
    
    # Evidence quality
    robustness_tier: RobustnessTier
    study_count: int = 1
    total_sample_size: int = 0
    sources: List[AdvertisingResearchSource] = Field(default_factory=list)
    
    # Implementation guidance
    implementation_notes: str = ""
    boundary_conditions: List[str] = Field(default_factory=list)
    contraindications: List[str] = Field(default_factory=list)
    
    # Mechanism mapping (links to ADAM's 9 mechanisms)
    related_mechanisms: List[str] = Field(default_factory=list)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    @property
    def is_meta_analyzed(self) -> bool:
        """Whether this finding is from meta-analysis."""
        return self.robustness_tier == RobustnessTier.TIER_1_META_ANALYZED
    
    @property
    def effect_magnitude(self) -> str:
        """Interpret effect size magnitude."""
        abs_effect = abs(self.effect_size)
        
        if self.effect_type in [EffectType.CORRELATION, EffectType.META_R]:
            if abs_effect >= 0.5:
                return "large"
            elif abs_effect >= 0.3:
                return "medium"
            elif abs_effect >= 0.1:
                return "small"
            else:
                return "trivial"
        elif self.effect_type == EffectType.COHENS_D:
            if abs_effect >= 0.8:
                return "large"
            elif abs_effect >= 0.5:
                return "medium"
            elif abs_effect >= 0.2:
                return "small"
            else:
                return "trivial"
        else:
            return "unknown"


class AdvertisingInteraction(BaseModel):
    """
    Interaction effect between two variables in advertising.
    
    Represents how a moderating variable changes the relationship
    between a predictor and outcome.
    """
    
    interaction_id: str = Field(
        default_factory=lambda: f"ai_{uuid.uuid4().hex[:12]}"
    )
    
    # Primary relationship
    primary_variable: str  # e.g., "celebrity_endorsement"
    primary_value: Optional[str] = None
    
    # Moderating variable
    moderating_variable: str  # e.g., "product_fit"
    moderating_value: Optional[str] = None
    
    # Interaction pattern
    interaction_type: InteractionType
    interaction_description: str
    
    # Conditional effects
    effect_when_moderator_present: float
    effect_when_moderator_absent: float
    effect_type: EffectType = EffectType.COHENS_D
    
    # Evidence
    robustness_tier: RobustnessTier = RobustnessTier.TIER_2_REPLICATED
    sources: List[AdvertisingResearchSource] = Field(default_factory=list)
    
    # Implementation
    implementation_notes: str = ""
    
    @property
    def effect_difference(self) -> float:
        """Difference in effect size based on moderator."""
        return self.effect_when_moderator_present - self.effect_when_moderator_absent


class MessageFrameRecommendation(BaseModel):
    """Recommendation for message framing based on psychological profile."""
    
    recommended_frame: str  # "gain", "loss", "mixed"
    frame_confidence: float = Field(ge=0.0, le=1.0)
    
    regulatory_focus_alignment: str  # "promotion", "prevention", "neutral"
    construal_level_alignment: str  # "abstract", "concrete", "adaptive"
    
    supporting_evidence: List[str] = Field(default_factory=list)
    contraindications: List[str] = Field(default_factory=list)
    
    # Specific recommendations
    headline_style: str = ""
    body_emphasis: str = ""
    cta_framing: str = ""


class CreativeElementRecommendation(BaseModel):
    """Recommendation for creative elements based on user profile."""
    
    user_id: str
    
    # Visual recommendations
    color_palette: str = ""
    whitespace_level: str = ""  # "high", "medium", "low"
    model_characteristics: str = ""
    
    # Message recommendations
    message_frame: MessageFrameRecommendation
    language_style: str = ""  # "concrete", "abstract"
    appeal_type: str = ""  # "emotional", "rational", "mixed"
    
    # Format recommendations
    optimal_video_length: Optional[int] = None
    narrative_structure: str = ""
    
    # Confidence and evidence
    overall_confidence: float = Field(ge=0.0, le=1.0)
    knowledge_items_applied: List[str] = Field(default_factory=list)


class EffectivenessPrediction(BaseModel):
    """Prediction of advertising effectiveness for a user-ad combination."""
    
    prediction_id: str = Field(
        default_factory=lambda: f"ep_{uuid.uuid4().hex[:12]}"
    )
    
    user_id: str
    ad_id: str
    
    # Predicted outcomes
    predicted_ad_attitude: float = Field(ge=0.0, le=1.0, default=0.5)
    predicted_brand_attitude: float = Field(ge=0.0, le=1.0, default=0.5)
    predicted_purchase_intent: float = Field(ge=0.0, le=1.0, default=0.5)
    predicted_engagement: float = Field(ge=0.0, le=1.0, default=0.5)
    
    # Overall effectiveness score
    effectiveness_score: float = Field(ge=0.0, le=1.0, default=0.5)
    
    # Confidence and explanation
    prediction_confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    knowledge_items_used: List[str] = Field(default_factory=list)
    
    # Key factors
    positive_factors: List[str] = Field(default_factory=list)
    negative_factors: List[str] = Field(default_factory=list)
    
    # Recommendations for improvement
    optimization_suggestions: List[str] = Field(default_factory=list)
    
    # Timestamp
    predicted_at: datetime = Field(default_factory=datetime.utcnow)


# =============================================================================
# KNOWLEDGE COLLECTIONS
# =============================================================================

class PersonalityAdKnowledge(BaseModel):
    """Collection of personality → ad response knowledge."""
    
    # Big Five mappings
    extraversion_effects: List[AdvertisingKnowledge] = Field(default_factory=list)
    openness_effects: List[AdvertisingKnowledge] = Field(default_factory=list)
    conscientiousness_effects: List[AdvertisingKnowledge] = Field(default_factory=list)
    neuroticism_effects: List[AdvertisingKnowledge] = Field(default_factory=list)
    agreeableness_effects: List[AdvertisingKnowledge] = Field(default_factory=list)
    
    # Extended traits
    need_for_cognition_effects: List[AdvertisingKnowledge] = Field(default_factory=list)
    self_monitoring_effects: List[AdvertisingKnowledge] = Field(default_factory=list)
    need_for_uniqueness_effects: List[AdvertisingKnowledge] = Field(default_factory=list)


class StateBasedKnowledge(BaseModel):
    """Collection of psychological state → ad response knowledge."""
    
    regulatory_focus_effects: List[AdvertisingKnowledge] = Field(default_factory=list)
    construal_level_effects: List[AdvertisingKnowledge] = Field(default_factory=list)
    mood_effects: List[AdvertisingKnowledge] = Field(default_factory=list)
    emotion_effects: List[AdvertisingKnowledge] = Field(default_factory=list)
    scarcity_effects: List[AdvertisingKnowledge] = Field(default_factory=list)


class MessageAppealKnowledge(BaseModel):
    """Collection of message appeal effectiveness knowledge."""
    
    fear_appeal_effects: List[AdvertisingKnowledge] = Field(default_factory=list)
    humor_effects: List[AdvertisingKnowledge] = Field(default_factory=list)
    narrative_effects: List[AdvertisingKnowledge] = Field(default_factory=list)
    framing_effects: List[AdvertisingKnowledge] = Field(default_factory=list)
    language_effects: List[AdvertisingKnowledge] = Field(default_factory=list)
