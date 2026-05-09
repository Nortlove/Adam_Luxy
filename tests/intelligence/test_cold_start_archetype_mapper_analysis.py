"""P.1 — ANALYSIS-C: cold_start_archetype_mapper synthetic
distribution sanity check tests.

Pin: synthetic-grid evaluator correctness, criteria-evaluation
logic, all 5 healthy-distribution criteria as architectural
invariants (current mapper passes all 5 — pinning catches
regressions if future tuning breaks any criterion), determinism,
report generation idempotence, zero-regression on the mapper
itself.

Per P.0 §9 + P.1 spec: this analysis runs purely from W.2a's
tunable constants; zero external data dependencies.
"""
import os
from pathlib import Path

import pytest

from adam.cold_start.models.enums import ArchetypeID
from adam.intelligence.cold_start_archetype_mapper_analysis import (
    CRITERION_1_MAX_DOMINANCE_THRESHOLD,
    CRITERION_2_MIN_REPRESENTATION_THRESHOLD,
    CRITERION_3_MIN_CHANGE_RATE,
    CRITERION_4_MAX_DEFAULT_RATE,
    CRITERION_5_DETERMINISM_CALL_COUNT,
    DEVICE_GRID,
    GEO_GRID,
    HOUR_GRID,
    IAB_GRID,
    evaluate_grid,
    write_analysis_report,
)


# ---------------------------------------------------------------------------
# Grid evaluator structural correctness
# ---------------------------------------------------------------------------

class TestGridEvaluatorStructure:

    def test_evaluate_grid_returns_expected_keys(self):
        results = evaluate_grid()
        expected_keys = {
            "total_combinations",
            "archetype_distribution",
            "default_fallback_count",
            "default_fallback_rate",
            "per_axis_effect",
            "criteria_evaluation",
            "grid_results",
        }
        assert expected_keys.issubset(set(results.keys()))

    def test_total_combinations_equals_cartesian_product(self):
        expected = (
            len(GEO_GRID)
            * len(DEVICE_GRID)
            * len(HOUR_GRID)
            * len(IAB_GRID)
        )
        results = evaluate_grid()
        assert results["total_combinations"] == expected

    def test_archetype_distribution_sums_to_total(self):
        results = evaluate_grid()
        assert sum(results["archetype_distribution"].values()) == (
            results["total_combinations"]
        )

    def test_grid_results_length_matches_total(self):
        results = evaluate_grid()
        assert len(results["grid_results"]) == results["total_combinations"]

    def test_per_axis_effect_covers_all_4_axes(self):
        results = evaluate_grid()
        assert set(results["per_axis_effect"].keys()) == {
            "geo", "device", "hour", "iab",
        }

    def test_per_axis_effect_change_rate_in_unit_range(self):
        results = evaluate_grid()
        for axis_name, effect in results["per_axis_effect"].items():
            assert 0.0 <= effect["change_rate"] <= 1.0


# ---------------------------------------------------------------------------
# Criteria evaluation framework
# ---------------------------------------------------------------------------

class TestCriteriaEvaluationFramework:

    def test_all_5_criteria_present_in_evaluation(self):
        results = evaluate_grid()
        crit = results["criteria_evaluation"]
        expected_criterion_keys = {
            "criterion_1_no_dominance",
            "criterion_1_max_share",
            "criterion_2_all_8_represented",
            "criterion_2_represented_count",
            "criterion_3_per_axis_effect",
            "criterion_3_min_change_rate",
            "criterion_4_default_rate_bounded",
            "criterion_4_default_rate",
            "criterion_5_deterministic",
        }
        assert expected_criterion_keys.issubset(set(crit.keys()))


# ---------------------------------------------------------------------------
# 5 healthy-distribution criteria pinned as architectural invariants
# ---------------------------------------------------------------------------

