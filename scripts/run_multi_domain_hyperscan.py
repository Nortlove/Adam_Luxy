#!/usr/bin/env python3
"""
ADAM MULTI-DOMAIN REVIEW PROCESSING PIPELINE
=============================================

Extends the 82-Framework Hyperscan analysis to multiple review domains:
- Yelp (businesses, restaurants, services)
- Steam (gaming)
- Sephora (beauty/cosmetics)
- Hotels, Airlines, Restaurants, Cars, Movies, Podcasts, etc.

DEEP-DIVE DOMAINS (extended analysis):
- Sephora: Demographics → archetype correlation, ingredient psychology
- Steam: Playtime → engagement psychology, genre → personality
- Yelp: Cross-category behavior, geographic psychology, social patterns

Author: ADAM Platform
"""

import argparse
import csv
import gc
import gzip
import json
import logging
import os
import sqlite3
import sys
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Callable
import numpy as np

import hyperscan

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# =============================================================================
# LOGGING SETUP
# =============================================================================
log_dir = Path(__file__).parent.parent / "logs"
log_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(log_dir / 'multi_domain_hyperscan.log')
    ]
)
logger = logging.getLogger(__name__)


# =============================================================================
# IMPORT 82-FRAMEWORK PATTERNS
# =============================================================================
from adam.intelligence.psychological_frameworks import (
    BIG_FIVE_MARKERS,
    NEED_FOR_COGNITION_MARKERS,
    SELF_MONITORING_MARKERS,
    DECISION_STYLE_MARKERS,
    UNCERTAINTY_TOLERANCE_MARKERS,
    REGULATORY_FOCUS_MARKERS,
    CONSTRUAL_LEVEL_MARKERS,
    TEMPORAL_ORIENTATION_MARKERS,
    APPROACH_AVOIDANCE_MARKERS,
    SELF_DETERMINATION_MARKERS,
    SOCIAL_PROOF_MARKERS,
    AUTHORITY_MARKERS,
    SCARCITY_MARKERS,
    RECIPROCITY_MARKERS,
    COMMITMENT_MARKERS,
    LIKING_MARKERS,
    LOSS_AVERSION_MARKERS,
    ANCHORING_MARKERS,
    FRAMING_MARKERS,
    WANTING_LIKING_MARKERS,
    AUTOMATIC_EVALUATION_MARKERS,
    EMBODIED_COGNITION_MARKERS,
    ATTENTION_MARKERS,
    PROCESSING_FLUENCY_MARKERS,
    MIMETIC_DESIRE_MARKERS,
    EVOLUTIONARY_MOTIVES_MARKERS,
    SOCIAL_COMPARISON_MARKERS,
    IDENTITY_MARKERS,
    BELONGINGNESS_MARKERS,
    DUAL_PROCESS_MARKERS,
    ELM_MARKERS,
    DECISION_FATIGUE_MARKERS,
    CHOICE_OVERLOAD_MARKERS,
    COGNITIVE_LOAD_MARKERS,
    LIWC_MARKERS,
    ABSOLUTIST_MARKERS,
    TEMPORAL_LINGUISTIC_MARKERS,
    CERTAINTY_MARKERS,
    EMOTIONAL_INTENSITY_MARKERS,
)


# =============================================================================
# DOMAIN-SPECIFIC EXTENSIONS
# =============================================================================

# Sephora: Beauty-specific psychological patterns
BEAUTY_PSYCHOLOGY_MARKERS = {
    "self_enhancement": {
        "patterns": [
            r"\b(transform|glow|radiant|beautiful|stunning|gorgeous|flawless)\b",
            r"\b(confidence|self-esteem|feel amazing|love myself)\b",
            r"\b(compliments|noticed|attention|heads turn)\b",
        ],
        "weight": 1.2
    },
    "perfectionism": {
        "patterns": [
            r"\b(perfect|flawless|no imperfections|completely smooth)\b",
            r"\b(every pore|every detail|precise|exact)\b",
            r"\b(obsessed with|must have|cant live without)\b",
        ],
        "weight": 1.1
    },
    "social_validation": {
        "patterns": [
            r"\b(influencer|tiktok|instagram|viral|trending)\b",
            r"\b(everyone loves|must-have|cult favorite)\b",
            r"\b(recommended by|celeb|professional)\b",
        ],
        "weight": 1.0
    },
    "ingredient_conscious": {
        "patterns": [
            r"\b(clean|natural|organic|vegan|cruelty.free)\b",
            r"\b(no parabens|no sulfates|hypoallergenic|dermatologist)\b",
            r"\b(retinol|vitamin c|hyaluronic|niacinamide|peptide)\b",
        ],
        "weight": 1.1
    },
    "routine_oriented": {
        "patterns": [
            r"\b(routine|regimen|daily|every night|every morning)\b",
            r"\b(step \d|first step|last step|layer)\b",
            r"\b(holy grail|staple|repurchase|backup)\b",
        ],
        "weight": 1.0
    }
}

# Steam: Gaming-specific psychological patterns
GAMING_PSYCHOLOGY_MARKERS = {
    "achievement_driven": {
        "patterns": [
            r"\b(achievement|trophy|100%|completionist|all endings)\b",
            r"\b(challenge|difficulty|hard mode|impossible)\b",
            r"\b(beat|conquer|master|dominate)\b",
        ],
        "weight": 1.2
    },
    "immersion_seeker": {
        "patterns": [
            r"\b(immersive|atmosphere|world|lore|story)\b",
            r"\b(hours flew|lost track|couldnt stop)\b",
            r"\b(beautiful|stunning graphics|breathtaking)\b",
        ],
        "weight": 1.1
    },
    "social_gamer": {
        "patterns": [
            r"\b(friends|multiplayer|co.op|together|community)\b",
            r"\b(guild|clan|team|squad)\b",
            r"\b(pvp|competitive|ranked|esports)\b",
        ],
        "weight": 1.0
    },
    "value_conscious": {
        "patterns": [
            r"\b(worth|value|hours per dollar|content)\b",
            r"\b(sale|discount|cheap|free to play)\b",
            r"\b(dlc|expansion|season pass)\b",
        ],
        "weight": 1.0
    },
    "nostalgia_seeker": {
        "patterns": [
            r"\b(nostalgia|childhood|classic|retro|remake)\b",
            r"\b(remember|back when|years ago|old school)\b",
            r"\b(sequel|franchise|series)\b",
        ],
        "weight": 1.1
    },
    "early_adopter": {
        "patterns": [
            r"\b(early access|beta|alpha|preview)\b",
            r"\b(potential|will be|looking forward)\b",
            r"\b(devs|updates|patches|roadmap)\b",
        ],
        "weight": 1.2
    }
}

# Yelp: Service/Experience psychological patterns
SERVICE_PSYCHOLOGY_MARKERS = {
    "experience_focused": {
        "patterns": [
            r"\b(experience|atmosphere|ambiance|vibe|feel)\b",
            r"\b(memorable|special|unforgettable|amazing time)\b",
            r"\b(recommend|must visit|hidden gem)\b",
        ],
        "weight": 1.1
    },
    "quality_focused": {
        "patterns": [
            r"\b(quality|authentic|fresh|real|genuine)\b",
            r"\b(best|top|excellent|outstanding|superb)\b",
            r"\b(consistent|reliable|always good)\b",
        ],
        "weight": 1.0
    },
    "service_sensitive": {
        "patterns": [
            r"\b(service|staff|waiter|server|friendly)\b",
            r"\b(attentive|helpful|rude|ignored|slow)\b",
            r"\b(manager|owner|handled|resolved)\b",
        ],
        "weight": 1.2
    },
    "price_value_conscious": {
        "patterns": [
            r"\b(price|expensive|cheap|affordable|worth)\b",
            r"\b(portion|size|value|deal|overpriced)\b",
            r"\b(tip|bill|total|cost)\b",
        ],
        "weight": 1.0
    },
    "social_context": {
        "patterns": [
            r"\b(date|family|friends|kids|group|party)\b",
            r"\b(occasion|birthday|anniversary|celebration)\b",
            r"\b(romantic|casual|business|quick)\b",
        ],
        "weight": 1.1
    },
    "local_loyalty": {
        "patterns": [
            r"\b(local|neighborhood|regular|always come|frequent)\b",
            r"\b(years|since \d|longtime|been coming)\b",
            r"\b(spot|place|go-to|favorite)\b",
        ],
        "weight": 1.0
    }
}

# Airline: Travel psychology patterns
AIRLINE_PSYCHOLOGY_MARKERS = {
    "comfort_seeker": {
        "patterns": [
            r"\b(comfortable|legroom|seat|recline|spacious)\b",
            r"\b(sleep|rest|relax|peaceful|quiet)\b",
            r"\b(pillow|blanket|amenity|kit)\b",
        ],
        "weight": 1.1
    },
    "service_oriented": {
        "patterns": [
            r"\b(crew|attendant|staff|friendly|helpful)\b",
            r"\b(attentive|professional|courteous|rude)\b",
            r"\b(service|assistance|accommodate)\b",
        ],
        "weight": 1.2
    },
    "reliability_focused": {
        "patterns": [
            r"\b(delay|on.?time|late|cancelled|punctual)\b",
            r"\b(connection|layover|missed|rebooked)\b",
            r"\b(reliable|consistent|always|never)\b",
        ],
        "weight": 1.3
    },
    "value_conscious": {
        "patterns": [
            r"\b(price|cheap|expensive|value|worth)\b",
            r"\b(budget|affordable|overpriced|fee)\b",
            r"\b(upgrade|class|premium|economy)\b",
        ],
        "weight": 1.0
    },
    "food_beverage": {
        "patterns": [
            r"\b(food|meal|snack|drink|beverage)\b",
            r"\b(catering|dining|menu|quality)\b",
            r"\b(hungry|delicious|terrible|bland)\b",
        ],
        "weight": 0.9
    },
    "entertainment_tech": {
        "patterns": [
            r"\b(entertainment|wifi|screen|movie|music)\b",
            r"\b(charging|usb|power|app|booking)\b",
            r"\b(modern|outdated|technology)\b",
        ],
        "weight": 0.8
    },
    "safety_trust": {
        "patterns": [
            r"\b(safe|safety|trust|secure|confident)\b",
            r"\b(turbulence|landing|takeoff|smooth)\b",
            r"\b(maintenance|clean|hygiene|covid)\b",
        ],
        "weight": 1.2
    }
}

# Automotive: Car buying psychology patterns
AUTOMOTIVE_PSYCHOLOGY_MARKERS = {
    "performance_seeker": {
        "patterns": [
            r"\b(power|engine|horsepower|acceleration|fast)\b",
            r"\b(handling|steering|responsive|sporty)\b",
            r"\b(performance|speed|turbo|0-60)\b",
        ],
        "weight": 1.2
    },
    "reliability_focused": {
        "patterns": [
            r"\b(reliable|dependable|last|durable|maintenance)\b",
            r"\b(problem|issue|repair|warranty|dealer)\b",
            r"\b(miles|years|still running|no problems)\b",
        ],
        "weight": 1.3
    },
    "comfort_luxury": {
        "patterns": [
            r"\b(comfortable|luxury|premium|leather|heated)\b",
            r"\b(quiet|smooth|ride|interior|cabin)\b",
            r"\b(features|technology|infotainment)\b",
        ],
        "weight": 1.1
    },
    "value_conscious": {
        "patterns": [
            r"\b(price|value|affordable|expensive|mpg)\b",
            r"\b(fuel|gas|economy|efficient|hybrid)\b",
            r"\b(cost|ownership|insurance|depreciation)\b",
        ],
        "weight": 1.0
    },
    "safety_family": {
        "patterns": [
            r"\b(safe|safety|crash|airbag|rating)\b",
            r"\b(family|kids|car seat|space|room)\b",
            r"\b(cargo|trunk|storage|practical)\b",
        ],
        "weight": 1.2
    },
    "brand_loyalty": {
        "patterns": [
            r"\b(always bought|loyal|fan|love this brand)\b",
            r"\b(switched from|compared to|better than)\b",
            r"\b(reputation|trust|known for)\b",
        ],
        "weight": 1.1
    },
    "style_image": {
        "patterns": [
            r"\b(look|style|design|beautiful|ugly)\b",
            r"\b(color|exterior|interior|modern)\b",
            r"\b(compliments|attention|head turner)\b",
        ],
        "weight": 0.9
    }
}

