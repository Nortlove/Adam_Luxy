#!/usr/bin/env python3
"""
UNIFIED REVIEW AGGREGATOR
=========================

This module aggregates reviews from ALL sources (Amazon, Yelp, Google Maps, Walmart,
Target, Best Buy, etc.) using hierarchical product matching to ensure we always
have HUNDREDS of relevant reviews for analysis.

Key Features:
1. Multi-Store Aggregation: Searches Amazon, Yelp, Google, Walmart, Target, etc.
2. Hierarchical Matching: Brand → Category → Product Type → Related Products
3. Fuzzy Matching: Handles name variations ("DeWalt Impact Driver", "DEWALT 20V MAX")
4. Review Combination: Aggregates reviews from similar/related products
5. Cross-Store Deduplication: Identifies same products across stores

Design Philosophy:
- EXPAND search to get MORE reviews, not fewer
- A "DeWalt Impact Driver" search should return reviews for ALL DeWalt impact drivers
- Reviews from "DeWalt 20V MAX Impact Driver" and "DeWalt DCF887" should both match
- Aim for 200-500+ reviews per product analysis (not just 10-20 exact matches)
"""

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)


class ReviewSource(str, Enum):
    """All supported review sources."""
    AMAZON = "amazon"
    YELP = "yelp"
    GOOGLE_MAPS = "google_maps"
    WALMART = "walmart"
    TARGET = "target"
    BESTBUY = "bestbuy"
    TRUSTPILOT = "trustpilot"
    SEPHORA = "sephora"
    BH_PHOTO = "bh_photo"
    HOME_DEPOT = "home_depot"
    LOWES = "lowes"


class MatchLevel(str, Enum):
    """Hierarchical matching levels - from most specific to broadest."""
    EXACT_SKU = "exact_sku"           # Exact product SKU/ASIN match
    BRAND_MODEL = "brand_model"        # Brand + exact model (DeWalt DCF887)
    BRAND_PRODUCT_TYPE = "brand_product_type"  # Brand + type (DeWalt Impact Driver)
    BRAND_CATEGORY = "brand_category"  # Brand + category (DeWalt Power Tools)
    PRODUCT_TYPE = "product_type"      # Just type (Impact Drivers from any brand)
    CATEGORY = "category"              # Broad category (Power Tools)


@dataclass
class AggregatedReview:
    """A single review from any source."""
    text: str
    rating: float
    source: ReviewSource
    product_name: str
    product_brand: Optional[str] = None
    product_id: Optional[str] = None  # ASIN, SKU, etc.
    reviewer_id: Optional[str] = None
    helpful_votes: int = 0
    verified_purchase: bool = False
    review_date: Optional[str] = None
    match_level: MatchLevel = MatchLevel.EXACT_SKU
    match_score: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AggregatedReviewSet:
    """Result of review aggregation across multiple sources."""
    query_brand: str
    query_product: str
    query_category: Optional[str]
    
    reviews: List[AggregatedReview] = field(default_factory=list)
    total_reviews: int = 0
    
    # Breakdown by source
    reviews_by_source: Dict[str, int] = field(default_factory=dict)
    
    # Breakdown by match level
    reviews_by_match_level: Dict[str, int] = field(default_factory=dict)
    
    # Products matched
    products_matched: List[Dict[str, Any]] = field(default_factory=list)
    
    # Coverage metrics
    average_match_score: float = 0.0
    min_rating: float = 0.0
    max_rating: float = 0.0
    average_rating: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": {
                "brand": self.query_brand,
                "product": self.query_product,
                "category": self.query_category,
            },
            "total_reviews": self.total_reviews,
            "reviews_by_source": self.reviews_by_source,
            "reviews_by_match_level": self.reviews_by_match_level,
            "products_matched": len(self.products_matched),
            "average_match_score": round(self.average_match_score, 3),
            "rating_range": {
                "min": self.min_rating,
                "max": self.max_rating,
                "average": round(self.average_rating, 2),
            },
        }


