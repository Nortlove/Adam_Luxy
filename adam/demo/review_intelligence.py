#!/usr/bin/env python3
"""
REVIEW INTELLIGENCE SERVICE
===========================

Provides intelligent review matching and analysis for the demo.
Uses the SmartReviewMatcher to find relevant reviews based on
brand, product name, and price.

This bridges the 13.6M+ review corpus to the demo's customer
intelligence capabilities.
"""

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class ReviewIntelligenceResult:
    """Result of review intelligence analysis."""
    brand: str
    product_name: str
    reviews_found: int
    reviews_analyzed: int
    avg_rating: float
    rating_distribution: Dict[int, int]
    top_positive_themes: List[str]
    top_negative_themes: List[str]
    sentiment_score: float  # -1 to 1
    buyer_archetypes: Dict[str, float]
    dominant_archetype: str
    archetype_confidence: float
    sample_reviews: List[Dict]
    match_quality: str  # "exact", "brand_keyword", "keyword_only"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "brand": self.brand,
            "product_name": self.product_name,
            "reviews_found": self.reviews_found,
            "reviews_analyzed": self.reviews_analyzed,
            "avg_rating": round(self.avg_rating, 2),
            "rating_distribution": self.rating_distribution,
            "top_positive_themes": self.top_positive_themes,
            "top_negative_themes": self.top_negative_themes,
            "sentiment_score": round(self.sentiment_score, 3),
            "buyer_archetypes": {k: round(v, 3) for k, v in self.buyer_archetypes.items()},
            "dominant_archetype": self.dominant_archetype,
            "archetype_confidence": round(self.archetype_confidence, 3),
            "sample_reviews": self.sample_reviews[:5],
            "match_quality": self.match_quality,
        }


def analyze_product_reviews(
    brand: str,
    product_name: str,
    price: Optional[float] = None,
    category: Optional[str] = None,
    max_reviews: int = 100,
) -> ReviewIntelligenceResult:
    """
    Analyze reviews for a product using smart matching.
    
    Args:
        brand: Product brand
        product_name: Product name
        price: Product price (for tier matching)
        category: Category to search
        max_reviews: Max reviews to analyze
        
    Returns:
        ReviewIntelligenceResult with analysis
    """
    from adam.intelligence.smart_review_matcher import find_product_reviews
    
    logger.info(f"Analyzing reviews for {brand} - {product_name}")
    
    # Find matching reviews
    matches, stats = find_product_reviews(
        brand=brand,
        product_name=product_name,
        price=price,
        category=category,
    )
    
    if not matches:
        logger.warning(f"No matching reviews found for {brand} - {product_name}")
        return _create_fallback_result(brand, product_name)
    
    # Analyze the matches
    reviews_to_analyze = matches[:max_reviews]
    
    # Calculate rating distribution
    rating_dist = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    total_rating = 0
    
    for match in reviews_to_analyze:
        rating = int(round(match.rating))
        if 1 <= rating <= 5:
            rating_dist[rating] += 1
            total_rating += match.rating
    
    avg_rating = total_rating / len(reviews_to_analyze) if reviews_to_analyze else 4.0
    
    # Determine sentiment
    positive_count = rating_dist[4] + rating_dist[5]
    negative_count = rating_dist[1] + rating_dist[2]
    total = sum(rating_dist.values())
    
    sentiment_score = (positive_count - negative_count) / total if total > 0 else 0
    
    # Infer archetypes from review text
    buyer_archetypes = _infer_archetypes_from_reviews(reviews_to_analyze)
    dominant = max(buyer_archetypes.items(), key=lambda x: x[1])
    
    # Extract themes
    positive_themes, negative_themes = _extract_themes(reviews_to_analyze)
    
    # Determine match quality
    match_quality = "exact"
    if matches[0].match_type == "brand_only":
        match_quality = "brand_only"
    elif matches[0].match_type in ["brand_single_keyword", "brand_multi_keyword"]:
        match_quality = "brand_keyword"
    elif matches[0].match_type == "keyword_price_match":
        match_quality = "keyword_only"
    
    # Build sample reviews
    sample_reviews = [
        {
            "text": m.review_text[:300] + "..." if len(m.review_text) > 300 else m.review_text,
            "rating": m.rating,
            "product": m.product_title[:100] if m.product_title else "",
            "match_type": m.match_type,
            "helpful_votes": m.helpful_votes,
        }
        for m in reviews_to_analyze[:10]
    ]
    
    return ReviewIntelligenceResult(
        brand=brand,
        product_name=product_name,
        reviews_found=stats.final_matches,
        reviews_analyzed=len(reviews_to_analyze),
        avg_rating=avg_rating,
        rating_distribution=rating_dist,
        top_positive_themes=positive_themes,
        top_negative_themes=negative_themes,
        sentiment_score=sentiment_score,
        buyer_archetypes=buyer_archetypes,
        dominant_archetype=dominant[0],
        archetype_confidence=dominant[1],
        sample_reviews=sample_reviews,
        match_quality=match_quality,
    )