# Podcast: Audio content psychology patterns
PODCAST_PSYCHOLOGY_MARKERS = {
    "content_depth": {
        "patterns": [
            r"\b(informative|educational|learn|insightful)\b",
            r"\b(research|expert|knowledge|deep dive)\b",
            r"\b(interesting|fascinating|thought.?provoking)\b",
        ],
        "weight": 1.2
    },
    "entertainment_value": {
        "patterns": [
            r"\b(funny|hilarious|entertaining|laugh)\b",
            r"\b(enjoy|love|favorite|binge)\b",
            r"\b(engaging|captivating|addicted|hooked)\b",
        ],
        "weight": 1.1
    },
    "host_connection": {
        "patterns": [
            r"\b(host|hosts|personality|chemistry)\b",
            r"\b(voice|authentic|genuine|relatable)\b",
            r"\b(like a friend|conversation|connection)\b",
        ],
        "weight": 1.2
    },
    "production_quality": {
        "patterns": [
            r"\b(audio|sound|quality|production)\b",
            r"\b(editing|ads|sponsors|interruption)\b",
            r"\b(professional|amateur|polished)\b",
        ],
        "weight": 0.9
    },
    "routine_habit": {
        "patterns": [
            r"\b(every (week|day|episode)|routine|habit)\b",
            r"\b(commute|workout|walk|drive)\b",
            r"\b(subscribe|notification|download)\b",
        ],
        "weight": 1.0
    },
    "topic_niche": {
        "patterns": [
            r"\b(niche|specific|unique|only podcast)\b",
            r"\b(topic|subject|coverage|perspective)\b",
            r"\b(finally|needed|been looking for)\b",
        ],
        "weight": 1.1
    }
}

# Movie/Entertainment: Film review psychology patterns  
MOVIE_PSYCHOLOGY_MARKERS = {
    "story_narrative": {
        "patterns": [
            r"\b(story|plot|narrative|script|writing)\b",
            r"\b(character|development|arc|journey)\b",
            r"\b(twist|ending|predictable|surprising)\b",
        ],
        "weight": 1.2
    },
    "emotional_impact": {
        "patterns": [
            r"\b(cried|laughed|scared|moved|emotional)\b",
            r"\b(feel|feeling|felt|heart|touching)\b",
            r"\b(powerful|intense|gripping|boring)\b",
        ],
        "weight": 1.3
    },
    "visual_spectacle": {
        "patterns": [
            r"\b(visual|cinematography|beautiful|stunning)\b",
            r"\b(effects|cgi|action|scenes)\b",
            r"\b(director|directed|shot|camera)\b",
        ],
        "weight": 1.0
    },
    "acting_performance": {
        "patterns": [
            r"\b(acting|actor|actress|performance|cast)\b",
            r"\b(played|role|convincing|believable)\b",
            r"\b(oscar|award|deserves|nomination)\b",
        ],
        "weight": 1.1
    },
    "critic_perspective": {
        "patterns": [
            r"\b(masterpiece|classic|must.?see|essential)\b",
            r"\b(overrated|underrated|disappointing|waste)\b",
            r"\b(recommend|avoid|skip|watch)\b",
        ],
        "weight": 1.0
    },
    "genre_expectations": {
        "patterns": [
            r"\b(horror|comedy|drama|action|thriller)\b",
            r"\b(genre|fans|typical|cliche|trope)\b",
            r"\b(original|fresh|same old|different)\b",
        ],
        "weight": 0.9
    }
}

# BH Photo / Electronics: Tech purchase psychology
ELECTRONICS_PSYCHOLOGY_MARKERS = {
    "tech_enthusiast": {
        "patterns": [
            r"\b(specs|specification|feature|capability)\b",
            r"\b(upgrade|latest|new model|generation)\b",
            r"\b(professional|pro|advanced|serious)\b",
        ],
        "weight": 1.2
    },
    "quality_focused": {
        "patterns": [
            r"\b(quality|build|construction|durable)\b",
            r"\b(premium|well.?made|solid|sturdy)\b",
            r"\b(cheap|flimsy|plastic|broke)\b",
        ],
        "weight": 1.1
    },
    "value_seeker": {
        "patterns": [
            r"\b(price|value|worth|deal|bargain)\b",
            r"\b(expensive|overpriced|affordable|budget)\b",
            r"\b(compare|alternative|option|choice)\b",
        ],
        "weight": 1.0
    },
    "service_experience": {
        "patterns": [
            r"\b(shipping|delivery|fast|quick|arrived)\b",
            r"\b(customer service|support|helpful|return)\b",
            r"\b(packaging|condition|damaged|perfect)\b",
        ],
        "weight": 1.1
    },
    "research_driven": {
        "patterns": [
            r"\b(research|review|compared|read about)\b",
            r"\b(finally|decided|after|considering)\b",
            r"\b(recommend|suggestion|advice)\b",
        ],
        "weight": 1.0
    }
}

# Netflix/Streaming: App review psychology
STREAMING_PSYCHOLOGY_MARKERS = {
    "content_library": {
        "patterns": [
            r"\b(content|library|selection|variety)\b",
            r"\b(shows|movies|series|original)\b",
            r"\b(missing|removed|added|new)\b",
        ],
        "weight": 1.2
    },
    "app_usability": {
        "patterns": [
            r"\b(app|interface|ui|design|navigate)\b",
            r"\b(easy|difficult|confusing|intuitive)\b",
            r"\b(update|version|bug|crash|fix)\b",
        ],
        "weight": 1.1
    },
    "streaming_quality": {
        "patterns": [
            r"\b(quality|resolution|hd|4k|buffer)\b",
            r"\b(loading|slow|fast|stream|lag)\b",
            r"\b(download|offline|data|wifi)\b",
        ],
        "weight": 1.0
    },
    "subscription_value": {
        "patterns": [
            r"\b(subscription|price|cost|worth|ads)\b",
            r"\b(cancel|renew|free trial|plan)\b",
            r"\b(expensive|cheap|value|money)\b",
        ],
        "weight": 1.1
    }
}


# =============================================================================
# DOMAIN CONFIGURATION
# =============================================================================

@dataclass
class DomainConfig:
    """Configuration for each review domain."""
    name: str
    folder: str
    file_pattern: str
    format: str  # csv, json, jsonl, sqlite, npz
    text_field: str
    rating_field: Optional[str]
    id_field: Optional[str]
    metadata_fields: List[str]
    extra_markers: Optional[Dict] = None
    deep_dive: bool = False
    processor: Optional[str] = None  # Custom processor name


DOMAIN_CONFIGS = {
    # DEEP-DIVE DOMAINS (Priority) - Already completed
    "sephora": DomainConfig(
        name="Sephora Beauty",
        folder="sephora_reviews",
        file_pattern="reviews_*.csv",
        format="csv",
        text_field="review_text",
        rating_field="rating",
        id_field="author_id",
        metadata_fields=["product_id", "product_name", "brand_name", "price_usd", 
                        "skin_tone", "eye_color", "skin_type", "hair_color",
                        "is_recommended", "helpfulness"],
        extra_markers=BEAUTY_PSYCHOLOGY_MARKERS,
        deep_dive=True,
        processor="sephora"
    ),
    "steam": DomainConfig(
        name="Steam Gaming",
        folder="steam_gamers_game_reviews",
        file_pattern="steam_reviews.csv",
        format="csv",
        text_field="review",
        rating_field="recommended",
        id_field="review_id",
        metadata_fields=["app_id", "app_name", "language", "votes_helpful", "votes_funny",
                        "steam_purchase", "received_for_free", "written_during_early_access",
                        "author.steamid", "author.num_games_owned", "author.num_reviews",
                        "author.playtime_forever", "author.playtime_last_two_weeks"],
        extra_markers=GAMING_PSYCHOLOGY_MARKERS,
        deep_dive=True,
        processor="steam"
    ),
    "yelp": DomainConfig(
        name="Yelp Reviews",
        folder="yelp_reviews",
        file_pattern="yelp_academic_dataset_review.json",
        format="jsonl",
        text_field="text",
        rating_field="stars",
        id_field="review_id",
        metadata_fields=["user_id", "business_id", "useful", "funny", "cool", "date"],
        extra_markers=SERVICE_PSYCHOLOGY_MARKERS,
        deep_dive=True,
        processor="yelp"
    ),
    
    # NEW DOMAINS WITH BRAND-CUSTOMER ALIGNMENT
    "airline": DomainConfig(
        name="Airline Reviews",
        folder="airline_reviews",
        file_pattern="Airline Company Reviews.csv",
        format="csv",
        text_field="Full_review",
        rating_field="Rating",
        id_field=None,
        metadata_fields=["Airline_Name", "Reviewer_Country", "Seat_Rating", 
                        "Cabin_staff_service_Rating", "Food_Beverages_Rating",
                        "Value_Rating", "Verified"],
        extra_markers=AIRLINE_PSYCHOLOGY_MARKERS,
        deep_dive=True,
        processor="airline"
    ),
    "car_edmunds": DomainConfig(
        name="Edmunds Car Reviews",
        folder="edmonds_reviews_by_car_company",
        file_pattern="Scraped_Car_Review_*.csv",
        format="csv",
        text_field="Review",
        rating_field="Rating",
        id_field=None,
        metadata_fields=["Vehicle_Title", "Review_Title", "Author_Name", "Review_Date"],
        extra_markers=AUTOMOTIVE_PSYCHOLOGY_MARKERS,
        deep_dive=True,
        processor="automotive"
    ),
    "bhphoto": DomainConfig(
        name="BH Photo Reviews",
        folder="bh-photo_reviews",
        file_pattern="bhphotovideo.csv",
        format="csv",
        text_field="text",  # Verified from header: text column
        rating_field="serviceRating",
        id_field="reviewID",
        metadata_fields=["title", "userLocation", "countryName", "region"],
        extra_markers=ELECTRONICS_PSYCHOLOGY_MARKERS,
        deep_dive=True,
        processor="electronics"
    ),
    "netflix": DomainConfig(
        name="Netflix App Reviews",
        folder="netflix_reviews",
        file_pattern="netflix_reviews.csv",
        format="csv",
        text_field="content",
        rating_field="score",
        id_field="reviewId",
        metadata_fields=["userName", "thumbsUpCount", "at"],
        extra_markers=STREAMING_PSYCHOLOGY_MARKERS,
        deep_dive=True,
        processor="streaming"
    ),
    "podcast": DomainConfig(
        name="Podcast Reviews",
        folder="podcast_reviews",
        file_pattern="reviews.json",
        format="jsonl",
        text_field="content",
        rating_field="rating",
        id_field="author_id",
        metadata_fields=["podcast_id", "title", "created_at"],
        extra_markers=PODCAST_PSYCHOLOGY_MARKERS,
        deep_dive=True,
        processor="podcast"
    ),
    "rotten_tomatoes": DomainConfig(
        name="Rotten Tomatoes Movie Reviews",
        folder="rotten_tomatoe_movie_review",
        file_pattern="rotten_tomatoes_movie_reviews.csv",
        format="csv",
        text_field="reviewText",
        rating_field="scoreSentiment",
        id_field="reviewId",
        metadata_fields=["id", "criticName", "isTopCritic", "originalScore", "publicatioName"],
        extra_markers=MOVIE_PSYCHOLOGY_MARKERS,
        deep_dive=True,
        processor="movie"
    ),
}


# =============================================================================
# HYPERSCAN ANALYZER (Adapted from Amazon script)
# =============================================================================

