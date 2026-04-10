# =============================================================================
# Deep Review Analyzer
# Location: adam/intelligence/deep_review_analyzer.py
# =============================================================================

"""
Deep Review Psychological Analysis

This analyzer treats each review as a WINDOW INTO CONSUMER PSYCHOLOGY.
Unlike social media posts where people perform, reviews are authentic
expressions focused on one thing: their experience with the product.

We extract:
1. Identity Revelation - Who is this person? What tribe do they belong to?
2. Emotional Journey - Anticipation → Purchase → Use → Long-term
3. Purchase Motivation Archaeology - What triggered the purchase?
4. Psychological Construct Extraction - All 35 constructs with MEANING
5. Nonconscious Process Indicators - System 1 vs System 2 decision
6. Expectation-Reality Analysis - Did the product deliver?

The review is evidence of a completed purchase journey. We extract every insight.
"""

import json
import logging
import os
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False


# =============================================================================
# PURCHASE MOTIVATION TAXONOMY
# =============================================================================

class PurchaseMotivation(str, Enum):
    """What drove the purchase decision."""
    FUNCTIONAL_NEED = "functional_need"  # Needed it to do something
    QUALITY_SEEKING = "quality_seeking"  # Wanted the best
    VALUE_SEEKING = "value_seeking"  # Wanted the best deal
    STATUS_SIGNALING = "status_signaling"  # Wanted others to see
    SELF_REWARD = "self_reward"  # Treating oneself
    GIFT_GIVING = "gift_giving"  # For someone else
    REPLACEMENT = "replacement"  # Old one broke/worn out
    UPGRADE = "upgrade"  # Wanted something better
    IMPULSE = "impulse"  # Spontaneous decision
    RESEARCH_DRIVEN = "research_driven"  # Extensive comparison
    RECOMMENDATION = "recommendation"  # Someone told them to buy
    BRAND_LOYALTY = "brand_loyalty"  # Trusts the brand
    SOCIAL_PROOF = "social_proof"  # Others have it
    FOMO = "fomo"  # Fear of missing out
    PROBLEM_SOLVING = "problem_solving"  # Specific problem to solve


class EmotionalState(str, Enum):
    """Emotional states expressed in reviews."""
    JOY = "joy"
    SATISFACTION = "satisfaction"
    RELIEF = "relief"
    EXCITEMENT = "excitement"
    PRIDE = "pride"
    GRATITUDE = "gratitude"
    DISAPPOINTMENT = "disappointment"
    FRUSTRATION = "frustration"
    REGRET = "regret"
    SURPRISE = "surprise"
    CONFIDENCE = "confidence"
    TRUST = "trust"


class DecisionStyle(str, Enum):
    """How they made the purchase decision."""
    SYSTEM1_INTUITIVE = "system1_intuitive"  # Fast, gut feeling
    SYSTEM2_DELIBERATE = "system2_deliberate"  # Slow, analytical
    MIXED = "mixed"


# =============================================================================
# DATA MODELS
# =============================================================================

@dataclass
class IdentityRevelation:
    """Identity information revealed in the review."""
    self_identification: str  # "As a professional...", "As a mom..."
    inferred_archetype: str
    archetype_confidence: float
    values_expressed: List[str]
    lifestyle_indicators: List[str]
    tribe_signals: List[str]  # What group they belong to
    role_in_purchase: str  # "buyer_for_self", "gift_giver", "business_buyer"


@dataclass
class EmotionalJourney:
    """The emotional arc of the purchase experience."""
    pre_purchase_emotion: Optional[EmotionalState]
    unboxing_emotion: Optional[EmotionalState]
    first_use_emotion: Optional[EmotionalState]
    long_term_emotion: Optional[EmotionalState]
    overall_emotional_tone: str
    emotional_intensity: float  # 0-1
    emotion_evidence: List[str]


