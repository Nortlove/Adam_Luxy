# =============================================================================
# Resonance Engineering — Layer 5: LEARN
# Location: adam/retargeting/resonance/resonance_learner.py
# =============================================================================

"""
Closed-Loop Resonance Learning.

Every outcome updates the resonance model's understanding of which
page_mindstate × mechanism × barrier combinations convert.

Five update targets per outcome:
1. Resonance model cell (Stage A→B→C progression)
2. HierarchicalPriorManager (page_context_cluster conditioning)
3. Resonance cache (invalidate stale entries)
4. Prediction accuracy tracker (for self-evaluation)
5. Observation buffer (for causal discovery + hypothesis generation)
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np

from adam.retargeting.resonance.models import PageMindstateVector, ResonanceScore
from adam.retargeting.resonance.resonance_model import ResonanceModel
from adam.retargeting.resonance.resonance_cache import ResonanceCache
from adam.retargeting.resonance.creative_adapter import CreativeAdapter

logger = logging.getLogger(__name__)


@dataclass
class ResonanceObservation:
    """A single (page_mindstate, mechanism, barrier, outcome) observation.

    These accumulate in the observation buffer and feed:
    - ResonanceModel cell updates (Stage B/C training)
    - Evolutionary engine hypothesis generation
    - Causal discovery for page × mechanism pathways
    """

    timestamp: float = field(default_factory=time.time)
    page_mindstate_vector: Optional[np.ndarray] = None
    page_cluster: str = ""
    page_domain: str = ""
    mechanism: str = ""
    barrier: str = ""
    archetype: str = ""
    touch_position: int = 0
    predicted_resonance: float = 1.0
    actual_converted: bool = False
    actual_engaged: bool = False
    outcome_score: float = 0.0  # 0.0-1.0 composite

    # User posterior context (Enhancement #36 integration)
    user_id: str = ""
    user_baseline: float = 0.5  # User's mean conversion rate across mechanisms
    user_residual: float = 0.0  # outcome - user_baseline (purer page effect)
    user_trajectory_state: str = ""  # warming/cooling/flat/step_change
    user_mechanisms_tried: int = 0
    design_effect_weight: float = 1.0  # Within-subject correlation discount


@dataclass
class PredictionAccuracyTracker:
    """Tracks resonance model prediction accuracy over time.

    Used by the self-evaluator (Layer 6) to detect concept drift.
    """

    predictions: List[float] = field(default_factory=list)
    outcomes: List[float] = field(default_factory=list)
    window_size: int = 200

    def record(self, predicted: float, actual: float) -> None:
        self.predictions.append(predicted)
        self.outcomes.append(actual)
        if len(self.predictions) > self.window_size * 2:
            self.predictions = self.predictions[-self.window_size:]
            self.outcomes = self.outcomes[-self.window_size:]

    @property
    def recent_accuracy(self) -> float:
        """Correlation between predictions and outcomes over recent window."""
        if len(self.predictions) < 20:
            return 0.5  # Insufficient data
        from scipy.stats import pearsonr
        preds = np.array(self.predictions[-self.window_size:])
        outs = np.array(self.outcomes[-self.window_size:])
        if np.std(preds) < 0.001 or np.std(outs) < 0.001:
            return 0.0
        r, _ = pearsonr(preds, outs)
        return max(0.0, float(r))

    @property
    def accuracy_trend(self) -> str:
        """Is accuracy improving, stable, or degrading?"""
        if len(self.predictions) < 100:
            return "insufficient_data"
        mid = len(self.predictions) // 2
        from scipy.stats import pearsonr
        early_preds = np.array(self.predictions[:mid])
        early_outs = np.array(self.outcomes[:mid])
        late_preds = np.array(self.predictions[mid:])
        late_outs = np.array(self.outcomes[mid:])

        try:
            r_early, _ = pearsonr(early_preds, early_outs)
            r_late, _ = pearsonr(late_preds, late_outs)
        except Exception:
            return "error"

        if r_late > r_early + 0.05:
            return "improving"
        elif r_late < r_early - 0.05:
            return "degrading"
        return "stable"


class ResonanceLearner:
    """Processes outcomes through the resonance learning pipeline.

    Integration: Called from RetargetingLearningLoop.process_touch_outcome()
    after the standard hierarchical posterior updates.
    """

    def __init__(
        self,
        resonance_model: Optional[ResonanceModel] = None,
        resonance_cache: Optional[ResonanceCache] = None,
        prior_manager=None,
    ):
        self._model = resonance_model or ResonanceModel()
        self._cache = resonance_cache or ResonanceCache()
        self._adapter = CreativeAdapter()
        self._prior_manager = prior_manager
        self._accuracy = PredictionAccuracyTracker()
        self._observations: List[ResonanceObservation] = []
        self._max_observations = 10000

    def process_outcome(
        self,
        page_mindstate: PageMindstateVector,
        mechanism: str,
        barrier: str,
        archetype: str,
        converted: bool,
        engaged: bool = False,
        touch_position: int = 0,
        predicted_resonance: float = 1.0,
        context: Optional[Dict[str, str]] = None,
        # Enhancement #36 integration: user posterior context
        user_id: str = "",
        user_baseline: float = 0.5,
        user_trajectory_state: str = "",
        user_mechanisms_tried: int = 0,
        design_effect_weight: float = 1.0,
    ) -> Dict[str, Any]:
        """Process a single outcome through the resonance learning pipeline.

        Args:
            page_mindstate: The page's psychological field at decision time
            mechanism: Mechanism deployed
            barrier: Barrier targeted
            archetype: User archetype
            converted: Did the user convert?
            engaged: Did the user engage (click, dwell)?
            touch_position: Position in the retargeting sequence
            predicted_resonance: What the model predicted
            context: Hierarchy context for prior updates
            user_id: User identifier (for user×page interaction tracking)
            user_baseline: User's mean conversion across all mechanisms
            user_trajectory_state: warming/cooling/flat/step_change
            user_mechanisms_tried: Distinct mechanisms this user has tried
            design_effect_weight: Within-subject correlation discount (0-1)

        Returns:
            Dict with learning results
        """
        results: Dict[str, Any] = {}
        outcome_score = 1.0 if converted else (0.3 if engaged else 0.0)

        # Compute user-residualized outcome for purer page-effect learning.
        # If user_X converts 80% of the time regardless of page, the page
        # gets less credit. If user_Y converts 10% baseline but converted
        # HERE, the page gets more credit.
        user_residual = outcome_score - user_baseline
        results["user_residual"] = round(user_residual, 4)

        # 1. Update resonance model cell
        # Use design_effect_weight to discount correlated within-user observations.
        # Without this, a user who sees 7 touches contributes 7x as much
        # to resonance estimates as a user with 1 touch — but those 7 obs
        # are correlated (same person), so they carry less information.
        self._model.record_outcome(
            page_mindstate, mechanism, barrier, archetype,
            converted, outcome_score,
            weight=design_effect_weight,
        )
        results["model_updated"] = True
        results["model_stats"] = self._model.stats

        # 2. Update hierarchical priors with page cluster conditioning
        if self._prior_manager is not None:
            cluster = self._adapter.classify_page_cluster(page_mindstate)
            ctx = dict(context or {})
            ctx["page_cluster"] = cluster

            levels = self._prior_manager.update_all_levels(
                mechanism=mechanism,
                barrier=barrier,
                archetype=archetype,
                reward=outcome_score,
                context=ctx,
                design_effect_weight=design_effect_weight,
            )
            results["prior_levels_updated"] = levels
            results["page_cluster"] = cluster

        # 3. Invalidate stale cache entries for this page
        if page_mindstate.url_pattern:
            self._cache.set_page_resonance(
                page_mindstate.url_pattern, mechanism,
                predicted_resonance,  # Update with latest prediction
            )

        # 4. Track prediction accuracy
        self._accuracy.record(predicted_resonance, outcome_score)
        results["prediction_accuracy"] = self._accuracy.recent_accuracy
        results["accuracy_trend"] = self._accuracy.accuracy_trend

        # 5. Store observation for hypothesis generation (with user context)
        obs = ResonanceObservation(
            page_mindstate_vector=page_mindstate.to_numpy(),
            page_cluster=self._adapter.classify_page_cluster(page_mindstate),
            page_domain=page_mindstate.domain,
            mechanism=mechanism,
            barrier=barrier,
            archetype=archetype,
            touch_position=touch_position,
            predicted_resonance=predicted_resonance,
            actual_converted=converted,
            actual_engaged=engaged,
            outcome_score=outcome_score,
            # User posterior context (Enhancement #36)
            user_id=user_id,
            user_baseline=user_baseline,
            user_residual=user_residual,
            user_trajectory_state=user_trajectory_state,
            user_mechanisms_tried=user_mechanisms_tried,
            design_effect_weight=design_effect_weight,
        )
        self._observations.append(obs)
        if len(self._observations) > self._max_observations:
            self._observations = self._observations[-self._max_observations:]

        results["total_observations"] = len(self._observations)
        results["design_effect_weight"] = design_effect_weight
        return results

    def get_observations(
        self,
        mechanism: Optional[str] = None,
        barrier: Optional[str] = None,
        min_observations: int = 0,
    ) -> List[ResonanceObservation]:
        """Get filtered observations for hypothesis generation or analysis."""
        filtered = self._observations
        if mechanism:
            filtered = [o for o in filtered if o.mechanism == mechanism]
        if barrier:
            filtered = [o for o in filtered if o.barrier == barrier]
        if len(filtered) < min_observations:
            return []
        return filtered

    @property
    def accuracy_tracker(self) -> PredictionAccuracyTracker:
        return self._accuracy

    @property
    def stats(self) -> Dict[str, Any]:
        return {
            "total_observations": len(self._observations),
            "prediction_accuracy": self._accuracy.recent_accuracy,
            "accuracy_trend": self._accuracy.accuracy_trend,
            "model_stats": self._model.stats,
            "cache_stats": self._cache.stats,
        }


# =============================================================================
# SINGLETON
# =============================================================================

_resonance_learner: Optional["ResonanceLearner"] = None


def get_resonance_learner() -> "ResonanceLearner":
    """Get or create the singleton ResonanceLearner."""
    global _resonance_learner
    if _resonance_learner is None:
        _resonance_learner = ResonanceLearner()
    return _resonance_learner
