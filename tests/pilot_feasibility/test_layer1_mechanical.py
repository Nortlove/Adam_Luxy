"""Tests for Path C Layer 1 — mechanical conversion-count cascade
(tools/pilot_feasibility_layer1_mechanical.py).

NOT a directive-anchored slice. Path C feasibility tooling.
"""
from __future__ import annotations

import importlib.util
import json
import math
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import pytest
from pydantic import ValidationError
from statsmodels.stats.proportion import proportion_confint


# Load the tool module (it lives under tools/, not adam/, so we have to
# import it by file path).
_TOOL_PATH = (
    Path(__file__).resolve().parents[2]
    / "tools"
    / "pilot_feasibility_layer1_mechanical.py"
)
_spec = importlib.util.spec_from_file_location(
    "pilot_feasibility_layer1_mechanical", str(_TOOL_PATH),
)
assert _spec is not None and _spec.loader is not None
layer1 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(layer1)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_inputs(
    *,
    impression_pool: int = 1_000_000,
    flight_length_days: int = 30,
    ctr: float = 0.001,
    ctr_low: float = 0.0005,
    ctr_high: float = 0.002,
    cr: float = 0.1,
    cr_low: float = 0.05,
    cr_high: float = 0.15,
    coverage: float = 1.0,
    coverage_low: float = 1.0,
    coverage_high: float = 1.0,
    confidence_level: float = 0.95,
) -> "layer1.FeasibilityInputs":
    """Default coverage triple is (1.0, 1.0, 1.0) — the trivial case
    that preserves prior P.1.L1 arithmetic. Tests that intentionally
    exercise non-trivial attribution-coverage pass coverage=0.85 etc."""
    return layer1.FeasibilityInputs(
        campaign=layer1.CampaignParameters(
            impression_pool=impression_pool,
            flight_length_days=flight_length_days,
        ),
        funnel=layer1.FunnelParameters(
            click_through_rate=ctr,
            click_through_rate_low=ctr_low,
            click_through_rate_high=ctr_high,
            conversion_rate=cr,
            conversion_rate_low=cr_low,
            conversion_rate_high=cr_high,
        ),
        attribution=layer1.AttributionParameters(
            coverage=coverage,
            coverage_low=coverage_low,
            coverage_high=coverage_high,
        ),
        confidence_level=confidence_level,
    )


# ---------------------------------------------------------------------------
# Wilson score interval — closed-form vs statsmodels cross-check
# ---------------------------------------------------------------------------

class TestWilsonClosedForm:
    @pytest.mark.parametrize(
        "n,count",
        [
            (100, 5),
            (100, 50),
            (1000, 10),
            (1000, 250),
            (10_000, 75),
            (10_000, 5_000),
            (100_000, 100),
            (100_000, 50_000),
        ],
    )
    def test_matches_statsmodels(self, n: int, count: int) -> None:
        sm_lo, sm_hi = proportion_confint(
            count=count, nobs=n, alpha=0.05, method="wilson",
        )
        my_lo, my_hi = layer1.wilson_score_interval(
            n=n, p_hat=count / n, alpha=0.05,
        )
        assert my_lo == pytest.approx(sm_lo, abs=1e-9)
        assert my_hi == pytest.approx(sm_hi, abs=1e-9)

    def test_p_hat_zero_yields_zero_lower_nonzero_upper(self) -> None:
        """At p_hat = 0, Wilson lower clamps to 0; upper bound is the
        non-zero closed-form value (Wilson 1927 — strictly positive)."""
        lo, hi = layer1.wilson_score_interval(n=100, p_hat=0.0, alpha=0.05)
        assert lo == 0.0
        assert hi > 0.0
        # Closed form at p=0: hi = z²/(n + z²) per Wilson.
        z = 1.959963984540054
        expected_hi = z**2 / (100 + z**2)
        assert hi == pytest.approx(expected_hi, rel=1e-9)

    def test_p_hat_one_yields_one_upper_nonone_lower(self) -> None:
        """At p_hat = 1, Wilson upper clamps to 1; lower bound is < 1."""
        lo, hi = layer1.wilson_score_interval(n=100, p_hat=1.0, alpha=0.05)
        assert hi == 1.0
        assert lo < 1.0

    def test_extreme_small_p_within_unit_interval(self) -> None:
        """At p ≈ 7.5e-5 (the campaign regime), bounds remain in
        [0, 1] without underflow / overflow."""
        lo, hi = layer1.wilson_score_interval(
            n=50_000_000, p_hat=7.5e-5, alpha=0.05,
        )
        assert 0.0 <= lo < 7.5e-5 < hi < 1.0

    def test_rejects_non_positive_n(self) -> None:
        with pytest.raises(ValueError):
            layer1.wilson_score_interval(n=0, p_hat=0.5, alpha=0.05)

    def test_rejects_p_hat_out_of_range(self) -> None:
        with pytest.raises(ValueError):
            layer1.wilson_score_interval(n=100, p_hat=-0.1, alpha=0.05)
        with pytest.raises(ValueError):
            layer1.wilson_score_interval(n=100, p_hat=1.1, alpha=0.05)

    def test_rejects_alpha_out_of_range(self) -> None:
        with pytest.raises(ValueError):
            layer1.wilson_score_interval(n=100, p_hat=0.5, alpha=0.0)
        with pytest.raises(ValueError):
            layer1.wilson_score_interval(n=100, p_hat=0.5, alpha=1.0)


