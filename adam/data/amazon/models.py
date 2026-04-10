# =============================================================================
# ADAM Amazon Data Models
# Location: adam/data/amazon/models.py
# =============================================================================

"""
AMAZON DATA MODELS

Data classes for Amazon review data.

These models are designed to:
1. Match the review_orchestrator's expectations
2. Preserve helpful_vote data for persuasive pattern analysis
3. Support hierarchical matching queries
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
import re


# =============================================================================
# PRICE TIER CONFIGURATION
# =============================================================================

PRICE_TIERS = {
    "budget": (0, 30),
    "low_mid": (30, 75),
    "mid": (75, 150),
    "premium": (150, 300),
    "luxury": (300, float('inf')),
}

# Common words to exclude from keyword extraction
STOP_WORDS = {
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "as", "is", "was", "are", "were", "been",
    "be", "have", "has", "had", "do", "does", "did", "will", "would",
    "could", "should", "may", "might", "must", "shall", "can", "need",
    "this", "that", "these", "those", "it", "its", "my", "your", "our",
    "their", "his", "her", "we", "you", "they", "i", "me", "him", "us",
    "new", "free", "best", "great", "good", "top", "premium", "quality",
    "pack", "set", "piece", "pcs", "count", "size", "color", "style",
}


# =============================================================================
# AMAZON REVIEW
# =============================================================================

@dataclass
class AmazonReview:
    """
    A single Amazon review with psychological signal data.
    
    Key fields for psychological analysis:
    - text: The review content (honest customer language)
    - rating: Customer satisfaction (1-5)
    - helpful_vote: Social proof - how many others found this helpful
    - verified_purchase: Whether this is a validated purchase
    
    The helpful_vote is especially important - reviews with high helpful
    votes contain language patterns that resonate with other customers.
    """
    
    asin: str
    rating: float
    text: str
    title: str = ""
    helpful_vote: int = 0
    verified_purchase: bool = False
    timestamp: Optional[int] = None
    user_id: Optional[str] = None
    product_title: str = ""
    product_brand: str = ""
    
    @property
    def date(self) -> Optional[datetime]:
        """Get review date from timestamp."""
        if self.timestamp:
            try:
                # Handle numeric timestamps (milliseconds)
                if isinstance(self.timestamp, (int, float)):
                    return datetime.fromtimestamp(self.timestamp / 1000)
                # Handle string timestamps (ISO format or Unix timestamp string)
                elif isinstance(self.timestamp, str):
                    # Try numeric string first
                    if self.timestamp.isdigit():
                        return datetime.fromtimestamp(int(self.timestamp) / 1000)
                    # Try ISO format
                    return datetime.fromisoformat(self.timestamp.replace('Z', '+00:00'))
            except (ValueError, OSError, TypeError):
                return None
        return None
    
    @property
    def is_high_quality(self) -> bool:
        """Check if this is a high-quality review for analysis."""
        return (
            len(self.text) >= 50 and
            self.verified_purchase and
            self.helpful_vote >= 0
        )
    
    @property
    def is_persuasive(self) -> bool:
        """
        Check if this review is persuasive (high helpful votes).
        
        Reviews with high helpful votes contain language that influenced
        other customers' decisions - valuable for persuasion learning.
        """
        return self.helpful_vote >= 5
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "asin": self.asin,
            "rating": self.rating,
            "text": self.text,
            "title": self.title,
            "helpful_vote": self.helpful_vote,
            "verified_purchase": self.verified_purchase,
            "timestamp": self.timestamp,
            "date": self.date.isoformat() if self.date else None,
            "product_title": self.product_title,
            "product_brand": self.product_brand,
        }


# =============================================================================
# AMAZON PRODUCT
# =============================================================================

@dataclass
class AmazonProduct:
    """
    An Amazon product with metadata.
    
    Product descriptions (title, description, features) represent
    the brand's "advertisement" - carefully crafted language meant
    to persuade customers.
    """
    
    asin: str
    title: str
    brand: str
    category: str = ""
    main_category: str = ""
    avg_rating: float = 0.0
    rating_count: int = 0
    price: Optional[float] = None
    description: str = ""
    features: List[str] = field(default_factory=list)
    images: List[str] = field(default_factory=list)
    match_score: float = 1.0
    
    @property
    def price_tier(self) -> str:
        """Get price tier for matching."""
        if not self.price:
            return "mid"
        for tier, (low, high) in PRICE_TIERS.items():
            if low <= self.price < high:
                return tier
        return "mid"
    
    @property
    def brand_copy(self) -> str:
        """
        Get the brand's "advertisement" text.
        
        This is the brand's opportunity to persuade - combining
        title, description, and features into a single text for analysis.
        """
        parts = [self.title]
        if self.description:
            parts.append(self.description)
        if self.features:
            parts.extend(self.features)
        return " ".join(parts)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "asin": self.asin,
            "title": self.title,
            "brand": self.brand,
            "category": self.category,
            "main_category": self.main_category,
            "avg_rating": self.avg_rating,
            "rating_count": self.rating_count,
            "price": self.price,
            "description": self.description,
            "features": self.features,
            "price_tier": self.price_tier,
            "match_score": self.match_score,
        }


# =============================================================================
# MATCH QUERY
# =============================================================================

@dataclass
class MatchQuery:
    """
    A query for finding matching reviews.
    
    Uses hierarchical matching:
    1. Brand + Full Title Match (best)
    2. Brand + Key Phrases
    3. Brand + Keywords
    4. Brand Only
    5. Keywords + Price Tier (fallback)
    """
    
    brand: str
    product_name: str
    category: Optional[str] = None
    price: Optional[float] = None
    max_results: int = 100
    
    # Extracted components (populated by extract_search_terms)
    keywords: List[str] = field(default_factory=list)
    key_phrases: List[str] = field(default_factory=list)
    price_tier: str = "mid"
    
    def extract_search_terms(self) -> "MatchQuery":
        """
        Extract keywords and phrases from product name.
        
        Returns self for chaining.
        """
        # Clean the product name
        name_clean = self.product_name.lower()
        name_clean = re.sub(r'[^\w\s-]', ' ', name_clean)
        
        # Split into words
        words = name_clean.split()
        
        # Filter stop words and short words
        self.keywords = [
            w for w in words 
            if w not in STOP_WORDS and len(w) > 2
        ]
        
        # Extract key phrases (2-3 word combinations)
        self.key_phrases = []
        
        # Find capitalized phrases in original
        original_words = self.product_name.split()
        current_phrase = []
        
        for word in original_words:
            if word and word[0].isupper() and word.lower() not in STOP_WORDS:
                current_phrase.append(word.lower())
            else:
                if len(current_phrase) >= 2:
                    self.key_phrases.append(' '.join(current_phrase))
                current_phrase = []
        
        # Don't forget the last phrase
        if len(current_phrase) >= 2:
            self.key_phrases.append(' '.join(current_phrase))
        
        # Also add hyphenated terms as phrases
        hyphenated = re.findall(r'\b\w+-\w+(?:-\w+)?\b', name_clean)
        self.key_phrases.extend(hyphenated)
        
        # Determine price tier
        if self.price:
            for tier, (low, high) in PRICE_TIERS.items():
                if low <= self.price < high:
                    self.price_tier = tier
                    break
        
        return self
    
    def to_fts_query(self) -> str:
        """
        Convert to FTS5 query string.
        
        Prioritizes brand match, then keywords.
        """
        parts = []
        
        # Brand is required
        brand_clean = self.brand.lower().strip()
        if brand_clean:
            parts.append(f'"{brand_clean}"')
        
        # Add keywords with OR
        for keyword in self.keywords[:5]:  # Limit to avoid overly complex queries
            parts.append(keyword)
        
        return " OR ".join(parts) if len(parts) > 1 else parts[0] if parts else ""
