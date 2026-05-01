# =============================================================================
# Spine #5 Option B — LogisticGoalStateModel
# Location: adam/intelligence/goal_state_logistic_model.py
# =============================================================================
"""Multinomial logistic regression goal-state prior with elastic-net.

Slice 17b — Option B implementation of the GoalStatePriorModel
Protocol from free_energy.py. Trained offline on labeled
(page_features, active_goal_state) tuples; predicts a multinomial
posterior at decision time via sklearn predict_proba.

Per directive Spine #5 line 216: "a small generative model trained
on the offline-pipeline output: page-content embeddings plus
user-state embeddings produce a posterior over which of ~12-15
active goal states the user is in."

Logistic regression with elastic-net (L1 + L2 mix) is the
classical baseline for "small generative model" — fast to train,
calibratable, and well-understood. Compared to Option C
(HierarchicalGoalStateModel): logistic is single-task multinomial
(one dominant goal per page) with no native uncertainty
quantification, whereas C is multi-label with hierarchical pooling.
The B + C dual-eval (Slice 17d) lets pilot data show which is
stronger per goal state.

WHY THIS EXISTS — DECISION-TIME CONSUMER

  cascade.run_bilateral_cascade
      ↓ (Slice 17d wires)
  page_features extraction → LogisticGoalStateModel.predict_p(features)
      ↓ GoalStatePosterior (multinomial over 14 goals)
  free_energy.compute_free_energy(p, candidate_mech, model, π)
      ↓ F(a | s, c) per candidate
  cascade.score - λ_F · F(a)        (directive line 521)

FEATURE EXTRACTION

The model consumes a fixed-shape feature vector built from
page_features at predict time:
  - posture_class as one-hot (4-dim: BLEND/VIGILANCE/NEUTRAL/UNKNOWN)
  - posture_confidence (1-dim scalar)
  - keyword-match indicators per goal (14-dim, one per inventory goal)
  - page edge_dimensions (variable; 27-dim when available, else
    zero-padded)

This shape is CONSISTENT across train and predict; the trained
model's coefficient matrix expects this exact column order.

DISCIPLINE (B3-LUXY a/b/c/d)
----------------------------

(a) Citations: directive Spine #5 line 216; standard multinomial
    logistic with elastic-net (Friedman, Hastie, Tibshirani 2010 —
    glmnet); sklearn.linear_model.LogisticRegression with penalty=
    'elasticnet' + solver='saga'.

(b) Tests pin: feature vector shape stability; train + predict
    round-trip with synthetic labels; predict_q delegates to
    closed_form_q_from_p; soft-fail on sklearn-missing → returns
    PassthroughGoalStateModel fallback; soft-fail on untrained
    model → fallback; model serialization round-trip via joblib.

(c) calibration_pending=True. ELASTIC_NET_L1_RATIO and
    REGULARIZATION_C are conservative defaults; cross-validation
    on accumulated labels will calibrate. A14 flag:
    SPINE_5_LOGISTIC_HYPERPARAMS_PILOT_PENDING.

(d) Honest tags — what is NOT in this slice (named successors):

    * Claude API label generator that produces the
      (page_features, active_goal_state) tuples this model trains
      on (Slice 18 / directive Section 6.2).
    * Cross-validation hyperparameter tuning loop (sibling — once
      enough labels accumulate).
    * Class-imbalance handling. Pilot labels may be imbalanced;
      v0.1 uses class_weight='balanced'. Sibling refinement when
      empirical distribution is observed.
    * Multi-label extension. Multinomial assumes single dominant
      goal per page; if pilot data shows multi-goal activation,
      Option C (Slice 17c hierarchical) is the natural successor.
    * Per-archetype feature vector — currently page-only +
      keyword-only. Adding user_state features (BONG mean, archetype
      one-hot) is sibling.
    * Embedding-based features (sentence-transformer page_text
      embedding) — directive line 216 mentions
      "page-content embeddings"; v0.1 uses keyword-presence
      vectors. Embedding integration is sibling.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from adam.intelligence.free_energy import (
    GoalStatePosterior,
    PassthroughGoalStateModel,
    closed_form_q_from_p,
)
from adam.intelligence.goal_state_inventory import (
    list_goal_states,
)
from adam.intelligence.page_attentional_posture_substrate import (
    POSTURE_BLEND,
    POSTURE_NEUTRAL,
    POSTURE_UNKNOWN,
    POSTURE_VIGILANCE,
)

logger = logging.getLogger(__name__)


# =============================================================================
# A14 calibration-pending hyperparameters
# =============================================================================

# A14 SPINE_5_LOGISTIC_HYPERPARAMS_PILOT_PENDING
ELASTIC_NET_L1_RATIO: float = 0.5
"""Mix between L1 (sparse coefficients) and L2 (smooth shrinkage).
0.5 is the elastic-net default; LUXY pilot CV will calibrate."""

REGULARIZATION_C: float = 1.0
"""sklearn's inverse regularization strength. Higher = less reg.
1.0 = standard default; CV calibrates."""

MAX_ITER: int = 1000
"""saga solver iteration cap. Conservative."""

CLASS_WEIGHT: str = "balanced"
"""Auto-balance class weights — pilot label distribution may be
heavily imbalanced toward common goals (commute_readiness)."""


# =============================================================================
# Feature extraction
# =============================================================================


_POSTURE_KEYS: List[str] = [
    POSTURE_BLEND,
    POSTURE_VIGILANCE,
    POSTURE_NEUTRAL,
    POSTURE_UNKNOWN,
]

_EDGE_DIMENSIONS_DEFAULT_LEN: int = 27
"""Standard 27-dim alignment vector size (matches BONG.DEFAULT_DIMENSIONS
length). Feature vector pads with zeros when edge_dimensions is
shorter or missing."""


def _goal_state_ids_sorted() -> List[str]:
    return sorted(g.id for g in list_goal_states())


def extract_feature_vector(
    page_features: Dict[str, Any],
) -> np.ndarray:
    """Build the fixed-shape feature vector consumed by the trained model.

    Shape: (4 posture one-hot) + (1 posture_confidence) + (14 keyword
    presence per goal) + (27 edge_dimensions zero-padded) = 46-dim.

    Stable column order — train + predict use the same extraction.
    """
    features: List[float] = []

    # 1. Posture one-hot
    posture_class = page_features.get("posture_class") or POSTURE_UNKNOWN
    for key in _POSTURE_KEYS:
        features.append(1.0 if posture_class == key else 0.0)

    # 2. Posture confidence
    try:
        conf = float(page_features.get("posture_confidence") or 0.0)
    except (TypeError, ValueError):
        conf = 0.0
    if conf < 0.0:
        conf = 0.0
    elif conf > 1.0:
        conf = 1.0
    features.append(conf)

    # 3. Keyword overlap per goal (binary indicator: does the page have
    #    ANY keyword matching this goal's inventory keywords?)
    page_keywords_raw = page_features.get("page_keywords", []) or []
    page_keywords = {str(k).lower() for k in page_keywords_raw}
    for goal_id in _goal_state_ids_sorted():
        goal = next((g for g in list_goal_states() if g.id == goal_id), None)
        if goal is None:
            features.append(0.0)
            continue
        goal_kw = {kw.lower() for kw in goal.keywords}
        features.append(1.0 if (page_keywords & goal_kw) else 0.0)

    # 4. Edge dimensions (page-side alignment vector when available)
    edge_dims_raw = page_features.get("edge_dimensions") or []
    edge_dims_padded = list(edge_dims_raw)[:_EDGE_DIMENSIONS_DEFAULT_LEN]
    while len(edge_dims_padded) < _EDGE_DIMENSIONS_DEFAULT_LEN:
        edge_dims_padded.append(0.0)
    for v in edge_dims_padded:
        try:
            features.append(float(v))
        except (TypeError, ValueError):
            features.append(0.0)

    return np.array(features, dtype=np.float64)


def feature_vector_dim() -> int:
    """Total feature-vector dimension. 4 + 1 + 14 + 27 = 46."""
    return (
        len(_POSTURE_KEYS)
        + 1
        + len(_goal_state_ids_sorted())
        + _EDGE_DIMENSIONS_DEFAULT_LEN
    )


# =============================================================================
# LogisticGoalStateModel
# =============================================================================


class LogisticGoalStateModel:
    """Multinomial logistic regression goal-state prior model.

    Implements the GoalStatePriorModel Protocol from free_energy.
    Soft-fails to PassthroughGoalStateModel when sklearn isn't
    available OR when the model isn't trained yet.

    Lifecycle:
        model = LogisticGoalStateModel()              # untrained
        model.train(labeled_pairs)                    # offline
        p = model.predict_p(page_features)            # decision-time
        q = model.predict_q(p, candidate_mechanism)   # decision-time
    """

    def __init__(self) -> None:
        self._sklearn_model: Optional[Any] = None
        self._goal_state_ids: List[str] = _goal_state_ids_sorted()
        self._fallback = PassthroughGoalStateModel()
        self._n_train_samples: int = 0
        self._n_train_classes: int = 0

    @property
    def model_name(self) -> str:
        return "logistic_v1"

    @property
    def is_trained(self) -> bool:
        return self._sklearn_model is not None

    @property
    def n_train_samples(self) -> int:
        """Sample count from last train() call. Used by callers to
        decide whether to trust the trained model vs fall back."""
        return self._n_train_samples

    @property
    def n_train_classes(self) -> int:
        """Distinct goal-state classes seen during training."""
        return self._n_train_classes

    def train(
        self,
        labeled_pairs: List[Tuple[Dict[str, Any], str]],
        *,
        l1_ratio: float = ELASTIC_NET_L1_RATIO,
        C: float = REGULARIZATION_C,
        max_iter: int = MAX_ITER,
    ) -> bool:
        """Fit the multinomial logistic on (page_features, goal_state_id).

        Returns True on successful fit; False when:
          - sklearn unavailable (logged at WARNING)
          - empty labeled_pairs
          - fewer than 2 distinct classes

        Honest tag: requires labels. Until Slice 18's Claude API
        label generator runs, callers train on synthetic seed
        labels OR fall back to the passthrough heuristic.
        """
        try:
            from sklearn.linear_model import LogisticRegression
        except ImportError:
            logger.warning(
                "LogisticGoalStateModel.train: sklearn not installed; "
                "model stays untrained → predict_p falls back to "
                "passthrough."
            )
            return False

        if not labeled_pairs:
            logger.warning("LogisticGoalStateModel.train: empty labels")
            return False

        # Build train matrices
        X = np.array([
            extract_feature_vector(features)
            for features, _ in labeled_pairs
        ])
        y = np.array([str(label) for _, label in labeled_pairs])

        unique_classes = sorted(set(y))
        if len(unique_classes) < 2:
            logger.warning(
                "LogisticGoalStateModel.train: need ≥2 classes; "
                "got %d (%s)", len(unique_classes), unique_classes,
            )
            return False

        try:
            # multi_class='multinomial' is the default in sklearn ≥1.5
            # (and the multi_class kwarg is deprecated there); omit
            # explicit kwarg to avoid the FutureWarning.
            clf = LogisticRegression(
                penalty="elasticnet",
                solver="saga",
                l1_ratio=float(l1_ratio),
                C=float(C),
                max_iter=int(max_iter),
                class_weight=CLASS_WEIGHT,
                n_jobs=-1,
            )
            clf.fit(X, y)
        except Exception as exc:
            logger.warning(
                "LogisticGoalStateModel.train: fit failed: %s", exc,
            )
            return False

        self._sklearn_model = clf
        self._n_train_samples = len(labeled_pairs)
        self._n_train_classes = len(unique_classes)
        return True

    def predict_p(
        self,
        page_features: Dict[str, Any],
        user_state: Optional[Dict[str, float]] = None,
    ) -> GoalStatePosterior:
        """Predict p(goal | s, c). Falls back to passthrough heuristic
        when model is untrained.

        user_state is accepted for Protocol conformance but not used
        by the v0.1 logistic model (page-only features). Adding user-
        state features (BONG mean, archetype one-hot) is a sibling
        slice.
        """
        if self._sklearn_model is None:
            # Soft-fail to passthrough — preserves cascade integration
            # contract (always returns valid posterior) while signaling
            # via model_name that real prediction wasn't available.
            fallback = self._fallback.predict_p(page_features, user_state)
            return GoalStatePosterior(
                probabilities=fallback.probabilities,
                model_name=f"{self.model_name}:fallback_passthrough",
            )

        x = extract_feature_vector(page_features).reshape(1, -1)
        try:
            probs = self._sklearn_model.predict_proba(x)[0]
        except Exception as exc:
            logger.warning(
                "LogisticGoalStateModel.predict_p: predict_proba failed: %s",
                exc,
            )
            fallback = self._fallback.predict_p(page_features, user_state)
            return GoalStatePosterior(
                probabilities=fallback.probabilities,
                model_name=f"{self.model_name}:fallback_predict_error",
            )

        # The model's classes_ attribute gives the column → goal_state
        # mapping; some inventory goals may not have been seen during
        # training — those get probability 0.
        classes = list(self._sklearn_model.classes_)
        all_goal_ids = self._goal_state_ids
        probabilities: Dict[str, float] = {gid: 0.0 for gid in all_goal_ids}
        for cls_name, prob in zip(classes, probs):
            if cls_name in probabilities:
                probabilities[cls_name] = float(prob)

        # Ensure normalization (predict_proba already returns
        # normalized probabilities, but classes outside the inventory
        # may have been dropped above).
        total = sum(probabilities.values())
        if total > 0.0:
            probabilities = {k: v / total for k, v in probabilities.items()}
        else:
            # Pathological — model produced no probability mass on
            # any inventory goal. Fall back.
            fallback = self._fallback.predict_p(page_features, user_state)
            return GoalStatePosterior(
                probabilities=fallback.probabilities,
                model_name=f"{self.model_name}:fallback_zero_mass",
            )

        return GoalStatePosterior(
            probabilities=probabilities,
            model_name=self.model_name,
        )

    def predict_q(
        self,
        p: GoalStatePosterior,
        candidate_mechanism: str,
    ) -> GoalStatePosterior:
        """Closed-form Bayesian update — same as B and C use.

        The goal-conditional likelihood L(a | g) is the inventory's
        mechanism_priors[a.mechanism]; the model_name on the
        returned posterior is this model's name (not 'closed_form_*')
        so the dual-eval logger can attribute it correctly.
        """
        return closed_form_q_from_p(
            p, candidate_mechanism, model_name=self.model_name,
        )
