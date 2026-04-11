#!/usr/bin/env python3
# =============================================================================
# ADAM Platform - Complete Cold-Start Learning Pipeline
# Location: scripts/run_complete_coldstart_learning.py
# =============================================================================

"""
COMPLETE COLD-START LEARNING PIPELINE

Processes ALL review sources (~24GB) to extract cold-start learning:

DATA SOURCES:
- BH Photo Product Reviews (71MB) - Electronics/Photography
- Edmonds Car Reviews (138MB) - 50+ automotive brands
- Sephora Product Reviews (512MB) - Beauty products
- Steam Game Reviews (7.6GB) - Gaming
- Movies & Shows (9.5GB) - Netflix, Rotten Tomatoes, MovieLens
- Music & Podcasts (5.1GB) - Podcast reviews

5 ANALYSIS TYPES (NOT full psycholinguistics):
1. Archetype Classification - Assign archetypes from behavioral signals
2. Category→Archetype Priors - What archetypes buy what categories
3. Cross-Category Behavior - Who buys what together
4. Reviewer Lifecycle Patterns - New vs experienced reviewers
5. Brand Loyalty Patterns - Single vs multi-brand behavior

OUTPUT:
- Compact cold-start priors (~100KB JSON files)
- Runtime-ready artifacts for ADAM system
- Storage report showing what can be deleted (~24GB)

Usage:
    # Full processing (takes ~30-60 minutes)
    python scripts/run_complete_coldstart_learning.py
    
    # Process and auto-delete raw files after confirmation
    python scripts/run_complete_coldstart_learning.py --cleanup
    
    # Quick test mode (sample only)
    python scripts/run_complete_coldstart_learning.py --test
"""

import argparse
import asyncio
import csv
import json
import logging
import os
import sqlite3
import sys
from collections import defaultdict
from dataclasses import dataclass, field
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
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)

# Increase CSV field size limit for large Steam reviews
csv.field_size_limit(sys.maxsize)


# =============================================================================
# PATHS
# =============================================================================

REVIEW_TODO_DIR = project_root / "review_todo"
LEARNING_DATA_DIR = project_root / "data" / "learning"
LEARNING_DATA_DIR.mkdir(parents=True, exist_ok=True)


# =============================================================================
# ARCHETYPE CLASSIFIER (Lightweight - No Psycholinguistics)
# =============================================================================

