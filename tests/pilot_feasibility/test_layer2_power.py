"""Tests for Path C Layer 2 — fixed-n statistical power
(tools/pilot_feasibility_layer2_power.py).

Directive-anchored: §G.2 OSF Pre-Registration → sample-size feasibility.
Predecessor: G.2.1.attr (a9a5be7) — Layer 1 attributable conversion
count + 3×3×3 sensitivity table.
"""
import importlib.util
import json
import math
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import pytest
from pydantic import ValidationError
from statsmodels.stats.power import NormalIndPower


# Load the tool module by file path (same pattern as L1).
_TOOL_PATH = (
    Path(__file__).resolve().parents[2]
    / "tools"
    / "pilot_feasibility_layer2_power.py"
)
_spec = importlib.util.spec_from_file_location(
    "pilot_feasibility_layer2_power", str(_TOOL_PATH),
)
assert _spec is not None and _spec.loader is not None
layer2 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(layer2)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _es_unpooled(p1: float, p2: float) -> float:
    """Standardized effect size matching the pooled-variance convention
    that NormalIndPower.power(alternative='larger', alpha=alpha/2) will
    reproduce. Per the module docstring, the Cohen 1988 textbook
    formula is the upper-tail-only approximation; statsmodels' two-sided
    form includes a small lower-tail correction."""
    var = p1 * (1 - p1) + p2 * (1 - p2)
    return (p2 - p1) / math.sqrt(var / 2.0)


def _make_layer_1_fixture(
    *,
    impression_pool: int = 10_000_000,
    attributable_per_cell: Optional[List[float]] = None,
) -> dict:
    """Synthetic Layer 1 JSON with 27 cells in canonical
    (ctr, cr, coverage) order. Caller can override per-cell
    attributable counts to exercise specific power regimes."""
    if attributable_per_cell is None:
        attributable_per_cell = [10_000.0] * 27
    assert len(attributable_per_cell) == 27, (
        f"need exactly 27 attributable values, got {len(attributable_per_cell)}"
    )
    labels = ["low", "mid", "high"]
    ctrs = [0.0008, 0.0015, 0.0025]
    crs = [0.02, 0.05, 0.08]
    coverages = [0.65, 0.85, 0.95]
    sens = []
    i = 0
    for ctr_idx in range(3):
        for cr_idx in range(3):
            for cov_idx in range(3):
                attr = attributable_per_cell[i]
                sens.append({
                    "ctr": ctrs[ctr_idx],
                    "ctr_label": labels[ctr_idx],
                    "cr": crs[cr_idx],
                    "cr_label": labels[cr_idx],
                    "coverage": coverages[cov_idx],
                    "coverage_label": labels[cov_idx],
                    "gross_expected_conversions": attr / coverages[cov_idx],
                    "attributable_expected_conversions": attr,
                    "wilson_ci_95": [0.0, 1.0],
                    "gross_wilson_ci_95": [0.0, 1.0],
                })
                i += 1
    return {
        "computed_at": "2026-05-06T12:00:00+00:00",
        "inputs": {
            "campaign": {
                "impression_pool": impression_pool,
                "flight_length_days": 90,
            },
            "funnel": {},
            "attribution": {},
            "confidence_level": 0.95,
        },
        "point_estimate": {
            "expected_clicks": 0.0,
            "gross_expected_conversions": 0.0,
            "attributable_expected_conversions":
                sum(attributable_per_cell) / 27,
            "wilson_ci_95": [0.0, 1.0],
            "wilson_ci_lo_count": 0.0,
            "wilson_ci_hi_count": 0.0,
            "gross_wilson_ci_95": [0.0, 1.0],
        },
        "sensitivity_table": sens,
        "interpretation_hooks": {
            "layer_2_power_input": sum(attributable_per_cell) / 27,
            "layer_3_cell_input": None,
        },
    }


def _make_inputs(
    *,
    alpha: float = 0.05,
    power: float = 0.80,
    allocation_ratio: float = 1.0,
    design_effect: float = 1.3,
    baseline_cr: float = 0.05,
    baseline_cr_low: float = 0.02,
    baseline_cr_high: float = 0.08,
    mde_relative: Optional[float] = 0.10,
    mde_absolute: Optional[float] = None,
    layer_1_path: str = "/tmp/synthetic_layer_1.json",
) -> "layer2.Layer2Inputs":
    return layer2.Layer2Inputs(
        layer_1_output_path=layer_1_path,
        design=layer2.ExperimentalDesign(
            alpha=alpha, power=power,
            allocation_ratio=allocation_ratio,
            design_effect=design_effect,
        ),
        endpoint=layer2.PrimaryEndpoint(
            baseline_cr=baseline_cr,
            baseline_cr_low=baseline_cr_low,
            baseline_cr_high=baseline_cr_high,
            mde_relative=mde_relative,
            mde_absolute=mde_absolute,
        ),
    )


