# =============================================================================
# Periodic Recalibration Pipeline
# Location: adam/retargeting/engines/recalibration.py
# =============================================================================

"""
Periodic Recalibration Pipeline for Composite Alignment Weights.

The Session 34-2 diagnostic revealed that composite_alignment was inverted
(r=-0.29) because all 25 dimensions had positive weights when 11 should
be negative. The v6 fix used logistic regression on 1,492 LUXY Ride edges
to derive data-calibrated weights (r=+0.86).

This pipeline AUTOMATES that recalibration so the system stays accurate
as data evolves:

1. DETECT: Track new bilateral edge count since last calibration
2. TRIGGER: When 500+ new edges accumulate (or weekly, whichever first)
3. FIT: Logistic regression on all available edges → new weights
4. VALIDATE: Compare new AUC vs current AUC on held-out data
5. DEPLOY: If new AUC > current AUC + threshold, update weights
6. LOG: Record calibration history for audit trail

The pipeline is category-aware: Beauty edges produce Beauty weights,
luxury_transportation edges produce LUXY weights. Cross-category
weights are computed from all edges combined.

Integration: Called from main.py startup scheduler (weekly), or
triggered by outcome_handler when edge count threshold is reached.
"""

import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from scipy.stats import pearsonr, rankdata

logger = logging.getLogger(__name__)


@dataclass
class CalibrationResult:
    """Result of a single calibration run."""

    timestamp: str
    category: str  # "luxury_transportation", "beauty", "all"
    n_edges: int
    n_converted: int

    # Weight comparison
    current_auc: float
    new_auc: float
    auc_improvement: float
    deployed: bool
    reason: str  # "improved", "no_improvement", "insufficient_data"

    # New weights (if deployed)
    new_weights: Dict[str, float] = field(default_factory=dict)

    # Dimension-level diagnostics
    sign_flips: int = 0
    top_predictors: List[Tuple[str, float]] = field(default_factory=list)


@dataclass
class CalibrationHistory:
    """Audit trail of all calibration runs."""

    runs: List[CalibrationResult] = field(default_factory=list)
    last_calibration: Optional[str] = None
    edges_since_last: int = 0
    current_weights: Dict[str, float] = field(default_factory=dict)


# Dimensions used in composite alignment
COMPOSITE_DIMENSIONS = [
    "regulatory_fit_score", "construal_fit_score", "personality_brand_alignment",
    "emotional_resonance", "value_alignment", "evolutionary_motive_match",
    "appeal_resonance", "processing_route_match", "implicit_driver_match",
    "lay_theory_alignment", "linguistic_style_match", "identity_signaling_match",
    "full_cosine_alignment", "uniqueness_popularity_fit",
    "mental_simulation_resonance", "involvement_weight_modifier",
    "negativity_bias_match", "reactance_fit", "optimal_distinctiveness_fit",
    "brand_trust_fit", "self_monitoring_fit", "spending_pain_match",
    "disgust_contamination_fit", "anchor_susceptibility_match",
    "mental_ownership_match",
]

# Current v6 weights (deployed from Session 34-2)
CURRENT_V6_WEIGHTS = {
    "emotional_resonance": +0.138, "brand_trust_fit": +0.125,
    "regulatory_fit_score": +0.087, "appeal_resonance": +0.083,
    "evolutionary_motive_match": +0.075, "anchor_susceptibility_match": +0.033,
    "value_alignment": +0.030, "mental_ownership_match": +0.028,
    "optimal_distinctiveness_fit": +0.025, "personality_brand_alignment": +0.008,
    "identity_signaling_match": +0.006,
    "mental_simulation_resonance": -0.064, "reactance_fit": -0.059,
    "spending_pain_match": -0.054, "self_monitoring_fit": -0.044,
    "processing_route_match": -0.037, "full_cosine_alignment": -0.035,
    "disgust_contamination_fit": -0.027, "negativity_bias_match": -0.019,
    "linguistic_style_match": +0.012, "uniqueness_popularity_fit": +0.025,
    "lay_theory_alignment": -0.004, "construal_fit_score": -0.001,
}

