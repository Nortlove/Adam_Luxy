"""
Populate Neo4j with the ADAM Construct Taxonomy Graph Schema.

AUTHORITATIVE SOURCE: taxonomy/Construct_Taxonomy_v2_COMPLETE.md
                      taxonomy/ADAM_Corpus_Architecture_Addendum_Dual_Annotation.md

Creates:
  - Construct nodes (all 35 domains, 441+ constructs)
  - PREDICTS edges with Bayesian parameters
  - MODULATES edges from the cross-domain dependency map
  - Node types for the three-edge-type schema (ProductDescription, Review, ProductEcosystem)
  - Three edge types: BRAND_CONVERTED, PEER_INFLUENCED, ECOSYSTEM_CONVERTED
  - Indexes and constraints

Usage:
    python scripts/populate_construct_graph.py --uri bolt://localhost:7687 --username neo4j --password PASSWORD
    python scripts/populate_construct_graph.py --dry-run  # Print Cypher without executing
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from adam.intelligence.construct_taxonomy import (
    ALL_DOMAINS,
    CROSS_DOMAIN_DEPENDENCIES,
    TEMPORAL_STABILITY_CONFIG,
    Construct,
    Domain,
    InferenceTier,
    ScoringSwitch,
    TemporalStability,
    get_all_constructs,
    get_taxonomy_summary,
    validate_construct_id_uniqueness,
)


# =============================================================================
# CYPHER GENERATION
# =============================================================================

def generate_constraints_and_indexes() -> list[str]:
    """Generate Cypher statements for constraints and indexes."""
    return [
        # Uniqueness constraints
        "CREATE CONSTRAINT construct_id_unique IF NOT EXISTS FOR (c:Construct) REQUIRE c.id IS UNIQUE",
        "CREATE CONSTRAINT domain_id_unique IF NOT EXISTS FOR (d:Domain) REQUIRE d.domain_id IS UNIQUE",
        "CREATE CONSTRAINT product_desc_asin_unique IF NOT EXISTS FOR (pd:ProductDescription) REQUIRE pd.asin IS UNIQUE",
        "CREATE CONSTRAINT review_id_unique IF NOT EXISTS FOR (r:Review) REQUIRE r.review_id IS UNIQUE",
        "CREATE CONSTRAINT ecosystem_asin_unique IF NOT EXISTS FOR (eco:ProductEcosystem) REQUIRE eco.asin IS UNIQUE",

        # Indexes for fast lookup
        "CREATE INDEX construct_domain IF NOT EXISTS FOR (c:Construct) ON (c.domain_id)",
        "CREATE INDEX construct_side IF NOT EXISTS FOR (c:Construct) ON (c.scoring_side)",
        "CREATE INDEX construct_tier IF NOT EXISTS FOR (c:Construct) ON (c.tier)",
        "CREATE INDEX construct_stability IF NOT EXISTS FOR (c:Construct) ON (c.temporal_stability)",
        "CREATE INDEX review_asin IF NOT EXISTS FOR (r:Review) ON (r.asin)",
        "CREATE INDEX review_helpful IF NOT EXISTS FOR (r:Review) ON (r.helpful_votes)",
    ]


def generate_domain_node(domain: Domain) -> str:
    """Generate Cypher MERGE for a Domain node."""
    return (
        f"MERGE (d:Domain {{domain_id: '{domain.domain_id}'}}) "
        f"SET d.domain_name = '{domain.domain_name}', "
        f"d.scoring_side = '{domain.scoring_side.value}', "
        f"d.construct_count = {domain.construct_count}, "
        f"d.purpose = '{_escape(domain.purpose)}', "
        f"d.primary_research = '{_escape(domain.primary_research)}'"
    )


def generate_construct_node(construct: Construct) -> str:
    """Generate Cypher MERGE for a Construct node."""
    stability_config = TEMPORAL_STABILITY_CONFIG.get(construct.temporal_stability, {})
    bayesian_alpha = stability_config.get("bayesian_alpha_base", 5.0)
    learning_rate = stability_config.get("update_learning_rate", 0.05)
    min_obs = stability_config.get("min_observations_for_update", 10)
    decay = stability_config.get("decay_rate", 0.001)

    return (
        f"MERGE (c:Construct {{id: '{construct.id}'}}) "
        f"SET c.name = '{_escape(construct.name)}', "
        f"c.domain_id = '{construct.domain_id}', "
        f"c.description = '{_escape(construct.description[:500])}', "
        f"c.scoring_side = '{construct.scoring_side.value}', "
        f"c.tier = '{construct.tier.value}', "
        f"c.temporal_stability = '{construct.temporal_stability.value}', "
        f"c.inference_tractability = '{construct.inference_tractability.value}', "
        f"c.range_min = {construct.range_min}, "
        f"c.range_max = {construct.range_max}, "
        f"c.prior_distribution = '{construct.prior.distribution}', "
        f"c.prior_alpha = {construct.prior.alpha}, "
        f"c.prior_beta = {construct.prior.beta}, "
        f"c.population_prior_only = {str(construct.population_prior_only).lower()}, "
        f"c.bayesian_alpha_base = {bayesian_alpha}, "
        f"c.update_learning_rate = {learning_rate}, "
        f"c.min_observations = {min_obs}, "
        f"c.decay_rate = {decay}, "
        f"c.ethical_note = '{_escape(construct.ethical_note)}', "
        f"c.state_modulation = {str(construct.state_modulation).lower()}"
    )


def generate_belongs_to_edges() -> list[str]:
    """Generate BELONGS_TO edges from Construct to Domain."""
    stmts = []
    for domain in ALL_DOMAINS.values():
        for cid in domain.constructs:
            stmts.append(
                f"MATCH (c:Construct {{id: '{cid}'}}), (d:Domain {{domain_id: '{domain.domain_id}'}}) "
                f"MERGE (c)-[:BELONGS_TO]->(d)"
            )
    return stmts


def generate_modulates_edges() -> list[str]:
    """Generate MODULATES edges from the cross-domain dependency map."""
    stmts = []
    for modulation_type, source_map in CROSS_DOMAIN_DEPENDENCIES.items():
        for source_id, target_ids in source_map.items():
            for target_id in target_ids:
                stmts.append(
                    f"MATCH (s:Construct {{id: '{source_id}'}}), (t:Construct {{id: '{target_id}'}}) "
                    f"MERGE (s)-[:MODULATES {{modulation_type: '{modulation_type}'}}]->(t)"
                )
    return stmts


def generate_predicts_edge_template() -> str:
    """Generate the template for PREDICTS edges (populated during corpus ingestion)."""
    return """
