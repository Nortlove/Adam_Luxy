# =============================================================================
# ADAM Persuasion Pharmacology — Canonical Regression Tests
# Location: tests/unit/test_persuasion_pharmacology_canonical.py
# =============================================================================

"""
CANONICAL REGRESSION TESTS — persuasion_pharmacology (B3-LUXY Phase 1 atom 2)

Pins the published anchors of the pharmacological canon to the atom's
implementation. Discipline-rule (b) artifact for the redo.

Anchors pinned:
- Hill 1910: E(0)=0, E(EC50)=E_max/2, E(∞)→E_max, monotonic in dose,
  Hill coefficient steepness.
- Solomon & Corbit 1974 / Stewart & Badiani 1993: tol(1)=1, tol(n>1)<1,
  monotonic decrease, floor at TOLERANCE_FLOOR.
- Shen 2007 §1: below threshold no penalty; above threshold linear penalty;
  adjusted_effect ≥ -0.3 floor.
- Bliss 1939: E_combined(0,b)=b; E_combined(a,0)=a; E_combined(1,1)=1;
  commutative; synergy > baseline; antagonism < baseline.
"""

import math

import pytest

from adam.atoms.core.persuasion_pharmacology import (
    MECHANISM_INTERACTIONS,
    MECHANISM_PHARMACOLOGY,
    _TOLERANCE_FLOOR,
    _TOXICITY_PENALTY_SLOPE,
    _apply_bliss_interaction,
    _bliss_independence_baseline,
    _hill_equation,
    _tolerance_factor,
    _toxicity_penalty,
)
from adam.atoms.models.chain_attestation import (
    CalibrationStatus,
    RelationType,
)


# =============================================================================
# HILL 1910 — DOSE-RESPONSE FORMULA
# =============================================================================


class TestHillEquation:
    """Pin Hill 1910 canonical sigmoidal dose-response."""

    def test_hill_zero_dose_zero_effect(self):
        """E(C=0) = 0 for any (EC_50, n, E_max)."""
        for ec50 in [0.1, 0.3, 0.5, 0.7]:
            for n in [1.0, 1.5, 2.5]:
                for emax in [0.5, 0.75, 1.0]:
                    assert _hill_equation(0.0, ec50, n, emax) == 0.0

    def test_hill_at_ec50_half_maximal_effect(self):
        """E(C = EC_50) = E_max / 2 — the canonical Hill pin."""
        for ec50 in [0.1, 0.3, 0.5, 0.7]:
            for n in [1.0, 1.5, 2.5]:
                for emax in [0.5, 0.75, 1.0]:
                    e = _hill_equation(ec50, ec50, n, emax)
                    assert e == pytest.approx(emax / 2.0, abs=1e-9)

    def test_hill_saturates_to_max_effect(self):
        """E(C → ∞) → E_max."""
        e = _hill_equation(100.0, 0.5, 2.0, 0.85)
        assert e == pytest.approx(0.85, abs=0.01)

    def test_hill_monotonic_in_dose(self):
        """Hill function is monotonically non-decreasing in dose."""
        prior = -1.0
        for dose in [0.0, 0.1, 0.2, 0.3, 0.5, 0.7, 1.0, 2.0]:
            e = _hill_equation(dose, 0.4, 2.0, 0.85)
            assert e >= prior
            prior = e

    def test_hill_higher_coefficient_steeper(self):
        """Larger n → steeper transition around EC_50.

        At C = 0.5 × EC_50, higher n produces LOWER effect (further
        below E_max/2). At C = 2 × EC_50, higher n produces HIGHER
        effect (closer to E_max).
        """
        ec50, emax = 0.4, 1.0
        # Below EC50
        e_low_n = _hill_equation(0.5 * ec50, ec50, 1.0, emax)
        e_high_n = _hill_equation(0.5 * ec50, ec50, 3.0, emax)
        assert e_high_n < e_low_n
        # Above EC50
        e_low_n = _hill_equation(2.0 * ec50, ec50, 1.0, emax)
        e_high_n = _hill_equation(2.0 * ec50, ec50, 3.0, emax)
        assert e_high_n > e_low_n


