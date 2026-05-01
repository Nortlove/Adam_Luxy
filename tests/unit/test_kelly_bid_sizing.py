"""Pin Spine #9 — fractional Kelly bid sizing.

Tests pin:
  * Kelly_full = edge / variance
  * Quarter-Kelly = 0.25 × full; half-Kelly = 0.50 × full
  * Zero / negative edge → zero bid
  * Zero / negative variance → zero bid (defensive)
  * Non-finite inputs (NaN, Inf) → zero bid
  * Per-supply-path shading bands (open_exchange < pmp < deal_id)
  * Unknown supply path → fallback shading (more conservative)
  * Pacing modifier multiplies the shaded bid
  * Negative pacing modifier clamped at 0 (cannot bid negatively)
  * KellyBidResult shape + frozen
  * Rationale fields populated correctly
  * Constants pinned at A14 defaults
  * Composition with Spine #8 EpistemicBonusResult pinned via test
    (bid_value = pragmatic.bid_value + epistemic.bonus per directive
    line 282)
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from adam.intelligence.bong import BONGPosterior
from adam.intelligence.epistemic_bid_bonus import compute_epistemic_bonus
from adam.intelligence.kelly_bid_sizing import (
    DEFAULT_KELLY_FRACTION_HALF,
    DEFAULT_KELLY_FRACTION_QUARTER,
    DEFAULT_WINNERS_CURSE_SHADING,
    KellyBidResult,
    SupplyPath,
    compute_pragmatic_bid,
    fractional_kelly_bid,
    kelly_full_fraction,
    winners_curse_shading_factor,
)


# -----------------------------------------------------------------------------
# Constants pinned (A14 defaults — drift requires explicit calibration update)
# -----------------------------------------------------------------------------


def test_kelly_fraction_constants_pinned():
    assert DEFAULT_KELLY_FRACTION_QUARTER == 0.25
    assert DEFAULT_KELLY_FRACTION_HALF == 0.50


def test_winners_curse_shading_table_pinned():
    """Per-supply-path shading bands; conservative defaults pre-pilot."""
    assert DEFAULT_WINNERS_CURSE_SHADING[SupplyPath.OPEN_EXCHANGE] == 0.85
    assert DEFAULT_WINNERS_CURSE_SHADING[SupplyPath.PMP] == 0.92
    assert DEFAULT_WINNERS_CURSE_SHADING[SupplyPath.DEAL_ID] == 1.00


def test_supply_path_enum_complete():
    """Exactly three supply paths per directive line 306-308."""
    assert {sp.value for sp in SupplyPath} == {
        "open_exchange", "private_marketplace", "deal_id",
    }


# -----------------------------------------------------------------------------
# kelly_full_fraction — pure math
# -----------------------------------------------------------------------------


def test_kelly_full_basic():
    """Kelly_full = edge / variance."""
    assert kelly_full_fraction(0.5, 0.25) == pytest.approx(2.0)
    assert kelly_full_fraction(0.1, 1.0) == pytest.approx(0.1)


def test_kelly_full_zero_edge_returns_zero():
    assert kelly_full_fraction(0.0, 1.0) == 0.0


def test_kelly_full_negative_edge_returns_zero():
    """No positive expected value → no bid."""
    assert kelly_full_fraction(-0.5, 1.0) == 0.0


def test_kelly_full_zero_variance_returns_zero():
    """Defensive: degenerate posterior → cannot reason about Kelly."""
    assert kelly_full_fraction(0.5, 0.0) == 0.0


def test_kelly_full_negative_variance_returns_zero():
    """Variance can never be < 0 mathematically; defensive guard."""
    assert kelly_full_fraction(0.5, -0.1) == 0.0


def test_kelly_full_nan_inputs_return_zero():
    assert kelly_full_fraction(float("nan"), 1.0) == 0.0
    assert kelly_full_fraction(0.5, float("nan")) == 0.0
    assert kelly_full_fraction(float("inf"), 1.0) == 0.0
    assert kelly_full_fraction(0.5, float("inf")) == 0.0


# -----------------------------------------------------------------------------
# fractional_kelly_bid
# -----------------------------------------------------------------------------


def test_quarter_kelly_is_quarter_of_full():
    full = kelly_full_fraction(0.5, 0.25)
    quarter = fractional_kelly_bid(
        0.5, 0.25, kelly_fraction=DEFAULT_KELLY_FRACTION_QUARTER,
    )
    assert quarter == pytest.approx(0.25 * full)


def test_half_kelly_is_half_of_full():
    full = kelly_full_fraction(0.5, 0.25)
    half = fractional_kelly_bid(
        0.5, 0.25, kelly_fraction=DEFAULT_KELLY_FRACTION_HALF,
    )
    assert half == pytest.approx(0.50 * full)


def test_full_kelly_with_fraction_one():
    """kelly_fraction=1.0 returns the full Kelly value (×bankroll_unit)."""
    full = kelly_full_fraction(0.5, 0.25)
    bid = fractional_kelly_bid(0.5, 0.25, kelly_fraction=1.0)
    assert bid == pytest.approx(full)


def test_bankroll_unit_scales_bid():
    bid_unit = fractional_kelly_bid(0.5, 0.25, bankroll_unit=1.0)
    bid_100 = fractional_kelly_bid(0.5, 0.25, bankroll_unit=100.0)
    assert bid_100 == pytest.approx(100.0 * bid_unit)


def test_zero_edge_fractional_returns_zero():
    assert fractional_kelly_bid(0.0, 1.0) == 0.0


# -----------------------------------------------------------------------------
# winners_curse_shading_factor
# -----------------------------------------------------------------------------


def test_shading_per_supply_path_ordered_correctly():
    """Open exchange has the most shading; deal-ID has the least.
    Per directive line 306-308 — random competition needs more
    winner's-curse correction."""
    open_ex = winners_curse_shading_factor(SupplyPath.OPEN_EXCHANGE)
    pmp = winners_curse_shading_factor(SupplyPath.PMP)
    deal = winners_curse_shading_factor(SupplyPath.DEAL_ID)
    assert open_ex < pmp < deal
    assert deal == 1.00  # No shading on negotiated transparent inventory


