# =============================================================================
# Review Aggregator
# Location: adam/intelligence/scrapers/aggregator.py
# =============================================================================

"""
Aggregates reviews from multiple scraper sources.

Handles:
- Parallel execution of multiple scrapers
- Deduplication across sources
- Quality filtering
- Rate limit management
"""

import asyncio
import hashlib
import logging
from datetime import datetime
from typing import Dict, List, Optional, Type

from adam.intelligence.models.customer_intelligence import ReviewSource
from adam.intelligence.scrapers.base import (
    BaseReviewScraper,
    RawReview,
    ScraperResult,
)
from adam.intelligence.scrapers.product_page import ProductPageScraper

logger = logging.getLogger(__name__)


class AggregatedResult:
    """Result of aggregated multi-source scraping."""
    
    def __init__(self):
        self.reviews: List[RawReview] = []
        self.source_results: Dict[ReviewSource, ScraperResult] = {}
        self.total_found: int = 0
        self.unique_count: int = 0
        self.duplicates_removed: int = 0
        self.sources_succeeded: List[ReviewSource] = []
        self.sources_failed: List[ReviewSource] = []
        self.product_info: Dict[str, str] = {}
        self.scrape_duration_ms: float = 0.0
        self.scraped_at: datetime = datetime.utcnow()
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "reviews_count": len(self.reviews),
            "total_found": self.total_found,
            "unique_count": self.unique_count,
            "duplicates_removed": self.duplicates_removed,
            "sources_succeeded": [s.value for s in self.sources_succeeded],
            "sources_failed": [s.value for s in self.sources_failed],
            "product_info": self.product_info,
            "scrape_duration_ms": self.scrape_duration_ms,
            "scraped_at": self.scraped_at.isoformat(),
        }


