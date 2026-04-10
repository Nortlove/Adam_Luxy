# =============================================================================
# Enterprise Review Scraper
# Location: adam/intelligence/scrapers/enterprise_scraper.py
# =============================================================================

"""
Enterprise-Grade Multi-Site Review Scraper

This is the FOUNDATION of ADAM's intelligence. Target:
- 100,000+ products scraped
- 10,000,000+ reviews in corpus
- All 45 major US retailers covered

Architecture:
- Playwright for JavaScript-rendered pages
- Per-domain rate limiting with exponential backoff
- Retry logic with configurable attempts
- Cross-source deduplication
- Review pagination (ALL reviews, not just visible)
- Pre-analysis pipeline integration

Usage:
    scraper = EnterpriseReviewScraper()
    
    # Scrape single product
    result = await scraper.scrape_product("https://amazon.com/dp/B08N5WRWNW")
    
    # Scrape entire category
    products = await scraper.scrape_category("amazon.com", "Electronics/Headphones", max_products=1000)
    
    # Build corpus continuously
    await scraper.build_corpus(target_products=100000)
"""

import asyncio
import hashlib
import logging
import random
import re
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from difflib import SequenceMatcher
from typing import Any, AsyncGenerator, Dict, List, Optional, Set, Tuple
from urllib.parse import urlparse, urljoin, quote

from adam.intelligence.models.customer_intelligence import ReviewSource
from adam.intelligence.scrapers.base import (
    BaseReviewScraper,
    RawReview,
    ScraperResult,
)

logger = logging.getLogger(__name__)

# Check Playwright availability
try:
    from playwright.async_api import async_playwright, Browser, Page, TimeoutError as PlaywrightTimeout
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    logger.warning("Playwright not installed. Run: pip install playwright && playwright install chromium")


# =============================================================================
# CONFIGURATION
# =============================================================================

# User agents for rotation
USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
]

# Rate limits per domain (requests per minute, min delay, max delay)
RATE_LIMITS = {
    # Tier 1 - High volume, need careful rate limiting
    "amazon.com": {"rpm": 15, "delay_min": 3.0, "delay_max": 6.0, "retry_delay": 60},
    "walmart.com": {"rpm": 12, "delay_min": 3.0, "delay_max": 5.0, "retry_delay": 45},
    "target.com": {"rpm": 15, "delay_min": 2.0, "delay_max": 4.0, "retry_delay": 30},
    "bestbuy.com": {"rpm": 15, "delay_min": 2.0, "delay_max": 4.0, "retry_delay": 30},
    "costco.com": {"rpm": 10, "delay_min": 4.0, "delay_max": 7.0, "retry_delay": 60},
    "homedepot.com": {"rpm": 12, "delay_min": 3.0, "delay_max": 5.0, "retry_delay": 45},
    "lowes.com": {"rpm": 12, "delay_min": 3.0, "delay_max": 5.0, "retry_delay": 45},
    
    # Tier 2 - Important retailers
    "chewy.com": {"rpm": 15, "delay_min": 2.0, "delay_max": 4.0, "retry_delay": 30},
    "sephora.com": {"rpm": 12, "delay_min": 3.0, "delay_max": 5.0, "retry_delay": 45},
    "nike.com": {"rpm": 10, "delay_min": 4.0, "delay_max": 6.0, "retry_delay": 60},
    "nordstrom.com": {"rpm": 12, "delay_min": 3.0, "delay_max": 5.0, "retry_delay": 45},
    "rei.com": {"rpm": 15, "delay_min": 2.0, "delay_max": 4.0, "retry_delay": 30},
    "wayfair.com": {"rpm": 10, "delay_min": 4.0, "delay_max": 6.0, "retry_delay": 60},
    "etsy.com": {"rpm": 12, "delay_min": 3.0, "delay_max": 5.0, "retry_delay": 45},
    
    # Tier 3 - Additional retailers
    "macys.com": {"rpm": 15, "delay_min": 2.0, "delay_max": 4.0, "retry_delay": 30},
    "kohls.com": {"rpm": 15, "delay_min": 2.0, "delay_max": 4.0, "retry_delay": 30},
    "jcpenney.com": {"rpm": 15, "delay_min": 2.0, "delay_max": 4.0, "retry_delay": 30},
    "newegg.com": {"rpm": 12, "delay_min": 3.0, "delay_max": 5.0, "retry_delay": 45},
    "bhphotovideo.com": {"rpm": 15, "delay_min": 2.0, "delay_max": 4.0, "retry_delay": 30},
    "gamestop.com": {"rpm": 15, "delay_min": 2.0, "delay_max": 4.0, "retry_delay": 30},
    "zappos.com": {"rpm": 15, "delay_min": 2.0, "delay_max": 4.0, "retry_delay": 30},
    "ulta.com": {"rpm": 12, "delay_min": 3.0, "delay_max": 5.0, "retry_delay": 45},
    "dickssportinggoods.com": {"rpm": 15, "delay_min": 2.0, "delay_max": 4.0, "retry_delay": 30},
    "williams-sonoma.com": {"rpm": 12, "delay_min": 3.0, "delay_max": 5.0, "retry_delay": 45},
    "potterybarn.com": {"rpm": 12, "delay_min": 3.0, "delay_max": 5.0, "retry_delay": 45},
    "crateandbarrel.com": {"rpm": 12, "delay_min": 3.0, "delay_max": 5.0, "retry_delay": 45},
    "bedbathandbeyond.com": {"rpm": 15, "delay_min": 2.0, "delay_max": 4.0, "retry_delay": 30},
    "overstock.com": {"rpm": 15, "delay_min": 2.0, "delay_max": 4.0, "retry_delay": 30},
    
    # Default for unknown domains
    "default": {"rpm": 10, "delay_min": 3.0, "delay_max": 5.0, "retry_delay": 45},
}

