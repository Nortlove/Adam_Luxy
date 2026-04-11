#!/usr/bin/env python3
# =============================================================================
# ADAM Platform - Amazon Corpus Learning Pipeline
# Location: scripts/run_amazon_corpus_learning.py
# =============================================================================

"""
AMAZON CORPUS LEARNING PIPELINE

Processes the complete Amazon review corpus (317GB, 50 categories) through
ADAM's robust learning system using the same 5 Analysis Types as our
multi-source learning:

DATA SOURCES (317GB Total):
- Home_and_Kitchen.jsonl (29GB)
- Clothing_Shoes_and_Jewelry.jsonl (26GB)
- Electronics.jsonl (21GB)
- Books.jsonl (19GB)
- Kindle_Store.jsonl (15GB)
- Tools_and_Home_Improvement.jsonl (12GB)
- Health_and_Household.jsonl (11GB)
- Beauty_and_Personal_Care.jsonl (10GB)
- ... and 42 more categories

5 ANALYSIS TYPES (NO full psycholinguistics):
1. Archetype Classification - Assign archetypes from behavioral signals
2. Category→Archetype Priors - What archetypes buy what categories
3. Cross-Category Behavior - Who buys what together (via reviewer_id)
4. Reviewer Lifecycle Patterns - New vs experienced reviewers
5. Brand Loyalty Patterns - Single vs multi-brand behavior

ADDITIONAL AMAZON-SPECIFIC LEARNING:
- Verified purchase weighting
- Helpful vote influence
- Price tier analysis (from metadata)
- Product category hierarchies
- Review quality scoring

OUTPUT:
- Merged cold-start priors with existing learning
- Amazon-specific category priors
- Brand→Archetype mappings for 1000s of brands
- Cross-category purchase patterns
- Reviewer expertise profiles

Usage:
    # Full processing (takes 2-4 hours for 317GB)
    python scripts/run_amazon_corpus_learning.py
    
    # Test mode (sample only, ~5 minutes)
    python scripts/run_amazon_corpus_learning.py --test
    
    # Resume from checkpoint
    python scripts/run_amazon_corpus_learning.py --resume
    
    # Specific categories only
    python scripts/run_amazon_corpus_learning.py --categories Electronics Books
    
    # Limit reviews per category
    python scripts/run_amazon_corpus_learning.py --max-per-category 100000
"""

import argparse
import asyncio
import json
import logging
import sys
import time
import gzip
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Set, Tuple
import hashlib
import re

import numpy as np

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Configure logging
log_dir = project_root / "logs"
log_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(log_dir / 'amazon_corpus_learning.log', mode='a'),
    ]
)
logger = logging.getLogger(__name__)


# =============================================================================
# PATHS
# =============================================================================

AMAZON_DATA_DIR = project_root / "amazon"
LEARNING_DATA_DIR = project_root / "data" / "learning"
LEARNING_DATA_DIR.mkdir(parents=True, exist_ok=True)

CHECKPOINT_PATH = LEARNING_DATA_DIR / "amazon_learning_checkpoint.json"
AMAZON_PRIORS_PATH = LEARNING_DATA_DIR / "amazon_coldstart_priors.json"
MERGED_PRIORS_PATH = LEARNING_DATA_DIR / "complete_coldstart_priors.json"


# =============================================================================
# CATEGORY MAPPING (Amazon categories → Learning categories)
# =============================================================================

AMAZON_CATEGORY_MAP = {
    # Product categories
    "Electronics": "Electronics",
    "Cell_Phones_and_Accessories": "Electronics",
    "Computers": "Electronics",
    "Camera_and_Photo": "Electronics",
    "Home_and_Kitchen": "Home_Kitchen",
    "Tools_and_Home_Improvement": "Home_Improvement",
    "Patio_Lawn_and_Garden": "Home_Garden",
    "Automotive": "Automotive",
    "Sports_and_Outdoors": "Sports_Outdoors",
    "Health_and_Household": "Health_Wellness",
    "Beauty_and_Personal_Care": "Beauty",
    "Grocery_and_Gourmet_Food": "Food_Grocery",
    "Pet_Supplies": "Pet_Care",
    "Baby_Products": "Baby_Kids",
    "Toys_and_Games": "Toys_Games",
    "Office_Products": "Office",
    "Industrial_and_Scientific": "Industrial",
    "Arts_Crafts_and_Sewing": "Arts_Crafts",
    "Musical_Instruments": "Music_Instruments",
    
    # Media categories
    "Books": "Books",
    "Kindle_Store": "Books_Digital",
    "Movies_and_TV": "Movies_TV",
    "CDs_and_Vinyl": "Music",
    "Digital_Music": "Music_Digital",
    "Video_Games": "Gaming",
    "Software": "Software",
    "Apps_for_Android": "Apps",
    
    # Fashion categories
    "Clothing_Shoes_and_Jewelry": "Fashion",
    "Amazon_Fashion": "Fashion",
    "Luxury_Beauty": "Luxury_Beauty",
    
    # Other
    "Magazine_Subscriptions": "Subscriptions",
    "Gift_Cards": "Gift_Cards",
    "Appliances": "Appliances",
    "All_Beauty": "Beauty",
}


# =============================================================================
# LIGHTWEIGHT ARCHETYPE CLASSIFIER (Same as multi-source)
# =============================================================================

