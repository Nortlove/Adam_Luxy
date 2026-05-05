"""G.3 — pharmacovigilance schema + disproportionality metrics tests.

Per directive §G.3: schema is fixed pre-pilot; tests pin
serialization round-trip + closed-form metric correctness on
canonical 2x2 tables. EBGM full-MGPS shrinkage iteration lands in
a later slice; the naive single-cell EBGM is tested here for
schema-level correctness.
"""
from __future__ import annotations

import math

import pytest

from adam.pharmacovigilance import (
    DisproportionalityMetrics,
    PharmacovigilanceCell,
    SignalThresholds,
    TreeScanResult,
    compute_ebgm_naive,
    compute_ic,
    compute_ic025,
    compute_prr,
    compute_ror,
    is_signal,
)


# ----------------------------------------------------------------------------
# Round-trip serialization
# ----------------------------------------------------------------------------

class TestRoundTrip:
    def test_disproportionality_metrics_round_trip(self):
        m = DisproportionalityMetrics(
            a=10, b=90, c=100, d=9800,
            prr=10.0, prr_chi2=42.0, ror=10.9,
            ic=2.5, ic025=1.8, ebgm=8.5, eb05=4.2,
        )
        d = m.to_dict()
        m2 = DisproportionalityMetrics.from_dict(d)
        assert m2 == m

    def test_pharmacovigilance_cell_round_trip(self):
        m = DisproportionalityMetrics(a=5, b=20, c=10, d=100)
        cell = PharmacovigilanceCell(
            creative_id="cr_8847221",
            cohort_id="cohort_status_seeker",
            posture="LEISURE_BROWSING",
            cell_id="cell_42",
            metrics=m,
            last_updated="2026-05-04T12:00:00Z",
            signal=False,
            notes="initial population",
        )
        d = cell.to_dict()
        cell2 = PharmacovigilanceCell.from_dict(d)
        assert cell2 == cell

    def test_pharmacovigilance_cell_minimal_round_trip(self):
        m = DisproportionalityMetrics(a=0, b=0, c=0, d=0)
        cell = PharmacovigilanceCell(
            creative_id="cr_x", cohort_id="cohort_y",
            posture="INFORMATION_FORAGING", cell_id="z", metrics=m,
        )
        d = cell.to_dict()
        cell2 = PharmacovigilanceCell.from_dict(d)
        assert cell2.creative_id == "cr_x"
        assert cell2.signal is False
        assert cell2.notes is None

    def test_tree_scan_result_dataclass(self):
        r = TreeScanResult(
            most_likely_cluster_path="creative_8847221.cohort_status_seeker.LEISURE_BROWSING",
            log_likelihood_ratio=12.4, relative_risk=2.8,
            cluster_observed=42, cluster_expected=15.0,
            pvalue=0.003, n_permutations=999,
        )
        assert r.most_likely_cluster_path.startswith("creative_")
        assert 0 <= r.pvalue <= 1


# ----------------------------------------------------------------------------
# PRR
# ----------------------------------------------------------------------------

class TestPRR:
    def test_prr_textbook_2x2(self):
        # Textbook example: target 10/100 events; baseline 100/10000 events.
        # PRR = (10/100) / (100/10000) = 0.10 / 0.01 = 10.0
        prr, chi2 = compute_prr(10, 90, 100, 9900)
        assert prr == pytest.approx(10.0, rel=1e-9)
        # Chi-squared > 4 (signal threshold)
        assert chi2 > 4.0

    def test_prr_no_disproportionality_returns_one(self):
        # Equal rates → PRR = 1.0
        prr, _ = compute_prr(10, 90, 100, 900)
        assert prr == pytest.approx(1.0, rel=1e-9)

    def test_prr_zero_target_arm_safe(self):
        prr, chi2 = compute_prr(0, 0, 100, 9900)
        assert prr == 0.0
        assert chi2 == 0.0

    def test_prr_zero_baseline_safe(self):
        prr, chi2 = compute_prr(10, 90, 0, 9900)
        assert prr == 0.0
        assert chi2 == 0.0


