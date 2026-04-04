# =============================================================================
# Nonconscious Profile — Composite Signal Aggregator
# Location: adam/retargeting/engines/nonconscious_profile.py
# Enhancement #34: Nonconscious Signal Intelligence Layer, Session 5
# =============================================================================

"""
Aggregates all 6 nonconscious behavioral signals into a single composite
profile that feeds the DiagnosticReasoner and retargeting planner.

This is the interface layer between raw signal data (StoredSignalProfile)
and the decision-making components. It computes:

1. Aggregate H1-H5 modifiers (additive across signals, clamped to [-0.5, 0.5])
2. Stage override signal (organic return → INTENDING)
3. Mechanism recommendation (from organic + reactance)
4. Device recommendation (from ELM compatibility)
5. Per-individual receptive window (empirical hour-of-day)

The DiagnosticReasoner consumes this via DiagnosticInput.external_h_modifiers.
The retargeting planner consumes stage/mechanism/device recommendations.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# H-modifier clamp range — prevents runaway from stacking multiple signals
_H_CLAMP_MIN = -0.5
_H_CLAMP_MAX = 0.5


@dataclass
class NonconsciousProfile:
    """Composite behavioral intelligence for one individual.

    Built from StoredSignalProfile by build_from_stored_profile().
    Consumed by DiagnosticReasoner (H-modifiers) and retargeting planner
    (stage/mechanism/device recommendations).
    """
    user_id: str

    # Signal 1: Click latency trajectory
    click_latency_trajectory: Optional[str] = None
    click_latency_slope: Optional[float] = None
    latest_conflict_class: Optional[str] = None

    # Signal 2: Barrier self-report
    self_reported_barrier: Optional[str] = None
    barrier_override_active: bool = False
    barrier_confidence: float = 0.0
    barrier_dimensions_to_target: List[str] = field(default_factory=list)

    # Signal 3: Organic return ratio
    organic_ratio: float = 0.0
    surge_multiplier: float = 0.0
    stage_signal: Optional[str] = None
    organic_mechanism_recommendation: Optional[str] = None

    # Signal 4: Processing depth distribution
    unprocessed_rate: float = 0.0
    avg_processing_depth_weight: float = 0.5

    # Signal 5: Device profile
    preferred_device: Optional[str] = None
    device_mechanism_mismatch: bool = False

    # Signal 6: Reactance signature
    reactance_detected: bool = False
    reactance_onset_touch: Optional[int] = None
    reactance_h4_modifier: float = 0.0

    # Per-individual receptive window (empirical, no theory overlay)
    best_engagement_hour: Optional[int] = None

    def compute_aggregate_h_modifiers(self) -> Dict[str, float]:
        """Combine all signal modifiers into a single set of H1-H5 adjustments.

        Modifiers are ADDITIVE across signals.
        The DiagnosticReasoner applies these before hypothesis evaluation.

        Returns:
            Dict with keys H1-H5 and float values clamped to [-0.5, 0.5].
        """
        h: Dict[str, float] = {"H1": 0.0, "H2": 0.0, "H3": 0.0, "H4": 0.0, "H5": 0.0}

        # Signal 1: Click latency trajectory
        if self.click_latency_trajectory == "resolving":
            h["H2"] -= 0.15
            h["H3"] -= 0.10
            h["H4"] -= 0.20
        elif self.click_latency_trajectory == "building":
            h["H2"] += 0.10
            h["H4"] += 0.25
        elif self.click_latency_trajectory == "oscillating":
            h["H1"] += 0.10
            h["H2"] += 0.15

        # Signal 4: Processing depth — per-impression weighting is in the
        # BONG/Thompson update pipeline (Session 2). At the profile level,
        # a high unprocessed_rate informs H5.
        if self.unprocessed_rate > 0.5:
            h["H5"] += 0.20  # Most impressions aren't being seen

        # Signal 5: Device mismatch
        if self.device_mechanism_mismatch:
            h["H1"] += 0.15

        # Signal 6: Reactance
        if self.reactance_detected:
            h["H4"] += 0.30
        elif self.reactance_h4_modifier != 0.0:
            h["H4"] += self.reactance_h4_modifier

        # Clamp all modifiers to prevent runaway
        for key in h:
            h[key] = max(_H_CLAMP_MIN, min(_H_CLAMP_MAX, h[key]))

        return h

    def get_mechanism_override(self) -> Optional[str]:
        """Get mechanism override if any signal demands a specific mechanism.

        Priority:
        1. Reactance detected → autonomy_restoration
        2. Organic INTENDING → implementation_intention
        """
        if self.reactance_detected:
            return "autonomy_restoration"
        if self.stage_signal == "intending" and self.organic_mechanism_recommendation:
            return self.organic_mechanism_recommendation
        return None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize for JSON logging / API response."""
        return {
            "user_id": self.user_id,
            "click_latency_trajectory": self.click_latency_trajectory,
            "click_latency_slope": self.click_latency_slope,
            "latest_conflict_class": self.latest_conflict_class,
            "self_reported_barrier": self.self_reported_barrier,
            "barrier_override_active": self.barrier_override_active,
            "barrier_confidence": self.barrier_confidence,
            "barrier_dimensions_to_target": self.barrier_dimensions_to_target,
            "organic_ratio": self.organic_ratio,
            "surge_multiplier": self.surge_multiplier,
            "stage_signal": self.stage_signal,
            "organic_mechanism_recommendation": self.organic_mechanism_recommendation,
            "unprocessed_rate": self.unprocessed_rate,
            "avg_processing_depth_weight": self.avg_processing_depth_weight,
            "preferred_device": self.preferred_device,
            "device_mechanism_mismatch": self.device_mechanism_mismatch,
            "reactance_detected": self.reactance_detected,
            "reactance_onset_touch": self.reactance_onset_touch,
            "reactance_h4_modifier": self.reactance_h4_modifier,
            "best_engagement_hour": self.best_engagement_hour,
            "aggregate_h_modifiers": self.compute_aggregate_h_modifiers(),
            "mechanism_override": self.get_mechanism_override(),
        }


