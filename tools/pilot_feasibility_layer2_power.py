#!/usr/bin/env python3
"""Path C Layer 2 — fixed-n statistical power calc for the LUXY pilot's
primary endpoint (directive §G.2 OSF Pre-Registration → sample-size
feasibility decomposition).

Composes on Layer 1's JSON output (P.1.L1 + G.2.1.attr extension) by
reading the 27-cell sensitivity table and computing per-cell
statistical power for detecting an MDE-of-interest.

Three-layer composition:
  Layer 1 (P.1.L1 + G.2.1.attr): mechanical attributable conversion
                                  count + Wilson 95% CI + 3×3×3
                                  sensitivity table.
  Layer 2 (this slice, G.2.2):   fixed-n statistical power per cell;
                                  per-cell verdict + top-level verdict;
                                  design-effect sensitivity side-table.
  Layer 3 (subsequent, G.2.3):   cell-level feasibility against A14
                                  retirement-trigger thresholds.

Why fixed-n now: directive §G.2 specifies always-valid sequential
methods (Howard-Ramdas confidence sequences; Johari-Pekelis-Walsh
mixture SPRT; Waudby-Smith e-process) for live analysis. Fixed-n is
the load-bearing FLOOR for sample-size feasibility — "do we have
enough volume" gets a clean binary answer under classical assumptions
before sequential machinery adds robustness. G.2.2.seq composes on
this fixed-n floor.

Math:
  Two-proportion z-test, unpooled-variance approximation (Cohen 1988
  *Statistical Power Analysis for the Behavioral Sciences* §6;
  textbook convention for OSF pre-registration sample-size
  justification):

      z_a       = Phi^{-1}(1 - alpha / 2)              # two-sided crit
      z_b       = Phi^{-1}(power)                       # target z
      var       = p1 (1 - p1) + p2 (1 - p2)             # sum of arm vars
      delta     = |p2 - p1|
      power(n)  = Phi(delta sqrt(n / var) - z_a)        # one-tail approx
      n(power)  = (z_a + z_b)^2 var / delta^2           # solve for n

  Effective per-arm n is then inflated by the IPSW design-effect
  multiplier (default 1.3 — typical IPSW efficiency loss):

      n_eff = ceil(n_classical * design_effect)

  Cross-check vs `statsmodels.stats.power.NormalIndPower` requires
  one-sided `alternative='larger'` with `alpha = alpha_user / 2` to
  match the upper-tail-only convention shipped here (the two-sided
  statsmodels form includes a small lower-tail correction that the
  Cohen 1988 textbook formula omits).

Per-cell verdict (against design.power target):
  feasible:     power_at_mde >= target
  marginal:     0.5 * target <= power_at_mde < target
  underpowered: power_at_mde < 0.5 * target

Top-level verdict:
  underpowered if any cell is underpowered;
  marginal if no underpowered cells but ≥1 marginal;
  feasible only if all 27 cells are feasible.

Design-effect sensitivity side-table: re-runs the 27-cell calc under
design_effect ∈ {1.0, 1.3, 1.7}; reports verdict + min_power across
cells per row. Surfaces IPSW efficiency-loss sensitivity without
expanding the main table to 81 cells.

References:
  Cohen 1988, *Statistical Power Analysis for the Behavioral Sciences*
    (2nd ed., Erlbaum, §6 — two-proportion power derivation).
  statsmodels.stats.power.NormalIndPower (used as cross-check
    reference in tests, NOT as production code — avoids transitive
    statsmodels runtime dependency).
  Directive §G.2 (OSF Pre-Registration → primary endpoint = IPSW-
    corrected weighted conversion rate; sequential methods for live
    analysis composed on this fixed-n floor by G.2.2.seq).
  Directive §0.5 #5 + §S8.4 (sapid attribution context, propagated
    via Layer 1's attributable-vs-gross distinction).
"""
# Note: deliberately NOT using `from __future__ import annotations` —
# importlib + Pydantic v2 + stringified annotations don't compose
# (lesson from P.1.L1 + G.2.1.attr).