class MultiDomainHyperscanAnalyzer:
    """
    Hyperscan-based analyzer for multi-domain review processing.
    Compiles all 82 frameworks + domain-specific patterns into single DB.
    """
    
    def __init__(self, domain_config: Optional[DomainConfig] = None):
        self.domain_config = domain_config
        self.patterns = []
        self.pattern_ids = []
        self.pattern_metadata = {}  # id -> (framework, dimension, weight)
        self.db = None
        self.scratch = None
        
        self._build_pattern_database()
        self._compile_database()
    
    def _add_patterns_from_dict(self, markers: Dict, framework_name: str):
        """Add patterns from a marker dictionary (handles nested structures)."""
        for dimension, config in markers.items():
            if isinstance(config, dict):
                # Handle nested structure from psychological_frameworks.py
                # Structure: {dimension: {high_markers: {subdim: [patterns]}, low_markers: {...}}}
                weight = config.get("weight", 1.0)
                
                # Direct patterns array (for domain-specific markers)
                if "patterns" in config:
                    patterns = config["patterns"]
                    for pattern in patterns:
                        pattern_id = len(self.patterns)
                        self.patterns.append(pattern.encode('utf-8'))
                        self.pattern_ids.append(pattern_id)
                        self.pattern_metadata[pattern_id] = {
                            "framework": framework_name,
                            "dimension": dimension,
                            "weight": weight
                        }
                
                # Nested high/low markers
                for marker_type in ["high_markers", "low_markers"]:
                    if marker_type in config:
                        subdims = config[marker_type]
                        if isinstance(subdims, dict):
                            for subdim, patterns in subdims.items():
                                if isinstance(patterns, list):
                                    for pattern in patterns:
                                        pattern_id = len(self.patterns)
                                        self.patterns.append(pattern.encode('utf-8'))
                                        self.pattern_ids.append(pattern_id)
                                        self.pattern_metadata[pattern_id] = {
                                            "framework": framework_name,
                                            "dimension": f"{dimension}.{marker_type}.{subdim}",
                                            "weight": weight if weight != 1.0 else (1.0 if marker_type == "high_markers" else 0.8)
                                        }
                
                # Direct sub-dimensions (e.g., regulatory_focus has promotion/prevention directly)
                for key, value in config.items():
                    if key not in ["description", "application", "high_markers", "low_markers", "weight", "patterns"]:
                        if isinstance(value, dict):
                            for subkey, patterns in value.items():
                                if isinstance(patterns, list):
                                    for pattern in patterns:
                                        pattern_id = len(self.patterns)
                                        self.patterns.append(pattern.encode('utf-8'))
                                        self.pattern_ids.append(pattern_id)
                                        self.pattern_metadata[pattern_id] = {
                                            "framework": framework_name,
                                            "dimension": f"{dimension}.{key}.{subkey}",
                                            "weight": 1.0
                                        }
                        elif isinstance(value, list):
                            for pattern in value:
                                pattern_id = len(self.patterns)
                                self.patterns.append(pattern.encode('utf-8'))
                                self.pattern_ids.append(pattern_id)
                                self.pattern_metadata[pattern_id] = {
                                    "framework": framework_name,
                                    "dimension": f"{dimension}.{key}",
                                    "weight": 1.0
                                }
            elif isinstance(config, list):
                # Simple list of patterns
                for pattern in config:
                    pattern_id = len(self.patterns)
                    self.patterns.append(pattern.encode('utf-8'))
                    self.pattern_ids.append(pattern_id)
                    self.pattern_metadata[pattern_id] = {
                        "framework": framework_name,
                        "dimension": dimension,
                        "weight": 1.0
                    }
    
    def _build_pattern_database(self):
        """Build combined pattern database from all frameworks."""
        logger.info("Building pattern database...")
        
        # Core 82 frameworks
        framework_sets = [
            (BIG_FIVE_MARKERS, "big_five"),
            (NEED_FOR_COGNITION_MARKERS, "need_for_cognition"),
            (SELF_MONITORING_MARKERS, "self_monitoring"),
            (DECISION_STYLE_MARKERS, "decision_style"),
            (UNCERTAINTY_TOLERANCE_MARKERS, "uncertainty_tolerance"),
            (REGULATORY_FOCUS_MARKERS, "regulatory_focus"),
            (CONSTRUAL_LEVEL_MARKERS, "construal_level"),
            (TEMPORAL_ORIENTATION_MARKERS, "temporal_orientation"),
            (APPROACH_AVOIDANCE_MARKERS, "approach_avoidance"),
            (SELF_DETERMINATION_MARKERS, "self_determination"),
            (SOCIAL_PROOF_MARKERS, "social_proof"),
            (AUTHORITY_MARKERS, "authority"),
            (SCARCITY_MARKERS, "scarcity"),
            (RECIPROCITY_MARKERS, "reciprocity"),
            (COMMITMENT_MARKERS, "commitment"),
            (LIKING_MARKERS, "liking"),
            (LOSS_AVERSION_MARKERS, "loss_aversion"),
            (ANCHORING_MARKERS, "anchoring"),
            (FRAMING_MARKERS, "framing"),
            (WANTING_LIKING_MARKERS, "wanting_liking"),
            (AUTOMATIC_EVALUATION_MARKERS, "automatic_evaluation"),
            (EMBODIED_COGNITION_MARKERS, "embodied_cognition"),
            (ATTENTION_MARKERS, "attention"),
            (PROCESSING_FLUENCY_MARKERS, "processing_fluency"),
            (MIMETIC_DESIRE_MARKERS, "mimetic_desire"),
            (EVOLUTIONARY_MOTIVES_MARKERS, "evolutionary_motives"),
            (SOCIAL_COMPARISON_MARKERS, "social_comparison"),
            (IDENTITY_MARKERS, "identity"),
            (BELONGINGNESS_MARKERS, "belongingness"),
            (DUAL_PROCESS_MARKERS, "dual_process"),
            (ELM_MARKERS, "elm"),
            (DECISION_FATIGUE_MARKERS, "decision_fatigue"),
            (CHOICE_OVERLOAD_MARKERS, "choice_overload"),
            (COGNITIVE_LOAD_MARKERS, "cognitive_load"),
            (LIWC_MARKERS, "liwc"),
            (ABSOLUTIST_MARKERS, "absolutist"),
            (TEMPORAL_LINGUISTIC_MARKERS, "temporal_linguistic"),
            (CERTAINTY_MARKERS, "certainty"),
            (EMOTIONAL_INTENSITY_MARKERS, "emotional_intensity"),
        ]
        
        for markers, name in framework_sets:
            self._add_patterns_from_dict(markers, name)
        
        # Add domain-specific patterns if configured
        if self.domain_config and self.domain_config.extra_markers:
            self._add_patterns_from_dict(
                self.domain_config.extra_markers,
                f"domain_{self.domain_config.name.lower().replace(' ', '_')}"
            )
        
        logger.info(f"Built pattern database: {len(self.patterns)} patterns")
    
    def _compile_database(self):
        """Compile patterns into Hyperscan database."""
        logger.info(f"Compiling {len(self.patterns)} patterns into Hyperscan database...")
        start = time.time()
        
        flags = [hyperscan.HS_FLAG_CASELESS | hyperscan.HS_FLAG_UTF8] * len(self.patterns)
        
        self.db = hyperscan.Database()
        self.db.compile(
            expressions=self.patterns,
            ids=self.pattern_ids,
            flags=flags
        )
        self.scratch = hyperscan.Scratch(self.db)
        
        elapsed = time.time() - start
        logger.info(f"Hyperscan database compiled in {elapsed:.2f}s with {len(self.patterns)} patterns")
    
    def analyze(self, text: str) -> Dict[str, Any]:
        """Analyze text and return psychological profile."""
        if not text or len(text) < 10:
            return {}
        
        matches = []
        
        def on_match(pattern_id, start, end, flags, context):
            matches.append(pattern_id)
            return None
        
        try:
            self.db.scan(text.lower().encode('utf-8'), match_event_handler=on_match, scratch=self.scratch)
        except Exception as e:
            return {}
        
        if not matches:
            return {}
        
        # Aggregate by framework and dimension
        framework_scores = defaultdict(float)
        dimension_scores = defaultdict(float)
        
        for pattern_id in matches:
            meta = self.pattern_metadata.get(pattern_id, {})
            framework = meta.get("framework", "unknown")
            dimension = meta.get("dimension", "unknown")
            weight = meta.get("weight", 1.0)
            
            framework_scores[framework] += weight
            dimension_scores[f"{framework}.{dimension}"] += weight
        
        # Compute archetype scores
        archetype_scores = self._compute_archetypes(framework_scores, dimension_scores)
        
        return {
            "framework_scores": dict(framework_scores),
            "dimension_scores": dict(dimension_scores),
            "archetype_scores": archetype_scores,
            "total_matches": len(matches),
            "primary_archetype": max(archetype_scores, key=archetype_scores.get) if archetype_scores else "unknown"
        }
    
    def _compute_archetypes(self, framework_scores: Dict, dimension_scores: Dict) -> Dict[str, float]:
        """Compute archetype probabilities from framework scores."""
        archetypes = {
            "achiever": 0.0,
            "explorer": 0.0,
            "connector": 0.0,
            "guardian": 0.0,
            "pragmatist": 0.0,
        }
        
        # Achiever: high achievement, promotion focus, extraversion
        archetypes["achiever"] = (
            framework_scores.get("regulatory_focus", 0) * 0.3 +
            framework_scores.get("big_five", 0) * 0.2 +
            framework_scores.get("self_determination", 0) * 0.2 +
            framework_scores.get("social_comparison", 0) * 0.3
        )
        
        # Explorer: high openness, novelty seeking, curiosity
        archetypes["explorer"] = (
            framework_scores.get("attention", 0) * 0.3 +
            framework_scores.get("approach_avoidance", 0) * 0.2 +
            framework_scores.get("need_for_cognition", 0) * 0.3 +
            framework_scores.get("uncertainty_tolerance", 0) * 0.2
        )
        
        # Connector: high agreeableness, social, belonging
        archetypes["connector"] = (
            framework_scores.get("belongingness", 0) * 0.3 +
            framework_scores.get("social_proof", 0) * 0.3 +
            framework_scores.get("mimetic_desire", 0) * 0.2 +
            framework_scores.get("liking", 0) * 0.2
        )
        
        # Guardian: high conscientiousness, prevention focus, risk averse
        archetypes["guardian"] = (
            framework_scores.get("loss_aversion", 0) * 0.3 +
            framework_scores.get("certainty", 0) * 0.2 +
            framework_scores.get("commitment", 0) * 0.3 +
            framework_scores.get("authority", 0) * 0.2
        )
        
        # Pragmatist: high value focus, rational decision
        archetypes["pragmatist"] = (
            framework_scores.get("decision_style", 0) * 0.3 +
            framework_scores.get("framing", 0) * 0.2 +
            framework_scores.get("anchoring", 0) * 0.3 +
            framework_scores.get("dual_process", 0) * 0.2
        )
        
        # Normalize
        total = sum(archetypes.values())
        if total > 0:
            archetypes = {k: v / total for k, v in archetypes.items()}
        
        return archetypes


# =============================================================================
# DOMAIN-SPECIFIC PROCESSORS
# =============================================================================

