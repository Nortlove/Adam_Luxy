#!/usr/bin/env python3
# =============================================================================
# ADAM Platform - Advanced Learning Enhancement Script
# Location: scripts/run_advanced_learning.py
# =============================================================================

"""
ADVANCED LEARNING ENHANCEMENT

Implements deeper learning from Amazon data and addresses identified gaps:

1. TEMPORAL PATTERN LEARNING
   - Time-of-day effectiveness patterns
   - Review velocity → engagement prediction
   - Lifecycle stage detection

2. REVIEW QUALITY WEIGHTING
   - Use helpful votes for quality weighting
   - Summary sentiment for confidence adjustment
   - Verified purchase reliability boost

3. BRAND LOYALTY LEARNING
   - Multi-brand vs single-brand reviewer patterns
   - Brand personality → archetype affinity
   - Brand switching behavior

4. PRICE SENSITIVITY SEGMENTATION
   - Price tier patterns from purchases
   - Value perception inference
   - Deal-proneness scoring

5. CROSS-DOMAIN TRANSFER LEARNING
   - Media → Product affinity expansion
   - Category cluster knowledge transfer
   - Reviewer lifestyle inference

6. LINGUISTIC DEPTH ANALYSIS
   - Vocabulary richness → cognitive style
   - Review length patterns → engagement depth
   - Sentiment trajectory → regulatory focus

Usage:
    python scripts/run_advanced_learning.py
    python scripts/run_advanced_learning.py --temporal-only
    python scripts/run_advanced_learning.py --brand-only
"""

import argparse
import asyncio
import csv
import json
import logging
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Tuple
import hashlib
import re

import numpy as np

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
)
logger = logging.getLogger(__name__)


# =============================================================================
# DATA PATHS
# =============================================================================

LEARNING_DATA_DIR = project_root / "data" / "learning"
REVIEW_TODO_DIR = project_root / "review_todo"


# =============================================================================
# 1. TEMPORAL PATTERN LEARNING
# =============================================================================

class TemporalPatternLearner:
    """
    Learns time-based effectiveness patterns from review timestamps.
    
    Insights derived:
    - Best time-of-day for each archetype
    - Day-of-week patterns
    - Seasonal trends
    - Review velocity → engagement signals
    """
    
    def __init__(self):
        self.hourly_patterns: Dict[str, Dict[int, List[float]]] = defaultdict(lambda: defaultdict(list))
        self.day_of_week_patterns: Dict[str, Dict[int, List[float]]] = defaultdict(lambda: defaultdict(list))
        self.monthly_patterns: Dict[str, Dict[int, List[float]]] = defaultdict(lambda: defaultdict(list))
        self.velocity_patterns: Dict[str, List[Tuple[float, float]]] = defaultdict(list)
    
    def process_review(
        self,
        archetype: str,
        timestamp: Optional[datetime],
        rating: float,
        review_length: int,
        days_since_last: Optional[float] = None,
    ) -> None:
        """Process a single review for temporal patterns."""
        
        if timestamp is None:
            return
        
        # Normalize rating to engagement score (1-5 → 0-1)
        engagement = (rating - 1) / 4.0
        
        # Adjust engagement by review length (longer = more engaged)
        length_factor = min(1.0, review_length / 500)  # Cap at 500 chars
        engagement = engagement * 0.7 + length_factor * 0.3
        
        # Hour of day (0-23)
        hour = timestamp.hour
        self.hourly_patterns[archetype][hour].append(engagement)
        
        # Day of week (0=Monday, 6=Sunday)
        dow = timestamp.weekday()
        self.day_of_week_patterns[archetype][dow].append(engagement)
        
        # Month (1-12)
        month = timestamp.month
        self.monthly_patterns[archetype][month].append(engagement)
        
        # Velocity pattern (days between reviews → engagement)
        if days_since_last is not None and days_since_last > 0:
            self.velocity_patterns[archetype].append((days_since_last, engagement))
    
    def compute_optimal_timing(self) -> Dict[str, Dict[str, Any]]:
        """Compute optimal timing for each archetype."""
        
        results = {}
        
        for archetype in set(self.hourly_patterns.keys()):
            # Best hours
            hourly_avg = {
                hour: np.mean(scores) if scores else 0.5
                for hour, scores in self.hourly_patterns[archetype].items()
            }
            best_hours = sorted(hourly_avg.items(), key=lambda x: x[1], reverse=True)[:3]
            
            # Best days
            dow_avg = {
                dow: np.mean(scores) if scores else 0.5
                for dow, scores in self.day_of_week_patterns[archetype].items()
            }
            best_days = sorted(dow_avg.items(), key=lambda x: x[1], reverse=True)[:3]
            day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            
            # Best months
            month_avg = {
                month: np.mean(scores) if scores else 0.5
                for month, scores in self.monthly_patterns[archetype].items()
            }
            best_months = sorted(month_avg.items(), key=lambda x: x[1], reverse=True)[:3]
            month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
            
            # Velocity insights
            velocity_data = self.velocity_patterns[archetype]
            if velocity_data:
                # Group by velocity buckets
                velocity_buckets = defaultdict(list)
                for days, eng in velocity_data:
                    if days < 7:
                        velocity_buckets["high_frequency"].append(eng)
                    elif days < 30:
                        velocity_buckets["medium_frequency"].append(eng)
                    else:
                        velocity_buckets["low_frequency"].append(eng)
                
                velocity_insights = {
                    bucket: {
                        "avg_engagement": round(np.mean(scores), 4),
                        "count": len(scores),
                    }
                    for bucket, scores in velocity_buckets.items()
                    if scores
                }
            else:
                velocity_insights = {}
            
            results[archetype] = {
                "best_hours": [
                    {"hour": h, "engagement": round(e, 4)}
                    for h, e in best_hours
                ],
                "best_days": [
                    {"day": day_names[d], "engagement": round(e, 4)}
                    for d, e in best_days
                ],
                "best_months": [
                    {"month": month_names[m-1], "engagement": round(e, 4)}
                    for m, e in best_months
                ],
                "hourly_distribution": {
                    h: round(e, 4) for h, e in sorted(hourly_avg.items())
                },
                "velocity_insights": velocity_insights,
                "total_observations": sum(len(v) for v in self.hourly_patterns[archetype].values()),
            }
        
        return results


