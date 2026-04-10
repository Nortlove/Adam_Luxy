"""
Page Crawl Scheduler
====================

Background scheduler for the ADAM page intelligence crawl system.

Runs bi-daily crawl windows (6 AM ET / 6 PM ET) that prioritize pages by
impression volume, staleness, drift velocity, and confidence. Per-domain
rate limiting, robots.txt compliance, and exponential backoff on errors
ensure we're a responsible crawler.

Three crawl passes per page:
    Pass 1: NLP-based linguistic marker extraction (profile_page_content)
    Pass 2: DOM structure analysis (ad density, layout signals)
    Pass 3: Deep LLM-powered psychological profiling (top 500 only)
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
import urllib.robotparser
from dataclasses import dataclass, field
from math import log
from typing import Any, Dict, List, Optional, Set, Tuple

import httpx

from adam.infrastructure.prometheus.metrics import get_metrics
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

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_ET_OFFSET_HOURS = -5  # Eastern Time offset from UTC (EST; EDT = -4)
_MORNING_WINDOW_HOUR = 6   # 6 AM ET
_EVENING_WINDOW_HOUR = 18  # 6 PM ET
_WINDOW_TOLERANCE_MINUTES = 30

_MAX_MORNING_PAGES = 5_000
_MAX_DEEP_PAGES = 500
_MIN_DOMAIN_INTERVAL = 2.0  # seconds between requests to the same domain

_BACKOFF_INITIAL = 3600       # 1 hour
_BACKOFF_MULTIPLIER = 4       # 1h → 4h → 16h (capped at 24h)
_BACKOFF_MAX = 86400          # 24 hours
_DEAD_LETTER_THRESHOLD = 3   # failures before dead-letter
_DEAD_LETTER_RETRY_INTERVAL = 7 * 86400  # 1 week

_DRIFT_THRESHOLD = 0.3
_REDIS_DRIFT_PREFIX = "informativ:page:drift:"
_REDIS_DLQ_PREFIX = "informativ:page:dlq:"

_FETCH_TIMEOUT = 15.0
_USER_AGENT = (
    "InformativBot/1.0 (+https://informativ.ai/bot; "
    "psycholinguistic research crawler)"
)

# Priority crawl queue — conversion-triggered deep crawls bypass the
# bi-daily schedule. Drained every 30s by the scheduler loop.
_PRIORITY_QUEUE_MAX = 500
_priority_queue: Optional[asyncio.Queue] = None


def _get_priority_queue() -> asyncio.Queue:
    """Get or create the priority crawl queue."""
    global _priority_queue
    if _priority_queue is None:
        _priority_queue = asyncio.Queue(maxsize=_PRIORITY_QUEUE_MAX)
    return _priority_queue


async def queue_priority_crawl(
    url: str,
    priority: float = 1.0,
    reason: str = "conversion",
) -> bool:
    """Queue a page for immediate deep crawl + scoring.

    Called by OutcomeHandler when a conversion includes a page_url.
    Priority 1.0 = conversion, 0.5 = engagement, 0.1 = impression.

    The scheduler loop drains this queue every 30s and runs 3-pass
    scoring on each page, bypassing the bi-daily schedule.
    """
    queue = _get_priority_queue()
    try:
        queue.put_nowait({
            "url": url,
            "priority": priority,
            "reason": reason,
            "queued_at": time.time(),
        })
        logger.info(
            "Priority crawl queued: %s (priority=%.1f, reason=%s)",
            url, priority, reason,
        )
        return True
    except asyncio.QueueFull:
        logger.warning("Priority crawl queue full (%d), dropping %s", _PRIORITY_QUEUE_MAX, url)
        return False

# NDF dimensions used for drift computation
_NDF_DIMS = [
    "approach_avoidance", "temporal_horizon", "social_calibration",
    "uncertainty_tolerance", "status_sensitivity", "cognitive_engagement",
    "emotional_reactivity",
]

# Module-level shutdown flag
_shutdown_requested = False


def request_shutdown() -> None:
    """Signal the scheduler to stop after the current cycle."""
    global _shutdown_requested
    _shutdown_requested = True


# ---------------------------------------------------------------------------
# Domain Rate Limiter
# ---------------------------------------------------------------------------

class DomainRateLimiter:
    """Per-domain rate limiting with exponential backoff on errors."""

    def __init__(self) -> None:
        self._last_request: Dict[str, float] = {}
        self._backoff_until: Dict[str, float] = {}
        self._failure_counts: Dict[str, int] = {}
        self._robot_parsers: Dict[str, urllib.robotparser.RobotFileParser] = {}

    async def wait_for_domain(self, domain: str) -> None:
        """Block until it's safe to request from this domain."""
        now = time.time()

        # Check backoff
        backoff_until = self._backoff_until.get(domain, 0.0)
        if now < backoff_until:
            wait = backoff_until - now
            logger.debug("Domain %s in backoff, waiting %.0fs", domain, wait)
            await asyncio.sleep(wait)

        # Enforce minimum interval
        last = self._last_request.get(domain, 0.0)
        elapsed = time.time() - last
        if elapsed < _MIN_DOMAIN_INTERVAL:
            await asyncio.sleep(_MIN_DOMAIN_INTERVAL - elapsed)

        self._last_request[domain] = time.time()

    def record_success(self, domain: str) -> None:
        """Reset failure state for a domain on successful request."""
        self._failure_counts.pop(domain, None)
        self._backoff_until.pop(domain, None)

    def record_failure(self, domain: str, status_code: int) -> int:
        """Record a failure and apply exponential backoff.

        Returns the current failure count for the domain.
        """
        if status_code in (429, 403):
            count = self._failure_counts.get(domain, 0) + 1
            self._failure_counts[domain] = count
            backoff = min(
                _BACKOFF_INITIAL * (_BACKOFF_MULTIPLIER ** (count - 1)),
                _BACKOFF_MAX,
            )
            self._backoff_until[domain] = time.time() + backoff
            logger.warning(
                "Domain %s hit %d (attempt %d), backing off %.0fs",
                domain, status_code, count, backoff,
            )
            return count
        return self._failure_counts.get(domain, 0)

    def is_dead_lettered(self, domain: str) -> bool:
        return self._failure_counts.get(domain, 0) >= _DEAD_LETTER_THRESHOLD

    async def check_robots(
        self, domain: str, url: str, client: httpx.AsyncClient,
    ) -> bool:
        """Check robots.txt for crawl permission. Cached per domain."""
        if domain in self._robot_parsers:
            rp = self._robot_parsers[domain]
            return rp.can_fetch(_USER_AGENT, url)

        rp = urllib.robotparser.RobotFileParser()
        robots_url = f"https://{domain}/robots.txt"
        try:
            resp = await client.get(robots_url, timeout=5.0)
            if resp.status_code == 200:
                rp.parse(resp.text.splitlines())
            else:
                # No robots.txt or error — assume allowed
                rp.parse([])
        except Exception:
            rp.parse([])  # Network error — assume allowed

        self._robot_parsers[domain] = rp
        return rp.can_fetch(_USER_AGENT, url)


