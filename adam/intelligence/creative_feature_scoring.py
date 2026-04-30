"""Claude-scored creative features — Item 3a (blend_fit creative scorer).

Mirror of ``adam/intelligence/pages/claude_feature_scoring.py`` for the
CREATIVE side of the blend_fit pairing. Where the page-side scorer
profiles "what does this page activate / induce?", the creative-side
scorer profiles "what does this creative fulfill / project?"

Produces a ``CreativeFeatureBundle`` (defined in ``blend_fit.py``)
ready to feed into ``compute_blend_fit(creative, page)`` for the
attention-inversion blend-vs-grab assessment.

The six axes:

1. ``register`` — linguistic register scalar [-1, 1] (informal → formal)
   plus a small-vocabulary category. Pairs with page-side register so
   creatives that match page register blend; creatives that diverge grab.
2. ``primary_metaphor_density`` + 8-axis profile — Chris's vocabulary:
   warmth, distance, vertical, solidity, containment, force, path,
   closeness. Creative metaphor that resonates with page-induced
   metaphor blends; mismatch grabs.
3. ``goal_fulfillment_profile`` — for each of the 8 GOAL_ACTIVATION_KEYS,
   does this creative ANSWER the primed goal? (Page primes; creative
   fulfills.) Same key vocabulary as page-side, opposite direction.
4. ``temporal_horizon_induction`` [-1, 1] — does the creative frame
   the offer near/concrete or far/abstract?
5. ``processing_fluency`` [0, 1] — is the creative easy to process?
   (Reber 1989). Pairs with page fluency.
6. ``attentional_posture`` [-1, 1] — does the creative read as
   blend-compatible (continuous with browsing context) or
   vigilance-activating (demands evaluative attention)? This is the
   load-bearing axis for the platform's attention-inversion
   commitment — high-vigilance creatives "grab" rather than "blend"
   per project_attention_inversion_platform_core.

Frame discipline (orientation A1, A5, A6):
  * Scores produced by Claude on creative copy — no hand-fabrication.
  * Every numeric field has explicit bounds; out-of-range values clamped.
  * Failures (API error, parse error, malformed response) return
    ``CreativeFeatureBundle.neutral()`` — every confidence field 0.0
    so downstream Welford/blend_fit weights skip the observation.
  * Module is async — caller awaits.

Decision-time consumer (Primary 1, no drift):
  ``compute_blend_fit(creative_bundle, page_bundle)`` consumes the
  bundle this scorer produces. Score feeds creative-variant ranking
  in the cascade's payload-build path (Item 3b — wired separately
  when there are multiple variants per mechanism).

Discipline rule (B3-LUXY a/b/c/d):
  (a) Schema mirrors PageFeatureBundle's; pairs documented above are
      the canonical blend_fit assumption (page=activate, creative=fulfill).
  (b) Regression tests pin: neutral on empty input; clamp out-of-range;
      missing fields fall back to confidence=0; round-trip via
      from_claude_response.
  (c) calibration_pending=True. The Claude prompt's calibration
      against pilot blend-fit outcomes is a future calibration slice.
      A14 flag: CREATIVE_FEATURE_SCORING_PROMPT_UNVALIDATED.
  (d) Honest tag — attentional_posture axis on the creative side is
      a self-assessment by Claude, not the empirically-derived
      posture from PageAttentionalPostureAccumulator. Pilot data
      will reveal whether self-assessed creative posture matches
      reader-observed posture; calibration-pending.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Mapping, Optional

from adam.intelligence.blend_fit import CreativeFeatureBundle
from adam.intelligence.pages.claude_feature_scoring import (
    GOAL_ACTIVATION_KEYS,
    PRIMARY_METAPHOR_AXIS_NAMES,
    REGISTER_CATEGORIES,
    _clamp_num,
)
from adam.llm.client import ClaudeClient

logger = logging.getLogger(__name__)


# =============================================================================
# Bundle factory — neutral fallback + Claude-response parser
# =============================================================================


def neutral_creative_bundle() -> CreativeFeatureBundle:
    """All-neutral bundle — every confidence 0.0. Used as the
    Claude-unavailable / parse-failure fallback so blend_fit's
    confidence-weighted alignment correctly skips the observation."""
    return CreativeFeatureBundle(
        register_score=0.0,
        register_category="journalistic",
        register_confidence=0.0,
        primary_metaphor_density=0.0,
        primary_metaphor_axes=[0.0] * len(PRIMARY_METAPHOR_AXIS_NAMES),
        primary_metaphor_confidence=0.0,
        goal_fulfillment_profile={k: 0.0 for k in GOAL_ACTIVATION_KEYS},
        goal_fulfillment_confidence=0.0,
        temporal_horizon_induction=0.0,
        temporal_horizon_confidence=0.0,
        processing_fluency=0.5,
        processing_fluency_confidence=0.0,
        attentional_posture=0.0,
        attentional_posture_confidence=0.0,
    )


def bundle_from_claude_response(
    response: Mapping[str, Any],
) -> CreativeFeatureBundle:
    """Build a CreativeFeatureBundle from Claude's structured JSON.

    Mirrors PageFeatureBundle.from_claude_response with the creative-side
    field translations:
      * goal_activation_profile → goal_fulfillment_profile (same keys,
        opposite directional meaning)
      * adds attentional_posture (creative-side self-assessment)
    """
    reg = response.get("register") or {}
    meta = response.get("primary_metaphor") or {}
    goals_resp = response.get("goal_fulfillment_profile") or {}
    goals_conf = response.get("goal_fulfillment_confidence", 0.0)
    temp = response.get("temporal_horizon") or {}
    flu = response.get("processing_fluency") or {}
    posture = response.get("attentional_posture") or {}

    register_score = _clamp_num(
        reg.get("score", 0.0), -1.0, 1.0, default=0.0,
    )
    register_category = reg.get("category", "journalistic")
    if register_category not in REGISTER_CATEGORIES:
        logger.debug(
            "register_category %r not in allowed set; falling back",
            register_category,
        )
        register_category = "journalistic"
    register_confidence = _clamp_num(
        reg.get("confidence", 0.0), 0.0, 1.0, default=0.0,
    )

    density = _clamp_num(
        meta.get("density", 0.0), 0.0, 1.0, default=0.0,
    )
    axes_resp = meta.get("axes") or {}
    axes = [
        _clamp_num(axes_resp.get(name, 0.0), 0.0, 1.0, default=0.0)
        for name in PRIMARY_METAPHOR_AXIS_NAMES
    ]
    meta_conf = _clamp_num(
        meta.get("confidence", 0.0), 0.0, 1.0, default=0.0,
    )

    goal_profile: Dict[str, float] = {}
    for goal_id in GOAL_ACTIVATION_KEYS:
        goal_profile[goal_id] = _clamp_num(
            goals_resp.get(goal_id, 0.0), 0.0, 1.0, default=0.0,
        )
    goal_conf = _clamp_num(goals_conf, 0.0, 1.0, default=0.0)

    horizon = _clamp_num(
        temp.get("induction", 0.0), -1.0, 1.0, default=0.0,
    )
    horizon_conf = _clamp_num(
        temp.get("confidence", 0.0), 0.0, 1.0, default=0.0,
    )

    fluency = _clamp_num(
        flu.get("score", 0.5), 0.0, 1.0, default=0.5,
    )
    fluency_conf = _clamp_num(
        flu.get("confidence", 0.0), 0.0, 1.0, default=0.0,
    )

    posture_score = _clamp_num(
        posture.get("score", 0.0), -1.0, 1.0, default=0.0,
    )
    posture_conf = _clamp_num(
        posture.get("confidence", 0.0), 0.0, 1.0, default=0.0,
    )

    bundle = CreativeFeatureBundle(
        register_score=register_score,
        register_category=register_category,
        register_confidence=register_confidence,
        primary_metaphor_density=density,
        primary_metaphor_axes=axes,
        primary_metaphor_confidence=meta_conf,
        goal_fulfillment_profile=goal_profile,
        goal_fulfillment_confidence=goal_conf,
        temporal_horizon_induction=horizon,
        temporal_horizon_confidence=horizon_conf,
        processing_fluency=fluency,
        processing_fluency_confidence=fluency_conf,
        attentional_posture=posture_score,
        attentional_posture_confidence=posture_conf,
    )
    bundle.validate()
    return bundle


# =============================================================================
# Scoring prompts
# =============================================================================


_SYSTEM_PROMPT = """\
You score advertising creative copy along six psycholinguistic axes
that determine whether the creative will BLEND into reading context
or GRAB attention. Scores follow attention-inversion theory: blend
creatives feel continuous with autopilot browsing; grab creatives
demand evaluative attention.

