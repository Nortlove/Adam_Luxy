#!/usr/bin/env python3
"""
BONG Calibration Check + Dead Dimension Analysis

Sections 5/A.1 and 5/A.2 of the Unified System Evolution Directive.

1. Pull 200K bilateral edges from Neo4j
2. Hold out 20K, compute BONG prior from remaining 180K
3. Check if 90% of holdout falls inside 90% credible ellipsoid
4. Identify 6 dead dimensions and near-duplicate pairs
5. Output correction factor if miscalibrated

Usage:
    PYTHONPATH=. python3 scripts/run_calibration_check.py
"""

import logging
import sys
import numpy as np
from scipy.stats import chi2

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger()

DIMENSIONS = [
    "regulatory_fit_score", "construal_fit_score", "personality_brand_alignment",
    "emotional_resonance", "value_alignment", "evolutionary_motive_match",
    "linguistic_style_matching", "spending_pain_match", "reactance_fit",
    "self_monitoring_fit", "processing_route_match", "mental_simulation_resonance",
    "optimal_distinctiveness_fit", "involvement_weight_modifier", "brand_trust_fit",
    "identity_signaling_match", "anchor_susceptibility_match", "lay_theory_alignment",
    "negativity_bias_match", "persuasion_confidence_multiplier",
]

QUERY = """
MATCH (pd:ProductDescription)-[bc:BRAND_CONVERTED]->(ar:AnnotatedReview)
RETURN
  bc.regulatory_fit_score AS regulatory_fit_score,
  bc.construal_fit_score AS construal_fit_score,
  bc.personality_brand_alignment AS personality_brand_alignment,
  bc.emotional_resonance AS emotional_resonance,
  bc.value_alignment AS value_alignment,
  bc.evolutionary_motive_match AS evolutionary_motive_match,
  bc.linguistic_style_matching AS linguistic_style_matching,
  bc.spending_pain_match AS spending_pain_match,
  bc.reactance_fit AS reactance_fit,
  bc.self_monitoring_fit AS self_monitoring_fit,
  bc.processing_route_match AS processing_route_match,
  bc.mental_simulation_resonance AS mental_simulation_resonance,
  bc.optimal_distinctiveness_fit AS optimal_distinctiveness_fit,
  bc.involvement_weight_modifier AS involvement_weight_modifier,
  bc.brand_trust_fit AS brand_trust_fit,
  bc.identity_signaling_match AS identity_signaling_match,
  bc.anchor_susceptibility_match AS anchor_susceptibility_match,
  bc.lay_theory_alignment AS lay_theory_alignment,
  bc.negativity_bias_match AS negativity_bias_match,
  bc.persuasion_confidence_multiplier AS persuasion_confidence_multiplier
LIMIT 200000
"""

RIDGE = 1e-4


def fetch_edges(driver):
    with driver.session() as session:
        result = session.run(QUERY)
        rows = []
        for record in result:
            row = []
            valid = True
            for dim in DIMENSIONS:
                val = record.get(dim)
                if val is None:
                    valid = False
                    break
                row.append(float(val))
            if valid:
                rows.append(row)
        return np.array(rows)


