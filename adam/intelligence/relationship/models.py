"""
Consumer-Brand Relationship Models
==================================

Core data models for the 5-Channel Consumer-Brand Relationship Detection System.

This module provides:
- ObservationChannel: The 5 channels through which relationships are observed
- RelationshipType: The 17+ relationship types between consumers and brands
- LanguagePattern: Validated linguistic patterns for relationship detection
- RelationshipSignal: Detected signals from text analysis
- ConsumerBrandRelationship: Full relationship profile between consumer and brand

Based on validated academic scales including:
- Escalas & Bettman (2003) Self-Brand Connection Scale
- Thomson, MacInnis & Park (2005) Brand Attachment Scale
- Park et al. (2010) Brand Attachment
- Taute & Sierra (2014) Brand Tribalism Scale
- Carroll & Ahuvia (2006) Brand Love Scale
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set, Any, ClassVar
from enum import Enum
from pydantic import BaseModel, Field
import re


# =============================================================================
# OBSERVATION CHANNELS (5-Channel Taxonomy)
# =============================================================================

class ObservationChannel(str, Enum):
    """
    The 5 channels through which consumer-brand relationships are observed.
    
    Channels 1-4 are INPUT channels (we detect relationships from these).
    Channel 5 is the OUTPUT channel (we generate recommendations for this).
    """
    CUSTOMER_REVIEWS = "customer_reviews"
    SOCIAL_SIGNALS = "social_signals"
    SELF_EXPRESSION = "self_expression"
    BRAND_POSITIONING = "brand_positioning"
    ADVERTISING = "advertising"  # OUTPUT channel


class ChannelRole(str, Enum):
    """Whether channel is input (detection) or output (recommendation)."""
    INPUT_DETECTION = "input_detection"
    OUTPUT_RECOMMENDATION = "output_recommendation"


# =============================================================================
# RELATIONSHIP CATEGORIES
# =============================================================================

class RelationshipCategory(str, Enum):
    """High-level categories of consumer-brand relationships."""
    SELF_DEFINITION = "self_definition"        # Brand integrated into self-concept
    SOCIAL_SIGNALING = "social_signaling"      # Brand for external communication
    SOCIAL_BELONGING = "social_belonging"      # Brand for group membership
    EMOTIONAL_BOND = "emotional_bond"          # Deep emotional connection
    FUNCTIONAL_UTILITY = "functional_utility"  # Practical, low-emotion
    GUIDANCE_AUTHORITY = "guidance_authority"  # Brand as expert/mentor
    THERAPEUTIC_ESCAPE = "therapeutic_escape"  # Comfort and stress relief
    TEMPORAL_NOSTALGIC = "temporal_nostalgic"  # Connection through time
    ASPIRATIONAL = "aspirational"              # Future-self projection
    NEGATIVE = "negative"                      # Hostile relationship


class RelationalModel(str, Enum):
    """Fiske's Relational Models Theory applied to consumer-brand relationships."""
    COMMUNAL_SHARING = "communal_sharing"      # We-ness, shared identity
    AUTHORITY_RANKING = "authority_ranking"    # Hierarchy, expertise
    EQUALITY_MATCHING = "equality_matching"    # Balanced reciprocity
    MARKET_PRICING = "market_pricing"          # Transactional, rational
    NEGATIVE_COMMUNAL = "negative_communal"    # Anti-brand community


# =============================================================================
# RELATIONSHIP TYPES (17+ Types from Research Synthesis)
# =============================================================================

