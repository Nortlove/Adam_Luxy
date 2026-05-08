"""F.1 / S6.1 (1 of 2) — cell constructor tests.

Pin the bid-time tuple constructor: quadrant boundary semantics,
construct_cell_id round-trip, get_cell_for_bid contract, pruned-cell
parent routing, latency budget, and full 2,880-cell coverage without
exception. Plus zero-regression that this slice adds new files only.
"""
import dataclasses
import random
import time

import pytest

from adam.cells import (
    AROUSAL_NEUTRAL_THRESHOLD,
    CELL_TAXONOMY,
    EXPECTED_CELL_COUNT,
    VALENCE_NEUTRAL_THRESHOLD,
    Cell,
    RegulatoryFocus,
    ValenceArousalQuadrant,
    compute_valence_arousal_quadrant,
    construct_cell_id,
    get_cell_for_bid,
)
from adam.cold_start.models.enums import ArchetypeID
from adam.intelligence.posture_five_class import FIVE_CLASS_POSTURES
from adam.retargeting.models.enums import ConversionStage


# ---------------------------------------------------------------------------
# Quadrant boundary semantics
# ---------------------------------------------------------------------------

class TestQuadrantBoundaries:
    """Test 12: compute_valence_arousal_quadrant for the 5 canonical
    boundary patterns (the 4 quadrant interiors + the at-threshold
    case which ties downward per spec)."""

    def test_high_v_high_a_yields_q1_excited(self):
        assert compute_valence_arousal_quadrant(0.5, 0.7) == \
            ValenceArousalQuadrant.Q1_EXCITED

    def test_high_v_low_a_yields_q2_contented(self):
        assert compute_valence_arousal_quadrant(0.5, 0.3) == \
            ValenceArousalQuadrant.Q2_CONTENTED

    def test_low_v_high_a_yields_q3_anxious(self):
        assert compute_valence_arousal_quadrant(-0.5, 0.7) == \
            ValenceArousalQuadrant.Q3_ANXIOUS

    def test_low_v_low_a_yields_q4_withdrawn(self):
        assert compute_valence_arousal_quadrant(-0.5, 0.3) == \
            ValenceArousalQuadrant.Q4_WITHDRAWN

    def test_at_threshold_ties_downward(self):
        """valence == 0 AND arousal == 0.5 → Q4_WITHDRAWN per spec
        (canonical convention: ties broken downward on each axis)."""
        assert compute_valence_arousal_quadrant(0.0, 0.5) == \
            ValenceArousalQuadrant.Q4_WITHDRAWN

    def test_threshold_constants_pinned(self):
        """Calibration interface: thresholds are module-level
        constants, not magic numbers in the function body."""
        assert VALENCE_NEUTRAL_THRESHOLD == 0.0
        assert AROUSAL_NEUTRAL_THRESHOLD == 0.5


# ---------------------------------------------------------------------------
# construct_cell_id contract
# ---------------------------------------------------------------------------

class TestConstructCellID:

    def test_construct_returns_taxonomy_member_for_canonical_inputs(self):
        """Test 13: with all-canonical inputs, the constructed cell_id
        exists in CELL_TAXONOMY."""
        cell_id = construct_cell_id(
            ArchetypeID.ANALYST, "TASK_COMPLETION",
            ConversionStage.INTENDING, RegulatoryFocus.PROMOTION,
            valence=0.5, arousal=0.7,
        )
        assert cell_id == "ANALYST_TC_INT_PROM_Q1"
        assert cell_id in CELL_TAXONOMY

    def test_round_trip_preserves_axes(self):
        """Test 14: get_cell on the constructed ID returns Cell with
        matching axis values."""
        cell_id = construct_cell_id(
            ArchetypeID.GUARDIAN, "SOCIAL_CONSUMPTION",
            ConversionStage.STALLED, RegulatoryFocus.PREVENTION,
            valence=-0.5, arousal=0.7,
        )
        cell = CELL_TAXONOMY[cell_id]
        assert cell.archetype == ArchetypeID.GUARDIAN
        assert cell.posture == "SOCIAL_CONSUMPTION"
        assert cell.conversion_stage == ConversionStage.STALLED
        assert cell.regulatory_focus == RegulatoryFocus.PREVENTION
        assert cell.valence_arousal == ValenceArousalQuadrant.Q3_ANXIOUS

    def test_full_2880_combinatorial_iteration_succeeds(self):
        """Test 18: iterate over the full 2,880-cell space; for each
        axis tuple, call construct_cell_id; assert each returns a
        valid cell_id without exception. With ConversionStage 6
        instead of original spec's 4-state journey: 2,880 not 1,920."""
        successful = 0
        for archetype in ArchetypeID:
            for posture in FIVE_CLASS_POSTURES:
                for stage in ConversionStage:
                    for reg in RegulatoryFocus:
                        for v_a in [
                            (0.5, 0.7),    # Q1
                            (0.5, 0.3),    # Q2
                            (-0.5, 0.7),   # Q3
                            (-0.5, 0.3),   # Q4
                        ]:
                            valence, arousal = v_a
                            cid = construct_cell_id(
                                archetype, posture, stage, reg,
                                valence, arousal,
                            )
                            assert cid in CELL_TAXONOMY
                            successful += 1
        assert successful == EXPECTED_CELL_COUNT


# ---------------------------------------------------------------------------
# get_cell_for_bid high-level accessor
# ---------------------------------------------------------------------------

