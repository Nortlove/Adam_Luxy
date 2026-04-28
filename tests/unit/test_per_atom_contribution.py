# =============================================================================
# ADAM Per-Atom Contribution Measurement — Tests
# Location: tests/unit/test_per_atom_contribution.py
# =============================================================================

"""
TESTS — per_atom_contribution (B3-LUXY Phase 3 deliverable 3)

Pins the three-metric battery:
- Metric 1: prediction lift (high-confidence outcome rate vs low)
- Metric 2: chain-link survival (% link posteriors > 0.5)
- Metric 3: mechanism-direction match (followed-suppression backfire rate)

Pins the post-pilot decision tree (plan doc §6):
- All 9 atoms pass → expand_full_system_audit
- 5-8 atoms pass → expand_selectively
- <5 atoms pass → stop_and_investigate
- <3 atoms evaluable → insufficient_data
"""

import pytest

from adam.atoms.models.chain_attestation import (
    AdjustmentEvidence,
    CalibrationStatus,
    ChainAttestation,
    ChainProvenance,
    ConstructLink,
    RelationType,
    TypedEvidence,
)
from adam.intelligence.per_atom_contribution import (
    LINK_POSTERIOR_SURVIVAL_FLOOR,
    LINK_SURVIVAL_THRESHOLD,
    MIN_DIRECTION_MATCH_DECISIONS,
    AtomContribution,
    AtomDecisionRecord,
    AtomVerdict,
    PerAtomContributionTracker,
    compute_chain_link_survival,
    compute_direction_match,
    compute_prediction_lift,
)


# =============================================================================
# HELPERS
# =============================================================================


def _make_attestation(
    atom_id: str,
    confidence: float = 0.7,
    pinned_count: int = 3,
    pending_count: int = 2,
    suppress_mechs: list[str] = None,
    boost_mechs: list[str] = None,
) -> ChainAttestation:
    """Build a ChainAttestation with N PINNED + M PILOT_PENDING links."""
    chain = []
    for i in range(pinned_count):
        chain.append(
            ConstructLink(
                source_construct=f"src_{atom_id}_{i}",
                relation_type=RelationType.MODULATED_BY,
                target_construct=f"tgt_{atom_id}_{i}",
                evidence_value=0.5,
                confidence=confidence,
                citation="test_citation",
                calibration_status=CalibrationStatus.PINNED,
            )
        )
    for i in range(pending_count):
        chain.append(
            ConstructLink(
                source_construct=f"src_{atom_id}_p{i}",
                relation_type=RelationType.PRODUCES,
                target_construct=f"tgt_{atom_id}_p{i}",
                evidence_value=0.5,
                confidence=confidence,
                citation="test_citation",
                calibration_status=CalibrationStatus.PILOT_PENDING,
            )
        )

    final = TypedEvidence(
        construct=f"final_{atom_id}",
        value=0.5,
        confidence=confidence,
        citation="test_citation",
        calibration_status=CalibrationStatus.PILOT_PENDING,
    )
    provenance = ChainProvenance(atom_id=atom_id)

    chain_link_ids = [link.link_id for link in chain]
    adjustments = []
    for mech in suppress_mechs or []:
        adjustments.append(
            AdjustmentEvidence(
                mechanism_id=mech,
                adjustment_value=-0.20,
                chain_links_responsible=chain_link_ids,
            )
        )
    for mech in boost_mechs or []:
        adjustments.append(
            AdjustmentEvidence(
                mechanism_id=mech,
                adjustment_value=0.15,
                chain_links_responsible=chain_link_ids,
            )
        )

    return ChainAttestation(
        atom_id=atom_id,
        request_id="req_test",
        target_construct=f"final_{atom_id}",
        chain=chain,
        final_assessment=final,
        mechanism_adjustments=adjustments,
        provenance=provenance,
    )


