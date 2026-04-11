#!/usr/bin/env python3
"""
MERGE INGESTION PRIORS
======================

Reads ALL result files from both Amazon unified ingestion and multi-dataset
ingestion, and produces a single comprehensive priors file:

    data/learning/ingestion_merged_priors.json

This is the SINGLE source of truth for all ingestion-derived priors
consumed by:
  - LearnedPriorsService (atom intelligence)
  - Thompson Sampling warm-start (Beta distribution initialization)
  - ColdStartService (population base rates)
  - AtomIntelligenceInjector (per-atom context)
  - Neo4j graph import (effectiveness edges)
  - ML Weak Supervisor (training label generation)

Usage:
    python3 scripts/merge_ingestion_priors.py

Output:
    data/learning/ingestion_merged_priors.json
"""

import json
import logging
import sys
from collections import defaultdict
from pathlib import Path
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# =============================================================================
# PATHS
# =============================================================================

BASE_DIR = Path(__file__).resolve().parent.parent
AMAZON_OUTPUT_DIR = BASE_DIR / "data" / "reingestion_output"
MULTI_DATASET_DIR = BASE_DIR / "data" / "multi_dataset_output"
OUTPUT_PATH = BASE_DIR / "data" / "learning" / "ingestion_merged_priors.json"


def load_amazon_results() -> list:
    """Load all Amazon *_result.json files."""
    results = []
    if not AMAZON_OUTPUT_DIR.exists():
        logger.warning(f"Amazon output directory not found: {AMAZON_OUTPUT_DIR}")
        return results

    for path in sorted(AMAZON_OUTPUT_DIR.glob("*_result.json")):
        try:
            with open(path) as f:
                data = json.load(f)
            data["_source_file"] = path.name
            data["_source_type"] = "amazon"
            results.append(data)
            logger.info(f"  Loaded: {path.name} ({data.get('reviews_processed', 0):,} reviews)")
        except Exception as e:
            logger.warning(f"  Failed to load {path.name}: {e}")

    return results


def load_multi_dataset_results() -> list:
    """Load all multi-dataset *_result.json files."""
    results = []
    if not MULTI_DATASET_DIR.exists():
        logger.warning(f"Multi-dataset directory not found: {MULTI_DATASET_DIR}")
        return results

    for path in sorted(MULTI_DATASET_DIR.glob("*_result.json")):
        if path.name == "SUMMARY.json":
            continue
        try:
            with open(path) as f:
                data = json.load(f)
            data["_source_file"] = path.name
            data["_source_type"] = "multi_dataset"
            results.append(data)
            name = data.get("name", data.get("category", path.stem))
            reviews = data.get("reviews_processed", data.get("total_reviews", 0))
            logger.info(f"  Loaded: {path.name} ({name}, {reviews:,} reviews)")
        except Exception as e:
            logger.warning(f"  Failed to load {path.name}: {e}")

    return results


def merge_effectiveness_matrices(amazon_results: list) -> dict:
    """
    Merge effectiveness matrices from all Amazon categories.
    
    Produces:
    {
        archetype: {
            mechanism: {
                "success_rate": weighted_avg,
                "sample_size": total_samples,
                "categories_seen": count
            }
        }
    }
    """
    merged = defaultdict(lambda: defaultdict(lambda: {"total_success": 0, "total_samples": 0, "categories": 0}))

    for result in amazon_results:
        matrix = result.get("effectiveness_matrix", {})
        for archetype, mechanisms in matrix.items():
            for mechanism, stats in mechanisms.items():
                sr = stats.get("success_rate", 0)
                ss = stats.get("sample_size", 0)
                if ss > 0:
                    merged[archetype][mechanism]["total_success"] += sr * ss
                    merged[archetype][mechanism]["total_samples"] += ss
                    merged[archetype][mechanism]["categories"] += 1

    # Compute weighted averages
    output = {}
    for archetype, mechanisms in merged.items():
        output[archetype] = {}
        for mechanism, stats in mechanisms.items():
            if stats["total_samples"] > 0:
                output[archetype][mechanism] = {
                    "success_rate": stats["total_success"] / stats["total_samples"],
                    "sample_size": stats["total_samples"],
                    "categories_seen": stats["categories"],
                }

    return output


