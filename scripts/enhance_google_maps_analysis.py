#!/usr/bin/env python3
"""
ADAM GOOGLE MAPS ENHANCED ANALYSIS
==================================

Post-processing script to enhance Google Maps checkpoint data with:
1. Population data integration (state-level from US Census 2020)
2. Location uniqueness metrics
3. Business density analysis
4. Category diversity indices
5. Psychological profile uniqueness scoring

Can be run after the main hyperscan processing completes.

Author: ADAM Platform
"""

import json
import logging
import math
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Tuple, Optional

# Add scripts directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

try:
    from political_enrichment import get_political_enrichment, PoliticalEnrichment
    POLITICAL_ENRICHMENT_AVAILABLE = True
except ImportError:
    POLITICAL_ENRICHMENT_AVAILABLE = False
    
try:
    from cultural_values_proxy import (
        compute_cultural_profile, 
        profile_to_dict, 
        get_advertising_implications
    )
    CULTURAL_VALUES_AVAILABLE = True
except ImportError:
    CULTURAL_VALUES_AVAILABLE = False

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# =============================================================================
# US STATE POPULATION DATA (2020 Census)
# =============================================================================

STATE_POPULATION = {
    # State name -> population (2020 Census)
    "Alabama": 5024279,
    "Alaska": 733391,
    "Arizona": 7151502,
    "Arkansas": 3011524,
    "California": 39538223,
    "Colorado": 5773714,
    "Connecticut": 3605944,
    "Delaware": 989948,
    "District_of_Columbia": 689545,
    "Florida": 21538187,
    "Georgia": 10711908,
    "Hawaii": 1455271,
    "Idaho": 1839106,
    "Illinois": 12812508,
    "Indiana": 6785528,
    "Iowa": 3190369,
    "Kansas": 2937880,
    "Kentucky": 4505836,
    "Louisiana": 4657757,
    "Maine": 1362359,
    "Maryland": 6177224,
    "Massachusetts": 7029917,
    "Michigan": 10077331,
    "Minnesota": 5706494,
    "Mississippi": 2961279,
    "Missouri": 6154913,
    "Montana": 1084225,
    "Nebraska": 1961504,
    "Nevada": 3104614,
    "New_Hampshire": 1377529,
    "New_Jersey": 9288994,
    "New_Mexico": 2117522,
    "New_York": 20201249,
    "North_Carolina": 10439388,
    "North_Dakota": 779094,
    "Ohio": 11799448,
    "Oklahoma": 3959353,
    "Oregon": 4237256,
    "Pennsylvania": 13002700,
    "Rhode_Island": 1097379,
    "South_Carolina": 5118425,
    "South_Dakota": 886667,
    "Tennessee": 6910840,
    "Texas": 29145505,
    "Utah": 3271616,
    "Vermont": 643077,
    "Virginia": 8631393,
    "Washington": 7705281,
    "West_Virginia": 1793716,
    "Wisconsin": 5893718,
    "Wyoming": 576851,
}

# State area in square miles (for density calculations)
STATE_AREA_SQ_MI = {
    "Alabama": 52420,
    "Alaska": 665384,
    "Arizona": 113990,
    "Arkansas": 53179,
    "California": 163695,
    "Colorado": 104094,
    "Connecticut": 5543,
    "Delaware": 2489,
    "District_of_Columbia": 68,
    "Florida": 65758,
    "Georgia": 59425,
    "Hawaii": 10932,
    "Idaho": 83569,
    "Illinois": 57914,
    "Indiana": 36420,
    "Iowa": 56273,
    "Kansas": 82278,
    "Kentucky": 40408,
    "Louisiana": 52378,
    "Maine": 35380,
    "Maryland": 12406,
    "Massachusetts": 10554,
    "Michigan": 96714,
    "Minnesota": 86936,
    "Mississippi": 48432,
    "Missouri": 69707,
    "Montana": 147040,
    "Nebraska": 77348,
    "Nevada": 110572,
    "New_Hampshire": 9349,
    "New_Jersey": 8723,
    "New_Mexico": 121590,
    "New_York": 54555,
    "North_Carolina": 53819,
    "North_Dakota": 70698,
    "Ohio": 44826,
    "Oklahoma": 69899,
    "Oregon": 98379,
    "Pennsylvania": 46054,
    "Rhode_Island": 1545,
    "South_Carolina": 32020,
    "South_Dakota": 77116,
    "Tennessee": 42144,
    "Texas": 268596,
    "Utah": 84897,
    "Vermont": 9616,
    "Virginia": 42775,
    "Washington": 71298,
    "West_Virginia": 24230,
    "Wisconsin": 65496,
    "Wyoming": 97813,
}

# =============================================================================
# POLITICAL LEANING DATA (2020 Presidential Election Results)
# =============================================================================

