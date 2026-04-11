#!/usr/bin/env python3
"""
Placement Page Crawler — Pre-indexes StackAdapt ad placement pages
===================================================================

This offline pipeline crawls the pages where StackAdapt places ads and
builds psychological profiles for each one. At bid time, the creative
intelligence endpoint looks up these pre-computed profiles in <2ms
instead of fetching pages in real-time (which would take 200-500ms).

The result: ADAM knows the psychological state every page puts the buyer
in BEFORE the bid request arrives.

Usage:
    # One-shot crawl of top placement pages
    python scripts/crawl_placement_pages.py

    # Continuous mode: crawl, sleep, repeat
    python scripts/crawl_placement_pages.py --continuous --interval 3600

    # Crawl specific domains
    python scripts/crawl_placement_pages.py --domains nytimes.com,amazon.com,cnn.com

    # Deep analysis with Claude (costs API credits)
    python scripts/crawl_placement_pages.py --deep-analysis

    # Dry run: show what would be crawled
    python scripts/crawl_placement_pages.py --dry-run --top-n 50

Schedule:
    - Daily: Top 1,000 URL patterns (highest impression volume)
    - Weekly: Top 10,000 URL patterns
    - Monthly: Full inventory crawl (all tracked patterns)
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import re
import signal
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

# Add project root to path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from adam.intelligence.page_intelligence import (
    PageIntelligenceCache,
    PageInventoryTracker,
    PagePsychologicalProfile,
    get_inventory_tracker,
    get_page_intelligence_cache,
    profile_page_content,
    _extract_domain,
    _url_to_pattern,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("placement_crawler")

# Graceful shutdown
_shutdown_requested = False


def _handle_signal(signum, frame):
    global _shutdown_requested
    logger.info("Shutdown requested (signal %d)", signum)
    _shutdown_requested = True


signal.signal(signal.SIGINT, _handle_signal)
signal.signal(signal.SIGTERM, _handle_signal)


# ---------------------------------------------------------------------------
# Multi-Strategy Page Fetcher
# ---------------------------------------------------------------------------
# Many publisher sites have anti-bot protections (Cloudflare, Akamai,
# PerimeterX, DataDome). A single httpx request will fail on ~30-40%
# of modern publisher sites. The solution is a cascade of strategies:
#
# Strategy 1: httpx with rotating headers (fastest, works on ~60% of sites)
# Strategy 2: Playwright headless with stealth (handles JS + basic protection)
# Strategy 3: Oxylabs proxy (handles Cloudflare/Akamai, costs per request)
# Strategy 4: Google Cache / Wayback Machine (free fallback for stubborn sites)
#
# The cascade tries each strategy in order, stopping at the first success.
# This gives us ~95% coverage across publisher inventory.

import random

_USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
]

# Domains known to require Playwright (JS-rendered or heavy anti-bot)
_PLAYWRIGHT_REQUIRED_DOMAINS = frozenset([
    "reddit.com", "twitter.com", "x.com", "instagram.com", "facebook.com",
    "linkedin.com", "tiktok.com", "pinterest.com", "medium.com",
])

# Domains known to block automated requests aggressively
_PROXY_REQUIRED_DOMAINS = frozenset([
    "bloomberg.com", "wsj.com", "ft.com",
])


def _parse_html_to_content(html: str, url: str) -> Optional[Dict[str, str]]:
    """Extract clean text from HTML using BeautifulSoup."""
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        logger.error("beautifulsoup4 not installed: pip install beautifulsoup4")
        return None

    try:
        soup = BeautifulSoup(html, "html.parser")

        # Remove noise elements
        for tag in soup(["script", "style", "nav", "footer", "header", "aside",
                         "iframe", "noscript", "svg", "form"]):
            tag.decompose()

        # Remove ad containers by common class/id patterns
        for selector in ["[class*='ad-']", "[class*='advertisement']",
                         "[id*='ad-']", "[class*='sidebar']", "[class*='cookie']",
                         "[class*='popup']", "[class*='modal']", "[class*='newsletter']"]:
            for tag in soup.select(selector):
                tag.decompose()

        title = ""
        if soup.title and soup.title.string:
            title = soup.title.string.strip()

        meta_desc = ""
        meta_tag = soup.find("meta", attrs={"name": "description"})
        if not meta_tag:
            meta_tag = soup.find("meta", attrs={"property": "og:description"})
        if meta_tag and meta_tag.get("content"):
            meta_desc = meta_tag["content"].strip()

        # Prefer article/main content, fall back to body
        main = (
            soup.find("article")
            or soup.find("main")
            or soup.find("div", role="main")
            or soup.find("div", class_=re.compile(r"article|content|story|post", re.I))
            or soup.find("body")
        )
        text = main.get_text(separator=" ", strip=True) if main else soup.get_text(separator=" ", strip=True)
        text = " ".join(text.split())[:10_000]

        word_count = len(text.split())
        if word_count < 20:
            return None

        return {
            "url": url,
            "title": title,
            "text": text,
            "meta_description": meta_desc,
            "word_count": word_count,
        }
    except Exception as e:
        logger.debug("HTML parse failed for %s: %s", url, type(e).__name__)
        return None


async def _strategy_httpx(url: str, timeout: int = 15) -> Optional[str]:
    """Strategy 1: httpx with rotating User-Agent. Fast, works on ~60% of sites."""
    try:
        import httpx
    except ImportError:
        return None

    headers = {
        "User-Agent": random.choice(_USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Cache-Control": "max-age=0",
    }

    try:
        async with httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=True,
            headers=headers,
            http2=True,
        ) as client:
            response = await client.get(url)

            if response.status_code == 403:
                logger.debug("httpx blocked (403) for %s", url)
                return None
            if response.status_code == 429:
                logger.debug("httpx rate-limited (429) for %s", url)
                return None
            if response.status_code != 200:
                logger.debug("httpx HTTP %d for %s", response.status_code, url)
                return None

            ct = response.headers.get("content-type", "")
            if "text/html" not in ct and "application/xhtml" not in ct:
                return None

            # Check for Cloudflare challenge pages
            html = response.text
            if "cf-browser-verification" in html or "just a moment" in html.lower()[:500]:
                logger.debug("httpx hit Cloudflare challenge for %s", url)
                return None

            return html
    except Exception as e:
        logger.debug("httpx failed for %s: %s", url, type(e).__name__)
        return None


async def _strategy_playwright(url: str, timeout: int = 25_000) -> Optional[str]:
    """Strategy 2: Playwright with stealth. Handles JS + basic anti-bot."""
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        logger.debug("Playwright not installed")
        return None

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-web-security",
                    "--disable-features=IsolateOrigins,site-per-process",
                ],
            )
            context = await browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent=random.choice(_USER_AGENTS),
                locale="en-US",
                timezone_id="America/New_York",
            )

            # Stealth: override navigator.webdriver
            await context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
                Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
                window.chrome = {runtime: {}};
            """)

            page = await context.new_page()

            try:
                response = await page.goto(url, timeout=timeout, wait_until="domcontentloaded")
                if response and response.status >= 400:
                    return None

                # Wait for content to render
                await page.wait_for_timeout(2000)

                # Check for Cloudflare interstitial and wait if needed
                content = await page.content()
                if "cf-browser-verification" in content or "just a moment" in content.lower()[:500]:
                    logger.debug("Playwright waiting for Cloudflare challenge on %s", url)
                    await page.wait_for_timeout(5000)
                    content = await page.content()

                return content
            finally:
                await page.close()
                await context.close()
                await browser.close()
    except Exception as e:
        logger.debug("Playwright failed for %s: %s", url, type(e).__name__)
        return None