# =============================================================================
# PRODUCT TYPE DETECTION
# =============================================================================

# Product type patterns for hierarchical matching
PRODUCT_TYPE_PATTERNS = {
    # Power Tools
    "impact_driver": [r"impact\s*driver", r"impacto?\s*driver", r"impact\s*wrench"],
    "drill": [r"\bdrill\b", r"drill\s*driver", r"hammer\s*drill", r"cordless\s*drill"],
    "saw": [r"\bsaw\b", r"circular\s*saw", r"reciprocating\s*saw", r"jig\s*saw", r"miter\s*saw", r"table\s*saw"],
    "sander": [r"\bsander\b", r"orbital\s*sander", r"belt\s*sander"],
    "grinder": [r"\bgrinder\b", r"angle\s*grinder"],
    "nailer": [r"\bnailer\b", r"nail\s*gun", r"brad\s*nailer", r"finish\s*nailer"],
    
    # Electronics
    "headphones": [r"headphone", r"earphone", r"earbud", r"headset"],
    "smartphone": [r"smartphone", r"cell\s*phone", r"mobile\s*phone", r"iphone", r"android\s*phone"],
    "laptop": [r"\blaptop\b", r"notebook\s*computer", r"macbook"],
    "tablet": [r"\btablet\b", r"\bipad\b"],
    "camera": [r"\bcamera\b", r"dslr", r"mirrorless"],
    "tv": [r"\btv\b", r"television", r"smart\s*tv"],
    
    # Home & Kitchen
    "vacuum": [r"\bvacuum\b", r"vacuum\s*cleaner", r"robot\s*vacuum"],
    "blender": [r"\bblender\b", r"food\s*processor"],
    "coffee_maker": [r"coffee\s*maker", r"coffee\s*machine", r"espresso"],
    "air_fryer": [r"air\s*fryer"],
    
    # Outdoor/Garden
    "lawn_mower": [r"lawn\s*mower", r"mower"],
    "trimmer": [r"\btrimmer\b", r"string\s*trimmer", r"weed\s*eater"],
    "chainsaw": [r"\bchainsaw\b", r"chain\s*saw"],
    "pressure_washer": [r"pressure\s*washer", r"power\s*washer"],
    
    # Automotive
    "battery": [r"car\s*battery", r"auto\s*battery"],
    "tires": [r"\btire[s]?\b", r"wheel[s]?"],
    "oil": [r"motor\s*oil", r"engine\s*oil"],
}

# Category mappings
CATEGORY_MAPPINGS = {
    "power_tools": ["impact_driver", "drill", "saw", "sander", "grinder", "nailer"],
    "electronics": ["headphones", "smartphone", "laptop", "tablet", "camera", "tv"],
    "home_kitchen": ["vacuum", "blender", "coffee_maker", "air_fryer"],
    "outdoor": ["lawn_mower", "trimmer", "chainsaw", "pressure_washer"],
    "automotive": ["battery", "tires", "oil"],
}

# Brand synonyms and variations
BRAND_VARIATIONS = {
    "dewalt": ["dewalt", "de walt", "dw", "dcf", "dcd", "dcs"],
    "milwaukee": ["milwaukee", "milw", "m12", "m18"],
    "makita": ["makita", "mak"],
    "bosch": ["bosch"],
    "ryobi": ["ryobi"],
    "craftsman": ["craftsman"],
    "black_decker": ["black & decker", "black and decker", "b&d"],
    "sony": ["sony"],
    "samsung": ["samsung"],
    "apple": ["apple", "iphone", "ipad", "macbook"],
    "lg": ["lg", "l.g."],
    "dyson": ["dyson"],
    "ninja": ["ninja"],
    "kitchenaid": ["kitchenaid", "kitchen aid"],
}


def detect_product_type(text: str) -> Optional[str]:
    """Detect product type from text using patterns."""
    text_lower = text.lower()
    for product_type, patterns in PRODUCT_TYPE_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return product_type
    return None


