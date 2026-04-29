# =============================================================================
# ADAM Spine #1 — Per-User N-of-1 Hierarchical Bayesian Engine
# Location: adam/intelligence/spine/spine_1_n_of_1_engine.py
# =============================================================================

"""Per-User N-of-1 Hierarchical Bayesian Engine — the spine of the spine.

PER DIRECTIVE SECTION 3 (canonical specification).

The per-user posterior over psychological-mechanism efficacy under
within-subject crossover, partially pooled across users via cohort-level
hyperpriors, updated online (via BONG — Bayesian Online Natural Gradient
— for conjugate exponential-family cases, Laplace approximation otherwise)
on every observation including non-response, with the per-user random
walk modeled as a Kalman state-space layer for non-stationarity (wrapped
by Spine #10).

Why this is the spine of the spine: every other primitive composes onto
this. Without per-user posteriors, there is no causal claim to make on
any individual user, the cohort layer collapses to demographic targeting,
the bilateral edge collapses to the population-level CATE, and the
decision-time counterfactual trace becomes a fiction.

DECISION-TIME CONSUMER (Rule A check)

This module is consumed at decision time by:
    - The trilateral L3 cascade (Spine #4) which reads posterior mean +
      90% credible interval per candidate mechanism
    - The active-inference free-energy scorer (Spine #5) which reads
      posterior precision to compute the precision-weighted KL term
    - The decision-time counterfactual trace (Spine #6) which reads the
      compressed user-posterior snapshot
    - The epistemic-value bonus (Spine #8) which reads posterior precision
      to compute closed-form information gain under BONG

Therefore: NOT measurement infrastructure. Cognitive primitive at the
serving path.

THIS COMMIT SHIPS

    - Pydantic models for the hierarchical-Bayesian state (UserPosterior,
      CohortPosterior, HierarchicalPosteriorSnapshot)
    - The likelihood specification module (which outcome class contributes
      what update weight to which posterior component)
    - The natural-parameter representation enabling BONG single-step
      natural-gradient updates
    - Pure-Python reference implementations of the conjugate-update
      arithmetic (NumPy only; JAX/NumPyro acceleration is a follow-up
      commit when the spec is pinned)

THIS COMMIT DOES NOT SHIP (follow-on commits)

    - JAX-accelerated BONG (this commit's NumPy reference is the spec
      that the JAX path must match)
    - NumPyro variational batch reconcile (Path B nightly)
    - HMC offline reconcile (Path C weekly)
    - Neo4j writeback (the Pydantic models + to_neo4j_props() are ready
      for it but the wire is in the next commit)
    - Redis hot cache (next commit)
    - Spine #10 Kalman wrapper (separate spine, separate commit)

PRINCIPLES HELD

    Principle 1 (single user, not campaign): every method on this engine
    operates on a per-user posterior. No campaign-level aggregation in
    this module — the campaign-level estimand is computed by aggregating
    per-user posteriors (Spine #1 → Spine #3 → mSPRT) elsewhere.

    Principle 2 (fitness function IS the ethics): the engine produces
    posteriors only; the policy that consumes them (Spine #4 fluency
    floor, Spine #5 free-energy) is where attention-inversion is
    enforced. This module never selects an arm; it provides the
    posteriors the policy reads.

    Principle 3 (causal not associative): the engine consumes outcomes
    that are linked to served impressions via sapid (Spine #11). The
    likelihood treats every outcome as a causal observation conditional
    on the served mechanism, not a marginal correlation.

REFERENCES

    Jones, Chang & Murphy 2024 — BONG (Bayesian Online Natural Gradient).
    Tomkins et al. — IntelligentPooling (DIAMANTE / HeartSteps II).
    Gelman & Hill 2006 — partial pooling theory.
    Papaspiliopoulos 2007 — non-centered parameterization (relevant to
        Path B variational reconcile, follow-on commit).
"""

from __future__ import annotations

import json
import logging
import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field, field_validator

logger = logging.getLogger(__name__)


# =============================================================================
# Configuration constants from the directive (Section 3)
# =============================================================================


