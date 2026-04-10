# =============================================================================
# Brand-as-Person Personality Model
# Location: adam/intelligence/models/brand_personality.py
# =============================================================================

"""
BRAND-AS-PERSON PSYCHOLOGICAL MODEL

This module defines the comprehensive Brand Personality Profile - treating the
brand as if it were a person with:

1. Big Five Personality (the brand's own personality)
2. Aaker Brand Personality Dimensions (sincerity, excitement, competence, etc.)
3. Brand Archetype (Jung/Mark 12 archetypes)
4. Demographic Impression (age, gender, class, occupation)
5. Brand-Consumer Relationship Dynamics
6. Consumer Attraction Patterns
7. Brand Voice Characteristics

This is a CORE PRIMITIVE in ADAM - brand personality informs:
- Mechanism selection (which psychological levers work for this brand)
- Station matching (brand voice → station persona fit)
- Copy generation (brand voice characteristics)
- Archetype targeting (which consumer archetypes are attracted)
- Learning (which brand-archetype combinations are effective)

Research foundations:
- Aaker, J. L. (1997). Dimensions of brand personality
- Mark & Pearson (2001). The Hero and the Outlaw - brand archetypes
- Fournier, S. (1998). Consumers and their brands
- Keller, K. L. (2013). Strategic Brand Management
"""

from datetime import datetime, timezone
from typing import Any, ClassVar, Dict, List, Optional, Tuple
from enum import Enum

from pydantic import BaseModel, Field


# =============================================================================
# ENUMS
# =============================================================================

class BrandArchetype(str, Enum):
    """Jung/Mark brand archetypes - 12 fundamental brand personalities."""
    INNOCENT = "innocent"       # Pure, optimistic, wholesome (Disney, Coca-Cola)
    SAGE = "sage"               # Wise, knowledgeable, expert (Google, McKinsey)
    EXPLORER = "explorer"       # Adventurous, pioneering (Jeep, REI, Patagonia)
    OUTLAW = "outlaw"           # Rebellious, disruptive (Harley-Davidson, Virgin)
    MAGICIAN = "magician"       # Transformative, visionary (Apple, Tesla)
    HERO = "hero"               # Courageous, determined (Nike, FedEx, BMW)
    LOVER = "lover"             # Passionate, sensual (Victoria's Secret, Chanel)
    JESTER = "jester"           # Fun, playful (M&M's, Old Spice)
    EVERYMAN = "everyman"       # Relatable, humble (IKEA, Target)
    CAREGIVER = "caregiver"     # Nurturing, protective (Johnson & Johnson, TOMS)
    RULER = "ruler"             # Authoritative, premium (Rolex, Mercedes-Benz)
    CREATOR = "creator"         # Innovative, artistic (Lego, Adobe)


class BrandRelationshipRole(str, Enum):
    """The role the brand plays in the consumer's life."""
    MENTOR = "mentor"               # Guides and teaches (DEWALT, MasterClass)
    FRIEND = "friend"               # Companion, peer (Budweiser, Ben & Jerry's)
    PARTNER = "partner"             # Equal collaborator (Nike, LinkedIn)
    SERVANT = "servant"             # Dedicated helper (Amazon, Zappos)
    ADMIRED_EXPERT = "admired_expert"  # Respected authority (Mayo Clinic, IBM)
    INSPIRING_LEADER = "inspiring_leader"  # Visionary to follow (Apple, Tesla)
    PROTECTIVE_GUARDIAN = "protective_guardian"  # Keeper of safety (Volvo, ADT)
    ENABLER = "enabler"             # Empowers achievement (Red Bull, GoPro)
    TRUSTED_ADVISOR = "trusted_advisor"  # Reliable counsel (Fidelity, WebMD)
    PLAYMATE = "playmate"           # Fun companion (Nintendo, Sour Patch Kids)


class BrandVoiceStyle(str, Enum):
    """How the brand communicates."""
    AUTHORITATIVE = "authoritative"     # Commands respect, expert knowledge
    CONVERSATIONAL = "conversational"   # Friendly, approachable
    INSPIRATIONAL = "inspirational"     # Motivating, uplifting
    TECHNICAL = "technical"             # Precise, detailed, professional
    PLAYFUL = "playful"                 # Fun, witty, irreverent
    SOPHISTICATED = "sophisticated"     # Elegant, refined
    RUGGED = "rugged"                   # Tough, no-nonsense
    NURTURING = "nurturing"             # Warm, caring, supportive
    PROVOCATIVE = "provocative"         # Challenging, edgy
    REASSURING = "reassuring"           # Calming, confidence-building