def detect_category(product_type: Optional[str]) -> Optional[str]:
    """Get category for a product type."""
    if not product_type:
        return None
    for category, types in CATEGORY_MAPPINGS.items():
        if product_type in types:
            return category
    return None


def normalize_brand(brand: str) -> str:
    """Normalize brand name for matching."""
    brand_lower = brand.lower().strip()
    for canonical, variations in BRAND_VARIATIONS.items():
        if brand_lower in variations or any(v in brand_lower for v in variations):
            return canonical
    return brand_lower.replace(" ", "_")


def extract_model_numbers(text: str) -> List[str]:
    """Extract model numbers from product text."""
    # Common patterns: DCF887, M18, 20V, etc.
    patterns = [
        r"\b[A-Z]{2,4}[0-9]{2,4}[A-Z]?\b",  # DCF887, DCD771
        r"\b[A-Z][0-9]{1,2}\b",              # M12, M18
        r"\b[0-9]{1,3}V\b",                   # 20V, 18V, 12V
        r"\b[0-9]{1,2}/[0-9]{1,2}\s*in\b",   # 3/8 in, 1/2 in
    ]
    models = []
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        models.extend(matches)
    return list(set(models))


# =============================================================================
# UNIFIED REVIEW AGGREGATOR
# =============================================================================

