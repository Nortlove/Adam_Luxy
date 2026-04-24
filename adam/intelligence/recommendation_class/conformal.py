"""ConformalCoverage — split-conformal wrap on plant-model projections.

Distribution-free marginal-coverage guarantee on the plant model's
predicted conversion rate. Given a calibration set of completed
(projected_rate, realized_rate) pairs, returns an interval around any
new projected rate such that the realized rate lies in the interval
with probability >= 1 - alpha (exchangeability assumption).

Pilot framing:

- At launch the calibration set is empty. Coverage is NOT yet
  guaranteed. The ConformalCoverage primitive refuses to emit intervals
  below `min_calibration_size` so callers don't mistake the empty-set
  fallback for a real coverage guarantee.
- As realized outcomes accumulate from completed rec-classes
  (horizon-complete + adjudicated), pairs land in the calibration set
  via `record_realization`. Once `min_calibration_size` is reached,
  intervals emit at the user-specified alpha.
- Coverage is MARGINAL (across the exchangeable distribution of cells),
  not conditional on any particular rec-class identity. Conditional
  coverage is a later extension.

Reference: Vovk, Gammerman & Shafer (2005) Algorithmic Learning in a
Random World; Lei et al. (2018) Distribution-Free Predictive Inference
for Regression (JASA).

Scope of this slice:

- Split-conformal with absolute residual as nonconformity score.
- Empty-cal refusal via `min_calibration_size`.
- Deterministic calibration-set ordering (append-only; ties broken by
  insertion order) so interval emission is reproducible.

NOT in this slice:

- Conditional conformal (Romano et al. 2019 CQR, local regression).
  Ships later if marginal coverage proves insufficient for the
  adjudicator's partition decisions.
- Jackknife+ or full-conformal variants. Split-conformal's exchange-
  ability assumption is the pilot minimum; the heavier variants add
  sample efficiency the pilot doesn't yet need.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Optional, Tuple


DEFAULT_MIN_CALIBRATION_SIZE = 20
DEFAULT_ALPHA = 0.10


# =============================================================================
# ConformalInterval — a computed prediction interval
# =============================================================================


@dataclass(frozen=True)
class ConformalInterval:
    """Distribution-free prediction interval around a projected rate.

    `lower` and `upper` are the interval endpoints clipped to [0, 1]
    (the natural rate support). The pre-clip endpoints are retained in
    `lower_raw` / `upper_raw` so callers auditing coverage know when
    clipping was active.

    `coverage_probability` is the nominal coverage the interval was
    computed at (1 - alpha). The MARGINAL guarantee holds under the
    exchangeability assumption of the calibration pairs.
    """

    projected_rate: float
    nonconformity_quantile: float
    lower: float
    upper: float
    lower_raw: float
    upper_raw: float
    coverage_probability: float
    calibration_size: int

    def width(self) -> float:
        return self.upper - self.lower

    def contains(self, realized_rate: float) -> bool:
        return self.lower <= realized_rate <= self.upper


# =============================================================================
# ConformalCoverage — calibration-set store + interval emission
# =============================================================================


@dataclass
class ConformalCoverage:
    """Split-conformal coverage store.

    Calibration pairs accumulate append-only via `record_realization`.
    Interval emission uses the (1 - alpha)-quantile of absolute
    residuals from the current calibration set.

    The store is explicitly mutable — calibration data streams in over
    the pilot's lifetime. Callers that need a snapshot for audit can
    use `snapshot_pairs()`.
    """

    min_calibration_size: int = DEFAULT_MIN_CALIBRATION_SIZE
    _pairs: List[Tuple[float, float]] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.min_calibration_size < 2:
            raise ValueError(
                f"min_calibration_size must be >= 2; "
                f"got {self.min_calibration_size}"
            )

    # ── CALIBRATION INTERFACE ────────────────────────────────────────────

    def record_realization(
        self, projected_rate: float, realized_rate: float,
    ) -> None:
        """Record a (projected, realized) calibration pair.

        Both rates are clamped to [0, 1] for robustness against
        numerical overflow; nonconformity is |projected - realized|
        so ordering is preserved under clamp.
        """
        if not (0.0 <= projected_rate <= 1.0):
            raise ValueError(
                f"projected_rate must be in [0, 1]; got {projected_rate}"
            )
        if not (0.0 <= realized_rate <= 1.0):
            raise ValueError(
                f"realized_rate must be in [0, 1]; got {realized_rate}"
            )
        self._pairs.append((projected_rate, realized_rate))

    def snapshot_pairs(self) -> List[Tuple[float, float]]:
        return list(self._pairs)

    def calibration_size(self) -> int:
        return len(self._pairs)

    # ── INTERVAL EMISSION ────────────────────────────────────────────────

    def interval(
        self, projected_rate: float, alpha: float = DEFAULT_ALPHA,
    ) -> ConformalInterval:
        """Emit a (1 - alpha)-coverage interval around the projected rate.

        Raises RuntimeError if the calibration set is below
        `min_calibration_size` — callers must check
        `calibration_size() >= min_calibration_size` before requesting
        intervals during pilot warmup, or the interval would not carry
        the marginal coverage guarantee.
        """
        if not (0.0 <= projected_rate <= 1.0):
            raise ValueError(
                f"projected_rate must be in [0, 1]; got {projected_rate}"
            )
        if not (0.0 < alpha < 1.0):
            raise ValueError(f"alpha must be in (0, 1); got {alpha}")
        n = len(self._pairs)
        if n < self.min_calibration_size:
            raise RuntimeError(
                f"calibration set size {n} below "
                f"min_calibration_size {self.min_calibration_size}; "
                "conformal interval refused"
            )

        residuals = sorted(abs(r - p) for p, r in self._pairs)

        # Split-conformal quantile: the ceil((n+1)(1-alpha))-th smallest
        # residual. Index is 1-based in the formula; we convert to
        # 0-based and clamp to [0, n-1].
        k = math.ceil((n + 1) * (1.0 - alpha))
        k = max(1, min(n, k))
        q = residuals[k - 1]

        lower_raw = projected_rate - q
        upper_raw = projected_rate + q
        return ConformalInterval(
            projected_rate=projected_rate,
            nonconformity_quantile=q,
            lower=max(0.0, lower_raw),
            upper=min(1.0, upper_raw),
            lower_raw=lower_raw,
            upper_raw=upper_raw,
            coverage_probability=1.0 - alpha,
            calibration_size=n,
        )

    def empirical_coverage(self, alpha: float = DEFAULT_ALPHA) -> float:
        """Fraction of calibration pairs whose realized rate falls in
        the interval built at the given alpha.

        For split-conformal with a clean calibration set, this should
        be approximately 1 - alpha (up to binomial noise). Diverging
        empirical coverage signals exchangeability violation — e.g.,
        systematic drift in projected-vs-realized over time, or cell
        heterogeneity the marginal guarantee cannot accommodate.
        """
        if not (0.0 < alpha < 1.0):
            raise ValueError(f"alpha must be in (0, 1); got {alpha}")
        n = len(self._pairs)
        if n < self.min_calibration_size:
            raise RuntimeError(
                f"calibration set size {n} below "
                f"min_calibration_size {self.min_calibration_size}"
            )
        hits = 0
        for p, r in self._pairs:
            iv = self.interval(p, alpha=alpha)
            if iv.contains(r):
                hits += 1
        return hits / n


__all__ = [
    "ConformalCoverage",
    "ConformalInterval",
    "DEFAULT_ALPHA",
    "DEFAULT_MIN_CALIBRATION_SIZE",
]
