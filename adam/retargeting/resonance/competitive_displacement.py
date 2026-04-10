# =============================================================================
# Competitive Displacement Detector
# Location: adam/retargeting/resonance/competitive_displacement.py
# =============================================================================

"""
Detects and responds to competitive advertising environments that
affect our signal's effectiveness.

When competing ads are on the same page, they create their own priming
effects that can cancel, redirect, or amplify our signal. A page
saturated with urgency-based ads will fatigue the scarcity channel,
making our scarcity mechanism less effective.

Signals consumed:
- ad_slot_count (from page DOM analysis or bid-stream signals)
- category_ad_density (from bid-stream: how many competitors bid on this page)
- competing_mechanisms (inferred from competitor creative analysis)

Outputs:
- mechanism_fatigue: {mechanism: fatigue_score} — channels already saturated
- open_channels: mechanisms with no competitive presence (opportunity)
- displacement_risk: float — overall competitive pressure on this page
- recommended_adjustment: per-mechanism bid adjustment

Integration:
- Fed to PlacementOptimizer to adjust bids based on competitive environment
- Fed to MechanismActivationAtom to avoid fatigued channels
- Fed to CreativeAdapter to differentiate against competitors
"""

import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


# Mechanism saturation thresholds
# (above this ad density for a mechanism, fatigue kicks in)
_SATURATION_THRESHOLD = 3  # 3+ competitors using same mechanism = saturated


@dataclass
class CompetitiveEnvironment:
    """Competitive advertising state for a page or domain."""

    domain: str
    ad_slot_count: int = 0
    category_ad_density: float = 0.0  # 0-1 scale
    competing_mechanisms: Dict[str, int] = field(default_factory=dict)  # mechanism → count

    # Derived
    mechanism_fatigue: Dict[str, float] = field(default_factory=dict)  # mechanism → 0-1
    open_channels: List[str] = field(default_factory=list)
    displacement_risk: float = 0.0
    recommended_adjustments: Dict[str, float] = field(default_factory=dict)

    updated_at: float = field(default_factory=time.time)


