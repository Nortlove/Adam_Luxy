# =============================================================================
# Purchase Journey Analyzer
# Location: adam/intelligence/purchase_journey_analyzer.py
# =============================================================================

"""
Purchase Journey Analyzer

This is the SYNTHESIS component that combines:
1. Deep Product Analysis (the "advertisement")
2. Deep Review Analysis (the consumer psychology)

Into EVIDENCE of what works in advertising.

Each purchase journey represents empirical proof:
- Which mechanisms were effective
- Which archetypes actually buy
- What product-customer matches work
- Which research principles are validated

This evidence feeds into:
- Thompson Sampling priors
- AtomDAG evidence paths
- Neo4j relationship weights
- Pattern learning
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum

from adam.intelligence.deep_product_analyzer import (
    DeepProductAnalysis,
    PersuasionMechanism,
    get_deep_product_analyzer,
)
from adam.intelligence.deep_review_analyzer import (
    DeepReviewAnalysis,
    PurchaseMotivation,
    get_deep_review_analyzer,
)

logger = logging.getLogger(__name__)


# =============================================================================
# DATA MODELS
# =============================================================================

@dataclass
class MechanismEffectiveness:
    """Evidence of how effective a persuasion mechanism was."""
    mechanism: str
    product_usage_strength: str  # How strongly the product used this mechanism
    reviewer_response: str  # "responded", "neutral", "resistant"
    effectiveness_score: float  # 0-1
    evidence: List[str]
    confidence: float


@dataclass
class ArchetypeMatch:
    """Evidence of product-archetype matching."""
    product_target_archetype: str
    reviewer_actual_archetype: str
    match_type: str  # "exact", "secondary", "unexpected"
    match_score: float
    insights: List[str]


@dataclass
class ResearchValidation:
    """Evidence validating psychological research."""
    principle: str
    researcher: str
    validated: bool
    evidence: str
    strength: str  # "weak", "moderate", "strong"


@dataclass
class PurchaseJourneyEvidence:
    """
    Complete evidence record from a single purchase journey.
    
    This represents what we LEARN from one customer's complete
    journey from seeing the product listing to leaving a review.
    """
    # Identifiers
    journey_id: str
    product_id: str
    review_id: str
    
    # Basic Info
    product_title: str
    brand: str
    rating: float
    
    # Mechanism Effectiveness Evidence
    mechanism_effectiveness: List[MechanismEffectiveness] = field(default_factory=list)
    most_effective_mechanism: Optional[str] = None
    least_effective_mechanism: Optional[str] = None
    
    # Archetype Matching Evidence
    archetype_match: Optional[ArchetypeMatch] = None
    target_archetype_validation: bool = False
    unexpected_archetype_discovery: Optional[str] = None
    
    # Value Proposition Validation
    functional_value_delivered: bool = False
    emotional_value_delivered: bool = False
    social_value_delivered: bool = False
    value_proposition_gaps: List[str] = field(default_factory=list)
    
    # Emotional Journey Mapping
    intended_emotional_response: str = ""
    actual_emotional_response: str = ""
    emotional_match: bool = False
    emotional_intensity_achieved: float = 0.0
    
    # Purchase Decision Insights
    decision_style_used: str = ""
    key_decision_factors: List[str] = field(default_factory=list)
    heuristics_activated: List[str] = field(default_factory=list)
    biases_leveraged: List[str] = field(default_factory=list)
    
    # Research Validations
    research_validations: List[ResearchValidation] = field(default_factory=list)
    
    # Aggregate Scores
    overall_journey_success: float = 0.0  # How well did the "ad" work?
    confidence: float = 0.0
    
    # Learning Signals
    should_increase_mechanism_priors: Dict[str, float] = field(default_factory=dict)
    should_decrease_mechanism_priors: Dict[str, float] = field(default_factory=dict)
    archetype_mechanism_evidence: Dict[str, Dict[str, float]] = field(default_factory=dict)
    
    # Timestamps
    analyzed_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "journey_id": self.journey_id,
            "product_id": self.product_id,
            "review_id": self.review_id,
            "product_title": self.product_title,
            "brand": self.brand,
            "rating": self.rating,
            "mechanism_effectiveness": [
                {
                    "mechanism": m.mechanism,
                    "effectiveness_score": m.effectiveness_score,
                    "reviewer_response": m.reviewer_response,
                    "evidence": m.evidence,
                }
                for m in self.mechanism_effectiveness
            ],
            "most_effective_mechanism": self.most_effective_mechanism,
            "archetype_match": {
                "product_target": self.archetype_match.product_target_archetype,
                "reviewer_actual": self.archetype_match.reviewer_actual_archetype,
                "match_type": self.archetype_match.match_type,
                "match_score": self.archetype_match.match_score,
            } if self.archetype_match else None,
            "value_delivered": {
                "functional": self.functional_value_delivered,
                "emotional": self.emotional_value_delivered,
                "social": self.social_value_delivered,
            },
            "emotional_match": self.emotional_match,
            "decision_style": self.decision_style_used,
            "key_decision_factors": self.key_decision_factors,
            "research_validations": [
                {
                    "principle": r.principle,
                    "validated": r.validated,
                    "strength": r.strength,
                }
                for r in self.research_validations
            ],
            "overall_success": self.overall_journey_success,
            "learning_signals": {
                "increase_priors": self.should_increase_mechanism_priors,
                "decrease_priors": self.should_decrease_mechanism_priors,
                "archetype_mechanism_evidence": self.archetype_mechanism_evidence,
            },
            "confidence": self.confidence,
            "analyzed_at": self.analyzed_at.isoformat(),
        }


# =============================================================================
# PURCHASE JOURNEY ANALYZER
# =============================================================================

class PurchaseJourneyAnalyzer:
    """
    Synthesizes product and review analyses into actionable evidence.
    
    This is where we determine:
    - What mechanisms actually worked
    - Whether the right archetype bought
    - Which research principles are validated
    - What should update our priors
    """
    
    def __init__(self):
        self.product_analyzer = get_deep_product_analyzer()
        self.review_analyzer = get_deep_review_analyzer()
    
    async def analyze_journey(
        self,
        product_analysis: DeepProductAnalysis,
        review_analysis: DeepReviewAnalysis,
    ) -> PurchaseJourneyEvidence:
        """
        Analyze a complete purchase journey.
        
        Args:
            product_analysis: Deep analysis of the product listing
            review_analysis: Deep analysis of the customer review
            
        Returns:
            PurchaseJourneyEvidence with learning signals
        """
        journey_id = f"{product_analysis.product_id}_{review_analysis.review_id}"
        
        logger.info(f"Analyzing purchase journey: {journey_id}")
        
        # Analyze mechanism effectiveness
        mechanism_effectiveness = self._analyze_mechanism_effectiveness(
            product_analysis, review_analysis
        )
        
        # Determine most/least effective
        most_effective = None
        least_effective = None
        if mechanism_effectiveness:
            sorted_mechs = sorted(
                mechanism_effectiveness, 
                key=lambda x: x.effectiveness_score,
                reverse=True
            )
            most_effective = sorted_mechs[0].mechanism
            if len(sorted_mechs) > 1:
                least_effective = sorted_mechs[-1].mechanism
        
        # Analyze archetype matching
        archetype_match = self._analyze_archetype_match(
            product_analysis, review_analysis
        )
        
        # Analyze value proposition delivery
        functional, emotional, social, gaps = self._analyze_value_delivery(
            product_analysis, review_analysis
        )
        
        # Analyze emotional journey
        intended_emotion, actual_emotion, emotion_match, intensity = self._analyze_emotional_journey(
            product_analysis, review_analysis
        )
        
        # Validate research principles
        research_validations = self._validate_research_principles(
            product_analysis, review_analysis
        )
        
        # Calculate overall success
        success_score = self._calculate_journey_success(
            review_analysis.rating,
            archetype_match,
            mechanism_effectiveness,
            emotion_match,
        )
        
        # Generate learning signals
        increase_priors, decrease_priors = self._generate_learning_signals(
            mechanism_effectiveness,
            review_analysis.rating,
        )
        
        # Generate archetype-mechanism evidence
        archetype_mechanism_evidence = self._generate_archetype_mechanism_evidence(
            review_analysis.identity.inferred_archetype,
            mechanism_effectiveness,
        )
        
        return PurchaseJourneyEvidence(
            journey_id=journey_id,
            product_id=product_analysis.product_id,
            review_id=review_analysis.review_id,
            product_title=product_analysis.title,
            brand=product_analysis.brand,
            rating=review_analysis.rating,
            mechanism_effectiveness=mechanism_effectiveness,
            most_effective_mechanism=most_effective,
            least_effective_mechanism=least_effective,
            archetype_match=archetype_match,
            target_archetype_validation=archetype_match.match_type == "exact" if archetype_match else False,
            unexpected_archetype_discovery=archetype_match.reviewer_actual_archetype 
                if archetype_match and archetype_match.match_type == "unexpected" else None,
            functional_value_delivered=functional,
            emotional_value_delivered=emotional,
            social_value_delivered=social,
            value_proposition_gaps=gaps,
            intended_emotional_response=intended_emotion,
            actual_emotional_response=actual_emotion,
            emotional_match=emotion_match,
            emotional_intensity_achieved=intensity,
            decision_style_used=review_analysis.purchase_archaeology.decision_style.value,
            key_decision_factors=review_analysis.purchase_archaeology.decision_factors,
            heuristics_activated=review_analysis.heuristics_evident,
            biases_leveraged=review_analysis.biases_evident,
            research_validations=research_validations,
            overall_journey_success=success_score,
            confidence=(product_analysis.analysis_confidence + review_analysis.analysis_confidence) / 2,
            should_increase_mechanism_priors=increase_priors,
            should_decrease_mechanism_priors=decrease_priors,
            archetype_mechanism_evidence=archetype_mechanism_evidence,
        )
    
    def _analyze_mechanism_effectiveness(
        self,
        product: DeepProductAnalysis,
        review: DeepReviewAnalysis,
    ) -> List[MechanismEffectiveness]:
        """
        Determine which mechanisms were effective based on review response.
        """
        results = []
        
        for mech in product.mechanisms_detected:
            # Check if reviewer showed response to this mechanism
            response = self._infer_mechanism_response(mech, review)
            
            # Calculate effectiveness
            effectiveness = self._calculate_mechanism_effectiveness(
                mech, review, response
            )
            
            results.append(MechanismEffectiveness(
                mechanism=mech.mechanism.value,
                product_usage_strength=mech.strength,
                reviewer_response=response,
                effectiveness_score=effectiveness,
                evidence=self._gather_mechanism_evidence(mech, review),
                confidence=mech.confidence,
            ))
        
        return results
    
    def _infer_mechanism_response(
        self,
        mechanism,
        review: DeepReviewAnalysis,
    ) -> str:
        """Infer how the reviewer responded to a mechanism."""
        mech_type = mechanism.mechanism
        
        # Check review for evidence of response
        if mech_type == PersuasionMechanism.SOCIAL_PROOF:
            # Did they mention reviews, popularity, others buying?
            indicators = ["reviews", "popular", "others", "everyone", "recommended"]
            if any(ind in review.review_text.lower() for ind in indicators):
                return "responded"
            if "social_proof" in [h.lower() for h in review.heuristics_evident]:
                return "responded"
        
        elif mech_type == PersuasionMechanism.AUTHORITY:
            # Did they mention quality, professional, expert, trusted brand?
            indicators = ["professional", "quality", "expert", "trusted", "reliable", "brand"]
            if any(ind in review.review_text.lower() for ind in indicators):
                return "responded"
            if review.identity.inferred_archetype in ["Achiever", "Analyzer"]:
                return "responded"  # These archetypes typically respond to authority
        
        elif mech_type == PersuasionMechanism.SCARCITY:
            # Did they mention urgency, limited, exclusive?
            indicators = ["finally got", "glad I got", "lucky to find", "limited"]
            if any(ind in review.review_text.lower() for ind in indicators):
                return "responded"
        
        elif mech_type == PersuasionMechanism.RECIPROCITY:
            # Did they mention bonuses, extras, included items?
            indicators = ["bonus", "extra", "included", "comes with", "free"]
            if any(ind in review.review_text.lower() for ind in indicators):
                return "responded"
        
        # Default: neutral if rating is 3+, resistant if below
        return "neutral" if review.rating >= 3 else "resistant"
    
    def _calculate_mechanism_effectiveness(
        self,
        mechanism,
        review: DeepReviewAnalysis,
        response: str,
    ) -> float:
        """Calculate effectiveness score for a mechanism."""
        base_score = 0.5
        
        # Response modifier
        if response == "responded":
            base_score += 0.3
        elif response == "resistant":
            base_score -= 0.3
        
        # Rating modifier (high rating = mechanisms worked)
        rating_modifier = (review.rating - 3) / 4  # -0.5 to 0.5
        base_score += rating_modifier * 0.2
        
        # Mechanism strength modifier
        strength_modifiers = {"subtle": -0.1, "moderate": 0, "strong": 0.1}
        base_score += strength_modifiers.get(mechanism.strength, 0)
        
        return max(0.0, min(1.0, base_score))
    
    def _gather_mechanism_evidence(
        self,
        mechanism,
        review: DeepReviewAnalysis,
    ) -> List[str]:
        """Gather evidence from review supporting mechanism effectiveness."""
        evidence = []
        
        # Add revealing quotes that might relate to this mechanism
        for quote in review.most_revealing_quotes:
            evidence.append(quote)
        
        # Add decision factors
        for factor in review.purchase_archaeology.decision_factors[:2]:
            evidence.append(f"Decision factor: {factor}")
        
        return evidence[:3]  # Limit to 3 pieces of evidence
    
    def _analyze_archetype_match(
        self,
        product: DeepProductAnalysis,
        review: DeepReviewAnalysis,
    ) -> Optional[ArchetypeMatch]:
        """Analyze if the product reached its target archetype."""
        product_target = product.target_archetype
        reviewer_archetype = review.identity.inferred_archetype
        
        if not product_target or not reviewer_archetype:
            return None
        
        # Determine match type
        if product_target.lower() == reviewer_archetype.lower():
            match_type = "exact"
            match_score = 0.9
        elif reviewer_archetype in [
            a for a, conf in product.secondary_archetypes.items() if conf > 0.3
        ]:
            match_type = "secondary"
            match_score = 0.6
        else:
            match_type = "unexpected"
            match_score = 0.3
        
        # Adjust by confidence
        match_score *= review.identity.archetype_confidence
        
        insights = []
        if match_type == "exact":
            insights.append(f"Product successfully reached target {product_target} archetype")
        elif match_type == "unexpected":
            insights.append(
                f"Product attracted {reviewer_archetype} instead of target {product_target} - "
                f"consider expanding targeting"
            )
        
        return ArchetypeMatch(
            product_target_archetype=product_target,
            reviewer_actual_archetype=reviewer_archetype,
            match_type=match_type,
            match_score=match_score,
            insights=insights,
        )
    
    def _analyze_value_delivery(
        self,
        product: DeepProductAnalysis,
        review: DeepReviewAnalysis,
    ) -> Tuple[bool, bool, bool, List[str]]:
        """Analyze if value propositions were delivered."""
        gaps = []
        
        # Check functional value
        functional_promised = bool(product.core_functional_benefit)
        functional_mentions = any(
            attr.sentiment == "positive" 
            for attr in review.attributes_mentioned
            if attr.attribute.lower() in ["quality", "performance", "function", "works"]
        )
        functional_delivered = functional_mentions or review.rating >= 4
        if functional_promised and not functional_delivered:
            gaps.append(f"Promised functional benefit '{product.core_functional_benefit}' not confirmed in review")
        
        # Check emotional value
        emotional_promised = bool(product.core_emotional_benefit)
        emotional_delivered = review.emotional_journey.emotional_intensity > 0.6 and \
                             review.emotional_journey.overall_emotional_tone not in ["negative", "disappointed"]
        if emotional_promised and not emotional_delivered:
            gaps.append(f"Promised emotional benefit '{product.core_emotional_benefit}' not achieved")
        
        # Check social value
        social_promised = bool(product.core_social_benefit)
        social_delivered = any(
            "recommend" in quote.lower() or "gift" in quote.lower()
            for quote in review.most_revealing_quotes
        )
        if social_promised and not social_delivered:
            gaps.append(f"Promised social benefit '{product.core_social_benefit}' not evident")
        
        return functional_delivered, emotional_delivered, social_delivered, gaps
    
    def _analyze_emotional_journey(
        self,
        product: DeepProductAnalysis,
        review: DeepReviewAnalysis,
    ) -> Tuple[str, str, bool, float]:
        """Analyze if intended emotional response was achieved."""
        # Get intended emotion from product
        intended = ""
        if product.emotional_appeals:
            strongest = max(product.emotional_appeals, key=lambda x: x.intensity)
            intended = strongest.trigger.value
        
        # Get actual emotion from review
        actual = review.emotional_journey.overall_emotional_tone
        intensity = review.emotional_journey.emotional_intensity
        
        # Check match
        emotion_mappings = {
            "aspiration": ["proud", "satisfied", "excited", "happy"],
            "security": ["confident", "safe", "trust", "relieved"],
            "excitement": ["excited", "thrilled", "happy", "joy"],
            "belonging": ["connected", "part of", "community"],
        }
        
        match = False
        if intended in emotion_mappings:
            match = actual.lower() in emotion_mappings[intended]
        elif review.rating >= 4:
            match = True  # High rating implies emotional needs met
        
        return intended, actual, match, intensity
    
    def _validate_research_principles(
        self,
        product: DeepProductAnalysis,
        review: DeepReviewAnalysis,
    ) -> List[ResearchValidation]:
        """Validate which research principles are confirmed by this journey."""
        validations = []
        
        # Combine research mappings from both analyses
        all_principles = (
            product.research_principles_applied + 
            review.research_principles_evident
        )
        
        for principle_data in all_principles:
            if isinstance(principle_data, dict):
                validations.append(ResearchValidation(
                    principle=principle_data.get("principle", ""),
                    researcher=principle_data.get("researcher", ""),
                    validated=review.rating >= 4,  # High rating = principle worked
                    evidence=principle_data.get("evidence", ""),
                    strength="strong" if review.rating >= 4 else "weak",
                ))
        
        return validations[:5]  # Limit to top 5
    
    def _calculate_journey_success(
        self,
        rating: float,
        archetype_match: Optional[ArchetypeMatch],
        mechanism_effectiveness: List[MechanismEffectiveness],
        emotion_match: bool,
    ) -> float:
        """Calculate overall journey success score."""
        # Rating contributes 40%
        rating_score = (rating - 1) / 4  # 0 to 1
        
        # Archetype match contributes 20%
        archetype_score = archetype_match.match_score if archetype_match else 0.5
        
        # Mechanism effectiveness contributes 25%
        mech_score = 0.5
        if mechanism_effectiveness:
            mech_score = sum(m.effectiveness_score for m in mechanism_effectiveness) / len(mechanism_effectiveness)
        
        # Emotional match contributes 15%
        emotion_score = 0.8 if emotion_match else 0.3
        
        return (
            rating_score * 0.4 +
            archetype_score * 0.2 +
            mech_score * 0.25 +
            emotion_score * 0.15
        )
    
    def _generate_learning_signals(
        self,
        mechanism_effectiveness: List[MechanismEffectiveness],
        rating: float,
    ) -> Tuple[Dict[str, float], Dict[str, float]]:
        """Generate signals for updating Thompson Sampling priors."""
        increase = {}
        decrease = {}
        
        for mech in mechanism_effectiveness:
            # High rating + responded = increase prior
            if rating >= 4 and mech.reviewer_response == "responded":
                increase[mech.mechanism] = mech.effectiveness_score * 0.1
            # Low rating + mechanism used strongly = decrease prior
            elif rating < 3 and mech.product_usage_strength == "strong":
                decrease[mech.mechanism] = (1 - mech.effectiveness_score) * 0.1
        
        return increase, decrease
    
    def _generate_archetype_mechanism_evidence(
        self,
        archetype: str,
        mechanism_effectiveness: List[MechanismEffectiveness],
    ) -> Dict[str, Dict[str, float]]:
        """Generate evidence for archetype-mechanism relationships."""
        if not archetype:
            return {}
        
        evidence = {archetype: {}}
        for mech in mechanism_effectiveness:
            if mech.reviewer_response == "responded":
                evidence[archetype][mech.mechanism] = mech.effectiveness_score
        
        return evidence


# =============================================================================
# SINGLETON
# =============================================================================

_journey_analyzer: Optional[PurchaseJourneyAnalyzer] = None


def get_purchase_journey_analyzer() -> PurchaseJourneyAnalyzer:
    """Get or create the purchase journey analyzer."""
    global _journey_analyzer
    if _journey_analyzer is None:
        _journey_analyzer = PurchaseJourneyAnalyzer()
    return _journey_analyzer
