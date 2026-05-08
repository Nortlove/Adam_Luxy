"""S6.2 Cell features schema — input bundle the predicate evaluator
consumes.

Aggregated from B/C/D/E/F.2 substrate at bid time by
CellFeaturesAggregator (adam/cells/aggregator.py). Predicates evaluate
against this bundle to determine cell-conditional creative selection.

Schema is a frozen dataclass for fast construction + immutability +
hashability. Values are pre-fetched at bid time; the dataclass is the
snapshot.

Per Q18=orthogonal (pre-flight Pass C): the canonical 5-class posture
(FIVE_CLASS_POSTURES) and the cascade's 4-class attentional posture
(`{blend_compatible, vigilance_activating, neutral, unknown}` from
adam/intelligence/page_attentional_posture_substrate.py:categorize_posture)
are SEPARATE features. The 5-class describes WHAT cognitive activity
the page elicits; the 4-class describes HOW the page recruits attention
(blend vs vigilance allocation). Both axes inform predicates
independently.
"""
from dataclasses import dataclass, field
from typing import Dict, FrozenSet, Optional

from adam.cells.taxonomy import (
    ConversionStage,
    RegulatoryFocus,
    ValenceArousalQuadrant,
)
from adam.cold_start.models.enums import ArchetypeID


@dataclass(frozen=True)
class CellFeatureSet:
    """Snapshot of all cell-relevant features at bid time.

    Frozen dataclass — predicates must not mutate features (treat as
    a read-only view of decision-time substrate state).
    """

    # ── Cell tuple axes (5 axes that define the cell_id) ────────────
    cell_id: str
    archetype: ArchetypeID
    posture: str  # 5-class canonical from FIVE_CLASS_POSTURES
    journey: ConversionStage
    regulatory_focus: RegulatoryFocus
    valence_arousal: ValenceArousalQuadrant

    # ── Page-priming raw signals (B substrate) ──────────────────────
    valence: float = 0.0                          # ∈ [-1, 1]
    arousal: float = 0.5                          # ∈ [0, 1]
    cognitive_load_estimate: float = 0.5          # ∈ [0, 1]
    persuasion_knowledge_activation: float = 0.0  # ∈ [0, 1]
    confidence_persuasion_knowledge: float = 0.5  # ∈ [0, 1]
    activated_frames: FrozenSet[str] = field(default_factory=frozenset)

    # ── Mindstate composites (C + D) ────────────────────────────────
    fomo_score: float = 0.0                       # ∈ [0, 1]
    psych_ownership_proxy: float = 0.0            # ∈ [0, 1]
    depletion_proxy: float = 0.0                  # ∈ [0, 1]
    session_position_seconds: float = 0.0
    browsing_momentum: float = 0.5                # ∈ [0, 1]

    # ── Cohort-level substrate (E + F.2) ────────────────────────────
    compensatory_consumption_pattern: bool = False
    compensatory_detection_confidence: float = 0.5
    cohort_mechanism_priors: Dict[str, float] = field(default_factory=dict)

    # ── Trait-side substrate (A.2 maximizer Beta posterior) ─────────
    maximizer_tendency_posterior_mean: float = 0.5
    """Per-user maximizer_tendency Beta posterior mean. Cold-start
    users carry the archetype prior posterior; returning users have
    bid-evidence-updated posteriors."""
    maximizer_tendency_posterior_strength: float = 10.0
    """α + β for the Beta posterior. Strength=10 = cold-start;
    higher = more bid evidence accumulated."""

    # ── Cascade orthogonal axis (Q18=orthogonal per Pass C) ─────────
    cascade_attentional_posture: Optional[str] = None
    """One of {blend_compatible, vigilance_activating, neutral,
    unknown} from
    adam/intelligence/page_attentional_posture_substrate.py.
    None when not provided. Orthogonal to the 5-class `posture` axis
    above — both inform predicates independently."""

    # ── Diagnostic / debugging ──────────────────────────────────────
    aggregated_at: Optional[str] = None
    """ISO8601 timestamp when this feature set was aggregated.
    None disables timing instrumentation."""
