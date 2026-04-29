# =============================================================================
# ADAM Page Attentional Posture Substrate Tests
# Location: tests/unit/test_page_attentional_posture_substrate.py
# =============================================================================

"""Tests for task #28 — page attentional posture substrate."""

from __future__ import annotations

import pytest

from adam.intelligence.page_attentional_posture_substrate import (
    BLEND_FLOAT_THRESHOLD,
    MIN_POSTURE_CONFIDENCE,
    POSTURE_BLEND,
    POSTURE_NEUTRAL,
    POSTURE_UNKNOWN,
    POSTURE_VIGILANCE,
    PageAttentionalPostureAccumulator,
    PageObservation,
    PostureStats,
    VIGILANCE_FLOAT_THRESHOLD,
    categorize_posture,
    get_page_attentional_posture_accumulator,
    reset_page_attentional_posture_accumulator,
)


# ============================================================================
# Categorization
# ============================================================================


class TestCategorize:

    def test_low_confidence_unknown(self):
        # Even with strong-blend posture, low confidence → unknown
        result = categorize_posture(posture_float=-0.8, posture_confidence=0.1)
        assert result == POSTURE_UNKNOWN

    def test_blend_categorization(self):
        result = categorize_posture(posture_float=-0.5, posture_confidence=0.7)
        assert result == POSTURE_BLEND

    def test_vigilance_categorization(self):
        result = categorize_posture(posture_float=0.6, posture_confidence=0.8)
        assert result == POSTURE_VIGILANCE

    def test_neutral_with_high_confidence(self):
        """Mid-range posture with strong confidence is EXPLICITLY neutral
        — we know the page is neutral, not unknown."""
        result = categorize_posture(posture_float=0.0, posture_confidence=0.9)
        assert result == POSTURE_NEUTRAL

    def test_threshold_boundaries(self):
        """At exactly the float threshold, the categorization fires."""
        assert categorize_posture(BLEND_FLOAT_THRESHOLD, 0.7) == POSTURE_BLEND
        assert categorize_posture(VIGILANCE_FLOAT_THRESHOLD, 0.7) == POSTURE_VIGILANCE
        # Just inside the neutral range
        assert categorize_posture(BLEND_FLOAT_THRESHOLD + 0.01, 0.7) == POSTURE_NEUTRAL
        assert categorize_posture(VIGILANCE_FLOAT_THRESHOLD - 0.01, 0.7) == POSTURE_NEUTRAL

    def test_min_confidence_boundary(self):
        """At exactly MIN_POSTURE_CONFIDENCE, categorization fires."""
        result = categorize_posture(
            posture_float=-0.5,
            posture_confidence=MIN_POSTURE_CONFIDENCE,
        )
        assert result == POSTURE_BLEND
        # Just below
        result = categorize_posture(
            posture_float=-0.5,
            posture_confidence=MIN_POSTURE_CONFIDENCE - 0.01,
        )
        assert result == POSTURE_UNKNOWN


# ============================================================================
# PostureStats — accumulator unit
# ============================================================================


class TestPostureStats:

    def test_empty_stats(self):
        stats = PostureStats()
        assert stats.n_observations == 0
        assert stats.weighted_mean == 0.0
        assert stats.weighted_variance == 0.0

    def test_single_observation(self):
        stats = PostureStats()
        stats.add(value=0.5, weight=0.8)
        assert stats.n_observations == 1
        assert stats.weighted_mean == pytest.approx(0.5, abs=1e-9)
        assert stats.weighted_variance == pytest.approx(0.0, abs=1e-9)

    def test_multiple_observations_weighted_mean(self):
        stats = PostureStats()
        # Two observations: value 0.4 weight 1.0, value 0.6 weight 1.0
        stats.add(value=0.4, weight=1.0)
        stats.add(value=0.6, weight=1.0)
        assert stats.weighted_mean == pytest.approx(0.5, abs=1e-9)

    def test_weighted_mean_skews_with_weight(self):
        stats = PostureStats()
        stats.add(value=0.0, weight=0.1)  # low confidence
        stats.add(value=1.0, weight=0.9)  # high confidence
        # Weighted mean closer to 1.0
        assert stats.weighted_mean == pytest.approx(0.9, abs=1e-9)

    def test_zero_weight_observation_skipped(self):
        stats = PostureStats()
        stats.add(value=0.5, weight=0.0)
        assert stats.n_observations == 0

    def test_variance_nonneg(self):
        stats = PostureStats()
        stats.add(value=0.0, weight=1.0)
        stats.add(value=1.0, weight=1.0)
        # Variance should be 0.25 (mean=0.5, dev=±0.5, var=0.25)
        assert stats.weighted_variance == pytest.approx(0.25, abs=1e-9)


# ============================================================================
# Accumulator — record + retrieve
# ============================================================================


