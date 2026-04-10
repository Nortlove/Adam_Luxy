# =============================================================================
# Temporal Dynamics — DDM Timing + Burstiness Detection
# Location: adam/retargeting/engines/temporal_dynamics.py
# Enhancement #34, Session 34-5 + Addendum B Category 4
# =============================================================================

"""
Temporal dynamics engine for retargeting timing optimization.

Two components:

1. DDM TIMING CAPTURE: Extracts time-to-click, dwell duration, and
   inter-event intervals from behavioral signals. These become features
   for drift-diffusion model parameter estimation (future) and immediate
   inputs to barrier diagnosis (response latency = reactance proxy).

2. BURSTINESS DETECTION: Fits the burstiness parameter B to per-user
   inter-event times. Human behavior follows power-law temporal patterns
   (Barabási, Nature 2005). The optimal time to deliver a retargeting
   touch is during an activity burst, not at fixed intervals.

   B = (σ - μ)/(σ + μ) where σ, μ are std and mean of inter-event times.
   B = 0: Poisson (regular timing) — fixed intervals are fine.
   B > 0.3: Bursty — fixed intervals miss opportunities and waste budget.

Integration: BurstAwareTimingController replaces fixed min_hours_between
in SuppressionController when burstiness is detected.
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class TimingFeatures:
    """Timing features extracted from behavioral events.

    These feed into:
    - Barrier diagnostic (response latency as reactance proxy)
    - DDM parameter estimation (future)
    - Burstiness detection
    """

    user_id: str

    # Per-event timing
    time_to_first_click_seconds: Optional[float] = None
    median_dwell_seconds: Optional[float] = None
    mean_inter_event_hours: Optional[float] = None
    std_inter_event_hours: Optional[float] = None

    # Burstiness
    burstiness_parameter: float = 0.0  # B ∈ [-1, 1], >0.3 = bursty
    is_bursty: bool = False
    current_burst_score: float = 0.0  # 0 = quiescent, 1 = peak burst

    # DDM proxies (before full HDDM estimation)
    estimated_drift_rate: Optional[float] = None  # From click latency patterns
    estimated_boundary: Optional[float] = None  # From decision time variance

    # Event count
    n_events: int = 0


@dataclass
class BurstState:
    """Per-user burst tracking state."""

    user_id: str
    event_timestamps: List[float] = field(default_factory=list)
    burstiness: float = 0.0
    last_burst_score: float = 0.0
    max_events: int = 100  # Keep last N events for memory efficiency


class TimingFeatureExtractor:
    """Extracts timing features from behavioral event streams.

    Called at two points:
    1. Webhook processing: when new event arrives, extract timing
    2. Touch decision: compute current burst state for delivery timing
    """

    def extract(
        self,
        events: List[Dict],
        user_id: str = "",
    ) -> TimingFeatures:
        """Extract timing features from event list.

        Args:
            events: List of {timestamp: float, event_type: str, ...} dicts
            user_id: For tracking

        Returns:
            TimingFeatures with all computed metrics
        """
        features = TimingFeatures(user_id=user_id, n_events=len(events))

        if len(events) < 2:
            return features

        timestamps = sorted(e.get("timestamp", 0) for e in events)

        # Inter-event intervals (hours)
        intervals_h = [
            (timestamps[i + 1] - timestamps[i]) / 3600.0
            for i in range(len(timestamps) - 1)
            if timestamps[i + 1] > timestamps[i]
        ]

        if intervals_h:
            features.mean_inter_event_hours = float(np.mean(intervals_h))
            features.std_inter_event_hours = float(np.std(intervals_h))

            # Burstiness parameter: B = (σ - μ) / (σ + μ)
            mu = features.mean_inter_event_hours
            sigma = features.std_inter_event_hours
            if mu + sigma > 0:
                features.burstiness_parameter = round(
                    (sigma - mu) / (sigma + mu), 4
                )
                features.is_bursty = features.burstiness_parameter > 0.3

        # Time-to-first-click
        click_events = [
            e for e in events if e.get("event_type") in ("click", "ad_click")
        ]
        if click_events and len(events) >= 2:
            first_event_ts = timestamps[0]
            first_click_ts = min(e.get("timestamp", 0) for e in click_events)
            if first_click_ts > first_event_ts:
                features.time_to_first_click_seconds = first_click_ts - first_event_ts

        # Median dwell (if dwell data available)
        dwells = [
            e.get("dwell_seconds", 0)
            for e in events
            if e.get("dwell_seconds", 0) > 0
        ]
        if dwells:
            features.median_dwell_seconds = float(np.median(dwells))

        # DDM drift rate proxy: inverse of median response time
        # (faster responses → higher drift rate → more evidence per unit time)
        if features.time_to_first_click_seconds and features.time_to_first_click_seconds > 0:
            features.estimated_drift_rate = round(
                1.0 / features.time_to_first_click_seconds, 4
            )

        # DDM boundary proxy: std of response times
        # (higher variance → wider boundary → more cautious decision maker)
        click_times = [
            e.get("timestamp", 0) for e in click_events
        ]
        if len(click_times) >= 3:
            click_intervals = [
                click_times[i + 1] - click_times[i]
                for i in range(len(click_times) - 1)
                if click_times[i + 1] > click_times[i]
            ]
            if click_intervals:
                features.estimated_boundary = round(float(np.std(click_intervals)), 4)

        return features


class BurstAwareTimingController:
    """Delivers retargeting touches synchronized with buyer activity bursts.

    Replaces fixed min_hours_between in SuppressionController when the
    buyer is detected as bursty (B > 0.3).

    During bursts: RELAX minimum interval (buyer is actively engaged,
    reactance per touch is lower because attention is focused).

    During quiescence: EXTEND interval (touch will land on deaf ears,
    only accumulates reactance).

    The burst score is an exponentially-weighted event density:
    burst_score = Σ exp(-age_hours / half_life) for recent events.
    """

    def __init__(
        self,
        decay_halflife_hours: float = 4.0,
        burst_threshold: float = 1.5,
        burst_min_hours: int = 4,   # Relaxed minimum during bursts
        quiet_min_hours: int = 48,  # Extended minimum during quiescence
        default_min_hours: int = 24,  # Standard (non-bursty users)
    ):
        self.halflife = decay_halflife_hours
        self.threshold = burst_threshold
        self.burst_min = burst_min_hours
        self.quiet_min = quiet_min_hours
        self.default_min = default_min_hours

        # Per-user state
        self._user_states: Dict[str, BurstState] = {}

    def record_event(self, user_id: str, timestamp: Optional[float] = None) -> None:
        """Record a behavioral event for burst tracking."""
        ts = timestamp or time.time()
        state = self._user_states.get(user_id)
        if state is None:
            state = BurstState(user_id=user_id)
            self._user_states[user_id] = state

        state.event_timestamps.append(ts)
        # Trim to max_events
        if len(state.event_timestamps) > state.max_events:
            state.event_timestamps = state.event_timestamps[-state.max_events:]

    def get_recommended_interval(
        self,
        user_id: str,
        reactance_budget: float = 1.0,
    ) -> Tuple[int, str, float]:
        """Get recommended minimum hours before next touch.

        Returns:
            (min_hours, reason, burst_score)
        """
        if reactance_budget <= 0.1:
            return self.quiet_min, "reactance_exhausted", 0.0

        state = self._user_states.get(user_id)
        if state is None or len(state.event_timestamps) < 3:
            return self.default_min, "insufficient_history", 0.0

        # Compute burst score
        now = time.time()
        burst_score = self._compute_burst_score(state.event_timestamps, now)
        state.last_burst_score = burst_score

        # Compute burstiness parameter
        intervals = [
            state.event_timestamps[i + 1] - state.event_timestamps[i]
            for i in range(len(state.event_timestamps) - 1)
            if state.event_timestamps[i + 1] > state.event_timestamps[i]
        ]
        if intervals:
            mu = np.mean(intervals)
            sigma = np.std(intervals)
            state.burstiness = (sigma - mu) / (sigma + mu) if (sigma + mu) > 0 else 0

        # Non-bursty user: use default timing
        if state.burstiness < 0.3:
            return self.default_min, "poisson_timing", burst_score

        # Bursty user: adapt to burst state
        if burst_score > self.threshold:
            return self.burst_min, "in_burst", burst_score
        else:
            return self.quiet_min, "quiescent", burst_score

    def should_deliver_now(
        self,
        user_id: str,
        hours_since_last_touch: float,
        reactance_budget: float = 1.0,
    ) -> Tuple[bool, str]:
        """Quick check: should we deliver a touch right now?

        Returns (should_deliver, reason)
        """
        min_hours, reason, burst_score = self.get_recommended_interval(
            user_id, reactance_budget
        )

        if hours_since_last_touch < min_hours:
            return False, f"too_soon ({hours_since_last_touch:.1f}h < {min_hours}h, {reason})"

        return True, f"ready ({reason}, burst={burst_score:.2f})"

    def _compute_burst_score(
        self, timestamps: List[float], now: float
    ) -> float:
        """Exponentially-weighted event density."""
        score = 0.0
        for ts in timestamps:
            age_hours = (now - ts) / 3600.0
            if age_hours >= 0:
                score += np.exp(-age_hours / self.halflife)
        return round(score, 4)

    @property
    def stats(self) -> Dict:
        """Monitoring stats."""
        bursty = sum(1 for s in self._user_states.values() if s.burstiness > 0.3)
        return {
            "tracked_users": len(self._user_states),
            "bursty_users": bursty,
            "bursty_pct": round(bursty / max(len(self._user_states), 1), 3),
        }