class RelationshipTypeId(str, Enum):
    """Identifiers for the 52 consumer-brand relationship types."""
    # ==========================================================================
    # SELF-DEFINITION CATEGORY
    # Brand integrated into self-concept
    # ==========================================================================
    SELF_IDENTITY_CORE = "self_identity_core"
    SELF_EXPRESSION_VEHICLE = "self_expression_vehicle"
    COMPARTMENTALIZED_IDENTITY = "compartmentalized_identity"
    
    # ==========================================================================
    # SOCIAL SIGNALING CATEGORY
    # Brand for external communication
    # ==========================================================================
    STATUS_MARKER = "status_marker"
    SOCIAL_COMPLIANCE = "social_compliance"
    
    # ==========================================================================
    # SOCIAL BELONGING CATEGORY
    # Brand for group membership
    # ==========================================================================
    TRIBAL_BADGE = "tribal_badge"
    CHAMPION_EVANGELIST = "champion_evangelist"
    
    # ==========================================================================
    # EMOTIONAL BOND CATEGORY
    # Deep emotional connection
    # ==========================================================================
    COMMITTED_PARTNERSHIP = "committed_partnership"
    DEPENDENCY = "dependency"
    FLING = "fling"
    SECRET_AFFAIR = "secret_affair"
    GUILTY_PLEASURE = "guilty_pleasure"
    RESCUE_SAVIOR = "rescue_savior"
    
    # ==========================================================================
    # FUNCTIONAL UTILITY CATEGORY
    # Practical, low-emotion
    # ==========================================================================
    RELIABLE_TOOL = "reliable_tool"
    BEST_FRIEND_UTILITY = "best_friend_utility"
    
    # ==========================================================================
    # GUIDANCE/AUTHORITY CATEGORY
    # Brand as expert/mentor
    # ==========================================================================
    MENTOR = "mentor"
    CAREGIVER = "caregiver"
    
    # ==========================================================================
    # THERAPEUTIC/ESCAPE CATEGORY
    # Comfort and stress relief
    # ==========================================================================
    COMFORT_COMPANION = "comfort_companion"
    ESCAPE_ARTIST = "escape_artist"
    
    # ==========================================================================
    # TEMPORAL/NOSTALGIC CATEGORY
    # Connection through time
    # ==========================================================================
    CHILDHOOD_FRIEND = "childhood_friend"
    SEASONAL_REKINDLER = "seasonal_rekindler"
    
    # ==========================================================================
    # ASPIRATIONAL CATEGORY
    # Future-self projection
    # ==========================================================================
    ASPIRATIONAL_ICON = "aspirational_icon"
    
    # ==========================================================================
    # ACQUISITION/EXPLORATION CATEGORY
    # Pre-commitment stages
    # ==========================================================================
    COURTSHIP_DATING = "courtship_dating"
    REBOUND_RELATIONSHIP = "rebound_relationship"
    
    # ==========================================================================
    # NEGATIVE/TRAPPED CATEGORY
    # Hostile or resentful relationships
    # ==========================================================================
    ENEMY = "enemy"
    EX_RELATIONSHIP = "ex_relationship"
    CAPTIVE_ENSLAVEMENT = "captive_enslavement"
    RELUCTANT_USER = "reluctant_user"
    
    # ==========================================================================
    # GUILT AND OBLIGATION CATEGORY (NEW - Fournier Extension)
    # Relationships maintained through psychological pressure
    # ==========================================================================
    ACCOUNTABILITY_CAPTOR = "accountability_captor"      # Duolingo owl effect - guilt/streak anxiety
    SUBSCRIPTION_CONSCIENCE = "subscription_conscience"  # Guilt about unused subscriptions
    
    # ==========================================================================
    # RITUAL AND TEMPORAL CATEGORY (NEW - Fournier Extension)
    # Relationships embedded in symbolic behavior and time
    # ==========================================================================
    SACRED_PRACTICE = "sacred_practice"    # Morning coffee ritual, skincare sanctuary
    TEMPORAL_MARKER = "temporal_marker"    # Brand marks life milestones/anniversaries
    
    # ==========================================================================
    # GRIEF AND LOSS CATEGORY (NEW - Fournier Extension)
    # Relationships defined by mourning and betrayal
    # ==========================================================================
    MOURNING_BOND = "mourning_bond"        # Grieving discontinued products
    FORMULA_BETRAYAL = "formula_betrayal"  # Anger at changed formulas/recipes
    
    # ==========================================================================
    # SALVATION AND REDEMPTION CATEGORY (NEW - Fournier Extension)
    # Brands that saved/transformed the consumer
    # ==========================================================================
    LIFE_RAFT = "life_raft"                # Brand rescued during crisis (breakup, illness)
    TRANSFORMATION_AGENT = "transformation_agent"  # Brand fundamentally changed who they are
    
    # ==========================================================================
    # COGNITIVE DEPENDENCY CATEGORY (NEW - Fournier Extension)
    # Brands as extensions of mind/capability
    # ==========================================================================
    SECOND_BRAIN = "second_brain"          # Notion/productivity tools as cognitive extension
    PLATFORM_LOCK_IN = "platform_lock_in"  # Rational choice + identity around ecosystem
    
    # ==========================================================================
    # TRIBAL AND IDENTITY CATEGORY (NEW - Fournier Extension)
    # Complex group/family/anti-identity dynamics
    # ==========================================================================
    TRIBAL_SIGNAL = "tribal_signal"        # Jeep Wave, Tesla Smile - recognition protocols
    INHERITED_LEGACY = "inherited_legacy"  # Generational loyalty ("my father's brand")
    IDENTITY_NEGATION = "identity_negation"  # Anti-consumption defining who you're NOT
    WORKSPACE_CULTURE = "workspace_culture"  # Team/org identity through shared tools
    
    # ==========================================================================
    # COLLECTOR AND QUEST CATEGORY (NEW - Fournier Extension)
    # Relationships defined by pursuit and completion
    # ==========================================================================
    GRAIL_QUEST = "grail_quest"            # Holy grail product pursuit
    COMPLETION_SEEKER = "completion_seeker"  # Project Pan - relationship through finishing
    
    # ==========================================================================
    # TRUST AND INTIMACY CATEGORY (NEW - Fournier Extension)
    # Relationships requiring deep vulnerability
    # ==========================================================================
    FINANCIAL_INTIMATE = "financial_intimate"  # Apps with access to sensitive financial data
    THERAPIST_PROVIDER = "therapist_provider"  # Barber/stylist as emotional confidant
    
    # ==========================================================================
    # INSIDER AND COMPLICITY CATEGORY (NEW - Fournier Extension)
    # Relationships built on exclusive knowledge/co-creation
    # ==========================================================================
    INSIDER_COMPACT = "insider_compact"    # IYKYK gatekeeping dynamics
    CO_CREATOR = "co_creator"              # Glossier model - active partner in brand
    
    # ==========================================================================
    # VALUES AND PERMISSION CATEGORY (NEW - Fournier Extension)
    # Brands that validate identity/choices
    # ==========================================================================
    ETHICAL_VALIDATOR = "ethical_validator"    # Moral permission through purchase
    STATUS_ARBITER = "status_arbiter"          # Access to otherwise unavailable social spheres
    COMPETENCE_VALIDATOR = "competence_validator"  # Confirms consumer made smart choice
    
    # ==========================================================================
    # META AND IRONIC CATEGORY (NEW - Fournier Extension)
    # Self-aware critical engagement
    # ==========================================================================
    IRONIC_AWARE = "ironic_aware"          # r/HailCorporate - critical distance while engaging


