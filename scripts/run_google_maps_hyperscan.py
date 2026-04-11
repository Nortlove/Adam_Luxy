#!/usr/bin/env python3
"""
ADAM GOOGLE MAPS LOCATION REVIEW PROCESSING PIPELINE
=====================================================

Processes Google Maps reviews by state with:
- 82-Framework psychological analysis
- Business metadata enrichment for brand positioning
- Brand-customer alignment analysis
- Category-level psychological profiling
- Geographic (state-level) aggregation

Data Structure:
- Reviews: review-{State}.json (JSONL)
- Metadata: meta-{State}.json (JSONL)
- Linked by: gmap_id

Author: ADAM Platform
"""

import argparse
import csv
import gc
import json
import logging
import os
import sys
import time
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

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
        logging.FileHandler(log_dir / 'google_maps_hyperscan.log')
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
# LOCATION-SPECIFIC PSYCHOLOGY MARKERS
# =============================================================================

LOCATION_PSYCHOLOGY_MARKERS = {
    "experience_quality": {
        "patterns": [
            r"\b(experience|atmosphere|ambiance|vibe|feel)\b",
            r"\b(amazing|wonderful|terrible|awful|great)\b",
            r"\b(loved|hated|enjoyed|disappointed)\b",
        ],
        "weight": 1.1
    },
    "service_quality": {
        "patterns": [
            r"\b(service|staff|employee|manager|friendly)\b",
            r"\b(helpful|rude|attentive|ignored|slow|fast)\b",
            r"\b(professional|unprofessional|courteous)\b",
        ],
        "weight": 1.2
    },
    "value_perception": {
        "patterns": [
            r"\b(price|expensive|cheap|affordable|overpriced)\b",
            r"\b(value|worth|deal|ripoff|reasonable)\b",
            r"\b(money|cost|pay|paid|charged)\b",
        ],
        "weight": 1.0
    },
    "recommendation_intent": {
        "patterns": [
            r"\b(recommend|suggest|tell everyone|avoid|skip)\b",
            r"\b(come back|return|never again|definitely)\b",
            r"\b(must visit|hidden gem|go-to|favorite)\b",
        ],
        "weight": 1.1
    },
    "location_convenience": {
        "patterns": [
            r"\b(location|convenient|parking|easy to find)\b",
            r"\b(close|nearby|accessible|far|hard to find)\b",
            r"\b(clean|dirty|neat|messy|organized)\b",
        ],
        "weight": 0.9
    },
    "wait_time": {
        "patterns": [
            r"\b(wait|waited|waiting|quick|fast|slow)\b",
            r"\b(line|queue|crowded|busy|empty)\b",
            r"\b(reservation|appointment|walk-in)\b",
        ],
        "weight": 1.0
    },
    "food_quality": {
        "patterns": [
            r"\b(food|meal|dish|taste|flavor|delicious)\b",
            r"\b(fresh|stale|bland|amazing|terrible)\b",
            r"\b(portion|serving|menu|options)\b",
        ],
        "weight": 1.1
    },
    "trust_safety": {
        "patterns": [
            r"\b(trust|safe|secure|reliable|honest)\b",
            r"\b(scam|fraud|sketchy|legit|genuine)\b",
            r"\b(professional|licensed|certified)\b",
        ],
        "weight": 1.2
    }
}


# =============================================================================
# HYPERSCAN ANALYZER
# =============================================================================

