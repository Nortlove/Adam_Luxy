#!/usr/bin/env python3
"""
EXPANDED TYPE INTEGRATION SERVICE
==================================

Integrates the new empirical psychology framework with the existing
granular type system, providing:
1. Backward compatibility with 3,775 original types
2. Forward expansion to 1.9M+ types when needed
3. Linguistic signal detection
4. Dynamic type inference from behavior/text
"""

import json
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path

from .empirical_psychology_framework import (
    EXPANDED_MOTIVATIONS,
    EXPANDED_DECISION_STYLES,
    EXPANDED_REGULATORY_FOCUS,
    EXPANDED_EMOTIONAL_INTENSITY,
    COGNITIVE_LOAD_TOLERANCE,
    TEMPORAL_ORIENTATION,
    SOCIAL_INFLUENCE_SUSCEPTIBILITY,
    LinguisticPatternAnalyzer,
    calculate_expanded_granular_type,
    ExpandedGranularType,
    export_empirical_framework_priors,
)

from .granular_type_enrichment import (
    GranularTypeEnrichmentService,
    EnrichedGranularType,
    PERSUADABILITY_BY_MOTIVATION,
    MECHANISM_BY_ARCHETYPE,
)


# =============================================================================
# MAPPING: OLD → NEW DIMENSIONS
# =============================================================================

# Map original 15 motivations to expanded 37 motivations
MOTIVATION_EXPANSION_MAP = {
    # Original → Primary Expanded (with alternatives)
    "impulse": ("immediate_gratification", ["excitement_seeking", "sensory_pleasure"]),
    "social_proof": ("social_approval", ["belonging_affirmation", "social_compliance"]),
    "status_signaling": ("status_signaling", ["ego_protection", "uniqueness_differentiation"]),
    "self_reward": ("self_esteem_enhancement", ["sensory_pleasure", "escapism"]),
    "gift_giving": ("altruistic_giving", ["role_fulfillment", "relationship_maintenance"]),
    "value_seeking": ("cost_minimization", ["efficiency_optimization", "opportunity_cost_awareness"]),
    "quality_seeking": ("quality_assurance", ["risk_mitigation", "mastery_seeking"]),
    "brand_loyalty": ("values_alignment", ["conservative_preservation", "recognition_based"]),
    "research_driven": ("mastery_seeking", ["pure_curiosity", "analytical_systematic"]),
    "recommendation": ("authority_compliance", ["social_referencing", "informational_seeker"]),
    "functional_need": ("problem_solving", ["efficiency_optimization", "cost_minimization"]),
    "replacement": ("risk_mitigation", ["quality_assurance", "problem_solving"]),
    "upgrade": ("goal_achievement", ["future_self_investment", "mastery_seeking"]),
    "curiosity": ("pure_curiosity", ["optimistic_exploration", "flow_experience"]),
    "problem_solving": ("problem_solving", ["efficiency_optimization", "analytical_systematic"]),
}

# Map original 3 decision styles to expanded 12
DECISION_STYLE_EXPANSION_MAP = {
    "fast": ("gut_instinct", ["affect_driven", "recognition_based"]),
    "moderate": ("satisficing", ["heuristic_based", "social_referencing"]),
    "deliberate": ("analytical_systematic", ["maximizing", "deliberative_reflective"]),
}

# Map original 2 regulatory focuses to expanded 8
REGULATORY_FOCUS_EXPANSION_MAP = {
    "promotion": ("eager_advancement", ["aspiration_driven", "optimistic_exploration"]),
    "prevention": ("vigilant_security", ["conservative_preservation", "anxious_avoidance"]),
}

# Map original 3 emotional intensities to expanded 9
EMOTIONAL_INTENSITY_EXPANSION_MAP = {
    "high": ("high_positive_activation", ["mixed_high_arousal"]),
    "moderate": ("moderate_positive", ["emotionally_neutral"]),
    "low": ("low_positive_calm", ["apathetic_disengaged"]),
}


# =============================================================================
# UNIFIED TYPE SERVICE
# =============================================================================

