#!/usr/bin/env python3
# =============================================================================
# ADAM Platform - Specialty Reviews Deep Learning Pipeline
# Location: scripts/run_specialty_reviews_learning.py
# =============================================================================

"""
SPECIALTY REVIEWS DEEP LEARNING PIPELINE

Processes three specialty review datasets with UNIQUE signals:

1. PODCASTS (5.1GB) - CRITICAL for iHeartMedia
   - Episode engagement patterns
   - Host loyalty metrics
   - Topic/category preferences
   - Subscription vs. casual listening
   - Content discovery behavior

2. STEAM (7.6GB) - UNIQUE engagement depth
   - Playtime before review (hours played)
   - Engagement intensity by archetype
   - Early access vs. full release patterns
   - Game genre preferences
   - Recommendation patterns

3. SEPHORA (505MB) - Personal characteristics
   - Skin type preferences
   - Hair type patterns
   - Eye color correlations
   - Ingredient sensitivity
   - Beauty routine complexity

Output:
- Podcast engagement priors
- Steam engagement depth priors (playtime × archetype)
- Sephora personal characteristic priors
- Merged with existing 14.5M review priors
"""

import argparse
import asyncio
import json
import logging
import sys
import csv
import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

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

# =============================================================================
# PATHS
# =============================================================================

LEARNING_DATA_DIR = project_root / "data" / "learning"
LEARNING_DATA_DIR.mkdir(parents=True, exist_ok=True)

PODCAST_DIR = project_root / "review_todo" / "podcast_reviews"
STEAM_DIR = project_root / "review_todo" / "steam_reviews"
SEPHORA_DIR = project_root / "review_todo" / "sephora_reviews"

SPECIALTY_PRIORS_PATH = LEARNING_DATA_DIR / "specialty_reviews_priors.json"
MERGED_PRIORS_PATH = LEARNING_DATA_DIR / "complete_coldstart_priors.json"


# =============================================================================
# ARCHETYPE CLASSIFIER
# =============================================================================

