# =============================================================================
# Spine #5 Option C — HierarchicalGoalStateModel (NumPyro SVI)
# Location: adam/intelligence/goal_state_hierarchical_model.py
# =============================================================================
"""Hierarchical Bayesian multi-label goal-state model (NumPyro SVI).

Slice 17c — Option C implementation of the GoalStatePriorModel
Protocol from free_energy.py. Per-goal Bernoulli posteriors with
hierarchical pooling across the 14 goals; trained via Stochastic
Variational Inference on multi-label
(page_features, active_goal_states) tuples.

Per directive Spine #5 line 216 + the broader Bayesian commitment
across the platform (BONG, hierarchical_bayes.py, M3 substrate).
This is the directive-faithful model: native multi-label, posterior
uncertainty, hierarchical pooling that tolerates fewer labels than
single-task logistic regression.

CONTRAST WITH OPTION B (LogisticGoalStateModel)
------------------------------------------------

  Logistic (B):    multinomial single-task, dense MLE point
                   estimates, sklearn predict_proba.

  Hierarchical (C): per-goal Bernoulli with hierarchical pooling,
                    multi-label labels, NumPyro SVI variational
                    posterior, samples-based predict.

The B + C dual-eval (Slice 17d) lets pilot data show which is
stronger per goal state. Same GoalStatePriorModel Protocol; same
GoalStatePosterior output shape; only the inference machinery
differs.

MODEL STRUCTURE

For each labeled (page_features, active_goals_set):
    for each goal g in inventory:
        logit_g = α_g + β_g · features
        active_g ~ Bernoulli(sigmoid(logit_g))

    Hierarchical priors:
        α_g ~ N(α_pop, σ_α)            per-goal intercept,
                                       pooled toward population mean
        β_g_d ~ N(0, σ_β)              regression coefficients,
                                       pooled toward zero (regularization)

    Hyperpriors:
        α_pop ~ N(0, 5)
        σ_α, σ_β ~ HalfNormal(1.0)

INFERENCE

NumPyro SVI with AutoNormal guide. Posterior over the variational
parameters; predict_p uses posterior point-estimates (modal) for
fast decision-time prediction.

OUTPUT SHAPING

The hierarchical model is multi-label internally (each goal has its
own Bernoulli). For the GoalStatePosterior shape (probabilities
sum to ~1 by convention), the output is RENORMALIZED across goals:

    p(g | s, c) = sigmoid(α̂_g + β̂_g · features)
                / Σ_g' sigmoid(α̂_g' + β̂_g' · features)

This makes B and C directly comparable — the cascade integration
+ free-energy math operate on the same shape regardless of model.
The "multi-label" advantage of C operates on the TRAINING side
(can train on labels where multiple goals coactivate) and the
INFERENCE side (posterior uncertainty propagates through the
hierarchical structure), not on the output shape.

DISCIPLINE (B3-LUXY a/b/c/d)
----------------------------

(a) Citations: directive Spine #5 line 216; hierarchical Bayesian
    inference (Gelman et al. 2013); SVI variational families
    (Hoffman et al. 2013); NumPyro AutoNormal guide; per-goal
    Bernoulli with hierarchical pooling (M3 substrate pattern from
    hierarchical_bayes.py 4e02e5b).

(b) Tests pin: import-skip when numpyro absent; train + predict
    round-trip with synthetic multi-label labels; predict
    concentrates on goals seen as active in training; predict_q
    delegates to closed_form_q_from_p with this model's name;
    soft-fail to passthrough when untrained; soft-fail to
    passthrough when train fails.

(c) calibration_pending=True. SVI_NUM_STEPS / SVI_LEARNING_RATE
    are conservative pre-pilot defaults; LUXY pilot data + held-out
    evaluation will calibrate. A14 flag:
    SPINE_5_HIERARCHICAL_SVI_HYPERPARAMS_PILOT_PENDING.

(d) Honest tags — what is NOT in this slice (named successors):

    * Claude API label generator (Slice 18 / Section 6.2).
    * Variational guide tuning (AutoMultivariateNormal vs AutoNormal,
      structured guides) — sibling once posterior shape complexity
      is observed.
    * MCMC fallback for posterior diagnostics (NUTS via Section 1
      Spine #1 Path C). v0.1 ships SVI for speed; HMC is sibling
      research-grade comparison.
    * Online posterior update (BONG-style natural gradient on the
      hierarchical structure). v0.1 batches; online is sibling.
    * Cohort-conditional priors. Spine #7 (BLOCKED on Loop B);
      sibling.
    * User-state conditioning. v0.1 features are page-only; adding
      BONG mean / archetype one-hot is sibling.
    * Per-goal hyperprior introspection / dashboard. The variational
      posterior carries σ_α / σ_β estimates that diagnose pooling
      strength; surfacing those is sibling visualization.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np

from adam.intelligence.free_energy import (
    GoalStatePosterior,
    PassthroughGoalStateModel,
    closed_form_q_from_p,
)
from adam.intelligence.goal_state_inventory import (
    list_goal_states,
)
from adam.intelligence.goal_state_logistic_model import (
    extract_feature_vector,
    feature_vector_dim,
)

logger = logging.getLogger(__name__)


# =============================================================================
# A14 calibration-pending hyperparameters
# =============================================================================

# A14 SPINE_5_HIERARCHICAL_SVI_HYPERPARAMS_PILOT_PENDING
SVI_NUM_STEPS: int = 2000
"""SVI iteration count. 2000 is conservative; LUXY data + held-out
ELBO trajectory will calibrate."""

SVI_LEARNING_RATE: float = 0.01
"""Adam learning rate for the SVI optimizer."""

PRIOR_ALPHA_POP_SCALE: float = 5.0
"""Scale of the population-level intercept prior. Wide → weak prior."""

PRIOR_SIGMA_HALFNORM_SCALE: float = 1.0
"""Scale of the half-normal hyperpriors on σ_α, σ_β."""

EPSILON_PROB: float = 1e-9
"""Numerical floor for probabilities — prevents log(0) downstream."""


def _try_import_numpyro() -> Optional[Any]:
    try:
        import numpyro  # noqa: F401
        return numpyro
    except ImportError:
        return None


def _goal_state_ids_sorted() -> List[str]:
    return sorted(g.id for g in list_goal_states())


# =============================================================================
# HierarchicalGoalStateModel
# =============================================================================


class HierarchicalGoalStateModel:
    """NumPyro SVI multi-label hierarchical Bayesian model.

    Implements GoalStatePriorModel Protocol. Soft-fails to
    PassthroughGoalStateModel when NumPyro isn't available OR the
    model isn't trained yet.

    Lifecycle:
        model = HierarchicalGoalStateModel()
        model.train(multi_label_pairs)              # offline SVI
        p = model.predict_p(page_features)          # decision-time
        q = model.predict_q(p, candidate_mechanism) # decision-time

    Multi-label labels: each tuple is (page_features,
    set_of_active_goal_state_ids). A page can be labeled with
    multiple goals — the model handles this natively (one Bernoulli
    per goal) where Logistic Regression (Option B) cannot.
    """

    def __init__(self) -> None:
        self._params: Optional[Dict[str, Any]] = None
        # Variational parameter point estimates, keyed by site name.
        self._goal_state_ids: List[str] = _goal_state_ids_sorted()
        self._fallback = PassthroughGoalStateModel()
        self._n_train_samples: int = 0
        self._feature_dim: int = feature_vector_dim()

    @property
    def model_name(self) -> str:
        return "hierarchical_bayes_v1"

    @property
    def is_trained(self) -> bool:
        return self._params is not None

    @property
    def n_train_samples(self) -> int:
        return self._n_train_samples

    def train(
        self,
        labeled_pairs: List[Tuple[Dict[str, Any], Set[str]]],
        *,
        num_steps: int = SVI_NUM_STEPS,
        learning_rate: float = SVI_LEARNING_RATE,
    ) -> bool:
        """Fit the hierarchical Bayesian model via SVI.

        Args:
            labeled_pairs: list of (page_features, active_goal_state_ids)
                tuples. The set of active goals can have any size
                from 0 to len(inventory). Multi-label is the
                differentiator vs Option B.
            num_steps: SVI iterations.
            learning_rate: optimizer learning rate.

        Returns True on successful fit; False when:
          - NumPyro unavailable
          - empty labeled_pairs
          - all-empty active-goals (no positive labels)
          - SVI fails to converge / raises
        """
        numpyro = _try_import_numpyro()
        if numpyro is None:
            logger.warning(
                "HierarchicalGoalStateModel.train: numpyro not installed; "
                "model stays untrained → predict_p falls back to "
                "passthrough."
            )
            return False

        if not labeled_pairs:
            logger.warning(
                "HierarchicalGoalStateModel.train: empty labels"
            )
            return False

        try:
            import jax
            import jax.numpy as jnp
            import numpyro
            import numpyro.distributions as dist
            from numpyro.infer import SVI, Trace_ELBO
            from numpyro.infer.autoguide import AutoNormal
        except ImportError as exc:
            logger.warning(
                "HierarchicalGoalStateModel.train: numpyro deps missing: %s",
                exc,
            )
            return False

        # Build training tensors
        X = np.array([
            extract_feature_vector(features)
            for features, _ in labeled_pairs
        ])
        # Y[i, g] = 1 if goal g is active for sample i, else 0
        n_samples = len(labeled_pairs)
        n_goals = len(self._goal_state_ids)
        Y = np.zeros((n_samples, n_goals), dtype=np.float32)
        for i, (_, active_set) in enumerate(labeled_pairs):
            for j, gid in enumerate(self._goal_state_ids):
                if gid in active_set:
                    Y[i, j] = 1.0

        if Y.sum() == 0.0:
            logger.warning(
                "HierarchicalGoalStateModel.train: all labels have empty "
                "active-goal sets — no positive labels to fit"
            )
            return False

        n_features = X.shape[1]

        def _model(features: jnp.ndarray, observations: jnp.ndarray) -> None:
            """Hierarchical multi-label Bernoulli model."""
            n_obs, _ = features.shape
            n_g = len(self._goal_state_ids)

            # Hyperpriors
            alpha_pop = numpyro.sample(
                "alpha_pop", dist.Normal(0.0, PRIOR_ALPHA_POP_SCALE),
            )
            sigma_alpha = numpyro.sample(
                "sigma_alpha",
                dist.HalfNormal(PRIOR_SIGMA_HALFNORM_SCALE),
            )
            sigma_beta = numpyro.sample(
                "sigma_beta",
                dist.HalfNormal(PRIOR_SIGMA_HALFNORM_SCALE),
            )

            # Per-goal intercepts (pooled toward alpha_pop)
            with numpyro.plate("goals_alpha", n_g):
                alpha = numpyro.sample(
                    "alpha", dist.Normal(alpha_pop, sigma_alpha),
                )

            # Per-(goal, feature) coefficients (pooled toward 0)
            with numpyro.plate("goals_beta", n_g):
                with numpyro.plate("features", n_features):
                    beta = numpyro.sample(
                        "beta", dist.Normal(0.0, sigma_beta),
                    )

            # Likelihood: per-(obs, goal) Bernoulli
            # logits[i, g] = alpha[g] + sum_d (beta[d, g] * features[i, d])
            logits = alpha[None, :] + features @ beta  # (n_obs, n_g)
            with numpyro.plate("observations", n_obs):
                with numpyro.plate("goals_obs", n_g):
                    numpyro.sample(
                        "y", dist.Bernoulli(logits=logits.T),
                        obs=observations.T,
                    )

        try:
            guide = AutoNormal(_model)
            optimizer = numpyro.optim.Adam(step_size=learning_rate)
            svi = SVI(_model, guide, optimizer, loss=Trace_ELBO())

            rng_key = jax.random.PRNGKey(0)
            X_jax = jnp.asarray(X)
            Y_jax = jnp.asarray(Y)

            svi_result = svi.run(
                rng_key, num_steps, X_jax, Y_jax, progress_bar=False,
            )
            params = svi_result.params

            # Extract point estimates from the guide's variational params.
            # AutoNormal stores _auto_loc / _auto_scale per site.
            self._params = {
                "alpha": np.asarray(params["alpha_auto_loc"]),
                "beta": np.asarray(params["beta_auto_loc"]),
            }
        except Exception as exc:
            logger.warning(
                "HierarchicalGoalStateModel.train: SVI failed: %s", exc,
            )
            return False

        self._n_train_samples = n_samples
        return True

    def predict_p(
        self,
        page_features: Dict[str, Any],
        user_state: Optional[Dict[str, float]] = None,
    ) -> GoalStatePosterior:
        """Predict p(goal | s, c). Falls back to passthrough when
        untrained.

        Output is renormalized across goals so probabilities sum to
        ~1 (the GoalStatePosterior multinomial-shape contract).
        Internally the model is multi-label (per-goal Bernoulli);
        the renormalization compresses to multinomial for the
        free-energy math + dual-eval comparability with Option B.
        """
        if self._params is None:
            fallback = self._fallback.predict_p(page_features, user_state)
            return GoalStatePosterior(
                probabilities=fallback.probabilities,
                model_name=f"{self.model_name}:fallback_passthrough",
            )

        x = extract_feature_vector(page_features)
        try:
            alpha = self._params["alpha"]              # (n_goals,)
            beta = self._params["beta"]                # (n_features, n_goals)
            logits = alpha + x @ beta                  # (n_goals,)
            # Sigmoid → per-goal active probability
            sigmoid = 1.0 / (1.0 + np.exp(-logits))
        except Exception as exc:
            logger.warning(
                "HierarchicalGoalStateModel.predict_p: numerical failure: %s",
                exc,
            )
            fallback = self._fallback.predict_p(page_features, user_state)
            return GoalStatePosterior(
                probabilities=fallback.probabilities,
                model_name=f"{self.model_name}:fallback_predict_error",
            )

        # Renormalize across goals → multinomial-shaped output
        total = float(sigmoid.sum())
        if total <= EPSILON_PROB:
            fallback = self._fallback.predict_p(page_features, user_state)
            return GoalStatePosterior(
                probabilities=fallback.probabilities,
                model_name=f"{self.model_name}:fallback_zero_mass",
            )

        probabilities: Dict[str, float] = {}
        for j, gid in enumerate(self._goal_state_ids):
            probabilities[gid] = float(sigmoid[j] / total)

        return GoalStatePosterior(
            probabilities=probabilities,
            model_name=self.model_name,
        )

    def predict_q(
        self,
        p: GoalStatePosterior,
        candidate_mechanism: str,
    ) -> GoalStatePosterior:
        """Closed-form Bayesian update — same as B and passthrough.

        The goal-conditional likelihood is the inventory's
        mechanism_priors regardless of which model produced p, so
        all three options share predict_q logic. Tagged with this
        model's name for dual-eval attribution.
        """
        return closed_form_q_from_p(
            p, candidate_mechanism, model_name=self.model_name,
        )