You return strict JSON only — no prose outside the schema. Every
numeric field has explicit bounds; coerce to bounds or omit (null)
when uncertain. Confidence fields express your certainty in the
score, not the strength of the signal."""


_USER_PROMPT_TEMPLATE = """\
Score this advertising creative on six axes.

CREATIVE:
HEADLINE: {headline}
{body_line}\
{cta_line}\
BRAND: {brand}

Return JSON with EXACTLY this schema:

{{
  "register": {{
    "score": float in [-1, 1],
    "category": one of [{register_categories}],
    "confidence": float in [0, 1]
  }},
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
  }},
  "goal_fulfillment_profile": {{
{goal_lines}
  }},
  "goal_fulfillment_confidence": float in [0, 1],
  "temporal_horizon": {{
    "induction": float in [-1, 1],
    "confidence": float in [0, 1]
  }},
  "processing_fluency": {{
    "score": float in [0, 1],
    "confidence": float in [0, 1]
  }},
  "attentional_posture": {{
    "score": float in [-1, 1],
    "confidence": float in [0, 1]
  }}
}}

Axis discipline:
- register.score: -1 = highly informal (slang, exclamations); 0 = mixed;
  +1 = highly formal (academic, reportorial)
- primary_metaphor.density: 0 = no metaphor; 1 = saturated metaphor
- primary_metaphor.axes: 8 dims of Lakoff-style primary metaphor
- goal_fulfillment_profile: for each named goal, score [0, 1] how much
  this creative ANSWERS / FULFILLS that goal (NOT activates — the
  question is "does this creative resolve the named goal?")
