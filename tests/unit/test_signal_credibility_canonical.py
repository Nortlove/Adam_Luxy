# =============================================================================
# ADAM Signal Credibility — Canonical Regression Tests
# Location: tests/unit/test_signal_credibility_canonical.py
# =============================================================================

"""
CANONICAL REGRESSION TESTS — signal_credibility (B3-LUXY Phase 2 atom 6)

Pins Spence 1973 §2.3 separating-equilibrium inequality and Zahavi 1975
handicap-principle proportionality to the atom's implementation.

Anchors pinned:
- Spence 1973 §2.3: separating equilibrium iff c_L > b > c_H
- Spence 1973 §3: credibility = sqrt((c_L - b)(b - c_H)) when separating
- Spence pooling: credibility = 0 when separating equilibrium fails
- Zahavi 1975: handicap factor = (c_L - c_H) / (c_L + c_H); reliable
  signaling requires factor > threshold
- Kirmani & Rao 2000: warranty has high handicap; cheap_talk has near-zero
"""

import math

import pytest

from adam.atoms.core.signal_credibility import (
    SIGNAL_COST_PARAMETERS,
    _HANDICAP_PROPORTIONALITY_THRESHOLD,
    _benefit_from_user_sensitivity,
    _spence_credibility_score,
    _spence_separating_equilibrium_satisfied,
    _zahavi_handicap_factor,
)
from adam.atoms.models.chain_attestation import (
    CalibrationStatus,
    RelationType,
)


# =============================================================================
# SPENCE 1973 §2.3 — SEPARATING EQUILIBRIUM
# =============================================================================


class TestSpenceSeparatingEquilibrium:
    """Pin Spence 1973 §2.3 canonical inequality c_L > b > c_H."""

    def test_separating_equilibrium_satisfied_canonical_case(self):
        """c_L=0.85, b=0.50, c_H=0.10 → separates."""
        assert _spence_separating_equilibrium_satisfied(c_L=0.85, b=0.50, c_H=0.10) is True

    def test_pooling_when_low_cost_below_benefit(self):
        """c_L ≤ b → low-quality types can profitably mimic → pools."""
        assert _spence_separating_equilibrium_satisfied(c_L=0.40, b=0.50, c_H=0.10) is False
        # boundary: equality also pools
        assert _spence_separating_equilibrium_satisfied(c_L=0.50, b=0.50, c_H=0.10) is False

    def test_pooling_when_benefit_below_high_cost(self):
        """b ≤ c_H → high-quality types won't bother → no signaling."""
        assert _spence_separating_equilibrium_satisfied(c_L=0.85, b=0.05, c_H=0.10) is False
        # boundary: equality also pools
        assert _spence_separating_equilibrium_satisfied(c_L=0.85, b=0.10, c_H=0.10) is False

    def test_pooling_when_costs_equal(self):
        """c_L = c_H → no cost differential → pools at any b."""
        assert _spence_separating_equilibrium_satisfied(c_L=0.5, b=0.50, c_H=0.5) is False

    def test_pooling_when_low_cost_below_high_cost(self):
        """Perverse case: c_L < c_H → low types pay LESS → can't separate."""
        assert _spence_separating_equilibrium_satisfied(c_L=0.20, b=0.50, c_H=0.80) is False


# =============================================================================
# SPENCE 1973 §3 — CREDIBILITY MAGNITUDE
# =============================================================================


class TestSpenceCredibilityMagnitude:
    """Pin Spence 1973 §3 credibility-as-margin operationalization."""

    def test_credibility_zero_when_pooling(self):
        """Pooling → credibility = 0."""
        assert _spence_credibility_score(c_L=0.40, b=0.50, c_H=0.30) == 0.0
        assert _spence_credibility_score(c_L=0.85, b=0.10, c_H=0.10) == 0.0

    def test_credibility_positive_when_separating(self):
        """Separating equilibrium → credibility > 0."""
        cred = _spence_credibility_score(c_L=0.85, b=0.50, c_H=0.10)
        assert cred > 0.0

    def test_credibility_geometric_mean_of_margins(self):
        """credibility = sqrt((c_L - b)(b - c_H)).
        With c_L=0.85, b=0.50, c_H=0.10:
            margin_low = 0.35
            margin_high = 0.40
            credibility = sqrt(0.35 × 0.40) = sqrt(0.14) ≈ 0.374
        """
        cred = _spence_credibility_score(c_L=0.85, b=0.50, c_H=0.10)
        expected = math.sqrt(0.35 * 0.40)
        assert cred == pytest.approx(expected, abs=1e-6)

    def test_credibility_increases_with_low_margin(self):
        """For fixed b, c_H: increasing c_L → larger c_L - b margin → higher credibility."""
        cred_low_cL = _spence_credibility_score(c_L=0.55, b=0.50, c_H=0.10)
        cred_high_cL = _spence_credibility_score(c_L=0.95, b=0.50, c_H=0.10)
        assert cred_high_cL > cred_low_cL

    def test_credibility_clamped_to_unit(self):
        """Credibility ∈ [0, 1] for any valid input."""
        cred = _spence_credibility_score(c_L=1.0, b=0.5, c_H=0.0)
        assert 0.0 <= cred <= 1.0


