# =============================================================================
# ADAM Behavioral Analytics: Cognitive Mechanism Models
# Location: adam/behavioral_analytics/models/mechanisms.py
# =============================================================================

"""
COGNITIVE MECHANISM MODELS

This module defines the mapping between behavioral signals and ADAM's
9 cognitive mechanisms. Every behavioral signal (mobile, desktop, media)
contributes evidence to one or more mechanisms.

The 9 Mechanisms (from ADAM_CTO_PERSONA.md):
1. Construal Level - Abstract vs concrete thinking
2. Regulatory Focus - Gains vs losses orientation
3. Automatic Evaluation - Pre-conscious approach/avoid
4. Wanting-Liking Dissociation - Desire ≠ enjoyment
5. Mimetic Desire - We want what others want
6. Attention Dynamics - Novelty and salience capture
7. Temporal Construal - Future vs present self
8. Identity Construction - Self-concept alignment
9. Evolutionary Adaptations - Primal psychological triggers

These mechanisms explain WHY people convert, not just THAT they convert.
This is ADAM's competitive moat.
"""

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field
import uuid


# =============================================================================
# COGNITIVE MECHANISM ENUM
# =============================================================================

class CognitiveMechanism(str, Enum):
    """
    ADAM's 9 cognitive mechanisms.
    
    These are the psychological drivers that explain WHY users
    make decisions. Each mechanism can be activated or suppressed
    based on behavioral signals and context.
    """
    # Abstract vs Concrete Thinking
    CONSTRUAL_LEVEL = "construal_level"
    
    # Gains vs Losses Orientation
    REGULATORY_FOCUS = "regulatory_focus"
    
    # Pre-conscious Approach/Avoid
    AUTOMATIC_EVALUATION = "automatic_evaluation"
    
    # Desire ≠ Enjoyment
    WANTING_LIKING = "wanting_liking"
    
    # We Want What Others Want
    MIMETIC_DESIRE = "mimetic_desire"
    
    # Novelty and Salience Capture
    ATTENTION_DYNAMICS = "attention_dynamics"
    
    # Future vs Present Self
    TEMPORAL_CONSTRUAL = "temporal_construal"
    
    # Self-concept Alignment
    IDENTITY_CONSTRUCTION = "identity_construction"
    
    # Primal Psychological Triggers
    EVOLUTIONARY_ADAPTATIONS = "evolutionary_adaptations"


class SignalSource(str, Enum):
    """Source of behavioral signal contributing to mechanism evidence."""
    # Mobile
    TOUCH_PRESSURE = "touch_pressure"
    TOUCH_DURATION = "touch_duration"
    SWIPE_DIRECTION = "swipe_direction"
    SWIPE_VELOCITY = "swipe_velocity"
    SWIPE_DIRECTNESS = "swipe_directness"
    SCROLL_DEPTH = "scroll_depth"
    SCROLL_VELOCITY = "scroll_velocity"
    SCROLL_REVERSAL = "scroll_reversal"
    ACCELEROMETER = "accelerometer"
    GYROSCOPE = "gyroscope"
    RESPONSE_LATENCY = "response_latency"
    HESITATION = "hesitation"
    RAGE_CLICK = "rage_click"
    
    # Desktop
    CURSOR_TRAJECTORY = "cursor_trajectory"
    CURSOR_INITIATION = "cursor_initiation"
    CURSOR_VELOCITY = "cursor_velocity"
    CURSOR_HOVER = "cursor_hover"
    CURSOR_X_FLIPS = "cursor_x_flips"
    KEYSTROKE_HOLD = "keystroke_hold"
    KEYSTROKE_FLIGHT = "keystroke_flight"
    KEYSTROKE_RHYTHM = "keystroke_rhythm"
    KEYSTROKE_ERRORS = "keystroke_errors"
    DESKTOP_SCROLL = "desktop_scroll"
    
    # Media Preferences
    MUSIC_PREFERENCE = "music_preference"
    PODCAST_PREFERENCE = "podcast_preference"
    BOOK_PREFERENCE = "book_preference"
    FILM_PREFERENCE = "film_preference"
    
    # Explicit Behavior
    DWELL_TIME = "dwell_time"
    CART_BEHAVIOR = "cart_behavior"
    PRICE_SENSITIVITY = "price_sensitivity"
    SOCIAL_PROOF_ENGAGEMENT = "social_proof_engagement"
    CATEGORY_EXPLORATION = "category_exploration"


class MechanismPolarity(str, Enum):
    """
    Polarity of mechanism inference.
    
    Some mechanisms have two poles (e.g., promotion vs prevention).
    Others are unipolar (e.g., mimetic susceptibility is 0-1).
    """
    BIPOLAR = "bipolar"  # -1 to 1 scale
    UNIPOLAR = "unipolar"  # 0 to 1 scale


