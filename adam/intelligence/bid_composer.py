# =============================================================================
# Bid Composer — populates DecisionTrace.AlternativeCandidate bid slots
# Location: adam/intelligence/bid_composer.py
# =============================================================================
"""Compose Spines #6 + #8 + #9 + Phase 2 at decision time.

Closes the wiring gap from the 2026-05-01 handoff: the
DecisionTrace AlternativeCandidate schema (ca03336) carries
``fluency_score`` / ``epistemic_bonus`` / ``bid_value`` slots; the
producer primitives (Spine #8 epistemic_bid_bonus e73f4c1, Spine #9
kelly_bid_sizing ff3a200, Phase 2 posture_mechanism_prior 3db50de)
shipped as substrate; until this slice no producer wired them into
the cascade-emitted trace.

WHY THIS EXISTS
---------------

The directive's Phase 4 deliverable line 1011-1015 names the schema
slots; lines 1016-1020 (Spine #8) and 1021-1024 (Spine #9) name the
producer primitives. Lines 970 + 974-976 (Phase 2) name the fluency
proxy. This slice is the typed composer that consumes the substrate
and populates the slots — without it, the DefensiveReasoningRender
shows "—" / nothing for those scoring components and the LUXY CMO
cannot inspect the dual-control decomposition.

ATTENTION-INVERSION DISCIPLINE
------------------------------

Foundation rule 11 (the fitness function IS the ethics) +
project_attention_inversion_platform_core memory: the directive line
220 names the structural attention-inversion safeguard:

    "the epistemic bonus is multiplied by an indicator that the
     candidate has already passed the Spine #4 fluency floor.
     Reactance prevention is structural, not voluntary."

At the cascade level (without a typed creative-resolution layer),
the per-alternative fluency proxy is the **posture × mechanism
compatibility prior** (Phase 2 line 970). When a candidate scores
LOW on that prior — meaning the mechanism's natural processing route
mismatches the page's attentional posture — fluency_passed=False
and ``compute_epistemic_bonus`` returns 0.0 with rationale
"blocked_by_fluency_floor". The structural gate is hard.

The pragmatic Kelly bid is NOT gated by mechanism-level fluency at
this layer — the directive's hard fluency floor (line 974) operates
at the creative-bundle level (creative + page → blend_fit). When
the creative-resolution layer ships, that hard filter will sit
EARLIER in the pipeline and drop creatives entirely; this slice
preserves the same structural commitment at the granularity it can
operate on (mechanism × posture).

COMPOSITION
-----------

Per-alternative:
    fluency_score   = compatibility_prior(posture, mechanism)
    fluency_passed  = (fluency_score > FLUENCY_PROXY_FLOOR)  # Phase 2 line 970
    epistemic_bonus = compute_epistemic_bonus(
                          individual=bong_posterior,
                          observation_precision=1.0,
                          fluency_passed=fluency_passed,
                          cohort_daily_budget=None,
                      ).bonus
    pragmatic_bid   = compute_pragmatic_bid(
                          posterior_edge=alternative.posterior_score,
                          posterior_variance=affinity_variance(bong, mechanism),
                          supply_path=supply_path,
                      ).bid_value
    bid_value       = pragmatic_bid + epistemic_bonus

Per the directive's dual-control formulation (line 282):
    bid_value(a | i, c) = pragmatic(a | i, c) + epistemic(a | i, c)

DISCIPLINE (B3-LUXY a/b/c/d)
----------------------------

(a) Citations: directive Phase 4 lines 1011-1024; Spine #8 lines
    273-293 (closed-form EIG); Spine #9 lines 295-313 (fractional
    Kelly + winner's-curse); Phase 2 line 970 (posture × mechanism
    compatibility prior); Spine #5 line 220 (fluency-floor gate on
    epistemic bonus). The dual-control composition pattern is pinned
    by the existing Spine #9 tests (test_kelly_bid_sizing.py
    test_dual_control_composition_*).

(b) Tests pin: per-alternative slots populated when bong_posterior +
    posture supplied; fluency_score equals compatibility_prior;
    epistemic_bonus=0 when posture×mechanism is LOW (structural
    gate); bid_value = pragmatic + epistemic; chosen-mechanism
    bid_value at trace level uses chosen_score as edge; missing
    inputs (no bong, no posture) return alternatives unchanged with
    all slots None; Pydantic round-trip preserves slot values;
    multi-alternative composition order preserved.

(c) calibration_pending=True. FLUENCY_PROXY_FLOOR = 0.30 sits between
    COMPATIBILITY_LOW (0.25) and COMPATIBILITY_MID (0.50) so a LOW-
    matched alternative is gated but a MID alternative passes. LUXY
    pilot data + the matched_vs_mismatched_diagonals accumulator will
    calibrate. A14 flag: BID_COMPOSER_FLUENCY_PROXY_FLOOR_PILOT_PENDING.

(d) Honest tags — what is NOT in this slice (named successors):

    * Creative-level hard fluency floor (the directive's line 974
      "wire as eligibility filter, not as score modifier"). That
      operates on (creative_bundle × page_bundle) via blend_fit,
      which requires a typed creative-resolution layer. When it
      ships, fluency_floor.filter_creatives_by_fluency_floor sits
      BEFORE the cascade and drops creatives entirely; this slice
      preserves the same structural commitment at the mechanism
      granularity (epistemic_bonus gated on posture×mechanism).
    * Cohort-specific daily budget cap on epistemic_bonus. Spine #7
      cohort discovery is BLOCKED on Loop B per the session handoff;
      compose_alternative_bid_metadata passes cohort_daily_budget=None
      so no cap is applied. When cohorts ship, the cohort budget
      flows in here.
    * Pacing modifier from cohort-conditional Whittle-index
      allocation. Same Loop-B blocker as cohort budget. Default
      pacing_modifier=1.0.
    * Supply-path detection from the bid request. The cascade does
      not currently parse SSP fields; default SupplyPath.OPEN_EXCHANGE
      (most conservative shading 0.85) until a parser ships.
    * Calibrated posterior_edge from a conversion-prediction layer.
      We use the cascade's mechanism_score (= posterior_score per
      alternative) as the proxy for E[reward]. The honest interpret-
      ation: this is a soft posterior-score-based bid until a
      conversion-prediction layer ships its own typed edge.
    * Per-supply-path empirical clearing-distribution shading.
      Spine #9 substrate uses scalar shading factors per directive
      line 309; the empirical estimator is its own slice.
"""

