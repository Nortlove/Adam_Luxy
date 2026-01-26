# =============================================================================
# ADAM Mechanism Activation Atom
# Location: adam/atoms/core/mechanism_activation.py
# =============================================================================

"""
MECHANISM ACTIVATION ATOM

Synthesizes outputs from upstream atoms to select which psychological
mechanisms to activate for this user/context.

Receives:
- Regulatory focus assessment
- Construal level assessment
- Personality expression
- Historical mechanism effectiveness

Outputs:
- Ranked mechanism recommendations
- Activation intensities
- Mechanism combinations
"""

import logging
from typing import Dict, List, Optional, Tuple

from adam.atoms.core.base import BaseAtom
from adam.intelligence.graph_edge_service import get_graph_edge_service
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


# Mechanism definitions aligned with the 9 core mechanisms
CORE_MECHANISMS = {
    "temporal_construal": {
        "name": "Temporal Construal",
        "description": "Near-future concrete vs far-future abstract framing",
        "regulatory_affinity": {"promotion": 0.4, "prevention": 0.6},
        "construal_affinity": {"abstract": 0.8, "concrete": 0.3},
    },
    "regulatory_focus": {
        "name": "Regulatory Focus",
        "description": "Promotion (gain) vs Prevention (loss) framing",
        "regulatory_affinity": {"promotion": 0.9, "prevention": 0.9},
        "construal_affinity": {"abstract": 0.5, "concrete": 0.5},
    },
    "social_proof": {
        "name": "Social Proof",
        "description": "Others' behavior as validation",
        "regulatory_affinity": {"promotion": 0.6, "prevention": 0.7},
        "construal_affinity": {"abstract": 0.4, "concrete": 0.7},
    },
    "scarcity": {
        "name": "Scarcity",
        "description": "Limited availability creates urgency",
        "regulatory_affinity": {"promotion": 0.3, "prevention": 0.9},
        "construal_affinity": {"abstract": 0.2, "concrete": 0.9},
    },
    "anchoring": {
        "name": "Anchoring",
        "description": "Reference points shape value perception",
        "regulatory_affinity": {"promotion": 0.5, "prevention": 0.5},
        "construal_affinity": {"abstract": 0.3, "concrete": 0.8},
    },
    "identity_construction": {
        "name": "Identity Construction",
        "description": "Self-concept and aspiration alignment",
        "regulatory_affinity": {"promotion": 0.8, "prevention": 0.3},
        "construal_affinity": {"abstract": 0.9, "concrete": 0.3},
    },
    "mimetic_desire": {
        "name": "Mimetic Desire",
        "description": "Wanting what valued others want",
        "regulatory_affinity": {"promotion": 0.7, "prevention": 0.4},
        "construal_affinity": {"abstract": 0.6, "concrete": 0.5},
    },
    "attention_dynamics": {
        "name": "Attention Dynamics",
        "description": "Salience and focus management",
        "regulatory_affinity": {"promotion": 0.5, "prevention": 0.6},
        "construal_affinity": {"abstract": 0.4, "concrete": 0.7},
    },
    "embodied_cognition": {
        "name": "Embodied Cognition",
        "description": "Physical experience shapes thinking",
        "regulatory_affinity": {"promotion": 0.5, "prevention": 0.5},
        "construal_affinity": {"abstract": 0.2, "concrete": 0.9},
    },
}


