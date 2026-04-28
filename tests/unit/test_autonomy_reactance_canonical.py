# =============================================================================
# ADAM Autonomy Reactance — Canonical Regression Tests
# Location: tests/unit/test_autonomy_reactance_canonical.py
# =============================================================================

"""
CANONICAL REGRESSION TESTS — autonomy_reactance (B3-LUXY Phase 0)

These tests pin the published anchors of the canonical reactance theory
to the atom's implementation. They are the discipline-rule (b) artifact
for the `autonomy_reactance` redo: regression tests pinning published
anchors, alongside (a) canonical formula in code with paper:section
citations and (c) calibration-pending flags on placeholder constants.

If any of these tests fail, the atom has drifted from canonical theory.
That is a defect, not a calibration question.

Anchors pinned:
- Brehm 1966 §1: reactance requires a valued freedom (I=0 → R=0)
- Brehm 1966 §1: reactance requires a threat (M=0 → R=0)
- Brehm & Brehm 1981 §3: R = I × M × P multiplicative structure
- Brehm & Brehm 1981 §3: monotonicity in I, M, P
- Brehm & Brehm 1981 §4: trait-state inversion (proneness ↔ threshold)
- Wicklund 1974 §6: boomerang sigmoid (P=0.5 at threshold; <<0.5 below;
  >>0.5 above)
- Miron & Brehm 2006 §4: repeat exposure amplifies P
- Steindl et al. 2015 §3: chain emits paper:section-grounded links
- Hong & Page 1989: HPRS proxy is PILOT_PENDING, not canonical
"""

import math

import pytest

from adam.atoms.core.autonomy_reactance import (
    MECHANISM_COERCIVENESS,
    _AUTONOMY_IMPORTANCE_DEFAULT,
    _BACKFIRE_SIGMOID_K,
    _P_BASELINE,
    _P_MAX,
    _P_REPEAT_AMPLIFIER_PER_EXPOSURE,
    _compute_backfire_probability,
    _compute_effective_threshold,
    _compute_propagation_factor,
    _compute_reactance_magnitude_brehm,
    _compute_reactance_proneness_proxy,
)
from adam.atoms.models.chain_attestation import (
    CalibrationStatus,
    ChainAttestation,
    ConstructLink,
    RelationType,
)


# =============================================================================
# BREHM 1966 / BREHM & BREHM 1981 — REACTANCE MAGNITUDE INVARIANTS
# =============================================================================