def build_from_stored_profile(
    stored: "StoredSignalProfile",
    last_mechanism: str = "",
    last_device: str = "",
) -> NonconsciousProfile:
    """Build a NonconsciousProfile from a StoredSignalProfile.

    This is the bridge between the persistence layer (Redis-backed
    StoredSignalProfile) and the decision layer (NonconsciousProfile).

    Args:
        stored: The persisted signal profile from Redis.
        last_mechanism: Most recently deployed mechanism (for device compat).
        last_device: Device the last ad was served on (for device compat).

    Returns:
        NonconsciousProfile ready for DiagnosticReasoner consumption.
    """
    profile = NonconsciousProfile(user_id=stored.user_id)

    # Signal 1: Click latency
    profile.click_latency_trajectory = stored.click_latency_trajectory or None
    profile.click_latency_slope = stored.click_latency_slope or None
    profile.latest_conflict_class = stored.latest_conflict_class or None

    # Signal 2: Barrier self-report
    profile.self_reported_barrier = stored.self_reported_barrier or None
    profile.barrier_confidence = stored.barrier_self_report_confidence
    profile.barrier_dimensions_to_target = stored.barrier_dimensions_to_target
    profile.barrier_override_active = (
        stored.barrier_self_report_confidence > 0.5
        and bool(stored.self_reported_barrier)
    )

    # Signal 3: Organic return
    profile.organic_ratio = stored.organic_ratio
    profile.stage_signal = stored.organic_stage or None
    profile.surge_multiplier = stored.organic_surge_multiplier
    profile.organic_mechanism_recommendation = (
        stored.organic_mechanism_recommendation or None
    )

    # Signal 5: Device compatibility
    if last_mechanism and last_device:
        from adam.retargeting.engines.device_compat import DeviceEngagementTracker
        tracker = DeviceEngagementTracker()
        profile.device_mechanism_mismatch = tracker.is_mismatched(
            last_mechanism, last_device,
        )
        rec = tracker.recommend_device(
            last_mechanism,
            stored.device_impressions,
            stored.device_clicks,
        )
        profile.preferred_device = rec["recommended_device"]

    # Signal 6: Reactance
    profile.reactance_detected = stored.reactance_detected
    profile.reactance_onset_touch = stored.reactance_onset_touch
    profile.reactance_h4_modifier = stored.reactance_h4_modifier

    # Receptive window
    profile.best_engagement_hour = stored.best_hour

    return profile


def enrich_diagnostic_input(
    inp: "DiagnosticInput",
    nonconscious: NonconsciousProfile,
) -> "DiagnosticInput":
    """Enrich a DiagnosticInput with nonconscious signal intelligence.

    Call this BEFORE passing the DiagnosticInput to reason_sync().
    Merges the aggregate H-modifiers into external_h_modifiers and
    applies barrier/mechanism overrides.

    Args:
        inp: The DiagnosticInput to enrich (modified in place).
        nonconscious: The computed NonconsciousProfile.

    Returns:
        The enriched DiagnosticInput (same object, for chaining).
    """
    # 1. Merge aggregate H-modifiers
    h_mods = nonconscious.compute_aggregate_h_modifiers()
    existing = inp.external_h_modifiers or {}
    for key in ("H1", "H2", "H3", "H4", "H5"):
        existing[key] = existing.get(key, 0.0) + h_mods.get(key, 0.0)
    inp.external_h_modifiers = existing

    # 2. Barrier override: if self-report overrides algorithmic diagnosis
    if (
        nonconscious.barrier_override_active
        and nonconscious.self_reported_barrier
        and inp.current_barrier
        and nonconscious.self_reported_barrier != inp.current_barrier
    ):
        inp.behavioral_signals["barrier_self_report_override"] = 1.0
        inp.behavioral_signals["self_reported_barrier"] = 1.0
        # The actual barrier swap happens in the retargeting planner,
        # not here — we just flag it in behavioral_signals.

    # 3. Reactance level from Signal 6
    if nonconscious.reactance_detected:
        inp.reactance_level = max(inp.reactance_level, 0.8)

    # 4. Stage override from Signal 3
    if nonconscious.stage_signal == "intending":
        inp.behavioral_signals["organic_intending"] = 1.0

    return inp


async def get_nonconscious_profile_for_user(
    user_id: str,
    last_mechanism: str = "",
    last_device: str = "",
) -> Optional[NonconsciousProfile]:
    """Load a user's nonconscious profile from Redis.

    Convenience function for use in API endpoints and orchestrators.
    Returns None if no signal data exists for this user.
    """
    try:
        from adam.core.dependencies import Infrastructure, LearningComponents
        infra = Infrastructure.get_instance()
        components = LearningComponents.get_instance(infra)
        collector = components.signal_collector
        if collector is None:
            return None

        stored = await collector.get_profile(user_id)
        if stored is None or stored.total_sessions == 0:
            return None

        return build_from_stored_profile(stored, last_mechanism, last_device)
    except Exception as e:
        logger.debug("Failed to load nonconscious profile for %s: %s", user_id, e)
        return None
