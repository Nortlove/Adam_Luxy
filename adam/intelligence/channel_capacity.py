"""
Channel Capacity × Message Complexity Matching
=================================================

Shannon's channel capacity theorem applied to advertising:
each impression is a communication channel with limited capacity.
The message complexity must match the channel capacity.

High capacity (CTV 15-30s, desktop with deep processing):
→ Deploy COMPLEX messages requiring central-route processing
→ Authority arguments, evidence chains, commitment sequences

Low capacity (mobile banner, sub-second attention):
→ Deploy SIMPLE messages working on peripheral route
→ Cognitive ease, social proof heuristics, liking cues

This is Petty & Cacioppo's ELM operationalized at the channel level.

Also generates strategic experiment variants:
- Control variant (null mechanism) — baseline for theory validation
- Inverse variant (predicted loser) — falsification test
- Superposition variant (multi-mechanism) — covers multiple routes
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from adam.intelligence.mechanism_adme import (
    MECHANISM_PROFILES,
    get_channel_compatible_mechanisms,
)

logger = logging.getLogger(__name__)


@dataclass
class ChannelProfile:
    """Profile of an ad channel's capacity."""
    channel_type: str  # "ctv", "display_desktop", "display_mobile", "native"
    avg_processing_depth: float  # seconds
    capacity_level: str  # "high", "medium", "low"
    max_message_complexity: str  # "complex", "moderate", "simple"
    compatible_routes: List[str]  # ["central", "peripheral", "dual"]


CHANNEL_PROFILES = {
    "ctv": ChannelProfile(
        channel_type="ctv",
        avg_processing_depth=20.0,
        capacity_level="high",
        max_message_complexity="complex",
        compatible_routes=["central", "peripheral", "dual"],
    ),
    "display_desktop": ChannelProfile(
        channel_type="display_desktop",
        avg_processing_depth=2.5,
        capacity_level="medium",
        max_message_complexity="moderate",
        compatible_routes=["central", "peripheral", "dual"],
    ),
    "display_mobile": ChannelProfile(
        channel_type="display_mobile",
        avg_processing_depth=1.2,
        capacity_level="low",
        max_message_complexity="simple",
        compatible_routes=["peripheral", "dual"],
    ),
    "native_desktop": ChannelProfile(
        channel_type="native_desktop",
        avg_processing_depth=3.0,
        capacity_level="medium",
        max_message_complexity="moderate",
        compatible_routes=["central", "peripheral", "dual"],
    ),
    "native_mobile": ChannelProfile(
        channel_type="native_mobile",
        avg_processing_depth=1.5,
        capacity_level="low",
        max_message_complexity="simple",
        compatible_routes=["peripheral", "dual"],
    ),
}


# Message complexity requirements per mechanism
MECHANISM_COMPLEXITY = {
    "authority": "complex",       # Needs argument comprehension
    "commitment": "complex",      # Needs deliberation
    "reciprocity": "complex",     # Needs perceived exchange evaluation
    "social_proof": "simple",     # Heuristic: "others do it"
    "cognitive_ease": "simple",   # Heuristic: "it's easy"
    "liking": "simple",           # Heuristic: "I like this"
    "scarcity": "simple",         # Heuristic: "act now"
    "curiosity": "moderate",      # Needs some engagement but not deep
    "loss_aversion": "moderate",  # Needs scenario imagination
    "unity": "moderate",          # Needs identity recognition
}

COMPLEXITY_ORDER = {"simple": 1, "moderate": 2, "complex": 3}


def get_channel_matched_mechanisms(
    channel_type: str,
    archetype_scores: Dict[str, float],
) -> List[Tuple[str, float, str]]:
    """Get mechanisms that match this channel's capacity, ranked by score.

    Returns list of (mechanism, adjusted_score, reasoning).
    """
    channel = CHANNEL_PROFILES.get(channel_type)
    if not channel:
        channel = CHANNEL_PROFILES["display_desktop"]

    max_complexity = COMPLEXITY_ORDER.get(channel.max_message_complexity, 2)
    results = []

    for mech, score in sorted(archetype_scores.items(), key=lambda x: x[1], reverse=True):
        mech_complexity = MECHANISM_COMPLEXITY.get(mech, "moderate")
        mech_level = COMPLEXITY_ORDER.get(mech_complexity, 2)

        profile = MECHANISM_PROFILES.get(mech)
        route = profile.processing_route if profile else "dual"

        if mech_level <= max_complexity and route in channel.compatible_routes:
            results.append((
                mech, score,
                f"{mech} ({mech_complexity}) fits {channel_type} ({channel.capacity_level} capacity)"
            ))
        else:
            # Penalize but don't exclude — StackAdapt may override
            penalty = 0.3 * (mech_level - max_complexity)
            adjusted = max(0.0, score - penalty)
            if adjusted > 0.2:
                results.append((
                    mech, adjusted,
                    f"{mech} ({mech_complexity}) PENALIZED on {channel_type}: "
                    f"requires {route} route, channel may not support"
                ))

    results.sort(key=lambda x: x[1], reverse=True)
    return results


@dataclass
class ExperimentVariant:
    """A creative variant for a designed experiment."""
    name: str
    role: str  # "treatment", "control", "inverse", "superposition"
    mechanism: str
    headline: str
    body: str
    cta: str
    hypothesis: str


