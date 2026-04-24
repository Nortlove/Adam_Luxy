"""Claude-scored page features — #7 MV slice.

Produces the five remaining page-side features that compose with the
attentional_posture dimension shipped in ``ba39535`` to form the
Claude-scored six-feature bundle named in the 2026-04-24 pilot plan:

1. ``register`` — linguistic register scalar [-1, 1] (informal → formal)
   plus a small-vocabulary category label.
2. ``primary_metaphor_density`` — overall density [0, 1] plus the
   8-axis profile populating the existing stub field on Author /
   Publication / Article nodes (see
   ``adam/intelligence/pages/entity_graph.py``). Chris's axis vocabulary:
   warmth, distance, vertical, solidity, containment, force, path,
   closeness.
3. ``goal_activation_profile`` — dict over the 8 goal ids in
   ``adam.intelligence.goal_activation.GOAL_TAXONOMY`` with scores
   [0, 1] naming the activation strength of each nonconscious goal by
   the page's content (Bargh auto-motive frame).
4. ``temporal_horizon_induction`` — construal-level scalar [-1, 1]
   (near / concrete → far / abstract). Feeds the rec-class pipeline's
   posture-band conditioning via ``PrimingCondition`` extensions in a
   later slice.
5. ``processing_fluency_profile`` — fluency scalar [0, 1] (hard → easy).
   Upstream of the per-cell processing-depth priors named in
   ``a14_compromises.DEPTH_PRIOR_UNVALIDATED`` as Tier 2 item 0a; the
   scoring primitive must ship before per-cell priors can be computed.

Scope of THIS slice
-------------------

- ``PageFeatureBundle`` dataclass with validated fields.
- ``score_page_features(claude_client, title, body, ...)`` — single
  Claude call per article returning the full bundle.
- Deterministic parsing with neutral fallbacks on malformed response
  (A1 / A5 discipline — must not fabricate scores).

NOT in this slice (named successors):

- Neo4j migration 029: add new properties to Author / Publication /
  Section / Topic / Article nodes + indexes.
- ``entity_graph.py`` Welford updates for the new features.
- Cascade consumption in ``page_edge_bridge.py`` (shift matrices per
  feature analogous to the attentional_posture shifts).
- Article-text crawl / extraction wiring — this module accepts
  pre-extracted title + body + optional dek and assumes the caller
  handles upstream fetching.

Frame discipline (orientation A1, A5, A6)
-----------------------------------------

- Scores are produced by Claude on article text. The caller's
  responsibility is clean text input; the module's responsibility is
  a stable prompt + strict schema validation + neutral fallback.
- Temperature 0.3 (inherited from ``complete_structured``) to reduce
  variance without collapsing onto rote outputs.
- Every numeric field has explicit bounds; invalid values from Claude
  are clamped to bounds, not silently accepted.
- No citation strings are produced. Claude's justifications (if any)
  are stripped before the bundle is returned — the bundle carries
  scores only, not prose claims. Future slices add evidence hooks.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Tuple

from adam.intelligence.goal_activation import GOAL_TAXONOMY
from adam.llm.client import ClaudeClient

logger = logging.getLogger(__name__)


# =============================================================================
# Constants — stable feature vocabularies
# =============================================================================


PRIMARY_METAPHOR_AXIS_NAMES: Tuple[str, ...] = (
    "warmth",
    "distance",
    "vertical",
    "solidity",
    "containment",
    "force",
    "path",
    "closeness",
)
"""Canonical axis ordering — must match the zero-stub vector shape in
``adam/intelligence/pages/entity_graph.py`` (PRIMARY_METAPHOR_AXES = 8)
and the Author / Publication node property
``primary_metaphor_axes: List[float]``. Do not reorder; downstream
consumers index by position."""


REGISTER_CATEGORIES: Tuple[str, ...] = (
    "academic",
    "journalistic",
    "editorial",
    "conversational",
    "tabloid",
    "technical",
    "marketing",
    "narrative",
)


# Defensive copy of goal ids at import time (GOAL_TAXONOMY is a dict;
# iteration order is insertion order in Python 3.7+, but we freeze it
# here to make the dependency explicit).
GOAL_ACTIVATION_KEYS: Tuple[str, ...] = tuple(sorted(GOAL_TAXONOMY.keys()))


# =============================================================================
# PageFeatureBundle — scored output
# =============================================================================


@dataclass(frozen=True)
class PageFeatureBundle:
    """Five scored features for a single article.

    Confidence fields are separate ``[0, 1]`` scalars so downstream
    Welford updates can weight observations by scoring certainty. All
    bounds-violating fields are clamped in construction via
    ``from_claude_response``.
    """

    register_score: float  # [-1, 1] informal → formal
    register_category: str  # one of REGISTER_CATEGORIES
    register_confidence: float  # [0, 1]

    primary_metaphor_density: float  # [0, 1]
    primary_metaphor_axes: List[float]  # length 8, each [0, 1]
    primary_metaphor_confidence: float  # [0, 1]

    goal_activation_profile: Dict[str, float]  # keys from GOAL_ACTIVATION_KEYS, values [0, 1]
    goal_activation_confidence: float  # [0, 1]

    temporal_horizon_induction: float  # [-1, 1] near → far
    temporal_horizon_confidence: float  # [0, 1]

    processing_fluency: float  # [0, 1] hard → easy
    processing_fluency_confidence: float  # [0, 1]

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
            "primary_metaphor_density", self.primary_metaphor_density, 0.0, 1.0,
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

        if set(self.goal_activation_profile.keys()) != set(GOAL_ACTIVATION_KEYS):
            missing = set(GOAL_ACTIVATION_KEYS) - set(self.goal_activation_profile.keys())
            extra = set(self.goal_activation_profile.keys()) - set(GOAL_ACTIVATION_KEYS)
            raise ValueError(
                f"goal_activation_profile keys mismatch. "
                f"missing={sorted(missing)}, extra={sorted(extra)}"
            )
        for goal_id, v in self.goal_activation_profile.items():
            _require_range(
                f"goal_activation_profile[{goal_id}]", v, 0.0, 1.0,
            )
        _require_range(
            "goal_activation_confidence",
            self.goal_activation_confidence, 0.0, 1.0,
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

    @staticmethod
    def neutral() -> "PageFeatureBundle":
        """Return the all-neutral bundle used as the Claude-unavailable
        fallback. Every confidence is 0.0 so downstream Welford updates
        correctly skip / zero-weight this observation."""
        return PageFeatureBundle(
            register_score=0.0,
            register_category="journalistic",
            register_confidence=0.0,
            primary_metaphor_density=0.0,
            primary_metaphor_axes=[0.0] * len(PRIMARY_METAPHOR_AXIS_NAMES),
            primary_metaphor_confidence=0.0,
            goal_activation_profile={k: 0.0 for k in GOAL_ACTIVATION_KEYS},
            goal_activation_confidence=0.0,
            temporal_horizon_induction=0.0,
            temporal_horizon_confidence=0.0,
            processing_fluency=0.5,
            processing_fluency_confidence=0.0,
        )

    @classmethod
    def from_claude_response(
        cls, response: Mapping[str, Any],
    ) -> "PageFeatureBundle":
        """Build a bundle from Claude's structured JSON response.

        Out-of-range numeric values are clamped; unknown enum values
        (register_category) fall back to ``"journalistic"``; missing
        fields fall back to their neutral equivalents with confidence
        0.0 on that feature. Validation still runs at the end — any
        invariant that cannot be recovered from fallback raises.
        """
        reg = response.get("register") or {}
        meta = response.get("primary_metaphor") or {}
        goals_resp = response.get("goal_activation_profile") or {}
        goals_conf = response.get("goal_activation_confidence", 0.0)
        temp = response.get("temporal_horizon") or {}
        flu = response.get("processing_fluency") or {}

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

        bundle = cls(
            register_score=register_score,
            register_category=register_category,
            register_confidence=register_confidence,
            primary_metaphor_density=density,
            primary_metaphor_axes=axes,
            primary_metaphor_confidence=meta_conf,
            goal_activation_profile=goal_profile,
            goal_activation_confidence=goal_conf,
            temporal_horizon_induction=horizon,
            temporal_horizon_confidence=horizon_conf,
            processing_fluency=fluency,
            processing_fluency_confidence=fluency_conf,
        )
        bundle.validate()
        return bundle


# =============================================================================
# Scoring prompt + schema
# =============================================================================


_SYSTEM_PROMPT = """\
You are a research-grounded analyst scoring web-article content along five
psycholinguistic dimensions drawn from cognitive-psychology and linguistics
literature. Score what the text is ACTUALLY DOING, not what it is ABOUT.