class LightweightArchetypeClassifier:
    """
    Classifies reviews into archetypes using behavioral signals only.
    
    No full psycholinguistic analysis - uses:
    - Rating patterns
    - Review length
    - Sentiment keywords
    - Category context
    """
    
    # Keyword-based sentiment indicators
    PROMOTION_WORDS = {"love", "amazing", "best", "excellent", "perfect", "great", "awesome", "fantastic", "incredible"}
    PREVENTION_WORDS = {"safe", "reliable", "trust", "quality", "durable", "secure", "warranty", "solid", "dependable"}
    ANALYTICAL_WORDS = {"however", "although", "compared", "versus", "ratio", "performance", "specs", "features"}
    SOCIAL_WORDS = {"recommend", "everyone", "friends", "family", "gift", "share", "community", "others"}
    
    # Category → Default archetype weighting
    CATEGORY_ARCHETYPE_BIAS = {
        "gaming": {"Explorer": 0.35, "Achiever": 0.30, "Connector": 0.25, "Guardian": 0.10},
        "electronics": {"Achiever": 0.30, "Analyzer": 0.25, "Guardian": 0.25, "Connector": 0.20},
        "automotive": {"Guardian": 0.30, "Achiever": 0.25, "Connector": 0.25, "Explorer": 0.20},
        "beauty": {"Connector": 0.40, "Achiever": 0.30, "Explorer": 0.20, "Guardian": 0.10},
        "movies": {"Connector": 0.35, "Explorer": 0.30, "Achiever": 0.20, "Analyzer": 0.15},
        "music": {"Connector": 0.40, "Explorer": 0.35, "Achiever": 0.15, "Analyzer": 0.10},
        "podcasts": {"Analyzer": 0.35, "Connector": 0.30, "Achiever": 0.20, "Explorer": 0.15},
    }
    
    def classify(
        self,
        text: str,
        rating: float,
        category: str,
        review_length: Optional[int] = None,
    ) -> Tuple[str, float]:
        """
        Classify a review into an archetype.
        
        Returns: (archetype, confidence)
        """
        text_lower = text.lower() if text else ""
        words = set(re.findall(r'\b\w+\b', text_lower))
        
        # Start with category bias
        category_key = category.lower().split("_")[0] if category else "general"
        base_weights = self.CATEGORY_ARCHETYPE_BIAS.get(
            category_key, 
            {"Connector": 0.30, "Achiever": 0.25, "Explorer": 0.20, "Guardian": 0.15, "Pragmatist": 0.05, "Analyzer": 0.05}
        ).copy()
        
        # Adjust by keyword presence
        promotion_score = len(words & self.PROMOTION_WORDS) / max(len(self.PROMOTION_WORDS), 1)
        prevention_score = len(words & self.PREVENTION_WORDS) / max(len(self.PREVENTION_WORDS), 1)
        analytical_score = len(words & self.ANALYTICAL_WORDS) / max(len(self.ANALYTICAL_WORDS), 1)
        social_score = len(words & self.SOCIAL_WORDS) / max(len(self.SOCIAL_WORDS), 1)
        
        # Apply adjustments
        if promotion_score > 0.1:
            base_weights["Achiever"] = base_weights.get("Achiever", 0.2) + 0.1
            base_weights["Explorer"] = base_weights.get("Explorer", 0.2) + 0.05
        
        if prevention_score > 0.1:
            base_weights["Guardian"] = base_weights.get("Guardian", 0.15) + 0.15
            base_weights["Pragmatist"] = base_weights.get("Pragmatist", 0.05) + 0.05
        
        if analytical_score > 0.1:
            base_weights["Analyzer"] = base_weights.get("Analyzer", 0.05) + 0.15
            base_weights["Pragmatist"] = base_weights.get("Pragmatist", 0.05) + 0.05
        
        if social_score > 0.1:
            base_weights["Connector"] = base_weights.get("Connector", 0.3) + 0.15
        
        # Adjust by rating extremity
        if rating is not None:
            if rating >= 4.5:
                base_weights["Connector"] = base_weights.get("Connector", 0.3) + 0.05
            elif rating <= 2:
                base_weights["Analyzer"] = base_weights.get("Analyzer", 0.05) + 0.1
        
        # Adjust by review length
        if review_length is not None:
            if review_length > 500:
                base_weights["Analyzer"] = base_weights.get("Analyzer", 0.05) + 0.1
            elif review_length < 50:
                base_weights["Pragmatist"] = base_weights.get("Pragmatist", 0.05) + 0.05
        
        # Normalize and select
        total = sum(base_weights.values())
        normalized = {k: v / total for k, v in base_weights.items()}
        
        archetype = max(normalized, key=normalized.get)
        confidence = normalized[archetype]
        
        return archetype, confidence


# =============================================================================
# AGGREGATE COLLECTORS
# =============================================================================

@dataclass
class ColdStartAggregator:
    """Collects aggregate statistics for cold-start learning."""
    
    # Category → Archetype counts
    category_archetypes: Dict[str, Dict[str, int]] = field(default_factory=lambda: defaultdict(lambda: defaultdict(int)))
    
    # Brand → Archetype counts
    brand_archetypes: Dict[str, Dict[str, int]] = field(default_factory=lambda: defaultdict(lambda: defaultdict(int)))
    
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
    
    # Temporal patterns
    hourly_engagement: Dict[str, Dict[int, List[float]]] = field(default_factory=lambda: defaultdict(lambda: defaultdict(list)))
    
    # Price tier patterns
    price_tiers: Dict[str, Dict[str, int]] = field(default_factory=lambda: defaultdict(lambda: defaultdict(int)))
    
    def add_review(
        self,
        source: str,
        reviewer_id: str,
        category: str,
        brand: Optional[str],
        archetype: str,
        rating: float,
        timestamp: Optional[datetime] = None,
        price: Optional[float] = None,
    ) -> None:
        """Add a single review to aggregates."""
        
        # Category → Archetype
        self.category_archetypes[category][archetype] += 1
        
        # Brand → Archetype
        if brand:
            self.brand_archetypes[brand][archetype] += 1
        
        # Reviewer tracking
        self.reviewer_categories[reviewer_id].add(category)
        if brand:
            self.reviewer_brands[reviewer_id].add(brand)
        self.reviewer_counts[reviewer_id] += 1
        self.reviewer_ratings[reviewer_id].append(rating)
        self.reviewer_archetypes[reviewer_id].append(archetype)
        
        # Source stats
        self.source_stats[source]["reviews"] += 1
        
        # Temporal patterns
        if timestamp:
            hour = timestamp.hour
            engagement = (rating - 1) / 4.0  # Normalize 1-5 to 0-1
            self.hourly_engagement[archetype][hour].append(engagement)
        
        # Price tiers
        if price and price > 0:
            if price < 25:
                tier = "budget"
            elif price < 100:
                tier = "mid_range"
            elif price < 500:
                tier = "premium"
            else:
                tier = "luxury"
            self.price_tiers[archetype][tier] += 1
    
    def finalize(self) -> None:
        """Compute cross-category pairs after all reviews processed."""
        
        for reviewer_id, categories in self.reviewer_categories.items():
            cats = list(categories)
            for i in range(len(cats)):
                for j in range(i + 1, len(cats)):
                    pair = tuple(sorted([cats[i], cats[j]]))
                    self.category_pairs[pair] += 1
        
        # Count unique reviewers per source
        # (Note: This is approximate since reviewer_id format varies by source)
        for source in self.source_stats:
            self.source_stats[source]["unique_reviewers"] = len([
                r for r in self.reviewer_counts if source.lower() in r.lower()
            ]) or self.source_stats[source]["reviews"] // 5  # Estimate


