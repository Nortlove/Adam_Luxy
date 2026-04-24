"""PlantModel — the inferential-chain-conditional prediction primitive.

The plant model is ADAM's native substitute for a treatment-effect-
significance framework. Given a RecommendationClass identity + the
inferential chain + CLT-recalibrated construct priors + audience summary
+ posture band, it outputs a predicted SpiesDistribution over the
outcome metric together with a bias-flag structure the adjudicator
consumes when reconciling predicted vs. realized at horizon completion.

Frame discipline (Foundation §4.3, §4.4; pilot plan 2026-04-24):

- The plant model predicts an OUTCOME DISTRIBUTION, not an expected
  delta. The projection is a bin-weighted SPIES distribution because
  the native adjudicator reports residual divergence against a
  distribution, not a scalar effect.
- Priors come from `effect_size_correction.py` — publication-bias
  corrected effects, never raw published values. Uncorrected construct
  priors set `publication_bias_residual=True` in the bias-flag
  structure so the adjudicator accounts for the remaining inflation.
- Single-level shrinkage toward a generic industry prior is the A14
  compromise committed to in `project_weakness_4_recommendation_class_primitive.md`.
  Every projection that takes this path emits `winners_curse_portion=True`
  in its CompetingActivations. The flag retires when Weakness #8 lands
  and the full hierarchy (industry → partner → advertiser → workspace
  → class) is available. See: ``a14_compromises.SINGLE_LEVEL_SHRINKAGE``.
- Attention-inversion posture enters via the `context_posture_band`:
  `autopilot_*` bands route a larger fraction of conversions through
  the autopilot route (the blend-and-fulfill fitness landscape the
  platform is selecting for); `vigilance_*` bands route a larger
  fraction through the attention route (fragile, regret-associated).
  Route fractions are DERIVED from expected processing-depth
  distributions per posture band composed with a relative
  P(convert | depth) proxy (see ``processing_depth_priors.py``).
  Both priors are externally sourced and unvalidated — see
  ``a14_compromises.DEPTH_PRIOR_UNVALIDATED``.
- Counter-regulation (habituation, reactance dynamics) is NOT modeled
  in the plant — it's carried as a structured bias flag until per-user
  habituation data lets us estimate it. This is the same retirement-
  trigger pattern as winners-curse. See:
  ``a14_compromises.COUNTER_REGULATION_UNTRACKED``.

Scope of this slice:

- `project()` — pre-observation: builds a `ProjectedImpact` with a
  predicted SpiesDistribution from the inputs.
- Deterministic given fixed inputs. Same (identity, chain_context,
  priors, audience_summary, posture) → same projection → same
  content_hash on the resulting ProjectedImpact.

NOT in this slice (land later):

- Interim-look execution wiring into task_23–32 daily pipeline
  (slice for whoever owns DCIL).
- Habituation model (expires the counter_regulation_untracked flag).
- Full hierarchical shrinkage (expires winners_curse_portion; lands
  with Weakness #8).
- Processing-depth weighted autopilot/attention allocation (currently
  posture-band-only; processing-depth weighting arrives with the
  Layer-11 dimension being fully calibrated — Foundation rule 11).
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass, field
from typing import List, Optional, Sequence

from adam.core.learning.effect_size_correction import (
    CorrectionMethod,
    PublicationBiasCorrectedEffect,
)
from adam.intelligence.recommendation_class.projected_impact import (
    AudienceScope,
    AudienceSummary,
    CompetingActivations,
    GoalFulfillmentOutcome,
    PrimingCondition,
    ProjectedImpact,
    SpiesDistribution,
)
from adam.intelligence.recommendation_class.graph import (
    RecommendationClassIdentity,
    recommendation_class_id,
)
from adam.intelligence.recommendation_class.processing_depth_priors import (
    VALID_POSTURE_BANDS,
    expected_route_fractions,
)


# =============================================================================
# Industry-prior baseline (A14 — single-level shrinkage)
# =============================================================================
# See: a14_compromises.SINGLE_LEVEL_SHRINKAGE
# Pilot uses a single generic industry prior. Hierarchy (industry → partner
# → advertiser → workspace → class) ships with Weakness #8.
# 2% durable-conversion-rate with concentration 30 is ADAM's pilot default —
# thin enough that ~30 real observations at a cell overwhelm it, wide enough
# that noisy cells don't drown in the prior.

DEFAULT_INDUSTRY_PRIOR_RATE = 0.02
DEFAULT_INDUSTRY_PRIOR_CONCENTRATION = 30.0


# =============================================================================
# Posture-band → route-fraction derivation
# =============================================================================
# See: a14_compromises.DEPTH_PRIOR_UNVALIDATED (successor to
# POSTURE_ONLY_ROUTE_SPLIT after the 2026-04-25 refactor)
#
# Route fractions are no longer a flat per-band table. They are derived
# from the expected processing-depth distribution per posture band
# composed with a relative P(convert | depth) proxy, both living in
# ``processing_depth_priors.py``. Each cell's (autopilot_fraction,
# attention_fraction) is computed at projection time by
# ``expected_route_fractions(posture_band)``.
#
# Refactor motivation (attention-inversion + Dawkins rule #11): the
# plant model's projection layer now branches on depth distributions
# rather than posture buckets. This unlocks:
#   - Adjudicator-side comparison of projected vs realized depth
#     distributions (new theory-failure signal).
#   - Two-axis recalibration (depth distribution × P(convert|depth))
#     rather than single-axis route fractions.
#   - Per-cell distribution priors as a named successor slice.


# =============================================================================
# SPIES binning
# =============================================================================
# Default SPIES binning for durable-conversion-rate projections. Bins
# concentrate resolution in the low-rate region where most real
# conversion rates actually live, with a long tail bin capturing rare
# high-performers. 8 bins is the practical minimum for meaningful
# residual-divergence decomposition without forcing elicitation that
# the internal plant model cannot actually differentiate.

DEFAULT_CONVERSION_RATE_BIN_EDGES: tuple[float, ...] = (
    0.000, 0.005, 0.010, 0.020, 0.040, 0.080, 0.150, 0.300, 1.000,
)


# =============================================================================
# PlantModelInputs — the inputs PlantModel.project consumes
# =============================================================================


@dataclass(frozen=True)
class PlantModelInputs:
    """All non-inferred inputs to a plant-model projection.

    Separating inputs from the model clarifies the contract: deterministic
    projection is a pure function of these inputs + the model's
    construction-time configuration. Callers construct this dataclass
    explicitly rather than passing bare kwargs, so auditing a projection
    later requires only replaying the inputs through the same model
    configuration.
    """

    identity: RecommendationClassIdentity
    audience_scope: AudienceScope
    priming_condition: PrimingCondition
    audience_summary: AudienceSummary
    construct_effect: Optional[PublicationBiasCorrectedEffect]
    # If None, the industry prior alone drives the projection — the
    # weakest case. If present, the construct's corrected effect size
    # informs the expected rate before shrinkage.
    horizon_days: int = 14
    outcome_metric: str = "durable_conversion_rate"
    # The SpiesDistribution.metric_name stamped on the projection.

    def validate(self) -> None:
        self.identity.validate()
        self.audience_scope.validate()
        self.priming_condition.validate()
        self.audience_summary.validate()
        if self.horizon_days <= 0:
            raise ValueError(
                f"PlantModelInputs.horizon_days must be positive; "
                f"got {self.horizon_days}"
            )
        if not self.outcome_metric:
            raise ValueError(
                "PlantModelInputs.outcome_metric is required"
            )
        if self.identity.archetype_id != self.audience_scope.archetype_id:
            raise ValueError(
                f"identity.archetype_id ({self.identity.archetype_id!r}) "
                f"must match audience_scope.archetype_id "
                f"({self.audience_scope.archetype_id!r})"
            )


# =============================================================================
# PlantModel — the predictive primitive
# =============================================================================


@dataclass(frozen=True)
class PlantModel:
    """Pre-observation projection of a RecommendationClass.

    Construction-time configuration lives on the instance (industry
    prior, bin edges). `project()` is a pure function of
    `PlantModelInputs` + this configuration.
    """

    industry_prior_rate: float = DEFAULT_INDUSTRY_PRIOR_RATE
    industry_prior_concentration: float = DEFAULT_INDUSTRY_PRIOR_CONCENTRATION
    bin_edges: tuple[float, ...] = DEFAULT_CONVERSION_RATE_BIN_EDGES
    baseline_rate: float = DEFAULT_INDUSTRY_PRIOR_RATE

    def __post_init__(self) -> None:
        if not (0.0 < self.industry_prior_rate < 1.0):
            raise ValueError(
                f"industry_prior_rate must be in (0, 1); "
                f"got {self.industry_prior_rate}"
            )
        if self.industry_prior_concentration <= 0:
            raise ValueError(
                f"industry_prior_concentration must be > 0; "
                f"got {self.industry_prior_concentration}"
            )
        if len(self.bin_edges) < 2:
            raise ValueError(
                f"bin_edges needs at least 2 entries; got {len(self.bin_edges)}"
            )
        for i in range(len(self.bin_edges) - 1):
            if self.bin_edges[i] >= self.bin_edges[i + 1]:
                raise ValueError(
                    f"bin_edges must be strictly increasing; "
                    f"edge[{i}]={self.bin_edges[i]} >= "
                    f"edge[{i+1}]={self.bin_edges[i+1]}"
                )
        if not (0.0 <= self.baseline_rate <= 1.0):
            raise ValueError(
                f"baseline_rate must be in [0, 1]; got {self.baseline_rate}"
            )

    # ── PROJECTION ────────────────────────────────────────────────────────

    def project(
        self,
        inputs: PlantModelInputs,
        claim_id: Optional[str] = None,
    ) -> ProjectedImpact:
        """Build a pre-registered ProjectedImpact from plant-model inputs.

        Returns a frozen ProjectedImpact whose content_hash is a
        deterministic function of the inputs + this plant model's
        configuration. Same (inputs, model) → same hash, forever.
        """
        inputs.validate()
        self._validate_posture_band(inputs.identity.context_posture_band)

        alpha_post, beta_post = self._posterior_parameters(inputs)
        bin_weights = self._beta_bin_weights(alpha_post, beta_post)
        projected_dist = SpiesDistribution(
            metric_name=inputs.outcome_metric,
            bin_edges=list(self.bin_edges),
            bin_weights=bin_weights,
        )

        autopilot_frac, attention_frac = self._route_split(
            inputs.identity.context_posture_band,
            inputs.priming_condition.attentional_posture,
            inputs.priming_condition.attentional_posture_confidence,
        )

        goal_outcome = GoalFulfillmentOutcome(
            outcome_metric=inputs.outcome_metric,
            projected_distribution=projected_dist,
            autopilot_route_fraction=autopilot_frac,
            attention_route_fraction=attention_frac,
            weighting_by_processing_depth=False,
            # False until processing-depth weighting is wired — honesty
            # flag so downstream readers know the split is posture-only.
        )

        competing = self._competing_activations(inputs)

        rec_class_id = recommendation_class_id(inputs.identity)
        resolved_claim_id = claim_id or self._deterministic_claim_id(
            rec_class_id, inputs,
        )

        claim = ProjectedImpact(
            claim_id=resolved_claim_id,
            recommendation_class_id=rec_class_id,
            priming_condition=inputs.priming_condition,
            audience_scope=inputs.audience_scope,
            goal_fulfillment_outcome=goal_outcome,
            competing_activations=competing,
            audience_summary=inputs.audience_summary,
            horizon_days=inputs.horizon_days,
        )
        claim.validate()

        content_hash = claim.compute_content_hash()
        return ProjectedImpact(
            claim_id=claim.claim_id,
            recommendation_class_id=claim.recommendation_class_id,
            priming_condition=claim.priming_condition,
            audience_scope=claim.audience_scope,
            goal_fulfillment_outcome=claim.goal_fulfillment_outcome,
            competing_activations=claim.competing_activations,
            audience_summary=claim.audience_summary,
            horizon_days=claim.horizon_days,
            created_at=None,  # filled by to_dict() on serialization
            content_hash=content_hash,
        )

    # ── PLANT MATH ────────────────────────────────────────────────────────

    def implied_rate(self, inputs: PlantModelInputs) -> float:
        """Posterior-mean conversion rate for the cell.

        This is the scalar projection the adjudicator compares against
        realized rates — drawn directly from the Beta posterior mean
        (alpha / (alpha + beta)), NOT from the bin-midpoint-weighted
        mean of the projected SPIES distribution. The SPIES binning is
        lossy (wide right-tail bins can inflate a midpoint mean) so
        scalar comparisons must bypass it.
        """
        alpha, beta_param = self.posterior_parameters(inputs)
        return alpha / (alpha + beta_param)

    def posterior_parameters(
        self, inputs: PlantModelInputs,
    ) -> tuple[float, float]:
        """Public accessor for the Beta(alpha, beta) posterior parameters."""
        inputs.validate()
        return self._posterior_parameters(inputs)

    def _posterior_parameters(
        self, inputs: PlantModelInputs,
    ) -> tuple[float, float]:
        """Single-level shrinkage toward the industry prior.

        Construct-effect interpretation:
          The corrected d from PublicationBiasCorrectedEffect is treated
          as a LOG-ODDS SHIFT on the industry baseline, NOT as an absolute
          probability. Effect sizes in advertising are differences from
          a low baseline (2% conversion typical); mapping d to an absolute
          probability around 0.5 (signal-detection framing) would yield
          nonsensical 50%+ projected rates. The log-odds shift
          interpretation composes correctly with the industry baseline:

            logit(p_construct) = logit(p_industry) + corrected_d

          This is the conservative interpretation at pilot launch. When
          external psychometric validation delivers construct-specific
          calibrations (month 4-5 contractor delivery), the interpretation
          can be sharpened per construct.

        Shrinkage weight: evidence strength at this cell pulls toward
        the construct-conditioned rate; low evidence shrinks toward
        the industry prior. Half-weight point at prior_concentration
        observations — matches the "effective prior sample size"
        interpretation.

        Winners-curse discipline: single-level shrinkage is the A14
        compromise (the flag carries forward to CompetingActivations).
        The industry prior is GENERIC by design — noisy cells should
        drown in it at low evidence counts. See:
        ``a14_compromises.SINGLE_LEVEL_SHRINKAGE``.
        """
        industry_alpha = (
            self.industry_prior_concentration * self.industry_prior_rate
        )
        industry_beta = (
            self.industry_prior_concentration * (1.0 - self.industry_prior_rate)
        )

        if inputs.construct_effect is None:
            return (industry_alpha, industry_beta)

        construct_rate = _logit_shifted_rate(
            baseline_rate=self.industry_prior_rate,
            logit_shift=inputs.construct_effect.corrected_d,
        )
        construct_alpha = self.industry_prior_concentration * construct_rate
        construct_beta = (
            self.industry_prior_concentration * (1.0 - construct_rate)
        )

        obs = inputs.audience_summary.observation_count
        w = obs / (obs + self.industry_prior_concentration)
        w = max(0.0, min(1.0, w))

        alpha_post = w * construct_alpha + (1.0 - w) * industry_alpha
        beta_post = w * construct_beta + (1.0 - w) * industry_beta
        return (alpha_post, beta_post)

    def _beta_bin_weights(
        self, alpha: float, beta_param: float,
    ) -> List[float]:
        """Discretize a Beta(alpha, beta) distribution over the bin edges.

        Uses the regularized incomplete beta function via a log-gamma
        implementation so the plant has no scipy dependency. Weights
        are the Beta CDF increments across consecutive edges; edges
        below 0 and above 1 are clamped for the Beta's [0, 1] support.
        """
        weights: List[float] = []
        prev_cdf: Optional[float] = None
        for i, edge in enumerate(self.bin_edges):
            clamped = max(0.0, min(1.0, edge))
            cdf = _regularized_incomplete_beta(clamped, alpha, beta_param)
            if prev_cdf is not None:
                increment = cdf - prev_cdf
                if increment < 0.0:
                    increment = 0.0
                weights.append(increment)
            prev_cdf = cdf
        # Normalize to sum to 1 exactly — absorbs tiny edge truncation
        # from clamping the last bin at edge=1.0 and numeric error.
        total = sum(weights)
        if total <= 0.0:
            # Degenerate fit: uniform over bins as a safe fallback. Only
            # reachable if alpha or beta misreports to produce no mass.
            uniform = 1.0 / len(weights)
            return [uniform] * len(weights)
        return [w / total for w in weights]

    def _route_split(
        self,
        context_posture_band: str,
        attentional_posture: float,
        attentional_posture_confidence: float,
    ) -> tuple[float, float]:
        """Assign autopilot / attention route fractions.

        Primary signal: ``expected_route_fractions(context_posture_band)``
        derives (autopilot_frac, attention_frac) from the expected
        processing-depth distribution × relative P(convert | depth)
        proxy (see ``processing_depth_priors.py``). These base
        fractions sum to 1.0 for the band.

        Secondary: the PrimingCondition's continuous
        ``attentional_posture × confidence`` nudges the split toward
        the signed direction (negative posture → autopilot; positive
        → attention) proportional to confidence. Cap at 0.1 mass
        shifted; low-confidence nudges don't overwhelm the base.
        """
        base_auto, base_att = expected_route_fractions(context_posture_band)
        max_shift = 0.10
        shift = max_shift * attentional_posture_confidence * attentional_posture
        # attentional_posture in [-1, 1]: -1 = autopilot, +1 = vigilance.
        # Negative shift → move mass toward autopilot route.
        auto_frac = base_auto - shift
        att_frac = base_att + shift
        # Clip and guard against overflow of the [0, 1] sum budget.
        auto_frac = max(0.0, min(1.0, auto_frac))
        att_frac = max(0.0, min(1.0, att_frac))
        if auto_frac + att_frac > 1.0:
            scale = 1.0 / (auto_frac + att_frac)
            auto_frac *= scale
            att_frac *= scale
        return (auto_frac, att_frac)

    def _competing_activations(
        self, inputs: PlantModelInputs,
    ) -> CompetingActivations:
        """Populate the structured bias-flag output for this projection.

        Every flag has an explicit retirement trigger documented in the
        pilot plan. The plant model sets them honestly: `True` means
        "known model limitation operating on this projection."
        """
        # Winners-curse: see a14_compromises.SINGLE_LEVEL_SHRINKAGE —
        # single-level shrinkage is the only shrinkage layer pilot ships.
        winners_curse = True

        # Depth-prior unvalidated: see a14_compromises.DEPTH_PRIOR_UNVALIDATED
        # — route fractions derive from expected depth distributions
        # and a relative P(convert|depth) proxy, both externally
        # sourced and per-posture-band rather than per-cell.
        attention_residual = True

        # Counter-regulation: see a14_compromises.COUNTER_REGULATION_UNTRACKED
        # — habituation/reactance dynamics not yet estimated.
        counter_regulation = True

        # Publication-bias residual: True unless the construct effect
        # is pre-registered (the strongest correction). RoBMA-median or
        # Schimmack-shrunk corrections still have residual bias the
        # adjudicator must account for.
        if inputs.construct_effect is None:
            publication_bias = True
        else:
            publication_bias = (
                inputs.construct_effect.correction_method
                != CorrectionMethod.PRE_REGISTERED
            )

        return CompetingActivations(
            counter_regulation_untracked=counter_regulation,
            attention_route_residual=attention_residual,
            winners_curse_portion=winners_curse,
            publication_bias_residual=publication_bias,
            baseline_rate=self.baseline_rate,
            notes=(
                "Pilot plant-model projection with single-level "
                "shrinkage, posture-only route split, and no counter-"
                "regulation estimation. Flags retire per "
                "project_pilot_execution_plan.md."
            ),
        )

    # ── DETERMINISM HELPERS ───────────────────────────────────────────────

    @staticmethod
    def _deterministic_claim_id(
        recommendation_class_id_value: str,
        inputs: PlantModelInputs,
    ) -> str:
        """Deterministic claim_id from the projection inputs.

        Callers can override by passing `claim_id=` to project(). The
        auto-generated id is stable on (class id, audience scope, horizon).
        """
        slug_parts = [
            recommendation_class_id_value,
            inputs.audience_scope.vertical,
            inputs.audience_scope.horizon_band,
            str(inputs.horizon_days),
            inputs.outcome_metric,
        ]
        slug = "|".join(slug_parts)
        digest = hashlib.sha256(slug.encode("utf-8")).hexdigest()[:16]
        return f"claim_{digest}"

    @staticmethod
    def _validate_posture_band(context_posture_band: str) -> None:
        if context_posture_band not in VALID_POSTURE_BANDS:
            raise ValueError(
                f"unknown context_posture_band {context_posture_band!r}; "
                f"must be one of {sorted(VALID_POSTURE_BANDS)}"
            )


# =============================================================================
# Regularized incomplete beta — pure-Python, no scipy
# =============================================================================


def _logit_shifted_rate(baseline_rate: float, logit_shift: float) -> float:
    """Shift a baseline rate by a logit-scale delta.

        logit(p) = log(p / (1 - p))
        p_shifted = sigmoid(logit(baseline) + logit_shift)

    Maps Cohen's d (treated as log-odds shift) to an absolute rate
    that stays in [0, 1] and composes correctly with low baselines.
    """
    eps = 1e-9
    clamped = min(max(baseline_rate, eps), 1.0 - eps)
    baseline_logit = math.log(clamped / (1.0 - clamped))
    shifted_logit = baseline_logit + logit_shift
    return 1.0 / (1.0 + math.exp(-shifted_logit))


def _regularized_incomplete_beta(
    x: float, a: float, b: float,
) -> float:
    """Regularized incomplete beta function I_x(a, b).

    Pure Python implementation via the continued-fraction expansion
    (Numerical Recipes §6.4). Avoids scipy so the plant model ships
    without heavy dependencies.

    Domain guards: I_0 = 0, I_1 = 1. Input x is clamped to [0, 1].
    """
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    if a <= 0.0 or b <= 0.0:
        raise ValueError(f"a and b must be positive; got a={a}, b={b}")

    log_bt = (
        math.lgamma(a + b)
        - math.lgamma(a)
        - math.lgamma(b)
        + a * math.log(x)
        + b * math.log(1.0 - x)
    )
    bt = math.exp(log_bt)

    if x < (a + 1.0) / (a + b + 2.0):
        return bt * _betacf(x, a, b) / a
    return 1.0 - bt * _betacf(1.0 - x, b, a) / b


def _betacf(
    x: float, a: float, b: float,
    max_iter: int = 200, eps: float = 3e-7,
) -> float:
    """Continued-fraction expansion used by the regularized incomplete
    beta. Lifted from Numerical Recipes in C §6.4 `betacf`."""
    qab = a + b
    qap = a + 1.0
    qam = a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < 1e-30:
        d = 1e-30
    d = 1.0 / d
    h = d
    for m in range(1, max_iter + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < 1e-30:
            d = 1e-30
        c = 1.0 + aa / c
        if abs(c) < 1e-30:
            c = 1e-30
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < 1e-30:
            d = 1e-30
        c = 1.0 + aa / c
        if abs(c) < 1e-30:
            c = 1e-30
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < eps:
            return h
    return h


# =============================================================================
# Exported names
# =============================================================================

__all__ = [
    "DEFAULT_CONVERSION_RATE_BIN_EDGES",
    "DEFAULT_INDUSTRY_PRIOR_CONCENTRATION",
    "DEFAULT_INDUSTRY_PRIOR_RATE",
    "PlantModel",
    "PlantModelInputs",
]
