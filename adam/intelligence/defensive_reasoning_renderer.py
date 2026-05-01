# =============================================================================
# Spine #13 — Defensive Reasoning renderer (5-layer why-view)
# Location: adam/intelligence/defensive_reasoning_renderer.py
# =============================================================================
"""Structured 5-layer why-view rendered from a ``DecisionTrace``.

Closes the renderer half of directive Spine #13 (lines 386-402 +
Section 7.2 line 849-859). Per directive Section 8.2 line 905:
"Defensive Reasoning at recommendation time. Keep; reframe to read
from DecisionTrace."

This is the consumer that closes the Spine #6 producer chain:

    cascade.run_bilateral_cascade
        ↓ (sync emit, ab10f26)
    InMemoryDecisionTraceLog
        ↓ (Task 38 hourly drain, 4fe27c6)
    Redis hot cache (d9b4d7c) + Neo4j archival (edd4ded)
        ↓ load_trace / load_trace_from_neo4j
    DefensiveReasoningRender (this slice)
        ↓ (front-end consumes the structured render)
    LUXY CMO + Becca see the inspectable do-calculus chain

WHY THIS EXISTS
---------------

Per directive line 393: "Without it, even a perfect inference engine
is invisible. The pilot succeeds when the CMO can articulate, in his
own words, what ADAM is doing differently — and that articulation
depends entirely on the partner surface giving him the vocabulary
and the inspectable artifacts."

The renderer takes one DecisionTrace and produces five structured
layers (per directive line 853-859):

  1. Plain-language one-liner.
  2. Counterfactual — what would have been served instead.
  3. Decomposition bar chart — chain_of_reasoning entries as %.
  4. Confidence — 90% credible interval per-user effect.
  5. Provenance — links to user history / cohort state / priors /
     elicitation.

The output is structured data; HTML / JSX rendering is downstream
front-end work that consumes this structured render.

DISCIPLINE (B3-LUXY a/b/c/d)
----------------------------

(a) Citations: directive Spine #13 lines 386-402; directive Section
    7.2 lines 849-859 (the partner-facing layer specification);
    directive Section 8.2 line 905 (the "reframe to read from
    DecisionTrace" rule). Pydantic v2 BaseModel for the render
    schema discipline.

(b) Tests pin: 5 layers populated correctly; counterfactual present
    iff trace.alternatives non-empty; decomposition mirrors
    trace.chain_of_reasoning; confidence layer "not_available" when
    no posterior data; provenance links built from decision_id +
    user_id; load_and_render integrates with Redis and Neo4j storage
    substrates.

(c) calibration_pending=False — the renderer is declarative; no
    pilot-data-dependent constants. (Calibration applies to the
    front-end layout / formatting choices, which are downstream.)

(d) Honest tags — what is NOT in this slice (named successors):

    * Primary-metaphor vocabulary in the one-liner. The directive
      example (line 855) reads: "Served the FORWARD-MOTION creative
      because user is in TASK_COMPLETION posture..." This requires
      a primary-metaphor inventory (Phase 6 line 1059 deliverable).
      Until shipped, the one-liner uses mechanism_name verbatim
      rather than metaphor names. Honest tag preserved in render
      output (`one_liner_uses_metaphor_inventory: bool`).
    * Confidence layer per-user 90% credible interval. The directive
      requires this from the per-user posterior (Spine #1). The
      DecisionTrace currently carries user_posterior_snapshot as
      a Dict[str, float] without explicit CI fields — when no CI
      data is in the snapshot, the confidence layer reports
      status="not_available". A confidence-snapshot helper that
      populates CI fields on the trace at decision time is its own
      sibling slice.
    * Cohort-pooled estimate alongside the per-user CI. Cohorts
      (Spine #7) are BLOCKED on Loop B per session handoff. Until
      cohorts ship, the cohort_pooled_estimate field stays None.
    * Provenance hyperlinks. This slice produces URL-shaped
      strings (e.g., /users/{user_id}/posterior_history); the
      front-end constructs the actual hyperlinks against its
      routing.
    * Loop B elicitation provenance link. The trace doesn't carry
      elicitation_id today; when the elicitation substrate ships
      its full 6-mode set, the trace will carry the elicitation
      reference and provenance.elicitation_link will populate.
    * HTML / JSX rendering of the layers — front-end downstream.
"""

from __future__ import annotations