# =============================================================================
# SOURCE PARSERS
# =============================================================================

def parse_bh_photo(filepath: Path, sample_rate: float = 1.0) -> Generator[Dict, None, None]:
    """Parse BH Photo reviews."""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                if sample_rate < 1.0 and np.random.random() > sample_rate:
                    continue
                text = row.get('text', '') or row.get('review', '') or ''
                if len(text) >= 20:
                    yield {
                        "source": "bh_photo",
                        "reviewer_id": f"bh_{row.get('author', i)}",
                        "category": "Electronics_Photography",
                        "brand": "B&H Photo",
                        "text": text,
                        "rating": float(row.get('serviceRating', row.get('rating', 4)) or 4),
                        "timestamp": None,
                        "price": None,
                    }
    except Exception as e:
        logger.warning(f"Error parsing BH Photo: {e}")


def parse_edmonds(filepath: Path, sample_rate: float = 1.0) -> Generator[Dict, None, None]:
    """Parse Edmonds car reviews."""
    brand = filepath.stem.replace("-", " ").replace("_", " ").title()
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                if sample_rate < 1.0 and np.random.random() > sample_rate:
                    continue
                text = row.get('Review', '') or row.get('review', '') or ''
                if len(text) >= 20:
                    yield {
                        "source": "edmonds",
                        "reviewer_id": f"edmonds_{row.get('Author', i)}",
                        "category": "Automotive",
                        "brand": brand,
                        "text": text,
                        "rating": float(row.get('Rating', 4) or 4),
                        "timestamp": None,
                        "price": None,
                    }
    except Exception as e:
        logger.warning(f"Error parsing Edmonds {filepath.name}: {e}")


def parse_sephora(filepath: Path, sample_rate: float = 1.0) -> Generator[Dict, None, None]:
    """Parse Sephora product reviews."""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                if sample_rate < 1.0 and np.random.random() > sample_rate:
                    continue
                text = row.get('review_text', '') or row.get('text', '') or ''
                if len(text) >= 20:
                    brand = row.get('brand_name', row.get('brand', 'Sephora'))
                    yield {
                        "source": "sephora",
                        "reviewer_id": f"sephora_{row.get('author_id', i)}",
                        "category": "Beauty",
                        "brand": brand,
                        "text": text,
                        "rating": float(row.get('rating', 4) or 4),
                        "timestamp": None,
                        "price": float(row.get('price_usd', 0) or 0) if row.get('price_usd') else None,
                    }
    except Exception as e:
        logger.warning(f"Error parsing Sephora {filepath.name}: {e}")


def parse_steam(filepath: Path, sample_rate: float = 0.1) -> Generator[Dict, None, None]:
    """Parse Steam game reviews (8GB file - sample by default)."""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                if sample_rate < 1.0 and np.random.random() > sample_rate:
                    continue
                text = row.get('review', '') or ''
                if len(text) >= 20:
                    recommended = row.get('recommended', 'True')
                    rating = 5.0 if recommended == 'True' else 2.0
                    
                    timestamp = None
                    ts_str = row.get('timestamp_created')
                    if ts_str:
                        try:
                            timestamp = datetime.fromtimestamp(int(ts_str))
                        except:
                            pass
                    
                    yield {
                        "source": "steam",
                        "reviewer_id": f"steam_{row.get('author.steamid', i)}",
                        "category": "Gaming",
                        "brand": row.get('app_name', 'Steam Game'),
                        "text": text,
                        "rating": rating,
                        "timestamp": timestamp,
                        "price": None,
                    }
    except Exception as e:
        logger.warning(f"Error parsing Steam: {e}")


