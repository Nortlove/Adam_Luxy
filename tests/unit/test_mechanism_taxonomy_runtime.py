# =============================================================================
# ADAM Mechanism Taxonomy Runtime Tests
# Location: tests/unit/test_mechanism_taxonomy_runtime.py
# =============================================================================

"""Tests for task #29 — runtime substrate for mechanism taxonomy."""

from __future__ import annotations

import pytest

from adam.intelligence.mechanism_taxonomy import MechanismRouteCategory
from adam.intelligence.mechanism_taxonomy_runtime import (
    CategoryConditionalCounts,
    TaggedDecision,
    TaxonomyConditionalAccumulator,
    get_taxonomy_accumulator,
    reset_taxonomy_accumulator,
    tag_decision,
)


# ============================================================================
# tag_decision
# ============================================================================


class TestTagDecision:

    def test_known_blend_compatible_mechanism(self):
        tagged = tag_decision("automatic_evaluation")
        assert tagged.was_known is True
        assert tagged.category == MechanismRouteCategory.BLEND_COMPATIBLE
        assert tagged.regret_correlation_prior is not None
        assert 0.0 <= tagged.regret_correlation_prior <= 1.0

    def test_known_vigilance_activating_mechanism(self):
        tagged = tag_decision("attention_dynamics")
        assert tagged.was_known is True
        assert tagged.category == MechanismRouteCategory.VIGILANCE_ACTIVATING
        assert tagged.regret_correlation_prior is not None

    def test_unknown_mechanism_drift_signal(self):
        """Unknown mechanism → was_known=False, category=None.
        Caller / ops monitoring detects drift via was_known=False."""
        tagged = tag_decision("totally_made_up_mechanism")
        assert tagged.was_known is False
        assert tagged.category is None
        assert tagged.regret_correlation_prior is None

    def test_empty_mechanism_name_raises(self):
        with pytest.raises(ValueError, match="non-empty"):
            tag_decision("")

    def test_tagged_at_set(self):
        tagged = tag_decision("automatic_evaluation")
        assert tagged.tagged_at is not None


# ============================================================================
# Conditional accumulator
# ============================================================================


class TestConditionalAccumulator:

    def test_record_known_blend_compatible_outcome(self):
        acc = TaxonomyConditionalAccumulator()
        tagged = tag_decision("automatic_evaluation")
        acc.record_outcome(
            tagged, page_posture="blend_compatible",
            converted=True, backfired=False,
        )
        cell = acc.get_cell(
            MechanismRouteCategory.BLEND_COMPATIBLE, "blend_compatible",
        )
        assert cell.n_decisions == 1
        assert cell.n_conversions == 1
        assert cell.n_backfires == 0

    def test_record_known_vigilance_outcome(self):
        acc = TaxonomyConditionalAccumulator()
        tagged = tag_decision("attention_dynamics")
        acc.record_outcome(
            tagged, page_posture="vigilance_activating",
            converted=True, backfired=True,
        )
        cell = acc.get_cell(
            MechanismRouteCategory.VIGILANCE_ACTIVATING,
            "vigilance_activating",
        )
        assert cell.n_decisions == 1
        assert cell.n_conversions == 1
        assert cell.n_backfires == 1

    def test_unknown_mechanism_skipped(self):
        """Drift case — unknown mechanism's outcome NOT accumulated."""
        acc = TaxonomyConditionalAccumulator()
        tagged = tag_decision("unknown_mechanism")
        acc.record_outcome(
            tagged, page_posture="blend_compatible",
            converted=True, backfired=False,
        )
        # No cells created
        assert len(acc.all_cells()) == 0

    def test_conversion_and_backfire_rates_computed(self):
        acc = TaxonomyConditionalAccumulator()
        tagged = tag_decision("automatic_evaluation")
        # Record 10 outcomes: 7 converted, 1 backfired (counted as
        # converted+backfired — refunds are post-conversion events)
        for i in range(10):
            converted = i < 7
            backfired = i == 0  # one backfire
            acc.record_outcome(
                tagged, page_posture="blend_compatible",
                converted=converted, backfired=backfired,
            )
        cell = acc.get_cell(
            MechanismRouteCategory.BLEND_COMPATIBLE, "blend_compatible",
        )
        assert cell.n_decisions == 10
        assert cell.n_conversions == 7
        assert cell.n_backfires == 1
        assert cell.conversion_rate == 0.7
        assert cell.backfire_rate == 0.1

    def test_empty_cell_returns_zero_rates(self):
        acc = TaxonomyConditionalAccumulator()
        cell = acc.get_cell(
            MechanismRouteCategory.BLEND_COMPATIBLE, "blend_compatible",
        )
        assert cell.n_decisions == 0
        assert cell.conversion_rate == 0.0
        assert cell.backfire_rate == 0.0


# ============================================================================
# matched vs mismatched diagonals — Foundation §2 test interface
# ============================================================================