class LightweightArchetypeClassifier:
    """
    Classifies reviews into archetypes using behavioral signals only.
    
    No full psycholinguistic analysis - uses:
    - Rating patterns
    - Review length
    - Sentiment keywords
    - Category context
    - Helpful votes
    - Verified purchase status
    """
    
    # Keyword-based sentiment indicators
    PROMOTION_WORDS = {"love", "amazing", "best", "excellent", "perfect", "great", "awesome", "fantastic", "incredible", "wonderful"}
    PREVENTION_WORDS = {"safe", "reliable", "trust", "quality", "durable", "secure", "warranty", "solid", "dependable", "sturdy"}
    ANALYTICAL_WORDS = {"however", "although", "compared", "versus", "ratio", "performance", "specs", "features", "analysis", "review"}
    SOCIAL_WORDS = {"recommend", "everyone", "friends", "family", "gift", "share", "community", "others", "bought", "gave"}
    EXPLORER_WORDS = {"tried", "discovered", "new", "different", "unique", "interesting", "curious", "experiment", "adventure"}
    
    # Category → Default archetype weighting
    CATEGORY_ARCHETYPE_BIAS = {
        "electronics": {"Achiever": 0.35, "Analyzer": 0.25, "Guardian": 0.20, "Explorer": 0.15, "Connector": 0.05},
        "automotive": {"Guardian": 0.35, "Achiever": 0.25, "Pragmatist": 0.20, "Connector": 0.15, "Explorer": 0.05},
        "beauty": {"Connector": 0.35, "Achiever": 0.25, "Explorer": 0.20, "Guardian": 0.15, "Analyzer": 0.05},
        "fashion": {"Connector": 0.30, "Explorer": 0.25, "Achiever": 0.20, "Guardian": 0.15, "Analyzer": 0.10},
        "books": {"Analyzer": 0.35, "Explorer": 0.25, "Connector": 0.20, "Achiever": 0.15, "Guardian": 0.05},
        "gaming": {"Explorer": 0.35, "Achiever": 0.30, "Connector": 0.20, "Analyzer": 0.10, "Guardian": 0.05},
        "movies": {"Connector": 0.30, "Explorer": 0.25, "Achiever": 0.20, "Analyzer": 0.15, "Guardian": 0.10},
        "music": {"Connector": 0.35, "Explorer": 0.30, "Achiever": 0.15, "Analyzer": 0.15, "Guardian": 0.05},
        "home": {"Guardian": 0.30, "Pragmatist": 0.25, "Achiever": 0.20, "Connector": 0.15, "Explorer": 0.10},
        "sports": {"Achiever": 0.35, "Explorer": 0.25, "Connector": 0.20, "Guardian": 0.15, "Pragmatist": 0.05},
        "health": {"Guardian": 0.35, "Connector": 0.25, "Achiever": 0.20, "Analyzer": 0.15, "Explorer": 0.05},
        "food": {"Connector": 0.30, "Explorer": 0.25, "Guardian": 0.20, "Achiever": 0.15, "Pragmatist": 0.10},
        "baby": {"Guardian": 0.40, "Connector": 0.30, "Achiever": 0.15, "Pragmatist": 0.10, "Explorer": 0.05},
        "pet": {"Connector": 0.35, "Guardian": 0.30, "Achiever": 0.15, "Explorer": 0.15, "Pragmatist": 0.05},
        "toys": {"Connector": 0.30, "Explorer": 0.25, "Achiever": 0.20, "Guardian": 0.15, "Pragmatist": 0.10},
        "office": {"Pragmatist": 0.30, "Achiever": 0.25, "Guardian": 0.20, "Analyzer": 0.15, "Connector": 0.10},
    }
    
    def classify(
        self,
        text: str,
        rating: float,
        category: str,
        review_length: Optional[int] = None,
        helpful_votes: int = 0,
        verified_purchase: bool = False,
    ) -> Tuple[str, float]:
        """
        Classify a review into an archetype.
        
        Returns: (archetype, confidence)
        """
        text_lower = text.lower() if text else ""
        words = set(re.findall(r'\b\w+\b', text_lower))
        
        # Start with category bias
        category_key = self._normalize_category(category)
        base_weights = self.CATEGORY_ARCHETYPE_BIAS.get(
            category_key, 
            {"Connector": 0.25, "Achiever": 0.20, "Explorer": 0.20, "Guardian": 0.20, "Pragmatist": 0.10, "Analyzer": 0.05}
        ).copy()
        
        # Adjust by keyword presence
        promotion_score = len(words & self.PROMOTION_WORDS) / max(len(self.PROMOTION_WORDS), 1)
        prevention_score = len(words & self.PREVENTION_WORDS) / max(len(self.PREVENTION_WORDS), 1)
        analytical_score = len(words & self.ANALYTICAL_WORDS) / max(len(self.ANALYTICAL_WORDS), 1)
        social_score = len(words & self.SOCIAL_WORDS) / max(len(self.SOCIAL_WORDS), 1)
        explorer_score = len(words & self.EXPLORER_WORDS) / max(len(self.EXPLORER_WORDS), 1)
        
        # Apply keyword adjustments
        if promotion_score > 0.1:
            base_weights["Achiever"] = base_weights.get("Achiever", 0.2) + 0.1
        
        if prevention_score > 0.1:
            base_weights["Guardian"] = base_weights.get("Guardian", 0.15) + 0.15
        
        if analytical_score > 0.1:
            base_weights["Analyzer"] = base_weights.get("Analyzer", 0.05) + 0.15
        
        if social_score > 0.1:
            base_weights["Connector"] = base_weights.get("Connector", 0.25) + 0.15
        
        if explorer_score > 0.1:
            base_weights["Explorer"] = base_weights.get("Explorer", 0.2) + 0.15
        
        # Adjust by rating extremity
        if rating >= 4.5:
            base_weights["Connector"] = base_weights.get("Connector", 0.25) + 0.05
            base_weights["Achiever"] = base_weights.get("Achiever", 0.2) + 0.05
        elif rating <= 2:
            base_weights["Analyzer"] = base_weights.get("Analyzer", 0.05) + 0.1
            base_weights["Guardian"] = base_weights.get("Guardian", 0.15) + 0.05
        
        # Adjust by review length (longer reviews = more analytical)
        if review_length is not None:
            if review_length > 500:
                base_weights["Analyzer"] = base_weights.get("Analyzer", 0.05) + 0.1
            elif review_length > 200:
                base_weights["Achiever"] = base_weights.get("Achiever", 0.2) + 0.05
            elif review_length < 50:
                base_weights["Pragmatist"] = base_weights.get("Pragmatist", 0.1) + 0.05
        
        # Adjust by helpful votes (high votes = more analytical/connector)
        if helpful_votes > 10:
            base_weights["Analyzer"] = base_weights.get("Analyzer", 0.05) + 0.1
            base_weights["Connector"] = base_weights.get("Connector", 0.25) + 0.05
        
        # Verified purchase = more trustworthy signal
        if verified_purchase:
            base_weights["Guardian"] = base_weights.get("Guardian", 0.15) + 0.05
        
        # Normalize and select
        total = sum(base_weights.values())
        normalized = {k: v / total for k, v in base_weights.items()}
        
        archetype = max(normalized, key=normalized.get)
        confidence = normalized[archetype]
        
        return archetype, confidence
    
    def _normalize_category(self, category: str) -> str:
        """Normalize category name for lookup."""
        cat_lower = category.lower().replace("_", " ").replace("-", " ")
        
        # Map to base categories
        if any(x in cat_lower for x in ["electronic", "phone", "computer", "camera"]):
            return "electronics"
        elif any(x in cat_lower for x in ["auto", "car", "vehicle"]):
            return "automotive"
        elif any(x in cat_lower for x in ["beauty", "cosmetic", "skincare"]):
            return "beauty"
        elif any(x in cat_lower for x in ["fashion", "clothing", "shoes", "jewelry"]):
            return "fashion"
        elif any(x in cat_lower for x in ["book", "kindle", "reading"]):
            return "books"
        elif any(x in cat_lower for x in ["game", "gaming", "video game"]):
            return "gaming"
        elif any(x in cat_lower for x in ["movie", "tv", "film", "video"]):
            return "movies"
        elif any(x in cat_lower for x in ["music", "cd", "vinyl", "audio"]):
            return "music"
        elif any(x in cat_lower for x in ["home", "kitchen", "furniture", "garden"]):
            return "home"
        elif any(x in cat_lower for x in ["sport", "outdoor", "fitness"]):
            return "sports"
        elif any(x in cat_lower for x in ["health", "medical", "wellness"]):
            return "health"
        elif any(x in cat_lower for x in ["food", "grocery", "gourmet"]):
            return "food"
        elif any(x in cat_lower for x in ["baby", "infant", "child"]):
            return "baby"
        elif any(x in cat_lower for x in ["pet", "dog", "cat"]):
            return "pet"
        elif any(x in cat_lower for x in ["toy", "game"]):
            return "toys"
        elif any(x in cat_lower for x in ["office", "business"]):
            return "office"
        
        return "general"


