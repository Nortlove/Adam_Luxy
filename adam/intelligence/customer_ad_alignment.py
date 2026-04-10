#!/usr/bin/env python3
"""
CUSTOMER-ADVERTISEMENT ALIGNMENT SERVICE
=========================================

Calculates psychological alignment scores between customer profiles and
advertisement/brand profiles. This is the core matching engine that enables:
1. Predicting ad effectiveness for specific customer types
2. Recommending optimal customer segments for ads
3. Optimizing ad copy for target audiences
4. Identifying mismatches that could cause backfire

The alignment algorithm considers:
- Motivation alignment (customer motivation ↔ ad value proposition)
- Decision style alignment (customer processing ↔ ad complexity)
- Regulatory focus alignment (customer focus ↔ ad framing)
- Emotional alignment (customer state ↔ ad emotional appeal)
- Mechanism effectiveness (customer susceptibility ↔ ad techniques)
- Cognitive load match (customer tolerance ↔ ad complexity)
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from functools import lru_cache
import math

from .empirical_psychology_framework import (
    EXPANDED_MOTIVATIONS,
    EXPANDED_DECISION_STYLES,
    EXPANDED_REGULATORY_FOCUS,
    EXPANDED_EMOTIONAL_INTENSITY,
    COGNITIVE_LOAD_TOLERANCE,
    TEMPORAL_ORIENTATION,
    SOCIAL_INFLUENCE_SUSCEPTIBILITY,
    calculate_expanded_granular_type,
    ExpandedGranularType,
    LinguisticPatternAnalyzer,
)

from .advertisement_psychology_framework import (
    PERSUASION_TECHNIQUES,
    EMOTIONAL_APPEALS,
    VALUE_PROPOSITIONS,
    BRAND_PERSONALITIES,
    LINGUISTIC_STYLES,
    AdvertisementAnalyzer,
    create_advertisement_profile,
    AdvertisementProfile,
)

from .expanded_type_integration import (
    ExpandedTypeIntegrationService,
    UnifiedGranularType,
)


# =============================================================================
# ALIGNMENT MATRICES (Research-Derived)
# =============================================================================

# Motivation ↔ Value Proposition Alignment Matrix
# High scores = high alignment between customer motivation and ad value proposition
MOTIVATION_VALUE_ALIGNMENT = {
    # Customer Motivation → Best Value Propositions
    "immediate_gratification": {"pleasure_enjoyment": 0.95, "convenience_ease": 0.85, "novelty_innovation": 0.7},
    "mastery_seeking": {"knowledge_expertise": 0.95, "performance_superiority": 0.85, "transformation": 0.7},
    "self_expression": {"self_expression": 0.95, "novelty_innovation": 0.8, "status_prestige": 0.7},
    "flow_experience": {"pleasure_enjoyment": 0.9, "novelty_innovation": 0.8},
    "personal_growth": {"transformation": 0.95, "knowledge_expertise": 0.85, "self_expression": 0.7},
    "values_alignment": {"social_responsibility": 0.95, "reliability_durability": 0.7},
    "goal_achievement": {"transformation": 0.9, "performance_superiority": 0.85},
    "role_fulfillment": {"reliability_durability": 0.8, "peace_of_mind": 0.75},
    "future_self_investment": {"transformation": 0.9, "knowledge_expertise": 0.8, "reliability_durability": 0.7},
    "guilt_avoidance": {"social_responsibility": 0.8, "peace_of_mind": 0.75},
    "ego_protection": {"status_prestige": 0.9, "performance_superiority": 0.8},
    "self_esteem_enhancement": {"self_expression": 0.85, "pleasure_enjoyment": 0.8, "status_prestige": 0.7},
    "anxiety_reduction": {"peace_of_mind": 0.95, "reliability_durability": 0.85},
    "social_compliance": {"belonging_connection": 0.9, "status_prestige": 0.7},
    "reward_seeking": {"cost_efficiency": 0.9, "pleasure_enjoyment": 0.7},
    "punishment_avoidance": {"peace_of_mind": 0.85, "reliability_durability": 0.8},
    "authority_compliance": {"knowledge_expertise": 0.8, "reliability_durability": 0.75},
    "sensory_pleasure": {"pleasure_enjoyment": 0.95, "self_expression": 0.7},
    "excitement_seeking": {"novelty_innovation": 0.95, "pleasure_enjoyment": 0.85},
    "nostalgia_comfort": {"belonging_connection": 0.8, "peace_of_mind": 0.75},
    "escapism": {"pleasure_enjoyment": 0.9, "transformation": 0.7},
    "social_enjoyment": {"belonging_connection": 0.9, "pleasure_enjoyment": 0.8},
    "problem_solving": {"performance_superiority": 0.9, "convenience_ease": 0.85, "cost_efficiency": 0.7},
    "efficiency_optimization": {"convenience_ease": 0.95, "performance_superiority": 0.8, "cost_efficiency": 0.75},
    "cost_minimization": {"cost_efficiency": 0.95, "convenience_ease": 0.7},
    "quality_assurance": {"reliability_durability": 0.95, "performance_superiority": 0.85},
    "risk_mitigation": {"peace_of_mind": 0.95, "reliability_durability": 0.9},
    "status_signaling": {"status_prestige": 0.95, "self_expression": 0.8},
    "belonging_affirmation": {"belonging_connection": 0.95, "social_responsibility": 0.7},
    "uniqueness_differentiation": {"self_expression": 0.95, "novelty_innovation": 0.85, "status_prestige": 0.7},
    "social_approval": {"belonging_connection": 0.85, "status_prestige": 0.8},
    "altruistic_giving": {"social_responsibility": 0.95, "belonging_connection": 0.7},
    "relationship_maintenance": {"belonging_connection": 0.9, "peace_of_mind": 0.7},
}

# Decision Style ↔ Linguistic Style Alignment
DECISION_STYLE_LINGUISTIC_ALIGNMENT = {
    "gut_instinct": {"emotional": 0.9, "urgent": 0.85, "minimalist": 0.8},
    "recognition_based": {"conversational": 0.85, "minimalist": 0.8},
    "affect_driven": {"emotional": 0.95, "storytelling": 0.8},
    "satisficing": {"conversational": 0.85, "minimalist": 0.8},
    "heuristic_based": {"professional": 0.8, "conversational": 0.75},
    "social_referencing": {"conversational": 0.85, "emotional": 0.7},
    "authority_deferring": {"professional": 0.9, "technical": 0.75},
    "maximizing": {"technical": 0.9, "professional": 0.85},
    "analytical_systematic": {"technical": 0.95, "professional": 0.85},
    "risk_calculating": {"technical": 0.85, "professional": 0.8},
    "deliberative_reflective": {"storytelling": 0.8, "professional": 0.75},
    "consensus_building": {"conversational": 0.85, "emotional": 0.7},
}

# Regulatory Focus ↔ Emotional Appeal Alignment
REGULATORY_EMOTIONAL_ALIGNMENT = {
    "eager_advancement": {"excitement": 0.9, "pride": 0.85, "anticipation": 0.8, "joy": 0.75},
    "aspiration_driven": {"empowerment": 0.9, "pride": 0.85, "anticipation": 0.8},
    "optimistic_exploration": {"excitement": 0.9, "surprise": 0.85, "anticipation": 0.8},
    "pragmatic_balanced": {"contentment": 0.8, "trust": 0.8},
    "situational_adaptive": {"trust": 0.8, "contentment": 0.75},
    "vigilant_security": {"trust": 0.9, "fear": 0.75, "anxiety": 0.7},
    "conservative_preservation": {"trust": 0.9, "nostalgia": 0.8, "contentment": 0.75},
    "anxious_avoidance": {"fear": 0.85, "anxiety": 0.8, "trust": 0.7},
}

# Archetype ↔ Brand Personality Alignment
ARCHETYPE_PERSONALITY_ALIGNMENT = {
    "explorer": {"excitement": 0.9, "ruggedness": 0.8, "sophistication": 0.6},
    "achiever": {"competence": 0.9, "sophistication": 0.8, "excitement": 0.7},
    "connector": {"sincerity": 0.9, "excitement": 0.7},
    "guardian": {"sincerity": 0.9, "competence": 0.8},
    "analyst": {"competence": 0.95, "sophistication": 0.7},
    "creator": {"excitement": 0.85, "sophistication": 0.8},
    "nurturer": {"sincerity": 0.95, "competence": 0.7},
    "pragmatist": {"competence": 0.85, "sincerity": 0.75, "ruggedness": 0.7},
}

# Mechanism Susceptibility by Decision Style
MECHANISM_SUSCEPTIBILITY = {
    "gut_instinct": {"scarcity": 0.9, "liking": 0.85, "social_proof": 0.8},
    "recognition_based": {"social_proof": 0.85, "authority": 0.8, "liking": 0.75},
    "affect_driven": {"liking": 0.9, "reciprocity": 0.8, "social_proof": 0.75},
    "satisficing": {"social_proof": 0.85, "authority": 0.75, "reciprocity": 0.7},
    "heuristic_based": {"authority": 0.85, "social_proof": 0.8, "commitment": 0.7},
    "social_referencing": {"social_proof": 0.95, "unity": 0.8, "liking": 0.75},
    "authority_deferring": {"authority": 0.95, "commitment": 0.8, "social_proof": 0.7},
    "maximizing": {"authority": 0.85, "commitment": 0.8, "social_proof": 0.65},
    "analytical_systematic": {"authority": 0.9, "commitment": 0.85, "reciprocity": 0.6},
    "risk_calculating": {"authority": 0.85, "commitment": 0.8, "social_proof": 0.7},
    "deliberative_reflective": {"commitment": 0.85, "authority": 0.8, "reciprocity": 0.75},
    "consensus_building": {"social_proof": 0.9, "unity": 0.85, "authority": 0.7},
}

# Cognitive Load Tolerance ↔ Ad Complexity Alignment
COGNITIVE_COMPLEXITY_ALIGNMENT = {
    "minimal_cognitive": {
        "conversational": 0.9, "minimalist": 0.95, "urgent": 0.85,
        "technical": 0.2, "professional": 0.4
    },
    "moderate_cognitive": {
        "conversational": 0.85, "professional": 0.8, "storytelling": 0.8,
        "technical": 0.5, "minimalist": 0.7
    },
    "high_cognitive": {
        "technical": 0.95, "professional": 0.9, "storytelling": 0.7,
        "minimalist": 0.4, "urgent": 0.3
    },
}

# Social Influence Type ↔ Persuasion Technique Alignment
SOCIAL_PERSUASION_ALIGNMENT = {
    "highly_independent": {
        "authority_expertise": 0.7, "scarcity_exclusivity": 0.6,
        "social_proof_numbers": 0.2, "bandwagon": 0.1
    },
    "informational_seeker": {
        "authority_expertise": 0.95, "authority_credentials": 0.9,
        "social_proof_expert": 0.85, "social_proof_numbers": 0.6
    },
    "socially_aware": {
        "social_proof_numbers": 0.85, "social_proof_similarity": 0.8,
        "social_proof_testimonials": 0.8, "bandwagon": 0.7
    },
    "normatively_driven": {
        "social_proof_numbers": 0.95, "bandwagon": 0.9,
        "social_proof_similarity": 0.85, "unity_shared_identity": 0.8
    },
    "opinion_leader": {
        "scarcity_exclusivity": 0.9, "authority_expertise": 0.8,
        "novelty_innovation": 0.85, "social_proof_numbers": 0.4
    },
}


# =============================================================================
# ALIGNMENT CALCULATOR
# =============================================================================

@dataclass
class AlignmentScore:
    """
    Complete alignment analysis between customer and advertisement.
    """
    
    # Overall scores
    overall_alignment: float  # 0-1, total match quality
    predicted_effectiveness: float  # 0-1, likely conversion impact
    backfire_risk: float  # 0-1, risk of negative reaction
    
    # Component scores
    motivation_alignment: float
    decision_style_alignment: float
    regulatory_focus_alignment: float
    emotional_alignment: float
    mechanism_alignment: float
    cognitive_alignment: float
    personality_alignment: float
    
    # Detailed breakdowns
    motivation_details: Dict[str, float]
    mechanism_details: Dict[str, float]
    emotional_details: Dict[str, float]
    
    # Recommendations
    alignment_strengths: List[str]
    alignment_weaknesses: List[str]
    optimization_suggestions: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "scores": {
                "overall_alignment": self.overall_alignment,
                "predicted_effectiveness": self.predicted_effectiveness,
                "backfire_risk": self.backfire_risk,
            },
            "components": {
                "motivation": self.motivation_alignment,
                "decision_style": self.decision_style_alignment,
                "regulatory_focus": self.regulatory_focus_alignment,
                "emotional": self.emotional_alignment,
                "mechanism": self.mechanism_alignment,
                "cognitive": self.cognitive_alignment,
                "personality": self.personality_alignment,
            },
            "details": {
                "motivation": self.motivation_details,
                "mechanism": self.mechanism_details,
                "emotional": self.emotional_details,
            },
            "recommendations": {
                "strengths": self.alignment_strengths,
                "weaknesses": self.alignment_weaknesses,
                "suggestions": self.optimization_suggestions,
            },
        }


class CustomerAdAlignmentService:
    """
    Service for calculating customer-advertisement alignment.
    """
    
    def __init__(self):
        self.customer_analyzer = LinguisticPatternAnalyzer()
        self.ad_analyzer = AdvertisementAnalyzer()
        self.type_service = ExpandedTypeIntegrationService()
    
    def calculate_alignment(
        self,
        customer_type: UnifiedGranularType,
        ad_profile: AdvertisementProfile,
    ) -> AlignmentScore:
        """
        Calculate comprehensive alignment between customer and advertisement.
        """
        
        # Calculate component alignments
        motivation_alignment, motivation_details = self._calculate_motivation_alignment(
            customer_type.expanded_motivation,
            ad_profile.value_propositions_used
        )
        
        decision_alignment = self._calculate_decision_style_alignment(
            customer_type.expanded_decision_style,
            ad_profile.linguistic_style
        )
        
        regulatory_alignment = self._calculate_regulatory_alignment(
            customer_type.expanded_regulatory_focus,
            ad_profile.primary_emotional_appeal,
            ad_profile.target_regulatory_focus
        )
        
        emotional_alignment, emotional_details = self._calculate_emotional_alignment(
            customer_type,
            ad_profile.emotional_appeals_used
        )
        
        mechanism_alignment, mechanism_details = self._calculate_mechanism_alignment(
            customer_type.expanded_decision_style,
            customer_type.social_influence_type,
            ad_profile.mechanism_emphasis
        )
        
        cognitive_alignment = self._calculate_cognitive_alignment(
            customer_type.cognitive_load_tolerance,
            ad_profile.linguistic_style,
            ad_profile.complexity_level
        )
        
        personality_alignment = self._calculate_personality_alignment(
            customer_type.archetype,
            ad_profile.brand_personality
        )
        
        # Calculate overall alignment (weighted combination)
        weights = {
            "motivation": 0.20,
            "decision": 0.15,
            "regulatory": 0.10,
            "emotional": 0.15,
            "mechanism": 0.20,
            "cognitive": 0.10,
            "personality": 0.10,
        }
        
        overall_alignment = (
            motivation_alignment * weights["motivation"] +
            decision_alignment * weights["decision"] +
            regulatory_alignment * weights["regulatory"] +
            emotional_alignment * weights["emotional"] +
            mechanism_alignment * weights["mechanism"] +
            cognitive_alignment * weights["cognitive"] +
            personality_alignment * weights["personality"]
        )
        
        # Calculate predicted effectiveness
        # Higher alignment + higher persuadability = higher effectiveness
        predicted_effectiveness = (
            overall_alignment * 0.6 +
            customer_type.persuadability_score * 0.3 +
            (1 - ad_profile.ethical_score) * 0.1  # Aggressive tactics can work short-term
        )
        predicted_effectiveness = min(1.0, predicted_effectiveness)
        
        # Calculate backfire risk
        backfire_risk = self._calculate_backfire_risk(
            customer_type,
            ad_profile,
            overall_alignment
        )
        
        # Generate recommendations
        strengths = self._identify_strengths(
            motivation_alignment, decision_alignment, mechanism_alignment,
            customer_type, ad_profile
        )
        
        weaknesses = self._identify_weaknesses(
            motivation_alignment, decision_alignment, mechanism_alignment,
            cognitive_alignment, customer_type, ad_profile
        )
        
        suggestions = self._generate_suggestions(
            customer_type, ad_profile, weaknesses
        )
        
        return AlignmentScore(
            overall_alignment=round(overall_alignment, 3),
            predicted_effectiveness=round(predicted_effectiveness, 3),
            backfire_risk=round(backfire_risk, 3),
            motivation_alignment=round(motivation_alignment, 3),
            decision_style_alignment=round(decision_alignment, 3),
            regulatory_focus_alignment=round(regulatory_alignment, 3),
            emotional_alignment=round(emotional_alignment, 3),
            mechanism_alignment=round(mechanism_alignment, 3),
            cognitive_alignment=round(cognitive_alignment, 3),
            personality_alignment=round(personality_alignment, 3),
            motivation_details=motivation_details,
            mechanism_details=mechanism_details,
            emotional_details=emotional_details,
            alignment_strengths=strengths,
            alignment_weaknesses=weaknesses,
            optimization_suggestions=suggestions,
        )
    
    def _calculate_motivation_alignment(
        self,
        customer_motivation: str,
        ad_value_propositions: Dict[str, float]
    ) -> Tuple[float, Dict[str, float]]:
        """Calculate alignment between customer motivation and ad value propositions."""
        
        alignment_matrix = MOTIVATION_VALUE_ALIGNMENT.get(customer_motivation, {})
        
        if not alignment_matrix or not ad_value_propositions:
            return 0.5, {}
        
        details = {}
        weighted_sum = 0.0
        total_weight = 0.0
        
        for value_prop, ad_score in ad_value_propositions.items():
            if ad_score > 0.1:  # Only consider present value propositions
                alignment = alignment_matrix.get(value_prop, 0.3)  # Default moderate alignment
                details[value_prop] = round(alignment * ad_score, 3)
                weighted_sum += alignment * ad_score
                total_weight += ad_score
        
        if total_weight > 0:
            overall = weighted_sum / total_weight
        else:
            overall = 0.5
        
        return min(1.0, overall), details
    
    def _calculate_decision_style_alignment(
        self,
        customer_decision_style: str,
        ad_linguistic_style: str
    ) -> float:
        """Calculate alignment between decision style and ad linguistic style."""
        
        alignment_matrix = DECISION_STYLE_LINGUISTIC_ALIGNMENT.get(customer_decision_style, {})
        return alignment_matrix.get(ad_linguistic_style, 0.5)
    
    def _calculate_regulatory_alignment(
        self,
        customer_regulatory: str,
        ad_emotion: str,
        ad_regulatory_target: str
    ) -> float:
        """Calculate regulatory focus alignment."""
        
        # Check if ad targets the right regulatory focus
        focus_match = 1.0 if customer_regulatory.split("_")[0] in ad_regulatory_target else 0.5
        
        # Check emotional alignment
        emotional_matrix = REGULATORY_EMOTIONAL_ALIGNMENT.get(customer_regulatory, {})
        emotional_match = emotional_matrix.get(ad_emotion, 0.4)
        
        return (focus_match * 0.6 + emotional_match * 0.4)
    
    def _calculate_emotional_alignment(
        self,
        customer_type: UnifiedGranularType,
        ad_emotions: Dict[str, float]
    ) -> Tuple[float, Dict[str, float]]:
        """Calculate emotional alignment."""
        
        details = {}
        
        # Get customer emotional state
        customer_emotional = customer_type.expanded_emotional_intensity
        
        # Get emotional preferences from regulatory focus
        regulatory_emotions = REGULATORY_EMOTIONAL_ALIGNMENT.get(
            customer_type.expanded_regulatory_focus, {}
        )
        
        weighted_sum = 0.0
        total_weight = 0.0
        
        for emotion, ad_score in ad_emotions.items():
            if ad_score > 0.1:
                # Check if emotion matches customer's preferred emotions
                preference = regulatory_emotions.get(emotion, 0.4)
                
                # Adjust based on emotional intensity match
                if "high" in customer_emotional and emotion in ["excitement", "fear", "surprise"]:
                    preference *= 1.2
                elif "low" in customer_emotional and emotion in ["contentment", "trust", "nostalgia"]:
                    preference *= 1.2
                
                preference = min(1.0, preference)
                details[emotion] = round(preference * ad_score, 3)
                weighted_sum += preference * ad_score
                total_weight += ad_score
        
        if total_weight > 0:
            overall = weighted_sum / total_weight
        else:
            overall = 0.5
        
        return min(1.0, overall), details
    
    def _calculate_mechanism_alignment(
        self,
        customer_decision_style: str,
        customer_social_influence: str,
        ad_mechanisms: Dict[str, float]
    ) -> Tuple[float, Dict[str, float]]:
        """Calculate persuasion mechanism alignment."""
        
        details = {}
        
        # Get customer's mechanism susceptibility
        decision_susceptibility = MECHANISM_SUSCEPTIBILITY.get(customer_decision_style, {})
        
        # Get social influence effects
        social_effects = SOCIAL_PERSUASION_ALIGNMENT.get(customer_social_influence, {})
        
        weighted_sum = 0.0
        total_weight = 0.0
        
        for mechanism, ad_score in ad_mechanisms.items():
            if ad_score > 0.1:
                # Combine decision style and social influence susceptibility
                decision_sus = decision_susceptibility.get(mechanism, 0.5)
                social_sus = social_effects.get(mechanism, 0.5) if social_effects else 0.5
                
                # Weight towards decision style susceptibility
                combined_sus = decision_sus * 0.7 + social_sus * 0.3
                
                details[mechanism] = round(combined_sus, 3)
                weighted_sum += combined_sus * ad_score
                total_weight += ad_score
        
        if total_weight > 0:
            overall = weighted_sum / total_weight
        else:
            overall = 0.5
        
        return min(1.0, overall), details
    
    def _calculate_cognitive_alignment(
        self,
        customer_cognitive: str,
        ad_style: str,
        ad_complexity: float
    ) -> float:
        """Calculate cognitive load alignment."""
        
        alignment_matrix = COGNITIVE_COMPLEXITY_ALIGNMENT.get(customer_cognitive, {})
        style_alignment = alignment_matrix.get(ad_style, 0.5)
        
        # Adjust for complexity match
        cognitive_preferences = {
            "minimal_cognitive": 0.2,
            "moderate_cognitive": 0.5,
            "high_cognitive": 0.8,
        }
        
        preferred_complexity = cognitive_preferences.get(customer_cognitive, 0.5)
        complexity_diff = abs(preferred_complexity - ad_complexity)
        complexity_penalty = complexity_diff * 0.5
        
        return max(0.0, style_alignment - complexity_penalty)
    
    def _calculate_personality_alignment(
        self,
        customer_archetype: str,
        ad_personality: str
    ) -> float:
        """Calculate brand personality alignment."""
        
        alignment_matrix = ARCHETYPE_PERSONALITY_ALIGNMENT.get(customer_archetype, {})
        return alignment_matrix.get(ad_personality, 0.5)
    
    def _calculate_backfire_risk(
        self,
        customer_type: UnifiedGranularType,
        ad_profile: AdvertisementProfile,
        overall_alignment: float
    ) -> float:
        """Calculate risk of negative reaction to the ad."""
        
        risk = 0.0
        
        # Low alignment increases backfire risk
        if overall_alignment < 0.4:
            risk += 0.3
        
        # High persuadability with aggressive tactics is risky
        if customer_type.persuadability_score < 0.3 and ad_profile.persuasion_intensity == "strong":
            risk += 0.3
        
        # Loss framing with promotion-focused customers
        if "promotion" in customer_type.expanded_regulatory_focus.lower() and ad_profile.target_regulatory_focus == "prevention":
            risk += 0.2
        
        # Cognitive overload
        if customer_type.cognitive_load_tolerance == "minimal_cognitive" and ad_profile.complexity_level > 0.7:
            risk += 0.25
        
        # Independent customers with heavy social proof
        if customer_type.social_influence_type == "highly_independent":
            social_proof_total = sum([
                ad_profile.mechanism_emphasis.get("social_proof", 0),
                ad_profile.mechanism_emphasis.get("unity", 0)
            ])
            if social_proof_total > 0.6:
                risk += 0.2
        
        return min(1.0, risk)
    
    def _identify_strengths(
        self,
        mot_align: float,
        dec_align: float,
        mech_align: float,
        customer: UnifiedGranularType,
        ad: AdvertisementProfile
    ) -> List[str]:
        """Identify alignment strengths."""
        
        strengths = []
        
        if mot_align > 0.7:
            strengths.append(f"Strong motivation match: {customer.expanded_motivation} ↔ {ad.primary_value_proposition}")
        
        if dec_align > 0.7:
            strengths.append(f"Good decision style fit: {customer.expanded_decision_style} ↔ {ad.linguistic_style}")
        
        if mech_align > 0.7:
            top_mechanism = max(ad.mechanism_emphasis.keys(), key=lambda k: ad.mechanism_emphasis[k])
            strengths.append(f"Effective mechanism: {top_mechanism} works well for this customer type")
        
        if customer.persuadability_score > 0.7:
            strengths.append("High persuadability customer - responsive to advertising")
        
        return strengths[:4]
    
    def _identify_weaknesses(
        self,
        mot_align: float,
        dec_align: float,
        mech_align: float,
        cog_align: float,
        customer: UnifiedGranularType,
        ad: AdvertisementProfile
    ) -> List[str]:
        """Identify alignment weaknesses."""
        
        weaknesses = []
        
        if mot_align < 0.4:
            weaknesses.append(f"Motivation mismatch: {customer.expanded_motivation} poorly served by {ad.primary_value_proposition}")
        
        if dec_align < 0.4:
            weaknesses.append(f"Style mismatch: {ad.linguistic_style} style doesn't fit {customer.expanded_decision_style} processing")
        
        if cog_align < 0.4:
            weaknesses.append(f"Cognitive overload risk: {customer.cognitive_load_tolerance} can't handle {ad.linguistic_style} complexity")
        
        if customer.persuadability_score < 0.3 and ad.persuasion_intensity == "strong":
            weaknesses.append("Aggressive tactics may backfire on low-persuadability customer")
        
        return weaknesses[:4]
    
    def _generate_suggestions(
        self,
        customer: UnifiedGranularType,
        ad: AdvertisementProfile,
        weaknesses: List[str]
    ) -> List[str]:
        """Generate optimization suggestions."""
        
        suggestions = []
        
        # Suggest better value propositions
        if customer.expanded_motivation in MOTIVATION_VALUE_ALIGNMENT:
            best_values = sorted(
                MOTIVATION_VALUE_ALIGNMENT[customer.expanded_motivation].items(),
                key=lambda x: x[1],
                reverse=True
            )[:2]
            current_best = ad.primary_value_proposition
            if best_values and best_values[0][0] != current_best:
                suggestions.append(f"Consider emphasizing {best_values[0][0]} value proposition instead")
        
        # Suggest linguistic style changes
        if customer.expanded_decision_style in DECISION_STYLE_LINGUISTIC_ALIGNMENT:
            best_styles = sorted(
                DECISION_STYLE_LINGUISTIC_ALIGNMENT[customer.expanded_decision_style].items(),
                key=lambda x: x[1],
                reverse=True
            )[:2]
            if best_styles and best_styles[0][0] != ad.linguistic_style:
                suggestions.append(f"Adjust copy to {best_styles[0][0]} style for better fit")
        
        # Suggest mechanism adjustments
        if customer.expanded_decision_style in MECHANISM_SUSCEPTIBILITY:
            best_mechanisms = sorted(
                MECHANISM_SUSCEPTIBILITY[customer.expanded_decision_style].items(),
                key=lambda x: x[1],
                reverse=True
            )[:2]
            suggestions.append(f"Lead with {best_mechanisms[0][0]} mechanism for this decision style")
        
        # Complexity suggestions
        if customer.cognitive_load_tolerance == "minimal_cognitive":
            suggestions.append("Simplify messaging - use shorter sentences and clearer CTAs")
        elif customer.cognitive_load_tolerance == "high_cognitive":
            suggestions.append("Add more technical details and specifications")
        
        return suggestions[:5]
    
    def analyze_ad_for_customer_text(
        self,
        customer_text: str,
        ad_text: str,
        archetype: str = "pragmatist"
    ) -> AlignmentScore:
        """
        Convenience method to analyze alignment from raw text.
        
        Args:
            customer_text: Text from customer (review, query, comment)
            ad_text: Advertisement or product description text
            archetype: Customer archetype (default pragmatist)
            
        Returns:
            AlignmentScore
        """
        
        # Infer customer type from text
        customer_type = self.type_service.infer_type_from_text(customer_text, archetype)
        
        # Create ad profile
        ad_profile = create_advertisement_profile(ad_text)
        
        # Calculate alignment
        return self.calculate_alignment(customer_type, ad_profile)
    
    def find_best_customer_segments(
        self,
        ad_profile: AdvertisementProfile,
        top_n: int = 5
    ) -> List[Tuple[Dict[str, str], float]]:
        """
        Find the best customer segments for an advertisement.
        
        Returns list of (customer_config, alignment_score) tuples.
        """
        
        results = []
        
        # Sample key combinations
        motivations = ["immediate_gratification", "mastery_seeking", "status_signaling", 
                      "cost_minimization", "anxiety_reduction", "social_approval"]
        decision_styles = ["gut_instinct", "satisficing", "analytical_systematic"]
        archetypes = ["explorer", "achiever", "guardian", "pragmatist"]
        
        for motivation in motivations:
            for decision in decision_styles:
                for archetype in archetypes:
                    customer = self.type_service.get_unified_type(
                        motivation=self._map_expanded_to_original_motivation(motivation),
                        decision_style=self._map_expanded_to_original_decision(decision),
                        archetype=archetype,
                        expanded_motivation=motivation,
                        expanded_decision_style=decision,
                    )
                    
                    alignment = self.calculate_alignment(customer, ad_profile)
                    
                    results.append((
                        {
                            "motivation": motivation,
                            "decision_style": decision,
                            "archetype": archetype,
                        },
                        alignment.overall_alignment
                    ))
        
        # Sort by alignment and return top N
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_n]
    
    def _map_expanded_to_original_motivation(self, expanded: str) -> str:
        """Map expanded motivation to original."""
        mapping = {
            "immediate_gratification": "impulse",
            "mastery_seeking": "research_driven",
            "status_signaling": "status_signaling",
            "cost_minimization": "value_seeking",
            "anxiety_reduction": "functional_need",
            "social_approval": "social_proof",
        }
        return mapping.get(expanded, "functional_need")
    
    def _map_expanded_to_original_decision(self, expanded: str) -> str:
        """Map expanded decision style to original."""
        mapping = {
            "gut_instinct": "fast",
            "satisficing": "moderate",
            "analytical_systematic": "deliberate",
        }
        return mapping.get(expanded, "moderate")


# =============================================================================
# EXPORTS
# =============================================================================

def export_alignment_priors() -> Dict[str, Any]:
    """Export alignment matrices for cold-start priors."""
    return {
        "motivation_value_alignment": MOTIVATION_VALUE_ALIGNMENT,
        "decision_linguistic_alignment": DECISION_STYLE_LINGUISTIC_ALIGNMENT,
        "regulatory_emotional_alignment": REGULATORY_EMOTIONAL_ALIGNMENT,
        "archetype_personality_alignment": ARCHETYPE_PERSONALITY_ALIGNMENT,
        "mechanism_susceptibility": MECHANISM_SUSCEPTIBILITY,
        "cognitive_complexity_alignment": COGNITIVE_COMPLEXITY_ALIGNMENT,
        "social_persuasion_alignment": SOCIAL_PERSUASION_ALIGNMENT,
    }


# =============================================================================
# TESTING
# =============================================================================

if __name__ == "__main__":
    print("\n" + "="*70)
    print("CUSTOMER-ADVERTISEMENT ALIGNMENT TEST")
    print("="*70)
    
    service = CustomerAdAlignmentService()
    
    # Test alignment calculation
    print("\n=== Sample Alignment Analysis ===")
    
    # Create sample customer
    customer = service.type_service.get_unified_type(
        motivation="impulse",
        decision_style="fast",
        regulatory_focus="promotion",
        emotional_intensity="high",
        archetype="explorer",
    )
    
    # Create sample ad
    ad_text = """
    LIMITED TIME OFFER! Only 3 left in stock! 
    Join millions of happy customers who've discovered the secret to success.
    Don't miss out on this exclusive opportunity - ends tonight!
    Act now and get 50% off plus free shipping!
    """
    
    ad_profile = create_advertisement_profile(ad_text)
    
    # Calculate alignment
    alignment = service.calculate_alignment(customer, ad_profile)
    
    print(f"\nCustomer: {customer.expanded_motivation} / {customer.expanded_decision_style}")
    print(f"Ad: {ad_profile.primary_persuasion_technique} / {ad_profile.primary_emotional_appeal}")
    
    print(f"\n--- Alignment Scores ---")
    print(f"Overall Alignment: {alignment.overall_alignment:.0%}")
    print(f"Predicted Effectiveness: {alignment.predicted_effectiveness:.0%}")
    print(f"Backfire Risk: {alignment.backfire_risk:.0%}")
    
    print(f"\n--- Component Scores ---")
    print(f"Motivation Alignment: {alignment.motivation_alignment:.0%}")
    print(f"Decision Style Alignment: {alignment.decision_style_alignment:.0%}")
    print(f"Mechanism Alignment: {alignment.mechanism_alignment:.0%}")
    print(f"Cognitive Alignment: {alignment.cognitive_alignment:.0%}")
    
    print(f"\n--- Strengths ---")
    for strength in alignment.alignment_strengths:
        print(f"  ✓ {strength}")
    
    print(f"\n--- Weaknesses ---")
    for weakness in alignment.alignment_weaknesses:
        print(f"  ✗ {weakness}")
    
    print(f"\n--- Suggestions ---")
    for suggestion in alignment.optimization_suggestions:
        print(f"  → {suggestion}")
    
    # Test finding best segments
    print("\n\n=== Best Customer Segments for Ad ===")
    best_segments = service.find_best_customer_segments(ad_profile)
    
    for i, (config, score) in enumerate(best_segments, 1):
        print(f"{i}. {config['motivation']} / {config['decision_style']} / {config['archetype']}: {score:.0%}")