from __future__ import annotations

import logging
from typing import Any, List, Optional

from adam.intelligence.decision_trace import AlternativeCandidate
from adam.intelligence.epistemic_bid_bonus import (
    DEFAULT_PRECISION_DECAY_SCALE,
    DEFAULT_W_MAX,
    compute_epistemic_bonus,
)
from adam.intelligence.kelly_bid_sizing import (
    DEFAULT_KELLY_FRACTION_QUARTER,
    SupplyPath,
    compute_pragmatic_bid,
)
from adam.intelligence.per_user_posterior_modulation import (
    BONG_TO_COHORT_DIM,
    MECHANISM_DIMENSION_MAP,
)
from adam.intelligence.posture_mechanism_prior import (
    COMPATIBILITY_LOW,
    compatibility_prior,
)

logger = logging.getLogger(__name__)


# A14 BID_COMPOSER_FLUENCY_PROXY_FLOOR_PILOT_PENDING
#
# Sits between COMPATIBILITY_LOW (0.25) and COMPATIBILITY_MID (0.50) so
# a LOW-matched alternative (mismatched diagonal) is gated but MID and
# HIGH alternatives pass. The structural attention-inversion gate at
# the mechanism granularity.
FLUENCY_PROXY_FLOOR: float = 0.30

# Default observation precision when caller doesn't supply one. The EIG
# is monotonic in this — high observation precision means each
# observation reduces variance more, so EIG per impression is higher.
# 1.0 is the closed-form default in epistemic_bid_bonus tests.
DEFAULT_OBSERVATION_PRECISION: float = 1.0

# Default supply path when the bid request doesn't carry SSP routing.
# OPEN_EXCHANGE has the highest winner's-curse shading (0.85) — the
# most conservative default.
DEFAULT_SUPPLY_PATH: SupplyPath = SupplyPath.OPEN_EXCHANGE