class SephoraProcessor:
    """Deep-dive processor for Sephora beauty reviews with brand positioning analysis."""
    
    def __init__(self, product_lookup: Dict[str, Dict] = None, analyzer=None):
        self.product_lookup = product_lookup or {}
        self.analyzer = analyzer
        self.brand_positioning_profiles = defaultdict(lambda: {
            "framework_scores": defaultdict(float),
            "archetype_scores": defaultdict(float),
            "product_count": 0,
            "highlights_analyzed": 0,
            "categories": defaultdict(int),
        })
    
    @staticmethod
    def extract_demographics(row: Dict) -> Dict[str, Any]:
        """Extract demographic information for psychological correlation."""
        return {
            "skin_tone": row.get("skin_tone", ""),
            "eye_color": row.get("eye_color", ""),
            "skin_type": row.get("skin_type", ""),
            "hair_color": row.get("hair_color", ""),
        }
    
    def analyze_brand_positioning(self, product_info: Dict) -> Dict[str, Any]:
        """
        Analyze product metadata to understand brand's psychological positioning.
        This is the BRAND side of brand-customer alignment.
        """
        if not self.analyzer:
            return {}
        
        brand = product_info.get("brand_name", "Unknown")
        
        # Combine all text that represents brand positioning
        positioning_text_parts = []
        
        # Product name often contains positioning keywords
        product_name = product_info.get("product_name", "")
        if product_name:
            positioning_text_parts.append(product_name)
        
        # Highlights are key positioning statements
        highlights = product_info.get("highlights", "")
        if highlights:
            # Parse highlights list format: "['item1', 'item2']"
            try:
                if highlights.startswith("["):
                    import ast
                    highlight_list = ast.literal_eval(highlights)
                    positioning_text_parts.extend(highlight_list)
                else:
                    positioning_text_parts.append(highlights)
            except:
                positioning_text_parts.append(str(highlights))
        
        # Categories indicate positioning
        for cat_field in ["primary_category", "secondary_category", "tertiary_category"]:
            cat = product_info.get(cat_field, "")
            if cat:
                positioning_text_parts.append(cat)
                self.brand_positioning_profiles[brand]["categories"][cat] += 1
        
        # Analyze combined positioning text
        positioning_text = " ".join(positioning_text_parts)
        if len(positioning_text) > 10:
            result = self.analyzer.analyze(positioning_text)
            if result:
                self.brand_positioning_profiles[brand]["product_count"] += 1
                self.brand_positioning_profiles[brand]["highlights_analyzed"] += 1 if highlights else 0
                
                for fw, score in result.get("framework_scores", {}).items():
                    self.brand_positioning_profiles[brand]["framework_scores"][fw] += score
                
                for arch, score in result.get("archetype_scores", {}).items():
                    self.brand_positioning_profiles[brand]["archetype_scores"][arch] += score
                
                return result
        
        return {}
    
    def get_normalized_brand_positioning(self) -> Dict[str, Dict]:
        """Get normalized brand positioning profiles for alignment calculation."""
        normalized = {}
        for brand, profile in self.brand_positioning_profiles.items():
            n = profile["product_count"]
            if n > 0:
                normalized[brand] = {
                    "framework_scores": {k: v/n for k, v in profile["framework_scores"].items()},
                    "archetype_scores": {k: v/n for k, v in profile["archetype_scores"].items()},
                    "product_count": n,
                    "highlights_analyzed": profile["highlights_analyzed"],
                    "top_categories": dict(sorted(profile["categories"].items(), key=lambda x: -x[1])[:5]),
                }
        return normalized
    
    @staticmethod
    def compute_demographic_archetype_correlation(
        demographics: Dict,
        archetype_scores: Dict
    ) -> Dict[str, float]:
        """Compute how demographics correlate with archetypes (for learning)."""
        return {
            "demographic_profile": demographics,
            "archetype_affinity": archetype_scores,
        }
    
    @staticmethod
    def analyze_ingredient_psychology(product_name: str, review_text: str) -> Dict[str, float]:
        """Analyze psychological drivers related to ingredients."""
        ingredient_psychology = defaultdict(float)
        
        # Science/efficacy seekers
        science_patterns = ["retinol", "vitamin c", "hyaluronic", "niacinamide", "peptide", "collagen"]
        for pattern in science_patterns:
            if pattern in review_text.lower() or pattern in product_name.lower():
                ingredient_psychology["science_seeker"] += 1.0
        
        # Clean/natural seekers
        clean_patterns = ["clean", "natural", "organic", "vegan", "cruelty-free", "no paraben"]
        for pattern in clean_patterns:
            if pattern in review_text.lower():
                ingredient_psychology["clean_beauty_seeker"] += 1.0
        
        # Luxury/prestige seekers
        luxury_patterns = ["luxurious", "premium", "high-end", "prestige", "exclusive"]
        for pattern in luxury_patterns:
            if pattern in review_text.lower():
                ingredient_psychology["luxury_seeker"] += 1.0
        
        return dict(ingredient_psychology)
    
    @staticmethod
    def compute_brand_customer_alignment(
        brand_positioning: Dict[str, float],
        customer_profile: Dict[str, float]
    ) -> float:
        """
        Compute alignment score between brand's positioning and customer's psychology.
        High alignment = brand speaks to the right psychological drivers for this customer type.
        """
        if not brand_positioning or not customer_profile:
            return 0.0
        
        # Compute cosine similarity between archetype vectors
        common_keys = set(brand_positioning.keys()) & set(customer_profile.keys())
        if not common_keys:
            return 0.0
        
        dot_product = sum(brand_positioning.get(k, 0) * customer_profile.get(k, 0) for k in common_keys)
        brand_mag = sum(v**2 for v in brand_positioning.values()) ** 0.5
        customer_mag = sum(v**2 for v in customer_profile.values()) ** 0.5
        
        if brand_mag == 0 or customer_mag == 0:
            return 0.0
        
        return dot_product / (brand_mag * customer_mag)


class SteamProcessor:
    """Deep-dive processor for Steam gaming reviews."""
    
    @staticmethod
    def extract_engagement_metrics(row: Dict) -> Dict[str, Any]:
        """Extract engagement metrics for psychological profiling."""
        try:
            playtime = float(row.get("author.playtime_forever", 0) or 0)
            playtime_recent = float(row.get("author.playtime_last_two_weeks", 0) or 0)
            games_owned = int(row.get("author.num_games_owned", 0) or 0)
            num_reviews = int(row.get("author.num_reviews", 0) or 0)
        except (ValueError, TypeError):
            playtime = playtime_recent = 0
            games_owned = num_reviews = 0
        
        return {
            "playtime_hours": playtime / 60,  # Convert minutes to hours
            "recent_playtime_hours": playtime_recent / 60,
            "games_owned": games_owned,
            "num_reviews": num_reviews,
            "early_access": row.get("written_during_early_access", "False") == "True",
            "free_copy": row.get("received_for_free", "False") == "True",
            "purchased": row.get("steam_purchase", "False") == "True",
        }
    
    @staticmethod
    def compute_gamer_archetype(engagement: Dict, archetype_scores: Dict) -> Dict[str, float]:
        """Compute gamer-specific archetype extensions."""
        gamer_archetypes = {
            "hardcore_gamer": 0.0,
            "casual_gamer": 0.0,
            "collector": 0.0,
            "early_adopter": 0.0,
            "social_gamer": 0.0,
            "value_hunter": 0.0,
        }
        
        # Hardcore: High playtime, few reviews (focused)
        if engagement["playtime_hours"] > 100:
            gamer_archetypes["hardcore_gamer"] += 0.5
        if engagement["playtime_hours"] > 500:
            gamer_archetypes["hardcore_gamer"] += 0.5
        
        # Collector: Many games owned
        if engagement["games_owned"] > 100:
            gamer_archetypes["collector"] += 0.5
        if engagement["games_owned"] > 500:
            gamer_archetypes["collector"] += 0.5
        
        # Early adopter: Early access reviews
        if engagement["early_access"]:
            gamer_archetypes["early_adopter"] += 1.0
        
        # Value hunter: Got free copy, or many games (sale hunter)
        if engagement["free_copy"]:
            gamer_archetypes["value_hunter"] += 0.5
        if engagement["games_owned"] > 200:
            gamer_archetypes["value_hunter"] += 0.3
        
        # Casual: Low playtime
        if engagement["playtime_hours"] < 20:
            gamer_archetypes["casual_gamer"] += 0.7
        
        # Normalize
        total = sum(gamer_archetypes.values())
        if total > 0:
            gamer_archetypes = {k: v / total for k, v in gamer_archetypes.items()}
        
        return gamer_archetypes


class YelpProcessor:
    """Deep-dive processor for Yelp reviews with business context."""
    
    def __init__(self, business_lookup: Dict[str, Dict] = None, user_lookup: Dict[str, Dict] = None):
        self.business_lookup = business_lookup or {}
        self.user_lookup = user_lookup or {}
    
    def enrich_review(self, review: Dict) -> Dict:
        """Enrich review with business and user context."""
        business_id = review.get("business_id", "")
        user_id = review.get("user_id", "")
        
        enriched = dict(review)
        
        if business_id in self.business_lookup:
            biz = self.business_lookup[business_id]
            enriched["_business_name"] = biz.get("name", "")
            enriched["_business_categories"] = biz.get("categories", "")
            enriched["_business_city"] = biz.get("city", "")
            enriched["_business_state"] = biz.get("state", "")
            enriched["_business_stars"] = biz.get("stars", 0)
        
        if user_id in self.user_lookup:
            user = self.user_lookup[user_id]
            enriched["_user_review_count"] = user.get("review_count", 0)
            enriched["_user_yelping_since"] = user.get("yelping_since", "")
            enriched["_user_elite"] = len(user.get("elite", "").split(",")) if user.get("elite") else 0
        
        return enriched
    
    @staticmethod
    def compute_reviewer_influence(user_data: Dict) -> Dict[str, float]:
        """Compute reviewer influence metrics."""
        influence = {
            "experience_level": 0.0,
            "elite_status": 0.0,
            "community_engagement": 0.0,
        }
        
        review_count = user_data.get("_user_review_count", 0)
        if review_count > 10:
            influence["experience_level"] = min(1.0, review_count / 100)
        
        elite_years = user_data.get("_user_elite", 0)
        if elite_years > 0:
            influence["elite_status"] = min(1.0, elite_years / 5)
        
        return influence


class AirlineProcessor:
    """Deep-dive processor for airline reviews with service quality analysis."""
    
    def __init__(self, airline_metadata: Dict[str, Dict] = None, analyzer=None):
        self.airline_metadata = airline_metadata or {}
        self.analyzer = analyzer
        self.brand_positioning_profiles = defaultdict(lambda: {
            "framework_scores": defaultdict(float),
            "archetype_scores": defaultdict(float),
            "review_count": 0,
            "avg_rating": 0.0,
            "service_ratings": defaultdict(list),
        })
    
    def extract_service_ratings(self, row: Dict) -> Dict[str, Any]:
        """Extract detailed service ratings for correlation analysis."""
        ratings = {}
        for field in ["Seat_Rating", "Cabin_staff_service_Rating", "Food_Beverages_Rating",
                     "Inflight_Rating", "Ground_service_Rating", "Value_Rating"]:
            try:
                val = row.get(field, "")
                if val and val != "":
                    ratings[field.replace("_Rating", "").lower()] = float(val)
            except (ValueError, TypeError):
                pass
        return ratings
    
    def update_brand_profile(self, airline: str, result: Dict, row: Dict):
        """Update brand positioning profile from review analysis."""
        if not result:
            return
        
        self.brand_positioning_profiles[airline]["review_count"] += 1
        
        for fw, score in result.get("framework_scores", {}).items():
            self.brand_positioning_profiles[airline]["framework_scores"][fw] += score
        
        for arch, score in result.get("archetype_scores", {}).items():
            self.brand_positioning_profiles[airline]["archetype_scores"][arch] += score
        
        # Track service ratings
        try:
            rating = float(row.get("Rating", 0) or 0)
            self.brand_positioning_profiles[airline]["avg_rating"] += rating
        except:
            pass
        
        service_ratings = self.extract_service_ratings(row)
        for service, rating in service_ratings.items():
            self.brand_positioning_profiles[airline]["service_ratings"][service].append(rating)
    
    def get_normalized_brand_positioning(self) -> Dict[str, Dict]:
        """Get normalized airline brand positioning profiles."""
        normalized = {}
        for airline, profile in self.brand_positioning_profiles.items():
            n = profile["review_count"]
            if n > 0:
                # Average service ratings
                avg_service_ratings = {}
                for service, ratings in profile["service_ratings"].items():
                    if ratings:
                        avg_service_ratings[service] = sum(ratings) / len(ratings)
                
                normalized[airline] = {
                    "framework_scores": {k: v/n for k, v in profile["framework_scores"].items()},
                    "archetype_scores": {k: v/n for k, v in profile["archetype_scores"].items()},
                    "review_count": n,
                    "avg_overall_rating": profile["avg_rating"] / n,
                    "avg_service_ratings": avg_service_ratings,
                }
        return normalized


