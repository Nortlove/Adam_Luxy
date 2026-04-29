# =============================================================================
# ADAM Mechanism Taxonomy Runtime — decision-time tagging + conditional accumulator
# Location: adam/intelligence/mechanism_taxonomy_runtime.py
# =============================================================================

"""
RUNTIME SUBSTRATE for `mechanism_taxonomy` (task #29 deliverable)

The static taxonomy in `adam.intelligence.mechanism_taxonomy` classifies
the 9 canonical CognitiveMechanism nodes into BLEND_COMPATIBLE vs
VIGILANCE_ACTIVATING per Foundation §2 attention-inversion. This module
adds the RUNTIME substrate the static module deliberately doesn't have:

  1. Decision-time tagging — record the route_category alongside the
     chosen mechanism on every decision, so outcome accumulation is
     conditional on the category
  2. Conditional accumulator — (mechanism_category × page_attentional_
     posture) outcome cells that compound through the pilot
  3. Foundation §2 test interface — matched_vs_mismatched_diagonals()
     gives the analytical view that tests the attention-inversion
     prediction once enough data has flowed

Why a sibling module instead of an extension of mechanism_taxonomy:

  - mechanism_taxonomy is a static registry — its entries are
    theoretical priors with literature anchors. Modifying that file
    to add runtime state would conflate static/dynamic concerns.
  - The runtime layer accumulates pilot data; the static layer is
    pinned reference. Different change cadences.
  - Per orientation A11: keep substrate boundaries clean.

DESIGN

Decision-time tagging is a single function — `tag_decision`. The
orchestrator calls it after `_select_mechanisms` produces the primary
mechanism. The result lands on the decision metadata (or the
PerAtomContributionTracker's record) for outcome-time accumulation.

The accumulator is a singleton with `record_outcome` taking the
mechanism category + page attentional posture + outcome flags. By Week
8 of the pilot, `matched_vs_mismatched_diagonals()` returns enough
data to test Foundation §2's prediction.

NOT IN SCOPE

  - Changes to `_select_mechanisms` to USE the taxonomy in scoring —
    that's a follow-on commit (selection wiring) and waits for pilot
    data confirming the taxonomy's predictive value.
  - Plant-model `_route_split` conditioning on category.
  - Adjudicator regret-signal diagnostics paired with
    `regret_correlation_prior`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from adam.intelligence.mechanism_taxonomy import (
    MECHANISM_TAXONOMY,
    MechanismRouteCategory,
)


# =============================================================================
# DECISION-TIME TAGGING
# =============================================================================


@dataclass(frozen=True)
class TaggedDecision:
    """Decision-time taxonomy tag.

    Carried on decision metadata so the outcome-time accumulator can
    stratify by mechanism_category × page_posture.

    `was_known` indicates whether the chosen mechanism was in the
    static MECHANISM_TAXONOMY. False → fell back to MIXED-style neutral
    classification — a drift signal worth alerting on (the cascade is
    selecting mechanisms outside the canonical 9).
    """

    mechanism_name: str
    category: Optional[MechanismRouteCategory]  # None when unknown
    was_known: bool
    regret_correlation_prior: Optional[float]
    tagged_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc),
    )


def tag_decision(mechanism_name: str) -> TaggedDecision:
    """Tag a decision's chosen mechanism with its route category.

    Args:
        mechanism_name: canonical mechanism identifier

    Returns:
        TaggedDecision with category + was_known flag.

        - If mechanism is in MECHANISM_TAXONOMY: category set,
          was_known=True, regret_correlation_prior populated
        - If mechanism is NOT in taxonomy: category=None,
          was_known=False, regret_correlation_prior=None.
          The decision still gets tagged — but its outcome won't
          contribute to the conditional analysis (skipped by the
          accumulator). Drift signal for ops monitoring.
    """
    if not mechanism_name:
        raise ValueError("mechanism_name must be non-empty")
    classification = MECHANISM_TAXONOMY.get(mechanism_name)
    if classification is None:
        return TaggedDecision(
            mechanism_name=mechanism_name,
            category=None,
            was_known=False,
            regret_correlation_prior=None,
        )
    return TaggedDecision(
        mechanism_name=mechanism_name,
        category=classification.category,
        was_known=True,
        regret_correlation_prior=classification.regret_correlation_prior,
    )


# =============================================================================
# CONDITIONAL ACCUMULATOR
# =============================================================================


@dataclass
class CategoryConditionalCounts:
    """Per-(mechanism_category, page_attentional_posture) outcome counts.

    Accumulates through the pilot. Once enough data lands,
    matched_vs_mismatched_diagonals() partitions cells for the
    Foundation §2 attention-inversion test.

    `n_decisions` — total decisions in this cell.
    `n_conversions` — conversion outcomes.
    `n_backfires` — refund / complaint / regret events.

    `regret_rate` weight is informed by the static taxonomy's
    regret_correlation_prior — but the rate itself is empirical
    (n_backfires / n_decisions). The prior is the EXPECTATION; the rate
    is the OBSERVATION. Adjudicator (post-pilot) compares them.
    """

    mechanism_category: MechanismRouteCategory
    page_attentional_posture: Optional[str]
    n_decisions: int = 0
    n_conversions: int = 0
    n_backfires: int = 0

    @property
    def conversion_rate(self) -> float:
        return (
            self.n_conversions / self.n_decisions
            if self.n_decisions else 0.0
        )

    @property
    def backfire_rate(self) -> float:
        return (
            self.n_backfires / self.n_decisions
            if self.n_decisions else 0.0
        )


class TaxonomyConditionalAccumulator:
    """Accumulates outcome counts conditional on (mechanism category,
    page attentional posture).

    Decision-flow integration:
      1. Decision time: orchestrator calls tag_decision() to get
         TaggedDecision; metadata stores category.
      2. Outcome time: outcome handler calls accumulator.record_outcome
         with the category + page_posture + converted/backfired flags.

    Foundation §2 test interface:
      matched_vs_mismatched_diagonals() returns (matched, mismatched).
      Foundation predicts matched cells outperform mismatched on
      conversion rate AND backfire rate.
    """

    def __init__(self) -> None:
        self._cells: Dict[
            Tuple[MechanismRouteCategory, Optional[str]],
            CategoryConditionalCounts,
        ] = {}

    def _get_or_create(
        self,
        mech_category: MechanismRouteCategory,
        page_posture: Optional[str],
    ) -> CategoryConditionalCounts:
        key = (mech_category, page_posture)
        if key not in self._cells:
            self._cells[key] = CategoryConditionalCounts(
                mechanism_category=mech_category,
                page_attentional_posture=page_posture,
            )
        return self._cells[key]

    def record_outcome(
        self,
        tagged: TaggedDecision,
        page_posture: Optional[str],
        *,
        converted: bool,
        backfired: bool = False,
    ) -> None:
        """Record an outcome conditional on the decision's tag.

        When the mechanism was unknown (was_known=False), the outcome is
        SILENTLY SKIPPED — accumulating into a None-category cell would
        contaminate the analysis. Caller can monitor was_known=False
        events separately for drift detection.
        """
        if not tagged.was_known or tagged.category is None:
            return  # drift case — not accumulated
        cell = self._get_or_create(tagged.category, page_posture)
        cell.n_decisions += 1
        if converted:
            cell.n_conversions += 1
        if backfired:
            cell.n_backfires += 1

    def get_cell(
        self,
        mech_category: MechanismRouteCategory,
        page_posture: Optional[str],
    ) -> CategoryConditionalCounts:
        """Return cell counts (creating empty cell if missing)."""
        return self._get_or_create(mech_category, page_posture)

    def all_cells(self) -> List[CategoryConditionalCounts]:
        return list(self._cells.values())

    def matched_vs_mismatched_diagonals(
        self,
    ) -> Tuple[
        List[CategoryConditionalCounts],
        List[CategoryConditionalCounts],
    ]:
        """Foundation §2 attention-inversion test interface.

        Returns (matched, mismatched) where:
          matched = cells where mechanism_category matches
            page_attentional_posture (e.g., BLEND_COMPATIBLE mech ×
            "blend_compatible" page; VIGILANCE_ACTIVATING mech ×
            "vigilance_activating" page)
          mismatched = the off-diagonal cells

        Cells with page_posture=None are EXCLUDED from both — they
        cannot be classified as matched or mismatched.

        Foundation predicts matched outperforms mismatched on
        conversion rate AND backfire rate. By pilot Week 8 with
        sufficient data per cell, this comparison fires.
        """
        matched: List[CategoryConditionalCounts] = []
        mismatched: List[CategoryConditionalCounts] = []
        for cell in self._cells.values():
            if cell.page_attentional_posture is None:
                continue
            mc_value = cell.mechanism_category.value
            if mc_value == cell.page_attentional_posture:
                matched.append(cell)
            else:
                mismatched.append(cell)
        return matched, mismatched

    def reset(self) -> None:
        """Test-only — clear all accumulated counts."""
        self._cells.clear()


# =============================================================================
# Singleton
# =============================================================================


_taxonomy_runtime_accumulator: Optional[TaxonomyConditionalAccumulator] = None


def get_taxonomy_accumulator() -> TaxonomyConditionalAccumulator:
    """Get or create the global taxonomy accumulator.

    Production wiring: outcome handler imports this and calls
    record_outcome at outcome time with the decision's TaggedDecision +
    page posture from the decision context.
    """
    global _taxonomy_runtime_accumulator
    if _taxonomy_runtime_accumulator is None:
        _taxonomy_runtime_accumulator = TaxonomyConditionalAccumulator()
    return _taxonomy_runtime_accumulator


def reset_taxonomy_accumulator() -> None:
    """Test-only — clear the singleton."""
    global _taxonomy_runtime_accumulator
    _taxonomy_runtime_accumulator = None


__all__ = [
    "CategoryConditionalCounts",
    "TaggedDecision",
    "TaxonomyConditionalAccumulator",
    "get_taxonomy_accumulator",
    "reset_taxonomy_accumulator",
    "tag_decision",
]
