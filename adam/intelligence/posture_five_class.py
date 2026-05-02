# =============================================================================
# Phase 2 — 5-class posture taxonomy + labeling schema
# Location: adam/intelligence/posture_five_class.py
# =============================================================================
"""Canonical 5-class posture taxonomy for the Phase 2 attentional-
posture head.

Per directive lines 173-180:

    "Page attentional-posture encoder ... five-class posture head
     trained on 300–500 hand-labeled exemplar URLs:
       — INFORMATION_FORAGING (research-mode, comparative-evaluation pages)
       — TASK_COMPLETION (booking flows, calendar/expense tooling,
         in-flow productivity)
       — LEISURE_BROWSING (entertainment, lifestyle, low-stakes content)
       — SOCIAL_CONSUMPTION (social media, news-as-feed, peer-driven
         content)
       — TRANSACTIONAL_COMPARISON (purchase-research, head-to-head
         comparisons, review-heavy)
     Classes are not arbitrary; each has a documented attentional
     signature in the cognitive psych literature, which becomes the
     partner-facing 'why' vocabulary.
     Output: posture distribution (5-vector) + raw 768-dim embedding.
     Both flow into the cascade."

Slice 22 ships the SCHEMA + LABELING substrate. The trained model
+ inference path are the multi-session arc that depends on
sentence-transformer + 300-500 hand-labels. This module gives:

  * The canonical 5 class strings (so all consumers reference the
    same vocabulary).
  * The attentional-signature descriptions (the "why" vocabulary
    the partner surface will render).
  * A bridge from the current 3-state substrate (BLEND / VIGILANCE
    / NEUTRAL — page_attentional_posture_substrate.py) to the
    5-class space, so consumers can be migrated incrementally
    even before the trained head ships.
  * The PostureDistribution shape (5-vector summing to 1).
  * PageLabelEntry — Pydantic model for the hand-labeled URL
    corpus.
  * Persistence helpers (Cypher MERGE) for the corpus storage.

DISCIPLINE (B3-LUXY a/b/c/d)
----------------------------

(a) Citations: directive lines 173-180 (5-class enumeration +
    documented attentional signatures) + Phase 2 Section 2 line
    967-969 (Phase 2 deliverable). Attentional-signature
    descriptions inherit from the cognitive-psych literature
    referenced in the directive (Section 4.2) — Pashler 1998
    (attention), Wickens 2008 (multiple-resource theory), Norman
    2013 (in-flow / out-of-flow stances). Bridge function from the
    current 3-state to 5-class is conservative: NEUTRAL maps to
    LEISURE_BROWSING (most common neutral page type per LUXY-
    plausible inventory); VIGILANCE maps to TRANSACTIONAL_COMPARISON
    or INFORMATION_FORAGING (high-vigilance research/comparison);
    BLEND maps to LEISURE_BROWSING by default.

(b) Tests pin: 5 canonical classes match directive enumeration;
    bridge from 3-state returns valid 5-class string with low
    confidence (operator should NOT trust the bridge for decisions
    requiring true 5-class precision); PageLabelEntry validates;
    distribution sums to 1; persist_page_label round-trips via
    Neo4j; load_labeled_pages returns parsed entries; persistence
    is idempotent (MERGE on url).

(c) calibration_pending=True. Bridge mapping (3-state → 5-class)
    is operator-conservative; the trained head replaces this with
    learned 5-class probabilities. A14 flag:
    PHASE_2_FIVE_CLASS_HEAD_PILOT_PENDING. The 300-500 hand-label
    corpus is built incrementally via the active-learning loop
    (sibling slice).

(d) Honest tags — what is NOT in this slice (named successors):

    * Trained 5-class head (sentence-transformer + classifier).
      Multi-session arc — depends on (i) 300-500 hand-labels
      accumulating via the active-learning loop, (ii) frozen
      sentence-transformer infrastructure deployed.
    * Active-learning loop wired to the offline pipeline. v0.1
      ships the LABEL persistence schema; the loop that selects
      uncertain URLs for human labeling is sibling.
    * Decision-time inference path (URL → 5-vector). Until the
      head ships, the cascade reads the 3-state substrate via
      categorize_posture and uses the bridge.
    * Multi-language tokenizer / domain-tuned variant of mpnet.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field, field_validator

logger = logging.getLogger(__name__)


# =============================================================================
# Canonical 5-class enumeration — directive lines 173-180
# =============================================================================

POSTURE_INFORMATION_FORAGING: str = "INFORMATION_FORAGING"
POSTURE_TASK_COMPLETION: str = "TASK_COMPLETION"
POSTURE_LEISURE_BROWSING: str = "LEISURE_BROWSING"
POSTURE_SOCIAL_CONSUMPTION: str = "SOCIAL_CONSUMPTION"
POSTURE_TRANSACTIONAL_COMPARISON: str = "TRANSACTIONAL_COMPARISON"


FIVE_CLASS_POSTURES: Tuple[str, ...] = (
    POSTURE_INFORMATION_FORAGING,
    POSTURE_TASK_COMPLETION,
    POSTURE_LEISURE_BROWSING,
    POSTURE_SOCIAL_CONSUMPTION,
    POSTURE_TRANSACTIONAL_COMPARISON,
)


# Attentional-signature descriptions (the partner-facing "why"
# vocabulary per directive line 178).
ATTENTIONAL_SIGNATURE: Dict[str, str] = {
    POSTURE_INFORMATION_FORAGING: (
        "research-mode, comparative-evaluation pages — user is "
        "actively scanning for differential signal; high cognitive "
        "engagement, low ad-receptivity unless ad complements the "
        "comparison frame"
    ),
    POSTURE_TASK_COMPLETION: (
        "booking flows, calendar/expense tooling, in-flow "
        "productivity — user has a specific goal in working memory; "
        "interruption is the highest-cost ad failure mode here"
    ),
    POSTURE_LEISURE_BROWSING: (
        "entertainment, lifestyle, low-stakes content — diffuse "
        "attentional posture; ad-receptivity moderate; "
        "blend-with-context is the dominant fluency lever"
    ),
    POSTURE_SOCIAL_CONSUMPTION: (
        "social media, news-as-feed, peer-driven content — "
        "attention sharded across micro-contexts; "
        "social-proof / unity mechanisms align with the posture"
    ),
    POSTURE_TRANSACTIONAL_COMPARISON: (
        "purchase-research, head-to-head comparisons, review-heavy "
        "pages — user is in evaluative-decision mode with already-"
        "primed purchase intent; authority / reason_why mechanisms "
        "align"
    ),
}


# =============================================================================
# Bridge: 3-state substrate (BLEND/VIGILANCE/NEUTRAL) → 5-class
# =============================================================================
#
# The current production substrate (page_attentional_posture_substrate)
# returns 3 states: blend_compatible, vigilance_activating, neutral.
# When consumers need 5-class semantics but only 3-state is available,
# we bridge conservatively. The trained head will replace this with
# learned 5-vector probabilities.

BRIDGE_THREE_TO_FIVE: Dict[str, str] = {
    "blend_compatible": POSTURE_LEISURE_BROWSING,
    "vigilance_activating": POSTURE_INFORMATION_FORAGING,
    "neutral": POSTURE_LEISURE_BROWSING,
    "unknown": POSTURE_LEISURE_BROWSING,
}

# Bridge confidence — operator should NOT trust the bridge for
# decisions requiring true 5-class precision. Low confidence flags
# this honestly.
BRIDGE_CONFIDENCE: float = 0.30


def bridge_three_to_five_class(
    three_class_label: str,
    three_class_confidence: Optional[float] = None,
) -> Tuple[str, float]:
    """Conservative mapping from the 3-state substrate to 5-class.

    Args:
        three_class_label: one of "blend_compatible" /
            "vigilance_activating" / "neutral" / "unknown".
        three_class_confidence: confidence from the source classifier
            (optional). When provided, the returned 5-class confidence
            is min(BRIDGE_CONFIDENCE, three_class_confidence) so the
            bridge never overstates certainty.

    Returns:
        (five_class_label, bridge_confidence). The label is one of
        FIVE_CLASS_POSTURES; the confidence is capped at
        BRIDGE_CONFIDENCE to flag the lossy mapping.
    """
    five_class = BRIDGE_THREE_TO_FIVE.get(
        (three_class_label or "").strip().lower(),
        POSTURE_LEISURE_BROWSING,
    )
    if three_class_confidence is None:
        return (five_class, BRIDGE_CONFIDENCE)
    return (
        five_class,
        min(BRIDGE_CONFIDENCE, max(0.0, float(three_class_confidence))),
    )


# =============================================================================
# Distribution shape — 5-vector summing to 1
# =============================================================================


@dataclass(frozen=True)
class PostureDistribution:
    """5-class posture probability distribution.

    Shape: 5-vector summing to 1.0 (within numerical tolerance).
    Class ordering matches FIVE_CLASS_POSTURES tuple. The trained
    head produces this directly; the bridge produces a one-hot
    distribution at the bridged class.
    """

    information_foraging: float
    task_completion: float
    leisure_browsing: float
    social_consumption: float
    transactional_comparison: float

    def as_vector(self) -> List[float]:
        return [
            self.information_foraging,
            self.task_completion,
            self.leisure_browsing,
            self.social_consumption,
            self.transactional_comparison,
        ]

    def argmax_class(self) -> str:
        """Return the highest-probability class label."""
        vec = self.as_vector()
        idx = max(range(len(vec)), key=lambda i: vec[i])
        return FIVE_CLASS_POSTURES[idx]


def one_hot_from_label(label: str) -> PostureDistribution:
    """Build a one-hot distribution at the given class. Useful for
    bridging a hard-classifier output into the distribution shape."""
    norm = (label or "").strip().upper()
    if norm not in FIVE_CLASS_POSTURES:
        # Conservative fallback — equal probability over all classes.
        eq = 1.0 / 5.0
        return PostureDistribution(
            information_foraging=eq, task_completion=eq,
            leisure_browsing=eq, social_consumption=eq,
            transactional_comparison=eq,
        )
    vec = [0.0] * 5
    vec[FIVE_CLASS_POSTURES.index(norm)] = 1.0
    return PostureDistribution(*vec)


# =============================================================================
# Hand-labeled URL corpus — schema + persistence
# =============================================================================


_PAGE_LABEL_NODE: str = "PostureLabel"


class PageLabelEntry(BaseModel):
    """One hand-labeled URL exemplar for the 5-class head training set.

    Per directive line 968: "trained on 300-500 hand-labeled URLs."
    """

    model_config = ConfigDict(extra="forbid")

    url: str
    label: str
    labeler: str = "operator"
    labeled_at_ts: float = Field(default_factory=time.time)
    notes: Optional[str] = None
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)

    @field_validator("label")
    @classmethod
    def _label_is_canonical(cls, v: str) -> str:
        norm = (v or "").strip().upper()
        if norm not in FIVE_CLASS_POSTURES:
            raise ValueError(
                f"label '{v}' must be one of {FIVE_CLASS_POSTURES}"
            )
        return norm


_PERSIST_LABEL_CYPHER: str = (
    f"MERGE (l:{_PAGE_LABEL_NODE} {{url: $url}}) "
    "SET l.label = $label, "
    "    l.labeler = $labeler, "
    "    l.labeled_at_ts = $labeled_at_ts, "
    "    l.notes = $notes, "
    "    l.confidence = $confidence"
)


_LOAD_LABELS_CYPHER: str = (
    f"MATCH (l:{_PAGE_LABEL_NODE}) "
    "RETURN l.url AS url, l.label AS label, l.labeler AS labeler, "
    "       l.labeled_at_ts AS labeled_at_ts, l.notes AS notes, "
    "       l.confidence AS confidence "
    "ORDER BY l.labeled_at_ts DESC "
    "LIMIT $limit"
)


_COUNT_LABELS_CYPHER: str = (
    f"MATCH (l:{_PAGE_LABEL_NODE}) "
    "RETURN count(l) AS n_labels, "
    "       count(DISTINCT l.label) AS n_classes_covered"
)


async def persist_page_label(
    entry: PageLabelEntry,
    driver: Optional[Any],
) -> bool:
    """Idempotent MERGE of one PageLabelEntry. Returns True on success."""
    if driver is None:
        return False
    try:
        async with driver.session() as session:
            await session.run(
                _PERSIST_LABEL_CYPHER,
                url=entry.url,
                label=entry.label,
                labeler=entry.labeler,
                labeled_at_ts=entry.labeled_at_ts,
                notes=entry.notes,
                confidence=entry.confidence,
            )
        return True
    except Exception as exc:
        logger.warning(
            "persist_page_label failed for url=%s: %s", entry.url, exc,
        )
        return False


async def load_labeled_pages(
    driver: Optional[Any],
    *,
    limit: int = 1000,
) -> List[PageLabelEntry]:
    """Load all persisted page labels (most-recent-first, capped at
    limit). Returns [] when driver missing / Cypher error."""
    if driver is None:
        return []
    try:
        async with driver.session() as session:
            result = await session.run(
                _LOAD_LABELS_CYPHER, limit=int(limit),
            )
            rows = await result.data()
    except Exception as exc:
        logger.warning("load_labeled_pages failed: %s", exc)
        return []

    out: List[PageLabelEntry] = []
    for row in rows:
        try:
            out.append(PageLabelEntry(
                url=str(row.get("url") or ""),
                label=str(row.get("label") or ""),
                labeler=str(row.get("labeler") or "operator"),
                labeled_at_ts=float(row.get("labeled_at_ts") or 0.0),
                notes=row.get("notes"),
                confidence=float(row.get("confidence") or 1.0),
            ))
        except Exception:
            continue  # skip malformed row
    return out


async def count_labels_corpus(
    driver: Optional[Any],
) -> Dict[str, int]:
    """Return {n_labels, n_classes_covered}. Used by an active-
    learning loop to decide whether the corpus has reached
    train-readiness (directive: 300-500 labels)."""
    if driver is None:
        return {"n_labels": 0, "n_classes_covered": 0}
    try:
        async with driver.session() as session:
            result = await session.run(_COUNT_LABELS_CYPHER)
            row = await result.single()
            if row is None:
                return {"n_labels": 0, "n_classes_covered": 0}
            return {
                "n_labels": int(row.get("n_labels") or 0),
                "n_classes_covered": int(row.get("n_classes_covered") or 0),
            }
    except Exception as exc:
        logger.warning("count_labels_corpus failed: %s", exc)
        return {"n_labels": 0, "n_classes_covered": 0}
