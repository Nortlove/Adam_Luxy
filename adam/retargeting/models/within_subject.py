# =============================================================================
# Repeated Measures / Within-Subject Experimental Design — Data Models
# Location: adam/retargeting/models/within_subject.py
# Enhancement #36, Session 36-1
# =============================================================================

"""
Data models for within-subject repeated measures analysis.

When a user receives 7 retargeting touches, those 7 outcomes are NOT
independent observations. They are correlated within-subject measurements
from the same person. This module provides the models to exploit that
structure for 2-4x faster convergence on mechanism effectiveness.

Key insight: between-subjects designs need ~175 observations to detect
d=0.3 (alpha=0.05, power=0.80). Within-subjects with rho=0.5 need ~88.
With rho=0.7, only ~53. Each user IS their own control.

Architecture:
- UserMechanismPosterior: per-(user, mechanism) Beta posterior
- UserPosteriorProfile: complete user-level statistical profile
- VarianceComponents: between/within variance decomposition
- WithinSubjectDesign: experimental design for a user's sequence
- MechanismContrast: pairwise within-user mechanism comparison
- TrajectoryAnalysis: longitudinal engagement trajectory
"""

import math
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from uuid import uuid4

import numpy as np
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Per-user mechanism posterior
# ---------------------------------------------------------------------------


class UserMechanismPosterior(BaseModel):
    """Beta(alpha, beta) posterior for a specific mechanism for a specific user.

    Unlike the population-level BarrierConditionedPosterior which is keyed by
    (mechanism, barrier, archetype), this is keyed by (user_id, mechanism)
    and optionally barrier. It tracks THIS user's response to THIS mechanism.

    With 3+ observations, the user-level posterior starts overriding the
    population posterior in Thompson Sampling — giving personalized
    mechanism selection.
    """

    user_id: str
    mechanism: str
    barrier: str = Field(
        default="",
        description="Optional barrier conditioning. Empty = marginal across barriers.",
    )

    # Beta distribution parameters — initialized from population posterior
    alpha: float = Field(default=2.0, description="Beta posterior success parameter")
    beta: float = Field(default=2.0, description="Beta posterior failure parameter")

    # Ordered outcome history (most recent at end, capped at 20)
    outcomes: List[float] = Field(
        default_factory=list,
        description="Ordered outcome scores for this mechanism, max 20 entries",
    )

    # Tracking
    sample_count: int = 0
    success_count: int = 0
    last_updated: float = Field(default_factory=time.time)

    @property
    def mean(self) -> float:
        """Posterior mean: E[Beta(a,b)] = a / (a+b)."""
        return self.alpha / (self.alpha + self.beta)

    @property
    def variance(self) -> float:
        """Posterior variance: Var[Beta(a,b)]."""
        a, b = self.alpha, self.beta
        return (a * b) / ((a + b) ** 2 * (a + b + 1))

    @property
    def confidence(self) -> float:
        """Confidence in [0, 1]: higher = tighter posterior."""
        return min(1.0, 1.0 / (1.0 + self.variance * 100))

    def sample(self) -> float:
        """Thompson Sampling: draw from Beta(alpha, beta)."""
        return float(np.random.beta(self.alpha, self.beta))

    def update(self, reward: float) -> None:
        """Bayesian update and append to outcome history."""
        self.alpha += reward
        self.beta += 1.0 - reward
        self.sample_count += 1
        if reward > 0.5:
            self.success_count += 1
        self.last_updated = time.time()

        # Keep outcome history bounded
        self.outcomes.append(reward)
        if len(self.outcomes) > 20:
            self.outcomes = self.outcomes[-20:]


# ---------------------------------------------------------------------------
# Variance components (mixed-effects decomposition)
# ---------------------------------------------------------------------------