async def _strategy_google_cache(url: str) -> Optional[str]:
    """Strategy 3: Google Cache fallback for heavily protected sites."""
    try:
        import httpx
    except ImportError:
        return None

    cache_url = f"https://webcache.googleusercontent.com/search?q=cache:{url}"
    try:
        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
            response = await client.get(cache_url, headers={
                "User-Agent": random.choice(_USER_AGENTS),
            })
            if response.status_code == 200:
                return response.text
    except Exception:
        pass
    return None


async def fetch_page_content(
    url: str,
    use_playwright: bool = True,
    use_cache_fallback: bool = True,
) -> Optional[Dict[str, str]]:
    """Fetch page content using a cascade of strategies.

    Strategy order:
    1. httpx (fast, ~60% success) — always tried first
    2. Playwright stealth (handles JS + basic protection) — if enabled
    3. Google Cache (free fallback for Cloudflare-heavy sites) — if enabled

    Returns parsed content dict or None if all strategies fail.
    """
    domain = _extract_domain(url) or ""

    # Strategy 1: httpx (skip for known Playwright-required domains)
    html = None
    if domain not in _PLAYWRIGHT_REQUIRED_DOMAINS:
        html = await _strategy_httpx(url)
        if html:
            result = _parse_html_to_content(html, url)
            if result and result["word_count"] >= 50:
                result["fetch_strategy"] = "httpx"
                return result
            # httpx got HTML but too little content — likely JS-rendered
            logger.debug("httpx content too thin for %s (%s words), trying Playwright",
                         url, result["word_count"] if result else 0)

    # Strategy 2: Playwright (if enabled)
    if use_playwright:
        html = await _strategy_playwright(url)
        if html:
            result = _parse_html_to_content(html, url)
            if result and result["word_count"] >= 30:
                result["fetch_strategy"] = "playwright"
                return result

    # Strategy 3: Google Cache (if enabled)
    if use_cache_fallback:
        html = await _strategy_google_cache(url)
        if html:
            result = _parse_html_to_content(html, url)
            if result and result["word_count"] >= 30:
                result["fetch_strategy"] = "google_cache"
                return result

    logger.info("All fetch strategies failed for %s", url)
    return None


