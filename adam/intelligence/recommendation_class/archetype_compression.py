"""Archetype compression — variational Dirichlet-process mixture over
feature vectors. Compresses a population of buyer feature vectors into a
discrete latent-component structure with auto-tuned component count.

Library choice (2026-04-25, `project_weakness_4_recommendation_class_primitive.md`
A14 compromise discipline): `sklearn.mixture.BayesianGaussianMixture` with
`dirichlet_process` weight prior. Single-level compression matching the
single-level shrinkage committed to in the 2026-04-24 structural-weakness
review. The wrapper boundary in this module IS the swap point for the
future PyMC migration — only `ArchetypeCompressor`'s internals change when
that lands.

Migration trigger (named successor, same pattern as the hierarchical-
shrinkage compromise): swap internals to PyMC NUTS-sampled HB when either
(a) the PsychologicalConstruct graph (migration 028, slice 5) is dense
enough to supply construct-conditional priors that exercise custom-prior
flexibility, or (b) Weakness #8 (multi-tenant scope) lands and a true
multi-level hierarchy (industry → partner → advertiser → workspace →
class) becomes load-bearing. Whichever fires first.

Honest framing: this is a variational mixture model, not full hierarchical
Bayes. The "HB latent-class" label used in the 2026-04-24 pilot plan and
handoff overstates what this slice delivers. The substrate here is a
variational latent-class compressor with the HB layer deferred. The
downstream consumer (the plant-model adjudicator) must not assume NUTS-
quality posteriors from this compressor — the posterior is a variational
approximation.

Covariance default:
  `spherical` (isotropic). Mean-field variational with full covariance
  over-parameterizes and fragments well-separated clusters into several
  components to model local within-cluster covariance, which defeats the
  DP prior's pruning goal. Spherical assumes isotropic within-component
  noise, which matches standardized bilateral-edge feature vectors and
  lets the DP prior actually concentrate mass on a small number of
  components. Callers with strong prior knowledge of anisotropic within-
  archetype covariance can override via the `covariance_type` arg.

Scope of this slice:

- Fit / predict / predict_proba wrapper over `BayesianGaussianMixture`
  with deterministic seeding.
- Per-observation MAP component assignment + soft posterior over
  components + fitted component means / weights / convergence flag.
- Content-hash digest over the fitted component means + weights, sorted
  by weight so trivially-permuted fits hash identically. Enables audit-
  level reproducibility checks.
- Does NOT displace the curated archetype catalog in `adam/constants.py`.
  That catalog remains the authoritative source for
  `AudienceScope.archetype_id` during the pilot. The compressor produces
  latent components that can be compared against curated archetypes — a
  bridge primitive, not a catalog replacement. When the compressor finds
  observations whose MAP component matches no curated archetype centroid,
  that signals catalog-expansion pressure for later work.

Attention-inversion discipline:
  This primitive is upstream of the autopilot/attention-route split. The
  split lives at the adjudicator layer on realized outcome data, not here.
  Library choice is neutral on attention-inversion.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import List, Optional

import numpy as np
from sklearn.mixture import BayesianGaussianMixture


# Deterministic default seed — the session date this slice shipped.
# Downstream consumers can override, but every fit that does not override
# produces identical output on identical input, forever.
DEFAULT_SEED = 20260425

DEFAULT_MAX_COMPONENTS = 16
DEFAULT_MIN_OBSERVATIONS = 8
# Smaller concentration → sparser posterior. sklearn's default of
# 1/n_components was empirically too permissive on well-separated data.
# 1e-3 pushes harder toward simplex corners.
DEFAULT_DIRICHLET_CONCENTRATION = 1e-3
# A component must carry at least this fraction of total mass to count
# as "non-negligible" by the weight-based filter. Kept as a secondary
# diagnostic. `effective_components` in the result is the primary signal
# and uses MAP-assignment count — see below.
DEFAULT_EFFECTIVE_WEIGHT_THRESHOLD = 1e-2
# Default covariance structure. See module docstring for why spherical is
# the pilot default. Valid values match sklearn: "spherical", "diag",
# "tied", "full".
DEFAULT_COVARIANCE_TYPE = "spherical"
_VALID_COVARIANCE_TYPES = frozenset({"spherical", "diag", "tied", "full"})


# =============================================================================
# ArchetypeCompressionResult — frozen output of a single fit
# =============================================================================


@dataclass(frozen=True)
class ArchetypeCompressionResult:
    """Frozen record of a single fit.

    Every list is JSON-serializable. Consumers that persist the result
    (e.g. the plant-model adjudicator auditing a fit's reproducibility)
    can serialize directly via dataclasses.asdict.
    """

    component_assignments: List[int]
    component_posteriors: List[List[float]]
    component_means: List[List[float]]
    component_weights: List[float]
    effective_components: int  # count of distinct MAP assignments (primary)
    nonnegligible_components: int  # count with weight >= threshold (secondary)
    n_observations: int
    n_features: int
    seed: int
    converged: bool

    @property
    def fit_hash(self) -> str:
        """SHA-256 digest over the fitted component means + weights + seed.

        Components are ordered by descending weight before hashing so that
        two fits differing only by permutation of identically-weighted
        components produce the same digest. Numeric precision is truncated
        to 8 decimal places to absorb float-repr noise below meaningful
        precision for mixture components.
        """
        ordered = sorted(
            zip(self.component_weights, self.component_means),
            key=lambda pair: (-pair[0], pair[1]),
        )
        payload = {
            "weights": [round(w, 8) for w, _ in ordered],
            "means": [[round(v, 8) for v in m] for _, m in ordered],
            "seed": self.seed,
        }
        canonical = json.dumps(
            payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# =============================================================================
# ArchetypeCompressor — fit / predict wrapper
# =============================================================================


class ArchetypeCompressor:
    """Variational Dirichlet-process mixture over feature vectors.

    The wrapper is the API boundary the rest of ADAM sees. Internal
    substitution of the fitter (sklearn → PyMC) happens behind this
    boundary when the migration trigger fires.

    Determinism: the fitter is seeded with a fixed `random_state`;
    identical input arrays produce identical fit output across Python
    processes on the same platform.
    """

    def __init__(
        self,
        max_components: int = DEFAULT_MAX_COMPONENTS,
        min_observations: int = DEFAULT_MIN_OBSERVATIONS,
        dirichlet_concentration: float = DEFAULT_DIRICHLET_CONCENTRATION,
        seed: int = DEFAULT_SEED,
        effective_weight_threshold: float = DEFAULT_EFFECTIVE_WEIGHT_THRESHOLD,
        covariance_type: str = DEFAULT_COVARIANCE_TYPE,
    ) -> None:
        if max_components < 2:
            raise ValueError(
                f"max_components must be >= 2; got {max_components}"
            )
        if min_observations < 2:
            raise ValueError(
                f"min_observations must be >= 2; got {min_observations}"
            )
        if dirichlet_concentration <= 0.0:
            raise ValueError(
                f"dirichlet_concentration must be > 0; got {dirichlet_concentration}"
            )
        if not (0.0 < effective_weight_threshold < 1.0):
            raise ValueError(
                f"effective_weight_threshold must be in (0, 1); "
                f"got {effective_weight_threshold}"
            )
        if covariance_type not in _VALID_COVARIANCE_TYPES:
            raise ValueError(
                f"covariance_type must be one of "
                f"{sorted(_VALID_COVARIANCE_TYPES)}; got {covariance_type!r}"
            )

        self._max_components = max_components
        self._min_observations = min_observations
        self._dirichlet_concentration = dirichlet_concentration
        self._seed = seed
        self._effective_weight_threshold = effective_weight_threshold
        self._covariance_type = covariance_type
        self._model: Optional[BayesianGaussianMixture] = None
        self._last_result: Optional[ArchetypeCompressionResult] = None

    # ── PUBLIC API ───────────────────────────────────────────────────────

    def fit(self, features) -> ArchetypeCompressionResult:
        """Fit the mixture on a (n_observations, n_features) array.

        Refuses to fit fewer than `min_observations` rows — below that,
        the variational posterior is too data-poor for the result to
        carry useful signal. Callers with too few observations should
        route through the curated archetype catalog in
        `adam/constants.py` instead.

        Refuses to fit zero-variance columns — the variational fitter
        would succeed silently but the posterior would be degenerate.
        Callers should pre-filter constant features.
        """
        X = self._coerce(features)
        n, d = X.shape
        if n < self._min_observations:
            raise ValueError(
                f"n_observations ({n}) below min_observations "
                f"({self._min_observations}); compressor fit refused"
            )
        if d == 0:
            raise ValueError("features has zero columns; nothing to fit")
        zero_var = np.where(X.std(axis=0) < 1e-12)[0]
        if zero_var.size > 0:
            raise ValueError(
                f"features contains zero-variance columns at indices "
                f"{zero_var.tolist()}; pre-filter and retry"
            )

        model = BayesianGaussianMixture(
            n_components=min(self._max_components, n),
            covariance_type=self._covariance_type,
            weight_concentration_prior_type="dirichlet_process",
            weight_concentration_prior=self._dirichlet_concentration,
            random_state=self._seed,
            max_iter=500,
            n_init=1,
            init_params="kmeans",
        )
        model.fit(X)
        self._model = model

        assignments = model.predict(X).astype(int).tolist()
        posteriors = model.predict_proba(X).astype(float).tolist()
        weights = model.weights_.astype(float).tolist()
        means = model.means_.astype(float).tolist()
        # Primary effective-count metric: components that actually produce
        # MAP assignments on the training data. sklearn's mean-field
        # variational DP does not prune weights to zero — components with
        # small-but-nonzero weights stay in `weights_` even when no
        # observation is assigned to them. Counting distinct MAP
        # assignments is the honest measure of components the fit USES.
        effective = len(set(assignments))
        nonnegligible = int(
            sum(1 for w in weights if w >= self._effective_weight_threshold)
        )

        result = ArchetypeCompressionResult(
            component_assignments=assignments,
            component_posteriors=posteriors,
            component_means=means,
            component_weights=weights,
            effective_components=effective,
            nonnegligible_components=nonnegligible,
            n_observations=int(n),
            n_features=int(d),
            seed=self._seed,
            converged=bool(model.converged_),
        )
        self._last_result = result
        return result

    def predict(self, features) -> List[int]:
        """Predict MAP component assignments for new observations.

        Requires a prior `fit` call. New observations must have the same
        number of features as the training data; the mixture will raise
        internally otherwise.
        """
        if self._model is None:
            raise RuntimeError(
                "ArchetypeCompressor.fit must be called before predict"
            )
        X = self._coerce(features)
        return self._model.predict(X).astype(int).tolist()

    def predict_proba(self, features) -> List[List[float]]:
        """Predict soft posteriors over components for new observations."""
        if self._model is None:
            raise RuntimeError(
                "ArchetypeCompressor.fit must be called before predict_proba"
            )
        X = self._coerce(features)
        return self._model.predict_proba(X).astype(float).tolist()

    @property
    def last_result(self) -> Optional[ArchetypeCompressionResult]:
        return self._last_result

    @property
    def seed(self) -> int:
        return self._seed

    @property
    def max_components(self) -> int:
        return self._max_components

    # ── INTERNAL ─────────────────────────────────────────────────────────

    @staticmethod
    def _coerce(features) -> np.ndarray:
        X = np.asarray(features, dtype=float)
        if X.ndim != 2:
            raise ValueError(
                f"features must be 2-D (n_observations, n_features); "
                f"got shape {X.shape}"
            )
        if not np.isfinite(X).all():
            raise ValueError("features contains non-finite values")
        return X
