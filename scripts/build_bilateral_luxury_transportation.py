#!/usr/bin/env python3
"""
Build the COMPLETE bilateral graph for luxury_transportation.

Uses the SAME annotation system as the Amazon 47M-edge graph:
- Ad-side: 65 dimensions via AD_SIDE_USER_PROMPT_TEMPLATE
- User-side: 65 dimensions via DUAL_PROMPT_TEMPLATE (+ 21 peer-ad)
- Edge computation: 27 alignment dimensions via compute_brand_buyer_edge()

Phases:
1. Annotate brand content (seller side) → ProductDescription nodes
2. Re-annotate reviews (buyer side) → AnnotatedReview nodes
3. Compute bilateral alignment edges → BRAND_CONVERTED edges
4. Write everything to Neo4j

Usage:
    source .env && export ANTHROPIC_API_KEY NEO4J_URI NEO4J_USERNAME NEO4J_PASSWORD
    python3 -u scripts/build_bilateral_luxury_transportation.py
"""

import json
import logging
import os
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from adam.corpus.annotators.prompt_templates import (
    AD_SIDE_SYSTEM_PROMPT,
    AD_SIDE_USER_PROMPT_TEMPLATE,
    DUAL_SYSTEM_PROMPT,
    DUAL_PROMPT_TEMPLATE,
    USER_ONLY_PROMPT_TEMPLATE,
)
from adam.corpus.models.ad_side_annotation import AdSideAnnotation
from adam.corpus.edge_builders.match_calculators import compute_brand_buyer_edge

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
logger = logging.getLogger(__name__)

REVIEWS_DIR = Path(__file__).parent.parent / "reviews"
BRAND_CONTENT_FILE = REVIEWS_DIR / "luxury_brand_content_crawled.json"
REVIEWS_FILE = REVIEWS_DIR / "luxury_transportation_complete.json"

# Output files
AD_SIDE_OUTPUT = REVIEWS_DIR / "luxury_ad_side_annotated.json"
USER_SIDE_OUTPUT = REVIEWS_DIR / "luxury_user_side_annotated.json"
EDGES_OUTPUT = REVIEWS_DIR / "luxury_bilateral_edges.json"

WORKERS = 8


def get_client():
    """Get Anthropic client."""
    import anthropic
    return anthropic.Anthropic()


# =============================================================================
# PHASE 1: AD-SIDE ANNOTATION (Brands)
# =============================================================================

def annotate_brand_ad_side(client, brand_name: str, brand_data: dict) -> dict:
    """Annotate a brand's content with the full 65-dim ad-side prompt."""
    # Build product-like record from brand content
    title = f"{brand_name} - Luxury Car Service"
    category = "Luxury Transportation"
    price = brand_data.get("pricing_positioning", "Premium")
    brand = brand_name
    description = brand_data.get("full_copy_block", "")
    if not description:
        # Concatenate available text
        parts = []
        for key in ["homepage_text", "about_text", "fleet_description",
                     "driver_quality", "technology", "sustainability"]:
            if brand_data.get(key):
                parts.append(str(brand_data[key]))
        for key in ["taglines", "service_descriptions", "value_propositions",
                     "safety_claims"]:
            if brand_data.get(key):
                parts.extend([str(x) for x in brand_data[key]])
        description = " ".join(parts)

    features = " | ".join(brand_data.get("value_propositions", [])[:10])

    if len(description) < 20:
        logger.warning(f"Insufficient text for {brand_name}, skipping")
        return None

    prompt = AD_SIDE_USER_PROMPT_TEMPLATE.format(
        title=title[:200],
        category=category,
        price=price,
        brand=brand,
        description_text=description[:3000],
        features_text=features[:1000],
    )

    for attempt in range(3):
        try:
            response = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=2000,
                system=AD_SIDE_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )
            text = response.content[0].text.strip()
            if text.startswith("```"):
                lines = text.split("\n")
                text = "\n".join(l for l in lines if not l.strip().startswith("```"))

            result = json.loads(text)

            # Convert to flat dict with ad_ prefix using AdSideAnnotation
            annotation = AdSideAnnotation(
                asin=f"lux_{brand_name.lower().replace(' ', '_')}",
                **result,
            )
            flat = annotation.to_flat_dict()
            flat["asin"] = annotation.asin
            flat["brand_name"] = brand_name
            flat["annotation_tier"] = "claude"
            return flat

        except json.JSONDecodeError as e:
            logger.warning(f"JSON error for {brand_name} (attempt {attempt+1}): {e}")
            time.sleep(1)
        except Exception as e:
            logger.warning(f"Error for {brand_name} (attempt {attempt+1}): {e}")
            time.sleep(2)

    return None


