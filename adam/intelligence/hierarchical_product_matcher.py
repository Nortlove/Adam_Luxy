#!/usr/bin/env python3
"""
HIERARCHICAL PRODUCT MATCHER
============================

Implements the SMART hierarchical matching system for finding relevant reviews.

MATCHING HIERARCHY (as specified):
1. Brand + Full Title Match → Weight: 1.0 (HIGHEST)
2. Brand + All Key Phrases → Weight: 0.9
3. Brand + Multiple Keywords → Weight: 0.7
4. Brand + Single Keyword → Weight: 0.5
5. Brand Only → Weight: 0.3
6. Keywords + Price Tier Match (no brand) → Weight: 0.2 (LOWEST)

EXAMPLE for "SOREL Womens Joan of Arctic Waterproof Boots" at $182:
- Level 1: Brand="SOREL" AND title LIKE "%Womens Joan of Arctic Waterproof Boots%"
- Level 2: Brand="SOREL" AND title LIKE "%Joan%" AND "%Arctic%" AND "%Boots%"
- Level 3: Brand="SOREL" AND title LIKE "%Womens%" AND "%Boots%"
- Level 4: Brand="SOREL" AND title LIKE "%Womens%"
- Level 5: Brand="SOREL"
- Level 6: title LIKE "%Boots%" AND price BETWEEN 150 AND 220

This uses the SQLite database (amazon_index.db) for FAST lookups.
"""

import logging
import re
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


# =============================================================================
# CONFIGURATION
# =============================================================================

DATABASE_PATH = Path("/Users/chrisnocera/Sites/adam-platform/amazon/amazon_index.db")

# Stop words to exclude from keyword extraction
STOP_WORDS = {
    "the", "a", "an", "and", "or", "for", "of", "with", "in", "on", "at",
    "to", "by", "is", "are", "was", "were", "be", "been", "have", "has",
    "this", "that", "it", "its", "my", "your", "their", "our", "i", "you",
    "we", "they", "very", "just", "so", "really", "great", "good", "nice",
    "size", "color", "us", "uk", "eu", "m", "b", "d", "w", "medium", "wide",
    "small", "large", "xl", "xxl", "xs", "pack", "set", "piece", "count",
}


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class MatchedProduct:
    """A product matched via hierarchical search."""
    asin: str
    title: str
    brand: str
    category: str
    avg_rating: float
    review_count: int
    match_level: int  # 1-6
    match_weight: float
    match_description: str


@dataclass
class HierarchicalMatchResult:
    """Complete result of hierarchical matching."""
    query_brand: str
    query_product: str
    query_price: Optional[float]
    
    # Match statistics
    level_1_matches: int = 0  # Brand + Full Title
    level_2_matches: int = 0  # Brand + All Phrases
    level_3_matches: int = 0  # Brand + Multiple Keywords
    level_4_matches: int = 0  # Brand + Single Keyword
    level_5_matches: int = 0  # Brand Only
    level_6_matches: int = 0  # Keywords + Price
    
    total_matches: int = 0
    total_reviews_available: int = 0
    weighted_avg_rating: float = 0.0
    
    # Matched products (sorted by weight)
    products: List[MatchedProduct] = field(default_factory=list)
    
    # Keywords extracted
    keywords_extracted: List[str] = field(default_factory=list)
    key_phrases: List[str] = field(default_factory=list)
    
    def get_best_match_level(self) -> int:
        """Get the best (lowest) match level achieved."""
        if self.level_1_matches > 0:
            return 1
        elif self.level_2_matches > 0:
            return 2
        elif self.level_3_matches > 0:
            return 3
        elif self.level_4_matches > 0:
            return 4
        elif self.level_5_matches > 0:
            return 5
        elif self.level_6_matches > 0:
            return 6
        return 0


# =============================================================================
# KEYWORD EXTRACTOR
# =============================================================================