# State -> (Trump %, Biden %, Margin, Lean)
# Positive margin = Republican lean, Negative = Democratic lean
STATE_POLITICAL = {
    "Alabama": {"trump_pct": 62.0, "biden_pct": 36.6, "margin": 25.4, "lean": "strong_republican"},
    "Alaska": {"trump_pct": 52.8, "biden_pct": 42.8, "margin": 10.0, "lean": "republican"},
    "Arizona": {"trump_pct": 49.1, "biden_pct": 49.4, "margin": -0.3, "lean": "swing"},
    "Arkansas": {"trump_pct": 62.4, "biden_pct": 34.8, "margin": 27.6, "lean": "strong_republican"},
    "California": {"trump_pct": 34.3, "biden_pct": 63.5, "margin": -29.2, "lean": "strong_democratic"},
    "Colorado": {"trump_pct": 41.9, "biden_pct": 55.4, "margin": -13.5, "lean": "democratic"},
    "Connecticut": {"trump_pct": 39.2, "biden_pct": 59.3, "margin": -20.1, "lean": "strong_democratic"},
    "Delaware": {"trump_pct": 39.8, "biden_pct": 58.7, "margin": -18.9, "lean": "democratic"},
    "District_of_Columbia": {"trump_pct": 5.4, "biden_pct": 92.2, "margin": -86.8, "lean": "strong_democratic"},
    "Florida": {"trump_pct": 51.2, "biden_pct": 47.9, "margin": 3.3, "lean": "lean_republican"},
    "Georgia": {"trump_pct": 49.2, "biden_pct": 49.5, "margin": -0.3, "lean": "swing"},
    "Hawaii": {"trump_pct": 34.3, "biden_pct": 63.7, "margin": -29.4, "lean": "strong_democratic"},
    "Idaho": {"trump_pct": 63.8, "biden_pct": 33.1, "margin": 30.7, "lean": "strong_republican"},
    "Illinois": {"trump_pct": 40.6, "biden_pct": 57.5, "margin": -16.9, "lean": "democratic"},
    "Indiana": {"trump_pct": 57.0, "biden_pct": 41.0, "margin": 16.0, "lean": "republican"},
    "Iowa": {"trump_pct": 53.1, "biden_pct": 44.9, "margin": 8.2, "lean": "republican"},
    "Kansas": {"trump_pct": 56.2, "biden_pct": 41.6, "margin": 14.6, "lean": "republican"},
    "Kentucky": {"trump_pct": 62.1, "biden_pct": 36.2, "margin": 25.9, "lean": "strong_republican"},
    "Louisiana": {"trump_pct": 58.5, "biden_pct": 39.9, "margin": 18.6, "lean": "republican"},
    "Maine": {"trump_pct": 44.0, "biden_pct": 53.1, "margin": -9.1, "lean": "lean_democratic"},
    "Maryland": {"trump_pct": 32.2, "biden_pct": 65.4, "margin": -33.2, "lean": "strong_democratic"},
    "Massachusetts": {"trump_pct": 32.1, "biden_pct": 65.6, "margin": -33.5, "lean": "strong_democratic"},
    "Michigan": {"trump_pct": 47.8, "biden_pct": 50.6, "margin": -2.8, "lean": "lean_democratic"},
    "Minnesota": {"trump_pct": 45.3, "biden_pct": 52.4, "margin": -7.1, "lean": "lean_democratic"},
    "Mississippi": {"trump_pct": 57.6, "biden_pct": 41.1, "margin": 16.5, "lean": "republican"},
    "Missouri": {"trump_pct": 56.8, "biden_pct": 41.4, "margin": 15.4, "lean": "republican"},
    "Montana": {"trump_pct": 56.9, "biden_pct": 40.5, "margin": 16.4, "lean": "republican"},
    "Nebraska": {"trump_pct": 58.2, "biden_pct": 39.2, "margin": 19.0, "lean": "republican"},
    "Nevada": {"trump_pct": 47.7, "biden_pct": 50.1, "margin": -2.4, "lean": "lean_democratic"},
    "New_Hampshire": {"trump_pct": 45.4, "biden_pct": 52.7, "margin": -7.3, "lean": "lean_democratic"},
    "New_Jersey": {"trump_pct": 41.4, "biden_pct": 57.3, "margin": -15.9, "lean": "democratic"},
    "New_Mexico": {"trump_pct": 43.5, "biden_pct": 54.3, "margin": -10.8, "lean": "democratic"},
    "New_York": {"trump_pct": 37.7, "biden_pct": 60.9, "margin": -23.2, "lean": "strong_democratic"},
    "North_Carolina": {"trump_pct": 49.9, "biden_pct": 48.6, "margin": 1.3, "lean": "swing"},
    "North_Dakota": {"trump_pct": 65.1, "biden_pct": 31.8, "margin": 33.3, "lean": "strong_republican"},
    "Ohio": {"trump_pct": 53.3, "biden_pct": 45.2, "margin": 8.1, "lean": "republican"},
    "Oklahoma": {"trump_pct": 65.4, "biden_pct": 32.3, "margin": 33.1, "lean": "strong_republican"},
    "Oregon": {"trump_pct": 40.4, "biden_pct": 56.5, "margin": -16.1, "lean": "democratic"},
    "Pennsylvania": {"trump_pct": 48.8, "biden_pct": 50.0, "margin": -1.2, "lean": "swing"},
    "Rhode_Island": {"trump_pct": 38.6, "biden_pct": 59.4, "margin": -20.8, "lean": "strong_democratic"},
    "South_Carolina": {"trump_pct": 55.1, "biden_pct": 43.4, "margin": 11.7, "lean": "republican"},
    "South_Dakota": {"trump_pct": 61.8, "biden_pct": 35.6, "margin": 26.2, "lean": "strong_republican"},
    "Tennessee": {"trump_pct": 60.7, "biden_pct": 37.5, "margin": 23.2, "lean": "strong_republican"},
    "Texas": {"trump_pct": 52.1, "biden_pct": 46.5, "margin": 5.6, "lean": "lean_republican"},
    "Utah": {"trump_pct": 58.1, "biden_pct": 37.6, "margin": 20.5, "lean": "republican"},
    "Vermont": {"trump_pct": 30.7, "biden_pct": 66.1, "margin": -35.4, "lean": "strong_democratic"},
    "Virginia": {"trump_pct": 44.0, "biden_pct": 54.1, "margin": -10.1, "lean": "democratic"},
    "Washington": {"trump_pct": 38.8, "biden_pct": 58.0, "margin": -19.2, "lean": "democratic"},
    "West_Virginia": {"trump_pct": 68.6, "biden_pct": 29.7, "margin": 38.9, "lean": "strong_republican"},
    "Wisconsin": {"trump_pct": 48.8, "biden_pct": 49.4, "margin": -0.6, "lean": "swing"},
    "Wyoming": {"trump_pct": 69.9, "biden_pct": 26.6, "margin": 43.3, "lean": "strong_republican"},
}