class GenderImpression(str, Enum):
    """Gender impression of the brand-as-person."""
    MASCULINE = "masculine"
    FEMININE = "feminine"
    NEUTRAL = "neutral"
    ANDROGYNOUS = "androgynous"


# =============================================================================
# BIG FIVE TRAIT (FOR BRAND)
# =============================================================================

class BrandBigFiveTrait(BaseModel):
    """A single Big Five trait for the brand-as-person."""
    
    score: float = Field(ge=0.0, le=1.0, description="0-1 score for this trait")
    reasoning: str = Field(default="", description="Why the brand has this score")
    evidence: List[str] = Field(default_factory=list, description="Supporting evidence")
    
    def __repr__(self) -> str:
        return f"BigFive({self.score:.0%}: {self.reasoning[:50]}...)"


class BrandBigFive(BaseModel):
    """
    Big Five personality of the brand-as-person.
    
    This is NOT the target audience's personality - this is the brand's
    own personality as if it were a human being.
    """
    
    openness: BrandBigFiveTrait = Field(
        default_factory=lambda: BrandBigFiveTrait(score=0.5),
        description="Creative, curious, open to new ideas vs. traditional"
    )
    conscientiousness: BrandBigFiveTrait = Field(
        default_factory=lambda: BrandBigFiveTrait(score=0.5),
        description="Organized, reliable, disciplined vs. flexible, spontaneous"
    )
    extraversion: BrandBigFiveTrait = Field(
        default_factory=lambda: BrandBigFiveTrait(score=0.5),
        description="Outgoing, energetic, talkative vs. reserved, quiet"
    )
    agreeableness: BrandBigFiveTrait = Field(
        default_factory=lambda: BrandBigFiveTrait(score=0.5),
        description="Friendly, compassionate, cooperative vs. competitive, tough"
    )
    neuroticism: BrandBigFiveTrait = Field(
        default_factory=lambda: BrandBigFiveTrait(score=0.5),
        description="Emotional, anxious vs. calm, stable, confident"
    )
    
    def to_vector(self) -> List[float]:
        """Convert to 5-element vector for similarity computation."""
        return [
            self.openness.score,
            self.conscientiousness.score,
            self.extraversion.score,
            self.agreeableness.score,
            self.neuroticism.score,
        ]
    
    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary of scores."""
        return {
            "openness": self.openness.score,
            "conscientiousness": self.conscientiousness.score,
            "extraversion": self.extraversion.score,
            "agreeableness": self.agreeableness.score,
            "neuroticism": self.neuroticism.score,
        }
    
    def get_dominant_traits(self, threshold: float = 0.7) -> List[str]:
        """Get traits that are notably high."""
        traits = []
        if self.openness.score >= threshold:
            traits.append("openness")
        if self.conscientiousness.score >= threshold:
            traits.append("conscientiousness")
        if self.extraversion.score >= threshold:
            traits.append("extraversion")
        if self.agreeableness.score >= threshold:
            traits.append("agreeableness")
        # Neuroticism is inverted - LOW neuroticism is notable
        if self.neuroticism.score <= (1 - threshold):
            traits.append("emotional_stability")
        return traits


# =============================================================================
# AAKER BRAND PERSONALITY
# =============================================================================

class AakerDimension(BaseModel):
    """A single Aaker brand personality dimension with facets."""
    
    score: float = Field(ge=0.0, le=1.0, description="0-1 score for this dimension")
    facets_expressed: List[str] = Field(
        default_factory=list,
        description="Which facets of this dimension are expressed"
    )
    evidence: List[str] = Field(default_factory=list)


class AakerBrandPersonality(BaseModel):
    """
    Aaker's (1997) Brand Personality Framework.
    
    Five dimensions that capture human personality traits applied to brands.
    """
    
    sincerity: AakerDimension = Field(
        default_factory=lambda: AakerDimension(
            score=0.5,
            facets_expressed=[]
        ),
        description="Down-to-earth, honest, wholesome, cheerful"
    )
    excitement: AakerDimension = Field(
        default_factory=lambda: AakerDimension(
            score=0.5,
            facets_expressed=[]
        ),
        description="Daring, spirited, imaginative, up-to-date"
    )
    competence: AakerDimension = Field(
        default_factory=lambda: AakerDimension(
            score=0.5,
            facets_expressed=[]
        ),
        description="Reliable, intelligent, successful"
    )
    sophistication: AakerDimension = Field(
        default_factory=lambda: AakerDimension(
            score=0.5,
            facets_expressed=[]
        ),
        description="Upper-class, charming, glamorous"
    )
    ruggedness: AakerDimension = Field(
        default_factory=lambda: AakerDimension(
            score=0.5,
            facets_expressed=[]
        ),
        description="Outdoorsy, tough, masculine"
    )
    
    # Aaker facets for reference
    FACETS: ClassVar[Dict[str, List[str]]] = {
        "sincerity": ["down-to-earth", "honest", "wholesome", "cheerful"],
        "excitement": ["daring", "spirited", "imaginative", "up-to-date"],
        "competence": ["reliable", "intelligent", "successful"],
        "sophistication": ["upper-class", "charming", "glamorous"],
        "ruggedness": ["outdoorsy", "tough", "masculine"],
    }
    
    def to_vector(self) -> List[float]:
        """Convert to 5-element vector."""
        return [
            self.sincerity.score,
            self.excitement.score,
            self.competence.score,
            self.sophistication.score,
            self.ruggedness.score,
        ]
    
    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary of scores."""
        return {
            "sincerity": self.sincerity.score,
            "excitement": self.excitement.score,
            "competence": self.competence.score,
            "sophistication": self.sophistication.score,
            "ruggedness": self.ruggedness.score,
        }
    
    def get_dominant_dimensions(self, threshold: float = 0.7) -> List[str]:
        """Get dimensions that are notably high."""
        dims = []
        if self.sincerity.score >= threshold:
            dims.append("sincerity")
        if self.excitement.score >= threshold:
            dims.append("excitement")
        if self.competence.score >= threshold:
            dims.append("competence")
        if self.sophistication.score >= threshold:
            dims.append("sophistication")
        if self.ruggedness.score >= threshold:
            dims.append("ruggedness")
        return dims


