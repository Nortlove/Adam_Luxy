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
from typing import Dict, List, Optional

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


# ─── Cascade adapter ──────────────────────────────────────────────────────
# Per CODEBASE_AUDIT_2026_04_29.md §6: trilateral_epistemic_value()
# existed but had NO caller. This adapter applies it as a bounded
# multiplicative bonus on top of cascade mechanism_scores, completing
# the trilateral information-value picture (buyer × page-mech × buyer-
# page) that the existing single-source IV bidding can't capture.

# Cap on per-mechanism trilateral bonus. The total_epistemic returned
# by trilateral_epistemic_value can be unbounded above; capping it
# keeps the bonus on the same scale as predictive_processing's ±15%.
_TRILATERAL_BONUS_CAP = 0.15


def apply_trilateral_epistemic_bonus(
    mechanism_scores: Dict[str, float],
    buyer_id: str,
    page_edge_dimensions: Optional[Dict[str, float]] = None,
    graph_cache: Optional[object] = None,
    bonus_cap: float = _TRILATERAL_BONUS_CAP,
) -> Dict[str, float]:
    """Augment cascade mechanism_scores with the trilateral epistemic value.

    For each mechanism with a primary-dimension fingerprint, compute
    trilateral_epistemic_value over the buyer's BONG covariance, the
    mechanism's feature vector, and the page's edge dimensions. The
    returned total_epistemic is squashed and capped, then applied
    multiplicatively as a soft bonus on the mechanism's score.

    Soft-fail in EVERY branch:
        * empty mechanism_scores  → return as-is
        * missing buyer_id        → return as-is
        * missing graph_cache or get_buyer_profile → return as-is
        * missing page_edge_dimensions → return as-is
        * BONG not initialized   → return as-is
        * any internal exception → return as-is

    The wire is best-effort: when in doubt, the cascade's substantive
    scoring stands.
    """
    if not mechanism_scores or not buyer_id or graph_cache is None:
        return mechanism_scores
    if not page_edge_dimensions:
        return mechanism_scores
    if not hasattr(graph_cache, "get_buyer_profile"):
        return mechanism_scores

    try:
        profile = graph_cache.get_buyer_profile(buyer_id=buyer_id)
    except Exception as exc:
        logger.debug("Trilateral wire: get_buyer_profile failed: %s", exc)
        return mechanism_scores
    if profile is None:
        return mechanism_scores
    bong_post = getattr(profile, "bong_posterior", None)
    if bong_post is None:
        return mechanism_scores

    try:
        from adam.intelligence.bong import get_bong_updater
        updater = get_bong_updater()
        if updater.prior_eta is None:
            return mechanism_scores
        buyer_cov = updater.get_covariance(bong_post)
        bong_dims: List[str] = list(updater.dimension_names)
    except Exception as exc:
        logger.debug("Trilateral wire: BONG covariance unavailable: %s", exc)
        return mechanism_scores

    try:
        from adam.intelligence.per_user_posterior_modulation import (
            BONG_TO_COHORT_DIM,
            MECHANISM_DIMENSION_MAP,
        )
    except Exception:
        return mechanism_scores

    # Build the page mindstate vector aligned to BONG's dimension order
    # (cohort-dim → BONG-dim translation handled below). Pad to 20 with
    # 0.5 for any BONG dim not present in page_edge_dimensions.
    cohort_to_bong = {v: k for k, v in BONG_TO_COHORT_DIM.items()}
    page_vec = np.array(
        [
            float(
                page_edge_dimensions.get(BONG_TO_COHORT_DIM.get(d, d), 0.5)
            )
            for d in bong_dims
        ],
        dtype=float,
    )

    modulated: Dict[str, float] = dict(mechanism_scores)

    for mech_id, base_score in mechanism_scores.items():
        primary_dims = MECHANISM_DIMENSION_MAP.get(mech_id)
        if not primary_dims:
            continue

        # Mechanism feature vector in BONG dim order: 1.0 on primary
        # dims (translated to BONG names), 0.5 elsewhere.
        bong_primary = {
            cohort_to_bong.get(d, d) for d in primary_dims
        }
        mech_vec = np.array(
            [(1.0 if d in bong_primary else 0.5) for d in bong_dims],
            dtype=float,
        )

        try:
            ev = trilateral_epistemic_value(
                buyer_covariance=buyer_cov,
                mechanism_vector=mech_vec,
                page_mindstate=page_vec,
                page_mechanism_observations=0,
                buyer_page_observations=0,
            )
            total = float(ev.get("total_epistemic", 0.0))
        except Exception as exc:
            logger.debug(
                "Trilateral wire: trilateral_epistemic_value failed for %s: %s",
                mech_id, exc,
            )
            continue

        # Squash unbounded total via tanh-like saturation, then cap.
        # tanh keeps ordering and bounds to (-1, 1); the cap further
        # limits the per-mechanism multiplicative effect.
        squashed = float(np.tanh(total))
        capped = max(-bonus_cap, min(bonus_cap, squashed * bonus_cap))
        if abs(capped) > 1e-6:
            modulated[mech_id] = max(0.0, min(1.0, base_score * (1.0 + capped)))

    return modulated