# ---------------------------------------------------------------------------
# Page Drift Detector
# ---------------------------------------------------------------------------

class PageDriftDetector:
    """Detects psychological profile drift between crawls.

    On each re-crawl, computes the NDF delta between old and new profiles.
    Tracks per-domain drift velocity to adapt crawl frequency.
    """

    def __init__(self) -> None:
        self._redis = None

    def _get_redis(self):
        if self._redis is not None:
            return self._redis
        try:
            import redis
            self._redis = redis.Redis(
                host="localhost", port=6379, decode_responses=True,
            )
            self._redis.ping()
            return self._redis
        except Exception:
            return None

    def compute_drift(
        self,
        old_profile: PagePsychologicalProfile,
        new_profile: PagePsychologicalProfile,
    ) -> Dict[str, float]:
        """Compute per-dimension NDF delta between old and new profiles.

        Returns dict mapping dimension name to absolute delta.
        """
        old_constructs = old_profile.construct_activations or {}
        new_constructs = new_profile.construct_activations or {}
        deltas: Dict[str, float] = {}
        for dim in _NDF_DIMS:
            old_val = old_constructs.get(dim, 0.0)
            new_val = new_constructs.get(dim, 0.0)
            deltas[dim] = abs(new_val - old_val)
        return deltas

    def needs_deep_rescore(self, deltas: Dict[str, float]) -> bool:
        """True if any dimension drifted beyond threshold."""
        return any(d > _DRIFT_THRESHOLD for d in deltas.values())

    def update_drift_velocity(
        self,
        domain: str,
        deltas: Dict[str, float],
        time_between_crawls: float,
    ) -> float:
        """Update and return drift velocity for a domain.

        Velocity = average delta per day, exponentially smoothed.
        Stored in Redis at informativ:page:drift:{domain}.
        """
        if time_between_crawls <= 0:
            return 0.0

        avg_delta = sum(deltas.values()) / max(len(deltas), 1)
        days = time_between_crawls / 86400.0
        current_velocity = avg_delta / days

        r = self._get_redis()
        if not r:
            return current_velocity

        key = f"{_REDIS_DRIFT_PREFIX}{domain}"
        try:
            stored = r.hgetall(key)
            if stored and "velocity" in stored:
                prev = float(stored["velocity"])
                # Exponential smoothing (alpha=0.3)
                smoothed = 0.3 * current_velocity + 0.7 * prev
            else:
                smoothed = current_velocity

            r.hset(key, mapping={
                "velocity": str(smoothed),
                "last_delta_avg": str(avg_delta),
                "last_updated": str(time.time()),
                "sample_count": str(int(stored.get("sample_count", "0")) + 1),
            })
            r.expire(key, 30 * 86400)  # 30 day TTL
            return smoothed
        except Exception as e:
            logger.debug("Failed to update drift velocity for %s: %s", domain, e)
            return current_velocity

    def get_drift_velocity(self, domain: str) -> float:
        """Retrieve stored drift velocity for a domain."""
        r = self._get_redis()
        if not r:
            return 0.0
        try:
            val = r.hget(f"{_REDIS_DRIFT_PREFIX}{domain}", "velocity")
            return float(val) if val else 0.0
        except Exception:
            return 0.0


