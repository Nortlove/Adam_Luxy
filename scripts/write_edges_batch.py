#!/usr/bin/env python3
"""Write luxury_transportation edges to Neo4j using UNWIND for batch performance."""

import json
import os
import sys
import time

EDGE_DIMS = [
    'regulatory_fit_score', 'construal_fit_score', 'personality_brand_alignment',
    'emotional_resonance', 'value_alignment', 'evolutionary_motive_match',
    'linguistic_style_matching', 'spending_pain_match', 'reactance_fit',
    'self_monitoring_fit', 'processing_route_match', 'mental_simulation_resonance',
    'optimal_distinctiveness_fit', 'involvement_weight_modifier', 'brand_trust_fit',
    'identity_signaling_match', 'anchor_susceptibility_match', 'lay_theory_alignment',
    'negativity_bias_match', 'persuasion_confidence_multiplier',
]


def main():
    from neo4j import GraphDatabase

    # Load
    with open('reviews/luxury_transportation_complete.json') as f:
        data = json.load(f)

    reviews = data['annotated_reviews']
    profiles = data['company_profiles']
    print(f"Loaded {len(reviews)} reviews, {len(profiles)} companies", flush=True)

    uri = os.environ.get('NEO4J_URI', 'bolt://localhost:7687')
    user = os.environ.get('NEO4J_USERNAME', 'neo4j')
    pw = os.environ.get('NEO4J_PASSWORD', '')

    if not pw:
        with open('.env') as f:
            for line in f:
                if line.startswith('NEO4J_PASSWORD='):
                    pw = line.strip().split('=', 1)[1]
                elif line.startswith('NEO4J_URI='):
                    uri = line.strip().split('=', 1)[1]
                elif line.startswith('NEO4J_USERNAME='):
                    user = line.strip().split('=', 1)[1]

    driver = GraphDatabase.driver(uri, auth=(user, pw))
    t0 = time.time()

    with driver.session() as session:
        # 1. Category
        session.run(
            "MERGE (pc:ProductCategory {name: 'luxury_transportation'}) "
            "SET pc.display_name = 'Luxury Transportation', "
            "pc.review_count = $count, pc.last_updated = datetime()",
            count=len(reviews)
        )
        print("Created ProductCategory", flush=True)

        # 2. Companies via UNWIND
        company_list = [
            {"name": c, "rc": p["review_count"], "ar": p["avg_rating"]}
            for c, p in profiles.items()
        ]
        session.run(
            "UNWIND $companies AS c "
            "MERGE (pd:ProductDescription {name: c.name, category: 'luxury_transportation'}) "
            "SET pd.review_count = c.rc, pd.avg_rating = c.ar, pd.last_updated = datetime() "
            "WITH pd "
            "MATCH (pc:ProductCategory {name: 'luxury_transportation'}) "
            "MERGE (pd)-[:IN_CATEGORY]->(pc)",
            companies=company_list
        )
        print(f"Created {len(company_list)} company nodes", flush=True)

        # 3. Reviews + edges via UNWIND in batches of 200
        batch_size = 200
        for batch_start in range(0, len(reviews), batch_size):
            batch = reviews[batch_start:batch_start + batch_size]

            rows = []
            for r in batch:
                row = {
                    "review_id": f"lux_{r['_review_id']}",
                    "company": r.get("_company", "Unknown"),
                    "rating": r.get("_rating", 3),
                    "archetype": r.get("buyer_archetype", "unknown"),
                    "mechanism": r.get("primary_mechanism", "unknown"),
                    "secondary_mechanism": r.get("secondary_mechanism", "unknown"),
                    "purchase_dance_stage": r.get("purchase_dance_stage", "unknown"),
                    "regulatory_focus": r.get("regulatory_focus", "unknown"),
                    "composite_alignment": r.get("composite_alignment", 0.5),
                }
                # Add all 20 dimensions
                for dim in EDGE_DIMS:
                    val = r.get(dim)
                    row[dim] = round(float(val), 4) if isinstance(val, (int, float)) else 0.5

                rows.append(row)

            session.run(
                "UNWIND $rows AS r "
                "MERGE (ar:AnnotatedReview {id: r.review_id}) "
                "SET ar.company = r.company, ar.rating = r.rating, "
                "ar.category = 'luxury_transportation', "
                "ar.buyer_archetype = r.archetype, "
                "ar.primary_mechanism = r.mechanism "
                "WITH ar, r "
                "MATCH (pd:ProductDescription {name: r.company, category: 'luxury_transportation'}) "
                "MERGE (ar)-[bc:BRAND_CONVERTED]->(pd) "
                "SET bc.regulatory_fit_score = r.regulatory_fit_score, "
                "bc.construal_fit_score = r.construal_fit_score, "
                "bc.personality_brand_alignment = r.personality_brand_alignment, "
                "bc.emotional_resonance = r.emotional_resonance, "
                "bc.value_alignment = r.value_alignment, "
                "bc.evolutionary_motive_match = r.evolutionary_motive_match, "
                "bc.linguistic_style_matching = r.linguistic_style_matching, "
                "bc.spending_pain_match = r.spending_pain_match, "
                "bc.reactance_fit = r.reactance_fit, "
                "bc.self_monitoring_fit = r.self_monitoring_fit, "
                "bc.processing_route_match = r.processing_route_match, "
                "bc.mental_simulation_resonance = r.mental_simulation_resonance, "
                "bc.optimal_distinctiveness_fit = r.optimal_distinctiveness_fit, "
                "bc.involvement_weight_modifier = r.involvement_weight_modifier, "
                "bc.brand_trust_fit = r.brand_trust_fit, "
                "bc.identity_signaling_match = r.identity_signaling_match, "
                "bc.anchor_susceptibility_match = r.anchor_susceptibility_match, "
                "bc.lay_theory_alignment = r.lay_theory_alignment, "
                "bc.negativity_bias_match = r.negativity_bias_match, "
                "bc.persuasion_confidence_multiplier = r.persuasion_confidence_multiplier, "
                "bc.primary_mechanism = r.mechanism, "
                "bc.secondary_mechanism = r.secondary_mechanism, "
                "bc.buyer_archetype = r.archetype, "
                "bc.purchase_dance_stage = r.purchase_dance_stage, "
                "bc.regulatory_focus = r.regulatory_focus, "
                "bc.composite_alignment = r.composite_alignment, "
                "bc.product_category = 'luxury_transportation'",
                rows=rows
            )
            elapsed = time.time() - t0
            print(f"  Written {min(batch_start + batch_size, len(reviews))}/{len(reviews)} edges ({elapsed:.1f}s)", flush=True)

        # 4. Bayesian priors
        priors = data.get('bayesian_priors', {})
        for key, prior in priors.items():
            parts = key.rsplit("_", 1)
            mechanism = parts[0] if len(parts) > 0 else key
            archetype = parts[1] if len(parts) > 1 else "all"

            session.run(
                "MERGE (bp:BayesianPrior {"
                "category: 'luxury_transportation', "
                "mechanism: $mechanism, "
                "archetype: $archetype}) "
                "SET bp.alpha = $alpha, bp.beta = $beta, "
                "bp.effectiveness = $eff, bp.sample_size = $n, "
                "bp.last_updated = datetime()",
                mechanism=mechanism, archetype=archetype,
                alpha=prior['alpha'], beta=prior['beta'],
                eff=prior['effectiveness'], n=prior['sample_size'],
            )
        print(f"Created {len(priors)} BayesianPrior nodes", flush=True)

        # 5. Summary query
        result = session.run(
            "MATCH (ar:AnnotatedReview {category: 'luxury_transportation'})"
            "-[bc:BRAND_CONVERTED]->(pd) "
            "RETURN count(bc) as edges, count(DISTINCT pd) as companies, "
            "count(DISTINCT ar) as reviews"
        )
        rec = result.single()
        print(f"\nNeo4j Summary:", flush=True)
        print(f"  BRAND_CONVERTED edges: {rec['edges']}", flush=True)
        print(f"  Companies: {rec['companies']}", flush=True)
        print(f"  Reviews: {rec['reviews']}", flush=True)

    driver.close()
    print(f"\nDone in {time.time() - t0:.1f}s", flush=True)


if __name__ == "__main__":
    main()
