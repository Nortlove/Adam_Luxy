# =============================================================================
# Impression Outcome Classifier
# Location: adam/retargeting/engines/impression_classifier.py
# =============================================================================

"""
Classifies non-click outcomes into their TRUE meaning.

The advertising industry's critical error: treating every non-click as
a negative signal. A non-click is actually 4 completely different things:

  A. UNPROCESSED — Never saw the ad (ad blindness, scrolled past)
     → Teaches nothing. Should NOT update mechanism posteriors.
     → Processing Depth weight = 0.05

  B. BUILDING — Processed but forming impressions (mere exposure effect)
     → Actually POSITIVE. Brand familiarity accumulating.
     → The person may convert organically later without ever clicking.
     → Processing Depth weight = 0.30

  C. REJECTED — Processed, evaluated, decided against
     → The actual negative signal. Mechanism or message wrong.
     → Processing Depth weight = 1.00

  D. AD-AVERSE — Will never click ANY ad (personality trait, not message failure)
     → Retargeting is futile. Only brand awareness via mere exposure.
     → Should be detected early and moved to awareness-only pool.

Classification uses behavioral evidence from our telemetry, not
StackAdapt viewability metrics (which we don't have in real-time).

The behavioral proxies:
  - Session depth → did they engage at all after clicking?
  - Cross-session evolution → is engagement deepening or declining?
  - Organic returns → are they coming back without ad prompting?
  - Section engagement patterns → what are they doing on the site?
"""

import logging
from enum import Enum
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class ImpressionOutcome(str, Enum):
    """True meaning of a non-click ad impression."""
    UNPROCESSED = "unprocessed"
    BUILDING = "building"
    REJECTED = "rejected"
    AD_AVERSE = "ad_averse"
    CLICKED = "clicked"        # They did click
    CONVERTED = "converted"    # They converted


# Posterior update weights per outcome type
OUTCOME_WEIGHTS = {
    ImpressionOutcome.UNPROCESSED: 0.05,  # Near-zero — noise, not signal
    ImpressionOutcome.BUILDING: 0.15,     # Mild positive (mere exposure value)
    ImpressionOutcome.REJECTED: 1.00,     # Full negative — genuine mechanism failure
    ImpressionOutcome.AD_AVERSE: 0.00,    # Zero — this person's non-click says nothing about the mechanism
    ImpressionOutcome.CLICKED: 0.80,      # Positive — they engaged
    ImpressionOutcome.CONVERTED: 1.00,    # Full positive — mechanism worked
}

# How much each outcome contributes to the "should we keep trying" decision
PERSISTENCE_WEIGHTS = {
    ImpressionOutcome.UNPROCESSED: 0.0,   # Doesn't count toward persistence budget
    ImpressionOutcome.BUILDING: -0.1,     # REDUCES pressure to give up (they're progressing)
    ImpressionOutcome.REJECTED: 0.3,      # Increases pressure to give up
    ImpressionOutcome.AD_AVERSE: -0.8,     # Strong signal to stop ad-targeting
    ImpressionOutcome.CLICKED: -0.2,      # Reduces pressure (they're engaging)
    ImpressionOutcome.CONVERTED: -1.0,    # Full stop — they converted
}


