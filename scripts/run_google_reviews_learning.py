#!/usr/bin/env python3
# =============================================================================
# ADAM Platform - Google Reviews Location-Aware Learning Pipeline
# Location: scripts/run_google_reviews_learning.py
# =============================================================================

"""
GOOGLE REVIEWS LOCATION-AWARE LEARNING PIPELINE

Processes the complete Google Maps review corpus (201GB, 51 states + DC) through
ADAM's robust learning system with UNIQUE LOCATION INTELLIGENCE:

DATA SOURCES (201GB Total):
- review-California.json (20GB) - Largest state
- review-Texas.json (20GB)
- review-Florida.json (19GB)
- review-New_York.json (9.8GB)
- ... and 48 more state files

UNIQUE LOCATION-BASED LEARNING:
1. State/Regional Archetype Patterns - Regional psychology variations
2. Local Business Categories - Healthcare, dining, services (different from Amazon)
3. Geographic Density - Urban/suburban/rural patterns from lat/long
4. Business Response Impact - How responses affect engagement per archetype
5. Regional Category Preferences - What categories dominate which regions

5 CORE ANALYSIS TYPES (Same as Amazon):
1. Archetype Classification - Assign archetypes from behavioral signals
2. Category→Archetype Priors - What archetypes use what local services
3. Cross-Category Behavior - Who uses what services together
4. Reviewer Lifecycle Patterns - New vs experienced local reviewers
5. Business Engagement Patterns - Response rates by archetype

OUTPUT:
- State-level archetype priors (51 states)
- Local service category priors (50+ categories)
- Urban/suburban/rural archetype patterns
- Business response effectiveness by archetype
- Regional cross-category preferences
- Merged with existing 8.3M review priors

Usage:
    # Full processing (takes 3-5 hours for 201GB)
    python scripts/run_google_reviews_learning.py
    
    # Test mode (sample only, ~5 minutes)
    python scripts/run_google_reviews_learning.py --test
    
    # Resume from checkpoint
    python scripts/run_google_reviews_learning.py --resume
    
    # Specific states only
    python scripts/run_google_reviews_learning.py --states California Texas
"""

import argparse
import asyncio
import json
import logging
import sys
import time
import math
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Set, Tuple
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
        logging.FileHandler(log_dir / 'google_reviews_learning.log', mode='a'),
    ]
)
logger = logging.getLogger(__name__)


# =============================================================================
# PATHS
# =============================================================================

GOOGLE_DATA_DIR = project_root / "google_reviews"
LEARNING_DATA_DIR = project_root / "data" / "learning"
LEARNING_DATA_DIR.mkdir(parents=True, exist_ok=True)

CHECKPOINT_PATH = LEARNING_DATA_DIR / "google_learning_checkpoint.json"
GOOGLE_PRIORS_PATH = LEARNING_DATA_DIR / "google_coldstart_priors.json"
MERGED_PRIORS_PATH = LEARNING_DATA_DIR / "complete_coldstart_priors.json"


# =============================================================================
# US REGIONS MAPPING
# =============================================================================

US_REGIONS = {
    # Northeast
    "Connecticut": "Northeast",
    "Maine": "Northeast",
    "Massachusetts": "Northeast",
    "New_Hampshire": "Northeast",
    "Rhode_Island": "Northeast",
    "Vermont": "Northeast",
    "New_Jersey": "Northeast",
    "New_York": "Northeast",
    "Pennsylvania": "Northeast",
    
    # Southeast
    "Alabama": "Southeast",
    "Arkansas": "Southeast",
    "Florida": "Southeast",
    "Georgia": "Southeast",
    "Kentucky": "Southeast",
    "Louisiana": "Southeast",
    "Mississippi": "Southeast",
    "North_Carolina": "Southeast",
    "South_Carolina": "Southeast",
    "Tennessee": "Southeast",
    "Virginia": "Southeast",
    "West_Virginia": "Southeast",
    
    # Midwest
    "Illinois": "Midwest",
    "Indiana": "Midwest",
    "Iowa": "Midwest",
    "Kansas": "Midwest",
    "Michigan": "Midwest",
    "Minnesota": "Midwest",
    "Missouri": "Midwest",
    "Nebraska": "Midwest",
    "North_Dakota": "Midwest",
    "Ohio": "Midwest",
    "South_Dakota": "Midwest",
    "Wisconsin": "Midwest",
    
    # Southwest
    "Arizona": "Southwest",
    "New_Mexico": "Southwest",
    "Oklahoma": "Southwest",
    "Texas": "Southwest",
    
    # West
    "Alaska": "West",
    "California": "West",
    "Colorado": "West",
    "Hawaii": "West",
    "Idaho": "West",
    "Montana": "West",
    "Nevada": "West",
    "Oregon": "West",
    "Utah": "West",
    "Washington": "West",
    "Wyoming": "West",
    
    # Federal District
    "District_of_Columbia": "Northeast",
}


# =============================================================================
# LOCAL BUSINESS CATEGORY MAPPING
# =============================================================================