def affinity_variance_for_mechanism(
    bong_posterior: Any,
    mechanism: str,
) -> Optional[float]:
    """Variance of the per-mechanism affinity under the BONG posterior.

    Mirrors confidence_snapshot's variance-of-mean reduction
    (independence assumption, diagonal approximation):

        var(affinity) = (1/n²) · Σ σ_i²

    over the mechanism's primary cohort-side dimensions.

    Returns None when:
      * mechanism not in MECHANISM_DIMENSION_MAP
      * BONG updater not initialized / read fails
      * No primary dim of the mechanism overlaps the BONG dim vocabulary

    Soft-fail: caller treats None as "no Kelly variance available".
    The honest behavior in that case is to return zero pragmatic bid
    (Kelly-degenerate); compute_pragmatic_bid handles it via the
    ``no_uncertainty`` rationale.
    """
    primary_dims = MECHANISM_DIMENSION_MAP.get(mechanism)
    if not primary_dims:
        return None

    try:
        from adam.intelligence.bong import get_bong_updater
        updater = get_bong_updater()
        if updater.prior_eta is None:
            return None
        var_vec = updater.get_per_dimension_variance(bong_posterior)
    except Exception as exc:  # noqa: BLE001
        logger.debug("affinity_variance_for_mechanism: BONG read failed: %s", exc)
        return None

    primary_set = set(primary_dims)
    vars_ = []
    for i, bong_dim in enumerate(updater.dimension_names):
        if i >= len(var_vec):
            break
        cohort_dim = BONG_TO_COHORT_DIM.get(bong_dim, bong_dim)
        if cohort_dim not in primary_set:
            continue
        try:
            vars_.append(float(var_vec[i]))
        except (TypeError, ValueError):
            continue

    if not vars_:
        return None

    n = len(vars_)
    return sum(vars_) / (n * n)


def compose_alternative_bid_metadata(
    alternative: AlternativeCandidate,
    *,
    posture: str,
    bong_posterior: Any,
    supply_path: SupplyPath = DEFAULT_SUPPLY_PATH,
    observation_precision: float = DEFAULT_OBSERVATION_PRECISION,
    w_max: float = DEFAULT_W_MAX,
    decay_scale: float = DEFAULT_PRECISION_DECAY_SCALE,
    kelly_fraction: float = DEFAULT_KELLY_FRACTION_QUARTER,
) -> AlternativeCandidate:
    """Return a new AlternativeCandidate with bid slots populated.

    The composition (per directive Phase 4 lines 1011-1024):
      fluency_score   = compatibility_prior(posture, mechanism)
      fluency_passed  = (fluency_score > FLUENCY_PROXY_FLOOR)
      epistemic_bonus = compute_epistemic_bonus(... fluency_passed)
      pragmatic_bid   = compute_pragmatic_bid(
                            posterior_edge=alternative.posterior_score,
                            posterior_variance=affinity_var,
                            supply_path)
      bid_value       = pragmatic_bid.bid_value + epistemic_bonus.bonus
      compatibility   = fluency_score (carried separately for the
                        mechanism_compatibility_score field)

    Soft-fail discipline: when bong_posterior is None or the variance
    extraction fails, slots that depend on BONG are left None; the
    fluency slot (posture-only) is still populated. Keeps the renderer
    honest — present what's available, leave absent what isn't.
    """
    # Fluency proxy — works without BONG.
    fluency = compatibility_prior(posture, alternative.mechanism)
    fluency_passed = fluency > FLUENCY_PROXY_FLOOR

    epistemic_bonus_value: Optional[float] = None
    bid_value_total: Optional[float] = None

    if bong_posterior is not None:
        try:
            epi_result = compute_epistemic_bonus(
                individual=bong_posterior,
                observation_precision=observation_precision,
                fluency_passed=fluency_passed,
                w_max=w_max,
                decay_scale=decay_scale,
                cohort_daily_budget=None,  # Loop-B blocker
            )
            epistemic_bonus_value = float(epi_result.bonus)
        except Exception as exc:  # noqa: BLE001
            logger.debug(
                "compose_alternative_bid_metadata: epistemic compute "
                "failed: %s", exc,
            )

        affinity_var = affinity_variance_for_mechanism(
            bong_posterior=bong_posterior,
            mechanism=alternative.mechanism,
        )
        if affinity_var is not None:
            try:
                kelly_result = compute_pragmatic_bid(
                    posterior_edge=float(alternative.posterior_score),
                    posterior_variance=affinity_var,
                    supply_path=supply_path,
                    kelly_fraction=kelly_fraction,
                )
                pragmatic = float(kelly_result.bid_value)
                # Dual-control sum (directive line 282).
                epi_addend = (
                    epistemic_bonus_value
                    if epistemic_bonus_value is not None
                    else 0.0
                )
                bid_value_total = pragmatic + epi_addend
            except Exception as exc:  # noqa: BLE001
                logger.debug(
                    "compose_alternative_bid_metadata: Kelly compute "
                    "failed: %s", exc,
                )

    return alternative.model_copy(
        update={
            "fluency_score": fluency,
            "mechanism_compatibility_score": fluency,
            "epistemic_bonus": epistemic_bonus_value,
            "bid_value": bid_value_total,
        }
    )


