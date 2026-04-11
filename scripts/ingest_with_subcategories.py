#!/usr/bin/env python3
"""
Amazon Review Ingestion with Sub-Category Linking

Processes reviews AND links them to the proper 6-level sub-category hierarchy.
Creates psychological profiles at each category level for granular targeting.

Usage:
    python3 scripts/ingest_with_subcategories.py --category Beauty_and_Personal_Care
"""

import json
import logging
import argparse
import re
import time
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent.parent
AMAZON_DIR = BASE_DIR / "amazon"
DATA_DIR = BASE_DIR / "data" / "learning"

# Import the psychological frameworks
import sys
sys.path.insert(0, str(BASE_DIR / "adam" / "intelligence"))

try:
    from deep_psycholinguistic_framework import PSYCHOLOGICAL_FRAMEWORKS, extract_all_frameworks
    FRAMEWORKS_AVAILABLE = True
except ImportError:
    FRAMEWORKS_AVAILABLE = False
    logger.warning("Deep psycholinguistic framework not available, using basic extraction")


# Basic framework patterns for fallback
BASIC_PATTERNS = {
    "regulatory_focus": {
        "promotion": ["achieve", "gain", "accomplish", "success", "win", "grow", "advance", "opportunity"],
        "prevention": ["safe", "secure", "protect", "avoid", "prevent", "careful", "responsible", "duty"]
    },
    "temporal_orientation": {
        "future": ["will", "going to", "plan", "hope", "expect", "anticipate", "future"],
        "present": ["now", "today", "currently", "enjoying", "using", "love"],
        "past": ["was", "used to", "remember", "before", "always had"]
    },
    "construal_level": {
        "abstract": ["concept", "idea", "overall", "generally", "philosophy", "principle"],
        "concrete": ["specifically", "exactly", "particular", "detail", "precise"]
    },
    "emotional_intensity": {
        "high": ["amazing", "incredible", "absolutely", "love", "hate", "terrible", "fantastic", "awful"],
        "medium": ["good", "nice", "fine", "okay", "decent", "solid"],
        "low": ["adequate", "sufficient", "functional", "works"]
    },
    "social_orientation": {
        "social": ["everyone", "people", "friends", "family", "recommend", "share", "gift"],
        "individual": ["I", "my", "personally", "myself", "me"]
    }
}

# Archetype patterns
ARCHETYPE_PATTERNS = {
    "achiever": ["best", "premium", "quality", "performance", "results", "effective", "professional", "success"],
    "explorer": ["try", "new", "different", "discover", "experiment", "curious", "unique", "adventure"],
    "connector": ["gift", "share", "recommend", "friends", "family", "together", "everyone", "community"],
    "guardian": ["safe", "reliable", "trust", "consistent", "dependable", "protect", "secure", "traditional"],
    "pragmatist": ["value", "price", "affordable", "practical", "works", "functional", "worth", "budget"]
}


@dataclass
class SubCategoryProfile:
    """Psychological profile for a sub-category"""
    category_path: str
    level: int
    archetype_totals: Dict[str, float] = field(default_factory=dict)
    framework_totals: Dict[str, float] = field(default_factory=dict)
    dimension_totals: Dict[str, float] = field(default_factory=dict)
    review_count: int = 0
    product_count: int = 0