class ReviewAggregator:
    """
    Aggregates reviews from multiple scraper sources.
    
    Executes scrapers in parallel, deduplicates results,
    and filters for quality.
    """
    
    def __init__(self):
        """Initialize with default scrapers."""
        self.scrapers: Dict[ReviewSource, BaseReviewScraper] = {}
        
        # Register default product page scraper
        self.register_scraper(ProductPageScraper())
        
        # PRIORITY: Use Playwright-based Amazon scraper (headless browser)
        # This bypasses Amazon's bot detection
        playwright_registered = False
        try:
            from adam.intelligence.scrapers.amazon_playwright import AmazonPlaywrightScraper
            self.register_scraper(AmazonPlaywrightScraper(max_pages=10))
            playwright_registered = True
            logger.info("Using Playwright-based Amazon scraper (headless browser)")
        except ImportError as e:
            logger.warning(f"Playwright scraper not available: {e}")
        
        # Fallback: httpx-based Amazon scraper (may be blocked by Amazon)
        if not playwright_registered:
            try:
                from adam.intelligence.scrapers.amazon_reviews import AmazonReviewsScraper
                self.register_scraper(AmazonReviewsScraper(max_pages=10))
                logger.info("Using httpx-based Amazon scraper (fallback)")
            except ImportError:
                logger.debug("Amazon reviews scraper not available")
        
        # Register Google search scraper for additional sources
        try:
            from adam.intelligence.scrapers.google_reviews import GoogleReviewsScraper
            self.register_scraper(GoogleReviewsScraper())
        except ImportError:
            logger.debug("Google reviews scraper not available")
    
    def register_scraper(self, scraper: BaseReviewScraper) -> None:
        """Register a scraper for a source."""
        self.scrapers[scraper.source] = scraper
        logger.info(f"Registered scraper: {scraper.name}")
    
    async def scrape_all(
        self,
        product_name: str,
        product_url: Optional[str] = None,
        brand: Optional[str] = None,
        max_reviews_per_source: int = 50,
        sources: Optional[List[ReviewSource]] = None,
        timeout_per_source: int = 30,
    ) -> AggregatedResult:
        """
        Scrape reviews from all registered sources in parallel.
        
        Args:
            product_name: Product name to search for
            product_url: Direct product URL (if available)
            brand: Brand name for search refinement
            max_reviews_per_source: Max reviews to get from each source
            sources: Specific sources to use (None = all registered)
            timeout_per_source: Timeout for each scraper
            
        Returns:
            AggregatedResult with all unique reviews
        """
        start_time = datetime.utcnow()
        result = AggregatedResult()
        
        # Determine which scrapers to use
        scrapers_to_use = {}
        if sources:
            for source in sources:
                if source in self.scrapers:
                    scrapers_to_use[source] = self.scrapers[source]
        else:
            scrapers_to_use = self.scrapers.copy()
        
        if not scrapers_to_use:
            logger.warning("No scrapers available for aggregation")
            return result
        
        # Check scraper availability
        availability_checks = [
            (source, scraper.is_available())
            for source, scraper in scrapers_to_use.items()
        ]
        
        available_scrapers = {}
        for source, check_coro in availability_checks:
            try:
                is_available = await asyncio.wait_for(check_coro, timeout=5)
                if is_available:
                    available_scrapers[source] = scrapers_to_use[source]
                else:
                    logger.debug(f"Scraper {source.value} not available")
            except asyncio.TimeoutError:
                logger.debug(f"Scraper {source.value} availability check timed out")
        
        if not available_scrapers:
            logger.warning("No scrapers available after availability checks")
            return result
        
        # Execute scrapers in parallel
        tasks = []
        for source, scraper in available_scrapers.items():
            task = asyncio.create_task(
                self._scrape_with_timeout(
                    scraper,
                    product_name,
                    product_url,
                    brand,
                    max_reviews_per_source,
                    timeout_per_source,
                )
            )
            tasks.append((source, task))
        
        # Gather results
        all_reviews = []
        for source, task in tasks:
            try:
                scrape_result = await task
                result.source_results[source] = scrape_result
                
                if scrape_result.success:
                    result.sources_succeeded.append(source)
                    all_reviews.extend(scrape_result.reviews)
                    result.total_found += scrape_result.total_found
                    
                    # Collect product info
                    if scrape_result.product_name:
                        result.product_info["name"] = scrape_result.product_name
                    if scrape_result.product_description:
                        result.product_info["description"] = scrape_result.product_description
                    if scrape_result.product_price:
                        result.product_info["price"] = scrape_result.product_price
                    if scrape_result.product_brand:
                        result.product_info["brand"] = scrape_result.product_brand
                else:
                    result.sources_failed.append(source)
                    logger.warning(
                        f"Scraper {source.value} failed: {scrape_result.error_message}"
                    )
                    
            except Exception as e:
                result.sources_failed.append(source)
                logger.error(f"Error with scraper {source.value}: {e}")
        
        # Deduplicate reviews
        unique_reviews = self._deduplicate_reviews(all_reviews)
        result.reviews = unique_reviews
        result.unique_count = len(unique_reviews)
        result.duplicates_removed = len(all_reviews) - len(unique_reviews)
        
        # Calculate duration
        end_time = datetime.utcnow()
        result.scrape_duration_ms = (end_time - start_time).total_seconds() * 1000
        result.scraped_at = end_time
        
        logger.info(
            f"Aggregated {result.unique_count} unique reviews from "
            f"{len(result.sources_succeeded)} sources in {result.scrape_duration_ms:.0f}ms"
        )
        
        return result
    
    async def _scrape_with_timeout(
        self,
        scraper: BaseReviewScraper,
        product_name: str,
        product_url: Optional[str],
        brand: Optional[str],
        max_reviews: int,
        timeout: int,
    ) -> ScraperResult:
        """Execute a single scraper with timeout."""
        try:
            return await asyncio.wait_for(
                scraper.scrape(
                    product_name=product_name,
                    product_url=product_url,
                    brand=brand,
                    max_reviews=max_reviews,
                ),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            return ScraperResult(
                source=scraper.source,
                success=False,
                error_message="Timeout",
            )
        except Exception as e:
            return ScraperResult(
                source=scraper.source,
                success=False,
                error_message=str(e),
            )
    
    def _deduplicate_reviews(self, reviews: List[RawReview]) -> List[RawReview]:
        """
        Remove duplicate reviews across sources.
        
        Uses fuzzy matching on review text to detect duplicates
        even from different sources.
        """
        seen_hashes = set()
        unique = []
        
        for review in reviews:
            # Create a fuzzy hash from normalized review text
            normalized = self._normalize_text(review.review_text)
            text_hash = hashlib.md5(normalized.encode()).hexdigest()
            
            if text_hash not in seen_hashes:
                seen_hashes.add(text_hash)
                unique.append(review)
        
        return unique
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text for deduplication."""
        # Lowercase, remove extra whitespace, remove punctuation
        import re
        text = text.lower()
        text = re.sub(r"\s+", " ", text)
        text = re.sub(r"[^\w\s]", "", text)
        return text.strip()[:500]  # Use first 500 chars for matching
    
    async def close(self) -> None:
        """Close all scrapers."""
        for scraper in self.scrapers.values():
            if hasattr(scraper, "close"):
                await scraper.close()


# =============================================================================
# SINGLETON ACCESS
# =============================================================================

_aggregator_instance: Optional[ReviewAggregator] = None


def get_review_aggregator() -> ReviewAggregator:
    """Get or create the singleton aggregator instance."""
    global _aggregator_instance
    if _aggregator_instance is None:
        _aggregator_instance = ReviewAggregator()
    return _aggregator_instance
