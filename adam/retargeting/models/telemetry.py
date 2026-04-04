# =============================================================================
# Nonconscious Signal Intelligence — Telemetry Models
# Location: adam/retargeting/models/telemetry.py
# Enhancement #34: Nonconscious Signal Intelligence Layer, Session 1
# =============================================================================

"""
Data models for site telemetry ingestion and nonconscious signal extraction.

These models represent the raw behavioral data collected by the INFORMATIV
telemetry script on advertiser sites (e.g., luxyride.com). The telemetry
captures section-level dwell, scroll behavior, navigation paths, and
referral classification — the inputs to all 6 nonconscious signals.

Data sources:
  A. StackAdapt GraphQL API (campaign/creative/domain/device metrics)
  B. StackAdapt Universal Pixel + Click URL Macros (sapid, cid, crid, etc.)
  C. INFORMATIV Site Telemetry JS (section dwell, scroll, navigation, referral)
"""

import time
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


# =============================================================================
# ENUMS
# =============================================================================

class ReferralType(str, Enum):
    """How the user arrived at the site."""
    AD_CLICK = "ad_click"          # Has sapid URL parameter (StackAdapt attributed)
    ORGANIC_SEARCH = "organic_search"  # Search engine referrer, no sapid
    DIRECT = "direct"              # No referrer, no sapid (typed URL / bookmark)
    SOCIAL = "social"              # Social media referrer
    EMAIL = "email"                # Email campaign referrer
    UNKNOWN = "unknown"


class DeviceType(str, Enum):
    """Device classification for ELM processing route mapping."""
    DESKTOP = "desktop"
    MOBILE = "mobile"
    TABLET = "tablet"


# =============================================================================
# SECTION ENGAGEMENT (Layer 1 of Barrier Self-Report)
# =============================================================================

class SectionEngagement(BaseModel):
    """Engagement metrics for a single DOM section on the advertiser's site.

    Captured by IntersectionObserver: timing starts when section enters
    viewport, stops when it leaves. Interactions counted within section bounds.
    """
    section_id: str = Field(
        ...,
        description="DOM section ID (e.g., 'section-pricing', 'section-reviews')",
    )
    dwell_seconds: float = Field(
        ..., ge=0,
        description="Total seconds the section was in the viewport",
    )
    scroll_depth_pct: float = Field(
        0.0, ge=0.0, le=1.0,
        description="How far they scrolled through this section (0-1)",
    )
    interactions: int = Field(
        0, ge=0,
        description="Click/expand/video-play count within this section",
    )
    first_visible_ts: Optional[float] = Field(
        None,
        description="Unix timestamp when section first entered viewport",
    )


# =============================================================================
# PAGE VISIT
# =============================================================================

class PageVisit(BaseModel):
    """A single page in the navigation path."""
    url: str
    dwell_seconds: float = Field(0.0, ge=0)
    scroll_depth_pct: float = Field(0.0, ge=0.0, le=1.0)
    timestamp: float = Field(default_factory=time.time)


# =============================================================================
# SCROLL METRICS
# =============================================================================

class ScrollMetrics(BaseModel):
    """Aggregate scroll behavior for the session.

    Scroll velocity and direction changes are diagnostic of processing depth:
    - Slow, steady scroll = reading/evaluating (central route)
    - Fast scroll with many direction changes = scanning (peripheral route)
    - Scroll-back to specific section = re-evaluation (high engagement)
    """
    max_depth_pct: float = Field(0.0, ge=0.0, le=1.0)
    avg_velocity_px_per_sec: float = Field(0.0, ge=0)
    direction_changes: int = Field(0, ge=0)
    scroll_backs: int = Field(
        0, ge=0,
        description="Times user scrolled back UP to a previous section",
    )


# =============================================================================
# TELEMETRY SESSION PAYLOAD (from JS → backend)
# =============================================================================

