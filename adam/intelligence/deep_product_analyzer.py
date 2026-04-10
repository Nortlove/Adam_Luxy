# =============================================================================
# Deep Product Page Analyzer
# Location: adam/intelligence/deep_product_analyzer.py
# =============================================================================

"""
Deep Product Page Psychological Analysis

This analyzer treats the product listing as an ADVERTISEMENT and extracts:
1. Brand Identity & Positioning - What identity is the brand claiming?
2. Persuasion Mechanisms - Which Cialdini principles are being used?
3. Psychological Triggers - What nonconscious processes are activated?
4. Value Proposition Architecture - Functional, emotional, social, self-expressive
5. Target Archetype Signals - Who is this product positioned for?
6. Self-Concept Appeal - How should the buyer see themselves?

The product page IS the advertisement. We analyze it as such.
"""

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Import Brand Personality models
try:
    from adam.intelligence.models.brand_personality import (
        BrandPersonalityProfile,
        BrandArchetype as BrandPersonalityArchetype,
        BrandRelationshipRole,
        BrandVoiceStyle,
        GenderImpression,
        BrandBigFive,
        BrandBigFiveTrait,
        AakerBrandPersonality,
        AakerDimension,
        BrandDemographicImpression,
        BrandConsumerRelationship,
        ConsumerAttractionDynamics,
        BrandVoiceCharacteristics,
        BrandMechanismPreferences,
    )
    BRAND_PERSONALITY_AVAILABLE = True
except ImportError:
    BRAND_PERSONALITY_AVAILABLE = False

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False


# =============================================================================
# PERSUASION MECHANISM TAXONOMY
# =============================================================================

class PersuasionMechanism(str, Enum):
    """Cialdini's principles + extensions."""
    # Cialdini's Classic 6
    RECIPROCITY = "reciprocity"  # Free bonuses, included accessories
    COMMITMENT_CONSISTENCY = "commitment_consistency"  # Reviews, ratings, "verified"
    SOCIAL_PROOF = "social_proof"  # Review counts, bestseller, "customers also bought"
    AUTHORITY = "authority"  # Expert endorsements, certifications, professional
    LIKING = "liking"  # Relatable imagery, brand personality, lifestyle
    SCARCITY = "scarcity"  # Limited stock, time pressure, exclusivity
    
    # Extended Mechanisms
    UNITY = "unity"  # Shared identity, tribe, community
    ANCHORING = "anchoring"  # Price comparisons, "was $X now $Y"
    LOSS_AVERSION = "loss_aversion"  # "Don't miss out", protection language
    DEFAULT_EFFECT = "default_effect"  # Pre-selected options, bundles
    FRAMING = "framing"  # Gain vs loss framing


class EmotionalTrigger(str, Enum):
    """Emotional appeals in product positioning."""
    FEAR = "fear"  # Fear of missing out, fear of failure, fear of judgment
    ASPIRATION = "aspiration"  # Status, achievement, becoming better
    BELONGING = "belonging"  # Community, acceptance, fitting in
    SECURITY = "security"  # Safety, protection, reliability
    EXCITEMENT = "excitement"  # Novelty, adventure, discovery
    COMFORT = "comfort"  # Ease, convenience, familiarity
    PRIDE = "pride"  # Accomplishment, ownership, showing off
    CARE = "care"  # Nurturing, protecting loved ones


class BrandArchetype(str, Enum):
    """Brand personality archetypes (Jung/Mark framework)."""
    INNOCENT = "innocent"  # Pure, optimistic, wholesome
    SAGE = "sage"  # Wise, knowledgeable, expert
    EXPLORER = "explorer"  # Adventurous, pioneering, independent
    OUTLAW = "outlaw"  # Rebellious, disruptive, revolutionary
    MAGICIAN = "magician"  # Transformative, visionary, innovative
    HERO = "hero"  # Courageous, determined, powerful
    LOVER = "lover"  # Passionate, sensual, intimate
    JESTER = "jester"  # Fun, playful, entertaining
    EVERYMAN = "everyman"  # Relatable, humble, authentic
    CAREGIVER = "caregiver"  # Nurturing, protective, supportive
    RULER = "ruler"  # Authoritative, premium, exclusive
    CREATOR = "creator"  # Innovative, artistic, imaginative


# =============================================================================
# DATA MODELS
# =============================================================================

@dataclass
class MechanismDetection:
    """A detected persuasion mechanism with evidence."""
    mechanism: PersuasionMechanism
    confidence: float  # 0-1
    evidence: List[str]  # Quotes/elements that indicate this mechanism
    strength: str  # "subtle", "moderate", "strong"
    location: str  # Where in the listing: "title", "bullets", "description", "images"


@dataclass
class EmotionalAppeal:
    """Detected emotional trigger."""
    trigger: EmotionalTrigger
    intensity: float  # 0-1
    evidence: List[str]
    target_response: str  # What feeling should the buyer have