LOCAL_CATEGORY_MAP = {
    # Healthcare
    "dentist": "Healthcare_Dental",
    "doctor": "Healthcare_Medical",
    "hospital": "Healthcare_Hospital",
    "pharmacy": "Healthcare_Pharmacy",
    "optometrist": "Healthcare_Vision",
    "chiropractor": "Healthcare_Alternative",
    "veterinarian": "Healthcare_Veterinary",
    "urgent care": "Healthcare_Urgent",
    "clinic": "Healthcare_Clinic",
    "medical": "Healthcare_Medical",
    "health": "Healthcare_Medical",
    "physical therapy": "Healthcare_Therapy",
    "mental health": "Healthcare_Mental",
    "dermatologist": "Healthcare_Specialty",
    
    # Food & Dining
    "restaurant": "Dining_Restaurant",
    "cafe": "Dining_Cafe",
    "coffee": "Dining_Coffee",
    "fast food": "Dining_FastFood",
    "pizza": "Dining_Pizza",
    "bar": "Dining_Bar",
    "brewery": "Dining_Brewery",
    "bakery": "Dining_Bakery",
    "deli": "Dining_Deli",
    "food": "Dining_Restaurant",
    "takeout": "Dining_Takeout",
    "catering": "Dining_Catering",
    "ice cream": "Dining_Dessert",
    "dessert": "Dining_Dessert",
    
    # Automotive
    "auto repair": "Auto_Repair",
    "car dealer": "Auto_Dealer",
    "car wash": "Auto_CarWash",
    "gas station": "Auto_Gas",
    "tire": "Auto_Tire",
    "mechanic": "Auto_Repair",
    "oil change": "Auto_Maintenance",
    "body shop": "Auto_BodyShop",
    "auto parts": "Auto_Parts",
    
    # Personal Services
    "salon": "Personal_Salon",
    "barber": "Personal_Barber",
    "spa": "Personal_Spa",
    "nail": "Personal_Nails",
    "gym": "Personal_Fitness",
    "fitness": "Personal_Fitness",
    "yoga": "Personal_Wellness",
    "massage": "Personal_Massage",
    "laundry": "Personal_Laundry",
    "dry cleaner": "Personal_DryClean",
    
    # Professional Services
    "lawyer": "Professional_Legal",
    "attorney": "Professional_Legal",
    "accountant": "Professional_Accounting",
    "real estate": "Professional_RealEstate",
    "insurance": "Professional_Insurance",
    "bank": "Professional_Banking",
    "financial": "Professional_Financial",
    "consultant": "Professional_Consulting",
    
    # Retail
    "store": "Retail_General",
    "shop": "Retail_General",
    "grocery": "Retail_Grocery",
    "supermarket": "Retail_Grocery",
    "convenience": "Retail_Convenience",
    "clothing": "Retail_Clothing",
    "electronics": "Retail_Electronics",
    "hardware": "Retail_Hardware",
    "furniture": "Retail_Furniture",
    "jewelry": "Retail_Jewelry",
    "florist": "Retail_Florist",
    "pet store": "Retail_Pet",
    "bookstore": "Retail_Books",
    "pharmacy": "Retail_Pharmacy",
    
    # Home Services
    "plumber": "Home_Plumbing",
    "electrician": "Home_Electrical",
    "hvac": "Home_HVAC",
    "roofing": "Home_Roofing",
    "landscaping": "Home_Landscaping",
    "cleaning": "Home_Cleaning",
    "pest control": "Home_PestControl",
    "moving": "Home_Moving",
    "contractor": "Home_Contractor",
    "painter": "Home_Painting",
    
    # Entertainment & Recreation
    "hotel": "Entertainment_Hotel",
    "motel": "Entertainment_Hotel",
    "theater": "Entertainment_Theater",
    "movie": "Entertainment_Movie",
    "museum": "Entertainment_Museum",
    "park": "Entertainment_Park",
    "golf": "Entertainment_Golf",
    "bowling": "Entertainment_Bowling",
    "arcade": "Entertainment_Arcade",
    "amusement": "Entertainment_Amusement",
    
    # Education
    "school": "Education_School",
    "university": "Education_University",
    "college": "Education_College",
    "tutoring": "Education_Tutoring",
    "daycare": "Education_Daycare",
    "preschool": "Education_Preschool",
    
    # Religious
    "church": "Religious_Church",
    "temple": "Religious_Temple",
    "mosque": "Religious_Mosque",
    "synagogue": "Religious_Synagogue",
    
    # Government
    "post office": "Government_PostOffice",
    "dmv": "Government_DMV",
    "courthouse": "Government_Court",
    "library": "Government_Library",
}


# =============================================================================
# LIGHTWEIGHT ARCHETYPE CLASSIFIER (Enhanced for Local Services)
# =============================================================================