@dataclass
class ExpectationAnalysis:
    """How expectations matched reality."""
    expectations_met: bool
    exceeded_expectations: bool
    specific_expectations: List[str]
    reality_description: str
    gap_description: str  # Positive or negative gap
    cognitive_dissonance_indicators: List[str]  # Post-purchase rationalization


@dataclass 
class PurchaseArchaeology:
    """Deep analysis of what drove the purchase."""
    primary_motivation: PurchaseMotivation
    secondary_motivations: List[PurchaseMotivation]
    trigger_event: str  # What made them start looking
    decision_factors: List[str]  # What tipped the scale
    alternatives_considered: List[str]
    influencers: List[str]  # What/who influenced them
    decision_style: DecisionStyle
    research_depth: str  # "minimal", "moderate", "extensive"


@dataclass
class ProductAttributeMention:
    """A product attribute mentioned in the review."""
    attribute: str
    sentiment: str  # "positive", "negative", "neutral"
    importance: float  # 0-1, how much they emphasized it
    exact_quote: str


@dataclass
class DeepReviewAnalysis:
    """
    Complete psychological analysis of a single review.
    
    This is a window into the consumer's mind - their identity,
    emotions, motivations, and decision-making process.
    """
    # Basic Info
    review_id: str
    rating: float
    review_text: str
    
    # Identity Analysis
    identity: IdentityRevelation
    
    # Emotional Analysis
    emotional_journey: EmotionalJourney
    emotions_expressed: List[Tuple[EmotionalState, float]]  # (emotion, intensity)
    
    # Expectation Analysis
    expectations: ExpectationAnalysis
    
    # Purchase Motivation Analysis
    purchase_archaeology: PurchaseArchaeology
    
    # Product Attribute Analysis
    attributes_mentioned: List[ProductAttributeMention]
    positive_attributes: List[str]
    negative_attributes: List[str]
    
    # Psychological Constructs (35 from Enhancement #27)
    construct_scores: Dict[str, float] = field(default_factory=dict)
    construct_evidence: Dict[str, List[str]] = field(default_factory=dict)
    
    # Regulatory Focus
    regulatory_focus: str = ""  # "promotion" or "prevention"
    regulatory_evidence: List[str] = field(default_factory=list)
    
    # Big Five Indicators
    personality_indicators: Dict[str, float] = field(default_factory=dict)
    
    # Nonconscious Indicators
    decision_style: DecisionStyle = DecisionStyle.MIXED
    heuristics_evident: List[str] = field(default_factory=list)
    biases_evident: List[str] = field(default_factory=list)
    
    # Key Quotes
    most_revealing_quotes: List[str] = field(default_factory=list)
    
    # Research Mappings
    research_principles_evident: List[Dict[str, str]] = field(default_factory=list)
    
    # Metadata
    analysis_timestamp: datetime = field(default_factory=datetime.utcnow)
    analysis_confidence: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "review_id": self.review_id,
            "rating": self.rating,
            "identity": {
                "self_identification": self.identity.self_identification,
                "inferred_archetype": self.identity.inferred_archetype,
                "archetype_confidence": self.identity.archetype_confidence,
                "values_expressed": self.identity.values_expressed,
                "tribe_signals": self.identity.tribe_signals,
            },
            "emotional_journey": {
                "overall_tone": self.emotional_journey.overall_emotional_tone,
                "intensity": self.emotional_journey.emotional_intensity,
            },
            "expectations": {
                "met": self.expectations.expectations_met,
                "exceeded": self.expectations.exceeded_expectations,
            },
            "purchase_motivation": {
                "primary": self.purchase_archaeology.primary_motivation.value,
                "trigger": self.purchase_archaeology.trigger_event,
                "decision_style": self.purchase_archaeology.decision_style.value,
            },
            "construct_scores": self.construct_scores,
            "regulatory_focus": self.regulatory_focus,
            "personality_indicators": self.personality_indicators,
            "positive_attributes": self.positive_attributes,
            "negative_attributes": self.negative_attributes,
            "most_revealing_quotes": self.most_revealing_quotes,
            "analysis_confidence": self.analysis_confidence,
        }