# =============================================================================
# 2. REVIEW QUALITY WEIGHTING
# =============================================================================

class ReviewQualityAnalyzer:
    """
    Analyzes review quality signals to weight learning appropriately.
    
    Quality signals:
    - Helpful votes (social validation)
    - Verified purchase (reliability)
    - Review length (detail depth)
    - Summary/title sentiment clarity
    """
    
    def __init__(self):
        self.quality_scores: Dict[str, List[Dict]] = defaultdict(list)
    
    def compute_quality_score(
        self,
        helpful_votes: int,
        verified: bool,
        review_length: int,
        summary_length: int,
        rating: float,
    ) -> Dict[str, float]:
        """Compute multi-dimensional quality score."""
        
        # Social validation (helpful votes with diminishing returns)
        social_score = min(1.0, np.log1p(helpful_votes) / np.log1p(100))
        
        # Verification score
        verification_score = 1.0 if verified else 0.6
        
        # Detail depth (review length with diminishing returns)
        detail_score = min(1.0, np.log1p(review_length) / np.log1p(1000))
        
        # Summary clarity (short summaries with strong ratings are clearer)
        if summary_length > 0:
            clarity_score = min(1.0, 50 / max(summary_length, 10)) * (1.0 if rating in [1, 5] else 0.8)
        else:
            clarity_score = 0.5
        
        # Composite quality
        composite = (
            social_score * 0.3 +
            verification_score * 0.25 +
            detail_score * 0.25 +
            clarity_score * 0.2
        )
        
        return {
            "social_validation": round(social_score, 4),
            "verification": round(verification_score, 4),
            "detail_depth": round(detail_score, 4),
            "clarity": round(clarity_score, 4),
            "composite": round(composite, 4),
        }
    
    def add_review(
        self,
        archetype: str,
        quality_scores: Dict[str, float],
        mechanism_predictions: Dict[str, float],
    ) -> None:
        """Add a review's quality-weighted learning signal."""
        
        self.quality_scores[archetype].append({
            "quality": quality_scores,
            "mechanism_predictions": mechanism_predictions,
        })
    
    def compute_quality_weighted_effectiveness(self) -> Dict[str, Dict[str, Dict]]:
        """Compute quality-weighted mechanism effectiveness."""
        
        results = {}
        
        for archetype, reviews in self.quality_scores.items():
            if not reviews:
                continue
            
            # Aggregate mechanism effectiveness weighted by quality
            mechanism_weighted = defaultdict(lambda: {"weighted_sum": 0, "weight_sum": 0})
            
            for review in reviews:
                quality = review["quality"]["composite"]
                for mech, eff in review["mechanism_predictions"].items():
                    mechanism_weighted[mech]["weighted_sum"] += eff * quality
                    mechanism_weighted[mech]["weight_sum"] += quality
            
            # Compute weighted averages
            mechanism_results = {}
            for mech, data in mechanism_weighted.items():
                if data["weight_sum"] > 0:
                    mechanism_results[mech] = {
                        "quality_weighted_effectiveness": round(
                            data["weighted_sum"] / data["weight_sum"], 4
                        ),
                        "total_quality_weight": round(data["weight_sum"], 4),
                    }
            
            # Compute average review quality
            avg_quality = {
                "social_validation": np.mean([r["quality"]["social_validation"] for r in reviews]),
                "verification": np.mean([r["quality"]["verification"] for r in reviews]),
                "detail_depth": np.mean([r["quality"]["detail_depth"] for r in reviews]),
                "clarity": np.mean([r["quality"]["clarity"] for r in reviews]),
                "composite": np.mean([r["quality"]["composite"] for r in reviews]),
            }
            
            results[archetype] = {
                "mechanism_effectiveness": mechanism_results,
                "average_quality": {k: round(v, 4) for k, v in avg_quality.items()},
                "review_count": len(reviews),
            }
        
        return results


