# =============================================================================
# Therapeutic Retargeting Engine — Rupture Detection & Repair
# Location: adam/retargeting/engines/rupture_detector.py
# Spec: Enhancement #33, Section B.3 + Session 33-4
# =============================================================================

"""
Rupture Detection and Repair Strategy System.

From therapeutic alliance research (Eubanks et al., 2018, k=11, N=1,314):
successful rupture resolution (d=.62) produces outcomes AT LEAST as strong
as frictionless journeys. The system detects three rupture types and
selects type-matched repair strategies.

This is a SHARED PLATFORM SERVICE — usable by any multi-touch system
(retargeting, email sequences, CRM, future sequential persuasion).

Critical: Wicklund's hydraulic principle — a second freedom threat before
the first dissipates = MULTIPLICATIVE compounding. Rapid touches after
rupture can permanently destroy the relationship.
"""

import logging
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from adam.retargeting.models.enums import RuptureType, TherapeuticMechanism

logger = logging.getLogger(__name__)


@dataclass
class RuptureAssessment:
    """Complete rupture assessment with repair recommendation."""

    rupture_type: RuptureType
    severity: float  # 0.0 = none, 1.0 = complete disengagement
    confidence: float  # How sure we are this is a rupture

    # Detection evidence
    evidence: Dict[str, float]

    # Repair recommendation
    repair_action: str  # "continue", "change_mechanism", "acknowledge", "pause", "suppress"
    repair_mechanism: Optional[TherapeuticMechanism] = None
    min_pause_hours: int = 0
    explanation: str = ""