# =============================================================================
# MECHANISM EVIDENCE MODELS
# =============================================================================

class MechanismEvidence(BaseModel):
    """
    Evidence for a cognitive mechanism from a behavioral signal.
    
    This represents a single signal's contribution to mechanism inference.
    Multiple evidence items are combined to produce the final mechanism state.
    """
    evidence_id: str = Field(default_factory=lambda: f"me_{uuid.uuid4().hex[:12]}")
    
    # What mechanism this evidence supports
    mechanism: CognitiveMechanism
    
    # What signal provided this evidence
    signal_source: SignalSource
    feature_name: str  # The specific feature (e.g., "trajectory_auc_mean")
    feature_value: float  # The observed value
    
    # Evidence strength and direction
    evidence_strength: float = Field(ge=0.0, le=1.0)
    evidence_direction: float = Field(ge=-1.0, le=1.0)
    # For bipolar mechanisms: -1 = one pole, +1 = opposite pole
    # For unipolar: 0 to 1
    
    # Research backing
    effect_size: float = 0.0  # Research effect size (Cohen's d or r)
    research_source: Optional[str] = None
    
    # Confidence in this evidence
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    
    # Timing
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        use_enum_values = True


class MechanismState(BaseModel):
    """
    Inferred state of a single mechanism for a user.
    
    Combines all evidence for this mechanism into a single state.
    """
    mechanism: CognitiveMechanism
    polarity: MechanismPolarity
    
    # Inferred value
    # Bipolar: -1 (one extreme) to 1 (opposite extreme), 0 = neutral
    # Unipolar: 0 (absent) to 1 (fully activated)
    value: float = 0.0
    
    # Confidence in the inference
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    
    # Evidence that contributed to this state
    evidence_count: int = 0
    evidence_sources: List[SignalSource] = Field(default_factory=list)
    
    # For bipolar mechanisms, which pole is dominant
    dominant_pole: Optional[str] = None
    
    # Recommended messaging approach
    messaging_implication: Optional[str] = None
    
    class Config:
        use_enum_values = True


# =============================================================================
# USER MECHANISM PROFILE
# =============================================================================