# Political lean categories for psychological correlation
POLITICAL_LEAN_CATEGORIES = {
    "strong_republican": {"ideology": "conservative", "margin_range": ">20R"},
    "republican": {"ideology": "conservative", "margin_range": "10-20R"},
    "lean_republican": {"ideology": "center-right", "margin_range": "3-10R"},
    "swing": {"ideology": "moderate", "margin_range": "-3 to +3"},
    "lean_democratic": {"ideology": "center-left", "margin_range": "3-10D"},
    "democratic": {"ideology": "liberal", "margin_range": "10-20D"},
    "strong_democratic": {"ideology": "progressive", "margin_range": ">20D"},
}


# Regional classifications for comparative analysis
STATE_REGIONS = {
    "Northeast": ["Connecticut", "Maine", "Massachusetts", "New_Hampshire", "Rhode_Island", 
                  "Vermont", "New_Jersey", "New_York", "Pennsylvania"],
    "Midwest": ["Illinois", "Indiana", "Michigan", "Ohio", "Wisconsin", "Iowa", "Kansas", 
                "Minnesota", "Missouri", "Nebraska", "North_Dakota", "South_Dakota"],
    "South": ["Delaware", "Florida", "Georgia", "Maryland", "North_Carolina", "South_Carolina",
              "Virginia", "District_of_Columbia", "West_Virginia", "Alabama", "Kentucky",
              "Mississippi", "Tennessee", "Arkansas", "Louisiana", "Oklahoma", "Texas"],
    "West": ["Arizona", "Colorado", "Idaho", "Montana", "Nevada", "New_Mexico", "Utah",
             "Wyoming", "Alaska", "California", "Hawaii", "Oregon", "Washington"],
}

# Reverse lookup: state -> region
STATE_TO_REGION = {}
for region, states in STATE_REGIONS.items():
    for state in states:
        STATE_TO_REGION[state] = region


# =============================================================================
# UNIQUENESS ANALYSIS FUNCTIONS
# =============================================================================

def compute_category_diversity_index(category_profiles: Dict[str, Dict]) -> Dict[str, float]:
    """
    Compute Shannon diversity index for business categories.
    Higher values = more diverse business ecosystem.
    """
    total_activity = sum(
        sum(archetypes.values()) 
        for archetypes in category_profiles.values()
    )
    
    if total_activity == 0:
        return {"diversity_index": 0, "effective_categories": 0}
    
    # Compute proportions
    proportions = []
    for cat, archetypes in category_profiles.items():
        cat_total = sum(archetypes.values())
        if cat_total > 0:
            p = cat_total / total_activity
            proportions.append(p)
    
    # Shannon diversity: H = -Σ(p * ln(p))
    shannon_h = -sum(p * math.log(p) for p in proportions if p > 0)
    
    # Effective number of categories (exponential of Shannon)
    effective_categories = math.exp(shannon_h) if shannon_h > 0 else 1
    
    return {
        "diversity_index": shannon_h,
        "effective_categories": effective_categories,
        "total_categories": len(proportions),
        "concentration_ratio_top5": sum(sorted(proportions, reverse=True)[:5]) if proportions else 0,
    }


