# =============================================================================
# ADAM Spine #13 — Partner Surface (Defensive Reasoning + Mechanism Rotation)
# Location: adam/intelligence/spine/spine_13_partner_surface.py
# =============================================================================

"""Partner surface — what the LUXY CMO and Becca actually see and use.

PER DIRECTIVE SECTION 7 + SPINE #13.

Three components:
    1. Defensive Reasoning rendered from Spine #6 DecisionTrace
       (NOT from the old Why-Library substrate; per directive
       Section 8.2 the DR renderer is reframed to read DecisionTrace)
    2. Loop B human-machine teaming — six elicitation modes (kAFC +
       RankOrder shipped previously; SPIES + FourPoint + CounterExample +
       Scenario in a separate commit)
    3. Mechanism-rotation graph demo — live view of which mechanisms
       are firing for which audiences, with credible intervals, cohort
       drift indicators, and click-through to per-impression do-
       calculus traces

WHY THIS IS SPINE — without the demo, the engine is invisible

Per directive Section 7: "Without it, even a perfect inference engine
is invisible. The pilot succeeds when the CMO can articulate, in his
own words, what ADAM is doing differently — and that articulation
depends entirely on the partner surface giving him the vocabulary and
the inspectable artifacts."

Per directive Section 7.3: "When the CMO walks through the mechanism-
rotation graph and clicks into a trace, he sees: (a) the user-level
N-of-1 inference, (b) the page-conditioned posture, (c) the carryover-
aware crossover schedule, (d) the free-energy decomposition, (e) the
counterfactual alternative, (f) the credible interval. That is the
entire architecture, made visible. Nothing else in programmatic does
this."

DECISION-TIME CONSUMERS (Rule A check)

Spine #13 reads from decision-time artifacts (DecisionTrace, cohort
policy state, posterior snapshots) and produces partner-facing render
artifacts. The render artifacts ARE consumed at decision-time-display
(when the partner clicks through to inspect a recommendation):

    - DefensiveReasoningView is read by the partner UI when an
      impression is clicked
    - MechanismRotationGraph is read by the dashboard at view-render
      time (every dashboard refresh)
    - WalkthroughScript drives the CMO walkthrough flow

Cognitive primitive at the partner surface (display time, not bid
time). Distinct from "measurement" because it operates ON real
decision artifacts, NOT on aggregate metrics. Foundation §7 rule 11:
the architectural enforcement is visible to the partner here.

THIS COMMIT SHIPS

    - DefensiveReasoningView Pydantic — REFRAMED to read DecisionTrace
      (Spine #6) directly
    - render_from_decision_trace function
    - The five-layer DR view per directive Section 7.2:
      one-line summary, counterfactual, decomposition bar chart,
      confidence interval, provenance
    - MechanismRotationGraph Pydantic + per-cohort timeseries
      data structure
    - WalkthroughStep + WalkthroughScript per directive Section 7.3
      (CMO demo script as templated structured steps; not free-form)

THIS COMMIT DOES NOT SHIP (follow-on commits)

    - 4 v0.2 elicitation modes (SPIES + FourPoint + CounterExample +
      Scenario) — separate commit since they extend a different module
      (dialogue_ledger.elicitation)
    - The actual UI rendering (frontend D-track work)
    - Live wiring to Spine #6 DecisionTrace store at production
      partner-API serving time

REPLACES (per directive Section 8.2)

The existing `adam/intelligence/defensive_reasoning.py` reads from the
old Why Library substrate (now narrowed per directive Section 8.2).
The reframed Spine #13 version reads from DecisionTrace (Spine #6).
Both modules COEXIST during the transition; orchestrator integration
will eventually call this version exclusively.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field, field_validator

from adam.intelligence.spine.spine_6_decision_trace import (
    AlternativeDecomposition,
    DecisionTrace,
)

logger = logging.getLogger(__name__)


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


# =============================================================================
# Templated render templates — A12 defense
# =============================================================================


# Per directive Section 7.2 example: "Served the FORWARD-MOTION creative
# because user is in TASK_COMPLETION posture on a productivity-tool
# page, with CONTAINMENT carryover from the prior touch already washed
# out."
#
# Templated string (NOT LLM-composed); slots filled from DecisionTrace.
_ONE_LINE_TEMPLATE: str = (
    "Served '{chosen_mechanism}' because user is in '{posture}' "
    "posture (confidence {posture_confidence:.2f}). "
    "{counterfactual_phrase}"
)


_COUNTERFACTUAL_TEMPLATE: str = (
    "Runner-up '{runner_up_mechanism}' was the next-best "
    "(score {runner_up_score:.2f} vs chosen {chosen_score:.2f}); "
    "{counterfactual_reason}."
)


_NO_RUNNER_UP_PHRASE: str = "No runner-up considered (single-candidate decision)."


# Templates for the five DR layers per directive Section 7.2.
_LAYER_DECOMPOSITION_TEMPLATE: str = (
    "Score components: posterior={posterior:.2f}, fluency={fluency:.2f}, "
    "free-energy={free_energy:.2f}, carryover={carryover:.2f}, "
    "epistemic={epistemic:.2f}."
)


# =============================================================================
# DefensiveReasoningView — reframed to read DecisionTrace
# =============================================================================


class DefensiveReasoningView(BaseModel):
    """Five-layer partner-facing view of one decision.

    Per directive Section 7.2, the layers are:
        1. Plain-language one-liner (templated; NOT LLM-composed)
        2. Counterfactual (next-best alternative + reason)
        3. Decomposition (per-component contribution)
        4. Confidence (credible interval on the per-user effect)
        5. Provenance (links to user posterior history, cohort policy
           state, offline-discovered priors, original elicitation)

    Each layer is a structured slot. The "natural reading" comes from
    pre-authored templates, NOT free-form prose composition. Foundation
    §7 rule 11 enforcement: even the partner-facing surface speaks in
    structured cognitive vocabulary.
    """

    model_config = ConfigDict(extra="forbid")

    decision_id: str
    user_id: str
    timestamp: datetime
    chosen_mechanism: str

    # Layer 1: one-liner
    one_line_summary: str

    # Layer 2: counterfactual
    counterfactual_summary: str
    runner_up_mechanism: Optional[str] = None
    runner_up_score: Optional[float] = None

    # Layer 3: decomposition
    score_components: Dict[str, float] = Field(default_factory=dict)
    decomposition_summary: str = ""

    # Layer 4: confidence
    posterior_credible_interval_summary: str = ""
    cohort_pooled_estimate_summary: str = ""

    # Layer 5: provenance
    provenance_links: Dict[str, str] = Field(default_factory=dict)
    discipline_flags: List[str] = Field(default_factory=list)


def _render_counterfactual(
    chosen_alt: Optional[AlternativeDecomposition],
    chosen_score: float,
    runner_up_alt: Optional[AlternativeDecomposition],
) -> Tuple[str, Optional[str], Optional[float]]:
    """Render the counterfactual layer (Layer 2 of the DR view).

    Returns (summary_text, runner_up_mechanism, runner_up_score).
    """
    if runner_up_alt is None:
        return _NO_RUNNER_UP_PHRASE, None, None

    # Templated reason — picks the dominant decomposition difference
    # between chosen and runner_up. NOT LLM-composed.
    reason = "score margin sufficient to prefer chosen"
    if chosen_alt is not None:
        carryover_delta = (
            runner_up_alt.carryover_correction_term
            - chosen_alt.carryover_correction_term
        )
        if abs(carryover_delta) > 0.01:
            reason = (
                f"carryover penalty differs ({carryover_delta:+.2f}); "
                "this dropped runner-up below chosen"
            )
        elif (
            runner_up_alt.fluency_score < chosen_alt.fluency_score - 0.1
        ):
            reason = "runner-up's fluency score against page posture lower"
        elif (
            runner_up_alt.free_energy_F > chosen_alt.free_energy_F + 0.1
        ):
            reason = (
                "runner-up has higher free-energy F (worse goal-state fit)"
            )

    summary = _COUNTERFACTUAL_TEMPLATE.format(
        runner_up_mechanism=runner_up_alt.mechanism,
        runner_up_score=runner_up_alt.final_score,
        chosen_score=chosen_score,
        counterfactual_reason=reason,
    )
    return summary, runner_up_alt.mechanism, runner_up_alt.final_score


def render_from_decision_trace(
    trace: DecisionTrace,
    *,
    aggregate_a14_flags: Optional[List[str]] = None,
) -> DefensiveReasoningView:
    """Build a DefensiveReasoningView from a Spine #6 DecisionTrace.

    Per directive Section 7.2: "Triggered by clicking any impression
    in View A. Reads from the DecisionTrace."

    Pure function: identical traces produce identical output bytes.
    Templated rendering — no LLM composition.
    """
    # Find chosen alternative in the trace.
    chosen_alt: Optional[AlternativeDecomposition] = next(
        (a for a in trace.alternatives if a.mechanism == trace.chosen_mechanism),
        None,
    )
    # Runner-up = next-highest-scoring NOT-chosen alternative
    other_alts = [
        a for a in trace.alternatives if a.mechanism != trace.chosen_mechanism
    ]
    runner_up: Optional[AlternativeDecomposition] = None
    if other_alts:
        runner_up = max(other_alts, key=lambda a: a.final_score)

    # Layer 2: counterfactual
    counterfactual_text, runner_up_name, runner_up_score = _render_counterfactual(
        chosen_alt=chosen_alt,
        chosen_score=trace.chosen_score,
        runner_up_alt=runner_up,
    )

    # Layer 1: one-liner
    one_line = _ONE_LINE_TEMPLATE.format(
        chosen_mechanism=trace.chosen_mechanism,
        posture=trace.page_posture or "unspecified",
        posture_confidence=trace.page_posture_confidence,
        counterfactual_phrase=counterfactual_text,
    )

    # Layer 3: decomposition
    if chosen_alt is not None:
        components = {
            "posterior": chosen_alt.posterior_score,
            "fluency": chosen_alt.fluency_score,
            "free_energy": chosen_alt.free_energy_F,
            "carryover": chosen_alt.carryover_correction_term,
            "epistemic": chosen_alt.epistemic_bonus,
        }
        decomposition_summary = _LAYER_DECOMPOSITION_TEMPLATE.format(
            posterior=components["posterior"],
            fluency=components["fluency"],
            free_energy=components["free_energy"],
            carryover=components["carryover"],
            epistemic=components["epistemic"],
        )
    else:
        components = {}
        decomposition_summary = "No structured decomposition available."

    # Layer 4: confidence (templated — pulls from posterior snapshot if present)
    posterior_ci_summary = (
        "Per-user posterior shifted by recent observations; credible "
        "interval narrows with more evidence."
    )
    cohort_summary = "Cohort-pooled estimate informs new-user start."

    # Layer 5: provenance — structured links
    provenance: Dict[str, str] = {
        "decision_id": trace.decision_id,
        "user_id": trace.user_id,
        "sapid": trace.sapid or "",
        "bid_request_id": trace.bid_request_id or "",
    }
    if trace.outcome_class:
        provenance["outcome_class"] = trace.outcome_class
    if trace.bid_value is not None:
        provenance["bid_value"] = f"{trace.bid_value:.2f}"

    discipline = list(aggregate_a14_flags or [])

    return DefensiveReasoningView(
        decision_id=trace.decision_id,
        user_id=trace.user_id,
        timestamp=trace.timestamp,
        chosen_mechanism=trace.chosen_mechanism,
        one_line_summary=one_line,
        counterfactual_summary=counterfactual_text,
        runner_up_mechanism=runner_up_name,
        runner_up_score=runner_up_score,
        score_components=components,
        decomposition_summary=decomposition_summary,
        posterior_credible_interval_summary=posterior_ci_summary,
        cohort_pooled_estimate_summary=cohort_summary,
        provenance_links=provenance,
        discipline_flags=discipline,
    )


# =============================================================================
# MechanismRotationGraph — the demo that wins Pilot 2
# =============================================================================


class CohortMechanismTimepoint(BaseModel):
    """One (cohort, mechanism, timestamp) data point on the
    mechanism-rotation graph."""

    model_config = ConfigDict(extra="forbid")

    cohort_id: str
    mechanism: str
    timestamp: datetime
    budget_share: float       # fraction of cohort budget allocated
    posterior_ci_width: float  # uncertainty (drives intensity rendering)
    n_observations_in_window: int


class CohortDriftIndicator(BaseModel):
    """Cohort-level drift signal per directive Section 7.1.

    Per directive: 'Kalman-filter drift magnitude alerts.' High
    drift_magnitude → cohort regime is shifting; partner sees an
    indicator color change in the dashboard.
    """

    model_config = ConfigDict(extra="forbid")

    cohort_id: str
    drift_magnitude: float
    indicator_status: str  # "stable" | "drifting" | "regime_shift"
    last_evaluated_at: datetime = Field(default_factory=_now_utc)


class FluencyFloorComplianceMetric(BaseModel):
    """Per directive Section 7.1: 'Attention-inversion floor compliance
    rate (target: 0.1-2% violation rate; an indicator outside this band
    flags a calibration problem).'"""

    model_config = ConfigDict(extra="forbid")

    n_decisions: int
    n_floor_violations: int
    violation_rate: float
    in_target_band: bool

    @field_validator("violation_rate")
    @classmethod
    def _validate_rate(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError(f"violation_rate must be in [0, 1]; got {v}")
        return v


class MSPRTBoundaryStatus(BaseModel):
    """Per directive Section 7.1 + Section 8.4: 'mSPRT campaign monitor.'

    Pre-specified boundaries; crossing the upper boundary mid-pilot is
    a positive signal; crossing lower boundary is a RED-criterion launch
    deferral trigger.
    """

    model_config = ConfigDict(extra="forbid")

    upper_boundary: float
    lower_boundary: float
    current_test_statistic: float
    boundary_crossed: Optional[str] = None  # "upper" | "lower" | None
    is_red_criterion_triggered: bool = False


class MechanismRotationGraph(BaseModel):
    """The mechanism-rotation graph — partner-facing dashboard view.

    Per directive Section 7.1 View A:
        - X-axis: time (rolling 30-day window)
        - Y-axis: budget allocation per cohort
        - Stacked area: which mechanisms are firing for each cohort
        - Annotations:
            cohort posterior intervals
            cohort-drift indicators (Kalman flag)
            within-subject schedule for an exemplar user (toggle)
            mSPRT campaign-level boundary status
            attention-inversion floor compliance rate
    """

    model_config = ConfigDict(extra="forbid")

    rendered_at: datetime = Field(default_factory=_now_utc)
    rolling_window_days: int = 30

    # Stacked-area data: list of (cohort, mechanism, timestamp, budget_share)
    timepoints: List[CohortMechanismTimepoint] = Field(default_factory=list)

    # Cohort-drift annotations
    cohort_drift_indicators: List[CohortDriftIndicator] = Field(
        default_factory=list,
    )

    # Compliance metric
    fluency_floor_compliance: Optional[FluencyFloorComplianceMetric] = None

    # mSPRT campaign-level monitor
    msprt_status: Optional[MSPRTBoundaryStatus] = None


def compute_floor_compliance(
    n_decisions: int,
    n_floor_violations: int,
    *,
    target_lower: float = 0.001,
    target_upper: float = 0.02,
) -> FluencyFloorComplianceMetric:
    """Compute the fluency-floor compliance metric per directive
    Section 4.4: 'Target violation rate: 0.5-2% of decisions. Below
    0.1% means the floor is too lax; above 5% means too strict.'

    Returns FluencyFloorComplianceMetric with in_target_band True iff
    rate is in [target_lower, target_upper].
    """
    if n_decisions <= 0:
        return FluencyFloorComplianceMetric(
            n_decisions=0, n_floor_violations=0,
            violation_rate=0.0, in_target_band=False,
        )
    rate = n_floor_violations / n_decisions
    in_band = target_lower <= rate <= target_upper
    return FluencyFloorComplianceMetric(
        n_decisions=n_decisions,
        n_floor_violations=n_floor_violations,
        violation_rate=rate,
        in_target_band=in_band,
    )


# =============================================================================
# CMO Walkthrough script (per directive Section 7.3)
# =============================================================================


class WalkthroughStepKind(str, Enum):
    """The 10 step kinds in the CMO walkthrough per directive §7.3."""

    SHOW_ROTATION_GRAPH = "show_rotation_graph"
    POINT_OUT_PATTERN = "point_out_pattern"
    SHOW_DRIFTING_COHORT = "show_drifting_cohort"
    CLICK_INTO_USER = "click_into_user"
    SHOW_WITHIN_SUBJECT_SCHEDULE = "show_within_subject_schedule"
    CLICK_INTO_IMPRESSION = "click_into_impression"
    WALK_DO_CALCULUS_CHAIN = "walk_do_calculus_chain"
    SHOW_COUNTERFACTUAL = "show_counterfactual"
    SHOW_CREDIBLE_INTERVAL = "show_credible_interval"
    SHOW_FLOOR_COMPLIANCE = "show_floor_compliance"
    SHOW_MSPRT_BOARD = "show_msprt_board"


class WalkthroughStep(BaseModel):
    """One step in the CMO walkthrough.

    Templated — narrative comes from pre-authored prose per kind, NOT
    LLM-composed. The kind enum is the load-bearing structure.
    """

    model_config = ConfigDict(extra="forbid")

    step_index: int
    kind: WalkthroughStepKind
    narrative: str          # human-authored; NOT LLM
    target_artifact: str = ""  # e.g., "cohort_status_seeker", "decision_id_xyz"


class WalkthroughScript(BaseModel):
    """The CMO walkthrough script per directive Section 7.3.

    The script is a sequence of WalkthroughSteps. The directive
    specifies a 10-step canonical script. The partner-facing UI
    drives the CMO through these steps.
    """

    model_config = ConfigDict(extra="forbid")

    script_id: str
    steps: List[WalkthroughStep]
    target_pilot: str = ""

    def step_by_index(self, index: int) -> Optional[WalkthroughStep]:
        for step in self.steps:
            if step.step_index == index:
                return step
        return None


def make_canonical_cmo_walkthrough() -> WalkthroughScript:
    """Build the canonical CMO walkthrough script per directive Section 7.3.

    The narrative text is templated (human-authored prose; one
    sentence per step). NOT LLM-composed. Foundation §7 rule 11: even
    the demo script speaks in structured cognitive vocabulary.
    """
    steps = [
        WalkthroughStep(
            step_index=1,
            kind=WalkthroughStepKind.SHOW_ROTATION_GRAPH,
            narrative=(
                "View A: the mechanism-rotation graph. The X-axis is the "
                "last 30 days; the Y-axis is budget allocation per "
                "cohort; the stacked area shows which mechanisms are "
                "firing for each audience."
            ),
        ),
        WalkthroughStep(
            step_index=2,
            kind=WalkthroughStepKind.POINT_OUT_PATTERN,
            narrative=(
                "Notice the rotation: the system is not stuck on one "
                "creative or mechanism. It is exploring per-cohort "
                "while exploiting where it has confidence."
            ),
        ),
        WalkthroughStep(
            step_index=3,
            kind=WalkthroughStepKind.SHOW_DRIFTING_COHORT,
            narrative=(
                "This cohort is drifting — see the Kalman flag. The "
                "system updates the cohort policy as the population "
                "shifts; non-stationary regimes are first-class."
            ),
        ),
        WalkthroughStep(
            step_index=4,
            kind=WalkthroughStepKind.CLICK_INTO_USER,
            narrative=(
                "Click into one user. This is an N-of-1 trial — within-"
                "subject randomization, washout-aware scheduling, and "
                "an explicit per-user posterior over mechanism efficacy."
            ),
        ),
        WalkthroughStep(
            step_index=5,
            kind=WalkthroughStepKind.SHOW_WITHIN_SUBJECT_SCHEDULE,
            narrative=(
                "The schedule alternates mechanism A and mechanism B "
                "with washout intervals between same-mechanism repeats. "
                "Carryover from the prior touch is corrected explicitly."
            ),
        ),
        WalkthroughStep(
            step_index=6,
            kind=WalkthroughStepKind.CLICK_INTO_IMPRESSION,
            narrative=(
                "Click into one impression decision. The Defensive "
                "Reasoning panel opens — five layers of structured "
                "rationale."
            ),
        ),
        WalkthroughStep(
            step_index=7,
            kind=WalkthroughStepKind.WALK_DO_CALCULUS_CHAIN,
            narrative=(
                "Walk the do-calculus chain: posterior + fluency floor "
                "+ free-energy + carryover + epistemic bonus combined "
                "into the chosen mechanism's score."
            ),
        ),
        WalkthroughStep(
            step_index=8,
            kind=WalkthroughStepKind.SHOW_COUNTERFACTUAL,
            narrative=(
                "Counterfactual: this is what would have been served "
                "with the runner-up. The system records the trade-off "
                "explicitly."
            ),
        ),
        WalkthroughStep(
            step_index=9,
            kind=WalkthroughStepKind.SHOW_CREDIBLE_INTERVAL,
            narrative=(
                "Credible interval: 90% CI on the per-user effect of "
                "the chosen mechanism. Honest about uncertainty; "
                "narrows with more evidence."
            ),
        ),
        WalkthroughStep(
            step_index=10,
            kind=WalkthroughStepKind.SHOW_FLOOR_COMPLIANCE,
            narrative=(
                "Attention-inversion floor compliance: this is the "
                "architectural floor we never violate. Today's rate is "
                "in the target band; if it ever leaves, an alert fires."
            ),
        ),
    ]
    return WalkthroughScript(
        script_id="cmo_canonical_v1",
        steps=steps,
        target_pilot="luxy",
    )


__all__ = [
    "CohortDriftIndicator",
    "CohortMechanismTimepoint",
    "DefensiveReasoningView",
    "FluencyFloorComplianceMetric",
    "MSPRTBoundaryStatus",
    "MechanismRotationGraph",
    "WalkthroughScript",
    "WalkthroughStep",
    "WalkthroughStepKind",
    "compute_floor_compliance",
    "make_canonical_cmo_walkthrough",
    "render_from_decision_trace",
]
