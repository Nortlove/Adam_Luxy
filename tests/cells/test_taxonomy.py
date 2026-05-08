"""F.1 / S6.1 (1 of 2) — cell taxonomy tests.

Pin the 2,880-cell static enumeration (Q15=(β) cardinality
8 × 5 × 6 × 3 × 4 = 2,880), cell ID format, axis coverage,
parent routing format, frozen-dataclass invariant, and module-import
correctness.

ConversionStage (6) is canonical via Enhancement #33; cell axis
cardinality follows that mapping. Heckhausen-Gollwitzer (1987) is
the theoretical lineage but not re-implemented as a separate enum.
"""
import dataclasses

import pytest

from adam.cells.taxonomy import (
    CELL_TAXONOMY,
    EXPECTED_CELL_COUNT,
    EXPECTED_PARENT_CELL_COUNT,
    Cell,
    RegulatoryFocus,
    ValenceArousalQuadrant,
    _construct_cell_id,
    get_active_cells,
    get_active_parent_cell_count,
    get_cell,
    get_parent_cell_id,
)
from adam.cold_start.models.enums import ArchetypeID
from adam.intelligence.posture_five_class import FIVE_CLASS_POSTURES
from adam.retargeting.models.enums import ConversionStage


class TestCellTaxonomyEnumeration:

    def test_cell_count_equals_2880(self):
        """Test 1: 8 × 5 × 6 × 3 × 4 = 2,880 cells per Q15=(β)
        (ConversionStage 6, not the original spec's JourneyState 4)."""
        assert len(CELL_TAXONOMY) == EXPECTED_CELL_COUNT
        assert EXPECTED_CELL_COUNT == 2880

    def test_cell_ids_are_unique(self):
        """Test 2: every cell_id appears exactly once. Dict keys
        already enforce uniqueness; this test pins that the keys
        match the cell.cell_id fields exactly."""
        for cell_id, cell in CELL_TAXONOMY.items():
            assert cell.cell_id == cell_id, (
                f"key/cell.cell_id mismatch: {cell_id!r} ≠ {cell.cell_id!r}"
            )

    def test_every_axis_combination_has_exactly_one_cell(self):
        """Test 3: every (archetype, posture, stage, regfocus, quadrant)
        tuple appears exactly once across the taxonomy."""
        seen_tuples = set()
        for cell in CELL_TAXONOMY.values():
            tup = (
                cell.archetype, cell.posture,
                cell.conversion_stage, cell.regulatory_focus,
                cell.valence_arousal,
            )
            assert tup not in seen_tuples, (
                f"duplicate axis tuple: {tup}"
            )
            seen_tuples.add(tup)
        assert len(seen_tuples) == EXPECTED_CELL_COUNT

    def test_cell_id_format_pinning(self):
        """Test 4: every cell_id matches the canonical format
        '{archetype}_{posture}_{stage}_{regfocus}_{quadrant}'
        with exactly 5 underscore-delimited parts."""
        for cell_id in CELL_TAXONOMY:
            parts = cell_id.split("_")
            assert len(parts) == 5, (
                f"cell_id {cell_id!r} has {len(parts)} parts, expected 5"
            )

    def test_all_cells_default_to_active_at_module_import(self):
        """Test 5: no pruning happens at module import — every cell
        starts is_active=True. Pruning is an offline pass that
        updates the flag explicitly."""
        for cell in CELL_TAXONOMY.values():
            assert cell.is_active is True, (
                f"cell {cell.cell_id} not active by default"
            )


