# =============================================================================
# ADAM Amazon Psychological Profiler
# Location: adam/data/amazon/profiler.py
# =============================================================================

"""
AMAZON PSYCHOLOGICAL PROFILER

Builds psychological profiles from Amazon review data:
1. Extract linguistic features from review text
2. Aggregate features per user
3. Infer Big Five personality from linguistic patterns
4. Cluster users into archetypes
5. Build category-level psychological profiles

Research foundation:
- Pennebaker & King (1999): Linguistic correlates of personality
- Yarkoni (2010): Big Five and blog language
- Schwartz et al. (2013): Facebook language and personality
- Mairesse et al. (2007): LIWC and personality recognition
"""

import logging
import math
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

import numpy as np

from adam.data.amazon.models import (
    AmazonReview,
    LinguisticFeatures,
    InferredBigFive,
    ReviewerArchetype,
    CategoryPsychology,
    AmazonUserProfile,
)
from adam.data.amazon.loader import (
    AmazonDataLoader,
    ReviewerAggregator,
    CATEGORY_PSYCHOLOGY_PRIORS,
)
from adam.data.amazon.features import LinguisticFeatureExtractor

logger = logging.getLogger(__name__)


# =============================================================================
# LINGUISTIC → BIG FIVE MAPPING
# =============================================================================

# Research-based mappings from linguistic features to Big Five
# Based on: Yarkoni (2010), Schwartz et al. (2013), Mairesse et al. (2007)

BIG_FIVE_MAPPINGS = {
    "openness": {
        # Positive indicators
        "word_length_avg": 0.15,      # Longer words → higher openness
        "articles": 0.10,              # More articles → more formal/open
        "prepositions": 0.08,          # More prepositions → complex thought
        "insight": 0.12,               # Insight words → reflective
        "tentative": 0.08,             # Tentative language → open to possibilities
        # Negative indicators
        "certainty": -0.08,            # Less certainty → more open
        "first_person_singular": -0.05, # Less "I" focus
    },
    "conscientiousness": {
        # Positive indicators
        "articles": 0.08,
        "work": 0.15,                  # Work-related words
        "certainty": 0.12,             # Certainty → organized thinking
        "prepositions": 0.08,
        # Negative indicators
        "discrepancy": -0.15,          # Fewer discrepancies → consistent
        "tentative": -0.08,            # Less tentative → decisive
        "negative_emotion": -0.10,     # Less negative emotion
        "swear_words": -0.15,
    },
    "extraversion": {
        # Positive indicators
        "social": 0.20,                # Social words key indicator
        "positive_emotion": 0.18,      # Positive emotion → extraverted
        "first_person_plural": 0.15,   # "We" usage → social orientation
        "friends": 0.12,
        "family": 0.10,
        # Negative indicators
        "first_person_singular": -0.12, # Less "I" → less introverted
        "tentative": -0.08,
        "articles": -0.05,             # Fewer articles → more casual
    },
    "agreeableness": {
        # Positive indicators
        "positive_emotion": 0.18,
        "social": 0.12,
        "family": 0.10,
        "friends": 0.10,
        # Negative indicators
        "anger": -0.20,                # Less anger
        "swear_words": -0.18,
        "negative_emotion": -0.12,
        "discrepancy": -0.08,
    },
    "neuroticism": {
        # Positive indicators
        "negative_emotion": 0.22,      # Negative emotion key indicator
        "anxiety": 0.20,               # Anxiety words
        "sadness": 0.15,
        "anger": 0.12,
        "first_person_singular": 0.15, # More "I" → self-focus
        "discrepancy": 0.10,
        # Negative indicators
        "positive_emotion": -0.15,
        "certainty": -0.10,
    },
}


# =============================================================================
# PSYCHOLOGICAL PROFILER
# =============================================================================

