#!/usr/bin/env python3
"""Phase 9 sweep executor — closes wrap-out hard-stop criterion (i).

Runs the 5-architecture × 2-horizon LHS sweep over the directive
Appendix A 7-grid space and persists the result as a JSON-lines
artifact under artifacts/phase_9_sweep/.

Per the wrap-out greenlight: the actual run uses REDUCED audience
sizes (capped at 50 per cohort) so the substrate-validating sweep
completes in reasonable time. Full-LUXY-scale execution at
audience=10000 is a separate operational slice.

Usage:
    python3 scripts/run_phase_9_sweep.py
    python3 scripts/run_phase_9_sweep.py --n-samples-lhs 25 --audience-cap 30
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from typing import Dict


def _build_factories(propensity_mc: int) -> Dict:
    """Default 5 architectures with E using a small MC sample count
    so the sweep runs in tractable time."""
    from adam.intelligence.simulation import (
        FullProposedStack,
        FullStackPlusCounterfactual,
        MarginalAdditiveBaseline,
        TrilateralCascadeOnly,
        TrilateralWithInteraction,
    )
    return {
        "A_marginal_additive": lambda seed: (
            MarginalAdditiveBaseline(seed=seed)
        ),
        "B_trilateral_cascade_only": lambda seed: (
            TrilateralCascadeOnly(seed=seed)
        ),
        "C_trilateral_plus_interaction": lambda seed: (
            TrilateralWithInteraction(seed=seed)
        ),
        "D_full_proposed_stack": lambda seed: (
            FullProposedStack(seed=seed)
        ),
        "E_full_stack_plus_counterfactual": lambda seed: (
            FullStackPlusCounterfactual(
                seed=seed, propensity_mc_samples=propensity_mc,
            )
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--n-samples-lhs", type=int, default=20,
        help="Number of LHS samples per (architecture × horizon). "
             "Total cells = 5 × 2 × n. Default 20 → 200 cells.",
    )
    parser.add_argument(
        "--audience-cap", type=int, default=30,
        help="Cap on audience_size_per_cohort (default 30 — keeps "
             "runtime tractable; full LUXY scale is sibling).",
    )
    parser.add_argument(
        "--horizons", type=int, nargs="+", default=[2, 4],
        help="Horizons in weeks. Default '2 4' (the wrap-out subset).",
    )
    parser.add_argument(
        "--propensity-mc", type=int, default=20,
        help="E's Monte-Carlo propensity samples per decision. "
             "Default 20 (lower = faster sweep; production v0.1 "
             "uses 50).",
    )
    parser.add_argument(
        "--seed", type=int, default=2026,
        help="Base seed for reproducible sweep.",
    )
    parser.add_argument(
        "--output", type=str, default=None,
        help="Output path. Default: "
             "artifacts/phase_9_sweep/sweep_<timestamp>.jsonl",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )
    log = logging.getLogger("run_phase_9_sweep")

    from adam.intelligence.simulation import (
        run_sweep,
        serialize_sweep_result_jsonl,
        sweep_summary,
    )

    factories = _build_factories(args.propensity_mc)
    log.info(
        "Running sweep: %d architectures × %d horizons × %d LHS samples = %d cells",
        len(factories),
        len(args.horizons),
        args.n_samples_lhs,
        len(factories) * len(args.horizons) * args.n_samples_lhs,
    )
    log.info(
        "Audience cap: %d per cohort | Propensity MC: %d | Seed: %d",
        args.audience_cap, args.propensity_mc, args.seed,
    )

    t0 = time.perf_counter()
    result = run_sweep(
        architectures=factories,
        horizons=tuple(args.horizons),
        sample_mode="lhs",
        n_samples_lhs=args.n_samples_lhs,
        base_seed=args.seed,
        audience_cap=args.audience_cap,
    )
    elapsed = time.perf_counter() - t0
    log.info("Sweep complete in %.1fs (%d cells)", elapsed, result.n_cells_total)

    # Persist artifact
    if args.output is None:
        ts = int(time.time())
        out_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "artifacts", "phase_9_sweep",
        )
        os.makedirs(out_dir, exist_ok=True)
        args.output = os.path.join(
            out_dir, f"sweep_{ts}.jsonl",
        )

    serialize_sweep_result_jsonl(result, args.output)
    log.info("Artifact written: %s (%d bytes)", args.output, os.path.getsize(args.output))

    print()
    print("=" * 110)
    print("PHASE 9 SWEEP SUMMARY")
    print("=" * 110)
    print(f"Cells: {result.n_cells_total}  | "
          f"Mode: {result.sample_mode}  | "
          f"Elapsed: {elapsed:.1f}s")
    print()
    print(sweep_summary(result))
    print()
    print("=" * 110)
    print("Per-architecture cumulative-lift distribution:")
    print("=" * 110)
    dist = result.cumulative_lift_distribution()
    for arch in result.architectures_compared:
        lifts = dist.get(arch, [])
        if not lifts:
            continue
        sorted_l = sorted(lifts)
        n = len(sorted_l)
        med = sorted_l[n // 2]
        p25 = sorted_l[n // 4]
        p75 = sorted_l[(3 * n) // 4]
        mean_lift = sum(lifts) / n
        print(
            f"  {arch:<40}  n={n}  "
            f"mean={mean_lift:+.4f}  "
            f"med={med:+.4f}  "
            f"p25/p75=[{p25:+.4f}, {p75:+.4f}]"
        )

    print()
    print("=" * 110)
    print("Counterfactual-trace ESS multiplier (E only, vs raw N):")
    print("=" * 110)
    ess_mults = result.counterfactual_ess_multiplier_distribution()
    if ess_mults:
        sorted_e = sorted(ess_mults)
        n = len(sorted_e)
        print(
            f"  n_cells={n}  "
            f"mean={sum(ess_mults)/n:.4f}  "
            f"med={sorted_e[n // 2]:.4f}  "
            f"min={sorted_e[0]:.4f}  "
            f"max={sorted_e[-1]:.4f}"
        )
    else:
        print("  (no E cells in this sweep)")

    print()
    print("=" * 110)
    print("Non-stationarity recovery curve (ABRUPT_SWITCHING cells only):")
    print("=" * 110)
    recovery = result.non_stationarity_recovery_curve()
    if not recovery:
        print("  (no ABRUPT_SWITCHING cells produced observable recovery — "
              "may indicate horizons too short for post-switch recovery; "
              "expand horizons or increase n_samples to surface the curve)")
    for arch, hours in recovery.items():
        if not hours:
            continue
        sorted_h = sorted(hours)
        n = len(sorted_h)
        print(
            f"  {arch:<40}  n={n}  "
            f"mean_hours={sum(hours)/n:.1f}  "
            f"med={sorted_h[n // 2]:.1f}  "
            f"min={sorted_h[0]:.1f}  "
            f"max={sorted_h[-1]:.1f}"
        )

    print()
    print("Artifact: " + args.output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
