"""Tests for Spine #9 — Kelly-Fraction Bid Sizing.

Pins per directive Section 2 (Spine #9) + Section 5:
    1. kelly_fraction returns 0 when edge non-positive
    2. kelly_fraction returns Kelly value when edge positive
    3. fractional_kelly applies κ correctly
    4. winner_curse_shading_factor: open_exchange highest, direct lowest
    5. compute_kelly_bid produces bid in [0, max_cap·reward]
    6. quarter-Kelly default produces SMALLER bids than full Kelly
    7. Open-exchange shaded bid is LOWER than direct (same posterior)
    8. drawdown_aware_pacing_weight zero when mean ≤ 0
    9. normalize_pacing_weights sum to 1 (or all zero)
"""

from __future__ import annotations

import math

import pytest

from adam.intelligence.spine.spine_9_kelly_bid import (
    DEFAULT_KELLY_FRACTION,
    KellyBidResult,
    SupplyPath,
    WINNER_CURSE_SHADING,
    compute_kelly_bid,
    drawdown_aware_pacing_weight,
    fractional_kelly,
    kelly_fraction,
    normalize_pacing_weights,
    winner_curse_shading_factor,
)


# -----------------------------------------------------------------------------
# kelly_fraction
# -----------------------------------------------------------------------------


class TestKellyFraction:

    def test_negative_edge_returns_zero(self):
        # p = 0.4, odds = 1.0 → edge = 0.4·1 - 0.6 = -0.2 → not profitable
        f = kelly_fraction(p_win=0.4, odds=1.0)
        assert f == 0.0

    def test_zero_edge_returns_zero(self):
        # p = 0.5, odds = 1.0 → edge = 0.5·1 - 0.5 = 0 → break-even
        f = kelly_fraction(p_win=0.5, odds=1.0)
        assert f == 0.0

    def test_positive_edge_returns_kelly(self):
        # p = 0.6, odds = 1.0 → edge = 0.6 - 0.4 = 0.2; f = 0.2/1 = 0.2
        f = kelly_fraction(p_win=0.6, odds=1.0)
        assert f == pytest.approx(0.2)

    def test_extreme_edge_clipped_to_one(self):
        # p = 1.0 (certain win), odds = 1.0 → edge = 1 - 0 = 1; f = 1
        f = kelly_fraction(p_win=1.0, odds=1.0)
        assert f == pytest.approx(1.0)

    def test_zero_odds_returns_zero(self):
        f = kelly_fraction(p_win=0.7, odds=0.0)
        assert f == 0.0

    def test_negative_odds_returns_zero(self):
        f = kelly_fraction(p_win=0.7, odds=-1.0)
        assert f == 0.0

    def test_p_win_out_of_range_raises(self):
        with pytest.raises(ValueError, match="p_win"):
            kelly_fraction(p_win=1.5, odds=1.0)
        with pytest.raises(ValueError, match="p_win"):
            kelly_fraction(p_win=-0.1, odds=1.0)


# -----------------------------------------------------------------------------
# fractional_kelly
# -----------------------------------------------------------------------------


class TestFractionalKelly:

    def test_quarter_kelly_default(self):
        f = fractional_kelly(p_win=0.6, odds=1.0)
        # full kelly = 0.2; quarter = 0.05
        assert f == pytest.approx(0.05)

    def test_full_kelly_kappa_one(self):
        f = fractional_kelly(p_win=0.6, odds=1.0, kelly_fraction_kappa=1.0)
        assert f == pytest.approx(0.2)

    def test_half_kelly_kappa(self):
        f = fractional_kelly(p_win=0.6, odds=1.0, kelly_fraction_kappa=0.5)
        assert f == pytest.approx(0.1)

    def test_invalid_kappa_zero_rejected(self):
        with pytest.raises(ValueError, match="kelly_fraction_kappa"):
            fractional_kelly(p_win=0.6, odds=1.0, kelly_fraction_kappa=0.0)

    def test_invalid_kappa_above_one_rejected(self):
        with pytest.raises(ValueError, match="kelly_fraction_kappa"):
            fractional_kelly(p_win=0.6, odds=1.0, kelly_fraction_kappa=1.5)


