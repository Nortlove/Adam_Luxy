"""
Validate the ADAM Construct Architecture.

Runs comprehensive checks:
1. Construct ID uniqueness across all 35 domains
2. Prior distribution sanity checks
3. Cross-domain dependency cycle detection
4. Edge-level latency benchmarks
5. Domain-to-atom mapping completeness
6. Three edge type support validation
7. Bayesian update convergence test
8. NDF backward compatibility check
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def main():
    errors: list[str] = []
    warnings: list[str] = []
    checks_passed = 0

    print("=" * 70)
    print("ADAM Construct Architecture Validation")
    print("=" * 70)

    # =========================================================================
    # CHECK 1: Construct ID Uniqueness
    # =========================================================================
    print("\n[1/8] Construct ID Uniqueness...")
    from adam.intelligence.construct_taxonomy import (
        validate_construct_id_uniqueness, get_all_constructs, get_taxonomy_summary,
        ALL_DOMAINS, TEMPORAL_STABILITY_CONFIG, CROSS_DOMAIN_DEPENDENCIES,
        InferenceTier, ScoringSwitch, TemporalStability,
    )
    duplicates = validate_construct_id_uniqueness()
    if duplicates:
        errors.append(f"Duplicate construct IDs: {duplicates}")
    else:
        print("  PASS: All construct IDs unique")
        checks_passed += 1

    # =========================================================================
    # CHECK 2: Prior Distribution Sanity
    # =========================================================================
    print("\n[2/8] Prior Distribution Sanity...")
    all_constructs = get_all_constructs()
    prior_issues: list[str] = []
    for cid, c in all_constructs.items():
        if c.prior.alpha <= 0 or c.prior.beta <= 0:
            prior_issues.append(f"{cid}: alpha={c.prior.alpha}, beta={c.prior.beta}")
        if c.prior.alpha > 100 or c.prior.beta > 100:
            prior_issues.append(f"{cid}: extreme prior alpha={c.prior.alpha}, beta={c.prior.beta}")
        # Check range consistency
        if c.range_min >= c.range_max:
            prior_issues.append(f"{cid}: invalid range [{c.range_min}, {c.range_max}]")
    if prior_issues:
        for issue in prior_issues:
            errors.append(f"Prior issue: {issue}")
    else:
        print("  PASS: All prior distributions valid")
        checks_passed += 1

    # =========================================================================
    # CHECK 3: Cross-Domain Dependency Cycle Detection
    # =========================================================================
    print("\n[3/8] Cross-Domain Dependency Cycles...")
    from adam.atoms.orchestration.construct_dag import ConstructDAG
    dag = ConstructDAG.build()
    cycles = dag.detect_cycles()
    if cycles:
        errors.append(f"Cycles in cross-domain DAG: {cycles}")
    else:
        print(f"  PASS: No cycles in {len(dag.nodes)}-node, {len(dag.edges)}-edge DAG")
        checks_passed += 1

    # =========================================================================
    # CHECK 4: Edge-Level Latency Benchmarks
    # =========================================================================
    print("\n[4/8] Edge-Level Latency Benchmarks...")
    from adam.intelligence.graph_construct_service import GraphConstructService, ConstructVector
    from adam.intelligence.construct_taxonomy import EdgeType

    svc = GraphConstructService()  # No Neo4j — tests prior-based path

    # Benchmark: user vector generation (should be <10ms for edge tier)
    start = time.monotonic()
    for _ in range(100):
        user_vec = svc.get_user_edge_vector("bench_user")
    edge_latency_ms = (time.monotonic() - start) * 1000 / 100

    # Benchmark: alignment computation
    brand_vec = svc.get_ad_vector("B00BENCH", EdgeType.BRAND_CONVERTED)
    start = time.monotonic()
    for _ in range(100):
        alignment = svc.compute_alignment(user_vec, brand_vec)
    align_latency_ms = (time.monotonic() - start) * 1000 / 100

    print(f"  User edge vector: {edge_latency_ms:.2f}ms (budget: 10ms)")
    print(f"  Alignment computation: {align_latency_ms:.2f}ms")
    if edge_latency_ms > 10:
        warnings.append(f"Edge vector latency {edge_latency_ms:.2f}ms exceeds 10ms budget")
    else:
        checks_passed += 1

    # =========================================================================
    # CHECK 5: Domain-to-Atom Mapping Completeness
    # =========================================================================
    print("\n[5/8] Domain-to-Atom Mapping Completeness...")
    from adam.atoms.orchestration.construct_dag import DOMAIN_ATOM_MAPPING
    taxonomy_domains = set(ALL_DOMAINS.keys())
    mapped_domains = set(DOMAIN_ATOM_MAPPING.keys())
    unmapped = taxonomy_domains - mapped_domains
    if unmapped:
        errors.append(f"Unmapped domains: {unmapped}")
    else:
        print(f"  PASS: All {len(taxonomy_domains)} domains mapped to atoms")
        checks_passed += 1

    # =========================================================================
    # CHECK 6: Three Edge Type Support
    # =========================================================================
    print("\n[6/8] Three Edge Type Support...")
    from adam.intelligence.bayesian_fusion import (
        BayesianFusionEngine, CampaignOutcome, OutcomeType, EdgeType as BEdgeType
    )
    engine = BayesianFusionEngine()
    outcome = CampaignOutcome(
        campaign_id="validation",
        user_id="val_user",
        outcome_type=OutcomeType.CONVERSION,
        outcome_value=1.0,
        user_construct_scores={"ci_social_proof": 0.8},
        ad_construct_scores={"pt_social_proof": 0.9},
        peer_construct_scores={"peer_authenticity": 0.7},
        ecosystem_construct_scores={"eco_sp_density": 0.6},
        edge_types=[BEdgeType.BRAND_CONVERTED, BEdgeType.PEER_INFLUENCED, BEdgeType.ECOSYSTEM_CONVERTED],
    )
    results = engine.process_outcome(outcome)
    edge_types_updated = set(r.edge_type for r in results)
    expected = {BEdgeType.BRAND_CONVERTED, BEdgeType.PEER_INFLUENCED, BEdgeType.ECOSYSTEM_CONVERTED}
    if edge_types_updated == expected:
        print(f"  PASS: All 3 edge types updated ({len(results)} edges)")
        checks_passed += 1
    else:
        errors.append(f"Missing edge types: {expected - edge_types_updated}")

    # =========================================================================
    # CHECK 7: Bayesian Update Convergence
    # =========================================================================
    print("\n[7/8] Bayesian Update Convergence Test...")
    engine2 = BayesianFusionEngine()
    # Simulate 100 positive outcomes for same pair
    for i in range(100):
        engine2.process_outcome(CampaignOutcome(
            campaign_id=f"conv_{i}",
            user_id="conv_user",
            outcome_type=OutcomeType.CONVERSION,
            outcome_value=1.0,
            user_construct_scores={"ci_social_proof": 0.8},
            ad_construct_scores={"pt_social_proof": 0.9},
            edge_types=[BEdgeType.BRAND_CONVERTED],
        ))
    state = engine2.get_posterior("ci_social_proof", "pt_social_proof", BEdgeType.BRAND_CONVERTED)
    if state.posterior_mean > state.prior_mean:
        print(f"  PASS: Posterior ({state.posterior_mean:.4f}) > Prior ({state.prior_mean:.4f}) after 100 positive outcomes")
        print(f"  Evidence strength: {state.evidence_strength}, n={state.n_observations}")
        checks_passed += 1
    else:
        errors.append(f"Posterior did not increase: prior={state.prior_mean:.4f}, posterior={state.posterior_mean:.4f}")

    # =========================================================================
    # CHECK 8: NDF Backward Compatibility
    # =========================================================================
    print("\n[8/8] NDF Backward Compatibility...")
    ctx = svc.to_atom_context("test_user")
    ndf_keys = set(ctx.get("ndf_intelligence", {}).get("profile", {}).keys())
    expected_ndf = {
        "uncertainty_tolerance", "cognitive_engagement", "approach_avoidance",
        "social_calibration", "arousal_seeking", "status_sensitivity",
        "temporal_horizon", "cognitive_velocity",
    }
    if expected_ndf.issubset(ndf_keys):
        print(f"  PASS: All {len(expected_ndf)} NDF dimensions present in backward-compatible context")
        checks_passed += 1
    else:
        missing_ndf = expected_ndf - ndf_keys
        errors.append(f"Missing NDF dimensions: {missing_ndf}")

    # =========================================================================
    # SUMMARY
    # =========================================================================
    summary = get_taxonomy_summary()

    print("\n" + "=" * 70)
    print("TAXONOMY SUMMARY")
    print("=" * 70)
    print(f"  Total domains: {summary['total_domains']}")
    print(f"  Total constructs: {summary['total_constructs']}")
    print(f"  Customer-side: {summary['customer_side']}")
    print(f"  Shared: {summary['shared']}")
    print(f"  Ad-side: {summary['ad_side']}")
    print(f"  Ecosystem: {summary['ecosystem']}")
    print(f"  Edge tier: {summary['edge_tier']}")
    print(f"  Reasoning tier: {summary['reasoning_tier']}")
    print(f"  Temporal stability: {summary['by_stability']}")
    print(f"  Ethical constraints: {summary['with_ethical_notes']}")

    print("\n" + "=" * 70)
    print("VALIDATION RESULTS")
    print("=" * 70)
    print(f"  Checks passed: {checks_passed}/8")
    print(f"  Errors: {len(errors)}")
    print(f"  Warnings: {len(warnings)}")

    if errors:
        print("\n  ERRORS:")
        for e in errors:
            print(f"    - {e}")
    if warnings:
        print("\n  WARNINGS:")
        for w in warnings:
            print(f"    - {w}")

    if not errors:
        print("\n  ** ALL VALIDATION CHECKS PASSED **")

    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