# ---------------------------------------------------------------------------
# Deep analysis with Claude (optional, for highest-value pages)
# ---------------------------------------------------------------------------

async def deep_profile_with_claude(
    url: str,
    text: str,
    title: str = "",
) -> Optional[PagePsychologicalProfile]:
    """Use Claude to produce a deep psychological profile of page content.

    This produces dramatically richer profiles than the heuristic profiler:
    - Nuanced emotional analysis (not just keyword counting)
    - Construct activation detection
    - Priming effect prediction
    - Cognitive load estimation from actual text complexity

    Cost: ~$0.01-0.03 per page (Claude Haiku via batch API).
    Use for top 1,000 highest-impression pages.
    """
    try:
        import anthropic
    except ImportError:
        logger.debug("anthropic SDK not available for deep profiling")
        return None

    domain = _extract_domain(url)
    pattern = _url_to_pattern(url)

    prompt = f"""Analyze this web page content for psychological profiling of ad placement.

Page URL: {url}
Page Title: {title}

Content (truncated to 3000 chars):
{text[:3000]}

Return a JSON object with these fields:
- emotional_valence: float -1.0 to 1.0 (negative to positive emotional tone)
- emotional_arousal: float 0.0 to 1.0 (calm to excited)
- cognitive_load: float 0.0 to 1.0 (simple to complex reading)
- purchase_intent_signal: float 0.0 to 1.0 (browsing to ready-to-buy)
- mindset: one of "informed", "purchasing", "social", "researching", "relaxed", "professional", "entertained"
- primary_topic: string (e.g., "personal finance", "beauty tips", "tech reviews")
- content_type: one of "article", "product_page", "review_page", "forum", "social", "educational", "video"
- optimal_tone: string (recommended ad tone for this context)
- recommended_complexity: one of "simple", "moderate", "detailed"
- avoid_tactics: list of strings (ad tactics that would feel manipulative here)
- top_constructs: dict of construct_name -> activation_strength (0-1), top 5

Return ONLY valid JSON, no explanation."""

    try:
        client = anthropic.Anthropic()
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}],
        )

        import json
        text_response = response.content[0].text.strip()
        # Handle potential markdown code blocks
        if text_response.startswith("```"):
            text_response = text_response.split("\n", 1)[1].rsplit("```", 1)[0]
        data = json.loads(text_response)

        profile = PagePsychologicalProfile(
            url_pattern=pattern,
            domain=domain or "",
            last_crawled=time.time(),
            emotional_valence=float(data.get("emotional_valence", 0)),
            emotional_arousal=float(data.get("emotional_arousal", 0.5)),
            cognitive_load=float(data.get("cognitive_load", 0.5)),
            purchase_intent_signal=float(data.get("purchase_intent_signal", 0)),
            mindset=data.get("mindset", "unknown"),
            primary_topic=data.get("primary_topic", ""),
            content_type=data.get("content_type", "article"),
            optimal_tone=data.get("optimal_tone", ""),
            recommended_complexity=data.get("recommended_complexity", "moderate"),
            avoid_tactics=data.get("avoid_tactics", []),
            construct_activations=data.get("top_constructs", {}),
            confidence=0.85,
            profile_source="claude_deep_analysis",
            crawl_count=1,
        )

        # Derive mechanism adjustments from mindset + constructs
        _MINDSET_ADJUSTMENTS = {
            "purchasing": {"scarcity": 1.40, "social_proof": 1.35, "commitment": 1.20, "loss_aversion": 1.25},
            "informed": {"authority": 1.25, "social_proof": 1.10, "scarcity": 0.80},
            "researching": {"authority": 1.35, "social_proof": 1.20, "scarcity": 0.70},
            "social": {"social_proof": 1.45, "liking": 1.35, "unity": 1.40},
            "relaxed": {"liking": 1.25, "social_proof": 1.20, "curiosity": 1.15},
            "professional": {"authority": 1.40, "commitment": 1.30, "scarcity": 0.85},
            "entertained": {"liking": 1.30, "social_proof": 1.15, "curiosity": 1.20},
        }
        profile.mechanism_adjustments = _MINDSET_ADJUSTMENTS.get(profile.mindset, {})

        return profile

    except Exception as e:
        logger.warning("Claude deep profiling failed for %s: %s", url, e)
        return None


