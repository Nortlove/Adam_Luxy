# =============================================================================
# Section 6.4 — Primary-metaphor coherence scorer
# Location: adam/intelligence/metaphor_coherence_scorer.py
# =============================================================================
"""Deterministic primary-metaphor coherence scorer.

Per directive Section 6.4 (line 1064): "Multi-dimensional scoring
(metaphor coherence, mechanism activation, predicted fluency,
reactance risk)." Slice 18 shipped the reactance-risk scorer; this
slice ships metaphor coherence — the second of the four scoring
dimensions that the offline-pipeline creative-generation loop
applies before a variant enters the candidate pool.

Per Phase 10 line 1135 (RED criterion #6): "Any creative in rotation
fails primary-metaphor coherence in spot check despite passing the
offline-pipeline scorer." The check function
``check_metaphor_coherence_failed`` already exists in
``phase_10_launch_sequence.py:239``; this slice ships the producer
that decides "did the creative pass the spot check."

CANONICAL AXES

The 8-axis primary-metaphor vocabulary is the canonical one from
``adam/intelligence/pages/claude_feature_scoring.py:80-89``:

    warmth, distance, vertical, solidity, containment,
    force, path, closeness

Reusing the same axis names + ordering keeps Buyer / Brand / Creative
metaphor bundles in one shared schema (see creative_metaphor_scoring +
buyer_metaphor_scoring siblings).

WHAT COHERENCE MEANS

A creative is *coherent* with its declared ``primary_metaphor`` axis
when the language in the copy invokes that axis more than the other
seven. v0.1 operationalizes this as a relative-density check:

    coherence_score = target_axis_hits / max(total_axis_hits, MIN_HITS)

When 80%+ of metaphor markers in the text belong to the target axis,
coherence is high (≈ 1.0). When markers are spread evenly across
axes, coherence is low (≈ 1/8 = 0.125). The threshold for "passes
spot check" is 0.50 — the target axis must dominate.

This is a TEXT-LEVEL deterministic check; the directive's "primary-
metaphor coherence with the target" (line 805) at decision time
reads :Creative.primary_metaphor_axes vector (the 8-dim continuous
score) which is produced via Claude analysis — that's a SEPARATE
sibling pathway. v0.1 here is the keyword-density scorer suitable
for offline-pipeline pre-publication gating.

THE PRIMITIVE

  * ``METAPHOR_COHERENCE_THRESHOLD`` — default 0.50
    (calibration_pending).
  * ``MetaphorCoherenceResult`` — frozen dataclass: coherence_score
    + per-axis hit counts + target_axis + flagged_markers list.
  * ``score_metaphor_coherence(text, target_metaphor)`` — pure
    function; returns the result.
  * ``passes_metaphor_coherence_check(text, target_metaphor)`` —
    convenience wrapper for the upload gate. Returns
    (passes, result).

DISCIPLINE (B3-LUXY a/b/c/d)
----------------------------

(a) Citations: directive Section 6.4 line 1064 (named scoring
    dimension) + Phase 10 line 1135 (RED criterion #6 — metaphor
    coherence spot check) + creative_upload_pipeline named-sibling
    flow. The 8-axis vocabulary is the canonical one from
    ``claude_feature_scoring.py:80-89`` (matches Buyer / Brand /
    Creative metaphor bundles). Marker words per axis are derived
    from the standard primary-metaphor literature (Lakoff & Johnson
    1980; Lakoff 1993; Grady 1997; Boroditsky 2000) — the cross-
    linguistic universal markers that the metaphor frame neurally
    recycles into. NOT a novel mapping; canonical source.

(b) Tests pin: empty / whitespace text → coherence 0; single
    target-axis marker (n=1) → coherence above threshold (target is
    100% of activations); cross-axis marker → coherence below
    threshold; unknown target_metaphor → returns 0.0 + raises in
    strict mode; per-axis hit counts populated; threshold = 0.50;
    flagged_markers contains (token, axis) tuples; pure function;
    MetaphorCoherenceResult is frozen.

(c) calibration_pending=True. v0.1 marker dictionaries are starter
    sets per axis (8-15 markers each, English only). LUXY pilot
    via:
      (i) CMO spot-check disagreements with v0.1 scorer surface
          marker gaps.
      (ii) Claude-API metaphor scoring (creative_metaphor_scoring.py)
          provides the continuous-score "ground truth" against which
          v0.1 calibrates.
    A14 flag: SECTION_6_4_METAPHOR_COHERENCE_PILOT_PENDING.

(d) Honest tags — what is NOT in this slice (named successors):

    * Continuous 8-dim metaphor vector via Claude API. This slice
      is the discrete keyword-density gate; the continuous vector
      lives in creative_metaphor_scoring + claude_feature_scoring.
    * Multilingual marker lists (English only).
    * NLP context-aware exclusions (idioms / quotations / negation).
    * Compound-marker phrase patterns ("on the same wavelength" →
      closeness; "uphill battle" → vertical+force interaction).
      v0.1 scores single tokens + small phrases.
    * Per-archetype coherence threshold tuning.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from adam.intelligence.pages.claude_feature_scoring import (
    PRIMARY_METAPHOR_AXIS_NAMES,
)

logger = logging.getLogger(__name__)


# A14 SECTION_6_4_METAPHOR_COHERENCE_PILOT_PENDING
METAPHOR_COHERENCE_THRESHOLD: float = 0.50

# Minimum hits before coherence ratio is meaningful — short copy
# with one accidental marker shouldn't saturate.
MIN_TOTAL_HITS_FOR_COHERENCE: int = 2


# =============================================================================
# Per-axis marker dictionaries
# =============================================================================
#
# The 8 primary-metaphor axes from claude_feature_scoring.py:80-89.
# Markers per axis derived from the cross-linguistic primary-metaphor
# literature (Lakoff & Johnson 1980; Grady 1997; Boroditsky 2000).
# All lower-cased; matched as word-bounded tokens in the scorer.

_METAPHOR_MARKERS: Dict[str, Tuple[str, ...]] = {
    "warmth": (
        "warm", "warmth", "hot", "heat", "cozy", "comforting",
        "embrace", "tender", "affectionate", "intimate",
        "friendly", "welcoming", "loving", "cold", "chilly",
        "frigid", "frosty", "icy",  # negative-pole markers
    ),
    "distance": (
        "near", "far", "close", "distant", "remote", "removed",
        "afar", "approach", "withdraw", "reach", "spanning",
        "gap", "miles", "stretches",
    ),
    "vertical": (
        "up", "down", "high", "low", "rise", "fall", "climb",
        "descend", "elevated", "lifted", "lowered", "peak",
        "summit", "bottom", "above", "below", "uphill",
        "downhill", "soar", "plunge", "tower", "topple",
    ),
    "solidity": (
        "solid", "firm", "stable", "rock", "concrete", "sturdy",
        "strong", "weak", "fragile", "brittle", "shaky",
        "rigid", "robust", "foundation", "bedrock", "anchor",
        "weight", "weighty", "substantial",
    ),
    "containment": (
        "in", "out", "inside", "outside", "within", "without",
        "contain", "container", "enclose", "envelop", "encompass",
        "trap", "trapped", "free", "release", "boundary",
        "wall", "barrier", "shelter", "protect", "shielded",
    ),
    "force": (
        "push", "pull", "drive", "press", "pressure", "thrust",
        "compel", "force", "exert", "strain", "yield", "resist",
        "overpower", "overwhelm", "powerful", "strong",
        "irresistible",
    ),
    "path": (
        "path", "road", "way", "journey", "route", "trail",
        "course", "direction", "step", "stride", "advance",
        "progress", "forward", "ahead", "onward", "destination",
        "milestone", "trek", "navigate", "travel",
    ),
    "closeness": (
        "together", "apart", "joined", "bonded", "connected",
        "intimate", "close-knit", "tight", "loose", "separate",
        "united", "merged", "linked", "attached", "estranged",
        "kindred", "alongside",
    ),
}


# Sanity check — every canonical axis has a marker list.
for _axis in PRIMARY_METAPHOR_AXIS_NAMES:
    if _axis not in _METAPHOR_MARKERS:
        raise RuntimeError(
            f"Slice 19 marker dict missing canonical axis '{_axis}' "
            f"— must mirror PRIMARY_METAPHOR_AXIS_NAMES exactly."
        )


@dataclass(frozen=True)
class MetaphorCoherenceResult:
    """Outcome of one metaphor-coherence score.

    ``target_metaphor``: the declared primary metaphor for the
        creative (one of PRIMARY_METAPHOR_AXIS_NAMES).
    ``coherence_score``: target_axis_hits / max(total_hits,
        MIN_TOTAL_HITS_FOR_COHERENCE) ∈ [0, 1]. Above
        METAPHOR_COHERENCE_THRESHOLD → passes.
    ``axis_hits``: per-axis hit count. Sum ≥ total_hits when a
        single token matches multiple axes (rare but possible —
        e.g., "tight" matches both solidity and closeness in some
        contexts; v0.1 scores it on every matching axis).
    ``target_hits``: hits on the target axis (subset of axis_hits).
    ``total_hits``: sum of axis_hits values.
    ``flagged_markers``: list of (token, axis) tuples — diagnostic.
    ``n_tokens``: word count.
    ``threshold_passed``: convenience flag.
    """

    target_metaphor: str
    coherence_score: float
    axis_hits: Dict[str, int]
    target_hits: int
    total_hits: int
    flagged_markers: List[Tuple[str, str]] = field(default_factory=list)
    n_tokens: int = 0
    threshold_passed: bool = False


def _tokenize_count(text: str) -> int:
    """Count words via simple whitespace-after-punctuation-strip."""
    if not text:
        return 0
    cleaned = re.sub(r"[^\w\s']", " ", text.lower())
    return len([t for t in cleaned.split() if t])


def _count_hits_per_axis(
    lowered_text: str,
) -> Tuple[Dict[str, int], List[Tuple[str, str]]]:
    """For each axis, count how many of its markers appear (word-
    bounded) in the text. Returns (axis_hits, flagged_markers)."""
    axis_hits: Dict[str, int] = {a: 0 for a in PRIMARY_METAPHOR_AXIS_NAMES}
    flagged: List[Tuple[str, str]] = []
    for axis_name in PRIMARY_METAPHOR_AXIS_NAMES:
        markers = _METAPHOR_MARKERS[axis_name]
        for m in markers:
            pattern = r"\b" + re.escape(m) + r"\b"
            n = len(re.findall(pattern, lowered_text))
            if n > 0:
                axis_hits[axis_name] += n
                flagged.append((m, axis_name))
    return axis_hits, flagged


def score_metaphor_coherence(
    text: str,
    target_metaphor: str,
    *,
    threshold: float = METAPHOR_COHERENCE_THRESHOLD,
    strict_target: bool = False,
) -> MetaphorCoherenceResult:
    """Score primary-metaphor coherence of creative copy.

    Args:
        text: ad copy text.
        target_metaphor: declared primary-metaphor axis. Must be one
            of PRIMARY_METAPHOR_AXIS_NAMES (case-insensitive). When
            unknown axis is passed and ``strict_target=True``, raises
            ValueError; default ``strict_target=False`` returns a
            zero-score result with target_metaphor preserved as input.
        threshold: pass threshold (default 0.50).
        strict_target: see above.

    Returns:
        MetaphorCoherenceResult.

    Behavior:
      * Empty / whitespace text → coherence 0, threshold not passed.
      * Unknown axis (not in canonical 8) → coherence 0; raises in
        strict mode (default off — caller may have type errors).
      * total_hits < MIN_TOTAL_HITS_FOR_COHERENCE → coherence ratio
        denominator is floored at MIN_TOTAL_HITS_FOR_COHERENCE so
        accidental single markers don't saturate.
      * coherence_score in [0, 1] always.
    """
    target_norm = (target_metaphor or "").strip().lower()
    if target_norm not in PRIMARY_METAPHOR_AXIS_NAMES:
        if strict_target:
            raise ValueError(
                f"Unknown target_metaphor '{target_metaphor}' — must "
                f"be one of {PRIMARY_METAPHOR_AXIS_NAMES}"
            )
        return MetaphorCoherenceResult(
            target_metaphor=target_metaphor or "",
            coherence_score=0.0,
            axis_hits={a: 0 for a in PRIMARY_METAPHOR_AXIS_NAMES},
            target_hits=0,
            total_hits=0,
            flagged_markers=[],
            n_tokens=_tokenize_count(text or ""),
            threshold_passed=False,
        )

    if not text or not text.strip():
        return MetaphorCoherenceResult(
            target_metaphor=target_norm,
            coherence_score=0.0,
            axis_hits={a: 0 for a in PRIMARY_METAPHOR_AXIS_NAMES},
            target_hits=0,
            total_hits=0,
            flagged_markers=[],
            n_tokens=0,
            threshold_passed=False,
        )

    n_tokens = _tokenize_count(text)
    lowered = text.lower()

    axis_hits, flagged = _count_hits_per_axis(lowered)
    total_hits = sum(axis_hits.values())
    target_hits = axis_hits[target_norm]

    denom = max(total_hits, MIN_TOTAL_HITS_FOR_COHERENCE)
    coherence = target_hits / float(denom) if denom > 0 else 0.0
    coherence = max(0.0, min(1.0, coherence))

    return MetaphorCoherenceResult(
        target_metaphor=target_norm,
        coherence_score=coherence,
        axis_hits=axis_hits,
        target_hits=target_hits,
        total_hits=total_hits,
        flagged_markers=flagged,
        n_tokens=n_tokens,
        threshold_passed=coherence >= threshold,
    )


def passes_metaphor_coherence_check(
    text: str,
    target_metaphor: str,
    *,
    threshold: float = METAPHOR_COHERENCE_THRESHOLD,
) -> Tuple[bool, MetaphorCoherenceResult]:
    """Convenience wrapper for the upload pipeline gate.

    Returns ``(passes, result)``. passes=True iff
    coherence_score >= threshold.
    """
    result = score_metaphor_coherence(
        text, target_metaphor, threshold=threshold,
    )
    return (result.threshold_passed, result)