class GoogleMapsHyperscanAnalyzer:
    """
    Hyperscan-based analyzer for Google Maps review processing.
    Compiles all 82 frameworks + location-specific patterns.
    """
    
    def __init__(self):
        self.patterns = []
        self.pattern_ids = []
        self.pattern_metadata = {}
        self.db = None
        self.scratch = None
        
        self._build_pattern_database()
        self._compile_database()
    
    def _add_patterns_from_dict(self, markers: Dict, framework_name: str):
        """Add patterns from a marker dictionary (handles nested structures)."""
        for dimension, config in markers.items():
            if isinstance(config, dict):
                weight = config.get("weight", 1.0)
                
                # Direct patterns array
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
                
                # Direct sub-dimensions
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
        
        # Add location-specific patterns
        self._add_patterns_from_dict(LOCATION_PSYCHOLOGY_MARKERS, "domain_location")
        
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
        logger.info(f"Hyperscan database compiled in {elapsed:.2f}s")
    
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
        archetype_scores = self._compute_archetypes(framework_scores)
        
        return {
            "framework_scores": dict(framework_scores),
            "dimension_scores": dict(dimension_scores),
            "archetype_scores": archetype_scores,
            "total_matches": len(matches),
            "primary_archetype": max(archetype_scores, key=archetype_scores.get) if archetype_scores else "unknown"
        }
    
    def _compute_archetypes(self, framework_scores: Dict) -> Dict[str, float]:
        """Compute archetype probabilities from framework scores."""
        archetypes = {
            "achiever": 0.0,
            "explorer": 0.0,
            "connector": 0.0,
            "guardian": 0.0,
            "pragmatist": 0.0,
        }
        
        archetypes["achiever"] = (
            framework_scores.get("regulatory_focus", 0) * 0.3 +
            framework_scores.get("big_five", 0) * 0.2 +
            framework_scores.get("self_determination", 0) * 0.2 +
            framework_scores.get("social_comparison", 0) * 0.3
        )
        
        archetypes["explorer"] = (
            framework_scores.get("attention", 0) * 0.3 +
            framework_scores.get("approach_avoidance", 0) * 0.2 +
            framework_scores.get("need_for_cognition", 0) * 0.3 +
            framework_scores.get("uncertainty_tolerance", 0) * 0.2
        )
        
        archetypes["connector"] = (
            framework_scores.get("belongingness", 0) * 0.3 +
            framework_scores.get("social_proof", 0) * 0.3 +
            framework_scores.get("mimetic_desire", 0) * 0.2 +
            framework_scores.get("liking", 0) * 0.2
        )
        
        archetypes["guardian"] = (
            framework_scores.get("loss_aversion", 0) * 0.3 +
            framework_scores.get("certainty", 0) * 0.2 +
            framework_scores.get("commitment", 0) * 0.3 +
            framework_scores.get("authority", 0) * 0.2
        )
        
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
# BUSINESS PROCESSOR (Brand Positioning Analysis)
# =============================================================================

class BusinessProcessor:
    """Processes business metadata for brand positioning analysis."""
    
    def __init__(self, analyzer: GoogleMapsHyperscanAnalyzer):
        self.analyzer = analyzer
        self.brand_positioning_profiles = defaultdict(lambda: {
            "framework_scores": defaultdict(float),
            "archetype_scores": defaultdict(float),
            "business_count": 0,
            "categories": defaultdict(int),
            "avg_rating_sum": 0.0,
        })
    
    def analyze_business_positioning(self, business: Dict) -> Dict[str, Any]:
        """
        Analyze business metadata to understand brand positioning.
        Uses: name, description, category
        """
        # Build positioning text from metadata
        text_parts = []
        
        name = business.get("name", "")
        if name:
            text_parts.append(name)
        
        description = business.get("description", "")
        if description:
            text_parts.append(description)
        
        # Categories are key for positioning
        categories = business.get("category", [])
        if categories:
            if isinstance(categories, list):
                text_parts.extend(categories)
                # Track category for this business type
                primary_category = categories[0] if categories else "Unknown"
            else:
                text_parts.append(str(categories))
                primary_category = str(categories)
        else:
            primary_category = "Unknown"
        
        positioning_text = " ".join(text_parts)
        
        if len(positioning_text) > 5:
            result = self.analyzer.analyze(positioning_text)
            if result:
                # Update brand positioning by primary category
                self.brand_positioning_profiles[primary_category]["business_count"] += 1
                
                for fw, score in result.get("framework_scores", {}).items():
                    self.brand_positioning_profiles[primary_category]["framework_scores"][fw] += score
                
                for arch, score in result.get("archetype_scores", {}).items():
                    self.brand_positioning_profiles[primary_category]["archetype_scores"][arch] += score
                
                # Track all categories
                if isinstance(categories, list):
                    for cat in categories:
                        self.brand_positioning_profiles[primary_category]["categories"][cat] += 1
                
                try:
                    avg_rating = float(business.get("avg_rating", 0) or 0)
                    self.brand_positioning_profiles[primary_category]["avg_rating_sum"] += avg_rating
                except:
                    pass
                
                return result
        
        return {}
    
    def get_normalized_brand_positioning(self) -> Dict[str, Dict]:
        """Get normalized category-level positioning profiles."""
        normalized = {}
        for category, profile in self.brand_positioning_profiles.items():
            n = profile["business_count"]
            if n >= 10:  # Only categories with meaningful data
                normalized[category] = {
                    "framework_scores": {k: v/n for k, v in profile["framework_scores"].items()},
                    "archetype_scores": {k: v/n for k, v in profile["archetype_scores"].items()},
                    "business_count": n,
                    "avg_rating": profile["avg_rating_sum"] / n if profile["avg_rating_sum"] > 0 else 0,
                    "subcategories": dict(sorted(profile["categories"].items(), key=lambda x: -x[1])[:10]),
                }
        return normalized