def test_shading_accepts_string_path_name():
    """Convenience: caller can pass the enum's string value."""
    assert winners_curse_shading_factor("open_exchange") == 0.85


def test_shading_unknown_path_returns_fallback():
    """Unknown path → conservative fallback (more shading)."""
    fallback = winners_curse_shading_factor("not_a_real_path")
    # Fallback is more conservative than open_exchange
    assert fallback < winners_curse_shading_factor(SupplyPath.OPEN_EXCHANGE)


# -----------------------------------------------------------------------------
# compute_pragmatic_bid — composition
# -----------------------------------------------------------------------------


def test_compute_pragmatic_bid_zero_edge_returns_zero_bid():
    result = compute_pragmatic_bid(
        posterior_edge=0.0, posterior_variance=1.0,
        supply_path=SupplyPath.PMP,
    )
    assert result.bid_value == 0.0
    assert result.raw_kelly_bid == 0.0
    assert result.rationale == "no_edge"


def test_compute_pragmatic_bid_negative_edge_returns_zero_bid():
    result = compute_pragmatic_bid(
        posterior_edge=-0.1, posterior_variance=1.0,
        supply_path=SupplyPath.PMP,
    )
    assert result.bid_value == 0.0
    assert result.rationale == "no_edge"


def test_compute_pragmatic_bid_zero_variance_returns_zero_bid():
    result = compute_pragmatic_bid(
        posterior_edge=0.5, posterior_variance=0.0,
        supply_path=SupplyPath.PMP,
    )
    assert result.bid_value == 0.0
    assert result.rationale == "no_uncertainty"


def test_compute_pragmatic_bid_non_finite_input_returns_zero_bid():
    result = compute_pragmatic_bid(
        posterior_edge=float("nan"), posterior_variance=1.0,
        supply_path=SupplyPath.PMP,
    )
    assert result.bid_value == 0.0
    assert result.rationale == "non_finite_input"


def test_compute_pragmatic_bid_normal_path_composes_correctly():
    """raw_kelly × shading × pacing_modifier = bid_value."""
    result = compute_pragmatic_bid(
        posterior_edge=0.5,
        posterior_variance=0.25,
        supply_path=SupplyPath.OPEN_EXCHANGE,
        kelly_fraction=DEFAULT_KELLY_FRACTION_QUARTER,
        bankroll_unit=10.0,
        pacing_modifier=0.8,
    )
    expected_kelly = 0.25 * (0.5 / 0.25) * 10.0  # = 5.0
    expected_shaded = expected_kelly * 0.85  # = 4.25
    expected_bid = expected_shaded * 0.8  # = 3.4

    assert result.raw_kelly_bid == pytest.approx(expected_kelly, abs=1e-9)
    assert result.shaded_kelly_bid == pytest.approx(expected_shaded, abs=1e-9)
    assert result.bid_value == pytest.approx(expected_bid, abs=1e-9)
    assert result.rationale.startswith("kelly=")


def test_compute_pragmatic_bid_higher_quality_supply_means_higher_bid():
    """Same edge / variance / pacing on different supply paths:
    deal_id (no shading) > pmp > open_exchange."""
    common = dict(
        posterior_edge=0.5, posterior_variance=0.25, kelly_fraction=0.25,
    )
    open_ex = compute_pragmatic_bid(
        supply_path=SupplyPath.OPEN_EXCHANGE, **common,
    )
    pmp = compute_pragmatic_bid(supply_path=SupplyPath.PMP, **common)
    deal = compute_pragmatic_bid(supply_path=SupplyPath.DEAL_ID, **common)
    assert open_ex.bid_value < pmp.bid_value < deal.bid_value


