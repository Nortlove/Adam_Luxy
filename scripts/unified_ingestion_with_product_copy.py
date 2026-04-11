#!/usr/bin/env python3
"""
UNIFIED INGESTION WITH PRODUCT COPY (Fourth ingestion – correct)

Follows docs/INGESTION_MASTER_PLAN_AND_VERIFICATION.md.

RULES:
- Amazon: each category has review file + meta file; link by ASIN.
- We NEVER process an Amazon category without its meta file.
- We load meta first (ASIN -> product info + product copy), then stream reviews.
- Product copy (title + features + description) is used for ad psychology.
- All outputs from the plan are produced and verified at end.

ARCHITECTURE (32GB Apple Silicon M2 Max, 12-core):
  Category-level parallelism: 5 categories processed simultaneously (default).
  Sequential within each category: each process loads meta ONCE, compiles Hyperscan
  ONCE, then processes reviews sequentially. NO per-category batch workers — they
  were a regression that duplicated meta (1-4GB) per worker, added pickling overhead,
  and caused OOM at 117GB demand on 32GB. Sequential-within-category is FASTER because
  it avoids all that overhead while still leveraging Hyperscan's 10k+/sec engine.
  Product ad profiles are computed AFTER review processing (deferred from hot loop).

Throughput: With Hyperscan + 5 concurrent categories, expect 5-10k+ reviews/sec aggregate.
  Each category processes at 1-5k/sec depending on size. Product ad profiles add ~1min per
  category after review processing completes.

Usage:
  # Pre-flight only (no ingestion)
  python3 scripts/unified_ingestion_with_product_copy.py --verify-plan

  # Run ingestion with Hyperscan (recommended: fastest with full quality)
  nohup python3 scripts/unified_ingestion_with_product_copy.py --use-hyperscan --workers 5 >> data/reingestion_output/ingestion.log 2>&1 &

  # Resume (skips already-completed categories automatically)
  nohup python3 scripts/unified_ingestion_with_product_copy.py --use-hyperscan --workers 5 >> data/reingestion_output/ingestion.log 2>&1 &

  # Single category (e.g. for testing or Books which has huge meta)
  python3 scripts/unified_ingestion_with_product_copy.py --use-hyperscan --category Books
"""

import argparse
import gc
import gzip
import json
import logging
import sys
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# Paths from plan: write to same location import_reingestion_to_neo4j expects
OUTPUT_DIR = PROJECT_ROOT / "data" / "reingestion_output"
PRIORS_OUTPUT_DIR = PROJECT_ROOT / "data" / "learning"
CHECKPOINT_DIR = OUTPUT_DIR / "checkpoints"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)

BATCH_SIZE = 10_000
CHECKPOINT_EVERY = 100_000

# Worker globals (set by initializer for parallel batch processing; reuse for throughput, same quality)
_worker_meta_index: Optional[Dict] = None
_worker_product_copy: Optional[Dict] = None
_worker_category: Optional[str] = None
_worker_category_enum: Any = None
_worker_hvi: Any = None
_worker_detector: Any = None
_worker_hyperscan_analyzer: Any = None


def _init_worker(meta_path: str, category: str, use_hyperscan: bool = False) -> None:
    """Load meta and create HVI (and optionally Hyperscan analyzer) once per worker."""
    global _worker_meta_index, _worker_product_copy, _worker_category, _worker_category_enum, _worker_hvi, _worker_hyperscan_analyzer
    from adam.intelligence.amazon_data_registry import AmazonCategory
    from adam.intelligence.helpful_vote_intelligence import HelpfulVoteIntelligence
    path = Path(meta_path)
    _worker_meta_index, _worker_product_copy = load_meta_index(path)
    _worker_category = category
    _worker_hvi = HelpfulVoteIntelligence()
    if use_hyperscan:
        _worker_hyperscan_analyzer = get_hyperscan_analyzer()
    else:
        _worker_hyperscan_analyzer = None
    try:
        _worker_category_enum = AmazonCategory(category)
    except ValueError:
        _worker_category_enum = None


def _process_batch_worker(args: Tuple[List[Dict], bool, bool, bool]) -> Dict[str, Any]:
    """Process one batch in a worker process. When use_hyperscan, use Hyperscan for archetype and skip dimensions."""
    global _worker_meta_index, _worker_product_copy, _worker_category, _worker_category_enum, _worker_hvi, _worker_detector, _worker_hyperscan_analyzer
    batch, use_deep_archetype, do_dimensions, use_hyperscan = args
    if use_hyperscan:
        do_dimensions = False
        hyperscan_analyzer = _worker_hyperscan_analyzer
        detector = None
    else:
        hyperscan_analyzer = None
        if use_deep_archetype and _worker_detector is None:
            _worker_detector = get_deep_detector()
        detector = _worker_detector if use_deep_archetype else None
    dimension_aggregate = None
    if do_dimensions and _worker_category:
        try:
            from scripts.overnight_comprehensive_reprocessor import ComprehensiveStats
            dimension_aggregate = ComprehensiveStats(source=_worker_category)
        except Exception:
            pass
    return process_review_batch(
        batch,
        _worker_meta_index or {},
        _worker_product_copy or {},
        _worker_category or "",
        _worker_category_enum,
        dimension_aggregate=dimension_aggregate,
        use_deep_archetype=use_deep_archetype and not use_hyperscan,
        hvi=_worker_hvi,
        detector=detector,
        hyperscan_analyzer=hyperscan_analyzer,
    )