# =============================================================================
# PROCESSING FUNCTIONS
# =============================================================================

def load_business_lookup(meta_path: Path) -> Dict[str, Dict]:
    """Load business metadata into a lookup dictionary by gmap_id."""
    lookup = {}
    logger.info(f"Loading business metadata: {meta_path.name}")
    
    try:
        with open(meta_path, 'r', encoding='utf-8', errors='replace') as f:
            count = 0
            for line in f:
                try:
                    business = json.loads(line)
                    gmap_id = business.get("gmap_id", "")
                    if gmap_id:
                        lookup[gmap_id] = {
                            "name": business.get("name", ""),
                            "description": business.get("description", ""),
                            "category": business.get("category", []),
                            "avg_rating": business.get("avg_rating", 0),
                            "num_of_reviews": business.get("num_of_reviews", 0),
                            "price": business.get("price", ""),
                            "address": business.get("address", ""),
                        }
                        count += 1
                except json.JSONDecodeError:
                    continue
        logger.info(f"  Loaded {count:,} businesses")
    except Exception as e:
        logger.error(f"Error loading metadata: {e}")
    
    return lookup


def process_state(
    state_name: str,
    review_path: Path,
    meta_path: Path,
    analyzer: GoogleMapsHyperscanAnalyzer,
    output_dir: Path,
    max_reviews: int = None,
) -> Dict[str, Any]:
    """Process reviews for a single state with brand positioning analysis."""
    
    logger.info(f"\n{'='*60}")
    logger.info(f"Processing: {state_name}")
    logger.info(f"  Reviews: {review_path.name}")
    logger.info(f"  Metadata: {meta_path.name}")
    logger.info(f"{'='*60}")
    
    # Load business metadata
    business_lookup = load_business_lookup(meta_path)
    
    # Initialize business processor for brand positioning
    business_processor = BusinessProcessor(analyzer)
    
    # Pre-analyze all businesses for positioning profiles
    logger.info(f"Analyzing business positioning from {len(business_lookup):,} businesses...")
    for gmap_id, business in business_lookup.items():
        business_processor.analyze_business_positioning(business)
    logger.info(f"  Built positioning profiles for {len(business_processor.brand_positioning_profiles):,} categories")
    
    # Aggregation structures
    framework_totals = defaultdict(float)
    archetype_totals = defaultdict(float)
    dimension_totals = defaultdict(float)
    category_customer_profiles = defaultdict(lambda: defaultdict(float))  # WHO visits each category
    business_customer_profiles = defaultdict(lambda: defaultdict(float))  # Top businesses
    rating_profiles = defaultdict(lambda: defaultdict(float))
    
    total_reviews = 0
    total_matches = 0
    enriched_count = 0
    start_time = time.time()
    
    try:
        with open(review_path, 'r', encoding='utf-8', errors='replace') as f:
            for line in f:
                try:
                    review = json.loads(line)
                except json.JSONDecodeError:
                    continue
                
                text = review.get("text", "")
                if not text or len(text) < 10:
                    continue
                
                # Analyze review text
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
                
                # Get business metadata for enrichment
                gmap_id = review.get("gmap_id", "")
                business = business_lookup.get(gmap_id, {})
                
                if business:
                    enriched_count += 1
                    
                    # Category-level customer profiling (WHO visits this type of business)
                    categories = business.get("category", [])
                    if categories and isinstance(categories, list):
                        primary_category = categories[0]
                        for arch, score in result.get("archetype_scores", {}).items():
                            category_customer_profiles[primary_category][arch] += score
                    
                    # Track top businesses (by review volume)
                    business_name = business.get("name", "Unknown")
                    for arch, score in result.get("archetype_scores", {}).items():
                        business_customer_profiles[business_name][arch] += score
                
                # Rating analysis
                try:
                    rating = int(review.get("rating", 0) or 0)
                    rating_bucket = "low" if rating <= 2 else "mid" if rating <= 3 else "high"
                    for arch, score in result.get("archetype_scores", {}).items():
                        rating_profiles[rating_bucket][arch] += score
                except:
                    pass
                
                total_reviews += 1
                total_matches += result.get("total_matches", 0)
                
                # Progress logging
                if total_reviews % 100000 == 0:
                    elapsed = time.time() - start_time
                    rate = total_reviews / elapsed if elapsed > 0 else 0
                    enrich_pct = (enriched_count / total_reviews * 100) if total_reviews > 0 else 0
                    logger.info(f"  {state_name}: {total_reviews:,} reviews ({rate:,.0f}/sec, {enrich_pct:.1f}% enriched)")
                    
                    if total_reviews % 500000 == 0:
                        gc.collect()
                
                if max_reviews and total_reviews >= max_reviews:
                    logger.info(f"  Reached max_reviews limit: {max_reviews}")
                    break
    
    except Exception as e:
        logger.error(f"Error processing {review_path}: {e}")
        raise
    
    elapsed = time.time() - start_time
    rate = total_reviews / elapsed if elapsed > 0 else 0
    enrich_pct = (enriched_count / total_reviews * 100) if total_reviews > 0 else 0
    logger.info(f"COMPLETED {state_name}: {total_reviews:,} reviews in {elapsed:.1f}s ({rate:,.0f}/sec, {enrich_pct:.1f}% enriched)")
    
    # Get normalized brand positioning
    brand_positioning = business_processor.get_normalized_brand_positioning()
    logger.info(f"  Brand positioning profiles for {len(brand_positioning):,} categories")
    
    # Compute category-customer alignment
    alignment_analysis = compute_category_alignment(
        brand_positioning,
        {k: dict(v) for k, v in category_customer_profiles.items()}
    )
    
    # Build result
    result = {
        "state": state_name,
        "review_file": str(review_path),
        "meta_file": str(meta_path),
        "total_reviews": total_reviews,
        "total_matches": total_matches,
        "enriched_count": enriched_count,
        "businesses_loaded": len(business_lookup),
        "processing_time_sec": elapsed,
        "framework_totals": dict(framework_totals),
        "archetype_totals": dict(archetype_totals),
        "dimension_totals": dict(dimension_totals),
        "category_customer_profiles": {k: dict(v) for k, v in category_customer_profiles.items()},
        "rating_profiles": {k: dict(v) for k, v in rating_profiles.items()},
        "brand_positioning_profiles": brand_positioning,
        "category_alignment": alignment_analysis,
        # Store top 100 businesses by review volume
        "top_businesses": {
            k: dict(v) for k, v in sorted(
                business_customer_profiles.items(),
                key=lambda x: sum(x[1].values()),
                reverse=True
            )[:100]
        },
    }
    
    # Save checkpoint
    checkpoint_path = output_dir / f"checkpoint_google_{state_name.lower().replace(' ', '_')}.json"
    with open(checkpoint_path, 'w') as f:
        json.dump(result, f, indent=2, default=str)
    logger.info(f"Checkpoint saved: {checkpoint_path}")
    
    return result


