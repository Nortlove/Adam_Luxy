"""Stage 2 B2 verification: page edge shift threaded through L3 scoring.

These tests pin the architectural fix that moves page-context effects from
post-hoc modulation into the edge-dimension repositioning that precedes
mechanism scoring (see ADAM_PAGE_INTELLIGENCE_REVIEW.md Pass B, and the
ADAM_STAGE_1_POST_WIRING_VERIFICATION follow-ups).

The Stage 1 wiring only stashed the shift vector on context_intelligence
as observability. Stage 2 actually threads it through level3_bilateral_edges
so mechanism_scores differ between the no-shift and shifted paths — that
is what these tests assert.
"""

from __future__ import annotations

from typing import Any, Dict

import pytest


# ---------------------------------------------------------------------------
# Stub graph cache
# ---------------------------------------------------------------------------

class StubGraphCache:
    """Minimal graph cache: returns a fixed edge aggregate and a stub ad profile.

    The edge_agg values are chosen so every edge dimension lands near 0.5
    neutral, which makes the test sensitive to shift application: a non-
    trivial shift must move the derived scores away from the baseline.
    """

    def __init__(self, edge_count: int = 500):
        self._edge_count = edge_count

    def get_edge_aggregates(self, asin: str, archetype: str) -> Dict[str, Any]:
        return {
            "edge_count": self._edge_count,
            "avg_reg_fit": 0.5,
            "avg_construal_fit": 0.5,
            "avg_personality_align": 0.5,
            "avg_emotional": 0.5,
            "avg_value": 0.5,
            "avg_evo": 0.5,
            "avg_composite": 0.5,
            "std_composite": 0.1,
            "avg_confidence": 0.7,
            "avg_linguistic": 0.5,
            "avg_persuasion_susceptibility": 0.5,
            "avg_cognitive_load_tolerance": 0.5,
            "avg_narrative_transport": 0.5,
            "avg_social_proof_sensitivity": 0.5,
            "avg_loss_aversion_intensity": 0.5,
            "avg_temporal_discounting": 0.5,
            "avg_brand_relationship_depth": 0.5,
            "avg_autonomy_reactance": 0.5,
            "avg_information_seeking": 0.5,
            "avg_mimetic_desire": 0.5,
            "avg_interoceptive_awareness": 0.5,
            "avg_cooperative_framing_fit": 0.5,
            "avg_decision_entropy": 0.5,
        }

    def get_product_profile(self, asin: str) -> Dict[str, Any]:
        return {}  # No ad profile — skip the modulation branch


def _fresh_base():
    from adam.api.stackadapt.bilateral_cascade import level1_archetype_prior
    return level1_archetype_prior("achiever")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestB2Stage2PageShiftInL3:
    """level3_bilateral_edges must consume page_shift in its scoring path."""

    def test_l3_signature_accepts_page_shift(self):
        import inspect
        from adam.api.stackadapt.bilateral_cascade import level3_bilateral_edges

        params = inspect.signature(level3_bilateral_edges).parameters
        assert "page_shift" in params, (
            "level3_bilateral_edges must accept page_shift kwarg (B2 Stage 2)"
        )
        assert "page_confidence" in params, (
            "level3_bilateral_edges must accept page_confidence kwarg"
        )

    def test_no_shift_is_behaviorally_identical(self):
        """Passing page_shift=None must not perturb mechanism_scores."""
        from adam.api.stackadapt.bilateral_cascade import level3_bilateral_edges

        cache = StubGraphCache()
        base_a = _fresh_base()
        base_b = _fresh_base()

        r_a = level3_bilateral_edges("asin_x", "achiever", cache, base_a)
        r_b = level3_bilateral_edges(
            "asin_x", "achiever", cache, base_b,
            page_shift=None, page_confidence=0.0,
        )
        assert r_a.mechanism_scores == r_b.mechanism_scores

    def test_shift_changes_mechanism_scores(self):
        """A non-trivial shift must produce different mechanism_scores."""
        from adam.api.stackadapt.bilateral_cascade import level3_bilateral_edges

        cache = StubGraphCache()
        baseline = level3_bilateral_edges(
            "asin_x", "achiever", cache, _fresh_base(),
        )

        # A realistic shift vector: loss-aversion amplified, autonomy
        # reactance dampened, narrative transport up. These are the
        # kinds of deltas compute_page_edge_shift produces on a
        # high-authority editorial page.
        shift = {
            "loss_aversion_intensity": 0.25,
            "autonomy_reactance": -0.20,
            "narrative_transport": 0.18,
            "social_proof_sensitivity": 0.15,
        }
        shifted = level3_bilateral_edges(
            "asin_x", "achiever", cache, _fresh_base(),
            page_shift=shift, page_confidence=0.8,
        )

        assert baseline.mechanism_scores != shifted.mechanism_scores, (
            "Page shift must perturb mechanism_scores — B2 Stage 2 wiring"
        )

        # Loss-aversion shift up → loss_aversion mechanism score up
        assert shifted.mechanism_scores["loss_aversion"] > baseline.mechanism_scores["loss_aversion"], (
            f"loss_aversion should rise with +0.25 loss_aversion_intensity shift. "
            f"baseline={baseline.mechanism_scores['loss_aversion']}, "
            f"shifted={shifted.mechanism_scores['loss_aversion']}"
        )

        # Social_proof shift up → social_proof mechanism score up
        assert shifted.mechanism_scores["social_proof"] > baseline.mechanism_scores["social_proof"]

    def test_shift_is_stashed_with_consumed_flag(self):
        """When a shift is applied, context_intelligence must record it."""
        from adam.api.stackadapt.bilateral_cascade import level3_bilateral_edges

        cache = StubGraphCache()
        shift = {"loss_aversion_intensity": 0.2}
        result = level3_bilateral_edges(
            "asin_x", "achiever", cache, _fresh_base(),
            page_shift=shift, page_confidence=0.7,
        )

        assert result.context_intelligence is not None
        pes = result.context_intelligence.get("page_edge_shift")
        assert pes is not None, "page_edge_shift stash missing from context_intelligence"
        assert pes["consumed_by_scoring"] is True, (
            "Stage 2 must mark consumed_by_scoring=True — this is the "
            "observability signal that distinguishes the pre-B2 post-hoc "
            "path from the B2 Stage 2 L3-consumed path"
        )
        assert pes["stage"] == "level3_scoring"
        assert pes["page_confidence"] == 0.7

    def test_helper_returns_empty_without_page_url(self):
        """The cascade helper must return neutral values when page_url is None."""
        from adam.api.stackadapt.bilateral_cascade import _compute_page_shift_for_cascade

        shift, conf, profile = _compute_page_shift_for_cascade(page_url=None)
        assert shift == {}
        assert conf == 0.0
        assert profile is None