class TestMatchedMismatchedDiagonals:

    def test_blend_on_blend_is_matched(self):
        acc = TaxonomyConditionalAccumulator()
        tagged = tag_decision("automatic_evaluation")  # BLEND_COMPATIBLE
        acc.record_outcome(
            tagged, page_posture="blend_compatible",
            converted=True, backfired=False,
        )
        matched, mismatched = acc.matched_vs_mismatched_diagonals()
        assert len(matched) == 1
        assert len(mismatched) == 0
        assert matched[0].mechanism_category == MechanismRouteCategory.BLEND_COMPATIBLE
        assert matched[0].page_attentional_posture == "blend_compatible"

    def test_vigilance_on_vigilance_is_matched(self):
        acc = TaxonomyConditionalAccumulator()
        tagged = tag_decision("attention_dynamics")
        acc.record_outcome(
            tagged, page_posture="vigilance_activating",
            converted=True, backfired=False,
        )
        matched, mismatched = acc.matched_vs_mismatched_diagonals()
        assert len(matched) == 1
        assert len(mismatched) == 0

    def test_blend_on_vigilance_is_mismatched(self):
        acc = TaxonomyConditionalAccumulator()
        tagged = tag_decision("automatic_evaluation")  # BLEND_COMPATIBLE
        acc.record_outcome(
            tagged, page_posture="vigilance_activating",
            converted=False, backfired=False,
        )
        matched, mismatched = acc.matched_vs_mismatched_diagonals()
        assert len(matched) == 0
        assert len(mismatched) == 1

    def test_vigilance_on_blend_is_mismatched(self):
        acc = TaxonomyConditionalAccumulator()
        tagged = tag_decision("attention_dynamics")  # VIGILANCE_ACTIVATING
        acc.record_outcome(
            tagged, page_posture="blend_compatible",
            converted=True, backfired=True,
        )
        matched, mismatched = acc.matched_vs_mismatched_diagonals()
        assert len(matched) == 0
        assert len(mismatched) == 1

    def test_none_page_posture_excluded_from_diagonals(self):
        """Cells with no page_posture cannot be classified —
        excluded from both diagonals."""
        acc = TaxonomyConditionalAccumulator()
        tagged = tag_decision("automatic_evaluation")
        acc.record_outcome(
            tagged, page_posture=None,
            converted=True, backfired=False,
        )
        matched, mismatched = acc.matched_vs_mismatched_diagonals()
        assert len(matched) == 0
        assert len(mismatched) == 0
        # But the cell exists in all_cells
        assert len(acc.all_cells()) == 1

    def test_full_test_scenario_foundation_2(self):
        """Foundation §2 prediction test scenario.

        Run synthetic data with planted lift on matched diagonals.
        Verify accumulator correctly partitions and the matched cells'
        conversion rates are higher than mismatched.
        """
        acc = TaxonomyConditionalAccumulator()
        blend_mech = tag_decision("automatic_evaluation")
        vig_mech = tag_decision("attention_dynamics")

        # Matched cells — high conversion (planted)
        for i in range(50):
            acc.record_outcome(
                blend_mech, page_posture="blend_compatible",
                converted=(i < 35),  # 70% conversion
                backfired=(i == 0),  # 2% backfire
            )
            acc.record_outcome(
                vig_mech, page_posture="vigilance_activating",
                converted=(i < 30),  # 60% conversion
                backfired=(i < 5),    # 10% backfire (vigilance has higher backfire)
            )
        # Mismatched cells — lower conversion (planted)
        for i in range(50):
            acc.record_outcome(
                blend_mech, page_posture="vigilance_activating",
                converted=(i < 20),  # 40% conversion
                backfired=(i == 0),
            )
            acc.record_outcome(
                vig_mech, page_posture="blend_compatible",
                converted=(i < 15),  # 30% conversion
                backfired=(i < 8),
            )

        matched, mismatched = acc.matched_vs_mismatched_diagonals()
        assert len(matched) == 2
        assert len(mismatched) == 2

        # Average matched conversion rate > mismatched
        m_rate = sum(c.conversion_rate for c in matched) / len(matched)
        mm_rate = sum(c.conversion_rate for c in mismatched) / len(mismatched)
        assert m_rate > mm_rate, (
            f"Matched cells conversion rate ({m_rate:.3f}) should exceed "
            f"mismatched cells ({mm_rate:.3f}) per Foundation §2 prediction"
        )


# ============================================================================
# Singleton
# ============================================================================


class TestSingleton:

    def test_singleton_consistency(self):
        reset_taxonomy_accumulator()
        try:
            a1 = get_taxonomy_accumulator()
            a2 = get_taxonomy_accumulator()
            assert a1 is a2
        finally:
            reset_taxonomy_accumulator()

    def test_reset_clears_singleton(self):
        reset_taxonomy_accumulator()
        a1 = get_taxonomy_accumulator()
        tagged = tag_decision("automatic_evaluation")
        a1.record_outcome(
            tagged, page_posture="blend_compatible",
            converted=True, backfired=False,
        )
        # Reset replaces the singleton
        reset_taxonomy_accumulator()
        a2 = get_taxonomy_accumulator()
        assert a2 is not a1
        assert len(a2.all_cells()) == 0
