"""
Session Psychological State Estimation
========================================

Treats the buyer's psychological state as a hidden variable that evolves
within a session. Each impression/click/page visit is a noisy observation
that shifts the state estimate.

The key insight: a buyer's BASELINE profile (from archetype + bilateral
edges) tells us who they ARE. But their CURRENT state (right now, in this
session) depends on what they've been doing. A buyer who just visited
three product comparison pages is in high cognitive engagement mode.
A buyer who just read three negative reviews is in prevention/loss mode.

This module implements a simplified Kalman-like update:

    state_{t+1} = state_t + K × (observation_t - predicted_t)

Where K (the gain) depends on the buyer's uncertainty profile:
    - High uncertainty → observations shift state more (exploring)
    - Low uncertainty → observations shift state less (exploiting)

The result: creative parameters that adapt to where the buyer IS RIGHT NOW,
not just who they ARE in general.

Storage: In-memory per-session (keyed by buyer_id), expires after 30 min.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Session timeout: 30 minutes of inactivity = new session
_SESSION_TIMEOUT_SECONDS = 30 * 60

# Maximum observations per session (prevent memory bloat)
_MAX_SESSION_OBSERVATIONS = 50

# How much each observation type shifts the state
_OBSERVATION_GAINS = {
    # Page visit signals → psychological state shift
    "product_view": 0.15,
    "comparison_page": 0.20,
    "review_page": 0.18,
    "cart_page": 0.25,
    "checkout_page": 0.30,
    "category_browse": 0.10,
    "search": 0.12,
    "impression": 0.05,
    "click": 0.20,
    "default": 0.10,
}


@dataclass
class SessionObservation:
    """A single behavioral signal within a session."""
    observation_type: str = "default"
    timestamp: float = 0.0

    # Inferred psychological shifts from this observation
    cognitive_engagement_shift: float = 0.0
    purchase_intent_shift: float = 0.0
    urgency_shift: float = 0.0
    social_calibration_shift: float = 0.0


@dataclass
class SessionState:
    """Estimated psychological state for a buyer within a session."""

    buyer_id: str = ""
    session_start: float = 0.0
    last_activity: float = 0.0
    observation_count: int = 0

    # NDF-aligned state dimensions (relative shifts from baseline)
    cognitive_engagement_delta: float = 0.0
    purchase_intent_delta: float = 0.0
    urgency_delta: float = 0.0
    social_calibration_delta: float = 0.0
    information_saturation: float = 0.0
    decision_readiness: float = 0.0

    # Session trajectory
    observations: List[str] = field(default_factory=list)

    @property
    def session_duration_seconds(self) -> float:
        if self.session_start == 0:
            return 0.0
        return self.last_activity - self.session_start

    @property
    def session_phase(self) -> str:
        """Infer session phase from trajectory."""
        if self.observation_count <= 1:
            return "entry"
        if self.decision_readiness > 0.6:
            return "decision"
        if self.purchase_intent_delta > 0.3:
            return "consideration"
        if self.information_saturation > 0.5:
            return "evaluation"
        return "exploration"

    def to_ndf_adjustments(self) -> Dict[str, float]:
        """Convert session state to NDF profile adjustments.

        These are ADDITIVE deltas applied on top of the baseline NDF.
        Positive = shifted upward from baseline; negative = shifted down.
        """
        return {
            "cognitive_engagement": self.cognitive_engagement_delta,
            "uncertainty_tolerance": -self.urgency_delta,  # More urgency = less tolerance
            "social_calibration": self.social_calibration_delta,
            "arousal_seeking": self.urgency_delta * 0.5,
        }

    def to_creative_adjustments(self) -> Dict[str, Any]:
        """Convert session state to creative parameter adjustments."""
        adjustments: Dict[str, Any] = {}

        phase = self.session_phase

        if phase == "decision":
            adjustments["urgency_boost"] = 0.2
            adjustments["cta_directness"] = "high"
            adjustments["copy_length_preference"] = "short"
        elif phase == "consideration":
            adjustments["social_proof_boost"] = 0.15
            adjustments["detail_level_boost"] = 0.1
            adjustments["copy_length_preference"] = "medium"
        elif phase == "evaluation":
            adjustments["authority_boost"] = 0.1
            adjustments["comparison_framing"] = True
            adjustments["copy_length_preference"] = "medium"
        elif phase == "exploration":
            adjustments["curiosity_boost"] = 0.1
            adjustments["breadth_over_depth"] = True
            adjustments["copy_length_preference"] = "medium"

        return adjustments


def _infer_observation_shifts(obs_type: str) -> SessionObservation:
    """Infer psychological shifts from an observation type."""
    obs = SessionObservation(
        observation_type=obs_type,
        timestamp=time.time(),
    )

    if obs_type in ("product_view", "comparison_page"):
        obs.cognitive_engagement_shift = 0.1
        obs.purchase_intent_shift = 0.05
    elif obs_type == "review_page":
        obs.cognitive_engagement_shift = 0.08
        obs.social_calibration_shift = 0.12
    elif obs_type in ("cart_page", "checkout_page"):
        obs.purchase_intent_shift = 0.25
        obs.urgency_shift = 0.15
        obs.cognitive_engagement_shift = -0.05  # Narrowing focus
    elif obs_type == "search":
        obs.cognitive_engagement_shift = 0.12
        obs.purchase_intent_shift = 0.03
    elif obs_type == "click":
        obs.purchase_intent_shift = 0.08
        obs.urgency_shift = 0.05
    elif obs_type == "impression":
        pass  # Minimal shift from passive viewing

    return obs


class SessionStateTracker:
    """Tracks per-buyer session state with Bayesian-like updates.

    Thread-safe via simple dict operations. Sessions expire after
    30 minutes of inactivity.
    """

    def __init__(self):
        self._sessions: Dict[str, SessionState] = {}
        self._last_cleanup: float = 0.0

    def update(
        self,
        buyer_id: str,
        observation_type: str = "impression",
        buyer_uncertainty: float = 0.5,
    ) -> SessionState:
        """Update session state with a new observation.

        The Kalman gain K scales by buyer_uncertainty:
        - High uncertainty (new buyer) → observations shift state MORE
        - Low uncertainty (known buyer) → observations shift state LESS

        This means new buyers' creative adapts quickly to session behavior,
        while well-known buyers' creative stays closer to their profile.
        """
        now = time.time()

        # Get or create session
        session = self._sessions.get(buyer_id)
        if session is None or (now - session.last_activity > _SESSION_TIMEOUT_SECONDS):
            session = SessionState(
                buyer_id=buyer_id,
                session_start=now,
            )
            self._sessions[buyer_id] = session

        # Infer psychological shifts from observation
        obs = _infer_observation_shifts(observation_type)

        # Kalman-like gain: higher uncertainty → larger state shifts
        # Range: 0.3 (confident buyer) to 1.0 (unknown buyer)
        K = 0.3 + 0.7 * min(1.0, buyer_uncertainty)

        # Apply observation gain (how much this observation type matters)
        obs_gain = _OBSERVATION_GAINS.get(observation_type, _OBSERVATION_GAINS["default"])
        effective_gain = K * obs_gain

        # Update state dimensions with decay toward zero (state reverts
        # to baseline over time without new observations)
        time_since_last = min(300.0, now - session.last_activity) if session.last_activity > 0 else 0
        decay = max(0.0, 1.0 - time_since_last / 1800.0)  # Full decay in 30 min

        session.cognitive_engagement_delta = (
            session.cognitive_engagement_delta * decay
            + obs.cognitive_engagement_shift * effective_gain
        )
        session.purchase_intent_delta = (
            session.purchase_intent_delta * decay
            + obs.purchase_intent_shift * effective_gain
        )
        session.urgency_delta = (
            session.urgency_delta * decay
            + obs.urgency_shift * effective_gain
        )
        session.social_calibration_delta = (
            session.social_calibration_delta * decay
            + obs.social_calibration_shift * effective_gain
        )

        # Information saturation increases with every observation (diminishing returns)
        session.information_saturation = min(
            1.0, session.information_saturation + 0.05 * effective_gain
        )

        # Decision readiness: high purchase intent + high urgency + moderate saturation
        session.decision_readiness = min(1.0, (
            session.purchase_intent_delta * 0.5
            + session.urgency_delta * 0.3
            + session.information_saturation * 0.2
        ))

        # Track observation
        session.observation_count += 1
        session.last_activity = now
        if len(session.observations) < _MAX_SESSION_OBSERVATIONS:
            session.observations.append(observation_type)

        # Periodic cleanup of expired sessions
        if now - self._last_cleanup > 300:
            self._cleanup_expired(now)

        return session

    def get_session(self, buyer_id: str) -> Optional[SessionState]:
        """Get current session state without updating."""
        session = self._sessions.get(buyer_id)
        if session is None:
            return None
        if time.time() - session.last_activity > _SESSION_TIMEOUT_SECONDS:
            del self._sessions[buyer_id]
            return None
        return session

    def _cleanup_expired(self, now: float) -> None:
        """Remove expired sessions."""
        expired = [
            bid for bid, s in self._sessions.items()
            if now - s.last_activity > _SESSION_TIMEOUT_SECONDS
        ]
        for bid in expired:
            del self._sessions[bid]
        self._last_cleanup = now

    @property
    def stats(self) -> Dict[str, Any]:
        return {
            "active_sessions": len(self._sessions),
            "total_observations": sum(
                s.observation_count for s in self._sessions.values()
            ),
        }


# ── Singleton ──────────────────────────────────────────────────────────────

_tracker: Optional[SessionStateTracker] = None


def get_session_tracker() -> SessionStateTracker:
    global _tracker
    if _tracker is None:
        _tracker = SessionStateTracker()
    return _tracker
