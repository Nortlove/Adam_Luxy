# =============================================================================
# Resonance Engineering — Layer 2: MODEL
# Location: adam/retargeting/resonance/resonance_model.py
# =============================================================================

"""
Resonance Model — Computes R(buyer, seller, page) = base × resonance_multiplier.

Three stages of increasing sophistication:

Stage A (0-50 obs/cell): Theory prior — dot product with ideal vectors
Stage B (50-500 obs):    Empirical — logistic regression on observed data
Stage C (500+ obs):      Neural — MLP capturing non-linear trilateral interactions

The model is per-cell: each (mechanism, barrier, archetype) combination
has its own stage. Common combinations advance faster. Rare ones inherit
from the hierarchy.
"""

import logging
import math
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from adam.retargeting.resonance.models import (
    PageMindstateVector,
    ResonanceScore,
    MINDSTATE_DIM_COUNT,
)
from adam.retargeting.resonance.cold_start import (
    compute_theory_resonance,
    compute_all_mechanism_resonances,
    get_ideal_vector,
)
from adam.retargeting.resonance.resonance_gradient import (
    compute_resonance_gradient,
    rank_dimensions_by_resonance_impact,
)

logger = logging.getLogger(__name__)

# Stage thresholds
STAGE_B_MIN_OBS = 50
STAGE_C_MIN_OBS = 500


@dataclass
class ResonanceCellState:
    """Tracks the learning state for one (mechanism, barrier, archetype) cell."""

    mechanism: str
    barrier: str
    archetype: str

    # Observation count
    n_observations: int = 0

    # Stage B weights (logistic regression coefficients)
    stage_b_weights: Optional[np.ndarray] = None
    stage_b_intercept: float = 0.0
    stage_b_fitted_at: float = 0.0

    # Stage C model (placeholder for neural network)
    stage_c_model: Optional[Any] = None

    # Observations buffer for fitting Stage B
    obs_page_vectors: List[np.ndarray] = field(default_factory=list)
    obs_outcomes: List[float] = field(default_factory=list)

    @property
    def current_stage(self) -> str:
        if self.stage_c_model is not None and self.n_observations >= STAGE_C_MIN_OBS:
            return "C"
        elif self.stage_b_weights is not None and self.n_observations >= STAGE_B_MIN_OBS:
            return "B"
        return "A"

    def record_observation(
        self,
        page_vector: np.ndarray,
        outcome: float,
        weight: float = 1.0,
    ) -> None:
        """Record a (page_mindstate, outcome) observation for this cell.

        Args:
            weight: Design-effect weight (0-1). Discounts correlated
                within-subject observations for Stage B fitting. Stored
                alongside the observation and used as sample_weight
                in logistic regression.
        """
        self.n_observations += 1
        self.obs_page_vectors.append(page_vector)
        self.obs_outcomes.append(outcome)
        # Store weight for Stage B fitting — if not tracking weights yet,
        # initialize with 1.0 for all prior observations
        if not hasattr(self, 'obs_weights'):
            self.obs_weights: List[float] = [1.0] * (len(self.obs_outcomes) - 1)
        self.obs_weights.append(weight)

        # Keep buffer manageable (last 2000 observations)
        if len(self.obs_page_vectors) > 2000:
            self.obs_page_vectors = self.obs_page_vectors[-2000:]
            self.obs_outcomes = self.obs_outcomes[-2000:]
            if hasattr(self, 'obs_weights'):
                self.obs_weights = self.obs_weights[-2000:]

        # Auto-fit Stage B when enough data
        if (self.n_observations >= STAGE_B_MIN_OBS
                and self.stage_b_weights is None
                and len(self.obs_page_vectors) >= STAGE_B_MIN_OBS):
            self._fit_stage_b()

    def _fit_stage_b(self) -> None:
        """Fit logistic regression for Stage B resonance model."""
        try:
            from sklearn.linear_model import LogisticRegression

            X = np.array(self.obs_page_vectors)
            y = np.array(self.obs_outcomes)

            # Need both classes
            if len(set(y)) < 2:
                return

            # Use design-effect weights for sample weighting if available
            sample_weights = None
            if hasattr(self, 'obs_weights') and len(self.obs_weights) == len(y):
                sample_weights = np.array(self.obs_weights)

            lr = LogisticRegression(penalty='l2', C=0.5, max_iter=500)
            lr.fit(X, y, sample_weight=sample_weights)

            self.stage_b_weights = lr.coef_[0]
            self.stage_b_intercept = float(lr.intercept_[0])
            self.stage_b_fitted_at = time.time()

            logger.info(
                "Stage B fitted for %s/%s/%s (n=%d)",
                self.mechanism, self.barrier, self.archetype, self.n_observations,
            )
        except Exception as e:
            logger.debug("Stage B fit failed: %s", e)


