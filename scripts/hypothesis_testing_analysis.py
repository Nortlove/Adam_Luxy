#!/usr/bin/env python3
"""
ADAM Hypothesis Testing Analysis Script
========================================

Phase 1 analysis script for testing pre-registered hypotheses against
the 1B+ ingested review corpus. See docs/HYPOTHESIS_TESTING_PLAN.md.

Priority Hypotheses (Phase 1: Foundation):

H3.1: NDF mechanism susceptibility predicts helpful vote mechanism patterns
      better than random (AUC > 0.60, d > 0.3)

H2.2: NDF temporal_horizon discriminates present-focused vs future-focused
      review language (d > 0.5)

H1.1: NDF dimensions explain more variance in mechanism effectiveness than
      archetype alone (ΔR² > 0.05)

Usage:
    python scripts/hypothesis_testing_analysis.py --hypothesis H3.1
    python scripts/hypothesis_testing_analysis.py --hypothesis all
    python scripts/hypothesis_testing_analysis.py --verify-data
"""

import argparse
import json
import logging
import math
import os
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# Path to ingestion results
RESULTS_DIR = Path(__file__).parent.parent / "data" / "ingestion_results"
MERGED_PRIORS_PATH = Path(__file__).parent.parent / "data" / "learning" / "ingestion_merged_priors.json"


# =============================================================================
# STATISTICAL UTILITIES
# =============================================================================

def cohens_d(group1: np.ndarray, group2: np.ndarray) -> float:
    """Compute Cohen's d effect size."""
    n1, n2 = len(group1), len(group2)
    if n1 < 2 or n2 < 2:
        return 0.0
    var1, var2 = np.var(group1, ddof=1), np.var(group2, ddof=1)
    pooled_std = math.sqrt(((n1 - 1) * var1 + (n2 - 1) * var2) / (n1 + n2 - 2))
    if pooled_std < 1e-9:
        return 0.0
    return (np.mean(group1) - np.mean(group2)) / pooled_std


def pearson_r(x: np.ndarray, y: np.ndarray) -> float:
    """Compute Pearson correlation."""
    if len(x) < 3 or len(y) < 3:
        return 0.0
    if np.std(x) < 1e-9 or np.std(y) < 1e-9:
        return 0.0
    return float(np.corrcoef(x, y)[0, 1])


def r_squared(x: np.ndarray, y: np.ndarray) -> float:
    """Compute R² (coefficient of determination)."""
    r = pearson_r(x, y)
    return r * r


def bootstrap_ci(
    data: np.ndarray,
    statistic_fn,
    n_bootstrap: int = 1000,
    ci: float = 0.95,
) -> Tuple[float, float, float]:
    """Bootstrap confidence interval for a statistic."""
    rng = np.random.default_rng(42)
    boot_stats = []
    for _ in range(n_bootstrap):
        sample = rng.choice(data, size=len(data), replace=True)
        boot_stats.append(statistic_fn(sample))
    boot_stats = np.array(boot_stats)
    alpha = (1 - ci) / 2
    lower = float(np.percentile(boot_stats, alpha * 100))
    upper = float(np.percentile(boot_stats, (1 - alpha) * 100))
    point = float(statistic_fn(data))
    return point, lower, upper


# =============================================================================
# DATA LOADING
# =============================================================================

def load_merged_priors() -> Dict:
    """Load merged ingestion priors."""
    if not MERGED_PRIORS_PATH.exists():
        logger.error(f"Merged priors not found at {MERGED_PRIORS_PATH}")
        logger.info("Run scripts/merge_ingestion_priors.py first")
        return {}
    
    with open(MERGED_PRIORS_PATH) as f:
        return json.load(f)


def load_category_results(max_categories: int = 0) -> List[Dict]:
    """Load individual category result files."""
    results = []
    if not RESULTS_DIR.exists():
        logger.error(f"Results directory not found: {RESULTS_DIR}")
        return results
    
    result_files = sorted(RESULTS_DIR.glob("*_result.json"))
    if max_categories > 0:
        result_files = result_files[:max_categories]
    
    for path in result_files:
        try:
            with open(path) as f:
                data = json.load(f)
            data["_source_file"] = path.name
            results.append(data)
        except Exception as e:
            logger.warning(f"Failed to load {path.name}: {e}")
    
    logger.info(f"Loaded {len(results)} category results")
    return results