def parse_netflix(filepath: Path, sample_rate: float = 1.0) -> Generator[Dict, None, None]:
    """Parse Netflix reviews."""
    try:
        for file in filepath.iterdir():
            if file.suffix in ['.csv', '.json']:
                if file.suffix == '.csv':
                    with open(file, 'r', encoding='utf-8', errors='ignore') as f:
                        reader = csv.DictReader(f)
                        for i, row in enumerate(reader):
                            if sample_rate < 1.0 and np.random.random() > sample_rate:
                                continue
                            text = row.get('review', '') or row.get('content', '') or ''
                            if len(text) >= 20:
                                yield {
                                    "source": "netflix",
                                    "reviewer_id": f"netflix_{row.get('user_id', i)}",
                                    "category": "Streaming",
                                    "brand": "Netflix",
                                    "text": text,
                                    "rating": float(row.get('score', row.get('rating', 4)) or 4),
                                    "timestamp": None,
                                    "price": None,
                                }
    except Exception as e:
        logger.warning(f"Error parsing Netflix: {e}")


def parse_rotten_tomatoes(filepath: Path, sample_rate: float = 1.0) -> Generator[Dict, None, None]:
    """Parse Rotten Tomatoes movie reviews."""
    try:
        for file in filepath.iterdir():
            if file.suffix == '.csv':
                with open(file, 'r', encoding='utf-8', errors='ignore') as f:
                    reader = csv.DictReader(f)
                    for i, row in enumerate(reader):
                        if sample_rate < 1.0 and np.random.random() > sample_rate:
                            continue
                        text = row.get('review', '') or row.get('content', '') or ''
                        if len(text) >= 20:
                            yield {
                                "source": "rotten_tomatoes",
                                "reviewer_id": f"rt_{row.get('critic_name', i)}",
                                "category": "Movies",
                                "brand": row.get('movie_title', 'Movie'),
                                "text": text,
                                "rating": 4.5 if row.get('review_type') == 'Fresh' else 2.5,
                                "timestamp": None,
                                "price": None,
                            }
    except Exception as e:
        logger.warning(f"Error parsing Rotten Tomatoes: {e}")


def parse_movielens(filepath: Path, sample_rate: float = 0.1) -> Generator[Dict, None, None]:
    """Parse MovieLens ratings."""
    try:
        ratings_file = filepath / "ratings.csv"
        movies_file = filepath / "movies.csv"
        
        # Load movie titles
        movies = {}
        if movies_file.exists():
            with open(movies_file, 'r', encoding='utf-8', errors='ignore') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    movies[row.get('movieId', '')] = row.get('title', 'Movie')
        
        # Process ratings
        if ratings_file.exists():
            with open(ratings_file, 'r', encoding='utf-8', errors='ignore') as f:
                reader = csv.DictReader(f)
                for i, row in enumerate(reader):
                    if sample_rate < 1.0 and np.random.random() > sample_rate:
                        continue
                    
                    movie_id = row.get('movieId', '')
                    movie_title = movies.get(movie_id, 'Movie')
                    
                    timestamp = None
                    ts_str = row.get('timestamp')
                    if ts_str:
                        try:
                            timestamp = datetime.fromtimestamp(int(ts_str))
                        except:
                            pass
                    
                    yield {
                        "source": "movielens",
                        "reviewer_id": f"ml_{row.get('userId', i)}",
                        "category": "Movies",
                        "brand": movie_title,
                        "text": f"Rating: {row.get('rating', 3)}",  # MovieLens has no text
                        "rating": float(row.get('rating', 3) or 3),
                        "timestamp": timestamp,
                        "price": None,
                    }
    except Exception as e:
        logger.warning(f"Error parsing MovieLens: {e}")