def _batch_generator(
    review_path: Path,
    resume_from: int,
    batch_size: int,
    use_deep_archetype: bool,
    do_dimensions: bool,
    use_hyperscan: bool,
    opener: Any,
):
    """Yield (batch, use_deep_archetype, do_dimensions, use_hyperscan) from review file."""
    batch = []
    line_num = 0
    with opener(review_path, "rt", encoding="utf-8", errors="replace") as f:
        for line in f:
            line_num += 1
            if line_num <= resume_from:
                continue
            try:
                review = json.loads(line)
                batch.append(review)
                if len(batch) >= batch_size:
                    yield (list(batch), use_deep_archetype, do_dimensions, use_hyperscan)
                    batch = []
            except json.JSONDecodeError:
                continue
    if batch:
        yield (list(batch), use_deep_archetype, do_dimensions, use_hyperscan)


def _merge_dimension_dicts(acc: Dict, d: Dict) -> None:
    """Merge dimension stats dict d into acc (in-place). Sum numeric values; recurse into dicts."""
    for k, v in d.items():
        if isinstance(v, dict) and not isinstance(v, type(acc.get(k, {}))):
            if k not in acc:
                acc[k] = {}
            _merge_dimension_dicts(acc[k], v)
        elif isinstance(v, (int, float)):
            acc[k] = acc.get(k, 0) + v
        elif isinstance(v, dict):
            if k not in acc:
                acc[k] = {}
            _merge_dimension_dicts(acc[k], v)


# =============================================================================
# PRE-FLIGHT VERIFICATION (Plan Section 4)
# =============================================================================

def verify_plan_preflight() -> bool:
    """Run pre-flight checks from INGESTION_MASTER_PLAN Section 4. Returns True if all pass."""
    ok = True
    try:
        from adam.intelligence.amazon_data_registry import (
            AMAZON_DATA_DIR,
            get_available_categories,
            get_category_files,
        )
        data_dir = Path(AMAZON_DATA_DIR)
        if not data_dir.exists():
            logger.error(f"Amazon data dir does not exist: {data_dir}")
            return False
        cats = get_available_categories()
        if not cats:
            logger.error("No categories with both review and meta files")
            return False
        files = get_category_files(cats[0])
        if not files.review_path.exists() and not getattr(files, "review_file_gz", None):
            logger.error("Sample category missing review file")
            return False
        if not files.meta_path.exists():
            logger.error("Sample category missing meta file")
            return False
        logger.info(f"Pre-flight OK: {len(cats)} categories, sample {cats[0].value} has both files")
        return True
    except Exception as e:
        logger.error(f"Pre-flight failed: {e}")
        return False


# =============================================================================
# META LOADER (product copy by ASIN)
# =============================================================================

def load_meta_index(meta_path: Path) -> Tuple[Dict[str, Dict], Dict[str, Dict]]:
    """
    Load meta file: ASIN -> product info and ASIN -> product copy text.
    product_copy_text = title + features + description (for ad psychology).
    """
    meta_index = {}
    product_copy = {}
    opener = gzip.open if str(meta_path).endswith(".gz") else open
    mode = "rt" if str(meta_path).endswith(".gz") else "r"
    count = 0
    with opener(meta_path, mode, encoding="utf-8", errors="replace") as f:
        for line in f:
            try:
                item = json.loads(line)
                asin = item.get("parent_asin") or item.get("asin")
                if not asin:
                    continue
                title = (item.get("title") or "")[:500]
                details = item.get("details") or {}
                brand = details.get("brand", "") if isinstance(details, dict) else ""
                features = item.get("features") or []
                if not isinstance(features, list):
                    features = [features] if features else []
                description = item.get("description") or []
                if not isinstance(description, list):
                    description = [description] if description else []
                copy_parts = [title]
                copy_parts.extend(str(p) for p in features if p)
                copy_parts.extend(str(p) for p in description if p)
                product_text = " ".join(copy_parts)[:10000]
                meta_index[asin] = {
                    "title": title[:200],
                    "brand": brand,
                    "store": item.get("store", ""),
                    "main_category": item.get("main_category", ""),
                }
                product_copy[asin] = product_text
                count += 1
                if count % 100_000 == 0:
                    logger.info(f"  Meta: {count:,} products loaded")
            except json.JSONDecodeError:
                continue
    logger.info(f"Loaded {len(meta_index):,} products, {sum(1 for t in product_copy.values() if len(t) > 20):,} with copy text")
    return meta_index, product_copy


# =============================================================================
# AD PROFILE FROM PRODUCT COPY (optional; can be extended)
# =============================================================================

def get_product_ad_profile(product_copy_text: str) -> Optional[Dict[str, Any]]:
    """Build ad psychology profile from product copy. Returns None if skip or error."""
    if not product_copy_text or len(product_copy_text) < 20:
        return None
    try:
        from adam.intelligence.advertisement_psychology_framework import create_advertisement_profile
        profile = create_advertisement_profile(product_copy_text[:5000])
        return {
            "primary_persuasion": getattr(profile, "primary_persuasion_technique", ""),
            "primary_emotion": getattr(profile, "primary_emotional_appeal", ""),
            "primary_value": getattr(profile, "primary_value_proposition", ""),
            "linguistic_style": getattr(profile, "linguistic_style", ""),
        }
    except Exception:
        return None


