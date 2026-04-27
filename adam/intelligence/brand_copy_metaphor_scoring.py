"""F2 — Brand-copy-side primary-metaphor scoring (8 axes per copy block).

Scores brand product copy (title + features + description) along the
canonical 8 primary-metaphor axes. Reuses
``PRIMARY_METAPHOR_AXIS_NAMES`` from
``adam/intelligence/pages/claude_feature_scoring.py`` — buyer-side
(F1), page-side (existing), and now brand-copy-side (F2) all live in
the SAME 8-axis space. That shared space is what makes F3's
bilateral edge metaphor dimension meaningful.

Three semantic perspectives, same axes:

    F1 buyer-side (review):
        "What does the buyer's language reveal about the BUYER's
        natural metaphor frame?" — trait expression
    Page-side (article body):
        "How does this article PRIME each axis in a reader?"
        — contextual activation
    F2 brand-copy-side (this module):
        "What metaphor frame is the brand's copy trying to ACTIVATE
        in the buyer?" — attempted activation

The bilateral edge in F3 will compute alignment between the buyer's
TRAIT vector (F1) and the brand's ATTEMPTED-ACTIVATION vector (F2).
High alignment = brand is reaching for the metaphor frame the buyer
naturally uses. Low alignment = brand is reaching for a different
frame — signal for either reframing the copy or routing to a
buyer with a matching frame.

Returns ``BrandCopyMetaphorBundle.neutral()`` on every failure path.
Same A14 discipline as F1: silent failures must not contaminate
the brand-side metaphor profile; neutral-with-low-confidence is
honest output when scoring fails.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from adam.intelligence.pages.claude_feature_scoring import (
    PRIMARY_METAPHOR_AXIS_NAMES,
)

logger = logging.getLogger(__name__)


_NUM_AXES = len(PRIMARY_METAPHOR_AXIS_NAMES)


@dataclass
class BrandCopyMetaphorBundle:
    """One brand's primary-metaphor profile from product copy scoring.

    Mirrors BuyerMetaphorBundle's shape (F1) so F3 can compute
    bilateral alignment via dot product.
    """

    primary_metaphor_axes: List[float] = field(
        default_factory=lambda: [0.0] * _NUM_AXES,
    )
    metaphor_density: float = 0.0
    confidence: float = 0.0
    asin: str = ""
    brand_id: str = ""

    @classmethod
    def neutral(cls, asin: str = "", brand_id: str = "") -> "BrandCopyMetaphorBundle":
        """Honest 'no signal' output. confidence=0 → downstream ignores."""
        return cls(
            primary_metaphor_axes=[0.0] * _NUM_AXES,
            metaphor_density=0.0,
            confidence=0.0,
            asin=asin,
            brand_id=brand_id,
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
        asin: str = "",
        brand_id: str = "",
    ) -> "BrandCopyMetaphorBundle":
        """Parse a Claude JSON response into a validated bundle.

        Tolerant of either a wrapped 'primary_metaphor' shape or a
        flat shape. Raises ValueError on a malformed response;
        caller catches and returns neutral().
        """
        if not isinstance(response, dict):
            raise ValueError(f"response is not a dict: {type(response)}")

        block = response.get("primary_metaphor", response)
        if not isinstance(block, dict):
            raise ValueError(f"primary_metaphor block is not a dict: {type(block)}")

        axes_dict = block.get("axes")
        if not isinstance(axes_dict, dict):
            raise ValueError(
                f"primary_metaphor.axes missing or not a dict: {type(axes_dict)}"
            )

        axes_vector: List[float] = []
        for axis_name in PRIMARY_METAPHOR_AXIS_NAMES:
            v = axes_dict.get(axis_name, 0.0)
            try:
                axes_vector.append(max(0.0, min(1.0, float(v))))
            except (TypeError, ValueError):
                raise ValueError(
                    f"axes.{axis_name}={v!r} not coercible to float"
                )

        density = max(0.0, min(1.0, float(block.get("density", 0.0))))
        confidence = max(0.0, min(1.0, float(block.get("confidence", 0.0))))

        bundle = cls(
            primary_metaphor_axes=axes_vector,
            metaphor_density=density,
            confidence=confidence,
            asin=asin,
            brand_id=brand_id,
        )
        bundle.validate()
        return bundle


_SYSTEM_PROMPT = """\
You are a research-grounded analyst scoring brand product copy
(title + features + description) along the 8 primary-metaphor axes
from cognitive-linguistics literature (Lakoff & Johnson 1980;
physical-to-social neural recycling; cross-linguistic universals).

