# =============================================================================
# Amazon Metadata Indexer
# Location: adam/data/amazon/indexer.py
# =============================================================================

"""
Builds and manages a searchable index of Amazon product metadata.

The index allows fast lookups by brand and product name without
loading the massive JSONL files into memory.

Index Structure (SQLite):
- products: parent_asin, title, brand, store, main_category, avg_rating, rating_count
- Full-text search on title and brand

Usage:
    indexer = MetadataIndexer("/path/to/amazon")
    indexer.build_index()  # One-time build
    
    # Search
    products = indexer.search(brand="Apple", product_name="iPhone", limit=10)
"""

import json
import logging
import os
import re
import sqlite3
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Tuple

from adam.data.amazon.models import AmazonProduct, ProductSearchResult

logger = logging.getLogger(__name__)


# Category mapping for search
CATEGORY_FILE_MAP = {
    # Consumer categories
    "beauty": ["All_Beauty", "Beauty_and_Personal_Care"],
    "fashion": ["Amazon_Fashion", "Clothing_Shoes_and_Jewelry"],
    "electronics": ["Digital_Music"],  # Electronics not in our set
    "books": ["Books", "Kindle_Store"],
    "media": ["Books", "Digital_Music", "Kindle_Store", "Magazine_Subscriptions", "Movies_and_TV"],
    "food": ["Grocery_and_Gourmet_Food"],
    "music": ["Digital_Music"],
    "movies": ["Movies_and_TV"],
    "clothing": ["Amazon_Fashion", "Clothing_Shoes_and_Jewelry"],
}