def run_phase1(client) -> dict:
    """Phase 1: Annotate all brands."""
    print("\n" + "=" * 60, flush=True)
    print("PHASE 1: AD-SIDE ANNOTATION (Brands)", flush=True)
    print("=" * 60, flush=True)

    # Load brand content
    if not BRAND_CONTENT_FILE.exists():
        # Use the ad copy we already have as fallback
        print("Brand content file not found, using existing ad copy", flush=True)
        with open(REVIEWS_DIR / "luxury_car_service_ads.json") as f:
            ads_data = json.load(f)
        with open(REVIEWS_DIR / "luxury_car_service_ads_expanded.json") as f:
            ads_expanded = json.load(f)

        # Group ads by company
        brands = {}
        for ad in ads_data.get("advertisements", []):
            company = ad.get("company", "Unknown")
            if company not in brands:
                brands[company] = {"taglines": [], "service_descriptions": [],
                                   "value_propositions": [], "full_copy_block": ""}
            text = f"{ad.get('headline', '')} {ad.get('body_copy', '')}"
            brands[company]["service_descriptions"].append(text)
            brands[company]["full_copy_block"] += " " + text

        for ad in ads_expanded.get("ads", []):
            company = ad.get("company", "Unknown")
            if company not in brands:
                brands[company] = {"taglines": [], "service_descriptions": [],
                                   "value_propositions": [], "full_copy_block": ""}
            text = ad.get("copy_text", "")
            if ad.get("copy_type") == "tagline":
                brands[company]["taglines"].append(text)
            brands[company]["full_copy_block"] += " " + text

        brand_content = {"brands": brands}
    else:
        with open(BRAND_CONTENT_FILE) as f:
            brand_content = json.load(f)

    brands = brand_content.get("brands", {})
    print(f"Brands to annotate: {len(brands)}", flush=True)

    ad_annotations = {}
    for brand_name, brand_data in brands.items():
        result = annotate_brand_ad_side(client, brand_name, brand_data)
        if result:
            ad_annotations[brand_name] = result
            print(f"  ✓ {brand_name}: {result.get('annotation_confidence', 0):.2f} confidence", flush=True)
        else:
            print(f"  ✗ {brand_name}: failed", flush=True)

    # Save
    with open(AD_SIDE_OUTPUT, "w") as f:
        json.dump(ad_annotations, f, indent=2)
    print(f"\nSaved {len(ad_annotations)} ad-side annotations to {AD_SIDE_OUTPUT}", flush=True)

    return ad_annotations


# =============================================================================
# PHASE 2: USER-SIDE ANNOTATION (Reviews)
# =============================================================================

def annotate_review_user_side(client, review: dict, idx: int) -> dict:
    """Annotate a single review with the full 65-dim dual prompt."""
    text = review.get("_text", review.get("review_text", ""))
    rating = review.get("_rating", review.get("rating", 3))
    company = review.get("_company", review.get("company", "Unknown"))

    if not text or len(text) < 20:
        return None

    # Use the dual prompt (user-side + peer-ad-side)
    prompt = DUAL_PROMPT_TEMPLATE.format(
        product_title=f"{company} - Luxury Car Service",
        category="Luxury Transportation",
        star_rating=rating,
        helpful_votes=0,
        review_text=text[:2000],
    )

    for attempt in range(3):
        try:
            response = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=2000,
                system=DUAL_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )
            resp_text = response.content[0].text.strip()
            if resp_text.startswith("```"):
                lines = resp_text.split("\n")
                resp_text = "\n".join(l for l in lines if not l.strip().startswith("```"))

            result = json.loads(resp_text)

            # Flatten user_side with user_ prefix
            user_side = result.get("user_side", result)
            flat = {}
            for key, value in user_side.items():
                if isinstance(value, dict):
                    for subkey, subval in value.items():
                        flat[f"user_{key}_{subkey}"] = subval
                elif isinstance(value, list):
                    flat[f"user_{key}"] = value
                else:
                    flat[f"user_{key}"] = value

            # Add peer-ad side if present
            peer_side = result.get("peer_ad_side", {})
            for key, value in peer_side.items():
                if isinstance(value, dict):
                    for subkey, subval in value.items():
                        flat[f"peer_ad_{key}_{subkey}"] = subval
                else:
                    flat[f"peer_ad_{key}"] = value

            # Add conversion outcome
            flat["user_conversion_outcome"] = result.get("conversion_outcome",
                user_side.get("conversion_outcome", "neutral"))

            # Metadata
            flat["_review_id"] = idx
            flat["_company"] = company
            flat["_rating"] = rating
            flat["_text"] = text
            flat["annotation_confidence"] = user_side.get("annotation_confidence", 0.5)
            flat["annotation_tier"] = "claude"

            return flat

        except json.JSONDecodeError as e:
            logger.warning(f"JSON error review {idx} (attempt {attempt+1})")
            time.sleep(1)
        except Exception as e:
            logger.warning(f"Error review {idx} (attempt {attempt+1}): {e}")
            time.sleep(2)

    return None


