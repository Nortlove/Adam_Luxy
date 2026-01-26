# =============================================================================
# ADAM Review Scrapers
# Location: adam/intelligence/scrapers/__init__.py
# =============================================================================

"""
Multi-source review scraping for ADAM platform.

Scrapers gather reviews from multiple sources:
- Product page (direct URL)
- Amazon product reviews (with pagination)
- Google search results for reviews
- Reddit discussions
- Social media mentions

All scrapers implement the BaseReviewScraper interface.
"""

from adam.intelligence.scrapers.base import (
    BaseReviewScraper,
    RawReview,
    ScraperResult,
)
from adam.intelligence.scrapers.product_page import ProductPageScraper
from adam.intelligence.scrapers.amazon_reviews import AmazonReviewsScraper
from adam.intelligence.scrapers.google_reviews import GoogleReviewsScraper
from adam.intelligence.scrapers.aggregator import ReviewAggregator, get_review_aggregator

__all__ = [
    "BaseReviewScraper",
    "RawReview",
    "ScraperResult",
    "ProductPageScraper",
    "AmazonReviewsScraper",
    "GoogleReviewsScraper",
    "ReviewAggregator",
    "get_review_aggregator",
]