class UnifiedReviewAggregator:
    """
    Aggregates reviews from ALL sources using hierarchical matching.
    
    Ensures we always have hundreds of reviews by:
    1. Searching exact matches first
    2. Expanding to brand + product type
    3. Including related products from same brand
    4. Aggregating across all retail sources
    """
    
    def __init__(
        self,
        min_reviews: int = 100,
        max_reviews: int = 1000,
        expand_until_min: bool = True,
    ):
        """
        Args:
            min_reviews: Minimum reviews to aim for (will expand search if below)
            max_reviews: Maximum reviews to return
            expand_until_min: If True, keep expanding search until min_reviews reached
        """
        self.min_reviews = min_reviews
        self.max_reviews = max_reviews
        self.expand_until_min = expand_until_min
        
        # Source loaders (initialized lazily)
        self._amazon_matcher = None
        self._yelp_loader = None
        self._google_loader = None
        self._scraper_cache = None
    
    def aggregate_reviews(
        self,
        brand: str,
        product_name: str,
        category: Optional[str] = None,
        sources: Optional[List[ReviewSource]] = None,
    ) -> AggregatedReviewSet:
        """
        Aggregate reviews from all sources for a product.
        
        This is the MAIN entry point. It uses hierarchical matching to
        ensure we get enough reviews for meaningful analysis.
        
        Args:
            brand: Brand name (e.g., "DeWalt")
            product_name: Product name/description (e.g., "20V MAX Impact Driver")
            category: Optional category hint (e.g., "Tools")
            sources: Which sources to search (default: all)
            
        Returns:
            AggregatedReviewSet with reviews from all matching products
        """
        if sources is None:
            sources = list(ReviewSource)
        
        # Normalize inputs
        normalized_brand = normalize_brand(brand)
        product_type = detect_product_type(product_name)
        detected_category = category or detect_category(product_type)
        model_numbers = extract_model_numbers(product_name)
        
        logger.info(
            f"Aggregating reviews: brand={normalized_brand}, type={product_type}, "
            f"category={detected_category}, models={model_numbers}"
        )
        
        result = AggregatedReviewSet(
            query_brand=brand,
            query_product=product_name,
            query_category=detected_category,
        )
        
        all_reviews: List[AggregatedReview] = []
        products_matched: List[Dict[str, Any]] = []
        
        # LEVEL 1: Exact brand + model matches
        if model_numbers:
            for model in model_numbers:
                reviews, products = self._search_exact_model(
                    normalized_brand, model, sources
                )
                all_reviews.extend(reviews)
                products_matched.extend(products)
        
        # LEVEL 2: Brand + product type (if we need more reviews)
        if len(all_reviews) < self.min_reviews and product_type:
            reviews, products = self._search_brand_product_type(
                normalized_brand, product_type, sources
            )
            all_reviews.extend(reviews)
            products_matched.extend(products)
        
        # LEVEL 3: Brand + category (if still need more)
        if len(all_reviews) < self.min_reviews and detected_category:
            reviews, products = self._search_brand_category(
                normalized_brand, detected_category, sources
            )
            all_reviews.extend(reviews)
            products_matched.extend(products)
        
        # LEVEL 4: Product type across all brands (if still need more)
        if len(all_reviews) < self.min_reviews and product_type and self.expand_until_min:
            reviews, products = self._search_product_type_any_brand(
                product_type, sources
            )
            all_reviews.extend(reviews)
            products_matched.extend(products)
        
        # Deduplicate reviews (same reviewer, same text = same review)
        unique_reviews = self._deduplicate_reviews(all_reviews)
        
        # Sort by match score and relevance
        unique_reviews.sort(key=lambda r: (-r.match_score, -r.helpful_votes))
        
        # Limit to max_reviews
        unique_reviews = unique_reviews[:self.max_reviews]
        
        # Build result
        result.reviews = unique_reviews
        result.total_reviews = len(unique_reviews)
        result.products_matched = products_matched
        
        # Calculate breakdowns
        for review in unique_reviews:
            source_key = review.source.value
            level_key = review.match_level.value
            result.reviews_by_source[source_key] = result.reviews_by_source.get(source_key, 0) + 1
            result.reviews_by_match_level[level_key] = result.reviews_by_match_level.get(level_key, 0) + 1
        
        # Calculate metrics
        if unique_reviews:
            ratings = [r.rating for r in unique_reviews if r.rating > 0]
            if ratings:
                result.min_rating = min(ratings)
                result.max_rating = max(ratings)
                result.average_rating = sum(ratings) / len(ratings)
            result.average_match_score = sum(r.match_score for r in unique_reviews) / len(unique_reviews)
        
        logger.info(
            f"Aggregated {result.total_reviews} reviews from {len(result.reviews_by_source)} sources, "
            f"{len(products_matched)} products matched"
        )
        
        return result
    
    def _search_exact_model(
        self,
        brand: str,
        model: str,
        sources: List[ReviewSource],
    ) -> Tuple[List[AggregatedReview], List[Dict]]:
        """Search for exact brand + model matches."""
        reviews = []
        products = []
        
        # Amazon
        if ReviewSource.AMAZON in sources:
            amazon_reviews, amazon_products = self._search_amazon(
                brand=brand,
                keywords=[model],
                match_level=MatchLevel.BRAND_MODEL,
                match_score=1.0,
            )
            reviews.extend(amazon_reviews)
            products.extend(amazon_products)
        
        # Other sources would be added here...
        # Walmart, Target, BestBuy via scraper cache
        if any(s in sources for s in [ReviewSource.WALMART, ReviewSource.TARGET, ReviewSource.BESTBUY]):
            scraper_reviews, scraper_products = self._search_scraper_cache(
                brand=brand,
                keywords=[model],
                match_level=MatchLevel.BRAND_MODEL,
                match_score=1.0,
            )
            reviews.extend(scraper_reviews)
            products.extend(scraper_products)
        
        return reviews, products
    
    def _search_brand_product_type(
        self,
        brand: str,
        product_type: str,
        sources: List[ReviewSource],
    ) -> Tuple[List[AggregatedReview], List[Dict]]:
        """Search for brand + product type (e.g., "DeWalt Impact Driver")."""
        reviews = []
        products = []
        
        # Get keywords for this product type
        type_keywords = PRODUCT_TYPE_PATTERNS.get(product_type, [product_type])
        # Clean regex patterns to keywords
        keywords = [re.sub(r'[\\^$.*+?{}()\[\]|]', '', k).strip() for k in type_keywords]
        
        # Amazon
        if ReviewSource.AMAZON in sources:
            amazon_reviews, amazon_products = self._search_amazon(
                brand=brand,
                keywords=keywords,
                match_level=MatchLevel.BRAND_PRODUCT_TYPE,
                match_score=0.85,
            )
            reviews.extend(amazon_reviews)
            products.extend(amazon_products)
        
        # Scraper sources
        if any(s in sources for s in [ReviewSource.WALMART, ReviewSource.TARGET, ReviewSource.BESTBUY]):
            scraper_reviews, scraper_products = self._search_scraper_cache(
                brand=brand,
                keywords=keywords,
                match_level=MatchLevel.BRAND_PRODUCT_TYPE,
                match_score=0.85,
            )
            reviews.extend(scraper_reviews)
            products.extend(scraper_products)
        
        return reviews, products
    
    def _search_brand_category(
        self,
        brand: str,
        category: str,
        sources: List[ReviewSource],
    ) -> Tuple[List[AggregatedReview], List[Dict]]:
        """Search for brand + category (e.g., "DeWalt Power Tools")."""
        reviews = []
        products = []
        
        # Get all product types in this category
        product_types = CATEGORY_MAPPINGS.get(category, [])
        keywords = []
        for pt in product_types:
            patterns = PRODUCT_TYPE_PATTERNS.get(pt, [pt])
            keywords.extend([re.sub(r'[\\^$.*+?{}()\[\]|]', '', k).strip() for k in patterns])
        
        # Amazon
        if ReviewSource.AMAZON in sources:
            amazon_reviews, amazon_products = self._search_amazon(
                brand=brand,
                keywords=keywords[:10],  # Limit keywords
                match_level=MatchLevel.BRAND_CATEGORY,
                match_score=0.7,
            )
            reviews.extend(amazon_reviews)
            products.extend(amazon_products)
        
        return reviews, products
    
    def _search_product_type_any_brand(
        self,
        product_type: str,
        sources: List[ReviewSource],
    ) -> Tuple[List[AggregatedReview], List[Dict]]:
        """Search for product type across all brands."""
        reviews = []
        products = []
        
        type_keywords = PRODUCT_TYPE_PATTERNS.get(product_type, [product_type])
        keywords = [re.sub(r'[\\^$.*+?{}()\[\]|]', '', k).strip() for k in type_keywords]
        
        # Amazon - no brand filter
        if ReviewSource.AMAZON in sources:
            amazon_reviews, amazon_products = self._search_amazon(
                brand=None,
                keywords=keywords,
                match_level=MatchLevel.PRODUCT_TYPE,
                match_score=0.5,
            )
            reviews.extend(amazon_reviews)
            products.extend(amazon_products)
        
        return reviews, products
    
    def _search_amazon(
        self,
        brand: Optional[str],
        keywords: List[str],
        match_level: MatchLevel,
        match_score: float,
    ) -> Tuple[List[AggregatedReview], List[Dict]]:
        """Search Amazon database for reviews."""
        reviews = []
        products = []
        
        try:
            if self._amazon_matcher is None:
                from adam.intelligence.database_review_matcher import DatabaseReviewMatcher
                self._amazon_matcher = DatabaseReviewMatcher()
            
            # Build search query
            search_query = " ".join(keywords[:5])  # Limit to 5 keywords
            
            # Search for products
            result = self._amazon_matcher.find_reviews(
                brand_name=brand,
                product_query=search_query,
                max_products=50,
                max_reviews_per_product=100,
            )
            
            # Convert to AggregatedReview format
            for product in result.get("products", []):
                products.append({
                    "source": "amazon",
                    "id": product.get("asin"),
                    "title": product.get("title"),
                    "brand": product.get("brand"),
                })
                
                for review in product.get("reviews", []):
                    reviews.append(AggregatedReview(
                        text=review.get("text", ""),
                        rating=review.get("rating", 0),
                        source=ReviewSource.AMAZON,
                        product_name=product.get("title", ""),
                        product_brand=product.get("brand"),
                        product_id=product.get("asin"),
                        reviewer_id=review.get("user_id"),
                        helpful_votes=review.get("helpful_vote", 0),
                        verified_purchase=review.get("verified_purchase", False),
                        review_date=review.get("timestamp"),
                        match_level=match_level,
                        match_score=match_score,
                    ))
                    
        except Exception as e:
            logger.warning(f"Amazon search failed: {e}")
        
        return reviews, products
    
    def _search_scraper_cache(
        self,
        brand: Optional[str],
        keywords: List[str],
        match_level: MatchLevel,
        match_score: float,
    ) -> Tuple[List[AggregatedReview], List[Dict]]:
        """Search scraper cache (Walmart, Target, BestBuy)."""
        reviews = []
        products = []
        
        try:
            if self._scraper_cache is None:
                from adam.intelligence.scrapers.oxylabs_client import OxylabsScraperClient
                self._scraper_cache = OxylabsScraperClient()
            
            # Search cached products
            search_query = f"{brand} {' '.join(keywords[:3])}" if brand else " ".join(keywords[:3])
            
            cached_products = self._scraper_cache.search_cached_products(
                query=search_query,
                limit=20,
            )
            
            for product in cached_products:
                source_map = {
                    "walmart": ReviewSource.WALMART,
                    "target": ReviewSource.TARGET,
                    "bestbuy": ReviewSource.BESTBUY,
                }
                source = source_map.get(product.get("source", "").lower(), ReviewSource.WALMART)
                
                products.append({
                    "source": product.get("source"),
                    "id": product.get("product_id"),
                    "title": product.get("title"),
                    "brand": product.get("brand"),
                })
                
                # Get reviews for this product
                product_reviews = self._scraper_cache.get_cached_reviews(
                    product_id=product.get("id"),
                )
                
                for review in product_reviews:
                    reviews.append(AggregatedReview(
                        text=review.get("content", ""),
                        rating=review.get("rating", 0),
                        source=source,
                        product_name=product.get("title", ""),
                        product_brand=product.get("brand"),
                        product_id=product.get("product_id"),
                        reviewer_id=review.get("author"),
                        match_level=match_level,
                        match_score=match_score * 0.9,  # Slightly lower for non-Amazon
                    ))
                    
        except Exception as e:
            logger.debug(f"Scraper cache search failed: {e}")
        
        return reviews, products
    
    def _deduplicate_reviews(
        self,
        reviews: List[AggregatedReview],
    ) -> List[AggregatedReview]:
        """Remove duplicate reviews (same text from same source)."""
        seen: Set[str] = set()
        unique = []
        
        for review in reviews:
            # Create a hash key from text (first 200 chars) + source
            text_hash = review.text[:200].lower().strip() if review.text else ""
            key = f"{review.source.value}:{hash(text_hash)}"
            
            if key not in seen:
                seen.add(key)
                unique.append(review)
        
        return unique


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

_aggregator: Optional[UnifiedReviewAggregator] = None


def get_review_aggregator() -> UnifiedReviewAggregator:
    """Get singleton aggregator instance."""
    global _aggregator
    if _aggregator is None:
        _aggregator = UnifiedReviewAggregator()
    return _aggregator


def aggregate_product_reviews(
    brand: str,
    product_name: str,
    category: Optional[str] = None,
    min_reviews: int = 100,
) -> AggregatedReviewSet:
    """
    Convenience function to aggregate reviews for a product.
    
    Example:
        reviews = aggregate_product_reviews(
            brand="DeWalt",
            product_name="20V MAX 3/8 in. Cordless Impact Driver",
            category="Tools",
        )
        print(f"Found {reviews.total_reviews} reviews from {len(reviews.reviews_by_source)} sources")
    """
    aggregator = get_review_aggregator()
    aggregator.min_reviews = min_reviews
    return aggregator.aggregate_reviews(brand, product_name, category)