# ----------------------------------------------------------------------------
# ROR
# ----------------------------------------------------------------------------

class TestROR:
    def test_ror_textbook_2x2(self):
        # ROR = (a*d) / (b*c) = (10*9900) / (90*100) = 99000/9000 = 11.0
        ror = compute_ror(10, 90, 100, 9900)
        assert ror == pytest.approx(11.0, rel=1e-9)

    def test_ror_inverse_under_row_swap(self):
        # Swapping rows in a 2x2 inverts the odds ratio.
        ror_normal = compute_ror(10, 90, 100, 9900)
        ror_swapped_rows = compute_ror(100, 9900, 10, 90)
        assert ror_normal * ror_swapped_rows == pytest.approx(1.0, rel=1e-9)

    def test_ror_zero_safe(self):
        assert compute_ror(0, 0, 0, 0) == 0.0
        assert compute_ror(10, 0, 100, 9900) == 0.0  # b=0


# ----------------------------------------------------------------------------
# IC + IC025
# ----------------------------------------------------------------------------

class TestIC:
    def test_ic_above_zero_for_disproportionate_cell(self):
        # Disproportionate: target = 10 events out of 100; baseline = 100/10000.
        # IC should be positive (signal direction).
        ic = compute_ic(10, 90, 100, 9900)
        assert ic > 0

    def test_ic_zero_for_proportional_cell(self):
        # Proportional rates → IC ≈ 0.
        # target = 10/100, baseline = 1000/10000 (both 10%) → no
        # disproportionality.
        ic = compute_ic(10, 90, 1000, 9000)
        assert abs(ic) < 0.5

    def test_ic_safe_on_empty(self):
        assert compute_ic(0, 0, 0, 0) == 0.0


class TestIC025:
    def test_ic025_below_ic(self):
        # IC025 is the lower 2.5th-percentile bound — must be < IC point.
        a, b, c, d = 10, 90, 100, 9900
        ic = compute_ic(a, b, c, d)
        ic025 = compute_ic025(a, b, c, d)
        assert ic025 < ic

    def test_ic025_low_count_pulled_more_negative(self):
        """Wilson-style variance penalty: lower count → larger gap
        between IC and IC025."""
        gap_low = compute_ic(2, 100, 1000, 100000) - compute_ic025(2, 100, 1000, 100000)
        gap_high = compute_ic(50, 100, 1000, 100000) - compute_ic025(50, 100, 1000, 100000)
        assert gap_low > gap_high


# ----------------------------------------------------------------------------
# EBGM (naive)
# ----------------------------------------------------------------------------

class TestEBGMNaive:
    def test_ebgm_above_one_for_disproportionate(self):
        ebgm = compute_ebgm_naive(10, 90, 100, 9900)
        assert ebgm > 1.0

    def test_ebgm_below_one_for_under_reported(self):
        # Target much less than expected.
        ebgm = compute_ebgm_naive(1, 99, 1000, 9000)
        assert ebgm < 1.0

    def test_ebgm_zero_safe(self):
        assert compute_ebgm_naive(0, 0, 0, 0) == 0.0

    def test_ebgm_prior_shrinks_toward_one_at_low_counts(self):
        # With the default Gamma(0.5, 0.5) prior and very low counts,
        # EBGM should shrink TOWARD the prior mean (≈1) compared to
        # the unshrunken raw rate.
        ebgm_low = compute_ebgm_naive(2, 8, 100, 9900)
        # Raw rate ratio at this cell: (2/10) / (100/10000) = 20.
        # Prior should pull EBGM well below 20.
        assert ebgm_low < 20.0


# ----------------------------------------------------------------------------
# is_signal — threshold logic
# ----------------------------------------------------------------------------

