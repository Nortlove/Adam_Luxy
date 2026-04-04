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
        Proper CLT assessment using four psychological distances
        (Trope & Liberman, 2010).

        Each distance dimension pushes toward abstract (high distance)
        or concrete (low distance):

        1. Temporal distance: How far is the purchase/action?
           - Session depth, funnel stage, temporal_discounting edge dim
        2. Social distance: How similar is the buyer to the brand's audience?
           - Archetype confidence, personality_alignment edge dim
        3. Spatial distance: How relevant is the product to the buyer?
           - Category match, brand_relationship_depth edge dim
        4. Hypothetical distance: How likely is the purchase?
           - Conversion probability, decision_entropy edge dim

        When bilateral edge dimensions are available (from prefetch),
        they override the heuristic proxies.
        """
        session = atom_input.request_context.session_context
        user_intel = atom_input.request_context.user_intelligence
        ad_context = atom_input.ad_context or {}
        edge_dims = ad_context.get("edge_dimensions", {})

        distances = []  # List of (distance_value 0-1, confidence, name)

        # --- 1. TEMPORAL DISTANCE ---
        # Low distance (concrete) when deep in session / near purchase
        temporal_dist = 0.5  # default moderate
        temporal_conf = 0.3
        if edge_dims.get("temporal_discounting") is not None:
            # Edge-derived: high temporal_discounting = present-focused = low distance
            temporal_dist = 1.0 - edge_dims["temporal_discounting"]
            temporal_conf = 0.7
        elif session:
            depth = session.decisions_in_session
            # Deeper session → closer to action → lower distance
            temporal_dist = max(0.0, 1.0 - depth * 0.15)
            temporal_conf = min(0.5, 0.3 + depth * 0.04)
        distances.append((temporal_dist, temporal_conf, "temporal"))

        # --- 2. SOCIAL DISTANCE ---
        # Low distance when buyer closely matches brand's audience
        social_dist = 0.5
        social_conf = 0.3
        if edge_dims.get("personality_alignment") is not None:
            # High personality alignment = low social distance
            social_dist = 1.0 - edge_dims["personality_alignment"]
            social_conf = 0.7
        elif user_intel.archetype_match:
            # Archetype confidence as proxy for social closeness
            social_dist = 1.0 - user_intel.archetype_match.confidence
            social_conf = 0.4
        distances.append((social_dist, social_conf, "social"))

        # --- 3. SPATIAL DISTANCE (product relevance) ---
        spatial_dist = 0.5
        spatial_conf = 0.3
        if edge_dims.get("brand_relationship_depth") is not None:
            # Deep brand relationship = low spatial distance
            spatial_dist = 1.0 - edge_dims["brand_relationship_depth"]
            spatial_conf = 0.7
        elif edge_dims.get("value_alignment") is not None:
            spatial_dist = 1.0 - edge_dims["value_alignment"]
            spatial_conf = 0.6
        distances.append((spatial_dist, spatial_conf, "spatial"))

        # --- 4. HYPOTHETICAL DISTANCE ---
        # Low distance when purchase is likely
        hypothetical_dist = 0.5
        hypothetical_conf = 0.3
        if edge_dims.get("decision_entropy") is not None:
            # High entropy = undecided = high hypothetical distance
            hypothetical_dist = edge_dims["decision_entropy"]
            hypothetical_conf = 0.6
        distances.append((hypothetical_dist, hypothetical_conf, "hypothetical"))

        # --- COMPOSITE ---
        # Confidence-weighted average of all 4 distances
        total_weight = sum(c for _, c, _ in distances)
        if total_weight > 0:
            composite_distance = sum(d * c for d, c, _ in distances) / total_weight
        else:
            composite_distance = 0.5

        # Higher distance → more abstract
        if composite_distance > 0.6:
            level = "abstract"
        elif composite_distance < 0.4:
            level = "concrete"
        else:
            level = "moderate"

        overall_conf = min(0.85, total_weight / 2.0)  # Scales with evidence count

        distance_details = {n: round(d, 3) for d, _, n in distances}
        has_edges = any(edge_dims.get(k) is not None for k in [
            "temporal_discounting", "personality_alignment",
            "brand_relationship_depth", "decision_entropy",
        ])

        reasoning = (
            f"CLT 4-distance: {distance_details} → composite={composite_distance:.2f} → {level}"
            f"{' (edge-backed)' if has_edges else ' (heuristic proxies)'}"
        )

        return IntelligenceEvidence(
            source_type=IntelligenceSourceType.TEMPORAL_PATTERNS,
            construct=self.TARGET_CONSTRUCT,
            assessment=level,
            assessment_value=composite_distance,
            confidence=overall_conf,
            confidence_semantics=ConfidenceSemantics.STATISTICAL,
            strength=EvidenceStrength.STRONG if has_edges else EvidenceStrength.MODERATE,
            reasoning=reasoning,
            metadata={
                "distances": distance_details,
                "composite_distance": composite_distance,
                "edge_backed": has_edges,
            },
        )
    
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