# =============================================================================
# ZAHAVI 1975 — HANDICAP PROPORTIONALITY
# =============================================================================


class TestZahaviHandicap:
    """Pin Zahavi 1975 handicap-factor formula and threshold."""

    def test_handicap_zero_when_costs_equal(self):
        """c_L = c_H → handicap factor = 0 (no proportionality)."""
        assert _zahavi_handicap_factor(c_L=0.5, c_H=0.5) == pytest.approx(0.0)

    def test_handicap_one_when_high_quality_costless(self):
        """c_H = 0 → handicap factor = 1 (perfect handicap)."""
        assert _zahavi_handicap_factor(c_L=0.5, c_H=0.0) == pytest.approx(1.0)

    def test_handicap_negative_when_costs_perverse(self):
        """c_H > c_L → handicap factor < 0 (high types pay more, broken)."""
        assert _zahavi_handicap_factor(c_L=0.2, c_H=0.8) < 0.0

    def test_handicap_warranty_high(self):
        """Warranty: c_L=0.85, c_H=0.10 → handicap = 0.75/0.95 ≈ 0.79."""
        params = SIGNAL_COST_PARAMETERS["warranty"]
        h = _zahavi_handicap_factor(c_L=params["c_L"], c_H=params["c_H"])
        assert h > 0.7

    def test_handicap_cheap_talk_low(self):
        """Cheap talk: c_L ≈ c_H ≈ 0 → handicap factor ≈ 0 → unreliable."""
        params = SIGNAL_COST_PARAMETERS["cheap_talk"]
        h = _zahavi_handicap_factor(c_L=params["c_L"], c_H=params["c_H"])
        assert h < _HANDICAP_PROPORTIONALITY_THRESHOLD

    def test_handicap_threshold_between_warranty_and_cheap_talk(self):
        """The proportionality threshold separates reliable from unreliable signals."""
        warranty_h = _zahavi_handicap_factor(
            c_L=SIGNAL_COST_PARAMETERS["warranty"]["c_L"],
            c_H=SIGNAL_COST_PARAMETERS["warranty"]["c_H"],
        )
        cheap_h = _zahavi_handicap_factor(
            c_L=SIGNAL_COST_PARAMETERS["cheap_talk"]["c_L"],
            c_H=SIGNAL_COST_PARAMETERS["cheap_talk"]["c_H"],
        )
        assert warranty_h > _HANDICAP_PROPORTIONALITY_THRESHOLD > cheap_h


# =============================================================================
# SIGNAL COST PARAMETERS — STRUCTURAL INVARIANTS
# =============================================================================