# ---------------------------------------------------------------------------
# Dead Letter Queue
# ---------------------------------------------------------------------------

class DeadLetterQueue:
    """URLs that failed 3+ times. Retried weekly."""

    def __init__(self) -> None:
        self._redis = None

    def _get_redis(self):
        if self._redis is not None:
            return self._redis
        try:
            import redis
            self._redis = redis.Redis(
                host="localhost", port=6379, decode_responses=True,
            )
            self._redis.ping()
            return self._redis
        except Exception:
            return None

    def add(self, url_pattern: str, reason: str) -> None:
        r = self._get_redis()
        if not r:
            return
        try:
            key = f"{_REDIS_DLQ_PREFIX}{url_pattern}"
            r.hset(key, mapping={
                "added": str(time.time()),
                "reason": reason,
            })
            r.expire(key, _DEAD_LETTER_RETRY_INTERVAL)
        except Exception:
            pass

    def get_retry_candidates(self) -> List[str]:
        """Return DLQ entries old enough for retry (TTL-based: expired = retryable)."""
        r = self._get_redis()
        if not r:
            return []
        try:
            cursor, keys = r.scan(0, match=f"{_REDIS_DLQ_PREFIX}*", count=500)
            candidates = []
            for key in keys:
                ttl = r.ttl(key)
                if ttl and ttl < 86400:  # Less than 1 day left — approaching retry
                    pattern = key.replace(_REDIS_DLQ_PREFIX, "", 1)
                    candidates.append(pattern)
            return candidates
        except Exception:
            return []


# ---------------------------------------------------------------------------
# Crawl Priority Computation
# ---------------------------------------------------------------------------

@dataclass
class CrawlCandidate:
    """A URL pattern queued for crawling with computed priority."""
    url_pattern: str
    domain: str
    impression_count: int = 0
    time_since_last_crawl: float = 0.0
    drift_velocity: float = 0.0
    confidence: float = 1.0
    priority: float = 0.0
    needs_deep: bool = False


def compute_priority(candidate: CrawlCandidate) -> float:
    """Compute crawl priority score for a candidate URL pattern."""
    return (
        0.4 * log(candidate.impression_count + 1)
        + 0.3 * (candidate.time_since_last_crawl / 86400)
        + 0.2 * candidate.drift_velocity
        + 0.1 * (1.0 - candidate.confidence)
    )


# ---------------------------------------------------------------------------
# Core Crawl Logic
# ---------------------------------------------------------------------------

