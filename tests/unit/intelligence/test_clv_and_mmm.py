"""Pin E3 — CLV (BTYD) + MMM (adstock + Hill saturation) substrates.

Discipline anchors:
    - Adstock + Hill are CANONICAL deterministic transforms. Tests
      pin numerical anchors so a future refactor can't silently shift
      them. A drift in adstock would silently misattribute carryover;
      a drift in Hill would silently misattribute saturation.
    - Both fitters raise *LibsMissingError when libs unavailable.
      Returning None on missing libs would let investor-facing
      reports consume meaningless CLV / ROI silently — exact drift
      pattern we exist to prevent.
    - NO INVENTED MAGNITUDES. The substrate computes per-archetype
      CLV from real data; it does NOT bake in 'Status Seekers have
      Nx CLV' magnitudes. Those land when fits run on actual outcome
      rows.
"""

from __future__ import annotations

import math
from unittest.mock import MagicMock, patch

import pytest

from adam.intelligence.clv_model import (
    CLVLibsMissingError,
    CLVPrediction,
    TransactionRow,
    fit_clv_for_archetype,
    fit_clv_per_archetype,
    load_transactions_from_neo4j,
)
from adam.intelligence.mmm_model import (
    MMMLibsMissingError,
    adstock_geometric,
    adstock_then_hill,
    channel_response_curve,
    fit_mmm,
    hill_saturation,
)


# =============================================================================
# Adstock — canonical formula behavior
# =============================================================================


def test_adstock_zero_carryover_passes_through():
    """λ=0 → no memory → adstocked == input."""
    impressions = [100.0, 200.0, 50.0, 0.0]
    result = adstock_geometric(impressions, carryover_rate=0.0)
    assert result == impressions


def test_adstock_full_carryover_is_running_sum():
    """λ=1 → infinite memory → cumulative sum."""
    impressions = [100.0, 200.0, 50.0]
    result = adstock_geometric(impressions, carryover_rate=1.0)
    assert result == [100.0, 300.0, 350.0]


def test_adstock_half_carryover_canonical_anchor():
    """λ=0.5: x_adstocked[t] = x[t] + 0.5·x_adstocked[t-1].
    For [100, 200, 50]: [100, 250, 175]. Pin numerical."""
    result = adstock_geometric([100.0, 200.0, 50.0], carryover_rate=0.5)
    assert result == [100.0, 250.0, 175.0]


def test_adstock_validates_carryover_rate():
    with pytest.raises(ValueError, match="carryover_rate"):
        adstock_geometric([100.0], carryover_rate=1.5)
    with pytest.raises(ValueError, match="carryover_rate"):
        adstock_geometric([100.0], carryover_rate=-0.1)


def test_adstock_empty_input_returns_empty():
    assert adstock_geometric([], carryover_rate=0.5) == []


def test_adstock_decay_anchor():
    """A single impulse at t=0, then zeros: should decay geometrically.
    [100, 0, 0, 0] with λ=0.5: [100, 50, 25, 12.5]."""
    result = adstock_geometric([100.0, 0.0, 0.0, 0.0], carryover_rate=0.5)
    assert result == [100.0, 50.0, 25.0, 12.5]


# =============================================================================
# Hill saturation — canonical formula behavior
# =============================================================================


def test_hill_at_zero_is_zero():
    """f(0) = 0 by definition (no spend → no response)."""
    assert hill_saturation(0.0, half_saturation=100.0, slope=1.5) == 0.0


def test_hill_at_half_saturation_is_half():
    """f(θ) = θ^k / (θ^k + θ^k) = 1/2. Anchor regardless of slope."""
    for k in [0.5, 1.0, 1.5, 2.0]:
        assert hill_saturation(100.0, half_saturation=100.0, slope=k) == pytest.approx(0.5)


def test_hill_approaches_one_for_large_x():
    """As x → ∞, f(x) → 1. Pin: at 100× half-saturation, very close to 1."""
    result = hill_saturation(10000.0, half_saturation=100.0, slope=1.5)
    assert result > 0.999


def test_hill_negative_input_returns_zero():
    """Saturation defined for x ≥ 0. Negative input → 0."""
    assert hill_saturation(-50.0, half_saturation=100.0, slope=1.5) == 0.0