# =============================================================================
# CHECKPOINT MANAGEMENT
# =============================================================================

@dataclass
class AmazonLearningCheckpoint:
    """Checkpoint for resumable Amazon learning."""
    started_at: str = ""
    last_updated: str = ""
    completed_categories: List[str] = field(default_factory=list)
    current_category: str = ""
    current_position: int = 0
    
    # Statistics
    total_reviews_processed: int = 0
    total_unique_reviewers: int = 0
    total_unique_products: int = 0
    total_unique_brands: int = 0
    
    # Archetype distribution
    archetype_counts: Dict[str, int] = field(default_factory=dict)
    
    # Category statistics
    category_review_counts: Dict[str, int] = field(default_factory=dict)
    
    def save(self):
        """Save checkpoint."""
        self.last_updated = datetime.now().isoformat()
        with open(CHECKPOINT_PATH, 'w') as f:
            json.dump(asdict(self), f, indent=2)
    
    @classmethod
    def load(cls) -> 'AmazonLearningCheckpoint':
        """Load checkpoint."""
        if CHECKPOINT_PATH.exists():
            with open(CHECKPOINT_PATH) as f:
                data = json.load(f)
                return cls(**data)
        return cls(started_at=datetime.now().isoformat())


# =============================================================================
# AGGREGATE COLLECTOR (Same structure as multi-source)
# =============================================================================