class AutomotiveProcessor:
    """Deep-dive processor for automotive reviews with brand/model analysis."""
    
    def __init__(self, analyzer=None):
        self.analyzer = analyzer
        self.brand_positioning_profiles = defaultdict(lambda: {
            "framework_scores": defaultdict(float),
            "archetype_scores": defaultdict(float),
            "vehicle_count": 0,
            "models": defaultdict(int),
            "avg_rating": 0.0,
        })
    
    @staticmethod
    def extract_brand_from_filename(filename: str) -> str:
        """Extract car brand from filename like Scraped_Car_Review_ford.csv"""
        # Extract brand from filename
        name = Path(filename).stem
        if "Scraped_Car_Review_" in name:
            brand = name.replace("Scraped_Car_Review_", "")
            return brand.title().replace("-", " ")  # land-rover -> Land Rover
        return "Unknown"
    
    @staticmethod
    def extract_vehicle_info(row: Dict) -> Dict[str, Any]:
        """Extract vehicle information from review."""
        vehicle_title = row.get("Vehicle_Title", "")
        # Parse "2006 Ford Mustang Coupe GT Premium 2dr Coupe (4.6L 8cyl 5M)"
        parts = vehicle_title.split()
        info = {
            "year": parts[0] if parts and parts[0].isdigit() else "",
            "make": parts[1] if len(parts) > 1 else "",
            "model": " ".join(parts[2:4]) if len(parts) > 2 else "",
            "full_title": vehicle_title,
        }
        return info
    
    def update_brand_profile(self, brand: str, result: Dict, row: Dict):
        """Update brand positioning profile."""
        if not result:
            return
        
        self.brand_positioning_profiles[brand]["vehicle_count"] += 1
        
        for fw, score in result.get("framework_scores", {}).items():
            self.brand_positioning_profiles[brand]["framework_scores"][fw] += score
        
        for arch, score in result.get("archetype_scores", {}).items():
            self.brand_positioning_profiles[brand]["archetype_scores"][arch] += score
        
        # Track model popularity
        vehicle_info = self.extract_vehicle_info(row)
        if vehicle_info["model"]:
            self.brand_positioning_profiles[brand]["models"][vehicle_info["model"]] += 1
        
        try:
            rating = float(row.get("Rating", 0) or 0)
            self.brand_positioning_profiles[brand]["avg_rating"] += rating
        except:
            pass
    
    def get_normalized_brand_positioning(self) -> Dict[str, Dict]:
        """Get normalized automotive brand positioning profiles."""
        normalized = {}
        for brand, profile in self.brand_positioning_profiles.items():
            n = profile["vehicle_count"]
            if n > 0:
                normalized[brand] = {
                    "framework_scores": {k: v/n for k, v in profile["framework_scores"].items()},
                    "archetype_scores": {k: v/n for k, v in profile["archetype_scores"].items()},
                    "vehicle_count": n,
                    "avg_rating": profile["avg_rating"] / n,
                    "top_models": dict(sorted(profile["models"].items(), key=lambda x: -x[1])[:10]),
                }
        return normalized


class PodcastProcessor:
    """Deep-dive processor for podcast reviews with show analysis."""
    
    def __init__(self, podcast_lookup: Dict[str, Dict] = None, analyzer=None):
        self.podcast_lookup = podcast_lookup or {}
        self.analyzer = analyzer
        self.brand_positioning_profiles = defaultdict(lambda: {
            "framework_scores": defaultdict(float),
            "archetype_scores": defaultdict(float),
            "review_count": 0,
            "avg_rating": 0.0,
            "podcast_info": {},
        })
    
    def enrich_review(self, review: Dict) -> Dict:
        """Enrich review with podcast metadata."""
        podcast_id = review.get("podcast_id", "")
        enriched = dict(review)
        
        if podcast_id in self.podcast_lookup:
            podcast = self.podcast_lookup[podcast_id]
            enriched["_podcast_title"] = podcast.get("title", "")
            enriched["_podcast_author"] = podcast.get("author", "")
            enriched["_podcast_description"] = podcast.get("description", "")
            enriched["_podcast_avg_rating"] = podcast.get("average_rating", 0)
        
        return enriched
    
    def analyze_podcast_positioning(self, podcast_info: Dict) -> Dict[str, Any]:
        """Analyze podcast metadata for brand positioning."""
        if not self.analyzer:
            return {}
        
        # Combine title and description for positioning analysis
        text_parts = []
        if podcast_info.get("title"):
            text_parts.append(podcast_info["title"])
        if podcast_info.get("description"):
            text_parts.append(podcast_info["description"])
        
        positioning_text = " ".join(text_parts)
        if len(positioning_text) > 10:
            return self.analyzer.analyze(positioning_text)
        return {}
    
    def update_brand_profile(self, podcast_id: str, result: Dict, row: Dict):
        """Update podcast brand positioning profile."""
        if not result:
            return
        
        self.brand_positioning_profiles[podcast_id]["review_count"] += 1
        
        for fw, score in result.get("framework_scores", {}).items():
            self.brand_positioning_profiles[podcast_id]["framework_scores"][fw] += score
        
        for arch, score in result.get("archetype_scores", {}).items():
            self.brand_positioning_profiles[podcast_id]["archetype_scores"][arch] += score
        
        try:
            rating = float(row.get("rating", 0) or 0)
            self.brand_positioning_profiles[podcast_id]["avg_rating"] += rating
        except:
            pass
        
        # Store podcast info on first encounter
        if podcast_id in self.podcast_lookup and not self.brand_positioning_profiles[podcast_id]["podcast_info"]:
            self.brand_positioning_profiles[podcast_id]["podcast_info"] = self.podcast_lookup[podcast_id]
    
    def get_normalized_brand_positioning(self) -> Dict[str, Dict]:
        """Get normalized podcast brand positioning profiles."""
        normalized = {}
        for podcast_id, profile in self.brand_positioning_profiles.items():
            n = profile["review_count"]
            if n >= 10:  # Only include podcasts with meaningful review counts
                normalized[podcast_id] = {
                    "framework_scores": {k: v/n for k, v in profile["framework_scores"].items()},
                    "archetype_scores": {k: v/n for k, v in profile["archetype_scores"].items()},
                    "review_count": n,
                    "avg_rating": profile["avg_rating"] / n,
                    "podcast_title": profile["podcast_info"].get("title", "Unknown"),
                    "podcast_author": profile["podcast_info"].get("author", ""),
                }
        return normalized


class MovieProcessor:
    """Deep-dive processor for movie reviews with film analysis."""
    
    def __init__(self, movie_lookup: Dict[str, Dict] = None, analyzer=None):
        self.movie_lookup = movie_lookup or {}
        self.analyzer = analyzer
        self.brand_positioning_profiles = defaultdict(lambda: {
            "framework_scores": defaultdict(float),
            "archetype_scores": defaultdict(float),
            "review_count": 0,
            "positive_count": 0,
            "negative_count": 0,
            "movie_info": {},
        })
    
    def analyze_movie_positioning(self, movie_info: Dict) -> Dict[str, Any]:
        """Analyze movie metadata for brand positioning."""
        if not self.analyzer:
            return {}
        
        # Use title and genre for positioning
        text_parts = []
        if movie_info.get("title"):
            text_parts.append(movie_info["title"])
        if movie_info.get("genre"):
            text_parts.append(movie_info["genre"])
        
        positioning_text = " ".join(text_parts)
        if len(positioning_text) > 5:
            return self.analyzer.analyze(positioning_text)
        return {}
    
    def update_brand_profile(self, movie_id: str, result: Dict, row: Dict):
        """Update movie brand positioning profile."""
        if not result:
            return
        
        self.brand_positioning_profiles[movie_id]["review_count"] += 1
        
        for fw, score in result.get("framework_scores", {}).items():
            self.brand_positioning_profiles[movie_id]["framework_scores"][fw] += score
        
        for arch, score in result.get("archetype_scores", {}).items():
            self.brand_positioning_profiles[movie_id]["archetype_scores"][arch] += score
        
        # Track sentiment
        sentiment = row.get("scoreSentiment", "")
        if sentiment == "POSITIVE":
            self.brand_positioning_profiles[movie_id]["positive_count"] += 1
        elif sentiment == "NEGATIVE":
            self.brand_positioning_profiles[movie_id]["negative_count"] += 1
        
        # Store movie info
        if movie_id in self.movie_lookup and not self.brand_positioning_profiles[movie_id]["movie_info"]:
            self.brand_positioning_profiles[movie_id]["movie_info"] = self.movie_lookup[movie_id]
    
    def get_normalized_brand_positioning(self) -> Dict[str, Dict]:
        """Get normalized movie brand positioning profiles."""
        normalized = {}
        for movie_id, profile in self.brand_positioning_profiles.items():
            n = profile["review_count"]
            if n >= 5:  # Only include movies with enough reviews
                total_sentiment = profile["positive_count"] + profile["negative_count"]
                normalized[movie_id] = {
                    "framework_scores": {k: v/n for k, v in profile["framework_scores"].items()},
                    "archetype_scores": {k: v/n for k, v in profile["archetype_scores"].items()},
                    "review_count": n,
                    "positive_rate": profile["positive_count"] / total_sentiment if total_sentiment > 0 else 0,
                    "movie_title": profile["movie_info"].get("title", movie_id),
                    "genre": profile["movie_info"].get("genre", ""),
                    "tomato_meter": profile["movie_info"].get("tomatoMeter", ""),
                }
        return normalized


class GenericBrandProcessor:
    """Generic processor for domains without specialized logic."""
    
    def __init__(self, brand_field: str = "brand_name", analyzer=None):
        self.brand_field = brand_field
        self.analyzer = analyzer
        self.brand_positioning_profiles = defaultdict(lambda: {
            "framework_scores": defaultdict(float),
            "archetype_scores": defaultdict(float),
            "review_count": 0,
            "avg_rating": 0.0,
        })
    
    def update_brand_profile(self, brand: str, result: Dict, row: Dict, rating_field: str = "rating"):
        """Update generic brand positioning profile."""
        if not result or not brand:
            return
        
        self.brand_positioning_profiles[brand]["review_count"] += 1
        
        for fw, score in result.get("framework_scores", {}).items():
            self.brand_positioning_profiles[brand]["framework_scores"][fw] += score
        
        for arch, score in result.get("archetype_scores", {}).items():
            self.brand_positioning_profiles[brand]["archetype_scores"][arch] += score
        
        try:
            rating = float(row.get(rating_field, 0) or 0)
            self.brand_positioning_profiles[brand]["avg_rating"] += rating
        except:
            pass
    
    def get_normalized_brand_positioning(self) -> Dict[str, Dict]:
        """Get normalized brand positioning profiles."""
        normalized = {}
        for brand, profile in self.brand_positioning_profiles.items():
            n = profile["review_count"]
            if n > 0:
                normalized[brand] = {
                    "framework_scores": {k: v/n for k, v in profile["framework_scores"].items()},
                    "archetype_scores": {k: v/n for k, v in profile["archetype_scores"].items()},
                    "review_count": n,
                    "avg_rating": profile["avg_rating"] / n if profile["avg_rating"] > 0 else 0,
                }
        return normalized


# =============================================================================
# MAIN PROCESSING FUNCTIONS
# =============================================================================

