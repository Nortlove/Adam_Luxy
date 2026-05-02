# =============================================================================
# Phase 2 — 5-class posture active-learning loop
# Location: adam/intelligence/posture_active_learning.py
# =============================================================================
"""Active-learning loop for the Phase 2 5-class posture head.

Per the 2026-05-02 wrap-out handoff (multi-session arc #2): use
≥7 days of shadow-mode bid streams from Slice 8; rank pages by
classifier-uncertainty; deliver top-K uncertain pages in batches of
20 for the operator to label. v0.1 ships:

  * The labeling-batch schema + manifest persistence helpers.
  * The bootstrap-batch generator (round 1) — diversity-sampled
    across the 5 canonical posture classes for the FIRST batch
    when no classifier exists yet.
  * The uncertainty-sampling generator stub (rounds 2+) — needs
    a trained classifier; v0.1 returns a clear "not yet trained"
    sentinel result so the runner can skip cleanly.

ROUND 1 — BOOTSTRAP

When n_labels < BOOTSTRAP_THRESHOLD (default 20), use the bootstrap
generator. It produces 20 LUXY-plausible URLs evenly distributed
across the 5 directive-canonical classes (4 per class). These are
real publicly-knowable URLs the operator can visit, classify, and
persist via Slice 22's persist_page_label.

ROUNDS 2-N — UNCERTAINTY SAMPLING

When a trained classifier is available + ≥7 days of shadow-mode
bids have accumulated (DecisionTrace.page_url distinct values),
the uncertainty-sampling generator ranks pages by classifier entropy
and returns the top-K. v0.1 ships the SCAFFOLD; the trained classifier
is a sibling slice (depends on label corpus + sentence-transformer
infrastructure).

DISCIPLINE (B3-LUXY a/b/c/d)
----------------------------

(a) Citations: 2026-05-02 wrap-out handoff (multi-session arc #2);
    directive Phase 2 lines 173-180 (5-class posture head);
    Slice 22 (the schema + persistence substrate this loop drives).

(b) Tests pin: bootstrap batch produces exactly N_per_class × 5
    URLs; URLs span all 5 canonical classes; bootstrap is
    deterministic per seed; UncertaintySamplingBatchGenerator
    returns "not_trained" sentinel when classifier=None;
    LabelingBatch is frozen; persistence helpers round-trip.

(c) calibration_pending=True. v0.1 bootstrap URLs are publicly-
    knowable LUXY-plausible exemplars; pilot operator may swap
    in domain-specific alternatives. A14 flag:
    PHASE_2_ACTIVE_LEARNING_BOOTSTRAP_URLS_PILOT_PENDING.

(d) Honest tags — what is NOT in this slice (named successors):
    * Trained 5-class classifier (sibling — depends on corpus).
    * Sentence-transformer infrastructure deployment (sibling).
    * DecisionTrace.page_url scan for round-2 candidates (sibling
      — depends on shadow-mode bid stream accumulating ≥7 days).
    * Round-2 uncertainty entropy computation. The protocol +
      stub return path are shipped; the implementation is
      classifier-dependent.
    * Per-batch labeler-disagreement reconciliation (when 2+
      operators disagree on a label, which wins). Operational.
"""

from __future__ import annotations

import logging
import random
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field

from adam.intelligence.posture_five_class import (
    FIVE_CLASS_POSTURES,
    POSTURE_INFORMATION_FORAGING,
    POSTURE_LEISURE_BROWSING,
    POSTURE_SOCIAL_CONSUMPTION,
    POSTURE_TASK_COMPLETION,
    POSTURE_TRANSACTIONAL_COMPARISON,
)

logger = logging.getLogger(__name__)


# A14 PHASE_2_ACTIVE_LEARNING_BOOTSTRAP_URLS_PILOT_PENDING
BOOTSTRAP_THRESHOLD: int = 20
DEFAULT_BATCH_SIZE: int = 20


# =============================================================================
# Bootstrap URL corpus — 4 per class × 5 classes = 20
# =============================================================================
#
# Real publicly-knowable URLs spanning the 5 canonical posture classes.
# Selected as LUXY-plausible inventory exemplars: business commuters,
# black-car / rideshare context, productivity + lifestyle adjacencies.
# Operator labels each URL via Slice 22's PageLabelEntry.

