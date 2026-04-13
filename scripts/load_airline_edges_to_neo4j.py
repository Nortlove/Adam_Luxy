#!/usr/bin/env python3
"""
Load premium airline bilateral edges into Neo4j.

Computes edges from the 11,805 filtered premium-airline satisfied travelers,
tags them as category='airline_premium', and loads into Neo4j alongside
existing LUXY Ride edges.

Also updates archetype priors with the new interaction-effect archetypes
validated from cross-category analysis.

Usage:
    source .env && python3 scripts/load_airline_edges_to_neo4j.py
"""

import json
import logging
import os
import sys
import time
from collections import Counter
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent
ANNOTATIONS_FILE = PROJECT_ROOT / "reviews_other" / "airline_reviews" / "airline_annotations_all.json"
AD_SIDE_FILE = PROJECT_ROOT / "reviews" / "luxury_ad_side_annotated.json"

# Premium airlines
PREMIUM_AIRLINES = {
    "Qatar Airways", "Emirates", "Singapore Airlines", "Cathay Pacific Airways",
    "ANA All Nippon Airways", "EVA Air", "Hainan Airlines", "Garuda Indonesia",
    "Asiana Airlines", "Japan Airlines", "Korean Air", "Thai Airways",
    "Swiss International Air Lines", "Lufthansa", "British Airways",
    "Virgin Atlantic Airways", "Air New Zealand", "Etihad Airways",
    "Turkish Airlines", "KLM Royal Dutch Airlines", "Qantas Airways",
    "Finnair", "Austrian Airlines", "SAS Scandinavian Airlines",
    "Air France", "Delta Air Lines",
}


def is_premium(airline: str) -> bool:
    return any(pa.lower() in airline.lower() or airline.lower() in pa.lower()
               for pa in PREMIUM_AIRLINES)


def _rating_to_pleasure(rating: float) -> float:
    return max(0.0, min(1.0, (rating - 1) / 9.0))


def map_to_user_side(ann: dict) -> dict:
    """Map 18-dim airline annotation to user-side format for edge computation."""
    return {
        "user_personality_openness": ann.get("openness", 0.5),
        "user_personality_conscientiousness": ann.get("conscientiousness", 0.5),
        "user_personality_extraversion": ann.get("extraversion", 0.5),
        "user_personality_agreeableness": ann.get("agreeableness", 0.5),
        "user_personality_neuroticism": ann.get("neuroticism", 0.5),
        "user_regulatory_focus_promotion": ann.get("promotion_focus", 0.5),
        "user_regulatory_focus_prevention": ann.get("prevention_focus", 0.5),
        "user_need_for_cognition": ann.get("need_for_cognition", 0.5),
        "user_negativity_bias": ann.get("negativity_bias", 0.5),
        "user_reactance": ann.get("reactance", 0.5),
        "user_brand_trust_known_brand_trust": ann.get("brand_trust", 0.5),
        "user_brand_trust_unknown_brand_skepticism": 1.0 - ann.get("brand_trust", 0.5),
        "user_brand_trust_review_reliance": 0.5,
        "user_spending_pain_sensitivity": ann.get("spending_pain", 0.5),
        "user_self_monitoring": ann.get("self_monitoring", 0.5),
        "user_emotion_pleasure": _rating_to_pleasure(ann.get("rating", 5)),
        "user_emotion_arousal": ann.get("emotional_expressiveness", 0.5),
        "user_emotion_dominance": 0.5 + 0.3 * (ann.get("promotion_focus", 0.5) - 0.5),
        "user_implicit_drivers_identity_signaling": ann.get("status_seeking", 0.3),
        "user_anchor_susceptibility": ann.get("anchor_susceptibility", 0.5),
        "user_decision_style_maximizer": ann.get("detail_orientation", 0.5),
        "user_decision_style_information_search_depth": ann.get("detail_orientation", 0.5),
        "user_construal_level": 1.0 - ann.get("detail_orientation", 0.5) * 0.6,
        "user_social_proof_reliance": ann.get("social_proof_reliance", 0.5),
        "user_uniqueness_need_creative_choice": ann.get("openness", 0.5) * 0.7,
        "user_uniqueness_need_unpopular_choice": max(0, ann.get("openness", 0.5) - 0.3) * 0.5,
        "user_uniqueness_need_avoidance_of_similarity": ann.get("status_seeking", 0.3) * 0.6,
        "user_optimal_distinctiveness": (ann.get("openness", 0.5) + ann.get("status_seeking", 0.3)) / 2,
        "user_purchase_involvement": 0.7,
        "user_anticipated_regret": ann.get("neuroticism", 0.5) * 0.6,
        "annotation_confidence": 0.65,
    }