# Default per-user posterior dimensionality. Per directive: "Per-user
# 27-dimensional Gaussian update is ~20K FLOPs". The 27 dims correspond
# to the 27 matched bilateral construct dimensions (Big Five, Regulatory
# Focus, Construal Level, Need for Cognition, Self-Monitoring, Moral
# Foundations, Reactance, Transportability, NFCL, Attachment, Sensation
# Seeking, Locus of Control, Hedonic/Utilitarian, Mindset, Ownership,
# Identity, Granularity, etc.).
USER_POSTERIOR_DIM: int = 27


# Storage-shape choice. Full-covariance is 27 × 27 = 729 floats per user
# (~3 GB for 1M users in Redis hot cache). Diagonal-plus-low-rank with
# rank-3 update gives ~80 floats per user (~80 MB for 1M). Per directive
# Section 3.2: "Storage: 729 floats per user (covariance + mean for full-
# cov), or ~80 floats per user (diagonal + low-rank-3 approximation)."
# Default to full-cov; production tuning may swap to diagonal+low-rank.
DEFAULT_FULL_COVARIANCE: bool = True


# Identity-stability weight bounds. Per directive Section 3.4: "Identity-
# stability weight is itself a learned object: how often does this user's
# identity persist across sessions? This degrades smoothly under privacy-
# conscious deployment."
IDENTITY_STABILITY_MIN: float = 0.0
IDENTITY_STABILITY_MAX: float = 1.0
IDENTITY_STABILITY_DEFAULT: float = 1.0  # New user assumed stable until proven otherwise


# =============================================================================
# Outcome class likelihood-weight schema (per directive Section 3.3)
# =============================================================================


# Each outcome class contributes a different update weight to the user
# posterior. Weights are themselves in a hyperprior and learned over
# time, but the directive specifies initial defaults.
@dataclass(frozen=True)
class OutcomeWeightSchema:
    """Likelihood-weight schema per outcome class.

    Per directive Section 3.3:
        CONVERSION, MICRO_CONVERSION: Bernoulli with positive update
            weight 1.0
        CLICK_QUALIFIED, VIEWED_ENGAGED: Bernoulli with positive weight
            0.3-0.5 (partial credit; user moved the funnel but didn't
            finish)
        CLICK_BOUNCED, VIEWED_DISENGAGED: Bernoulli with negative weight
            0.5-1.0
        FREQUENCY_FATIGUE_FIRED, AUDIENCE_AGED_OUT: censoring events;
            update the survival/competing-risks structure rather than
            the binary outcome
        IMPRESSION_NON_VIEWABLE: discarded for posterior update (no
            signal); logged for accounting
    """

    weight: float
    sign: int  # +1 = positive evidence, -1 = negative evidence, 0 = no update
    is_censoring: bool = False
    description: str = ""


_DEFAULT_OUTCOME_SCHEMA: Dict[str, OutcomeWeightSchema] = {
    "CONVERSION": OutcomeWeightSchema(
        weight=1.0, sign=+1,
        description="Booking confirmed / demo requested (LUXY-defined)",
    ),
    "MICRO_CONVERSION": OutcomeWeightSchema(
        weight=1.0, sign=+1,
        description="Added to cart / started booking flow",
    ),
    "CLICK_QUALIFIED": OutcomeWeightSchema(
        weight=0.4, sign=+1,
        description="Clicked + meaningful on-site behavior",
    ),
    "VIEWED_ENGAGED": OutcomeWeightSchema(
        weight=0.3, sign=+1,
        description="Viewability + dwell ≥ threshold + scroll engagement",
    ),
    "CLICK_BOUNCED": OutcomeWeightSchema(
        weight=0.7, sign=-1,
        description="Clicked + immediate bounce (<5s on site)",
    ),
    "VIEWED_DISENGAGED": OutcomeWeightSchema(
        weight=0.5, sign=-1,
        description="Viewability + dwell < threshold",
    ),
    "FREQUENCY_FATIGUE_FIRED": OutcomeWeightSchema(
        weight=0.5, sign=-1, is_censoring=True,
        description="Frequency cap triggered with no prior engagement",
    ),
    "AUDIENCE_AGED_OUT": OutcomeWeightSchema(
        weight=0.5, sign=-1, is_censoring=True,
        description="Left audience window without conversion",
    ),
    "IMPRESSION_NON_VIEWABLE": OutcomeWeightSchema(
        weight=0.0, sign=0,
        description="Served but not viewable; discarded for posterior",
    ),
}