def parse_podcasts(filepath: Path, sample_rate: float = 0.2) -> Generator[Dict, None, None]:
    """Parse podcast reviews (JSON lines)."""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            for i, line in enumerate(f):
                if sample_rate < 1.0 and np.random.random() > sample_rate:
                    continue
                try:
                    row = json.loads(line)
                    text = row.get('content', '') or row.get('title', '') or ''
                    if len(text) >= 20:
                        timestamp = None
                        ts_str = row.get('created_at')
                        if ts_str:
                            try:
                                timestamp = datetime.fromisoformat(ts_str.replace('+00', '+00:00'))
                            except:
                                pass
                        
                        yield {
                            "source": "podcasts",
                            "reviewer_id": f"pod_{row.get('author_id', i)}",
                            "category": "Podcasts",
                            "brand": row.get('podcast_id', 'Podcast')[:20],
                            "text": text,
                            "rating": float(row.get('rating', 3) or 3),
                            "timestamp": timestamp,
                            "price": None,
                        }
                except json.JSONDecodeError:
                    continue
    except Exception as e:
        logger.warning(f"Error parsing Podcasts: {e}")


# =============================================================================
# MAIN PROCESSING PIPELINE
# =============================================================================

async def process_all_reviews(test_mode: bool = False) -> ColdStartAggregator:
    """Process all review sources and collect aggregates."""
    
    aggregator = ColdStartAggregator()
    classifier = LightweightArchetypeClassifier()
    
    # Sample rates (lower for test mode, lower for huge files)
    sample_rate = 0.01 if test_mode else 1.0
    steam_sample_rate = 0.001 if test_mode else 0.05  # Steam is 8GB
    movielens_sample_rate = 0.001 if test_mode else 0.05  # MovieLens is large
    podcast_sample_rate = 0.01 if test_mode else 0.1  # Podcasts are 2.3GB
    
    total_processed = 0
    
    # =========================================================================
    # 1. BH PHOTO
    # =========================================================================
    logger.info("Processing BH Photo reviews...")
    bh_dir = REVIEW_TODO_DIR / "BH Photo Product Reviews"
    if bh_dir.exists():
        for file in bh_dir.glob("*.csv"):
            for review in parse_bh_photo(file, sample_rate):
                archetype, confidence = classifier.classify(
                    review["text"], review["rating"], review["category"], len(review["text"])
                )
                aggregator.add_review(
                    source=review["source"],
                    reviewer_id=review["reviewer_id"],
                    category=review["category"],
                    brand=review["brand"],
                    archetype=archetype,
                    rating=review["rating"],
                    timestamp=review["timestamp"],
                    price=review["price"],
                )
                total_processed += 1
        logger.info(f"  Processed BH Photo: {aggregator.source_stats['bh_photo']['reviews']} reviews")
    
    # =========================================================================
    # 2. EDMONDS CAR REVIEWS
    # =========================================================================
    logger.info("Processing Edmonds Car Reviews...")
    edmonds_dir = REVIEW_TODO_DIR / "Edmonds Car Reviews"
    if edmonds_dir.exists():
        for file in edmonds_dir.glob("*.csv"):
            for review in parse_edmonds(file, sample_rate):
                archetype, confidence = classifier.classify(
                    review["text"], review["rating"], review["category"], len(review["text"])
                )
                aggregator.add_review(
                    source=review["source"],
                    reviewer_id=review["reviewer_id"],
                    category=review["category"],
                    brand=review["brand"],
                    archetype=archetype,
                    rating=review["rating"],
                    timestamp=review["timestamp"],
                    price=review["price"],
                )
                total_processed += 1
        logger.info(f"  Processed Edmonds: {aggregator.source_stats['edmonds']['reviews']} reviews")
    
    # =========================================================================
    # 3. SEPHORA
    # =========================================================================
    logger.info("Processing Sephora reviews...")
    sephora_dir = REVIEW_TODO_DIR / "Sephora Product Reviews"
    if sephora_dir.exists():
        for file in sephora_dir.glob("*.csv"):
            for review in parse_sephora(file, sample_rate):
                archetype, confidence = classifier.classify(
                    review["text"], review["rating"], review["category"], len(review["text"])
                )
                aggregator.add_review(
                    source=review["source"],
                    reviewer_id=review["reviewer_id"],
                    category=review["category"],
                    brand=review["brand"],
                    archetype=archetype,
                    rating=review["rating"],
                    timestamp=review["timestamp"],
                    price=review["price"],
                )
                total_processed += 1
        logger.info(f"  Processed Sephora: {aggregator.source_stats['sephora']['reviews']} reviews")
    
    # =========================================================================
    # 4. STEAM (8GB - sampled)
    # =========================================================================
    logger.info("Processing Steam reviews (sampled)...")
    steam_dir = REVIEW_TODO_DIR / "Steam Game Reviews"
    if steam_dir.exists():
        steam_file = steam_dir / "steam_reviews.csv"
        if steam_file.exists():
            count = 0
            for review in parse_steam(steam_file, steam_sample_rate):
                archetype, confidence = classifier.classify(
                    review["text"], review["rating"], review["category"], len(review["text"])
                )
                aggregator.add_review(
                    source=review["source"],
                    reviewer_id=review["reviewer_id"],
                    category=review["category"],
                    brand=review["brand"],
                    archetype=archetype,
                    rating=review["rating"],
                    timestamp=review["timestamp"],
                    price=review["price"],
                )
                total_processed += 1
                count += 1
                if count % 100000 == 0:
                    logger.info(f"    Steam progress: {count} reviews...")
            logger.info(f"  Processed Steam: {aggregator.source_stats['steam']['reviews']} reviews")
    
    # =========================================================================
    # 5. NETFLIX
    # =========================================================================
    logger.info("Processing Netflix reviews...")
    netflix_dir = REVIEW_TODO_DIR / "Movies & Shows" / "Netflix Reviews"
    if netflix_dir.exists():
        for review in parse_netflix(netflix_dir, sample_rate):
            archetype, confidence = classifier.classify(
                review["text"], review["rating"], review["category"], len(review["text"])
            )
            aggregator.add_review(
                source=review["source"],
                reviewer_id=review["reviewer_id"],
                category=review["category"],
                brand=review["brand"],
                archetype=archetype,
                rating=review["rating"],
                timestamp=review["timestamp"],
                price=review["price"],
            )
            total_processed += 1
        logger.info(f"  Processed Netflix: {aggregator.source_stats['netflix']['reviews']} reviews")
    
    # =========================================================================
    # 6. ROTTEN TOMATOES
    # =========================================================================
    logger.info("Processing Rotten Tomatoes reviews...")
    rt_dir = REVIEW_TODO_DIR / "Movies & Shows" / "Rotten Tomatoes Movie Reviews"
    if rt_dir.exists():
        for review in parse_rotten_tomatoes(rt_dir, sample_rate):
            archetype, confidence = classifier.classify(
                review["text"], review["rating"], review["category"], len(review["text"])
            )
            aggregator.add_review(
                source=review["source"],
                reviewer_id=review["reviewer_id"],
                category=review["category"],
                brand=review["brand"],
                archetype=archetype,
                rating=review["rating"],
                timestamp=review["timestamp"],
                price=review["price"],
            )
            total_processed += 1
        logger.info(f"  Processed Rotten Tomatoes: {aggregator.source_stats['rotten_tomatoes']['reviews']} reviews")
    
    # =========================================================================
    # 7. MOVIELENS
    # =========================================================================
    logger.info("Processing MovieLens ratings...")
    ml_dir = REVIEW_TODO_DIR / "Movies & Shows" / "Movie - Lens - 25M - 1995 to 2020"
    if ml_dir.exists():
        count = 0
        for review in parse_movielens(ml_dir, movielens_sample_rate):
            archetype, confidence = classifier.classify(
                review["text"], review["rating"], review["category"], len(review["text"])
            )
            aggregator.add_review(
                source=review["source"],
                reviewer_id=review["reviewer_id"],
                category=review["category"],
                brand=review["brand"],
                archetype=archetype,
                rating=review["rating"],
                timestamp=review["timestamp"],
                price=review["price"],
            )
            total_processed += 1
            count += 1
            if count % 500000 == 0:
                logger.info(f"    MovieLens progress: {count} ratings...")
        logger.info(f"  Processed MovieLens: {aggregator.source_stats['movielens']['reviews']} reviews")
    
    # =========================================================================
    # 8. PODCASTS
    # =========================================================================
    logger.info("Processing Podcast reviews...")
    podcast_file = REVIEW_TODO_DIR / "Music & Podcasts Reviews" / "reviews.json"
    if podcast_file.exists():
        count = 0
        for review in parse_podcasts(podcast_file, podcast_sample_rate):
            archetype, confidence = classifier.classify(
                review["text"], review["rating"], review["category"], len(review["text"])
            )
            aggregator.add_review(
                source=review["source"],
                reviewer_id=review["reviewer_id"],
                category=review["category"],
                brand=review["brand"],
                archetype=archetype,
                rating=review["rating"],
                timestamp=review["timestamp"],
                price=review["price"],
            )
            total_processed += 1
            count += 1
            if count % 100000 == 0:
                logger.info(f"    Podcasts progress: {count} reviews...")
        logger.info(f"  Processed Podcasts: {aggregator.source_stats['podcasts']['reviews']} reviews")
    
    # Finalize cross-category pairs
    logger.info("Finalizing cross-category analysis...")
    aggregator.finalize()
    
    logger.info(f"\nTotal reviews processed: {total_processed}")
    
    return aggregator


