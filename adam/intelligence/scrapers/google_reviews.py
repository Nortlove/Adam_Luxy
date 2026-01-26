# =============================================================================
# Google Reviews Search Scraper
# Location: adam/intelligence/scrapers/google_reviews.py
# =============================================================================

"""
Google Search Scraper for Product Reviews

Searches Google for product reviews and extracts review snippets
from search results. This provides additional review sources beyond
the product page itself.

Searches for:
- "{product name} reviews"
- "{product name} {brand} reviews"
- "{product name} customer reviews"
- "{product name} reddit" (for Reddit discussions)
"""

import asyncio
import hashlib
import logging
import re
import time
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus

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
]


class GoogleReviewsScraper(BaseReviewScraper):
    """
    Scrapes review snippets from Google search results.
    
    This scraper:
    1. Searches Google for product reviews
    2. Extracts review snippets from search results
    3. Identifies review content from various sources
    """
    
    def __init__(self, timeout: int = 30):
        """
        Initialize the scraper.
        
        Args:
            timeout: Request timeout in seconds
        """
        self.timeout = timeout
        self._client: Optional[Any] = None
        self._user_agent_index = 0
    
    @property
    def source(self) -> ReviewSource:
        return ReviewSource.GOOGLE_REVIEWS
    
    @property
    def name(self) -> str:
        return "Google Reviews Search Scraper"
    
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
    
    async def scrape(
        self,
        product_name: str,
        product_url: Optional[str] = None,
        brand: Optional[str] = None,
        max_reviews: int = 50,
    ) -> ScraperResult:
        """
        Search Google for product reviews.
        
        Args:
            product_name: Product name to search for
            product_url: Not used for Google search
            brand: Brand name for better search
            max_reviews: Maximum review snippets to extract
            
        Returns:
            ScraperResult with review snippets
        """
        start_time = time.time()
        
        if not product_name:
            return ScraperResult(
                source=self.source,
                success=False,
                error_message="Product name is required",
                scrape_duration_ms=(time.time() - start_time) * 1000,
            )
        
        if not await self.is_available():
            return ScraperResult(
                source=self.source,
                success=False,
                error_message="Required libraries (httpx, beautifulsoup4) not installed",
                scrape_duration_ms=(time.time() - start_time) * 1000,
            )
        
        all_reviews = []
        
        # Build search queries
        queries = [
            f"{product_name} reviews",
            f"{product_name} customer reviews",
        ]
        
        if brand:
            queries.insert(0, f"{brand} {product_name} reviews")
        
        # Add Reddit search for authentic discussions
        queries.append(f"{product_name} reddit")
        
        try:
            client = await self._get_client()
            headers = {
                "User-Agent": self._get_next_user_agent(),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
            }
            
            for query in queries:
                if len(all_reviews) >= max_reviews:
                    break
                
                # Build Google search URL
                search_url = f"https://www.google.com/search?q={quote_plus(query)}&num=20"
                
                logger.debug(f"Searching: {query}")
                
                try:
                    response = await client.get(search_url, headers=headers)
                    response.raise_for_status()
                    
                    soup = BeautifulSoup(response.text, "html.parser")
                    
                    # Extract review snippets from search results
                    snippets = self._extract_review_snippets(soup, query)
                    all_reviews.extend(snippets)
                    
                    logger.debug(f"Found {len(snippets)} snippets for '{query}'")
                    
                    # Rate limiting
                    await asyncio.sleep(1.0)
                    
                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 429:
                        logger.warning("Rate limited by Google")
                        break
                    continue
                except Exception as e:
                    logger.debug(f"Error searching '{query}': {e}")
                    continue
            
            # Deduplicate and truncate
            seen_texts = set()
            unique_reviews = []
            for review in all_reviews:
                text_hash = hashlib.md5(review.review_text[:100].encode()).hexdigest()
                if text_hash not in seen_texts:
                    seen_texts.add(text_hash)
                    unique_reviews.append(review)
            
            unique_reviews = unique_reviews[:max_reviews]
            
            return ScraperResult(
                source=self.source,
                reviews=unique_reviews,
                total_found=len(unique_reviews),
                product_name=product_name,
                product_brand=brand,
                success=len(unique_reviews) > 0,
                scrape_duration_ms=(time.time() - start_time) * 1000,
            )
            
        except Exception as e:
            logger.error(f"Error in Google review search: {e}")
            return ScraperResult(
                source=self.source,
                reviews=all_reviews,
                total_found=len(all_reviews),
                success=len(all_reviews) > 0,
                error_message=str(e),
                scrape_duration_ms=(time.time() - start_time) * 1000,
            )
    
    def _extract_review_snippets(self, soup: Any, query: str) -> List[RawReview]:
        """Extract review-like snippets from Google search results."""
        reviews = []
        
        # Find search result containers
        result_divs = soup.find_all("div", class_=re.compile(r"g|result", re.I))
        
        for i, div in enumerate(result_divs):
            try:
                # Get the snippet text
                snippet_el = div.find(class_=re.compile(r"snippet|description|VwiC3b", re.I))
                if not snippet_el:
                    # Try finding any paragraph-like content
                    snippet_el = div.find("span", class_=re.compile(r"st|aCOpRe"))
                
                if not snippet_el:
                    continue
                
                snippet_text = snippet_el.get_text().strip()
                
                # Filter for review-like content
                if not self._is_review_like(snippet_text):
                    continue
                
                # Get source URL
                link_el = div.find("a", href=True)
                source_url = link_el.get("href", "") if link_el else ""
                
                # Determine source type
                source_type = self._determine_source(source_url)
                
                # Try to extract rating if mentioned
                rating = self._extract_rating_from_text(snippet_text)
                
                # Generate review ID
                review_id = hashlib.md5(
                    f"google_{i}_{snippet_text[:50]}".encode()
                ).hexdigest()[:12]
                
                reviews.append(RawReview(
                    review_id=f"ggl_{review_id}",
                    source=source_type,
                    source_url=source_url,
                    review_text=snippet_text,
                    rating=rating,
                ))
                
            except Exception as e:
                logger.debug(f"Error extracting snippet: {e}")
                continue
        
        return reviews
    
    def _is_review_like(self, text: str) -> bool:
        """Check if text appears to be a review."""
        if len(text) < 50:
            return False
        
        # Review indicators
        review_words = [
            "review", "rating", "stars", "recommend", "bought",
            "purchase", "quality", "worth", "love", "hate",
            "great", "terrible", "best", "worst", "amazing",
            "disappointed", "satisfied", "product", "experience"
        ]
        
        text_lower = text.lower()
        matches = sum(1 for word in review_words if word in text_lower)
        
        return matches >= 2
    
    def _determine_source(self, url: str) -> ReviewSource:
        """Determine the review source from URL."""
        url_lower = url.lower()
        
        if "reddit.com" in url_lower:
            return ReviewSource.REDDIT
        elif "amazon.com" in url_lower:
            return ReviewSource.AMAZON
        else:
            return ReviewSource.GOOGLE_REVIEWS
    
    def _extract_rating_from_text(self, text: str) -> float:
        """Try to extract a rating from text."""
        # Look for patterns like "4.5/5", "4.5 stars", "rated 4.5"
        patterns = [
            r'(\d+\.?\d*)\s*(?:out of\s*)?(?:/\s*)?5\s*(?:stars?)?',
            r'(\d+\.?\d*)\s*stars?',
            r'rated?\s*(\d+\.?\d*)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                rating = float(match.group(1))
                if 1 <= rating <= 5:
                    return rating
        
        # Default to neutral
        return 3.0
    
    async def close(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None


# =============================================================================
# SINGLETON
# =============================================================================

_scraper: Optional[GoogleReviewsScraper] = None


def get_google_reviews_scraper() -> GoogleReviewsScraper:
    """Get singleton Google Reviews Scraper."""
    global _scraper
    if _scraper is None:
        _scraper = GoogleReviewsScraper()
    return _scraper
