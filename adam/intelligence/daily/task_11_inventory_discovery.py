"""
Task 11: Programmatic Inventory Discovery
==========================================

Solves the cold-start problem for page intelligence: how do we know
WHICH pages to crawl BEFORE StackAdapt sends bid requests?

Three discovery strategies:

1. ADS.TXT PARSING — Every publisher that sells programmatic inventory
   publishes an ads.txt file listing authorized sellers. By parsing
   ads.txt files across the top 10K websites, we build a map of which
   publishers are available through StackAdapt's exchange partners
   (Xandr, Index Exchange, PubMatic, TripleLift, Magnite, etc.).
   If a publisher lists one of these exchanges, StackAdapt CAN buy
   their inventory → we should pre-score their pages.

2. SITEMAP CRAWLING — Once we identify a publisher domain, crawling
   their sitemap.xml gives us ALL article URLs (not just section pages).
   This moves us from "nytimes.com/business" to every individual article.
   Sitemaps typically contain 10K-50K URLs per domain.

3. RSS FEED MONITORING — Subscribe to publisher RSS feeds for real-time
   new content discovery. When a publisher posts a new article, we can
   profile it within minutes — before StackAdapt even sends the first
   bid request for that page.

Together these three strategies give us proactive coverage of the
programmatic open web, not just reactive discovery from live traffic.

Produces:
- Expanded domain inventory (from ads.txt exchange matching)
- Article-level URL candidates (from sitemaps)
- Real-time new page discovery (from RSS feeds)
- All fed into PageInventoryTracker for priority-based crawling

Redis keys:
- informativ:inventory:domains — discovered programmatic domains
- informativ:inventory:adstxt:{domain} — ads.txt exchange matches
- informativ:inventory:sitemap:{domain} — sitemap URL count + freshest URLs
- informativ:inventory:rss:{domain} — RSS feed URLs + last fetch time
"""

from __future__ import annotations

import logging
import re
import time
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import urlparse

from adam.intelligence.daily.base import DailyStrengtheningTask, TaskResult

logger = logging.getLogger(__name__)

# StackAdapt's known exchange/SSP partners
# These are the seller IDs/domains that appear in ads.txt when a publisher
# is available through StackAdapt's supply path.
_STACKADAPT_EXCHANGE_PARTNERS = {
    # Major SSPs that StackAdapt buys from
    "google.com",           # Google Ad Manager / AdX
    "indexexchange.com",    # Index Exchange
    "pubmatic.com",         # PubMatic
    "openx.com",            # OpenX
    "appnexus.com",         # Xandr (Microsoft)
    "rubiconproject.com",   # Magnite (formerly Rubicon)
    "magnite.com",          # Magnite
    "triplelift.com",       # TripleLift
    "sharethrough.com",     # Sharethrough
    "sovrn.com",            # Sovrn
    "33across.com",         # 33Across
    "smartadserver.com",    # Equativ (Smart)
    "media.net",            # Media.net
    "yahoo.com",            # Yahoo DSP
    "contextweb.com",       # PulsePoint
    "spotxchange.com",      # SpotX (Magnite)
    "improvedigital.com",   # Improve Digital
    "rhythmone.com",        # RhythmOne
    "outbrain.com",         # Outbrain
    "taboola.com",          # Taboola
    "criteo.com",           # Criteo
    "yieldmo.com",          # Yieldmo
    "kargo.com",            # Kargo
    "gumgum.com",           # GumGum
    "undertone.com",        # Undertone
    "emxdgt.com",           # EMX Digital
    "adcolony.com",         # AdColony
    "smaato.com",           # Smaato
    "inmobi.com",           # InMobi
    "conversantmedia.com",  # Conversant
    "freewheel.com",        # FreeWheel (Comcast)
    "synacor.com",          # Synacor
}