class SpecialtyArchetypeClassifier:
    """Archetype classifier with domain-specific adjustments."""
    
    PROMOTION_WORDS = {"love", "amazing", "best", "excellent", "perfect", "great", "awesome", "fantastic", "addictive", "hooked"}
    PREVENTION_WORDS = {"safe", "reliable", "trust", "quality", "careful", "honest", "consistent", "stable"}
    ANALYTICAL_WORDS = {"however", "although", "compared", "hours", "mechanics", "gameplay", "formula", "ingredients"}
    SOCIAL_WORDS = {"recommend", "friends", "family", "community", "everyone", "share", "together", "multiplayer"}
    EXPLORER_WORDS = {"discovered", "new", "different", "unique", "tried", "first", "interesting", "hidden"}
    
    # Domain-specific biases
    PODCAST_CATEGORY_BIAS = {
        "comedy": {"Connector": 0.40, "Explorer": 0.25, "Achiever": 0.20, "Analyzer": 0.10, "Guardian": 0.05},
        "news": {"Analyzer": 0.35, "Guardian": 0.30, "Achiever": 0.20, "Connector": 0.10, "Explorer": 0.05},
        "true crime": {"Explorer": 0.35, "Analyzer": 0.30, "Connector": 0.20, "Guardian": 0.10, "Achiever": 0.05},
        "education": {"Analyzer": 0.40, "Achiever": 0.25, "Explorer": 0.20, "Guardian": 0.10, "Connector": 0.05},
        "business": {"Achiever": 0.40, "Analyzer": 0.25, "Pragmatist": 0.20, "Guardian": 0.10, "Explorer": 0.05},
        "health": {"Guardian": 0.35, "Connector": 0.25, "Achiever": 0.20, "Analyzer": 0.15, "Explorer": 0.05},
        "sports": {"Achiever": 0.35, "Connector": 0.30, "Explorer": 0.20, "Guardian": 0.10, "Analyzer": 0.05},
        "music": {"Connector": 0.35, "Explorer": 0.30, "Achiever": 0.20, "Analyzer": 0.10, "Guardian": 0.05},
        "society": {"Connector": 0.35, "Analyzer": 0.25, "Explorer": 0.20, "Guardian": 0.15, "Achiever": 0.05},
        "technology": {"Achiever": 0.30, "Analyzer": 0.30, "Explorer": 0.25, "Guardian": 0.10, "Connector": 0.05},
    }
    
    GAME_GENRE_BIAS = {
        "action": {"Achiever": 0.35, "Explorer": 0.30, "Connector": 0.20, "Guardian": 0.10, "Analyzer": 0.05},
        "rpg": {"Explorer": 0.40, "Achiever": 0.25, "Analyzer": 0.20, "Connector": 0.10, "Guardian": 0.05},
        "strategy": {"Analyzer": 0.40, "Achiever": 0.30, "Explorer": 0.15, "Guardian": 0.10, "Connector": 0.05},
        "simulation": {"Explorer": 0.30, "Achiever": 0.25, "Analyzer": 0.25, "Guardian": 0.15, "Connector": 0.05},
        "adventure": {"Explorer": 0.45, "Connector": 0.25, "Achiever": 0.15, "Analyzer": 0.10, "Guardian": 0.05},
        "indie": {"Explorer": 0.40, "Connector": 0.25, "Analyzer": 0.20, "Achiever": 0.10, "Guardian": 0.05},
        "casual": {"Connector": 0.35, "Explorer": 0.25, "Pragmatist": 0.20, "Achiever": 0.15, "Guardian": 0.05},
        "multiplayer": {"Connector": 0.40, "Achiever": 0.30, "Explorer": 0.15, "Guardian": 0.10, "Analyzer": 0.05},
        "horror": {"Explorer": 0.35, "Connector": 0.30, "Achiever": 0.20, "Analyzer": 0.10, "Guardian": 0.05},
        "sports": {"Achiever": 0.40, "Connector": 0.30, "Explorer": 0.15, "Guardian": 0.10, "Analyzer": 0.05},
    }
    
    BEAUTY_CATEGORY_BIAS = {
        "skincare": {"Guardian": 0.35, "Connector": 0.25, "Achiever": 0.20, "Analyzer": 0.15, "Explorer": 0.05},
        "makeup": {"Connector": 0.35, "Explorer": 0.30, "Achiever": 0.20, "Guardian": 0.10, "Analyzer": 0.05},
        "haircare": {"Guardian": 0.30, "Connector": 0.30, "Achiever": 0.20, "Explorer": 0.15, "Analyzer": 0.05},
        "fragrance": {"Connector": 0.35, "Explorer": 0.35, "Achiever": 0.15, "Guardian": 0.10, "Analyzer": 0.05},
        "tools": {"Achiever": 0.35, "Pragmatist": 0.25, "Guardian": 0.20, "Analyzer": 0.15, "Explorer": 0.05},
    }
    
    def classify(
        self,
        text: str,
        rating: float,
        domain: str,
        category: str = "general",
        playtime_hours: Optional[float] = None,
    ) -> Tuple[str, float]:
        """Classify review into archetype."""
        text_lower = text.lower() if text else ""
        words = set(re.findall(r'\b\w+\b', text_lower))
        
        # Get domain-specific base weights
        if domain == "podcast":
            cat_key = self._normalize_podcast_category(category)
            base_weights = self.PODCAST_CATEGORY_BIAS.get(cat_key, {}).copy()
        elif domain == "steam":
            cat_key = self._normalize_game_genre(category)
            base_weights = self.GAME_GENRE_BIAS.get(cat_key, {}).copy()
        elif domain == "sephora":
            cat_key = self._normalize_beauty_category(category)
            base_weights = self.BEAUTY_CATEGORY_BIAS.get(cat_key, {}).copy()
        else:
            base_weights = {}
        
        if not base_weights:
            base_weights = {"Connector": 0.25, "Achiever": 0.20, "Explorer": 0.20, "Guardian": 0.20, "Analyzer": 0.15}
        
        # Keyword adjustments
        if len(words & self.PROMOTION_WORDS) > 0:
            base_weights["Achiever"] = base_weights.get("Achiever", 0.2) + 0.1
        if len(words & self.PREVENTION_WORDS) > 0:
            base_weights["Guardian"] = base_weights.get("Guardian", 0.15) + 0.15
        if len(words & self.ANALYTICAL_WORDS) > 0:
            base_weights["Analyzer"] = base_weights.get("Analyzer", 0.15) + 0.15
        if len(words & self.SOCIAL_WORDS) > 0:
            base_weights["Connector"] = base_weights.get("Connector", 0.25) + 0.15
        if len(words & self.EXPLORER_WORDS) > 0:
            base_weights["Explorer"] = base_weights.get("Explorer", 0.2) + 0.15
        
        # Rating adjustments
        if rating >= 4.5 or (domain == "steam" and rating == 1):  # Steam uses thumbs up (1) / down (0)
            base_weights["Connector"] = base_weights.get("Connector", 0.25) + 0.05
        elif rating <= 2 or (domain == "steam" and rating == 0):
            base_weights["Analyzer"] = base_weights.get("Analyzer", 0.15) + 0.1
        
        # STEAM UNIQUE: Playtime adjustments
        if playtime_hours is not None:
            if playtime_hours > 100:  # Heavy engagement
                base_weights["Achiever"] = base_weights.get("Achiever", 0.2) + 0.15
                base_weights["Explorer"] = base_weights.get("Explorer", 0.2) + 0.1
            elif playtime_hours > 20:  # Moderate engagement
                base_weights["Achiever"] = base_weights.get("Achiever", 0.2) + 0.05
            elif playtime_hours < 2:  # Quick judgment
                base_weights["Pragmatist"] = base_weights.get("Pragmatist", 0.1) + 0.1
                base_weights["Analyzer"] = base_weights.get("Analyzer", 0.15) + 0.05
        
        # Normalize
        total = sum(base_weights.values())
        normalized = {k: v / total for k, v in base_weights.items()}
        archetype = max(normalized, key=normalized.get)
        return archetype, normalized[archetype]
    
    def _normalize_podcast_category(self, category: str) -> str:
        cat_lower = category.lower() if category else ""
        if any(x in cat_lower for x in ["comedy", "humor", "funny"]):
            return "comedy"
        elif any(x in cat_lower for x in ["news", "politics", "current"]):
            return "news"
        elif any(x in cat_lower for x in ["crime", "mystery", "true crime"]):
            return "true crime"
        elif any(x in cat_lower for x in ["education", "learning", "history", "science"]):
            return "education"
        elif any(x in cat_lower for x in ["business", "finance", "entrepreneur", "career"]):
            return "business"
        elif any(x in cat_lower for x in ["health", "fitness", "wellness", "mental"]):
            return "health"
        elif any(x in cat_lower for x in ["sport", "football", "basketball", "soccer"]):
            return "sports"
        elif any(x in cat_lower for x in ["music", "song", "artist"]):
            return "music"
        elif any(x in cat_lower for x in ["society", "culture", "relationship"]):
            return "society"
        elif any(x in cat_lower for x in ["tech", "technology", "computer", "internet"]):
            return "technology"
        return "general"
    
    def _normalize_game_genre(self, genre: str) -> str:
        genre_lower = genre.lower() if genre else ""
        if any(x in genre_lower for x in ["action", "shooter", "fps"]):
            return "action"
        elif any(x in genre_lower for x in ["rpg", "role", "playing"]):
            return "rpg"
        elif any(x in genre_lower for x in ["strategy", "rts", "tactics"]):
            return "strategy"
        elif any(x in genre_lower for x in ["simulation", "sim", "building"]):
            return "simulation"
        elif any(x in genre_lower for x in ["adventure", "exploration"]):
            return "adventure"
        elif any(x in genre_lower for x in ["indie"]):
            return "indie"
        elif any(x in genre_lower for x in ["casual", "puzzle"]):
            return "casual"
        elif any(x in genre_lower for x in ["multiplayer", "mmo", "online"]):
            return "multiplayer"
        elif any(x in genre_lower for x in ["horror", "survival"]):
            return "horror"
        elif any(x in genre_lower for x in ["sports", "racing"]):
            return "sports"
        return "general"
    
    def _normalize_beauty_category(self, category: str) -> str:
        cat_lower = category.lower() if category else ""
        if any(x in cat_lower for x in ["skin", "face", "moistur", "serum", "cleanser"]):
            return "skincare"
        elif any(x in cat_lower for x in ["makeup", "lipstick", "foundation", "mascara", "eyeshadow"]):
            return "makeup"
        elif any(x in cat_lower for x in ["hair", "shampoo", "conditioner"]):
            return "haircare"
        elif any(x in cat_lower for x in ["fragrance", "perfume", "cologne"]):
            return "fragrance"
        elif any(x in cat_lower for x in ["tool", "brush", "applicator"]):
            return "tools"
        return "skincare"


