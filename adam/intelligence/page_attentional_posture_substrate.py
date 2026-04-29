# =============================================================================
# ADAM Page Attentional Posture Substrate (task #28)
# Location: adam/intelligence/page_attentional_posture_substrate.py
# =============================================================================

"""
PAGE ATTENTIONAL POSTURE SUBSTRATE — categorical layer atop float

Existing page_intelligence.py already carries an `attentional_posture`
float on the page profile (-1=blend-dominant, 0=neutral, +1=vigilance-
dominant) plus an `attentional_posture_confidence`. This module
provides the categorical layer on top — bridging the float to the
canonical "blend_compatible" / "vigilance_activating" labels that the
mechanism_taxonomy_runtime accumulator + the bilateral cascade's
trilateral query consume.

WHY A CATEGORICAL LAYER

The float attentional_posture is the right granularity for inference
internals. The categorical labels are the right granularity for:

  - mechanism_taxonomy_runtime: matched-vs-mismatched diagonals need a
    discrete page label
  - cascade trilateral query: "find edges from buyers in
    vigilance-activating page contexts"
  - dashboard / Uncertainty Panel: "this page's posture is
    blend_compatible (confidence 0.78)"

Discrete labels with a confidence threshold below which the posture
falls back to "neutral" preserve the discipline anchor: when we don't
know, we don't categorize.

BAYESIAN LEARNING — Author × Publication × Section priors

The pilot accumulates per-page posture observations. The substrate
groups observations by (author, publication, section) hierarchically
so that:

  - A new article from a known author inherits the author's posterior
    posture (Bayesian shrinkage)
  - A new section in a known publication inherits the publication's
    posterior
  - Truly cold-start pages fall back to category-default neutral

Full hierarchical Bayesian implementation (PyMC non-centered) is a
post-pilot follow-on (Phase 1.1). This module ships the substrate:
empirical Bayes shrinkage with simple weighted averaging at each level.

DISCIPLINE

  - Categorical labels are DERIVED, not asserted. The float remains
    the source of truth on the page profile; this module reads it.
  - Confidence threshold: posture must have confidence >=
    `MIN_POSTURE_CONFIDENCE` to be classified categorically. Below
    that, label is "neutral".
  - Neutral pages do NOT fall through to a "default" category. They
    are explicitly neutral; mechanism-taxonomy-runtime excludes them
    from the matched/mismatched diagonals.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple


# =============================================================================
# THRESHOLDS — A14 calibration-pending
# =============================================================================

# A14 PAGE_ATTENTIONAL_POSTURE_THRESHOLDS_PILOT_PENDING
# - Confidence floor below which posture is "neutral" regardless of value
# - Float thresholds for blend / vigilance categorical assignment

MIN_POSTURE_CONFIDENCE: float = 0.40
"""Confidence below this → posture label is neutral. Foundation
discipline anchor: when we don't know, we don't categorize."""

BLEND_FLOAT_THRESHOLD: float = -0.20
"""attentional_posture <= -0.20 → blend_compatible."""

VIGILANCE_FLOAT_THRESHOLD: float = 0.20
"""attentional_posture >= +0.20 → vigilance_activating."""


# =============================================================================
# CATEGORICAL POSTURE
# =============================================================================


# String labels matched to mechanism_taxonomy_runtime's expectations.
# Keep these EXACT — the runtime accumulator's matched-vs-mismatched
# logic compares string equality on category.value vs. this label.
POSTURE_BLEND: str = "blend_compatible"
POSTURE_VIGILANCE: str = "vigilance_activating"
POSTURE_NEUTRAL: str = "neutral"
POSTURE_UNKNOWN: str = "unknown"


def categorize_posture(
    posture_float: float,
    posture_confidence: float,
) -> str:
    """Translate page_intelligence's (posture_float, posture_confidence)
    into a categorical label.

    Args:
        posture_float: in [-1.0, 1.0]; -1 = full blend, +1 = full
            vigilance, 0 = neutral
        posture_confidence: in [0.0, 1.0]; 0 = no evidence, 1 = strong
            signal

    Returns:
        One of POSTURE_BLEND / POSTURE_VIGILANCE / POSTURE_NEUTRAL /
        POSTURE_UNKNOWN.

        - confidence < MIN_POSTURE_CONFIDENCE → POSTURE_UNKNOWN
        - confidence above floor:
            posture_float <= BLEND_FLOAT_THRESHOLD → POSTURE_BLEND
            posture_float >= VIGILANCE_FLOAT_THRESHOLD → POSTURE_VIGILANCE
            otherwise → POSTURE_NEUTRAL (between thresholds with
                       sufficient confidence — explicitly mid-range)
    """
    if posture_confidence < MIN_POSTURE_CONFIDENCE:
        return POSTURE_UNKNOWN
    if posture_float <= BLEND_FLOAT_THRESHOLD:
        return POSTURE_BLEND
    if posture_float >= VIGILANCE_FLOAT_THRESHOLD:
        return POSTURE_VIGILANCE
    return POSTURE_NEUTRAL


# =============================================================================
# OBSERVATION + ACCUMULATION
# =============================================================================


@dataclass(frozen=True)
class PageObservation:
    """One page's observed (posture, confidence) at decision time."""

    page_url: str
    posture_float: float
    posture_confidence: float
    author_id: Optional[str] = None
    publication_id: Optional[str] = None
    section_id: Optional[str] = None
    observed_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc),
    )