# =============================================================================
# GENERATE COMPACT PRIORS
# =============================================================================

def generate_cold_start_priors(aggregator: ColdStartAggregator) -> Dict[str, Any]:
    """Generate compact cold-start priors from aggregates."""
    
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
    # 2. Brand → Archetype Priors (Top 100 brands)
    # =========================================================================
    brand_priors = {}
    sorted_brands = sorted(
        aggregator.brand_archetypes.items(),
        key=lambda x: sum(x[1].values()),
        reverse=True
    )[:100]
    
    for brand, archetypes in sorted_brands:
        total = sum(archetypes.values())
        if total >= 10:  # Minimum threshold
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
        if cooccur < 10:
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
        "new_reviewer": {"count": 0, "archetypes": defaultdict(int)},      # 1-2 reviews
        "casual": {"count": 0, "archetypes": defaultdict(int)},             # 3-10 reviews
        "engaged": {"count": 0, "archetypes": defaultdict(int)},            # 11-50 reviews
        "power_user": {"count": 0, "archetypes": defaultdict(int)},         # 51+ reviews
    }
    
    for reviewer_id, count in aggregator.reviewer_counts.items():
        archetypes = aggregator.reviewer_archetypes.get(reviewer_id, [])
        if not archetypes:
            continue
        
        # Get most common archetype for this reviewer
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
    
    # Convert to priors
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
        "brand_loyalist": {"count": 0, "archetypes": defaultdict(int)},    # 1 brand
        "selective": {"count": 0, "archetypes": defaultdict(int)},          # 2-3 brands
        "explorer": {"count": 0, "archetypes": defaultdict(int)},           # 4+ brands
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
    # 6. Temporal Patterns
    # =========================================================================
    temporal_priors = {}
    for archetype, hourly in aggregator.hourly_engagement.items():
        if not hourly:
            continue
        
        hourly_avg = {}
        for hour, engagements in hourly.items():
            if engagements:
                hourly_avg[hour] = round(np.mean(engagements), 4)
        
        if hourly_avg:
            best_hours = sorted(hourly_avg.items(), key=lambda x: x[1], reverse=True)[:3]
            temporal_priors[archetype] = {
                "best_hours": [h[0] for h in best_hours],
                "hourly_engagement": hourly_avg,
            }
    
    priors["temporal_patterns"] = temporal_priors
    
    # =========================================================================
    # 7. Price Tier Preferences
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
    # 8. Source Statistics
    # =========================================================================
    priors["source_statistics"] = dict(aggregator.source_stats)
    
    # =========================================================================
    # 9. Global Archetype Distribution
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
# STORAGE REPORT
# =============================================================================