@dataclass
class AmazonColdStartAggregator:
    """Collects aggregate statistics for cold-start learning from Amazon."""
    
    # Category → Archetype counts
    category_archetypes: Dict[str, Dict[str, int]] = field(default_factory=lambda: defaultdict(lambda: defaultdict(int)))
    
    # Brand → Archetype counts
    brand_archetypes: Dict[str, Dict[str, int]] = field(default_factory=lambda: defaultdict(lambda: defaultdict(int)))
    
    # Product → Archetype counts (limited to top products)
    product_archetypes: Dict[str, Dict[str, int]] = field(default_factory=lambda: defaultdict(lambda: defaultdict(int)))
    
    # Reviewer → Categories reviewed
    reviewer_categories: Dict[str, Set[str]] = field(default_factory=lambda: defaultdict(set))
    
    # Reviewer → Brands reviewed
    reviewer_brands: Dict[str, Set[str]] = field(default_factory=lambda: defaultdict(set))
    
    # Reviewer → Review count (for lifecycle)
    reviewer_counts: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    
    # Reviewer → Ratings (for pattern analysis)
    reviewer_ratings: Dict[str, List[float]] = field(default_factory=lambda: defaultdict(list))
    
    # Reviewer → Archetype assignments
    reviewer_archetypes: Dict[str, List[str]] = field(default_factory=lambda: defaultdict(list))
    
    # Category co-occurrence
    category_pairs: Dict[Tuple[str, str], int] = field(default_factory=lambda: defaultdict(int))
    
    # Source statistics
    source_stats: Dict[str, Dict[str, int]] = field(default_factory=lambda: defaultdict(lambda: {"reviews": 0, "unique_reviewers": 0}))
    
    # Price tier patterns (from metadata)
    price_tiers: Dict[str, Dict[str, int]] = field(default_factory=lambda: defaultdict(lambda: defaultdict(int)))
    
    # Verified purchase patterns
    verified_archetypes: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    unverified_archetypes: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    
    # Helpful vote patterns
    helpful_archetypes: Dict[str, List[int]] = field(default_factory=lambda: defaultdict(list))
    
    def add_review(
        self,
        source: str,
        reviewer_id: str,
        category: str,
        brand: Optional[str],
        product_id: Optional[str],
        archetype: str,
        rating: float,
        verified: bool = False,
        helpful_votes: int = 0,
        price: Optional[float] = None,
    ) -> None:
        """Add a single review to aggregates."""
        
        # Category → Archetype
        self.category_archetypes[category][archetype] += 1
        
        # Brand → Archetype
        if brand:
            self.brand_archetypes[brand][archetype] += 1
        
        # Product → Archetype (limit storage)
        if product_id and len(self.product_archetypes) < 10000:
            self.product_archetypes[product_id][archetype] += 1
        
        # Reviewer tracking
        self.reviewer_categories[reviewer_id].add(category)
        if brand:
            self.reviewer_brands[reviewer_id].add(brand)
        self.reviewer_counts[reviewer_id] += 1
        
        # Only track first 5 ratings per reviewer (memory management)
        if len(self.reviewer_ratings[reviewer_id]) < 5:
            self.reviewer_ratings[reviewer_id].append(rating)
        
        # Only track first 3 archetypes per reviewer
        if len(self.reviewer_archetypes[reviewer_id]) < 3:
            self.reviewer_archetypes[reviewer_id].append(archetype)
        
        # Source stats
        self.source_stats[source]["reviews"] += 1
        
        # Verified purchase tracking
        if verified:
            self.verified_archetypes[archetype] += 1
        else:
            self.unverified_archetypes[archetype] += 1
        
        # Helpful vote tracking
        if helpful_votes > 0:
            self.helpful_archetypes[archetype].append(min(helpful_votes, 100))  # Cap at 100
        
        # Price tiers
        try:
            price_float = float(price) if price else 0
        except (ValueError, TypeError):
            price_float = 0
        
        if price_float > 0:
            if price_float < 25:
                tier = "budget"
            elif price_float < 100:
                tier = "mid_range"
            elif price_float < 500:
                tier = "premium"
            else:
                tier = "luxury"
            self.price_tiers[archetype][tier] += 1
    
    def finalize(self) -> None:
        """Compute cross-category pairs after all reviews processed."""
        
        # Only process reviewers with multiple categories
        multi_cat_reviewers = [
            (rid, cats) for rid, cats in self.reviewer_categories.items()
            if len(cats) > 1
        ]
        
        # Sample if too many (memory management)
        if len(multi_cat_reviewers) > 100000:
            import random
            multi_cat_reviewers = random.sample(multi_cat_reviewers, 100000)
        
        for reviewer_id, categories in multi_cat_reviewers:
            cats = list(categories)
            for i in range(len(cats)):
                for j in range(i + 1, len(cats)):
                    pair = tuple(sorted([cats[i], cats[j]]))
                    self.category_pairs[pair] += 1
        
        # Count unique reviewers per source
        for source in self.source_stats:
            self.source_stats[source]["unique_reviewers"] = len([
                r for r, cats in self.reviewer_categories.items()
                if any(source.lower() in cat.lower() for cat in cats)
            ]) or self.source_stats[source]["reviews"] // 5


# =============================================================================
# AMAZON REVIEW PARSER
# =============================================================================

def parse_amazon_reviews(
    filepath: Path,
    sample_rate: float = 1.0,
    max_reviews: Optional[int] = None,
) -> Generator[Dict, None, None]:
    """
    Parse Amazon review JSONL file (streaming).
    
    Handles both regular and gzip compressed files.
    """
    category = filepath.stem.replace("_", " ").replace("-", " ").title()
    
    # Check if gzipped
    open_func = gzip.open if filepath.suffix == '.gz' else open
    
    count = 0
    try:
        with open_func(filepath, 'rt', encoding='utf-8', errors='ignore') as f:
            for line in f:
                if max_reviews and count >= max_reviews:
                    break
                
                if sample_rate < 1.0 and np.random.random() > sample_rate:
                    continue
                
                try:
                    row = json.loads(line)
                    
                    text = row.get('text', '') or row.get('reviewText', '') or ''
                    if len(text) < 20:
                        continue
                    
                    # Extract fields
                    rating = float(row.get('rating', row.get('overall', 3)) or 3)
                    reviewer_id = row.get('user_id', row.get('reviewerID', ''))
                    product_id = row.get('parent_asin', row.get('asin', ''))
                    verified = row.get('verified_purchase', row.get('verified', False))
                    helpful_votes = row.get('helpful_vote', 0)
                    
                    # Try to extract brand from title or metadata
                    title = row.get('title', '') or row.get('summary', '')
                    
                    yield {
                        "source": "amazon",
                        "category": category,
                        "reviewer_id": f"amz_{reviewer_id}" if reviewer_id else f"amz_{count}",
                        "product_id": product_id,
                        "brand": None,  # Will be extracted from metadata if available
                        "text": text,
                        "title": title,
                        "rating": rating,
                        "verified": verified,
                        "helpful_votes": helpful_votes,
                        "timestamp": row.get('timestamp', row.get('unixReviewTime')),
                    }
                    
                    count += 1
                    
                except json.JSONDecodeError:
                    continue
                    
    except Exception as e:
        logger.warning(f"Error parsing {filepath.name}: {e}")
    
    logger.info(f"  Parsed {count} reviews from {filepath.name}")