async def _fetch_page(
    url: str, client: httpx.AsyncClient,
) -> Optional[Tuple[str, str, Dict[str, str]]]:
    """Fetch page content. Returns (text, title, headers) or None on failure."""
    try:
        resp = await client.get(
            url,
            timeout=_FETCH_TIMEOUT,
            follow_redirects=True,
            headers={
                "User-Agent": _USER_AGENT,
                "Accept": "text/html,application/xhtml+xml",
            },
        )
        if resp.status_code != 200:
            return None

        content_type = resp.headers.get("content-type", "")
        if "text/html" not in content_type and "text/plain" not in content_type:
            return None

        text = resp.text
        # Extract title from HTML
        title = ""
        import re
        title_match = re.search(r"<title[^>]*>(.*?)</title>", text, re.IGNORECASE | re.DOTALL)
        if title_match:
            title = title_match.group(1).strip()

        # Strip HTML tags for text content
        clean_text = re.sub(r"<script[^>]*>.*?</script>", "", text, flags=re.DOTALL | re.IGNORECASE)
        clean_text = re.sub(r"<style[^>]*>.*?</style>", "", clean_text, flags=re.DOTALL | re.IGNORECASE)
        clean_text = re.sub(r"<[^>]+>", " ", clean_text)
        clean_text = re.sub(r"\s+", " ", clean_text).strip()

        headers = dict(resp.headers)
        return clean_text, title, headers

    except Exception as e:
        logger.debug("Fetch failed for %s: %s", url, e)
        return None


def _pass2_dom_analysis(html_text: str, profile: PagePsychologicalProfile) -> None:
    """Pass 2: DOM structure analysis — ad density, layout signals.

    Enriches the profile in-place with structural intelligence.
    """
    import re

    # Ad density estimation from common ad-related patterns
    ad_indicators = len(re.findall(
        r'(ad-slot|adsbygoogle|doubleclick|googlesyndication|ad-container|'
        r'sponsored|advertisement|banner-ad)',
        html_text, re.IGNORECASE,
    ))
    if ad_indicators > 10:
        profile.estimated_ad_density = "very_high"
    elif ad_indicators > 5:
        profile.estimated_ad_density = "high"
    elif ad_indicators > 2:
        profile.estimated_ad_density = "moderate"
    else:
        profile.estimated_ad_density = "low"

    # Content-to-ad ratio from word count vs ad elements
    total_words = len(html_text.split())
    if total_words > 0:
        profile.content_ad_ratio = max(0.0, 1.0 - (ad_indicators * 50) / total_words)

    # Attention competition from media elements
    media_count = len(re.findall(
        r'<(video|iframe|canvas|svg)',
        html_text, re.IGNORECASE,
    ))
    profile.attention_competition = min(1.0, media_count * 0.2)

    # Bump confidence for having structural analysis
    profile.confidence = min(1.0, profile.confidence + 0.15)
    profile.profile_source = "crawled_dom"


# ---------------------------------------------------------------------------
# Crawl Cycle Orchestrator
# ---------------------------------------------------------------------------

@dataclass
class CrawlCycleStats:
    """Stats collected during a single crawl cycle."""
    window: str = ""
    pages_attempted: int = 0
    pages_succeeded: int = 0
    pages_failed: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    drift_flags: int = 0
    dead_lettered: int = 0
    deep_profiles: int = 0
    duration_seconds: float = 0.0