@dataclass
class UnifiedGranularType:
    """
    Unified customer type that bridges original and expanded systems.
    
    Provides:
    - Original type code for backward compatibility
    - Expanded type code for deeper analysis
    - All psychological dimensions (original + expanded)
    - Combined scoring and mechanism recommendations
    """
    
    # Identification
    original_type_code: str
    expanded_type_code: str
    
    # Original dimensions (for compatibility)
    motivation: str
    decision_style: str
    regulatory_focus: str
    emotional_intensity: str
    archetype: str
    
    # Expanded dimensions (for depth)
    expanded_motivation: str
    motivation_category: str
    expanded_decision_style: str
    processing_mode: str
    expanded_regulatory_focus: str
    expanded_emotional_intensity: str
    cognitive_load_tolerance: str
    temporal_orientation: str
    social_influence_type: str
    
    # Computed scores
    persuadability_score: float
    autonomy_level: float
    hedonic_vs_utilitarian: float
    risk_tolerance: float
    temporal_stability: float
    
    # Mechanism recommendations
    mechanism_effectiveness: Dict[str, float]
    optimal_mechanism_sequence: List[str]
    
    # Messaging recommendations
    message_framing: str
    emotional_appeal_level: str
    information_density: str
    urgency_appropriateness: float
    social_proof_effectiveness: float
    
    # Linguistic signals
    linguistic_markers: List[str]
    behavioral_signals: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ExpandedTypeIntegrationService:
    """
    Service that integrates original and expanded granular type systems.
    
    Provides:
    1. Seamless upgrade from original to expanded types
    2. Linguistic analysis for type inference
    3. Behavioral signal detection
    4. Unified API for both systems
    """
    
    def __init__(self, priors_dir: Optional[Path] = None):
        self.original_service = GranularTypeEnrichmentService(priors_dir)
        self.linguistic_analyzer = LinguisticPatternAnalyzer()
        self._type_cache: Dict[str, UnifiedGranularType] = {}
    
    def get_unified_type(
        self,
        # Original dimensions
        motivation: str,
        decision_style: str,
        regulatory_focus: str = "promotion",
        emotional_intensity: str = "moderate",
        archetype: str = "pragmatist",
        # Optional expanded dimensions (auto-mapped if not provided)
        expanded_motivation: Optional[str] = None,
        expanded_decision_style: Optional[str] = None,
        expanded_regulatory_focus: Optional[str] = None,
        expanded_emotional_intensity: Optional[str] = None,
        cognitive_load: str = "moderate_cognitive",
        temporal_orientation: str = "medium_term",
        social_influence: str = "socially_aware",
    ) -> UnifiedGranularType:
        """
        Get a unified granular type bridging original and expanded systems.
        """
        
        # Map original to expanded if not provided
        if not expanded_motivation:
            exp_mot, _ = MOTIVATION_EXPANSION_MAP.get(motivation, (motivation, []))
            expanded_motivation = exp_mot
        
        if not expanded_decision_style:
            exp_dec, _ = DECISION_STYLE_EXPANSION_MAP.get(decision_style, (decision_style, []))
            expanded_decision_style = exp_dec
        
        if not expanded_regulatory_focus:
            exp_reg, _ = REGULATORY_FOCUS_EXPANSION_MAP.get(regulatory_focus, (regulatory_focus, []))
            expanded_regulatory_focus = exp_reg
        
        if not expanded_emotional_intensity:
            exp_emo, _ = EMOTIONAL_INTENSITY_EXPANSION_MAP.get(emotional_intensity, (emotional_intensity, []))
            expanded_emotional_intensity = exp_emo
        
        # Get original enriched type
        original_type = self.original_service.enrich_type(
            motivation=motivation,
            decision_style=decision_style,
            regulatory_focus=regulatory_focus,
            emotional_intensity=emotional_intensity,
            price_sensitivity="moderate",
            archetype=archetype,
        )
        
        # Get expanded type
        expanded_type = calculate_expanded_granular_type(
            motivation=expanded_motivation,
            decision_style=expanded_decision_style,
            regulatory_focus=expanded_regulatory_focus,
            emotional_intensity=expanded_emotional_intensity,
            cognitive_load=cognitive_load,
            temporal_orientation=temporal_orientation,
            social_influence=social_influence,
        )
        
        # Get linguistic markers from expanded dimensions
        linguistic_markers = []
        if expanded_motivation in EXPANDED_MOTIVATIONS:
            linguistic_markers.extend(EXPANDED_MOTIVATIONS[expanded_motivation].linguistic_markers[:5])
        if expanded_decision_style in EXPANDED_DECISION_STYLES:
            linguistic_markers.extend(EXPANDED_DECISION_STYLES[expanded_decision_style].linguistic_markers[:3])
        
        # Get behavioral signals
        behavioral_signals = []
        if expanded_motivation in EXPANDED_MOTIVATIONS:
            behavioral_signals.extend(EXPANDED_MOTIVATIONS[expanded_motivation].behavioral_signals)
        
        # Combine persuadability from both systems (weighted)
        combined_persuadability = (
            original_type.persuadability_score * 0.6 +
            expanded_type.persuadability_score * 0.4
        )
        
        # Combine mechanism effectiveness
        combined_mechanisms = {}
        for mech in original_type.mechanism_effectiveness:
            orig_score = original_type.mechanism_effectiveness.get(mech, 0.5)
            exp_score = expanded_type.mechanism_effectiveness.get(mech, 0.5)
            combined_mechanisms[mech] = (orig_score * 0.5 + exp_score * 0.5)
        
        # Combine sequences (prioritize expanded which has more nuance)
        combined_sequence = expanded_type.optimal_mechanism_sequence
        
        return UnifiedGranularType(
            original_type_code=original_type.type_code,
            expanded_type_code=expanded_type.type_code,
            motivation=motivation,
            decision_style=decision_style,
            regulatory_focus=regulatory_focus,
            emotional_intensity=emotional_intensity,
            archetype=archetype,
            expanded_motivation=expanded_motivation,
            motivation_category=expanded_type.motivation_category,
            expanded_decision_style=expanded_decision_style,
            processing_mode=expanded_type.processing_mode,
            expanded_regulatory_focus=expanded_regulatory_focus,
            expanded_emotional_intensity=expanded_emotional_intensity,
            cognitive_load_tolerance=cognitive_load,
            temporal_orientation=temporal_orientation,
            social_influence_type=social_influence,
            persuadability_score=round(combined_persuadability, 3),
            autonomy_level=expanded_type.autonomy_level,
            hedonic_vs_utilitarian=expanded_type.hedonic_vs_utilitarian,
            risk_tolerance=expanded_type.risk_tolerance,
            temporal_stability=original_type.temporal_stability,
            mechanism_effectiveness=combined_mechanisms,
            optimal_mechanism_sequence=combined_sequence,
            message_framing=expanded_type.message_framing,
            emotional_appeal_level=expanded_type.emotional_appeal_level,
            information_density=expanded_type.information_density,
            urgency_appropriateness=expanded_type.urgency_appropriateness,
            social_proof_effectiveness=expanded_type.social_proof_effectiveness,
            linguistic_markers=linguistic_markers,
            behavioral_signals=behavioral_signals,
        )
    
    def infer_type_from_text(
        self,
        text: str,
        archetype: str = "pragmatist",
    ) -> UnifiedGranularType:
        """
        Infer customer type from text (review, comment, search query, etc.).
        
        Uses linguistic pattern analysis to detect psychological dimensions.
        """
        
        # Analyze text
        dominant = self.linguistic_analyzer.get_dominant_dimensions(text)
        
        # Extract dimensions from analysis
        expanded_motivation = None
        expanded_decision = None
        expanded_regulatory = None
        expanded_emotional = None
        cognitive_load = "moderate_cognitive"
        temporal = "medium_term"
        social = "socially_aware"
        
        if "motivation" in dominant:
            expanded_motivation = dominant["motivation"][0]
        if "decision_style" in dominant:
            expanded_decision = dominant["decision_style"][0]
        if "regulatory_focus" in dominant:
            expanded_regulatory = dominant["regulatory_focus"][0]
        if "emotional_intensity" in dominant:
            expanded_emotional = dominant["emotional_intensity"][0]
        if "cognitive_load" in dominant:
            cognitive_load = dominant["cognitive_load"][0]
        if "temporal_orientation" in dominant:
            temporal = dominant["temporal_orientation"][0]
        if "social_influence" in dominant:
            social = dominant["social_influence"][0]
        
        # Map back to original dimensions for compatibility
        original_motivation = self._reverse_map_motivation(expanded_motivation or "problem_solving")
        original_decision = self._reverse_map_decision(expanded_decision or "satisficing")
        original_regulatory = self._reverse_map_regulatory(expanded_regulatory or "pragmatic_balanced")
        original_emotional = self._reverse_map_emotional(expanded_emotional or "moderate_positive")
        
        return self.get_unified_type(
            motivation=original_motivation,
            decision_style=original_decision,
            regulatory_focus=original_regulatory,
            emotional_intensity=original_emotional,
            archetype=archetype,
            expanded_motivation=expanded_motivation,
            expanded_decision_style=expanded_decision,
            expanded_regulatory_focus=expanded_regulatory,
            expanded_emotional_intensity=expanded_emotional,
            cognitive_load=cognitive_load,
            temporal_orientation=temporal,
            social_influence=social,
        )
    
    def _reverse_map_motivation(self, expanded: str) -> str:
        """Map expanded motivation back to original."""
        for original, (primary, alts) in MOTIVATION_EXPANSION_MAP.items():
            if expanded == primary or expanded in alts:
                return original
        return "functional_need"  # Default
    
    def _reverse_map_decision(self, expanded: str) -> str:
        """Map expanded decision style back to original."""
        for original, (primary, alts) in DECISION_STYLE_EXPANSION_MAP.items():
            if expanded == primary or expanded in alts:
                return original
        return "moderate"
    
    def _reverse_map_regulatory(self, expanded: str) -> str:
        """Map expanded regulatory focus back to original."""
        for original, (primary, alts) in REGULATORY_FOCUS_EXPANSION_MAP.items():
            if expanded == primary or expanded in alts:
                return original
        return "promotion"
    
    def _reverse_map_emotional(self, expanded: str) -> str:
        """Map expanded emotional intensity back to original."""
        for original, (primary, alts) in EMOTIONAL_INTENSITY_EXPANSION_MAP.items():
            if expanded == primary or expanded in alts:
                return original
        return "moderate"
    
    def get_dimension_alternatives(
        self,
        motivation: str,
        decision_style: str,
        regulatory_focus: str,
        emotional_intensity: str,
    ) -> Dict[str, List[str]]:
        """
        Get alternative expanded dimensions for an original type.
        
        Useful for A/B testing and exploring adjacent type profiles.
        """
        
        mot_primary, mot_alts = MOTIVATION_EXPANSION_MAP.get(
            motivation, (motivation, [])
        )
        dec_primary, dec_alts = DECISION_STYLE_EXPANSION_MAP.get(
            decision_style, (decision_style, [])
        )
        reg_primary, reg_alts = REGULATORY_FOCUS_EXPANSION_MAP.get(
            regulatory_focus, (regulatory_focus, [])
        )
        emo_primary, emo_alts = EMOTIONAL_INTENSITY_EXPANSION_MAP.get(
            emotional_intensity, (emotional_intensity, [])
        )
        
        return {
            "motivation": [mot_primary] + mot_alts,
            "decision_style": [dec_primary] + dec_alts,
            "regulatory_focus": [reg_primary] + reg_alts,
            "emotional_intensity": [emo_primary] + emo_alts,
        }
    
    def generate_expanded_type_report(
        self,
        unified_type: UnifiedGranularType,
    ) -> str:
        """Generate detailed human-readable report for a type."""
        
        lines = [
            "=" * 60,
            f"UNIFIED GRANULAR TYPE REPORT",
            "=" * 60,
            "",
            "IDENTIFICATION",
            "-" * 30,
            f"Original Code: {unified_type.original_type_code}",
            f"Expanded Code: {unified_type.expanded_type_code}",
            "",
            "ORIGINAL DIMENSIONS",
            "-" * 30,
            f"Motivation: {unified_type.motivation}",
            f"Decision Style: {unified_type.decision_style}",
            f"Regulatory Focus: {unified_type.regulatory_focus}",
            f"Emotional Intensity: {unified_type.emotional_intensity}",
            f"Archetype: {unified_type.archetype}",
            "",
            "EXPANDED DIMENSIONS (Research-Backed)",
            "-" * 30,
            f"Motivation: {unified_type.expanded_motivation} ({unified_type.motivation_category})",
            f"Decision Style: {unified_type.expanded_decision_style} ({unified_type.processing_mode})",
            f"Regulatory Focus: {unified_type.expanded_regulatory_focus}",
            f"Emotional Intensity: {unified_type.expanded_emotional_intensity}",
            f"Cognitive Load: {unified_type.cognitive_load_tolerance}",
            f"Temporal Orientation: {unified_type.temporal_orientation}",
            f"Social Influence: {unified_type.social_influence_type}",
            "",
            "PSYCHOLOGICAL PROFILE",
            "-" * 30,
            f"Persuadability Score: {unified_type.persuadability_score:.0%}",
            f"Autonomy Level: {unified_type.autonomy_level:.0%}",
            f"Hedonic vs Utilitarian: {unified_type.hedonic_vs_utilitarian:+.2f}",
            f"Risk Tolerance: {unified_type.risk_tolerance:.0%}",
            f"Temporal Stability: {unified_type.temporal_stability:.0%}",
            "",
            "MESSAGING RECOMMENDATIONS",
            "-" * 30,
            f"Message Framing: {unified_type.message_framing.upper()}",
            f"Emotional Appeal: {unified_type.emotional_appeal_level}",
            f"Information Density: {unified_type.information_density}",
            f"Urgency Appropriateness: {unified_type.urgency_appropriateness:.0%}",
            f"Social Proof Effectiveness: {unified_type.social_proof_effectiveness:.0%}",
            "",
            "MECHANISM SEQUENCE",
            "-" * 30,
            f"Optimal Sequence: {' → '.join(unified_type.optimal_mechanism_sequence[:4])}",
            "",
            "DETECTION SIGNALS",
            "-" * 30,
            f"Linguistic Markers: {', '.join(unified_type.linguistic_markers[:5])}",
            f"Behavioral Signals: {', '.join(unified_type.behavioral_signals[:3])}",
            "",
            "=" * 60,
        ]
        
        return "\n".join(lines)