def generate_storage_report() -> Dict[str, Any]:
    """Generate report of storage that can be freed."""
    
    report = {
        "directories": [],
        "total_size_bytes": 0,
        "total_size_human": "",
    }
    
    dirs_to_check = [
        ("BH Photo Product Reviews", REVIEW_TODO_DIR / "BH Photo Product Reviews"),
        ("Edmonds Car Reviews", REVIEW_TODO_DIR / "Edmonds Car Reviews"),
        ("Sephora Product Reviews", REVIEW_TODO_DIR / "Sephora Product Reviews"),
        ("Steam Game Reviews", REVIEW_TODO_DIR / "Steam Game Reviews"),
        ("Movies & Shows", REVIEW_TODO_DIR / "Movies & Shows"),
        ("Music & Podcasts Reviews", REVIEW_TODO_DIR / "Music & Podcasts Reviews"),
    ]
    
    total_bytes = 0
    
    for name, path in dirs_to_check:
        if path.exists():
            size = 0
            for f in path.rglob("*"):
                if f.is_file():
                    size += f.stat().st_size
            
            size_human = f"{size / (1024**3):.2f} GB" if size > 1024**3 else f"{size / (1024**2):.2f} MB"
            
            report["directories"].append({
                "name": name,
                "path": str(path),
                "size_bytes": size,
                "size_human": size_human,
            })
            total_bytes += size
    
    report["total_size_bytes"] = total_bytes
    report["total_size_human"] = f"{total_bytes / (1024**3):.2f} GB"
    
    return report


