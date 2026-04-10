# =============================================================================
# Unified Multi-Source Review Scraper
# Location: adam/intelligence/scrapers/unified_scraper.py
# =============================================================================

"""
Unified Multi-Source Review Scraper

Scrapes product reviews from multiple platforms using Playwright:
- Amazon (primary)
- Walmart
- Best Buy
- Target
- Costco
- Home Depot
- Generic product pages

Architecture:
1. All scrapers use Playwright for consistency and bot-bypass
2. Smart URL detection routes to appropriate scraper
3. Parallel scraping across multiple sources
4. Deduplication across sources
5. Claude integration for summarization (optional)

Usage:
    scraper = get_unified_scraper()
    result = await scraper.scrape_all_sources(
        product_name="iPhone 15 Pro",
        product_urls=["https://amazon.com/...", "https://walmart.com/..."],
        max_reviews_per_source=50
    )
"""

import asyncio
import hashlib
import logging
import re
import random
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse, quote

from adam.intelligence.models.customer_intelligence import ReviewSource
from adam.intelligence.scrapers.base import (
    BaseReviewScraper,
    RawReview,
    ScraperResult,
)

logger = logging.getLogger(__name__)

# Check Playwright availability
try:
    from playwright.async_api import async_playwright, Browser, Page
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    logger.warning("Playwright not installed. Run: pip install playwright && playwright install chromium")


# =============================================================================
# CONFIGURATION
# =============================================================================

USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
]

RATE_LIMITS = {
    "amazon.com": {"delay_min": 2.0, "delay_max": 4.0},
    "walmart.com": {"delay_min": 2.0, "delay_max": 4.0},
    "bestbuy.com": {"delay_min": 2.0, "delay_max": 3.0},
    "target.com": {"delay_min": 2.0, "delay_max": 3.0},
    "costco.com": {"delay_min": 2.0, "delay_max": 4.0},
    "homedepot.com": {"delay_min": 2.0, "delay_max": 4.0},
    "default": {"delay_min": 1.5, "delay_max": 3.0},
}


@dataclass
class UnifiedScraperResult:
    """Result from unified multi-source scraping."""
    reviews: List[RawReview] = field(default_factory=list)
    source_results: Dict[str, ScraperResult] = field(default_factory=dict)
    total_found: int = 0
    unique_count: int = 0
    duplicates_removed: int = 0
    sources_succeeded: List[str] = field(default_factory=list)
    sources_failed: List[str] = field(default_factory=list)
    product_info: Dict[str, Any] = field(default_factory=dict)
    scrape_duration_ms: float = 0.0
    scraped_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> dict:
        return {
            "reviews_count": len(self.reviews),
            "total_found": self.total_found,
            "unique_count": self.unique_count,
            "duplicates_removed": self.duplicates_removed,
            "sources_succeeded": self.sources_succeeded,
            "sources_failed": self.sources_failed,
            "product_info": self.product_info,
            "scrape_duration_ms": self.scrape_duration_ms,
            "scraped_at": self.scraped_at.isoformat(),
        }


# =============================================================================
# BASE PLAYWRIGHT SCRAPER
# =============================================================================

class PlaywrightBaseScraper(ABC):
    """Base class for all Playwright-based scrapers."""
    
    DOMAIN: str = "unknown"
    SOURCE_NAME: str = "Unknown"
    
    def __init__(self, headless: bool = True):
        self.headless = headless
        self._playwright = None
        self._browser = None
    
    async def _get_browser(self) -> Any:
        """Get or create browser instance."""
        if not PLAYWRIGHT_AVAILABLE:
            raise ImportError("Playwright not installed")
        
        if self._browser is None:
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(headless=self.headless)
        
        return self._browser
    
    async def _create_page(self, browser: Any) -> Any:
        """Create a new page with realistic settings."""
        return await browser.new_page(
            viewport={'width': 1920, 'height': 1080},
            user_agent=random.choice(USER_AGENTS),
        )
    
    async def _random_delay(self, domain: str = "default"):
        """Add random delay to simulate human behavior."""
        config = RATE_LIMITS.get(domain, RATE_LIMITS["default"])
        delay = random.uniform(config["delay_min"], config["delay_max"])
        await asyncio.sleep(delay)
    
    async def _scroll_page(self, page: Any, percentages: List[float] = None):
        """Scroll page to load dynamic content."""
        if percentages is None:
            percentages = [0.3, 0.5, 0.7, 0.9]
        
        for pct in percentages:
            await page.evaluate(f"window.scrollTo(0, document.body.scrollHeight * {pct})")
            await asyncio.sleep(0.5)
    
    @abstractmethod
    async def scrape(
        self,
        product_url: str,
        product_name: str,
        brand: Optional[str] = None,
        max_reviews: int = 50,
    ) -> ScraperResult:
        """Scrape reviews from this source."""
        pass
    
    async def close(self):
        """Close browser and playwright."""
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None