def _make_record(
    atom_id: str = "atom_test",
    decision_id: str = "d1",
    confidence: float = 0.7,
    success: bool = True,
    outcome_value: float = 1.0,
    backfire_signal: bool = False,
    mechanism_followed: str = "authority",
    suppress_mechs: list[str] = None,
    boost_mechs: list[str] = None,
) -> AtomDecisionRecord:
    att = _make_attestation(
        atom_id=atom_id,
        confidence=confidence,
        suppress_mechs=suppress_mechs,
        boost_mechs=boost_mechs,
    )
    return AtomDecisionRecord(
        decision_id=decision_id,
        atom_id=atom_id,
        chain_attestation=att,
        outcome_value=outcome_value,
        success=success,
        backfire_signal=backfire_signal,
        mechanism_followed=mechanism_followed,
    )


# =============================================================================
# DATA-STRUCTURE INVARIANTS
# =============================================================================


class TestAtomDecisionRecord:
    def test_post_init_counts_pinned_vs_pending(self):
        """PINNED + PILOT_PENDING links counted from chain after construction."""
        record = _make_record()  # default: 3 pinned + 2 pending
        assert record.pinned_links_count == 3
        assert record.pilot_pending_links_count == 2

    def test_pinned_only_chain_zero_pending(self):
        att = _make_attestation("a", pinned_count=5, pending_count=0)
        record = AtomDecisionRecord(
            decision_id="d1", atom_id="a",
            chain_attestation=att,
            outcome_value=1.0, success=True,
        )
        assert record.pinned_links_count == 5
        assert record.pilot_pending_links_count == 0


# =============================================================================
# METRIC 2: CHAIN-LINK SURVIVAL
# =============================================================================


class TestChainLinkSurvival:
    def test_no_links_returns_zero(self):
        n_obs, n_surv, rate = compute_chain_link_survival([], {"foo": 0.7})
        assert n_obs == 0
        assert n_surv == 0
        assert rate == 0.0

    def test_no_posteriors_returns_zero(self):
        n_obs, n_surv, rate = compute_chain_link_survival(["link1"], {})
        assert n_obs == 0
        assert rate == 0.0

    def test_all_surviving_returns_one(self):
        link_keys = ["a", "b", "c"]
        posteriors = {"a": 0.7, "b": 0.6, "c": 0.55}
        n_obs, n_surv, rate = compute_chain_link_survival(link_keys, posteriors)
        assert n_obs == 3
        assert n_surv == 3
        assert rate == pytest.approx(1.0)

    def test_partial_survival(self):
        link_keys = ["a", "b", "c", "d"]
        posteriors = {"a": 0.7, "b": 0.4, "c": 0.6, "d": 0.3}
        n_obs, n_surv, rate = compute_chain_link_survival(link_keys, posteriors)
        # a, c survive (>0.5); b, d don't
        assert n_obs == 4
        assert n_surv == 2
        assert rate == pytest.approx(0.5)

    def test_at_floor_does_not_count_as_survived(self):
        """posterior == floor: NOT surviving (strict > floor)."""
        link_keys = ["a"]
        posteriors = {"a": LINK_POSTERIOR_SURVIVAL_FLOOR}
        n_obs, n_surv, rate = compute_chain_link_survival(link_keys, posteriors)
        assert n_obs == 1
        assert n_surv == 0

    def test_unobserved_links_excluded_from_denominator(self):
        """Links without posterior data don't count against survival rate."""
        link_keys = ["a", "b", "c_no_data"]
        posteriors = {"a": 0.7, "b": 0.6}  # c has no posterior
        n_obs, n_surv, rate = compute_chain_link_survival(link_keys, posteriors)
        assert n_obs == 2  # only a, b observed
        assert n_surv == 2
        assert rate == pytest.approx(1.0)


# =============================================================================
# METRIC 1: PREDICTION LIFT
# =============================================================================