class TestSignalCostStructure:
    """Pin structural invariants on SIGNAL_COST_PARAMETERS."""

    def test_warranty_handicap_satisfies_separating_equilibrium_for_typical_b(self):
        """Warranty (c_L=0.85, c_H=0.10) should separate for typical b ∈ [0.4, 0.7]."""
        params = SIGNAL_COST_PARAMETERS["warranty"]
        for b in [0.40, 0.50, 0.60, 0.70]:
            assert _spence_separating_equilibrium_satisfied(
                c_L=params["c_L"], b=b, c_H=params["c_H"]
            )

    def test_cheap_talk_never_separates(self):
        """Cheap talk has c_L ≈ c_H so cannot separate at any reasonable b."""
        params = SIGNAL_COST_PARAMETERS["cheap_talk"]
        for b in [0.10, 0.30, 0.50, 0.70, 0.90]:
            # If b is between the tiny c_H and c_L, technically could
            # "separate" mathematically but the gap is so small it's useless.
            # The key invariant: the credibility SCORE is near zero.
            cred = _spence_credibility_score(
                c_L=params["c_L"], b=b, c_H=params["c_H"]
            )
            assert cred < 0.05

    def test_premium_pricing_separates_at_high_b(self):
        """Price premium (c_L=0.80, c_H=0.15) separates at typical b."""
        params = SIGNAL_COST_PARAMETERS["price_premium"]
        assert _spence_separating_equilibrium_satisfied(
            c_L=params["c_L"], b=0.50, c_H=params["c_H"]
        )

    def test_all_costly_signals_have_substantial_handicap(self):
        """All canonical costly signals (warranty, premium, brand_invest,
        transparency, third_party) have handicap > threshold."""
        for stype in ["warranty", "price_premium", "brand_investment",
                      "transparency", "third_party_validation"]:
            params = SIGNAL_COST_PARAMETERS[stype]
            h = _zahavi_handicap_factor(c_L=params["c_L"], c_H=params["c_H"])
            assert h > _HANDICAP_PROPORTIONALITY_THRESHOLD, \
                f"{stype}: handicap {h:.2f} below threshold"


# =============================================================================
# CHAIN ATTESTATION — STRUCTURAL & A14-FLAG INVARIANTS
# =============================================================================


class TestSignalCredibilityChainAttestation:
    """Pin the Spence-canonical chain shape (5 links, L3 + L4 PINNED)."""

    def _make_atom_with_state(self):
        from unittest.mock import MagicMock, patch
        from adam.atoms.core.signal_credibility import SignalCredibilityAtom

        atom = SignalCredibilityAtom(blackboard=MagicMock(), bridge=MagicMock())
        atom_input = MagicMock()
        atom_input.ad_context = {
            "category": "Luxury",
            "product_description": "Premium handcraft luxury exclusive",
            "creative_text": "Risk-free guarantee, certified",
        }
        atom_input.request_id = "req_test"
        # No upstream brand_personality
        atom_input.get_upstream = MagicMock(return_value=None)

        with patch(
            "adam.atoms.core.signal_credibility.PsychologicalConstructResolver"
        ) as mock_psy_class:
            mock_psy = MagicMock()
            mock_psy.has_any = True
            mock_psy.uncertainty_tolerance = 0.3  # → high sensitivity
            mock_psy.cognitive_engagement = 0.7
            mock_psy.status_sensitivity = 0.6
            mock_psy.approach_avoidance = 0.5
            mock_psy_class.return_value = mock_psy
            user_sensitivity = atom._assess_user_sensitivity(atom_input)

        brand_signals = atom._detect_brand_signals(atom_input)
        per_signal = atom._compute_per_signal_credibility(
            brand_signals, user_sensitivity["overall"]
        )
        adjustments = atom._compute_mechanism_adjustments(
            per_signal, user_sensitivity["overall"]
        )

        return atom, atom_input, user_sensitivity, per_signal, adjustments

    def test_chain_has_five_links(self):
        atom, atom_input, sens, per_signal, adj = self._make_atom_with_state()
        attestation = atom._build_chain_attestation(atom_input, sens, per_signal, adj)
        assert len(attestation.chain) == 5

    def test_chain_relation_type_sequence(self):
        atom, atom_input, sens, per_signal, adj = self._make_atom_with_state()
        attestation = atom._build_chain_attestation(atom_input, sens, per_signal, adj)
        expected = [
            RelationType.PRODUCES,        # L1: signals → cost_estimates
            RelationType.MODULATED_BY,    # L2: costs × sensitivity → benefit
            RelationType.PRODUCES,        # L3: (c_L,b,c_H) → separating_equilibrium (PINNED)
            RelationType.MODULATED_BY,    # L4: separating → handicap_validated (PINNED)
            RelationType.PRODUCES,        # L5: validated → adjustments
        ]
        actual = [link.relation_type for link in attestation.chain]
        assert actual == expected

    def test_chain_pinned_at_canonical_steps(self):
        """L3 (Spence inequality) and L4 (Zahavi handicap) are PINNED."""
        atom, atom_input, sens, per_signal, adj = self._make_atom_with_state()
        attestation = atom._build_chain_attestation(atom_input, sens, per_signal, adj)
        statuses = [link.calibration_status for link in attestation.chain]
        assert statuses[2] == CalibrationStatus.PINNED  # L3 Spence
        assert statuses[3] == CalibrationStatus.PINNED  # L4 Zahavi
        assert statuses[0] == CalibrationStatus.PILOT_PENDING
        assert statuses[1] == CalibrationStatus.PILOT_PENDING
        assert statuses[4] == CalibrationStatus.PILOT_PENDING

    def test_chain_provenance_lists_a14_flags(self):
        atom, atom_input, sens, per_signal, adj = self._make_atom_with_state()
        attestation = atom._build_chain_attestation(atom_input, sens, per_signal, adj)
        flags = set(attestation.provenance.a14_flags_active)
        assert "SPENCE_COST_CURVES_PILOT_PENDING" in flags
        assert "SIGNAL_BENEFIT_FROM_SENSITIVITY_PILOT_PENDING" in flags
        assert "HANDICAP_PROPORTIONALITY_FACTOR_PILOT_PENDING" in flags
        assert "KIRMANI_RAO_MECHANISM_MAPPINGS_PILOT_PENDING" in flags

    def test_chain_links_have_canonical_citations(self):
        atom, atom_input, sens, per_signal, adj = self._make_atom_with_state()
        attestation = atom._build_chain_attestation(atom_input, sens, per_signal, adj)
        canonical = {"Spence", "Zahavi", "Kirmani", "Connelly"}
        for link in attestation.chain:
            assert link.citation
            assert any(a in link.citation for a in canonical), \
                f"Link missing canonical citation: {link.citation}"


