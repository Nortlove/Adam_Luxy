"""
Mechanism ADME Profiles — Pharmacokinetic Models for Persuasion
================================================================

Each persuasion mechanism has absorption, distribution, metabolism,
and excretion kinetics — just like a drug. These profiles determine:

- How QUICKLY the mechanism takes effect (absorption)
- How BROADLY it shifts psychological state (distribution)
- How FAST the effect decays (metabolism / half-life)
- When the effect is fully gone (excretion)

This directly controls RETARGETING TIMING:
- After authority (slow metabolism, t½=10d): wait 7 days before next touch
- After scarcity (fast metabolism, t½=4h): follow up within 24 hours
- After cognitive ease (medium, t½=2d): follow up in 2-3 days

And CREATIVE SELECTION:
- On high-capacity channels (CTV, deep processing): deploy slow-absorption
  mechanisms that require central-route processing (authority, commitment)
- On low-capacity channels (mobile, peripheral): deploy fast-absorption
  mechanisms that work on peripheral route (cognitive ease, social proof)

Grounded in Petty & Cacioppo's ELM + Chris Nocera's pharmacodynamic
modeling background.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class ADMEProfile:
    """Pharmacokinetic profile for a persuasion mechanism."""
    mechanism: str

    # Absorption: how quickly does the message register?
    # 0-1 scale. 1.0 = instant (peripheral route). 0.2 = slow (requires deep processing)
    absorption_rate: float

    # Processing route required
    # "central" = needs argument comprehension (>2s processing depth)
    # "peripheral" = works on heuristic cues (<2s sufficient)
    # "dual" = works on both but through different pathways
    processing_route: str

    # Minimum channel capacity (processing depth in seconds) for effectiveness
    min_channel_capacity: float

    # Distribution: how many psychological dimensions does it shift?
    # Wider distribution = more secondary effects through BONG covariance
    distribution_width: int  # number of dimensions meaningfully affected

    # Primary dimensions affected
    primary_dimensions: List[str]

    # Metabolism: half-life in hours
    # How long until the effect is at 50% strength
    half_life_hours: float

    # Excretion: total effective duration in hours
    # After this, the effect is negligible (<5% of peak)
    total_duration_hours: float

    # Optimal retargeting delay: when to deploy the NEXT touch
    # Based on metabolism — deploy next mechanism when current is at ~30% strength
    optimal_next_touch_hours: float

    # Reactance accumulation rate: how quickly does repeated exposure
    # trigger persuasion knowledge? Higher = faster reactance buildup
    reactance_rate: float

    # Max effective exposures before reactance dominates
    max_exposures: int

    def effect_at_time(self, hours_since_exposure: float) -> float:
        """Calculate remaining effect strength at a given time."""
        if hours_since_exposure <= 0:
            return 1.0
        decay = math.exp(-0.693 * hours_since_exposure / self.half_life_hours)
        return max(0.0, decay)

    def is_effective_on_channel(self, processing_depth_seconds: float) -> bool:
        """Can this mechanism work on a channel with this processing depth?"""
        return processing_depth_seconds >= self.min_channel_capacity

    def reactance_at_exposure(self, exposure_count: int) -> float:
        """Cumulative reactance after N exposures of this mechanism."""
        if exposure_count <= 1:
            return 0.0
        return min(1.0, self.reactance_rate * (exposure_count - 1))


# ════════════════════════════════════════════════════════════
# ADME Profiles per Mechanism (from bilateral evidence + theory)
# ════════════════════════════════════════════════════════════

MECHANISM_PROFILES: Dict[str, ADMEProfile] = {
    "authority": ADMEProfile(
        mechanism="authority",
        absorption_rate=0.3,
        processing_route="central",
        min_channel_capacity=2.0,
        distribution_width=5,
        primary_dimensions=["brand_relationship_depth", "regulatory_fit",
                           "persuasion_susceptibility", "value_alignment",
                           "construal_fit"],
        half_life_hours=240,       # 10 days — authority effects persist
        total_duration_hours=720,  # 30 days
        optimal_next_touch_hours=168,  # 7 days
        reactance_rate=0.15,
        max_exposures=4,
    ),
    "social_proof": ADMEProfile(
        mechanism="social_proof",
        absorption_rate=0.7,
        processing_route="dual",
        min_channel_capacity=1.0,
        distribution_width=4,
        primary_dimensions=["social_proof_sensitivity", "mimetic_desire",
                           "personality_alignment", "value_alignment"],
        half_life_hours=72,        # 3 days
        total_duration_hours=240,  # 10 days
        optimal_next_touch_hours=72,   # 3 days
        reactance_rate=0.10,
        max_exposures=5,
    ),
    "cognitive_ease": ADMEProfile(
        mechanism="cognitive_ease",
        absorption_rate=0.9,
        processing_route="peripheral",
        min_channel_capacity=0.5,
        distribution_width=2,
        primary_dimensions=["cognitive_load_tolerance", "decision_entropy"],
        half_life_hours=48,        # 2 days
        total_duration_hours=168,  # 7 days
        optimal_next_touch_hours=48,   # 2 days
        reactance_rate=0.05,
        max_exposures=8,
    ),
    "scarcity": ADMEProfile(
        mechanism="scarcity",
        absorption_rate=0.95,
        processing_route="peripheral",
        min_channel_capacity=0.3,
        distribution_width=2,
        primary_dimensions=["loss_aversion_intensity", "temporal_discounting"],
        half_life_hours=4,         # 4 hours — urgency decays fast
        total_duration_hours=24,   # 1 day
        optimal_next_touch_hours=12,   # 12 hours
        reactance_rate=0.30,
        max_exposures=2,
    ),
    "commitment": ADMEProfile(
        mechanism="commitment",
        absorption_rate=0.25,
        processing_route="central",
        min_channel_capacity=2.5,
        distribution_width=4,
        primary_dimensions=["brand_relationship_depth", "value_alignment",
                           "cooperative_framing_fit", "regulatory_fit"],
        half_life_hours=336,       # 14 days — commitment is durable
        total_duration_hours=1008, # 42 days
        optimal_next_touch_hours=168,  # 7 days
        reactance_rate=0.08,
        max_exposures=6,
    ),
    "liking": ADMEProfile(
        mechanism="liking",
        absorption_rate=0.8,
        processing_route="peripheral",
        min_channel_capacity=0.5,
        distribution_width=3,
        primary_dimensions=["emotional_resonance", "personality_alignment",
                           "interoceptive_awareness"],
        half_life_hours=48,        # 2 days
        total_duration_hours=168,  # 7 days
        optimal_next_touch_hours=48,   # 2 days
        reactance_rate=0.08,
        max_exposures=6,
    ),
    "curiosity": ADMEProfile(
        mechanism="curiosity",
        absorption_rate=0.85,
        processing_route="dual",
        min_channel_capacity=0.8,
        distribution_width=3,
        primary_dimensions=["information_seeking", "narrative_transport",
                           "cognitive_load_tolerance"],
        half_life_hours=24,        # 1 day — curiosity fades fast if unfulfilled
        total_duration_hours=72,   # 3 days
        optimal_next_touch_hours=24,   # 1 day
        reactance_rate=0.12,
        max_exposures=3,
    ),
    "reciprocity": ADMEProfile(
        mechanism="reciprocity",
        absorption_rate=0.4,
        processing_route="central",
        min_channel_capacity=1.5,
        distribution_width=3,
        primary_dimensions=["cooperative_framing_fit", "value_alignment",
                           "personality_alignment"],
        half_life_hours=168,       # 7 days
        total_duration_hours=504,  # 21 days
        optimal_next_touch_hours=120,  # 5 days
        reactance_rate=0.12,
        max_exposures=4,
    ),
    "loss_aversion": ADMEProfile(
        mechanism="loss_aversion",
        absorption_rate=0.75,
        processing_route="dual",
        min_channel_capacity=1.0,
        distribution_width=3,
        primary_dimensions=["loss_aversion_intensity", "regulatory_fit",
                           "emotional_resonance"],
        half_life_hours=12,        # 12 hours — loss feeling fades
        total_duration_hours=48,   # 2 days
        optimal_next_touch_hours=24,   # 1 day
        reactance_rate=0.25,
        max_exposures=3,
    ),
    "unity": ADMEProfile(
        mechanism="unity",
        absorption_rate=0.6,
        processing_route="dual",
        min_channel_capacity=1.0,
        distribution_width=4,
        primary_dimensions=["mimetic_desire", "social_proof_sensitivity",
                           "value_alignment", "cooperative_framing_fit"],
        half_life_hours=120,       # 5 days
        total_duration_hours=360,  # 15 days
        optimal_next_touch_hours=96,   # 4 days
        reactance_rate=0.10,
        max_exposures=5,
    ),
}


def get_adme_profile(mechanism: str) -> Optional[ADMEProfile]:
    """Get the ADME profile for a mechanism."""
    return MECHANISM_PROFILES.get(mechanism)


def get_optimal_retargeting_delay(mechanism: str) -> float:
    """Get optimal hours before next retargeting touch."""
    profile = MECHANISM_PROFILES.get(mechanism)
    return profile.optimal_next_touch_hours if profile else 72.0


def get_channel_compatible_mechanisms(
    processing_depth_seconds: float,
) -> List[str]:
    """Get mechanisms that can work at this processing depth."""
    compatible = []
    for name, profile in MECHANISM_PROFILES.items():
        if profile.is_effective_on_channel(processing_depth_seconds):
            compatible.append(name)
    return compatible


def select_mechanism_for_channel(
    archetype_scores: Dict[str, float],
    processing_depth: float,
    exposure_counts: Optional[Dict[str, int]] = None,
) -> Tuple[str, str]:
    """Select the best mechanism given channel capacity constraints.

    Returns (mechanism, reasoning).
    """
    exposure_counts = exposure_counts or {}
    compatible = get_channel_compatible_mechanisms(processing_depth)

    if not compatible:
        return "cognitive_ease", "No mechanism fits this channel capacity"

    # Score each compatible mechanism
    best = None
    best_score = -1.0
    reasoning_parts = []

    for mech in compatible:
        profile = MECHANISM_PROFILES[mech]
        base_score = archetype_scores.get(mech, 0.5)

        # Penalize for reactance from prior exposures
        exposure = exposure_counts.get(mech, 0)
        reactance_penalty = profile.reactance_at_exposure(exposure)
        if exposure >= profile.max_exposures:
            reasoning_parts.append(
                f"{mech}: SUPPRESSED (exposure {exposure} >= max {profile.max_exposures})"
            )
            continue

        effective_score = base_score * (1 - reactance_penalty)

        if effective_score > best_score:
            best_score = effective_score
            best = mech

    if best is None:
        return "cognitive_ease", "All mechanisms exhausted; defaulting to lowest-reactance option"

    profile = MECHANISM_PROFILES[best]
    reasoning = (
        f"Selected {best} (score={best_score:.3f}, "
        f"route={profile.processing_route}, "
        f"t½={profile.half_life_hours}h, "
        f"next_touch={profile.optimal_next_touch_hours}h)"
    )

    return best, reasoning


def compute_retargeting_sequence(
    archetype_scores: Dict[str, float],
    channel_capacity: float = 2.0,
    max_touches: int = 3,
) -> List[Dict]:
    """Compute the optimal retargeting sequence with ADME-informed timing.

    Returns a list of touches, each with mechanism, delay, and reasoning.
    """
    sequence = []
    exposure_counts: Dict[str, int] = {}
    cumulative_hours = 0.0

    for touch_num in range(1, max_touches + 1):
        mechanism, reasoning = select_mechanism_for_channel(
            archetype_scores, channel_capacity, exposure_counts
        )
        profile = MECHANISM_PROFILES.get(mechanism)
        if not profile:
            break

        delay = profile.optimal_next_touch_hours if touch_num > 1 else 0

        sequence.append({
            "touch": touch_num,
            "mechanism": mechanism,
            "delay_hours": delay,
            "cumulative_hours": cumulative_hours + delay,
            "half_life_hours": profile.half_life_hours,
            "processing_route": profile.processing_route,
            "max_exposures_remaining": profile.max_exposures - exposure_counts.get(mechanism, 0),
            "reasoning": reasoning,
        })

        exposure_counts[mechanism] = exposure_counts.get(mechanism, 0) + 1
        cumulative_hours += delay

    return sequence