# =============================================================================
# SOLOMON & CORBIT 1974 — TOLERANCE EXPONENTIAL DECAY
# =============================================================================


class TestToleranceFactor:
    """Pin Solomon & Corbit 1974 / Stewart & Badiani 1993 tolerance decay."""

    def test_tolerance_first_exposure_is_one(self):
        """tol(1) = 1.0 — no tolerance on first exposure."""
        for rate in [0.05, 0.15, 0.3, 0.5]:
            assert _tolerance_factor(1, rate) == pytest.approx(1.0)

    def test_tolerance_zero_or_negative_is_one(self):
        """tol(n ≤ 0) = 1.0 — defensive guard for unusable counts."""
        assert _tolerance_factor(0, 0.3) == pytest.approx(1.0)
        assert _tolerance_factor(-5, 0.3) == pytest.approx(1.0)

    def test_tolerance_decreases_with_repeat_exposure(self):
        """tol(n > 1) < 1.0 — opponent process kicks in."""
        for rate in [0.05, 0.15, 0.3]:
            assert _tolerance_factor(2, rate) < 1.0

    def test_tolerance_monotonically_decreasing(self):
        """tol is monotonically non-increasing in exposure_count."""
        prior = float("inf")
        for n in [1, 2, 3, 5, 10, 20, 50]:
            t = _tolerance_factor(n, 0.2)
            assert t <= prior
            prior = t

    def test_tolerance_floor_pin(self):
        """At very high exposure_count, tol → TOLERANCE_FLOOR (not zero)."""
        t = _tolerance_factor(1000, 0.5)
        assert t == pytest.approx(_TOLERANCE_FLOOR)
        # Floor invariant: never drops below
        assert t >= _TOLERANCE_FLOOR

    def test_tolerance_higher_rate_faster_decay(self):
        """Larger tolerance_rate → faster decay of effective dose."""
        n = 5
        t_low_rate = _tolerance_factor(n, 0.05)
        t_high_rate = _tolerance_factor(n, 0.5)
        assert t_high_rate < t_low_rate


# =============================================================================
# SHEN 2007 — THERAPEUTIC INDEX / TOXICITY PENALTY
# =============================================================================


class TestToxicityPenalty:
    """Pin Shen 2007 §1 therapeutic-index penalty structure."""

    def test_toxicity_below_threshold_no_penalty(self):
        """effective_dose ≤ threshold → no penalty, is_toxic=False."""
        adjusted, is_toxic = _toxicity_penalty(0.5, 0.7, 0.6)
        assert adjusted == pytest.approx(0.6)
        assert is_toxic is False

    def test_toxicity_at_threshold_no_penalty(self):
        """effective_dose = threshold → no penalty, is_toxic=False (boundary)."""
        adjusted, is_toxic = _toxicity_penalty(0.7, 0.7, 0.6)
        assert adjusted == pytest.approx(0.6)
        assert is_toxic is False

    def test_toxicity_above_threshold_linear_penalty(self):
        """penalty = (excess) × _TOXICITY_PENALTY_SLOPE."""
        # excess = 0.1, slope = 2.0 → penalty = 0.2
        adjusted, is_toxic = _toxicity_penalty(0.8, 0.7, 0.6)
        assert is_toxic is True
        assert adjusted == pytest.approx(0.6 - 0.1 * _TOXICITY_PENALTY_SLOPE, abs=1e-6)

    def test_toxicity_floor_at_negative_three_tenths(self):
        """adjusted_effect floor at -0.3 (backfire ceiling)."""
        # extreme excess → penalty huge → would push below floor
        adjusted, is_toxic = _toxicity_penalty(2.0, 0.5, 0.5)
        assert is_toxic is True
        assert adjusted >= -0.3
        assert adjusted == pytest.approx(-0.3)


# =============================================================================
# BLISS 1939 — INDEPENDENCE BASELINE FOR COMBINED EFFECTS
# =============================================================================


