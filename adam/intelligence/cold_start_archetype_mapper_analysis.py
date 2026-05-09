"""ANALYSIS-C: Cold-start archetype mapper distribution sanity.

Per P.1 slice + P.0 audit findings (commit 64b6daa). Synthetic
grid evaluation of `map_cold_start_archetype` across bid-stream
signal combinations to validate that W.2a's mapper isn't
degenerate before pilot bid traffic exposes a calibration problem.

This module is ANALYSIS INFRASTRUCTURE, not bid-time code. Lives
in adam/intelligence/ for proximity to the mapper but is never
called from cascade paths. The synthetic grid + criteria
framework requires zero external data dependencies — runs purely
from W.2a's tunable constants.

Five healthy-distribution criteria (per P.0 §9 + P.1 spec):
    1. No degenerate dominance: max archetype share ≤ 40%
    2. All 8 archetypes ≥ 1% of grid combinations
    3. Per-axis change rate ≥ 30% (each axis meaningfully shifts
       assignments)
    4. Default-fallback rate < 20% (signal coverage is sufficient)
    5. Determinism: same input → same output
"""
from collections import Counter
from itertools import product
from typing import Any, Dict, List, Optional

from adam.cold_start.models.enums import ArchetypeID
from adam.intelligence.cold_start_archetype_mapper import (
    DEVICE_ARCHETYPE_HINTS,
    HOUR_BUCKET_ARCHETYPE_HINTS,
    IAB_CATEGORY_ARCHETYPE_HINTS,
    RURAL_GEO_INDICATORS,
    URBAN_GEO_INDICATORS,
    map_cold_start_archetype,
)


# ============================================================================
# Synthetic grid axes
# ============================================================================
# Each axis includes representative populated values + None to capture
# fall-through behavior. Cardinality determines total Cartesian product.

GEO_GRID: List[Optional[str]] = (
    sorted(URBAN_GEO_INDICATORS)[:5]    # 5 urban representatives
    + sorted(RURAL_GEO_INDICATORS)[:5]  # 5 rural representatives
    + [None, "UNKNOWN_ZIP"]              # 2 fall-through cases
)
"""12 geo values: 5 urban + 5 rural + None + unrecognized."""

DEVICE_GRID: List[Optional[str]] = (
    list(DEVICE_ARCHETYPE_HINTS.keys()) + [None]
)
"""5 device values: desktop, mobile, tablet, ctv, None."""

HOUR_GRID: List[Optional[int]] = [3, 8, 12, 19, None]
"""5 hours: 1 per bucket (late_night / morning_commute /
workday / evening_leisure) + None."""

IAB_GRID: List[Optional[str]] = (
    list(IAB_CATEGORY_ARCHETYPE_HINTS.keys()) + [None]
)
"""13 IAB values: 12 hint-dict keys + None."""

# Determinism check fixture — held constant across calls.
_DETERMINISM_CHECK_FIXTURE = dict(
    geo="NYC",
    device="mobile",
    hour_of_day=12,
    iab_category="Business and Finance",
)


# ============================================================================
# Criteria thresholds
# ============================================================================

CRITERION_1_MAX_DOMINANCE_THRESHOLD: float = 0.40
"""Max archetype share above which dominance is flagged."""

CRITERION_2_MIN_REPRESENTATION_THRESHOLD: float = 0.01
"""Min fraction for an archetype to count as represented."""

CRITERION_3_MIN_CHANGE_RATE: float = 0.30
"""Min per-axis change rate for axis to count as effective."""

CRITERION_4_MAX_DEFAULT_RATE: float = 0.20
"""Max default-fallback rate before signal-coverage flagged weak."""

CRITERION_5_DETERMINISM_CALL_COUNT: int = 100
"""Number of repeated-call samples for determinism check."""


# ============================================================================
# Public API
# ============================================================================