def parse_amazon_metadata(filepath: Path) -> Dict[str, Dict]:
    """
    Parse Amazon metadata file to get brand/price info.
    
    Returns dict mapping product_id → {brand, price, ...}
    """
    metadata = {}
    
    if not filepath.exists():
        return metadata
    
    open_func = gzip.open if filepath.suffix == '.gz' else open
    
    try:
        with open_func(filepath, 'rt', encoding='utf-8', errors='ignore') as f:
            for line in f:
                try:
                    row = json.loads(line)
                    product_id = row.get('parent_asin', row.get('asin', ''))
                    if product_id:
                        metadata[product_id] = {
                            "brand": row.get('brand', row.get('manufacturer', '')),
                            "price": row.get('price'),
                            "title": row.get('title', ''),
                            "categories": row.get('categories', []),
                        }
                except json.JSONDecodeError:
                    continue
    except Exception as e:
        logger.warning(f"Error parsing metadata {filepath.name}: {e}")
    
    return metadata


# =============================================================================
# MAIN PROCESSING PIPELINE
# =============================================================================

async def process_amazon_corpus(
    test_mode: bool = False,
    resume: bool = False,
    categories: Optional[List[str]] = None,
    max_per_category: Optional[int] = None,
) -> AmazonColdStartAggregator:
    """Process Amazon review corpus and collect aggregates."""
    
    # Load or create checkpoint
    if resume:
        checkpoint = AmazonLearningCheckpoint.load()
        logger.info(f"Resuming from checkpoint: {checkpoint.total_reviews_processed} reviews processed")
    else:
        checkpoint = AmazonLearningCheckpoint(started_at=datetime.now().isoformat())
    
    aggregator = AmazonColdStartAggregator()
    classifier = LightweightArchetypeClassifier()
    
    # Sample rates
    if test_mode:
        sample_rate = 0.001  # 0.1% for test
        max_per_category = max_per_category or 10000
    else:
        sample_rate = 0.01  # 1% sampling (317GB → ~3GB worth of processing)
        max_per_category = max_per_category or 500000
    
    # Find all JSONL files (reviews, not metadata)
    review_files = sorted([
        f for f in AMAZON_DATA_DIR.glob("*.jsonl")
        if not f.name.startswith("meta_")
    ], key=lambda x: x.stat().st_size, reverse=True)  # Largest first
    
    # Filter by categories if specified
    if categories:
        categories_lower = [c.lower().replace(" ", "_") for c in categories]
        review_files = [
            f for f in review_files
            if any(c in f.name.lower() for c in categories_lower)
        ]
    
    # Skip completed categories if resuming
    if resume and checkpoint.completed_categories:
        review_files = [
            f for f in review_files
            if f.stem not in checkpoint.completed_categories
        ]
    
    logger.info(f"Processing {len(review_files)} category files")
    logger.info(f"Sample rate: {sample_rate:.1%}, Max per category: {max_per_category}")
    
    total_processed = 0
    
    for file_idx, review_file in enumerate(review_files):
        category_name = review_file.stem
        checkpoint.current_category = category_name
        
        logger.info(f"\n[{file_idx+1}/{len(review_files)}] Processing {category_name}...")
        
        # Try to load metadata for this category
        metadata_file = AMAZON_DATA_DIR / f"meta_{category_name}.jsonl"
        metadata = {}
        if metadata_file.exists():
            logger.info(f"  Loading metadata from {metadata_file.name}...")
            metadata = parse_amazon_metadata(metadata_file)
            logger.info(f"  Loaded metadata for {len(metadata)} products")
        
        # Process reviews
        category_count = 0
        for review in parse_amazon_reviews(review_file, sample_rate, max_per_category):
            # Enrich with metadata
            brand = review.get("brand")
            price = None
            if review["product_id"] and review["product_id"] in metadata:
                meta = metadata[review["product_id"]]
                brand = brand or meta.get("brand")
                price = meta.get("price")
            
            # Classify archetype
            archetype, confidence = classifier.classify(
                review["text"],
                review["rating"],
                review["category"],
                len(review["text"]),
                review.get("helpful_votes", 0),
                review.get("verified", False),
            )
            
            # Add to aggregator
            aggregator.add_review(
                source="amazon",
                reviewer_id=review["reviewer_id"],
                category=AMAZON_CATEGORY_MAP.get(category_name, category_name),
                brand=brand,
                product_id=review["product_id"],
                archetype=archetype,
                rating=review["rating"],
                verified=review.get("verified", False),
                helpful_votes=review.get("helpful_votes", 0),
                price=price,
            )
            
            category_count += 1
            total_processed += 1
            
            # Progress logging
            if category_count % 50000 == 0:
                logger.info(f"    Progress: {category_count} reviews...")
                checkpoint.total_reviews_processed = total_processed
                checkpoint.save()
        
        # Update checkpoint
        checkpoint.completed_categories.append(category_name)
        checkpoint.category_review_counts[category_name] = category_count
        checkpoint.total_reviews_processed = total_processed
        checkpoint.save()
        
        logger.info(f"  Completed {category_name}: {category_count} reviews")
        
        # Clear metadata to free memory
        metadata.clear()
    
    # Finalize
    logger.info("\nFinalizing cross-category analysis...")
    aggregator.finalize()
    
    # Update checkpoint with unique counts
    checkpoint.total_unique_reviewers = len(aggregator.reviewer_categories)
    checkpoint.total_unique_brands = len(aggregator.brand_archetypes)
    checkpoint.total_unique_products = len(aggregator.product_archetypes)
    
    # Archetype distribution
    global_archetypes = defaultdict(int)
    for category, archetypes in aggregator.category_archetypes.items():
        for arch, count in archetypes.items():
            global_archetypes[arch] += count
    checkpoint.archetype_counts = dict(global_archetypes)
    checkpoint.save()
    
    logger.info(f"\nTotal reviews processed: {total_processed}")
    logger.info(f"Unique reviewers: {len(aggregator.reviewer_categories)}")
    logger.info(f"Unique brands: {len(aggregator.brand_archetypes)}")
    
    return aggregator