import logging
from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from adam.intelligence.decision_trace import (
    AlternativeCandidate,
    ChainOfReasoningEntry,
    DecisionTrace,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Layer-3 / -4 / -5 sub-models
# =============================================================================


class ConfidenceLayer(BaseModel):
    """Per-user 90% credible interval on the chosen mechanism's effect.

    ``status`` is one of:
      - "available" — ci_lower / ci_upper are populated
      - "not_available" — no CI data on the trace; sibling slice will
        wire confidence-snapshot helper to populate
    """

    model_config = ConfigDict(extra="forbid")

    status: str = "not_available"
    ci_lower: Optional[float] = None
    ci_upper: Optional[float] = None
    ci_level: float = 0.90
    point_estimate: Optional[float] = None
    cohort_pooled_estimate: Optional[float] = None


class ProvenanceLayer(BaseModel):
    """Links into the user's posterior history / cohort state / priors /
    elicitation. URL-shaped strings; the front-end binds them to its
    routing.
    """

    model_config = ConfigDict(extra="forbid")

    user_history_link: Optional[str] = None
    cohort_state_link: Optional[str] = None
    priors_link: Optional[str] = None
    elicitation_link: Optional[str] = None


# =============================================================================
# DefensiveReasoningRender — the 5-layer output
# =============================================================================


class DefensiveReasoningRender(BaseModel):
    """Structured 5-layer Defensive Reasoning render (directive line 853-859)."""

    model_config = ConfigDict(extra="forbid")

    decision_id: str
    one_liner: str
    counterfactual: Optional[str] = None
    decomposition: List[ChainOfReasoningEntry] = Field(default_factory=list)
    confidence: ConfidenceLayer = Field(default_factory=ConfidenceLayer)
    provenance: ProvenanceLayer = Field(default_factory=ProvenanceLayer)

    # Honest-tag flags so consumers know what's pending vs. available.
    one_liner_uses_metaphor_inventory: bool = False
    """Per directive line 855, the one-liner SHOULD use primary-
    metaphor names (FORWARD-MOTION, TASK_COMPLETION, CONTAINMENT).
    Until the metaphor inventory ships (Phase 6 line 1059), this
    slice uses raw mechanism / posture names — flag stays False so
    the front-end can surface the limitation if needed."""


# =============================================================================
# Renderer
# =============================================================================


def _render_one_liner(
    trace: DecisionTrace,
    top_alternative: Optional[AlternativeCandidate],
) -> str:
    """Compose the plain-language one-liner.

    Per directive line 855: "Served the FORWARD-MOTION creative
    because user is in TASK_COMPLETION posture on a productivity-
    tool page, with CONTAINMENT carryover from yesterday's touch
    already washed out. Expected utility 0.067; runner-up
    RELIABILITY-AS-WEIGHT at 0.041."

    Until the primary-metaphor inventory ships (Phase 6 line 1059),
    this uses mechanism + posture names verbatim rather than
    metaphor names. The one_liner_uses_metaphor_inventory flag on
    the render stays False so consumers know.
    """
    posture_phrase = (
        f"{trace.posture_class} posture"
        if trace.posture_class
        else "neutral page posture"
    )
    runner_up_phrase = (
        f"; runner-up {top_alternative.mechanism} at "
        f"{top_alternative.posterior_score:.3f}"
        if top_alternative is not None
        else ""
    )
    return (
        f"Served the {trace.chosen_mechanism} mechanism for user "
        f"in {posture_phrase}. "
        f"Expected utility {trace.chosen_score:.3f}{runner_up_phrase}."
    )


def _render_counterfactual(
    trace: DecisionTrace,
    top_alternative: Optional[AlternativeCandidate],
) -> Optional[str]:
    """Compose the counterfactual layer.

    Per directive line 856: "Would have served RELIABILITY-AS-WEIGHT,
    but the carryover penalty from yesterday's CONTAINMENT touch
    dropped its expected utility below FORWARD-MOTION."

    Returns None when no alternatives are present in the trace —
    the layer is honestly absent rather than rendered as "no
    counterfactual" placeholder.
    """
    if top_alternative is None:
        return None

    # Compute the gap that decided in favor of chosen
    gap = trace.chosen_score - top_alternative.posterior_score
    gap_phrase = (
        f"by {gap:.3f}" if gap > 0 else f"by {abs(gap):.3f} (after tiebreak)"
    )
    return (
        f"Would have served {top_alternative.mechanism} (creative "
        f"{top_alternative.creative_id}) but {trace.chosen_mechanism} "
        f"scored higher {gap_phrase}."
    )


def _render_confidence(trace: DecisionTrace) -> ConfidenceLayer:
    """Build the confidence layer from the trace's user posterior snapshot.

    The trace's user_posterior_snapshot is a Dict[str, float]; CI
    fields are conventional keys:
      - ci_lower_90 / ci_upper_90 → populates ci_lower / ci_upper
      - point_estimate → populates point_estimate
      - cohort_pooled_estimate → populates cohort_pooled_estimate

    When none of these keys are present, status="not_available" and
    all numeric fields stay None.
    """
    snap = trace.user_posterior_snapshot or {}
    ci_lo = snap.get("ci_lower_90")
    ci_hi = snap.get("ci_upper_90")
    point = snap.get("point_estimate")
    cohort = snap.get("cohort_pooled_estimate")

    if ci_lo is None and ci_hi is None and point is None:
        return ConfidenceLayer(status="not_available")

    return ConfidenceLayer(
        status="available",
        ci_lower=float(ci_lo) if ci_lo is not None else None,
        ci_upper=float(ci_hi) if ci_hi is not None else None,
        ci_level=0.90,
        point_estimate=float(point) if point is not None else None,
        cohort_pooled_estimate=(
            float(cohort) if cohort is not None else None
        ),
    )


def _render_provenance(trace: DecisionTrace) -> ProvenanceLayer:
    """Build URL-shaped provenance links.

    Conventions:
      - /users/{user_id}/posterior_history
      - /cohorts/state?user_id={user_id}
      - /priors?archetype={archetype}  (when user_posterior_snapshot
        carries archetype marker)
      - elicitation_link stays None until elicitation substrate
        ships its 6-mode set and the trace carries elicitation_id

    Fields are None when the underlying data isn't on the trace —
    no fabricated links.
    """
    user_history_link: Optional[str] = None
    cohort_state_link: Optional[str] = None
    priors_link: Optional[str] = None

    if trace.user_id:
        user_history_link = f"/users/{trace.user_id}/posterior_history"
        cohort_state_link = f"/cohorts/state?user_id={trace.user_id}"

    snap = trace.user_posterior_snapshot or {}
    if "archetype" in snap:
        # The cascade producer (ab10f26) places archetype as a
        # presence marker. We don't know the archetype name from the
        # snapshot key alone; the priors_link uses the user_id route
        # as a fallback that the front-end can resolve.
        if trace.user_id:
            priors_link = f"/priors?user_id={trace.user_id}"

    return ProvenanceLayer(
        user_history_link=user_history_link,
        cohort_state_link=cohort_state_link,
        priors_link=priors_link,
        elicitation_link=None,
    )


def render_defensive_reasoning(trace: DecisionTrace) -> DefensiveReasoningRender:
    """Render one DecisionTrace into the 5-layer DefensiveReasoningRender.

    Pure function — no IO, no side effects. The async ``load_and_render``
    helper combines this with storage loads when needed.
    """
    # Top alternative by posterior_score (descending). When ties exist,
    # the first by trace order wins — deterministic.
    top_alt: Optional[AlternativeCandidate] = None
    if trace.alternatives:
        top_alt = max(
            trace.alternatives, key=lambda a: a.posterior_score,
        )

    return DefensiveReasoningRender(
        decision_id=trace.decision_id,
        one_liner=_render_one_liner(trace, top_alt),
        counterfactual=_render_counterfactual(trace, top_alt),
        decomposition=list(trace.chain_of_reasoning.entries),
        confidence=_render_confidence(trace),
        provenance=_render_provenance(trace),
        one_liner_uses_metaphor_inventory=False,
    )


# =============================================================================
# Storage convenience — load + render
# =============================================================================


async def load_and_render(
    decision_id: str,
    redis_client: Optional[Any] = None,
    neo4j_driver: Optional[Any] = None,
) -> Optional[DefensiveReasoningRender]:
    """Load a DecisionTrace from storage then render it.

    Resolution order (per directive line 248: Redis hot, Neo4j warm):
      1. Try Redis (decision_trace_store.load_trace)
      2. Fall back to Neo4j (decision_trace_neo4j.load_trace_from_neo4j)
      3. None of the above → return None

    Returns None when the trace cannot be found anywhere or when
    storage soft-fails. Caller (the partner surface) treats None as
    "trace not in archive" and degrades gracefully.
    """
    trace: Optional[DecisionTrace] = None

    if redis_client is not None:
        try:
            from adam.intelligence.decision_trace_store import load_trace
            trace = await load_trace(decision_id, redis_client)
        except Exception as exc:
            logger.debug(
                "load_and_render: Redis load failed for decision_id=%s: %s",
                decision_id, exc,
            )

    if trace is None and neo4j_driver is not None:
        try:
            from adam.intelligence.decision_trace_neo4j import (
                load_trace_from_neo4j,
            )
            trace = await load_trace_from_neo4j(decision_id, neo4j_driver)
        except Exception as exc:
            logger.debug(
                "load_and_render: Neo4j load failed for decision_id=%s: %s",
                decision_id, exc,
            )

    if trace is None:
        return None

    return render_defensive_reasoning(trace)