class TestIsSignal:
    def test_no_signal_when_all_metrics_below_threshold(self):
        m = DisproportionalityMetrics(
            a=1, b=99, c=100, d=9900,
            prr=1.0, prr_chi2=0.5, ror=1.0,
            ic=0.0, ic025=-0.5, ebgm=1.0, eb05=0.5,
        )
        assert is_signal(m) is False

    def test_signal_any_mode_fires_on_eb05(self):
        m = DisproportionalityMetrics(
            a=10, b=90, c=100, d=9900,
            prr=1.0, prr_chi2=0.0, ror=1.0,
            ic=0.0, ic025=-1.0, ebgm=10.0, eb05=2.5,
        )
        assert is_signal(m, mode="any") is True

    def test_signal_any_mode_fires_on_ic025(self):
        m = DisproportionalityMetrics(
            a=10, b=90, c=100, d=9900,
            prr=1.0, prr_chi2=0.0, ror=1.0,
            ic=2.0, ic025=1.5, ebgm=1.0, eb05=1.0,
        )
        assert is_signal(m, mode="any") is True

    def test_signal_consensus_mode_requires_two(self):
        m_one = DisproportionalityMetrics(
            a=5, b=95, c=100, d=9900,
            prr=1.0, prr_chi2=0.0, ror=1.0,
            ic=0.0, ic025=-1.0, ebgm=10.0, eb05=2.5,  # only EB05
        )
        assert is_signal(m_one, mode="consensus") is False
        m_two = DisproportionalityMetrics(
            a=10, b=90, c=100, d=9900,
            prr=1.0, prr_chi2=0.0, ror=1.0,
            ic=2.0, ic025=1.5, ebgm=10.0, eb05=2.5,  # IC025 + EB05
        )
        assert is_signal(m_two, mode="consensus") is True

    def test_signal_prr_requires_chi2_too(self):
        # PRR > 2 alone insufficient — needs chi2 > 4 too.
        m = DisproportionalityMetrics(
            a=5, b=10, c=10, d=100,
            prr=3.5, prr_chi2=2.0, ror=1.0,
            ic=0.0, ic025=-0.5, ebgm=1.0, eb05=1.0,
        )
        assert is_signal(m) is False
        m2 = DisproportionalityMetrics(
            a=5, b=10, c=10, d=100,
            prr=3.5, prr_chi2=10.0, ror=1.0,
            ic=0.0, ic025=-0.5, ebgm=1.0, eb05=1.0,
        )
        assert is_signal(m2) is True


# ----------------------------------------------------------------------------
# Custom thresholds
# ----------------------------------------------------------------------------

class TestThresholds:
    def test_default_thresholds(self):
        t = SignalThresholds()
        assert t.eb05_threshold == 2.0
        assert t.ic025_threshold == 0.0
        assert t.prr_threshold == 2.0
        assert t.prr_chi2_threshold == 4.0
        assert t.ror_threshold == 2.0

    def test_custom_threshold_strictness(self):
        # With stricter thresholds, a borderline cell flips from signal to no-signal.
        m = DisproportionalityMetrics(
            a=5, b=95, c=100, d=9900,
            prr=1.0, prr_chi2=0.0, ror=1.0,
            ic=0.5, ic025=0.1, ebgm=1.5, eb05=1.5,
        )
        # Default — IC025=0.1 > 0 → signal.
        assert is_signal(m) is True
        # Stricter IC025 threshold of 0.5 — no signal.
        strict = SignalThresholds(ic025_threshold=0.5)
        assert is_signal(m, thresholds=strict) is False


# ----------------------------------------------------------------------------
# Schema-grain pin: (creative × cohort × posture × cell)
# ----------------------------------------------------------------------------

class TestSignalLocalizationGrain:
    """Pin the directive §G.3 grain: per (creative × cohort × posture × cell)."""

    def test_cell_carries_all_four_grain_dimensions(self):
        m = DisproportionalityMetrics(a=1, b=1, c=1, d=1)
        cell = PharmacovigilanceCell(
            creative_id="A", cohort_id="B", posture="TASK_COMPLETION",
            cell_id="C", metrics=m,
        )
        # All four are required keyword args by the dataclass; the test
        # is a structural pin against accidental schema changes that
        # collapse the grain.
        assert cell.creative_id == "A"
        assert cell.cohort_id == "B"
        assert cell.posture == "TASK_COMPLETION"
        assert cell.cell_id == "C"