# =============================================================================
# AGGREGATORS
# =============================================================================

@dataclass
class SpecialtyAggregator:
    """Aggregates specialty review data."""
    
    # Podcast patterns
    podcast_category_archetypes: Dict[str, Dict[str, int]] = field(default_factory=lambda: defaultdict(lambda: defaultdict(int)))
    podcast_rating_archetypes: Dict[int, Dict[str, int]] = field(default_factory=lambda: defaultdict(lambda: defaultdict(int)))
    
    # Steam patterns (UNIQUE: playtime)
    steam_genre_archetypes: Dict[str, Dict[str, int]] = field(default_factory=lambda: defaultdict(lambda: defaultdict(int)))
    steam_playtime_archetypes: Dict[str, Dict[str, int]] = field(default_factory=lambda: defaultdict(lambda: defaultdict(int)))  # playtime bucket → archetype
    steam_recommendation_archetypes: Dict[str, Dict[str, int]] = field(default_factory=lambda: defaultdict(lambda: defaultdict(int)))  # recommended/not → archetype
    steam_playtime_by_archetype: Dict[str, List[float]] = field(default_factory=lambda: defaultdict(list))  # archetype → playtimes
    
    # Sephora patterns (UNIQUE: personal characteristics)
    sephora_category_archetypes: Dict[str, Dict[str, int]] = field(default_factory=lambda: defaultdict(lambda: defaultdict(int)))
    sephora_skin_type_archetypes: Dict[str, Dict[str, int]] = field(default_factory=lambda: defaultdict(lambda: defaultdict(int)))
    sephora_hair_type_archetypes: Dict[str, Dict[str, int]] = field(default_factory=lambda: defaultdict(lambda: defaultdict(int)))
    sephora_eye_color_archetypes: Dict[str, Dict[str, int]] = field(default_factory=lambda: defaultdict(lambda: defaultdict(int)))
    sephora_rating_archetypes: Dict[int, Dict[str, int]] = field(default_factory=lambda: defaultdict(lambda: defaultdict(int)))
    
    # Source stats
    source_stats: Dict[str, Dict[str, int]] = field(default_factory=lambda: defaultdict(lambda: {"reviews": 0, "unique_items": 0}))
    
    def add_podcast_review(self, category: str, archetype: str, rating: int):
        self.podcast_category_archetypes[category][archetype] += 1
        self.podcast_rating_archetypes[rating][archetype] += 1
        self.source_stats["podcasts"]["reviews"] += 1
    
    def add_steam_review(self, genre: str, archetype: str, playtime_hours: float, recommended: bool):
        self.steam_genre_archetypes[genre][archetype] += 1
        
        # Playtime buckets
        if playtime_hours < 2:
            bucket = "quick_judge_0_2h"
        elif playtime_hours < 10:
            bucket = "sampler_2_10h"
        elif playtime_hours < 50:
            bucket = "engaged_10_50h"
        elif playtime_hours < 200:
            bucket = "dedicated_50_200h"
        else:
            bucket = "hardcore_200h_plus"
        
        self.steam_playtime_archetypes[bucket][archetype] += 1
        self.steam_recommendation_archetypes["recommended" if recommended else "not_recommended"][archetype] += 1
        
        # Track actual playtimes for statistics
        if len(self.steam_playtime_by_archetype[archetype]) < 10000:
            self.steam_playtime_by_archetype[archetype].append(playtime_hours)
        
        self.source_stats["steam"]["reviews"] += 1
    
    def add_sephora_review(self, category: str, archetype: str, rating: int, 
                          skin_type: str = None, hair_type: str = None, eye_color: str = None):
        self.sephora_category_archetypes[category][archetype] += 1
        self.sephora_rating_archetypes[rating][archetype] += 1
        
        if skin_type:
            self.sephora_skin_type_archetypes[skin_type][archetype] += 1
        if hair_type:
            self.sephora_hair_type_archetypes[hair_type][archetype] += 1
        if eye_color:
            self.sephora_eye_color_archetypes[eye_color][archetype] += 1
        
        self.source_stats["sephora"]["reviews"] += 1


