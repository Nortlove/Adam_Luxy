#!/usr/bin/env python3
# =============================================================================
# ADAM Platform - Google Reviews Enhanced Learning (High-Value Additions)
# Location: scripts/run_google_enhanced_learning.py
# =============================================================================

"""
GOOGLE REVIEWS ENHANCED LEARNING

Extracts additional high-value patterns from Google Reviews:

1. STATE × CATEGORY × ARCHETYPE (3-way interaction)
   - Enables hyper-local targeting
   - "What archetype prefers Healthcare_Dental in Texas vs. California?"
   - "What archetypes use Auto_Repair in urban Northeast vs. rural Southwest?"

2. TEMPORAL PATTERNS BY REGION/STATE
   - Timezone-aware engagement windows
   - Regional cultural patterns (early risers vs. night owls)
   - Best hours to reach each archetype by region

3. BUSINESS RATING × ARCHETYPE CORRELATION
   - Do certain archetypes prefer highly-rated businesses?
   - Rating standards by archetype

4. DAY-OF-WEEK PATTERNS BY REGION
   - Weekend vs. weekday engagement by region
   - Cultural differences in review timing

Usage:
    python scripts/run_google_enhanced_learning.py
"""

import argparse
import asyncio
import json
import logging
import sys
import math
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
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


# =============================================================================
# PATHS
# =============================================================================

GOOGLE_DATA_DIR = project_root / "google_reviews"
LEARNING_DATA_DIR = project_root / "data" / "learning"
LEARNING_DATA_DIR.mkdir(parents=True, exist_ok=True)

ENHANCED_PRIORS_PATH = LEARNING_DATA_DIR / "google_enhanced_priors.json"
MERGED_PRIORS_PATH = LEARNING_DATA_DIR / "complete_coldstart_priors.json"


# =============================================================================
# REGION MAPPINGS
# =============================================================================

US_REGIONS = {
    "Connecticut": "Northeast", "Maine": "Northeast", "Massachusetts": "Northeast",
    "New_Hampshire": "Northeast", "Rhode_Island": "Northeast", "Vermont": "Northeast",
    "New_Jersey": "Northeast", "New_York": "Northeast", "Pennsylvania": "Northeast",
    "Alabama": "Southeast", "Arkansas": "Southeast", "Florida": "Southeast",
    "Georgia": "Southeast", "Kentucky": "Southeast", "Louisiana": "Southeast",
    "Mississippi": "Southeast", "North_Carolina": "Southeast", "South_Carolina": "Southeast",
    "Tennessee": "Southeast", "Virginia": "Southeast", "West_Virginia": "Southeast",
    "Illinois": "Midwest", "Indiana": "Midwest", "Iowa": "Midwest",
    "Kansas": "Midwest", "Michigan": "Midwest", "Minnesota": "Midwest",
    "Missouri": "Midwest", "Nebraska": "Midwest", "North_Dakota": "Midwest",
    "Ohio": "Midwest", "South_Dakota": "Midwest", "Wisconsin": "Midwest",
    "Arizona": "Southwest", "New_Mexico": "Southwest", "Oklahoma": "Southwest", "Texas": "Southwest",
    "Alaska": "West", "California": "West", "Colorado": "West", "Hawaii": "West",
    "Idaho": "West", "Montana": "West", "Nevada": "West", "Oregon": "West",
    "Utah": "West", "Washington": "West", "Wyoming": "West",
    "District_of_Columbia": "Northeast",
}

# Timezone offsets from UTC for regions (approximate)
REGION_TIMEZONE_OFFSET = {
    "Northeast": -5,  # EST
    "Southeast": -5,  # EST
    "Midwest": -6,    # CST
    "Southwest": -6,  # CST/MST mix
    "West": -8,       # PST
}

# Local category mapping (simplified from main script)
LOCAL_CATEGORY_MAP = {
    "dentist": "Healthcare_Dental", "doctor": "Healthcare_Medical", "hospital": "Healthcare_Hospital",
    "pharmacy": "Healthcare_Pharmacy", "clinic": "Healthcare_Clinic", "health": "Healthcare_General",
    "restaurant": "Dining_Restaurant", "cafe": "Dining_Cafe", "coffee": "Dining_Coffee",
    "fast food": "Dining_FastFood", "pizza": "Dining_Pizza", "bar": "Dining_Bar",
    "auto repair": "Auto_Repair", "car dealer": "Auto_Dealer", "mechanic": "Auto_Repair",
    "gas station": "Auto_Gas", "car wash": "Auto_CarWash",
    "salon": "Personal_Salon", "barber": "Personal_Barber", "spa": "Personal_Spa",
    "gym": "Personal_Fitness", "fitness": "Personal_Fitness",
    "lawyer": "Professional_Legal", "accountant": "Professional_Accounting",
    "bank": "Professional_Banking", "insurance": "Professional_Insurance",
    "store": "Retail_General", "grocery": "Retail_Grocery", "supermarket": "Retail_Grocery",
    "hotel": "Entertainment_Hotel", "theater": "Entertainment_Theater",
    "school": "Education_School", "daycare": "Education_Daycare",
}


