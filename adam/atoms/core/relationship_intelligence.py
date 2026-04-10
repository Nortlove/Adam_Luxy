# =============================================================================
# ADAM RelationshipIntelligenceAtom
# Location: adam/atoms/core/relationship_intelligence.py
# =============================================================================

"""
RELATIONSHIP INTELLIGENCE ATOM

Level 2 atom that provides consumer-brand relationship intelligence to the DAG.

This atom:
1. Analyzes available review/social text for relationship signals
2. Queries stored relationship profiles from Neo4j
3. Determines the primary consumer-brand relationship type
4. Provides relationship-specific mechanism recommendations
5. Provides relationship-specific messaging guidance

The Consumer-Brand Relationship is a CORE PRIMITIVE - it influences:
- Mechanism selection (different relationships respond to different mechanisms)
- Copy tone and messaging (relationship determines appropriate tone)
- Ad template selection (relationship determines creative approach)
- Station matching (relationship type affects audience targeting)

5-Channel Observation Framework:
- Channel 1: Customer Reviews (how customer talks about brand)
- Channel 2: Social Signals (how customer signals to others)
- Channel 3: Self-Expression (how customer uses brand for identity)
- Channel 4: Brand Positioning (how brand defines itself)
- Channel 5: Advertising (OUTPUT - what we're optimizing)

Psychological Foundation:
- Escalas & Bettman (2003) Self-Brand Connection Scale
- Thomson, MacInnis & Park (2005) Brand Attachment Scale
- Taute & Sierra (2014) Brand Tribalism Scale
- Carroll & Ahuvia (2006) Brand Love Scale
- Fournier (1998) Consumer-Brand Relationship Framework
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field

from adam.atoms.core.base import BaseAtom
from adam.atoms.models.evidence import (
    IntelligenceEvidence,
    MultiSourceEvidence,
    FusionResult,
    EvidenceStrength,
)
from adam.atoms.models.atom_io import AtomInput, AtomOutput
from adam.blackboard.models.zone2_reasoning import AtomType
from adam.graph_reasoning.models.intelligence_sources import (
    IntelligenceSourceType,
    ConfidenceSemantics,
)

from adam.intelligence.relationship import (
    RelationshipTypeId,
    RelationshipStrength,
    ObservationChannel,
    ConsumerBrandRelationship,
    RELATIONSHIP_MECHANISM_MAP,
    get_relationship_detector,
)
from adam.atoms.core.dsp_integration import DSPDataAccessor

logger = logging.getLogger(__name__)


# =============================================================================
# RELATIONSHIP EVIDENCE MODELS
# =============================================================================

class RelationshipEvidence(BaseModel):
    """Evidence from consumer-brand relationship analysis."""
    
    brand_id: str
    relationship_id: Optional[str] = None
    
    # Primary relationship
    primary_relationship_type: str
    primary_confidence: float = Field(ge=0.0, le=1.0)
    
    # Secondary relationships
    secondary_relationships: Dict[str, float] = Field(default_factory=dict)
    
    # Strength
    relationship_strength: str  # RelationshipStrength value
    strength_score: float = Field(ge=0.0, le=1.0)
    
    # Channel evidence
    channel_evidence: Dict[str, float] = Field(default_factory=dict)
    
    # Characteristics
    emotional_intensity: float = Field(ge=0.0, le=1.0, default=0.5)
    identity_integration: float = Field(ge=0.0, le=1.0, default=0.0)
    social_function: float = Field(ge=0.0, le=1.0, default=0.0)
    functional_orientation: float = Field(ge=0.0, le=1.0, default=0.0)
    
    # Predictions
    predicted_loyalty: float = Field(ge=0.0, le=1.0, default=0.5)
    advocacy_likelihood: float = Field(ge=0.0, le=1.0, default=0.5)
    vulnerability_to_dissolution: str = "moderate"
    
    # Recommended strategy
    recommended_engagement_strategy: str = ""
    engagement_tone: str = ""
    messaging_avoid: List[str] = Field(default_factory=list)
    
    # Mechanism recommendations
    recommended_mechanisms: List[str] = Field(default_factory=list)
    ad_templates: List[str] = Field(default_factory=list)
    
    # Signal count (evidence volume)
    signal_count: int = 0


class RelationshipIntelligenceResult(BaseModel):
    """Result of relationship intelligence atom."""
    
    user_id: str
    request_id: str
    brand_id: Optional[str] = None
    
    # Primary output: relationship type for targeting
    primary_relationship_type: str = "reliable_tool"  # Default to functional
    relationship_confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    
    # Evidence
    relationship_evidence: Optional[RelationshipEvidence] = None
    
    # Mechanism recommendations (highest priority output)
    recommended_mechanisms: List[str] = Field(default_factory=list)
    mechanism_weights: Dict[str, float] = Field(default_factory=dict)
    
    # Messaging recommendations
    engagement_tone: str = ""
    messaging_avoid: List[str] = Field(default_factory=list)
    
    # Reasoning
    reasoning: str = ""


# =============================================================================
# RELATIONSHIP INTELLIGENCE ATOM
# =============================================================================

class RelationshipIntelligenceAtom(BaseAtom):
    """
    Level 2 atom that provides consumer-brand relationship intelligence.
    
    Dependencies:
    - UserStateAtom (for user archetype if available)
    - BrandPersonalityAtom (for brand context)
    
    Provides to downstream:
    - primary_relationship_type (for mechanism selection)
    - recommended_mechanisms (for MechanismActivationAtom)
    - engagement_tone (for MessageFramingAtom / CopyGeneration)
    
    Intelligence Sources:
    - GRAPH_EMERGENCE (primary - stored relationships from Neo4j)
    - NONCONSCIOUS_SIGNALS (from live text analysis if reviews available)
    - BANDIT_POSTERIORS (learned relationship-mechanism effectiveness)
    """
    
    ATOM_TYPE = AtomType.CUSTOM
    ATOM_NAME = "relationship_intelligence"
    TARGET_CONSTRUCT = "consumer_brand_relationship"
    
    REQUIRED_SOURCES = [
        IntelligenceSourceType.GRAPH_EMERGENCE,
    ]
    
    OPTIONAL_SOURCES = [
        IntelligenceSourceType.NONCONSCIOUS_SIGNALS,  # Text analysis for relationship signals
        IntelligenceSourceType.BANDIT_POSTERIORS,
        IntelligenceSourceType.EMPIRICAL_PATTERNS,
    ]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._relationship_graph_builder = None
        self._relationship_detector = None
    
    async def _get_relationship_graph_builder(self):
        """Lazy initialization of relationship graph builder."""
        if self._relationship_graph_builder is None:
            try:
                from adam.intelligence.relationship import RelationshipGraphBuilder
                driver = self.bridge.neo4j_driver if hasattr(self.bridge, 'neo4j_driver') else None
                if driver:
                    self._relationship_graph_builder = RelationshipGraphBuilder(driver)
            except Exception as e:
                logger.warning(f"Could not initialize relationship graph builder: {e}")
        return self._relationship_graph_builder
    
    def _get_relationship_detector(self):
        """Get the relationship detector service."""
        if self._relationship_detector is None:
            self._relationship_detector = get_relationship_detector()
        return self._relationship_detector
    
    async def _gather_evidence(
        self,
        atom_input: AtomInput,
    ) -> MultiSourceEvidence:
        """
        Gather relationship evidence from multiple sources.
        
        1. Check Neo4j for existing relationship profiles
        2. Analyze any provided review text for live signals
        3. Combine with brand personality context
        """
        evidence = MultiSourceEvidence(
            construct=self.TARGET_CONSTRUCT,
        )
        
        # Get brand_id from request context
        brand_id = None
        if atom_input.request_context:
            brand_id = getattr(atom_input.request_context, "brand_id", None)
            # Also check ad candidates for brand
            for candidate in getattr(atom_input.request_context, "ad_candidates", []) or []:
                if isinstance(candidate, dict) and candidate.get("brand_id"):
                    brand_id = candidate["brand_id"]
                    break
        
        if not brand_id:
            logger.debug("No brand_id in request context")
            return evidence
        
        # 1. Query stored relationships from Neo4j
        graph_builder = await self._get_relationship_graph_builder()
        relationship_data = None
        
        if graph_builder:
            try:
                # Get relationship distribution for brand
                distribution = await graph_builder.get_brand_relationship_distribution(brand_id)
                primary_type_result = await graph_builder.get_primary_relationship_type(brand_id)
                
                if distribution and primary_type_result:
                    primary_type, count = primary_type_result
                    
                    # Build evidence from stored data
                    relationship_data = RelationshipEvidence(
                        brand_id=brand_id,
                        primary_relationship_type=primary_type,
                        primary_confidence=distribution.get(primary_type, {}).get('avg_confidence', 0.5),
                        secondary_relationships={
                            rt: data['avg_confidence']
                            for rt, data in distribution.items()
                            if rt != primary_type
                        },
                        relationship_strength='moderate',
                        strength_score=distribution.get(primary_type, {}).get('avg_strength', 0.5),
                        signal_count=count,
                        recommended_mechanisms=RELATIONSHIP_MECHANISM_MAP.get(
                            RelationshipTypeId(primary_type) if primary_type in [e.value for e in RelationshipTypeId] else RelationshipTypeId.RELIABLE_TOOL,
                            []
                        )[:4],
                    )
                    
                    # Get engagement tone from relationship type
                    try:
                        rel_type_id = RelationshipTypeId(primary_type)
                        relationship_data.engagement_tone = self._get_engagement_tone(rel_type_id)
                        relationship_data.messaging_avoid = self._get_messaging_avoid(rel_type_id)
                        relationship_data.recommended_engagement_strategy = self._get_engagement_strategy(rel_type_id)
                    except ValueError:
                        # Unknown relationship type - keep default engagement settings
                        logger.debug(f"Unknown relationship type '{primary_type}', using defaults")
                    
                    evidence.evidence[IntelligenceSourceType.GRAPH_EMERGENCE] = IntelligenceEvidence(
                        source_type=IntelligenceSourceType.GRAPH_EMERGENCE,
                        construct=self.TARGET_CONSTRUCT,
                        value=relationship_data.primary_confidence,
                        confidence=0.8 if count >= 10 else 0.5,
                        metadata={
                            "relationship_evidence": relationship_data.model_dump(),
                            "found": True,
                            "signal_count": count,
                        },
                        timestamp=datetime.now(timezone.utc),
                        strength=EvidenceStrength.STRONG if count >= 10 else EvidenceStrength.MODERATE,
                    )
                    
            except Exception as e:
                logger.warning(f"Error getting relationship from graph: {e}")
        
        # 2. Analyze live text if provided (reviews, social posts)
        review_texts = getattr(atom_input.request_context, "review_texts", []) if atom_input.request_context else []
        social_texts = getattr(atom_input.request_context, "social_texts", []) if atom_input.request_context else []
        
        if review_texts or social_texts:
            try:
                detector = self._get_relationship_detector()
                
                # Build text list with channels
                texts = []
                for text in review_texts:
                    if isinstance(text, str):
                        texts.append({
                            'text': text,
                            'channel': ObservationChannel.CUSTOMER_REVIEWS,
                        })
                    elif isinstance(text, dict):
                        texts.append(text)
                
                for text in social_texts:
                    if isinstance(text, str):
                        texts.append({
                            'text': text,
                            'channel': ObservationChannel.SOCIAL_SIGNALS,
                        })
                    elif isinstance(text, dict):
                        texts.append(text)
                
                if texts:
                    # Analyze texts
                    relationship = detector.analyze_texts(texts, brand_id)
                    
                    # Build evidence
                    nlp_evidence = RelationshipEvidence(
                        brand_id=brand_id,
                        relationship_id=relationship.relationship_id,
                        primary_relationship_type=relationship.primary_relationship_type.value,
                        primary_confidence=relationship.primary_confidence,
                        secondary_relationships={
                            rt.value: score for rt, score in relationship.secondary_relationships.items()
                        },
                        relationship_strength=relationship.strength.value,
                        strength_score=relationship.strength_score,
                        channel_evidence={
                            ch.value: score for ch, score in relationship.channel_evidence.items()
                        },
                        emotional_intensity=relationship.emotional_intensity,
                        identity_integration=relationship.identity_integration,
                        social_function=relationship.social_function,
                        functional_orientation=relationship.functional_orientation,
                        predicted_loyalty=relationship.predicted_loyalty,
                        advocacy_likelihood=relationship.advocacy_likelihood,
                        vulnerability_to_dissolution=relationship.vulnerability_to_dissolution,
                        recommended_engagement_strategy=relationship.recommended_engagement_strategy or "",
                        engagement_tone=relationship.get_engagement_tone(),
                        messaging_avoid=relationship.get_messaging_avoid_list(),
                        recommended_mechanisms=relationship.recommended_mechanisms,
                        ad_templates=relationship.recommended_ad_templates,
                        signal_count=relationship.signal_count,
                    )
                    
                    evidence.evidence[IntelligenceSourceType.NONCONSCIOUS_SIGNALS] = IntelligenceEvidence(
                        source_type=IntelligenceSourceType.NONCONSCIOUS_SIGNALS,
                        construct=self.TARGET_CONSTRUCT,
                        value=relationship.primary_confidence,
                        confidence=relationship.primary_confidence,
                        metadata={
                            "relationship_evidence": nlp_evidence.model_dump(),
                            "found": True,
                            "signal_count": relationship.signal_count,
                            "from_live_analysis": True,
                        },
                        timestamp=datetime.now(timezone.utc),
                        strength=EvidenceStrength.STRONG if relationship.signal_count >= 5 else EvidenceStrength.MODERATE,
                    )
                    
            except Exception as e:
                logger.warning(f"Error analyzing review texts: {e}")
        
        return evidence
    
    def _get_engagement_tone(self, rel_type: RelationshipTypeId) -> str:
        """Get recommended messaging tone based on relationship type (all 52 types)."""
        tone_map = {
            # =================================================================
            # SELF-DEFINITION CATEGORY
            # =================================================================
            RelationshipTypeId.SELF_IDENTITY_CORE: "affirming, heritage-focused, celebratory",
            RelationshipTypeId.SELF_EXPRESSION_VEHICLE: "authentic, expressive, value-aligned",
            RelationshipTypeId.COMPARTMENTALIZED_IDENTITY: "context-aware, role-specific, respectful of boundaries",
            
            # =================================================================
            # SOCIAL SIGNALING CATEGORY
            # =================================================================
            RelationshipTypeId.STATUS_MARKER: "exclusive, premium, aspirational",
            RelationshipTypeId.SOCIAL_COMPLIANCE: "personal value-focused, autonomy-supporting",
            
            # =================================================================
            # SOCIAL BELONGING CATEGORY
            # =================================================================
            RelationshipTypeId.TRIBAL_BADGE: "inclusive to tribe, insider language",
            RelationshipTypeId.CHAMPION_EVANGELIST: "recognizing, empowering, co-creative",
            
            # =================================================================
            # EMOTIONAL BOND CATEGORY
            # =================================================================
            RelationshipTypeId.COMMITTED_PARTNERSHIP: "warm, appreciative, partnership-oriented",
            RelationshipTypeId.DEPENDENCY: "reassuring, always-there, reliable",
            RelationshipTypeId.FLING: "exciting, spontaneous, limited-time",
            RelationshipTypeId.SECRET_AFFAIR: "discreet, private, non-judgmental",
            RelationshipTypeId.GUILTY_PLEASURE: "normalizing, permission-giving, judgment-free",
            RelationshipTypeId.RESCUE_SAVIOR: "grateful, honoring, testimonial-celebrating",
            
            # =================================================================
            # FUNCTIONAL CATEGORY
            # =================================================================
            RelationshipTypeId.RELIABLE_TOOL: "clear, confident, no-nonsense",
            RelationshipTypeId.BEST_FRIEND_UTILITY: "reliable, trustworthy, everyday supportive",
            
            # =================================================================
            # GUIDANCE CATEGORY
            # =================================================================
            RelationshipTypeId.MENTOR: "expert, educational, helpful",
            RelationshipTypeId.CAREGIVER: "nurturing, protective, reassuring",
            
            # =================================================================
            # THERAPEUTIC CATEGORY
            # =================================================================
            RelationshipTypeId.COMFORT_COMPANION: "warm, soothing, gentle",
            RelationshipTypeId.ESCAPE_ARTIST: "escapist, transformative, fantasy-enabling",
            
            # =================================================================
            # TEMPORAL/NOSTALGIC CATEGORY
            # =================================================================
            RelationshipTypeId.CHILDHOOD_FRIEND: "nostalgic, familiar, comforting",
            RelationshipTypeId.SEASONAL_REKINDLER: "anticipation-building, tradition-honoring, timely",
            
            # =================================================================
            # ASPIRATIONAL CATEGORY
            # =================================================================
            RelationshipTypeId.ASPIRATIONAL_ICON: "inspirational, achievable dream",
            
            # =================================================================
            # ACQUISITION/EXPLORATION CATEGORY
            # =================================================================
            RelationshipTypeId.COURTSHIP_DATING: "risk-reducing, demonstrating, credibility-building",
            RelationshipTypeId.REBOUND_RELATIONSHIP: "positive-focused, differentiated, non-comparative",
            
            # =================================================================
            # NEGATIVE/TRAPPED CATEGORY
            # =================================================================
            RelationshipTypeId.ENEMY: "acknowledge issue, rebuild trust",
            RelationshipTypeId.EX_RELATIONSHIP: "win-back, improvement-showing, second-chance",
            RelationshipTypeId.CAPTIVE_ENSLAVEMENT: "value-demonstrating, friction-reducing, gratitude-expressing",
            RelationshipTypeId.RELUCTANT_USER: "value-improving, expectation-exceeding, reframing",
            
            # =================================================================
            # GUILT AND OBLIGATION CATEGORY (Fournier Extension)
            # =================================================================
            RelationshipTypeId.ACCOUNTABILITY_CAPTOR: "gentle progress, compassionate recovery, progress-visualizing",
            RelationshipTypeId.SUBSCRIPTION_CONSCIENCE: "value-reminding, flexible, guilt-relieving",
            
            # =================================================================
            # RITUAL AND TEMPORAL CATEGORY (Fournier Extension)
            # =================================================================
            RelationshipTypeId.SACRED_PRACTICE: "ceremony-enhancing, sensory-immersive, ritual-honoring",
            RelationshipTypeId.TEMPORAL_MARKER: "milestone-celebrating, memory-anchoring, legacy-building",
            
            # =================================================================
            # GRIEF AND LOSS CATEGORY (Fournier Extension)
            # =================================================================
            RelationshipTypeId.MOURNING_BOND: "empathetic, grief-acknowledging, gentle",
            RelationshipTypeId.FORMULA_BETRAYAL: "transparent, apologetic, heritage-respecting",
            
            # =================================================================
            # SALVATION AND REDEMPTION CATEGORY (Fournier Extension)
            # =================================================================
            RelationshipTypeId.LIFE_RAFT: "supportive presence, community-oriented, gratitude-reinforcing",
            RelationshipTypeId.TRANSFORMATION_AGENT: "transformation-celebrating, before/after honoring, ambassador-elevating",
            
            # =================================================================
            # COGNITIVE DEPENDENCY CATEGORY (Fournier Extension)
            # =================================================================
            RelationshipTypeId.SECOND_BRAIN: "reliability-assuring, capability-extending, seamless",
            RelationshipTypeId.PLATFORM_LOCK_IN: "ecosystem-valuing, investment-protecting, loyalty-rewarding",
            
            # =================================================================
            # TRIBAL AND IDENTITY CATEGORY (Fournier Extension)
            # =================================================================
            RelationshipTypeId.TRIBAL_SIGNAL: "protocol-celebrating, insider-recognizing, ritual-honoring",
            RelationshipTypeId.INHERITED_LEGACY: "heritage-honoring, generational-storytelling, tradition-continuing",
            RelationshipTypeId.IDENTITY_NEGATION: "values-aligned, authentic, anti-mainstream",
            RelationshipTypeId.WORKSPACE_CULTURE: "team-productivity-focused, collaboration-enhancing, culture-aligned",
            
            # =================================================================
            # COLLECTOR AND QUEST CATEGORY (Fournier Extension)
            # =================================================================
            RelationshipTypeId.GRAIL_QUEST: "scarcity-acknowledging, pursuit-celebrating, attainment-milestone",
            RelationshipTypeId.COMPLETION_SEEKER: "progress-tracking, completion-celebrating, mindful",
            
            # =================================================================
            # TRUST AND INTIMACY CATEGORY (Fournier Extension)
            # =================================================================
            RelationshipTypeId.FINANCIAL_INTIMATE: "security-assuring, privacy-protecting, transparent",
            RelationshipTypeId.THERAPIST_PROVIDER: "emotional-supportive, continuity-emphasizing, personal",
            
            # =================================================================
            # INSIDER AND COMPLICITY CATEGORY (Fournier Extension)
            # =================================================================
            RelationshipTypeId.INSIDER_COMPACT: "insider-language, gatekeeping-respecting, earned-access",
            RelationshipTypeId.CO_CREATOR: "co-creative, feedback-implementing, community-owning",
            
            # =================================================================
            # VALUES AND PERMISSION CATEGORY (Fournier Extension)
            # =================================================================
            RelationshipTypeId.ETHICAL_VALIDATOR: "values-reflecting, guilt-free, impact-transparent",
            RelationshipTypeId.STATUS_ARBITER: "access-providing, tier-progressing, exclusivity-gatekeeper",
            RelationshipTypeId.COMPETENCE_VALIDATOR: "smart-choice-confirming, research-validating, quality-proving",
            
            # =================================================================
            # META AND IRONIC CATEGORY (Fournier Extension)
            # =================================================================
            RelationshipTypeId.IRONIC_AWARE: "self-aware, authentically-transparent, meta-humorous",
        }
        return tone_map.get(rel_type, "warm, engaging")
    
    def _get_messaging_avoid(self, rel_type: RelationshipTypeId) -> List[str]:
        """Get list of messaging approaches to avoid (all 52 types)."""
        avoid_map = {
            # =================================================================
            # SELF-DEFINITION CATEGORY
            # =================================================================
            RelationshipTypeId.SELF_IDENTITY_CORE: ["trying to change them", "aggressive CTAs", "questioning identity"],
            RelationshipTypeId.SELF_EXPRESSION_VEHICLE: ["inauthentic messaging", "values contradiction", "generic appeals"],
            RelationshipTypeId.COMPARTMENTALIZED_IDENTITY: ["over-extending brand meaning", "context confusion", "all-or-nothing"],
            
            # =================================================================
            # SOCIAL SIGNALING CATEGORY
            # =================================================================
            RelationshipTypeId.STATUS_MARKER: ["discount messaging", "mass market imagery", "budget language"],
            RelationshipTypeId.SOCIAL_COMPLIANCE: ["peer pressure language", "conformity emphasis", "herd messaging"],
            
            # =================================================================
            # SOCIAL BELONGING CATEGORY
            # =================================================================
            RelationshipTypeId.TRIBAL_BADGE: ["mass market appeal", "generic messaging", "outsider perspective"],
            RelationshipTypeId.CHAMPION_EVANGELIST: ["selling to them", "acquisition messaging", "treating as prospect"],
            
            # =================================================================
            # EMOTIONAL BOND CATEGORY
            # =================================================================
            RelationshipTypeId.COMMITTED_PARTNERSHIP: ["acquisition messaging", "hard sells", "assuming disloyalty"],
            RelationshipTypeId.DEPENDENCY: ["threatening availability", "change messaging", "disruption"],
            RelationshipTypeId.FLING: ["commitment language", "long-term promises", "heavy relationship framing"],
            RelationshipTypeId.SECRET_AFFAIR: ["social proof", "public visibility", "sharing encouragement"],
            RelationshipTypeId.GUILTY_PLEASURE: ["social proof", "public endorsement asks", "shame triggers"],
            RelationshipTypeId.RESCUE_SAVIOR: ["minimizing their story", "forgetting the rescue", "routine messaging"],
            
            # =================================================================
            # FUNCTIONAL CATEGORY
            # =================================================================
            RelationshipTypeId.RELIABLE_TOOL: ["emotional appeals", "identity messaging", "flowery language"],
            RelationshipTypeId.BEST_FRIEND_UTILITY: ["purely transactional language", "cold functional only", "no warmth"],
            
            # =================================================================
            # GUIDANCE CATEGORY
            # =================================================================
            RelationshipTypeId.MENTOR: ["salesy pitches", "condescending tone", "dumbing down"],
            RelationshipTypeId.CAREGIVER: ["harsh messaging", "abandonment themes", "cold efficiency"],
            
            # =================================================================
            # THERAPEUTIC CATEGORY
            # =================================================================
            RelationshipTypeId.COMFORT_COMPANION: ["urgent CTAs", "anxiety-inducing content", "pressure"],
            RelationshipTypeId.ESCAPE_ARTIST: ["reality emphasis", "responsibility messaging", "mundane framing"],
            
            # =================================================================
            # TEMPORAL/NOSTALGIC CATEGORY
            # =================================================================
            RelationshipTypeId.CHILDHOOD_FRIEND: ["modernization for its own sake", "dismissing heritage", "too trendy"],
            RelationshipTypeId.SEASONAL_REKINDLER: ["off-season messaging", "year-round pushing", "ignoring timing"],
            
            # =================================================================
            # ASPIRATIONAL CATEGORY
            # =================================================================
            RelationshipTypeId.ASPIRATIONAL_ICON: ["unachievable framing", "elite exclusion", "crushing dreams"],
            
            # =================================================================
            # ACQUISITION/EXPLORATION CATEGORY
            # =================================================================
            RelationshipTypeId.COURTSHIP_DATING: ["assuming loyalty", "retention messaging", "long-term commitment language"],
            RelationshipTypeId.REBOUND_RELATIONSHIP: ["competitor mentions", "comparison messaging", "negative focus"],
            
            # =================================================================
            # NEGATIVE/TRAPPED CATEGORY
            # =================================================================
            RelationshipTypeId.ENEMY: ["defensive messaging", "dismissing concerns", "doubling down"],
            RelationshipTypeId.EX_RELATIONSHIP: ["assuming current relationship", "ignoring history", "aggressive re-engagement"],
            RelationshipTypeId.CAPTIVE_ENSLAVEMENT: ["loyalty messaging", "gratitude assumptions", "ignoring frustration"],
            RelationshipTypeId.RELUCTANT_USER: ["enthusiasm assumptions", "loyalty language", "satisfaction claims"],
            
            # =================================================================
            # GUILT AND OBLIGATION CATEGORY (Fournier Extension)
            # =================================================================
            RelationshipTypeId.ACCOUNTABILITY_CAPTOR: ["excessive guilt", "harsh judgment", "shame-heavy messaging"],
            RelationshipTypeId.SUBSCRIPTION_CONSCIENCE: ["adding more guilt", "value-blind messaging", "retention hard sells"],
            
            # =================================================================
            # RITUAL AND TEMPORAL CATEGORY (Fournier Extension)
            # =================================================================
            RelationshipTypeId.SACRED_PRACTICE: ["disrupting ritual", "urgent CTAs", "breaking the ceremony"],
            RelationshipTypeId.TEMPORAL_MARKER: ["minimizing milestones", "generic messaging", "forgetting the memory"],
            
            # =================================================================
            # GRIEF AND LOSS CATEGORY (Fournier Extension)
            # =================================================================
            RelationshipTypeId.MOURNING_BOND: ["dismissing grief", "quick replacement pushing", "move on messaging"],
            RelationshipTypeId.FORMULA_BETRAYAL: ["defending change", "gaslighting", "same label claims"],
            
            # =================================================================
            # SALVATION AND REDEMPTION CATEGORY (Fournier Extension)
            # =================================================================
            RelationshipTypeId.LIFE_RAFT: ["forgetting crisis role", "routine marketing", "losing supportive presence"],
            RelationshipTypeId.TRANSFORMATION_AGENT: ["minimizing change", "forgetting before/after", "treating as regular customer"],
            
            # =================================================================
            # COGNITIVE DEPENDENCY CATEGORY (Fournier Extension)
            # =================================================================
            RelationshipTypeId.SECOND_BRAIN: ["threatening data", "reliability doubts", "availability uncertainty"],
            RelationshipTypeId.PLATFORM_LOCK_IN: ["trap language", "acknowledging lock-in negatively", "competitor switching ease"],
            
            # =================================================================
            # TRIBAL AND IDENTITY CATEGORY (Fournier Extension)
            # =================================================================
            RelationshipTypeId.TRIBAL_SIGNAL: ["outsider language", "protocol ignorance", "inauthenticity"],
            RelationshipTypeId.INHERITED_LEGACY: ["dismissing heritage", "generational disconnect", "modernization pressure"],
            RelationshipTypeId.IDENTITY_NEGATION: ["mainstream appeals", "consumption encouragement", "mass market"],
            RelationshipTypeId.WORKSPACE_CULTURE: ["individual focus only", "ignoring team", "isolation messaging"],
            
            # =================================================================
            # COLLECTOR AND QUEST CATEGORY (Fournier Extension)
            # =================================================================
            RelationshipTypeId.GRAIL_QUEST: ["abundance messaging", "easy availability", "mass market framing"],
            RelationshipTypeId.COMPLETION_SEEKER: ["buy more pressure", "new product pushing", "completion dismissal"],
            
            # =================================================================
            # TRUST AND INTIMACY CATEGORY (Fournier Extension)
            # =================================================================
            RelationshipTypeId.FINANCIAL_INTIMATE: ["cavalier data handling", "security minimization", "trust assumptions"],
            RelationshipTypeId.THERAPIST_PROVIDER: ["discontinuity", "impersonal messaging", "relationship dismissal"],
            
            # =================================================================
            # INSIDER AND COMPLICITY CATEGORY (Fournier Extension)
            # =================================================================
            RelationshipTypeId.INSIDER_COMPACT: ["mass accessibility", "outsider perspective", "gatekeeping destruction"],
            RelationshipTypeId.CO_CREATOR: ["ignoring input", "corporate distance", "one-way communication"],
            
            # =================================================================
            # VALUES AND PERMISSION CATEGORY (Fournier Extension)
            # =================================================================
            RelationshipTypeId.ETHICAL_VALIDATOR: ["greenwashing", "values hypocrisy", "guilt inducement"],
            RelationshipTypeId.STATUS_ARBITER: ["easy access messaging", "tier destruction", "exclusivity erosion"],
            RelationshipTypeId.COMPETENCE_VALIDATOR: ["emotional appeals", "impulse messaging", "ignoring research"],
            
            # =================================================================
            # META AND IRONIC CATEGORY (Fournier Extension)
            # =================================================================
            RelationshipTypeId.IRONIC_AWARE: ["pretending not to market", "inauthentic earnestness", "ignoring their awareness"],
        }
        return avoid_map.get(rel_type, [])
    
    def _get_engagement_strategy(self, rel_type: RelationshipTypeId) -> str:
        """Get recommended engagement strategy name (all 52 types)."""
        strategy_map = {
            # =================================================================
            # SELF-DEFINITION CATEGORY
            # =================================================================
            RelationshipTypeId.SELF_IDENTITY_CORE: "identity_affirmation",
            RelationshipTypeId.SELF_EXPRESSION_VEHICLE: "value_expression",
            RelationshipTypeId.COMPARTMENTALIZED_IDENTITY: "context_support",
            
            # =================================================================
            # SOCIAL SIGNALING CATEGORY
            # =================================================================
            RelationshipTypeId.STATUS_MARKER: "status_recognition",
            RelationshipTypeId.SOCIAL_COMPLIANCE: "genuine_preference_building",
            
            # =================================================================
            # SOCIAL BELONGING CATEGORY
            # =================================================================
            RelationshipTypeId.TRIBAL_BADGE: "tribal_belonging",
            RelationshipTypeId.CHAMPION_EVANGELIST: "ambassador_empowerment",
            
            # =================================================================
            # EMOTIONAL BOND CATEGORY
            # =================================================================
            RelationshipTypeId.COMMITTED_PARTNERSHIP: "relationship_deepening",
            RelationshipTypeId.DEPENDENCY: "reassurance_reliability",
            RelationshipTypeId.FLING: "novelty_excitement",
            RelationshipTypeId.SECRET_AFFAIR: "discreet_indulgence",
            RelationshipTypeId.GUILTY_PLEASURE: "permission_normalization",
            RelationshipTypeId.RESCUE_SAVIOR: "gratitude_testimonial",
            
            # =================================================================
            # FUNCTIONAL CATEGORY
            # =================================================================
            RelationshipTypeId.RELIABLE_TOOL: "functional_value",
            RelationshipTypeId.BEST_FRIEND_UTILITY: "trusted_support",
            
            # =================================================================
            # GUIDANCE CATEGORY
            # =================================================================
            RelationshipTypeId.MENTOR: "expertise_guidance",
            RelationshipTypeId.CAREGIVER: "nurturing_protection",
            
            # =================================================================
            # THERAPEUTIC CATEGORY
            # =================================================================
            RelationshipTypeId.COMFORT_COMPANION: "comfort_provision",
            RelationshipTypeId.ESCAPE_ARTIST: "escapism_facilitation",
            
            # =================================================================
            # TEMPORAL/NOSTALGIC CATEGORY
            # =================================================================
            RelationshipTypeId.CHILDHOOD_FRIEND: "nostalgia_connection",
            RelationshipTypeId.SEASONAL_REKINDLER: "anticipation_tradition",
            
            # =================================================================
            # ASPIRATIONAL CATEGORY
            # =================================================================
            RelationshipTypeId.ASPIRATIONAL_ICON: "aspiration_bridge",
            
            # =================================================================
            # ACQUISITION/EXPLORATION CATEGORY
            # =================================================================
            RelationshipTypeId.COURTSHIP_DATING: "trial_conversion",
            RelationshipTypeId.REBOUND_RELATIONSHIP: "positive_differentiation",
            
            # =================================================================
            # NEGATIVE/TRAPPED CATEGORY
            # =================================================================
            RelationshipTypeId.ENEMY: "trust_rebuilding",
            RelationshipTypeId.EX_RELATIONSHIP: "win_back",
            RelationshipTypeId.CAPTIVE_ENSLAVEMENT: "value_demonstration",
            RelationshipTypeId.RELUCTANT_USER: "perception_improvement",
            
            # =================================================================
            # GUILT AND OBLIGATION CATEGORY (Fournier Extension)
            # =================================================================
            RelationshipTypeId.ACCOUNTABILITY_CAPTOR: "gentle_accountability",
            RelationshipTypeId.SUBSCRIPTION_CONSCIENCE: "value_reactivation",
            
            # =================================================================
            # RITUAL AND TEMPORAL CATEGORY (Fournier Extension)
            # =================================================================
            RelationshipTypeId.SACRED_PRACTICE: "ritual_enhancement",
            RelationshipTypeId.TEMPORAL_MARKER: "milestone_celebration",
            
            # =================================================================
            # GRIEF AND LOSS CATEGORY (Fournier Extension)
            # =================================================================
            RelationshipTypeId.MOURNING_BOND: "empathy_support",
            RelationshipTypeId.FORMULA_BETRAYAL: "transparency_recovery",
            
            # =================================================================
            # SALVATION AND REDEMPTION CATEGORY (Fournier Extension)
            # =================================================================
            RelationshipTypeId.LIFE_RAFT: "continued_presence",
            RelationshipTypeId.TRANSFORMATION_AGENT: "transformation_celebration",
            
            # =================================================================
            # COGNITIVE DEPENDENCY CATEGORY (Fournier Extension)
            # =================================================================
            RelationshipTypeId.SECOND_BRAIN: "cognitive_reliability",
            RelationshipTypeId.PLATFORM_LOCK_IN: "ecosystem_value",
            
            # =================================================================
            # TRIBAL AND IDENTITY CATEGORY (Fournier Extension)
            # =================================================================
            RelationshipTypeId.TRIBAL_SIGNAL: "protocol_celebration",
            RelationshipTypeId.INHERITED_LEGACY: "heritage_honor",
            RelationshipTypeId.IDENTITY_NEGATION: "values_authenticity",
            RelationshipTypeId.WORKSPACE_CULTURE: "team_collaboration",
            
            # =================================================================
            # COLLECTOR AND QUEST CATEGORY (Fournier Extension)
            # =================================================================
            RelationshipTypeId.GRAIL_QUEST: "scarcity_celebration",
            RelationshipTypeId.COMPLETION_SEEKER: "progress_acknowledgment",
            
            # =================================================================
            # TRUST AND INTIMACY CATEGORY (Fournier Extension)
            # =================================================================
            RelationshipTypeId.FINANCIAL_INTIMATE: "security_trust",
            RelationshipTypeId.THERAPIST_PROVIDER: "emotional_continuity",
            
            # =================================================================
            # INSIDER AND COMPLICITY CATEGORY (Fournier Extension)
            # =================================================================
            RelationshipTypeId.INSIDER_COMPACT: "exclusive_knowledge",
            RelationshipTypeId.CO_CREATOR: "collaborative_development",
            
            # =================================================================
            # VALUES AND PERMISSION CATEGORY (Fournier Extension)
            # =================================================================
            RelationshipTypeId.ETHICAL_VALIDATOR: "values_reflection",
            RelationshipTypeId.STATUS_ARBITER: "access_progression",
            RelationshipTypeId.COMPETENCE_VALIDATOR: "smart_choice_validation",
            
            # =================================================================
            # META AND IRONIC CATEGORY (Fournier Extension)
            # =================================================================
            RelationshipTypeId.IRONIC_AWARE: "transparent_authenticity",
        }
        return strategy_map.get(rel_type, "general_engagement")
    
    async def _fuse_without_claude(
        self,
        evidence: MultiSourceEvidence,
        atom_input: AtomInput,
    ) -> FusionResult:
        """
        Fuse relationship evidence without Claude.
        
        Priority:
        1. Live NLP analysis (most recent, specific)
        2. Graph data (historical aggregate)
        """
        # Get evidence sources
        nlp_evidence = evidence.evidence.get(IntelligenceSourceType.NONCONSCIOUS_SIGNALS)
        graph_evidence = evidence.evidence.get(IntelligenceSourceType.GRAPH_EMERGENCE)
        
        if not nlp_evidence and not graph_evidence:
            return FusionResult(
                construct=self.TARGET_CONSTRUCT,
                assessment="0.5",
                assessment_value=0.5,
                confidence=0.3,
                reasoning="No relationship data available; defaulting to functional relationship",
                contributing_sources=[],
            )
        
        # Prefer live NLP analysis if available
        if nlp_evidence and nlp_evidence.metadata.get("from_live_analysis"):
            rel_data = nlp_evidence.metadata.get("relationship_evidence", {})
            return FusionResult(
                construct=self.TARGET_CONSTRUCT,
                assessment=str(nlp_evidence.value),
                assessment_value=nlp_evidence.value,
                confidence=nlp_evidence.confidence,
                reasoning=f"Live analysis detected {rel_data.get('primary_relationship_type', 'unknown')} "
                          f"relationship (confidence: {nlp_evidence.confidence:.2f}, "
                          f"signals: {rel_data.get('signal_count', 0)})",
                contributing_sources=[IntelligenceSourceType.NONCONSCIOUS_SIGNALS],
                source_weights={
                    IntelligenceSourceType.NONCONSCIOUS_SIGNALS: 1.0,
                },
            )
        
        # Fall back to graph evidence
        if graph_evidence and graph_evidence.metadata.get("found"):
            rel_data = graph_evidence.metadata.get("relationship_evidence", {})
            return FusionResult(
                construct=self.TARGET_CONSTRUCT,
                assessment=str(graph_evidence.value),
                assessment_value=graph_evidence.value,
                confidence=graph_evidence.confidence,
                reasoning=f"Historical data shows {rel_data.get('primary_relationship_type', 'unknown')} "
                          f"relationship (based on {rel_data.get('signal_count', 0)} observations)",
                contributing_sources=[IntelligenceSourceType.GRAPH_EMERGENCE],
                source_weights={
                    IntelligenceSourceType.GRAPH_EMERGENCE: 1.0,
                },
            )
        
        return FusionResult(
            construct=self.TARGET_CONSTRUCT,
            assessment="0.5",
            assessment_value=0.5,
            confidence=0.3,
            reasoning="Insufficient relationship data",
            contributing_sources=[],
        )
    
    async def _build_output(
        self,
        atom_input: AtomInput,
        evidence: MultiSourceEvidence,
        fusion_result: FusionResult,
    ) -> AtomOutput:
        """Build relationship intelligence output."""
        
        # Get best relationship evidence
        relationship_evidence = None
        nlp_evi = evidence.evidence.get(IntelligenceSourceType.NONCONSCIOUS_SIGNALS)
        graph_evi = evidence.evidence.get(IntelligenceSourceType.GRAPH_EMERGENCE)
        
        # Prefer NLP if available
        if nlp_evi and nlp_evi.metadata.get("relationship_evidence"):
            relationship_evidence = RelationshipEvidence(**nlp_evi.metadata["relationship_evidence"])
        elif graph_evi and graph_evi.metadata.get("relationship_evidence"):
            relationship_evidence = RelationshipEvidence(**graph_evi.metadata["relationship_evidence"])
        
        # Build result
        primary_type = "reliable_tool"
        recommended_mechanisms = []
        mechanism_weights = {}
        engagement_tone = ""
        messaging_avoid = []
        
        if relationship_evidence:
            primary_type = relationship_evidence.primary_relationship_type
            recommended_mechanisms = relationship_evidence.recommended_mechanisms
            engagement_tone = relationship_evidence.engagement_tone
            messaging_avoid = relationship_evidence.messaging_avoid
            
            # Build mechanism weights
            for i, mech in enumerate(recommended_mechanisms):
                mechanism_weights[mech] = 1.0 - (i * 0.15)  # Decreasing weight

        # DSP relationship amplification: boost/dampen mechanisms by relationship type
        dsp = DSPDataAccessor(atom_input)
        if dsp.has_dsp and mechanism_weights:
            # Relationship amplification: mechanisms that work well with this relationship type
            rel_boosts = dsp.get_all_relationship_boosts()
            for mech in list(mechanism_weights.keys()):
                boost = rel_boosts.get(mech)
                if boost is not None:
                    # Boost is a factor (e.g., 0.3 = +30% amplification)
                    mechanism_weights[mech] = min(1.0, mechanism_weights[mech] * (1.0 + boost * 0.15))

            # Empirical effectiveness: validate relationship-mechanism mappings
            empirical = dsp.get_all_empirical()
            for mech in list(mechanism_weights.keys()):
                emp = empirical.get(mech)
                if emp and emp.get("sample_size", 0) > 100:
                    success = emp.get("success_rate", 0.5)
                    # Slight adjustment: empirically effective mechanisms get a small boost
                    mechanism_weights[mech] = min(1.0, mechanism_weights[mech] + (success - 0.5) * 0.1)

        result = RelationshipIntelligenceResult(
            user_id=atom_input.user_id,
            request_id=atom_input.request_id,
            brand_id=relationship_evidence.brand_id if relationship_evidence else None,
            primary_relationship_type=primary_type,
            relationship_confidence=fusion_result.confidence,
            relationship_evidence=relationship_evidence,
            recommended_mechanisms=recommended_mechanisms,
            mechanism_weights=mechanism_weights,
            engagement_tone=engagement_tone,
            messaging_avoid=messaging_avoid,
            reasoning=fusion_result.reasoning,
        )
        
        # Build atom output
        return AtomOutput(
            atom_id=self.config.atom_id,
            atom_type=self.ATOM_TYPE,
            request_id=atom_input.request_id,
            fusion_result=fusion_result,
            primary_assessment=primary_type,
            overall_confidence=fusion_result.confidence,
            evidence_package=evidence,
            inferred_states={
                "emotional_intensity": relationship_evidence.emotional_intensity if relationship_evidence else 0.5,
                "identity_integration": relationship_evidence.identity_integration if relationship_evidence else 0.0,
                "social_function": relationship_evidence.social_function if relationship_evidence else 0.0,
                "predicted_loyalty": relationship_evidence.predicted_loyalty if relationship_evidence else 0.5,
                "strength_score": relationship_evidence.strength_score if relationship_evidence else 0.5,
            },
            secondary_assessments={
                "relationship_type": primary_type,  # Moved here - strings go in secondary_assessments
                "primary_relationship_type": primary_type,
                "relationship_strength": relationship_evidence.relationship_strength if relationship_evidence else "moderate",
                "advocacy_likelihood": relationship_evidence.advocacy_likelihood if relationship_evidence else 0.5,
                "recommended_engagement_strategy": relationship_evidence.recommended_engagement_strategy if relationship_evidence else None,
            },
            recommendations={
                "mechanisms": recommended_mechanisms,
                "mechanism_weights": mechanism_weights,
                "engagement_tone": engagement_tone,
                "messaging_avoid": messaging_avoid,
                "ad_templates": relationship_evidence.ad_templates if relationship_evidence else [],
            },
        )
    
    async def _query_construct_specific(
        self,
        source: IntelligenceSourceType,
        atom_input: AtomInput,
    ) -> Optional[IntelligenceEvidence]:
        """
        Query construct-specific sources for relationship intelligence.
        
        Relationship intelligence gets evidence from:
        - GRAPH_EMERGENCE: Stored relationships from Neo4j
        - NONCONSCIOUS_SIGNALS: Live text analysis for relationship signals
        - BANDIT_POSTERIORS: Learned relationship-mechanism effectiveness
        """
        if source == IntelligenceSourceType.GRAPH_EMERGENCE:
            return await self._query_stored_relationships(atom_input)
        
        if source == IntelligenceSourceType.NONCONSCIOUS_SIGNALS:
            return await self._query_live_relationship_signals(atom_input)
        
        if source == IntelligenceSourceType.BANDIT_POSTERIORS:
            return await self._query_relationship_effectiveness(atom_input)
        
        return None
    
    async def _query_stored_relationships(
        self,
        atom_input: AtomInput,
    ) -> Optional[IntelligenceEvidence]:
        """Query stored relationships from Neo4j."""
        brand_id = None
        if atom_input.request_context:
            brand_id = getattr(atom_input.request_context, "brand_id", None)
        
        if not brand_id:
            return None
        
        graph_builder = await self._get_relationship_graph_builder()
        if not graph_builder:
            return None
        
        try:
            distribution = await graph_builder.get_brand_relationship_distribution(brand_id)
            primary_type_result = await graph_builder.get_primary_relationship_type(brand_id)
            
            if distribution and primary_type_result:
                primary_type, count = primary_type_result
                return IntelligenceEvidence(
                    source_type=IntelligenceSourceType.GRAPH_EMERGENCE,
                    construct=self.TARGET_CONSTRUCT,
                    value=distribution.get(primary_type, {}).get('avg_confidence', 0.5),
                    confidence=0.8 if count >= 10 else 0.5,
                    metadata={
                        "primary_relationship_type": primary_type,
                        "distribution": distribution,
                        "signal_count": count,
                    },
                    timestamp=datetime.now(timezone.utc),
                    strength=EvidenceStrength.STRONG if count >= 10 else EvidenceStrength.MODERATE,
                )
        except Exception as e:
            logger.warning(f"Error querying stored relationships: {e}")
        
        return None
    
    async def _query_live_relationship_signals(
        self,
        atom_input: AtomInput,
    ) -> Optional[IntelligenceEvidence]:
        """Query live relationship signals from text analysis."""
        if not atom_input.request_context:
            return None
        
        review_texts = getattr(atom_input.request_context, "review_texts", []) or []
        social_texts = getattr(atom_input.request_context, "social_texts", []) or []
        brand_id = getattr(atom_input.request_context, "brand_id", None)
        
        if not (review_texts or social_texts) or not brand_id:
            return None
        
        try:
            detector = self._get_relationship_detector()
            texts = []
            
            for text in review_texts:
                if isinstance(text, str):
                    texts.append({'text': text, 'channel': ObservationChannel.CUSTOMER_REVIEWS})
                elif isinstance(text, dict):
                    texts.append(text)
            
            for text in social_texts:
                if isinstance(text, str):
                    texts.append({'text': text, 'channel': ObservationChannel.SOCIAL_SIGNALS})
                elif isinstance(text, dict):
                    texts.append(text)
            
            if texts:
                relationship = detector.analyze_texts(texts, brand_id)
                return IntelligenceEvidence(
                    source_type=IntelligenceSourceType.NONCONSCIOUS_SIGNALS,
                    construct=self.TARGET_CONSTRUCT,
                    value=relationship.primary_confidence,
                    confidence=min(0.9, 0.5 + len(texts) * 0.05),
                    metadata={
                        "relationship_type": relationship.primary_relationship_type.value,
                        "confidence": relationship.primary_confidence,
                        "signal_count": relationship.signal_count,
                    },
                    timestamp=datetime.now(timezone.utc),
                    strength=EvidenceStrength.STRONG if len(texts) >= 5 else EvidenceStrength.MODERATE,
                )
        except Exception as e:
            logger.warning(f"Error analyzing live relationship signals: {e}")
        
        return None
    
    async def _query_relationship_effectiveness(
        self,
        atom_input: AtomInput,
    ) -> Optional[IntelligenceEvidence]:
        """Query learned relationship-mechanism effectiveness from bandits."""
        # This would query Thompson Sampling posteriors for relationship effectiveness
        # For now, return None as this requires bandit integration
        return None


# =============================================================================
# FACTORY
# =============================================================================

def create_relationship_intelligence_atom(
    bridge: "InteractionBridge",
    blackboard: Optional["BlackboardService"] = None,
) -> RelationshipIntelligenceAtom:
    """Create a relationship intelligence atom."""
    from adam.atoms.models.atom_io import AtomConfig, AtomTier
    
    config = AtomConfig(
        atom_id="atom_relationship_intelligence",
        atom_type=AtomType.CUSTOM,
        tier=AtomTier.STANDARD,
        use_claude_fusion=False,  # Rule-based fusion
        required_sources=[IntelligenceSourceType.GRAPH_EMERGENCE],
        optional_sources=[
            IntelligenceSourceType.NONCONSCIOUS_SIGNALS,
            IntelligenceSourceType.BANDIT_POSTERIORS,
        ],
    )
    
    return RelationshipIntelligenceAtom(
        config=config,
        bridge=bridge,
        blackboard=blackboard,
    )