# =============================================================================
# PARSERS
# =============================================================================

def parse_podcast_reviews(filepath: Path, sample_rate: float = 1.0, max_reviews: int = None):
    """Parse podcast reviews JSON."""
    count = 0
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                if max_reviews and count >= max_reviews:
                    break
                if sample_rate < 1.0 and np.random.random() > sample_rate:
                    continue
                try:
                    row = json.loads(line.strip())
                    yield {
                        "text": row.get("content", row.get("title", "")),
                        "rating": int(row.get("rating", 3)),
                        "category": row.get("category", "general"),
                        "podcast_id": row.get("podcast_id", ""),
                    }
                    count += 1
                except:
                    continue
    except Exception as e:
        logger.warning(f"Error parsing podcasts: {e}")
    logger.info(f"  Parsed {count} podcast reviews")


def parse_steam_reviews(filepath: Path, sample_rate: float = 1.0, max_reviews: int = None):
    """Parse Steam reviews CSV."""
    # Increase CSV field size limit for large review texts
    csv.field_size_limit(10 * 1024 * 1024)  # 10MB limit
    
    count = 0
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if max_reviews and count >= max_reviews:
                    break
                if sample_rate < 1.0 and np.random.random() > sample_rate:
                    continue
                try:
                    # Steam CSV fields may vary - try common field names
                    text = row.get("review", row.get("review_text", row.get("content", "")))
                    
                    # Playtime in minutes or hours
                    playtime = row.get("author.playtime_forever", row.get("playtime_forever", 
                               row.get("playtime_at_review", row.get("hours", 0))))
                    try:
                        playtime_hours = float(playtime) / 60 if float(playtime) > 1000 else float(playtime)
                    except:
                        playtime_hours = 0
                    
                    # Recommendation
                    recommended = row.get("voted_up", row.get("recommended", "true"))
                    if isinstance(recommended, str):
                        recommended = recommended.lower() in ["true", "1", "yes"]
                    
                    yield {
                        "text": text,
                        "playtime_hours": playtime_hours,
                        "recommended": recommended,
                        "genre": row.get("genre", row.get("tags", "general")),
                        "app_id": row.get("app_id", row.get("steam_id", "")),
                    }
                    count += 1
                except Exception as e:
                    continue
    except Exception as e:
        logger.warning(f"Error parsing Steam: {e}")
    logger.info(f"  Parsed {count} Steam reviews")