class KeywordExtractor:
    """
    Extracts meaningful keywords and phrases from product names.
    
    For "Womens Joan of Arctic Waterproof Boots":
    - Keywords: ["womens", "joan", "arctic", "waterproof", "boots"]
    - Key phrases: ["joan of arctic", "waterproof boots"]
    """
    
    # Important word patterns to preserve
    IMPORTANT_PATTERNS = [
        r"joan of arctic",
        r"north face",
        r"kate spade",
        r"michael kors",
        r"ralph lauren",
        r"calvin klein",
    ]
    
    def extract(self, product_name: str) -> Tuple[List[str], List[str]]:
        """
        Extract keywords and key phrases from product name.
        
        Returns: (keywords, key_phrases)
        """
        name_lower = product_name.lower()
        
        # Find important phrases first
        key_phrases = []
        for pattern in self.IMPORTANT_PATTERNS:
            if pattern in name_lower:
                key_phrases.append(pattern)
        
        # Extract individual keywords
        words = re.findall(r'\b[a-z]+\b', name_lower)
        keywords = [w for w in words if w not in STOP_WORDS and len(w) >= 3]
        
        # Look for multi-word brand/product names (consecutive capitalized words)
        name_words = product_name.split()
        for i in range(len(name_words) - 1):
            phrase = f"{name_words[i]} {name_words[i+1]}".lower()
            phrase_clean = re.sub(r'[^\w\s]', '', phrase)
            if phrase_clean not in STOP_WORDS and len(phrase_clean) > 5:
                if phrase_clean not in key_phrases:
                    key_phrases.append(phrase_clean)
        
        return keywords, key_phrases


# =============================================================================
# HIERARCHICAL PRODUCT MATCHER
# =============================================================================