# =============================================================================
# LIGHTWEIGHT ARCHETYPE CLASSIFIER
# =============================================================================

class LightweightArchetypeClassifier:
    """Same classifier as main script."""
    
    PROMOTION_WORDS = {"love", "amazing", "best", "excellent", "perfect", "great", "awesome", "fantastic"}
    PREVENTION_WORDS = {"safe", "reliable", "trust", "quality", "careful", "professional", "honest", "clean"}
    ANALYTICAL_WORDS = {"however", "although", "compared", "price", "cost", "wait", "time", "service"}
    SOCIAL_WORDS = {"recommend", "everyone", "friends", "family", "staff", "friendly", "welcoming"}
    EXPLORER_WORDS = {"tried", "discovered", "new", "different", "unique", "first", "interesting"}
    
    CATEGORY_ARCHETYPE_BIAS = {
        "healthcare": {"Guardian": 0.45, "Analyzer": 0.25, "Connector": 0.15, "Achiever": 0.10, "Explorer": 0.05},
        "dining": {"Connector": 0.35, "Explorer": 0.30, "Achiever": 0.15, "Guardian": 0.10, "Analyzer": 0.10},
        "auto": {"Guardian": 0.35, "Pragmatist": 0.25, "Achiever": 0.20, "Analyzer": 0.15, "Connector": 0.05},
        "personal": {"Connector": 0.40, "Achiever": 0.25, "Explorer": 0.15, "Guardian": 0.15, "Pragmatist": 0.05},
        "professional": {"Guardian": 0.35, "Analyzer": 0.30, "Achiever": 0.20, "Pragmatist": 0.10, "Connector": 0.05},
        "retail": {"Explorer": 0.30, "Connector": 0.25, "Achiever": 0.20, "Guardian": 0.15, "Pragmatist": 0.10},
        "entertainment": {"Explorer": 0.35, "Connector": 0.30, "Achiever": 0.20, "Analyzer": 0.10, "Guardian": 0.05},
        "education": {"Guardian": 0.35, "Analyzer": 0.30, "Connector": 0.20, "Achiever": 0.10, "Explorer": 0.05},
    }
    
    def classify(self, text: str, rating: float, category: str, review_length: int = 0) -> Tuple[str, float]:
        text_lower = text.lower() if text else ""
        words = set(re.findall(r'\b\w+\b', text_lower))
        
        category_key = self._normalize_category(category)
        base_weights = self.CATEGORY_ARCHETYPE_BIAS.get(
            category_key, 
            {"Connector": 0.25, "Achiever": 0.20, "Explorer": 0.20, "Guardian": 0.20, "Pragmatist": 0.10, "Analyzer": 0.05}
        ).copy()
        
        # Keyword adjustments
        if len(words & self.PROMOTION_WORDS) > 0:
            base_weights["Achiever"] = base_weights.get("Achiever", 0.2) + 0.1
        if len(words & self.PREVENTION_WORDS) > 0:
            base_weights["Guardian"] = base_weights.get("Guardian", 0.15) + 0.15
        if len(words & self.ANALYTICAL_WORDS) > 0:
            base_weights["Analyzer"] = base_weights.get("Analyzer", 0.05) + 0.15
        if len(words & self.SOCIAL_WORDS) > 0:
            base_weights["Connector"] = base_weights.get("Connector", 0.25) + 0.15
        if len(words & self.EXPLORER_WORDS) > 0:
            base_weights["Explorer"] = base_weights.get("Explorer", 0.2) + 0.15
        
        # Rating adjustments
        if rating >= 4.5:
            base_weights["Connector"] = base_weights.get("Connector", 0.25) + 0.05
        elif rating <= 2:
            base_weights["Analyzer"] = base_weights.get("Analyzer", 0.05) + 0.1
        
        # Length adjustments
        if review_length > 500:
            base_weights["Analyzer"] = base_weights.get("Analyzer", 0.05) + 0.1
        elif review_length < 50:
            base_weights["Pragmatist"] = base_weights.get("Pragmatist", 0.1) + 0.05
        
        total = sum(base_weights.values())
        normalized = {k: v / total for k, v in base_weights.items()}
        archetype = max(normalized, key=normalized.get)
        return archetype, normalized[archetype]
    
    def _normalize_category(self, category: str) -> str:
        cat_lower = category.lower()
        if any(x in cat_lower for x in ["health", "dental", "doctor", "medical", "hospital", "pharmacy"]):
            return "healthcare"
        elif any(x in cat_lower for x in ["restaurant", "cafe", "coffee", "food", "dining", "pizza", "bar"]):
            return "dining"
        elif any(x in cat_lower for x in ["auto", "car", "mechanic", "tire", "gas"]):
            return "auto"
        elif any(x in cat_lower for x in ["salon", "barber", "spa", "gym", "fitness"]):
            return "personal"
        elif any(x in cat_lower for x in ["lawyer", "accountant", "bank", "insurance"]):
            return "professional"
        elif any(x in cat_lower for x in ["store", "shop", "grocery", "retail"]):
            return "retail"
        elif any(x in cat_lower for x in ["hotel", "theater", "movie", "entertainment"]):
            return "entertainment"
        elif any(x in cat_lower for x in ["school", "university", "education", "daycare"]):
            return "education"
        return "general"


