# =============================================================================
# ADAM M2 Pipeline — Fit-and-Calibrate Orchestrator
# Location: adam/intelligence/m2_pipeline.py
# =============================================================================

"""Fit-and-calibrate orchestrator: bridges causal_forest + causal_conformal.

PURPOSE

The substrate is split for separation of concerns:
    causal_forest.py      — wraps EconML's CausalForestDML (M2 fit)
    causal_conformal.py   — split-conformal wrap on treatment-effect predictions

Production callers want ONE call that returns BOTH:
    - τ̂ from CausalForestDML
    - distribution-free coverage interval from the conformal wrap
    - calibration-pending discipline flag when the wrap is not yet warm

This module is that bridge. It is the production-facing M2 entry point.

A14 FLAG

Identifier:
    M2_CONFORMAL_CALIBRATION_PENDING

Retirement trigger:
    Retire when (a) the M2 conformal wrap has accumulated ≥20
    (predicted, realized) calibration pairs, AND (b) empirical coverage
    at α=0.05 falls within ±5pp of nominal 95% on the rolling window of
    the most recent 30 pairs.

    Until both conditions hold, every M2 result carries the flag in its
    `a14_flags_active` and the Prometheus counter increments per call.

WHY A SEPARATE MODULE

`causal_forest.py` is library-bound (econml + sklearn). `causal_conformal.py`
is library-free. Mixing them would force every conformal user to drag
the EconML import surface. Keeping the bridge separate means callers
that only need conformal calibration on, say, manually-supplied lift
estimates avoid the M2 dependency cost.

The bridge also is the natural place to put the A14 flag emission and
realized-lift computation — the substrate primitives stay pure.

USAGE

    from adam.intelligence.causal_conformal import ConformalLiftWrap
    from adam.intelligence.causal_forest import LoggedDecisionRow
    from adam.intelligence.m2_pipeline import fit_and_calibrate

    wrap = ConformalLiftWrap(min_calibration_size=20)
    result = fit_and_calibrate(
        rows=rows,
        wrap=wrap,
        atom_id="atom_test",
        holdout_fraction=0.2,
        alpha=0.05,
    )
    # result.cate         → CATEResult (always present unless rows degenerate)
    # result.interval     → ConformalLiftInterval or None (None when wrap cold)
    # result.a14_flags    → ["M2_CONFORMAL_CALIBRATION_PENDING"] when cold

REFERENCES

Wager & Athey (2018) Estimation and Inference of Heterogeneous Treatment
Effects using Random Forests (JASA). Athey, Tibshirani & Wager (2019)
Generalized Random Forests (Annals of Statistics). Vovk, Gammerman &
Shafer (2005) Algorithmic Learning in a Random World.
"""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from adam.intelligence.causal_conformal import (
    ConformalLiftInterval,
    ConformalLiftWrap,
    DEFAULT_ALPHA,
)
from adam.intelligence.causal_forest import (
    CATEResult,
    LibsMissingError,
    LoggedDecisionRow,
    fit_causal_forest_for_cell,
)

logger = logging.getLogger(__name__)


# =============================================================================
# A14 flag constants
# =============================================================================


M2_CONFORMAL_CALIBRATION_PENDING_FLAG: str = "M2_CONFORMAL_CALIBRATION_PENDING"

M2_CALIBRATION_RETIREMENT_TRIGGER: str = (
    "Retire M2_CONFORMAL_CALIBRATION_PENDING when the M2 conformal wrap "
    "has accumulated ≥20 (predicted, realized) calibration pairs AND "
    "empirical coverage at α=0.05 falls within ±5pp of nominal 95% on "
    "the rolling window of the most recent 30 pairs."
)

# Empirical-coverage band on the rolling window for retirement check.
_RETIREMENT_COVERAGE_BAND: float = 0.05
_RETIREMENT_ROLLING_WINDOW: int = 30
_RETIREMENT_MIN_CALIBRATION_SIZE: int = 20


# =============================================================================
# Result bundle
# =============================================================================


@dataclass(frozen=True)
class M2Result:
    """Bundle returned by `fit_and_calibrate`.

    `cate` is the CausalForestDML output (always present). `interval` is
    the conformal interval (None when the wrap has not accumulated
    `min_calibration_size` pairs yet). `a14_flags` lists active discipline
    flags — `M2_CONFORMAL_CALIBRATION_PENDING` is present whenever the
    interval is None or the empirical-coverage retirement check has not
    yet passed.
    """

    cate: CATEResult
    interval: Optional[ConformalLiftInterval]
    a14_flags: List[str]
    realized_lift: Optional[float]
    calibration_size_after: int


