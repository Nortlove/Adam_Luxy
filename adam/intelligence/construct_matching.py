#!/usr/bin/env python3
"""
ADAM CONSTRUCT MATCHING ENGINE
==============================

Unified intelligence layer that matches:
- Customer Susceptibility (Tier 1-2: from reviews)
- Brand Positioning (Tier 3: from brand descriptions)

This creates the optimal mechanism selection by finding the intersection
where customer responsiveness meets brand voice alignment.

FLOW:
┌─────────────────────────────────────────────────────────────────────┐
│                      CUSTOMER REVIEWS                                │
│                            ↓                                         │
│              Tier 1: Mechanism Susceptibility                        │
│              Tier 2: Message Crafting Traits                         │
└─────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────┐
│                    CONSTRUCT MATCHING ENGINE                         │
│   Customer Susceptibility × Brand Positioning = Optimal Mechanism   │
└─────────────────────────────────────────────────────────────────────┘
                              ↑
┌─────────────────────────────────────────────────────────────────────┐
│                      BRAND DESCRIPTIONS                              │
│                            ↓                                         │
│              Tier 3: Brand Positioning Traits                        │
└─────────────────────────────────────────────────────────────────────┘

KEY PRINCIPLE:
The best mechanism is one where:
1. Customer is SUSCEPTIBLE to it (will respond)
2. Brand VOICE supports it (authentic to brand)
3. Context is APPROPRIATE for it (timing, channel)

A mechanism that scores high on customer susceptibility but LOW on brand
alignment will feel inauthentic. A mechanism that aligns with brand voice
but the customer is LOW susceptibility will be ineffective.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from adam.intelligence.persuasion_susceptibility import (
    PersuasionSusceptibilityAnalyzer,
    SusceptibilityScore,
    analyze_customer_susceptibility,
)
from adam.intelligence.brand_trait_extraction import (
    BrandTraitAnalyzer,
    BrandTraitScore,
    analyze_brand_traits,
)

logger = logging.getLogger(__name__)


@dataclass
class MechanismMatch:
    """Represents a mechanism with matched customer-brand scores."""
    mechanism: str
    customer_susceptibility: float  # 0-1: How responsive customer is
    brand_alignment: float  # 0-1: How well it fits brand voice
    combined_score: float  # Weighted combination
    confidence: float  # Confidence in the match
    reasoning: str
    warnings: List[str] = field(default_factory=list)
    
    @property
    def recommendation(self) -> str:
        """Generate recommendation level."""
        if self.combined_score >= 0.7 and self.confidence >= 0.5:
            return "strongly_recommended"
        elif self.combined_score >= 0.5:
            return "recommended"
        elif self.combined_score >= 0.3:
            return "use_cautiously"
        else:
            return "avoid"


@dataclass
class MessageStyleMatch:
    """Recommendations for message style based on construct matching."""
    complexity: str  # "detailed", "moderate", "simple"
    tone: str  # "professional", "friendly", "urgent"
    emotional_rational: str  # "emotional", "balanced", "rational"
    evidence_level: str  # "high", "moderate", "low"
    urgency_level: str  # "high", "moderate", "avoid"
    reasoning: List[str] = field(default_factory=list)


# =============================================================================
# MECHANISM-TRAIT MAPPINGS
# =============================================================================

# Maps mechanisms to the customer susceptibility and brand traits that support them
MECHANISM_MAPPINGS = {
    "social_proof": {
        "customer_susceptibility": [
            ("social_proof_susceptibility", 1.0),  # Primary driver
        ],
        "brand_traits": [
            ("trust_communication", 0.5),  # Social proof is a trust signal
            ("accessibility_vs_exclusivity", -0.3),  # More accessible = more social proof
        ],
        "anti_signals": [
            ("reactance_tendency", -0.3),  # High reactance dampens
        ],
    },
    
    "authority": {
        "customer_susceptibility": [
            ("authority_bias_susceptibility", 1.0),
        ],
        "brand_traits": [
            ("authority_positioning", 0.8),  # Brand must support authority claims
            ("trust_communication", 0.3),
        ],
        "anti_signals": [
            ("skepticism_level", -0.2),  # Skeptics need MORE evidence
        ],
    },
    
    "scarcity": {
        "customer_susceptibility": [
            ("scarcity_reactivity", 1.0),
        ],
        "brand_traits": [
            ("urgency_scarcity_usage", 0.7),  # Brand must use scarcity naturally
            ("accessibility_vs_exclusivity", 0.4),  # Exclusivity supports scarcity
        ],
        "anti_signals": [
            ("reactance_tendency", -0.5),  # High reactance = scarcity backfires
        ],
    },
    
    "urgency": {
        "customer_susceptibility": [
            ("scarcity_reactivity", 0.8),
            ("delay_discounting", 0.6),  # Impulse buyers respond to urgency
        ],
        "brand_traits": [
            ("urgency_scarcity_usage", 0.8),
        ],
        "anti_signals": [
            ("reactance_tendency", -0.6),
        ],
    },
    
    "storytelling": {
        "customer_susceptibility": [
            ("information_avoidance", 0.3),  # Avoiders prefer stories over data
        ],
        "brand_traits": [
            ("emotional_vs_rational", 0.7),  # Emotional brands = storytelling
            ("authenticity_signals", 0.6),  # Authentic brands have stories
        ],
        "anti_signals": [],
    },
    
    "evidence": {
        "customer_susceptibility": [
            ("skepticism_level", 0.8),  # Skeptics need evidence
            ("cognitive_load_tolerance", 0.4),  # Need to process evidence
        ],
        "brand_traits": [
            ("authority_positioning", 0.5),
            ("emotional_vs_rational", -0.5),  # Inverse - rational brands
        ],
        "anti_signals": [
            ("information_avoidance", -0.4),  # Avoiders don't want evidence
        ],
    },
    
    "guarantee": {
        "customer_susceptibility": [
            ("risk_aversion", 0.9),  # Risk averse need guarantees
        ],
        "brand_traits": [
            ("risk_mitigation", 0.8),  # Brand must offer guarantees
            ("trust_communication", 0.5),
        ],
        "anti_signals": [],
    },
    
    "value_framing": {
        "customer_susceptibility": [
            ("price_sensitivity", 0.9),
            ("anchoring_susceptibility", 0.5),
        ],
        "brand_traits": [
            ("accessibility_vs_exclusivity", -0.3),  # Accessible brands = value
        ],
        "anti_signals": [],
    },
    
    "premium_positioning": {
        "customer_susceptibility": [
            ("price_sensitivity", -0.8),  # Inverse - not price sensitive
        ],
        "brand_traits": [
            ("accessibility_vs_exclusivity", 0.8),  # Premium brands
            ("authority_positioning", 0.4),
        ],
        "anti_signals": [],
    },
    
    "simplicity": {
        "customer_susceptibility": [
            ("cognitive_load_tolerance", -0.7),  # Low tolerance = need simple
            ("information_avoidance", 0.6),
        ],
        "brand_traits": [
            ("emotional_vs_rational", 0.3),  # Emotional brands can be simple
        ],
        "anti_signals": [],
    },
    
    "detailed_specs": {
        "customer_susceptibility": [
            ("cognitive_load_tolerance", 0.8),  # High tolerance = want details
            ("skepticism_level", 0.4),  # Skeptics want verification
        ],
        "brand_traits": [
            ("emotional_vs_rational", -0.6),  # Rational brands
            ("authority_positioning", 0.3),
        ],
        "anti_signals": [
            ("information_avoidance", -0.5),
        ],
    },
    
    "instant_gratification": {
        "customer_susceptibility": [
            ("delay_discounting", 0.9),  # High discounting = want now
        ],
        "brand_traits": [
            ("urgency_scarcity_usage", 0.4),
        ],
        "anti_signals": [],
    },
    
    "investment_framing": {
        "customer_susceptibility": [
            ("delay_discounting", -0.8),  # Low discounting = long-term thinkers
            ("risk_aversion", 0.3),
        ],
        "brand_traits": [
            ("trust_communication", 0.4),
            ("innovation_vs_heritage", -0.3),  # Heritage = proven investment
        ],
        "anti_signals": [],
    },
    
    "values_based": {
        "customer_susceptibility": [],  # All customers can respond to values
        "brand_traits": [
            ("social_responsibility", 0.9),  # Brand must have CSR
            ("authenticity_signals", 0.5),
        ],
        "anti_signals": [],
    },
    
    # Tier 3: Brand-Customer Matching Mechanisms
    "loyalty_rewards": {
        "customer_susceptibility": [
            ("loyalty_vs_variety", 1.0),  # High loyalty = responds to loyalty programs
        ],
        "brand_traits": [
            ("trust_communication", 0.5),
            ("authenticity_signals", 0.4),
        ],
        "anti_signals": [],
    },
    
    "novelty_appeal": {
        "customer_susceptibility": [
            ("loyalty_vs_variety", -0.9),  # Low loyalty (variety seekers) = novelty works
        ],
        "brand_traits": [
            ("innovation_vs_heritage", 0.8),  # Innovative brands
        ],
        "anti_signals": [
            ("risk_aversion", -0.3),  # Risk averse may resist novelty
        ],
    },
    
    "switching_incentive": {
        "customer_susceptibility": [
            ("loyalty_vs_variety", -0.8),  # Variety seekers switch
            ("price_sensitivity", 0.5),  # Price sensitive respond to incentives
        ],
        "brand_traits": [
            ("accessibility_vs_exclusivity", -0.4),  # Accessible brands compete on switching
        ],
        "anti_signals": [],
    },
    
    "impulse_trigger": {
        "customer_susceptibility": [
            ("compulsive_buying", 1.0),  # High compulsive = impulse works
            ("delay_discounting", 0.6),  # Want it now
        ],
        "brand_traits": [
            ("urgency_scarcity_usage", 0.5),
        ],
        "anti_signals": [
            ("reactance_tendency", -0.3),  # Reactance resists impulse triggers
        ],
    },
    
    "emotional_purchase": {
        "customer_susceptibility": [
            ("compulsive_buying", 0.8),
        ],
        "brand_traits": [
            ("emotional_vs_rational", 0.7),  # Emotional brands
            ("authenticity_signals", 0.4),
        ],
        "anti_signals": [
            ("skepticism_level", -0.3),  # Skeptics resist pure emotional appeals
        ],
    },
}


# =============================================================================
# MAIN MATCHING ENGINE
# =============================================================================

class ConstructMatchingEngine:
    """
    Matches customer susceptibility profiles with brand positioning
    to determine optimal mechanism selection.
    """
    
    def __init__(self):
        self.customer_analyzer = PersuasionSusceptibilityAnalyzer()
        self.brand_analyzer = BrandTraitAnalyzer()
        self.mechanism_mappings = MECHANISM_MAPPINGS
    
    def match(
        self,
        customer_reviews: List[str],
        brand_descriptions: List[str],
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Perform full construct matching analysis.
        
        Args:
            customer_reviews: List of customer review texts
            brand_descriptions: List of brand description texts
            context: Optional context (time, channel, etc.)
            
        Returns:
            Complete matching analysis with mechanism recommendations
        """
        # Analyze customer susceptibility
        customer_result = analyze_customer_susceptibility(customer_reviews)
        customer_profile = customer_result.get("susceptibility_profile", {})
        
        # Analyze brand traits
        brand_result = analyze_brand_traits(brand_descriptions)
        brand_profile = brand_result.get("brand_traits", {})
        
        # Match mechanisms
        mechanism_matches = self._match_mechanisms(customer_profile, brand_profile)
        
        # Determine message style
        message_style = self._determine_message_style(customer_profile, brand_profile)
        
        # Generate warnings
        warnings = self._generate_warnings(customer_profile, brand_profile, mechanism_matches)
        
        # Rank and select top mechanisms
        ranked_mechanisms = sorted(
            mechanism_matches.values(),
            key=lambda x: x.combined_score,
            reverse=True
        )
        
        return {
            "customer_susceptibility": customer_profile,
            "brand_positioning": brand_profile,
            "mechanism_matches": {m.mechanism: {
                "customer_susceptibility": m.customer_susceptibility,
                "brand_alignment": m.brand_alignment,
                "combined_score": m.combined_score,
                "confidence": m.confidence,
                "recommendation": m.recommendation,
                "reasoning": m.reasoning,
                "warnings": m.warnings,
            } for m in mechanism_matches.values()},
            "recommended_mechanisms": [
                m.mechanism for m in ranked_mechanisms[:5] 
                if m.recommendation in ["strongly_recommended", "recommended"]
            ],
            "avoid_mechanisms": [
                m.mechanism for m in ranked_mechanisms 
                if m.recommendation == "avoid"
            ],
            "message_style": {
                "complexity": message_style.complexity,
                "tone": message_style.tone,
                "emotional_rational": message_style.emotional_rational,
                "evidence_level": message_style.evidence_level,
                "urgency_level": message_style.urgency_level,
                "reasoning": message_style.reasoning,
            },
            "warnings": warnings,
            "summary": self._generate_summary(ranked_mechanisms, message_style, warnings),
        }
    
    def _match_mechanisms(
        self,
        customer_profile: Dict[str, Dict],
        brand_profile: Dict[str, Dict],
    ) -> Dict[str, MechanismMatch]:
        """Match all mechanisms based on customer and brand profiles."""
        matches = {}
        
        for mechanism, mapping in self.mechanism_mappings.items():
            customer_score, customer_conf = self._compute_customer_score(
                customer_profile, mapping
            )
            brand_score, brand_conf = self._compute_brand_score(
                brand_profile, mapping
            )
            
            # Combined score: weighted geometric mean (both must be present)
            # If brand doesn't support it, cap effectiveness even if customer susceptible
            if customer_score > 0 and brand_score > 0:
                combined = (customer_score ** 0.6) * (brand_score ** 0.4)
            elif customer_score > 0:
                combined = customer_score * 0.5  # Penalize lack of brand support
            else:
                combined = 0.0
            
            confidence = min(customer_conf, brand_conf) if customer_conf > 0 and brand_conf > 0 else 0.0
            
            # Generate reasoning
            reasoning = self._generate_mechanism_reasoning(
                mechanism, customer_score, brand_score, customer_profile, brand_profile, mapping
            )
            
            # Check for warnings
            warnings = self._check_mechanism_warnings(
                mechanism, customer_profile, brand_profile
            )
            
            matches[mechanism] = MechanismMatch(
                mechanism=mechanism,
                customer_susceptibility=customer_score,
                brand_alignment=brand_score,
                combined_score=combined,
                confidence=confidence,
                reasoning=reasoning,
                warnings=warnings,
            )
        
        return matches
    
    def _compute_customer_score(
        self,
        profile: Dict[str, Dict],
        mapping: Dict,
    ) -> Tuple[float, float]:
        """Compute customer susceptibility score for a mechanism."""
        customer_mappings = mapping.get("customer_susceptibility", [])
        anti_signals = mapping.get("anti_signals", [])
        
        if not customer_mappings and not anti_signals:
            return 0.5, 0.0  # Neutral, no confidence
        
        score = 0.0
        weight_sum = 0.0
        confidence_sum = 0.0
        
        # Positive susceptibility signals
        for construct, weight in customer_mappings:
            if construct in profile:
                construct_data = profile[construct]
                construct_score = construct_data.get("score", 0.5)
                construct_conf = construct_data.get("confidence", 0.0)
                
                score += construct_score * weight
                weight_sum += abs(weight)
                confidence_sum += construct_conf
        
        # Anti-signals (reduce score)
        for construct, weight in anti_signals:
            if construct in profile:
                construct_data = profile[construct]
                construct_score = construct_data.get("score", 0.5)
                construct_conf = construct_data.get("confidence", 0.0)
                
                # Anti-signals: high score = negative impact
                score += construct_score * weight  # weight is negative
                weight_sum += abs(weight)
                confidence_sum += construct_conf
        
        if weight_sum > 0:
            normalized_score = max(0.0, min(1.0, score / weight_sum + 0.5))
            avg_confidence = confidence_sum / (len(customer_mappings) + len(anti_signals))
        else:
            normalized_score = 0.5
            avg_confidence = 0.0
        
        return normalized_score, avg_confidence
    
    def _compute_brand_score(
        self,
        profile: Dict[str, Dict],
        mapping: Dict,
    ) -> Tuple[float, float]:
        """Compute brand alignment score for a mechanism."""
        brand_mappings = mapping.get("brand_traits", [])
        
        if not brand_mappings:
            return 0.5, 0.0  # Neutral, no specific brand requirement
        
        score = 0.0
        weight_sum = 0.0
        confidence_sum = 0.0
        
        for trait, weight in brand_mappings:
            if trait in profile:
                trait_data = profile[trait]
                trait_score = trait_data.get("score", 0.5)
                trait_conf = trait_data.get("confidence", 0.0)
                
                if weight > 0:
                    score += trait_score * weight
                else:
                    # Inverse relationship
                    score += (1 - trait_score) * abs(weight)
                
                weight_sum += abs(weight)
                confidence_sum += trait_conf
        
        if weight_sum > 0:
            normalized_score = max(0.0, min(1.0, score / weight_sum))
            avg_confidence = confidence_sum / len(brand_mappings)
        else:
            normalized_score = 0.5
            avg_confidence = 0.0
        
        return normalized_score, avg_confidence
    
    def _determine_message_style(
        self,
        customer_profile: Dict[str, Dict],
        brand_profile: Dict[str, Dict],
    ) -> MessageStyleMatch:
        """Determine recommended message style from profiles."""
        reasoning = []
        
        # Complexity
        cog_load = customer_profile.get("cognitive_load_tolerance", {}).get("score", 0.5)
        info_avoid = customer_profile.get("information_avoidance", {}).get("score", 0.5)
        brand_rational = brand_profile.get("emotional_vs_rational", {}).get("score", 0.5)
        
        if cog_load < 0.4 or info_avoid > 0.6:
            complexity = "simple"
            reasoning.append("Low cognitive tolerance or high info avoidance → simple messaging")
        elif cog_load > 0.6 and brand_rational < 0.4:
            complexity = "detailed"
            reasoning.append("High cognitive tolerance + rational brand → detailed messaging")
        else:
            complexity = "moderate"
        
        # Tone
        brand_auth = brand_profile.get("authority_positioning", {}).get("score", 0.5)
        brand_authentic = brand_profile.get("authenticity_signals", {}).get("score", 0.5)
        
        if brand_auth > 0.6:
            tone = "professional"
            reasoning.append("High authority positioning → professional tone")
        elif brand_authentic > 0.6:
            tone = "friendly"
            reasoning.append("High authenticity → friendly/relatable tone")
        else:
            tone = "balanced"
        
        # Emotional vs Rational
        if brand_rational > 0.6:
            emotional_rational = "emotional"
            reasoning.append("Emotional brand positioning → emotional messaging")
        elif brand_rational < 0.4:
            emotional_rational = "rational"
            reasoning.append("Rational brand positioning → evidence-based messaging")
        else:
            emotional_rational = "balanced"
        
        # Evidence level
        skepticism = customer_profile.get("skepticism_level", {}).get("score", 0.5)
        if skepticism > 0.6:
            evidence_level = "high"
            reasoning.append("High customer skepticism → lead with evidence")
        elif skepticism < 0.4:
            evidence_level = "low"
            reasoning.append("Low skepticism → lighter evidence burden")
        else:
            evidence_level = "moderate"
        
        # Urgency
        reactance = customer_profile.get("reactance_tendency", {}).get("score", 0.5)
        brand_urgency = brand_profile.get("urgency_scarcity_usage", {}).get("score", 0.5)
        scarcity_react = customer_profile.get("scarcity_reactivity", {}).get("score", 0.5)
        
        if reactance > 0.6:
            urgency_level = "avoid"
            reasoning.append("High reactance → avoid urgency tactics")
        elif brand_urgency > 0.6 and scarcity_react > 0.5:
            urgency_level = "high"
            reasoning.append("Brand uses urgency + customer receptive → use urgency")
        else:
            urgency_level = "moderate"
        
        return MessageStyleMatch(
            complexity=complexity,
            tone=tone,
            emotional_rational=emotional_rational,
            evidence_level=evidence_level,
            urgency_level=urgency_level,
            reasoning=reasoning,
        )
    
    def _generate_mechanism_reasoning(
        self,
        mechanism: str,
        customer_score: float,
        brand_score: float,
        customer_profile: Dict,
        brand_profile: Dict,
        mapping: Dict,
    ) -> str:
        """Generate human-readable reasoning for mechanism match."""
        parts = []
        
        if customer_score > 0.6:
            parts.append(f"Customer highly susceptible ({customer_score:.2f})")
        elif customer_score < 0.4:
            parts.append(f"Customer low susceptibility ({customer_score:.2f})")
        
        if brand_score > 0.6:
            parts.append(f"Brand strongly supports ({brand_score:.2f})")
        elif brand_score < 0.4:
            parts.append(f"Brand doesn't align ({brand_score:.2f})")
        
        return " | ".join(parts) if parts else "Neutral match"
    
    def _check_mechanism_warnings(
        self,
        mechanism: str,
        customer_profile: Dict,
        brand_profile: Dict,
    ) -> List[str]:
        """Check for specific warnings about using this mechanism."""
        warnings = []
        
        reactance = customer_profile.get("reactance_tendency", {}).get("score", 0.5)
        
        if mechanism in ["scarcity", "urgency", "fomo"] and reactance > 0.6:
            warnings.append("High reactance detected - this mechanism may backfire")
        
        skepticism = customer_profile.get("skepticism_level", {}).get("score", 0.5)
        brand_auth = brand_profile.get("authority_positioning", {}).get("score", 0.5)
        
        if mechanism == "authority" and skepticism > 0.7 and brand_auth < 0.5:
            warnings.append("Skeptical customers + weak authority positioning - need strong evidence")
        
        return warnings
    
    def _generate_warnings(
        self,
        customer_profile: Dict,
        brand_profile: Dict,
        mechanism_matches: Dict[str, MechanismMatch],
    ) -> List[Dict[str, str]]:
        """Generate overall warnings about the match."""
        warnings = []
        
        # Reactance warning
        reactance = customer_profile.get("reactance_tendency", {})
        if reactance.get("score", 0) > 0.6 and reactance.get("confidence", 0) > 0.3:
            warnings.append({
                "type": "high_reactance",
                "severity": "high",
                "message": "High customer reactance - avoid pressure tactics, emphasize choice",
            })
        
        # Skepticism + weak authority mismatch
        skepticism = customer_profile.get("skepticism_level", {})
        brand_auth = brand_profile.get("authority_positioning", {})
        if (skepticism.get("score", 0) > 0.6 and 
            brand_auth.get("score", 0) < 0.4):
            warnings.append({
                "type": "credibility_gap",
                "severity": "medium",
                "message": "Skeptical customers but brand lacks authority positioning - need third-party validation",
            })
        
        # Information avoidance + detailed brand mismatch
        info_avoid = customer_profile.get("information_avoidance", {})
        brand_rational = brand_profile.get("emotional_vs_rational", {})
        if (info_avoid.get("score", 0) > 0.6 and 
            brand_rational.get("score", 0) < 0.4):
            warnings.append({
                "type": "complexity_mismatch",
                "severity": "medium",
                "message": "Customers avoid info but brand is detail-heavy - simplify messaging",
            })
        
        return warnings
    
    def _generate_summary(
        self,
        ranked_mechanisms: List[MechanismMatch],
        message_style: MessageStyleMatch,
        warnings: List[Dict],
    ) -> str:
        """Generate executive summary of matching analysis."""
        parts = []
        
        # Top mechanisms
        top = [m for m in ranked_mechanisms[:3] if m.recommendation != "avoid"]
        if top:
            mech_names = [m.mechanism.replace("_", " ") for m in top]
            parts.append(f"Top mechanisms: {', '.join(mech_names)}")
        
        # Message style
        parts.append(f"Style: {message_style.tone} tone, {message_style.complexity} complexity")
        
        # Key warning
        if warnings:
            high_warnings = [w for w in warnings if w.get("severity") == "high"]
            if high_warnings:
                parts.append(f"⚠️ {high_warnings[0]['message']}")
        
        return " | ".join(parts)


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def match_constructs(
    customer_reviews: List[str],
    brand_descriptions: List[str],
    context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Main entry point for construct matching.
    
    Args:
        customer_reviews: List of customer review texts
        brand_descriptions: List of brand description texts
        context: Optional context dict
        
    Returns:
        Complete matching analysis
    """
    engine = ConstructMatchingEngine()
    return engine.match(customer_reviews, brand_descriptions, context)


def get_optimal_mechanisms(
    customer_reviews: List[str],
    brand_descriptions: List[str],
    top_n: int = 5,
) -> List[str]:
    """
    Quick function to get top N recommended mechanisms.
    
    Args:
        customer_reviews: List of customer review texts
        brand_descriptions: List of brand description texts
        top_n: Number of mechanisms to return
        
    Returns:
        List of mechanism names
    """
    result = match_constructs(customer_reviews, brand_descriptions)
    return result.get("recommended_mechanisms", [])[:top_n]


# =============================================================================
# EXAMPLE USAGE
# =============================================================================

if __name__ == "__main__":
    # Example: Tech product with analytical customers, authoritative brand
    customer_reviews = [
        "I spent weeks researching before buying. Read every review and compared specs.",
        "The technical specifications were important to me. I needed to verify the claims.",
        "Don't just trust marketing - I tested it myself before recommending.",
        "After reading the clinical studies, I was convinced. Evidence matters.",
    ]
    
    brand_descriptions = [
        """
        Developed by MIT engineers with 15+ patents. Clinically proven technology
        backed by peer-reviewed research. Industry leader in precision equipment.
        Trusted by professionals worldwide. 30-day money-back guarantee.
        """
    ]
    
    result = match_constructs(customer_reviews, brand_descriptions)
    
    print("=" * 70)
    print("CONSTRUCT MATCHING ANALYSIS")
    print("=" * 70)
    
    print(f"\nSummary: {result['summary']}")
    
    print("\nRecommended Mechanisms:")
    for mech in result["recommended_mechanisms"]:
        match_data = result["mechanism_matches"][mech]
        print(f"  ✓ {mech}: {match_data['combined_score']:.2f} ({match_data['recommendation']})")
        print(f"    Customer: {match_data['customer_susceptibility']:.2f} | Brand: {match_data['brand_alignment']:.2f}")
    
    print("\nAvoid Mechanisms:")
    for mech in result["avoid_mechanisms"]:
        match_data = result["mechanism_matches"][mech]
        print(f"  ✗ {mech}: {match_data['combined_score']:.2f}")
    
    print("\nMessage Style:")
    style = result["message_style"]
    print(f"  Complexity: {style['complexity']}")
    print(f"  Tone: {style['tone']}")
    print(f"  Evidence: {style['evidence_level']}")
    print(f"  Urgency: {style['urgency_level']}")
    
    if result["warnings"]:
        print("\nWarnings:")
        for w in result["warnings"]:
            print(f"  ⚠️ [{w['severity']}] {w['message']}")