# =============================================================================
# GENERATE COLD-START PRIORS
# =============================================================================

def generate_amazon_priors(aggregator: AmazonColdStartAggregator) -> Dict[str, Any]:
    """Generate cold-start priors from Amazon aggregates."""
    
    priors = {}
    
    # =========================================================================
    # 1. Category → Archetype Priors
    # =========================================================================
    category_priors = {}
    for category, archetypes in aggregator.category_archetypes.items():
        total = sum(archetypes.values())
        if total > 0:
            category_priors[category] = {
                arch: round(count / total, 4)
                for arch, count in archetypes.items()
            }
    priors["category_archetype_priors"] = category_priors
    
    # =========================================================================
    # 2. Brand → Archetype Priors (Top 500 brands)
    # =========================================================================
    brand_priors = {}
    sorted_brands = sorted(
        aggregator.brand_archetypes.items(),
        key=lambda x: sum(x[1].values()),
        reverse=True
    )[:500]
    
    for brand, archetypes in sorted_brands:
        total = sum(archetypes.values())
        if total >= 20:  # Minimum threshold
            brand_priors[brand] = {
                arch: round(count / total, 4)
                for arch, count in archetypes.items()
            }
    priors["brand_archetype_priors"] = brand_priors
    
    # =========================================================================
    # 3. Cross-Category Transfer Lift
    # =========================================================================
    category_counts = {cat: sum(archs.values()) for cat, archs in aggregator.category_archetypes.items()}
    total_reviewers = len(aggregator.reviewer_categories)
    
    cross_category = {}
    for (cat1, cat2), cooccur in aggregator.category_pairs.items():
        if cooccur < 50:
            continue
        
        expected = (category_counts.get(cat1, 1) / max(total_reviewers, 1)) * \
                   (category_counts.get(cat2, 1) / max(total_reviewers, 1)) * total_reviewers
        
        if expected > 0:
            lift = cooccur / expected
            if cat1 not in cross_category:
                cross_category[cat1] = {}
            cross_category[cat1][cat2] = round(lift, 4)
    
    priors["cross_category_lift"] = cross_category
    
    # =========================================================================
    # 4. Reviewer Lifecycle Patterns
    # =========================================================================
    lifecycle = {
        "new_reviewer": {"count": 0, "archetypes": defaultdict(int)},
        "casual": {"count": 0, "archetypes": defaultdict(int)},
        "engaged": {"count": 0, "archetypes": defaultdict(int)},
        "power_user": {"count": 0, "archetypes": defaultdict(int)},
    }
    
    for reviewer_id, count in aggregator.reviewer_counts.items():
        archetypes = aggregator.reviewer_archetypes.get(reviewer_id, [])
        if not archetypes:
            continue
        
        arch_counts = defaultdict(int)
        for arch in archetypes:
            arch_counts[arch] += 1
        dominant_arch = max(arch_counts, key=arch_counts.get)
        
        if count <= 2:
            segment = "new_reviewer"
        elif count <= 10:
            segment = "casual"
        elif count <= 50:
            segment = "engaged"
        else:
            segment = "power_user"
        
        lifecycle[segment]["count"] += 1
        lifecycle[segment]["archetypes"][dominant_arch] += 1
    
    lifecycle_priors = {}
    for segment, data in lifecycle.items():
        total = sum(data["archetypes"].values())
        if total > 0:
            lifecycle_priors[segment] = {
                "count": data["count"],
                "archetype_distribution": {
                    arch: round(count / total, 4)
                    for arch, count in data["archetypes"].items()
                }
            }
    priors["reviewer_lifecycle"] = lifecycle_priors
    
    # =========================================================================
    # 5. Brand Loyalty Segments
    # =========================================================================
    loyalty = {
        "brand_loyalist": {"count": 0, "archetypes": defaultdict(int)},
        "selective": {"count": 0, "archetypes": defaultdict(int)},
        "explorer": {"count": 0, "archetypes": defaultdict(int)},
    }
    
    for reviewer_id, brands in aggregator.reviewer_brands.items():
        archetypes = aggregator.reviewer_archetypes.get(reviewer_id, [])
        if not archetypes:
            continue
        
        arch_counts = defaultdict(int)
        for arch in archetypes:
            arch_counts[arch] += 1
        dominant_arch = max(arch_counts, key=arch_counts.get)
        
        num_brands = len(brands)
        if num_brands == 1:
            segment = "brand_loyalist"
        elif num_brands <= 3:
            segment = "selective"
        else:
            segment = "explorer"
        
        loyalty[segment]["count"] += 1
        loyalty[segment]["archetypes"][dominant_arch] += 1
    
    loyalty_priors = {}
    for segment, data in loyalty.items():
        total = sum(data["archetypes"].values())
        if total > 0:
            loyalty_priors[segment] = {
                "count": data["count"],
                "archetype_distribution": {
                    arch: round(count / total, 4)
                    for arch, count in data["archetypes"].items()
                }
            }
    priors["brand_loyalty_segments"] = loyalty_priors
    
    # =========================================================================
    # 6. Price Tier Preferences
    # =========================================================================
    price_priors = {}
    for archetype, tiers in aggregator.price_tiers.items():
        total = sum(tiers.values())
        if total > 0:
            price_priors[archetype] = {
                tier: round(count / total, 4)
                for tier, count in tiers.items()
            }
    priors["price_tier_preferences"] = price_priors
    
    # =========================================================================
    # 7. Verified Purchase Patterns
    # =========================================================================
    verified_total = sum(aggregator.verified_archetypes.values())
    unverified_total = sum(aggregator.unverified_archetypes.values())
    
    priors["verified_purchase_patterns"] = {
        "verified": {
            arch: round(count / max(verified_total, 1), 4)
            for arch, count in aggregator.verified_archetypes.items()
        },
        "unverified": {
            arch: round(count / max(unverified_total, 1), 4)
            for arch, count in aggregator.unverified_archetypes.items()
        },
    }
    
    # =========================================================================
    # 8. Helpful Vote Patterns
    # =========================================================================
    helpful_patterns = {}
    for archetype, votes in aggregator.helpful_archetypes.items():
        if votes:
            helpful_patterns[archetype] = {
                "avg_helpful_votes": round(np.mean(votes), 2),
                "max_helpful_votes": max(votes),
                "reviews_with_votes": len(votes),
            }
    priors["helpful_vote_patterns"] = helpful_patterns
    
    # =========================================================================
    # 9. Source Statistics
    # =========================================================================
    priors["source_statistics"] = dict(aggregator.source_stats)
    
    # =========================================================================
    # 10. Global Archetype Distribution
    # =========================================================================
    global_archetypes = defaultdict(int)
    for category, archetypes in aggregator.category_archetypes.items():
        for arch, count in archetypes.items():
            global_archetypes[arch] += count
    
    total = sum(global_archetypes.values())
    if total > 0:
        priors["global_archetype_distribution"] = {
            arch: round(count / total, 4)
            for arch, count in global_archetypes.items()
        }
    
    return priors