def get_outcome_schema(outcome_class: str) -> OutcomeWeightSchema:
    """Return the OutcomeWeightSchema for an outcome class.

    Raises ValueError when the class is not in the schema vocabulary —
    Spine #11 owns the outcome vocabulary; unknown classes here mean a
    new outcome arrived without a corresponding schema entry.
    """
    schema = _DEFAULT_OUTCOME_SCHEMA.get(outcome_class)
    if schema is None:
        raise ValueError(
            f"Unknown outcome_class '{outcome_class}'. "
            f"Add to _DEFAULT_OUTCOME_SCHEMA in spine_1_n_of_1_engine.py "
            f"AND to the Spine #11 outcome vocabulary; both must agree."
        )
    return schema


def known_outcome_classes() -> List[str]:
    """Return the list of outcome classes the schema knows about."""
    return list(_DEFAULT_OUTCOME_SCHEMA.keys())


# =============================================================================
# Pydantic models — hierarchical posterior state
# =============================================================================


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


class UserPosterior(BaseModel):
    """Per-user hierarchical-Bayesian posterior state.

    Stored as natural-parameter representation: precision matrix
    (Λ = Σ⁻¹) and precision-weighted mean (η = Λ μ). BONG single-step
    natural-gradient updates compose additively in natural-parameter
    space, which is why this representation is canonical.

    Conversion back to standard mean-and-covariance representation:
        μ = Λ⁻¹ η
        Σ = Λ⁻¹

    Storage shape:
        full_cov=True  → 729 floats per user (precision matrix flattened
                         + precision-weighted mean) for d=27
        full_cov=False → ~80 floats per user (diagonal + low-rank-3)
                         (NOT YET IMPLEMENTED in this commit)
    """

    model_config = ConfigDict(extra="forbid")

    user_id: str
    dim: int = USER_POSTERIOR_DIM

    # Natural-parameter form (canonical)
    precision_matrix_flat: List[float]    # Λ flattened; len = dim²
    precision_weighted_mean: List[float]  # η = Λ μ; len = dim

    # Cohort assignment as posterior distribution (NOT hard partition).
    # Per directive Section 3.4: "Cohort assignment is *not* a hard
    # partition. Each user has a posterior distribution over cohort
    # membership."
    cohort_membership: List[float] = Field(default_factory=list)
    cohort_ids: List[str] = Field(default_factory=list)

    # Identity-stability weight (Section 3.4).
    identity_stability: float = IDENTITY_STABILITY_DEFAULT

    # Bookkeeping
    total_observations: int = 0
    last_updated_at: datetime = Field(default_factory=_now_utc)
    last_outcome_class: Optional[str] = None

    @field_validator("identity_stability")
    @classmethod
    def _validate_identity_stability(cls, v: float) -> float:
        if not IDENTITY_STABILITY_MIN <= v <= IDENTITY_STABILITY_MAX:
            raise ValueError(
                f"identity_stability must be in "
                f"[{IDENTITY_STABILITY_MIN}, {IDENTITY_STABILITY_MAX}]; "
                f"got {v}"
            )
        return v

    @field_validator("precision_matrix_flat")
    @classmethod
    def _validate_precision_shape(
        cls, v: List[float], info,
    ) -> List[float]:
        d = info.data.get("dim", USER_POSTERIOR_DIM)
        expected = d * d
        if len(v) != expected:
            raise ValueError(
                f"precision_matrix_flat length must be dim² = "
                f"{expected} for dim={d}; got {len(v)}"
            )
        return v

    @field_validator("precision_weighted_mean")
    @classmethod
    def _validate_mean_shape(
        cls, v: List[float], info,
    ) -> List[float]:
        d = info.data.get("dim", USER_POSTERIOR_DIM)
        if len(v) != d:
            raise ValueError(
                f"precision_weighted_mean length must be dim = {d}; "
                f"got {len(v)}"
            )
        return v

    @field_validator("cohort_membership")
    @classmethod
    def _validate_cohort_membership(cls, v: List[float]) -> List[float]:
        # Allow empty (cohort assignment not yet computed).
        if not v:
            return v
        # Otherwise must sum to ~1 and be non-negative.
        for w in v:
            if w < 0.0 or w > 1.0:
                raise ValueError(
                    f"cohort_membership entries must be in [0, 1]; got {w}"
                )
        s = sum(v)
        if abs(s - 1.0) > 1e-6:
            raise ValueError(
                f"cohort_membership must sum to 1.0; got {s}"
            )
        return v

    def to_neo4j_props(self) -> Dict[str, Any]:
        """Serialize to Neo4j-property-friendly dict.

        Float arrays serialize as JSON strings (Neo4j scalar discipline);
        on read, JSON-decode back into List[float]. Dim is stored
        explicitly so reads can reshape correctly.
        """
        return {
            "user_id": self.user_id,
            "dim": int(self.dim),
            "precision_matrix_flat_json": json.dumps(self.precision_matrix_flat),
            "precision_weighted_mean_json": json.dumps(self.precision_weighted_mean),
            "cohort_membership_json": json.dumps(self.cohort_membership),
            "cohort_ids_json": json.dumps(self.cohort_ids),
            "identity_stability": float(self.identity_stability),
            "total_observations": int(self.total_observations),
            "last_updated_at": self.last_updated_at.isoformat(),
            "last_outcome_class": self.last_outcome_class or "",
        }