def process_csv_domain(
    domain_config: DomainConfig,
    file_path: Path,
    analyzer: MultiDomainHyperscanAnalyzer,
    output_dir: Path,
    product_lookup: Dict[str, Dict] = None,
    movie_lookup: Dict[str, Dict] = None,
    batch_size: int = 5000,
    max_reviews: int = None,
) -> Dict[str, Any]:
    """Process a CSV-format review file with brand positioning analysis."""
    logger.info(f"Processing {domain_config.name}: {file_path}")
    
    # Aggregation structures
    framework_totals = defaultdict(float)
    archetype_totals = defaultdict(float)
    dimension_totals = defaultdict(float)
    brand_customer_profiles = defaultdict(lambda: defaultdict(float))  # WHO BUYS from brand
    domain_specific = defaultdict(lambda: defaultdict(float))
    
    total_reviews = 0
    total_matches = 0
    start_time = time.time()
    
    # Extract brand from filename for automotive domain
    file_brand = None
    if domain_config.processor == "automotive":
        file_brand = AutomotiveProcessor.extract_brand_from_filename(str(file_path))
        logger.info(f"  Processing brand: {file_brand}")
    
    # Domain-specific processor with brand positioning analysis
    processor = None
    if domain_config.processor == "sephora":
        processor = SephoraProcessor(product_lookup=product_lookup, analyzer=analyzer)
        # Pre-analyze all products to build brand positioning profiles
        if product_lookup:
            logger.info(f"Analyzing brand positioning from {len(product_lookup):,} products...")
            for product_id, product_info in product_lookup.items():
                processor.analyze_brand_positioning(product_info)
            logger.info(f"  Built positioning profiles for {len(processor.brand_positioning_profiles):,} brands")
    elif domain_config.processor == "steam":
        processor = SteamProcessor()
    elif domain_config.processor == "airline":
        processor = AirlineProcessor(analyzer=analyzer)
    elif domain_config.processor == "automotive":
        processor = AutomotiveProcessor(analyzer=analyzer)
    elif domain_config.processor == "movie":
        processor = MovieProcessor(movie_lookup=movie_lookup, analyzer=analyzer)
        # Pre-analyze movie metadata for positioning
        if movie_lookup:
            logger.info(f"Analyzing movie positioning from {len(movie_lookup):,} movies...")
            for movie_id, movie_info in movie_lookup.items():
                processor.analyze_movie_positioning(movie_info)
    elif domain_config.processor in ["electronics", "streaming"]:
        # Generic processor for simpler domains
        brand_field = "brand_name"  # Default
        processor = GenericBrandProcessor(brand_field=brand_field, analyzer=analyzer)
    
    try:
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                text = row.get(domain_config.text_field, '')
                if not text or len(text) < 10:
                    continue
                
                # Analyze text
                result = analyzer.analyze(text)
                if not result:
                    continue
                
                # Aggregate framework scores
                for fw, score in result.get("framework_scores", {}).items():
                    framework_totals[fw] += score
                
                for arch, score in result.get("archetype_scores", {}).items():
                    archetype_totals[arch] += score
                
                for dim, score in result.get("dimension_scores", {}).items():
                    dimension_totals[dim] += score
                
                # Determine brand based on domain type
                if domain_config.processor == "automotive":
                    brand = file_brand  # Brand from filename
                elif domain_config.processor == "airline":
                    brand = row.get("Airline_Name", "Unknown")
                elif domain_config.processor == "movie":
                    brand = row.get("id", "Unknown")  # Movie ID as brand
                elif domain_config.processor == "streaming":
                    brand = "Netflix"  # Single brand
                elif domain_config.processor == "electronics":
                    brand = "BH Photo"  # Single retailer, but could extract product brands later
                else:
                    brand = row.get("brand_name") or row.get("app_name") or "Unknown"
                
                # Brand CUSTOMER aggregation (who buys from this brand - customer psychology)
                for arch, score in result.get("archetype_scores", {}).items():
                    brand_customer_profiles[brand][arch] += score
                
                # Domain-specific deep processing
                if processor and domain_config.deep_dive:
                    if domain_config.processor == "sephora":
                        demographics = processor.extract_demographics(row)
                        if any(demographics.values()):
                            for demo_key, demo_val in demographics.items():
                                if demo_val:
                                    for arch, score in result.get("archetype_scores", {}).items():
                                        domain_specific[f"demo_{demo_key}_{demo_val}"][arch] += score
                        
                        ingredient_psych = processor.analyze_ingredient_psychology(
                            row.get("product_name", ""),
                            text
                        )
                        for ing_type, score in ingredient_psych.items():
                            domain_specific["ingredient_psychology"][ing_type] += score
                    
                    elif domain_config.processor == "steam":
                        engagement = processor.extract_engagement_metrics(row)
                        gamer_archetypes = processor.compute_gamer_archetype(
                            engagement,
                            result.get("archetype_scores", {})
                        )
                        for gamer_arch, score in gamer_archetypes.items():
                            domain_specific["gamer_archetypes"][gamer_arch] += score
                        
                        # Playtime correlation
                        playtime_bucket = "0-20h" if engagement["playtime_hours"] < 20 else \
                                         "20-100h" if engagement["playtime_hours"] < 100 else \
                                         "100-500h" if engagement["playtime_hours"] < 500 else "500h+"
                        for arch, score in result.get("archetype_scores", {}).items():
                            domain_specific[f"playtime_{playtime_bucket}"][arch] += score
                    
                    elif domain_config.processor == "airline":
                        processor.update_brand_profile(brand, result, row)
                        # Service rating analysis
                        service_ratings = processor.extract_service_ratings(row)
                        for service, rating in service_ratings.items():
                            bucket = "low" if rating <= 2 else "mid" if rating <= 4 else "high"
                            for arch, score in result.get("archetype_scores", {}).items():
                                domain_specific[f"service_{service}_{bucket}"][arch] += score
                    
                    elif domain_config.processor == "automotive":
                        processor.update_brand_profile(brand, result, row)
                        # Vehicle info analysis
                        vehicle_info = processor.extract_vehicle_info(row)
                        if vehicle_info.get("year"):
                            try:
                                year = int(vehicle_info["year"])
                                age_bucket = "new" if year >= 2015 else "mid" if year >= 2005 else "classic"
                                for arch, score in result.get("archetype_scores", {}).items():
                                    domain_specific[f"vehicle_age_{age_bucket}"][arch] += score
                            except:
                                pass
                    
                    elif domain_config.processor == "movie":
                        processor.update_brand_profile(brand, result, row)
                        # Critic type analysis
                        is_top_critic = row.get("isTopCritic", "False") == "True"
                        critic_type = "top_critic" if is_top_critic else "regular_critic"
                        for arch, score in result.get("archetype_scores", {}).items():
                            domain_specific[critic_type][arch] += score
                        
                        # Sentiment analysis
                        sentiment = row.get("scoreSentiment", "")
                        if sentiment:
                            for arch, score in result.get("archetype_scores", {}).items():
                                domain_specific[f"sentiment_{sentiment.lower()}"][arch] += score
                    
                    elif domain_config.processor in ["electronics", "streaming"]:
                        processor.update_brand_profile(brand, result, row, domain_config.rating_field)
                        # Rating bucket analysis
                        try:
                            rating = float(row.get(domain_config.rating_field, 0) or 0)
                            rating_bucket = "low" if rating <= 2 else "mid" if rating <= 4 else "high"
                            for arch, score in result.get("archetype_scores", {}).items():
                                domain_specific[f"rating_{rating_bucket}"][arch] += score
                        except:
                            pass
                
                total_reviews += 1
                total_matches += result.get("total_matches", 0)
                
                # Progress logging
                if total_reviews % 50000 == 0:
                    elapsed = time.time() - start_time
                    rate = total_reviews / elapsed if elapsed > 0 else 0
                    logger.info(f"  {domain_config.name}: {total_reviews:,} reviews ({rate:,.0f}/sec)")
                    
                    if total_reviews % 100000 == 0:
                        gc.collect()
                
                if max_reviews and total_reviews >= max_reviews:
                    logger.info(f"  Reached max_reviews limit: {max_reviews}")
                    break
    
    except Exception as e:
        logger.error(f"Error processing {file_path}: {e}")
        raise
    
    elapsed = time.time() - start_time
    rate = total_reviews / elapsed if elapsed > 0 else 0
    logger.info(f"COMPLETED {domain_config.name}: {total_reviews:,} reviews in {elapsed:.1f}s ({rate:,.0f}/sec)")
    
    # Build result with brand-customer alignment analysis
    final_result = {
        "domain": domain_config.name,
        "file": str(file_path),
        "total_reviews": total_reviews,
        "total_matches": total_matches,
        "processing_time_sec": elapsed,
        "framework_totals": dict(framework_totals),
        "archetype_totals": dict(archetype_totals),
        "dimension_totals": dict(dimension_totals),
        "brand_customer_profiles": {k: dict(v) for k, v in brand_customer_profiles.items()},  # WHO BUYS
        "domain_specific": {k: dict(v) for k, v in domain_specific.items()},
    }
    
    # Add brand positioning analysis (HOW BRANDS POSITION)
    if processor and hasattr(processor, 'get_normalized_brand_positioning'):
        brand_positioning = processor.get_normalized_brand_positioning()
        if brand_positioning:
            final_result["brand_positioning_profiles"] = brand_positioning  # BRAND'S PSYCHOLOGY
            logger.info(f"  Brand positioning profiles built for {len(brand_positioning):,} brands")
            
            # Compute brand-customer alignment
            alignment_analysis = compute_global_brand_customer_alignment(
                brand_positioning,
                {k: dict(v) for k, v in brand_customer_profiles.items()}
            )
            final_result["brand_customer_alignment"] = alignment_analysis
    
    return final_result