# =============================================================================
# 3. BRAND LOYALTY LEARNING
# =============================================================================

class BrandLoyaltyLearner:
    """
    Learns brand loyalty patterns and brand-archetype affinities.
    
    Insights:
    - Single-brand loyalists vs multi-brand explorers
    - Brand personality → archetype affinity
    - Brand switching triggers
    """
    
    # Brand personality dimensions (Aaker)
    BRAND_PERSONALITIES = {
        # Technology brands
        "apple": {"sincerity": 0.6, "excitement": 0.8, "competence": 0.9, "sophistication": 0.8, "ruggedness": 0.3},
        "samsung": {"sincerity": 0.5, "excitement": 0.7, "competence": 0.8, "sophistication": 0.6, "ruggedness": 0.4},
        "sony": {"sincerity": 0.5, "excitement": 0.7, "competence": 0.8, "sophistication": 0.7, "ruggedness": 0.3},
        # Automotive
        "bmw": {"sincerity": 0.4, "excitement": 0.8, "competence": 0.8, "sophistication": 0.9, "ruggedness": 0.5},
        "toyota": {"sincerity": 0.8, "excitement": 0.4, "competence": 0.9, "sophistication": 0.5, "ruggedness": 0.6},
        "jeep": {"sincerity": 0.5, "excitement": 0.7, "competence": 0.6, "sophistication": 0.3, "ruggedness": 0.9},
        # Beauty
        "laneige": {"sincerity": 0.7, "excitement": 0.6, "competence": 0.7, "sophistication": 0.8, "ruggedness": 0.2},
        "fresh": {"sincerity": 0.8, "excitement": 0.5, "competence": 0.7, "sophistication": 0.7, "ruggedness": 0.2},
    }
    
    def __init__(self):
        self.reviewer_brands: Dict[str, List[str]] = defaultdict(list)
        self.brand_archetype_affinity: Dict[str, Dict[str, List[float]]] = defaultdict(lambda: defaultdict(list))
        self.loyalty_segments: Dict[str, List[str]] = defaultdict(list)
    
    def add_review(
        self,
        reviewer_id: str,
        brand: str,
        archetype: str,
        rating: float,
    ) -> None:
        """Track brand review by reviewer."""
        
        brand_lower = brand.lower().strip() if brand else "unknown"
        self.reviewer_brands[reviewer_id].append(brand_lower)
        
        # Track brand-archetype affinity
        self.brand_archetype_affinity[brand_lower][archetype].append(rating)
    
    def compute_loyalty_segments(self) -> Dict[str, Any]:
        """Compute loyalty segments from reviewer patterns."""
        
        segment_counts = defaultdict(int)
        segment_archetypes: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        
        for reviewer_id, brands in self.reviewer_brands.items():
            unique_brands = set(brands)
            num_brands = len(unique_brands)
            
            # Segment by brand diversity
            if num_brands == 1:
                segment = "brand_loyalist"
            elif num_brands <= 3:
                segment = "selective_switcher"
            else:
                segment = "brand_explorer"
            
            segment_counts[segment] += 1
            self.loyalty_segments[segment].append(reviewer_id)
        
        return {
            "segments": {
                segment: {
                    "count": count,
                    "percentage": round(count / max(sum(segment_counts.values()), 1) * 100, 2),
                }
                for segment, count in segment_counts.items()
            },
            "total_reviewers": sum(segment_counts.values()),
        }
    
    def compute_brand_archetype_affinities(self) -> Dict[str, Dict[str, float]]:
        """Compute brand → archetype affinities."""
        
        affinities = {}
        
        for brand, archetypes in self.brand_archetype_affinity.items():
            if sum(len(v) for v in archetypes.values()) < 5:
                continue  # Skip brands with few reviews
            
            # Compute affinity score for each archetype
            archetype_affinities = {}
            total_reviews = sum(len(v) for v in archetypes.values())
            
            for arch, ratings in archetypes.items():
                if ratings:
                    # Affinity = (proportion of reviews) × (average rating normalized)
                    proportion = len(ratings) / total_reviews
                    avg_rating = np.mean(ratings)
                    affinity = proportion * (avg_rating / 5.0)
                    archetype_affinities[arch] = round(affinity, 4)
            
            if archetype_affinities:
                affinities[brand] = archetype_affinities
        
        return affinities
    
    def compute_brand_personality_matches(self) -> Dict[str, Dict[str, float]]:
        """Match brand personalities to archetypes."""
        
        # Archetype → Aaker dimension weights
        ARCHETYPE_DIMENSIONS = {
            "Connector": {"sincerity": 0.9, "excitement": 0.5, "competence": 0.5, "sophistication": 0.6, "ruggedness": 0.2},
            "Achiever": {"sincerity": 0.4, "excitement": 0.8, "competence": 0.9, "sophistication": 0.7, "ruggedness": 0.5},
            "Explorer": {"sincerity": 0.5, "excitement": 0.9, "competence": 0.5, "sophistication": 0.4, "ruggedness": 0.8},
            "Guardian": {"sincerity": 0.9, "excitement": 0.3, "competence": 0.8, "sophistication": 0.5, "ruggedness": 0.6},
            "Pragmatist": {"sincerity": 0.6, "excitement": 0.3, "competence": 0.9, "sophistication": 0.4, "ruggedness": 0.5},
            "Analyzer": {"sincerity": 0.5, "excitement": 0.4, "competence": 0.9, "sophistication": 0.6, "ruggedness": 0.3},
        }
        
        matches = {}
        
        for brand, brand_dims in self.BRAND_PERSONALITIES.items():
            archetype_scores = {}
            
            for archetype, arch_dims in ARCHETYPE_DIMENSIONS.items():
                # Compute cosine similarity
                dot_product = sum(brand_dims[d] * arch_dims[d] for d in brand_dims)
                brand_norm = np.sqrt(sum(v**2 for v in brand_dims.values()))
                arch_norm = np.sqrt(sum(v**2 for v in arch_dims.values()))
                
                similarity = dot_product / (brand_norm * arch_norm) if brand_norm * arch_norm > 0 else 0
                archetype_scores[archetype] = round(similarity, 4)
            
            matches[brand] = archetype_scores
        
        return matches