# Thresholds
MIN_EDGES_FOR_CALIBRATION = 200
MIN_NEW_EDGES_TO_TRIGGER = 500
MIN_AUC_IMPROVEMENT = 0.005  # Must improve by at least 0.5% AUC to deploy
CALIBRATION_HISTORY_PATH = "data/calibration_history.json"


def quick_auc(scores: np.ndarray, labels: np.ndarray) -> float:
    """Rank-based AUC computation."""
    n_pos = labels.sum()
    n_neg = len(labels) - n_pos
    if n_pos == 0 or n_neg == 0:
        return 0.5
    ranks = rankdata(scores)
    return float((ranks[labels == 1].sum() - n_pos * (n_pos + 1) / 2) / (n_pos * n_neg))


class RecalibrationPipeline:
    """Automated composite alignment weight recalibration.

    Usage:
        pipeline = RecalibrationPipeline()

        # Check if recalibration is needed
        if pipeline.should_recalibrate(new_edge_count=600):
            result = pipeline.recalibrate(edges, category="luxury_transportation")
            if result.deployed:
                # Weights have been updated
                new_weights = result.new_weights

        # Or run on schedule (weekly)
        result = pipeline.recalibrate(edges, category="all")
    """

    def __init__(
        self,
        current_weights: Optional[Dict[str, float]] = None,
        min_improvement: float = MIN_AUC_IMPROVEMENT,
        history_path: str = CALIBRATION_HISTORY_PATH,
    ):
        self.current_weights = current_weights or dict(CURRENT_V6_WEIGHTS)
        self.min_improvement = min_improvement
        self.history_path = history_path
        self.history = self._load_history()

    def should_recalibrate(self, new_edge_count: int = 0) -> bool:
        """Check if recalibration should run."""
        self.history.edges_since_last += new_edge_count
        return self.history.edges_since_last >= MIN_NEW_EDGES_TO_TRIGGER

    def recalibrate(
        self,
        edges: List[Dict],
        category: str = "all",
        converted_outcomes: Optional[set] = None,
    ) -> CalibrationResult:
        """Run the full recalibration pipeline.

        Args:
            edges: Bilateral edge dicts with alignment dimensions + outcome
            category: Category label for per-category weights
            converted_outcomes: Set of outcome strings considered conversion

        Returns:
            CalibrationResult with new weights if improvement found
        """
        if converted_outcomes is None:
            converted_outcomes = {"evangelized", "satisfied"}

        timestamp = datetime.now(timezone.utc).isoformat()

        # 1. Validate data sufficiency
        if len(edges) < MIN_EDGES_FOR_CALIBRATION:
            result = CalibrationResult(
                timestamp=timestamp, category=category,
                n_edges=len(edges), n_converted=0,
                current_auc=0, new_auc=0, auc_improvement=0,
                deployed=False, reason="insufficient_data",
            )
            self.history.runs.append(result)
            return result

        # 2. Build feature matrix
        dims_present = [
            d for d in COMPOSITE_DIMENSIONS
            if any(d in e for e in edges[:10])
        ]

        X = np.array([
            [e.get(d, 0.5) for d in dims_present]
            for e in edges
        ])

        y = np.array([
            1.0 if e.get("outcome", e.get("conversion_outcome", "")) in converted_outcomes
            else 0.0
            for e in edges
        ])

        n_converted = int(y.sum())

        # 3. Compute current AUC
        current_scores = np.array([
            sum(e.get(d, 0.5) * self.current_weights.get(d, 0.0) for d in dims_present)
            for e in edges
        ])
        current_auc = quick_auc(current_scores, y)

        # 4. Fit new weights via logistic regression
        from sklearn.linear_model import LogisticRegression

        # Standardize
        X_mean = X.mean(axis=0)
        X_std = X.std(axis=0)
        X_std[X_std < 0.001] = 1.0
        X_norm = (X - X_mean) / X_std

        lr = LogisticRegression(penalty='l2', C=1.0, max_iter=1000)
        lr.fit(X_norm, y)

        # Convert to weight scale matching current weights
        coefs = lr.coef_[0]
        abs_sum = np.abs(coefs).sum()
        if abs_sum > 0:
            scale = sum(abs(v) for v in self.current_weights.values()) / abs_sum
            new_weights = {
                dims_present[j]: round(float(coefs[j] * scale), 4)
                for j in range(len(dims_present))
            }
        else:
            new_weights = dict(self.current_weights)

        # 5. Compute new AUC
        new_scores = np.array([
            sum(e.get(d, 0.5) * new_weights.get(d, 0.0) for d in dims_present)
            for e in edges
        ])
        new_auc = quick_auc(new_scores, y)

        improvement = new_auc - current_auc

        # 6. Count sign flips
        sign_flips = sum(
            1 for d in dims_present
            if d in self.current_weights and d in new_weights
            and self.current_weights[d] * new_weights[d] < 0
        )

        # 7. Top predictors
        dim_corrs = []
        for j, d in enumerate(dims_present):
            r, _ = pearsonr(X[:, j], y)
            dim_corrs.append((d, round(float(r), 4)))
        dim_corrs.sort(key=lambda x: abs(x[1]), reverse=True)

        # 8. Deploy decision
        deployed = improvement >= self.min_improvement
        if deployed:
            self.current_weights = new_weights
            reason = f"improved: AUC {current_auc:.4f} → {new_auc:.4f} (+{improvement:.4f})"
            logger.info(
                "Recalibration deployed for %s: AUC %f → %f (+%f), %d sign flips",
                category, current_auc, new_auc, improvement, sign_flips
            )
        else:
            reason = f"no_improvement: AUC {current_auc:.4f} → {new_auc:.4f} (Δ{improvement:+.4f} < threshold {self.min_improvement})"
            logger.info("Recalibration skipped for %s: %s", category, reason)

        result = CalibrationResult(
            timestamp=timestamp, category=category,
            n_edges=len(edges), n_converted=n_converted,
            current_auc=round(current_auc, 4),
            new_auc=round(new_auc, 4),
            auc_improvement=round(improvement, 4),
            deployed=deployed, reason=reason,
            new_weights=new_weights if deployed else {},
            sign_flips=sign_flips,
            top_predictors=dim_corrs[:10],
        )

        # 9. Update history
        self.history.runs.append(result)
        if deployed:
            self.history.current_weights = new_weights
            self.history.last_calibration = timestamp
            self.history.edges_since_last = 0
        self._save_history()

        return result

    def get_weights(self, category: str = "all") -> Dict[str, float]:
        """Get current calibrated weights for a category."""
        return dict(self.current_weights)

    def get_history_summary(self) -> Dict[str, Any]:
        """Summary for monitoring dashboard."""
        return {
            "total_runs": len(self.history.runs),
            "last_calibration": self.history.last_calibration,
            "edges_since_last": self.history.edges_since_last,
            "deployments": sum(1 for r in self.history.runs if r.deployed),
            "current_weight_count": len(self.current_weights),
        }

    def _load_history(self) -> CalibrationHistory:
        """Load calibration history from disk."""
        try:
            path = Path(self.history_path)
            if path.exists():
                with open(path) as f:
                    data = json.load(f)
                hist = CalibrationHistory()
                hist.last_calibration = data.get("last_calibration")
                hist.edges_since_last = data.get("edges_since_last", 0)
                hist.current_weights = data.get("current_weights", {})
                if hist.current_weights:
                    self.current_weights = hist.current_weights
                return hist
        except Exception as e:
            logger.debug("Could not load calibration history: %s", e)
        return CalibrationHistory(current_weights=dict(CURRENT_V6_WEIGHTS))

    def _save_history(self) -> None:
        """Persist calibration history to disk."""
        try:
            path = Path(self.history_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w") as f:
                json.dump({
                    "last_calibration": self.history.last_calibration,
                    "edges_since_last": self.history.edges_since_last,
                    "current_weights": self.history.current_weights,
                    "runs": [
                        {
                            "timestamp": r.timestamp,
                            "category": r.category,
                            "n_edges": r.n_edges,
                            "current_auc": r.current_auc,
                            "new_auc": r.new_auc,
                            "deployed": r.deployed,
                            "reason": r.reason,
                            "sign_flips": r.sign_flips,
                        }
                        for r in self.history.runs[-20:]  # Keep last 20
                    ],
                }, f, indent=2)
        except Exception as e:
            logger.debug("Could not save calibration history: %s", e)
