#!/usr/bin/env python3
"""
SMART REVIEW MATCHER
====================

Intelligent hierarchical matching system for finding relevant reviews
based on brand, product name, and price tier.

MATCHING HIERARCHY (highest to lowest weight):
1. Brand + Full Title Match (weight: 1.0)
2. Brand + All Key Phrases (weight: 0.9)
3. Brand + Partial Phrases (weight: 0.7)
4. Brand + Single Keywords (weight: 0.5)
5. Brand Only (weight: 0.3)
6. Keywords Only + Price Match (weight: 0.2)

This ensures we find the BEST matching reviews even when exact
product names don't exist in the corpus.
"""

import gzip
import json
import logging
import re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


# =============================================================================
# CONFIGURATION
# =============================================================================

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

# Price tier ranges for matching
PRICE_TIERS = {
    "budget": (0, 30),
    "low_mid": (30, 75),
    "mid": (75, 150),
    "premium": (150, 300),
    "luxury": (300, float('inf')),
}


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class MatchResult:
    """A single review match with its weight and metadata."""
    review_id: str
    review_text: str
    rating: float
    match_weight: float
    match_type: str  # e.g., "brand_full_title", "brand_keywords", etc.
    matched_terms: List[str]
    product_title: str = ""
    brand: str = ""
    price: Optional[float] = None
    helpful_votes: int = 0
    verified_purchase: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "review_id": self.review_id,
            "review_text": self.review_text[:500] + "..." if len(self.review_text) > 500 else self.review_text,
            "rating": self.rating,
            "match_weight": self.match_weight,
            "match_type": self.match_type,
            "matched_terms": self.matched_terms,
            "product_title": self.product_title,
            "brand": self.brand,
            "price": self.price,
        }


@dataclass
class MatchQuery:
    """A query for finding matching reviews."""
    brand: str
    product_name: str
    price: Optional[float] = None
    category: Optional[str] = None
    
    # Extracted components (populated by extract_search_terms)
    keywords: List[str] = field(default_factory=list)
    key_phrases: List[str] = field(default_factory=list)
    price_tier: str = "mid"
    
    def extract_search_terms(self):
        """Extract keywords and phrases from product name."""
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
        
        # Extract key phrases (2-3 word combinations that might be product names)
        # Look for patterns like "Joan of Arctic", "Air Max", etc.
        self.key_phrases = []
        
        # Find capitalized phrases in original (before lowercasing)
        original_words = self.product_name.split()
        current_phrase = []
        
        for word in original_words:
            # Check if word starts with capital (likely part of product name)
            if word and word[0].isupper() and word.lower() not in STOP_WORDS:
                current_phrase.append(word.lower())
            else:
                if len(current_phrase) >= 2:
                    self.key_phrases.append(' '.join(current_phrase))
                current_phrase = []
        
        # Don't forget the last phrase
        if len(current_phrase) >= 2:
            self.key_phrases.append(' '.join(current_phrase))
        
        # Also add any hyphenated terms as phrases
        hyphenated = re.findall(r'\b\w+-\w+(?:-\w+)?\b', name_clean)
        self.key_phrases.extend(hyphenated)
        
        # Determine price tier
        if self.price:
            for tier, (low, high) in PRICE_TIERS.items():
                if low <= self.price < high:
                    self.price_tier = tier
                    break
        
        return self


@dataclass
class MatchingStats:
    """Statistics about the matching process."""
    total_reviews_searched: int = 0
    brand_matches: int = 0
    title_matches: int = 0
    keyword_matches: int = 0
    price_tier_matches: int = 0
    final_matches: int = 0
    search_time_ms: float = 0.0


# =============================================================================
# SMART REVIEW MATCHER
# =============================================================================