# ---------------------------------------------------------------------------
# Point estimate
# ---------------------------------------------------------------------------

class TestPointEstimate:
    def test_known_answer_million_imps(self) -> None:
        """1_000_000 imps × 0.001 CTR × 0.1 CR → 100 attributable
        conversions at coverage=1.0 (preserves prior P.1.L1 arithmetic)."""
        inputs = _make_inputs(
            impression_pool=1_000_000, ctr=0.001, cr=0.1,
        )
        point = layer1.compute_point_estimate(inputs)
        assert point.expected_clicks == pytest.approx(1000.0, rel=1e-12)
        assert point.attributable_expected_conversions == pytest.approx(
            100.0, rel=1e-12,
        )
        # At coverage=1.0, attributable equals gross.
        assert point.gross_expected_conversions == pytest.approx(
            point.attributable_expected_conversions, rel=1e-12,
        )

    def test_wilson_ci_brackets_point_estimate(self) -> None:
        inputs = _make_inputs(impression_pool=1_000_000, ctr=0.001, cr=0.1)
        point = layer1.compute_point_estimate(inputs)
        lo_count, hi_count = point.wilson_ci_lo_count, point.wilson_ci_hi_count
        assert lo_count <= point.attributable_expected_conversions <= hi_count

    def test_confidence_level_widens_interval(self) -> None:
        """Higher confidence (0.99 vs 0.95) → wider Wilson CI."""
        narrow = layer1.compute_point_estimate(
            _make_inputs(confidence_level=0.95),
        )
        wide = layer1.compute_point_estimate(
            _make_inputs(confidence_level=0.99),
        )
        narrow_width = narrow.wilson_ci_hi_count - narrow.wilson_ci_lo_count
        wide_width = wide.wilson_ci_hi_count - wide.wilson_ci_lo_count
        assert wide_width > narrow_width


# ---------------------------------------------------------------------------
# Sensitivity table
# ---------------------------------------------------------------------------