def test_hill_validates_positive_half_saturation():
    with pytest.raises(ValueError, match="half_saturation"):
        hill_saturation(100.0, half_saturation=0.0, slope=1.5)
    with pytest.raises(ValueError, match="half_saturation"):
        hill_saturation(100.0, half_saturation=-10.0, slope=1.5)


def test_hill_validates_positive_slope():
    with pytest.raises(ValueError, match="slope"):
        hill_saturation(100.0, half_saturation=100.0, slope=0.0)


def test_hill_higher_slope_steeper_curve():
    """Slope k controls curve shape. At x = θ/2, higher k means
    smaller f (steeper transition near θ)."""
    half = 100.0
    x_below = 50.0  # below half-saturation
    f_low_k = hill_saturation(x_below, half, slope=0.5)
    f_high_k = hill_saturation(x_below, half, slope=3.0)
    # Below half-saturation, higher k should give SMALLER response
    # (sigmoidal vs Michaelis-Menten)
    assert f_high_k < f_low_k


# =============================================================================
# Composed adstock-then-hill
# =============================================================================


def test_adstock_then_hill_composition():
    """First adstock, then Hill. Order matters: applying Hill first
    would compress before the carryover sums.

    [100, 100], λ=0.5, θ=100, k=1.5:
        adstocked = [100, 150]
        hill = [hill(100, 100, 1.5), hill(150, 100, 1.5)]
              = [0.5, ~0.648]
    """
    result = adstock_then_hill(
        [100.0, 100.0],
        carryover_rate=0.5, half_saturation=100.0, slope=1.5,
    )
    assert result[0] == pytest.approx(0.5)
    # 150^1.5 / (150^1.5 + 100^1.5) = ~1837 / (1837 + 1000) = ~0.6479
    assert result[1] == pytest.approx(0.6479, abs=0.001)


# =============================================================================
# MMM Bayesian fit — soft-import gate
# =============================================================================


def test_fit_mmm_raises_libs_missing_when_pymc_unavailable():
    with patch(
        "adam.intelligence.mmm_model._try_import_pymc",
        return_value=None,
    ):
        with pytest.raises(MMMLibsMissingError):
            fit_mmm(
                channel_data={"social_proof": [100.0, 200.0]},
                outcome=[10.0, 20.0],
            )


def test_fit_mmm_validates_shapes():
    """outcome length and per-channel data length must match. Pre-empt
    the PyMC graph build; raise ValueError BEFORE the lib check."""
    with pytest.raises(ValueError, match="outcome"):
        fit_mmm(
            channel_data={"social_proof": [100.0, 200.0, 50.0]},
            outcome=[10.0, 20.0],  # length 2, channel has length 3
        )


def test_fit_mmm_rejects_empty_inputs():
    with pytest.raises(ValueError):
        fit_mmm(channel_data={}, outcome=[10.0])
    with pytest.raises(ValueError):
        fit_mmm(channel_data={"a": [100.0]}, outcome=[])


# =============================================================================
# Channel response curve — visualization helper
# =============================================================================


def test_channel_response_curve_returns_pairs():
    """Returns list of (spend, response) pairs for each input level."""
    spend_levels = [0.0, 100.0, 500.0, 1000.0, 5000.0]
    curve = channel_response_curve(
        spend_levels,
        carryover_rate=0.5, half_saturation=1000.0, slope=1.5,
    )
    assert len(curve) == 5
    assert all(len(pair) == 2 for pair in curve)
    # First pair: spend=0, response=0
    assert curve[0] == (0.0, 0.0)
    # At half-saturation (1000), response should be ~0.5
    half_sat_pair = next(p for p in curve if p[0] == 1000.0)
    assert half_sat_pair[1] == pytest.approx(0.5)


def test_channel_response_curve_monotonic():
    """Response should be monotonically non-decreasing with spend."""
    spend_levels = [0.0, 100.0, 500.0, 1000.0, 5000.0]
    curve = channel_response_curve(
        spend_levels,
        carryover_rate=0.5, half_saturation=1000.0, slope=1.5,
    )
    responses = [r for _, r in curve]
    for i in range(1, len(responses)):
        assert responses[i] >= responses[i - 1]


# =============================================================================
# CLV fitter — soft-import gate
# =============================================================================


