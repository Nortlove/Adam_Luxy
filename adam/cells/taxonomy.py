"""S6.1 Cell Taxonomy — static enumeration of the bid-time decision
cell space.

Per directive §3 S6: cells defined as tuples of
(trait_archetype × posture × conversion_stage × regulatory_focus ×
valence_arousal_quadrant).

Cardinality per Q15=(β) adjudication:
    8 × 5 × 6 × 3 × 4 = 2,880 cells

ConversionStage (6) is used in place of the spec's original
"4 canonical journey states" — it is the canonical retargeting
journey vocabulary since Enhancement #33 (mapped from JourneyStage's
13 values via to_conversion_stage at adam/user/journey/models.py:67).
Cells reuse this vocabulary to prevent parallel-collapsing drift.
Heckhausen-Gollwitzer (1987) Rubicon-phase theoretical lineage is
cited but NOT re-implemented as a separate enum.

Cell axes are STATIC. New substrate signals (B's
persuasion_knowledge_activation, C+D's mindstate composites
fomo_score / psych_ownership_proxy / depletion_proxy, E's cohort
compensatory_consumption_pattern) are FEATURES-ON-CELLS consumed by
S6.2's predicate evaluator (forthcoming), NOT cell axes. Inflating
the tuple space with feature axes would push it to 311,040+ cells
which fails the practicality bar.

Empirical-density pruning marks active vs inactive cells based on
cohort-discovery population data; pruning is offline, evaluation is
bid-time. Pruned cells route to a parent cell during bid-time
evaluation (parent = same archetype + posture, ignoring
journey/regfocus/quadrant; 8 × 5 = 40 distinct parent cells).

References:
    Heckhausen, H., & Gollwitzer, P. M. (1987). Thought contents and
        cognitive functioning in motivational versus volitional states
        of mind. Motivation and Emotion 11(2), 101-120. (Theoretical
        lineage for journey-stage cell-conditioning generally.)
    Mehrabian, A., & Russell, J. A. (1974). An approach to environmental
        psychology. (PAD framework underlying ValenceArousalQuadrant.)
    Higgins, E. T. (1997). Beyond pleasure and pain. American
        Psychologist 52(12), 1280-1300. (Regulatory focus.)
    Enhancement #33 — adam/retargeting/models/enums.py:21 ConversionStage
        canonical 6-stage mapping in the retargeting engine; cells share
        this vocabulary.
"""
from dataclasses import dataclass
from enum import Enum
from typing import Dict, FrozenSet, Tuple

from adam.cold_start.models.enums import ArchetypeID
from adam.intelligence.posture_five_class import FIVE_CLASS_POSTURES
from adam.retargeting.models.enums import ConversionStage


# ---------------------------------------------------------------------------
# Cell axis enums local to S6 (regulatory_focus + quadrant)
# ---------------------------------------------------------------------------

class RegulatoryFocus(str, Enum):
    """Regulatory focus axis — three values from
    PagePrimingSignature.regulatory_focus_priming (B / S6-prep.2)."""
    PROMOTION = "promotion"
    PREVENTION = "prevention"
    NEUTRAL = "neutral"


class ValenceArousalQuadrant(str, Enum):
    """Mehrabian-Russell PAD-derived 4-quadrant decomposition of the
    valence × arousal plane.

    Boundary semantics (canonical, ties broken downward):
        valence > 0     → high-valence; valence ≤ 0 → low-valence
        arousal > 0.5   → high-arousal; arousal ≤ 0.5 → low-arousal
    """
    Q1_EXCITED = "excited"        # high-V + high-A
    Q2_CONTENTED = "contented"    # high-V + low-A
    Q3_ANXIOUS = "anxious"        # low-V + high-A
    Q4_WITHDRAWN = "withdrawn"    # low-V + low-A


# ---------------------------------------------------------------------------
# Cell dataclass
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Cell:
    """A single bid-time decision cell.

    Attributes:
        cell_id: Compact human-readable cell identifier per the
            "{archetype}_{posture}_{stage}_{regfocus}_{quadrant}"
            format.
        archetype: One of 8 ArchetypeID values.
        posture: One of 5 FIVE_CLASS_POSTURES strings.
        conversion_stage: One of 6 ConversionStage values.
        regulatory_focus: One of 3 RegulatoryFocus values.
        valence_arousal: One of 4 ValenceArousalQuadrant values.
        is_active: True for cells with sufficient cohort-empirical
            population to warrant separate treatment. False for cells
            pruned due to insufficient population. Default True;
            pruning runs offline based on cohort-discovery data and
            updates this flag. Pruned cells route to a parent cell
            during bid-time evaluation (parent = same archetype +
            posture, ignoring stage/regfocus/quadrant).
    """
    cell_id: str
    archetype: ArchetypeID
    posture: str
    conversion_stage: ConversionStage
    regulatory_focus: RegulatoryFocus
    valence_arousal: ValenceArousalQuadrant
    is_active: bool = True


# ---------------------------------------------------------------------------
# Short-code maps for cell ID construction
# ---------------------------------------------------------------------------

