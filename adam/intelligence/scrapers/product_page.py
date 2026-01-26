# =============================================================================
# Product Page Scraper
# Location: adam/intelligence/scrapers/product_page.py
# =============================================================================

"""
Scraper for reviews directly on product pages.

Supports common e-commerce sites:
- Amazon
- Target
- Walmart
- Best Buy
- Generic sites with Schema.org markup

Uses BeautifulSoup for HTML parsing and extracts:
- Product info (name, description, price)
- Reviews (text, rating, date, reviewer)
"""

import asyncio
import hashlib
import logging
import re
import time
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from pydantic import BaseModel

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

try:
    import json
    JSON_AVAILABLE = True
except ImportError:
    JSON_AVAILABLE = False


# =============================================================================
# USER AGENTS FOR SCRAPING
# =============================================================================

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
]


# =============================================================================
# PRODUCT PAGE SCRAPER
# =============================================================================

class ProductPageScraper(BaseReviewScraper):
    """
    Scrapes reviews from product pages.
    
    Supports multiple e-commerce sites with site-specific parsers
    and a generic fallback using Schema.org markup.
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
        return ReviewSource.PRODUCT_PAGE
    
    @property
    def name(self) -> str:
        return "Product Page Scraper"
    
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
        max_reviews: int = 100,
    ) -> ScraperResult:
        """
        Scrape reviews from a product page.
        
        Args:
            product_name: Product name
            product_url: URL of the product page
            brand: Brand name
            max_reviews: Maximum reviews to extract
            
        Returns:
            ScraperResult with reviews and product info
        """
        start_time = time.time()
        
        if not product_url:
            return ScraperResult(
                source=self.source,
                success=False,
                error_message="Product URL is required for page scraping",
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
        
        try:
            # Fetch the page
            client = await self._get_client()
            headers = {"User-Agent": self._get_next_user_agent()}
            
            response = await client.get(product_url, headers=headers)
            response.raise_for_status()
            
            html = response.text
            soup = BeautifulSoup(html, "html.parser")
            
            # Determine site type
            domain = urlparse(product_url).netloc.lower()
            
            # Extract product info
            product_info = self._extract_product_info(soup, domain)
            
            # Extract reviews based on site
            if "amazon" in domain:
                reviews = self._extract_amazon_reviews(soup, product_url, max_reviews)
            elif "target" in domain:
                reviews = self._extract_target_reviews(soup, product_url, max_reviews)
            elif "walmart" in domain:
                reviews = self._extract_walmart_reviews(soup, product_url, max_reviews)
            else:
                # Generic extraction using Schema.org
                reviews = self._extract_generic_reviews(soup, product_url, max_reviews)
            
            return ScraperResult(
                source=self.source,
                source_url=product_url,
                reviews=reviews,
                total_found=len(reviews),
                product_name=product_info.get("name") or product_name,
                product_description=product_info.get("description"),
                product_price=product_info.get("price"),
                product_brand=product_info.get("brand") or brand,
                product_images=product_info.get("images", []),
                success=True,
                scrape_duration_ms=(time.time() - start_time) * 1000,
            )
            
        except httpx.HTTPStatusError as e:
            logger.warning(f"HTTP error scraping {product_url}: {e}")
            return ScraperResult(
                source=self.source,
                source_url=product_url,
                success=False,
                error_message=f"HTTP {e.response.status_code}",
                rate_limited=e.response.status_code == 429,
                scrape_duration_ms=(time.time() - start_time) * 1000,
            )
        except Exception as e:
            logger.error(f"Error scraping {product_url}: {e}")
            return ScraperResult(
                source=self.source,
                source_url=product_url,
                success=False,
                error_message=str(e),
                scrape_duration_ms=(time.time() - start_time) * 1000,
            )
    
    def _extract_product_info(self, soup: Any, domain: str) -> Dict[str, Any]:
        """Extract product information from page."""
        info = {}
        
        # Try Schema.org JSON-LD first
        scripts = soup.find_all("script", {"type": "application/ld+json"})
        for script in scripts:
            try:
                import json
                data = json.loads(script.string)
                if isinstance(data, list):
                    data = data[0]
                if data.get("@type") == "Product":
                    info["name"] = data.get("name")
                    info["description"] = data.get("description")
                    info["brand"] = data.get("brand", {}).get("name")
                    if "offers" in data:
                        offers = data["offers"]
                        if isinstance(offers, list):
                            offers = offers[0]
                        info["price"] = offers.get("price")
                    if "image" in data:
                        imgs = data["image"]
                        if isinstance(imgs, str):
                            info["images"] = [imgs]
                        elif isinstance(imgs, list):
                            info["images"] = imgs[:5]
                    break
            except Exception:
                continue
        
        # Fallback to meta tags
        if not info.get("name"):
            og_title = soup.find("meta", {"property": "og:title"})
            if og_title:
                info["name"] = og_title.get("content")
        
        if not info.get("description"):
            og_desc = soup.find("meta", {"property": "og:description"})
            if og_desc:
                info["description"] = og_desc.get("content")
        
        if not info.get("images"):
            og_image = soup.find("meta", {"property": "og:image"})
            if og_image:
                info["images"] = [og_image.get("content")]
        
        return info
    
    def _extract_amazon_reviews(
        self, 
        soup: Any, 
        url: str,
        max_reviews: int
    ) -> List[RawReview]:
        """Extract reviews from Amazon product page."""
        reviews = []
        
        # Amazon review containers
        review_containers = soup.find_all(
            "div", {"data-hook": "review"}
        )
        
        for i, container in enumerate(review_containers[:max_reviews]):
            try:
                # Rating
                rating_el = container.find("i", {"data-hook": "review-star-rating"})
                if rating_el:
                    rating_text = rating_el.get_text()
                    rating = float(re.search(r"(\d+\.?\d*)", rating_text).group(1))
                else:
                    rating = 3.0
                
                # Review text
                text_el = container.find("span", {"data-hook": "review-body"})
                review_text = text_el.get_text().strip() if text_el else ""
                
                if not review_text:
                    continue
                
                # Reviewer name
                name_el = container.find("span", class_="a-profile-name")
                reviewer_name = name_el.get_text().strip() if name_el else None
                
                # Date
                date_el = container.find("span", {"data-hook": "review-date"})
                review_date = None
                if date_el:
                    date_text = date_el.get_text()
                    # Try to parse "on January 1, 2024"
                    match = re.search(r"on (.+)$", date_text)
                    if match:
                        try:
                            from dateutil import parser
                            review_date = parser.parse(match.group(1))
                        except Exception:
                            pass
                
                # Verified purchase
                verified = container.find("span", {"data-hook": "avp-badge"}) is not None
                
                # Helpful votes
                helpful_el = container.find("span", {"data-hook": "helpful-vote-statement"})
                helpful_votes = 0
                if helpful_el:
                    helpful_text = helpful_el.get_text()
                    match = re.search(r"(\d+)", helpful_text)
                    if match:
                        helpful_votes = int(match.group(1))
                
                # Generate review ID
                review_id = hashlib.md5(
                    f"{url}_{i}_{review_text[:50]}".encode()
                ).hexdigest()[:12]
                
                reviews.append(RawReview(
                    review_id=f"amz_{review_id}",
                    source=ReviewSource.AMAZON,
                    source_url=url,
                    review_text=review_text,
                    rating=rating,
                    review_date=review_date,
                    reviewer_name=reviewer_name,
                    verified_purchase=verified,
                    helpful_votes=helpful_votes,
                ))
                
            except Exception as e:
                logger.debug(f"Error parsing Amazon review: {e}")
                continue
        
        return reviews
    
    def _extract_target_reviews(
        self, 
        soup: Any, 
        url: str,
        max_reviews: int
    ) -> List[RawReview]:
        """Extract reviews from Target product page."""
        reviews = []
        
        # Target reviews are often loaded dynamically
        # Try to find any review containers
        review_containers = soup.find_all(
            "div", class_=re.compile(r"review", re.I)
        )
        
        for i, container in enumerate(review_containers[:max_reviews]):
            try:
                # Look for rating (stars)
                rating = 3.0
                stars = container.find_all(class_=re.compile(r"star|rating", re.I))
                for star in stars:
                    text = star.get_text() or star.get("aria-label", "")
                    match = re.search(r"(\d+\.?\d*)", str(text))
                    if match:
                        rating = float(match.group(1))
                        break
                
                # Look for review text
                text_el = container.find(class_=re.compile(r"text|body|content", re.I))
                review_text = text_el.get_text().strip() if text_el else ""
                
                if not review_text or len(review_text) < 10:
                    continue
                
                review_id = hashlib.md5(
                    f"{url}_{i}_{review_text[:50]}".encode()
                ).hexdigest()[:12]
                
                reviews.append(RawReview(
                    review_id=f"tgt_{review_id}",
                    source=ReviewSource.PRODUCT_PAGE,
                    source_url=url,
                    review_text=review_text,
                    rating=rating,
                ))
                
            except Exception as e:
                logger.debug(f"Error parsing Target review: {e}")
                continue
        
        return reviews
    
    def _extract_walmart_reviews(
        self, 
        soup: Any, 
        url: str,
        max_reviews: int
    ) -> List[RawReview]:
        """Extract reviews from Walmart product page."""
        # Similar pattern to Target
        return self._extract_generic_reviews(soup, url, max_reviews)
    
    def _extract_generic_reviews(
        self, 
        soup: Any, 
        url: str,
        max_reviews: int
    ) -> List[RawReview]:
        """
        Generic review extraction using Schema.org markup.
        
        Falls back to heuristic search for review-like content.
        """
        reviews = []
        
        # Try Schema.org Review markup
        scripts = soup.find_all("script", {"type": "application/ld+json"})
        for script in scripts:
            try:
                import json
                data = json.loads(script.string)
                if isinstance(data, dict) and data.get("@type") == "Product":
                    review_data = data.get("review", [])
                    if isinstance(review_data, dict):
                        review_data = [review_data]
                    
                    for i, r in enumerate(review_data[:max_reviews]):
                        review_text = r.get("reviewBody", "")
                        if not review_text:
                            continue
                        
                        rating_data = r.get("reviewRating", {})
                        rating = float(rating_data.get("ratingValue", 3))
                        
                        author = r.get("author", {})
                        reviewer_name = author.get("name") if isinstance(author, dict) else str(author)
                        
                        review_id = hashlib.md5(
                            f"{url}_{i}_{review_text[:50]}".encode()
                        ).hexdigest()[:12]
                        
                        reviews.append(RawReview(
                            review_id=f"gen_{review_id}",
                            source=ReviewSource.PRODUCT_PAGE,
                            source_url=url,
                            review_text=review_text,
                            rating=max(1.0, min(5.0, rating)),
                            reviewer_name=reviewer_name,
                        ))
            except Exception:
                continue
        
        # If no Schema.org reviews, try heuristic search
        if not reviews:
            review_containers = soup.find_all(
                ["div", "article", "li"],
                class_=re.compile(r"review|comment|feedback", re.I)
            )
            
            for i, container in enumerate(review_containers[:max_reviews]):
                text = container.get_text().strip()
                if len(text) > 50:  # Minimum review length
                    review_id = hashlib.md5(
                        f"{url}_{i}_{text[:50]}".encode()
                    ).hexdigest()[:12]
                    
                    reviews.append(RawReview(
                        review_id=f"gen_{review_id}",
                        source=ReviewSource.PRODUCT_PAGE,
                        source_url=url,
                        review_text=text[:2000],  # Limit length
                        rating=3.0,  # Default neutral
                    ))
        
        return reviews
    
    async def close(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
