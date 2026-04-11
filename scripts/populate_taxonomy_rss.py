#!/usr/bin/env python3
"""
RSS-Based Taxonomy Population — Legitimate Content Access
===========================================================

Instead of fighting anti-bot systems, uses legitimate RSS feeds to get
article content. Most major publishers provide full RSS feeds for every
section — explicitly designed for machine consumption.

For each article:
1. Get title + description from RSS (25-67 words)
2. Try AMP version of the URL for full text (bypasses most anti-bot)
3. Fall back to httpx fetch with gentle headers
4. Score with 20-dim edge extraction
5. Extract category from feed name, author from content
6. Record into taxonomy hierarchy

Usage:
    PYTHONPATH=. python3 scripts/populate_taxonomy_rss.py
    PYTHONPATH=. python3 scripts/populate_taxonomy_rss.py --domain cnn.com
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import random
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("rss_taxonomy")

# ════════════════════════════════════════════════════════════════════
# RSS FEED REGISTRY — legitimate content access for major publishers
# ════════════════════════════════════════════════════════════════════

_RSS_FEEDS = {
    "cnn.com": [
        ("top_stories", "http://rss.cnn.com/rss/cnn_topstories.rss"),
        ("world", "http://rss.cnn.com/rss/cnn_world.rss"),
        ("us", "http://rss.cnn.com/rss/cnn_us.rss"),
        ("business", "http://rss.cnn.com/rss/money_latest.rss"),
        ("politics", "http://rss.cnn.com/rss/cnn_allpolitics.rss"),
        ("health", "http://rss.cnn.com/rss/cnn_health.rss"),
        ("entertainment", "http://rss.cnn.com/rss/cnn_showbiz.rss"),
        ("technology", "http://rss.cnn.com/rss/cnn_tech.rss"),
        ("travel", "http://rss.cnn.com/rss/cnn_travel.rss"),
    ],
    "nytimes.com": [
        ("home", "https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml"),
        ("world", "https://rss.nytimes.com/services/xml/rss/nyt/World.xml"),
        ("us", "https://rss.nytimes.com/services/xml/rss/nyt/US.xml"),
        ("business", "https://rss.nytimes.com/services/xml/rss/nyt/Business.xml"),
        ("technology", "https://rss.nytimes.com/services/xml/rss/nyt/Technology.xml"),
        ("sports", "https://rss.nytimes.com/services/xml/rss/nyt/Sports.xml"),
        ("health", "https://rss.nytimes.com/services/xml/rss/nyt/Health.xml"),
        ("opinion", "https://rss.nytimes.com/services/xml/rss/nyt/Opinion.xml"),
        ("science", "https://rss.nytimes.com/services/xml/rss/nyt/Science.xml"),
        ("arts", "https://rss.nytimes.com/services/xml/rss/nyt/Arts.xml"),
    ],
    "espn.com": [
        ("top", "https://www.espn.com/espn/rss/news"),
        ("nfl", "https://www.espn.com/espn/rss/nfl/news"),
        ("nba", "https://www.espn.com/espn/rss/nba/news"),
        ("mlb", "https://www.espn.com/espn/rss/mlb/news"),
    ],
    "techcrunch.com": [
        ("all", "https://techcrunch.com/feed/"),
    ],
    "bloomberg.com": [
        ("markets", "https://feeds.bloomberg.com/markets/news.rss"),
    ],
    "wsj.com": [
        ("opinion", "https://feeds.a.dj.wsj.com/rss/RSSOpinion.xml"),
        ("world", "https://feeds.a.dj.wsj.com/rss/RSSWorldNews.xml"),
        ("business", "https://feeds.a.dj.wsj.com/rss/WSJcomUSBusiness.xml"),
        ("markets", "https://feeds.a.dj.wsj.com/rss/RSSMarketsMain.xml"),
        ("technology", "https://feeds.a.dj.wsj.com/rss/RSSWSJD.xml"),
    ],
    "reuters.com": [
        ("world", "https://www.reutersagency.com/feed/?best-topics=world&post_type=best"),
        ("business", "https://www.reutersagency.com/feed/?best-topics=business-finance&post_type=best"),
        ("tech", "https://www.reutersagency.com/feed/?best-topics=tech&post_type=best"),
    ],
    "bbc.com": [
        ("top", "https://feeds.bbci.co.uk/news/rss.xml"),
        ("world", "https://feeds.bbci.co.uk/news/world/rss.xml"),
        ("business", "https://feeds.bbci.co.uk/news/business/rss.xml"),
        ("technology", "https://feeds.bbci.co.uk/news/technology/rss.xml"),
        ("science", "https://feeds.bbci.co.uk/news/science_and_environment/rss.xml"),
        ("entertainment", "https://feeds.bbci.co.uk/news/entertainment_and_arts/rss.xml"),
        ("health", "https://feeds.bbci.co.uk/news/health/rss.xml"),
    ],
    "foxnews.com": [
        ("latest", "https://moxie.foxnews.com/google-publisher/latest.xml"),
        ("politics", "https://moxie.foxnews.com/google-publisher/politics.xml"),
        ("sports", "https://moxie.foxnews.com/google-publisher/sports.xml"),
        ("entertainment", "https://moxie.foxnews.com/google-publisher/entertainment.xml"),
        ("health", "https://moxie.foxnews.com/google-publisher/health.xml"),
        ("science", "https://moxie.foxnews.com/google-publisher/science.xml"),
        ("travel", "https://moxie.foxnews.com/google-publisher/travel.xml"),
    ],
    "washingtonpost.com": [
        ("national", "https://feeds.washingtonpost.com/rss/national"),
        ("world", "https://feeds.washingtonpost.com/rss/world"),
        ("business", "https://feeds.washingtonpost.com/rss/business"),
        ("technology", "https://feeds.washingtonpost.com/rss/business/technology"),
        ("politics", "https://feeds.washingtonpost.com/rss/politics"),
        ("opinions", "https://feeds.washingtonpost.com/rss/opinions"),
        ("sports", "https://feeds.washingtonpost.com/rss/sports"),
        ("entertainment", "https://feeds.washingtonpost.com/rss/entertainment"),
        ("lifestyle", "https://feeds.washingtonpost.com/rss/lifestyle"),
    ],
    "usatoday.com": [
        ("home", "http://rssfeeds.usatoday.com/UsatodaycomNation-TopStories"),
        ("sports", "http://rssfeeds.usatoday.com/UsatodaycomSports-TopStories"),
        ("money", "http://rssfeeds.usatoday.com/UsatodaycomMoney-TopStories"),
        ("life", "http://rssfeeds.usatoday.com/UsatodaycomLife-TopStories"),
        ("tech", "http://rssfeeds.usatoday.com/UsatodaycomTech-TopStories"),
        ("travel", "http://rssfeeds.usatoday.com/UsatodaycomTravel-TopStories"),
    ],
    "cnbc.com": [
        ("top", "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100003114"),
        ("business", "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10001147"),
        ("technology", "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=19854910"),
        ("health", "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10000108"),
    ],
    "nbcnews.com": [
        ("top", "https://feeds.nbcnews.com/nbcnews/public/news"),
        ("world", "https://feeds.nbcnews.com/nbcnews/public/world"),
        ("us", "https://feeds.nbcnews.com/nbcnews/public/us-news"),
        ("politics", "https://feeds.nbcnews.com/nbcnews/public/politics"),
        ("health", "https://feeds.nbcnews.com/nbcnews/public/health"),
        ("tech", "https://feeds.nbcnews.com/nbcnews/public/tech"),
        ("science", "https://feeds.nbcnews.com/nbcnews/public/science"),
        ("business", "https://feeds.nbcnews.com/nbcnews/public/business"),
    ],
    "apnews.com": [
        ("top", "https://rsshub.app/apnews/topics/apf-topnews"),
    ],
    "forbes.com": [
        ("all", "https://www.forbes.com/real-time/feed2/"),
    ],
    "wired.com": [
        ("all", "https://www.wired.com/feed/rss"),
    ],
    "theverge.com": [
        ("all", "https://www.theverge.com/rss/index.xml"),
    ],
    "arstechnica.com": [
        ("all", "https://feeds.arstechnica.com/arstechnica/index"),
    ],
    "healthline.com": [
        ("nutrition", "https://www.healthline.com/rss/nutrition"),
        ("health", "https://www.healthline.com/rss/health-news"),
        ("fitness", "https://www.healthline.com/rss/fitness"),
    ],
    "webmd.com": [
        ("health", "https://rssfeeds.webmd.com/rss/rss.aspx?RSSSource=RSS_PUBLIC"),
    ],
    "investopedia.com": [
        ("all", "https://www.investopedia.com/feedbuilder/feed/getfeed?feedName=rss_headline"),
    ],
    "variety.com": [
        ("all", "https://variety.com/feed/"),
    ],
    "people.com": [
        ("all", "https://people.com/feed/"),
    ],
}


def _parse_rss_items(xml_text: str, category: str, domain: str) -> List[Dict[str, Any]]:
    """Parse RSS XML into article items with title, description, link, author."""
    items = []

    # Split into <item> or <entry> blocks
    item_blocks = re.findall(r"<item[^>]*>(.*?)</item>", xml_text, re.DOTALL)
    if not item_blocks:
        item_blocks = re.findall(r"<entry[^>]*>(.*?)</entry>", xml_text, re.DOTALL)

    for block in item_blocks:
        title = ""
        desc = ""
        link = ""
        author = ""

        # Title
        m = re.search(r"<title[^>]*>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</title>", block, re.DOTALL)
        if m:
            title = re.sub(r"<[^>]+>", "", m.group(1)).strip()

        # Description
        m = re.search(r"<description[^>]*>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</description>", block, re.DOTALL)
        if not m:
            m = re.search(r"<summary[^>]*>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</summary>", block, re.DOTALL)
        if not m:
            m = re.search(r"<content[^>]*>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</content>", block, re.DOTALL)
        if m:
            desc = re.sub(r"<[^>]+>", "", m.group(1)).strip()

        # Link
        m = re.search(r"<link[^>]*>(https?://[^<]+)</link>", block)
        if not m:
            m = re.search(r'<link[^>]+href="(https?://[^"]+)"', block)
        if m:
            link = m.group(1).strip()

        # Author
        m = re.search(r"<(?:author|dc:creator)[^>]*>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</(?:author|dc:creator)>", block, re.DOTALL)
        if m:
            author_text = re.sub(r"<[^>]+>", "", m.group(1)).strip()
            # Clean "By Author Name" format
            author = re.sub(r"^by\s+", "", author_text, flags=re.IGNORECASE).strip()

        if title and len(title) > 10:
            scorable_text = f"{title}. {desc}" if desc else title
            items.append({
                "title": title,
                "description": desc,
                "link": link,
                "author": author,
                "category": category,
                "domain": domain,
                "scorable_text": scorable_text,
                "word_count": len(scorable_text.split()),
            })

    return items


async def fetch_full_text(url: str, client) -> Optional[str]:
    """Try to fetch full article text via AMP or direct fetch."""
    if not url:
        return None

    # Strategy 1: Google AMP cache
    try:
        # Convert URL to AMP cache URL
        from urllib.parse import urlparse
        parsed = urlparse(url)
        amp_url = f"https://{parsed.netloc}.cdn.ampproject.org/v/s/{parsed.netloc}{parsed.path}?amp_js_v=0.1"
        resp = await client.get(amp_url, headers={
            "User-Agent": "Mozilla/5.0 (compatible; ADAM/1.0)"
        })
        if resp.status_code == 200 and len(resp.text) > 500:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(resp.text, "html.parser")
            for tag in soup(["script", "style", "nav", "footer", "header"]):
                tag.decompose()
            main = soup.find("article") or soup.find("main") or soup.find("body")
            if main:
                text = main.get_text(separator=" ", strip=True)
                text = " ".join(text.split())[:8000]
                if len(text.split()) > 50:
                    return text
    except Exception:
        pass

    # Strategy 2: Direct fetch with gentle headers
    try:
        resp = await client.get(url, headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml",
        })
        if resp.status_code == 200 and "text/html" in resp.headers.get("content-type", ""):
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(resp.text, "html.parser")
            for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
                tag.decompose()
            for sel in ["[class*='ad-']", "[class*='sidebar']", "[class*='newsletter']"]:
                for tag in soup.select(sel):
                    tag.decompose()
            main = soup.find("article") or soup.find("main") or soup.find("body")
            if main:
                text = main.get_text(separator=" ", strip=True)
                text = " ".join(text.split())[:8000]
                if len(text.split()) > 50:
                    return text
    except Exception:
        pass

    return None


async def process_domain(domain: str, max_articles: int = 60) -> Dict[str, Any]:
    """Process a domain via RSS feeds — score articles, build taxonomy."""
    import httpx
    from adam.intelligence.page_edge_scoring import score_page_full_width
    from adam.intelligence.page_intelligence import profile_page_content, get_page_intelligence_cache
    from adam.intelligence.domain_taxonomy import (
        extract_article_metadata, get_domain_taxonomy, ArticleMetadata,
    )

    feeds = _RSS_FEEDS.get(domain, [])
    if not feeds:
        return {"domain": domain, "articles": 0, "note": "No RSS feeds registered"}

    taxonomy = get_domain_taxonomy(domain)
    cache = get_page_intelligence_cache()

    stats = {
        "domain": domain,
        "articles_scored": 0,
        "articles_with_full_text": 0,
        "categories": set(),
        "authors": set(),
        "feeds_processed": 0,
    }

    all_items = []

    async with httpx.AsyncClient(timeout=12, follow_redirects=True) as client:
        # Phase 1: Collect articles from all RSS feeds
        for feed_category, feed_url in feeds:
            try:
                resp = await client.get(feed_url, headers={
                    "User-Agent": "Mozilla/5.0 (compatible; ADAM/1.0)"
                })
                if resp.status_code == 200:
                    items = _parse_rss_items(resp.text, feed_category, domain)
                    all_items.extend(items)
                    stats["feeds_processed"] += 1
            except Exception as e:
                logger.debug("Feed %s failed: %s", feed_url, type(e).__name__)
            await asyncio.sleep(0.5)

        logger.info("  %s: %d articles from %d/%d feeds",
                     domain, len(all_items), stats["feeds_processed"], len(feeds))

        # Deduplicate by title
        seen_titles = set()
        unique_items = []
        for item in all_items:
            title_key = item["title"][:50].lower()
            if title_key not in seen_titles:
                seen_titles.add(title_key)
                unique_items.append(item)

        # Phase 2: Score each article
        for item in unique_items[:max_articles]:
            try:
                text = item["scorable_text"]

                # Try to get full text for better scoring
                if item["word_count"] < 80 and item.get("link"):
                    full_text = await fetch_full_text(item["link"], client)
                    if full_text:
                        text = full_text
                        stats["articles_with_full_text"] += 1
                    await asyncio.sleep(random.uniform(0.8, 1.5))

                # Score with 20-dim edge extraction
                edge_profile = score_page_full_width(text=text, url=item.get("link", ""))

                # Also get standard profile for page cache storage
                profile = profile_page_content(
                    url=item.get("link", f"https://{domain}/"),
                    text_content=text,
                    title=item["title"],
                )

                # Build metadata for taxonomy
                meta = ArticleMetadata(
                    url=item.get("link", ""),
                    domain=domain,
                    category=item["category"],
                    title=item["title"],
                    authors=[item["author"]] if item.get("author") else [],
                    word_count=len(text.split()),
                    edge_dimensions=edge_profile.dimensions,
                    ndf_vector=profile.construct_activations,
                    mechanism_adjustments=profile.mechanism_adjustments,
                    mindset=profile.mindset,
                    confidence=edge_profile.confidence,
                )

                # Record into taxonomy hierarchy
                result = taxonomy.record_article(meta)

                # Store in page cache
                cache.store(profile)

                stats["articles_scored"] += 1
                stats["categories"].add(item["category"])
                if item.get("author"):
                    stats["authors"].add(item["author"])

                if stats["articles_scored"] % 20 == 0:
                    logger.info("  %s: %d scored | cats=%s | authors=%d",
                                domain, stats["articles_scored"],
                                sorted(stats["categories"])[:6], len(stats["authors"]))

            except Exception as e:
                logger.debug("Article scoring failed: %s", type(e).__name__)

    stats["categories"] = sorted(stats["categories"])
    stats["authors"] = sorted(list(stats["authors"])[:20])

    logger.info("  %s DONE: %d scored (%d full text), %d categories, %d authors",
                domain, stats["articles_scored"], stats["articles_with_full_text"],
                len(stats["categories"]), len(stats["authors"]))

    return stats


async def run(args):
    logger.info("=" * 60)
    logger.info("RSS-BASED TAXONOMY POPULATION")
    logger.info("=" * 60)

    if args.domain:
        domains = [args.domain]
    else:
        domains = list(_RSS_FEEDS.keys())

    logger.info("Domains: %d, Max articles/domain: %d", len(domains), args.max_articles)
    start = time.time()

    all_stats = []
    total_scored = 0

    for domain in domains:
        stats = await process_domain(domain, args.max_articles)
        all_stats.append(stats)
        total_scored += stats["articles_scored"]

    elapsed = time.time() - start

    logger.info("")
    logger.info("=" * 60)
    logger.info("RESULTS")
    logger.info("=" * 60)
    for s in all_stats:
        cats = s["categories"] if isinstance(s["categories"], list) else sorted(s["categories"])
        logger.info("  %-25s scored=%-4d full_text=%-4d cats=%-3d authors=%-3d",
                     s["domain"], s["articles_scored"],
                     s.get("articles_with_full_text", 0),
                     len(cats), len(s.get("authors", [])))

    logger.info("")
    logger.info("TOTAL: %d articles scored in %.0fs", total_scored, elapsed)

    # Check taxonomy status
    import redis
    r = redis.Redis(host="localhost", port=6379, decode_responses=True)
    cats = len(r.keys("informativ:taxonomy:*:cat:*"))
    authors = len(r.keys("informativ:taxonomy:*:author:*"))
    reliable = sum(1 for k in r.keys("informativ:taxonomy:*:cat:*")
                   if int(r.hget(k, "observation_count") or 0) >= 5)
    logger.info("TAXONOMY: %d categories (%d reliable), %d authors", cats, reliable, authors)


def main():
    parser = argparse.ArgumentParser(description="RSS-based taxonomy population")
    parser.add_argument("--domain", type=str, default="",
                        help="Single domain to process")
    parser.add_argument("--max-articles", type=int, default=50,
                        help="Max articles per domain (default: 50)")
    args = parser.parse_args()
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