def run_calibration(X, n_holdout=20000, credible_level=0.90):
    """Calibration check: does the 90% credible region contain 90% of holdout?"""
    n = X.shape[0]
    d = X.shape[1]

    indices = np.random.RandomState(42).permutation(n)
    holdout = X[indices[:n_holdout]]
    train = X[indices[n_holdout:]]

    logger.info(f"  Train: {len(train)}, Holdout: {len(holdout)}, Dims: {d}")

    train_mean = train.mean(axis=0)
    train_cov = np.cov(train, rowvar=False) + np.eye(d) * RIDGE

    # Identify active dimensions (non-zero variance)
    col_std = train.std(axis=0)
    active = col_std > 1e-8
    n_active = active.sum()
    logger.info(f"  Active dimensions: {n_active}/{d}")

    if n_active < d:
        dead_names = [DIMENSIONS[i] for i in range(d) if not active[i]]
        logger.info(f"  Dead dimensions: {dead_names}")
        # Work only on active subspace for Mahalanobis
        train_cov_active = train_cov[np.ix_(active, active)]
        train_mean_active = train_mean[active]
        holdout_active = holdout[:, active]
        d_eff = n_active
    else:
        train_cov_active = train_cov
        train_mean_active = train_mean
        holdout_active = holdout
        d_eff = d

    try:
        train_precision = np.linalg.inv(train_cov_active)
    except np.linalg.LinAlgError:
        logger.info("  SINGULAR covariance — adding stronger ridge")
        train_precision = np.linalg.inv(train_cov_active + np.eye(d_eff) * 0.01)

    # Mahalanobis distances
    deltas = holdout_active - train_mean_active
    mahal_sq = np.sum(deltas @ train_precision * deltas, axis=1)

    chi2_threshold = chi2.ppf(credible_level, df=d_eff)
    fraction_inside = np.mean(mahal_sq < chi2_threshold)
    median_mahal = np.median(mahal_sq)
    expected_median = chi2.ppf(0.5, df=d_eff)

    logger.info(f"\n  CALIBRATION RESULTS (credible level={credible_level}):")
    logger.info(f"  Expected fraction inside: {credible_level:.2f}")
    logger.info(f"  Actual fraction inside:   {fraction_inside:.4f}")
    logger.info(f"  Chi2 threshold (df={d_eff}): {chi2_threshold:.2f}")
    logger.info(f"  Median Mahalanobis²:      {median_mahal:.2f}")
    logger.info(f"  Expected median:          {expected_median:.2f}")

    # Determine calibration status
    if fraction_inside < credible_level - 0.05:
        target_quantile = np.percentile(mahal_sq, credible_level * 100)
        correction = target_quantile / chi2_threshold
        status = "OVERCONFIDENT"
        logger.info(f"\n  STATUS: {status}")
        logger.info(f"  Prior is TOO TIGHT. Multiply covariance by {correction:.3f}")
    elif fraction_inside > credible_level + 0.05:
        target_quantile = np.percentile(mahal_sq, credible_level * 100)
        correction = target_quantile / chi2_threshold
        status = "UNDERCONFIDENT"
        logger.info(f"\n  STATUS: {status}")
        logger.info(f"  Prior is TOO WIDE. Multiply covariance by {correction:.3f}")
    else:
        correction = 1.0
        status = "CALIBRATED"
        logger.info(f"\n  STATUS: {status}")
        logger.info(f"  No correction needed")

    return {
        "status": status,
        "fraction_inside": float(fraction_inside),
        "correction_factor": float(correction),
        "active_dimensions": int(n_active),
        "effective_df": int(d_eff),
    }


def run_dead_dimension_analysis(X):
    """Identify dead dimensions and near-duplicate pairs."""
    d = X.shape[1]
    cov = np.cov(X, rowvar=False) + np.eye(d) * RIDGE

    eigenvalues, eigenvectors = np.linalg.eigh(cov)
    idx = np.argsort(eigenvalues)[::-1]
    eigenvalues = eigenvalues[idx]
    eigenvectors = eigenvectors[:, idx]

    # Effective rank
    threshold = eigenvalues[0] * 0.01
    effective_rank = int(np.sum(eigenvalues > threshold))

    # Dead subspace loading per original dimension
    dead_eigvecs = eigenvectors[:, effective_rank:]
    dead_loading = np.sum(dead_eigvecs ** 2, axis=1)

    logger.info(f"\n{'='*60}")
    logger.info(f"  DEAD DIMENSION ANALYSIS")
    logger.info(f"{'='*60}")
    logger.info(f"\n  Effective rank: {effective_rank}/{d}")

    logger.info(f"\n  Per-dimension dead subspace fraction:")
    dim_report = []
    for i, name in enumerate(DIMENSIONS):
        var = cov[i, i]
        dead_frac = dead_loading[i]
        dim_report.append((name, dead_frac, var))

    dim_report.sort(key=lambda x: x[1], reverse=True)
    for name, dead_frac, var in dim_report:
        marker = " *** DEAD" if dead_frac > 0.5 else (" * HIGH" if dead_frac > 0.3 else "")
        logger.info(f"    {name:40s} dead_frac={dead_frac:.4f}  var={var:.6f}{marker}")

    # Near-duplicate pairs
    stds = np.sqrt(np.diag(cov))
    stds[stds == 0] = 1.0
    corr = cov / np.outer(stds, stds)

    logger.info(f"\n  Near-duplicate pairs (|r| > 0.85):")
    duplicates_found = False
    for i in range(d):
        for j in range(i + 1, d):
            if abs(corr[i, j]) > 0.85:
                logger.info(f"    r={corr[i,j]:+.3f}: {DIMENSIONS[i]} × {DIMENSIONS[j]}")
                duplicates_found = True
    if not duplicates_found:
        logger.info(f"    None found")

    # Strong correlations
    logger.info(f"\n  Strongest correlations (|r| > 0.3):")
    pairs = []
    for i in range(d):
        for j in range(i + 1, d):
            r = corr[i, j]
            if abs(r) > 0.3 and not np.isnan(r):
                pairs.append((abs(r), r, DIMENSIONS[i], DIMENSIONS[j]))
    pairs.sort(reverse=True)
    for _, r, a, b in pairs[:15]:
        logger.info(f"    r={r:+.3f}: {a} × {b}")

    dead_dims = [name for name, frac, _ in dim_report if frac > 0.5]
    logger.info(f"\n  DEAD DIMENSIONS (>50% in null subspace): {dead_dims}")
    logger.info(f"  These dimensions do not carry independent information.")
    logger.info(f"  Barrier diagnosis on these dimensions targets a proxy, not a real construct.")

    return {
        "effective_rank": effective_rank,
        "dead_dimensions": dead_dims,
        "dimension_report": dim_report,
        "eigenvalues": eigenvalues.tolist(),
    }