class TestHealthyDistributionInvariants:
    """Per P.1 spec: pin all 5 criteria as must-pass invariants
    given current mapper state. If a future change to W.2a's
    mapper or its hint dicts causes any criterion to fail, these
    tests catch it as a regression.

    Current state (2026-05-09): all 5 criteria PASS.
    """

    @pytest.fixture(scope="class")
    def evaluation(self):
        return evaluate_grid()

    def test_criterion_1_no_archetype_dominance(self, evaluation):
        """Max archetype share must be ≤ 40% across the grid."""
        crit = evaluation["criteria_evaluation"]
        assert crit["criterion_1_no_dominance"], (
            f"max archetype share "
            f"{crit['criterion_1_max_share']*100:.1f}% exceeds "
            f"{CRITERION_1_MAX_DOMINANCE_THRESHOLD*100:.0f}% threshold"
        )

    def test_criterion_2_all_8_archetypes_represented(self, evaluation):
        """Each of 8 ArchetypeIDs must appear ≥ 1% of grid combinations."""
        crit = evaluation["criteria_evaluation"]
        assert crit["criterion_2_all_8_represented"], (
            f"only {crit['criterion_2_represented_count']}/8 "
            f"archetypes meet the {CRITERION_2_MIN_REPRESENTATION_THRESHOLD*100:.0f}% "
            f"representation threshold"
        )

    def test_criterion_3_per_axis_effect(self, evaluation):
        """Each axis must change archetype assignment in ≥ 30% of
        pivot groups (axis must matter)."""
        crit = evaluation["criteria_evaluation"]
        assert crit["criterion_3_per_axis_effect"], (
            f"min per-axis change rate "
            f"{crit['criterion_3_min_change_rate']*100:.1f}% below "
            f"{CRITERION_3_MIN_CHANGE_RATE*100:.0f}% threshold"
        )

    def test_criterion_4_default_fallback_rate_bounded(self, evaluation):
        """Default-fallback rate < 20% (signal coverage sufficient)."""
        crit = evaluation["criteria_evaluation"]
        assert crit["criterion_4_default_rate_bounded"], (
            f"default-fallback rate "
            f"{crit['criterion_4_default_rate']*100:.3f}% exceeds "
            f"{CRITERION_4_MAX_DEFAULT_RATE*100:.0f}% threshold"
        )

    def test_criterion_5_determinism(self, evaluation):
        """Same input must produce same output across N calls."""
        crit = evaluation["criteria_evaluation"]
        assert crit["criterion_5_deterministic"], (
            f"map_cold_start_archetype produced divergent outputs "
            f"across {CRITERION_5_DETERMINISM_CALL_COUNT} repeated calls"
        )


# ---------------------------------------------------------------------------
# Report writer
# ---------------------------------------------------------------------------

class TestReportWriter:

    def test_write_analysis_report_creates_file(self, tmp_path):
        output = str(tmp_path / "test_report.md")
        write_analysis_report(output_path=output)
        assert os.path.exists(output)

    def test_write_analysis_report_idempotent(self, tmp_path):
        """Running twice produces the same file content modulo
        the timestamp line. Pin structural idempotence — body
        sections (criteria, distribution) are deterministic given
        deterministic mapper state."""
        output = str(tmp_path / "test_report_a.md")
        write_analysis_report(output_path=output)
        with open(output) as f:
            content_a = f.read()

        write_analysis_report(output_path=output)
        with open(output) as f:
            content_b = f.read()

        # Strip the timestamp line for comparison
        def _strip_timestamp(content):
            return "\n".join(
                line for line in content.split("\n")
                if not line.startswith("## Generated:")
            )
        assert _strip_timestamp(content_a) == _strip_timestamp(content_b)

    def test_report_contains_executive_summary(self, tmp_path):
        output = str(tmp_path / "test_report.md")
        write_analysis_report(output_path=output)
        with open(output) as f:
            content = f.read()
        assert "## §1 Executive Summary" in content
        assert "RESULT:" in content

    def test_report_contains_per_axis_table(self, tmp_path):
        output = str(tmp_path / "test_report.md")
        write_analysis_report(output_path=output)
        with open(output) as f:
            content = f.read()
        assert "## §4 Per-axis effect" in content
        assert "| Axis | Groups with change |" in content


# ---------------------------------------------------------------------------
# Persisted analysis report (the actual P.1 output) sanity
# ---------------------------------------------------------------------------

class TestPersistedReport:

    def test_persisted_report_exists(self):
        """The P.1 analysis report committed at
        docs/analyses/ exists and is readable."""
        path = Path(
            "docs/analyses/"
            "COLD_START_ARCHETYPE_MAPPER_DISTRIBUTION_P1.md"
        )
        assert path.exists()

    def test_persisted_report_pins_all_5_criteria_as_pass(self):
        """The committed P.1 report must show all 5 criteria as
        PASS (current mapper state). If a future mapper tuning
        causes a criterion to fail, regenerating the report and
        committing it must surface the new state — and the
        TestHealthyDistributionInvariants tests above must be
        updated."""
        path = Path(
            "docs/analyses/"
            "COLD_START_ARCHETYPE_MAPPER_DISTRIBUTION_P1.md"
        )
        content = path.read_text()
        assert "**RESULT: All 5 criteria PASS.**" in content


# ---------------------------------------------------------------------------
# Zero-regression on the mapper itself
# ---------------------------------------------------------------------------

class TestZeroRegressionOnMapper:

    def test_mapper_still_resolves(self):
        """W.2a mapper unaffected by P.1's analysis module."""
        from adam.intelligence.cold_start_archetype_mapper import (
            map_cold_start_archetype,
        )
        result = map_cold_start_archetype(
            geo="NYC", device="mobile",
            hour_of_day=12, iab_category="Business and Finance",
        )
        assert isinstance(result, ArchetypeID)

    def test_mapper_constants_unchanged(self):
        from adam.intelligence import cold_start_archetype_mapper as m
        # Spot-check a few constants — full test surface is in
        # tests/intelligence/test_cold_start_archetype_mapper.py
        assert m.COLD_START_DEFAULT_ARCHETYPE == ArchetypeID.PRAGMATIST
        assert "scarcity" not in m.IAB_CATEGORY_ARCHETYPE_HINTS  # sanity
