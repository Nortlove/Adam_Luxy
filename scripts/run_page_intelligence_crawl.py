#!/usr/bin/env python3
"""
Run an immediate page intelligence crawl for the LUXY Ride campaign domains.

Seeds the PageInventoryTracker with campaign-relevant domains from the
whitelist, then runs one crawl cycle with Pass 1 (NLP) + Pass 2 (edge scoring).

Usage:
    source .env && export ANTHROPIC_API_KEY NEO4J_URI NEO4J_USERNAME NEO4J_PASSWORD
    python3 -u scripts/run_page_intelligence_crawl.py
"""

import asyncio
import json
import logging
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
logger = logging.getLogger(__name__)

# Campaign domains from the whitelist + seed domains
CAMPAIGN_DOMAINS = [
    # Corporate Executive domains
    "cnbc.com", "bloomberg.com", "wsj.com", "forbes.com", "reuters.com",
    "hbr.org", "ft.com", "barrons.com", "fastcompany.com", "inc.com",
    "businessinsider.com", "fortune.com",
    # Airport Anxiety domains
    "weather.com", "flightaware.com", "tripadvisor.com", "kayak.com",
    "seatguru.com", "thepointsguy.com", "cntraveler.com",
    "usatoday.com", "tsa.gov",
    # Special Occasion domains
    "theknot.com", "brides.com", "people.com", "pinterest.com",
    "weddingwire.com", "marthastewart.com", "vogue.com",
    "townandcountrymag.com", "instyle.com",
    # General high-traffic domains
    "cnn.com", "nytimes.com", "washingtonpost.com", "bbc.com",
    "foxnews.com", "nbcnews.com", "espn.com",
    "webmd.com", "healthline.com",
    "reddit.com", "medium.com",
    "techcrunch.com", "theverge.com", "wired.com",
]

# Sample article paths per domain for seeding
SEED_URLS = {
    "cnbc.com": ["/markets", "/business", "/investing", "/technology"],
    "bloomberg.com": ["/markets", "/technology", "/wealth"],
    "forbes.com": ["/business", "/leadership", "/travel"],
    "weather.com": ["/weather/today", "/weather/tenday", "/travel"],
    "tripadvisor.com": ["/Tourism", "/Airlines", "/Hotels"],
    "theknot.com": ["/content/wedding-planning", "/content/wedding-venues"],
    "cnn.com": ["/business", "/travel", "/style", "/health"],
    "espn.com": ["/nfl", "/nba", "/mlb"],
    "people.com": ["/style", "/home", "/food"],
    "reuters.com": ["/business", "/markets", "/world"],
}


