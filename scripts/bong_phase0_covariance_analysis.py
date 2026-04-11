#!/usr/bin/env python3
"""
BONG Phase 0: Population Covariance Quality Assessment

Before building Upgrade #1 (BONG multivariate Gaussian posteriors), we need
to answer: is the 20x20 population covariance matrix trustworthy enough to
propagate cross-dimension updates?

This script:
1. Pulls bilateral edges from Neo4j
2. Computes the population covariance matrix
3. Examines the eigenvalue spectrum (ill-conditioning check)
4. Tests cross-category stability (do correlations hold across verticals?)
5. Recommends: full covariance, diagonal+low-rank, or stay diagonal

If the covariance is ill-conditioned or unstable across categories,
BONG would propagate BAD cross-dimension updates — worse than independent
Betas that don't infect each other.

Usage:
    PYTHONPATH=. python3 scripts/bong_phase0_covariance_analysis.py
"""

import logging
import sys
import numpy as np

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger()

# The 20 bilateral edge dimensions
DIMENSIONS = [
    "regulatory_fit_score",
    "construal_fit_score",
    "personality_brand_alignment",
    "emotional_resonance",
    "value_alignment",
    "evolutionary_motive_match",
    "linguistic_style_matching",
    "spending_pain_match",
    "reactance_fit",
    "self_monitoring_fit",
    "processing_route_match",
    "mental_simulation_resonance",
    "optimal_distinctiveness_fit",
    "involvement_weight_modifier",
    "brand_trust_fit",
    "identity_signaling_match",
    "anchor_susceptibility_match",
    "lay_theory_alignment",
    "negativity_bias_match",
    "persuasion_confidence_multiplier",
]

QUERY = """
MATCH (pd:ProductDescription)-[bc:BRAND_CONVERTED]->(ar:AnnotatedReview)
WHERE ($category = '' OR pd.category_path STARTS WITH $category)
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
  bc.persuasion_confidence_multiplier AS persuasion_confidence_multiplier,
  pd.category_path AS category
LIMIT 100000
"""


def fetch_edges(driver, category=""):
    """Fetch bilateral edges from Neo4j."""
    with driver.session() as session:
        result = session.run(QUERY, category=category)
        rows = []
        for record in result:
            row = {}
            valid = True
            for dim in DIMENSIONS:
                val = record.get(dim)
                if val is None:
                    valid = False
                    break
                row[dim] = float(val)
            if valid:
                row["category"] = record.get("category", "")
                rows.append(row)
        return rows


def edges_to_matrix(edges):
    """Convert edge dicts to numpy matrix."""
    return np.array([[e[d] for d in DIMENSIONS] for e in edges])


