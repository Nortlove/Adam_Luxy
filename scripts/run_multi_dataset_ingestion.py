#!/usr/bin/env python3
"""
MULTI-DATASET REVIEW INTELLIGENCE INGESTION
============================================

Processes all non-Amazon review datasets with psychological extraction.

Processing Order (Small → Large, Google LAST):
1. Trustpilot (2.6MB) - Brand reputation signals
2. BH Photo (71MB) - Tech product expertise  
3. Airline (128MB) - Service touchpoint psychology
4. Auto/Edmunds (138MB) - High-value purchase decisions
5. Sephora (504MB) - Physical identity (skin/eye color)
6. Restaurants (919MB) - Local dining preferences
7. MovieLens (1.1GB) - Psychological genome tags
8. Hotel (2.2GB) - Travel decision patterns
9. Podcast (5.1GB) - Audio content → iHeart alignment
10. Steam (7.6GB) - Engagement depth (playtime)
11. Movies/Netflix (9.5GB) - Entertainment preferences
12. Yelp Academic (16GB) - Social influence (friends, elite)
13. Twitter (19GB) - Mental health + emotional states
14. Reddit MBTI (2.7GB) - Personality ground truth (self-identified)
15. Glassdoor (279MB) - Professional values + dual-valence NDF
16. Rent the Runway (118MB) - Occasion-driven decision psychology
17. TWCS (493MB) - Service recovery persuasion + escalation dynamics
18. Google Local (201GB) - Hyperlocal targeting (LAST - MASSIVE)

Output:
- Per-dataset intelligence files
- Unified psychological constructs
- DSP/SSP/Agency formatted outputs
- Learning artifacts for Graph/AoT/LangGraph
"""

import argparse
import csv
import gzip
import json
import logging
import multiprocessing as mp
import os
import re
import sys
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Set, Tuple
import math

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# Increase CSV field size limit for large fields
csv.field_size_limit(sys.maxsize)


# =============================================================================
# NEW EXTRACTION LAYER: NDF + Hyperscan + 430+ Dimensions
# =============================================================================

_hyperscan_analyzer = None
_deep_detector = None
_ndf_extract_fn = None
_ndf_aggregator_cls = None
_comprehensive_extract_fn = None
_comprehensive_stats_cls = None


def _init_ndf():
    """Lazy-load NDF extraction functions."""
    global _ndf_extract_fn, _ndf_aggregator_cls
    if _ndf_extract_fn is not None:
        return True
    try:
        from adam.intelligence.ndf_extractor import extract_ndf, NDFAggregator
        _ndf_extract_fn = extract_ndf
        _ndf_aggregator_cls = NDFAggregator
        logger.info("NDF extraction enabled (7 nonconscious decision dimensions)")
        return True
    except Exception as e:
        logger.warning(f"NDF extraction unavailable: {e}")
        return False


def _init_hyperscan():
    """Lazy-load Hyperscan analyzer (82-framework, 10k+ reviews/sec)."""
    global _hyperscan_analyzer
    if _hyperscan_analyzer is not None:
        return _hyperscan_analyzer
    try:
        import hyperscan  # noqa: F401
        from scripts.run_82_framework_hyperscan import HyperscanAnalyzer
        _hyperscan_analyzer = HyperscanAnalyzer()
        logger.info("Hyperscan analyzer initialized (82-framework, 10k+ reviews/sec)")
        return _hyperscan_analyzer
    except Exception as e:
        logger.debug(f"Hyperscan unavailable, using fallback archetype detection: {e}")
        return None


def _init_deep_detector():
    """Lazy-load DeepArchetypeDetector fallback."""
    global _deep_detector
    if _deep_detector is not None:
        return _deep_detector
    try:
        from adam.intelligence.deep_archetype_detection import DeepArchetypeDetector
        _deep_detector = DeepArchetypeDetector()
        logger.info("DeepArchetypeDetector initialized (fallback archetype detection)")
        return _deep_detector
    except Exception as e:
        logger.debug(f"DeepArchetypeDetector unavailable: {e}")
        return None


def _init_comprehensive():
    """Lazy-load comprehensive profile extraction (430+ dimensions)."""
    global _comprehensive_extract_fn, _comprehensive_stats_cls
    if _comprehensive_extract_fn is not None:
        return True
    try:
        from scripts.overnight_comprehensive_reprocessor import (
            extract_comprehensive_profile,
            ComprehensiveStats,
        )
        _comprehensive_extract_fn = extract_comprehensive_profile
        _comprehensive_stats_cls = ComprehensiveStats
        logger.info("Comprehensive profile extraction enabled (430+ dimensions + 10 new)")
        return True
    except Exception as e:
        logger.warning(f"Comprehensive profile extraction unavailable: {e}")
        return False


def init_new_extraction_layer():
    """Initialize all new extraction components. Call once at startup."""
    ndf_ok = _init_ndf()
    hs = _init_hyperscan()
    if hs is None:
        _init_deep_detector()
    comp_ok = _init_comprehensive()
    return ndf_ok, (hs is not None or _deep_detector is not None), comp_ok


def detect_archetype_new(text: str) -> str:
    """Detect archetype using Hyperscan (fast) or DeepArchetypeDetector (fallback)."""
    if _hyperscan_analyzer is not None:
        try:
            result = _hyperscan_analyzer.analyze(text)
            arch = result.get("archetype", "") if isinstance(result, dict) else ""
            if arch:
                return arch
        except Exception:
            pass
    if _deep_detector is not None:
        try:
            result = _deep_detector.detect(text)
            if isinstance(result, dict):
                return result.get("primary_archetype", result.get("archetype", "unknown"))
        except Exception:
            pass
    return "unknown"


def extract_new_intelligence(text: str, rating: float, ndf_agg, comp_stats):
    """
    Apply all new extraction layers to a single review text.
    
    Args:
        text: Review text (must be non-empty)
        rating: Normalized rating (0-1)
        ndf_agg: NDFAggregator instance (or None to skip NDF)
        comp_stats: ComprehensiveStats instance (or None to skip 430+ dims)
    """
    if not text or len(text) < 30:
        return
    
    archetype = "unknown"
    
    # 1. Archetype detection (Hyperscan or Deep)
    if len(text) > 50:
        archetype = detect_archetype_new(text)
    
    # 2. NDF extraction
    if ndf_agg is not None and _ndf_extract_fn is not None:
        try:
            ndf = _ndf_extract_fn(text, rating=rating * 5.0 if rating else 0.0)
            ndf_agg.add(ndf, archetype=archetype)
        except Exception:
            pass
    
    # 3. 430+ dimensions via comprehensive profile
    if comp_stats is not None and _comprehensive_extract_fn is not None and len(text) > 50:
        try:
            profile = _comprehensive_extract_fn(text, rating * 5.0 if rating else 0.0)
            if profile:
                comp_stats.add_profile(profile, rating * 5.0 if rating else 0.0)
        except Exception:
            pass


def create_ndf_aggregator():
    """Create a new NDFAggregator if available."""
    if _ndf_aggregator_cls is not None:
        return _ndf_aggregator_cls()
    return None


def create_comprehensive_stats(source_name: str):
    """Create a new ComprehensiveStats if available."""
    if _comprehensive_stats_cls is not None:
        return _comprehensive_stats_cls(source=source_name)
    return None


# =============================================================================
# CONFIGURATION
# =============================================================================

# Data paths
REVIEW_DATA_ROOT = Path("/Volumes/Sped/Nocera Models/Review Data")
OUTPUT_DIR = Path("/Users/chrisnocera/Sites/adam-platform/data/multi_dataset_output")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Hardware optimization
NUM_WORKERS = 8
BATCH_SIZE = 10000
CHECKPOINT_INTERVAL = 100000

# Dataset definitions (ordered by size - smallest first, Google LAST)
DATASETS = [
    {
        "name": "trustpilot",
        "display_name": "Trustpilot",
        "path": REVIEW_DATA_ROOT / "Trust Pilot Reviews 2022" / "trust_pilot_reviews_data_2022_06.csv",
        "file_type": "csv",
        "text_field": "review_text",
        "rating_field": "rating",
        "unique_value": "Brand reputation and B2B trust signals",
        "size_mb": 2.6,
    },
    {
        "name": "bh_photo",
        "display_name": "BH Photo",
        "path": REVIEW_DATA_ROOT / "BH Photo E-Commerce Product Reviews" / "bhphotovideo.csv",
        "file_type": "csv",
        "text_field": "text",  # Actual field name
        "rating_field": "serviceRating",  # Actual field name
        "unique_value": "Tech product expertise and professional buyer psychology",
        "size_mb": 71,
    },
    {
        "name": "airline",
        "display_name": "Airline Reviews",
        "path": REVIEW_DATA_ROOT / "airline_reviews" / "Airline Company Reviews.csv",
        "file_type": "csv",
        "text_field": "Comment",  # Actual field name
        "rating_field": "Rating",  # Actual field name (1-10 scale)
        "unique_value": "Service touchpoint analysis and travel decision psychology",
        "size_mb": 128,
    },
    {
        "name": "automotive",
        "display_name": "Automotive (Edmunds)",
        "path": REVIEW_DATA_ROOT / "Auto" / "Edmonds by Car Company - by Make & Model",
        "file_type": "csv_folder",
        "text_field": "Review",
        "rating_field": "Rating",
        "unique_value": "High-value purchase decisions and brand personality",
        "size_mb": 138,
    },
    {
        "name": "sephora",
        "display_name": "Sephora Beauty",
        "path": REVIEW_DATA_ROOT / "sephora_reviews",
        "file_type": "csv_multi",
        "files": ["reviews_0-250.csv", "reviews_250-500.csv", "reviews_500-750.csv", 
                  "reviews_750-1250.csv", "reviews_1250-end.csv"],
        "product_file": "product_info.csv",
        "text_field": "review_text",
        "rating_field": "rating",
        "unique_value": "Physical identity signals (skin tone, eye color, hair type)",
        "size_mb": 504,
    },
    {
        "name": "restaurant",
        "display_name": "Restaurant Reviews",
        "path": REVIEW_DATA_ROOT / "Restaurants",
        "file_type": "csv_multi",
        "files": ["200k_Restaurants_Mostly_US.csv", "380K_US_Restaurants.csv"],
        "text_field": "text",
        "rating_field": "stars",
        "unique_value": "Local dining preferences and social occasion signals",
        "size_mb": 919,
    },
    {
        "name": "movielens",
        "display_name": "MovieLens Genome",
        "path": REVIEW_DATA_ROOT / "Movies & Shows" / "Movie - Lens - 25M - 1995 to 2020",
        "file_type": "movielens",
        "unique_value": "Psychological genome tags (1128 tags) and preference patterns",
        "size_mb": 1100,
    },
    {
        "name": "hotel",
        "display_name": "Hotel Reviews",
        "path": REVIEW_DATA_ROOT / "hotel_reviews" / "hotels.csv",
        "file_type": "csv",
        "text_field": "review_text",
        "rating_field": "rating",
        "unique_value": "Travel decision patterns and experience economy signals",
        "size_mb": 2200,
    },
    {
        "name": "podcast",
        "display_name": "Podcast Reviews",
        "path": REVIEW_DATA_ROOT / "Music & Podcasts" / "Podcast",
        "file_type": "podcast",
        "unique_value": "Audio content preferences - direct iHeart SSP alignment",
        "size_mb": 5100,
    },
    {
        "name": "steam",
        "display_name": "Steam Gaming",
        "path": REVIEW_DATA_ROOT / "Gaming" / "Steam Gamers Reviews" / "steam_reviews.csv",
        "file_type": "csv",
        "text_field": "review",
        "rating_field": "voted_up",  # Boolean - needs conversion
        "unique_value": "Engagement depth (playtime hours) and gaming psychology",
        "size_mb": 7600,
    },
    {
        "name": "movies_netflix",
        "display_name": "Movies & Netflix",
        "path": REVIEW_DATA_ROOT / "Movies & Shows",
        "file_type": "movies_multi",
        "unique_value": "Entertainment preferences and narrative psychology",
        "size_mb": 9500,
    },
    {
        "name": "yelp",
        "display_name": "Yelp Academic",
        "path": REVIEW_DATA_ROOT / "yelp_reviews",
        "file_type": "yelp",
        "unique_value": "Social influence (friends network, elite status, compliments)",
        "size_mb": 16000,
    },
    {
        "name": "twitter",
        "display_name": "Twitter Mental Health",
        "path": REVIEW_DATA_ROOT / "Twitter",
        "file_type": "twitter",
        "unique_value": "Emotional state intelligence and mental health signals",
        "size_mb": 19000,
    },
    # NEW DATASETS: Reddit MBTI, Glassdoor, Rent the Runway
    {
        "name": "reddit_mbti",
        "display_name": "Reddit MBTI (Personality Ground Truth)",
        "path": Path("/Users/chrisnocera/Sites/adam-platform/reviews/Reddit MBTI Dataset_Self Identified"),
        "file_type": "reddit_mbti",
        "unique_value": "13M posts with self-identified MBTI types -- personality ground truth calibration",
        "size_mb": 2700,
    },
    {
        "name": "glassdoor",
        "display_name": "Glassdoor Reviews (Professional Values)",
        "path": Path("/Users/chrisnocera/Sites/adam-platform/reviews/glassdoor_reviews/glassdoor_reviews.csv"),
        "file_type": "glassdoor",
        "unique_value": "1.5M employer reviews with dual-valence pros/cons -- professional decision psychology",
        "size_mb": 279,
    },
    {
        "name": "rent_the_runway",
        "display_name": "Rent the Runway (Occasion Psychology)",
        "path": Path("/Users/chrisnocera/Sites/adam-platform/reviews/Rent the Runway/renttherunway_final_data.json"),
        "file_type": "rent_the_runway",
        "unique_value": "192K fashion reviews with occasion context (wedding/party/work) -- situational targeting",
        "size_mb": 118,
    },
    # TWCS: Twitter Customer Service (conversational pairs)
    {
        "name": "twcs",
        "display_name": "Twitter Customer Service (Service Recovery Persuasion)",
        "path": Path("/Users/chrisnocera/Sites/adam-platform/reviews/twcs/twcs.csv"),
        "file_type": "twcs",
        "unique_value": "2.8M brand-customer conversational pairs across 108 brands -- service recovery persuasion fingerprints, escalation dynamics, complaint-state NDF",
        "size_mb": 493,
    },
    # GOOGLE LOCAL LAST - BY FAR THE LARGEST
    {
        "name": "google_local",
        "display_name": "Google Local (50 States)",
        "path": REVIEW_DATA_ROOT / "Google",
        "file_type": "google",
        "unique_value": "Hyperlocal GPS-level targeting with 677M+ reviews, 6 strategic extraction layers",
        "size_mb": 201000,
    },
]