class TestSensitivityTable:
    def test_cardinality_is_twentyseven(self) -> None:
        """3×3×3 = 27 cells over (CTR, CR, coverage)."""
        sens = layer1.compute_sensitivity_table(_make_inputs())
        assert len(sens) == 27

    def test_all_label_combinations_present(self) -> None:
        sens = layer1.compute_sensitivity_table(_make_inputs())
        labels = {(c.ctr_label, c.cr_label, c.coverage_label) for c in sens}
        expected = {
            (ctr_lbl, cr_lbl, cov_lbl)
            for ctr_lbl in ("low", "mid", "high")
            for cr_lbl in ("low", "mid", "high")
            for cov_lbl in ("low", "mid", "high")
        }
        assert labels == expected

    def test_monotonicity_in_ctr_at_fixed_cr_and_coverage(self) -> None:
        """At fixed CR and coverage, attributable_expected_conversions
        strictly increases as CTR moves low → mid → high. With the
        default helper (coverage triple = 1.0), all 9 (CR, coverage)
        cells should exhibit this property over CTR; assert across all."""
        sens = layer1.compute_sensitivity_table(_make_inputs())
        for cr_lbl in ("low", "mid", "high"):
            for cov_lbl in ("low", "mid", "high"):
                row = sorted(
                    (
                        c for c in sens
                        if c.cr_label == cr_lbl and c.coverage_label == cov_lbl
                    ),
                    key=lambda c: c.ctr,
                )
                for prior, current in zip(row, row[1:]):
                    assert (
                        current.attributable_expected_conversions
                        > prior.attributable_expected_conversions
                    )

    def test_monotonicity_in_cr_at_fixed_ctr_and_coverage(self) -> None:
        """At fixed CTR and coverage, attributable_expected_conversions
        strictly increases as CR moves low → mid → high."""
        sens = layer1.compute_sensitivity_table(_make_inputs())
        for ctr_lbl in ("low", "mid", "high"):
            for cov_lbl in ("low", "mid", "high"):
                row = sorted(
                    (
                        c for c in sens
                        if c.ctr_label == ctr_lbl
                        and c.coverage_label == cov_lbl
                    ),
                    key=lambda c: c.cr,
                )
                for prior, current in zip(row, row[1:]):
                    assert (
                        current.attributable_expected_conversions
                        > prior.attributable_expected_conversions
                    )

    def test_mid_cell_matches_point_estimate(self) -> None:
        """The (CTR_mid, CR_mid, coverage_mid) sensitivity cell coincides
        with the point estimate computed from the same inputs."""
        inputs = _make_inputs()
        point = layer1.compute_point_estimate(inputs)
        sens = layer1.compute_sensitivity_table(inputs)
        mid = next(
            c for c in sens
            if c.ctr_label == "mid"
            and c.cr_label == "mid"
            and c.coverage_label == "mid"
        )
        assert mid.attributable_expected_conversions == pytest.approx(
            point.attributable_expected_conversions, rel=1e-12,
        )
        assert mid.gross_expected_conversions == pytest.approx(
            point.gross_expected_conversions, rel=1e-12,
        )


# ---------------------------------------------------------------------------
# Pydantic validation
# ---------------------------------------------------------------------------

class TestPydanticValidation:
    def test_negative_impression_pool_rejected(self) -> None:
        with pytest.raises(ValidationError):
            layer1.CampaignParameters(
                impression_pool=-1, flight_length_days=30,
            )

    def test_zero_impression_pool_rejected(self) -> None:
        with pytest.raises(ValidationError):
            layer1.CampaignParameters(
                impression_pool=0, flight_length_days=30,
            )

    def test_cr_above_one_rejected(self) -> None:
        with pytest.raises(ValidationError):
            layer1.FunnelParameters(
                click_through_rate=0.001,
                click_through_rate_low=0.0005,
                click_through_rate_high=0.002,
                conversion_rate=1.5,        # invalid
                conversion_rate_low=0.05,
                conversion_rate_high=0.99,
            )

    def test_ctr_above_one_rejected(self) -> None:
        with pytest.raises(ValidationError):
            layer1.FunnelParameters(
                click_through_rate=1.5,      # invalid (lt=1)
                click_through_rate_low=0.0005,
                click_through_rate_high=0.99,
                conversion_rate=0.1,
                conversion_rate_low=0.05,
                conversion_rate_high=0.15,
            )

    def test_ctr_low_above_ctr_rejected(self) -> None:
        with pytest.raises(ValidationError):
            layer1.FunnelParameters(
                click_through_rate=0.001,
                click_through_rate_low=0.005,    # > point
                click_through_rate_high=0.01,
                conversion_rate=0.1,
                conversion_rate_low=0.05,
                conversion_rate_high=0.15,
            )

    def test_cr_low_above_cr_rejected(self) -> None:
        with pytest.raises(ValidationError):
            layer1.FunnelParameters(
                click_through_rate=0.001,
                click_through_rate_low=0.0005,
                click_through_rate_high=0.002,
                conversion_rate=0.1,
                conversion_rate_low=0.5,        # > point
                conversion_rate_high=0.6,
            )

    def test_ctr_high_below_ctr_rejected(self) -> None:
        with pytest.raises(ValidationError):
            layer1.FunnelParameters(
                click_through_rate=0.005,
                click_through_rate_low=0.001,
                click_through_rate_high=0.002,  # < point
                conversion_rate=0.1,
                conversion_rate_low=0.05,
                conversion_rate_high=0.15,
            )

    def test_cr_high_below_cr_rejected(self) -> None:
        with pytest.raises(ValidationError):
            layer1.FunnelParameters(
                click_through_rate=0.001,
                click_through_rate_low=0.0005,
                click_through_rate_high=0.002,
                conversion_rate=0.5,
                conversion_rate_low=0.1,
                conversion_rate_high=0.2,       # < point
            )

    def test_confidence_level_out_of_range_rejected(self) -> None:
        with pytest.raises(ValidationError):
            layer1.FeasibilityInputs(
                campaign=layer1.CampaignParameters(
                    impression_pool=1000, flight_length_days=30,
                ),
                funnel=layer1.FunnelParameters(
                    click_through_rate=0.001,
                    click_through_rate_low=0.0005,
                    click_through_rate_high=0.002,
                    conversion_rate=0.1,
                    conversion_rate_low=0.05,
                    conversion_rate_high=0.15,
                ),
                confidence_level=1.0,    # not strictly < 1
            )