def merge_archetype_distributions(all_results: list) -> dict:
    """
    Merge archetype distributions across all sources.
    
    Returns:
    {
        "global": {archetype: proportion},
        "by_category": {category: {archetype: proportion}},
        "by_source": {source: {archetype: proportion}}
    }
    """
    global_counts = defaultdict(int)
    by_category = defaultdict(lambda: defaultdict(int))
    by_source = defaultdict(lambda: defaultdict(int))

    for result in all_results:
        dist = result.get("archetype_distribution", {})
        category = result.get("category", result.get("name", "unknown"))
        source = result.get("_source_type", "unknown")

        for archetype, count in dist.items():
            if isinstance(count, (int, float)):
                global_counts[archetype] += count
                by_category[category][archetype] += count
                by_source[source][archetype] += count

    # Normalize to proportions
    def normalize(counts):
        total = sum(counts.values())
        if total == 0:
            return {}
        return {k: v / total for k, v in sorted(counts.items(), key=lambda x: -x[1])}

    return {
        "global": normalize(global_counts),
        "by_category": {cat: normalize(counts) for cat, counts in by_category.items()},
        "by_source": {src: normalize(counts) for src, counts in by_source.items()},
    }


def merge_dimension_distributions(amazon_results: list) -> dict:
    """Merge dimensional distributions from all Amazon categories."""
    merged = defaultdict(lambda: defaultdict(int))

    for result in amazon_results:
        dims = result.get("dimension_distributions", {})
        for dimension_group, distribution in dims.items():
            if isinstance(distribution, dict):
                for value, count in distribution.items():
                    if isinstance(count, (int, float)):
                        merged[dimension_group][value] += count

    # Normalize each dimension group
    output = {}
    for group, counts in merged.items():
        total = sum(counts.values())
        if total > 0:
            output[group] = {k: v / total for k, v in sorted(counts.items(), key=lambda x: -x[1])}

    return output


def merge_ndf_population(all_results: list) -> dict:
    """Merge NDF population data from all sources that have it."""
    all_profiles = []
    archetype_ndf = defaultdict(lambda: defaultdict(list))
    category_ndf = defaultdict(lambda: defaultdict(list))

    ndf_dims = [
        "approach_avoidance", "temporal_horizon", "social_calibration",
        "uncertainty_tolerance", "status_sensitivity",
        "cognitive_engagement", "arousal_seeking",
    ]

    for result in all_results:
        ndf_data = result.get("ndf_population", {})
        category = result.get("category", result.get("name", "unknown"))

        # Category-level NDF averages
        ndf_averages = ndf_data.get("ndf_averages", {})
        if ndf_averages:
            for dim in ndf_dims:
                val = ndf_averages.get(dim)
                if val is not None:
                    category_ndf[category][dim].append(val)

        # Archetype-level NDF profiles
        arch_profiles = ndf_data.get("ndf_archetype_profiles", {})
        for archetype, profile in arch_profiles.items():
            if isinstance(profile, dict):
                for dim in ndf_dims:
                    val = profile.get(dim)
                    if val is not None:
                        archetype_ndf[archetype][dim].append(val)

    # Compute means
    def mean_profile(dim_lists):
        return {dim: sum(vals) / len(vals) for dim, vals in dim_lists.items() if vals}

    return {
        "ndf_by_archetype": {arch: mean_profile(dims) for arch, dims in archetype_ndf.items()},
        "ndf_by_category": {cat: mean_profile(dims) for cat, dims in category_ndf.items()},
        "ndf_dimensions": ndf_dims,
    }


def merge_product_ad_profiles(amazon_results: list) -> dict:
    """Aggregate product ad profile statistics across all categories."""
    technique_counts = defaultdict(int)
    emotion_counts = defaultdict(int)
    value_counts = defaultdict(int)
    style_counts = defaultdict(int)
    category_profiles = {}

    for result in amazon_results:
        category = result.get("category", "unknown")
        profiles = result.get("product_ad_profiles", {})

        cat_tech = defaultdict(int)
        cat_emotion = defaultdict(int)
        cat_value = defaultdict(int)
        cat_style = defaultdict(int)

        for asin, profile in profiles.items():
            if not isinstance(profile, dict):
                continue
            tech = profile.get("primary_persuasion_technique") or profile.get("primary_persuasion")
            emotion = profile.get("primary_emotional_appeal") or profile.get("primary_emotion")
            value = profile.get("primary_value_proposition") or profile.get("primary_value")
            style = profile.get("linguistic_style")

            if tech:
                technique_counts[tech] += 1
                cat_tech[tech] += 1
            if emotion:
                emotion_counts[emotion] += 1
                cat_emotion[emotion] += 1
            if value:
                value_counts[value] += 1
                cat_value[value] += 1
            if style:
                style_counts[style] += 1
                cat_style[style] += 1

        # Category dominant profiles
        if cat_tech:
            category_profiles[category] = {
                "dominant_persuasion": max(cat_tech, key=cat_tech.get),
                "dominant_emotion": max(cat_emotion, key=cat_emotion.get) if cat_emotion else None,
                "dominant_value": max(cat_value, key=cat_value.get) if cat_value else None,
                "dominant_style": max(cat_style, key=cat_style.get) if cat_style else None,
            }

    def normalize(counts):
        total = sum(counts.values())
        return {k: v / total for k, v in sorted(counts.items(), key=lambda x: -x[1])} if total else {}

    return {
        "persuasion_technique_distribution": normalize(technique_counts),
        "emotional_appeal_distribution": normalize(emotion_counts),
        "value_proposition_distribution": normalize(value_counts),
        "linguistic_style_distribution": normalize(style_counts),
        "category_product_profiles": category_profiles,
    }


