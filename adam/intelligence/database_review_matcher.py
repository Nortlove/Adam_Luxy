#!/usr/bin/env python3
"""
DATABASE-BACKED REVIEW MATCHER
==============================

Uses the pre-built SQLite database (amazon_index.db) for FAST product lookups,
then fetches reviews from the JSONL files only for matched ASINs.

The database has:
- Products indexed by ASIN with brand, title, category, avg_rating, rating_count
- Full-text search (FTS5) for fast product discovery

This is the CORRECT and FAST way to match reviews.
"""

import json
import logging
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


# =============================================================================
# CONFIGURATION
# =============================================================================

DATABASE_PATH = Path("/Users/chrisnocera/Sites/adam-platform/amazon/amazon_index.db")
REVIEWS_PATH = Path("/Users/chrisnocera/Sites/adam-platform/amazon/Clothing_Shoes_and_Jewelry.jsonl")


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class Product:
    """Product from database."""
    asin: str
    title: str
    brand: str
    category: str
    avg_rating: float
    rating_count: int
    match_score: float = 1.0


@dataclass
class Review:
    """Review matched by ASIN."""
    asin: str
    rating: float
    title: str
    text: str
    helpful_vote: int = 0
    verified_purchase: bool = False
    product_title: str = ""
    product_brand: str = ""


@dataclass
class MatchResult:
    """Result of database-backed matching."""
    query_brand: str
    query_product: str
    products_found: int
    total_reviews_available: int
    reviews_loaded: int
    avg_rating: float
    products: List[Product]
    reviews: List[Review]
    
    def get_rating_distribution(self) -> Dict[int, int]:
        dist = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        for r in self.reviews:
            rating = int(round(r.rating))
            if 1 <= rating <= 5:
                dist[rating] += 1
        return dist


# =============================================================================
# DATABASE REVIEW MATCHER
# =============================================================================

class DatabaseReviewMatcher:
    """
    Fast database-backed review matcher.
    
    Uses SQLite with FTS5 for product discovery, then loads
    reviews only for matched ASINs.
    """
    
    def __init__(
        self,
        db_path: Path = DATABASE_PATH,
        reviews_path: Path = REVIEWS_PATH,
    ):
        self.db_path = db_path
        self.reviews_path = reviews_path
        self._conn: Optional[sqlite3.Connection] = None
    
    def _get_conn(self) -> sqlite3.Connection:
        """Get database connection."""
        if self._conn is None:
            self._conn = sqlite3.connect(str(self.db_path))
            self._conn.row_factory = sqlite3.Row
        return self._conn
    
    def find_products(
        self,
        brand: str,
        product_name: str,
        max_products: int = 50,
    ) -> List[Product]:
        """
        Find products matching brand and product name.
        
        Uses full-text search for fast lookup.
        """
        conn = self._get_conn()
        products = []
        
        # First try: Brand + keywords from title
        brand_lower = brand.lower().strip()
        keywords = [w for w in product_name.lower().split() if len(w) > 2]
        
        # Query 1: Exact brand + title keywords match
        query = """
            SELECT parent_asin, title, brand, main_category, avg_rating, rating_count
            FROM products
            WHERE LOWER(brand) LIKE ?
            AND (
        """
        params = [f"%{brand_lower}%"]
        
        # Add keyword conditions
        keyword_conditions = []
        for kw in keywords[:5]:  # Limit keywords
            keyword_conditions.append("LOWER(title) LIKE ?")
            params.append(f"%{kw}%")
        
        if keyword_conditions:
            query += " AND ".join(keyword_conditions)
        else:
            query += "1=1"
        
        query += f") ORDER BY rating_count DESC LIMIT {max_products}"
        
        try:
            cursor = conn.execute(query, params)
            for row in cursor:
                products.append(Product(
                    asin=row["parent_asin"],
                    title=row["title"] or "",
                    brand=row["brand"] or "",
                    category=row["main_category"] or "",
                    avg_rating=row["avg_rating"] or 0.0,
                    rating_count=row["rating_count"] or 0,
                    match_score=1.0,
                ))
        except Exception as e:
            logger.error(f"Database query error: {e}")
        
        # If few results, try brand-only query
        if len(products) < 10:
            query2 = """
                SELECT parent_asin, title, brand, main_category, avg_rating, rating_count
                FROM products
                WHERE LOWER(brand) LIKE ?
                ORDER BY rating_count DESC
                LIMIT ?
            """
            try:
                cursor = conn.execute(query2, [f"%{brand_lower}%", max_products - len(products)])
                seen_asins = {p.asin for p in products}
                for row in cursor:
                    if row["parent_asin"] not in seen_asins:
                        products.append(Product(
                            asin=row["parent_asin"],
                            title=row["title"] or "",
                            brand=row["brand"] or "",
                            category=row["main_category"] or "",
                            avg_rating=row["avg_rating"] or 0.0,
                            rating_count=row["rating_count"] or 0,
                            match_score=0.5,
                        ))
            except Exception as e:
                logger.error(f"Brand-only query error: {e}")
        
        logger.info(f"Found {len(products)} products for {brand}")
        return products
    
    def load_reviews_for_asins(
        self,
        asins: Set[str],
        products: Dict[str, Product],
        max_reviews: int = 500,
    ) -> List[Review]:
        """
        Load reviews for specific ASINs from the JSONL file.
        
        This is the slow part - we have to scan the file.
        For production, we'd want a review index too.
        """
        if not self.reviews_path.exists():
            logger.error(f"Reviews file not found: {self.reviews_path}")
            return []
        
        reviews = []
        reviews_checked = 0
        
        logger.info(f"Loading reviews for {len(asins)} ASINs from {self.reviews_path}")
        
        try:
            with open(self.reviews_path, 'r', encoding='utf-8') as f:
                for line in f:
                    reviews_checked += 1
                    
                    if reviews_checked % 5000000 == 0:
                        logger.info(f"  Checked {reviews_checked:,} reviews, found {len(reviews)}")
                    
                    try:
                        review = json.loads(line)
                        asin = review.get("parent_asin") or review.get("asin")
                        
                        if asin in asins:
                            product = products.get(asin)
                            
                            reviews.append(Review(
                                asin=asin,
                                rating=review.get("rating", 0),
                                title=review.get("title", ""),
                                text=review.get("text", ""),
                                helpful_vote=review.get("helpful_vote", 0),
                                verified_purchase=review.get("verified_purchase", False),
                                product_title=product.title if product else "",
                                product_brand=product.brand if product else "",
                            ))
                            
                            if len(reviews) >= max_reviews:
                                logger.info(f"Reached max reviews ({max_reviews})")
                                return reviews
                    
                    except json.JSONDecodeError:
                        continue
            
            logger.info(f"Finished: checked {reviews_checked:,}, found {len(reviews)}")
            
        except Exception as e:
            logger.error(f"Error loading reviews: {e}")
        
        return reviews
    
    def find_reviews(
        self,
        brand: str,
        product_name: str,
        max_products: int = 50,
        max_reviews: int = 500,
        load_reviews: bool = True,
    ) -> MatchResult:
        """
        Find products and their reviews.
        
        Args:
            brand: Product brand
            product_name: Product name
            max_products: Max products to match
            max_reviews: Max reviews to load
            load_reviews: Whether to load actual reviews (slow)
            
        Returns:
            MatchResult with products and reviews
        """
        # Step 1: Find products in database (FAST)
        products = self.find_products(brand, product_name, max_products)
        
        if not products:
            return MatchResult(
                query_brand=brand,
                query_product=product_name,
                products_found=0,
                total_reviews_available=0,
                reviews_loaded=0,
                avg_rating=0.0,
                products=[],
                reviews=[],
            )
        
        # Calculate total reviews available
        total_reviews = sum(p.rating_count for p in products)
        
        # Calculate weighted average rating
        if total_reviews > 0:
            weighted_rating = sum(p.avg_rating * p.rating_count for p in products) / total_reviews
        else:
            weighted_rating = sum(p.avg_rating for p in products) / len(products) if products else 0
        
        # Step 2: Optionally load reviews (SLOW)
        reviews = []
        if load_reviews:
            asins = {p.asin for p in products}
            product_dict = {p.asin: p for p in products}
            reviews = self.load_reviews_for_asins(asins, product_dict, max_reviews)
        
        return MatchResult(
            query_brand=brand,
            query_product=product_name,
            products_found=len(products),
            total_reviews_available=total_reviews,
            reviews_loaded=len(reviews),
            avg_rating=weighted_rating,
            products=products,
            reviews=reviews,
        )


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