class RelationshipStrength(str, Enum):
    """Strength levels for consumer-brand relationships."""
    WEAK = "weak"              # 1-2: Low engagement, easily switchable
    MODERATE = "moderate"      # 3: Meaningful but not defining
    STRONG = "strong"          # 4: Important relationship
    VERY_STRONG = "very_strong"  # 5: Core part of identity


# =============================================================================
# LANGUAGE PATTERN MODELS
# =============================================================================

class LinguisticMarkerType(str, Enum):
    """Types of linguistic markers that indicate relationship patterns."""
    # Core markers
    IDENTITY_INTEGRATION = "identity_integration"    # "I am a X person"
    VALUE_ALIGNMENT = "value_alignment"              # "They share my values"
    EMOTIONAL_ATTACHMENT = "emotional_attachment"    # "I love this brand"
    TRIBAL_MEMBERSHIP = "tribal_membership"          # "Fellow X owners"
    STATUS_DISPLAY = "status_display"                # "People notice when..."
    DEPENDENCY = "dependency"                        # "Can't live without"
    NOSTALGIA = "nostalgia"                         # "Reminds me of..."
    EXPERTISE = "expertise"                          # "They taught me..."
    FUNCTIONAL = "functional"                        # "Works as expected"
    HOSTILE = "hostile"                             # "Never again"
    
    # Expanded relationship markers
    EVANGELISM = "evangelism"                        # "I tell everyone about..."
    GUILT_SHAME = "guilt_shame"                      # "My guilty pleasure..."
    RESCUE_GRATITUDE = "rescue_gratitude"            # "Saved my life/business..."
    EXPLORATION_TRIAL = "exploration_trial"          # "Trying out...", "First time..."
    REBOUND_REJECTION = "rebound_rejection"          # "Switched from...", "After X disappointed..."
    ENTRAPMENT = "entrapment"                        # "No choice...", "Stuck with..."
    RELUCTANCE = "reluctance"                        # "Have to use...", "Only option..."
    PEER_CONFORMITY = "peer_conformity"              # "Everyone uses...", "Pressure to..."
    CONTEXT_SPECIFIC = "context_specific"            # "For work I use...", "When I'm [role]..."
    SEASONAL_TEMPORAL = "seasonal_temporal"          # "Every [season]...", "Annual tradition..."
    
    # ==========================================================================
    # NEW FOURNIER EXTENSION MARKERS
    # ==========================================================================
    # Guilt and Obligation
    STREAK_ANXIETY = "streak_anxiety"                # "Broke my streak", "Duo owl"
    SUBSCRIPTION_GUILT = "subscription_guilt"        # "Paying but not using"
    
    # Ritual and Temporal
    RITUAL_SACRED = "ritual_sacred"                  # "My ritual", "sacred", "sanctuary"
    MILESTONE_MARKER = "milestone_marker"            # "Where we got engaged", "graduation"
    
    # Grief and Loss
    PRODUCT_GRIEF = "product_grief"                  # "Devastated", "mourning", "RIP"
    FORMULA_ANGER = "formula_anger"                  # "They changed it", "not the same"
    
    # Salvation and Redemption
    CRISIS_RESCUE = "crisis_rescue"                  # "Got me through", "saved me during"
    TRANSFORMATION = "transformation"                # "Changed my life", "I'm different now"
    
    # Cognitive Dependency
    COGNITIVE_EXTENSION = "cognitive_extension"      # "Second brain", "extension of my mind"
    ECOSYSTEM_LOCK = "ecosystem_lock"                # "Stuck with the platform", "batteries"
    
    # Tribal and Identity
    RECOGNITION_PROTOCOL = "recognition_protocol"    # "The wave", "we acknowledge each other"
    GENERATIONAL = "generational"                    # "My father's brand", "passed down"
    ANTI_CONSUMPTION = "anti_consumption"            # "Refuse to buy", "against consumerism"
    TEAM_CULTURE = "team_culture"                    # "Our team uses", "we run on"
    
    # Collector and Quest
    GRAIL_PURSUIT = "grail_pursuit"                  # "Holy grail", "endgame", "the one"
    COMPLETION_DRIVE = "completion_drive"            # "Finally finished", "panned", "emptied"
    
    # Trust and Intimacy
    FINANCIAL_TRUST = "financial_trust"              # "Trust with my money", "sensitive data"
    EMOTIONAL_CONFIDANT = "emotional_confidant"      # "Tells me everything", "like therapy"
    
    # Insider and Complicity
    GATEKEEPING = "gatekeeping"                      # "IYKYK", "not for everyone"
    CO_CREATION = "co_creation"                      # "We built this together", "community created"
    
    # Values and Permission
    ETHICAL_PERMISSION = "ethical_permission"        # "Feel good buying", "guilt-free"
    ACCESS_PROVIDER = "access_provider"              # "Got me in", "opened doors"
    SMART_CHOICE = "smart_choice"                    # "Research proved", "I chose wisely"
    
    # Meta and Ironic
    META_AWARENESS = "meta_awareness"                # "I know I'm being marketed to", "ironic"


