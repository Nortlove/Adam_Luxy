"""S6.2 — Path A integration smoke tests.

The full bilateral_cascade end-to-end is not callable in unit tests
without Neo4j + Redis + StackAdapt fixture. These tests pin the
integration BLOCK as inserted: the imports resolve, the fail-soft
template wraps the call, the modulation flows through
apply_cell_modulation, and the existing posture × mechanism
modulation block remains untouched.
"""
import inspect

import pytest

from adam.cells import (
    apply_cell_modulation,
    default_aggregator,
    evaluate_predicates,
)
from adam.cells.evaluator import CombinedModulation


class TestIntegrationBlockInsertion:
    """Pin that the S6.2 integration block exists in
    bilateral_cascade.py at the expected location with the expected
    fail-soft template."""

    def _cascade_source(self):
        from adam.api.stackadapt import bilateral_cascade
        return inspect.getsource(bilateral_cascade)

    def test_s62_integration_block_present(self):
        src = self._cascade_source()
        assert "S6.2 CELL-CONDITIONAL CREATIVE-SELECTION MODULATION" in src

    def test_imports_default_aggregator_evaluate_apply(self):
        src = self._cascade_source()
        # Lazy imports inside the try block.
        assert "from adam.cells import (" in src
        assert "apply_cell_modulation" in src
        assert "default_aggregator" in src
        assert "evaluate_predicates" in src

    def test_fail_soft_try_except_template(self):
        src = self._cascade_source()
        # Same fail-soft pattern as posture × mechanism modulation.
        assert "Cell-conditional modulation skipped:" in src

    def test_neutral_modulation_does_not_modify_mechanism_scores(self):
        src = self._cascade_source()
        # Pin the is_neutral guard — neutral modulation must skip
        # the apply step.
        assert "is_neutral" in src

    def test_inserted_after_posture_modulation_block(self):
        """Pin ordering: S6.2 sits between posture × mechanism
        modulation and the hard fluency floor. Boosts apply to the
        posture-modulated baseline; floor still drops LOW
        compatibility mechanisms even after S6.2 boosted them."""
        src = self._cascade_source()
        idx_posture = src.index("Posture × mechanism modulation skipped")
        idx_s62 = src.index("S6.2 CELL-CONDITIONAL CREATIVE-SELECTION MODULATION")
        idx_floor = src.index("HARD FLUENCY FLOOR")
        assert idx_posture < idx_s62 < idx_floor


class TestEndToEndDefaultAggregator:
    """Aggregate via the default_aggregator and run evaluator —
    pin that the round-trip works without Neo4j/Redis/cascade
    machinery."""

    def test_default_aggregator_to_evaluator_to_apply_round_trip(self):
        agg = default_aggregator()
        features = agg.aggregate(buyer_id="u1", url_hash="h1")
        modulation = evaluate_predicates(features)
        # With all-default substrate, no seed predicate fires —
        # neutral modulation expected.
        assert isinstance(modulation, CombinedModulation)
        assert modulation.is_neutral

        # apply_cell_modulation on neutral modulation returns input
        # mechanism_scores unchanged.
        ms = {"social_proof": 0.7, "scarcity": 0.5}
        result = apply_cell_modulation(ms, modulation)
        assert result == ms

    def test_real_data_path_high_fomo_promotion_fires(self):
        """When substrate is non-default (high FOMO + promotion focus),
        the high_fomo_promotion seed predicate fires and modulation
        boosts scarcity."""
        from adam.cells import CellFeatureSet
        from adam.cells.taxonomy import (
            ConversionStage, RegulatoryFocus, ValenceArousalQuadrant,
        )
        from adam.cold_start.models.enums import ArchetypeID

        features = CellFeatureSet(
            cell_id="ANALYST_TC_INT_PROM_Q1",
            archetype=ArchetypeID.ANALYST,
            posture="TASK_COMPLETION",
            journey=ConversionStage.INTENDING,
            regulatory_focus=RegulatoryFocus.PROMOTION,
            valence_arousal=ValenceArousalQuadrant.Q1_EXCITED,
            fomo_score=0.85,  # triggers high_fomo_promotion
        )
        modulation = evaluate_predicates(features)
        assert "high_fomo_promotion" in modulation.fired_predicates
        assert modulation.class_boosts.get("scarcity") == 1.5

        ms = {"scarcity": 0.6, "authority": 0.5, "reciprocity": 0.4}
        result = apply_cell_modulation(ms, modulation)
        assert abs(result["scarcity"] - 0.9) < 1e-9
        assert abs(result["reciprocity"] - 0.28) < 1e-9
        assert result["authority"] == 0.5
