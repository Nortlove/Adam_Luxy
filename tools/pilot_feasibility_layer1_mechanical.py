#!/usr/bin/env python3
"""Path C Layer 1 — mechanical conversion-count cascade with Wilson 95% CI.

NOT a directive-anchored slice. This is feasibility tooling for the LUXY
pilot's primary-endpoint power calc, parameterized so it runs today with
placeholder priors and re-runs cleanly when Becca delivers concrete LUXY
numbers (CR, flight length, addressable impression pool).

Three-layer composition:
  Layer 1 (this module): mechanical count cascade with Wilson 95% CI
                         + 3×3 (CTR, CR) sensitivity table.
  Layer 2 (subsequent):  statistical power vs primary endpoint —
                         consumes `point_estimate.expected_conversions`
                         from Layer 1's JSON output.
  Layer 3 (subsequent):  cell-level feasibility against A14 retirement-
                         trigger thresholds — consumes the per-cell
                         counts derivable from Layer 1 + a cell
                         allocation table.

Two distinct uncertainties, computed and shipped separately:

  1. Within-cell sampling uncertainty (Wilson CI). Treats each impression
     as a Bernoulli trial with success probability p = CTR × CR. The
     Wilson 1927 score interval is preferred over the normal-approximation
     Wald interval at extreme p_hat (here p ~ 7.5e-5 is far from 0.5).
     This is the load-bearing number for Layer 2's power calc.

  2. Across-cell parameter uncertainty (sensitivity table). 3×3 grid over
     (CTR_low, CTR, CTR_high) × (CR_low, CR, CR_high). Each cell shows
     the point estimate plus Wilson CI computed under that cell's CTR
     and CR. Auditable robustness check; not an input to downstream
     layers.

Reference:
  Wilson 1927, "Probable inference, the law of succession, and statistical
  inference," J. Amer. Statist. Assoc. 22:209-212.
"""
# Note: deliberately NOT using `from __future__ import annotations` here.
# The module is loaded via importlib.util.spec_from_file_location +
# exec_module from the test suite (because tools/ is not on the
# adam.* import path), and stringified annotations from future-annotations
# don't always resolve cleanly against the importlib-loaded module's
# __dict__ when Pydantic v2 tries to build the model. Concrete-type
# annotations sidestep the issue.

import argparse
import json
import math
import sys
from datetime import datetime, timezone
from itertools import product
from typing import List, Optional, Sequence, Tuple

from pydantic import BaseModel, Field, model_validator
from scipy.stats import norm


# ---------------------------------------------------------------------------
# Wilson 1927 score interval
# ---------------------------------------------------------------------------

def wilson_score_interval(
    *, n: int, p_hat: float, alpha: float = 0.05,
) -> Tuple[float, float]:
    """Wilson 1927 score interval for a binomial proportion.

    Closed form for the (1 - alpha) confidence interval on a Bernoulli
    proportion observed at n trials with sample proportion p_hat:

        z       = Phi^{-1}(1 - alpha / 2)
        denom   = 1 + z² / n
        center  = (p_hat + z² / (2n)) / denom
        radius  = z * sqrt(p_hat * (1 - p_hat) / n + z² / (4n²)) / denom
        [lo, hi] = clamp([center - radius, center + radius], 0, 1)

    The Wilson interval is the canonical small-sample / extreme-p
    alternative to the normal-approximation Wald interval. At p_hat = 0
    the lower bound is 0 (clamped) and the upper bound is non-zero
    (Wilson 1927); at p_hat = 1 the upper bound is 1 (clamped) and the
    lower bound is < 1.
    """
    if n <= 0:
        raise ValueError(f"n must be positive, got {n!r}")
    if not 0.0 <= p_hat <= 1.0:
        raise ValueError(f"p_hat must be in [0, 1], got {p_hat!r}")
    if not 0.0 < alpha < 1.0:
        raise ValueError(f"alpha must be in (0, 1), got {alpha!r}")

    z = float(norm.ppf(1.0 - alpha / 2.0))
    z_sq = z * z
    # Boundary-exact cases: Wilson 1927 yields a closed form at p_hat ∈
    # {0, 1} that floating-point cancellation slightly disturbs (e.g.,
    # ~1e-18 residual on the cancelled lower bound at p_hat=0). Special-
    # case so the interval boundary is exact.
    if p_hat == 0.0:
        return (0.0, z_sq / (n + z_sq))
    if p_hat == 1.0:
        return (n / (n + z_sq), 1.0)
    denominator = 1.0 + z_sq / n
    center = (p_hat + z_sq / (2.0 * n)) / denominator
    radius = (
        z * math.sqrt(p_hat * (1.0 - p_hat) / n + z_sq / (4.0 * n * n))
    ) / denominator
    lower = max(0.0, center - radius)
    upper = min(1.0, center + radius)
    return lower, upper