class LanguagePattern(BaseModel):
    """
    A validated linguistic pattern for detecting relationship types.
    
    Patterns are derived from validated academic scales and weighted
    by channel context for accurate detection.
    """
    pattern_id: str = Field(description="Unique pattern identifier")
    pattern_text: str = Field(description="Human-readable pattern description")
    pattern_regex: str = Field(description="Regex for pattern matching")
    examples: List[str] = Field(default_factory=list, description="Example phrases")
    
    relationship_type: RelationshipTypeId = Field(description="Target relationship type")
    marker_type: LinguisticMarkerType = Field(description="Type of linguistic marker")
    
    base_weight: float = Field(default=0.8, ge=0.0, le=1.0, description="Base detection weight")
    
    # Channel-specific weights
    channel_weights: Dict[ObservationChannel, float] = Field(
        default_factory=dict,
        description="Weight multipliers by observation channel"
    )
    
    # Validation source
    validated_source: Optional[str] = Field(default=None, description="Academic scale citation")
    cronbachs_alpha: Optional[float] = Field(default=None, description="Reliability coefficient")
    
    def get_weight_for_channel(self, channel: ObservationChannel) -> float:
        """Get the pattern weight adjusted for a specific channel."""
        multiplier = self.channel_weights.get(channel, 1.0)
        return self.base_weight * multiplier
    
    def matches(self, text: str) -> bool:
        """Check if text matches this pattern."""
        return bool(re.search(self.pattern_regex, text.lower()))
    
    def match_confidence(self, text: str, channel: ObservationChannel) -> float:
        """Get match confidence for text in a specific channel."""
        if not self.matches(text):
            return 0.0
        return self.get_weight_for_channel(channel)


# =============================================================================
# RELATIONSHIP TYPE DEFINITION
# =============================================================================

class RelationshipTypeDefinition(BaseModel):
    """
    Complete definition of a consumer-brand relationship type.
    """
    type_id: RelationshipTypeId
    type_name: str
    category: RelationshipCategory
    relational_model: RelationalModel
    
    definition: str = Field(description="Full definition of this relationship type")
    distinguishing_features: List[str] = Field(default_factory=list)
    
    # Strength characteristics
    typical_strength_range: tuple = Field(default=(RelationshipStrength.MODERATE, RelationshipStrength.STRONG))
    vulnerability_to_dissolution: str = Field(default="moderate")
    
    # Detection configuration
    primary_detection_channel: ObservationChannel
    secondary_detection_channels: List[ObservationChannel] = Field(default_factory=list)
    
    # Associated patterns (populated at runtime)
    language_patterns: List[str] = Field(default_factory=list, description="Pattern IDs")
    
    # Compatible archetypes
    compatible_archetypes: List[str] = Field(default_factory=list)
    
    # Recommended engagement strategies
    engagement_strategies: List[str] = Field(default_factory=list)
    
    # Ad creative templates
    ad_templates: List[str] = Field(default_factory=list)
    
    # Mechanism compatibility (for AtomDAG integration)
    compatible_mechanisms: List[str] = Field(default_factory=list)
    
    def to_neo4j_properties(self) -> Dict[str, Any]:
        """Convert to Neo4j node properties."""
        return {
            "type_id": self.type_id.value,
            "type_name": self.type_name,
            "category": self.category.value,
            "relational_model": self.relational_model.value,
            "definition": self.definition,
            "distinguishing_features": self.distinguishing_features,
            "vulnerability_to_dissolution": self.vulnerability_to_dissolution,
            "primary_detection_channel": self.primary_detection_channel.value,
            "secondary_detection_channels": [c.value for c in self.secondary_detection_channels],
            "compatible_archetypes": self.compatible_archetypes,
            "compatible_mechanisms": self.compatible_mechanisms,
        }


# =============================================================================
# SIGNAL MODELS
# =============================================================================

