# =============================================================================
# Amazon Reviews Scraper with Pagination
# Location: adam/intelligence/scrapers/amazon_reviews.py
# =============================================================================

"""
Enhanced Amazon Reviews Scraper

Handles pagination to get ALL reviews, not just the first page.

Strategies:
1. Extract ASIN from product URL
2. Access reviews page directly (/product-reviews/{ASIN}/)
3. Paginate through all review pages
4. Handle both star-filtered and all-reviews pages
"""

import asyncio
import hashlib
import logging
import re
import time
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse, parse_qs

from adam.intelligence.models.customer_intelligence import ReviewSource
from adam.intelligence.scrapers.base import (
    BaseReviewScraper,
    RawReview,
    ScraperResult,
)

logger = logging.getLogger(__name__)

# Try to import HTTP and parsing libraries
try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False

try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False


# =============================================================================
# USER AGENTS
# =============================================================================

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
]


class AmazonReviewsScraper(BaseReviewScraper):
    """
    Scrapes Amazon reviews with full pagination support.
    
    This scraper:
    1. Extracts ASIN from product URL
    2. Navigates to the reviews page
    3. Paginates through ALL reviews (not just first page)
    4. Extracts comprehensive review data
    """
    
    def __init__(self, timeout: int = 30, max_pages: int = 10):
        """
        Initialize the scraper.
        
        Args:
            timeout: Request timeout in seconds
            max_pages: Maximum number of review pages to fetch
        """
        self.timeout = timeout
        self.max_pages = max_pages
        self._client: Optional[Any] = None
        self._user_agent_index = 0
    
    @property
    def source(self) -> ReviewSource:
        return ReviewSource.AMAZON
    
    @property
    def name(self) -> str:
        return "Amazon Reviews Scraper (Paginated)"
    
    async def is_available(self) -> bool:
        """Check if required libraries are available."""
        return HTTPX_AVAILABLE and BS4_AVAILABLE
    
    def _get_next_user_agent(self) -> str:
        """Rotate through user agents."""
        agent = USER_AGENTS[self._user_agent_index % len(USER_AGENTS)]
        self._user_agent_index += 1
        return agent
    
    async def _get_client(self):
        """Get or create HTTP client."""
        if not HTTPX_AVAILABLE:
            raise ImportError("httpx is required for scraping")
        
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=self.timeout,
                follow_redirects=True,
            )
        return self._client
    
    def _extract_asin(self, url: str) -> Optional[str]:
        """
        Extract ASIN from Amazon URL.
        
        Handles various URL formats:
        - /dp/B0CHX2F5QT
        - /gp/product/B0CHX2F5QT
        - /product-reviews/B0CHX2F5QT
        """
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
    
    def _get_reviews_url(self, asin: str, page: int = 1, filter_star: Optional[int] = None) -> str:
        """
        Build Amazon reviews page URL.
        
        Args:
            asin: Product ASIN
            page: Page number (1-indexed)
            filter_star: Optional star filter (1-5) or None for all
        """
        base = f"https://www.amazon.com/product-reviews/{asin}"
        params = [
            "ref=cm_cr_dp_d_show_all_btm",
            f"pageNumber={page}",
            "reviewerType=all_reviews",
            "sortBy=recent",
        ]
        
        if filter_star:
            params.append(f"filterByStar={filter_star}_star")
        
        return f"{base}?{'&'.join(params)}"
    
    async def scrape(
        self,
        product_name: str,
        product_url: Optional[str] = None,
        brand: Optional[str] = None,
        max_reviews: int = 100,
    ) -> ScraperResult:
        """
        Scrape Amazon reviews with pagination.
        
        Args:
            product_name: Product name
            product_url: Amazon product URL
            brand: Brand name
            max_reviews: Maximum reviews to extract
            
        Returns:
            ScraperResult with all extracted reviews
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
                error_message="Required libraries (httpx, beautifulsoup4) not installed",
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
        
        logger.info(f"Scraping Amazon reviews for ASIN: {asin}")
        
        all_reviews = []
        product_info = {}
        total_review_count = 0
        
        try:
            client = await self._get_client()
            headers = {
                "User-Agent": self._get_next_user_agent(),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
            }
            
            # Paginate through review pages
            for page in range(1, self.max_pages + 1):
                if len(all_reviews) >= max_reviews:
                    break
                
                reviews_url = self._get_reviews_url(asin, page)
                logger.debug(f"Fetching page {page}: {reviews_url}")
                
                try:
                    response = await client.get(reviews_url, headers=headers)
                    response.raise_for_status()
                    
                    soup = BeautifulSoup(response.text, "html.parser")
                    
                    # Extract total review count on first page
                    if page == 1:
                        total_review_count = self._extract_total_reviews(soup)
                        product_info = self._extract_product_info(soup)
                        logger.info(f"Total reviews available: {total_review_count}")
                    
                    # Extract reviews from this page
                    page_reviews = self._extract_reviews_from_page(soup, reviews_url)
                    
                    if not page_reviews:
                        logger.debug(f"No reviews found on page {page}, stopping pagination")
                        break
                    
                    all_reviews.extend(page_reviews)
                    logger.debug(f"Page {page}: Found {len(page_reviews)} reviews (total: {len(all_reviews)})")
                    
                    # Rate limiting - be respectful
                    if page < self.max_pages:
                        await asyncio.sleep(0.5)
                    
                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 429:
                        logger.warning("Rate limited, stopping pagination")
                        break
                    raise
            
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
            logger.error(f"Error scraping Amazon reviews: {e}")
            return ScraperResult(
                source=self.source,
                source_url=product_url,
                reviews=all_reviews,  # Return any reviews we got
                total_found=len(all_reviews),
                success=len(all_reviews) > 0,  # Partial success if we got some
                error_message=str(e),
                scrape_duration_ms=(time.time() - start_time) * 1000,
            )
    
    def _extract_total_reviews(self, soup: Any) -> int:
        """Extract total review count from page."""
        try:
            # Look for "X global ratings"
            count_el = soup.find(attrs={"data-hook": "total-review-count"})
            if count_el:
                text = count_el.get_text()
                match = re.search(r'([\d,]+)', text)
                if match:
                    return int(match.group(1).replace(',', ''))
            
            # Alternative: look for ratings count
            ratings_el = soup.find(class_=re.compile(r'total.*rating', re.I))
            if ratings_el:
                text = ratings_el.get_text()
                match = re.search(r'([\d,]+)', text)
                if match:
                    return int(match.group(1).replace(',', ''))
        except Exception:
            pass
        
        return 0
    
    def _extract_product_info(self, soup: Any) -> Dict[str, Any]:
        """Extract product information from reviews page."""
        info = {}
        
        try:
            # Product title
            title_el = soup.find(attrs={"data-hook": "product-link"})
            if title_el:
                info["name"] = title_el.get_text().strip()
            
            # Average rating
            rating_el = soup.find(attrs={"data-hook": "rating-out-of-text"})
            if rating_el:
                text = rating_el.get_text()
                match = re.search(r'(\d+\.?\d*)', text)
                if match:
                    info["avg_rating"] = float(match.group(1))
        except Exception:
            pass
        
        return info
    
    def _extract_reviews_from_page(self, soup: Any, url: str) -> List[RawReview]:
        """Extract all reviews from a single page."""
        reviews = []
        
        # Find all review containers
        review_containers = soup.find_all("div", attrs={"data-hook": "review"})
        
        for container in review_containers:
            try:
                review = self._parse_review_container(container, url)
                if review:
                    reviews.append(review)
            except Exception as e:
                logger.debug(f"Error parsing review: {e}")
                continue
        
        return reviews
    
    def _parse_review_container(self, container: Any, url: str) -> Optional[RawReview]:
        """Parse a single review container."""
        # Review ID
        review_id = container.get("id", "")
        if not review_id:
            review_id = hashlib.md5(str(container)[:200].encode()).hexdigest()[:12]
        
        # Rating (1-5 stars)
        rating = 3.0
        rating_el = container.find("i", attrs={"data-hook": "review-star-rating"})
        if not rating_el:
            rating_el = container.find("i", attrs={"data-hook": "cmps-review-star-rating"})
        if rating_el:
            rating_text = rating_el.get_text() or rating_el.get("class", [""])[0]
            match = re.search(r'(\d+\.?\d*)', str(rating_text))
            if match:
                rating = float(match.group(1))
        
        # Review title
        title_el = container.find(attrs={"data-hook": "review-title"})
        title = title_el.get_text().strip() if title_el else ""
        
        # Review body
        body_el = container.find("span", attrs={"data-hook": "review-body"})
        body = body_el.get_text().strip() if body_el else ""
        
        if not body:
            return None
        
        # Combine title and body
        review_text = f"{title}. {body}" if title else body
        
        # Reviewer name
        name_el = container.find("span", class_="a-profile-name")
        reviewer_name = name_el.get_text().strip() if name_el else None
        
        # Review date
        date_el = container.find("span", attrs={"data-hook": "review-date"})
        review_date = None
        if date_el:
            date_text = date_el.get_text()
            match = re.search(r'on (.+)$', date_text)
            if match:
                try:
                    from dateutil import parser
                    review_date = parser.parse(match.group(1))
                except Exception:
                    pass
        
        # Verified purchase
        verified = container.find("span", attrs={"data-hook": "avp-badge"}) is not None
        
        # Helpful votes
        helpful_el = container.find("span", attrs={"data-hook": "helpful-vote-statement"})
        helpful_votes = 0
        if helpful_el:
            helpful_text = helpful_el.get_text()
            match = re.search(r'(\d+)', helpful_text)
            if match:
                helpful_votes = int(match.group(1))
        
        return RawReview(
            review_id=f"amz_{review_id}",
            source=ReviewSource.AMAZON,
            source_url=url,
            review_text=review_text,
            rating=rating,
            review_date=review_date,
            reviewer_name=reviewer_name,
            verified_purchase=verified,
            helpful_votes=helpful_votes,
        )
    
    async def close(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None


# =============================================================================
# SINGLETON
# =============================================================================

_scraper: Optional[AmazonReviewsScraper] = None


def get_amazon_reviews_scraper(max_pages: int = 10) -> AmazonReviewsScraper:
    """Get singleton Amazon Reviews Scraper."""
    global _scraper
    if _scraper is None:
        _scraper = AmazonReviewsScraper(max_pages=max_pages)
    return _scraper
