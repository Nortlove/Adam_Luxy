# =============================================================================
# Therapeutic Retargeting Engine — Behavioral Signal Processors
# Location: adam/retargeting/engines/signal_processors.py
# =============================================================================

"""
Behavioral signal preprocessing for stage classification and barrier diagnosis.

Normalizes raw behavioral signals from different sources (StackAdapt pixels,
site analytics, CRM events) into a unified feature set for the stage
classifier and barrier diagnostic engine.

This is a PLATFORM SERVICE — used by both first-touch (bilateral cascade)
and retargeting paths.
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Signal types that the system can ingest
# ---------------------------------------------------------------------------
SIGNAL_TYPES = {
    # Awareness signals
    "ad_impression": {"stage_weight": 0.05, "ownership_gain": 0.0},
    "ad_dwell_2s": {"stage_weight": 0.10, "ownership_gain": 0.02},
    "ad_click": {"stage_weight": 0.20, "ownership_gain": 0.05},

    # Consideration signals
    "site_visit": {"stage_weight": 0.15, "ownership_gain": 0.05},
    "page_view": {"stage_weight": 0.10, "ownership_gain": 0.03},
    "pricing_page": {"stage_weight": 0.25, "ownership_gain": 0.08},
    "review_page": {"stage_weight": 0.18, "ownership_gain": 0.06},
    "comparison_page": {"stage_weight": 0.20, "ownership_gain": 0.07},
    "competitor_visit": {"stage_weight": 0.15, "ownership_gain": 0.0},

    # Intent signals
    "email_signup": {"stage_weight": 0.30, "ownership_gain": 0.10},
    "cart_add": {"stage_weight": 0.35, "ownership_gain": 0.15},
    "booking_start": {"stage_weight": 0.40, "ownership_gain": 0.20},
    "configurator_use": {"stage_weight": 0.35, "ownership_gain": 0.18},

    # Stall signals
    "cart_abandon": {"stage_weight": -0.10, "ownership_gain": -0.05},
    "booking_abandon": {"stage_weight": -0.15, "ownership_gain": -0.05},

    # Conversion signals
    "purchase": {"stage_weight": 1.00, "ownership_gain": 1.0},
    "booking_complete": {"stage_weight": 1.00, "ownership_gain": 1.0},

    # Negative signals (rupture indicators)
    "unsubscribe": {"stage_weight": -0.50, "ownership_gain": -0.30},
    "complaint": {"stage_weight": -0.60, "ownership_gain": -0.40},
    "ad_hide": {"stage_weight": -0.20, "ownership_gain": -0.10},
}


@dataclass
class BehavioralSignal:
    """A single behavioral observation from any source."""

    signal_type: str
    timestamp: float = field(default_factory=time.time)
    source: str = ""  # "stackadapt_pixel", "site_analytics", "crm", etc.
    value: float = 1.0  # Signal intensity (default 1.0 for binary events)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProcessedSignalSet:
    """Unified feature set derived from raw behavioral signals.

    This is the input to both ConversionStageClassifier and
    ConversionBarrierDiagnosticEngine.
    """

    user_id: str
    brand_id: str

    # Engagement metrics
    total_impressions: int = 0
    total_clicks: int = 0
    total_site_visits: int = 0
    total_page_views: int = 0
    total_dwell_minutes: float = 0.0

    # Funnel progression
    pricing_page_visits: int = 0
    review_page_visits: int = 0
    comparison_page_visits: int = 0
    competitor_visits: int = 0
    email_signups: int = 0
    cart_additions: int = 0
    booking_starts: int = 0
    booking_completions: int = 0

    # Abandonment
    cart_abandons: int = 0
    booking_abandons: int = 0

    # Negative signals
    unsubscribes: int = 0
    complaints: int = 0
    ad_hides: int = 0

    # Temporal features
    hours_since_first_interaction: float = 0.0
    hours_since_last_interaction: float = 0.0
    hours_since_last_site_visit: float = 0.0
    interaction_frequency_per_day: float = 0.0
    days_active: int = 0

    # Engagement velocity (rate of change over last 3 interactions)
    engagement_velocity: float = 0.0  # positive = accelerating, negative = decaying
    engagement_velocity_trend: str = "stable"  # accelerating, stable, decaying

    # Ownership proxy
    booking_steps_completed: int = 0
    pages_viewed: int = 0

    # Computed stage score (weighted sum of signals)
    stage_score: float = 0.0

    # Raw signals (for engines that need full detail)
    raw_signals: List[BehavioralSignal] = field(default_factory=list)


class BehavioralSignalProcessor:
    """Processes raw behavioral signals into a unified feature set.

    Callable from:
    - Bilateral cascade (first-touch): processes buyer_id history
    - Retargeting engine: processes touch sequence + buyer history
    - Webhook handler: processes new conversion/engagement event
    """

    def process(
        self,
        user_id: str,
        brand_id: str,
        signals: List[BehavioralSignal],
    ) -> ProcessedSignalSet:
        """Transform raw signals into unified features.

        Args:
            user_id: The user being analyzed
            brand_id: The brand context
            signals: Raw behavioral signals, sorted by timestamp

        Returns:
            ProcessedSignalSet with all computed features
        """
        if not signals:
            return ProcessedSignalSet(user_id=user_id, brand_id=brand_id)

        result = ProcessedSignalSet(
            user_id=user_id,
            brand_id=brand_id,
            raw_signals=signals,
        )

        now = time.time()
        timestamps = []

        for sig in signals:
            timestamps.append(sig.timestamp)
            stype = sig.signal_type

            # Count by type
            if stype == "ad_impression":
                result.total_impressions += 1
            elif stype == "ad_click":
                result.total_clicks += 1
            elif stype == "site_visit":
                result.total_site_visits += 1
            elif stype == "page_view":
                result.total_page_views += 1
                result.pages_viewed += 1
            elif stype == "pricing_page":
                result.pricing_page_visits += 1
                result.pages_viewed += 1
            elif stype == "review_page":
                result.review_page_visits += 1
                result.pages_viewed += 1
            elif stype == "comparison_page":
                result.comparison_page_visits += 1
                result.pages_viewed += 1
            elif stype == "competitor_visit":
                result.competitor_visits += 1
            elif stype == "email_signup":
                result.email_signups += 1
            elif stype == "cart_add":
                result.cart_additions += 1
            elif stype == "booking_start":
                result.booking_starts += 1
                result.booking_steps_completed += 1
            elif stype == "configurator_use":
                result.booking_steps_completed += 1
            elif stype == "cart_abandon":
                result.cart_abandons += 1
            elif stype == "booking_abandon":
                result.booking_abandons += 1
            elif stype == "booking_complete":
                result.booking_completions += 1
            elif stype == "purchase":
                result.booking_completions += 1
            elif stype == "unsubscribe":
                result.unsubscribes += 1
            elif stype == "complaint":
                result.complaints += 1
            elif stype == "ad_hide":
                result.ad_hides += 1

            # Accumulate dwell time from metadata
            if "dwell_seconds" in sig.metadata:
                result.total_dwell_minutes += sig.metadata["dwell_seconds"] / 60.0

        # Temporal features
        if timestamps:
            first_ts = min(timestamps)
            last_ts = max(timestamps)
            result.hours_since_first_interaction = (now - first_ts) / 3600.0
            result.hours_since_last_interaction = (now - last_ts) / 3600.0

            span_days = max(1.0, (last_ts - first_ts) / 86400.0)
            result.days_active = max(1, int(span_days))
            result.interaction_frequency_per_day = len(signals) / span_days

        # Hours since last site visit
        site_timestamps = [
            s.timestamp for s in signals
            if s.signal_type in ("site_visit", "page_view", "pricing_page",
                                  "review_page", "comparison_page")
        ]
        if site_timestamps:
            result.hours_since_last_site_visit = (now - max(site_timestamps)) / 3600.0

        # Engagement velocity: compare last 3 signals' stage weights to previous 3
        result.engagement_velocity, result.engagement_velocity_trend = (
            self._compute_engagement_velocity(signals)
        )

        # Weighted stage score
        result.stage_score = self._compute_stage_score(signals)

        return result

    def _compute_stage_score(self, signals: List[BehavioralSignal]) -> float:
        """Compute weighted sum of signal stage weights.

        More recent signals weighted higher (exponential recency).
        """
        if not signals:
            return 0.0

        now = time.time()
        weighted_sum = 0.0
        weight_total = 0.0

        for sig in signals:
            config = SIGNAL_TYPES.get(sig.signal_type)
            if not config:
                continue

            # Recency weight: half-life of 72 hours
            hours_ago = (now - sig.timestamp) / 3600.0
            recency_weight = 2.0 ** (-hours_ago / 72.0)

            weighted_sum += config["stage_weight"] * sig.value * recency_weight
            weight_total += recency_weight

        return weighted_sum / max(weight_total, 1.0)

    def _compute_engagement_velocity(
        self, signals: List[BehavioralSignal]
    ) -> tuple[float, str]:
        """Compute rate of change in engagement over recent signals.

        Compares average stage weight of last 3 signals to previous 3.
        Requires at least 6 signals for reliable comparison (3 recent vs
        3 previous). With 4-5 signals, uses available previous signals
        but lowers confidence. With <4 signals, returns stable.
        """
        if len(signals) < 4:
            return 0.0, "stable"

        def _avg_weight(sigs: List[BehavioralSignal]) -> float:
            weights = []
            for s in sigs:
                config = SIGNAL_TYPES.get(s.signal_type)
                if config:
                    weights.append(config["stage_weight"])
            return sum(weights) / max(len(weights), 1)

        recent = _avg_weight(signals[-3:])
        previous = _avg_weight(signals[-6:-3]) if len(signals) >= 6 else _avg_weight(signals[:-3])
        velocity = recent - previous

        if velocity > 0.05:
            trend = "accelerating"
        elif velocity < -0.05:
            trend = "decaying"
        else:
            trend = "stable"

        return round(velocity, 4), trend
