# =============================================================================
# ADAM Ambiguity Attitude — Canonical Regression Tests
# Location: tests/unit/test_ambiguity_attitude_canonical.py
# =============================================================================

"""
CANONICAL REGRESSION TESTS — ambiguity_attitude (B3-LUXY Phase 2 atom 8)

Pins Ellsberg 1961 §IV ambiguity premium formula and Heath & Tversky
1991 §3 competence shift to the atom's implementation.

Anchors pinned:
- Ellsberg 1961 §IV: π = (EU_known - EU_unknown) / EU_unknown
- π > 0 ↔ ambiguity averse; π < 0 ↔ seeking; π = 0 ↔ neutral
- Heath & Tversky 1991 §3: high competence → ↑ tolerance
- Fox & Tversky 1995 §2: comparative frame amplifies positive premium
- Three-class trichotomy: averse / tolerant / seeking
"""

import pytest

from adam.atoms.core.ambiguity_attitude import (
    AMBIGUITY_MECHANISM_MAP,
    NDF_AMBIGUITY_MAP,
    _AMBIGUITY_AVERSE_THRESHOLD,
    _AMBIGUITY_SEEKING_THRESHOLD,
    _COMPETENCE_MAX_SHIFT,
    _apply_comparative_ignorance,
    _apply_competence_shift,
    _classify_ambiguity_attitude,
    _ellsberg_ambiguity_premium,
)
from adam.atoms.models.chain_attestation import (
    CalibrationStatus,
    RelationType,
)


# =============================================================================
# ELLSBERG 1961 §IV — AMBIGUITY PREMIUM
# =============================================================================


class TestEllsbergPremium:
    """Pin Ellsberg 1961 §IV canonical premium formula."""

    def test_neutral_when_eus_equal(self):
        """EU_known = EU_unknown → π = 0 (Savage axioms hold)."""
        assert _ellsberg_ambiguity_premium(0.5, 0.5) == pytest.approx(0.0)
        assert _ellsberg_ambiguity_premium(0.7, 0.7) == pytest.approx(0.0)

    def test_positive_when_known_higher_averse(self):
        """EU_known > EU_unknown → π > 0 (averse direction)."""
        assert _ellsberg_ambiguity_premium(eu_known=0.7, eu_unknown=0.5) > 0
        assert _ellsberg_ambiguity_premium(eu_known=0.8, eu_unknown=0.4) > 0

    def test_negative_when_unknown_higher_seeking(self):
        """EU_known < EU_unknown → π < 0 (seeking direction)."""
        assert _ellsberg_ambiguity_premium(eu_known=0.3, eu_unknown=0.7) < 0

    def test_canonical_calculation(self):
        """π = (0.7 - 0.4) / 0.4 = 0.75."""
        result = _ellsberg_ambiguity_premium(eu_known=0.7, eu_unknown=0.4)
        assert result == pytest.approx(0.75, abs=1e-9)

    def test_zero_unknown_returns_zero(self):
        """Defensive: EU_unknown = 0 → return 0 (cannot divide)."""
        assert _ellsberg_ambiguity_premium(eu_known=0.5, eu_unknown=0.0) == 0.0
        assert _ellsberg_ambiguity_premium(eu_known=0.5, eu_unknown=-0.1) == 0.0

    def test_premium_monotonic_in_known(self):
        """For fixed EU_unknown, premium increases with EU_known."""
        prior = -float("inf")
        for eu_k in [0.3, 0.4, 0.5, 0.6, 0.7]:
            p = _ellsberg_ambiguity_premium(eu_known=eu_k, eu_unknown=0.5)
            assert p >= prior
            prior = p


# =============================================================================
# HEATH & TVERSKY 1991 §3 — COMPETENCE SHIFT
# =============================================================================


class TestCompetenceShift:
    """Pin Heath & Tversky 1991 §3 competence-shift moderation."""

    def test_neutral_competence_no_shift(self):
        """competence = 0.5 → no shift."""
        assert _apply_competence_shift(0.4, competence=0.5) == pytest.approx(0.4)

    def test_high_competence_increases_tolerance(self):
        """High competence → tolerance increases."""
        baseline = 0.4
        high_comp = _apply_competence_shift(baseline, competence=1.0)
        assert high_comp > baseline

    def test_low_competence_decreases_tolerance(self):
        """Low competence → tolerance decreases."""
        baseline = 0.6
        low_comp = _apply_competence_shift(baseline, competence=0.0)
        assert low_comp < baseline

    def test_max_shift_bounded_by_constant(self):
        """Maximum shift bounded by _COMPETENCE_MAX_SHIFT."""
        baseline = 0.5
        max_comp = _apply_competence_shift(baseline, competence=1.0)
        # competence=1, shift = (1.0-0.5)*2*0.20 = 0.20
        assert max_comp == pytest.approx(0.5 + _COMPETENCE_MAX_SHIFT, abs=1e-9)

    def test_competence_shift_clamped_to_valid_range(self):
        """Effective tolerance ∈ [0.05, 0.95]."""
        result = _apply_competence_shift(0.95, competence=1.0)
        assert result <= 0.95
        result = _apply_competence_shift(0.05, competence=0.0)
        assert result >= 0.05