# =============================================================================
# PSYCHOLOGICAL EXTRACTION
# =============================================================================

# 35 Psychological Constructs
CONSTRUCTS = {
    # Tier 1: Customer Susceptibility
    "social_proof_susceptibility": {
        "positive": ["everyone", "popular", "bestseller", "trending", "most people", 
                    "others love", "highly rated", "recommended", "millions"],
        "negative": ["don't care what others", "my own opinion"],
    },
    "scarcity_susceptibility": {
        "positive": ["limited", "rare", "exclusive", "only", "last chance", "sold out", 
                    "hard to find", "special edition"],
        "negative": ["always available", "plenty", "no rush"],
    },
    "authority_susceptibility": {
        "positive": ["expert", "professional", "doctor", "scientist", "certified",
                    "award", "endorsed", "approved", "official"],
        "negative": ["don't trust experts", "do my own research"],
    },
    "novelty_seeking": {
        "positive": ["new", "innovative", "unique", "different", "first", "cutting edge",
                    "latest", "never seen", "revolutionary"],
        "negative": ["classic", "traditional", "tried and true"],
    },
    "price_sensitivity": {
        "positive": ["expensive", "overpriced", "cheaper", "deal", "value", "budget",
                    "affordable", "cost", "price", "money"],
        "negative": ["worth every penny", "money well spent"],
    },
    "brand_loyalty": {
        "positive": ["always buy", "loyal", "favorite brand", "only brand", 
                    "been using for years", "never switch"],
        "negative": ["switching", "trying new", "brand doesn't matter"],
    },
    "impulse_tendency": {
        "positive": ["impulse", "couldn't resist", "had to have", "spontaneous",
                    "saw it and", "right away"],
        "negative": ["researched", "thought about it", "compared"],
    },
    # Tier 2: Message Crafting
    "regulatory_focus": {
        "promotion": ["gain", "achieve", "success", "aspiration", "hope", "dream", "opportunity"],
        "prevention": ["avoid", "prevent", "protect", "safe", "secure", "ought", "should"],
    },
    "construal_level": {
        "abstract": ["overall", "generally", "concept", "purpose", "meaning", "why"],
        "concrete": ["specifically", "exactly", "detail", "step", "how", "feature"],
    },
    "narrative_preference": {
        "story": ["story", "journey", "experience", "happened", "remember when"],
        "facts": ["facts", "data", "statistics", "numbers", "evidence", "proof"],
    },
    # Tier 3: Brand Matching (Big Five)
    "openness": ["creative", "imaginative", "curious", "adventurous", "artistic"],
    "conscientiousness": ["organized", "reliable", "disciplined", "thorough", "careful"],
    "extraversion": ["social", "outgoing", "energetic", "talkative", "enthusiastic"],
    "agreeableness": ["kind", "cooperative", "trusting", "helpful", "generous"],
    "neuroticism": ["anxious", "worried", "stressed", "nervous", "emotional"],
}

# 12 Jungian Archetypes
ARCHETYPE_MARKERS = {
    "innocent": ["pure", "simple", "honest", "trust", "faith", "optimistic", "wholesome"],
    "sage": ["understand", "knowledge", "wisdom", "learn", "truth", "insight", "analyze"],
    "explorer": ["adventure", "discover", "freedom", "journey", "explore", "authentic"],
    "outlaw": ["rebel", "break", "disrupt", "radical", "revolution", "unconventional"],
    "magician": ["transform", "magic", "dream", "vision", "create", "imagine"],
    "hero": ["challenge", "overcome", "achieve", "strength", "courage", "victory"],
    "lover": ["love", "passion", "beautiful", "intimate", "sensual", "romantic"],
    "jester": ["fun", "laugh", "play", "enjoy", "humor", "joke", "entertaining"],
    "everyman": ["everyone", "common", "regular", "relatable", "belong", "community"],
    "caregiver": ["care", "help", "support", "protect", "nurture", "compassion"],
    "ruler": ["control", "lead", "power", "premium", "luxury", "status", "success"],
    "creator": ["create", "design", "innovative", "artistic", "original", "vision"],
}

# Persuasion Mechanisms
MECHANISM_MARKERS = {
    "social_proof": ["everyone", "popular", "reviews", "recommended", "bestseller"],
    "scarcity": ["limited", "only", "last", "exclusive", "rare", "while supplies"],
    "authority": ["expert", "doctor", "certified", "award", "professional"],
    "reciprocity": ["free", "gift", "bonus", "included", "complimentary"],
    "commitment": ["always", "committed", "consistent", "loyal", "habit"],
    "liking": ["love", "like", "enjoy", "pleasant", "friendly", "beautiful"],
    "unity": ["we", "us", "together", "family", "community", "belong"],
    "storytelling": ["story", "journey", "experience", "happened", "remember"],
    "fear_appeal": ["worry", "afraid", "risk", "danger", "threat", "avoid"],
    "nostalgia": ["remember", "classic", "traditional", "childhood", "heritage"],
    "aspiration": ["dream", "goal", "aspire", "become", "future", "achieve"],
    "urgency": ["now", "today", "hurry", "limited time", "don't miss"],
}


def extract_constructs(text: str) -> Dict[str, float]:
    """Extract psychological construct scores from text."""
    if not text:
        return {}
    
    text_lower = text.lower()
    constructs = {}
    
    for construct, markers in CONSTRUCTS.items():
        if isinstance(markers, dict):
            if "positive" in markers and "negative" in markers:
                pos = sum(1 for m in markers["positive"] if m in text_lower)
                neg = sum(1 for m in markers["negative"] if m in text_lower)
                total = pos + neg
                if total > 0:
                    constructs[construct] = pos / total
            elif "promotion" in markers and "prevention" in markers:
                promo = sum(1 for m in markers["promotion"] if m in text_lower)
                prev = sum(1 for m in markers["prevention"] if m in text_lower)
                total = promo + prev
                if total > 0:
                    constructs[construct] = promo / total
            elif "abstract" in markers and "concrete" in markers:
                abstract = sum(1 for m in markers["abstract"] if m in text_lower)
                concrete = sum(1 for m in markers["concrete"] if m in text_lower)
                total = abstract + concrete
                if total > 0:
                    constructs[construct] = abstract / total
            elif "story" in markers and "facts" in markers:
                story = sum(1 for m in markers["story"] if m in text_lower)
                facts = sum(1 for m in markers["facts"] if m in text_lower)
                total = story + facts
                if total > 0:
                    constructs[construct] = story / total
        else:
            count = sum(1 for m in markers if m in text_lower)
            constructs[construct] = min(1.0, count / 5)
    
    return constructs


def detect_archetypes(text: str) -> Dict[str, float]:
    """Detect archetype signals in text."""
    if not text:
        return {}
    
    text_lower = text.lower()
    archetypes = {}
    total = 0
    
    for archetype, markers in ARCHETYPE_MARKERS.items():
        count = sum(1 for m in markers if m in text_lower)
        archetypes[archetype] = count
        total += count
    
    if total > 0:
        archetypes = {k: v / total for k, v in archetypes.items()}
    
    return archetypes


def detect_mechanisms(text: str) -> Dict[str, float]:
    """Detect persuasion mechanisms in text."""
    if not text:
        return {}
    
    text_lower = text.lower()
    mechanisms = {}
    
    for mechanism, markers in MECHANISM_MARKERS.items():
        count = sum(1 for m in markers if m in text_lower)
        mechanisms[mechanism] = min(1.0, count / 3)
    
    return mechanisms


def extract_persuasive_patterns(text: str, rating: float = None, helpful: float = None) -> List[Dict]:
    """Extract persuasive language patterns."""
    patterns = []
    if not text or len(text) < 50:
        return patterns
    
    sentences = re.split(r'[.!?]', text)
    for sentence in sentences:
        sentence = sentence.strip()
        if 20 < len(sentence) < 200:
            mechanisms = []
            sentence_lower = sentence.lower()
            for mech, markers in MECHANISM_MARKERS.items():
                if any(m in sentence_lower for m in markers):
                    mechanisms.append(mech)
            
            if mechanisms:
                patterns.append({
                    "text": sentence,
                    "mechanisms": mechanisms,
                    "rating": rating,
                    "helpful": helpful,
                })
    
    return patterns[:10]  # Limit per review


# =============================================================================
# DATASET PROCESSORS
# =============================================================================

@dataclass
class DatasetResult:
    """Result of processing one dataset."""
    name: str
    display_name: str
    reviews_processed: int = 0
    high_quality_reviews: int = 0
    templates_extracted: int = 0
    
    # Aggregated psychological data
    construct_totals: Dict[str, float] = field(default_factory=dict)
    construct_counts: Dict[str, int] = field(default_factory=dict)
    archetype_totals: Dict[str, float] = field(default_factory=dict)
    mechanism_totals: Dict[str, float] = field(default_factory=dict)
    
    # Top templates
    templates: List[Dict] = field(default_factory=list)
    
    # Dataset-specific intelligence
    specific_intelligence: Dict[str, Any] = field(default_factory=dict)
    
    # NEW: NDF population data (from NDFAggregator)
    ndf_population: Dict[str, Any] = field(default_factory=dict)
    
    # NEW: 430+ dimension distributions (from ComprehensiveStats)
    dimension_distributions: Dict[str, Any] = field(default_factory=dict)
    
    duration_seconds: float = 0.0
    
    def to_dict(self) -> Dict:
        # Calculate averages
        construct_avgs = {}
        for k, v in self.construct_totals.items():
            count = self.construct_counts.get(k, 1)
            construct_avgs[k] = v / count if count > 0 else 0
        
        mechanism_avgs = {k: v / max(1, self.reviews_processed) 
                         for k, v in self.mechanism_totals.items()}
        archetype_avgs = {k: v / max(1, self.reviews_processed) 
                         for k, v in self.archetype_totals.items()}
        
        out = {
            "name": self.name,
            "display_name": self.display_name,
            "reviews_processed": self.reviews_processed,
            "high_quality_reviews": self.high_quality_reviews,
            "templates_extracted": self.templates_extracted,
            "construct_averages": construct_avgs,
            "archetype_distribution": archetype_avgs,
            "mechanism_effectiveness": mechanism_avgs,
            "top_templates": self.templates[:500],
            "specific_intelligence": self.specific_intelligence,
            "duration_seconds": self.duration_seconds,
        }
        
        # Include new extraction data when present
        if self.ndf_population:
            out["ndf_population"] = self.ndf_population
        if self.dimension_distributions:
            out["dimension_distributions"] = self.dimension_distributions
        
        return out


def _finalize_new_extraction(result: DatasetResult, ndf_agg, comp_stats):
    """Finalize new extraction data into the result."""
    if ndf_agg is not None:
        ndf_data = ndf_agg.to_dict()
        if ndf_data.get("ndf_count", 0) > 0:
            result.ndf_population = ndf_data
            logger.info(f"  {result.display_name}: NDF from {ndf_data['ndf_count']:,} reviews "
                        f"({len(ndf_data.get('ndf_archetype_profiles', {}))} archetype profiles)")
    if comp_stats is not None and comp_stats.review_count > 0:
        result.dimension_distributions = comp_stats.to_dict()
        logger.info(f"  {result.display_name}: 430+ dimensions from {comp_stats.review_count:,} reviews")


def process_csv_dataset(config: Dict) -> DatasetResult:
    """Process a single CSV file dataset."""
    result = DatasetResult(name=config["name"], display_name=config["display_name"])
    start_time = time.time()
    
    path = config["path"]
    text_field = config.get("text_field", "review_text")
    rating_field = config.get("rating_field", "rating")
    
    # NEW: Initialize extraction layers
    ndf_agg = create_ndf_aggregator()
    comp_stats = create_comprehensive_stats(config["name"])
    
    logger.info(f"Processing {config['display_name']}...")
    
    try:
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                text = row.get(text_field, "")
                if not text or len(text) < 20:
                    continue
                
                # Get rating
                try:
                    rating_val = row.get(rating_field, "")
                    if rating_val == "True" or rating_val == True:
                        rating = 1.0
                    elif rating_val == "False" or rating_val == False:
                        rating = 0.0
                    else:
                        rating = float(rating_val) if rating_val else None
                except:
                    rating = None
                
                # Extract psychology (legacy)
                constructs = extract_constructs(text)
                archetypes = detect_archetypes(text)
                mechanisms = detect_mechanisms(text)
                
                # NEW: NDF + archetype + 430+ dimensions
                extract_new_intelligence(text, rating if rating else 0.0, ndf_agg, comp_stats)
                
                # Aggregate
                for k, v in constructs.items():
                    result.construct_totals[k] = result.construct_totals.get(k, 0) + v
                    result.construct_counts[k] = result.construct_counts.get(k, 0) + 1
                
                for k, v in archetypes.items():
                    result.archetype_totals[k] = result.archetype_totals.get(k, 0) + v
                
                for k, v in mechanisms.items():
                    result.mechanism_totals[k] = result.mechanism_totals.get(k, 0) + v
                
                # Extract templates from high-quality reviews
                if len(text) > 100 and rating and rating >= 0.8:
                    patterns = extract_persuasive_patterns(text, rating)
                    if patterns:
                        result.templates.extend(patterns)
                        result.templates_extracted += len(patterns)
                        result.high_quality_reviews += 1
                
                result.reviews_processed += 1
                
                if result.reviews_processed % 50000 == 0:
                    logger.info(f"  {config['display_name']}: {result.reviews_processed:,} reviews processed")
    
    except Exception as e:
        logger.error(f"Error processing {config['display_name']}: {e}")
    
    # NEW: Finalize extraction data
    _finalize_new_extraction(result, ndf_agg, comp_stats)
    
    result.duration_seconds = time.time() - start_time
    
    # Sort templates by quality
    result.templates.sort(key=lambda x: len(x.get("mechanisms", [])), reverse=True)
    
    logger.info(f"  {config['display_name']} COMPLETE: {result.reviews_processed:,} reviews, "
                f"{result.templates_extracted} templates in {result.duration_seconds:.1f}s")
    
    return result


