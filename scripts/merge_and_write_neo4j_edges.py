"""
Merge both annotation batches (518 + 974 = 1,492 reviews) and write
BRAND_CONVERTED edges to Neo4j for the luxury_transportation category.

Also:
- Create AnnotatedReview nodes
- Create/update ProductDescription nodes per company
- Create BayesianPrior node for luxury_transportation
- Compute gradient fields
"""

import json
import os
import sys
import statistics
from collections import Counter, defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from adam.intelligence.annotation_engine import ANNOTATION_DIMENSIONS

REVIEWS_DIR = os.path.join(os.path.dirname(__file__), "..", "reviews")

# The 20 edge property names (same as Neo4j BRAND_CONVERTED edge properties)
EDGE_DIMS = list(ANNOTATION_DIMENSIONS.keys())


def load_and_merge():
    """Load both annotation batches and merge."""
    # Batch 1
    with open(os.path.join(REVIEWS_DIR, "luxury_car_service_deep_annotated.json")) as f:
        batch1 = json.load(f)
    reviews1 = batch1["annotated_reviews"]

    # Batch 2
    with open(os.path.join(REVIEWS_DIR, "new_reviews_deep_annotated.json")) as f:
        batch2 = json.load(f)
    reviews2 = batch2["annotated_reviews"]

    # Re-index batch 2 IDs to avoid collision
    for i, r in enumerate(reviews2):
        r["_review_id"] = f"B2-{i:04d}"

    all_reviews = reviews1 + reviews2
    print(f"Merged: {len(reviews1)} + {len(reviews2)} = {len(all_reviews)} reviews")

    return all_reviews


def compute_category_stats(reviews):
    """Compute aggregate statistics for the luxury_transportation category."""
    stats = {}
    for dim in EDGE_DIMS:
        vals = [r[dim] for r in reviews if isinstance(r.get(dim), (int, float))]
        if vals:
            stats[dim] = {
                "mean": round(statistics.mean(vals), 4),
                "stdev": round(statistics.stdev(vals), 4) if len(vals) > 1 else 0,
                "min": round(min(vals), 4),
                "max": round(max(vals), 4),
                "median": round(statistics.median(vals), 4),
            }

    mechanisms = Counter(r.get("primary_mechanism", "unknown") for r in reviews)
    archetypes = Counter(r.get("buyer_archetype", "unknown") for r in reviews)
    reg_focus = Counter(r.get("regulatory_focus", "unknown") for r in reviews)

    return {
        "dimensions": stats,
        "mechanisms": dict(mechanisms),
        "archetypes": dict(archetypes),
        "regulatory_focus": dict(reg_focus),
        "total_reviews": len(reviews),
    }


def compute_company_profiles(reviews):
    """Compute per-company aggregate profiles for ProductDescription nodes."""
    by_company = defaultdict(list)
    for r in reviews:
        company = r.get("_company", "Unknown")
        if company and company != "Unknown":
            by_company[company].append(r)

    profiles = {}
    for company, company_reviews in by_company.items():
        profile = {"company": company, "review_count": len(company_reviews)}

        # Average dimensions
        for dim in EDGE_DIMS:
            vals = [r[dim] for r in company_reviews if isinstance(r.get(dim), (int, float))]
            if vals:
                profile[f"avg_{dim}"] = round(statistics.mean(vals), 4)

        # Top mechanisms
        mechs = Counter(r.get("primary_mechanism", "?") for r in company_reviews)
        profile["primary_mechanisms"] = dict(mechs.most_common(3))

        # Top archetypes
        archs = Counter(r.get("buyer_archetype", "?") for r in company_reviews)
        profile["buyer_archetypes"] = dict(archs.most_common(5))

        # Rating distribution
        ratings = Counter(r.get("_rating", 0) for r in company_reviews)
        profile["rating_distribution"] = dict(ratings)
        profile["avg_rating"] = round(
            sum(r.get("_rating", 0) for r in company_reviews) / len(company_reviews), 2
        )

        profiles[company] = profile

    return profiles


