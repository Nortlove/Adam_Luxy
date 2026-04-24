"""blend_fit — creative ↔ page alignment primitive (attention-inversion
platform-core implication #1).

Every creative-selection decision can now be conditioned on how
continuously a creative reads within the context it ships into. High
blend_fit creatives BLEND into the attentional pattern the context
produced; low blend_fit creatives interrupt the pattern and get
routed to conscious evaluation. Selection pressure shaped by
blend_fit moves the fitness landscape toward blend-and-fulfill
rather than grab-attention (Foundation rule 11: the fitness function
IS the ethics).

See: ``project_attention_inversion_platform_core.md`` — this module
ships implication #1 of five. Implication #2 (mechanism-taxonomy
split along blend-compatible vs vigilance-activating) is a separate
slice (Tier 1 #15).

Scope of THIS slice
-------------------

- ``CreativeFeatureBundle`` — frozen dataclass parallel to
  ``PageFeatureBundle`` in ``claude_feature_scoring.py`` with one
  directional flip: the page ACTIVATES goals; the creative FULFILLS
  goals. Shape is otherwise identical so alignment math is symmetric.
- ``compute_blend_fit(creative, page)`` — confidence-weighted
  alignment across the six feature axes. Returns a scalar in [0, 1]
  plus a structured ``BlendFitDecomposition`` attributing the score
  to each axis (useful for debugging and for the ILA's
  HYPOTHESIZE / VALIDATE loop on creative selection).

Frame discipline (orientation A1, A5; platform-core attention-inversion)
------------------------------------------------------------------------

- Alignment math uses only stored feature values + confidences. No
  learned model, no invented weights beyond the attention-inversion
  rationale named in ``a14_compromises.BLEND_FIT_WEIGHTS_UNVALIDATED``.
- Confidence weighting is first-class. When either side has zero
  confidence on a feature, that feature's contribution to blend_fit
  drops to zero — low-confidence features cannot drive selection.
- Per-feature alignment + decomposition is returned alongside the
  scalar so the selection layer can audit which axis a blend_fit
  score actually depends on rather than treating the scalar as a
  black-box ranking.

NOT in this slice
-----------------

- **Creative-side feature scorer**. The ``CreativeFeatureBundle``
  shape is defined here; the scorer that produces it from creative
  text / copy / CTA is a named follow-up (mirror of
  ``adam/intelligence/pages/claude_feature_scoring.py``).
- **Selection integration**. The bandit / mechanism-selector that
  would call ``compute_blend_fit`` to weight creatives is wired in a
  separate slice.
- **Learned weights**. The blend-axis weights are static and
  externally motivated; learning them from pilot data is post-pilot
  work named in ``a14_compromises.BLEND_FIT_WEIGHTS_UNVALIDATED``.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from typing import Dict, List, Mapping

from adam.intelligence.pages.claude_feature_scoring import (
    GOAL_ACTIVATION_KEYS,
    PRIMARY_METAPHOR_AXIS_NAMES,
    PageFeatureBundle,
    REGISTER_CATEGORIES,
)

logger = logging.getLogger(__name__)


# =============================================================================
# CreativeFeatureBundle — creative-side mirror of PageFeatureBundle
# =============================================================================


@dataclass(frozen=True)
class CreativeFeatureBundle:
    """Scored feature bundle for a creative.

    Mirrors ``PageFeatureBundle`` with one directional flip:
    ``goal_fulfillment_profile`` names which goals the creative
    FULFILLS (i.e., the goals whose priming is answered by engaging
    with this creative), not which goals the creative activates. The
    distinction matters because blend_fit pairs page-side activation
    with creative-side fulfillment.
    """

    register_score: float  # [-1, 1]
    register_category: str  # REGISTER_CATEGORIES
    register_confidence: float  # [0, 1]

    primary_metaphor_density: float  # [0, 1]
    primary_metaphor_axes: List[float]  # 8 dims, [0, 1] each
    primary_metaphor_confidence: float  # [0, 1]

    goal_fulfillment_profile: Dict[str, float]  # GOAL_ACTIVATION_KEYS → [0, 1]
    goal_fulfillment_confidence: float  # [0, 1]

    temporal_horizon_induction: float  # [-1, 1]
    temporal_horizon_confidence: float  # [0, 1]

    processing_fluency: float  # [0, 1]
    processing_fluency_confidence: float  # [0, 1]

    attentional_posture: float  # [-1, 1]
    attentional_posture_confidence: float  # [0, 1]

    def validate(self) -> None:
        _require_range("register_score", self.register_score, -1.0, 1.0)
        if self.register_category not in REGISTER_CATEGORIES:
            raise ValueError(
                f"register_category {self.register_category!r} not in "
                f"{REGISTER_CATEGORIES}"
            )
        _require_range(
            "register_confidence", self.register_confidence, 0.0, 1.0,
        )

        _require_range(
            "primary_metaphor_density",
            self.primary_metaphor_density, 0.0, 1.0,
        )
        if len(self.primary_metaphor_axes) != len(PRIMARY_METAPHOR_AXIS_NAMES):
            raise ValueError(
                f"primary_metaphor_axes length "
                f"{len(self.primary_metaphor_axes)} != "
                f"{len(PRIMARY_METAPHOR_AXIS_NAMES)}"
            )
        for i, v in enumerate(self.primary_metaphor_axes):
            _require_range(
                f"primary_metaphor_axes[{PRIMARY_METAPHOR_AXIS_NAMES[i]}]",
                v, 0.0, 1.0,
            )
        _require_range(
            "primary_metaphor_confidence",
            self.primary_metaphor_confidence, 0.0, 1.0,
        )

        if set(self.goal_fulfillment_profile.keys()) != set(GOAL_ACTIVATION_KEYS):
            missing = set(GOAL_ACTIVATION_KEYS) - set(self.goal_fulfillment_profile.keys())
            extra = set(self.goal_fulfillment_profile.keys()) - set(GOAL_ACTIVATION_KEYS)
            raise ValueError(
                f"goal_fulfillment_profile keys mismatch. "
                f"missing={sorted(missing)}, extra={sorted(extra)}"
            )
        for goal_id, v in self.goal_fulfillment_profile.items():
            _require_range(
                f"goal_fulfillment_profile[{goal_id}]", v, 0.0, 1.0,
            )
        _require_range(
            "goal_fulfillment_confidence",
            self.goal_fulfillment_confidence, 0.0, 1.0,
        )

        _require_range(
            "temporal_horizon_induction",
            self.temporal_horizon_induction, -1.0, 1.0,
        )
        _require_range(
            "temporal_horizon_confidence",
            self.temporal_horizon_confidence, 0.0, 1.0,
        )

        _require_range(
            "processing_fluency", self.processing_fluency, 0.0, 1.0,
        )
        _require_range(
            "processing_fluency_confidence",
            self.processing_fluency_confidence, 0.0, 1.0,
        )

        _require_range(
            "attentional_posture",
            self.attentional_posture, -1.0, 1.0,
        )
        _require_range(
            "attentional_posture_confidence",
            self.attentional_posture_confidence, 0.0, 1.0,
        )


# =============================================================================
# Blend-axis weights (externally motivated)
# =============================================================================
#
# Weights assigned per attention-inversion theoretical reasoning. The
# goal axis carries the most weight because goal-activation /
# goal-fulfillment pairing is the mechanism by which context-primed
# goals get fulfilled without demanding attention. Processing-fluency
# and attentional-posture are secondary disruption channels — mismatch
# on either triggers conscious awareness. Register, primary-metaphor,
# and temporal-horizon are tertiary continuity axes.
#
# Weights are a flag: ``a14_compromises.BLEND_FIT_WEIGHTS_UNVALIDATED``.
# Empirical calibration on pilot data is a named successor slice.

_BLEND_AXIS_WEIGHTS: Mapping[str, float] = {
    "goal":    0.30,
    "metaphor": 0.20,
    "fluency": 0.15,
    "posture": 0.15,
    "register": 0.10,
    "horizon": 0.10,
}


# =============================================================================
# BlendFitDecomposition — per-axis attribution
# =============================================================================


@dataclass(frozen=True)
class BlendFitDecomposition:
    """Per-axis attribution of a blend_fit score.

    ``per_axis_alignment``: raw alignment [0, 1] for each axis before
    confidence weighting.
    ``per_axis_weight``: effective weight = nominal_weight ×
    page_confidence × creative_confidence. Sums of weights may be
    below 1.0 when confidences are low.
    ``per_axis_contribution``: alignment × weight, summing to the
    final blend_fit scalar (modulo float accumulation).
    ``total_effective_weight``: sum of per_axis_weight. When zero,
    blend_fit falls back to 0.5 (neutral) rather than 0 — zero
    effective weight means "no information," not "bad fit."
    """
    per_axis_alignment: Dict[str, float]
    per_axis_weight: Dict[str, float]
    per_axis_contribution: Dict[str, float]
    total_effective_weight: float


# =============================================================================
# compute_blend_fit — the primitive
# =============================================================================


def compute_blend_fit(
    creative: CreativeFeatureBundle,
    page: PageFeatureBundle,
) -> tuple[float, BlendFitDecomposition]:
    """Compute a confidence-weighted alignment score in [0, 1].

    Returns the scalar score AND a per-axis decomposition so
    downstream consumers (ILA, selection layer, adjudicator) can
    audit which axes drove the score rather than treating the scalar
    as black-box.

    Neutral fallback: when total effective weight is zero (e.g.,
    every axis has zero confidence on one side), returns 0.5 with
    an empty decomposition. This is "no information" honesty — it
    is not a good fit OR a bad fit.
    """
    alignments: Dict[str, float] = {}
    weights: Dict[str, float] = {}
    contributions: Dict[str, float] = {}

    # --- register (numeric axis) ----------------------------------------
    reg_align = 1.0 - abs(creative.register_score - page.register_score) / 2.0
    alignments["register"] = max(0.0, min(1.0, reg_align))
    weights["register"] = (
        _BLEND_AXIS_WEIGHTS["register"]
        * creative.register_confidence
        * page.register_confidence
    )

    # --- primary_metaphor (8-axis cosine similarity, rescaled) ---------
    metaphor_align = _rescaled_cosine(
        creative.primary_metaphor_axes,
        page.primary_metaphor_axes,
    )
    alignments["metaphor"] = metaphor_align
    weights["metaphor"] = (
        _BLEND_AXIS_WEIGHTS["metaphor"]
        * creative.primary_metaphor_confidence
        * page.primary_metaphor_confidence
    )

    # --- goal (page ACTIVATES, creative FULFILLS) ----------------------
    # min_overlap / total_activation: when page activates goals at
    # mass A and creative fulfills at mass F, the effective fulfillment
    # is min(A, F) summed across goals. Normalized by total activation.
    total_activation = sum(page.goal_activation_profile.values())
    if total_activation > 0.0:
        min_overlap = sum(
            min(
                page.goal_activation_profile.get(k, 0.0),
                creative.goal_fulfillment_profile.get(k, 0.0),
            )
            for k in GOAL_ACTIVATION_KEYS
        )
        goal_align = min_overlap / total_activation
    else:
        # Page activates nothing — neutral.
        goal_align = 0.5
    alignments["goal"] = max(0.0, min(1.0, goal_align))
    weights["goal"] = (
        _BLEND_AXIS_WEIGHTS["goal"]
        * creative.goal_fulfillment_confidence
        * page.goal_activation_confidence
    )

    # --- temporal_horizon ----------------------------------------------
    horizon_align = 1.0 - abs(
        creative.temporal_horizon_induction - page.temporal_horizon_induction
    ) / 2.0
    alignments["horizon"] = max(0.0, min(1.0, horizon_align))
    weights["horizon"] = (
        _BLEND_AXIS_WEIGHTS["horizon"]
        * creative.temporal_horizon_confidence
        * page.temporal_horizon_confidence
    )

    # --- processing_fluency --------------------------------------------
    fluency_align = 1.0 - abs(
        creative.processing_fluency - page.processing_fluency
    )
    alignments["fluency"] = max(0.0, min(1.0, fluency_align))
    weights["fluency"] = (
        _BLEND_AXIS_WEIGHTS["fluency"]
        * creative.processing_fluency_confidence
        * page.processing_fluency_confidence
    )

    # --- attentional_posture -------------------------------------------
    # Page attentional_posture is not in PageFeatureBundle (it ships on
    # ArticleObservation and in downstream PagePsychologicalProfile).
    # For MV blend_fit, we pair creative.attentional_posture against
    # page's attentional_posture if the caller supplies it via the
    # page bundle's posture_shim (see docstring below). When absent,
    # posture contributes zero weight.
    page_posture = getattr(page, "attentional_posture", None)
    page_posture_confidence = getattr(
        page, "attentional_posture_confidence", 0.0,
    )
    if page_posture is not None:
        posture_align = 1.0 - abs(
            creative.attentional_posture - page_posture
        ) / 2.0
        alignments["posture"] = max(0.0, min(1.0, posture_align))
        weights["posture"] = (
            _BLEND_AXIS_WEIGHTS["posture"]
            * creative.attentional_posture_confidence
            * page_posture_confidence
        )
    else:
        alignments["posture"] = 0.5  # neutral — no signal either way
        weights["posture"] = 0.0

    # --- aggregate -----------------------------------------------------
    total_weight = sum(weights.values())
    if total_weight <= 0.0:
        decomposition = BlendFitDecomposition(
            per_axis_alignment=alignments,
            per_axis_weight=weights,
            per_axis_contribution={k: 0.0 for k in alignments},
            total_effective_weight=0.0,
        )
        return (0.5, decomposition)

    for axis in alignments:
        contributions[axis] = (alignments[axis] * weights[axis]) / total_weight

    score = sum(contributions.values())
    # Guard against accumulation past bounds.
    score = max(0.0, min(1.0, score))

    decomposition = BlendFitDecomposition(
        per_axis_alignment=alignments,
        per_axis_weight=weights,
        per_axis_contribution=contributions,
        total_effective_weight=total_weight,
    )
    return (score, decomposition)


# =============================================================================
# Helpers
# =============================================================================


def _rescaled_cosine(a: List[float], b: List[float]) -> float:
    """Cosine similarity rescaled from [-1, 1] to [0, 1]. Returns 0.5
    (neutral) when either vector has zero norm."""
    if len(a) != len(b):
        return 0.5
    dot = sum(ai * bi for ai, bi in zip(a, b))
    norm_a = math.sqrt(sum(ai * ai for ai in a))
    norm_b = math.sqrt(sum(bi * bi for bi in b))
    if norm_a <= 0.0 or norm_b <= 0.0:
        return 0.5
    cos = dot / (norm_a * norm_b)
    # Clamp then rescale [-1, 1] → [0, 1].
    cos = max(-1.0, min(1.0, cos))
    return (cos + 1.0) / 2.0


def _require_range(name: str, value: float, lo: float, hi: float) -> None:
    if not (lo <= value <= hi):
        raise ValueError(f"{name} {value} outside [{lo}, {hi}]")


__all__ = [
    "BlendFitDecomposition",
    "CreativeFeatureBundle",
    "compute_blend_fit",
]
