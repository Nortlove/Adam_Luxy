# =============================================================================
# Counterfactual Tracker — "What Would We Do Differently?"
# Location: adam/intelligence/counterfactual_tracker.py
# =============================================================================

"""
For every impression where we DON'T convert, asks:
"If we'd used mechanism Y instead of X, what would have happened?"

This doubles the effective learning sample size by extracting signal
from failures as well as successes. Every non-conversion is a
counterfactual experiment that teaches us about alternatives.

Uses the existing counterfactual_mechanisms.py for reasoning and
the hypothesis engine for tracking predictions.

Wired into outcome handler: on every non-conversion, generate
counterfactual predictions. When a CONVERSION does happen in a
similar context, validate the counterfactual predictions.
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class CounterfactualPrediction:
    """What WOULD have happened with a different mechanism."""
    decision_id: str
    actual_mechanism: str
    actual_converted: bool
    counterfactual_mechanism: str
    predicted_effectiveness: float  # 0-1
    reasoning: str
    context_signature: str  # Hash of relevant dimensions for matching
    created_at: float = field(default_factory=time.time)
    validated: Optional[bool] = None
    validation_source: str = ""


class CounterfactualTracker:
    """Tracks counterfactual predictions and validates them against real outcomes.

    For every non-conversion:
    1. Ask: what mechanism SHOULD we have used?
    2. Predict: what would the conversion rate have been?
    3. Store the prediction
    4. When a conversion happens in a SIMILAR context, check:
       did the counterfactual mechanism match what actually worked?

    This creates a secondary learning signal from every failure.
    """

    def __init__(self):
        self._predictions: List[CounterfactualPrediction] = []
        self._validated: List[CounterfactualPrediction] = []
        self._mechanism_alternatives: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))
        self._max_predictions = 10_000

    def generate_counterfactual(
        self,
        decision_id: str,
        mechanism_used: str,
        converted: bool,
        edge_dimensions: Dict[str, float],
        archetype: str = "",
    ) -> List[CounterfactualPrediction]:
        """Generate counterfactual predictions for a non-conversion.

        "If we'd used authority instead of social_proof on this analytical
        page for this careful_truster, the theory chain says we'd have
        converted because low_uncertainty → need_for_closure → authority."
        """
        if converted:
            # Conversions are for validation, not counterfactual generation
            self._validate_against_conversion(mechanism_used, edge_dimensions)
            return []

        predictions = []

        # Get alternative mechanisms from the hypothesis engine
        try:
            from adam.intelligence.inferential_hypothesis_engine import get_inferential_hypothesis_engine
            hyp_engine = get_inferential_hypothesis_engine()
            matching = hyp_engine.get_predictions_for_context(edge_dimensions)

            for hyp in matching[:3]:  # Top 3 alternative mechanisms
                if hyp.predicted_mechanism != mechanism_used:
                    # Build context signature for later matching
                    sig_parts = []
                    for dim, val in sorted(edge_dimensions.items()):
                        if abs(val - 0.5) > 0.1:  # Only significant dimensions
                            sig_parts.append(f"{dim}:{val:.1f}")
                    context_sig = "|".join(sig_parts[:5])

                    pred = CounterfactualPrediction(
                        decision_id=decision_id,
                        actual_mechanism=mechanism_used,
                        actual_converted=False,
                        counterfactual_mechanism=hyp.predicted_mechanism,
                        predicted_effectiveness=hyp.predicted_effectiveness,
                        reasoning=hyp.theory_explanation[:200],
                        context_signature=context_sig,
                    )
                    predictions.append(pred)
                    self._predictions.append(pred)

                    # Track mechanism alternatives
                    self._mechanism_alternatives[mechanism_used][hyp.predicted_mechanism] += 1

        except Exception as e:
            logger.debug("Counterfactual generation failed: %s", e)

        if len(self._predictions) > self._max_predictions:
            self._predictions = self._predictions[-self._max_predictions:]

        return predictions

    def _validate_against_conversion(
        self,
        mechanism_that_converted: str,
        edge_dimensions: Dict[str, float],
    ) -> int:
        """When a conversion happens, check if any counterfactual predicted it.

        If a previous non-conversion with mechanism X generated a
        counterfactual "use mechanism Y instead", and NOW mechanism Y
        converts in a similar context — the counterfactual was RIGHT.
        """
        validated_count = 0

        # Build context signature
        sig_parts = []
        for dim, val in sorted(edge_dimensions.items()):
            if abs(val - 0.5) > 0.1:
                sig_parts.append(f"{dim}:{val:.1f}")
        context_sig = "|".join(sig_parts[:5])

        # Find matching counterfactual predictions
        for pred in self._predictions:
            if pred.validated is not None:
                continue
            if pred.counterfactual_mechanism == mechanism_that_converted:
                # Check context similarity (simple signature match)
                if pred.context_signature == context_sig or self._contexts_similar(pred, edge_dimensions):
                    pred.validated = True
                    pred.validation_source = f"conversion with {mechanism_that_converted}"
                    self._validated.append(pred)
                    validated_count += 1

                    logger.info(
                        "Counterfactual VALIDATED: predicted %s would beat %s — confirmed",
                        pred.counterfactual_mechanism, pred.actual_mechanism,
                    )

        return validated_count

    def _contexts_similar(self, pred: CounterfactualPrediction, dims: Dict[str, float]) -> bool:
        """Check if a prediction's context is similar to current dimensions."""
        # Simple: check if the significant dimensions match within tolerance
        for part in pred.context_signature.split("|"):
            if ":" in part:
                dim, val_str = part.split(":", 1)
                try:
                    pred_val = float(val_str)
                    actual_val = dims.get(dim, 0.5)
                    if abs(pred_val - actual_val) > 0.2:
                        return False
                except ValueError:
                    pass
        return True

    def get_recommended_alternatives(self, mechanism: str) -> List[Tuple[str, int]]:
        """Get recommended alternative mechanisms based on counterfactual history.

        Returns mechanisms that counterfactual analysis suggests would
        have worked better, ranked by frequency.
        """
        alts = self._mechanism_alternatives.get(mechanism, {})
        return sorted(alts.items(), key=lambda x: x[1], reverse=True)

    @property
    def stats(self) -> Dict[str, Any]:
        total_validated = sum(1 for p in self._validated if p.validated)
        total_invalidated = sum(1 for p in self._validated if p.validated is False)
        return {
            "total_predictions": len(self._predictions),
            "validated": total_validated,
            "invalidated": total_invalidated,
            "accuracy": total_validated / max(total_validated + total_invalidated, 1),
            "mechanism_alternatives": dict(self._mechanism_alternatives),
        }


# Singleton
_tracker = None
def get_counterfactual_tracker():
    global _tracker
    if _tracker is None:
        _tracker = CounterfactualTracker()
    return _tracker