# ---------------------------------------------------------------------------
# Power vs statsmodels
# ---------------------------------------------------------------------------

class TestPowerCrossCheck:
    def test_power_at_matches_statsmodels(self) -> None:
        """power_at(n=1000, p1=0.05, p2=0.075, alpha=0.05) matches
        NormalIndPower(alternative='larger', alpha=alpha/2) within 1e-6."""
        n, p1, p2, alpha = 1000, 0.05, 0.075, 0.05
        my_power = layer2.power_at(n, p1, p2, alpha)
        es = _es_unpooled(p1, p2)
        sm_power = NormalIndPower().power(
            effect_size=es, nobs1=n, alpha=alpha / 2.0,
            ratio=1.0, alternative="larger",
        )
        assert my_power == pytest.approx(sm_power, abs=1e-6)

    def test_n_for_mde_matches_statsmodels(self) -> None:
        """n_for_mde_power(p1=0.05, mde=0.005, alpha=0.05, power=0.80)
        matches NormalIndPower.solve_power within 1.0 sample (ceiling
        vs float)."""
        p1, mde, alpha, power = 0.05, 0.005, 0.05, 0.80
        my_n = layer2.n_for_mde_power(p1, mde, alpha, power, design_effect=1.0)
        es = _es_unpooled(p1, p1 + mde)
        sm_n = NormalIndPower().solve_power(
            effect_size=es, alpha=alpha / 2.0, power=power,
            ratio=1.0, alternative="larger",
        )
        assert abs(my_n - sm_n) <= 1.0


class TestPowerAt:
    def test_power_increases_with_n(self) -> None:
        p1, p2, alpha = 0.05, 0.075, 0.05
        ns = [500, 1_000, 2_000, 5_000, 10_000]
        powers = [layer2.power_at(n, p1, p2, alpha) for n in ns]
        for prior, current in zip(powers, powers[1:]):
            assert current > prior

    def test_power_increases_with_mde(self) -> None:
        n, p1, alpha = 1000, 0.05, 0.05
        mdes = [0.005, 0.01, 0.02, 0.04]
        powers = [
            layer2.power_at(n, p1, p1 + mde, alpha) for mde in mdes
        ]
        for prior, current in zip(powers, powers[1:]):
            assert current > prior

    def test_power_at_zero_effect_equals_alpha_over_two(self) -> None:
        """At p1 == p2, the upper-tail-only power approximation reduces
        to alpha/2 (the upper-tail rejection probability under H0)."""
        n, p1, alpha = 1000, 0.05, 0.05
        # Use a tiny epsilon so var > 0 — at exact equality the function
        # would return 1.0 by the var-zero short-circuit.
        eps = 1e-12
        p2 = p1 + eps
        power = layer2.power_at(n, p1, p2, alpha)
        assert power == pytest.approx(alpha / 2.0, abs=1e-6)

    def test_rejects_invalid_inputs(self) -> None:
        with pytest.raises(ValueError):
            layer2.power_at(0, 0.05, 0.075, 0.05)
        with pytest.raises(ValueError):
            layer2.power_at(1000, 0.0, 0.075, 0.05)
        with pytest.raises(ValueError):
            layer2.power_at(1000, 0.05, 1.0, 0.05)
        with pytest.raises(ValueError):
            layer2.power_at(1000, 0.05, 0.075, 0.0)


class TestNForMdePower:
    def test_n_decreases_with_mde(self) -> None:
        """Larger MDE → smaller required n."""
        p1, alpha, power = 0.05, 0.05, 0.80
        mdes = [0.002, 0.005, 0.01, 0.02]
        ns = [
            layer2.n_for_mde_power(p1, mde, alpha, power, design_effect=1.0)
            for mde in mdes
        ]
        for prior, current in zip(ns, ns[1:]):
            assert current < prior

    def test_design_effect_inflates_n_linearly(self) -> None:
        """At design_effect=2.0, required n is exactly 2x the
        design_effect=1.0 case (within the ceiling)."""
        p1, mde, alpha, power = 0.05, 0.005, 0.05, 0.80
        n_de1 = layer2.n_for_mde_power(p1, mde, alpha, power, design_effect=1.0)
        n_de2 = layer2.n_for_mde_power(p1, mde, alpha, power, design_effect=2.0)
        assert abs(n_de2 - 2 * n_de1) <= 1

    def test_rejects_invalid_inputs(self) -> None:
        with pytest.raises(ValueError):
            layer2.n_for_mde_power(0.05, 0.005, 0.05, 0.80, design_effect=0.5)
        with pytest.raises(ValueError):
            layer2.n_for_mde_power(0.05, -0.005, 0.05, 0.80)
        with pytest.raises(ValueError):
            layer2.n_for_mde_power(0.5, 0.6, 0.05, 0.80)  # p1+mde >= 1