# =============================================================================
# WALMART SCRAPER
# =============================================================================

class WalmartPlaywrightScraper(PlaywrightBaseScraper):
    """Scrapes Walmart product reviews using Playwright."""
    
    DOMAIN = "walmart.com"
    SOURCE_NAME = "Walmart"
    
    def _extract_product_id(self, url: str) -> Optional[str]:
        """Extract product ID from Walmart URL."""
        # Pattern: walmart.com/ip/Product-Name/123456789
        match = re.search(r'/ip/[^/]+/(\d+)', url)
        if match:
            return match.group(1)
        
        # Pattern: walmart.com/ip/123456789
        match = re.search(r'/ip/(\d+)', url)
        if match:
            return match.group(1)
        
        return None
    
    async def scrape(
        self,
        product_url: str,
        product_name: str,
        brand: Optional[str] = None,
        max_reviews: int = 50,
    ) -> ScraperResult:
        """Scrape Walmart reviews."""
        start_time = time.time()
        reviews = []
        product_info = {}
        
        if not PLAYWRIGHT_AVAILABLE:
            return ScraperResult(
                source=ReviewSource.WALMART,
                source_url=product_url,
                success=False,
                error_message="Playwright not installed",
                scrape_duration_ms=(time.time() - start_time) * 1000,
            )
        
        product_id = self._extract_product_id(product_url)
        if not product_id:
            return ScraperResult(
                source=ReviewSource.WALMART,
                source_url=product_url,
                success=False,
                error_message="Could not extract product ID from URL",
                scrape_duration_ms=(time.time() - start_time) * 1000,
            )
        
        page = None
        try:
            browser = await self._get_browser()
            page = await self._create_page(browser)
            
            # Navigate to product page
            logger.info(f"Scraping Walmart reviews for product ID: {product_id}")
            await page.goto(product_url, wait_until='networkidle', timeout=45000)
            await self._random_delay(self.DOMAIN)
            
            # Scroll to load reviews
            await self._scroll_page(page)
            
            # Extract product info
            try:
                title_el = await page.query_selector('[data-testid="product-title"]')
                if title_el:
                    product_info["name"] = (await title_el.text_content() or "").strip()
            except Exception:
                pass
            
            # Find reviews section
            reviews_section = await page.query_selector('[data-testid="reviews-list"]')
            if not reviews_section:
                # Try clicking to expand reviews
                reviews_tab = await page.query_selector('button:has-text("Reviews")')
                if reviews_tab:
                    await reviews_tab.click()
                    await asyncio.sleep(2)
                    reviews_section = await page.query_selector('[data-testid="reviews-list"]')
            
            if reviews_section:
                # Extract individual reviews
                review_elements = await page.query_selector_all('[data-testid="customer-review"]')
                
                for i, elem in enumerate(review_elements[:max_reviews]):
                    try:
                        review = await self._parse_walmart_review(elem, product_url, i)
                        if review:
                            reviews.append(review)
                    except Exception as e:
                        logger.debug(f"Error parsing Walmart review {i}: {e}")
            
            logger.info(f"Extracted {len(reviews)} reviews from Walmart")
            
            return ScraperResult(
                source=ReviewSource.WALMART,
                source_url=product_url,
                reviews=reviews,
                total_found=len(reviews),
                product_name=product_info.get("name", product_name),
                product_brand=brand,
                success=True,
                scrape_duration_ms=(time.time() - start_time) * 1000,
            )
            
        except Exception as e:
            logger.error(f"Error scraping Walmart: {e}")
            return ScraperResult(
                source=ReviewSource.WALMART,
                source_url=product_url,
                reviews=reviews,
                total_found=len(reviews),
                success=len(reviews) > 0,
                error_message=str(e),
                scrape_duration_ms=(time.time() - start_time) * 1000,
            )
        finally:
            if page:
                await page.close()
    
    async def _parse_walmart_review(
        self, elem: Any, url: str, index: int
    ) -> Optional[RawReview]:
        """Parse a single Walmart review element."""
        # Rating
        rating = 3.0
        rating_el = await elem.query_selector('[data-testid="review-rating"]')
        if rating_el:
            rating_text = await rating_el.text_content() or ""
            match = re.search(r'(\d+\.?\d*)', rating_text)
            if match:
                rating = float(match.group(1))
        
        # Review text
        text_el = await elem.query_selector('[data-testid="review-text"]')
        if not text_el:
            text_el = await elem.query_selector('.review-text')
        
        review_text = ""
        if text_el:
            review_text = (await text_el.text_content() or "").strip()
        
        if not review_text or len(review_text) < 20:
            return None
        
        # Reviewer name
        name_el = await elem.query_selector('.reviewer-name, [data-testid="reviewer-name"]')
        reviewer_name = None
        if name_el:
            reviewer_name = (await name_el.text_content() or "").strip()
        
        # Verified purchase
        verified_el = await elem.query_selector('text*="Verified"')
        verified = verified_el is not None
        
        # Generate unique ID
        review_id = hashlib.md5(f"walmart_{index}_{review_text[:50]}".encode()).hexdigest()[:12]
        
        return RawReview(
            review_id=f"wmt_{review_id}",
            source=ReviewSource.WALMART,
            source_url=url,
            review_text=review_text,
            rating=rating,
            reviewer_name=reviewer_name,
            verified_purchase=verified,
        )


