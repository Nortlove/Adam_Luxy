"""Ad-side annotation model for product descriptions (Domains 29-33)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class FramingScores(BaseModel):
    gain: float = Field(0.0, ge=0.0, le=1.0)
    loss: float = Field(0.0, ge=0.0, le=1.0)
    hedonic: float = Field(0.0, ge=0.0, le=1.0)
    utilitarian: float = Field(0.0, ge=0.0, le=1.0)


class AppealScores(BaseModel):
    rational: float = Field(0.0, ge=0.0, le=1.0)
    emotional: float = Field(0.0, ge=0.0, le=1.0)
    fear: float = Field(0.0, ge=0.0, le=1.0)
    narrative: float = Field(0.0, ge=0.0, le=1.0)
    comparative: float = Field(0.0, ge=0.0, le=1.0)


class ProcessingTargets(BaseModel):
    construal_level: float = Field(0.5, ge=0.0, le=1.0)
    processing_route: float = Field(0.5, ge=0.0, le=1.0)


class PersuasionTechniques(BaseModel):
    social_proof: float = Field(0.0, ge=0.0, le=1.0)
    scarcity: float = Field(0.0, ge=0.0, le=1.0)
    authority: float = Field(0.0, ge=0.0, le=1.0)
    reciprocity: float = Field(0.0, ge=0.0, le=1.0)
    commitment: float = Field(0.0, ge=0.0, le=1.0)
    liking: float = Field(0.0, ge=0.0, le=1.0)
    anchoring: float = Field(0.0, ge=0.0, le=1.0)
    storytelling: float = Field(0.0, ge=0.0, le=1.0)


class ValuePropositions(BaseModel):
    performance: float = Field(0.0, ge=0.0, le=1.0)
    convenience: float = Field(0.0, ge=0.0, le=1.0)
    reliability: float = Field(0.0, ge=0.0, le=1.0)
    cost: float = Field(0.0, ge=0.0, le=1.0)
    pleasure: float = Field(0.0, ge=0.0, le=1.0)
    peace_of_mind: float = Field(0.0, ge=0.0, le=1.0)
    self_expression: float = Field(0.0, ge=0.0, le=1.0)
    transformation: float = Field(0.0, ge=0.0, le=1.0)
    status: float = Field(0.0, ge=0.0, le=1.0)
    belonging: float = Field(0.0, ge=0.0, le=1.0)
    social_responsibility: float = Field(0.0, ge=0.0, le=1.0)
    novelty: float = Field(0.0, ge=0.0, le=1.0)
    knowledge: float = Field(0.0, ge=0.0, le=1.0)


class BrandPersonality(BaseModel):
    sincerity: float = Field(0.0, ge=0.0, le=1.0)
    excitement: float = Field(0.0, ge=0.0, le=1.0)
    competence: float = Field(0.0, ge=0.0, le=1.0)
    sophistication: float = Field(0.0, ge=0.0, le=1.0)
    ruggedness: float = Field(0.0, ge=0.0, le=1.0)
    authenticity: float = Field(0.0, ge=0.0, le=1.0)
    warmth: float = Field(0.0, ge=0.0, le=1.0)


class LinguisticStyle(BaseModel):
    formality: float = Field(0.5, ge=0.0, le=1.0)
    complexity: float = Field(0.5, ge=0.0, le=1.0)
    emotional_tone: float = Field(0.0, ge=-1.0, le=1.0)
    directness: float = Field(0.5, ge=0.0, le=1.0)


class EvolutionaryTargets(BaseModel):
    self_protection: float = Field(0.0, ge=0.0, le=1.0)
    affiliation: float = Field(0.0, ge=0.0, le=1.0)
    status: float = Field(0.0, ge=0.0, le=1.0)
    mate_acquisition: float = Field(0.0, ge=0.0, le=1.0)
    kin_care: float = Field(0.0, ge=0.0, le=1.0)
    disease_avoidance: float = Field(0.0, ge=0.0, le=1.0)


class ImplicitTargets(BaseModel):
    fluency: float = Field(0.0, ge=0.0, le=1.0)
    embodied_cognition: float = Field(0.0, ge=0.0, le=1.0)
    psychological_ownership: float = Field(0.0, ge=0.0, le=1.0)
    nonconscious_goal: float = Field(0.0, ge=0.0, le=1.0)


class AttachmentPositioning(BaseModel):
    warmth: float = Field(0.5, ge=0.0, le=1.0)
    reassurance: float = Field(0.5, ge=0.0, le=1.0)


class AgencyFraming(BaseModel):
    locus: float = Field(0.5, ge=0.0, le=1.0)


class BrandTrustSignals(BaseModel):
    credibility_cues: float = Field(0.0, ge=0.0, le=1.0)
    transparency: float = Field(0.0, ge=0.0, le=1.0)
    familiarity_leverage: float = Field(0.0, ge=0.0, le=1.0)


class AdSideAnnotation(BaseModel):
    """Full ad-side annotation for a product description.

    Covers Domains 29-33 from the construct taxonomy plus evolutionary
    and implicit targeting.
    """
    asin: str
    annotation_confidence: float = Field(0.0, ge=0.0, le=1.0)
    annotation_tier: str = "tier_1_core"

    framing: FramingScores = Field(default_factory=FramingScores)
    appeals: AppealScores = Field(default_factory=AppealScores)
    processing_targets: ProcessingTargets = Field(default_factory=ProcessingTargets)
    persuasion_techniques: PersuasionTechniques = Field(default_factory=PersuasionTechniques)
    value_propositions: ValuePropositions = Field(default_factory=ValuePropositions)
    brand_personality: BrandPersonality = Field(default_factory=BrandPersonality)
    linguistic_style: LinguisticStyle = Field(default_factory=LinguisticStyle)
    evolutionary_targets: EvolutionaryTargets = Field(default_factory=EvolutionaryTargets)
    implicit_targets: ImplicitTargets = Field(default_factory=ImplicitTargets)
    attachment_positioning: AttachmentPositioning = Field(default_factory=AttachmentPositioning)
    agency_framing: AgencyFraming = Field(default_factory=AgencyFraming)
    emotional_specificity: float = Field(0.5, ge=0.0, le=1.0)
    mental_simulation_vividness: float = Field(0.0, ge=0.0, le=1.0)
    social_visibility: float = Field(0.0, ge=0.0, le=1.0)
    brand_trust_signals: BrandTrustSignals = Field(default_factory=BrandTrustSignals)
    reactance_triggers: float = Field(0.0, ge=0.0, le=1.0)
    anchor_deployment: float = Field(0.0, ge=0.0, le=1.0)
    contamination_risk_framing: float = Field(0.0, ge=0.0, le=1.0)

    def to_flat_dict(self) -> dict[str, float]:
        """Flatten all scores into a single dict for Neo4j properties."""
        flat: dict[str, float] = {"annotation_confidence": self.annotation_confidence}
        for section_name in [
            "framing", "appeals", "processing_targets", "persuasion_techniques",
            "value_propositions", "brand_personality", "linguistic_style",
            "evolutionary_targets", "implicit_targets",
            "attachment_positioning", "agency_framing", "brand_trust_signals",
        ]:
            section = getattr(self, section_name)
            for k, v in section.model_dump().items():
                flat[f"ad_{section_name}_{k}"] = v
        flat["ad_emotional_specificity"] = self.emotional_specificity
        flat["ad_mental_simulation_vividness"] = self.mental_simulation_vividness
        flat["ad_social_visibility"] = self.social_visibility
        flat["ad_reactance_triggers"] = self.reactance_triggers
        flat["ad_anchor_deployment"] = self.anchor_deployment
        flat["ad_contamination_risk_framing"] = self.contamination_risk_framing
        return flat
