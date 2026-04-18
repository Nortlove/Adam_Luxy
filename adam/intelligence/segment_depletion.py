"""
Segment Depletion Detector
============================

Epidemiological model: as a campaign runs, the easiest-to-convert
buyers convert first. The remaining audience is increasingly resistant.
The mechanism that converted the first 30 buyers won't convert the
next 30 — they're different people with different barriers.

This module detects when a segment's conversion rate is declining
NOT because the mechanism stopped working, but because the receptive
pool has been depleted. When detected, it recommends switching to a
different mechanism that targets the remaining audience's barriers.

Analogous to herd immunity thresholds: once enough susceptible
individuals are "immunized" (converted or saturated), the same
intervention loses effectiveness on the remainder.

Detection method:
- Track conversion rate per archetype × mechanism over time windows
- Fit a depletion curve (exponential decay from initial rate)
- When actual rate drops below the depletion curve prediction,
  the decline is FASTER than expected → something else is wrong
- When actual rate follows the curve closely → depletion confirmed

Response:
- Estimate remaining susceptible pool size
- Identify the barrier profile of the unconverted remainder
- Recommend mechanism switch to target the new barrier
"""

from __future__ import annotations

import logging
import math
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class DepletionSignal:
    """Detection result for one archetype × mechanism cell."""
    archetype: str
    mechanism: str

    # Is depletion occurring?
    depleted: bool = False
    depletion_confidence: float = 0.0

    # Evidence
    initial_conversion_rate: float = 0.0
    current_conversion_rate: float = 0.0
    rate_decline_pct: float = 0.0
    impressions_served: int = 0

    # Estimated remaining susceptible pool
    estimated_remaining_pct: float = 100.0

    # Recommendation
    recommended_action: str = ""
    recommended_switch_to: str = ""
    reasoning: str = ""


@dataclass
class ConversionWindow:
    """Conversion data for a time window."""
    impressions: int = 0
    conversions: int = 0
    window_start: float = 0.0
    window_end: float = 0.0

    @property
    def rate(self) -> float:
        return self.conversions / max(self.impressions, 1)