def compute_category_alignment(
    category_positioning: Dict[str, Dict],
    category_customer_profiles: Dict[str, Dict]
) -> Dict[str, Any]:
    """Compute alignment between category positioning and customer psychology."""
    
    alignments = {}
    total_alignment = 0.0
    aligned_count = 0
    
    for category in set(category_positioning.keys()) & set(category_customer_profiles.keys()):
        cat_pos = category_positioning[category].get("archetype_scores", {})
        customer_prof = category_customer_profiles[category]
        
        # Normalize
        total_cust = sum(customer_prof.values())
        if total_cust > 0:
            customer_prof_norm = {k: v/total_cust for k, v in customer_prof.items()}
        else:
            continue
        
        total_cat = sum(cat_pos.values())
        if total_cat > 0:
            cat_pos_norm = {k: v/total_cat for k, v in cat_pos.items()}
        else:
            continue
        
        # Cosine similarity
        common_keys = set(cat_pos_norm.keys()) & set(customer_prof_norm.keys())
        if not common_keys:
            continue
        
        dot_product = sum(cat_pos_norm.get(k, 0) * customer_prof_norm.get(k, 0) for k in common_keys)
        cat_mag = sum(v**2 for v in cat_pos_norm.values()) ** 0.5
        cust_mag = sum(v**2 for v in customer_prof_norm.values()) ** 0.5
        
        if cat_mag > 0 and cust_mag > 0:
            alignment = dot_product / (cat_mag * cust_mag)
        else:
            alignment = 0.0
        
        alignments[category] = {
            "alignment_score": alignment,
            "category_primary_archetype": max(cat_pos_norm, key=cat_pos_norm.get) if cat_pos_norm else "unknown",
            "customer_primary_archetype": max(customer_prof_norm, key=customer_prof_norm.get) if customer_prof_norm else "unknown",
            "business_count": category_positioning[category].get("business_count", 0),
        }
        
        total_alignment += alignment
        aligned_count += 1
    
    avg_alignment = total_alignment / aligned_count if aligned_count > 0 else 0.0
    
    return {
        "category_alignments": alignments,
        "average_alignment": avg_alignment,
        "total_categories_analyzed": aligned_count,
    }