class TelemetrySessionPayload(BaseModel):
    """Complete telemetry payload emitted by the INFORMATIV JS script
    at session end (beforeunload / visibilitychange).

    This is the primary ingest model for POST /api/v1/signals/session.
    """

    # ── Identity ──
    visitor_id: str = Field(
        ...,
        description="First-party cookie ID (persistent across sessions)",
    )
    session_id: str = Field(
        ...,
        description="Unique session ID (new per visit)",
    )

    # ── StackAdapt attribution (from URL macros) ──
    sapid: Optional[str] = Field(
        None,
        description="StackAdapt postback ID — present only on ad-click arrivals",
    )
    campaign_id: Optional[str] = Field(None, description="StackAdapt campaign ID")
    creative_id: Optional[str] = Field(None, description="StackAdapt creative ID")
    domain: Optional[str] = Field(None, description="Publisher domain where ad was shown")

    # ── Device + context ──
    device_type: DeviceType = DeviceType.DESKTOP
    viewport_width: int = Field(0, ge=0)
    viewport_height: int = Field(0, ge=0)
    user_agent: Optional[str] = None

    # ── Referral classification ──
    referral_type: ReferralType = ReferralType.UNKNOWN
    referrer_url: Optional[str] = None

    # ── Timing ──
    arrival_timestamp: float = Field(
        ...,
        description="Unix timestamp of page arrival (performance.timeOrigin + navigationStart)",
    )
    first_interaction_timestamp: Optional[float] = Field(
        None,
        description="Unix timestamp of first meaningful interaction (click, scroll >10%)",
    )
    departure_timestamp: float = Field(
        default_factory=time.time,
        description="Unix timestamp of session end",
    )

    # ── Engagement data ──
    landing_page: str = Field(..., description="Landing page URL path")
    pages_visited: List[PageVisit] = Field(default_factory=list)
    section_engagements: List[SectionEngagement] = Field(default_factory=list)
    scroll_metrics: Optional[ScrollMetrics] = None

    # ── Return visit detection ──
    is_return_visit: bool = Field(
        False,
        description="True if visitor_id cookie existed before this session",
    )
    previous_visit_count: int = Field(
        0, ge=0,
        description="Number of prior sessions for this visitor_id",
    )

    # ── Computed properties ──
    @property
    def total_session_seconds(self) -> float:
        return max(0.0, self.departure_timestamp - self.arrival_timestamp)

    @property
    def is_ad_attributed(self) -> bool:
        return self.sapid is not None

    @property
    def is_organic(self) -> bool:
        return self.sapid is None

    @property
    def bounced(self) -> bool:
        return len(self.pages_visited) <= 1

    @field_validator("visitor_id", "session_id")
    @classmethod
    def must_be_nonempty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Must be a non-empty string")
        return v.strip()


# =============================================================================
# CLICK LATENCY OBSERVATION (Signal 1)
# =============================================================================

class ClickLatencyData(BaseModel):
    """Click latency extracted from impression→click timing.

    Impression timestamp comes from StackAdapt {TIMESTAMP} macro in click URL.
    Page arrival timestamp from our telemetry (performance.timeOrigin).
    Delta = click latency = approach-avoidance conflict duration.
    """
    impression_timestamp: Optional[float] = Field(
        None,
        description="Unix timestamp of ad impression (from StackAdapt macro)",
    )
    click_timestamp: Optional[float] = Field(
        None,
        description="Unix timestamp of ad click (page arrival minus load overhead)",
    )

    @property
    def latency_seconds(self) -> Optional[float]:
        if self.impression_timestamp and self.click_timestamp:
            delta = self.click_timestamp - self.impression_timestamp
            return delta if delta > 0 else None
        return None


# =============================================================================
# STORED SIGNAL PROFILE (per-user, persisted to Redis)
# =============================================================================

