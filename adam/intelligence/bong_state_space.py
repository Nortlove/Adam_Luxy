# =============================================================================
# Spine #10 — Online Kalman / State-Space Personalization wrapping BONG
# Location: adam/intelligence/bong_state_space.py
# =============================================================================
"""Kalman state-space layer over BONG natural-gradient updates.

Closes directive Phase 1 line 998 + §"Spine #10 — Online Kalman-Filter /
State-Space Personalization" (directive lines 314-331). Self-contained
slice — does not depend on Loop B or HMM cohorts (Spine #7).

WHY THIS EXISTS
---------------

The directive's diagnosis (§ Spine #10): per-user mechanism-effect
parameters drift over time (mood, day-of-week, life-event transitions).
BONG (Spine #1) gives the within-time-slice posterior structure — exact
Bayesian addition in natural parameters — but it has no model of state
evolution between observations. Without state-space drift modeling,
posteriors lock onto stale evidence and cannot transition when the
user evolves. Stationary priors are wrong in B2B-travel where intent
is event-driven.

The Kalman layer is the missing transition model:
    State:        θ_i,t  = 20-dim per-user posterior mean at time t
    Transition:   θ_i,t+1 = θ_i,t + ε_t,  ε_t ~ N(0, Q_i)
    Observation:  each impression conditions on θ_i,t (via BONG)
    Forgetting:   Q_i is itself in a hyperprior — large = non-stationary

Integration with BONG (directive line 329): the Kalman prediction step
runs **between observations** and inflates the precision matrix by Q_i⁻¹
(equivalently: inflates the covariance by Q_i). On the next observation,
BONG performs its natural-gradient update on the inflated prior. The
mean is preserved by the prediction step (it's a random-walk transition,
not a deterministic shift) — only uncertainty grows.

DIAGONAL-ONLY FORMULATION (this slice)
--------------------------------------

We use a diagonal Q_i, which is the load-bearing part of the directive's
"trivially storable per user" claim at 20-dim construct space and is
also what every comparable piece of substrate already in the codebase
uses (``session_state.SessionStateTracker``, ``predictive_processing.
update_belief``, ``graph_state_inference._precision_weighted_fusion``).
Full-covariance Q_i is named as a future slice.

The diagonal-only Kalman predict step in natural parameters:

    Posterior covariance:    Σ = Λ⁻¹ ≈ D⁻¹      (diagonal-dominant)
    Add process noise Q:     Σ' = Σ + Q · dt
    Convert back:            D' = 1 / (Σ + Q · dt) = D / (1 + D · q · dt)
    Preserve mean μ = η/D:   η' = D' · μ = (D'/D) · η

So per dimension:
    forgetting_factor[i]  = 1 / (1 + D[i] · q[i] · dt)
    D[i]   ← D[i] · forgetting_factor[i]
    η[i]   ← η[i] · forgetting_factor[i]
    last_predict_ts ← now

This:
  * Preserves μ (BONG-recoverable mean is unchanged by predict alone).
  * Monotonically increases per-dim variance.
  * Recovers the identity transformation when q · dt → 0 (no drift).
  * Is O(d) — same complexity as BONG's update.
  * Respects the natural-parameter discipline (no detour through Σ).

EMPIRICAL-BAYES q ESTIMATOR
---------------------------

The directive (line 327) says Q_i should be learned per user via
empirical Bayes. We implement a recursive Bayesian update on the
process noise scale: given residual prediction errors over a recent
window, the unexplained variance not absorbed by the current posterior
variance is attributed to Q.

For dimension i:
    residual[t]      = observation[t] - μ[t-]            (pre-update mean)
    explained_var[i] = current per-dim posterior variance D⁻¹[i]
    total_var[i]     ≈ EMA(residual[i]²) over window
    q_hat[i]         = max(0, total_var[i] - explained_var[i]) / dt_window

Calibration-pending: window size, EMA half-life, and minimum q-floor
are conservative defaults; LUXY pilot data will calibrate.

DISCIPLINE (B3-LUXY a/b/c/d)
----------------------------

(a) Citation: Kalman 1960 (linear-Gaussian state-space filter); Titsias
    et al. 2014/2017 variational state-space (the directive's named
    precedent). Standard mean-preserving variance-inflation derivation
    for natural-parameter representations of MVN under additive
    process noise (West & Harrison, "Bayesian Forecasting and Dynamic
    Models" §2.4).

(b) Tests pin: predict preserves μ exactly; predict inflates per-dim
    variance monotonically with q*dt; predict with q=0 is identity;
    predict_then_update produces the same posterior as predict followed
    by BONG.update; dt-awareness (longer dt → more inflation); EB
    estimator recovers larger q on noisier residuals; soft-fail without
    config.

(c) calibration_pending=True. Defaults:
      DEFAULT_PROCESS_NOISE_PER_DAY = 0.001  (1‰ variance per day)
      DEFAULT_EB_WINDOW_TOUCHES     = 30
      DEFAULT_EB_EMA_HALF_LIFE      = 14    (touches)
      DEFAULT_Q_FLOOR               = 1e-6
      DEFAULT_Q_CEILING             = 1.0
    A14 flag: BONG_STATE_SPACE_PROCESS_NOISE_PILOT_PENDING.

(d) Honest tags — what is NOT in this slice (named successors):

    * Full-covariance Q_i — the directive lines 318+ explicitly note that
      27-dim full-covariance Kalman is storable per user. We ship the
      diagonal first; full-covariance composes via Woodbury once
      validated.
    * Particle-filter fallback for non-Gaussian residuals (directive
      line 318) — Kalman is the linear-Gaussian path; particle filter
      handles long-tail / multi-modal / discrete state.
    * Learned forgetting from posterior-predictive (full hierarchical
      Bayes update on Q itself) — we ship the residual-EB approximation
      first; the hierarchical version composes with Spine #1 nightly.
    * State-space layer for the per-mechanism Beta posteriors in
      ``UserPosteriorProfile.mechanism_posteriors`` — currently this
      slice is the BONG (alignment-dim) wrapper; the per-mechanism
      Kalman wrapper is a separate sibling slice.

DECISION-TIME CONSUMER
----------------------

  * Cascade hot path: any caller that holds a per-individual
    ``BONGPosterior`` and wants to apply a fresh observation should
    route through ``BONGStateSpaceWrapper.predict_then_update`` rather
    than directly through ``BONGUpdater.update`` — the predict step
    silently inflates variance for the elapsed time since
    ``last_predict_ts``.
  * The wrapper is opt-in: when ``predict_then_update`` is not used,
    BONG behaves identically to its unwrapped self (no drift
    modeling). This preserves the existing call sites bit-for-bit.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Iterable, List, Optional

import numpy as np

from adam.intelligence.bong import BONGPosterior, BONGUpdater, MIN_PRECISION

logger = logging.getLogger(__name__)


# Calibration-pending defaults — see § Discipline (c).
DEFAULT_PROCESS_NOISE_PER_DAY: float = 0.001
DEFAULT_EB_WINDOW_TOUCHES: int = 30
DEFAULT_EB_EMA_HALF_LIFE: float = 14.0
DEFAULT_Q_FLOOR: float = 1e-6
DEFAULT_Q_CEILING: float = 1.0
SECONDS_PER_DAY: float = 86400.0


@dataclass
class KalmanStateSpaceConfig:
    """Per-user (or per-cohort) state-space drift configuration.

    Attributes:
        process_noise_diag: shape (d,) — diagonal of Q_i. Variance added
            *per day* per dimension. ``0.001`` corresponds to ~0.001
            variance increase per dim per day (very slow drift). Per
            second the actual added variance is
            ``process_noise_diag * (dt_seconds / SECONDS_PER_DAY)``.
        last_predict_ts: epoch seconds — the last time ``predict`` ran
            for this individual. Updated by ``predict``. ``0.0``
            interpreted as "use BONGPosterior.last_updated" on first
            predict call (avoids first-touch overshoot).
        process_noise_units: free-text label for diagnostics ("per_day",
            "per_touch"). Default "per_day". When "per_touch", dt is
            counted as 1 per call regardless of wall-clock — useful for
            test determinism and for environments without reliable
            timestamps.
    """

    process_noise_diag: np.ndarray
    last_predict_ts: float = 0.0
    process_noise_units: str = "per_day"

    def __post_init__(self) -> None:
        # Numerical guards on the noise vector: NaN/negative → floor.
        if self.process_noise_diag is None:
            raise ValueError(
                "KalmanStateSpaceConfig.process_noise_diag must be provided",
            )
        arr = np.asarray(self.process_noise_diag, dtype=np.float64)
        # NaN is ambiguous (no signal) → floor to safe slow-drift default.
        # ±inf is unambiguous (very large) → let clip pin to ceiling.
        arr = np.where(np.isnan(arr), DEFAULT_Q_FLOOR, arr)
        arr = np.clip(arr, DEFAULT_Q_FLOOR, DEFAULT_Q_CEILING)
        self.process_noise_diag = arr


@dataclass
class StateSpaceDiagnostics:
    """Summary of one predict step — for logging / observability."""

    elapsed_seconds: float = 0.0
    forgetting_factor_min: float = 1.0
    forgetting_factor_max: float = 1.0
    pre_predict_variance_mean: float = 0.0
    post_predict_variance_mean: float = 0.0


def make_default_config(d: int) -> KalmanStateSpaceConfig:
    """Build a ``KalmanStateSpaceConfig`` with directive-default per-day
    noise on each of ``d`` dimensions.

    Convenience for cold-start users (no per-user EB estimate yet).
    """
    return KalmanStateSpaceConfig(
        process_noise_diag=np.full(d, DEFAULT_PROCESS_NOISE_PER_DAY),
        last_predict_ts=0.0,
        process_noise_units="per_day",
    )


class BONGStateSpaceWrapper:
    """Kalman state-space layer wrapping a ``BONGUpdater``.

    Composition:
        wrapper = BONGStateSpaceWrapper(bong_updater)
        wrapper.predict(individual, config)              # between observations
        wrapper.predict_then_update(...)                 # observation arrival

    The wrapper is opt-in. Existing call sites that route through
    ``BONGUpdater.update`` directly continue to work unchanged.
    """

    def __init__(self, bong_updater: BONGUpdater) -> None:
        self.bong = bong_updater

    # ------------------------------------------------------------------
    # Predict — inflate variance for elapsed time
    # ------------------------------------------------------------------

    def predict(
        self,
        individual: BONGPosterior,
        config: KalmanStateSpaceConfig,
        now_ts: Optional[float] = None,
    ) -> StateSpaceDiagnostics:
        """Run the Kalman prediction step — mean-preserving variance growth.

        Mutates ``individual.D`` and ``individual.eta`` in place such
        that the recovered mean ``μ = η/D`` is unchanged (per dim) but
        the per-dim posterior variance grows by ``q * dt``.

        Args:
            individual: ``BONGPosterior`` to advance.
            config: per-user drift config. ``last_predict_ts`` is updated
                to ``now_ts`` after the predict step.
            now_ts: epoch seconds. Defaults to ``time.time()``.

        Returns: ``StateSpaceDiagnostics`` summarizing the predict step.
        """
        diagnostics = StateSpaceDiagnostics()

        # Compute elapsed time in the configured units.
        now = float(now_ts) if now_ts is not None else time.time()
        if config.process_noise_units == "per_touch":
            dt = 1.0
        else:
            # "per_day" → dt in days
            ref_ts = config.last_predict_ts
            if ref_ts <= 0.0:
                # First predict — fall back to the individual's
                # last_updated to avoid overshooting the very first step.
                ref_ts = (
                    individual.last_updated
                    if individual.last_updated > 0.0
                    else now
                )
            dt_seconds = max(0.0, now - ref_ts)
            diagnostics.elapsed_seconds = dt_seconds
            dt = dt_seconds / SECONDS_PER_DAY

        # Clip dt to a sane upper bound so a posterior that's been
        # idle for years doesn't get its variance inflated to garbage.
        # 30 days is well past any realistic retargeting window.
        if config.process_noise_units == "per_day":
            dt = min(dt, 30.0)

        # Pre-predict variance mean for diagnostics.
        try:
            pre_var = 1.0 / np.maximum(individual.D, MIN_PRECISION)
            diagnostics.pre_predict_variance_mean = float(pre_var.mean())
        except Exception:
            pass

        if dt <= 0.0:
            # No time elapsed — predict is the identity.
            config.last_predict_ts = now
            try:
                diagnostics.post_predict_variance_mean = (
                    diagnostics.pre_predict_variance_mean
                )
            except Exception:
                pass
            return diagnostics

        # Per-dim mean-preserving inflation.
        # forgetting_factor = 1 / (1 + D * q * dt)
        q_arr = np.asarray(config.process_noise_diag, dtype=np.float64)
        if q_arr.shape[0] != individual.D.shape[0]:
            logger.warning(
                "predict skipped — q shape %s != individual.D shape %s",
                q_arr.shape, individual.D.shape,
            )
            config.last_predict_ts = now
            return diagnostics

        forgetting = 1.0 / (1.0 + individual.D * q_arr * dt)
        forgetting = np.clip(forgetting, 1e-12, 1.0)

        diagnostics.forgetting_factor_min = float(forgetting.min())
        diagnostics.forgetting_factor_max = float(forgetting.max())

        individual.D = individual.D * forgetting
        individual.eta = individual.eta * forgetting
        # Floor to avoid sub-MIN_PRECISION D values upstream Woodbury
        # uses; this is the same floor BONG itself enforces.
        individual.D = np.maximum(individual.D, MIN_PRECISION)
        individual.last_updated = now

        try:
            post_var = 1.0 / np.maximum(individual.D, MIN_PRECISION)
            diagnostics.post_predict_variance_mean = float(post_var.mean())
        except Exception:
            pass

        config.last_predict_ts = now
        return diagnostics

    # ------------------------------------------------------------------
    # Predict + update — the directive's wrapping operation
    # ------------------------------------------------------------------

    def predict_then_update(
        self,
        individual: BONGPosterior,
        observation: np.ndarray,
        config: KalmanStateSpaceConfig,
        noise_precision: float = 1.0,
        observed_mask: Optional[np.ndarray] = None,
        now_ts: Optional[float] = None,
    ) -> BONGPosterior:
        """Run predict then BONG.update — the canonical observation entry.

        Equivalent to:
            wrapper.predict(individual, config, now_ts)
            return bong.update(individual, observation, noise_precision,
                               observed_mask)

        Returns the (mutated) individual.
        """
        self.predict(individual, config, now_ts=now_ts)
        return self.bong.update(
            individual, observation,
            noise_precision=noise_precision,
            observed_mask=observed_mask,
        )

    # ------------------------------------------------------------------
    # Empirical-Bayes q estimator
    # ------------------------------------------------------------------

    def estimate_process_noise_eb(
        self,
        individual: BONGPosterior,
        residuals: Iterable[np.ndarray],
        elapsed_per_residual: Iterable[float],
        ema_half_life: float = DEFAULT_EB_EMA_HALF_LIFE,
    ) -> np.ndarray:
        """Recursive-EB process-noise estimate from recent residuals.

        Args:
            individual: posterior whose explained variance is subtracted
                from the residual variance.
            residuals: iterable of (d,) residual vectors
                (observation - pre-update μ) collected across recent
                touches.
            elapsed_per_residual: per-residual elapsed time in the
                config's units (days for "per_day", touches for
                "per_touch"). Aligned 1:1 with ``residuals``.
            ema_half_life: EMA half-life (touches). Smaller = more
                responsive to recent change; larger = smoother.

        Returns: shape (d,) estimated process noise diagonal, clipped to
        [DEFAULT_Q_FLOOR, DEFAULT_Q_CEILING].

        Soft-fail discipline: empty residuals → return DEFAULT-noise
        vector matching ``individual.D.shape[0]``.
        """
        d = int(individual.D.shape[0])
        residual_list = [np.asarray(r, dtype=np.float64) for r in residuals]
        dt_list = [float(x) for x in elapsed_per_residual]

        if not residual_list or not dt_list:
            return np.full(d, DEFAULT_PROCESS_NOISE_PER_DAY)

        if len(residual_list) != len(dt_list):
            logger.warning(
                "EB q skipped — residuals=%d != dts=%d",
                len(residual_list), len(dt_list),
            )
            return np.full(d, DEFAULT_PROCESS_NOISE_PER_DAY)

        # Window cap to keep the estimator bounded.
        if len(residual_list) > DEFAULT_EB_WINDOW_TOUCHES:
            residual_list = residual_list[-DEFAULT_EB_WINDOW_TOUCHES:]
            dt_list = dt_list[-DEFAULT_EB_WINDOW_TOUCHES:]

        # EMA decay weight per residual (most recent = largest).
        # decay per step = 0.5 ** (1 / ema_half_life)
        decay = 0.5 ** (1.0 / max(ema_half_life, 1e-6))

        # Build EMA of squared residuals per dimension and EMA of dt.
        ema_resid_sq = np.zeros(d, dtype=np.float64)
        ema_dt = 0.0
        weight_sum = 0.0
        for offset, (r, dt) in enumerate(reversed(list(zip(residual_list, dt_list)))):
            w = decay ** offset
            if r.shape[0] != d:
                continue
            ema_resid_sq += w * (r * r)
            ema_dt += w * max(dt, 1e-9)
            weight_sum += w

        if weight_sum <= 0.0 or ema_dt <= 0.0:
            return np.full(d, DEFAULT_PROCESS_NOISE_PER_DAY)

        residual_var = ema_resid_sq / weight_sum
        avg_dt = ema_dt / weight_sum

        explained_var = 1.0 / np.maximum(individual.D, MIN_PRECISION)
        unexplained = np.clip(residual_var - explained_var, 0.0, None)
        q_hat = unexplained / max(avg_dt, 1e-9)

        return np.clip(q_hat, DEFAULT_Q_FLOOR, DEFAULT_Q_CEILING)


# Convenience: get a default-wired wrapper using the BONG singleton.
def get_bong_state_space_wrapper(bong_updater: Optional[BONGUpdater] = None) -> BONGStateSpaceWrapper:
    if bong_updater is None:
        from adam.intelligence.bong import get_bong_updater
        bong_updater = get_bong_updater()
    return BONGStateSpaceWrapper(bong_updater)