class SubCategoryIngestor:
    """Ingests reviews with sub-category awareness"""
    
    def __init__(self, category: str):
        self.category = category
        self.review_file = AMAZON_DIR / f"{category}.jsonl"
        self.meta_file = AMAZON_DIR / f"meta_{category}.jsonl"
        
        # Mappings
        self.asin_to_categories: Dict[str, List[str]] = {}  # ASIN -> category path list
        self.asin_to_title: Dict[str, str] = {}
        
        # Profiles by category path
        self.category_profiles: Dict[str, SubCategoryProfile] = {}
        
        # Product-level profiles
        self.product_profiles: Dict[str, Dict[str, float]] = {}
        
        # Stats
        self.stats = {
            "reviews_processed": 0,
            "reviews_matched": 0,
            "products_seen": set(),
            "category_paths_seen": set()
        }
    
    def load_meta_mapping(self) -> int:
        """Load ASIN -> sub-category mapping from meta file"""
        logger.info(f"Loading meta file: {self.meta_file}")
        
        count = 0
        with open(self.meta_file) as f:
            for line in f:
                try:
                    data = json.loads(line)
                    asin = data.get("parent_asin") or data.get("asin")
                    categories = data.get("categories", [])
                    title = data.get("title", "")
                    
                    if asin and categories:
                        self.asin_to_categories[asin] = categories
                        self.asin_to_title[asin] = title
                        count += 1
                        
                except:
                    continue
        
        logger.info(f"Loaded {count:,} product -> category mappings")
        return count
    
    def extract_psychology(self, text: str) -> Tuple[Dict[str, float], Dict[str, float], Dict[str, float]]:
        """Extract psychological signals from review text"""
        if not text:
            return {}, {}, {}
        
        text_lower = text.lower()
        words = set(re.findall(r'\b\w+\b', text_lower))
        
        # Extract archetypes
        archetypes = {}
        for arch, patterns in ARCHETYPE_PATTERNS.items():
            score = sum(1 for p in patterns if p in words)
            if score > 0:
                archetypes[arch] = score
        
        # Extract frameworks
        frameworks = {}
        for fw_name, fw_dims in BASIC_PATTERNS.items():
            for dim_name, patterns in fw_dims.items():
                score = sum(1 for p in patterns if p in words)
                if score > 0:
                    key = f"{fw_name}.{dim_name}"
                    frameworks[key] = score
        
        # Use deep extraction if available
        dimensions = {}
        if FRAMEWORKS_AVAILABLE:
            try:
                deep_results = extract_all_frameworks(text)
                for fw_name, fw_data in deep_results.items():
                    if isinstance(fw_data, dict):
                        for dim, val in fw_data.items():
                            if isinstance(val, (int, float)) and val > 0:
                                dimensions[f"{fw_name}.{dim}"] = val
            except:
                pass
        
        return archetypes, frameworks, dimensions
    
    def process_reviews(self, max_reviews: int = None, batch_log: int = 100000) -> Dict[str, int]:
        """Process all reviews with sub-category linking"""
        logger.info(f"Processing reviews: {self.review_file}")
        
        start_time = time.time()
        
        with open(self.review_file) as f:
            for i, line in enumerate(f):
                if max_reviews and i >= max_reviews:
                    break
                
                try:
                    review = json.loads(line)
                    self._process_single_review(review)
                    
                except json.JSONDecodeError:
                    continue
                except Exception as e:
                    continue
                
                if (i + 1) % batch_log == 0:
                    elapsed = time.time() - start_time
                    rate = (i + 1) / elapsed
                    logger.info(f"Processed {i+1:,} reviews ({rate:.0f}/sec), "
                               f"matched: {self.stats['reviews_matched']:,}, "
                               f"paths: {len(self.stats['category_paths_seen'])}")
        
        self.stats["reviews_processed"] = i + 1
        
        elapsed = time.time() - start_time
        logger.info(f"Completed: {self.stats['reviews_processed']:,} reviews in {elapsed:.1f}s "
                   f"({self.stats['reviews_processed']/elapsed:.0f}/sec)")
        
        return self.stats
    
    def _process_single_review(self, review: Dict[str, Any]):
        """Process a single review"""
        asin = review.get("parent_asin") or review.get("asin")
        text = review.get("text", "")
        rating = review.get("rating", 0)
        
        if not asin or not text:
            return
        
        # Get category path for this product
        categories = self.asin_to_categories.get(asin)
        if not categories:
            return
        
        self.stats["reviews_matched"] += 1
        self.stats["products_seen"].add(asin)
        
        # Extract psychology
        archetypes, frameworks, dimensions = self.extract_psychology(text)
        
        if not archetypes and not frameworks:
            return
        
        # Update profiles at EACH level of the category hierarchy
        for level in range(len(categories)):
            path = " > ".join(categories[:level + 1])
            self.stats["category_paths_seen"].add(path)
            
            # Get or create profile for this path
            if path not in self.category_profiles:
                self.category_profiles[path] = SubCategoryProfile(
                    category_path=path,
                    level=level
                )
            
            profile = self.category_profiles[path]
            profile.review_count += 1
            
            # Accumulate archetypes
            for arch, score in archetypes.items():
                profile.archetype_totals[arch] = profile.archetype_totals.get(arch, 0) + score
            
            # Accumulate frameworks
            for fw, score in frameworks.items():
                profile.framework_totals[fw] = profile.framework_totals.get(fw, 0) + score
            
            # Accumulate dimensions
            for dim, score in dimensions.items():
                profile.dimension_totals[dim] = profile.dimension_totals.get(dim, 0) + score
        
        # Update product-level profile
        if asin not in self.product_profiles:
            self.product_profiles[asin] = {
                "category_path": " > ".join(categories),
                "archetypes": {},
                "review_count": 0
            }
        
        prod = self.product_profiles[asin]
        prod["review_count"] += 1
        for arch, score in archetypes.items():
            prod["archetypes"][arch] = prod["archetypes"].get(arch, 0) + score
    
    def save_checkpoint(self) -> Path:
        """Save checkpoint with sub-category profiles"""
        checkpoint_file = DATA_DIR / f"checkpoint_subcategory_{self.category}.json"
        
        # Convert profiles to serializable format
        profiles_data = {}
        for path, profile in self.category_profiles.items():
            profiles_data[path] = {
                "category_path": profile.category_path,
                "level": profile.level,
                "review_count": profile.review_count,
                "archetype_totals": profile.archetype_totals,
                "framework_totals": profile.framework_totals,
                "dimension_totals": dict(list(profile.dimension_totals.items())[:100])  # Top 100
            }
        
        checkpoint = {
            "category": self.category,
            "stats": {
                "reviews_processed": self.stats["reviews_processed"],
                "reviews_matched": self.stats["reviews_matched"],
                "products_seen": len(self.stats["products_seen"]),
                "category_paths": len(self.stats["category_paths_seen"])
            },
            "category_profiles": profiles_data,
            "product_count": len(self.product_profiles)
        }
        
        with open(checkpoint_file, 'w') as f:
            json.dump(checkpoint, f, indent=2)
        
        logger.info(f"Saved checkpoint: {checkpoint_file}")
        return checkpoint_file
    
    def embed_to_neo4j(self) -> Dict[str, int]:
        """Embed sub-category profiles to Neo4j"""
        try:
            from neo4j import GraphDatabase
            driver = GraphDatabase.driver(
                "bolt://localhost:7687",
                auth=("neo4j", "atomofthought")
            )
        except Exception as e:
            logger.warning(f"Could not connect to Neo4j: {e}")
            return {"embedded": 0}
        
        stats = {"profiles_embedded": 0, "relationships": 0}
        
        with driver.session() as session:
            # Create schema
            session.run("""
                CREATE CONSTRAINT subcat_profile_path IF NOT EXISTS
                FOR (p:SubCategoryProfile) REQUIRE p.category_path IS UNIQUE
            """)
            
            # Embed each profile
            for path, profile in self.category_profiles.items():
                # Create profile node
                query = """
                MERGE (p:SubCategoryProfile {category_path: $path})
                SET p.level = $level,
                    p.review_count = $review_count,
                    p.category = $category,
                    p.arch_achiever = $arch_achiever,
                    p.arch_explorer = $arch_explorer,
                    p.arch_connector = $arch_connector,
                    p.arch_guardian = $arch_guardian,
                    p.arch_pragmatist = $arch_pragmatist
                """
                
                session.run(query, {
                    "path": path,
                    "level": profile.level,
                    "review_count": profile.review_count,
                    "category": self.category,
                    "arch_achiever": profile.archetype_totals.get("achiever", 0),
                    "arch_explorer": profile.archetype_totals.get("explorer", 0),
                    "arch_connector": profile.archetype_totals.get("connector", 0),
                    "arch_guardian": profile.archetype_totals.get("guardian", 0),
                    "arch_pragmatist": profile.archetype_totals.get("pragmatist", 0),
                })
                stats["profiles_embedded"] += 1
                
                # Link to AmazonCategoryPath if exists
                session.run("""
                    MATCH (p:SubCategoryProfile {category_path: $path})
                    MATCH (acp:AmazonCategoryPath {full_path: $path})
                    MERGE (p)-[:PROFILES]->(acp)
                """, {"path": path})
                stats["relationships"] += 1
        
        driver.close()
        logger.info(f"Embedded {stats['profiles_embedded']} profiles to Neo4j")
        return stats


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--category", default="Beauty_and_Personal_Care")
    parser.add_argument("--max-reviews", type=int, default=None)
    parser.add_argument("--batch-log", type=int, default=100000)
    args = parser.parse_args()
    
    print("=" * 70)
    print(f"SUB-CATEGORY AWARE INGESTION: {args.category}")
    print("=" * 70)
    
    ingestor = SubCategoryIngestor(args.category)
    
    # Load meta mapping
    print("\n1. Loading product -> sub-category mapping...")
    mapping_count = ingestor.load_meta_mapping()
    
    # Process reviews
    print("\n2. Processing reviews with sub-category linking...")
    stats = ingestor.process_reviews(max_reviews=args.max_reviews, batch_log=args.batch_log)
    
    # Save checkpoint
    print("\n3. Saving checkpoint...")
    checkpoint_file = ingestor.save_checkpoint()
    
    # Embed to Neo4j
    print("\n4. Embedding to Neo4j...")
    embed_stats = ingestor.embed_to_neo4j()
    
    print("\n" + "=" * 70)
    print("INGESTION COMPLETE")
    print("=" * 70)
    print(f"\nReviews processed: {stats['reviews_processed']:,}")
    print(f"Reviews matched to sub-categories: {stats['reviews_matched']:,}")
    print(f"Unique products: {len(stats['products_seen']):,}")
    print(f"Unique category paths profiled: {len(stats['category_paths_seen'])}")
    print(f"Neo4j profiles embedded: {embed_stats.get('profiles_embedded', 0)}")
    print(f"\nCheckpoint: {checkpoint_file}")


if __name__ == "__main__":
    main()