class StoredSignalProfile(BaseModel):
    """Persisted per-user signal state in Redis.

    Accumulates across sessions. Read by the DiagnosticReasoner
    before hypothesis evaluation and by the retargeting planner
    before constructing the next touch.
    """
    user_id: str

    # Visit history
    total_sessions: int = 0
    ad_attributed_sessions: int = 0
    organic_sessions: int = 0
    total_page_views: int = 0

    # Section engagement accumulator (barrier signal)
    section_dwell_totals: Dict[str, float] = Field(
        default_factory=dict,
        description="Cumulative dwell seconds per section across all sessions",
    )
    section_interaction_totals: Dict[str, int] = Field(
        default_factory=dict,
        description="Cumulative interaction count per section across all sessions",
    )

    # Click latency history (Signal 1)
    click_latencies: List[float] = Field(
        default_factory=list,
        description="Ordered list of click latency values (seconds)",
    )

    # Click latency trajectory (Signal 1 — computed, not accumulated)
    click_latency_trajectory: str = Field(
        "",
        description="Trajectory type: resolving/building/oscillating/stable/insufficient",
    )
    click_latency_slope: float = Field(
        0.0,
        description="OLS slope of latency across touches (seconds/touch)",
    )
    latest_conflict_class: str = Field(
        "",
        description="Conflict class of most recent click: automatic/moderate/high_conflict",
    )

    # Barrier self-report (Signal 2 — computed from section engagement)
    self_reported_barrier: str = Field(
        "",
        description="Top barrier inferred from section engagement patterns",
    )
    barrier_self_report_confidence: float = Field(
        0.0,
        description="Confidence of the self-reported barrier (0-1)",
    )
    barrier_dimensions_to_target: List[str] = Field(
        default_factory=list,
        description="Alignment dimensions associated with self-reported barrier",
    )

    # Device engagement (Signal 5)
    device_impressions: Dict[str, int] = Field(
        default_factory=dict,
        description="Impression count per device type",
    )
    device_clicks: Dict[str, int] = Field(
        default_factory=dict,
        description="Click count per device type",
    )

    # Engagement history (Signal 6 — frequency decay)
    touch_outcomes: List[bool] = Field(
        default_factory=list,
        description="Ordered list of click/no-click per touch",
    )

    # Return visit timestamps (Signal 3)
    visit_timestamps: List[float] = Field(
        default_factory=list,
        description="Timestamps of all visits for temporal analysis",
    )
    visit_is_organic: List[bool] = Field(
        default_factory=list,
        description="Whether each visit was organic (parallel to visit_timestamps)",
    )

    # Organic return analysis (Signal 3 — computed)
    organic_stage: str = Field(
        "",
        description="Stage signal: evaluating_externally/evaluating_with_interest/intending",
    )
    organic_surge_multiplier: float = Field(
        0.0,
        description="Individual organic ratio / population baseline",
    )
    organic_mechanism_recommendation: str = Field(
        "",
        description="Mechanism recommendation from organic analysis",
    )

    # Device compatibility (Signal 5 — computed)
    device_mechanism_mismatch: bool = Field(
        False,
        description="Whether the most recent mechanism was mismatched to served device",
    )

    # Frequency decay / reactance (Signal 6 — computed)
    reactance_detected: bool = Field(
        False,
        description="Whether individual reactance onset has been detected",
    )
    reactance_onset_touch: Optional[int] = Field(
        None,
        description="Touch number where reactance was first detected",
    )
    reactance_h4_modifier: float = Field(
        0.0,
        description="H4 modifier from frequency decay analysis",
    )

    # Best engagement hour (empirical, no theory overlay)
    hour_engagement_counts: Dict[int, int] = Field(
        default_factory=dict,
        description="Engagement count per hour of day (0-23)",
    )

    # Last updated
    last_updated: float = Field(default_factory=time.time)

    @property
    def organic_ratio(self) -> float:
        total = self.ad_attributed_sessions + self.organic_sessions
        return self.organic_sessions / total if total > 0 else 0.0

    @property
    def best_hour(self) -> Optional[int]:
        if not self.hour_engagement_counts:
            return None
        return max(self.hour_engagement_counts, key=self.hour_engagement_counts.get)