def aggregate_all_states(output_dir: Path) -> Dict[str, Any]:
    """Aggregate results from all state checkpoints."""
    logger.info("Aggregating all state results...")
    
    unified = {
        "framework_totals": defaultdict(float),
        "archetype_totals": defaultdict(float),
        "category_profiles": defaultdict(lambda: defaultdict(float)),
        "state_summaries": {},
        "total_reviews": 0,
        "states_processed": [],
    }
    
    for checkpoint_file in sorted(output_dir.glob("checkpoint_google_*.json")):
        logger.info(f"  Loading {checkpoint_file.name}")
        with open(checkpoint_file, 'r') as f:
            data = json.load(f)
        
        state = data.get("state", "unknown")
        unified["states_processed"].append(state)
        unified["total_reviews"] += data.get("total_reviews", 0)
        
        for fw, score in data.get("framework_totals", {}).items():
            unified["framework_totals"][fw] += score
        
        for arch, score in data.get("archetype_totals", {}).items():
            unified["archetype_totals"][arch] += score
        
        # Aggregate category profiles
        for cat, profiles in data.get("category_customer_profiles", {}).items():
            for arch, score in profiles.items():
                unified["category_profiles"][cat][arch] += score
        
        # State summary
        unified["state_summaries"][state] = {
            "total_reviews": data.get("total_reviews", 0),
            "businesses": data.get("businesses_loaded", 0),
            "enriched_pct": data.get("enriched_count", 0) / max(data.get("total_reviews", 1), 1) * 100,
        }
    
    # Convert defaultdicts
    unified["framework_totals"] = dict(unified["framework_totals"])
    unified["archetype_totals"] = dict(unified["archetype_totals"])
    unified["category_profiles"] = {k: dict(v) for k, v in unified["category_profiles"].items()}
    
    return unified


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="ADAM Google Maps Review Processing")
    parser.add_argument("--data-dir", type=str,
                       default="/Users/chrisnocera/Sites/adam-platform/google_location_reviews",
                       help="Directory containing Google Maps review/meta files")
    parser.add_argument("--output-dir", type=str,
                       default="/Users/chrisnocera/Sites/adam-platform/data/learning/google_maps",
                       help="Output directory for checkpoints")
    parser.add_argument("--states", type=str, nargs="+",
                       help="Specific states to process")
    parser.add_argument("--max-reviews", type=int, default=None,
                       help="Maximum reviews per state (for testing)")
    parser.add_argument("--resume", action="store_true",
                       help="Resume from existing checkpoints")
    parser.add_argument("--aggregate-only", action="store_true",
                       help="Only aggregate existing checkpoints")
    
    args = parser.parse_args()
    
    data_dir = Path(args.data_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info("=" * 60)
    logger.info("ADAM GOOGLE MAPS HYPERSCAN PIPELINE")
    logger.info("=" * 60)
    logger.info(f"Data directory: {data_dir}")
    logger.info(f"Output directory: {output_dir}")
    
    if args.aggregate_only:
        unified = aggregate_all_states(output_dir)
        priors_path = output_dir / "google_maps_priors.json"
        with open(priors_path, 'w') as f:
            json.dump(unified, f, indent=2)
        logger.info(f"Unified priors saved: {priors_path}")
        logger.info(f"Total reviews across all states: {unified['total_reviews']:,}")
        return
    
    # Find all state pairs
    review_files = sorted(data_dir.glob("review-*.json"))
    
    if not review_files:
        logger.error(f"No review files found in {data_dir}")
        return
    
    # Build state list
    states_to_process = []
    for review_file in review_files:
        state_name = review_file.stem.replace("review-", "")
        meta_file = data_dir / f"meta-{state_name}.json"
        
        if meta_file.exists():
            if args.states and state_name not in args.states:
                continue
            states_to_process.append((state_name, review_file, meta_file))
        else:
            logger.warning(f"Missing metadata for {state_name}")
    
    logger.info(f"States to process: {len(states_to_process)}")
    
    # Check for existing checkpoints
    existing_checkpoints = set()
    if args.resume:
        for f in output_dir.glob("checkpoint_google_*.json"):
            state_name = f.stem.replace("checkpoint_google_", "")
            existing_checkpoints.add(state_name)
        logger.info(f"Found {len(existing_checkpoints)} existing checkpoints")
    
    # Create analyzer (once, reuse for all states)
    analyzer = GoogleMapsHyperscanAnalyzer()
    
    # Process each state
    for state_name, review_path, meta_path in states_to_process:
        checkpoint_name = state_name.lower().replace(" ", "_")
        
        if args.resume and checkpoint_name in existing_checkpoints:
            logger.info(f"Skipping {state_name} (checkpoint exists)")
            continue
        
        try:
            process_state(
                state_name,
                review_path,
                meta_path,
                analyzer,
                output_dir,
                max_reviews=args.max_reviews
            )
        except Exception as e:
            logger.error(f"Error processing {state_name}: {e}", exc_info=True)
            continue
        
        # Clear memory between states
        gc.collect()
    
    # Final aggregation
    logger.info("\n" + "=" * 60)
    logger.info("FINAL AGGREGATION")
    logger.info("=" * 60)
    
    unified = aggregate_all_states(output_dir)
    priors_path = output_dir / "google_maps_priors.json"
    with open(priors_path, 'w') as f:
        json.dump(unified, f, indent=2)
    
    logger.info(f"\nUnified priors saved: {priors_path}")
    logger.info(f"Total reviews across all states: {unified['total_reviews']:,}")
    logger.info(f"States processed: {unified['states_processed']}")
    
    logger.info("\n" + "=" * 60)
    logger.info("GOOGLE MAPS PROCESSING COMPLETE")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