class RelationshipSignal(BaseModel):
    """
    A detected signal indicating a consumer-brand relationship.
    """
    signal_id: str
    channel: ObservationChannel
    source_text: str
    source_id: Optional[str] = None  # Review ID, post ID, etc.
    
    # Detection results
    matched_patterns: List[str] = Field(default_factory=list, description="Pattern IDs that matched")
    relationship_type: RelationshipTypeId
    confidence: float = Field(ge=0.0, le=1.0)
    
    # Context
    brand_id: Optional[str] = None
    consumer_id: Optional[str] = None
    detected_at: Optional[str] = None
    
    # Extracted features
    emotional_intensity: float = Field(default=0.5, ge=0.0, le=1.0)
    identity_integration: float = Field(default=0.0, ge=0.0, le=1.0)
    social_display: float = Field(default=0.0, ge=0.0, le=1.0)
    
    def to_neo4j_properties(self) -> Dict[str, Any]:
        """Convert to Neo4j node properties."""
        return {
            "signal_id": self.signal_id,
            "channel": self.channel.value,
            "source_text": self.source_text[:500],  # Truncate for storage
            "source_id": self.source_id,
            "relationship_type": self.relationship_type.value,
            "confidence": self.confidence,
            "brand_id": self.brand_id,
            "consumer_id": self.consumer_id,
            "detected_at": self.detected_at,
            "emotional_intensity": self.emotional_intensity,
            "identity_integration": self.identity_integration,
            "social_display": self.social_display,
        }


# =============================================================================
# CONSUMER-BRAND RELATIONSHIP PROFILE
# =============================================================================

class ConsumerBrandRelationship(BaseModel):
    """
    Complete relationship profile between a consumer and a brand.
    
    This is the primary output of the relationship detection system,
    aggregating signals across all channels into a unified profile.
    """
    relationship_id: str
    brand_id: str
    consumer_id: Optional[str] = None  # Optional for aggregate analysis
    
    # Primary detected relationship
    primary_relationship_type: RelationshipTypeId
    primary_confidence: float = Field(ge=0.0, le=1.0)
    
    # Secondary relationships (often multiple apply)
    secondary_relationships: Dict[RelationshipTypeId, float] = Field(
        default_factory=dict,
        description="Other detected relationships with confidence scores"
    )
    
    # Overall relationship strength
    strength: RelationshipStrength
    strength_score: float = Field(ge=0.0, le=1.0)
    
    # Channel-specific scores (how much evidence from each channel)
    channel_evidence: Dict[ObservationChannel, float] = Field(default_factory=dict)
    
    # Aggregated signals
    signals: List[str] = Field(default_factory=list, description="Signal IDs")
    signal_count: int = 0
    
    # Derived characteristics
    emotional_intensity: float = Field(default=0.5, ge=0.0, le=1.0)
    identity_integration: float = Field(default=0.0, ge=0.0, le=1.0)
    social_function: float = Field(default=0.0, ge=0.0, le=1.0)
    functional_orientation: float = Field(default=0.0, ge=0.0, le=1.0)
    
    # Relationship dynamics
    vulnerability_to_dissolution: str = Field(default="moderate")
    predicted_loyalty: float = Field(default=0.5, ge=0.0, le=1.0)
    advocacy_likelihood: float = Field(default=0.5, ge=0.0, le=1.0)
    
    # Recommended engagement
    recommended_engagement_strategy: Optional[str] = None
    recommended_ad_templates: List[str] = Field(default_factory=list)
    recommended_mechanisms: List[str] = Field(default_factory=list)
    
    # Metadata
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    analysis_version: str = "2.0"
    
    def get_engagement_tone(self) -> str:
        """Get recommended messaging tone based on relationship type."""
        tone_map = {
            RelationshipTypeId.SELF_IDENTITY_CORE: "affirming, heritage-focused, celebratory",
            RelationshipTypeId.SELF_EXPRESSION_VEHICLE: "authentic, expressive, value-aligned",
            RelationshipTypeId.STATUS_MARKER: "exclusive, premium, aspirational",
            RelationshipTypeId.TRIBAL_BADGE: "inclusive to tribe, insider language",
            RelationshipTypeId.COMMITTED_PARTNERSHIP: "warm, appreciative, partnership-oriented",
            RelationshipTypeId.DEPENDENCY: "reassuring, always-there, reliable",
            RelationshipTypeId.RELIABLE_TOOL: "clear, confident, no-nonsense",
            RelationshipTypeId.MENTOR: "expert, educational, helpful",
            RelationshipTypeId.COMFORT_COMPANION: "warm, soothing, gentle",
            RelationshipTypeId.CHILDHOOD_FRIEND: "nostalgic, familiar, comforting",
            RelationshipTypeId.ASPIRATIONAL_ICON: "inspirational, achievable dream",
            RelationshipTypeId.ENEMY: "acknowledge issue, rebuild trust",
        }
        return tone_map.get(self.primary_relationship_type, "warm, engaging")
    
    def get_messaging_avoid_list(self) -> List[str]:
        """Get list of messaging approaches to avoid for this relationship."""
        avoid_map = {
            RelationshipTypeId.SELF_IDENTITY_CORE: ["trying to change them", "aggressive CTAs"],
            RelationshipTypeId.STATUS_MARKER: ["discount messaging", "mass market imagery"],
            RelationshipTypeId.TRIBAL_BADGE: ["mass market appeal", "generic messaging"],
            RelationshipTypeId.COMMITTED_PARTNERSHIP: ["acquisition messaging", "hard sells"],
            RelationshipTypeId.RELIABLE_TOOL: ["emotional appeals", "identity messaging"],
            RelationshipTypeId.MENTOR: ["salesy pitches", "condescending tone"],
            RelationshipTypeId.COMFORT_COMPANION: ["urgent CTAs", "anxiety-inducing content"],
        }
        return avoid_map.get(self.primary_relationship_type, [])
    
    def to_neo4j_properties(self) -> Dict[str, Any]:
        """Convert to Neo4j node properties."""
        return {
            "relationship_id": self.relationship_id,
            "brand_id": self.brand_id,
            "consumer_id": self.consumer_id,
            "primary_relationship_type": self.primary_relationship_type.value,
            "primary_confidence": self.primary_confidence,
            "strength": self.strength.value,
            "strength_score": self.strength_score,
            "emotional_intensity": self.emotional_intensity,
            "identity_integration": self.identity_integration,
            "social_function": self.social_function,
            "functional_orientation": self.functional_orientation,
            "vulnerability_to_dissolution": self.vulnerability_to_dissolution,
            "predicted_loyalty": self.predicted_loyalty,
            "advocacy_likelihood": self.advocacy_likelihood,
            "recommended_engagement_strategy": self.recommended_engagement_strategy,
            "signal_count": self.signal_count,
        }