def analyze_covariance(X, label="ALL"):
    """Full covariance analysis on a data matrix."""
    n, d = X.shape
    logger.info(f"\n{'='*60}")
    logger.info(f"  {label}: {n} edges x {d} dimensions")
    logger.info(f"{'='*60}")

    # Compute covariance
    cov = np.cov(X.T)
    corr = np.corrcoef(X.T)

    # Eigenvalue spectrum
    eigvals = np.linalg.eigvalsh(cov)
    eigvals_sorted = np.sort(eigvals)[::-1]

    logger.info(f"\n  EIGENVALUE SPECTRUM:")
    logger.info(f"  {'Rank':<6} {'Eigenvalue':<15} {'% Variance':<12} {'Cumulative %':<12}")
    total_var = eigvals_sorted.sum()
    cumulative = 0.0
    for i, ev in enumerate(eigvals_sorted):
        pct = 100.0 * ev / total_var if total_var > 0 else 0
        cumulative += pct
        marker = " ***" if ev < 1e-6 else (" *" if ev < 1e-4 else "")
        logger.info(f"  {i+1:<6} {ev:<15.6f} {pct:<12.2f} {cumulative:<12.2f}{marker}")

    # Condition number
    cond = eigvals_sorted[0] / max(eigvals_sorted[-1], 1e-15)
    logger.info(f"\n  CONDITION NUMBER: {cond:.1f}")
    if cond > 1e6:
        logger.info(f"  *** ILL-CONDITIONED — regularization required")
    elif cond > 1e3:
        logger.info(f"  ** MODERATE conditioning — diagonal+low-rank recommended")
    else:
        logger.info(f"  OK — full covariance usable")

    # Effective rank (number of eigenvalues above 1% of max)
    threshold = eigvals_sorted[0] * 0.01
    effective_rank = sum(1 for ev in eigvals_sorted if ev > threshold)
    logger.info(f"  EFFECTIVE RANK: {effective_rank}/{d} (eigenvalues > 1% of max)")

    # Strongest off-diagonal correlations
    logger.info(f"\n  TOP 10 OFF-DIAGONAL CORRELATIONS:")
    corr_pairs = []
    for i in range(d):
        for j in range(i+1, d):
            corr_pairs.append((abs(corr[i, j]), corr[i, j], DIMENSIONS[i], DIMENSIONS[j]))
    corr_pairs.sort(reverse=True)

    for abs_r, r, dim_a, dim_b in corr_pairs[:10]:
        strength = "STRONG" if abs_r > 0.5 else ("MODERATE" if abs_r > 0.3 else "WEAK")
        logger.info(f"  r={r:+.3f} ({strength}): {dim_a} x {dim_b}")

    # Near-zero correlations count
    weak_count = sum(1 for abs_r, _, _, _ in corr_pairs if abs_r < 0.1)
    moderate_count = sum(1 for abs_r, _, _, _ in corr_pairs if 0.1 <= abs_r < 0.3)
    strong_count = sum(1 for abs_r, _, _, _ in corr_pairs if abs_r >= 0.3)
    total_pairs = len(corr_pairs)
    logger.info(f"\n  CORRELATION DISTRIBUTION:")
    logger.info(f"  Strong (|r|>0.3): {strong_count}/{total_pairs} ({100*strong_count/total_pairs:.0f}%)")
    logger.info(f"  Moderate (0.1-0.3): {moderate_count}/{total_pairs} ({100*moderate_count/total_pairs:.0f}%)")
    logger.info(f"  Weak (|r|<0.1): {weak_count}/{total_pairs} ({100*weak_count/total_pairs:.0f}%)")

    return cov, corr, eigvals_sorted


def compare_across_categories(edge_data_by_category):
    """Check if correlations are stable across categories."""
    logger.info(f"\n{'='*60}")
    logger.info(f"  CROSS-CATEGORY STABILITY ANALYSIS")
    logger.info(f"{'='*60}")

    if len(edge_data_by_category) < 2:
        logger.info("  Need 2+ categories for stability analysis")
        return

    # Compute correlation matrix for each category
    corr_matrices = {}
    for cat, edges in edge_data_by_category.items():
        if len(edges) < 50:
            continue
        X = edges_to_matrix(edges)
        corr_matrices[cat] = np.corrcoef(X.T)

    if len(corr_matrices) < 2:
        logger.info("  Not enough categories with sufficient data")
        return

    # Compare each pair of categories
    categories = list(corr_matrices.keys())
    max_deviation = 0.0
    unstable_pairs = []

    for i in range(len(categories)):
        for j in range(i+1, len(categories)):
            cat_a, cat_b = categories[i], categories[j]
            diff = np.abs(corr_matrices[cat_a] - corr_matrices[cat_b])
            # Only look at off-diagonal
            np.fill_diagonal(diff, 0)
            max_diff = diff.max()
            mean_diff = diff[np.triu_indices_from(diff, k=1)].mean()

            logger.info(f"\n  {cat_a[:30]} vs {cat_b[:30]}:")
            logger.info(f"    Mean |correlation difference|: {mean_diff:.3f}")
            logger.info(f"    Max |correlation difference|: {max_diff:.3f}")

            if max_diff > max_deviation:
                max_deviation = max_diff

            # Find the most unstable dimension pairs
            for di in range(len(DIMENSIONS)):
                for dj in range(di+1, len(DIMENSIONS)):
                    d = abs(corr_matrices[cat_a][di, dj] - corr_matrices[cat_b][di, dj])
                    if d > 0.3:
                        unstable_pairs.append((d, DIMENSIONS[di], DIMENSIONS[dj], cat_a, cat_b))

    if unstable_pairs:
        unstable_pairs.sort(reverse=True)
        logger.info(f"\n  UNSTABLE CORRELATIONS (differ by >0.3 across categories):")
        for d, dim_a, dim_b, cat_a, cat_b in unstable_pairs[:10]:
            logger.info(f"    delta={d:.3f}: {dim_a} x {dim_b}")
            logger.info(f"      ({cat_a[:25]} vs {cat_b[:25]})")
    else:
        logger.info(f"\n  All correlations stable across categories (max delta={max_deviation:.3f})")

    return max_deviation, unstable_pairs


