# =============================================================================
# ADAM Social Media Scraper
# Location: adam/intelligence/scrapers/social_scraper.py
# =============================================================================

"""
SOCIAL MEDIA SCRAPER

Collects social signals from Reddit and other platforms for relationship intelligence.

This provides Channel 2 (Social Signals) for the 5-Channel Observation Framework:
- Channel 1: Customer Reviews (existing)
- Channel 2: Social Signals (THIS FILE) 
- Channel 3: Self-Expression (extracted from channels 1-2)
- Channel 4: Brand Positioning (product page analysis)
- Channel 5: Advertising (output)

Social signals reveal HOW consumers talk about brands in social contexts:
- Different from reviews (social proof vs purchase justification)
- Identity signaling (what they want others to know)
- Tribal markers (community belonging)
- Emotional expression (less filtered than reviews)

Uses Oxylabs AI Studio for reliable scraping.
"""

import asyncio
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# =============================================================================
# DATA MODELS
# =============================================================================

@dataclass
class SocialPost:
    """A social media post with metadata."""
    platform: str  # "reddit", "twitter", etc.
    post_id: str
    text: str
    author: Optional[str] = None
    subreddit: Optional[str] = None  # Reddit-specific
    score: int = 0  # Upvotes/likes
    comment_count: int = 0
    created_at: Optional[str] = None
    url: Optional[str] = None
    post_type: str = "comment"  # "post", "comment", "reply"
    parent_id: Optional[str] = None


@dataclass
class SocialSearchResult:
    """Results from social media search."""
    brand: str
    product: Optional[str] = None
    platform: str = "reddit"
    posts: List[SocialPost] = field(default_factory=list)
    total_found: int = 0
    scraped_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    @property
    def post_count(self) -> int:
        return len(self.posts)


# =============================================================================
# REDDIT SCRAPER (VIA OXYLABS)
# =============================================================================