class MechanismActivationAtom(BaseAtom):
    """
    Atom for selecting and activating psychological mechanisms.
    
    Synthesizes upstream atom outputs to determine:
    1. Which mechanisms to activate
    2. At what intensity
    3. In what combination
    """
    
    ATOM_TYPE = AtomType.MECHANISM_ACTIVATION
    ATOM_NAME = "mechanism_activation"
    TARGET_CONSTRUCT = "mechanism_selection"
    
    REQUIRED_SOURCES = [
        IntelligenceSourceType.MECHANISM_TRAJECTORIES,
        IntelligenceSourceType.BANDIT_POSTERIORS,
    ]
    
    OPTIONAL_SOURCES = [
        IntelligenceSourceType.GRAPH_EMERGENCE,
        IntelligenceSourceType.CROSS_DOMAIN_TRANSFER,
    ]
    
    async def _query_construct_specific(
        self,
        source: IntelligenceSourceType,
        atom_input: AtomInput,
    ) -> Optional[IntelligenceEvidence]:
        """Query construct-specific sources for mechanism selection."""
        
        if source == IntelligenceSourceType.CROSS_DOMAIN_TRANSFER:
            return await self._query_transfer_patterns(atom_input)
        
        return None
    
    async def _query_transfer_patterns(
        self,
        atom_input: AtomInput,
    ) -> Optional[IntelligenceEvidence]:
        """Query cross-domain transfer patterns for mechanisms."""
        # Would query Neo4j for patterns that transfer across categories
        return None
    
    def _get_upstream_assessments(
        self,
        atom_input: AtomInput,
    ) -> Tuple[str, str, float]:
        """Extract assessments from upstream atoms."""
        reg_focus = "balanced"
        construal = "moderate"
        confidence = 0.5
        
        # Get regulatory focus
        rf_output = atom_input.get_upstream("atom_regulatory_focus")
        if rf_output:
            reg_focus = rf_output.primary_assessment
            confidence = max(confidence, rf_output.overall_confidence)
        
        # Get construal level
        cl_output = atom_input.get_upstream("atom_construal_level")
        if cl_output:
            construal = cl_output.primary_assessment
            confidence = max(confidence, cl_output.overall_confidence)
        
        return reg_focus, construal, confidence
    
    def _score_mechanisms(
        self,
        reg_focus: str,
        construal: str,
        mechanism_history: Optional[Dict[str, float]] = None,
    ) -> Dict[str, float]:
        """
        Score mechanisms based on psychological state and history.
        """
        scores: Dict[str, float] = {}
        
        for mech_id, mech_def in CORE_MECHANISMS.items():
            # Base score from psychological fit
            reg_affinity = mech_def["regulatory_affinity"].get(reg_focus, 0.5)
            const_affinity = mech_def["construal_affinity"].get(construal, 0.5)
            
            # Weighted average (regulatory focus slightly more important)
            fit_score = 0.55 * reg_affinity + 0.45 * const_affinity
            
            # Adjust by historical effectiveness
            if mechanism_history and mech_id in mechanism_history:
                hist_score = mechanism_history[mech_id]
                # Blend: 60% fit, 40% history
                final_score = 0.6 * fit_score + 0.4 * hist_score
            else:
                final_score = fit_score
            
            scores[mech_id] = final_score
        
        return scores
    
    async def _apply_synergy_adjustments(
        self,
        scores: Dict[str, float],
        context: Optional[Dict[str, str]] = None,
    ) -> Dict[str, float]:
        """
        Apply graph-based synergy/antagonism adjustments to scores.
        
        Leverages SYNERGIZES_WITH and ANTAGONIZES edges from Neo4j
        to boost compatible mechanisms and penalize conflicting ones.
        """
        try:
            edge_service = get_graph_edge_service()
            adjusted = await edge_service.compute_synergy_adjusted_scores(
                mechanism_scores=scores,
                context=context,
            )
            
            logger.debug(
                f"Synergy adjustments applied: "
                f"{sum(abs(adjusted[k] - scores[k]) for k in scores):.3f} total delta"
            )
            
            return adjusted
            
        except Exception as e:
            logger.warning(f"Failed to apply synergy adjustments: {e}")
            return scores
    
    def _select_mechanisms(
        self,
        scores: Dict[str, float],
        top_n: int = 3,
    ) -> List[Tuple[str, float, bool]]:
        """
        Select top mechanisms with activation details.
        
        Returns: List of (mechanism_id, intensity, is_primary)
        """
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        
        selected = []
        for i, (mech_id, score) in enumerate(ranked[:top_n]):
            is_primary = (i == 0)
            # Intensity based on score (0.5 = moderate, 1.0 = full)
            intensity = 0.3 + score * 0.7
            selected.append((mech_id, intensity, is_primary))
        
        return selected
    
    async def _build_output(
        self,
        atom_input: AtomInput,
        evidence: MultiSourceEvidence,
        fusion_result: FusionResult,
    ) -> AtomOutput:
        """Build mechanism activation output."""
        
        # Get upstream assessments
        reg_focus, construal, upstream_confidence = self._get_upstream_assessments(
            atom_input
        )
        
        # Get mechanism history from evidence
        mechanism_history = {}
        mech_evi = evidence.get_evidence(IntelligenceSourceType.MECHANISM_TRAJECTORIES)
        if mech_evi and mech_evi.assessment_value is not None:
            # Would populate from full mechanism history
            pass
        
        # Score mechanisms (base scores from psychological fit)
        base_scores = self._score_mechanisms(reg_focus, construal, mechanism_history)
        
        # Apply graph-based synergy adjustments
        # This leverages SYNERGIZES_WITH and ANTAGONIZES edges
        context = {
            "regulatory_focus": reg_focus,
            "construal_level": construal,
        }
        scores = await self._apply_synergy_adjustments(base_scores, context)
        
        # Select top mechanisms
        selections = self._select_mechanisms(scores, top_n=3)
        
        # Build outputs
        primary_mechanism = selections[0][0] if selections else "social_proof"
        recommended = [s[0] for s in selections]
        weights = {s[0]: s[1] for s in selections}
        
        # Update fusion result
        fusion_result.assessment = primary_mechanism
        fusion_result.confidence = upstream_confidence * 0.9
        
        return AtomOutput(
            atom_id=self.config.atom_id,
            atom_type=self.ATOM_TYPE,
            request_id=atom_input.request_id,
            fusion_result=fusion_result,
            primary_assessment=primary_mechanism,
            secondary_assessments={
                "regulatory_focus": reg_focus,
                "construal_level": construal,
                "mechanism_scores": scores,
            },
            recommended_mechanisms=recommended,
            mechanism_weights=weights,
            inferred_states={
                f"mechanism_{m}": s for m, s in scores.items()
            },
            overall_confidence=fusion_result.confidence,
            evidence_package=evidence,
            sources_queried=len(evidence.sources_queried),
            claude_used=fusion_result.claude_used,
        )