class CohortPosterior(BaseModel):
    """Per-cohort hyperprior — the partial-pooling target for new and
    low-volume users.

    Per directive Section 3.4: "a user with strong cohort-1 membership
    inherits cohort-1's mechanism priors heavily. As they accumulate
    observations, their cohort posterior updates AND their per-user
    posterior diverges from the cohort prior."

    Stored in the same natural-parameter form as UserPosterior so the
    partial-pooling mixture is a precision-weighted natural-parameter
    sum.
    """

    model_config = ConfigDict(extra="forbid")

    cohort_id: str
    dim: int = USER_POSTERIOR_DIM

    precision_matrix_flat: List[float]
    precision_weighted_mean: List[float]

    n_users_in_cohort: int = 0
    n_observations_in_cohort: int = 0
    last_updated_at: datetime = Field(default_factory=_now_utc)

    @field_validator("precision_matrix_flat")
    @classmethod
    def _validate_precision_shape(
        cls, v: List[float], info,
    ) -> List[float]:
        d = info.data.get("dim", USER_POSTERIOR_DIM)
        expected = d * d
        if len(v) != expected:
            raise ValueError(
                f"precision_matrix_flat length must be dim² = "
                f"{expected}; got {len(v)}"
            )
        return v

    @field_validator("precision_weighted_mean")
    @classmethod
    def _validate_mean_shape(
        cls, v: List[float], info,
    ) -> List[float]:
        d = info.data.get("dim", USER_POSTERIOR_DIM)
        if len(v) != d:
            raise ValueError(
                f"precision_weighted_mean length must be dim = {d}; "
                f"got {len(v)}"
            )
        return v


class HierarchicalPosteriorSnapshot(BaseModel):
    """Compressed snapshot of a user's effective prior at decision time.

    Used by the trilateral cascade (Spine #4), free-energy scorer
    (Spine #5), and decision trace (Spine #6) at decision time. The
    snapshot encodes the partial-pooling mixture:

        effective_prior_i = ω_i · per_user_posterior_i
                          + (1 − ω_i) · cohort_mixture_prior_i

    where ω_i is identity_stability and the cohort mixture is the
    weighted sum of cohort priors per cohort_membership.

    Smaller than the full UserPosterior + CohortPosterior set —
    decision-time consumers don't need full covariance matrices, just
    the effective mean and a precision summary.
    """

    model_config = ConfigDict(extra="forbid")

    user_id: str
    dim: int = USER_POSTERIOR_DIM

    effective_mean: List[float]              # μ_eff ∈ ℝ^dim
    effective_precision_diag: List[float]    # diag(Λ_eff); summary
    effective_precision_logdet: float        # log det Λ_eff; for KL
    identity_stability: float
    cohort_membership: List[float]
    cohort_ids: List[str]
    n_observations: int

    snapshotted_at: datetime = Field(default_factory=_now_utc)