def cleanup_raw_files(report: Dict[str, Any], confirm: bool = False) -> None:
    """Delete raw review files after confirmation."""
    
    print("\n" + "=" * 70)
    print("STORAGE CLEANUP")
    print("=" * 70)
    
    print(f"\nThe following directories can be deleted to free {report['total_size_human']}:\n")
    
    for d in report["directories"]:
        print(f"  • {d['name']}: {d['size_human']}")
        print(f"    Path: {d['path']}")
    
    if not confirm:
        print("\n⚠️  Run with --cleanup flag to delete these files.")
        return
    
    print("\n" + "-" * 50)
    response = input("Are you SURE you want to delete these files? (type 'DELETE' to confirm): ")
    
    if response != "DELETE":
        print("Cancelled. No files deleted.")
        return
    
    import shutil
    
    for d in report["directories"]:
        path = Path(d["path"])
        if path.exists():
            print(f"Deleting {d['name']}...")
            shutil.rmtree(path)
            print(f"  ✓ Deleted {d['size_human']}")
    
    print(f"\n✓ Freed {report['total_size_human']} of storage!")


# =============================================================================
# MAIN
# =============================================================================

async def main():
    parser = argparse.ArgumentParser(description="Complete Cold-Start Learning Pipeline")
    parser.add_argument("--test", action="store_true", help="Test mode (sample only)")
    parser.add_argument("--cleanup", action="store_true", help="Delete raw files after learning")
    args = parser.parse_args()
    
    start_time = datetime.now()
    
    print("\n" + "=" * 70)
    print("ADAM COMPLETE COLD-START LEARNING PIPELINE")
    print("=" * 70)
    print(f"\nStarted at: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Mode: {'TEST (sampled)' if args.test else 'FULL PROCESSING'}")
    print()
    
    # =========================================================================
    # PROCESS ALL REVIEWS
    # =========================================================================
    
    logger.info("Starting review processing...")
    aggregator = await process_all_reviews(test_mode=args.test)
    
    # =========================================================================
    # GENERATE COLD-START PRIORS
    # =========================================================================
    
    logger.info("\nGenerating cold-start priors...")
    priors = generate_cold_start_priors(aggregator)
    
    # Save priors
    priors_file = LEARNING_DATA_DIR / "complete_coldstart_priors.json"
    with open(priors_file, 'w') as f:
        json.dump(priors, f, indent=2, default=str)
    
    priors_size = priors_file.stat().st_size
    logger.info(f"✓ Cold-start priors saved: {priors_file}")
    logger.info(f"  Size: {priors_size / 1024:.1f} KB")
    
    # =========================================================================
    # SUMMARY
    # =========================================================================
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    print("\n" + "=" * 70)
    print("LEARNING COMPLETE")
    print("=" * 70)
    
    print(f"\nProcessing time: {duration:.1f} seconds ({duration/60:.1f} minutes)")
    
    print("\nSource Statistics:")
    for source, stats in priors.get("source_statistics", {}).items():
        print(f"  • {source}: {stats.get('reviews', 0):,} reviews")
    
    print(f"\nCategories learned: {len(priors.get('category_archetype_priors', {}))}")
    print(f"Brands learned: {len(priors.get('brand_archetype_priors', {}))}")
    print(f"Cross-category pairs: {sum(len(v) for v in priors.get('cross_category_lift', {}).values())}")
    
    print("\nGlobal Archetype Distribution:")
    for arch, pct in priors.get("global_archetype_distribution", {}).items():
        print(f"  • {arch}: {pct:.1%}")
    
    print(f"\nCold-start priors file: {priors_file}")
    print(f"Priors size: {priors_size / 1024:.1f} KB (compact!)")
    
    # =========================================================================
    # STORAGE REPORT
    # =========================================================================
    
    storage_report = generate_storage_report()
    
    print("\n" + "-" * 50)
    print(f"STORAGE AVAILABLE FOR CLEANUP: {storage_report['total_size_human']}")
    print("-" * 50)
    
    # Save storage report
    report_file = LEARNING_DATA_DIR / "storage_cleanup_report.json"
    with open(report_file, 'w') as f:
        json.dump(storage_report, f, indent=2)
    print(f"\nStorage report saved: {report_file}")
    
    # Cleanup if requested
    cleanup_raw_files(storage_report, confirm=args.cleanup)
    
    print("\n✓ Pipeline complete!")
    print(f"\nNext: Load Google Reviews into freed space at:")
    print(f"  {REVIEW_TODO_DIR}")


if __name__ == "__main__":
    asyncio.run(main())
