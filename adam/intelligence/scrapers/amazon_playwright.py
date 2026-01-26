# =============================================================================
# Amazon Reviews Scraper - Playwright Headless Browser
# Location: adam/intelligence/scrapers/amazon_playwright.py
# =============================================================================

"""
Playwright-Based Amazon Reviews Scraper

Uses a headless browser to bypass Amazon's bot detection and scrape reviews.

Key Features:
1. Renders JavaScript like a real browser
2. Handles dynamic content loading
3. Clicks through pagination
4. Extracts full review data
5. Respects rate limits with delays

Requirements:
- playwright package: pip install playwright
- Browser binary: playwright install chromium
"""

import asyncio
import hashlib
import logging
import re
import random
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from adam.intelligence.models.customer_intelligence import ReviewSource
from adam.intelligence.scrapers.base import (
    BaseReviewScraper,
    RawReview,
    ScraperResult,
)

logger = logging.getLogger(__name__)

# Check if Playwright is available
try:
    from playwright.async_api import async_playwright, Browser, Page, Playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    logger.warning("Playwright not installed. Run: pip install playwright && playwright install chromium")


class AmazonPlaywrightScraper(BaseReviewScraper):
    """
    Scrapes Amazon reviews using Playwright headless browser.
    
    This bypasses Amazon's bot detection by:
    - Using a real browser engine (Chromium)
    - Rendering JavaScript
    - Simulating human-like behavior (delays, scrolling)
    - Using realistic viewport and user agent
    """
    
    # Realistic user agents
    USER_AGENTS = [
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    ]
    
    def __init__(
        self,
        max_pages: int = 10,
        page_delay_ms: tuple = (1000, 3000),
        headless: bool = True,
    ):
        """
        Initialize the Playwright scraper.
        
        Args:
            max_pages: Maximum number of review pages to scrape
            page_delay_ms: Min/max delay between page loads (milliseconds)
            headless: Whether to run browser in headless mode
        """
        self.max_pages = max_pages
        self.page_delay_ms = page_delay_ms
        self.headless = headless
        self._playwright: Optional[Any] = None
        self._browser: Optional[Any] = None
    
    @property
    def source(self) -> ReviewSource:
        return ReviewSource.AMAZON
    
    @property
    def name(self) -> str:
        return "Amazon Playwright Scraper (Headless Browser)"
    
    async def is_available(self) -> bool:
        """Check if Playwright is installed and browser is available."""
        return PLAYWRIGHT_AVAILABLE
    
    def _extract_asin(self, url: str) -> Optional[str]:
        """Extract ASIN from Amazon URL."""
        patterns = [
            r'/dp/([A-Z0-9]{10})',
            r'/gp/product/([A-Z0-9]{10})',
            r'/product-reviews/([A-Z0-9]{10})',
            r'/([A-Z0-9]{10})(?:/|$|\?)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url, re.IGNORECASE)
            if match:
                return match.group(1).upper()
        
        return None
    
    async def _get_browser(self) -> Any:
        """Get or create browser instance."""
        if not PLAYWRIGHT_AVAILABLE:
            raise ImportError("Playwright not installed")
        
        if self._browser is None:
            self._playwright = await async_playwright().start()
            # Simple browser launch - no extra args that might trigger detection
            self._browser = await self._playwright.chromium.launch(
                headless=self.headless,
            )
        
        return self._browser
    
    async def _create_page(self, browser: Any) -> Any:
        """Create a new page with realistic settings."""
        # Simple page setup matching what works in direct test
        page = await browser.new_page(
            viewport={'width': 1920, 'height': 1080},
            user_agent=random.choice(self.USER_AGENTS),
        )
        
        return page
    
    async def _random_delay(self):
        """Add random delay to simulate human behavior."""
        delay = random.randint(self.page_delay_ms[0], self.page_delay_ms[1])
        await asyncio.sleep(delay / 1000)
    
    async def scrape(
        self,
        product_name: str,
        product_url: Optional[str] = None,
        brand: Optional[str] = None,
        max_reviews: int = 100,
    ) -> ScraperResult:
        """
        Scrape Amazon reviews using headless browser.
        
        Args:
            product_name: Product name
            product_url: Amazon product URL
            brand: Brand name
            max_reviews: Maximum reviews to extract
            
        Returns:
            ScraperResult with extracted reviews
        """
        start_time = time.time()
        
        if not product_url:
            return ScraperResult(
                source=self.source,
                success=False,
                error_message="Product URL is required",
                scrape_duration_ms=(time.time() - start_time) * 1000,
            )
        
        if not await self.is_available():
            return ScraperResult(
                source=self.source,
                source_url=product_url,
                success=False,
                error_message="Playwright not installed. Run: pip install playwright && playwright install chromium",
                scrape_duration_ms=(time.time() - start_time) * 1000,
            )
        
        # Extract ASIN
        asin = self._extract_asin(product_url)
        if not asin:
            return ScraperResult(
                source=self.source,
                source_url=product_url,
                success=False,
                error_message="Could not extract ASIN from URL",
                scrape_duration_ms=(time.time() - start_time) * 1000,
            )
        
        logger.info(f"Scraping Amazon reviews for ASIN: {asin} using Playwright")
        
        all_reviews = []
        product_info = {}
        total_review_count = 0
        page = None
        
        try:
            browser = await self._get_browser()
            page = await self._create_page(browser)
            
            # Go directly to product page - more reliable than reviews page
            product_page_url = f"https://www.amazon.com/dp/{asin}"
            logger.info(f"Navigating to product page: {product_page_url}")
            
            await page.goto(product_page_url, wait_until='networkidle', timeout=45000)
            await self._random_delay()
            
            # Scroll down to load reviews section (reviews are at bottom of page)
            logger.info("Scrolling to load reviews...")
            for scroll_pct in [0.3, 0.5, 0.7, 0.9]:
                await page.evaluate(f"window.scrollTo(0, document.body.scrollHeight * {scroll_pct})")
                await asyncio.sleep(0.5)
            
            # Wait for dynamic content to load
            await asyncio.sleep(2)
            
            # Scroll to reviews section specifically
            reviews_section = await page.query_selector('#reviewsMedley')
            if reviews_section:
                await reviews_section.scroll_into_view_if_needed()
                await asyncio.sleep(1)
            
            # Check for review elements directly
            review_count = await page.evaluate('''
                () => document.querySelectorAll('[data-hook="review"]').length
            ''')
            logger.info(f"Found {review_count} review elements on page")
            
            # If no reviews found with data-hook, try alternate approach
            if review_count == 0:
                # Check for customer reviews section
                alt_count = await page.evaluate('''
                    () => document.querySelectorAll('.review, [id^="customer_review"]').length
                ''')
                logger.info(f"Found {alt_count} reviews with alternate selectors")
            
            # Extract total review count
            total_review_count = await self._extract_total_reviews(page)
            logger.info(f"Total reviews available: {total_review_count}")
            
            # Extract product info
            product_info = await self._extract_product_info(page)
            
            # Paginate through reviews
            page_num = 1
            while page_num <= self.max_pages and len(all_reviews) < max_reviews:
                logger.debug(f"Extracting reviews from page {page_num}")
                
                # Extract reviews from current page
                page_reviews = await self._extract_reviews_from_page(page, product_url)
                
                if not page_reviews:
                    logger.debug(f"No reviews found on page {page_num}, stopping")
                    break
                
                all_reviews.extend(page_reviews)
                logger.info(f"Page {page_num}: Extracted {len(page_reviews)} reviews (total: {len(all_reviews)})")
                
                if len(all_reviews) >= max_reviews:
                    break
                
                # Try to go to next page
                has_next = await self._go_to_next_page(page)
                if not has_next:
                    logger.debug("No more pages available")
                    break
                
                page_num += 1
                await self._random_delay()
            
            # Truncate to max_reviews
            all_reviews = all_reviews[:max_reviews]
            
            return ScraperResult(
                source=self.source,
                source_url=product_url,
                reviews=all_reviews,
                total_found=len(all_reviews),
                total_available=total_review_count,
                product_name=product_info.get("name") or product_name,
                product_description=product_info.get("description"),
                product_brand=product_info.get("brand") or brand,
                success=True,
                scrape_duration_ms=(time.time() - start_time) * 1000,
            )
            
        except Exception as e:
            logger.error(f"Error scraping Amazon reviews with Playwright: {e}")
            return ScraperResult(
                source=self.source,
                source_url=product_url,
                reviews=all_reviews,
                total_found=len(all_reviews),
                success=len(all_reviews) > 0,
                error_message=str(e),
                scrape_duration_ms=(time.time() - start_time) * 1000,
            )
        finally:
            if page:
                await page.close()
    
    async def _extract_total_reviews(self, page: Any) -> int:
        """Extract total review count from page."""
        try:
            # Try data-hook attribute
            count_el = await page.query_selector('[data-hook="total-review-count"]')
            if count_el:
                text = await count_el.text_content()
                match = re.search(r'([\d,]+)', text)
                if match:
                    return int(match.group(1).replace(',', ''))
            
            # Try filtering info
            filter_el = await page.query_selector('.a-section.a-spacing-none.a-text-center')
            if filter_el:
                text = await filter_el.text_content()
                match = re.search(r'([\d,]+)\s+(?:global\s+)?ratings?', text, re.I)
                if match:
                    return int(match.group(1).replace(',', ''))
        except Exception as e:
            logger.debug(f"Error extracting total reviews: {e}")
        
        return 0
    
    async def _extract_product_info(self, page: Any) -> Dict[str, Any]:
        """Extract product information from page."""
        info = {}
        
        try:
            # Product title
            title_el = await page.query_selector('[data-hook="product-link"]')
            if not title_el:
                title_el = await page.query_selector('#productTitle')
            if title_el:
                info["name"] = (await title_el.text_content()).strip()
            
            # Brand
            brand_el = await page.query_selector('#bylineInfo')
            if brand_el:
                text = await brand_el.text_content()
                match = re.search(r'(?:Visit|Brand:)\s*(.+?)(?:\s+Store|$)', text)
                if match:
                    info["brand"] = match.group(1).strip()
        except Exception as e:
            logger.debug(f"Error extracting product info: {e}")
        
        return info
    
    async def _extract_reviews_from_page(self, page: Any, url: str) -> List[RawReview]:
        """Extract all reviews from current page."""
        reviews = []
        
        # Try multiple selectors for review containers
        selectors = [
            '[data-hook="review"]',
            '.review',
            '#cm_cr-review_list .review',
            '.a-section.review',
            '[id^="customer_review"]',
        ]
        
        review_containers = []
        for selector in selectors:
            containers = await page.query_selector_all(selector)
            if containers:
                logger.debug(f"Found {len(containers)} reviews with selector: {selector}")
                review_containers = containers
                break
        
        if not review_containers:
            # Last resort: try to find any element with review text
            logger.warning("No standard review containers found, trying text-based search")
            # Try to get review text from the customer reviews section
            review_section = await page.query_selector('#reviewsMedley')
            if review_section:
                # Get all span elements that might contain review text
                spans = await review_section.query_selector_all('span.a-size-base.review-text-content span')
                for i, span in enumerate(spans[:20]):
                    text = await span.text_content()
                    if text and len(text) > 50:
                        review_id = hashlib.md5(f"text_{i}_{text[:50]}".encode()).hexdigest()[:12]
                        reviews.append(RawReview(
                            review_id=f"amz_pw_{review_id}",
                            source=ReviewSource.AMAZON,
                            source_url=url,
                            review_text=text.strip(),
                            rating=4.0,  # Default rating
                        ))
        
        for i, container in enumerate(review_containers):
            try:
                review = await self._parse_review_element(container, url, i)
                if review:
                    reviews.append(review)
            except Exception as e:
                logger.debug(f"Error parsing review {i}: {e}")
                continue
        
        return reviews
    
    async def _parse_review_element(self, container: Any, url: str, index: int) -> Optional[RawReview]:
        """Parse a single review element."""
        # Get review ID
        review_id = await container.get_attribute('id') or f"review_{index}"
        
        # Rating - try multiple selectors and extraction methods
        rating = None  # Start with None to track if extraction succeeded
        rating_extracted = False
        
        rating_selectors = [
            '[data-hook="review-star-rating"]',
            '[data-hook="cmps-review-star-rating"]',
            'i.a-icon-star',
            '.review-rating',
            'span.a-icon-alt',  # Amazon often puts rating in icon alt text
        ]
        
        for selector in rating_selectors:
            if rating_extracted:
                break
                
            rating_el = await container.query_selector(selector)
            if rating_el:
                # Try aria-label first (most reliable on modern Amazon)
                aria_label = await rating_el.get_attribute('aria-label') or ''
                if aria_label:
                    match = re.search(r'(\d+\.?\d*)\s*out\s*of\s*5', aria_label, re.I)
                    if match:
                        rating = float(match.group(1))
                        rating_extracted = True
                        logger.debug(f"Review {index}: Extracted rating {rating} from aria-label")
                        break
                
                # Try text content
                rating_text = await rating_el.text_content() or ''
                
                # Pattern: "5.0 out of 5 stars"
                match = re.search(r'(\d+\.?\d*)\s*out\s*of\s*5', rating_text, re.I)
                if match:
                    rating = float(match.group(1))
                    rating_extracted = True
                    logger.debug(f"Review {index}: Extracted rating {rating} from text")
                    break
                
                # Pattern: standalone number
                match = re.search(r'^(\d+\.?\d*)$', rating_text.strip())
                if match:
                    val = float(match.group(1))
                    if 1.0 <= val <= 5.0:
                        rating = val
                        rating_extracted = True
                        logger.debug(f"Review {index}: Extracted rating {rating} from standalone number")
                        break
                
                # Try class attribute (e.g., "a-star-4", "a-star-5")
                rating_class = await rating_el.get_attribute('class') or ''
                match = re.search(r'a-star-(\d)', rating_class)
                if match:
                    rating = float(match.group(1))
                    rating_extracted = True
                    logger.debug(f"Review {index}: Extracted rating {rating} from class")
                    break
        
        # If no rating found, try the review title area (sometimes contains rating)
        if not rating_extracted:
            title_area = await container.query_selector('[data-hook="review-title"]')
            if title_area:
                title_text = await title_area.text_content() or ''
                match = re.search(r'(\d+\.?\d*)\s*out\s*of\s*5', title_text, re.I)
                if match:
                    rating = float(match.group(1))
                    rating_extracted = True
                    logger.debug(f"Review {index}: Extracted rating {rating} from title area")
        
        # Default to 3.0 if extraction failed, but LOG IT
        if not rating_extracted or rating is None:
            rating = 3.0
            logger.warning(f"Review {index}: Rating extraction FAILED - defaulting to {rating}. URL: {url}")
        
        # Review title - try multiple selectors
        title = ""
        title_selectors = [
            '[data-hook="review-title"] span:not(.a-letter-space)',
            '[data-hook="review-title"]',
            '.review-title',
        ]
        for selector in title_selectors:
            title_el = await container.query_selector(selector)
            if title_el:
                title = (await title_el.text_content() or "").strip()
                # Clean up title (remove rating text if included)
                title = re.sub(r'^\d+\.?\d*\s*out\s*of\s*\d+\s*stars?\s*', '', title, flags=re.I)
                if title:
                    break
        
        # Review body - try multiple selectors
        body = ""
        body_selectors = [
            '[data-hook="review-body"] span',
            '.review-text-content span',
            '[data-hook="review-body"]',
            '.reviewText',
        ]
        for selector in body_selectors:
            body_el = await container.query_selector(selector)
            if body_el:
                body = (await body_el.text_content() or "").strip()
                if body and len(body) > 20:
                    break
        
        # If still no body, get all text from container
        if not body or len(body) < 20:
            all_text = await container.text_content() or ""
            # Try to extract review text (skip metadata)
            if len(all_text) > 100:
                body = all_text.strip()
        
        if not body or len(body) < 20:
            logger.debug(f"Skipping review {index} - no body text")
            return None
        
        # Combine title and body
        review_text = f"{title}. {body}" if title else body
        
        # Reviewer name
        name_el = await container.query_selector('.a-profile-name')
        reviewer_name = None
        if name_el:
            reviewer_name = (await name_el.text_content() or "").strip()
        
        # Review date
        date_el = await container.query_selector('[data-hook="review-date"]')
        review_date = None
        if date_el:
            date_text = await date_el.text_content() or ""
            match = re.search(r'on (.+)$', date_text)
            if match:
                try:
                    from dateutil import parser
                    review_date = parser.parse(match.group(1))
                except Exception:
                    pass
        
        # Verified purchase
        verified_el = await container.query_selector('[data-hook="avp-badge"]')
        verified = verified_el is not None
        
        # Helpful votes
        helpful_el = await container.query_selector('[data-hook="helpful-vote-statement"]')
        helpful_votes = 0
        if helpful_el:
            helpful_text = await helpful_el.text_content() or ""
            match = re.search(r'(\d+)', helpful_text)
            if match:
                helpful_votes = int(match.group(1))
        
        # Generate unique ID
        unique_id = hashlib.md5(f"{review_id}_{review_text[:50]}".encode()).hexdigest()[:12]
        
        return RawReview(
            review_id=f"amz_pw_{unique_id}",
            source=ReviewSource.AMAZON,
            source_url=url,
            review_text=review_text,
            rating=rating,
            review_date=review_date,
            reviewer_name=reviewer_name,
            verified_purchase=verified,
            helpful_votes=helpful_votes,
        )
    
    async def _go_to_next_page(self, page: Any) -> bool:
        """Navigate to the next page of reviews."""
        try:
            # Find "Next" button
            next_btn = await page.query_selector('li.a-last:not(.a-disabled) a')
            
            if not next_btn:
                # Try alternate selector
                next_btn = await page.query_selector('.a-pagination .a-last:not(.a-disabled) a')
            
            if not next_btn:
                return False
            
            # Click and wait for navigation
            await next_btn.click()
            await page.wait_for_load_state('domcontentloaded')
            
            # Wait for reviews to load
            try:
                await page.wait_for_selector('[data-hook="review"]', timeout=10000)
            except Exception:
                pass
            
            return True
            
        except Exception as e:
            logger.debug(f"Error navigating to next page: {e}")
            return False
    
    async def close(self):
        """Close browser and playwright."""
        if self._browser:
            await self._browser.close()
            self._browser = None
        
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None


# =============================================================================
# SINGLETON
# =============================================================================

_scraper: Optional[AmazonPlaywrightScraper] = None


def get_amazon_playwright_scraper(max_pages: int = 10) -> AmazonPlaywrightScraper:
    """Get singleton Amazon Playwright Scraper."""
    global _scraper
    if _scraper is None:
        _scraper = AmazonPlaywrightScraper(max_pages=max_pages)
    return _scraper