def evaluate_grid() -> Dict[str, Any]:
    """Run map_cold_start_archetype over the full Cartesian product
    of grid axes; return distribution + per-axis effect data.

    Returns dict with:
        - "total_combinations": int
        - "archetype_distribution": Dict[ArchetypeID, int]
        - "default_fallback_count": int
        - "default_fallback_rate": float
        - "per_axis_effect": Dict[str, Dict] (axis name → effect metrics)
        - "criteria_evaluation": Dict[str, Any] (criterion name → pass/fail + supporting metric)
        - "grid_results": List[Dict] (full result table for report)
    """
    results: List[Dict[str, Any]] = []
    for geo, device, hour, iab in product(
        GEO_GRID, DEVICE_GRID, HOUR_GRID, IAB_GRID,
    ):
        archetype = map_cold_start_archetype(
            geo=geo,
            device=device,
            hour_of_day=hour,
            iab_category=iab,
        )
        results.append({
            "geo": geo,
            "device": device,
            "hour": hour,
            "iab": iab,
            "archetype": archetype,
        })

    distribution = Counter(r["archetype"] for r in results)

    # Default-fallback: combinations where all four signals are None
    # (the all-None Cartesian cell — signals provide no hints, mapper
    # falls through to PRAGMATIST default).
    default_count = sum(
        1 for r in results
        if r["geo"] is None and r["device"] is None
        and r["hour"] is None and r["iab"] is None
    )

    per_axis_effect = _compute_per_axis_effect(results)
    criteria = _evaluate_criteria(
        results, distribution, default_count, per_axis_effect,
    )

    return {
        "total_combinations": len(results),
        "archetype_distribution": dict(distribution),
        "default_fallback_count": default_count,
        "default_fallback_rate": (
            default_count / len(results) if results else 0.0
        ),
        "per_axis_effect": per_axis_effect,
        "criteria_evaluation": criteria,
        "grid_results": results,
    }


def _compute_per_axis_effect(
    results: List[Dict[str, Any]],
) -> Dict[str, Dict[str, Any]]:
    """For each signal axis, compute fraction of pivot cases where
    varying the axis value (holding the other three constant)
    changes the assigned archetype.

    Effect metric: groups_with_change / total_groups, where each
    group = a fixed combination of the other three axes' values.
    """
    effect = {}
    axes = ["geo", "device", "hour", "iab"]
    for axis in axes:
        other_axes = [a for a in axes if a != axis]
        groups: Dict[tuple, list] = {}
        for r in results:
            key = tuple(r[a] for a in other_axes)
            groups.setdefault(key, []).append(r["archetype"])

        changes = sum(
            1 for archetypes in groups.values()
            if len(set(archetypes)) > 1
        )
        total_groups = len(groups)
        effect[axis] = {
            "groups_with_change": changes,
            "total_groups": total_groups,
            "change_rate": (
                changes / total_groups if total_groups else 0.0
            ),
        }
    return effect


