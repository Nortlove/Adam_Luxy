#!/usr/bin/env python3
"""
Batch Amazon Sub-Category Ingestion

Processes ALL Amazon categories from external drive with sub-category linking.
Reads directly from external drive, saves checkpoints locally.

Usage:
    python3 scripts/batch_subcategory_ingest.py
"""

import json
import logging
import re
import time
import sys
import gzip
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass, field

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Paths
EXTERNAL_DRIVE = Path("/Volumes/Sped/Nocera Models/Review Data/Amazon")
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data" / "learning"

# Archetype patterns
ARCHETYPE_PATTERNS = {
    "achiever": ["best", "premium", "quality", "performance", "results", "effective", "professional", "success", "excellent", "perfect"],
    "explorer": ["try", "new", "different", "discover", "experiment", "curious", "unique", "adventure", "interesting", "surprising"],
    "connector": ["gift", "share", "recommend", "friends", "family", "together", "everyone", "community", "love", "gave"],
    "guardian": ["safe", "reliable", "trust", "consistent", "dependable", "protect", "secure", "traditional", "always", "years"],
    "pragmatist": ["value", "price", "affordable", "practical", "works", "functional", "worth", "budget", "cheap", "deal"]
}

# Framework patterns
FRAMEWORK_PATTERNS = {
    "regulatory_focus.promotion": ["achieve", "gain", "accomplish", "success", "win", "grow", "advance", "opportunity", "aspire"],
    "regulatory_focus.prevention": ["safe", "secure", "protect", "avoid", "prevent", "careful", "responsible", "duty", "must"],
    "temporal.future": ["will", "going to", "plan", "hope", "expect", "anticipate", "future", "soon"],
    "temporal.present": ["now", "today", "currently", "enjoying", "using", "love", "is", "am"],
    "temporal.past": ["was", "used to", "remember", "before", "always had", "been", "worked"],
    "construal.abstract": ["concept", "idea", "overall", "generally", "philosophy", "principle", "essence"],
    "construal.concrete": ["specifically", "exactly", "particular", "detail", "precise", "inch", "size"],
    "emotional.high": ["amazing", "incredible", "absolutely", "love", "hate", "terrible", "fantastic", "awful", "obsessed"],
    "emotional.medium": ["good", "nice", "fine", "okay", "decent", "solid", "happy", "satisfied"],
    "emotional.low": ["adequate", "sufficient", "functional", "works", "acceptable"],
    "social.high": ["everyone", "people", "friends", "family", "recommend", "share", "gift", "party"],
    "social.individual": ["I", "my", "personally", "myself", "me", "own"]
}


@dataclass
class CategoryProfile:
    """Profile for a sub-category path"""
    path: str
    level: int
    archetypes: Dict[str, float] = field(default_factory=dict)
    frameworks: Dict[str, float] = field(default_factory=dict)
    review_count: int = 0