@dataclass
class ValueProposition:
    """Categorized value proposition."""
    proposition_type: str  # "functional", "emotional", "social", "self_expressive"
    statement: str
    benefit: str
    evidence_from_listing: str


@dataclass
class DeepProductAnalysis:
    """
    Complete psychological analysis of a product listing.
    
    This treats the product page as an advertisement and extracts
    all psychological positioning elements.
    """
    # Basic Product Info
    product_id: str
    title: str
    brand: str
    category: str
    price: Optional[float]
    
    # Brand Positioning
    brand_archetype: BrandArchetype
    brand_archetype_confidence: float
    brand_personality_traits: List[str]
    brand_voice_tone: List[str]
    brand_identity_claims: List[str]  # What identity the brand claims
    
    # Self-Concept Appeal
    buyer_identity_projection: str  # How buyer should see themselves
    social_identity_signals: List[str]  # What group membership this signals
    aspirational_elements: List[str]  # What lifestyle/status this promises
    self_expressive_value: str  # What owning this says about you
    
    # Persuasion Mechanisms
    mechanisms_detected: List[MechanismDetection] = field(default_factory=list)
    primary_mechanism: Optional[PersuasionMechanism] = None
    mechanism_sophistication: str = "basic"  # "basic", "moderate", "sophisticated"
    
    # Emotional Appeals
    emotional_appeals: List[EmotionalAppeal] = field(default_factory=list)
    primary_emotion_targeted: Optional[EmotionalTrigger] = None
    emotional_journey_intended: List[str] = field(default_factory=list)
    
    # Value Propositions
    value_propositions: List[ValueProposition] = field(default_factory=list)
    core_functional_benefit: str = ""
    core_emotional_benefit: str = ""
    core_social_benefit: str = ""
    
    # Psychological Triggers
    loss_aversion_triggers: List[str] = field(default_factory=list)
    gain_framing_elements: List[str] = field(default_factory=list)
    urgency_elements: List[str] = field(default_factory=list)
    trust_signals: List[str] = field(default_factory=list)
    
    # Target Customer Profile
    target_archetype: str = ""
    target_archetype_confidence: float = 0.0
    secondary_archetypes: Dict[str, float] = field(default_factory=dict)
    target_regulatory_focus: str = ""  # "promotion" or "prevention"
    target_construal_level: str = ""  # "abstract" or "concrete"
    
    # Nonconscious Process Predictions
    system1_triggers: List[str] = field(default_factory=list)  # Fast, intuitive
    heuristics_activated: List[str] = field(default_factory=list)
    cognitive_biases_leveraged: List[str] = field(default_factory=list)
    
    # Research Mappings
    research_principles_applied: List[Dict[str, str]] = field(default_factory=list)
    
    # Metadata
    analysis_timestamp: datetime = field(default_factory=datetime.utcnow)
    analysis_confidence: float = 0.0
    raw_product_data: Dict = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "product_id": self.product_id,
            "title": self.title,
            "brand": self.brand,
            "category": self.category,
            "price": self.price,
            "brand_archetype": self.brand_archetype.value if self.brand_archetype else None,
            "brand_archetype_confidence": self.brand_archetype_confidence,
            "brand_personality_traits": self.brand_personality_traits,
            "brand_identity_claims": self.brand_identity_claims,
            "buyer_identity_projection": self.buyer_identity_projection,
            "social_identity_signals": self.social_identity_signals,
            "aspirational_elements": self.aspirational_elements,
            "mechanisms_detected": [
                {
                    "mechanism": m.mechanism.value,
                    "confidence": m.confidence,
                    "evidence": m.evidence,
                    "strength": m.strength,
                }
                for m in self.mechanisms_detected
            ],
            "primary_mechanism": self.primary_mechanism.value if self.primary_mechanism else None,
            "emotional_appeals": [
                {
                    "trigger": e.trigger.value,
                    "intensity": e.intensity,
                    "evidence": e.evidence,
                }
                for e in self.emotional_appeals
            ],
            "primary_emotion_targeted": self.primary_emotion_targeted.value if self.primary_emotion_targeted else None,
            "value_propositions": [
                {
                    "type": v.proposition_type,
                    "statement": v.statement,
                    "benefit": v.benefit,
                }
                for v in self.value_propositions
            ],
            "target_archetype": self.target_archetype,
            "target_archetype_confidence": self.target_archetype_confidence,
            "target_regulatory_focus": self.target_regulatory_focus,
            "system1_triggers": self.system1_triggers,
            "heuristics_activated": self.heuristics_activated,
            "research_principles_applied": self.research_principles_applied,
            "analysis_confidence": self.analysis_confidence,
        }


# =============================================================================
# DEEP PRODUCT ANALYZER
# =============================================================================

