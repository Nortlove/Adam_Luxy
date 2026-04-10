"""User-side annotation model for reviews (Domains 1-22)."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class PersonalityScores(BaseModel):
    openness: float = Field(0.5, ge=0.0, le=1.0)
    conscientiousness: float = Field(0.5, ge=0.0, le=1.0)
    extraversion: float = Field(0.5, ge=0.0, le=1.0)
    agreeableness: float = Field(0.5, ge=0.0, le=1.0)
    neuroticism: float = Field(0.5, ge=0.0, le=1.0)
    confidence_openness: float = Field(0.0, ge=0.0, le=1.0)
    confidence_conscientiousness: float = Field(0.0, ge=0.0, le=1.0)
    confidence_extraversion: float = Field(0.0, ge=0.0, le=1.0)
    confidence_agreeableness: float = Field(0.0, ge=0.0, le=1.0)
    confidence_neuroticism: float = Field(0.0, ge=0.0, le=1.0)


class RegulatoryFocus(BaseModel):
    promotion: float = Field(0.5, ge=0.0, le=1.0)
    prevention: float = Field(0.5, ge=0.0, le=1.0)


class DecisionStyle(BaseModel):
    maximizer: float = Field(0.5, ge=0.0, le=1.0)
    impulse: float = Field(0.0, ge=0.0, le=1.0)
    information_search_depth: float = Field(0.5, ge=0.0, le=1.0)


class EvolutionaryMotives(BaseModel):
    self_protection: float = Field(0.0, ge=0.0, le=1.0)
    affiliation: float = Field(0.0, ge=0.0, le=1.0)
    status: float = Field(0.0, ge=0.0, le=1.0)
    mate_acquisition: float = Field(0.0, ge=0.0, le=1.0)
    kin_care: float = Field(0.0, ge=0.0, le=1.0)
    disease_avoidance: float = Field(0.0, ge=0.0, le=1.0)


class MechanismsCited(BaseModel):
    social_proof: float = Field(0.0, ge=0.0, le=1.0)
    authority: float = Field(0.0, ge=0.0, le=1.0)
    scarcity: float = Field(0.0, ge=0.0, le=1.0)
    reciprocity: float = Field(0.0, ge=0.0, le=1.0)
    commitment: float = Field(0.0, ge=0.0, le=1.0)
    liking: float = Field(0.0, ge=0.0, le=1.0)


class EmotionScores(BaseModel):
    pleasure: float = Field(0.0, ge=-1.0, le=1.0)
    arousal: float = Field(0.5, ge=0.0, le=1.0)
    dominance: float = Field(0.5, ge=0.0, le=1.0)
    primary_emotions: list[str] = Field(default_factory=list)


class ImplicitDrivers(BaseModel):
    compensatory: float = Field(0.0, ge=0.0, le=1.0)
    identity_signaling: float = Field(0.0, ge=0.0, le=1.0)
    wanting_over_liking: float = Field(0.0, ge=0.0, le=1.0)


class LayTheories(BaseModel):
    price_quality: float = Field(0.0, ge=0.0, le=1.0)
    natural_goodness: float = Field(0.0, ge=0.0, le=1.0)
    effort_quality: float = Field(0.0, ge=0.0, le=1.0)
    scarcity_value: float = Field(0.0, ge=0.0, le=1.0)


class AttachmentStyle(BaseModel):
    anxiety: float = Field(0.5, ge=0.0, le=1.0)
    avoidance: float = Field(0.5, ge=0.0, le=1.0)


class UserLinguisticStyle(BaseModel):
    formality: float = Field(0.5, ge=0.0, le=1.0)
    complexity: float = Field(0.5, ge=0.0, le=1.0)
    emotional_expressiveness: float = Field(0.5, ge=0.0, le=1.0)
    directness: float = Field(0.5, ge=0.0, le=1.0)


class UniquenessNeed(BaseModel):
    creative_choice: float = Field(0.0, ge=0.0, le=1.0)
    unpopular_choice: float = Field(0.0, ge=0.0, le=1.0)
    avoidance_of_similarity: float = Field(0.0, ge=0.0, le=1.0)


class BrandTrust(BaseModel):
    known_brand_trust: float = Field(0.5, ge=0.0, le=1.0)
    unknown_brand_skepticism: float = Field(0.5, ge=0.0, le=1.0)
    review_reliance: float = Field(0.5, ge=0.0, le=1.0)


class UserSideAnnotation(BaseModel):
    """Full user-side annotation for a review.

    Covers Domains 1-22 from the construct taxonomy.
    Reveals the reviewer's psychological profile as expressed
    through their natural language.
    """
    review_id: str
    annotation_confidence: float = Field(0.0, ge=0.0, le=1.0)
    annotation_tier: str = "tier_1_core"

    personality: PersonalityScores = Field(default_factory=PersonalityScores)
    regulatory_focus: RegulatoryFocus = Field(default_factory=RegulatoryFocus)
    decision_style: DecisionStyle = Field(default_factory=DecisionStyle)
    construal_level: float = Field(0.5, ge=0.0, le=1.0)
    need_for_cognition: float = Field(0.5, ge=0.0, le=1.0)
    evolutionary_motives: EvolutionaryMotives = Field(default_factory=EvolutionaryMotives)
    mechanisms_cited: MechanismsCited = Field(default_factory=MechanismsCited)
    emotion: EmotionScores = Field(default_factory=EmotionScores)
    stated_purchase_reason: str = ""
    implicit_drivers: ImplicitDrivers = Field(default_factory=ImplicitDrivers)
    lay_theories: LayTheories = Field(default_factory=LayTheories)
    attachment_style: AttachmentStyle = Field(default_factory=AttachmentStyle)
    locus_of_control: float = Field(0.5, ge=0.0, le=1.0)
    emotional_granularity: float = Field(0.5, ge=0.0, le=1.0)
    linguistic_style: UserLinguisticStyle = Field(default_factory=UserLinguisticStyle)
    uniqueness_need: UniquenessNeed = Field(default_factory=UniquenessNeed)
    purchase_involvement: float = Field(0.5, ge=0.0, le=1.0)
    anticipated_regret: float = Field(0.0, ge=0.0, le=1.0)
    negativity_seeking: float = Field(0.0, ge=0.0, le=1.0)
    negativity_bias: float = Field(0.0, ge=0.0, le=1.0)
    reactance: float = Field(0.0, ge=0.0, le=1.0)
    optimal_distinctiveness: float = Field(0.0, ge=0.0, le=1.0)
    brand_trust: BrandTrust = Field(default_factory=BrandTrust)
    self_monitoring: float = Field(0.0, ge=0.0, le=1.0)
    spending_pain_sensitivity: float = Field(0.0, ge=0.0, le=1.0)
    disgust_sensitivity: float = Field(0.0, ge=0.0, le=1.0)
    anchor_susceptibility: float = Field(0.0, ge=0.0, le=1.0)
    mental_ownership_strength: float = Field(0.0, ge=0.0, le=1.0)
    conversion_outcome: str = "satisfied"

    def to_flat_dict(self) -> dict[str, object]:
        """Flatten all scores into a single dict for Neo4j properties."""
        flat: dict[str, object] = {
            "annotation_confidence": self.annotation_confidence,
            "annotation_tier": self.annotation_tier,
            "user_construal_level": self.construal_level,
            "user_need_for_cognition": self.need_for_cognition,
            "user_stated_purchase_reason": self.stated_purchase_reason,
            "user_conversion_outcome": self.conversion_outcome,
            "user_locus_of_control": self.locus_of_control,
            "user_emotional_granularity": self.emotional_granularity,
        }
        flat["user_purchase_involvement"] = self.purchase_involvement
        flat["user_anticipated_regret"] = self.anticipated_regret
        flat["user_negativity_seeking"] = self.negativity_seeking
        flat["user_negativity_bias"] = self.negativity_bias
        flat["user_reactance"] = self.reactance
        flat["user_optimal_distinctiveness"] = self.optimal_distinctiveness
        flat["user_self_monitoring"] = self.self_monitoring
        flat["user_spending_pain_sensitivity"] = self.spending_pain_sensitivity
        flat["user_disgust_sensitivity"] = self.disgust_sensitivity
        flat["user_anchor_susceptibility"] = self.anchor_susceptibility
        flat["user_mental_ownership_strength"] = self.mental_ownership_strength
        for section_name in [
            "personality", "regulatory_focus", "decision_style",
            "evolutionary_motives", "mechanisms_cited", "emotion",
            "implicit_drivers", "lay_theories", "attachment_style",
            "linguistic_style", "uniqueness_need", "brand_trust",
        ]:
            section = getattr(self, section_name)
            for k, v in section.model_dump().items():
                if isinstance(v, list):
                    flat[f"user_{section_name}_{k}"] = v
                else:
                    flat[f"user_{section_name}_{k}"] = v
        return flat