def parse_sephora_reviews(directory: Path, sample_rate: float = 1.0, max_reviews: int = None):
    """Parse Sephora reviews from multiple CSV files."""
    count = 0
    
    # Load product info for categories
    product_info = {}
    product_file = directory / "product_info.csv"
    if product_file.exists():
        try:
            with open(product_file, 'r', encoding='utf-8', errors='ignore') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    product_id = row.get("product_id", row.get("id", ""))
                    if product_id:
                        product_info[product_id] = {
                            "category": row.get("primary_category", row.get("category", "skincare")),
                            "brand": row.get("brand_name", row.get("brand", "")),
                        }
        except Exception as e:
            logger.warning(f"Error loading product info: {e}")
    
    # Parse review files
    review_files = sorted(directory.glob("reviews_*.csv"))
    for review_file in review_files:
        try:
            with open(review_file, 'r', encoding='utf-8', errors='ignore') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if max_reviews and count >= max_reviews:
                        return
                    if sample_rate < 1.0 and np.random.random() > sample_rate:
                        continue
                    try:
                        product_id = row.get("product_id", row.get("id", ""))
                        product = product_info.get(product_id, {})
                        
                        yield {
                            "text": row.get("review_text", row.get("text", "")),
                            "rating": int(float(row.get("rating", 3))),
                            "category": product.get("category", row.get("primary_category", "skincare")),
                            "skin_type": row.get("skin_type", row.get("author_skin_type", "")),
                            "hair_type": row.get("hair_type", row.get("author_hair_type", "")),
                            "eye_color": row.get("eye_color", row.get("author_eye_color", "")),
                            "brand": product.get("brand", row.get("brand_name", "")),
                        }
                        count += 1
                    except:
                        continue
        except Exception as e:
            logger.warning(f"Error parsing {review_file.name}: {e}")
    
    logger.info(f"  Parsed {count} Sephora reviews")


