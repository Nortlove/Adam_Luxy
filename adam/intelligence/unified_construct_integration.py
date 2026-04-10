#!/usr/bin/env python3
"""
UNIFIED CONSTRUCT INTEGRATION
=============================

Phase 6: Full Intelligence Utilization

This module integrates ALL 35 psychological constructs into mechanism selection,
ensuring that the full depth of psychological profiling drives ad decisions.

Previously:
- 35 constructs were defined but not fully utilized
- Mechanism selection used only 6-7 constructs
- Rich construct data was computed but ignored

Now:
- All 35 constructs with mechanism_influences are used
- Construct profiles from reviews are mapped to mechanism adjustments
- Comprehensive psychological intelligence drives every decision

The 35 constructs span 7 domains:
1. Cognitive Processing (3): NFC, PSP, HRI
2. Self-Regulatory (3): SM, RF, LAM
3. Social (3): SCO, Conformity, Fairness
4. Information Processing (3): HA, VT, DT
5. Motivation (3): AT, Achievement, Approach
6. Decision Making (3): Maximizer, SC, TI
7. Uncertainty (3): AT, RU, CR

Plus specialized constructs for emotions, temporal patterns, etc.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum

logger = logging.getLogger(__name__)


# =============================================================================
# CONSTRUCT DOMAINS
# =============================================================================

class ConstructDomain(str, Enum):
    """Domains for the 35 psychological constructs."""
    COGNITIVE_PROCESSING = "cognitive_processing"
    SELF_REGULATORY = "self_regulatory"
    SOCIAL = "social"
    INFORMATION_PROCESSING = "information_processing"
    MOTIVATION = "motivation"
    DECISION_MAKING = "decision_making"
    UNCERTAINTY = "uncertainty"
    EMOTIONAL = "emotional"
    TEMPORAL = "temporal"
    BIG_FIVE = "big_five"


# =============================================================================
# MECHANISM INFLUENCE MAPPINGS (from CONSTRUCT_DEFINITIONS)
# =============================================================================

# Maps each construct to its influence on cognitive mechanisms
# Positive values = construct increases mechanism effectiveness
# Negative values = construct decreases mechanism effectiveness

CONSTRUCT_MECHANISM_INFLUENCES: Dict[str, Dict[str, float]] = {
    # Cognitive Processing Domain
    "cognitive_nfc": {
        "construal_level": 0.3,
        "automatic_evaluation": -0.2,
        "attention_dynamics": 0.25,
    },
    "cognitive_psp": {
        "automatic_evaluation": -0.4,
        "construal_level": 0.2,
        "attention_dynamics": 0.2,
    },
    "cognitive_hri": {
        "automatic_evaluation": 0.4,
        "mimetic_desire": 0.25,
        "construal_level": -0.2,
    },
    
    # Self-Regulatory Domain
    "selfreg_sm": {
        "identity_construction": 0.35,
        "mimetic_desire": 0.3,
        "automatic_evaluation": 0.15,
    },
    "selfreg_rf": {
        "regulatory_focus": 0.5,
        "temporal_construal": 0.2,
        "wanting_liking": 0.15,
    },
    "selfreg_lam": {
        "automatic_evaluation": 0.2,
        "attention_dynamics": 0.15,
        "wanting_liking": 0.25,
    },
    
    # Social Domain
    "social_sco": {
        "mimetic_desire": 0.4,
        "identity_construction": 0.3,
        "social_proof": 0.35,
    },
    "social_conformity": {
        "mimetic_desire": 0.45,
        "social_proof": 0.4,
        "automatic_evaluation": 0.15,
    },
    "social_fairness": {
        "loss_aversion": 0.25,
        "automatic_evaluation": -0.15,
        "regulatory_focus": -0.1,
    },
    
    # Information Processing Domain
    "info_holistic_analytic": {
        "construal_level": 0.35,
        "attention_dynamics": 0.2,
        "automatic_evaluation": -0.2,
    },
    "info_visualizer_verbalizer": {
        "attention_dynamics": 0.15,
        "construal_level": 0.1,
    },
    "info_domain_trans": {
        "construal_level": -0.2,
        "attention_dynamics": 0.25,
    },
    
    # Motivation Domain
    "motivation_at": {
        "wanting_liking": 0.35,
        "regulatory_focus": 0.25,
        "identity_construction": 0.2,
    },
    "motivation_achievement": {
        "regulatory_focus": 0.4,
        "identity_construction": 0.3,
        "wanting_liking": 0.25,
    },
    "motivation_approach": {
        "regulatory_focus": 0.35,
        "wanting_liking": 0.3,
        "automatic_evaluation": 0.2,
    },
    
    # Decision Making Domain
    "decision_maximizer": {
        "automatic_evaluation": -0.35,
        "attention_dynamics": 0.3,
        "construal_level": 0.2,
    },
    "decision_sc": {
        "automatic_evaluation": 0.25,
        "construal_level": -0.15,
        "loss_aversion": 0.2,
    },
    "decision_ti": {
        "loss_aversion": 0.35,
        "automatic_evaluation": 0.2,
        "regulatory_focus": 0.15,
    },
    
    # Uncertainty Domain
    "uncertainty_at": {
        "loss_aversion": -0.25,
        "automatic_evaluation": 0.15,
        "wanting_liking": 0.2,
    },
    "uncertainty_ru": {
        "loss_aversion": 0.4,
        "automatic_evaluation": -0.2,
        "construal_level": -0.15,
    },
    "uncertainty_cr": {
        "construal_level": 0.3,
        "automatic_evaluation": -0.15,
        "attention_dynamics": 0.15,
    },
    
    # Emotional Domain
    "emotional_intensity": {
        "automatic_evaluation": 0.3,
        "wanting_liking": 0.35,
        "loss_aversion": 0.2,
    },
    "emotional_regulation": {
        "automatic_evaluation": -0.2,
        "construal_level": 0.15,
        "regulatory_focus": 0.1,
    },
    
    # Temporal Domain
    "temporal_orientation": {
        "temporal_construal": 0.4,
        "construal_level": 0.25,
        "loss_aversion": -0.15,
    },
    "temporal_discounting": {
        "loss_aversion": 0.3,
        "automatic_evaluation": 0.2,
        "wanting_liking": 0.25,
    },
    
    # Big Five Traits (mapped to mechanisms)
    "big5_openness": {
        "construal_level": 0.3,
        "identity_construction": 0.25,
        "automatic_evaluation": -0.1,
    },
    "big5_conscientiousness": {
        "regulatory_focus": 0.25,
        "automatic_evaluation": -0.2,
        "loss_aversion": 0.15,
    },
    "big5_extraversion": {
        "social_proof": 0.3,
        "mimetic_desire": 0.25,
        "wanting_liking": 0.2,
    },
    "big5_agreeableness": {
        "social_proof": 0.25,
        "mimetic_desire": 0.2,
        "automatic_evaluation": 0.15,
    },
    "big5_neuroticism": {
        "loss_aversion": 0.35,
        "regulatory_focus": -0.2,
        "automatic_evaluation": 0.15,
    },
    
    # Susceptibility Constructs (map to mechanisms)
    "suscept_social_proof": {
        "social_proof": 0.6,
        "mimetic_desire": 0.4,
    },
    "suscept_authority": {
        "automatic_evaluation": 0.3,
        "construal_level": 0.2,
    },
    "suscept_scarcity": {
        "loss_aversion": 0.5,
        "automatic_evaluation": 0.3,
    },
    "suscept_anchoring": {
        "automatic_evaluation": 0.4,
        "construal_level": -0.2,
    },
    "suscept_delay_discounting": {
        "temporal_construal": 0.4,
        "wanting_liking": 0.3,
    },
}


@dataclass
class ConstructProfile:
    """A user's psychological construct profile."""
    
    construct_scores: Dict[str, float] = field(default_factory=dict)
    confidence_scores: Dict[str, float] = field(default_factory=dict)
    source: str = "review_analysis"
    
    @property
    def active_constructs(self) -> List[str]:
        """Get constructs with non-neutral scores (deviation from 0.5)."""
        return [
            cid for cid, score in self.construct_scores.items()
            if abs(score - 0.5) > 0.1 and self.confidence_scores.get(cid, 0) > 0.3
        ]
    
    def get_domain_profile(self, domain: ConstructDomain) -> Dict[str, float]:
        """Get scores for a specific domain."""
        domain_prefix = domain.value.split("_")[0]  # e.g., "cognitive"
        return {
            cid: score
            for cid, score in self.construct_scores.items()
            if cid.startswith(domain_prefix)
        }