class AmazonPsychologicalProfiler:
    """
    Builds psychological profiles from Amazon review data.
    
    Pipeline:
    1. Load reviews from JSONL files
    2. Extract linguistic features per review
    3. Aggregate features per user
    4. Infer Big Five personality
    5. Cluster into archetypes
    """
    
    def __init__(
        self,
        data_dir: str = "/amazon",
        min_reviews_for_profile: int = 3,
        min_words_for_profile: int = 100,
    ):
        """
        Initialize profiler.
        
        Args:
            data_dir: Path to Amazon data directory
            min_reviews_for_profile: Minimum reviews needed for personality inference
            min_words_for_profile: Minimum total words needed for inference
        """
        self.loader = AmazonDataLoader(data_dir)
        self.feature_extractor = LinguisticFeatureExtractor()
        self.aggregator = ReviewerAggregator()
        
        self.min_reviews = min_reviews_for_profile
        self.min_words = min_words_for_profile
        
        # Caches
        self._user_profiles: Dict[str, AmazonUserProfile] = {}
        self._category_profiles: Dict[str, CategoryPsychology] = {}
        self._archetypes: List[ReviewerArchetype] = []
    
    def process_category(
        self,
        category: str,
        limit: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Process all reviews from a category.
        
        Args:
            category: Category name
            limit: Maximum reviews to process
        
        Returns:
            Processing statistics
        """
        logger.info(f"Processing category: {category}")
        
        stats = {
            "category": category,
            "reviews_processed": 0,
            "users_seen": set(),
            "errors": 0,
        }
        
        try:
            for review in self.loader.stream_reviews(category, limit=limit):
                try:
                    self.aggregator.add_review(review, category)
                    stats["reviews_processed"] += 1
                    stats["users_seen"].add(review.user_id)
                except Exception as e:
                    stats["errors"] += 1
                    if stats["errors"] < 5:
                        logger.warning(f"Error processing review: {e}")
        except Exception as e:
            logger.error(f"Error streaming category {category}: {e}")
        
        stats["unique_users"] = len(stats["users_seen"])
        del stats["users_seen"]
        
        logger.info(f"Processed {stats['reviews_processed']} reviews, {stats['unique_users']} users")
        return stats
    
    def process_all_categories(
        self,
        limit_per_category: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Process all available categories.
        
        Args:
            limit_per_category: Maximum reviews per category
        
        Returns:
            Aggregate statistics
        """
        all_stats = {
            "categories_processed": 0,
            "total_reviews": 0,
            "total_users": 0,
            "category_stats": [],
        }
        
        for category in self.loader.available_categories:
            stats = self.process_category(category, limit=limit_per_category)
            all_stats["category_stats"].append(stats)
            all_stats["categories_processed"] += 1
            all_stats["total_reviews"] += stats["reviews_processed"]
        
        # Get unique users across all categories
        all_stats["total_users"] = len(self.aggregator.users)
        
        logger.info(
            f"Processed {all_stats['categories_processed']} categories, "
            f"{all_stats['total_reviews']} reviews, "
            f"{all_stats['total_users']} unique users"
        )
        
        return all_stats
    
    def extract_user_linguistic_features(self, user_id: str) -> Optional[LinguisticFeatures]:
        """
        Extract aggregated linguistic features for a user.
        
        Args:
            user_id: Amazon user ID
        
        Returns:
            LinguisticFeatures or None if insufficient data
        """
        if user_id not in self.aggregator.users:
            return None
        
        user_data = self.aggregator.users[user_id]
        review_count = len(user_data["reviews"])
        total_words = user_data["total_words"]
        
        # Check minimums
        if review_count < self.min_reviews or total_words < self.min_words:
            return None
        
        # Concatenate all review text
        all_text = self.aggregator.get_user_text(user_id)
        
        # Extract features
        features = self.feature_extractor.extract(all_text)
        features.user_id = user_id
        features.review_id = f"agg_{user_id}"
        
        return features
    
    def infer_big_five(self, features: LinguisticFeatures) -> InferredBigFive:
        """
        Infer Big Five personality from linguistic features.
        
        Uses research-based mappings from linguistic markers to traits.
        
        Args:
            features: Extracted linguistic features
        
        Returns:
            InferredBigFive personality profile
        """
        scores = {}
        confidences = {}
        
        for trait, mappings in BIG_FIVE_MAPPINGS.items():
            score = 0.5  # Start at neutral
            weight_sum = 0.0
            
            for feature_name, weight in mappings.items():
                # Get feature value
                if hasattr(features, feature_name):
                    value = getattr(features, feature_name)
                    if isinstance(value, (int, float)):
                        # Apply mapping
                        score += (value - 0.5) * weight
                        weight_sum += abs(weight)
            
            # Normalize to 0-1 range
            scores[trait] = max(0.0, min(1.0, score))
            
            # Confidence based on word count and feature coverage
            base_confidence = min(1.0, features.word_count / 500)  # More words = more confident
            coverage_confidence = weight_sum / sum(abs(w) for w in mappings.values())
            confidences[trait] = base_confidence * coverage_confidence * 0.8
        
        # Get user summary for additional info
        user_summary = self.aggregator.get_user_summary(features.user_id)
        
        return InferredBigFive(
            amazon_user_id=features.user_id,
            openness=scores["openness"],
            conscientiousness=scores["conscientiousness"],
            extraversion=scores["extraversion"],
            agreeableness=scores["agreeableness"],
            neuroticism=scores["neuroticism"],
            openness_confidence=confidences["openness"],
            conscientiousness_confidence=confidences["conscientiousness"],
            extraversion_confidence=confidences["extraversion"],
            agreeableness_confidence=confidences["agreeableness"],
            neuroticism_confidence=confidences["neuroticism"],
            inference_confidence=sum(confidences.values()) / 5,
            review_count_used=user_summary.get("review_count", 1),
            total_word_count=user_summary.get("total_words", 100),
            categories_reviewed=user_summary.get("categories", []),
            inference_method="linguistic",
            model_version="v1.0",
            first_review_at=datetime.fromtimestamp(
                user_summary.get("first_review_time", 0) / 1000, tz=timezone.utc
            ),
            last_review_at=datetime.fromtimestamp(
                user_summary.get("last_review_time", 0) / 1000, tz=timezone.utc
            ),
        )
    
    def build_user_profile(self, user_id: str) -> Optional[AmazonUserProfile]:
        """
        Build complete psychological profile for a user.
        
        Args:
            user_id: Amazon user ID
        
        Returns:
            AmazonUserProfile or None if insufficient data
        """
        # Get user summary
        summary = self.aggregator.get_user_summary(user_id)
        if not summary:
            return None
        
        # Extract linguistic features
        features = self.extract_user_linguistic_features(user_id)
        
        # Infer personality if we have features
        personality = None
        if features:
            personality = self.infer_big_five(features)
        
        # Build profile
        profile = AmazonUserProfile(
            amazon_user_id=user_id,
            review_count=summary["review_count"],
            first_review_at=datetime.fromtimestamp(
                summary["first_review_time"] / 1000, tz=timezone.utc
            ) if summary.get("first_review_time") else None,
            last_review_at=datetime.fromtimestamp(
                summary["last_review_time"] / 1000, tz=timezone.utc
            ) if summary.get("last_review_time") else None,
            categories_reviewed=summary["categories"],
            primary_category=summary["categories"][0] if summary["categories"] else None,
            avg_rating=summary.get("avg_rating"),
            avg_review_length=summary.get("avg_review_length", 0),
            total_helpful_votes=summary.get("total_helpful_votes", 0),
            verified_purchase_ratio=summary.get("verified_purchase_ratio", 0),
            linguistic_profile=features,
            inferred_personality=personality,
            profile_confidence=personality.inference_confidence if personality else 0.2,
            profile_completeness=self._calculate_completeness(summary, features, personality),
        )
        
        self._user_profiles[user_id] = profile
        return profile
    
    def _calculate_completeness(
        self,
        summary: Dict[str, Any],
        features: Optional[LinguisticFeatures],
        personality: Optional[InferredBigFive],
    ) -> float:
        """Calculate profile completeness score."""
        score = 0.0
        
        # Review count contribution
        review_count = summary.get("review_count", 0)
        score += min(0.3, review_count * 0.03)
        
        # Category diversity
        category_count = summary.get("category_count", 0)
        score += min(0.2, category_count * 0.05)
        
        # Linguistic features
        if features:
            score += 0.25
        
        # Personality inference
        if personality:
            score += 0.25 * personality.inference_confidence
        
        return min(1.0, score)
    
    def build_all_profiles(self) -> Dict[str, Any]:
        """
        Build profiles for all users with sufficient data.
        
        Returns:
            Statistics about profile building
        """
        eligible_users = self.aggregator.get_users_with_min_reviews(self.min_reviews)
        
        logger.info(f"Building profiles for {len(eligible_users)} eligible users")
        
        stats = {
            "eligible_users": len(eligible_users),
            "profiles_built": 0,
            "profiles_with_personality": 0,
            "avg_confidence": 0.0,
        }
        
        confidence_sum = 0.0
        
        for user_id in eligible_users:
            profile = self.build_user_profile(user_id)
            if profile:
                stats["profiles_built"] += 1
                if profile.inferred_personality:
                    stats["profiles_with_personality"] += 1
                    confidence_sum += profile.profile_confidence
        
        if stats["profiles_with_personality"] > 0:
            stats["avg_confidence"] = confidence_sum / stats["profiles_with_personality"]
        
        logger.info(
            f"Built {stats['profiles_built']} profiles, "
            f"{stats['profiles_with_personality']} with personality"
        )
        
        return stats
    
    def build_category_profile(self, category: str) -> CategoryPsychology:
        """
        Build psychological profile for a category.
        
        Aggregates personality data from all users who reviewed
        products in this category.
        
        Args:
            category: Category name
        
        Returns:
            CategoryPsychology profile
        """
        # Get priors if available
        priors = CATEGORY_PSYCHOLOGY_PRIORS.get(category, {})
        big_five_priors = priors.get("big_five", {})
        
        # Aggregate from user profiles
        traits = defaultdict(list)
        behavioral_stats = {
            "ratings": [],
            "review_lengths": [],
            "verified_ratios": [],
        }
        
        user_count = 0
        sample_count = 0
        
        for user_id, profile in self._user_profiles.items():
            if category not in profile.categories_reviewed:
                continue
            
            user_count += 1
            
            if profile.inferred_personality:
                sample_count += 1
                personality = profile.inferred_personality
                traits["openness"].append(personality.openness)
                traits["conscientiousness"].append(personality.conscientiousness)
                traits["extraversion"].append(personality.extraversion)
                traits["agreeableness"].append(personality.agreeableness)
                traits["neuroticism"].append(personality.neuroticism)
            
            if profile.avg_rating:
                behavioral_stats["ratings"].append(profile.avg_rating)
            behavioral_stats["review_lengths"].append(profile.avg_review_length)
            behavioral_stats["verified_ratios"].append(profile.verified_purchase_ratio)
        
        # Calculate means and stds, fall back to priors
        def get_stats(trait_list, prior_mean=0.5):
            if trait_list:
                mean = sum(trait_list) / len(trait_list)
                variance = sum((x - mean) ** 2 for x in trait_list) / len(trait_list)
                std = math.sqrt(variance)
                return mean, std
            return prior_mean, 0.15
        
        profile = CategoryPsychology(
            category_name=category,
            openness_mean=get_stats(traits["openness"], big_five_priors.get("openness", 0.5))[0],
            openness_std=get_stats(traits["openness"])[1],
            conscientiousness_mean=get_stats(traits["conscientiousness"], big_five_priors.get("conscientiousness", 0.5))[0],
            conscientiousness_std=get_stats(traits["conscientiousness"])[1],
            extraversion_mean=get_stats(traits["extraversion"], big_five_priors.get("extraversion", 0.5))[0],
            extraversion_std=get_stats(traits["extraversion"])[1],
            agreeableness_mean=get_stats(traits["agreeableness"], big_five_priors.get("agreeableness", 0.5))[0],
            agreeableness_std=get_stats(traits["agreeableness"])[1],
            neuroticism_mean=get_stats(traits["neuroticism"], big_five_priors.get("neuroticism", 0.5))[0],
            neuroticism_std=get_stats(traits["neuroticism"])[1],
            mechanism_effectiveness=priors.get("mechanisms", {}),
            avg_rating=sum(behavioral_stats["ratings"]) / len(behavioral_stats["ratings"]) if behavioral_stats["ratings"] else 4.0,
            avg_review_length=sum(behavioral_stats["review_lengths"]) / len(behavioral_stats["review_lengths"]) if behavioral_stats["review_lengths"] else 100,
            verified_purchase_ratio=sum(behavioral_stats["verified_ratios"]) / len(behavioral_stats["verified_ratios"]) if behavioral_stats["verified_ratios"] else 0.7,
            sample_size=sample_count,
            unique_users=user_count,
        )
        
        self._category_profiles[category] = profile
        return profile
    
    def get_user_profile(self, user_id: str) -> Optional[AmazonUserProfile]:
        """Get cached user profile."""
        return self._user_profiles.get(user_id)
    
    def get_category_profile(self, category: str) -> Optional[CategoryPsychology]:
        """Get cached category profile."""
        return self._category_profiles.get(category)
    
    def get_all_profiles(self) -> Dict[str, AmazonUserProfile]:
        """Get all cached user profiles."""
        return self._user_profiles
    
    def export_profiles_for_neo4j(self) -> List[Dict[str, Any]]:
        """
        Export profiles in format suitable for Neo4j ingestion.
        
        Returns:
            List of profile dictionaries
        """
        exports = []
        
        for user_id, profile in self._user_profiles.items():
            export = {
                "amazon_user_id": user_id,
                "review_count": profile.review_count,
                "categories": profile.categories_reviewed,
                "primary_category": profile.primary_category,
                "avg_rating": profile.avg_rating,
                "profile_confidence": profile.profile_confidence,
            }
            
            if profile.inferred_personality:
                p = profile.inferred_personality
                export.update({
                    "openness": p.openness,
                    "conscientiousness": p.conscientiousness,
                    "extraversion": p.extraversion,
                    "agreeableness": p.agreeableness,
                    "neuroticism": p.neuroticism,
                    "personality_confidence": p.inference_confidence,
                })
            
            exports.append(export)
        
        return exports


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def create_profiler(data_dir: str = "/amazon") -> AmazonPsychologicalProfiler:
    """Create a profiler instance."""
    return AmazonPsychologicalProfiler(data_dir)


def quick_profile_category(
    data_dir: str,
    category: str,
    limit: int = 10000,
) -> Tuple[Dict[str, Any], List[AmazonUserProfile]]:
    """
    Quick method to profile a single category.
    
    Returns:
        Tuple of (stats, profiles)
    """
    profiler = AmazonPsychologicalProfiler(data_dir)
    
    # Process reviews
    stats = profiler.process_category(category, limit=limit)
    
    # Build profiles
    profile_stats = profiler.build_all_profiles()
    stats.update(profile_stats)
    
    # Get profiles
    profiles = list(profiler.get_all_profiles().values())
    
    return stats, profiles