# =============================================================================
# ENHANCED AGGREGATOR
# =============================================================================

@dataclass
class EnhancedAggregator:
    """Collects enhanced patterns from Google Reviews."""
    
    # 3-WAY: State × Category × Archetype
    state_category_archetypes: Dict[str, Dict[str, Dict[str, int]]] = field(
        default_factory=lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
    )
    
    # Temporal by Region: Region × Hour × Archetype
    region_hour_archetypes: Dict[str, Dict[int, Dict[str, int]]] = field(
        default_factory=lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
    )
    
    # Temporal by State: State × Hour × Archetype
    state_hour_archetypes: Dict[str, Dict[int, Dict[str, int]]] = field(
        default_factory=lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
    )
    
    # Day of Week by Region: Region × DayOfWeek × Archetype
    region_dow_archetypes: Dict[str, Dict[int, Dict[str, int]]] = field(
        default_factory=lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
    )
    
    # Business Rating × Archetype: Rating bucket → Archetype
    rating_archetypes: Dict[str, Dict[str, int]] = field(
        default_factory=lambda: defaultdict(lambda: defaultdict(int))
    )
    
    # Density × Category × Archetype (3-way with density)
    density_category_archetypes: Dict[str, Dict[str, Dict[str, int]]] = field(
        default_factory=lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
    )
    
    # Statistics
    total_reviews: int = 0
    
    def add_review(
        self,
        state: str,
        region: str,
        category: str,
        archetype: str,
        rating: float,
        hour_of_day: Optional[int] = None,
        day_of_week: Optional[int] = None,
        density: str = "unknown",
    ) -> None:
        """Add a review to enhanced aggregates."""
        
        self.total_reviews += 1
        
        # 3-WAY: State × Category × Archetype
        self.state_category_archetypes[state][category][archetype] += 1
        
        # Temporal by Region
        if hour_of_day is not None:
            self.region_hour_archetypes[region][hour_of_day][archetype] += 1
            self.state_hour_archetypes[state][hour_of_day][archetype] += 1
        
        # Day of Week by Region
        if day_of_week is not None:
            self.region_dow_archetypes[region][day_of_week][archetype] += 1
        
        # Rating buckets
        if rating <= 2:
            rating_bucket = "low_1_2"
        elif rating <= 3:
            rating_bucket = "mid_3"
        elif rating <= 4:
            rating_bucket = "good_4"
        else:
            rating_bucket = "excellent_5"
        self.rating_archetypes[rating_bucket][archetype] += 1
        
        # Density × Category × Archetype
        self.density_category_archetypes[density][category][archetype] += 1


# =============================================================================
# PARSE FUNCTIONS
# =============================================================================

def map_to_local_category(categories: List[str]) -> str:
    """Map Google business categories to our taxonomy."""
    if not categories:
        return "General"
    all_cats = " ".join(categories).lower()
    for keyword, mapped_cat in LOCAL_CATEGORY_MAP.items():
        if keyword in all_cats:
            return mapped_cat
    return categories[0] if categories else "General"


