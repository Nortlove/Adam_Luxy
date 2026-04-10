"""
Corpus Fusion Data Models
=========================

Structured models for the five-layer fusion architecture.
Every model carries provenance (source, evidence count, confidence)
so that downstream consumers can make informed exploration/exploitation
decisions.
"""

from __future__ import annotations

import math
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, computed_field


# =============================================================================
# ENUMS
# =============================================================================

class PriorSourceType(str, Enum):
    """Origin of the intelligence."""
    CORPUS = "corpus"          # Amazon 937M review corpus
    CAMPAIGN = "campaign"      # Live campaign outcome
    FUSED = "fused"            # Bayesian fusion of corpus + campaign
    TRANSFER = "transfer"      # Cross-category psychological transfer
    HELPFUL_VOTE = "helpful_vote"  # Helpful-vote-validated


class PlatformID(str, Enum):
    """Supported partner platforms."""
    STACKADAPT = "stackadapt"
    AUDIOBOOM = "audioboom"
    IHEART = "iheart"
    AMAZON = "amazon"          # Corpus origin platform


class ConfidenceLevel(str, Enum):
    """Qualitative confidence for human-readable outputs."""
    VERY_HIGH = "very_high"    # 10k+ evidence, fused data
    HIGH = "high"              # 1k+ evidence, corpus data
    MODERATE = "moderate"      # 100+ evidence or transfer
    LOW = "low"                # <100 evidence
    SPECULATIVE = "speculative"  # Transfer with thin evidence


# =============================================================================
# LAYER 1: PRIOR EXTRACTION MODELS
# =============================================================================

class PriorConfidence(BaseModel):
    """
    Confidence metadata for a corpus prior.

    Every prior must carry its evidence weight so that Thompson
    bandits can calibrate exploration vs exploitation.
    """
    evidence_count: int = Field(0, description="Number of purchase events backing this prior")
    categories_seen: int = Field(0, description="Number of categories this pattern appears in")
    helpful_vote_weight: float = Field(
        1.0,
        description="Confidence multiplier from helpful votes (>1.0 = boosted)"
    )
    source_type: PriorSourceType = PriorSourceType.CORPUS
    confidence_level: ConfidenceLevel = ConfidenceLevel.LOW
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @computed_field
    @property
    def confidence_score(self) -> float:
        """
        Numeric confidence in [0, 1].

        Based on evidence count with helpful-vote boost.
        Formula: min(1.0, log(1 + evidence) / log(1 + 10000)) * hv_weight
        """
        if self.evidence_count <= 0:
            return 0.05
        raw = math.log(1 + self.evidence_count) / math.log(1 + 10000)
        boosted = raw * self.helpful_vote_weight
        return min(1.0, boosted)

    @computed_field
    @property
    def ci_width(self) -> float:
        """
        95% confidence interval half-width.

        Approximation based on binomial proportion CI.
        """
        if self.evidence_count <= 1:
            return 0.5
        return 1.96 / math.sqrt(self.evidence_count)


class PriorSource(BaseModel):
    """Provenance chain for a prior — traces back to raw data."""
    source_type: PriorSourceType
    category: Optional[str] = None
    archetype: Optional[str] = None
    mechanism: Optional[str] = None
    platform: Optional[PlatformID] = None
    # If this is a transfer prior, from which source category
    transfer_from_category: Optional[str] = None
    transfer_via: Optional[str] = None  # The psychological invariant used


class MechanismPriorDetail(BaseModel):
    """Effectiveness prior for a single mechanism."""
    mechanism: str
    effect_size: float = Field(
        description="Expected conversion probability or effectiveness score"
    )
    alpha: float = Field(1.0, description="Beta distribution alpha (successes)")
    beta_param: float = Field(1.0, description="Beta distribution beta (failures)")
    confidence: PriorConfidence = Field(default_factory=PriorConfidence)
    creative_implications: Optional[Dict[str, Any]] = None
    source: PriorSource = Field(default_factory=lambda: PriorSource(
        source_type=PriorSourceType.CORPUS
    ))

    @computed_field
    @property
    def ci_low(self) -> float:
        """Lower bound of 95% CI."""
        return max(0.0, self.effect_size - self.confidence.ci_width)

    @computed_field
    @property
    def ci_high(self) -> float:
        """Upper bound of 95% CI."""
        return min(1.0, self.effect_size + self.confidence.ci_width)