# =============================================================================
# BRAND DEMOGRAPHIC IMPRESSION
# =============================================================================

class BrandDemographicImpression(BaseModel):
    """
    The demographic impression of the brand-as-person.
    
    If this brand were a person, what would they look like?
    """
    
    description_as_person: str = Field(
        default="",
        description="Full description of the brand as a human being"
    )
    
    age_impression: str = Field(
        default="",
        description="How old does this brand feel? (e.g., 'Late 40s - mature, experienced')"
    )
    age_range_low: int = Field(default=30, ge=0, le=100)
    age_range_high: int = Field(default=50, ge=0, le=100)
    
    gender_impression: GenderImpression = Field(
        default=GenderImpression.NEUTRAL,
        description="What gender does this brand project?"
    )
    gender_reasoning: str = Field(default="")
    
    socioeconomic_impression: str = Field(
        default="",
        description="What class does this brand project? (working class, middle, upper, etc.)"
    )
    
    occupation_impression: str = Field(
        default="",
        description="What job would this person have? (master craftsman, CEO, artist, etc.)"
    )
    
    lifestyle_impression: str = Field(
        default="",
        description="How does this person live? Hobbies, values, daily life"
    )


# =============================================================================
# CONSUMER ATTRACTION DYNAMICS
# =============================================================================