def recommend(cov, eigvals, max_deviation, unstable_count):
    """Final recommendation."""
    logger.info(f"\n{'='*60}")
    logger.info(f"  RECOMMENDATION")
    logger.info(f"{'='*60}")

    d = len(eigvals)
    cond = eigvals[0] / max(eigvals[-1], 1e-15)
    effective_rank = sum(1 for ev in eigvals if ev > eigvals[0] * 0.01)

    if cond > 1e6:
        logger.info(f"\n  MATRIX IS ILL-CONDITIONED (condition={cond:.0f})")
        logger.info(f"  --> Use diagonal + low-rank approximation")
        logger.info(f"      Keep top {effective_rank} eigencomponents, regularize rest")
        logger.info(f"      BONG with regularized covariance: safe")
        logger.info(f"      BONG with raw covariance: DANGEROUS (will propagate noise)")
        approach = "diagonal_plus_low_rank"
    elif max_deviation > 0.3:
        logger.info(f"\n  CORRELATIONS UNSTABLE ACROSS CATEGORIES (max delta={max_deviation:.3f})")
        logger.info(f"  --> Use diagonal + category-specific low-rank")
        logger.info(f"      {unstable_count} dimension pairs differ by >0.3 across categories")
        logger.info(f"      Shared diagonal + per-category off-diagonal corrections")
        approach = "diagonal_plus_category_rank"
    elif effective_rank < d * 0.7:
        logger.info(f"\n  LOW EFFECTIVE RANK ({effective_rank}/{d})")
        logger.info(f"  --> Use low-rank approximation (top {effective_rank} components)")
        logger.info(f"      Full covariance wastes capacity on noise dimensions")
        approach = "low_rank"
    else:
        logger.info(f"\n  COVARIANCE IS WELL-CONDITIONED AND STABLE")
        logger.info(f"  --> Full covariance safe for BONG")
        logger.info(f"      Condition={cond:.0f}, effective rank={effective_rank}/{d}")
        logger.info(f"      Cross-category max delta={max_deviation:.3f}")
        approach = "full_covariance"

    logger.info(f"\n  APPROACH: {approach}")
    return approach