def _row(buyer_id: str, archetype: str, freq: int = 5,
         recency: float = 100.0, T: float = 200.0,
         monetary: float = 50.0) -> TransactionRow:
    return TransactionRow(
        buyer_id=buyer_id, archetype=archetype,
        frequency=freq, recency=recency, T=T,
        monetary_value=monetary,
    )


def test_clv_raises_libs_missing_when_lifetimes_unavailable():
    """fit_clv_for_archetype raises CLVLibsMissingError when
    `lifetimes` isn't installed AND there are enough buyers to
    attempt a fit."""
    rows = [_row(f"b{i}", "status_seeker") for i in range(50)]
    with patch(
        "adam.intelligence.clv_model._try_import_lifetimes",
        return_value=None,
    ):
        with pytest.raises(CLVLibsMissingError):
            fit_clv_for_archetype(rows, min_buyers=30)


def test_clv_returns_empty_below_min_buyers():
    """Below min_buyers: skip fit (don't raise). Returns ([], None)
    so the per-archetype orchestrator records as 'skipped_low_n'."""
    rows = [_row(f"b{i}", "status_seeker") for i in range(10)]
    preds, agg = fit_clv_for_archetype(rows, min_buyers=30)
    assert preds == []
    assert agg is None


def test_clv_returns_empty_on_no_repeat_buyers():
    """BG/NBD requires frequency >= 1 (repeat buyers). Buyers with
    frequency=0 are excluded; if none qualify, return empty without
    attempting fit."""
    rows = [
        _row(f"b{i}", "status_seeker", freq=0)
        for i in range(50)
    ]
    preds, agg = fit_clv_for_archetype(rows, min_buyers=30)
    assert preds == []
    assert agg is None


def test_clv_per_archetype_orchestrator_handles_missing_libs():
    """fit_clv_per_archetype raises CLVLibsMissingError when lifetimes
    isn't installed AND any archetype has enough data."""
    rows = (
        [_row(f"a{i}", "status_seeker") for i in range(50)]
        + [_row(f"b{i}", "easy_decider") for i in range(50)]
    )
    with patch(
        "adam.intelligence.clv_model._try_import_lifetimes",
        return_value=None,
    ):
        with pytest.raises(CLVLibsMissingError):
            fit_clv_per_archetype(rows, min_buyers_per_archetype=30)


def test_clv_per_archetype_skips_low_n_archetypes():
    """When some archetypes have < min_buyers, they're recorded as
    'skipped_low_n' in diagnostics. Other archetypes proceed normally."""
    rows = (
        [_row(f"a{i}", "status_seeker") for i in range(50)]    # enough
        + [_row(f"b{i}", "rare_archetype") for i in range(5)]   # too few
    )
    # With lifetimes mocked-missing, the WHOLE thing fails on the
    # status_seeker fit. So we test the low-n path with rows that
    # only contain insufficient archetypes:
    sparse = [_row(f"b{i}", "rare_archetype") for i in range(5)]
    preds, aggs, diag = fit_clv_per_archetype(
        sparse, min_buyers_per_archetype=30,
    )
    assert preds == {}
    assert aggs == {}
    assert diag.archetypes_skipped_low_n == 1


# =============================================================================
# Data loader — soft-fail on missing driver
# =============================================================================


def test_load_transactions_returns_empty_on_no_driver():
    rows = load_transactions_from_neo4j(driver=None)
    assert rows == []


# =============================================================================
# Discipline check: no invented archetype CLV magnitudes
# =============================================================================


def test_no_baked_archetype_clv_magnitudes_in_substrate():
    """Search the source for any constant claim like 'Status Seekers
    have Nx CLV' that would be drift. The substrate must compute CLV
    from data; it must NOT pre-bake the differentiation magnitudes
    investors will care about."""
    import adam.intelligence.clv_model as clv
    import inspect
    source = inspect.getsource(clv)

    # Drift trip-wires: phrasings that would indicate baked
    # differentiation magnitudes
    forbidden_phrases = [
        "status_seeker.*=.*\\d+\\.\\d+",  # = a number for status_seeker
        "lifetime_value_multiplier",
        "archetype_clv_baseline",
    ]
    import re
    for pattern in forbidden_phrases:
        if re.search(pattern, source, re.IGNORECASE):
            raise AssertionError(
                f"clv_model.py contains pattern '{pattern}' suggesting "
                f"baked archetype CLV magnitudes. The substrate must "
                f"compute these from data, not pre-bake them."
            )