# ---------------------------------------------------------------------------
# JSON output schema
# ---------------------------------------------------------------------------

class TestJsonSchema:
    def test_top_level_keys_present(self) -> None:
        inputs = _make_inputs()
        point = layer1.compute_point_estimate(inputs)
        sens = layer1.compute_sensitivity_table(inputs)
        payload = layer1.emit_json_payload(inputs, point, sens)
        for key in (
            "computed_at", "inputs", "point_estimate",
            "sensitivity_table", "interpretation_hooks",
        ):
            assert key in payload

    def test_iso8601_parseable(self) -> None:
        inputs = _make_inputs()
        point = layer1.compute_point_estimate(inputs)
        sens = layer1.compute_sensitivity_table(inputs)
        payload = layer1.emit_json_payload(inputs, point, sens)
        # Should not raise.
        parsed = datetime.fromisoformat(payload["computed_at"])
        assert parsed.tzinfo is not None  # UTC-stamped

    def test_sensitivity_table_is_list_of_twentyseven_dicts(self) -> None:
        inputs = _make_inputs()
        point = layer1.compute_point_estimate(inputs)
        sens = layer1.compute_sensitivity_table(inputs)
        payload = layer1.emit_json_payload(inputs, point, sens)
        table = payload["sensitivity_table"]
        assert isinstance(table, list)
        assert len(table) == 27
        for row in table:
            for k in (
                "ctr", "ctr_label", "cr", "cr_label",
                "coverage", "coverage_label",
                "gross_expected_conversions",
                "attributable_expected_conversions",
                "wilson_ci_95", "gross_wilson_ci_95",
            ):
                assert k in row

    def test_point_estimate_keys(self) -> None:
        inputs = _make_inputs()
        point = layer1.compute_point_estimate(inputs)
        sens = layer1.compute_sensitivity_table(inputs)
        payload = layer1.emit_json_payload(inputs, point, sens)
        pe = payload["point_estimate"]
        for k in (
            "expected_clicks",
            "gross_expected_conversions",
            "attributable_expected_conversions",
            "wilson_ci_95",
            "wilson_ci_lo_count",
            "wilson_ci_hi_count",
            "gross_wilson_ci_95",
        ):
            assert k in pe
        assert isinstance(pe["wilson_ci_95"], list) and len(pe["wilson_ci_95"]) == 2
        assert (
            isinstance(pe["gross_wilson_ci_95"], list)
            and len(pe["gross_wilson_ci_95"]) == 2
        )

    def test_interpretation_hooks_point_at_attributable(self) -> None:
        """G.2.1.attr semantic: layer_2_power_input is the
        ATTRIBUTABLE count (not the gross). At coverage<1.0 these
        differ; the test below pins both."""
        inputs = _make_inputs(coverage=0.85, coverage_low=0.65, coverage_high=0.95)
        point = layer1.compute_point_estimate(inputs)
        sens = layer1.compute_sensitivity_table(inputs)
        payload = layer1.emit_json_payload(inputs, point, sens)
        hooks = payload["interpretation_hooks"]
        assert hooks["layer_2_power_input"] == point.attributable_expected_conversions
        assert hooks["layer_2_power_input"] != point.gross_expected_conversions
        assert hooks["layer_3_cell_input"] is None


# ---------------------------------------------------------------------------
# CLI smoke
# ---------------------------------------------------------------------------