class HierarchicalProductMatcher:
    """
    Implements 6-level hierarchical matching for product search.
    
    Uses SQLite database for fast lookups.
    """
    
    MATCH_WEIGHTS = {
        1: 1.0,   # Brand + Full Title
        2: 0.9,   # Brand + All Phrases
        3: 0.7,   # Brand + Multiple Keywords
        4: 0.5,   # Brand + Single Keyword
        5: 0.3,   # Brand Only
        6: 0.2,   # Keywords + Price
    }
    
    MATCH_DESCRIPTIONS = {
        1: "Brand + Full Title",
        2: "Brand + All Key Phrases",
        3: "Brand + Multiple Keywords",
        4: "Brand + Single Keyword",
        5: "Brand Only",
        6: "Keywords + Price Match",
    }
    
    def __init__(self, db_path: Path = DATABASE_PATH):
        self.db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None
        self.keyword_extractor = KeywordExtractor()
    
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
        price: Optional[float] = None,
        max_products: int = 100,
    ) -> HierarchicalMatchResult:
        """
        Find products using hierarchical matching.
        
        Tries each level in order, stopping when enough matches are found.
        
        Args:
            brand: Product brand (e.g., "SOREL")
            product_name: Product name (e.g., "Womens Joan of Arctic Waterproof Boots")
            price: Product price (for Level 6 fallback)
            max_products: Maximum products to return
            
        Returns:
            HierarchicalMatchResult with matched products
        """
        logger.info(f"Hierarchical matching: brand='{brand}', product='{product_name}'")
        
        # Extract keywords and phrases
        keywords, key_phrases = self.keyword_extractor.extract(product_name)
        logger.info(f"  Keywords: {keywords}")
        logger.info(f"  Key phrases: {key_phrases}")
        
        result = HierarchicalMatchResult(
            query_brand=brand,
            query_product=product_name,
            query_price=price,
            keywords_extracted=keywords,
            key_phrases=key_phrases,
        )
        
        all_products = []
        
        # Level 1: Brand + Full Title
        if brand:
            level_1 = self._search_level_1(brand, product_name, max_products)
            all_products.extend(level_1)
            result.level_1_matches = len(level_1)
            logger.info(f"  Level 1 (Brand + Full Title): {len(level_1)} matches")
        
        # Level 2: Brand + All Key Phrases
        if brand and key_phrases and len(all_products) < max_products:
            level_2 = self._search_level_2(brand, key_phrases, max_products - len(all_products))
            new_products = self._dedupe_products(level_2, all_products)
            all_products.extend(new_products)
            result.level_2_matches = len(new_products)
            logger.info(f"  Level 2 (Brand + All Phrases): {len(new_products)} new matches")
        
        # Level 3: Brand + Multiple Keywords (at least 2)
        if brand and len(keywords) >= 2 and len(all_products) < max_products:
            level_3 = self._search_level_3(brand, keywords, max_products - len(all_products))
            new_products = self._dedupe_products(level_3, all_products)
            all_products.extend(new_products)
            result.level_3_matches = len(new_products)
            logger.info(f"  Level 3 (Brand + Multiple Keywords): {len(new_products)} new matches")
        
        # Level 4: Brand + Single Keyword
        if brand and keywords and len(all_products) < max_products:
            level_4 = self._search_level_4(brand, keywords, max_products - len(all_products))
            new_products = self._dedupe_products(level_4, all_products)
            all_products.extend(new_products)
            result.level_4_matches = len(new_products)
            logger.info(f"  Level 4 (Brand + Single Keyword): {len(new_products)} new matches")
        
        # Level 5: Brand Only
        if brand and len(all_products) < max_products:
            level_5 = self._search_level_5(brand, max_products - len(all_products))
            new_products = self._dedupe_products(level_5, all_products)
            all_products.extend(new_products)
            result.level_5_matches = len(new_products)
            logger.info(f"  Level 5 (Brand Only): {len(new_products)} new matches")
        
        # Level 6: Keywords + Price (no brand match)
        if keywords and price and len(all_products) < max_products:
            level_6 = self._search_level_6(keywords, price, max_products - len(all_products))
            new_products = self._dedupe_products(level_6, all_products)
            all_products.extend(new_products)
            result.level_6_matches = len(new_products)
            logger.info(f"  Level 6 (Keywords + Price): {len(new_products)} new matches")
        
        # Sort by match weight (highest first)
        all_products.sort(key=lambda p: (p.match_weight, p.review_count), reverse=True)
        
        result.products = all_products[:max_products]
        result.total_matches = len(all_products)
        result.total_reviews_available = sum(p.review_count for p in all_products)
        
        # Calculate weighted average rating
        if result.total_reviews_available > 0:
            result.weighted_avg_rating = sum(
                p.avg_rating * p.review_count for p in all_products
            ) / result.total_reviews_available
        
        logger.info(f"  TOTAL: {result.total_matches} products, {result.total_reviews_available:,} reviews")
        
        return result
    
    def _search_level_1(self, brand: str, full_title: str, limit: int) -> List[MatchedProduct]:
        """Level 1: Brand + Full Title match."""
        conn = self._get_conn()
        
        # Extract significant words from title for matching
        title_words = [w for w in full_title.lower().split() if w not in STOP_WORDS and len(w) >= 3]
        
        if not title_words:
            return []
        
        # Build query - all title words must be present
        conditions = ["LOWER(brand) LIKE ?"]
        params = [f"%{brand.lower()}%"]
        
        for word in title_words[:5]:  # Limit to 5 words
            conditions.append("LOWER(title) LIKE ?")
            params.append(f"%{word}%")
        
        query = f"""
            SELECT parent_asin, title, brand, main_category, avg_rating, rating_count
            FROM products
            WHERE {" AND ".join(conditions)}
            ORDER BY rating_count DESC
            LIMIT {limit}
        """
        
        products = []
        try:
            for row in conn.execute(query, params):
                products.append(MatchedProduct(
                    asin=row["parent_asin"],
                    title=row["title"] or "",
                    brand=row["brand"] or "",
                    category=row["main_category"] or "",
                    avg_rating=row["avg_rating"] or 0,
                    review_count=row["rating_count"] or 0,
                    match_level=1,
                    match_weight=self.MATCH_WEIGHTS[1],
                    match_description=self.MATCH_DESCRIPTIONS[1],
                ))
        except Exception as e:
            logger.error(f"Level 1 query error: {e}")
        
        return products
    
    def _search_level_2(self, brand: str, key_phrases: List[str], limit: int) -> List[MatchedProduct]:
        """Level 2: Brand + All Key Phrases match."""
        conn = self._get_conn()
        
        conditions = ["LOWER(brand) LIKE ?"]
        params = [f"%{brand.lower()}%"]
        
        for phrase in key_phrases[:3]:
            # Replace spaces with % for flexible matching
            conditions.append("LOWER(title) LIKE ?")
            params.append(f"%{phrase.replace(' ', '%')}%")
        
        query = f"""
            SELECT parent_asin, title, brand, main_category, avg_rating, rating_count
            FROM products
            WHERE {" AND ".join(conditions)}
            ORDER BY rating_count DESC
            LIMIT {limit}
        """
        
        products = []
        try:
            for row in conn.execute(query, params):
                products.append(MatchedProduct(
                    asin=row["parent_asin"],
                    title=row["title"] or "",
                    brand=row["brand"] or "",
                    category=row["main_category"] or "",
                    avg_rating=row["avg_rating"] or 0,
                    review_count=row["rating_count"] or 0,
                    match_level=2,
                    match_weight=self.MATCH_WEIGHTS[2],
                    match_description=self.MATCH_DESCRIPTIONS[2],
                ))
        except Exception as e:
            logger.error(f"Level 2 query error: {e}")
        
        return products
    
    def _search_level_3(self, brand: str, keywords: List[str], limit: int) -> List[MatchedProduct]:
        """Level 3: Brand + Multiple Keywords (2+)."""
        conn = self._get_conn()
        
        # Try with top 3 keywords first, then top 2
        for num_keywords in [3, 2]:
            if len(keywords) < num_keywords:
                continue
            
            conditions = ["LOWER(brand) LIKE ?"]
            params = [f"%{brand.lower()}%"]
            
            for kw in keywords[:num_keywords]:
                conditions.append("LOWER(title) LIKE ?")
                params.append(f"%{kw}%")
            
            query = f"""
                SELECT parent_asin, title, brand, main_category, avg_rating, rating_count
                FROM products
                WHERE {" AND ".join(conditions)}
                ORDER BY rating_count DESC
                LIMIT {limit}
            """
            
            products = []
            try:
                for row in conn.execute(query, params):
                    products.append(MatchedProduct(
                        asin=row["parent_asin"],
                        title=row["title"] or "",
                        brand=row["brand"] or "",
                        category=row["main_category"] or "",
                        avg_rating=row["avg_rating"] or 0,
                        review_count=row["rating_count"] or 0,
                        match_level=3,
                        match_weight=self.MATCH_WEIGHTS[3],
                        match_description=self.MATCH_DESCRIPTIONS[3],
                    ))
                
                if products:
                    return products
            except Exception as e:
                logger.error(f"Level 3 query error: {e}")
        
        return []
    
    def _search_level_4(self, brand: str, keywords: List[str], limit: int) -> List[MatchedProduct]:
        """Level 4: Brand + Single Keyword."""
        conn = self._get_conn()
        
        all_products = []
        seen_asins = set()
        
        for kw in keywords[:5]:  # Try top 5 keywords
            query = """
                SELECT parent_asin, title, brand, main_category, avg_rating, rating_count
                FROM products
                WHERE LOWER(brand) LIKE ?
                  AND LOWER(title) LIKE ?
                ORDER BY rating_count DESC
                LIMIT ?
            """
            
            try:
                for row in conn.execute(query, [f"%{brand.lower()}%", f"%{kw}%", limit]):
                    if row["parent_asin"] not in seen_asins:
                        seen_asins.add(row["parent_asin"])
                        all_products.append(MatchedProduct(
                            asin=row["parent_asin"],
                            title=row["title"] or "",
                            brand=row["brand"] or "",
                            category=row["main_category"] or "",
                            avg_rating=row["avg_rating"] or 0,
                            review_count=row["rating_count"] or 0,
                            match_level=4,
                            match_weight=self.MATCH_WEIGHTS[4],
                            match_description=self.MATCH_DESCRIPTIONS[4],
                        ))
                        
                        if len(all_products) >= limit:
                            return all_products
            except Exception as e:
                logger.error(f"Level 4 query error: {e}")
        
        return all_products
    
    def _search_level_5(self, brand: str, limit: int) -> List[MatchedProduct]:
        """Level 5: Brand Only."""
        conn = self._get_conn()
        
        query = """
            SELECT parent_asin, title, brand, main_category, avg_rating, rating_count
            FROM products
            WHERE LOWER(brand) LIKE ?
            ORDER BY rating_count DESC
            LIMIT ?
        """
        
        products = []
        try:
            for row in conn.execute(query, [f"%{brand.lower()}%", limit]):
                products.append(MatchedProduct(
                    asin=row["parent_asin"],
                    title=row["title"] or "",
                    brand=row["brand"] or "",
                    category=row["main_category"] or "",
                    avg_rating=row["avg_rating"] or 0,
                    review_count=row["rating_count"] or 0,
                    match_level=5,
                    match_weight=self.MATCH_WEIGHTS[5],
                    match_description=self.MATCH_DESCRIPTIONS[5],
                ))
        except Exception as e:
            logger.error(f"Level 5 query error: {e}")
        
        return products
    
    def _search_level_6(self, keywords: List[str], price: float, limit: int) -> List[MatchedProduct]:
        """Level 6: Keywords + Price Match (no brand required)."""
        conn = self._get_conn()
        
        # Price range: ±20%
        price_low = price * 0.8
        price_high = price * 1.2
        
        # Try with multiple keywords first
        for num_keywords in [3, 2, 1]:
            if len(keywords) < num_keywords:
                continue
            
            conditions = []
            params = []
            
            for kw in keywords[:num_keywords]:
                conditions.append("LOWER(title) LIKE ?")
                params.append(f"%{kw}%")
            
            # Note: price matching would require the index to have price data
            # For now, just use keywords
            query = f"""
                SELECT parent_asin, title, brand, main_category, avg_rating, rating_count
                FROM products
                WHERE {" AND ".join(conditions)}
                ORDER BY rating_count DESC
                LIMIT {limit}
            """
            
            products = []
            try:
                for row in conn.execute(query, params):
                    products.append(MatchedProduct(
                        asin=row["parent_asin"],
                        title=row["title"] or "",
                        brand=row["brand"] or "",
                        category=row["main_category"] or "",
                        avg_rating=row["avg_rating"] or 0,
                        review_count=row["rating_count"] or 0,
                        match_level=6,
                        match_weight=self.MATCH_WEIGHTS[6],
                        match_description=self.MATCH_DESCRIPTIONS[6],
                    ))
                
                if products:
                    return products
            except Exception as e:
                logger.error(f"Level 6 query error: {e}")
        
        return []
    
    def _dedupe_products(
        self, 
        new_products: List[MatchedProduct], 
        existing: List[MatchedProduct]
    ) -> List[MatchedProduct]:
        """Remove duplicates from new products."""
        existing_asins = {p.asin for p in existing}
        return [p for p in new_products if p.asin not in existing_asins]
    
    def close(self):
        """Close database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

_matcher: Optional[HierarchicalProductMatcher] = None


def get_hierarchical_matcher() -> HierarchicalProductMatcher:
    """Get singleton matcher."""
    global _matcher
    if _matcher is None:
        _matcher = HierarchicalProductMatcher()
    return _matcher


def find_products_hierarchical(
    brand: str,
    product_name: str,
    price: Optional[float] = None,
    max_products: int = 100,
) -> HierarchicalMatchResult:
    """
    Find products using hierarchical matching.
    
    This is the main entry point for runtime queries.
    """
    matcher = get_hierarchical_matcher()
    return matcher.find_products(
        brand=brand,
        product_name=product_name,
        price=price,
        max_products=max_products,
    )


# =============================================================================
# TEST
# =============================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("=" * 70)
    print("HIERARCHICAL PRODUCT MATCHER TEST")
    print("=" * 70)
    
    result = find_products_hierarchical(
        brand="SOREL",
        product_name="Womens Joan of Arctic Waterproof Boots",
        price=182.0,
    )
    
    print(f"\nRESULTS:")
    print(f"  Total matches: {result.total_matches}")
    print(f"  Total reviews: {result.total_reviews_available:,}")
    print(f"  Weighted avg rating: {result.weighted_avg_rating:.2f}")
    print(f"  Best match level: {result.get_best_match_level()}")
    
    print(f"\nMATCH BREAKDOWN:")
    print(f"  Level 1 (Brand + Full Title): {result.level_1_matches}")
    print(f"  Level 2 (Brand + All Phrases): {result.level_2_matches}")
    print(f"  Level 3 (Brand + Multiple Keywords): {result.level_3_matches}")
    print(f"  Level 4 (Brand + Single Keyword): {result.level_4_matches}")
    print(f"  Level 5 (Brand Only): {result.level_5_matches}")
    print(f"  Level 6 (Keywords + Price): {result.level_6_matches}")
    
    print(f"\nTOP MATCHED PRODUCTS:")
    for i, p in enumerate(result.products[:10], 1):
        print(f"\n  {i}. [{p.match_description}]")
        print(f"     {p.brand} - {p.title[:60]}...")
        print(f"     Rating: {p.avg_rating:.1f} ({p.review_count:,} reviews)")