def apply_correction_to_bong(correction_factor):
    """Apply calibration correction to the installed BONG prior."""
    if abs(correction_factor - 1.0) < 0.01:
        logger.info("\n  No BONG correction needed (factor ≈ 1.0)")
        return

    try:
        from adam.intelligence.bong import get_bong_updater
        updater = get_bong_updater()
        if updater.prior_D is not None:
            # Scaling precision = inverse-scaling covariance
            # If overconfident (cov too small), correction > 1, so we divide D
            # If underconfident (cov too large), correction < 1, so we multiply D
            updater.prior_D = updater.prior_D / correction_factor
            updater.prior_eta = updater.prior_D * updater.population_mean
            logger.info(f"\n  Applied correction factor {correction_factor:.3f} to BONG prior")
            logger.info(f"  New precision range: [{updater.prior_D.min():.4f}, {updater.prior_D.max():.4f}]")
        else:
            logger.info("\n  BONG prior not initialized — correction skipped")
    except Exception as e:
        logger.info(f"\n  BONG correction failed: {e}")


def main():
    logger.info("=" * 70)
    logger.info("  BONG CALIBRATION CHECK + DEAD DIMENSION ANALYSIS")
    logger.info("  Unified System Evolution Directive, Sections 5/A.1 + 5/A.2")
    logger.info("=" * 70)

    try:
        from neo4j import GraphDatabase
        driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "atomofthought"))
        driver.verify_connectivity()
        logger.info("\n  Connected to Neo4j")
    except Exception as e:
        logger.info(f"\n  Neo4j not available: {e}")
        sys.exit(1)

    logger.info("  Fetching 200K bilateral edges...")
    X = fetch_edges(driver)
    driver.close()
    logger.info(f"  Retrieved {X.shape[0]} edges × {X.shape[1]} dimensions")

    if X.shape[0] < 1000:
        logger.info("  Insufficient data")
        sys.exit(1)

    # 1. Calibration check
    logger.info(f"\n{'='*60}")
    logger.info(f"  SECTION A.1: CALIBRATION CHECK")
    logger.info(f"{'='*60}")
    cal = run_calibration(X)

    # 2. Dead dimension analysis
    dead = run_dead_dimension_analysis(X)

    # 3. Apply correction if needed
    if cal["status"] != "CALIBRATED":
        logger.info(f"\n{'='*60}")
        logger.info(f"  APPLYING CALIBRATION CORRECTION")
        logger.info(f"{'='*60}")
        apply_correction_to_bong(cal["correction_factor"])

    # Summary
    logger.info(f"\n{'='*60}")
    logger.info(f"  SUMMARY")
    logger.info(f"{'='*60}")
    logger.info(f"  Calibration: {cal['status']} (correction={cal['correction_factor']:.3f})")
    logger.info(f"  Active dims: {cal['active_dimensions']}/20")
    logger.info(f"  Effective rank: {dead['effective_rank']}/20")
    logger.info(f"  Dead dimensions: {dead['dead_dimensions']}")
    logger.info(f"  Coverage: {cal['fraction_inside']:.1%} at 90% credible level")
    logger.info(f"{'='*60}")


if __name__ == "__main__":
    main()