def compute_archetype_uniqueness(archetype_totals: Dict[str, float], 
                                  national_average: Dict[str, float] = None) -> Dict[str, Any]:
    """
    Compute how unique a location's archetype distribution is compared to national average.
    """
    if not archetype_totals:
        return {}
    
    # Normalize local distribution
    total = sum(archetype_totals.values())
    if total == 0:
        return {}
    
    local_dist = {k: v/total for k, v in archetype_totals.items()}
    
    # Default national average (will be computed from aggregation)
    if national_average is None:
        national_average = {
            "achiever": 0.25,
            "explorer": 0.25,
            "connector": 0.15,
            "guardian": 0.15,
            "pragmatist": 0.20,
        }
    
    # Compute divergence from national average
    divergences = {}
    for archetype in local_dist:
        local_pct = local_dist.get(archetype, 0)
        national_pct = national_average.get(archetype, 0.2)
        divergence = (local_pct - national_pct) / national_pct if national_pct > 0 else 0
        divergences[archetype] = {
            "local_pct": local_pct,
            "national_pct": national_pct,
            "divergence_pct": divergence * 100,
        }
    
    # Overall uniqueness score (sum of absolute divergences)
    uniqueness_score = sum(abs(d["divergence_pct"]) for d in divergences.values()) / len(divergences)
    
    # Dominant archetype
    dominant = max(local_dist, key=local_dist.get)
    
    return {
        "archetype_divergences": divergences,
        "uniqueness_score": uniqueness_score,
        "dominant_archetype": dominant,
        "dominant_pct": local_dist[dominant] * 100,
    }


def compute_category_uniqueness(category_profiles: Dict[str, Dict],
                                 national_categories: Dict[str, float] = None) -> Dict[str, Any]:
    """
    Identify unique/distinctive business categories for a location.
    """
    if not category_profiles:
        return {}
    
    # Compute local category totals
    local_totals = {}
    total_activity = 0
    for cat, archetypes in category_profiles.items():
        cat_total = sum(archetypes.values())
        local_totals[cat] = cat_total
        total_activity += cat_total
    
    if total_activity == 0:
        return {}
    
    # Normalize
    local_dist = {k: v/total_activity for k, v in local_totals.items()}
    
    # Find over-represented categories (compared to uniform distribution)
    n_categories = len(local_dist)
    uniform_pct = 1.0 / n_categories if n_categories > 0 else 0
    
    over_represented = []
    under_represented = []
    
    for cat, pct in sorted(local_dist.items(), key=lambda x: -x[1])[:50]:
        if pct > uniform_pct * 2:  # More than 2x expected
            over_represented.append({
                "category": cat,
                "local_pct": pct * 100,
                "over_index": pct / uniform_pct if uniform_pct > 0 else 0,
            })
        elif pct < uniform_pct * 0.5:  # Less than half expected
            under_represented.append({
                "category": cat,
                "local_pct": pct * 100,
                "under_index": uniform_pct / pct if pct > 0 else 0,
            })
    
    return {
        "top_categories": list(local_dist.items())[:20],
        "over_represented": over_represented[:10],
        "under_represented": under_represented[:10],
        "category_concentration": local_dist.get(max(local_dist, key=local_dist.get), 0) if local_dist else 0,
    }


def compute_rating_patterns(rating_profiles: Dict[str, Dict]) -> Dict[str, Any]:
    """
    Analyze rating distribution patterns for psychological insights.
    """
    if not rating_profiles:
        return {}
    
    # Compute totals per rating bucket
    low_total = sum(rating_profiles.get("low", {}).values())
    mid_total = sum(rating_profiles.get("mid", {}).values())
    high_total = sum(rating_profiles.get("high", {}).values())
    total = low_total + mid_total + high_total
    
    if total == 0:
        return {}
    
    # Rating distribution
    rating_dist = {
        "low_pct": low_total / total * 100,
        "mid_pct": mid_total / total * 100,
        "high_pct": high_total / total * 100,
    }
    
    # Sentiment polarity (high vs low)
    polarity = (high_total - low_total) / total if total > 0 else 0
    
    # Archetype differences by rating
    archetype_by_rating = {}
    for rating_bucket in ["low", "mid", "high"]:
        if rating_bucket in rating_profiles:
            bucket_total = sum(rating_profiles[rating_bucket].values())
            if bucket_total > 0:
                archetype_by_rating[rating_bucket] = {
                    k: v/bucket_total for k, v in rating_profiles[rating_bucket].items()
                }
    
    return {
        "rating_distribution": rating_dist,
        "sentiment_polarity": polarity,
        "polarity_label": "positive" if polarity > 0.3 else "negative" if polarity < -0.1 else "neutral",
        "archetype_by_rating": archetype_by_rating,
    }


