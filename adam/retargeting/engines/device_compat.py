# =============================================================================
# Device-Mechanism Compatibility — Signal 5
# Location: adam/retargeting/engines/device_compat.py
# Enhancement #34: Nonconscious Signal Intelligence Layer, Session 4
# =============================================================================

"""
Maps processing mode (central/peripheral) to mechanism effectiveness
per device type, based on the Elaboration Likelihood Model (Petty &
Cacioppo 1986).

Central route processing (analytical, effortful, argument-quality-dependent)
requires cognitive bandwidth. Peripheral route processing (heuristic,
affect-driven, cue-dependent) does not.

Desktop = higher bandwidth = central route amplified.
Mobile = lower bandwidth = peripheral route amplified.

This signal serves two purposes:
1. DIAGNOSTIC: If a mechanism was served on a mismatched device, boost
   H1 (wrong context) rather than H2 (wrong mechanism). The mechanism
   may be right; the delivery channel was wrong.
2. PRESCRIPTIVE: recommend_device() tells the campaign planner which
   device to target for each mechanism.
"""

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


# =============================================================================
# MECHANISM-DEVICE COMPATIBILITY MATRIX
# =============================================================================

# Values > 1.0: mechanism amplified on this device.
# Values < 1.0: mechanism dampened on this device.
# Derived from ELM processing route × device bandwidth mapping.

MECHANISM_DEVICE_COMPAT: Dict[str, Dict[str, float]] = {
    # Central route mechanisms — desktop amplified
    "evidence_proof":           {"desktop": 1.30, "mobile": 0.70, "tablet": 1.00},
    "claude_argument":          {"desktop": 1.25, "mobile": 0.75, "tablet": 1.00},
    "implementation_intention": {"desktop": 1.30, "mobile": 0.60, "tablet": 0.90},

    # Peripheral route mechanisms — mobile amplified
    "narrative_transportation":  {"desktop": 0.90, "mobile": 1.20, "tablet": 1.10},
    "loss_framing":             {"desktop": 0.90, "mobile": 1.20, "tablet": 1.00},
    "social_proof_matched":     {"desktop": 1.00, "mobile": 1.15, "tablet": 1.05},
    "scarcity_signal":          {"desktop": 0.95, "mobile": 1.20, "tablet": 1.05},

    # Route-independent mechanisms — anchoring and autonomy are automatic
    "price_anchor":             {"desktop": 1.10, "mobile": 1.10, "tablet": 1.10},
    "autonomy_restoration":     {"desktop": 1.00, "mobile": 1.00, "tablet": 1.00},
}

# H1 modifier thresholds
_STRONG_MISMATCH_THRESHOLD = 0.75   # compat < 0.75 → significant mismatch
_MILD_MISMATCH_THRESHOLD = 0.90     # compat < 0.90 → mild mismatch
_STRONG_MISMATCH_H1 = 0.15
_MILD_MISMATCH_H1 = 0.05


# =============================================================================
# DEVICE ENGAGEMENT TRACKER
# =============================================================================

class DeviceEngagementTracker:
    """Stateless engine that computes device-mechanism compatibility
    and recommends optimal device for each mechanism.

    Reads from StoredSignalProfile's device_impressions/device_clicks.
    """

    def recommend_device(
        self,
        mechanism: str,
        device_impressions: Dict[str, int],
        device_clicks: Dict[str, int],
    ) -> Dict[str, Any]:
        """Recommend the optimal device for a mechanism deployment.

        Blends individual device engagement data with the ELM-derived
        mechanism compatibility matrix. When individual data is sufficient
        (>= 3 impressions on a device), individual rate gets 60% weight.

        Args:
            mechanism: Mechanism ID string.
            device_impressions: Per-device impression counts from profile.
            device_clicks: Per-device click counts from profile.

        Returns:
            Dict with recommended_device, scores per device, mechanism.
        """
        compat = MECHANISM_DEVICE_COMPAT.get(mechanism, {})

        scores = {}
        for device in ("desktop", "mobile", "tablet"):
            imps = device_impressions.get(device, 0)
            clicks = device_clicks.get(device, 0)
            mech_score = compat.get(device, 1.0)

            if imps >= 3:
                # Enough individual data: blend individual CTR with compat
                individual_ctr = clicks / imps
                scores[device] = round(individual_ctr * 0.6 + mech_score * 0.4, 4)
            else:
                # Not enough data: use mechanism compatibility alone
                scores[device] = mech_score

        best = max(scores, key=scores.get) if scores else "desktop"

        return {
            "recommended_device": best,
            "scores": scores,
            "mechanism": mechanism,
        }

    def get_h1_modifier(
        self,
        mechanism: str,
        served_device: str,
    ) -> float:
        """Compute H1 modifier for device-mechanism mismatch.

        If the mechanism was served on a device that's poorly matched,
        boost H1 (wrong context) rather than H2 (wrong mechanism).
        The mechanism may be right; the delivery channel was wrong.

        Args:
            mechanism: Mechanism ID string.
            served_device: Device type the ad was served on.

        Returns:
            H1 modifier (0.0, 0.05, or 0.15).
        """
        compat = MECHANISM_DEVICE_COMPAT.get(mechanism, {}).get(served_device, 1.0)

        if compat < _STRONG_MISMATCH_THRESHOLD:
            return _STRONG_MISMATCH_H1
        elif compat < _MILD_MISMATCH_THRESHOLD:
            return _MILD_MISMATCH_H1
        return 0.0

    def is_mismatched(self, mechanism: str, served_device: str) -> bool:
        """Quick check: is this mechanism poorly matched to this device?"""
        compat = MECHANISM_DEVICE_COMPAT.get(mechanism, {}).get(served_device, 1.0)
        return compat < _MILD_MISMATCH_THRESHOLD


def get_device_tracker() -> DeviceEngagementTracker:
    """Get a DeviceEngagementTracker instance (stateless)."""
    return DeviceEngagementTracker()
