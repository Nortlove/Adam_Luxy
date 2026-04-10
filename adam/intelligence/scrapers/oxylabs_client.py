# =============================================================================
# Oxylabs Integration Client
# Location: adam/intelligence/scrapers/oxylabs_client.py
# =============================================================================

"""
Oxylabs Web Scraping Client - Enterprise-Grade Review Collection

This client replaces our broken direct scrapers with Oxylabs' API, which handles:
- Anti-bot bypass (CAPTCHA, login walls, rate limiting)
- Proxy rotation
- Structured data parsing

Supported Sources:
- Amazon: Products + Reviews (primary)
- Walmart: Products + Reviews

Smart Fallback:
- If URL is not Amazon/Walmart, automatically searches Amazon for the product

Caching:
- All scraped data is cached to avoid re-scraping
- Cache includes raw reviews + timestamps for freshness
"""

import asyncio
import hashlib
import json
import logging
import os
import re
import sqlite3
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse, parse_qs

import aiohttp

logger = logging.getLogger(__name__)


# =============================================================================
# CONFIGURATION
# =============================================================================

OXYLABS_API_URL = "https://realtime.oxylabs.io/v1/queries"
DEFAULT_GEO_LOCATION = "90210"  # Beverly Hills for consistent US results
CACHE_EXPIRY_HOURS = 24 * 7  # Cache for 1 week
MAX_REVIEWS_PER_REQUEST = 20  # Oxylabs returns ~10-15 reviews per product page


class OxylabsSource(str, Enum):
    """Supported Oxylabs data sources."""
    AMAZON_PRODUCT = "amazon_product"
    AMAZON_SEARCH = "amazon_search"
    WALMART_PRODUCT = "universal"  # Walmart uses universal source
    WALMART_SEARCH = "walmart_search"


# =============================================================================
# DATA MODELS
# =============================================================================

@dataclass
class ScrapedReview:
    """A single review from Oxylabs."""
    author: str
    rating: Optional[float]
    content: str
    title: Optional[str] = None
    date: Optional[str] = None
    verified_purchase: bool = False
    helpful_votes: int = 0
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class ScrapedProduct:
    """Product data from Oxylabs."""
    source: str  # amazon, walmart
    product_id: str  # ASIN or Walmart ID
    title: str
    brand: Optional[str]
    price: Optional[float]
    rating: Optional[float]
    reviews_count: int
    reviews: List[ScrapedReview] = field(default_factory=list)
    images: List[str] = field(default_factory=list)
    bullet_points: Optional[str] = None
    description: Optional[str] = None
    category: List[str] = field(default_factory=list)
    url: Optional[str] = None
    scraped_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    def to_dict(self) -> Dict:
        d = asdict(self)
        d['reviews'] = [r.to_dict() if isinstance(r, ScrapedReview) else r for r in self.reviews]
        return d


# =============================================================================
# CACHE LAYER
# =============================================================================

