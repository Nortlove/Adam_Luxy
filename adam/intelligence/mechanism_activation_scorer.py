# =============================================================================
# Section 6.4 — Mechanism activation scorer
# Location: adam/intelligence/mechanism_activation_scorer.py
# =============================================================================
"""Deterministic per-mechanism activation strength scorer.

Per directive Section 6.4 line 1064 ("multi-dimensional scoring:
metaphor coherence, mechanism activation, predicted fluency,
reactance risk"). Slice 1 ships predicted fluency (mechanism × posture);
Slice 18 ships reactance risk; Slice 19 ships metaphor coherence;
this slice ships **mechanism activation** — does the creative copy
actually invoke the language of the target mechanism?

WHY THIS EXISTS

A creative tagged with ``mechanism=social_proof`` should contain
social-proof language ("everyone is", "millions trust", "bestselling")
more than language for OTHER mechanisms (scarcity / authority /
reciprocity / etc.). Without this scorer, an operator could upload a
creative whose declared mechanism doesn't match its actual copy
content — Slice 13's manifest entry would be metadata-correct but
content-wrong, and the cascade's per-mechanism posterior would
update on a creative that doesn't actually deploy that mechanism.

THE PRIMITIVE

  * ``MECHANISM_ACTIVATION_THRESHOLD`` — default 0.50.
  * ``MechanismActivationResult`` — frozen dataclass: target_mechanism,
    activation_score, target_hits, total_hits, per_mechanism_hits,
    flagged_markers, n_tokens, threshold_passed.
  * ``score_mechanism_activation(text, target_mechanism)`` — pure
    function.
  * ``passes_mechanism_activation_check`` — convenience wrapper.

Mechanism vocabulary derived from the existing ad-embedding mechanism
keywords (``embeddings/pipeline.py:603-620``) — the canonical set
that the embedding pipeline already uses for ad classification.
Reusing it keeps the scorer + the embedding side aligned on what
"social_proof activation" means at the keyword level.

DISCIPLINE (B3-LUXY a/b/c/d)
----------------------------

(a) Citations: directive Section 6.4 line 1064 (named scoring
    dimension) + ``embeddings/pipeline.py:603-620`` (canonical
    mechanism keywords already used for ad embedding). Mechanisms
    enumerate the canonical set used elsewhere in the codebase
    (social_proof, scarcity, authority, reciprocity, commitment,
    liking, unity, reason_why) — Cialdini six + reason-why +
    unity. Marker words from Cialdini 1984 + advertising-copy
    discourse analysis (e.g., Petty & Cacioppo's ELM literature on
    central-route arguments).

(b) Tests pin: empty / whitespace text → score 0; unknown
    target_mechanism → score 0 (non-strict) / raises (strict);
    on-target markers → high activation; off-target markers → low;
    per-mechanism_hits populated; threshold = 0.50; pure function;
    MechanismActivationResult is frozen; mechanism set matches
    canonical 8.

(c) calibration_pending=True. Marker dictionaries are starter sets;
    LUXY pilot calibrates against (i) Claude-API mechanism-activation
    scoring (creative_metaphor_scoring sibling), (ii) cascade's
    per-mechanism conversion correlations from real traffic.
    A14 flag: SECTION_6_4_MECHANISM_ACTIVATION_PILOT_PENDING.

(d) Honest tags — what is NOT in this slice (named successors):
    * Continuous mechanism-activation vector via Claude API (sibling
      with creative_metaphor_scoring's claude_feature_scoring path).
    * Multilingual marker lists.
    * NLP context awareness (idiom / quotation exclusion).
    * Per-archetype activation thresholds.
    * Compound-marker phrase patterns.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# A14 SECTION_6_4_MECHANISM_ACTIVATION_PILOT_PENDING
MECHANISM_ACTIVATION_THRESHOLD: float = 0.50

# Single-marker false-positive guard — same pattern as Slice 19.
MIN_TOTAL_HITS_FOR_ACTIVATION: int = 2


# =============================================================================
# Per-mechanism marker dictionaries
# =============================================================================
#
# Mirrors + extends embeddings/pipeline.py:603-620 (the canonical
# mechanism-keyword set used by the ad embedding pipeline). Markers
# match word-bounded tokens.

_MECHANISM_MARKERS: Dict[str, Tuple[str, ...]] = {
    "social_proof": (
        "everyone", "popular", "bestselling", "best seller", "best-seller",
        "trusted", "trusted by", "million", "millions", "thousands",
        "customers", "users", "loved by", "loved", "rated", "top-rated",
        "top rated", "favorite", "voted", "recommended",
        "people are", "join the",
    ),
    "scarcity": (
        "limited", "only", "last chance", "hurry", "exclusive",
        "running out", "while supplies last", "while supplies",
        "don't miss", "rare", "few left", "selling fast",
        "limited time", "limited offer", "special edition",
    ),
    "authority": (
        "expert", "experts", "doctor", "doctors", "scientist",
        "scientists", "research", "study", "studies", "proven",
        "certified", "official", "endorsed", "professional",
        "industry-leading", "award-winning", "credentialed",
        "specialists", "academy",
    ),
    "reciprocity": (
        "free", "gift", "gifted", "bonus", "complimentary", "no cost",
        "give you", "yours free", "on us", "no obligation",
        "free trial", "extra",
    ),
    "commitment": (
        "start", "begin", "first step", "simple", "easy",
        "quick", "trial", "try", "small step", "starter",
        "kick off", "begin your", "commit",
    ),
    "liking": (
        "you", "your", "friend", "together", "personal",
        "personalized", "custom", "just for you", "your style",
        "tailored", "for you",
    ),
    "unity": (
        "we", "us", "our", "ours", "together", "community", "join",
        "belong", "family", "tribe", "fellow", "shared",
        "we're", "our community",
    ),
    "reason_why": (
        "because", "that's why", "reason", "so you can",
        "which means", "therefore", "due to", "as a result",
        "this is why", "the reason",
    ),
}


CANONICAL_MECHANISMS: Tuple[str, ...] = tuple(
    sorted(_MECHANISM_MARKERS.keys())
)


@dataclass(frozen=True)
class MechanismActivationResult:
    """Outcome of one mechanism-activation score.

    ``target_mechanism``: declared mechanism for the creative.
    ``activation_score``: target_hits / max(total_hits, MIN_TOTAL_HITS)
        ∈ [0, 1].
    ``target_hits``: hits on the target mechanism.
    ``total_hits``: sum of all per-mechanism hits.
    ``per_mechanism_hits``: per-mechanism count.
    ``flagged_markers``: list of (token, mechanism) tuples.
    ``n_tokens``: word count.
    ``threshold_passed``: convenience flag.
    """

    target_mechanism: str
    activation_score: float
    target_hits: int
    total_hits: int
    per_mechanism_hits: Dict[str, int]
    flagged_markers: List[Tuple[str, str]] = field(default_factory=list)
    n_tokens: int = 0
    threshold_passed: bool = False


def _tokenize_count(text: str) -> int:
    if not text:
        return 0
    cleaned = re.sub(r"[^\w\s']", " ", text.lower())
    return len([t for t in cleaned.split() if t])


def _count_hits_per_mechanism(
    lowered_text: str,
) -> Tuple[Dict[str, int], List[Tuple[str, str]]]:
    """Per-mechanism hit count + flagged markers."""
    hits: Dict[str, int] = {m: 0 for m in CANONICAL_MECHANISMS}
    flagged: List[Tuple[str, str]] = []
    for mech in CANONICAL_MECHANISMS:
        markers = _MECHANISM_MARKERS[mech]
        for m in markers:
            pattern = r"\b" + re.escape(m) + r"\b"
            n = len(re.findall(pattern, lowered_text))
            if n > 0:
                hits[mech] += n
                flagged.append((m, mech))
    return hits, flagged


def score_mechanism_activation(
    text: str,
    target_mechanism: str,
    *,
    threshold: float = MECHANISM_ACTIVATION_THRESHOLD,
    strict_target: bool = False,
) -> MechanismActivationResult:
    """Score per-mechanism activation strength of creative copy."""
    target_norm = (target_mechanism or "").strip().lower()
    if target_norm not in CANONICAL_MECHANISMS:
        if strict_target:
            raise ValueError(
                f"Unknown target_mechanism '{target_mechanism}' — must "
                f"be one of {CANONICAL_MECHANISMS}"
            )
        return MechanismActivationResult(
            target_mechanism=target_mechanism or "",
            activation_score=0.0,
            target_hits=0,
            total_hits=0,
            per_mechanism_hits={m: 0 for m in CANONICAL_MECHANISMS},
            flagged_markers=[],
            n_tokens=_tokenize_count(text or ""),
            threshold_passed=False,
        )

    if not text or not text.strip():
        return MechanismActivationResult(
            target_mechanism=target_norm,
            activation_score=0.0,
            target_hits=0,
            total_hits=0,
            per_mechanism_hits={m: 0 for m in CANONICAL_MECHANISMS},
            flagged_markers=[],
            n_tokens=0,
            threshold_passed=False,
        )

    n_tokens = _tokenize_count(text)
    lowered = text.lower()

    per_mech_hits, flagged = _count_hits_per_mechanism(lowered)
    total_hits = sum(per_mech_hits.values())
    target_hits = per_mech_hits[target_norm]

    denom = max(total_hits, MIN_TOTAL_HITS_FOR_ACTIVATION)
    activation = target_hits / float(denom) if denom > 0 else 0.0
    activation = max(0.0, min(1.0, activation))

    return MechanismActivationResult(
        target_mechanism=target_norm,
        activation_score=activation,
        target_hits=target_hits,
        total_hits=total_hits,
        per_mechanism_hits=per_mech_hits,
        flagged_markers=flagged,
        n_tokens=n_tokens,
        threshold_passed=activation >= threshold,
    )


def passes_mechanism_activation_check(
    text: str,
    target_mechanism: str,
    *,
    threshold: float = MECHANISM_ACTIVATION_THRESHOLD,
) -> Tuple[bool, MechanismActivationResult]:
    """Convenience wrapper for the upload pipeline gate."""
    result = score_mechanism_activation(
        text, target_mechanism, threshold=threshold,
    )
    return (result.threshold_passed, result)