def run_phase2(client) -> list:
    """Phase 2: Re-annotate all reviews with full dual prompt."""
    print("\n" + "=" * 60, flush=True)
    print("PHASE 2: USER-SIDE ANNOTATION (Reviews)", flush=True)
    print("=" * 60, flush=True)

    # Check for existing partial results
    if USER_SIDE_OUTPUT.exists():
        with open(USER_SIDE_OUTPUT) as f:
            existing = json.load(f)
        if existing.get("status") == "complete":
            print(f"Already complete: {len(existing['annotations'])} reviews", flush=True)
            return existing["annotations"]
        completed = existing.get("annotations", [])
        completed_ids = {a["_review_id"] for a in completed}
        print(f"Resuming from {len(completed)} completed", flush=True)
    else:
        completed = []
        completed_ids = set()

    with open(REVIEWS_FILE) as f:
        data = json.load(f)
    reviews = data["annotated_reviews"]
    total = len(reviews)
    print(f"Total reviews: {total}", flush=True)

    remaining = [(i, r) for i, r in enumerate(reviews) if i not in completed_ids]
    print(f"Remaining: {len(remaining)}", flush=True)

    errors = 0
    t0 = time.time()

    with ThreadPoolExecutor(max_workers=WORKERS) as executor:
        chunk_size = 50
        for chunk_start in range(0, len(remaining), chunk_size):
            chunk = remaining[chunk_start:chunk_start + chunk_size]

            futures = {}
            for idx, review in chunk:
                f = executor.submit(annotate_review_user_side, client, review, idx)
                futures[f] = idx

            for future in as_completed(futures):
                result = future.result()
                if result:
                    completed.append(result)
                    completed_ids.add(result["_review_id"])
                else:
                    errors += 1

            elapsed = time.time() - t0
            rate = len(completed) / elapsed if elapsed > 0 else 0
            eta = (len(remaining) - len(completed) + len(data["annotated_reviews"]) - total) / rate if rate > 0 else 0
            print(
                f"  [{len(completed)}/{total}] {errors} err, "
                f"{rate:.1f}/s, ETA {max(0,eta)/60:.1f}min",
                flush=True,
            )

            # Checkpoint
            with open(USER_SIDE_OUTPUT, "w") as f:
                json.dump({"status": "in_progress", "annotations": completed}, f)

    # Final save
    with open(USER_SIDE_OUTPUT, "w") as f:
        json.dump({"status": "complete", "annotations": completed, "errors": errors}, f, indent=2)
    print(f"\nSaved {len(completed)} user-side annotations ({errors} errors)", flush=True)

    return completed


# =============================================================================
# PHASE 3: COMPUTE BILATERAL EDGES
# =============================================================================