def main():
    logger.info("=" * 70)
    logger.info("  BONG PHASE 0: Population Covariance Quality Assessment")
    logger.info("=" * 70)

    # Try to connect to Neo4j
    try:
        from neo4j import GraphDatabase
        driver = GraphDatabase.driver(
            "bolt://localhost:7687",
            auth=("neo4j", "atomofthought"),
        )
        driver.verify_connectivity()
        logger.info("\n  Connected to Neo4j")
    except Exception as e:
        logger.info(f"\n  Neo4j not available ({e})")
        logger.info("  Running with synthetic data to demonstrate the analysis...")
        driver = None

    if driver:
        # Fetch real edges
        logger.info("  Fetching bilateral edges...")
        all_edges = fetch_edges(driver, category="")
        logger.info(f"  Retrieved {len(all_edges)} valid edges")

        if len(all_edges) < 100:
            logger.info("  Insufficient edges for covariance analysis")
            driver.close()
            return

        # Full population analysis
        X_all = edges_to_matrix(all_edges)
        cov_all, corr_all, eigvals_all = analyze_covariance(X_all, "FULL POPULATION")

        # Per-category analysis
        categories = {}
        for edge in all_edges:
            cat = edge.get("category", "unknown")
            # Use top-level category
            top_cat = cat.split("/")[0] if cat else "unknown"
            categories.setdefault(top_cat, []).append(edge)

        # Filter to categories with enough data
        viable_cats = {k: v for k, v in categories.items() if len(v) >= 100}
        logger.info(f"\n  Categories with 100+ edges: {len(viable_cats)}")
        for cat, edges in sorted(viable_cats.items(), key=lambda x: -len(x[1]))[:5]:
            X_cat = edges_to_matrix(edges)
            analyze_covariance(X_cat, f"CATEGORY: {cat[:40]}")

        # Cross-category stability
        stability_result = compare_across_categories(viable_cats)
        if stability_result:
            max_dev, unstable = stability_result
        else:
            max_dev, unstable = 0.0, []
        unstable_count = len(unstable) if unstable else 0

        # Final recommendation
        recommend(cov_all, eigvals_all, max_dev or 0.0, unstable_count)

        driver.close()
    else:
        # Synthetic demonstration
        logger.info("\n  Generating synthetic bilateral edge data for analysis demo...")
        np.random.seed(42)

        # Simulate realistic correlation structure
        d = len(DIMENSIONS)
        # Create a covariance with known structure:
        # Block 1 (dims 0-4): trust/emotion cluster, correlated ~0.5
        # Block 2 (dims 5-9): cognitive/processing cluster, correlated ~0.3
        # Block 3 (dims 10-14): identity/social cluster, correlated ~0.4
        # Block 4 (dims 15-19): value/price cluster, anti-correlated with block 1
        true_cov = np.eye(d) * 0.1
        # Block correlations
        for i in range(5):
            for j in range(5):
                if i != j:
                    true_cov[i, j] = 0.05
        for i in range(5, 10):
            for j in range(5, 10):
                if i != j:
                    true_cov[i, j] = 0.03
        for i in range(10, 15):
            for j in range(10, 15):
                if i != j:
                    true_cov[i, j] = 0.04
        # Anti-correlation between blocks 1 and 4
        for i in range(5):
            for j in range(15, 20):
                true_cov[i, j] = -0.03
                true_cov[j, i] = -0.03

        # Ensure positive definite
        eigvals_check = np.linalg.eigvalsh(true_cov)
        if eigvals_check.min() < 0:
            true_cov += np.eye(d) * (abs(eigvals_check.min()) + 0.01)

        mean = np.random.uniform(0.2, 0.7, d)
        X_all = np.random.multivariate_normal(mean, true_cov, size=5000)

        cov_all, corr_all, eigvals_all = analyze_covariance(X_all, "SYNTHETIC POPULATION")

        # Simulate 2 categories with slightly different structure
        X_cat1 = np.random.multivariate_normal(mean, true_cov * 1.1, size=2000)
        X_cat2 = np.random.multivariate_normal(mean + 0.05, true_cov * 0.9, size=2000)

        corr1 = np.corrcoef(X_cat1.T)
        corr2 = np.corrcoef(X_cat2.T)
        diff = np.abs(corr1 - corr2)
        np.fill_diagonal(diff, 0)
        max_dev = diff.max()
        logger.info(f"\n  Cross-category max correlation difference: {max_dev:.3f}")

        recommend(cov_all, eigvals_all, max_dev, 0)

    logger.info("\n" + "=" * 70)
    logger.info("  Phase 0 complete. Use results to determine BONG initialization strategy.")
    logger.info("=" * 70)


if __name__ == "__main__":
    main()