class VarianceComponents(BaseModel):
    """Variance decomposition from the mixed-effects estimator.

    Separates total outcome variance into:
    - between_user: sigma^2_u — how much users differ from each other
    - within_user: sigma^2_e — how much a single user varies across touches
    - mechanism_interaction: sigma^2_um — user x mechanism interaction

    ICC (intraclass correlation) = sigma^2_u / (sigma^2_u + sigma^2_e)
    determines the design-effect discount: observations from the same user
    carry less independent information than observations from different users.
    """

    between_user_variance: float = Field(
        default=0.05,
        ge=0.0,
        description="sigma^2_u: how much users differ from each other",
    )
    within_user_variance: float = Field(
        default=0.05,
        ge=0.0,
        description="sigma^2_e: how much one user varies across touches",
    )
    mechanism_interaction_variance: float = Field(
        default=0.02,
        ge=0.0,
        description="sigma^2_um: user x mechanism interaction variance",
    )

    @property
    def icc(self) -> float:
        """Intraclass correlation coefficient.

        ICC = sigma^2_u / (sigma^2_u + sigma^2_e)
        High ICC (>0.5): users are very different from each other;
        within-user observations are highly correlated.
        Low ICC (<0.2): users are similar; within-user observations
        are relatively independent.
        """
        total = self.between_user_variance + self.within_user_variance
        if total < 1e-10:
            return 0.0
        return self.between_user_variance / total

    def design_effect_weight(self, n_observations_from_user: int) -> float:
        """Weight for one more observation from a user with n prior observations.

        In a design with correlated observations, the effective sample size
        is n_eff = n / (1 + (n-1) * ICC). So each additional observation
        contributes 1 / (1 + (n-1) * ICC) independent-equivalent units.

        A user with 5 observations and ICC=0.4 contributes weight=0.38
        per observation to population posteriors (vs 1.0 if independent).
        """
        if n_observations_from_user <= 0:
            return 1.0
        return 1.0 / (1.0 + (n_observations_from_user - 1) * self.icc)

    @property
    def effective_n_per_observation(self) -> float:
        """How much each additional same-user observation is worth.

        Computed for typical sequence length (7 touches).
        """
        return self.design_effect_weight(7)

    @property
    def personalization_signal(self) -> float:
        """How much user x mechanism interaction matters.

        High value (>0.3) means mechanism effectiveness varies a lot
        between users — strong signal for personalization.
        Low value (<0.1) means mechanisms work similarly across users.
        """
        total = (
            self.between_user_variance
            + self.within_user_variance
            + self.mechanism_interaction_variance
        )
        if total < 1e-10:
            return 0.0
        return self.mechanism_interaction_variance / total


# ---------------------------------------------------------------------------
# Mechanism contrast (within-user pairwise comparison)
# ---------------------------------------------------------------------------


class MechanismContrast(BaseModel):
    """Pairwise within-user mechanism comparison.

    When the same user has tried both mechanism A and mechanism B,
    the paired difference in outcomes is a strong causal signal
    (each person is their own control).
    """

    mechanism_a: str
    mechanism_b: str
    barrier: str = ""

    # Within-user effect size: mean(outcomes_a) - mean(outcomes_b)
    effect_estimate: float = 0.0
    # Standard error of the paired difference
    effect_se: float = Field(default=1.0, gt=0.0)

    observations_a: int = 0
    observations_b: int = 0

    @property
    def t_statistic(self) -> float:
        """Paired t-statistic for the within-user contrast."""
        if self.effect_se < 1e-10:
            return 0.0
        return self.effect_estimate / self.effect_se

    @property
    def total_paired_observations(self) -> int:
        """Number of paired observations (min of a and b)."""
        return min(self.observations_a, self.observations_b)

    def power_to_detect(
        self,
        effect_size: float = 0.3,
        alpha: float = 0.05,
        correlation: float = 0.5,
    ) -> float:
        """Statistical power for paired within-subject comparison.

        Uses the paired-samples power formula:
        n_paired = n_independent * (1 - rho) / 2

        For d=0.3, alpha=0.05:
        - rho=0.5: need ~88 paired obs (44 per mechanism)
        - rho=0.7: need ~53 paired obs (27 per mechanism)
        """
        n = self.total_paired_observations
        if n < 2:
            return 0.0

        # Paired t-test power: power = Phi(d * sqrt(n) / sqrt(2*(1-rho)) - z_alpha)
        from scipy.stats import norm

        z_alpha = norm.ppf(1 - alpha / 2)
        noncentrality = effect_size * math.sqrt(n) / math.sqrt(2 * (1 - correlation))
        power = 1.0 - norm.cdf(z_alpha - noncentrality)
        return float(power)


# ---------------------------------------------------------------------------
# Trajectory analysis (longitudinal engagement modeling)
# ---------------------------------------------------------------------------


