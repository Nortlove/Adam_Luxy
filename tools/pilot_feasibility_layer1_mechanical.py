#!/usr/bin/env python3
"""Path C Layer 1 — mechanical conversion-count cascade with Wilson 95% CI.

Originally landed as the non-directive-anchored P.1.L1 (commit 7e31c68);
extended in slice G.2.1.attr with the attribution-coverage dimension.
Tooling for the LUXY pilot's primary-endpoint power calc, parameterized
so it runs today with placeholder priors and re-runs cleanly when Becca
delivers concrete LUXY numbers (CR, flight length, addressable
impression pool, real attribution coverage measured at S8.7).

Three-layer composition:
  Layer 1 (this module): mechanical count cascade with Wilson 95% CI
                         + 3×3×3 (CTR, CR, coverage) sensitivity table.
  Layer 2 (subsequent):  statistical power vs primary endpoint —
                         consumes
                         `point_estimate.attributable_expected_conversions`
                         from Layer 1's JSON output via the named
                         `interpretation_hooks.layer_2_power_input` slot.
  Layer 3 (subsequent):  cell-level feasibility against A14 retirement-
                         trigger thresholds — consumes the per-cell
                         counts derivable from Layer 1 + a cell
                         allocation table.

Three distinct uncertainties, computed and shipped separately:

  1. Within-cell sampling uncertainty (Wilson CI on the ATTRIBUTABLE
     proportion). Treats each impression as a Bernoulli trial with
     success probability p = CTR × CR × coverage, where `coverage` is
     the fraction of conversions correctly attributed via sapid
     URL-macro postback correlation (directive §0.5 #5 + §S8.4). The
     Wilson 1927 score interval is preferred over the normal-
     approximation Wald interval at extreme p_hat. This is the
     load-bearing number for Layer 2's power calc.

  2. Within-cell sampling uncertainty (Wilson CI on the GROSS
     proportion p = CTR × CR). Shipped alongside the attributable
     CI for QA — distinguishes "what the campaign mechanically
     generated" from "what the analysis can measure." Not the input
     to Layer 2.

  3. Across-cell parameter uncertainty (3×3×3 sensitivity grid over
     (CTR_low/mid/high) × (CR_low/mid/high) × (coverage_low/mid/high)).
     Each of the 27 cells reports both gross and attributable counts
     plus their Wilson CIs. Auditable robustness check; not an input
     to downstream layers.

Why attribution-coverage matters here, not later: directive §7
flags "if sapid correlation rate < 80% at S8.7" as a failure-mode
trigger. Coverage uncertainty is structural (depends on browser /
device / postback-loss patterns), not measurement noise — the gross
count cannot stand in as a proxy for the attributable count without
overstating the analysis's power.

References:
  Wilson 1927, "Probable inference, the law of succession, and statistical
    inference," J. Amer. Statist. Assoc. 22:209-212.
  Directive §0.5 #5 (URL-macro `sapid={SA_POSTBACK_ID}` attribution).
  Directive §S8.4 (pixel postback wiring end-to-end).
  Directive §7 (failure-mode playbook — sapid coverage 80% floor).
  Directive §G.2 (OSF Pre-Registration — sample-size feasibility).
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


class AttributionParameters(BaseModel):
    """Attribution-coverage rates with pessimistic / point / optimistic
    estimates.

    `coverage` is the fraction of conversions correctly attributed via
    sapid URL-macro postback correlation. Per directive §7 the
    operational floor before a failure-mode response triggers is
    ~0.80; the CLI default of 0.85 reflects realistic programmatic-
    attribution coverage with modest headroom above that floor. Real
    LUXY coverage will be measured at S8.7 sandbox round-trip.

    Cross-field validator enforces low ≤ point ≤ high.
    """

    coverage: float = Field(gt=0, le=1)
    coverage_low: float = Field(gt=0, le=1)
    coverage_high: float = Field(gt=0, le=1)

    @model_validator(mode="after")
    def _check_brackets(self) -> "AttributionParameters":
        if not (self.coverage_low <= self.coverage <= self.coverage_high):
            raise ValueError(
                f"coverage brackets must satisfy low ≤ point ≤ high; got "
                f"low={self.coverage_low!r}, point={self.coverage!r}, "
                f"high={self.coverage_high!r}"
            )
        return self


AttributionParameters.model_rebuild()


class FeasibilityInputs(BaseModel):
    campaign: CampaignParameters
    funnel: FunnelParameters
    attribution: AttributionParameters
    confidence_level: float = Field(default=0.95, gt=0, lt=1)


# ---------------------------------------------------------------------------
# Computation
# ---------------------------------------------------------------------------

class PointEstimate(BaseModel):
    """Point-estimate output. Two count tracks coexist: gross
    (mechanically generated by the campaign) and attributable (what the
    analysis can measure via sapid postback correlation).

    `wilson_ci_95` and the *_count fields are interpreted on the
    ATTRIBUTABLE proportion — they are the load-bearing numbers for
    Layer 2's power calc. `gross_wilson_ci_95` is shipped alongside
    for QA.
    """

    expected_clicks: float
    gross_expected_conversions: float
    attributable_expected_conversions: float
    wilson_ci_95: Tuple[float, float]        # attributable proportion bounds
    wilson_ci_lo_count: float                # attributable lo × n
    wilson_ci_hi_count: float                # attributable hi × n
    gross_wilson_ci_95: Tuple[float, float]  # gross proportion bounds (QA)


class SensitivityCell(BaseModel):
    ctr: float
    ctr_label: str   # "low" | "mid" | "high"
    cr: float
    cr_label: str
    coverage: float
    coverage_label: str  # "low" | "mid" | "high"
    gross_expected_conversions: float
    attributable_expected_conversions: float
    wilson_ci_95: Tuple[float, float]        # attributable
    gross_wilson_ci_95: Tuple[float, float]  # gross (QA)


PointEstimate.model_rebuild()
SensitivityCell.model_rebuild()


def compute_point_estimate(inputs: FeasibilityInputs) -> PointEstimate:
    n = inputs.campaign.impression_pool
    ctr = inputs.funnel.click_through_rate
    cr = inputs.funnel.conversion_rate
    coverage = inputs.attribution.coverage
    p_gross = ctr * cr
    p_attr = ctr * cr * coverage
    alpha = 1.0 - inputs.confidence_level
    attr_lo, attr_hi = wilson_score_interval(n=n, p_hat=p_attr, alpha=alpha)
    gross_lo, gross_hi = wilson_score_interval(n=n, p_hat=p_gross, alpha=alpha)
    return PointEstimate(
        expected_clicks=n * ctr,
        gross_expected_conversions=n * p_gross,
        attributable_expected_conversions=n * p_attr,
        wilson_ci_95=(attr_lo, attr_hi),
        wilson_ci_lo_count=attr_lo * n,
        wilson_ci_hi_count=attr_hi * n,
        gross_wilson_ci_95=(gross_lo, gross_hi),
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
    coverage_axes = [
        ("low", inputs.attribution.coverage_low),
        ("mid", inputs.attribution.coverage),
        ("high", inputs.attribution.coverage_high),
    ]
    cells: List[SensitivityCell] = []
    for (ctr_label, ctr), (cr_label, cr), (cov_label, cov) in product(
        ctr_axes, cr_axes, coverage_axes,
    ):
        p_gross = ctr * cr
        p_attr = ctr * cr * cov
        attr_lo, attr_hi = wilson_score_interval(
            n=n, p_hat=p_attr, alpha=alpha,
        )
        gross_lo, gross_hi = wilson_score_interval(
            n=n, p_hat=p_gross, alpha=alpha,
        )
        cells.append(SensitivityCell(
            ctr=ctr, ctr_label=ctr_label,
            cr=cr, cr_label=cr_label,
            coverage=cov, coverage_label=cov_label,
            gross_expected_conversions=n * p_gross,
            attributable_expected_conversions=n * p_attr,
            wilson_ci_95=(attr_lo, attr_hi),
            gross_wilson_ci_95=(gross_lo, gross_hi),
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
    rule = "=" * 78
    sub = "-" * 78
    lines = [
        rule,
        "Layer 1 — mechanical conversion-count cascade (Wilson 95% CI)",
        rule,
        f"Impression pool:           {inputs.campaign.impression_pool:,}",
        f"Flight length:             {inputs.campaign.flight_length_days} days",
        f"CTR      (low/mid/high):   "
        f"{inputs.funnel.click_through_rate_low:.5f} / "
        f"{inputs.funnel.click_through_rate:.5f} / "
        f"{inputs.funnel.click_through_rate_high:.5f}",
        f"CR       (low/mid/high):   "
        f"{inputs.funnel.conversion_rate_low:.5f} / "
        f"{inputs.funnel.conversion_rate:.5f} / "
        f"{inputs.funnel.conversion_rate_high:.5f}",
        f"Coverage (low/mid/high):   "
        f"{inputs.attribution.coverage_low:.3f} / "
        f"{inputs.attribution.coverage:.3f} / "
        f"{inputs.attribution.coverage_high:.3f}",
        "",
        "POINT ESTIMATE",
        sub,
        f"  Expected clicks:                    {point.expected_clicks:,.1f}",
        f"  Gross expected conversions:         "
        f"{point.gross_expected_conversions:,.1f}",
        f"  Attributable expected conversions:  "
        f"{point.attributable_expected_conversions:,.1f}  "
        f"(load-bearing for Layer 2)",
        f"  Wilson 95% CI on attributable count: "
        f"[{point.wilson_ci_lo_count:,.1f}, {point.wilson_ci_hi_count:,.1f}]",
        "",
        "SENSITIVITY 3×3×3 — three (CTR × CR) tables, one per coverage level",
        "(cells = ATTRIBUTABLE expected conversions)",
        sub,
    ]
    by_cov_ctr: dict = {}
    for cell in sensitivity:
        by_cov_ctr.setdefault(cell.coverage_label, {}).setdefault(
            cell.ctr_label, {},
        )[cell.cr_label] = cell
    header = (
        f"    {'CTR':<8}{'CR_low':>14}{'CR_mid':>14}{'CR_high':>14}"
    )
    for cov_label in ("low", "mid", "high"):
        cov_value = by_cov_ctr[cov_label]["mid"]["mid"].coverage
        lines.append(f"  coverage={cov_label} ({cov_value:.3f})")
        lines.append(header)
        for ctr_label in ("low", "mid", "high"):
            row = f"    {ctr_label:<8}"
            for cr_label in ("low", "mid", "high"):
                cell = by_cov_ctr[cov_label][ctr_label][cr_label]
                row += f"{cell.attributable_expected_conversions:>13,.1f} "
            lines.append(row)
        lines.append("")
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
            "gross_expected_conversions": point.gross_expected_conversions,
            "attributable_expected_conversions":
                point.attributable_expected_conversions,
            "wilson_ci_95": list(point.wilson_ci_95),  # attributable
            "wilson_ci_lo_count": point.wilson_ci_lo_count,  # attributable
            "wilson_ci_hi_count": point.wilson_ci_hi_count,  # attributable
            "gross_wilson_ci_95": list(point.gross_wilson_ci_95),  # QA only
        },
        "sensitivity_table": [
            {
                "ctr": c.ctr,
                "ctr_label": c.ctr_label,
                "cr": c.cr,
                "cr_label": c.cr_label,
                "coverage": c.coverage,
                "coverage_label": c.coverage_label,
                "gross_expected_conversions": c.gross_expected_conversions,
                "attributable_expected_conversions":
                    c.attributable_expected_conversions,
                "wilson_ci_95": list(c.wilson_ci_95),  # attributable
                "gross_wilson_ci_95": list(c.gross_wilson_ci_95),  # QA only
            }
            for c in sensitivity
        ],
        "interpretation_hooks": {
            # G.2.1.attr (extending P.1.L1): Layer 2's power calc consumes
            # the ATTRIBUTABLE count, not the gross. The slice that landed
            # P.1.L1 (commit 7e31c68) wired layer_2_power_input to
            # `expected_conversions` (gross-only, pre-attribution); the
            # extension pivots this slot to the attributable count so
            # Layer 2 doesn't overstate its power. Per directive §7
            # the 80% sapid-coverage floor is the operational threshold;
            # using gross would be the equivalent of assuming 100%
            # coverage at all times.
            "layer_2_power_input": point.attributable_expected_conversions,
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
    # Attribution-coverage defaults reflect §7's 80% sapid-coverage
    # failure-mode floor with modest headroom: mid 0.85 (above floor),
    # low 0.65 (below floor — exercises the failure-mode regime),
    # high 0.95 (programmatic-attribution practical ceiling). Real
    # LUXY coverage will be measured at S8.7 sandbox round-trip.
    "attribution_coverage": 0.85,
    "attribution_coverage_low": 0.65,
    "attribution_coverage_high": 0.95,
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
        "--attribution-coverage", type=float,
        default=_PLACEHOLDER_DEFAULTS["attribution_coverage"],
        help=(
            "Point sapid postback-correlation coverage. Default 0.85 "
            "(modest headroom above directive §7's 80% failure-mode "
            "floor). Real LUXY coverage measured at S8.7."
        ),
    )
    p.add_argument(
        "--attribution-coverage-low", type=float,
        default=_PLACEHOLDER_DEFAULTS["attribution_coverage_low"],
        help=(
            "Pessimistic coverage. Default 0.65 — exercises the regime "
            "below directive §7's 80% floor."
        ),
    )
    p.add_argument(
        "--attribution-coverage-high", type=float,
        default=_PLACEHOLDER_DEFAULTS["attribution_coverage_high"],
        help=(
            "Optimistic coverage. Default 0.95 — programmatic-"
            "attribution practical ceiling."
        ),
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
        attribution=AttributionParameters(
            coverage=args.attribution_coverage,
            coverage_low=args.attribution_coverage_low,
            coverage_high=args.attribution_coverage_high,
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