def merge_category_effectiveness(amazon_results: list) -> dict:
    """Per-category effectiveness matrices for category-specific Thompson warm-start."""
    output = {}
    for result in amazon_results:
        category = result.get("category", "unknown")
        matrix = result.get("effectiveness_matrix", {})
        if matrix:
            output[category] = matrix
    return output


def merge_template_stats(amazon_results: list) -> dict:
    """Template statistics (not full templates — those stay on disk)."""
    total_templates = 0
    mechanism_template_counts = defaultdict(int)
    archetype_template_counts = defaultdict(int)

    for result in amazon_results:
        templates = result.get("templates", [])
        total_templates += len(templates)
        for t in templates:
            for mech in t.get("mechanisms", []):
                mechanism_template_counts[mech] += 1
            arch = t.get("archetype")
            if arch:
                archetype_template_counts[arch] += 1

    return {
        "total_templates": total_templates,
        "templates_by_mechanism": dict(mechanism_template_counts),
        "templates_by_archetype": dict(archetype_template_counts),
    }


def main():
    """Main merge pipeline."""
    logger.info("=" * 60)
    logger.info("ADAM Ingestion Priors Merge Pipeline")
    logger.info("=" * 60)

    # Step 1: Load all results
    logger.info("\n--- Loading Amazon results ---")
    amazon_results = load_amazon_results()
    logger.info(f"Loaded {len(amazon_results)} Amazon category results")

    logger.info("\n--- Loading multi-dataset results ---")
    multi_results = load_multi_dataset_results()
    logger.info(f"Loaded {len(multi_results)} multi-dataset results")

    all_results = amazon_results + multi_results

    if not all_results:
        logger.error("No results found. Exiting.")
        sys.exit(1)

    # Step 2: Compute totals
    total_reviews = sum(
        r.get("reviews_processed", r.get("total_reviews", 0))
        for r in all_results
    )
    total_products = sum(
        r.get("products_linked", r.get("products_processed", 0))
        for r in amazon_results
    )

    logger.info(f"\nTotal reviews across all sources: {total_reviews:,}")
    logger.info(f"Total products linked: {total_products:,}")

    # Step 3: Merge everything
    logger.info("\n--- Merging effectiveness matrices ---")
    effectiveness = merge_effectiveness_matrices(amazon_results)
    logger.info(f"  {len(effectiveness)} archetypes × {max(len(m) for m in effectiveness.values()) if effectiveness else 0} mechanisms")

    logger.info("--- Merging archetype distributions ---")
    archetypes = merge_archetype_distributions(all_results)
    logger.info(f"  Global: {len(archetypes['global'])} archetypes")
    logger.info(f"  Categories: {len(archetypes['by_category'])}")

    logger.info("--- Merging dimension distributions ---")
    dimensions = merge_dimension_distributions(amazon_results)
    logger.info(f"  {len(dimensions)} dimension groups")

    logger.info("--- Merging NDF population data ---")
    ndf = merge_ndf_population(all_results)
    logger.info(f"  NDF by archetype: {len(ndf['ndf_by_archetype'])}")
    logger.info(f"  NDF by category: {len(ndf['ndf_by_category'])}")

    # Build ndf_population in a shape LearnedPriorsService can load (ndf_count, ndf_archetype_profiles, ndf_means)
    ndf_for_runtime = dict(ndf)
    ndf_for_runtime["ndf_archetype_profiles"] = ndf.get("ndf_by_archetype", {})
    ndf_for_runtime["ndf_count"] = total_reviews  # proxy for total NDF observations
    if ndf.get("ndf_by_archetype"):
        # Global ndf_means as average of archetype profiles (for fallback)
        arch_profs = ndf["ndf_by_archetype"]
        dims = ndf.get("ndf_dimensions", ["approach_avoidance", "temporal_horizon", "social_calibration",
                                          "uncertainty_tolerance", "status_sensitivity", "cognitive_engagement", "arousal_seeking"])
        ndf_for_runtime["ndf_means"] = {}
        for d in dims:
            vals = [float(p.get(d)) for p in arch_profs.values() if isinstance(p, dict) and p.get(d) is not None and isinstance(p.get(d), (int, float))]
            ndf_for_runtime["ndf_means"][d] = round(sum(vals) / len(vals), 4) if vals else 0.0
    else:
        ndf_for_runtime["ndf_means"] = {}

    logger.info("--- Extracting Google hyperlocal (state/vertical NDF) ---")
    google_hyperlocal = {}
    for r in multi_results:
        if r.get("name") == "google_local" or (r.get("_source_file") or "").startswith("google"):
            spec = r.get("specific_intelligence", {})
            if spec:
                google_hyperlocal = {
                    "state_ndf_profiles": spec.get("state_ndf_profiles", {}),
                    "category_ndf_profiles": spec.get("category_ndf_profiles", {}),
                    "price_tier_ndf_profiles": spec.get("price_tier_ndf_profiles", {}),
                    "vertical_ndf_profiles": spec.get("vertical_ndf_profiles", {}),
                    "business_response_intelligence": spec.get("business_response_intelligence", {}),
                    "location_profiles": spec.get("location_profiles", {}),
                    "hyperlocal_targeting": spec.get("hyperlocal_targeting", True),
                    "states_processed": spec.get("states_processed", 0),
                }
                logger.info(f"  Google hyperlocal: {len(google_hyperlocal.get('state_ndf_profiles', {}))} states, "
                           f"{len(google_hyperlocal.get('vertical_ndf_profiles', {}))} verticals")
            break

    logger.info("--- Merging product ad profiles ---")
    ad_profiles = merge_product_ad_profiles(amazon_results)
    logger.info(f"  Category profiles: {len(ad_profiles['category_product_profiles'])}")

    logger.info("--- Merging category effectiveness ---")
    cat_effectiveness = merge_category_effectiveness(amazon_results)
    logger.info(f"  {len(cat_effectiveness)} categories with effectiveness data")

    logger.info("--- Merging template statistics ---")
    template_stats = merge_template_stats(amazon_results)
    logger.info(f"  Total templates: {template_stats['total_templates']:,}")

    # Step 4: Assemble output
    merged = {
        "source": "merge_ingestion_priors.py",
        "generated_at": datetime.now().isoformat(),
        "total_reviews_processed": total_reviews,
        "total_products_linked": total_products,
        "amazon_categories": len(amazon_results),
        "multi_dataset_sources": len(multi_results),

        # Core effectiveness (for Thompson warm-start)
        "global_effectiveness_matrix": effectiveness,

        # Per-category effectiveness (for category-specific priors)
        "category_effectiveness_matrices": cat_effectiveness,

        # Archetype distributions (for cold-start + population priors)
        "global_archetype_distribution": archetypes["global"],
        "category_archetype_distributions": archetypes["by_category"],
        "source_archetype_distributions": archetypes["by_source"],

        # Dimensional distributions (for 430+ dimension priors)
        "dimension_distributions": dimensions,

        # NDF population data (for NDF Bayesian updates)
        # Shape includes ndf_by_archetype, ndf_by_category AND ndf_count, ndf_archetype_profiles, ndf_means for LearnedPriorsService
        "ndf_population": ndf_for_runtime,

        # Google hyperlocal (state/vertical/category/price NDF + location profiles) for geo-aware targeting
        "google_hyperlocal": google_hyperlocal,

        # Product ad profile aggregates (for alignment system)
        "product_ad_profile_aggregates": ad_profiles,

        # Category product profiles (for product-level fallback)
        "category_product_profiles": ad_profiles.get("category_product_profiles", {}),

        # Template statistics (metadata only — templates stay on disk)
        "template_statistics": template_stats,

        # Source file inventory
        "source_files": {
            "amazon": [r["_source_file"] for r in amazon_results],
            "multi_dataset": [r["_source_file"] for r in multi_results],
        },
    }

    # Step 5: Write output
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(merged, f, indent=2, default=str)

    file_size_mb = OUTPUT_PATH.stat().st_size / (1024 * 1024)
    logger.info(f"\n{'=' * 60}")
    logger.info(f"Output written to: {OUTPUT_PATH}")
    logger.info(f"File size: {file_size_mb:.1f} MB")
    logger.info(f"{'=' * 60}")

    # Summary
    logger.info("\nMERGE SUMMARY:")
    logger.info(f"  Reviews:           {total_reviews:>15,}")
    logger.info(f"  Products:          {total_products:>15,}")
    logger.info(f"  Amazon categories: {len(amazon_results):>15}")
    logger.info(f"  Other datasets:    {len(multi_results):>15}")
    logger.info(f"  Archetypes:        {len(archetypes['global']):>15}")
    logger.info(f"  Effectiveness:     {sum(len(m) for m in effectiveness.values()):>15} pairs")
    logger.info(f"  Dimensions:        {len(dimensions):>15} groups")
    logger.info(f"  NDF profiles:      {len(ndf['ndf_by_archetype']):>15} archetypes")
    logger.info(f"  Templates:         {template_stats['total_templates']:>15,}")


if __name__ == "__main__":
    main()