# ---------------------------------------------------------------------------
# Main crawl orchestrator
# ---------------------------------------------------------------------------

async def crawl_batch(
    urls: List[str],
    cache: PageIntelligenceCache,
    deep_analysis: bool = False,
    rate_limit_delay: float = 1.5,
    use_playwright: bool = True,
) -> Dict[str, int]:
    """Crawl a batch of URLs and store their NDF-grounded psychological profiles.

    Uses multi-strategy fetch cascade:
    1. httpx with rotating headers (~60% success)
    2. Playwright with stealth (JS + basic anti-bot)
    3. Google Cache fallback (heavily protected sites)

    Returns:
        {"crawled": N, "profiled": N, "stored": N, "failed": N, "skipped": N,
         "strategies": {"httpx": N, "playwright": N, "google_cache": N}}
    """
    stats = {
        "crawled": 0, "profiled": 0, "stored": 0,
        "failed": 0, "skipped": 0,
        "strategies": {"httpx": 0, "playwright": 0, "google_cache": 0},
    }
    seen_patterns: Set[str] = set()

    for i, url in enumerate(urls):
        if _shutdown_requested:
            logger.info("Shutdown requested, stopping crawl at %d/%d", i, len(urls))
            break

        # Deduplicate by URL pattern
        pattern = _url_to_pattern(url)
        if pattern in seen_patterns:
            stats["skipped"] += 1
            continue
        seen_patterns.add(pattern)

        # Rate limiting (randomized to avoid pattern detection)
        if i > 0:
            jitter = random.uniform(0.5, 1.5)
            await asyncio.sleep(rate_limit_delay * jitter)

        # Multi-strategy fetch cascade
        content = await fetch_page_content(
            url,
            use_playwright=use_playwright,
            use_cache_fallback=True,
        )

        if content is None:
            stats["failed"] += 1
            continue

        stats["crawled"] += 1
        strategy = content.get("fetch_strategy", "unknown")
        if strategy in stats["strategies"]:
            stats["strategies"][strategy] += 1

        # Profile the page using NDF-grounded analysis
        if deep_analysis:
            profile = await deep_profile_with_claude(
                url=url,
                text=content["text"],
                title=content.get("title", ""),
            )
            if profile is None:
                profile = profile_page_content(
                    url=url,
                    text_content=content["text"],
                    title=content.get("title", ""),
                    meta_description=content.get("meta_description", ""),
                )
        else:
            profile = profile_page_content(
                url=url,
                text_content=content["text"],
                title=content.get("title", ""),
                meta_description=content.get("meta_description", ""),
            )

        stats["profiled"] += 1

        # Store in cache
        if cache.store(profile):
            stats["stored"] += 1
            if (stats["stored"] % 25 == 0):
                logger.info(
                    "Stored: %s → mindset=%s, NDF=[α=%.2f τ=%.2f σ=%.2f κ=%.2f λ=%.2f] conf=%.2f via %s",
                    profile.url_pattern[:60],
                    profile.mindset,
                    profile.construct_activations.get("approach_avoidance", 0),
                    profile.construct_activations.get("temporal_horizon", 0),
                    profile.construct_activations.get("social_calibration", 0),
                    profile.construct_activations.get("cognitive_engagement", 0),
                    profile.construct_activations.get("arousal_seeking", 0),
                    profile.confidence,
                    strategy,
                )
        else:
            logger.warning("Failed to store profile for %s", url)

        if (i + 1) % 50 == 0:
            logger.info(
                "Progress: %d/%d crawled=%d stored=%d failed=%d "
                "(httpx=%d playwright=%d cache=%d)",
                i + 1, len(urls), stats["crawled"], stats["stored"], stats["failed"],
                stats["strategies"]["httpx"],
                stats["strategies"]["playwright"],
                stats["strategies"]["google_cache"],
            )

    return stats


