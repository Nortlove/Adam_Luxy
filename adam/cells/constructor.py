"""Cell tuple constructor — reads substrate signals at bid time and
constructs cell IDs for cell-conditional decisioning.

All inputs are cached pre-bid:
    - archetype: from per_user_posterior_modulation pipeline (A.2)
    - posture: from posture_classifier (G1.path4)
    - conversion_stage: from journey state machine via
      to_conversion_stage(JourneyStage) at adam/user/journey/models.py:67
    - regulatory_focus: from PagePrimingSignature.regulatory_focus_priming
    - valence/arousal: from PagePrimingSignature

Bid-time latency: <2ms per call (5 cached lookups + 1 quadrant
computation + 1 dict lookup).

Calling convention for raw JourneyStage:
    Bid-time callers passing raw JourneyStage values must convert
    via the canonical mapping before calling construct_cell_id /
    get_cell_for_bid:

        from adam.user.journey.models import to_conversion_stage
        from adam.retargeting.models.enums import ConversionStage

        stage_str = to_conversion_stage(journey_stage)
        conv_stage = ConversionStage(stage_str)
        cell = get_cell_for_bid(..., conversion_stage=conv_stage, ...)

    Cells share ConversionStage with the retargeting engine since
    Enhancement #33 — both vocabularies stay synchronized as the
    journey machine evolves.
"""
from typing import Dict

from adam.cells.taxonomy import (
    CELL_TAXONOMY,
    Cell,
    RegulatoryFocus,
    ValenceArousalQuadrant,
    _POSTURE_CODES,
    _construct_cell_id,
    get_cell,
    get_parent_cell_id,
)
from adam.cold_start.models.enums import ArchetypeID
from adam.retargeting.models.enums import ConversionStage


# ---------------------------------------------------------------------------
# Quadrant boundary thresholds (canonical PAD-derived).
# ---------------------------------------------------------------------------

VALENCE_NEUTRAL_THRESHOLD: float = 0.0
AROUSAL_NEUTRAL_THRESHOLD: float = 0.5


def compute_valence_arousal_quadrant(
    valence: float,
    arousal: float,
) -> ValenceArousalQuadrant:
    """Compute valence-arousal quadrant from continuous values.

    Args:
        valence: ∈ [-1, 1] from PagePrimingSignature
        arousal: ∈ [0, 1] from PagePrimingSignature

    Returns:
        ValenceArousalQuadrant — Q1/Q2/Q3/Q4 per Mehrabian-Russell
        PAD lineage.

    Boundary semantics: values exactly at threshold (valence=0 or
    arousal=0.5) are placed in the LOW quadrant for that axis
    (canonical convention; ties broken downward).
    """
    high_valence = valence > VALENCE_NEUTRAL_THRESHOLD
    high_arousal = arousal > AROUSAL_NEUTRAL_THRESHOLD

    if high_valence and high_arousal:
        return ValenceArousalQuadrant.Q1_EXCITED
    if high_valence and not high_arousal:
        return ValenceArousalQuadrant.Q2_CONTENTED
    if not high_valence and high_arousal:
        return ValenceArousalQuadrant.Q3_ANXIOUS
    return ValenceArousalQuadrant.Q4_WITHDRAWN


def construct_cell_id(
    archetype: ArchetypeID,
    posture: str,
    conversion_stage: ConversionStage,
    regulatory_focus: RegulatoryFocus,
    valence: float,
    arousal: float,
) -> str:
    """Construct cell ID from substrate signals.

    Returns the active cell's ID if the constructed cell is active in
    CELL_TAXONOMY; otherwise returns the parent cell ID for routing
    per the empirical-density pruning rule.

    Bid-time latency: <2ms total (computation + dict lookup).
    """
    quadrant = compute_valence_arousal_quadrant(valence, arousal)
    cell_id = _construct_cell_id(
        archetype, posture, conversion_stage, regulatory_focus, quadrant,
    )
    if cell_id not in CELL_TAXONOMY:
        # Construction logic and CELL_TAXONOMY enumeration must agree;
        # this can only happen if taxonomy is modified out-of-band.
        # Fail loudly to surface the inconsistency.
        raise KeyError(
            f"Constructed cell_id {cell_id} not in CELL_TAXONOMY. "
            f"Taxonomy may be out of sync with constructor."
        )

    cell = CELL_TAXONOMY[cell_id]
    if cell.is_active:
        return cell_id
    return get_parent_cell_id(cell_id)


def get_cell_for_bid(
    archetype: ArchetypeID,
    posture: str,
    conversion_stage: ConversionStage,
    regulatory_focus: RegulatoryFocus,
    valence: float,
    arousal: float,
) -> Cell:
    """High-level bid-time accessor.

    Returns the Cell object (active or synthesized parent) for the
    given substrate signal tuple. Primary entry point for downstream
    consumers (S6.2 predicate evaluator, retargeting orchestrator,
    funnel_mpc creative selection).
    """
    cell_id = construct_cell_id(
        archetype, posture, conversion_stage, regulatory_focus,
        valence, arousal,
    )
    if cell_id in CELL_TAXONOMY:
        return get_cell(cell_id)
    return _synthesize_parent_cell(cell_id)


# Reverse map for parent-cell synthesis.
_POSTURE_CODE_TO_NAME: Dict[str, str] = {
    code: name for name, code in _POSTURE_CODES.items()
}


def _synthesize_parent_cell(parent_cell_id: str) -> Cell:
    """Resolve a parent cell ID to a synthesized Cell object.

    Parent cells don't exist in CELL_TAXONOMY — they represent the
    (archetype, posture) aggregation level used when a child cell
    is pruned for insufficient cohort population. Synthesized lazily
    with neutral defaults for the collapsed dimensions.
    """
    parts = parent_cell_id.split("_")
    if len(parts) < 3 or parts[-1] != "PARENT":
        raise ValueError(
            f"Malformed parent_cell_id: {parent_cell_id} — "
            f"expected '{{archetype}}_{{posture}}_PARENT'"
        )
    archetype_short = parts[0]
    posture_short = parts[1]

    archetype = next(
        a for a in ArchetypeID if a.value.upper() == archetype_short
    )
    posture_long = _POSTURE_CODE_TO_NAME[posture_short]

    return Cell(
        cell_id=parent_cell_id,
        archetype=archetype,
        posture=posture_long,
        conversion_stage=ConversionStage.UNAWARE,  # neutral default
        regulatory_focus=RegulatoryFocus.NEUTRAL,  # neutral default
        valence_arousal=ValenceArousalQuadrant.Q2_CONTENTED,  # neutral
        is_active=True,
    )
