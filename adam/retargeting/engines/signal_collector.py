# =============================================================================
# Nonconscious Signal Collector
# Location: adam/retargeting/engines/signal_collector.py
# Enhancement #34: Nonconscious Signal Intelligence Layer, Session 1
# =============================================================================

"""
Receives site telemetry payloads and accumulates per-user nonconscious
signal profiles in Redis.

This is the data collection layer — it does NOT compute signals (that's
Sessions 2-4). It:
  1. Validates and deduplicates incoming telemetry sessions
  2. Classifies referral type (ad-attributed vs organic)
  3. Extracts section engagements, click latency, device info
  4. Accumulates into StoredSignalProfile (Redis, 90-day TTL)
  5. Updates population baselines (organic ratio, CTR)

The signal computation engines (ProcessingDepthClassifier, ClickLatencyTracker,
BarrierSelfReportExtractor, OrganicReturnTracker, DeviceEngagementTracker,
FrequencyDecayDetector) consume StoredSignalProfile downstream.
"""

import json
import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import redis.asyncio as redis

from adam.infrastructure.redis.cache import (
    ADAMRedisCache,
    CacheDomain,
    CacheKeyBuilder,
    DOMAIN_TTLS,
)
from adam.retargeting.models.telemetry import (
    ReferralType,
    StoredSignalProfile,
    TelemetrySessionPayload,
)

logger = logging.getLogger(__name__)


# Session dedup TTL — reject duplicate session_ids within this window
_SESSION_DEDUP_TTL = 3600  # 1 hour


