"""F3 — Bilateral edge metaphor dimension.

Computes the alignment between a buyer's NATURAL metaphor frame
(F1: BuyerMetaphorBundle from review scoring) and a brand's
ATTEMPTED activation frame (F2: BrandCopyMetaphorBundle from copy
scoring). The result extends the existing 20-dim bilateral edge
profile with a 21st dimension: ``metaphor_alignment``.

Math (all defensible, no invented weights):

    cosine_similarity = (buyer · brand_copy) / (|buyer| · |brand_copy|)
        Standard cosine on the 8-axis vectors. Bounded [0, 1] for
        non-negative axis values (which our [0, 1] scoring guarantees).
        Defined as 0 when either norm is zero (no signal on that side).

    density_agreement = 1 − |buyer_density − brand_density|
        Bounded [0, 1]. Captures intensity match: high cosine with
        mismatched densities means "they reach for the same axes but
        with very different metaphor saturation" — which is a weaker
        alignment claim than matched densities.

    confidence_floor = min(buyer_confidence, brand_confidence)
        Gates the alignment claim by the weaker side's evidence. We
        do NOT claim alignment we don't have evidence for on both
        halves. min() is the standard min-evidence composition; sum
        or product would over-claim.

    metaphor_alignment = cosine_similarity * confidence_floor

The bilateral-edge dimension exposed downstream is
``metaphor_alignment``. ``density_agreement`` is exposed separately so
consumers that want to use it can; we don't pre-compose it into the
single scalar because that would bake in a specific weighting.

Returns ``MetaphorAlignmentResult.neutral()`` on every failure path
(missing inputs, zero norm, axis count mismatch). Confidence on
neutral is 0 — same A14 discipline as F1 / F2.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import List, Optional

from adam.intelligence.brand_copy_metaphor_scoring import BrandCopyMetaphorBundle
from adam.intelligence.buyer_metaphor_scoring import BuyerMetaphorBundle
from adam.intelligence.pages.claude_feature_scoring import (
    PRIMARY_METAPHOR_AXIS_NAMES,
)

logger = logging.getLogger(__name__)


_NUM_AXES = len(PRIMARY_METAPHOR_AXIS_NAMES)


@dataclass
class MetaphorAlignmentResult:
    """Bilateral metaphor alignment between buyer and brand_copy.

    metaphor_alignment is the headline scalar that goes into the
    21st bilateral-edge dimension (joins regulatory_fit,
    construal_fit, narrative_transport, etc.). The other fields are
    diagnostics that callers who want richer analysis can use.
    """

    metaphor_alignment: float = 0.0          # the bilateral-edge value
    cosine_similarity: float = 0.0           # raw cosine before gating
    density_agreement: float = 0.0           # 1 − |density_a − density_b|
    confidence: float = 0.0                  # min(buyer_conf, brand_conf)
    per_axis_closeness: List[float] = field(default_factory=list)
    # 1 − |a_i − b_i| per axis; same axis order as PRIMARY_METAPHOR_AXIS_NAMES.
    # Diagnostic — exposes WHICH axes drove the alignment.

    buyer_id: str = ""
    asin: str = ""
    brand_id: str = ""

    @classmethod
    def neutral(
        cls, buyer_id: str = "", asin: str = "", brand_id: str = "",
    ) -> "MetaphorAlignmentResult":
        return cls(
            metaphor_alignment=0.0,
            cosine_similarity=0.0,
            density_agreement=0.0,
            confidence=0.0,
            per_axis_closeness=[0.0] * _NUM_AXES,
            buyer_id=buyer_id,
            asin=asin,
            brand_id=brand_id,
        )

    def to_edge_dimensions(self) -> dict:
        """Render as a partial edge_dimensions dict for merge into the
        canonical buyer_edge_dimensions consumed by
        compute_decision_probability and the cascade."""
        return {"metaphor_alignment": round(self.metaphor_alignment, 4)}


def _cosine_similarity(a: List[float], b: List[float]) -> float:
    """Cosine similarity for two non-negative axis vectors.

    Returns 0.0 when either norm is zero (no signal). Result in
    [0, 1] for the [0, 1] axis range our metaphor scorers produce.
    """
    if len(a) != len(b):
        return 0.0
    dot = sum(ai * bi for ai, bi in zip(a, b))
    norm_a = math.sqrt(sum(ai * ai for ai in a))
    norm_b = math.sqrt(sum(bi * bi for bi in b))
    if norm_a < 1e-9 or norm_b < 1e-9:
        return 0.0
    sim = dot / (norm_a * norm_b)
    # Floating-point can push slightly past 1; clamp.
    return max(0.0, min(1.0, sim))


def compute_metaphor_alignment(
    buyer: Optional[BuyerMetaphorBundle],
    brand: Optional[BrandCopyMetaphorBundle],
) -> MetaphorAlignmentResult:
    """Compute bilateral metaphor alignment.

    Returns ``MetaphorAlignmentResult.neutral()`` when:
      - either bundle is None
      - either bundle has confidence == 0 (no signal)
      - axis vectors have wrong length (schema drift)

    The alignment is gated by the weaker side's evidence — we don't
    claim a high alignment when one side has zero scoring confidence.
    """
    if buyer is None or brand is None:
        return MetaphorAlignmentResult.neutral()

    if buyer.confidence <= 0.0 or brand.confidence <= 0.0:
        # No usable evidence on at least one side — the discipline
        # anchor: don't fabricate alignment.
        return MetaphorAlignmentResult.neutral(
            buyer_id=buyer.buyer_id,
            asin=brand.asin,
            brand_id=brand.brand_id,
        )

    a = buyer.primary_metaphor_axes
    b = brand.primary_metaphor_axes

    if len(a) != _NUM_AXES or len(b) != _NUM_AXES:
        # Schema drift — log and return neutral.
        logger.warning(
            "Metaphor alignment: axis count mismatch (buyer=%d brand=%d expected=%d)",
            len(a), len(b), _NUM_AXES,
        )
        return MetaphorAlignmentResult.neutral(
            buyer_id=buyer.buyer_id,
            asin=brand.asin,
            brand_id=brand.brand_id,
        )

    cos = _cosine_similarity(a, b)
    density_agree = 1.0 - abs(buyer.metaphor_density - brand.metaphor_density)
    density_agree = max(0.0, min(1.0, density_agree))
    confidence_floor = min(buyer.confidence, brand.confidence)

    # Per-axis closeness for diagnostic exposure
    per_axis = [
        1.0 - abs(ai - bi)
        for ai, bi in zip(a, b)
    ]

    metaphor_alignment = cos * confidence_floor

    return MetaphorAlignmentResult(
        metaphor_alignment=round(metaphor_alignment, 4),
        cosine_similarity=round(cos, 4),
        density_agreement=round(density_agree, 4),
        confidence=round(confidence_floor, 4),
        per_axis_closeness=[round(v, 4) for v in per_axis],
        buyer_id=buyer.buyer_id,
        asin=brand.asin,
        brand_id=brand.brand_id,
    )