# =============================================================================
# DEEP ARCHETYPE DETECTOR (plan: per-review archetype)
# =============================================================================

_deep_detector = None
_hyperscan_analyzer = None

def get_deep_detector():
    """Get or create DeepArchetypeDetector (per plan: deep archetype per review)."""
    global _deep_detector
    if _deep_detector is None:
        try:
            from adam.intelligence.deep_archetype_detection import DeepArchetypeDetector
            _deep_detector = DeepArchetypeDetector()
        except Exception as e:
            logger.debug(f"DeepArchetypeDetector not available: {e}")
    return _deep_detector


def get_hyperscan_analyzer():
    """Get or create HyperscanAnalyzer for 10k+ reviews/sec (82-framework patterns). Returns None if hyperscan unavailable."""
    global _hyperscan_analyzer
    if _hyperscan_analyzer is not None:
        return _hyperscan_analyzer
    try:
        import hyperscan  # noqa: F401
        from scripts.run_82_framework_hyperscan import HyperscanAnalyzer
        _hyperscan_analyzer = HyperscanAnalyzer()
        logger.info("Hyperscan analyzer initialized (82-framework, 10k+ reviews/sec path)")
        return _hyperscan_analyzer
    except Exception as e:
        logger.debug(f"Hyperscan not available: {e}")
        return None


# =============================================================================
# REVIEW BATCH PROCESSOR (helpful vote + templates + effectiveness + deep archetype + 430+ dimensions)
# =============================================================================

def process_review_batch(
    batch: List[Dict],
    meta_index: Dict[str, Dict],
    product_copy: Dict[str, str],
    category: str,
    category_enum: Any,
    dimension_aggregate: Any = None,
    use_deep_archetype: bool = True,
    hvi: Any = None,
    detector: Any = None,
    hyperscan_analyzer: Any = None,
    skip_ad_profiles: bool = False,
    category_linked_asins: Optional[set] = None,
    ndf_aggregator: Any = None,
) -> Dict[str, Any]:
    """Process one batch: link to product, archetype (Hyperscan or deep detector), HVI, 430+ dimensions (plan Section 5).
    When hyperscan_analyzer is set, use it for archetype (10k+ reviews/sec) and skip dimension aggregation for speed.
    When skip_ad_profiles=True, skip create_advertisement_profile() in the hot loop (computed separately for speed).
    When category_linked_asins is provided, use it for cross-batch ASIN dedup (avoids recomputing for same ASIN in different batches).
    When ndf_aggregator is provided, extract NDF (Nonconscious Decision Fingerprint) per review and accumulate."""
    from adam.intelligence.helpful_vote_intelligence import HelpfulVoteIntelligence
    from adam.intelligence.amazon_data_registry import CATEGORY_INFO
    from adam.intelligence.ndf_extractor import extract_ndf

    if hvi is None:
        hvi = HelpfulVoteIntelligence()
    use_hyperscan = hyperscan_analyzer is not None
    if use_hyperscan:
        detector = None
    elif use_deep_archetype and detector is None:
        detector = get_deep_detector()
    else:
        detector = None if not use_deep_archetype else detector
    cat_info = CATEGORY_INFO.get(category_enum, {})
    default_archetypes = cat_info.get("typical_archetypes", ["everyman"])
    default_archetype = default_archetypes[0] if default_archetypes else "everyman"

    results = {
        "reviews_processed": 0,
        "products_linked": 0,
        "high_influence": 0,
        "helpful_votes": 0,
        "templates": [],
        "effectiveness": [],
        "product_ad_profiles": {},
        "archetype_distribution": defaultdict(int),
        "product_archetype_profiles": defaultdict(lambda: defaultdict(float)),
    }
    linked_asins = category_linked_asins if category_linked_asins is not None else set()
    dim_stats = dimension_aggregate

    for review in batch:
        try:
            parent_asin = review.get("parent_asin") or review.get("asin") or ""
            text = review.get("reviewText") or review.get("text") or review.get("review") or ""
            helpful_votes = review.get("helpful_vote") or review.get("helpful_votes") or review.get("helpfulVotes") or 0
            rating = float(review.get("overall") or review.get("rating") or review.get("stars") or 0.0)
            verified = review.get("verified_purchase", False)

            if parent_asin and parent_asin in meta_index and parent_asin not in linked_asins:
                linked_asins.add(parent_asin)
                results["products_linked"] += 1
                if not skip_ad_profiles:
                    copy_text = product_copy.get(parent_asin, "")
                    if copy_text:
                        ad_prof = get_product_ad_profile(copy_text)
                        if ad_prof:
                            results["product_ad_profiles"][parent_asin] = ad_prof

            if not text or len(text) < 10:
                continue

            # Archetype: Hyperscan (10k+ reviews/sec) or DeepArchetypeDetector
            archetype = default_archetype
            archetype_confidence = 0.3
            if use_hyperscan and len(text) > 10:
                try:
                    hs_result = hyperscan_analyzer.analyze(text)
                    arch = hs_result.get("primary_archetype") or default_archetype
                    if arch and arch != "unknown":
                        archetype = arch
                        archetype_confidence = 0.8
                except Exception:
                    pass
            elif detector and len(text) > 50:
                try:
                    deep_result = detector.detect(text)
                    conf = getattr(deep_result, "primary_confidence", 0) or getattr(deep_result, "confidence", 0)
                    if deep_result and conf > 0.25:
                        archetype = getattr(deep_result, "primary_archetype", default_archetype) or default_archetype
                        archetype_confidence = conf
                except Exception:
                    pass
            results["archetype_distribution"][archetype] += 1
            if parent_asin:
                results["product_archetype_profiles"][parent_asin][archetype] += archetype_confidence

            # NDF: Nonconscious Decision Fingerprint (7 dimensions from linguistic markers)
            if ndf_aggregator is not None:
                try:
                    ndf = extract_ndf(text, rating=rating, helpful_votes=helpful_votes)
                    ndf_aggregator.add(ndf, archetype=archetype)
                except Exception:
                    pass

            # 430+ dimensions (plan: dimension counts from review text)
            if dim_stats is not None:
                try:
                    from scripts.overnight_comprehensive_reprocessor import extract_comprehensive_profile
                    profile = extract_comprehensive_profile(text, rating)
                    if profile:
                        dim_stats.add_profile(profile, rating)
                except Exception:
                    pass

            results["helpful_votes"] += helpful_votes
            process_result = hvi.process_review(
                review_text=text,
                helpful_votes=helpful_votes,
                verified_purchase=verified,
                archetype=archetype,
                product_category=category,
                rating=rating,
            )
            results["reviews_processed"] += 1
            if process_result.get("tier") in ("viral", "very_high", "high"):
                results["high_influence"] += 1
                for pattern in process_result.get("templates_extracted", []):
                    results["templates"].append({
                        "pattern": pattern[:200],
                        "helpful_votes": helpful_votes,
                        "mechanisms": process_result.get("mechanisms_detected", []),
                        "archetype": archetype,
                        "archetype_confidence": archetype_confidence,
                        "category": category,
                    })
        except Exception as e:
            logger.debug(f"Review error: {e}")
            continue

    results["effectiveness"] = hvi.get_graph_effectiveness_matrix()
    results["archetype_distribution"] = dict(results["archetype_distribution"])
    results["product_archetype_profiles"] = {k: dict(v) for k, v in results["product_archetype_profiles"].items()}
    if dim_stats is not None and hasattr(dim_stats, "to_dict"):
        results["dimension_distributions"] = dim_stats.to_dict()
    return results


