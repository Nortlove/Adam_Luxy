# =============================================================================
# ADAM Causal Conformal — split-conformal wrap on treatment-effect predictions
# Location: adam/intelligence/causal_conformal.py
# =============================================================================

"""
CAUSAL CONFORMAL WRAP

Distribution-free, finite-sample marginal-coverage guarantee on
treatment-effect / lift predictions. Sibling of
`adam.intelligence.recommendation_class.conformal.ConformalCoverage`
but targeted at treatment effects, which can be any real number
(positive, negative, unbounded) — not rate-bounded to [0, 1].

PILOT FRAMING

At pilot launch the calibration set is empty. As outcomes accumulate
from completed measurement cells (CATE estimate × realized lift on
held-out data), pairs land in the calibration set via
`record_realization`. Once `min_calibration_size` is reached, intervals
emit at the user-specified alpha with valid finite-sample marginal
coverage under exchangeability.

This is the layer that converts the synthetic A/B simulation's parametric
delta-method CI (which under-covers at moderate N) into a defensible
conformal CI with valid coverage AT ANY N.

INTEGRATION WITH M2 (CausalForestDML)

When `econml` is installed and `causal_forest.fit_causal_forest_for_cell`
runs against logged decision data, its output `CATEResult.tau_hat` is a
predicted lift. The realized lift on a held-out subset of the same cell
gives the calibration pair `(tau_hat, realized_tau)`. Wire pattern:

    wrap = ConformalLiftWrap(min_calibration_size=20)

    # Pre-pilot: bootstrap calibration set from synthetic sim
    sim = SyntheticABSimulator(planted_lift=0.25, seed=42)
    for sub_seed in range(50):
        decisions = sim.generate_decisions(n=2000)
        outcomes = sim.generate_outcomes(decisions)
        observed = sim.compute_observed_lift(decisions, outcomes)
        wrap.record_realization(
            predicted_lift=0.25,             # planted (treated as known)
            realized_lift=observed.relative_lift,
        )

    # Pilot ongoing: live calibration as M2 fits land
    cate_result = fit_causal_forest_for_cell(rows, ...)
    holdout_observed = compute_observed_lift_on_holdout(...)
    wrap.record_realization(
        predicted_lift=cate_result.tau_hat,
        realized_lift=holdout_observed,
    )

    # Public-facing intervals
    interval = wrap.interval(
        predicted_lift=cate_result.tau_hat,
        alpha=0.05,
    )

REFERENCES

Vovk, Gammerman & Shafer (2005) Algorithmic Learning in a Random World.
Lei et al. (2018) Distribution-Free Predictive Inference for Regression
(JASA). Romano et al. (2019) Conformalized Quantile Regression — for
the locally-adaptive variant when marginal coverage proves insufficient.

WHY SIBLING NOT EXTENSION

The existing rec-class ConformalCoverage clamps targets to [0, 1] (the
natural rate support for plant-model projections). Treatment effects can
be any real number — clamping would be wrong. Building a sibling rather
than parameterizing avoids accidentally breaking the rec-class path.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Tuple


DEFAULT_MIN_CALIBRATION_SIZE = 20
DEFAULT_ALPHA = 0.05


# =============================================================================
# Interval result
# =============================================================================


@dataclass(frozen=True)
class ConformalLiftInterval:
    """Distribution-free marginal-coverage prediction interval on a
    treatment-effect estimate.

    Coverage holds under the exchangeability assumption: future cells'
    nonconformity scores have the same distribution as the calibration
    set's. Drift in the data-generating process (market shift, audience
    composition change, creative fatigue) violates exchangeability and
    erodes coverage.
    """

    point_estimate: float
    nonconformity_quantile: float
    lower: float
    upper: float
    coverage_probability: float
    calibration_size: int

    def width(self) -> float:
        return self.upper - self.lower

    def contains(self, realized_lift: float) -> bool:
        return self.lower <= realized_lift <= self.upper


# =============================================================================
# Wrap — calibration-set store + interval emission
# =============================================================================


@dataclass
class ConformalLiftWrap:
    """Split-conformal wrap on treatment-effect predictions.

    Calibration pairs accumulate append-only via `record_realization`.
    Interval emission uses the (1 - alpha)-quantile of absolute
    residuals from the current calibration set.

    The store is mutable — calibration data streams in over the pilot's
    lifetime. Callers needing a snapshot for audit can use
    `snapshot_pairs()`.
    """

    min_calibration_size: int = DEFAULT_MIN_CALIBRATION_SIZE
    _pairs: List[Tuple[float, float]] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.min_calibration_size < 2:
            raise ValueError(
                f"min_calibration_size must be >= 2; got {self.min_calibration_size}"
            )

    # ── Calibration interface ──

    def record_realization(
        self, predicted_lift: float, realized_lift: float,
    ) -> None:
        """Record a (predicted, realized) calibration pair.

        Both values are signed and unbounded — treatment effects can be
        positive (lift), negative (backfire), or zero (no effect). The
        wrap does not clamp; the caller is responsible for sanity.
        """
        if not math.isfinite(predicted_lift):
            raise ValueError(f"predicted_lift must be finite; got {predicted_lift}")
        if not math.isfinite(realized_lift):
            raise ValueError(f"realized_lift must be finite; got {realized_lift}")
        self._pairs.append((predicted_lift, realized_lift))

    def snapshot_pairs(self) -> List[Tuple[float, float]]:
        return list(self._pairs)

    def calibration_size(self) -> int:
        return len(self._pairs)

    def reset(self) -> None:
        """Clear the calibration set. Test-only."""
        self._pairs.clear()

    # ── Interval emission ──

    def interval(
        self, predicted_lift: float, alpha: float = DEFAULT_ALPHA,
    ) -> ConformalLiftInterval:
        """Emit a (1 - alpha)-coverage interval around `predicted_lift`.

        Raises RuntimeError when calibration_size < min_calibration_size.
        Callers must verify warmup is complete before requesting
        intervals during pilot startup, or coverage is not guaranteed.
        """
        if not math.isfinite(predicted_lift):
            raise ValueError(f"predicted_lift must be finite; got {predicted_lift}")
        if not (0.0 < alpha < 1.0):
            raise ValueError(f"alpha must be in (0, 1); got {alpha}")
        n = len(self._pairs)
        if n < self.min_calibration_size:
            raise RuntimeError(
                f"calibration_size {n} below min_calibration_size "
                f"{self.min_calibration_size}; conformal interval refused"
            )

        residuals = sorted(abs(r - p) for p, r in self._pairs)

        # Split-conformal quantile: the ceil((n+1)(1-alpha))-th smallest
        # residual. 1-based in literature; convert to 0-based and clamp.
        k = math.ceil((n + 1) * (1.0 - alpha))
        k = max(1, min(n, k))
        q = residuals[k - 1]

        return ConformalLiftInterval(
            point_estimate=predicted_lift,
            nonconformity_quantile=q,
            lower=predicted_lift - q,
            upper=predicted_lift + q,
            coverage_probability=1.0 - alpha,
            calibration_size=n,
        )

    def empirical_coverage(self, alpha: float = DEFAULT_ALPHA) -> float:
        """Fraction of calibration pairs whose realized lift falls in
        the interval built at the given alpha.

        For a clean calibration set under exchangeability, should be
        approximately 1 - alpha. Drift in the data-generating process
        across the pilot's lifetime causes empirical coverage to diverge
        from nominal — that signal is itself useful and should be
        monitored.
        """
        if not (0.0 < alpha < 1.0):
            raise ValueError(f"alpha must be in (0, 1); got {alpha}")
        n = len(self._pairs)
        if n < self.min_calibration_size:
            raise RuntimeError(
                f"calibration_size {n} below min_calibration_size "
                f"{self.min_calibration_size}"
            )
        hits = 0
        for p, r in self._pairs:
            iv = self.interval(p, alpha=alpha)
            if iv.contains(r):
                hits += 1
        return hits / n


__all__ = [
    "ConformalLiftWrap",
    "ConformalLiftInterval",
    "DEFAULT_ALPHA",
    "DEFAULT_MIN_CALIBRATION_SIZE",
]
