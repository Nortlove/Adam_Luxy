# =============================================================================
# BONG — Bayesian Online Natural Gradient Posterior Engine
# Location: adam/intelligence/bong.py
# Reference: Jones, Chang, Murphy (NeurIPS 2024)
# =============================================================================

"""
Multivariate Gaussian posteriors with diagonal + low-rank precision.

Replaces independent Beta(alpha, beta) posteriors per alignment dimension
with a single multivariate normal that captures cross-dimension correlations.
When we observe high brand_trust_fit, the correlated update also shifts
emotional_resonance (r=0.582 in our population). Independent Betas miss this.

Storage: Natural parameter form with diagonal + low-rank factored precision.

    Λ = D + U @ U.T

    D = diag(d_1, ..., d_20)     — per-dimension precision (20 floats)
    U = 20 × k factor matrix     — rank-k cross-dimension structure
    η = Λ @ μ                    — precision-weighted mean (20 floats)

Update rule: η += τ * y, D += τ * I  (ADDITION — O(d), exact Bayesian)

Phase 0 analysis of 100K live bilateral edges found:
- Condition number 2×10^14 (ill-conditioned)
- Effective rank 13/20
- 6 dimensions with zero eigenvalue
- Strongest correlation: r=0.582 (regulatory_fit × emotional_resonance)

The diagonal+low-rank form handles this safely: D captures well-estimated
per-dimension precision, U captures the rank-13 cross-dimension structure,
and degenerate dimensions are regularized.
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

# Default dimensions (the 20 bilateral alignment dimensions)
DEFAULT_DIMENSIONS = [
    "regulatory_fit_score",
    "construal_fit_score",
    "personality_brand_alignment",
    "emotional_resonance",
    "value_alignment",
    "evolutionary_motive_match",
    "linguistic_style_matching",
    "spending_pain_match",
    "reactance_fit",
    "self_monitoring_fit",
    "processing_route_match",
    "mental_simulation_resonance",
    "optimal_distinctiveness_fit",
    "involvement_weight_modifier",
    "brand_trust_fit",
    "identity_signaling_match",
    "anchor_susceptibility_match",
    "lay_theory_alignment",
    "negativity_bias_match",
    "persuasion_confidence_multiplier",
]

# Regularization ridge for zero-eigenvalue dimensions
EIGENVALUE_RIDGE = 1e-4

# Minimum precision to prevent numerical instability
MIN_PRECISION = 1e-6


@dataclass
class BONGPosterior:
    """Per-individual multivariate Gaussian posterior in natural parameter form.

    Natural parameters enable Bayesian updates via ADDITION:
        posterior_eta = prior_eta + likelihood_eta
        posterior_D   = prior_D   + likelihood_D

    The precision matrix Λ = D + U @ U.T is never formed explicitly.
    All operations use the Woodbury identity for O(k^3 + k^2 d) cost
    instead of O(d^3).

    Storage per individual: d (eta) + d (D) = 40 floats = 320 bytes
    The factor matrix U is shared across all individuals (population structure).
    """

    eta: np.ndarray            # shape (d,) — precision-weighted mean
    D: np.ndarray              # shape (d,) — diagonal precision
    observation_count: int = 0
    last_updated: float = field(default_factory=time.time)

    @property
    def d(self) -> int:
        return len(self.eta)


class BONGUpdater:
    """Bayesian Online Natural Gradient updater for per-individual posteriors.

    Population-level structure (U matrix) is shared and initialized once
    from the eigendecomposition of the bilateral edge covariance. Per-individual
    state (eta, D) is lightweight and updated via O(d) addition.

    Usage:
        updater = BONGUpdater()
        updater.initialize_from_eigendecomposition(eigvecs, eigvals, pop_mean)

        individual = updater.create_individual()
        updater.update(individual, observation, noise_precision=1.0)
        sample = updater.thompson_sample(individual)
        iv = updater.information_value(individual)
    """

    def __init__(
        self,
        dimension_names: Optional[List[str]] = None,
        rank: int = 13,
    ):
        self.dimension_names = dimension_names or DEFAULT_DIMENSIONS
        self.d = len(self.dimension_names)
        self.k = min(rank, self.d)  # low-rank factor dimension

        # Population-level structure (shared, immutable after init)
        self.U: Optional[np.ndarray] = None  # shape (d, k) — factor matrix
        self.prior_eta: Optional[np.ndarray] = None
        self.prior_D: Optional[np.ndarray] = None
        self.population_mean: Optional[np.ndarray] = None

        self._dim_index = {name: i for i, name in enumerate(self.dimension_names)}

    # ─── INITIALIZATION ─────────────────────────────────────────

    def initialize_from_eigendecomposition(
        self,
        eigenvectors: np.ndarray,   # shape (d, k) — top-k eigenvectors
        eigenvalues: np.ndarray,    # shape (k,) — top-k eigenvalues
        population_mean: np.ndarray,  # shape (d,) — population mean alignment
        population_variances: Optional[np.ndarray] = None,  # shape (d,) — per-dim variances
    ):
        """Initialize population structure from Phase 0 eigendecomposition.

        Args:
            eigenvectors: Top-k eigenvectors of population covariance
            eigenvalues: Corresponding eigenvalues
            population_mean: Mean alignment vector from bilateral edges
            population_variances: Per-dimension variances (for diagonal precision)
        """
        k_actual = min(len(eigenvalues), self.k)
        self.k = k_actual

        # Factor matrix: U = V @ diag(sqrt(eigenvalues))
        # So U @ U.T recovers the low-rank part of covariance
        sqrt_eig = np.sqrt(np.maximum(eigenvalues[:k_actual], EIGENVALUE_RIDGE))
        self.U = eigenvectors[:, :k_actual] * sqrt_eig[np.newaxis, :]

        # Diagonal precision from per-dimension variances
        if population_variances is not None:
            # Regularize zero-variance dimensions
            reg_variances = np.maximum(population_variances, EIGENVALUE_RIDGE)
            self.prior_D = 1.0 / reg_variances
        else:
            # Default weak precision
            self.prior_D = np.full(self.d, 4.0)  # equivalent to Beta(2,2) total count

        self.population_mean = population_mean.copy()

        # Prior natural parameters
        # For MVN: eta = Λ @ μ where Λ = D + U @ U.T
        # Approximate: eta ≈ D * μ (ignoring U contribution for prior)
        # This is safe because U captures population covariance, not prior mean
        self.prior_eta = self.prior_D * population_mean

        logger.info(
            "BONG initialized: d=%d, rank=%d, pop_mean range=[%.3f, %.3f], "
            "precision range=[%.3f, %.3f]",
            self.d, self.k,
            population_mean.min(), population_mean.max(),
            self.prior_D.min(), self.prior_D.max(),
        )

    def initialize_from_population_stats(
        self,
        population_mean: np.ndarray,
        population_covariance: np.ndarray,
    ):
        """Initialize from raw population statistics.

        Computes eigendecomposition internally. Use this when you have
        the covariance matrix but haven't done Phase 0 analysis separately.
        """
        eigenvalues, eigenvectors = np.linalg.eigh(population_covariance)

        # Sort descending
        idx = np.argsort(eigenvalues)[::-1]
        eigenvalues = eigenvalues[idx]
        eigenvectors = eigenvectors[:, idx]

        # Keep top-k with eigenvalue > 1% of max
        threshold = eigenvalues[0] * 0.01
        k_effective = max(1, int(np.sum(eigenvalues > threshold)))
        self.k = min(k_effective, self.k)

        population_variances = np.diag(population_covariance)

        self.initialize_from_eigendecomposition(
            eigenvectors=eigenvectors,
            eigenvalues=eigenvalues,
            population_mean=population_mean,
            population_variances=population_variances,
        )

    def initialize_from_file(self, priors_path: str = "data/bong_population_priors.npz"):
        """Initialize from exported Phase 0 eigendecomposition.

        Args:
            priors_path: Path to .npz file from export_bong_priors.py
        """
        try:
            data = np.load(priors_path, allow_pickle=True)
            self.initialize_from_eigendecomposition(
                eigenvectors=data["eigenvectors"],
                eigenvalues=data["eigenvalues"],
                population_mean=data["population_mean"],
                population_variances=data["population_variances"],
            )
            effective_rank = int(data["effective_rank"][0])
            n_edges = int(data["n_edges"][0])
            logger.info(
                "BONG initialized from %s: %d edges, rank=%d",
                priors_path, n_edges, effective_rank,
            )
            return True
        except FileNotFoundError:
            logger.debug("BONG priors file not found: %s", priors_path)
            return False
        except Exception as e:
            logger.warning("Failed to load BONG priors from %s: %s", priors_path, e)
            return False

    def initialize_default(self):
        """Initialize with uninformative diagonal priors (no population data).

        Use this as fallback when Phase 0 data isn't available.
        Equivalent to current independent Beta(2,2) posteriors.
        """
        self.U = np.zeros((self.d, 1))  # rank-1 with zero factor = diagonal only
        self.k = 1
        self.prior_D = np.full(self.d, 4.0)  # Beta(2,2) has α+β=4 total precision
        self.population_mean = np.full(self.d, 0.5)  # uninformative mean
        self.prior_eta = self.prior_D * self.population_mean

    # ─── PER-INDIVIDUAL OPERATIONS ──────────────────────────────

    def create_individual(
        self,
        archetype_mean: Optional[np.ndarray] = None,
    ) -> BONGPosterior:
        """Create posterior for a new individual.

        Starts at population prior, optionally shifted to archetype mean.
        """
        if self.prior_eta is None:
            self.initialize_default()

        eta = self.prior_eta.copy()
        D = self.prior_D.copy()

        if archetype_mean is not None:
            # Shift prior mean to archetype-specific location
            # eta = D * archetype_mean (approximately, ignoring U contribution)
            eta = D * archetype_mean

        return BONGPosterior(eta=eta, D=D)

    def update(
        self,
        individual: BONGPosterior,
        observation: np.ndarray,
        noise_precision: float = 1.0,
        observed_mask: Optional[np.ndarray] = None,
    ) -> BONGPosterior:
        """Single-step exact Bayesian update via natural gradient.

        In natural parameter space, Bayesian updating is ADDITION.
        O(d) operation. No matrix inversion.

        Args:
            individual: Current posterior
            observation: shape (d,) observed alignment values
            noise_precision: Inverse observation variance. Higher = more trusted.
            observed_mask: Optional boolean mask for partial observations.
                If provided, only dimensions where mask=True are updated.
        """
        if observed_mask is not None:
            # Partial observation: only update observed dimensions
            tau = noise_precision * observed_mask.astype(float)
        else:
            tau = noise_precision

        individual.D += tau
        individual.eta += tau * observation
        individual.observation_count += 1
        individual.last_updated = time.time()

        return individual

    def get_mean(self, individual: BONGPosterior) -> np.ndarray:
        """Recover posterior mean from natural parameters.

        Uses Woodbury identity for O(k^3 + k^2 d) instead of O(d^3).
        """
        return self._woodbury_solve(individual.D, individual.eta)

    def get_per_dimension_variance(self, individual: BONGPosterior) -> np.ndarray:
        """Fast approximate per-dimension variance (diagonal of covariance).

        Uses D^{-1} approximation (ignores low-rank correction).
        Exact for diagonal-only posteriors. Underestimates when U is significant.
        """
        return 1.0 / np.maximum(individual.D, MIN_PRECISION)

    def get_per_dimension_variance_exact(self, individual: BONGPosterior) -> np.ndarray:
        """Exact per-dimension variance (diagonal of full covariance via Woodbury).

        More expensive: O(k^2 d). Use when exact variance matters.
        """
        D_inv = 1.0 / np.maximum(individual.D, MIN_PRECISION)
        if self.U is None or np.allclose(self.U, 0):
            return D_inv

        # Woodbury: Σ = D^{-1} - D^{-1} U (I + U.T D^{-1} U)^{-1} U.T D^{-1}
        D_inv_U = D_inv[:, np.newaxis] * self.U  # (d, k)
        M = np.eye(self.k) + self.U.T @ D_inv_U  # (k, k)
        M_inv = np.linalg.inv(M)
        correction = D_inv_U @ M_inv @ D_inv_U.T  # (d, d)
        return D_inv - np.diag(correction)

    # ─── PROPAGATION METHODS (Unified System Evolution §1.1) ───

    def get_covariance(self, individual: BONGPosterior) -> np.ndarray:
        """Full d×d covariance matrix via Woodbury identity.

        Σ = (D + U U.T)^{-1} = D^{-1} - D^{-1} U (I + U.T D^{-1} U)^{-1} U.T D^{-1}
        """
        D_inv = 1.0 / np.maximum(individual.D, MIN_PRECISION)
        if self.U is None or np.allclose(self.U, 0):
            return np.diag(D_inv)

        D_inv_U = D_inv[:, np.newaxis] * self.U
        M = np.eye(self.k) + self.U.T @ D_inv_U
        M_inv = np.linalg.inv(M)
        cov = np.diag(D_inv) - D_inv_U @ M_inv @ D_inv_U.T
        return (cov + cov.T) / 2  # ensure symmetry

    def conditional_shift(
        self,
        individual: BONGPosterior,
        target_dim_index: int,
        intervention_magnitude: float,
    ) -> np.ndarray:
        """Predict shift on ALL dimensions given intervention on ONE dimension.

        Uses the conditional Gaussian formula:
            E[X_other | X_target shifted by delta] = regression_weights * delta
            regression_weights = Cov(:, target) / Var(target)

        This is the core propagation primitive. It answers:
        "If I improve brand_trust_fit by 0.15 SD, what happens to
        all 19 other dimensions?"

        Returns:
            np.ndarray shape (d,) — expected shift per dimension.
            Entry [target_dim_index] = intervention_magnitude.
        """
        cov = self.get_covariance(individual)
        sigma_target = cov[target_dim_index, target_dim_index]

        if sigma_target < MIN_PRECISION:
            result = np.zeros(self.d)
            result[target_dim_index] = intervention_magnitude
            return result

        sigma_cross = cov[:, target_dim_index]
        regression_weights = sigma_cross / sigma_target
        return regression_weights * intervention_magnitude

    def propagated_barrier_impact(
        self,
        individual: BONGPosterior,
        alignment_scores: Dict[str, float],
        thresholds: Dict[str, float],
        gradient_field: Optional[Dict[str, float]] = None,
    ) -> List[Dict]:
        """Rank barriers by TOTAL propagated conversion lift, not just gap size.

        For each below-threshold dimension, computes the propagated benefit
        of closing that gap through the BONG correlation structure. The
        barrier to target is the one where intervention propagates the most
        total improvement weighted by the gradient field.

        This changes which barrier the retargeting engine targets, which
        changes which mechanism it selects, which changes everything downstream.

        Returns ranked list of barriers with propagation analysis.
        """
        cov = self.get_covariance(individual)
        candidates = []

        for dim_name, score in alignment_scores.items():
            threshold = thresholds.get(dim_name, 0.5)
            gap = threshold - score
            if gap <= 0:
                continue

            dim_idx = self._dim_index.get(dim_name)
            if dim_idx is None:
                continue

            sigma_target = cov[dim_idx, dim_idx]
            if sigma_target < MIN_PRECISION:
                continue

            # Propagated shift from closing this gap
            shifts = self.conditional_shift(individual, dim_idx, gap)

            # Weight by gradient field
            total_lift = 0.0
            secondary = {}
            for j, other_dim in enumerate(self.dimension_names):
                shift = shifts[j]
                grad = (gradient_field or {}).get(other_dim, 1.0 / self.d)
                lift = shift * grad
                total_lift += lift
                if abs(shift) > 0.01 and other_dim != dim_name:
                    secondary[other_dim] = {
                        "shift": round(float(shift), 4),
                        "gradient": round(float(grad), 4),
                        "lift": round(float(lift), 6),
                    }

            direct_lift = gap * (gradient_field or {}).get(dim_name, 1.0 / self.d)

            candidates.append({
                "barrier_dimension": dim_name,
                "direct_gap": round(float(gap), 4),
                "direct_lift": round(float(direct_lift), 6),
                "total_propagated_lift": round(float(total_lift), 6),
                "propagation_multiplier": round(
                    float(total_lift / max(direct_lift, 1e-6)), 2
                ),
                "secondary_benefits": secondary,
            })

        candidates.sort(key=lambda c: c["total_propagated_lift"], reverse=True)
        return candidates

    def find_indirect_resolution_paths(
        self,
        frustrated_pairs: List[Tuple[str, str, float]],
    ) -> List[Dict]:
        """Recheck frustrated pairs using BONG population covariance.

        For each frustrated pair, finds dimensions that positively correlate
        with BOTH frustrated dimensions — potential indirect resolvers that
        could improve both simultaneously, shortening retargeting sequences.
        """
        if self.prior_D is None:
            return []

        # Build population covariance from prior
        pop_posterior = BONGPosterior(
            eta=self.prior_eta.copy(),
            D=self.prior_D.copy(),
        )
        cov = self.get_covariance(pop_posterior)
        stds = np.sqrt(np.maximum(np.diag(cov), MIN_PRECISION))
        corr = cov / np.outer(stds, stds)

        results = []
        for dim_a, dim_b, original_corr in frustrated_pairs:
            idx_a = self._dim_index.get(dim_a)
            idx_b = self._dim_index.get(dim_b)
            if idx_a is None or idx_b is None:
                results.append({
                    "dim_a": dim_a, "dim_b": dim_b,
                    "direct_correlation": float(original_corr),
                    "truly_frustrated": True,
                    "indirect_resolvers": [],
                    "note": "dimension not in BONG space",
                })
                continue

            live_corr = float(corr[idx_a, idx_b])

            resolvers = []
            for i, dim_c in enumerate(self.dimension_names):
                if i == idx_a or i == idx_b:
                    continue
                corr_ca = corr[i, idx_a]
                corr_cb = corr[i, idx_b]
                if corr_ca > 0.15 and corr_cb > 0.15:
                    resolvers.append({
                        "dimension": dim_c,
                        "corr_with_a": round(float(corr_ca), 3),
                        "corr_with_b": round(float(corr_cb), 3),
                        "resolution_strength": round(float(corr_ca * corr_cb), 4),
                    })

            resolvers.sort(key=lambda r: r["resolution_strength"], reverse=True)

            results.append({
                "dim_a": dim_a,
                "dim_b": dim_b,
                "original_correlation": float(original_corr),
                "live_correlation": live_corr,
                "truly_frustrated": len(resolvers) == 0,
                "indirect_resolvers": resolvers[:3],
                "sequence_impact": (
                    "SEQUENTIAL RESOLUTION REQUIRED"
                    if not resolvers
                    else f"SIMULTANEOUS via {resolvers[0]['dimension']}"
                ),
            })

        return results

    # ─── THOMPSON SAMPLING ──────────────────────────────────────

    def thompson_sample(self, individual: BONGPosterior) -> np.ndarray:
        """Sample from posterior for Thompson Sampling.

        Returns d-dimensional sample representing a plausible alignment
        state for this individual. Use to compute alignment score with
        each candidate mechanism's ideal profile.
        """
        mean = self.get_mean(individual)
        var = self.get_per_dimension_variance(individual)

        # Fast diagonal sampling (ignores off-diagonal covariance)
        # For Thompson Sampling, this is sufficient — the exploration
        # benefit of correlated sampling is second-order
        return np.random.normal(mean, np.sqrt(np.maximum(var, MIN_PRECISION)))

    def thompson_sample_correlated(self, individual: BONGPosterior) -> np.ndarray:
        """Correlated Thompson sample (respects full covariance structure).

        More expensive but produces better exploration for strongly
        correlated dimensions. Use when precision matters more than speed.
        """
        mean = self.get_mean(individual)
        D_inv = 1.0 / np.maximum(individual.D, MIN_PRECISION)

        if self.U is None or np.allclose(self.U, 0):
            return np.random.normal(mean, np.sqrt(D_inv))

        # Full covariance via Woodbury
        D_inv_U = D_inv[:, np.newaxis] * self.U
        M = np.eye(self.k) + self.U.T @ D_inv_U
        M_inv = np.linalg.inv(M)
        cov = np.diag(D_inv) - D_inv_U @ M_inv @ D_inv_U.T

        # Ensure positive semi-definite (numerical stability)
        cov = (cov + cov.T) / 2
        eigvals = np.linalg.eigvalsh(cov)
        if eigvals.min() < 0:
            cov += np.eye(self.d) * (abs(eigvals.min()) + MIN_PRECISION)

        return np.random.multivariate_normal(mean, cov)

    def information_value(self, individual: BONGPosterior) -> float:
        """Compute information value (posterior entropy) for bidding.

        Higher entropy = more uncertain = higher information value = bid more.

        Uses log-determinant of precision via Woodbury:
            log|D + U U.T| = log|D| + log|I + U.T D^{-1} U|
        """
        # log|D|
        log_det_D = np.sum(np.log(np.maximum(individual.D, MIN_PRECISION)))

        if self.U is None or np.allclose(self.U, 0):
            log_det_Lambda = log_det_D
        else:
            # log|I + U.T D^{-1} U|
            D_inv = 1.0 / np.maximum(individual.D, MIN_PRECISION)
            D_inv_U = D_inv[:, np.newaxis] * self.U
            M = np.eye(self.k) + self.U.T @ D_inv_U
            sign, log_det_M = np.linalg.slogdet(M)
            log_det_Lambda = log_det_D + log_det_M

        # Entropy of MVN: H = 0.5 * (d * (1 + log(2π)) - log|Λ|)
        entropy = 0.5 * (self.d * (1 + np.log(2 * np.pi)) - log_det_Lambda)
        return float(entropy)

    def information_gain(
        self,
        individual: BONGPosterior,
        observation: np.ndarray,
        noise_precision: float = 1.0,
    ) -> float:
        """Expected information gain from observing this individual.

        Computes the difference in entropy before and after a hypothetical
        observation. Used for information value bidding.
        """
        entropy_before = self.information_value(individual)

        # Simulate update
        hypothetical = BONGPosterior(
            eta=individual.eta + noise_precision * observation,
            D=individual.D + noise_precision,
            observation_count=individual.observation_count + 1,
        )
        entropy_after = self.information_value(hypothetical)

        return max(0.0, entropy_before - entropy_after)

    # ─── BACKWARD COMPATIBILITY ─────────────────────────────────

    def get_construct_stats(
        self, individual: BONGPosterior,
    ) -> Dict[str, Dict[str, float]]:
        """Get per-dimension statistics for backward compatibility.

        Returns dict matching the old ConstructPosterior interface:
        {dim_name: {"mean": ..., "variance": ..., "confidence": ...}}
        """
        mean = self.get_mean(individual)
        var = self.get_per_dimension_variance(individual)

        stats = {}
        for i, name in enumerate(self.dimension_names):
            v = float(var[i])
            stats[name] = {
                "mean": float(mean[i]),
                "variance": v,
                "std": float(np.sqrt(max(v, 0))),
                "confidence": float(1.0 - min(1.0, 4.0 * v)),
            }
        return stats

    def to_legacy_betas(
        self, individual: BONGPosterior,
    ) -> Dict[str, Tuple[float, float]]:
        """Convert MVN marginals to approximate Beta(α, β) parameters.

        For backward compatibility with code expecting Beta posteriors.
        Uses method-of-moments: match Beta mean and variance to MVN marginals.
        """
        mean = self.get_mean(individual)
        var = self.get_per_dimension_variance(individual)

        betas = {}
        for i, name in enumerate(self.dimension_names):
            m = float(np.clip(mean[i], 0.01, 0.99))
            v = float(np.clip(var[i], 1e-6, 0.24))
            # Method of moments for Beta: α = m((m(1-m)/v) - 1), β = (1-m)((m(1-m)/v) - 1)
            common = max(0.1, m * (1 - m) / v - 1)
            alpha = m * common
            beta = (1 - m) * common
            betas[name] = (max(0.1, alpha), max(0.1, beta))
        return betas

    # ─── SERIALIZATION ──────────────────────────────────────────

    def serialize(self, individual: BONGPosterior) -> bytes:
        """Serialize for Redis storage.

        Format: [d, observation_count, last_updated, eta(d), D(d)]
        Total: 3 + 2d floats = 43 floats = 344 bytes for d=20
        """
        header = np.array([float(self.d), float(individual.observation_count),
                           individual.last_updated])
        return np.concatenate([header, individual.eta, individual.D]).tobytes()

    def deserialize(self, data: bytes) -> BONGPosterior:
        """Deserialize from Redis."""
        arr = np.frombuffer(data, dtype=np.float64)
        d = int(arr[0])
        obs_count = int(arr[1])
        last_updated = float(arr[2])
        eta = arr[3:3+d].copy()
        D = arr[3+d:3+2*d].copy()
        return BONGPosterior(
            eta=eta, D=D,
            observation_count=obs_count,
            last_updated=last_updated,
        )

    # ─── INTERNAL ───────────────────────────────────────────────

    def _woodbury_solve(self, D: np.ndarray, b: np.ndarray) -> np.ndarray:
        """Solve (D + U U.T) x = b using Woodbury identity.

        (D + U U.T)^{-1} b = D^{-1} b - D^{-1} U (I + U.T D^{-1} U)^{-1} U.T D^{-1} b
        """
        D_inv_b = b / np.maximum(D, MIN_PRECISION)

        if self.U is None or np.allclose(self.U, 0):
            return D_inv_b

        D_inv = 1.0 / np.maximum(D, MIN_PRECISION)
        D_inv_U = D_inv[:, np.newaxis] * self.U  # (d, k)
        M = np.eye(self.k) + self.U.T @ D_inv_U  # (k, k)
        # Solve M @ z = U.T @ D_inv_b
        z = np.linalg.solve(M, self.U.T @ D_inv_b)
        return D_inv_b - D_inv_U @ z


# =============================================================================
# SINGLETON
# =============================================================================

_bong_updater: Optional[BONGUpdater] = None


def get_bong_updater() -> BONGUpdater:
    """Get or create the singleton BONGUpdater.

    Tries to load population priors from data/bong_population_priors.npz
    (exported by scripts/export_bong_priors.py). Falls back to uninformative
    diagonal priors if the file doesn't exist.
    """
    global _bong_updater
    if _bong_updater is None:
        _bong_updater = BONGUpdater()
        if not _bong_updater.initialize_from_file():
            _bong_updater.initialize_default()
            logger.info("BONGUpdater using default diagonal priors (no population data)")
    return _bong_updater