async def run_crawl():
    from adam.intelligence.page_intelligence import (
        get_inventory_tracker,
        get_page_intelligence_cache,
        profile_page_content,
    )
    from adam.intelligence.page_edge_scoring import score_page_full_width

    tracker = get_inventory_tracker()
    cache = get_page_intelligence_cache()

    # Step 1: Seed the tracker with campaign domains
    print("STEP 1: Seeding inventory tracker", flush=True)
    for domain in CAMPAIGN_DOMAINS:
        base_url = f"https://www.{domain}/"
        # Record fake impressions to make these high-priority
        for _ in range(10):
            tracker.record_placement(base_url)
        # Also seed specific article URLs
        if domain in SEED_URLS:
            for path in SEED_URLS[domain]:
                url = f"https://www.{domain}{path}"
                for _ in range(5):
                    tracker.record_placement(url)

    stats = tracker.stats
    print(f"  Seeded: {stats['unique_domains']} domains, {stats['unique_patterns']} URL patterns", flush=True)

    # Step 2: Load category edge priors for Tier 1 scoring
    print("\nSTEP 2: Loading category edge priors", flush=True)
    try:
        from adam.intelligence.page_edge_scoring import load_category_edge_priors
        priors = await load_category_edge_priors()
        print(f"  Loaded {len(priors)} category priors from Neo4j", flush=True)
    except Exception as e:
        print(f"  Priors not loaded: {e} (Tier 2/3 scoring still works)", flush=True)

    # Step 3: Crawl pages
    print("\nSTEP 3: Crawling campaign domains", flush=True)

    try:
        import httpx
    except ImportError:
        os.system("pip3 install httpx")
        import httpx

    # Build candidate list
    candidates = tracker.get_crawl_candidates(n=200, min_impressions=1)
    print(f"  Candidates: {len(candidates)}", flush=True)

    succeeded = 0
    failed = 0
    cached = 0
    t0 = time.time()

    async with httpx.AsyncClient(
        timeout=15.0,
        follow_redirects=True,
        headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"},
    ) as client:
        for item in candidates:
            url_pattern = item if isinstance(item, str) else item[0]
            # Check cache first
            existing = cache.lookup(url_pattern)
            if existing and existing.confidence > 0.3:
                cached += 1
                continue

            # Fetch
            try:
                url = url_pattern if url_pattern.startswith("http") else f"https://{url_pattern}"
                resp = await client.get(url)
                if resp.status_code != 200:
                    failed += 1
                    continue

                text = resp.text
                title = ""
                # Extract title from HTML
                import re
                title_match = re.search(r"<title[^>]*>(.*?)</title>", text, re.IGNORECASE | re.DOTALL)
                if title_match:
                    title = title_match.group(1).strip()[:200]

                # Strip HTML tags for text analysis
                clean_text = re.sub(r"<script[^>]*>.*?</script>", "", text, flags=re.DOTALL | re.IGNORECASE)
                clean_text = re.sub(r"<style[^>]*>.*?</style>", "", clean_text, flags=re.DOTALL | re.IGNORECASE)
                clean_text = re.sub(r"<[^>]+>", " ", clean_text)
                clean_text = re.sub(r"\s+", " ", clean_text).strip()

                if len(clean_text) < 100:
                    failed += 1
                    continue

                # Pass 1: NLP profile
                profile = profile_page_content(
                    url=url,
                    text_content=clean_text[:10000],
                    title=title,
                )

                # Pass 2: Full-width edge scoring
                edge_profile = score_page_full_width(
                    text=clean_text[:10000],
                    url=url,
                    category="",
                )
                if edge_profile and hasattr(edge_profile, 'dimensions'):
                    profile.edge_dimensions = edge_profile.dimensions
                    profile.edge_scoring_tier = edge_profile.tier

                # Store in cache
                cache.store(profile)
                succeeded += 1

                domain = re.sub(r"https?://(www\.)?", "", url).split("/")[0]
                if succeeded % 10 == 0:
                    elapsed = time.time() - t0
                    print(f"  [{succeeded} ok, {failed} fail, {cached} cached] {elapsed:.0f}s", flush=True)

                # Rate limit
                await asyncio.sleep(0.5)

            except Exception as e:
                failed += 1
                if failed <= 3:
                    logger.debug(f"Crawl error for {url_pattern}: {e}")

    elapsed = time.time() - t0
    print(f"\n  DONE: {succeeded} crawled, {failed} failed, {cached} already cached, {elapsed:.0f}s", flush=True)

    # Step 4: Report cache state
    print("\nSTEP 4: Cache state", flush=True)
    cache_stats = cache.stats
    print(f"  {cache_stats}", flush=True)

    # Check Redis for page profiles
    try:
        import redis
        r = redis.Redis(host="localhost", port=6379)
        page_keys = r.keys("informativ:page:*")
        domain_keys = r.keys("informativ:page:domain:*")
        print(f"  Redis page profiles: {len(page_keys)}", flush=True)
        print(f"  Redis domain profiles: {len(domain_keys)}", flush=True)

        # Show a few
        for key in list(page_keys)[:5]:
            print(f"    {key.decode()}", flush=True)
    except Exception as e:
        print(f"  Redis check failed: {e}", flush=True)


if __name__ == "__main__":
    asyncio.run(run_crawl())