# ---------------------------------------------------------------------------
# Pydantic input models
# ---------------------------------------------------------------------------

class CampaignParameters(BaseModel):
    """Campaign-level inputs: addressable impression pool + flight."""

    impression_pool: int = Field(gt=0, description="Total addressable impressions over the flight")
    flight_length_days: int = Field(gt=0, description="Flight length in days")


class FunnelParameters(BaseModel):
    """Funnel rates with pessimistic / point / optimistic estimates.

    `*_low` and `*_high` bracket the parameter-uncertainty range; the
    bare `click_through_rate` and `conversion_rate` are the point
    estimates. Cross-field validator enforces low ≤ point ≤ high.
    """

    click_through_rate: float = Field(gt=0, lt=1)
    click_through_rate_low: float = Field(gt=0, lt=1)
    click_through_rate_high: float = Field(gt=0, lt=1)
    conversion_rate: float = Field(gt=0, le=1)
    conversion_rate_low: float = Field(gt=0, le=1)
    conversion_rate_high: float = Field(gt=0, le=1)

    @model_validator(mode="after")
    def _check_brackets(self) -> "FunnelParameters":
        if not (
            self.click_through_rate_low
            <= self.click_through_rate
            <= self.click_through_rate_high
        ):
            raise ValueError(
                f"CTR brackets must satisfy low ≤ point ≤ high; got "
                f"low={self.click_through_rate_low!r}, "
                f"point={self.click_through_rate!r}, "
                f"high={self.click_through_rate_high!r}"
            )
        if not (
            self.conversion_rate_low
            <= self.conversion_rate
            <= self.conversion_rate_high
        ):
            raise ValueError(
                f"CR brackets must satisfy low ≤ point ≤ high; got "
                f"low={self.conversion_rate_low!r}, "
                f"point={self.conversion_rate!r}, "
                f"high={self.conversion_rate_high!r}"
            )
        return self


class FeasibilityInputs(BaseModel):
    campaign: CampaignParameters
    funnel: FunnelParameters
    confidence_level: float = Field(default=0.95, gt=0, lt=1)


# ---------------------------------------------------------------------------
# Computation
# ---------------------------------------------------------------------------

class PointEstimate(BaseModel):
    expected_clicks: float
    expected_conversions: float
    wilson_ci_95: Tuple[float, float]   # proportion bounds in [0, 1]
    wilson_ci_lo_count: float           # proportion × n
    wilson_ci_hi_count: float


class SensitivityCell(BaseModel):
    ctr: float
    ctr_label: str   # "low" | "mid" | "high"
    cr: float
    cr_label: str
    expected_conversions: float
    wilson_ci_95: Tuple[float, float]


def compute_point_estimate(inputs: FeasibilityInputs) -> PointEstimate:
    n = inputs.campaign.impression_pool
    ctr = inputs.funnel.click_through_rate
    cr = inputs.funnel.conversion_rate
    p = ctr * cr
    alpha = 1.0 - inputs.confidence_level
    lo, hi = wilson_score_interval(n=n, p_hat=p, alpha=alpha)
    return PointEstimate(
        expected_clicks=n * ctr,
        expected_conversions=n * p,
        wilson_ci_95=(lo, hi),
        wilson_ci_lo_count=lo * n,
        wilson_ci_hi_count=hi * n,
    )


