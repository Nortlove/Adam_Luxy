# =============================================================================
# ADAM Spine #12 — Offline Mechanism-Discovery Pipeline (Slow Brain)
# Location: adam/intelligence/spine/spine_12_offline_discovery.py
# =============================================================================

"""Offline mechanism-discovery pipeline — Claude API as the slow brain.

PER DIRECTIVE SECTION 6.

The brain's separation of slow learning (cortex; reflective; expensive;
rare) from fast acting (subcortex; reflexive; cheap; constant) is the
right architecture for ADAM. The online pipeline is the reflex arc;
the offline pipeline is the slow-learning brain. Never confuse them
in latency budget or in persistence.

WHY THIS IS SPINE — the slow-learning brain

Per directive: "Claude is the offline reasoning engine; the online
policy is the reflex arc. The Markov-blanket separation between slow
learning (offline) and fast acting (online) is the architecture of
the brain itself, and is the right architecture here. Every mechanism,
primary metaphor, archetype, and interaction in the live system was
discovered or refined offline first. Without this pipeline, the
platform's vocabulary is frozen at the moment of pilot launch."

DECISION-TIME CONSUMERS (Rule A check)

Spine #12 itself runs OFFLINE. But its OUTPUTS are decision-time
consumed:
  - Refined hierarchical priors (Spine #3 + Spine #1) — read at
    decision time as posteriors
  - New mechanism vocabulary entries (Spine #2 mechanism class table,
    Spine #4 compatibility matrix) — read at decision time during
    eligibility filtering and trilateral scoring
  - Primary-metaphor inventory + per-metaphor compatibility scores —
    read at decision time during creative selection
  - Updated reactance-risk scores per creative — read at decision time
    as a hard-floor companion to Spine #4 fluency floor

The pipeline itself is offline; the artifacts it produces are
decision-time substrate. Justified under Rule A as "produces decision-
time inputs"; latency budget is hours-to-weeks per directive.

THIS COMMIT SHIPS

    - Pipeline cadence enums + summary Pydantic models (Daily, Weekly,
      Monthly, Quarterly per directive Section 6.2)
    - Knockoff-filter FDR control (pure-Python reference; Candès et
      al. 2018 model-X knockoffs at small N)
    - PrimaryMetaphor Pydantic + LUXY initial inventory per directive
      Section 6.3 (CONTAINMENT/CONTROL, RELIABILITY-AS-WEIGHT,
      FORWARD-MOTION/PROGRESS, STATUS-AS-VERTICALITY, TIME-AS-RESOURCE)
    - ReactanceRiskScore Pydantic + independent reactance scorer per
      directive Section 6.5 (a SECOND architectural defense alongside
      Spine #4 fluency floor)
    - ProposedMechanism Pydantic + propose/critique/promote pipeline
      scaffolding (M6 critic REPURPOSED here from serving path —
      directive Section 8.1)
    - BrandIntelligenceLibrary scaffolding + LUXY-specific seed
      (per directive Section 6.3)

THIS COMMIT DOES NOT SHIP (follow-on commits)

    - Actual Claude API integration (Anthropic client wired; offline
      pipeline calls happen via existing claude_summarizer/argument
      generation infrastructure)
    - Cron / Airflow scheduling of cadences (operational; production
      deploy task)
    - Bayesian Causal Forest with horseshoe priors (research-grade
      heterogeneous-effects modeling; runs in weekly cadence; lib
      installation pending)

REFERENCES

    Bai 2022 — Constitutional AI: Harmlessness from AI Feedback.
    Liu 2023 — G-Eval: NLG Evaluation using GPT-4.
    Min 2023 — FActScore: Fine-grained Atomic Evaluation of Factual
        Precision in Long Form Text Generation.
    Barber & Candès 2015 — knockoff filter.
    Candès, Fan, Janson, Lv 2018 — model-X knockoffs.
    Conceptual metaphor theory: Lakoff & Johnson; Grady on primary
        metaphors. Chris's own doctoral work on cross-linguistic
        primary-metaphor universals.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field, field_validator

logger = logging.getLogger(__name__)


# =============================================================================
# Pipeline cadences (per directive Section 6.2)
# =============================================================================


class PipelineCadence(str, Enum):
    """The four cadences per directive Section 6.2."""

    DAILY = "daily"        # ingest prior 24h decision traces; hypothesis generation
    WEEKLY = "weekly"      # BCF re-fit; transferability re-fit; HMC reconcile
    MONTHLY = "monthly"    # full corpus-level mechanism re-discovery
    QUARTERLY = "quarterly"  # full hierarchical-prior reconciliation


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


# =============================================================================
# Summary models per cadence
# =============================================================================


class DailyDecisionSummary(BaseModel):
    """Output of the daily cadence: stratified-sample summary of the
    prior 24h decision traces.

    Per directive Section 6.2: "stratified-sample summary (which
    mechanisms underperformed vs. which overperformed, in which
    contexts, for which cohorts). Claude API runs hypothesis
    generation: 'given these underperformance patterns, what
    mechanism refinements should we propose?'"
    """

    model_config = ConfigDict(extra="forbid")

    summary_date: datetime = Field(default_factory=_now_utc)
    n_decisions: int
    n_outcomes_observed: int

    # Per-mechanism performance (templated; not free-form)
    mechanism_performance: Dict[str, Dict[str, float]] = Field(default_factory=dict)
    # Format: mechanism_name → {ctr, conv_rate, avg_reward, n}

    # Cohort-conditional patterns
    cohort_mechanism_performance: Dict[str, Dict[str, Dict[str, float]]] = Field(
        default_factory=dict,
    )
    # Format: cohort_id → mechanism → {ctr, ...}

    # Underperformance flags (mechanisms below cohort baseline)
    underperformance_alerts: List[str] = Field(default_factory=list)

    # Candidate refinements (TEMPLATED tags, not free-form prose)
    candidate_refinement_tags: List[str] = Field(default_factory=list)


# =============================================================================
# Knockoff-filter FDR control (per directive Section 6.2)
# =============================================================================


@dataclass(frozen=True)
class KnockoffSelection:
    """Result of a knockoff-filter FDR selection.

    Per directive: "use the model-X knockoff filter (Candès et al.
    2018). Robust at small N, doesn't require asymptotic
    approximations, controls FDR at user-specified level."
    """

    selected_features: List[str]
    fdr_target: float
    threshold: float
    n_features_considered: int
    n_features_selected: int


def knockoff_filter_select(
    feature_z_statistics: Dict[str, float],
    feature_knockoff_z_statistics: Dict[str, float],
    *,
    fdr_target: float = 0.1,
) -> KnockoffSelection:
    """Apply the knockoff-filter procedure to select non-zero features.

    Per Candès et al. 2018 — the model-X knockoff filter:
        1. For each feature j, compute a statistic W_j = |z_j| - |z̃_j|
           where z_j is the test statistic from the original feature
           and z̃_j is the same from the knockoff
        2. Sort |W_j| in decreasing order
        3. Find the largest threshold T such that
           {#{j : W_j ≤ -T} + 1} / max(1, #{j : W_j ≥ T}) ≤ fdr_target
        4. Select features with W_j ≥ T

    For positive W_j, the original feature has stronger signal than its
    knockoff — evidence for non-zero effect.

    Args:
        feature_z_statistics: dict of feature_name → z_statistic
        feature_knockoff_z_statistics: same shape; knockoff z for each
        fdr_target: FDR control level (default 0.1)

    Returns KnockoffSelection.
    """
    if not 0.0 < fdr_target < 1.0:
        raise ValueError(f"fdr_target must be in (0, 1); got {fdr_target}")

    if set(feature_z_statistics.keys()) != set(feature_knockoff_z_statistics.keys()):
        raise ValueError(
            "feature_z_statistics and feature_knockoff_z_statistics must "
            "have the same set of keys"
        )

    n_features = len(feature_z_statistics)
    if n_features == 0:
        return KnockoffSelection(
            selected_features=[], fdr_target=fdr_target,
            threshold=float("inf"),
            n_features_considered=0, n_features_selected=0,
        )

    # Compute W_j = |z_j| - |z̃_j|
    W: Dict[str, float] = {
        feat: abs(feature_z_statistics[feat])
              - abs(feature_knockoff_z_statistics[feat])
        for feat in feature_z_statistics
    }

    # Sort |W_j| in decreasing order; iterate thresholds
    abs_W_values = sorted(set(abs(w) for w in W.values()), reverse=True)
    chosen_threshold = float("inf")  # default: select nothing
    selected: List[str] = []

    for T in abs_W_values:
        # #{j : W_j ≥ T} (positive evidence)
        n_pos = sum(1 for w in W.values() if w >= T)
        # #{j : W_j ≤ -T} (negative evidence — proxy for false positives)
        n_neg = sum(1 for w in W.values() if w <= -T)
        # FDR estimate
        fdr_estimate = (n_neg + 1) / max(1, n_pos)
        if fdr_estimate <= fdr_target and n_pos > 0:
            chosen_threshold = T
            selected = [feat for feat, w in W.items() if w >= T]
            break

    return KnockoffSelection(
        selected_features=selected,
        fdr_target=fdr_target,
        threshold=chosen_threshold,
        n_features_considered=n_features,
        n_features_selected=len(selected),
    )


# =============================================================================
# Primary-metaphor inventory (per directive Section 6.3 + 6.4)
# =============================================================================


class PrimaryMetaphor(BaseModel):
    """A primary metaphor in Chris's primary-metaphor framework.

    Per directive Section 6.3: "For LUXY: encode CONTAINMENT/CONTROL,
    RELIABILITY-AS-WEIGHT, FORWARD-MOTION/PROGRESS, STATUS-AS-
    VERTICALITY, TIME-AS-RESOURCE as the active inventory."

    Per Chris's doctoral work on cross-linguistic primary-metaphor
    universals (Grady) + physical-to-social neural recycling.
    """

    model_config = ConfigDict(extra="forbid")

    name: str
    source_domain: str       # the physical/perceptual source (e.g., "physical containment")
    target_domain: str       # the abstract target (e.g., "control / safety")
    canonical_lexicon: List[str] = Field(default_factory=list)  # surface-form keywords
    description: str = ""    # Chris-authored or human-curated; NOT LLM-composed


# Per directive Section 6.3 — LUXY initial inventory.
# Pilot-pending; offline pipeline expands from corpus.
LUXY_INITIAL_PRIMARY_METAPHORS: Tuple[PrimaryMetaphor, ...] = (
    PrimaryMetaphor(
        name="containment_control",
        source_domain="physical_containment",
        target_domain="control_safety",
        canonical_lexicon=[
            "secure", "private", "enclosed", "contained", "your space",
            "in control", "managed", "controlled environment",
        ],
        description=(
            "CONTAINMENT/CONTROL: physical containment (a vehicle, a room) "
            "maps onto psychological safety + control"
        ),
    ),
    PrimaryMetaphor(
        name="reliability_as_weight",
        source_domain="physical_weight",
        target_domain="dependability",
        canonical_lexicon=[
            "solid", "weighty", "substantial", "anchored", "grounded",
            "dependable", "rock-solid", "trusted",
        ],
        description=(
            "RELIABILITY-AS-WEIGHT: physical weight maps onto reliability + "
            "dependability"
        ),
    ),
    PrimaryMetaphor(
        name="forward_motion_progress",
        source_domain="forward_movement",
        target_domain="progress_advancement",
        canonical_lexicon=[
            "moving forward", "ahead of schedule", "smooth progress",
            "advancing", "on the way", "in motion", "momentum",
        ],
        description=(
            "FORWARD-MOTION/PROGRESS: physical forward movement maps onto "
            "task / goal completion"
        ),
    ),
    PrimaryMetaphor(
        name="status_as_verticality",
        source_domain="vertical_position",
        target_domain="social_status",
        canonical_lexicon=[
            "elevated", "premier", "above", "rise", "high-end", "top-tier",
            "executive level", "uplifted",
        ],
        description=(
            "STATUS-AS-VERTICALITY: vertical position maps onto social "
            "status and standing"
        ),
    ),
    PrimaryMetaphor(
        name="time_as_resource",
        source_domain="resource_economy",
        target_domain="time",
        canonical_lexicon=[
            "save time", "spend time", "time well-used", "investment of time",
            "time-rich", "efficient with time",
        ],
        description=(
            "TIME-AS-RESOURCE: time treated as a finite economy resource "
            "(spendable, savable)"
        ),
    ),
)


def luxy_initial_metaphor_inventory() -> Dict[str, PrimaryMetaphor]:
    """Return the LUXY initial primary-metaphor inventory keyed by name."""
    return {m.name: m for m in LUXY_INITIAL_PRIMARY_METAPHORS}


# =============================================================================
# Reactance-risk scorer (per directive Section 6.5)
# =============================================================================


# Per directive Section 6.5:
# "Persuasion-intensity / explicitness markers ('only,' 'must,' 'limited
# time,' 'act now,' urgency cues). Pressure-language density. Override-
# of-user-control cues (countdown timers, scarcity claims, social-proof
# manipulation)."

REACTANCE_PRESSURE_PHRASES: Tuple[str, ...] = (
    "limited time", "act now", "must", "you must", "you have to",
    "don't miss", "last chance", "expires today", "expires soon",
    "only \\d+ left", "only a few", "while supplies last",
    "before it's gone", "running out", "selling fast",
)

REACTANCE_OVERRIDE_PHRASES: Tuple[str, ...] = (
    "countdown", "timer", "ticking", "tick-tock",
    "everyone's buying", "everyone is signing up",
    "you'd be foolish", "smart people", "not to miss",
)

REACTANCE_EXPLICITNESS_PHRASES: Tuple[str, ...] = (
    "compelling", "irresistible", "unbeatable", "unmissable",
    "stand out", "break through", "attention-grabbing", "eye-catching",
)


@dataclass(frozen=True)
class ReactanceRiskScore:
    """Reactance-risk score for a creative.

    Per directive Section 6.5: "Above a threshold reactance score, the
    creative is rejected at offline-pipeline time and never enters the
    live candidate pool. This is a SECOND architectural defense
    (alongside the fluency floor) of the attention-inversion principle."

    Foundation §7 rule 11 protected at the offline pipeline as well as
    the decision-time fluency floor.
    """

    creative_text: str
    pressure_density: float           # phrases per 100 words
    override_density: float
    explicitness_density: float
    total_score: float                # weighted composite
    rejected: bool                    # true iff total_score > threshold
    matched_phrases: List[str] = field(default_factory=list)


def score_reactance_risk(
    creative_text: str,
    *,
    rejection_threshold: float = 0.05,
) -> ReactanceRiskScore:
    """Score the reactance risk of a creative text.

    Per directive Section 6.5. Pure pattern-matching reference (no
    LLM call). Counts phrases per 100 words; total score is weighted
    composite.

    Above rejection_threshold: creative rejected at offline pipeline;
    never enters live candidate pool.
    """
    import re

    text = creative_text.lower()
    word_count = max(1, len(creative_text.split()))
    per_100 = 100.0 / word_count

    matched: List[str] = []

    def _count_phrases(phrases: Tuple[str, ...]) -> Tuple[int, List[str]]:
        n = 0
        seen: List[str] = []
        for phrase in phrases:
            # Use regex search for phrases that contain regex tokens
            pattern = phrase if "\\d" in phrase else re.escape(phrase)
            try:
                count = len(re.findall(pattern, text))
            except re.error:
                count = text.count(phrase)
            if count > 0:
                n += count
                seen.append(phrase)
        return n, seen

    n_pressure, p_seen = _count_phrases(REACTANCE_PRESSURE_PHRASES)
    n_override, o_seen = _count_phrases(REACTANCE_OVERRIDE_PHRASES)
    n_explicit, e_seen = _count_phrases(REACTANCE_EXPLICITNESS_PHRASES)

    matched.extend(p_seen)
    matched.extend(o_seen)
    matched.extend(e_seen)

    pressure_density = n_pressure * per_100 / 100.0   # 0..1 normalized
    override_density = n_override * per_100 / 100.0
    explicitness_density = n_explicit * per_100 / 100.0

    # Weighted composite: override-of-control weighted highest (most
    # reactance-inducing per Brehm reactance theory).
    total = (
        0.4 * pressure_density
        + 0.4 * override_density
        + 0.2 * explicitness_density
    )

    return ReactanceRiskScore(
        creative_text=creative_text,
        pressure_density=pressure_density,
        override_density=override_density,
        explicitness_density=explicitness_density,
        total_score=total,
        rejected=total > rejection_threshold,
        matched_phrases=sorted(set(matched)),
    )


# =============================================================================
# Proposed mechanism + critique-promote pipeline (M6 repurposed)
# =============================================================================


class ProposalStatus(str, Enum):
    """Lifecycle of a proposed mechanism."""

    PROPOSED = "proposed"             # Claude API generated the proposal
    CRITIQUED = "critiqued"           # M6 cross-family critic reviewed
    KNOCKOFF_FILTERED = "knockoff_filtered"   # FDR filter passed
    HUMAN_APPROVED = "human_approved"
    HUMAN_REJECTED = "human_rejected"
    PROMOTED = "promoted"              # Active in live system
    DEPRECATED = "deprecated"


class ProposedMechanism(BaseModel):
    """A new mechanism proposed by the offline pipeline.

    Per directive Section 6.2 monthly cadence: "Claude API runs over a
    sampled slice of the Amazon review corpus (stratified by category)
    and proposes new mechanism atoms, new construct interactions, new
    primary metaphors. Knockoff filter applied. Constitutional-AI
    critic (M6, repurposed): Opus critiques Sonnet's proposals against
    corpus evidence and existing taxonomy."

    Note: M6 critic moved from serving path (cut per directive Section
    8.1) to offline pipeline here (where it is genuinely useful).
    """

    model_config = ConfigDict(extra="forbid")

    proposal_id: str
    proposed_mechanism_name: str
    proposed_class: str  # e.g., "state_prime", "construal_shift", "trait_aligned"
    rationale_tag: str   # categorical reason; NOT free-form
    status: ProposalStatus = ProposalStatus.PROPOSED

    # Critic evaluation (M6 cross-family critic OUTPUT)
    critic_findings_count: int = 0
    critic_overall_disposition: Optional[str] = None  # APPROVE / REVISE / REJECT

    # Knockoff filter result
    knockoff_filter_passed: bool = False

    # Source data
    source_corpus_evidence_size: int = 0

    proposed_at: datetime = Field(default_factory=_now_utc)


# =============================================================================
# Brand Intelligence Library scaffolding
# =============================================================================


class BrandIntelligenceLibrary(BaseModel):
    """Per-brand intelligence library — primary metaphor inventory,
    archetype inventory, goal-state inventory, etc.

    Per directive Section 6.3 — LUXY specification: ingests LUXY
    website / blog / press / social / agency creative inventory /
    competitor positioning / customer testimonials / TMC integration
    docs. Outputs primary-metaphor inventory + brand-side construct
    annotation + archetype inventory + goal-state inventory.
    """

    model_config = ConfigDict(extra="forbid")

    brand_id: str
    brand_name: str

    primary_metaphor_inventory: Dict[str, PrimaryMetaphor] = Field(default_factory=dict)

    # Archetype inventory per directive Section 6.3
    target_archetypes: List[str] = Field(default_factory=list)
    suppress_archetypes: List[str] = Field(default_factory=list)

    # Goal-state inventory (decision-time consumed by Spine #5 free-energy)
    goal_state_inventory: List[str] = Field(default_factory=list)

    # 27-dim brand-side construct annotation
    brand_construct_annotation: Dict[str, float] = Field(default_factory=dict)

    last_corpus_ingestion_at: Optional[datetime] = None


def make_luxy_brand_intelligence_seed() -> BrandIntelligenceLibrary:
    """Initial LUXY BrandIntelligenceLibrary seed per directive
    Section 6.3.

    Initial values; offline pipeline refines from corpus ingestion.
    """
    return BrandIntelligenceLibrary(
        brand_id="luxy",
        brand_name="LUXY",
        primary_metaphor_inventory=luxy_initial_metaphor_inventory(),
        target_archetypes=["status_seeker", "careful_truster", "easy_decider"],
        suppress_archetypes=["skeptical_analyst", "disillusioned"],
        goal_state_inventory=[
            "commute_readiness", "expense_management", "trip_planning",
            "professional_encounter_prep", "anxiety_reduction",
            "status_display", "time_pressure",
        ],
    )


__all__ = [
    "BrandIntelligenceLibrary",
    "DailyDecisionSummary",
    "KnockoffSelection",
    "LUXY_INITIAL_PRIMARY_METAPHORS",
    "PipelineCadence",
    "PrimaryMetaphor",
    "ProposalStatus",
    "ProposedMechanism",
    "REACTANCE_EXPLICITNESS_PHRASES",
    "REACTANCE_OVERRIDE_PHRASES",
    "REACTANCE_PRESSURE_PHRASES",
    "ReactanceRiskScore",
    "knockoff_filter_select",
    "luxy_initial_metaphor_inventory",
    "make_luxy_brand_intelligence_seed",
    "score_reactance_risk",
]