# Top programmatic publisher domains by estimated impression volume
# Source: industry knowledge of high-traffic ad-supported sites
_TOP_PROGRAMMATIC_DOMAINS = [
    # Tier 1: Highest volume news/media (>100M monthly impressions)
    "cnn.com", "nytimes.com", "washingtonpost.com", "foxnews.com",
    "nbcnews.com", "bbc.com", "usatoday.com", "reuters.com",
    "theguardian.com", "apnews.com", "nypost.com", "dailymail.co.uk",
    "msn.com", "news.yahoo.com", "abcnews.go.com",

    # Tier 1: Sports & Entertainment
    "espn.com", "bleacherreport.com", "cbssports.com", "si.com",
    "people.com", "tmz.com", "eonline.com", "variety.com",
    "hollywoodreporter.com", "deadline.com", "ew.com",

    # Tier 1: Tech
    "techcrunch.com", "theverge.com", "wired.com", "arstechnica.com",
    "cnet.com", "zdnet.com", "engadget.com", "tomsguide.com",
    "pcmag.com", "mashable.com", "gizmodo.com",

    # Tier 1: Business/Finance
    "forbes.com", "businessinsider.com", "cnbc.com", "marketwatch.com",
    "investopedia.com", "fool.com", "bankrate.com", "nerdwallet.com",
    "kiplinger.com", "thestreet.com",

    # Tier 1: Health/Wellness
    "webmd.com", "healthline.com", "mayoclinic.org", "medicalnewstoday.com",
    "verywellhealth.com", "health.com", "everydayhealth.com",

    # Tier 1: Lifestyle/Home
    "allrecipes.com", "foodnetwork.com", "epicurious.com", "bonappetit.com",
    "hgtv.com", "realsimple.com", "bhg.com", "architecturaldigest.com",
    "marthastewart.com",

    # Tier 1: Parenting/Family
    "parents.com", "whattoexpect.com", "babycenter.com",

    # Tier 1: Weather (massive impression volume)
    "weather.com", "accuweather.com",

    # Tier 2: High-traffic verticals
    "autotrader.com", "caranddriver.com", "motortrend.com",
    "edmunds.com", "kbb.com",
    "zillow.com", "realtor.com", "redfin.com", "apartments.com",
    "tripadvisor.com", "lonelyplanet.com", "kayak.com",
    "ign.com", "gamespot.com", "polygon.com", "kotaku.com",
    "cosmopolitan.com", "glamour.com", "vogue.com", "elle.com",
    "gq.com", "esquire.com", "menshealth.com", "womenshealthmag.com",
    "runnersworld.com", "bicycling.com",
    "rollingstone.com", "pitchfork.com", "billboard.com",
    "space.com", "livescience.com", "sciencealert.com",

    # Tier 2: UGC/Social with ads
    "reddit.com", "quora.com", "medium.com",
    "stackexchange.com", "stackoverflow.com",

    # Tier 2: Reference/Education
    "britannica.com", "dictionary.com", "thesaurus.com",
    "howstuffworks.com", "thoughtco.com",

    # Tier 2: Shopping/Review
    "wirecutter.com", "consumerreports.org", "reviews.com",
    "bestproducts.com", "goodhousekeeping.com",

    # Tier 3: Long-tail high-quality
    "theatlantic.com", "newyorker.com", "slate.com", "salon.com",
    "vox.com", "axios.com", "politico.com", "thehill.com",
    "fivethirtyeight.com", "propublica.org",
    "nationalgeographic.com", "smithsonianmag.com",
    "psychologytoday.com", "scientificamerican.com",
]

# Common RSS feed URL patterns
_RSS_PATTERNS = [
    "/feed", "/rss", "/feeds/all.rss.xml", "/feed/",
    "/rss.xml", "/atom.xml", "/feeds/posts/default",
    "/index.xml", "/?feed=rss2",
]

# Common sitemap URL patterns
_SITEMAP_PATTERNS = [
    "/sitemap.xml", "/sitemap_index.xml", "/sitemap-index.xml",
    "/sitemaps/sitemap.xml", "/news-sitemap.xml",
    "/sitemap-news.xml", "/post-sitemap.xml",
]


