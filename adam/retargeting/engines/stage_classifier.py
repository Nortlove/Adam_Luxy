# =============================================================================
# Therapeutic Retargeting Engine — Conversion Stage Classifier
# Location: adam/retargeting/engines/stage_classifier.py
# =============================================================================

"""
TTM-derived Conversion Stage Classifier.

Classifies users into 6 conversion stages from behavioral signals — NOT
self-report. The stage determines which therapeutic mechanisms are
appropriate. Stage-mismatched interventions generate resistance
(Krebs et al., 2010, k=88).

This is a PLATFORM SERVICE — callable from:
- Bilateral cascade (first-touch): infer stage from buyer history
- Retargeting engine: classify before each touch
- Webhook handler: reclassify after each outcome
- Universal Intelligence API: enrich responses with stage info
"""

import logging
from typing import Dict, List, Optional, Tuple

from adam.retargeting.models.enums import ConversionStage
from adam.retargeting.engines.signal_processors import (
    BehavioralSignal,
    BehavioralSignalProcessor,
    ProcessedSignalSet,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Stage classification thresholds
# These are the decision boundaries for stage assignment. Each stage has
# conditions that must be met. The classifier evaluates in order from
# CONVERTED (most advanced) to UNAWARE (least advanced) and assigns the
# MOST ADVANCED stage whose conditions are met.
# ---------------------------------------------------------------------------
_STAGE_CONDITIONS = {
    ConversionStage.CONVERTED: {
        "booking_completions_gte": 1,
    },
    ConversionStage.STALLED: {
        # Was intending (had booking/cart activity) but stopped
        "had_intent_signal": True,
        "hours_since_last_interaction_gte": 48.0,
    },
    ConversionStage.INTENDING: {
        # Active intent: cart, booking, email signup, or 3+ return visits
        "any_of": [
            {"cart_additions_gte": 1},
            {"booking_starts_gte": 1},
            {"email_signups_gte": 1},
            {"total_site_visits_gte": 3},
        ],
    },
    ConversionStage.EVALUATING: {
        # Active comparison: multiple pages, pricing, reviews, competitor visits
        "any_of": [
            {"pricing_page_visits_gte": 1},
            {"review_page_visits_gte": 1},
            {"comparison_page_visits_gte": 1},
            {"competitor_visits_gte": 1},
            {"total_page_views_gte": 3},
        ],
    },
    ConversionStage.CURIOUS: {
        # Initial awareness: ad engagement or single site visit
        "any_of": [
            {"total_clicks_gte": 1},
            {"total_site_visits_gte": 1},
            {"stage_score_gte": 0.05},
        ],
    },
    ConversionStage.UNAWARE: {
        # Default: no meaningful engagement
    },
}


class ConversionStageClassifier:
    """Classifies users into TTM-derived conversion stages.

    Runs EVERY TIME a new behavioral signal arrives (Krebs et al., 2010:
    dynamically re-tailored interventions that iteratively reassess
    outperform static segmentation).

    Usage:
        classifier = ConversionStageClassifier()
        stage, confidence, signals = classifier.classify(processed_signals)
        # OR from raw signals:
        stage, confidence, signals = classifier.classify_from_raw(
            user_id, brand_id, raw_signals
        )
    """

    def __init__(self):
        self._processor = BehavioralSignalProcessor()

    def classify(
        self,
        signals: ProcessedSignalSet,
    ) -> Tuple[ConversionStage, float, Dict[str, float]]:
        """Classify conversion stage from processed behavioral signals.

        Args:
            signals: Preprocessed behavioral signal set

        Returns:
            (stage, confidence, evidence_dict) where evidence_dict contains
            the key signals that determined classification.
        """
        evidence: Dict[str, float] = {}

        # Check CONVERTED first
        if signals.booking_completions >= 1:
            evidence["booking_completions"] = signals.booking_completions
            return ConversionStage.CONVERTED, 0.99, evidence

        # Check STALLED: had intent signals but gone quiet
        had_intent = (
            signals.cart_additions > 0
            or signals.booking_starts > 0
            or signals.email_signups > 0
        )
        if had_intent and signals.hours_since_last_interaction >= 48.0:
            evidence["had_intent"] = 1.0
            evidence["hours_since_last"] = signals.hours_since_last_interaction
            # Confidence scales with silence duration
            stall_confidence = min(0.95, 0.6 + 0.05 * (
                signals.hours_since_last_interaction - 48.0) / 24.0
            )
            return ConversionStage.STALLED, stall_confidence, evidence

        # Check INTENDING
        if had_intent:
            evidence["cart_additions"] = signals.cart_additions
            evidence["booking_starts"] = signals.booking_starts
            evidence["email_signups"] = signals.email_signups
            evidence["total_site_visits"] = signals.total_site_visits
            # Confidence from number of intent signals
            intent_count = (
                signals.cart_additions
                + signals.booking_starts
                + signals.email_signups
            )
            intent_confidence = min(0.95, 0.65 + 0.10 * intent_count)
            return ConversionStage.INTENDING, intent_confidence, evidence

        # Check EVALUATING
        evaluating_signals = (
            signals.pricing_page_visits
            + signals.review_page_visits
            + signals.comparison_page_visits
            + signals.competitor_visits
        )
        if evaluating_signals >= 1 or signals.total_page_views >= 3:
            evidence["pricing_page_visits"] = signals.pricing_page_visits
            evidence["review_page_visits"] = signals.review_page_visits
            evidence["comparison_page_visits"] = signals.comparison_page_visits
            evidence["competitor_visits"] = signals.competitor_visits
            evidence["total_page_views"] = signals.total_page_views
            eval_confidence = min(0.90, 0.50 + 0.08 * evaluating_signals)
            return ConversionStage.EVALUATING, eval_confidence, evidence

        # Check CURIOUS
        if (signals.total_clicks >= 1
                or signals.total_site_visits >= 1
                or signals.stage_score >= 0.05):
            evidence["total_clicks"] = signals.total_clicks
            evidence["total_site_visits"] = signals.total_site_visits
            evidence["stage_score"] = signals.stage_score
            return ConversionStage.CURIOUS, 0.60, evidence

        # Default: UNAWARE
        evidence["no_engagement"] = 1.0
        return ConversionStage.UNAWARE, 0.80, evidence

    def classify_from_raw(
        self,
        user_id: str,
        brand_id: str,
        raw_signals: List[BehavioralSignal],
    ) -> Tuple[ConversionStage, float, Dict[str, float]]:
        """Convenience: process raw signals and classify in one call."""
        processed = self._processor.process(user_id, brand_id, raw_signals)
        return self.classify(processed)

    def classify_from_touch_history(
        self,
        touch_history: List[Dict],
        behavioral_signals: Dict[str, float],
    ) -> Tuple[ConversionStage, float, Dict[str, float]]:
        """Classify from retargeting touch history + behavioral signal dict.

        This is the interface used by the barrier diagnostic engine, which
        passes touch outcomes and behavioral counters rather than raw signals.

        Args:
            touch_history: List of touch dicts with engagement_occurred, outcome, etc.
            behavioral_signals: Dict with keys like pages_viewed, booking_steps_completed,
                               hours_since_last_visit, etc.

        Returns:
            (stage, confidence, evidence_dict)
        """
        # Build a ProcessedSignalSet from the behavioral dict
        signals = ProcessedSignalSet(
            user_id=behavioral_signals.get("user_id", ""),
            brand_id=behavioral_signals.get("brand_id", ""),
            total_impressions=int(behavioral_signals.get("total_impressions", 0)),
            total_clicks=int(behavioral_signals.get("total_clicks", 0)),
            total_site_visits=int(behavioral_signals.get("total_site_visits", 0)),
            total_page_views=int(behavioral_signals.get("pages_viewed", 0)),
            total_dwell_minutes=behavioral_signals.get("total_dwell_minutes", 0.0),
            pricing_page_visits=int(behavioral_signals.get("pricing_page_visits", 0)),
            review_page_visits=int(behavioral_signals.get("review_page_visits", 0)),
            comparison_page_visits=int(behavioral_signals.get("comparison_page_visits", 0)),
            competitor_visits=int(behavioral_signals.get("competitor_visits", 0)),
            email_signups=int(behavioral_signals.get("email_signups", 0)),
            cart_additions=int(behavioral_signals.get("cart_additions", 0)),
            booking_starts=int(behavioral_signals.get("booking_starts", 0)),
            booking_completions=int(behavioral_signals.get("booking_completions", 0)),
            cart_abandons=int(behavioral_signals.get("cart_abandons", 0)),
            booking_abandons=int(behavioral_signals.get("booking_abandons", 0)),
            unsubscribes=int(behavioral_signals.get("unsubscribes", 0)),
            complaints=int(behavioral_signals.get("complaints", 0)),
            hours_since_last_interaction=behavioral_signals.get(
                "hours_since_last_visit", 0.0
            ),
            booking_steps_completed=int(
                behavioral_signals.get("booking_steps_completed", 0)
            ),
            pages_viewed=int(behavioral_signals.get("pages_viewed", 0)),
        )

        return self.classify(signals)