class TestMdeAtPower:
    def test_mde_decreases_with_n(self) -> None:
        """Larger n → smaller MDE achievable at fixed power."""
        p1, alpha, power = 0.05, 0.05, 0.80
        ns = [500, 1_000, 5_000, 10_000, 50_000]
        mdes = [
            layer2.mde_at_power(n, p1, alpha, power) for n in ns
        ]
        assert all(m is not None for m in mdes)
        for prior, current in zip(mdes, mdes[1:]):
            assert current < prior

    def test_returns_none_when_target_unreachable(self) -> None:
        """At pathologically tiny n, no MDE in (0, 1-p1) reaches the
        target power → return None rather than raising."""
        # n=2, p1=0.05, target_power=0.999 — even max MDE won't reach it
        # because max delta = 0.95 - eps and var ~ 0.06, so power max
        # ~ Phi(0.95 * sqrt(2/0.06) - 1.96) = Phi(5.49 - 1.96) ~ 0.9998.
        # Use a smaller n to guarantee unreachability.
        result = layer2.mde_at_power(1, 0.05, 0.05, 0.9999)
        assert result is None

    def test_round_trip_at_solved_mde(self) -> None:
        """If mde_at_power returns delta, then power_at(n, p1, p1+delta, alpha)
        equals the requested target power."""
        n, p1, alpha, power = 5000, 0.05, 0.05, 0.80
        delta = layer2.mde_at_power(n, p1, alpha, power)
        assert delta is not None
        round_trip = layer2.power_at(n, p1, p1 + delta, alpha)
        assert round_trip == pytest.approx(power, abs=1e-5)


# ---------------------------------------------------------------------------
# Pydantic validation
# ---------------------------------------------------------------------------

class TestPydanticValidation:
    def test_alpha_at_one_rejected(self) -> None:
        with pytest.raises(ValidationError):
            layer2.ExperimentalDesign(alpha=1.0)

    def test_power_at_zero_rejected(self) -> None:
        with pytest.raises(ValidationError):
            layer2.ExperimentalDesign(power=0.0)

    def test_allocation_ratio_zero_rejected(self) -> None:
        with pytest.raises(ValidationError):
            layer2.ExperimentalDesign(allocation_ratio=0.0)

    def test_design_effect_below_one_rejected(self) -> None:
        with pytest.raises(ValidationError):
            layer2.ExperimentalDesign(design_effect=0.9)

    def test_neither_mde_provided_rejected(self) -> None:
        with pytest.raises(ValidationError):
            layer2.PrimaryEndpoint(
                baseline_cr=0.05,
                baseline_cr_low=0.02,
                baseline_cr_high=0.08,
                # mde_relative=None, mde_absolute=None
            )

    def test_both_mde_provided_rejected(self) -> None:
        with pytest.raises(ValidationError):
            layer2.PrimaryEndpoint(
                baseline_cr=0.05,
                baseline_cr_low=0.02,
                baseline_cr_high=0.08,
                mde_relative=0.10,
                mde_absolute=0.005,
            )

    def test_baseline_cr_low_above_baseline_rejected(self) -> None:
        with pytest.raises(ValidationError):
            layer2.PrimaryEndpoint(
                baseline_cr=0.05,
                baseline_cr_low=0.07,  # > baseline
                baseline_cr_high=0.08,
                mde_relative=0.10,
            )


# ---------------------------------------------------------------------------
# Per-cell processing + verdict logic
# ---------------------------------------------------------------------------

