# =============================================================================
# Within-subject eligibility filter — Spine #2 decision-time gate
# Location: adam/intelligence/within_subject_eligibility.py
# =============================================================================
"""Hard washout-respecting eligibility filter at decision time.

Closes audit Tier 1 #3: ``adam/retargeting/scheduler.py`` (415 lines)
ships ABAB / RAR / SMART design generators + the
``washout_hours_for(mechanism)`` table, but no caller in
``run_bilateral_cascade`` invokes any of it. Steps 4 (schedule check)
and 10 (carryover correction) of the directive's 14-step pipeline
were entirely absent from the decision flow. The directive (line 122)
makes the role explicit:

    "the scheduler is the only object allowed to determine which
     mechanism is eligible for a given user at a given moment.
     The bilateral cascade (Spine #4) and the active-inference free-
     energy scorer (Spine #5) operate only over the eligibility-
     filtered candidate set."

WHY THIS EXISTS
---------------

This module is the decision-time eligibility primitive. It composes
``washout_hours_for(mechanism)`` from the existing scheduler with
a per-buyer touch history to drop candidates whose mechanism washout
floor has not elapsed. Output: the eligible candidate set the
cascade must score over.

Foundation rule 11 (the fitness function IS the ethics) angle: the
washout floor is non-overrideable per scheduler.py:36-39. Even RAR
(adaptive randomization that wants to reweight by reward) cannot
deploy a touch inside the washout window of the prior mechanism for
that user — protects the reactance-prone user from compounding
multiplicative reactance (Wicklund hydraulic model). This filter is
the architectural enforcement of that floor at decision time.

THE PRIMITIVE
-------------

  * ``EligibilityResult`` — frozen dataclass: filtered_scores,
    n_dropped, dropped_mechanisms, n_eligible, all_dropped, bypassed.
  * ``passes_washout(mechanism, hours_since_last_touch, washout_hours)``
    — single-pair gate. None/missing last-touch → eligible (no history
    means no washout violation possible).
  * ``apply_within_subject_eligibility(mechanism_scores,
    user_touch_history, fail_open_on_all_drop)`` — bulk filter.
    Returns EligibilityResult.

ALL-DROP SEMANTIC (v0.1)
------------------------

If every candidate's washout has not elapsed, the directive (line
122) authorizes refusing all bids ("the scheduler is permitted to
refuse all mechanisms when no compatible context exists"). For v0.1
we soft-fail open and emit a counter + log warning instead of
dropping the bid path — same discipline as Slice 1 (mechanism
fluency floor). The hard refuse-all-bid semantic is named as a
sibling slice; the counter surfaces production firing of this case.

DISCIPLINE (B3-LUXY a/b/c/d)
----------------------------

(a) Citations: directive line 122 (scheduler is the only eligibility
    authority); directive Section 5.1 Step 4 line 686 (within-subject
    schedule check); directive Spine #2 lines 98-124 (washout
    intervals); existing
    ``adam/retargeting/scheduler.washout_hours_for`` (Spine #2
    substrate); audit 2026-05-01 Tier 1 #3.

(b) Tests pin: candidate inside washout dropped; candidate past
    washout kept; no history (cold buyer) → all kept; all-drop
    bypass with WARN; threshold parameterizable per-mechanism via
    washout_hours_for; counters consistent with the diff;
    EligibilityResult frozen.

(c) calibration_pending=True. Default washout multiplier 3× t½
    inherited from scheduler.WASHOUT_HALF_LIFE_MULTIPLIER. LUXY
    pilot data via the per-user response-curve estimator will
    calibrate. A14 flag inherited:
    SCHEDULER_WASHOUT_MULTIPLIER_PILOT_PENDING.

(d) Honest tags — what is NOT in this slice (named successors):

    * Step 10 carryover correction term (directive Section 5.1
      line 692). Same per-buyer touch-history dependency; populates
      ``AlternativeCandidate.carryover_correction_term`` with
      ``ρ · effect(m_prev) · exp(-Δ/τ)``. Sibling slice composing
      with this primitive.
    * Refuse-all-bid hard semantic — SHIPPED in Slice 13
      (2026-05-02 handoff). The cascade's eligibility-block all-drop
      branch now sets ``CreativeIntelligence.refused=True`` +
      ``refusal_reason="within_subject_washout_all_dropped"`` +
      clears mechanism_scores. The service detects refused=True and
      returns a no-bid response shape (no decision persistence).
      Same flip applied to Slice 1's fluency-floor all-drop branch.
    * Persistent (Redis) per-mechanism touch history. v0.1 reads
      from the in-process ``decision_cache`` which is sufficient
      for single-pod Railway deploy. Multi-pod replication via
      Redis is a sibling slice.
    * Mechanism-pair carryover coefficients ρ_m1→m2 (directive
      line 117-118). The current AR(1) carryover lives in
      hierarchical Bayes nightly reconcile (single ρ per user).
      Pair-indexed coefficients are a sibling slice.
    * Cross-mechanism transition (e.g., A→B): we use the MAX of
      the two mechanism washouts per scheduler.washout_hours_between
      semantics — but at the eligibility filter we only have the
      candidate side. We use ``washout_hours_for(candidate)`` AND
      ``washout_hours_for(last_touched_mechanism)`` and take MAX
      per-pair when the user's last touch is a different mechanism.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from adam.retargeting.scheduler import washout_hours_for

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class EligibilityResult:
    """Outcome of running the within-subject eligibility filter.

    ``filtered_scores``: eligible scores. When ``bypassed=True``,
        equals the input mechanism_scores (no drops applied — same
        contract as ``MechanismFluencyResult``).
    ``n_dropped``: count of mechanisms whose washout had not elapsed.
    ``dropped_mechanisms``: ordered list of dropped mechanism names.
    ``n_eligible``: count of mechanisms remaining after the filter.
    ``all_dropped``: True iff every candidate was inside its washout
        window. Slice 3 sibling will treat this as "refuse all bids";
        for v0.1 we fail-open with bypassed=True.
    ``bypassed``: True when the all-drop case fired and the input
        was returned unchanged.
    ``drop_reasons``: per-dropped-mechanism human-readable reason
        for diagnostics + dashboard surfaces.
    """

    filtered_scores: Dict[str, float]
    n_dropped: int
    dropped_mechanisms: List[str] = field(default_factory=list)
    n_eligible: int = 0
    all_dropped: bool = False
    bypassed: bool = False
    drop_reasons: Dict[str, str] = field(default_factory=dict)


def passes_washout(
    mechanism: str,
    hours_since_last_touch: Optional[float],
    *,
    washout_hours: Optional[float] = None,
    last_touched_mechanism: Optional[str] = None,
) -> bool:
    """Return True iff the mechanism is eligible at this moment.

    Args:
        mechanism: candidate mechanism name.
        hours_since_last_touch: hours since the user's most recent
            touch ON this mechanism (or last_touched_mechanism, see
            below). None / missing → True (no history means we cannot
            certify an in-flight washout violation).
        washout_hours: optional override of the per-mechanism washout
            floor. Defaults to ``washout_hours_for(mechanism)``.
        last_touched_mechanism: when the prior touch was a DIFFERENT
            mechanism, the cross-mechanism transition takes the MAX
            of both washouts (per ``washout_hours_between``
            semantics). Default None means same-mechanism semantics.

    Same-mechanism: hours_since_last_touch >= washout_hours_for(mech).
    Cross-mechanism: hours_since_last_touch >= max(
        washout_hours_for(mech), washout_hours_for(last_touched_mechanism))
    """
    if hours_since_last_touch is None:
        return True

    if washout_hours is None:
        # Slice 24: dispatch via v3_interfaces.WashoutModel registry.
        # Default impl delegates to washout_hours_for (Slice 3 substrate);
        # v3 1.F will register a PK/PD model whose min_wait_hours is
        # derived from a continuous Hill curve over residual effect.
        try:
            from adam.intelligence.v3_interfaces import (
                get_active_washout_model,
            )
            _wm = get_active_washout_model()
            floor = _wm.min_wait_hours(mechanism)
            if last_touched_mechanism and last_touched_mechanism != mechanism:
                floor = max(
                    floor, _wm.min_wait_hours(last_touched_mechanism),
                )
        except Exception:
            # Soft-fail to direct call — registry is optional substrate
            # for v3 wrapping; bid path must NEVER block on lookup.
            floor = washout_hours_for(mechanism)
            if last_touched_mechanism and last_touched_mechanism != mechanism:
                floor = max(floor, washout_hours_for(last_touched_mechanism))
    else:
        floor = washout_hours

    return hours_since_last_touch >= floor


def apply_within_subject_eligibility(
    mechanism_scores: Dict[str, float],
    user_touch_history: Optional[Dict[str, float]],
    *,
    last_touched_mechanism: Optional[str] = None,
) -> EligibilityResult:
    """Drop mechanisms whose washout floor has not elapsed for this user.

    Args:
        mechanism_scores: cascade-produced scores per candidate.
        user_touch_history: ``Dict[mechanism, hours_since_last_touch]``.
            None → cold buyer (no history) → all eligible. Empty dict
            also treated as no-signal pass-through.
        last_touched_mechanism: most recent mechanism the user was
            touched with (across all mechanisms). Used to compute
            cross-mechanism MAX-washout for candidates that DIFFER
            from the most recent touch. None → same-mechanism
            semantics throughout.

    Returns:
        ``EligibilityResult``. The cascade reads ``filtered_scores``
        and uses it as the new mechanism_scores going into selection.
        ``n_dropped`` and ``all_dropped`` feed Prometheus counters.

    Behavior:
      * Empty mechanism_scores → empty result, no drops.
      * No user_touch_history (cold buyer) → pass-through.
      * Some candidates inside washout → drop them; return filtered.
      * ALL candidates inside washout → bypass + warn (Slice 3 sibling
        will hard-refuse the bid).
    """
    if not mechanism_scores:
        return EligibilityResult(
            filtered_scores=mechanism_scores,
            n_dropped=0,
            dropped_mechanisms=[],
            n_eligible=0,
            all_dropped=False,
            bypassed=False,
        )

    if not user_touch_history:
        # Cold buyer or no signal — all candidates eligible.
        return EligibilityResult(
            filtered_scores=mechanism_scores,
            n_dropped=0,
            dropped_mechanisms=[],
            n_eligible=len(mechanism_scores),
            all_dropped=False,
            bypassed=False,
        )

    eligible: Dict[str, float] = {}
    dropped: List[str] = []
    drop_reasons: Dict[str, str] = {}

    for mech, score in mechanism_scores.items():
        # Per-mechanism last-touch — None when this user has never
        # been touched with THIS specific mechanism.
        same_mech_age = user_touch_history.get(mech)
        # Cross-mechanism check: if the user's most recent touch was
        # a DIFFERENT mechanism, that mechanism's washout also gates
        # this candidate.
        cross_mech_age: Optional[float] = None
        if (
            last_touched_mechanism
            and last_touched_mechanism != mech
            and last_touched_mechanism in user_touch_history
        ):
            cross_mech_age = user_touch_history[last_touched_mechanism]

        # Same-mechanism gate
        same_floor = washout_hours_for(mech)
        same_ok = same_mech_age is None or same_mech_age >= same_floor

        # Cross-mechanism gate
        cross_floor = (
            washout_hours_for(last_touched_mechanism)
            if last_touched_mechanism else 0.0
        )
        cross_ok = cross_mech_age is None or cross_mech_age >= cross_floor

        if same_ok and cross_ok:
            eligible[mech] = score
        else:
            dropped.append(mech)
            if not same_ok:
                drop_reasons[mech] = (
                    f"same-mechanism washout: "
                    f"{same_mech_age:.1f}h since last touch < "
                    f"{same_floor:.1f}h floor"
                )
            else:
                drop_reasons[mech] = (
                    f"cross-mechanism washout from "
                    f"{last_touched_mechanism}: "
                    f"{cross_mech_age:.1f}h < {cross_floor:.1f}h floor"
                )

    n_dropped = len(dropped)
    n_input = len(mechanism_scores)
    all_dropped = n_dropped == n_input and n_input > 0

    if all_dropped:
        # v0.1 fail-open + counter + WARN. Sibling slice will replace
        # with refuse-all-bid per directive line 122.
        logger.warning(
            "within_subject_eligibility: all %d candidates inside "
            "washout window for last_touched=%s — bypassing filter "
            "(refuse-all-bid sibling slice awaits)",
            n_input,
            last_touched_mechanism,
        )
        return EligibilityResult(
            filtered_scores=mechanism_scores,
            n_dropped=n_dropped,
            dropped_mechanisms=dropped,
            n_eligible=n_input,
            all_dropped=True,
            bypassed=True,
            drop_reasons=drop_reasons,
        )

    return EligibilityResult(
        filtered_scores=eligible,
        n_dropped=n_dropped,
        dropped_mechanisms=dropped,
        n_eligible=len(eligible),
        all_dropped=False,
        bypassed=False,
        drop_reasons=drop_reasons,
    )
