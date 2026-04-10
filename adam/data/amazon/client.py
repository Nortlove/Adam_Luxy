# =============================================================================
# ADAM Amazon Local Client
# Location: adam/data/amazon/client.py
# =============================================================================

"""
AMAZON LOCAL CLIENT

Provides fast access to the local Amazon review database (1 billion+ reviews).

Architecture:
1. SQLite FTS5 for fast product discovery (amazon_index.db)
2. JSONL files for raw review data
3. Hierarchical matching for flexible queries

This client supports the core data philosophy:
- Customer reviews = psychological gold mine (honest language)
- Brand copy = persuasion attempts (product descriptions)
- Helpful votes = proven persuasive content
"""

import asyncio
import gzip
import json
import logging
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from concurrent.futures import ThreadPoolExecutor

from adam.data.amazon.models import (
    AmazonReview,
    AmazonProduct,
    MatchQuery,
)

logger = logging.getLogger(__name__)


# =============================================================================
# CONFIGURATION
# =============================================================================

# Default paths - can be overridden via environment or constructor
DEFAULT_DB_PATH = Path("/Users/chrisnocera/Sites/adam-platform/amazon/amazon_index.db")
DEFAULT_REVIEWS_DIR = Path("/Users/chrisnocera/Sites/adam-platform/amazon")

# Executor for blocking SQLite operations
_executor = ThreadPoolExecutor(max_workers=4)


# =============================================================================
# AMAZON LOCAL CLIENT
# =============================================================================