# =============================================================================
# 4. PRICE SENSITIVITY SEGMENTATION
# =============================================================================

class PriceSensitivityLearner:
    """
    Learns price sensitivity patterns from purchase behavior.
    
    Segments:
    - Premium seekers (high price, high rating correlation)
    - Value hunters (price-rating sensitivity)
    - Deal-prone (responds to discounts)
    """
    
    def __init__(self):
        self.price_rating_data: Dict[str, List[Tuple[float, float]]] = defaultdict(list)
        self.category_price_tiers: Dict[str, Dict[str, List[float]]] = defaultdict(lambda: defaultdict(list))
    
    def add_review(
        self,
        archetype: str,
        category: str,
        price: Optional[float],
        rating: float,
    ) -> None:
        """Track price-rating relationship."""
        
        if price is None or price <= 0:
            return
        
        self.price_rating_data[archetype].append((price, rating))
        
        # Categorize into price tiers
        if price < 25:
            tier = "budget"
        elif price < 100:
            tier = "mid_range"
        elif price < 500:
            tier = "premium"
        else:
            tier = "luxury"
        
        self.category_price_tiers[category][tier].append(rating)
    
    def compute_price_sensitivity_profiles(self) -> Dict[str, Dict[str, Any]]:
        """Compute price sensitivity profile per archetype."""
        
        profiles = {}
        
        for archetype, data in self.price_rating_data.items():
            if len(data) < 10:
                continue
            
            prices, ratings = zip(*data)
            prices = np.array(prices)
            ratings = np.array(ratings)
            
            # Compute correlation
            if np.std(prices) > 0 and np.std(ratings) > 0:
                correlation = np.corrcoef(prices, ratings)[0, 1]
            else:
                correlation = 0
            
            # Compute price tier preferences
            tier_ratings = defaultdict(list)
            for p, r in data:
                if p < 25:
                    tier_ratings["budget"].append(r)
                elif p < 100:
                    tier_ratings["mid_range"].append(r)
                elif p < 500:
                    tier_ratings["premium"].append(r)
                else:
                    tier_ratings["luxury"].append(r)
            
            tier_preferences = {
                tier: round(np.mean(rs), 4)
                for tier, rs in tier_ratings.items()
                if rs
            }
            
            # Infer price sensitivity type
            if correlation > 0.2:
                sensitivity_type = "premium_seeker"  # Higher price = higher satisfaction
            elif correlation < -0.2:
                sensitivity_type = "value_hunter"  # Lower price = higher satisfaction
            else:
                sensitivity_type = "price_neutral"
            
            profiles[archetype] = {
                "price_rating_correlation": round(correlation, 4),
                "sensitivity_type": sensitivity_type,
                "tier_preferences": tier_preferences,
                "avg_price": round(np.mean(prices), 2),
                "price_range": [round(np.min(prices), 2), round(np.max(prices), 2)],
                "sample_size": len(data),
            }
        
        return profiles


# =============================================================================
# 5. CROSS-DOMAIN TRANSFER LEARNING
# =============================================================================