async def generate_seed_urls(domains: List[str]) -> List[str]:
    """Generate seed URLs for domains that haven't been seen in live traffic.

    For each domain, generate common URL patterns to crawl:
    - Homepage
    - Common section pages (/business, /tech, /sports, etc.)
    """
    urls = []
    common_sections = [
        "", "business", "technology", "sports", "entertainment",
        "health", "science", "politics", "opinion", "lifestyle",
    ]
    for domain in domains:
        for section in common_sections:
            if section:
                urls.append(f"https://{domain}/{section}")
            else:
                urls.append(f"https://{domain}/")
    return urls


async def run_crawl(args: argparse.Namespace) -> None:
    """Main crawl execution."""
    cache = get_page_intelligence_cache()
    tracker = get_inventory_tracker()

    logger.info("=== Placement Page Crawler ===")
    logger.info("Cache stats: %s", cache.stats)
    logger.info("Inventory stats: %s", tracker.stats)

    # Determine URLs to crawl
    urls_to_crawl: List[str] = []

    if args.domains:
        # Crawl specific domains
        domains = [d.strip() for d in args.domains.split(",")]
        urls_to_crawl = await generate_seed_urls(domains)
        logger.info("Seeded %d URLs from %d specified domains", len(urls_to_crawl), len(domains))

    elif tracker.stats["unique_domains"] > 0:
        # Use inventory from live traffic
        candidates = tracker.get_crawl_candidates(n=args.top_n)
        if candidates:
            # URL patterns aren't full URLs — need to reconstruct
            # Use recent_urls that match the top patterns
            recent = tracker._recent_urls
            pattern_set = set(candidates)
            urls_to_crawl = [
                u for u in recent
                if _url_to_pattern(u) in pattern_set
            ]
            # Also generate homepage URLs for top domains
            top_domains = tracker.get_top_domains(n=min(args.top_n, 200))
            for domain, count in top_domains:
                urls_to_crawl.append(f"https://{domain}/")

            logger.info(
                "Selected %d URLs from live inventory (%d domains, %d patterns)",
                len(urls_to_crawl), len(top_domains), len(candidates),
            )
        else:
            logger.info("No crawl candidates in inventory (min impressions: 5)")

    if not urls_to_crawl:
        # Seed with known high-traffic publisher domains
        seed_domains = [
            "cnn.com", "nytimes.com", "washingtonpost.com", "bbc.com",
            "foxnews.com", "nbcnews.com", "usatoday.com", "reuters.com",
            "theguardian.com", "apnews.com", "espn.com", "bleacherreport.com",
            "weather.com", "accuweather.com", "webmd.com", "healthline.com",
            "allrecipes.com", "foodnetwork.com", "buzzfeed.com", "huffpost.com",
            "forbes.com", "businessinsider.com", "cnbc.com", "bloomberg.com",
            "techcrunch.com", "theverge.com", "wired.com", "arstechnica.com",
            "people.com", "tmz.com", "eonline.com", "variety.com",
            "amazon.com", "walmart.com", "target.com", "bestbuy.com",
            "reddit.com", "quora.com", "medium.com", "substack.com",
        ]
        urls_to_crawl = await generate_seed_urls(seed_domains[:args.top_n])
        logger.info("No inventory data — seeding with %d URLs from %d common domains",
                     len(urls_to_crawl), min(len(seed_domains), args.top_n))

    # Deduplicate
    urls_to_crawl = list(dict.fromkeys(urls_to_crawl))  # Preserves order
    logger.info("Total URLs to crawl: %d", len(urls_to_crawl))

    if args.dry_run:
        logger.info("=== DRY RUN — URLs that would be crawled ===")
        for i, url in enumerate(urls_to_crawl[:100]):
            logger.info("  %3d. %s → pattern: %s", i + 1, url, _url_to_pattern(url))
        if len(urls_to_crawl) > 100:
            logger.info("  ... and %d more", len(urls_to_crawl) - 100)
        return

    # Execute crawl
    start = time.time()
    stats = await crawl_batch(
        urls=urls_to_crawl,
        cache=cache,
        deep_analysis=args.deep_analysis,
        rate_limit_delay=args.delay,
        use_playwright=args.playwright,
    )
    elapsed = time.time() - start

    logger.info("=== Crawl Complete ===")
    logger.info("Duration: %.1f seconds", elapsed)
    logger.info("Results: %s", stats)
    logger.info("Cache stats: %s", cache.stats)
    if stats["crawled"] > 0:
        logger.info(
            "Throughput: %.1f pages/min, %.0f%% success rate",
            stats["crawled"] / (elapsed / 60),
            stats["stored"] / stats["crawled"] * 100,
        )