class CompetitiveDisplacementDetector:
    """Tracks and responds to competitive environments.

    Maintains per-domain competitive state from bid-stream and
    page intelligence signals. Updates on each impression.
    """

    # All mechanisms we track
    ALL_MECHANISMS = {
        "authority", "social_proof", "scarcity", "loss_aversion",
        "commitment", "liking", "reciprocity", "unity",
        "curiosity", "cognitive_ease", "storytelling",
        "evidence_proof", "narrative_transportation",
        "anxiety_resolution", "loss_framing",
    }

    def __init__(self):
        self._environments: Dict[str, CompetitiveEnvironment] = {}
        self._domain_history: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

    def update_from_impression(
        self,
        domain: str,
        ad_slot_count: int = 0,
        category_ad_density: float = 0.0,
        competing_creative_signals: Optional[Dict[str, Any]] = None,
    ) -> CompetitiveEnvironment:
        """Update competitive environment from an impression event.

        Args:
            domain: Page domain
            ad_slot_count: Number of ad slots on the page (from DOM or bid-stream)
            category_ad_density: Fraction of bid-stream targeting this page (0-1)
            competing_creative_signals: Inferred competitor mechanisms from
                creative analysis (if available from bid-stream)
        """
        env = self._environments.get(domain)
        if env is None:
            env = CompetitiveEnvironment(domain=domain)
            self._environments[env.domain] = env

        env.ad_slot_count = ad_slot_count
        env.category_ad_density = category_ad_density
        env.updated_at = time.time()

        # Update competing mechanisms from signals
        if competing_creative_signals:
            detected_mechs = competing_creative_signals.get("mechanisms_detected", {})
            for mech, count in detected_mechs.items():
                env.competing_mechanisms[mech] = count

        # Compute derived state
        self._compute_fatigue(env)
        self._compute_displacement_risk(env)
        self._compute_adjustments(env)

        # Record history for trend detection
        self._domain_history[domain].append({
            "timestamp": env.updated_at,
            "ad_density": category_ad_density,
            "slot_count": ad_slot_count,
        })
        # Cap history
        if len(self._domain_history[domain]) > 100:
            self._domain_history[domain] = self._domain_history[domain][-100:]

        return env

    def get_environment(self, domain: str) -> Optional[CompetitiveEnvironment]:
        """Get competitive environment for a domain."""
        env = self._environments.get(domain)
        if env and time.time() - env.updated_at > 3600:
            return None  # Stale (>1hr)
        return env

    def get_mechanism_adjustment(
        self,
        domain: str,
        mechanism: str,
    ) -> float:
        """Get bid/score adjustment for a mechanism on a domain.

        Returns: multiplier (1.0 = no change, <1.0 = reduce, >1.0 = boost)
        """
        env = self._environments.get(domain)
        if not env:
            return 1.0
        return env.recommended_adjustments.get(mechanism, 1.0)

    def get_open_channels(self, domain: str) -> List[str]:
        """Get mechanisms with no competitive presence on this domain.

        These are OPPORTUNITY channels — deploying a mechanism no
        competitor uses means zero fatigue and maximum distinctiveness.
        """
        env = self._environments.get(domain)
        if not env:
            return list(self.ALL_MECHANISMS)
        return env.open_channels

    def _compute_fatigue(self, env: CompetitiveEnvironment) -> None:
        """Compute mechanism fatigue from competitive presence."""
        env.mechanism_fatigue = {}
        occupied_mechs: Set[str] = set()

        for mech, count in env.competing_mechanisms.items():
            if count >= _SATURATION_THRESHOLD:
                env.mechanism_fatigue[mech] = min(1.0, count / 5.0)
                occupied_mechs.add(mech)
            elif count > 0:
                env.mechanism_fatigue[mech] = count / (_SATURATION_THRESHOLD * 2)
                occupied_mechs.add(mech)

        # Open channels = mechanisms with zero competitive presence
        env.open_channels = [
            m for m in self.ALL_MECHANISMS if m not in occupied_mechs
        ]

    def _compute_displacement_risk(self, env: CompetitiveEnvironment) -> None:
        """Compute overall competitive displacement risk."""
        # Higher with more ad slots, higher ad density, more fatigued mechanisms
        slot_risk = min(1.0, env.ad_slot_count / 10.0) * 0.3
        density_risk = env.category_ad_density * 0.4
        fatigue_risk = (
            sum(env.mechanism_fatigue.values()) / max(len(env.mechanism_fatigue), 1)
            if env.mechanism_fatigue else 0.0
        ) * 0.3

        env.displacement_risk = slot_risk + density_risk + fatigue_risk

    def _compute_adjustments(self, env: CompetitiveEnvironment) -> None:
        """Compute per-mechanism bid/score adjustments.

        Fatigued mechanisms get reduced. Open channels get boosted.
        """
        env.recommended_adjustments = {}

        for mech in self.ALL_MECHANISMS:
            if mech in env.mechanism_fatigue:
                fatigue = env.mechanism_fatigue[mech]
                # Reduce bid proportionally to fatigue
                env.recommended_adjustments[mech] = max(0.5, 1.0 - fatigue * 0.5)
            elif mech in env.open_channels:
                # Boost open channels — opportunity to differentiate
                env.recommended_adjustments[mech] = min(1.3, 1.0 + env.displacement_risk * 0.3)
            else:
                env.recommended_adjustments[mech] = 1.0

    def get_trend(self, domain: str) -> Optional[str]:
        """Detect competitive density trend for a domain.

        Returns: "increasing", "decreasing", "stable", or None
        """
        history = self._domain_history.get(domain, [])
        if len(history) < 5:
            return None

        recent = [h["ad_density"] for h in history[-5:]]
        older = [h["ad_density"] for h in history[-10:-5]] if len(history) >= 10 else recent

        avg_recent = sum(recent) / len(recent)
        avg_older = sum(older) / len(older)

        if avg_recent > avg_older * 1.2:
            return "increasing"
        elif avg_recent < avg_older * 0.8:
            return "decreasing"
        return "stable"

    @property
    def stats(self) -> Dict[str, Any]:
        return {
            "domains_tracked": len(self._environments),
            "avg_displacement_risk": (
                sum(e.displacement_risk for e in self._environments.values())
                / max(len(self._environments), 1)
            ),
            "avg_open_channels": (
                sum(len(e.open_channels) for e in self._environments.values())
                / max(len(self._environments), 1)
            ),
        }


# =============================================================================
# SINGLETON
# =============================================================================

_detector: Optional[CompetitiveDisplacementDetector] = None


def get_competitive_detector() -> CompetitiveDisplacementDetector:
    global _detector
    if _detector is None:
        _detector = CompetitiveDisplacementDetector()
    return _detector