class TrajectoryAnalysis(BaseModel):
    """Longitudinal trajectory analysis for a user's retargeting sequence.

    Models the shape of engagement over time to detect:
    - Warming: increasing engagement (mechanism is working)
    - Cooling: decreasing engagement (reactance building)
    - Inverted-U: initial engagement then decline (habituation)
    - Step change: sudden shift at a specific touch (breakthrough or rupture)
    - Flat: no trajectory (random variation)
    """

    user_id: str
    sequence_id: str

    # Ordered data (by touch position)
    touch_outcomes: List[float] = Field(default_factory=list)
    touch_mechanisms: List[str] = Field(default_factory=list)

    # OLS trend estimates
    linear_trend: float = Field(
        default=0.0,
        description="Slope of engagement over touches. Positive = warming.",
    )
    quadratic_trend: float = Field(
        default=0.0,
        description="Curvature. Negative with positive linear = inverted-U.",
    )

    # Changepoint detection
    changepoint_position: Optional[int] = Field(
        default=None,
        description="Touch position where trajectory changed direction",
    )
    changepoint_mechanism: Optional[str] = Field(
        default=None,
        description="Mechanism deployed at the changepoint touch",
    )

    # Autocorrelation
    ar1_coefficient: float = Field(
        default=0.0,
        description="AR(1) autocorrelation. High = outcomes are predictable from previous.",
    )

    # Classification
    trajectory_type: str = Field(
        default="insufficient_data",
        description="'warming', 'cooling', 'inverted_u', 'flat', 'step_change', 'insufficient_data'",
    )
    classification_confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Confidence in trajectory classification (R^2 of best-fit model)",
    )

    # Derived insights
    turning_point_touch: Optional[int] = Field(
        default=None,
        description="The touch that inflected the trajectory (if any)",
    )
    turning_point_mechanism: Optional[str] = Field(
        default=None,
        description="Mechanism at the turning point",
    )


# ---------------------------------------------------------------------------
# Within-subject experimental design
# ---------------------------------------------------------------------------


class WithinSubjectDesign(BaseModel):
    """Experimental design for a user's retargeting sequence.

    Instead of treating the sequence as a pure funnel, this structures it
    as a balanced incomplete block design where each user tests 2-3
    mechanisms. This enables within-subject comparisons with paired
    statistical power.

    Default allocation for 7 touches:
    - Touches 1-2: exploit (best known mechanism)
    - Touch 3: explore (second-best, for comparison)
    - Touches 4-5: exploit (may switch if exploration was better)
    - Touch 6: explore (if uncertainty remains)
    - Touch 7: exploit (close sequence with best)
    """

    user_id: str
    sequence_id: str

    # Design type
    design_type: str = Field(
        default="balanced_incomplete_block",
        description="'balanced_incomplete_block', 'adaptive_crossover', 'exploratory'",
    )

    # Slot allocation (1-indexed touch positions)
    exploration_slots: List[int] = Field(
        default_factory=lambda: [3, 6],
        description="Touch positions reserved for mechanism exploration",
    )
    exploitation_slots: List[int] = Field(
        default_factory=lambda: [1, 2, 4, 5, 7],
        description="Touch positions using best-known mechanism",
    )

    # Planned contrasts
    planned_contrasts: List[MechanismContrast] = Field(
        default_factory=list,
        description="Mechanism pairs being compared within this user",
    )

    # Power tracking
    power_estimates: Dict[str, float] = Field(
        default_factory=dict,
        description="mechanism -> estimated power with current data",
    )

    # Adaptive flags
    exploration_complete: bool = Field(
        default=False,
        description="True when power > 0.80 to detect d=0.3 for top mechanism comparison",
    )
    mechanisms_tested: List[str] = Field(
        default_factory=list,
        description="Mechanisms that have been deployed for this user",
    )

    def is_exploration_slot(self, touch_position: int) -> bool:
        """Check if this touch position should explore a new mechanism."""
        if self.exploration_complete:
            return False
        return touch_position in self.exploration_slots

    def remaining_exploration_slots(self, current_position: int) -> int:
        """How many exploration slots remain after current position."""
        return sum(1 for s in self.exploration_slots if s > current_position)


# ---------------------------------------------------------------------------
# Complete user-level posterior profile
# ---------------------------------------------------------------------------


