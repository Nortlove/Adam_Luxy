# =============================================================================
# ADAM Amazon Data Loader
# Location: adam/data/amazon/loader.py
# =============================================================================

"""
AMAZON DATA LOADER

Loads and processes Amazon review data from JSONL files.
Handles the exact format provided:

REVIEW FILES: {Category}.jsonl
METADATA FILES: meta_{Category}.jsonl

Key field mappings:
- reviewerID → user_id
- asin → asin
- reviewText → text
- overall → rating
- summary → title
- unixReviewTime → timestamp
- vote → helpful_vote
- verified → verified_purchase
"""

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, Generator, List, Optional, Tuple
from uuid import uuid4

from pydantic import BaseModel, Field

from adam.data.amazon.models import (
    AmazonReview,
    ProductMetadata,
    AmazonCategory,
    LinguisticFeatures,
    AmazonUserProfile,
)

logger = logging.getLogger(__name__)


# =============================================================================
# RAW DATA MODELS (match exact JSONL format)
# =============================================================================

class RawAmazonReview(BaseModel):
    """
    Raw review format from the Amazon dataset (2023 format).
    Maps to internal AmazonReview model.
    
    The 2023 Amazon Review dataset uses different field names:
    - rating (not overall)
    - user_id (not reviewerID)
    - text (not reviewText)
    - title (not summary)
    - timestamp (milliseconds, not unixReviewTime)
    - helpful_vote (not vote)
    - verified_purchase (not verified)
    """
    
    # Core fields (2023 format)
    rating: float = Field(..., ge=1.0, le=5.0, description="Star rating")
    asin: str = Field(..., description="Product ASIN")
    user_id: str = Field(..., description="Reviewer user ID")
    text: Optional[str] = Field(default="", description="Review body text")
    title: Optional[str] = Field(default="", description="Review title")
    
    # Optional fields
    parent_asin: Optional[str] = Field(default=None)
    timestamp: Optional[int] = Field(default=None, description="Timestamp in milliseconds")
    helpful_vote: Optional[int] = Field(default=0)
    verified_purchase: Optional[bool] = Field(default=False)
    images: Optional[List[Dict[str, Any]]] = Field(default=None)
    
    class Config:
        extra = "ignore"
    
    def to_internal_review(self, category: str) -> AmazonReview:
        """Convert to internal AmazonReview model."""
        
        return AmazonReview(
            rating=self.rating,
            title=self.title or "",
            text=self.text or "",
            asin=self.asin,
            parent_asin=self.parent_asin or self.asin,
            user_id=self.user_id,
            timestamp=self.timestamp or 0,
            helpful_vote=self.helpful_vote or 0,
            verified_purchase=self.verified_purchase or False,
        )


class RawProductMetadata(BaseModel):
    """
    Raw product metadata format from the Amazon dataset (2023 format).
    
    The 2023 format has different fields:
    - main_category (explicit category)
    - features (list of features)
    - description (list of strings)
    - categories (flat list of strings)
    - details (dict with metadata)
    - average_rating, rating_number
    - parent_asin
    """
    
    # Core fields (2023 format)
    parent_asin: str = Field(..., description="Product ASIN")
    title: Optional[str] = Field(default="")
    main_category: Optional[str] = Field(default=None)
    
    # Product details
    features: Optional[List[str]] = Field(default=None)
    description: Optional[List[str]] = Field(default=None)
    price: Optional[float] = Field(default=None)
    store: Optional[str] = Field(default=None)
    
    # Ratings
    average_rating: Optional[float] = Field(default=None)
    rating_number: Optional[int] = Field(default=None)
    
    # Images and videos
    images: Optional[List[Dict[str, Any]]] = Field(default=None)
    videos: Optional[List[Dict[str, Any]]] = Field(default=None)
    
    # Categories (flat list in 2023 format)
    categories: Optional[List[str]] = Field(default=None)
    
    # Additional details
    details: Optional[Dict[str, str]] = Field(default=None)
    subtitle: Optional[str] = Field(default=None)
    author: Optional[Dict[str, Any]] = Field(default=None)
    
    # Related products
    bought_together: Optional[List[str]] = Field(default=None)
    
    class Config:
        extra = "ignore"
    
    def to_internal_metadata(self, category: str) -> ProductMetadata:
        """Convert to internal ProductMetadata model."""
        
        return ProductMetadata(
            main_category=self.main_category or category,
            title=self.title or "",
            features=self.features or [],
            description=self.description or [],
            price=self.price,
            store=self.store,
            categories=self.categories or [],
            parent_asin=self.parent_asin,
            bought_together=self.bought_together,
        )