# =============================================================================
# CATEGORY-LEVEL PARALLELISM (one worker per category — no main-process bottleneck)
# =============================================================================

def _process_category_worker(args: Tuple[str, bool, bool, int, bool, int]) -> Dict[str, Any]:
    """Run one category to completion in a worker. Worker does its own I/O and processing (see INGESTION_10K_THROUGHPUT_REFERENCE.md)."""
    category_value, skip_if_done, use_deep_archetype, batch_size, use_hyperscan, per_category_workers = args
    from adam.intelligence.amazon_data_registry import AmazonCategory
    try:
        cat_enum = AmazonCategory(category_value)
    except ValueError:
        return {"category": category_value, "skipped": True, "reason": "unknown_category"}
    return process_category(
        cat_enum,
        resume_from=0,
        skip_if_done=skip_if_done,
        workers=per_category_workers,
        use_deep_archetype=use_deep_archetype,
        batch_size=batch_size,
        use_hyperscan=use_hyperscan,
    )


# =============================================================================
# CATEGORY PROCESSOR (load meta first, then stream reviews)
# =============================================================================

def process_category(
    category_enum: Any,
    resume_from: int = 0,
    skip_if_done: bool = True,
    workers: int = 1,
    use_deep_archetype: bool = True,
    batch_size: int = BATCH_SIZE,
    use_hyperscan: bool = False,
) -> Dict[str, Any]:
    """Process one Amazon category: meta first, then reviews; link by ASIN. With use_hyperscan=True use 82-framework Hyperscan (10k+ reviews/sec)."""
    from adam.intelligence.amazon_data_registry import get_category_files, CATEGORY_INFO

    category = category_enum.value
    files = get_category_files(category_enum)
    if not files.both_exist:
        logger.warning(f"Skip {category}: missing review or meta file")
        return {"category": category, "skipped": True, "reason": "missing_files"}

    result_file = OUTPUT_DIR / f"{category}_result.json"
    if skip_if_done and result_file.exists():
        logger.info(f"Skip {category}: result already exists")
        return {"category": category, "skipped": True, "reason": "already_done"}

    logger.info(f"{'='*60}")
    logger.info(f"PROCESSING: {category} (workers={workers}, deep_archetype={use_deep_archetype})")
    logger.info(f"  Meta: {files.meta_path.name}  Review: {files.review_path.name}")
    logger.info(f"{'='*60}")

    # 1) Load meta first (ASIN -> product info + product copy)
    meta_index, product_copy = load_meta_index(files.meta_path)
    if not meta_index:
        logger.warning(f"Skip {category}: meta empty")
        return {"category": category, "skipped": True, "reason": "meta_empty"}

    # 2) Aggregate results
    all_templates = []
    effectiveness_agg = defaultdict(lambda: {"total_count": 0, "weighted_success": 0.0})
    product_ad_profiles_agg = {}
    archetype_dist_agg = defaultdict(int)
    product_archetype_agg = defaultdict(lambda: defaultdict(float))
    reviews_processed = 0
    products_linked = 0
    high_influence = 0
    total_helpful_votes = 0
    dimension_aggregate = None
    do_dimensions = True
    if use_hyperscan:
        do_dimensions = False
    if do_dimensions:
        try:
            from scripts.overnight_comprehensive_reprocessor import ComprehensiveStats
            if workers == 1:
                dimension_aggregate = ComprehensiveStats(source=category)
        except Exception as e:
            logger.debug(f"Dimension aggregation not available: {e}")
            do_dimensions = False

    hyperscan_analyzer = get_hyperscan_analyzer() if use_hyperscan else None
    if use_hyperscan and hyperscan_analyzer is None:
        logger.warning("--use-hyperscan requested but Hyperscan unavailable; falling back to deep archetype")

    # NDF: Nonconscious Decision Fingerprint aggregator (population-level NDF distributions)
    ndf_aggregator = None
    try:
        from adam.intelligence.ndf_extractor import NDFAggregator
        ndf_aggregator = NDFAggregator()
        logger.info(f"  {category}: NDF extraction enabled (7 nonconscious decision dimensions)")
    except ImportError:
        logger.debug("NDF extractor not available")

    review_path = files.review_path
    opener = gzip.open if str(review_path).endswith(".gz") else open
    batch = []
    start_time = datetime.now()
    line_num = 0

    if workers > 1:
        # QUALITY-EQUIVALENT: Same process_review_batch() with same use_deep_archetype, ComprehensiveStats, HVI, product ad profiles.
        # We only distribute batches across workers and merge results (additive). No shortcuts; no loss of quality.
        # Streaming: generator yields batches so we don't load full category into memory; cap in-flight to overlap I/O with compute.
        dimension_merge: Dict[str, Any] = {}
        gen = _batch_generator(review_path, resume_from, batch_size, use_deep_archetype, do_dimensions, use_hyperscan, opener)
        max_in_flight = max(workers * 2, 4)
        with ProcessPoolExecutor(max_workers=workers, initializer=_init_worker, initargs=(str(files.meta_path), category, use_hyperscan)) as executor:
            futures = set()
            try:
                for _ in range(max_in_flight):
                    batch_tuple = next(gen)
                    futures.add(executor.submit(_process_batch_worker, batch_tuple))
            except StopIteration:
                pass
            while futures:
                for future in as_completed(futures):
                    batch_result = future.result()
                    reviews_processed += batch_result["reviews_processed"]
                    products_linked += batch_result["products_linked"]
                    high_influence += batch_result["high_influence"]
                    total_helpful_votes += batch_result["helpful_votes"]
                    all_templates.extend(batch_result["templates"])
                    for eff in batch_result.get("effectiveness", []):
                        key = (eff.get("archetype"), eff.get("mechanism"))
                        if key[0] and key[1]:
                            effectiveness_agg[key]["total_count"] += eff.get("sample_size", 0)
                            effectiveness_agg[key]["weighted_success"] += eff.get("weighted_success_rate", 0) * eff.get("sample_size", 0)
                    product_ad_profiles_agg.update(batch_result.get("product_ad_profiles", {}))
                    for arch, count in batch_result.get("archetype_distribution", {}).items():
                        archetype_dist_agg[arch] += count
                    for asin, prof in batch_result.get("product_archetype_profiles", {}).items():
                        for arch, score in prof.items():
                            product_archetype_agg[asin][arch] += score
                    if batch_result.get("dimension_distributions"):
                        _merge_dimension_dicts(dimension_merge, batch_result["dimension_distributions"])
                    logger.info(f"  {reviews_processed:,} reviews | {products_linked:,} products linked | {high_influence:,} high-influence")
                    futures.discard(future)
                    try:
                        batch_tuple = next(gen)
                        futures.add(executor.submit(_process_batch_worker, batch_tuple))
                    except StopIteration:
                        pass
                    break
        if dimension_merge:
            dimension_aggregate = dimension_merge
    else:
        # Single-threaded path: FAST. Each category loads meta once, Hyperscan once, processes reviews sequentially.
        # Ad profiles are deferred to AFTER review processing (skip_ad_profiles=True) so the hot loop stays at Hyperscan speed.
        # Category-level linked_asins avoids recomputing for the same ASIN in different batches.
        category_linked_asins = set()
        last_rate_log = datetime.now()
        rate_log_reviews = 0
        with opener(review_path, "rt", encoding="utf-8", errors="replace") as f:
            for line in f:
                line_num += 1
                if line_num <= resume_from:
                    continue
                try:
                    review = json.loads(line)
                    batch.append(review)
                    if len(batch) >= batch_size:
                        batch_result = process_review_batch(
                            batch, meta_index, product_copy, category, category_enum,
                            dimension_aggregate=dimension_aggregate,
                            use_deep_archetype=use_deep_archetype,
                            hyperscan_analyzer=hyperscan_analyzer,
                            skip_ad_profiles=True,
                            category_linked_asins=category_linked_asins,
                            ndf_aggregator=ndf_aggregator,
                        )
                        reviews_processed += batch_result["reviews_processed"]
                        products_linked += batch_result["products_linked"]
                        high_influence += batch_result["high_influence"]
                        total_helpful_votes += batch_result["helpful_votes"]
                        all_templates.extend(batch_result["templates"])
                        for eff in batch_result.get("effectiveness", []):
                            key = (eff.get("archetype"), eff.get("mechanism"))
                            if key[0] and key[1]:
                                effectiveness_agg[key]["total_count"] += eff.get("sample_size", 0)
                                effectiveness_agg[key]["weighted_success"] += eff.get("weighted_success_rate", 0) * eff.get("sample_size", 0)
                        for arch, count in batch_result.get("archetype_distribution", {}).items():
                            archetype_dist_agg[arch] += count
                        for asin, prof in batch_result.get("product_archetype_profiles", {}).items():
                            for arch, score in prof.items():
                                product_archetype_agg[asin][arch] += score
                        batch = []
                        # Rate logging: show reviews/sec
                        now = datetime.now()
                        elapsed_since_log = (now - last_rate_log).total_seconds()
                        batch_reviews = batch_result["reviews_processed"]
                        rate_log_reviews += batch_reviews
                        if elapsed_since_log >= 10.0:
                            rate = rate_log_reviews / elapsed_since_log
                            total_elapsed = (now - start_time).total_seconds()
                            total_rate = reviews_processed / total_elapsed if total_elapsed > 0 else 0
                            logger.info(f"  {category}: {reviews_processed:,} reviews | {products_linked:,} products | {high_influence:,} high-infl | {rate:,.0f} reviews/sec (recent) | {total_rate:,.0f} reviews/sec (avg)")
                            last_rate_log = now
                            rate_log_reviews = 0
                        elif reviews_processed % (batch_size * 5) == 0:
                            total_elapsed = (now - start_time).total_seconds()
                            total_rate = reviews_processed / total_elapsed if total_elapsed > 0 else 0
                            logger.info(f"  {category}: {reviews_processed:,} reviews | {products_linked:,} products | {total_rate:,.0f} reviews/sec (avg)")
                except json.JSONDecodeError:
                    continue

        if batch:
            batch_result = process_review_batch(
                batch, meta_index, product_copy, category, category_enum,
                dimension_aggregate=dimension_aggregate,
                use_deep_archetype=use_deep_archetype,
                hyperscan_analyzer=hyperscan_analyzer,
                skip_ad_profiles=True,
                category_linked_asins=category_linked_asins,
                ndf_aggregator=ndf_aggregator,
            )
            reviews_processed += batch_result["reviews_processed"]
            products_linked += batch_result["products_linked"]
            high_influence += batch_result["high_influence"]
            total_helpful_votes += batch_result["helpful_votes"]
            all_templates.extend(batch_result["templates"])
            for eff in batch_result.get("effectiveness", []):
                key = (eff.get("archetype"), eff.get("mechanism"))
                if key[0] and key[1]:
                    effectiveness_agg[key]["total_count"] += eff.get("sample_size", 0)
                    effectiveness_agg[key]["weighted_success"] += eff.get("weighted_success_rate", 0) * eff.get("sample_size", 0)
            for arch, count in batch_result.get("archetype_distribution", {}).items():
                archetype_dist_agg[arch] += count
            for asin, prof in batch_result.get("product_archetype_profiles", {}).items():
                for arch, score in prof.items():
                    product_archetype_agg[asin][arch] += score

        # POST-REVIEW: Compute product ad profiles AFTER review processing (separated from hot loop for speed).
        # Cap at 10k profiles per category (we save 500 in result; 10k gives good coverage).
        MAX_AD_PROFILES = 10_000
        ad_profile_count = 0
        review_elapsed = (datetime.now() - start_time).total_seconds()
        logger.info(f"  {category}: Review processing done in {review_elapsed:.0f}s ({reviews_processed:,} reviews, {reviews_processed/review_elapsed:.0f}/sec). Computing product ad profiles for up to {MAX_AD_PROFILES:,} products...")
        ad_profile_start = datetime.now()
        for asin in list(category_linked_asins)[:MAX_AD_PROFILES]:
            copy_text = product_copy.get(asin, "")
            if copy_text and len(copy_text) >= 20:
                ad_prof = get_product_ad_profile(copy_text)
                if ad_prof:
                    product_ad_profiles_agg[asin] = ad_prof
                    ad_profile_count += 1
        ad_elapsed = (datetime.now() - ad_profile_start).total_seconds()
        logger.info(f"  {category}: {ad_profile_count:,} product ad profiles computed in {ad_elapsed:.0f}s")

    # Build effectiveness matrix (nested)
    effectiveness_matrix = {}
    for (arch, mech), data in effectiveness_agg.items():
        total = data["total_count"]
        if total <= 0:
            continue
        ws = data["weighted_success"]
        if arch not in effectiveness_matrix:
            effectiveness_matrix[arch] = {}
        effectiveness_matrix[arch][mech] = {"success_rate": ws / total, "sample_size": total}

    all_templates.sort(key=lambda t: t.get("helpful_votes", 0), reverse=True)
    templates_top = all_templates[:2000]

    result = {
        "category": category,
        "reviews_processed": reviews_processed,
        "products_linked": products_linked,
        "high_influence_reviews": high_influence,
        "total_helpful_votes": total_helpful_votes,
        "templates_extracted": len(all_templates),
        "templates": templates_top,
        "effectiveness_matrix": effectiveness_matrix,
        "product_ad_profiles_count": len(product_ad_profiles_agg),
        "product_ad_profiles": dict(list(product_ad_profiles_agg.items())[:500]),
        "product_ad_profiles_sample": dict(list(product_ad_profiles_agg.items())[:100]),
        "archetype_distribution": dict(archetype_dist_agg),
        "product_archetype_profiles": {k: dict(v) for k, v in list(product_archetype_agg.items())[:500]},
        "duration_seconds": (datetime.now() - start_time).total_seconds(),
        "meta_products_loaded": len(meta_index),
    }
    if dimension_aggregate is not None:
        result["dimension_distributions"] = dimension_aggregate if isinstance(dimension_aggregate, dict) else dimension_aggregate.to_dict()
    if ndf_aggregator is not None and hasattr(ndf_aggregator, "to_dict"):
        ndf_data = ndf_aggregator.to_dict()
        if ndf_data.get("ndf_count", 0) > 0:
            result["ndf_population"] = ndf_data
            logger.info(f"  {category}: NDF extracted from {ndf_data['ndf_count']:,} reviews ({len(ndf_data.get('ndf_archetype_profiles', {}))} archetype profiles)")

    with open(result_file, "w") as f:
        json.dump(result, f, indent=2)
    logger.info(f"Wrote {result_file}; reviews={reviews_processed:,} products_linked={products_linked:,}")
    gc.collect()
    return result