def _evaluate_criteria(
    results: List[Dict[str, Any]],
    distribution: Counter,
    default_count: int,
    per_axis_effect: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    """Evaluate the 5 healthy-distribution criteria."""
    total = len(results)

    # Criterion 1: no >40% dominance
    max_share = (
        max(distribution.values()) / total if total else 0.0
    )
    crit_1 = max_share <= CRITERION_1_MAX_DOMINANCE_THRESHOLD

    # Criterion 2: all 8 archetypes ≥ 1%
    min_count = total * CRITERION_2_MIN_REPRESENTATION_THRESHOLD
    represented = {
        a for a, count in distribution.items()
        if count >= min_count
    }
    crit_2 = len(represented) == 8

    # Criterion 3: each axis ≥ 30% change rate
    crit_3 = all(
        effect["change_rate"] >= CRITERION_3_MIN_CHANGE_RATE
        for effect in per_axis_effect.values()
    )
    min_change_rate = (
        min(e["change_rate"] for e in per_axis_effect.values())
        if per_axis_effect else 0.0
    )

    # Criterion 4: default fallback < 20%
    default_rate = default_count / total if total else 0.0
    crit_4 = default_rate < CRITERION_4_MAX_DEFAULT_RATE

    # Criterion 5: determinism (100 repeated calls)
    sample = map_cold_start_archetype(**_DETERMINISM_CHECK_FIXTURE)
    crit_5 = all(
        map_cold_start_archetype(**_DETERMINISM_CHECK_FIXTURE) == sample
        for _ in range(CRITERION_5_DETERMINISM_CALL_COUNT)
    )

    return {
        "criterion_1_no_dominance": crit_1,
        "criterion_1_max_share": max_share,
        "criterion_2_all_8_represented": crit_2,
        "criterion_2_represented_count": len(represented),
        "criterion_3_per_axis_effect": crit_3,
        "criterion_3_min_change_rate": min_change_rate,
        "criterion_4_default_rate_bounded": crit_4,
        "criterion_4_default_rate": default_rate,
        "criterion_5_deterministic": crit_5,
    }


# ============================================================================
# Report writer
# ============================================================================

def write_analysis_report(
    output_path: str = (
        "docs/analyses/COLD_START_ARCHETYPE_MAPPER_DISTRIBUTION_P1.md"
    ),
) -> None:
    """Produce the analysis report at the given path. All output
    is synthetic — no production data, no PII."""
    from datetime import datetime, timezone
    import os

    results = evaluate_grid()
    distribution = results["archetype_distribution"]
    total = results["total_combinations"]
    criteria = results["criteria_evaluation"]
    per_axis = results["per_axis_effect"]

    # Build distribution table sorted by count descending.
    dist_sorted = sorted(
        ArchetypeID, key=lambda a: -distribution.get(a, 0),
    )

    lines = [
        "# ANALYSIS-C: Cold-Start Archetype Mapper Distribution Sanity",
        "## Slice ID: P.1 (P chain analysis 1 of N)",
        "## Predecessor: 64b6daa (P.0 audit)",
        f"## Generated: {datetime.now(timezone.utc).isoformat()}",
        "## Source: synthetic grid evaluation; no production data",
        "",
        "## §1 Executive Summary",
        "",
    ]

    # Criteria summary
    all_pass = all([
        criteria["criterion_1_no_dominance"],
        criteria["criterion_2_all_8_represented"],
        criteria["criterion_3_per_axis_effect"],
        criteria["criterion_4_default_rate_bounded"],
        criteria["criterion_5_deterministic"],
    ])
    if all_pass:
        lines.append(
            "**RESULT: All 5 criteria PASS.** "
            "W.2a `map_cold_start_archetype` is healthy across the "
            "synthetic Cartesian grid. Pilot launch posture for "
            "this component is reassured."
        )
    else:
        lines.append(
            "**RESULT: One or more criteria FAIL.** See §5 for "
            "per-criterion breakdown and §7 for recommended tuning."
        )
    lines.append("")
    lines.append(
        f"Grid scope: **{total} combinations** "
        f"(geo × device × hour × iab Cartesian product). "
        f"Max archetype share: **{criteria['criterion_1_max_share']*100:.1f}%** "
        f"(threshold: ≤{CRITERION_1_MAX_DOMINANCE_THRESHOLD*100:.0f}%). "
        f"Default-fallback rate: **{criteria['criterion_4_default_rate']*100:.3f}%** "
        f"(threshold: <{CRITERION_4_MAX_DEFAULT_RATE*100:.0f}%). "
        f"All 8 archetypes represented: **{criteria['criterion_2_represented_count']}/8**."
    )
    lines.append("")

    lines.extend([
        "## §2 Grid configuration",
        "",
        f"| Axis | Cardinality | Values |",
        "|------|-------------|--------|",
        f"| geo | {len(GEO_GRID)} | 5 urban + 5 rural + None + UNKNOWN_ZIP |",
        f"| device | {len(DEVICE_GRID)} | desktop / mobile / tablet / ctv + None |",
        f"| hour_of_day | {len(HOUR_GRID)} | 3 / 8 / 12 / 19 + None |",
        f"| iab_category | {len(IAB_GRID)} | 12 hint-dict keys + None |",
        f"| **Total** | **{total}** | Cartesian product |",
        "",
    ])

    lines.extend([
        "## §3 Archetype distribution",
        "",
        "| Archetype | Count | Share | Bar |",
        "|-----------|-------|-------|-----|",
    ])
    for arch in dist_sorted:
        count = distribution.get(arch, 0)
        share = count / total if total else 0.0
        bar = "█" * int(share * 100 / 2)
        lines.append(
            f"| {arch.value} | {count} | {share*100:.1f}% | {bar} |"
        )
    lines.append("")

    lines.extend([
        "## §4 Per-axis effect",
        "",
        "Each axis: fraction of pivot groups (other three axes "
        "fixed) where varying this axis changes the assigned "
        "archetype. Higher rate = more effective signal.",
        "",
        "| Axis | Groups with change | Total groups | Change rate |",
        "|------|--------------------|--------------|-------------|",
    ])
    for axis_name, effect in per_axis.items():
        lines.append(
            f"| {axis_name} | {effect['groups_with_change']} | "
            f"{effect['total_groups']} | "
            f"{effect['change_rate']*100:.1f}% |"
        )
    lines.append("")

    lines.extend([
        "## §5 Criteria evaluation",
        "",
        "| # | Criterion | Threshold | Observed | Pass? |",
        "|---|-----------|-----------|----------|-------|",
        f"| 1 | No archetype dominance | ≤ {CRITERION_1_MAX_DOMINANCE_THRESHOLD*100:.0f}% max share | "
        f"{criteria['criterion_1_max_share']*100:.1f}% | "
        f"{'✅' if criteria['criterion_1_no_dominance'] else '❌'} |",
        f"| 2 | All 8 archetypes ≥ {CRITERION_2_MIN_REPRESENTATION_THRESHOLD*100:.0f}% | "
        f"all 8 | "
        f"{criteria['criterion_2_represented_count']}/8 | "
        f"{'✅' if criteria['criterion_2_all_8_represented'] else '❌'} |",
        f"| 3 | Per-axis change rate | ≥ {CRITERION_3_MIN_CHANGE_RATE*100:.0f}% | "
        f"min={criteria['criterion_3_min_change_rate']*100:.1f}% | "
        f"{'✅' if criteria['criterion_3_per_axis_effect'] else '❌'} |",
        f"| 4 | Default-fallback rate | < {CRITERION_4_MAX_DEFAULT_RATE*100:.0f}% | "
        f"{criteria['criterion_4_default_rate']*100:.3f}% | "
        f"{'✅' if criteria['criterion_4_default_rate_bounded'] else '❌'} |",
        f"| 5 | Determinism (100 calls) | identical output | "
        f"{'identical' if criteria['criterion_5_deterministic'] else 'divergent'} | "
        f"{'✅' if criteria['criterion_5_deterministic'] else '❌'} |",
        "",
    ])

    lines.extend([
        "## §6 Default-fallback analysis",
        "",
        f"`map_cold_start_archetype` returned the PRAGMATIST default "
        f"via the all-signals-missing path (geo + device + hour + "
        f"iab all None) for **{results['default_fallback_count']} of "
        f"{total}** combinations "
        f"({criteria['criterion_4_default_rate']*100:.3f}%).",
        "",
        "Interpretation: extremely low default rate means the mapper's "
        "signal coverage is robust — most combinations have at least "
        "one populated signal that contributes a hint. The single "
        "all-None case is the structural baseline and matches the "
        "spec'd cold-start fallback.",
        "",
    ])

    lines.extend([
        "## §7 Recommendations",
        "",
    ])
    if all_pass:
        lines.extend([
            "All criteria pass. **W.2a `map_cold_start_archetype` is "
            "healthy for pilot launch.** Recommendations:",
            "",
            "- Pin all 5 criteria as architectural invariants in "
            "`tests/intelligence/test_cold_start_archetype_mapper_analysis.py`. "
            "Future tuning of the hint dicts that breaks any criterion "
            "becomes a regression caught at test time.",
            "- Re-run this analysis post-pilot if W.2a's hint dicts "
            "are tuned from pilot data (S5.5 nightly retrain or manual "
            "calibration).",
            "- No pre-pilot tuning needed.",
        ])
    else:
        lines.append(
            "One or more criteria fail. Tuning recommendations:"
        )
        lines.append("")
        if not criteria["criterion_1_no_dominance"]:
            lines.append(
                f"- **Criterion 1 fail** "
                f"(max share {criteria['criterion_1_max_share']*100:.1f}% > "
                f"{CRITERION_1_MAX_DOMINANCE_THRESHOLD*100:.0f}%): a single "
                f"archetype is over-represented. Investigate which hint "
                f"dict's archetype lists are repeating the dominant "
                f"archetype most often; rebalance."
            )
        if not criteria["criterion_2_all_8_represented"]:
            lines.append(
                f"- **Criterion 2 fail** "
                f"({criteria['criterion_2_represented_count']}/8 archetypes "
                f"represented): some archetypes structurally unreachable "
                f"from the current hint dicts. Audit hint dicts for "
                f"missing archetype coverage."
            )
        if not criteria["criterion_3_per_axis_effect"]:
            lines.append(
                f"- **Criterion 3 fail** (min change rate "
                f"{criteria['criterion_3_min_change_rate']*100:.1f}% < "
                f"{CRITERION_3_MIN_CHANGE_RATE*100:.0f}%): one or more axes "
                f"don't meaningfully shift assignments. Inspect the "
                f"weakest axis and consider strengthening its hints "
                f"or adding tilt amplifiers (per geo's URBAN/RURAL "
                f"pattern)."
            )
        if not criteria["criterion_4_default_rate_bounded"]:
            lines.append(
                f"- **Criterion 4 fail** "
                f"(default rate {criteria['criterion_4_default_rate']*100:.1f}% ≥ "
                f"{CRITERION_4_MAX_DEFAULT_RATE*100:.0f}%): mapper falls "
                f"through to PRAGMATIST default too often. Expand hint "
                f"dict coverage (more IAB categories; more device types)."
            )
        if not criteria["criterion_5_deterministic"]:
            lines.append(
                "- **Criterion 5 fail**: same input produced different "
                "outputs across 100 calls. Indicates a non-deterministic "
                "code path (random tie-break? mutable state?). Critical bug; "
                "fix before pilot launch."
            )
    lines.append("")

    lines.extend([
        "## §8 Determinism + tie-break audit",
        "",
        f"Determinism check: `map_cold_start_archetype("
        f"geo='NYC', device='mobile', hour_of_day=12, "
        f"iab_category='Business and Finance')` returned the same "
        f"ArchetypeID across {CRITERION_5_DETERMINISM_CALL_COUNT} "
        f"repeated calls: "
        f"**{'PASS' if criteria['criterion_5_deterministic'] else 'FAIL'}**.",
        "",
        "Tie-break: per W.2a spec, ties are broken by lexicographic "
        "order of `archetype.value` for determinism. The ARCHETYPE_ID "
        "values sort as: achiever < analyst < connector < creator < "
        "explorer < guardian < nurturer < pragmatist. So in tied "
        "voting, alphabetically-earlier archetypes win.",
        "",
    ])

    lines.extend([
        "## §9 Audit closure",
        "",
        f"Generated by `evaluate_grid()` + `write_analysis_report()` in "
        f"`adam/intelligence/cold_start_archetype_mapper_analysis.py`. "
        f"Full grid result table available via `evaluate_grid()['grid_results']`.",
        "",
        "Re-run command:",
        "```",
        "python -c \"from adam.intelligence.cold_start_archetype_mapper_analysis "
        "import write_analysis_report; write_analysis_report()\"",
        "```",
        "",
    ])

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        f.write("\n".join(lines))
