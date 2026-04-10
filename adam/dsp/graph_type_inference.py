"""
Graph Type Inference Service
============================

Queries the Neo4j graph's 1.9M+ GranularType system for mechanism recommendations.

Instead of computing NDF-similarity-weighted averages (correlational), this service
traverses the actual graph edges that encode the full expanded type system:

    1. Identify the customer's GranularType from their psychological dimensions
       (motivation, decision_style, regulatory_focus, emotional_intensity,
        cognitive_load, temporal_orientation, social_influence)
    2. Traverse SUSCEPTIBLE_TO edges to get mechanism/technique recommendations
       with alignment scores, causal chains, and empirical calibration
    3. Traverse ALIGNS_WITH_VALUE edges to find matching value propositions
    4. Traverse MATCHES_STYLE edges for linguistic style recommendations
    5. Traverse RESONATES_WITH edges for emotional appeal recommendations
    6. Apply ProductCategory moderation if a product category is available

This is the inferential backbone — each edge carries:
    - alignment_score: from the 7 alignment matrices (theoretical)
    - empirical_validation: from 937M review corpus (observed)
    - calibration_confidence: agreement between theory and evidence
    - causal basis: which psychological dimensions drive this edge
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ============================================================================
# Output Models
# ============================================================================

@dataclass
class MechanismRecommendation:
    """A recommended persuasion mechanism with inferential justification."""
    mechanism: str
    alignment_score: float
    empirical_validation: Optional[float] = None
    empirical_sample_size: Optional[int] = None
    calibration_confidence: Optional[float] = None
    causal_basis: str = ""
    source_matrix: str = ""
    category_moderation: Optional[float] = None
    # Effective score = alignment_score * (1 + category_moderation) if moderation exists
    effective_score: float = 0.0


@dataclass
class TechniqueRecommendation:
    """A recommended specific persuasion technique."""
    technique: str
    alignment_score: float
    social_basis: str = ""


@dataclass
class ValuePropositionMatch:
    """A matching value proposition for ad content."""
    value_proposition: str
    alignment_score: float
    motivation_basis: str = ""


@dataclass
class StyleRecommendation:
    """A recommended linguistic style."""
    style: str
    alignment_score: float
    decision_basis: str = ""
    cognitive_basis: str = ""


@dataclass
class EmotionalAppealMatch:
    """A matching emotional appeal."""
    appeal: str
    alignment_score: float
    regulatory_basis: str = ""


@dataclass
class TypeInferenceResult:
    """Complete result of graph-based type inference."""
    type_id: str
    type_found: bool
    dimensions: Dict[str, str] = field(default_factory=dict)

    # Ranked recommendations from graph traversal
    mechanism_recommendations: List[MechanismRecommendation] = field(default_factory=list)
    technique_recommendations: List[TechniqueRecommendation] = field(default_factory=list)
    value_propositions: List[ValuePropositionMatch] = field(default_factory=list)
    style_recommendations: List[StyleRecommendation] = field(default_factory=list)
    emotional_appeals: List[EmotionalAppealMatch] = field(default_factory=list)

    # Metadata
    category_moderation_applied: bool = False
    product_category: str = ""
    inference_method: str = "graph_type_system"

    def to_mechanism_priors(self) -> Dict[str, float]:
        """Convert mechanism recommendations to mechanism priors dict for atom compatibility."""
        priors = {}
        for rec in self.mechanism_recommendations:
            priors[rec.mechanism] = rec.effective_score or rec.alignment_score
        return priors

    def to_ad_context(self) -> Dict[str, Any]:
        """Convert to ad_context dict for atom pipeline."""
        return {
            "graph_type_inference": {
                "type_id": self.type_id,
                "type_found": self.type_found,
                "dimensions": self.dimensions,
                "inference_method": self.inference_method,
            },
            "graph_mechanism_priors": self.to_mechanism_priors(),
            "graph_value_propositions": [
                {"value": vp.value_proposition, "score": vp.alignment_score}
                for vp in self.value_propositions
            ],
            "graph_style_recommendations": [
                {"style": s.style, "score": s.alignment_score}
                for s in self.style_recommendations
            ],
            "graph_emotional_appeals": [
                {"appeal": e.appeal, "score": e.alignment_score}
                for e in self.emotional_appeals
            ],
            "graph_technique_recommendations": [
                {"technique": t.technique, "score": t.alignment_score}
                for t in self.technique_recommendations
            ],
        }


# ============================================================================
# Service
# ============================================================================

class GraphTypeInferenceService:
    """
    Queries the Neo4j type system graph for mechanism recommendations.

    Usage:
        service = GraphTypeInferenceService(neo4j_driver)
        result = service.infer(
            motivation="mastery_seeking",
            decision_style="analytical_systematic",
            regulatory_focus="eager_advancement",
            emotional_intensity="moderate_positive",
            cognitive_load="high_cognitive",
            temporal_orientation="long_term_future",
            social_influence="informational_seeker",
            product_category="Electronics",
        )
        # result.mechanism_recommendations -> ranked mechanisms with scores
        # result.to_mechanism_priors() -> {"authority": 0.9, "commitment": 0.85, ...}
    """

    def __init__(self, neo4j_driver):
        self._driver = neo4j_driver

    def infer(
        self,
        motivation: str,
        decision_style: str,
        regulatory_focus: str,
        emotional_intensity: str = "moderate_positive",
        cognitive_load: str = "moderate_cognitive",
        temporal_orientation: str = "medium_term",
        social_influence: str = "socially_aware",
        product_category: Optional[str] = None,
    ) -> TypeInferenceResult:
        """
        Query the graph for a specific GranularType and return all recommendations.

        Args:
            motivation: One of 37 motivation types
            decision_style: One of 12 decision styles
            regulatory_focus: One of 8 regulatory focus types
            emotional_intensity: One of 9 emotional intensity types
            cognitive_load: One of 3 cognitive load tolerance levels
            temporal_orientation: One of 4 temporal orientations
            social_influence: One of 5 social influence types
            product_category: Optional product category for moderation

        Returns:
            TypeInferenceResult with ranked recommendations from graph traversal
        """
        type_id = f"{motivation}|{decision_style}|{regulatory_focus}|{emotional_intensity}|{cognitive_load}|{temporal_orientation}|{social_influence}"

        dimensions = {
            "motivation": motivation,
            "decision_style": decision_style,
            "regulatory_focus": regulatory_focus,
            "emotional_intensity": emotional_intensity,
            "cognitive_load": cognitive_load,
            "temporal_orientation": temporal_orientation,
            "social_influence": social_influence,
        }

        result = TypeInferenceResult(
            type_id=type_id,
            type_found=False,
            dimensions=dimensions,
            product_category=product_category or "",
        )

        try:
            with self._driver.session() as session:
                # 1. Verify the type node exists
                exists = session.run(
                    "MATCH (t:GranularType {type_id: $type_id}) RETURN t.type_id as id",
                    type_id=type_id,
                ).single()

                if not exists:
                    logger.warning(f"GranularType not found: {type_id}")
                    result.inference_method = "type_not_found"
                    return result

                result.type_found = True

                # 2. Get mechanism recommendations (SUSCEPTIBLE_TO → PersuasionMechanism)
                result.mechanism_recommendations = self._get_mechanism_recommendations(
                    session, type_id, product_category
                )

                # 3. Get technique recommendations (SUSCEPTIBLE_TO → PersuasionTechnique)
                result.technique_recommendations = self._get_technique_recommendations(
                    session, type_id
                )

                # 4. Get value proposition matches (ALIGNS_WITH_VALUE → ValueProposition)
                result.value_propositions = self._get_value_propositions(
                    session, type_id
                )

                # 5. Get style recommendations (MATCHES_STYLE → LinguisticStyle)
                result.style_recommendations = self._get_style_recommendations(
                    session, type_id
                )

                # 6. Get emotional appeal matches (RESONATES_WITH → EmotionalAppeal)
                result.emotional_appeals = self._get_emotional_appeals(
                    session, type_id
                )

                result.category_moderation_applied = product_category is not None

        except Exception as e:
            logger.error(f"Graph type inference failed: {e}")
            result.inference_method = f"graph_error: {str(e)[:100]}"

        return result

    def _get_mechanism_recommendations(
        self, session, type_id: str, product_category: Optional[str]
    ) -> List[MechanismRecommendation]:
        """Traverse SUSCEPTIBLE_TO edges to PersuasionMechanism nodes."""
        cypher = """
        MATCH (t:GranularType {type_id: $type_id})-[r:SUSCEPTIBLE_TO]->(m:PersuasionMechanism)
        OPTIONAL MATCH (cat:ProductCategory {name: $category})-[mod:MODERATES]->(m)
        RETURN m.name as mechanism,
               r.alignment_score as alignment_score,
               r.empirical_validation as empirical_validation,
               r.empirical_sample_size as empirical_sample_size,
               r.calibration_confidence as calibration_confidence,
               r.decision_basis as decision_basis,
               r.source_matrix as source_matrix,
               mod.delta as category_delta
        ORDER BY r.alignment_score DESC
        """
        records = session.run(
            cypher, type_id=type_id, category=product_category or ""
        ).data()

        recommendations = []
        for rec in records:
            score = rec["alignment_score"] or 0.0
            delta = rec.get("category_delta")
            effective = score * (1 + delta) if delta else score

            recommendations.append(MechanismRecommendation(
                mechanism=rec["mechanism"],
                alignment_score=score,
                empirical_validation=rec.get("empirical_validation"),
                empirical_sample_size=rec.get("empirical_sample_size"),
                calibration_confidence=rec.get("calibration_confidence"),
                causal_basis=rec.get("decision_basis", ""),
                source_matrix=rec.get("source_matrix", ""),
                category_moderation=delta,
                effective_score=round(effective, 4),
            ))

        return recommendations

    def _get_technique_recommendations(
        self, session, type_id: str
    ) -> List[TechniqueRecommendation]:
        """Traverse SUSCEPTIBLE_TO edges to PersuasionTechnique nodes."""
        cypher = """
        MATCH (t:GranularType {type_id: $type_id})-[r:SUSCEPTIBLE_TO]->(pt:PersuasionTechnique)
        RETURN pt.name as technique,
               r.alignment_score as alignment_score,
               r.social_basis as social_basis
        ORDER BY r.alignment_score DESC
        """
        records = session.run(cypher, type_id=type_id).data()
        return [
            TechniqueRecommendation(
                technique=rec["technique"],
                alignment_score=rec["alignment_score"] or 0.0,
                social_basis=rec.get("social_basis", ""),
            )
            for rec in records
        ]

    def _get_value_propositions(
        self, session, type_id: str
    ) -> List[ValuePropositionMatch]:
        """Traverse ALIGNS_WITH_VALUE edges."""
        cypher = """
        MATCH (t:GranularType {type_id: $type_id})-[r:ALIGNS_WITH_VALUE]->(vp:ValueProposition)
        RETURN vp.name as value_proposition,
               r.alignment_score as alignment_score,
               r.motivation_basis as motivation_basis
        ORDER BY r.alignment_score DESC
        """
        records = session.run(cypher, type_id=type_id).data()
        return [
            ValuePropositionMatch(
                value_proposition=rec["value_proposition"],
                alignment_score=rec["alignment_score"] or 0.0,
                motivation_basis=rec.get("motivation_basis", ""),
            )
            for rec in records
        ]

    def _get_style_recommendations(
        self, session, type_id: str
    ) -> List[StyleRecommendation]:
        """Traverse MATCHES_STYLE edges."""
        cypher = """
        MATCH (t:GranularType {type_id: $type_id})-[r:MATCHES_STYLE]->(ls:LinguisticStyle)
        RETURN ls.name as style,
               r.alignment_score as alignment_score,
               r.decision_basis as decision_basis,
               r.cognitive_basis as cognitive_basis
        ORDER BY r.alignment_score DESC
        """
        records = session.run(cypher, type_id=type_id).data()
        return [
            StyleRecommendation(
                style=rec["style"],
                alignment_score=rec["alignment_score"] or 0.0,
                decision_basis=rec.get("decision_basis", ""),
                cognitive_basis=rec.get("cognitive_basis", ""),
            )
            for rec in records
        ]

    def _get_emotional_appeals(
        self, session, type_id: str
    ) -> List[EmotionalAppealMatch]:
        """Traverse RESONATES_WITH edges."""
        cypher = """
        MATCH (t:GranularType {type_id: $type_id})-[r:RESONATES_WITH]->(ea:EmotionalAppeal)
        RETURN ea.name as appeal,
               r.alignment_score as alignment_score,
               r.regulatory_basis as regulatory_basis
        ORDER BY r.alignment_score DESC
        """
        records = session.run(cypher, type_id=type_id).data()
        return [
            EmotionalAppealMatch(
                appeal=rec["appeal"],
                alignment_score=rec["alignment_score"] or 0.0,
                regulatory_basis=rec.get("regulatory_basis", ""),
            )
            for rec in records
        ]

    def infer_from_partial(
        self,
        motivation: Optional[str] = None,
        decision_style: Optional[str] = None,
        regulatory_focus: Optional[str] = None,
        product_category: Optional[str] = None,
        **kwargs,
    ) -> TypeInferenceResult:
        """
        Infer with partial dimensions — uses defaults for missing dimensions.

        Useful when only some psychological dimensions are known (e.g., from
        limited behavioral signals). Fills missing dimensions with population
        mode values.
        """
        # Population defaults (most common values)
        defaults = {
            "motivation": "quality_assurance",
            "decision_style": "satisficing",
            "regulatory_focus": "pragmatic_balanced",
            "emotional_intensity": "moderate_positive",
            "cognitive_load": "moderate_cognitive",
            "temporal_orientation": "medium_term",
            "social_influence": "socially_aware",
        }

        return self.infer(
            motivation=motivation or defaults["motivation"],
            decision_style=decision_style or defaults["decision_style"],
            regulatory_focus=regulatory_focus or defaults["regulatory_focus"],
            emotional_intensity=kwargs.get("emotional_intensity") or defaults["emotional_intensity"],
            cognitive_load=kwargs.get("cognitive_load") or defaults["cognitive_load"],
            temporal_orientation=kwargs.get("temporal_orientation") or defaults["temporal_orientation"],
            social_influence=kwargs.get("social_influence") or defaults["social_influence"],
            product_category=product_category,
        )