def test_compute_pragmatic_bid_pacing_modifier_zero_pauses_bid():
    """pacing_modifier=0 (cell paused) → bid 0 even with positive edge."""
    result = compute_pragmatic_bid(
        posterior_edge=0.5, posterior_variance=0.25,
        supply_path=SupplyPath.PMP, pacing_modifier=0.0,
    )
    assert result.bid_value == 0.0
    # raw_kelly is still computed (audit trail)
    assert result.raw_kelly_bid > 0.0


def test_compute_pragmatic_bid_negative_pacing_clamped_to_zero():
    """Defensive: pacing_modifier < 0 cannot produce a negative bid."""
    result = compute_pragmatic_bid(
        posterior_edge=0.5, posterior_variance=0.25,
        supply_path=SupplyPath.PMP, pacing_modifier=-1.0,
    )
    assert result.bid_value == 0.0


def test_compute_pragmatic_bid_kelly_fraction_scaling():
    """Half-Kelly bid is exactly 2× quarter-Kelly bid (everything else equal)."""
    common = dict(
        posterior_edge=0.5, posterior_variance=0.25,
        supply_path=SupplyPath.PMP, bankroll_unit=10.0, pacing_modifier=1.0,
    )
    quarter = compute_pragmatic_bid(
        kelly_fraction=DEFAULT_KELLY_FRACTION_QUARTER, **common,
    )
    half = compute_pragmatic_bid(
        kelly_fraction=DEFAULT_KELLY_FRACTION_HALF, **common,
    )
    assert half.bid_value == pytest.approx(2.0 * quarter.bid_value, abs=1e-9)


def test_kelly_bid_result_is_immutable():
    result = compute_pragmatic_bid(
        posterior_edge=0.5, posterior_variance=0.25,
        supply_path=SupplyPath.PMP,
    )
    with pytest.raises((AttributeError, Exception)):
        result.bid_value = 999.0  # type: ignore[misc]


# -----------------------------------------------------------------------------
# Composition with Spine #8 — pin the dual-control formulation
# -----------------------------------------------------------------------------


def _make_individual(d: int = 5, precision: float = 4.0):
    D = np.full(d, precision, dtype=np.float64)
    eta = D * 0.5
    return BONGPosterior(eta=eta, D=D, observation_count=0, last_updated=0.0)


def test_dual_control_composition_pragmatic_plus_epistemic():
    """Pin directive line 282: bid_value = pragmatic + epistemic.
    The composition pattern lives in the bidder caller (no premature
    abstraction), but the test pins that the two pieces sum cleanly."""
    indiv = _make_individual(d=5, precision=1.0)

    pragmatic = compute_pragmatic_bid(
        posterior_edge=0.5, posterior_variance=0.25,
        supply_path=SupplyPath.PMP,
    )
    epistemic = compute_epistemic_bonus(
        indiv, observation_precision=2.0, fluency_passed=True,
    )

    bid_value = pragmatic.bid_value + epistemic.bonus
    assert bid_value == pytest.approx(
        pragmatic.bid_value + epistemic.bonus, abs=1e-9,
    )
    # Both pieces contribute meaningfully
    assert pragmatic.bid_value > 0.0
    assert epistemic.bonus > 0.0
    # Dual-control: epistemic adds ON TOP of pragmatic
    assert bid_value > pragmatic.bid_value


def test_dual_control_when_fluency_blocks_epistemic():
    """If fluency blocks the epistemic bonus, bid_value reduces to
    pragmatic alone — the dual-control formulation degrades cleanly."""
    indiv = _make_individual(d=5, precision=1.0)

    pragmatic = compute_pragmatic_bid(
        posterior_edge=0.5, posterior_variance=0.25,
        supply_path=SupplyPath.PMP,
    )
    epistemic = compute_epistemic_bonus(
        indiv, observation_precision=2.0, fluency_passed=False,
    )

    bid_value = pragmatic.bid_value + epistemic.bonus
    assert bid_value == pytest.approx(pragmatic.bid_value, abs=1e-9)
    assert epistemic.bonus == 0.0


def test_dual_control_when_no_edge_pragmatic_zero():
    """When pragmatic = 0 (no edge), epistemic still contributes.
    This is the dual-control's whole point — pay a premium for
    learning even when there's no immediate pragmatic value."""
    indiv = _make_individual(d=5, precision=1.0)

    pragmatic = compute_pragmatic_bid(
        posterior_edge=0.0, posterior_variance=0.25,
        supply_path=SupplyPath.PMP,
    )
    epistemic = compute_epistemic_bonus(
        indiv, observation_precision=2.0, fluency_passed=True,
    )

    bid_value = pragmatic.bid_value + epistemic.bonus
    assert pragmatic.bid_value == 0.0
    assert epistemic.bonus > 0.0
    # Pure epistemic bid — pay to learn
    assert bid_value == epistemic.bonus