class ConsumerAttractionDynamics(BaseModel):
    """
    Who is attracted to this brand and why?
    
    This captures the brand-consumer relationship at a deep psychological level.
    """
    
    # Which personality types are drawn to this brand
    attracts_personality_types: List[str] = Field(
        default_factory=list,
        description="What personality types are naturally drawn to this brand"
    )
    
    # Which archetypes (ADAM's consumer archetypes) are attracted
    attracts_archetypes: List[str] = Field(
        default_factory=list,
        description="Consumer archetypes attracted: ACHIEVER, EXPLORER, GUARDIAN, etc."
    )
    archetype_attraction_scores: Dict[str, float] = Field(
        default_factory=dict,
        description="Strength of attraction for each archetype (0-1)"
    )
    
    # Identity needs fulfilled
    identity_needs_fulfilled: List[str] = Field(
        default_factory=list,
        description="What identity needs does buying this brand fulfill?"
    )
    
    # Social signaling
    social_signaling_value: str = Field(
        default="",
        description="What does owning this brand signal to others?"
    )
    
    # Self-concept enhancement
    self_concept_enhancement: str = Field(
        default="",
        description="How does this brand make the buyer feel about themselves?"
    )
    
    # Emotional needs
    emotional_needs_met: List[str] = Field(
        default_factory=list,
        description="What emotional needs does this brand meet?"
    )
    
    # Values alignment
    values_alignment: List[str] = Field(
        default_factory=list,
        description="What values must a consumer hold to be attracted?"
    )


# =============================================================================
# BRAND-CONSUMER RELATIONSHIP
# =============================================================================

class BrandConsumerRelationship(BaseModel):
    """
    The relationship between brand and consumer.
    
    Based on Fournier's (1998) consumer-brand relationship framework.
    """
    
    relationship_role: BrandRelationshipRole = Field(
        default=BrandRelationshipRole.PARTNER,
        description="What role does the brand play in the consumer's life?"
    )
    relationship_role_description: str = Field(
        default="",
        description="Detailed description of the relationship dynamic"
    )
    
    relationship_type: str = Field(
        default="",
        description="committed partnership, casual acquaintance, fling, etc."
    )
    
    emotional_bond_fulfilled: str = Field(
        default="",
        description="What emotional need does this relationship fulfill?"
    )
    
    # Power dynamics
    power_balance: str = Field(
        default="equal",
        description="equal, brand-dominant, consumer-dominant"
    )
    
    # Intimacy level
    intimacy_level: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="How intimate is the brand-consumer relationship?"
    )
    
    # Trust level
    trust_foundation: str = Field(
        default="",
        description="What is the basis of trust? (competence, reliability, shared values)"
    )


# =============================================================================
# BRAND VOICE CHARACTERISTICS
# =============================================================================

class BrandVoiceCharacteristics(BaseModel):
    """
    How the brand speaks and communicates.
    
    Essential for copy generation and messaging alignment.
    """
    
    voice_style: BrandVoiceStyle = Field(
        default=BrandVoiceStyle.CONVERSATIONAL,
        description="Primary voice style"
    )
    
    how_it_speaks: str = Field(
        default="",
        description="Describe how this brand talks to consumers"
    )
    
    vocabulary_style: str = Field(
        default="",
        description="Technical? Casual? Authoritative? Professional?"
    )
    
    emotional_register: str = Field(
        default="",
        description="Warm? Cold? Encouraging? Demanding? Playful?"
    )
    
    communication_values: List[str] = Field(
        default_factory=list,
        description="What values come through in how it communicates?"
    )
    
    # Specific characteristics
    formality: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="0=very casual, 1=very formal"
    )
    
    energy: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="0=calm/measured, 1=high energy/enthusiastic"
    )
    
    humor: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="0=serious, 1=very humorous"
    )
    
    directness: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="0=indirect/subtle, 1=very direct"
    )
    
    # Vocabulary preferences
    preferred_words: List[str] = Field(
        default_factory=list,
        description="Words/phrases this brand would use"
    )
    
    forbidden_words: List[str] = Field(
        default_factory=list,
        description="Words/phrases this brand would never use"
    )


# =============================================================================
# MECHANISM PREFERENCES
# =============================================================================

class BrandMechanismPreferences(BaseModel):
    """
    Which psychological mechanisms align with this brand's personality.
    
    Some mechanisms are more appropriate for certain brand personalities.
    E.g., Scarcity may not fit a brand with high Sincerity.
    """
    
    preferred_mechanisms: List[str] = Field(
        default_factory=list,
        description="Mechanisms that align with brand personality"
    )
    
    mechanism_alignment_scores: Dict[str, float] = Field(
        default_factory=dict,
        description="Alignment score for each mechanism (0-1)"
    )
    
    forbidden_mechanisms: List[str] = Field(
        default_factory=list,
        description="Mechanisms that would damage brand integrity"
    )
    
    mechanism_reasoning: Dict[str, str] = Field(
        default_factory=dict,
        description="Why each mechanism does/doesn't fit"
    )