# =============================================================================
# FOX & TVERSKY 1995 §2 — COMPARATIVE IGNORANCE
# =============================================================================


class TestComparativeIgnorance:
    """Pin Fox & Tversky 1995 §2 comparative-frame amplification."""

    def test_no_amplification_when_not_comparative(self):
        """Non-comparative frame → premium unchanged."""
        assert _apply_comparative_ignorance(0.3, comparative_frame=False) == 0.3
        assert _apply_comparative_ignorance(-0.2, comparative_frame=False) == -0.2

    def test_amplifies_positive_premium_when_comparative(self):
        """Comparative frame → positive premium amplified by 1.3."""
        result = _apply_comparative_ignorance(0.3, comparative_frame=True)
        assert result == pytest.approx(0.39, abs=1e-9)

    def test_does_not_amplify_negative_premium(self):
        """Negative premium (seeking) NOT amplified by comparative frame."""
        # Fox & Tversky 1995 §2 specifies amplification of aversion only
        result = _apply_comparative_ignorance(-0.3, comparative_frame=True)
        assert result == -0.3

    def test_zero_premium_unchanged(self):
        """Zero premium stays zero regardless of frame."""
        assert _apply_comparative_ignorance(0.0, comparative_frame=True) == 0.0


# =============================================================================
# CLASSIFICATION TRICHOTOMY
# =============================================================================


class TestAmbiguityClassification:
    """Pin three-class averse/tolerant/seeking trichotomy."""

    def test_low_tolerance_classifies_averse(self):
        assert _classify_ambiguity_attitude(0.20) == "ambiguity_averse"
        assert _classify_ambiguity_attitude(_AMBIGUITY_AVERSE_THRESHOLD - 0.01) == "ambiguity_averse"

    def test_high_tolerance_classifies_seeking(self):
        assert _classify_ambiguity_attitude(0.80) == "ambiguity_seeking"
        assert _classify_ambiguity_attitude(_AMBIGUITY_SEEKING_THRESHOLD + 0.01) == "ambiguity_seeking"

    def test_moderate_tolerance_classifies_tolerant(self):
        assert _classify_ambiguity_attitude(0.50) == "ambiguity_tolerant"

    def test_at_averse_threshold_is_tolerant(self):
        """Boundary: tolerance = averse_threshold is tolerant (not <)."""
        assert _classify_ambiguity_attitude(_AMBIGUITY_AVERSE_THRESHOLD) == "ambiguity_tolerant"

    def test_at_seeking_threshold_is_tolerant(self):
        """Boundary: tolerance = seeking_threshold is tolerant (not >)."""
        assert _classify_ambiguity_attitude(_AMBIGUITY_SEEKING_THRESHOLD) == "ambiguity_tolerant"


# =============================================================================
# CHAIN ATTESTATION — STRUCTURAL & A14-FLAG INVARIANTS
# =============================================================================