# =============================================================================
# END-TO-END INTEGRATION
# =============================================================================


class TestSignalCredibilityIntegration:
    """End-to-end checks that the atom produces sensible Spence/Zahavi output."""

    def _make_atom(self):
        from unittest.mock import MagicMock
        from adam.atoms.core.signal_credibility import SignalCredibilityAtom
        return SignalCredibilityAtom(blackboard=MagicMock(), bridge=MagicMock())

    def test_warranty_signal_yields_separating_credibility(self):
        """Brand with warranty → high-credibility-validated signal."""
        atom = self._make_atom()
        per_signal = atom._compute_per_signal_credibility(
            brand_signals={"warranty": 0.80}, user_sensitivity=0.6
        )
        warranty_data = per_signal["warranty"]
        assert warranty_data["separates"] == 1.0  # boolean cast
        assert warranty_data["credibility"] > 0.0
        assert warranty_data["handicap_validated"] == 1.0

    def test_cheap_talk_signal_pools(self):
        """Brand with only cheap talk → no credibility."""
        atom = self._make_atom()
        per_signal = atom._compute_per_signal_credibility(
            brand_signals={"cheap_talk": 0.80}, user_sensitivity=0.7
        )
        cheap_data = per_signal["cheap_talk"]
        # Either separates is 0 OR credibility is near-zero (likely both)
        assert cheap_data["credibility"] < 0.05

    def test_high_sensitivity_user_with_cheap_talk_penalizes_authority(self):
        """High-PK user + cheap-talk-only brand → authority/commitment
        get negative adjustments per Spence pooling logic."""
        atom = self._make_atom()
        per_signal = atom._compute_per_signal_credibility(
            brand_signals={"cheap_talk": 0.80}, user_sensitivity=0.75
        )
        adj = atom._compute_mechanism_adjustments(per_signal, user_sensitivity=0.75)
        assert adj.get("authority", 0.0) < 0
        assert adj.get("commitment", 0.0) < 0

    def test_warranty_brand_boosts_authority_and_commitment(self):
        """Brand with warranty → authority/commitment/social_proof get boosted
        per Kirmani & Rao 2000 mapping."""
        atom = self._make_atom()
        per_signal = atom._compute_per_signal_credibility(
            brand_signals={"warranty": 0.80}, user_sensitivity=0.6
        )
        adj = atom._compute_mechanism_adjustments(per_signal, user_sensitivity=0.6)
        # Warranty maps to commitment, authority, social_proof per
        # SIGNAL_COST_PARAMETERS["warranty"]["mechanisms"]
        assert adj.get("commitment", 0.0) > 0
        assert adj.get("authority", 0.0) > 0