def export_expanded_priors() -> Dict[str, Any]:
    """Export all expanded framework priors for cold-start."""
    
    empirical_priors = export_empirical_framework_priors()
    
    return {
        **empirical_priors,
        "expansion_mappings": {
            "motivation": MOTIVATION_EXPANSION_MAP,
            "decision_style": DECISION_STYLE_EXPANSION_MAP,
            "regulatory_focus": REGULATORY_FOCUS_EXPANSION_MAP,
            "emotional_intensity": EMOTIONAL_INTENSITY_EXPANSION_MAP,
        },
    }


# =============================================================================
# TESTING
# =============================================================================

if __name__ == "__main__":
    print("\n" + "="*70)
    print("EXPANDED TYPE INTEGRATION TEST")
    print("="*70)
    
    service = ExpandedTypeIntegrationService()
    
    # Test unified type
    print("\n=== Unified Type (Original + Expanded) ===")
    unified = service.get_unified_type(
        motivation="impulse",
        decision_style="fast",
        regulatory_focus="promotion",
        emotional_intensity="high",
        archetype="explorer",
    )
    
    print(service.generate_expanded_type_report(unified))
    
    # Test text inference
    print("\n=== Type Inference from Text ===")
    test_text = "I need this NOW! Can't wait another minute, everyone's already got one!"
    inferred = service.infer_type_from_text(test_text, archetype="connector")
    
    print(f"Text: \"{test_text}\"")
    print(f"\nInferred Type:")
    print(f"  Original: {inferred.motivation} / {inferred.decision_style}")
    print(f"  Expanded: {inferred.expanded_motivation} / {inferred.expanded_decision_style}")
    print(f"  Persuadability: {inferred.persuadability_score:.0%}")