class RedditScraper:
    """
    Scrapes Reddit discussions about brands/products using Oxylabs AI Studio.
    
    Reddit is valuable for relationship intelligence because:
    - Honest opinions (pseudonymous)
    - Community context (subreddits = tribes)
    - Discussion threads (see debates)
    - Voting signals (community validation)
    """
    
    # Schema for extracting Reddit posts/comments
    REDDIT_SEARCH_SCHEMA = {
        "type": "object",
        "properties": {
            "posts": {
                "type": "array",
                "description": "Extract posts and comments discussing the brand/product",
                "maxItems": 30,
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "text": {"type": "string"},
                        "author": {"type": "string"},
                        "subreddit": {"type": "string"},
                        "score": {"type": "integer"},
                        "comment_count": {"type": "integer"},
                        "post_url": {"type": "string"},
                        "post_type": {"type": "string"},
                    }
                }
            }
        }
    }
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize Reddit scraper with Oxylabs API key."""
        self.api_key = api_key or os.environ.get("OXYLABS_API_KEY")
        self._scraper = None
        
        if not self.api_key:
            logger.warning("No OXYLABS_API_KEY - Reddit scraping will be unavailable")
    
    def _get_scraper(self):
        """Lazy initialization of Oxylabs AI Scraper."""
        if self._scraper is None and self.api_key:
            try:
                from oxylabs_ai_studio.apps.ai_scraper import AiScraper
                self._scraper = AiScraper(api_key=self.api_key)
                logger.info("Oxylabs AI Scraper initialized for Reddit")
            except ImportError:
                logger.warning("oxylabs-ai-studio package not installed")
        return self._scraper
    
    def search_brand(
        self,
        brand: str,
        product: Optional[str] = None,
        max_posts: int = 30,
        subreddits: Optional[List[str]] = None,
    ) -> SocialSearchResult:
        """
        Search Reddit for discussions about a brand/product.
        
        Args:
            brand: Brand name to search for
            product: Optional product name to narrow search
            max_posts: Maximum posts to retrieve
            subreddits: Optional list of subreddits to search
            
        Returns:
            SocialSearchResult with posts
        """
        if not self.api_key:
            logger.warning("Reddit scraping unavailable - no API key")
            return SocialSearchResult(brand=brand, product=product, posts=[])
        
        scraper = self._get_scraper()
        if not scraper:
            return SocialSearchResult(brand=brand, product=product, posts=[])
        
        # Build search query
        query = brand
        if product:
            query = f"{brand} {product}"
        
        # Use Reddit search URL
        search_url = f"https://www.reddit.com/search/?q={query.replace(' ', '%20')}&sort=relevance&t=year"
        
        logger.info(f"Searching Reddit for: {query}")
        
        try:
            result = scraper.scrape(
                url=search_url,
                output_format="json",
                schema=self.REDDIT_SEARCH_SCHEMA,
                render_javascript=True,
                geo_location="United States",
            )
            
            # Handle result
            if result is None:
                logger.warning("Reddit search returned None")
                return SocialSearchResult(brand=brand, product=product, posts=[])
            
            data = result.data if hasattr(result, 'data') else result
            
            if not isinstance(data, dict):
                logger.warning(f"Unexpected Reddit data format: {type(data)}")
                return SocialSearchResult(brand=brand, product=product, posts=[])
            
            # Parse posts
            posts = []
            raw_posts = data.get("posts") or []
            
            for p in raw_posts[:max_posts]:
                if not p or not isinstance(p, dict):
                    continue
                    
                text = p.get("text") or p.get("title") or ""
                if not text or len(text) < 10:
                    continue
                
                posts.append(SocialPost(
                    platform="reddit",
                    post_id=p.get("post_url", "")[-8:] or f"rd_{len(posts)}",
                    text=text,
                    author=p.get("author"),
                    subreddit=p.get("subreddit"),
                    score=p.get("score", 0),
                    comment_count=p.get("comment_count", 0),
                    url=p.get("post_url"),
                    post_type=p.get("post_type", "post"),
                ))
            
            logger.info(f"Reddit search found {len(posts)} relevant posts for {query}")
            
            return SocialSearchResult(
                brand=brand,
                product=product,
                platform="reddit",
                posts=posts,
                total_found=len(raw_posts),
            )
            
        except Exception as e:
            logger.error(f"Reddit search failed: {e}")
            return SocialSearchResult(brand=brand, product=product, posts=[])
    
    def get_subreddit_posts(
        self,
        subreddit: str,
        brand: str,
        max_posts: int = 20,
    ) -> SocialSearchResult:
        """
        Get posts from a specific subreddit mentioning a brand.
        
        Useful for category-specific discussions (e.g., r/watches for luxury watches).
        """
        if not self.api_key:
            return SocialSearchResult(brand=brand, posts=[])
        
        scraper = self._get_scraper()
        if not scraper:
            return SocialSearchResult(brand=brand, posts=[])
        
        # Search within subreddit
        search_url = f"https://www.reddit.com/r/{subreddit}/search/?q={brand.replace(' ', '%20')}&restrict_sr=1&sort=relevance&t=year"
        
        logger.info(f"Searching r/{subreddit} for: {brand}")
        
        try:
            result = scraper.scrape(
                url=search_url,
                output_format="json",
                schema=self.REDDIT_SEARCH_SCHEMA,
                render_javascript=True,
                geo_location="United States",
            )
            
            data = result.data if hasattr(result, 'data') and result.data else {}
            
            posts = []
            for p in (data.get("posts") or [])[:max_posts]:
                if not p:
                    continue
                text = p.get("text") or p.get("title") or ""
                if text and len(text) >= 10:
                    posts.append(SocialPost(
                        platform="reddit",
                        post_id=p.get("post_url", "")[-8:] or f"rd_{len(posts)}",
                        text=text,
                        author=p.get("author"),
                        subreddit=subreddit,
                        score=p.get("score", 0),
                        comment_count=p.get("comment_count", 0),
                        url=p.get("post_url"),
                        post_type=p.get("post_type", "post"),
                    ))
            
            return SocialSearchResult(
                brand=brand,
                platform="reddit",
                posts=posts,
                total_found=len(posts),
            )
            
        except Exception as e:
            logger.error(f"Subreddit search failed: {e}")
            return SocialSearchResult(brand=brand, posts=[])


# =============================================================================
# SOCIAL SIGNAL AGGREGATOR
# =============================================================================

class SocialSignalAggregator:
    """
    Aggregates social signals from multiple platforms.
    
    Currently supports:
    - Reddit (primary - most useful for brand discussions)
    
    Future:
    - Twitter/X (short-form opinions)
    - Instagram (visual + captions)
    - TikTok (video discussions)
    """
    
    def __init__(self):
        self.reddit_scraper = RedditScraper()
    
    async def collect_social_signals(
        self,
        brand: str,
        product: Optional[str] = None,
        max_posts_per_platform: int = 30,
        relevant_subreddits: Optional[List[str]] = None,
    ) -> Dict[str, SocialSearchResult]:
        """
        Collect social signals from all available platforms.
        
        Args:
            brand: Brand name
            product: Optional product name
            max_posts_per_platform: Max posts per platform
            relevant_subreddits: Optional subreddits to search
            
        Returns:
            Dict mapping platform -> SocialSearchResult
        """
        results = {}
        
        # Reddit - run in thread pool since it's synchronous
        reddit_result = await asyncio.to_thread(
            self.reddit_scraper.search_brand,
            brand=brand,
            product=product,
            max_posts=max_posts_per_platform,
        )
        
        if reddit_result.posts:
            results["reddit"] = reddit_result
            logger.info(f"Collected {len(reddit_result.posts)} Reddit posts for {brand}")
        
        # If specific subreddits provided, search those too
        if relevant_subreddits:
            for subreddit in relevant_subreddits[:3]:  # Max 3 subreddits
                sub_result = await asyncio.to_thread(
                    self.reddit_scraper.get_subreddit_posts,
                    subreddit=subreddit,
                    brand=brand,
                    max_posts=max_posts_per_platform // 2,
                )
                if sub_result.posts:
                    # Merge with main Reddit results
                    if "reddit" in results:
                        # Add posts that aren't duplicates
                        existing_ids = {p.post_id for p in results["reddit"].posts}
                        for post in sub_result.posts:
                            if post.post_id not in existing_ids:
                                results["reddit"].posts.append(post)
                    else:
                        results["reddit"] = sub_result
        
        return results
    
    def get_texts_for_relationship_analysis(
        self,
        results: Dict[str, SocialSearchResult],
    ) -> List[Dict[str, Any]]:
        """
        Convert social search results to format needed for relationship detection.
        
        Returns list of dicts with 'text' and 'channel' keys.
        """
        from adam.intelligence.relationship import ObservationChannel
        
        texts = []
        
        for platform, result in results.items():
            for post in result.posts:
                if post.text and len(post.text) >= 20:
                    texts.append({
                        "text": post.text,
                        "channel": ObservationChannel.SOCIAL_SIGNALS,
                        "source_id": f"{platform}:{post.post_id}",
                        "metadata": {
                            "platform": platform,
                            "subreddit": post.subreddit,
                            "score": post.score,
                            "author": post.author,
                        }
                    })
        
        return texts


# =============================================================================
# FACTORY FUNCTIONS
# =============================================================================

def get_social_aggregator() -> SocialSignalAggregator:
    """Get the social signal aggregator instance."""
    return SocialSignalAggregator()


def get_reddit_scraper() -> RedditScraper:
    """Get the Reddit scraper instance."""
    return RedditScraper()