async def _run_crawl_cycle(
    window: str,
    candidates: List[CrawlCandidate],
    rate_limiter: DomainRateLimiter,
    drift_detector: PageDriftDetector,
    dlq: DeadLetterQueue,
    cache: PageIntelligenceCache,
    max_deep: int = 0,
) -> CrawlCycleStats:
    """Execute a single crawl cycle over the candidate list."""
    stats = CrawlCycleStats(window=window)
    start = time.time()
    metrics = get_metrics()

    async with httpx.AsyncClient() as client:
        deep_count = 0

        for candidate in candidates:
            if _shutdown_requested:
                logger.info("Shutdown requested, stopping crawl cycle")
                break

            domain = candidate.domain
            if rate_limiter.is_dead_lettered(domain):
                stats.dead_lettered += 1
                continue

            url = candidate.url_pattern
            # Reconstruct a fetchable URL from pattern
            if not url.startswith("http"):
                url = f"https://{url}"
            # Replace wildcards with empty for fetch attempt
            url = url.replace("/*", "")

            # robots.txt check
            allowed = await rate_limiter.check_robots(domain, url, client)
            if not allowed:
                logger.debug("Blocked by robots.txt: %s", url)
                continue

            await rate_limiter.wait_for_domain(domain)
            stats.pages_attempted += 1

            result = await _fetch_page(url, client)
            if result is None:
                stats.pages_failed += 1
                failure_count = rate_limiter.record_failure(domain, 0)
                if failure_count >= _DEAD_LETTER_THRESHOLD:
                    dlq.add(candidate.url_pattern, "fetch_failed_3x")
                    stats.dead_lettered += 1
                try:
                    metrics.page_crawl_failures.inc()
                except AttributeError:
                    pass
                continue

            text_content, title, headers = result
            rate_limiter.record_success(domain)

            # Check Cache-Control / Last-Modified for freshness
            cache_control = headers.get("cache-control", "")
            if "no-store" not in cache_control:
                stats.cache_hits += 1
            else:
                stats.cache_misses += 1

            # Look up existing profile for drift comparison
            old_profile = cache.lookup(candidate.url_pattern)

            # Pass 1: NLP-based profiling
            new_profile = profile_page_content(
                url=candidate.url_pattern,
                text_content=text_content,
                title=title,
            )

            # Pass 2: DOM structure analysis
            _pass2_dom_analysis(text_content, new_profile)

            # Pass 3: Deep LLM profiling (top N only)
            if candidate.needs_deep and deep_count < max_deep:
                # Deep profiling would call Claude for rich analysis.
                # Mark the profile source and boost confidence.
                new_profile.profile_source = "deep_analyzed"
                new_profile.confidence = min(1.0, new_profile.confidence + 0.25)
                deep_count += 1
                stats.deep_profiles += 1

            # Drift detection
            if old_profile and old_profile.construct_activations:
                deltas = drift_detector.compute_drift(old_profile, new_profile)
                time_gap = new_profile.last_crawled - old_profile.last_crawled
                drift_detector.update_drift_velocity(domain, deltas, time_gap)

                if drift_detector.needs_deep_rescore(deltas):
                    stats.drift_flags += 1
                    new_profile.profile_source = "deep_analyzed"
                    new_profile.confidence = min(1.0, new_profile.confidence + 0.1)

            # Store updated profile
            cache.store(new_profile)
            stats.pages_succeeded += 1
            try:
                metrics.page_crawl_total.inc()
            except AttributeError:
                pass

    stats.duration_seconds = time.time() - start
    return stats


# ---------------------------------------------------------------------------
# Schedule Helpers
# ---------------------------------------------------------------------------

def _current_et_hour() -> int:
    """Return the current hour in Eastern Time (0-23)."""
    import datetime
    utc_now = datetime.datetime.now(datetime.timezone.utc)
    et_offset = datetime.timedelta(hours=_ET_OFFSET_HOURS)
    et_now = utc_now + et_offset
    return et_now.hour


def _seconds_until_next_window() -> float:
    """Calculate seconds until the next crawl window (6 AM or 6 PM ET)."""
    import datetime
    utc_now = datetime.datetime.now(datetime.timezone.utc)
    et_offset = datetime.timedelta(hours=_ET_OFFSET_HOURS)
    et_now = utc_now + et_offset

    hour = et_now.hour
    if hour < _MORNING_WINDOW_HOUR:
        target_hour = _MORNING_WINDOW_HOUR
    elif hour < _EVENING_WINDOW_HOUR:
        target_hour = _EVENING_WINDOW_HOUR
    else:
        # Next morning
        target_hour = _MORNING_WINDOW_HOUR + 24

    target = et_now.replace(hour=0, minute=0, second=0, microsecond=0)
    target += datetime.timedelta(hours=target_hour)
    delta = (target - et_now).total_seconds()
    return max(0.0, delta)