# =============================================================================
# BEST BUY SCRAPER
# =============================================================================

class BestBuyPlaywrightScraper(PlaywrightBaseScraper):
    """Scrapes Best Buy product reviews using Playwright."""
    
    DOMAIN = "bestbuy.com"
    SOURCE_NAME = "BestBuy"
    
    def _extract_sku(self, url: str) -> Optional[str]:
        """Extract SKU from Best Buy URL."""
        # Pattern: bestbuy.com/site/product-name/1234567.p
        match = re.search(r'/(\d{7})\.p', url)
        if match:
            return match.group(1)
        return None
    
    async def scrape(
        self,
        product_url: str,
        product_name: str,
        brand: Optional[str] = None,
        max_reviews: int = 50,
    ) -> ScraperResult:
        """Scrape Best Buy reviews."""
        start_time = time.time()
        reviews = []
        
        if not PLAYWRIGHT_AVAILABLE:
            return ScraperResult(
                source=ReviewSource.BESTBUY,
                source_url=product_url,
                success=False,
                error_message="Playwright not installed",
                scrape_duration_ms=(time.time() - start_time) * 1000,
            )
        
        page = None
        try:
            browser = await self._get_browser()
            page = await self._create_page(browser)
            
            logger.info(f"Scraping Best Buy reviews from: {product_url}")
            await page.goto(product_url, wait_until='networkidle', timeout=45000)
            await self._random_delay(self.DOMAIN)
            await self._scroll_page(page)
            
            # Click on reviews tab if exists
            reviews_tab = await page.query_selector('button:has-text("Reviews"), a:has-text("Reviews")')
            if reviews_tab:
                await reviews_tab.click()
                await asyncio.sleep(2)
            
            # Extract reviews
            review_elements = await page.query_selector_all('.review-item, [data-track="Review"]')
            
            for i, elem in enumerate(review_elements[:max_reviews]):
                try:
                    review = await self._parse_bestbuy_review(elem, product_url, i)
                    if review:
                        reviews.append(review)
                except Exception as e:
                    logger.debug(f"Error parsing Best Buy review {i}: {e}")
            
            logger.info(f"Extracted {len(reviews)} reviews from Best Buy")
            
            return ScraperResult(
                source=ReviewSource.BESTBUY,
                source_url=product_url,
                reviews=reviews,
                total_found=len(reviews),
                product_name=product_name,
                product_brand=brand,
                success=True,
                scrape_duration_ms=(time.time() - start_time) * 1000,
            )
            
        except Exception as e:
            logger.error(f"Error scraping Best Buy: {e}")
            return ScraperResult(
                source=ReviewSource.BESTBUY,
                source_url=product_url,
                reviews=reviews,
                success=len(reviews) > 0,
                error_message=str(e),
                scrape_duration_ms=(time.time() - start_time) * 1000,
            )
        finally:
            if page:
                await page.close()
    
    async def _parse_bestbuy_review(
        self, elem: Any, url: str, index: int
    ) -> Optional[RawReview]:
        """Parse a single Best Buy review element."""
        # Rating - Best Buy uses filled stars
        rating = 3.0
        stars = await elem.query_selector_all('.c-star-icon-v2.filled, [class*="star-filled"]')
        if stars:
            rating = float(len(stars))
        
        # Review text
        text_el = await elem.query_selector('.review-body, .ugc-review-body')
        review_text = ""
        if text_el:
            review_text = (await text_el.text_content() or "").strip()
        
        if not review_text or len(review_text) < 20:
            return None
        
        # Title
        title_el = await elem.query_selector('.review-title, .ugc-review-title')
        title = ""
        if title_el:
            title = (await title_el.text_content() or "").strip()
        
        if title:
            review_text = f"{title}. {review_text}"
        
        # Reviewer name
        name_el = await elem.query_selector('.review-author, .ugc-author')
        reviewer_name = None
        if name_el:
            reviewer_name = (await name_el.text_content() or "").strip()
        
        # Verified purchase
        verified_el = await elem.query_selector('text*="Verified"')
        verified = verified_el is not None
        
        review_id = hashlib.md5(f"bestbuy_{index}_{review_text[:50]}".encode()).hexdigest()[:12]
        
        return RawReview(
            review_id=f"bby_{review_id}",
            source=ReviewSource.BESTBUY,
            source_url=url,
            review_text=review_text,
            rating=rating,
            reviewer_name=reviewer_name,
            verified_purchase=verified,
        )