class UserMechanismProfile(BaseModel):
    """
    Complete mechanism profile for a user session.
    
    This is the unified output that maps all behavioral signals
    (mobile, desktop, media) to the 9 cognitive mechanisms.
    
    Used by atoms for mechanism selection and message framing.
    """
    profile_id: str = Field(default_factory=lambda: f"mp_{uuid.uuid4().hex[:12]}")
    user_id: Optional[str] = None
    session_id: str
    
    # Timestamp
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # =========================================================================
    # THE 9 MECHANISMS
    # =========================================================================
    
    # 1. Construal Level: -1 = concrete, +1 = abstract
    construal_level: float = Field(
        default=0.0, ge=-1.0, le=1.0,
        description="-1=concrete (how), +1=abstract (why)"
    )
    construal_level_confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    
    # 2. Regulatory Focus: -1 = prevention, +1 = promotion
    regulatory_focus: float = Field(
        default=0.0, ge=-1.0, le=1.0,
        description="-1=prevention (avoid loss), +1=promotion (achieve gain)"
    )
    regulatory_focus_confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    
    # 3. Automatic Evaluation: -1 = avoid, +1 = approach
    automatic_evaluation: float = Field(
        default=0.0, ge=-1.0, le=1.0,
        description="-1=automatic avoidance, +1=automatic approach"
    )
    automatic_evaluation_confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    
    # 4. Wanting-Liking Gap: 0 = aligned, 1 = highly dissociated
    wanting_liking_gap: float = Field(
        default=0.0, ge=0.0, le=1.0,
        description="0=want what they like, 1=want but don't like"
    )
    wanting_liking_confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    
    # 5. Mimetic Susceptibility: 0 = low, 1 = high
    mimetic_susceptibility: float = Field(
        default=0.5, ge=0.0, le=1.0,
        description="0=immune to social proof, 1=highly influenced"
    )
    mimetic_susceptibility_confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    
    # 6. Attention Engagement: 0 = low, 1 = high
    attention_engagement: float = Field(
        default=0.5, ge=0.0, le=1.0,
        description="0=distracted, 1=deeply engaged"
    )
    attention_engagement_confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    
    # 7. Temporal Orientation: -1 = present, +1 = future
    temporal_orientation: float = Field(
        default=0.0, ge=-1.0, le=1.0,
        description="-1=present-focused, +1=future-focused"
    )
    temporal_orientation_confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    
    # 8. Identity Activation: 0 = low, 1 = high
    identity_activation: float = Field(
        default=0.5, ge=0.0, le=1.0,
        description="0=functional evaluation, 1=identity-driven"
    )
    identity_activation_confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    
    # 9. Evolutionary Sensitivity: 0 = low, 1 = high
    evolutionary_sensitivity: float = Field(
        default=0.5, ge=0.0, le=1.0,
        description="0=immune to primal triggers, 1=highly responsive"
    )
    evolutionary_sensitivity_confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    
    # =========================================================================
    # EVIDENCE TRACKING
    # =========================================================================
    
    # All evidence that contributed to this profile
    evidence_by_mechanism: Dict[str, List[MechanismEvidence]] = Field(
        default_factory=dict
    )
    
    # Signal sources used
    signal_sources_used: List[SignalSource] = Field(default_factory=list)
    signal_domains: List[str] = Field(default_factory=list)  # mobile, desktop, media
    
    # Overall confidence (weighted by mechanism confidences)
    overall_confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    
    # Total evidence count
    total_evidence_count: int = 0
    
    # =========================================================================
    # METHODS
    # =========================================================================
    
    def get_mechanism_state(self, mechanism: CognitiveMechanism) -> MechanismState:
        """Get the state of a specific mechanism."""
        mechanism_map = {
            CognitiveMechanism.CONSTRUAL_LEVEL: (
                self.construal_level, 
                self.construal_level_confidence,
                MechanismPolarity.BIPOLAR,
                "concrete" if self.construal_level < 0 else "abstract"
            ),
            CognitiveMechanism.REGULATORY_FOCUS: (
                self.regulatory_focus,
                self.regulatory_focus_confidence,
                MechanismPolarity.BIPOLAR,
                "prevention" if self.regulatory_focus < 0 else "promotion"
            ),
            CognitiveMechanism.AUTOMATIC_EVALUATION: (
                self.automatic_evaluation,
                self.automatic_evaluation_confidence,
                MechanismPolarity.BIPOLAR,
                "avoid" if self.automatic_evaluation < 0 else "approach"
            ),
            CognitiveMechanism.WANTING_LIKING: (
                self.wanting_liking_gap,
                self.wanting_liking_confidence,
                MechanismPolarity.UNIPOLAR,
                None
            ),
            CognitiveMechanism.MIMETIC_DESIRE: (
                self.mimetic_susceptibility,
                self.mimetic_susceptibility_confidence,
                MechanismPolarity.UNIPOLAR,
                None
            ),
            CognitiveMechanism.ATTENTION_DYNAMICS: (
                self.attention_engagement,
                self.attention_engagement_confidence,
                MechanismPolarity.UNIPOLAR,
                None
            ),
            CognitiveMechanism.TEMPORAL_CONSTRUAL: (
                self.temporal_orientation,
                self.temporal_orientation_confidence,
                MechanismPolarity.BIPOLAR,
                "present" if self.temporal_orientation < 0 else "future"
            ),
            CognitiveMechanism.IDENTITY_CONSTRUCTION: (
                self.identity_activation,
                self.identity_activation_confidence,
                MechanismPolarity.UNIPOLAR,
                None
            ),
            CognitiveMechanism.EVOLUTIONARY_ADAPTATIONS: (
                self.evolutionary_sensitivity,
                self.evolutionary_sensitivity_confidence,
                MechanismPolarity.UNIPOLAR,
                None
            ),
        }
        
        value, confidence, polarity, pole = mechanism_map[mechanism]
        evidence = self.evidence_by_mechanism.get(mechanism.value, [])
        
        return MechanismState(
            mechanism=mechanism,
            polarity=polarity,
            value=value,
            confidence=confidence,
            evidence_count=len(evidence),
            evidence_sources=[e.signal_source for e in evidence],
            dominant_pole=pole,
        )
    
    def get_dominant_mechanisms(
        self, 
        threshold: float = 0.6,
        min_confidence: float = 0.5,
    ) -> List[Tuple[CognitiveMechanism, float]]:
        """
        Get mechanisms with strong activation above threshold.
        
        For bipolar mechanisms, uses absolute value.
        Returns list of (mechanism, strength) tuples sorted by strength.
        """
        dominant = []
        
        mechanism_values = [
            (CognitiveMechanism.CONSTRUAL_LEVEL, abs(self.construal_level), self.construal_level_confidence),
            (CognitiveMechanism.REGULATORY_FOCUS, abs(self.regulatory_focus), self.regulatory_focus_confidence),
            (CognitiveMechanism.AUTOMATIC_EVALUATION, abs(self.automatic_evaluation), self.automatic_evaluation_confidence),
            (CognitiveMechanism.WANTING_LIKING, self.wanting_liking_gap, self.wanting_liking_confidence),
            (CognitiveMechanism.MIMETIC_DESIRE, self.mimetic_susceptibility, self.mimetic_susceptibility_confidence),
            (CognitiveMechanism.ATTENTION_DYNAMICS, self.attention_engagement, self.attention_engagement_confidence),
            (CognitiveMechanism.TEMPORAL_CONSTRUAL, abs(self.temporal_orientation), self.temporal_orientation_confidence),
            (CognitiveMechanism.IDENTITY_CONSTRUCTION, self.identity_activation, self.identity_activation_confidence),
            (CognitiveMechanism.EVOLUTIONARY_ADAPTATIONS, self.evolutionary_sensitivity, self.evolutionary_sensitivity_confidence),
        ]
        
        for mechanism, strength, confidence in mechanism_values:
            if strength >= threshold and confidence >= min_confidence:
                dominant.append((mechanism, strength))
        
        # Sort by strength descending
        dominant.sort(key=lambda x: x[1], reverse=True)
        return dominant
    
    def get_messaging_recommendations(self) -> Dict[str, Any]:
        """
        Get messaging recommendations based on mechanism profile.
        
        This is what atoms use to select mechanism-aligned messaging.
        """
        recommendations = {}
        
        # Construal Level
        if abs(self.construal_level) > 0.3:
            if self.construal_level > 0:
                recommendations["framing"] = "abstract_why"
                recommendations["construal_message"] = "Focus on values, identity, purpose"
            else:
                recommendations["framing"] = "concrete_how"
                recommendations["construal_message"] = "Focus on features, steps, details"
        
        # Regulatory Focus
        if abs(self.regulatory_focus) > 0.3:
            if self.regulatory_focus > 0:
                recommendations["focus"] = "promotion"
                recommendations["focus_message"] = "Frame as gains, achievements, aspirations"
            else:
                recommendations["focus"] = "prevention"
                recommendations["focus_message"] = "Frame as protection, security, avoiding loss"
        
        # Automatic Evaluation
        if abs(self.automatic_evaluation) > 0.3:
            if self.automatic_evaluation > 0:
                recommendations["friction"] = "reduce"
                recommendations["evaluation_message"] = "Positive automatic response - minimize obstacles"
            else:
                recommendations["friction"] = "add_reassurance"
                recommendations["evaluation_message"] = "Negative automatic response - add trust signals"
        
        # Mimetic Desire
        if self.mimetic_susceptibility > 0.6:
            recommendations["social_proof"] = "prominent"
            recommendations["mimetic_message"] = "Emphasize what others are doing"
        elif self.mimetic_susceptibility < 0.3:
            recommendations["social_proof"] = "minimal"
            recommendations["mimetic_message"] = "Focus on individual benefits, not social proof"
        
        # Attention
        if self.attention_engagement < 0.4:
            recommendations["attention"] = "capture"
            recommendations["attention_message"] = "Use novelty, movement, urgency to capture attention"
        else:
            recommendations["attention"] = "maintain"
            recommendations["attention_message"] = "Attention is high - deliver value, don't distract"
        
        # Temporal
        if abs(self.temporal_orientation) > 0.3:
            if self.temporal_orientation > 0:
                recommendations["temporal"] = "future"
                recommendations["temporal_message"] = "Emphasize long-term benefits, investment"
            else:
                recommendations["temporal"] = "present"
                recommendations["temporal_message"] = "Emphasize immediate gratification, urgency"
        
        # Identity
        if self.identity_activation > 0.6:
            recommendations["identity"] = "activated"
            recommendations["identity_message"] = "Connect product to self-concept, values"
        
        # Evolutionary
        if self.evolutionary_sensitivity > 0.6:
            recommendations["evolutionary"] = "responsive"
            recommendations["evolutionary_message"] = "Safe to use scarcity, social proof, authority"
        
        return recommendations
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "profile_id": self.profile_id,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "created_at": self.created_at.isoformat(),
            # Mechanism values
            "construal_level": self.construal_level,
            "regulatory_focus": self.regulatory_focus,
            "automatic_evaluation": self.automatic_evaluation,
            "wanting_liking_gap": self.wanting_liking_gap,
            "mimetic_susceptibility": self.mimetic_susceptibility,
            "attention_engagement": self.attention_engagement,
            "temporal_orientation": self.temporal_orientation,
            "identity_activation": self.identity_activation,
            "evolutionary_sensitivity": self.evolutionary_sensitivity,
            # Confidence values
            "confidences": {
                "construal_level": self.construal_level_confidence,
                "regulatory_focus": self.regulatory_focus_confidence,
                "automatic_evaluation": self.automatic_evaluation_confidence,
                "wanting_liking": self.wanting_liking_confidence,
                "mimetic": self.mimetic_susceptibility_confidence,
                "attention": self.attention_engagement_confidence,
                "temporal": self.temporal_orientation_confidence,
                "identity": self.identity_activation_confidence,
                "evolutionary": self.evolutionary_sensitivity_confidence,
            },
            # Summary
            "overall_confidence": self.overall_confidence,
            "total_evidence_count": self.total_evidence_count,
            "signal_domains": self.signal_domains,
            "dominant_mechanisms": [
                {"mechanism": m.value, "strength": s}
                for m, s in self.get_dominant_mechanisms()
            ],
            "recommendations": self.get_messaging_recommendations(),
        }