class ReviewCache:
    """
    SQLite-based cache for scraped product data.
    
    Stores:
    - Raw product data + reviews
    - Scraped timestamp
    - Analysis results (if available)
    
    Benefits:
    - Avoid re-scraping same products
    - Enable learning from historical data
    - Track analysis improvements over time
    """
    
    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            # Default to adam-platform/data/review_cache.db
            data_dir = Path(__file__).parent.parent.parent.parent / "data"
            data_dir.mkdir(exist_ok=True)
            db_path = str(data_dir / "review_cache.db")
        
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Initialize the database schema."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Products table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id TEXT PRIMARY KEY,
                source TEXT NOT NULL,
                product_id TEXT NOT NULL,
                title TEXT,
                brand TEXT,
                price REAL,
                rating REAL,
                reviews_count INTEGER,
                data_json TEXT NOT NULL,
                scraped_at TEXT NOT NULL,
                analysis_json TEXT,
                analyzed_at TEXT,
                UNIQUE(source, product_id)
            )
        """)
        
        # Reviews table (for efficient review-level queries)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id TEXT NOT NULL,
                source TEXT NOT NULL,
                author TEXT,
                rating REAL,
                content TEXT NOT NULL,
                title TEXT,
                date TEXT,
                content_hash TEXT UNIQUE,
                FOREIGN KEY (product_id) REFERENCES products(id)
            )
        """)
        
        # Search queries table (to cache search results)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS search_queries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query TEXT NOT NULL,
                source TEXT NOT NULL,
                results_json TEXT NOT NULL,
                searched_at TEXT NOT NULL,
                UNIQUE(query, source)
            )
        """)
        
        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_products_source_id ON products(source, product_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_reviews_product ON reviews(product_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_search_query ON search_queries(query, source)")
        
        conn.commit()
        conn.close()
        logger.info(f"Review cache initialized at {self.db_path}")
    
    def get_product(self, source: str, product_id: str, max_age_hours: int = CACHE_EXPIRY_HOURS) -> Optional[ScrapedProduct]:
        """Get cached product if fresh enough."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT data_json, scraped_at FROM products 
            WHERE source = ? AND product_id = ?
        """, (source, product_id))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            data_json, scraped_at = row
            scraped_time = datetime.fromisoformat(scraped_at)
            if datetime.utcnow() - scraped_time < timedelta(hours=max_age_hours):
                data = json.loads(data_json)
                logger.info(f"Cache hit for {source}:{product_id} (age: {datetime.utcnow() - scraped_time})")
                return self._dict_to_product(data)
            else:
                logger.info(f"Cache stale for {source}:{product_id}")
        
        return None
    
    def save_product(self, product: ScrapedProduct, analysis: Optional[Dict] = None):
        """Save product and its reviews to cache."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        product_data = product.to_dict()
        cache_id = f"{product.source}:{product.product_id}"
        
        # Upsert product
        cursor.execute("""
            INSERT OR REPLACE INTO products 
            (id, source, product_id, title, brand, price, rating, reviews_count, data_json, scraped_at, analysis_json, analyzed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            cache_id,
            product.source,
            product.product_id,
            product.title,
            product.brand,
            product.price,
            product.rating,
            product.reviews_count,
            json.dumps(product_data),
            product.scraped_at,
            json.dumps(analysis) if analysis else None,
            datetime.utcnow().isoformat() if analysis else None,
        ))
        
        # Save individual reviews
        for review in product.reviews:
            content_hash = hashlib.md5(review.content.encode()).hexdigest()
            try:
                cursor.execute("""
                    INSERT OR IGNORE INTO reviews 
                    (product_id, source, author, rating, content, title, date, content_hash)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    cache_id,
                    product.source,
                    review.author,
                    review.rating,
                    review.content,
                    review.title,
                    review.date,
                    content_hash,
                ))
            except sqlite3.IntegrityError:
                pass  # Duplicate review, skip
        
        conn.commit()
        conn.close()
        logger.info(f"Cached product {cache_id} with {len(product.reviews)} reviews")
    
    def save_analysis(self, source: str, product_id: str, analysis: Dict):
        """Update analysis for an existing cached product."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE products 
            SET analysis_json = ?, analyzed_at = ?
            WHERE source = ? AND product_id = ?
        """, (
            json.dumps(analysis),
            datetime.utcnow().isoformat(),
            source,
            product_id,
        ))
        
        conn.commit()
        conn.close()
    
    def get_all_reviews(self, limit: int = 10000) -> List[Dict]:
        """Get all cached reviews for learning/analysis."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT r.author, r.rating, r.content, r.title, r.source, p.brand, p.title as product_title
            FROM reviews r
            JOIN products p ON r.product_id = p.id
            ORDER BY r.id DESC
            LIMIT ?
        """, (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [
            {
                "author": row[0],
                "rating": row[1],
                "content": row[2],
                "title": row[3],
                "source": row[4],
                "brand": row[5],
                "product_title": row[6],
            }
            for row in rows
        ]
    
    def get_stats(self) -> Dict:
        """Get cache statistics."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM products")
        products_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM reviews")
        reviews_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT source, COUNT(*) FROM products GROUP BY source")
        by_source = dict(cursor.fetchall())
        
        conn.close()
        
        return {
            "total_products": products_count,
            "total_reviews": reviews_count,
            "by_source": by_source,
            "cache_path": self.db_path,
        }
    
    def search_cached_products(
        self,
        query: str,
        brand: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict]:
        """
        Search cached products by keyword/brand.
        
        This supports the UnifiedReviewAggregator by searching across all
        cached products from Walmart, Target, BestBuy, etc.
        
        Args:
            query: Search query (keywords)
            brand: Optional brand filter
            limit: Maximum products to return
            
        Returns:
            List of matching products with metadata
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Build query - search in title and brand
        query_lower = f"%{query.lower()}%"
        
        if brand:
            brand_lower = f"%{brand.lower()}%"
            cursor.execute("""
                SELECT id, source, product_id, title, brand, rating, reviews_count, data_json
                FROM products
                WHERE (LOWER(title) LIKE ? OR LOWER(brand) LIKE ?)
                AND LOWER(brand) LIKE ?
                ORDER BY reviews_count DESC
                LIMIT ?
            """, (query_lower, query_lower, brand_lower, limit))
        else:
            cursor.execute("""
                SELECT id, source, product_id, title, brand, rating, reviews_count, data_json
                FROM products
                WHERE LOWER(title) LIKE ? OR LOWER(brand) LIKE ?
                ORDER BY reviews_count DESC
                LIMIT ?
            """, (query_lower, query_lower, limit))
        
        rows = cursor.fetchall()
        conn.close()
        
        results = []
        for row in rows:
            results.append({
                "id": row[0],
                "source": row[1],
                "product_id": row[2],
                "title": row[3],
                "brand": row[4],
                "rating": row[5],
                "reviews_count": row[6],
            })
        
        return results
    
    def get_cached_reviews(
        self,
        product_id: str,
        limit: int = 100,
    ) -> List[Dict]:
        """
        Get cached reviews for a specific product.
        
        Args:
            product_id: The cache ID (source:product_id format) or just product_id
            limit: Maximum reviews to return
            
        Returns:
            List of reviews with content and metadata
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Handle both formats: "walmart:12345" or just "12345"
        if ":" in product_id:
            cache_id = product_id
        else:
            # Search for any product with this ID
            cursor.execute("""
                SELECT id FROM products WHERE product_id = ? LIMIT 1
            """, (product_id,))
            row = cursor.fetchone()
            cache_id = row[0] if row else product_id
        
        cursor.execute("""
            SELECT author, rating, content, title, date, source
            FROM reviews
            WHERE product_id = ?
            LIMIT ?
        """, (cache_id, limit))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [
            {
                "author": row[0],
                "rating": row[1],
                "content": row[2],
                "title": row[3],
                "date": row[4],
                "source": row[5],
            }
            for row in rows
        ]
    
    def search_reviews_by_brand(
        self,
        brand: str,
        keywords: Optional[List[str]] = None,
        limit: int = 500,
    ) -> List[Dict]:
        """
        Search all reviews for a brand, optionally filtered by keywords.
        
        This is useful for aggregating reviews across ALL products from a brand.
        
        Args:
            brand: Brand name to search
            keywords: Optional keywords to filter by (in review content or product title)
            limit: Maximum reviews to return
            
        Returns:
            List of reviews with product context
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        brand_lower = f"%{brand.lower()}%"
        
        if keywords:
            # Build keyword filter
            keyword_conditions = " OR ".join(
                ["LOWER(r.content) LIKE ? OR LOWER(p.title) LIKE ?" for _ in keywords]
            )
            keyword_params = []
            for kw in keywords:
                kw_lower = f"%{kw.lower()}%"
                keyword_params.extend([kw_lower, kw_lower])
            
            cursor.execute(f"""
                SELECT r.author, r.rating, r.content, r.title, r.source, 
                       p.brand, p.title as product_title, p.product_id
                FROM reviews r
                JOIN products p ON r.product_id = p.id
                WHERE LOWER(p.brand) LIKE ?
                AND ({keyword_conditions})
                ORDER BY r.rating DESC
                LIMIT ?
            """, [brand_lower] + keyword_params + [limit])
        else:
            cursor.execute("""
                SELECT r.author, r.rating, r.content, r.title, r.source, 
                       p.brand, p.title as product_title, p.product_id
                FROM reviews r
                JOIN products p ON r.product_id = p.id
                WHERE LOWER(p.brand) LIKE ?
                ORDER BY r.rating DESC
                LIMIT ?
            """, (brand_lower, limit))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [
            {
                "author": row[0],
                "rating": row[1],
                "content": row[2],
                "title": row[3],
                "source": row[4],
                "brand": row[5],
                "product_title": row[6],
                "product_id": row[7],
            }
            for row in rows
        ]
    
    def _dict_to_product(self, data: Dict) -> ScrapedProduct:
        """Convert dict back to ScrapedProduct."""
        reviews = [
            ScrapedReview(**r) if isinstance(r, dict) else r 
            for r in data.get('reviews', [])
        ]
        return ScrapedProduct(
            source=data['source'],
            product_id=data['product_id'],
            title=data['title'],
            brand=data.get('brand'),
            price=data.get('price'),
            rating=data.get('rating'),
            reviews_count=data.get('reviews_count', 0),
            reviews=reviews,
            images=data.get('images', []),
            bullet_points=data.get('bullet_points'),
            description=data.get('description'),
            category=data.get('category', []),
            url=data.get('url'),
            scraped_at=data.get('scraped_at', datetime.utcnow().isoformat()),
        )


# =============================================================================
# URL PARSING UTILITIES
# =============================================================================

def extract_amazon_asin(url: str) -> Optional[str]:
    """Extract ASIN from Amazon URL."""
    # Patterns: /dp/ASIN, /gp/product/ASIN, /product/ASIN
    patterns = [
        r'/dp/([A-Z0-9]{10})',
        r'/gp/product/([A-Z0-9]{10})',
        r'/product/([A-Z0-9]{10})',
        r'amazon\.com.*?/([A-Z0-9]{10})(?:[/?]|$)',
    ]
    for pattern in patterns:
        match = re.search(pattern, url, re.IGNORECASE)
        if match:
            return match.group(1).upper()
    return None


def extract_walmart_id(url: str) -> Optional[str]:
    """Extract product ID from Walmart URL."""
    # Pattern: /ip/product-name/ID
    match = re.search(r'/ip/[^/]+/(\d+)', url)
    if match:
        return match.group(1)
    return None


def identify_source(url: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Identify the source and product ID from a URL.
    
    Returns:
        (source, product_id) or (None, None) if not recognized
    """
    parsed = urlparse(url)
    domain = parsed.netloc.lower()
    
    if 'amazon' in domain:
        asin = extract_amazon_asin(url)
        return ('amazon', asin) if asin else (None, None)
    
    elif 'walmart' in domain:
        product_id = extract_walmart_id(url)
        return ('walmart', product_id) if product_id else (None, None)
    
    # Add more retailers here as needed
    return (None, None)


def extract_product_name_from_url(url: str) -> Optional[str]:
    """
    Try to extract product name from URL for fallback search.
    
    Works for URLs like:
    - /product-name-here/123456
    - /dp/ASIN/product-name
    """
    parsed = urlparse(url)
    path = parsed.path
    
    # Remove common path prefixes
    path = re.sub(r'^/(dp|ip|p|product|item)/', '', path)
    
    # Extract the product name part (usually hyphenated)
    parts = path.split('/')
    for part in parts:
        # Look for hyphenated product names
        if '-' in part and len(part) > 10:
            # Convert hyphens to spaces
            name = part.replace('-', ' ')
            # Remove IDs at the end
            name = re.sub(r'\s+\d+$', '', name)
            return name
    
    return None


# =============================================================================
# OXYLABS CLIENT
# =============================================================================

class OxylabsClient:
    """
    Async client for Oxylabs web scraping API.
    
    Features:
    - Automatic caching to avoid re-scraping
    - Smart fallback: if URL isn't Amazon/Walmart, search Amazon
    - Stores all data for learning
    """
    
    def __init__(
        self,
        username: Optional[str] = None,
        password: Optional[str] = None,
        cache: Optional[ReviewCache] = None,
    ):
        self.username = username or os.environ.get("OXYLABS_USER")
        self.password = password or os.environ.get("OXYLABS_PASSWORD")
        
        if not self.username or not self.password:
            raise ValueError(
                "Oxylabs credentials required. Set OXYLABS_USER and OXYLABS_PASSWORD "
                "environment variables or pass username/password to constructor."
            )
        
        self.cache = cache or ReviewCache()
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None or self._session.closed:
            auth = aiohttp.BasicAuth(self.username, self.password)
            self._session = aiohttp.ClientSession(auth=auth)
        return self._session
    
    async def close(self):
        """Close the aiohttp session."""
        if self._session and not self._session.closed:
            await self._session.close()
    
    async def _make_request(self, payload: Dict) -> Dict:
        """Make request to Oxylabs API."""
        session = await self._get_session()
        
        try:
            async with session.post(
                OXYLABS_API_URL,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=aiohttp.ClientTimeout(total=60),
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"Oxylabs API error {response.status}: {error_text}")
                    raise Exception(f"Oxylabs API error: {response.status}")
                
                return await response.json()
        
        except asyncio.TimeoutError:
            logger.error("Oxylabs API timeout")
            raise
    
    # =========================================================================
    # AMAZON METHODS
    # =========================================================================
    
    async def get_amazon_product(
        self,
        asin: str,
        geo_location: str = DEFAULT_GEO_LOCATION,
        use_cache: bool = True,
    ) -> ScrapedProduct:
        """
        Get Amazon product data including reviews.
        
        Args:
            asin: Amazon Standard Identification Number
            geo_location: US zip code for localized results
            use_cache: Whether to use cached data if available
            
        Returns:
            ScrapedProduct with reviews
        """
        # Check cache first
        if use_cache:
            cached = self.cache.get_product("amazon", asin)
            if cached:
                return cached
        
        # Make API request
        payload = {
            "source": OxylabsSource.AMAZON_PRODUCT.value,
            "query": asin,
            "geo_location": geo_location,
            "parse": True,
        }
        
        logger.info(f"Fetching Amazon product {asin} via Oxylabs")
        response = await self._make_request(payload)
        
        # Parse response
        content = response.get("results", [{}])[0].get("content", {})
        
        if not content or content.get("parse_status_code") == 404:
            raise ValueError(f"Product {asin} not found on Amazon")
        
        # Extract reviews
        raw_reviews = content.get("reviews", [])
        reviews = []
        for r in raw_reviews:
            reviews.append(ScrapedReview(
                author=r.get("author", "Anonymous"),
                rating=r.get("rating"),
                content=r.get("content", ""),
                title=r.get("title"),
                date=r.get("date"),
                verified_purchase=r.get("verified_purchase", False),
                helpful_votes=r.get("helpful_votes", 0),
            ))
        
        product = ScrapedProduct(
            source="amazon",
            product_id=asin,
            title=content.get("title", content.get("product_name", "")),
            brand=content.get("brand"),
            price=content.get("price"),
            rating=content.get("rating"),
            reviews_count=content.get("reviews_count", 0),
            reviews=reviews,
            images=content.get("images", []),
            bullet_points=content.get("bullet_points"),
            description=content.get("description"),
            category=content.get("category", []),
            url=f"https://www.amazon.com/dp/{asin}",
        )
        
        # Cache the result
        self.cache.save_product(product)
        
        logger.info(f"Scraped Amazon product {asin}: {len(reviews)} reviews, rating {product.rating}")
        return product
    
    async def search_amazon(
        self,
        query: str,
        max_results: int = 10,
        geo_location: str = DEFAULT_GEO_LOCATION,
    ) -> List[Dict]:
        """
        Search Amazon for products.
        
        Args:
            query: Search query (product name, brand, etc.)
            max_results: Maximum number of results
            geo_location: US zip code
            
        Returns:
            List of product summaries with ASINs
        """
        payload = {
            "source": OxylabsSource.AMAZON_SEARCH.value,
            "query": query,
            "geo_location": geo_location,
            "parse": True,
        }
        
        logger.info(f"Searching Amazon for: {query}")
        response = await self._make_request(payload)
        
        content = response.get("results", [{}])[0].get("content", {})
        results = content.get("results", {}).get("organic", [])
        
        products = []
        for r in results[:max_results]:
            products.append({
                "asin": r.get("asin"),
                "title": r.get("title"),
                "brand": r.get("brand"),
                "price": r.get("price"),
                "rating": r.get("rating"),
                "reviews_count": r.get("reviews_count"),
                "url": r.get("url"),
            })
        
        logger.info(f"Found {len(products)} Amazon products for '{query}'")
        return products
    
    # =========================================================================
    # WALMART METHODS
    # =========================================================================
    
    async def get_walmart_product(
        self,
        product_id: str,
        use_cache: bool = True,
    ) -> ScrapedProduct:
        """
        Get Walmart product data.
        
        Note: Walmart uses the 'universal' source in Oxylabs.
        """
        # Check cache first
        if use_cache:
            cached = self.cache.get_product("walmart", product_id)
            if cached:
                return cached
        
        url = f"https://www.walmart.com/ip/{product_id}"
        
        payload = {
            "source": "universal",
            "url": url,
            "parse": True,
        }
        
        logger.info(f"Fetching Walmart product {product_id} via Oxylabs")
        response = await self._make_request(payload)
        
        content = response.get("results", [{}])[0].get("content", {})
        
        # Walmart parsing is different - may need adjustment
        product = ScrapedProduct(
            source="walmart",
            product_id=product_id,
            title=content.get("title", ""),
            brand=content.get("brand"),
            price=content.get("price"),
            rating=content.get("rating"),
            reviews_count=content.get("reviews_count", 0),
            reviews=[],  # Walmart reviews may require separate endpoint
            url=url,
        )
        
        self.cache.save_product(product)
        return product
    
    # =========================================================================
    # SMART FALLBACK - THE KEY FEATURE
    # =========================================================================
    
    async def get_product_with_reviews(
        self,
        url: Optional[str] = None,
        product_name: Optional[str] = None,
        brand: Optional[str] = None,
        use_cache: bool = True,
        min_reviews: int = 5,
    ) -> ScrapedProduct:
        """
        Get product with reviews, using smart fallback.
        
        Strategy:
        1. If URL is Amazon/Walmart, scrape directly
        2. If URL is other retailer, search Amazon for the product
        3. If no URL, search Amazon by product name + brand
        
        This ensures we ALWAYS get reviews, even for HomeDepot/Target/etc. URLs.
        
        Args:
            url: Product URL (any retailer)
            product_name: Product name for search fallback
            brand: Brand name for better search results
            use_cache: Use cached data if available
            min_reviews: Minimum reviews needed (triggers broader search if not met)
            
        Returns:
            ScrapedProduct with reviews
        """
        # Try to identify the source from URL
        source, product_id = identify_source(url) if url else (None, None)
        
        # CASE 1: Direct Amazon URL
        if source == "amazon" and product_id:
            try:
                product = await self.get_amazon_product(product_id, use_cache=use_cache)
                if len(product.reviews) >= min_reviews:
                    return product
                logger.info(f"Amazon product {product_id} has only {len(product.reviews)} reviews, searching for more...")
            except Exception as e:
                logger.warning(f"Failed to get Amazon product {product_id}: {e}")
        
        # CASE 2: Direct Walmart URL
        elif source == "walmart" and product_id:
            try:
                product = await self.get_walmart_product(product_id, use_cache=use_cache)
                if len(product.reviews) >= min_reviews:
                    return product
            except Exception as e:
                logger.warning(f"Failed to get Walmart product {product_id}: {e}")
        
        # CASE 3: Fallback - Search Amazon for the product
        # This handles HomeDepot, Target, BestBuy, or any other retailer
        search_query = self._build_search_query(url, product_name, brand)
        
        if not search_query:
            raise ValueError("Cannot determine product to search. Provide URL or product_name.")
        
        logger.info(f"Fallback: Searching Amazon for '{search_query}'")
        
        # Search Amazon
        search_results = await self.search_amazon(search_query, max_results=5)
        
        if not search_results:
            raise ValueError(f"No products found on Amazon for: {search_query}")
        
        # Get the best match (most reviews)
        best_match = max(search_results, key=lambda x: x.get("reviews_count", 0) or 0)
        best_asin = best_match.get("asin")
        
        if not best_asin:
            raise ValueError(f"No valid ASIN found for: {search_query}")
        
        logger.info(f"Best match: {best_match.get('title')[:50]}... ({best_match.get('reviews_count')} reviews)")
        
        # Get full product with reviews
        return await self.get_amazon_product(best_asin, use_cache=use_cache)
    
    def _build_search_query(
        self,
        url: Optional[str],
        product_name: Optional[str],
        brand: Optional[str],
    ) -> Optional[str]:
        """Build search query from available information."""
        parts = []
        
        # Try to extract product name from URL
        if url:
            name_from_url = extract_product_name_from_url(url)
            if name_from_url:
                parts.append(name_from_url)
        
        # Add explicit product name
        if product_name:
            parts.append(product_name)
        
        # Add brand
        if brand:
            parts.insert(0, brand)
        
        if not parts:
            return None
        
        # Combine and clean up
        query = " ".join(parts)
        # Remove duplicates and excessive spaces
        query = " ".join(dict.fromkeys(query.split()))
        return query[:100]  # Limit length
    
    # =========================================================================
    # BULK OPERATIONS (for building review corpus)
    # =========================================================================
    
    async def scrape_product_list(
        self,
        asins: List[str],
        concurrency: int = 3,
        delay_seconds: float = 1.0,
    ) -> List[ScrapedProduct]:
        """
        Scrape multiple Amazon products.
        
        Args:
            asins: List of ASINs to scrape
            concurrency: Max concurrent requests
            delay_seconds: Delay between requests
            
        Returns:
            List of scraped products
        """
        semaphore = asyncio.Semaphore(concurrency)
        results = []
        
        async def scrape_one(asin: str) -> Optional[ScrapedProduct]:
            async with semaphore:
                try:
                    product = await self.get_amazon_product(asin)
                    await asyncio.sleep(delay_seconds)
                    return product
                except Exception as e:
                    logger.error(f"Failed to scrape {asin}: {e}")
                    return None
        
        tasks = [scrape_one(asin) for asin in asins]
        products = await asyncio.gather(*tasks)
        
        return [p for p in products if p is not None]
    
    async def build_review_corpus(
        self,
        search_queries: List[str],
        products_per_query: int = 10,
        concurrency: int = 2,
    ) -> Dict[str, int]:
        """
        Build a corpus of reviews by searching for products.
        
        Args:
            search_queries: List of search terms (e.g., ["dewalt drill", "makita saw"])
            products_per_query: How many products to scrape per query
            concurrency: Max concurrent searches
            
        Returns:
            Stats about what was scraped
        """
        total_products = 0
        total_reviews = 0
        
        for query in search_queries:
            logger.info(f"Building corpus for: {query}")
            
            try:
                # Search
                results = await self.search_amazon(query, max_results=products_per_query)
                
                # Scrape each product
                asins = [r["asin"] for r in results if r.get("asin")]
                products = await self.scrape_product_list(asins, concurrency=concurrency)
                
                total_products += len(products)
                total_reviews += sum(len(p.reviews) for p in products)
                
            except Exception as e:
                logger.error(f"Failed to process query '{query}': {e}")
        
        stats = {
            "queries_processed": len(search_queries),
            "products_scraped": total_products,
            "reviews_collected": total_reviews,
        }
        
        logger.info(f"Corpus build complete: {stats}")
        return stats


# =============================================================================
# SINGLETON ACCESSOR
# =============================================================================

_oxylabs_client: Optional[OxylabsClient] = None


def get_oxylabs_client() -> OxylabsClient:
    """Get or create the singleton OxylabsClient."""
    global _oxylabs_client
    
    if _oxylabs_client is None:
        _oxylabs_client = OxylabsClient()
    
    return _oxylabs_client


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

async def scrape_reviews_for_product(
    url: Optional[str] = None,
    product_name: Optional[str] = None,
    brand: Optional[str] = None,
) -> ScrapedProduct:
    """
    Convenience function to scrape reviews for any product.
    
    Handles:
    - Amazon URLs
    - Walmart URLs
    - Any other retailer URL (falls back to Amazon search)
    - Just a product name + brand
    """
    client = get_oxylabs_client()
    return await client.get_product_with_reviews(
        url=url,
        product_name=product_name,
        brand=brand,
    )
