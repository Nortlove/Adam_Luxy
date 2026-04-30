"""Pin Spine #10 — Online Kalman state-space wrapping BONG.

Directive Phase 1 line 998 + § Spine #10 (lines 314-331). Tests pin:

  * Predict preserves μ exactly (random-walk transition is mean-preserving).
  * Predict inflates per-dim variance monotonically with q*dt.
  * q=0 → predict is identity transformation.
  * dt=0 → predict is identity (no time elapsed).
  * predict_then_update == predict followed by BONGUpdater.update.
  * Longer dt → more variance inflation.
  * EB q estimator: noisier residuals → larger q estimate.
  * EB q estimator: empty residuals → fall back to DEFAULT_PROCESS_NOISE_PER_DAY.
  * Numerical guards: NaN q → floored, negative q → floored, q over ceiling
    → clipped.
  * Idle posterior cap: dt clipped to 30 days under per_day units so
    long-idle posteriors don't go to garbage variance.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from adam.intelligence.bong import BONGPosterior, BONGUpdater, MIN_PRECISION
from adam.intelligence.bong_state_space import (
    BONGStateSpaceWrapper,
    DEFAULT_PROCESS_NOISE_PER_DAY,
    DEFAULT_Q_CEILING,
    DEFAULT_Q_FLOOR,
    KalmanStateSpaceConfig,
    SECONDS_PER_DAY,
    make_default_config,
)


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------


def _make_individual(d: int = 5, mean: float = 0.5, precision: float = 4.0):
    """Build a BONGPosterior with known μ = mean and per-dim D = precision."""
    D = np.full(d, precision, dtype=np.float64)
    eta = D * mean  # so that μ = eta / D = mean
    return BONGPosterior(eta=eta, D=D, observation_count=0, last_updated=0.0)


def _wrapper(d: int = 5):
    bong = BONGUpdater(dimension_names=[f"dim_{i}" for i in range(d)])
    bong.initialize_default()
    return BONGStateSpaceWrapper(bong)


# -----------------------------------------------------------------------------
# Config validation — defensive guards
# -----------------------------------------------------------------------------


def test_config_rejects_none_noise():
    with pytest.raises(ValueError):
        KalmanStateSpaceConfig(process_noise_diag=None)  # type: ignore[arg-type]


def test_config_clips_nan_to_floor():
    cfg = KalmanStateSpaceConfig(
        process_noise_diag=np.array([np.nan, 0.001, np.inf, 0.5]),
    )
    assert math.isclose(cfg.process_noise_diag[0], DEFAULT_Q_FLOOR)
    assert math.isclose(cfg.process_noise_diag[1], 0.001)
    # inf clipped to ceiling, not floor
    assert math.isclose(cfg.process_noise_diag[2], DEFAULT_Q_CEILING)
    assert math.isclose(cfg.process_noise_diag[3], 0.5)


def test_config_clips_negative_to_floor():
    cfg = KalmanStateSpaceConfig(
        process_noise_diag=np.array([-0.5, 0.001, -1.0]),
    )
    assert math.isclose(cfg.process_noise_diag[0], DEFAULT_Q_FLOOR)
    assert math.isclose(cfg.process_noise_diag[2], DEFAULT_Q_FLOOR)


def test_config_clips_above_ceiling():
    cfg = KalmanStateSpaceConfig(
        process_noise_diag=np.array([2.0, 100.0, 0.5]),
    )
    assert math.isclose(cfg.process_noise_diag[0], DEFAULT_Q_CEILING)
    assert math.isclose(cfg.process_noise_diag[1], DEFAULT_Q_CEILING)
    assert math.isclose(cfg.process_noise_diag[2], 0.5)


def test_make_default_config_shape_and_values():
    cfg = make_default_config(20)
    assert cfg.process_noise_diag.shape == (20,)
    assert np.allclose(cfg.process_noise_diag, DEFAULT_PROCESS_NOISE_PER_DAY)
    assert cfg.process_noise_units == "per_day"


# -----------------------------------------------------------------------------
# Predict invariants
# -----------------------------------------------------------------------------


def test_predict_preserves_mean_exactly():
    """Random-walk transition is mean-preserving by construction:
    μ' = η'/D' = (D'/D · η) / (D' ) = η/D = μ."""
    wrapper = _wrapper(d=5)
    indiv = _make_individual(d=5, mean=0.7, precision=10.0)
    cfg = KalmanStateSpaceConfig(
        process_noise_diag=np.full(5, 0.01),
        last_predict_ts=0.0,
        process_noise_units="per_touch",
    )
    pre_mu = indiv.eta / indiv.D
    wrapper.predict(indiv, cfg)
    post_mu = indiv.eta / indiv.D
    assert np.allclose(pre_mu, post_mu, atol=1e-10), (
        f"predict shifted mean from {pre_mu} to {post_mu}"
    )


def test_predict_with_zero_q_is_identity():
    """q=0 → forgetting_factor = 1 → no change to (D, eta)."""
    wrapper = _wrapper(d=4)
    indiv = _make_individual(d=4, mean=0.3, precision=8.0)
    cfg = KalmanStateSpaceConfig(
        process_noise_diag=np.full(4, 0.0),  # will be floored to DEFAULT_Q_FLOOR
        process_noise_units="per_touch",
    )
    # Floor at 1e-6 with D=8 and dt=1 → forgetting ≈ 1/(1 + 8e-6) ≈ 1.0
    pre_D = indiv.D.copy()
    pre_eta = indiv.eta.copy()
    wrapper.predict(indiv, cfg)
    assert np.allclose(indiv.D, pre_D, rtol=1e-4)
    assert np.allclose(indiv.eta, pre_eta, rtol=1e-4)


def test_predict_with_zero_dt_is_identity():
    """dt=0 (no time elapsed) → no inflation."""
    wrapper = _wrapper(d=3)
    indiv = _make_individual(d=3, mean=0.4, precision=6.0)
    indiv.last_updated = 1000.0
    cfg = KalmanStateSpaceConfig(
        process_noise_diag=np.full(3, 0.5),
        last_predict_ts=1000.0,
        process_noise_units="per_day",
    )
    pre_D = indiv.D.copy()
    pre_eta = indiv.eta.copy()
    wrapper.predict(indiv, cfg, now_ts=1000.0)  # same wall-clock
    assert np.allclose(indiv.D, pre_D)
    assert np.allclose(indiv.eta, pre_eta)


def test_predict_inflates_variance_monotonically():
    """Variance V = 1/D must strictly increase under positive q*dt."""
    wrapper = _wrapper(d=4)
    indiv = _make_individual(d=4, mean=0.5, precision=10.0)
    cfg = KalmanStateSpaceConfig(
        process_noise_diag=np.full(4, 0.5),
        process_noise_units="per_touch",
    )
    pre_var = 1.0 / indiv.D
    wrapper.predict(indiv, cfg)
    post_var = 1.0 / indiv.D
    assert np.all(post_var > pre_var), "variance must increase under q*dt > 0"


def test_predict_longer_dt_more_inflation():
    """dt=10 days inflates more than dt=1 day for the same q."""
    wrapper = _wrapper(d=3)
    indiv_a = _make_individual(d=3, mean=0.5, precision=10.0)
    indiv_b = _make_individual(d=3, mean=0.5, precision=10.0)
    # last_predict_ts pinned to a real reference; now_ts advances past it
    base_ts = 1_700_000_000.0
    cfg_a = KalmanStateSpaceConfig(
        process_noise_diag=np.full(3, 0.1),
        last_predict_ts=base_ts,
        process_noise_units="per_day",
    )
    cfg_b = KalmanStateSpaceConfig(
        process_noise_diag=np.full(3, 0.1),
        last_predict_ts=base_ts,
        process_noise_units="per_day",
    )
    wrapper.predict(indiv_a, cfg_a, now_ts=base_ts + 1.0 * SECONDS_PER_DAY)
    wrapper.predict(indiv_b, cfg_b, now_ts=base_ts + 10.0 * SECONDS_PER_DAY)

    var_a = 1.0 / indiv_a.D
    var_b = 1.0 / indiv_b.D
    assert np.all(var_b > var_a), (
        "10-day dt must inflate variance more than 1-day dt"
    )


def test_predict_clips_idle_dt_at_30_days():
    """Posterior idle for years → dt clipped to 30 days under per_day."""
    wrapper = _wrapper(d=3)
    indiv_30 = _make_individual(d=3, mean=0.5, precision=10.0)
    indiv_1y = _make_individual(d=3, mean=0.5, precision=10.0)
    base_ts = 1_700_000_000.0
    cfg_30 = KalmanStateSpaceConfig(
        process_noise_diag=np.full(3, 0.05),
        last_predict_ts=base_ts,
        process_noise_units="per_day",
    )
    cfg_1y = KalmanStateSpaceConfig(
        process_noise_diag=np.full(3, 0.05),
        last_predict_ts=base_ts,
        process_noise_units="per_day",
    )
    wrapper.predict(indiv_30, cfg_30, now_ts=base_ts + 30.0 * SECONDS_PER_DAY)
    wrapper.predict(indiv_1y, cfg_1y, now_ts=base_ts + 365.0 * SECONDS_PER_DAY)
    # Post-clip both should match (1y clipped to 30d).
    assert np.allclose(indiv_30.D, indiv_1y.D, rtol=1e-6)


def test_predict_floors_D_at_min_precision():
    """Aggressive q*dt should not push D below MIN_PRECISION."""
    wrapper = _wrapper(d=2)
    indiv = _make_individual(d=2, mean=0.5, precision=10.0)
    base_ts = 1_700_000_000.0
    cfg = KalmanStateSpaceConfig(
        # extreme noise, large dt — should clip at floor anyway, then
        # forgetting_factor ≈ 1/(1 + 10*1.0*30) ≈ 0.0033 → D ≈ 0.033
        process_noise_diag=np.full(2, DEFAULT_Q_CEILING),
        last_predict_ts=base_ts,
        process_noise_units="per_day",
    )
    wrapper.predict(indiv, cfg, now_ts=base_ts + 365.0 * SECONDS_PER_DAY)
    assert np.all(indiv.D >= MIN_PRECISION)


def test_predict_updates_last_predict_ts():
    """After predict, config.last_predict_ts == now_ts."""
    wrapper = _wrapper(d=3)
    indiv = _make_individual(d=3)
    cfg = KalmanStateSpaceConfig(
        process_noise_diag=np.full(3, 0.001),
        last_predict_ts=100.0,
        process_noise_units="per_day",
    )
    wrapper.predict(indiv, cfg, now_ts=200.0)
    assert cfg.last_predict_ts == 200.0


def test_predict_skips_on_shape_mismatch():
    """q.shape != D.shape → predict is a no-op (logs warning)."""
    wrapper = _wrapper(d=4)
    indiv = _make_individual(d=4, mean=0.5, precision=10.0)
    cfg = KalmanStateSpaceConfig(
        process_noise_diag=np.full(7, 0.1),  # wrong size
        process_noise_units="per_touch",
    )
    pre_D = indiv.D.copy()
    pre_eta = indiv.eta.copy()
    wrapper.predict(indiv, cfg)
    assert np.allclose(indiv.D, pre_D)
    assert np.allclose(indiv.eta, pre_eta)


# -----------------------------------------------------------------------------
# Predict + update composition
# -----------------------------------------------------------------------------


def test_predict_then_update_matches_manual_composition():
    """wrapper.predict_then_update == predict + bong.update sequentially."""
    bong = BONGUpdater(dimension_names=[f"d_{i}" for i in range(4)])
    bong.initialize_default()
    wrapper = BONGStateSpaceWrapper(bong)

    indiv_a = _make_individual(d=4, mean=0.4, precision=8.0)
    indiv_b = _make_individual(d=4, mean=0.4, precision=8.0)
    cfg_a = KalmanStateSpaceConfig(
        process_noise_diag=np.full(4, 0.05),
        process_noise_units="per_touch",
    )
    cfg_b = KalmanStateSpaceConfig(
        process_noise_diag=np.full(4, 0.05),
        process_noise_units="per_touch",
    )

    obs = np.array([0.6, 0.7, 0.5, 0.8])

    # Path A: composite call
    wrapper.predict_then_update(
        indiv_a, obs, cfg_a, noise_precision=2.0,
    )
    # Path B: manual sequence
    wrapper.predict(indiv_b, cfg_b)
    bong.update(indiv_b, obs, noise_precision=2.0)

    assert np.allclose(indiv_a.D, indiv_b.D)
    assert np.allclose(indiv_a.eta, indiv_b.eta)


def test_predict_then_update_uses_observed_mask():
    """observed_mask must propagate through wrapper to bong.update."""
    bong = BONGUpdater(dimension_names=[f"d_{i}" for i in range(4)])
    bong.initialize_default()
    wrapper = BONGStateSpaceWrapper(bong)
    indiv = _make_individual(d=4, mean=0.4, precision=8.0)
    cfg = KalmanStateSpaceConfig(
        process_noise_diag=np.full(4, 0.0),  # no inflation
        process_noise_units="per_touch",
    )
    obs = np.array([1.0, 1.0, 1.0, 1.0])
    mask = np.array([True, False, True, False])
    pre_D = indiv.D.copy()
    pre_eta = indiv.eta.copy()
    wrapper.predict_then_update(
        indiv, obs, cfg, noise_precision=1.0, observed_mask=mask,
    )
    # Dimensions where mask=False should be unchanged (modulo the
    # tiny floored q*dt step, which we made zero above).
    assert math.isclose(indiv.D[1], pre_D[1], rel_tol=1e-3)
    assert math.isclose(indiv.D[3], pre_D[3], rel_tol=1e-3)
    # Dimensions where mask=True should have D updated by noise_precision=1.
    assert indiv.D[0] > pre_D[0]
    assert indiv.D[2] > pre_D[2]


# -----------------------------------------------------------------------------
# Empirical-Bayes q estimator
# -----------------------------------------------------------------------------


def test_eb_q_empty_residuals_returns_default():
    wrapper = _wrapper(d=5)
    indiv = _make_individual(d=5)
    q = wrapper.estimate_process_noise_eb(indiv, [], [])
    assert q.shape == (5,)
    assert np.allclose(q, DEFAULT_PROCESS_NOISE_PER_DAY)


def test_eb_q_mismatched_lengths_returns_default():
    wrapper = _wrapper(d=3)
    indiv = _make_individual(d=3)
    residuals = [np.zeros(3)]
    dts = [1.0, 2.0]  # length mismatch
    q = wrapper.estimate_process_noise_eb(indiv, residuals, dts)
    assert q.shape == (3,)
    assert np.allclose(q, DEFAULT_PROCESS_NOISE_PER_DAY)


def test_eb_q_larger_residuals_yield_larger_q():
    """Two cohorts of residuals — larger residuals → larger q estimate."""
    wrapper = _wrapper(d=2)
    indiv_a = _make_individual(d=2, precision=10.0)
    indiv_b = _make_individual(d=2, precision=10.0)

    rng = np.random.default_rng(7)
    quiet = [rng.normal(0.0, 0.05, size=2) for _ in range(20)]
    noisy = [rng.normal(0.0, 0.5, size=2) for _ in range(20)]
    dts = [1.0] * 20

    q_quiet = wrapper.estimate_process_noise_eb(indiv_a, quiet, dts)
    q_noisy = wrapper.estimate_process_noise_eb(indiv_b, noisy, dts)

    # Noisy residuals should produce a larger or equal q than quiet,
    # in at least one dim, by a meaningful margin.
    assert (q_noisy.mean() > q_quiet.mean()), (
        f"expected noisier residuals → larger q, got "
        f"q_quiet={q_quiet} q_noisy={q_noisy}"
    )


def test_eb_q_clipped_to_bounds():
    """Pathological residuals (huge variance) → q clipped at ceiling."""
    wrapper = _wrapper(d=2)
    indiv = _make_individual(d=2, precision=10.0)

    # Huge residuals every touch
    huge = [np.full(2, 100.0) for _ in range(10)]
    dts = [1.0] * 10
    q = wrapper.estimate_process_noise_eb(indiv, huge, dts)
    assert np.all(q <= DEFAULT_Q_CEILING)
    assert np.all(q >= DEFAULT_Q_FLOOR)


def test_eb_q_window_caps_residual_history():
    """Residuals beyond DEFAULT_EB_WINDOW_TOUCHES are dropped from the
    estimate — old prediction errors don't dominate when the cap drops
    them entirely.

    This is the strong form of the cap: build a history where ALL
    noisy residuals are older than the window, and ALL recent residuals
    within the window are quiet. The cap must throw the noisy block
    away, so q reflects the quiet recent residuals only.
    """
    from adam.intelligence.bong_state_space import DEFAULT_EB_WINDOW_TOUCHES
    wrapper = _wrapper(d=2)
    indiv = _make_individual(d=2, precision=10.0)

    rng = np.random.default_rng(11)
    # Old huge-residual block — must be entirely dropped by the window cap
    long_history = [rng.normal(0.0, 5.0, size=2) for _ in range(200)]
    # Recent block — sized exactly to the window so noisy items are dropped
    long_history.extend(
        rng.normal(0.0, 0.05, size=2)
        for _ in range(DEFAULT_EB_WINDOW_TOUCHES)
    )
    dts = [1.0] * len(long_history)
    q = wrapper.estimate_process_noise_eb(indiv, long_history, dts)

    # With only quiet residuals in the cap, q should be at/near floor.
    assert np.all(q <= DEFAULT_Q_CEILING * 0.5), (
        f"window cap failed to drop noisy old residuals; q={q}"
    )