class TestCLISmoke:
    def test_cli_runs_with_placeholder_defaults(self, tmp_path) -> None:
        """End-to-end: subprocess invocation with placeholder-default args
        produces parseable JSON with non-zero attributable + gross
        conversions; sensitivity table is 27 cells; attributable < gross
        because the placeholder coverage default (0.85) < 1.0."""
        out = tmp_path / "layer1_smoke.json"
        result = subprocess.run(
            [sys.executable, str(_TOOL_PATH), "--output", str(out)],
            capture_output=True, text=True, check=False,
        )
        assert result.returncode == 0, (
            f"stderr: {result.stderr}\nstdout: {result.stdout}"
        )
        payload = json.loads(out.read_text())
        pe = payload["point_estimate"]
        assert pe["attributable_expected_conversions"] > 0
        assert pe["gross_expected_conversions"] > 0
        assert (
            pe["attributable_expected_conversions"]
            < pe["gross_expected_conversions"]
        )  # coverage 0.85 < 1.0
        assert len(payload["sensitivity_table"]) == 27

    def test_cli_explicit_args_override_defaults_at_full_coverage(
        self, tmp_path,
    ) -> None:
        """Pin the prior P.1.L1 known-answer at coverage=1.0 (trivial-
        attribution case). 1M × 0.001 × 0.1 × 1.0 = 100 attributable."""
        out = tmp_path / "layer1_explicit.json"
        result = subprocess.run(
            [
                sys.executable, str(_TOOL_PATH),
                "--impression-pool", "1000000",
                "--flight-length-days", "30",
                "--ctr", "0.001",
                "--ctr-low", "0.0005",
                "--ctr-high", "0.002",
                "--cr", "0.1",
                "--cr-low", "0.05",
                "--cr-high", "0.15",
                "--attribution-coverage", "1.0",
                "--attribution-coverage-low", "1.0",
                "--attribution-coverage-high", "1.0",
                "--output", str(out),
            ],
            capture_output=True, text=True, check=False,
        )
        assert result.returncode == 0, result.stderr
        payload = json.loads(out.read_text())
        # 1M × 0.001 × 0.1 × 1.0 = 100 attributable; 1M × 0.001 × 0.1
        # = 100 gross. Equal at coverage=1.0.
        assert payload["point_estimate"][
            "attributable_expected_conversions"
        ] == pytest.approx(100.0, rel=1e-12)
        assert payload["point_estimate"][
            "gross_expected_conversions"
        ] == pytest.approx(100.0, rel=1e-12)

    def test_cli_explicit_attribution_flags(self, tmp_path) -> None:
        """1M × 0.001 × 0.1 × 0.85 = 85 attributable; 100 gross."""
        out = tmp_path / "layer1_attr.json"
        result = subprocess.run(
            [
                sys.executable, str(_TOOL_PATH),
                "--impression-pool", "1000000",
                "--ctr", "0.001",
                "--ctr-low", "0.0005",
                "--ctr-high", "0.002",
                "--cr", "0.1",
                "--cr-low", "0.05",
                "--cr-high", "0.15",
                "--attribution-coverage", "0.85",
                "--attribution-coverage-low", "0.65",
                "--attribution-coverage-high", "0.95",
                "--output", str(out),
            ],
            capture_output=True, text=True, check=False,
        )
        assert result.returncode == 0, result.stderr
        payload = json.loads(out.read_text())
        assert payload["point_estimate"][
            "attributable_expected_conversions"
        ] == pytest.approx(85.0, rel=1e-12)
        assert payload["point_estimate"][
            "gross_expected_conversions"
        ] == pytest.approx(100.0, rel=1e-12)


# ---------------------------------------------------------------------------
# G.2.1.attr — attribution-coverage dimension (NEW)
# ---------------------------------------------------------------------------

class TestAttributionParameters:
    def test_basic_construction(self) -> None:
        attr = layer1.AttributionParameters(
            coverage=0.85, coverage_low=0.65, coverage_high=0.95,
        )
        assert attr.coverage == 0.85

    def test_full_coverage_accepted(self) -> None:
        # le=1 allows 1.0 — the trivial case for backward compat.
        attr = layer1.AttributionParameters(
            coverage=1.0, coverage_low=1.0, coverage_high=1.0,
        )
        assert attr.coverage == 1.0

    def test_coverage_above_one_rejected(self) -> None:
        with pytest.raises(ValidationError):
            layer1.AttributionParameters(
                coverage=1.5, coverage_low=0.65, coverage_high=1.5,
            )

    def test_coverage_zero_rejected(self) -> None:
        # Field gt=0 — strict.
        with pytest.raises(ValidationError):
            layer1.AttributionParameters(
                coverage=0.0, coverage_low=0.0, coverage_high=0.5,
            )

    def test_coverage_low_above_coverage_rejected(self) -> None:
        with pytest.raises(ValidationError):
            layer1.AttributionParameters(
                coverage=0.6, coverage_low=0.7, coverage_high=0.95,
            )

    def test_coverage_high_below_coverage_rejected(self) -> None:
        with pytest.raises(ValidationError):
            layer1.AttributionParameters(
                coverage=0.85, coverage_low=0.65, coverage_high=0.7,
            )