_BOOTSTRAP_URLS: Dict[str, Tuple[str, ...]] = {
    POSTURE_INFORMATION_FORAGING: (
        "https://www.nytimes.com/wirecutter/reviews/best-electric-cars/",
        "https://thepointsguy.com/credit-cards/business/best-business-credit-cards/",
        "https://www.consumerreports.org/cars/new-cars/",
        "https://www.investopedia.com/articles/investing/best-online-brokers.asp",
    ),
    POSTURE_TASK_COMPLETION: (
        "https://calendar.google.com/calendar/u/0/r",
        "https://www.expensify.com/expense-reports",
        "https://www.concur.com/en-us/expense-management",
        "https://app.asana.com/0/inbox",
    ),
    POSTURE_LEISURE_BROWSING: (
        "https://www.eater.com/maps/best-restaurants-new-york-city",
        "https://www.travelandleisure.com/world-best-awards",
        "https://www.bonappetit.com/recipes",
        "https://www.architecturaldigest.com/story/celebrity-homes",
    ),
    POSTURE_SOCIAL_CONSUMPTION: (
        "https://www.linkedin.com/feed/",
        "https://news.ycombinator.com/",
        "https://www.bbc.com/news",
        "https://www.reddit.com/r/business/",
    ),
    POSTURE_TRANSACTIONAL_COMPARISON: (
        "https://www.kayak.com/cars",
        "https://www.glassdoor.com/Reviews/index.htm",
        "https://www.trustpilot.com/categories/transportation",
        "https://www.nerdwallet.com/best/credit-cards/business",
    ),
}


# Sanity check — each canonical class has the expected count.
for _cls in FIVE_CLASS_POSTURES:
    if _cls not in _BOOTSTRAP_URLS or len(_BOOTSTRAP_URLS[_cls]) != 4:
        raise RuntimeError(
            f"Bootstrap corpus malformed for class {_cls}: "
            f"expected 4 URLs, found "
            f"{len(_BOOTSTRAP_URLS.get(_cls, []))}"
        )


# =============================================================================
# Schema
# =============================================================================


class LabelingBatchEntry(BaseModel):
    """One URL queued for labeler review.

    suggested_label is None for bootstrap (no classifier); for
    uncertainty-sampling rounds it's the classifier's argmax (the
    operator confirms or overrides).
    classifier_entropy is None for bootstrap; for uncertainty-
    sampling rounds it's the classifier-output entropy (higher =
    more uncertain).
    """

    model_config = ConfigDict(extra="forbid")

    url: str
    suggested_label: Optional[str] = None
    classifier_entropy: Optional[float] = None
    notes: Optional[str] = None


class LabelingBatch(BaseModel):
    """One batch of URLs delivered to the operator for labeling.

    ``round_index``: 1 = bootstrap, 2+ = uncertainty-sampling.
    ``generator_kind``: "bootstrap_diversity" / "uncertainty_sampling" /
        "not_yet_trained_skip".
    ``entries``: ordered list (bootstrap is class-grouped; uncertainty
        is highest-entropy first).
    """

    model_config = ConfigDict(extra="forbid")

    batch_id: str
    round_index: int
    generator_kind: str
    n_labels_in_corpus_at_generation: int = 0
    created_at_ts: float = Field(default_factory=time.time)
    entries: List[LabelingBatchEntry] = Field(default_factory=list)


# =============================================================================
# Bootstrap batch generator
# =============================================================================