class TestSensitivityPropagation:
    def test_propagation_emits_27_cells(self) -> None:
        layer_1 = _make_layer_1_fixture()
        inputs = _make_inputs()
        payload = layer2.compute_layer_2(layer_1, inputs)
        assert len(payload["per_cell"]) == 27

    def test_propagation_preserves_layer_1_keys(self) -> None:
        """Per-cell rows propagate the full Layer 1 cell + add Layer 2
        fields."""
        layer_1 = _make_layer_1_fixture()
        inputs = _make_inputs()
        payload = layer2.compute_layer_2(layer_1, inputs)
        for cell in payload["per_cell"]:
            for k in (
                "ctr", "ctr_label", "cr", "cr_label",
                "coverage", "coverage_label",
                "gross_expected_conversions",
                "attributable_expected_conversions",
                "attributable_per_arm", "n_eff_per_arm",
                "power_at_mde", "verdict",
            ):
                assert k in cell, f"missing key: {k}"

    def test_attributable_per_arm_at_balanced_allocation(self) -> None:
        layer_1 = _make_layer_1_fixture(
            attributable_per_cell=[1000.0] * 27,
        )
        inputs = _make_inputs(allocation_ratio=1.0)
        payload = layer2.compute_layer_2(layer_1, inputs)
        for cell in payload["per_cell"]:
            assert cell["attributable_per_arm"] == pytest.approx(500.0)


class TestTopVerdictLogic:
    def test_all_feasible_top_feasible(self) -> None:
        per_cell = [{"verdict": "feasible"}] * 27
        assert layer2.top_verdict(per_cell) == "feasible"

    def test_some_marginal_top_marginal(self) -> None:
        per_cell = (
            [{"verdict": "feasible"}] * 25
            + [{"verdict": "marginal"}] * 2
        )
        assert layer2.top_verdict(per_cell) == "marginal"

    def test_any_underpowered_top_underpowered(self) -> None:
        per_cell = (
            [{"verdict": "feasible"}] * 24
            + [{"verdict": "marginal"}] * 2
            + [{"verdict": "underpowered"}] * 1
        )
        assert layer2.top_verdict(per_cell) == "underpowered"

    def test_all_underpowered_top_underpowered(self) -> None:
        per_cell = [{"verdict": "underpowered"}] * 27
        assert layer2.top_verdict(per_cell) == "underpowered"


class TestEndToEndVerdict:
    def test_high_volume_yields_top_feasible(self) -> None:
        """All 27 cells with very high attributable count → all
        feasible → top verdict feasible."""
        layer_1 = _make_layer_1_fixture(
            attributable_per_cell=[1_000_000.0] * 27,
        )
        inputs = _make_inputs(
            baseline_cr=0.05, mde_relative=0.10,
        )
        payload = layer2.compute_layer_2(layer_1, inputs)
        assert payload["verdict"] == "feasible"

    def test_low_volume_yields_top_underpowered(self) -> None:
        """All 27 cells with tiny attributable count → all
        underpowered → top verdict underpowered."""
        layer_1 = _make_layer_1_fixture(
            attributable_per_cell=[10.0] * 27,
        )
        inputs = _make_inputs(
            baseline_cr=0.05, mde_relative=0.10,
        )
        payload = layer2.compute_layer_2(layer_1, inputs)
        assert payload["verdict"] == "underpowered"


class TestMdeRelativeAbsoluteEquivalence:
    def test_equivalent_at_same_resolved_mde(self) -> None:
        """At baseline_cr=0.05, mde_relative=0.10 ⇒ resolved MDE = 0.005,
        which equals mde_absolute=0.005. The resulting per-cell
        verdicts must agree across all 27 cells."""
        layer_1 = _make_layer_1_fixture()
        inputs_rel = _make_inputs(
            baseline_cr=0.05, mde_relative=0.10, mde_absolute=None,
        )
        inputs_abs = _make_inputs(
            baseline_cr=0.05, mde_relative=None, mde_absolute=0.005,
        )
        payload_rel = layer2.compute_layer_2(layer_1, inputs_rel)
        payload_abs = layer2.compute_layer_2(layer_1, inputs_abs)
        for cr, ca in zip(payload_rel["per_cell"], payload_abs["per_cell"]):
            assert cr["verdict"] == ca["verdict"]
            assert cr["power_at_mde"] == pytest.approx(
                ca["power_at_mde"], abs=1e-12,
            )


# ---------------------------------------------------------------------------
# Design-effect side-table
# ---------------------------------------------------------------------------