class MetadataIndexer:
    """
    Indexes Amazon product metadata for fast search.
    
    Uses SQLite for storage and FTS5 for full-text search.
    """
    
    def __init__(
        self,
        data_dir: str,
        index_path: Optional[str] = None,
    ):
        """
        Initialize the indexer.
        
        Args:
            data_dir: Path to Amazon data directory containing JSONL files
            index_path: Path to SQLite index file (default: data_dir/amazon_index.db)
        """
        self.data_dir = Path(data_dir)
        self.index_path = Path(index_path) if index_path else self.data_dir / "amazon_index.db"
        self._conn: Optional[sqlite3.Connection] = None
    
    @property
    def conn(self) -> sqlite3.Connection:
        """Get or create database connection."""
        if self._conn is None:
            self._conn = sqlite3.connect(str(self.index_path))
            self._conn.row_factory = sqlite3.Row
            # Enable FTS5
            self._conn.execute("PRAGMA journal_mode=WAL")
        return self._conn
    
    def close(self):
        """Close database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None
    
    @property
    def index_exists(self) -> bool:
        """Check if index has been built."""
        if not self.index_path.exists():
            return False
        try:
            cursor = self.conn.execute(
                "SELECT COUNT(*) FROM products"
            )
            count = cursor.fetchone()[0]
            return count > 0
        except sqlite3.OperationalError:
            return False
    
    def get_available_categories(self) -> List[str]:
        """Get list of categories with metadata files."""
        categories = []
        for path in self.data_dir.glob("meta_*.jsonl"):
            category = path.stem.replace("meta_", "")
            categories.append(category)
        return sorted(categories)
    
    def build_index(
        self,
        categories: Optional[List[str]] = None,
        limit_per_category: Optional[int] = None,
        force_rebuild: bool = False,
    ) -> Dict[str, Any]:
        """
        Build the search index from metadata files.
        
        Args:
            categories: List of categories to index (None = all)
            limit_per_category: Limit products per category (for testing)
            force_rebuild: Rebuild even if index exists
            
        Returns:
            Statistics about the indexing process
        """
        if self.index_exists and not force_rebuild:
            logger.info("Index already exists. Use force_rebuild=True to rebuild.")
            return {"status": "skipped", "reason": "index_exists"}
        
        logger.info(f"Building Amazon metadata index at {self.index_path}")
        
        # Create tables
        self._create_tables()
        
        stats = {
            "categories": [],
            "total_products": 0,
            "total_with_brand": 0,
        }
        
        available = self.get_available_categories()
        to_process = categories if categories else available
        
        for category in to_process:
            if category not in available:
                logger.warning(f"Category {category} not found, skipping")
                continue
            
            meta_path = self.data_dir / f"meta_{category}.jsonl"
            if not meta_path.exists():
                continue
            
            logger.info(f"Indexing {category}...")
            count = 0
            brand_count = 0
            
            batch = []
            batch_size = 10000
            
            for product_data in self._stream_metadata(meta_path):
                product = AmazonProduct.from_jsonl(product_data)
                
                batch.append((
                    product.parent_asin,
                    product.title,
                    product.effective_brand,
                    product.store or "",
                    product.main_category or category,
                    product.average_rating,
                    product.rating_number,
                    category,
                ))
                
                if product.effective_brand:
                    brand_count += 1
                
                count += 1
                
                if limit_per_category and count >= limit_per_category:
                    break
                
                if len(batch) >= batch_size:
                    self._insert_batch(batch)
                    # Commit every 100K products within category to prevent huge transactions
                    if count % 100000 == 0:
                        self.conn.commit()
                    batch = []
                    logger.info(f"  → {count:,} products indexed...")
                    # Force flush output
                    import sys
                    sys.stdout.flush()
            
            # Insert remaining
            if batch:
                self._insert_batch(batch)
            
            # COMMIT AFTER EACH CATEGORY to prevent data loss
            self.conn.commit()
            
            stats["categories"].append({
                "category": category,
                "products": count,
                "with_brand": brand_count,
            })
            stats["total_products"] += count
            stats["total_with_brand"] += brand_count
            
            logger.info(f"  ✓ {count:,} products ({brand_count:,} with brand) - COMMITTED")
            
            # Force flush output
            import sys
            sys.stdout.flush()
            sys.stderr.flush()
        
        # Build FTS index
        logger.info("Building full-text search index...")
        self._build_fts_index()
        
        self.conn.commit()
        logger.info(f"Index complete: {stats['total_products']:,} products")
        
        return stats
    
    def _create_tables(self):
        """Create database tables."""
        self.conn.executescript("""
            DROP TABLE IF EXISTS products;
            DROP TABLE IF EXISTS products_fts;
            
            CREATE TABLE products (
                parent_asin TEXT PRIMARY KEY,
                title TEXT,
                brand TEXT,
                store TEXT,
                main_category TEXT,
                avg_rating REAL,
                rating_count INTEGER,
                source_category TEXT
            );
            
            CREATE INDEX idx_brand ON products(brand);
            CREATE INDEX idx_category ON products(source_category);
            CREATE INDEX idx_main_category ON products(main_category);
        """)
    
    def _build_fts_index(self):
        """Build FTS5 full-text search index."""
        self.conn.executescript("""
            CREATE VIRTUAL TABLE IF NOT EXISTS products_fts USING fts5(
                parent_asin,
                title,
                brand,
                content=products,
                content_rowid=rowid
            );
            
            INSERT INTO products_fts(products_fts) VALUES('rebuild');
        """)
    
    def _insert_batch(self, batch: List[Tuple]):
        """Insert a batch of products."""
        self.conn.executemany("""
            INSERT OR REPLACE INTO products
            (parent_asin, title, brand, store, main_category, avg_rating, rating_count, source_category)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, batch)
    
    def _stream_metadata(self, path: Path) -> Generator[Dict, None, None]:
        """Stream metadata records from JSONL file."""
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    yield json.loads(line.strip())
                except json.JSONDecodeError:
                    continue
    
    def search(
        self,
        brand: Optional[str] = None,
        product_name: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 20,
    ) -> List[ProductSearchResult]:
        """
        Search for products by brand and/or name.
        
        Uses a multi-tier search strategy:
        1. Exact brand + name match
        2. Brand-only match
        3. Full-text search on title
        4. Fuzzy matching
        
        Args:
            brand: Brand name to search for
            product_name: Product name/keywords
            category: Limit to specific category
            limit: Maximum results
            
        Returns:
            List of ProductSearchResult ordered by match quality
        """
        if not self.index_exists:
            logger.warning("Index not built. Call build_index() first.")
            return []
        
        results = []
        seen_asins = set()
        
        # Normalize inputs
        brand_normalized = self._normalize(brand) if brand else None
        name_normalized = self._normalize(product_name) if product_name else None
        
        # Determine categories to search
        search_categories = self._resolve_categories(category)
        
        # Tier 1: Exact brand match with name keywords
        if brand and product_name:
            tier1 = self._search_exact_brand_name(
                brand_normalized, name_normalized, search_categories, limit
            )
            for r in tier1:
                if r.product.parent_asin not in seen_asins:
                    r.match_score = 1.0
                    r.match_type = "exact"
                    results.append(r)
                    seen_asins.add(r.product.parent_asin)
        
        # Tier 2: Brand-only match
        if brand and len(results) < limit:
            tier2 = self._search_brand_only(
                brand_normalized, search_categories, limit - len(results)
            )
            for r in tier2:
                if r.product.parent_asin not in seen_asins:
                    r.match_score = 0.8
                    r.match_type = "brand"
                    results.append(r)
                    seen_asins.add(r.product.parent_asin)
        
        # Tier 3: FTS search on title
        if product_name and len(results) < limit:
            tier3 = self._search_fts(
                name_normalized, search_categories, limit - len(results)
            )
            for r in tier3:
                if r.product.parent_asin not in seen_asins:
                    r.match_score = 0.6
                    r.match_type = "fuzzy"
                    results.append(r)
                    seen_asins.add(r.product.parent_asin)
        
        return results[:limit]
    
    def _normalize(self, text: str) -> str:
        """Normalize text for matching."""
        if not text:
            return ""
        # Lowercase, remove punctuation, collapse whitespace
        text = text.lower()
        text = re.sub(r'[^\w\s]', ' ', text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    
    def _resolve_categories(self, category: Optional[str]) -> Optional[List[str]]:
        """Resolve category hint to actual file categories."""
        if not category:
            return None
        
        category_lower = category.lower()
        
        # Check direct mapping
        if category_lower in CATEGORY_FILE_MAP:
            return CATEGORY_FILE_MAP[category_lower]
        
        # Check if it's an exact category name
        available = self.get_available_categories()
        for avail in available:
            if category_lower == avail.lower():
                return [avail]
        
        # Fuzzy match
        for avail in available:
            if category_lower in avail.lower():
                return [avail]
        
        return None
    
    def _search_exact_brand_name(
        self,
        brand: str,
        name: str,
        categories: Optional[List[str]],
        limit: int,
    ) -> List[ProductSearchResult]:
        """Search with exact brand and name keywords."""
        # First try exact brand match with ALL name keywords
        name_keywords = name.split()
        
        query = """
            SELECT p.* FROM products p
            WHERE LOWER(p.brand) = ?
        """
        params = [brand]
        
        # Require ALL keywords to be present
        for keyword in name_keywords:
            if len(keyword) >= 3:  # Skip short words
                query += " AND LOWER(p.title) LIKE ?"
                params.append(f"%{keyword}%")
        
        if categories:
            placeholders = ",".join("?" * len(categories))
            query += f" AND p.source_category IN ({placeholders})"
            params.extend(categories)
        
        query += " ORDER BY p.rating_count DESC LIMIT ?"
        params.append(limit)
        
        results = self._execute_search(query, params)
        
        # If no results with ALL keywords, try with ANY keyword
        if not results and len(name_keywords) > 1:
            query2 = """
                SELECT p.* FROM products p
                WHERE LOWER(p.brand) = ?
                AND ("""
            params2 = [brand]
            
            keyword_conditions = []
            for keyword in name_keywords:
                if len(keyword) >= 3:
                    keyword_conditions.append("LOWER(p.title) LIKE ?")
                    params2.append(f"%{keyword}%")
            
            if keyword_conditions:
                query2 += " OR ".join(keyword_conditions) + ")"
                
                if categories:
                    placeholders = ",".join("?" * len(categories))
                    query2 += f" AND p.source_category IN ({placeholders})"
                    params2.extend(categories)
                
                query2 += " ORDER BY p.rating_count DESC LIMIT ?"
                params2.append(limit)
                
                results = self._execute_search(query2, params2)
        
        return results
    
    def _search_brand_only(
        self,
        brand: str,
        categories: Optional[List[str]],
        limit: int,
    ) -> List[ProductSearchResult]:
        """Search by brand only."""
        # Try exact match first
        query = """
            SELECT p.* FROM products p
            WHERE LOWER(p.brand) = ?
        """
        params = [brand]
        
        if categories:
            placeholders = ",".join("?" * len(categories))
            query += f" AND p.source_category IN ({placeholders})"
            params.extend(categories)
        
        query += " ORDER BY p.rating_count DESC LIMIT ?"
        params.append(limit)
        
        results = self._execute_search(query, params)
        
        # If few results, try LIKE match
        if len(results) < limit // 2:
            query2 = """
                SELECT p.* FROM products p
                WHERE LOWER(p.brand) LIKE ?
            """
            params2 = [f"%{brand}%"]
            
            if categories:
                placeholders = ",".join("?" * len(categories))
                query2 += f" AND p.source_category IN ({placeholders})"
                params2.extend(categories)
            
            query2 += " ORDER BY p.rating_count DESC LIMIT ?"
            params2.append(limit - len(results))
            
            results.extend(self._execute_search(query2, params2))
        
        return results
    
    def _search_fts(
        self,
        query_text: str,
        categories: Optional[List[str]],
        limit: int,
    ) -> List[ProductSearchResult]:
        """Full-text search on title."""
        # Prepare FTS query (escape special characters)
        fts_query = " OR ".join(query_text.split())
        
        query = """
            SELECT p.* FROM products p
            JOIN products_fts fts ON p.rowid = fts.rowid
            WHERE products_fts MATCH ?
        """
        params = [fts_query]
        
        if categories:
            placeholders = ",".join("?" * len(categories))
            query += f" AND p.source_category IN ({placeholders})"
            params.extend(categories)
        
        query += " ORDER BY p.rating_count DESC LIMIT ?"
        params.append(limit)
        
        try:
            return self._execute_search(query, params)
        except sqlite3.OperationalError:
            # FTS query failed, fall back to LIKE
            return self._search_like(query_text, categories, limit)
    
    def _search_like(
        self,
        query_text: str,
        categories: Optional[List[str]],
        limit: int,
    ) -> List[ProductSearchResult]:
        """Fallback LIKE search."""
        query = """
            SELECT p.* FROM products p
            WHERE LOWER(p.title) LIKE ?
        """
        params = [f"%{query_text}%"]
        
        if categories:
            placeholders = ",".join("?" * len(categories))
            query += f" AND p.source_category IN ({placeholders})"
            params.extend(categories)
        
        query += " ORDER BY p.rating_count DESC LIMIT ?"
        params.append(limit)
        
        return self._execute_search(query, params)
    
    def _execute_search(self, query: str, params: List) -> List[ProductSearchResult]:
        """Execute search query and return results."""
        try:
            cursor = self.conn.execute(query, params)
            results = []
            for row in cursor.fetchall():
                product = AmazonProduct(
                    parent_asin=row["parent_asin"],
                    title=row["title"],
                    brand=row["brand"],
                    store=row["store"],
                    main_category=row["main_category"],
                    average_rating=row["avg_rating"],
                    rating_number=row["rating_count"],
                )
                results.append(ProductSearchResult(
                    product=product,
                    match_score=0.0,  # Set by caller
                    match_type="",    # Set by caller
                    category=row["source_category"],
                    review_count=row["rating_count"],
                ))
            return results
        except sqlite3.OperationalError as e:
            logger.warning(f"Search query failed: {e}")
            return []
    
    def get_product_by_asin(self, asin: str) -> Optional[AmazonProduct]:
        """Get a single product by ASIN."""
        cursor = self.conn.execute("""
            SELECT * FROM products WHERE parent_asin = ?
        """, [asin])
        row = cursor.fetchone()
        if row:
            return AmazonProduct(
                parent_asin=row["parent_asin"],
                title=row["title"],
                brand=row["brand"],
                store=row["store"],
                main_category=row["main_category"],
                average_rating=row["avg_rating"],
                rating_number=row["rating_count"],
            )
        return None
    
    def get_stats(self) -> Dict[str, Any]:
        """Get index statistics."""
        if not self.index_exists:
            return {"status": "not_built"}
        
        cursor = self.conn.execute("SELECT COUNT(*) FROM products")
        total = cursor.fetchone()[0]
        
        cursor = self.conn.execute("SELECT COUNT(*) FROM products WHERE brand IS NOT NULL AND brand != ''")
        with_brand = cursor.fetchone()[0]
        
        cursor = self.conn.execute("SELECT source_category, COUNT(*) as cnt FROM products GROUP BY source_category ORDER BY cnt DESC")
        by_category = {row[0]: row[1] for row in cursor.fetchall()}
        
        return {
            "status": "built",
            "total_products": total,
            "with_brand": with_brand,
            "by_category": by_category,
        }


def build_metadata_index(
    data_dir: str,
    categories: Optional[List[str]] = None,
    limit_per_category: Optional[int] = None,
    force_rebuild: bool = False,
) -> Dict[str, Any]:
    """
    Convenience function to build the metadata index.
    
    Args:
        data_dir: Path to Amazon data directory
        categories: Categories to index (None = all)
        limit_per_category: Limit per category (for testing)
        force_rebuild: Force rebuild even if exists
        
    Returns:
        Indexing statistics
    """
    indexer = MetadataIndexer(data_dir)
    try:
        return indexer.build_index(
            categories=categories,
            limit_per_category=limit_per_category,
            force_rebuild=force_rebuild,
        )
    finally:
        indexer.close()
