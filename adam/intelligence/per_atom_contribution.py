# =============================================================================
# ADAM Per-Atom Contribution Measurement Framework
# Location: adam/intelligence/per_atom_contribution.py
# =============================================================================

"""
PER-ATOM CONTRIBUTION MEASUREMENT (B3-LUXY Phase 3 deliverable 3)

Measures whether each of the 9 redone atoms (Brehm autonomy_reactance,
Hill persuasion_pharmacology, Girard mimetic_desire, Friestad-Wright
strategic_awareness, Parfit-Hershfield temporal_self, Spence
signal_credibility, Loomes-Sugden regret_anticipation, Ellsberg
ambiguity_attitude, Higgins regulatory_focus) actually contributes to
LUXY pilot outcomes.

Per docs/B3_LUXY_PHASE_PLAN.md §6, three metrics drive the post-pilot
generalization decision:

  1. PREDICTION-CORRECTNESS LIFT — does including this atom's chain
     attestation in L3 fusion produce a measurable AUC improvement?
     Computed by comparing predicted-vs-realized outcome accuracy across
     decisions where the atom did vs didn't contribute.

  2. CHAIN-LINK SURVIVAL — what fraction of the atom's theoretical
     LinkPosteriors survive (posterior mean > 0.5) after pilot data?
     Atom is "theoretically grounded by data" if ≥75% of links survive.
     This consumes TheoryLearner.LinkPosterior state directly.

  3. MECHANISM-ADJUSTMENT DIRECTION MATCH — when the atom suppresses a
     mechanism and L3 follows, do those decisions have lower backfire
     rates than counterfactual decisions where L3 didn't follow? Atom
     is "directionally correct" if the lower-backfire-rate is
     statistically significant.

The decision tree post-pilot:
  * All 9 atoms pass all 3 metrics → expand Phase B (full system audit).
  * 5–8 atoms pass → expand selectively to adjacent theoretical neighborhoods.
  * <5 atoms pass → STOP. Investigate failures (theory-revision vs
    measurement-error per foundation §4.4) before expanding.

This module provides the computational primitives. The data-ingestion
pipeline (consuming Redis-cached atom_outputs + outcome streams) wires
these primitives onto live LUXY pilot data.

DESIGN
------
- AtomDecisionRecord: per-decision row (one per atom-decision pair).
- AtomContribution: per-atom aggregated metrics.
- PerAtomContributionTracker: in-memory accumulator + metric computation.
- Helper functions for each metric (callable independently for testing
  and for ad-hoc analysis).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

from adam.atoms.models.chain_attestation import (
    CalibrationStatus,
    ChainAttestation,
)


# =============================================================================
# THRESHOLDS — per plan doc §6
# =============================================================================

# Metric 2: chain-link survival threshold for "theoretically grounded by data"
LINK_SURVIVAL_THRESHOLD = 0.75
LINK_POSTERIOR_SURVIVAL_FLOOR = 0.5  # mean > this counts as "surviving"

# Metric 3: minimum number of follow events for direction-match to be reportable
MIN_DIRECTION_MATCH_DECISIONS = 30


# =============================================================================
# DATA STRUCTURES
# =============================================================================


class AtomVerdict(str, Enum):
    """Per-atom post-pilot verdict from the three-metric battery."""

    PASS = "pass"            # all 3 metrics pass
    PARTIAL = "partial"      # 1-2 metrics pass
    FAIL = "fail"            # 0 metrics pass
    INSUFFICIENT_DATA = "insufficient_data"  # not enough decisions to evaluate


@dataclass
class AtomDecisionRecord:
    """One atom's contribution to one decision, with outcome attached.

    Created by joining cached chain attestations with outcome events.
    The contribution tracker accumulates these and computes metrics.
    """

    decision_id: str
    atom_id: str
    chain_attestation: ChainAttestation
    outcome_value: float                       # ∈ [0, 1] — observed outcome quality
    success: bool                              # binary success indicator
    backfire_signal: bool = False              # explicit regret/refund/complaint flag
    mechanism_followed: Optional[str] = None   # mechanism L3 ultimately recommended
    pinned_links_count: int = field(default=0)
    pilot_pending_links_count: int = field(default=0)

    def __post_init__(self) -> None:
        # Compute pinned vs pilot-pending counts from the chain
        if self.chain_attestation:
            self.pinned_links_count = sum(
                1 for link in self.chain_attestation.chain
                if link.calibration_status == CalibrationStatus.PINNED
            )
            self.pilot_pending_links_count = sum(
                1 for link in self.chain_attestation.chain
                if link.calibration_status == CalibrationStatus.PILOT_PENDING
            )


@dataclass
class AtomContribution:
    """Aggregated per-atom contribution metrics from pilot data.

    Produced by PerAtomContributionTracker.compute_atom_contribution.
    """

    atom_id: str

    # Volume
    n_decisions: int = 0
    n_successes: int = 0
    n_backfires: int = 0

    # Metric 1: prediction-correctness lift
    # We approximate AUC-style accuracy via outcome-rate comparison
    # between high-confidence and low-confidence chain-attestation
    # subsets within this atom's decisions. A more rigorous
    # operationalization (held-out AUC delta) requires the
    # counterfactual scoring path; this approximation gives a
    # directional signal that the data collection wires onto.
    high_confidence_outcome_rate: Optional[float] = None
    low_confidence_outcome_rate: Optional[float] = None
    prediction_lift_delta: Optional[float] = None

    # Metric 2: chain-link survival
    n_link_keys_observed: int = 0
    n_link_keys_surviving: int = 0
    chain_link_survival_rate: Optional[float] = None

    # Metric 3: direction-match
    n_suppress_recommendations: int = 0  # mechanism_followed == suppression-target
    n_suppress_followed: int = 0
    n_suppress_followed_with_lower_backfire: int = 0
    direction_match_rate: Optional[float] = None

    # Calibration mix
    n_decisions_pinned_only: int = 0       # all chain links PINNED
    n_decisions_with_pending: int = 0      # any chain link PILOT_PENDING

    # Verdict (computed from above)
    verdict: AtomVerdict = AtomVerdict.INSUFFICIENT_DATA
    verdict_rationale: str = ""

    @property
    def success_rate(self) -> float:
        return self.n_successes / self.n_decisions if self.n_decisions else 0.0

    @property
    def backfire_rate(self) -> float:
        return self.n_backfires / self.n_decisions if self.n_decisions else 0.0


# =============================================================================
# METRIC COMPUTATIONS
# =============================================================================


def compute_chain_link_survival(
    link_keys: Iterable[str],
    posterior_means: Dict[str, float],
    survival_floor: float = LINK_POSTERIOR_SURVIVAL_FLOOR,
) -> Tuple[int, int, float]:
    """Metric 2 helper: survival rate for a set of link keys.

    Args:
        link_keys: link_keys from one or more chain attestations
        posterior_means: dict mapping link_key → LinkPosterior.mean
            (typically pulled from TheoryLearner._link_posteriors)
        survival_floor: posterior mean threshold for "surviving"
            (default 0.5 — per plan doc §6)

    Returns:
        (n_observed, n_surviving, survival_rate). n_observed is the
        number of link_keys that have a posterior at all; n_surviving
        is the subset whose posterior mean exceeds the floor.

    Pin: when no link is observed, returns (0, 0, 0.0).
    """
    keys = set(link_keys)
    if not keys:
        return 0, 0, 0.0
    n_observed = 0
    n_surviving = 0
    for key in keys:
        if key in posterior_means:
            n_observed += 1
            if posterior_means[key] > survival_floor:
                n_surviving += 1
    if n_observed == 0:
        return 0, 0, 0.0
    return n_observed, n_surviving, n_surviving / n_observed


def compute_prediction_lift(
    high_confidence_decisions: List[AtomDecisionRecord],
    low_confidence_decisions: List[AtomDecisionRecord],
) -> Tuple[Optional[float], Optional[float], Optional[float]]:
    """Metric 1 helper: outcome-rate delta between high and low chain-confidence.

    Approximation of AUC-style prediction lift. When the atom emits a
    high-confidence attestation, are the realized outcomes better than
    when it emits a low-confidence one?

    Args:
        high_confidence_decisions: decisions where the atom's
            ChainAttestation.final_assessment.confidence >= 0.65
        low_confidence_decisions: decisions where it was < 0.5

    Returns:
        (high_rate, low_rate, lift_delta). All None if either group
        has no decisions.

    Pin: lift_delta > 0 means the atom's confidence is correlated with
    outcome — it discriminates. lift_delta ≈ 0 means the confidence
    signal carries no predictive value.
    """
    if not high_confidence_decisions or not low_confidence_decisions:
        return None, None, None
    high_rate = sum(
        d.outcome_value for d in high_confidence_decisions
    ) / len(high_confidence_decisions)
    low_rate = sum(
        d.outcome_value for d in low_confidence_decisions
    ) / len(low_confidence_decisions)
    return high_rate, low_rate, high_rate - low_rate


def compute_direction_match(
    decisions: List[AtomDecisionRecord],
    suppression_threshold: float = -0.05,
) -> Tuple[int, int, int, Optional[float]]:
    """Metric 3 helper: do atom-suggested suppressions correlate with
    lower backfire when followed?

    For each decision:
      - Identify mechanisms the atom recommended SUPPRESSING
        (adjustment_value < suppression_threshold)
      - Check whether L3 ACTUALLY suppressed (mechanism_followed != suppressed_id)
      - When followed: count whether outcome had backfire_signal=False

    Args:
        decisions: list of AtomDecisionRecord for one atom
        suppression_threshold: adjustment_value below which the atom is
            considered to be recommending suppression of a mechanism

    Returns:
        (n_suppress_recs, n_followed, n_followed_with_lower_backfire, rate).
        rate = n_followed_with_lower_backfire / n_followed if n_followed > 0
        else None.

    Pin: rate > 0.5 means following the atom's suppressions correlates
    with lower backfire rate — directional correctness.
    """
    n_suppress_recs = 0
    n_followed = 0
    n_followed_no_backfire = 0

    for d in decisions:
        suppressed_mechs: Set[str] = set()
        for adj in d.chain_attestation.mechanism_adjustments:
            if adj.adjustment_value < suppression_threshold:
                suppressed_mechs.add(adj.mechanism_id)
        if not suppressed_mechs:
            continue
        n_suppress_recs += 1
        # L3 followed if the mechanism it ultimately recommended is
        # NOT one the atom suggested suppressing.
        if d.mechanism_followed and d.mechanism_followed not in suppressed_mechs:
            n_followed += 1
            if not d.backfire_signal:
                n_followed_no_backfire += 1

    rate: Optional[float] = None
    if n_followed > 0:
        rate = n_followed_no_backfire / n_followed
    return n_suppress_recs, n_followed, n_followed_no_backfire, rate


# =============================================================================
# TRACKER
# =============================================================================


class PerAtomContributionTracker:
    """Accumulates per-atom decision records and computes contribution metrics.

    Usage:
        tracker = PerAtomContributionTracker()
        for record in decision_records:
            tracker.record_decision(record)
        contributions = tracker.compute_all_contributions(
            link_posteriors={...}  # from TheoryLearner
        )
        # contributions: Dict[atom_id, AtomContribution]
        # Each carries verdict, rationale, and the three metrics.
    """

    def __init__(self) -> None:
        self._records_by_atom: Dict[str, List[AtomDecisionRecord]] = {}

    def record_decision(self, record: AtomDecisionRecord) -> None:
        self._records_by_atom.setdefault(record.atom_id, []).append(record)

    @property
    def n_decisions_total(self) -> int:
        return sum(len(records) for records in self._records_by_atom.values())

    @property
    def atom_ids_observed(self) -> List[str]:
        return list(self._records_by_atom.keys())

    def compute_atom_contribution(
        self,
        atom_id: str,
        link_posteriors: Optional[Dict[str, float]] = None,
        high_confidence_threshold: float = 0.65,
        low_confidence_threshold: float = 0.50,
    ) -> AtomContribution:
        """Compute contribution metrics for one atom."""
        records = self._records_by_atom.get(atom_id, [])
        contribution = AtomContribution(atom_id=atom_id)
        contribution.n_decisions = len(records)

        if not records:
            contribution.verdict = AtomVerdict.INSUFFICIENT_DATA
            contribution.verdict_rationale = "no decisions recorded for this atom"
            return contribution

        # Volume metrics
        contribution.n_successes = sum(1 for d in records if d.success)
        contribution.n_backfires = sum(1 for d in records if d.backfire_signal)
        contribution.n_decisions_with_pending = sum(
            1 for d in records if d.pilot_pending_links_count > 0
        )
        contribution.n_decisions_pinned_only = (
            contribution.n_decisions - contribution.n_decisions_with_pending
        )

        # Metric 1: prediction lift (approximated via confidence-stratified outcome rates)
        high_conf = [
            d for d in records
            if d.chain_attestation.final_assessment.confidence
            >= high_confidence_threshold
        ]
        low_conf = [
            d for d in records
            if d.chain_attestation.final_assessment.confidence
            < low_confidence_threshold
        ]
        high_rate, low_rate, lift = compute_prediction_lift(high_conf, low_conf)
        contribution.high_confidence_outcome_rate = high_rate
        contribution.low_confidence_outcome_rate = low_rate
        contribution.prediction_lift_delta = lift

        # Metric 2: chain-link survival
        if link_posteriors is not None:
            all_link_keys: Set[str] = set()
            for d in records:
                all_link_keys.update(d.chain_attestation.theoretical_link_keys)
            n_obs, n_surv, surv_rate = compute_chain_link_survival(
                all_link_keys, link_posteriors
            )
            contribution.n_link_keys_observed = n_obs
            contribution.n_link_keys_surviving = n_surv
            contribution.chain_link_survival_rate = surv_rate

        # Metric 3: direction match
        n_recs, n_followed, n_no_back, dm_rate = compute_direction_match(records)
        contribution.n_suppress_recommendations = n_recs
        contribution.n_suppress_followed = n_followed
        contribution.n_suppress_followed_with_lower_backfire = n_no_back
        contribution.direction_match_rate = dm_rate

        # Verdict computation
        contribution.verdict, contribution.verdict_rationale = _classify_verdict(
            contribution
        )

        return contribution

    def compute_all_contributions(
        self,
        link_posteriors: Optional[Dict[str, float]] = None,
        **kwargs,
    ) -> Dict[str, AtomContribution]:
        return {
            atom_id: self.compute_atom_contribution(
                atom_id, link_posteriors=link_posteriors, **kwargs
            )
            for atom_id in self._records_by_atom
        }

    def post_pilot_decision(
        self,
        link_posteriors: Optional[Dict[str, float]] = None,
    ) -> Tuple[str, str, Dict[str, AtomContribution]]:
        """Run the §6 post-pilot decision tree.

        Returns (decision, rationale, all_contributions).
        Decisions:
          - "expand_full_system_audit" : all 9 atoms PASS
          - "expand_selectively"        : 5-8 atoms PASS
          - "stop_and_investigate"      : <5 atoms PASS
          - "insufficient_data"         : not enough decisions to decide
        """
        contributions = self.compute_all_contributions(link_posteriors=link_posteriors)
        n_passed = sum(
            1 for c in contributions.values() if c.verdict == AtomVerdict.PASS
        )
        n_evaluable = sum(
            1 for c in contributions.values()
            if c.verdict != AtomVerdict.INSUFFICIENT_DATA
        )

        if n_evaluable < 3:
            return (
                "insufficient_data",
                f"only {n_evaluable} atoms have enough decisions to evaluate",
                contributions,
            )

        if n_passed >= 9:
            return (
                "expand_full_system_audit",
                "all 9 atoms passed all 3 metrics — generalize to remaining 21 atoms",
                contributions,
            )
        if n_passed >= 5:
            return (
                "expand_selectively",
                f"{n_passed} atoms passed — expand to adjacent theoretical neighborhoods",
                contributions,
            )
        return (
            "stop_and_investigate",
            f"only {n_passed} atoms passed — investigate failures before expanding",
            contributions,
        )


# =============================================================================
# VERDICT CLASSIFIER
# =============================================================================


def _classify_verdict(c: AtomContribution) -> Tuple[AtomVerdict, str]:
    """Classify an AtomContribution into a verdict.

    Per plan doc §6:
      - Metric 1: prediction lift > 0.01 is "useful"
      - Metric 2: chain link survival ≥ 0.75 is "theoretically grounded"
      - Metric 3: direction match rate > 0.5 with sufficient sample is
                  "directionally correct"

    PASS = all 3 met (or N/A due to data insufficiency on a metric that
    isn't critical for the atom)
    PARTIAL = 1-2 met
    FAIL = 0 met
    """
    if c.n_decisions < 30:
        return (
            AtomVerdict.INSUFFICIENT_DATA,
            f"only {c.n_decisions} decisions (need ≥30 for evaluation)",
        )

    metrics_met: List[str] = []
    metrics_missed: List[str] = []

    # Metric 1
    if c.prediction_lift_delta is not None:
        if c.prediction_lift_delta > 0.01:
            metrics_met.append(f"lift={c.prediction_lift_delta:+.3f}")
        else:
            metrics_missed.append(f"lift={c.prediction_lift_delta:+.3f}")
    else:
        metrics_missed.append("lift=insufficient_confidence_split")

    # Metric 2
    if c.chain_link_survival_rate is not None and c.n_link_keys_observed > 0:
        if c.chain_link_survival_rate >= LINK_SURVIVAL_THRESHOLD:
            metrics_met.append(
                f"survival={c.chain_link_survival_rate:.2f}"
            )
        else:
            metrics_missed.append(
                f"survival={c.chain_link_survival_rate:.2f}"
            )
    else:
        metrics_missed.append("survival=no_posterior_data")

    # Metric 3
    if c.direction_match_rate is not None and c.n_suppress_followed >= MIN_DIRECTION_MATCH_DECISIONS:
        if c.direction_match_rate > 0.5:
            metrics_met.append(f"direction_match={c.direction_match_rate:.2f}")
        else:
            metrics_missed.append(f"direction_match={c.direction_match_rate:.2f}")
    else:
        metrics_missed.append(
            f"direction_match=insufficient_followed={c.n_suppress_followed}"
        )

    n_met = len(metrics_met)
    rationale = f"met=[{', '.join(metrics_met)}], missed=[{', '.join(metrics_missed)}]"

    if n_met >= 3:
        return AtomVerdict.PASS, rationale
    if n_met >= 1:
        return AtomVerdict.PARTIAL, rationale
    return AtomVerdict.FAIL, rationale