class SmartReviewMatcher:
    """
    Intelligent hierarchical review matching system.
    
    Finds the best matching reviews for a product using a multi-level
    search strategy that prioritizes specificity while ensuring
    we always find relevant matches.
    """
    
    def __init__(
        self,
        amazon_data_dir: Optional[Path] = None,
        max_reviews_per_query: int = 100,
        cache_enabled: bool = True,
    ):
        """
        Initialize the matcher.
        
        Args:
            amazon_data_dir: Path to Amazon review data
            max_reviews_per_query: Maximum reviews to return per query
            cache_enabled: Whether to cache loaded reviews
        """
        self.amazon_data_dir = amazon_data_dir or Path("/Volumes/Sped/Nocera Models/Review Data/Amazon")
        self.max_reviews = max_reviews_per_query
        self.cache_enabled = cache_enabled
        
        # Caches
        self._brand_index: Dict[str, List[Dict]] = {}  # brand -> reviews
        self._category_loaded: Set[str] = set()
        self._review_cache: Dict[str, List[Dict]] = {}  # category -> reviews
    
    def find_matching_reviews(
        self,
        brand: str,
        product_name: str,
        price: Optional[float] = None,
        category: Optional[str] = None,
        categories_to_search: Optional[List[str]] = None,
    ) -> Tuple[List[MatchResult], MatchingStats]:
        """
        Find matching reviews using hierarchical matching.
        
        Args:
            brand: Product brand (e.g., "SOREL")
            product_name: Product name (e.g., "Womens Joan of Arctic Waterproof Boots")
            price: Product price for tier matching
            category: Primary category to search (e.g., "Clothing_Shoes_and_Jewelry")
            categories_to_search: Additional categories to search
            
        Returns:
            Tuple of (matched reviews, matching statistics)
        """
        import time
        start_time = time.time()
        
        stats = MatchingStats()
        
        # Build the query
        query = MatchQuery(
            brand=brand,
            product_name=product_name,
            price=price,
            category=category,
        )
        query.extract_search_terms()
        
        logger.info(f"Smart matching: brand='{brand}', keywords={query.keywords}, phrases={query.key_phrases}")
        
        # Determine which categories to search
        search_categories = []
        if category:
            search_categories.append(category)
        if categories_to_search:
            search_categories.extend(categories_to_search)
        
        # Default categories for common product types
        if not search_categories:
            search_categories = self._infer_categories(product_name, query.keywords)
        
        # Collect all matches
        all_matches: List[MatchResult] = []
        
        for cat in search_categories:
            reviews = self._load_category_reviews(cat)
            stats.total_reviews_searched += len(reviews)
            
            cat_matches = self._match_reviews_hierarchical(
                reviews=reviews,
                query=query,
                stats=stats,
            )
            all_matches.extend(cat_matches)
        
        # Sort by weight (highest first) and deduplicate
        all_matches.sort(key=lambda m: m.match_weight, reverse=True)
        
        # Deduplicate by review_id
        seen_ids = set()
        unique_matches = []
        for match in all_matches:
            if match.review_id not in seen_ids:
                seen_ids.add(match.review_id)
                unique_matches.append(match)
        
        # Limit results
        final_matches = unique_matches[:self.max_reviews]
        stats.final_matches = len(final_matches)
        stats.search_time_ms = (time.time() - start_time) * 1000
        
        logger.info(
            f"Smart matching complete: {stats.final_matches} matches found "
            f"from {stats.total_reviews_searched} reviews in {stats.search_time_ms:.0f}ms"
        )
        
        return final_matches, stats
    
    def _match_reviews_hierarchical(
        self,
        reviews: List[Dict],
        query: MatchQuery,
        stats: MatchingStats,
    ) -> List[MatchResult]:
        """
        Apply hierarchical matching to a list of reviews.
        
        Matching Levels:
        1. Brand + Full Title (weight: 1.0)
        2. Brand + All Key Phrases (weight: 0.9)
        3. Brand + Multiple Keywords (weight: 0.7)
        4. Brand + Single Keyword (weight: 0.5)
        5. Brand Only (weight: 0.3)
        6. Keywords + Price Tier Match (weight: 0.2)
        
        NOTE: Brand matching is done against the review TEXT since
        Amazon review data doesn't always have a brand field.
        """
        matches = []
        brand_lower = query.brand.lower().strip()
        title_lower = query.product_name.lower().strip()
        keywords = [k.lower() for k in query.keywords]
        key_phrases = [p.lower() for p in query.key_phrases]
        
        for review in reviews:
            # Extract review fields
            review_text = review.get("text", "") or review.get("reviewText", "") or ""
            review_title = review.get("title", "") or review.get("summary", "") or ""
            product_title = review.get("parent_asin_title", "") or review.get("asin_title", "") or ""
            review_brand = review.get("brand", "") or ""
            rating = review.get("rating", 0) or review.get("overall", 0) or 0
            review_id = review.get("review_id", "") or review.get("reviewerID", "") or review.get("user_id", "") or str(hash(review_text[:100]))
            price = review.get("price")
            helpful = review.get("helpful_vote", 0) or review.get("helpful", [0, 0])
            if isinstance(helpful, list):
                helpful = helpful[0] if helpful else 0
            verified = review.get("verified_purchase", False) or review.get("verified", False)
            asin = review.get("asin", "") or review.get("parent_asin", "")
            
            # Normalize for matching - IMPORTANT: Search across ALL text fields
            product_title_lower = product_title.lower()
            review_brand_lower = review_brand.lower()
            review_text_lower = review_text.lower()
            review_title_lower = review_title.lower()
            
            # Combine all searchable text
            full_text_lower = f"{product_title_lower} {review_text_lower} {review_title_lower} {review_brand_lower}"
            
            # Check if brand is mentioned ANYWHERE in the review content
            # This is crucial since Amazon reviews don't have a brand field
            brand_found_in_text = brand_lower and (
                brand_lower in review_brand_lower or
                brand_lower in review_text_lower or
                brand_lower in review_title_lower or
                brand_lower in product_title_lower
            )
            
            # === LEVEL 1: Brand + Full Title Match (weight: 1.0) ===
            if brand_found_in_text:
                stats.brand_matches += 1
                
                # Check for title match
                title_words = title_lower.split()
                title_match_count = sum(1 for w in title_words if w in product_title_lower)
                title_match_ratio = title_match_count / len(title_words) if title_words else 0
                
                if title_match_ratio > 0.8:  # 80%+ title match
                    stats.title_matches += 1
                    matches.append(MatchResult(
                        review_id=review_id,
                        review_text=review_text,
                        rating=float(rating),
                        match_weight=1.0,
                        match_type="brand_full_title",
                        matched_terms=[brand_lower] + title_words,
                        product_title=product_title,
                        brand=review_brand,
                        price=price,
                        helpful_votes=helpful,
                        verified_purchase=verified,
                    ))
                    continue
                
                # === LEVEL 2: Brand + All Key Phrases (weight: 0.9) ===
                if key_phrases:
                    phrases_found = [p for p in key_phrases if p in product_title_lower]
                    if len(phrases_found) == len(key_phrases):
                        matches.append(MatchResult(
                            review_id=review_id,
                            review_text=review_text,
                            rating=float(rating),
                            match_weight=0.9,
                            match_type="brand_all_phrases",
                            matched_terms=[brand_lower] + phrases_found,
                            product_title=product_title,
                            brand=review_brand,
                            price=price,
                            helpful_votes=helpful,
                            verified_purchase=verified,
                        ))
                        continue
                
                # === LEVEL 3: Brand + Multiple Keywords (weight: 0.7) ===
                if len(keywords) >= 2:
                    keywords_found = [k for k in keywords if k in product_title_lower or k in full_text_lower]
                    if len(keywords_found) >= 2:
                        # Weight based on how many keywords matched
                        weight = 0.5 + (0.2 * min(len(keywords_found) / len(keywords), 1.0))
                        stats.keyword_matches += 1
                        matches.append(MatchResult(
                            review_id=review_id,
                            review_text=review_text,
                            rating=float(rating),
                            match_weight=weight,
                            match_type="brand_multi_keyword",
                            matched_terms=[brand_lower] + keywords_found,
                            product_title=product_title,
                            brand=review_brand,
                            price=price,
                            helpful_votes=helpful,
                            verified_purchase=verified,
                        ))
                        continue
                
                # === LEVEL 4: Brand + Single Keyword (weight: 0.5) ===
                if keywords:
                    keywords_found = [k for k in keywords if k in product_title_lower]
                    if keywords_found:
                        matches.append(MatchResult(
                            review_id=review_id,
                            review_text=review_text,
                            rating=float(rating),
                            match_weight=0.5,
                            match_type="brand_single_keyword",
                            matched_terms=[brand_lower] + keywords_found[:1],
                            product_title=product_title,
                            brand=review_brand,
                            price=price,
                            helpful_votes=helpful,
                            verified_purchase=verified,
                        ))
                        continue
                
                # === LEVEL 5: Brand Only (weight: 0.3) ===
                matches.append(MatchResult(
                    review_id=review_id,
                    review_text=review_text,
                    rating=float(rating),
                    match_weight=0.3,
                    match_type="brand_only",
                    matched_terms=[brand_lower],
                    product_title=product_title,
                    brand=review_brand,
                    price=price,
                    helpful_votes=helpful,
                    verified_purchase=verified,
                ))
            
            # === LEVEL 6: Keywords + Price Tier Match (no brand match, weight: 0.2) ===
            elif not brand_found_in_text:
                # Only if we have keywords and price info
                if keywords and query.price and price:
                    keywords_found = [k for k in keywords if k in product_title_lower]
                    
                    if len(keywords_found) >= 2:
                        # Check price tier match
                        try:
                            price_float = float(price) if isinstance(price, str) else price
                            query_tier = query.price_tier
                            
                            # Determine review product's price tier
                            review_tier = "mid"
                            for tier, (low, high) in PRICE_TIERS.items():
                                if low <= price_float < high:
                                    review_tier = tier
                                    break
                            
                            if review_tier == query_tier:
                                stats.price_tier_matches += 1
                                matches.append(MatchResult(
                                    review_id=review_id,
                                    review_text=review_text,
                                    rating=float(rating),
                                    match_weight=0.2,
                                    match_type="keyword_price_match",
                                    matched_terms=keywords_found,
                                    product_title=product_title,
                                    brand=review_brand,
                                    price=price,
                                    helpful_votes=helpful,
                                    verified_purchase=verified,
                                ))
                        except (ValueError, TypeError):
                            pass
        
        return matches
    
    def _infer_categories(self, product_name: str, keywords: List[str]) -> List[str]:
        """Infer likely categories from product name and keywords."""
        name_lower = product_name.lower()
        
        # Category inference rules
        if any(w in name_lower for w in ["boot", "shoe", "sneaker", "sandal", "heel", "loafer"]):
            return ["Clothing_Shoes_and_Jewelry", "Sports_and_Outdoors"]
        elif any(w in name_lower for w in ["phone", "tablet", "laptop", "computer", "electronics"]):
            return ["Electronics", "Cell_Phones_and_Accessories"]
        elif any(w in name_lower for w in ["kitchen", "cookware", "appliance"]):
            return ["Home_and_Kitchen", "Appliances"]
        elif any(w in name_lower for w in ["tool", "drill", "saw", "hammer"]):
            return ["Tools_and_Home_Improvement"]
        elif any(w in name_lower for w in ["toy", "game", "puzzle"]):
            return ["Toys_and_Games"]
        elif any(w in name_lower for w in ["beauty", "makeup", "skincare", "cosmetic"]):
            return ["Beauty_and_Personal_Care", "All_Beauty"]
        elif any(w in name_lower for w in ["book", "novel", "reading"]):
            return ["Books", "Kindle_Store"]
        elif any(w in name_lower for w in ["pet", "dog", "cat"]):
            return ["Pet_Supplies"]
        elif any(w in name_lower for w in ["outdoor", "camping", "hiking", "sports"]):
            return ["Sports_and_Outdoors", "Patio_Lawn_and_Garden"]
        elif any(w in name_lower for w in ["car", "auto", "vehicle"]):
            return ["Automotive"]
        else:
            # Default to most common categories
            return ["Clothing_Shoes_and_Jewelry", "Electronics", "Home_and_Kitchen"]
    
    def _load_metadata(self, category: str) -> Dict[str, Dict]:
        """Load metadata file to get product titles and brands by ASIN."""
        metadata = {}
        
        meta_paths = [
            self.amazon_data_dir / f"meta_{category}.jsonl",
            self.amazon_data_dir / f"meta_{category}.jsonl.gz",
        ]
        
        for filepath in meta_paths:
            if filepath.exists():
                logger.info(f"Loading metadata from {filepath}")
                try:
                    opener = gzip.open if filepath.suffix == '.gz' else open
                    with opener(filepath, 'rt', encoding='utf-8') as f:
                        for i, line in enumerate(f):
                            if i >= 100000:  # Limit metadata loading
                                break
                            try:
                                item = json.loads(line)
                                asin = item.get("parent_asin") or item.get("asin")
                                if asin:
                                    metadata[asin] = {
                                        "title": item.get("title", ""),
                                        "brand": item.get("brand", "") or item.get("store", ""),
                                        "price": item.get("price"),
                                        "categories": item.get("categories", []),
                                    }
                            except json.JSONDecodeError:
                                continue
                    logger.info(f"Loaded {len(metadata)} metadata records")
                    break
                except Exception as e:
                    logger.error(f"Error loading metadata {filepath}: {e}")
        
        return metadata
    
    def _load_category_reviews(self, category: str, max_reviews: int = 100000) -> List[Dict]:
        """
        Load reviews from a category file with metadata enrichment.
        
        Supports both .jsonl and .jsonl.gz formats.
        """
        if category in self._review_cache:
            return self._review_cache[category]
        
        # First load metadata to enrich reviews
        metadata = self._load_metadata(category)
        
        reviews = []
        
        # Try different file paths and formats
        possible_paths = [
            self.amazon_data_dir / f"{category}.jsonl",
            self.amazon_data_dir / f"{category}.jsonl.gz",
            Path(f"/Users/chrisnocera/Sites/adam-platform/amazon/{category}.jsonl"),
        ]
        
        for filepath in possible_paths:
            if filepath.exists():
                logger.info(f"Loading reviews from {filepath}")
                
                try:
                    opener = gzip.open if filepath.suffix == '.gz' else open
                    with opener(filepath, 'rt', encoding='utf-8') as f:
                        for i, line in enumerate(f):
                            if i >= max_reviews:
                                break
                            try:
                                review = json.loads(line)
                                
                                # Enrich with metadata if available
                                asin = review.get("parent_asin") or review.get("asin")
                                if asin and asin in metadata:
                                    meta = metadata[asin]
                                    review["parent_asin_title"] = meta.get("title", "")
                                    review["brand"] = meta.get("brand", "")
                                    if not review.get("price"):
                                        review["price"] = meta.get("price")
                                
                                reviews.append(review)
                            except json.JSONDecodeError:
                                continue
                    
                    logger.info(f"Loaded {len(reviews)} reviews from {category}")
                    break
                    
                except Exception as e:
                    logger.error(f"Error loading {filepath}: {e}")
                    continue
        
        if self.cache_enabled and reviews:
            self._review_cache[category] = reviews
        
        return reviews
    
    def search_brand(
        self,
        brand: str,
        categories: Optional[List[str]] = None,
        max_results: int = 1000,
    ) -> List[Dict]:
        """
        Search for all reviews from a specific brand.
        
        Args:
            brand: Brand name to search for
            categories: Categories to search (or all if None)
            max_results: Maximum results to return
            
        Returns:
            List of review dictionaries
        """
        brand_lower = brand.lower().strip()
        results = []
        
        if categories is None:
            categories = ["Clothing_Shoes_and_Jewelry"]  # Default
        
        for cat in categories:
            reviews = self._load_category_reviews(cat)
            
            for review in reviews:
                review_brand = (review.get("brand", "") or "").lower()
                if brand_lower in review_brand:
                    results.append(review)
                    if len(results) >= max_results:
                        return results
        
        return results