# =============================================================================
# DATASET CONFIGURATION
# =============================================================================

# Available categories in the dataset
AVAILABLE_CATEGORIES = [
    "All_Beauty",
    "Amazon_Fashion",
    "Beauty_and_Personal_Care",
    "Books",
    "Clothing_Shoes_and_Jewelry",
    "Digital_Music",
    "Grocery_and_Gourmet_Food",
    "Kindle_Store",
    "Magazine_Subscriptions",
    "Movies_and_TV",
]

# Category psychological priors (research-based estimates)
CATEGORY_PSYCHOLOGY_PRIORS = {
    "All_Beauty": {
        "big_five": {"openness": 0.58, "conscientiousness": 0.52, "extraversion": 0.62, "agreeableness": 0.58, "neuroticism": 0.55},
        "mechanisms": ["identity_expression", "social_proof", "authenticity"],
        "decision_style": "experiential",
    },
    "Amazon_Fashion": {
        "big_five": {"openness": 0.65, "conscientiousness": 0.48, "extraversion": 0.68, "agreeableness": 0.55, "neuroticism": 0.52},
        "mechanisms": ["social_proof", "identity_expression", "novelty"],
        "decision_style": "intuitive",
    },
    "Beauty_and_Personal_Care": {
        "big_five": {"openness": 0.55, "conscientiousness": 0.54, "extraversion": 0.60, "agreeableness": 0.58, "neuroticism": 0.54},
        "mechanisms": ["authority", "social_proof", "identity_expression"],
        "decision_style": "experiential",
    },
    "Books": {
        "big_five": {"openness": 0.72, "conscientiousness": 0.58, "extraversion": 0.42, "agreeableness": 0.55, "neuroticism": 0.52},
        "mechanisms": ["authority", "intellectual_stimulation", "self_improvement"],
        "decision_style": "analytical",
    },
    "Clothing_Shoes_and_Jewelry": {
        "big_five": {"openness": 0.62, "conscientiousness": 0.50, "extraversion": 0.65, "agreeableness": 0.55, "neuroticism": 0.53},
        "mechanisms": ["social_proof", "identity_expression", "scarcity"],
        "decision_style": "intuitive",
    },
    "Digital_Music": {
        "big_five": {"openness": 0.68, "conscientiousness": 0.45, "extraversion": 0.55, "agreeableness": 0.52, "neuroticism": 0.50},
        "mechanisms": ["nostalgia", "identity_expression", "novelty"],
        "decision_style": "experiential",
    },
    "Grocery_and_Gourmet_Food": {
        "big_five": {"openness": 0.55, "conscientiousness": 0.60, "extraversion": 0.52, "agreeableness": 0.58, "neuroticism": 0.48},
        "mechanisms": ["authority", "health_wellness", "authenticity"],
        "decision_style": "habitual",
    },
    "Kindle_Store": {
        "big_five": {"openness": 0.70, "conscientiousness": 0.55, "extraversion": 0.45, "agreeableness": 0.52, "neuroticism": 0.50},
        "mechanisms": ["convenience", "intellectual_stimulation", "value"],
        "decision_style": "analytical",
    },
    "Magazine_Subscriptions": {
        "big_five": {"openness": 0.65, "conscientiousness": 0.58, "extraversion": 0.50, "agreeableness": 0.55, "neuroticism": 0.48},
        "mechanisms": ["authority", "social_identity", "habit"],
        "decision_style": "habitual",
    },
    "Movies_and_TV": {
        "big_five": {"openness": 0.62, "conscientiousness": 0.48, "extraversion": 0.55, "agreeableness": 0.52, "neuroticism": 0.52},
        "mechanisms": ["nostalgia", "social_proof", "escapism"],
        "decision_style": "experiential",
    },
}


# =============================================================================
# DATA LOADER
# =============================================================================