import argparse
import json
import math
import sys
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from pydantic import BaseModel, Field, model_validator
from scipy.optimize import brentq
from scipy.stats import norm


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class ExperimentalDesign(BaseModel):
    """Experimental-design knobs.

    `alpha` — two-sided significance level (default 0.05).
    `power` — target statistical power (default 0.80).
    `allocation_ratio` — n_treatment / n_control (default 1.0 = balanced).
        Affects only the per-arm split; the test math here assumes
        equal n per arm. Future work could extend.
    `design_effect` — IPSW efficiency-loss inflation factor (default 1.3).
        Multiplies the classical n. Must be ≥ 1.0; values < 1.0 would
        imply IPSW *increases* effective sample size, which is not
        consistent with the canonical IPSW variance-inflation result.
    """

    alpha: float = Field(default=0.05, gt=0, lt=1)
    power: float = Field(default=0.80, gt=0, lt=1)
    allocation_ratio: float = Field(default=1.0, gt=0)
    design_effect: float = Field(default=1.3, ge=1.0)


ExperimentalDesign.model_rebuild()


class PrimaryEndpoint(BaseModel):
    """Primary endpoint specification.

    `baseline_cr` is the control-arm conversion rate; the (low/high)
    triple bracket parameter uncertainty. Exactly one of
    `mde_relative` (e.g., 0.10 = 10% lift over baseline) or
    `mde_absolute` (e.g., 0.005 = 0.5pp absolute lift) must be
    supplied — they are equivalent expressions of the same minimum
    detectable effect.
    """

    baseline_cr: float = Field(gt=0, lt=1)
    baseline_cr_low: float = Field(gt=0, lt=1)
    baseline_cr_high: float = Field(gt=0, lt=1)
    mde_relative: Optional[float] = Field(default=None, gt=0)
    mde_absolute: Optional[float] = Field(default=None, gt=0)

    @model_validator(mode="after")
    def _check(self) -> "PrimaryEndpoint":
        if (self.mde_relative is None) == (self.mde_absolute is None):
            raise ValueError(
                "exactly one of mde_relative or mde_absolute is required"
            )
        if not (
            self.baseline_cr_low <= self.baseline_cr <= self.baseline_cr_high
        ):
            raise ValueError(
                f"baseline_cr brackets must satisfy low ≤ point ≤ high; got "
                f"low={self.baseline_cr_low!r}, point={self.baseline_cr!r}, "
                f"high={self.baseline_cr_high!r}"
            )
        return self

    def resolved_mde_absolute(self) -> float:
        """Absolute MDE — derives from mde_relative * baseline_cr if
        mde_relative was supplied; otherwise returns mde_absolute."""
        if self.mde_relative is not None:
            return self.baseline_cr * self.mde_relative
        return self.mde_absolute  # type: ignore[return-value]


PrimaryEndpoint.model_rebuild()


class Layer2Inputs(BaseModel):
    layer_1_output_path: str
    design: ExperimentalDesign
    endpoint: PrimaryEndpoint


Layer2Inputs.model_rebuild()


# ---------------------------------------------------------------------------
# Power primitives (Cohen 1988)
# ---------------------------------------------------------------------------

def power_at(
    n_per_arm: float,
    p1: float,
    p2: float,
    alpha: float,
) -> float:
    """Statistical power of the two-proportion z-test at sample size
    `n_per_arm` per arm under unpooled-variance approximation.

        power = Phi(delta sqrt(n / var) - z_alpha/2)
        var = p1 (1 - p1) + p2 (1 - p2)
        delta = |p2 - p1|

    Returns power in [0, 1]. Two-sided test convention: `z_alpha/2`
    is the critical value, but only the upper tail of the alternative
    distribution is counted (Cohen 1988 §6; the omitted lower tail is
    negligible at non-trivial effect sizes).
    """
    if n_per_arm <= 0:
        raise ValueError(f"n_per_arm must be positive, got {n_per_arm!r}")
    if not 0.0 < p1 < 1.0:
        raise ValueError(f"p1 must be in (0, 1), got {p1!r}")
    if not 0.0 < p2 < 1.0:
        raise ValueError(f"p2 must be in (0, 1), got {p2!r}")
    if not 0.0 < alpha < 1.0:
        raise ValueError(f"alpha must be in (0, 1), got {alpha!r}")

    var = p1 * (1.0 - p1) + p2 * (1.0 - p2)
    if var <= 0:  # only at p1, p2 ∈ {0, 1} — already excluded above
        return 1.0
    delta = abs(p2 - p1)
    z_a = float(norm.ppf(1.0 - alpha / 2.0))
    z_under_alt = delta * math.sqrt(n_per_arm / var) - z_a
    return float(norm.cdf(z_under_alt))