class CorpusPrior(BaseModel):
    """
    Complete structured prior for a query (category × profile × mechanisms).

    This is the primary output of the PriorExtractionService.
    It feeds directly into Thompson Sampling bandits as informed
    starting distributions.
    """
    category: str
    archetype: Optional[str] = None
    trait_profile: Optional[Dict[str, float]] = None

    # Ranked mechanism priors
    mechanism_priors: List[MechanismPriorDetail] = Field(default_factory=list)

    # Aggregate metadata
    total_evidence: int = 0
    dominant_mechanism: Optional[str] = None
    overall_confidence: PriorConfidence = Field(default_factory=PriorConfidence)

    # Transfer information
    is_transfer: bool = False
    transfer_source_categories: List[str] = Field(default_factory=list)
    transfer_invariant: Optional[str] = None  # e.g. "high_openness"

    # Helpful-vote boost
    helpful_vote_density: float = Field(
        0.0, description="Avg helpful votes per review in this category"
    )

    # Product-level intelligence (when ASIN/product is specified)
    product_asin: Optional[str] = Field(
        None, description="Specific ASIN this prior was resolved for"
    )
    product_mechanism_priors: Dict[str, float] = Field(
        default_factory=dict,
        description="Product-weighted mechanism priors (archetype affinity × effectiveness)"
    )
    product_ad_profile: Optional[Dict[str, str]] = Field(
        None,
        description="Product's psychological ad profile (persuasion, emotion, value, style)"
    )
    product_archetype_affinities: Optional[Dict[str, float]] = Field(
        None,
        description="Which archetypes are drawn to this specific product"
    )
    product_intelligence_source: Optional[str] = Field(
        None,
        description="'direct_product', 'similar_product_transfer', or None"
    )

    # -----------------------------------------------------------------
    # Convenience properties for consumers that expect dict-style access
    # -----------------------------------------------------------------

    @property
    def confidence(self) -> float:
        """Numeric confidence score (0-1) derived from overall_confidence."""
        _LEVEL_MAP = {
            ConfidenceLevel.VERY_HIGH: 0.95,
            ConfidenceLevel.HIGH: 0.80,
            ConfidenceLevel.MODERATE: 0.55,
            ConfidenceLevel.LOW: 0.30,
            ConfidenceLevel.SPECULATIVE: 0.15,
        }
        return _LEVEL_MAP.get(self.overall_confidence.confidence_level, 0.30)

    @property
    def transfer_sources(self) -> List[str]:
        """Alias for transfer_source_categories."""
        return self.transfer_source_categories

    @property
    def evidence_count(self) -> int:
        """Alias for total_evidence."""
        return self.total_evidence

    def get_mechanism_dict(self) -> Dict[str, float]:
        """Return mechanism priors as {mechanism: effect_size} dict."""
        return {mp.mechanism: mp.effect_size for mp in self.mechanism_priors}

    def get_mechanism_prior(self, mechanism: str) -> Optional[MechanismPriorDetail]:
        """Look up a single mechanism prior."""
        for mp in self.mechanism_priors:
            if mp.mechanism == mechanism:
                return mp
        return None

    def to_beta_distributions(self) -> Dict[str, tuple]:
        """Convert to {mechanism: (alpha, beta)} for Thompson Sampler."""
        return {
            mp.mechanism: (mp.alpha, mp.beta_param)
            for mp in self.mechanism_priors
        }

    def ranked_mechanisms(self, top_k: int = 5) -> List[MechanismPriorDetail]:
        """Return top K mechanisms ranked by effect size."""
        return sorted(
            self.mechanism_priors,
            key=lambda m: m.effect_size,
            reverse=True,
        )[:top_k]


# =============================================================================
# LAYER 2: CREATIVE PATTERN MODELS
# =============================================================================

class PersuasionFraming(BaseModel):
    """Psychological framing pattern extracted from the corpus."""
    regulatory_focus: str = Field(
        "balanced",
        description="promotion | prevention | balanced"
    )
    construal_level: str = Field(
        "mixed",
        description="abstract (why) | concrete (how) | mixed"
    )
    emotional_register: List[str] = Field(
        default_factory=list,
        description="Primary emotions (excitement, trust, fear, belonging...)"
    )
    mechanism_deployment: List[str] = Field(
        default_factory=list,
        description="Mechanisms used (social_proof, scarcity, authority...)"
    )
    implicit_drivers: List[str] = Field(
        default_factory=list,
        description="Unconscious appeals (status_signaling, identity_affirmation...)"
    )
    decision_stage: str = Field(
        "consideration",
        description="discovery | consideration | intent | conversion"
    )
    advertising_style: str = Field(
        "emotional",
        description="direct_response | brand_building | rational | emotional | comparative | aspirational"
    )