def run_phase3(ad_annotations: dict, user_annotations: list) -> list:
    """Phase 3: Compute bilateral alignment edges."""
    print("\n" + "=" * 60, flush=True)
    print("PHASE 3: COMPUTE BILATERAL ALIGNMENT EDGES", flush=True)
    print("=" * 60, flush=True)

    edges = []
    no_match = 0

    for user_ann in user_annotations:
        company = user_ann.get("_company", "Unknown")
        rating = user_ann.get("_rating", 3)
        text = user_ann.get("_text", "")
        review_id = user_ann.get("_review_id", 0)

        # Find matching ad annotation
        ad_ann = ad_annotations.get(company)
        if not ad_ann:
            # Fall back to closest match or use RideLux as category proxy
            # Since all reviews serve as category intelligence for RideLux,
            # use the most similar brand or aggregate
            ad_ann = ad_annotations.get("LUXY Ride") or ad_annotations.get("Blacklane")
            if not ad_ann:
                # Use first available
                ad_ann = next(iter(ad_annotations.values()), None)
            if not ad_ann:
                no_match += 1
                continue

        # Build review_meta
        review_meta = {
            "rating": rating,
            "helpful_vote": 0,
            "total_vote": 0,
            "text": text,
            "category": "Luxury Transportation",
            "timestamp": 0,
        }

        try:
            edge_props = compute_brand_buyer_edge(
                ad_annotation=ad_ann,
                user_annotation=user_ann,
                review_meta=review_meta,
            )
            edge_props["_review_id"] = review_id
            edge_props["_company"] = company
            edge_props["_ad_brand"] = ad_ann.get("brand_name", "Unknown")
            edges.append(edge_props)
        except Exception as e:
            logger.warning(f"Edge computation failed for review {review_id}: {e}")

    print(f"Computed {len(edges)} bilateral edges ({no_match} no ad match)", flush=True)

    # Stats
    if edges:
        print("\nEdge dimension means:", flush=True)
        for dim in ["regulatory_fit_score", "construal_fit_score",
                     "personality_brand_alignment", "emotional_resonance",
                     "value_alignment", "composite_alignment"]:
            vals = [e.get(dim, 0) for e in edges]
            if vals:
                avg = sum(vals) / len(vals)
                print(f"  {dim}: {avg:.4f}", flush=True)

        outcomes = Counter(e.get("outcome", "?") for e in edges)
        print(f"\nOutcome distribution: {dict(outcomes)}", flush=True)

    # Save
    with open(EDGES_OUTPUT, "w") as f:
        json.dump({"total": len(edges), "edges": edges}, f, indent=2)
    print(f"Saved to {EDGES_OUTPUT}", flush=True)

    return edges


# =============================================================================
# PHASE 4: WRITE TO NEO4J
# =============================================================================

