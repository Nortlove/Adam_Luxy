# =============================================================================
# ADAM Regulatory Focus Atom
# Location: adam/atoms/core/regulatory_focus.py
# =============================================================================

"""
REGULATORY FOCUS ATOM

Assesses user's regulatory focus orientation:
- Promotion focus: Achievement, aspirations, ideals
- Prevention focus: Safety, responsibilities, oughts

Multi-source evidence:
- Trait-based: Big Five personality (high Extraversion → promotion)
- State-based: Current arousal and context
- Empirical: Past responses to promotion/prevention messaging
- Mechanism: Historical effectiveness of focus-aligned mechanisms
"""

import logging
from typing import List, Optional

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

logger = logging.getLogger(__name__)


class RegulatoryFocusAtom(BaseAtom):
    """
    Atom for assessing regulatory focus orientation.
    
    Regulatory Focus Theory (Higgins, 1997):
    - Promotion focus: Motivated by gains, growth, accomplishment
    - Prevention focus: Motivated by safety, security, avoiding losses
    """
    
    ATOM_TYPE = AtomType.REGULATORY_FOCUS
    ATOM_NAME = "regulatory_focus"
    TARGET_CONSTRUCT = "regulatory_focus"
    
    REQUIRED_SOURCES = [
        IntelligenceSourceType.MECHANISM_TRAJECTORIES,
    ]
    
    OPTIONAL_SOURCES = [
        IntelligenceSourceType.EMPIRICAL_PATTERNS,
        IntelligenceSourceType.NONCONSCIOUS_SIGNALS,
        IntelligenceSourceType.GRAPH_EMERGENCE,
        IntelligenceSourceType.BANDIT_POSTERIORS,
    ]
    
    # Mapping from Big Five to regulatory focus
    # High Extraversion + Openness → Promotion
    # High Conscientiousness + Neuroticism → Prevention
    
    async def _query_construct_specific(
        self,
        source: IntelligenceSourceType,
        atom_input: AtomInput,
    ) -> Optional[IntelligenceEvidence]:
        """Query construct-specific sources for regulatory focus."""
        
        if source == IntelligenceSourceType.NONCONSCIOUS_SIGNALS:
            return await self._query_arousal_signals(atom_input)
        elif source == IntelligenceSourceType.EMPIRICAL_PATTERNS:
            return await self._query_focus_patterns(atom_input)
        elif source == IntelligenceSourceType.BANDIT_POSTERIORS:
            return await self._query_focus_bandits(atom_input)
        
        return None
    
    async def _query_arousal_signals(
        self,
        atom_input: AtomInput,
    ) -> Optional[IntelligenceEvidence]:
        """
        Query arousal signals from current session.
        
        High arousal typically shifts users toward prevention focus
        (Yerkes-Dodson law: high arousal → narrow focus → safety seeking).
        """
        user_intel = atom_input.request_context.user_intelligence
        
        # Check real-time signals
        if user_intel.current_arousal is not None:
            arousal = user_intel.current_arousal
            
            # High arousal → prevention, low arousal → promotion
            if arousal > 0.7:
                focus = "prevention"
                reasoning = f"High arousal ({arousal:.2f}) suggests prevention orientation"
            elif arousal < 0.4:
                focus = "promotion"
                reasoning = f"Low arousal ({arousal:.2f}) allows promotion orientation"
            else:
                focus = "balanced"
                reasoning = f"Moderate arousal ({arousal:.2f}) suggests balanced focus"
            
            return IntelligenceEvidence(
                source_type=IntelligenceSourceType.NONCONSCIOUS_SIGNALS,
                construct=self.TARGET_CONSTRUCT,
                assessment=focus,
                assessment_value=arousal,
                confidence=0.6,
                confidence_semantics=ConfidenceSemantics.SIGNAL_STRENGTH,
                strength=EvidenceStrength.MODERATE,
                reasoning=reasoning,
            )
        
        return None
    
    async def _query_focus_patterns(
        self,
        atom_input: AtomInput,
    ) -> Optional[IntelligenceEvidence]:
        """
        Query empirically discovered patterns for regulatory focus.
        
        Looks for patterns like:
        - Users with behavior X respond to promotion messaging
        - Users in session context Y prefer prevention framing
        """
        # Would query Neo4j for empirical patterns
        # For now, derive from profile if available
        user_intel = atom_input.request_context.user_intelligence
        
        if user_intel.profile and user_intel.profile.big_five:
            bf = user_intel.profile.big_five
            
            # Promotion indicators: high Extraversion, high Openness
            promotion_score = (bf.extraversion + bf.openness) / 2
            
            # Prevention indicators: high Conscientiousness, high Neuroticism
            prevention_score = (bf.conscientiousness + bf.neuroticism) / 2
            
            if promotion_score > prevention_score + 0.15:
                focus = "promotion"
                confidence = min(0.85, 0.5 + abs(promotion_score - prevention_score))
            elif prevention_score > promotion_score + 0.15:
                focus = "prevention"
                confidence = min(0.85, 0.5 + abs(prevention_score - promotion_score))
            else:
                focus = "balanced"
                confidence = 0.5
            
            return IntelligenceEvidence(
                source_type=IntelligenceSourceType.EMPIRICAL_PATTERNS,
                construct=self.TARGET_CONSTRUCT,
                assessment=focus,
                assessment_value=promotion_score - prevention_score,
                confidence=confidence,
                confidence_semantics=ConfidenceSemantics.STATISTICAL,
                strength=EvidenceStrength.MODERATE,
                reasoning=f"Big Five profile suggests {focus} (P={promotion_score:.2f}, V={prevention_score:.2f})",
            )
        
        return None
    
    async def _query_focus_bandits(
        self,
        atom_input: AtomInput,
    ) -> Optional[IntelligenceEvidence]:
        """
        Query bandit posteriors for focus-aligned messaging.
        """
        user_intel = atom_input.request_context.user_intelligence
        
        if user_intel.mechanism_history:
            # Look for focus-related mechanisms
            promo_mechs = ["gain_framing", "aspiration_activation", "achievement"]
            prev_mechs = ["loss_framing", "safety_activation", "responsibility"]
            
            promo_success = 0.5
            prev_success = 0.5
            promo_trials = 0
            prev_trials = 0
            
            for mech_id, mech in user_intel.mechanism_history.mechanisms.items():
                if any(pm in mech_id.lower() for pm in promo_mechs):
                    promo_success = max(promo_success, mech.success_rate)
                    promo_trials += mech.trial_count
                elif any(pm in mech_id.lower() for pm in prev_mechs):
                    prev_success = max(prev_success, mech.success_rate)
                    prev_trials += mech.trial_count
            
            total_trials = promo_trials + prev_trials
            if total_trials > 5:
                if promo_success > prev_success + 0.1:
                    focus = "promotion"
                    confidence = 0.7
                elif prev_success > promo_success + 0.1:
                    focus = "prevention"
                    confidence = 0.7
                else:
                    focus = "balanced"
                    confidence = 0.5
                
                return IntelligenceEvidence(
                    source_type=IntelligenceSourceType.BANDIT_POSTERIORS,
                    construct=self.TARGET_CONSTRUCT,
                    assessment=focus,
                    confidence=confidence,
                    confidence_semantics=ConfidenceSemantics.BAYESIAN_POSTERIOR,
                    strength=self._trial_count_to_strength(total_trials),
                    support_count=total_trials,
                    reasoning=f"Focus bandit: promotion={promo_success:.2f}, prevention={prev_success:.2f}",
                )
        
        return None
    
    async def _build_output(
        self,
        atom_input: AtomInput,
        evidence: MultiSourceEvidence,
        fusion_result: FusionResult,
    ) -> AtomOutput:
        """Build regulatory focus output."""
        
        # Map assessment to recommended mechanisms
        focus = fusion_result.assessment
        
        if focus == "promotion":
            recommended = ["gain_framing", "aspiration_activation", "growth_messaging"]
            weights = {"gain_framing": 0.8, "aspiration_activation": 0.6}
        elif focus == "prevention":
            recommended = ["loss_framing", "safety_activation", "security_messaging"]
            weights = {"loss_framing": 0.8, "safety_activation": 0.6}
        else:  # balanced
            recommended = ["balanced_framing", "dual_focus"]
            weights = {"balanced_framing": 0.6}
        
        # Calculate promotion vs prevention tendency
        promo_tendency = 0.5
        prev_tendency = 0.5
        if focus == "promotion":
            promo_tendency = 0.5 + fusion_result.confidence * 0.4
            prev_tendency = 0.5 - fusion_result.confidence * 0.3
        elif focus == "prevention":
            prev_tendency = 0.5 + fusion_result.confidence * 0.4
            promo_tendency = 0.5 - fusion_result.confidence * 0.3
        
        return AtomOutput(
            atom_id=self.config.atom_id,
            atom_type=self.ATOM_TYPE,
            request_id=atom_input.request_id,
            fusion_result=fusion_result,
            primary_assessment=focus,
            secondary_assessments={
                "promotion_tendency": promo_tendency,
                "prevention_tendency": prev_tendency,
            },
            recommended_mechanisms=recommended,
            mechanism_weights=weights,
            inferred_states={
                "regulatory_focus_promotion": promo_tendency,
                "regulatory_focus_prevention": prev_tendency,
            },
            overall_confidence=fusion_result.confidence,
            evidence_package=evidence,
            sources_queried=len(evidence.sources_queried),
            claude_used=fusion_result.claude_used,
        )