class ImpressionClassifier:
    """Classifies the true meaning of ad impressions from behavioral evidence."""

    def classify_user_response(
        self,
        profile: Dict,
        touch_number: int = 0,
    ) -> Tuple[ImpressionOutcome, float, str]:
        """Classify a user's overall response pattern.

        Looks at their TRAJECTORY across all sessions, not just one event.

        Returns:
            (outcome, confidence, reasoning)
        """
        total_sessions = profile.get("total_sessions", 0)
        ad_sessions = profile.get("ad_attributed_sessions", 0)
        organic_sessions = profile.get("organic_sessions", 0)
        converted = profile.get("converted", False)

        if converted:
            return ImpressionOutcome.CONVERTED, 1.0, "User converted."

        if total_sessions == 0:
            return ImpressionOutcome.UNPROCESSED, 0.5, "No sessions recorded."

        # ── Evidence collection ──

        # Total engagement depth
        section_dwell = profile.get("section_dwell_totals", {})
        total_dwell = sum(section_dwell.values())

        # Engagement evolution
        touch_outcomes = profile.get("touch_outcomes", [])
        n_clicks = sum(1 for t in touch_outcomes if t)
        n_touches = len(touch_outcomes)

        # Organic behavior
        organic_ratio = organic_sessions / max(1, total_sessions)

        # Reactance
        reactance = profile.get("reactance_detected", False)

        # ── Classification logic ──

        # If they've clicked at least once, they're not ad-averse
        if n_clicks > 0:
            if total_dwell > 30:
                return (
                    ImpressionOutcome.BUILDING, 0.8,
                    f"Clicked {n_clicks}/{n_touches} times, {total_dwell:.0f}s section engagement. "
                    f"Building toward conversion."
                )
            else:
                return (
                    ImpressionOutcome.CLICKED, 0.7,
                    f"Clicked {n_clicks}/{n_touches} times but shallow engagement ({total_dwell:.0f}s). "
                    f"Message attracted attention but didn't resonate deeply."
                )

        # No clicks ever — determine why

        # HIGH ad exposure + ZERO clicks + ZERO organic returns = likely ad-averse
        if ad_sessions >= 3 and n_clicks == 0 and organic_sessions == 0 and total_dwell < 5:
            return (
                ImpressionOutcome.AD_AVERSE, 0.7,
                f"{ad_sessions} ad impressions with zero clicks and zero organic visits. "
                f"Likely ad-averse personality. Move to awareness-only pool. "
                f"Stop retargeting — if they convert, it will be through organic search."
            )

        # Some ad exposure + organic returns = building through mere exposure
        if organic_sessions > 0:
            return (
                ImpressionOutcome.BUILDING, 0.75,
                f"No ad clicks but {organic_sessions} organic returns. "
                f"Brand awareness is forming through mere exposure. "
                f"Continue low-frequency brand impressions — they're self-directing."
            )

        # Engagement depth without clicks = building but barrier present
        if total_dwell > 20:
            return (
                ImpressionOutcome.BUILDING, 0.65,
                f"No clicks but {total_dwell:.0f}s of site engagement. "
                f"They're interested but the ad didn't trigger the click. "
                f"The barrier is between ad and click, not between interest and product."
            )

        # Reactance detected = rejected
        if reactance:
            return (
                ImpressionOutcome.REJECTED, 0.8,
                f"Reactance detected after {n_touches} touches. "
                f"The retargeting sequence created resistance. "
                f"Switch to autonomy_restoration or release."
            )

        # Low ad exposure, no engagement = probably unprocessed
        if ad_sessions <= 2 and total_dwell < 5:
            return (
                ImpressionOutcome.UNPROCESSED, 0.6,
                f"Only {ad_sessions} ad impressions, minimal engagement ({total_dwell:.0f}s). "
                f"Likely never processed the ads meaningfully. "
                f"Continue targeting — insufficient exposure so far."
            )

        # Default: still evaluating
        return (
            ImpressionOutcome.BUILDING, 0.5,
            f"Mixed signals: {ad_sessions} ad sessions, {organic_sessions} organic, "
            f"{total_dwell:.0f}s dwell. Classify as building — insufficient evidence for rejection."
        )

    def compute_adjusted_learning_weight(
        self,
        profile: Dict,
    ) -> Tuple[float, str]:
        """Compute the learning weight for this user's outcomes.

        Instead of treating every non-click as weight=1.0 failure,
        adjust based on the TRUE meaning of their non-engagement.

        Returns:
            (weight, explanation)
        """
        outcome, confidence, reasoning = self.classify_user_response(profile)
        base_weight = OUTCOME_WEIGHTS[outcome]

        # Scale by confidence
        weight = base_weight * confidence + (1.0 - confidence) * 0.5

        return (
            round(weight, 3),
            f"Outcome: {outcome.value} (conf={confidence:.2f}). "
            f"Learning weight: {weight:.3f}. {reasoning}"
        )

    def compute_persistence_score(
        self,
        profile: Dict,
    ) -> Tuple[float, str]:
        """Should we keep targeting this person?

        Returns a score from -1 (definitely stop) to +1 (definitely continue).
        0 = neutral / insufficient evidence.
        """
        outcome, confidence, reasoning = self.classify_user_response(profile)
        persistence = PERSISTENCE_WEIGHTS[outcome]

        # Factor in conversion distance from puzzle solver
        touches_remaining = profile.get("estimated_touches_remaining", 4.0)
        if touches_remaining > 6:
            persistence -= 0.2  # Getting expensive
        elif touches_remaining < 2:
            persistence += 0.2  # Almost there

        # Factor in organic signals
        organic = profile.get("organic_sessions", 0)
        if organic > 0:
            persistence += 0.15  # They're self-directing — good sign

        persistence = max(-1.0, min(1.0, persistence))

        if persistence < -0.3:
            action = "RELEASE — move to awareness-only or dormant pool"
        elif persistence < 0:
            action = "REDUCE — lower frequency, switch to softer mechanism"
        elif persistence < 0.3:
            action = "CONTINUE — maintain current strategy"
        else:
            action = "ACCELERATE — increase frequency, they're close"

        return (
            round(persistence, 3),
            f"{action}. Score: {persistence:.2f}. {reasoning}"
        )


def get_impression_classifier() -> ImpressionClassifier:
    return ImpressionClassifier()
