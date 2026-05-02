# =============================================================================
# Section 6.5 — Reactance-risk pre-publication scorer
# Location: adam/intelligence/reactance_risk_scorer.py
# =============================================================================
"""Deterministic reactance-risk scorer for pre-publication creative gating.

Per directive Section 6.5 (lines 811-820):

    "In addition to fluency floor (Spine #4), every generated creative is
     scored independently for reactance risk:
       — Persuasion-intensity / explicitness markers ('only,' 'must,'
         'limited time,' 'act now,' urgency cues).
       — Pressure-language density.
       — Override-of-user-control cues (countdown timers, scarcity claims,
         social-proof manipulation).
     Reactance score is one of the dimensions that the BCF heterogeneous-
     effects model can identify as a moderator. Above a threshold reactance
     score, the creative is rejected at offline-pipeline time and never
     enters the live candidate pool. This is a second architectural defense
     (alongside the fluency floor) of the attention-inversion principle."

Closes the named sibling tag from
``creative_upload_pipeline.py:71-73``:

    "Reactance-risk independent scorer (Section 6.5 line 1067) — every
     uploaded creative should pass reactance scoring before reaching this
     pipeline. Sibling slice."

WHY THIS EXISTS

A creative that a generator produced may be technically aligned with
mechanism + metaphor + posture but still trigger reactance via persuasion-
intensity markers — "act now," "limited time," countdown timers, etc.
The fluency floor catches *posture × mechanism* mismatch; this scorer
catches *language-pressure × all-postures* mismatch. Both are second
defenses of attention-inversion (Foundation §7).

THE PRIMITIVE

  * ``ReactanceRiskResult`` — frozen dataclass: total_score (0..1) +
    per-dimension subscores (explicitness / pressure / control_override) +
    flagged_markers list (token, category) for diagnostics.
  * ``score_reactance_risk(text)`` — pure function, no I/O. Tokenizes,
    matches against three marker lists, computes density, returns
    ReactanceRiskResult.
  * ``REACTANCE_REJECT_THRESHOLD`` — default 0.50 (calibration_pending).
    Above this → reject before upload. Tunable via env override or
    upload_creative kwarg.

DISCIPLINE (B3-LUXY a/b/c/d)
----------------------------

(a) Citations: directive Section 6.5 lines 811-820 + Section 6.4 line 805
    (named in creative-generation scoring) + creative_upload_pipeline.py
    honest tag (named sibling at line 71-73). Marker lists derived from
    the directive's literal examples + Brehm's reactance theory taxonomy
    (autonomy threats: ought, must, should, only, force, require) + Cialdini
    pressure-tactics inventory (scarcity / urgency / social-proof
    manipulation cues).

(b) Tests pin: empty / whitespace text → score 0; single explicitness
    marker → contributes to explicitness subscore; multiple pressure
    markers → density-scaled; control-override marker (countdown) →
    flagged in control_override; flagged_markers list contains
    (token, category) tuples; total_score in [0, 1]; ReactanceRiskResult
    frozen; default threshold = 0.50; pure function (idempotent on
    same input).

(c) calibration_pending=True. v0.1 threshold 0.50 conservative. LUXY
    pilot via:
      (i) BCF heterogeneous-effects model on per-creative reactance
          score → backfire-conversion correlation.
      (ii) CMO review-flagged creatives that pass v0.1 threshold but
          induce reactance during walkthrough.
    A14 flag: SECTION_6_5_REACTANCE_THRESHOLD_PILOT_PENDING.

(d) Honest tags — what is NOT in this slice (named successors):

    * Visual / non-text reactance markers (countdown timer animations,
      flashing UI). v0.1 scores TEXT only — banner copy, native ad
      headline, video voiceover transcript. Visual scoring requires
      a separate frame analyzer. Sibling slice.
    * Per-archetype reactance threshold tuning (defensive_skeptic
      may need a stricter threshold than naive_starter). v0.1 uses
      one threshold. Sibling.
    * Reactance × posture interaction. The directive's BCF
      heterogeneous-effects model sits in the offline analytics
      pipeline; v0.1 is the static scorer. Sibling slice surfaces
      the interaction at decision time.
    * Multilingual / translated marker lists. v0.1 is English only.
    * NLP-sophisticated context awareness (e.g., "act now" in a
      Shakespeare quote should not trigger). v0.1 is pure keyword
      density. Sibling slice for context-aware NLP.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# A14 SECTION_6_5_REACTANCE_THRESHOLD_PILOT_PENDING
REACTANCE_REJECT_THRESHOLD: float = 0.50


# =============================================================================
# Marker dictionaries — three categories per directive's enumeration
# =============================================================================
#
# All markers lower-cased; the scorer lower-cases input before matching.
# Multi-word phrases (e.g., "limited time") are matched as exact phrases.

# Explicitness markers — directive line 813:
#   "Persuasion-intensity / explicitness markers (only, must, limited
#    time, act now, urgency cues)."
EXPLICITNESS_MARKERS: Tuple[str, ...] = (
    "only",
    "must",
    "have to",
    "need to",
    "should",
    "ought",
    "force",
    "require",
    "demand",
    "act now",
    "buy now",
    "click now",
    "subscribe now",
    "limited time",
    "limited offer",
    "today only",
    "expires today",
    "expires soon",
    "while supplies last",
    "right now",
    "immediate",
    "instant",
    "don't miss",
    "do not miss",
    "miss out",
)

# Pressure-language markers — overlap with explicitness but emphasize
# urgency intensity rather than bare imperative.
PRESSURE_MARKERS: Tuple[str, ...] = (
    "hurry",
    "rush",
    "deadline",
    "running out",
    "selling fast",
    "almost gone",
    "last chance",
    "final hours",
    "final days",
    "final call",
    "don't wait",
    "do not wait",
    "now or never",
    "before it's too late",
    "before its too late",
    "before it is too late",
)

# Control-override markers — directive line 815:
#   "Override-of-user-control cues (countdown timers, scarcity claims,
#    social-proof manipulation)."
CONTROL_OVERRIDE_MARKERS: Tuple[str, ...] = (
    "countdown",
    "ticking",
    "seconds left",
    "minutes left",
    "hours left",
    "days left",
    "only 1 left",
    "only 2 left",
    "only 3 left",
    "only 4 left",
    "only 5 left",
    "1 left",
    "2 left",
    "3 left",
    "selling out",
    "sold out soon",
    # Social-proof manipulation cues
    "everyone is",
    "everybody is",
    "all your friends",
    "millions are",
    "thousands are",
    "people just like you",
    "join the rush",
)


# =============================================================================
# Result
# =============================================================================


@dataclass(frozen=True)
class ReactanceRiskResult:
    """Outcome of one reactance-risk score.

    ``total_score``: composite reactance risk in [0, 1]. Above
        ``REACTANCE_REJECT_THRESHOLD`` → reject before publication.
    ``explicitness_score``: subscore [0, 1] from explicitness markers.
    ``pressure_score``: subscore [0, 1] from pressure-language markers.
    ``control_override_score``: subscore [0, 1] from control-override
        cues.
    ``flagged_markers``: list of (token, category) tuples — diagnostic /
        operator-explanation surface.
    ``n_tokens``: word count (for density calculations).
    """

    total_score: float
    explicitness_score: float
    pressure_score: float
    control_override_score: float
    flagged_markers: List[Tuple[str, str]] = field(default_factory=list)
    n_tokens: int = 0


def _tokenize(text: str) -> List[str]:
    """Lowercase, strip punctuation, split on whitespace."""
    if not text:
        return []
    cleaned = re.sub(r"[^\w\s']", " ", text.lower())
    return [t for t in cleaned.split() if t]


def _count_phrase_hits(
    lowered_text: str, markers: Tuple[str, ...],
) -> List[Tuple[str, int]]:
    """For each marker, return (marker, count) — using word-boundary
    regex so 'must' doesn't match 'mustard'."""
    hits: List[Tuple[str, int]] = []
    for m in markers:
        # Use word-boundary regex; multi-word phrases match exactly.
        pattern = r"\b" + re.escape(m) + r"\b"
        n = len(re.findall(pattern, lowered_text))
        if n > 0:
            hits.append((m, n))
    return hits


