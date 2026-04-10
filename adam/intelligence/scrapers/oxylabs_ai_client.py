# =============================================================================
# Oxylabs AI Studio Client
# Location: adam/intelligence/scrapers/oxylabs_ai_client.py
# =============================================================================

"""
Oxylabs AI Studio Client - Enterprise-Grade Review Collection

Uses the new Oxylabs AI Studio SDK (pip install oxylabs-ai-studio) which provides:
- AI-powered scraping with natural language prompts
- Automatic anti-bot bypass
- Structured data extraction
- No username/password - just API key

SDK Reference: https://github.com/oxylabs/oxylabs-ai-studio-py
"""

import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


# =============================================================================
# DATA MODELS (compatible with existing codebase)
# =============================================================================

@dataclass
class OxylabsReview:
    """A single review from Oxylabs AI Studio."""
    review_text: str
    rating: Optional[float] = None
    reviewer_name: Optional[str] = None
    review_date: Optional[str] = None
    verified_purchase: bool = False
    helpful_votes: int = 0
    review_title: Optional[str] = None


@dataclass  
class ScrapedProduct:
    """Product data from Oxylabs AI Studio."""
    source: str  # "amazon", "walmart", etc.
    product_id: str
    title: str
    brand: Optional[str] = None
    price: Optional[float] = None
    rating: Optional[float] = None
    reviews_count: int = 0
    description: Optional[str] = None
    category: Optional[str] = None
    url: Optional[str] = None
    reviews: List[OxylabsReview] = field(default_factory=list)
    scraped_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    # Additional fields expected by review_orchestrator
    images: List[str] = field(default_factory=list)
    bullet_points: List[str] = field(default_factory=list)


# =============================================================================
# OXYLABS AI STUDIO CLIENT
# =============================================================================