def n_for_mde_power(
    p1: float,
    mde: float,
    alpha: float,
    power: float,
    *,
    design_effect: float = 1.0,
) -> int:
    """Required per-arm sample size for the named MDE at the named
    power, with optional IPSW design-effect inflation.

        n_classical = (z_alpha/2 + z_power)^2 var / delta^2
        n_eff = ceil(n_classical * design_effect)
    """
    if mde <= 0:
        raise ValueError(f"mde must be positive, got {mde!r}")
    p2 = p1 + mde
    if p2 >= 1.0:
        raise ValueError(
            f"p1 + mde must be < 1.0, got p1={p1!r}, mde={mde!r}"
        )
    if not 0.0 < alpha < 1.0:
        raise ValueError(f"alpha must be in (0, 1), got {alpha!r}")
    if not 0.0 < power < 1.0:
        raise ValueError(f"power must be in (0, 1), got {power!r}")
    if design_effect < 1.0:
        raise ValueError(
            f"design_effect must be >= 1.0, got {design_effect!r}"
        )

    z_a = float(norm.ppf(1.0 - alpha / 2.0))
    z_b = float(norm.ppf(power))
    var = p1 * (1.0 - p1) + p2 * (1.0 - p2)
    n_classical = (z_a + z_b) ** 2 * var / mde ** 2
    return int(math.ceil(n_classical * design_effect))


def mde_at_power(
    n_per_arm: float,
    p1: float,
    alpha: float,
    power: float,
) -> Optional[float]:
    """Solve for the absolute MDE achievable at the named power and n.

    Brent's method on f(delta) = power_at(n, p1, p1+delta, alpha) - power
    over delta ∈ [eps, 1 - p1 - eps]. Reports the positive direction
    (lift) only. Returns `None` if the bracket has same-sign endpoints
    (target power exceeds achievable maximum at the given n) — that
    cell is then "best-case unachievable" rather than algorithmically
    failed.
    """
    if n_per_arm <= 0:
        raise ValueError(f"n_per_arm must be positive, got {n_per_arm!r}")
    eps = 1e-6
    delta_max = 1.0 - p1 - eps
    if delta_max <= eps:
        return None

    def f(delta: float) -> float:
        return power_at(n_per_arm, p1, p1 + delta, alpha) - power

    try:
        f_lo = f(eps)
        f_hi = f(delta_max)
        if f_lo * f_hi > 0:
            # Same-sign endpoints — target power not bracketed.
            return None
        delta = float(brentq(f, eps, delta_max, xtol=1e-7))
        return delta
    except (ValueError, RuntimeError):
        return None


# ---------------------------------------------------------------------------
# Layer 1 ingestion + per-cell processing
# ---------------------------------------------------------------------------

def load_layer_1_output(path: str) -> dict:
    """Load Layer 1 JSON. Raises FileNotFoundError if the path does
    not exist (propagates out of main with a useful traceback)."""
    with open(path) as f:
        return json.load(f)


def _layer_1_provenance(layer_1: dict, path: str) -> dict:
    """Provenance summary of the Layer 1 input — path + computed_at +
    impression_pool (the campaign-identifying summary; Layer 1 has no
    explicit campaign_id field but impression_pool serves as a
    sufficient discriminator at this point in the pipeline)."""
    inputs = layer_1.get("inputs", {})
    campaign = inputs.get("campaign", {})
    return {
        "path": path,
        "computed_at": layer_1.get("computed_at"),
        "impression_pool": campaign.get("impression_pool"),
        "flight_length_days": campaign.get("flight_length_days"),
    }