def parse_reviews_enhanced(filepath: Path, sample_rate: float = 0.01) -> list:
    """Parse Google reviews with enhanced extraction."""
    state = filepath.stem.replace("review-", "")
    region = US_REGIONS.get(state, "Unknown")
    
    reviews = []
    count = 0
    
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                if np.random.random() > sample_rate:
                    continue
                
                try:
                    row = json.loads(line.strip())
                    
                    text = row.get('text', '') or ''
                    rating = float(row.get('rating', 3) or 3)
                    
                    # Parse timestamp for temporal patterns
                    timestamp = row.get('time')
                    hour_of_day = None
                    day_of_week = None
                    if timestamp:
                        try:
                            dt = datetime.fromtimestamp(timestamp / 1000)
                            hour_of_day = dt.hour
                            day_of_week = dt.weekday()  # 0=Monday, 6=Sunday
                        except:
                            pass
                    
                    reviews.append({
                        "state": state,
                        "region": region,
                        "text": text,
                        "rating": rating,
                        "hour_of_day": hour_of_day,
                        "day_of_week": day_of_week,
                        "business_id": row.get('gmap_id', ''),
                    })
                    
                    count += 1
                    if count >= 100000:  # Cap per file for enhanced learning
                        break
                        
                except json.JSONDecodeError:
                    continue
    except Exception as e:
        logger.warning(f"Error parsing {filepath.name}: {e}")
    
    return reviews


def parse_metadata(filepath: Path) -> Dict[str, Dict]:
    """Parse metadata file."""
    metadata = {}
    if not filepath.exists():
        return metadata
    
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                try:
                    row = json.loads(line.strip())
                    gmap_id = row.get('gmap_id', '')
                    if gmap_id:
                        categories = row.get('category', [])
                        if isinstance(categories, str):
                            categories = [categories]
                        
                        # Determine density from coordinates
                        lat = row.get('latitude')
                        lon = row.get('longitude')
                        density = classify_density(lat, lon) if lat and lon else "unknown"
                        
                        metadata[gmap_id] = {
                            "categories": categories,
                            "density": density,
                        }
                except:
                    continue
    except:
        pass
    
    return metadata