def compute_population_metrics(state_name: str, data: Dict) -> Dict[str, Any]:
    """
    Compute population-adjusted metrics for a state.
    """
    population = STATE_POPULATION.get(state_name, 0)
    area = STATE_AREA_SQ_MI.get(state_name, 0)
    region = STATE_TO_REGION.get(state_name, "Unknown")
    
    total_reviews = data.get("total_reviews", 0)
    businesses_loaded = data.get("businesses_loaded", 0)
    
    metrics = {
        "population": population,
        "area_sq_mi": area,
        "region": region,
        "population_density": population / area if area > 0 else 0,
    }
    
    if population > 0:
        metrics["reviews_per_1000_pop"] = (total_reviews / population) * 1000
        metrics["businesses_per_1000_pop"] = (businesses_loaded / population) * 1000
    else:
        metrics["reviews_per_1000_pop"] = 0
        metrics["businesses_per_1000_pop"] = 0
    
    if businesses_loaded > 0:
        metrics["reviews_per_business"] = total_reviews / businesses_loaded
    else:
        metrics["reviews_per_business"] = 0
    
    return metrics


def compute_political_metrics(state_name: str) -> Dict[str, Any]:
    """
    Get political leaning data for a state.
    """
    political = STATE_POLITICAL.get(state_name, {})
    
    if not political:
        return {"available": False}
    
    lean = political.get("lean", "unknown")
    lean_info = POLITICAL_LEAN_CATEGORIES.get(lean, {})
    
    return {
        "available": True,
        "trump_pct_2020": political.get("trump_pct", 0),
        "biden_pct_2020": political.get("biden_pct", 0),
        "margin_2020": political.get("margin", 0),
        "political_lean": lean,
        "ideology_label": lean_info.get("ideology", "unknown"),
        "margin_category": lean_info.get("margin_range", "unknown"),
        # Simplified lean score: -1 (strong D) to +1 (strong R)
        "lean_score": political.get("margin", 0) / 50.0,  # Normalized
    }