class NonconsciousSignalCollector:
    """Ingests site telemetry and maintains per-user signal profiles.

    Thread-safe via Redis atomic operations. Designed for concurrent
    telemetry ingestion from multiple site visitors.
    """

    def __init__(self, redis_client: redis.Redis):
        self._redis = redis_client
        self._cache = ADAMRedisCache(redis_client)
        self._profile_ttl = DOMAIN_TTLS[CacheDomain.NONCONSCIOUS]

    async def ingest_session(
        self, payload: TelemetrySessionPayload
    ) -> Dict[str, Any]:
        """Process a telemetry session payload.

        Returns a summary dict with what was updated.
        Idempotent: duplicate session_ids are rejected.
        """
        # 1. Dedup check
        dedup_key = CacheKeyBuilder.nonconscious_session(payload.session_id)
        already_seen = await self._redis.set(
            dedup_key, "1", nx=True, ex=_SESSION_DEDUP_TTL
        )
        if not already_seen:
            logger.debug("Duplicate session %s, skipping", payload.session_id)
            return {"status": "duplicate", "session_id": payload.session_id}

        # 2. Load or create user profile
        profile = await self._load_profile(payload.visitor_id)

        # 3. Accumulate session data into profile
        self._accumulate_visit(profile, payload)
        self._accumulate_sections(profile, payload)
        self._accumulate_click_latency(profile, payload)
        self._accumulate_device(profile, payload)
        self._accumulate_engagement_hour(profile, payload)

        # 4. Compute derived signals from accumulated data
        self._compute_click_latency_trajectory(profile, payload)
        self._compute_barrier_self_report(profile, payload)
        pop_organic = await self.get_population_organic_ratio()
        self._compute_organic_return(profile, pop_organic)
        self._compute_frequency_decay(profile)

        profile.last_updated = time.time()

        # 5. Persist updated profile
        await self._save_profile(profile)

        # 6. Update population baselines
        await self._update_population_baselines(payload)

        logger.info(
            "Ingested session %s for user %s (sessions=%d, organic_ratio=%.2f, "
            "trajectory=%s, barrier=%s)",
            payload.session_id,
            payload.visitor_id,
            profile.total_sessions,
            profile.organic_ratio,
            profile.click_latency_trajectory or "none",
            profile.self_reported_barrier or "none",
        )

        return {
            "status": "ingested",
            "session_id": payload.session_id,
            "visitor_id": payload.visitor_id,
            "total_sessions": profile.total_sessions,
            "is_organic": payload.is_organic,
            "sections_recorded": len(payload.section_engagements),
            "pages_visited": len(payload.pages_visited),
            "click_latency_trajectory": profile.click_latency_trajectory,
            "self_reported_barrier": profile.self_reported_barrier,
        }

    async def get_profile(self, user_id: str) -> Optional[StoredSignalProfile]:
        """Retrieve a user's accumulated signal profile."""
        return await self._load_profile(user_id)

    async def get_population_organic_ratio(self) -> float:
        """Get the current population-level organic visit ratio."""
        key = CacheKeyBuilder.nonconscious_population("organic_ratio")
        val = await self._redis.get(key)
        return float(val) if val else 0.15  # default starting estimate

    async def get_population_ctr(self) -> float:
        """Get the current population-level CTR."""
        key = CacheKeyBuilder.nonconscious_population("ctr")
        val = await self._redis.get(key)
        return float(val) if val else 0.02  # default starting estimate

    # ─── Profile persistence ─────────────────────────────────────────

    async def _load_profile(self, user_id: str) -> StoredSignalProfile:
        """Load profile from Redis or create a new one."""
        key = CacheKeyBuilder.nonconscious_profile(user_id)
        raw = await self._redis.get(key)
        if raw:
            try:
                return StoredSignalProfile.model_validate_json(raw)
            except Exception:
                logger.warning("Corrupt profile for %s, creating fresh", user_id)
        return StoredSignalProfile(user_id=user_id)

    async def _save_profile(self, profile: StoredSignalProfile) -> None:
        """Persist profile to Redis with 90-day TTL."""
        key = CacheKeyBuilder.nonconscious_profile(profile.user_id)
        await self._redis.set(
            key,
            profile.model_dump_json(),
            ex=self._profile_ttl,
        )

    # ─── Accumulation methods ────────────────────────────────────────

    def _accumulate_visit(
        self, profile: StoredSignalProfile, payload: TelemetrySessionPayload
    ) -> None:
        """Update visit counts and organic/ad-attributed classification."""
        profile.total_sessions += 1
        profile.total_page_views += max(1, len(payload.pages_visited))

        if payload.is_organic:
            profile.organic_sessions += 1
        else:
            profile.ad_attributed_sessions += 1

        # Track visit timestamps and organic flags for Signal 3
        profile.visit_timestamps.append(payload.arrival_timestamp)
        profile.visit_is_organic.append(payload.is_organic)

    def _accumulate_sections(
        self, profile: StoredSignalProfile, payload: TelemetrySessionPayload
    ) -> None:
        """Accumulate section-level dwell and interaction data."""
        for se in payload.section_engagements:
            sid = se.section_id
            profile.section_dwell_totals[sid] = (
                profile.section_dwell_totals.get(sid, 0.0) + se.dwell_seconds
            )
            profile.section_interaction_totals[sid] = (
                profile.section_interaction_totals.get(sid, 0) + se.interactions
            )

    def _accumulate_click_latency(
        self, profile: StoredSignalProfile, payload: TelemetrySessionPayload
    ) -> None:
        """Extract click latency if this was an ad-click arrival.

        Click latency = time from ad impression to page arrival.
        Only available when sapid is present (ad-attributed click).

        The impression timestamp comes from the StackAdapt {TIMESTAMP} macro
        appended to the click URL as &ts={TIMESTAMP}. The telemetry JS
        parses it and includes it in first_interaction_timestamp or we
        compute it from arrival_timestamp.
        """
        if not payload.is_ad_attributed:
            return

        # When the StackAdapt {TIMESTAMP} macro is available, compute
        # latency as arrival_timestamp - impression_timestamp.
        # The impression_ts is not directly in the payload yet (it arrives
        # via the ts= URL param which the JS stores in the payload).
        # For now, use first_interaction_timestamp - arrival_timestamp
        # as a proxy for engagement latency on the landing page.
        # This will be refined when StackAdapt impression reports are
        # joined by sapid in a later enrichment step.
        if payload.first_interaction_timestamp and payload.arrival_timestamp:
            latency = payload.first_interaction_timestamp - payload.arrival_timestamp
            if 0 < latency < 120:  # Sanity bound: 0-120 seconds
                profile.click_latencies.append(round(latency, 3))

    def _accumulate_device(
        self, profile: StoredSignalProfile, payload: TelemetrySessionPayload
    ) -> None:
        """Track device-type engagement for Signal 5."""
        device = payload.device_type.value
        profile.device_impressions[device] = (
            profile.device_impressions.get(device, 0) + 1
        )
        # Clicks are tracked at outcome time (not session ingest), but we
        # count sessions as "impressions" for the device engagement model.

    def _accumulate_engagement_hour(
        self, profile: StoredSignalProfile, payload: TelemetrySessionPayload
    ) -> None:
        """Track hour-of-day engagement for per-individual receptive windows."""
        hour = datetime.fromtimestamp(
            payload.arrival_timestamp, tz=timezone.utc
        ).hour
        profile.hour_engagement_counts[hour] = (
            profile.hour_engagement_counts.get(hour, 0) + 1
        )

    # ─── Derived signal computation ────────────────────────────────────

    def _compute_click_latency_trajectory(
        self, profile: StoredSignalProfile, payload: TelemetrySessionPayload
    ) -> None:
        """Recompute click latency trajectory from accumulated latencies.

        Called after every session ingest. Updates trajectory_type, slope,
        and latest_conflict_class on the profile.
        """
        if not profile.click_latencies:
            return

        from adam.retargeting.engines.click_latency import (
            ClickLatencyTracker,
        )
        tracker = ClickLatencyTracker()

        # Compute trajectory
        traj = tracker.compute_trajectory(profile.click_latencies)
        profile.click_latency_trajectory = traj["trajectory_type"]
        profile.click_latency_slope = traj["slope"]

        # Classify latest click conflict
        device = payload.device_type.value if payload.device_type else "desktop"
        latest = profile.click_latencies[-1]
        conflict = tracker.classify_conflict(latest, device)
        profile.latest_conflict_class = conflict.value

    def _compute_barrier_self_report(
        self, profile: StoredSignalProfile, payload: TelemetrySessionPayload
    ) -> None:
        """Compute barrier self-report from cumulative section engagement.

        Uses the CUMULATIVE section engagement across all sessions (not just
        the current one) to build a more stable barrier diagnosis. Each new
        session updates the running totals, and we re-extract the barrier.
        """
        if not profile.section_dwell_totals:
            return

        from adam.retargeting.engines.barrier_self_report import (
            BarrierSelfReportExtractor,
            SECTION_BARRIER_MAP,
        )
        from adam.retargeting.models.telemetry import SectionEngagement

        # Build synthetic SectionEngagement list from cumulative profile data
        cumulative_engagements = []
        for sid, dwell in profile.section_dwell_totals.items():
            if sid in SECTION_BARRIER_MAP:
                cumulative_engagements.append(SectionEngagement(
                    section_id=sid,
                    dwell_seconds=dwell,
                    interactions=profile.section_interaction_totals.get(sid, 0),
                ))

        if not cumulative_engagements:
            return

        extractor = BarrierSelfReportExtractor()
        result = extractor.extract_barrier(
            section_engagements=cumulative_engagements,
            total_session_seconds=0.0,  # cumulative, not per-session
            bounced=False,
        )

        if result:
            profile.self_reported_barrier = result["self_reported_barrier"]
            profile.barrier_self_report_confidence = result["confidence"]
            profile.barrier_dimensions_to_target = result.get("dimensions_to_target", [])

    def _compute_organic_return(
        self, profile: StoredSignalProfile, population_organic_ratio: float
    ) -> None:
        """Compute organic return stage signal (Signal 3).

        Compares individual organic ratio to population baseline.
        Surge detection triggers INTENDING stage classification.
        """
        if len(profile.visit_is_organic) < 2:
            return

        from adam.retargeting.engines.organic_return import OrganicReturnTracker
        tracker = OrganicReturnTracker()

        result = tracker.get_stage_signal(
            visit_is_organic=profile.visit_is_organic,
            population_organic_ratio=population_organic_ratio,
        )
        if result:
            profile.organic_stage = result["stage"]
            profile.organic_surge_multiplier = result["surge_multiplier"]
            profile.organic_mechanism_recommendation = result["mechanism_recommendation"]

    def _compute_frequency_decay(
        self, profile: StoredSignalProfile,
    ) -> None:
        """Compute frequency decay / reactance signal (Signal 6).

        Compares recent engagement window to historical engagement.
        Flags reactance onset when recent engagement drops significantly.
        """
        if len(profile.touch_outcomes) < 4:
            return

        from adam.retargeting.engines.frequency_decay import FrequencyDecayDetector
        detector = FrequencyDecayDetector()

        result = detector.detect_reactance(
            touch_outcomes=profile.touch_outcomes,
        )
        if result:
            profile.reactance_detected = result["reactance_detected"]
            profile.reactance_onset_touch = result["reactance_onset_touch"]
            profile.reactance_h4_modifier = result["h4_modifier"]

    # ─── Population baselines ────────────────────────────────────────

    async def _update_population_baselines(
        self, payload: TelemetrySessionPayload
    ) -> None:
        """Update population-level baselines using exponential moving average.

        These baselines are used by Signal 3 (organic return surge detection)
        and Signal 6 (frequency decay / population CTR).
        """
        # Organic ratio EMA
        organic_key = CacheKeyBuilder.nonconscious_population("organic_ratio")
        count_key = CacheKeyBuilder.nonconscious_population("total_sessions")

        total = await self._redis.incr(count_key)
        alpha = min(0.01, 2.0 / (total + 1))

        current_ratio = float(await self._redis.get(organic_key) or 0.15)
        new_ratio = (1 - alpha) * current_ratio + alpha * float(payload.is_organic)
        await self._redis.set(organic_key, str(new_ratio))
