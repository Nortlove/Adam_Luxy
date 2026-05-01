# =============================================================================
# Spine #6 — Confidence-snapshot helper (DR-renderer Layer 4 closure)
# Location: adam/intelligence/confidence_snapshot.py
# =============================================================================
"""90% credible interval over the per-user effect of a chosen mechanism.

Closes the DefensiveReasoningRender's ``confidence.status="not_available"``
gap (``defensive_reasoning_renderer.py:_render_confidence`` lines 246-276):
the renderer looks for ``ci_lower_90`` / ``ci_upper_90`` / ``point_estimate``
keys on ``DecisionTrace.user_posterior_snapshot``; until this slice no
producer populated them. Per directive line 858:

    "Confidence. 90% credible interval on the per-user effect of the
     chosen mechanism, with the cohort-pooled estimate alongside."

This module is the canonical producer for those three keys. It composes
existing primitives only — ``BONGUpdater.get_mean`` /
``get_per_dimension_variance`` for the per-user posterior, and
``per_user_posterior_modulation.MECHANISM_DIMENSION_MAP`` for the
cohort-side dimension reduction. No new substrate.

WHY THIS EXISTS
---------------

The directive's "per-user effect of the chosen mechanism" is the average
posterior alignment across the mechanism's primary cohort-side dimensions
(e.g., ``regulatory_focus`` → ``["regulatory_fit"]``;
``temporal_construal`` → ``["construal_fit", "temporal_discounting"]``).
The personal_affinity that ``per_user_posterior_modulation._shrink_scores``
already uses for the score modulation is the same scalar — this slice
extends it with a 90% credible interval so the renderer can report the
posterior with appropriate humility.

CANONICAL FORMULA
-----------------

For a mechanism with primary dimensions ``d_1, …, d_n`` and per-dimension
posterior marginal distributions ``alignment[d_i] ~ N(μ_i, σ_i²)`` (the
diagonal Gaussian approximation that BONG already uses for
get_per_dimension_variance):

    point_estimate = (1/n) · Σ μ_i               (per-mechanism affinity)
    var(affinity)  = (1/n²) · Σ σ_i²              (independence assumption)
    σ              = sqrt(var(affinity))
    ci_lower_90    = point_estimate − z_{0.95} · σ
    ci_upper_90    = point_estimate + z_{0.95} · σ
    z_{0.95}       = 1.6448536269514722  (scipy.stats.norm.ppf(0.95))

The independence assumption matches the diagonal approximation used
by BONG.get_per_dimension_variance (bong.py:319-325). Full Woodbury-
corrected variance is a sibling slice; this slice keeps the
approximation consistent with what every other consumer of BONG
variance already uses.

DECISION-TIME CONSUMER
----------------------

  cascade.run_bilateral_cascade
      ↓ (build_trace_from_cascade, this slice merges snapshot)
  DecisionTrace.user_posterior_snapshot.{ci_lower_90, ci_upper_90,
                                         point_estimate}
      ↓ (Spine #6 emit, drain to Redis + Neo4j)
  DefensiveReasoningRender.confidence.status="available"
      ↓
  LUXY CMO + Becca see the 90% CI in the partner-facing render.

DISCIPLINE (B3-LUXY a/b/c/d)
----------------------------

(a) Citation: directive line 858 ("Confidence. 90% credible interval
    on the per-user effect of the chosen mechanism…"); standard
    Gaussian quantile z_{0.95} = 1.6448536269514722; BONG's diagonal
    variance approximation (bong.py:319-325 ``get_per_dimension_variance``).

(b) Tests pin: empty / missing buyer-profile → empty snapshot dict;
    profile without bong_posterior → empty snapshot; mechanism
    not in MECHANISM_DIMENSION_MAP → empty snapshot; canonical CI
    width matches 2 · z_{0.95} · σ; multi-dim mechanism uses the
    affinity-mean formula; symmetric CI around point_estimate;
    ci_lower_90 < point_estimate < ci_upper_90 strict ordering.

(c) calibration_pending=False — the formula is closed-form Gaussian.
    The cohort_pooled_estimate field is intentionally NOT populated
    here (Spine #7 cohort discovery is BLOCKED on Loop B per session
    handoff). Honest tag: when cohorts ship, a sibling slice adds
    cohort_pooled_estimate alongside the per-user CI.

(d) Honest tags — what is NOT in this slice (named successors):

    * Cohort-pooled estimate (BLOCKED on Loop B — Spine #7 cohort
      discovery substrate ships independently).
    * Full Woodbury-corrected variance (sibling — composes BONG.U
      structure into the variance reduction).
    * BONG-side primary-dimension mapping. This slice reuses
      ``per_user_posterior_modulation.MECHANISM_DIMENSION_MAP`` (the
      cohort-side vocabulary) and translates BONG dim names via the
      same ``BONG_TO_COHORT_DIM`` table that the modulator uses.
      Single source of truth — no duplication.
    * Mechanism aliases. The map covers 18 mechanisms named by the
      MechanismActivation atom (Doc 3 §III). When a chosen mechanism
      is outside the map, the helper returns an empty dict and the
      renderer correctly falls back to status="not_available".
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from adam.intelligence.per_user_posterior_modulation import (
    BONG_TO_COHORT_DIM,
    MECHANISM_DIMENSION_MAP,
)

logger = logging.getLogger(__name__)


# Standard normal 95th percentile (two-sided 90% CI half-width factor).
# z = scipy.stats.norm.ppf(0.95). Pinned numerically to avoid scipy
# dependency at import time — tests verify equivalence to scipy if
# available.
Z_QUANTILE_95: float = 1.6448536269514722

# Lower bound on per-dimension variance to prevent zero-width CI under
# numerically degenerate posteriors. Matches MIN_PRECISION discipline
# in bong.py (bong.py:73).
_MIN_VAR: float = 1e-9


def compute_confidence_snapshot(
    *,
    buyer_id: str,
    graph_cache: Any,
    chosen_mechanism: str,
    ci_level: float = 0.90,
) -> Dict[str, float]:
    """Compute 90% CI snapshot keys for the chosen mechanism's per-user effect.

    Returns a dict with keys ``point_estimate`` / ``ci_lower_90`` /
    ``ci_upper_90`` populated when a BONG posterior is available for
    this buyer AND the chosen mechanism is in the canonical dimension
    map. Returns ``{}`` (empty dict) on any of:

      * buyer_id empty / graph_cache missing / no get_buyer_profile
      * profile is None / has no bong_posterior
      * BONG updater not initialized (initialize_default never ran)
      * chosen_mechanism not in MECHANISM_DIMENSION_MAP
      * none of the mechanism's primary dimensions resolved to BONG dims

    The renderer (defensive_reasoning_renderer._render_confidence) treats
    an empty / partial dict as ``status="not_available"`` — this contract
    is the reason the helper returns empty dict rather than raising.

    Args:
        buyer_id: StackAdapt postback id / sapid round-trip id.
        graph_cache: GraphIntelligenceCache (or compatible) exposing
            ``get_buyer_profile(buyer_id) -> profile`` with
            ``profile.bong_posterior`` (a BONGPosterior).
        chosen_mechanism: Mechanism name (one of the keys of
            MECHANISM_DIMENSION_MAP); directive line 858's "chosen
            mechanism" of the decision.
        ci_level: 0 < ci_level < 1. Pilot uses 0.90 per directive
            line 858. Tests parameterize alternate levels; the
            keys stay ``ci_lower_90`` / ``ci_upper_90`` for renderer
            compatibility regardless of level (the level is encoded
            in the renderer's ``ConfidenceLayer.ci_level`` field).

    Returns:
        ``{point_estimate, ci_lower_90, ci_upper_90}`` or ``{}``.
        ``cohort_pooled_estimate`` is intentionally absent until
        Spine #7 cohort discovery ships.
    """
    if not buyer_id or graph_cache is None or not chosen_mechanism:
        return {}

    primary_dims = MECHANISM_DIMENSION_MAP.get(chosen_mechanism)
    if not primary_dims:
        return {}

    if not hasattr(graph_cache, "get_buyer_profile"):
        return {}

    try:
        profile = graph_cache.get_buyer_profile(buyer_id=buyer_id)
    except Exception as exc:  # noqa: BLE001 — soft-fail by design
        logger.debug(
            "compute_confidence_snapshot: get_buyer_profile failed: %s", exc,
        )
        return {}

    if profile is None:
        return {}

    bong_post = getattr(profile, "bong_posterior", None)
    if bong_post is None:
        return {}

    return _snapshot_from_bong(
        bong_posterior=bong_post,
        primary_dims=primary_dims,
        ci_level=ci_level,
    )


def _snapshot_from_bong(
    *,
    bong_posterior: Any,
    primary_dims: list,
    ci_level: float,
) -> Dict[str, float]:
    """Pure inner helper — extracted for direct unit-test ergonomics."""
    try:
        from adam.intelligence.bong import get_bong_updater
    except Exception:
        return {}

    try:
        updater = get_bong_updater()
        if updater.prior_eta is None:
            return {}
        mean_vec = updater.get_mean(bong_posterior)
        var_vec = updater.get_per_dimension_variance(bong_posterior)
    except Exception as exc:  # noqa: BLE001
        logger.debug(
            "compute_confidence_snapshot: BONG read failed: %s", exc,
        )
        return {}

    primary_set = set(primary_dims)
    means: list = []
    vars_: list = []
    for i, bong_dim in enumerate(updater.dimension_names):
        if i >= len(mean_vec):
            break
        cohort_dim = BONG_TO_COHORT_DIM.get(bong_dim, bong_dim)
        if cohort_dim not in primary_set:
            continue
        try:
            means.append(float(mean_vec[i]))
            vars_.append(max(_MIN_VAR, float(var_vec[i])))
        except (TypeError, ValueError):
            continue

    if not means:
        return {}

    n = len(means)
    point_estimate = sum(means) / n
    affinity_var = sum(vars_) / (n * n)  # var of mean under independence
    sigma = affinity_var ** 0.5

    z = _z_quantile(ci_level)
    half_width = z * sigma
    return {
        "point_estimate": point_estimate,
        "ci_lower_90": point_estimate - half_width,
        "ci_upper_90": point_estimate + half_width,
    }


def _z_quantile(ci_level: float) -> float:
    """Two-sided z-quantile for a (1-α) CI.

    Pinned numerically for ci_level=0.90 to avoid scipy at import
    time; falls back to scipy when present for non-pilot levels.
    """
    if abs(ci_level - 0.90) < 1e-9:
        return Z_QUANTILE_95

    try:
        from scipy.stats import norm  # type: ignore
        return float(norm.ppf((1.0 + ci_level) / 2.0))
    except Exception:
        # Without scipy and with a non-canonical level, fall back to
        # 0.90 quantile rather than failing the snapshot. Caller
        # passes ci_level=0.90 in the pilot; non-pilot levels are
        # tested against the scipy-installed environment.
        return Z_QUANTILE_95