// PREDICTS edge template — created during Phase 2 (alignment decomposition) and Phase 6 (corpus)
// Each PREDICTS edge connects a user-side construct to an ad-side construct
// with Bayesian parameters that update from campaign data.
//
// CREATE (user_c:Construct {id: $user_construct_id})-[:PREDICTS {
//     prior_mean: $effect_size,
//     prior_variance: $uncertainty,
//     posterior_mean: $effect_size,  // starts equal to prior
//     posterior_variance: $uncertainty,
//     n_observations: 0,
//     effect_direction: $direction,  // +1 or -1
//     research_source: $citation,
//     boundary_conditions: $conditions,
//     credible_interval_lower: $ci_low,
//     credible_interval_upper: $ci_high
// }]->(ad_c:Construct {id: $ad_construct_id})
"""


def generate_three_edge_type_schema() -> list[str]:
    """Generate schema support for the three edge types from the Addendum."""
    return [
        # Node types for the three-edge architecture
        "// ProductDescription node — one per ASIN, holds ad-side annotations (Domains 29-33)",
        "// Review node — one per review, holds user-side annotations (Domains 1-22)",
        "//   AND peer-ad-side annotations (Domains 29-33 + Domain 34) as separate properties",
        "// ProductEcosystem node — one per ASIN, holds ecosystem annotations (Domain 35)",
        "",
        "// Edge Type 1: BRAND_CONVERTED",
        "// (pd:ProductDescription)-[:BRAND_CONVERTED {regulatory_fit, construal_fit, personality_alignment,",
        "//   evolutionary_motive_match, outcome, star_rating, annotation_tier}]->(r:Review)",
        "",
        "// Edge Type 2: PEER_INFLUENCED",
        "// (pr:Review)-[:PEER_INFLUENCED {influence_weight, peer_authenticity_match, risk_resolution_match,",
        "//   narrative_resonance, outcome, star_rating}]->(r:Review)",
        "",
        "// Edge Type 3: ECOSYSTEM_CONVERTED",
        "// (eco:ProductEcosystem)-[:ECOSYSTEM_CONVERTED {frame_coherence_at_time, risk_coverage_at_time,",
        "//   sp_density_at_time, cialdini_coverage_at_time, outcome, star_rating}]->(r:Review)",
    ]


def _escape(s: str) -> str:
    """Escape single quotes for Cypher strings."""
    if not s:
        return ""
    return s.replace("\\", "\\\\").replace("'", "\\'").replace("\n", " ")


# =============================================================================
# EXECUTION
# =============================================================================

def generate_all_cypher() -> list[str]:
    """Generate all Cypher statements for the full schema."""
    stmts: list[str] = []

    # 1. Constraints and indexes
    stmts.extend(generate_constraints_and_indexes())

    # 2. Domain nodes
    for domain in ALL_DOMAINS.values():
        stmts.append(generate_domain_node(domain))

    # 3. Construct nodes
    all_constructs = get_all_constructs()
    for construct in all_constructs.values():
        stmts.append(generate_construct_node(construct))

    # 4. BELONGS_TO edges
    stmts.extend(generate_belongs_to_edges())

    # 5. MODULATES edges
    stmts.extend(generate_modulates_edges())

    return stmts


def run_dry(stmts: list[str]) -> None:
    """Print all Cypher statements without executing."""
    print(f"// ADAM Construct Taxonomy Graph Schema")
    print(f"// Total statements: {len(stmts)}")
    print(f"// Taxonomy summary:")
    summary = get_taxonomy_summary()
    for k, v in summary.items():
        print(f"//   {k}: {v}")
    print()
    for i, stmt in enumerate(stmts, 1):
        print(f"// [{i}/{len(stmts)}]")
        print(f"{stmt};")
        print()


def run_neo4j(uri: str, username: str, password: str, stmts: list[str]) -> None:
    """Execute all Cypher statements against Neo4j."""
    try:
        from neo4j import GraphDatabase
    except ImportError:
        print("ERROR: neo4j package not installed. Run: pip install neo4j")
        sys.exit(1)

    # Pre-flight: validate construct ID uniqueness
    duplicates = validate_construct_id_uniqueness()
    if duplicates:
        print(f"ERROR: Duplicate construct IDs found: {duplicates}")
        sys.exit(1)

    driver = GraphDatabase.driver(uri, auth=(username, password))
    print(f"Connected to Neo4j at {uri}")
    print(f"Executing {len(stmts)} statements...")

    with driver.session() as session:
        for i, stmt in enumerate(stmts, 1):
            if stmt.startswith("//"):
                continue  # Skip comments
            try:
                session.run(stmt)
                if i % 50 == 0:
                    print(f"  [{i}/{len(stmts)}] completed...")
            except Exception as e:
                print(f"  ERROR at statement {i}: {e}")
                print(f"  Statement: {stmt[:200]}...")

    driver.close()

    summary = get_taxonomy_summary()
    print(f"\nSchema population complete!")
    print(f"  Domains: {summary['total_domains']}")
    print(f"  Constructs: {summary['total_constructs']}")
    print(f"  Edge tier: {summary['edge_tier']}")
    print(f"  Reasoning tier: {summary['reasoning_tier']}")
    print(f"  Ethical constraints: {summary['with_ethical_notes']}")
    print(f"  Duplicates: {summary['duplicates']}")


def main():
    parser = argparse.ArgumentParser(description="Populate Neo4j with ADAM construct taxonomy")
    parser.add_argument("--uri", default="bolt://localhost:7687", help="Neo4j URI")
    parser.add_argument("--username", default="neo4j", help="Neo4j username")
    parser.add_argument("--password", default="", help="Neo4j password")
    parser.add_argument("--dry-run", action="store_true", help="Print Cypher without executing")
    parser.add_argument("--clear", action="store_true", help="Clear existing construct/domain nodes first")
    args = parser.parse_args()

    stmts = generate_all_cypher()

    if args.clear:
        clear_stmts = [
            "MATCH (c:Construct) DETACH DELETE c",
            "MATCH (d:Domain) DETACH DELETE d",
        ]
        stmts = clear_stmts + stmts

    if args.dry_run:
        run_dry(stmts)
    else:
        if not args.password:
            print("ERROR: --password required when not using --dry-run")
            sys.exit(1)
        run_neo4j(args.uri, args.username, args.password, stmts)


if __name__ == "__main__":
    main()