class CreativePattern(BaseModel):
    """
    A corpus-derived creative pattern with proven conversion.

    Not literal copy — structural patterns that constrain Claude's
    generation toward empirically validated approaches.
    """
    pattern_id: str
    category: str
    target_archetype: Optional[str] = None
    target_trait_profile: Optional[Dict[str, float]] = None

    framing: PersuasionFraming = Field(default_factory=PersuasionFraming)

    # Effectiveness evidence
    purchase_confirmation_rate: float = 0.0
    evidence_count: int = 0
    helpful_vote_boost: float = 1.0
    confidence: PriorConfidence = Field(default_factory=PriorConfidence)

    # Source patterns (anonymized structural patterns, not literal copy)
    language_register: str = "neutral"  # technical | casual | aspirational | authoritative
    sentence_structure: str = "varied"  # short_punchy | detailed_analytical | narrative | varied
    key_appeals: List[str] = Field(default_factory=list)  # What the copy emphasizes

    def to_claude_constraint(self) -> str:
        """Convert to a structured constraint string for Claude prompts."""
        parts = [
            f"Use {self.framing.regulatory_focus} framing",
            f"with {self.framing.construal_level} construal level.",
        ]
        if self.framing.emotional_register:
            parts.append(f"Activate emotions: {', '.join(self.framing.emotional_register[:3])}.")
        if self.framing.mechanism_deployment:
            parts.append(f"Deploy mechanisms: {', '.join(self.framing.mechanism_deployment[:3])}.")
        if self.framing.implicit_drivers:
            parts.append(f"Implicit drivers: {', '.join(self.framing.implicit_drivers[:2])}.")
        parts.append(f"Language register: {self.language_register}.")
        if self.evidence_count > 0:
            parts.append(
                f"(Backed by {self.evidence_count:,} purchase confirmations "
                f"at {self.purchase_confirmation_rate:.0%} positive rate.)"
            )
        return " ".join(parts)


class CreativeConstraints(BaseModel):
    """
    Bundle of creative constraints for a generation request.

    Output of CreativePatternExtractor; input to CopyGenerationService.
    """
    category: str
    target_profile: Optional[Dict[str, float]] = None
    platform: Optional[PlatformID] = None

    # Ranked patterns from corpus
    patterns: List[CreativePattern] = Field(default_factory=list)

    # Aggregated guidance (merged from top patterns)
    recommended_framing: Optional[PersuasionFraming] = None
    recommended_mechanisms: List[str] = Field(default_factory=list)
    recommended_emotional_register: List[str] = Field(default_factory=list)

    # Resonance templates (from helpful-vote layer)
    resonance_templates: List[str] = Field(
        default_factory=list,
        description="High-helpful-vote language patterns proven persuasive"
    )

    overall_confidence: float = 0.0

    def to_prompt_instructions(self) -> str:
        """Generate prompt instructions for Claude from all patterns."""
        if not self.patterns:
            return ""

        top = self.patterns[0]
        instructions = [
            "## Corpus-Backed Creative Constraints",
            "",
            top.to_claude_constraint(),
            "",
        ]
        if self.recommended_mechanisms:
            instructions.append(
                f"Priority mechanisms (corpus-ranked): {', '.join(self.recommended_mechanisms[:5])}"
            )
        if self.resonance_templates:
            instructions.append("")
            instructions.append("## Peer-Validated Persuasion Templates")
            instructions.append("These language patterns had high helpful-vote validation:")
            for tmpl in self.resonance_templates[:3]:
                instructions.append(f"  - \"{tmpl}\"")

        return "\n".join(instructions)


# =============================================================================
# LAYER 3: PLATFORM CALIBRATION MODELS
# =============================================================================

class PlatformCalibration(BaseModel):
    """
    Platform-specific adjustment factor on a corpus prior.

    effective_score = corpus_prior × platform_factor × recency_weight
    """
    platform: PlatformID
    mechanism: str
    category: str

    # Calibration factors
    platform_factor: float = Field(
        1.0,
        description="Multiplier on corpus prior (>1 = works better here, <1 = worse)"
    )
    recency_weight: float = Field(
        1.0,
        description="Temporal decay weight (1.0 = fully current)"
    )

    # Evidence
    campaign_observations: int = 0
    corpus_prior_value: float = 0.5
    observed_effectiveness: float = 0.5

    # Convergence
    is_stable: bool = False
    stability_iterations: int = 0

    @computed_field
    @property
    def calibrated_score(self) -> float:
        """The final calibrated effectiveness score."""
        return min(1.0, self.corpus_prior_value * self.platform_factor * self.recency_weight)

    @computed_field
    @property
    def divergence(self) -> float:
        """How much the platform differs from corpus expectation."""
        if self.corpus_prior_value == 0:
            return 0.0
        return abs(self.platform_factor - 1.0)