async def run_continuous(args: argparse.Namespace) -> None:
    """Run crawl continuously on a schedule."""
    cycle = 0
    while not _shutdown_requested:
        cycle += 1
        logger.info("=== Crawl cycle %d (interval=%ds) ===", cycle, args.interval)

        try:
            await run_crawl(args)
        except Exception as e:
            logger.error("Crawl cycle %d failed: %s", cycle, e)

        if _shutdown_requested:
            break

        logger.info("Sleeping %d seconds until next cycle...", args.interval)
        # Sleep in small increments to allow shutdown
        for _ in range(args.interval):
            if _shutdown_requested:
                break
            await asyncio.sleep(1)


def main():
    parser = argparse.ArgumentParser(
        description="Crawl StackAdapt placement pages for psychological profiling",
    )
    parser.add_argument(
        "--top-n", type=int, default=100,
        help="Number of top URL patterns to crawl (default: 100)",
    )
    parser.add_argument(
        "--domains", type=str, default="",
        help="Comma-separated list of domains to crawl (overrides inventory)",
    )
    parser.add_argument(
        "--deep-analysis", action="store_true",
        help="Use Claude for deep psychological profiling (costs API credits)",
    )
    parser.add_argument(
        "--playwright", action="store_true",
        help="Enable Playwright fallback for JavaScript-heavy pages",
    )
    parser.add_argument(
        "--delay", type=float, default=1.5,
        help="Delay between requests in seconds (default: 1.5)",
    )
    parser.add_argument(
        "--continuous", action="store_true",
        help="Run continuously (crawl, sleep, repeat)",
    )
    parser.add_argument(
        "--interval", type=int, default=3600,
        help="Seconds between continuous crawl cycles (default: 3600 = 1 hour)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Show what would be crawled without actually crawling",
    )

    args = parser.parse_args()

    if args.continuous:
        asyncio.run(run_continuous(args))
    else:
        asyncio.run(run_crawl(args))


if __name__ == "__main__":
    main()
