# =============================================================================
# Resonance Engineering — Resonance Gradient Computation
# Location: adam/retargeting/resonance/resonance_gradient.py
# =============================================================================

"""
Computes ∂P(conversion)/∂page_mindstate for each mechanism.

This is the PAGE-SIDE analogue of the existing gradient fields
(adam/intelligence/gradient_fields.py) which compute buyer-side gradients.

The resonance gradient tells us: for a given mechanism, which page
dimensions should we INCREASE or DECREASE to improve conversion probability?
This drives the placement optimizer (Layer 3).
"""

import logging
import math
from typing import Dict, List, Optional, Tuple

import numpy as np

from adam.retargeting.resonance.models import (
    PageMindstateVector,
    ALL_MINDSTATE_DIMS,
    MINDSTATE_DIM_COUNT,
)
from adam.retargeting.resonance.cold_start import (
    get_ideal_vector,
    RESONANCE_TEMPERATURE,
)

logger = logging.getLogger(__name__)


def compute_resonance_gradient(
    mechanism: str,
    page_mindstate: PageMindstateVector,
    temperature: float = RESONANCE_TEMPERATURE,
) -> Dict[str, float]:
    """Compute ∂resonance/∂page_dim for each of the 32 page dimensions.

    For Stage A (theory prior), the gradient of the sigmoid resonance function
    with respect to each page dimension is:

    ∂R/∂page_i = ideal_i × sigmoid'(alignment/T) / T

    where sigmoid'(x) = sigmoid(x)(1 - sigmoid(x))

    Positive gradient = increasing this page dimension improves resonance.
    Negative gradient = decreasing this page dimension improves resonance.

    Returns:
        {dim_name: gradient_value} sorted by absolute magnitude
    """
    page_vec = page_mindstate.to_numpy()
    ideal = get_ideal_vector(mechanism)

    # Current alignment
    alignment = float(np.dot(page_vec - 0.5, ideal))

    # Sigmoid and its derivative
    sig = 1.0 / (1.0 + math.exp(-alignment / temperature))
    sig_deriv = sig * (1.0 - sig) / temperature

    # Gradient: ∂R/∂page_i = ideal_i × sigmoid'
    # Scale factor to map from sigmoid derivative to resonance multiplier derivative
    scale = 2.7  # Range of multiplier is 2.7 (0.3 to 3.0)

    gradients = {}
    for i, dim in enumerate(ALL_MINDSTATE_DIMS):
        grad = float(ideal[i] * sig_deriv * scale)
        if abs(grad) > 0.001:  # Only report meaningful gradients
            gradients[dim] = round(grad, 4)

    return dict(sorted(gradients.items(), key=lambda x: abs(x[1]), reverse=True))


def compute_optimal_direction(
    mechanism: str,
    page_mindstate: PageMindstateVector,
    step_size: float = 0.1,
) -> PageMindstateVector:
    """Compute the page mindstate that's one gradient step closer to optimal.

    This is used by the placement optimizer to determine the IDEAL page
    environment: starting from the current page, which direction should
    we move to maximize resonance?

    Returns a new PageMindstateVector representing the "improved" page state.
    """
    gradient = compute_resonance_gradient(mechanism, page_mindstate)
    page_vec = page_mindstate.to_numpy()

    # Take a gradient step
    for i, dim in enumerate(ALL_MINDSTATE_DIMS):
        if dim in gradient:
            page_vec[i] = np.clip(page_vec[i] + step_size * gradient[dim], 0.0, 1.0)

    return PageMindstateVector.from_numpy(page_vec, {
        "domain": page_mindstate.domain,
        "url_pattern": page_mindstate.url_pattern,
        "confidence": page_mindstate.confidence,
    })


def rank_dimensions_by_resonance_impact(
    mechanism: str,
) -> List[Tuple[str, float, str]]:
    """Rank all 32 page dimensions by their impact on this mechanism's resonance.

    Returns list of (dim_name, ideal_value, direction) sorted by impact.
    Direction is "increase" or "decrease" depending on the ideal vector sign.
    """
    ideal = get_ideal_vector(mechanism)
    ranked = []

    for i, dim in enumerate(ALL_MINDSTATE_DIMS):
        val = float(ideal[i])
        if abs(val) > 0.01:
            direction = "increase" if val > 0 else "decrease"
            ranked.append((dim, abs(val), direction))

    ranked.sort(key=lambda x: x[1], reverse=True)
    return ranked