class TestBrehmReactanceFormula:
    """Pin the canonical R = I × M × P formula from Brehm 1966 +
    Brehm & Brehm 1981 §3."""

    def test_brehm_reactance_zero_when_importance_zero(self):
        """Brehm 1966 §1: no valued freedom → no reactance to threaten.
        R(I=0, M, P) = 0 for any M, P."""
        for M in (0.0, 0.3, 0.7, 1.0):
            for P in (1.0, 1.2, 1.5):
                assert _compute_reactance_magnitude_brehm(0.0, M, P) == 0.0

    def test_brehm_reactance_zero_when_threat_zero(self):
        """Brehm 1966 §1: no threat → no reactance.
        R(I, M=0, P) = 0 for any I, P."""
        for I in (0.0, 0.3, 0.7, 1.0):
            for P in (1.0, 1.2, 1.5):
                assert _compute_reactance_magnitude_brehm(I, 0.0, P) == 0.0

    def test_brehm_reactance_monotonic_in_threat_magnitude(self):
        """Brehm & Brehm 1981 §3: for fixed (I, P), R increases monotonically with M."""
        I, P = 0.7, 1.0
        prior = -1.0
        for M in [0.0, 0.1, 0.3, 0.5, 0.7, 0.9, 1.0]:
            R = _compute_reactance_magnitude_brehm(I, M, P)
            assert R >= prior, f"M={M} produced R={R} which is not >= prior R={prior}"
            prior = R

    def test_brehm_reactance_monotonic_in_importance(self):
        """Brehm & Brehm 1981 §3: for fixed (M, P), R increases monotonically with I."""
        M, P = 0.7, 1.0
        prior = -1.0
        for I in [0.0, 0.1, 0.3, 0.5, 0.7, 0.9, 1.0]:
            R = _compute_reactance_magnitude_brehm(I, M, P)
            assert R >= prior, f"I={I} produced R={R} which is not >= prior R={prior}"
            prior = R

    def test_brehm_reactance_multiplicative_not_additive(self):
        """Brehm 1966 §1.3: strong threat to unimportant freedom → minimal reactance.

        Key prediction distinguishing multiplicative from additive
        composition: if the formula were additive (R = αI + βM), then
        strong M with weak I would still produce substantial R. The
        multiplicative formula correctly predicts that low I × high M
        ≈ low M × high I ≈ small R.
        """
        # Strong threat × weak importance
        R_strong_M = _compute_reactance_magnitude_brehm(0.1, 1.0, 1.0)
        # Weak threat × strong importance
        R_strong_I = _compute_reactance_magnitude_brehm(1.0, 0.1, 1.0)
        # Both moderate
        R_balanced = _compute_reactance_magnitude_brehm(0.5, 0.5, 1.0)

        # Multiplicative: (0.1)(1.0) = (1.0)(0.1) = 0.1; (0.5)(0.5) = 0.25
        assert R_strong_M == pytest.approx(0.1, rel=0.01)
        assert R_strong_I == pytest.approx(0.1, rel=0.01)
        assert R_balanced == pytest.approx(0.25, rel=0.01)
        # Balanced moderate produces MORE reactance than extreme imbalance,
        # which only the multiplicative form predicts correctly.
        assert R_balanced > R_strong_M
        assert R_balanced > R_strong_I

    def test_brehm_reactance_clamped_to_unit_interval(self):
        """R ∈ [0, 1] regardless of P > 1 amplification."""
        # Even with maximum P, R cannot exceed 1.0
        R = _compute_reactance_magnitude_brehm(1.0, 1.0, _P_MAX)
        assert 0.0 <= R <= 1.0


# =============================================================================
# BREHM & BREHM 1981 — TRAIT-STATE INVERSION
# =============================================================================


class TestProneessThresholdInversion:
    """Pin the trait-state relationship: high proneness → low threshold
    (Brehm & Brehm 1981 §4)."""

    def test_high_proneness_produces_low_threshold(self):
        """Brehm & Brehm 1981 §4: high trait reactance → low situational threshold."""
        threshold_high_prone = _compute_effective_threshold(0.9)
        threshold_low_prone = _compute_effective_threshold(0.1)
        assert threshold_high_prone < threshold_low_prone

    def test_threshold_inversion_is_monotonic(self):
        """Threshold strictly decreases as proneness increases."""
        prior_threshold = float("inf")
        for proneness in [0.1, 0.2, 0.5, 0.7, 0.9]:
            t = _compute_effective_threshold(proneness)
            assert t < prior_threshold
            prior_threshold = t


# =============================================================================
# WICKLUND 1974 §6 — BOOMERANG SIGMOID
# =============================================================================


class TestWicklundBackfire:
    """Pin Wicklund 1974 §6 boomerang behavior — when reactance exceeds
    threshold, response reverses. Sigmoid transition with k = _BACKFIRE_SIGMOID_K
    (PILOT_PENDING)."""

    def test_wicklund_backfire_at_threshold_half(self):
        """Sigmoid pin: P(R = threshold) = 0.5."""
        for threshold in [0.2, 0.5, 0.8]:
            p = _compute_backfire_probability(
                reactance_magnitude=threshold,
                effective_threshold=threshold,
            )
            assert p == pytest.approx(0.5, abs=1e-9)

    def test_wicklund_backfire_well_below_threshold_low(self):
        """For R well below threshold, P(backfire) < 0.05."""
        # delta = -1.0, sigmoid(5 * -1.0) = sigmoid(-5) ≈ 0.0067
        p = _compute_backfire_probability(
            reactance_magnitude=0.0,
            effective_threshold=1.0,
        )
        assert p < 0.05

    def test_wicklund_backfire_well_above_threshold_high(self):
        """For R well above threshold, P(backfire) > 0.95."""
        # delta = +1.0, sigmoid(5 * 1.0) ≈ 0.9933
        p = _compute_backfire_probability(
            reactance_magnitude=1.0,
            effective_threshold=0.0,
        )
        assert p > 0.95

    def test_wicklund_backfire_monotonic_in_reactance(self):
        """For fixed threshold, P(backfire) monotonically increases with R."""
        threshold = 0.5
        prior = -1.0
        for R in [0.0, 0.1, 0.3, 0.5, 0.7, 0.9, 1.0]:
            p = _compute_backfire_probability(R, threshold)
            assert p >= prior, f"R={R}: P={p} not >= prior P={prior}"
            prior = p