# =============================================================================
# MERGE WITH EXISTING PRIORS
# =============================================================================

def merge_with_existing_priors(amazon_priors: Dict, existing_path: Path) -> Dict:
    """
    Merge Amazon priors with existing cold-start priors.
    
    Uses weighted combination based on review counts.
    """
    if not existing_path.exists():
        return amazon_priors
    
    with open(existing_path) as f:
        existing = json.load(f)
    
    merged = {}
    
    # Merge category priors (combine and re-weight)
    merged_categories = {}
    existing_cats = existing.get("category_archetype_priors", {})
    amazon_cats = amazon_priors.get("category_archetype_priors", {})
    
    all_categories = set(existing_cats.keys()) | set(amazon_cats.keys())
    for cat in all_categories:
        if cat in existing_cats and cat in amazon_cats:
            # Merge by averaging
            merged_categories[cat] = {}
            all_archs = set(existing_cats[cat].keys()) | set(amazon_cats[cat].keys())
            for arch in all_archs:
                e_val = existing_cats[cat].get(arch, 0)
                a_val = amazon_cats[cat].get(arch, 0)
                merged_categories[cat][arch] = round((e_val + a_val) / 2, 4)
        elif cat in existing_cats:
            merged_categories[cat] = existing_cats[cat]
        else:
            merged_categories[cat] = amazon_cats[cat]
    
    merged["category_archetype_priors"] = merged_categories
    
    # Merge brand priors (combine, prefer Amazon for conflicts as it has more brands)
    merged_brands = {}
    existing_brands = existing.get("brand_archetype_priors", {})
    amazon_brands = amazon_priors.get("brand_archetype_priors", {})
    
    merged_brands.update(existing_brands)
    merged_brands.update(amazon_brands)  # Amazon overwrites if conflict
    merged["brand_archetype_priors"] = merged_brands
    
    # Merge cross-category lift (union)
    merged_lift = {}
    existing_lift = existing.get("cross_category_lift", {})
    amazon_lift = amazon_priors.get("cross_category_lift", {})
    
    for cat, targets in existing_lift.items():
        merged_lift[cat] = targets.copy()
    for cat, targets in amazon_lift.items():
        if cat not in merged_lift:
            merged_lift[cat] = {}
        merged_lift[cat].update(targets)
    merged["cross_category_lift"] = merged_lift
    
    # Merge lifecycle (combine counts and recompute)
    merged["reviewer_lifecycle"] = amazon_priors.get("reviewer_lifecycle", existing.get("reviewer_lifecycle", {}))
    
    # Merge loyalty segments
    merged["brand_loyalty_segments"] = amazon_priors.get("brand_loyalty_segments", existing.get("brand_loyalty_segments", {}))
    
    # Keep temporal patterns from existing (Amazon doesn't have timestamp data typically)
    merged["temporal_patterns"] = existing.get("temporal_patterns", {})
    
    # Merge price preferences
    merged["price_tier_preferences"] = amazon_priors.get("price_tier_preferences", existing.get("price_tier_preferences", {}))
    
    # Amazon-specific additions
    merged["verified_purchase_patterns"] = amazon_priors.get("verified_purchase_patterns", {})
    merged["helpful_vote_patterns"] = amazon_priors.get("helpful_vote_patterns", {})
    
    # Merge source statistics
    merged_stats = {}
    existing_stats = existing.get("source_statistics", {})
    amazon_stats = amazon_priors.get("source_statistics", {})
    merged_stats.update(existing_stats)
    merged_stats.update(amazon_stats)
    merged["source_statistics"] = merged_stats
    
    # Merge global distribution (weighted average)
    existing_global = existing.get("global_archetype_distribution", {})
    amazon_global = amazon_priors.get("global_archetype_distribution", {})
    
    existing_total = sum(
        s.get("reviews", 0) for s in existing.get("source_statistics", {}).values()
    )
    amazon_total = sum(
        s.get("reviews", 0) for s in amazon_priors.get("source_statistics", {}).values()
    )
    
    total_weight = existing_total + amazon_total
    if total_weight > 0:
        merged_global = {}
        all_archs = set(existing_global.keys()) | set(amazon_global.keys())
        for arch in all_archs:
            e_val = existing_global.get(arch, 0) * existing_total
            a_val = amazon_global.get(arch, 0) * amazon_total
            merged_global[arch] = round((e_val + a_val) / total_weight, 4)
        merged["global_archetype_distribution"] = merged_global
    
    return merged