# =============================================================================
# MECHANISM-SIGNAL MAPPINGS
# =============================================================================

# This defines which signals map to which mechanisms with what effect sizes
# Used by the engine to build mechanism profiles from features

MECHANISM_SIGNAL_MAP: Dict[CognitiveMechanism, List[Dict[str, Any]]] = {
    CognitiveMechanism.CONSTRUAL_LEVEL: [
        # Abstract indicators
        {"signal": SignalSource.SCROLL_DEPTH, "feature": "max_depth", "direction": 1, "effect_size": 0.25, "threshold_high": 0.8},
        {"signal": SignalSource.CATEGORY_EXPLORATION, "feature": "category_breadth", "direction": 1, "effect_size": 0.30},
        {"signal": SignalSource.RESPONSE_LATENCY, "feature": "response_latency_mean", "direction": 1, "effect_size": 0.35, "threshold_low": 2000},
        # Concrete indicators
        {"signal": SignalSource.SCROLL_VELOCITY, "feature": "scroll_velocity_mean", "direction": -1, "effect_size": 0.20, "threshold_high": 500},
        {"signal": SignalSource.SWIPE_VELOCITY, "feature": "velocity_mean", "direction": -1, "effect_size": 0.25, "threshold_high": 800},
    ],
    CognitiveMechanism.REGULATORY_FOCUS: [
        # Promotion indicators
        {"signal": SignalSource.SWIPE_DIRECTION, "feature": "right_swipe_ratio", "direction": 1, "effect_size": 0.35},
        {"signal": SignalSource.CURSOR_TRAJECTORY, "feature": "trajectory_conflict_mean", "direction": -1, "effect_size": 0.40},
        {"signal": SignalSource.CURSOR_INITIATION, "feature": "trajectory_initiation_mean", "direction": -1, "effect_size": 0.48, "threshold_low": 400},
        # Prevention indicators
        {"signal": SignalSource.HESITATION, "feature": "hesitation_count", "direction": -1, "effect_size": 0.40, "threshold_high": 3},
        {"signal": SignalSource.SCROLL_REVERSAL, "feature": "reversal_ratio", "direction": -1, "effect_size": 0.30, "threshold_high": 0.3},
    ],
    CognitiveMechanism.AUTOMATIC_EVALUATION: [
        # Approach indicators
        {"signal": SignalSource.RESPONSE_LATENCY, "feature": "response_latency_mean", "direction": 1, "effect_size": 0.50, "threshold_low": 600},
        {"signal": SignalSource.TOUCH_PRESSURE, "feature": "pressure_mean", "direction": 1, "effect_size": 0.45, "invert": True},
        {"signal": SignalSource.CURSOR_INITIATION, "feature": "trajectory_initiation_mean", "direction": 1, "effect_size": 0.48, "threshold_low": 400},
        # Avoid indicators
        {"signal": SignalSource.SWIPE_DIRECTION, "feature": "right_swipe_ratio", "direction": 1, "effect_size": 0.35},
    ],
    CognitiveMechanism.WANTING_LIKING: [
        # Gap indicators (high = dissociated)
        {"signal": SignalSource.CART_BEHAVIOR, "feature": "cart_abandon_rate", "direction": 1, "effect_size": 0.40},
        {"signal": SignalSource.SCROLL_REVERSAL, "feature": "reversal_ratio", "direction": 1, "effect_size": 0.30},
        {"signal": SignalSource.RAGE_CLICK, "feature": "rage_click_count", "direction": 1, "effect_size": 0.35},
    ],
    CognitiveMechanism.MIMETIC_DESIRE: [
        # High susceptibility indicators
        {"signal": SignalSource.SOCIAL_PROOF_ENGAGEMENT, "feature": "social_proof_dwell", "direction": 1, "effect_size": 0.46},
        {"signal": SignalSource.CURSOR_HOVER, "feature": "hover_reviews_mean", "direction": 1, "effect_size": 0.40},
        {"signal": SignalSource.PODCAST_PREFERENCE, "feature": "news_politics_preference", "direction": -1, "effect_size": 0.38},
    ],
    CognitiveMechanism.ATTENTION_DYNAMICS: [
        # High engagement indicators
        {"signal": SignalSource.SCROLL_VELOCITY, "feature": "scroll_velocity_mean", "direction": -1, "effect_size": 0.35},
        {"signal": SignalSource.CURSOR_HOVER, "feature": "hover_duration_mean", "direction": 1, "effect_size": 0.40},
        {"signal": SignalSource.DWELL_TIME, "feature": "dwell_time_mean", "direction": 1, "effect_size": 0.45},
        # Low engagement indicators
        {"signal": SignalSource.ACCELEROMETER, "feature": "magnitude_std", "direction": -1, "effect_size": 0.35},
    ],
    CognitiveMechanism.TEMPORAL_CONSTRUAL: [
        # Future-oriented indicators
        {"signal": SignalSource.RESPONSE_LATENCY, "feature": "response_latency_mean", "direction": 1, "effect_size": 0.30, "threshold_high": 2000},
        {"signal": SignalSource.SCROLL_DEPTH, "feature": "max_depth", "direction": 1, "effect_size": 0.25},
        # Present-oriented indicators
        {"signal": SignalSource.HESITATION, "feature": "pre_cta_hesitation_ratio", "direction": -1, "effect_size": 0.35},
        {"signal": SignalSource.PRICE_SENSITIVITY, "feature": "price_compare_count", "direction": -1, "effect_size": 0.40},
    ],
    CognitiveMechanism.IDENTITY_CONSTRUCTION: [
        # High identity activation
        {"signal": SignalSource.CATEGORY_EXPLORATION, "feature": "category_consistency", "direction": 1, "effect_size": 0.35},
        {"signal": SignalSource.MUSIC_PREFERENCE, "feature": "genre_loyalty", "direction": 1, "effect_size": 0.40},
        {"signal": SignalSource.KEYSTROKE_RHYTHM, "feature": "keystroke_seq_rhythm_regularity", "direction": 1, "effect_size": 0.30},
    ],
    CognitiveMechanism.EVOLUTIONARY_ADAPTATIONS: [
        # High sensitivity indicators
        {"signal": SignalSource.RESPONSE_LATENCY, "feature": "scarcity_response_latency", "direction": 1, "effect_size": 0.45},
        {"signal": SignalSource.TOUCH_PRESSURE, "feature": "pressure_mean", "direction": 1, "effect_size": 0.40},
        {"signal": SignalSource.PODCAST_PREFERENCE, "feature": "true_crime_preference", "direction": 1, "effect_size": 0.51},
    ],
}