def compute_sensitivity_table(
    inputs: FeasibilityInputs,
) -> List[SensitivityCell]:
    n = inputs.campaign.impression_pool
    alpha = 1.0 - inputs.confidence_level
    ctr_axes = [
        ("low", inputs.funnel.click_through_rate_low),
        ("mid", inputs.funnel.click_through_rate),
        ("high", inputs.funnel.click_through_rate_high),
    ]
    cr_axes = [
        ("low", inputs.funnel.conversion_rate_low),
        ("mid", inputs.funnel.conversion_rate),
        ("high", inputs.funnel.conversion_rate_high),
    ]
    cells: List[SensitivityCell] = []
    for (ctr_label, ctr), (cr_label, cr) in product(ctr_axes, cr_axes):
        p = ctr * cr
        lo, hi = wilson_score_interval(n=n, p_hat=p, alpha=alpha)
        cells.append(SensitivityCell(
            ctr=ctr, ctr_label=ctr_label,
            cr=cr, cr_label=cr_label,
            expected_conversions=n * p,
            wilson_ci_95=(lo, hi),
        ))
    return cells


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def render_text_summary(
    inputs: FeasibilityInputs,
    point: PointEstimate,
    sensitivity: Sequence[SensitivityCell],
) -> str:
    """Pretty-printed text summary for stdout."""
    rule = "=" * 72
    sub = "-" * 72
    lines = [
        rule,
        "Layer 1 — mechanical conversion-count cascade (Wilson 95% CI)",
        rule,
        f"Impression pool:    {inputs.campaign.impression_pool:,}",
        f"Flight length:      {inputs.campaign.flight_length_days} days",
        f"CTR (low/mid/high): "
        f"{inputs.funnel.click_through_rate_low:.5f} / "
        f"{inputs.funnel.click_through_rate:.5f} / "
        f"{inputs.funnel.click_through_rate_high:.5f}",
        f"CR  (low/mid/high): "
        f"{inputs.funnel.conversion_rate_low:.5f} / "
        f"{inputs.funnel.conversion_rate:.5f} / "
        f"{inputs.funnel.conversion_rate_high:.5f}",
        "",
        "POINT ESTIMATE",
        sub,
        f"  Expected clicks:       {point.expected_clicks:,.1f}",
        f"  Expected conversions:  {point.expected_conversions:,.1f}",
        f"  Wilson 95% CI (count): "
        f"[{point.wilson_ci_lo_count:,.1f}, {point.wilson_ci_hi_count:,.1f}]",
        "",
        "SENSITIVITY 3×3 (rows = CTR, cols = CR; cells = expected conversions)",
        sub,
    ]
    by_ctr: dict = {}
    for cell in sensitivity:
        by_ctr.setdefault(cell.ctr_label, {})[cell.cr_label] = cell
    header = (
        f"  {'CTR':<8}{'CR_low':>14}{'CR_mid':>14}{'CR_high':>14}"
    )
    lines.append(header)
    for ctr_label in ("low", "mid", "high"):
        row = f"  {ctr_label:<8}"
        for cr_label in ("low", "mid", "high"):
            cell = by_ctr[ctr_label][cr_label]
            row += f"{cell.expected_conversions:>13,.1f} "
        lines.append(row)
    lines.append(rule)
    return "\n".join(lines)