def compute_bayesian_priors(reviews):
    """Compute BayesianPrior parameters for luxury_transportation category.

    For each mechanism, compute effectiveness per archetype using the
    annotated data as evidence for Thompson Sampling initialization.
    """
    # Group by mechanism × archetype
    mech_arch = defaultdict(lambda: {"positive": 0, "total": 0, "dims": defaultdict(list)})

    for r in reviews:
        mech = r.get("primary_mechanism", "unknown")
        arch = r.get("buyer_archetype", "unknown")
        rating = r.get("_rating", 3)
        composite = r.get("composite_alignment", 0.5)

        key = f"{mech}_{arch}"
        mech_arch[key]["total"] += 1

        # "Positive" = high rating AND high alignment (proxy for conversion)
        if rating >= 4 and composite > 0.5:
            mech_arch[key]["positive"] += 1

        # Store dimension values for gradient computation
        for dim in EDGE_DIMS:
            val = r.get(dim)
            if isinstance(val, (int, float)):
                mech_arch[key]["dims"][dim].append(val)

    priors = {}
    for key, data in mech_arch.items():
        alpha = data["positive"] + 1  # Beta prior smoothing
        beta = (data["total"] - data["positive"]) + 1
        effectiveness = alpha / (alpha + beta)

        # Gradient: which dimensions have highest variance (most discriminating)
        gradients = {}
        for dim, vals in data["dims"].items():
            if len(vals) > 5:
                gradients[dim] = round(statistics.stdev(vals), 4)

        priors[key] = {
            "alpha": alpha,
            "beta": beta,
            "effectiveness": round(effectiveness, 4),
            "sample_size": data["total"],
            "gradient_priorities": dict(
                sorted(gradients.items(), key=lambda x: -x[1])[:5]
            ),
        }

    return priors