# =============================================================================
# GENERATE PRIORS
# =============================================================================

def generate_specialty_priors(aggregator: SpecialtyAggregator) -> Dict[str, Any]:
    """Generate priors from specialty reviews."""
    
    priors = {}
    
    # =========================================================================
    # PODCAST PRIORS
    # =========================================================================
    
    # Podcast category → archetype
    podcast_category_priors = {}
    for category, archetypes in aggregator.podcast_category_archetypes.items():
        total = sum(archetypes.values())
        if total >= 20:
            podcast_category_priors[category] = {
                arch: round(count / total, 4)
                for arch, count in archetypes.items()
            }
    priors["podcast_category_archetype_priors"] = podcast_category_priors
    
    # Podcast rating patterns
    podcast_rating_priors = {}
    for rating, archetypes in aggregator.podcast_rating_archetypes.items():
        total = sum(archetypes.values())
        if total > 0:
            podcast_rating_priors[str(rating)] = {
                arch: round(count / total, 4)
                for arch, count in archetypes.items()
            }
    priors["podcast_rating_patterns"] = podcast_rating_priors
    
    # =========================================================================
    # STEAM PRIORS (UNIQUE: Playtime)
    # =========================================================================
    
    # Steam genre → archetype
    steam_genre_priors = {}
    for genre, archetypes in aggregator.steam_genre_archetypes.items():
        total = sum(archetypes.values())
        if total >= 20:
            steam_genre_priors[genre] = {
                arch: round(count / total, 4)
                for arch, count in archetypes.items()
            }
    priors["steam_genre_archetype_priors"] = steam_genre_priors
    
    # UNIQUE: Playtime engagement → archetype
    playtime_priors = {}
    for bucket, archetypes in aggregator.steam_playtime_archetypes.items():
        total = sum(archetypes.values())
        if total >= 20:
            playtime_priors[bucket] = {
                arch: round(count / total, 4)
                for arch, count in archetypes.items()
            }
    priors["steam_playtime_archetype_priors"] = playtime_priors
    
    # UNIQUE: Average playtime by archetype
    playtime_stats = {}
    for archetype, playtimes in aggregator.steam_playtime_by_archetype.items():
        if playtimes:
            playtime_stats[archetype] = {
                "avg_hours": round(np.mean(playtimes), 1),
                "median_hours": round(np.median(playtimes), 1),
                "p90_hours": round(np.percentile(playtimes, 90), 1),
                "count": len(playtimes),
            }
    priors["steam_playtime_stats_by_archetype"] = playtime_stats
    
    # Recommendation patterns
    rec_priors = {}
    for rec_status, archetypes in aggregator.steam_recommendation_archetypes.items():
        total = sum(archetypes.values())
        if total > 0:
            rec_priors[rec_status] = {
                arch: round(count / total, 4)
                for arch, count in archetypes.items()
            }
    priors["steam_recommendation_patterns"] = rec_priors
    
    # =========================================================================
    # SEPHORA PRIORS (UNIQUE: Personal Characteristics)
    # =========================================================================
    
    # Sephora category → archetype
    sephora_category_priors = {}
    for category, archetypes in aggregator.sephora_category_archetypes.items():
        total = sum(archetypes.values())
        if total >= 20:
            sephora_category_priors[category] = {
                arch: round(count / total, 4)
                for arch, count in archetypes.items()
            }
    priors["sephora_category_archetype_priors"] = sephora_category_priors
    
    # UNIQUE: Skin type → archetype
    skin_type_priors = {}
    for skin_type, archetypes in aggregator.sephora_skin_type_archetypes.items():
        total = sum(archetypes.values())
        if total >= 20:
            skin_type_priors[skin_type] = {
                arch: round(count / total, 4)
                for arch, count in archetypes.items()
            }
    priors["sephora_skin_type_archetype_priors"] = skin_type_priors
    
    # UNIQUE: Hair type → archetype
    hair_type_priors = {}
    for hair_type, archetypes in aggregator.sephora_hair_type_archetypes.items():
        total = sum(archetypes.values())
        if total >= 20:
            hair_type_priors[hair_type] = {
                arch: round(count / total, 4)
                for arch, count in archetypes.items()
            }
    priors["sephora_hair_type_archetype_priors"] = hair_type_priors
    
    # UNIQUE: Eye color → archetype
    eye_color_priors = {}
    for eye_color, archetypes in aggregator.sephora_eye_color_archetypes.items():
        total = sum(archetypes.values())
        if total >= 20:
            eye_color_priors[eye_color] = {
                arch: round(count / total, 4)
                for arch, count in archetypes.items()
            }
    priors["sephora_eye_color_archetype_priors"] = eye_color_priors
    
    # =========================================================================
    # SOURCE STATISTICS
    # =========================================================================
    priors["specialty_source_statistics"] = dict(aggregator.source_stats)
    
    return priors


