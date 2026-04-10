#!/usr/bin/env python3
"""
ASIN-BASED REVIEW MATCHER
=========================

The CORRECT way to match Amazon reviews: via ASIN.

Amazon reviews are linked to products via ASIN (Amazon Standard Identification Number).
The metadata files contain product info (brand, title, price) indexed by ASIN.
The review files contain reviews indexed by ASIN.

MATCHING FLOW:
1. Search METADATA for products matching brand/title → get ASINs
2. Load REVIEWS and filter to those ASINs
3. Return exact product reviews

This is MUCH more accurate than text-based searching.
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

AMAZON_DATA_DIR = Path("/Volumes/Sped/Nocera Models/Review Data/Amazon")

# Stop words for title matching
STOP_WORDS = {
    "the", "a", "an", "and", "or", "for", "of", "with", "in", "on", "at",
    "to", "by", "is", "are", "was", "were", "be", "been", "have", "has",
    "size", "color", "us", "uk", "eu", "m", "b", "d", "w", "medium", "wide",
}


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class ProductMatch:
    """A product found in metadata."""
    asin: str
    title: str
    brand: str
    price: Optional[float] = None
    match_score: float = 0.0
    match_type: str = ""  # "exact_title", "brand_keywords", "brand_only"


@dataclass
class ReviewMatch:
    """A review matched via ASIN."""
    asin: str
    review_id: str
    rating: float
    title: str
    text: str
    helpful_vote: int = 0
    verified_purchase: bool = False
    timestamp: Optional[int] = None
    product_title: str = ""
    product_brand: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "asin": self.asin,
            "rating": self.rating,
            "title": self.title,
            "text": self.text[:500] + "..." if len(self.text) > 500 else self.text,
            "helpful_vote": self.helpful_vote,
            "verified_purchase": self.verified_purchase,
            "product_title": self.product_title,
            "product_brand": self.product_brand,
        }


@dataclass
class ASINMatchResult:
    """Complete result of ASIN-based matching."""
    query_brand: str
    query_product: str
    products_found: int
    reviews_found: int
    products: List[ProductMatch]
    reviews: List[ReviewMatch]
    match_quality: str  # "exact", "brand_keywords", "brand_only", "no_match"
    
    def get_avg_rating(self) -> float:
        if not self.reviews:
            return 0.0
        return sum(r.rating for r in self.reviews) / len(self.reviews)
    
    def get_rating_distribution(self) -> Dict[int, int]:
        dist = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        for r in self.reviews:
            rating = int(round(r.rating))
            if 1 <= rating <= 5:
                dist[rating] += 1
        return dist


# =============================================================================
# ASIN REVIEW MATCHER
# =============================================================================

class ASINReviewMatcher:
    """
    ASIN-based review matcher.
    
    Uses the proper Amazon data model:
    - Metadata files: product info indexed by ASIN
    - Review files: reviews indexed by ASIN
    """
    
    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = data_dir or AMAZON_DATA_DIR
        self._metadata_cache: Dict[str, Dict[str, Dict]] = {}  # category -> asin -> product info
        self._asin_to_reviews: Dict[str, List[Dict]] = {}  # asin -> reviews (for loaded data)
    
    def find_reviews(
        self,
        brand: str,
        product_name: str,
        price: Optional[float] = None,
        category: Optional[str] = None,
        max_reviews: int = 500,
    ) -> ASINMatchResult:
        """
        Find reviews for a product using ASIN-based matching.
        
        Args:
            brand: Product brand (e.g., "SOREL")
            product_name: Product name (e.g., "Joan of Arctic Boots")
            price: Product price (for filtering)
            category: Category to search (e.g., "Clothing_Shoes_and_Jewelry")
            max_reviews: Maximum reviews to return
            
        Returns:
            ASINMatchResult with matched products and reviews
        """
        logger.info(f"ASIN matching: brand='{brand}', product='{product_name}'")
        
        # Determine category
        if not category:
            category = self._infer_category(product_name)
        
        # Step 1: Search metadata for matching products → get ASINs
        products = self._search_metadata(
            category=category,
            brand=brand,
            product_name=product_name,
            price=price,
        )
        
        if not products:
            logger.warning(f"No products found for {brand} - {product_name}")
            return ASINMatchResult(
                query_brand=brand,
                query_product=product_name,
                products_found=0,
                reviews_found=0,
                products=[],
                reviews=[],
                match_quality="no_match",
            )
        
        # Get ASINs from matched products
        asins = {p.asin for p in products}
        logger.info(f"Found {len(products)} matching products with {len(asins)} unique ASINs")
        
        # Step 2: Load reviews for those ASINs
        reviews = self._load_reviews_for_asins(
            category=category,
            asins=asins,
            max_reviews=max_reviews,
            products={p.asin: p for p in products},
        )
        
        logger.info(f"Found {len(reviews)} reviews for matched products")
        
        # Determine match quality
        if products[0].match_type == "exact_title":
            match_quality = "exact"
        elif products[0].match_type == "brand_keywords":
            match_quality = "brand_keywords"
        else:
            match_quality = "brand_only"
        
        return ASINMatchResult(
            query_brand=brand,
            query_product=product_name,
            products_found=len(products),
            reviews_found=len(reviews),
            products=products,
            reviews=reviews,
            match_quality=match_quality,
        )
    
    def _search_metadata(
        self,
        category: str,
        brand: str,
        product_name: str,
        price: Optional[float] = None,
    ) -> List[ProductMatch]:
        """
        Search metadata file for matching products.
        
        MATCHING HIERARCHY:
        1. Brand + Title keywords (highest score)
        2. Brand only (medium score)
        3. Title keywords only (lower score)
        """
        products = []
        brand_lower = brand.lower().strip()
        
        # Extract keywords from product name
        keywords = self._extract_keywords(product_name)
        logger.info(f"Searching metadata with keywords: {keywords}")
        
        # Load metadata
        metadata = self._load_metadata(category)
        
        for asin, info in metadata.items():
            product_brand = (info.get("brand", "") or info.get("store", "") or "").lower()
            product_title = (info.get("title", "") or "").lower()
            product_price = info.get("price")
            
            match_score = 0.0
            match_type = ""
            
            # Check brand match
            brand_match = brand_lower and (
                brand_lower in product_brand or
                brand_lower in product_title
            )
            
            if brand_match:
                # Brand matches - now check title
                # Count keyword matches
                keyword_matches = sum(1 for kw in keywords if kw in product_title)
                keyword_ratio = keyword_matches / len(keywords) if keywords else 0
                
                if keyword_ratio >= 0.6:  # 60%+ keywords match
                    match_score = 0.9 + (keyword_ratio * 0.1)  # 0.9 - 1.0
                    match_type = "exact_title"
                elif keyword_ratio >= 0.3:  # 30%+ keywords
                    match_score = 0.6 + (keyword_ratio * 0.3)  # 0.6 - 0.9
                    match_type = "brand_keywords"
                else:
                    match_score = 0.4
                    match_type = "brand_only"
                
                # Parse price
                parsed_price = None
                if product_price:
                    try:
                        if isinstance(product_price, str):
                            # Remove $ and parse
                            parsed_price = float(product_price.replace("$", "").replace(",", "").split("-")[0].strip())
                        else:
                            parsed_price = float(product_price)
                    except (ValueError, TypeError):
                        pass
                
                products.append(ProductMatch(
                    asin=asin,
                    title=info.get("title", ""),
                    brand=info.get("brand", "") or info.get("store", ""),
                    price=parsed_price,
                    match_score=match_score,
                    match_type=match_type,
                ))
        
        # Sort by match score
        products.sort(key=lambda p: p.match_score, reverse=True)
        
        # Limit to top matches
        return products[:100]
    
    def _load_reviews_for_asins(
        self,
        category: str,
        asins: Set[str],
        max_reviews: int,
        products: Dict[str, ProductMatch],
    ) -> List[ReviewMatch]:
        """Load reviews for specific ASINs."""
        reviews = []
        
        # Try to load review file
        review_paths = [
            self.data_dir / f"{category}.jsonl",
            self.data_dir / f"{category}.jsonl.gz",
        ]
        
        for filepath in review_paths:
            if not filepath.exists():
                continue
            
            logger.info(f"Loading reviews from {filepath}")
            
            try:
                opener = gzip.open if filepath.suffix == '.gz' else open
                reviews_checked = 0
                
                with opener(filepath, 'rt', encoding='utf-8') as f:
                    for line in f:
                        reviews_checked += 1
                        
                        # Progress logging
                        if reviews_checked % 1000000 == 0:
                            logger.info(f"  Checked {reviews_checked:,} reviews, found {len(reviews)}")
                        
                        try:
                            review = json.loads(line)
                            
                            # Check if this review is for one of our ASINs
                            review_asin = review.get("parent_asin") or review.get("asin")
                            
                            if review_asin in asins:
                                product = products.get(review_asin, ProductMatch(asin=review_asin, title="", brand=""))
                                
                                reviews.append(ReviewMatch(
                                    asin=review_asin,
                                    review_id=review.get("user_id", ""),
                                    rating=review.get("rating", 0) or review.get("overall", 0),
                                    title=review.get("title", "") or review.get("summary", ""),
                                    text=review.get("text", "") or review.get("reviewText", ""),
                                    helpful_vote=review.get("helpful_vote", 0),
                                    verified_purchase=review.get("verified_purchase", False),
                                    timestamp=review.get("timestamp"),
                                    product_title=product.title,
                                    product_brand=product.brand,
                                ))
                                
                                if len(reviews) >= max_reviews:
                                    logger.info(f"Reached max reviews ({max_reviews})")
                                    return reviews
                        
                        except json.JSONDecodeError:
                            continue
                
                logger.info(f"Finished scanning {reviews_checked:,} reviews, found {len(reviews)}")
                break
                
            except Exception as e:
                logger.error(f"Error loading reviews from {filepath}: {e}")
                continue
        
        return reviews
    
    def _load_metadata(self, category: str) -> Dict[str, Dict]:
        """Load metadata file for a category."""
        if category in self._metadata_cache:
            return self._metadata_cache[category]
        
        metadata = {}
        
        meta_paths = [
            self.data_dir / f"meta_{category}.jsonl",
            self.data_dir / f"meta_{category}.jsonl.gz",
        ]
        
        for filepath in meta_paths:
            if not filepath.exists():
                continue
            
            logger.info(f"Loading metadata from {filepath}")
            
            try:
                opener = gzip.open if filepath.suffix == '.gz' else open
                
                with opener(filepath, 'rt', encoding='utf-8') as f:
                    for line in f:
                        try:
                            item = json.loads(line)
                            asin = item.get("parent_asin") or item.get("asin")
                            if asin:
                                metadata[asin] = item
                        except json.JSONDecodeError:
                            continue
                
                logger.info(f"Loaded {len(metadata):,} products from metadata")
                break
                
            except Exception as e:
                logger.error(f"Error loading metadata: {e}")
        
        self._metadata_cache[category] = metadata
        return metadata
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract meaningful keywords from product name."""
        # Clean and split
        text_clean = re.sub(r'[^\w\s-]', ' ', text.lower())
        words = text_clean.split()
        
        # Filter
        keywords = [
            w for w in words
            if w not in STOP_WORDS and len(w) > 2
        ]
        
        return keywords
    
    def _infer_category(self, product_name: str) -> str:
        """Infer category from product name."""
        name_lower = product_name.lower()
        
        if any(w in name_lower for w in ["boot", "shoe", "sneaker", "sandal", "heel"]):
            return "Clothing_Shoes_and_Jewelry"
        elif any(w in name_lower for w in ["phone", "tablet", "laptop", "headphone"]):
            return "Electronics"
        elif any(w in name_lower for w in ["kitchen", "cookware", "pan", "pot"]):
            return "Home_and_Kitchen"
        elif any(w in name_lower for w in ["tool", "drill", "saw"]):
            return "Tools_and_Home_Improvement"
        else:
            return "Clothing_Shoes_and_Jewelry"  # Default


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