# =============================================================================
# Realized-lift estimator on the holdout set
# =============================================================================


def _ipw_realized_lift(rows: List[LoggedDecisionRow]) -> Optional[float]:
    """Compute IPW-weighted difference-in-means on a holdout set.

    Returns None when the holdout has no treated rows or no control rows
    or all propensities are degenerate (≤0 or ≥1) after truncation.

    IPW formula (truncated at [0.05, 0.95] to bound variance from
    extreme propensities — Crump et al. 2009):

        realized_tau = mean( Y_i * T_i / p_i )
                     - mean( Y_i * (1 - T_i) / (1 - p_i) )

    Falls back to plain difference-in-means when no propensities or all
    propensities are degenerate.
    """
    if not rows:
        return None

    treated_y: List[float] = []
    treated_w: List[float] = []
    control_y: List[float] = []
    control_w: List[float] = []

    have_propensities = False
    p_lo, p_hi = 0.05, 0.95

    for r in rows:
        # Truncate propensity to keep IPW weights bounded.
        p = r.propensity
        if 0.0 < p < 1.0:
            have_propensities = True
            p = max(p_lo, min(p_hi, p))
        if r.treatment == 1:
            treated_y.append(r.outcome)
            treated_w.append((1.0 / p) if have_propensities and p > 0 else 1.0)
        else:
            control_y.append(r.outcome)
            control_w.append((1.0 / (1.0 - p)) if have_propensities and p < 1 else 1.0)

    if not treated_y or not control_y:
        return None

    treated_mean = sum(y * w for y, w in zip(treated_y, treated_w)) / sum(treated_w)
    control_mean = sum(y * w for y, w in zip(control_y, control_w)) / sum(control_w)
    return treated_mean - control_mean


# =============================================================================
# Empirical-coverage retirement check
# =============================================================================


def _retirement_check_passes(
    wrap: ConformalLiftWrap,
    alpha: float = DEFAULT_ALPHA,
    rolling_window: int = _RETIREMENT_ROLLING_WINDOW,
    band: float = _RETIREMENT_COVERAGE_BAND,
    min_size: int = _RETIREMENT_MIN_CALIBRATION_SIZE,
) -> bool:
    """Return True iff the wrap meets BOTH retirement conditions.

    Conditions:
        (a) calibration_size ≥ min_size, AND
        (b) empirical coverage at α=alpha on the rolling-window subset is
            within ±band of nominal (1 - alpha).

    Note: empirical_coverage is computed over the WHOLE wrap; we
    approximate the rolling-window check by snapshotting the most-recent
    `rolling_window` pairs into a temp wrap. This is honest about what
    the retirement check measures — recent regime, not pilot lifetime.
    """
    n = wrap.calibration_size()
    if n < min_size:
        return False

    pairs = wrap.snapshot_pairs()
    recent = pairs[-rolling_window:] if len(pairs) > rolling_window else pairs

    if len(recent) < min_size:
        return False

    # Build a transient wrap to compute coverage on the rolling window.
    transient = ConformalLiftWrap(min_calibration_size=2)
    for p, r in recent:
        transient.record_realization(predicted_lift=p, realized_lift=r)

    nominal = 1.0 - alpha
    try:
        empirical = transient.empirical_coverage(alpha=alpha)
    except RuntimeError:
        return False

    # Small float-tolerance epsilon (1e-9) avoids spurious failures at
    # the band edge from FP arithmetic — abs(1.0 - 0.95) actually
    # evaluates to 0.050000000000000044 in double precision.
    return abs(empirical - nominal) <= band + 1e-9


# =============================================================================
# A14 flag emission
# =============================================================================


def _increment_a14_counter(atom_id: str, flag: str) -> None:
    """Increment the Prometheus a14_flag_active counter; non-fatal.

    Mirrors the pattern in campaign_orchestrator.py (the cascade-time
    emission point) so the M2 weekly-fit increments share a counter
    namespace with decision-time flags. Bounded cardinality: M2 emits
    exactly one (atom_id, flag) tuple unless callers vary atom_id.
    """
    try:
        from adam.infrastructure.prometheus.metrics import get_metrics
        pm = get_metrics()
        pm.a14_flag_active.labels(atom_id=atom_id, a14_flag=flag).inc()
    except Exception as exc:
        logger.debug("M2 A14 metric emission failed: %s", exc)


# =============================================================================
# Holdout split
# =============================================================================


