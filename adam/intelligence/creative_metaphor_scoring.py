"""F4 — Creative-side primary-metaphor scoring (8 axes per generated variant).

Closes the third corner of Sprint F's primary-metaphor track:

    F1 buyer-side (review):
        "What does the buyer's review reveal about their NATURAL
        metaphor frame?" — TRAIT EXPRESSION
    F2 brand-copy-side (product copy):
        "What metaphor frame is the brand's copy TRYING to activate?"
        — ATTEMPTED ACTIVATION
    F4 creative-side (this module — generated ad copy):
        "What metaphor frame does the GENERATED CREATIVE actually
        DELIVER?" — DELIVERED ACTIVATION

Why F4 is a distinct perspective from F2:
    F2 scores what the BRAND WANTS to activate via static product
    copy. F4 scores what the GENERATED CREATIVE actually does. Creatives
    are OUTPUTS of generation (Claude, templates, RANKING-selected
    variants) and can DRIFT from brand intent. F4 is the verification
    step: does the creative we're about to ship actually deliver the
    metaphor frame we intended? When F4 disagrees with F2, that's a
    signal — generation drift, template misalignment, or RANKING
    picking the wrong axis.

Shape parallel to F1 / F2: 8 canonical axes from PRIMARY_METAPHOR_AXIS_NAMES,
metaphor_density, confidence, plus creative-specific identifiers.
Reuses the canonical axis names so F3's bilateral alignment math
applies identically (creative × buyer → delivered-vs-trait alignment).

Audit finding (2026-04-27): blend_fit.py explicitly named F4 as a
follow-up at lines 48-51:
    'Creative-side feature scorer. The CreativeFeatureBundle shape is
     defined here; the scorer that produces it from creative text /
     copy / CTA is a named follow-up (mirror of
     adam/intelligence/pages/claude_feature_scoring.py).'
F4 is the named slice. The CreativeMetaphorBundle shape here is the
metaphor portion of the larger CreativeFeatureBundle; an adapter
helper produces the CreativeFeatureBundle's metaphor fields from this
bundle so the broader blend_fit pipeline can consume both.

Returns ``CreativeMetaphorBundle.neutral()`` on every failure path —
same A14 discipline as F1 / F2.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from adam.intelligence.buyer_metaphor_scoring import BuyerMetaphorBundle
from adam.intelligence.pages.claude_feature_scoring import (
    PRIMARY_METAPHOR_AXIS_NAMES,
)

logger = logging.getLogger(__name__)


_NUM_AXES = len(PRIMARY_METAPHOR_AXIS_NAMES)


@dataclass
class CreativeMetaphorBundle:
    """One generated creative's primary-metaphor profile.

    Same shape as F1's BuyerMetaphorBundle and F2's
    BrandCopyMetaphorBundle: 8 axes + density + confidence. Identifier
    fields name the creative variant (creative_id), the brand it's
    serving (brand_id), and the originating decision (decision_id)
    so the bundle can be joined back to the cascade decision that
    produced it.
    """

    primary_metaphor_axes: List[float] = field(
        default_factory=lambda: [0.0] * _NUM_AXES,
    )
    metaphor_density: float = 0.0
    confidence: float = 0.0
    creative_id: str = ""
    variant_id: str = ""
    brand_id: str = ""
    decision_id: str = ""

    @classmethod
    def neutral(
        cls, creative_id: str = "", variant_id: str = "",
        brand_id: str = "", decision_id: str = "",
    ) -> "CreativeMetaphorBundle":
        """Honest 'no signal' output. confidence=0 → downstream ignores."""
        return cls(
            primary_metaphor_axes=[0.0] * _NUM_AXES,
            metaphor_density=0.0,
            confidence=0.0,
            creative_id=creative_id,
            variant_id=variant_id,
            brand_id=brand_id,
            decision_id=decision_id,
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
        creative_id: str = "",
        variant_id: str = "",
        brand_id: str = "",
        decision_id: str = "",
    ) -> "CreativeMetaphorBundle":
        """Parse a Claude JSON response into a validated bundle.

        Tolerant of either a wrapped 'primary_metaphor' shape or a
        flat shape — same semantics as F1 / F2.
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
            creative_id=creative_id,
            variant_id=variant_id,
            brand_id=brand_id,
            decision_id=decision_id,
        )
        bundle.validate()
        return bundle