@dataclass
class PostureStats:
    """Per-key (author / publication / section) posture statistics.

    Tracks running sum + count + sum-of-squares so we can compute mean
    and variance incrementally. Confidence-weighted: each observation
    contributes its `posture_confidence` as the weight.
    """

    n_observations: int = 0
    sum_weight: float = 0.0       # Σ confidence
    sum_weighted_value: float = 0.0  # Σ confidence × value
    sum_weighted_sq: float = 0.0     # Σ confidence × value²

    def add(self, value: float, weight: float) -> None:
        if weight <= 0.0:
            return
        self.n_observations += 1
        self.sum_weight += weight
        self.sum_weighted_value += weight * value
        self.sum_weighted_sq += weight * value * value

    @property
    def weighted_mean(self) -> float:
        if self.sum_weight <= 0.0:
            return 0.0
        return self.sum_weighted_value / self.sum_weight

    @property
    def weighted_variance(self) -> float:
        if self.sum_weight <= 0.0:
            return 0.0
        mean = self.weighted_mean
        return max(0.0, self.sum_weighted_sq / self.sum_weight - mean * mean)

    @property
    def weighted_std(self) -> float:
        from math import sqrt
        return sqrt(self.weighted_variance)


class PageAttentionalPostureAccumulator:
    """Hierarchical-Bayes-flavored accumulator for per-page posture.

    Three levels:
      1. Author (most specific)
      2. Publication (intermediate)
      3. Section (broadest)

    For a new observation, all three keys (when present) get the
    contribution. For a query at posture-prediction time, the most-
    specific matching key wins (Author → Publication → Section →
    fallback).

    This is empirical-Bayes shrinkage at each level, not full
    PyMC non-centered hierarchical Bayes — that's Phase 1.1 work
    once enough data exists per (Author, Publication, Section) cell.
    """

    def __init__(self) -> None:
        self._by_author: Dict[str, PostureStats] = {}
        self._by_publication: Dict[str, PostureStats] = {}
        self._by_section: Dict[str, PostureStats] = {}

    def record(self, obs: PageObservation) -> None:
        """Record one observation against all applicable hierarchy levels."""
        weight = max(0.0, min(1.0, obs.posture_confidence))
        if weight == 0.0:
            return  # Confidence-zero observations contribute nothing

        if obs.author_id:
            self._by_author.setdefault(
                obs.author_id, PostureStats(),
            ).add(obs.posture_float, weight)
        if obs.publication_id:
            self._by_publication.setdefault(
                obs.publication_id, PostureStats(),
            ).add(obs.posture_float, weight)
        if obs.section_id:
            self._by_section.setdefault(
                obs.section_id, PostureStats(),
            ).add(obs.posture_float, weight)

    def get_author_stats(self, author_id: str) -> Optional[PostureStats]:
        return self._by_author.get(author_id)

    def get_publication_stats(
        self, publication_id: str,
    ) -> Optional[PostureStats]:
        return self._by_publication.get(publication_id)

    def get_section_stats(self, section_id: str) -> Optional[PostureStats]:
        return self._by_section.get(section_id)

    def predict_posture(
        self,
        *,
        author_id: Optional[str] = None,
        publication_id: Optional[str] = None,
        section_id: Optional[str] = None,
        min_observations: int = 5,
    ) -> Optional[Tuple[float, float]]:
        """Predict (posture_float, posture_confidence) for a NEW page
        given its (author, publication, section).

        Resolution order: Author → Publication → Section. The first
        level with >= `min_observations` observations is used. When all
        three are below threshold, returns None — caller falls back to
        per-page extraction (no prior evidence).

        Confidence of the predicted posture is the level's normalized
        observation count (capped at 1.0 at min_observations × 4).
        """
        for getter, key in (
            (self.get_author_stats, author_id),
            (self.get_publication_stats, publication_id),
            (self.get_section_stats, section_id),
        ):
            if not key:
                continue
            stats = getter(key)
            if stats is None or stats.n_observations < min_observations:
                continue
            mean = stats.weighted_mean
            confidence_n = min(1.0, stats.n_observations / (min_observations * 4))
            return (mean, confidence_n)
        return None

    def all_author_ids(self) -> List[str]:
        return sorted(self._by_author.keys())

    def all_publication_ids(self) -> List[str]:
        return sorted(self._by_publication.keys())

    def all_section_ids(self) -> List[str]:
        return sorted(self._by_section.keys())

    def reset(self) -> None:
        """Test-only — clear all accumulated state."""
        self._by_author.clear()
        self._by_publication.clear()
        self._by_section.clear()