_matcher: Optional[ASINReviewMatcher] = None


def get_asin_matcher() -> ASINReviewMatcher:
    """Get singleton matcher."""
    global _matcher
    if _matcher is None:
        _matcher = ASINReviewMatcher()
    return _matcher


def find_product_reviews_by_asin(
    brand: str,
    product_name: str,
    price: Optional[float] = None,
    category: Optional[str] = None,
    max_reviews: int = 500,
) -> ASINMatchResult:
    """
    Find reviews using ASIN-based matching.
    
    This is the CORRECT way to match Amazon reviews.
    """
    matcher = get_asin_matcher()
    return matcher.find_reviews(
        brand=brand,
        product_name=product_name,
        price=price,
        category=category,
        max_reviews=max_reviews,
    )


# =============================================================================
# TEST
# =============================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("=" * 70)
    print("ASIN-BASED REVIEW MATCHER TEST")
    print("=" * 70)
    
    result = find_product_reviews_by_asin(
        brand="SOREL",
        product_name="Joan of Arctic Boots",
        price=182.0,
        category="Clothing_Shoes_and_Jewelry",
        max_reviews=100,
    )
    
    print(f"\nRESULTS:")
    print(f"  Products found: {result.products_found}")
    print(f"  Reviews found: {result.reviews_found}")
    print(f"  Match quality: {result.match_quality}")
    print(f"  Average rating: {result.get_avg_rating():.2f}")
    print(f"  Rating distribution: {result.get_rating_distribution()}")
    
    print(f"\nTOP MATCHED PRODUCTS:")
    for i, p in enumerate(result.products[:5], 1):
        print(f"  {i}. [{p.match_type}] {p.brand} - {p.title[:60]}...")
        print(f"     ASIN: {p.asin}, Score: {p.match_score:.2f}")
    
    print(f"\nSAMPLE REVIEWS:")
    for i, r in enumerate(result.reviews[:5], 1):
        print(f"\n  {i}. Rating: {r.rating} - {r.title}")
        print(f"     Product: {r.product_title[:50]}...")
        print(f"     Review: {r.text[:150]}...")