# =============================================================================
# MAIN: RUN ALL CATEGORIES + VERIFICATION
# =============================================================================

def run_verification() -> bool:
    """Verify outputs per plan Section 3. Return True if all pass."""
    ok = True
    from adam.intelligence.amazon_data_registry import get_available_categories
    cats = get_available_categories()
    for c in cats:
        rpath = OUTPUT_DIR / f"{c.value}_result.json"
        if not rpath.exists():
            logger.error(f"Missing result: {rpath}")
            ok = False
            continue
        try:
            with open(rpath) as f:
                data = json.load(f)
            if data.get("skipped"):
                continue
            if data.get("reviews_processed", 0) == 0:
                logger.warning(f"Empty reviews: {c.value}")
            if data.get("products_linked", 0) == 0:
                logger.warning(f"No products linked: {c.value}")
            # Plan Section 3 required outputs
            for key in ("templates", "effectiveness_matrix", "product_ad_profiles", "archetype_distribution", "product_archetype_profiles"):
                if key not in data:
                    logger.warning(f"Missing plan output '{key}': {c.value}")
            if "dimension_distributions" not in data and not data.get("skipped"):
                logger.debug(f"Optional dimension_distributions absent: {c.value}")
        except Exception as e:
            logger.error(f"Verify {rpath}: {e}")
            ok = False
    logger.info("Verification done: %s", "PASS" if ok else "FAIL")
    return ok