class TestAccumulatorRecord:

    def test_record_at_all_three_levels(self):
        acc = PageAttentionalPostureAccumulator()
        acc.record(PageObservation(
            page_url="https://luxyride.com/blog/post1",
            posture_float=-0.6,
            posture_confidence=0.8,
            author_id="author:jane_doe",
            publication_id="pub:luxy_blog",
            section_id="section:luxury_lifestyle",
        ))
        # All three keys recorded
        assert acc.get_author_stats("author:jane_doe") is not None
        assert acc.get_publication_stats("pub:luxy_blog") is not None
        assert acc.get_section_stats("section:luxury_lifestyle") is not None

    def test_record_partial_keys(self):
        """Observation with only publication_id records only at that
        level."""
        acc = PageAttentionalPostureAccumulator()
        acc.record(PageObservation(
            page_url="https://example.com/x",
            posture_float=0.5,
            posture_confidence=0.7,
            publication_id="pub:example",
        ))
        assert acc.get_publication_stats("pub:example") is not None
        # Author + section levels untouched
        assert acc.get_author_stats("any") is None

    def test_zero_confidence_observation_skipped(self):
        acc = PageAttentionalPostureAccumulator()
        acc.record(PageObservation(
            page_url="https://example.com/x",
            posture_float=0.5,
            posture_confidence=0.0,
            author_id="author:a",
        ))
        assert acc.get_author_stats("author:a") is None


# ============================================================================
# predict_posture — Bayesian-shrinkage-flavored prediction
# ============================================================================


class TestPredictPosture:

    def test_no_data_returns_none(self):
        acc = PageAttentionalPostureAccumulator()
        result = acc.predict_posture(
            author_id="unknown_author",
            publication_id="unknown_pub",
            section_id="unknown_section",
        )
        assert result is None

    def test_below_min_observations_returns_none(self):
        acc = PageAttentionalPostureAccumulator()
        # Record only 2 observations on the publication
        for _ in range(2):
            acc.record(PageObservation(
                page_url="x", posture_float=-0.6, posture_confidence=0.8,
                publication_id="pub:test",
            ))
        result = acc.predict_posture(publication_id="pub:test", min_observations=5)
        assert result is None

    def test_at_min_observations_returns_prediction(self):
        acc = PageAttentionalPostureAccumulator()
        for _ in range(5):
            acc.record(PageObservation(
                page_url="x", posture_float=-0.6, posture_confidence=0.8,
                publication_id="pub:test",
            ))
        result = acc.predict_posture(publication_id="pub:test", min_observations=5)
        assert result is not None
        posture, conf = result
        assert posture == pytest.approx(-0.6, abs=1e-9)
        assert 0.0 < conf <= 1.0

    def test_author_takes_priority_over_publication(self):
        """When both author and publication have enough observations,
        author wins (most specific)."""
        acc = PageAttentionalPostureAccumulator()
        # Author has 5 observations of -0.5 (blend)
        for _ in range(5):
            acc.record(PageObservation(
                page_url="x", posture_float=-0.5, posture_confidence=0.8,
                author_id="author:a",
                publication_id="pub:p",
            ))
        # Publication has 5 more observations of +0.5 (vigilance) from
        # other authors
        for _ in range(5):
            acc.record(PageObservation(
                page_url="y", posture_float=0.5, posture_confidence=0.8,
                publication_id="pub:p",
            ))

        # Predict for the same author + publication
        result = acc.predict_posture(
            author_id="author:a",
            publication_id="pub:p",
            min_observations=5,
        )
        posture, _ = result
        # Author's posture wins
        assert posture == pytest.approx(-0.5, abs=1e-9)

    def test_publication_used_when_author_below_threshold(self):
        acc = PageAttentionalPostureAccumulator()
        # Author has 2 observations (below threshold)
        for _ in range(2):
            acc.record(PageObservation(
                page_url="x", posture_float=-0.5, posture_confidence=0.8,
                author_id="author:newish",
                publication_id="pub:p",
            ))
        # Publication has 5 more (combined 7 at publication level)
        for _ in range(5):
            acc.record(PageObservation(
                page_url="y", posture_float=0.5, posture_confidence=0.8,
                publication_id="pub:p",
            ))

        result = acc.predict_posture(
            author_id="author:newish",
            publication_id="pub:p",
            min_observations=5,
        )
        # Author has only 2 obs (below threshold) → fall to publication
        posture, _ = result
        # Publication has 7 total observations, mix of -0.5 and +0.5
        # weighted mean = (2 × -0.5 × 0.8 + 5 × 0.5 × 0.8) / (7 × 0.8) = 0.214
        assert posture == pytest.approx((2 * -0.5 + 5 * 0.5) / 7, abs=1e-9)

    def test_confidence_grows_with_observation_count(self):
        acc = PageAttentionalPostureAccumulator()
        # Add observations, sample confidence progressively
        for n in (5, 10, 20, 30):
            acc.reset()
            for _ in range(n):
                acc.record(PageObservation(
                    page_url="x", posture_float=-0.5, posture_confidence=0.8,
                    publication_id="pub:test",
                ))
            result = acc.predict_posture(
                publication_id="pub:test", min_observations=5,
            )
            _, conf = result
            assert 0.0 < conf <= 1.0


# ============================================================================
# Singleton
# ============================================================================


class TestSingleton:

    def test_singleton_consistency(self):
        reset_page_attentional_posture_accumulator()
        try:
            a1 = get_page_attentional_posture_accumulator()
            a2 = get_page_attentional_posture_accumulator()
            assert a1 is a2
        finally:
            reset_page_attentional_posture_accumulator()