class ResonanceModel:
    """Computes resonance multiplier for (buyer, mechanism, page) triples.

    Usage:
        model = ResonanceModel()

        # Compute resonance for a single decision
        score = model.compute_resonance(
            page_mindstate=page_mv,
            mechanism="evidence_proof",
            barrier="trust_deficit",
            archetype="careful_truster",
        )

        # After outcome, update the model
        model.record_outcome(
            page_mindstate=page_mv,
            mechanism="evidence_proof",
            barrier="trust_deficit",
            archetype="careful_truster",
            converted=True,
        )
    """

    def __init__(self):
        # Per-cell learning state
        self._cells: Dict[Tuple[str, str, str], ResonanceCellState] = {}

    def compute_resonance(
        self,
        page_mindstate: PageMindstateVector,
        mechanism: str,
        barrier: str = "",
        archetype: str = "",
        base_conversion_probability: float = 0.5,
        buyer_covariance: Optional[np.ndarray] = None,
        epistemic_weight: float = 0.2,
    ) -> ResonanceScore:
        """Compute the resonance multiplier for this configuration.

        Automatically selects the appropriate stage (A/B/C) based on
        the data available for this cell.

        When buyer_covariance is provided (from BONG posterior), adds an
        epistemic resonance bonus for pages that resolve high-uncertainty
        buyer dimensions. This connects information value bidding to
        page prescription — pages that TEACH us about the buyer get
        higher resonance even if the exploitation resonance is moderate.

        Args:
            page_mindstate: 32-dim page psychological field
            mechanism: TherapeuticMechanism being deployed
            barrier: BarrierCategory being targeted (empty for first-touch)
            archetype: User archetype
            base_conversion_probability: P(conversion) without page context
            buyer_covariance: BONG posterior covariance (20x20 or None)
            epistemic_weight: Weight on epistemic vs exploitation resonance

        Returns:
            ResonanceScore with multiplier and contributing dimensions
        """
        cell = self._get_cell(mechanism, barrier, archetype)
        stage = cell.current_stage

        if stage == "B" and cell.stage_b_weights is not None:
            multiplier = self._compute_stage_b(page_mindstate, cell)
        elif stage == "C" and cell.stage_c_model is not None:
            multiplier = self._compute_stage_c(page_mindstate, cell)
        else:
            multiplier = compute_theory_resonance(page_mindstate, mechanism)

        # Confidence-weight: low-confidence pages get multiplier compressed toward 1.0
        confidence = page_mindstate.confidence
        weighted_multiplier = 1.0 + (multiplier - 1.0) * confidence

        effective_prob = min(0.95, max(0.01,
            base_conversion_probability * weighted_multiplier
        ))

        # Contributing dimensions
        gradient = compute_resonance_gradient(mechanism, page_mindstate)
        from adam.retargeting.resonance.models import ALL_MINDSTATE_DIMS
        page_vec = page_mindstate.to_numpy()
        top_contributors = []
        for dim, grad in list(gradient.items())[:5]:
            idx = ALL_MINDSTATE_DIMS.index(dim) if dim in ALL_MINDSTATE_DIMS else -1
            top_contributors.append({
                "dimension": dim,
                "gradient": grad,
                "page_value": round(float(page_vec[idx]), 3) if idx >= 0 else 0.0,
            })

        # BONG epistemic bonus: pages that resolve buyer uncertainty get
        # additional resonance. This connects information value to placement.
        epistemic_resonance = 0.0
        if buyer_covariance is not None and epistemic_weight > 0:
            try:
                page_edge_dims = page_vec[:min(20, len(page_vec))]
                buyer_cov_d = min(20, buyer_covariance.shape[0])
                page_trimmed = page_edge_dims[:buyer_cov_d]
                cov_trimmed = buyer_covariance[:buyer_cov_d, :buyer_cov_d]
                # How uncertain is this buyer along the dims this page activates?
                uncertainty_along_page = float(page_trimmed @ cov_trimmed @ page_trimmed)
                epistemic_resonance = 0.5 * np.log1p(max(0, uncertainty_along_page))
                weighted_multiplier += epistemic_weight * epistemic_resonance
                # Re-clamp effective probability
                effective_prob = min(0.95, max(0.01,
                    base_conversion_probability * weighted_multiplier
                ))
            except Exception:
                pass  # BONG not available or dimension mismatch

        return ResonanceScore(
            base_conversion_probability=round(base_conversion_probability, 4),
            resonance_multiplier=round(weighted_multiplier, 4),
            effective_probability=round(effective_prob, 4),
            contributing_dimensions=top_contributors,
            confidence=round(confidence, 3),
            model_stage=stage,
            mechanism=mechanism,
            barrier=barrier,
            archetype=archetype,
        )

    def compute_all_resonances(
        self,
        page_mindstate: PageMindstateVector,
        candidate_mechanisms: Optional[List[str]] = None,
        barrier: str = "",
        archetype: str = "",
    ) -> Dict[str, float]:
        """Compute resonance for all candidate mechanisms on this page.

        Returns {mechanism: resonance_multiplier} sorted by resonance.
        """
        if candidate_mechanisms is None:
            from adam.constants import THERAPEUTIC_MECHANISMS
            candidate_mechanisms = THERAPEUTIC_MECHANISMS

        resonances = {}
        for mech in candidate_mechanisms:
            score = self.compute_resonance(
                page_mindstate, mech, barrier, archetype
            )
            resonances[mech] = score.resonance_multiplier

        return dict(sorted(resonances.items(), key=lambda x: x[1], reverse=True))

    def record_outcome(
        self,
        page_mindstate: PageMindstateVector,
        mechanism: str,
        barrier: str,
        archetype: str,
        converted: bool,
        engagement_score: float = 0.0,
        weight: float = 1.0,
    ) -> None:
        """Record an outcome to update the resonance model.

        Feeds the observation to the appropriate cell for Stage B/C training.

        Args:
            weight: Design-effect weight (0-1). Within-subject repeated
                observations are correlated, so a user who sees 7 touches
                contributes less than 7 independent observations. The weight
                discounts the observation's influence on Stage B fitting.
        """
        cell = self._get_cell(mechanism, barrier, archetype)
        page_vec = page_mindstate.to_numpy()
        outcome = 1.0 if converted else (0.3 if engagement_score > 0.1 else 0.0)
        cell.record_observation(page_vec, outcome, weight=weight)

    def _compute_stage_b(
        self,
        page_mindstate: PageMindstateVector,
        cell: ResonanceCellState,
    ) -> float:
        """Stage B: logistic regression resonance multiplier."""
        page_vec = page_mindstate.to_numpy()
        logit = float(np.dot(cell.stage_b_weights, page_vec) + cell.stage_b_intercept)

        # Map logit to resonance multiplier [0.3, 3.0]
        prob = 1.0 / (1.0 + math.exp(-logit))
        return 0.3 + prob * 2.7

    def _compute_stage_c(
        self,
        page_mindstate: PageMindstateVector,
        cell: ResonanceCellState,
    ) -> float:
        """Stage C: neural network resonance multiplier (placeholder)."""
        # When implemented: cell.stage_c_model.predict(page_vec)
        # For now, fall back to Stage B or A
        if cell.stage_b_weights is not None:
            return self._compute_stage_b(page_mindstate, cell)
        return compute_theory_resonance(page_mindstate, cell.mechanism)

    def _get_cell(self, mechanism: str, barrier: str, archetype: str) -> ResonanceCellState:
        """Get or create a cell for this (mechanism, barrier, archetype) triple."""
        key = (mechanism, barrier, archetype)
        if key not in self._cells:
            self._cells[key] = ResonanceCellState(
                mechanism=mechanism, barrier=barrier, archetype=archetype
            )
        return self._cells[key]

    @property
    def stats(self) -> Dict[str, Any]:
        """Model statistics for monitoring."""
        cells_by_stage = {"A": 0, "B": 0, "C": 0}
        total_obs = 0
        for cell in self._cells.values():
            cells_by_stage[cell.current_stage] += 1
            total_obs += cell.n_observations

        return {
            "total_cells": len(self._cells),
            "cells_by_stage": cells_by_stage,
            "total_observations": total_obs,
        }