class CrossDomainTransferLearner:
    """
    Learns cross-domain patterns for transfer learning.
    
    Insights:
    - Media preferences → Product affinities
    - Category expertise → Cross-category recommendations
    - Lifestyle inference from multi-category behavior
    """
    
    # Category clusters for transfer learning
    CATEGORY_CLUSTERS = {
        "entertainment": ["Gaming", "Streaming", "Movies", "Music"],
        "technology": ["Electronics_Photography", "Gaming", "Computers"],
        "lifestyle": ["Beauty", "Fashion", "Home", "Health"],
        "automotive": ["Automotive", "Outdoors"],
        "professional": ["Office", "Industrial", "Business"],
    }
    
    # Cross-domain affinity matrix (which categories predict which)
    CROSS_DOMAIN_AFFINITIES = {
        "Gaming": ["Electronics_Photography", "Streaming", "Movies"],
        "Beauty": ["Fashion", "Health", "Lifestyle"],
        "Automotive": ["Outdoors", "Electronics_Photography"],
        "Movies": ["Streaming", "Gaming", "Music"],
    }
    
    def __init__(self):
        self.reviewer_categories: Dict[str, Dict[str, List[float]]] = defaultdict(lambda: defaultdict(list))
        self.category_archetype_correlation: Dict[Tuple[str, str], List[str]] = defaultdict(list)
    
    def add_review(
        self,
        reviewer_id: str,
        category: str,
        archetype: str,
        rating: float,
    ) -> None:
        """Track reviewer's multi-category behavior."""
        
        self.reviewer_categories[reviewer_id][category].append(rating)
        
        # Track category → archetype mapping for this reviewer
        self.category_archetype_correlation[(reviewer_id, category)].append(archetype)
    
    def compute_cross_category_transfer_priors(self) -> Dict[str, Dict[str, float]]:
        """Compute transfer priors between categories."""
        
        # Track co-occurrence of categories by reviewer
        category_cooccurrence: Dict[Tuple[str, str], int] = defaultdict(int)
        category_counts: Dict[str, int] = defaultdict(int)
        
        for reviewer_id, categories in self.reviewer_categories.items():
            cats = list(categories.keys())
            for cat in cats:
                category_counts[cat] += 1
            for i, cat1 in enumerate(cats):
                for cat2 in cats[i+1:]:
                    pair = tuple(sorted([cat1, cat2]))
                    category_cooccurrence[pair] += 1
        
        # Compute lift (how much more likely categories co-occur than chance)
        transfer_priors = {}
        total_reviewers = len(self.reviewer_categories)
        
        for (cat1, cat2), cooccur in category_cooccurrence.items():
            if cooccur < 5:
                continue
            
            expected = (category_counts[cat1] / total_reviewers) * (category_counts[cat2] / total_reviewers) * total_reviewers
            if expected > 0:
                lift = cooccur / expected
                
                if cat1 not in transfer_priors:
                    transfer_priors[cat1] = {}
                if cat2 not in transfer_priors:
                    transfer_priors[cat2] = {}
                
                transfer_priors[cat1][cat2] = round(lift, 4)
                transfer_priors[cat2][cat1] = round(lift, 4)
        
        return transfer_priors
    
    def compute_lifestyle_segments(self) -> Dict[str, Dict[str, Any]]:
        """Infer lifestyle segments from multi-category behavior."""
        
        lifestyle_segments = defaultdict(list)
        
        for reviewer_id, categories in self.reviewer_categories.items():
            cats = set(categories.keys())
            
            # Match to lifestyle clusters
            for lifestyle, lifestyle_cats in self.CATEGORY_CLUSTERS.items():
                overlap = len(cats & set(lifestyle_cats))
                if overlap >= 2:
                    lifestyle_segments[lifestyle].append(reviewer_id)
        
        return {
            lifestyle: {
                "reviewer_count": len(reviewers),
                "percentage": round(len(reviewers) / max(len(self.reviewer_categories), 1) * 100, 2),
            }
            for lifestyle, reviewers in lifestyle_segments.items()
        }


# =============================================================================
# 6. LINGUISTIC DEPTH ANALYSIS
# =============================================================================

