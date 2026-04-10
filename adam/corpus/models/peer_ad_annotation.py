"""Peer-ad-side annotation model for reviews (Domains 29-33 + Domain 34)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class RiskResolution(BaseModel):
    financial: float = Field(0.0, ge=0.0, le=1.0)
    performance: float = Field(0.0, ge=0.0, le=1.0)
    social: float = Field(0.0, ge=0.0, le=1.0)
    durability: float = Field(0.0, ge=0.0, le=1.0)


class PeerAdSideAnnotation(BaseModel):
    """Peer-ad-side annotation for a review.

    Scores the review AS PERSUASION CONTENT for future readers.
    Covers Domains 29-33 (standard ad-side) + Domain 34 (peer persuasion).
    """
    review_id: str
    annotation_confidence: float = Field(0.0, ge=0.0, le=1.0)

    # Domain 34: Peer Persuasion Constructs
    testimonial_authenticity: float = Field(0.0, ge=0.0, le=1.0)
    relatable_vulnerability: float = Field(0.0, ge=0.0, le=1.0)
    outcome_specificity: float = Field(0.0, ge=0.0, le=1.0)
    outcome_timeline: float = Field(0.0, ge=0.0, le=1.0)
    before_after_narrative: float = Field(0.0, ge=0.0, le=1.0)

    risk_resolution: RiskResolution = Field(default_factory=RiskResolution)

    use_case_matching: float = Field(0.0, ge=0.0, le=1.0)
    social_proof_amplification: float = Field(0.0, ge=0.0, le=1.0)
    objection_preemption: float = Field(0.0, ge=0.0, le=1.0)
    domain_expertise_signals: float = Field(0.0, ge=0.0, le=1.0)
    comparative_depth: float = Field(0.0, ge=0.0, le=1.0)
    emotional_contagion_potency: float = Field(0.0, ge=0.0, le=1.0)
    narrative_arc_completeness: float = Field(0.0, ge=0.0, le=1.0)
    resolved_anxiety_narrative: float = Field(0.0, ge=0.0, le=1.0)
    recommendation_strength: float = Field(0.0, ge=0.0, le=1.0)
    mental_simulation_enablement: float = Field(0.0, ge=0.0, le=1.0)
    negative_diagnosticity: float = Field(0.0, ge=0.0, le=1.0)

    def to_flat_dict(self) -> dict[str, float]:
        """Flatten for Neo4j properties with peer_ad_ prefix."""
        flat: dict[str, float] = {
            "peer_ad_annotation_confidence": self.annotation_confidence,
            "peer_ad_testimonial_authenticity": self.testimonial_authenticity,
            "peer_ad_relatable_vulnerability": self.relatable_vulnerability,
            "peer_ad_outcome_specificity": self.outcome_specificity,
            "peer_ad_outcome_timeline": self.outcome_timeline,
            "peer_ad_before_after_narrative": self.before_after_narrative,
            "peer_ad_use_case_matching": self.use_case_matching,
            "peer_ad_social_proof_amplification": self.social_proof_amplification,
            "peer_ad_objection_preemption": self.objection_preemption,
            "peer_ad_domain_expertise_signals": self.domain_expertise_signals,
            "peer_ad_comparative_depth": self.comparative_depth,
            "peer_ad_emotional_contagion_potency": self.emotional_contagion_potency,
            "peer_ad_narrative_arc_completeness": self.narrative_arc_completeness,
            "peer_ad_resolved_anxiety_narrative": self.resolved_anxiety_narrative,
            "peer_ad_recommendation_strength": self.recommendation_strength,
            "peer_ad_mental_simulation_enablement": self.mental_simulation_enablement,
            "peer_ad_negative_diagnosticity": self.negative_diagnosticity,
        }
        for k, v in self.risk_resolution.model_dump().items():
            flat[f"peer_ad_risk_resolution_{k}"] = v
        return flat
