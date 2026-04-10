# =============================================================================
# ADAM Amazon Data Ingestion Service
# Location: adam/data/amazon/ingestion.py
# =============================================================================

"""
AMAZON DATA INGESTION

Processes Amazon review JSONL files into Neo4j for psychological prior generation.

The pipeline:
1. Stream JSONL files line-by-line (memory efficient for 1.2B+ reviews)
2. Parse into typed Pydantic models
3. Batch insert into Neo4j
4. Track ingestion progress in Redis

Usage:
    service = AmazonIngestionService(neo4j_driver, redis_client)
    await service.ingest_category("Books", data_path="/path/to/Books.jsonl")
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import AsyncGenerator, Dict, List, Optional, Tuple

from neo4j import AsyncDriver
import redis.asyncio as redis
import structlog
from prometheus_client import Counter, Histogram, Gauge

from adam.data.amazon.models import (
    AmazonReview,
    ProductMetadata,
    AmazonCategory,
)

logger = structlog.get_logger(__name__)

# =============================================================================
# METRICS
# =============================================================================

REVIEWS_INGESTED = Counter(
    "adam_amazon_reviews_ingested_total",
    "Total number of Amazon reviews ingested",
    ["category"]
)

PRODUCTS_INGESTED = Counter(
    "adam_amazon_products_ingested_total",
    "Total number of Amazon products ingested",
    ["category"]
)

INGESTION_LATENCY = Histogram(
    "adam_amazon_ingestion_batch_latency_seconds",
    "Latency of batch insertion",
    ["entity_type"]
)

INGESTION_PROGRESS = Gauge(
    "adam_amazon_ingestion_progress",
    "Current ingestion progress (lines processed)",
    ["category"]
)


# =============================================================================
# INGESTION SERVICE
# =============================================================================

class AmazonIngestionService:
    """
    Ingests Amazon review data into Neo4j.
    
    Design principles:
    - Streaming: Process files line-by-line, never load full file
    - Batching: Insert in configurable batch sizes
    - Resumable: Track progress in Redis for crash recovery
    - Observable: Emit metrics for monitoring
    """
    
    DEFAULT_BATCH_SIZE = 1000
    PROGRESS_KEY_PREFIX = "adam:amazon:ingestion:"
    
    def __init__(
        self,
        neo4j_driver: AsyncDriver,
        redis_client: redis.Redis,
        database: str = "adam",
        batch_size: int = DEFAULT_BATCH_SIZE,
    ):
        self._neo4j = neo4j_driver
        self._redis = redis_client
        self._database = database
        self._batch_size = batch_size
        self._log = structlog.get_logger(__name__)
    
    # =========================================================================
    # PUBLIC API
    # =========================================================================
    
    async def ingest_category(
        self,
        category: str,
        reviews_path: Path,
        metadata_path: Optional[Path] = None,
        resume: bool = True,
    ) -> Tuple[int, int]:
        """
        Ingest a complete category of Amazon reviews.
        
        Args:
            category: Category name (e.g., "Books")
            reviews_path: Path to {Category}.jsonl
            metadata_path: Path to meta_{Category}.jsonl (optional)
            resume: Whether to resume from last checkpoint
            
        Returns:
            Tuple of (reviews_ingested, products_ingested)
        """
        self._log.info("Starting category ingestion",
                      category=category,
                      reviews_path=str(reviews_path))
        
        reviews_count = 0
        products_count = 0
        
        # Ingest reviews
        if reviews_path.exists():
            reviews_count = await self._ingest_reviews(
                category=category,
                file_path=reviews_path,
                resume=resume
            )
        else:
            self._log.warning("Reviews file not found", path=str(reviews_path))
        
        # Ingest product metadata
        if metadata_path and metadata_path.exists():
            products_count = await self._ingest_products(
                category=category,
                file_path=metadata_path,
                resume=resume
            )
        elif metadata_path:
            self._log.warning("Metadata file not found", path=str(metadata_path))
        
        self._log.info("Category ingestion complete",
                      category=category,
                      reviews_count=reviews_count,
                      products_count=products_count)
        
        return (reviews_count, products_count)
    
    async def ingest_all_categories(
        self,
        data_directory: Path,
        categories: Optional[List[str]] = None,
    ) -> Dict[str, Tuple[int, int]]:
        """
        Ingest all (or specified) categories from a directory.
        
        Expected directory structure:
            data_directory/
                Books.jsonl
                meta_Books.jsonl
                Electronics.jsonl
                meta_Electronics.jsonl
                ...
                
        Args:
            data_directory: Directory containing JSONL files
            categories: List of category names to ingest (None = all)
            
        Returns:
            Dict mapping category name to (reviews, products) counts
        """
        results = {}
        
        # Discover categories
        if categories is None:
            categories = self._discover_categories(data_directory)
        
        self._log.info("Ingesting categories",
                      count=len(categories),
                      categories=categories[:5])  # Log first 5
        
        for category in categories:
            reviews_path = data_directory / f"{category}.jsonl"
            metadata_path = data_directory / f"meta_{category}.jsonl"
            
            try:
                results[category] = await self.ingest_category(
                    category=category,
                    reviews_path=reviews_path,
                    metadata_path=metadata_path,
                )
            except Exception as e:
                self._log.error("Failed to ingest category",
                              category=category,
                              error=str(e))
                results[category] = (0, 0)
        
        return results
    
    # =========================================================================
    # PRIVATE: REVIEWS INGESTION
    # =========================================================================
    
    async def _ingest_reviews(
        self,
        category: str,
        file_path: Path,
        resume: bool = True,
    ) -> int:
        """Ingest reviews from a JSONL file."""
        
        # Get resume position
        start_line = 0
        if resume:
            start_line = await self._get_progress(category, "reviews")
        
        self._log.info("Ingesting reviews",
                      category=category,
                      start_line=start_line)
        
        count = 0
        batch = []
        
        async for line_num, review in self._stream_reviews(file_path, start_line):
            batch.append(review)
            
            if len(batch) >= self._batch_size:
                await self._insert_review_batch(batch, category)
                count += len(batch)
                
                # Update progress
                await self._set_progress(category, "reviews", line_num)
                INGESTION_PROGRESS.labels(category=category).set(line_num)
                
                self._log.debug("Batch inserted",
                              category=category,
                              batch_size=len(batch),
                              total=count)
                batch = []
        
        # Final batch
        if batch:
            await self._insert_review_batch(batch, category)
            count += len(batch)
        
        REVIEWS_INGESTED.labels(category=category).inc(count)
        return count
    
    async def _stream_reviews(
        self,
        file_path: Path,
        start_line: int = 0,
    ) -> AsyncGenerator[Tuple[int, AmazonReview], None]:
        """Stream reviews from JSONL file."""
        
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f):
                if line_num < start_line:
                    continue
                
                try:
                    data = json.loads(line.strip())
                    review = AmazonReview(**data)
                    yield line_num, review
                except json.JSONDecodeError as e:
                    self._log.warning("Invalid JSON",
                                     line_num=line_num,
                                     error=str(e))
                except Exception as e:
                    self._log.warning("Failed to parse review",
                                     line_num=line_num,
                                     error=str(e))
    
    async def _insert_review_batch(
        self,
        reviews: List[AmazonReview],
        category: str,
    ) -> None:
        """Insert a batch of reviews into Neo4j."""
        
        with INGESTION_LATENCY.labels(entity_type="review").time():
            async with self._neo4j.session(database=self._database) as session:
                await session.execute_write(
                    self._create_reviews_tx,
                    reviews=reviews,
                    category=category,
                )
    
    @staticmethod
    async def _create_reviews_tx(tx, reviews: List[AmazonReview], category: str):
        """Transaction function for inserting reviews."""
        
        # Build batch data
        batch_data = []
        for r in reviews:
            batch_data.append({
                "review_id": r.review_id,
                "rating": r.rating,
                "title": r.title,
                "text": r.text[:10000],  # Truncate very long reviews
                "asin": r.asin,
                "parent_asin": r.parent_asin,
                "user_id": r.user_id,
                "timestamp": r.timestamp,
                "timestamp_dt": r.timestamp_dt.isoformat(),
                "helpful_vote": r.helpful_vote,
                "verified_purchase": r.verified_purchase,
                "word_count": r.word_count,
                "category": category,
            })
        
        # Upsert reviews and users in single query
        query = """
        UNWIND $batch AS review
        
        // Merge user
        MERGE (u:AmazonUser {amazon_user_id: review.user_id})
        ON CREATE SET
            u.created_at = datetime(),
            u.review_count = 0,
            u.first_review_at = datetime(review.timestamp_dt)
        ON MATCH SET
            u.first_review_at = CASE 
                WHEN datetime(review.timestamp_dt) < u.first_review_at 
                THEN datetime(review.timestamp_dt) 
                ELSE u.first_review_at 
            END
        SET u.review_count = u.review_count + 1,
            u.last_review_at = datetime(review.timestamp_dt),
            u.updated_at = datetime()
        
        // Merge review
        MERGE (r:AmazonReview {review_id: review.review_id})
        SET r.rating = review.rating,
            r.title = review.title,
            r.text = review.text,
            r.asin = review.asin,
            r.parent_asin = review.parent_asin,
            r.user_id = review.user_id,
            r.timestamp = review.timestamp,
            r.timestamp_dt = datetime(review.timestamp_dt),
            r.helpful_vote = review.helpful_vote,
            r.verified_purchase = review.verified_purchase,
            r.word_count = review.word_count,
            r.category = review.category,
            r.created_at = datetime()
        
        // Create relationship
        MERGE (u)-[:WROTE_REVIEW]->(r)
        
        // Merge category
        MERGE (c:AmazonCategory {name: review.category})
        MERGE (r)-[:IN_CATEGORY]->(c)
        """
        
        await tx.run(query, batch=batch_data)
    
    # =========================================================================
    # PRIVATE: PRODUCTS INGESTION
    # =========================================================================
    
    async def _ingest_products(
        self,
        category: str,
        file_path: Path,
        resume: bool = True,
    ) -> int:
        """Ingest product metadata from a JSONL file."""
        
        start_line = 0
        if resume:
            start_line = await self._get_progress(category, "products")
        
        self._log.info("Ingesting products",
                      category=category,
                      start_line=start_line)
        
        count = 0
        batch = []
        
        async for line_num, product in self._stream_products(file_path, start_line):
            batch.append(product)
            
            if len(batch) >= self._batch_size:
                await self._insert_product_batch(batch, category)
                count += len(batch)
                await self._set_progress(category, "products", line_num)
                batch = []
        
        if batch:
            await self._insert_product_batch(batch, category)
            count += len(batch)
        
        PRODUCTS_INGESTED.labels(category=category).inc(count)
        return count
    
    async def _stream_products(
        self,
        file_path: Path,
        start_line: int = 0,
    ) -> AsyncGenerator[Tuple[int, ProductMetadata], None]:
        """Stream products from JSONL file."""
        
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f):
                if line_num < start_line:
                    continue
                
                try:
                    data = json.loads(line.strip())
                    product = ProductMetadata(**data)
                    yield line_num, product
                except Exception as e:
                    self._log.warning("Failed to parse product",
                                     line_num=line_num,
                                     error=str(e))
    
    async def _insert_product_batch(
        self,
        products: List[ProductMetadata],
        category: str,
    ) -> None:
        """Insert a batch of products into Neo4j."""
        
        with INGESTION_LATENCY.labels(entity_type="product").time():
            async with self._neo4j.session(database=self._database) as session:
                await session.execute_write(
                    self._create_products_tx,
                    products=products,
                    category=category,
                )
    
    @staticmethod
    async def _create_products_tx(tx, products: List[ProductMetadata], category: str):
        """Transaction function for inserting products."""
        
        batch_data = []
        for p in products:
            # Extract description as string
            description = " ".join(p.description) if p.description else ""
            features = " | ".join(p.features) if p.features else ""
            
            batch_data.append({
                "asin": p.parent_asin,
                "title": p.title,
                "subtitle": p.subtitle,
                "main_category": p.main_category,
                "categories": p.categories,
                "average_rating": p.average_rating,
                "rating_number": p.rating_number,
                "price": p.price,
                "store": p.store,
                "description": description[:5000],
                "features": features[:2000],
                "category": category,
            })
        
        query = """
        UNWIND $batch AS product
        
        MERGE (p:AmazonProduct {asin: product.asin})
        SET p.title = product.title,
            p.subtitle = product.subtitle,
            p.main_category = product.main_category,
            p.average_rating = product.average_rating,
            p.rating_number = product.rating_number,
            p.price = product.price,
            p.store = product.store,
            p.description = product.description,
            p.features = product.features,
            p.updated_at = datetime()
        
        // Main category relationship
        MERGE (c:AmazonCategory {name: product.main_category})
        MERGE (p)-[:BELONGS_TO_CATEGORY {is_main_category: true}]->(c)
        
        // Subcategory relationships
        FOREACH (cat IN product.categories |
            MERGE (sc:AmazonCategory {name: cat})
            MERGE (p)-[:BELONGS_TO_CATEGORY {is_main_category: false}]->(sc)
        )
        """
        
        await tx.run(query, batch=batch_data)
    
    # =========================================================================
    # PRIVATE: PROGRESS TRACKING
    # =========================================================================
    
    async def _get_progress(self, category: str, entity_type: str) -> int:
        """Get last processed line number from Redis."""
        key = f"{self.PROGRESS_KEY_PREFIX}{category}:{entity_type}"
        value = await self._redis.get(key)
        return int(value) if value else 0
    
    async def _set_progress(self, category: str, entity_type: str, line_num: int) -> None:
        """Save progress to Redis."""
        key = f"{self.PROGRESS_KEY_PREFIX}{category}:{entity_type}"
        await self._redis.set(key, str(line_num))
    
    def _discover_categories(self, data_directory: Path) -> List[str]:
        """Discover available categories from directory."""
        categories = set()
        
        for f in data_directory.glob("*.jsonl"):
            name = f.stem
            if not name.startswith("meta_"):
                categories.add(name)
        
        return sorted(categories)
    
    # =========================================================================
    # PSYCHOLOGICAL PROFILE INGESTION
    # =========================================================================
    
    async def ingest_user_profiles(
        self,
        profiles: List[Dict],
        batch_size: Optional[int] = None,
    ) -> int:
        """
        Ingest user psychological profiles into Neo4j.
        
        Creates AmazonReviewer nodes with Big Five traits and links
        them to archetypes and categories.
        
        Args:
            profiles: List of profile dicts (from profiler.export_profiles_for_neo4j())
            batch_size: Batch size for insertion
            
        Returns:
            Number of profiles ingested
        """
        batch_size = batch_size or self._batch_size
        total = 0
        
        self._log.info("Ingesting user profiles", count=len(profiles))
        
        for i in range(0, len(profiles), batch_size):
            batch = profiles[i:i + batch_size]
            
            async with self._neo4j.session(database=self._database) as session:
                async with session.begin_transaction() as tx:
                    await self._insert_user_profiles_batch(tx, batch)
                    await tx.commit()
            
            total += len(batch)
            self._log.debug("Profile batch inserted", count=len(batch), total=total)
        
        self._log.info("User profiles ingested", total=total)
        return total
    
    async def _insert_user_profiles_batch(
        self,
        tx,
        batch: List[Dict],
    ) -> None:
        """Insert a batch of user profiles."""
        
        query = """
        UNWIND $batch AS profile
        
        // Create or update reviewer
        MERGE (r:AmazonReviewer {amazon_user_id: profile.amazon_user_id})
        SET r.review_count = profile.review_count,
            r.primary_category = profile.primary_category,
            r.avg_rating = profile.avg_rating,
            r.profile_confidence = profile.profile_confidence,
            r.updated_at = datetime()
        
        // Add Big Five traits if present
        FOREACH (_ IN CASE WHEN profile.openness IS NOT NULL THEN [1] ELSE [] END |
            SET r.openness = profile.openness,
                r.conscientiousness = profile.conscientiousness,
                r.extraversion = profile.extraversion,
                r.agreeableness = profile.agreeableness,
                r.neuroticism = profile.neuroticism,
                r.personality_confidence = profile.personality_confidence
        )
        
        // Link to categories reviewed
        FOREACH (cat IN profile.categories |
            MERGE (c:AmazonCategory {name: cat})
            MERGE (r)-[:REVIEWED_IN]->(c)
        )
        """
        
        await tx.run(query, batch=batch)
    
    async def ingest_category_profiles(
        self,
        category_profiles: List[Dict],
    ) -> int:
        """
        Ingest category psychological profiles into Neo4j.
        
        Creates CategoryPsychology nodes with aggregated Big Five
        distributions and mechanism effectiveness.
        
        Args:
            category_profiles: List of CategoryPsychology dicts
            
        Returns:
            Number of profiles ingested
        """
        self._log.info("Ingesting category profiles", count=len(category_profiles))
        
        async with self._neo4j.session(database=self._database) as session:
            async with session.begin_transaction() as tx:
                for profile in category_profiles:
                    await self._insert_category_profile(tx, profile)
                await tx.commit()
        
        self._log.info("Category profiles ingested", count=len(category_profiles))
        return len(category_profiles)
    
    async def _insert_category_profile(
        self,
        tx,
        profile: Dict,
    ) -> None:
        """Insert a single category profile."""
        
        query = """
        MERGE (cp:CategoryPsychology {category_name: $category_name})
        SET cp.openness_mean = $openness_mean,
            cp.openness_std = $openness_std,
            cp.conscientiousness_mean = $conscientiousness_mean,
            cp.conscientiousness_std = $conscientiousness_std,
            cp.extraversion_mean = $extraversion_mean,
            cp.extraversion_std = $extraversion_std,
            cp.agreeableness_mean = $agreeableness_mean,
            cp.agreeableness_std = $agreeableness_std,
            cp.neuroticism_mean = $neuroticism_mean,
            cp.neuroticism_std = $neuroticism_std,
            cp.avg_rating = $avg_rating,
            cp.avg_review_length = $avg_review_length,
            cp.sample_size = $sample_size,
            cp.unique_users = $unique_users,
            cp.updated_at = datetime()
        
        // Link to Amazon category
        MERGE (c:AmazonCategory {name: $category_name})
        MERGE (cp)-[:DESCRIBES]->(c)
        """
        
        await tx.run(query, **profile)
    
    async def ingest_archetypes(
        self,
        archetypes: List[Dict],
    ) -> int:
        """
        Ingest reviewer archetypes into Neo4j.
        
        Creates ReviewerArchetype nodes for cold-start matching.
        
        Args:
            archetypes: List of archetype dicts
            
        Returns:
            Number of archetypes ingested
        """
        self._log.info("Ingesting archetypes", count=len(archetypes))
        
        async with self._neo4j.session(database=self._database) as session:
            async with session.begin_transaction() as tx:
                for archetype in archetypes:
                    await self._insert_archetype(tx, archetype)
                await tx.commit()
        
        self._log.info("Archetypes ingested", count=len(archetypes))
        return len(archetypes)
    
    async def _insert_archetype(
        self,
        tx,
        archetype: Dict,
    ) -> None:
        """Insert a single archetype."""
        
        query = """
        MERGE (a:ReviewerArchetype {archetype_id: $archetype_id})
        SET a.name = $name,
            a.description = $description,
            a.cluster_id = $cluster_id,
            a.member_count = $member_count,
            a.openness_mean = $openness_mean,
            a.conscientiousness_mean = $conscientiousness_mean,
            a.extraversion_mean = $extraversion_mean,
            a.agreeableness_mean = $agreeableness_mean,
            a.neuroticism_mean = $neuroticism_mean,
            a.avg_rating = $avg_rating,
            a.avg_review_length = $avg_review_length,
            a.updated_at = datetime()
        """
        
        await tx.run(query, **archetype)