# Top categories per retailer (from CSV analysis)
RETAILER_CATEGORIES = {
    "amazon.com": [
        "Electronics", "Home & Kitchen", "Clothing", "Books", "Beauty",
        "Health & Personal Care", "Sports & Outdoors", "Toys & Games",
        "Automotive", "Pet Supplies", "Office Products", "Tools & Home Improvement",
    ],
    "walmart.com": [
        "Electronics", "Home", "Clothing", "Grocery", "Toys",
        "Health & Beauty", "Sports & Outdoors", "Automotive", "Pets",
    ],
    "target.com": [
        "Electronics", "Home", "Clothing", "Beauty", "Baby",
        "Toys", "Sports & Outdoors", "Grocery",
    ],
    "bestbuy.com": [
        "TVs & Home Theater", "Computers & Tablets", "Cell Phones",
        "Audio", "Cameras", "Video Games", "Appliances", "Smart Home",
    ],
    "costco.com": [
        "Electronics", "Appliances", "Furniture", "Health & Beauty",
        "Grocery", "Office", "Clothing", "Jewelry",
    ],
    "homedepot.com": [
        "Appliances", "Tools", "Building Materials", "Flooring",
        "Paint", "Outdoor Living", "Bath", "Lighting", "Plumbing",
    ],
    "lowes.com": [
        "Appliances", "Tools", "Building Supplies", "Flooring",
        "Paint", "Outdoor Living", "Bathroom", "Lighting",
    ],
    "chewy.com": [
        "Dog Food", "Cat Food", "Pet Supplies", "Pet Pharmacy",
        "Dog Treats", "Cat Litter", "Aquarium", "Bird",
    ],
    "sephora.com": [
        "Makeup", "Skincare", "Fragrance", "Hair",
        "Tools & Brushes", "Bath & Body", "Men",
    ],
    "nike.com": [
        "Running", "Basketball", "Training", "Lifestyle",
        "Football", "Soccer", "Golf", "Tennis",
    ],
}


# =============================================================================
# RATE LIMITER
# =============================================================================

class RateLimiter:
    """
    Per-domain rate limiter with exponential backoff.
    
    Tracks request times per domain and enforces rate limits.
    Implements exponential backoff on rate limit hits.
    """
    
    def __init__(self):
        self._last_request: Dict[str, float] = {}
        self._request_count: Dict[str, int] = {}
        self._window_start: Dict[str, float] = {}
        self._backoff_until: Dict[str, float] = {}
        self._consecutive_failures: Dict[str, int] = {}
    
    def _get_domain(self, url: str) -> str:
        """Extract domain from URL."""
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        # Remove www. prefix
        if domain.startswith("www."):
            domain = domain[4:]
        return domain
    
    def _get_config(self, domain: str) -> dict:
        """Get rate limit config for domain."""
        return RATE_LIMITS.get(domain, RATE_LIMITS["default"])
    
    async def wait_for_slot(self, url: str) -> None:
        """
        Wait until we can make a request to this domain.
        
        Respects rate limits and backoff periods.
        """
        domain = self._get_domain(url)
        config = self._get_config(domain)
        
        now = time.time()
        
        # Check if we're in backoff period
        backoff_until = self._backoff_until.get(domain, 0)
        if now < backoff_until:
            wait_time = backoff_until - now
            logger.warning(f"Rate limited for {domain}, waiting {wait_time:.1f}s")
            await asyncio.sleep(wait_time)
            now = time.time()
        
        # Check if we need to reset the window
        window_start = self._window_start.get(domain, 0)
        if now - window_start > 60:
            self._window_start[domain] = now
            self._request_count[domain] = 0
        
        # Check if we've hit the rate limit
        request_count = self._request_count.get(domain, 0)
        rpm = config["rpm"]
        if request_count >= rpm:
            # Wait until window resets
            wait_time = 60 - (now - window_start)
            if wait_time > 0:
                logger.info(f"Rate limit reached for {domain}, waiting {wait_time:.1f}s")
                await asyncio.sleep(wait_time)
            self._window_start[domain] = time.time()
            self._request_count[domain] = 0
        
        # Enforce minimum delay between requests
        last_request = self._last_request.get(domain, 0)
        delay = random.uniform(config["delay_min"], config["delay_max"])
        elapsed = now - last_request
        if elapsed < delay:
            await asyncio.sleep(delay - elapsed)
    
    def record_request(self, url: str) -> None:
        """Record that a request was made."""
        domain = self._get_domain(url)
        now = time.time()
        self._last_request[domain] = now
        self._request_count[domain] = self._request_count.get(domain, 0) + 1
        self._consecutive_failures[domain] = 0
    
    def record_failure(self, url: str, is_rate_limit: bool = False) -> None:
        """Record a failed request, possibly triggering backoff."""
        domain = self._get_domain(url)
        config = self._get_config(domain)
        
        failures = self._consecutive_failures.get(domain, 0) + 1
        self._consecutive_failures[domain] = failures
        
        if is_rate_limit or failures >= 3:
            # Exponential backoff
            backoff = config["retry_delay"] * (2 ** min(failures - 1, 5))
            self._backoff_until[domain] = time.time() + backoff
            logger.warning(f"Backing off {domain} for {backoff:.0f}s after {failures} failures")


# =============================================================================
# DEDUPLICATION ENGINE
# =============================================================================

class DeduplicationEngine:
    """
    Cross-source review deduplication using fingerprinting and similarity.
    
    Reviews from different sources for the same product may be duplicates
    (e.g., syndicated reviews). This engine identifies and removes them.
    """
    
    def __init__(self, similarity_threshold: float = 0.85):
        self.similarity_threshold = similarity_threshold
        self._seen_fingerprints: Set[str] = set()
        self._seen_texts: List[str] = []
    
    def _fingerprint(self, review: RawReview) -> str:
        """Generate a fingerprint for a review."""
        # Normalize text
        text = review.review_text.lower().strip()
        text = re.sub(r'\s+', ' ', text)
        
        # Include rating and approximate length
        key = f"{text[:100]}|{review.rating}|{len(text)//50}"
        return hashlib.md5(key.encode()).hexdigest()
    
    def _text_similarity(self, text1: str, text2: str) -> float:
        """Calculate text similarity using SequenceMatcher."""
        # Normalize
        t1 = text1.lower().strip()[:500]
        t2 = text2.lower().strip()[:500]
        return SequenceMatcher(None, t1, t2).ratio()
    
    def is_duplicate(self, review: RawReview) -> bool:
        """Check if a review is a duplicate."""
        fingerprint = self._fingerprint(review)
        
        # Exact fingerprint match
        if fingerprint in self._seen_fingerprints:
            return True
        
        # Similarity check against recent reviews
        review_text = review.review_text
        for seen_text in self._seen_texts[-1000:]:  # Check last 1000
            if self._text_similarity(review_text, seen_text) > self.similarity_threshold:
                return True
        
        return False
    
    def add_review(self, review: RawReview) -> None:
        """Add a review to the deduplication index."""
        fingerprint = self._fingerprint(review)
        self._seen_fingerprints.add(fingerprint)
        self._seen_texts.append(review.review_text)
        
        # Keep memory bounded
        if len(self._seen_texts) > 10000:
            self._seen_texts = self._seen_texts[-5000:]
    
    def deduplicate(self, reviews: List[RawReview]) -> List[RawReview]:
        """Deduplicate a list of reviews."""
        unique = []
        for review in reviews:
            if not self.is_duplicate(review):
                self.add_review(review)
                unique.append(review)
        return unique