def _infer_archetypes_from_reviews(reviews) -> Dict[str, float]:
    """Infer buyer archetypes from review text patterns."""
    
    archetype_scores = {
        "Achiever": 0.0,
        "Explorer": 0.0,
        "Guardian": 0.0,
        "Connector": 0.0,
        "Pragmatist": 0.0,
    }
    
    # Archetype keyword patterns
    patterns = {
        "Achiever": ["quality", "premium", "best", "excellent", "perfect", "worth", "invest", "professional"],
        "Explorer": ["love", "amazing", "adventure", "new", "try", "discover", "unique", "different"],
        "Guardian": ["safe", "reliable", "durable", "sturdy", "protect", "secure", "trust", "warranty"],
        "Connector": ["gift", "family", "friend", "recommend", "everyone", "share", "style", "fashion"],
        "Pragmatist": ["value", "price", "deal", "practical", "basic", "functional", "cheap", "budget"],
    }
    
    total_reviews = len(reviews)
    
    for match in reviews:
        text_lower = match.review_text.lower()
        
        for archetype, keywords in patterns.items():
            for keyword in keywords:
                if keyword in text_lower:
                    archetype_scores[archetype] += 1
    
    # Normalize
    total_signals = sum(archetype_scores.values())
    if total_signals > 0:
        archetype_scores = {k: v / total_signals for k, v in archetype_scores.items()}
    else:
        # Default distribution
        archetype_scores = {k: 0.2 for k in archetype_scores}
    
    return archetype_scores


def _extract_themes(reviews) -> Tuple[List[str], List[str]]:
    """Extract positive and negative themes from reviews."""
    from collections import Counter
    
    positive_words = Counter()
    negative_words = Counter()
    
    positive_indicators = [
        "love", "great", "perfect", "excellent", "amazing", "comfortable", 
        "warm", "quality", "fit", "recommend", "beautiful", "durable",
        "stylish", "waterproof", "worth", "best"
    ]
    
    negative_indicators = [
        "disappointed", "returned", "uncomfortable", "small", "large",
        "broke", "cheap", "poor", "defect", "problem", "issue",
        "cold", "wet", "sizing", "tight", "narrow"
    ]
    
    for match in reviews:
        text_lower = match.review_text.lower()
        rating = match.rating
        
        for word in positive_indicators:
            if word in text_lower:
                if rating >= 4:
                    positive_words[word] += 2
                else:
                    positive_words[word] += 1
        
        for word in negative_indicators:
            if word in text_lower:
                if rating <= 2:
                    negative_words[word] += 2
                else:
                    negative_words[word] += 1
    
    positive_themes = [w for w, c in positive_words.most_common(5)]
    negative_themes = [w for w, c in negative_words.most_common(5)]
    
    return positive_themes, negative_themes


def _create_fallback_result(brand: str, product_name: str) -> ReviewIntelligenceResult:
    """
    Create a fallback result when no reviews are found.
    
    ⚠️ NOTE: This returns LEGACY archetype data as a fallback.
    When real reviews are available, the system uses the 3,750+ granular type system.
    """
    return ReviewIntelligenceResult(
        brand=brand,
        product_name=product_name,
        reviews_found=0,
        reviews_analyzed=0,
        avg_rating=0.0,  # No data - don't fake it
        rating_distribution={1: 0, 2: 0, 3: 0, 4: 0, 5: 0},
        top_positive_themes=[],  # No data
        top_negative_themes=[],  # No data
        sentiment_score=0.0,  # No data
        # LEGACY archetype distribution (fallback only)
        # The granular system uses 15 motivations × 3 styles × 2 focuses × 3 intensities × 4 prices × 8 archetypes
        buyer_archetypes={
            "Achiever": 0.125, "Explorer": 0.125,
            "Guardian": 0.125, "Connector": 0.125,
            "Pragmatist": 0.125, "Analyst": 0.125,
            "Creator": 0.125, "Nurturer": 0.125,
            # Equal distribution = no data
            "_warning": "FALLBACK - No reviews analyzed. Equal distribution indicates no real data."
        },
        dominant_archetype="Unknown",  # No data - don't fake it
        archetype_confidence=0.0,  # No confidence - no data
        sample_reviews=[],
        match_quality="no_match",
    )
