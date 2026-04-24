"""Unit tests for processing_depth_priors — the depth-conditioned
route-split primitive consumed by the plant model."""

from __future__ import annotations

import math

import pytest

from adam.intelligence.recommendation_class import (
    ATTENTION_ROUTE_DEPTHS,
    AUTOPILOT_ROUTE_DEPTHS,
    NON_CONVERTING_DEPTHS,
    VALID_POSTURE_BANDS,
    expected_depth_distribution,
    expected_route_fractions,
    normalize_depth_counts_to_distribution,
    route_split_from_counts,
)
from adam.retargeting.engines.processing_depth import ProcessingDepth


# -----------------------------------------------------------------------------
# Depth → route mapping contract
# -----------------------------------------------------------------------------


class TestDepthRouteMapping:
    def test_mapping_partitions_processing_depth(self):
        """Every ProcessingDepth falls in exactly one bucket."""
        all_depths = set(ProcessingDepth)
        buckets = [AUTOPILOT_ROUTE_DEPTHS, ATTENTION_ROUTE_DEPTHS, NON_CONVERTING_DEPTHS]
        covered = set()
        for bucket in buckets:
            assert not covered & bucket, (
                f"depth appears in multiple buckets"
            )
            covered |= bucket
        assert covered == all_depths, (
            f"some depths uncovered: {all_depths - covered}"
        )

    def test_autopilot_depths_are_shallow(self):
        assert ProcessingDepth.UNPROCESSED in AUTOPILOT_ROUTE_DEPTHS
        assert ProcessingDepth.PERIPHERAL in AUTOPILOT_ROUTE_DEPTHS

    def test_attention_depths_are_evaluated(self):
        assert ProcessingDepth.EVALUATED in ATTENTION_ROUTE_DEPTHS

    def test_rejected_is_non_converting(self):
        assert ProcessingDepth.REJECTED in NON_CONVERTING_DEPTHS


# -----------------------------------------------------------------------------
# Expected depth distribution
# -----------------------------------------------------------------------------


class TestExpectedDepthDistribution:
    @pytest.mark.parametrize("band", sorted(VALID_POSTURE_BANDS))
    def test_distribution_sums_to_one(self, band):
        dist = expected_depth_distribution(band)
        assert math.isclose(sum(dist.values()), 1.0, abs_tol=1e-6)

    @pytest.mark.parametrize("band", sorted(VALID_POSTURE_BANDS))
    def test_distribution_covers_all_depths(self, band):
        dist = expected_depth_distribution(band)
        assert set(dist.keys()) == set(ProcessingDepth)

    @pytest.mark.parametrize("band", sorted(VALID_POSTURE_BANDS))
    def test_distribution_is_nonnegative(self, band):
        dist = expected_depth_distribution(band)
        assert all(v >= 0.0 for v in dist.values())

    def test_rejects_unknown_band(self):
        with pytest.raises(ValueError, match="unknown posture_band"):
            expected_depth_distribution("cosmic_autopilot")

    def test_autopilot_high_has_more_shallow_than_vigilance_high(self):
        """Directional sanity: autopilot contexts have more shallow
        processing than vigilance contexts."""
        auto_high = expected_depth_distribution("autopilot_high")
        vig_high = expected_depth_distribution("vigilance_high")
        shallow_auto = (
            auto_high[ProcessingDepth.UNPROCESSED]
            + auto_high[ProcessingDepth.PERIPHERAL]
        )
        shallow_vig = (
            vig_high[ProcessingDepth.UNPROCESSED]
            + vig_high[ProcessingDepth.PERIPHERAL]
        )
        assert shallow_auto > shallow_vig

    def test_vigilance_high_has_more_evaluated_than_autopilot_high(self):
        auto_high = expected_depth_distribution("autopilot_high")
        vig_high = expected_depth_distribution("vigilance_high")
        assert (
            vig_high[ProcessingDepth.EVALUATED]
            > auto_high[ProcessingDepth.EVALUATED]
        )


# -----------------------------------------------------------------------------
# Expected route fractions (derived from distribution × P(convert|depth))
# -----------------------------------------------------------------------------


class TestExpectedRouteFractions:
    @pytest.mark.parametrize("band", sorted(VALID_POSTURE_BANDS))
    def test_fractions_sum_to_one(self, band):
        auto, att = expected_route_fractions(band)
        assert math.isclose(auto + att, 1.0, abs_tol=1e-6)

    @pytest.mark.parametrize("band", sorted(VALID_POSTURE_BANDS))
    def test_fractions_in_unit_interval(self, band):
        auto, att = expected_route_fractions(band)
        assert 0.0 <= auto <= 1.0
        assert 0.0 <= att <= 1.0

    def test_autopilot_high_has_higher_autopilot_fraction_than_vigilance_high(self):
        auto_auto, _ = expected_route_fractions("autopilot_high")
        vig_auto, _ = expected_route_fractions("vigilance_high")
        assert auto_auto > vig_auto

    def test_rejects_unknown_band(self):
        with pytest.raises(ValueError, match="unknown posture_band"):
            expected_route_fractions("cosmic_autopilot")


# -----------------------------------------------------------------------------
# route_split_from_counts (Scope 2 helper)
# -----------------------------------------------------------------------------


class TestRouteSplitFromCounts:
    def test_empty_counts_returns_zeros(self):
        assert route_split_from_counts({}) == (0, 0)

    def test_shallow_depths_go_to_autopilot(self):
        counts = {
            "unprocessed": 5,
            "peripheral": 10,
            "evaluated": 3,
        }
        auto, att = route_split_from_counts(counts)
        assert auto == 15
        assert att == 3

    def test_rejected_depths_excluded_from_both(self):
        counts = {
            "unprocessed": 5,
            "evaluated": 3,
            "deliberate_rejection": 7,
        }
        auto, att = route_split_from_counts(counts)
        assert auto == 5
        assert att == 3
        # Rejected contributed nothing.
        assert auto + att != sum(counts.values())

    def test_unknown_depth_raises(self):
        with pytest.raises(ValueError, match="unknown ProcessingDepth"):
            route_split_from_counts({"partial_attention": 3})

    def test_negative_count_raises(self):
        with pytest.raises(ValueError, match="must be >= 0"):
            route_split_from_counts({"unprocessed": -1})


# -----------------------------------------------------------------------------
# normalize_depth_counts_to_distribution
# -----------------------------------------------------------------------------


class TestNormalizeDepthCountsToDistribution:
    def test_empty_returns_all_zeros(self):
        dist = normalize_depth_counts_to_distribution({})
        assert set(dist.keys()) == {d.value for d in ProcessingDepth}
        assert all(v == 0.0 for v in dist.values())

    def test_distribution_sums_to_one_for_non_empty_input(self):
        counts = {
            "unprocessed": 40,
            "peripheral": 35,
            "evaluated": 18,
            "deliberate_rejection": 7,
        }
        dist = normalize_depth_counts_to_distribution(counts)
        assert math.isclose(sum(dist.values()), 1.0, abs_tol=1e-6)

    def test_distribution_matches_count_fractions(self):
        counts = {"unprocessed": 50, "peripheral": 50}
        dist = normalize_depth_counts_to_distribution(counts)
        assert math.isclose(dist["unprocessed"], 0.5)
        assert math.isclose(dist["peripheral"], 0.5)
        assert dist["evaluated"] == 0.0
        assert dist["deliberate_rejection"] == 0.0

    def test_rejects_unknown_depth(self):
        with pytest.raises(ValueError):
            normalize_depth_counts_to_distribution({"partial_attention": 5})