@dataclass
class MechanismAdjustment:
    """Adjustment to mechanism effectiveness based on constructs."""
    
    mechanism_id: str
    base_effectiveness: float
    construct_adjustment: float
    final_effectiveness: float
    contributing_constructs: List[Tuple[str, float]]  # [(construct_id, contribution)]
    confidence: float
    
    @property
    def adjustment_direction(self) -> str:
        if self.construct_adjustment > 0.1:
            return "enhanced"
        elif self.construct_adjustment < -0.1:
            return "reduced"
        return "neutral"


class UnifiedConstructIntegration:
    """
    Integrates all 35 psychological constructs into mechanism selection.
    
    This is the central hub for translating psychological profiles
    into mechanism effectiveness adjustments.
    """
    
    def __init__(self):
        self._adjustments_computed: int = 0
    
    def compute_mechanism_adjustments(
        self,
        construct_profile: ConstructProfile,
        mechanisms: List[str],
    ) -> Dict[str, MechanismAdjustment]:
        """
        Compute mechanism effectiveness adjustments based on construct profile.
        
        This is the core function that makes all 35 constructs actionable.
        
        Args:
            construct_profile: User's psychological construct scores
            mechanisms: List of mechanism IDs to compute adjustments for
            
        Returns:
            Dict mapping mechanism_id to MechanismAdjustment
        """
        adjustments = {}
        
        for mechanism_id in mechanisms:
            # Start with base effectiveness
            base_effectiveness = 0.5
            construct_adjustment = 0.0
            contributing_constructs = []
            total_influence_weight = 0.0
            
            # Iterate through all constructs
            for construct_id, score in construct_profile.construct_scores.items():
                # Get mechanism influences for this construct
                influences = CONSTRUCT_MECHANISM_INFLUENCES.get(construct_id, {})
                
                if mechanism_id in influences:
                    influence_strength = influences[mechanism_id]
                    confidence = construct_profile.confidence_scores.get(construct_id, 0.5)
                    
                    # Score deviation from neutral (0.5)
                    score_deviation = score - 0.5
                    
                    # Compute contribution: influence * deviation * confidence
                    contribution = influence_strength * score_deviation * confidence
                    
                    if abs(contribution) > 0.01:
                        construct_adjustment += contribution
                        contributing_constructs.append((construct_id, contribution))
                        total_influence_weight += abs(influence_strength) * confidence
            
            # Clamp adjustment to reasonable range
            construct_adjustment = max(-0.4, min(0.4, construct_adjustment))
            
            # Compute final effectiveness
            final_effectiveness = base_effectiveness + construct_adjustment
            final_effectiveness = max(0.1, min(0.9, final_effectiveness))
            
            # Compute confidence based on construct coverage and confidence
            num_contributing = len(contributing_constructs)
            avg_confidence = (
                sum(construct_profile.confidence_scores.get(cid, 0.5) for cid, _ in contributing_constructs)
                / max(1, num_contributing)
            )
            adjustment_confidence = min(1.0, (num_contributing / 5) * avg_confidence)
            
            adjustments[mechanism_id] = MechanismAdjustment(
                mechanism_id=mechanism_id,
                base_effectiveness=base_effectiveness,
                construct_adjustment=construct_adjustment,
                final_effectiveness=final_effectiveness,
                contributing_constructs=sorted(
                    contributing_constructs,
                    key=lambda x: abs(x[1]),
                    reverse=True
                ),
                confidence=adjustment_confidence,
            )
        
        self._adjustments_computed += 1
        
        return adjustments
    
    def get_recommended_mechanisms(
        self,
        construct_profile: ConstructProfile,
        top_n: int = 5,
    ) -> List[Tuple[str, MechanismAdjustment]]:
        """
        Get top N recommended mechanisms based on construct profile.
        
        Returns mechanisms ordered by final_effectiveness * confidence.
        """
        # Get all mechanism IDs from the influence mappings
        all_mechanisms = set()
        for influences in CONSTRUCT_MECHANISM_INFLUENCES.values():
            all_mechanisms.update(influences.keys())
        
        # Compute adjustments for all mechanisms
        adjustments = self.compute_mechanism_adjustments(
            construct_profile,
            list(all_mechanisms),
        )
        
        # Sort by effectiveness * confidence
        ranked = sorted(
            adjustments.items(),
            key=lambda x: x[1].final_effectiveness * x[1].confidence,
            reverse=True,
        )
        
        return ranked[:top_n]
    
    def get_mechanism_warnings(
        self,
        construct_profile: ConstructProfile,
        mechanism_id: str,
    ) -> List[str]:
        """
        Get warnings for using a mechanism with this construct profile.
        
        Helps avoid backfire effects.
        """
        warnings = []
        
        # Check for strong negative influences
        for construct_id, score in construct_profile.construct_scores.items():
            influences = CONSTRUCT_MECHANISM_INFLUENCES.get(construct_id, {})
            
            if mechanism_id in influences:
                influence = influences[mechanism_id]
                score_deviation = score - 0.5
                
                # Warning if high score + negative influence or low score + positive influence
                if influence < -0.2 and score > 0.7:
                    construct_name = construct_id.replace("_", " ").title()
                    warnings.append(
                        f"High {construct_name} ({score:.2f}) may reduce effectiveness of {mechanism_id}"
                    )
                elif influence > 0.2 and score < 0.3:
                    construct_name = construct_id.replace("_", " ").title()
                    warnings.append(
                        f"Low {construct_name} ({score:.2f}) may not respond well to {mechanism_id}"
                    )
        
        return warnings
    
    def get_stats(self) -> Dict[str, Any]:
        """Get integration statistics."""
        return {
            "adjustments_computed": self._adjustments_computed,
            "constructs_available": len(CONSTRUCT_MECHANISM_INFLUENCES),
            "mechanisms_covered": len(set(
                m for infl in CONSTRUCT_MECHANISM_INFLUENCES.values() for m in infl.keys()
            )),
        }