# =============================================================================
# Singleton
# =============================================================================


_accumulator: Optional[PageAttentionalPostureAccumulator] = None


def get_page_attentional_posture_accumulator() -> PageAttentionalPostureAccumulator:
    global _accumulator
    if _accumulator is None:
        _accumulator = PageAttentionalPostureAccumulator()
    return _accumulator


def reset_page_attentional_posture_accumulator() -> None:
    """Test-only — clear the singleton."""
    global _accumulator
    _accumulator = None


def record_and_categorize_page_posture(
    *,
    page_url: str,
    posture_float: float,
    posture_confidence: float,
    author_id: Optional[str] = None,
    publication_id: Optional[str] = None,
    section_id: Optional[str] = None,
    accumulator: Optional[PageAttentionalPostureAccumulator] = None,
) -> Dict[str, Any]:
    """Decision-time helper for page-side posture wiring (task A4).

    One-stop function that:
      1. Categorizes the float posture into a string label per
         `categorize_posture` thresholds
      2. Records a PageObservation in the singleton accumulator
         (or the test-supplied accumulator)
      3. Returns a dict suitable for stamping on decision metadata
         that the OutcomeHandler's task-A2 wiring consumes

    Returns:
        {
          "page_attentional_posture": str,  // categorical label
          "raw_posture": float,
          "posture_confidence": float,
          "page_url": str,
        }

    The dict's `page_attentional_posture` key matches exactly what
    OutcomeHandler.process_outcome reads via
    `metadata.get("page_attentional_posture")`. So caller stamps this
    dict on the decision metadata at decision time; outcome handler
    reads it at outcome time; the matched/mismatched diagonal
    accumulator gets populated.

    Foundation §2 attention-inversion test fully fires when:
      - This helper is called at decision time (A4 wiring) — populates
        the accumulator AND stamps the metadata
      - OutcomeHandler tags the mechanism + reads the metadata at
        outcome time (A2 wiring, already shipped) — records the
        outcome to the conditional accumulator
      - Both are wired → matched_vs_mismatched_diagonals returns
        cells with data
    """
    if accumulator is None:
        accumulator = get_page_attentional_posture_accumulator()

    label = categorize_posture(posture_float, posture_confidence)
    accumulator.record(PageObservation(
        page_url=page_url,
        posture_float=posture_float,
        posture_confidence=posture_confidence,
        author_id=author_id,
        publication_id=publication_id,
        section_id=section_id,
    ))
    return {
        "page_attentional_posture": label,
        "raw_posture": float(posture_float),
        "posture_confidence": float(posture_confidence),
        "page_url": page_url,
    }


__all__ = [
    "BLEND_FLOAT_THRESHOLD",
    "MIN_POSTURE_CONFIDENCE",
    "POSTURE_BLEND",
    "POSTURE_NEUTRAL",
    "POSTURE_UNKNOWN",
    "POSTURE_VIGILANCE",
    "PageAttentionalPostureAccumulator",
    "PageObservation",
    "PostureStats",
    "VIGILANCE_FLOAT_THRESHOLD",
    "categorize_posture",
    "get_page_attentional_posture_accumulator",
    "record_and_categorize_page_posture",
    "reset_page_attentional_posture_accumulator",
]