class RuptureDetector:
    """Detects engagement ruptures using Safran & Muran typology.

    Three rupture types:
    - WITHDRAWAL: Silent disengagement (declining CTR, longer gaps, ad blindness)
    - CONFRONTATION: Active rejection (unsubscribe, complaint, ad hide)
    - DECAY: Gradual fading without clear trigger

    Each has different detection signatures and different repair strategies.
    """

    def __init__(
        self,
        withdrawal_velocity_threshold: float = 0.3,
        decay_gap_multiplier: float = 2.0,
        min_touches_for_detection: int = 2,
    ):
        self._withdrawal_threshold = withdrawal_velocity_threshold
        self._decay_multiplier = decay_gap_multiplier
        self._min_touches = min_touches_for_detection

    def assess(
        self,
        touch_history: List[Dict],
        behavioral_signals: Optional[Dict[str, float]] = None,
        archetype_id: str = "",
    ) -> RuptureAssessment:
        """Produce a complete rupture assessment with repair recommendation.

        Args:
            touch_history: List of touch dicts with keys:
                - engagement_occurred (bool)
                - mechanism (str)
                - hours_since_delivery (float)
                - hours_since_previous (float)
                - outcome (str): "engaged", "ignored", "bounced"
                - delivered_at (float, timestamp)
            behavioral_signals: Dict with keys like unsubscribe_signal,
                complaint_signal, ad_hide_signal, etc.
            archetype_id: Used for archetype-specific median timing

        Returns:
            RuptureAssessment with repair recommendation
        """
        behavioral_signals = behavioral_signals or {}

        # Check for confrontation FIRST (most urgent)
        confrontation = self._detect_confrontation(behavioral_signals)
        if confrontation is not None:
            return confrontation

        if len(touch_history) < self._min_touches:
            return RuptureAssessment(
                rupture_type=RuptureType.NONE,
                severity=0.0,
                confidence=0.8,
                evidence={"touches": len(touch_history)},
                repair_action="continue",
                explanation="Insufficient touch history for rupture detection",
            )

        # Check withdrawal (most common, hardest to detect)
        withdrawal = self._detect_withdrawal(touch_history)
        if withdrawal is not None:
            return withdrawal

        # Check decay (gradual)
        decay = self._detect_decay(touch_history)
        if decay is not None:
            return decay

        return RuptureAssessment(
            rupture_type=RuptureType.NONE,
            severity=0.0,
            confidence=0.7,
            evidence=self._compute_health_evidence(touch_history),
            repair_action="continue",
            explanation="No rupture detected. Engagement pattern is healthy.",
        )

    def _detect_confrontation(
        self, signals: Dict[str, float]
    ) -> Optional[RuptureAssessment]:
        """Detect CONFRONTATION ruptures from explicit negative signals."""
        evidence = {}

        unsubscribe = signals.get("unsubscribe_signal", 0)
        complaint = signals.get("complaint_signal", 0)
        ad_hide = signals.get("ad_hide_signal", 0)

        if unsubscribe > 0:
            evidence["unsubscribe"] = unsubscribe
        if complaint > 0:
            evidence["complaint"] = complaint
        if ad_hide > 0:
            evidence["ad_hide"] = ad_hide

        if not evidence:
            return None

        # Severity by signal type
        severity = 0.0
        if complaint > 0:
            severity = 0.95
        elif unsubscribe > 0:
            severity = 0.90
        elif ad_hide > 0:
            severity = 0.60

        return RuptureAssessment(
            rupture_type=RuptureType.CONFRONTATION,
            severity=severity,
            confidence=0.95,  # Explicit signals are high-confidence
            evidence=evidence,
            repair_action="acknowledge" if severity < 0.95 else "suppress",
            repair_mechanism=TherapeuticMechanism.AUTONOMY_RESTORATION,
            min_pause_hours=72 if severity < 0.95 else 336,  # 3 days or 2 weeks
            explanation=(
                "Confrontation rupture detected. User has actively rejected "
                "engagement. Repair requires transparent acknowledgment + "
                "changed approach. Clinical evidence: explicit acknowledgment "
                "is effective for confrontation (unlike withdrawal)."
            ),
        )

    def _detect_withdrawal(
        self, touch_history: List[Dict]
    ) -> Optional[RuptureAssessment]:
        """Detect WITHDRAWAL ruptures from engagement velocity decline.

        Withdrawal = movements AWAY: declining engagement, ad blindness.
        Most common, hardest to detect.

        Repair: Change mechanism completely. Do NOT acknowledge withdrawal
        explicitly (clinical evidence: self-disclosure ineffective for
        withdrawal — Safran & Muran).
        """
        # Check last 3 touches: all ignored = withdrawal
        recent = touch_history[-3:]
        recent_engagements = [t.get("engagement_occurred", False) for t in recent]

        if len(recent) >= 3 and not any(recent_engagements):
            # 3+ consecutive non-engagements
            consecutive_ignores = 0
            for t in reversed(touch_history):
                if t.get("engagement_occurred"):
                    break
                consecutive_ignores += 1

            severity = min(1.0, 0.5 + 0.1 * consecutive_ignores)

            # Find what mechanisms failed
            failed_mechanisms = [
                t.get("mechanism", "unknown")
                for t in touch_history[-consecutive_ignores:]
            ]

            return RuptureAssessment(
                rupture_type=RuptureType.WITHDRAWAL,
                severity=severity,
                confidence=0.75,
                evidence={
                    "consecutive_ignores": consecutive_ignores,
                    "failed_mechanisms": len(set(failed_mechanisms)),
                },
                repair_action="change_mechanism",
                repair_mechanism=TherapeuticMechanism.NARRATIVE_TRANSPORTATION,
                min_pause_hours=48,
                explanation=(
                    f"Withdrawal rupture: {consecutive_ignores} consecutive "
                    f"non-engagements. Failed mechanisms: {set(failed_mechanisms)}. "
                    f"Repair: switch to narrative transportation (high transport "
                    f"reduces critical thoughts r=-.20). Do NOT acknowledge the "
                    f"withdrawal explicitly."
                ),
            )

        # Check engagement rate decline
        if len(touch_history) >= 4:
            first_half = touch_history[: len(touch_history) // 2]
            second_half = touch_history[len(touch_history) // 2 :]

            rate_first = sum(
                1 for t in first_half if t.get("engagement_occurred")
            ) / max(len(first_half), 1)
            rate_second = sum(
                1 for t in second_half if t.get("engagement_occurred")
            ) / max(len(second_half), 1)

            if rate_first > 0 and rate_second / max(rate_first, 0.01) < self._withdrawal_threshold:
                return RuptureAssessment(
                    rupture_type=RuptureType.WITHDRAWAL,
                    severity=0.5,
                    confidence=0.60,
                    evidence={
                        "rate_first_half": round(rate_first, 3),
                        "rate_second_half": round(rate_second, 3),
                        "velocity_ratio": round(
                            rate_second / max(rate_first, 0.01), 3
                        ),
                    },
                    repair_action="change_mechanism",
                    repair_mechanism=TherapeuticMechanism.NOVELTY_DISRUPTION,
                    min_pause_hours=24,
                    explanation=(
                        f"Engagement rate dropped from {rate_first:.0%} to "
                        f"{rate_second:.0%}. Introducing novelty disruption to "
                        f"break pattern and re-engage System 2 processing."
                    ),
                )

        return None

    def _detect_decay(
        self, touch_history: List[Dict]
    ) -> Optional[RuptureAssessment]:
        """Detect DECAY ruptures from gradual disengagement.

        Decay = time since last engagement exceeds 2x the median gap
        for this user's history.
        """
        # Find last engagement
        last_engagement_idx = None
        for i in range(len(touch_history) - 1, -1, -1):
            if touch_history[i].get("engagement_occurred"):
                last_engagement_idx = i
                break

        if last_engagement_idx is None:
            # Never engaged — this is not decay, it's withdrawal
            return None

        touches_since = len(touch_history) - 1 - last_engagement_idx
        if touches_since < 3:
            return None

        # Compute median inter-engagement gap from history
        engagement_timestamps = [
            t.get("delivered_at", 0)
            for t in touch_history
            if t.get("engagement_occurred")
        ]

        if len(engagement_timestamps) < 2:
            median_gap_hours = 48.0  # Default
        else:
            gaps = []
            for i in range(1, len(engagement_timestamps)):
                gap = (engagement_timestamps[i] - engagement_timestamps[i - 1]) / 3600.0
                if gap > 0:
                    gaps.append(gap)
            median_gap_hours = sorted(gaps)[len(gaps) // 2] if gaps else 48.0

        # Current gap
        now = time.time()
        last_engagement_ts = touch_history[last_engagement_idx].get(
            "delivered_at", now - 86400
        )
        current_gap_hours = (now - last_engagement_ts) / 3600.0

        if current_gap_hours > median_gap_hours * self._decay_multiplier:
            severity = min(
                1.0, 0.4 + 0.1 * (current_gap_hours / max(median_gap_hours, 1))
            )

            return RuptureAssessment(
                rupture_type=RuptureType.DECAY,
                severity=severity,
                confidence=0.55,
                evidence={
                    "current_gap_hours": round(current_gap_hours, 1),
                    "median_gap_hours": round(median_gap_hours, 1),
                    "gap_ratio": round(
                        current_gap_hours / max(median_gap_hours, 1), 2
                    ),
                    "touches_since_engagement": touches_since,
                },
                repair_action="change_mechanism",
                repair_mechanism=TherapeuticMechanism.VIVID_SCENARIO,
                min_pause_hours=0,  # Decay needs re-engagement, not more silence
                explanation=(
                    f"Decay detected: {current_gap_hours:.0f}h since last "
                    f"engagement (median gap: {median_gap_hours:.0f}h, ratio: "
                    f"{current_gap_hours/max(median_gap_hours,1):.1f}x). "
                    f"Reset narrative arc with vivid scenario to re-engage."
                ),
            )

        return None

    def _compute_health_evidence(
        self, touch_history: List[Dict]
    ) -> Dict[str, float]:
        """Compute engagement health metrics when no rupture detected."""
        total = len(touch_history)
        engaged = sum(1 for t in touch_history if t.get("engagement_occurred"))
        rate = engaged / max(total, 1)

        return {
            "total_touches": total,
            "engaged_touches": engaged,
            "engagement_rate": round(rate, 3),
        }