class LocalServiceArchetypeClassifier:
    """
    Classifies reviews into archetypes using behavioral signals.
    Enhanced for local service businesses.
    
    Uses:
    - Rating patterns
    - Review length
    - Sentiment keywords
    - Local service category context
    - Business response impact
    - Photo uploads
    """
    
    # Keyword-based sentiment indicators
    PROMOTION_WORDS = {"love", "amazing", "best", "excellent", "perfect", "great", "awesome", "fantastic", "incredible", "wonderful", "recommend"}
    PREVENTION_WORDS = {"safe", "reliable", "trust", "quality", "careful", "thorough", "professional", "honest", "dependable", "clean"}
    ANALYTICAL_WORDS = {"however", "although", "compared", "price", "cost", "wait", "time", "service", "experience", "review"}
    SOCIAL_WORDS = {"recommend", "everyone", "friends", "family", "staff", "friendly", "community", "welcoming", "atmosphere", "team"}
    EXPLORER_WORDS = {"tried", "discovered", "new", "different", "unique", "first", "interesting", "curious", "finally", "hidden gem"}
    
    # Local service category → Default archetype weighting
    CATEGORY_ARCHETYPE_BIAS = {
        # Healthcare - Guardian dominant (trust, safety)
        "healthcare": {"Guardian": 0.45, "Analyzer": 0.25, "Connector": 0.15, "Achiever": 0.10, "Explorer": 0.05},
        
        # Dining - Connector/Explorer dominant (social, discovery)
        "dining": {"Connector": 0.35, "Explorer": 0.30, "Achiever": 0.15, "Guardian": 0.10, "Analyzer": 0.10},
        
        # Automotive - Guardian/Pragmatist dominant (reliability, practicality)
        "auto": {"Guardian": 0.35, "Pragmatist": 0.25, "Achiever": 0.20, "Analyzer": 0.15, "Connector": 0.05},
        
        # Personal services - Connector dominant (relationship)
        "personal": {"Connector": 0.40, "Achiever": 0.25, "Explorer": 0.15, "Guardian": 0.15, "Pragmatist": 0.05},
        
        # Professional - Analyzer/Guardian dominant (expertise, trust)
        "professional": {"Guardian": 0.35, "Analyzer": 0.30, "Achiever": 0.20, "Pragmatist": 0.10, "Connector": 0.05},
        
        # Retail - Explorer/Connector dominant
        "retail": {"Explorer": 0.30, "Connector": 0.25, "Achiever": 0.20, "Guardian": 0.15, "Pragmatist": 0.10},
        
        # Home services - Guardian/Pragmatist dominant
        "home": {"Guardian": 0.35, "Pragmatist": 0.30, "Achiever": 0.20, "Analyzer": 0.10, "Connector": 0.05},
        
        # Entertainment - Explorer/Connector dominant
        "entertainment": {"Explorer": 0.35, "Connector": 0.30, "Achiever": 0.20, "Analyzer": 0.10, "Guardian": 0.05},
        
        # Education - Analyzer/Guardian dominant
        "education": {"Guardian": 0.35, "Analyzer": 0.30, "Connector": 0.20, "Achiever": 0.10, "Explorer": 0.05},
    }
    
    def classify(
        self,
        text: str,
        rating: float,
        category: str,
        review_length: Optional[int] = None,
        has_photos: bool = False,
        has_business_response: bool = False,
        response_time_hours: Optional[float] = None,
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
        
        # Adjust by rating
        if rating >= 4.5:
            base_weights["Connector"] = base_weights.get("Connector", 0.25) + 0.05
            base_weights["Achiever"] = base_weights.get("Achiever", 0.2) + 0.05
        elif rating <= 2:
            base_weights["Analyzer"] = base_weights.get("Analyzer", 0.05) + 0.1
            base_weights["Guardian"] = base_weights.get("Guardian", 0.15) + 0.05
        
        # Adjust by review length
        if review_length is not None:
            if review_length > 500:
                base_weights["Analyzer"] = base_weights.get("Analyzer", 0.05) + 0.1
            elif review_length > 200:
                base_weights["Achiever"] = base_weights.get("Achiever", 0.2) + 0.05
            elif review_length < 50:
                base_weights["Pragmatist"] = base_weights.get("Pragmatist", 0.1) + 0.05
        
        # Photo uploads suggest Explorer/Connector
        if has_photos:
            base_weights["Explorer"] = base_weights.get("Explorer", 0.2) + 0.1
            base_weights["Connector"] = base_weights.get("Connector", 0.25) + 0.05
        
        # Business response engagement
        if has_business_response:
            base_weights["Connector"] = base_weights.get("Connector", 0.25) + 0.05
        
        # Fast response appreciation
        if response_time_hours is not None and response_time_hours < 24:
            base_weights["Achiever"] = base_weights.get("Achiever", 0.2) + 0.05
        
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
        if any(x in cat_lower for x in ["health", "dental", "doctor", "medical", "hospital", "pharmacy", "clinic"]):
            return "healthcare"
        elif any(x in cat_lower for x in ["restaurant", "cafe", "coffee", "food", "dining", "pizza", "bar", "brewery"]):
            return "dining"
        elif any(x in cat_lower for x in ["auto", "car", "mechanic", "tire", "gas"]):
            return "auto"
        elif any(x in cat_lower for x in ["salon", "barber", "spa", "gym", "fitness", "nail", "massage"]):
            return "personal"
        elif any(x in cat_lower for x in ["lawyer", "attorney", "accountant", "bank", "insurance", "real estate"]):
            return "professional"
        elif any(x in cat_lower for x in ["store", "shop", "grocery", "retail", "mall"]):
            return "retail"
        elif any(x in cat_lower for x in ["plumb", "electric", "hvac", "roof", "landscap", "clean", "contractor"]):
            return "home"
        elif any(x in cat_lower for x in ["hotel", "theater", "movie", "museum", "park", "entertainment"]):
            return "entertainment"
        elif any(x in cat_lower for x in ["school", "university", "college", "tutor", "daycare", "education"]):
            return "education"
        
        return "general"


# =============================================================================
# GEOGRAPHIC DENSITY CLASSIFIER
# =============================================================================

class GeographicDensityClassifier:
    """
    Classify locations as urban/suburban/rural based on business density
    and geographic patterns.
    """
    
    # Major metro area centers (lat, long, radius in km)
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
        "San_Jose": (37.3382, -121.8863, 30),
        "Austin": (30.2672, -97.7431, 35),
        "Jacksonville": (30.3322, -81.6557, 40),
        "San_Francisco": (37.7749, -122.4194, 25),
        "Indianapolis": (39.7684, -86.1581, 30),
        "Columbus": (39.9612, -82.9988, 30),
        "Fort_Worth": (32.7555, -97.3308, 35),
        "Charlotte": (35.2271, -80.8431, 30),
        "Seattle": (47.6062, -122.3321, 35),
        "Denver": (39.7392, -104.9903, 40),
        "Washington_DC": (38.9072, -77.0369, 40),
        "Boston": (42.3601, -71.0589, 35),
        "Nashville": (36.1627, -86.7816, 35),
        "Detroit": (42.3314, -83.0458, 40),
        "Portland": (45.5051, -122.6750, 30),
        "Las_Vegas": (36.1699, -115.1398, 35),
        "Miami": (25.7617, -80.1918, 40),
        "Atlanta": (33.7490, -84.3880, 50),
    }
    
    @staticmethod
    def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two points in km."""
        R = 6371  # Earth's radius in km
        
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)
        
        a = math.sin(delta_lat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        return R * c
    
    def classify(self, latitude: float, longitude: float) -> str:
        """
        Classify location as urban/suburban/rural.
        
        Returns: "urban", "suburban", or "rural"
        """
        if latitude is None or longitude is None:
            return "unknown"
        
        # Check distance to major metros
        min_distance = float('inf')
        for metro, (lat, lon, radius) in self.MAJOR_METROS.items():
            distance = self.haversine_distance(latitude, longitude, lat, lon)
            min_distance = min(min_distance, distance)
            
            if distance <= radius * 0.5:  # Within 50% of metro radius = urban
                return "urban"
            elif distance <= radius:  # Within metro radius = suburban
                return "suburban"
        
        # If not near any major metro
        if min_distance <= 100:  # Within 100km of a metro
            return "suburban"
        else:
            return "rural"


# =============================================================================
# CHECKPOINT MANAGEMENT
# =============================================================================

@dataclass
class GoogleLearningCheckpoint:
    """Checkpoint for resumable Google learning."""
    started_at: str = ""
    last_updated: str = ""
    completed_states: List[str] = field(default_factory=list)
    current_state: str = ""
    current_position: int = 0
    
    # Statistics
    total_reviews_processed: int = 0
    total_unique_reviewers: int = 0
    total_unique_businesses: int = 0
    
    # Archetype distribution
    archetype_counts: Dict[str, int] = field(default_factory=dict)
    
    # State statistics
    state_review_counts: Dict[str, int] = field(default_factory=dict)
    
    def save(self):
        """Save checkpoint."""
        self.last_updated = datetime.now().isoformat()
        with open(CHECKPOINT_PATH, 'w') as f:
            json.dump(asdict(self), f, indent=2)
    
    @classmethod
    def load(cls) -> 'GoogleLearningCheckpoint':
        """Load checkpoint."""
        if CHECKPOINT_PATH.exists():
            with open(CHECKPOINT_PATH) as f:
                data = json.load(f)
                return cls(**data)
        return cls(started_at=datetime.now().isoformat())


# =============================================================================
# AGGREGATE COLLECTOR (Location-Aware)
# =============================================================================

@dataclass
class GoogleColdStartAggregator:
    """Collects aggregate statistics for cold-start learning from Google Reviews."""
    
    # State → Archetype counts
    state_archetypes: Dict[str, Dict[str, int]] = field(default_factory=lambda: defaultdict(lambda: defaultdict(int)))
    
    # Region → Archetype counts
    region_archetypes: Dict[str, Dict[str, int]] = field(default_factory=lambda: defaultdict(lambda: defaultdict(int)))
    
    # Local Category → Archetype counts
    category_archetypes: Dict[str, Dict[str, int]] = field(default_factory=lambda: defaultdict(lambda: defaultdict(int)))
    
    # Geographic density → Archetype counts
    density_archetypes: Dict[str, Dict[str, int]] = field(default_factory=lambda: defaultdict(lambda: defaultdict(int)))
    
    # Business → Archetype counts (limited to top businesses)
    business_archetypes: Dict[str, Dict[str, int]] = field(default_factory=lambda: defaultdict(lambda: defaultdict(int)))
    
    # Reviewer → States reviewed
    reviewer_states: Dict[str, Set[str]] = field(default_factory=lambda: defaultdict(set))
    
    # Reviewer → Categories reviewed
    reviewer_categories: Dict[str, Set[str]] = field(default_factory=lambda: defaultdict(set))
    
    # Reviewer → Review count (for lifecycle)
    reviewer_counts: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    
    # Reviewer → Ratings
    reviewer_ratings: Dict[str, List[float]] = field(default_factory=lambda: defaultdict(list))
    
    # Reviewer → Archetype assignments
    reviewer_archetypes: Dict[str, List[str]] = field(default_factory=lambda: defaultdict(list))
    
    # Category co-occurrence
    category_pairs: Dict[Tuple[str, str], int] = field(default_factory=lambda: defaultdict(int))
    
    # State-Category patterns
    state_category_counts: Dict[str, Dict[str, int]] = field(default_factory=lambda: defaultdict(lambda: defaultdict(int)))
    
    # Business response patterns
    response_archetypes: Dict[str, Dict[str, int]] = field(default_factory=lambda: defaultdict(lambda: defaultdict(int)))  # has_response/no_response → archetype
    response_time_archetypes: Dict[str, List[float]] = field(default_factory=lambda: defaultdict(list))  # archetype → response times
    
    # Temporal patterns by state
    state_temporal: Dict[str, Dict[int, int]] = field(default_factory=lambda: defaultdict(lambda: defaultdict(int)))  # state → hour → count
    
    # Price tier patterns
    price_tier_archetypes: Dict[str, Dict[str, int]] = field(default_factory=lambda: defaultdict(lambda: defaultdict(int)))
    
    # Photo patterns
    photo_archetypes: Dict[str, int] = field(default_factory=lambda: defaultdict(int))  # archetype → reviews with photos
    
    # Source statistics
    source_stats: Dict[str, Dict[str, int]] = field(default_factory=lambda: defaultdict(lambda: {"reviews": 0, "unique_reviewers": 0, "unique_businesses": 0}))
    
    def add_review(
        self,
        state: str,
        region: str,
        reviewer_id: str,
        business_id: str,
        category: str,
        archetype: str,
        rating: float,
        density: str = "unknown",
        has_photos: bool = False,
        has_response: bool = False,
        response_time_hours: Optional[float] = None,
        price_tier: Optional[str] = None,
        hour_of_day: Optional[int] = None,
    ) -> None:
        """Add a single review to aggregates."""
        
        # State → Archetype
        self.state_archetypes[state][archetype] += 1
        
        # Region → Archetype
        self.region_archetypes[region][archetype] += 1
        
        # Category → Archetype
        self.category_archetypes[category][archetype] += 1
        
        # Density → Archetype
        self.density_archetypes[density][archetype] += 1
        
        # Business → Archetype (limit storage)
        if business_id and len(self.business_archetypes) < 50000:
            self.business_archetypes[business_id][archetype] += 1
        
        # Reviewer tracking
        self.reviewer_states[reviewer_id].add(state)
        self.reviewer_categories[reviewer_id].add(category)
        self.reviewer_counts[reviewer_id] += 1
        
        # Only track first 5 ratings per reviewer
        if len(self.reviewer_ratings[reviewer_id]) < 5:
            self.reviewer_ratings[reviewer_id].append(rating)
        
        # Only track first 3 archetypes per reviewer
        if len(self.reviewer_archetypes[reviewer_id]) < 3:
            self.reviewer_archetypes[reviewer_id].append(archetype)
        
        # State-Category
        self.state_category_counts[state][category] += 1
        
        # Business response patterns
        response_key = "has_response" if has_response else "no_response"
        self.response_archetypes[response_key][archetype] += 1
        
        if response_time_hours is not None:
            self.response_time_archetypes[archetype].append(min(response_time_hours, 168))  # Cap at 1 week
        
        # Temporal by state
        if hour_of_day is not None:
            self.state_temporal[state][hour_of_day] += 1
        
        # Price tier
        if price_tier:
            self.price_tier_archetypes[archetype][price_tier] += 1
        
        # Photo patterns
        if has_photos:
            self.photo_archetypes[archetype] += 1
        
        # Source stats
        self.source_stats["google"]["reviews"] += 1
    
    def finalize(self) -> None:
        """Compute cross-category pairs after all reviews processed."""
        
        # Only process reviewers with multiple categories
        multi_cat_reviewers = [
            (rid, cats) for rid, cats in self.reviewer_categories.items()
            if len(cats) > 1
        ]
        
        # Sample if too many
        if len(multi_cat_reviewers) > 100000:
            import random
            multi_cat_reviewers = random.sample(multi_cat_reviewers, 100000)
        
        for reviewer_id, categories in multi_cat_reviewers:
            cats = list(categories)
            for i in range(len(cats)):
                for j in range(i + 1, len(cats)):
                    pair = tuple(sorted([cats[i], cats[j]]))
                    self.category_pairs[pair] += 1
        
        # Count unique reviewers and businesses
        self.source_stats["google"]["unique_reviewers"] = len(self.reviewer_counts)
        self.source_stats["google"]["unique_businesses"] = len(self.business_archetypes)


# =============================================================================
# GOOGLE REVIEW PARSER
# =============================================================================

def parse_google_reviews(
    filepath: Path,
    sample_rate: float = 1.0,
    max_reviews: Optional[int] = None,
) -> Generator[Dict, None, None]:
    """
    Parse Google review JSON file (streaming, one-line-per-review).
    """
    state = filepath.stem.replace("review-", "").replace("_", " ").title().replace(" ", "_")
    
    count = 0
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                if max_reviews and count >= max_reviews:
                    break
                
                if sample_rate < 1.0 and np.random.random() > sample_rate:
                    continue
                
                try:
                    # Google reviews are JSON objects, one per line
                    row = json.loads(line.strip())
                    
                    text = row.get('text', '') or ''
                    if len(text) < 10:  # Very short reviews still valid for local
                        text = ""  # But we'll still process for rating patterns
                    
                    rating = float(row.get('rating', 3) or 3)
                    reviewer_id = row.get('user_id', '')
                    business_id = row.get('gmap_id', '')
                    
                    # Parse timestamp
                    timestamp = row.get('time')
                    hour_of_day = None
                    if timestamp:
                        try:
                            # Unix timestamp in milliseconds
                            dt = datetime.fromtimestamp(timestamp / 1000)
                            hour_of_day = dt.hour
                        except:
                            pass
                    
                    # Photos
                    pics = row.get('pics', [])
                    has_photos = bool(pics and len(pics) > 0)
                    
                    # Business response
                    resp = row.get('resp', {})
                    has_response = bool(resp and resp.get('text'))
                    response_time_hours = None
                    if has_response and timestamp and resp.get('time'):
                        try:
                            response_time_hours = (resp['time'] - timestamp) / (1000 * 3600)
                        except:
                            pass
                    
                    yield {
                        "source": "google",
                        "state": state,
                        "reviewer_id": f"goog_{reviewer_id}" if reviewer_id else f"goog_{count}",
                        "business_id": business_id,
                        "text": text,
                        "rating": rating,
                        "has_photos": has_photos,
                        "has_response": has_response,
                        "response_time_hours": response_time_hours,
                        "hour_of_day": hour_of_day,
                    }
                    
                    count += 1
                    
                except json.JSONDecodeError:
                    continue
                    
    except Exception as e:
        logger.warning(f"Error parsing {filepath.name}: {e}")
    
    logger.info(f"  Parsed {count} reviews from {filepath.name}")


def parse_google_metadata(filepath: Path) -> Dict[str, Dict]:
    """
    Parse Google metadata file to get business info.
    
    Returns dict mapping gmap_id → {category, lat, long, price, ...}
    """
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
                        # Extract categories
                        categories = row.get('category', [])
                        if isinstance(categories, str):
                            categories = [categories]
                        
                        # Extract price tier
                        price = row.get('price', '')
                        price_tier = None
                        if price:
                            if price.count('$') == 1:
                                price_tier = "budget"
                            elif price.count('$') == 2:
                                price_tier = "mid_range"
                            elif price.count('$') == 3:
                                price_tier = "premium"
                            elif price.count('$') >= 4:
                                price_tier = "luxury"
                        
                        metadata[gmap_id] = {
                            "name": row.get('name', ''),
                            "categories": categories,
                            "latitude": row.get('latitude'),
                            "longitude": row.get('longitude'),
                            "price_tier": price_tier,
                            "avg_rating": row.get('avg_rating'),
                            "num_reviews": row.get('num_of_reviews', 0),
                        }
                except json.JSONDecodeError:
                    continue
    except Exception as e:
        logger.warning(f"Error parsing metadata {filepath.name}: {e}")
    
    return metadata


def map_to_local_category(categories: List[str]) -> str:
    """Map Google business categories to our local category taxonomy."""
    if not categories:
        return "General"
    
    # Join all categories and search for matches
    all_cats = " ".join(categories).lower()
    
    for keyword, mapped_cat in LOCAL_CATEGORY_MAP.items():
        if keyword in all_cats:
            return mapped_cat
    
    # Default to first category or General
    return categories[0] if categories else "General"


# =============================================================================
# MAIN PROCESSING PIPELINE
# =============================================================================

async def process_google_corpus(
    test_mode: bool = False,
    resume: bool = False,
    states: Optional[List[str]] = None,
    max_per_state: Optional[int] = None,
) -> GoogleColdStartAggregator:
    """Process Google review corpus and collect aggregates."""
    
    # Load or create checkpoint
    if resume:
        checkpoint = GoogleLearningCheckpoint.load()
        logger.info(f"Resuming from checkpoint: {checkpoint.total_reviews_processed} reviews processed")
    else:
        checkpoint = GoogleLearningCheckpoint(started_at=datetime.now().isoformat())
    
    aggregator = GoogleColdStartAggregator()
    classifier = LocalServiceArchetypeClassifier()
    density_classifier = GeographicDensityClassifier()
    
    # Sample rates
    if test_mode:
        sample_rate = 0.001  # 0.1% for test
        max_per_state = max_per_state or 10000
    else:
        sample_rate = 0.01  # 1% sampling (201GB → ~2GB worth)
        max_per_state = max_per_state or 500000
    
    # Find all review files
    review_files = sorted([
        f for f in GOOGLE_DATA_DIR.glob("review-*.json")
    ], key=lambda x: x.stat().st_size, reverse=True)  # Largest first
    
    # Filter by states if specified
    if states:
        states_lower = [s.lower().replace(" ", "_") for s in states]
        review_files = [
            f for f in review_files
            if any(s in f.name.lower() for s in states_lower)
        ]
    
    # Skip completed states if resuming
    if resume and checkpoint.completed_states:
        review_files = [
            f for f in review_files
            if f.stem.replace("review-", "") not in checkpoint.completed_states
        ]
    
    logger.info(f"Processing {len(review_files)} state files")
    logger.info(f"Sample rate: {sample_rate:.1%}, Max per state: {max_per_state}")
    
    total_processed = 0
    
    for file_idx, review_file in enumerate(review_files):
        state_name = review_file.stem.replace("review-", "")
        region = US_REGIONS.get(state_name, "Unknown")
        checkpoint.current_state = state_name
        
        logger.info(f"\n[{file_idx+1}/{len(review_files)}] Processing {state_name} ({region})...")
        
        # Try to load metadata for this state
        metadata_file = GOOGLE_DATA_DIR / f"meta-{state_name}.json"
        metadata = {}
        if metadata_file.exists():
            logger.info(f"  Loading metadata from {metadata_file.name}...")
            metadata = parse_google_metadata(metadata_file)
            logger.info(f"  Loaded metadata for {len(metadata)} businesses")
        
        # Process reviews
        state_count = 0
        for review in parse_google_reviews(review_file, sample_rate, max_per_state):
            # Enrich with metadata
            categories = ["General"]
            latitude = None
            longitude = None
            price_tier = None
            
            if review["business_id"] and review["business_id"] in metadata:
                meta = metadata[review["business_id"]]
                categories = meta.get("categories", ["General"])
                latitude = meta.get("latitude")
                longitude = meta.get("longitude")
                price_tier = meta.get("price_tier")
            
            # Map to local category
            local_category = map_to_local_category(categories)
            
            # Classify geographic density
            density = density_classifier.classify(latitude, longitude) if latitude else "unknown"
            
            # Classify archetype
            archetype, confidence = classifier.classify(
                review["text"],
                review["rating"],
                local_category,
                len(review["text"]) if review["text"] else 0,
                review.get("has_photos", False),
                review.get("has_response", False),
                review.get("response_time_hours"),
            )
            
            # Add to aggregator
            aggregator.add_review(
                state=state_name,
                region=region,
                reviewer_id=review["reviewer_id"],
                business_id=review["business_id"],
                category=local_category,
                archetype=archetype,
                rating=review["rating"],
                density=density,
                has_photos=review.get("has_photos", False),
                has_response=review.get("has_response", False),
                response_time_hours=review.get("response_time_hours"),
                price_tier=price_tier,
                hour_of_day=review.get("hour_of_day"),
            )
            
            state_count += 1
            total_processed += 1
            
            # Progress logging
            if state_count % 50000 == 0:
                logger.info(f"    Progress: {state_count} reviews...")
                checkpoint.total_reviews_processed = total_processed
                checkpoint.save()
        
        # Update checkpoint
        checkpoint.completed_states.append(state_name)
        checkpoint.state_review_counts[state_name] = state_count
        checkpoint.total_reviews_processed = total_processed
        checkpoint.save()
        
        logger.info(f"  Completed {state_name}: {state_count} reviews")
        
        # Clear metadata to free memory
        metadata.clear()
    
    # Finalize
    logger.info("\nFinalizing cross-category analysis...")
    aggregator.finalize()
    
    # Update checkpoint with unique counts
    checkpoint.total_unique_reviewers = len(aggregator.reviewer_counts)
    checkpoint.total_unique_businesses = len(aggregator.business_archetypes)
    
    # Archetype distribution
    global_archetypes = defaultdict(int)
    for state, archetypes in aggregator.state_archetypes.items():
        for arch, count in archetypes.items():
            global_archetypes[arch] += count
    checkpoint.archetype_counts = dict(global_archetypes)
    checkpoint.save()
    
    logger.info(f"\nTotal reviews processed: {total_processed}")
    logger.info(f"Unique reviewers: {len(aggregator.reviewer_counts)}")
    logger.info(f"Unique businesses: {len(aggregator.business_archetypes)}")
    
    return aggregator


# =============================================================================
# GENERATE COLD-START PRIORS
# =============================================================================

def generate_google_priors(aggregator: GoogleColdStartAggregator) -> Dict[str, Any]:
    """Generate cold-start priors from Google aggregates."""
    
    priors = {}
    
    # =========================================================================
    # 1. State → Archetype Priors (UNIQUE TO GOOGLE!)
    # =========================================================================
    state_priors = {}
    for state, archetypes in aggregator.state_archetypes.items():
        total = sum(archetypes.values())
        if total > 0:
            state_priors[state] = {
                arch: round(count / total, 4)
                for arch, count in archetypes.items()
            }
    priors["state_archetype_priors"] = state_priors
    
    # =========================================================================
    # 2. Region → Archetype Priors
    # =========================================================================
    region_priors = {}
    for region, archetypes in aggregator.region_archetypes.items():
        total = sum(archetypes.values())
        if total > 0:
            region_priors[region] = {
                arch: round(count / total, 4)
                for arch, count in archetypes.items()
            }
    priors["region_archetype_priors"] = region_priors
    
    # =========================================================================
    # 3. Local Category → Archetype Priors (UNIQUE TO GOOGLE!)
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
    # 4. Geographic Density → Archetype Priors (UNIQUE TO GOOGLE!)
    # =========================================================================
    density_priors = {}
    for density, archetypes in aggregator.density_archetypes.items():
        total = sum(archetypes.values())
        if total > 0:
            density_priors[density] = {
                arch: round(count / total, 4)
                for arch, count in archetypes.items()
            }
    priors["density_archetype_priors"] = density_priors
    
    # =========================================================================
    # 5. Business Response Impact (UNIQUE TO GOOGLE!)
    # =========================================================================
    response_priors = {}
    for response_type, archetypes in aggregator.response_archetypes.items():
        total = sum(archetypes.values())
        if total > 0:
            response_priors[response_type] = {
                arch: round(count / total, 4)
                for arch, count in archetypes.items()
            }
    priors["business_response_archetypes"] = response_priors
    
    # Average response time by archetype
    response_times = {}
    for archetype, times in aggregator.response_time_archetypes.items():
        if times:
            response_times[archetype] = {
                "avg_response_hours": round(np.mean(times), 2),
                "median_response_hours": round(np.median(times), 2),
                "count": len(times),
            }
    priors["response_time_by_archetype"] = response_times
    
    # =========================================================================
    # 6. State-Category Preferences (UNIQUE TO GOOGLE!)
    # =========================================================================
    state_category_priors = {}
    for state, categories in aggregator.state_category_counts.items():
        total = sum(categories.values())
        if total > 100:  # Only states with enough data
            top_cats = sorted(categories.items(), key=lambda x: x[1], reverse=True)[:10]
            state_category_priors[state] = {
                cat: round(count / total, 4)
                for cat, count in top_cats
            }
    priors["state_category_preferences"] = state_category_priors
    
    # =========================================================================
    # 7. Cross-Category Lift
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
    # 8. Reviewer Lifecycle Patterns
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
    # 9. Price Tier Preferences
    # =========================================================================
    price_priors = {}
    for archetype, tiers in aggregator.price_tier_archetypes.items():
        total = sum(tiers.values())
        if total > 0:
            price_priors[archetype] = {
                tier: round(count / total, 4)
                for tier, count in tiers.items()
            }
    priors["price_tier_preferences"] = price_priors
    
    # =========================================================================
    # 10. Photo Upload Patterns (UNIQUE TO GOOGLE!)
    # =========================================================================
    total_photos = sum(aggregator.photo_archetypes.values())
    if total_photos > 0:
        priors["photo_upload_by_archetype"] = {
            arch: round(count / total_photos, 4)
            for arch, count in aggregator.photo_archetypes.items()
        }
    
    # =========================================================================
    # 11. Multi-State Reviewers (UNIQUE TO GOOGLE!)
    # =========================================================================
    multi_state = {
        "single_state": {"count": 0, "archetypes": defaultdict(int)},
        "multi_state": {"count": 0, "archetypes": defaultdict(int)},
        "traveler": {"count": 0, "archetypes": defaultdict(int)},
    }
    
    for reviewer_id, states in aggregator.reviewer_states.items():
        archetypes = aggregator.reviewer_archetypes.get(reviewer_id, [])
        if not archetypes:
            continue
        
        arch_counts = defaultdict(int)
        for arch in archetypes:
            arch_counts[arch] += 1
        dominant_arch = max(arch_counts, key=arch_counts.get)
        
        num_states = len(states)
        if num_states == 1:
            segment = "single_state"
        elif num_states <= 3:
            segment = "multi_state"
        else:
            segment = "traveler"
        
        multi_state[segment]["count"] += 1
        multi_state[segment]["archetypes"][dominant_arch] += 1
    
    multi_state_priors = {}
    for segment, data in multi_state.items():
        total = sum(data["archetypes"].values())
        if total > 0:
            multi_state_priors[segment] = {
                "count": data["count"],
                "archetype_distribution": {
                    arch: round(count / total, 4)
                    for arch, count in data["archetypes"].items()
                }
            }
    priors["multi_state_patterns"] = multi_state_priors
    
    # =========================================================================
    # 12. Source Statistics
    # =========================================================================
    priors["source_statistics"] = dict(aggregator.source_stats)
    
    # =========================================================================
    # 13. Global Archetype Distribution
    # =========================================================================
    global_archetypes = defaultdict(int)
    for state, archetypes in aggregator.state_archetypes.items():
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

def merge_with_existing_priors(google_priors: Dict, existing_path: Path) -> Dict:
    """
    Merge Google priors with existing cold-start priors.
    
    Google priors ADD NEW dimensions (state, region, density) without replacing existing.
    """
    if not existing_path.exists():
        return google_priors
    
    with open(existing_path) as f:
        existing = json.load(f)
    
    merged = existing.copy()
    
    # =========================================================================
    # ADD NEW LOCATION-BASED PRIORS (Google-exclusive)
    # =========================================================================
    
    # State priors (NEW)
    merged["state_archetype_priors"] = google_priors.get("state_archetype_priors", {})
    
    # Region priors (NEW)
    merged["region_archetype_priors"] = google_priors.get("region_archetype_priors", {})
    
    # Density priors (NEW)
    merged["density_archetype_priors"] = google_priors.get("density_archetype_priors", {})
    
    # Business response patterns (NEW)
    merged["business_response_archetypes"] = google_priors.get("business_response_archetypes", {})
    merged["response_time_by_archetype"] = google_priors.get("response_time_by_archetype", {})
    
    # State-category preferences (NEW)
    merged["state_category_preferences"] = google_priors.get("state_category_preferences", {})
    
    # Photo upload patterns (NEW)
    merged["photo_upload_by_archetype"] = google_priors.get("photo_upload_by_archetype", {})
    
    # Multi-state patterns (NEW)
    merged["multi_state_patterns"] = google_priors.get("multi_state_patterns", {})
    
    # =========================================================================
    # MERGE OVERLAPPING PRIORS
    # =========================================================================
    
    # Merge category priors (Google has local services, Amazon has products)
    existing_cats = existing.get("category_archetype_priors", {})
    google_cats = google_priors.get("category_archetype_priors", {})
    merged_cats = existing_cats.copy()
    
    for cat, priors in google_cats.items():
        if cat not in merged_cats:
            merged_cats[cat] = priors
        else:
            # Average if overlapping
            for arch, prob in priors.items():
                existing_prob = merged_cats[cat].get(arch, 0)
                merged_cats[cat][arch] = round((existing_prob + prob) / 2, 4)
    
    merged["category_archetype_priors"] = merged_cats
    
    # Merge cross-category lift (union)
    existing_lift = existing.get("cross_category_lift", {})
    google_lift = google_priors.get("cross_category_lift", {})
    
    for cat, targets in google_lift.items():
        if cat not in existing_lift:
            existing_lift[cat] = {}
        existing_lift[cat].update(targets)
    merged["cross_category_lift"] = existing_lift
    
    # Merge lifecycle (weighted by review count)
    existing_lifecycle = existing.get("reviewer_lifecycle", {})
    google_lifecycle = google_priors.get("reviewer_lifecycle", {})
    
    for segment in ["new_reviewer", "casual", "engaged", "power_user"]:
        if segment in google_lifecycle and segment in existing_lifecycle:
            existing_count = existing_lifecycle[segment].get("count", 0)
            google_count = google_lifecycle[segment].get("count", 0)
            total_count = existing_count + google_count
            
            if total_count > 0:
                existing_dist = existing_lifecycle[segment].get("archetype_distribution", {})
                google_dist = google_lifecycle[segment].get("archetype_distribution", {})
                
                merged_dist = {}
                all_archs = set(existing_dist.keys()) | set(google_dist.keys())
                for arch in all_archs:
                    e_val = existing_dist.get(arch, 0) * existing_count
                    g_val = google_dist.get(arch, 0) * google_count
                    merged_dist[arch] = round((e_val + g_val) / total_count, 4)
                
                merged["reviewer_lifecycle"][segment] = {
                    "count": total_count,
                    "archetype_distribution": merged_dist,
                }
        elif segment in google_lifecycle:
            merged["reviewer_lifecycle"][segment] = google_lifecycle[segment]
    
    # Merge price tier preferences
    existing_price = existing.get("price_tier_preferences", {})
    google_price = google_priors.get("price_tier_preferences", {})
    
    for arch in set(existing_price.keys()) | set(google_price.keys()):
        if arch in existing_price and arch in google_price:
            merged_tiers = {}
            for tier in ["budget", "mid_range", "premium", "luxury"]:
                e_val = existing_price[arch].get(tier, 0)
                g_val = google_price[arch].get(tier, 0)
                merged_tiers[tier] = round((e_val + g_val) / 2, 4)
            merged["price_tier_preferences"][arch] = merged_tiers
        elif arch in google_price:
            merged["price_tier_preferences"][arch] = google_price[arch]
    
    # Merge source statistics
    existing_stats = existing.get("source_statistics", {})
    google_stats = google_priors.get("source_statistics", {})
    merged_stats = existing_stats.copy()
    merged_stats.update(google_stats)
    merged["source_statistics"] = merged_stats
    
    # Merge global distribution (weighted)
    existing_global = existing.get("global_archetype_distribution", {})
    google_global = google_priors.get("global_archetype_distribution", {})
    
    existing_total = sum(s.get("reviews", 0) for s in existing.get("source_statistics", {}).values())
    google_total = sum(s.get("reviews", 0) for s in google_priors.get("source_statistics", {}).values())
    total_weight = existing_total + google_total
    
    if total_weight > 0:
        merged_global = {}
        all_archs = set(existing_global.keys()) | set(google_global.keys())
        for arch in all_archs:
            e_val = existing_global.get(arch, 0) * existing_total
            g_val = google_global.get(arch, 0) * google_total
            merged_global[arch] = round((e_val + g_val) / total_weight, 4)
        merged["global_archetype_distribution"] = merged_global
    
    return merged


# =============================================================================
# MAIN
# =============================================================================

async def main():
    parser = argparse.ArgumentParser(description="Google Reviews Learning Pipeline")
    parser.add_argument("--test", action="store_true", help="Test mode (sample only)")
    parser.add_argument("--resume", action="store_true", help="Resume from checkpoint")
    parser.add_argument("--states", nargs="+", help="Specific states to process")
    parser.add_argument("--max-per-state", type=int, help="Max reviews per state")
    args = parser.parse_args()
    
    start_time = datetime.now()
    
    print("\n" + "=" * 70)
    print("ADAM GOOGLE REVIEWS LOCATION-AWARE LEARNING PIPELINE")
    print("=" * 70)
    print(f"\nStarted at: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Mode: {'TEST (sampled)' if args.test else 'FULL PROCESSING'}")
    if args.states:
        print(f"States: {', '.join(args.states)}")
    print()
    
    # =========================================================================
    # PROCESS GOOGLE REVIEWS
    # =========================================================================
    
    logger.info("Starting Google review processing...")
    aggregator = await process_google_corpus(
        test_mode=args.test,
        resume=args.resume,
        states=args.states,
        max_per_state=args.max_per_state,
    )
    
    # =========================================================================
    # GENERATE GOOGLE PRIORS
    # =========================================================================
    
    logger.info("\nGenerating Google cold-start priors...")
    google_priors = generate_google_priors(aggregator)
    
    # Save Google-specific priors
    with open(GOOGLE_PRIORS_PATH, 'w') as f:
        json.dump(google_priors, f, indent=2, default=str)
    
    google_size = GOOGLE_PRIORS_PATH.stat().st_size
    logger.info(f"✓ Google priors saved: {GOOGLE_PRIORS_PATH}")
    logger.info(f"  Size: {google_size / 1024:.1f} KB")
    
    # =========================================================================
    # MERGE WITH EXISTING PRIORS
    # =========================================================================
    
    logger.info("\nMerging with existing cold-start priors...")
    merged_priors = merge_with_existing_priors(google_priors, MERGED_PRIORS_PATH)
    
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
    print("GOOGLE LEARNING COMPLETE")
    print("=" * 70)
    
    print(f"\nProcessing time: {duration:.1f} seconds ({duration/60:.1f} minutes)")
    
    print(f"\nStates learned: {len(google_priors.get('state_archetype_priors', {}))}")
    print(f"Regions learned: {len(google_priors.get('region_archetype_priors', {}))}")
    print(f"Local categories learned: {len(google_priors.get('category_archetype_priors', {}))}")
    print(f"Density types: {len(google_priors.get('density_archetype_priors', {}))}")
    
    print("\nGlobal Archetype Distribution:")
    for arch, pct in google_priors.get("global_archetype_distribution", {}).items():
        print(f"  • {arch}: {pct:.1%}")
    
    print(f"\nGoogle priors file: {GOOGLE_PRIORS_PATH}")
    print(f"Merged priors file: {MERGED_PRIORS_PATH}")
    
    print("\n✓ Pipeline complete!")
    print("\nUNIQUE LOCATION INTELLIGENCE EXTRACTED:")
    print("  • State-level archetype patterns (51 states)")
    print("  • Regional preferences (5 US regions)")
    print("  • Urban/suburban/rural patterns")
    print("  • Local service category priors (healthcare, dining, auto, etc.)")
    print("  • Business response effectiveness")
    print("  • Multi-state traveler patterns")
    print("\nNext steps:")
    print("  1. Run learning strengthening: python scripts/run_learning_strengthening.py")
    print("  2. Update LearnedPriorsService with location methods")
    print("  3. Verify: python -c \"from adam.core.learning.learned_priors_integration import get_priors_summary; print(get_priors_summary())\"")


if __name__ == "__main__":
    asyncio.run(main())