class OxylabsAIClient:
    """
    Client for Oxylabs AI Studio SDK.
    
    Uses natural language prompts to extract product data and reviews.
    Only requires an API key (no username/password).
    
    Target: 50 reviews for robust psychological analysis.
    """
    
    # Default number of reviews to request for robust psychological analysis
    DEFAULT_MAX_REVIEWS = 50
    
    # Schema for extracting Amazon product reviews
    REVIEW_SCHEMA = {
        "type": "object",
        "properties": {
            "product_title": {"type": "string"},
            "brand": {"type": "string"},
            "price": {"type": "string"},
            "rating": {"type": "number"},
            "total_reviews": {"type": "integer"},
            "reviews": {
                "type": "array",
                "description": "Extract up to 50 customer reviews for psychological analysis",
                "maxItems": 50,  # Request up to 50 reviews
                "items": {
                    "type": "object",
                    "properties": {
                        "review_text": {"type": "string"},
                        "rating": {"type": "number"},
                        "reviewer_name": {"type": "string"},
                        "review_date": {"type": "string"},
                        "review_title": {"type": "string"},
                        "verified_purchase": {"type": "boolean"},
                        "helpful_votes": {"type": "integer"}
                    }
                }
            }
        }
    }
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the Oxylabs AI Studio client.
        
        Args:
            api_key: Oxylabs API key. If not provided, reads from OXYLABS_API_KEY env var.
        """
        self.api_key = api_key or os.environ.get("OXYLABS_API_KEY")
        
        if not self.api_key:
            raise ValueError(
                "Oxylabs API key required. Set OXYLABS_API_KEY environment variable "
                "or pass api_key to constructor."
            )
        
        self._scraper = None
        self._browser_agent = None
        logger.info("OxylabsAIClient initialized with API key")
    
    def _get_scraper(self):
        """Lazy initialization of AI Scraper."""
        if self._scraper is None:
            try:
                from oxylabs_ai_studio.apps.ai_scraper import AiScraper
                self._scraper = AiScraper(api_key=self.api_key)
                logger.info("Oxylabs AI Scraper initialized")
            except ImportError:
                raise ImportError(
                    "oxylabs-ai-studio package not installed. "
                    "Run: pip install oxylabs-ai-studio"
                )
        return self._scraper
    
    def _get_browser_agent(self):
        """Lazy initialization of Browser Agent for complex interactions."""
        if self._browser_agent is None:
            try:
                from oxylabs_ai_studio.apps.browser_agent import BrowserAgent
                self._browser_agent = BrowserAgent(api_key=self.api_key)
                logger.info("Oxylabs Browser Agent initialized")
            except ImportError:
                raise ImportError(
                    "oxylabs-ai-studio package not installed. "
                    "Run: pip install oxylabs-ai-studio"
                )
        return self._browser_agent
    
    def _extract_asin_from_url(self, url: str) -> Optional[str]:
        """Extract ASIN from Amazon URL."""
        # Pattern: /dp/ASIN or /product/ASIN or /gp/product/ASIN
        patterns = [
            r'/dp/([A-Z0-9]{10})',
            r'/product/([A-Z0-9]{10})',
            r'/gp/product/([A-Z0-9]{10})',
        ]
        import re
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None
    
    def get_amazon_product(
        self,
        asin: str,
        geo_location: str = "United States",
        max_reviews: int = 50,
    ) -> ScrapedProduct:
        """
        Get Amazon product data including reviews using AI scraping.
        
        Args:
            asin: Amazon Standard Identification Number
            geo_location: Country for localized results
            max_reviews: Maximum number of reviews to extract (default: 50 for robust analysis)
            
        Returns:
            ScrapedProduct with reviews (up to max_reviews)
        """
        url = f"https://www.amazon.com/dp/{asin}"
        logger.info(f"Scraping Amazon product {asin} via Oxylabs AI Studio (requesting {max_reviews} reviews)")
        
        scraper = self._get_scraper()
        
        try:
            # Use AI scraper with natural language prompt
            result = scraper.scrape(
                url=url,
                output_format="json",
                schema=self.REVIEW_SCHEMA,
                render_javascript=True,
                geo_location=geo_location,
            )
            
            # Handle None or missing data
            if result is None:
                logger.warning(f"Oxylabs returned None for {asin}")
                return ScrapedProduct(
                    source="amazon",
                    product_id=asin,
                    title="",
                    url=url,
                    reviews=[],
                )
            
            # Extract data from result (may be wrapped in result object)
            data = None
            if hasattr(result, 'data') and result.data is not None:
                data = result.data
            elif isinstance(result, dict):
                data = result
            else:
                logger.warning(f"Unexpected result type from Oxylabs: {type(result)}")
                return ScrapedProduct(
                    source="amazon",
                    product_id=asin,
                    title="",
                    url=url,
                    reviews=[],
                )
            
            # Parse the response
            reviews = []
            if isinstance(data, dict):
                # Extract reviews safely
                raw_reviews = data.get("reviews") or []
                for r in raw_reviews:
                    if r and isinstance(r, dict) and r.get("review_text"):
                        reviews.append(OxylabsReview(
                            review_text=r.get("review_text", ""),
                            rating=r.get("rating"),
                            reviewer_name=r.get("reviewer_name"),
                            review_date=r.get("review_date"),
                            review_title=r.get("review_title"),
                            verified_purchase=r.get("verified_purchase", False),
                            helpful_votes=r.get("helpful_votes", 0),
                        ))
                
                logger.info(f"Parsed {len(reviews)} reviews from Oxylabs response")
                
                return ScrapedProduct(
                    source="amazon",
                    product_id=asin,
                    title=data.get("product_title") or "",
                    brand=data.get("brand"),
                    price=self._parse_price(data.get("price")),
                    rating=data.get("rating"),
                    reviews_count=data.get("total_reviews") or len(reviews),
                    description=data.get("description"),
                    url=url,
                    reviews=reviews,
                    images=data.get("images") or [],
                    bullet_points=data.get("bullet_points") or [],
                )
            
            # Data is not a dict
            logger.warning(f"Unexpected data format from Oxylabs: {type(data)}")
            return ScrapedProduct(
                source="amazon",
                product_id=asin,
                title="",
                url=url,
                reviews=[],
            )
            
        except Exception as e:
            logger.error(f"Oxylabs AI scraping failed for {asin}: {e}")
            raise
    
    def search_amazon(
        self,
        query: str,
        geo_location: str = "United States",
    ) -> List[Dict[str, Any]]:
        """
        Search Amazon for products.
        
        Args:
            query: Search query
            geo_location: Country for localized results
            
        Returns:
            List of product search results
        """
        url = f"https://www.amazon.com/s?k={query.replace(' ', '+')}"
        logger.info(f"Searching Amazon for: {query}")
        
        scraper = self._get_scraper()
        
        search_schema = {
            "type": "object",
            "properties": {
                "products": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "asin": {"type": "string"},
                            "price": {"type": "string"},
                            "rating": {"type": "number"},
                            "reviews_count": {"type": "integer"},
                        }
                    }
                }
            }
        }
        
        try:
            result = scraper.scrape(
                url=url,
                output_format="json",
                schema=search_schema,
                render_javascript=True,
                geo_location=geo_location,
            )
            
            data = result.data if hasattr(result, 'data') else result
            return data.get("products", []) if isinstance(data, dict) else []
            
        except Exception as e:
            logger.error(f"Amazon search failed: {e}")
            return []
    
    def get_product_with_reviews(
        self,
        url: Optional[str] = None,
        product_name: Optional[str] = None,
        brand: Optional[str] = None,
        use_cache: bool = True,
        max_reviews: int = 50,
    ) -> ScrapedProduct:
        """
        Get product with reviews - main entry point.
        
        Smart handling:
        - If Amazon URL provided, scrape directly
        - If other URL, search Amazon for the product
        - If no URL, search Amazon by product name
        
        Args:
            url: Product page URL (optional)
            product_name: Product name for search (optional)
            brand: Brand name (optional)
            use_cache: Whether to use cached results (not yet implemented)
            max_reviews: Maximum reviews to extract (default: 50 for robust analysis)
            
        Returns:
            ScrapedProduct with up to max_reviews reviews
        """
        # Try to extract ASIN from Amazon URL
        if url:
            parsed = urlparse(url)
            if "amazon" in parsed.netloc.lower():
                asin = self._extract_asin_from_url(url)
                if asin:
                    logger.info(f"Detected Amazon URL with ASIN: {asin}")
                    return self.get_amazon_product(asin, max_reviews=max_reviews)
        
        # Search Amazon for the product
        search_query = f"{brand} {product_name}" if brand else product_name
        if search_query:
            logger.info(f"Searching Amazon for: {search_query}")
            results = self.search_amazon(search_query)
            
            if results:
                # Get the first result
                first = results[0]
                asin = first.get("asin")
                if asin:
                    return self.get_amazon_product(asin, max_reviews=max_reviews)
        
        # Return empty product if nothing found
        return ScrapedProduct(
            source="unknown",
            product_id="",
            title=product_name or "",
            brand=brand,
            reviews=[],
        )
    
    def _parse_price(self, price_str: Optional[str]) -> Optional[float]:
        """Parse price string to float."""
        if not price_str:
            return None
        try:
            import re
            # Extract numeric value from price string
            match = re.search(r'[\d,]+\.?\d*', price_str.replace(',', ''))
            if match:
                return float(match.group())
        except:
            pass
        return None


# =============================================================================
# SINGLETON ACCESSOR
# =============================================================================

_oxylabs_ai_client: Optional[OxylabsAIClient] = None


def get_oxylabs_ai_client() -> OxylabsAIClient:
    """Get or create the singleton OxylabsAIClient."""
    global _oxylabs_ai_client
    
    if _oxylabs_ai_client is None:
        _oxylabs_ai_client = OxylabsAIClient()
    
    return _oxylabs_ai_client
