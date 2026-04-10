# =============================================================================
# Trilateral Epistemic Value Computation
# Location: adam/intelligence/trilateral_epistemic.py
# Unified System Evolution Directive, Section 4
# =============================================================================

"""
Computes epistemic value across the full trilateral space:
    Buyer uncertainty × Page×Mechanism uncertainty × Buyer×Page uncertainty

The previous epistemic computation only considered buyer uncertainty projected
onto the mechanism's dimensions. The trilateral version considers what we learn
about the PERSON, about the MECHANISM ON THIS PAGE, and about HOW THIS PERSON
responds to THIS PAGE ENVIRONMENT.

This replaces a single-source epistemic bonus with a three-source computation
that captures the full information structure of each impression.
"""

import logging
from typing import Dict, Optional

import numpy as np

logger = logging.getLogger(__name__)


def trilateral_epistemic_value(
    buyer_covariance: np.ndarray,
    mechanism_vector: np.ndarray,
    page_mindstate: np.ndarray,
    page_mechanism_observations: int = 0,
    buyer_page_observations: int = 0,
) -> Dict[str, float]:
    """Compute epistemic value across all three uncertainty sources.

    Args:
        buyer_covariance: BONG posterior covariance (20x20) for this buyer
        mechanism_vector: 20-dim observation model for the candidate mechanism
        page_mindstate: 32-dim page vector (first 20 = edge dims used here)
        page_mechanism_observations: How many times this mechanism ran on this
            page cluster (from resonance model Stage A/B/C tracking)
        buyer_page_observations: How many times this buyer was served on this
            page cluster (from per-user page_mechanism_posteriors)

    Returns:
        Dict with buyer_epistemic, page_mechanism_epistemic, buyer_page_epistemic,
        total_epistemic, and component weights.
    """
    d = buyer_covariance.shape[0]
    page_edge = page_mindstate[:d]
    mech_vec = mechanism_vector[:d]

    # ── Source 1: Buyer epistemic ──
    # How much will we learn about THIS PERSON by deploying this mechanism?
    # BONG uncertainty projected onto mechanism's target dimensions.
    projected_var = float(mech_vec @ buyer_covariance @ mech_vec)
    buyer_epistemic = 0.5 * np.log1p(max(0, projected_var))

    # ── Source 2: Page × Mechanism epistemic ──
    # How much data do we have for this mechanism on this page cluster?
    # Fewer observations = more epistemic value from this observation.
    # Decays as 1/(1 + n/10) — halves at 10 observations.
    page_mechanism_epistemic = 1.0 / (1.0 + page_mechanism_observations / 10.0)

    # ── Source 3: Buyer × Page epistemic ──
    # How much will we learn about how THIS PERSON responds to THIS PAGE?
    # BONG uncertainty projected onto page's active dimensions.
    page_projected_var = float(page_edge @ buyer_covariance @ page_edge)
    buyer_page_epistemic = 0.5 * np.log1p(max(0, page_projected_var))
    # Discount by observations: diminishes as we learn this person×page combo
    buyer_page_epistemic *= 1.0 / (1.0 + buyer_page_observations / 5.0)

    total = buyer_epistemic + page_mechanism_epistemic + buyer_page_epistemic

    return {
        "buyer_epistemic": round(float(buyer_epistemic), 4),
        "page_mechanism_epistemic": round(float(page_mechanism_epistemic), 4),
        "buyer_page_epistemic": round(float(buyer_page_epistemic), 4),
        "total_epistemic": round(float(total), 4),
        "buyer_pct": round(float(buyer_epistemic / max(total, 1e-6) * 100), 1),
        "page_mech_pct": round(float(page_mechanism_epistemic / max(total, 1e-6) * 100), 1),
        "buyer_page_pct": round(float(buyer_page_epistemic / max(total, 1e-6) * 100), 1),
    }


def adaptive_epistemic_weight(
    trajectory_type: str = "stable",
    observation_count: int = 0,
    base_weight: float = 0.3,
) -> float:
    """Adapt exploration intensity based on individual's state stability.

    New individuals (few observations) get high exploration regardless.
    Stable well-observed individuals get near-zero exploration.
    Non-stationary individuals (cooling, step_change) always get moderate-high.

    Args:
        trajectory_type: From Step 13.5 trajectory analysis
        observation_count: Total observations for this buyer
        base_weight: Maximum epistemic weight (0.3 = 30% exploration at peak)

    Returns:
        Adapted epistemic weight [0, base_weight]
    """
    # Observation-based decay: explore less as we learn more
    observation_decay = 1.0 / (1.0 + observation_count / 10.0)

    # Trajectory-based boost: explore more if state is changing
    trajectory_multiplier = {
        "stable": 0.1,
        "flat": 0.1,
        "warming": 0.5,
        "cooling": 0.8,
        "step_change": 1.5,
        "inverted_u": 0.6,
        "insufficient_data": 0.5,
    }.get(trajectory_type, 0.3)

    # Combine: max of observation-based and trajectory-based
    weight = base_weight * max(observation_decay, trajectory_multiplier)
    return round(float(weight), 4)