class TestPredictionLift:
    def test_empty_groups_return_none(self):
        h, l, lift = compute_prediction_lift([], [_make_record()])
        assert h is None and l is None and lift is None

    def test_high_confidence_better_outcomes_positive_lift(self):
        """When high-confidence decisions have better outcomes, lift > 0."""
        high = [_make_record(outcome_value=1.0) for _ in range(5)]
        low = [_make_record(outcome_value=0.3) for _ in range(5)]
        h, l, lift = compute_prediction_lift(high, low)
        assert h == pytest.approx(1.0)
        assert l == pytest.approx(0.3)
        assert lift == pytest.approx(0.7)

    def test_no_difference_returns_zero_lift(self):
        high = [_make_record(outcome_value=0.7) for _ in range(3)]
        low = [_make_record(outcome_value=0.7) for _ in range(3)]
        _, _, lift = compute_prediction_lift(high, low)
        assert lift == pytest.approx(0.0)

    def test_negative_lift_when_low_confidence_outperforms(self):
        """If low-confidence subset has BETTER outcomes (i.e. atom's confidence
        signal is anti-predictive), lift < 0 — the atom is failing metric 1."""
        high = [_make_record(outcome_value=0.3) for _ in range(3)]
        low = [_make_record(outcome_value=0.8) for _ in range(3)]
        _, _, lift = compute_prediction_lift(high, low)
        assert lift < 0


# =============================================================================
# METRIC 3: DIRECTION MATCH
# =============================================================================


class TestDirectionMatch:
    def test_no_suppression_recs_returns_none(self):
        records = [
            _make_record(suppress_mechs=None, boost_mechs=["authority"])
            for _ in range(5)
        ]
        n_recs, n_followed, n_no_back, rate = compute_direction_match(records)
        assert n_recs == 0
        assert n_followed == 0
        assert rate is None

    def test_l3_followed_no_backfire_high_match_rate(self):
        """When L3 follows the suppression and backfire is absent, rate → 1.0."""
        # Atom suppressed scarcity; L3 picked authority instead; no backfire
        records = [
            _make_record(
                suppress_mechs=["scarcity"],
                mechanism_followed="authority",
                backfire_signal=False,
            )
            for _ in range(5)
        ]
        n_recs, n_followed, n_no_back, rate = compute_direction_match(records)
        assert n_recs == 5
        assert n_followed == 5
        assert n_no_back == 5
        assert rate == pytest.approx(1.0)

    def test_l3_ignored_suppression_not_counted_as_followed(self):
        """When L3 picks the suppressed mechanism anyway, it doesn't count
        as 'followed'."""
        records = [
            _make_record(
                suppress_mechs=["scarcity"],
                mechanism_followed="scarcity",  # L3 picked the suppressed one
                backfire_signal=False,
            )
            for _ in range(5)
        ]
        n_recs, n_followed, _, _ = compute_direction_match(records)
        assert n_recs == 5
        assert n_followed == 0

    def test_followed_with_backfire_lowers_rate(self):
        """Followed but had backfire: degrades direction-match rate."""
        records = [
            _make_record(
                suppress_mechs=["scarcity"],
                mechanism_followed="authority",
                backfire_signal=True,  # backfire occurred anyway
            )
            for _ in range(5)
        ]
        n_recs, n_followed, n_no_back, rate = compute_direction_match(records)
        assert n_followed == 5
        assert n_no_back == 0  # all backfired
        assert rate == pytest.approx(0.0)


# =============================================================================
# TRACKER — END-TO-END
# =============================================================================


