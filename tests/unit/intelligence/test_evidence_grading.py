"""Pin E4 — GRADE + E-values + fragility analysis.

Discipline anchors:
    - All three formulas are CANONICAL (Cochrane handbook, VanderWeele
      & Ding 2017, Walsh 2014). Tests pin canonical numerical anchors
      so a future refactor can't silently change the math.
    - Each tool soft-fails independently. build_evidence_package skips
      a component when its inputs are missing rather than raising.
    - The discipline rule for ADAM: MRT (M1) starts HIGH (randomized);
      OPE on logged data starts LOW (observational). Pin both.
"""

from __future__ import annotations

import pytest

from adam.intelligence.evidence_grading import (
    EValueResult,
    EvidenceGrade,
    EvidencePackage,
    FragilityResult,
    GRADEDowngrades,
    GRADEResult,
    StudyDesign,
    build_evidence_package,
    compute_e_value,
    e_value_for_or_with_baseline,
    e_value_for_risk_ratio,
    fragility_index,
    grade_evidence,
)


# =============================================================================
# 1. GRADE
# =============================================================================


def test_grade_randomized_no_downgrades_is_high():
    """ADAM's MRT (M1): randomized excursion trial → HIGH starting grade,
    no downgrades → HIGH final grade."""
    result = grade_evidence(StudyDesign.RANDOMIZED)
    assert result.grade == EvidenceGrade.HIGH
    assert result.starting_grade == EvidenceGrade.HIGH


def test_grade_observational_no_downgrades_is_low():
    """OPE on logged data is observational → LOW starting grade per
    Cochrane handbook §5.1."""
    result = grade_evidence(StudyDesign.OBSERVATIONAL)
    assert result.grade == EvidenceGrade.LOW


def test_grade_one_downgrade_drops_one_level():
    """Each non-severe downgrade dimension → -1 grade level."""
    downgrades = GRADEDowngrades(imprecision=True)
    result = grade_evidence(StudyDesign.RANDOMIZED, downgrades=downgrades)
    assert result.grade == EvidenceGrade.MODERATE
    assert "imprecision" in result.triggered[0]


def test_grade_severe_downgrade_drops_two_levels():
    """Severe imprecision → -2 grade levels."""
    downgrades = GRADEDowngrades(severe_imprecision=True)
    result = grade_evidence(StudyDesign.RANDOMIZED, downgrades=downgrades)
    assert result.grade == EvidenceGrade.LOW


def test_grade_multiple_downgrades_compound():
    """Two -1 dimensions → -2 from start."""
    downgrades = GRADEDowngrades(
        imprecision=True, indirectness=True,
    )
    result = grade_evidence(StudyDesign.RANDOMIZED, downgrades=downgrades)
    assert result.grade == EvidenceGrade.LOW
    assert result.downgrade_count == 2


def test_grade_bottoms_at_very_low():
    """Even with extreme downgrades, can't go below VERY_LOW."""
    downgrades = GRADEDowngrades(
        severe_risk_of_bias=True,
        severe_inconsistency=True,
        severe_indirectness=True,
        severe_imprecision=True,
        severe_publication_bias=True,
    )
    result = grade_evidence(StudyDesign.RANDOMIZED, downgrades=downgrades)
    assert result.grade == EvidenceGrade.VERY_LOW


def test_grade_caps_at_high():
    """Even with multiple upgrades on observational, can't exceed HIGH."""
    downgrades = GRADEDowngrades(
        very_large_effect=True, dose_response=True,
        plausible_confounding_attenuates=True,
    )
    result = grade_evidence(StudyDesign.OBSERVATIONAL, downgrades=downgrades)
    assert result.grade == EvidenceGrade.HIGH


def test_grade_upgrades_only_apply_to_observational():
    """Cochrane handbook §14.5: upgrades are not valid for RCTs."""
    downgrades = GRADEDowngrades(very_large_effect=True)
    result = grade_evidence(StudyDesign.RANDOMIZED, downgrades=downgrades)
    # Randomized + no real downgrades: still HIGH. Upgrades silently
    # ignored per handbook (no-op rather than error).
    assert result.grade == EvidenceGrade.HIGH
    # The upgrade_count should be 0 because we didn't apply it
    assert result.upgrade_count == 0


# =============================================================================
# 2. E-values
# =============================================================================