class TestDesignEffectSensitivity:
    def test_cardinality_is_three(self) -> None:
        layer_1 = _make_layer_1_fixture()
        inputs = _make_inputs()
        payload = layer2.compute_layer_2(layer_1, inputs)
        assert len(payload["design_effect_sensitivity"]) == 3
        des = [r["design_effect"] for r in payload["design_effect_sensitivity"]]
        assert des == [1.0, 1.3, 1.7]

    def test_min_power_decreases_with_design_effect(self) -> None:
        """Larger design_effect → smaller effective n → lower power."""
        layer_1 = _make_layer_1_fixture(
            attributable_per_cell=[100_000.0] * 27,
        )
        inputs = _make_inputs(baseline_cr=0.05, mde_relative=0.10)
        payload = layer2.compute_layer_2(layer_1, inputs)
        rows = payload["design_effect_sensitivity"]
        for prior, current in zip(rows, rows[1:]):
            assert current["min_power_across_cells"] < prior["min_power_across_cells"]


# ---------------------------------------------------------------------------
# JSON output schema
# ---------------------------------------------------------------------------

class TestJsonSchema:
    def test_top_level_keys(self) -> None:
        layer_1 = _make_layer_1_fixture()
        inputs = _make_inputs()
        payload = layer2.compute_layer_2(layer_1, inputs)
        for k in (
            "computed_at", "layer_1_provenance", "design", "endpoint",
            "per_cell", "design_effect_sensitivity", "verdict",
            "interpretation_hooks",
        ):
            assert k in payload

    def test_endpoint_includes_resolved_mde(self) -> None:
        layer_1 = _make_layer_1_fixture()
        inputs = _make_inputs(
            baseline_cr=0.05, mde_relative=0.10, mde_absolute=None,
        )
        payload = layer2.compute_layer_2(layer_1, inputs)
        assert payload["endpoint"]["resolved_mde_absolute"] == pytest.approx(
            0.005, rel=1e-12,
        )

    def test_iso8601_parseable(self) -> None:
        layer_1 = _make_layer_1_fixture()
        inputs = _make_inputs()
        payload = layer2.compute_layer_2(layer_1, inputs)
        dt = datetime.fromisoformat(payload["computed_at"])
        assert dt.tzinfo is not None

    def test_layer_3_input_is_none(self) -> None:
        layer_1 = _make_layer_1_fixture()
        inputs = _make_inputs()
        payload = layer2.compute_layer_2(layer_1, inputs)
        assert payload["interpretation_hooks"]["layer_3_input"] is None

    def test_provenance_has_path_and_computed_at(self) -> None:
        layer_1 = _make_layer_1_fixture(impression_pool=99_999_999)
        inputs = _make_inputs(layer_1_path="/tmp/test_l1.json")
        payload = layer2.compute_layer_2(layer_1, inputs)
        prov = payload["layer_1_provenance"]
        assert prov["path"] == "/tmp/test_l1.json"
        assert prov["impression_pool"] == 99_999_999
        assert prov["computed_at"] == "2026-05-06T12:00:00+00:00"


# ---------------------------------------------------------------------------
# CLI smoke
# ---------------------------------------------------------------------------

class TestCLISmoke:
    def test_cli_runs_against_synthetic_layer_1(self, tmp_path) -> None:
        l1_path = tmp_path / "synthetic_l1.json"
        l2_path = tmp_path / "l2_output.json"
        l1_path.write_text(json.dumps(_make_layer_1_fixture(
            attributable_per_cell=[100_000.0] * 27,
        )))
        result = subprocess.run(
            [
                sys.executable, str(_TOOL_PATH),
                "--layer-1-input", str(l1_path),
                "--alpha", "0.05",
                "--power", "0.80",
                "--baseline-cr", "0.05",
                "--baseline-cr-low", "0.02",
                "--baseline-cr-high", "0.08",
                "--mde-relative", "0.10",
                "--output", str(l2_path),
            ],
            capture_output=True, text=True, check=False,
        )
        assert result.returncode == 0, (
            f"stderr: {result.stderr}\nstdout: {result.stdout}"
        )
        payload = json.loads(l2_path.read_text())
        assert len(payload["per_cell"]) == 27
        assert payload["verdict"] in ("feasible", "marginal", "underpowered")

    def test_cli_rejects_neither_mde(self, tmp_path) -> None:
        l1_path = tmp_path / "synthetic_l1.json"
        l1_path.write_text(json.dumps(_make_layer_1_fixture()))
        result = subprocess.run(
            [
                sys.executable, str(_TOOL_PATH),
                "--layer-1-input", str(l1_path),
                "--baseline-cr", "0.05",
                "--baseline-cr-low", "0.02",
                "--baseline-cr-high", "0.08",
                # No --mde-relative or --mde-absolute
            ],
            capture_output=True, text=True, check=False,
        )
        assert result.returncode != 0
        assert "exactly one of" in result.stderr.lower()