def emit_json_payload(
    inputs: FeasibilityInputs,
    point: PointEstimate,
    sensitivity: Sequence[SensitivityCell],
) -> dict:
    return {
        "computed_at": datetime.now(timezone.utc).isoformat(),
        "inputs": inputs.model_dump(),
        "point_estimate": {
            "expected_clicks": point.expected_clicks,
            "expected_conversions": point.expected_conversions,
            "wilson_ci_95": list(point.wilson_ci_95),
            "wilson_ci_lo_count": point.wilson_ci_lo_count,
            "wilson_ci_hi_count": point.wilson_ci_hi_count,
        },
        "sensitivity_table": [
            {
                "ctr": c.ctr,
                "ctr_label": c.ctr_label,
                "cr": c.cr,
                "cr_label": c.cr_label,
                "expected_conversions": c.expected_conversions,
                "wilson_ci_95": list(c.wilson_ci_95),
            }
            for c in sensitivity
        ],
        "interpretation_hooks": {
            "layer_2_power_input": point.expected_conversions,
            "layer_3_cell_input": None,
        },
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

# Placeholder defaults for first-run-without-Becca-numbers. Order of
# magnitude only. The "mid" values are not LUXY-specific; they are
# reasonable industry midpoints meant to exercise the tool, not to
# anchor decisions. Re-run with concrete LUXY numbers when they land.
_PLACEHOLDER_DEFAULTS = {
    "impression_pool": 50_000_000,
    "flight_length_days": 90,
    "ctr": 0.0015,
    "ctr_low": 0.0008,
    "ctr_high": 0.0025,
    "cr": 0.05,
    "cr_low": 0.02,
    "cr_high": 0.08,
}


def _build_argparser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument(
        "--impression-pool", type=int,
        default=_PLACEHOLDER_DEFAULTS["impression_pool"],
        help=(
            "Addressable impression pool over the flight. PLACEHOLDER "
            "default 50M; replace with Becca's LUXY-specific number."
        ),
    )
    p.add_argument(
        "--flight-length-days", type=int,
        default=_PLACEHOLDER_DEFAULTS["flight_length_days"],
        help="Flight length in days. PLACEHOLDER default 90.",
    )
    p.add_argument(
        "--ctr", type=float,
        default=_PLACEHOLDER_DEFAULTS["ctr"],
        help="Point CTR estimate. PLACEHOLDER default 0.0015.",
    )
    p.add_argument(
        "--ctr-low", type=float,
        default=_PLACEHOLDER_DEFAULTS["ctr_low"],
        help="Pessimistic CTR. PLACEHOLDER default 0.0008.",
    )
    p.add_argument(
        "--ctr-high", type=float,
        default=_PLACEHOLDER_DEFAULTS["ctr_high"],
        help="Optimistic CTR. PLACEHOLDER default 0.0025.",
    )
    p.add_argument(
        "--cr", type=float,
        default=_PLACEHOLDER_DEFAULTS["cr"],
        help="Point conversion rate. PLACEHOLDER default 0.05.",
    )
    p.add_argument(
        "--cr-low", type=float,
        default=_PLACEHOLDER_DEFAULTS["cr_low"],
        help="Pessimistic CR. PLACEHOLDER default 0.02.",
    )
    p.add_argument(
        "--cr-high", type=float,
        default=_PLACEHOLDER_DEFAULTS["cr_high"],
        help="Optimistic CR. PLACEHOLDER default 0.08.",
    )
    p.add_argument(
        "--confidence-level", type=float, default=0.95,
        help="CI confidence level (default 0.95).",
    )
    p.add_argument(
        "--output", type=str, default=None,
        help="JSON output path. If omitted, only stdout summary is printed.",
    )
    return p


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = _build_argparser().parse_args(argv)
    inputs = FeasibilityInputs(
        campaign=CampaignParameters(
            impression_pool=args.impression_pool,
            flight_length_days=args.flight_length_days,
        ),
        funnel=FunnelParameters(
            click_through_rate=args.ctr,
            click_through_rate_low=args.ctr_low,
            click_through_rate_high=args.ctr_high,
            conversion_rate=args.cr,
            conversion_rate_low=args.cr_low,
            conversion_rate_high=args.cr_high,
        ),
        confidence_level=args.confidence_level,
    )
    point = compute_point_estimate(inputs)
    sensitivity = compute_sensitivity_table(inputs)

    print(render_text_summary(inputs, point, sensitivity))

    if args.output:
        payload = emit_json_payload(inputs, point, sensitivity)
        with open(args.output, "w") as f:
            json.dump(payload, f, indent=2)
        print(f"\nWrote {args.output}")
    return 0


# Pydantic v2 forward-reference rebuild — needed because nested BaseModel
# references in `FeasibilityInputs.campaign: CampaignParameters` don't
# always resolve cleanly when this module is loaded via
# `importlib.util.spec_from_file_location` + `exec_module` (as it must
# be, because the file lives under tools/ rather than adam/). Calling
# `model_rebuild()` after every class is defined makes the resolution
# explicit and importlib-loader-safe.
FeasibilityInputs.model_rebuild()


if __name__ == "__main__":
    sys.exit(main())
