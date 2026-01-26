# =============================================================================
# ADAM Construal Level Atom
# Location: adam/atoms/core/construal_level.py
# =============================================================================

"""
CONSTRUAL LEVEL ATOM

Assesses user's construal level:
- Abstract (high level): Big picture, "why", values, goals
- Concrete (low level): Details, "how", features, actions

Construal Level Theory (Trope & Liberman, 2010):
- Psychological distance increases abstraction
- Temporal, spatial, social, hypothetical distance all affect construal
"""

import logging
from typing import Optional

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


class ConstrualLevelAtom(BaseAtom):
    """
    Atom for assessing construal level (abstract vs concrete).
    
    High construal (abstract):
    - Focus on goals, values, "why"
    - Respond to big-picture messaging
    - More influenced by desirability
    
    Low construal (concrete):
    - Focus on actions, features, "how"
    - Respond to detail-oriented messaging
    - More influenced by feasibility
    """
    
    ATOM_TYPE = AtomType.CONSTRUAL_LEVEL
    ATOM_NAME = "construal_level"
    TARGET_CONSTRUCT = "construal_level"
    
    REQUIRED_SOURCES = [
        IntelligenceSourceType.MECHANISM_TRAJECTORIES,
    ]
    
    OPTIONAL_SOURCES = [
        IntelligenceSourceType.TEMPORAL_PATTERNS,
        IntelligenceSourceType.NONCONSCIOUS_SIGNALS,
        IntelligenceSourceType.GRAPH_EMERGENCE,
    ]
    
    async def _query_construct_specific(
        self,
        source: IntelligenceSourceType,
        atom_input: AtomInput,
    ) -> Optional[IntelligenceEvidence]:
        """Query construct-specific sources for construal level."""
        
        if source == IntelligenceSourceType.TEMPORAL_PATTERNS:
            return await self._query_temporal_distance(atom_input)
        elif source == IntelligenceSourceType.NONCONSCIOUS_SIGNALS:
            return await self._query_cognitive_load(atom_input)
        
        return None
    
    async def _query_temporal_distance(
        self,
        atom_input: AtomInput,
    ) -> Optional[IntelligenceEvidence]:
        """
        Query temporal patterns that affect construal.
        
        Greater psychological distance → higher construal level.
        """
        session = atom_input.request_context.session_context
        
        if session:
            # Session depth affects construal
            # Early in session → more abstract (browsing)
            # Deep in session → more concrete (deciding)
            session_depth = session.decisions_in_session
            
            if session_depth <= 1:
                level = "abstract"
                reasoning = "Early session suggests browsing/abstract mindset"
            elif session_depth >= 5:
                level = "concrete"
                reasoning = "Deep session suggests decision/concrete mindset"
            else:
                level = "moderate"
                reasoning = f"Session depth {session_depth} suggests moderate construal"
            
            confidence = min(0.7, 0.4 + session_depth * 0.05)
            
            return IntelligenceEvidence(
                source_type=IntelligenceSourceType.TEMPORAL_PATTERNS,
                construct=self.TARGET_CONSTRUCT,
                assessment=level,
                assessment_value=float(session_depth),
                confidence=confidence,
                confidence_semantics=ConfidenceSemantics.STATISTICAL,
                strength=EvidenceStrength.MODERATE,
                reasoning=reasoning,
            )
        
        return None
    
    async def _query_cognitive_load(
        self,
        atom_input: AtomInput,
    ) -> Optional[IntelligenceEvidence]:
        """
        Query cognitive load signals.
        
        High cognitive load → concrete (can't process abstract)
        Low cognitive load → can handle either
        """
        user_intel = atom_input.request_context.user_intelligence
        
        # Arousal as proxy for cognitive load
        if user_intel.current_arousal is not None:
            arousal = user_intel.current_arousal
            
            # High arousal typically means higher load → concrete
            if arousal > 0.7:
                level = "concrete"
                reasoning = f"High arousal ({arousal:.2f}) suggests concrete processing"
                confidence = 0.65
            elif arousal < 0.3:
                level = "abstract"
                reasoning = f"Low arousal ({arousal:.2f}) allows abstract processing"
                confidence = 0.55
            else:
                level = "moderate"
                reasoning = f"Moderate arousal ({arousal:.2f})"
                confidence = 0.45
            
            return IntelligenceEvidence(
                source_type=IntelligenceSourceType.NONCONSCIOUS_SIGNALS,
                construct=self.TARGET_CONSTRUCT,
                assessment=level,
                assessment_value=arousal,
                confidence=confidence,
                confidence_semantics=ConfidenceSemantics.SIGNAL_STRENGTH,
                strength=EvidenceStrength.MODERATE,
                reasoning=reasoning,
            )
        
        return None
    
    async def _build_output(
        self,
        atom_input: AtomInput,
        evidence: MultiSourceEvidence,
        fusion_result: FusionResult,
    ) -> AtomOutput:
        """Build construal level output."""
        
        level = fusion_result.assessment
        
        # Map to mechanism recommendations
        if level == "abstract":
            recommended = ["why_framing", "value_emphasis", "big_picture"]
            weights = {"why_framing": 0.8, "value_emphasis": 0.7}
        elif level == "concrete":
            recommended = ["how_framing", "feature_emphasis", "action_focus"]
            weights = {"how_framing": 0.8, "feature_emphasis": 0.7}
        else:  # moderate
            recommended = ["balanced_framing"]
            weights = {"balanced_framing": 0.6}
        
        # Calculate abstract vs concrete tendency
        if level == "abstract":
            abstract_tendency = 0.5 + fusion_result.confidence * 0.4
            concrete_tendency = 0.5 - fusion_result.confidence * 0.3
        elif level == "concrete":
            concrete_tendency = 0.5 + fusion_result.confidence * 0.4
            abstract_tendency = 0.5 - fusion_result.confidence * 0.3
        else:
            abstract_tendency = 0.5
            concrete_tendency = 0.5
        
        return AtomOutput(
            atom_id=self.config.atom_id,
            atom_type=self.ATOM_TYPE,
            request_id=atom_input.request_id,
            fusion_result=fusion_result,
            primary_assessment=level,
            secondary_assessments={
                "abstract_tendency": abstract_tendency,
                "concrete_tendency": concrete_tendency,
            },
            recommended_mechanisms=recommended,
            mechanism_weights=weights,
            inferred_states={
                "construal_abstract": abstract_tendency,
                "construal_concrete": concrete_tendency,
            },
            overall_confidence=fusion_result.confidence,
            evidence_package=evidence,
            sources_queried=len(evidence.sources_queried),
            claude_used=fusion_result.claude_used,
        )