# =============================================================================
# DEEP REVIEW ANALYZER
# =============================================================================

DEEP_REVIEW_PROMPT = '''You are an expert consumer psychologist analyzing a product review.

This review represents a COMPLETED PURCHASE JOURNEY. This person:
1. Saw the product listing (was convinced by the "advertisement")
2. Made a purchase decision (nonconscious processes were activated)
3. Used the product (expectation met reality)
4. Felt compelled to write a review (strong emotional response)

Extract EVERY psychological insight from this review. Read between the lines.
What do the words MEAN, not just what they SAY?

PRODUCT: {product_title}
BRAND: {brand}
RATING: {rating}/5

REVIEW TEXT:
"{review_text}"

Return comprehensive JSON analysis:

{{
    "identity_analysis": {{
        "self_identification": "How they identify themselves (e.g., 'as a professional', 'as a mother'). If not explicit, infer from context.",
        "inferred_archetype": "Achiever|Explorer|Guardian|Connector|Pragmatist|Analyzer|Rebel|Nurturer",
        "archetype_confidence": 0.0-1.0,
        "values_expressed": ["Values this person holds based on their language"],
        "lifestyle_indicators": ["What their lifestyle seems to be"],
        "tribe_signals": ["What groups/communities they seem to belong to"],
        "role_in_purchase": "buyer_for_self|gift_giver|business_buyer|household_purchaser"
    }},
    
    "emotional_journey": {{
        "pre_purchase_emotion": "What they felt before buying (anticipation, need, desire, etc.)",
        "unboxing_emotion": "What they felt when receiving/opening",
        "first_use_emotion": "What they felt on first use",
        "long_term_emotion": "What they feel now (if mentioned)",
        "overall_emotional_tone": "Single word describing overall tone",
        "emotional_intensity": 0.0-1.0,
        "emotion_evidence": ["Specific phrases showing emotion"]
    }},
    
    "expectations_analysis": {{
        "expectations_met": true/false,
        "exceeded_expectations": true/false,
        "specific_expectations": ["What they expected before purchase"],
        "reality_description": "What they actually experienced",
        "gap_description": "How reality differed from expectations (positive or negative)",
        "cognitive_dissonance_indicators": ["Signs of post-purchase rationalization"]
    }},
    
    "purchase_archaeology": {{
        "primary_motivation": "functional_need|quality_seeking|value_seeking|status_signaling|self_reward|gift_giving|replacement|upgrade|impulse|research_driven|recommendation|brand_loyalty|social_proof|fomo|problem_solving",
        "secondary_motivations": ["Other motivations"],
        "trigger_event": "What made them start looking for this product",
        "decision_factors": ["What specifically made them choose THIS product"],
        "alternatives_considered": ["Other products they mention considering"],
        "influencers": ["What/who influenced their decision (reviews, friend, ad, etc.)"],
        "decision_style": "system1_intuitive|system2_deliberate|mixed",
        "research_depth": "minimal|moderate|extensive"
    }},
    
    "product_attributes_mentioned": [
        {{
            "attribute": "Name of attribute (quality, price, design, etc.)",
            "sentiment": "positive|negative|neutral",
            "importance": 0.0-1.0,
            "exact_quote": "Their exact words about this attribute"
        }}
    ],
    
    "psychological_constructs": {{
        "conscientiousness": {{"score": 0.0-1.0, "evidence": ["phrases showing this"]}},
        "openness": {{"score": 0.0-1.0, "evidence": []}},
        "extraversion": {{"score": 0.0-1.0, "evidence": []}},
        "agreeableness": {{"score": 0.0-1.0, "evidence": []}},
        "neuroticism": {{"score": 0.0-1.0, "evidence": []}},
        "achievement_motivation": {{"score": 0.0-1.0, "evidence": []}},
        "quality_focus": {{"score": 0.0-1.0, "evidence": []}},
        "value_orientation": {{"score": 0.0-1.0, "evidence": []}},
        "social_orientation": {{"score": 0.0-1.0, "evidence": []}},
        "innovation_seeking": {{"score": 0.0-1.0, "evidence": []}}
    }},
    
    "regulatory_focus": {{
        "focus": "promotion|prevention",
        "evidence": ["Phrases showing promotion focus (gains, achievements) or prevention focus (avoiding loss, safety)"]
    }},
    
    "nonconscious_indicators": {{
        "decision_style": "system1_intuitive|system2_deliberate|mixed",
        "heuristics_evident": ["Mental shortcuts they used: 'brand = quality', 'price = value', etc."],
        "biases_evident": ["Cognitive biases shown: confirmation bias, anchoring, etc."]
    }},
    
    "most_revealing_quotes": [
        "The most psychologically revealing 2-3 sentences from this review"
    ],
    
    "research_principles_evident": [
        {{
            "principle": "Name of psychological principle",
            "researcher": "Cialdini, Kahneman, etc.",
            "evidence": "How this review demonstrates this principle"
        }}
    ],
    
    "analysis_confidence": 0.0-1.0
}}

IMPORTANT:
- Read MEANING, not just words. "It works" means different things from different people.
- Infer identity even if not explicitly stated. Language reveals who we are.
- The emotional journey matters - track how feelings evolved.
- Every review reveals purchase motivation if you look carefully.
- Map to research principles where possible.

Return ONLY valid JSON.'''