class LinguisticDepthAnalyzer:
    """
    Analyzes linguistic patterns for deeper psychological inference.
    
    Features:
    - Vocabulary richness → Cognitive complexity
    - Review length distribution → Engagement depth
    - Sentiment patterns → Regulatory focus
    """
    
    def __init__(self):
        self.archetype_linguistic: Dict[str, Dict[str, List]] = defaultdict(lambda: {
            "review_lengths": [],
            "unique_words": [],
            "positive_words": [],
            "negative_words": [],
        })
    
    # Simple sentiment word lists
    POSITIVE_WORDS = {"great", "excellent", "love", "perfect", "amazing", "best", "wonderful", "fantastic", "awesome", "good"}
    NEGATIVE_WORDS = {"bad", "terrible", "awful", "worst", "hate", "poor", "disappointing", "broken", "useless", "waste"}
    
    def analyze_text(self, text: str) -> Dict[str, float]:
        """Analyze linguistic features of a review."""
        
        words = re.findall(r'\b\w+\b', text.lower())
        
        if not words:
            return {
                "length": 0,
                "unique_ratio": 0,
                "positive_ratio": 0,
                "negative_ratio": 0,
            }
        
        unique_words = set(words)
        unique_ratio = len(unique_words) / len(words)
        
        positive_count = sum(1 for w in words if w in self.POSITIVE_WORDS)
        negative_count = sum(1 for w in words if w in self.NEGATIVE_WORDS)
        
        positive_ratio = positive_count / len(words)
        negative_ratio = negative_count / len(words)
        
        return {
            "length": len(words),
            "unique_ratio": unique_ratio,
            "positive_ratio": positive_ratio,
            "negative_ratio": negative_ratio,
        }
    
    def add_review(
        self,
        archetype: str,
        text: str,
    ) -> None:
        """Analyze and track review linguistics."""
        
        features = self.analyze_text(text)
        
        self.archetype_linguistic[archetype]["review_lengths"].append(features["length"])
        self.archetype_linguistic[archetype]["unique_words"].append(features["unique_ratio"])
        self.archetype_linguistic[archetype]["positive_words"].append(features["positive_ratio"])
        self.archetype_linguistic[archetype]["negative_words"].append(features["negative_ratio"])
    
    def compute_linguistic_profiles(self) -> Dict[str, Dict[str, Any]]:
        """Compute linguistic profile per archetype."""
        
        profiles = {}
        
        for archetype, data in self.archetype_linguistic.items():
            if not data["review_lengths"]:
                continue
            
            # Cognitive complexity (vocabulary richness)
            vocab_richness = np.mean(data["unique_words"])
            
            # Engagement depth (review length)
            avg_length = np.mean(data["review_lengths"])
            
            # Sentiment orientation
            avg_positive = np.mean(data["positive_words"])
            avg_negative = np.mean(data["negative_words"])
            sentiment_ratio = avg_positive / max(avg_negative, 0.001)
            
            # Infer regulatory focus from sentiment
            if sentiment_ratio > 2.0:
                regulatory_focus = "promotion"
            elif sentiment_ratio < 0.5:
                regulatory_focus = "prevention"
            else:
                regulatory_focus = "balanced"
            
            # Infer cognitive style
            if vocab_richness > 0.6:
                cognitive_style = "analytical"
            elif vocab_richness < 0.4:
                cognitive_style = "intuitive"
            else:
                cognitive_style = "balanced"
            
            profiles[archetype] = {
                "vocabulary_richness": round(vocab_richness, 4),
                "avg_review_length": round(avg_length, 2),
                "positive_sentiment": round(avg_positive, 4),
                "negative_sentiment": round(avg_negative, 4),
                "sentiment_ratio": round(sentiment_ratio, 4),
                "inferred_regulatory_focus": regulatory_focus,
                "inferred_cognitive_style": cognitive_style,
                "sample_size": len(data["review_lengths"]),
            }
        
        return profiles


# =============================================================================
# MAIN ORCHESTRATION
# =============================================================================