def process_jsonl_domain(
    domain_config: DomainConfig,
    file_path: Path,
    analyzer: MultiDomainHyperscanAnalyzer,
    output_dir: Path,
    business_lookup: Dict = None,
    user_lookup: Dict = None,
    podcast_lookup: Dict = None,
    batch_size: int = 5000,
    max_reviews: int = None,
) -> Dict[str, Any]:
    """Process a JSONL-format review file (e.g., Yelp, Podcasts)."""
    logger.info(f"Processing {domain_config.name}: {file_path}")
    
    # Aggregation structures
    framework_totals = defaultdict(float)
    archetype_totals = defaultdict(float)
    dimension_totals = defaultdict(float)
    category_profiles = defaultdict(lambda: defaultdict(float))
    geographic_profiles = defaultdict(lambda: defaultdict(float))
    domain_specific = defaultdict(lambda: defaultdict(float))
    
    total_reviews = 0
    total_matches = 0
    enriched_count = 0
    start_time = time.time()
    
    # Domain-specific processor
    processor = None
    brand_customer_profiles = defaultdict(lambda: defaultdict(float))  # WHO BUYS from brand
    
    if domain_config.processor == "yelp":
        processor = YelpProcessor(business_lookup, user_lookup)
    elif domain_config.processor == "podcast":
        processor = PodcastProcessor(podcast_lookup=podcast_lookup, analyzer=analyzer)
        # Pre-analyze podcast metadata for positioning
        if podcast_lookup:
            logger.info(f"Analyzing podcast positioning from {len(podcast_lookup):,} podcasts...")
            analyzed = 0
            for podcast_id, podcast_info in podcast_lookup.items():
                result = processor.analyze_podcast_positioning(podcast_info)
                if result:
                    analyzed += 1
            logger.info(f"  Built positioning profiles for {analyzed:,} podcasts with content")
    
    try:
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            for line in f:
                try:
                    review = json.loads(line)
                except json.JSONDecodeError:
                    continue
                
                text = review.get(domain_config.text_field, '')
                if not text or len(text) < 10:
                    continue
                
                # Enrich with context based on domain
                if domain_config.processor == "yelp" and processor:
                    review = processor.enrich_review(review)
                    if "_business_name" in review:
                        enriched_count += 1
                elif domain_config.processor == "podcast" and processor:
                    review = processor.enrich_review(review)
                    if "_podcast_title" in review:
                        enriched_count += 1
                
                # Analyze text
                result = analyzer.analyze(text)
                if not result:
                    continue
                
                # Aggregate
                for fw, score in result.get("framework_scores", {}).items():
                    framework_totals[fw] += score
                
                for arch, score in result.get("archetype_scores", {}).items():
                    archetype_totals[arch] += score
                
                for dim, score in result.get("dimension_scores", {}).items():
                    dimension_totals[dim] += score
                
                # Domain-specific processing
                if domain_config.processor == "yelp":
                    # Category profiling (Yelp)
                    categories = review.get("_business_categories", "")
                    if categories:
                        for cat in categories.split(", ")[:3]:  # Top 3 categories
                            for arch, score in result.get("archetype_scores", {}).items():
                                category_profiles[cat][arch] += score
                    
                    # Geographic profiling
                    state = review.get("_business_state", "")
                    if state:
                        for arch, score in result.get("archetype_scores", {}).items():
                            geographic_profiles[state][arch] += score
                    
                    # Reviewer influence
                    if processor:
                        influence = processor.compute_reviewer_influence(review)
                        if influence.get("elite_status", 0) > 0:
                            for arch, score in result.get("archetype_scores", {}).items():
                                domain_specific["elite_reviewers"][arch] += score
                
                elif domain_config.processor == "podcast":
                    # Podcast brand profiling
                    podcast_id = review.get("podcast_id", "Unknown")
                    for arch, score in result.get("archetype_scores", {}).items():
                        brand_customer_profiles[podcast_id][arch] += score
                    
                    # Update podcast processor's brand profile
                    if processor:
                        processor.update_brand_profile(podcast_id, result, review)
                    
                    # Podcast category from enriched data
                    podcast_title = review.get("_podcast_title", "")
                    if podcast_title:
                        # Group by first letter for quick categorization
                        first_letter = podcast_title[0].upper() if podcast_title else "?"
                        for arch, score in result.get("archetype_scores", {}).items():
                            category_profiles[f"title_{first_letter}"][arch] += score
                
                # Rating sentiment analysis (common to both)
                stars = review.get(domain_config.rating_field, 0)
                try:
                    stars = float(stars)
                    rating_bucket = "low" if stars <= 2 else "mid" if stars <= 4 else "high"
                    for arch, score in result.get("archetype_scores", {}).items():
                        domain_specific[f"rating_{rating_bucket}"][arch] += score
                except (ValueError, TypeError):
                    pass
                
                total_reviews += 1
                total_matches += result.get("total_matches", 0)
                
                # Progress
                if total_reviews % 100000 == 0:
                    elapsed = time.time() - start_time
                    rate = total_reviews / elapsed if elapsed > 0 else 0
                    enrich_pct = (enriched_count / total_reviews * 100) if total_reviews > 0 else 0
                    logger.info(f"  {domain_config.name}: {total_reviews:,} ({rate:,.0f}/sec, {enrich_pct:.1f}% enriched)")
                    
                    if total_reviews % 500000 == 0:
                        gc.collect()
                        logger.info(f"  [GC] Memory cleared at {total_reviews:,}")
                
                if max_reviews and total_reviews >= max_reviews:
                    logger.info(f"  Reached max_reviews limit: {max_reviews}")
                    break
    
    except Exception as e:
        logger.error(f"Error processing {file_path}: {e}")
        raise
    
    elapsed = time.time() - start_time
    rate = total_reviews / elapsed if elapsed > 0 else 0
    enrich_pct = (enriched_count / total_reviews * 100) if total_reviews > 0 else 0
    logger.info(f"COMPLETED {domain_config.name}: {total_reviews:,} reviews in {elapsed:.1f}s ({rate:,.0f}/sec, {enrich_pct:.1f}% enriched)")
    
    final_result = {
        "domain": domain_config.name,
        "file": str(file_path),
        "total_reviews": total_reviews,
        "total_matches": total_matches,
        "enriched_count": enriched_count,
        "processing_time_sec": elapsed,
        "framework_totals": dict(framework_totals),
        "archetype_totals": dict(archetype_totals),
        "dimension_totals": dict(dimension_totals),
        "category_profiles": {k: dict(v) for k, v in category_profiles.items()},
        "geographic_profiles": {k: dict(v) for k, v in geographic_profiles.items()},
        "domain_specific": {k: dict(v) for k, v in domain_specific.items()},
        "brand_customer_profiles": {k: dict(v) for k, v in brand_customer_profiles.items()},
    }
    
    # Add brand positioning analysis for podcasts
    if processor and hasattr(processor, 'get_normalized_brand_positioning'):
        brand_positioning = processor.get_normalized_brand_positioning()
        if brand_positioning:
            final_result["brand_positioning_profiles"] = brand_positioning
            logger.info(f"  Brand positioning profiles built for {len(brand_positioning):,} podcasts")
            
            # Compute brand-customer alignment
            alignment_analysis = compute_global_brand_customer_alignment(
                brand_positioning,
                {k: dict(v) for k, v in brand_customer_profiles.items()}
            )
            final_result["brand_customer_alignment"] = alignment_analysis
    
    return final_result


def load_sephora_product_lookup(sephora_dir: Path) -> Dict[str, Dict]:
    """Load Sephora product metadata for brand positioning analysis."""
    product_lookup = {}
    product_file = sephora_dir / "product_info.csv"
    
    if not product_file.exists():
        logger.warning(f"Sephora product_info.csv not found at {product_file}")
        return product_lookup
    
    logger.info("Loading Sephora product metadata for brand positioning analysis...")
    try:
        with open(product_file, 'r', encoding='utf-8', errors='replace') as f:
            reader = csv.DictReader(f)
            count = 0
            for row in reader:
                product_id = row.get("product_id", "")
                if product_id:
                    product_lookup[product_id] = {
                        "product_name": row.get("product_name", ""),
                        "brand_name": row.get("brand_name", ""),
                        "brand_id": row.get("brand_id", ""),
                        "highlights": row.get("highlights", ""),
                        "ingredients": row.get("ingredients", ""),
                        "price_usd": row.get("price_usd", ""),
                        "primary_category": row.get("primary_category", ""),
                        "secondary_category": row.get("secondary_category", ""),
                        "tertiary_category": row.get("tertiary_category", ""),
                        "loves_count": row.get("loves_count", ""),
                        "rating": row.get("rating", ""),
                    }
                    count += 1
        logger.info(f"  Loaded {count:,} products for brand positioning analysis")
    except Exception as e:
        logger.error(f"Error loading Sephora product metadata: {e}")
    
    return product_lookup


def compute_global_brand_customer_alignment(
    brand_positioning_profiles: Dict[str, Dict],
    brand_customer_profiles: Dict[str, Dict]
) -> Dict[str, Any]:
    """
    Compute alignment between brand positioning and customer psychology for all brands.
    
    Returns metrics showing which brands are well-aligned with their customers.
    """
    logger.info("Computing brand-customer alignment analysis...")
    
    alignments = {}
    total_alignment = 0.0
    aligned_count = 0
    high_alignment_brands = []
    low_alignment_brands = []
    
    for brand in set(brand_positioning_profiles.keys()) & set(brand_customer_profiles.keys()):
        brand_pos = brand_positioning_profiles[brand].get("archetype_scores", {})
        customer_prof = brand_customer_profiles[brand]
        
        # Normalize customer profile
        total_cust = sum(customer_prof.values())
        if total_cust > 0:
            customer_prof_norm = {k: v/total_cust for k, v in customer_prof.items()}
        else:
            continue
        
        # Normalize brand positioning
        total_brand = sum(brand_pos.values())
        if total_brand > 0:
            brand_pos_norm = {k: v/total_brand for k, v in brand_pos.items()}
        else:
            continue
        
        # Compute alignment (cosine similarity)
        alignment = SephoraProcessor.compute_brand_customer_alignment(brand_pos_norm, customer_prof_norm)
        
        alignments[brand] = {
            "alignment_score": alignment,
            "brand_primary_archetype": max(brand_pos_norm, key=brand_pos_norm.get) if brand_pos_norm else "unknown",
            "customer_primary_archetype": max(customer_prof_norm, key=customer_prof_norm.get) if customer_prof_norm else "unknown",
            "product_count": brand_positioning_profiles[brand].get("product_count", 0),
        }
        
        total_alignment += alignment
        aligned_count += 1
        
        if alignment > 0.8:
            high_alignment_brands.append((brand, alignment))
        elif alignment < 0.4:
            low_alignment_brands.append((brand, alignment))
    
    avg_alignment = total_alignment / aligned_count if aligned_count > 0 else 0.0
    
    # Identify alignment patterns
    correct_targeting = sum(1 for b in alignments.values() 
                          if b["brand_primary_archetype"] == b["customer_primary_archetype"])
    
    logger.info(f"  Analyzed {aligned_count:,} brands with both positioning and customer data")
    logger.info(f"  Average alignment score: {avg_alignment:.2%}")
    logger.info(f"  High-alignment brands (>80%): {len(high_alignment_brands)}")
    logger.info(f"  Low-alignment brands (<40%): {len(low_alignment_brands)}")
    logger.info(f"  Brands with correct primary target: {correct_targeting}/{aligned_count} ({correct_targeting/aligned_count*100:.1f}%)" if aligned_count > 0 else "")
    
    return {
        "brand_alignments": alignments,
        "average_alignment": avg_alignment,
        "total_brands_analyzed": aligned_count,
        "high_alignment_count": len(high_alignment_brands),
        "low_alignment_count": len(low_alignment_brands),
        "correct_targeting_count": correct_targeting,
        "top_aligned_brands": sorted(high_alignment_brands, key=lambda x: -x[1])[:20],
        "worst_aligned_brands": sorted(low_alignment_brands, key=lambda x: x[1])[:20],
    }


def load_podcast_lookup(podcast_dir: Path) -> Dict[str, Dict]:
    """Load podcast metadata for brand positioning analysis."""
    podcast_lookup = {}
    podcast_file = podcast_dir / "podcasts.json"
    
    if not podcast_file.exists():
        logger.warning(f"Podcast metadata not found at {podcast_file}")
        return podcast_lookup
    
    logger.info("Loading podcast metadata for brand positioning analysis...")
    try:
        count = 0
        with open(podcast_file, 'r', encoding='utf-8', errors='replace') as f:
            for line in f:
                try:
                    podcast = json.loads(line)
                    podcast_id = podcast.get("podcast_id", "")
                    if podcast_id and podcast.get("title"):  # Only store podcasts with titles
                        podcast_lookup[podcast_id] = {
                            "title": podcast.get("title", ""),
                            "author": podcast.get("author", ""),
                            "description": podcast.get("description", ""),
                            "average_rating": podcast.get("average_rating", 0),
                            "ratings_count": podcast.get("ratings_count", 0),
                        }
                        count += 1
                except json.JSONDecodeError:
                    continue
        logger.info(f"  Loaded {count:,} podcasts for positioning analysis")
    except Exception as e:
        logger.error(f"Error loading podcast metadata: {e}")
    
    return podcast_lookup


def load_movie_lookup(movie_dir: Path) -> Dict[str, Dict]:
    """Load Rotten Tomatoes movie metadata for brand positioning analysis."""
    movie_lookup = {}
    movie_file = movie_dir / "rotten_tomatoes_movies.csv"
    
    if not movie_file.exists():
        logger.warning(f"Movie metadata not found at {movie_file}")
        return movie_lookup
    
    logger.info("Loading movie metadata for brand positioning analysis...")
    try:
        with open(movie_file, 'r', encoding='utf-8', errors='replace') as f:
            reader = csv.DictReader(f)
            count = 0
            for row in reader:
                movie_id = row.get("id", "")
                if movie_id:
                    movie_lookup[movie_id] = {
                        "title": row.get("title", ""),
                        "genre": row.get("genre", ""),
                        "tomatoMeter": row.get("tomatoMeter", ""),
                        "audienceScore": row.get("audienceScore", ""),
                        "rating": row.get("rating", ""),
                        "director": row.get("director", ""),
                        "releaseDateTheaters": row.get("releaseDateTheaters", ""),
                    }
                    count += 1
        logger.info(f"  Loaded {count:,} movies for positioning analysis")
    except Exception as e:
        logger.error(f"Error loading movie metadata: {e}")
    
    return movie_lookup


def load_airline_metadata(airline_dir: Path) -> Dict[str, Dict]:
    """Load airline quality ratings metadata for brand positioning analysis."""
    airline_metadata = {}
    metadata_file = airline_dir / "Airline Quality Ratings.csv"
    
    if not metadata_file.exists():
        logger.warning(f"Airline quality metadata not found at {metadata_file}")
        return airline_metadata
    
    logger.info("Loading airline quality metadata for positioning analysis...")
    # Note: This file has individual passenger ratings, not airline-level positioning
    # We'll use it for aggregate quality metrics per airline
    return airline_metadata