class AmazonDataLoader:
    """
    Loads Amazon review and metadata files.
    
    Usage:
        loader = AmazonDataLoader("/path/to/amazon")
        
        # Stream reviews
        for review in loader.stream_reviews("Books"):
            process(review)
        
        # Load all reviews for a category
        reviews = loader.load_reviews("Books", limit=10000)
    """
    
    def __init__(self, data_dir: str):
        """
        Initialize loader with data directory.
        
        Args:
            data_dir: Path to directory containing JSONL files
        """
        self.data_dir = Path(data_dir)
        
        if not self.data_dir.exists():
            raise FileNotFoundError(f"Data directory not found: {data_dir}")
        
        # Discover available categories
        self.available_categories = self._discover_categories()
        logger.info(f"Amazon loader initialized with {len(self.available_categories)} categories")
    
    def _discover_categories(self) -> List[str]:
        """Discover available category files."""
        categories = []
        
        for file in self.data_dir.glob("*.jsonl"):
            # Skip metadata files
            if file.name.startswith("meta_"):
                continue
            
            category = file.stem  # Filename without extension
            categories.append(category)
        
        return sorted(categories)
    
    def get_review_file(self, category: str) -> Path:
        """Get path to review file for category."""
        return self.data_dir / f"{category}.jsonl"
    
    def get_metadata_file(self, category: str) -> Path:
        """Get path to metadata file for category."""
        return self.data_dir / f"meta_{category}.jsonl"
    
    def stream_reviews(
        self,
        category: str,
        skip: int = 0,
        limit: Optional[int] = None,
    ) -> Generator[AmazonReview, None, None]:
        """
        Stream reviews from a category file.
        
        Args:
            category: Category name (e.g., "Books")
            skip: Number of reviews to skip
            limit: Maximum reviews to return (None = all)
        
        Yields:
            AmazonReview objects
        """
        review_file = self.get_review_file(category)
        
        if not review_file.exists():
            raise FileNotFoundError(f"Review file not found: {review_file}")
        
        count = 0
        skipped = 0
        errors = 0
        
        with open(review_file, "r", encoding="utf-8") as f:
            for line in f:
                # Skip lines
                if skipped < skip:
                    skipped += 1
                    continue
                
                # Check limit
                if limit and count >= limit:
                    break
                
                line = line.strip()
                if not line:
                    continue
                
                try:
                    data = json.loads(line)
                    raw_review = RawAmazonReview(**data)
                    review = raw_review.to_internal_review(category)
                    
                    # Skip empty reviews
                    if not review.text or len(review.text) < 10:
                        continue
                    
                    count += 1
                    yield review
                    
                except json.JSONDecodeError as e:
                    errors += 1
                    if errors < 10:
                        logger.warning(f"JSON parse error in {category}: {e}")
                except Exception as e:
                    errors += 1
                    if errors < 10:
                        logger.warning(f"Error processing review in {category}: {e}")
        
        logger.info(f"Streamed {count} reviews from {category} (errors: {errors})")
    
    def load_reviews(
        self,
        category: str,
        skip: int = 0,
        limit: Optional[int] = None,
    ) -> List[AmazonReview]:
        """Load reviews into memory."""
        return list(self.stream_reviews(category, skip, limit))
    
    def stream_metadata(
        self,
        category: str,
        limit: Optional[int] = None,
    ) -> Generator[ProductMetadata, None, None]:
        """
        Stream product metadata from a category file.
        
        Args:
            category: Category name
            limit: Maximum products to return
        
        Yields:
            ProductMetadata objects
        """
        metadata_file = self.get_metadata_file(category)
        
        if not metadata_file.exists():
            raise FileNotFoundError(f"Metadata file not found: {metadata_file}")
        
        count = 0
        errors = 0
        
        with open(metadata_file, "r", encoding="utf-8") as f:
            for line in f:
                if limit and count >= limit:
                    break
                
                line = line.strip()
                if not line:
                    continue
                
                try:
                    data = json.loads(line)
                    raw_metadata = RawProductMetadata(**data)
                    metadata = raw_metadata.to_internal_metadata(category)
                    
                    count += 1
                    yield metadata
                    
                except json.JSONDecodeError as e:
                    errors += 1
                    if errors < 10:
                        logger.warning(f"JSON parse error in meta_{category}: {e}")
                except Exception as e:
                    errors += 1
                    if errors < 10:
                        logger.warning(f"Error processing metadata in {category}: {e}")
        
        logger.info(f"Streamed {count} products from {category} (errors: {errors})")
    
    def load_metadata(
        self,
        category: str,
        limit: Optional[int] = None,
    ) -> List[ProductMetadata]:
        """Load product metadata into memory."""
        return list(self.stream_metadata(category, limit))
    
    def get_category_stats(self, category: str) -> Dict[str, Any]:
        """Get basic statistics for a category."""
        review_file = self.get_review_file(category)
        metadata_file = self.get_metadata_file(category)
        
        stats = {
            "category": category,
            "review_file_exists": review_file.exists(),
            "metadata_file_exists": metadata_file.exists(),
            "review_file_size_mb": 0,
            "metadata_file_size_mb": 0,
        }
        
        if review_file.exists():
            stats["review_file_size_mb"] = review_file.stat().st_size / (1024 * 1024)
        
        if metadata_file.exists():
            stats["metadata_file_size_mb"] = metadata_file.stat().st_size / (1024 * 1024)
        
        return stats
    
    def get_all_stats(self) -> List[Dict[str, Any]]:
        """Get statistics for all categories."""
        return [self.get_category_stats(cat) for cat in self.available_categories]