def process_csv_folder(config: Dict) -> DatasetResult:
    """Process a folder of CSV files."""
    result = DatasetResult(name=config["name"], display_name=config["display_name"])
    start_time = time.time()
    
    folder_path = Path(config["path"])
    text_field = config.get("text_field", "Review")
    rating_field = config.get("rating_field", "Rating")
    
    # NEW: Initialize extraction layers
    ndf_agg = create_ndf_aggregator()
    comp_stats = create_comprehensive_stats(config["name"])
    
    logger.info(f"Processing {config['display_name']} (folder)...")
    
    # Get all CSV files in folder
    csv_files = list(folder_path.glob("*.csv"))
    
    for csv_file in csv_files:
        try:
            with open(csv_file, 'r', encoding='utf-8', errors='ignore') as f:
                reader = csv.DictReader(f)
                
                for row in reader:
                    text = row.get(text_field, "")
                    if not text or len(text) < 20:
                        continue
                    
                    try:
                        rating = float(row.get(rating_field, 0)) / 5.0  # Normalize to 0-1
                    except:
                        rating = None
                    
                    constructs = extract_constructs(text)
                    archetypes = detect_archetypes(text)
                    mechanisms = detect_mechanisms(text)
                    
                    # NEW: NDF + archetype + 430+ dimensions
                    extract_new_intelligence(text, rating if rating else 0.0, ndf_agg, comp_stats)
                    
                    for k, v in constructs.items():
                        result.construct_totals[k] = result.construct_totals.get(k, 0) + v
                        result.construct_counts[k] = result.construct_counts.get(k, 0) + 1
                    
                    for k, v in archetypes.items():
                        result.archetype_totals[k] = result.archetype_totals.get(k, 0) + v
                    
                    for k, v in mechanisms.items():
                        result.mechanism_totals[k] = result.mechanism_totals.get(k, 0) + v
                    
                    if len(text) > 100 and rating and rating >= 0.8:
                        patterns = extract_persuasive_patterns(text, rating)
                        if patterns:
                            # Add car make/model context
                            make = row.get("Make", "")
                            model = row.get("Model", "")
                            for p in patterns:
                                p["make"] = make
                                p["model"] = model
                            result.templates.extend(patterns)
                            result.templates_extracted += len(patterns)
                            result.high_quality_reviews += 1
                    
                    result.reviews_processed += 1
        
        except Exception as e:
            logger.warning(f"Error processing {csv_file.name}: {e}")
    
    # NEW: Finalize extraction data
    _finalize_new_extraction(result, ndf_agg, comp_stats)
    
    result.duration_seconds = time.time() - start_time
    result.templates.sort(key=lambda x: len(x.get("mechanisms", [])), reverse=True)
    
    logger.info(f"  {config['display_name']} COMPLETE: {result.reviews_processed:,} reviews in {result.duration_seconds:.1f}s")
    
    return result


def process_csv_multi(config: Dict) -> DatasetResult:
    """Process multiple CSV files in a folder."""
    result = DatasetResult(name=config["name"], display_name=config["display_name"])
    start_time = time.time()
    
    folder_path = Path(config["path"])
    text_field = config.get("text_field", "review_text")
    rating_field = config.get("rating_field", "rating")
    files = config.get("files", [])
    
    # NEW: Initialize extraction layers
    ndf_agg = create_ndf_aggregator()
    comp_stats = create_comprehensive_stats(config["name"])
    
    logger.info(f"Processing {config['display_name']} (multi-file)...")
    
    # Load product info if available (for Sephora)
    product_info = {}
    product_file = config.get("product_file")
    if product_file:
        product_path = folder_path / product_file
        if product_path.exists():
            try:
                with open(product_path, 'r', encoding='utf-8', errors='ignore') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        pid = row.get("product_id", "")
                        if pid:
                            product_info[pid] = row
                logger.info(f"  Loaded {len(product_info)} products")
            except Exception as e:
                logger.warning(f"Could not load product info: {e}")
    
    for filename in files:
        file_path = folder_path / filename
        if not file_path.exists():
            continue
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                reader = csv.DictReader(f)
                
                for row in reader:
                    text = row.get(text_field, "")
                    if not text or len(text) < 20:
                        continue
                    
                    try:
                        rating = float(row.get(rating_field, 0)) / 5.0
                    except:
                        rating = None
                    
                    constructs = extract_constructs(text)
                    archetypes = detect_archetypes(text)
                    mechanisms = detect_mechanisms(text)
                    
                    # NEW: NDF + archetype + 430+ dimensions
                    extract_new_intelligence(text, rating if rating else 0.0, ndf_agg, comp_stats)
                    
                    for k, v in constructs.items():
                        result.construct_totals[k] = result.construct_totals.get(k, 0) + v
                        result.construct_counts[k] = result.construct_counts.get(k, 0) + 1
                    
                    for k, v in archetypes.items():
                        result.archetype_totals[k] = result.archetype_totals.get(k, 0) + v
                    
                    for k, v in mechanisms.items():
                        result.mechanism_totals[k] = result.mechanism_totals.get(k, 0) + v
                    
                    if len(text) > 100 and rating and rating >= 0.8:
                        patterns = extract_persuasive_patterns(text, rating)
                        if patterns:
                            # Add Sephora-specific context
                            pid = row.get("product_id", "")
                            product = product_info.get(pid, {})
                            for p in patterns:
                                p["skin_tone"] = row.get("skin_tone", "")
                                p["eye_color"] = row.get("eye_color", "")
                                p["hair_color"] = row.get("hair_color", "")
                                p["skin_type"] = row.get("skin_type", "")
                                p["category"] = product.get("primary_category", "")
                            result.templates.extend(patterns)
                            result.templates_extracted += len(patterns)
                            result.high_quality_reviews += 1
                    
                    result.reviews_processed += 1
                    
                    if result.reviews_processed % 100000 == 0:
                        logger.info(f"  {config['display_name']}: {result.reviews_processed:,} reviews")
        
        except Exception as e:
            logger.warning(f"Error processing {filename}: {e}")
    
    # Add specific intelligence for Sephora
    if config["name"] == "sephora":
        result.specific_intelligence["physical_identity_signals"] = True
        result.specific_intelligence["skin_tone_coverage"] = True
        result.specific_intelligence["eye_color_coverage"] = True
    
    # NEW: Finalize extraction data
    _finalize_new_extraction(result, ndf_agg, comp_stats)
    
    result.duration_seconds = time.time() - start_time
    result.templates.sort(key=lambda x: len(x.get("mechanisms", [])), reverse=True)
    
    logger.info(f"  {config['display_name']} COMPLETE: {result.reviews_processed:,} reviews in {result.duration_seconds:.1f}s")
    
    return result