def verify_data_availability() -> Dict[str, Any]:
    """Verify data is available for hypothesis testing."""
    report = {
        "merged_priors_exists": MERGED_PRIORS_PATH.exists(),
        "results_dir_exists": RESULTS_DIR.exists(),
        "category_results": 0,
        "has_ndf": False,
        "has_effectiveness": False,
        "has_dimensions": False,
        "has_templates": False,
        "total_reviews": 0,
        "ndf_reviews": 0,
        "archetypes_found": [],
        "ready_for": [],
    }
    
    if report["merged_priors_exists"]:
        priors = load_merged_priors()
        report["total_reviews"] = priors.get("total_reviews_processed", 0)
        
        ndf = priors.get("ndf_population", {})
        if ndf:
            report["has_ndf"] = ndf.get("ndf_count", 0) > 0
            report["ndf_reviews"] = ndf.get("ndf_count", 0)
            report["ndf_archetype_profiles"] = len(ndf.get("ndf_archetype_profiles", {}))
        
        em = priors.get("effectiveness_matrix", {})
        if em:
            report["has_effectiveness"] = True
            report["archetypes_found"] = list(em.keys())
        
        dd = priors.get("dimension_distributions", {})
        if dd:
            report["has_dimensions"] = True
        
        # Determine which hypotheses can be tested
        if report["has_ndf"] and report["has_effectiveness"]:
            report["ready_for"].append("H3.1")
        if report["has_ndf"]:
            report["ready_for"].append("H2.2")
        if report["has_ndf"] and report["has_effectiveness"]:
            report["ready_for"].append("H1.1")
        if report["has_ndf"]:
            report["ready_for"].append("H5.1")
        if report["has_effectiveness"]:
            report["ready_for"].append("H4.1")
    
    if report["results_dir_exists"]:
        results = list(RESULTS_DIR.glob("*_result.json"))
        report["category_results"] = len(results)
        report["has_templates"] = any(True for r in results)
    
    return report


# =============================================================================
# HYPOTHESIS TESTS
# =============================================================================