def compute_edges(annotations: list, ad_annotation: dict) -> list:
    """Compute bilateral edges against LUXY Ride ad-side."""
    from adam.corpus.edge_builders.match_calculators import compute_brand_buyer_edge

    edges = []
    for ann in annotations:
        user_side = map_to_user_side(ann)
        review_meta = {
            "rating": ann.get("rating", 5),
            "helpful_vote": 0, "total_vote": 0, "text": "",
            "category": "Premium Air Travel",
            "timestamp": 0,
        }
        try:
            edge = compute_brand_buyer_edge(
                ad_annotation=ad_annotation,
                user_annotation=user_side,
                review_meta=review_meta,
            )
            # Add metadata
            edge["_review_id"] = ann.get("review_id", "")
            edge["_airline"] = ann.get("airline", "")
            edge["_rating"] = ann.get("rating", 0)
            edge["_country"] = ann.get("country", "")
            edge["_outcome"] = ann.get("outcome", "")
            # Raw dims for archetype classification
            for dim in ["openness", "conscientiousness", "extraversion", "agreeableness",
                        "neuroticism", "promotion_focus", "prevention_focus",
                        "need_for_cognition", "negativity_bias", "reactance",
                        "brand_trust", "spending_pain", "self_monitoring",
                        "emotional_expressiveness", "social_proof_reliance",
                        "anchor_susceptibility", "status_seeking", "detail_orientation"]:
                edge[f"_raw_{dim}"] = ann.get(dim, 0.5)
            edges.append(edge)
        except Exception:
            pass
    return edges


def classify_archetype(edge: dict) -> str:
    """Classify an edge into one of the validated archetypes (polar + moderate)."""
    r = lambda d: edge.get(f"_raw_{d}", 0.5)

    # Interaction effects
    explorer = r("openness") * r("promotion_focus")
    loyalist = r("agreeableness") * r("brand_trust")
    reliable = r("conscientiousness") * r("agreeableness")
    prevention = r("conscientiousness") * r("prevention_focus")
    anxious = r("neuroticism") * r("spending_pain")
    vocal = r("emotional_expressiveness") * r("reactance")
    defensive = r("neuroticism") * r("reactance")
    dependable = r("brand_trust") * r("conscientiousness")
    consensus = r("agreeableness") * r("social_proof_reliance")

    # Suppress archetypes first (worst first)
    if defensive > 0.3 and r("neuroticism") > 0.55 and r("reactance") > 0.55:
        return "defensive_skeptic"
    if anxious > 0.3 and r("neuroticism") > 0.55:
        return "anxious_economist"
    if vocal > 0.3 and r("reactance") > 0.55:
        return "vocal_resistor"

    # Target archetypes — pick strongest interaction
    scores = {
        "explorer": explorer,
        "trusting_loyalist": loyalist,
        "reliable_cooperator": reliable,
        "prevention_planner": prevention,
        "dependable_loyalist": dependable,
        "consensus_seeker": consensus,
    }
    best = max(scores, key=scores.get)

    # Disambiguation
    if best == "trusting_loyalist" and reliable > loyalist * 0.9:
        if r("conscientiousness") > r("agreeableness"):
            return "reliable_cooperator"
    if best == "dependable_loyalist" and loyalist > dependable * 0.95:
        if r("agreeableness") > r("conscientiousness"):
            return "trusting_loyalist"

    return best