class TestPublicAccessors:

    def test_get_cell_returns_cell_for_known_id(self):
        sample_id = next(iter(CELL_TAXONOMY))
        cell = get_cell(sample_id)
        assert isinstance(cell, Cell)
        assert cell.cell_id == sample_id

    def test_get_cell_raises_keyerror_on_unknown_id(self):
        """Test 6: unknown cell_id raises KeyError."""
        with pytest.raises(KeyError):
            get_cell("NONEXISTENT_XX_XXX_XXXX_XX")

    def test_get_active_cells_returns_full_set_when_all_active(self):
        """Test 7: with default is_active=True on every cell,
        get_active_cells returns the full 2,880 cell IDs."""
        active = get_active_cells()
        assert isinstance(active, frozenset)
        assert len(active) == EXPECTED_CELL_COUNT

    def test_get_parent_cell_id_format(self):
        """Test 8: parent ID = '{archetype}_{posture}_PARENT'."""
        cell_id = "ANALYST_TC_INT_PROM_Q1"
        assert get_parent_cell_id(cell_id) == "ANALYST_TC_PARENT"

    def test_get_parent_cell_id_works_for_all_cells(self):
        """Every cell in the taxonomy has a derivable parent ID."""
        seen_parents = set()
        for cell_id in CELL_TAXONOMY:
            pid = get_parent_cell_id(cell_id)
            assert pid.endswith("_PARENT")
            seen_parents.add(pid)
        # Test 9 numerically: 8 archetypes × 5 postures = 40 parents.
        assert len(seen_parents) == EXPECTED_PARENT_CELL_COUNT

    def test_get_parent_cell_id_rejects_malformed(self):
        with pytest.raises(ValueError, match="Malformed cell_id"):
            get_parent_cell_id("BAD")

    def test_get_active_parent_cell_count_pinned_at_40(self):
        """Test 9: parent count = 8 × 5 = 40."""
        assert get_active_parent_cell_count() == 40
        assert EXPECTED_PARENT_CELL_COUNT == 40


class TestFrozenInvariant:

    def test_cell_dataclass_is_frozen(self):
        """Test 10: Cell instances cannot be mutated after
        construction (frozen dataclass invariant)."""
        cell = next(iter(CELL_TAXONOMY.values()))
        with pytest.raises(dataclasses.FrozenInstanceError):
            cell.is_active = False  # type: ignore[misc]


class TestSubstrateEnumCoverage:

    def test_all_archetypes_appear(self):
        """Test 11a: every ArchetypeID value used at least once."""
        seen = {c.archetype for c in CELL_TAXONOMY.values()}
        for a in ArchetypeID:
            assert a in seen, f"archetype {a} not present in taxonomy"

    def test_all_postures_appear(self):
        """Test 11b: every FIVE_CLASS_POSTURES value used."""
        seen = {c.posture for c in CELL_TAXONOMY.values()}
        for p in FIVE_CLASS_POSTURES:
            assert p in seen, f"posture {p} not present in taxonomy"

    def test_all_conversion_stages_appear(self):
        """Test 11c: every ConversionStage (6 values) used.
        Per Q15=(β): cells use ConversionStage, NOT JourneyStage (13)."""
        seen = {c.conversion_stage for c in CELL_TAXONOMY.values()}
        for s in ConversionStage:
            assert s in seen, f"stage {s} not present in taxonomy"
        assert len(seen) == 6

    def test_all_regulatory_focus_values_appear(self):
        """Test 11d: PROMOTION + PREVENTION + NEUTRAL all used."""
        seen = {c.regulatory_focus for c in CELL_TAXONOMY.values()}
        for r in RegulatoryFocus:
            assert r in seen
        assert len(seen) == 3

    def test_all_quadrants_appear(self):
        """Test 11e: Q1/Q2/Q3/Q4 all used."""
        seen = {c.valence_arousal for c in CELL_TAXONOMY.values()}
        for q in ValenceArousalQuadrant:
            assert q in seen
        assert len(seen) == 4


class TestCanonicalCellIDExample:
    """Pin the canonical example cell ID from the slice spec
    (ANALYST + TASK_COMPLETION + INTENDING + PROMOTION + Q1)."""

    def test_canonical_example_constructs_correctly(self):
        cid = _construct_cell_id(
            ArchetypeID.ANALYST,
            "TASK_COMPLETION",
            ConversionStage.INTENDING,
            RegulatoryFocus.PROMOTION,
            ValenceArousalQuadrant.Q1_EXCITED,
        )
        assert cid == "ANALYST_TC_INT_PROM_Q1"

    def test_canonical_example_present_in_taxonomy(self):
        """The canonical example MUST exist in CELL_TAXONOMY since
        all 2,880 axis combinations are enumerated at import."""
        assert "ANALYST_TC_INT_PROM_Q1" in CELL_TAXONOMY