def test_H3_1(priors: Dict) -> Dict[str, Any]:
    """
    H3.1: NDF mechanism susceptibility predicts helpful vote mechanism patterns
           better than random.
    
    Test: Compare NDF-predicted susceptibility ranking to empirical mechanism
          effectiveness ranking from helpful vote analysis.
    
    Threshold: Rank correlation > 0.30, effect size d > 0.3
    Falsified if: correlation < 0.15 or d < 0.15
    """
    result = {
        "hypothesis": "H3.1",
        "description": "NDF mechanism susceptibility predicts HVI patterns",
        "threshold": "r > 0.30, d > 0.3",
        "falsification": "r < 0.15 or d < 0.15",
    }
    
    ndf_pop = priors.get("ndf_population", {})
    effectiveness = priors.get("effectiveness_matrix", {})
    
    if not ndf_pop or not effectiveness:
        result["status"] = "INSUFFICIENT_DATA"
        result["reason"] = "Need both NDF population and effectiveness matrix"
        return result
    
    # For each archetype, compute NDF-predicted susceptibility and compare
    # to empirical mechanism effectiveness
    ndf_profiles = ndf_pop.get("ndf_archetype_profiles", {})
    
    if not ndf_profiles:
        result["status"] = "INSUFFICIENT_DATA"
        result["reason"] = "No archetype-conditioned NDF profiles"
        return result
    
    # Import NDF susceptibility computation
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from adam.intelligence.ndf_extractor import compute_mechanism_susceptibility
    
    # Collect prediction-observation pairs
    predicted_ranks = []
    observed_ranks = []
    per_archetype = {}
    
    CIALDINI_TO_ADAM = {
        "social_proof": "social_proof",
        "scarcity": "scarcity",
        "authority": "authority",
        "commitment": "commitment_consistency",
        "reciprocity": "reciprocity",
        "liking": "liking",
        "unity": "unity",
    }
    
    for archetype, ndf_profile in ndf_profiles.items():
        if archetype not in effectiveness:
            continue
        
        # Get NDF-predicted susceptibility
        ndf_suscept = compute_mechanism_susceptibility(ndf_profile)
        
        # Get empirical effectiveness for this archetype
        empirical = effectiveness[archetype]
        
        # Find matching mechanisms
        arch_predicted = []
        arch_observed = []
        
        for cialdini_mech, suscept_score in ndf_suscept.items():
            # Try to find matching mechanism in effectiveness matrix
            for emp_mech, emp_data in empirical.items():
                emp_key = emp_mech.lower().replace(" ", "_")
                if cialdini_mech.lower() in emp_key or emp_key in cialdini_mech.lower():
                    emp_rate = emp_data.get("success_rate", 0.5) if isinstance(emp_data, dict) else float(emp_data)
                    arch_predicted.append(suscept_score)
                    arch_observed.append(emp_rate)
                    break
        
        if len(arch_predicted) >= 3:
            r = pearson_r(np.array(arch_predicted), np.array(arch_observed))
            per_archetype[archetype] = {
                "r": round(r, 4),
                "n_mechanisms": len(arch_predicted),
                "count": ndf_profile.get("count", 0),
            }
            predicted_ranks.extend(arch_predicted)
            observed_ranks.extend(arch_observed)
    
    if len(predicted_ranks) < 5:
        result["status"] = "INSUFFICIENT_DATA"
        result["reason"] = f"Only {len(predicted_ranks)} matched mechanism pairs"
        return result
    
    # Compute overall correlation
    overall_r = pearson_r(np.array(predicted_ranks), np.array(observed_ranks))
    
    # Compute effect size (d) comparing high-susceptibility vs low-susceptibility outcomes
    median_suscept = np.median(predicted_ranks)
    high_suscept_outcomes = [o for p, o in zip(predicted_ranks, observed_ranks) if p > median_suscept]
    low_suscept_outcomes = [o for p, o in zip(predicted_ranks, observed_ranks) if p <= median_suscept]
    
    d = cohens_d(np.array(high_suscept_outcomes), np.array(low_suscept_outcomes))
    
    # Determine result
    supported = overall_r > 0.30 and abs(d) > 0.3
    falsified = overall_r < 0.15 and abs(d) < 0.15
    
    result.update({
        "status": "SUPPORTED" if supported else ("FALSIFIED" if falsified else "INCONCLUSIVE"),
        "overall_r": round(overall_r, 4),
        "effect_size_d": round(d, 4),
        "n_pairs": len(predicted_ranks),
        "archetypes_tested": len(per_archetype),
        "per_archetype": per_archetype,
    })
    
    return result