DEEP_ANALYSIS_PROMPT = '''You are an expert in consumer psychology, advertising research, and behavioral economics.

Analyze this product listing AS AN ADVERTISEMENT. The product page is designed to convert browsers into buyers. Extract every psychological element being used.

PRODUCT DATA:
Title: {title}
Brand: {brand}
Price: {price}
Category: {category}

Bullet Points / Key Features:
{bullet_points}

Description:
{description}

Return a comprehensive JSON analysis:

{{
    "brand_analysis": {{
        "brand_archetype": "innocent|sage|explorer|outlaw|magician|hero|lover|jester|everyman|caregiver|ruler|creator",
        "brand_archetype_confidence": 0.0-1.0,
        "brand_personality_traits": ["trait1", "trait2", "trait3"],
        "brand_voice_tone": ["professional", "friendly", etc.],
        "brand_identity_claims": ["What identity/values the brand claims to represent"]
    }},
    
    "self_concept_appeal": {{
        "buyer_identity_projection": "How the buyer should see themselves with this product",
        "social_identity_signals": ["What tribe/group this signals membership in"],
        "aspirational_elements": ["What lifestyle or status this promises"],
        "self_expressive_value": "What owning this product says about you"
    }},
    
    "persuasion_mechanisms": [
        {{
            "mechanism": "social_proof|authority|scarcity|reciprocity|liking|commitment_consistency|unity|anchoring|loss_aversion|framing",
            "confidence": 0.0-1.0,
            "evidence": ["Specific text/elements that show this mechanism"],
            "strength": "subtle|moderate|strong",
            "location": "title|bullets|description|images|reviews"
        }}
    ],
    
    "emotional_appeals": [
        {{
            "trigger": "fear|aspiration|belonging|security|excitement|comfort|pride|care",
            "intensity": 0.0-1.0,
            "evidence": ["Text that triggers this emotion"],
            "target_response": "What feeling should the buyer have"
        }}
    ],
    
    "value_propositions": [
        {{
            "type": "functional|emotional|social|self_expressive",
            "statement": "The value proposition statement",
            "benefit": "The specific benefit",
            "evidence": "Where this appears in the listing"
        }}
    ],
    
    "psychological_triggers": {{
        "loss_aversion_triggers": ["Elements that trigger fear of missing out or loss"],
        "gain_framing_elements": ["Elements that frame benefits as gains"],
        "urgency_elements": ["Time pressure or scarcity elements"],
        "trust_signals": ["Elements that build credibility"]
    }},
    
    "target_customer": {{
        "primary_archetype": "Achiever|Explorer|Guardian|Connector|Pragmatist|Analyzer|Rebel|Nurturer",
        "archetype_confidence": 0.0-1.0,
        "secondary_archetypes": {{"archetype": confidence}},
        "regulatory_focus": "promotion|prevention",
        "construal_level": "abstract|concrete",
        "reasoning": "Why this archetype is targeted"
    }},
    
    "nonconscious_processes": {{
        "system1_triggers": ["Fast, intuitive processing triggers"],
        "heuristics_activated": ["Mental shortcuts likely used: availability, anchoring, social proof, authority, etc."],
        "cognitive_biases_leveraged": ["Specific biases: loss aversion, endowment effect, bandwagon, etc."]
    }},
    
    "research_mappings": [
        {{
            "principle": "Name of psychological principle",
            "researcher": "Cialdini, Kahneman, etc.",
            "application": "How it's applied in this listing",
            "evidence": "Specific element showing this"
        }}
    ],
    
    "analysis_confidence": 0.0-1.0
}}

IMPORTANT:
- This is a product listing, treat it as a carefully crafted advertisement
- Extract SPECIFIC evidence from the text, don't just make generic observations
- Consider what NONCONSCIOUS processes are being triggered
- Map to actual research and psychological principles
- Be precise about which mechanisms are being used and how strong they are

Return ONLY valid JSON.'''


# =============================================================================
# BRAND-AS-PERSON ANALYSIS PROMPT
# =============================================================================