def design_experiment_variants(
    archetype: str,
    predicted_winner: str,
    predicted_loser: str,
    archetype_scores: Dict[str, float],
) -> List[ExperimentVariant]:
    """Design a set of creative variants that turns StackAdapt's
    A/B optimization into a controlled scientific experiment.

    Includes:
    - Treatment: the predicted winner (validates our theory)
    - Control: generic copy with no specific mechanism (baseline)
    - Inverse: the predicted loser (falsification test)
    - Superposition: multi-mechanism creative (tests whether
      combined approaches outperform single mechanisms)
    """
    variants = []

    # 1. Treatment — the predicted winner
    variants.append(ExperimentVariant(
        name=f"{archetype}-Treatment-{predicted_winner}",
        role="treatment",
        mechanism=predicted_winner,
        headline=_get_mechanism_headline(predicted_winner),
        body=_get_mechanism_body(predicted_winner),
        cta=_get_mechanism_cta(predicted_winner),
        hypothesis=(
            f"INFORMATIV predicts {predicted_winner} is optimal for "
            f"{archetype} (score={archetype_scores.get(predicted_winner, 0):.3f})"
        ),
    ))

    # 2. Control — no specific mechanism (null hypothesis baseline)
    variants.append(ExperimentVariant(
        name=f"{archetype}-Control",
        role="control",
        mechanism="none",
        headline="Premium ground transportation",
        body="Professional car service for any occasion. Book online.",
        cta="Learn more",
        hypothesis="Baseline: generic copy with no psychological mechanism",
    ))

    # 3. Inverse — the predicted loser (falsification)
    variants.append(ExperimentVariant(
        name=f"{archetype}-Inverse-{predicted_loser}",
        role="inverse",
        mechanism=predicted_loser,
        headline=_get_mechanism_headline(predicted_loser),
        body=_get_mechanism_body(predicted_loser),
        cta=_get_mechanism_cta(predicted_loser),
        hypothesis=(
            f"Theory predicts {predicted_loser} should UNDERPERFORM for "
            f"{archetype}. If it wins, our model needs revision."
        ),
    ))

    # 4. Superposition — multi-mechanism creative
    top3 = sorted(archetype_scores.items(), key=lambda x: x[1], reverse=True)[:3]
    top3_names = [m for m, _ in top3]
    variants.append(ExperimentVariant(
        name=f"{archetype}-Superposition",
        role="superposition",
        mechanism="multi",
        headline=_get_superposition_headline(top3_names),
        body=_get_superposition_body(top3_names),
        cta="Experience the difference",
        hypothesis=(
            f"Tests whether combining {'+'.join(top3_names)} outperforms "
            f"single-mechanism variants. If yes, buyer psychology is more "
            f"heterogeneous than our archetype model assumes."
        ),
    ))

    return variants


# ════════════════════════════════════════════════════════════
# Creative templates per mechanism
# ════════════════════════════════════════════════════════════

def _get_mechanism_headline(mechanism: str) -> str:
    headlines = {
        "authority": "The executive standard in ground transportation",
        "social_proof": "10,000+ professionals trust LUXY",
        "cognitive_ease": "Premium transport. One tap.",
        "scarcity": "Limited fleet. Unlimited impression.",
        "commitment": "Your company deserves better than rideshare",
        "liking": "Make every ride unforgettable",
        "curiosity": "What luxury transport is actually like",
        "loss_aversion": "Don't risk unreliable transport for your next trip",
        "reciprocity": "We invest in your experience. You'll see why.",
        "unity": "Join the professionals who refuse to compromise",
    }
    return headlines.get(mechanism, "Premium ground transportation")


def _get_mechanism_body(mechanism: str) -> str:
    bodies = {
        "authority": "Trusted by Fortune 500 travel managers. On-time guarantee backed by real-time flight tracking.",
        "social_proof": "Join the professionals who demand reliability and discretion in every ride.",
        "cognitive_ease": "No surge pricing. No uncertainty. Just seamless professional transportation.",
        "scarcity": "Our curated fleet is reserved for those who expect excellence.",
        "commitment": "Dedicated account management. Volume pricing. Duty of care compliance.",
        "liking": "Every detail designed around your comfort. Because the ride matters too.",
        "curiosity": "No stiffness. No pretension. Just a better way to move.",
        "loss_aversion": "Surge pricing. Unreliable drivers. Unprofessional vehicles. Why risk it?",
        "reciprocity": "Free waiting time. Flight tracking. Complimentary water. We give first.",
        "unity": "The professionals who move markets don't leave ground transport to chance.",
    }
    return bodies.get(mechanism, "Professional car service for any occasion.")


def _get_mechanism_cta(mechanism: str) -> str:
    ctas = {
        "authority": "See why professionals choose LUXY",
        "social_proof": "Join the professionals",
        "cognitive_ease": "Book now",
        "scarcity": "Reserve your car",
        "commitment": "Set up your account",
        "liking": "Experience the difference",
        "curiosity": "Try your first ride",
        "loss_aversion": "Switch to guaranteed transport",
        "reciprocity": "See what we offer",
        "unity": "Join us",
    }
    return ctas.get(mechanism, "Learn more")


def _get_superposition_headline(mechanisms: List[str]) -> str:
    """Multi-mechanism headline covering top 3 approaches."""
    parts = {
        "authority": "the executive standard",
        "social_proof": "chosen by 10,000+ professionals",
        "cognitive_ease": "book in 30 seconds",
        "commitment": "your dedicated car service",
        "curiosity": "discover the difference",
        "liking": "designed for your comfort",
        "scarcity": "limited premium fleet",
    }
    relevant = [parts.get(m, "") for m in mechanisms if m in parts][:2]
    if len(relevant) >= 2:
        return f"LUXY Ride — {relevant[0]}, {relevant[1]}"
    return "LUXY Ride — premium ground transportation"


def _get_superposition_body(mechanisms: List[str]) -> str:
    """Multi-mechanism body that covers multiple persuasion routes."""
    return (
        "The executive standard in ground transportation. "
        "Trusted by 10,000+ professionals. "
        "Book in 30 seconds — no surge, no uncertainty, no hassle."
    )
