"""F1 — Buyer-side primary-metaphor scoring (8 axes per review).

Scores a buyer's review text along the canonical 8 primary-metaphor axes
(Lakoff & Johnson 1980 lineage, Chris Nocera's primary-metaphor research
on physical-to-social neural recycling + cross-linguistic universals).

Reuses ``PRIMARY_METAPHOR_AXIS_NAMES`` from
``adam/intelligence/pages/claude_feature_scoring.py`` so the
buyer-side and page-side vectors live in the same axis space — that
shared space is what makes the bilateral edge metaphor dimension (F3,
queued) meaningful.

Discipline anchor — buyer-side semantics differ from page-side:

    Page-side (claude_feature_scoring.score_page_features):
        "How does this article PRIME each metaphor axis in a reader?"
        Contextual / activation question.

    Buyer-side (this module):
        "How does this review reveal the buyer's NATURAL metaphor frame?"
        Trait / expression question — what does the buyer reach for
        when narrating their experience?

Same 8 axes, same Lakoff-Johnson rubric, different question. Reusing
the shared axis vocabulary lets a future bilateral-edge metaphor
score compute (buyer_axis_vector · brand_copy_axis_vector) — meaningful
because both halves are in the same space.

Returns ``BuyerMetaphorBundle.neutral()`` on every failure path. Per
A14 discipline (silent failures must not contaminate trait estimates),
neutral-with-low-confidence is the honest output when scoring fails;
downstream consumers ignore observations whose confidence is 0.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from adam.intelligence.pages.claude_feature_scoring import (
    PRIMARY_METAPHOR_AXIS_NAMES,
)

logger = logging.getLogger(__name__)


_NUM_AXES = len(PRIMARY_METAPHOR_AXIS_NAMES)


@dataclass
class BuyerMetaphorBundle:
    """One buyer's primary-metaphor profile from review scoring.

    Mirrors the shape of PageFeatureBundle's metaphor portion so a
    future bilateral-edge computation can do dot-product comparisons
    across the same axis space.
    """

    primary_metaphor_axes: List[float] = field(
        default_factory=lambda: [0.0] * _NUM_AXES,
    )
    metaphor_density: float = 0.0
    confidence: float = 0.0
    review_id: str = ""
    buyer_id: str = ""

    @classmethod
    def neutral(cls, review_id: str = "", buyer_id: str = "") -> "BuyerMetaphorBundle":
        """Honest 'no signal' output. confidence=0 → downstream ignores."""
        return cls(
            primary_metaphor_axes=[0.0] * _NUM_AXES,
            metaphor_density=0.0,
            confidence=0.0,
            review_id=review_id,
            buyer_id=buyer_id,
        )

    def validate(self) -> None:
        if len(self.primary_metaphor_axes) != _NUM_AXES:
            raise ValueError(
                f"primary_metaphor_axes length {len(self.primary_metaphor_axes)} "
                f"!= canonical {_NUM_AXES}"
            )
        for i, v in enumerate(self.primary_metaphor_axes):
            if not (0.0 <= float(v) <= 1.0):
                raise ValueError(
                    f"primary_metaphor_axes[{PRIMARY_METAPHOR_AXIS_NAMES[i]}]={v} "
                    f"outside [0, 1]"
                )
        if not (0.0 <= self.metaphor_density <= 1.0):
            raise ValueError(
                f"metaphor_density={self.metaphor_density} outside [0, 1]"
            )
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(
                f"confidence={self.confidence} outside [0, 1]"
            )

    @classmethod
    def from_claude_response(
        cls,
        response: Dict[str, Any],
        review_id: str = "",
        buyer_id: str = "",
    ) -> "BuyerMetaphorBundle":
        """Parse a Claude JSON response into a validated bundle.

        Tolerant of the 'primary_metaphor' wrapper key but also
        accepts a flat shape. Raises ValueError on a malformed
        response — caller catches and returns neutral().
        """
        if not isinstance(response, dict):
            raise ValueError(f"response is not a dict: {type(response)}")

        # Accept either { "primary_metaphor": {...} } wrapper or flat
        block = response.get("primary_metaphor", response)
        if not isinstance(block, dict):
            raise ValueError(f"primary_metaphor block is not a dict: {type(block)}")

        axes_dict = block.get("axes")
        if not isinstance(axes_dict, dict):
            raise ValueError(
                f"primary_metaphor.axes missing or not a dict: {type(axes_dict)}"
            )

        # Build axis vector in canonical order
        axes_vector: List[float] = []
        for axis_name in PRIMARY_METAPHOR_AXIS_NAMES:
            v = axes_dict.get(axis_name, 0.0)
            try:
                axes_vector.append(max(0.0, min(1.0, float(v))))
            except (TypeError, ValueError):
                raise ValueError(
                    f"axes.{axis_name}={v!r} not coercible to float"
                )

        density = float(block.get("density", 0.0))
        density = max(0.0, min(1.0, density))
        confidence = float(block.get("confidence", 0.0))
        confidence = max(0.0, min(1.0, confidence))

        bundle = cls(
            primary_metaphor_axes=axes_vector,
            metaphor_density=density,
            confidence=confidence,
            review_id=review_id,
            buyer_id=buyer_id,
        )
        bundle.validate()
        return bundle


_SYSTEM_PROMPT = """\
You are a research-grounded analyst scoring buyer review text along
the 8 primary-metaphor axes from cognitive-linguistics literature
(Lakoff & Johnson 1980; physical-to-social neural recycling; cross-
linguistic universals).

