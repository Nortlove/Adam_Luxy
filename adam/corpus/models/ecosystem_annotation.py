"""Product ecosystem annotation model (Domain 35)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class EcosystemAnnotation(BaseModel):
    """Domain 35 annotation — one per product (ASIN).

    Captures the composite persuasion environment formed by the
    product description + all its reviews together.
    """
    asin: str

    # Ecosystem Coherence
    frame_coherence: float = Field(0.0, ge=0.0, le=1.0)
    claim_validation_ratio: float = Field(0.0, ge=0.0, le=1.0)
    frame_extension: float = Field(0.0, ge=0.0, le=1.0)

    # Risk & Objection Coverage
    risk_coverage_completeness: float = Field(0.0, ge=0.0, le=1.0)
    objection_coverage_depth: float = Field(0.0, ge=0.0, le=1.0)

    # Social Proof Structure
    social_proof_density: float = Field(0.0, ge=0.0, le=1.0)
    social_proof_diversity: float = Field(0.0, ge=0.0, le=1.0)
    authority_layering: float = Field(0.0, ge=0.0, le=1.0)

    # Persuasion Completeness
    cialdini_coverage: float = Field(0.0, ge=0.0, le=1.0)
    persuasion_gap_analysis: str = ""

    # Temporal Structure
    temporal_persuasion_arc: float = Field(0.0, ge=0.0, le=1.0)
    negative_review_resolution_quality: float = Field(0.0, ge=0.0, le=1.0)

    # Aggregate stats
    review_count: int = 0
    avg_rating: float = 0.0
    verified_purchase_ratio: float = 0.0
    helpful_vote_concentration: float = Field(0.0, ge=0.0, le=1.0)

    def to_flat_dict(self) -> dict[str, object]:
        """Flatten for Neo4j properties."""
        return {
            "eco_frame_coherence": self.frame_coherence,
            "eco_claim_validation_ratio": self.claim_validation_ratio,
            "eco_frame_extension": self.frame_extension,
            "eco_risk_coverage": self.risk_coverage_completeness,
            "eco_objection_coverage": self.objection_coverage_depth,
            "eco_sp_density": self.social_proof_density,
            "eco_sp_diversity": self.social_proof_diversity,
            "eco_authority_layers": self.authority_layering,
            "eco_cialdini_coverage": self.cialdini_coverage,
            "eco_persuasion_gaps": self.persuasion_gap_analysis,
            "eco_temporal_arc": self.temporal_persuasion_arc,
            "eco_neg_review_resolution": self.negative_review_resolution_quality,
            "eco_review_count": self.review_count,
            "eco_avg_rating": self.avg_rating,
            "eco_verified_ratio": self.verified_purchase_ratio,
            "eco_helpful_concentration": self.helpful_vote_concentration,
        }