class UserPosteriorProfile(BaseModel):
    """Complete within-subject statistical profile for one user x one brand.

    This is the user-level model that sits between CAMPAIGN and SEQUENCE
    in the 6-level Bayesian hierarchy. It tracks:
    - Per-mechanism Beta posteriors (what works for THIS person)
    - Random intercept (how responsive this user is overall vs population)
    - Mechanism slopes (per-mechanism deviation from population)
    - Within-user autocorrelation (how predictable outcomes are)
    - Engagement trajectory (warming, cooling, inverted-U)
    - Variance components (for design-effect discounting)

    Persisted in: L1 memory cache (50K entries) -> L2 Redis (30-day TTL)
    -> L3 Neo4j (permanent, debounced writes).
    """

    user_id: str
    brand_id: str
    archetype_id: str

    # Per-mechanism posteriors (keyed by mechanism name)
    mechanism_posteriors: Dict[str, UserMechanismPosterior] = Field(
        default_factory=dict,
    )

    # Per-mechanism×page_cluster posteriors (keyed by "mechanism:page_cluster")
    # Tracks user×page interaction: "does this user respond to proof on
    # analytical pages differently than on emotional pages?"
    page_mechanism_posteriors: Dict[str, UserMechanismPosterior] = Field(
        default_factory=dict,
    )

    # Random effects (mixed-effects model components)
    random_intercept: float = Field(
        default=0.0,
        description=(
            "User-level baseline deviation from population mean. "
            "Positive = more responsive than average."
        ),
    )
    random_intercept_variance: float = Field(
        default=0.05,
        description="Uncertainty in random intercept estimate",
    )
    mechanism_slopes: Dict[str, float] = Field(
        default_factory=dict,
        description=(
            "Per-mechanism random slopes: how much more/less this user "
            "responds to mechanism X vs population. Keyed by mechanism name."
        ),
    )

    # Within-user temporal structure
    within_user_correlation: float = Field(
        default=0.0,
        description="Estimated AR(1) autocorrelation across sequential touches",
    )

    # Trajectory (updated incrementally with each touch)
    trajectory_trend: float = Field(
        default=0.0,
        description="Linear slope of engagement over touches. Positive = warming.",
    )
    trajectory_curvature: float = Field(
        default=0.0,
        description="Quadratic term. Negative + positive linear = inverted-U.",
    )

    # Aggregate tracking
    total_touches_observed: int = 0
    total_reward_sum: float = 0.0
    all_outcomes: List[float] = Field(
        default_factory=list,
        description="All outcome scores in order, max 50 entries",
    )
    all_mechanisms: List[str] = Field(
        default_factory=list,
        description="Mechanisms deployed in order, max 50 entries",
    )

    # Variance components (from population-level mixed-effects estimator)
    variance_components: VarianceComponents = Field(
        default_factory=VarianceComponents,
    )

    # Timestamps
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )

    @property
    def user_mean_reward(self) -> float:
        """This user's mean outcome across all touches."""
        if self.total_touches_observed == 0:
            return 0.5  # Uninformative
        return self.total_reward_sum / self.total_touches_observed

    @property
    def mechanisms_tried(self) -> int:
        """Number of distinct mechanisms this user has experienced."""
        return len(self.mechanism_posteriors)

    @property
    def design_effect_weight(self) -> float:
        """Weight for next population-level update from this user."""
        return self.variance_components.design_effect_weight(
            self.total_touches_observed
        )

    def get_mechanism_posterior(self, mechanism: str) -> Optional[UserMechanismPosterior]:
        """Get this user's posterior for a specific mechanism, or None."""
        return self.mechanism_posteriors.get(mechanism)

    def get_best_mechanism(self) -> Optional[Tuple[str, float]]:
        """Return (mechanism_name, posterior_mean) for user's best mechanism."""
        if not self.mechanism_posteriors:
            return None
        best = max(
            self.mechanism_posteriors.items(),
            key=lambda kv: kv[1].mean,
        )
        return best[0], best[1].mean

    def update_trajectory(self) -> None:
        """Recompute trajectory trend from outcome history.

        Uses online OLS for linear and quadratic terms.
        Called after each new outcome is appended to all_outcomes.
        """
        n = len(self.all_outcomes)
        if n < 3:
            self.trajectory_trend = 0.0
            self.trajectory_curvature = 0.0
            return

        # Simple OLS: y = a + b*x + c*x^2
        # Use centered positions to reduce collinearity
        x = np.arange(n, dtype=np.float64)
        x_centered = x - x.mean()
        y = np.array(self.all_outcomes, dtype=np.float64)

        # Linear fit
        if n < 4:
            # Not enough data for quadratic — linear only
            x_mat = np.column_stack([np.ones(n), x_centered])
        else:
            x_mat = np.column_stack([np.ones(n), x_centered, x_centered ** 2])

        try:
            coeffs, _, _, _ = np.linalg.lstsq(x_mat, y, rcond=None)
            self.trajectory_trend = float(coeffs[1])
            self.trajectory_curvature = float(coeffs[2]) if len(coeffs) > 2 else 0.0
        except (np.linalg.LinAlgError, ValueError):
            self.trajectory_trend = 0.0
            self.trajectory_curvature = 0.0

    def update_ar1(self) -> None:
        """Estimate AR(1) autocorrelation from outcome sequence.

        rho = Cov(y_t, y_{t-1}) / Var(y_t)
        With 7 observations, this is a rough estimate but still informative.
        """
        if len(self.all_outcomes) < 3:
            self.within_user_correlation = 0.0
            return

        y = np.array(self.all_outcomes, dtype=np.float64)
        y_mean = y.mean()
        y_var = y.var()
        if y_var < 1e-10:
            self.within_user_correlation = 0.0
            return

        # Lag-1 autocovariance
        lag1_cov = np.mean((y[1:] - y_mean) * (y[:-1] - y_mean))
        self.within_user_correlation = float(np.clip(lag1_cov / y_var, -0.99, 0.99))
