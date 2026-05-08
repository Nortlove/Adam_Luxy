"""S6 Cell Taxonomy + cell-conditional decisioning surface.

F.1 / S6.1 (1 of 2 — substrate-side enumeration + tuple constructor).
F.2 ships cohort detection logic populating E's deferred
compensatory_consumption_pattern flag.
S6.2 ships the consumer side: aggregator + predicate evaluator +
Path A integration in run_bilateral_cascade.
"""

from adam.cells.aggregator import (
    CellFeaturesAggregator,
    default_aggregator,
    production_aggregator,
)
from adam.cells.constructor import (
    AROUSAL_NEUTRAL_THRESHOLD,
    VALENCE_NEUTRAL_THRESHOLD,
    compute_valence_arousal_quadrant,
    construct_cell_id,
    get_cell_for_bid,
)
from adam.cells.evaluator import (
    CombinedModulation,
    CreativeModulation,
    apply_cell_modulation,
    cell_predicate,
    evaluate_predicates,
    get_registered_predicates,
)
from adam.cells.features import CellFeatureSet
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

# Trigger seed predicate registration at package import time.
from adam.cells import predicates  # noqa: F401, E402

__all__ = [
    "AROUSAL_NEUTRAL_THRESHOLD",
    "CELL_TAXONOMY",
    "Cell",
    "CellFeatureSet",
    "CellFeaturesAggregator",
    "CombinedModulation",
    "CreativeModulation",
    "EXPECTED_CELL_COUNT",
    "RegulatoryFocus",
    "VALENCE_NEUTRAL_THRESHOLD",
    "ValenceArousalQuadrant",
    "apply_cell_modulation",
    "cell_predicate",
    "compute_valence_arousal_quadrant",
    "construct_cell_id",
    "default_aggregator",
    "production_aggregator",
    "evaluate_predicates",
    "get_active_cells",
    "get_active_parent_cell_count",
    "get_cell",
    "get_cell_for_bid",
    "get_parent_cell_id",
    "get_registered_predicates",
]