def _split_rows(
    rows: List[LoggedDecisionRow],
    holdout_fraction: float,
    seed: int,
) -> tuple[List[LoggedDecisionRow], List[LoggedDecisionRow]]:
    """Split rows into (fit, holdout). Stable under fixed seed.

    Both arms must contain treated AND control rows; if the random split
    breaks that, we redraw up to 5 times before giving up and returning
    an empty holdout (the caller will skip calibration).
    """
    if holdout_fraction <= 0.0 or holdout_fraction >= 1.0:
        raise ValueError(
            f"holdout_fraction must be in (0, 1); got {holdout_fraction}"
        )

    rng = random.Random(seed)

    for _ in range(5):
        shuffled = list(rows)
        rng.shuffle(shuffled)
        n_holdout = max(2, int(round(len(shuffled) * holdout_fraction)))
        holdout = shuffled[:n_holdout]
        fit = shuffled[n_holdout:]

        ht = {r.treatment for r in holdout}
        ft = {r.treatment for r in fit}
        if len(ht) >= 2 and len(ft) >= 2:
            return fit, holdout

    # Both arms not present after 5 draws — return all to fit, empty holdout.
    return list(rows), []


# =============================================================================
# The fit-and-calibrate orchestrator
# =============================================================================


def fit_and_calibrate(
    rows: List[LoggedDecisionRow],
    wrap: ConformalLiftWrap,
    atom_id: str = "m2_pipeline",
    holdout_fraction: float = 0.2,
    alpha: float = DEFAULT_ALPHA,
    seed: int = 42,
    forest_params: Optional[Dict[str, Any]] = None,
) -> M2Result:
    """Fit M2 on (fit set), record realized lift on (holdout set), build interval.

    This is the production-facing entry point for M2. Single call,
    single bundle returned. The A14 flag is set on the result and
    incremented on the Prometheus counter when the wrap is not yet warm
    or the empirical-coverage retirement check has not passed.

    Args:
        rows: pscore_known-true logged decision rows for one cell
        wrap: the conformal wrap (mutated — calibration pair appended)
        atom_id: Prometheus label for the A14 counter
        holdout_fraction: fraction of rows reserved for realized-lift
        alpha: conformal coverage target (default 0.05 → 95% interval)
        seed: split RNG seed
        forest_params: optional override of CausalForestDML params

    Returns:
        M2Result containing cate, interval (or None), a14_flags list,
        realized_lift (or None), calibration_size_after.

    Raises:
        LibsMissingError when EconML isn't installed (propagated from
        the substrate; the drift-defense pattern is preserved here).
        ValueError when rows is empty.
    """
    if not rows:
        raise ValueError("fit_and_calibrate: empty rows")

    fit_rows, holdout_rows = _split_rows(rows, holdout_fraction, seed)

    # Fit on the fit set.
    cate = fit_causal_forest_for_cell(fit_rows, forest_params=forest_params)

    # Compute realized lift on the holdout set; None when holdout is
    # degenerate (no contrast). Calibration pair is recorded only when
    # we have a real realized value.
    realized_lift = _ipw_realized_lift(holdout_rows) if holdout_rows else None

    if realized_lift is not None:
        wrap.record_realization(
            predicted_lift=cate.tau_hat,
            realized_lift=realized_lift,
        )

    n_after = wrap.calibration_size()

    # Build interval iff wrap is warm. Even when warm, the A14 flag
    # remains active until the empirical-coverage retirement check
    # passes — a wrap with 20 pairs but with empirical coverage at 70%
    # cannot be claimed at 95% nominal.
    interval: Optional[ConformalLiftInterval] = None
    a14_flags: List[str] = []

    if n_after >= wrap.min_calibration_size:
        try:
            interval = wrap.interval(predicted_lift=cate.tau_hat, alpha=alpha)
        except RuntimeError:
            interval = None

    if not _retirement_check_passes(wrap, alpha=alpha):
        a14_flags.append(M2_CONFORMAL_CALIBRATION_PENDING_FLAG)
        _increment_a14_counter(atom_id, M2_CONFORMAL_CALIBRATION_PENDING_FLAG)

    return M2Result(
        cate=cate,
        interval=interval,
        a14_flags=a14_flags,
        realized_lift=realized_lift,
        calibration_size_after=n_after,
    )


__all__ = [
    "M2Result",
    "fit_and_calibrate",
    "M2_CONFORMAL_CALIBRATION_PENDING_FLAG",
    "M2_CALIBRATION_RETIREMENT_TRIGGER",
]