def process_cell(
    cell: dict,
    design: ExperimentalDesign,
    endpoint: PrimaryEndpoint,
    *,
    design_effect_override: Optional[float] = None,
) -> dict:
    """Compute Layer 2 fields for one Layer 1 sensitivity cell."""
    de = (
        design_effect_override
        if design_effect_override is not None
        else design.design_effect
    )
    total_attributable = float(cell["attributable_expected_conversions"])
    attributable_per_arm = total_attributable / (1.0 + design.allocation_ratio)
    n_eff_per_arm = attributable_per_arm / de

    p1 = endpoint.baseline_cr
    mde_abs = endpoint.resolved_mde_absolute()
    p2 = p1 + mde_abs

    if n_eff_per_arm <= 0 or p2 >= 1.0:
        # Pathological cell: negative effective n, or MDE pushes p2
        # past 1. Mark as unresolvable; verdict is underpowered.
        power = 0.0
        mde_solved: Optional[float] = None
    else:
        power = power_at(n_eff_per_arm, p1, p2, design.alpha)
        mde_solved = mde_at_power(
            n_eff_per_arm, p1, design.alpha, design.power,
        )

    target = design.power
    if power >= target:
        verdict = "feasible"
    elif power >= 0.5 * target:
        verdict = "marginal"
    else:
        verdict = "underpowered"

    out = dict(cell)  # propagate full L1 cell
    out["attributable_per_arm"] = attributable_per_arm
    out["n_eff_per_arm"] = n_eff_per_arm
    out["power_at_mde"] = power
    out["mde_at_power"] = mde_solved
    out["verdict"] = verdict
    return out


def top_verdict(per_cell: List[dict]) -> str:
    """Aggregate top-level verdict across the per-cell verdicts."""
    if any(c["verdict"] == "underpowered" for c in per_cell):
        return "underpowered"
    if any(c["verdict"] == "marginal" for c in per_cell):
        return "marginal"
    return "feasible"


def design_effect_sensitivity(
    layer_1: dict,
    design: ExperimentalDesign,
    endpoint: PrimaryEndpoint,
    *,
    sweep: Tuple[float, ...] = (1.0, 1.3, 1.7),
) -> List[dict]:
    """Re-run the per-cell calc under each design_effect in `sweep`;
    report verdict + min_power_across_cells per row."""
    cells = layer_1["sensitivity_table"]
    rows: List[dict] = []
    for de in sweep:
        per_cell = [
            process_cell(c, design, endpoint, design_effect_override=de)
            for c in cells
        ]
        rows.append({
            "design_effect": de,
            "verdict": top_verdict(per_cell),
            "min_power_across_cells": min(
                c["power_at_mde"] for c in per_cell
            ),
        })
    return rows


# ---------------------------------------------------------------------------
# Top-level computation
# ---------------------------------------------------------------------------

def compute_layer_2(
    layer_1: dict,
    inputs: Layer2Inputs,
) -> dict:
    cells = layer_1["sensitivity_table"]
    per_cell = [
        process_cell(c, inputs.design, inputs.endpoint) for c in cells
    ]
    sensitivity = design_effect_sensitivity(
        layer_1, inputs.design, inputs.endpoint,
    )

    endpoint_dump = inputs.endpoint.model_dump()
    endpoint_dump["resolved_mde_absolute"] = inputs.endpoint.resolved_mde_absolute()

    return {
        "computed_at": datetime.now(timezone.utc).isoformat(),
        "layer_1_provenance": _layer_1_provenance(
            layer_1, inputs.layer_1_output_path,
        ),
        "design": inputs.design.model_dump(),
        "endpoint": endpoint_dump,
        "per_cell": per_cell,
        "design_effect_sensitivity": sensitivity,
        "verdict": top_verdict(per_cell),
        "interpretation_hooks": {
            # Layer 3 (G.2.3, deferred) will consume per-cell verdicts +
            # n_eff_per_arm to evaluate against A14 retirement-trigger
            # thresholds (e.g., MECHANISM_PHARMACOLOGY_LITERATURE_MIDPOINTS_
            # PILOT_PENDING needs ≥50 multi-exposure decisions per
            # mechanism). The slot is named here so Layer 3 wires
            # by-name, not by position.
            "layer_3_input": None,
        },
    }


# ---------------------------------------------------------------------------
# Output rendering
# ---------------------------------------------------------------------------