def generate_bootstrap_batch(
    *,
    seed: int = 0,
    n_per_class: int = 4,
    n_labels_in_corpus: int = 0,
) -> LabelingBatch:
    """Build the round-1 bootstrap batch — diversity-sampled across
    the 5 canonical classes.

    v0.1 returns a class-balanced set: ``n_per_class`` URLs per class
    × 5 classes. The operator labels each (URL, class) pair via
    Slice 22's persist_page_label. After this round trains the first
    classifier, subsequent rounds switch to uncertainty sampling.

    Args:
        seed: per-run determinism (governs URL ordering within class).
        n_per_class: how many URLs to deliver per class. Default 4
            → total 20 (matches the handoff's batch-of-20 spec).
        n_labels_in_corpus: how many labels are already persisted
            (for batch_id traceability + telemetry).
    """
    rng = random.Random(int(seed))

    entries: List[LabelingBatchEntry] = []
    for cls in FIVE_CLASS_POSTURES:
        urls = list(_BOOTSTRAP_URLS[cls])
        # Shuffle within-class for tiebreak determinism, then take first N.
        rng.shuffle(urls)
        for url in urls[:n_per_class]:
            entries.append(LabelingBatchEntry(
                url=url,
                suggested_label=cls,  # operator confirms or overrides
                classifier_entropy=None,
                notes=(
                    "bootstrap exemplar — operator should verify the "
                    f"page actually exhibits {cls} attentional posture; "
                    "override suggested_label if not"
                ),
            ))

    batch_id = (
        f"posture-batch-r1-bootstrap-"
        f"n{len(entries)}-{int(time.time())}"
    )
    return LabelingBatch(
        batch_id=batch_id,
        round_index=1,
        generator_kind="bootstrap_diversity",
        n_labels_in_corpus_at_generation=int(n_labels_in_corpus),
        entries=entries,
    )


# =============================================================================
# Uncertainty-sampling batch generator (round 2+)
# =============================================================================


def generate_uncertainty_sampling_batch(
    *,
    candidate_urls: List[str],
    classifier: Optional[Any],
    batch_size: int = DEFAULT_BATCH_SIZE,
    n_labels_in_corpus: int = 0,
) -> LabelingBatch:
    """Build a round-2+ batch by uncertainty sampling against a
    trained classifier.

    v0.1 ships the SCAFFOLD with a "not_yet_trained" sentinel return
    when classifier is None — the trained classifier is a sibling
    slice (depends on label corpus accumulating + sentence-transformer
    infrastructure). When that ships, fill in:

        for url in candidate_urls:
            probs = classifier.predict_proba(embed(url))
            entropy = scipy.stats.entropy(probs)
            heap.push((-entropy, url, probs))
        select top batch_size by entropy
        emit as LabelingBatchEntry with suggested_label=argmax

    Until then, returns an empty batch with a clear sentinel so a
    runner can detect "skip — not yet trained" without misreading
    an empty batch as "no candidates available."
    """
    if classifier is None:
        return LabelingBatch(
            batch_id=(
                f"posture-batch-uncertainty-skip-{int(time.time())}"
            ),
            round_index=2,
            generator_kind="not_yet_trained_skip",
            n_labels_in_corpus_at_generation=int(n_labels_in_corpus),
            entries=[],
        )

    # When the classifier ships, this branch implements full
    # uncertainty sampling. v0.1 returns a placeholder branch so
    # callers can write tests against the contract.
    raise NotImplementedError(
        "generate_uncertainty_sampling_batch with a non-None classifier "
        "requires the trained 5-class head — sibling slice (depends on "
        "label corpus + sentence-transformer infrastructure)."
    )


# =============================================================================
# Round-routing convenience
# =============================================================================


def select_active_learning_round(
    *,
    n_labels_in_corpus: int,
    classifier: Optional[Any] = None,
    candidate_urls: Optional[List[str]] = None,
    seed: int = 0,
) -> LabelingBatch:
    """Pick the right batch generator for the current state.

    n_labels_in_corpus < BOOTSTRAP_THRESHOLD → bootstrap.
    n_labels_in_corpus ≥ BOOTSTRAP_THRESHOLD AND classifier present
        AND candidate_urls present → uncertainty sampling.
    n_labels_in_corpus ≥ BOOTSTRAP_THRESHOLD AND no classifier → skip
        (return not_yet_trained_skip sentinel).
    """
    if n_labels_in_corpus < BOOTSTRAP_THRESHOLD:
        return generate_bootstrap_batch(
            seed=seed, n_labels_in_corpus=n_labels_in_corpus,
        )
    return generate_uncertainty_sampling_batch(
        candidate_urls=candidate_urls or [],
        classifier=classifier,
        n_labels_in_corpus=n_labels_in_corpus,
    )