def write_to_neo4j(reviews, category_stats, company_profiles, bayesian_priors):
    """Write everything to Neo4j."""
    try:
        from neo4j import GraphDatabase
    except ImportError:
        print("neo4j package not installed, saving Cypher to file instead")
        save_cypher_file(reviews, category_stats, company_profiles, bayesian_priors)
        return

    # Load Neo4j credentials
    uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
    user = os.environ.get("NEO4J_USERNAME", "neo4j")
    password = os.environ.get("NEO4J_PASSWORD", "")

    if not password:
        # Try .env
        env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
        if os.path.exists(env_path):
            with open(env_path) as f:
                for line in f:
                    if line.startswith("NEO4J_PASSWORD="):
                        password = line.strip().split("=", 1)[1]
                    elif line.startswith("NEO4J_URI="):
                        uri = line.strip().split("=", 1)[1]
                    elif line.startswith("NEO4J_USERNAME="):
                        user = line.strip().split("=", 1)[1]

    if not password:
        print("No Neo4j password found. Saving Cypher to file instead.")
        save_cypher_file(reviews, category_stats, company_profiles, bayesian_priors)
        return

    driver = GraphDatabase.driver(uri, auth=(user, password))

    try:
        with driver.session() as session:
            # 1. Create ProductCategory node
            session.run("""
                MERGE (pc:ProductCategory {name: 'luxury_transportation'})
                SET pc.display_name = 'Luxury Transportation',
                    pc.review_count = $count,
                    pc.last_updated = datetime()
            """, count=len(reviews))
            print("Created ProductCategory: luxury_transportation")

            # 2. Create company ProductDescription nodes
            for company, profile in company_profiles.items():
                props = {
                    "name": company,
                    "category": "luxury_transportation",
                    "review_count": profile["review_count"],
                    "avg_rating": profile["avg_rating"],
                }
                # Add average dimension scores
                for dim in EDGE_DIMS:
                    key = f"avg_{dim}"
                    if key in profile:
                        props[key] = profile[key]

                session.run("""
                    MERGE (pd:ProductDescription {name: $name, category: $category})
                    SET pd += $props,
                        pd.last_updated = datetime()
                """, name=company, category="luxury_transportation", props=props)

                # Link to category
                session.run("""
                    MATCH (pd:ProductDescription {name: $name, category: 'luxury_transportation'})
                    MATCH (pc:ProductCategory {name: 'luxury_transportation'})
                    MERGE (pd)-[:IN_CATEGORY]->(pc)
                """, name=company)

            print(f"Created {len(company_profiles)} ProductDescription nodes")

            # 3. Create AnnotatedReview nodes and BRAND_CONVERTED edges
            batch_size = 50
            for i in range(0, len(reviews), batch_size):
                batch = reviews[i:i + batch_size]

                for r in batch:
                    review_id = f"lux_review_{r['_review_id']}"
                    company = r.get("_company", "Unknown")

                    # Build edge properties (the 20 dimensions + metadata)
                    edge_props = {}
                    for dim in EDGE_DIMS:
                        val = r.get(dim)
                        if isinstance(val, (int, float)):
                            edge_props[dim] = round(float(val), 4)

                    edge_props["primary_mechanism"] = r.get("primary_mechanism", "unknown")
                    edge_props["secondary_mechanism"] = r.get("secondary_mechanism", "unknown")
                    edge_props["buyer_archetype"] = r.get("buyer_archetype", "unknown")
                    edge_props["purchase_dance_stage"] = r.get("purchase_dance_stage", "unknown")
                    edge_props["regulatory_focus"] = r.get("regulatory_focus", "unknown")
                    edge_props["composite_alignment"] = r.get("composite_alignment", 0.5)
                    edge_props["product_category"] = "luxury_transportation"

                    session.run("""
                        MERGE (ar:AnnotatedReview {id: $review_id})
                        SET ar.text = $text,
                            ar.company = $company,
                            ar.rating = $rating,
                            ar.category = 'luxury_transportation',
                            ar.buyer_archetype = $archetype,
                            ar.primary_mechanism = $mechanism,
                            ar.regulatory_focus = $reg_focus,
                            ar.triggering_moment = $trigger,
                            ar.anti_trigger = $anti_trigger,
                            ar.ad_recommendation = $ad_rec

                        WITH ar
                        MATCH (pd:ProductDescription {name: $company, category: 'luxury_transportation'})
                        MERGE (ar)-[bc:BRAND_CONVERTED]->(pd)
                        SET bc += $edge_props
                    """,
                        review_id=review_id,
                        text=r.get("_text", "")[:500],  # Truncate for storage
                        company=company,
                        rating=r.get("_rating", 3),
                        archetype=r.get("buyer_archetype", "unknown"),
                        mechanism=r.get("primary_mechanism", "unknown"),
                        reg_focus=r.get("regulatory_focus", "unknown"),
                        trigger=r.get("triggering_moment", ""),
                        anti_trigger=r.get("anti_trigger", ""),
                        ad_rec=r.get("ad_recommendation", ""),
                        edge_props=edge_props,
                    )

                print(f"  Written {min(i + batch_size, len(reviews))}/{len(reviews)} edges")

            # 4. Create BayesianPrior node
            for key, prior in bayesian_priors.items():
                parts = key.split("_", 1)
                mechanism = parts[0] if len(parts) > 0 else key
                archetype = parts[1] if len(parts) > 1 else "all"

                session.run("""
                    MERGE (bp:BayesianPrior {
                        category: 'luxury_transportation',
                        mechanism: $mechanism,
                        archetype: $archetype
                    })
                    SET bp.alpha = $alpha,
                        bp.beta = $beta,
                        bp.effectiveness = $effectiveness,
                        bp.sample_size = $sample_size,
                        bp.last_updated = datetime()
                """,
                    mechanism=mechanism,
                    archetype=archetype,
                    alpha=prior["alpha"],
                    beta=prior["beta"],
                    effectiveness=prior["effectiveness"],
                    sample_size=prior["sample_size"],
                )

            print(f"Created {len(bayesian_priors)} BayesianPrior nodes")

            # 5. Summary query
            result = session.run("""
                MATCH (ar:AnnotatedReview {category: 'luxury_transportation'})-[bc:BRAND_CONVERTED]->(pd:ProductDescription)
                RETURN count(bc) as edge_count,
                       count(DISTINCT pd) as company_count,
                       count(DISTINCT ar) as review_count
            """)
            record = result.single()
            if record:
                print(f"\nNeo4j Summary:")
                print(f"  BRAND_CONVERTED edges: {record['edge_count']}")
                print(f"  Companies: {record['company_count']}")
                print(f"  Reviews: {record['review_count']}")

    finally:
        driver.close()