_SYSTEM_PROMPT = """\
You are a research-grounded analyst scoring AD CREATIVE COPY along
the 8 primary-metaphor axes from cognitive-linguistics literature
(Lakoff & Johnson 1980; physical-to-social neural recycling;
cross-linguistic universals).

The QUESTION is: what metaphor frame does this GENERATED CREATIVE
actually DELIVER? This is delivered activation — the metaphor frame
the creative's headline + body + CTA jointly invoke when read.

Distinct from page-side (contextual priming of what surrounding
content does to a reader) and from brand-product-copy-side (what
the brand WANTS to activate via static descriptive copy). A
creative is the OUTPUT of generation; it can drift from brand
intent. Score what THIS specific creative does, not what the brand
wished for.

Discipline:
- Every score comes with a confidence in [0, 1]. Short creatives
  (just a headline) reveal less metaphor than longer copy with body
  and CTA — return lower confidence accordingly.
- Score what the COPY is doing, not what it is ABOUT. A car
  creative whose body says "Discover the road less traveled"
  reaches for path metaphor (journey, exploration); one that just
  lists "0-60 in 4.5s, 350hp" scores zero metaphor density.
- Return ONLY the JSON object specified. No prose outside it.
- Neutral is an honest output when evidence is thin.
"""


_USER_PROMPT_TEMPLATE = """\
Score the following ad creative along the 8 primary-metaphor axes —
what metaphor frame does the creative DELIVER.

HEADLINE: {headline}

BODY: {body}

CTA: {cta}

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
    "density": float in [0, 1],
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

If the creative is empty or too short / too generic to score, return
near-zero density and confidence below 0.3.
"""


async def score_creative_metaphors(
    claude_client: Any,
    headline: str = "",
    body: str = "",
    cta: str = "",
    creative_id: str = "",
    variant_id: str = "",
    brand_id: str = "",
    decision_id: str = "",
    model: Optional[str] = None,
    max_chars_per_field: int = 2000,
) -> CreativeMetaphorBundle:
    """Score one generated creative on the 8 metaphor axes.

    Soft-fail: any error path returns
    ``CreativeMetaphorBundle.neutral()`` with confidence=0 so
    downstream alignment / aggregate updates ignore the observation.

    ``max_chars_per_field`` truncates each field independently; ad
    copy is typically short (headlines ≤ 100 chars, body ≤ 300,
    CTA ≤ 50), so 2000 per field is a generous ceiling.
    """
    h = (headline or "").strip()[:max_chars_per_field]
    b = (body or "").strip()[:max_chars_per_field]
    c = (cta or "").strip()[:max_chars_per_field]

    if not (h or b or c):
        return CreativeMetaphorBundle.neutral(
            creative_id=creative_id, variant_id=variant_id,
            brand_id=brand_id, decision_id=decision_id,
        )

    user_prompt = _USER_PROMPT_TEMPLATE.format(
        headline=h or "(none)",
        body=b or "(none)",
        cta=c or "(none)",
    )

    try:
        response = await claude_client.complete_structured(
            prompt=user_prompt,
            output_schema={"type": "object"},
            system=_SYSTEM_PROMPT,
            model=model,
        )
    except Exception as exc:  # noqa: BLE001 — API failure must not cascade
        logger.warning("score_creative_metaphors Claude call failed: %s", exc)
        return CreativeMetaphorBundle.neutral(
            creative_id=creative_id, variant_id=variant_id,
            brand_id=brand_id, decision_id=decision_id,
        )

    if not response:
        return CreativeMetaphorBundle.neutral(
            creative_id=creative_id, variant_id=variant_id,
            brand_id=brand_id, decision_id=decision_id,
        )

    try:
        return CreativeMetaphorBundle.from_claude_response(
            response,
            creative_id=creative_id, variant_id=variant_id,
            brand_id=brand_id, decision_id=decision_id,
        )
    except Exception as exc:
        logger.warning(
            "score_creative_metaphors parse failed: %s; response=%s",
            exc, response,
        )
        return CreativeMetaphorBundle.neutral(
            creative_id=creative_id, variant_id=variant_id,
            brand_id=brand_id, decision_id=decision_id,
        )


# =============================================================================
# Creative × Buyer alignment — the natural F4 use case
# =============================================================================
# Reuses the canonical math from F3 (cosine similarity gated by min-
# confidence). The DELIVERED activation (creative) vs the buyer's
# NATURAL frame (review) — high alignment means the creative reaches
# for the metaphor frame the buyer naturally uses; low alignment is
# generation drift or a buyer-creative mismatch the RANKING layer
# should fix.