def compose_alternatives(
    alternatives: List[AlternativeCandidate],
    *,
    posture: str,
    bong_posterior: Any,
    supply_path: SupplyPath = DEFAULT_SUPPLY_PATH,
    observation_precision: float = DEFAULT_OBSERVATION_PRECISION,
    w_max: float = DEFAULT_W_MAX,
    decay_scale: float = DEFAULT_PRECISION_DECAY_SCALE,
    kelly_fraction: float = DEFAULT_KELLY_FRACTION_QUARTER,
) -> List[AlternativeCandidate]:
    """Bulk version — order preserved.

    Returns a NEW list; input alternatives are not mutated (Pydantic
    BaseModel.model_copy returns a fresh instance).
    """
    return [
        compose_alternative_bid_metadata(
            alt,
            posture=posture,
            bong_posterior=bong_posterior,
            supply_path=supply_path,
            observation_precision=observation_precision,
            w_max=w_max,
            decay_scale=decay_scale,
            kelly_fraction=kelly_fraction,
        )
        for alt in alternatives
    ]


def compose_chosen_bid_value(
    *,
    chosen_mechanism: str,
    chosen_score: float,
    posture: str,
    bong_posterior: Any,
    supply_path: SupplyPath = DEFAULT_SUPPLY_PATH,
    observation_precision: float = DEFAULT_OBSERVATION_PRECISION,
    w_max: float = DEFAULT_W_MAX,
    decay_scale: float = DEFAULT_PRECISION_DECAY_SCALE,
    kelly_fraction: float = DEFAULT_KELLY_FRACTION_QUARTER,
) -> Optional[float]:
    """Compose the trace-level ``bid_value`` for the chosen mechanism.

    Returns None when bong_posterior is None / variance unavailable
    (caller leaves DecisionTrace.bid_value at None and the renderer
    correctly omits it).
    """
    if bong_posterior is None:
        return None

    fluency = compatibility_prior(posture, chosen_mechanism)
    fluency_passed = fluency > FLUENCY_PROXY_FLOOR

    affinity_var = affinity_variance_for_mechanism(
        bong_posterior=bong_posterior,
        mechanism=chosen_mechanism,
    )
    if affinity_var is None:
        return None

    try:
        kelly_result = compute_pragmatic_bid(
            posterior_edge=float(chosen_score),
            posterior_variance=affinity_var,
            supply_path=supply_path,
            kelly_fraction=kelly_fraction,
        )
        pragmatic = float(kelly_result.bid_value)
    except Exception as exc:  # noqa: BLE001
        logger.debug(
            "compose_chosen_bid_value: Kelly compute failed: %s", exc,
        )
        return None

    try:
        epi_result = compute_epistemic_bonus(
            individual=bong_posterior,
            observation_precision=observation_precision,
            fluency_passed=fluency_passed,
            w_max=w_max,
            decay_scale=decay_scale,
            cohort_daily_budget=None,
        )
        epistemic = float(epi_result.bonus)
    except Exception as exc:  # noqa: BLE001
        logger.debug(
            "compose_chosen_bid_value: epistemic compute failed: %s", exc,
        )
        epistemic = 0.0

    return pragmatic + epistemic