def process_movielens(config: Dict) -> DatasetResult:
    """Process MovieLens dataset with psychological genome tags."""
    result = DatasetResult(name=config["name"], display_name=config["display_name"])
    start_time = time.time()
    
    path = Path(config["path"])
    
    logger.info(f"Processing {config['display_name']}...")
    
    # Load genome tags
    genome_tags = {}
    tags_file = path / "genome-tags.csv"
    if tags_file.exists():
        with open(tags_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                tag_id = row.get("tagId", "")
                tag_name = row.get("tag", "")
                if tag_id and tag_name:
                    genome_tags[tag_id] = tag_name
    
    logger.info(f"  Loaded {len(genome_tags)} genome tags")
    
    # Process ratings with genome scores
    # MovieLens is unique - it has pre-computed psychological tags per movie
    genome_scores_file = path / "genome-scores.csv"
    movie_psychographics = defaultdict(dict)
    
    if genome_scores_file.exists():
        with open(genome_scores_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                movie_id = row.get("movieId", "")
                tag_id = row.get("tagId", "")
                relevance = float(row.get("relevance", 0))
                
                tag_name = genome_tags.get(tag_id, "")
                if tag_name and relevance > 0.5:
                    movie_psychographics[movie_id][tag_name] = relevance
                
                result.reviews_processed += 1
                if result.reviews_processed % 1000000 == 0:
                    logger.info(f"  Genome scores: {result.reviews_processed:,} processed")
    
    result.specific_intelligence["genome_tags_count"] = len(genome_tags)
    result.specific_intelligence["movies_with_psychographics"] = len(movie_psychographics)
    result.specific_intelligence["tag_examples"] = list(genome_tags.values())[:50]
    
    # Map genome tags to our constructs and archetypes
    tag_to_construct = {
        "action": "extraversion",
        "romance": "agreeableness",
        "dark": "neuroticism",
        "thought-provoking": "openness",
        "classic": "conscientiousness",
    }
    
    for movie_id, tags in movie_psychographics.items():
        for tag, score in tags.items():
            tag_lower = tag.lower()
            for tag_keyword, construct in tag_to_construct.items():
                if tag_keyword in tag_lower:
                    result.construct_totals[construct] = result.construct_totals.get(construct, 0) + score
                    result.construct_counts[construct] = result.construct_counts.get(construct, 0) + 1
    
    result.duration_seconds = time.time() - start_time
    logger.info(f"  {config['display_name']} COMPLETE: {result.reviews_processed:,} genome scores in {result.duration_seconds:.1f}s")
    
    return result


def process_podcast(config: Dict) -> DatasetResult:
    """Process podcast reviews - critical for iHeart SSP."""
    result = DatasetResult(name=config["name"], display_name=config["display_name"])
    start_time = time.time()
    
    path = Path(config["path"])
    
    # NEW: Initialize extraction layers
    ndf_agg = create_ndf_aggregator()
    comp_stats = create_comprehensive_stats(config["name"])
    
    logger.info(f"Processing {config['display_name']}...")
    
    # Load podcasts metadata
    podcasts_file = path / "podcasts.json"
    podcasts = {}
    if podcasts_file.exists():
        with open(podcasts_file, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    podcast = json.loads(line)
                    pid = podcast.get("podcast_id", "")
                    if pid:
                        podcasts[pid] = podcast
                except:
                    continue
    
    logger.info(f"  Loaded {len(podcasts)} podcasts")
    
    # Load categories
    categories_file = path / "categories.json"
    categories = {}
    if categories_file.exists():
        with open(categories_file, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    cat = json.loads(line)
                    cat_id = cat.get("category_id", "")
                    if cat_id:
                        categories[cat_id] = cat
                except:
                    continue
    
    logger.info(f"  Loaded {len(categories)} categories")
    
    # Process reviews
    reviews_file = path / "reviews.json"
    if reviews_file.exists():
        with open(reviews_file, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    review = json.loads(line)
                    text = review.get("content", "")
                    if not text or len(text) < 20:
                        continue
                    
                    rating = review.get("rating", 0) / 5.0
                    
                    constructs = extract_constructs(text)
                    archetypes = detect_archetypes(text)
                    mechanisms = detect_mechanisms(text)
                    
                    # NEW: NDF + archetype + 430+ dimensions
                    extract_new_intelligence(text, rating, ndf_agg, comp_stats)
                    
                    for k, v in constructs.items():
                        result.construct_totals[k] = result.construct_totals.get(k, 0) + v
                        result.construct_counts[k] = result.construct_counts.get(k, 0) + 1
                    
                    for k, v in archetypes.items():
                        result.archetype_totals[k] = result.archetype_totals.get(k, 0) + v
                    
                    for k, v in mechanisms.items():
                        result.mechanism_totals[k] = result.mechanism_totals.get(k, 0) + v
                    
                    if len(text) > 100 and rating >= 0.8:
                        patterns = extract_persuasive_patterns(text, rating)
                        if patterns:
                            # Add podcast context for iHeart
                            podcast_id = review.get("podcast_id", "")
                            podcast = podcasts.get(podcast_id, {})
                            for p in patterns:
                                p["podcast_title"] = podcast.get("title", "")
                                p["podcast_category"] = podcast.get("category", "")
                            result.templates.extend(patterns)
                            result.templates_extracted += len(patterns)
                            result.high_quality_reviews += 1
                    
                    result.reviews_processed += 1
                    if result.reviews_processed % 100000 == 0:
                        logger.info(f"  {config['display_name']}: {result.reviews_processed:,} reviews")
                
                except Exception as e:
                    continue
    
    result.specific_intelligence["iheart_alignment"] = True
    result.specific_intelligence["podcasts_count"] = len(podcasts)
    result.specific_intelligence["categories_count"] = len(categories)
    
    # NEW: Finalize extraction data
    _finalize_new_extraction(result, ndf_agg, comp_stats)
    
    result.duration_seconds = time.time() - start_time
    result.templates.sort(key=lambda x: len(x.get("mechanisms", [])), reverse=True)
    
    logger.info(f"  {config['display_name']} COMPLETE: {result.reviews_processed:,} reviews in {result.duration_seconds:.1f}s")
    
    return result


def process_yelp(config: Dict) -> DatasetResult:
    """Process Yelp academic dataset with social influence signals."""
    result = DatasetResult(name=config["name"], display_name=config["display_name"])
    start_time = time.time()
    
    path = Path(config["path"])
    
    # NEW: Initialize extraction layers
    ndf_agg = create_ndf_aggregator()
    comp_stats = create_comprehensive_stats(config["name"])
    
    logger.info(f"Processing {config['display_name']}...")
    
    # Load users for social influence analysis
    users = {}
    users_file = path / "yelp_academic_dataset_user.json"
    if users_file.exists():
        logger.info("  Loading users for social influence analysis...")
        with open(users_file, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    user = json.loads(line)
                    uid = user.get("user_id", "")
                    if uid:
                        users[uid] = {
                            "review_count": user.get("review_count", 0),
                            "friends_count": len(user.get("friends", "").split(",")),
                            "elite": len(user.get("elite", "").split(",")) if user.get("elite") else 0,
                            "compliments_total": sum([
                                user.get(f"compliment_{t}", 0) 
                                for t in ["hot", "more", "profile", "cute", "list", "note", 
                                         "plain", "cool", "funny", "writer", "photos"]
                            ]),
                        }
                except:
                    continue
        logger.info(f"  Loaded {len(users)} users")
    
    # Process reviews
    reviews_file = path / "yelp_academic_dataset_review.json"
    if reviews_file.exists():
        with open(reviews_file, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    review = json.loads(line)
                    text = review.get("text", "")
                    if not text or len(text) < 20:
                        continue
                    
                    rating = review.get("stars", 0) / 5.0
                    
                    # Helpful signal from useful + funny + cool
                    helpful = (review.get("useful", 0) + review.get("funny", 0) + 
                              review.get("cool", 0)) / 10.0  # Normalize
                    
                    constructs = extract_constructs(text)
                    archetypes = detect_archetypes(text)
                    mechanisms = detect_mechanisms(text)
                    
                    # NEW: NDF + archetype + 430+ dimensions
                    extract_new_intelligence(text, rating, ndf_agg, comp_stats)
                    
                    for k, v in constructs.items():
                        result.construct_totals[k] = result.construct_totals.get(k, 0) + v
                        result.construct_counts[k] = result.construct_counts.get(k, 0) + 1
                    
                    for k, v in archetypes.items():
                        result.archetype_totals[k] = result.archetype_totals.get(k, 0) + v
                    
                    for k, v in mechanisms.items():
                        result.mechanism_totals[k] = result.mechanism_totals.get(k, 0) + v
                    
                    if len(text) > 100 and rating >= 0.8:
                        patterns = extract_persuasive_patterns(text, rating, helpful)
                        if patterns:
                            # Add social influence context
                            user_id = review.get("user_id", "")
                            user = users.get(user_id, {})
                            for p in patterns:
                                p["user_elite_years"] = user.get("elite", 0)
                                p["user_friends"] = user.get("friends_count", 0)
                                p["user_compliments"] = user.get("compliments_total", 0)
                                p["useful"] = review.get("useful", 0)
                                p["funny"] = review.get("funny", 0)
                                p["cool"] = review.get("cool", 0)
                            result.templates.extend(patterns)
                            result.templates_extracted += len(patterns)
                            result.high_quality_reviews += 1
                    
                    result.reviews_processed += 1
                    if result.reviews_processed % 200000 == 0:
                        logger.info(f"  {config['display_name']}: {result.reviews_processed:,} reviews")
                
                except:
                    continue
    
    result.specific_intelligence["social_influence_signals"] = True
    result.specific_intelligence["users_analyzed"] = len(users)
    
    # NEW: Finalize extraction data
    _finalize_new_extraction(result, ndf_agg, comp_stats)
    
    result.duration_seconds = time.time() - start_time
    result.templates.sort(key=lambda x: x.get("useful", 0), reverse=True)
    
    logger.info(f"  {config['display_name']} COMPLETE: {result.reviews_processed:,} reviews in {result.duration_seconds:.1f}s")
    
    return result


def process_twitter(config: Dict) -> DatasetResult:
    """
    Process Twitter mental health dataset - emotional state intelligence.
    
    IMPORTANT: The tweet_profiles_anonymized.csv does NOT contain tweet text (anonymized).
    Instead, we use musics_profiles_anonymized.csv which contains:
    - lyric: Actual text content for psychological extraction
    - emotion_*_score: Pre-computed emotion scores (anger, joy, sadness, etc.)
    - sentiment_direction/score: Sentiment analysis
    - disorder: Mental health classification (for ethical safeguards)
    - genres: Music preferences for psychographic signals
    """
    result = DatasetResult(name=config["name"], display_name=config["display_name"])
    start_time = time.time()
    
    path = Path(config["path"])
    
    # NEW: Initialize extraction layers
    ndf_agg = create_ndf_aggregator()
    comp_stats = create_comprehensive_stats(config["name"])
    
    logger.info(f"Processing {config['display_name']}...")
    
    # Emotion aggregation from pre-computed scores
    emotion_totals = {
        "anger": 0.0, "disgust": 0.0, "fear": 0.0, "joy": 0.0,
        "neutral": 0.0, "sadness": 0.0, "surprise": 0.0
    }
    emotion_counts = 0
    
    # Genre-based psychographic signals
    genre_profiles = defaultdict(lambda: {"count": 0, "emotions": defaultdict(float)})
    
    # Process music profiles (PRIMARY DATA SOURCE - has actual text content)
    music_file = path / "musics_profiles_anonymized.csv"
    if music_file.exists():
        try:
            logger.info(f"  Processing music profiles with lyrics and emotions...")
            with open(music_file, 'r', encoding='utf-8', errors='ignore') as f:
                reader = csv.DictReader(f)
                
                for row in reader:
                    # Get lyric text for psychological extraction
                    text = row.get("lyric", "")
                    disorder = row.get("disorder", "control")
                    
                    # Aggregate pre-computed emotion scores
                    try:
                        for emotion in emotion_totals.keys():
                            score_key = f"emotion_{emotion}_score"
                            score = float(row.get(score_key, 0) or 0)
                            emotion_totals[emotion] += score
                        emotion_counts += 1
                    except (ValueError, TypeError):
                        pass
                    
                    # Track genre-based psychographic profiles
                    genres = row.get("genres", "")
                    if genres:
                        for genre in genres.split(","):
                            genre = genre.strip().lower()
                            if genre:
                                genre_profiles[genre]["count"] += 1
                                for emotion in emotion_totals.keys():
                                    score_key = f"emotion_{emotion}_score"
                                    try:
                                        score = float(row.get(score_key, 0) or 0)
                                        genre_profiles[genre]["emotions"][emotion] += score
                                    except (ValueError, TypeError):
                                        pass
                    
                    # Extract psychological signals from lyrics if available
                    if text and len(text) > 50:
                        constructs = extract_constructs(text)
                        archetypes = detect_archetypes(text)
                        mechanisms = detect_mechanisms(text)
                        
                        # NEW: NDF + archetype + 430+ dimensions
                        extract_new_intelligence(text, 0.5, ndf_agg, comp_stats)
                        
                        for k, v in constructs.items():
                            result.construct_totals[k] = result.construct_totals.get(k, 0) + v
                            result.construct_counts[k] = result.construct_counts.get(k, 0) + 1
                        
                        for k, v in archetypes.items():
                            result.archetype_totals[k] = result.archetype_totals.get(k, 0) + v
                        
                        for k, v in mechanisms.items():
                            result.mechanism_totals[k] = result.mechanism_totals.get(k, 0) + v
                        
                        # Extract patterns (ETHICAL SAFEGUARD: only from control group)
                        if disorder == "control" and len(text) > 100:
                            patterns = extract_persuasive_patterns(text)
                            if patterns:
                                result.templates.extend(patterns)
                                result.templates_extracted += len(patterns)
                                result.high_quality_reviews += 1
                        
                        result.reviews_processed += 1
                    
                    if result.reviews_processed % 100000 == 0 and result.reviews_processed > 0:
                        logger.info(f"  {config['display_name']}: {result.reviews_processed:,} lyrics processed")
        
        except Exception as e:
            logger.error(f"Error processing music profiles: {e}")
            import traceback
            traceback.print_exc()
    else:
        logger.warning(f"  Music profiles file not found: {music_file}")
    
    # Also process tweet metadata for engagement signals (no text, just counts)
    tweets_file = path / "tweet_profiles_anonymized.csv"
    engagement_signals = {"total_likes": 0, "total_retweets": 0, "total_replies": 0, "tweet_count": 0}
    if tweets_file.exists():
        try:
            logger.info(f"  Processing tweet engagement metadata...")
            with open(tweets_file, 'r', encoding='utf-8', errors='ignore') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    try:
                        engagement_signals["total_likes"] += int(row.get("like_count", 0) or 0)
                        engagement_signals["total_retweets"] += int(row.get("retweet_count", 0) or 0)
                        engagement_signals["total_replies"] += int(row.get("reply_count", 0) or 0)
                        engagement_signals["tweet_count"] += 1
                    except (ValueError, TypeError):
                        pass
        except Exception as e:
            logger.debug(f"Could not process tweet metadata: {e}")
    
    # Calculate average emotion scores
    avg_emotions = {}
    if emotion_counts > 0:
        avg_emotions = {k: v / emotion_counts for k, v in emotion_totals.items()}
    
    # Calculate genre emotion profiles
    genre_emotion_profiles = {}
    for genre, data in genre_profiles.items():
        if data["count"] > 10:  # Only include genres with sufficient data
            genre_emotion_profiles[genre] = {
                "count": data["count"],
                "avg_emotions": {k: v / data["count"] for k, v in data["emotions"].items()}
            }
    
    # Store specific intelligence
    result.specific_intelligence["emotional_state_signals"] = True
    result.specific_intelligence["avg_emotion_profile"] = avg_emotions
    result.specific_intelligence["genre_emotion_profiles"] = dict(list(genre_emotion_profiles.items())[:50])  # Top 50
    result.specific_intelligence["engagement_signals"] = engagement_signals
    result.specific_intelligence["ethical_safeguard"] = "STRICT: No targeting based on mental health status - only control group patterns used"
    result.specific_intelligence["data_source"] = "musics_profiles_anonymized.csv (lyrics + pre-computed emotions)"
    
    # NEW: Finalize extraction data
    _finalize_new_extraction(result, ndf_agg, comp_stats)
    
    result.duration_seconds = time.time() - start_time
    
    logger.info(f"  {config['display_name']} COMPLETE: {result.reviews_processed:,} lyrics in {result.duration_seconds:.1f}s")
    logger.info(f"    Emotion samples: {emotion_counts:,}, Genre profiles: {len(genre_emotion_profiles)}")
    
    return result


# =============================================================================
# GOOGLE: Category-to-Advertising-Vertical Mapping (Layer 6)
# =============================================================================

CATEGORY_TO_VERTICAL = {
    # AUTO vertical
    "Auto repair shop": "auto", "Car dealer": "auto", "Used car dealer": "auto",
    "Auto body shop": "auto", "Auto parts store": "auto", "Car wash": "auto",
    "Tire shop": "auto", "Car rental agency": "auto", "Oil change service": "auto",
    "Truck dealer": "auto", "Motorcycle dealer": "auto", "Auto glass shop": "auto",
    "Transmission shop": "auto", "Auto detailing service": "auto",
    "Auto electrical service": "auto", "Brake shop": "auto", "Muffler shop": "auto",
    "Towing service": "auto", "Auto insurance agency": "auto",
    # DINING vertical
    "Restaurant": "dining", "Pizza restaurant": "dining", "Deli": "dining",
    "Bakery": "dining", "Cafe": "dining", "Bar": "dining", "Coffee shop": "dining",
    "Fast food restaurant": "dining", "Chinese restaurant": "dining",
    "Mexican restaurant": "dining", "Italian restaurant": "dining",
    "Thai restaurant": "dining", "Japanese restaurant": "dining",
    "Indian restaurant": "dining", "Sushi restaurant": "dining",
    "Vietnamese restaurant": "dining", "Korean restaurant": "dining",
    "Seafood restaurant": "dining", "Steak house": "dining",
    "Hamburger restaurant": "dining", "Sandwich shop": "dining",
    "Ice cream shop": "dining", "Donut shop": "dining", "Juice bar": "dining",
    "Bubble tea store": "dining", "Breakfast restaurant": "dining",
    "Buffet restaurant": "dining", "BBQ restaurant": "dining",
    "Brunch restaurant": "dining", "Food truck": "dining",
    "American restaurant": "dining", "French restaurant": "dining",
    "Mediterranean restaurant": "dining", "Greek restaurant": "dining",
    "African restaurant": "dining", "Caribbean restaurant": "dining",
    "Gastropub": "dining", "Ramen restaurant": "dining",
    # GROCERY / FOOD RETAIL
    "Grocery store": "grocery", "Supermarket": "grocery",
    "Convenience store": "grocery", "Liquor store": "grocery",
    "Health food store": "grocery", "Organic food store": "grocery",
    "Butcher shop": "grocery", "Farmers market": "grocery",
    # HEALTH / MEDICAL vertical
    "Doctor": "health", "Dentist": "health", "Pharmacy": "health",
    "Hospital": "health", "Veterinarian": "health", "Chiropractor": "health",
    "Physical therapist": "health", "Optometrist": "health",
    "Urgent care center": "health", "Medical clinic": "health",
    "Dermatologist": "health", "Pediatrician": "health",
    "Orthopedic surgeon": "health", "Psychologist": "health",
    "Psychiatrist": "health", "Counselor": "health",
    "Acupuncture clinic": "health", "Allergist": "health",
    # BEAUTY / PERSONAL CARE vertical
    "Beauty salon": "beauty", "Hair salon": "beauty", "Nail salon": "beauty",
    "Barber shop": "beauty", "Spa": "beauty", "Massage therapist": "beauty",
    "Waxing hair removal service": "beauty", "Tanning salon": "beauty",
    "Tattoo shop": "beauty", "Eyebrow bar": "beauty", "Skin care clinic": "beauty",
    "Laser hair removal service": "beauty", "Day spa": "beauty",
    # FINANCE vertical
    "Bank": "finance", "Insurance agency": "finance",
    "Financial planner": "finance", "Accounting firm": "finance",
    "Tax preparation service": "finance", "Credit union": "finance",
    "Mortgage broker": "finance", "Loan agency": "finance",
    "Investment company": "finance",
    # PROFESSIONAL SERVICES vertical
    "Attorney": "professional", "Real estate agency": "professional",
    "Contractor": "professional", "Plumber": "professional",
    "Electrician": "professional", "Roofing contractor": "professional",
    "HVAC contractor": "professional", "Painter": "professional",
    "Landscaper": "professional", "Tree service": "professional",
    "Pest control service": "professional", "Cleaning service": "professional",
    "Moving company": "professional", "Locksmith": "professional",
    "Notary public": "professional", "Printing service": "professional",
    # RETAIL vertical
    "Clothing store": "retail", "Gift shop": "retail", "Jewelry store": "retail",
    "Furniture store": "retail", "Hardware store": "retail",
    "Pet store": "retail", "Cell phone store": "retail",
    "Electronics store": "retail", "Shoe store": "retail",
    "Sporting goods store": "retail", "Book store": "retail",
    "Toy store": "retail", "Thrift store": "retail",
    "Department store": "retail", "Shopping mall": "retail",
    "Florist": "retail", "Bicycle shop": "retail",
    "Musical instrument store": "retail", "Home improvement store": "retail",
    "Discount store": "retail", "Dollar store": "retail",
    # FITNESS vertical
    "Gym": "fitness", "Yoga studio": "fitness", "Fitness center": "fitness",
    "Personal trainer": "fitness", "Martial arts school": "fitness",
    "Pilates studio": "fitness", "CrossFit gym": "fitness",
    "Dance school": "fitness", "Swimming pool": "fitness",
    # EDUCATION vertical
    "School": "education", "University": "education",
    "Tutoring service": "education", "Driving school": "education",
    "Music school": "education", "Preschool": "education",
    "Language school": "education", "Library": "education",
    "Community college": "education",
    # ENTERTAINMENT vertical
    "Movie theater": "entertainment", "Night club": "entertainment",
    "Amusement park": "entertainment", "Museum": "entertainment",
    "Bowling alley": "entertainment", "Arcade": "entertainment",
    "Concert hall": "entertainment", "Golf course": "entertainment",
    "Zoo": "entertainment", "Aquarium": "entertainment",
    "Escape room center": "entertainment",
    # TRAVEL / LODGING vertical
    "Hotel": "travel", "Motel": "travel", "Resort hotel": "travel",
    "Bed and breakfast": "travel", "Hostel": "travel",
    "Travel agency": "travel", "Airport": "travel",
    "Campground": "travel", "RV park": "travel",
    # HOME SERVICES vertical
    "Laundromat": "home_services", "Storage facility": "home_services",
    "Dry cleaner": "home_services", "Tailor": "home_services",
    "Carpet cleaning service": "home_services",
    # RELIGIOUS / COMMUNITY
    "Church": "community", "Mosque": "community", "Synagogue": "community",
    "Non-profit organization": "community", "Community center": "community",
    # GOVERNMENT / CIVIC
    "Post office": "government", "City hall": "government",
    "Fire station": "government", "Police department": "government",
    "DMV": "government", "Court house": "government",
}

# Top 50 categories for per-category NDF profiles
TOP_GOOGLE_CATEGORIES = [
    "Restaurant", "Beauty salon", "Auto repair shop", "Hair salon",
    "Nail salon", "Doctor", "Convenience store", "Dentist",
    "Gas station", "Barber shop", "Church", "Grocery store",
    "Bar", "Attorney", "Pharmacy", "Cell phone store",
    "Insurance agency", "Bank", "Clothing store", "Fast food restaurant",
    "Coffee shop", "Pizza restaurant", "Hotel", "Gym",
    "Car dealer", "Bakery", "Deli", "Real estate agency",
    "Laundromat", "Gift shop", "Cafe", "Park",
    "Veterinarian", "Chiropractor", "Pet store", "Plumber",
    "Furniture store", "Massage therapist", "Contractor", "Auto body shop",
    "Jewelry store", "Chinese restaurant", "Mexican restaurant",
    "Electrician", "Storage facility", "Thrift store",
    "Hardware store", "Liquor store", "School", "Spa",
]


def _load_meta_index(meta_file: Path) -> Dict[str, Dict]:
    """Load meta file into gmap_id -> {category, price} lookup dict.
    
    Only keeps fields needed for enrichment to minimize memory.
    """
    index = {}
    try:
        with open(meta_file, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    d = json.loads(line)
                    gmap_id = d.get("gmap_id", "")
                    if not gmap_id:
                        continue
                    cats = d.get("category") or []
                    price = d.get("price") or ""
                    # Store only what we need
                    index[gmap_id] = {
                        "cats": cats,
                        "price": price,
                    }
                except (json.JSONDecodeError, Exception):
                    continue
    except Exception as e:
        logger.warning(f"Could not load meta index from {meta_file}: {e}")
    return index


def process_google_local(config: Dict) -> DatasetResult:
    """
    Process Google Local dataset - 50+ states, hyperlocal targeting.
    
    STRATEGIC EXTRACTION LAYERS:
    1. Standard: NDF + 430+ dimensions on all reviews
    2. Category-conditioned NDF profiles (top 50 categories)
    3. Geographic NDF profiles (per state)
    4. Price-tier NDF profiles ($, $$, $$$, $$$$)
    5. Business response intelligence (NDF + mechanisms on owner responses)
    6. Advertising-vertical aggregation
    """
    result = DatasetResult(name=config["name"], display_name=config["display_name"])
    start_time = time.time()
    
    path = Path(config["path"])
    
    # Layer 1: Global NDF + 430+ dimensions
    ndf_agg = create_ndf_aggregator()
    comp_stats = create_comprehensive_stats(config["name"])
    
    # Layer 2: Per-category NDF aggregators
    category_ndf_aggs = {}
    for cat in TOP_GOOGLE_CATEGORIES:
        agg = create_ndf_aggregator()
        if agg is not None:
            category_ndf_aggs[cat] = agg
    
    # Layer 3: Per-state NDF aggregators
    state_ndf_aggs = {}  # Created on-the-fly per state
    
    # Layer 4: Per-price-tier NDF aggregators
    price_tiers = ["$", "$$", "$$$", "$$$$"]
    price_ndf_aggs = {}
    for tier in price_tiers:
        agg = create_ndf_aggregator()
        if agg is not None:
            price_ndf_aggs[tier] = agg
    
    # Layer 5: Business response intelligence
    response_ndf_agg = create_ndf_aggregator()  # Global response NDF
    response_mechanism_by_category = defaultdict(lambda: defaultdict(float))
    response_count_by_category = defaultdict(int)
    response_rating_by_category = defaultdict(lambda: defaultdict(int))  # cat -> {rating -> count}
    total_responses_processed = 0
    
    # Layer 6: Per-vertical NDF aggregators
    vertical_ndf_aggs = {}
    for vert in set(CATEGORY_TO_VERTICAL.values()):
        agg = create_ndf_aggregator()
        if agg is not None:
            vertical_ndf_aggs[vert] = agg
    
    # Legacy location profiles (kept for backward compat)
    location_profiles = defaultdict(lambda: {
        "review_count": 0,
        "construct_totals": {},
        "archetype_totals": {},
    })
    
    logger.info(f"Processing {config['display_name']} (STRATEGIC HYPERLOCAL EXTRACTION)...")
    logger.info(f"  Layers: NDF+430, {len(category_ndf_aggs)} categories, per-state NDF, "
                f"{len(price_ndf_aggs)} price tiers, response intel, {len(vertical_ndf_aggs)} verticals")
    
    # Get all state files
    state_files = sorted(path.glob("review-*.json"))
    meta_files = {f.stem.replace("meta-", ""): f for f in path.glob("meta-*.json")}
    
    logger.info(f"  Found {len(state_files)} state review files, {len(meta_files)} meta files")
    
    for state_file in state_files:
        state_name = state_file.stem.replace("review-", "")
        logger.info(f"  Processing {state_name}...")
        
        # Layer 3: Create per-state NDF aggregator
        state_ndf = create_ndf_aggregator()
        if state_ndf is not None:
            state_ndf_aggs[state_name] = state_ndf
        
        # Pre-load meta index for this state (Layer 1-6 enrichment)
        meta_file = meta_files.get(state_name)
        meta_index = {}
        if meta_file:
            meta_index = _load_meta_index(meta_file)
            logger.info(f"    Loaded {len(meta_index):,} business profiles for {state_name}")
        else:
            logger.warning(f"    No meta file for {state_name}")
        
        state_reviews = 0
        
        try:
            with open(state_file, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        review = json.loads(line)
                        text = review.get("text") or ""
                        if not text or len(text) < 20:
                            continue
                        
                        rating = review.get("rating", 0) / 5.0
                        gmap_id = review.get("gmap_id", "")
                        
                        # --- Look up business metadata ---
                        biz = meta_index.get(gmap_id, {})
                        biz_cats = biz.get("cats", [])
                        biz_price = biz.get("price", "")
                        primary_cat = biz_cats[0] if biz_cats else ""
                        
                        # Determine advertising vertical
                        vertical = ""
                        for cat in biz_cats:
                            vertical = CATEGORY_TO_VERTICAL.get(cat, "")
                            if vertical:
                                break
                        
                        # --- Legacy extraction ---
                        constructs = extract_constructs(text)
                        archetypes = detect_archetypes(text)
                        mechanisms = detect_mechanisms(text)
                        
                        # --- Layer 1: Global NDF + 430+ ---
                        ndf_val = None
                        archetype_val = "unknown"
                        if _ndf_extract_fn is not None and len(text) > 30:
                            try:
                                ndf_val = _ndf_extract_fn(text, rating=rating * 5.0)
                                archetype_val = detect_archetype_new(text)
                                if ndf_agg is not None:
                                    ndf_agg.add(ndf_val, archetype=archetype_val)
                            except Exception:
                                ndf_val = None
                        
                        # 430+ dimensions
                        if comp_stats is not None and _comprehensive_extract_fn is not None and len(text) > 50:
                            try:
                                profile = _comprehensive_extract_fn(text, rating * 5.0)
                                if profile:
                                    comp_stats.add_profile(profile, rating * 5.0)
                            except Exception:
                                pass
                        
                        # --- Layer 2: Category-conditioned NDF ---
                        if ndf_val is not None and primary_cat in category_ndf_aggs:
                            category_ndf_aggs[primary_cat].add(ndf_val, archetype=archetype_val)
                        
                        # --- Layer 3: State NDF ---
                        if ndf_val is not None and state_ndf is not None:
                            state_ndf.add(ndf_val, archetype=archetype_val)
                        
                        # --- Layer 4: Price-tier NDF ---
                        if ndf_val is not None and biz_price in price_ndf_aggs:
                            price_ndf_aggs[biz_price].add(ndf_val, archetype=archetype_val)
                        
                        # --- Layer 5: Business response intelligence ---
                        resp = review.get("resp")
                        if resp and isinstance(resp, dict):
                            resp_text = resp.get("text") or ""
                            if len(resp_text) > 30:
                                resp_rating = review.get("rating", 3)
                                resp_cat = primary_cat or "unknown"
                                
                                # NDF on response text
                                if _ndf_extract_fn is not None and response_ndf_agg is not None:
                                    try:
                                        resp_ndf = _ndf_extract_fn(resp_text, rating=3.0)
                                        response_ndf_agg.add(resp_ndf)
                                    except Exception:
                                        pass
                                
                                # Mechanism detection on response
                                resp_mechs = detect_mechanisms(resp_text)
                                for mech, score in resp_mechs.items():
                                    response_mechanism_by_category[resp_cat][mech] += score
                                response_count_by_category[resp_cat] += 1
                                response_rating_by_category[resp_cat][resp_rating] += 1
                                total_responses_processed += 1
                        
                        # --- Layer 6: Vertical NDF ---
                        if ndf_val is not None and vertical and vertical in vertical_ndf_aggs:
                            vertical_ndf_aggs[vertical].add(ndf_val, archetype=archetype_val)
                        
                        # --- Legacy aggregation ---
                        location = location_profiles[state_name]
                        location["review_count"] += 1
                        
                        for k, v in constructs.items():
                            result.construct_totals[k] = result.construct_totals.get(k, 0) + v
                            result.construct_counts[k] = result.construct_counts.get(k, 0) + 1
                            location["construct_totals"][k] = location["construct_totals"].get(k, 0) + v
                        
                        for k, v in archetypes.items():
                            result.archetype_totals[k] = result.archetype_totals.get(k, 0) + v
                            location["archetype_totals"][k] = location["archetype_totals"].get(k, 0) + v
                        
                        for k, v in mechanisms.items():
                            result.mechanism_totals[k] = result.mechanism_totals.get(k, 0) + v
                        
                        # Templates from high-quality reviews
                        if len(text) > 100 and rating >= 0.8:
                            patterns = extract_persuasive_patterns(text, rating)
                            if patterns:
                                for p in patterns[:2]:
                                    p["state"] = state_name
                                    p["gmap_id"] = gmap_id
                                    p["category"] = primary_cat
                                    p["vertical"] = vertical
                                result.templates.extend(patterns[:2])
                                result.templates_extracted += len(patterns[:2])
                                result.high_quality_reviews += 1
                        
                        result.reviews_processed += 1
                        state_reviews += 1
                        
                        if result.reviews_processed % 500000 == 0:
                            logger.info(f"    Total: {result.reviews_processed:,} reviews | "
                                        f"Responses: {total_responses_processed:,}")
                    
                    except json.JSONDecodeError:
                        continue
                    except Exception:
                        continue
        
        except Exception as e:
            logger.error(f"Error processing {state_name}: {e}")
        
        # Free meta index memory after each state
        del meta_index
        
        # Checkpoint after each state
        checkpoint_data = {
            "state": state_name,
            "reviews": state_reviews,
            "total_so_far": result.reviews_processed,
            "responses_so_far": total_responses_processed,
        }
        if state_ndf is not None:
            checkpoint_data["state_ndf_count"] = state_ndf._count if hasattr(state_ndf, '_count') else 0
        checkpoint_file = OUTPUT_DIR / f"google_checkpoint_{state_name}.json"
        with open(checkpoint_file, 'w') as f:
            json.dump(checkpoint_data, f)
        
        logger.info(f"    {state_name} complete: {state_reviews:,} reviews")
    
    # =========================================================================
    # FINALIZE ALL LAYERS
    # =========================================================================
    
    # Layer 1: Global NDF + 430+
    _finalize_new_extraction(result, ndf_agg, comp_stats)
    
    # Layer 2: Category-conditioned NDF profiles
    category_ndf_profiles = {}
    for cat, agg in category_ndf_aggs.items():
        if hasattr(agg, '_count') and agg._count > 100:
            category_ndf_profiles[cat] = agg.to_dict()
    result.specific_intelligence["category_ndf_profiles"] = category_ndf_profiles
    logger.info(f"  Category NDF profiles: {len(category_ndf_profiles)} categories with data")
    
    # Layer 3: State NDF profiles
    state_ndf_profiles = {}
    for state, agg in state_ndf_aggs.items():
        if hasattr(agg, '_count') and agg._count > 100:
            state_ndf_profiles[state] = agg.to_dict()
    result.specific_intelligence["state_ndf_profiles"] = state_ndf_profiles
    logger.info(f"  State NDF profiles: {len(state_ndf_profiles)} states with data")
    
    # Layer 4: Price-tier NDF profiles
    price_ndf_profiles = {}
    for tier, agg in price_ndf_aggs.items():
        if hasattr(agg, '_count') and agg._count > 50:
            price_ndf_profiles[tier] = agg.to_dict()
    result.specific_intelligence["price_tier_ndf_profiles"] = price_ndf_profiles
    logger.info(f"  Price tier profiles: {len(price_ndf_profiles)} tiers with data")
    
    # Layer 5: Business response intelligence
    resp_intel = {
        "total_responses": total_responses_processed,
        "response_ndf": response_ndf_agg.to_dict() if response_ndf_agg and hasattr(response_ndf_agg, '_count') and response_ndf_agg._count > 0 else {},
        "mechanism_by_category": {},
        "rating_distribution_by_category": {},
    }
    for cat in response_count_by_category:
        cnt = response_count_by_category[cat]
        if cnt > 10:
            resp_intel["mechanism_by_category"][cat] = {
                mech: round(score / cnt, 4)
                for mech, score in response_mechanism_by_category[cat].items()
            }
            resp_intel["rating_distribution_by_category"][cat] = dict(response_rating_by_category[cat])
    result.specific_intelligence["business_response_intelligence"] = resp_intel
    logger.info(f"  Response intelligence: {total_responses_processed:,} responses across "
                f"{len(resp_intel['mechanism_by_category'])} categories")
    
    # Layer 6: Vertical NDF profiles
    vertical_profiles = {}
    for vert, agg in vertical_ndf_aggs.items():
        if hasattr(agg, '_count') and agg._count > 100:
            vertical_profiles[vert] = agg.to_dict()
    result.specific_intelligence["vertical_ndf_profiles"] = vertical_profiles
    logger.info(f"  Vertical profiles: {len(vertical_profiles)} ad verticals with data")
    
    # Legacy location profiles (backward compat)
    result.specific_intelligence["hyperlocal_targeting"] = True
    result.specific_intelligence["states_processed"] = len(location_profiles)
    result.specific_intelligence["location_profiles"] = {
        state: {
            "review_count": profile["review_count"],
            "top_construct": max(profile["construct_totals"].items(), key=lambda x: x[1])[0] if profile["construct_totals"] else None,
            "top_archetype": max(profile["archetype_totals"].items(), key=lambda x: x[1])[0] if profile["archetype_totals"] else None,
        }
        for state, profile in location_profiles.items()
    }
    
    result.duration_seconds = time.time() - start_time
    result.templates.sort(key=lambda x: len(x.get("mechanisms", [])), reverse=True)
    
    logger.info(f"  {config['display_name']} COMPLETE: {result.reviews_processed:,} reviews "
                f"in {result.duration_seconds/3600:.2f} hours")
    
    return result


# =============================================================================
# NEW DATASET PROCESSORS: Reddit MBTI, Glassdoor, Rent the Runway
# =============================================================================

def process_reddit_mbti(config: Dict) -> DatasetResult:
    """
    Process Reddit MBTI dataset -- personality ground truth calibration.
    
    13M posts from 11,774 users with self-identified MBTI types.
    Strategic value: MBTI-conditioned NDF profiles validate our NDF
    against established personality science.
    """
    result = DatasetResult(name=config["name"], display_name=config["display_name"])
    start_time = time.time()
    
    path = Path(config["path"])
    
    # Global NDF + 430+
    ndf_agg = create_ndf_aggregator()
    comp_stats = create_comprehensive_stats(config["name"])
    
    # MBTI-unique: per-type NDF aggregators (16 types)
    MBTI_TYPES = [
        "INTJ", "INTP", "ENTJ", "ENTP",
        "INFJ", "INFP", "ENFJ", "ENFP",
        "ISTJ", "ISFJ", "ESTJ", "ESFJ",
        "ISTP", "ISFP", "ESTP", "ESFP",
    ]
    mbti_ndf_aggs = {}
    for mbti in MBTI_TYPES:
        agg = create_ndf_aggregator()
        if agg is not None:
            mbti_ndf_aggs[mbti] = agg
    
    # Archetype-MBTI alignment tracking
    archetype_mbti_counts = defaultdict(lambda: defaultdict(int))
    
    # Load author -> MBTI mapping
    author_file = path / "unique_author.csv"
    author_mbti = {}
    if author_file.exists():
        with open(author_file, 'r', encoding='utf-8', errors='ignore') as f:
            reader = csv.DictReader(f)
            for row in reader:
                author = row.get("author", "")
                mbti = (row.get("mbti", "") or "").upper().strip()
                if author and mbti in MBTI_TYPES:
                    author_mbti[author] = mbti
        logger.info(f"  Loaded {len(author_mbti):,} author-MBTI mappings")
    
    logger.info(f"Processing {config['display_name']}...")
    
    post_file = path / "reddit_post.csv"
    if post_file.exists():
        try:
            with open(post_file, 'r', encoding='utf-8', errors='ignore') as f:
                reader = csv.DictReader(f)
                
                for row in reader:
                    text = row.get("body", "")
                    if not text or len(text) < 30:
                        continue
                    
                    author = row.get("author", "")
                    mbti = (row.get("mbti", "") or "").upper().strip()
                    if not mbti or mbti not in MBTI_TYPES:
                        mbti = author_mbti.get(author, "")
                    
                    # Legacy extraction
                    constructs = extract_constructs(text)
                    archetypes = detect_archetypes(text)
                    mechanisms = detect_mechanisms(text)
                    
                    for k, v in constructs.items():
                        result.construct_totals[k] = result.construct_totals.get(k, 0) + v
                        result.construct_counts[k] = result.construct_counts.get(k, 0) + 1
                    for k, v in archetypes.items():
                        result.archetype_totals[k] = result.archetype_totals.get(k, 0) + v
                    for k, v in mechanisms.items():
                        result.mechanism_totals[k] = result.mechanism_totals.get(k, 0) + v
                    
                    # NDF extraction
                    ndf_val = None
                    archetype_val = "unknown"
                    if _ndf_extract_fn is not None and len(text) > 50:
                        try:
                            ndf_val = _ndf_extract_fn(text, rating=0.0)
                            archetype_val = detect_archetype_new(text)
                            if ndf_agg is not None:
                                ndf_agg.add(ndf_val, archetype=archetype_val)
                        except Exception:
                            ndf_val = None
                    
                    # 430+ dimensions
                    if comp_stats is not None and _comprehensive_extract_fn is not None and len(text) > 50:
                        try:
                            profile = _comprehensive_extract_fn(text, 0.0)
                            if profile:
                                comp_stats.add_profile(profile, 0.0)
                        except Exception:
                            pass
                    
                    # MBTI-conditioned NDF
                    if ndf_val is not None and mbti and mbti in mbti_ndf_aggs:
                        mbti_ndf_aggs[mbti].add(ndf_val, archetype=archetype_val)
                    
                    # Archetype-MBTI alignment
                    if archetype_val != "unknown" and mbti:
                        archetype_mbti_counts[archetype_val][mbti] += 1
                    
                    result.reviews_processed += 1
                    
                    if result.reviews_processed % 500000 == 0:
                        logger.info(f"  {config['display_name']}: {result.reviews_processed:,} posts")
        
        except Exception as e:
            logger.error(f"Error processing Reddit MBTI: {e}")
            import traceback
            traceback.print_exc()
    
    # Finalize
    _finalize_new_extraction(result, ndf_agg, comp_stats)
    
    # MBTI-conditioned NDF profiles
    mbti_ndf_profiles = {}
    for mbti, agg in mbti_ndf_aggs.items():
        if hasattr(agg, '_count') and agg._count > 50:
            mbti_ndf_profiles[mbti] = agg.to_dict()
    result.specific_intelligence["mbti_ndf_profiles"] = mbti_ndf_profiles
    logger.info(f"  MBTI NDF profiles: {len(mbti_ndf_profiles)} types with data")
    
    # Archetype-MBTI alignment
    result.specific_intelligence["archetype_mbti_distribution"] = {
        arch: dict(mbti_dist)
        for arch, mbti_dist in archetype_mbti_counts.items()
        if sum(mbti_dist.values()) > 20
    }
    result.specific_intelligence["personality_ground_truth"] = True
    result.specific_intelligence["total_authors"] = len(author_mbti)
    
    result.duration_seconds = time.time() - start_time
    logger.info(f"  {config['display_name']} COMPLETE: {result.reviews_processed:,} posts "
                f"in {result.duration_seconds:.1f}s")
    
    return result


def process_glassdoor(config: Dict) -> DatasetResult:
    """
    Process Glassdoor reviews -- professional values and B2B psychology.
    
    1.5M reviews with separate pros/cons. Strategic value: dual-valence
    NDF extraction reveals how language shifts between positive and
    negative framing -- directly informing regulatory focus targeting.
    """
    result = DatasetResult(name=config["name"], display_name=config["display_name"])
    start_time = time.time()
    
    path = config["path"]
    
    # Global NDF + 430+ (on concatenated text)
    ndf_agg = create_ndf_aggregator()
    comp_stats = create_comprehensive_stats(config["name"])
    
    # Dual-valence: separate NDF for pros vs cons
    pro_ndf_agg = create_ndf_aggregator()
    con_ndf_agg = create_ndf_aggregator()
    
    logger.info(f"Processing {config['display_name']}...")
    
    try:
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                pros = row.get("pros", "") or ""
                cons = row.get("cons", "") or ""
                headline = row.get("headline", "") or ""
                
                # Concatenated text for standard extraction
                text = f"{headline} {pros} {cons}".strip()
                if not text or len(text) < 30:
                    continue
                
                try:
                    rating = float(row.get("overall_rating", 0)) / 5.0
                except (ValueError, TypeError):
                    rating = 0.5
                
                # Legacy extraction
                constructs = extract_constructs(text)
                archetypes = detect_archetypes(text)
                mechanisms = detect_mechanisms(text)
                
                for k, v in constructs.items():
                    result.construct_totals[k] = result.construct_totals.get(k, 0) + v
                    result.construct_counts[k] = result.construct_counts.get(k, 0) + 1
                for k, v in archetypes.items():
                    result.archetype_totals[k] = result.archetype_totals.get(k, 0) + v
                for k, v in mechanisms.items():
                    result.mechanism_totals[k] = result.mechanism_totals.get(k, 0) + v
                
                # Global NDF + 430+
                extract_new_intelligence(text, rating, ndf_agg, comp_stats)
                
                # Dual-valence NDF: pros (promotion frame)
                if pro_ndf_agg is not None and _ndf_extract_fn is not None and len(pros) > 30:
                    try:
                        pro_ndf = _ndf_extract_fn(pros, rating=rating * 5.0)
                        pro_ndf_agg.add(pro_ndf)
                    except Exception:
                        pass
                
                # Dual-valence NDF: cons (prevention frame)
                if con_ndf_agg is not None and _ndf_extract_fn is not None and len(cons) > 30:
                    try:
                        con_ndf = _ndf_extract_fn(cons, rating=rating * 5.0)
                        con_ndf_agg.add(con_ndf)
                    except Exception:
                        pass
                
                result.reviews_processed += 1
                
                if result.reviews_processed % 200000 == 0:
                    logger.info(f"  {config['display_name']}: {result.reviews_processed:,} reviews")
    
    except Exception as e:
        logger.error(f"Error processing Glassdoor: {e}")
        import traceback
        traceback.print_exc()
    
    # Finalize
    _finalize_new_extraction(result, ndf_agg, comp_stats)
    
    # Dual-valence NDF profiles
    pro_data = pro_ndf_agg.to_dict() if pro_ndf_agg and hasattr(pro_ndf_agg, '_count') and pro_ndf_agg._count > 0 else {}
    con_data = con_ndf_agg.to_dict() if con_ndf_agg and hasattr(con_ndf_agg, '_count') and con_ndf_agg._count > 0 else {}
    
    # Compute valence delta (how NDF shifts from positive to negative framing)
    ndf_valence_delta = {}
    if pro_data and con_data:
        pro_means = pro_data.get("ndf_means", {})
        con_means = con_data.get("ndf_means", {})
        for dim in pro_means:
            if dim in con_means:
                ndf_valence_delta[dim] = round(pro_means[dim] - con_means[dim], 4)
    
    result.specific_intelligence["pro_ndf_profile"] = pro_data
    result.specific_intelligence["con_ndf_profile"] = con_data
    result.specific_intelligence["ndf_valence_delta"] = ndf_valence_delta
    result.specific_intelligence["dual_valence_extraction"] = True
    result.specific_intelligence["professional_psychology"] = True
    
    if ndf_valence_delta:
        logger.info(f"  Valence delta (pro - con): {ndf_valence_delta}")
    
    result.duration_seconds = time.time() - start_time
    logger.info(f"  {config['display_name']} COMPLETE: {result.reviews_processed:,} reviews "
                f"in {result.duration_seconds:.1f}s")
    
    return result


def process_rent_the_runway(config: Dict) -> DatasetResult:
    """
    Process Rent the Runway -- occasion-driven decision psychology.
    
    192K reviews with occasion context (wedding, party, work, etc.)
    and body attributes. Strategic value: occasion-conditioned NDF
    profiles inform situational targeting.
    """
    result = DatasetResult(name=config["name"], display_name=config["display_name"])
    start_time = time.time()
    
    path = config["path"]
    
    # Global NDF + 430+
    ndf_agg = create_ndf_aggregator()
    comp_stats = create_comprehensive_stats(config["name"])
    
    # Occasion-conditioned NDF aggregators
    OCCASIONS = ["wedding", "party", "work", "formal affair", "vacation",
                 "date", "everyday", "other"]
    occasion_ndf_aggs = {}
    for occ in OCCASIONS:
        agg = create_ndf_aggregator()
        if agg is not None:
            occasion_ndf_aggs[occ] = agg
    
    # Body-type NDF aggregation (aggregate only, no individual data stored)
    BODY_TYPES = ["hourglass", "straight & narrow", "pear", "athletic",
                  "petite", "full bust", "apple"]
    body_ndf_aggs = {}
    for bt in BODY_TYPES:
        agg = create_ndf_aggregator()
        if agg is not None:
            body_ndf_aggs[bt] = agg
    
    logger.info(f"Processing {config['display_name']}...")
    
    try:
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    review = json.loads(line)
                except (json.JSONDecodeError, Exception):
                    continue
                
                text = review.get("review_text", "") or ""
                if not text or len(text) < 30:
                    continue
                
                try:
                    rating = float(review.get("rating", 0)) / 10.0  # RTR uses 1-10 scale
                except (ValueError, TypeError):
                    rating = 0.5
                
                occasion = (review.get("rented for", "") or "").lower().strip()
                body_type = (review.get("body type", "") or "").lower().strip()
                
                # Legacy extraction
                constructs = extract_constructs(text)
                archetypes = detect_archetypes(text)
                mechanisms = detect_mechanisms(text)
                
                for k, v in constructs.items():
                    result.construct_totals[k] = result.construct_totals.get(k, 0) + v
                    result.construct_counts[k] = result.construct_counts.get(k, 0) + 1
                for k, v in archetypes.items():
                    result.archetype_totals[k] = result.archetype_totals.get(k, 0) + v
                for k, v in mechanisms.items():
                    result.mechanism_totals[k] = result.mechanism_totals.get(k, 0) + v
                
                # NDF extraction
                ndf_val = None
                archetype_val = "unknown"
                if _ndf_extract_fn is not None and len(text) > 50:
                    try:
                        ndf_val = _ndf_extract_fn(text, rating=rating * 5.0)
                        archetype_val = detect_archetype_new(text)
                        if ndf_agg is not None:
                            ndf_agg.add(ndf_val, archetype=archetype_val)
                    except Exception:
                        ndf_val = None
                
                # 430+ dimensions
                if comp_stats is not None and _comprehensive_extract_fn is not None and len(text) > 50:
                    try:
                        profile = _comprehensive_extract_fn(text, rating * 5.0)
                        if profile:
                            comp_stats.add_profile(profile, rating * 5.0)
                    except Exception:
                        pass
                
                # Occasion-conditioned NDF
                if ndf_val is not None and occasion in occasion_ndf_aggs:
                    occasion_ndf_aggs[occasion].add(ndf_val, archetype=archetype_val)
                
                # Body-type NDF (aggregate only -- no individual data)
                if ndf_val is not None and body_type in body_ndf_aggs:
                    body_ndf_aggs[body_type].add(ndf_val, archetype=archetype_val)
                
                # Templates
                if len(text) > 100 and rating >= 0.7:
                    patterns = extract_persuasive_patterns(text, rating)
                    if patterns:
                        for p in patterns:
                            p["occasion"] = occasion
                        result.templates.extend(patterns)
                        result.templates_extracted += len(patterns)
                        result.high_quality_reviews += 1
                
                result.reviews_processed += 1
                
                if result.reviews_processed % 50000 == 0:
                    logger.info(f"  {config['display_name']}: {result.reviews_processed:,} reviews")
    
    except Exception as e:
        logger.error(f"Error processing Rent the Runway: {e}")
        import traceback
        traceback.print_exc()
    
    # Finalize
    _finalize_new_extraction(result, ndf_agg, comp_stats)
    
    # Occasion-conditioned NDF profiles
    occasion_ndf_profiles = {}
    for occ, agg in occasion_ndf_aggs.items():
        if hasattr(agg, '_count') and agg._count > 20:
            occasion_ndf_profiles[occ] = agg.to_dict()
    result.specific_intelligence["occasion_ndf_profiles"] = occasion_ndf_profiles
    logger.info(f"  Occasion NDF profiles: {len(occasion_ndf_profiles)} occasions with data")
    
    # Body-confidence signals (aggregate only)
    body_signals = {}
    for bt, agg in body_ndf_aggs.items():
        if hasattr(agg, '_count') and agg._count > 20:
            body_signals[bt] = agg.to_dict()
    result.specific_intelligence["body_confidence_signals"] = body_signals
    result.specific_intelligence["occasion_driven_psychology"] = True
    result.specific_intelligence["fashion_rental_domain"] = True
    
    result.duration_seconds = time.time() - start_time
    result.templates.sort(key=lambda x: len(x.get("mechanisms", [])), reverse=True)
    
    logger.info(f"  {config['display_name']} COMPLETE: {result.reviews_processed:,} reviews "
                f"in {result.duration_seconds:.1f}s")
    
    return result


# =============================================================================
# TWCS: Brand-to-Industry Mapping (for industry-level persuasion aggregation)
# =============================================================================

TWCS_BRAND_INDUSTRY = {
    # E-COMMERCE / RETAIL
    "AmazonHelp": "ecommerce", "AskTarget": "retail",
    "Tesco": "grocery", "sainsburys": "grocery",
    # TECH
    "AppleSupport": "tech",
    # TRANSPORTATION / RIDE-SHARE
    "Uber_Support": "transportation",
    # STREAMING / ENTERTAINMENT
    "SpotifyCares": "streaming", "hulu_support": "streaming",
    # AIRLINES / TRAVEL
    "Delta": "travel", "AmericanAir": "travel", "SouthwestAir": "travel",
    "British_Airways": "travel", "VirginTrains": "travel",
    "GWRHelp": "travel", "AirAsiaSupport": "travel", "SW_Help": "travel",
    # TELECOM / ISP
    "TMobileHelp": "telecom", "comcastcares": "telecom",
    "Ask_Spectrum": "telecom", "sprintcare": "telecom",
    "VerizonSupport": "telecom", "O2": "telecom", "idea_cares": "telecom",
    "Safaricom_Care": "telecom",
    # GAMING
    "XboxSupport": "gaming", "AskPlayStation": "gaming", "ATVIAssist": "gaming",
    # DINING / QSR
    "ChipotleTweets": "dining",
    # LOGISTICS
    "UPSHelp": "logistics",
    # FINANCE
    "BofA_Help": "finance",
}


def process_twcs(config: Dict) -> DatasetResult:
    """
    Process Twitter Customer Service -- Service recovery persuasion intelligence.
    
    2.8M tweets across 108 brands. This is NOT treated as standard reviews.
    Instead, three unique extraction layers exploit what makes this data
    fundamentally different from the rest of our corpus:
    
    LAYER 1 - SERVICE RECOVERY PERSUASION FINGERPRINTS:
      NDF profiles of brand outbound responses grouped by brand and industry.
      Reveals how each brand crafts persuasive recovery language --
      e.g., Amazon leans on authority/process while Southwest uses empathy/liking.
      Directly informs brand-ad alignment for StackAdapt.
    
    LAYER 2 - ESCALATION/DE-ESCALATION DYNAMICS:
      Paired NDF analysis of customer→brand conversational flows. Identifies
      which persuasion mechanisms most effectively shift negative emotional
      states. Applicable to retargeting and negative-sentiment ad contexts.
    
    LAYER 3 - COMPLAINT-STATE NDF PROFILES:
      Customer inbound NDF under high emotional arousal -- a psychological
      state poorly represented in our 1B+ review corpus (which captures
      post-hoc reflection). Provides population-level baselines for
      nonconscious mechanisms during distress.
    """
    result = DatasetResult(name=config["name"], display_name=config["display_name"])
    start_time = time.time()
    
    path = config["path"]
    
    # Global NDF + 430+
    ndf_agg = create_ndf_aggregator()
    comp_stats = create_comprehensive_stats(config["name"])
    
    # ─── Layer 1: Brand-level & Industry-level NDF (outbound responses) ───
    brand_ndf_aggs = {}  # brand_id → NDFAggregator (created lazily)
    
    industry_ndf_aggs = {}  # industry → NDFAggregator
    for ind in set(TWCS_BRAND_INDUSTRY.values()):
        agg = create_ndf_aggregator()
        if agg is not None:
            industry_ndf_aggs[ind] = agg
    
    # Brand mechanism usage tracking (which mechanisms brands deploy most)
    brand_mechanism_usage = defaultdict(lambda: defaultdict(float))
    
    # ─── Layer 2: Paired escalation/de-escalation dynamics ───
    # Cache inbound NDF for paired lookup when brand responds
    inbound_ndf_cache = {}  # tweet_id → {ndf, archetype, mechanisms}
    MAX_CACHE_SIZE = 500000  # ~500K entries, ~200MB memory ceiling
    
    # Track which mechanisms brands introduce vs. what customers expressed
    deescalation_mechanism_scores = defaultdict(lambda: {"effective": 0, "total": 0})
    paired_analysis_count = 0
    
    # ─── Layer 3: Customer complaint-state NDF (inbound only) ───
    complaint_ndf_agg = create_ndf_aggregator()
    
    # Industry-level complaint NDF (grouped by which industry the customer is complaining about)
    industry_complaint_ndf_aggs = {}
    for ind in set(TWCS_BRAND_INDUSTRY.values()):
        agg = create_ndf_aggregator()
        if agg is not None:
            industry_complaint_ndf_aggs[ind] = agg
    
    # ─── Stats tracking ───
    inbound_processed = 0
    outbound_processed = 0
    too_short_skipped = 0
    
    logger.info(f"Processing {config['display_name']}...")
    logger.info(f"  Strategy: 3-layer extraction (brand fingerprints, escalation dynamics, complaint-state NDF)")
    
    try:
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                text = row.get("text", "") or ""
                is_inbound = row.get("inbound", "").strip().lower() == "true"
                author = row.get("author_id", "") or ""
                tweet_id = row.get("tweet_id", "") or ""
                in_response_to = row.get("in_response_to_tweet_id", "") or ""
                
                # Filter short messages -- NDF needs substance
                if not text or len(text) < 80:
                    too_short_skipped += 1
                    continue
                
                # Clean @mentions from start for cleaner extraction
                clean_text = re.sub(r'^(@\S+\s+)+', '', text).strip()
                if len(clean_text) < 50:
                    too_short_skipped += 1
                    continue
                
                # Legacy extraction
                constructs = extract_constructs(clean_text)
                archetypes = detect_archetypes(clean_text)
                mechanisms = detect_mechanisms(clean_text)
                
                for k, v in constructs.items():
                    result.construct_totals[k] = result.construct_totals.get(k, 0) + v
                    result.construct_counts[k] = result.construct_counts.get(k, 0) + 1
                for k, v in archetypes.items():
                    result.archetype_totals[k] = result.archetype_totals.get(k, 0) + v
                for k, v in mechanisms.items():
                    result.mechanism_totals[k] = result.mechanism_totals.get(k, 0) + v
                
                # NDF extraction (use neutral 2.5 rating -- service context, not product rating)
                ndf_val = None
                archetype_val = "unknown"
                if _ndf_extract_fn is not None:
                    try:
                        ndf_val = _ndf_extract_fn(clean_text, rating=2.5)
                        archetype_val = detect_archetype_new(clean_text)
                        if ndf_agg is not None:
                            ndf_agg.add(ndf_val, archetype=archetype_val)
                    except Exception:
                        ndf_val = None
                
                # 430+ dimensions
                if comp_stats is not None and _comprehensive_extract_fn is not None:
                    try:
                        profile = _comprehensive_extract_fn(clean_text, 2.5)
                        if profile:
                            comp_stats.add_profile(profile, 2.5)
                    except Exception:
                        pass
                
                # ═══════════════════════════════════════════════════════
                # INBOUND (Customer complaint)
                # ═══════════════════════════════════════════════════════
                if is_inbound:
                    inbound_processed += 1
                    
                    # Layer 3: Complaint-state NDF
                    if ndf_val is not None and complaint_ndf_agg is not None:
                        complaint_ndf_agg.add(ndf_val, archetype=archetype_val)
                    
                    # Cache for Layer 2 paired analysis
                    if ndf_val is not None and tweet_id and len(inbound_ndf_cache) < MAX_CACHE_SIZE:
                        inbound_ndf_cache[tweet_id] = {
                            "ndf": ndf_val,
                            "archetype": archetype_val,
                            "mechanisms": mechanisms,
                        }
                
                # ═══════════════════════════════════════════════════════
                # OUTBOUND (Brand response)
                # ═══════════════════════════════════════════════════════
                else:
                    outbound_processed += 1
                    brand = author
                    industry = TWCS_BRAND_INDUSTRY.get(brand, "")
                    
                    if ndf_val is not None:
                        # Layer 1: Brand-level persuasion NDF
                        if brand not in brand_ndf_aggs:
                            agg = create_ndf_aggregator()
                            if agg is not None:
                                brand_ndf_aggs[brand] = agg
                        if brand in brand_ndf_aggs:
                            brand_ndf_aggs[brand].add(ndf_val, archetype=archetype_val)
                        
                        # Layer 1b: Industry-level persuasion NDF
                        if industry and industry in industry_ndf_aggs:
                            industry_ndf_aggs[industry].add(ndf_val, archetype=archetype_val)
                    
                    # Track brand mechanism usage (what persuasion tools they deploy)
                    for mech_name, mech_score in mechanisms.items():
                        if mech_score > 0:
                            brand_mechanism_usage[brand][mech_name] += mech_score
                    
                    # Layer 2: Paired escalation/de-escalation analysis
                    if ndf_val is not None and in_response_to and in_response_to in inbound_ndf_cache:
                        customer_data = inbound_ndf_cache[in_response_to]
                        customer_mechs = customer_data["mechanisms"]
                        
                        # Which mechanisms does the brand INTRODUCE that the customer
                        # was NOT already expressing? These are active de-escalation tools.
                        for mech_name, mech_score in mechanisms.items():
                            if mech_score > 0:
                                deescalation_mechanism_scores[mech_name]["total"] += 1
                                # Brand introduces a mechanism not present in the complaint
                                if customer_mechs.get(mech_name, 0) < 0.3:
                                    deescalation_mechanism_scores[mech_name]["effective"] += 1
                        
                        paired_analysis_count += 1
                        
                        # Route customer complaint NDF to the correct industry bucket
                        if industry and industry in industry_complaint_ndf_aggs:
                            industry_complaint_ndf_aggs[industry].add(
                                customer_data["ndf"], archetype=customer_data["archetype"]
                            )
                        
                        # Free memory
                        del inbound_ndf_cache[in_response_to]
                
                # Templates (high-quality brand responses only -- persuasive service recovery language)
                if not is_inbound and len(clean_text) > 100:
                    patterns = extract_persuasive_patterns(clean_text)
                    if patterns:
                        for p in patterns:
                            p["brand"] = author
                            p["context"] = "service_recovery"
                        result.templates.extend(patterns)
                        result.templates_extracted += len(patterns)
                        result.high_quality_reviews += 1
                
                result.reviews_processed += 1
                
                if result.reviews_processed % 200000 == 0:
                    logger.info(
                        f"  {config['display_name']}: {result.reviews_processed:,} tweets "
                        f"(in: {inbound_processed:,}, out: {outbound_processed:,}, "
                        f"paired: {paired_analysis_count:,}, cache: {len(inbound_ndf_cache):,})"
                    )
    
    except Exception as e:
        logger.error(f"Error processing TWCS: {e}")
        import traceback
        traceback.print_exc()
    
    # ═══════════════════════════════════════════════════════════════════════
    # FINALIZE
    # ═══════════════════════════════════════════════════════════════════════
    
    # Global NDF + 430+
    _finalize_new_extraction(result, ndf_agg, comp_stats)
    
    # ─── Layer 1 Output: Brand Persuasion Fingerprints ───
    brand_persuasion_profiles = {}
    for brand, agg in brand_ndf_aggs.items():
        if hasattr(agg, '_count') and agg._count > 50:
            brand_data = agg.to_dict()
            # Append mechanism usage summary
            if brand in brand_mechanism_usage:
                total_mechs = sum(brand_mechanism_usage[brand].values())
                if total_mechs > 0:
                    brand_data["mechanism_preferences"] = {
                        k: round(v / total_mechs, 4)
                        for k, v in sorted(
                            brand_mechanism_usage[brand].items(),
                            key=lambda x: x[1], reverse=True
                        )
                    }
            brand_persuasion_profiles[brand] = brand_data
    
    result.specific_intelligence["brand_persuasion_fingerprints"] = brand_persuasion_profiles
    logger.info(f"  Layer 1 — Brand persuasion fingerprints: {len(brand_persuasion_profiles)} brands (50+ responses each)")
    
    # Industry-level persuasion profiles
    industry_persuasion_profiles = {}
    for ind, agg in industry_ndf_aggs.items():
        if hasattr(agg, '_count') and agg._count > 100:
            industry_persuasion_profiles[ind] = agg.to_dict()
    result.specific_intelligence["industry_persuasion_profiles"] = industry_persuasion_profiles
    logger.info(f"  Layer 1 — Industry persuasion profiles: {list(industry_persuasion_profiles.keys())}")
    
    # ─── Layer 2 Output: Escalation/De-escalation Dynamics ───
    deescalation_effectiveness = {}
    for mech, scores in deescalation_mechanism_scores.items():
        if scores["total"] > 50:  # Minimum sample size for reliability
            eff = scores["effective"] / scores["total"]
            deescalation_effectiveness[mech] = {
                "effectiveness_ratio": round(eff, 4),
                "sample_size": scores["total"],
                "introduced_as_new": scores["effective"],
                "interpretation": (
                    "High ratio = brands frequently introduce this mechanism "
                    "to shift conversations away from customer's emotional state"
                ),
            }
    deescalation_effectiveness = dict(
        sorted(deescalation_effectiveness.items(),
               key=lambda x: x[1]["effectiveness_ratio"], reverse=True)
    )
    result.specific_intelligence["deescalation_dynamics"] = deescalation_effectiveness
    result.specific_intelligence["paired_conversations_analyzed"] = paired_analysis_count
    logger.info(f"  Layer 2 — Paired conversations analyzed: {paired_analysis_count:,}")
    if deescalation_effectiveness:
        top_3 = list(deescalation_effectiveness.items())[:3]
        logger.info(f"  Layer 2 — Top de-escalation mechanisms: "
                    f"{[(m, d['effectiveness_ratio']) for m, d in top_3]}")
    
    # ─── Layer 3 Output: Complaint-State NDF Profiles ───
    complaint_data = {}
    if complaint_ndf_agg and hasattr(complaint_ndf_agg, '_count') and complaint_ndf_agg._count > 0:
        complaint_data = complaint_ndf_agg.to_dict()
    result.specific_intelligence["complaint_state_ndf"] = complaint_data
    if complaint_data:
        logger.info(f"  Layer 3 — Complaint-state NDF from {complaint_data.get('ndf_count', 0):,} customer messages")
    
    # Industry-level complaint NDF
    industry_complaint_profiles = {}
    for ind, agg in industry_complaint_ndf_aggs.items():
        if hasattr(agg, '_count') and agg._count > 20:
            industry_complaint_profiles[ind] = agg.to_dict()
    result.specific_intelligence["industry_complaint_ndf_profiles"] = industry_complaint_profiles
    logger.info(f"  Layer 3 — Industry complaint profiles: {list(industry_complaint_profiles.keys())}")
    
    # ─── Metadata ───
    result.specific_intelligence["service_recovery_intelligence"] = True
    result.specific_intelligence["escalation_dynamics"] = True
    result.specific_intelligence["conversational_pair_data"] = True
    result.specific_intelligence["inbound_processed"] = inbound_processed
    result.specific_intelligence["outbound_processed"] = outbound_processed
    result.specific_intelligence["too_short_filtered"] = too_short_skipped
    result.specific_intelligence["brands_represented"] = len(brand_ndf_aggs)
    result.specific_intelligence["ndf_cache_max"] = MAX_CACHE_SIZE
    result.specific_intelligence["ethical_note"] = (
        "Service interactions analyzed for aggregate persuasion patterns only. "
        "No individual customer identification or targeting based on complaint content. "
        "Brand responses analyzed for communication strategy, not for replication."
    )
    
    result.duration_seconds = time.time() - start_time
    result.templates.sort(key=lambda x: len(x.get("mechanisms", [])), reverse=True)
    
    logger.info(
        f"  {config['display_name']} COMPLETE: {result.reviews_processed:,} tweets "
        f"({inbound_processed:,} customer + {outbound_processed:,} brand) "
        f"in {result.duration_seconds:.1f}s"
    )
    
    return result


# =============================================================================
# MAIN PIPELINE
# =============================================================================

def process_dataset(config: Dict) -> DatasetResult:
    """Route to appropriate processor based on file type."""
    file_type = config.get("file_type", "csv")
    
    if file_type == "csv":
        return process_csv_dataset(config)
    elif file_type == "csv_folder":
        return process_csv_folder(config)
    elif file_type == "csv_multi":
        return process_csv_multi(config)
    elif file_type == "movielens":
        return process_movielens(config)
    elif file_type == "podcast":
        return process_podcast(config)
    elif file_type == "yelp":
        return process_yelp(config)
    elif file_type == "twitter":
        return process_twitter(config)
    elif file_type == "google":
        return process_google_local(config)
    elif file_type == "reddit_mbti":
        return process_reddit_mbti(config)
    elif file_type == "glassdoor":
        return process_glassdoor(config)
    elif file_type == "rent_the_runway":
        return process_rent_the_runway(config)
    elif file_type == "twcs":
        return process_twcs(config)
    else:
        logger.warning(f"Unknown file type: {file_type}")
        return DatasetResult(name=config["name"], display_name=config["display_name"])


def _result_has_new_extractions(result_file: Path) -> bool:
    """Check if an existing result file contains new-format data (NDF, dimensions)."""
    try:
        with open(result_file, 'r') as f:
            data = json.load(f)
        return "ndf_population" in data or "dimension_distributions" in data
    except Exception:
        return False


def run_full_ingestion(skip_google: bool = False, resume_from: str = None, force: bool = False):
    """Run full multi-dataset ingestion."""
    
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    MULTI-DATASET REVIEW INTELLIGENCE                        ║
║                    + NDF + 430+ Dimensions + Deep Archetype                 ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  Processing: 14 datasets (Small → Large, Google LAST)                       ║
║  NEW: NDF (7 dims), Hyperscan archetype, 430+ comprehensive dimensions     ║
║  Purpose: Power DSP, SSP, and Agency targeting without cookies              ║
╚══════════════════════════════════════════════════════════════════════════════╝
    """)
    
    # NEW: Initialize all extraction layers once at startup
    ndf_ok, arch_ok, comp_ok = init_new_extraction_layer()
    logger.info(f"Extraction layers: NDF={ndf_ok}, Archetype={arch_ok}, Comprehensive={comp_ok}")
    
    start_time = time.time()
    all_results = []
    
    datasets_to_process = DATASETS.copy()
    
    # Skip Google if requested (for testing)
    if skip_google:
        datasets_to_process = [d for d in datasets_to_process if d["name"] != "google_local"]
        logger.info("Skipping Google Local (201GB) - will process separately")
    
    # Resume from specific dataset if requested
    if resume_from:
        found = False
        for i, d in enumerate(datasets_to_process):
            if d["name"] == resume_from:
                datasets_to_process = datasets_to_process[i:]
                found = True
                break
        if not found:
            logger.error(f"Dataset '{resume_from}' not found")
            return
    
    # Check for existing results to skip (only skip if new-format or not forced)
    completed = set()
    old_format = set()
    for result_file in OUTPUT_DIR.glob("*_result.json"):
        name = result_file.stem.replace("_result", "")
        if _result_has_new_extractions(result_file):
            completed.add(name)
        else:
            old_format.add(name)
    
    if force:
        logger.info(f"FORCE mode: re-running all datasets (ignoring existing results)")
        completed = set()
    elif old_format:
        logger.info(f"Old-format results (will re-run): {old_format}")
        logger.info(f"New-format results (will skip): {completed}")
    else:
        logger.info(f"Already completed (new format): {completed}")
    
    for i, config in enumerate(datasets_to_process, 1):
        if config["name"] in completed:
            logger.info(f"[{i}/{len(datasets_to_process)}] Skipping {config['display_name']} (already complete)")
            continue
        
        logger.info(f"\n[{i}/{len(datasets_to_process)}] Processing {config['display_name']}...")
        logger.info(f"  Size: {config.get('size_mb', 0):,} MB")
        logger.info(f"  Unique Value: {config.get('unique_value', 'N/A')}")
        
        try:
            result = process_dataset(config)
            all_results.append(result)
            
            # Save individual result
            result_file = OUTPUT_DIR / f"{config['name']}_result.json"
            with open(result_file, 'w') as f:
                json.dump(result.to_dict(), f, indent=2)
            
            logger.info(f"  Saved: {result_file}")
            
        except Exception as e:
            logger.error(f"Error processing {config['display_name']}: {e}")
            import traceback
            traceback.print_exc()
    
    # Create summary
    total_duration = time.time() - start_time
    
    summary = {
        "total_datasets": len(all_results),
        "total_reviews": sum(r.reviews_processed for r in all_results),
        "total_templates": sum(r.templates_extracted for r in all_results),
        "total_duration_hours": total_duration / 3600,
        "datasets": [r.to_dict() for r in all_results],
    }
    
    summary_file = OUTPUT_DIR / "SUMMARY.json"
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                              INGESTION COMPLETE                             ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  Datasets Processed: {len(all_results):>5}                                              ║
║  Total Reviews: {summary['total_reviews']:>15,}                                        ║
║  Templates Extracted: {summary['total_templates']:>10,}                                     ║
║  Duration: {summary['total_duration_hours']:>6.2f} hours                                          ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  Output: {str(OUTPUT_DIR):<60} ║
╚══════════════════════════════════════════════════════════════════════════════╝
    """)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Multi-Dataset Review Intelligence Ingestion")
    parser.add_argument("--skip-google", action="store_true", 
                       help="Skip Google Local (201GB) - process separately")
    parser.add_argument("--google-only", action="store_true",
                       help="Only process Google Local")
    parser.add_argument("--resume-from", type=str,
                       help="Resume from specific dataset name")
    parser.add_argument("--test", action="store_true",
                       help="Test mode - only process first 3 smallest datasets")
    parser.add_argument("--force", action="store_true",
                       help="Force re-run even if results exist (ignore all existing)")
    
    args = parser.parse_args()
    
    if args.google_only:
        # Only process Google
        init_new_extraction_layer()
        google_config = [d for d in DATASETS if d["name"] == "google_local"][0]
        result = process_google_local(google_config)
        result_file = OUTPUT_DIR / "google_local_result.json"
        with open(result_file, 'w') as f:
            json.dump(result.to_dict(), f, indent=2)
        print(f"Google Local complete: {result.reviews_processed:,} reviews")
    elif args.test:
        # Test mode - only first 3
        DATASETS_COPY = DATASETS[:3]
        DATASETS.clear()
        DATASETS.extend(DATASETS_COPY)
        run_full_ingestion(skip_google=True, force=args.force)
    else:
        run_full_ingestion(skip_google=args.skip_google, resume_from=args.resume_from, force=args.force)
