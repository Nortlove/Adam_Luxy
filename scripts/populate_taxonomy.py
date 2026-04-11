#!/usr/bin/env python3
"""
Deep Taxonomy Population — One-Time Intensive Crawl
=====================================================

Aggressively crawls articles from priority publishers to build
statistical depth in the domain taxonomy. Unlike the daily task
(which processes ~15 domains × ~30 articles), this script goes
deep: 50+ articles per domain across all categories.

Strategy:
1. For each domain, fetch the sitemap to get article URLs
2. Distribute URLs across categories (not just the RSS top stories)
3. Fetch, extract metadata, NDF-profile, record into taxonomy
4. Target: 10+ articles per category for reliable centroids

Usage:
    PYTHONPATH=. python3 scripts/populate_taxonomy.py
    PYTHONPATH=. python3 scripts/populate_taxonomy.py --domains cnn.com,foxnews.com
    PYTHONPATH=. python3 scripts/populate_taxonomy.py --articles-per-domain 100
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
from typing import Any, Dict, List, Optional, Set, Tuple

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("taxonomy_populator")

# Priority domains — ordered by ad inventory importance
PRIORITY_DOMAINS = [
    "cnn.com", "foxnews.com", "washingtonpost.com", "nytimes.com",
    "nbcnews.com", "bbc.com", "reuters.com", "usatoday.com",
    "apnews.com", "nypost.com",
    "espn.com", "bleacherreport.com", "cbssports.com",
    "forbes.com", "cnbc.com", "businessinsider.com", "marketwatch.com",
    "techcrunch.com", "theverge.com", "wired.com", "arstechnica.com",
    "cnet.com", "pcmag.com",
    "webmd.com", "healthline.com",
    "people.com", "variety.com", "eonline.com",
    "allrecipes.com", "foodnetwork.com",
    "investopedia.com", "nerdwallet.com", "bankrate.com",
]


async def discover_article_urls(domain: str, target_count: int = 100) -> List[str]:
    """Discover article URLs through multiple strategies."""
    import httpx

    urls: List[str] = []
    seen: Set[str] = set()

    def add_url(url: str):
        if url not in seen and domain in url and url.startswith("http"):
            # Filter out non-article URLs
            if any(skip in url for skip in [".xml", ".json", ".jpg", ".png", ".css", ".js",
                                             "/video/", "/gallery/", "/live-tv", "/search",
                                             "/login", "/signup", "/subscribe", "/404"]):
                return
            seen.add(url)
            urls.append(url)

    async with httpx.AsyncClient(timeout=12, follow_redirects=True) as client:
        headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}

        # Strategy 1: RSS feeds (freshest content)
        rss_patterns = ["/feed", "/rss", "/rss.xml", "/feed/", "/atom.xml"]
        for pattern in rss_patterns:
            try:
                resp = await client.get(f"https://{domain}{pattern}", headers=headers)
                if resp.status_code == 200 and ("<rss" in resp.text[:500] or "<feed" in resp.text[:500]):
                    for link in re.findall(r"<link>([^<]+)</link>", resp.text):
                        add_url(link.strip())
                    for link in re.findall(r'<link[^>]+href="([^"]+)"', resp.text):
                        add_url(link.strip())
                    if urls:
                        logger.info("  RSS: found %d URLs from %s", len(urls), pattern)
                        break
            except Exception:
                pass

        # Strategy 2: Sitemap crawl (deepest coverage)
        sitemap_patterns = [
            "/sitemap.xml", "/sitemap_index.xml", "/news-sitemap.xml",
            "/sitemap-news.xml", "/post-sitemap.xml", "/sitemap-index.xml",
        ]
        for pattern in sitemap_patterns:
            try:
                resp = await client.get(f"https://{domain}{pattern}", headers=headers)
                if resp.status_code != 200:
                    continue

                text = resp.text
                if "<sitemapindex" in text:
                    # Index — fetch child sitemaps (prefer news/post)
                    child_urls = re.findall(r"<loc>(.*?)</loc>", text)
                    # Prioritize: news sitemaps first, then post, then recent
                    news = [u for u in child_urls if "news" in u.lower()]
                    post = [u for u in child_urls if "post" in u.lower() or "article" in u.lower()]
                    recent = [u for u in child_urls if "2026" in u or "2025" in u]
                    targets = news[:3] + post[:2] + recent[:3] + child_urls[:2]
                    targets = list(dict.fromkeys(targets))  # Dedupe preserving order

                    for child_url in targets[:5]:
                        try:
                            child_resp = await client.get(child_url, headers=headers)
                            if child_resp.status_code == 200:
                                for loc in re.findall(r"<loc>(.*?)</loc>", child_resp.text):
                                    if not loc.endswith(".xml"):
                                        add_url(loc.strip())
                        except Exception:
                            pass
                        await asyncio.sleep(0.5)

                elif "<urlset" in text:
                    for loc in re.findall(r"<loc>(.*?)</loc>", text):
                        if not loc.endswith(".xml"):
                            add_url(loc.strip())

                if len(urls) > 20:
                    logger.info("  Sitemap: found %d URLs from %s", len(urls), pattern)
                    break
            except Exception:
                pass

        # Strategy 3: Homepage link extraction (catch-all)
        if len(urls) < target_count // 2:
            try:
                resp = await client.get(f"https://{domain}/", headers=headers)
                if resp.status_code == 200:
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(resp.text, "html.parser")
                    for a in soup.find_all("a", href=True):
                        href = a["href"]
                        if href.startswith("/") and len(href) > 10:
                            add_url(f"https://{domain}{href}")
                        elif href.startswith("http") and domain in href:
                            add_url(href)
            except Exception:
                pass

        # Strategy 4: Section pages (fill gaps)
        sections = ["politics", "business", "health", "technology", "sports",
                     "entertainment", "science", "travel", "style", "opinion",
                     "world", "us", "money", "culture", "food", "lifestyle"]
        for section in sections:
            if len(urls) >= target_count:
                break
            try:
                resp = await client.get(f"https://{domain}/{section}", headers=headers)
                if resp.status_code == 200 and "text/html" in resp.headers.get("content-type", ""):
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(resp.text, "html.parser")
                    for a in soup.find_all("a", href=True):
                        href = a["href"]
                        if href.startswith("/") and len(href) > 20:
                            add_url(f"https://{domain}{href}")
                        elif href.startswith("http") and domain in href and len(href) > 40:
                            add_url(href)
            except Exception:
                pass
            await asyncio.sleep(0.5)

    # Shuffle to distribute across categories (not just latest)
    random.shuffle(urls)
    logger.info("  Total: %d unique article URLs discovered for %s", len(urls), domain)
    return urls[:target_count]


async def process_article(
    url: str, client, taxonomy, cache,
) -> Optional[Dict[str, Any]]:
    """Fetch, extract metadata, NDF-profile, and record one article."""
    from adam.intelligence.domain_taxonomy import extract_article_metadata
    from adam.intelligence.page_intelligence import profile_page_content

    try:
        resp = await client.get(url, headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        })
        if resp.status_code != 200:
            return None
        if "text/html" not in resp.headers.get("content-type", ""):
            return None

        html = resp.text

        # Extract metadata
        meta = extract_article_metadata(url, html)

        # Extract clean text
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header", "aside", "iframe"]):
            tag.decompose()
        for sel in ["[class*='ad-']", "[class*='advertisement']", "[class*='sidebar']",
                     "[class*='newsletter']", "[class*='cookie']", "[class*='popup']"]:
            for tag in soup.select(sel):
                tag.decompose()

        main = (soup.find("article") or soup.find("main")
                or soup.find("div", role="main") or soup.find("body"))
        text = main.get_text(separator=" ", strip=True) if main else ""
        text = " ".join(text.split())[:10000]

        if len(text.split()) < 50:
            return None

        # NDF profile
        profile = profile_page_content(url=url, text_content=text, title=meta.title or "")

        # Populate metadata
        # Prefer full-width edge dimensions (20-dim); fallback to NDF
        meta.edge_dimensions = profile.edge_dimensions if profile.edge_dimensions else {}
        meta.ndf_vector = profile.construct_activations
        meta.mechanism_adjustments = profile.mechanism_adjustments
        meta.mindset = profile.mindset
        meta.confidence = profile.confidence
        meta.word_count = len(text.split())

        # Record into taxonomy
        result = taxonomy.record_article(meta)

        # Also store in page cache
        cache.store(profile)

        return {
            "url": url,
            "category": meta.category,
            "subcategory": meta.subcategory,
            "author": meta.authors[0] if meta.authors else "",
            "title": meta.title[:60] if meta.title else "",
            "mindset": meta.mindset,
            "confidence": meta.confidence,
            "recorded": result.get("recorded", False),
        }

    except Exception as e:
        return None


async def process_domain(
    domain: str, articles_per_domain: int = 60,
) -> Dict[str, Any]:
    """Process a single domain: discover URLs, fetch articles, build taxonomy."""
    import httpx
    from adam.intelligence.domain_taxonomy import get_domain_taxonomy
    from adam.intelligence.page_intelligence import get_page_intelligence_cache

    taxonomy = get_domain_taxonomy(domain)
    cache = get_page_intelligence_cache()

    logger.info("Processing %s (target: %d articles)...", domain, articles_per_domain)

    # Discover article URLs
    urls = await discover_article_urls(domain, target_count=articles_per_domain * 2)

    if not urls:
        logger.warning("  No URLs found for %s", domain)
        return {"domain": domain, "articles": 0, "categories": set(), "authors": set()}

    stats = {
        "domain": domain,
        "urls_found": len(urls),
        "articles": 0,
        "failed": 0,
        "categories": set(),
        "authors": set(),
    }

    async with httpx.AsyncClient(timeout=12, follow_redirects=True) as client:
        for i, url in enumerate(urls[:articles_per_domain]):
            result = await process_article(url, client, taxonomy, cache)

            if result:
                stats["articles"] += 1
                if result["category"]:
                    stats["categories"].add(result["category"])
                if result["author"]:
                    stats["authors"].add(result["author"])

                if stats["articles"] % 10 == 0:
                    logger.info(
                        "  %s: %d/%d articles | cats=%s | authors=%d",
                        domain, stats["articles"], articles_per_domain,
                        sorted(stats["categories"])[:6], len(stats["authors"]),
                    )
            else:
                stats["failed"] += 1

            # Rate limit
            await asyncio.sleep(random.uniform(0.8, 1.5))

    stats["categories"] = sorted(stats["categories"])
    stats["authors"] = sorted(list(stats["authors"])[:30])

    logger.info(
        "  %s DONE: %d articles, %d categories, %d authors",
        domain, stats["articles"], len(stats["categories"]), len(stats["authors"]),
    )
    return stats


async def run(args):
    """Main execution."""
    logger.info("=" * 60)
    logger.info("TAXONOMY POPULATION — Deep Crawl")
    logger.info("=" * 60)

    if args.domains:
        domains = [d.strip() for d in args.domains.split(",")]
    else:
        domains = PRIORITY_DOMAINS

    domains = domains[:args.max_domains]
    logger.info("Domains: %d, Articles/domain: %d", len(domains), args.articles_per_domain)

    all_stats = []
    total_articles = 0
    total_categories = set()
    total_authors = set()

    start = time.time()

    for domain in domains:
        stats = await process_domain(domain, args.articles_per_domain)
        all_stats.append(stats)
        total_articles += stats["articles"]
        total_categories.update(stats["categories"])
        total_authors.update(stats["authors"])

    elapsed = time.time() - start

    # Summary
    logger.info("")
    logger.info("=" * 60)
    logger.info("RESULTS")
    logger.info("=" * 60)
    for s in all_stats:
        cats = s["categories"] if isinstance(s["categories"], list) else sorted(s["categories"])
        logger.info(
            "  %-25s articles=%-4d categories=%-3d authors=%-3d",
            s["domain"], s["articles"], len(cats), len(s["authors"]),
        )

    logger.info("")
    logger.info("TOTAL: %d articles, %d categories, %d authors in %.0fs",
                total_articles, len(total_categories), len(total_authors), elapsed)

    # Check taxonomy reliability
    import redis
    r = redis.Redis(host="localhost", port=6379, decode_responses=True)
    reliable = 0
    total_cats = 0
    for key in r.keys("informativ:taxonomy:*:cat:*"):
        data = r.hgetall(key)
        n = int(data.get("observation_count", 0))
        total_cats += 1
        if n >= 5:
            reliable += 1

    logger.info("")
    logger.info("TAXONOMY STATUS:")
    logger.info("  Category centroids: %d total, %d reliable (5+ obs)", total_cats, reliable)
    logger.info("  Author fingerprints: %d", len(r.keys("informativ:taxonomy:*:author:*")))
    logger.info("  Page profiles in cache: %d", len(r.keys("informativ:page:*")))


def main():
    parser = argparse.ArgumentParser(description="Deep taxonomy population")
    parser.add_argument("--domains", type=str, default="",
                        help="Comma-separated domains (default: all priority)")
    parser.add_argument("--articles-per-domain", type=int, default=60,
                        help="Target articles per domain (default: 60)")
    parser.add_argument("--max-domains", type=int, default=20,
                        help="Max domains to process (default: 20)")
    args = parser.parse_args()
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
