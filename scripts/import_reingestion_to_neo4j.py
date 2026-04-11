#!/usr/bin/env python3
"""
IMPORT RE-INGESTION RESULTS TO NEO4J

This script takes the JSON results from run_full_reingestion.py and
stores them in Neo4j for real-time decision support.

Imports:
1. Persuasive templates (from high-helpful-vote reviews)
2. Effectiveness matrices (archetype → mechanism success rates)
3. Journey patterns (from bought_together data)

Usage:
    python scripts/import_reingestion_to_neo4j.py

Or import specific category:
    python scripts/import_reingestion_to_neo4j.py --category All_Beauty
"""

import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from adam.infrastructure.neo4j.pattern_persistence import (
    get_pattern_persistence,
    PersuasiveTemplateData,
    EffectivenessData,
    JourneyData,
    PatternSource,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# =============================================================================
# CONFIGURATION
# =============================================================================

OUTPUT_DIR = Path("data/reingestion_output")
MULTI_DATASET_DIR = Path(__file__).resolve().parent.parent / "data" / "multi_dataset_output"
GOOGLE_RESULT_FILE = MULTI_DATASET_DIR / "google_local_result.json"

NDF_DIMS = [
    "approach_avoidance", "temporal_horizon", "social_calibration",
    "uncertainty_tolerance", "status_sensitivity", "cognitive_engagement", "arousal_seeking",
]


# =============================================================================
# IMPORT FUNCTIONS
# =============================================================================

async def import_category_results(
    category: str,
    result_file: Path,
) -> Dict[str, int]:
    """
    Import results from a single category.
    
    Returns counts of imported items.
    """
    counts = {
        "templates": 0,
        "effectiveness": 0,
        "journeys": 0,
    }
    
    if not result_file.exists():
        logger.warning(f"Result file not found: {result_file}")
        return counts
    
    logger.info(f"Importing {category}...")
    
    with open(result_file, "r") as f:
        data = json.load(f)
    
    persistence = get_pattern_persistence()
    
    # 1. Import templates
    templates_data = data.get("templates", [])
    if templates_data:
        templates = [
            PersuasiveTemplateData(
                pattern=t["pattern"],
                mechanism=t["mechanisms"][0] if t["mechanisms"] else "unknown",
                archetype=t["archetype"],
                category=category,
                helpful_votes=t["helpful_votes"],
                occurrence_count=1,
            )
            for t in templates_data
            if t.get("pattern") and t.get("mechanisms")
        ]
        
        if templates:
            counts["templates"] = await persistence.store_templates(
                templates,
                source=PatternSource.REVIEW_INGESTION,
            )
    
    # 2. Import effectiveness matrix
    effectiveness_data = data.get("effectiveness_matrix", {})
    if effectiveness_data:
        counts["effectiveness"] = await persistence.store_effectiveness_matrix(
            effectiveness_data,
            category=category,
        )
    
    # 3. Import product ad profiles (POST-INGESTION Phase 1)
    # Creates ProductAdProfile nodes with persuasion/emotion/value/style
    ad_profiles = data.get("product_ad_profiles", {})
    if not ad_profiles:
        ad_profiles = data.get("product_ad_profiles_sample", {})
    if ad_profiles:
        counts["product_ad_profiles"] = await import_product_ad_profiles(
            ad_profiles, category, persistence
        )
    
    # 4. Import product archetype profiles (POST-INGESTION Phase 1)
    # Creates ProductArchetypeProfile nodes linking products → archetypes
    archetype_profiles = data.get("product_archetype_profiles", {})
    if archetype_profiles:
        counts["product_archetype_profiles"] = await import_product_archetype_profiles(
            archetype_profiles, category, persistence
        )
    
    # 5. Import NDF population data (Nonconscious Decision Fingerprint)
    # Creates NDFProfile nodes per archetype with 7 nonconscious decision dimensions
    ndf_pop = data.get("ndf_population")
    if ndf_pop and ndf_pop.get("ndf_count", 0) > 0:
        counts["ndf_profiles"] = await import_ndf_profiles(
            ndf_pop, category, persistence
        )
    
    logger.info(
        f"  {category}: {counts['templates']} templates, "
        f"{counts['effectiveness']} effectiveness, "
        f"{counts.get('product_ad_profiles', 0)} ad profiles, "
        f"{counts.get('product_archetype_profiles', 0)} archetype profiles, "
        f"{counts.get('ndf_profiles', 0)} NDF profiles"
    )
    
    return counts


async def import_product_ad_profiles(
    profiles: Dict[str, Dict],
    category: str,
    persistence: Any,
) -> int:
    """
    Import product ad profiles to Neo4j as ProductAdProfile nodes.
    
    POST-INGESTION Phase 1: Creates nodes for product-level ad psychology
    enabling queries like:
      MATCH (p:ProductAdProfile {category: 'Electronics'})
      WHERE p.primary_persuasion = 'social_proof'
      RETURN p.asin, p.primary_emotion, p.primary_value
    
    Args:
        profiles: {asin: {primary_persuasion, primary_emotion, primary_value, linguistic_style}}
        category: Category name
        persistence: Pattern persistence service
    
    Returns:
        Number of profiles imported
    """
    if not profiles:
        return 0
    
    count = 0
    batch = []
    
    for asin, prof in profiles.items():
        batch.append({
            "asin": asin,
            "category": category,
            "primary_persuasion": prof.get("primary_persuasion", ""),
            "primary_emotion": prof.get("primary_emotion", ""),
            "primary_value": prof.get("primary_value", ""),
            "linguistic_style": prof.get("linguistic_style", ""),
        })
        
        if len(batch) >= 500:
            imported = await _store_ad_profile_batch(batch, persistence)
            count += imported
            batch = []
    
    if batch:
        imported = await _store_ad_profile_batch(batch, persistence)
        count += imported
    
    return count


async def _store_ad_profile_batch(batch: List[Dict], persistence: Any) -> int:
    """Store a batch of product ad profiles in Neo4j."""
    try:
        if hasattr(persistence, "store_product_ad_profiles"):
            return await persistence.store_product_ad_profiles(batch)
        
        # Fallback: direct Cypher if method not available yet
        if hasattr(persistence, "_driver") and persistence._driver:
            async with persistence._driver.session() as session:
                result = await session.run(
                    """
                    UNWIND $batch AS prof
                    MERGE (p:ProductAdProfile {asin: prof.asin})
                    SET p.category = prof.category,
                        p.primary_persuasion = prof.primary_persuasion,
                        p.primary_emotion = prof.primary_emotion,
                        p.primary_value = prof.primary_value,
                        p.linguistic_style = prof.linguistic_style,
                        p.updated_at = datetime()
                    RETURN count(p) AS cnt
                    """,
                    batch=batch,
                )
                record = await result.single()
                return record["cnt"] if record else 0
        
        return 0
    except Exception as e:
        logger.warning(f"Failed to store ad profiles batch: {e}")
        return 0


async def import_product_archetype_profiles(
    profiles: Dict[str, Dict],
    category: str,
    persistence: Any,
) -> int:
    """
    Import product archetype profiles to Neo4j.
    
    POST-INGESTION Phase 1: Creates edges from products to archetypes
    based on which customer archetypes purchase/review which products.
    
    Enables cross-domain transfer queries:
      MATCH (p:ProductArchetypeProfile)-[:ATTRACTS]->(a:Archetype)
      WHERE p.category = 'Electronics'
      RETURN a.name, count(p), avg(p.affinity)
    
    Args:
        profiles: {asin: {archetype: score, ...}}
        category: Category name
        persistence: Pattern persistence service
    
    Returns:
        Number of profiles imported
    """
    if not profiles:
        return 0
    
    count = 0
    batch = []
    
    for asin, archetypes in profiles.items():
        if not isinstance(archetypes, dict):
            continue
        for archetype, score in archetypes.items():
            batch.append({
                "asin": asin,
                "category": category,
                "archetype": archetype,
                "affinity": float(score) if isinstance(score, (int, float)) else 0.5,
            })
        
        if len(batch) >= 1000:
            imported = await _store_archetype_profile_batch(batch, persistence)
            count += imported
            batch = []
    
    if batch:
        imported = await _store_archetype_profile_batch(batch, persistence)
        count += imported
    
    return count


async def _store_archetype_profile_batch(batch: List[Dict], persistence: Any) -> int:
    """Store a batch of product archetype profiles in Neo4j."""
    try:
        if hasattr(persistence, "store_product_archetype_profiles"):
            return await persistence.store_product_archetype_profiles(batch)
        
        # Fallback: direct Cypher
        if hasattr(persistence, "_driver") and persistence._driver:
            async with persistence._driver.session() as session:
                result = await session.run(
                    """
                    UNWIND $batch AS prof
                    MERGE (p:ProductArchetypeProfile {asin: prof.asin, archetype: prof.archetype})
                    SET p.category = prof.category,
                        p.affinity = prof.affinity,
                        p.updated_at = datetime()
                    RETURN count(p) AS cnt
                    """,
                    batch=batch,
                )
                record = await result.single()
                return record["cnt"] if record else 0
        
        return 0
    except Exception as e:
        logger.warning(f"Failed to store archetype profiles batch: {e}")
        return 0


async def import_ndf_profiles(
    ndf_data: Dict,
    category: str,
    persistence: Any,
) -> int:
    """
    Import NDF (Nonconscious Decision Fingerprint) archetype profiles to Neo4j.
    
    Creates NDFArchetypeProfile nodes that store the 7 nonconscious decision
    dimensions for each archetype as observed in this category. This enables
    queries like:
      MATCH (n:NDFArchetypeProfile {archetype: 'caregiver'})
      RETURN n.approach_avoidance, n.social_calibration, n.category
    
    Also creates a category-level NDFPopulation node with aggregate stats.
    """
    count = 0
    
    try:
        driver = getattr(persistence, "_driver", None)
        if not driver:
            logger.debug("No Neo4j driver available for NDF import")
            return 0
        
        async with driver.session() as session:
            # 1. Store category-level NDF population stats
            ndf_means = ndf_data.get("ndf_means", {})
            ndf_stds = ndf_data.get("ndf_stds", {})
            ndf_count = ndf_data.get("ndf_count", 0)
            
            await session.run(
                """
                MERGE (n:NDFPopulation {category: $category})
                SET n.ndf_count = $ndf_count,
                    n.approach_avoidance_mean = $aa_mean,
                    n.approach_avoidance_std = $aa_std,
                    n.temporal_horizon_mean = $th_mean,
                    n.temporal_horizon_std = $th_std,
                    n.social_calibration_mean = $sc_mean,
                    n.social_calibration_std = $sc_std,
                    n.uncertainty_tolerance_mean = $ut_mean,
                    n.uncertainty_tolerance_std = $ut_std,
                    n.status_sensitivity_mean = $ss_mean,
                    n.status_sensitivity_std = $ss_std,
                    n.cognitive_engagement_mean = $ce_mean,
                    n.cognitive_engagement_std = $ce_std,
                    n.arousal_seeking_mean = $as_mean,
                    n.arousal_seeking_std = $as_std,
                    n.updated_at = datetime()
                RETURN count(n) AS cnt
                """,
                category=category,
                ndf_count=ndf_count,
                aa_mean=ndf_means.get("approach_avoidance", 0.0),
                aa_std=ndf_stds.get("approach_avoidance", 0.0),
                th_mean=ndf_means.get("temporal_horizon", 0.0),
                th_std=ndf_stds.get("temporal_horizon", 0.0),
                sc_mean=ndf_means.get("social_calibration", 0.0),
                sc_std=ndf_stds.get("social_calibration", 0.0),
                ut_mean=ndf_means.get("uncertainty_tolerance", 0.0),
                ut_std=ndf_stds.get("uncertainty_tolerance", 0.0),
                ss_mean=ndf_means.get("status_sensitivity", 0.0),
                ss_std=ndf_stds.get("status_sensitivity", 0.0),
                ce_mean=ndf_means.get("cognitive_engagement", 0.0),
                ce_std=ndf_stds.get("cognitive_engagement", 0.0),
                as_mean=ndf_means.get("arousal_seeking", 0.0),
                as_std=ndf_stds.get("arousal_seeking", 0.0),
            )
            count += 1
            
            # 2. Store archetype-conditioned NDF profiles
            arch_profiles = ndf_data.get("ndf_archetype_profiles", {})
            if arch_profiles:
                batch = []
                for archetype, profile in arch_profiles.items():
                    arch_count = profile.get("count", 0)
                    if arch_count < 10:
                        continue
                    batch.append({
                        "category": category,
                        "archetype": archetype,
                        "arch_count": arch_count,
                        "approach_avoidance": profile.get("approach_avoidance", 0.0),
                        "temporal_horizon": profile.get("temporal_horizon", 0.0),
                        "social_calibration": profile.get("social_calibration", 0.0),
                        "uncertainty_tolerance": profile.get("uncertainty_tolerance", 0.0),
                        "status_sensitivity": profile.get("status_sensitivity", 0.0),
                        "cognitive_engagement": profile.get("cognitive_engagement", 0.0),
                        "arousal_seeking": profile.get("arousal_seeking", 0.0),
                    })
                
                if batch:
                    result = await session.run(
                        """
                        UNWIND $batch AS prof
                        MERGE (n:NDFArchetypeProfile {category: prof.category, archetype: prof.archetype})
                        SET n.ndf_count = prof.arch_count,
                            n.approach_avoidance = prof.approach_avoidance,
                            n.temporal_horizon = prof.temporal_horizon,
                            n.social_calibration = prof.social_calibration,
                            n.uncertainty_tolerance = prof.uncertainty_tolerance,
                            n.status_sensitivity = prof.status_sensitivity,
                            n.cognitive_engagement = prof.cognitive_engagement,
                            n.arousal_seeking = prof.arousal_seeking,
                            n.updated_at = datetime()
                        RETURN count(n) AS cnt
                        """,
                        batch=batch,
                    )
                    record = await result.single()
                    count += record["cnt"] if record else 0
    
    except Exception as e:
        logger.warning(f"Failed to import NDF profiles for {category}: {e}")
    
    return count


async def import_google_hyperlocal_to_neo4j() -> Dict[str, int]:
    """
    Import Google Local state and vertical NDF profiles to Neo4j for graph queries.
    
    Creates:
    - (:StateNDFProfile {state, approach_avoidance, temporal_horizon, ...}) per state
    - (:VerticalNDFProfile {vertical, approach_avoidance, ...}) per ad vertical
    
    Enables queries like:
      MATCH (s:StateNDFProfile {state: 'California'}), (v:VerticalNDFProfile {vertical: 'dining'})
      RETURN s.social_calibration, v.temporal_horizon
    
    Reads from data/multi_dataset_output/google_local_result.json (specific_intelligence).
    """
    counts = {"state_ndf_profiles": 0, "vertical_ndf_profiles": 0}
    
    if not GOOGLE_RESULT_FILE.exists():
        logger.warning(f"Google result file not found: {GOOGLE_RESULT_FILE}. Skip Google hyperlocal import.")
        return counts
    
    try:
        with open(GOOGLE_RESULT_FILE, "r") as f:
            data = json.load(f)
    except Exception as e:
        logger.warning(f"Failed to load Google result: {e}")
        return counts
    
    spec = data.get("specific_intelligence", {})
    state_profs = spec.get("state_ndf_profiles", {})
    vertical_profs = spec.get("vertical_ndf_profiles", {})
    
    if not state_profs and not vertical_profs:
        logger.info("No state or vertical NDF profiles in Google result. Skip.")
        return counts
    
    from adam.infrastructure.neo4j.client import get_neo4j_client
    
    client = get_neo4j_client()
    if not client.is_connected:
        await client.connect()
    if not client.driver:
        logger.warning("Neo4j driver not available. Skip Google hyperlocal import.")
        return counts
    
    async with await client.session() as session:
        # Schema for Google hyperlocal nodes
        try:
            await session.run(
                "CREATE INDEX state_ndf_state IF NOT EXISTS FOR (s:StateNDFProfile) ON (s.state)"
            )
            await session.run(
                "CREATE INDEX vertical_ndf_vertical IF NOT EXISTS FOR (v:VerticalNDFProfile) ON (v.vertical)"
            )
        except Exception as e:
            if "equivalent" not in str(e).lower() and "already exists" not in str(e).lower():
                logger.warning(f"Schema creation for Google NDF: {e}")
        
        def _dims_from_profile(prof: Dict) -> Dict[str, float]:
            if not isinstance(prof, dict):
                return {}
            means = prof.get("ndf_means", {})
            if means:
                return {d: float(means.get(d, 0.0)) for d in NDF_DIMS}
            return {d: float(prof.get(d, 0.0)) for d in NDF_DIMS}
        
        # 1. State NDF profiles
        if state_profs:
            batch = []
            for state_name, prof in state_profs.items():
                dims = _dims_from_profile(prof)
                if not dims:
                    continue
                batch.append({
                    "state": state_name,
                    **dims,
                })
            if batch:
                result = await session.run(
                    """
                    UNWIND $batch AS row
                    MERGE (s:StateNDFProfile {state: row.state})
                    SET s.approach_avoidance = row.approach_avoidance,
                        s.temporal_horizon = row.temporal_horizon,
                        s.social_calibration = row.social_calibration,
                        s.uncertainty_tolerance = row.uncertainty_tolerance,
                        s.status_sensitivity = row.status_sensitivity,
                        s.cognitive_engagement = row.cognitive_engagement,
                        s.arousal_seeking = row.arousal_seeking,
                        s.source = 'google_local_ingestion'
                    RETURN count(s) AS cnt
                    """,
                    batch=batch,
                )
                record = await result.single()
                counts["state_ndf_profiles"] = record["cnt"] if record else len(batch)
                logger.info(f"  State NDF profiles: {counts['state_ndf_profiles']} states")
        
        # 2. Vertical NDF profiles
        if vertical_profs:
            batch = []
            for vertical_name, prof in vertical_profs.items():
                dims = _dims_from_profile(prof)
                if not dims:
                    continue
                batch.append({
                    "vertical": vertical_name,
                    **dims,
                })
            if batch:
                result = await session.run(
                    """
                    UNWIND $batch AS row
                    MERGE (v:VerticalNDFProfile {vertical: row.vertical})
                    SET v.approach_avoidance = row.approach_avoidance,
                        v.temporal_horizon = row.temporal_horizon,
                        v.social_calibration = row.social_calibration,
                        v.uncertainty_tolerance = row.uncertainty_tolerance,
                        v.status_sensitivity = row.status_sensitivity,
                        v.cognitive_engagement = row.cognitive_engagement,
                        v.arousal_seeking = row.arousal_seeking,
                        v.source = 'google_local_ingestion'
                    RETURN count(v) AS cnt
                    """,
                    batch=batch,
                )
                record = await result.single()
                counts["vertical_ndf_profiles"] = record["cnt"] if record else len(batch)
                logger.info(f"  Vertical NDF profiles: {counts['vertical_ndf_profiles']} verticals")
    
    return counts


async def import_all_results() -> Dict[str, int]:
    """
    Import all category results.
    
    Returns total counts.
    """
    totals = {
        "templates": 0,
        "effectiveness": 0,
        "journeys": 0,
        "categories": 0,
        "product_ad_profiles": 0,
        "product_archetype_profiles": 0,
    }
    
    # Find all result files
    result_files = list(OUTPUT_DIR.glob("*_result.json"))
    
    # Exclude TOTAL summary
    result_files = [f for f in result_files if "TOTAL" not in f.name]
    
    logger.info(f"Found {len(result_files)} category result files")
    
    for result_file in sorted(result_files):
        category = result_file.stem.replace("_result", "")
        
        try:
            counts = await import_category_results(category, result_file)
            
            totals["templates"] += counts["templates"]
            totals["effectiveness"] += counts["effectiveness"]
            totals["journeys"] += counts.get("journeys", 0)
            totals["product_ad_profiles"] += counts.get("product_ad_profiles", 0)
            totals["product_archetype_profiles"] += counts.get("product_archetype_profiles", 0)
            totals["categories"] += 1
            
        except Exception as e:
            logger.error(f"Failed to import {category}: {e}")
    
    return totals


async def import_journey_patterns(
    categories: Optional[List[str]] = None,
    batch_size: int = 10000,
) -> Dict[str, int]:
    """
    Import journey patterns from bought_together data in metadata files.
    
    Reads the meta_*.jsonl files and extracts co-purchase relationships
    to create BOUGHT_WITH relationships in Neo4j.
    
    Args:
        categories: List of categories to process (None = all completed)
        batch_size: Number of records per batch
        
    Returns:
        Dict with counts: journey_patterns, products, edges_total
    """
    import gzip
    
    from adam.intelligence.amazon_data_registry import (
        AmazonCategory,
        get_category_files,
        get_available_categories,
        AMAZON_DATA_DIR,
    )
    from adam.intelligence.journey_intelligence import (
        JourneyIntelligenceService,
        JourneyEdge,
    )
    
    totals = {
        "journey_patterns": 0,
        "products": 0,
        "edges_total": 0,
        "categories_processed": 0,
    }
    
    # Determine which categories to process
    if categories:
        category_list = [AmazonCategory(c) for c in categories]
    else:
        # Use categories that have completed re-ingestion
        result_files = list(OUTPUT_DIR.glob("*_result.json"))
        result_files = [f for f in result_files if "TOTAL" not in f.name]
        category_list = []
        for f in result_files:
            cat_name = f.stem.replace("_result", "")
            try:
                category_list.append(AmazonCategory(cat_name))
            except ValueError:
                logger.warning(f"Unknown category: {cat_name}")
    
    logger.info(f"Processing journey patterns for {len(category_list)} categories")
    
    # Create journey service
    journey_service = JourneyIntelligenceService()
    
    # Process each category's metadata
    for category in category_list:
        files = get_category_files(category)
        
        if not files.meta_path.exists():
            logger.warning(f"Meta file not found for {category.value}")
            continue
        
        logger.info(f"Processing journeys for {category.value}...")
        
        # Read metadata file
        meta_path = files.meta_path
        opener = gzip.open if str(meta_path).endswith('.gz') else open
        
        batch = []
        edges_for_category = 0
        products_for_category = 0
        
        try:
            with opener(meta_path, 'rt', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    try:
                        record = json.loads(line)
                        
                        # Only process records with bought_together data
                        bought_together = record.get("bought_together", [])
                        if bought_together:
                            batch.append(record)
                        
                        # Process batch
                        if len(batch) >= batch_size:
                            edges = journey_service.add_journey_edges_from_metadata(
                                batch, 
                                category=category.value
                            )
                            edges_for_category += edges
                            products_for_category += len(batch)
                            batch = []
                            
                            if line_num % 100000 == 0:
                                logger.info(
                                    f"  {category.value}: {line_num:,} records, "
                                    f"{edges_for_category:,} edges"
                                )
                    
                    except json.JSONDecodeError:
                        continue
                
                # Process remaining batch
                if batch:
                    edges = journey_service.add_journey_edges_from_metadata(
                        batch,
                        category=category.value
                    )
                    edges_for_category += edges
                    products_for_category += len(batch)
        
        except Exception as e:
            logger.error(f"Failed to process {category.value}: {e}")
            continue
        
        totals["edges_total"] += edges_for_category
        totals["products"] += products_for_category
        totals["categories_processed"] += 1
        
        logger.info(
            f"  {category.value}: {products_for_category:,} products, "
            f"{edges_for_category:,} edges"
        )
    
    # Compute journey metrics
    logger.info("Computing journey metrics...")
    journey_service.compute_journey_metrics()
    
    # Detect clusters
    logger.info("Detecting product clusters...")
    num_clusters = journey_service.detect_clusters(min_size=3)
    logger.info(f"  Found {num_clusters} product clusters")
    
    # Persist to Neo4j
    logger.info("Persisting journey patterns to Neo4j...")
    persist_result = await journey_service.persist_to_graph()
    
    totals["journey_patterns"] = persist_result.get("journey_patterns", 0)
    
    logger.info(
        f"Journey import complete: {totals['journey_patterns']:,} patterns, "
        f"{totals['products']:,} products, {num_clusters} clusters"
    )
    
    return totals


# =============================================================================
# MAIN
# =============================================================================

async def main():
    """Run the import."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Import re-ingestion results to Neo4j")
    parser.add_argument("--category", type=str, help="Import specific category")
    parser.add_argument("--journeys-only", action="store_true", 
                        help="Only import journey patterns (bought_together)")
    parser.add_argument("--include-journeys", action="store_true",
                        help="Include journey patterns in full import")
    parser.add_argument("--skip-journeys", action="store_true",
                        help="Skip journey patterns (default, for faster import)")
    parser.add_argument("--google-hyperlocal", action="store_true",
                        help="Import Google Local state/vertical NDF profiles to Neo4j (from multi_dataset_output)")
    
    args = parser.parse_args()
    
    print("=" * 70)
    print("IMPORT RE-INGESTION RESULTS TO NEO4J")
    print("=" * 70)
    
    # Initialize persistence (creates indexes)
    persistence = get_pattern_persistence()
    await persistence.initialize_schema()
    
    # Google hyperlocal only (state/vertical NDF from Google Local ingestion)
    if args.google_hyperlocal:
        print("\nImporting Google hyperlocal (state + vertical NDF) to Neo4j...")
        persistence = get_pattern_persistence()
        await persistence.initialize_schema()
        counts = await import_google_hyperlocal_to_neo4j()
        print("\n" + "=" * 70)
        print("GOOGLE HYPERLOCAL IMPORT COMPLETE")
        print("=" * 70)
        print(f"State NDF profiles:  {counts['state_ndf_profiles']}")
        print(f"Vertical NDF profiles: {counts['vertical_ndf_profiles']}")
        print("\nQuery example: MATCH (s:StateNDFProfile {state: 'California'}) RETURN s")
        return
    
    # Journey-only mode
    if args.journeys_only:
        print("\nImporting journey patterns only...")
        categories = [args.category] if args.category else None
        journey_totals = await import_journey_patterns(categories=categories)
        
        print("\n" + "=" * 70)
        print("JOURNEY IMPORT COMPLETE")
        print("=" * 70)
        print(f"Categories: {journey_totals['categories_processed']}")
        print(f"Products with journeys: {journey_totals['products']:,}")
        print(f"Journey edges: {journey_totals['edges_total']:,}")
        print(f"Patterns stored: {journey_totals['journey_patterns']:,}")
        print("\nJourney data is now available in Neo4j!")
        return
    
    # Single category mode
    if args.category:
        result_file = OUTPUT_DIR / f"{args.category}_result.json"
        counts = await import_category_results(args.category, result_file)
        
        print(f"\n{args.category} Import Complete:")
        print(f"  Templates: {counts['templates']}")
        print(f"  Effectiveness: {counts['effectiveness']}")
        
        # Optionally include journeys
        if args.include_journeys:
            print("\nImporting journey patterns...")
            journey_totals = await import_journey_patterns(categories=[args.category])
            print(f"  Journey patterns: {journey_totals['journey_patterns']:,}")
        
        print("\nData is now available in Neo4j!")
        return
    
    # Full import mode
    totals = await import_all_results()
    
    print("\n" + "=" * 70)
    print("TEMPLATE & EFFECTIVENESS IMPORT COMPLETE")
    print("=" * 70)
    print(f"Categories: {totals['categories']}")
    print(f"Templates: {totals['templates']:,}")
    print(f"Effectiveness Records: {totals['effectiveness']:,}")
    print(f"Product Ad Profiles: {totals['product_ad_profiles']:,}")
    print(f"Product Archetype Profiles: {totals['product_archetype_profiles']:,}")
    
    # Include journeys if requested
    if args.include_journeys:
        print("\n" + "=" * 70)
        print("IMPORTING JOURNEY PATTERNS")
        print("=" * 70)
        journey_totals = await import_journey_patterns()
        
        print("\n" + "=" * 70)
        print("JOURNEY IMPORT COMPLETE")
        print("=" * 70)
        print(f"Products with journeys: {journey_totals['products']:,}")
        print(f"Journey edges: {journey_totals['edges_total']:,}")
        print(f"Patterns stored: {journey_totals['journey_patterns']:,}")
    else:
        print("\n[Tip: Run with --include-journeys or --journeys-only for bought_together data]")
    
    # Optionally import Google hyperlocal if result file exists (state/vertical NDF for graph queries)
    if GOOGLE_RESULT_FILE.exists():
        print("\nImporting Google hyperlocal (state + vertical NDF)...")
        gh_counts = await import_google_hyperlocal_to_neo4j()
        print(f"  State NDF: {gh_counts['state_ndf_profiles']}, Vertical NDF: {gh_counts['vertical_ndf_profiles']}")
    
    print("\nData is now available in Neo4j for real-time queries!")


if __name__ == "__main__":
    asyncio.run(main())