The QUESTION is about the BUYER's natural metaphor frame — what
metaphor system they reach for when narrating their own experience —
NOT about the product or about how the review would influence a
reader.

Discipline:
- Every score comes with a confidence in [0, 1]. When the review is
  too short or too neutral to reveal a metaphor frame, return
  near-zero density AND a low confidence — do not invent.
- Score what the BUYER's language is doing, not what they are
  describing. A review of a thermometer that uses "warmth" language
  metaphorically (warm welcome, warm reception) scores high on
  warmth axis; one that just says "it reads 72°F" scores zero.
- Return ONLY the JSON object specified. No prose outside it.
- Neutral is an honest output when evidence is thin.
"""


_USER_PROMPT_TEMPLATE = """\
Score the following buyer review along the 8 primary-metaphor axes.

REVIEW TEXT:
{review}

The 8 axes (Lakoff & Johnson 1980):
- warmth: warm/cold (affection, welcome, hostility)
- distance: near/far (psychological proximity)
- vertical: up/down (status, mood, achievement)
- solidity: solid/fluid (stability, reliability)
- containment: inside/outside (belonging, exclusion)
- force: push/pull (compulsion, motivation)
- path: source/path/goal (journey, progress, arrival)
- closeness: tight/loose (intimacy, attachment)

Return JSON exactly:
{{
  "primary_metaphor": {{
    "density": float in [0, 1],      // overall metaphor saturation in the review
    "axes": {{
      "warmth": float in [0, 1],
      "distance": float in [0, 1],
      "vertical": float in [0, 1],
      "solidity": float in [0, 1],
      "containment": float in [0, 1],
      "force": float in [0, 1],
      "path": float in [0, 1],
      "closeness": float in [0, 1]
    }},
    "confidence": float in [0, 1]
  }}
}}

If the review is empty or too short to score, return near-zero density
and confidence below 0.3.
"""


async def score_review_metaphors(
    claude_client: Any,
    review_text: str,
    review_id: str = "",
    buyer_id: str = "",
    model: Optional[str] = None,
    max_chars: int = 4000,
) -> BuyerMetaphorBundle:
    """Score a single review with Claude on the 8 primary-metaphor axes.

    Soft-fail: any error path returns ``BuyerMetaphorBundle.neutral()``
    with confidence=0 so downstream Welford / aggregate updates ignore
    the observation.

    ``max_chars`` truncates long reviews; metaphor signals are usually
    detectable in the first 4000 chars (~600 words) and longer texts
    don't materially improve scoring stability.
    """
    if not review_text or not review_text.strip():
        return BuyerMetaphorBundle.neutral(review_id=review_id, buyer_id=buyer_id)

    truncated = review_text.strip()[:max_chars]
    user_prompt = _USER_PROMPT_TEMPLATE.format(review=truncated)

    try:
        response = await claude_client.complete_structured(
            prompt=user_prompt,
            output_schema={"type": "object"},
            system=_SYSTEM_PROMPT,
            model=model,
        )
    except Exception as exc:  # noqa: BLE001 — API failure must not cascade
        logger.warning("score_review_metaphors Claude call failed: %s", exc)
        return BuyerMetaphorBundle.neutral(review_id=review_id, buyer_id=buyer_id)

    if not response:
        return BuyerMetaphorBundle.neutral(review_id=review_id, buyer_id=buyer_id)

    try:
        return BuyerMetaphorBundle.from_claude_response(
            response, review_id=review_id, buyer_id=buyer_id,
        )
    except Exception as exc:
        logger.warning(
            "score_review_metaphors parse failed: %s; response=%s",
            exc, response,
        )
        return BuyerMetaphorBundle.neutral(review_id=review_id, buyer_id=buyer_id)


def aggregate_buyer_metaphor_axes(
    bundles: List[BuyerMetaphorBundle],
    min_confidence: float = 0.3,
) -> Optional[BuyerMetaphorBundle]:
    """Aggregate multiple per-review bundles into one buyer-level vector.

    Confidence-weighted mean across the 8 axes. Bundles with
    confidence below ``min_confidence`` are excluded — same discipline
    as page-side aggregation in entity_graph.py.

    Returns None when no bundle clears the confidence threshold (the
    buyer doesn't yet have enough scored reviews to support a
    metaphor profile claim).
    """
    valid = [b for b in bundles if b.confidence >= min_confidence]
    if not valid:
        return None

    total_weight = sum(b.confidence for b in valid)
    if total_weight <= 0:
        return None

    aggregated_axes = [0.0] * _NUM_AXES
    aggregated_density = 0.0
    for b in valid:
        w = b.confidence / total_weight
        for i in range(_NUM_AXES):
            aggregated_axes[i] += b.primary_metaphor_axes[i] * w
        aggregated_density += b.metaphor_density * w

    # Aggregate confidence: not the mean — sum-bounded by 1, reflecting
    # accumulation of evidence. After 5+ confident reviews we should be
    # near-saturated.
    accumulated_confidence = min(1.0, total_weight / max(1, len(valid)))

    buyer_id = valid[0].buyer_id
    return BuyerMetaphorBundle(
        primary_metaphor_axes=[round(v, 4) for v in aggregated_axes],
        metaphor_density=round(aggregated_density, 4),
        confidence=round(accumulated_confidence, 4),
        review_id=f"aggregated_{len(valid)}_reviews",
        buyer_id=buyer_id,
    )