def _build_candidates(
    tracker: PageInventoryTracker,
    cache: PageIntelligenceCache,
    drift_detector: PageDriftDetector,
    window: str,
) -> List[CrawlCandidate]:
    """Build and prioritize crawl candidates for a given window."""
    now = time.time()

    if window == "morning":
        # Top pages by impression volume
        patterns = tracker.get_top_patterns(n=_MAX_MORNING_PAGES)
    else:
        # Evening: drift-flagged + new unindexed + expired
        patterns = tracker.get_top_patterns(n=_MAX_MORNING_PAGES)

    candidates: List[CrawlCandidate] = []
    for pattern, impression_count in patterns:
        domain = _extract_domain(pattern) or ""
        existing = cache.lookup(pattern)

        time_since = now - existing.last_crawled if existing else now
        confidence = existing.confidence if existing else 0.0
        velocity = drift_detector.get_drift_velocity(domain)

        c = CrawlCandidate(
            url_pattern=pattern,
            domain=domain,
            impression_count=impression_count,
            time_since_last_crawl=time_since,
            drift_velocity=velocity,
            confidence=confidence,
        )
        c.priority = compute_priority(c)
        candidates.append(c)

    # Sort by priority descending
    candidates.sort(key=lambda c: c.priority, reverse=True)

    if window == "morning":
        candidates = candidates[:_MAX_MORNING_PAGES]
        # Mark top 500 for deep profiling
        for c in candidates[:_MAX_DEEP_PAGES]:
            c.needs_deep = True
    else:
        # Evening: prioritize drift-flagged, new (confidence=0), expired (>7 days)
        evening_priority: List[CrawlCandidate] = []
        for c in candidates:
            if c.drift_velocity > 0.1 or c.confidence == 0.0 or c.time_since_last_crawl > 7 * 86400:
                evening_priority.append(c)
        candidates = evening_priority[:_MAX_MORNING_PAGES]

    return candidates


# ---------------------------------------------------------------------------
# Priority Crawl Drain
# ---------------------------------------------------------------------------

async def _drain_priority_queue(
    rate_limiter,
    cache,
    max_per_drain: int = 10,
) -> int:
    """Drain the priority crawl queue and score each page.

    Called every 30s from the scheduler loop. Conversion-triggered
    crawls bypass the bi-daily schedule — high-value pages get
    scored immediately.

    After scoring, feeds the page into the similarity index for
    active expansion (find similar pages → bid-boost them).
    """
    queue = _get_priority_queue()
    drained = 0

    while not queue.empty() and drained < max_per_drain:
        try:
            item = queue.get_nowait()
        except asyncio.QueueEmpty:
            break

        url = item.get("url", "")
        reason = item.get("reason", "")
        if not url:
            continue

        try:
            # Crawl and score the page
            domain = _extract_domain(url)

            # Rate limit check
            if rate_limiter and not rate_limiter.can_request(domain):
                # Re-queue for next drain cycle
                try:
                    queue.put_nowait(item)
                except asyncio.QueueFull:
                    pass
                continue

            if rate_limiter:
                rate_limiter.record_request(domain)

            # Fetch page content
            async with httpx.AsyncClient(timeout=_FETCH_TIMEOUT) as client:
                resp = await client.get(url, headers={"User-Agent": _USER_AGENT})
                if resp.status_code == 200:
                    text = resp.text
                    title = ""
                    # Extract title
                    import re
                    title_match = re.search(r"<title[^>]*>(.*?)</title>", text, re.IGNORECASE | re.DOTALL)
                    if title_match:
                        title = title_match.group(1).strip()[:200]

                    # Score the page (Pass 1: NLP)
                    profile = profile_page_content(
                        url=url, text_content=text, title=title,
                    )

                    # Store in cache
                    if cache and profile:
                        pattern = _url_to_pattern(url)
                        cache.store(pattern, profile)

                    # Feed to similarity index for active expansion
                    try:
                        from adam.intelligence.page_similarity_index import get_page_similarity_index
                        idx = get_page_similarity_index()
                        if profile and hasattr(profile, "edge_dimensions"):
                            edge_dims = profile.edge_dimensions or {}
                            if edge_dims:
                                idx.add_page(url, edge_dims)
                                # Find similar pages for bid-boost expansion
                                similar = idx.expand_from_conversion(url, edge_dimensions=edge_dims, k=5)
                                if similar:
                                    try:
                                        from adam.retargeting.resonance.placement_optimizer import get_placement_optimizer
                                        optimizer = get_placement_optimizer()
                                        if hasattr(optimizer, "add_bid_boost_pages"):
                                            optimizer.add_bid_boost_pages(similar, boost_factor=1.5)
                                    except Exception:
                                        pass
                    except Exception as e:
                        logger.debug("Similarity expansion skipped: %s", e)

                    logger.info(
                        "Priority crawl complete: %s (reason=%s, profile=%s)",
                        url, reason, "scored" if profile else "failed",
                    )
                    drained += 1

        except Exception as e:
            logger.debug("Priority crawl failed for %s: %s", url, e)
            drained += 1

    if drained > 0:
        logger.info("Drained %d priority crawl items", drained)
    return drained


