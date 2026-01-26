# =============================================================================
# ADAM Enhancement #13: Thompson Sampling Package
# Location: adam/cold_start/thompson/__init__.py
# =============================================================================

"""
Thompson Sampling for Cold Start Mechanism Selection

Implements:
- Beta posterior maintenance for each mechanism
- Thompson sampling for explore/exploit balance
- Exploration bonus for uncertain mechanisms
- Outcome-based posterior updates
"""

from .sampler import (
    ThompsonSampler,
    get_thompson_sampler,
)

__all__ = [
    "ThompsonSampler",
    "get_thompson_sampler",
]
