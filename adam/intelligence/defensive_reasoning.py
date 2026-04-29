# =============================================================================
# ADAM — Defensive Reasoning at Recommendation Time
# Location: adam/intelligence/defensive_reasoning.py
# =============================================================================

"""Partner-facing renderer for "why this recommendation, why not the
alternatives" at decision-display time. HMT §10 + Foundation §4.3.

PURPOSE

When a partner views a recommendation, the Defensive Reasoning surface
gives them the structured rationale:

    - Why this recommendation was selected (templated reason tags +
      one-line per-tag rendering)
    - The construct chain that produced it (links to ChainAttestation
      records via the rendering primitive in chain_rendering.py)
    - Which alternatives were considered (mechanism / archetype /
      variant) and the templated rejection reason for each
    - Aggregate A14 flags carried by the underlying chain (so the
      partner sees calibration-pending state, not a falsely confident
      view)

A12 ENFORCEMENT — STRUCTURED, NEVER PROSE

The renderer NEVER composes free-form prose. Every line in the partner-
facing view is a template populated from structured input:
  - Why entry (categorical reason tags + structured alternatives)
  - Chain attestations (typed evidence + adjustments)
  - A14 flags (named identifiers from the calibration-pending counter)

If a reason or alternative reads naturally as English, that's because
the TEMPLATE strings were authored to read naturally — the data filling
them is structured. The data flow is:

    structured input (Why entry + chain attestations + A14 flags)
        →  templated render functions
        →  DefensiveReasoningView (Pydantic, structured)
        →  partner API JSON

No LLM call sits anywhere in this path.

A14 FLAG

Identifier:
    DEFENSIVE_REASONING_INTERIM_RENDERER

Retirement trigger:
    Retire when (a) ≥30 rendered defensive-reasoning views have been
    validated by Chris or a stat-reviewer for vocabulary fit, AND
    (b) the alternatives section has been instrumented with M2-derived
    causal-margin numbers (not just raw cascade scores at the moment
    of selection).

DESIGN NOTES

- The renderer is a PURE FUNCTION of (Why entry, chain attestations).
  Identical inputs produce identical output bytes. This is necessary
  for caching and for audit (a partner asking "what was the
  recommendation rationale on date X?" gets the same answer two months
  later).

- When the Why Library has no entry for a recommendation_id, the
  renderer returns None — the partner-facing layer surfaces a
  "rationale not yet captured" state rather than fabricating one.
  Silent fabrication is the A11 drift defense rejected here.

- Aggregate A14 flags from the chain attestations are surfaced in the
  view's `discipline_flags` field. The partner sees calibration-
  pending state explicitly, not buried.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from adam.intelligence.why_library import (
    AlternativeConsidered,
    WhyEntry,
    query_why_for_recommendation,
)

logger = logging.getLogger(__name__)


# =============================================================================
# A14 flag constants
# =============================================================================


DEFENSIVE_REASONING_INTERIM_RENDERER_FLAG: str = (
    "DEFENSIVE_REASONING_INTERIM_RENDERER"
)

DEFENSIVE_REASONING_RETIREMENT_TRIGGER: str = (
    "Retire DEFENSIVE_REASONING_INTERIM_RENDERER when (a) ≥30 rendered "
    "defensive-reasoning views have been validated by Chris or a stat-"
    "reviewer for vocabulary fit, AND (b) the alternatives section has "
    "been instrumented with M2-derived causal-margin numbers (not just "
    "raw cascade scores at the moment of selection)."
)


# =============================================================================
# Templated reason-tag → human-readable line
# =============================================================================


# Each tag in PRIMARY_REASON_TAGS gets a one-line template. The
# templates are AUTHORED as English-reading strings; the SUBSTITUTIONS
# are structured (archetype / mechanism / score). This is the
# allowable shape per A12 — natural-reading templates populated from
# structured data, NOT free-form composition.
_REASON_TAG_TEMPLATES: Dict[str, str] = {
    "archetype_match_strong": (
        "Bilateral edge evidence for {archetype} dominates this audience."
    ),
    "mechanism_uncertainty_low": (
        "Posterior on {mechanism} is tight; selection is high-confidence."
    ),
    "page_attentional_posture_aligned": (
        "Page context blends with {mechanism} per attention-inversion."
    ),
    "construct_chain_high_confidence": (
        "Atom chain calibration for this recommendation is strong."
    ),
    "edge_dimension_load_bearing": (
        "A specific bilateral edge dimension is load-bearing for "
        "{archetype} × {mechanism}."
    ),
    "cohort_response_consistent": (
        "Aggregate cohort response favors {mechanism} for {archetype}."
    ),
    "mechanism_taxonomy_blend_compatible": (
        "{mechanism} is blend-compatible (does not activate vigilance) "
        "for {archetype}."
    ),
    "primary_metaphor_resonance": (
        "Primary-metaphor scoring favors this argument shape."
    ),
    "horizon_consistent_with_signal": (
        "Multi-horizon adjudication does not flag this recommendation."
    ),
}


_WHY_NOT_TAG_TEMPLATES: Dict[str, str] = {
    "score_margin_below_threshold": (
        "{value} scored {score:.2f} (below selected mechanism's margin)."
    ),
    "uncertainty_too_wide": (
        "{value} posterior CI too wide for confident selection."
    ),
    "vigilance_activating_for_archetype": (
        "{value} activates vigilance for this archetype (taxonomy mismatch)."
    ),
    "page_posture_misaligned": (
        "{value} would mismatch the current page's attentional posture."
    ),
    "calibration_pending": (
        "{value} carries an active calibration-pending flag."
    ),
    "horizon_discordance_alert": (
        "{value} flagged by multi-horizon discordance check."
    ),
    "construct_chain_unconverged": (
        "{value} has missing or unconverged chain links."
    ),
    "deviation_lifecycle_pending": (
        "Past partner override on {value} still awaits adjudication."
    ),
    "cohort_signal_weak": (
        "Aggregate cohort signal for {value} is too weak to support."
    ),
}


# =============================================================================
# Pydantic view model — structured partner-facing output
# =============================================================================


class ReasonLine(BaseModel):
    """One rendered reason line in the partner-facing view."""

    model_config = ConfigDict(extra="forbid")

    tag: str
    template_filled: str   # The natural-reading line from the template


class AlternativeLine(BaseModel):
    """One rendered alternative-considered line."""

    model_config = ConfigDict(extra="forbid")

    alternative_kind: str
    alternative_value: str
    score_at_consideration: float
    why_not_tag: str
    why_not_filled: str    # The natural-reading line from the template
    why_not_annotation: Optional[str] = None  # Pass-through (human-authored only)


class DefensiveReasoningView(BaseModel):
    """The structured partner-facing "why" view at decision time.

    Every field is structured. The natural-reading lines (template_filled,
    why_not_filled) come from substituting structured slots into pre-
    authored templates — NOT from LLM composition.
    """

    model_config = ConfigDict(extra="forbid")

    recommendation_id: str
    archetype: str
    mechanism: str
    primary_reasons: List[ReasonLine]
    alternatives_considered: List[AlternativeLine]
    evidence_chain_refs: List[str] = Field(default_factory=list)
    discipline_flags: List[str] = Field(default_factory=list)
    rendered_summary: str  # Top-line one-liner (templated)


# =============================================================================
# Renderer
# =============================================================================


def _render_reason_line(
    tag: str, archetype: str, mechanism: str,
) -> ReasonLine:
    """Render one reason tag into a ReasonLine via the template."""
    template = _REASON_TAG_TEMPLATES.get(tag)
    if template is None:
        # Unknown tag — surface honestly with a stable shape rather
        # than fabricating an explanation. The validator on WhyEntry
        # rejects unknown tags upstream, so this branch is a defense
        # in depth.
        filled = f"Reason tag '{tag}' has no rendering template."
    else:
        filled = template.format(archetype=archetype, mechanism=mechanism)
    return ReasonLine(tag=tag, template_filled=filled)


def _render_alternative_line(alt: AlternativeConsidered) -> AlternativeLine:
    """Render one alternative-considered into an AlternativeLine."""
    template = _WHY_NOT_TAG_TEMPLATES.get(alt.why_not_tag)
    if template is None:
        filled = f"Why-not tag '{alt.why_not_tag}' has no rendering template."
    else:
        filled = template.format(
            value=alt.alternative_value,
            score=alt.score_at_consideration,
        )
    return AlternativeLine(
        alternative_kind=alt.alternative_kind,
        alternative_value=alt.alternative_value,
        score_at_consideration=alt.score_at_consideration,
        why_not_tag=alt.why_not_tag,
        why_not_filled=filled,
        why_not_annotation=alt.why_not_annotation,
    )


def _render_summary(
    archetype: str, mechanism: str, n_reasons: int, n_alternatives: int,
) -> str:
    """Render the top-line summary. Templated, structured input only."""
    if n_alternatives == 0:
        return (
            f"Recommended '{mechanism}' for '{archetype}'. "
            f"{n_reasons} primary reason(s)."
        )
    return (
        f"Recommended '{mechanism}' for '{archetype}'. "
        f"{n_reasons} primary reason(s); "
        f"{n_alternatives} alternative(s) considered."
    )


def build_defensive_reasoning_view(
    recommendation_id: str,
    *,
    aggregate_a14_flags: Optional[List[str]] = None,
    why_entry_override: Optional[WhyEntry] = None,
) -> Optional[DefensiveReasoningView]:
    """Build the partner-facing view for a recommendation.

    Reads the Why Library entry (or accepts an override for tests).
    Renders each reason tag and alternative through the templated
    formatting. Adds aggregate A14 flags from the underlying chain
    so the partner sees calibration-pending state explicitly.

    Returns None when no Why entry is recorded for the recommendation_id.
    The partner-facing layer surfaces "rationale not yet captured"
    state rather than fabricating one — A11 defense.
    """
    entry = why_entry_override or query_why_for_recommendation(recommendation_id)
    if entry is None:
        logger.debug(
            "No Why entry for recommendation_id=%s — returning None",
            recommendation_id,
        )
        return None

    primary_reasons = [
        _render_reason_line(tag, entry.archetype, entry.mechanism)
        for tag in entry.primary_reason_tags
    ]
    alternatives = [
        _render_alternative_line(alt)
        for alt in entry.alternatives_considered
    ]

    discipline_flags = list(aggregate_a14_flags or [])
    # The renderer itself carries an A14 flag (interim-renderer).
    # Surface it on every view so the discipline is visible.
    discipline_flags.append(DEFENSIVE_REASONING_INTERIM_RENDERER_FLAG)

    summary = _render_summary(
        entry.archetype,
        entry.mechanism,
        n_reasons=len(primary_reasons),
        n_alternatives=len(alternatives),
    )

    return DefensiveReasoningView(
        recommendation_id=entry.recommendation_id,
        archetype=entry.archetype,
        mechanism=entry.mechanism,
        primary_reasons=primary_reasons,
        alternatives_considered=alternatives,
        evidence_chain_refs=list(entry.evidence_chain_refs),
        discipline_flags=discipline_flags,
        rendered_summary=summary,
    )


def render_view_to_dict(view: DefensiveReasoningView) -> Dict[str, Any]:
    """Convert a DefensiveReasoningView to a JSON-serializable dict.

    Used by the partner API to ship the view over the wire.
    """
    return view.model_dump(mode="json")


__all__ = [
    "AlternativeLine",
    "DefensiveReasoningView",
    "DEFENSIVE_REASONING_INTERIM_RENDERER_FLAG",
    "DEFENSIVE_REASONING_RETIREMENT_TRIGGER",
    "ReasonLine",
    "build_defensive_reasoning_view",
    "render_view_to_dict",
]
