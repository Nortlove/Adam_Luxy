"""Psychological transaction edge models for the three edge types."""

from __future__ import annotations

from pydantic import BaseModel, Field


class BrandBuyerEdge(BaseModel):
    """Edge Type 1: BRAND_CONVERTED.

    Connects ProductDescription (ad-side) -> AnnotatedReview (user-side).
    Carries computed match scores between brand framing and buyer psychology.
    """
    product_asin: str
    review_id: str

    # Computed match scores
    regulatory_fit_score: float = Field(0.0, ge=-1.0, le=1.0)
    construal_fit_score: float = Field(0.0, ge=0.0, le=1.0)
    personality_brand_alignment: float = Field(0.0, ge=0.0, le=1.0)
    emotional_resonance: float = Field(0.0, ge=0.0, le=1.0)
    value_alignment: float = Field(0.0, ge=0.0, le=1.0)
    evolutionary_motive_match: float = Field(0.0, ge=0.0, le=1.0)
    mechanism_effectiveness_scores: dict[str, float] = Field(default_factory=dict)

    # Outcome data
    star_rating: float = 0.0
    outcome: str = "satisfied"
    helpful_votes: int = 0
    persuasion_confidence_multiplier: float = 1.0
    annotation_tier: str = "tier_1_core"

    def to_edge_props(self) -> dict[str, object]:
        """Return properties for the Neo4j edge."""
        props = {
            "regulatory_fit_score": self.regulatory_fit_score,
            "construal_fit_score": self.construal_fit_score,
            "personality_brand_alignment": self.personality_brand_alignment,
            "emotional_resonance": self.emotional_resonance,
            "value_alignment": self.value_alignment,
            "evolutionary_motive_match": self.evolutionary_motive_match,
            "star_rating": self.star_rating,
            "outcome": self.outcome,
            "helpful_votes": self.helpful_votes,
            "persuasion_confidence_multiplier": self.persuasion_confidence_multiplier,
            "annotation_tier": self.annotation_tier,
        }
        # Store mechanism effectiveness as individual properties
        for mech, score in self.mechanism_effectiveness_scores.items():
            props[f"mech_{mech}"] = score
        return props


class PeerBuyerEdge(BaseModel):
    """Edge Type 2: PEER_INFLUENCED.

    Connects influential Review (peer-ad-side) -> subsequent buyer Review (user-side).
    """
    peer_review_id: str
    buyer_review_id: str

    influence_weight: float = Field(0.0, ge=0.0)
    peer_authenticity_resonance: float = Field(0.0, ge=0.0, le=1.0)
    risk_resolution_match: float = Field(0.0, ge=0.0, le=1.0)
    narrative_resonance: float = Field(0.0, ge=0.0, le=1.0)
    use_case_alignment: float = Field(0.0, ge=0.0, le=1.0)

    star_rating: float = 0.0
    outcome: str = "satisfied"

    def to_edge_props(self) -> dict[str, object]:
        return {
            "influence_weight": self.influence_weight,
            "peer_authenticity_resonance": self.peer_authenticity_resonance,
            "risk_resolution_match": self.risk_resolution_match,
            "narrative_resonance": self.narrative_resonance,
            "use_case_alignment": self.use_case_alignment,
            "star_rating": self.star_rating,
            "outcome": self.outcome,
        }


class EcosystemBuyerEdge(BaseModel):
    """Edge Type 3: ECOSYSTEM_CONVERTED.

    Connects ProductEcosystem -> AnnotatedReview (user-side).
    Captures the holistic persuasion environment effect at time of purchase.
    """
    product_asin: str
    review_id: str

    frame_coherence_at_time: float = Field(0.0, ge=0.0, le=1.0)
    risk_coverage_at_time: float = Field(0.0, ge=0.0, le=1.0)
    sp_density_at_time: float = Field(0.0, ge=0.0, le=1.0)
    cialdini_coverage_at_time: float = Field(0.0, ge=0.0, le=1.0)
    sp_diversity_at_time: float = Field(0.0, ge=0.0, le=1.0)
    authority_layers_at_time: float = Field(0.0, ge=0.0, le=1.0)
    persuasion_gaps_at_time: str = ""

    star_rating: float = 0.0
    outcome: str = "satisfied"

    def to_edge_props(self) -> dict[str, object]:
        return {
            "frame_coherence_at_time": self.frame_coherence_at_time,
            "risk_coverage_at_time": self.risk_coverage_at_time,
            "sp_density_at_time": self.sp_density_at_time,
            "cialdini_coverage_at_time": self.cialdini_coverage_at_time,
            "sp_diversity_at_time": self.sp_diversity_at_time,
            "authority_layers_at_time": self.authority_layers_at_time,
            "persuasion_gaps_at_time": self.persuasion_gaps_at_time,
            "star_rating": self.star_rating,
            "outcome": self.outcome,
        }