# =============================================================================
# SINGLETON AND HELPERS
# =============================================================================

_integration: Optional[UnifiedConstructIntegration] = None


def get_unified_construct_integration() -> UnifiedConstructIntegration:
    """Get singleton unified construct integration."""
    global _integration
    if _integration is None:
        _integration = UnifiedConstructIntegration()
    return _integration


def adjust_mechanisms_with_constructs(
    construct_scores: Dict[str, float],
    construct_confidences: Dict[str, float],
    mechanisms: List[str],
) -> Dict[str, float]:
    """
    Convenience function to get mechanism adjustments from construct scores.
    
    Returns dict mapping mechanism_id -> adjusted_effectiveness
    """
    integration = get_unified_construct_integration()
    
    profile = ConstructProfile(
        construct_scores=construct_scores,
        confidence_scores=construct_confidences,
    )
    
    adjustments = integration.compute_mechanism_adjustments(profile, mechanisms)
    
    return {
        mechanism_id: adj.final_effectiveness
        for mechanism_id, adj in adjustments.items()
    }


def get_construct_based_recommendations(
    construct_scores: Dict[str, float],
    construct_confidences: Dict[str, float],
    top_n: int = 5,
) -> List[Dict[str, Any]]:
    """
    Get mechanism recommendations based on construct profile.
    
    Returns list of dicts with mechanism info and adjustments.
    """
    integration = get_unified_construct_integration()
    
    profile = ConstructProfile(
        construct_scores=construct_scores,
        confidence_scores=construct_confidences,
    )
    
    recommendations = integration.get_recommended_mechanisms(profile, top_n)
    
    return [
        {
            "mechanism_id": mechanism_id,
            "effectiveness": adj.final_effectiveness,
            "adjustment": adj.construct_adjustment,
            "direction": adj.adjustment_direction,
            "top_contributing_constructs": [
                {"construct": cid, "contribution": contrib}
                for cid, contrib in adj.contributing_constructs[:3]
            ],
            "confidence": adj.confidence,
            "warnings": integration.get_mechanism_warnings(profile, mechanism_id),
        }
        for mechanism_id, adj in recommendations
    ]