class TestPerAtomContributionTracker:
    def test_tracker_aggregates_records(self):
        tracker = PerAtomContributionTracker()
        for i in range(5):
            tracker.record_decision(_make_record(atom_id="atom_a", decision_id=f"d{i}"))
        for i in range(3):
            tracker.record_decision(_make_record(atom_id="atom_b", decision_id=f"d{i}"))

        assert tracker.n_decisions_total == 8
        assert set(tracker.atom_ids_observed) == {"atom_a", "atom_b"}

    def test_unknown_atom_returns_insufficient_data(self):
        tracker = PerAtomContributionTracker()
        contribution = tracker.compute_atom_contribution("atom_nonexistent")
        assert contribution.verdict == AtomVerdict.INSUFFICIENT_DATA
        assert contribution.n_decisions == 0

    def test_too_few_decisions_classifies_insufficient(self):
        """Below 30 decisions → INSUFFICIENT_DATA verdict."""
        tracker = PerAtomContributionTracker()
        for i in range(10):
            tracker.record_decision(_make_record(atom_id="atom_a", decision_id=f"d{i}"))
        contribution = tracker.compute_atom_contribution("atom_a")
        assert contribution.verdict == AtomVerdict.INSUFFICIENT_DATA

    def test_passing_atom_classifies_pass(self):
        """An atom meeting all 3 metrics → PASS verdict."""
        tracker = PerAtomContributionTracker()
        # Build 60 decisions: 30 high-confidence high-outcome,
        # 30 low-confidence low-outcome, all suppression-followed-no-backfire
        for i in range(30):
            tracker.record_decision(
                _make_record(
                    atom_id="atom_pass",
                    decision_id=f"high_{i}",
                    confidence=0.85,
                    outcome_value=0.95,
                    success=True,
                    suppress_mechs=["scarcity"],
                    mechanism_followed="authority",
                    backfire_signal=False,
                )
            )
        for i in range(30):
            tracker.record_decision(
                _make_record(
                    atom_id="atom_pass",
                    decision_id=f"low_{i}",
                    confidence=0.30,
                    outcome_value=0.20,
                    success=False,
                    suppress_mechs=["scarcity"],
                    mechanism_followed="authority",
                    backfire_signal=False,
                )
            )

        # Get the link_keys of the recorded chains so posteriors can be
        # supplied for metric 2
        records = tracker._records_by_atom["atom_pass"]
        all_link_keys = set()
        for r in records:
            all_link_keys.update(r.chain_attestation.theoretical_link_keys)
        # All posteriors above survival floor → metric 2 passes
        link_posteriors = {key: 0.85 for key in all_link_keys}

        contribution = tracker.compute_atom_contribution(
            "atom_pass", link_posteriors=link_posteriors
        )
        assert contribution.verdict == AtomVerdict.PASS
        assert contribution.prediction_lift_delta is not None
        assert contribution.prediction_lift_delta > 0.5
        assert contribution.chain_link_survival_rate == pytest.approx(1.0)
        assert contribution.direction_match_rate == pytest.approx(1.0)

    def test_failing_atom_classifies_fail(self):
        """An atom meeting 0 metrics → FAIL verdict."""
        tracker = PerAtomContributionTracker()
        # 30 high-conf low-outcome, 30 low-conf high-outcome (anti-predictive)
        # Suppressions never followed (L3 ignores)
        for i in range(30):
            tracker.record_decision(
                _make_record(
                    atom_id="atom_fail",
                    decision_id=f"a_{i}",
                    confidence=0.85,
                    outcome_value=0.20,
                    success=False,
                    suppress_mechs=["scarcity"],
                    mechanism_followed="scarcity",  # ignored suppression
                    backfire_signal=True,
                )
            )
        for i in range(30):
            tracker.record_decision(
                _make_record(
                    atom_id="atom_fail",
                    decision_id=f"b_{i}",
                    confidence=0.30,
                    outcome_value=0.95,
                    success=True,
                    suppress_mechs=["scarcity"],
                    mechanism_followed="scarcity",
                    backfire_signal=True,
                )
            )

        records = tracker._records_by_atom["atom_fail"]
        all_link_keys = set()
        for r in records:
            all_link_keys.update(r.chain_attestation.theoretical_link_keys)
        # Posteriors all below survival floor → metric 2 fails
        link_posteriors = {key: 0.20 for key in all_link_keys}

        contribution = tracker.compute_atom_contribution(
            "atom_fail", link_posteriors=link_posteriors
        )
        assert contribution.verdict == AtomVerdict.FAIL


# =============================================================================
# POST-PILOT DECISION TREE
# =============================================================================