# =============================================================================
# BASE ENTERPRISE SCRAPER
# =============================================================================

class EnterpriseBaseScraper(ABC):
    """
    Base class for enterprise-grade Playwright scrapers.
    
    Provides:
    - Browser management with connection pooling
    - Realistic page creation with anti-detection measures
    - Rate limiting integration
    - Retry logic with exponential backoff
    - Pagination support
    """
    
    DOMAIN: str = "unknown"
    SOURCE_NAME: str = "Unknown"
    
    def __init__(
        self,
        rate_limiter: RateLimiter,
        headless: bool = True,
        max_retries: int = 3,
    ):
        self.rate_limiter = rate_limiter
        self.headless = headless
        self.max_retries = max_retries
        self._playwright = None
        self._browser: Optional[Browser] = None
    
    async def _get_browser(self) -> Browser:
        """Get or create browser instance."""
        if not PLAYWRIGHT_AVAILABLE:
            raise ImportError("Playwright not installed. Run: pip install playwright && playwright install chromium")
        
        if self._browser is None:
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(
                headless=self.headless,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--no-sandbox',
                ]
            )
        
        return self._browser
    
    async def _create_page(self) -> Page:
        """Create a new page with realistic settings and anti-detection."""
        browser = await self._get_browser()
        
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent=random.choice(USER_AGENTS),
            locale='en-US',
            timezone_id='America/New_York',
        )
        
        page = await context.new_page()
        
        # Anti-detection: Override navigator.webdriver
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
        """)
        
        return page
    
    async def _scroll_page(self, page: Page, scroll_count: int = 5) -> None:
        """Scroll page to load dynamic content."""
        for i in range(scroll_count):
            await page.evaluate(f"window.scrollTo(0, document.body.scrollHeight * {(i+1)/(scroll_count+1)})")
            await asyncio.sleep(0.3 + random.uniform(0, 0.3))
    
    async def _safe_goto(self, page: Page, url: str, timeout: int = 30000) -> bool:
        """Navigate to URL with rate limiting and error handling."""
        await self.rate_limiter.wait_for_slot(url)
        
        for attempt in range(self.max_retries):
            try:
                response = await page.goto(url, timeout=timeout, wait_until="domcontentloaded")
                self.rate_limiter.record_request(url)
                
                if response and response.status == 429:
                    self.rate_limiter.record_failure(url, is_rate_limit=True)
                    continue
                
                if response and response.status >= 400:
                    logger.warning(f"HTTP {response.status} for {url}")
                    self.rate_limiter.record_failure(url)
                    continue
                
                return True
                
            except PlaywrightTimeout:
                logger.warning(f"Timeout loading {url} (attempt {attempt + 1})")
                self.rate_limiter.record_failure(url)
            except Exception as e:
                logger.error(f"Error loading {url}: {e}")
                self.rate_limiter.record_failure(url)
            
            if attempt < self.max_retries - 1:
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
        
        return False
    
    @abstractmethod
    async def scrape_product(
        self,
        product_url: str,
        max_reviews: int = 500,
    ) -> ScraperResult:
        """Scrape all reviews for a single product."""
        pass
    
    @abstractmethod
    async def get_category_products(
        self,
        category: str,
        max_products: int = 100,
    ) -> List[str]:
        """Get product URLs from a category page."""
        pass
    
    async def close(self) -> None:
        """Close browser and clean up resources."""
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None


# =============================================================================
# AMAZON ENTERPRISE SCRAPER
# =============================================================================

class AmazonEnterpriseScraper(EnterpriseBaseScraper):
    """
    Enterprise-grade Amazon review scraper.
    
    Features:
    - Full review pagination (not just first page)
    - Handles lazy-loaded reviews
    - Extracts all review metadata
    - Robust error handling
    """
    
    DOMAIN = "amazon.com"
    SOURCE_NAME = "Amazon"
    
    def _extract_asin(self, url: str) -> Optional[str]:
        """Extract ASIN from Amazon URL."""
        patterns = [
            r'/dp/([A-Z0-9]{10})',
            r'/product/([A-Z0-9]{10})',
            r'/gp/product/([A-Z0-9]{10})',
            r'asin=([A-Z0-9]{10})',
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None
    
    async def scrape_product(
        self,
        product_url: str,
        max_reviews: int = 500,
    ) -> ScraperResult:
        """Scrape all reviews for an Amazon product."""
        start_time = time.time()
        reviews = []
        
        asin = self._extract_asin(product_url)
        if not asin:
            return ScraperResult(
                source=ReviewSource.AMAZON,
                source_url=product_url,
                success=False,
                error_message="Could not extract ASIN from URL",
            )
        
        page = await self._create_page()
        
        try:
            # First, get product info from main page
            product_info = await self._get_product_info(page, product_url)
            
            # Then scrape reviews from all-reviews page
            reviews_url = f"https://www.amazon.com/product-reviews/{asin}/ref=cm_cr_dp_d_show_all_btm?ie=UTF8&reviewerType=all_reviews"
            
            page_num = 1
            while len(reviews) < max_reviews:
                paged_url = f"{reviews_url}&pageNumber={page_num}"
                
                if not await self._safe_goto(page, paged_url):
                    break
                
                await self._scroll_page(page, scroll_count=3)
                await asyncio.sleep(1)
                
                page_reviews = await self._extract_reviews(page, asin)
                
                if not page_reviews:
                    break
                
                reviews.extend(page_reviews)
                logger.info(f"Amazon {asin}: scraped page {page_num}, total reviews: {len(reviews)}")
                
                # Check for next page
                has_next = await page.query_selector('li.a-last:not(.a-disabled) a')
                if not has_next:
                    break
                
                page_num += 1
                
                # Safety limit
                if page_num > 50:
                    break
            
            return ScraperResult(
                source=ReviewSource.AMAZON,
                source_url=product_url,
                reviews=reviews[:max_reviews],
                total_found=len(reviews),
                success=True,
                scrape_duration_ms=(time.time() - start_time) * 1000,
                **product_info,
            )
            
        except Exception as e:
            logger.error(f"Error scraping Amazon {product_url}: {e}")
            return ScraperResult(
                source=ReviewSource.AMAZON,
                source_url=product_url,
                reviews=reviews,
                total_found=len(reviews),
                success=False,
                error_message=str(e),
                scrape_duration_ms=(time.time() - start_time) * 1000,
            )
        finally:
            await page.context.close()
    
    async def _get_product_info(self, page: Page, url: str) -> dict:
        """Extract product info from main product page."""
        info = {}
        
        if not await self._safe_goto(page, url):
            return info
        
        try:
            # Product name
            title_el = await page.query_selector('#productTitle')
            if title_el:
                info['product_name'] = (await title_el.inner_text()).strip()
            
            # Brand
            brand_el = await page.query_selector('#bylineInfo')
            if brand_el:
                brand_text = await brand_el.inner_text()
                info['product_brand'] = brand_text.replace('Visit the ', '').replace(' Store', '').strip()
            
            # Price
            price_el = await page.query_selector('.a-price .a-offscreen')
            if price_el:
                info['product_price'] = await price_el.inner_text()
            
            # Description
            desc_el = await page.query_selector('#productDescription')
            if desc_el:
                info['product_description'] = (await desc_el.inner_text()).strip()[:1000]
            
        except Exception as e:
            logger.warning(f"Error extracting product info: {e}")
        
        return info
    
    async def _extract_reviews(self, page: Page, asin: str) -> List[RawReview]:
        """Extract reviews from current page."""
        reviews = []
        
        review_elements = await page.query_selector_all('[data-hook="review"]')
        
        for elem in review_elements:
            try:
                review_id = await elem.get_attribute('id') or f"amzn_{asin}_{len(reviews)}"
                
                # Rating
                rating = 3.0
                rating_el = await elem.query_selector('[data-hook="review-star-rating"] span, [data-hook="cmps-review-star-rating"] span')
                if rating_el:
                    rating_text = await rating_el.inner_text()
                    match = re.search(r'(\d+(?:\.\d+)?)', rating_text)
                    if match:
                        rating = float(match.group(1))
                
                # Title
                title = ""
                title_el = await elem.query_selector('[data-hook="review-title"] span:last-child')
                if title_el:
                    title = (await title_el.inner_text()).strip()
                
                # Body
                body = ""
                body_el = await elem.query_selector('[data-hook="review-body"] span')
                if body_el:
                    body = (await body_el.inner_text()).strip()
                
                if not body:
                    continue
                
                # Date
                review_date = None
                date_el = await elem.query_selector('[data-hook="review-date"]')
                if date_el:
                    date_text = await date_el.inner_text()
                    # Parse "Reviewed in the United States on January 15, 2024"
                    match = re.search(r'on (.+)$', date_text)
                    if match:
                        try:
                            review_date = datetime.strptime(match.group(1), '%B %d, %Y')
                        except ValueError:
                            pass
                
                # Verified
                verified = False
                verified_el = await elem.query_selector('[data-hook="avp-badge"]')
                if verified_el:
                    verified = True
                
                # Helpful votes
                helpful_votes = 0
                helpful_el = await elem.query_selector('[data-hook="helpful-vote-statement"]')
                if helpful_el:
                    helpful_text = await helpful_el.inner_text()
                    match = re.search(r'(\d+)', helpful_text)
                    if match:
                        helpful_votes = int(match.group(1))
                
                # Reviewer name
                reviewer_name = None
                name_el = await elem.query_selector('.a-profile-name')
                if name_el:
                    reviewer_name = await name_el.inner_text()
                
                reviews.append(RawReview(
                    review_id=review_id,
                    source=ReviewSource.AMAZON,
                    source_url=f"https://www.amazon.com/dp/{asin}",
                    review_text=f"{title}\n\n{body}" if title else body,
                    rating=rating,
                    review_date=review_date,
                    reviewer_name=reviewer_name,
                    verified_purchase=verified,
                    helpful_votes=helpful_votes,
                ))
                
            except Exception as e:
                logger.warning(f"Error extracting review: {e}")
                continue
        
        return reviews
    
    async def get_category_products(
        self,
        category: str,
        max_products: int = 100,
    ) -> List[str]:
        """Get product URLs from Amazon category/search."""
        products = []
        page = await self._create_page()
        
        try:
            # Use search to find products in category
            search_url = f"https://www.amazon.com/s?k={quote(category)}"
            
            page_num = 1
            while len(products) < max_products:
                paged_url = f"{search_url}&page={page_num}"
                
                if not await self._safe_goto(page, paged_url):
                    break
                
                await self._scroll_page(page)
                
                # Extract product links
                links = await page.query_selector_all('[data-asin]:not([data-asin=""]) h2 a')
                
                for link in links:
                    href = await link.get_attribute('href')
                    if href:
                        full_url = urljoin("https://www.amazon.com", href)
                        asin = self._extract_asin(full_url)
                        if asin and full_url not in products:
                            products.append(full_url)
                            
                            if len(products) >= max_products:
                                break
                
                # Check for next page
                next_btn = await page.query_selector('.s-pagination-next:not(.s-pagination-disabled)')
                if not next_btn:
                    break
                
                page_num += 1
                
                if page_num > 20:  # Safety limit
                    break
                    
        except Exception as e:
            logger.error(f"Error getting Amazon category products: {e}")
        finally:
            await page.context.close()
        
        return products


# =============================================================================
# WALMART ENTERPRISE SCRAPER
# =============================================================================

class WalmartEnterpriseScraper(EnterpriseBaseScraper):
    """
    Enterprise-grade Walmart review scraper.
    
    Walmart uses a React-based frontend with reviews loaded via API.
    """
    
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
    
    async def scrape_product(
        self,
        product_url: str,
        max_reviews: int = 500,
    ) -> ScraperResult:
        """Scrape all reviews for a Walmart product."""
        start_time = time.time()
        reviews = []
        
        product_id = self._extract_product_id(product_url)
        if not product_id:
            return ScraperResult(
                source=ReviewSource.WALMART,
                source_url=product_url,
                success=False,
                error_message="Could not extract product ID from URL",
            )
        
        page = await self._create_page()
        
        try:
            # Navigate to product page
            if not await self._safe_goto(page, product_url):
                return ScraperResult(
                    source=ReviewSource.WALMART,
                    source_url=product_url,
                    success=False,
                    error_message="Failed to load product page",
                )
            
            await self._scroll_page(page, scroll_count=5)
            
            # Extract product info
            product_info = await self._get_product_info(page)
            
            # Click "See all reviews" if available
            try:
                see_all = await page.query_selector('[data-testid="see-all-reviews"]')
                if see_all:
                    await see_all.click()
                    await asyncio.sleep(2)
            except Exception:
                pass
            
            # Extract reviews from current page
            page_reviews = await self._extract_reviews(page, product_id)
            reviews.extend(page_reviews)
            
            # Paginate through reviews
            page_num = 1
            while len(reviews) < max_reviews and page_num < 20:
                # Try to find and click next page
                next_btn = await page.query_selector('[aria-label="Next Page"]')
                if not next_btn:
                    break
                
                try:
                    await next_btn.click()
                    await asyncio.sleep(2)
                    
                    new_reviews = await self._extract_reviews(page, product_id)
                    if not new_reviews:
                        break
                    
                    reviews.extend(new_reviews)
                    page_num += 1
                    logger.info(f"Walmart {product_id}: scraped page {page_num}, total: {len(reviews)}")
                except Exception:
                    break
            
            return ScraperResult(
                source=ReviewSource.WALMART,
                source_url=product_url,
                reviews=reviews[:max_reviews],
                total_found=len(reviews),
                success=True,
                scrape_duration_ms=(time.time() - start_time) * 1000,
                **product_info,
            )
            
        except Exception as e:
            logger.error(f"Error scraping Walmart {product_url}: {e}")
            return ScraperResult(
                source=ReviewSource.WALMART,
                source_url=product_url,
                reviews=reviews,
                success=False,
                error_message=str(e),
                scrape_duration_ms=(time.time() - start_time) * 1000,
            )
        finally:
            await page.context.close()
    
    async def _get_product_info(self, page: Page) -> dict:
        """Extract product info from page."""
        info = {}
        try:
            title_el = await page.query_selector('h1[itemprop="name"]')
            if title_el:
                info['product_name'] = (await title_el.inner_text()).strip()
            
            price_el = await page.query_selector('[itemprop="price"]')
            if price_el:
                info['product_price'] = await price_el.inner_text()
        except Exception as e:
            logger.warning(f"Error getting Walmart product info: {e}")
        return info
    
    async def _extract_reviews(self, page: Page, product_id: str) -> List[RawReview]:
        """Extract reviews from current page."""
        reviews = []
        
        review_elements = await page.query_selector_all('[data-testid="review-card"]')
        
        for elem in review_elements:
            try:
                # Rating
                rating = 3.0
                stars = await elem.query_selector_all('[data-testid="stars"] svg[fill="#ffc220"]')
                if stars:
                    rating = len(stars)
                
                # Title
                title = ""
                title_el = await elem.query_selector('h3')
                if title_el:
                    title = (await title_el.inner_text()).strip()
                
                # Body
                body = ""
                body_el = await elem.query_selector('[data-testid="review-text"]')
                if body_el:
                    body = (await body_el.inner_text()).strip()
                
                if not body:
                    continue
                
                # Verified
                verified = False
                verified_el = await elem.query_selector('[data-testid="verified-badge"]')
                if verified_el:
                    verified = True
                
                # Helpful votes
                helpful_votes = 0
                helpful_el = await elem.query_selector('[data-testid="helpful-count"]')
                if helpful_el:
                    helpful_text = await helpful_el.inner_text()
                    match = re.search(r'(\d+)', helpful_text)
                    if match:
                        helpful_votes = int(match.group(1))
                
                review_id = f"wmt_{product_id}_{len(reviews)}_{hashlib.md5(body[:50].encode()).hexdigest()[:8]}"
                
                reviews.append(RawReview(
                    review_id=review_id,
                    source=ReviewSource.WALMART,
                    source_url=f"https://www.walmart.com/ip/{product_id}",
                    review_text=f"{title}\n\n{body}" if title else body,
                    rating=float(rating),
                    verified_purchase=verified,
                    helpful_votes=helpful_votes,
                ))
            except Exception as e:
                logger.warning(f"Error extracting Walmart review: {e}")
                continue
        
        return reviews
    
    async def get_category_products(
        self,
        category: str,
        max_products: int = 100,
    ) -> List[str]:
        """Get product URLs from Walmart search."""
        products = []
        page = await self._create_page()
        
        try:
            search_url = f"https://www.walmart.com/search?q={quote(category)}"
            
            if not await self._safe_goto(page, search_url):
                return products
            
            await self._scroll_page(page)
            
            # Extract product links
            links = await page.query_selector_all('[data-item-id] a[href*="/ip/"]')
            
            for link in links:
                if len(products) >= max_products:
                    break
                href = await link.get_attribute('href')
                if href:
                    full_url = urljoin("https://www.walmart.com", href)
                    if full_url not in products:
                        products.append(full_url)
            
        except Exception as e:
            logger.error(f"Error getting Walmart category products: {e}")
        finally:
            await page.context.close()
        
        return products


# =============================================================================
# BESTBUY ENTERPRISE SCRAPER
# =============================================================================

class BestBuyEnterpriseScraper(EnterpriseBaseScraper):
    """Enterprise-grade BestBuy review scraper."""
    
    DOMAIN = "bestbuy.com"
    SOURCE_NAME = "BestBuy"
    
    def _extract_sku(self, url: str) -> Optional[str]:
        """Extract SKU from BestBuy URL."""
        # Pattern: bestbuy.com/site/product-name/1234567.p
        match = re.search(r'/(\d{7})\.p', url)
        if match:
            return match.group(1)
        # Pattern: skuId=1234567
        match = re.search(r'skuId=(\d+)', url)
        if match:
            return match.group(1)
        return None
    
    async def scrape_product(
        self,
        product_url: str,
        max_reviews: int = 500,
    ) -> ScraperResult:
        """Scrape reviews from BestBuy product."""
        start_time = time.time()
        reviews = []
        
        sku = self._extract_sku(product_url)
        if not sku:
            return ScraperResult(
                source=ReviewSource.BESTBUY,
                source_url=product_url,
                success=False,
                error_message="Could not extract SKU from URL",
            )
        
        page = await self._create_page()
        
        try:
            # BestBuy has a dedicated reviews page
            reviews_url = f"https://www.bestbuy.com/site/reviews/{sku}?variant=A"
            
            if not await self._safe_goto(page, reviews_url):
                # Fallback to product page
                if not await self._safe_goto(page, product_url):
                    return ScraperResult(
                        source=ReviewSource.BESTBUY,
                        source_url=product_url,
                        success=False,
                        error_message="Failed to load page",
                    )
            
            await self._scroll_page(page, scroll_count=5)
            
            # Extract reviews
            page_num = 1
            while len(reviews) < max_reviews and page_num <= 20:
                page_reviews = await self._extract_reviews(page, sku)
                
                if not page_reviews:
                    break
                
                reviews.extend(page_reviews)
                logger.info(f"BestBuy {sku}: scraped page {page_num}, total: {len(reviews)}")
                
                # Try to go to next page
                next_btn = await page.query_selector('a[aria-label="Next"]')
                if not next_btn:
                    break
                
                try:
                    await next_btn.click()
                    await asyncio.sleep(2)
                    page_num += 1
                except Exception:
                    break
            
            return ScraperResult(
                source=ReviewSource.BESTBUY,
                source_url=product_url,
                reviews=reviews[:max_reviews],
                total_found=len(reviews),
                success=True,
                scrape_duration_ms=(time.time() - start_time) * 1000,
            )
            
        except Exception as e:
            logger.error(f"Error scraping BestBuy {product_url}: {e}")
            return ScraperResult(
                source=ReviewSource.BESTBUY,
                source_url=product_url,
                reviews=reviews,
                success=False,
                error_message=str(e),
            )
        finally:
            await page.context.close()
    
    async def _extract_reviews(self, page: Page, sku: str) -> List[RawReview]:
        """Extract reviews from current page."""
        reviews = []
        
        review_elements = await page.query_selector_all('.review-item')
        
        for elem in review_elements:
            try:
                # Rating
                rating = 3.0
                rating_el = await elem.query_selector('.c-review-average')
                if rating_el:
                    rating_text = await rating_el.inner_text()
                    match = re.search(r'(\d+(?:\.\d+)?)', rating_text)
                    if match:
                        rating = float(match.group(1))
                
                # Title
                title = ""
                title_el = await elem.query_selector('.review-title')
                if title_el:
                    title = (await title_el.inner_text()).strip()
                
                # Body
                body = ""
                body_el = await elem.query_selector('.review-content p')
                if body_el:
                    body = (await body_el.inner_text()).strip()
                
                if not body:
                    continue
                
                # Verified
                verified = False
                verified_el = await elem.query_selector('.verified-purchaser')
                if verified_el:
                    verified = True
                
                review_id = f"bby_{sku}_{len(reviews)}_{hashlib.md5(body[:50].encode()).hexdigest()[:8]}"
                
                reviews.append(RawReview(
                    review_id=review_id,
                    source=ReviewSource.BESTBUY,
                    source_url=f"https://www.bestbuy.com/site/{sku}.p",
                    review_text=f"{title}\n\n{body}" if title else body,
                    rating=rating,
                    verified_purchase=verified,
                ))
            except Exception as e:
                logger.warning(f"Error extracting BestBuy review: {e}")
                continue
        
        return reviews
    
    async def get_category_products(
        self,
        category: str,
        max_products: int = 100,
    ) -> List[str]:
        """Get product URLs from BestBuy search."""
        products = []
        page = await self._create_page()
        
        try:
            search_url = f"https://www.bestbuy.com/site/searchpage.jsp?st={quote(category)}"
            
            if not await self._safe_goto(page, search_url):
                return products
            
            await self._scroll_page(page)
            
            links = await page.query_selector_all('a.image-link[href*=".p?"]')
            
            for link in links:
                if len(products) >= max_products:
                    break
                href = await link.get_attribute('href')
                if href:
                    full_url = urljoin("https://www.bestbuy.com", href)
                    if full_url not in products:
                        products.append(full_url)
            
        except Exception as e:
            logger.error(f"Error getting BestBuy category products: {e}")
        finally:
            await page.context.close()
        
        return products


# =============================================================================
# TARGET ENTERPRISE SCRAPER
# =============================================================================

class TargetEnterpriseScraper(EnterpriseBaseScraper):
    """Enterprise-grade Target review scraper."""
    
    DOMAIN = "target.com"
    SOURCE_NAME = "Target"
    
    def _extract_tcin(self, url: str) -> Optional[str]:
        """Extract TCIN from Target URL."""
        # Pattern: target.com/p/product-name/-/A-12345678
        match = re.search(r'/A-(\d+)', url)
        if match:
            return match.group(1)
        return None
    
    async def scrape_product(
        self,
        product_url: str,
        max_reviews: int = 500,
    ) -> ScraperResult:
        """Scrape reviews from Target product."""
        start_time = time.time()
        reviews = []
        
        tcin = self._extract_tcin(product_url)
        if not tcin:
            return ScraperResult(
                source=ReviewSource.TARGET,
                source_url=product_url,
                success=False,
                error_message="Could not extract TCIN from URL",
            )
        
        page = await self._create_page()
        
        try:
            if not await self._safe_goto(page, product_url):
                return ScraperResult(
                    source=ReviewSource.TARGET,
                    source_url=product_url,
                    success=False,
                    error_message="Failed to load page",
                )
            
            await self._scroll_page(page, scroll_count=5)
            
            # Click to expand reviews section
            try:
                reviews_section = await page.query_selector('[data-test="reviews-section"]')
                if reviews_section:
                    await reviews_section.scroll_into_view_if_needed()
                    await asyncio.sleep(1)
            except Exception:
                pass
            
            # Extract reviews
            page_reviews = await self._extract_reviews(page, tcin)
            reviews.extend(page_reviews)
            
            # Load more reviews
            while len(reviews) < max_reviews:
                load_more = await page.query_selector('[data-test="load-more-reviews"]')
                if not load_more:
                    break
                
                try:
                    await load_more.click()
                    await asyncio.sleep(2)
                    
                    new_reviews = await self._extract_reviews(page, tcin)
                    new_count = len(new_reviews) - len(reviews)
                    if new_count <= 0:
                        break
                    
                    reviews = new_reviews
                    logger.info(f"Target {tcin}: loaded more, total: {len(reviews)}")
                except Exception:
                    break
            
            return ScraperResult(
                source=ReviewSource.TARGET,
                source_url=product_url,
                reviews=reviews[:max_reviews],
                total_found=len(reviews),
                success=True,
                scrape_duration_ms=(time.time() - start_time) * 1000,
            )
            
        except Exception as e:
            logger.error(f"Error scraping Target {product_url}: {e}")
            return ScraperResult(
                source=ReviewSource.TARGET,
                source_url=product_url,
                reviews=reviews,
                success=False,
                error_message=str(e),
            )
        finally:
            await page.context.close()
    
    async def _extract_reviews(self, page: Page, tcin: str) -> List[RawReview]:
        """Extract reviews from current page."""
        reviews = []
        
        review_elements = await page.query_selector_all('[data-test="review-card"]')
        
        for elem in review_elements:
            try:
                # Rating
                rating = 3.0
                rating_el = await elem.query_selector('[data-test="ratings"]')
                if rating_el:
                    rating_text = await rating_el.get_attribute('aria-label')
                    if rating_text:
                        match = re.search(r'(\d+(?:\.\d+)?)', rating_text)
                        if match:
                            rating = float(match.group(1))
                
                # Title
                title = ""
                title_el = await elem.query_selector('h4')
                if title_el:
                    title = (await title_el.inner_text()).strip()
                
                # Body
                body = ""
                body_el = await elem.query_selector('[data-test="review-text"]')
                if body_el:
                    body = (await body_el.inner_text()).strip()
                
                if not body:
                    continue
                
                review_id = f"tgt_{tcin}_{len(reviews)}_{hashlib.md5(body[:50].encode()).hexdigest()[:8]}"
                
                reviews.append(RawReview(
                    review_id=review_id,
                    source=ReviewSource.TARGET,
                    source_url=f"https://www.target.com/p/-/A-{tcin}",
                    review_text=f"{title}\n\n{body}" if title else body,
                    rating=rating,
                ))
            except Exception as e:
                logger.warning(f"Error extracting Target review: {e}")
                continue
        
        return reviews
    
    async def get_category_products(
        self,
        category: str,
        max_products: int = 100,
    ) -> List[str]:
        """Get product URLs from Target search."""
        products = []
        page = await self._create_page()
        
        try:
            search_url = f"https://www.target.com/s?searchTerm={quote(category)}"
            
            if not await self._safe_goto(page, search_url):
                return products
            
            await self._scroll_page(page)
            
            links = await page.query_selector_all('a[href*="/p/"][href*="/-/A-"]')
            
            for link in links:
                if len(products) >= max_products:
                    break
                href = await link.get_attribute('href')
                if href:
                    full_url = urljoin("https://www.target.com", href)
                    if full_url not in products:
                        products.append(full_url)
            
        except Exception as e:
            logger.error(f"Error getting Target category products: {e}")
        finally:
            await page.context.close()
        
        return products


# =============================================================================
# HOME DEPOT ENTERPRISE SCRAPER
# =============================================================================

class HomeDepotEnterpriseScraper(EnterpriseBaseScraper):
    """Enterprise-grade Home Depot review scraper."""
    
    DOMAIN = "homedepot.com"
    SOURCE_NAME = "Home Depot"
    
    def _extract_product_id(self, url: str) -> Optional[str]:
        """Extract product ID from Home Depot URL."""
        # Pattern: homedepot.com/p/Product-Name/123456789
        match = re.search(r'/p/[^/]+/(\d+)', url)
        if match:
            return match.group(1)
        return None
    
    async def scrape_product(
        self,
        product_url: str,
        max_reviews: int = 500,
    ) -> ScraperResult:
        """Scrape reviews from Home Depot product."""
        start_time = time.time()
        reviews = []
        
        product_id = self._extract_product_id(product_url)
        if not product_id:
            return ScraperResult(
                source=ReviewSource.PRODUCT_PAGE,
                source_url=product_url,
                success=False,
                error_message="Could not extract product ID from URL",
            )
        
        page = await self._create_page()
        
        try:
            if not await self._safe_goto(page, product_url):
                return ScraperResult(
                    source=ReviewSource.PRODUCT_PAGE,
                    source_url=product_url,
                    success=False,
                    error_message="Failed to load page",
                )
            
            await self._scroll_page(page, scroll_count=8)
            
            # Extract reviews
            reviews = await self._extract_reviews(page, product_id)
            
            return ScraperResult(
                source=ReviewSource.PRODUCT_PAGE,
                source_url=product_url,
                reviews=reviews[:max_reviews],
                total_found=len(reviews),
                success=True,
                scrape_duration_ms=(time.time() - start_time) * 1000,
            )
            
        except Exception as e:
            logger.error(f"Error scraping Home Depot {product_url}: {e}")
            return ScraperResult(
                source=ReviewSource.PRODUCT_PAGE,
                source_url=product_url,
                reviews=reviews,
                success=False,
                error_message=str(e),
            )
        finally:
            await page.context.close()
    
    async def _extract_reviews(self, page: Page, product_id: str) -> List[RawReview]:
        """Extract reviews from page."""
        reviews = []
        
        review_elements = await page.query_selector_all('.review-item, [data-component="ReviewItem"]')
        
        for elem in review_elements:
            try:
                # Rating
                rating = 3.0
                rating_el = await elem.query_selector('[class*="stars"]')
                if rating_el:
                    style = await rating_el.get_attribute('style')
                    if style:
                        match = re.search(r'width:\s*(\d+)', style)
                        if match:
                            rating = float(match.group(1)) / 20  # Convert percentage to 1-5
                
                # Body
                body = ""
                body_el = await elem.query_selector('.review-content, [class*="review-text"]')
                if body_el:
                    body = (await body_el.inner_text()).strip()
                
                if not body:
                    continue
                
                review_id = f"hd_{product_id}_{len(reviews)}_{hashlib.md5(body[:50].encode()).hexdigest()[:8]}"
                
                reviews.append(RawReview(
                    review_id=review_id,
                    source=ReviewSource.PRODUCT_PAGE,
                    source_url=f"https://www.homedepot.com/p/{product_id}",
                    review_text=body,
                    rating=rating,
                ))
            except Exception:
                continue
        
        return reviews
    
    async def get_category_products(
        self,
        category: str,
        max_products: int = 100,
    ) -> List[str]:
        """Get product URLs from Home Depot search."""
        products = []
        page = await self._create_page()
        
        try:
            search_url = f"https://www.homedepot.com/s/{quote(category)}"
            
            if not await self._safe_goto(page, search_url):
                return products
            
            await self._scroll_page(page)
            
            links = await page.query_selector_all('a[href*="/p/"]')
            
            for link in links:
                if len(products) >= max_products:
                    break
                href = await link.get_attribute('href')
                if href and '/p/' in href:
                    full_url = urljoin("https://www.homedepot.com", href)
                    if full_url not in products:
                        products.append(full_url)
            
        except Exception as e:
            logger.error(f"Error getting Home Depot category products: {e}")
        finally:
            await page.context.close()
        
        return products


# =============================================================================
# ENTERPRISE SCRAPER ORCHESTRATOR
# =============================================================================

class EnterpriseReviewScraper:
    """
    Main orchestrator for enterprise-grade multi-site review scraping.
    
    Coordinates multiple site-specific scrapers, handles rate limiting,
    deduplication, and corpus building.
    
    Usage:
        scraper = EnterpriseReviewScraper()
        
        # Scrape single product
        result = await scraper.scrape_product("https://amazon.com/dp/B08N5WRWNW")
        
        # Scrape category
        products = await scraper.scrape_category("amazon.com", "headphones", max_products=100)
        
        # Build corpus
        await scraper.build_corpus(target_products=10000)
    """
    
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.rate_limiter = RateLimiter()
        self.deduplicator = DeduplicationEngine()
        
        # Initialize scrapers
        self._scrapers: Dict[str, EnterpriseBaseScraper] = {}
    
    def _get_scraper(self, domain: str) -> Optional[EnterpriseBaseScraper]:
        """Get or create scraper for domain."""
        if domain not in self._scrapers:
            scraper_class = self._get_scraper_class(domain)
            if scraper_class:
                self._scrapers[domain] = scraper_class(
                    rate_limiter=self.rate_limiter,
                    headless=self.headless,
                )
        return self._scrapers.get(domain)
    
    def _get_scraper_class(self, domain: str):
        """Get scraper class for domain."""
        scrapers = {
            # Tier 1 - Critical retailers
            "amazon.com": AmazonEnterpriseScraper,
            "walmart.com": WalmartEnterpriseScraper,
            "target.com": TargetEnterpriseScraper,
            "bestbuy.com": BestBuyEnterpriseScraper,
            "homedepot.com": HomeDepotEnterpriseScraper,
            # TODO: Add more Tier 1 scrapers
            # "costco.com": CostcoEnterpriseScraper,
            # "lowes.com": LowesEnterpriseScraper,
            
            # TODO: Tier 2 - Important retailers
            # "chewy.com": ChewyEnterpriseScraper,
            # "sephora.com": SephoraEnterpriseScraper,
            # "nike.com": NikeEnterpriseScraper,
            # "nordstrom.com": NordstromEnterpriseScraper,
            # "rei.com": REIEnterpriseScraper,
            # "wayfair.com": WayfairEnterpriseScraper,
            # "etsy.com": EtsyEnterpriseScraper,
        }
        return scrapers.get(domain)
    
    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL."""
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        if domain.startswith("www."):
            domain = domain[4:]
        return domain
    
    async def scrape_product(
        self,
        product_url: str,
        max_reviews: int = 500,
    ) -> ScraperResult:
        """Scrape reviews for a single product."""
        domain = self._extract_domain(product_url)
        scraper = self._get_scraper(domain)
        
        if not scraper:
            return ScraperResult(
                source=ReviewSource.PRODUCT_PAGE,
                source_url=product_url,
                success=False,
                error_message=f"No scraper available for {domain}",
            )
        
        result = await scraper.scrape_product(product_url, max_reviews)
        
        # Deduplicate reviews
        if result.reviews:
            result.reviews = self.deduplicator.deduplicate(result.reviews)
        
        return result
    
    async def scrape_category(
        self,
        retailer: str,
        category: str,
        max_products: int = 100,
        max_reviews_per_product: int = 100,
    ) -> List[ScraperResult]:
        """Scrape all products in a category."""
        scraper = self._get_scraper(retailer)
        
        if not scraper:
            logger.error(f"No scraper available for {retailer}")
            return []
        
        # Get product URLs
        logger.info(f"Getting product URLs for {retailer}/{category}")
        product_urls = await scraper.get_category_products(category, max_products)
        logger.info(f"Found {len(product_urls)} products")
        
        # Scrape each product
        results = []
        for i, url in enumerate(product_urls):
            logger.info(f"Scraping product {i+1}/{len(product_urls)}: {url[:60]}...")
            result = await self.scrape_product(url, max_reviews_per_product)
            results.append(result)
            
            if result.success:
                logger.info(f"  -> {len(result.reviews)} reviews")
            else:
                logger.warning(f"  -> Failed: {result.error_message}")
        
        return results
    
    async def build_corpus(
        self,
        target_products: int = 10000,
        retailers: Optional[List[str]] = None,
    ) -> None:
        """
        Build massive review corpus across all retailers.
        
        This is the main entry point for corpus building.
        Runs continuously until target is reached.
        """
        if retailers is None:
            retailers = list(RETAILER_CATEGORIES.keys())
        
        total_scraped = 0
        
        for retailer in retailers:
            if total_scraped >= target_products:
                break
            
            scraper = self._get_scraper(retailer)
            if not scraper:
                logger.warning(f"No scraper for {retailer}, skipping")
                continue
            
            categories = RETAILER_CATEGORIES.get(retailer, [])
            
            for category in categories:
                if total_scraped >= target_products:
                    break
                
                logger.info(f"Scraping {retailer}/{category}")
                
                remaining = target_products - total_scraped
                products_to_scrape = min(remaining, 100)
                
                results = await self.scrape_category(
                    retailer,
                    category,
                    max_products=products_to_scrape,
                    max_reviews_per_product=100,
                )
                
                successful = sum(1 for r in results if r.success)
                total_scraped += successful
                
                logger.info(f"Progress: {total_scraped}/{target_products} products scraped")
    
    async def close(self) -> None:
        """Close all scrapers and clean up."""
        for scraper in self._scrapers.values():
            await scraper.close()
        self._scrapers.clear()


# =============================================================================
# SINGLETON ACCESS
# =============================================================================

_enterprise_scraper: Optional[EnterpriseReviewScraper] = None


def get_enterprise_scraper(headless: bool = True) -> EnterpriseReviewScraper:
    """Get or create the enterprise scraper singleton."""
    global _enterprise_scraper
    if _enterprise_scraper is None:
        _enterprise_scraper = EnterpriseReviewScraper(headless=headless)
    return _enterprise_scraper


async def scrape_product(url: str, max_reviews: int = 500) -> ScraperResult:
    """Convenience function to scrape a single product."""
    scraper = get_enterprise_scraper()
    return await scraper.scrape_product(url, max_reviews)
