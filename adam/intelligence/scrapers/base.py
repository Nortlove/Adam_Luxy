# =============================================================================
# Base Review Scraper
# Location: adam/intelligence/scrapers/base.py
# =============================================================================

"""
Abstract base class for review scrapers.

All scraper implementations (product page, Google, Amazon, Reddit, etc.)
inherit from this base class and implement the scrape() method.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from adam.intelligence.models.customer_intelligence import ReviewSource


class RawReview(BaseModel):
    """
    Raw review data as scraped from a source.
    
    This is the unprocessed form before psychological analysis.
    """
    # Identity
    review_id: str
    source: ReviewSource
    source_url: Optional[str] = None
    
    # Content
    review_text: str
    rating: float = Field(ge=1.0, le=5.0)
    
    # Metadata
    review_date: Optional[datetime] = None
    reviewer_name: Optional[str] = None
    verified_purchase: bool = False
    helpful_votes: int = 0
    
    # Product context
    product_name: Optional[str] = None
    product_variant: Optional[str] = None
    
    # Scrape metadata
    scraped_at: datetime = Field(default_factory=datetime.utcnow)


class ScraperResult(BaseModel):
    """
    Result of a scraping operation.
    
    Contains reviews found plus metadata about the scrape.
    """
    # Source info
    source: ReviewSource
    source_url: Optional[str] = None
    
    # Results
    reviews: List[RawReview] = Field(default_factory=list)
    total_found: int = 0
    
    # Product info (if extracted)
    product_name: Optional[str] = None
    product_description: Optional[str] = None
    product_price: Optional[str] = None
    product_brand: Optional[str] = None
    product_images: List[str] = Field(default_factory=list)
    
    # Scrape metadata
    success: bool = True
    error_message: Optional[str] = None
    scrape_duration_ms: float = 0.0
    scraped_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Rate limiting info
    rate_limited: bool = False
    retry_after_seconds: Optional[int] = None


class BaseReviewScraper(ABC):
    """
    Abstract base class for review scrapers.
    
    Implementations:
    - ProductPageScraper: Scrapes reviews from direct product URLs
    - GoogleReviewScraper: Searches Google for reviews
    - AmazonReviewScraper: Scrapes Amazon product reviews
    - RedditScraper: Searches Reddit for product discussions
    - SocialScraper: Monitors social media mentions
    """
    
    @property
    @abstractmethod
    def source(self) -> ReviewSource:
        """The review source this scraper handles."""
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name for this scraper."""
        pass
    
    @abstractmethod
    async def scrape(
        self,
        product_name: str,
        product_url: Optional[str] = None,
        brand: Optional[str] = None,
        max_reviews: int = 100,
    ) -> ScraperResult:
        """
        Scrape reviews for a product.
        
        Args:
            product_name: Name of the product
            product_url: Direct URL to product (if available)
            brand: Brand name (for search refinement)
            max_reviews: Maximum number of reviews to return
            
        Returns:
            ScraperResult with reviews and metadata
        """
        pass
    
    @abstractmethod
    async def is_available(self) -> bool:
        """
        Check if this scraper is currently available.
        
        May return False if rate limited, credentials missing, etc.
        """
        pass
    
    async def health_check(self) -> dict:
        """
        Perform a health check on this scraper.
        
        Returns dict with status info.
        """
        available = await self.is_available()
        return {
            "scraper": self.name,
            "source": self.source.value,
            "available": available,
            "timestamp": datetime.utcnow().isoformat(),
        }
