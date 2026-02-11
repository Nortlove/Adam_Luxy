#!/usr/bin/env python3
"""
POPULATE NEO4J GRAPH — Create Base Nodes for GDS Algorithms

This script creates the foundational graph structure that GDS algorithms need:

1. CustomerArchetype nodes (from ingestion archetype distributions)
2. CognitiveMechanism nodes (all mechanisms used in ADAM)
3. RESPONDS_TO edges (archetype → mechanism effectiveness from 937M+ reviews)
4. MECHANISM_SYNERGY edges (mechanism co-occurrence patterns)
5. NDFProfile properties on archetypes (7 nonconscious decision dimensions)
6. Category nodes with archetype distribution properties

Without these nodes, the GDS algorithms (Node Similarity, Louvain, PageRank,
Betweenness Centrality) in adam/intelligence/graph/gds_runtime.py return empty.

Usage:
    python3 scripts/populate_neo4j_graph.py
    python3 scripts/populate_neo4j_graph.py --uri bolt://localhost:7687 --password YOUR_PASSWORD
    python3 scripts/populate_neo4j_graph.py --validate-only

Dependencies:
    pip install neo4j
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# ============================================================================
# PATHS
# ============================================================================

BASE_DIR = Path(__file__).resolve().parent.parent
MERGED_PRIORS_PATH = BASE_DIR / "data" / "learning" / "ingestion_merged_priors.json"


# ============================================================================
# ALL COGNITIVE MECHANISMS IN ADAM
# ============================================================================

COGNITIVE_MECHANISMS = {
    "social_proof": {
        "display_name": "Social Proof",
        "cialdini_principle": "Social Proof",
        "description": "Leverages the behavior of others to validate decisions",
        "academic_source": "Cialdini (2001)",
    },
    "scarcity": {
        "display_name": "Scarcity",
        "cialdini_principle": "Scarcity",
        "description": "Creates urgency through limited availability",
        "academic_source": "Cialdini (2001)",
    },
    "authority": {
        "display_name": "Authority",
        "cialdini_principle": "Authority",
        "description": "Leverages expert endorsement and credibility",
        "academic_source": "Cialdini (2001)",
    },
    "commitment": {
        "display_name": "Commitment & Consistency",
        "cialdini_principle": "Commitment/Consistency",
        "description": "Leverages desire to act consistently with prior actions",
        "academic_source": "Cialdini (2001)",
    },
    "reciprocity": {
        "display_name": "Reciprocity",
        "cialdini_principle": "Reciprocity",
        "description": "Triggers obligation through giving before asking",
        "academic_source": "Cialdini (2001)",
    },
    "liking": {
        "display_name": "Liking",
        "cialdini_principle": "Liking",
        "description": "Builds persuasion through affinity and relatability",
        "academic_source": "Cialdini (2001)",
    },
    "unity": {
        "display_name": "Unity",
        "cialdini_principle": "Unity",
        "description": "Creates shared identity and in-group belonging",
        "academic_source": "Cialdini (2016)",
    },
    "fomo": {
        "display_name": "Fear of Missing Out",
        "cialdini_principle": "Scarcity (variant)",
        "description": "Creates anxiety about missing opportunities",
        "academic_source": "Przybylski et al. (2013)",
    },
    "identity_construction": {
        "display_name": "Identity Construction",
        "cialdini_principle": "Unity (extended)",
        "description": "Helps consumers construct desired self-identity",
        "academic_source": "Belk (1988)",
    },
    "mimetic_desire": {
        "display_name": "Mimetic Desire",
        "cialdini_principle": "Social Proof (extended)",
        "description": "Desire mediated through observing others' desires",
        "academic_source": "Girard (1961)",
    },
    "attention_dynamics": {
        "display_name": "Attention Dynamics",
        "cialdini_principle": "N/A",
        "description": "Captures and sustains cognitive attention",
        "academic_source": "Kahneman (1973)",
    },
    "embodied_cognition": {
        "display_name": "Embodied Cognition",
        "cialdini_principle": "N/A",
        "description": "Leverages physical/sensory processing for persuasion",
        "academic_source": "Barsalou (2008)",
    },
    "storytelling": {
        "display_name": "Narrative Transport",
        "cialdini_principle": "N/A",
        "description": "Persuasion through narrative immersion",
        "academic_source": "Green & Brock (2000)",
    },
    "fear_appeal": {
        "display_name": "Fear Appeal",
        "cialdini_principle": "N/A",
        "description": "Motivates action through fear of negative outcomes",
        "academic_source": "Witte (1992)",
    },
    "humor": {
        "display_name": "Humor",
        "cialdini_principle": "Liking (variant)",
        "description": "Disarms resistance through entertainment",
        "academic_source": "Eisend (2009)",
    },
}


# ============================================================================
# GRAPH POPULATION FUNCTIONS
# ============================================================================

def load_merged_priors() -> Dict[str, Any]:
    """Load the merged ingestion priors."""
    if not MERGED_PRIORS_PATH.exists():
        logger.error(f"Merged priors not found at {MERGED_PRIORS_PATH}")
        logger.error("Run: python3 scripts/merge_ingestion_priors.py first")
        sys.exit(1)

    with open(MERGED_PRIORS_PATH) as f:
        priors = json.load(f)

    logger.info(
        f"Loaded merged priors: {priors['total_reviews_processed']:,} reviews, "
        f"{priors['amazon_categories']} Amazon categories, "
        f"{priors['multi_dataset_sources']} other datasets"
    )
    return priors


def create_constraints_and_indexes(session) -> int:
    """Create uniqueness constraints and indexes for optimal GDS performance."""
    constraints = [
        "CREATE CONSTRAINT IF NOT EXISTS FOR (a:CustomerArchetype) REQUIRE a.name IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (m:CognitiveMechanism) REQUIRE m.name IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (c:ProductCategory) REQUIRE c.name IS UNIQUE",
        "CREATE INDEX IF NOT EXISTS FOR (a:CustomerArchetype) ON (a.name)",
        "CREATE INDEX IF NOT EXISTS FOR (m:CognitiveMechanism) ON (m.name)",
        "CREATE INDEX IF NOT EXISTS FOR ()-[r:RESPONDS_TO]-() ON (r.effectiveness)",
        "CREATE INDEX IF NOT EXISTS FOR (c:ProductCategory) ON (c.name)",
    ]
    count = 0
    for cypher in constraints:
        try:
            session.run(cypher)
            count += 1
        except Exception as e:
            # Constraints may already exist
            logger.debug(f"Constraint/index note: {e}")
            count += 1
    return count


def create_archetype_nodes(session, priors: Dict) -> int:
    """
    Create CustomerArchetype nodes with NDF profiles and population proportions.

    Each node stores:
    - name: archetype identifier
    - proportion: global population proportion (from 937M+ reviews)
    - categories_seen: number of categories where this archetype appears
    - NDF dimensions: 7 nonconscious decision fingerprint values
    """
    global_dist = priors.get("global_archetype_distribution", {})
    ndf_by_archetype = priors.get("ndf_population", {}).get("ndf_by_archetype", {})

    if not global_dist:
        logger.warning("No archetype distribution data found")
        return 0

    # Build archetype data with NDF profiles
    archetype_data = []
    for archetype, proportion in global_dist.items():
        ndf = ndf_by_archetype.get(archetype, {})
        archetype_data.append({
            "name": archetype,
            "proportion": proportion,
            "approach_avoidance": ndf.get("approach_avoidance", 0.5),
            "temporal_horizon": ndf.get("temporal_horizon", 0.5),
            "social_calibration": ndf.get("social_calibration", 0.5),
            "uncertainty_tolerance": ndf.get("uncertainty_tolerance", 0.5),
            "status_sensitivity": ndf.get("status_sensitivity", 0.5),
            "cognitive_engagement": ndf.get("cognitive_engagement", 0.5),
            "arousal_seeking": ndf.get("arousal_seeking", 0.5),
        })

    result = session.run(
        """
        UNWIND $archetypes AS arch
        MERGE (a:CustomerArchetype {name: arch.name})
        SET a.proportion = arch.proportion,
            a.approach_avoidance = arch.approach_avoidance,
            a.temporal_horizon = arch.temporal_horizon,
            a.social_calibration = arch.social_calibration,
            a.uncertainty_tolerance = arch.uncertainty_tolerance,
            a.status_sensitivity = arch.status_sensitivity,
            a.cognitive_engagement = arch.cognitive_engagement,
            a.arousal_seeking = arch.arousal_seeking,
            a.source = 'ingestion_937M_reviews',
            a.updated_at = datetime()
        RETURN count(a) AS cnt
        """,
        archetypes=archetype_data,
    )

    record = result.single()
    count = record["cnt"] if record else 0
    logger.info(f"Created/updated {count} CustomerArchetype nodes")
    return count


def create_mechanism_nodes(session) -> int:
    """
    Create CognitiveMechanism nodes with metadata.

    Each node stores:
    - name: mechanism identifier
    - display_name: human-readable name
    - cialdini_principle: mapping to Cialdini framework
    - description: what this mechanism does
    - academic_source: academic citation
    """
    mechanism_data = [
        {
            "name": name,
            "display_name": meta["display_name"],
            "cialdini_principle": meta["cialdini_principle"],
            "description": meta["description"],
            "academic_source": meta["academic_source"],
        }
        for name, meta in COGNITIVE_MECHANISMS.items()
    ]

    result = session.run(
        """
        UNWIND $mechanisms AS mech
        MERGE (m:CognitiveMechanism {name: mech.name})
        SET m.display_name = mech.display_name,
            m.cialdini_principle = mech.cialdini_principle,
            m.description = mech.description,
            m.academic_source = mech.academic_source,
            m.updated_at = datetime()
        RETURN count(m) AS cnt
        """,
        mechanisms=mechanism_data,
    )

    record = result.single()
    count = record["cnt"] if record else 0
    logger.info(f"Created/updated {count} CognitiveMechanism nodes")
    return count


def create_responds_to_edges(session, priors: Dict) -> int:
    """
    Create RESPONDS_TO edges from the global effectiveness matrix.

    Each edge encodes: (CustomerArchetype)-[:RESPONDS_TO]->(CognitiveMechanism)
    with properties:
    - effectiveness: weighted success rate across all categories
    - sample_size: total observations supporting this edge
    - categories_seen: how many categories contributed to this estimate
    - confidence: statistical confidence (higher sample_size = higher confidence)
    """
    effectiveness = priors.get("global_effectiveness_matrix", {})
    if not effectiveness:
        logger.warning("No effectiveness matrix data found")
        return 0

    edges = []
    for archetype, mechanisms in effectiveness.items():
        for mechanism, stats in mechanisms.items():
            sr = stats.get("success_rate", 0.0)
            ss = stats.get("sample_size", 0)
            cats = stats.get("categories_seen", 0)

            # Compute confidence: Bayesian-inspired, scales with sample size
            # At 1000 samples, confidence ~0.9; at 100, ~0.5; at 10, ~0.1
            import math
            confidence = 1.0 - math.exp(-ss / 500.0) if ss > 0 else 0.0

            edges.append({
                "archetype": archetype,
                "mechanism": mechanism,
                "effectiveness": sr,
                "sample_size": ss,
                "categories_seen": cats,
                "confidence": round(confidence, 4),
            })

    # Batch create edges
    batch_size = 500
    total_created = 0

    for i in range(0, len(edges), batch_size):
        batch = edges[i:i + batch_size]
        result = session.run(
            """
            UNWIND $edges AS edge
            MATCH (a:CustomerArchetype {name: edge.archetype})
            MATCH (m:CognitiveMechanism {name: edge.mechanism})
            MERGE (a)-[r:RESPONDS_TO]->(m)
            SET r.effectiveness = edge.effectiveness,
                r.sample_size = edge.sample_size,
                r.categories_seen = edge.categories_seen,
                r.confidence = edge.confidence,
                r.source = 'ingestion_937M_reviews',
                r.updated_at = datetime()
            RETURN count(r) AS cnt
            """,
            edges=batch,
        )
        record = result.single()
        total_created += record["cnt"] if record else 0

    logger.info(f"Created/updated {total_created} RESPONDS_TO edges")
    return total_created


def create_mechanism_synergy_edges(session, priors: Dict) -> int:
    """
    Create MECHANISM_SYNERGY edges from mechanism co-occurrence in effectiveness data.

    Two mechanisms have synergy when they both have high effectiveness for the
    same archetype. The synergy score is the geometric mean of their effectiveness.
    """
    effectiveness = priors.get("global_effectiveness_matrix", {})
    if not effectiveness:
        return 0

    # Compute mechanism co-effectiveness per archetype
    synergies: Dict[tuple, Dict] = {}

    for archetype, mechanisms in effectiveness.items():
        mech_list = list(mechanisms.keys())
        for i in range(len(mech_list)):
            for j in range(i + 1, len(mech_list)):
                m1, m2 = mech_list[i], mech_list[j]
                eff1 = mechanisms[m1].get("success_rate", 0)
                eff2 = mechanisms[m2].get("success_rate", 0)

                if eff1 > 0.1 and eff2 > 0.1:
                    key = tuple(sorted([m1, m2]))
                    if key not in synergies:
                        synergies[key] = {
                            "co_occurrences": 0,
                            "combined_lifts": [],
                        }
                    synergies[key]["co_occurrences"] += 1
                    import math
                    synergies[key]["combined_lifts"].append(
                        math.sqrt(eff1 * eff2)
                    )

    # Create edges for pairs that co-occur in multiple archetypes
    edges = []
    for (m1, m2), stats in synergies.items():
        if stats["co_occurrences"] >= 3:  # Seen together in 3+ archetypes
            avg_lift = sum(stats["combined_lifts"]) / len(stats["combined_lifts"])
            edges.append({
                "mechanism1": m1,
                "mechanism2": m2,
                "synergy_score": round(avg_lift, 4),
                "co_occurrence_count": stats["co_occurrences"],
                "combined_lift": round(avg_lift, 4),
            })

    if not edges:
        return 0

    result = session.run(
        """
        UNWIND $edges AS edge
        MATCH (m1:CognitiveMechanism {name: edge.mechanism1})
        MATCH (m2:CognitiveMechanism {name: edge.mechanism2})
        MERGE (m1)-[r:MECHANISM_SYNERGY]->(m2)
        SET r.synergy_score = edge.synergy_score,
            r.co_occurrence_count = edge.co_occurrence_count,
            r.combined_lift = edge.combined_lift,
            r.source = 'ingestion_co_occurrence',
            r.updated_at = datetime()
        RETURN count(r) AS cnt
        """,
        edges=edges,
    )

    record = result.single()
    count = record["cnt"] if record else 0
    logger.info(f"Created/updated {count} MECHANISM_SYNERGY edges")
    return count


def create_category_nodes(session, priors: Dict) -> int:
    """Create ProductCategory nodes with archetype distribution properties."""
    cat_dists = priors.get("category_archetype_distributions", {})
    cat_profiles = priors.get("category_product_profiles", {})

    if not cat_dists:
        return 0

    categories = []
    for cat_name, dist in cat_dists.items():
        profile = cat_profiles.get(cat_name, {})
        # Get top 3 archetypes for this category
        top_archetypes = sorted(dist.items(), key=lambda x: -x[1])[:3]

        categories.append({
            "name": cat_name,
            "top_archetype_1": top_archetypes[0][0] if len(top_archetypes) > 0 else "",
            "top_archetype_1_pct": top_archetypes[0][1] if len(top_archetypes) > 0 else 0,
            "top_archetype_2": top_archetypes[1][0] if len(top_archetypes) > 1 else "",
            "top_archetype_2_pct": top_archetypes[1][1] if len(top_archetypes) > 1 else 0,
            "top_archetype_3": top_archetypes[2][0] if len(top_archetypes) > 2 else "",
            "top_archetype_3_pct": top_archetypes[2][1] if len(top_archetypes) > 2 else 0,
            "dominant_persuasion": profile.get("dominant_persuasion", ""),
            "dominant_emotion": profile.get("dominant_emotion", ""),
            "dominant_value": profile.get("dominant_value", ""),
            "num_archetypes": len(dist),
        })

    result = session.run(
        """
        UNWIND $categories AS cat
        MERGE (c:ProductCategory {name: cat.name})
        SET c.top_archetype_1 = cat.top_archetype_1,
            c.top_archetype_1_pct = cat.top_archetype_1_pct,
            c.top_archetype_2 = cat.top_archetype_2,
            c.top_archetype_2_pct = cat.top_archetype_2_pct,
            c.top_archetype_3 = cat.top_archetype_3,
            c.top_archetype_3_pct = cat.top_archetype_3_pct,
            c.dominant_persuasion = cat.dominant_persuasion,
            c.dominant_emotion = cat.dominant_emotion,
            c.dominant_value = cat.dominant_value,
            c.num_archetypes = cat.num_archetypes,
            c.updated_at = datetime()
        RETURN count(c) AS cnt
        """,
        categories=categories,
    )

    record = result.single()
    count = record["cnt"] if record else 0
    logger.info(f"Created/updated {count} ProductCategory nodes")
    return count


def create_category_archetype_edges(session, priors: Dict) -> int:
    """Create HAS_ARCHETYPE edges between categories and archetypes."""
    cat_dists = priors.get("category_archetype_distributions", {})
    if not cat_dists:
        return 0

    edges = []
    for cat_name, dist in cat_dists.items():
        for archetype, proportion in dist.items():
            if proportion > 0.01:  # Only meaningful proportions
                edges.append({
                    "category": cat_name,
                    "archetype": archetype,
                    "proportion": proportion,
                })

    batch_size = 500
    total = 0
    for i in range(0, len(edges), batch_size):
        batch = edges[i:i + batch_size]
        result = session.run(
            """
            UNWIND $edges AS edge
            MATCH (c:ProductCategory {name: edge.category})
            MATCH (a:CustomerArchetype {name: edge.archetype})
            MERGE (c)-[r:HAS_ARCHETYPE]->(a)
            SET r.proportion = edge.proportion,
                r.updated_at = datetime()
            RETURN count(r) AS cnt
            """,
            edges=batch,
        )
        record = result.single()
        total += record["cnt"] if record else 0

    logger.info(f"Created/updated {total} HAS_ARCHETYPE edges")
    return total


def validate_graph(session) -> Dict[str, Any]:
    """Validate the graph has the expected structure for GDS algorithms."""
    validations = {}

    # Count nodes
    for label in ["CustomerArchetype", "CognitiveMechanism", "ProductCategory"]:
        result = session.run(f"MATCH (n:{label}) RETURN count(n) AS cnt")
        record = result.single()
        validations[f"{label}_count"] = record["cnt"] if record else 0

    # Count edges
    for rel_type in ["RESPONDS_TO", "MECHANISM_SYNERGY", "HAS_ARCHETYPE"]:
        result = session.run(f"MATCH ()-[r:{rel_type}]->() RETURN count(r) AS cnt")
        record = result.single()
        validations[f"{rel_type}_count"] = record["cnt"] if record else 0

    # Check GDS availability
    try:
        result = session.run("RETURN gds.version() AS version")
        record = result.single()
        validations["gds_version"] = record["version"] if record else "not available"
        validations["gds_available"] = True
    except Exception:
        validations["gds_version"] = "not installed"
        validations["gds_available"] = False

    # Sample effectiveness edges
    result = session.run("""
        MATCH (a:CustomerArchetype)-[r:RESPONDS_TO]->(m:CognitiveMechanism)
        RETURN a.name AS archetype, m.name AS mechanism,
               r.effectiveness AS effectiveness, r.sample_size AS samples
        ORDER BY r.effectiveness DESC
        LIMIT 5
    """)
    validations["top_effectiveness"] = [dict(r) for r in result]

    return validations


# ============================================================================
# MAIN
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Populate Neo4j with base nodes for GDS algorithms"
    )
    parser.add_argument(
        "--uri", type=str, default="bolt://localhost:7687",
        help="Neo4j URI"
    )
    parser.add_argument("--username", type=str, default="neo4j", help="Neo4j username")
    parser.add_argument("--password", type=str, default="", help="Neo4j password")
    parser.add_argument(
        "--validate-only", action="store_true",
        help="Only validate existing graph, don't create nodes"
    )

    args = parser.parse_args()

    # Try to get password from environment or config
    password = args.password
    if not password:
        import os
        password = os.environ.get("NEO4J_PASSWORD", "")

    if not password:
        # Try loading from config
        try:
            sys.path.insert(0, str(BASE_DIR))
            from adam.config.settings import get_settings
            settings = get_settings()
            password = settings.neo4j_password
        except Exception:
            pass

    if not password:
        logger.warning(
            "No Neo4j password provided. Set NEO4J_PASSWORD env var, "
            "pass --password, or configure in adam/config/settings.py"
        )

    try:
        from neo4j import GraphDatabase
    except ImportError:
        logger.error("neo4j package not installed. Run: pip install neo4j")
        sys.exit(1)

    print("=" * 70)
    print("POPULATE NEO4J GRAPH — Base Nodes for GDS Algorithms")
    print("=" * 70)

    driver = GraphDatabase.driver(args.uri, auth=(args.username, password))

    try:
        # Verify connection
        with driver.session() as session:
            session.run("RETURN 1")
        logger.info(f"Connected to Neo4j at {args.uri}")
    except Exception as e:
        logger.error(f"Cannot connect to Neo4j: {e}")
        logger.info("Make sure Neo4j is running and credentials are correct")
        sys.exit(1)

    if args.validate_only:
        with driver.session() as session:
            validations = validate_graph(session)
        print("\n--- GRAPH VALIDATION ---")
        for key, val in validations.items():
            if key == "top_effectiveness":
                print(f"\nTop effectiveness edges:")
                for edge in val:
                    print(
                        f"  {edge['archetype']} → {edge['mechanism']}: "
                        f"{edge['effectiveness']:.4f} ({edge['samples']:,} samples)"
                    )
            else:
                print(f"  {key}: {val}")
        driver.close()
        return

    # Load priors
    priors = load_merged_priors()

    with driver.session() as session:
        # Step 1: Constraints and indexes
        print("\n--- Creating constraints and indexes ---")
        create_constraints_and_indexes(session)

        # Step 2: Create base nodes
        print("\n--- Creating CustomerArchetype nodes ---")
        n_archetypes = create_archetype_nodes(session, priors)

        print("\n--- Creating CognitiveMechanism nodes ---")
        n_mechanisms = create_mechanism_nodes(session)

        # Step 3: Create edges
        print("\n--- Creating RESPONDS_TO edges ---")
        n_responds_to = create_responds_to_edges(session, priors)

        print("\n--- Creating MECHANISM_SYNERGY edges ---")
        n_synergies = create_mechanism_synergy_edges(session, priors)

        # Step 4: Create category structure
        print("\n--- Creating ProductCategory nodes ---")
        n_categories = create_category_nodes(session, priors)

        print("\n--- Creating HAS_ARCHETYPE edges ---")
        n_cat_arch = create_category_archetype_edges(session, priors)

        # Step 5: Theory Graph (Inferential Intelligence)
        print("\n--- Populating Theory Graph (PsychologicalState, Need, Route, Context + edges) ---")
        try:
            from adam.intelligence.graph.theory_schema import populate_theory_graph
            theory_counts = populate_theory_graph(session)
            n_theory_nodes = sum(
                theory_counts.get(k, 0)
                for k in ["PsychologicalState", "PsychologicalNeed", "ProcessingRoute", "ContextCondition"]
            )
            n_theory_edges = sum(
                theory_counts.get(k, 0)
                for k in ["CREATES_NEED", "SATISFIED_BY", "ACTIVATES_ROUTE", "REQUIRES_QUALITY", "MODERATES"]
            )
        except Exception as e:
            logger.warning(f"Theory graph population failed (non-fatal): {e}")
            n_theory_nodes = 0
            n_theory_edges = 0
            theory_counts = {}

        # Step 6: Validate
        print("\n--- Validating graph ---")
        validations = validate_graph(session)

    driver.close()

    # Summary
    print("\n" + "=" * 70)
    print("GRAPH POPULATION COMPLETE")
    print("=" * 70)
    print(f"  CustomerArchetype nodes:  {n_archetypes}")
    print(f"  CognitiveMechanism nodes: {n_mechanisms}")
    print(f"  ProductCategory nodes:    {n_categories}")
    print(f"  RESPONDS_TO edges:        {n_responds_to}")
    print(f"  MECHANISM_SYNERGY edges:  {n_synergies}")
    print(f"  HAS_ARCHETYPE edges:      {n_cat_arch}")
    print(f"  Theory Graph nodes:       {n_theory_nodes}")
    print(f"  Theory Graph edges:       {n_theory_edges}")
    if theory_counts:
        for k, v in theory_counts.items():
            print(f"    {k}: {v}")
    print(f"  GDS available:            {validations.get('gds_available', False)}")
    print(f"  GDS version:              {validations.get('gds_version', 'N/A')}")

    if validations.get("top_effectiveness"):
        print("\n  Top effectiveness edges (sample):")
        for edge in validations["top_effectiveness"][:3]:
            print(
                f"    {edge['archetype']} → {edge['mechanism']}: "
                f"{edge['effectiveness']:.4f}"
            )

    print("\nGDS algorithms can now operate on real data.")
    print("Run: python3 scripts/populate_neo4j_graph.py --validate-only")
    print("to verify the graph at any time.")


if __name__ == "__main__":
    main()