class TestPostPilotDecisionTree:
    def _build_tracker_with_n_passing(self, n_pass: int, n_total: int):
        """Build a tracker where n_pass atoms pass and (n_total - n_pass) fail.
        Every atom has 60 decisions to be evaluable."""
        tracker = PerAtomContributionTracker()
        for k in range(n_total):
            atom_id = f"atom_{k}"
            passing = k < n_pass
            for i in range(30):
                tracker.record_decision(
                    _make_record(
                        atom_id=atom_id,
                        decision_id=f"{atom_id}_high_{i}",
                        confidence=0.85,
                        outcome_value=0.95 if passing else 0.20,
                        success=passing,
                        suppress_mechs=["scarcity"],
                        mechanism_followed="authority" if passing else "scarcity",
                        backfire_signal=not passing,
                    )
                )
            for i in range(30):
                tracker.record_decision(
                    _make_record(
                        atom_id=atom_id,
                        decision_id=f"{atom_id}_low_{i}",
                        confidence=0.30,
                        outcome_value=0.20 if passing else 0.95,
                        success=not passing,
                        suppress_mechs=["scarcity"],
                        mechanism_followed="authority" if passing else "scarcity",
                        backfire_signal=not passing,
                    )
                )
        # Build link_posteriors based on whether atom passes
        link_posteriors = {}
        for atom_id, records in tracker._records_by_atom.items():
            atom_passing = int(atom_id.split("_")[1]) < n_pass
            for r in records:
                for key in r.chain_attestation.theoretical_link_keys:
                    link_posteriors[key] = 0.85 if atom_passing else 0.20
        return tracker, link_posteriors

    def test_all_nine_pass_expand_full_audit(self):
        tracker, posteriors = self._build_tracker_with_n_passing(n_pass=9, n_total=9)
        decision, rationale, contributions = tracker.post_pilot_decision(
            link_posteriors=posteriors
        )
        assert decision == "expand_full_system_audit"
        assert all(c.verdict == AtomVerdict.PASS for c in contributions.values())

    def test_seven_pass_expand_selectively(self):
        tracker, posteriors = self._build_tracker_with_n_passing(n_pass=7, n_total=9)
        decision, _, contributions = tracker.post_pilot_decision(
            link_posteriors=posteriors
        )
        assert decision == "expand_selectively"

    def test_three_pass_stop_and_investigate(self):
        tracker, posteriors = self._build_tracker_with_n_passing(n_pass=3, n_total=9)
        decision, _, _ = tracker.post_pilot_decision(link_posteriors=posteriors)
        assert decision == "stop_and_investigate"

    def test_zero_pass_stop_and_investigate(self):
        tracker, posteriors = self._build_tracker_with_n_passing(n_pass=0, n_total=9)
        decision, _, _ = tracker.post_pilot_decision(link_posteriors=posteriors)
        assert decision == "stop_and_investigate"

    def test_insufficient_evaluable_atoms_returns_insufficient(self):
        """Only 2 atoms have enough decisions → can't decide."""
        tracker = PerAtomContributionTracker()
        for atom_id in ("atom_a", "atom_b"):
            for i in range(60):
                tracker.record_decision(
                    _make_record(
                        atom_id=atom_id,
                        decision_id=f"{atom_id}_{i}",
                        confidence=0.85,
                    )
                )
        decision, _, _ = tracker.post_pilot_decision()
        assert decision == "insufficient_data"


# =============================================================================
# CALIBRATION-MIX TRACKING
# =============================================================================


class TestCalibrationMixTracking:
    """Per-atom segmentation by pinned-only vs has-pilot-pending."""

    def test_pinned_only_vs_pending_counts(self):
        tracker = PerAtomContributionTracker()
        # Atom with mix of pinned-only and has-pending decisions
        for i in range(20):
            att = _make_attestation("atom_a", pinned_count=5, pending_count=0)
            record = AtomDecisionRecord(
                decision_id=f"pinned_{i}",
                atom_id="atom_a",
                chain_attestation=att,
                outcome_value=1.0,
                success=True,
            )
            tracker.record_decision(record)
        for i in range(15):
            att = _make_attestation("atom_a", pinned_count=3, pending_count=2)
            record = AtomDecisionRecord(
                decision_id=f"mixed_{i}",
                atom_id="atom_a",
                chain_attestation=att,
                outcome_value=1.0,
                success=True,
            )
            tracker.record_decision(record)

        contribution = tracker.compute_atom_contribution("atom_a")
        assert contribution.n_decisions == 35
        assert contribution.n_decisions_pinned_only == 20
        assert contribution.n_decisions_with_pending == 15