class TestBlissIndependence:
    """Pin Bliss 1939 independence baseline + interaction modifier."""

    def test_bliss_baseline_zero_a_returns_b(self):
        """E_combined(0, b) = b."""
        for b in [0.0, 0.3, 0.7, 1.0]:
            assert _bliss_independence_baseline(0.0, b) == pytest.approx(b)

    def test_bliss_baseline_zero_b_returns_a(self):
        """E_combined(a, 0) = a."""
        for a in [0.0, 0.3, 0.7, 1.0]:
            assert _bliss_independence_baseline(a, 0.0) == pytest.approx(a)

    def test_bliss_baseline_max_max_is_one(self):
        """E_combined(1, 1) = 1 (saturation)."""
        assert _bliss_independence_baseline(1.0, 1.0) == pytest.approx(1.0)

    def test_bliss_baseline_commutative(self):
        """f(a, b) = f(b, a) — Bliss is symmetric."""
        for a, b in [(0.3, 0.7), (0.5, 0.2), (0.9, 0.1), (0.4, 0.4)]:
            assert _bliss_independence_baseline(a, b) == pytest.approx(
                _bliss_independence_baseline(b, a)
            )

    def test_bliss_independence_calculation(self):
        """E_combined(0.3, 0.4) = 0.3 + 0.4 - 0.12 = 0.58."""
        result = _bliss_independence_baseline(0.3, 0.4)
        assert result == pytest.approx(0.58, abs=1e-6)

    def test_bliss_synergy_above_baseline(self):
        """Positive interaction magnitude → result > baseline."""
        baseline = _bliss_independence_baseline(0.3, 0.4)
        synergistic = _apply_bliss_interaction(0.3, 0.4, 0.2)
        assert synergistic > baseline

    def test_bliss_antagonism_below_baseline(self):
        """Negative interaction magnitude → result < baseline."""
        baseline = _bliss_independence_baseline(0.5, 0.4)
        antagonistic = _apply_bliss_interaction(0.5, 0.4, -0.2)
        assert antagonistic < baseline

    def test_bliss_zero_interaction_equals_baseline(self):
        """Zero interaction magnitude → result = baseline."""
        baseline = _bliss_independence_baseline(0.3, 0.6)
        result = _apply_bliss_interaction(0.3, 0.6, 0.0)
        assert result == pytest.approx(baseline)

    def test_bliss_interaction_clamped_above_at_one(self):
        """Combined effect cannot exceed 1.0."""
        result = _apply_bliss_interaction(0.9, 0.9, 0.5)
        assert result <= 1.0


# =============================================================================
# DOSE-RESPONSE INTEGRATION
# =============================================================================


class TestDoseResponseIntegration:
    """Pin the integrated dose-response computation (Hill + tolerance + toxicity)."""

    def _make_atom(self):
        from unittest.mock import MagicMock
        from adam.atoms.core.persuasion_pharmacology import PersuasionPharmacologyAtom
        return PersuasionPharmacologyAtom(
            blackboard=MagicMock(),
            bridge=MagicMock(),
        )

    def test_known_mechanism_returns_full_dose_response(self):
        atom = self._make_atom()
        dr = atom._compute_dose_response("scarcity", dose=0.5, exposure_count=1)
        assert "effect" in dr
        assert "effective_dose" in dr
        assert "tolerance_factor" in dr
        assert "in_therapeutic_window" in dr
        assert "toxic" in dr

    def test_unknown_mechanism_returns_default(self):
        atom = self._make_atom()
        dr = atom._compute_dose_response("nonexistent_mechanism", dose=0.5)
        # Returns a defensive default
        assert dr["effect"] == pytest.approx(0.25)
        assert dr["toxic"] is False

    def test_first_exposure_no_tolerance(self):
        atom = self._make_atom()
        dr = atom._compute_dose_response("scarcity", dose=0.5, exposure_count=1)
        assert dr["tolerance_factor"] == pytest.approx(1.0)
        assert dr["effective_dose"] == pytest.approx(0.5)

    def test_repeated_exposure_reduces_effective_dose(self):
        atom = self._make_atom()
        dr_1 = atom._compute_dose_response("attention_dynamics", dose=0.5, exposure_count=1)
        dr_10 = atom._compute_dose_response("attention_dynamics", dose=0.5, exposure_count=10)
        assert dr_10["effective_dose"] < dr_1["effective_dose"]
        assert dr_10["tolerance_factor"] < dr_1["tolerance_factor"]

    def test_low_tolerance_mechanism_resists_decay(self):
        atom = self._make_atom()
        # identity_construction has tolerance_rate=0.05 (very low)
        # attention_dynamics has tolerance_rate=0.35 (very high)
        dr_id = atom._compute_dose_response("identity_construction", dose=0.5, exposure_count=10)
        dr_att = atom._compute_dose_response("attention_dynamics", dose=0.5, exposure_count=10)
        assert dr_id["tolerance_factor"] > dr_att["tolerance_factor"]