# =============================================================================
# MIRON & BREHM 2006 §4 — REPEAT-EXPOSURE PROPAGATION
# =============================================================================


class TestPropagationFactor:
    """Pin the P amplification under repeat exposure (Miron & Brehm 2006
    §4). Magnitude is PILOT_PENDING but structure is PINNED."""

    def test_propagation_baseline_is_one(self):
        """Single exposure: P = 1.0 (no pattern, no amplification)."""
        assert _compute_propagation_factor(1) == pytest.approx(_P_BASELINE)

    def test_propagation_amplified_by_repeat_exposure(self):
        """Multi-exposure: P > 1.0."""
        for n in [2, 3, 5, 10]:
            P = _compute_propagation_factor(n)
            assert P > _P_BASELINE

    def test_propagation_saturates(self):
        """P does not grow without bound — saturates at _P_MAX."""
        P = _compute_propagation_factor(100)
        assert P <= _P_MAX

    def test_propagation_monotonic(self):
        """P monotonically non-decreasing in exposure count."""
        prior = 0.0
        for n in [1, 2, 3, 5, 10, 100]:
            P = _compute_propagation_factor(n)
            assert P >= prior
            prior = P


# =============================================================================
# HONG & PAGE 1989 — HPRS PROXY (PILOT_PENDING)
# =============================================================================


class TestProneessProxy:
    """The proneness proxy is PILOT_PENDING — these tests pin its
    structural properties, not specific values. HPRS itself is the
    canonical instrument; our proxy from NDF dimensions is documented
    as a placeholder pending pilot calibration."""

    def test_proneness_clamped_to_valid_range(self):
        """Proneness ∈ [0.1, 0.9] for any input combination."""
        for ce in [0.0, 0.5, 1.0]:
            for aa in [0.0, 0.5, 1.0]:
                for ut in [0.0, 0.5, 1.0]:
                    for aas in [0.0, 0.5, 1.0]:
                        p = _compute_reactance_proneness_proxy(ce, aa, ut, aas)
                        assert 0.1 <= p <= 0.9

    def test_proneness_high_ce_increases_proneness(self):
        """Theory: high cognitive engagement → detects manipulation → ↑ proneness."""
        low_ce = _compute_reactance_proneness_proxy(0.0, 0.5, 0.5, 0.5)
        high_ce = _compute_reactance_proneness_proxy(1.0, 0.5, 0.5, 0.5)
        assert high_ce > low_ce

    def test_proneness_high_aa_decreases_proneness(self):
        """Theory: high approach motivation → tolerates pressure → ↓ proneness."""
        low_aa = _compute_reactance_proneness_proxy(0.5, 0.0, 0.5, 0.5)
        high_aa = _compute_reactance_proneness_proxy(0.5, 1.0, 0.5, 0.5)
        assert high_aa < low_aa

    def test_proneness_high_ut_decreases_proneness(self):
        """Theory: uncertainty-tolerant users tolerate pressure → ↓ proneness."""
        low_ut = _compute_reactance_proneness_proxy(0.5, 0.5, 0.0, 0.5)
        high_ut = _compute_reactance_proneness_proxy(0.5, 0.5, 1.0, 0.5)
        assert high_ut < low_ut

    def test_proneness_high_arousal_seeking_decreases_proneness(self):
        """Theory: thrill-seekers handle pressure → ↓ proneness."""
        low_as = _compute_reactance_proneness_proxy(0.5, 0.5, 0.5, 0.0)
        high_as = _compute_reactance_proneness_proxy(0.5, 0.5, 0.5, 1.0)
        assert high_as < low_as

    def test_proneness_neutral_inputs_near_baseline(self):
        """All inputs at 0.5 → proneness near 0.5 baseline."""
        p = _compute_reactance_proneness_proxy(0.5, 0.5, 0.5, 0.5)
        assert p == pytest.approx(0.5, abs=0.05)