# Posture short codes (2-letter):
_POSTURE_CODES: Dict[str, str] = {
    "INFORMATION_FORAGING": "IF",
    "TASK_COMPLETION": "TC",
    "LEISURE_BROWSING": "LB",
    "SOCIAL_CONSUMPTION": "SC",
    "TRANSACTIONAL_COMPARISON": "TX",
}

# ConversionStage short codes (3-letter):
_STAGE_CODES: Dict[ConversionStage, str] = {
    ConversionStage.UNAWARE: "UNA",
    ConversionStage.CURIOUS: "CUR",
    ConversionStage.EVALUATING: "EVA",
    ConversionStage.INTENDING: "INT",
    ConversionStage.STALLED: "STA",
    ConversionStage.CONVERTED: "CON",
}

# Regulatory focus short codes (4-letter):
_REGFOCUS_CODES: Dict[RegulatoryFocus, str] = {
    RegulatoryFocus.PROMOTION: "PROM",
    RegulatoryFocus.PREVENTION: "PREV",
    RegulatoryFocus.NEUTRAL: "NEUT",
}

# Quadrant short codes (2-letter):
_QUADRANT_CODES: Dict[ValenceArousalQuadrant, str] = {
    ValenceArousalQuadrant.Q1_EXCITED: "Q1",
    ValenceArousalQuadrant.Q2_CONTENTED: "Q2",
    ValenceArousalQuadrant.Q3_ANXIOUS: "Q3",
    ValenceArousalQuadrant.Q4_WITHDRAWN: "Q4",
}


def _construct_cell_id(
    archetype: ArchetypeID,
    posture: str,
    conversion_stage: ConversionStage,
    regulatory_focus: RegulatoryFocus,
    quadrant: ValenceArousalQuadrant,
) -> str:
    """Construct human-readable cell ID per the canonical format:

        "{archetype_short}_{posture_short}_{stage_short}_{regfocus_short}_{quadrant_short}"

    Example: ArchetypeID.ANALYST + TASK_COMPLETION + ConversionStage.INTENDING
             + RegulatoryFocus.PROMOTION + Q1_EXCITED
             → "ANALYST_TC_INT_PROM_Q1"
    """
    archetype_short = archetype.value.upper()
    posture_short = _POSTURE_CODES[posture]
    stage_short = _STAGE_CODES[conversion_stage]
    reg_short = _REGFOCUS_CODES[regulatory_focus]
    quadrant_short = _QUADRANT_CODES[quadrant]
    return (
        f"{archetype_short}_{posture_short}_{stage_short}_"
        f"{reg_short}_{quadrant_short}"
    )


# ---------------------------------------------------------------------------
# Static taxonomy enumeration (8 × 5 × 6 × 3 × 4 = 2,880 cells)
# ---------------------------------------------------------------------------

EXPECTED_CELL_COUNT: int = 2880  # 8 × 5 × 6 × 3 × 4

EXPECTED_PARENT_CELL_COUNT: int = 40  # 8 archetypes × 5 postures


def _build_cell_taxonomy() -> Dict[str, Cell]:
    cells: Dict[str, Cell] = {}
    for archetype in ArchetypeID:
        for posture in FIVE_CLASS_POSTURES:
            for stage in ConversionStage:
                for reg in RegulatoryFocus:
                    for quadrant in ValenceArousalQuadrant:
                        cell_id = _construct_cell_id(
                            archetype, posture, stage, reg, quadrant,
                        )
                        cells[cell_id] = Cell(
                            cell_id=cell_id,
                            archetype=archetype,
                            posture=posture,
                            conversion_stage=stage,
                            regulatory_focus=reg,
                            valence_arousal=quadrant,
                            is_active=True,
                        )
    return cells


CELL_TAXONOMY: Dict[str, Cell] = _build_cell_taxonomy()


# ---------------------------------------------------------------------------
# Public accessors
# ---------------------------------------------------------------------------

def get_cell(cell_id: str) -> Cell:
    """Retrieve a cell by ID. Raises KeyError if not found."""
    return CELL_TAXONOMY[cell_id]


def get_active_cells() -> FrozenSet[str]:
    """Return frozen set of active cell IDs."""
    return frozenset(
        cell_id for cell_id, cell in CELL_TAXONOMY.items()
        if cell.is_active
    )


def get_parent_cell_id(cell_id: str) -> str:
    """Compute parent cell ID for empirically-pruned cells.

    Parent = same archetype + posture, with stage/regfocus/quadrant
    collapsed. Used at bid time to route from pruned (is_active=False)
    cells to their populated parents.

    Parent format: "{archetype_short}_{posture_short}_PARENT"
    """
    parts = cell_id.split("_")
    if len(parts) < 5:
        raise ValueError(f"Malformed cell_id: {cell_id}")
    return f"{parts[0]}_{parts[1]}_PARENT"


def get_active_parent_cell_count() -> int:
    """Number of distinct (archetype, posture) parent cells.
    Always 8 × 5 = 40 unless explicitly modified."""
    return EXPECTED_PARENT_CELL_COUNT