class DeepReviewAnalyzer:
    """
    Deep psychological analysis of customer reviews.
    
    Extracts identity, emotion, motivation, and psychological constructs
    from review text to understand the complete consumer psychology.
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
    
    async def analyze_review(
        self,
        review_id: str,
        review_text: str,
        rating: float,
        product_title: str,
        brand: str,
    ) -> DeepReviewAnalysis:
        """
        Perform deep psychological analysis of a review.
        
        Args:
            review_id: Unique identifier
            review_text: The review content
            rating: Star rating (1-5)
            product_title: Product being reviewed
            brand: Brand name
            
        Returns:
            DeepReviewAnalysis with complete psychological profile
        """
        logger.info(f"Deep analyzing review {review_id}")
        
        prompt = DEEP_REVIEW_PROMPT.format(
            product_title=product_title,
            brand=brand,
            rating=rating,
            review_text=review_text,
        )
        
        try:
            client = self._get_client()
            response = client.messages.create(
                model=self.model,
                max_tokens=3000,
                messages=[{"role": "user", "content": prompt}]
            )
            
            raw_response = response.content[0].text
            
            try:
                analysis = json.loads(raw_response)
            except json.JSONDecodeError:
                json_match = re.search(r'\{[\s\S]*\}', raw_response)
                if json_match:
                    analysis = json.loads(json_match.group())
                else:
                    raise ValueError("Could not parse response")
            
            return self._build_analysis(
                review_id=review_id,
                review_text=review_text,
                rating=rating,
                analysis=analysis,
            )
            
        except Exception as e:
            logger.error(f"Deep review analysis failed: {e}")
            return self._create_fallback_analysis(review_id, review_text, rating)
    
    def _build_analysis(
        self,
        review_id: str,
        review_text: str,
        rating: float,
        analysis: Dict,
    ) -> DeepReviewAnalysis:
        """Build DeepReviewAnalysis from Claude's response."""
        
        # Parse identity
        identity_data = analysis.get("identity_analysis", {})
        identity = IdentityRevelation(
            self_identification=identity_data.get("self_identification", ""),
            inferred_archetype=identity_data.get("inferred_archetype", "Pragmatist"),
            archetype_confidence=identity_data.get("archetype_confidence", 0.5),
            values_expressed=identity_data.get("values_expressed", []),
            lifestyle_indicators=identity_data.get("lifestyle_indicators", []),
            tribe_signals=identity_data.get("tribe_signals", []),
            role_in_purchase=identity_data.get("role_in_purchase", "buyer_for_self"),
        )
        
        # Parse emotional journey
        emotion_data = analysis.get("emotional_journey", {})
        
        def parse_emotion(e) -> Optional[EmotionalState]:
            if not e:
                return None
            try:
                return EmotionalState(e.lower())
            except ValueError:
                # Map common terms
                mappings = {
                    "happy": EmotionalState.JOY,
                    "satisfied": EmotionalState.SATISFACTION,
                    "pleased": EmotionalState.SATISFACTION,
                    "excited": EmotionalState.EXCITEMENT,
                    "disappointed": EmotionalState.DISAPPOINTMENT,
                }
                return mappings.get(e.lower(), EmotionalState.SATISFACTION)
        
        emotional_journey = EmotionalJourney(
            pre_purchase_emotion=parse_emotion(emotion_data.get("pre_purchase_emotion")),
            unboxing_emotion=parse_emotion(emotion_data.get("unboxing_emotion")),
            first_use_emotion=parse_emotion(emotion_data.get("first_use_emotion")),
            long_term_emotion=parse_emotion(emotion_data.get("long_term_emotion")),
            overall_emotional_tone=emotion_data.get("overall_emotional_tone", "neutral"),
            emotional_intensity=emotion_data.get("emotional_intensity", 0.5),
            emotion_evidence=emotion_data.get("emotion_evidence", []),
        )
        
        # Parse expectations
        expect_data = analysis.get("expectations_analysis", {})
        expectations = ExpectationAnalysis(
            expectations_met=expect_data.get("expectations_met", True),
            exceeded_expectations=expect_data.get("exceeded_expectations", False),
            specific_expectations=expect_data.get("specific_expectations", []),
            reality_description=expect_data.get("reality_description", ""),
            gap_description=expect_data.get("gap_description", ""),
            cognitive_dissonance_indicators=expect_data.get("cognitive_dissonance_indicators", []),
        )
        
        # Parse purchase archaeology
        purchase_data = analysis.get("purchase_archaeology", {})
        primary_motivation_str = purchase_data.get("primary_motivation", "functional_need")
        try:
            primary_motivation = PurchaseMotivation(primary_motivation_str)
        except ValueError:
            primary_motivation = PurchaseMotivation.FUNCTIONAL_NEED
        
        secondary_motivations = []
        for m in purchase_data.get("secondary_motivations", []):
            try:
                secondary_motivations.append(PurchaseMotivation(m))
            except ValueError:
                continue
        
        decision_style_str = purchase_data.get("decision_style", "mixed")
        try:
            decision_style = DecisionStyle(decision_style_str)
        except ValueError:
            decision_style = DecisionStyle.MIXED
        
        purchase_archaeology = PurchaseArchaeology(
            primary_motivation=primary_motivation,
            secondary_motivations=secondary_motivations,
            trigger_event=purchase_data.get("trigger_event", ""),
            decision_factors=purchase_data.get("decision_factors", []),
            alternatives_considered=purchase_data.get("alternatives_considered", []),
            influencers=purchase_data.get("influencers", []),
            decision_style=decision_style,
            research_depth=purchase_data.get("research_depth", "moderate"),
        )
        
        # Parse product attributes
        attributes = []
        positive_attrs = []
        negative_attrs = []
        for attr in analysis.get("product_attributes_mentioned", []):
            attributes.append(ProductAttributeMention(
                attribute=attr.get("attribute", ""),
                sentiment=attr.get("sentiment", "neutral"),
                importance=attr.get("importance", 0.5),
                exact_quote=attr.get("exact_quote", ""),
            ))
            if attr.get("sentiment") == "positive":
                positive_attrs.append(attr.get("attribute", ""))
            elif attr.get("sentiment") == "negative":
                negative_attrs.append(attr.get("attribute", ""))
        
        # Parse constructs
        constructs_data = analysis.get("psychological_constructs", {})
        construct_scores = {}
        construct_evidence = {}
        for construct, data in constructs_data.items():
            if isinstance(data, dict):
                construct_scores[construct] = data.get("score", 0.5)
                construct_evidence[construct] = data.get("evidence", [])
        
        # Parse regulatory focus
        reg_data = analysis.get("regulatory_focus", {})
        
        # Parse nonconscious
        noncon_data = analysis.get("nonconscious_indicators", {})
        
        return DeepReviewAnalysis(
            review_id=review_id,
            rating=rating,
            review_text=review_text,
            identity=identity,
            emotional_journey=emotional_journey,
            emotions_expressed=[],  # Would need more parsing
            expectations=expectations,
            purchase_archaeology=purchase_archaeology,
            attributes_mentioned=attributes,
            positive_attributes=positive_attrs,
            negative_attributes=negative_attrs,
            construct_scores=construct_scores,
            construct_evidence=construct_evidence,
            regulatory_focus=reg_data.get("focus", "promotion"),
            regulatory_evidence=reg_data.get("evidence", []),
            personality_indicators={
                k: v for k, v in construct_scores.items()
                if k in ["conscientiousness", "openness", "extraversion", "agreeableness", "neuroticism"]
            },
            decision_style=decision_style,
            heuristics_evident=noncon_data.get("heuristics_evident", []),
            biases_evident=noncon_data.get("biases_evident", []),
            most_revealing_quotes=analysis.get("most_revealing_quotes", []),
            research_principles_evident=analysis.get("research_principles_evident", []),
            analysis_confidence=analysis.get("analysis_confidence", 0.7),
        )
    
    def _create_fallback_analysis(
        self,
        review_id: str,
        review_text: str,
        rating: float,
    ) -> DeepReviewAnalysis:
        """Create minimal analysis when Claude fails."""
        return DeepReviewAnalysis(
            review_id=review_id,
            rating=rating,
            review_text=review_text,
            identity=IdentityRevelation(
                self_identification="",
                inferred_archetype="Pragmatist",
                archetype_confidence=0.3,
                values_expressed=[],
                lifestyle_indicators=[],
                tribe_signals=[],
                role_in_purchase="buyer_for_self",
            ),
            emotional_journey=EmotionalJourney(
                pre_purchase_emotion=None,
                unboxing_emotion=None,
                first_use_emotion=None,
                long_term_emotion=None,
                overall_emotional_tone="neutral" if rating >= 3 else "negative",
                emotional_intensity=0.5,
                emotion_evidence=[],
            ),
            emotions_expressed=[],
            expectations=ExpectationAnalysis(
                expectations_met=rating >= 4,
                exceeded_expectations=rating == 5,
                specific_expectations=[],
                reality_description="",
                gap_description="",
                cognitive_dissonance_indicators=[],
            ),
            purchase_archaeology=PurchaseArchaeology(
                primary_motivation=PurchaseMotivation.FUNCTIONAL_NEED,
                secondary_motivations=[],
                trigger_event="",
                decision_factors=[],
                alternatives_considered=[],
                influencers=[],
                decision_style=DecisionStyle.MIXED,
                research_depth="moderate",
            ),
            attributes_mentioned=[],
            positive_attributes=[],
            negative_attributes=[],
            analysis_confidence=0.2,
        )


# =============================================================================
# SINGLETON
# =============================================================================

_deep_review_analyzer: Optional[DeepReviewAnalyzer] = None


def get_deep_review_analyzer() -> DeepReviewAnalyzer:
    """Get or create the deep review analyzer."""
    global _deep_review_analyzer
    if _deep_review_analyzer is None:
        _deep_review_analyzer = DeepReviewAnalyzer()
    return _deep_review_analyzer