class TestAttributableConversionMath:
    def test_known_answer_attributable(self) -> None:
        """1_000_000 × 0.001 CTR × 0.1 CR × 0.85 coverage = 85.0
        attributable conversions exactly."""
        inputs = _make_inputs(
            impression_pool=1_000_000, ctr=0.001, cr=0.1,
            coverage=0.85, coverage_low=0.65, coverage_high=0.95,
        )
        point = layer1.compute_point_estimate(inputs)
        assert point.attributable_expected_conversions == pytest.approx(
            85.0, rel=1e-12,
        )
        assert point.gross_expected_conversions == pytest.approx(
            100.0, rel=1e-12,
        )

    def test_full_coverage_attributable_equals_gross(self) -> None:
        """At coverage=1.0, attributable count == gross count exactly —
        preserves prior P.1.L1 numerical behavior."""
        inputs = _make_inputs(impression_pool=1_000_000, ctr=0.001, cr=0.1)
        # default coverage triple in helper is (1.0, 1.0, 1.0)
        point = layer1.compute_point_estimate(inputs)
        assert point.attributable_expected_conversions == pytest.approx(
            point.gross_expected_conversions, rel=1e-12,
        )

    @pytest.mark.parametrize(
        "n,count_attributable",
        [
            (10_000, 75),
            (100_000, 250),
            (1_000_000, 850),
            (50_000_000, 3_750),
        ],
    )
    def test_attributable_wilson_matches_statsmodels(
        self, n: int, count_attributable: int,
    ) -> None:
        """Wilson CI on attributable proportion matches statsmodels at
        realistic (n, p_attributable) points within 1e-9."""
        p_attr = count_attributable / n
        sm_lo, sm_hi = proportion_confint(
            count=count_attributable, nobs=n, alpha=0.05, method="wilson",
        )
        my_lo, my_hi = layer1.wilson_score_interval(
            n=n, p_hat=p_attr, alpha=0.05,
        )
        assert my_lo == pytest.approx(sm_lo, abs=1e-9)
        assert my_hi == pytest.approx(sm_hi, abs=1e-9)


class TestSensitivityCoverageDimension:
    def test_monotonicity_in_coverage_at_fixed_ctr_cr(self) -> None:
        """Hold (CTR, CR) fixed at mid; sweep coverage low → mid → high;
        attributable_expected_conversions strictly increasing."""
        inputs = _make_inputs(
            coverage=0.85, coverage_low=0.65, coverage_high=0.95,
        )
        sens = layer1.compute_sensitivity_table(inputs)
        row = sorted(
            (
                c for c in sens
                if c.ctr_label == "mid" and c.cr_label == "mid"
            ),
            key=lambda c: c.coverage,
        )
        assert len(row) == 3
        for prior, current in zip(row, row[1:]):
            assert (
                current.attributable_expected_conversions
                > prior.attributable_expected_conversions
            )

    def test_gross_unchanged_across_coverage(self) -> None:
        """Gross conversions don't depend on attribution coverage.
        Hold (CTR, CR) fixed; gross_expected_conversions is identical
        across the three coverage cells."""
        inputs = _make_inputs(
            coverage=0.85, coverage_low=0.65, coverage_high=0.95,
        )
        sens = layer1.compute_sensitivity_table(inputs)
        for ctr_lbl in ("low", "mid", "high"):
            for cr_lbl in ("low", "mid", "high"):
                cells = [
                    c for c in sens
                    if c.ctr_label == ctr_lbl and c.cr_label == cr_lbl
                ]
                gross_values = {c.gross_expected_conversions for c in cells}
                assert len(gross_values) == 1, (
                    f"gross_expected_conversions varies across coverage at "
                    f"(ctr={ctr_lbl}, cr={cr_lbl}): {gross_values}"
                )

    def test_attributable_equals_gross_times_coverage(self) -> None:
        """Identity: attributable_expected_conversions == n * CTR * CR
        * coverage == gross_expected_conversions * coverage."""
        inputs = _make_inputs(
            coverage=0.85, coverage_low=0.65, coverage_high=0.95,
        )
        sens = layer1.compute_sensitivity_table(inputs)
        for cell in sens:
            expected_attr = cell.gross_expected_conversions * cell.coverage
            assert cell.attributable_expected_conversions == pytest.approx(
                expected_attr, rel=1e-12,
            )