def compute_political_archetype_correlation(
    archetype_totals: Dict[str, float],
    political_metrics: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Analyze correlation between political leaning and psychological archetypes.
    
    This helps understand if certain archetypes are more prevalent in 
    different political environments.
    """
    if not political_metrics.get("available") or not archetype_totals:
        return {}
    
    total = sum(archetype_totals.values())
    if total == 0:
        return {}
    
    # Normalize archetype distribution
    archetype_dist = {k: v/total for k, v in archetype_totals.items()}
    
    lean_score = political_metrics.get("lean_score", 0)
    political_lean = political_metrics.get("political_lean", "unknown")
    
    # Track archetype prevalence by political lean
    # This data can be aggregated across states to find patterns
    return {
        "political_lean": political_lean,
        "lean_score": lean_score,
        "archetype_distribution": archetype_dist,
        "dominant_archetype": max(archetype_dist, key=archetype_dist.get),
        # Correlation hypothesis markers
        "correlation_data": {
            "achiever_pct": archetype_dist.get("achiever", 0),
            "explorer_pct": archetype_dist.get("explorer", 0),
            "connector_pct": archetype_dist.get("connector", 0),
            "guardian_pct": archetype_dist.get("guardian", 0),
            "pragmatist_pct": archetype_dist.get("pragmatist", 0),
            "lean_score": lean_score,
        }
    }


def compute_cultural_values_profile(
    state_name: str,
    political_metrics: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Compute cultural values profile based on political lean.
    
    Uses research-based correlations to estimate:
    - Moral foundations (Haidt)
    - World values (Inglehart-Welzel)
    - Decision-making style
    - Religiosity
    """
    if not CULTURAL_VALUES_AVAILABLE:
        return {"available": False, "reason": "Cultural values module not loaded"}
    
    if not political_metrics.get("available"):
        return {"available": False, "reason": "Political metrics not available"}
    
    lean_score = political_metrics.get("lean_score", 0)
    
    # Compute full cultural profile
    profile = compute_cultural_profile(lean_score, state_name)
    profile_dict = profile_to_dict(profile)
    
    # Get advertising implications
    ad_implications = get_advertising_implications(profile)
    
    return {
        "available": True,
        "lean_score_used": lean_score,
        "moral_foundations": profile_dict["moral_foundations"],
        "world_values": profile_dict["world_values"],
        "decision_style": profile_dict["decision_style"],
        "religiosity": profile_dict["religiosity"],
        "summary": profile_dict["summary"],
        "advertising_implications": ad_implications,
    }


def compute_zip_level_political_distribution(
    data: Dict[str, Any],
    state_name: str
) -> Dict[str, Any]:
    """
    Compute ZIP code level political distribution for a state.
    
    Uses the ZIP codes found in the business data to create a granular
    political profile of where reviews/businesses are actually located.
    """
    if not POLITICAL_ENRICHMENT_AVAILABLE:
        return {"available": False, "reason": "Political enrichment module not loaded"}
    
    try:
        enrichment = get_political_enrichment()
        enrichment.load_data()
    except Exception as e:
        return {"available": False, "reason": str(e)}
    
    # Extract ZIP codes from category profiles (if available)
    # The Google Maps data includes postal codes in metadata
    category_profiles = data.get("category_customer_profiles", {})
    
    # Aggregate political lean by reviews weighted
    lean_distribution = defaultdict(lambda: {"count": 0, "reviews": 0})
    zip_data = []
    
    # Get state-level political data as baseline
    state_political = enrichment.get_political_by_state(state_name.lower().replace("_", " "))
    
    if not state_political:
        return {
            "available": False,
            "reason": f"State '{state_name}' not found in political data",
        }
    
    # Return state-level for now with enhanced granularity info
    # Full ZIP-level would require integrating with the business metadata during processing
    state_political["available"] = True
    state_political["granularity"] = "state"
    state_political["note"] = "ZIP-level requires business postal code integration"
    
    # Get county breakdown for the state
    county_breakdown = []
    for (county, state), pol_data in enrichment.county_to_political.items():
        if state == state_name.lower().replace("_", " "):
            county_breakdown.append({
                "county": county,
                "lean_category": pol_data.get("lean_category"),
                "lean_score": pol_data.get("lean_score"),
                "total_votes": pol_data.get("total_votes", 0),
            })
    
    # Sort by vote count to show most populous counties
    county_breakdown.sort(key=lambda x: -x.get("total_votes", 0))
    
    # Aggregate county distribution
    county_lean_dist = defaultdict(int)
    for county in county_breakdown:
        county_lean_dist[county.get("lean_category", "unknown")] += 1
    
    return {
        "available": True,
        "granularity": "county",
        "state_overall": {
            "lean_category": state_political.get("lean_category"),
            "lean_score": state_political.get("lean_score"),
            "margin": state_political.get("margin"),
            "ideology_label": state_political.get("ideology_label"),
        },
        "counties_total": len(county_breakdown),
        "county_lean_distribution": dict(county_lean_dist),
        "top_10_counties": county_breakdown[:10],
    }


def compute_location_profile(state_name: str, data: Dict) -> Dict[str, Any]:
    """
    Generate comprehensive location profile combining all uniqueness metrics.
    """
    profile = {
        "state": state_name,
        "summary": {},
        "population_metrics": {},
        "political_metrics": {},
        "cultural_values": {},
        "political_distribution": {},
        "political_archetype_correlation": {},
        "diversity_metrics": {},
        "archetype_analysis": {},
        "category_analysis": {},
        "rating_analysis": {},
        "location_signature": {},
    }
    
    # Population metrics
    profile["population_metrics"] = compute_population_metrics(state_name, data)
    
    # Political metrics (state-level baseline)
    profile["political_metrics"] = compute_political_metrics(state_name)
    
    # Cultural values profile (ideology, morality, religiosity, decision style)
    profile["cultural_values"] = compute_cultural_values_profile(state_name, profile["political_metrics"])
    
    # Granular political distribution (county-level when available)
    profile["political_distribution"] = compute_zip_level_political_distribution(data, state_name)
    
    # Diversity metrics
    category_profiles = data.get("category_customer_profiles", {})
    profile["diversity_metrics"] = compute_category_diversity_index(category_profiles)
    
    # Archetype analysis
    archetype_totals = data.get("archetype_totals", {})
    profile["archetype_analysis"] = compute_archetype_uniqueness(archetype_totals)
    
    # Political-archetype correlation
    profile["political_archetype_correlation"] = compute_political_archetype_correlation(
        archetype_totals,
        profile["political_metrics"]
    )
    
    # Category analysis
    profile["category_analysis"] = compute_category_uniqueness(category_profiles)
    
    # Rating analysis
    rating_profiles = data.get("rating_profiles", {})
    profile["rating_analysis"] = compute_rating_patterns(rating_profiles)
    
    # Generate location signature (key distinguishing characteristics)
    signature = []
    
    # Population-based signature
    pop = profile["population_metrics"].get("population", 0)
    if pop > 10000000:
        signature.append("mega_state")
    elif pop > 5000000:
        signature.append("large_state")
    elif pop > 1000000:
        signature.append("mid_state")
    else:
        signature.append("small_state")
    
    # Review engagement signature
    reviews_per_1k = profile["population_metrics"].get("reviews_per_1000_pop", 0)
    if reviews_per_1k > 500:
        signature.append("high_engagement")
    elif reviews_per_1k > 200:
        signature.append("moderate_engagement")
    else:
        signature.append("low_engagement")
    
    # Diversity signature
    diversity = profile["diversity_metrics"].get("diversity_index", 0)
    if diversity > 4:
        signature.append("highly_diverse_economy")
    elif diversity > 3:
        signature.append("diverse_economy")
    else:
        signature.append("concentrated_economy")
    
    # Dominant archetype signature
    if profile["archetype_analysis"]:
        dominant = profile["archetype_analysis"].get("dominant_archetype", "unknown")
        signature.append(f"{dominant}_dominant")
    
    # Sentiment signature
    if profile["rating_analysis"]:
        polarity_label = profile["rating_analysis"].get("polarity_label", "neutral")
        signature.append(f"{polarity_label}_sentiment")
    
    # Political signature
    if profile["political_metrics"].get("available"):
        political_lean = profile["political_metrics"].get("political_lean", "unknown")
        signature.append(f"political_{political_lean}")
    
    profile["location_signature"] = signature
    
    # Summary
    profile["summary"] = {
        "total_reviews": data.get("total_reviews", 0),
        "total_businesses": data.get("businesses_loaded", 0),
        "categories_tracked": len(category_profiles),
        "region": profile["population_metrics"].get("region", "Unknown"),
        "political_lean": profile["political_metrics"].get("political_lean", "Unknown"),
        "signature_tags": signature,
    }
    
    return profile


# =============================================================================
# MAIN ENHANCEMENT FUNCTION
# =============================================================================

def enhance_checkpoint(checkpoint_path: Path) -> Dict[str, Any]:
    """
    Enhance a single checkpoint with additional analysis.
    """
    logger.info(f"Enhancing: {checkpoint_path.name}")
    
    with open(checkpoint_path, 'r') as f:
        data = json.load(f)
    
    state_name = data.get("state", checkpoint_path.stem.replace("checkpoint_google_", ""))
    
    # Compute enhanced profile
    enhanced_profile = compute_location_profile(state_name, data)
    
    # Add to original data
    data["enhanced_analysis"] = enhanced_profile
    
    return data


def enhance_all_checkpoints(checkpoint_dir: Path, output_dir: Path = None):
    """
    Enhance all Google Maps checkpoints with additional analysis.
    """
    if output_dir is None:
        output_dir = checkpoint_dir
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    checkpoints = sorted(checkpoint_dir.glob("checkpoint_google_*.json"))
    logger.info(f"Found {len(checkpoints)} checkpoints to enhance")
    
    all_profiles = []
    national_totals = defaultdict(float)
    
    # First pass: collect national totals for comparison
    for checkpoint_path in checkpoints:
        with open(checkpoint_path, 'r') as f:
            data = json.load(f)
        
        for arch, score in data.get("archetype_totals", {}).items():
            national_totals[arch] += score
    
    # Normalize national totals
    total = sum(national_totals.values())
    national_average = {k: v/total for k, v in national_totals.items()} if total > 0 else {}
    
    logger.info(f"National archetype distribution: {national_average}")
    
    # Second pass: enhance with national comparison
    for checkpoint_path in checkpoints:
        enhanced_data = enhance_checkpoint(checkpoint_path)
        
        # Re-compute with national average
        if national_average:
            archetype_totals = enhanced_data.get("archetype_totals", {})
            enhanced_data["enhanced_analysis"]["archetype_analysis"] = compute_archetype_uniqueness(
                archetype_totals, 
                national_average
            )
        
        # Save enhanced version
        enhanced_path = output_dir / f"enhanced_{checkpoint_path.name}"
        with open(enhanced_path, 'w') as f:
            json.dump(enhanced_data, f, indent=2, default=str)
        logger.info(f"  Saved: {enhanced_path.name}")
        
        all_profiles.append(enhanced_data["enhanced_analysis"])
    
    # Generate comparative summary
    summary = {
        "total_states_analyzed": len(all_profiles),
        "national_archetype_distribution": national_average,
        "state_profiles": {p["state"]: p["summary"] for p in all_profiles},
        "regional_aggregates": compute_regional_aggregates(all_profiles),
        "political_psychology_analysis": compute_political_psychology_patterns(all_profiles),
        "ranking": {
            "by_reviews_per_capita": sorted(
                [(p["state"], p["population_metrics"].get("reviews_per_1000_pop", 0)) 
                 for p in all_profiles],
                key=lambda x: -x[1]
            )[:10],
            "by_diversity": sorted(
                [(p["state"], p["diversity_metrics"].get("diversity_index", 0)) 
                 for p in all_profiles],
                key=lambda x: -x[1]
            )[:10],
            "by_uniqueness": sorted(
                [(p["state"], p["archetype_analysis"].get("uniqueness_score", 0)) 
                 for p in all_profiles if p.get("archetype_analysis")],
                key=lambda x: -x[1]
            )[:10],
            "by_political_lean": sorted(
                [(p["state"], p["political_metrics"].get("margin_2020", 0)) 
                 for p in all_profiles if p.get("political_metrics", {}).get("available")],
                key=lambda x: x[1]
            ),  # Most Democratic to most Republican
        }
    }
    
    summary_path = output_dir / "google_maps_enhanced_summary.json"
    with open(summary_path, 'w') as f:
        json.dump(summary, f, indent=2, default=str)
    logger.info(f"\nEnhanced summary saved: {summary_path}")
    
    return summary


def compute_regional_aggregates(profiles: List[Dict]) -> Dict[str, Any]:
    """
    Compute regional aggregate statistics.
    """
    regional = {}
    
    for region_name in STATE_REGIONS:
        region_profiles = [p for p in profiles if p.get("population_metrics", {}).get("region") == region_name]
        
        if not region_profiles:
            continue
        
        total_reviews = sum(p.get("summary", {}).get("total_reviews", 0) for p in region_profiles)
        total_businesses = sum(p.get("summary", {}).get("total_businesses", 0) for p in region_profiles)
        avg_diversity = sum(p.get("diversity_metrics", {}).get("diversity_index", 0) for p in region_profiles) / len(region_profiles)
        
        regional[region_name] = {
            "states_count": len(region_profiles),
            "total_reviews": total_reviews,
            "total_businesses": total_businesses,
            "avg_diversity_index": avg_diversity,
        }
    
    return regional


def compute_political_psychology_patterns(profiles: List[Dict]) -> Dict[str, Any]:
    """
    Analyze patterns between political leaning and psychological archetypes across states.
    
    This reveals if certain archetypes correlate with political environments.
    """
    # Group states by political lean
    lean_groups = defaultdict(list)
    
    for profile in profiles:
        pol_corr = profile.get("political_archetype_correlation", {})
        if not pol_corr:
            continue
        
        lean = pol_corr.get("political_lean", "unknown")
        corr_data = pol_corr.get("correlation_data", {})
        
        if corr_data:
            lean_groups[lean].append(corr_data)
    
    # Compute averages per political lean group
    lean_averages = {}
    for lean, data_list in lean_groups.items():
        if not data_list:
            continue
        
        n = len(data_list)
        lean_averages[lean] = {
            "states_count": n,
            "avg_achiever": sum(d.get("achiever_pct", 0) for d in data_list) / n,
            "avg_explorer": sum(d.get("explorer_pct", 0) for d in data_list) / n,
            "avg_connector": sum(d.get("connector_pct", 0) for d in data_list) / n,
            "avg_guardian": sum(d.get("guardian_pct", 0) for d in data_list) / n,
            "avg_pragmatist": sum(d.get("pragmatist_pct", 0) for d in data_list) / n,
            "avg_lean_score": sum(d.get("lean_score", 0) for d in data_list) / n,
        }
    
    # Identify patterns
    patterns = []
    
    # Compare strong_republican vs strong_democratic
    if "strong_republican" in lean_averages and "strong_democratic" in lean_averages:
        rep = lean_averages["strong_republican"]
        dem = lean_averages["strong_democratic"]
        
        for archetype in ["achiever", "explorer", "connector", "guardian", "pragmatist"]:
            rep_avg = rep.get(f"avg_{archetype}", 0)
            dem_avg = dem.get(f"avg_{archetype}", 0)
            diff = rep_avg - dem_avg
            
            if abs(diff) > 0.02:  # More than 2% difference
                direction = "higher in Republican" if diff > 0 else "higher in Democratic"
                patterns.append({
                    "archetype": archetype,
                    "difference_pct": diff * 100,
                    "pattern": direction,
                })
    
    return {
        "lean_averages": lean_averages,
        "patterns_detected": patterns,
        "methodology": "Comparing archetype distributions across political leanings",
    }


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Enhance Google Maps checkpoint analysis")
    parser.add_argument("--checkpoint-dir", type=str,
                       default="/Users/chrisnocera/Sites/adam-platform/data/learning/google_maps",
                       help="Directory containing checkpoints")
    parser.add_argument("--output-dir", type=str, default=None,
                       help="Output directory (defaults to checkpoint-dir)")
    
    args = parser.parse_args()
    
    checkpoint_dir = Path(args.checkpoint_dir)
    output_dir = Path(args.output_dir) if args.output_dir else checkpoint_dir
    
    logger.info("=" * 60)
    logger.info("GOOGLE MAPS ENHANCED ANALYSIS")
    logger.info("=" * 60)
    
    summary = enhance_all_checkpoints(checkpoint_dir, output_dir)
    
    logger.info("\n" + "=" * 60)
    logger.info("ENHANCEMENT COMPLETE")
    logger.info("=" * 60)
    logger.info(f"States analyzed: {summary['total_states_analyzed']}")
    logger.info(f"\nTop states by review engagement (reviews per 1000 pop):")
    for state, score in summary["ranking"]["by_reviews_per_capita"][:5]:
        logger.info(f"  {state}: {score:.1f}")
    logger.info(f"\nTop states by diversity:")
    for state, score in summary["ranking"]["by_diversity"][:5]:
        logger.info(f"  {state}: {score:.2f}")