# -----------------------------------------------------------------------------
# Winner's-curse shading
# -----------------------------------------------------------------------------


class TestWinnerCurseShading:

    def test_open_exchange_highest_shading(self):
        s_open = winner_curse_shading_factor(SupplyPath.OPEN_EXCHANGE)
        s_pmp = winner_curse_shading_factor(SupplyPath.PMP)
        s_deal = winner_curse_shading_factor(SupplyPath.DEAL_ID)
        s_direct = winner_curse_shading_factor(SupplyPath.DIRECT)
        assert s_open > s_pmp > s_deal > s_direct

    def test_direct_no_shading(self):
        assert winner_curse_shading_factor(SupplyPath.DIRECT) == 0.0


# -----------------------------------------------------------------------------
# compute_kelly_bid
# -----------------------------------------------------------------------------


class TestComputeKellyBid:

    def test_zero_reward_zero_bid(self):
        result = compute_kelly_bid(
            p_win=0.6, expected_reward=0.0,
            auction_clearing_estimate=1.0,
        )
        assert result.bid_amount == 0.0

    def test_zero_clearing_zero_bid(self):
        result = compute_kelly_bid(
            p_win=0.6, expected_reward=10.0,
            auction_clearing_estimate=0.0,
        )
        assert result.bid_amount == 0.0

    def test_positive_edge_produces_bid(self):
        # p = 0.5 conversion, reward = $10, clearing = $1.
        # odds = (10-1)/1 = 9
        # full kelly = (0.5·9 - 0.5)/9 = 4/9 ≈ 0.444
        # quarter kelly = 0.111
        # bid = 0.111 · 10 = $1.11 (before shading)
        # OPEN_EXCHANGE shading 0.12 → $0.97
        result = compute_kelly_bid(
            p_win=0.5, expected_reward=10.0,
            auction_clearing_estimate=1.0,
            supply_path=SupplyPath.OPEN_EXCHANGE,
        )
        assert result.bid_amount > 0.0
        assert result.bid_amount < 10.0  # < reward

    def test_quarter_kelly_smaller_than_full(self):
        full = compute_kelly_bid(
            p_win=0.6, expected_reward=10.0,
            auction_clearing_estimate=1.0,
            kelly_fraction_kappa=1.0,
        )
        quarter = compute_kelly_bid(
            p_win=0.6, expected_reward=10.0,
            auction_clearing_estimate=1.0,
            kelly_fraction_kappa=0.25,
        )
        assert quarter.bid_amount < full.bid_amount

    def test_open_exchange_shaded_lower_than_direct(self):
        bid_open = compute_kelly_bid(
            p_win=0.6, expected_reward=10.0,
            auction_clearing_estimate=1.0,
            supply_path=SupplyPath.OPEN_EXCHANGE,
        )
        bid_direct = compute_kelly_bid(
            p_win=0.6, expected_reward=10.0,
            auction_clearing_estimate=1.0,
            supply_path=SupplyPath.DIRECT,
        )
        assert bid_open.bid_amount < bid_direct.bid_amount

    def test_capped_at_max_fraction_of_reward(self):
        # Full kelly with very high edge could bid > max_fraction · reward.
        # Test with extreme p_win.
        result = compute_kelly_bid(
            p_win=0.99, expected_reward=10.0,
            auction_clearing_estimate=0.1,
            supply_path=SupplyPath.DIRECT,  # no shading
            kelly_fraction_kappa=1.0,        # full Kelly
            max_bid_fraction_of_reward=0.3,
        )
        # Bid capped at 0.3 · 10 = $3.00.
        assert result.bid_amount <= 3.0
        assert result.capped_by_max_fraction is True

    def test_zero_edge_zero_bid(self):
        # p=0.5, odds = (10-10)/10 = 0 → no profitable bet.
        # Wait: clearing = reward → odds = 0 (no payoff above clearing).
        result = compute_kelly_bid(
            p_win=0.5, expected_reward=10.0,
            auction_clearing_estimate=10.0,
            supply_path=SupplyPath.DIRECT,
        )
        # With odds = 0, kelly_fraction returns 0; bid = 0.
        assert result.bid_amount == 0.0