class AmazonLocalClient:
    """
    Client for accessing local Amazon review data.
    
    Features:
    - Fast FTS5-based product discovery
    - Hierarchical matching (brand → keywords → price tier)
    - Async interface for integration with async code
    - Preserves helpful_vote for persuasion analysis
    
    Usage:
        client = AmazonLocalClient()
        await client.initialize()
        
        reviews, products = await client.get_reviews_by_brand("Nike", limit=100)
    """
    
    def __init__(
        self,
        db_path: Optional[Path] = None,
        reviews_dir: Optional[Path] = None,
    ):
        """
        Initialize the client.
        
        Args:
            db_path: Path to amazon_index.db (uses default if None)
            reviews_dir: Path to directory containing JSONL review files
        """
        self.db_path = db_path or DEFAULT_DB_PATH
        self.reviews_dir = reviews_dir or DEFAULT_REVIEWS_DIR
        
        self._connection: Optional[sqlite3.Connection] = None
        self._initialized = False
        self._category_files: Dict[str, Path] = {}
        
        logger.info(f"AmazonLocalClient created with db={self.db_path}")
    
    async def initialize(self) -> None:
        """
        Initialize the client.
        
        - Opens database connection
        - Discovers available review files
        """
        if self._initialized:
            return
        
        # Run blocking init in executor
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(_executor, self._init_sync)
        
        self._initialized = True
        logger.info(
            f"AmazonLocalClient initialized: "
            f"db={self.db_path.exists()}, "
            f"categories={len(self._category_files)}"
        )
    
    def _init_sync(self) -> None:
        """Synchronous initialization."""
        # Open database connection
        if self.db_path.exists():
            self._connection = sqlite3.connect(
                str(self.db_path),
                check_same_thread=False,
                timeout=30.0,
            )
            self._connection.row_factory = sqlite3.Row
            logger.info(f"Connected to database: {self.db_path}")
        else:
            logger.warning(f"Database not found: {self.db_path}")
        
        # Discover JSONL review files
        if self.reviews_dir.exists():
            for file in self.reviews_dir.glob("*.jsonl*"):
                # Extract category from filename
                category = file.stem.replace(".jsonl", "").replace("_", " ")
                self._category_files[category.lower()] = file
            
            logger.info(f"Found {len(self._category_files)} review files")
    
    async def close(self) -> None:
        """Close the client."""
        if self._connection:
            self._connection.close()
            self._connection = None
        self._initialized = False
    
    # =========================================================================
    # MAIN QUERY METHODS
    # =========================================================================
    
    async def get_reviews_by_brand(
        self,
        brand: str,
        category: Optional[str] = None,
        limit: int = 100,
    ) -> Tuple[List[AmazonReview], List[AmazonProduct]]:
        """
        Get reviews for a brand.
        
        This is the primary method for brand-based review retrieval.
        Uses FTS5 for fast brand matching.
        
        Args:
            brand: Brand name (e.g., "Lululemon", "Nike")
            category: Optional category filter
            limit: Maximum reviews to return
            
        Returns:
            Tuple of (reviews, products)
        """
        await self.initialize()
        
        if not self._connection:
            logger.warning("No database connection")
            return [], []
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            _executor,
            self._get_reviews_by_brand_sync,
            brand,
            category,
            limit,
        )
    
    def _get_reviews_by_brand_sync(
        self,
        brand: str,
        category: Optional[str],
        limit: int,
    ) -> Tuple[List[AmazonReview], List[AmazonProduct]]:
        """Synchronous brand search."""
        products = []
        reviews = []
        
        try:
            cursor = self._connection.cursor()
            
            # Search for products by brand using FTS5
            # FTS5 is a content-less table, so we join with products table
            try:
                cursor.execute("""
                    SELECT p.parent_asin as asin, p.title, p.brand, 
                           p.main_category, p.avg_rating, p.rating_count
                    FROM products_fts fts
                    JOIN products p ON p.rowid = fts.rowid
                    WHERE fts.brand MATCH ?
                    LIMIT 100
                """, (f'"{brand}"',))
            except sqlite3.OperationalError as e:
                logger.debug(f"FTS query failed: {e}, trying direct query")
                # Fallback - use GLOB which is faster than LIKE for prefix match
                cursor.execute("""
                    SELECT parent_asin as asin, title, brand, main_category, 
                           avg_rating, rating_count
                    FROM products
                    WHERE brand GLOB ?
                    LIMIT 100
                """, (f"*{brand}*",))
            
            rows = cursor.fetchall()
            
            # Convert to products
            asins = set()
            for row in rows:
                product = AmazonProduct(
                    asin=row["asin"],
                    title=row["title"],
                    brand=row["brand"] or brand,
                    main_category=row["main_category"] or "",
                    avg_rating=row["avg_rating"] or 0.0,
                    rating_count=row["rating_count"] or 0,
                )
                products.append(product)
                asins.add(row["asin"])
            
            if not asins:
                logger.debug(f"No products found for brand: {brand}")
                return [], []
            
            # Now get reviews for these ASINs
            # Try the reviews table if it exists
            try:
                placeholders = ",".join(["?" for _ in asins])
                cursor.execute(f"""
                    SELECT asin, rating, title, text, helpful_vote, verified_purchase,
                           timestamp, user_id
                    FROM reviews
                    WHERE asin IN ({placeholders})
                    LIMIT ?
                """, (*asins, limit))
                
                for row in cursor.fetchall():
                    review = AmazonReview(
                        asin=row["asin"],
                        rating=row["rating"] or 3.0,
                        text=row["text"] or "",
                        title=row["title"] or "",
                        helpful_vote=row["helpful_vote"] or 0,
                        verified_purchase=bool(row["verified_purchase"]),
                        timestamp=row["timestamp"],
                        user_id=row["user_id"],
                    )
                    reviews.append(review)
                    
            except sqlite3.OperationalError as e:
                # Reviews table doesn't exist - try JSONL loading if available
                logger.debug(f"Reviews table not found: {e}, trying JSONL")
                if asins and self._category_files:
                    logger.info(f"Loading reviews from JSONL for {len(asins)} ASINs")
                    reviews = self._load_reviews_from_jsonl(asins, limit)
                else:
                    logger.info(f"Reviews not in database - use pre-learning or JSONL processing")
            
            logger.info(f"Found {len(products)} products, {len(reviews)} reviews for {brand}")
            return reviews, products
            
        except Exception as e:
            logger.error(f"Brand search failed: {e}")
            return [], []
    
    async def get_reviews_for_product(
        self,
        brand: str,
        product_name: str,
        category: Optional[str] = None,
        price: Optional[float] = None,
        limit: int = 100,
    ) -> List[AmazonReview]:
        """
        Get reviews for a specific product using hierarchical matching.
        
        Matching hierarchy:
        1. Brand + Full Title Match (best)
        2. Brand + Key Phrases
        3. Brand + Keywords
        4. Brand Only
        5. Keywords + Price Tier (fallback)
        
        Args:
            brand: Brand name
            product_name: Product name or description
            category: Optional category filter
            price: Optional price for tier matching
            limit: Maximum reviews
            
        Returns:
            List of matching reviews
        """
        await self.initialize()
        
        # Build query
        query = MatchQuery(
            brand=brand,
            product_name=product_name,
            category=category,
            price=price,
            max_results=limit,
        ).extract_search_terms()
        
        # Get reviews
        reviews, _ = await self.get_reviews_by_brand(
            brand=brand,
            category=category,
            limit=limit * 2,  # Get more for filtering
        )
        
        if not reviews:
            return []
        
        # Score and filter reviews by relevance
        scored_reviews = []
        for review in reviews:
            score = self._score_review_relevance(review, query)
            if score > 0:
                scored_reviews.append((score, review))
        
        # Sort by score and return top N
        scored_reviews.sort(key=lambda x: -x[0])
        return [review for _, review in scored_reviews[:limit]]
    
    def _score_review_relevance(
        self,
        review: AmazonReview,
        query: MatchQuery,
    ) -> float:
        """
        Score a review's relevance to a query.
        
        Considers:
        - Product title match
        - Keyword overlap
        - Helpful vote boost (persuasive reviews get bonus)
        """
        score = 0.0
        
        # Check product title
        title_lower = (review.product_title or "").lower()
        
        # Full title match
        if query.product_name.lower() in title_lower:
            score += 1.0
        
        # Key phrase matches
        for phrase in query.key_phrases:
            if phrase in title_lower:
                score += 0.5
        
        # Keyword matches
        for keyword in query.keywords:
            if keyword in title_lower:
                score += 0.2
        
        # Brand match (required)
        brand_lower = (review.product_brand or "").lower()
        if query.brand.lower() not in brand_lower:
            return 0.0  # No match
        
        # Helpful vote bonus (persuasive reviews are more valuable)
        if review.helpful_vote > 0:
            # Log scale bonus for helpful votes
            import math
            helpful_bonus = 0.1 * math.log(1 + review.helpful_vote)
            score += min(helpful_bonus, 0.5)  # Cap at 0.5 bonus
        
        # Verified purchase bonus
        if review.verified_purchase:
            score += 0.1
        
        return score
    
    def _load_reviews_from_jsonl(
        self,
        asins: Set[str],
        limit: int,
    ) -> List[AmazonReview]:
        """
        Load reviews from JSONL files for given ASINs.
        
        This is slower but works when reviews aren't in the database.
        """
        reviews = []
        
        for category, filepath in self._category_files.items():
            if len(reviews) >= limit:
                break
            
            try:
                if filepath.suffix == ".gz":
                    with gzip.open(filepath, 'rt', encoding='utf-8') as f:
                        for line in f:
                            if len(reviews) >= limit:
                                break
                            self._process_jsonl_line(line, asins, reviews)
                else:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        for line in f:
                            if len(reviews) >= limit:
                                break
                            self._process_jsonl_line(line, asins, reviews)
                            
            except Exception as e:
                logger.error(f"Error reading {filepath}: {e}")
        
        return reviews
    
    def _process_jsonl_line(
        self,
        line: str,
        asins: Set[str],
        reviews: List[AmazonReview],
    ) -> None:
        """Process a single JSONL line."""
        try:
            data = json.loads(line)
            asin = data.get("asin") or data.get("parent_asin")
            
            if asin and asin in asins:
                review = AmazonReview(
                    asin=asin,
                    rating=float(data.get("rating", data.get("overall", 3))),
                    text=data.get("text", data.get("reviewText", "")),
                    title=data.get("title", data.get("summary", "")),
                    helpful_vote=data.get("helpful_vote", 0) or 0,
                    verified_purchase=data.get("verified_purchase", False),
                    timestamp=data.get("timestamp"),
                    user_id=data.get("user_id", data.get("reviewerID")),
                )
                reviews.append(review)
                
        except (json.JSONDecodeError, KeyError, ValueError):
            pass
    
    # =========================================================================
    # UTILITY METHODS
    # =========================================================================
    
    async def get_brand_categories(
        self,
        brand: str,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        Get available categories for a brand.
        
        Used by the demo UI for faceted search.
        """
        await self.initialize()
        
        if not self._connection:
            return []
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            _executor,
            self._get_brand_categories_sync,
            brand,
            limit,
        )
    
    def _get_brand_categories_sync(
        self,
        brand: str,
        limit: int,
    ) -> List[Dict[str, Any]]:
        """Synchronous category search."""
        try:
            cursor = self._connection.cursor()
            
            # Use FTS5 join for fast category lookup
            cursor.execute("""
                SELECT p.main_category, COUNT(*) as count, AVG(p.avg_rating) as avg_rating
                FROM products_fts fts
                JOIN products p ON p.rowid = fts.rowid
                WHERE fts.brand MATCH ?
                GROUP BY p.main_category
                ORDER BY count DESC
                LIMIT ?
            """, (f'"{brand}"', limit))
            
            categories = []
            for row in cursor.fetchall():
                if row["main_category"]:
                    categories.append({
                        "category": row["main_category"],
                        "product_count": row["count"],
                        "avg_rating": round(row["avg_rating"] or 0, 2),
                    })
            
            return categories
            
        except Exception as e:
            logger.error(f"Category search failed: {e}")
            return []
    
    async def get_high_helpful_reviews(
        self,
        brand: str,
        min_helpful_votes: int = 10,
        limit: int = 50,
    ) -> List[AmazonReview]:
        """
        Get reviews with high helpful votes.
        
        These reviews contain language patterns that resonated with
        other customers - valuable for persuasion learning.
        
        Args:
            brand: Brand to search
            min_helpful_votes: Minimum helpful votes threshold
            limit: Maximum reviews
            
        Returns:
            List of high-helpful-vote reviews
        """
        reviews, _ = await self.get_reviews_by_brand(brand, limit=limit * 3)
        
        # Filter and sort by helpful votes
        helpful_reviews = [
            r for r in reviews 
            if r.helpful_vote >= min_helpful_votes
        ]
        helpful_reviews.sort(key=lambda r: -r.helpful_vote)
        
        return helpful_reviews[:limit]
    
    async def stream_raw_reviews_for_brand(
        self,
        brand: str,
        category: Optional[str] = None,
        limit: int = 1000,
    ) -> List[AmazonReview]:
        """
        Stream raw reviews directly from JSONL files.
        
        Phase 6: Enable raw review access for fresh psychological profiles.
        
        This bypasses the database for cases where:
        - Reviews aren't indexed
        - We need fresh analysis
        - We want to access the full review corpus
        
        Args:
            brand: Brand name to search (case-insensitive)
            category: Optional category filter
            limit: Maximum reviews to return
            
        Returns:
            List of AmazonReview objects
        """
        await self.initialize()
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            _executor,
            self._stream_raw_reviews_sync,
            brand,
            category,
            limit,
        )
    
    def _stream_raw_reviews_sync(
        self,
        brand: str,
        category: Optional[str],
        limit: int,
    ) -> List[AmazonReview]:
        """Synchronous streaming from JSONL files."""
        reviews = []
        brand_lower = brand.lower()
        category_lower = category.lower() if category else None
        
        # Determine which files to scan
        files_to_scan = []
        if category_lower and category_lower in self._category_files:
            files_to_scan = [self._category_files[category_lower]]
        else:
            files_to_scan = list(self._category_files.values())
        
        for filepath in files_to_scan:
            if len(reviews) >= limit:
                break
            
            try:
                if filepath.suffix == ".gz":
                    opener = lambda p: gzip.open(p, 'rt', encoding='utf-8')
                else:
                    opener = lambda p: open(p, 'r', encoding='utf-8')
                
                with opener(filepath) as f:
                    for line_num, line in enumerate(f):
                        if len(reviews) >= limit:
                            break
                        
                        # Skip every Nth line for sampling large files
                        if limit < 100 and line_num % 10 != 0:
                            continue
                        
                        review = self._parse_jsonl_for_brand(line, brand_lower)
                        if review:
                            reviews.append(review)
                            
            except Exception as e:
                logger.error(f"Error streaming from {filepath}: {e}")
        
        logger.info(
            f"Streamed {len(reviews)} raw reviews for brand '{brand}' "
            f"from {len(files_to_scan)} files"
        )
        
        return reviews
    
    def _parse_jsonl_for_brand(
        self,
        line: str,
        brand_lower: str,
    ) -> Optional[AmazonReview]:
        """Parse a JSONL line and check if it matches the brand."""
        try:
            data = json.loads(line)
            
            # Check if this review mentions the brand
            # Look in text, title, and brand field
            review_brand = (data.get("brand") or "").lower()
            review_title = (data.get("title") or data.get("summary") or "").lower()
            review_text = (data.get("text") or data.get("reviewText") or "").lower()
            
            # Match if brand is in brand field, title, or prominent in text
            if not (brand_lower in review_brand or 
                    brand_lower in review_title or
                    (brand_lower in review_text[:200])):  # Check first 200 chars of text
                return None
            
            return AmazonReview(
                asin=data.get("asin") or data.get("parent_asin") or "",
                rating=float(data.get("rating", data.get("overall", 3))),
                text=data.get("text") or data.get("reviewText") or "",
                title=data.get("title") or data.get("summary") or "",
                helpful_vote=data.get("helpful_vote", 0) or 0,
                verified_purchase=data.get("verified_purchase", False),
                timestamp=data.get("timestamp"),
                user_id=data.get("user_id", data.get("reviewerID")),
            )
            
        except (json.JSONDecodeError, KeyError, ValueError):
            return None
    
    async def get_category_sample(
        self,
        category: str,
        sample_size: int = 100,
    ) -> List[AmazonReview]:
        """
        Get a random sample of reviews from a category.
        
        Useful for building baseline psychological profiles.
        """
        await self.initialize()
        
        category_lower = category.lower()
        if category_lower not in self._category_files:
            logger.warning(f"Category not found: {category}")
            return []
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            _executor,
            self._sample_category_sync,
            category_lower,
            sample_size,
        )
    
    def _sample_category_sync(
        self,
        category_lower: str,
        sample_size: int,
    ) -> List[AmazonReview]:
        """Sample reviews from a category file."""
        filepath = self._category_files[category_lower]
        reviews = []
        
        try:
            # Count lines (approximately)
            line_count = 0
            if filepath.suffix == ".gz":
                with gzip.open(filepath, 'rt', encoding='utf-8') as f:
                    for _ in f:
                        line_count += 1
                        if line_count > 100000:  # Sample from first 100k
                            break
            else:
                with open(filepath, 'r', encoding='utf-8') as f:
                    for _ in f:
                        line_count += 1
                        if line_count > 100000:
                            break
            
            # Calculate step size for uniform sampling
            import random
            step = max(1, line_count // sample_size)
            
            # Sample reviews
            if filepath.suffix == ".gz":
                opener = lambda p: gzip.open(p, 'rt', encoding='utf-8')
            else:
                opener = lambda p: open(p, 'r', encoding='utf-8')
            
            with opener(filepath) as f:
                for i, line in enumerate(f):
                    if len(reviews) >= sample_size:
                        break
                    
                    # Sample every Nth line with some randomness
                    if i % step == 0 or random.random() < 0.01:
                        try:
                            data = json.loads(line)
                            review = AmazonReview(
                                asin=data.get("asin") or data.get("parent_asin") or "",
                                rating=float(data.get("rating", data.get("overall", 3))),
                                text=data.get("text") or data.get("reviewText") or "",
                                title=data.get("title") or data.get("summary") or "",
                                helpful_vote=data.get("helpful_vote", 0) or 0,
                                verified_purchase=data.get("verified_purchase", False),
                                timestamp=data.get("timestamp"),
                                user_id=data.get("user_id", data.get("reviewerID")),
                            )
                            reviews.append(review)
                        except (json.JSONDecodeError, KeyError, ValueError):
                            pass
                            
        except Exception as e:
            logger.error(f"Error sampling from {filepath}: {e}")
        
        return reviews
    
    def get_stats(self) -> Dict[str, Any]:
        """Get client statistics."""
        return {
            "initialized": self._initialized,
            "db_exists": self.db_path.exists(),
            "reviews_dir_exists": self.reviews_dir.exists(),
            "category_files": len(self._category_files),
            "categories": list(self._category_files.keys())[:10],
            "raw_access_available": len(self._category_files) > 0,
        }


# =============================================================================
# SINGLETON FACTORY
# =============================================================================

_client: Optional[AmazonLocalClient] = None


def get_amazon_client(
    db_path: Optional[Path] = None,
    reviews_dir: Optional[Path] = None,
) -> AmazonLocalClient:
    """
    Get or create the Amazon client singleton.
    
    Args:
        db_path: Optional database path (uses default if None)
        reviews_dir: Optional reviews directory (uses default if None)
        
    Returns:
        AmazonLocalClient instance
    """
    global _client
    
    if _client is None:
        _client = AmazonLocalClient(
            db_path=db_path,
            reviews_dir=reviews_dir,
        )
    
    return _client


def reset_amazon_client() -> None:
    """Reset the Amazon client singleton."""
    global _client
    if _client:
        asyncio.create_task(_client.close())
    _client = None
