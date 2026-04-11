#!/usr/bin/env python3
"""
Export BONG Population Priors from Neo4j Bilateral Edges

Computes the regularized eigendecomposition of the population covariance
matrix and exports it for BONGUpdater initialization. Also computes
per-archetype mean vectors.

Output: data/bong_population_priors.npz (numpy archive)
  - eigenvectors: (d, k) top-k eigenvectors
  - eigenvalues: (k,) corresponding eigenvalues
  - population_mean: (d,) mean alignment vector
  - population_variances: (d,) per-dimension variances
  - dimension_names: list of dimension names
  - archetype_means: dict of archetype -> (d,) mean vectors
  - effective_rank: int
  - ridge: float (regularization applied)

Usage:
    PYTHONPATH=. python3 scripts/export_bong_priors.py
"""

import json
import logging
import os
import sys

import numpy as np

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger()

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
  ar.user_archetype AS archetype
LIMIT 200000
"""

EIGENVALUE_THRESHOLD_PCT = 0.01  # Keep eigenvalues > 1% of max
RIDGE = 1e-4  # Regularization for zero-eigenvalue dimensions
OUTPUT_DIR = "data"
OUTPUT_FILE = "bong_population_priors.npz"


def fetch_edges(driver):
    """Fetch bilateral edges with archetype labels."""
    with driver.session() as session:
        result = session.run(QUERY)
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
                row["archetype"] = record.get("archetype", "unknown") or "unknown"
                rows.append(row)
        return rows


def main():
    logger.info("=" * 60)
    logger.info("  BONG Prior Export: Bilateral Edge Eigendecomposition")
    logger.info("=" * 60)

    try:
        from neo4j import GraphDatabase
        driver = GraphDatabase.driver(
            "bolt://localhost:7687",
            auth=("neo4j", "atomofthought"),
        )
        driver.verify_connectivity()
        logger.info("\n  Connected to Neo4j")
    except Exception as e:
        logger.info(f"\n  Neo4j not available: {e}")
        logger.info("  Cannot export priors without live data.")
        sys.exit(1)

    # Fetch edges
    logger.info("  Fetching bilateral edges...")
    edges = fetch_edges(driver)
    logger.info(f"  Retrieved {len(edges)} valid edges")
    driver.close()

    if len(edges) < 500:
        logger.info("  Insufficient data for reliable covariance estimation")
        sys.exit(1)

    d = len(DIMENSIONS)

    # Build data matrix
    X = np.array([[e[dim] for dim in DIMENSIONS] for e in edges])
    n = X.shape[0]

    # Identify constant (zero-variance) dimensions
    col_std = X.std(axis=0)
    active_dims = col_std > 1e-8
    n_active = active_dims.sum()
    n_dead = d - n_active
    logger.info(f"\n  Dimensions: {d} total, {n_active} active, {n_dead} constant/dead")

    if n_dead > 0:
        dead_names = [DIMENSIONS[i] for i in range(d) if not active_dims[i]]
        logger.info(f"  Dead dimensions: {dead_names}")

    # Population mean and variance
    population_mean = X.mean(axis=0)
    population_variances = X.var(axis=0)

    # Regularize zero-variance dimensions
    population_variances = np.maximum(population_variances, RIDGE)

    # Compute covariance on active dimensions only, then embed back
    X_centered = X - population_mean
    cov_full = (X_centered.T @ X_centered) / (n - 1)

    # Regularize
    cov_full += np.eye(d) * RIDGE

    # Eigendecomposition
    eigenvalues, eigenvectors = np.linalg.eigh(cov_full)

    # Sort descending
    idx = np.argsort(eigenvalues)[::-1]
    eigenvalues = eigenvalues[idx]
    eigenvectors = eigenvectors[:, idx]

    # Determine effective rank
    threshold = eigenvalues[0] * EIGENVALUE_THRESHOLD_PCT
    effective_rank = int(np.sum(eigenvalues > threshold))
    logger.info(f"\n  Eigenvalue spectrum:")
    logger.info(f"  Max: {eigenvalues[0]:.6f}")
    logger.info(f"  Min (non-zero): {eigenvalues[eigenvalues > RIDGE].min():.6f}")
    logger.info(f"  Effective rank: {effective_rank}/{d}")
    logger.info(f"  Variance explained by top-{effective_rank}: "
                f"{100 * eigenvalues[:effective_rank].sum() / eigenvalues.sum():.1f}%")

    # Keep top-k eigenvectors
    k = effective_rank
    top_eigvecs = eigenvectors[:, :k]
    top_eigvals = eigenvalues[:k]

    logger.info(f"\n  Top {k} eigenvalues: {np.round(top_eigvals, 6).tolist()}")

    # Per-archetype means
    archetype_edges = {}
    for e in edges:
        arch = e["archetype"]
        archetype_edges.setdefault(arch, []).append(e)

    archetype_means = {}
    for arch, arch_edges in archetype_edges.items():
        if len(arch_edges) >= 20:
            X_arch = np.array([[e[dim] for dim in DIMENSIONS] for e in arch_edges])
            archetype_means[arch] = X_arch.mean(axis=0)
            logger.info(f"  Archetype '{arch}': {len(arch_edges)} edges, "
                        f"mean range [{X_arch.mean(axis=0).min():.3f}, {X_arch.mean(axis=0).max():.3f}]")

    # Export
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_path = os.path.join(OUTPUT_DIR, OUTPUT_FILE)

    np.savez(
        output_path,
        eigenvectors=top_eigvecs,
        eigenvalues=top_eigvals,
        population_mean=population_mean,
        population_variances=population_variances,
        dimension_names=np.array(DIMENSIONS),
        effective_rank=np.array([effective_rank]),
        ridge=np.array([RIDGE]),
        n_edges=np.array([n]),
    )

    # Save archetype means separately (np.savez doesn't handle dicts of arrays well)
    archetype_path = os.path.join(OUTPUT_DIR, "bong_archetype_means.npz")
    np.savez(archetype_path, **{k: v for k, v in archetype_means.items()})

    logger.info(f"\n  Exported to: {output_path}")
    logger.info(f"  Archetype means: {archetype_path}")
    logger.info(f"  Eigenvectors shape: {top_eigvecs.shape}")
    logger.info(f"  Eigenvalues shape: {top_eigvals.shape}")
    logger.info(f"  Population mean shape: {population_mean.shape}")
    logger.info(f"  Archetypes with means: {list(archetype_means.keys())}")

    # Verification: reconstruct and check condition number
    reconstructed_cov = top_eigvecs @ np.diag(top_eigvals) @ top_eigvecs.T + np.eye(d) * RIDGE
    cond = np.linalg.cond(reconstructed_cov)
    logger.info(f"\n  Reconstructed covariance condition number: {cond:.1f}")
    logger.info(f"  {'SAFE' if cond < 1e6 else 'WARNING: still ill-conditioned'}")

    logger.info(f"\n{'='*60}")
    logger.info(f"  Export complete. BONGUpdater can load from {output_path}")
    logger.info(f"{'='*60}")


if __name__ == "__main__":
    main()