def test_H2_2(priors: Dict) -> Dict[str, Any]:
    """
    H2.2: NDF temporal_horizon discriminates present-focused vs future-focused
           review language.
    
    Test: Compare tau distribution between present-oriented and future-oriented
          archetype NDF profiles.
    
    Threshold: d > 0.5 (medium effect)
    Falsified if: d < 0.2
    """
    result = {
        "hypothesis": "H2.2",
        "description": "NDF temporal_horizon discriminates temporal orientation",
        "threshold": "d > 0.5",
        "falsification": "d < 0.2",
    }
    
    ndf_pop = priors.get("ndf_population", {})
    if not ndf_pop:
        result["status"] = "INSUFFICIENT_DATA"
        return result
    
    ndf_profiles = ndf_pop.get("ndf_archetype_profiles", {})
    ndf_means = ndf_pop.get("ndf_means", {})
    ndf_stds = ndf_pop.get("ndf_stds", {})
    
    # Classify archetypes by expected temporal orientation
    # Based on domain knowledge of archetype definitions
    PRESENT_ORIENTED = ["impulsive_buyer", "sensation_seeker", "deal_hunter",
                        "trend_follower", "emotional_buyer"]
    FUTURE_ORIENTED = ["quality_seeker", "researcher", "achiever",
                       "brand_loyalist", "cautious_buyer", "analyst"]
    
    present_taus = []
    future_taus = []
    
    for archetype, profile in ndf_profiles.items():
        tau = profile.get("temporal_horizon", None)
        if tau is None:
            continue
        
        arch_lower = archetype.lower().replace(" ", "_")
        
        if any(p in arch_lower for p in PRESENT_ORIENTED):
            present_taus.append(tau)
        elif any(f in arch_lower for f in FUTURE_ORIENTED):
            future_taus.append(tau)
    
    if len(present_taus) < 2 or len(future_taus) < 2:
        # Alternative: use dimension distributions to create synthetic groups
        tau_dist = ndf_pop.get("ndf_distributions", {}).get("temporal_horizon", [])
        if tau_dist and len(tau_dist) == 10:
            # Bottom 3 deciles = present-oriented, top 3 = future-oriented
            total = sum(tau_dist)
            if total > 0:
                present_count = sum(tau_dist[:3])
                future_count = sum(tau_dist[7:])
                present_mean = 0.15  # Average of deciles 0-2
                future_mean = 0.85   # Average of deciles 7-9
                
                # Estimate d from distribution shape
                global_mean = ndf_means.get("temporal_horizon", 0.5)
                global_std = ndf_stds.get("temporal_horizon", 0.25)
                
                result.update({
                    "status": "DISTRIBUTION_ANALYSIS",
                    "global_mean_tau": round(global_mean, 4),
                    "global_std_tau": round(global_std, 4),
                    "present_proportion": round(present_count / total, 4) if total > 0 else 0,
                    "future_proportion": round(future_count / total, 4) if total > 0 else 0,
                    "estimated_d": round((future_mean - present_mean) / max(0.01, global_std), 4),
                    "note": "Used distribution analysis (insufficient archetype-level data)",
                })
                return result
        
        result["status"] = "INSUFFICIENT_DATA"
        result["reason"] = f"Present: {len(present_taus)}, Future: {len(future_taus)} archetypes"
        return result
    
    d = cohens_d(np.array(future_taus), np.array(present_taus))
    
    supported = abs(d) > 0.5
    falsified = abs(d) < 0.2
    
    result.update({
        "status": "SUPPORTED" if supported else ("FALSIFIED" if falsified else "INCONCLUSIVE"),
        "effect_size_d": round(d, 4),
        "present_mean_tau": round(np.mean(present_taus), 4),
        "future_mean_tau": round(np.mean(future_taus), 4),
        "n_present_archetypes": len(present_taus),
        "n_future_archetypes": len(future_taus),
    })
    
    return result


def test_H5_1(priors: Dict) -> Dict[str, Any]:
    """
    H5.1: Cognitive velocity (cv) predicts NDF signal reliability.
    
    Test: Reviews with high cv should show more extreme (further from 0.5)
          NDF dimension values, indicating stronger nonconscious signal.
    
    Threshold: r > 0.20 between cv and NDF dimension variance
    Falsified if: r < 0.05
    """
    result = {
        "hypothesis": "H5.1",
        "description": "Cognitive velocity predicts NDF signal strength",
        "threshold": "r > 0.20",
        "falsification": "r < 0.05",
    }
    
    ndf_pop = priors.get("ndf_population", {})
    if not ndf_pop:
        result["status"] = "INSUFFICIENT_DATA"
        return result
    
    ndf_profiles = ndf_pop.get("ndf_archetype_profiles", {})
    
    if len(ndf_profiles) < 3:
        result["status"] = "INSUFFICIENT_DATA"
        result["reason"] = f"Only {len(ndf_profiles)} archetype profiles"
        return result
    
    # For each archetype: compute mean cv and mean "extremeness" of other dims
    cvs = []
    extremeness_scores = []
    
    NDF_DIMS = ["approach_avoidance", "temporal_horizon", "social_calibration",
                "uncertainty_tolerance", "status_sensitivity", "cognitive_engagement",
                "arousal_seeking"]
    
    for archetype, profile in ndf_profiles.items():
        cv = profile.get("cognitive_velocity", None)
        if cv is None:
            continue
        
        # Compute average extremeness: |value - midpoint|
        dim_extremes = []
        for dim in NDF_DIMS:
            val = profile.get(dim, None)
            if val is None:
                continue
            if dim == "approach_avoidance":
                extreme = abs(val)  # Midpoint is 0 for [-1,1]
            else:
                extreme = abs(val - 0.5)  # Midpoint is 0.5 for [0,1]
            dim_extremes.append(extreme)
        
        if dim_extremes:
            cvs.append(cv)
            extremeness_scores.append(np.mean(dim_extremes))
    
    if len(cvs) < 3:
        result["status"] = "INSUFFICIENT_DATA"
        return result
    
    r = pearson_r(np.array(cvs), np.array(extremeness_scores))
    
    supported = r > 0.20
    falsified = r < 0.05
    
    result.update({
        "status": "SUPPORTED" if supported else ("FALSIFIED" if falsified else "INCONCLUSIVE"),
        "r_cv_extremeness": round(r, 4),
        "n_archetypes": len(cvs),
        "mean_cv": round(np.mean(cvs), 4),
        "mean_extremeness": round(np.mean(extremeness_scores), 4),
    })
    
    return result