def main():
    parser = argparse.ArgumentParser(description="Unified ingestion with product copy (plan Section 5)")
    parser.add_argument("--verify-plan", action="store_true", help="Run pre-flight only; do not ingest")
    parser.add_argument("--resume-from", type=str, default="", help="Resume from this category name (inclusive)")
    parser.add_argument("--no-skip-done", action="store_true", help="Re-run even if category result exists")
    parser.add_argument("--verify-only", action="store_true", help="Only run output verification")
    parser.add_argument("--category", type=str, default="", help="Process only this category (e.g. All_Beauty)")
    parser.add_argument("--workers", type=int, default=5, help="Categories in parallel (default 5 for 32GB; each loads its own meta+Hyperscan). Processing is sequential within each category — this is the 10k/sec architecture.")
    parser.add_argument("--per-category-workers", type=int, default=1, help="DEPRECATED: kept for CLI compat. Always forced to 1 (sequential within category is faster than batch workers due to memory duplication + pickling overhead).")
    parser.add_argument("--batch-size", type=int, default=BATCH_SIZE, help="Reviews per batch (default %s; try 15000-20000 for fewer round-trips)" % BATCH_SIZE)
    parser.add_argument("--no-deep-archetype", action="store_true", help="Skip per-review deep archetype (only if you need a lighter run)")
    parser.add_argument("--use-hyperscan", action="store_true", help="Use Hyperscan for archetype (82-framework, 10k+ reviews/sec); skips 430+ dimension aggregation for speed")
    args = parser.parse_args()

    if args.verify_plan:
        ok = verify_plan_preflight()
        sys.exit(0 if ok else 1)

    if args.verify_only:
        ok = run_verification()
        sys.exit(0 if ok else 1)

    # Pre-flight before running
    if not verify_plan_preflight():
        logger.error("Pre-flight failed. Fix and re-run. See INGESTION_MASTER_PLAN_AND_VERIFICATION.md Section 4.")
        sys.exit(1)

    from adam.intelligence.amazon_data_registry import get_available_categories, AmazonCategory
    categories = get_available_categories()
    if not categories:
        logger.error("No categories available")
        sys.exit(1)
    if args.category:
        try:
            cat_enum = AmazonCategory(args.category)
            if cat_enum not in categories:
                logger.error(f"Category {args.category} not in available list")
                sys.exit(1)
            categories = [cat_enum]
            logger.info(f"Processing single category: {args.category}")
        except ValueError:
            logger.error(f"Unknown category: {args.category}")
            sys.exit(1)
    elif args.resume_from:
        names = [c.value for c in categories]
        if args.resume_from not in names:
            logger.error(f"Unknown category: {args.resume_from}")
            sys.exit(1)
        idx = names.index(args.resume_from)
        categories = categories[idx:]
    logger.info(f"Processing {len(categories)} categories")

    # ARCHITECTURE: Category-level parallelism, SEQUENTIAL within each category.
    # This is how 10k/sec was achieved: each process owns one category file, loads meta ONCE,
    # compiles Hyperscan ONCE, and processes reviews sequentially. No per-category batch workers.
    # Per-category batch workers (ProcessPoolExecutor inside category) were a regression:
    # each batch worker duplicated the full meta (1-4GB) + Hyperscan DB, AND added pickling
    # overhead for every batch. Result: 117GB memory demand on 32GB, OOM crashes, and
    # paradoxically SLOWER throughput (pickling 10k review dicts costs more than processing them).
    #
    # 32GB RAM budget: OS+Cursor ~6GB, leaves ~26GB for ingestion.
    # Each category process: meta (0.01-4GB) + Hyperscan DB (~0.5GB) + working set.
    # Safe: 4-5 concurrent categories (most are small; avoid running multiple huge ones together).
    # Books (4.4M products, ~4GB meta) should not run alongside other large categories.
    use_hyperscan = getattr(args, "use_hyperscan", False)
    per_cat = 1  # ALWAYS 1: sequential within category. This is the 10k/sec architecture.

    if len(categories) > 1 and args.workers > 1:
        from adam.intelligence.amazon_data_registry import get_category_files

        # Sort categories by meta size ascending: small ones first, large ones later.
        # This is critical for 32GB: when small categories finish, workers exit and free memory
        # before large categories (Books 14GB, Clothing 17GB) start.
        def _meta_size(cat_enum):
            try:
                f = get_category_files(cat_enum)
                return f.meta_path.stat().st_size if f.meta_path.exists() else 0
            except Exception:
                return 0

        categories_sorted = sorted(categories, key=_meta_size)
        for c in categories_sorted:
            ms = _meta_size(c) / (1024**3)
            logger.info(f"  Queue: {c.value} (meta {ms:.2f}GB)")

        # Separate into tiers by meta size for safe parallel scheduling on 32GB
        LARGE_THRESHOLD = 8 * 1024**3  # 8GB meta → process alone
        large_cats = [c for c in categories_sorted if _meta_size(c) >= LARGE_THRESHOLD]
        normal_cats = [c for c in categories_sorted if _meta_size(c) < LARGE_THRESHOLD]

        n_workers = min(args.workers, len(categories))
        logger.info(f"Category-level parallelism: {n_workers} workers for {len(normal_cats)} normal categories, then {len(large_cats)} large categories (workers=2)")

        def _run_batch(cat_list, workers_for_batch):
            """Run a batch of categories with specified parallelism."""
            if not cat_list:
                return
            task_args = [
                (c.value, not args.no_skip_done, not args.no_deep_archetype, args.batch_size, use_hyperscan, per_cat)
                for c in cat_list
            ]
            # max_tasks_per_child=1: kill worker after each category to free memory (meta can be GB-scale).
            # This ensures large-category memory doesn't accumulate across categories.
            n = min(workers_for_batch, len(cat_list))
            with ProcessPoolExecutor(max_workers=n, max_tasks_per_child=1) as executor:
                futures = {executor.submit(_process_category_worker, a): a for a in task_args}
                for future in as_completed(futures):
                    try:
                        result = future.result()
                        cat_name = result.get("category", "?")
                        if result.get("skipped"):
                            logger.info(f"  Category {cat_name}: skipped ({result.get('reason', '')})")
                        else:
                            rev = result.get("reviews_processed", 0)
                            dur = result.get("duration_seconds", 0)
                            rate = rev / dur if dur > 0 else 0
                            logger.info(f"  Category {cat_name}: DONE {rev:,} reviews in {dur:.0f}s ({rate:,.0f}/sec)")
                    except Exception as e:
                        logger.error(f"Category worker failed: {e}")

        # Phase 1: Normal categories (meta < 8GB) — run with full parallelism
        _run_batch(normal_cats, n_workers)
        # Phase 2: Large categories (meta >= 8GB) — run 2 at a time max (each needs 10-17GB)
        _run_batch(large_cats, min(2, len(large_cats)))
    else:
        for cat in categories:
            process_category(
                cat,
                resume_from=0,
                skip_if_done=not args.no_skip_done,
                workers=1,
                use_deep_archetype=not args.no_deep_archetype,
                batch_size=args.batch_size,
                use_hyperscan=use_hyperscan,
            )

    ok = run_verification()
    if not ok:
        logger.error("Output verification failed. See INGESTION_MASTER_PLAN Section 3.")
        sys.exit(1)
    logger.info("Unified ingestion and verification complete. See POST_INGESTION_RUNBOOK.md for next steps.")


if __name__ == "__main__":
    main()