# =============================================================================
# RELATIONSHIP-TO-MECHANISM MAPPING
# =============================================================================

# Maps relationship types to effective psychological mechanisms
RELATIONSHIP_MECHANISM_MAP: Dict[RelationshipTypeId, List[str]] = {
    # ==========================================================================
    # SELF-DEFINITION CATEGORY
    # ==========================================================================
    RelationshipTypeId.SELF_IDENTITY_CORE: [
        "self_expression",
        "identity_affirmation", 
        "symbolic_self_completion",
        "narrative_transportation",
    ],
    RelationshipTypeId.SELF_EXPRESSION_VEHICLE: [
        "self_expression",
        "aesthetic_appeal",
        "value_expression",
        "social_identity",
    ],
    RelationshipTypeId.COMPARTMENTALIZED_IDENTITY: [
        "context_reinforcement",
        "role_specific_appeal",
        "situational_relevance",
        "identity_facet_support",
    ],
    
    # ==========================================================================
    # SOCIAL SIGNALING CATEGORY
    # ==========================================================================
    RelationshipTypeId.STATUS_MARKER: [
        "social_proof",
        "scarcity",
        "authority",
        "costly_signaling",
    ],
    RelationshipTypeId.SOCIAL_COMPLIANCE: [
        "personal_value_demonstration",
        "genuine_preference_building",
        "intrinsic_motivation",
        "autonomy_support",
    ],
    
    # ==========================================================================
    # SOCIAL BELONGING CATEGORY
    # ==========================================================================
    RelationshipTypeId.TRIBAL_BADGE: [
        "social_identity",
        "in_group_bias",
        "communal_sharing",
        "commitment_consistency",
    ],
    RelationshipTypeId.CHAMPION_EVANGELIST: [
        "recognition",
        "exclusive_access",
        "co_creation",
        "ambassador_empowerment",
        "insider_status",
    ],
    
    # ==========================================================================
    # EMOTIONAL BOND CATEGORY
    # ==========================================================================
    RelationshipTypeId.COMMITTED_PARTNERSHIP: [
        "reciprocity",
        "commitment_consistency",
        "emotional_appeal",
        "trust_building",
    ],
    RelationshipTypeId.DEPENDENCY: [
        "loss_aversion",
        "endowment_effect",
        "habit_formation",
        "fear_appeal",
    ],
    RelationshipTypeId.GUILTY_PLEASURE: [
        "normalization",
        "permission_giving",
        "private_indulgence",
        "judgment_free_messaging",
    ],
    RelationshipTypeId.RESCUE_SAVIOR: [
        "narrative_transportation",
        "testimonial_amplification",
        "transformation_story",
        "gratitude_reinforcement",
    ],
    
    # ==========================================================================
    # FUNCTIONAL UTILITY CATEGORY
    # ==========================================================================
    RelationshipTypeId.RELIABLE_TOOL: [
        "problem_solution",
        "rational_appeal",
        "demonstration",
        "comparison",
    ],
    
    # ==========================================================================
    # GUIDANCE/AUTHORITY CATEGORY
    # ==========================================================================
    RelationshipTypeId.MENTOR: [
        "authority",
        "expertise_appeal",
        "educational_content",
        "trust_building",
    ],
    
    # ==========================================================================
    # THERAPEUTIC/ESCAPE CATEGORY
    # ==========================================================================
    RelationshipTypeId.COMFORT_COMPANION: [
        "emotional_appeal",
        "sensory_appeal",
        "stress_relief",
        "self_care",
    ],
    
    # ==========================================================================
    # TEMPORAL/NOSTALGIC CATEGORY
    # ==========================================================================
    RelationshipTypeId.CHILDHOOD_FRIEND: [
        "nostalgia",
        "narrative_transportation",
        "emotional_appeal",
        "familiarity",
    ],
    RelationshipTypeId.SEASONAL_REKINDLER: [
        "anticipation_building",
        "tradition_reinforcement",
        "temporal_priming",
        "seasonal_nostalgia",
    ],
    
    # ==========================================================================
    # ASPIRATIONAL CATEGORY
    # ==========================================================================
    RelationshipTypeId.ASPIRATIONAL_ICON: [
        "aspiration",
        "future_self",
        "social_proof",
        "transformation",
    ],
    
    # ==========================================================================
    # ACQUISITION/EXPLORATION CATEGORY
    # ==========================================================================
    RelationshipTypeId.COURTSHIP_DATING: [
        "social_proof",
        "risk_reduction",
        "demonstration",
        "trial_offer",
        "credibility_building",
    ],
    RelationshipTypeId.REBOUND_RELATIONSHIP: [
        "positive_affirmation",
        "unique_value_demonstration",
        "differentiation",
        "avoid_comparison",
    ],
    
    # ==========================================================================
    # NEGATIVE/TRAPPED CATEGORY
    # ==========================================================================
    RelationshipTypeId.ENEMY: [
        "acknowledgment",
        "apology",
        "trust_rebuilding",
        "overcompensation",
    ],
    RelationshipTypeId.CAPTIVE_ENSLAVEMENT: [
        "value_demonstration",
        "surprise_delight",
        "friction_reduction",
        "gratitude_expression",
    ],
    RelationshipTypeId.RELUCTANT_USER: [
        "value_perception_improvement",
        "quality_demonstration",
        "expectation_exceeding",
        "reframing",
    ],
    
    # ==========================================================================
    # ADDITIONAL RELATIONSHIP TYPES (Complete Coverage)
    # ==========================================================================
    RelationshipTypeId.FLING: [
        "excitement",
        "novelty",
        "spontaneity",
        "limited_time_offer",
    ],
    RelationshipTypeId.SECRET_AFFAIR: [
        "discretion",
        "privacy_respect",
        "exclusive_access",
        "judgment_free",
    ],
    RelationshipTypeId.BEST_FRIEND_UTILITY: [
        "reliability",
        "trust_building",
        "problem_solution",
        "everyday_support",
    ],
    RelationshipTypeId.CAREGIVER: [
        "nurturing",
        "protection",
        "reassurance",
        "safety",
    ],
    RelationshipTypeId.ESCAPE_ARTIST: [
        "escapism",
        "fantasy",
        "stress_relief",
        "transformation",
    ],
    RelationshipTypeId.EX_RELATIONSHIP: [
        "acknowledgment",
        "win_back",
        "improvement_demonstration",
        "second_chance",
    ],
    
    # ==========================================================================
    # FOURNIER EXTENSION: GUILT AND OBLIGATION CATEGORY
    # ==========================================================================
    RelationshipTypeId.ACCOUNTABILITY_CAPTOR: [
        "streak_protection",
        "loss_aversion",
        "sunk_cost_leverage",
        "gentle_guilt",
        "progress_visualization",
    ],
    RelationshipTypeId.SUBSCRIPTION_CONSCIENCE: [
        "value_reminder",
        "usage_reactivation",
        "guilt_relief",
        "flexible_commitment",
        "pause_option",
    ],
    
    # ==========================================================================
    # FOURNIER EXTENSION: RITUAL AND TEMPORAL CATEGORY
    # ==========================================================================
    RelationshipTypeId.SACRED_PRACTICE: [
        "ritual_enhancement",
        "sensory_immersion",
        "mindfulness_support",
        "ceremony_elevation",
        "sacred_space_creation",
    ],
    RelationshipTypeId.TEMPORAL_MARKER: [
        "milestone_celebration",
        "memory_anchoring",
        "legacy_building",
        "anniversary_recognition",
        "life_chapter_support",
    ],
    
    # ==========================================================================
    # FOURNIER EXTENSION: GRIEF AND LOSS CATEGORY
    # ==========================================================================
    RelationshipTypeId.MOURNING_BOND: [
        "empathy_acknowledgment",
        "community_grief_support",
        "alternative_suggestion",
        "legacy_preservation",
        "bring_back_campaigns",
    ],
    RelationshipTypeId.FORMULA_BETRAYAL: [
        "transparency",
        "classic_version_return",
        "apology",
        "consumer_input_promise",
        "heritage_respect",
    ],
    
    # ==========================================================================
    # FOURNIER EXTENSION: SALVATION AND REDEMPTION CATEGORY
    # ==========================================================================
    RelationshipTypeId.LIFE_RAFT: [
        "gratitude_reinforcement",
        "community_support",
        "testimonial_celebration",
        "continued_presence",
        "crisis_readiness",
    ],
    RelationshipTypeId.TRANSFORMATION_AGENT: [
        "transformation_story",
        "before_after",
        "identity_celebration",
        "continued_growth_support",
        "ambassador_elevation",
    ],
    
    # ==========================================================================
    # FOURNIER EXTENSION: COGNITIVE DEPENDENCY CATEGORY
    # ==========================================================================
    RelationshipTypeId.SECOND_BRAIN: [
        "capability_extension",
        "integration_depth",
        "reliability_assurance",
        "cognitive_load_reduction",
        "seamless_sync",
    ],
    RelationshipTypeId.PLATFORM_LOCK_IN: [
        "ecosystem_value",
        "switching_cost_justification",
        "investment_protection",
        "cross_product_benefits",
        "loyalty_rewards",
    ],
    
    # ==========================================================================
    # FOURNIER EXTENSION: TRIBAL AND IDENTITY CATEGORY
    # ==========================================================================
    RelationshipTypeId.TRIBAL_SIGNAL: [
        "insider_recognition",
        "protocol_celebration",
        "community_rituals",
        "badge_of_belonging",
        "shared_language",
    ],
    RelationshipTypeId.INHERITED_LEGACY: [
        "heritage_honor",
        "generational_story",
        "family_tradition",
        "legacy_continuation",
        "heirloom_quality",
    ],
    RelationshipTypeId.IDENTITY_NEGATION: [
        "values_alignment",
        "anti_mainstream",
        "conscious_choice",
        "authenticity_appeal",
        "rejection_validation",
    ],
    RelationshipTypeId.WORKSPACE_CULTURE: [
        "team_productivity",
        "collaboration_enhancement",
        "culture_alignment",
        "shared_success",
        "organizational_identity",
    ],
    
    # ==========================================================================
    # FOURNIER EXTENSION: COLLECTOR AND QUEST CATEGORY
    # ==========================================================================
    RelationshipTypeId.GRAIL_QUEST: [
        "scarcity_acknowledgment",
        "pursuit_celebration",
        "exclusivity",
        "attainment_milestone",
        "collector_community",
    ],
    RelationshipTypeId.COMPLETION_SEEKER: [
        "progress_tracking",
        "completion_celebration",
        "journey_acknowledgment",
        "mindful_consumption",
        "community_sharing",
    ],
    
    # ==========================================================================
    # FOURNIER EXTENSION: TRUST AND INTIMACY CATEGORY
    # ==========================================================================
    RelationshipTypeId.FINANCIAL_INTIMATE: [
        "security_assurance",
        "privacy_protection",
        "transparency",
        "trust_building",
        "vulnerability_respect",
    ],
    RelationshipTypeId.THERAPIST_PROVIDER: [
        "emotional_support",
        "continuity",
        "personal_connection",
        "confidentiality",
        "relationship_depth",
    ],
    
    # ==========================================================================
    # FOURNIER EXTENSION: INSIDER AND COMPLICITY CATEGORY
    # ==========================================================================
    RelationshipTypeId.INSIDER_COMPACT: [
        "exclusive_knowledge",
        "gatekeeping_respect",
        "insider_language",
        "earned_access",
        "community_standards",
    ],
    RelationshipTypeId.CO_CREATOR: [
        "co_creation_invitation",
        "feedback_implementation",
        "community_ownership",
        "collaborative_development",
        "creator_recognition",
    ],
    
    # ==========================================================================
    # FOURNIER EXTENSION: VALUES AND PERMISSION CATEGORY
    # ==========================================================================
    RelationshipTypeId.ETHICAL_VALIDATOR: [
        "values_reflection",
        "guilt_free_permission",
        "impact_transparency",
        "conscious_consumption",
        "moral_alignment",
    ],
    RelationshipTypeId.STATUS_ARBITER: [
        "access_provision",
        "social_elevation",
        "exclusivity_gateway",
        "aspiration_enablement",
        "tier_progression",
    ],
    RelationshipTypeId.COMPETENCE_VALIDATOR: [
        "smart_choice_confirmation",
        "research_validation",
        "expert_endorsement",
        "quality_proof",
        "decision_affirmation",
    ],
    
    # ==========================================================================
    # FOURNIER EXTENSION: META AND IRONIC CATEGORY
    # ==========================================================================
    RelationshipTypeId.IRONIC_AWARE: [
        "self_awareness_acknowledgment",
        "authentic_transparency",
        "meta_humor",
        "anti_marketing_marketing",
        "honest_positioning",
    ],
}