# Major metros for density classification
MAJOR_METROS = {
    "New_York": (40.7128, -74.0060, 50),
    "Los_Angeles": (34.0522, -118.2437, 80),
    "Chicago": (41.8781, -87.6298, 40),
    "Houston": (29.7604, -95.3698, 60),
    "Phoenix": (33.4484, -112.0740, 50),
    "Philadelphia": (39.9526, -75.1652, 35),
    "San_Antonio": (29.4241, -98.4936, 40),
    "San_Diego": (32.7157, -117.1611, 40),
    "Dallas": (32.7767, -96.7970, 50),
    "San_Francisco": (37.7749, -122.4194, 25),
    "Seattle": (47.6062, -122.3321, 35),
    "Denver": (39.7392, -104.9903, 40),
    "Boston": (42.3601, -71.0589, 35),
    "Miami": (25.7617, -80.1918, 40),
    "Atlanta": (33.7490, -84.3880, 50),
}


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance in km."""
    R = 6371
    lat1_rad, lat2_rad = math.radians(lat1), math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    a = math.sin(delta_lat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))


def classify_density(latitude: float, longitude: float) -> str:
    """Classify location as urban/suburban/rural."""
    for metro, (lat, lon, radius) in MAJOR_METROS.items():
        distance = haversine_distance(latitude, longitude, lat, lon)
        if distance <= radius * 0.5:
            return "urban"
        elif distance <= radius:
            return "suburban"
    return "rural"


# =============================================================================
# GENERATE ENHANCED PRIORS
# =============================================================================

def generate_enhanced_priors(aggregator: EnhancedAggregator) -> Dict[str, Any]:
    """Generate enhanced priors from aggregates."""
    
    priors = {}
    
    # =========================================================================
    # 1. STATE × CATEGORY × ARCHETYPE (3-way)
    # =========================================================================
    state_category_priors = {}
    for state, categories in aggregator.state_category_archetypes.items():
        state_category_priors[state] = {}
        for category, archetypes in categories.items():
            total = sum(archetypes.values())
            if total >= 50:  # Minimum threshold
                state_category_priors[state][category] = {
                    arch: round(count / total, 4)
                    for arch, count in archetypes.items()
                }
    priors["state_category_archetype_priors"] = state_category_priors
    
    # =========================================================================
    # 2. TEMPORAL BY REGION (Region × Hour → Archetype)
    # =========================================================================
    region_temporal = {}
    for region, hours in aggregator.region_hour_archetypes.items():
        region_temporal[region] = {}
        for hour, archetypes in hours.items():
            total = sum(archetypes.values())
            if total >= 20:
                # Get dominant archetype for this hour
                dominant = max(archetypes.items(), key=lambda x: x[1])
                region_temporal[region][str(hour)] = {
                    "dominant_archetype": dominant[0],
                    "confidence": round(dominant[1] / total, 4),
                    "distribution": {
                        arch: round(count / total, 4)
                        for arch, count in archetypes.items()
                    }
                }
        
        # Calculate best hours per archetype for this region
        archetype_hours = defaultdict(list)
        for hour, archetypes in hours.items():
            total = sum(archetypes.values())
            if total > 0:
                for arch, count in archetypes.items():
                    archetype_hours[arch].append((hour, count / total))
        
        best_hours = {}
        for arch, hour_scores in archetype_hours.items():
            sorted_hours = sorted(hour_scores, key=lambda x: x[1], reverse=True)
            best_hours[arch] = [h for h, _ in sorted_hours[:3]]
        
        region_temporal[region]["best_hours_by_archetype"] = best_hours
    
    priors["region_temporal_patterns"] = region_temporal
    
    # =========================================================================
    # 3. DAY OF WEEK BY REGION
    # =========================================================================
    dow_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    region_dow = {}
    for region, days in aggregator.region_dow_archetypes.items():
        region_dow[region] = {}
        for dow, archetypes in days.items():
            total = sum(archetypes.values())
            if total >= 20:
                dominant = max(archetypes.items(), key=lambda x: x[1])
                region_dow[region][dow_names[dow]] = {
                    "dominant_archetype": dominant[0],
                    "distribution": {
                        arch: round(count / total, 4)
                        for arch, count in archetypes.items()
                    }
                }
    priors["region_day_of_week_patterns"] = region_dow
    
    # =========================================================================
    # 4. RATING × ARCHETYPE
    # =========================================================================
    rating_priors = {}
    for rating_bucket, archetypes in aggregator.rating_archetypes.items():
        total = sum(archetypes.values())
        if total > 0:
            rating_priors[rating_bucket] = {
                arch: round(count / total, 4)
                for arch, count in archetypes.items()
            }
    priors["rating_archetype_correlation"] = rating_priors
    
    # =========================================================================
    # 5. DENSITY × CATEGORY × ARCHETYPE
    # =========================================================================
    density_category_priors = {}
    for density, categories in aggregator.density_category_archetypes.items():
        density_category_priors[density] = {}
        for category, archetypes in categories.items():
            total = sum(archetypes.values())
            if total >= 30:
                density_category_priors[density][category] = {
                    arch: round(count / total, 4)
                    for arch, count in archetypes.items()
                }
    priors["density_category_archetype_priors"] = density_category_priors
    
    # =========================================================================
    # 6. STATISTICS
    # =========================================================================
    priors["enhanced_learning_stats"] = {
        "total_reviews_processed": aggregator.total_reviews,
        "states_with_category_data": len(state_category_priors),
        "regions_with_temporal_data": len(region_temporal),
        "density_types_with_category_data": len(density_category_priors),
    }
    
    return priors


def merge_enhanced_priors(enhanced: Dict, existing_path: Path) -> Dict:
    """Merge enhanced priors with existing."""
    if not existing_path.exists():
        return enhanced
    
    with open(existing_path) as f:
        existing = json.load(f)
    
    merged = existing.copy()
    
    # Add all enhanced priors (these are new dimensions)
    merged["state_category_archetype_priors"] = enhanced.get("state_category_archetype_priors", {})
    merged["region_temporal_patterns"] = enhanced.get("region_temporal_patterns", {})
    merged["region_day_of_week_patterns"] = enhanced.get("region_day_of_week_patterns", {})
    merged["rating_archetype_correlation"] = enhanced.get("rating_archetype_correlation", {})
    merged["density_category_archetype_priors"] = enhanced.get("density_category_archetype_priors", {})
    merged["enhanced_learning_stats"] = enhanced.get("enhanced_learning_stats", {})
    
    return merged


# =============================================================================
# MAIN
# =============================================================================

async def main():
    start_time = datetime.now()
    
    print("\n" + "=" * 70)
    print("GOOGLE REVIEWS ENHANCED LEARNING")
    print("=" * 70)
    print(f"Started at: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("\nExtracting high-value patterns:")
    print("  1. State × Category × Archetype (3-way interaction)")
    print("  2. Temporal patterns by Region (timezone-aware)")
    print("  3. Day-of-week patterns by Region")
    print("  4. Rating × Archetype correlation")
    print("  5. Density × Category × Archetype")
    print()
    
    aggregator = EnhancedAggregator()
    classifier = LightweightArchetypeClassifier()
    
    # Find all review files
    review_files = sorted([
        f for f in GOOGLE_DATA_DIR.glob("review-*.json")
    ], key=lambda x: x.stat().st_size, reverse=True)
    
    logger.info(f"Processing {len(review_files)} state files...")
    
    for file_idx, review_file in enumerate(review_files):
        state_name = review_file.stem.replace("review-", "")
        region = US_REGIONS.get(state_name, "Unknown")
        
        logger.info(f"[{file_idx+1}/{len(review_files)}] {state_name} ({region})...")
        
        # Load metadata
        metadata_file = GOOGLE_DATA_DIR / f"meta-{state_name}.json"
        metadata = parse_metadata(metadata_file)
        
        # Parse reviews
        reviews = parse_reviews_enhanced(review_file, sample_rate=0.01)
        
        for review in reviews:
            # Get category and density from metadata
            categories = ["General"]
            density = "unknown"
            if review["business_id"] in metadata:
                meta = metadata[review["business_id"]]
                categories = meta.get("categories", ["General"])
                density = meta.get("density", "unknown")
            
            local_category = map_to_local_category(categories)
            
            # Classify
            archetype, _ = classifier.classify(
                review["text"],
                review["rating"],
                local_category,
                len(review["text"]) if review["text"] else 0,
            )
            
            # Add to aggregator
            aggregator.add_review(
                state=review["state"],
                region=review["region"],
                category=local_category,
                archetype=archetype,
                rating=review["rating"],
                hour_of_day=review.get("hour_of_day"),
                day_of_week=review.get("day_of_week"),
                density=density,
            )
        
        logger.info(f"  Processed {len(reviews)} reviews")
    
    # Generate priors
    logger.info("\nGenerating enhanced priors...")
    enhanced_priors = generate_enhanced_priors(aggregator)
    
    # Save enhanced priors
    with open(ENHANCED_PRIORS_PATH, 'w') as f:
        json.dump(enhanced_priors, f, indent=2)
    logger.info(f"✓ Enhanced priors saved: {ENHANCED_PRIORS_PATH}")
    
    # Merge with existing
    logger.info("Merging with existing priors...")
    merged = merge_enhanced_priors(enhanced_priors, MERGED_PRIORS_PATH)
    
    with open(MERGED_PRIORS_PATH, 'w') as f:
        json.dump(merged, f, indent=2)
    logger.info(f"✓ Merged priors saved: {MERGED_PRIORS_PATH}")
    
    # Summary
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    print("\n" + "=" * 70)
    print("ENHANCED LEARNING COMPLETE")
    print("=" * 70)
    print(f"\nProcessing time: {duration:.1f} seconds ({duration/60:.1f} minutes)")
    print(f"\nReviews processed: {aggregator.total_reviews:,}")
    
    stats = enhanced_priors.get("enhanced_learning_stats", {})
    print(f"\nEnhanced patterns extracted:")
    print(f"  • State × Category combinations: {stats.get('states_with_category_data', 0)} states")
    print(f"  • Region temporal patterns: {stats.get('regions_with_temporal_data', 0)} regions")
    print(f"  • Density × Category patterns: {stats.get('density_types_with_category_data', 0)} density types")
    
    # Show some examples
    print("\n" + "-" * 50)
    print("EXAMPLE: California Healthcare_Dental archetypes:")
    ca_dental = enhanced_priors.get("state_category_archetype_priors", {}).get("California", {}).get("Healthcare_Dental", {})
    if ca_dental:
        for arch, prob in sorted(ca_dental.items(), key=lambda x: x[1], reverse=True)[:3]:
            print(f"  • {arch}: {prob:.1%}")
    
    print("\nEXAMPLE: West region best hours by archetype:")
    west_temporal = enhanced_priors.get("region_temporal_patterns", {}).get("West", {}).get("best_hours_by_archetype", {})
    if west_temporal:
        for arch, hours in list(west_temporal.items())[:3]:
            print(f"  • {arch}: {hours}")
    
    print("\n✓ Enhanced learning complete!")


if __name__ == "__main__":
    asyncio.run(main())