# =============================================================================
# Pure-Python conjugate-update arithmetic (BONG reference)
# =============================================================================


def init_user_posterior(
    user_id: str,
    cohort_prior: Optional[CohortPosterior] = None,
    dim: int = USER_POSTERIOR_DIM,
) -> UserPosterior:
    """Initialize a UserPosterior.

    When cohort_prior is provided, the user starts at the cohort prior
    (natural-parameter copy). When cohort_prior is None, the user
    starts at a wide population prior (identity precision; mean zero).
    """
    if cohort_prior is None:
        # Wide population prior: precision = identity (each dim has
        # variance 1.0); precision-weighted mean = 0.
        precision_matrix_flat = _identity_matrix_flat(dim)
        precision_weighted_mean = [0.0] * dim
        cohort_membership: List[float] = []
        cohort_ids: List[str] = []
    else:
        precision_matrix_flat = list(cohort_prior.precision_matrix_flat)
        precision_weighted_mean = list(cohort_prior.precision_weighted_mean)
        cohort_membership = [1.0]
        cohort_ids = [cohort_prior.cohort_id]

    return UserPosterior(
        user_id=user_id,
        dim=dim,
        precision_matrix_flat=precision_matrix_flat,
        precision_weighted_mean=precision_weighted_mean,
        cohort_membership=cohort_membership,
        cohort_ids=cohort_ids,
    )


def _identity_matrix_flat(dim: int) -> List[float]:
    """Flattened dim×dim identity matrix in row-major order."""
    out = [0.0] * (dim * dim)
    for i in range(dim):
        out[i * dim + i] = 1.0
    return out


def _zero_matrix_flat(dim: int) -> List[float]:
    return [0.0] * (dim * dim)


def bong_update_step(
    posterior: UserPosterior,
    feature_vector: List[float],
    outcome_value: float,
    outcome_class: str,
) -> UserPosterior:
    """BONG single-step natural-gradient update on a UserPosterior.

    Per Jones, Chang & Murphy 2024: BONG performs a single natural-
    gradient step in natural-parameter space; for exponential-family
    conjugate components this recovers exact Bayesian inference.

    For the Gaussian-likelihood approximation used here:
        Λ_new = Λ_old + w · x xᵀ
        η_new = η_old + w · sign · y · x

    where:
        x = feature_vector (the design vector for this observation)
        y = outcome_value (signed/scaled per outcome class)
        w = update weight from the OutcomeWeightSchema
        sign = ±1 from the OutcomeWeightSchema

    For outcome classes with weight=0 (IMPRESSION_NON_VIEWABLE), no
    update; the posterior is returned unchanged.

    Returns a new UserPosterior with updated natural parameters,
    incremented observation count, and updated last_outcome_class +
    last_updated_at.
    """
    schema = get_outcome_schema(outcome_class)

    # No-signal outcomes leave the posterior unchanged but bump the
    # last_updated_at + observation count for accounting.
    if schema.weight == 0.0:
        return posterior.model_copy(update={
            "total_observations": posterior.total_observations + 1,
            "last_outcome_class": outcome_class,
            "last_updated_at": _now_utc(),
        })

    d = posterior.dim
    if len(feature_vector) != d:
        raise ValueError(
            f"feature_vector length must be dim = {d}; "
            f"got {len(feature_vector)}"
        )

    # Λ_new = Λ_old + w · x xᵀ
    new_precision = list(posterior.precision_matrix_flat)
    w = schema.weight
    for i in range(d):
        x_i = feature_vector[i]
        if x_i == 0.0:
            continue
        for j in range(d):
            x_j = feature_vector[j]
            if x_j == 0.0:
                continue
            new_precision[i * d + j] += w * x_i * x_j

    # η_new = η_old + w · sign · y · x
    new_eta = list(posterior.precision_weighted_mean)
    factor = w * float(schema.sign) * float(outcome_value)
    for i in range(d):
        new_eta[i] += factor * feature_vector[i]

    return posterior.model_copy(update={
        "precision_matrix_flat": new_precision,
        "precision_weighted_mean": new_eta,
        "total_observations": posterior.total_observations + 1,
        "last_outcome_class": outcome_class,
        "last_updated_at": _now_utc(),
    })