# =============================================================================
# RELATIONSHIP-TO-ARCHETYPE COMPATIBILITY
# =============================================================================

# Maps relationship types to compatible brand archetypes
RELATIONSHIP_ARCHETYPE_MAP: Dict[RelationshipTypeId, List[str]] = {
    RelationshipTypeId.SELF_IDENTITY_CORE: [
        "Hero", "Outlaw", "Explorer", "Ruler"
    ],
    RelationshipTypeId.SELF_EXPRESSION_VEHICLE: [
        "Creator", "Explorer", "Outlaw", "Magician"
    ],
    RelationshipTypeId.STATUS_MARKER: [
        "Ruler", "Lover", "Hero", "Magician"
    ],
    RelationshipTypeId.TRIBAL_BADGE: [
        "Outlaw", "Hero", "Explorer", "Everyman"
    ],
    RelationshipTypeId.COMMITTED_PARTNERSHIP: [
        "Lover", "Caregiver", "Everyman", "Sage"
    ],
    RelationshipTypeId.RELIABLE_TOOL: [
        "Sage", "Everyman", "Ruler", "Caregiver"
    ],
    RelationshipTypeId.MENTOR: [
        "Sage", "Ruler", "Caregiver", "Hero"
    ],
    RelationshipTypeId.COMFORT_COMPANION: [
        "Caregiver", "Innocent", "Everyman", "Lover"
    ],
    RelationshipTypeId.CHILDHOOD_FRIEND: [
        "Everyman", "Innocent", "Jester", "Caregiver"
    ],
    RelationshipTypeId.ASPIRATIONAL_ICON: [
        "Hero", "Magician", "Explorer", "Ruler"
    ],
}