# =============================================================================
# MECHANISM POLARITIES
# =============================================================================

MECHANISM_POLARITY: Dict[CognitiveMechanism, MechanismPolarity] = {
    CognitiveMechanism.CONSTRUAL_LEVEL: MechanismPolarity.BIPOLAR,
    CognitiveMechanism.REGULATORY_FOCUS: MechanismPolarity.BIPOLAR,
    CognitiveMechanism.AUTOMATIC_EVALUATION: MechanismPolarity.BIPOLAR,
    CognitiveMechanism.WANTING_LIKING: MechanismPolarity.UNIPOLAR,
    CognitiveMechanism.MIMETIC_DESIRE: MechanismPolarity.UNIPOLAR,
    CognitiveMechanism.ATTENTION_DYNAMICS: MechanismPolarity.UNIPOLAR,
    CognitiveMechanism.TEMPORAL_CONSTRUAL: MechanismPolarity.BIPOLAR,
    CognitiveMechanism.IDENTITY_CONSTRUCTION: MechanismPolarity.UNIPOLAR,
    CognitiveMechanism.EVOLUTIONARY_ADAPTATIONS: MechanismPolarity.UNIPOLAR,
}


# =============================================================================
# MECHANISM EFFECTIVENESS (Bayesian Learning)
# =============================================================================

