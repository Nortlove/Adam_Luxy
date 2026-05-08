"""S6.1 Cell Taxonomy — bid-time decision cell space.

F.1 / S6.1 (1 of 2 — substrate-side enumeration + tuple constructor).
F.2 ships cohort detection logic populating E's deferred
compensatory_consumption_pattern flag.
"""

from adam.cells.constructor import (
    AROUSAL_NEUTRAL_THRESHOLD,
    VALENCE_NEUTRAL_THRESHOLD,
    compute_valence_arousal_quadrant,
    construct_cell_id,
    get_cell_for_bid,
)
from adam.cells.taxonomy import (
    CELL_TAXONOMY,
    EXPECTED_CELL_COUNT,
    Cell,
    RegulatoryFocus,
    ValenceArousalQuadrant,
    get_active_cells,
    get_active_parent_cell_count,
    get_cell,
    get_parent_cell_id,
)

__all__ = [
    "AROUSAL_NEUTRAL_THRESHOLD",
    "CELL_TAXONOMY",
    "Cell",
    "EXPECTED_CELL_COUNT",
    "RegulatoryFocus",
    "VALENCE_NEUTRAL_THRESHOLD",
    "ValenceArousalQuadrant",
    "compute_valence_arousal_quadrant",
    "construct_cell_id",
    "get_active_cells",
    "get_active_parent_cell_count",
    "get_cell",
    "get_cell_for_bid",
    "get_parent_cell_id",
]