BRAND_AS_PERSON_PROMPT = '''You are an expert in brand psychology, consumer behavior, and personality theory.

Analyze this BRAND as if it were a PERSON. The brand has personality traits, values, a communication style, and attracts certain types of people.

BRAND: {brand}
PRODUCT: {title}
CATEGORY: {category}

PRODUCT COPY / BRAND MESSAGING:
{bullet_points}

{description}

Treat the brand as a HUMAN BEING and return detailed JSON:

{{
    "brand_as_person": {{
        "description_as_person": "Describe this brand as if it were a human being - age, appearance, demeanor, how they carry themselves",
        "age_impression": "How old does this brand feel? (e.g., 'Late 40s - mature, experienced, proven')",
        "age_range_low": 25,
        "age_range_high": 55,
        "gender_impression": "masculine|feminine|neutral|androgynous",
        "gender_reasoning": "Why this gender impression",
        "socioeconomic_impression": "What class does this brand project? (working class, middle class, upper-middle, premium/luxury)",
        "occupation_impression": "What job would this person have? Be specific (master craftsman, creative director, etc.)",
        "lifestyle_impression": "How does this person live? Values, hobbies, daily life"
    }},
    
    "brand_big_five": {{
        "openness": {{
            "score": 0.0-1.0,
            "reasoning": "Is the brand creative, traditional, innovative, or conventional?",
            "evidence": ["Specific text showing this"]
        }},
        "conscientiousness": {{
            "score": 0.0-1.0,
            "reasoning": "Is the brand reliable, meticulous, disciplined, or flexible/spontaneous?",
            "evidence": ["Specific text showing this"]
        }},
        "extraversion": {{
            "score": 0.0-1.0,
            "reasoning": "Is the brand outgoing, energetic, bold, or reserved/quiet?",
            "evidence": ["Specific text showing this"]
        }},
        "agreeableness": {{
            "score": 0.0-1.0,
            "reasoning": "Is the brand friendly, warm, cooperative, or competitive/tough?",
            "evidence": ["Specific text showing this"]
        }},
        "neuroticism": {{
            "score": 0.0-1.0,
            "reasoning": "Is the brand anxious/reactive or calm/stable/confident? (low = calm, high = anxious)",
            "evidence": ["Specific text showing this"]
        }}
    }},
    
    "aaker_brand_personality": {{
        "sincerity": {{
            "score": 0.0-1.0,
            "facets": ["Which of: down-to-earth, honest, wholesome, cheerful"]
        }},
        "excitement": {{
            "score": 0.0-1.0,
            "facets": ["Which of: daring, spirited, imaginative, up-to-date"]
        }},
        "competence": {{
            "score": 0.0-1.0,
            "facets": ["Which of: reliable, intelligent, successful"]
        }},
        "sophistication": {{
            "score": 0.0-1.0,
            "facets": ["Which of: upper-class, charming, glamorous"]
        }},
        "ruggedness": {{
            "score": 0.0-1.0,
            "facets": ["Which of: outdoorsy, tough, masculine"]
        }}
    }},
    
    "brand_archetype": {{
        "primary": "innocent|sage|explorer|outlaw|magician|hero|lover|jester|everyman|caregiver|ruler|creator",
        "confidence": 0.0-1.0,
        "reasoning": "Why this archetype",
        "secondary_archetypes": {{"archetype": confidence}}
    }},
    
    "brand_consumer_relationship": {{
        "relationship_role": "mentor|friend|partner|servant|admired_expert|inspiring_leader|protective_guardian|enabler|trusted_advisor|playmate",
        "role_description": "Describe the brand's role in detail",
        "relationship_type": "committed partnership, casual acquaintance, dependency, fling, etc.",
        "emotional_bond_fulfilled": "What emotional need does this relationship fulfill?",
        "power_balance": "equal|brand-dominant|consumer-dominant",
        "trust_foundation": "What is the basis of trust? (competence, reliability, shared values, etc.)"
    }},
    
    "consumer_attraction": {{
        "attracts_personality_types": ["What personality types are drawn to this brand"],
        "attracts_archetypes": ["ACHIEVER", "EXPLORER", "GUARDIAN", "CONNECTOR", etc.],
        "archetype_attraction_scores": {{"ACHIEVER": 0.8, "EXPLORER": 0.3}},
        "identity_needs_fulfilled": ["What identity needs does buying this brand fulfill?"],
        "social_signaling_value": "What does owning this brand signal to others?",
        "self_concept_enhancement": "How does this brand make the buyer feel about themselves?",
        "emotional_needs_met": ["What emotional needs does this brand meet?"],
        "values_alignment": ["What values must a consumer hold to be attracted?"]
    }},
    
    "brand_voice": {{
        "voice_style": "authoritative|conversational|inspirational|technical|playful|sophisticated|rugged|nurturing|provocative|reassuring",
        "how_it_speaks": "Describe how this brand talks to consumers",
        "vocabulary_style": "Technical? Casual? Authoritative? Professional?",
        "emotional_register": "Warm? Cold? Encouraging? Demanding? Playful?",
        "communication_values": ["What values come through in how it communicates"],
        "formality": 0.0-1.0,
        "energy": 0.0-1.0,
        "humor": 0.0-1.0,
        "directness": 0.0-1.0
    }},
    
    "mechanism_preferences": {{
        "preferred_mechanisms": ["Mechanisms that fit this brand's personality"],
        "mechanism_alignment": {{"social_proof": 0.8, "scarcity": 0.3}},
        "forbidden_mechanisms": ["Mechanisms that would damage brand integrity"],
        "reasoning": "Why certain mechanisms fit or don't fit"
    }}
}}

IMPORTANT:
- Think of the brand as a REAL PERSON standing in front of you
- Extract SPECIFIC evidence from the product copy
- Consider the brand's entire history and positioning, not just this one product
- Be precise with scores - don't just use 0.5 for everything

Return ONLY valid JSON.'''