class MechanismEffectiveness(BaseModel):
    """
    Bayesian effectiveness tracking for a mechanism with a specific user.
    
    Uses Beta distribution parameters (alpha, beta) for Thompson Sampling.
    This enables:
    1. Exploration vs exploitation of mechanisms
    2. Continuous learning from outcomes
    3. Uncertainty-aware mechanism selection
    
    Reference: Enhancement #06 Gradient Bridge - Multi-level Credit Attribution
    """
    effectiveness_id: str = Field(default_factory=lambda: f"meff_{uuid.uuid4().hex[:12]}")
    
    # What we're tracking
    user_id: str
    mechanism: CognitiveMechanism
    
    # Beta distribution parameters (Bayesian prior)
    alpha: float = Field(default=1.0, ge=0.0)  # Success pseudo-count
    beta: float = Field(default=1.0, ge=0.0)   # Failure pseudo-count
    
    # Derived metrics
    @property
    def mean_effectiveness(self) -> float:
        """Expected effectiveness (mean of Beta distribution)."""
        return self.alpha / (self.alpha + self.beta)
    
    @property
    def trial_count(self) -> float:
        """Total pseudo-trials."""
        return self.alpha + self.beta - 2  # Subtract prior
    
    @property
    def confidence(self) -> float:
        """Confidence based on trial count."""
        if self.trial_count < 5:
            return 0.3
        elif self.trial_count < 20:
            return 0.5
        elif self.trial_count < 50:
            return 0.7
        else:
            return 0.9
    
    @property
    def variance(self) -> float:
        """Variance of Beta distribution (uncertainty)."""
        ab = self.alpha + self.beta
        return (self.alpha * self.beta) / (ab * ab * (ab + 1))
    
    # Context tracking
    context_segment: Optional[str] = None  # e.g., "high_arousal_mobile"
    category_id: Optional[str] = None
    
    # History
    last_success_at: Optional[datetime] = None
    last_failure_at: Optional[datetime] = None
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    
    # Decay tracking
    days_since_last_success: Optional[int] = None
    
    def update(self, success: bool, weight: float = 1.0) -> "MechanismEffectiveness":
        """Update posterior with new observation."""
        if success:
            self.alpha += weight
            self.last_success_at = datetime.utcnow()
        else:
            self.beta += weight
            self.last_failure_at = datetime.utcnow()
        self.last_updated = datetime.utcnow()
        return self
    
    def sample(self) -> float:
        """Thompson Sampling: draw from posterior."""
        import random
        # Python's random.betavariate uses (alpha, beta) parameters
        return random.betavariate(self.alpha, self.beta)
    
    class Config:
        use_enum_values = True