_matcher: Optional[DatabaseReviewMatcher] = None


def get_db_matcher() -> DatabaseReviewMatcher:
    """Get singleton matcher."""
    global _matcher
    if _matcher is None:
        _matcher = DatabaseReviewMatcher()
    return _matcher


def find_reviews_fast(
    brand: str,
    product_name: str,
    max_products: int = 50,
    load_reviews: bool = False,
) -> MatchResult:
    """
    FAST product lookup using database.
    
    Set load_reviews=False for instant results (product info only).
    Set load_reviews=True to also fetch actual review text (slower).
    """
    matcher = get_db_matcher()
    return matcher.find_reviews(
        brand=brand,
        product_name=product_name,
        max_products=max_products,
        load_reviews=load_reviews,
    )


# =============================================================================
# TEST
# =============================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("=" * 70)
    print("DATABASE REVIEW MATCHER TEST")
    print("=" * 70)
    
    # Test 1: Fast product lookup (no review loading)
    print("\n--- TEST 1: Fast Product Lookup (no reviews) ---")
    result = find_reviews_fast(
        brand="SOREL",
        product_name="Joan of Arctic Boots",
        load_reviews=False,
    )
    
    print(f"\nProducts found: {result.products_found}")
    print(f"Total reviews available: {result.total_reviews_available:,}")
    print(f"Average rating: {result.avg_rating:.2f}")
    
    print("\nTop products by review count:")
    for p in sorted(result.products, key=lambda x: x.rating_count, reverse=True)[:10]:
        print(f"  [{p.asin}] {p.title[:60]}...")
        print(f"    Rating: {p.avg_rating:.1f} ({p.rating_count:,} reviews)")
    
    # Test 2: With review loading (slower)
    print("\n--- TEST 2: With Review Loading (slower) ---")
    print("Loading actual reviews... (this may take a while)")
    result2 = find_reviews_fast(
        brand="SOREL",
        product_name="Joan of Arctic Boots",
        max_products=10,  # Fewer products
        load_reviews=True,
    )
    
    print(f"\nReviews loaded: {result2.reviews_loaded}")
    print(f"Rating distribution: {result2.get_rating_distribution()}")
    
    if result2.reviews:
        print("\nSample reviews:")
        for r in result2.reviews[:5]:
            print(f"\n  Rating: {r.rating} - {r.title}")
            print(f"  Product: {r.product_title[:50]}...")
            print(f"  Review: {r.text[:150]}...")