def load_to_neo4j(edges: list):
    """Load airline premium edges into Neo4j."""
    from neo4j import GraphDatabase

    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user = os.getenv("NEO4J_USERNAME", "neo4j")
    pw = os.getenv("NEO4J_PASSWORD", "")
    if not pw:
        env_file = PROJECT_ROOT / ".env"
        if env_file.exists():
            for line in env_file.read_text().splitlines():
                if line.startswith("NEO4J_PASSWORD="):
                    pw = line.split("=", 1)[1].strip().strip('"').strip("'")
                elif line.startswith("NEO4J_URI="):
                    uri = line.split("=", 1)[1].strip().strip('"').strip("'")
                elif line.startswith("NEO4J_USERNAME="):
                    user = line.split("=", 1)[1].strip().strip('"').strip("'")

    logger.info("Connecting to Neo4j at %s ...", uri)
    driver = GraphDatabase.driver(uri, auth=(user, pw))
    driver.verify_connectivity()
    logger.info("Connected.")

    with driver.session() as session:
        # Check existing airline edges
        result = session.run(
            "MATCH (ar:AnnotatedReview {category: 'airline_premium'})"
            "-[bc:BRAND_CONVERTED]->() RETURN count(bc) AS n"
        )
        existing = result.single()["n"]
        if existing > 0:
            logger.info("Found %d existing airline_premium edges. Cleaning...", existing)
            session.run(
                "MATCH (ar:AnnotatedReview {category: 'airline_premium'})"
                "-[bc:BRAND_CONVERTED]->() DELETE bc"
            )
            session.run(
                "MATCH (ar:AnnotatedReview {category: 'airline_premium'}) "
                "DETACH DELETE ar"
            )
            logger.info("Cleaned.")

        # Ensure LUXY Ride ProductDescription exists
        session.run("""
            MERGE (pd:ProductDescription {asin: 'lux_luxy_ride'})
            ON CREATE SET pd.name = 'LUXY Ride',
                          pd.product_category = 'Luxury Transportation',
                          pd.category = 'luxury_transportation'
        """)

        # Ensure ProductCategory exists
        session.run("""
            MERGE (pc:ProductCategory {name: 'luxury_transportation'})
            ON CREATE SET pc.display_name = 'Luxury Transportation'
        """)
        session.run("""
            MERGE (pc:ProductCategory {name: 'airline_premium'})
            ON CREATE SET pc.display_name = 'Premium Air Travel (Cross-Category Validation)'
        """)

        # Batch load edges
        batch_size = 200
        loaded = 0
        t0 = time.time()

        for i in range(0, len(edges), batch_size):
            batch = edges[i:i + batch_size]
            rows = []
            for e in batch:
                archetype = classify_archetype(e)
                review_id = f"airline_{e['_review_id']}"

                # Edge properties (numeric only)
                edge_props = {k: v for k, v in e.items()
                              if not k.startswith("_") and isinstance(v, (int, float))}

                rows.append({
                    "review_id": review_id,
                    "airline": e.get("_airline", "Unknown"),
                    "rating": e.get("_rating", 0),
                    "outcome": e.get("_outcome", "neutral"),
                    "country": e.get("_country", ""),
                    "archetype": archetype,
                    "edge_props": edge_props,
                    # Raw dims for graph queries
                    "openness": e.get("_raw_openness", 0.5),
                    "conscientiousness": e.get("_raw_conscientiousness", 0.5),
                    "extraversion": e.get("_raw_extraversion", 0.5),
                    "agreeableness": e.get("_raw_agreeableness", 0.5),
                    "neuroticism": e.get("_raw_neuroticism", 0.5),
                    "promotion_focus": e.get("_raw_promotion_focus", 0.5),
                    "prevention_focus": e.get("_raw_prevention_focus", 0.5),
                    "brand_trust": e.get("_raw_brand_trust", 0.5),
                    "spending_pain": e.get("_raw_spending_pain", 0.5),
                    "reactance": e.get("_raw_reactance", 0.5),
                    "negativity_bias": e.get("_raw_negativity_bias", 0.5),
                    "status_seeking": e.get("_raw_status_seeking", 0.5),
                })

            session.run("""
                UNWIND $rows AS r
                CREATE (ar:AnnotatedReview {
                    id: r.review_id,
                    category: 'airline_premium',
                    airline: r.airline,
                    rating: r.rating,
                    outcome: r.outcome,
                    country: r.country,
                    archetype: r.archetype,
                    openness: r.openness,
                    conscientiousness: r.conscientiousness,
                    extraversion: r.extraversion,
                    agreeableness: r.agreeableness,
                    neuroticism: r.neuroticism,
                    promotion_focus: r.promotion_focus,
                    prevention_focus: r.prevention_focus,
                    brand_trust: r.brand_trust,
                    spending_pain: r.spending_pain,
                    reactance: r.reactance,
                    negativity_bias: r.negativity_bias,
                    status_seeking: r.status_seeking,
                    annotation_tier: 'batch_claude'
                })
                WITH ar, r
                MATCH (pd:ProductDescription {asin: 'lux_luxy_ride'})
                CREATE (pd)-[bc:BRAND_CONVERTED]->(ar)
                SET bc += r.edge_props,
                    bc.source_category = 'airline_premium',
                    bc.archetype = r.archetype,
                    bc.cross_category = true
            """, rows=rows)

            loaded += len(batch)
            if loaded % 1000 == 0 or loaded >= len(edges):
                elapsed = time.time() - t0
                logger.info("  Loaded %d / %d edges (%.1fs)", loaded, len(edges), elapsed)

        # Link to category
        session.run("""
            MATCH (ar:AnnotatedReview {category: 'airline_premium'})
            MATCH (pc:ProductCategory {name: 'airline_premium'})
            MERGE (ar)-[:IN_CATEGORY]->(pc)
        """)

        # Update archetype priors with validated interaction-effect archetypes
        logger.info("Updating archetype priors with validated archetypes...")
        validated_archetypes = {
            "explorer": {
                "social_proof": (3, 5), "authority": (3, 5), "scarcity": (5, 3),
                "narrative": (7, 1), "aspiration": (7, 1), "urgency": (4, 4),
            },
            "trusting_loyalist": {
                "social_proof": (7, 1), "authority": (6, 2), "scarcity": (3, 5),
                "narrative": (5, 3), "aspiration": (5, 3), "urgency": (2, 6),
            },
            "reliable_cooperator": {
                "social_proof": (5, 3), "authority": (6, 2), "scarcity": (3, 5),
                "narrative": (4, 4), "aspiration": (4, 4), "urgency": (3, 5),
            },
            "prevention_planner": {
                "social_proof": (4, 4), "authority": (7, 1), "scarcity": (2, 6),
                "narrative": (3, 5), "aspiration": (2, 6), "urgency": (5, 3),
            },
            "anxious_economist": {
                "social_proof": (2, 6), "authority": (4, 4), "scarcity": (1, 7),
                "narrative": (2, 6), "aspiration": (1, 7), "urgency": (2, 6),
            },
            "vocal_resistor": {
                "social_proof": (1, 7), "authority": (2, 6), "scarcity": (1, 7),
                "narrative": (2, 6), "aspiration": (1, 7), "urgency": (1, 7),
            },
        }

        for arch_id, mechanisms in validated_archetypes.items():
            session.run("""
                MERGE (a:CustomerArchetype {archetype_id: $arch_id})
                SET a.name = $arch_id,
                    a.source = 'cross_category_validated',
                    a.validation_n = 11805
            """, arch_id=arch_id)

            for mech, (alpha, beta) in mechanisms.items():
                session.run("""
                    MATCH (a:CustomerArchetype {archetype_id: $arch_id})
                    MERGE (m:Mechanism {name: $mech})
                    MERGE (a)-[r:RESPONDS_TO]->(m)
                    SET r.alpha = $alpha, r.beta = $beta,
                        r.effectiveness = toFloat($alpha) / ($alpha + $beta),
                        r.validated = true,
                        r.validation_source = 'airline_premium_11805'
                """, arch_id=arch_id, mech=mech, alpha=alpha, beta=beta)

        # Summary
        result = session.run("""
            MATCH ()-[bc:BRAND_CONVERTED]->()
            RETURN count(bc) AS total_edges,
                   count(CASE WHEN bc.cross_category = true THEN 1 END) AS airline_edges,
                   count(CASE WHEN bc.cross_category IS NULL THEN 1 END) AS luxy_edges
        """)
        rec = result.single()
        logger.info("\n=== Neo4j Final State ===")
        logger.info("  Total BRAND_CONVERTED edges: %d", rec["total_edges"])
        logger.info("  LUXY Ride edges: %d", rec["luxy_edges"])
        logger.info("  Airline premium edges: %d", rec["airline_edges"])

        # Archetype distribution
        result = session.run("""
            MATCH ()-[bc:BRAND_CONVERTED]->(ar:AnnotatedReview {category: 'airline_premium'})
            RETURN bc.archetype AS archetype, count(*) AS n
            ORDER BY n DESC
        """)
        logger.info("\n  Archetype distribution (airline):")
        for rec in result:
            logger.info("    %s: %d", rec["archetype"], rec["n"])

        result = session.run("""
            MATCH (a:CustomerArchetype)
            RETURN count(a) AS n
        """)
        logger.info("  CustomerArchetype nodes: %d", result.single()["n"])

    driver.close()
    logger.info("Done.")