class MechanismActivation(BaseModel):
    """
    Record of a mechanism activation in a decision.
    
    Used for credit attribution and learning.
    Reference: Enhancement #04 Atom of Thought DAG
    """
    activation_id: str = Field(default_factory=lambda: f"mact_{uuid.uuid4().hex[:12]}")
    
    # Context
    decision_id: str
    user_id: str
    session_id: str
    
    # What was activated
    mechanism: CognitiveMechanism
    intensity: float = Field(ge=0.0, le=1.0)  # How strongly activated
    is_primary: bool = False  # Was this the primary mechanism?
    
    # Evidence that led to activation
    evidence_ids: List[str] = Field(default_factory=list)
    evidence_strength: float = Field(ge=0.0, le=1.0, default=0.5)
    
    # Prior effectiveness (from history)
    prior_effectiveness: float = Field(ge=0.0, le=1.0, default=0.5)
    prior_confidence: float = Field(ge=0.0, le=1.0, default=0.3)
    
    # Timing
    activated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Message used (for learning)
    message_type: Optional[str] = None
    message_framing: Optional[str] = None
    
    class Config:
        use_enum_values = True


class MechanismInteraction(BaseModel):
    """
    Learned interaction between two mechanisms.
    
    Some mechanisms amplify or suppress each other.
    E.g., High construal + promotion focus → aspirational messaging works well.
    
    Reference: Enhancement #03 Meta-Learning Orchestration
    """
    interaction_id: str = Field(default_factory=lambda: f"mint_{uuid.uuid4().hex[:12]}")
    
    # The interacting mechanisms
    mechanism_a: CognitiveMechanism
    mechanism_b: CognitiveMechanism
    
    # Interaction type
    interaction_type: str = "synergistic"  # "synergistic", "suppressive", "neutral"
    
    # Learned interaction strength
    # Positive = synergistic (both high → better outcomes)
    # Negative = suppressive (both high → worse outcomes)
    interaction_strength: float = Field(ge=-1.0, le=1.0, default=0.0)
    
    # Confidence in the interaction
    sample_size: int = Field(ge=0, default=0)
    confidence: float = Field(ge=0.0, le=1.0, default=0.0)
    
    # Context where this interaction was observed
    applicable_contexts: List[str] = Field(default_factory=list)
    
    # Timing
    discovered_at: datetime = Field(default_factory=datetime.utcnow)
    last_validated: Optional[datetime] = None
    
    class Config:
        use_enum_values = True


# =============================================================================
# SUPRALIMINAL SIGNALS (Desktop/Explicit)
# =============================================================================