class TestGetCellForBid:

    def test_returns_cell_object_with_matching_axes(self):
        """Test 15: high-level accessor returns a Cell instance."""
        cell = get_cell_for_bid(
            ArchetypeID.EXPLORER, "INFORMATION_FORAGING",
            ConversionStage.CURIOUS, RegulatoryFocus.NEUTRAL,
            valence=0.5, arousal=0.7,
        )
        assert isinstance(cell, Cell)
        assert cell.archetype == ArchetypeID.EXPLORER
        assert cell.posture == "INFORMATION_FORAGING"
        assert cell.conversion_stage == ConversionStage.CURIOUS

    def test_pruned_cell_routes_to_parent(self):
        """Tests 16 + 20: when the constructed cell is is_active=False,
        the bid-time accessor returns a synthesized parent Cell with
        cell_id ending in '_PARENT'."""
        sample = next(iter(CELL_TAXONOMY.values()))
        # Map quadrant back to canonical (valence, arousal) pair.
        quadrant_to_va = {
            ValenceArousalQuadrant.Q1_EXCITED: (0.5, 0.7),
            ValenceArousalQuadrant.Q2_CONTENTED: (0.5, 0.3),
            ValenceArousalQuadrant.Q3_ANXIOUS: (-0.5, 0.7),
            ValenceArousalQuadrant.Q4_WITHDRAWN: (-0.5, 0.3),
        }
        valence, arousal = quadrant_to_va[sample.valence_arousal]

        # Mark this cell pruned by swapping in a frozen copy with
        # is_active=False.
        original = CELL_TAXONOMY[sample.cell_id]
        pruned = dataclasses.replace(original, is_active=False)
        CELL_TAXONOMY[sample.cell_id] = pruned
        try:
            parent = get_cell_for_bid(
                sample.archetype, sample.posture,
                sample.conversion_stage, sample.regulatory_focus,
                valence, arousal,
            )
            assert parent.cell_id.endswith("_PARENT")
            # Parent inherits archetype + posture; collapsed dims
            # take neutral defaults.
            assert parent.archetype == sample.archetype
            assert parent.posture == sample.posture
            assert parent.regulatory_focus == RegulatoryFocus.NEUTRAL
        finally:
            # Restore taxonomy state.
            CELL_TAXONOMY[sample.cell_id] = original


# ---------------------------------------------------------------------------
# Latency budget
# ---------------------------------------------------------------------------

class TestLatencyBudget:

    def test_construct_cell_id_p99_under_2ms(self):
        """Test 17: time construct_cell_id over 10,000 randomly-
        parameterized calls; p99 < 2ms. In practice this is
        microseconds (5 dict lookups + a few enum ops)."""
        rng = random.Random(2026)
        latencies_us = []
        archetypes = list(ArchetypeID)
        postures = list(FIVE_CLASS_POSTURES)
        stages = list(ConversionStage)
        regs = list(RegulatoryFocus)
        for _ in range(10000):
            t0 = time.perf_counter()
            construct_cell_id(
                rng.choice(archetypes),
                rng.choice(postures),
                rng.choice(stages),
                rng.choice(regs),
                rng.uniform(-1, 1),
                rng.uniform(0, 1),
            )
            latencies_us.append((time.perf_counter() - t0) * 1_000_000)
        latencies_us.sort()
        p99 = latencies_us[int(len(latencies_us) * 0.99)]
        assert p99 < 2000, (
            f"p99 latency {p99:.1f}μs exceeds 2ms bid-time budget"
        )


# ---------------------------------------------------------------------------
# Zero-regression
# ---------------------------------------------------------------------------

class TestZeroRegression:
    """Test 19: this slice adds new files only. No modifications to
    A.2's archetype priors, B's PagePrimingSignature, C/D's mindstate
    composites, E's UserCohort schema, or any other existing module.

    Pinned by importing the prior-slice surfaces and asserting they
    are still accessible / unchanged.
    """

    def test_archetype_id_enum_unchanged(self):
        """A.2 surface intact."""
        assert ArchetypeID.ANALYST.value == "analyst"
        assert len(list(ArchetypeID)) == 8

    def test_page_priming_signature_v2_dimensions_unchanged(self):
        """B surface intact: V2 schema with 6 dimensions."""
        from adam.priming import SIGNATURE_DIMENSIONS, SIGNATURE_VERSION_V2
        assert "persuasion_knowledge_activation" in SIGNATURE_DIMENSIONS
        assert SIGNATURE_VERSION_V2  # truthy version constant

    def test_page_mindstate_vector_composite_states_unchanged(self):
        """C + D surfaces intact: fomo_score + psych_ownership_proxy
        + depletion_proxy still on PageMindstateVector."""
        from adam.retargeting.resonance.models import (
            DEPLETION_THRESHOLD_SECONDS, PageMindstateVector,
        )
        m = PageMindstateVector()
        assert hasattr(m, "fomo_score")
        assert hasattr(m, "psych_ownership_proxy")
        assert hasattr(m, "depletion_proxy")
        assert DEPLETION_THRESHOLD_SECONDS == 1800.0

    def test_user_cohort_schema_slot_unchanged(self):
        """E surface intact: compensatory_consumption_pattern slot
        still on UserCohort with safe defaults."""
        from adam.intelligence.cohort_discovery import UserCohort
        c = UserCohort(cohort_id="x", size=1, sample_members=[])
        assert c.compensatory_consumption_pattern is False
        assert c.compensatory_detection_confidence == 0.5

    def test_five_class_postures_unchanged(self):
        """G1.path4 substrate intact."""
        assert len(FIVE_CLASS_POSTURES) == 5
        assert "INFORMATION_FORAGING" in FIVE_CLASS_POSTURES
