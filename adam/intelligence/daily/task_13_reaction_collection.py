"""
Task 13: Audience Reaction Collection
=======================================

Collects and profiles audience reactions to content:
- Web: article comments, Reddit threads about articles
- CTV: IMDB reviews, Reddit episode discussions

Reactions REVEAL the actual psychological state content creates,
providing confirmation or correction of the content-based NDF prediction.

Schedule: Twice daily (run after taxonomy builder)
Redis keys:
- informativ:reaction:web:{url_pattern} — web reaction profiles (24h TTL)
- informativ:reaction:ctv:{content_id} — CTV reaction profiles (48h TTL)
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from typing import Any, Dict, List, Optional

from adam.intelligence.daily.base import DailyStrengtheningTask, TaskResult

logger = logging.getLogger(__name__)

_REDDIT_SEARCH_URL = "https://www.reddit.com/search.json"
_REDDIT_DELAY = 2.0  # seconds between Reddit requests
_DEFAULT_DELAY = 1.0  # seconds between other requests

_WEB_REACTION_TTL = 86400       # 24 hours
_CTV_REACTION_TTL = 172800      # 48 hours

_MAX_WEB_PAGES = 100
_MAX_CTV_CONTENT = 50

# CSS selectors for comment sections
_COMMENT_SELECTORS = [
    "[class*='comment']",
    "[id*='disqus']",
    "[class*='discussion']",
    "[id*='comments']",
    "[class*='responses']",
    "[class*='user-content']",
]


class ReactionCollectionTask(DailyStrengtheningTask):
    """Collect audience reactions and compute NDF confirmation/correction."""

    @property
    def name(self) -> str:
        return "reaction_collection"

    @property
    def schedule_hours(self) -> List[int]:
        return [4, 16]  # Twice daily, after taxonomy builder

    @property
    def frequency_hours(self) -> int:
        return 12

    async def execute(self) -> TaskResult:
        result = TaskResult(task_name=self.name, success=True)

        # Phase 1: Web page reactions
        web_stats = await self._collect_web_reactions()
        result.items_processed += web_stats.get("pages_checked", 0)
        result.items_stored += web_stats.get("reactions_stored", 0)
        result.details["web"] = web_stats

        # Phase 2: CTV content reactions
        ctv_stats = await self._collect_ctv_reactions()
        result.items_processed += ctv_stats.get("content_checked", 0)
        result.items_stored += ctv_stats.get("reactions_stored", 0)
        result.details["ctv"] = ctv_stats

        result.errors = web_stats.get("errors", 0) + ctv_stats.get("errors", 0)
        return result

    # ── Web Reactions ────────────────────────────────────────────────

    async def _collect_web_reactions(self) -> Dict[str, Any]:
        """Collect reactions for top web pages by impression count."""
        stats = {
            "pages_checked": 0,
            "reactions_found": 0,
            "reactions_stored": 0,
            "errors": 0,
        }

        top_pages = self._get_top_web_pages()
        if not top_pages:
            stats["note"] = "No web pages found in impression tracking"
            return stats

        try:
            import httpx
        except ImportError:
            stats["note"] = "httpx not installed"
            return stats

        async with httpx.AsyncClient(
            timeout=15,
            follow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"},
        ) as client:
            for page_url in top_pages[:_MAX_WEB_PAGES]:
                try:
                    reactions = await self._collect_reactions_for_page(
                        client, page_url,
                    )
                    stats["pages_checked"] += 1

                    if not reactions:
                        continue

                    stats["reactions_found"] += 1

                    # NDF-profile the reaction text
                    profile = self._profile_reactions(reactions, page_url)
                    if profile:
                        # Compare with content NDF and compute correction
                        corrected = self._compute_correction(page_url, profile)
                        if corrected:
                            stored = self._store_web_reaction(page_url, corrected)
                            if stored:
                                stats["reactions_stored"] += 1

                except Exception as e:
                    stats["errors"] += 1
                    logger.debug("Reaction collection failed for %s: %s", page_url, e)

        return stats

    def _get_top_web_pages(self) -> List[str]:
        """Get top web pages by impression count from Redis inventory."""
        r = self._get_redis()
        if not r:
            return []

        pages = []
        try:
            # Check impression tracking keys
            cursor = 0
            scored = []
            while True:
                cursor, keys = r.scan(
                    cursor, match="informativ:page:*", count=200,
                )
                for key in keys:
                    # Skip domain-level keys
                    if ":domain:" in key or ":_patterns" in key:
                        continue
                    try:
                        data = r.hgetall(key)
                        impressions = int(data.get("crawl_count", data.get("impression_count", "0")))
                        url_pattern = data.get("url_pattern", "")
                        if url_pattern and impressions > 0:
                            scored.append((url_pattern, impressions))
                    except Exception:
                        pass
                if cursor == 0:
                    break

            # Sort by impression count, highest first
            scored.sort(key=lambda x: x[1], reverse=True)
            pages = [url for url, _ in scored[:_MAX_WEB_PAGES]]

        except Exception as e:
            logger.debug("Failed to get top web pages: %s", e)

        return pages

    async def _collect_reactions_for_page(
        self,
        client: Any,
        page_url: str,
    ) -> List[str]:
        """Collect reaction texts from HTML comments and Reddit threads."""
        reactions: List[str] = []

        # Source 1: HTML comments on the article page
        try:
            resp = await client.get(page_url)
            if resp.status_code == 200 and "text/html" in resp.headers.get("content-type", ""):
                html_comments = self._extract_html_comments(resp.text)
                reactions.extend(html_comments)
        except Exception:
            pass

        await asyncio.sleep(_DEFAULT_DELAY)

        # Source 2: Reddit threads mentioning this URL
        try:
            reddit_comments = await self._search_reddit(client, page_url)
            reactions.extend(reddit_comments)
        except Exception:
            pass

        await asyncio.sleep(_REDDIT_DELAY)

        return reactions

    def _extract_html_comments(self, html: str) -> List[str]:
        """Extract comment text from HTML using common comment section selectors."""
        comments: List[str] = []

        try:
            from bs4 import BeautifulSoup
        except ImportError:
            return comments

        soup = BeautifulSoup(html, "html.parser")
        seen_texts: set = set()

        for selector in _COMMENT_SELECTORS:
            try:
                elements = soup.select(selector)
                for el in elements:
                    text = el.get_text(separator=" ", strip=True)
                    text = " ".join(text.split())
                    # Filter: must be substantive (not just "Reply" or a username)
                    if len(text) > 30 and text not in seen_texts:
                        seen_texts.add(text)
                        comments.append(text[:2000])  # Cap individual comment length
            except Exception:
                pass

        return comments[:50]  # Cap total comments per page

    async def _search_reddit(self, client: Any, query: str) -> List[str]:
        """Search Reddit for discussions about a URL or topic."""
        comments: List[str] = []

        try:
            resp = await client.get(
                _REDDIT_SEARCH_URL,
                params={"q": query, "sort": "new", "limit": "25"},
                headers={
                    "User-Agent": "ADAM-Intelligence/1.0 (research)",
                },
            )
            if resp.status_code != 200:
                return comments

            data = resp.json()
            children = data.get("data", {}).get("children", [])

            for child in children:
                post = child.get("data", {})
                title = post.get("title", "")
                selftext = post.get("selftext", "")
                combined = f"{title} {selftext}".strip()
                if len(combined) > 20:
                    comments.append(combined[:3000])

        except Exception as e:
            logger.debug("Reddit search failed for %s: %s", query[:60], e)

        return comments

    # ── CTV Reactions ────────────────────────────────────────────────

    async def _collect_ctv_reactions(self) -> Dict[str, Any]:
        """Collect reactions for CTV content from Reddit and IMDB."""
        stats = {
            "content_checked": 0,
            "reactions_found": 0,
            "reactions_stored": 0,
            "errors": 0,
        }

        ctv_content = self._get_ctv_content_ids()
        if not ctv_content:
            stats["note"] = "No CTV content found in Redis"
            return stats

        try:
            import httpx
        except ImportError:
            stats["note"] = "httpx not installed"
            return stats

        async with httpx.AsyncClient(
            timeout=15,
            follow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"},
        ) as client:
            for content_id, content_meta in ctv_content[:_MAX_CTV_CONTENT]:
                try:
                    reactions: List[str] = []
                    stats["content_checked"] += 1

                    title = content_meta.get("title", content_id)

                    # Source 1: Reddit discussions about the show
                    reddit_comments = await self._search_reddit(
                        client, f"{title} TV show discussion",
                    )
                    reactions.extend(reddit_comments)
                    await asyncio.sleep(_REDDIT_DELAY)

                    # Source 2: IMDB reviews if content_id is a TMDb/IMDB ID
                    if content_id.startswith("tt"):
                        imdb_reviews = await self._fetch_imdb_reviews(
                            client, content_id,
                        )
                        reactions.extend(imdb_reviews)
                        await asyncio.sleep(_DEFAULT_DELAY)

                    if not reactions:
                        continue

                    stats["reactions_found"] += 1

                    # Profile the reactions
                    profile = self._profile_reactions(reactions, content_id)
                    if profile:
                        corrected = self._compute_ctv_correction(
                            content_id, content_meta, profile,
                        )
                        if corrected:
                            stored = self._store_ctv_reaction(content_id, corrected)
                            if stored:
                                stats["reactions_stored"] += 1

                except Exception as e:
                    stats["errors"] += 1
                    logger.debug(
                        "CTV reaction collection failed for %s: %s",
                        content_id, e,
                    )

        return stats

    def _get_ctv_content_ids(self) -> List[tuple]:
        """Get CTV content IDs from Redis profiles."""
        r = self._get_redis()
        if not r:
            return []

        results = []
        try:
            cursor = 0
            while True:
                cursor, keys = r.scan(
                    cursor, match="informativ:ctv:profile:*", count=100,
                )
                for key in keys:
                    content_id = key.replace("informativ:ctv:profile:", "")
                    try:
                        data = r.hgetall(key)
                        results.append((content_id, data or {}))
                    except Exception:
                        results.append((content_id, {}))
                if cursor == 0:
                    break
        except Exception:
            pass

        return results[:_MAX_CTV_CONTENT]

    async def _fetch_imdb_reviews(self, client: Any, imdb_id: str) -> List[str]:
        """Fetch user reviews from IMDB for a given title ID."""
        reviews: List[str] = []

        try:
            url = f"https://www.imdb.com/title/{imdb_id}/reviews"
            resp = await client.get(url)
            if resp.status_code != 200:
                return reviews

            # Extract review text from HTML
            try:
                from bs4 import BeautifulSoup
            except ImportError:
                return reviews

            soup = BeautifulSoup(resp.text, "html.parser")

            # IMDB review containers
            for review_el in soup.select(".review-container, .text, .content .text"):
                text = review_el.get_text(separator=" ", strip=True)
                text = " ".join(text.split())
                if len(text) > 50:
                    reviews.append(text[:3000])

            # Also try lister-item-content pattern
            if not reviews:
                for item in soup.select(".lister-item-content"):
                    text = item.get_text(separator=" ", strip=True)
                    text = " ".join(text.split())
                    if len(text) > 50:
                        reviews.append(text[:3000])

        except Exception as e:
            logger.debug("IMDB review fetch failed for %s: %s", imdb_id, e)

        return reviews[:30]

    # ── NDF Profiling & Correction ───────────────────────────────────

    def _profile_reactions(
        self, reactions: List[str], source_id: str,
    ) -> Optional[Dict[str, Any]]:
        """NDF-profile collected reaction texts."""
        if not reactions:
            return None

        try:
            from adam.intelligence.reaction_intelligence import extract_reaction_ndf
        except ImportError:
            # Fallback: use base NDF extraction
            combined = " ".join(reactions[:20])[:15000]
            ndf = self._ndf_from_text(combined)
            return {
                "ndf_vector": ndf,
                "reaction_count": len(reactions),
                "total_chars": sum(len(r) for r in reactions),
                "source": source_id,
            }

        # Use dedicated reaction NDF extractor
        combined = " ".join(reactions[:20])[:15000]
        reaction_ndf = extract_reaction_ndf(combined)
        return {
            "ndf_vector": reaction_ndf.get("ndf_vector", {}),
            "emotional_tone": reaction_ndf.get("emotional_tone", {}),
            "engagement_level": reaction_ndf.get("engagement_level", 0.5),
            "reaction_count": len(reactions),
            "total_chars": sum(len(r) for r in reactions),
            "source": source_id,
        }

    def _compute_correction(
        self, page_url: str, reaction_profile: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """Compare reaction NDF with content NDF; compute confirmation/correction."""
        try:
            from adam.intelligence.reaction_intelligence import (
                compute_confirmation_correction,
            )
        except ImportError:
            # Fallback: store raw reaction profile without correction
            return {
                "reaction_ndf": reaction_profile.get("ndf_vector", {}),
                "reaction_count": reaction_profile.get("reaction_count", 0),
                "correction_applied": False,
                "collected_at": time.time(),
            }

        # Get existing content NDF
        content_ndf = self._get_content_ndf(page_url)

        correction = compute_confirmation_correction(
            content_ndf=content_ndf,
            reaction_ndf=reaction_profile.get("ndf_vector", {}),
        )
        correction["reaction_count"] = reaction_profile.get("reaction_count", 0)
        correction["collected_at"] = time.time()
        return correction

    def _compute_ctv_correction(
        self,
        content_id: str,
        content_meta: Dict[str, Any],
        reaction_profile: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """Compute correction for CTV content."""
        try:
            from adam.intelligence.reaction_intelligence import (
                compute_confirmation_correction,
            )
        except ImportError:
            return {
                "reaction_ndf": reaction_profile.get("ndf_vector", {}),
                "reaction_count": reaction_profile.get("reaction_count", 0),
                "correction_applied": False,
                "collected_at": time.time(),
            }

        # Get content NDF from CTV profile
        content_ndf = {}
        ndf_json = content_meta.get("ndf_vector", "{}")
        if isinstance(ndf_json, str):
            try:
                content_ndf = json.loads(ndf_json)
            except Exception:
                pass
        elif isinstance(ndf_json, dict):
            content_ndf = ndf_json

        correction = compute_confirmation_correction(
            content_ndf=content_ndf,
            reaction_ndf=reaction_profile.get("ndf_vector", {}),
        )
        correction["reaction_count"] = reaction_profile.get("reaction_count", 0)
        correction["content_id"] = content_id
        correction["collected_at"] = time.time()
        return correction

    def _get_content_ndf(self, page_url: str) -> Dict[str, float]:
        """Retrieve the content-side NDF for a page."""
        try:
            from adam.intelligence.page_intelligence import (
                get_page_intelligence_cache,
            )
            cache = get_page_intelligence_cache()
            profile = cache.lookup(page_url)
            if profile:
                return profile.construct_activations
        except Exception:
            pass
        return {}

    def _store_web_reaction(
        self, page_url: str, data: Dict[str, Any],
    ) -> bool:
        """Store web reaction profile in Redis."""
        from adam.intelligence.page_intelligence import _url_to_pattern
        pattern = _url_to_pattern(page_url)
        key = f"informativ:reaction:web:{pattern}"
        return self._store_redis_hash(key, data, ttl=_WEB_REACTION_TTL)

    def _store_ctv_reaction(
        self, content_id: str, data: Dict[str, Any],
    ) -> bool:
        """Store CTV reaction profile in Redis."""
        key = f"informativ:reaction:ctv:{content_id}"
        return self._store_redis_hash(key, data, ttl=_CTV_REACTION_TTL)