class SupraliminalSignalProfile(BaseModel):
    """
    Profile of supraliminal (conscious/explicit) signals.
    
    These are signals users are aware of producing:
    - Cursor movements
    - Keystroke patterns
    - Explicit scroll behavior
    - Click patterns
    
    In contrast to subliminal (touch pressure, accelerometer) which users
    don't consciously control.
    
    Reference: Enhancement #08 Signal Aggregation
    """
    profile_id: str = Field(default_factory=lambda: f"ssp_{uuid.uuid4().hex[:12]}")
    
    user_id: str
    session_id: str
    
    # Cursor dynamics (Decision Conflict indicators)
    cursor_trajectory_auc_mean: float = Field(default=0.0)  # Higher = more conflict
    cursor_movement_time_mean_ms: float = Field(default=0.0)
    cursor_x_flip_count: int = Field(default=0)
    cursor_hover_time_total_ms: float = Field(default=0.0)
    cursor_initiation_time_mean_ms: float = Field(default=0.0)
    
    # Keystroke dynamics (Cognitive Load indicators)
    keystroke_hold_time_mean_ms: float = Field(default=0.0)  # Longer = higher load
    keystroke_flight_time_mean_ms: float = Field(default=0.0)
    keystroke_typing_speed_cpm: float = Field(default=0.0)
    keystroke_error_rate: float = Field(default=0.0)
    keystroke_rhythm_regularity: float = Field(default=0.5)  # Higher = more regular
    
    # Scroll behavior (Engagement indicators)
    scroll_depth_max: float = Field(default=0.0)
    scroll_reversal_count: int = Field(default=0)  # Higher = re-reading = interest
    scroll_velocity_mean: float = Field(default=0.0)
    scroll_pause_count: int = Field(default=0)
    
    # Derived psychological inferences
    @property
    def decision_conflict_score(self) -> float:
        """Inferred decision conflict from cursor patterns."""
        # Higher AUC and more x-flips = more conflict
        auc_contribution = min(1.0, self.cursor_trajectory_auc_mean)
        flip_contribution = min(1.0, self.cursor_x_flip_count / 5)
        return (auc_contribution * 0.6 + flip_contribution * 0.4)
    
    @property
    def cognitive_load_score(self) -> float:
        """Inferred cognitive load from keystroke patterns."""
        # Longer hold times, lower speed, more errors = higher load
        hold_contribution = min(1.0, self.keystroke_hold_time_mean_ms / 200)
        error_contribution = min(1.0, self.keystroke_error_rate * 5)
        speed_contribution = max(0, 1 - (self.keystroke_typing_speed_cpm / 300))
        return (hold_contribution * 0.4 + error_contribution * 0.3 + speed_contribution * 0.3)
    
    @property
    def engagement_score(self) -> float:
        """Inferred engagement from scroll behavior."""
        depth_contribution = self.scroll_depth_max
        reversal_contribution = min(1.0, self.scroll_reversal_count / 3)
        return (depth_contribution * 0.6 + reversal_contribution * 0.4)
    
    # Timing
    created_at: datetime = Field(default_factory=datetime.utcnow)
    measurement_duration_ms: float = Field(default=0.0)
    
    # Confidence
    overall_confidence: float = Field(default=0.5)


# =============================================================================
# BEHAVIORAL DISCOVERY (Pattern Mining)
# =============================================================================

class BehavioralDiscovery(BaseModel):
    """
    A discovered behavioral pattern that wasn't pre-programmed.
    
    These emerge from the data through:
    1. Statistical significance testing
    2. Hypothesis generation and validation
    3. Cross-user pattern mining
    
    Reference: ADAM_EMERGENT_INTELLIGENCE_ARCHITECTURE.md - Graph-Emergent Insights
    """
    discovery_id: str = Field(default_factory=lambda: f"disc_{uuid.uuid4().hex[:12]}")
    
    # Pattern definition
    pattern_name: str
    pattern_description: str
    
    # Signal sequence or combination
    signal_pattern: List[Dict[str, Any]] = Field(default_factory=list)
    # Example: [{"signal": "cursor_trajectory_auc", "operator": ">", "value": 0.7},
    #           {"signal": "keystroke_hold_time", "operator": ">", "value": 150}]
    
    # What it predicts
    predicted_outcome: str  # e.g., "conversion", "abandonment"
    predicted_direction: str = "positive"  # "positive", "negative"
    
    # Statistical validation
    sample_size: int = Field(ge=0)
    effect_size: float = Field(ge=0.0)  # Cohen's d or odds ratio
    p_value: Optional[float] = None
    confidence_interval_lower: Optional[float] = None
    confidence_interval_upper: Optional[float] = None
    
    # Lift over baseline
    baseline_rate: float = Field(ge=0.0, le=1.0, default=0.0)
    pattern_rate: float = Field(ge=0.0, le=1.0, default=0.0)
    lift: float = Field(default=1.0)  # pattern_rate / baseline_rate
    
    # Validation status
    status: str = "discovered"  # "discovered", "testing", "validated", "deprecated"
    validation_count: int = Field(default=0, ge=0)
    validation_successes: int = Field(default=0, ge=0)
    
    @property
    def validation_rate(self) -> float:
        """Success rate of predictions."""
        if self.validation_count == 0:
            return 0.0
        return self.validation_successes / self.validation_count
    
    # Related mechanisms
    likely_mechanisms: List[CognitiveMechanism] = Field(default_factory=list)
    mechanism_explanation: Optional[str] = None
    
    # Applicable segments
    applicable_segments: List[str] = Field(default_factory=list)
    applicable_categories: List[str] = Field(default_factory=list)
    
    # Discovery metadata
    discovery_algorithm: str = "frequent_pattern_mining"
    discovered_at: datetime = Field(default_factory=datetime.utcnow)
    discovered_by: str = "system"  # "system" or "hypothesis_engine"
    
    # Decay tracking
    last_successful_prediction: Optional[datetime] = None
    prediction_decay_days: int = Field(default=0, ge=0)
    
    class Config:
        use_enum_values = True