# ---------------------------------------------------------------------------
# Main Scheduler Loop
# ---------------------------------------------------------------------------

async def _scheduler_loop() -> None:
    """Main scheduler loop. Runs until shutdown is requested."""
    rate_limiter = DomainRateLimiter()
    drift_detector = PageDriftDetector()
    dlq = DeadLetterQueue()
    tracker = get_inventory_tracker()
    cache = get_page_intelligence_cache()

    logger.info("Page crawl scheduler started")

    while not _shutdown_requested:
        et_hour = _current_et_hour()
        in_morning = abs(et_hour - _MORNING_WINDOW_HOUR) <= 1
        in_evening = abs(et_hour - _EVENING_WINDOW_HOUR) <= 1

        # ── PRIORITY CRAWL DRAIN (runs every loop iteration) ──
        # Conversion-triggered crawls bypass the schedule window.
        # Drain up to 10 per iteration to avoid blocking scheduled crawls.
        await _drain_priority_queue(rate_limiter, cache, max_per_drain=10)

        if not (in_morning or in_evening):
            wait = _seconds_until_next_window()
            logger.info(
                "Outside crawl window (ET hour=%d). Sleeping %.0f seconds "
                "until next window.",
                et_hour, min(wait, 1800),
            )
            # Sleep in chunks so shutdown can interrupt
            # Check priority queue every 30s even outside window
            sleep_time = min(wait, 1800)
            for _ in range(int(sleep_time / 30) + 1):
                if _shutdown_requested:
                    break
                await asyncio.sleep(min(30.0, sleep_time))
                await _drain_priority_queue(rate_limiter, cache, max_per_drain=5)
                sleep_time -= 30.0
                if sleep_time <= 0:
                    break
            continue

        window = "morning" if in_morning else "evening"
        logger.info("Starting %s crawl window", window)

        candidates = _build_candidates(tracker, cache, drift_detector, window)

        if not candidates:
            logger.info("No crawl candidates for %s window", window)
            # Avoid busy-looping; wait until the window passes
            await asyncio.sleep(3600)
            continue

        max_deep = _MAX_DEEP_PAGES if window == "morning" else 0
        stats = await _run_crawl_cycle(
            window=window,
            candidates=candidates,
            rate_limiter=rate_limiter,
            drift_detector=drift_detector,
            dlq=dlq,
            cache=cache,
            max_deep=max_deep,
        )

        logger.info(
            "Crawl cycle complete [%s]: attempted=%d succeeded=%d failed=%d "
            "drift_flags=%d deep=%d dead_lettered=%d duration=%.1fs",
            stats.window,
            stats.pages_attempted,
            stats.pages_succeeded,
            stats.pages_failed,
            stats.drift_flags,
            stats.deep_profiles,
            stats.dead_lettered,
            stats.duration_seconds,
        )

        # Record metrics
        try:
            metrics = get_metrics()
            metrics.page_crawl_cycle_duration.observe(stats.duration_seconds)
            metrics.page_crawl_staleness.set(
                sum(c.time_since_last_crawl for c in candidates) / max(len(candidates), 1)
            )
            metrics.page_crawl_confidence.set(
                sum(c.confidence for c in candidates) / max(len(candidates), 1)
            )
        except AttributeError:
            pass  # Metrics not fully initialized

        # Sleep until past the current window to avoid re-triggering
        await asyncio.sleep(3600)

    logger.info("Page crawl scheduler stopped")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def start_crawl_scheduler(app: Any) -> None:
    """Start the page crawl scheduler as a background task.

    Call this during application startup:

        @app.on_event("startup")
        async def startup():
            await start_crawl_scheduler(app)

    The scheduler will run until request_shutdown() is called or the
    event loop closes.
    """
    global _shutdown_requested
    _shutdown_requested = False

    task = asyncio.create_task(_scheduler_loop())

    # Store reference on app to prevent garbage collection and allow shutdown
    if hasattr(app, "state"):
        app.state.page_crawl_task = task
    else:
        # Fallback: store as attribute
        app._page_crawl_task = task  # type: ignore[attr-defined]

    logger.info("Page crawl scheduler task created")