class InventoryDiscoveryTask(DailyStrengtheningTask):
    """Discover programmatic ad inventory across the open web."""

    @property
    def name(self) -> str:
        return "inventory_discovery"

    @property
    def schedule_hours(self) -> List[int]:
        return [1]  # 1 AM UTC daily

    @property
    def frequency_hours(self) -> int:
        return 24

    async def execute(self) -> TaskResult:
        result = TaskResult(task_name=self.name, success=True)

        # Phase 1: Parse ads.txt for exchange-matched publishers
        exchange_matched = await self._discover_via_adstxt(result)

        # Phase 2: Discover sitemaps for article-level URLs
        sitemap_urls = await self._discover_via_sitemaps(result)

        # Phase 3: Discover RSS feeds for real-time content
        rss_feeds = await self._discover_rss_feeds(result)

        # Phase 4: Feed discovered URLs into the inventory tracker
        await self._feed_inventory_tracker(exchange_matched, sitemap_urls, rss_feeds, result)

        # Phase 5: Store discovered domain inventory
        all_domains = set()
        all_domains.update(exchange_matched)
        all_domains.update(d for d, _ in sitemap_urls)
        all_domains.update(d for d, _ in rss_feeds)

        if all_domains:
            self._store_redis_hash("informativ:inventory:domains", {
                "domains": list(all_domains),
                "count": len(all_domains),
                "exchange_matched": len(exchange_matched),
                "sitemap_discovered": len(sitemap_urls),
                "rss_discovered": len(rss_feeds),
                "computed_at": time.time(),
            }, ttl=86400 * 7)

        result.details["exchange_matched_domains"] = len(exchange_matched)
        result.details["sitemap_urls_discovered"] = sum(c for _, c in sitemap_urls)
        result.details["rss_feeds_found"] = len(rss_feeds)
        result.details["total_domains"] = len(all_domains)
        return result

    async def _discover_via_adstxt(self, result: TaskResult) -> Set[str]:
        """Parse ads.txt files to find publishers in StackAdapt's supply path.

        ads.txt format: domain, account_id, relationship, [cert_authority]
        Example: google.com, pub-1234567890, DIRECT, f08c47fec0942fa0

        If a publisher's ads.txt lists any of StackAdapt's exchange partners,
        StackAdapt CAN buy that inventory.
        """
        exchange_matched: Set[str] = set()

        try:
            import httpx
        except ImportError:
            return exchange_matched

        # Check ads.txt for ALL known programmatic domains
        domains_to_check = _TOP_PROGRAMMATIC_DOMAINS

        async with httpx.AsyncClient(timeout=8, follow_redirects=True) as client:
            for domain in domains_to_check:
                result.items_processed += 1
                try:
                    url = f"https://{domain}/ads.txt"
                    resp = await client.get(url, headers={
                        "User-Agent": "Mozilla/5.0 (compatible; ADAM/1.0; +https://informativ.ai)"
                    })

                    if resp.status_code != 200:
                        continue

                    text = resp.text
                    if len(text) < 20:
                        continue

                    # Parse ads.txt lines
                    exchanges_found = set()
                    for line in text.split("\n"):
                        line = line.strip()
                        if not line or line.startswith("#"):
                            continue
                        parts = [p.strip().lower() for p in line.split(",")]
                        if len(parts) >= 3:
                            exchange_domain = parts[0]
                            if exchange_domain in _STACKADAPT_EXCHANGE_PARTNERS:
                                exchanges_found.add(exchange_domain)

                    if exchanges_found:
                        exchange_matched.add(domain)

                        # Store per-domain ads.txt data
                        self._store_redis_hash(
                            f"informativ:inventory:adstxt:{domain}",
                            {
                                "domain": domain,
                                "exchanges": list(exchanges_found),
                                "exchange_count": len(exchanges_found),
                                "stackadapt_reachable": True,
                                "checked_at": time.time(),
                            },
                            ttl=86400 * 7,
                        )
                        result.items_stored += 1

                except Exception as e:
                    logger.debug("ads.txt fetch failed for %s: %s", domain, type(e).__name__)

                # Light rate limiting
                import asyncio
                await asyncio.sleep(0.3)

        logger.info(
            "ads.txt discovery: %d/%d domains are in StackAdapt's supply path",
            len(exchange_matched), len(domains_to_check),
        )
        return exchange_matched

    async def _discover_via_sitemaps(self, result: TaskResult) -> List[Tuple[str, int]]:
        """Crawl sitemap.xml files to discover article-level URLs.

        This is what moves us from "nytimes.com/business" to every
        individual article URL — the actual pages where ads appear.

        Returns list of (domain, url_count) tuples.
        """
        sitemap_results: List[Tuple[str, int]] = []

        try:
            import httpx
        except ImportError:
            return sitemap_results

        # Focus on domains we've already confirmed via ads.txt or have in inventory
        r = self._get_redis()
        confirmed_domains: Set[str] = set()

        # Add domains from ads.txt discovery
        if r:
            try:
                cursor = 0
                while True:
                    cursor, keys = r.scan(cursor, match="informativ:inventory:adstxt:*", count=100)
                    for key in keys:
                        domain = key.split(":")[-1]
                        confirmed_domains.add(domain)
                    if cursor == 0:
                        break
            except Exception:
                pass

        # Also add domains from inventory tracker
        try:
            from adam.intelligence.page_intelligence import get_inventory_tracker
            tracker = get_inventory_tracker()
            for domain, _ in tracker.get_top_domains(200):
                confirmed_domains.add(domain)
        except Exception:
            pass

        # Fallback to top programmatic domains
        if not confirmed_domains:
            confirmed_domains = set(_TOP_PROGRAMMATIC_DOMAINS[:50])

        # Limit to 30 domains per run (sitemaps can be large)
        domains_to_crawl = list(confirmed_domains)[:30]

        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
            for domain in domains_to_crawl:
                try:
                    urls_found = await self._parse_sitemap(client, domain)
                    if urls_found:
                        sitemap_results.append((domain, len(urls_found)))

                        # Store freshest URLs (last 200 per domain)
                        self._store_redis_hash(
                            f"informativ:inventory:sitemap:{domain}",
                            {
                                "domain": domain,
                                "total_urls": len(urls_found),
                                "sample_urls": urls_found[:200],
                                "checked_at": time.time(),
                            },
                            ttl=86400 * 3,
                        )
                        result.items_stored += 1

                except Exception as e:
                    logger.debug("Sitemap crawl failed for %s: %s", domain, type(e).__name__)

                import asyncio
                await asyncio.sleep(0.5)

        return sitemap_results

    async def _parse_sitemap(
        self, client, domain: str, max_urls: int = 500,
    ) -> List[str]:
        """Parse a domain's sitemap.xml and extract article URLs."""
        urls = []

        for pattern in _SITEMAP_PATTERNS:
            try:
                url = f"https://{domain}{pattern}"
                resp = await client.get(url, headers={
                    "User-Agent": "Mozilla/5.0 (compatible; ADAM/1.0)"
                })

                if resp.status_code != 200:
                    continue

                text = resp.text
                if "<urlset" not in text and "<sitemapindex" not in text:
                    continue

                # If it's a sitemap index, grab the first few child sitemaps
                if "<sitemapindex" in text:
                    child_urls = re.findall(r"<loc>(.*?)</loc>", text)
                    # Prefer news sitemaps
                    news_sitemaps = [u for u in child_urls if "news" in u.lower()]
                    post_sitemaps = [u for u in child_urls if "post" in u.lower()]
                    target_sitemaps = (news_sitemaps or post_sitemaps or child_urls)[:3]

                    for child_url in target_sitemaps:
                        try:
                            child_resp = await client.get(child_url, headers={
                                "User-Agent": "Mozilla/5.0 (compatible; ADAM/1.0)"
                            })
                            if child_resp.status_code == 200:
                                child_locs = re.findall(r"<loc>(.*?)</loc>", child_resp.text)
                                urls.extend(child_locs[:max_urls // 3])
                        except Exception:
                            pass
                else:
                    # Direct urlset
                    locs = re.findall(r"<loc>(.*?)</loc>", text)
                    urls.extend(locs[:max_urls])

                if urls:
                    break  # Found a working sitemap, stop trying patterns

            except Exception:
                continue

        return urls[:max_urls]

    async def _discover_rss_feeds(self, result: TaskResult) -> List[Tuple[str, str]]:
        """Discover RSS feeds for real-time new content monitoring.

        Returns list of (domain, feed_url) tuples.
        """
        feeds: List[Tuple[str, str]] = []

        try:
            import httpx
        except ImportError:
            return feeds

        # Check RSS feeds for top publishers
        domains_to_check = _TOP_PROGRAMMATIC_DOMAINS[:50]

        async with httpx.AsyncClient(timeout=8, follow_redirects=True) as client:
            for domain in domains_to_check:
                try:
                    feed_url = await self._find_rss_feed(client, domain)
                    if feed_url:
                        feeds.append((domain, feed_url))

                        self._store_redis_hash(
                            f"informativ:inventory:rss:{domain}",
                            {
                                "domain": domain,
                                "feed_url": feed_url,
                                "discovered_at": time.time(),
                                "last_fetched": 0,
                            },
                            ttl=86400 * 14,
                        )
                        result.items_stored += 1

                except Exception:
                    pass

                import asyncio
                await asyncio.sleep(0.3)

        logger.info("RSS discovery: found %d feeds from %d domains", len(feeds), len(domains_to_check))
        return feeds

    async def _find_rss_feed(self, client, domain: str) -> Optional[str]:
        """Find a working RSS feed URL for a domain."""
        # First check homepage for RSS link tags
        try:
            resp = await client.get(f"https://{domain}/", headers={
                "User-Agent": "Mozilla/5.0 (compatible; ADAM/1.0)"
            })
            if resp.status_code == 200:
                # Look for RSS link in HTML head
                rss_match = re.search(
                    r'<link[^>]+type="application/rss\+xml"[^>]+href="([^"]+)"',
                    resp.text[:5000],
                )
                if rss_match:
                    feed_url = rss_match.group(1)
                    if not feed_url.startswith("http"):
                        feed_url = f"https://{domain}{feed_url}"
                    return feed_url

                atom_match = re.search(
                    r'<link[^>]+type="application/atom\+xml"[^>]+href="([^"]+)"',
                    resp.text[:5000],
                )
                if atom_match:
                    feed_url = atom_match.group(1)
                    if not feed_url.startswith("http"):
                        feed_url = f"https://{domain}{feed_url}"
                    return feed_url
        except Exception:
            pass

        # Fallback: try common RSS URL patterns
        for pattern in _RSS_PATTERNS[:4]:
            try:
                url = f"https://{domain}{pattern}"
                resp = await client.get(url, headers={
                    "User-Agent": "Mozilla/5.0 (compatible; ADAM/1.0)"
                })
                if resp.status_code == 200:
                    ct = resp.headers.get("content-type", "")
                    text_start = resp.text[:200].lower()
                    if "xml" in ct or "rss" in ct or "<rss" in text_start or "<feed" in text_start:
                        return url
            except Exception:
                continue

        return None

    async def _feed_inventory_tracker(
        self,
        exchange_matched: Set[str],
        sitemap_urls: List[Tuple[str, int]],
        rss_feeds: List[Tuple[str, str]],
        result: TaskResult,
    ) -> None:
        """Feed discovered URLs into PageInventoryTracker for crawl prioritization.

        This is the bridge between discovery and the existing crawl pipeline.
        The inventory tracker already has priority-based crawling logic —
        we just need to feed it URLs.
        """
        try:
            from adam.intelligence.page_intelligence import get_inventory_tracker
            tracker = get_inventory_tracker()
        except Exception:
            return

        # Feed exchange-matched domains (homepage as minimum)
        for domain in exchange_matched:
            tracker.record_placement(f"https://{domain}/")

        # Feed sitemap-discovered URLs
        r = self._get_redis()
        if r:
            for domain, _ in sitemap_urls:
                try:
                    import json
                    data = r.hgetall(f"informativ:inventory:sitemap:{domain}")
                    if data:
                        sample_urls = data.get("sample_urls", "[]")
                        if isinstance(sample_urls, str):
                            sample_urls = json.loads(sample_urls)
                        for url in sample_urls[:50]:  # Top 50 per domain
                            tracker.record_placement(url)
                except Exception:
                    pass

        # Feed RSS-discovered new content
        try:
            import httpx
            async with httpx.AsyncClient(timeout=8) as client:
                for domain, feed_url in rss_feeds[:20]:
                    try:
                        resp = await client.get(feed_url, headers={
                            "User-Agent": "Mozilla/5.0 (compatible; ADAM/1.0)"
                        })
                        if resp.status_code == 200:
                            # Extract URLs from RSS items
                            links = re.findall(r"<link>([^<]+)</link>", resp.text)
                            links += re.findall(r'<link[^>]+href="([^"]+)"', resp.text)
                            for link in links[:20]:
                                if link.startswith("http") and domain in link:
                                    tracker.record_placement(link)
                    except Exception:
                        pass

                    import asyncio
                    await asyncio.sleep(0.3)
        except ImportError:
            pass

        result.details["tracker_stats"] = tracker.stats