class BatchSubcategoryIngestor:
    """Batch process all Amazon categories"""
    
    def __init__(self):
        self.external_path = EXTERNAL_DRIVE
        self.categories_to_process = []
        
    def discover_categories(self) -> List[str]:
        """Find all categories with both review and meta files (supports .gz)"""
        categories = []
        seen = set()
        
        # Check uncompressed files first
        for review_file in self.external_path.glob("*.jsonl"):
            if review_file.name.startswith("meta_") or ".gz" in review_file.name:
                continue
            
            category = review_file.stem
            meta_file = self.external_path / f"meta_{category}.jsonl"
            meta_file_gz = self.external_path / f"meta_{category}.jsonl.gz"
            
            if meta_file.exists() or meta_file_gz.exists():
                categories.append(category)
                seen.add(category)
                logger.info(f"Found: {category}")
        
        # Check compressed files that don't have uncompressed versions
        for review_file in self.external_path.glob("*.jsonl.gz"):
            if review_file.name.startswith("meta_"):
                continue
            
            category = review_file.stem.replace(".jsonl", "")
            if category in seen:
                continue
            
            # Check for corresponding uncompressed file
            uncompressed = self.external_path / f"{category}.jsonl"
            if uncompressed.exists():
                continue  # Will be handled above
            
            meta_file = self.external_path / f"meta_{category}.jsonl"
            meta_file_gz = self.external_path / f"meta_{category}.jsonl.gz"
            
            if meta_file.exists() or meta_file_gz.exists():
                categories.append(category)
                logger.info(f"Found (compressed): {category}")
        
        self.categories_to_process = sorted(categories)
        return self.categories_to_process
    
    def _open_file(self, filepath: Path):
        """Open file, handling both .gz and regular files"""
        gz_path = Path(str(filepath) + ".gz")
        
        if filepath.exists():
            return open(filepath, encoding='utf-8', errors='replace')
        elif gz_path.exists():
            return gzip.open(gz_path, 'rt', encoding='utf-8', errors='replace')
        else:
            raise FileNotFoundError(f"Neither {filepath} nor {gz_path} exists")
    
    def process_category(self, category: str) -> Dict[str, Any]:
        """Process a single category with sub-category linking"""
        review_file = self.external_path / f"{category}.jsonl"
        meta_file = self.external_path / f"meta_{category}.jsonl"
        
        logger.info(f"\n{'='*60}")
        logger.info(f"Processing: {category}")
        logger.info(f"{'='*60}")
        
        # Load ASIN -> category mapping
        asin_to_categories = {}
        logger.info(f"Loading meta file...")
        
        try:
            with self._open_file(meta_file) as f:
                for line in f:
                    try:
                        data = json.loads(line)
                        asin = data.get("parent_asin") or data.get("asin")
                        cats = data.get("categories", [])
                        if asin and cats:
                            asin_to_categories[asin] = cats
                    except json.JSONDecodeError:
                        continue
                    except Exception:
                        continue
        except FileNotFoundError:
            logger.warning(f"Meta file not found: {meta_file}")
        except Exception as e:
            logger.warning(f"Error reading meta file: {e}")
        
        logger.info(f"Loaded {len(asin_to_categories):,} product mappings")
        
        # Process reviews
        category_profiles: Dict[str, CategoryProfile] = {}
        stats = {
            "reviews_processed": 0,
            "reviews_matched": 0,
            "products_seen": set(),
            "paths_seen": set()
        }
        
        start_time = time.time()
        
        logger.info(f"Processing reviews...")
        i = 0
        try:
            with self._open_file(review_file) as f:
                for i, line in enumerate(f):
                    try:
                        review = json.loads(line)
                        asin = review.get("parent_asin") or review.get("asin")
                        text = review.get("text", "")
                        
                        if not asin or not text:
                            continue
                        
                        categories = asin_to_categories.get(asin)
                        if not categories:
                            continue
                        
                        stats["reviews_matched"] += 1
                        stats["products_seen"].add(asin)
                        
                        # Extract psychology
                        archetypes, frameworks = self._extract_psychology(text)
                        
                        if not archetypes:
                            continue
                        
                        # Update profiles at each level
                        for level in range(len(categories)):
                            path = " > ".join(categories[:level + 1])
                            stats["paths_seen"].add(path)
                            
                            if path not in category_profiles:
                                category_profiles[path] = CategoryProfile(path=path, level=level)
                            
                            profile = category_profiles[path]
                            profile.review_count += 1
                            
                            for arch, score in archetypes.items():
                                profile.archetypes[arch] = profile.archetypes.get(arch, 0) + score
                            
                            for fw, score in frameworks.items():
                                profile.frameworks[fw] = profile.frameworks.get(fw, 0) + score
                        
                    except json.JSONDecodeError:
                        continue
                    except Exception:
                        continue
                    
                    stats["reviews_processed"] = i + 1
                    
                    if (i + 1) % 500000 == 0:
                        elapsed = time.time() - start_time
                        rate = (i + 1) / elapsed
                        logger.info(f"  {i+1:,} reviews ({rate:.0f}/sec), "
                                   f"matched: {stats['reviews_matched']:,}, "
                                   f"paths: {len(stats['paths_seen'])}")
        except Exception as e:
            logger.error(f"Error reading review file: {e}")
        
        elapsed = time.time() - start_time
        stats["reviews_processed"] = i + 1 if i > 0 else 0
        logger.info(f"Completed: {stats['reviews_processed']:,} reviews in {elapsed:.1f}s")
        
        # Save checkpoint
        checkpoint = self._save_checkpoint(category, category_profiles, stats)
        
        # Embed to Neo4j
        neo4j_count = self._embed_to_neo4j(category, category_profiles)
        
        return {
            "category": category,
            "reviews_processed": stats["reviews_processed"],
            "reviews_matched": stats["reviews_matched"],
            "products": len(stats["products_seen"]),
            "paths": len(stats["paths_seen"]),
            "profiles": len(category_profiles),
            "neo4j_embedded": neo4j_count,
            "time_seconds": elapsed
        }
    
    def _extract_psychology(self, text: str) -> Tuple[Dict[str, float], Dict[str, float]]:
        """Extract psychological signals"""
        if not text:
            return {}, {}
        
        text_lower = text.lower()
        words = set(re.findall(r'\b\w+\b', text_lower))
        
        archetypes = {}
        for arch, patterns in ARCHETYPE_PATTERNS.items():
            score = sum(1 for p in patterns if p in words)
            if score > 0:
                archetypes[arch] = score
        
        frameworks = {}
        for fw_name, patterns in FRAMEWORK_PATTERNS.items():
            score = sum(1 for p in patterns if p in words)
            if score > 0:
                frameworks[fw_name] = score
        
        return archetypes, frameworks
    
    def _save_checkpoint(self, category: str, profiles: Dict[str, CategoryProfile], stats: Dict) -> Path:
        """Save checkpoint locally"""
        checkpoint_file = DATA_DIR / f"checkpoint_subcategory_{category}.json"
        
        profiles_data = {}
        for path, profile in profiles.items():
            profiles_data[path] = {
                "path": profile.path,
                "level": profile.level,
                "review_count": profile.review_count,
                "archetypes": profile.archetypes,
                "frameworks": profile.frameworks
            }
        
        checkpoint = {
            "category": category,
            "stats": {
                "reviews_processed": stats["reviews_processed"],
                "reviews_matched": stats["reviews_matched"],
                "products": len(stats["products_seen"]),
                "paths": len(stats["paths_seen"])
            },
            "profiles": profiles_data
        }
        
        with open(checkpoint_file, 'w') as f:
            json.dump(checkpoint, f)
        
        logger.info(f"Saved: {checkpoint_file}")
        return checkpoint_file
    
    def _embed_to_neo4j(self, category: str, profiles: Dict[str, CategoryProfile]) -> int:
        """Embed profiles to Neo4j"""
        try:
            from neo4j import GraphDatabase
            driver = GraphDatabase.driver(
                "bolt://localhost:7687",
                auth=("neo4j", "atomofthought")
            )
        except Exception as e:
            logger.warning(f"Neo4j not available: {e}")
            return 0
        
        count = 0
        with driver.session() as session:
            for path, profile in profiles.items():
                try:
                    session.run("""
                        MERGE (p:SubCategoryProfile {category_path: $path})
                        SET p.category = $category,
                            p.level = $level,
                            p.review_count = $review_count,
                            p.arch_achiever = $arch_achiever,
                            p.arch_explorer = $arch_explorer,
                            p.arch_connector = $arch_connector,
                            p.arch_guardian = $arch_guardian,
                            p.arch_pragmatist = $arch_pragmatist
                    """, {
                        "path": path,
                        "category": category,
                        "level": profile.level,
                        "review_count": profile.review_count,
                        "arch_achiever": profile.archetypes.get("achiever", 0),
                        "arch_explorer": profile.archetypes.get("explorer", 0),
                        "arch_connector": profile.archetypes.get("connector", 0),
                        "arch_guardian": profile.archetypes.get("guardian", 0),
                        "arch_pragmatist": profile.archetypes.get("pragmatist", 0),
                    })
                    count += 1
                except:
                    continue
        
        driver.close()
        logger.info(f"Embedded {count} profiles to Neo4j")
        return count
    
    def run_all(self, skip_completed: bool = True) -> List[Dict]:
        """Process all categories"""
        results = []
        
        # Discover categories
        categories = self.discover_categories()
        logger.info(f"\nFound {len(categories)} categories to process")
        
        # Skip categories
        SKIP_CATEGORIES = {"Video_Games", "Unknown"}
        categories = [c for c in categories if c not in SKIP_CATEGORIES]
        
        # Check for already completed
        if skip_completed:
            completed = []
            for cat in categories:
                checkpoint = DATA_DIR / f"checkpoint_subcategory_{cat}.json"
                if checkpoint.exists():
                    completed.append(cat)
            
            categories = [c for c in categories if c not in completed]
            logger.info(f"Skipping {len(completed)} already completed")
            logger.info(f"Will process {len(categories)} categories")
        
        # Process each
        for i, category in enumerate(categories, 1):
            logger.info(f"\n[{i}/{len(categories)}] Processing {category}")
            
            try:
                result = self.process_category(category)
                results.append(result)
                
                # Summary
                logger.info(f"✅ {category}: {result['reviews_matched']:,} reviews, "
                           f"{result['paths']} paths, {result['neo4j_embedded']} embedded")
                
            except Exception as e:
                logger.error(f"❌ {category}: {e}")
                results.append({"category": category, "error": str(e)})
        
        return results


def main():
    print("=" * 70)
    print("BATCH AMAZON SUB-CATEGORY INGESTION")
    print("=" * 70)
    print(f"\nExternal drive: {EXTERNAL_DRIVE}")
    print(f"Output: {DATA_DIR}")
    
    # Check external drive
    if not EXTERNAL_DRIVE.exists():
        print(f"\n❌ External drive not found: {EXTERNAL_DRIVE}")
        sys.exit(1)
    
    ingestor = BatchSubcategoryIngestor()
    results = ingestor.run_all(skip_completed=True)
    
    # Final summary
    print("\n" + "=" * 70)
    print("BATCH COMPLETE")
    print("=" * 70)
    
    total_reviews = sum(r.get("reviews_matched", 0) for r in results)
    total_paths = sum(r.get("paths", 0) for r in results)
    total_embedded = sum(r.get("neo4j_embedded", 0) for r in results)
    
    print(f"\nCategories processed: {len(results)}")
    print(f"Total reviews matched: {total_reviews:,}")
    print(f"Total sub-category paths: {total_paths:,}")
    print(f"Total Neo4j profiles: {total_embedded:,}")


if __name__ == "__main__":
    main()