def save_cypher_file(reviews, category_stats, company_profiles, bayesian_priors):
    """Save Cypher statements to file for manual import."""
    output_path = os.path.join(REVIEWS_DIR, "neo4j_import_luxury_transportation.cypher")
    with open(output_path, "w") as f:
        f.write("// Luxury Transportation Category Import\n")
        f.write(f"// {len(reviews)} reviews, {len(company_profiles)} companies\n\n")

        f.write("// Create category\n")
        f.write(f"MERGE (pc:ProductCategory {{name: 'luxury_transportation'}})\n")
        f.write(f"SET pc.display_name = 'Luxury Transportation', pc.review_count = {len(reviews)};\n\n")

        for company, profile in company_profiles.items():
            f.write(f"// {company}\n")
            f.write(f"MERGE (pd:ProductDescription {{name: '{company}', category: 'luxury_transportation'}})\n")
            f.write(f"SET pd.review_count = {profile['review_count']}, pd.avg_rating = {profile['avg_rating']};\n\n")

    print(f"Saved Cypher to {output_path}")


def save_combined_output(reviews, category_stats, company_profiles, bayesian_priors):
    """Save the combined annotated dataset."""
    output = {
        "metadata": {
            "total_reviews": len(reviews),
            "category": "luxury_transportation",
            "batch1_count": 518,
            "batch2_count": 974,
        },
        "category_stats": category_stats,
        "company_profiles": company_profiles,
        "bayesian_priors": bayesian_priors,
        "annotated_reviews": reviews,
    }

    output_path = os.path.join(REVIEWS_DIR, "luxury_transportation_complete.json")
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"Saved complete dataset to {output_path}")


def main():
    # Merge
    all_reviews = load_and_merge()

    # Compute stats
    category_stats = compute_category_stats(all_reviews)
    print(f"\nCategory Stats:")
    print(f"  Total reviews: {category_stats['total_reviews']}")
    print(f"  Top mechanisms: {Counter(category_stats['mechanisms']).most_common(5)}")
    print(f"  Top archetypes: {Counter(category_stats['archetypes']).most_common(5)}")

    # Company profiles
    company_profiles = compute_company_profiles(all_reviews)
    print(f"\nCompany Profiles ({len(company_profiles)} companies):")
    for company, profile in sorted(company_profiles.items(), key=lambda x: -x[1]["review_count"]):
        print(f"  {company}: {profile['review_count']} reviews, avg rating {profile['avg_rating']}")

    # Bayesian priors
    bayesian_priors = compute_bayesian_priors(all_reviews)
    print(f"\nBayesian Priors ({len(bayesian_priors)} mechanism×archetype cells):")
    for key, prior in sorted(bayesian_priors.items(), key=lambda x: -x[1]["effectiveness"])[:10]:
        print(f"  {key}: effectiveness={prior['effectiveness']}, n={prior['sample_size']}")

    # Save combined
    save_combined_output(all_reviews, category_stats, company_profiles, bayesian_priors)

    # Write to Neo4j
    write_to_neo4j(all_reviews, category_stats, company_profiles, bayesian_priors)


if __name__ == "__main__":
    main()