class TestAmbiguityChainAttestation:
    """Pin the Ellsberg-canonical chain shape (5 links; L2+L3 PINNED)."""

    def _make_atom_with_state(self, is_novel=False, comparative_frame=False, competence=0.5):
        from unittest.mock import MagicMock, patch
        from adam.atoms.core.ambiguity_attitude import AmbiguityAttitudeAtom

        atom = AmbiguityAttitudeAtom(blackboard=MagicMock(), bridge=MagicMock())
        atom_input = MagicMock()
        atom_input.ad_context = {
            "is_new_category": is_novel,
            "comparative_frame": comparative_frame,
            "user_category_competence": competence,
        }
        atom_input.request_id = "req_test"
        atom_input.get_upstream = MagicMock(return_value=None)

        with patch(
            "adam.atoms.core.ambiguity_attitude.PsychologicalConstructResolver"
        ) as mock_psy_class:
            mock_psy = MagicMock()
            mock_psy.has_any = True
            mock_psy.as_full_construct_dict = MagicMock(return_value={
                "uncertainty_tolerance": 0.4,
                "approach_avoidance": 0.5,
                "cognitive_engagement": 0.6,
                "arousal_seeking": 0.5,
                "temporal_horizon": 0.5,
            })
            mock_psy_class.return_value = mock_psy
            ambiguity_state = atom._compute_ambiguity_state(atom_input)

        adjustments = atom._compute_mechanism_adjustments(ambiguity_state)
        return atom, atom_input, ambiguity_state, adjustments

    def test_chain_has_five_links(self):
        atom, atom_input, state, adj = self._make_atom_with_state()
        attestation = atom._build_chain_attestation(atom_input, state, adj)
        assert len(attestation.chain) == 5

    def test_chain_relation_type_sequence(self):
        atom, atom_input, state, adj = self._make_atom_with_state()
        attestation = atom._build_chain_attestation(atom_input, state, adj)
        expected = [
            RelationType.MODULATED_BY,  # L1: dispositional → baseline
            RelationType.MODULATED_BY,  # L2: competence → effective (PINNED)
            RelationType.PRODUCES,       # L3: effective × context → premium (PINNED)
            RelationType.PRODUCES,       # L4: premium → classification
            RelationType.PRODUCES,       # L5: classification → adjustments
        ]
        actual = [link.relation_type for link in attestation.chain]
        assert actual == expected

    def test_chain_pinned_at_canonical_steps(self):
        """L2 (Heath & Tversky competence) and L3 (Ellsberg formula) are PINNED."""
        atom, atom_input, state, adj = self._make_atom_with_state()
        attestation = atom._build_chain_attestation(atom_input, state, adj)
        statuses = [link.calibration_status for link in attestation.chain]
        assert statuses[1] == CalibrationStatus.PINNED  # L2 H&T
        assert statuses[2] == CalibrationStatus.PINNED  # L3 Ellsberg
        assert statuses[0] == CalibrationStatus.PILOT_PENDING
        assert statuses[3] == CalibrationStatus.PILOT_PENDING
        assert statuses[4] == CalibrationStatus.PILOT_PENDING

    def test_chain_provenance_lists_a14_flags(self):
        atom, atom_input, state, adj = self._make_atom_with_state()
        attestation = atom._build_chain_attestation(atom_input, state, adj)
        flags = set(attestation.provenance.a14_flags_active)
        assert "ELLSBERG_AMBIGUITY_PREMIUM_PILOT_PENDING" in flags
        assert "NDF_AMBIGUITY_WEIGHTS_PILOT_PENDING" in flags
        assert "COMPETENCE_AMBIGUITY_SHIFT_PILOT_PENDING" in flags
        assert "AMBIGUITY_CLASSIFICATION_THRESHOLDS_PILOT_PENDING" in flags
        assert "AMBIGUITY_MECHANISM_MAGNITUDES_PILOT_PENDING" in flags

    def test_chain_links_have_canonical_citations(self):
        atom, atom_input, state, adj = self._make_atom_with_state()
        attestation = atom._build_chain_attestation(atom_input, state, adj)
        canonical = {"Ellsberg", "Heath", "Tversky", "Fox", "Camerer"}
        for link in attestation.chain:
            assert link.citation
            assert any(c in link.citation for c in canonical), \
                f"Link missing canonical citation: {link.citation}"


# =============================================================================
# END-TO-END
# =============================================================================


class TestAmbiguityAttitudeIntegration:
    """End-to-end checks: novel category + low tolerance → certainty mechanisms."""

    def _make_atom(self):
        from unittest.mock import MagicMock
        from adam.atoms.core.ambiguity_attitude import AmbiguityAttitudeAtom
        return AmbiguityAttitudeAtom(blackboard=MagicMock(), bridge=MagicMock())

    def test_averse_user_boosted_certainty_mechanisms(self):
        atom = self._make_atom()
        state = {
            "baseline_tolerance": 0.20,
            "competence": 0.5,
            "effective_tolerance": 0.20,
            "context_ambiguity": 0.8,
            "eu_known": 0.20,
            "eu_unknown": 0.04,
            "ambiguity_premium": 4.0,
            "comparative_frame": False,
            "attitude": "ambiguity_averse",
            "ambiguity_gap": 0.64,
            "needs_certainty": True,
            "signal_quality": 1.0,
        }
        adj = atom._compute_mechanism_adjustments(state)
        assert adj.get("social_proof", 0.0) > 0
        assert adj.get("authority", 0.0) > 0
        assert adj.get("commitment", 0.0) > 0

    def test_seeking_user_boosted_novelty_mechanisms(self):
        atom = self._make_atom()
        state = {
            "baseline_tolerance": 0.85,
            "competence": 0.7,
            "effective_tolerance": 0.85,
            "context_ambiguity": 0.5,
            "eu_known": 0.85,
            "eu_unknown": 0.425,
            "ambiguity_premium": 1.0,
            "comparative_frame": False,
            "attitude": "ambiguity_seeking",
            "ambiguity_gap": 0.075,
            "needs_certainty": False,
            "signal_quality": 1.0,
        }
        adj = atom._compute_mechanism_adjustments(state)
        assert adj.get("attention_dynamics", 0.0) > 0
        assert adj.get("embodied_cognition", 0.0) > 0
        assert adj.get("commitment", 0.0) < 0  # boring for seekers

    def test_competence_shifts_attitude(self):
        """A user with low baseline tolerance + high competence has higher
        effective tolerance (Heath & Tversky 1991)."""
        atom, _, low_comp_state, _ = TestAmbiguityChainAttestation()._make_atom_with_state(
            competence=0.0
        )
        _, _, high_comp_state, _ = TestAmbiguityChainAttestation()._make_atom_with_state(
            competence=1.0
        )
        assert high_comp_state["effective_tolerance"] > low_comp_state["effective_tolerance"]