def test_e_value_no_effect_is_one():
    """RR=1 means no effect → no confounding needed → E-value = 1."""
    assert e_value_for_risk_ratio(1.0) == pytest.approx(1.0)


def test_e_value_for_rr_2_is_canonical():
    """Canonical anchor: RR=2 → E ≈ 3.41 (VanderWeele-Ding 2017
    Table 1 example). Pin to detect formula drift."""
    e = e_value_for_risk_ratio(2.0)
    assert e == pytest.approx(3.4142, abs=0.001)


def test_e_value_for_matz_corrected_or_is_about_two():
    """Matz 2017 corrected: OR=1.30 (per PERSONALITY_MATCHING_EFFECT
    in effect_size_correction.py). Convert to RR ≈ 1.30 (rare-outcome
    approximation), E-value ≈ 1.92."""
    e = e_value_for_risk_ratio(1.30)
    assert 1.85 < e < 2.0


def test_e_value_inverse_for_rr_below_one():
    """For RR < 1, the formula flips the ratio and applies the same
    formula. RR=0.5 → flip to 2.0 → E ≈ 3.41. Symmetry around RR=1."""
    e_above = e_value_for_risk_ratio(2.0)
    e_below = e_value_for_risk_ratio(0.5)
    assert e_above == pytest.approx(e_below)


def test_e_value_negative_rr_returns_one():
    """Degenerate input: RR ≤ 0 doesn't make sense; return 1 (no effect)."""
    assert e_value_for_risk_ratio(-1.0) == 1.0
    assert e_value_for_risk_ratio(0.0) == 1.0


def test_e_value_or_to_rr_conversion():
    """OR=1.30 with baseline=0.05 (rare outcome): RR ≈ 1.285,
    E ≈ 1.90 (close to RR-direct E since outcome is rare).
    OR=1.30 with baseline=0.50 (common outcome): RR ≈ 1.13,
    E ≈ 1.51 — substantially different."""
    rare = e_value_for_or_with_baseline(1.30, baseline_risk=0.05)
    common = e_value_for_or_with_baseline(1.30, baseline_risk=0.50)
    # Same OR, lower E for common outcomes — the conversion bites
    assert rare > common


def test_e_value_or_baseline_validation():
    with pytest.raises(ValueError):
        e_value_for_or_with_baseline(1.5, baseline_risk=0.0)
    with pytest.raises(ValueError):
        e_value_for_or_with_baseline(1.5, baseline_risk=1.0)


def test_compute_e_value_returns_pair():
    """compute_e_value returns BOTH point and CI E-values per
    VanderWeele-Ding 2017 §3 reporting convention."""
    result = compute_e_value(rr_point=2.0, rr_ci_lower=1.5)
    assert result.e_value_point == pytest.approx(3.414, abs=0.001)
    # E for RR=1.5: 1.5 + sqrt(1.5*0.5) ≈ 2.366
    assert result.e_value_ci_lower == pytest.approx(2.366, abs=0.001)
    assert "Unmeasured confounding" in result.interpretation


# =============================================================================
# 3. Fragility index
# =============================================================================


def test_fragility_initially_significant_returns_positive_index():
    """A clearly-significant 2x2 has a positive fragility index."""
    # 80/100 vs 20/100 conversion — overwhelming difference
    result = fragility_index(
        treatment_successes=80, treatment_total=100,
        control_successes=20, control_total=100,
    )
    assert result.initial_significant is True
    assert result.fragility_index > 0
    # 80% vs 20% should require many flips to lose significance
    assert result.fragility_index >= 10


def test_fragility_initially_NON_significant_returns_zero():
    """Walsh 2014: fragility is undefined for non-significant results.
    Returns FI=0 with initial_significant=False."""
    result = fragility_index(
        treatment_successes=10, treatment_total=100,
        control_successes=9, control_total=100,
    )
    assert result.initial_significant is False
    assert result.fragility_index == 0


def test_fragility_quotient_is_index_over_total():
    result = fragility_index(
        treatment_successes=80, treatment_total=100,
        control_successes=20, control_total=100,
    )
    assert result.fragility_quotient == pytest.approx(
        result.fragility_index / 200.0,
    )


