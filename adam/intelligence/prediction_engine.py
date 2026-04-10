# =============================================================================
# Prediction Engine — Opportunity Finder + Prediction Tracker
# Location: adam/intelligence/prediction_engine.py
# =============================================================================

"""
Uses validated causal hypotheses to PREDICT where conversion will occur,
ACT on those predictions by deploying configurations, and TRACK whether
predictions are correct to compound intelligence.

This is where the system becomes PROACTIVE rather than reactive.
Instead of waiting for data to accumulate across contexts, it:
1. Takes a validated hypothesis
2. Finds pages/contexts matching the hypothesis conditions
3. Deploys the predicted optimal configuration
4. Tracks outcomes to validate/invalidate the prediction
5. Updates the hypothesis and generates derived hypotheses

The prediction accuracy should INCREASE over time. If it doesn't,
the causal model is wrong and needs revision.

Cross-disciplinary inspiration:
- DRUG DISCOVERY: Phase I trial → Phase II prediction → Phase III validation
- WEATHER FORECASTING: Model predicts → Observation validates → Model improves
- CHESS ENGINES: Position evaluation → Move prediction → Outcome → Self-play improvement
"""

import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class Prediction:
    """A specific prediction made by the system.

    Not a general hypothesis — a CONCRETE prediction:
    "On page X, mechanism Y will convert buyer archetype Z
    because hypothesis H says so."
    """

    prediction_id: str
    hypothesis_id: str  # Which hypothesis generated this prediction

    # What we predict
    page_url: str
    mechanism: str
    archetype: str
    predicted_conversion_rate: float
    predicted_resonance: float

    # Configuration to deploy
    recommended_copy_params: Dict[str, Any] = field(default_factory=dict)
    recommended_bid_multiplier: float = 1.0

    # Outcome tracking
    impressions_served: int = 0
    conversions_observed: int = 0
    actual_conversion_rate: float = 0.0

    # Validation
    prediction_validated: Optional[bool] = None
    validation_reason: str = ""

    # Timing
    created_at: float = field(default_factory=time.time)
    first_impression_at: float = 0.0
    last_outcome_at: float = 0.0

    @property
    def is_mature(self) -> bool:
        """Has this prediction been tested enough to validate/invalidate?"""
        return self.impressions_served >= 10

    @property
    def accuracy(self) -> float:
        """How close was the prediction to reality?"""
        if self.impressions_served == 0:
            return 0.0
        actual = self.conversions_observed / self.impressions_served
        predicted = self.predicted_conversion_rate
        # 1 - |actual - predicted| / max(actual, predicted, 0.01)
        return max(0.0, 1.0 - abs(actual - predicted) / max(predicted, 0.01))


