#!/usr/bin/env python3
"""Smoke test M2 (CausalForestDML) + M3 (PyMC + NumPyro) libs end-to-end.

Run this BEFORE deploying to verify the M2/M3 fit pipelines actually work
in the current Python environment. Synthetic data only — does NOT touch
Aura. Exits 0 on success, 1 on any failure.

Usage:
    python3 scripts/smoke_test_m2_m3_libs.py

Why this exists:
    Tasks 34 (HB nightly refit) and 35 (CF weekly fit) were shipped
    2026-04-29 (commits ec8c489), but their fit functions raise
    LibsMissingError until pymc + numpyro + econml are installed AND
    their transitive dependency graph resolves cleanly. The pinning
    surface is fragile (numpyro/jax compat, scipy/statsmodels compat);
    this script confirms the current env can actually fit before the
    daily scheduler runs the live tasks.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

# Make the script runnable from any cwd by adding the project root to sys.path.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import numpy as np


def test_m3_hierarchical_bayes() -> bool:
    """Synthetic HB fit. Returns True on pass."""
    np.random.seed(42)
    from adam.intelligence.hierarchical_bayes import (
        HierarchicalObservation,
        fit_hierarchical_model,
    )
    import adam.intelligence.hierarchical_bayes as hb_mod

    obs = []
    true_p = {
        "saver": {"social_proof": 0.05, "authority": 0.03},
        "spender": {"social_proof": 0.08, "authority": 0.06},
        "loyalist": {"social_proof": 0.06, "authority": 0.07},
    }
    for archetype in ["saver", "spender", "loyalist"]:
        for mechanism in ["social_proof", "authority"]:
            for category in ["luxury", "tech", "auto", "travel"]:
                for _ in range(50):
                    p = true_p[archetype][mechanism]
                    obs.append(HierarchicalObservation(
                        archetype=archetype,
                        mechanism=mechanism,
                        category=category,
                        success=int(np.random.random() < p),
                    ))

    # Fast smoke: 200/200/2 instead of production 1500/2000/4
    hb_mod._NUTS_PARAMS = {
        "draws": 200, "tune": 200, "target_accept": 0.9, "chains": 2,
    }
    cells, diag = fit_hierarchical_model(obs)

    print(f"M3 HB:  cells={diag.cells_recovered}  "
          f"r_hat_max={diag.r_hat_max:.3f}  "
          f"divergences={diag.divergences}  "
          f"errors={len(diag.errors)}")

    if diag.cells_recovered == 0:
        print("  FAIL: no cells recovered")
        return False
    if diag.r_hat_max > 1.20:
        print(f"  FAIL: r_hat_max {diag.r_hat_max} > 1.20")
        return False
    if len(diag.errors) > 0:
        print(f"  FAIL: errors: {diag.errors[:3]}")
        return False
    return True


def test_m2_causal_forest() -> bool:
    """Synthetic CF fit. Returns True on pass."""
    np.random.seed(42)
    from adam.intelligence.causal_forest import (
        LoggedDecisionRow,
        fit_causal_forest_for_cell,
    )

    rows = []
    for i in range(200):
        treated = i % 2
        context = {
            "device_type_score": float(np.random.random()),
            "tod_normalized": float(np.random.random()),
            "posture_score": float(np.random.random()),
        }
        base = 0.04
        te = 0.05 if treated else 0.0
        outcome = float(np.random.random() < base + te)
        rows.append(LoggedDecisionRow(
            archetype="saver", mechanism="social_proof", category="luxury",
            user_id=f"u{i}", context_features=context,
            treatment=treated, outcome=outcome, propensity=0.5,
            pscore_known=True, timestamp_ms=int(time.time() * 1000),
        ))

    result = fit_causal_forest_for_cell(rows)
    print(f"M2 CF:  n_events={result.n_events}  "
          f"tau_hat={result.tau_hat:.4f}  "
          f"95%CI=[{result.tau_lower:.3f}, {result.tau_upper:.3f}]  "
          f"underpowered={result.cell_under_powered}")

    if result.n_events == 0:
        print("  FAIL: no events processed")
        return False
    if result.cell_under_powered:
        print(f"  WARN: underpowered (expected for n=200; not a fail)")
    return True


def main() -> int:
    print("=" * 60)
    print("M2 + M3 lib smoke test — synthetic data only")
    print("=" * 60)

    # Library version banner
    try:
        import pymc, numpyro, econml, jax, statsmodels
        print(
            f"pymc {pymc.__version__} | "
            f"numpyro {numpyro.__version__} | "
            f"econml {econml.__version__} | "
            f"jax {jax.__version__} | "
            f"statsmodels {statsmodels.__version__}"
        )
    except ImportError as exc:
        print(f"FATAL: missing M2/M3 lib: {exc}")
        return 1

    print()
    m3_ok = test_m3_hierarchical_bayes()
    print()
    m2_ok = test_m2_causal_forest()
    print()

    if m3_ok and m2_ok:
        print("=" * 60)
        print("ALL SMOKE TESTS PASSED — M2 + M3 ready for production")
        print("=" * 60)
        return 0
    else:
        print("=" * 60)
        print("SMOKE TEST FAILURE — see output above")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())