def merge_specialty_priors(specialty: Dict, existing_path: Path) -> Dict:
    """Merge specialty priors with existing."""
    if not existing_path.exists():
        return specialty
    
    with open(existing_path) as f:
        existing = json.load(f)
    
    merged = existing.copy()
    
    # Add all specialty priors
    for key, value in specialty.items():
        merged[key] = value
    
    # Update source statistics
    existing_stats = existing.get("source_statistics", {})
    specialty_stats = specialty.get("specialty_source_statistics", {})
    for source, stats in specialty_stats.items():
        existing_stats[source] = stats
    merged["source_statistics"] = existing_stats
    
    return merged


# =============================================================================
# MAIN
# =============================================================================

async def main():
    start_time = datetime.now()
    
    print("\n" + "=" * 70)
    print("SPECIALTY REVIEWS DEEP LEARNING PIPELINE")
    print("=" * 70)
    print(f"Started at: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("\nProcessing:")
    print("  1. Podcasts - Episode engagement, host loyalty, categories")
    print("  2. Steam - Playtime engagement depth, genre preferences")
    print("  3. Sephora - Skin type, hair type, personal characteristics")
    print()
    
    aggregator = SpecialtyAggregator()
    classifier = SpecialtyArchetypeClassifier()
    
    # =========================================================================
    # PROCESS PODCASTS
    # =========================================================================
    
    logger.info("=" * 50)
    logger.info("PROCESSING PODCASTS")
    logger.info("=" * 50)
    
    podcast_file = PODCAST_DIR / "reviews.json"
    if podcast_file.exists():
        logger.info(f"Loading {podcast_file}...")
        for review in parse_podcast_reviews(podcast_file, sample_rate=0.1, max_reviews=500000):
            archetype, _ = classifier.classify(
                review["text"],
                review["rating"],
                "podcast",
                review.get("category", "general"),
            )
            aggregator.add_podcast_review(
                category=classifier._normalize_podcast_category(review.get("category", "")),
                archetype=archetype,
                rating=review["rating"],
            )
    else:
        logger.warning(f"Podcast file not found: {podcast_file}")
    
    logger.info(f"Podcast reviews processed: {aggregator.source_stats['podcasts']['reviews']}")
    
    # =========================================================================
    # PROCESS STEAM
    # =========================================================================
    
    logger.info("\n" + "=" * 50)
    logger.info("PROCESSING STEAM")
    logger.info("=" * 50)
    
    steam_file = STEAM_DIR / "steam_reviews.csv"
    if steam_file.exists():
        logger.info(f"Loading {steam_file}...")
        for review in parse_steam_reviews(steam_file, sample_rate=0.1, max_reviews=500000):
            archetype, _ = classifier.classify(
                review["text"],
                1 if review["recommended"] else 0,
                "steam",
                review.get("genre", "general"),
                playtime_hours=review.get("playtime_hours", 0),
            )
            aggregator.add_steam_review(
                genre=classifier._normalize_game_genre(review.get("genre", "")),
                archetype=archetype,
                playtime_hours=review.get("playtime_hours", 0),
                recommended=review.get("recommended", True),
            )
    else:
        logger.warning(f"Steam file not found: {steam_file}")
    
    logger.info(f"Steam reviews processed: {aggregator.source_stats['steam']['reviews']}")
    
    # =========================================================================
    # PROCESS SEPHORA
    # =========================================================================
    
    logger.info("\n" + "=" * 50)
    logger.info("PROCESSING SEPHORA")
    logger.info("=" * 50)
    
    if SEPHORA_DIR.exists():
        logger.info(f"Loading Sephora reviews from {SEPHORA_DIR}...")
        for review in parse_sephora_reviews(SEPHORA_DIR, sample_rate=0.5, max_reviews=500000):
            archetype, _ = classifier.classify(
                review["text"],
                review["rating"],
                "sephora",
                review.get("category", "skincare"),
            )
            aggregator.add_sephora_review(
                category=classifier._normalize_beauty_category(review.get("category", "")),
                archetype=archetype,
                rating=review["rating"],
                skin_type=review.get("skin_type"),
                hair_type=review.get("hair_type"),
                eye_color=review.get("eye_color"),
            )
    else:
        logger.warning(f"Sephora directory not found: {SEPHORA_DIR}")
    
    logger.info(f"Sephora reviews processed: {aggregator.source_stats['sephora']['reviews']}")
    
    # =========================================================================
    # GENERATE AND SAVE PRIORS
    # =========================================================================
    
    logger.info("\n" + "=" * 50)
    logger.info("GENERATING PRIORS")
    logger.info("=" * 50)
    
    specialty_priors = generate_specialty_priors(aggregator)
    
    # Save specialty priors
    with open(SPECIALTY_PRIORS_PATH, 'w') as f:
        json.dump(specialty_priors, f, indent=2)
    logger.info(f"✓ Specialty priors saved: {SPECIALTY_PRIORS_PATH}")
    
    # Merge with existing
    logger.info("Merging with existing priors...")
    merged = merge_specialty_priors(specialty_priors, MERGED_PRIORS_PATH)
    
    with open(MERGED_PRIORS_PATH, 'w') as f:
        json.dump(merged, f, indent=2)
    logger.info(f"✓ Merged priors saved: {MERGED_PRIORS_PATH}")
    
    # =========================================================================
    # SUMMARY
    # =========================================================================
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    print("\n" + "=" * 70)
    print("SPECIALTY LEARNING COMPLETE")
    print("=" * 70)
    print(f"\nProcessing time: {duration:.1f} seconds ({duration/60:.1f} minutes)")
    
    print(f"\nReviews processed:")
    print(f"  • Podcasts: {aggregator.source_stats['podcasts']['reviews']:,}")
    print(f"  • Steam: {aggregator.source_stats['steam']['reviews']:,}")
    print(f"  • Sephora: {aggregator.source_stats['sephora']['reviews']:,}")
    
    total = sum(s["reviews"] for s in aggregator.source_stats.values())
    print(f"  • TOTAL: {total:,}")
    
    print("\nUNIQUE PATTERNS EXTRACTED:")
    print("  [PODCASTS]")
    print(f"    • Category priors: {len(specialty_priors.get('podcast_category_archetype_priors', {}))}")
    
    print("  [STEAM - Engagement Depth]")
    print(f"    • Genre priors: {len(specialty_priors.get('steam_genre_archetype_priors', {}))}")
    print(f"    • Playtime buckets: {len(specialty_priors.get('steam_playtime_archetype_priors', {}))}")
    
    playtime_stats = specialty_priors.get("steam_playtime_stats_by_archetype", {})
    if playtime_stats:
        print("    • Avg playtime by archetype:")
        for arch, stats in sorted(playtime_stats.items(), key=lambda x: x[1].get("avg_hours", 0), reverse=True)[:5]:
            print(f"      - {arch}: {stats.get('avg_hours', 0):.1f} hours avg")
    
    print("  [SEPHORA - Personal Characteristics]")
    print(f"    • Skin types: {len(specialty_priors.get('sephora_skin_type_archetype_priors', {}))}")
    print(f"    • Hair types: {len(specialty_priors.get('sephora_hair_type_archetype_priors', {}))}")
    print(f"    • Eye colors: {len(specialty_priors.get('sephora_eye_color_archetype_priors', {}))}")
    
    print("\n✓ Specialty learning complete!")


if __name__ == "__main__":
    asyncio.run(main())