class DeepProductAnalyzer:
    """
    Deep psychological analysis of product listings.
    
    Treats the product page as an advertisement and extracts all
    psychological positioning elements used to convert buyers.
    """
    
    def __init__(self, api_key: Optional[str] = None, model: str = "claude-sonnet-4-20250514"):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self.model = model
        self._client = None
    
    def _get_client(self):
        if not ANTHROPIC_AVAILABLE:
            raise ImportError("Anthropic library required")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY required")
        if self._client is None:
            self._client = anthropic.Anthropic(api_key=self.api_key)
        return self._client
    
    async def analyze_product_listing(
        self,
        product_id: str,
        title: str,
        brand: str,
        price: Optional[float],
        category: str,
        bullet_points: Optional[str],
        description: Optional[str],
        images: Optional[List[str]] = None,
        raw_data: Optional[Dict] = None,
    ) -> DeepProductAnalysis:
        """
        Perform deep psychological analysis of a product listing.
        
        Args:
            product_id: Unique identifier (ASIN, SKU, etc.)
            title: Product title
            brand: Brand name
            price: Price (if available)
            category: Product category
            bullet_points: Key features / bullet points
            description: Full product description
            images: Image URLs (for future multimodal analysis)
            raw_data: Original scraped data
            
        Returns:
            DeepProductAnalysis with complete psychological profile
        """
        logger.info(f"Deep analyzing product: {brand} - {title[:50]}...")
        
        # Format the prompt
        prompt = DEEP_ANALYSIS_PROMPT.format(
            title=title,
            brand=brand or "Unknown",
            price=f"${price}" if price else "Not specified",
            category=category or "General",
            bullet_points=bullet_points or "Not available",
            description=description or "Not available",
        )
        
        try:
            client = self._get_client()
            response = client.messages.create(
                model=self.model,
                max_tokens=4000,
                messages=[{"role": "user", "content": prompt}]
            )
            
            raw_response = response.content[0].text
            
            # Parse JSON
            try:
                analysis = json.loads(raw_response)
            except json.JSONDecodeError:
                import re
                json_match = re.search(r'\{[\s\S]*\}', raw_response)
                if json_match:
                    analysis = json.loads(json_match.group())
                else:
                    raise ValueError("Could not parse Claude response")
            
            # Build the analysis object
            return self._build_analysis(
                product_id=product_id,
                title=title,
                brand=brand,
                price=price,
                category=category,
                analysis=analysis,
                raw_data=raw_data,
            )
            
        except Exception as e:
            logger.error(f"Deep analysis failed: {e}")
            # Return minimal analysis
            return DeepProductAnalysis(
                product_id=product_id,
                title=title,
                brand=brand or "",
                category=category or "",
                price=price,
                brand_archetype=BrandArchetype.EVERYMAN,
                brand_archetype_confidence=0.0,
                brand_personality_traits=[],
                brand_voice_tone=[],
                brand_identity_claims=[],
                buyer_identity_projection="",
                social_identity_signals=[],
                aspirational_elements=[],
                self_expressive_value="",
                analysis_confidence=0.0,
            )
    
    def _build_analysis(
        self,
        product_id: str,
        title: str,
        brand: str,
        price: Optional[float],
        category: str,
        analysis: Dict,
        raw_data: Optional[Dict],
    ) -> DeepProductAnalysis:
        """Build DeepProductAnalysis from Claude's response."""
        
        # Parse brand archetype
        brand_data = analysis.get("brand_analysis", {})
        archetype_str = brand_data.get("brand_archetype", "everyman").lower()
        try:
            brand_archetype = BrandArchetype(archetype_str)
        except ValueError:
            brand_archetype = BrandArchetype.EVERYMAN
        
        # Parse mechanisms
        mechanisms = []
        for m in analysis.get("persuasion_mechanisms", []):
            try:
                mechanisms.append(MechanismDetection(
                    mechanism=PersuasionMechanism(m.get("mechanism", "social_proof")),
                    confidence=m.get("confidence", 0.5),
                    evidence=m.get("evidence", []),
                    strength=m.get("strength", "moderate"),
                    location=m.get("location", "description"),
                ))
            except (ValueError, KeyError):
                continue
        
        # Determine primary mechanism
        primary_mechanism = None
        if mechanisms:
            strongest = max(mechanisms, key=lambda x: x.confidence)
            primary_mechanism = strongest.mechanism
        
        # Parse emotional appeals
        emotional_appeals = []
        for e in analysis.get("emotional_appeals", []):
            try:
                emotional_appeals.append(EmotionalAppeal(
                    trigger=EmotionalTrigger(e.get("trigger", "aspiration")),
                    intensity=e.get("intensity", 0.5),
                    evidence=e.get("evidence", []),
                    target_response=e.get("target_response", ""),
                ))
            except (ValueError, KeyError):
                continue
        
        primary_emotion = None
        if emotional_appeals:
            strongest = max(emotional_appeals, key=lambda x: x.intensity)
            primary_emotion = strongest.trigger
        
        # Parse value propositions
        value_props = []
        for v in analysis.get("value_propositions", []):
            value_props.append(ValueProposition(
                proposition_type=v.get("type", "functional"),
                statement=v.get("statement", ""),
                benefit=v.get("benefit", ""),
                evidence_from_listing=v.get("evidence", ""),
            ))
        
        # Extract core benefits
        core_functional = ""
        core_emotional = ""
        core_social = ""
        for vp in value_props:
            if vp.proposition_type == "functional" and not core_functional:
                core_functional = vp.benefit
            elif vp.proposition_type == "emotional" and not core_emotional:
                core_emotional = vp.benefit
            elif vp.proposition_type == "social" and not core_social:
                core_social = vp.benefit
        
        # Parse target customer
        target = analysis.get("target_customer", {})
        
        # Parse nonconscious processes
        nonconscious = analysis.get("nonconscious_processes", {})
        
        # Parse psychological triggers
        psych_triggers = analysis.get("psychological_triggers", {})
        
        # Parse self-concept
        self_concept = analysis.get("self_concept_appeal", {})
        
        return DeepProductAnalysis(
            product_id=product_id,
            title=title,
            brand=brand or "",
            category=category or "",
            price=price,
            
            # Brand
            brand_archetype=brand_archetype,
            brand_archetype_confidence=brand_data.get("brand_archetype_confidence", 0.5),
            brand_personality_traits=brand_data.get("brand_personality_traits", []),
            brand_voice_tone=brand_data.get("brand_voice_tone", []),
            brand_identity_claims=brand_data.get("brand_identity_claims", []),
            
            # Self-concept
            buyer_identity_projection=self_concept.get("buyer_identity_projection", ""),
            social_identity_signals=self_concept.get("social_identity_signals", []),
            aspirational_elements=self_concept.get("aspirational_elements", []),
            self_expressive_value=self_concept.get("self_expressive_value", ""),
            
            # Mechanisms
            mechanisms_detected=mechanisms,
            primary_mechanism=primary_mechanism,
            mechanism_sophistication="moderate",
            
            # Emotions
            emotional_appeals=emotional_appeals,
            primary_emotion_targeted=primary_emotion,
            
            # Value props
            value_propositions=value_props,
            core_functional_benefit=core_functional,
            core_emotional_benefit=core_emotional,
            core_social_benefit=core_social,
            
            # Triggers
            loss_aversion_triggers=psych_triggers.get("loss_aversion_triggers", []),
            gain_framing_elements=psych_triggers.get("gain_framing_elements", []),
            urgency_elements=psych_triggers.get("urgency_elements", []),
            trust_signals=psych_triggers.get("trust_signals", []),
            
            # Target
            target_archetype=target.get("primary_archetype", ""),
            target_archetype_confidence=target.get("archetype_confidence", 0.5),
            secondary_archetypes=target.get("secondary_archetypes", {}),
            target_regulatory_focus=target.get("regulatory_focus", "promotion"),
            target_construal_level=target.get("construal_level", "concrete"),
            
            # Nonconscious
            system1_triggers=nonconscious.get("system1_triggers", []),
            heuristics_activated=nonconscious.get("heuristics_activated", []),
            cognitive_biases_leveraged=nonconscious.get("cognitive_biases_leveraged", []),
            
            # Research
            research_principles_applied=analysis.get("research_mappings", []),
            
            # Meta
            analysis_confidence=analysis.get("analysis_confidence", 0.7),
            raw_product_data=raw_data or {},
        )
    
    # =========================================================================
    # BRAND-AS-PERSON ANALYSIS
    # =========================================================================
    
    async def extract_brand_personality(
        self,
        brand: str,
        title: str,
        category: str,
        bullet_points: Optional[str],
        description: Optional[str],
        product_id: Optional[str] = None,
    ) -> Optional["BrandPersonalityProfile"]:
        """
        Extract comprehensive Brand-as-Person personality profile.
        
        This treats the brand as if it were a human being and extracts:
        - Brand Big Five personality
        - Aaker brand personality dimensions
        - Brand archetype (Jung/Mark)
        - Demographic impression (age, gender, class)
        - Brand-consumer relationship dynamics
        - Consumer attraction patterns
        - Brand voice characteristics
        
        Args:
            brand: Brand name
            title: Product title
            category: Product category
            bullet_points: Key features / bullet points
            description: Full product description
            product_id: Optional product ID for tracking
            
        Returns:
            BrandPersonalityProfile or None if extraction fails
        """
        if not BRAND_PERSONALITY_AVAILABLE:
            logger.warning("Brand personality models not available")
            return None
        
        logger.info(f"Extracting brand-as-person profile for: {brand}")
        
        # Format the prompt
        prompt = BRAND_AS_PERSON_PROMPT.format(
            brand=brand or "Unknown Brand",
            title=title,
            category=category or "General",
            bullet_points=bullet_points or "Not available",
            description=description or "Not available",
        )
        
        try:
            client = self._get_client()
            response = client.messages.create(
                model=self.model,
                max_tokens=4000,
                messages=[{"role": "user", "content": prompt}]
            )
            
            raw_response = response.content[0].text
            
            # Parse JSON
            try:
                data = json.loads(raw_response)
            except json.JSONDecodeError:
                import re
                json_match = re.search(r'\{[\s\S]*\}', raw_response)
                if json_match:
                    data = json.loads(json_match.group())
                else:
                    raise ValueError("Could not parse Claude response")
            
            # Build the BrandPersonalityProfile
            return self._build_brand_personality_profile(
                brand=brand,
                data=data,
                product_id=product_id,
            )
            
        except Exception as e:
            logger.error(f"Brand personality extraction failed: {e}")
            return None
    
    def _build_brand_personality_profile(
        self,
        brand: str,
        data: Dict,
        product_id: Optional[str] = None,
    ) -> "BrandPersonalityProfile":
        """Build BrandPersonalityProfile from Claude's response."""
        
        # Brand as person (demographic impression)
        bap = data.get("brand_as_person", {})
        
        # Parse gender impression
        gender_str = bap.get("gender_impression", "neutral").lower()
        try:
            gender = GenderImpression(gender_str)
        except ValueError:
            gender = GenderImpression.NEUTRAL
        
        demographic = BrandDemographicImpression(
            description_as_person=bap.get("description_as_person", ""),
            age_impression=bap.get("age_impression", ""),
            age_range_low=bap.get("age_range_low", 30),
            age_range_high=bap.get("age_range_high", 50),
            gender_impression=gender,
            gender_reasoning=bap.get("gender_reasoning", ""),
            socioeconomic_impression=bap.get("socioeconomic_impression", ""),
            occupation_impression=bap.get("occupation_impression", ""),
            lifestyle_impression=bap.get("lifestyle_impression", ""),
        )
        
        # Brand Big Five
        b5_data = data.get("brand_big_five", {})
        brand_big_five = BrandBigFive(
            openness=BrandBigFiveTrait(
                score=b5_data.get("openness", {}).get("score", 0.5),
                reasoning=b5_data.get("openness", {}).get("reasoning", ""),
                evidence=b5_data.get("openness", {}).get("evidence", []),
            ),
            conscientiousness=BrandBigFiveTrait(
                score=b5_data.get("conscientiousness", {}).get("score", 0.5),
                reasoning=b5_data.get("conscientiousness", {}).get("reasoning", ""),
                evidence=b5_data.get("conscientiousness", {}).get("evidence", []),
            ),
            extraversion=BrandBigFiveTrait(
                score=b5_data.get("extraversion", {}).get("score", 0.5),
                reasoning=b5_data.get("extraversion", {}).get("reasoning", ""),
                evidence=b5_data.get("extraversion", {}).get("evidence", []),
            ),
            agreeableness=BrandBigFiveTrait(
                score=b5_data.get("agreeableness", {}).get("score", 0.5),
                reasoning=b5_data.get("agreeableness", {}).get("reasoning", ""),
                evidence=b5_data.get("agreeableness", {}).get("evidence", []),
            ),
            neuroticism=BrandBigFiveTrait(
                score=b5_data.get("neuroticism", {}).get("score", 0.5),
                reasoning=b5_data.get("neuroticism", {}).get("reasoning", ""),
                evidence=b5_data.get("neuroticism", {}).get("evidence", []),
            ),
        )
        
        # Aaker Brand Personality
        aaker_data = data.get("aaker_brand_personality", {})
        aaker = AakerBrandPersonality(
            sincerity=AakerDimension(
                score=aaker_data.get("sincerity", {}).get("score", 0.5),
                facets_expressed=aaker_data.get("sincerity", {}).get("facets", []),
            ),
            excitement=AakerDimension(
                score=aaker_data.get("excitement", {}).get("score", 0.5),
                facets_expressed=aaker_data.get("excitement", {}).get("facets", []),
            ),
            competence=AakerDimension(
                score=aaker_data.get("competence", {}).get("score", 0.5),
                facets_expressed=aaker_data.get("competence", {}).get("facets", []),
            ),
            sophistication=AakerDimension(
                score=aaker_data.get("sophistication", {}).get("score", 0.5),
                facets_expressed=aaker_data.get("sophistication", {}).get("facets", []),
            ),
            ruggedness=AakerDimension(
                score=aaker_data.get("ruggedness", {}).get("score", 0.5),
                facets_expressed=aaker_data.get("ruggedness", {}).get("facets", []),
            ),
        )
        
        # Brand Archetype
        arch_data = data.get("brand_archetype", {})
        archetype_str = arch_data.get("primary", "everyman").lower()
        try:
            brand_archetype = BrandPersonalityArchetype(archetype_str)
        except ValueError:
            brand_archetype = BrandPersonalityArchetype.EVERYMAN
        
        # Brand-Consumer Relationship
        rel_data = data.get("brand_consumer_relationship", {})
        role_str = rel_data.get("relationship_role", "partner").lower()
        try:
            relationship_role = BrandRelationshipRole(role_str)
        except ValueError:
            relationship_role = BrandRelationshipRole.PARTNER
        
        relationship = BrandConsumerRelationship(
            relationship_role=relationship_role,
            relationship_role_description=rel_data.get("role_description", ""),
            relationship_type=rel_data.get("relationship_type", ""),
            emotional_bond_fulfilled=rel_data.get("emotional_bond_fulfilled", ""),
            power_balance=rel_data.get("power_balance", "equal"),
            trust_foundation=rel_data.get("trust_foundation", ""),
        )
        
        # Consumer Attraction
        attr_data = data.get("consumer_attraction", {})
        attraction = ConsumerAttractionDynamics(
            attracts_personality_types=attr_data.get("attracts_personality_types", []),
            attracts_archetypes=attr_data.get("attracts_archetypes", []),
            archetype_attraction_scores=attr_data.get("archetype_attraction_scores", {}),
            identity_needs_fulfilled=attr_data.get("identity_needs_fulfilled", []),
            social_signaling_value=attr_data.get("social_signaling_value", ""),
            self_concept_enhancement=attr_data.get("self_concept_enhancement", ""),
            emotional_needs_met=attr_data.get("emotional_needs_met", []),
            values_alignment=attr_data.get("values_alignment", []),
        )
        
        # Brand Voice
        voice_data = data.get("brand_voice", {})
        voice_style_str = voice_data.get("voice_style", "conversational").lower()
        try:
            voice_style = BrandVoiceStyle(voice_style_str)
        except ValueError:
            voice_style = BrandVoiceStyle.CONVERSATIONAL
        
        voice = BrandVoiceCharacteristics(
            voice_style=voice_style,
            how_it_speaks=voice_data.get("how_it_speaks", ""),
            vocabulary_style=voice_data.get("vocabulary_style", ""),
            emotional_register=voice_data.get("emotional_register", ""),
            communication_values=voice_data.get("communication_values", []),
            formality=voice_data.get("formality", 0.5),
            energy=voice_data.get("energy", 0.5),
            humor=voice_data.get("humor", 0.3),
            directness=voice_data.get("directness", 0.5),
        )
        
        # Mechanism Preferences
        mech_data = data.get("mechanism_preferences", {})
        mechanism_prefs = BrandMechanismPreferences(
            preferred_mechanisms=mech_data.get("preferred_mechanisms", []),
            mechanism_alignment_scores=mech_data.get("mechanism_alignment", {}),
            forbidden_mechanisms=mech_data.get("forbidden_mechanisms", []),
            mechanism_reasoning={"overall": mech_data.get("reasoning", "")},
        )
        
        # Generate brand_id from brand name
        import hashlib
        brand_id = hashlib.md5(brand.lower().encode()).hexdigest()[:12]
        
        # Build the profile
        return BrandPersonalityProfile(
            brand_id=brand_id,
            brand_name=brand,
            brand_archetype=brand_archetype,
            brand_archetype_confidence=arch_data.get("confidence", 0.7),
            secondary_archetypes=arch_data.get("secondary_archetypes", {}),
            archetype_reasoning=arch_data.get("reasoning", ""),
            brand_big_five=brand_big_five,
            aaker_personality=aaker,
            demographic_impression=demographic,
            consumer_relationship=relationship,
            attraction_dynamics=attraction,
            voice=voice,
            mechanism_preferences=mechanism_prefs,
            source_product_ids=[product_id] if product_id else [],
            analysis_confidence=0.8,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )


# =============================================================================
# SINGLETON
# =============================================================================

_deep_analyzer: Optional[DeepProductAnalyzer] = None


def get_deep_product_analyzer() -> DeepProductAnalyzer:
    """Get or create the deep product analyzer."""
    global _deep_analyzer
    if _deep_analyzer is None:
        _deep_analyzer = DeepProductAnalyzer()
    return _deep_analyzer