# =============================================================================
# TARGET SCRAPER
# =============================================================================

class TargetPlaywrightScraper(PlaywrightBaseScraper):
    """Scrapes Target product reviews using Playwright."""
    
    DOMAIN = "target.com"
    SOURCE_NAME = "Target"
    
    async def scrape(
        self,
        product_url: str,
        product_name: str,
        brand: Optional[str] = None,
        max_reviews: int = 50,
    ) -> ScraperResult:
        """Scrape Target reviews."""
        start_time = time.time()
        reviews = []
        
        if not PLAYWRIGHT_AVAILABLE:
            return ScraperResult(
                source=ReviewSource.TARGET,
                source_url=product_url,
                success=False,
                error_message="Playwright not installed",
                scrape_duration_ms=(time.time() - start_time) * 1000,
            )
        
        page = None
        try:
            browser = await self._get_browser()
            page = await self._create_page(browser)
            
            logger.info(f"Scraping Target reviews from: {product_url}")
            await page.goto(product_url, wait_until='networkidle', timeout=45000)
            await self._random_delay(self.DOMAIN)
            await self._scroll_page(page)
            
            # Click reviews section
            reviews_section = await page.query_selector('[data-test="reviews-section"]')
            if reviews_section:
                await reviews_section.scroll_into_view_if_needed()
                await asyncio.sleep(1)
            
            # Extract reviews
            review_elements = await page.query_selector_all('[data-test="review-card"]')
            
            for i, elem in enumerate(review_elements[:max_reviews]):
                try:
                    review = await self._parse_target_review(elem, product_url, i)
                    if review:
                        reviews.append(review)
                except Exception as e:
                    logger.debug(f"Error parsing Target review {i}: {e}")
            
            logger.info(f"Extracted {len(reviews)} reviews from Target")
            
            return ScraperResult(
                source=ReviewSource.TARGET,
                source_url=product_url,
                reviews=reviews,
                total_found=len(reviews),
                product_name=product_name,
                product_brand=brand,
                success=True,
                scrape_duration_ms=(time.time() - start_time) * 1000,
            )
            
        except Exception as e:
            logger.error(f"Error scraping Target: {e}")
            return ScraperResult(
                source=ReviewSource.TARGET,
                source_url=product_url,
                reviews=reviews,
                success=len(reviews) > 0,
                error_message=str(e),
                scrape_duration_ms=(time.time() - start_time) * 1000,
            )
        finally:
            if page:
                await page.close()
    
    async def _parse_target_review(
        self, elem: Any, url: str, index: int
    ) -> Optional[RawReview]:
        """Parse a single Target review element."""
        # Rating
        rating = 3.0
        rating_el = await elem.query_selector('[data-test="review-rating"]')
        if rating_el:
            rating_text = await rating_el.get_attribute('aria-label') or ""
            match = re.search(r'(\d+\.?\d*)\s*out\s*of\s*5', rating_text, re.I)
            if match:
                rating = float(match.group(1))
        
        # Review text
        text_el = await elem.query_selector('[data-test="review-text"]')
        review_text = ""
        if text_el:
            review_text = (await text_el.text_content() or "").strip()
        
        if not review_text or len(review_text) < 20:
            return None
        
        # Title
        title_el = await elem.query_selector('[data-test="review-title"]')
        if title_el:
            title = (await title_el.text_content() or "").strip()
            if title:
                review_text = f"{title}. {review_text}"
        
        review_id = hashlib.md5(f"target_{index}_{review_text[:50]}".encode()).hexdigest()[:12]
        
        return RawReview(
            review_id=f"tgt_{review_id}",
            source=ReviewSource.TARGET,
            source_url=url,
            review_text=review_text,
            rating=rating,
        )