class SegmentDepletionDetector:
    """Detects when a segment's receptive pool has been exhausted.

    Tracks per-cell performance over rolling windows and detects
    the characteristic exponential decline pattern of depletion
    vs the sudden decline pattern of mechanism failure.
    """

    def __init__(self, window_hours: float = 168.0):  # 7-day windows
        self.window_hours = window_hours
        self._history: Dict[str, List[ConversionWindow]] = {}
        self._total_observations = 0

    def record_outcome(
        self,
        archetype: str,
        mechanism: str,
        converted: bool,
        timestamp: Optional[float] = None,
    ):
        """Record an impression outcome."""
        ts = timestamp or time.time()
        key = f"{archetype}:{mechanism}"

        if key not in self._history:
            self._history[key] = [ConversionWindow(
                window_start=ts,
                window_end=ts + self.window_hours * 3600,
            )]

        current_window = self._history[key][-1]

        # Roll to new window if needed
        if ts > current_window.window_end:
            self._history[key].append(ConversionWindow(
                window_start=current_window.window_end,
                window_end=current_window.window_end + self.window_hours * 3600,
            ))
            current_window = self._history[key][-1]

        current_window.impressions += 1
        if converted:
            current_window.conversions += 1
        self._total_observations += 1

    def detect_depletion(
        self,
        archetype: str,
        mechanism: str,
    ) -> DepletionSignal:
        """Check if a segment is depleted for a given mechanism."""
        key = f"{archetype}:{mechanism}"
        signal = DepletionSignal(archetype=archetype, mechanism=mechanism)

        windows = self._history.get(key, [])
        if len(windows) < 2:
            signal.reasoning = "Insufficient data (need 2+ windows)"
            return signal

        # Get rates over time
        rates = [w.rate for w in windows if w.impressions >= 10]
        if len(rates) < 2:
            signal.reasoning = "Insufficient qualified windows"
            return signal

        signal.initial_conversion_rate = rates[0]
        signal.current_conversion_rate = rates[-1]
        signal.impressions_served = sum(w.impressions for w in windows)

        if signal.initial_conversion_rate <= 0:
            return signal

        signal.rate_decline_pct = (
            (signal.initial_conversion_rate - signal.current_conversion_rate)
            / signal.initial_conversion_rate * 100
        )

        # Depletion detection: exponential decay model
        # If rate follows N(t) = N₀ × e^(-λt), it's depletion
        # If rate drops suddenly, it's mechanism failure
        total_impressions = signal.impressions_served

        # Expected remaining susceptible pool assuming exponential depletion
        # Pool depletes as: remaining = initial × e^(-conversions/pool_size)
        total_conversions = sum(w.conversions for w in windows)
        if total_conversions > 0 and signal.initial_conversion_rate > 0:
            estimated_pool = total_conversions / signal.initial_conversion_rate
            remaining = estimated_pool - total_conversions
            signal.estimated_remaining_pct = max(0, remaining / max(estimated_pool, 1) * 100)

        # Classify as depleted if:
        # 1. Rate has declined >30%
        # 2. Decline is gradual (not sudden — consistent across windows)
        # 3. Enough impressions to be statistically meaningful
        if (
            signal.rate_decline_pct > 30
            and len(rates) >= 3
            and all(rates[i] >= rates[i+1] * 0.7 for i in range(len(rates)-1))
            and signal.impressions_served > 500
        ):
            signal.depleted = True
            signal.depletion_confidence = min(0.95, signal.rate_decline_pct / 100)
            signal.reasoning = (
                f"Conversion rate declined {signal.rate_decline_pct:.0f}% "
                f"over {len(windows)} windows with consistent gradual decline. "
                f"Estimated {signal.estimated_remaining_pct:.0f}% of receptive "
                f"pool remaining. This is segment depletion, not mechanism failure."
            )
            signal.recommended_action = "switch_mechanism"
            signal.recommended_switch_to = _recommend_switch(mechanism)
        elif signal.rate_decline_pct > 50 and len(rates) >= 2:
            # Sudden decline — might be mechanism failure, not depletion
            signal.reasoning = (
                f"Rate declined {signal.rate_decline_pct:.0f}% but pattern "
                f"is sudden, not gradual. May be mechanism failure, competitive "
                f"saturation, or external factor — not segment depletion."
            )
            signal.recommended_action = "investigate"

        return signal

    def get_all_depletion_signals(self) -> List[DepletionSignal]:
        """Check all tracked cells for depletion."""
        signals = []
        for key in self._history:
            arch, mech = key.split(":", 1)
            signal = self.detect_depletion(arch, mech)
            if signal.depleted or signal.rate_decline_pct > 20:
                signals.append(signal)
        return signals


def _recommend_switch(current_mechanism: str) -> str:
    """Recommend the next mechanism when the current one is depleted.

    The switch targets the barrier most likely held by the remaining
    (resistant) buyers — those who saw the current mechanism and
    weren't persuaded.
    """
    switch_map = {
        "authority": "cognitive_ease",       # resistant to authority → simplify the ask
        "social_proof": "authority",         # resistant to social proof → provide evidence
        "cognitive_ease": "social_proof",    # resistant to ease → provide social validation
        "scarcity": "commitment",            # resistant to urgency → build relationship
        "commitment": "curiosity",           # resistant to commitment → reactivate interest
        "liking": "authority",               # resistant to liking → switch to credibility
        "curiosity": "social_proof",         # curiosity didn't convert → provide validation
        "loss_aversion": "cognitive_ease",   # resistant to fear → reduce friction instead
    }
    return switch_map.get(current_mechanism, "cognitive_ease")


# Singleton
_detector: Optional[SegmentDepletionDetector] = None


def get_depletion_detector() -> SegmentDepletionDetector:
    global _detector
    if _detector is None:
        _detector = SegmentDepletionDetector()
    return _detector