def render_text_summary(payload: dict) -> str:
    rule = "=" * 78
    sub = "-" * 78
    design = payload["design"]
    endpoint = payload["endpoint"]
    lines = [
        rule,
        "Layer 2 — fixed-n statistical power",
        rule,
        f"Layer 1 input:        {payload['layer_1_provenance']['path']}",
        f"Layer 1 computed_at:  {payload['layer_1_provenance']['computed_at']}",
        f"Impression pool:      "
        f"{payload['layer_1_provenance']['impression_pool']:,}",
        "",
        f"alpha={design['alpha']}  target power={design['power']}  "
        f"allocation={design['allocation_ratio']}  "
        f"design_effect={design['design_effect']}",
        f"baseline_cr={endpoint['baseline_cr']}  "
        f"resolved MDE (absolute)={endpoint['resolved_mde_absolute']:.5f}",
        "",
        f"TOP-LEVEL VERDICT: {payload['verdict'].upper()}",
        "",
        "PER-CELL COUNTS (out of 27):",
        sub,
    ]
    counts = {"feasible": 0, "marginal": 0, "underpowered": 0}
    for c in payload["per_cell"]:
        counts[c["verdict"]] += 1
    for v in ("feasible", "marginal", "underpowered"):
        lines.append(f"  {v}: {counts[v]}")

    lines.append("")
    lines.append("DESIGN-EFFECT SENSITIVITY:")
    lines.append(sub)
    for row in payload["design_effect_sensitivity"]:
        lines.append(
            f"  design_effect={row['design_effect']:.1f}  "
            f"verdict={row['verdict']:<13s}  "
            f"min_power_across_cells={row['min_power_across_cells']:.4f}"
        )
    lines.append(rule)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _build_argparser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument(
        "--layer-1-input", type=str, required=True,
        help="Path to Layer 1 JSON output (P.1.L1 / G.2.1.attr emit_json_payload).",
    )
    p.add_argument("--alpha", type=float, default=0.05)
    p.add_argument("--power", type=float, default=0.80)
    p.add_argument("--allocation-ratio", type=float, default=1.0)
    p.add_argument(
        "--design-effect", type=float, default=1.3,
        help="IPSW efficiency-loss inflation factor (default 1.3).",
    )
    p.add_argument("--baseline-cr", type=float, required=True)
    p.add_argument("--baseline-cr-low", type=float, required=True)
    p.add_argument("--baseline-cr-high", type=float, required=True)
    p.add_argument(
        "--mde-relative", type=float, default=None,
        help="Relative MDE (e.g., 0.10 = 10% lift). "
             "Mutually exclusive with --mde-absolute.",
    )
    p.add_argument(
        "--mde-absolute", type=float, default=None,
        help="Absolute MDE (e.g., 0.005 = 0.5pp). "
             "Mutually exclusive with --mde-relative.",
    )
    p.add_argument(
        "--output", type=str, default=None,
        help="JSON output path. If omitted, only stdout summary is printed.",
    )
    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = _build_argparser().parse_args(argv)

    if (args.mde_relative is None) == (args.mde_absolute is None):
        print(
            "ERROR: exactly one of --mde-relative or --mde-absolute required",
            file=sys.stderr,
        )
        return 2

    layer_1 = load_layer_1_output(args.layer_1_input)

    inputs = Layer2Inputs(
        layer_1_output_path=args.layer_1_input,
        design=ExperimentalDesign(
            alpha=args.alpha,
            power=args.power,
            allocation_ratio=args.allocation_ratio,
            design_effect=args.design_effect,
        ),
        endpoint=PrimaryEndpoint(
            baseline_cr=args.baseline_cr,
            baseline_cr_low=args.baseline_cr_low,
            baseline_cr_high=args.baseline_cr_high,
            mde_relative=args.mde_relative,
            mde_absolute=args.mde_absolute,
        ),
    )

    payload = compute_layer_2(layer_1, inputs)
    print(render_text_summary(payload))

    if args.output:
        with open(args.output, "w") as f:
            json.dump(payload, f, indent=2)
        print(f"\nWrote {args.output}")
    return 0


# Forward-ref rebuild — needed because the test suite loads this module
# via importlib.util.spec_from_file_location, and Pydantic v2's
# nested-BaseModel field resolution can stumble on that loader without
# explicit rebuild calls.
ExperimentalDesign.model_rebuild()
PrimaryEndpoint.model_rebuild()
Layer2Inputs.model_rebuild()


if __name__ == "__main__":
    sys.exit(main())