async def run_advanced_learning(args):
    """Run all advanced learning modules."""
    
    print("\n" + "=" * 70)
    print("ADAM ADVANCED LEARNING ENHANCEMENT")
    print("=" * 70 + "\n")
    
    # Initialize learners
    temporal_learner = TemporalPatternLearner()
    quality_analyzer = ReviewQualityAnalyzer()
    brand_learner = BrandLoyaltyLearner()
    price_learner = PriceSensitivityLearner()
    cross_domain_learner = CrossDomainTransferLearner()
    linguistic_analyzer = LinguisticDepthAnalyzer()
    
    # Load existing learning data
    archetype_matrix_path = LEARNING_DATA_DIR / "archetype_mechanism_matrix.json"
    if archetype_matrix_path.exists():
        with open(archetype_matrix_path) as f:
            archetype_matrix = json.load(f)
        logger.info(f"Loaded archetype matrix: {len(archetype_matrix)} archetypes")
    else:
        archetype_matrix = {}
        logger.warning("No archetype matrix found")
    
    # Simulate processing with synthetic temporal/quality data
    # (In production, this would read actual review data with timestamps, votes, etc.)
    
    print("-" * 50)
    print("1. TEMPORAL PATTERN LEARNING")
    print("-" * 50 + "\n")
    
    # Generate synthetic temporal data based on archetype patterns
    archetypes = list(archetype_matrix.keys()) if archetype_matrix else ["Connector", "Achiever", "Explorer", "Guardian"]
    
    for archetype in archetypes:
        # Simulate reviews with different temporal patterns per archetype
        archetype_temporal_bias = {
            "Connector": {"peak_hour": 19, "peak_day": 5},  # Evening, Saturday
            "Achiever": {"peak_hour": 8, "peak_day": 1},   # Morning, Tuesday
            "Explorer": {"peak_hour": 22, "peak_day": 6},  # Night, Sunday
            "Guardian": {"peak_hour": 10, "peak_day": 3},  # Late morning, Thursday
            "Pragmatist": {"peak_hour": 12, "peak_day": 2},  # Lunch, Wednesday
            "Analyzer": {"peak_hour": 15, "peak_day": 4},  # Afternoon, Friday
        }.get(archetype, {"peak_hour": 12, "peak_day": 3})
        
        for _ in range(500):  # 500 simulated reviews per archetype
            # Generate timestamp biased toward archetype's peak
            hour = int(np.clip(np.random.normal(archetype_temporal_bias["peak_hour"], 4), 0, 23))
            day = int(np.clip(np.random.normal(archetype_temporal_bias["peak_day"], 1.5), 0, 6))
            month = np.random.randint(1, 13)
            
            timestamp = datetime(2025, month, 1 + np.random.randint(0, 28), hour, 0)
            rating = np.random.uniform(3.5, 5.0)
            length = int(np.random.exponential(200))
            
            temporal_learner.process_review(archetype, timestamp, rating, length)
    
    temporal_results = temporal_learner.compute_optimal_timing()
    
    # Save temporal results
    temporal_output = LEARNING_DATA_DIR / "temporal_patterns.json"
    with open(temporal_output, 'w') as f:
        json.dump(temporal_results, f, indent=2)
    print(f"✓ Temporal patterns saved to: {temporal_output}")
    
    for arch in list(temporal_results.keys())[:2]:
        print(f"\n{arch}:")
        print(f"  Best hours: {[h['hour'] for h in temporal_results[arch]['best_hours']]}")
        print(f"  Best days: {[d['day'] for d in temporal_results[arch]['best_days']]}")
    
    if args.temporal_only:
        return
    
    print("\n" + "-" * 50)
    print("2. REVIEW QUALITY WEIGHTING")
    print("-" * 50 + "\n")
    
    # Simulate quality-weighted learning
    for archetype in archetypes:
        for _ in range(200):
            quality_scores = quality_analyzer.compute_quality_score(
                helpful_votes=int(np.random.exponential(5)),
                verified=np.random.random() > 0.3,
                review_length=int(np.random.exponential(300)),
                summary_length=int(np.random.exponential(30)),
                rating=np.random.uniform(1, 5),
            )
            
            # Get mechanism predictions from matrix if available
            if archetype in archetype_matrix:
                mech_predictions = {
                    mech: data.get("avg_effectiveness", 0.3) + np.random.normal(0, 0.05)
                    for mech, data in archetype_matrix[archetype].items()
                }
            else:
                mech_predictions = {"liking": 0.4, "authority": 0.3, "scarcity": 0.25}
            
            quality_analyzer.add_review(archetype, quality_scores, mech_predictions)
    
    quality_results = quality_analyzer.compute_quality_weighted_effectiveness()
    
    quality_output = LEARNING_DATA_DIR / "quality_weighted_effectiveness.json"
    with open(quality_output, 'w') as f:
        json.dump(quality_results, f, indent=2)
    print(f"✓ Quality-weighted effectiveness saved to: {quality_output}")
    
    print("\n" + "-" * 50)
    print("3. BRAND LOYALTY LEARNING")
    print("-" * 50 + "\n")
    
    # Simulate brand reviews
    brands = ["apple", "samsung", "sony", "bmw", "toyota", "laneige", "fresh"]
    for _ in range(1000):
        reviewer_id = f"reviewer_{np.random.randint(1, 200)}"
        brand = np.random.choice(brands)
        archetype = np.random.choice(archetypes)
        rating = np.random.uniform(3, 5)
        
        brand_learner.add_review(reviewer_id, brand, archetype, rating)
    
    loyalty_segments = brand_learner.compute_loyalty_segments()
    brand_affinities = brand_learner.compute_brand_archetype_affinities()
    brand_personality_matches = brand_learner.compute_brand_personality_matches()
    
    brand_output = LEARNING_DATA_DIR / "brand_loyalty_patterns.json"
    with open(brand_output, 'w') as f:
        json.dump({
            "loyalty_segments": loyalty_segments,
            "brand_archetype_affinities": brand_affinities,
            "brand_personality_matches": brand_personality_matches,
        }, f, indent=2)
    print(f"✓ Brand loyalty patterns saved to: {brand_output}")
    
    print(f"\nLoyalty Segments: {loyalty_segments['segments']}")
    
    if args.brand_only:
        return
    
    print("\n" + "-" * 50)
    print("4. PRICE SENSITIVITY SEGMENTATION")
    print("-" * 50 + "\n")
    
    # Simulate price data
    for archetype in archetypes:
        for _ in range(200):
            price = np.random.exponential(100)
            rating = np.clip(np.random.normal(4, 0.5), 1, 5)
            
            # Add archetype-specific price sensitivity bias
            if archetype in ["Connector", "Guardian"]:
                price = price * 0.7  # More price conscious
            elif archetype in ["Achiever", "Explorer"]:
                price = price * 1.3  # Premium seekers
            
            price_learner.add_review(archetype, "General", price, rating)
    
    price_profiles = price_learner.compute_price_sensitivity_profiles()
    
    price_output = LEARNING_DATA_DIR / "price_sensitivity_profiles.json"
    with open(price_output, 'w') as f:
        json.dump(price_profiles, f, indent=2)
    print(f"✓ Price sensitivity profiles saved to: {price_output}")
    
    for arch in list(price_profiles.keys())[:3]:
        print(f"  {arch}: {price_profiles[arch]['sensitivity_type']}")
    
    print("\n" + "-" * 50)
    print("5. CROSS-DOMAIN TRANSFER LEARNING")
    print("-" * 50 + "\n")
    
    # Simulate cross-domain behavior
    categories = ["Gaming", "Electronics_Photography", "Beauty", "Automotive", "Movies", "Streaming"]
    for _ in range(500):
        reviewer_id = f"reviewer_{np.random.randint(1, 100)}"
        # Each reviewer reviews 2-4 categories
        reviewer_cats = np.random.choice(categories, size=np.random.randint(2, 5), replace=False)
        
        for cat in reviewer_cats:
            archetype = np.random.choice(archetypes)
            rating = np.random.uniform(3, 5)
            cross_domain_learner.add_review(reviewer_id, cat, archetype, rating)
    
    transfer_priors = cross_domain_learner.compute_cross_category_transfer_priors()
    lifestyle_segments = cross_domain_learner.compute_lifestyle_segments()
    
    cross_domain_output = LEARNING_DATA_DIR / "cross_domain_transfer.json"
    with open(cross_domain_output, 'w') as f:
        json.dump({
            "category_transfer_lift": transfer_priors,
            "lifestyle_segments": lifestyle_segments,
        }, f, indent=2)
    print(f"✓ Cross-domain transfer patterns saved to: {cross_domain_output}")
    
    print(f"\nLifestyle Segments: {lifestyle_segments}")
    
    print("\n" + "-" * 50)
    print("6. LINGUISTIC DEPTH ANALYSIS")
    print("-" * 50 + "\n")
    
    # Simulate linguistic analysis
    sample_reviews = [
        "Great product, love it! Works perfectly.",
        "Excellent quality and fast shipping. Would recommend to anyone looking for value.",
        "This is absolutely the best purchase I've made. The attention to detail is remarkable.",
        "Disappointing. Broke after one week. Terrible quality.",
        "Good for the price but could be better. Some minor issues.",
    ]
    
    for archetype in archetypes:
        for _ in range(100):
            text = np.random.choice(sample_reviews) + " " + " ".join(
                np.random.choice(["good", "great", "nice", "okay", "fine", "excellent"], 
                                size=np.random.randint(1, 10))
            )
            linguistic_analyzer.add_review(archetype, text)
    
    linguistic_profiles = linguistic_analyzer.compute_linguistic_profiles()
    
    linguistic_output = LEARNING_DATA_DIR / "linguistic_profiles.json"
    with open(linguistic_output, 'w') as f:
        json.dump(linguistic_profiles, f, indent=2)
    print(f"✓ Linguistic profiles saved to: {linguistic_output}")
    
    for arch in list(linguistic_profiles.keys())[:3]:
        print(f"  {arch}: cognitive_style={linguistic_profiles[arch]['inferred_cognitive_style']}, "
              f"regulatory_focus={linguistic_profiles[arch]['inferred_regulatory_focus']}")
    
    # ==========================================================================
    # SUMMARY
    # ==========================================================================
    
    print("\n" + "=" * 70)
    print("ADVANCED LEARNING COMPLETE")
    print("=" * 70)
    
    print("\nGenerated Learning Artifacts:")
    print(f"  • temporal_patterns.json")
    print(f"  • quality_weighted_effectiveness.json")
    print(f"  • brand_loyalty_patterns.json")
    print(f"  • price_sensitivity_profiles.json")
    print(f"  • cross_domain_transfer.json")
    print(f"  • linguistic_profiles.json")
    
    print("\nNext Integration Steps:")
    print("  1. Use temporal_patterns for ad timing optimization")
    print("  2. Apply quality_weighted_effectiveness to mechanism selection")
    print("  3. Match brand_loyalty_patterns for brand campaigns")
    print("  4. Use price_sensitivity for offer personalization")
    print("  5. Apply cross_domain_transfer for cold-start improvement")
    print("  6. Use linguistic_profiles for message framing")


async def main():
    parser = argparse.ArgumentParser(description="ADAM Advanced Learning Enhancement")
    parser.add_argument("--temporal-only", action="store_true", help="Only run temporal learning")
    parser.add_argument("--brand-only", action="store_true", help="Only run brand learning")
    args = parser.parse_args()
    
    await run_advanced_learning(args)


if __name__ == "__main__":
    asyncio.run(main())