# =============================================================================
# SINGLETON AND HELPER FUNCTIONS
# =============================================================================

_matcher: Optional[SmartReviewMatcher] = None


def get_smart_matcher() -> SmartReviewMatcher:
    """Get singleton SmartReviewMatcher instance."""
    global _matcher
    if _matcher is None:
        _matcher = SmartReviewMatcher()
    return _matcher


def find_product_reviews(
    brand: str,
    product_name: str,
    price: Optional[float] = None,
    category: Optional[str] = None,
) -> Tuple[List[MatchResult], MatchingStats]:
    """
    Convenience function to find matching reviews for a product.
    
    Args:
        brand: Product brand
        product_name: Product name
        price: Product price (for tier matching)
        category: Primary category to search
        
    Returns:
        Tuple of (matches, stats)
    """
    matcher = get_smart_matcher()
    return matcher.find_matching_reviews(
        brand=brand,
        product_name=product_name,
        price=price,
        category=category,
    )


# =============================================================================
# TEST / DEMO
# =============================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Test with SOREL boots
    print("=" * 70)
    print("TESTING SMART REVIEW MATCHER")
    print("=" * 70)
    
    matcher = SmartReviewMatcher()
    
    matches, stats = matcher.find_matching_reviews(
        brand="SOREL",
        product_name="Womens Joan of Arctic Waterproof Boots",
        price=182.0,
        category="Clothing_Shoes_and_Jewelry",
    )
    
    print(f"\nMatching Statistics:")
    print(f"  Total reviews searched: {stats.total_reviews_searched:,}")
    print(f"  Brand matches: {stats.brand_matches:,}")
    print(f"  Title matches: {stats.title_matches:,}")
    print(f"  Keyword matches: {stats.keyword_matches:,}")
    print(f"  Price tier matches: {stats.price_tier_matches:,}")
    print(f"  Final matches: {stats.final_matches:,}")
    print(f"  Search time: {stats.search_time_ms:.0f}ms")
    
    print(f"\nTop 10 Matches:")
    for i, match in enumerate(matches[:10], 1):
        print(f"\n{i}. [{match.match_type}] Weight: {match.match_weight:.2f}")
        print(f"   Product: {match.product_title[:60]}...")
        print(f"   Brand: {match.brand}")
        print(f"   Rating: {match.rating}")
        print(f"   Terms: {match.matched_terms}")
        print(f"   Review: {match.review_text[:100]}...")
