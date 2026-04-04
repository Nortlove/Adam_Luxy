# =============================================================================
# Frequency Decay Detector — Signal 6
# Location: adam/retargeting/engines/frequency_decay.py
# Enhancement #34: Nonconscious Signal Intelligence Layer, Session 4
# =============================================================================

"""
Detects individual reactance onset using Bayesian changepoint detection
with a Beta-Bernoulli conjugate model.

Linear slope is wrong for sparse binary data (5-10 click/no-click events).
Instead, we use a sliding window approach: compare recent engagement
(last 3 touches) to historical engagement (all prior touches). If recent
engagement is significantly lower, flag reactance onset.

This is simpler than full BOCD (Adams-MacKay algorithm) but appropriate
for the data volume at pilot scale (5-15 touches per individual).
At scale (50+ touches), upgrade to full BOCD with population-informed priors.

When reactance is detected:
- H4 modifier = +0.30 (strong reactance evidence)
- Recommendation: switch_to_autonomy_restoration
- Retargeting planner should BACK OFF or change mechanism completely

When engagement is declining but not yet flagged:
- H4 modifier = +0.10 (mild engagement decline)
- Recommendation: monitor

When engagement is stable or increasing:
- H4 modifier = -0.10 (counter-evidence against reactance)
"""

import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


# Minimum touches required for any analysis
MIN_TOUCHES_FOR_ANALYSIS = 4

# Minimum touches for reliable reactance detection
MIN_TOUCHES_FOR_REACTANCE = 5

# Recent window size (last N touches)
RECENT_WINDOW = 3

# Early window minimum size
MIN_EARLY_WINDOW = 2

# Rate decline threshold: recent rate < 0.5 * early rate → reactance
RATE_DECLINE_FACTOR = 0.5


# =============================================================================
# FREQUENCY DECAY DETECTOR
# =============================================================================

class FrequencyDecayDetector:
    """Stateless engine that detects individual reactance onset from
    a sequence of click/no-click outcomes.

    Reads from StoredSignalProfile's touch_outcomes list.
    """

    def detect_reactance(
        self,
        touch_outcomes: List[bool],
        population_ctr: float = 0.02,
    ) -> Optional[Dict]:
        """Detect reactance from a sequence of touch outcomes.

        Args:
            touch_outcomes: Ordered list of click (True) / no-click (False)
                per retargeting touch.
            population_ctr: Population-level click-through rate
                (from Redis population metrics).

        Returns:
            Dict with reactance_detected, onset_touch, h4_modifier,
            recommendation, or None if insufficient data.
        """
        n = len(touch_outcomes)

        if n < MIN_TOUCHES_FOR_ANALYSIS:
            return None

        # Split into early and recent windows
        split = max(MIN_EARLY_WINDOW, n - RECENT_WINDOW)
        early = touch_outcomes[:split]
        recent = touch_outcomes[split:]

        early_rate = sum(early) / len(early) if early else 0.0
        recent_rate = sum(recent) / len(recent) if recent else 0.0
        overall_rate = sum(touch_outcomes) / n

        # Beta posterior for recent engagement
        # Prior: Beta(1, 1) (uniform)
        recent_alpha = 1 + sum(recent)
        recent_beta_param = 1 + len(recent) - sum(recent)

        early_alpha = 1 + sum(early)
        early_beta_param = 1 + len(early) - sum(early)

        # Reactance detection
        reactance_detected = False
        reactance_touch = None

        if early_rate > 0 and recent_rate < RATE_DECLINE_FACTOR * early_rate and n >= MIN_TOUCHES_FOR_REACTANCE:
            reactance_detected = True
            reactance_touch = split + 1  # approximate onset
        elif sum(recent) == 0 and sum(early) > 0 and n >= MIN_TOUCHES_FOR_ANALYSIS:
            # Complete engagement cessation after prior engagement
            reactance_detected = True
            reactance_touch = split + 1

        # Compute H4 modifier and recommendation
        if reactance_detected:
            h4_modifier = 0.30
            recommendation = "switch_to_autonomy_restoration"
        elif recent_rate < early_rate and early_rate > 0:
            h4_modifier = 0.10  # mild engagement decline
            recommendation = "monitor"
        else:
            h4_modifier = -0.10  # engagement stable or increasing
            recommendation = "continue_current"

        return {
            "total_touches": n,
            "early_rate": round(float(early_rate), 3),
            "recent_rate": round(float(recent_rate), 3),
            "overall_rate": round(float(overall_rate), 3),
            "early_window_size": len(early),
            "recent_window_size": len(recent),
            "early_posterior": {"alpha": early_alpha, "beta": early_beta_param},
            "recent_posterior": {"alpha": recent_alpha, "beta": recent_beta_param},
            "reactance_detected": reactance_detected,
            "reactance_onset_touch": reactance_touch,
            "h4_modifier": h4_modifier,
            "recommendation": recommendation,
        }


def get_frequency_decay_detector() -> FrequencyDecayDetector:
    """Get a FrequencyDecayDetector instance (stateless)."""
    return FrequencyDecayDetector()
