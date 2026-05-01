# =============================================================================
# Phase 3 — FDR control on δ_iac (closes directive line 988 + 1055)
# Location: adam/intelligence/iac_fdr_selection.py
# =============================================================================
"""FDR control on horseshoe δ_iac posterior — selects materially non-zero
interaction triples for use as ``pre_specified_interactions`` in the
next horseshoe fit.

Closes the named-successor slice from directive Phase 3 line 988 +
Phase 6 line 1055:

    line 988: "Knockoff-filter FDR control on which interactions
               are non-zero."
    line 1055: "Knockoff-filter FDR control wired."

WHY THIS EXISTS
---------------

The horseshoe substrate (4e02e5b) gives a continuous posterior on
δ_iac per (archetype, mechanism, category) interaction triple. The
horseshoe's own shrinkage already concentrates posterior mass on
zero for irrelevant interactions, but it's a SOFT selection — any
threshold on |posterior_mean| is arbitrary without an explicit
false-discovery framework.

This module is the explicit framework. It takes the IacPriorMoments
(shipped 71ee4ea) — per-triple (mean, variance) pairs from the
horseshoe posterior — computes z-statistics, and applies BH-style
FDR thresholding to select the triples that survive at the target
FDR rate.

DECISION-TIME CONSUMER
----------------------

The selected triples form the next nightly horseshoe fit's
``pre_specified_interactions`` list. The flow:

  nightly horseshoe fit (4e02e5b's build_hierarchical_model_with_interactions)
        ↓ posterior produces δ_iac per triple
  IacPriorMoments (71ee4ea's extract_iac_prior_from_inferencedata)
        ↓
  select_iac_via_fdr(moments, fdr_target=0.10)        ← THIS SLICE
        ↓ returns IacFDRSelectionResult.selected_triples
  next nightly fit's pre_specified_interactions list
        ↓
  pre_specified triples bypass horseshoe shrinkage with wider
  Normal(0, 1.0) priors — system's belief about which interactions
  exist iteratively tightens

Without FDR, the pre_specified_interactions list stays at whatever
Chris hand-authors per directive line 987 ("~10–15 interactions
Chris believes exist"). With FDR, the system learns which
interactions to pre-specify from data, with controlled false-
discovery rate.

ALGORITHM (BH-style on z-statistics)
-------------------------------------

For each triple (a, m, c) with posterior moments (μ_j, σ²_j):

    z_j = |μ_j| / sqrt(σ²_j)              (two-sided z-statistic)
    p_j = 2 * (1 - Φ(z_j))                (two-sided p-value)

Then Benjamini-Hochberg (1995) procedure with target rate q:

    Sort p-values ascending: p_(1) ≤ p_(2) ≤ ... ≤ p_(m)
    Find largest k such that p_(k) ≤ k * q / m
    Reject all H_(i) for i ≤ k → selected_triples

The BH procedure controls the False Discovery Rate at q under
independence + positive-regression-dependence (Benjamini-Yekutieli
2001). For horseshoe posteriors over interaction triples, the PRD
condition is reasonable since interactions on the same archetype
are positively correlated through the shared population posterior.

DISCIPLINE (B3-LUXY a/b/c/d)
----------------------------

(a) Citations:
    - Benjamini & Hochberg 1995 ("Controlling the False Discovery
      Rate"), the canonical BH procedure.
    - Benjamini & Yekutieli 2001 ("The Control of the False Discovery
      Rate in Multiple Testing under Dependency") for the PRD
      condition that justifies BH on positively-correlated tests.
    - Candès, Fan, Janson, Lv 2018 ("Panning for Gold: Model-X
      Knockoffs for High-Dimensional Controlled Variable Selection")
      — the directive's named target. Full model-X knockoff requires
      feature-construction + retraining, which is the sibling slice
      called out in honest tags below. The BH-on-z-statistics here
      is the v0.1 that respects FDR at q under the assumed
      dependence structure.

(b) Tests pin: BH threshold algorithm correctness on synthetic
    cases; FDR target respected on null + signal mix; empty moments
    → empty selection; strong signal triples are selected; weak
    signal not selected; pure-null sets produce few false discoveries
    in expectation; selection is deterministic for fixed input.

(c) calibration_pending=True. ``DEFAULT_FDR_TARGET=0.10`` matches
    the directive's implicit anchor (the directive doesn't quote a
    specific FDR target; 10% is the standard exploratory-analysis
    default). LUXY pilot data will calibrate. A14 flag:
    PHASE_3_IAC_FDR_TARGET_PILOT_PENDING.

(d) Honest tags — what is NOT in this slice (named successors):

    * Full model-X knockoff per Candès et al. 2018. The directive
      explicitly names "Knockoff-filter FDR control" — the true
      knockoff procedure constructs knockoff variables that mimic
      the X distribution but are conditionally independent of Y
      given X, then refits the model on [X, X̃] and uses the sign-
      flip threshold. This requires the design matrix + a knockoff
      generator (`knockpy` library or equivalent) + model retraining.
      This slice ships the BH-on-posterior-magnitudes substrate;
      the full knockoff is a sibling slice when the design-matrix
      interface ships.
    * Wiring into nightly horseshoe fit. The selection result's
      ``selected_triples`` is ready as a List[Tuple[str, str, str]]
      consumable by ``build_hierarchical_model_with_interactions``'s
      ``pre_specified_interactions`` parameter; the wiring slice
      that ties the FDR selector into the nightly Task 34 +
      hierarchical_bayes refit is its own slice.
    * Storey 2002 q-value extension (more powerful than BH at small
      effect counts). BH is the canonical default; Storey is a
      sibling refinement.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import List, Tuple

from adam.intelligence.iac_prior import IacPriorMoments, TripleKey

logger = logging.getLogger(__name__)


# A14 PHASE_3_IAC_FDR_TARGET_PILOT_PENDING
DEFAULT_FDR_TARGET: float = 0.10
"""Standard exploratory-analysis FDR rate. LUXY pilot data may inform
a tighter cut (0.05) once we have empirical posterior dispersion."""

# Numerical floor on posterior_sd to prevent z-statistic blow-up on
# pathologically tight posterior moments.
_MIN_POSTERIOR_SD: float = 1e-6

# Numerical floor on p-values so log/comparison operations don't
# trip on exact zero.
_MIN_P_VALUE: float = 1e-300


# =============================================================================
# Result type
# =============================================================================


@dataclass(frozen=True)
class IacFDRSelectionResult:
    """Outcome of one FDR selection over an IacPriorMoments.

    ``selected_triples``: list of (archetype, mechanism, category)
        triples that pass the FDR threshold, sorted lexicographically
        for deterministic downstream consumption.
    ``fdr_target``: the q used for selection.
    ``z_threshold``: the |z| value above which triples are selected.
    ``n_selected``: convenience cache of len(selected_triples).
    ``n_candidates``: total triples evaluated (size of input moments).
    ``z_scores_by_triple``: per-triple |z|-statistic for downstream
        diagnostics + dashboard surfaces.
    """

    selected_triples: List[TripleKey]
    fdr_target: float
    z_threshold: float
    n_selected: int
    n_candidates: int
    z_scores_by_triple: List[Tuple[TripleKey, float]] = field(
        default_factory=list,
    )


# =============================================================================
# z-statistic + p-value helpers
# =============================================================================


def _two_sided_z(mean: float, variance: float) -> float:
    """Compute |z| = |mean| / sqrt(variance) with numerical guards."""
    sd = math.sqrt(max(variance, 0.0))
    sd = max(sd, _MIN_POSTERIOR_SD)
    return abs(mean) / sd


def _two_sided_p_from_z(z: float) -> float:
    """Two-sided p-value from |z|: 2 * (1 - Φ(z))."""
    if not math.isfinite(z) or z < 0.0:
        return 1.0
    # Use erfc for numerical stability at large z:
    #   1 - Φ(z) = 0.5 * erfc(z / sqrt(2))
    p = math.erfc(z / math.sqrt(2.0))
    if p < _MIN_P_VALUE:
        p = _MIN_P_VALUE
    return p


# =============================================================================
# BH threshold finder
# =============================================================================


def _bh_threshold(p_values_sorted_asc: List[float], q: float) -> int:
    """Return k_max such that p_(k+1) ≤ (k+1) * q / m for k+1 ∈ [1, m].

    BH procedure: find the largest k where the kth-smallest p-value
    is below k * q / m. All hypotheses with p ≤ p_(k) are rejected.
    Returns the number of rejections (= k).
    """
    m = len(p_values_sorted_asc)
    if m == 0:
        return 0

    k_max = 0
    for i, p in enumerate(p_values_sorted_asc, start=1):
        # i-th smallest p (1-indexed) compared to threshold i * q / m
        threshold = i * q / m
        if p <= threshold:
            k_max = i
        # NOTE: we do NOT break early — BH threshold is the LARGEST i
        # for which the inequality holds, and the inequality can fail
        # then hold again later for a more powerful k.

    return k_max


# =============================================================================
# Selection
# =============================================================================


def select_iac_via_fdr(
    moments: IacPriorMoments,
    fdr_target: float = DEFAULT_FDR_TARGET,
) -> IacFDRSelectionResult:
    """Select δ_iac triples that survive FDR control at q = fdr_target.

    Args:
        moments: IacPriorMoments holding (mean, variance) per triple.
            From extract_iac_prior_from_inferencedata (71ee4ea).
        fdr_target: target FDR rate q ∈ (0, 1). Default 0.10.

    Returns: IacFDRSelectionResult with selected triples, threshold,
    and per-triple z-scores. Empty moments → empty selection (no
    error). FDR target outside (0, 1] → empty selection (defensive
    soft-fail).

    The procedure:
      1. For each triple (a, m, c): compute z = |μ| / σ, p = 2(1 - Φ(z))
      2. Sort p-values ascending
      3. BH threshold: largest k with p_(k) ≤ k * q / m
      4. Reject all H_(i) with i ≤ k → selected triples
      5. Determine z_threshold from the maximum selected p-value's
         corresponding z (for dashboard/diagnostic surface)

    Selected triples are returned sorted lexicographically so
    downstream consumers (next horseshoe fit's
    pre_specified_interactions) get deterministic ordering.
    """
    # Defensive guards
    if moments is None or moments.is_empty():
        return IacFDRSelectionResult(
            selected_triples=[],
            fdr_target=float(fdr_target),
            z_threshold=float("inf"),
            n_selected=0,
            n_candidates=0,
            z_scores_by_triple=[],
        )

    if not (0.0 < fdr_target <= 1.0):
        logger.debug(
            "select_iac_via_fdr: fdr_target=%s outside (0, 1] — empty selection",
            fdr_target,
        )
        return IacFDRSelectionResult(
            selected_triples=[],
            fdr_target=float(fdr_target),
            z_threshold=float("inf"),
            n_selected=0,
            n_candidates=moments.n_triples,
            z_scores_by_triple=[],
        )

    # Compute z-stats and p-values per triple
    triple_pvals: List[Tuple[TripleKey, float, float]] = []
    z_diagnostics: List[Tuple[TripleKey, float]] = []
    for triple, (mu, var) in moments.moments.items():
        z = _two_sided_z(mu, var)
        p = _two_sided_p_from_z(z)
        triple_pvals.append((triple, z, p))
        z_diagnostics.append((triple, z))

    # Sort by p ascending
    triple_pvals.sort(key=lambda x: x[2])

    # BH threshold
    sorted_pvals = [pv for (_, _, pv) in triple_pvals]
    k_reject = _bh_threshold(sorted_pvals, q=float(fdr_target))

    if k_reject == 0:
        return IacFDRSelectionResult(
            selected_triples=[],
            fdr_target=float(fdr_target),
            z_threshold=float("inf"),
            n_selected=0,
            n_candidates=moments.n_triples,
            z_scores_by_triple=sorted(z_diagnostics, key=lambda x: x[0]),
        )

    selected_with_z = [
        (triple, z) for (triple, z, _p) in triple_pvals[:k_reject]
    ]
    # Determine z_threshold: minimum |z| among selected
    z_threshold = min(z for (_, z) in selected_with_z)

    # Sort selected lexicographically for deterministic downstream
    selected_triples = sorted(
        triple for (triple, _) in selected_with_z
    )

    return IacFDRSelectionResult(
        selected_triples=selected_triples,
        fdr_target=float(fdr_target),
        z_threshold=float(z_threshold),
        n_selected=len(selected_triples),
        n_candidates=moments.n_triples,
        z_scores_by_triple=sorted(z_diagnostics, key=lambda x: x[0]),
    )


# =============================================================================
# Convenience helper for nightly fit wiring
# =============================================================================


def select_pre_specified_for_next_fit(
    moments: IacPriorMoments,
    fdr_target: float = DEFAULT_FDR_TARGET,
) -> List[TripleKey]:
    """Return just the selected triples for use as next fit's
    pre_specified_interactions argument.

    Thin convenience wrapper over select_iac_via_fdr. The full
    IacFDRSelectionResult carries z-statistics + diagnostic data
    for dashboard surfaces; this helper returns just the list shape
    that build_hierarchical_model_with_interactions consumes.
    """
    return select_iac_via_fdr(moments, fdr_target=fdr_target).selected_triples
