# =============================================================================
# Counterfactual Learning via Propensity-Weighted Imputation
# Location: adam/intelligence/counterfactual_learner.py
# Unified System Evolution Directive, Section 3
# =============================================================================

"""
For each impression where mechanism A was deployed, estimates what
non-deployed mechanisms B, C, D... WOULD have produced, then feeds
those imputed observations through BONG with discounted precision.

This is NOT a standalone estimator. It feeds back into the existing
BONG updater as noisy observations. The BONG update rule already
accepts a `noise_precision` parameter — counterfactual observations
get lower precision (more noise = less trusted).

Result: every impression teaches about ALL candidate mechanisms,
not just the one deployed. Learning convergence multiplied.
"""

import logging
from typing import Dict, List, Optional

import numpy as np

from adam.retargeting.engines.mechanism_observation_models import (
    get_mechanism_vector,
    get_all_mechanism_vectors,
)

logger = logging.getLogger(__name__)

# Maximum precision weight for counterfactual observations.
# Direct observations get precision ~1.0; counterfactuals are always less.
MAX_COUNTERFACTUAL_PRECISION = 0.30


class CounterfactualLearner:
    """Generates counterfactual outcome estimates for non-deployed mechanisms.

    NOT a standalone estimator. Feeds imputed observations back into the
    existing BONG updater with discounted precision.

    The precision discount reflects:
    - How similar is the non-deployed mechanism to the deployed one?
    - How close was the selection decision? (propensity informativeness)

    Similar mechanisms with close selection decisions → more confident
    counterfactual. Dissimilar mechanisms or lopsided decisions → less
    confident.
    """

    def __init__(self):
        self.mechanism_vectors = get_all_mechanism_vectors()
        self.total_counterfactuals_generated = 0
        self.total_fed_to_bong = 0

    def compute_counterfactual_observations(
        self,
        deployed_mechanism: str,
        deployed_outcome_shift: np.ndarray,
        mechanism_probabilities: Dict[str, float],
        candidate_mechanisms: List[str],
    ) -> List[Dict]:
        """For each non-deployed mechanism, estimate what the observation
        WOULD have been and how confident we are in that estimate.

        Args:
            deployed_mechanism: Which mechanism was actually deployed
            deployed_outcome_shift: 20-dim observed shift (post - pre BONG mean)
            mechanism_probabilities: P(selected) per mechanism from Thompson Sampling
            candidate_mechanisms: All mechanisms that were candidates

        Returns:
            List of imputed observations, each with:
            - mechanism_id
            - imputed_shift (20-dim)
            - precision_weight (scalar)
            - reasoning
        """
        deployed_prob = mechanism_probabilities.get(deployed_mechanism, 0.5)
        deployed_vec = get_mechanism_vector(deployed_mechanism)

        counterfactuals = []

        for mechanism in candidate_mechanisms:
            if mechanism == deployed_mechanism:
                continue

            mech_prob = mechanism_probabilities.get(mechanism, 0.1)
            mech_vec = get_mechanism_vector(mechanism)

            # Similarity: how much do these mechanisms overlap in target dimensions?
            similarity = float(np.dot(deployed_vec, mech_vec))
            similarity = max(0.0, similarity)

            if similarity < 0.05:
                continue  # Too dissimilar — no useful counterfactual

            # Imputed shift: project deployed outcome onto this mechanism's dimensions
            # Intuition: if evidence_proof shifted trust by +0.08 and claude_argument
            # also targets trust (similarity=0.7), estimate claude_argument would have
            # shifted trust by ~0.08 * 0.7
            imputed_shift = deployed_outcome_shift * similarity

            # Zero out dimensions this mechanism doesn't target but deployed did
            for i in range(len(mech_vec)):
                if mech_vec[i] > 0.3 and deployed_vec[i] < 0.1:
                    imputed_shift[i] = 0.0

            # Precision: how much should BONG trust this?
            # Close decisions = informative counterfactual
            propensity_informativeness = min(
                mech_prob / max(deployed_prob, 0.01), 1.0
            )
            precision = similarity * propensity_informativeness * MAX_COUNTERFACTUAL_PRECISION

            if precision < 0.01:
                continue

            counterfactuals.append({
                "mechanism_id": mechanism,
                "imputed_shift": imputed_shift,
                "precision_weight": float(precision),
                "similarity": float(similarity),
                "propensity_informativeness": float(propensity_informativeness),
                "reasoning": (
                    f"CF for {mechanism}: similarity={similarity:.2f} with "
                    f"{deployed_mechanism}, propensity={propensity_informativeness:.2f}, "
                    f"precision={precision:.3f}"
                ),
            })

        self.total_counterfactuals_generated += len(counterfactuals)
        return counterfactuals

    def feed_counterfactuals_to_bong(
        self,
        bong_updater,
        individual_posterior,
        counterfactuals: List[Dict],
    ):
        """Feed imputed counterfactual observations into BONG with discounted precision.

        Each counterfactual is treated as a noisy observation.
        Low precision = BONG treats it as very noisy = slight posterior shift.
        """
        for cf in counterfactuals:
            # The imputed shift is relative to pre-state. Convert to absolute
            # observation by adding to current mean.
            current_mean = bong_updater.get_mean(individual_posterior)
            imputed_observation = current_mean + cf["imputed_shift"]

            bong_updater.update(
                individual=individual_posterior,
                observation=imputed_observation,
                noise_precision=cf["precision_weight"],
            )
            self.total_fed_to_bong += 1

    @property
    def learning_multiplier(self) -> float:
        """How many total updates per direct observation.

        1.0 = no counterfactuals (just direct).
        3.0 = each direct observation generates 2 additional counterfactuals.
        """
        if self.total_fed_to_bong == 0:
            return 1.0
        direct = self.total_fed_to_bong - self.total_counterfactuals_generated
        if direct <= 0:
            return float(self.total_fed_to_bong)
        return self.total_fed_to_bong / max(direct, 1)

    @property
    def stats(self) -> Dict:
        return {
            "total_counterfactuals_generated": self.total_counterfactuals_generated,
            "total_fed_to_bong": self.total_fed_to_bong,
            "learning_multiplier": round(self.learning_multiplier, 2),
        }


# Singleton
_counterfactual_learner: Optional[CounterfactualLearner] = None


def get_counterfactual_learner() -> CounterfactualLearner:
    """Get or create the singleton CounterfactualLearner."""
    global _counterfactual_learner
    if _counterfactual_learner is None:
        _counterfactual_learner = CounterfactualLearner()
    return _counterfactual_learner