def natural_to_standard(
    posterior: UserPosterior,
) -> Tuple[List[float], List[float]]:
    """Convert (Λ, η) natural parameters to (μ, Σ) standard form.

    Returns (mean, covariance_flat). Covariance is flattened row-major.

    Implementation: pure-Python Cholesky-based inverse for d=27.
    NumPy/JAX would accelerate; left for the next commit (the spec is
    that the JAX path must produce the same numerical result as this
    reference, modulo floating-point tolerance).

    For singular precision matrices (precision rank-deficient), this
    raises ValueError — the caller's BONG step should never produce a
    singular precision under positive update weights, so a singular
    matrix means upstream contract violation.
    """
    d = posterior.dim
    P = _flat_to_matrix(posterior.precision_matrix_flat, d)
    eta = list(posterior.precision_weighted_mean)
    Sigma = _matrix_inverse(P)
    mu = _matrix_vector_mul(Sigma, eta)
    return mu, _matrix_to_flat(Sigma)


# =============================================================================
# Partial-pooling — effective prior at decision time (Section 3.4)
# =============================================================================


def compute_effective_prior_snapshot(
    posterior: UserPosterior,
    cohort_priors: Dict[str, CohortPosterior],
) -> HierarchicalPosteriorSnapshot:
    """Compute the effective decision-time prior for a user.

    Per directive Section 3.4:

        effective_prior_i = ω_i · per_user_posterior_i
                          + (1 − ω_i) · cohort_mixture_prior_i

        cohort_mixture_prior_i = sum_k P(cohort_k | i) · prior_cohort_k

    Implementation: mixture in natural-parameter space (precision-
    weighted mixing), then convert to standard form for the snapshot.

    Cohort priors are looked up by cohort_ids. Missing cohorts are
    skipped from the mixture and the membership weights are
    renormalized over present cohorts (degraded gracefully).

    Edge cases:
      - Empty cohort_membership: snapshot uses only per-user posterior.
      - All cohort priors missing: same as above.
    """
    d = posterior.dim
    omega = float(posterior.identity_stability)

    # User-side natural parameters
    P_user = _flat_to_matrix(posterior.precision_matrix_flat, d)
    eta_user = list(posterior.precision_weighted_mean)

    # Cohort mixture in natural-parameter space.
    # Mix the precision matrices and precision-weighted means using
    # cohort_membership as weights.
    P_cohort = [[0.0] * d for _ in range(d)]
    eta_cohort = [0.0] * d
    cohort_weight_total = 0.0

    for k, cohort_id in enumerate(posterior.cohort_ids):
        if k >= len(posterior.cohort_membership):
            break
        weight = posterior.cohort_membership[k]
        prior = cohort_priors.get(cohort_id)
        if prior is None:
            continue
        cohort_weight_total += weight
        P_k = _flat_to_matrix(prior.precision_matrix_flat, d)
        for i in range(d):
            for j in range(d):
                P_cohort[i][j] += weight * P_k[i][j]
            eta_cohort[i] += weight * prior.precision_weighted_mean[i]

    # Renormalize cohort mixture if some cohorts were missing.
    if cohort_weight_total > 0.0 and cohort_weight_total < 1.0:
        scale = 1.0 / cohort_weight_total
        for i in range(d):
            for j in range(d):
                P_cohort[i][j] *= scale
            eta_cohort[i] *= scale

    # Effective natural parameters: ω · user + (1 − ω) · cohort
    if cohort_weight_total > 0.0:
        P_eff = [
            [omega * P_user[i][j] + (1.0 - omega) * P_cohort[i][j]
             for j in range(d)]
            for i in range(d)
        ]
        eta_eff = [
            omega * eta_user[i] + (1.0 - omega) * eta_cohort[i]
            for i in range(d)
        ]
    else:
        # No cohort priors available — fall back to user-only.
        P_eff = P_user
        eta_eff = eta_user

    # Convert to standard form.
    Sigma_eff = _matrix_inverse(P_eff)
    mu_eff = _matrix_vector_mul(Sigma_eff, eta_eff)

    # Diagonal precision summary + log-determinant for KL computations
    # (consumed by Spine #5 free-energy KL term).
    precision_diag = [P_eff[i][i] for i in range(d)]
    precision_logdet = _logdet_via_cholesky(P_eff)

    return HierarchicalPosteriorSnapshot(
        user_id=posterior.user_id,
        dim=d,
        effective_mean=mu_eff,
        effective_precision_diag=precision_diag,
        effective_precision_logdet=precision_logdet,
        identity_stability=omega,
        cohort_membership=list(posterior.cohort_membership),
        cohort_ids=list(posterior.cohort_ids),
        n_observations=posterior.total_observations,
    )