@dataclass
class CreativeBuyerAlignmentResult:
    """Alignment between a generated creative and a buyer's metaphor frame."""

    metaphor_alignment: float = 0.0
    cosine_similarity: float = 0.0
    density_agreement: float = 0.0
    confidence: float = 0.0
    per_axis_closeness: List[float] = field(default_factory=list)
    creative_id: str = ""
    variant_id: str = ""
    buyer_id: str = ""

    @classmethod
    def neutral(
        cls, creative_id: str = "", variant_id: str = "",
        buyer_id: str = "",
    ) -> "CreativeBuyerAlignmentResult":
        return cls(
            metaphor_alignment=0.0,
            cosine_similarity=0.0,
            density_agreement=0.0,
            confidence=0.0,
            per_axis_closeness=[0.0] * _NUM_AXES,
            creative_id=creative_id,
            variant_id=variant_id,
            buyer_id=buyer_id,
        )


def compute_creative_buyer_alignment(
    creative: Optional[CreativeMetaphorBundle],
    buyer: Optional[BuyerMetaphorBundle],
) -> CreativeBuyerAlignmentResult:
    """Compute alignment between generated creative and buyer.

    Same math as F3's compute_metaphor_alignment (cosine similarity
    gated by min-confidence). Different bundle types but identical
    axis space — F1 / F2 / F4 all reuse PRIMARY_METAPHOR_AXIS_NAMES.

    Returns neutral when either bundle is missing, has zero
    confidence, or has wrong axis count (schema drift).
    """
    if creative is None or buyer is None:
        return CreativeBuyerAlignmentResult.neutral()

    if creative.confidence <= 0.0 or buyer.confidence <= 0.0:
        return CreativeBuyerAlignmentResult.neutral(
            creative_id=creative.creative_id,
            variant_id=creative.variant_id,
            buyer_id=buyer.buyer_id,
        )

    a = creative.primary_metaphor_axes
    b = buyer.primary_metaphor_axes

    if len(a) != _NUM_AXES or len(b) != _NUM_AXES:
        logger.warning(
            "Creative-buyer alignment: axis count mismatch (creative=%d buyer=%d expected=%d)",
            len(a), len(b), _NUM_AXES,
        )
        return CreativeBuyerAlignmentResult.neutral(
            creative_id=creative.creative_id,
            variant_id=creative.variant_id,
            buyer_id=buyer.buyer_id,
        )

    cos = _cosine_similarity(a, b)
    density_agree = 1.0 - abs(creative.metaphor_density - buyer.metaphor_density)
    density_agree = max(0.0, min(1.0, density_agree))
    confidence_floor = min(creative.confidence, buyer.confidence)
    per_axis = [1.0 - abs(ai - bi) for ai, bi in zip(a, b)]

    metaphor_alignment = cos * confidence_floor

    return CreativeBuyerAlignmentResult(
        metaphor_alignment=round(metaphor_alignment, 4),
        cosine_similarity=round(cos, 4),
        density_agreement=round(density_agree, 4),
        confidence=round(confidence_floor, 4),
        per_axis_closeness=[round(v, 4) for v in per_axis],
        creative_id=creative.creative_id,
        variant_id=creative.variant_id,
        buyer_id=buyer.buyer_id,
    )


def _cosine_similarity(a: List[float], b: List[float]) -> float:
    """Cosine similarity for two non-negative axis vectors.

    Identical math to metaphor_alignment._cosine_similarity. Reproduced
    here to keep this module's dependency surface minimal — both
    callers compute the same primitive on the same axis space.
    """
    if len(a) != len(b):
        return 0.0
    dot = sum(ai * bi for ai, bi in zip(a, b))
    norm_a = math.sqrt(sum(ai * ai for ai in a))
    norm_b = math.sqrt(sum(bi * bi for bi in b))
    if norm_a < 1e-9 or norm_b < 1e-9:
        return 0.0
    return max(0.0, min(1.0, dot / (norm_a * norm_b)))


# =============================================================================
# Adapter for blend_fit consumers
# =============================================================================


def to_creative_feature_metaphor_fields(
    bundle: CreativeMetaphorBundle,
) -> Dict[str, Any]:
    """Convert a CreativeMetaphorBundle into the metaphor portion of
    a CreativeFeatureBundle (defined in adam/intelligence/blend_fit.py).

    blend_fit.CreativeFeatureBundle has fields:
        primary_metaphor_density, primary_metaphor_axes,
        primary_metaphor_confidence
    Returns a dict with those keys so callers building a full
    CreativeFeatureBundle can splice the F4 output into the metaphor
    portion without coupling F4 to the larger bundle's other fields
    (register / goal_fulfillment / temporal_horizon / processing_fluency
    / attentional_posture — separate scorers per blend_fit's NOT-IN-
    THIS-SLICE list).
    """
    return {
        "primary_metaphor_density": bundle.metaphor_density,
        "primary_metaphor_axes": list(bundle.primary_metaphor_axes),
        "primary_metaphor_confidence": bundle.confidence,
    }