# =============================================================================
# CHAIN ATTESTATION — STRUCTURAL & INTEGRATION-CONTRACT INVARIANTS
# =============================================================================


def _make_synthetic_chain() -> ChainAttestation:
    """Build a synthetic ChainAttestation directly (without instantiating
    the full atom — that requires Blackboard/Bridge mocks). Used for
    schema-level invariant checks."""
    from adam.atoms.models.chain_attestation import (
        AdjustmentEvidence,
        ChainProvenance,
        TypedEvidence,
    )

    chain = [
        ConstructLink(
            source_construct="user_dispositional_signals",
            relation_type=RelationType.MODULATED_BY,
            target_construct="reactance_proneness",
            evidence_value=0.6,
            confidence=0.7,
            citation="Hong & Page 1989 (HPRS instrument)",
            calibration_status=CalibrationStatus.PILOT_PENDING,
        ),
        ConstructLink(
            source_construct="reactance_proneness",
            relation_type=RelationType.MODULATED_BY,
            target_construct="effective_threshold",
            evidence_value=0.4,
            confidence=0.7,
            citation="Brehm & Brehm 1981 §4",
            calibration_status=CalibrationStatus.PINNED,
        ),
        ConstructLink(
            source_construct="mechanism_coerciveness",
            relation_type=RelationType.THREATENS,
            target_construct="autonomy_freedom",
            evidence_value=0.5,
            confidence=0.6,
            citation="Brehm 1966 §1.2",
            calibration_status=CalibrationStatus.PILOT_PENDING,
        ),
    ]
    final = TypedEvidence(
        construct="reactance_threshold",
        value=0.7,
        confidence=0.65,
        citation="Wicklund 1974 §6",
        calibration_status=CalibrationStatus.PILOT_PENDING,
    )
    provenance = ChainProvenance(
        atom_id="atom_autonomy_reactance",
        atom_version="2.0",
    )
    return ChainAttestation(
        atom_id="atom_autonomy_reactance",
        request_id="test_req",
        target_construct="reactance_threshold",
        chain=chain,
        final_assessment=final,
        provenance=provenance,
    )


class TestChainAttestationContract:
    """Pin the integration-contract invariants of the chain-attestation
    primitive. These are schema-level guarantees that downstream
    consumers (L3 cascade, TheoryLearner, contribution measurement)
    rely on."""

    def test_link_key_matches_theory_learner_format(self):
        """LinkPosterior key format: '{relation}:{source}:{target}'."""
        link = ConstructLink(
            source_construct="user_dispositional_signals",
            relation_type=RelationType.MODULATED_BY,
            target_construct="reactance_proneness",
            evidence_value=0.6,
            confidence=0.7,
            citation="Hong & Page 1989",
        )
        assert link.link_key == "MODULATED_BY:user_dispositional_signals:reactance_proneness"

    def test_chain_to_chain_data_has_required_keys(self):
        """TheoryLearner.process_chain_outcome expects:
        chain_id, theoretical_link_keys, recommended_mechanism."""
        attestation = _make_synthetic_chain()
        chain_data = attestation.to_chain_data(recommended_mechanism="storytelling")
        assert "chain_id" in chain_data
        assert "theoretical_link_keys" in chain_data
        assert "recommended_mechanism" in chain_data
        assert chain_data["recommended_mechanism"] == "storytelling"

    def test_theoretical_link_keys_match_chain_order(self):
        """theoretical_link_keys preserves chain order (load-bearing
        for per-link credit attribution)."""
        attestation = _make_synthetic_chain()
        keys = attestation.theoretical_link_keys
        assert len(keys) == len(attestation.chain)
        for i, link in enumerate(attestation.chain):
            assert keys[i] == link.link_key

    def test_every_link_has_non_empty_citation(self):
        """Discipline rule (a) at the schema level: every link must have
        a paper:section citation."""
        attestation = _make_synthetic_chain()
        for link in attestation.chain:
            assert link.citation
            assert len(link.citation) > 5  # substantive, not just "x"

    def test_pilot_pending_links_detected(self):
        """has_pilot_pending_links() correctly flags mixed-calibration chains."""
        attestation = _make_synthetic_chain()
        # Synthetic chain has both PINNED and PILOT_PENDING links
        assert attestation.has_pilot_pending_links() is True

    def test_chain_summary_human_readable(self):
        """chain_summary() produces a left-to-right arrow-formatted string."""
        attestation = _make_synthetic_chain()
        summary = attestation.chain_summary()
        assert "user_dispositional_signals" in summary
        assert "MODULATED_BY" in summary
        assert "reactance_proneness" in summary
        assert "->" in summary