# =============================================================================
# USER AGGREGATOR
# =============================================================================

class ReviewerAggregator:
    """
    Aggregates reviews by user for psychological profiling.
    
    The key insight: A user's personality can be inferred by analyzing
    the linguistic patterns across ALL their reviews, not just one.
    """
    
    def __init__(self):
        self.users: Dict[str, Dict[str, Any]] = {}
    
    def add_review(self, review: AmazonReview, category: str):
        """Add a review to user aggregation."""
        user_id = review.user_id
        
        if user_id not in self.users:
            self.users[user_id] = {
                "user_id": user_id,
                "reviews": [],
                "categories": set(),
                "total_words": 0,
                "total_helpful_votes": 0,
                "verified_count": 0,
                "rating_sum": 0.0,
                "first_review_time": review.timestamp,
                "last_review_time": review.timestamp,
            }
        
        user_data = self.users[user_id]
        
        # Add review text
        user_data["reviews"].append({
            "text": review.text,
            "title": review.title,
            "rating": review.rating,
            "category": category,
            "timestamp": review.timestamp,
            "word_count": review.word_count,
        })
        
        # Update aggregates
        user_data["categories"].add(category)
        user_data["total_words"] += review.word_count
        user_data["total_helpful_votes"] += review.helpful_vote
        user_data["rating_sum"] += review.rating
        
        if review.verified_purchase:
            user_data["verified_count"] += 1
        
        # Update timestamps
        if review.timestamp < user_data["first_review_time"]:
            user_data["first_review_time"] = review.timestamp
        if review.timestamp > user_data["last_review_time"]:
            user_data["last_review_time"] = review.timestamp
    
    def get_user_text(self, user_id: str) -> str:
        """Get all review text for a user (for linguistic analysis)."""
        if user_id not in self.users:
            return ""
        
        texts = [r["text"] for r in self.users[user_id]["reviews"]]
        return " ".join(texts)
    
    def get_user_summary(self, user_id: str) -> Dict[str, Any]:
        """Get aggregated summary for a user."""
        if user_id not in self.users:
            return {}
        
        user_data = self.users[user_id]
        review_count = len(user_data["reviews"])
        
        return {
            "user_id": user_id,
            "review_count": review_count,
            "categories": list(user_data["categories"]),
            "category_count": len(user_data["categories"]),
            "total_words": user_data["total_words"],
            "avg_review_length": user_data["total_words"] / review_count if review_count else 0,
            "total_helpful_votes": user_data["total_helpful_votes"],
            "avg_rating": user_data["rating_sum"] / review_count if review_count else 0,
            "verified_purchase_ratio": user_data["verified_count"] / review_count if review_count else 0,
            "first_review_time": user_data["first_review_time"],
            "last_review_time": user_data["last_review_time"],
        }
    
    def get_users_with_min_reviews(self, min_reviews: int = 5) -> List[str]:
        """Get users with at least min_reviews reviews."""
        return [
            user_id for user_id, data in self.users.items()
            if len(data["reviews"]) >= min_reviews
        ]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get aggregation statistics."""
        review_counts = [len(u["reviews"]) for u in self.users.values()]
        
        return {
            "total_users": len(self.users),
            "total_reviews": sum(review_counts),
            "users_with_1_review": sum(1 for c in review_counts if c == 1),
            "users_with_5_plus_reviews": sum(1 for c in review_counts if c >= 5),
            "users_with_10_plus_reviews": sum(1 for c in review_counts if c >= 10),
            "avg_reviews_per_user": sum(review_counts) / len(review_counts) if review_counts else 0,
            "max_reviews_per_user": max(review_counts) if review_counts else 0,
        }


# =============================================================================
# FACTORY FUNCTION
# =============================================================================

def create_loader(data_dir: str = None) -> AmazonDataLoader:
    """Create Amazon data loader with default settings."""
    if data_dir is None:
        # Default to adam-platform/amazon
        import os
        data_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
            "amazon"
        )
    return AmazonDataLoader(data_dir)