class PredictionEngine:
    """Generates, tracks, and learns from predictions.

    The engine maintains:
    - Active predictions (being tested)
    - Prediction history (for accuracy tracking)
    - Prediction accuracy trend (should be improving)
    """

    def __init__(self):
        self._active_predictions: Dict[str, Prediction] = {}
        self._completed_predictions: List[Prediction] = []
        self._prediction_counter = 0
        self._accuracy_window: List[float] = []

    def generate_predictions(
        self,
        hypothesis_id: str,
        max_predictions: int = 5,
    ) -> List[Prediction]:
        """Generate concrete predictions from a validated hypothesis.

        Finds pages matching the hypothesis conditions and creates
        specific, trackable predictions for each.
        """
        from adam.intelligence.inferential_hypothesis_engine import (
            get_inferential_hypothesis_engine,
        )
        from adam.intelligence.page_similarity_index import get_page_similarity_index

        hyp_engine = get_inferential_hypothesis_engine()
        sim_index = get_page_similarity_index()

        hyp = hyp_engine._hypotheses.get(hypothesis_id)
        if not hyp or not hyp.is_actionable:
            return []

        # Find pages matching hypothesis conditions
        predictions = []
        if sim_index.size > 0:
            from adam.intelligence.page_similarity_index import EDGE_DIMENSIONS

            for url, vec in sim_index._vectors.items():
                # Build dimension dict from the stored vector
                dims = {EDGE_DIMENSIONS[i]: float(vec[i]) for i in range(min(len(EDGE_DIMENSIONS), len(vec)))}

                if hyp.matches_context(dims):
                    self._prediction_counter += 1
                    pred = Prediction(
                        prediction_id=f"pred_{self._prediction_counter:06d}",
                        hypothesis_id=hypothesis_id,
                        page_url=url,
                        mechanism=hyp.predicted_mechanism,
                        archetype="",  # Applies to any matching buyer
                        predicted_conversion_rate=hyp.predicted_effectiveness * 0.5,
                        predicted_resonance=hyp.confidence,
                        recommended_bid_multiplier=1.0 + hyp.confidence * 0.5,
                    )
                    predictions.append(pred)
                    self._active_predictions[pred.prediction_id] = pred

                    if len(predictions) >= max_predictions:
                        break

        # If no indexed pages match, use the hypothesis to recommend crawling
        if not predictions:
            logger.info(
                "No indexed pages match hypothesis %s — recommend crawling for matches",
                hypothesis_id,
            )
            # Queue pages for crawling based on hypothesis conditions
            self._queue_exploratory_crawl(hyp)

        logger.info(
            "Generated %d predictions from hypothesis %s",
            len(predictions), hypothesis_id,
        )
        return predictions

    def record_impression(self, prediction_id: str) -> None:
        """Record that a prediction-driven impression was served."""
        pred = self._active_predictions.get(prediction_id)
        if pred:
            pred.impressions_served += 1
            if pred.first_impression_at == 0:
                pred.first_impression_at = time.time()

    def record_outcome(
        self,
        prediction_id: str,
        converted: bool,
    ) -> Optional[Prediction]:
        """Record an outcome for a prediction.

        If the prediction reaches maturity (10+ impressions),
        validate or invalidate it and update the source hypothesis.
        """
        pred = self._active_predictions.get(prediction_id)
        if not pred:
            return None

        pred.last_outcome_at = time.time()
        if converted:
            pred.conversions_observed += 1

        pred.actual_conversion_rate = (
            pred.conversions_observed / max(pred.impressions_served, 1)
        )

        # Check if mature enough to validate
        if pred.is_mature and pred.prediction_validated is None:
            self._validate_prediction(pred)

        return pred

    def _validate_prediction(self, pred: Prediction) -> None:
        """Validate or invalidate a mature prediction.

        Updates the source hypothesis based on prediction accuracy.
        """
        accuracy = pred.accuracy

        if accuracy > 0.5:
            pred.prediction_validated = True
            pred.validation_reason = (
                f"Predicted {pred.predicted_conversion_rate:.2%}, "
                f"observed {pred.actual_conversion_rate:.2%} "
                f"({pred.conversions_observed}/{pred.impressions_served})"
            )
            logger.info(
                "Prediction VALIDATED: %s (accuracy=%.2f, predicted=%.2f%%, actual=%.2f%%)",
                pred.prediction_id, accuracy,
                pred.predicted_conversion_rate * 100,
                pred.actual_conversion_rate * 100,
            )
        else:
            pred.prediction_validated = False
            pred.validation_reason = (
                f"Predicted {pred.predicted_conversion_rate:.2%}, "
                f"observed {pred.actual_conversion_rate:.2%} — prediction too far off"
            )
            logger.info(
                "Prediction INVALIDATED: %s (accuracy=%.2f)",
                pred.prediction_id, accuracy,
            )

        # Update accuracy tracking
        self._accuracy_window.append(accuracy)
        if len(self._accuracy_window) > 100:
            self._accuracy_window = self._accuracy_window[-100:]

        # Move to completed
        self._completed_predictions.append(pred)
        del self._active_predictions[pred.prediction_id]

        # Feedback to hypothesis engine
        self._update_hypothesis(pred)

    def _update_hypothesis(self, pred: Prediction) -> None:
        """Feed prediction outcome back to the hypothesis engine."""
        try:
            from adam.intelligence.inferential_hypothesis_engine import (
                get_inferential_hypothesis_engine,
            )
            engine = get_inferential_hypothesis_engine()

            # Construct an observation for hypothesis testing
            observation = {
                "mechanism_sent": pred.mechanism,
                "converted": pred.prediction_validated,
                "edge_dimensions": {},  # Would need page dims
            }
            engine.test_empirically(pred.hypothesis_id, observation)
        except Exception as e:
            logger.debug("Hypothesis update failed: %s", e)

    def _queue_exploratory_crawl(self, hyp) -> None:
        """Queue pages for crawling that might match hypothesis conditions.

        This is ACTIVE HYPOTHESIS TESTING — the system doesn't wait for
        matching pages to appear. It goes LOOKING for them.

        Strategy:
        1. Identify which page TYPES would satisfy the conditions
           (e.g., clt > 0.7 → analytical/financial pages)
        2. Query the page inventory for domains in those clusters
        3. Queue those domains for priority crawling
        4. When crawled and scored, check if they match
        5. If they match, create a prediction and bid-boost
        """
        try:
            # Map conditions to likely page clusters
            cluster_hints = self._conditions_to_clusters(hyp.conditions)

            if cluster_hints:
                logger.info(
                    "Active hypothesis testing: hyp=%s seeking page clusters %s",
                    hyp.hypothesis_id, cluster_hints,
                )

                # Try to find domains associated with these clusters
                # from our site profiles
                try:
                    import json
                    with open("campaigns/ridelux_v6/luxy_ride_site_profiles.json") as f:
                        profiles = json.load(f)

                    for domain, profile in profiles.get("profiles", {}).items():
                        # Check if this domain's profile matches the hypothesis conditions
                        dims = {
                            "cognitive_load_tolerance": profile.get("processing_route", 0.5),
                            "emotional_resonance": profile.get("emotional_warmth", 0.5),
                            "social_proof_sensitivity": profile.get("social_proof_density", 0.5),
                            "autonomy_reactance": 1.0 - profile.get("autonomy_respect", 0.5),
                        }

                        if hyp.matches_context(dims):
                            # This domain likely has pages matching the hypothesis!
                            # Queue for priority crawling
                            import asyncio
                            from adam.intelligence.page_crawl_scheduler import queue_priority_crawl
                            try:
                                loop = asyncio.get_running_loop()
                                loop.create_task(queue_priority_crawl(
                                    url=f"https://{domain}/",
                                    priority=hyp.confidence,
                                    reason=f"hypothesis_test:{hyp.hypothesis_id}",
                                ))
                            except RuntimeError:
                                pass  # No event loop — will be picked up next cycle

                            # Also boost bids on this domain
                            try:
                                from adam.retargeting.resonance.placement_optimizer import get_placement_optimizer
                                opt = get_placement_optimizer()
                                opt.add_bid_boost_pages(
                                    [domain],
                                    boost_factor=1.0 + hyp.confidence * 0.5,
                                )
                            except Exception:
                                pass

                            logger.info(
                                "Hypothesis test triggered: crawling %s for hyp=%s (confidence=%.2f)",
                                domain, hyp.hypothesis_id, hyp.confidence,
                            )

                except FileNotFoundError:
                    pass

        except Exception as e:
            logger.debug("Exploratory crawl queue failed: %s", e)

    def _conditions_to_clusters(
        self, conditions: Dict[str, tuple]
    ) -> List[str]:
        """Map hypothesis conditions to page cluster types."""
        clusters = []
        for dim, (op, threshold) in conditions.items():
            if dim == "cognitive_load_tolerance" and op == ">" and threshold > 0.6:
                clusters.append("analytical")
            elif dim == "emotional_resonance" and op == ">" and threshold > 0.6:
                clusters.append("emotional")
            elif dim == "social_proof_sensitivity" and op == ">" and threshold > 0.6:
                clusters.append("social")
            elif dim == "cognitive_load_tolerance" and op == "<" and threshold < 0.4:
                clusters.append("transactional")
        return clusters if clusters else ["general"]

    def generate_highest_value_predictions(
        self,
        max_hypotheses: int = 3,
        max_predictions_per: int = 5,
    ) -> List[Prediction]:
        """Generate predictions for the highest-information-value hypotheses.

        This is the system's ACTIVE EXPERIMENTATION strategy. Instead of
        testing hypotheses in random order, it prioritizes the ones that
        teach the most about the causal structure.

        Called periodically (e.g., every 100 impressions) to ensure the
        system is always running its most informative experiments.
        """
        from adam.intelligence.inferential_hypothesis_engine import (
            get_inferential_hypothesis_engine,
        )
        hyp_engine = get_inferential_hypothesis_engine()

        ranking = hyp_engine.get_test_priority_ranking()
        all_predictions = []

        for hyp_id, info_value, reason in ranking[:max_hypotheses]:
            preds = self.generate_predictions(hyp_id, max_predictions=max_predictions_per)
            for p in preds:
                # Tag with info value so bid multiplier reflects test priority
                p.recommended_bid_multiplier = max(
                    p.recommended_bid_multiplier,
                    1.0 + info_value * 1.0,  # Higher IV → higher bid → more likely to win
                )
            all_predictions.extend(preds)

            logger.info(
                "Priority test: hyp=%s info_value=%.4f → %d predictions. Reason: %s",
                hyp_id, info_value, len(preds), reason,
            )

        return all_predictions

    @property
    def prediction_accuracy_trend(self) -> str:
        """Is prediction accuracy improving, stable, or declining?"""
        if len(self._accuracy_window) < 10:
            return "insufficient_data"

        first_half = self._accuracy_window[:len(self._accuracy_window) // 2]
        second_half = self._accuracy_window[len(self._accuracy_window) // 2:]

        avg_first = sum(first_half) / len(first_half)
        avg_second = sum(second_half) / len(second_half)

        if avg_second > avg_first + 0.05:
            return "improving"
        elif avg_second < avg_first - 0.05:
            return "declining"
        return "stable"

    @property
    def stats(self) -> Dict[str, Any]:
        avg_accuracy = (
            sum(self._accuracy_window) / len(self._accuracy_window)
            if self._accuracy_window else 0.0
        )
        return {
            "active_predictions": len(self._active_predictions),
            "completed_predictions": len(self._completed_predictions),
            "validated": sum(1 for p in self._completed_predictions if p.prediction_validated),
            "invalidated": sum(1 for p in self._completed_predictions if p.prediction_validated is False),
            "avg_accuracy": round(avg_accuracy, 3),
            "accuracy_trend": self.prediction_accuracy_trend,
        }


# =============================================================================
# SINGLETON
# =============================================================================

_engine: Optional[PredictionEngine] = None


def get_prediction_engine() -> PredictionEngine:
    global _engine
    if _engine is None:
        _engine = PredictionEngine()
    return _engine