# =============================================================================
# ATOM-LEVEL CHAIN EMISSION — SYNTHETIC INPUT END-TO-END
# =============================================================================


class TestAtomChainEmission:
    """Pin the atom's chain-attestation emission shape (5 links, expected
    relations, all pilot-pending flags surfaced)."""

    def _make_atom_with_state(
        self,
        proneness: float = 0.5,
        exposure_count: int = 1,
    ):
        """Construct the atom with mocked Blackboard/Bridge — only used
        to exercise the chain-construction methods, not the full
        execution flow."""
        from unittest.mock import MagicMock

        from adam.atoms.core.autonomy_reactance import AutonomyReactanceAtom

        atom = AutonomyReactanceAtom(
            blackboard=MagicMock(),
            bridge=MagicMock(),
        )

        user_state = {
            "proneness": proneness,
            "threshold": 1.0 - proneness,
            "persuasion_knowledge": 0.5,
            "exposure_count": float(exposure_count),
            "signal_quality": 1.0,
            "pk_from_upstream": 0.0,
            "ndf_ce": 0.5,
            "ndf_aa": 0.5,
            "ndf_ut": 0.5,
            "ndf_aas": 0.5,
        }
        per_mechanism = atom._compute_per_mechanism_backfire(user_state)
        return atom, user_state, per_mechanism

    def test_chain_has_five_links(self):
        """B3-LUXY Phase 0 chain shape: exactly 5 links."""
        from unittest.mock import MagicMock

        atom, state, per_m = self._make_atom_with_state()
        atom_input = MagicMock()
        atom_input.request_id = "req_test"
        attestation = atom._build_chain_attestation(atom_input, state, per_m)
        assert len(attestation.chain) == 5

    def test_chain_has_expected_relation_types(self):
        """Pin the relation-type sequence of the autonomy_reactance chain."""
        from unittest.mock import MagicMock

        atom, state, per_m = self._make_atom_with_state()
        atom_input = MagicMock()
        atom_input.request_id = "req_test"
        attestation = atom._build_chain_attestation(atom_input, state, per_m)

        expected = [
            RelationType.MODULATED_BY,   # L1: dispositional → proneness
            RelationType.MODULATED_BY,   # L2: proneness → threshold
            RelationType.THREATENS,      # L3: coerciveness → freedom
            RelationType.AMPLIFIES,      # L4: threat × PK → magnitude
            RelationType.PRODUCES,       # L5: magnitude > threshold → backfire
        ]
        actual = [link.relation_type for link in attestation.chain]
        assert actual == expected

    def test_chain_provenance_lists_all_a14_flags(self):
        """All four atom-level A14 flags present in provenance."""
        from unittest.mock import MagicMock

        atom, state, per_m = self._make_atom_with_state()
        atom_input = MagicMock()
        atom_input.request_id = "req_test"
        attestation = atom._build_chain_attestation(atom_input, state, per_m)

        flags = set(attestation.provenance.a14_flags_active)
        assert "REACTANCE_THRESHOLD_COEFFICIENTS_PILOT_PENDING" in flags
        assert "MECHANISM_COERCIVENESS_LITERATURE_MIDPOINTS_PILOT_PENDING" in flags
        assert "BACKFIRE_SIGMOID_STEEPNESS_PILOT_PENDING" in flags
        assert "PROPAGATION_FACTOR_REPEAT_EXPOSURE_PILOT_PENDING" in flags

    def test_chain_emits_pinned_and_pilot_pending_mix(self):
        """Mixed calibration: L2 and L4 PINNED (canonical structure);
        L1, L3, L5 PILOT_PENDING (placeholder magnitudes)."""
        from unittest.mock import MagicMock

        atom, state, per_m = self._make_atom_with_state()
        atom_input = MagicMock()
        atom_input.request_id = "req_test"
        attestation = atom._build_chain_attestation(atom_input, state, per_m)

        statuses = [link.calibration_status for link in attestation.chain]
        assert statuses[0] == CalibrationStatus.PILOT_PENDING  # L1 HPRS proxy
        assert statuses[1] == CalibrationStatus.PINNED          # L2 inversion
        assert statuses[2] == CalibrationStatus.PILOT_PENDING  # L3 coerciveness
        assert statuses[3] == CalibrationStatus.PINNED          # L4 Brehm structure
        assert statuses[4] == CalibrationStatus.PILOT_PENDING  # L5 sigmoid steepness

    def test_high_coercive_mechanisms_get_negative_adjustment_when_proneness_high(self):
        """Wicklund 1974 §6: high-proneness user + high-coerciveness mechanism
        → reactance exceeds threshold → backfire predicted → negative adjustment."""
        atom, state, per_m = self._make_atom_with_state(proneness=0.8)

        # Scarcity (coerciveness 0.85) and urgency (0.90) should be flagged
        assert per_m["scarcity"]["adjustment"] < 0
        assert per_m["urgency"]["adjustment"] < 0

    def test_low_coercive_mechanisms_get_zero_or_positive_adjustment_when_proneness_high(self):
        """High-proneness user + autonomy-preserving mechanism → boost
        the alternative."""
        atom, state, per_m = self._make_atom_with_state(proneness=0.8)

        # Storytelling (0.10), embodied_cognition (0.10), unity (0.15)
        # should NOT be penalized when reactance is high.
        assert per_m["storytelling"]["adjustment"] >= 0
        assert per_m["embodied_cognition"]["adjustment"] >= 0
        assert per_m["unity"]["adjustment"] >= 0

    def test_low_proneness_user_no_backfire_for_moderate_mechanism(self):
        """Low-proneness user (high tolerance) → moderate-coerciveness
        mechanism produces low backfire probability."""
        atom, state, per_m = self._make_atom_with_state(proneness=0.2)
        # Authority (coerciveness 0.5) on tolerant user — should NOT
        # be predicted to backfire.
        assert per_m["authority"]["backfire_probability"] < 0.5


# =============================================================================
# SCHEMA-CONTRACT ROUND-TRIPPING
# =============================================================================


class TestChainAttestationSerialization:
    """Pydantic round-trip + JSON serialization invariants — load-bearing
    for blackboard persistence and dashboard rendering."""

    def test_chain_attestation_pydantic_round_trip(self):
        """ChainAttestation can be dumped and reloaded without information loss."""
        original = _make_synthetic_chain()
        dumped = original.model_dump()
        rehydrated = ChainAttestation(**dumped)

        assert rehydrated.atom_id == original.atom_id
        assert len(rehydrated.chain) == len(original.chain)
        assert rehydrated.theoretical_link_keys == original.theoretical_link_keys

    def test_to_chain_data_is_json_serializable(self):
        """chain_data dict (the TheoryLearner contract) must be JSON-serializable
        end-to-end — used by Redis persistence."""
        import json

        attestation = _make_synthetic_chain()
        chain_data = attestation.to_chain_data(recommended_mechanism="authority")
        # No exception means it's JSON-serializable
        encoded = json.dumps(chain_data)
        decoded = json.loads(encoded)
        assert decoded["chain_id"] == attestation.attestation_id
        assert decoded["theoretical_link_keys"] == attestation.theoretical_link_keys
