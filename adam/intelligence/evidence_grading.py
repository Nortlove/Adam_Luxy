"""E4 — GRADE + E-values + fragility analysis for ADAM effect-size claims.

When the OPE / WCLS / causal-forest pipelines produce effect-size
estimates, those estimates need quality grading + sensitivity to
unmeasured confounding + fragility analysis before they can stand
under investor / Becca / regulatory scrutiny. This module provides
the three textbook tools.

Pre-registration substrate already exists at
``adam/intelligence/recommendation_class/pre_registration.py`` — git-
commit-based file convention. This module supplies the post-observation
analysis tools that read pre-registered claims and grade them.

Three components, each canonical:

    1. GRADE (Guyatt et al. 2008-2011, Cochrane handbook):
       Five downgrade dimensions — risk of bias, inconsistency,
       indirectness, imprecision, publication bias — applied to a
       starting grade (HIGH for randomized, LOW for observational).
       The discipline anchor: ADAM's MRT is a randomized excursion
       trial → starts HIGH; OPE on logged data → starts LOW.

    2. E-values (VanderWeele & Ding, Annals of Internal Medicine 2017):
       Minimum strength of unmeasured confounding (on the risk-ratio
       scale) required to fully explain away an observed effect.
       Higher E-value → result is MORE robust to unmeasured confounding.

           E = RR + sqrt(RR * (RR - 1))    for RR >= 1
           E = (1/RR) + sqrt((1/RR) * ((1/RR) - 1))    for RR < 1

       For odds ratios, RR_approx = OR / (1 - p_base + p_base * OR).

    3. Fragility index (Walsh, Srinathan, McAuley et al., J Clin Epi
       2014):
       For binary outcome 2x2 tables, the minimum number of event
       reassignments (success → failure) that flip statistical
       significance. Pilot-relevant: a fragility index of 1 means
       changing one buyer's conversion would flip the conclusion —
       a result no investor should rest on.

All three are CANONICAL — formulas reproduced from the published
literature. ADAM's job is faithful implementation, not invention.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)


# =============================================================================
# 1. GRADE quality of evidence
# =============================================================================


class EvidenceGrade(str, Enum):
    """Canonical 4-level GRADE scale (Guyatt 2008-2011)."""
    HIGH = "high"
    MODERATE = "moderate"
    LOW = "low"
    VERY_LOW = "very_low"


_GRADE_ORDER = [
    EvidenceGrade.HIGH,
    EvidenceGrade.MODERATE,
    EvidenceGrade.LOW,
    EvidenceGrade.VERY_LOW,
]


class StudyDesign(str, Enum):
    """Starting grade per design.

    Per GRADE handbook §5.1: 'High-quality evidence' starts at HIGH for
    randomized; LOW for observational. ADAM's MRT (M1) is per-impression
    randomized → HIGH. ADAM's OPE on logged data is observational → LOW.
    """
    RANDOMIZED = "randomized"          # → starts HIGH
    OBSERVATIONAL = "observational"    # → starts LOW


@dataclass
class GRADEDowngrades:
    """Per-dimension downgrade flags. Each True → drop one grade level.

    Per Cochrane handbook §14.2: dimensions are independent; each
    triggered → -1 grade. Two triggered on the same dimension → -2 only
    if the issue is severe (we use a separate `severe_*` flag).

    The five canonical dimensions:
      - risk_of_bias: methodological flaws in the study design
      - inconsistency: heterogeneity across studies / cells
      - indirectness: mismatch between study question and pilot question
      - imprecision: wide confidence intervals / small sample
      - publication_bias: suspected file-drawer + selective reporting
    """
    risk_of_bias: bool = False
    severe_risk_of_bias: bool = False    # -2 instead of -1
    inconsistency: bool = False
    severe_inconsistency: bool = False
    indirectness: bool = False
    severe_indirectness: bool = False
    imprecision: bool = False
    severe_imprecision: bool = False
    publication_bias: bool = False
    severe_publication_bias: bool = False
    # Upgrades (observational only — Cochrane §14.5):
    large_effect: bool = False              # +1 (RR > 2 or RR < 0.5)
    very_large_effect: bool = False         # +2 (RR > 5 or RR < 0.2)
    dose_response: bool = False             # +1 (gradient evident)
    plausible_confounding_attenuates: bool = False  # +1


@dataclass
class GRADEResult:
    """One grading outcome with full reasoning trace."""
    grade: EvidenceGrade
    starting_grade: EvidenceGrade
    downgrade_count: int
    upgrade_count: int
    triggered: List[str] = field(default_factory=list)


def grade_evidence(
    design: StudyDesign,
    downgrades: Optional[GRADEDowngrades] = None,
) -> GRADEResult:
    """Apply GRADE per Cochrane handbook §14.

    Starts at HIGH (randomized) or LOW (observational); downgrades
    move it down the 4-level scale, upgrades (only valid for
    observational) move it up. Bounded at HIGH and VERY_LOW.
    """
    downgrades = downgrades or GRADEDowngrades()

    starting = EvidenceGrade.HIGH if design == StudyDesign.RANDOMIZED else EvidenceGrade.LOW
    start_idx = _GRADE_ORDER.index(starting)

    # Count downgrades (severe = 2, normal = 1)
    triggered: List[str] = []
    downgrade_count = 0
    for dim in (
        "risk_of_bias", "inconsistency", "indirectness",
        "imprecision", "publication_bias",
    ):
        severe = getattr(downgrades, f"severe_{dim}")
        normal = getattr(downgrades, dim)
        if severe:
            downgrade_count += 2
            triggered.append(f"-2 {dim} (severe)")
        elif normal:
            downgrade_count += 1
            triggered.append(f"-1 {dim}")

    # Upgrades only valid for observational starts (handbook §14.5)
    upgrade_count = 0
    if design == StudyDesign.OBSERVATIONAL:
        if downgrades.very_large_effect:
            upgrade_count += 2
            triggered.append("+2 very large effect")
        elif downgrades.large_effect:
            upgrade_count += 1
            triggered.append("+1 large effect")
        if downgrades.dose_response:
            upgrade_count += 1
            triggered.append("+1 dose-response gradient")
        if downgrades.plausible_confounding_attenuates:
            upgrade_count += 1
            triggered.append("+1 plausible confounding would reduce effect")

    final_idx = start_idx + downgrade_count - upgrade_count
    final_idx = max(0, min(len(_GRADE_ORDER) - 1, final_idx))

    return GRADEResult(
        grade=_GRADE_ORDER[final_idx],
        starting_grade=starting,
        downgrade_count=downgrade_count,
        upgrade_count=upgrade_count,
        triggered=triggered,
    )


# =============================================================================
# 2. E-values (VanderWeele & Ding 2017)
# =============================================================================


@dataclass
class EValueResult:
    """E-value pair: point estimate + lower CI bound."""
    e_value_point: float          # for the point estimate
    e_value_ci_lower: float       # for the CI bound nearer the null
    interpretation: str           # human-readable summary


def e_value_for_risk_ratio(rr: float) -> float:
    """E-value for a risk-ratio point estimate.

    Formula (VanderWeele & Ding 2017, Annals Intern Med 167(4)):
        For RR >= 1:  E = RR + sqrt(RR · (RR − 1))
        For RR <  1:  flip the ratio (use 1/RR), apply same formula

    Returns the minimum strength (on the RR scale) that an unmeasured
    confounder would need to have, with both the exposure AND the
    outcome, to fully explain away the observed RR.

    For RR == 1, E = 1 (no confounding needed — there's no effect).
    For RR == 2, E ≈ 3.41.
    For RR == 1.30 (Matz 2017 corrected), E ≈ 1.92.
    """
    if rr <= 0:
        # RR must be positive; degenerate input → return 1 (no effect)
        return 1.0
    if rr < 1.0:
        rr = 1.0 / rr
    return rr + math.sqrt(rr * (rr - 1.0))


def e_value_for_or_with_baseline(odds_ratio: float, baseline_risk: float) -> float:
    """E-value for an OR, converted to RR via the baseline risk.

    OR → RR conversion (Zhang & Yu 1998):
        RR = OR / (1 - p + p · OR)

    Where p is the baseline risk in the unexposed group. Used when
    only OR is reported (common in logistic regression). For rare
    outcomes (p < 5%), OR ≈ RR; for common outcomes the conversion
    matters.
    """
    if not (0.0 < baseline_risk < 1.0):
        raise ValueError(
            f"baseline_risk={baseline_risk} must be in (0, 1) — interpretable risk"
        )
    if odds_ratio <= 0:
        return 1.0
    rr = odds_ratio / (1.0 - baseline_risk + baseline_risk * odds_ratio)
    return e_value_for_risk_ratio(rr)


def compute_e_value(
    rr_point: float,
    rr_ci_lower: float,
) -> EValueResult:
    """Pair-wise E-value: point estimate + nearer-null CI bound.

    Per VanderWeele & Ding 2017 §3: report BOTH. The CI E-value is
    the more conservative claim — 'an unmeasured confounder would
    need at LEAST this strength to push the entire CI past the null.'
    """
    e_point = e_value_for_risk_ratio(rr_point)
    e_ci = e_value_for_risk_ratio(rr_ci_lower)

    interpretation = (
        f"Unmeasured confounding with RR_conf >= {e_point:.2f} (point) / "
        f">= {e_ci:.2f} (CI bound) would be required to fully explain "
        f"the observed effect away. Higher E-value → more robust to "
        f"unmeasured confounding."
    )

    return EValueResult(
        e_value_point=round(e_point, 3),
        e_value_ci_lower=round(e_ci, 3),
        interpretation=interpretation,
    )


# =============================================================================
# 3. Fragility index (Walsh et al. 2014, J Clin Epi 67(6))
# =============================================================================


@dataclass
class FragilityResult:
    """Fragility analysis for a binary 2x2 outcome table.

    fragility_index: minimum event flips to lose significance
    fragility_quotient: fragility_index / total_sample_size
        (interpretive: <1% means highly fragile — Walsh suggests
         FI=4 or FQ=0.013 as rules of thumb for 'robust')
    """
    fragility_index: int
    fragility_quotient: float
    initial_p_value: float
    initial_significant: bool
    flip_direction: str              # "to_treatment_failure" or "to_control_success"


def fragility_index(
    treatment_successes: int,
    treatment_total: int,
    control_successes: int,
    control_total: int,
    alpha: float = 0.05,
) -> FragilityResult:
    """Compute fragility index per Walsh 2014.

    For a 2x2 table that's INITIALLY SIGNIFICANT:
        Iteratively flip one event from treatment_success → failure
        (or control_failure → success, whichever brings closer to null)
        until p > alpha. The count of flips is the fragility index.

    For an INITIALLY NON-SIGNIFICANT table:
        Returns FI=0 and initial_significant=False. Walsh defines
        fragility only for initially-significant results.

    Uses Fisher's exact test (one-sided closer-to-null direction),
    standard for 2x2 binary outcomes.
    """
    if treatment_total <= 0 or control_total <= 0:
        raise ValueError("totals must be positive")
    if not (0 <= treatment_successes <= treatment_total):
        raise ValueError(
            f"treatment_successes={treatment_successes} outside [0, {treatment_total}]"
        )
    if not (0 <= control_successes <= control_total):
        raise ValueError(
            f"control_successes={control_successes} outside [0, {control_total}]"
        )

    p_initial = _fisher_two_sided(
        treatment_successes, treatment_total,
        control_successes, control_total,
    )

    if p_initial > alpha:
        return FragilityResult(
            fragility_index=0,
            fragility_quotient=0.0,
            initial_p_value=round(p_initial, 5),
            initial_significant=False,
            flip_direction="not_applicable",
        )

    # Determine which direction reduces evidence: if treatment rate >
    # control rate, flipping treatment_success → failure narrows the gap
    t_rate = treatment_successes / treatment_total
    c_rate = control_successes / control_total
    flip_direction = (
        "to_treatment_failure" if t_rate > c_rate
        else "to_control_success"
    )

    flips = 0
    t_succ, c_succ = treatment_successes, control_successes
    total_n = treatment_total + control_total

    # Cap iterations at full table size (degenerate but safe)
    while flips < total_n:
        if flip_direction == "to_treatment_failure":
            if t_succ <= 0:
                break
            t_succ -= 1
        else:
            if c_succ >= control_total:
                break
            c_succ += 1

        flips += 1
        p = _fisher_two_sided(
            t_succ, treatment_total, c_succ, control_total,
        )
        if p > alpha:
            return FragilityResult(
                fragility_index=flips,
                fragility_quotient=round(flips / total_n, 4),
                initial_p_value=round(p_initial, 5),
                initial_significant=True,
                flip_direction=flip_direction,
            )

    # Degenerate — couldn't flip enough to lose significance even
    # exhausting the table. Walsh notes this can happen with very
    # large tables; report the cap.
    return FragilityResult(
        fragility_index=flips,
        fragility_quotient=round(flips / total_n, 4),
        initial_p_value=round(p_initial, 5),
        initial_significant=True,
        flip_direction=flip_direction,
    )


def _fisher_two_sided(
    a: int, n_a: int, b: int, n_b: int,
) -> float:
    """Two-sided Fisher's exact test p-value for a 2x2 table.

    Uses scipy when available; falls back to a numerically-stable
    pure-Python implementation otherwise. The test is canonical for
    binary 2x2 outcomes — small N exact, no normal-approximation
    drift at low cell counts.
    """
    try:
        from scipy.stats import fisher_exact
        # 2x2: [[t_succ, t_fail], [c_succ, c_fail]]
        table = [[a, n_a - a], [b, n_b - b]]
        _odds, p = fisher_exact(table, alternative="two-sided")
        return float(p)
    except ImportError:
        return _fisher_two_sided_python(a, n_a, b, n_b)


def _fisher_two_sided_python(
    a: int, n_a: int, b: int, n_b: int,
) -> float:
    """Pure-Python Fisher exact (two-sided), via hypergeometric sum.

    For testing environments without scipy. Numerically stable for
    moderate sample sizes (< 10000 total).
    """
    n = n_a + n_b
    k = a + b  # total successes
    # P(X = x) under hypergeometric(n, k, n_a)
    def hg_pmf(x: int) -> float:
        if x < max(0, k - n_b) or x > min(k, n_a):
            return 0.0
        return (
            math.comb(n_a, x) * math.comb(n_b, k - x)
            / math.comb(n, k)
        )
    observed_pmf = hg_pmf(a)
    p_value = 0.0
    for x in range(max(0, k - n_b), min(k, n_a) + 1):
        if hg_pmf(x) <= observed_pmf + 1e-12:
            p_value += hg_pmf(x)
    return min(1.0, p_value)


# =============================================================================
# Composed evidence package
# =============================================================================


@dataclass
class EvidencePackage:
    """One claim's full evidence package: GRADE + E-value + fragility.

    Suitable for stamping onto a ProjectedImpactClaim adjudication
    report or onto a campaign-level effect-size claim before
    presentation.
    """
    grade: GRADEResult
    e_value: Optional[EValueResult]
    fragility: Optional[FragilityResult]
    summary: str                     # one-line investor-ready summary


def build_evidence_package(
    design: StudyDesign,
    rr_point: Optional[float] = None,
    rr_ci_lower: Optional[float] = None,
    fragility_table: Optional[Tuple[int, int, int, int]] = None,
    downgrades: Optional[GRADEDowngrades] = None,
    alpha: float = 0.05,
) -> EvidencePackage:
    """Assemble all three analyses for one claim.

    Args:
        design: RANDOMIZED or OBSERVATIONAL (drives GRADE start)
        rr_point: point estimate of the risk ratio (None to skip E-value)
        rr_ci_lower: lower CI bound nearer the null (None to skip)
        fragility_table: (t_succ, t_n, c_succ, c_n) tuple, or None
        downgrades: GRADEDowngrades flags
        alpha: significance threshold for fragility test

    Each component soft-fails independently — missing fragility_table
    just means no fragility analysis is computed; missing rr_* means
    no E-value. Caller decides what to require.
    """
    grade_result = grade_evidence(design, downgrades=downgrades)

    e_value_result = None
    if rr_point is not None and rr_ci_lower is not None:
        e_value_result = compute_e_value(rr_point, rr_ci_lower)

    fragility_result = None
    if fragility_table is not None:
        try:
            fragility_result = fragility_index(
                *fragility_table, alpha=alpha,
            )
        except ValueError as exc:
            logger.warning("Fragility analysis skipped: %s", exc)

    parts = [f"GRADE: {grade_result.grade.value}"]
    if e_value_result:
        parts.append(f"E-value: {e_value_result.e_value_point:.2f} (point)")
    if fragility_result and fragility_result.initial_significant:
        parts.append(f"FI: {fragility_result.fragility_index}")
    summary = " | ".join(parts)

    return EvidencePackage(
        grade=grade_result,
        e_value=e_value_result,
        fragility=fragility_result,
        summary=summary,
    )
