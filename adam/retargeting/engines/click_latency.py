# =============================================================================
# Click Latency Tracker — Signal 1
# Location: adam/retargeting/engines/click_latency.py
# Enhancement #34: Nonconscious Signal Intelligence Layer, Session 3
# =============================================================================

"""
Measures approach-avoidance conflict duration from click latency and
tracks barrier resolution/building across retargeting sequences.

Click latency = time from ad impression to ad click. This is a behavioral
proxy for approach-avoidance conflict (Krajbich et al. 2010, Milosavljevic
et al. 2011). Short latency = automatic approach (mechanism resonated).
Long latency = high conflict (barrier present but attraction exists).

The SLOPE of latency across touches is the key diagnostic:
  - Negative slope: barrier resolving. Mechanism is working.
  - Positive slope: barrier building. Likely reactance.
  - Oscillating: mechanism effectiveness inconsistent.
  - Stable: no trajectory signal.

Thresholds are calibrated from DDM consumer choice literature.
Non-decision time ~400ms (mobile) / ~200ms (desktop).
Evidence accumulation for automatic choices: ~600-800ms.
"""

import logging
from enum import Enum
from typing import Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


# =============================================================================
# CONFLICT CLASSIFICATION
# =============================================================================

# Starting values grounded in DDM consumer choice literature.
# Calibrate from own data after 500+ clicks.
AUTOMATIC_THRESHOLD_SECONDS = 1.0   # Below: automatic approach, minimal conflict
CONFLICT_THRESHOLD_SECONDS = 4.0    # Above: high approach-avoidance conflict

# Mobile adds ~200ms non-decision time vs desktop
MOBILE_ADJUSTMENT_SECONDS = 0.2


class ConflictClass(str, Enum):
    """Click latency conflict classification."""
    AUTOMATIC = "automatic"       # Low conflict. Mechanism resonated.
    MODERATE = "moderate"         # Deliberating. Barrier present but attracted.
    HIGH_CONFLICT = "high_conflict"  # Extended conflict. Strong barrier.


class TrajectoryType(str, Enum):
    """Cross-touch latency trajectory classification."""
    RESOLVING = "resolving"       # Negative slope — barrier resolving
    BUILDING = "building"         # Positive slope — barrier building / reactance
    OSCILLATING = "oscillating"   # Non-monotonic — inconsistent effectiveness
    STABLE = "stable"             # Flat slope — no trajectory signal
    INSUFFICIENT = "insufficient" # < 3 observations


# =============================================================================
# TRAJECTORY H-MODIFIERS
# =============================================================================

# Applied to DiagnosticReasoner H1-H5 via external_h_modifiers.
# A "building" trajectory is the strongest single-signal modifier
# for H4 (reactance) in the system (+0.25).

TRAJECTORY_H_MODIFIERS: Dict[TrajectoryType, Dict[str, float]] = {
    TrajectoryType.RESOLVING: {
        "H1": 0.0,
        "H2": -0.15,  # Mechanism is working (less likely wrong)
        "H3": -0.10,  # Stage match confirmed by resolving conflict
        "H4": -0.20,  # Barrier resolving = no reactance
        "H5": 0.0,
    },
    TrajectoryType.BUILDING: {
        "H1": 0.0,
        "H2": 0.10,   # Mechanism may be wrong (conflict increasing)
        "H3": 0.05,
        "H4": 0.25,   # STRONGEST single-signal H4 modifier
        "H5": 0.05,
    },
    TrajectoryType.OSCILLATING: {
        "H1": 0.10,   # Context inconsistency — page mindstate varying
        "H2": 0.15,   # Mechanism effectiveness unstable
        "H3": 0.0,
        "H4": 0.0,
        "H5": 0.0,
    },
    TrajectoryType.STABLE: {
        "H1": 0.0, "H2": 0.0, "H3": 0.0, "H4": 0.0, "H5": 0.0,
    },
    TrajectoryType.INSUFFICIENT: {
        "H1": 0.0, "H2": 0.0, "H3": 0.0, "H4": 0.0, "H5": 0.0,
    },
}

# Slope thresholds for trajectory classification (seconds per touch)
_RESOLVING_SLOPE_THRESHOLD = -0.3
_BUILDING_SLOPE_THRESHOLD = 0.3


# =============================================================================
# CLICK LATENCY TRACKER
# =============================================================================

class ClickLatencyTracker:
    """Track click latency across retargeting touches per individual.

    Stateless computation engine — reads from and writes to
    StoredSignalProfile's click_latencies list.
    """

    def classify_conflict(
        self,
        latency_seconds: float,
        device: str = "desktop",
    ) -> ConflictClass:
        """Classify approach-avoidance conflict from click latency.

        Args:
            latency_seconds: Time from impression to click.
            device: "mobile", "tablet", or "desktop".

        Returns:
            ConflictClass enum value.
        """
        adjustment = MOBILE_ADJUSTMENT_SECONDS if device == "mobile" else 0.0
        adjusted = latency_seconds - adjustment

        if adjusted < AUTOMATIC_THRESHOLD_SECONDS:
            return ConflictClass.AUTOMATIC
        elif adjusted < CONFLICT_THRESHOLD_SECONDS:
            return ConflictClass.MODERATE
        else:
            return ConflictClass.HIGH_CONFLICT

    def compute_trajectory(
        self,
        latencies: List[float],
    ) -> Dict:
        """Compute latency trajectory from an ordered list of click latencies.

        Args:
            latencies: Ordered list of click latency values (seconds),
                one per ad-click touch.

        Returns:
            Dict with trajectory_type, slope, n_observations, h_modifiers.
            Returns None-like result if insufficient data.
        """
        n = len(latencies)

        if n < 2:
            return {
                "trajectory_type": TrajectoryType.INSUFFICIENT.value,
                "slope": 0.0,
                "n_observations": n,
                "h_modifiers": TRAJECTORY_H_MODIFIERS[TrajectoryType.INSUFFICIENT].copy(),
            }

        # Simple OLS slope
        x = np.arange(n, dtype=float)
        slope = float(np.polyfit(x, latencies, 1)[0])

        if n < 3:
            # With only 2 points, slope is unreliable — report but don't classify
            return {
                "trajectory_type": TrajectoryType.INSUFFICIENT.value,
                "slope": slope,
                "n_observations": n,
                "h_modifiers": TRAJECTORY_H_MODIFIERS[TrajectoryType.INSUFFICIENT].copy(),
            }

        # Classify trajectory
        if slope < _RESOLVING_SLOPE_THRESHOLD:
            ttype = TrajectoryType.RESOLVING
        elif slope > _BUILDING_SLOPE_THRESHOLD:
            ttype = TrajectoryType.BUILDING
        else:
            # Check non-monotonicity (oscillation)
            diffs = np.diff(latencies)
            if len(diffs) >= 2:
                sign_changes = int(np.sum(diffs[:-1] * diffs[1:] < 0))
            else:
                sign_changes = 0

            if sign_changes > 0:
                ttype = TrajectoryType.OSCILLATING
            else:
                ttype = TrajectoryType.STABLE

        return {
            "trajectory_type": ttype.value,
            "slope": slope,
            "n_observations": n,
            "h_modifiers": TRAJECTORY_H_MODIFIERS[ttype].copy(),
            "latest_latency": latencies[-1],
            "mean_latency": float(np.mean(latencies)),
        }


def get_click_latency_tracker() -> ClickLatencyTracker:
    """Get a ClickLatencyTracker instance (stateless, no singleton needed)."""
    return ClickLatencyTracker()