def score_reactance_risk(
    text: str,
    *,
    explicitness_weight: float = 0.40,
    pressure_weight: float = 0.30,
    control_override_weight: float = 0.30,
) -> ReactanceRiskResult:
    """Compute reactance risk for ad copy text.

    Args:
        text: ad copy text (banner / native / voiceover transcript).
        explicitness_weight / pressure_weight / control_override_weight:
            mixing weights for the three subscores. Default tuned to
            directive's emphasis (explicitness slightly above the others
            since it's listed first + most operationally common).

    Returns:
        ReactanceRiskResult. total_score = weighted average of
        subscores. Each subscore = min(1.0, hits / SATURATION_K)
        — 3 hits in a category saturate the subscore at 1.0. This
        count-based saturation matches reactance-theory mechanism
        better than density-based scaling: a 30-word ad with 3
        "act now"/"limited time"/"hurry" pressure markers triggers
        the same psychological response as a 100-word ad with the
        same 3 markers — total length doesn't dilute the signal.

        Short-copy floor: when n_tokens < 5, we additionally divide
        each subscore by 2.0 — single-word ad with one urgency
        marker shouldn't saturate immediately (false-positive risk).
    """
    if not text or not text.strip():
        return ReactanceRiskResult(
            total_score=0.0,
            explicitness_score=0.0,
            pressure_score=0.0,
            control_override_score=0.0,
            flagged_markers=[],
            n_tokens=0,
        )

    tokens = _tokenize(text)
    n_tokens = len(tokens)
    lowered = text.lower()

    explicitness_hits = _count_phrase_hits(lowered, EXPLICITNESS_MARKERS)
    pressure_hits = _count_phrase_hits(lowered, PRESSURE_MARKERS)
    control_hits = _count_phrase_hits(lowered, CONTROL_OVERRIDE_MARKERS)

    expl_total = sum(c for _, c in explicitness_hits)
    pres_total = sum(c for _, c in pressure_hits)
    ctrl_total = sum(c for _, c in control_hits)

    # Count-based saturation: 3 hits per category saturate the subscore.
    SATURATION_K = 3.0
    explicitness_score = min(1.0, expl_total / SATURATION_K)
    pressure_score = min(1.0, pres_total / SATURATION_K)
    control_override_score = min(1.0, ctrl_total / SATURATION_K)

    # Short-copy false-positive guard: ultra-short ads with one marker
    # shouldn't saturate by default.
    if n_tokens < 5:
        explicitness_score *= 0.5
        pressure_score *= 0.5
        control_override_score *= 0.5

    weight_sum = (
        explicitness_weight + pressure_weight + control_override_weight
    )
    if weight_sum <= 0:
        weight_sum = 1.0
    total_score = (
        explicitness_weight * explicitness_score
        + pressure_weight * pressure_score
        + control_override_weight * control_override_score
    ) / weight_sum
    total_score = max(0.0, min(1.0, total_score))

    flagged: List[Tuple[str, str]] = []
    for tok, _ in explicitness_hits:
        flagged.append((tok, "explicitness"))
    for tok, _ in pressure_hits:
        flagged.append((tok, "pressure"))
    for tok, _ in control_hits:
        flagged.append((tok, "control_override"))

    return ReactanceRiskResult(
        total_score=total_score,
        explicitness_score=explicitness_score,
        pressure_score=pressure_score,
        control_override_score=control_override_score,
        flagged_markers=flagged,
        n_tokens=n_tokens,
    )


def passes_reactance_check(
    text: str,
    *,
    threshold: float = REACTANCE_REJECT_THRESHOLD,
) -> Tuple[bool, ReactanceRiskResult]:
    """Convenience wrapper for the upload pipeline gate.

    Returns ``(passes, result)`` — passes is True when
    total_score < threshold. The result is always returned for
    diagnostic / logging.
    """
    result = score_reactance_risk(text)
    return (result.total_score < threshold, result)
