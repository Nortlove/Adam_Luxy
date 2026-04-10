"""
Task 12: Domain Taxonomy Builder
==================================

Crawls articles from priority domains, extracts structured metadata
(category, subcategory, author, title, keywords), NDF-profiles each
article, and feeds observations into the DomainTaxonomy hierarchy.

Over time, this builds per-domain hierarchical models:
    Domain → Category → Subcategory → Author → Article

With enough observations, the taxonomy enables inference for unscored
articles: "This is a CNN/Politics article by Author X → we predict
NDF vector Z with confidence 0.7 even without scoring the content."

Strategy per run:
- For each priority domain, fetch RSS feed (freshest articles)
- If no RSS, use sitemap URLs
- For each article: fetch, extract metadata, NDF-profile, record
- After all articles: compute consistency scores, identify patterns

Redis keys:
- informativ:taxonomy:{domain} — domain config + category list
- informativ:taxonomy:{domain}:cat:{category} — category centroid
- informativ:taxonomy:{domain}:sub:{cat/subcat} — subcategory centroid
- informativ:taxonomy:{domain}:author:{slug} — author fingerprint
- informativ:taxonomy:{domain}:patterns — learned patterns
"""

from __future__ import annotations

import json
import logging
import re
import time
from typing import Any, Dict, List, Optional, Set

from adam.intelligence.daily.base import DailyStrengtheningTask, TaskResult

logger = logging.getLogger(__name__)

# Priority domains for taxonomy building (highest ad inventory)
_PRIORITY_DOMAINS = [
    "cnn.com", "nytimes.com", "washingtonpost.com", "foxnews.com",
    "nbcnews.com", "bbc.com", "reuters.com", "apnews.com",
    "espn.com", "forbes.com", "cnbc.com", "businessinsider.com",
    "techcrunch.com", "theverge.com", "wired.com", "arstechnica.com",
    "webmd.com", "healthline.com", "usatoday.com", "nypost.com",
    "variety.com", "people.com", "buzzfeed.com", "huffpost.com",
    "cnet.com", "pcmag.com", "investopedia.com", "nerdwallet.com",
    "allrecipes.com", "foodnetwork.com",
]

_MAX_ARTICLES_PER_DOMAIN = 30
_MAX_DOMAINS_PER_RUN = 15