def main():
    logger.info("=" * 60)
    logger.info("LOAD PREMIUM AIRLINE EDGES TO NEO4J")
    logger.info("=" * 60)

    # Load source data
    logger.info("Loading annotations...")
    with open(ANNOTATIONS_FILE) as f:
        all_annotations = json.load(f)
    logger.info("  Total: %d", len(all_annotations))

    logger.info("Loading LUXY Ride ad-side...")
    with open(AD_SIDE_FILE) as f:
        ad_annotations = json.load(f)
    luxy_ad = ad_annotations.get("LUXY Ride") or ad_annotations.get("LUXYRide")

    # Filter premium satisfied
    filtered = [a for a in all_annotations
                if is_premium(a.get("airline", "")) and a.get("rating", 0) >= 7]
    logger.info("  Filtered premium satisfied: %d", len(filtered))

    # Compute edges
    logger.info("Computing bilateral edges...")
    edges = compute_edges(filtered, luxy_ad)
    logger.info("  Computed: %d edges", len(edges))

    # Classify archetypes
    arch_dist = Counter(classify_archetype(e) for e in edges)
    logger.info("  Archetype distribution:")
    for arch, n in arch_dist.most_common():
        logger.info("    %s: %d (%.1f%%)", arch, n, n / len(edges) * 100)

    # Load to Neo4j
    load_to_neo4j(edges)


if __name__ == "__main__":
    main()
