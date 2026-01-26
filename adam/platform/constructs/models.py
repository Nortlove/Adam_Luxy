# =============================================================================
# ADAM Psychological Constructs Models (#27)
# Location: adam/platform/constructs/models.py
# =============================================================================

"""
EXTENDED PSYCHOLOGICAL CONSTRUCT MODELS

Pydantic models for the 12-domain psychological framework.

Research Foundation:
- Cacioppo & Petty (1982): Need for Cognition
- Snyder (1974): Self-Monitoring
- Higgins (1997): Regulatory Focus Theory
- Schwartz et al. (2012): Basic Human Values
- Zimbardo & Boyd (1999): Time Perspective Inventory
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


# =============================================================================
# CORE MODELS
# =============================================================================

class ConstructConfidence(str, Enum):
    """Confidence level for construct inference."""
    
    HIGH = "high"           # Multiple strong signals
    MEDIUM = "medium"       # Some behavioral evidence
    LOW = "low"             # Inferred from priors
    COLD_START = "cold_start"  # Archetype-based default


class ConstructScore(BaseModel):
    """A single psychological construct score."""
    
    value: float = Field(default=0.5, ge=0.0, le=1.0)
    confidence: ConstructConfidence = ConstructConfidence.MEDIUM
    signal_count: int = 0  # Number of signals contributing
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Attribution
    primary_signal_source: Optional[str] = None
    
    def to_float(self) -> float:
        """Return just the value."""
        return self.value


# =============================================================================
# DOMAIN 1: COGNITIVE PROCESSING
# =============================================================================

class CognitiveProcessingDomain(BaseModel):
    """
    Domain 1: How users process information.
    
    Research: Cacioppo & Petty (1982), Stanovich & West (2000)
    """
    
    # Need for Cognition (NFC)
    # High NFC: Enjoy thinking, seek complex arguments
    # Low NFC: Prefer simple, heuristic-based decisions
    need_for_cognition: ConstructScore = Field(default_factory=ConstructScore)
    
    # Processing Speed Preference
    # Fast: Quick decisions, peripheral route
    # Slow: Deliberate, central route
    processing_speed: ConstructScore = Field(default_factory=ConstructScore)
    
    # Heuristic Reliance Index
    # High: Uses mental shortcuts heavily
    # Low: Systematic processing
    heuristic_reliance: ConstructScore = Field(default_factory=ConstructScore)
    
    # Persuasion implications
    def get_persuasion_strategy(self) -> Dict[str, Any]:
        nfc = self.need_for_cognition.value
        return {
            "argument_complexity": "high" if nfc > 0.6 else "low",
            "evidence_depth": "detailed" if nfc > 0.6 else "summary",
            "processing_route": "central" if nfc > 0.6 else "peripheral",
        }


# =============================================================================
# DOMAIN 2: SELF-REGULATORY
# =============================================================================

class SelfRegulatoryDomain(BaseModel):
    """
    Domain 2: How users regulate behavior and pursue goals.
    
    Research: Snyder (1974), Higgins (1997), Kruglanski et al. (2000)
    """
    
    # Self-Monitoring
    # High: Adapts presentation to social context
    # Low: Consistent across situations
    self_monitoring: ConstructScore = Field(default_factory=ConstructScore)
    
    # Regulatory Focus (Higgins)
    # Promotion: Focused on gains, aspirations
    # Prevention: Focused on safety, responsibilities
    promotion_focus: ConstructScore = Field(default_factory=ConstructScore)
    prevention_focus: ConstructScore = Field(default_factory=ConstructScore)
    
    # Locomotion-Assessment Mode (Kruglanski)
    # Locomotion: Action-oriented, "just do it"
    # Assessment: Evaluation-oriented, compare options
    locomotion: ConstructScore = Field(default_factory=ConstructScore)
    assessment: ConstructScore = Field(default_factory=ConstructScore)
    
    @property
    def dominant_focus(self) -> str:
        if self.promotion_focus.value > self.prevention_focus.value + 0.15:
            return "promotion"
        elif self.prevention_focus.value > self.promotion_focus.value + 0.15:
            return "prevention"
        return "balanced"
    
    def get_framing_strategy(self) -> str:
        """Get optimal message framing."""
        if self.dominant_focus == "promotion":
            return "gain"
        elif self.dominant_focus == "prevention":
            return "loss"
        return "balanced"


# =============================================================================
# DOMAIN 3: TEMPORAL PSYCHOLOGY
# =============================================================================

class TemporalPsychologyDomain(BaseModel):
    """
    Domain 3: How users relate to time.
    
    Research: Zimbardo & Boyd (1999), Ersner-Hershfield (2009)
    """
    
    # Temporal Orientation
    # Past: Nostalgic, tradition-focused
    # Present: Hedonistic or fatalistic
    # Future: Planning, goal-oriented
    past_orientation: ConstructScore = Field(default_factory=ConstructScore)
    present_orientation: ConstructScore = Field(default_factory=ConstructScore)
    future_orientation: ConstructScore = Field(default_factory=ConstructScore)
    
    # Future Self-Continuity
    # High: Strong connection to future self
    # Low: Disconnected from future consequences
    future_self_continuity: ConstructScore = Field(default_factory=ConstructScore)
    
    # Delay Discounting Rate
    # High: Strong preference for immediate rewards
    # Low: Comfortable with delayed gratification
    delay_discounting: ConstructScore = Field(default_factory=ConstructScore)
    
    # Planning Horizon (in days)
    planning_horizon: ConstructScore = Field(default_factory=ConstructScore)
    
    @property
    def dominant_orientation(self) -> str:
        scores = {
            "past": self.past_orientation.value,
            "present": self.present_orientation.value,
            "future": self.future_orientation.value,
        }
        return max(scores, key=scores.get)


# =============================================================================
# DOMAIN 4: DECISION MAKING
# =============================================================================

class DecisionMakingDomain(BaseModel):
    """
    Domain 4: How users make choices.
    
    Research: Schwartz (2002), Zeelenberg (1999), Iyengar & Lepper (2000)
    """
    
    # Maximizer-Satisficer (Schwartz)
    # Maximizer: Seeks best option, exhaustive search
    # Satisficer: Accepts "good enough"
    maximizer_tendency: ConstructScore = Field(default_factory=ConstructScore)
    
    # Regret Anticipation Style
    # High: Strong anticipated regret, risk-averse
    # Low: Less concerned about wrong choices
    regret_anticipation: ConstructScore = Field(default_factory=ConstructScore)
    
    # Choice Overload Susceptibility
    # High: Paralyzed by too many options
    # Low: Comfortable with many choices
    choice_overload_susceptibility: ConstructScore = Field(default_factory=ConstructScore)
    
    def get_choice_architecture(self) -> Dict[str, Any]:
        """Get optimal choice presentation."""
        return {
            "num_options": 3 if self.choice_overload_susceptibility.value > 0.6 else 6,
            "comparison_tools": self.maximizer_tendency.value > 0.6,
            "regret_reassurance": self.regret_anticipation.value > 0.6,
        }


# =============================================================================
# DOMAIN 5: SOCIAL-COGNITIVE
# =============================================================================

class SocialCognitiveDomain(BaseModel):
    """
    Domain 5: How users are influenced by others.
    
    Research: Cialdini (2001), Asch (1951), Rogers (1962)
    """
    
    # Susceptibility to Social Proof
    # High: Strongly influenced by others' behavior
    # Low: Independent decision-maker
    social_proof_susceptibility: ConstructScore = Field(default_factory=ConstructScore)
    
    # Conformity Tendency
    # High: Aligns with group norms
    # Low: Non-conformist
    conformity: ConstructScore = Field(default_factory=ConstructScore)
    
    # Opinion Leadership
    # High: Influences others' opinions
    # Low: Follows others' opinions
    opinion_leadership: ConstructScore = Field(default_factory=ConstructScore)
    
    # Need for Uniqueness
    # High: Seeks differentiation
    # Low: Comfortable with similarity
    need_for_uniqueness: ConstructScore = Field(default_factory=ConstructScore)
    
    def get_social_strategy(self) -> Dict[str, Any]:
        return {
            "use_testimonials": self.social_proof_susceptibility.value > 0.6,
            "use_scarcity": self.conformity.value < 0.4,
            "use_exclusivity": self.need_for_uniqueness.value > 0.6,
        }


# =============================================================================
# DOMAIN 6: UNCERTAINTY PROCESSING
# =============================================================================

class UncertaintyProcessingDomain(BaseModel):
    """
    Domain 6: How users handle ambiguity.
    
    Research: Budner (1962), Webster & Kruglanski (1994)
    """
    
    # Ambiguity Tolerance
    # High: Comfortable with uncertainty
    # Low: Needs clarity, structure
    ambiguity_tolerance: ConstructScore = Field(default_factory=ConstructScore)
    
    # Need for Closure
    # High: Wants quick, definitive answers
    # Low: Comfortable with open questions
    need_for_closure: ConstructScore = Field(default_factory=ConstructScore)
    
    # Risk Tolerance
    # High: Comfortable with uncertainty
    # Low: Risk-averse
    risk_tolerance: ConstructScore = Field(default_factory=ConstructScore)


# =============================================================================
# DOMAIN 7: INFORMATION PROCESSING
# =============================================================================

class InformationProcessingDomain(BaseModel):
    """
    Domain 7: How users prefer to receive information.
    
    Research: Riding & Cheema (1991), Nisbett et al. (2001)
    """
    
    # Visualizer-Verbalizer
    # Visualizer: Prefers images, diagrams
    # Verbalizer: Prefers text, descriptions
    visualizer_tendency: ConstructScore = Field(default_factory=ConstructScore)
    
    # Holistic-Analytic Style
    # Holistic: Big picture, context-dependent
    # Analytic: Detail-focused, context-independent
    holistic_style: ConstructScore = Field(default_factory=ConstructScore)
    
    # Field Independence
    # High: Separates elements from context
    # Low: Context-sensitive processing
    field_independence: ConstructScore = Field(default_factory=ConstructScore)
    
    def get_content_format(self) -> Dict[str, Any]:
        return {
            "prefer_images": self.visualizer_tendency.value > 0.6,
            "prefer_text": self.visualizer_tendency.value < 0.4,
            "show_context": self.holistic_style.value > 0.6,
            "focus_details": self.holistic_style.value < 0.4,
        }


# =============================================================================
# DOMAIN 8: MOTIVATIONAL PROFILE
# =============================================================================

class MotivationalProfileDomain(BaseModel):
    """
    Domain 8: What drives user behavior.
    
    Research: McClelland (1961), Deci & Ryan (2000)
    """
    
    # Achievement Motivation
    # High: Driven by accomplishment
    achievement_motivation: ConstructScore = Field(default_factory=ConstructScore)
    
    # Power Motivation
    # High: Driven by influence, status
    power_motivation: ConstructScore = Field(default_factory=ConstructScore)
    
    # Affiliation Motivation
    # High: Driven by relationships, belonging
    affiliation_motivation: ConstructScore = Field(default_factory=ConstructScore)
    
    # Intrinsic-Extrinsic Balance
    # High: Intrinsically motivated
    # Low: Extrinsically motivated
    intrinsic_motivation: ConstructScore = Field(default_factory=ConstructScore)
    
    @property
    def primary_motivation(self) -> str:
        scores = {
            "achievement": self.achievement_motivation.value,
            "power": self.power_motivation.value,
            "affiliation": self.affiliation_motivation.value,
        }
        return max(scores, key=scores.get)


# =============================================================================
# DOMAIN 9: EMOTIONAL PROCESSING
# =============================================================================

class EmotionalProcessingDomain(BaseModel):
    """
    Domain 9: How users experience and process emotions.
    
    Research: Larsen & Diener (1987), Barrett (2004)
    """
    
    # Affect Intensity
    # High: Experiences emotions strongly
    # Low: More emotionally stable
    affect_intensity: ConstructScore = Field(default_factory=ConstructScore)
    
    # Emotional Granularity
    # High: Differentiates subtle emotions
    # Low: Broad emotional categories
    emotional_granularity: ConstructScore = Field(default_factory=ConstructScore)
    
    # Mood-Congruent Processing
    # High: Judgments influenced by current mood
    # Low: More objective processing
    mood_congruent_processing: ConstructScore = Field(default_factory=ConstructScore)


# =============================================================================
# DOMAIN 10: PURCHASE PSYCHOLOGY
# =============================================================================

class PurchasePsychologyDomain(BaseModel):
    """
    Domain 10: Purchase-specific psychological factors.
    
    Research: Rook (1987), Wood (1998)
    """
    
    # Purchase Confidence Threshold
    # High: Needs high confidence to buy
    # Low: Comfortable with quick decisions
    purchase_confidence_threshold: ConstructScore = Field(default_factory=ConstructScore)
    
    # Return Anxiety
    # High: Worried about returns/hassle
    # Low: Comfortable with returns
    return_anxiety: ConstructScore = Field(default_factory=ConstructScore)
    
    # Post-Purchase Rationalization
    # High: Strong need to justify purchases
    # Low: Less concerned with justification
    post_purchase_rationalization: ConstructScore = Field(default_factory=ConstructScore)
    
    # Impulse Buying Tendency
    # High: Prone to impulse purchases
    # Low: Planned purchaser
    impulse_buying: ConstructScore = Field(default_factory=ConstructScore)


# =============================================================================
# DOMAIN 11: VALUE ORIENTATION
# =============================================================================

class ValueOrientationDomain(BaseModel):
    """
    Domain 11: Core values that guide decisions.
    
    Research: Schwartz (1992), Hofstede (1980)
    """
    
    # Individualism-Collectivism
    # High: Individual goals, self-reliance
    # Low: Group goals, interdependence
    individualism: ConstructScore = Field(default_factory=ConstructScore)
    
    # Materialism
    # High: Material possessions = success
    # Low: Non-material values
    materialism: ConstructScore = Field(default_factory=ConstructScore)
    
    # Environmental Concern
    # High: Eco-conscious decisions
    # Low: Less concerned with environment
    environmental_concern: ConstructScore = Field(default_factory=ConstructScore)
    
    # Traditionalism
    # High: Values tradition, convention
    # Low: Values novelty, change
    traditionalism: ConstructScore = Field(default_factory=ConstructScore)


# =============================================================================
# DOMAIN 12: EMERGENT CONSTRUCTS
# =============================================================================

class EmergentConstructsDomain(BaseModel):
    """
    Domain 12: Novel constructs discovered through #04 Atom of Thought.
    
    These are dynamically discovered patterns that don't fit
    established psychological categories but have predictive value.
    """
    
    # Discovered constructs (dynamic)
    discovered_constructs: Dict[str, ConstructScore] = Field(default_factory=dict)
    
    # Construct discovery metadata
    discovery_count: int = 0
    last_discovery: Optional[datetime] = None
    
    def add_construct(self, name: str, value: float, confidence: ConstructConfidence):
        """Add a newly discovered construct."""
        self.discovered_constructs[name] = ConstructScore(
            value=value,
            confidence=confidence,
            signal_count=1,
        )
        self.discovery_count += 1
        self.last_discovery = datetime.now(timezone.utc)


# =============================================================================
# COMPLETE PROFILE
# =============================================================================

class ExtendedPsychologicalProfile(BaseModel):
    """
    Complete Extended Psychological Profile.
    
    Contains all 12 domains with 35+ constructs for precision persuasion.
    This is the full psychological intelligence for a user.
    """
    
    profile_id: str = Field(default_factory=lambda: f"psy_{uuid4().hex[:12]}")
    user_id: Optional[str] = None
    
    # The 12 Domains
    cognitive_processing: CognitiveProcessingDomain = Field(
        default_factory=CognitiveProcessingDomain
    )
    self_regulatory: SelfRegulatoryDomain = Field(
        default_factory=SelfRegulatoryDomain
    )
    temporal_psychology: TemporalPsychologyDomain = Field(
        default_factory=TemporalPsychologyDomain
    )
    decision_making: DecisionMakingDomain = Field(
        default_factory=DecisionMakingDomain
    )
    social_cognitive: SocialCognitiveDomain = Field(
        default_factory=SocialCognitiveDomain
    )
    uncertainty_processing: UncertaintyProcessingDomain = Field(
        default_factory=UncertaintyProcessingDomain
    )
    information_processing: InformationProcessingDomain = Field(
        default_factory=InformationProcessingDomain
    )
    motivational_profile: MotivationalProfileDomain = Field(
        default_factory=MotivationalProfileDomain
    )
    emotional_processing: EmotionalProcessingDomain = Field(
        default_factory=EmotionalProcessingDomain
    )
    purchase_psychology: PurchasePsychologyDomain = Field(
        default_factory=PurchasePsychologyDomain
    )
    value_orientation: ValueOrientationDomain = Field(
        default_factory=ValueOrientationDomain
    )
    emergent_constructs: EmergentConstructsDomain = Field(
        default_factory=EmergentConstructsDomain
    )
    
    # Profile metadata
    data_tier: str = "cold_start"  # cold_start, developing, established, full
    overall_confidence: float = 0.5
    signal_count: int = 0
    
    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    def get_persuasion_strategy(self) -> Dict[str, Any]:
        """Generate comprehensive persuasion strategy from profile."""
        return {
            "argument_style": self.cognitive_processing.get_persuasion_strategy(),
            "framing": self.self_regulatory.get_framing_strategy(),
            "temporal_focus": self.temporal_psychology.dominant_orientation,
            "choice_architecture": self.decision_making.get_choice_architecture(),
            "social_elements": self.social_cognitive.get_social_strategy(),
            "content_format": self.information_processing.get_content_format(),
            "primary_motivation": self.motivational_profile.primary_motivation,
        }
    
    def get_top_constructs(self, n: int = 5) -> List[Dict[str, Any]]:
        """Get the top N most extreme/confident constructs."""
        constructs = []
        
        # Collect all construct scores
        for domain_name in [
            "cognitive_processing", "self_regulatory", "temporal_psychology",
            "decision_making", "social_cognitive", "uncertainty_processing",
            "information_processing", "motivational_profile", "emotional_processing",
            "purchase_psychology", "value_orientation"
        ]:
            domain = getattr(self, domain_name)
            for field_name, field_value in domain:
                if isinstance(field_value, ConstructScore):
                    extremity = abs(field_value.value - 0.5)
                    constructs.append({
                        "domain": domain_name,
                        "construct": field_name,
                        "value": field_value.value,
                        "confidence": field_value.confidence.value,
                        "extremity": extremity,
                    })
        
        # Sort by extremity and return top N
        constructs.sort(key=lambda x: x["extremity"], reverse=True)
        return constructs[:n]