# -----------------------------------------------------------------------------
# Drawdown-aware pacing weight
# -----------------------------------------------------------------------------


class TestDrawdownAwarePacingWeight:

    def test_zero_or_negative_mean_zero_weight(self):
        assert drawdown_aware_pacing_weight(
            expected_lift_mean=0.0, expected_lift_stddev=0.1,
        ) == 0.0
        assert drawdown_aware_pacing_weight(
            expected_lift_mean=-0.1, expected_lift_stddev=0.1,
        ) == 0.0

    def test_zero_or_negative_stddev_zero_weight(self):
        assert drawdown_aware_pacing_weight(
            expected_lift_mean=0.5, expected_lift_stddev=0.0,
        ) == 0.0

    def test_higher_mean_higher_weight(self):
        w_low = drawdown_aware_pacing_weight(
            expected_lift_mean=0.1, expected_lift_stddev=0.1,
        )
        w_high = drawdown_aware_pacing_weight(
            expected_lift_mean=0.5, expected_lift_stddev=0.1,
        )
        assert w_high > w_low

    def test_higher_stddev_lower_weight(self):
        """High variance lowers the pacing weight (drawdown-aware:
        less budget allocated to noisy cells)."""
        w_tight = drawdown_aware_pacing_weight(
            expected_lift_mean=0.3, expected_lift_stddev=0.05,
        )
        w_wide = drawdown_aware_pacing_weight(
            expected_lift_mean=0.3, expected_lift_stddev=0.5,
        )
        assert w_tight > w_wide

    def test_kappa_scales_weight(self):
        w_quarter = drawdown_aware_pacing_weight(
            expected_lift_mean=0.3, expected_lift_stddev=0.1,
            kelly_fraction_kappa=0.25,
        )
        w_half = drawdown_aware_pacing_weight(
            expected_lift_mean=0.3, expected_lift_stddev=0.1,
            kelly_fraction_kappa=0.5,
        )
        assert w_half == pytest.approx(2.0 * w_quarter)


class TestNormalizePacingWeights:

    def test_normalizes_to_sum_one(self):
        weights = {"a": 1.0, "b": 2.0, "c": 3.0}
        normalized = normalize_pacing_weights(weights)
        assert sum(normalized.values()) == pytest.approx(1.0)
        assert normalized["c"] > normalized["b"] > normalized["a"]

    def test_all_zero_returns_zeros(self):
        weights = {"a": 0.0, "b": 0.0}
        normalized = normalize_pacing_weights(weights)
        assert normalized == {"a": 0.0, "b": 0.0}

    def test_negative_weights_treated_as_zero(self):
        weights = {"a": -0.5, "b": 1.0}
        normalized = normalize_pacing_weights(weights)
        # a treated as 0; only b has weight.
        assert normalized["a"] == 0.0
        assert normalized["b"] == pytest.approx(1.0)


# -----------------------------------------------------------------------------
# End-to-end: posterior uncertainty drives bid behavior
# -----------------------------------------------------------------------------


class TestEndToEndKellyBidUnderUncertainty:

    def test_uncertain_posterior_low_bid(self):
        """Lower p_win (uncertain conversion) → lower bid."""
        confident = compute_kelly_bid(
            p_win=0.8, expected_reward=10.0,
            auction_clearing_estimate=1.0,
        )
        uncertain = compute_kelly_bid(
            p_win=0.3, expected_reward=10.0,
            auction_clearing_estimate=1.0,
        )
        assert confident.bid_amount > uncertain.bid_amount

    def test_unprofitable_posterior_zero_bid(self):
        """Posterior says don't bid → bid is zero."""
        result = compute_kelly_bid(
            p_win=0.1,            # very unlikely conversion
            expected_reward=2.0,   # low reward
            auction_clearing_estimate=1.0,
        )
        assert result.bid_amount == 0.0
        assert result.kelly_fraction_full == 0.0