def run_phase4(ad_annotations: dict, user_annotations: list, edges: list):
    """Phase 4: Write everything to Neo4j."""
    print("\n" + "=" * 60, flush=True)
    print("PHASE 4: WRITE TO NEO4J", flush=True)
    print("=" * 60, flush=True)

    from neo4j import GraphDatabase

    uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
    user = os.environ.get("NEO4J_USERNAME", "neo4j")
    pw = os.environ.get("NEO4J_PASSWORD", "")
    if not pw:
        with open(Path(__file__).parent.parent / ".env") as f:
            for line in f:
                if line.startswith("NEO4J_PASSWORD="):
                    pw = line.strip().split("=", 1)[1]
                elif line.startswith("NEO4J_URI="):
                    uri = line.strip().split("=", 1)[1]

    driver = GraphDatabase.driver(uri, auth=(user, pw))

    with driver.session() as session:
        # Clean up old luxury_transportation edges
        print("Cleaning old luxury_transportation edges...", flush=True)
        session.run(
            "MATCH (ar:AnnotatedReview {category: 'luxury_transportation'})"
            "-[bc:BRAND_CONVERTED]->() DELETE bc"
        )
        session.run(
            "MATCH (ar:AnnotatedReview {category: 'luxury_transportation'}) "
            "DETACH DELETE ar"
        )
        session.run(
            "MATCH (pd:ProductDescription {category: 'luxury_transportation'}) "
            "DETACH DELETE pd"
        )
        print("Cleaned", flush=True)

        # Create ProductDescription nodes with full ad-side dims
        for brand_name, ad_ann in ad_annotations.items():
            asin = ad_ann.get("asin", f"lux_{brand_name.lower()}")
            props = {k: v for k, v in ad_ann.items()
                     if k.startswith("ad_") and isinstance(v, (int, float))}
            props["title"] = f"{brand_name} - Luxury Car Service"
            props["main_category"] = "Luxury Transportation"
            props["annotation_confidence"] = ad_ann.get("annotation_confidence", 0.5)
            props["annotation_tier"] = "claude"

            session.run(
                "MERGE (pd:ProductDescription {asin: $asin}) "
                "SET pd += $props, pd.name = $name, "
                "pd.category = 'luxury_transportation', "
                "pd.last_updated = datetime()",
                asin=asin, name=brand_name, props=props,
            )

            # Link to category
            session.run(
                "MATCH (pd:ProductDescription {asin: $asin}) "
                "MATCH (pc:ProductCategory {name: 'luxury_transportation'}) "
                "MERGE (pd)-[:IN_CATEGORY]->(pc)",
                asin=asin,
            )
        print(f"Created {len(ad_annotations)} ProductDescription nodes", flush=True)

        # Create AnnotatedReview nodes with full user-side dims
        batch_size = 200
        for i in range(0, len(user_annotations), batch_size):
            batch = user_annotations[i:i + batch_size]
            rows = []
            for u in batch:
                review_id = f"lux_bilateral_{u['_review_id']}"
                props = {k: v for k, v in u.items()
                         if k.startswith("user_") and isinstance(v, (int, float))}
                props.update({k: v for k, v in u.items()
                              if k.startswith("peer_ad_") and isinstance(v, (int, float))})
                rows.append({
                    "review_id": review_id,
                    "company": u.get("_company", "Unknown"),
                    "rating": u.get("_rating", 3),
                    "confidence": u.get("annotation_confidence", 0.5),
                    "props": props,
                })

            session.run(
                "UNWIND $rows AS r "
                "MERGE (ar:AnnotatedReview {id: r.review_id}) "
                "SET ar += r.props, ar.company = r.company, "
                "ar.rating = r.rating, "
                "ar.category = 'luxury_transportation', "
                "ar.annotation_confidence = r.confidence, "
                "ar.annotation_tier = 'claude'",
                rows=rows,
            )
            print(f"  Reviews: {min(i + batch_size, len(user_annotations))}/{len(user_annotations)}", flush=True)

        # Create BRAND_CONVERTED edges with bilateral alignment
        for i in range(0, len(edges), batch_size):
            batch = edges[i:i + batch_size]
            rows = []
            for e in batch:
                review_id = f"lux_bilateral_{e['_review_id']}"
                company = e.get("_company", "Unknown")
                ad_brand = e.get("_ad_brand", company)
                ad_asin = f"lux_{ad_brand.lower().replace(' ', '_')}"

                # Edge properties (all 27 alignment dims + metadata)
                edge_props = {k: v for k, v in e.items()
                              if not k.startswith("_") and isinstance(v, (int, float, str))}

                rows.append({
                    "review_id": review_id,
                    "ad_asin": ad_asin,
                    "edge_props": edge_props,
                })

            session.run(
                "UNWIND $rows AS r "
                "MATCH (pd:ProductDescription {asin: r.ad_asin}) "
                "MATCH (ar:AnnotatedReview {id: r.review_id}) "
                "MERGE (pd)-[bc:BRAND_CONVERTED]->(ar) "
                "SET bc += r.edge_props",
                rows=rows,
            )
            print(f"  Edges: {min(i + batch_size, len(edges))}/{len(edges)}", flush=True)

        # Summary
        result = session.run(
            "MATCH (pd:ProductDescription {category: 'luxury_transportation'})"
            "-[bc:BRAND_CONVERTED]->(ar:AnnotatedReview) "
            "RETURN count(bc) as edges, count(DISTINCT pd) as brands, "
            "count(DISTINCT ar) as reviews"
        )
        rec = result.single()
        print(f"\nNeo4j Final State:", flush=True)
        print(f"  BRAND_CONVERTED edges: {rec['edges']}", flush=True)
        print(f"  ProductDescription nodes: {rec['brands']}", flush=True)
        print(f"  AnnotatedReview nodes: {rec['reviews']}", flush=True)

    driver.close()
    print("Done!", flush=True)


# =============================================================================
# MAIN
# =============================================================================

def main():
    client = get_client()

    # Quick API test
    try:
        r = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=10,
            messages=[{"role": "user", "content": "Say ok"}],
        )
        print(f"API test: {r.content[0].text}", flush=True)
    except Exception as e:
        print(f"API test failed: {e}", flush=True)
        return

    # Phase 1: Ad-side
    ad_annotations = run_phase1(client)

    # Phase 2: User-side (this is the big one — 1,492 reviews)
    user_annotations = run_phase2(client)

    # Phase 3: Compute edges
    edges = run_phase3(ad_annotations, user_annotations)

    # Phase 4: Write to Neo4j
    run_phase4(ad_annotations, user_annotations, edges)


if __name__ == "__main__":
    main()