class TaxonomyBuilderTask(DailyStrengtheningTask):
    """Build domain taxonomies from article metadata and NDF profiles."""

    @property
    def name(self) -> str:
        return "taxonomy_builder"

    @property
    def schedule_hours(self) -> List[int]:
        return [2, 14]  # Twice daily

    @property
    def frequency_hours(self) -> int:
        return 12

    async def execute(self) -> TaskResult:
        result = TaskResult(task_name=self.name, success=True)

        # Determine which domains to process this run
        domains = self._select_domains()
        result.details["domains_selected"] = len(domains)

        for domain in domains:
            try:
                domain_result = await self._process_domain(domain)
                result.items_processed += domain_result.get("articles_processed", 0)
                result.items_stored += domain_result.get("taxonomy_updates", 0)
                result.details[domain] = domain_result
            except Exception as e:
                result.errors += 1
                logger.debug("Taxonomy build failed for %s: %s", domain, e)

        # After processing, identify cross-domain patterns
        await self._analyze_patterns(result)

        return result

    def _select_domains(self) -> List[str]:
        """Select domains for this run. Rotate through priority list."""
        r = self._get_redis()
        domains = list(_PRIORITY_DOMAINS)

        # Add domains from inventory tracker
        try:
            from adam.intelligence.page_intelligence import get_inventory_tracker
            tracker = get_inventory_tracker()
            for domain, _ in tracker.get_top_domains(50):
                if domain not in domains:
                    domains.append(domain)
        except Exception:
            pass

        # Prioritize domains with fewest taxonomy observations
        if r:
            scored = []
            for domain in domains:
                try:
                    data = r.hgetall(f"informativ:taxonomy:{domain}")
                    n = int(data.get("observation_count", 0)) if data else 0
                    scored.append((domain, n))
                except Exception:
                    scored.append((domain, 0))
            # Sort: lowest observation count first (needs more data)
            scored.sort(key=lambda x: x[1])
            domains = [d for d, _ in scored]

        return domains[:_MAX_DOMAINS_PER_RUN]

    async def _process_domain(self, domain: str) -> Dict[str, Any]:
        """Process a single domain: fetch articles, extract metadata, build taxonomy."""
        from adam.intelligence.domain_taxonomy import (
            DomainTaxonomy, extract_article_metadata, get_domain_taxonomy,
        )
        from adam.intelligence.page_intelligence import (
            profile_page_content, get_page_intelligence_cache,
        )

        taxonomy = get_domain_taxonomy(domain)
        cache = get_page_intelligence_cache()

        stats = {
            "domain": domain,
            "articles_fetched": 0,
            "articles_processed": 0,
            "taxonomy_updates": 0,
            "categories_found": set(),
            "authors_found": set(),
        }

        # Get article URLs from RSS or sitemaps
        article_urls = await self._get_article_urls(domain)
        if not article_urls:
            stats["note"] = "No article URLs found"
            return stats

        try:
            import httpx
        except ImportError:
            return stats

        async with httpx.AsyncClient(timeout=12, follow_redirects=True) as client:
            for url in article_urls[:_MAX_ARTICLES_PER_DOMAIN]:
                try:
                    # Fetch article
                    resp = await client.get(url, headers={
                        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
                    })

                    if resp.status_code != 200:
                        continue
                    if "text/html" not in resp.headers.get("content-type", ""):
                        continue

                    html = resp.text
                    stats["articles_fetched"] += 1

                    # Extract structured metadata
                    meta = extract_article_metadata(url, html)

                    # Extract clean text for NDF profiling
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(html, "html.parser")
                    for tag in soup(["script", "style", "nav", "footer",
                                     "header", "aside", "iframe"]):
                        tag.decompose()
                    # Remove ad containers
                    for sel in ["[class*='ad-']", "[class*='advertisement']",
                                "[class*='sidebar']", "[class*='newsletter']"]:
                        for tag in soup.select(sel):
                            tag.decompose()

                    main = (soup.find("article") or soup.find("main")
                            or soup.find("div", role="main") or soup.find("body"))
                    text = main.get_text(separator=" ", strip=True) if main else ""
                    text = " ".join(text.split())[:10000]

                    if len(text.split()) < 50:
                        continue

                    # NDF profile
                    title = meta.title or ""
                    profile = profile_page_content(
                        url=url, text_content=text, title=title,
                    )

                    # Populate metadata with NDF results
                    # Prefer full-width edge dimensions; fallback to NDF
                    meta.edge_dimensions = profile.edge_dimensions if profile.edge_dimensions else {}
                    meta.ndf_vector = profile.construct_activations
                    meta.mechanism_adjustments = profile.mechanism_adjustments
                    meta.mindset = profile.mindset
                    meta.confidence = profile.confidence
                    meta.word_count = len(text.split())

                    # Record into taxonomy hierarchy
                    record_result = taxonomy.record_article(meta)
                    if record_result.get("recorded"):
                        stats["taxonomy_updates"] += 1

                    stats["articles_processed"] += 1

                    if meta.category:
                        stats["categories_found"].add(meta.category)
                    if meta.author_slug:
                        stats["authors_found"].add(meta.author_slug)

                    # Also store in page cache for direct lookup
                    cache.store(profile)

                    if stats["articles_processed"] % 10 == 0:
                        logger.info(
                            "  %s: %d articles | cats=%s | authors=%d",
                            domain,
                            stats["articles_processed"],
                            list(stats["categories_found"])[:5],
                            len(stats["authors_found"]),
                        )

                except Exception as e:
                    logger.debug("Article processing failed for %s: %s", url, type(e).__name__)

                # Rate limit
                import asyncio
                await asyncio.sleep(1.0)

        # Convert sets to lists for JSON serialization
        stats["categories_found"] = sorted(stats["categories_found"])
        stats["authors_found"] = sorted(list(stats["authors_found"])[:20])

        return stats

    async def _get_article_urls(self, domain: str) -> List[str]:
        """Get article URLs for a domain from RSS feeds or sitemaps."""
        urls: List[str] = []

        r = self._get_redis()

        # Try RSS feed first (freshest content)
        if r:
            try:
                rss_data = r.hgetall(f"informativ:inventory:rss:{domain}")
                if rss_data:
                    feed_url = rss_data.get("feed_url", "")
                    if feed_url:
                        rss_urls = await self._fetch_rss_urls(feed_url, domain)
                        urls.extend(rss_urls)
            except Exception:
                pass

        # Supplement with sitemap URLs
        if r and len(urls) < _MAX_ARTICLES_PER_DOMAIN:
            try:
                sitemap_data = r.hgetall(f"informativ:inventory:sitemap:{domain}")
                if sitemap_data and "sample_urls" in sitemap_data:
                    sample = json.loads(sitemap_data["sample_urls"])
                    # Filter to actual article URLs (not sub-sitemaps)
                    article_urls = [
                        u for u in sample
                        if u.startswith("http") and domain in u
                        and not u.endswith(".xml")
                        and len(u.split("/")) >= 4
                    ]
                    urls.extend(article_urls[:_MAX_ARTICLES_PER_DOMAIN])
            except Exception:
                pass

        # Fallback: generate section URLs
        if not urls:
            sections = [
                "", "business", "politics", "health", "technology",
                "entertainment", "sports", "science", "travel", "style",
            ]
            for section in sections:
                if section:
                    urls.append(f"https://{domain}/{section}")
                else:
                    urls.append(f"https://{domain}/")

        # Deduplicate
        seen = set()
        unique = []
        for url in urls:
            if url not in seen:
                seen.add(url)
                unique.append(url)

        return unique

    async def _fetch_rss_urls(self, feed_url: str, domain: str) -> List[str]:
        """Fetch article URLs from an RSS feed."""
        urls = []
        try:
            import httpx
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(feed_url, headers={
                    "User-Agent": "Mozilla/5.0 (compatible; ADAM/1.0)"
                })
                if resp.status_code == 200:
                    # Extract URLs from RSS items
                    links = re.findall(r"<link>([^<]+)</link>", resp.text)
                    links += re.findall(r'<link[^>]+href="([^"]+)"', resp.text)
                    for link in links:
                        if link.startswith("http") and domain in link:
                            urls.append(link)
        except Exception:
            pass
        return urls[:_MAX_ARTICLES_PER_DOMAIN]

    async def _analyze_patterns(self, result: TaskResult) -> None:
        """Analyze learned taxonomy patterns across domains.

        Identifies:
        - High-consistency categories (reliable priors)
        - Author voice fingerprints (stable NDF)
        - Category NDF signatures (what makes politics different from health)
        """
        r = self._get_redis()
        if not r:
            return

        patterns = {
            "high_consistency_categories": [],
            "stable_authors": [],
            "category_distinctiveness": {},
        }

        try:
            # Find categories with high consistency
            cursor = 0
            while True:
                cursor, keys = r.scan(
                    cursor, match="informativ:taxonomy:*:cat:*", count=100,
                )
                for key in keys:
                    data = r.hgetall(key)
                    if data:
                        n = int(data.get("observation_count", 0))
                        c = float(data.get("overall_consistency", 0))
                        if n >= 5 and c > 0.6:
                            parts = key.replace("informativ:taxonomy:", "").split(":cat:")
                            patterns["high_consistency_categories"].append({
                                "domain": parts[0],
                                "category": parts[1] if len(parts) > 1 else "",
                                "observations": n,
                                "consistency": c,
                            })
                if cursor == 0:
                    break

            # Find stable authors
            cursor = 0
            while True:
                cursor, keys = r.scan(
                    cursor, match="informativ:taxonomy:*:author:*", count=100,
                )
                for key in keys:
                    data = r.hgetall(key)
                    if data:
                        n = int(data.get("observation_count", 0))
                        c = float(data.get("overall_consistency", 0))
                        if n >= 3 and c > 0.5:
                            patterns["stable_authors"].append({
                                "key": key.replace("informativ:taxonomy:", ""),
                                "observations": n,
                                "consistency": c,
                                "name": data.get("author_name", ""),
                            })
                if cursor == 0:
                    break

        except Exception as e:
            logger.debug("Pattern analysis failed: %s", e)

        if patterns["high_consistency_categories"] or patterns["stable_authors"]:
            self._store_redis_hash("informativ:taxonomy:_patterns", {
                "high_consistency_categories": patterns["high_consistency_categories"],
                "stable_authors": patterns["stable_authors"],
                "analyzed_at": time.time(),
            }, ttl=86400)

            result.details["high_consistency_categories"] = len(
                patterns["high_consistency_categories"]
            )
            result.details["stable_authors"] = len(patterns["stable_authors"])
