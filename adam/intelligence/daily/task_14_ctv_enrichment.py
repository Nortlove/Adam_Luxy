"""
Task 14: CTV Content Enrichment
=================================

Populates CTV content profiles from TMDb API, IMDB data, and
episode guide sites. Each show/movie is NDF-profiled using its
description, genre, and viewer reviews.

Schedule: Daily at 3 AM UTC
Redis keys:
- informativ:ctv:profile:{content_id} — CTV profiles (30-day TTL)
- informativ:ctv:taxonomy:{platform}:genre:{genre} — genre centroids
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any, Dict, List, Optional

from adam.intelligence.daily.base import DailyStrengtheningTask, TaskResult

logger = logging.getLogger(__name__)

_CTV_PROFILE_TTL = 86400 * 30   # 30 days
_GENRE_CENTROID_TTL = 86400 * 14  # 14 days

_TMDB_API_BASE = "https://api.themoviedb.org/3"

# Pre-built list of popular current shows across streaming platforms.
# Used as fallback when TMDb API key is not available.
_POPULAR_SHOWS = [
    # Apple TV+
    {"title": "Severance", "genre": ["thriller", "sci_fi", "drama"], "platform": "apple_tv", "tmdb_id": "95396"},
    {"title": "Slow Horses", "genre": ["thriller", "drama"], "platform": "apple_tv", "tmdb_id": "113988"},
    {"title": "Silo", "genre": ["sci_fi", "drama", "mystery"], "platform": "apple_tv", "tmdb_id": "125988"},
    {"title": "The Morning Show", "genre": ["drama"], "platform": "apple_tv", "tmdb_id": "75191"},
    {"title": "Shrinking", "genre": ["comedy", "drama"], "platform": "apple_tv", "tmdb_id": "136311"},
    {"title": "Ted Lasso", "genre": ["comedy", "drama", "sport"], "platform": "apple_tv", "tmdb_id": "97546"},

    # Hulu
    {"title": "The Bear", "genre": ["drama", "comedy"], "platform": "hulu", "tmdb_id": "136315"},
    {"title": "Only Murders in the Building", "genre": ["comedy", "mystery"], "platform": "hulu", "tmdb_id": "107113"},
    {"title": "Shogun", "genre": ["drama", "historical"], "platform": "hulu", "tmdb_id": "126308"},
    {"title": "The Handmaid's Tale", "genre": ["drama", "sci_fi"], "platform": "hulu", "tmdb_id": "69478"},

    # Netflix
    {"title": "Squid Game", "genre": ["thriller", "drama"], "platform": "netflix", "tmdb_id": "93405"},
    {"title": "Wednesday", "genre": ["comedy", "mystery", "fantasy"], "platform": "netflix", "tmdb_id": "119051"},
    {"title": "Stranger Things", "genre": ["sci_fi", "horror", "drama"], "platform": "netflix", "tmdb_id": "66732"},
    {"title": "Black Mirror", "genre": ["sci_fi", "thriller", "drama"], "platform": "netflix", "tmdb_id": "42009"},
    {"title": "The Diplomat", "genre": ["thriller", "drama"], "platform": "netflix", "tmdb_id": "151533"},
    {"title": "Beef", "genre": ["drama", "comedy"], "platform": "netflix", "tmdb_id": "154521"},
    {"title": "3 Body Problem", "genre": ["sci_fi", "drama", "mystery"], "platform": "netflix", "tmdb_id": "108545"},
    {"title": "Ripley", "genre": ["thriller", "drama", "crime"], "platform": "netflix", "tmdb_id": "37854"},
    {"title": "Baby Reindeer", "genre": ["drama", "thriller"], "platform": "netflix", "tmdb_id": "239770"},
    {"title": "The Night Agent", "genre": ["thriller", "action"], "platform": "netflix", "tmdb_id": "155441"},

    # HBO / Max
    {"title": "House of the Dragon", "genre": ["fantasy", "drama"], "platform": "hbo", "tmdb_id": "94997"},
    {"title": "The Last of Us", "genre": ["drama", "sci_fi", "action"], "platform": "hbo", "tmdb_id": "100088"},
    {"title": "The White Lotus", "genre": ["drama", "comedy"], "platform": "hbo", "tmdb_id": "111803"},
    {"title": "Succession", "genre": ["drama"], "platform": "hbo", "tmdb_id": "76331"},
    {"title": "True Detective", "genre": ["crime", "drama", "mystery"], "platform": "hbo", "tmdb_id": "46648"},
    {"title": "Industry", "genre": ["drama"], "platform": "hbo", "tmdb_id": "94990"},
    {"title": "Hacks", "genre": ["comedy", "drama"], "platform": "hbo", "tmdb_id": "117031"},

    # Disney+
    {"title": "Andor", "genre": ["sci_fi", "drama", "action"], "platform": "disney_plus", "tmdb_id": "83867"},
    {"title": "Loki", "genre": ["sci_fi", "fantasy", "action"], "platform": "disney_plus", "tmdb_id": "84958"},
    {"title": "The Mandalorian", "genre": ["sci_fi", "action", "adventure"], "platform": "disney_plus", "tmdb_id": "82856"},
    {"title": "Percy Jackson", "genre": ["fantasy", "adventure"], "platform": "disney_plus", "tmdb_id": "121234"},
    {"title": "Echo", "genre": ["action", "drama"], "platform": "disney_plus", "tmdb_id": "115036"},

    # Amazon Prime
    {"title": "The Boys", "genre": ["action", "comedy", "sci_fi"], "platform": "amazon_prime", "tmdb_id": "76479"},
    {"title": "Fallout", "genre": ["sci_fi", "action", "drama"], "platform": "amazon_prime", "tmdb_id": "106379"},
    {"title": "Reacher", "genre": ["action", "crime", "thriller"], "platform": "amazon_prime", "tmdb_id": "108978"},
    {"title": "The Rings of Power", "genre": ["fantasy", "drama", "adventure"], "platform": "amazon_prime", "tmdb_id": "84773"},
    {"title": "Citadel", "genre": ["action", "thriller", "sci_fi"], "platform": "amazon_prime", "tmdb_id": "114472"},
    {"title": "Mr. & Mrs. Smith", "genre": ["action", "comedy", "thriller"], "platform": "amazon_prime", "tmdb_id": "218145"},

    # Peacock
    {"title": "Poker Face", "genre": ["mystery", "comedy", "drama"], "platform": "peacock", "tmdb_id": "156902"},
    {"title": "Bel-Air", "genre": ["drama"], "platform": "peacock", "tmdb_id": "133372"},
    {"title": "The Traitors", "genre": ["reality", "game_show"], "platform": "peacock", "tmdb_id": "216070"},

    # Paramount+
    {"title": "Yellowjackets", "genre": ["drama", "thriller", "mystery"], "platform": "paramount_plus", "tmdb_id": "73586"},
    {"title": "Tulsa King", "genre": ["crime", "drama"], "platform": "paramount_plus", "tmdb_id": "152831"},
    {"title": "Lioness", "genre": ["action", "thriller", "drama"], "platform": "paramount_plus", "tmdb_id": "209085"},
    {"title": "1923", "genre": ["drama", "western"], "platform": "paramount_plus", "tmdb_id": "153312"},

    # Tubi (free ad-supported)
    {"title": "Tubi Originals: Corrective Measures", "genre": ["action", "sci_fi"], "platform": "tubi", "tmdb_id": ""},
    {"title": "Tubi Originals: Swim", "genre": ["horror", "thriller"], "platform": "tubi", "tmdb_id": ""},

    # Pluto TV (free ad-supported)
    {"title": "Pluto TV Movies", "genre": ["drama", "action"], "platform": "pluto", "tmdb_id": ""},
    {"title": "Pluto TV Crime", "genre": ["crime", "drama", "mystery"], "platform": "pluto", "tmdb_id": ""},
]

_STREAMING_PLATFORMS = [
    "netflix", "hulu", "hbo", "disney_plus", "apple_tv",
    "amazon_prime", "peacock", "paramount_plus", "tubi", "pluto",
]


class CTVEnrichmentTask(DailyStrengtheningTask):
    """Populate CTV content profiles from metadata APIs and show lists."""

    @property
    def name(self) -> str:
        return "ctv_enrichment"

    @property
    def schedule_hours(self) -> List[int]:
        return [3]  # Daily at 3 AM UTC

    @property
    def frequency_hours(self) -> int:
        return 24

    async def execute(self) -> TaskResult:
        result = TaskResult(task_name=self.name, success=True)

        tmdb_key = os.environ.get("TMDB_API_KEY", "")
        result.details["tmdb_available"] = bool(tmdb_key)

        # Phase 1: Profile shows from the pre-built list and/or TMDb
        show_stats = await self._process_shows(tmdb_key)
        result.items_processed += show_stats.get("shows_processed", 0)
        result.items_stored += show_stats.get("profiles_stored", 0)
        result.errors += show_stats.get("errors", 0)
        result.details["shows"] = show_stats

        # Phase 2: Build genre centroids for taxonomy inference
        taxonomy_stats = self._build_genre_taxonomy()
        result.details["taxonomy"] = taxonomy_stats

        return result

    async def _process_shows(self, tmdb_key: str) -> Dict[str, Any]:
        """Process all shows: fetch metadata, NDF-profile, store."""
        stats = {
            "shows_processed": 0,
            "profiles_stored": 0,
            "tmdb_fetched": 0,
            "fallback_used": 0,
            "errors": 0,
        }

        try:
            import httpx
        except ImportError:
            stats["note"] = "httpx not installed"
            return stats

        async with httpx.AsyncClient(timeout=15) as client:
            for show in _POPULAR_SHOWS:
                try:
                    show_data = dict(show)  # Copy to avoid mutation

                    # Try TMDb API for richer metadata
                    if tmdb_key and show.get("tmdb_id"):
                        enriched = await self._fetch_tmdb_metadata(
                            client, tmdb_key, show["tmdb_id"],
                        )
                        if enriched:
                            show_data.update(enriched)
                            stats["tmdb_fetched"] += 1
                        else:
                            stats["fallback_used"] += 1
                    else:
                        stats["fallback_used"] += 1

                    # Profile the show
                    profile = self._profile_show(show_data)
                    if profile:
                        stored = self._store_ctv_profile(show_data, profile)
                        if stored:
                            stats["profiles_stored"] += 1

                    stats["shows_processed"] += 1

                except Exception as e:
                    stats["errors"] += 1
                    logger.debug(
                        "CTV enrichment failed for %s: %s",
                        show.get("title", "?"), e,
                    )

                # Rate limit TMDb requests
                if tmdb_key and show.get("tmdb_id"):
                    import asyncio
                    await asyncio.sleep(0.3)

        return stats

    async def _fetch_tmdb_metadata(
        self, client: Any, api_key: str, tmdb_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Fetch show metadata from TMDb API."""
        if not tmdb_id:
            return None

        try:
            url = f"{_TMDB_API_BASE}/tv/{tmdb_id}"
            resp = await client.get(
                url,
                params={"api_key": api_key, "language": "en-US"},
            )
            if resp.status_code != 200:
                return None

            data = resp.json()
            return {
                "overview": data.get("overview", ""),
                "tmdb_genres": [g.get("name", "") for g in data.get("genres", [])],
                "vote_average": data.get("vote_average", 0),
                "vote_count": data.get("vote_count", 0),
                "popularity": data.get("popularity", 0),
                "first_air_date": data.get("first_air_date", ""),
                "status": data.get("status", ""),
                "tagline": data.get("tagline", ""),
                "number_of_seasons": data.get("number_of_seasons", 0),
                "networks": [n.get("name", "") for n in data.get("networks", [])],
            }

        except Exception as e:
            logger.debug("TMDb fetch failed for %s: %s", tmdb_id, e)
            return None

    def _profile_show(self, show_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """NDF-profile a show using its metadata."""
        title = show_data.get("title", "")
        overview = show_data.get("overview", "")
        genres = show_data.get("genre", [])
        tagline = show_data.get("tagline", "")

        # Build descriptive text for NDF profiling
        text_parts = [title]
        if tagline:
            text_parts.append(tagline)
        if overview:
            text_parts.append(overview)
        text_parts.append(f"Genre: {', '.join(genres)}")
        text_parts.append(f"Platform: {show_data.get('platform', 'streaming')}")

        text = ". ".join(text_parts)

        # Try dedicated CTV profiler first
        try:
            from adam.intelligence.ctv_intelligence import profile_ctv_content
            profile = profile_ctv_content(
                content_id=show_data.get("tmdb_id", ""),
                title=title,
                description=overview or title,
                genre=genres,
                platform=show_data.get("platform", ""),
            )
            return {
                "ndf_vector": profile.construct_activations,
                "mechanism_adjustments": profile.mechanism_adjustments,
                "mindset": profile.mindset,
                "confidence": profile.confidence,
                "remaining_bandwidth": profile.remaining_bandwidth,
                "title": title,
                "genres": genres,
                "platform": show_data.get("platform", ""),
                "content_type": "ctv_content",
                "profile_source": profile.profile_source,
            }
        except Exception as e:
            logger.debug("CTV profiler failed for %s: %s", title, e)

        # Fallback: use base NDF extraction
        ndf = self._ndf_from_text(text)
        return {
            "ndf_vector": ndf,
            "title": title,
            "genres": genres,
            "platform": show_data.get("platform", ""),
            "confidence": 0.5 if overview else 0.3,
        }

    def _store_ctv_profile(
        self, show_data: Dict[str, Any], profile: Dict[str, Any],
    ) -> bool:
        """Store CTV profile in Redis."""
        content_id = show_data.get("tmdb_id", "")
        if not content_id:
            # Generate a slug-based ID for shows without TMDb ID
            title = show_data.get("title", "unknown")
            content_id = title.lower().replace(" ", "_").replace("'", "")[:50]

        key = f"informativ:ctv:profile:{content_id}"

        store_data = {
            "title": show_data.get("title", ""),
            "platform": show_data.get("platform", ""),
            "genres": show_data.get("genre", []),
            "ndf_vector": profile.get("ndf_vector", {}),
            "confidence": profile.get("confidence", 0.5),
            "vote_average": show_data.get("vote_average", 0),
            "popularity": show_data.get("popularity", 0),
            "overview": show_data.get("overview", "")[:500],
            "enriched_at": time.time(),
            "content_type": "ctv_content",
        }

        return self._store_redis_hash(key, store_data, ttl=_CTV_PROFILE_TTL)

    def _build_genre_taxonomy(self) -> Dict[str, Any]:
        """Build genre centroids from stored CTV profiles for taxonomy inference."""
        r = self._get_redis()
        if not r:
            return {"note": "Redis not available"}

        stats = {
            "genres_updated": 0,
            "platforms_covered": set(),
        }

        # Collect NDF vectors per (platform, genre) pair
        genre_vectors: Dict[str, List[Dict[str, float]]] = {}

        try:
            cursor = 0
            while True:
                cursor, keys = r.scan(
                    cursor, match="informativ:ctv:profile:*", count=100,
                )
                for key in keys:
                    try:
                        data = r.hgetall(key)
                        if not data:
                            continue

                        platform = data.get("platform", "unknown")
                        genres_raw = data.get("genres", "[]")
                        if isinstance(genres_raw, str):
                            try:
                                genres = json.loads(genres_raw)
                            except Exception:
                                genres = []
                        else:
                            genres = genres_raw if isinstance(genres_raw, list) else []

                        ndf_raw = data.get("ndf_vector", "{}")
                        if isinstance(ndf_raw, str):
                            try:
                                ndf = json.loads(ndf_raw)
                            except Exception:
                                ndf = {}
                        else:
                            ndf = ndf_raw if isinstance(ndf_raw, dict) else {}

                        if not ndf:
                            continue

                        stats["platforms_covered"].add(platform)

                        for genre in genres:
                            bucket_key = f"{platform}:{genre}"
                            if bucket_key not in genre_vectors:
                                genre_vectors[bucket_key] = []
                            genre_vectors[bucket_key].append(ndf)

                    except Exception:
                        pass
                if cursor == 0:
                    break

            # Compute and store centroids
            for bucket_key, vectors in genre_vectors.items():
                if len(vectors) < 2:
                    continue

                centroid = self._compute_centroid(vectors)
                if centroid:
                    platform, genre = bucket_key.split(":", 1)
                    centroid_key = f"informativ:ctv:taxonomy:{platform}:genre:{genre}"
                    centroid_data = {
                        "centroid": centroid,
                        "observation_count": len(vectors),
                        "computed_at": time.time(),
                    }
                    self._store_redis_hash(
                        centroid_key, centroid_data, ttl=_GENRE_CENTROID_TTL,
                    )
                    stats["genres_updated"] += 1

        except Exception as e:
            logger.debug("Genre taxonomy build failed: %s", e)

        stats["platforms_covered"] = sorted(stats["platforms_covered"])
        return stats

    def _compute_centroid(
        self, vectors: List[Dict[str, float]],
    ) -> Dict[str, float]:
        """Compute the centroid (element-wise mean) of NDF vectors."""
        if not vectors:
            return {}

        all_dims: set = set()
        for v in vectors:
            all_dims.update(v.keys())

        centroid = {}
        for dim in all_dims:
            values = [v.get(dim, 0.0) for v in vectors]
            try:
                centroid[dim] = sum(float(x) for x in values) / len(values)
            except (ValueError, TypeError):
                centroid[dim] = 0.0

        return centroid