Discipline:
- Every score comes with a confidence in [0, 1]. When you can't tell from
  the text, return a near-neutral score AND a low confidence — do not
  invent scores.
- Return ONLY the JSON object specified by the schema. No prose outside it.
- Neutral is an honest output when evidence is thin.
"""


_USER_PROMPT_TEMPLATE = """\
Score the following article along five dimensions.

TITLE: {title}
{dek_line}
BODY:
{body}

Return a JSON object with exactly this shape:

{{
  "register": {{
    "score": float in [-1, 1],      // -1 fully informal, +1 fully formal
    "category": one of [{register_categories}],
    "confidence": float in [0, 1]
  }},

  "primary_metaphor": {{
    // Primary metaphor theory (physical-to-social neural recycling,
    // cross-linguistic universals — Lakoff & Johnson 1980 lineage).
    // Rate how frequently the text invokes each primary-metaphor axis.
    "density": float in [0, 1],     // overall metaphor saturation
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

  // Nonconscious goal activation (Bargh auto-motive model). Score how
  // strongly the article's content would PRIME each goal in a reader.
  // All scores in [0, 1]; many articles activate multiple goals at
  // different strengths.
  "goal_activation_profile": {{
{goal_lines}
  }},
  "goal_activation_confidence": float in [0, 1],

  "temporal_horizon": {{
    // Construal-level induction (Trope & Liberman). -1 = near / concrete
    // / immediate-framing. +1 = far / abstract / distant-framing.
    "induction": float in [-1, 1],
    "confidence": float in [0, 1]
  }},

  "processing_fluency": {{
    // Reber's processing-fluency construct. 0 = hard-to-process
    // (dense, jargon-heavy, syntactically complex). 1 = easy to process
    // (clear, well-structured, familiar vocabulary).
    "score": float in [0, 1],
    "confidence": float in [0, 1]
  }}
}}
"""


# =============================================================================
# Scoring entry point
# =============================================================================


async def score_page_features(
    claude_client: ClaudeClient,
    title: str,
    body: str,
    dek: Optional[str] = None,
    model: Optional[str] = None,
    max_body_chars: int = 6000,
) -> PageFeatureBundle:
    """Score a single article with Claude and return a validated bundle.

    On any failure (API error, parse error, malformed response), returns
    ``PageFeatureBundle.neutral()`` — every confidence field is 0.0 so
    downstream Welford updates correctly ignore the observation.

    ``max_body_chars`` truncates long bodies to a scoring-tractable
    prefix. Research shows article openings carry the dominant signal
    for register / metaphor / goal-activation at the article level;
    6000 chars ≈ first ~1000 words is empirically the range where
    extending further yields diminishing score stability.
    """
    if not title or not title.strip():
        logger.debug("score_page_features: empty title, returning neutral")
        return PageFeatureBundle.neutral()
    if not body or not body.strip():
        logger.debug("score_page_features: empty body, returning neutral")
        return PageFeatureBundle.neutral()

    body_truncated = body.strip()[:max_body_chars]
    dek_line = f"DEK: {dek.strip()}\n" if dek and dek.strip() else ""
    register_list = ", ".join(
        f'"{c}"' for c in REGISTER_CATEGORIES
    )
    goal_lines = "\n".join(
        f'    "{goal_id}": float in [0, 1],'
        for goal_id in GOAL_ACTIVATION_KEYS
    )

    user_prompt = _USER_PROMPT_TEMPLATE.format(
        title=title.strip(),
        dek_line=dek_line,
        body=body_truncated,
        register_categories=register_list,
        goal_lines=goal_lines,
    )

    try:
        # complete_structured inlines schema-in-prompt and parses JSON.
        # We pass a minimal schema dict since our prompt already names
        # the exact output shape. The dict is used by the client for
        # its own prompt augmentation; we are already fully specific.
        response = await claude_client.complete_structured(
            prompt=user_prompt,
            output_schema={"type": "object"},
            system=_SYSTEM_PROMPT,
            model=model,
        )
    except Exception as exc:  # noqa: BLE001 — API failures must not
        # cascade into ingestion failure; return neutral and log.
        logger.warning("score_page_features Claude call failed: %s", exc)
        return PageFeatureBundle.neutral()

    if not response:
        logger.debug("score_page_features: empty response, returning neutral")
        return PageFeatureBundle.neutral()

    try:
        return PageFeatureBundle.from_claude_response(response)
    except Exception as exc:  # noqa: BLE001 — parse failure must not
        # cascade; return neutral and log for diagnostics.
        logger.warning(
            "score_page_features response parse failed: %s; response=%s",
            exc, response,
        )
        return PageFeatureBundle.neutral()


# =============================================================================
# Internal helpers
# =============================================================================


def _clamp_num(value: Any, lo: float, hi: float, default: float) -> float:
    """Coerce ``value`` to float and clamp to [lo, hi]; return
    ``default`` when coercion fails."""
    try:
        v = float(value)
    except (TypeError, ValueError):
        return default
    if v != v:  # NaN
        return default
    return max(lo, min(hi, v))


def _require_range(name: str, value: float, lo: float, hi: float) -> None:
    if not (lo <= value <= hi):
        raise ValueError(
            f"{name} {value} outside [{lo}, {hi}]"
        )


__all__ = [
    "GOAL_ACTIVATION_KEYS",
    "PRIMARY_METAPHOR_AXIS_NAMES",
    "PageFeatureBundle",
    "REGISTER_CATEGORIES",
    "score_page_features",
]