def test_fragility_flip_direction_treatment_failure_when_treatment_higher():
    """When treatment_rate > control_rate, flipping treatment_success
    → failure narrows the gap toward null."""
    result = fragility_index(
        treatment_successes=70, treatment_total=100,
        control_successes=30, control_total=100,
    )
    assert result.flip_direction == "to_treatment_failure"


def test_fragility_flip_direction_control_success_when_control_higher():
    """When control_rate > treatment_rate (treatment HARMS), flipping
    control_failure → success narrows the gap."""
    result = fragility_index(
        treatment_successes=30, treatment_total=100,
        control_successes=70, control_total=100,
    )
    assert result.flip_direction == "to_control_success"


def test_fragility_validates_inputs():
    with pytest.raises(ValueError):
        fragility_index(
            treatment_successes=150, treatment_total=100,
            control_successes=50, control_total=100,
        )
    with pytest.raises(ValueError):
        fragility_index(
            treatment_successes=50, treatment_total=0,
            control_successes=50, control_total=100,
        )


def test_fragility_small_sample_high_fragility():
    """Walsh 2014 motivation: small-sample 'significant' results are
    fragile. 5/10 vs 0/10 is significant (Fisher exact) but only ONE
    flip from non-significant — exactly what Walsh warned against."""
    result = fragility_index(
        treatment_successes=5, treatment_total=10,
        control_successes=0, control_total=10,
    )
    if result.initial_significant:
        # Should be very fragile — 1-3 flips at most
        assert result.fragility_index <= 3


# =============================================================================
# Composed package
# =============================================================================


def test_evidence_package_composes_all_three():
    """Full package with all inputs available."""
    package = build_evidence_package(
        design=StudyDesign.RANDOMIZED,
        rr_point=2.0,
        rr_ci_lower=1.5,
        fragility_table=(80, 100, 20, 100),
        downgrades=GRADEDowngrades(imprecision=True),
    )
    assert package.grade.grade == EvidenceGrade.MODERATE
    assert package.e_value is not None
    assert package.fragility is not None
    assert package.fragility.initial_significant is True
    # Summary should mention all three
    assert "GRADE" in package.summary
    assert "E-value" in package.summary
    assert "FI" in package.summary


def test_evidence_package_skips_e_value_when_rr_missing():
    """Soft-fail: missing inputs skip components, don't raise."""
    package = build_evidence_package(
        design=StudyDesign.OBSERVATIONAL,
        rr_point=None, rr_ci_lower=None,
        fragility_table=(50, 100, 30, 100),
    )
    assert package.grade is not None
    assert package.e_value is None
    assert package.fragility is not None


def test_evidence_package_skips_fragility_when_table_missing():
    package = build_evidence_package(
        design=StudyDesign.RANDOMIZED,
        rr_point=2.0, rr_ci_lower=1.5,
        fragility_table=None,
    )
    assert package.fragility is None
    assert package.e_value is not None


def test_evidence_package_minimal_just_grade():
    """Even with only design specified, get a grade. Other components
    silently skipped."""
    package = build_evidence_package(design=StudyDesign.RANDOMIZED)
    assert package.grade.grade == EvidenceGrade.HIGH
    assert package.e_value is None
    assert package.fragility is None


def test_evidence_package_skips_fragility_on_invalid_table():
    """build_evidence_package soft-fails fragility on ValueError —
    invalid table doesn't crash the whole package."""
    package = build_evidence_package(
        design=StudyDesign.RANDOMIZED,
        fragility_table=(150, 100, 50, 100),  # invalid: t_succ > t_total
    )
    # Other components still work; fragility quietly skipped
    assert package.grade is not None
    assert package.fragility is None


# =============================================================================
# Discipline: starting-grade rule pinned for ADAM-specific designs
# =============================================================================


def test_adam_mrt_starts_high():
    """Pin the discipline rule: M1 MRT (per-impression randomized
    excursion trial) starts at HIGH per Cochrane §5.1. A future
    refactor that classified MRT as observational would silently
    downgrade every ADAM evidence claim."""
    result = grade_evidence(StudyDesign.RANDOMIZED)
    assert result.starting_grade == EvidenceGrade.HIGH


def test_adam_ope_starts_low():
    """OPE on logged data is observational → LOW. Pre-pilot when MRT
    isn't yet running, this is the floor we operate from."""
    result = grade_evidence(StudyDesign.OBSERVATIONAL)
    assert result.starting_grade == EvidenceGrade.LOW