# =============================================================================
# CHAIN ATTESTATION — STRUCTURAL & A14-FLAG INVARIANTS
# =============================================================================


class TestPharmacologyChainAttestation:
    """Pin the atom's chain-attestation emission shape."""

    def _make_atom_with_state(self, exposure_count=1):
        from unittest.mock import MagicMock
        from adam.atoms.core.persuasion_pharmacology import PersuasionPharmacologyAtom
        atom = PersuasionPharmacologyAtom(
            blackboard=MagicMock(),
            bridge=MagicMock(),
        )
        per_mechanism, interactions, _ = self._compute_synthetic_prescription(
            atom, exposure_count
        )
        return atom, per_mechanism, interactions, exposure_count

    @staticmethod
    def _compute_synthetic_prescription(atom, exposure_count):
        per_mechanism = {}
        for mech in ["scarcity", "social_proof", "authority"]:
            per_mechanism[mech] = atom._compute_dose_response(
                mech, dose=0.5, exposure_count=exposure_count
            )
        # Synergy pair: scarcity + social_proof
        interactions = atom._compute_interaction_effects(
            ["scarcity", "social_proof", "authority"], per_mechanism
        )
        return per_mechanism, interactions, exposure_count

    def test_chain_has_five_links(self):
        from unittest.mock import MagicMock
        atom, per_m, interactions, exp_count = self._make_atom_with_state()
        atom_input = MagicMock()
        atom_input.request_id = "req_test"
        attestation = atom._build_chain_attestation(
            atom_input, per_m, interactions, exp_count
        )
        assert len(attestation.chain) == 5

    def test_chain_relation_type_sequence(self):
        """Pin the relation-type sequence: MODULATED_BY, PRODUCES, THREATENS,
        AMPLIFIES, PRODUCES."""
        from unittest.mock import MagicMock
        atom, per_m, interactions, exp_count = self._make_atom_with_state()
        atom_input = MagicMock()
        atom_input.request_id = "req_test"
        attestation = atom._build_chain_attestation(
            atom_input, per_m, interactions, exp_count
        )

        expected = [
            RelationType.MODULATED_BY,  # L1: tolerance modulates dose
            RelationType.PRODUCES,       # L2: dose produces effect (Hill)
            RelationType.THREATENS,      # L3: dose-vs-threshold threatens
            RelationType.AMPLIFIES,      # L4: pair co-activation amplifies
            RelationType.PRODUCES,       # L5: composite produces recommendation
        ]
        actual = [link.relation_type for link in attestation.chain]
        assert actual == expected

    def test_chain_provenance_lists_all_a14_flags(self):
        from unittest.mock import MagicMock
        atom, per_m, interactions, exp_count = self._make_atom_with_state()
        atom_input = MagicMock()
        atom_input.request_id = "req_test"
        attestation = atom._build_chain_attestation(
            atom_input, per_m, interactions, exp_count
        )

        flags = set(attestation.provenance.a14_flags_active)
        assert "MECHANISM_PHARMACOLOGY_LITERATURE_MIDPOINTS_PILOT_PENDING" in flags
        assert "TOLERANCE_RATE_EXPONENTIAL_PILOT_PENDING" in flags
        assert "TOXICITY_PENALTY_SLOPE_PILOT_PENDING" in flags
        assert "BLISS_INTERACTION_MAGNITUDES_PILOT_PENDING" in flags
        assert "TOLERANCE_FLOOR_PILOT_PENDING" in flags

    def test_chain_links_have_citations(self):
        """Every link must have a non-empty citation (discipline rule a)."""
        from unittest.mock import MagicMock
        atom, per_m, interactions, exp_count = self._make_atom_with_state()
        atom_input = MagicMock()
        atom_input.request_id = "req_test"
        attestation = atom._build_chain_attestation(
            atom_input, per_m, interactions, exp_count
        )
        for link in attestation.chain:
            assert link.citation
            assert len(link.citation) > 5

    def test_chain_pinned_links_at_canonical_steps(self):
        """L2 (Hill equation) and L5 (composite recommendation) are PINNED;
        the rest are PILOT_PENDING (placeholder magnitudes)."""
        from unittest.mock import MagicMock
        atom, per_m, interactions, exp_count = self._make_atom_with_state()
        atom_input = MagicMock()
        atom_input.request_id = "req_test"
        attestation = atom._build_chain_attestation(
            atom_input, per_m, interactions, exp_count
        )
        statuses = [link.calibration_status for link in attestation.chain]
        assert statuses[0] == CalibrationStatus.PILOT_PENDING  # L1 tolerance
        assert statuses[1] == CalibrationStatus.PINNED          # L2 Hill
        assert statuses[2] == CalibrationStatus.PILOT_PENDING  # L3 toxicity
        assert statuses[3] == CalibrationStatus.PILOT_PENDING  # L4 Bliss
        assert statuses[4] == CalibrationStatus.PINNED          # L5 composite

    def test_chain_link_keys_match_theory_learner_format(self):
        from unittest.mock import MagicMock
        atom, per_m, interactions, exp_count = self._make_atom_with_state()
        atom_input = MagicMock()
        atom_input.request_id = "req_test"
        attestation = atom._build_chain_attestation(
            atom_input, per_m, interactions, exp_count
        )
        for link in attestation.chain:
            # Format: {relation}:{source}:{target}
            parts = link.link_key.split(":")
            assert len(parts) == 3
            assert parts[0] == link.relation_type.value
            assert parts[1] == link.source_construct
            assert parts[2] == link.target_construct