- temporal_horizon.induction: -1 = creative frames offer as near /
  concrete (now / today); +1 = far / abstract (eventually / strategy)
- processing_fluency.score: 0 = hard to process (jargon, complex
  syntax); 1 = effortlessly processable
- attentional_posture.score: -1 = blend-compatible (reads as
  continuous with browsing context); +1 = vigilance-activating
  (demands evaluative attention to engage)
"""


# =============================================================================
# Scoring entry point
# =============================================================================


async def score_creative_features(
    claude_client: ClaudeClient,
    headline: str,
    body: str = "",
    cta: str = "",
    brand: str = "",
    model: Optional[str] = None,
) -> CreativeFeatureBundle:
    """Score a creative with Claude and return a validated bundle.

    On any failure (API error, parse error, malformed response), returns
    ``neutral_creative_bundle()`` — every confidence field 0.0 so
    downstream blend_fit correctly ignores the observation.

    Args:
        claude_client: Initialized ClaudeClient
        headline: Creative headline (required for non-neutral output)
        body: Creative body / value-prop text (optional)
        cta: Call-to-action text (optional)
        brand: Brand name for context (optional)
        model: Override the client's default model (optional)

    Returns:
        CreativeFeatureBundle with validated fields. On failure,
        a neutral bundle.
    """
    if not headline or not headline.strip():
        logger.debug("score_creative_features: empty headline, returning neutral")
        return neutral_creative_bundle()

    body_line = f"BODY: {body.strip()}\n" if body and body.strip() else ""
    cta_line = f"CTA: {cta.strip()}\n" if cta and cta.strip() else ""
    register_list = ", ".join(f'"{c}"' for c in REGISTER_CATEGORIES)
    goal_lines = "\n".join(
        f'    "{goal_id}": float in [0, 1],'
        for goal_id in GOAL_ACTIVATION_KEYS
    )

    user_prompt = _USER_PROMPT_TEMPLATE.format(
        headline=headline.strip(),
        body_line=body_line,
        cta_line=cta_line,
        brand=brand.strip() or "(unspecified)",
        register_categories=register_list,
        goal_lines=goal_lines,
    )

    try:
        response = await claude_client.complete_structured(
            prompt=user_prompt,
            output_schema={"type": "object"},
            system=_SYSTEM_PROMPT,
            model=model,
        )
    except Exception as exc:  # noqa: BLE001 — must not cascade
        logger.warning("score_creative_features Claude call failed: %s", exc)
        return neutral_creative_bundle()

    if not response:
        logger.debug("score_creative_features: empty response, returning neutral")
        return neutral_creative_bundle()

    try:
        return bundle_from_claude_response(response)
    except Exception as exc:  # noqa: BLE001 — parse failure must not cascade
        logger.warning(
            "score_creative_features response parse failed: %s; response=%s",
            exc, response,
        )
        return neutral_creative_bundle()
