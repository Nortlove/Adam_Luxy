# =============================================================================
# Organic Return Tracker — Signal 3
# Location: adam/retargeting/engines/organic_return.py
# Enhancement #34: Nonconscious Signal Intelligence Layer, Session 4
# =============================================================================

"""
Detects when internal motivation has formed by tracking the ratio of
self-initiated (organic) visits to ad-prompted visits.

A rising organic return ratio indicates the retargeting sequence planted
a seed the person is nurturing independently. This is the behavioral
signature of stage transition from EVALUATING to INTENDING.

Instead of a fixed threshold (0.3), we use surge detection: compare
the individual's organic ratio to the population baseline. An individual
whose organic ratio exceeds 2x the population baseline is showing
anomalous self-directed interest.

CRITICAL: Do NOT serve more barrier-resolution creative to someone who
is already internally motivated — that triggers reactance. When stage
== INTENDING, switch to implementation_intention mechanism.
"""

import logging
from enum import Enum
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


# =============================================================================
# STAGE SIGNAL
# =============================================================================

class OrganicStage(str, Enum):
    """Stage classification from organic return analysis."""
    EVALUATING_EXTERNALLY = "evaluating_externally"
    # All visits ad-prompted. Intervention not creating lasting shift.

    EVALUATING_WITH_INTEREST = "evaluating_with_interest"
    # Some organic returns. Interest building but not self-sustaining.

    INTENDING = "intending"
    # Organic ratio surge detected. Internal motivation formed.
    # Switch to implementation_intention.


# Surge multiplier threshold: individual organic ratio must be >= 2x
# the population baseline to qualify as INTENDING.
SURGE_MULTIPLIER_THRESHOLD = 2.0

# Minimum evidence requirements
MIN_ORGANIC_COUNT_FOR_INTENDING = 2   # At least 2 organic visits
MIN_TOTAL_VISITS_FOR_INTENDING = 3    # At least 3 total visits
MIN_TOTAL_VISITS_FOR_INTEREST = 2     # At least 2 for any signal


# =============================================================================
# ORGANIC RETURN TRACKER
# =============================================================================

class OrganicReturnTracker:
    """Stateless engine that computes stage signal from visit history.

    Reads from StoredSignalProfile's visit_is_organic list and
    population organic ratio baseline.
    """

    def get_stage_signal(
        self,
        visit_is_organic: List[bool],
        population_organic_ratio: float = 0.15,
    ) -> Optional[Dict]:
        """Compute stage signal from visit history.

        Args:
            visit_is_organic: Ordered list of booleans — True if organic,
                False if ad-attributed. One per visit.
            population_organic_ratio: Population baseline organic ratio
                (from Redis population metrics).

        Returns:
            Dict with stage, mechanism_recommendation, surge_multiplier,
            or None if insufficient data.
        """
        total = len(visit_is_organic)
        if total < MIN_TOTAL_VISITS_FOR_INTEREST:
            return None

        organic_count = sum(1 for v in visit_is_organic if v)
        individual_ratio = organic_count / total

        # Surge detection: compare to population baseline
        surge_multiplier = (
            individual_ratio / population_organic_ratio
            if population_organic_ratio > 0 else 0.0
        )

        # Stage classification
        if (
            surge_multiplier >= SURGE_MULTIPLIER_THRESHOLD
            and organic_count >= MIN_ORGANIC_COUNT_FOR_INTENDING
            and total >= MIN_TOTAL_VISITS_FOR_INTENDING
        ):
            stage = OrganicStage.INTENDING
            mechanism_rec = "implementation_intention"
            note = (
                f"Organic ratio {individual_ratio:.2f} is {surge_multiplier:.1f}x "
                f"population baseline ({population_organic_ratio:.2f}). "
                f"Internal motivation formed. Switch to implementation_intention."
            )
        elif organic_count >= 1:
            stage = OrganicStage.EVALUATING_WITH_INTEREST
            mechanism_rec = "continue_current"
            note = "Some organic returns. Interest building but not yet self-sustaining."
        else:
            stage = OrganicStage.EVALUATING_EXTERNALLY
            mechanism_rec = "barrier_resolution"
            note = "All visits ad-prompted. Intervention not creating lasting shift."

        return {
            "organic_ratio": round(individual_ratio, 3),
            "organic_count": organic_count,
            "total_visits": total,
            "surge_multiplier": round(surge_multiplier, 2),
            "population_baseline": population_organic_ratio,
            "stage": stage.value,
            "mechanism_recommendation": mechanism_rec,
            "note": note,
        }


def get_organic_return_tracker() -> OrganicReturnTracker:
    """Get an OrganicReturnTracker instance (stateless)."""
    return OrganicReturnTracker()