class PlatformCalibrationSet(BaseModel):
    """All calibrations for a platform."""
    platform: PlatformID
    calibrations: Dict[str, PlatformCalibration] = Field(
        default_factory=dict,
        description="Keyed by '{mechanism}:{category}'"
    )
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    total_observations: int = 0


# =============================================================================
# LAYER 4: BIDIRECTIONAL LEARNING MODELS
# =============================================================================

class LearningSignalSource(BaseModel):
    """Source information for a bidirectional learning signal."""
    platform: PlatformID
    campaign_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ModalityAdjustment(BaseModel):
    """
    Adjustment for modality differences (text-based corpus → audio/visual campaigns).

    When live campaigns show that a mechanism works differently on audio
    than the corpus predicted from text-based Amazon reviews, this captures
    that modality-specific calibration.
    """
    modality: str  # text | audio | video | display | native
    mechanism: str
    category: str
    corpus_effectiveness: float
    modality_effectiveness: float
    adjustment_factor: float = 1.0
    observation_count: int = 0
    confidence: float = 0.0


class ChannelAdjustment(BaseModel):
    """
    Adjustment for channel-specific dynamics.

    Amazon purchase behavior may differ from programmatic ad response
    or podcast listener behavior.
    """
    channel: str  # programmatic_display | podcast | streaming_audio | social
    mechanism: str
    category: str
    corpus_effectiveness: float
    channel_effectiveness: float
    adjustment_factor: float = 1.0
    observation_count: int = 0
    confidence: float = 0.0


class ConvergenceState(BaseModel):
    """Tracks when a fused prior becomes stable."""
    mechanism: str
    category: str
    platform: PlatformID
    prior_value: float
    posterior_value: float
    iterations: int = 0
    delta_history: List[float] = Field(default_factory=list)
    is_converged: bool = False
    convergence_threshold: float = 0.01  # Delta < 1% = converged

    def check_convergence(self) -> bool:
        """Check if the last 5 updates all had small deltas."""
        if len(self.delta_history) < 5:
            return False
        recent = self.delta_history[-5:]
        self.is_converged = all(abs(d) < self.convergence_threshold for d in recent)
        return self.is_converged


# =============================================================================
# LAYER 5: PERSUASION RESONANCE MODELS
# =============================================================================

class ResonanceTemplate(BaseModel):
    """
    A helpful-vote-validated persuasion template.

    First-class graph entity representing language/framing patterns
    that have been peer-validated through helpful votes.
    """
    template_id: str
    category: str
    archetype: str
    mechanism: str

    # The pattern (structural, not literal copy)
    pattern: str
    language_register: str = "neutral"
    framing: Optional[PersuasionFraming] = None

    # Vote evidence
    helpful_votes: int = 0
    category_avg_votes: float = 1.0
    normalized_vote_score: float = 0.0  # votes / category_avg

    # Effectiveness
    purchase_confirmation_rate: float = 0.0
    evidence_count: int = 0

    # Source
    source_type: PriorSourceType = PriorSourceType.HELPFUL_VOTE

    @computed_field
    @property
    def resonance_score(self) -> float:
        """
        Composite resonance score.

        Combines vote normalization with purchase confirmation rate.
        """
        if self.category_avg_votes <= 0:
            vote_factor = 1.0
        else:
            vote_factor = min(10.0, self.helpful_votes / max(1.0, self.category_avg_votes))
        return self.purchase_confirmation_rate * (1.0 + math.log(1 + vote_factor))

    @computed_field
    @property
    def confidence_multiplier(self) -> float:
        """
        How much this template should boost confidence on related priors.

        Helpful votes above category average = confidence boost.
        """
        if self.category_avg_votes <= 0:
            return 1.0
        ratio = self.helpful_votes / max(1.0, self.category_avg_votes)
        if ratio <= 1.0:
            return 1.0
        return 1.0 + math.log(ratio) * 0.2  # Logarithmic boost


class CategoryResonanceProfile(BaseModel):
    """Aggregated resonance data for a category × archetype."""
    category: str
    archetype: str
    templates: List[ResonanceTemplate] = Field(default_factory=list)
    dominant_mechanisms: List[str] = Field(default_factory=list)
    avg_resonance_score: float = 0.0
    total_helpful_votes: int = 0
    template_count: int = 0