def load_yelp_lookups(yelp_dir: Path) -> Tuple[Dict, Dict]:
    """Load Yelp business and user lookup dictionaries."""
    business_lookup = {}
    user_lookup = {}
    
    # Load businesses
    business_file = yelp_dir / "yelp_academic_dataset_business.json"
    if business_file.exists():
        logger.info("Loading Yelp business data...")
        with open(business_file, 'r', encoding='utf-8') as f:
            count = 0
            for line in f:
                try:
                    biz = json.loads(line)
                    business_lookup[biz["business_id"]] = biz
                    count += 1
                except:
                    continue
        logger.info(f"  Loaded {count:,} businesses")
    
    # Load users (sample for memory efficiency)
    user_file = yelp_dir / "yelp_academic_dataset_user.json"
    if user_file.exists():
        logger.info("Loading Yelp user data (sampling)...")
        with open(user_file, 'r', encoding='utf-8') as f:
            count = 0
            for line in f:
                try:
                    user = json.loads(line)
                    # Only store users with significant activity
                    if user.get("review_count", 0) >= 5:
                        user_lookup[user["user_id"]] = {
                            "review_count": user.get("review_count", 0),
                            "yelping_since": user.get("yelping_since", ""),
                            "elite": user.get("elite", ""),
                        }
                        count += 1
                except:
                    continue
        logger.info(f"  Loaded {count:,} active users")
    
    return business_lookup, user_lookup


def save_checkpoint(results: Dict, output_dir: Path, domain_name: str):
    """Save processing checkpoint."""
    checkpoint_path = output_dir / f"checkpoint_{domain_name.replace(' ', '_').lower()}.json"
    with open(checkpoint_path, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    logger.info(f"Checkpoint saved: {checkpoint_path}")


def aggregate_all_domains(output_dir: Path) -> Dict[str, Any]:
    """Aggregate results from all domain checkpoints into unified priors."""
    logger.info("Aggregating all domain results...")
    
    unified = {
        "framework_totals": defaultdict(float),
        "archetype_totals": defaultdict(float),
        "domain_insights": {},
        "total_reviews": 0,
        "domains_processed": [],
    }
    
    for checkpoint_file in output_dir.glob("checkpoint_*.json"):
        logger.info(f"  Loading {checkpoint_file.name}")
        with open(checkpoint_file, 'r') as f:
            data = json.load(f)
        
        domain = data.get("domain", "unknown")
        unified["domains_processed"].append(domain)
        unified["total_reviews"] += data.get("total_reviews", 0)
        
        for fw, score in data.get("framework_totals", {}).items():
            unified["framework_totals"][fw] += score
        
        for arch, score in data.get("archetype_totals", {}).items():
            unified["archetype_totals"][arch] += score
        
        # Store domain-specific insights
        unified["domain_insights"][domain] = {
            "total_reviews": data.get("total_reviews", 0),
            "processing_time": data.get("processing_time_sec", 0),
            "category_profiles": data.get("category_profiles", {}),
            "geographic_profiles": data.get("geographic_profiles", {}),
            "domain_specific": data.get("domain_specific", {}),
            "brand_profiles": data.get("brand_profiles", {}),
        }
    
    # Normalize framework totals
    total = sum(unified["framework_totals"].values())
    if total > 0:
        unified["normalized_frameworks"] = {k: v/total for k, v in unified["framework_totals"].items()}
    
    total_arch = sum(unified["archetype_totals"].values())
    if total_arch > 0:
        unified["normalized_archetypes"] = {k: v/total_arch for k, v in unified["archetype_totals"].items()}
    
    # Convert defaultdicts
    unified["framework_totals"] = dict(unified["framework_totals"])
    unified["archetype_totals"] = dict(unified["archetype_totals"])
    
    return unified


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="ADAM Multi-Domain Review Processing")
    parser.add_argument("--reviews-dir", type=str, 
                       default="/Users/chrisnocera/Sites/adam-platform/reviews_other",
                       help="Path to reviews_other directory")
    parser.add_argument("--output-dir", type=str,
                       default="/Users/chrisnocera/Sites/adam-platform/data/learning/multi_domain",
                       help="Output directory for checkpoints and priors")
    parser.add_argument("--domains", type=str, nargs="+",
                       help="Specific domains to process (default: all)")
    parser.add_argument("--deep-dive-only", action="store_true",
                       help="Only process deep-dive domains (Sephora, Steam, Yelp)")
    parser.add_argument("--max-reviews", type=int, default=None,
                       help="Maximum reviews per domain (for testing)")
    parser.add_argument("--resume", action="store_true",
                       help="Resume from existing checkpoints")
    parser.add_argument("--aggregate-only", action="store_true",
                       help="Only aggregate existing checkpoints")
    
    args = parser.parse_args()
    
    reviews_dir = Path(args.reviews_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info("=" * 60)
    logger.info("ADAM MULTI-DOMAIN HYPERSCAN PIPELINE")
    logger.info("=" * 60)
    logger.info(f"Reviews directory: {reviews_dir}")
    logger.info(f"Output directory: {output_dir}")
    
    if args.aggregate_only:
        unified = aggregate_all_domains(output_dir)
        priors_path = output_dir / "multi_domain_priors.json"
        with open(priors_path, 'w') as f:
            json.dump(unified, f, indent=2)
        logger.info(f"Unified priors saved: {priors_path}")
        logger.info(f"Total reviews across all domains: {unified['total_reviews']:,}")
        return
    
    # Determine which domains to process
    domains_to_process = []
    if args.domains:
        domains_to_process = args.domains
    elif args.deep_dive_only:
        domains_to_process = ["sephora", "steam", "yelp"]
    else:
        domains_to_process = list(DOMAIN_CONFIGS.keys())
    
    logger.info(f"Domains to process: {domains_to_process}")
    
    # Check for existing checkpoints if resuming
    existing_checkpoints = set()
    if args.resume:
        for f in output_dir.glob("checkpoint_*.json"):
            domain_name = f.stem.replace("checkpoint_", "")
            existing_checkpoints.add(domain_name)
        logger.info(f"Found {len(existing_checkpoints)} existing checkpoints")
    
    # Process each domain
    for domain_key in domains_to_process:
        if domain_key not in DOMAIN_CONFIGS:
            logger.warning(f"Unknown domain: {domain_key}")
            continue
        
        config = DOMAIN_CONFIGS[domain_key]
        checkpoint_name = config.name.replace(' ', '_').lower()
        
        if args.resume and checkpoint_name in existing_checkpoints:
            logger.info(f"Skipping {config.name} (checkpoint exists)")
            continue
        
        domain_dir = reviews_dir / config.folder
        if not domain_dir.exists():
            logger.warning(f"Directory not found: {domain_dir}")
            continue
        
        # Find files to process
        files = list(domain_dir.glob(config.file_pattern))
        if not files:
            logger.warning(f"No files matching {config.file_pattern} in {domain_dir}")
            continue
        
        logger.info(f"\n{'='*60}")
        logger.info(f"Processing: {config.name}")
        logger.info(f"Files: {len(files)}")
        logger.info(f"Format: {config.format}")
        logger.info(f"Deep-dive: {config.deep_dive}")
        logger.info(f"{'='*60}")
        
        # Create domain-specific analyzer
        analyzer = MultiDomainHyperscanAnalyzer(config)
        
        # Load domain-specific metadata for brand positioning analysis
        product_lookup = {}
        movie_lookup = {}
        podcast_lookup = {}
        business_lookup = {}
        user_lookup = {}
        
        if config.processor == "sephora":
            product_lookup = load_sephora_product_lookup(domain_dir)
        elif config.processor == "movie":
            movie_lookup = load_movie_lookup(domain_dir)
        elif config.processor == "podcast":
            podcast_lookup = load_podcast_lookup(domain_dir)
        elif config.processor == "yelp":
            business_lookup, user_lookup = load_yelp_lookups(domain_dir)
        
        # Increase CSV field limit for large fields (Steam reviews can be huge)
        csv.field_size_limit(sys.maxsize)
        
        # Process based on format
        all_results = []
        
        for file_path in files:
            try:
                if config.format == "csv":
                    result = process_csv_domain(
                        config, file_path, analyzer, output_dir,
                        product_lookup=product_lookup,
                        movie_lookup=movie_lookup,
                        max_reviews=args.max_reviews
                    )
                elif config.format == "jsonl":
                    result = process_jsonl_domain(
                        config, file_path, analyzer, output_dir,
                        business_lookup=business_lookup,
                        user_lookup=user_lookup,
                        podcast_lookup=podcast_lookup,
                        max_reviews=args.max_reviews
                    )
                else:
                    logger.warning(f"Unsupported format: {config.format}")
                    continue
                
                all_results.append(result)
                
            except Exception as e:
                logger.error(f"Error processing {file_path}: {e}", exc_info=True)
                continue
        
        # Aggregate results for this domain
        if all_results:
            aggregated = {
                "domain": config.name,
                "files_processed": len(all_results),
                "total_reviews": sum(r.get("total_reviews", 0) for r in all_results),
                "total_matches": sum(r.get("total_matches", 0) for r in all_results),
                "processing_time_sec": sum(r.get("processing_time_sec", 0) for r in all_results),
                "framework_totals": defaultdict(float),
                "archetype_totals": defaultdict(float),
                "dimension_totals": defaultdict(float),
                "brand_customer_profiles": defaultdict(lambda: defaultdict(float)),  # WHO BUYS
                "category_profiles": defaultdict(lambda: defaultdict(float)),
                "geographic_profiles": defaultdict(lambda: defaultdict(float)),
                "domain_specific": defaultdict(lambda: defaultdict(float)),
            }
            
            for result in all_results:
                for fw, score in result.get("framework_totals", {}).items():
                    aggregated["framework_totals"][fw] += score
                for arch, score in result.get("archetype_totals", {}).items():
                    aggregated["archetype_totals"][arch] += score
                for dim, score in result.get("dimension_totals", {}).items():
                    aggregated["dimension_totals"][dim] += score
                
                # Brand CUSTOMER profiles (who buys from each brand)
                for brand, profiles in result.get("brand_customer_profiles", {}).items():
                    for arch, score in profiles.items():
                        aggregated["brand_customer_profiles"][brand][arch] += score
                
                for cat, profiles in result.get("category_profiles", {}).items():
                    for arch, score in profiles.items():
                        aggregated["category_profiles"][cat][arch] += score
                
                for geo, profiles in result.get("geographic_profiles", {}).items():
                    for arch, score in profiles.items():
                        aggregated["geographic_profiles"][geo][arch] += score
                
                for key, data in result.get("domain_specific", {}).items():
                    for subkey, score in data.items():
                        aggregated["domain_specific"][key][subkey] += score
                
                # Brand positioning profiles (how brands position)
                if "brand_positioning_profiles" in result:
                    if "brand_positioning_profiles" not in aggregated:
                        aggregated["brand_positioning_profiles"] = {}
                    aggregated["brand_positioning_profiles"].update(result["brand_positioning_profiles"])
                
                # Brand-customer alignment analysis
                if "brand_customer_alignment" in result:
                    aggregated["brand_customer_alignment"] = result["brand_customer_alignment"]
            
            # Convert defaultdicts
            aggregated["framework_totals"] = dict(aggregated["framework_totals"])
            aggregated["archetype_totals"] = dict(aggregated["archetype_totals"])
            aggregated["dimension_totals"] = dict(aggregated["dimension_totals"])
            aggregated["brand_customer_profiles"] = {k: dict(v) for k, v in aggregated["brand_customer_profiles"].items()}
            aggregated["category_profiles"] = {k: dict(v) for k, v in aggregated["category_profiles"].items()}
            aggregated["geographic_profiles"] = {k: dict(v) for k, v in aggregated["geographic_profiles"].items()}
            aggregated["domain_specific"] = {k: dict(v) for k, v in aggregated["domain_specific"].items()}
            
            save_checkpoint(aggregated, output_dir, config.name)
        
        # Clear memory
        del analyzer
        gc.collect()
    
    # Final aggregation
    logger.info("\n" + "=" * 60)
    logger.info("FINAL AGGREGATION")
    logger.info("=" * 60)
    
    unified = aggregate_all_domains(output_dir)
    priors_path = output_dir / "multi_domain_priors.json"
    with open(priors_path, 'w') as f:
        json.dump(unified, f, indent=2)
    
    logger.info(f"\nUnified priors saved: {priors_path}")
    logger.info(f"Total reviews across all domains: {unified['total_reviews']:,}")
    logger.info(f"Domains processed: {unified['domains_processed']}")
    
    logger.info("\n" + "=" * 60)
    logger.info("MULTI-DOMAIN PROCESSING COMPLETE")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