The QUESTION is: what metaphor frame is the brand's copy TRYING TO
ACTIVATE in the reader's mind? This is attempted activation, NOT
contextual priming (page-side) and NOT trait expression
(buyer-review side).

Discipline:
- Every score comes with a confidence in [0, 1]. When the copy is
  too short or too generic to reveal an attempted metaphor frame,
  return near-zero density AND a low confidence — do not invent.
- Score what the BRAND's copy is REACHING FOR. A skincare brand
  saying "transform your morning ritual" reaches for path / vertical
  metaphor (journey, elevation); one that just lists ingredients
  without metaphoric framing scores low density.
- Return ONLY the JSON object specified. No prose outside it.
- Neutral is an honest output when evidence is thin.
"""


_USER_PROMPT_TEMPLATE = """\
Score the following brand product copy along the 8 primary-metaphor
axes — what metaphor frame is the brand TRYING TO ACTIVATE.

PRODUCT TITLE: {title}

FEATURES:
{features}

DESCRIPTION:
{description}

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
    "density": float in [0, 1],      // overall metaphor saturation
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

If the copy is empty or too short / too generic to score, return
near-zero density and confidence below 0.3.
"""


async def score_brand_copy_metaphors(
    claude_client: Any,
    title: str = "",
    features: str = "",
    description: str = "",
    asin: str = "",
    brand_id: str = "",
    model: Optional[str] = None,
    max_chars: int = 5000,
) -> BrandCopyMetaphorBundle:
    """Score one brand's product copy with Claude on the 8 metaphor axes.

    Soft-fail: any error path returns
    ``BrandCopyMetaphorBundle.neutral()`` with confidence=0 so
    downstream Welford / aggregate updates ignore the observation.

    ``max_chars`` truncates each input field to keep total prompt
    bounded. Brand copy is typically short (titles ≤ 200 chars,
    features 5-10 bullet points, description ≤ 2000 chars), so the
    5000 default is a generous ceiling.
    """
    title_clean = (title or "").strip()
    features_clean = (features or "").strip()
    description_clean = (description or "").strip()

    # All-empty input → neutral
    if not (title_clean or features_clean or description_clean):
        return BrandCopyMetaphorBundle.neutral(asin=asin, brand_id=brand_id)

    user_prompt = _USER_PROMPT_TEMPLATE.format(
        title=title_clean[:max_chars] or "(none)",
        features=features_clean[:max_chars] or "(none)",
        description=description_clean[:max_chars] or "(none)",
    )

    try:
        response = await claude_client.complete_structured(
            prompt=user_prompt,
            output_schema={"type": "object"},
            system=_SYSTEM_PROMPT,
            model=model,
        )
    except Exception as exc:  # noqa: BLE001 — API failure must not cascade
        logger.warning("score_brand_copy_metaphors Claude call failed: %s", exc)
        return BrandCopyMetaphorBundle.neutral(asin=asin, brand_id=brand_id)

    if not response:
        return BrandCopyMetaphorBundle.neutral(asin=asin, brand_id=brand_id)

    try:
        return BrandCopyMetaphorBundle.from_claude_response(
            response, asin=asin, brand_id=brand_id,
        )
    except Exception as exc:
        logger.warning(
            "score_brand_copy_metaphors parse failed: %s; response=%s",
            exc, response,
        )
        return BrandCopyMetaphorBundle.neutral(asin=asin, brand_id=brand_id)