# =============================================================================
# UNIFIED SCRAPER ORCHESTRATOR
# =============================================================================

class UnifiedReviewScraper:
    """
    Unified orchestrator for multi-source review scraping.
    
    Features:
    - Smart URL routing to appropriate scraper
    - Parallel scraping across sources
    - Deduplication
    - Claude summarization (optional)
    """
    
    def __init__(self, headless: bool = True):
        """Initialize unified scraper with all platform scrapers."""
        self.headless = headless
        
        # Initialize scrapers lazily
        self._scrapers: Dict[str, PlaywrightBaseScraper] = {}
        
        # Domain to scraper mapping
        self._domain_map = {
            "amazon.com": "amazon",
            "amazon.co.uk": "amazon",
            "walmart.com": "walmart",
            "bestbuy.com": "bestbuy",
            "target.com": "target",
        }
    
    def _get_scraper(self, domain: str) -> Optional[PlaywrightBaseScraper]:
        """Get or create scraper for domain."""
        scraper_type = self._domain_map.get(domain)
        
        if not scraper_type:
            return None
        
        if scraper_type not in self._scrapers:
            if scraper_type == "amazon":
                from adam.intelligence.scrapers.amazon_playwright import AmazonPlaywrightScraper
                self._scrapers["amazon"] = AmazonPlaywrightScraper(
                    max_pages=10, headless=self.headless
                )
            elif scraper_type == "walmart":
                self._scrapers["walmart"] = WalmartPlaywrightScraper(headless=self.headless)
            elif scraper_type == "bestbuy":
                self._scrapers["bestbuy"] = BestBuyPlaywrightScraper(headless=self.headless)
            elif scraper_type == "target":
                self._scrapers["target"] = TargetPlaywrightScraper(headless=self.headless)
        
        return self._scrapers.get(scraper_type)
    
    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL."""
        parsed = urlparse(url)
        domain = parsed.netloc.replace("www.", "")
        return domain
    
    def _deduplicate_reviews(
        self, reviews: List[RawReview], similarity_threshold: float = 0.85
    ) -> Tuple[List[RawReview], int]:
        """Remove duplicate reviews based on text similarity."""
        if not reviews:
            return [], 0
        
        unique = []
        seen_hashes = set()
        duplicates = 0
        
        for review in reviews:
            # Quick hash check first
            text_hash = hashlib.md5(review.review_text[:100].lower().encode()).hexdigest()
            
            if text_hash in seen_hashes:
                duplicates += 1
                continue
            
            # Check similarity with existing reviews
            is_duplicate = False
            normalized = review.review_text.lower()[:200]
            
            for existing in unique[-20:]:  # Only check recent reviews for speed
                existing_norm = existing.review_text.lower()[:200]
                similarity = SequenceMatcher(None, normalized, existing_norm).ratio()
                
                if similarity >= similarity_threshold:
                    is_duplicate = True
                    duplicates += 1
                    break
            
            if not is_duplicate:
                unique.append(review)
                seen_hashes.add(text_hash)
        
        return unique, duplicates
    
    async def scrape_url(
        self,
        url: str,
        product_name: str,
        brand: Optional[str] = None,
        max_reviews: int = 50,
    ) -> ScraperResult:
        """Scrape reviews from a single URL."""
        domain = self._extract_domain(url)
        scraper = self._get_scraper(domain)
        
        if not scraper:
            return ScraperResult(
                source=ReviewSource.PRODUCT_PAGE,
                source_url=url,
                success=False,
                error_message=f"No scraper available for domain: {domain}",
            )
        
        return await scraper.scrape(
            product_url=url,
            product_name=product_name,
            brand=brand,
            max_reviews=max_reviews,
        )
    
    async def scrape_all_sources(
        self,
        product_name: str,
        product_urls: List[str],
        brand: Optional[str] = None,
        max_reviews_per_source: int = 50,
        deduplicate: bool = True,
    ) -> UnifiedScraperResult:
        """
        Scrape reviews from multiple URLs in parallel.
        
        Args:
            product_name: Product name
            product_urls: List of product URLs to scrape
            brand: Brand name
            max_reviews_per_source: Max reviews per source
            deduplicate: Whether to remove duplicates
            
        Returns:
            UnifiedScraperResult with all reviews
        """
        start_time = time.time()
        result = UnifiedScraperResult()
        
        if not product_urls:
            return result
        
        # Create scrape tasks
        tasks = []
        for url in product_urls:
            task = self.scrape_url(
                url=url,
                product_name=product_name,
                brand=brand,
                max_reviews=max_reviews_per_source,
            )
            tasks.append(task)
        
        # Execute in parallel
        scrape_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        all_reviews = []
        
        for url, scrape_result in zip(product_urls, scrape_results):
            domain = self._extract_domain(url)
            
            if isinstance(scrape_result, Exception):
                logger.error(f"Scraping {domain} failed with exception: {scrape_result}")
                result.sources_failed.append(domain)
                continue
            
            result.source_results[domain] = scrape_result
            
            if scrape_result.success:
                result.sources_succeeded.append(domain)
                all_reviews.extend(scrape_result.reviews)
                result.total_found += scrape_result.total_found
                
                # Capture product info from first successful source
                if not result.product_info.get("name") and scrape_result.product_name:
                    result.product_info["name"] = scrape_result.product_name
                if not result.product_info.get("brand") and scrape_result.product_brand:
                    result.product_info["brand"] = scrape_result.product_brand
            else:
                result.sources_failed.append(domain)
        
        # Deduplicate
        if deduplicate and all_reviews:
            unique_reviews, duplicates = self._deduplicate_reviews(all_reviews)
            result.reviews = unique_reviews
            result.unique_count = len(unique_reviews)
            result.duplicates_removed = duplicates
        else:
            result.reviews = all_reviews
            result.unique_count = len(all_reviews)
        
        result.scrape_duration_ms = (time.time() - start_time) * 1000
        
        logger.info(
            f"Unified scraping complete: {len(result.reviews)} unique reviews from "
            f"{len(result.sources_succeeded)} sources in {result.scrape_duration_ms:.0f}ms"
        )
        
        return result
    
    async def search_and_scrape(
        self,
        product_name: str,
        brand: Optional[str] = None,
        max_reviews_per_source: int = 50,
    ) -> UnifiedScraperResult:
        """
        Search for product across multiple platforms and scrape reviews.
        
        This is useful when you only have a product name, not URLs.
        
        Args:
            product_name: Product name to search for
            brand: Brand name
            max_reviews_per_source: Max reviews per source
            
        Returns:
            UnifiedScraperResult with all reviews
        """
        # Build search URLs for each platform
        search_term = quote(f"{brand} {product_name}" if brand else product_name)
        
        search_urls = [
            f"https://www.amazon.com/s?k={search_term}",
            f"https://www.walmart.com/search?q={search_term}",
        ]
        
        # For now, return empty - full implementation would:
        # 1. Search each platform
        # 2. Find the best matching product
        # 3. Scrape reviews from that product page
        
        logger.warning("search_and_scrape not fully implemented - provide direct URLs")
        return UnifiedScraperResult()
    
    async def close(self):
        """Close all scrapers."""
        for scraper in self._scrapers.values():
            await scraper.close()


# =============================================================================
# SINGLETON
# =============================================================================

_unified_scraper: Optional[UnifiedReviewScraper] = None


def get_unified_scraper(headless: bool = True) -> UnifiedReviewScraper:
    """Get singleton unified scraper."""
    global _unified_scraper
    if _unified_scraper is None:
        _unified_scraper = UnifiedReviewScraper(headless=headless)
    return _unified_scraper
