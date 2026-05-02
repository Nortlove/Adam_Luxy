# =============================================================================
# Step 10 — Carryover correction wired BEFORE selection
# Location: adam/intelligence/carryover_correction.py
# =============================================================================
"""Apply the directive's Step 10 carryover correction at decision time.

Closes the named sibling tag from Slice 3 (within_subject_eligibility
honest tag (d) lines 85-89): "Step 10 carryover correction term —
populates AlternativeCandidate.carryover_correction_term with
``ρ · effect(m_prev) · exp(-Δ/τ)``. Sibling slice composing with
this primitive."

Per directive Section 5.1 Step 10 (line 692):

    "Carryover correction (Spine #2): score → score − carryover_penalty."

And the canonical formula at directive lines 116-118 + 477:

    carryover_term_t = ρ_m1→m2 · effect(m1, t-Δ) · exp(-Δ / τ_m1)

Where:
  * ρ_m1→m2 is a learned mechanism-pair carryover coefficient.
  * effect(m1, t-Δ) is the prior touched mechanism's response value.
  * Δ is hours since the prior touch.
  * τ_m1 is the per-mechanism decay constant (directive line 111
    names hours-scale: 3-8h half-life for state primes / arousal).

WHY THIS EXISTS

Without Step 10, the cascade's per-user posterior treats sequential
within-subject touches as if they were independent. The directive
(Spine #2 lines 99-101) is explicit: "behavioral non-pharmaceutical
carryover is real and confounds within-subject inference unless it
is either washed out or modeled. Without this primitive, the per-
user posteriors from Spine #1 are biased and the within-subject
contrasts (the partner-facing demonstrable claim) are artifacts of
order, not effect."

Slice 3 wired the WASHOUT side (eligibility filter dropping mechanisms
inside their washout window). This slice closes the MODELED side:
even within an admissible window, the residual carryover effect is
subtracted from the candidate's score so the selection isn't
double-counting predicted response that was already going to happen.

THE PRIMITIVE

  * ``compute_carryover_penalty(*, candidate_mechanism,
    last_touched_mechanism, hours_since_last_touch, rho, effect_prev,
    tau)`` — returns the per-candidate penalty (the value the cascade
    SUBTRACTS from the score per directive Step 10 line 692). When
    candidate ≠ last_touched_mechanism, returns 0 in v0.1 (single-ρ
    approximation; see honest tag (d)).

  * ``apply_carryover_correction(mechanism_scores,
    last_touched_mechanism, hours_since_last_touch, rho, effect_prev,
    tau)`` — the wire-point primitive. Builds per-mechanism penalty
    dict, returns ``CarryoverCorrectionResult`` with modulated_scores
    (score - penalty, floored at 0) + per_mechanism_penalty +
    n_corrected.

DISCIPLINE (B3-LUXY a/b/c/d)
----------------------------

(a) Citations: directive Section 5.1 Step 10 (line 692) +
    Spine #2 carryover formula (lines 116-118 + 477) +
    within_subject_eligibility honest tag (d) (lines 85-89). ρ
    sourced from ``UserPosteriorProfile.within_user_correlation``
    (single per-user AR(1), populated by Task 36 nightly HMC
    reconcile per ``user_posterior_hmc_reconcile.py:608``).
    effect(m_prev) sourced from
    ``UserPosteriorProfile.mechanism_posteriors[m_prev].mean``
    (Beta posterior mean ∈ [0, 1]).
    τ sourced from ``washout_hours_for(m_prev)`` (closest existing
    per-mechanism time-scale primitive).

(b) Tests pin: candidate ≠ last_touched_mechanism → penalty 0
    (single-ρ approximation); ρ=0 → penalty 0 (no signal); Δ=0 +
    τ>0 → penalty = ρ × effect (no decay); Δ→∞ → penalty → 0
    (decay exhausts); negative ρ → negative penalty → score INCREASE
    (rare; reflects interference rather than priming);
    score floor preserved (no score < 0); empty mechanism_scores →
    pass-through; missing tau (≤0) → no decay applied (penalty
    saturates); pure formula round-trip; CarryoverCorrectionResult
    frozen.

(c) calibration_pending=True. v0.1 uses single per-user ρ (the
    canonical pair-indexed ρ_m1→m2 is honest-tag sibling). LUXY
    pilot data via Task 36 + the per-mechanism response-curve
    estimator will calibrate. A14 flag:
    PHASE_2_CARRYOVER_PAIR_RHO_PILOT_PENDING.

(d) Honest tags — what is NOT in this slice (named successors):

    * Pair-indexed ``ρ_m1→m2`` per directive lines 117-118
      ("learned mechanism-pair carryover coefficient (positive =
      priming, negative = interference); priors come from offline
      mechanism-pair semantic-similarity"). v0.1 uses
      ``within_user_correlation`` (single ρ per user) → cross-
      mechanism penalty is 0 (no claim made). Pair-indexed sibling
      will activate cross-mechanism corrections. Same sibling named
      in within_subject_eligibility.py:97-100.
    * effect(m_prev) using the directive's "effect(m1, t-Δ)"
      formulation — v0.1 reads ``mechanism_posteriors[m_prev].mean``
      (current Beta posterior mean ∈ [0, 1]). The directive's
      time-conditional ``effect(m, t-Δ)`` reads the historical
      response at the time of the touch; sibling slice replaces
      with the trajectory-evaluated response.
    * τ per-mechanism calibration against directive line 111
      ("State primes: 3-8h half-life for arousal carryover"). v0.1
      uses ``washout_hours_for(m_prev)`` — same per-mechanism
      time-scale as the eligibility filter. Pilot calibration via
      LUXY response curves replaces.
    * Chosen-mechanism carryover decomposition on the trace top-
      level (directive line 242: "chain_of_reasoning … KL term,
      pragmatic term, fluency, compatibility, carryover, epistemic
      contribution percentage"). This slice populates per-alternative
      ``carryover_correction_term``; the chosen-side score-component
      decomposition is sibling slice via
      ``decompose_score_components`` helper.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Dict, Optional

logger = logging.getLogger(__name__)


# A14 PHASE_2_CARRYOVER_PAIR_RHO_PILOT_PENDING
#
# v0.1 uses single per-user ρ (UserPosteriorProfile.within_user_correlation).
# Cross-mechanism penalty is 0 — pair-indexed ρ_m1→m2 is sibling slice.

# Score floor — Step 10 subtracts a penalty; we floor at 0 to keep
# scores in [0, ∞). Existing modulation primitives (posture_modulation,
# per_user_posterior_modulation, score_space_epistemic) all use this
# convention.
SCORE_FLOOR: float = 0.0


@dataclass(frozen=True)
class CarryoverCorrectionResult:
    """Outcome of running the Step 10 carryover correction.

    ``modulated_scores``: per-mechanism scores after the carryover
        penalty is subtracted (floored at SCORE_FLOOR). When penalty
        is identically zero across all mechanisms (e.g., no last-
        touched, ρ=0, missing user posterior), equals the input
        mechanism_scores unchanged.
    ``per_mechanism_penalty``: ``{mechanism: penalty_value}`` for the
        diagnostic + trace-population side. Cross-mechanism candidates
        carry 0.0 in v0.1 (single-ρ approximation). Empty when no
        correction was applied.
    ``n_corrected``: count of mechanisms whose score was shifted by
        more than numerical noise (1e-9 tolerance).
    ``rho``: the ρ value used (echoed for diagnostics).
    """

    modulated_scores: Dict[str, float]
    per_mechanism_penalty: Dict[str, float] = field(default_factory=dict)
    n_corrected: int = 0
    rho: float = 0.0


def compute_carryover_penalty(
    *,
    candidate_mechanism: str,
    last_touched_mechanism: Optional[str],
    hours_since_last_touch: Optional[float],
    rho: float,
    effect_prev: float,
    tau: float,
) -> float:
    """Compute the directive's Step 10 carryover penalty for one candidate.

    Per directive lines 116-118 + 477:

        carryover_term = ρ · effect(m_prev) · exp(-Δ / τ)

    v0.1 single-ρ approximation: when candidate ≠ last_touched_mechanism,
    returns 0 (no claim about cross-mechanism carryover until pair-
    indexed ρ_m1→m2 sibling ships).

    Args:
        candidate_mechanism: the mechanism being scored.
        last_touched_mechanism: the user's most-recently-touched
            mechanism (None means cold buyer / no prior touch).
        hours_since_last_touch: Δ in hours. None / negative → 0
            (treated as immediately post-touch).
        rho: AR(1) coefficient ∈ [-1, 1]. The user's
            ``within_user_correlation``. ρ=0 → no correction.
        effect_prev: the response value at the prior touch. v0.1
            uses ``mechanism_posteriors[m_prev].mean`` ∈ [0, 1].
            Pass 0.5 (uninformative) when no posterior available.
        tau: time-decay constant in hours. Should be > 0; tau ≤ 0
            disables decay (penalty saturates).

    Returns:
        The penalty value (positive = subtract from score). Exact
        zero in the cross-mechanism / cold-buyer / ρ=0 cases.
    """
    if not candidate_mechanism or not last_touched_mechanism:
        return 0.0
    if candidate_mechanism != last_touched_mechanism:
        # v0.1 single-ρ approximation — no cross-mechanism claim.
        return 0.0
    if rho == 0.0:
        return 0.0

    delta_h = max(0.0, float(hours_since_last_touch or 0.0))

    if tau is None or tau <= 0.0:
        # No decay applied — penalty is the full ρ · effect product.
        decay = 1.0
    else:
        decay = math.exp(-delta_h / float(tau))

    return float(rho) * float(effect_prev) * decay


def apply_carryover_correction(
    mechanism_scores: Dict[str, float],
    *,
    last_touched_mechanism: Optional[str],
    hours_since_last_touch: Optional[float],
    rho: float,
    effect_prev_for_last_touched: float,
    tau: float,
) -> CarryoverCorrectionResult:
    """Apply the Step 10 score modulation per directive line 692.

    Args:
        mechanism_scores: candidate scores from cascade through Step 9
            (post-eligibility, post-free-energy, post-epistemic).
        last_touched_mechanism: prior touch mechanism (None → no
            correction).
        hours_since_last_touch: Δ in hours.
        rho: AR(1) coefficient (UserPosteriorProfile.within_user_correlation).
        effect_prev_for_last_touched: response value at prior touch
            (mechanism_posteriors[m_prev].mean). 0.5 when no posterior.
        tau: per-mechanism decay constant (hours).

    Returns:
        CarryoverCorrectionResult. The cascade reads modulated_scores
        and uses it as the new mechanism_scores going into selection.
        per_mechanism_penalty is threaded into build_trace_from_cascade
        so AlternativeCandidate.carryover_correction_term reflects the
        actual values used at decision time.

    Behavior:
      * Empty mechanism_scores → empty result.
      * No last_touched_mechanism → pass-through (no correction).
      * ρ=0 → pass-through (no signal).
      * Cross-mechanism penalty is 0 in v0.1 (single-ρ approximation);
        per_mechanism_penalty[other] entries are 0.0 (recorded so the
        trace shows the correction was attempted but no cross-mechanism
        claim was made).
      * Score floor [0, ∞) preserved.
    """
    if not mechanism_scores:
        return CarryoverCorrectionResult(
            modulated_scores={}, per_mechanism_penalty={}, n_corrected=0,
            rho=float(rho),
        )

    if not last_touched_mechanism or rho == 0.0:
        # Pass-through — surface every mechanism as 0 penalty so the
        # trace honestly reflects "no carryover signal" vs "uncomputed".
        return CarryoverCorrectionResult(
            modulated_scores=dict(mechanism_scores),
            per_mechanism_penalty={m: 0.0 for m in mechanism_scores},
            n_corrected=0,
            rho=float(rho),
        )

    modulated: Dict[str, float] = {}
    penalties: Dict[str, float] = {}
    n_shifted = 0

    for mech, score in mechanism_scores.items():
        try:
            base_score = float(score)
        except (TypeError, ValueError):
            modulated[mech] = score
            penalties[mech] = 0.0
            continue

        penalty = compute_carryover_penalty(
            candidate_mechanism=mech,
            last_touched_mechanism=last_touched_mechanism,
            hours_since_last_touch=hours_since_last_touch,
            rho=rho,
            effect_prev=effect_prev_for_last_touched,
            tau=tau,
        )
        penalties[mech] = penalty

        # Step 10 (directive line 692): score → score − carryover_penalty.
        new_score = base_score - penalty
        if new_score < SCORE_FLOOR:
            new_score = SCORE_FLOOR
        modulated[mech] = new_score

        if abs(new_score - base_score) > 1e-9:
            n_shifted += 1

    return CarryoverCorrectionResult(
        modulated_scores=modulated,
        per_mechanism_penalty=penalties,
        n_corrected=n_shifted,
        rho=float(rho),
    )