# =============================================================================
# MAIN
# =============================================================================

async def main():
    parser = argparse.ArgumentParser(description="Amazon Corpus Learning Pipeline")
    parser.add_argument("--test", action="store_true", help="Test mode (sample only)")
    parser.add_argument("--resume", action="store_true", help="Resume from checkpoint")
    parser.add_argument("--categories", nargs="+", help="Specific categories to process")
    parser.add_argument("--max-per-category", type=int, help="Max reviews per category")
    args = parser.parse_args()
    
    start_time = datetime.now()
    
    print("\n" + "=" * 70)
    print("ADAM AMAZON CORPUS LEARNING PIPELINE")
    print("=" * 70)
    print(f"\nStarted at: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Mode: {'TEST (sampled)' if args.test else 'FULL PROCESSING'}")
    if args.categories:
        print(f"Categories: {', '.join(args.categories)}")
    print()
    
    # =========================================================================
    # PROCESS AMAZON REVIEWS
    # =========================================================================
    
    logger.info("Starting Amazon review processing...")
    aggregator = await process_amazon_corpus(
        test_mode=args.test,
        resume=args.resume,
        categories=args.categories,
        max_per_category=args.max_per_category,
    )
    
    # =========================================================================
    # GENERATE AMAZON PRIORS
    # =========================================================================
    
    logger.info("\nGenerating Amazon cold-start priors...")
    amazon_priors = generate_amazon_priors(aggregator)
    
    # Save Amazon-specific priors
    with open(AMAZON_PRIORS_PATH, 'w') as f:
        json.dump(amazon_priors, f, indent=2, default=str)
    
    amazon_size = AMAZON_PRIORS_PATH.stat().st_size
    logger.info(f"✓ Amazon priors saved: {AMAZON_PRIORS_PATH}")
    logger.info(f"  Size: {amazon_size / 1024:.1f} KB")
    
    # =========================================================================
    # MERGE WITH EXISTING PRIORS
    # =========================================================================
    
    logger.info("\nMerging with existing cold-start priors...")
    merged_priors = merge_with_existing_priors(amazon_priors, MERGED_PRIORS_PATH)
    
    # Save merged priors
    with open(MERGED_PRIORS_PATH, 'w') as f:
        json.dump(merged_priors, f, indent=2, default=str)
    
    merged_size = MERGED_PRIORS_PATH.stat().st_size
    logger.info(f"✓ Merged priors saved: {MERGED_PRIORS_PATH}")
    logger.info(f"  Size: {merged_size / 1024:.1f} KB")
    
    # =========================================================================
    # SUMMARY
    # =========================================================================
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    print("\n" + "=" * 70)
    print("AMAZON LEARNING COMPLETE")
    print("=" * 70)
    
    print(f"\nProcessing time: {duration:.1f} seconds ({duration/60:.1f} minutes)")
    
    print(f"\nCategories learned: {len(amazon_priors.get('category_archetype_priors', {}))}")
    print(f"Brands learned: {len(amazon_priors.get('brand_archetype_priors', {}))}")
    print(f"Cross-category pairs: {sum(len(v) for v in amazon_priors.get('cross_category_lift', {}).values())}")
    
    print("\nGlobal Archetype Distribution:")
    for arch, pct in amazon_priors.get("global_archetype_distribution", {}).items():
        print(f"  • {arch}: {pct:.1%}")
    
    print(f"\nAmazon priors file: {AMAZON_PRIORS_PATH}")
    print(f"Merged priors file: {MERGED_PRIORS_PATH}")
    
    print("\n✓ Pipeline complete!")
    print("\nNext steps:")
    print("  1. Run learning strengthening: python scripts/run_learning_strengthening.py")
    print("  2. Verify integration: python -c \"from adam.core.learning.learned_priors_integration import get_priors_summary; print(get_priors_summary())\"")


if __name__ == "__main__":
    asyncio.run(main())