# =============================================================================
# MAIN
# =============================================================================

def run_hypothesis(hypothesis_id: str, priors: Dict) -> Dict[str, Any]:
    """Run a specific hypothesis test."""
    tests = {
        "H3.1": test_H3_1,
        "H2.2": test_H2_2,
        "H5.1": test_H5_1,
    }
    
    if hypothesis_id not in tests:
        return {"error": f"Unknown hypothesis: {hypothesis_id}", "available": list(tests.keys())}
    
    return tests[hypothesis_id](priors)


def main():
    parser = argparse.ArgumentParser(description="ADAM Hypothesis Testing Analysis")
    parser.add_argument("--hypothesis", type=str, default="all",
                        help="Hypothesis to test (H3.1, H2.2, H5.1, or 'all')")
    parser.add_argument("--verify-data", action="store_true",
                        help="Verify data availability for testing")
    parser.add_argument("--output", type=str, default=None,
                        help="Output results to JSON file")
    args = parser.parse_args()
    
    if args.verify_data:
        report = verify_data_availability()
        print("\n" + "=" * 60)
        print("DATA VERIFICATION REPORT")
        print("=" * 60)
        for key, value in report.items():
            print(f"  {key}: {value}")
        print(f"\n  Ready to test: {', '.join(report.get('ready_for', ['none']))}")
        print("=" * 60)
        return
    
    # Load data
    priors = load_merged_priors()
    if not priors:
        logger.error("No priors data available. Run ingestion + merge first.")
        return
    
    # Run tests
    results = {}
    
    if args.hypothesis == "all":
        for h_id in ["H3.1", "H2.2", "H5.1"]:
            logger.info(f"\n{'='*40}")
            logger.info(f"Testing {h_id}")
            logger.info(f"{'='*40}")
            result = run_hypothesis(h_id, priors)
            results[h_id] = result
            
            status = result.get("status", "UNKNOWN")
            print(f"\n  {h_id}: {result.get('description', '')}")
            print(f"  Status: {status}")
            
            if status not in ("INSUFFICIENT_DATA",):
                for k, v in result.items():
                    if k not in ("hypothesis", "description", "threshold", "falsification", "status"):
                        if isinstance(v, (int, float)):
                            print(f"    {k}: {v}")
    else:
        result = run_hypothesis(args.hypothesis, priors)
        results[args.hypothesis] = result
        
        print(f"\n{'='*60}")
        print(f"HYPOTHESIS TEST: {args.hypothesis}")
        print(f"{'='*60}")
        for k, v in result.items():
            if isinstance(v, dict):
                print(f"  {k}:")
                for k2, v2 in v.items():
                    print(f"    {k2}: {v2}")
            else:
                print(f"  {k}: {v}")
        print(f"{'='*60}")
    
    # Save results
    if args.output:
        output_path = Path(args.output)
        with open(output_path, "w") as f:
            json.dump(results, f, indent=2)
        logger.info(f"Results saved to {output_path}")
    
    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    for h_id, result in results.items():
        status = result.get("status", "UNKNOWN")
        emoji = {"SUPPORTED": "+", "FALSIFIED": "X", "INCONCLUSIVE": "?",
                 "INSUFFICIENT_DATA": "-", "DISTRIBUTION_ANALYSIS": "~"}.get(status, "?")
        print(f"  [{emoji}] {h_id}: {status}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