# =============================================================================
# Linear algebra helpers — pure-Python reference (NumPy-replaceable)
# =============================================================================


def _flat_to_matrix(flat: List[float], d: int) -> List[List[float]]:
    """Reshape a flattened row-major matrix into a list-of-lists."""
    return [list(flat[i * d:(i + 1) * d]) for i in range(d)]


def _matrix_to_flat(M: List[List[float]]) -> List[float]:
    """Flatten a list-of-lists matrix to row-major."""
    out: List[float] = []
    for row in M:
        out.extend(row)
    return out


def _matrix_vector_mul(M: List[List[float]], v: List[float]) -> List[float]:
    """Dense matrix × vector product."""
    d = len(v)
    return [sum(M[i][k] * v[k] for k in range(d)) for i in range(d)]


def _matrix_inverse(M: List[List[float]]) -> List[List[float]]:
    """Pure-Python matrix inverse via Gauss-Jordan elimination.

    For d=27 this is O(d³) ≈ 20K ops — acceptable for the reference.
    NumPy/JAX replacement is the next commit.
    """
    d = len(M)
    # Augmented matrix [M | I]
    aug = [list(M[i]) + [1.0 if i == j else 0.0 for j in range(d)]
           for i in range(d)]

    for i in range(d):
        # Pivot
        pivot = aug[i][i]
        if abs(pivot) < 1e-12:
            # Search for a non-zero pivot below
            for k in range(i + 1, d):
                if abs(aug[k][i]) >= 1e-12:
                    aug[i], aug[k] = aug[k], aug[i]
                    pivot = aug[i][i]
                    break
            else:
                raise ValueError(
                    "Matrix is singular at row "
                    f"{i}; cannot invert. Check upstream BONG update "
                    "weights — singularity should never occur under "
                    "positive update weights."
                )
        # Scale pivot row
        for j in range(2 * d):
            aug[i][j] /= pivot
        # Eliminate other rows
        for k in range(d):
            if k == i:
                continue
            factor = aug[k][i]
            if factor == 0.0:
                continue
            for j in range(2 * d):
                aug[k][j] -= factor * aug[i][j]

    # Extract inverse from right half
    return [aug[i][d:] for i in range(d)]


def _logdet_via_cholesky(M: List[List[float]]) -> float:
    """Log-determinant of a positive-definite matrix via Cholesky.

    For non-PD matrices, returns -inf (signals numerical issue). The
    BONG update under positive weights produces PD precision matrices;
    a non-PD result here means an upstream contract violation.
    """
    d = len(M)
    L = [[0.0] * d for _ in range(d)]
    for i in range(d):
        for j in range(i + 1):
            s = sum(L[i][k] * L[j][k] for k in range(j))
            if i == j:
                v = M[i][i] - s
                if v <= 0.0:
                    return float("-inf")
                L[i][j] = math.sqrt(v)
            else:
                L[i][j] = (M[i][j] - s) / L[j][j]
    # log det = 2 · sum(log L_ii)
    return 2.0 * sum(math.log(L[i][i]) for i in range(d))


__all__ = [
    "USER_POSTERIOR_DIM",
    "IDENTITY_STABILITY_DEFAULT",
    "OutcomeWeightSchema",
    "UserPosterior",
    "CohortPosterior",
    "HierarchicalPosteriorSnapshot",
    "bong_update_step",
    "compute_effective_prior_snapshot",
    "get_outcome_schema",
    "init_user_posterior",
    "known_outcome_classes",
    "natural_to_standard",
]