# =============================================================================
# INTERACTION ADJUSTMENTS — END-TO-END
# =============================================================================


class TestInteractionEffects:
    """Pin pairwise interaction adjustments via Bliss."""

    def _make_atom(self):
        from unittest.mock import MagicMock
        from adam.atoms.core.persuasion_pharmacology import PersuasionPharmacologyAtom
        return PersuasionPharmacologyAtom(
            blackboard=MagicMock(),
            bridge=MagicMock(),
        )

    def test_synergy_pair_produces_positive_adjustment(self):
        """scarcity + social_proof has +0.20 magnitude → positive adjustment."""
        atom = self._make_atom()
        per_m = {
            "scarcity": atom._compute_dose_response("scarcity", 0.5),
            "social_proof": atom._compute_dose_response("social_proof", 0.5),
        }
        adj = atom._compute_interaction_effects(["scarcity", "social_proof"], per_m)
        # Both should be boosted
        assert adj["scarcity"] > 0
        assert adj["social_proof"] > 0

    def test_antagonism_pair_produces_negative_adjustment(self):
        """scarcity + authority has -0.15 magnitude → negative adjustment."""
        atom = self._make_atom()
        per_m = {
            "scarcity": atom._compute_dose_response("scarcity", 0.5),
            "authority": atom._compute_dose_response("authority", 0.5),
        }
        adj = atom._compute_interaction_effects(["scarcity", "authority"], per_m)
        assert adj["scarcity"] < 0
        assert adj["authority"] < 0

    def test_inactive_mechanism_no_adjustment(self):
        """Mechanisms not in active list get no interaction adjustment."""
        atom = self._make_atom()
        per_m = {
            "scarcity": atom._compute_dose_response("scarcity", 0.5),
            "social_proof": atom._compute_dose_response("social_proof", 0.5),
            "embodied_cognition": atom._compute_dose_response("embodied_cognition", 0.5),
        }
        # Only scarcity + social_proof active
        adj = atom._compute_interaction_effects(["scarcity", "social_proof"], per_m)
        assert "embodied_cognition" not in adj