# =============================================================================
# COMPLETE BRAND PERSONALITY PROFILE
# =============================================================================

class BrandPersonalityProfile(BaseModel):
    """
    Complete Brand-as-Person Psychological Profile.
    
    This is a CORE PRIMITIVE in ADAM - the comprehensive psychological
    profile of a brand treated as if it were a human being.
    
    Usage:
    - Extracted from product pages via DeepProductAnalyzer
    - Stored in Neo4j as Brand nodes
    - Flows through AtomDAG via BrandPersonalityAtom
    - Informs mechanism selection, station matching, copy generation
    - Learnings update effectiveness via Gradient Bridge
    """
    
    # Identity
    brand_id: str = Field(description="Unique brand identifier")
    brand_name: str = Field(description="Brand name")
    
    # Brand Archetype (Jung/Mark)
    brand_archetype: BrandArchetype = Field(
        default=BrandArchetype.EVERYMAN,
        description="Primary brand archetype"
    )
    brand_archetype_confidence: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0
    )
    secondary_archetypes: Dict[str, float] = Field(
        default_factory=dict,
        description="Secondary archetypes with confidence scores"
    )
    archetype_reasoning: str = Field(
        default="",
        description="Why this archetype was assigned"
    )
    
    # Brand Big Five (the brand's personality)
    brand_big_five: BrandBigFive = Field(
        default_factory=BrandBigFive,
        description="Big Five personality of the brand-as-person"
    )
    
    # Aaker Brand Personality
    aaker_personality: AakerBrandPersonality = Field(
        default_factory=AakerBrandPersonality,
        description="Aaker's brand personality dimensions"
    )
    
    # Demographic Impression
    demographic_impression: BrandDemographicImpression = Field(
        default_factory=BrandDemographicImpression,
        description="If the brand were a person, what would they look like?"
    )
    
    # Brand-Consumer Relationship
    consumer_relationship: BrandConsumerRelationship = Field(
        default_factory=BrandConsumerRelationship,
        description="The brand's relationship with consumers"
    )
    
    # Consumer Attraction
    attraction_dynamics: ConsumerAttractionDynamics = Field(
        default_factory=ConsumerAttractionDynamics,
        description="Who is attracted to this brand and why"
    )
    
    # Brand Voice
    voice: BrandVoiceCharacteristics = Field(
        default_factory=BrandVoiceCharacteristics,
        description="How the brand communicates"
    )
    
    # Mechanism Preferences
    mechanism_preferences: BrandMechanismPreferences = Field(
        default_factory=BrandMechanismPreferences,
        description="Which psychological mechanisms fit this brand"
    )
    
    # Additional traits (free-form)
    personality_traits: List[str] = Field(
        default_factory=list,
        description="Additional personality trait descriptors"
    )
    
    identity_claims: List[str] = Field(
        default_factory=list,
        description="What identity/values the brand claims"
    )
    
    # Metadata
    source_product_ids: List[str] = Field(
        default_factory=list,
        description="Products this profile was derived from"
    )
    
    analysis_confidence: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Overall confidence in this profile"
    )
    
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    
    # Learning metadata
    outcome_count: int = Field(
        default=0,
        description="Number of outcomes used to refine this profile"
    )
    effectiveness_by_archetype: Dict[str, float] = Field(
        default_factory=dict,
        description="Learned effectiveness for each consumer archetype"
    )
    
    # =========================================================================
    # METHODS
    # =========================================================================
    
    def get_archetype_compatibility(self, consumer_archetype: str) -> float:
        """
        Get compatibility score between this brand and a consumer archetype.
        
        Returns learned effectiveness if available, else estimates from
        attraction dynamics.
        """
        # First check learned effectiveness
        if consumer_archetype in self.effectiveness_by_archetype:
            return self.effectiveness_by_archetype[consumer_archetype]
        
        # Fall back to attraction dynamics
        if consumer_archetype in self.attraction_dynamics.archetype_attraction_scores:
            return self.attraction_dynamics.archetype_attraction_scores[consumer_archetype]
        
        # Default estimate based on archetype presence in attracts list
        upper_archetype = consumer_archetype.upper()
        for attr_arch in self.attraction_dynamics.attracts_archetypes:
            if attr_arch.upper() == upper_archetype:
                return 0.7  # Present in attracts list
        
        return 0.5  # Neutral
    
    def get_mechanism_fit(self, mechanism: str) -> float:
        """Get how well a mechanism fits this brand's personality."""
        mechanism_lower = mechanism.lower()
        
        # Check forbidden first
        for forbidden in self.mechanism_preferences.forbidden_mechanisms:
            if forbidden.lower() == mechanism_lower:
                return 0.1  # Very low but not zero
        
        # Check alignment scores
        if mechanism_lower in self.mechanism_preferences.mechanism_alignment_scores:
            return self.mechanism_preferences.mechanism_alignment_scores[mechanism_lower]
        
        # Check preferred
        for preferred in self.mechanism_preferences.preferred_mechanisms:
            if preferred.lower() == mechanism_lower:
                return 0.85
        
        return 0.5  # Neutral
    
    def get_voice_vector(self) -> List[float]:
        """Get voice characteristics as a vector for matching."""
        return [
            self.voice.formality,
            self.voice.energy,
            self.voice.humor,
            self.voice.directness,
        ]
    
    def to_neo4j_properties(self) -> Dict[str, Any]:
        """Convert to flat dictionary for Neo4j node properties."""
        return {
            "brand_id": self.brand_id,
            "brand_name": self.brand_name,
            "brand_archetype": self.brand_archetype.value,
            "brand_archetype_confidence": self.brand_archetype_confidence,
            
            # Big Five
            "big_five_openness": self.brand_big_five.openness.score,
            "big_five_conscientiousness": self.brand_big_five.conscientiousness.score,
            "big_five_extraversion": self.brand_big_five.extraversion.score,
            "big_five_agreeableness": self.brand_big_five.agreeableness.score,
            "big_five_neuroticism": self.brand_big_five.neuroticism.score,
            
            # Aaker
            "aaker_sincerity": self.aaker_personality.sincerity.score,
            "aaker_excitement": self.aaker_personality.excitement.score,
            "aaker_competence": self.aaker_personality.competence.score,
            "aaker_sophistication": self.aaker_personality.sophistication.score,
            "aaker_ruggedness": self.aaker_personality.ruggedness.score,
            
            # Demographic
            "description_as_person": self.demographic_impression.description_as_person,
            "age_impression": self.demographic_impression.age_impression,
            "gender_impression": self.demographic_impression.gender_impression.value,
            "socioeconomic_impression": self.demographic_impression.socioeconomic_impression,
            "occupation_impression": self.demographic_impression.occupation_impression,
            
            # Relationship
            "relationship_role": self.consumer_relationship.relationship_role.value,
            "emotional_bond": self.consumer_relationship.emotional_bond_fulfilled,
            
            # Voice
            "voice_style": self.voice.voice_style.value,
            "voice_formality": self.voice.formality,
            "voice_energy": self.voice.energy,
            "voice_humor": self.voice.humor,
            "voice_directness": self.voice.directness,
            "how_it_speaks": self.voice.how_it_speaks,
            
            # Social
            "social_signal": self.attraction_dynamics.social_signaling_value,
            "self_concept_enhancement": self.attraction_dynamics.self_concept_enhancement,
            
            # Metadata
            "analysis_confidence": self.analysis_confidence,
            "outcome_count": self.outcome_count,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to full dictionary."""
        return {
            "brand_id": self.brand_id,
            "brand_name": self.brand_name,
            "brand_archetype": self.brand_archetype.value,
            "brand_archetype_confidence": self.brand_archetype_confidence,
            "secondary_archetypes": self.secondary_archetypes,
            "brand_big_five": {
                "openness": self.brand_big_five.openness.score,
                "conscientiousness": self.brand_big_five.conscientiousness.score,
                "extraversion": self.brand_big_five.extraversion.score,
                "agreeableness": self.brand_big_five.agreeableness.score,
                "neuroticism": self.brand_big_five.neuroticism.score,
            },
            "aaker_personality": self.aaker_personality.to_dict(),
            "demographic_impression": {
                "description_as_person": self.demographic_impression.description_as_person,
                "age_impression": self.demographic_impression.age_impression,
                "gender_impression": self.demographic_impression.gender_impression.value,
                "occupation_impression": self.demographic_impression.occupation_impression,
            },
            "consumer_relationship": {
                "role": self.consumer_relationship.relationship_role.value,
                "emotional_bond": self.consumer_relationship.emotional_bond_fulfilled,
            },
            "attraction_dynamics": {
                "attracts_archetypes": self.attraction_dynamics.attracts_archetypes,
                "social_signal": self.attraction_dynamics.social_signaling_value,
                "self_concept_enhancement": self.attraction_dynamics.self_concept_enhancement,
            },
            "voice": {
                "style": self.voice.voice_style.value,
                "how_it_speaks": self.voice.how_it_speaks,
                "formality": self.voice.formality,
                "energy": self.voice.energy,
            },
            "mechanism_preferences": {
                "preferred": self.mechanism_preferences.preferred_mechanisms,
                "forbidden": self.mechanism_preferences.forbidden_mechanisms,
            },
            "analysis_confidence": self.analysis_confidence,
        }


# =============================================================================
# COMPATIBILITY FUNCTIONS
# =============================================================================

def compute_brand_user_compatibility(
    brand_profile: BrandPersonalityProfile,
    user_big_five: Dict[str, float],
    user_archetype: str,
) -> Tuple[float, Dict[str, float]]:
    """
    Compute compatibility between a brand and a user.
    
    Returns:
        Tuple of (overall_score, component_scores)
    """
    scores = {}
    
    # 1. Archetype compatibility (40% weight)
    archetype_score = brand_profile.get_archetype_compatibility(user_archetype)
    scores["archetype_compatibility"] = archetype_score
    
    # 2. Personality compatibility (30% weight)
    # Compare brand Big Five to user Big Five
    brand_b5 = brand_profile.brand_big_five.to_dict()
    personality_diff = 0.0
    for trait in ["openness", "conscientiousness", "extraversion", "agreeableness"]:
        if trait in user_big_five:
            diff = abs(brand_b5.get(trait, 0.5) - user_big_five[trait])
            personality_diff += diff
    # Neuroticism is inverted - low brand neuroticism matches any user
    personality_score = 1.0 - (personality_diff / 4.0)
    scores["personality_compatibility"] = personality_score
    
    # 3. Identity alignment (20% weight)
    # Based on attraction dynamics
    identity_score = 0.5
    if brand_profile.attraction_dynamics.attracts_archetypes:
        if user_archetype.upper() in [a.upper() for a in brand_profile.attraction_dynamics.attracts_archetypes]:
            identity_score = 0.8
    scores["identity_alignment"] = identity_score
    
    # 4. Relationship fit (10% weight)
    # Some archetypes prefer certain relationship roles
    relationship_fit = 0.5
    role = brand_profile.consumer_relationship.relationship_role
    archetype_upper = user_archetype.upper()
    
    # Achievers like mentors and admired experts
    if archetype_upper in ["ACHIEVER", "ACHIEVEMENT_DRIVEN"]:
        if role in [BrandRelationshipRole.MENTOR, BrandRelationshipRole.ADMIRED_EXPERT]:
            relationship_fit = 0.8
    # Explorers like enablers and inspiring leaders
    elif archetype_upper in ["EXPLORER", "NOVELTY_SEEKER"]:
        if role in [BrandRelationshipRole.ENABLER, BrandRelationshipRole.INSPIRING_LEADER]:
            relationship_fit = 0.8
    # Guardians like protective guardians and trusted advisors
    elif archetype_upper in ["GUARDIAN", "SECURITY_SEEKER"]:
        if role in [BrandRelationshipRole.PROTECTIVE_GUARDIAN, BrandRelationshipRole.TRUSTED_ADVISOR]:
            relationship_fit = 0.8
    
    scores["relationship_fit"] = relationship_fit
    
    # Combine with weights
    overall = (
        archetype_score * 0.40 +
        personality_score * 0.30 +
        identity_score * 0.20 +
        relationship_fit * 0.10
    )
    
    return overall, scores
