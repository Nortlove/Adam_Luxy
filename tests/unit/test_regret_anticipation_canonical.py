# =============================================================================
# ADAM Regret Anticipation — Canonical Regression Tests
# Location: tests/unit/test_regret_anticipation_canonical.py
# =============================================================================

"""
CANONICAL REGRESSION TESTS — regret_anticipation (B3-LUXY Phase 2 atom 7)

Pins Loomes & Sugden 1982 eq. 4 R-function and Bell 1982 §3
reversibility moderation to the atom's implementation.

Anchors pinned:
- Loomes & Sugden 1982 eq. 4: R(0)=0, R(-z)=-R(z), R monotone increasing,
  |R(z)| > z for z > 0 with β > 1 (regret aversion).
- Bell 1982 §3: reversibility moderates action-regret only (not inaction).
- Inman & Zeelenberg 2002: dominant-type classification by balance.
- Connolly & Zeelenberg 2002: regret-mechanism mappings.
"""

import pytest

from adam.atoms.core.regret_anticipation import (
    CATEGORY_REGRET_PROFILES,
    REGRET_MECHANISM_MAP,
    _REGRET_AVERSION_BETA,
    _REVERSIBILITY_MODERATION_GAMMA,
    _apply_reversibility_moderation,
    _classify_dominant_regret_type,
    _regret_function,
    _resolve_category_regret_profile,
)
from adam.atoms.models.chain_attestation import (
    CalibrationStatus,
    RelationType,
)


# =============================================================================
# LOOMES & SUGDEN 1982 EQ. 4 — REGRET FUNCTION R(z)
# =============================================================================


class TestLoomesSugdenRFunction:
    """Pin canonical R-function structural properties."""

    def test_r_zero_outcome_zero_regret(self):
        """R(0) = 0 — Loomes & Sugden 1982 eq. 4 boundary."""
        for beta in [0.5, 1.0, 1.2, 2.0]:
            assert _regret_function(0.0, beta) == 0.0

    def test_r_antisymmetric(self):
        """R(-z) = -R(z) — antisymmetry pin."""
        for beta in [0.5, 1.0, 1.2, 2.0]:
            for z in [0.1, 0.3, 0.7, 1.0]:
                pos = _regret_function(z, beta)
                neg = _regret_function(-z, beta)
                assert neg == pytest.approx(-pos, abs=1e-9)

    def test_r_monotonic_increasing(self):
        """R'(z) > 0 — R is monotonically increasing in z."""
        for beta in [0.5, 1.0, 1.2, 2.0]:
            prior = -float("inf")
            for z in [-1.0, -0.5, -0.1, 0.0, 0.1, 0.5, 1.0]:
                r = _regret_function(z, beta)
                assert r >= prior
                prior = r

    def test_regret_aversion_when_beta_greater_than_one(self):
        """β > 1 → |R(z)| > |z| for |z| > 1; |R(z)| < |z| for |z| < 1.

        Specifically the power form sign(z)|z|^β grows faster than linear
        for |z| > 1 and slower for |z| < 1 when β > 1. The standard
        regret-aversion test uses |z| close to 1 where the curvature
        manifests as steeper-than-linear-but-bounded growth.
        """
        # For z = 1.0, R(1.0, β=1.2) = 1.0^1.2 = 1.0 — boundary case
        assert _regret_function(1.0, beta=1.2) == pytest.approx(1.0, abs=1e-9)
        # For z = 0.5, R(0.5, 1.2) = 0.5^1.2 ≈ 0.435 < 0.5 (sub-linear here)
        assert _regret_function(0.5, beta=1.2) < 0.5
        # For z = 2.0, R(2.0, 1.2) = 2.0^1.2 ≈ 2.30 > 2.0 (super-linear)
        assert _regret_function(2.0, beta=1.2) > 2.0

    def test_linear_when_beta_equals_one(self):
        """β = 1 → R(z) = z (linear baseline, no regret aversion)."""
        for z in [-0.7, -0.3, 0.0, 0.3, 0.7]:
            assert _regret_function(z, beta=1.0) == pytest.approx(z, abs=1e-9)

    def test_default_beta_pins_active(self):
        """Default β value is the literature midpoint 1.2 (regret-averse)."""
        assert _REGRET_AVERSION_BETA == pytest.approx(1.2)


# =============================================================================
# BELL 1982 §3 — REVERSIBILITY MODERATION
# =============================================================================


class TestBellReversibilityModeration:
    """Pin Bell 1982 §3 reversibility-moderates-action-regret structure."""

    def test_zero_reversibility_no_moderation(self):
        """reversibility = 0 → action_regret unchanged."""
        original = 0.7
        moderated = _apply_reversibility_moderation(original, reversibility=0.0)
        assert moderated == pytest.approx(original)

    def test_max_reversibility_full_gamma_moderation(self):
        """reversibility = 1 → action_regret reduced by γ."""
        original = 0.7
        moderated = _apply_reversibility_moderation(original, reversibility=1.0)
        # 0.7 * (1 - 0.5 * 1) = 0.7 * 0.5 = 0.35
        expected = original * (1.0 - _REVERSIBILITY_MODERATION_GAMMA)
        assert moderated == pytest.approx(expected, abs=1e-9)

    def test_moderation_monotonic_in_reversibility(self):
        """Higher reversibility → lower effective action regret."""
        original = 0.5
        prior = float("inf")
        for r in [0.0, 0.2, 0.5, 0.8, 1.0]:
            mod = _apply_reversibility_moderation(original, reversibility=r)
            assert mod <= prior
            prior = mod

    def test_moderation_clamped_at_zero(self):
        """Moderated regret never goes below zero (defensive)."""
        # Even with extreme parameters, output is bounded
        mod = _apply_reversibility_moderation(0.5, reversibility=10.0)
        assert mod >= 0.0


# =============================================================================
# INMAN & ZEELENBERG 2002 — DOMINANT-TYPE CLASSIFICATION
# =============================================================================


class TestDominantTypeClassification:
    """Pin Inman & Zeelenberg 2002 action vs inaction classification."""

    def test_inaction_dominant_when_inaction_higher(self):
        assert _classify_dominant_regret_type(
            action_regret=0.3, inaction_regret=0.7
        ) == "inaction"

    def test_action_dominant_when_action_higher(self):
        assert _classify_dominant_regret_type(
            action_regret=0.7, inaction_regret=0.3
        ) == "action"

    def test_balanced_when_close(self):
        """Within threshold (default 0.05) → balanced."""
        assert _classify_dominant_regret_type(
            action_regret=0.5, inaction_regret=0.52
        ) == "balanced"
        assert _classify_dominant_regret_type(
            action_regret=0.5, inaction_regret=0.5
        ) == "balanced"

    def test_threshold_boundary(self):
        """Difference clearly below threshold → balanced.
        Difference clearly above threshold → dominant.
        (Avoid exact-threshold values to dodge floating-point.)"""
        # Clearly below threshold (default 0.05): difference 0.04
        assert _classify_dominant_regret_type(
            action_regret=0.5, inaction_regret=0.54
        ) == "balanced"
        # Clearly above threshold: difference 0.10
        assert _classify_dominant_regret_type(
            action_regret=0.5, inaction_regret=0.60
        ) == "inaction"


# =============================================================================
# CATEGORY REGRET PROFILES
# =============================================================================


class TestCategoryRegretProfiles:
    """Pin per-category regret asymmetries from Inman & Zeelenberg 2002."""

    def test_food_inaction_dominant(self):
        """Food: action 0.20, inaction 0.80 → strongly inaction-dominant
        (you can't undo the meal you skipped)."""
        profile = _resolve_category_regret_profile("Food")
        assert profile["inaction"] > profile["action"]

    def test_automotive_action_dominant(self):
        """Automotive: action 0.80, inaction 0.20 → strongly action-dominant
        (cars are major commitments with high buyer's remorse risk)."""
        profile = _resolve_category_regret_profile("Automotive")
        assert profile["action"] > profile["inaction"]

    def test_health_high_action_low_reversibility(self):
        """Health: action 0.70, reversibility 0.20 — high action regret
        + low reversibility means action-regret stays effective even
        after Bell moderation."""
        profile = _resolve_category_regret_profile("Health")
        assert profile["action"] > 0.6
        assert profile["reversibility"] < 0.3

    def test_subscription_high_reversibility(self):
        """Subscription: reversibility 0.80 — easy to cancel reduces
        action regret substantially."""
        profile = _resolve_category_regret_profile("Subscription")
        assert profile["reversibility"] > 0.7

    def test_unknown_category_returns_none(self):
        """No-match category returns None (defensive)."""
        assert _resolve_category_regret_profile("UnknownCategory") is None
        assert _resolve_category_regret_profile("") is None

    def test_case_insensitive_match(self):
        upper = _resolve_category_regret_profile("FOOD")
        lower = _resolve_category_regret_profile("food")
        assert upper == lower

    def test_partial_match(self):
        """Substring matching: 'Premium Travel' matches 'Travel'."""
        profile = _resolve_category_regret_profile("Premium Travel Booking")
        assert profile is not None
        assert profile["inaction"] > profile["action"]  # Travel is inaction-dominant


# =============================================================================
# CHAIN ATTESTATION — STRUCTURAL & A14-FLAG INVARIANTS
# =============================================================================


class TestRegretChainAttestation:
    """Pin the Loomes-Sugden-canonical chain shape (5 links; L2+L3 PINNED)."""

    def _make_atom_with_state(self, category="Automotive"):
        from unittest.mock import MagicMock, patch
        from adam.atoms.core.regret_anticipation import RegretAnticipationAtom

        atom = RegretAnticipationAtom(blackboard=MagicMock(), bridge=MagicMock())
        atom_input = MagicMock()
        atom_input.ad_context = {"category": category}
        atom_input.request_id = "req_test"
        atom_input.get_upstream = MagicMock(return_value=None)

        with patch(
            "adam.atoms.core.regret_anticipation.PsychologicalConstructResolver"
        ) as mock_psy_class:
            mock_psy = MagicMock()
            mock_psy.has_any = True
            mock_psy.as_full_construct_dict = MagicMock(return_value={
                "approach_avoidance": 0.5,
                "uncertainty_tolerance": 0.4,
                "temporal_horizon": 0.5,
                "arousal_seeking": 0.5,
                "status_sensitivity": 0.5,
                "cognitive_engagement": 0.6,
            })
            mock_psy_class.return_value = mock_psy
            regret_state = atom._compute_regret_state(atom_input)

        adjustments = atom._compute_mechanism_adjustments(regret_state)
        return atom, atom_input, regret_state, adjustments

    def test_chain_has_five_links(self):
        atom, atom_input, state, adj = self._make_atom_with_state()
        attestation = atom._build_chain_attestation(atom_input, state, adj)
        assert len(attestation.chain) == 5

    def test_chain_relation_type_sequence(self):
        atom, atom_input, state, adj = self._make_atom_with_state()
        attestation = atom._build_chain_attestation(atom_input, state, adj)
        expected = [
            RelationType.MODULATED_BY,  # L1: dispositional × category → balance
            RelationType.PRODUCES,       # L2: balance × uncertainty → R-function (PINNED)
            RelationType.MODULATED_BY,   # L3: R × reversibility → effective (PINNED)
            RelationType.PRODUCES,       # L4: effective → dominant_type
            RelationType.PRODUCES,       # L5: dominant_type → adjustments
        ]
        actual = [link.relation_type for link in attestation.chain]
        assert actual == expected

    def test_chain_pinned_at_canonical_steps(self):
        """L2 (Loomes & Sugden R) and L3 (Bell reversibility) are PINNED."""
        atom, atom_input, state, adj = self._make_atom_with_state()
        attestation = atom._build_chain_attestation(atom_input, state, adj)
        statuses = [link.calibration_status for link in attestation.chain]
        assert statuses[1] == CalibrationStatus.PINNED  # L2 L&S
        assert statuses[2] == CalibrationStatus.PINNED  # L3 Bell
        assert statuses[0] == CalibrationStatus.PILOT_PENDING
        assert statuses[3] == CalibrationStatus.PILOT_PENDING
        assert statuses[4] == CalibrationStatus.PILOT_PENDING

    def test_chain_provenance_lists_a14_flags(self):
        atom, atom_input, state, adj = self._make_atom_with_state()
        attestation = atom._build_chain_attestation(atom_input, state, adj)
        flags = set(attestation.provenance.a14_flags_active)
        assert "REGRET_AVERSION_BETA_PILOT_PENDING" in flags
        assert "LOOMES_SUGDEN_REVERSIBILITY_WEIGHTS_PILOT_PENDING" in flags
        assert "CATEGORY_REGRET_PROFILES_PILOT_PENDING" in flags
        assert "NDF_REGRET_WEIGHTS_PILOT_PENDING" in flags
        assert "REGRET_MECHANISM_MAPPINGS_PILOT_PENDING" in flags

    def test_chain_links_have_canonical_citations(self):
        atom, atom_input, state, adj = self._make_atom_with_state()
        attestation = atom._build_chain_attestation(atom_input, state, adj)
        canonical = {"Loomes", "Sugden", "Bell", "Inman", "Zeelenberg",
                     "Gilovich", "Medvec", "Connolly"}
        for link in attestation.chain:
            assert link.citation
            assert any(c in link.citation for c in canonical), \
                f"Link missing canonical citation: {link.citation}"


# =============================================================================
# END-TO-END INTEGRATION
# =============================================================================


class TestRegretAnticipationIntegration:
    """End-to-end tests on dominant-regret outcomes."""

    def _make_atom(self):
        from unittest.mock import MagicMock
        from adam.atoms.core.regret_anticipation import RegretAnticipationAtom
        return RegretAnticipationAtom(blackboard=MagicMock(), bridge=MagicMock())

    def test_inaction_dominant_boosts_scarcity(self):
        """Inaction-dominant regret → REGRET_MECHANISM_MAP boosts scarcity."""
        atom = self._make_atom()
        regret_state = {
            "action_regret_raw": 0.20,
            "inaction_regret_raw": 0.80,
            "r_action": 0.15,
            "r_inaction": 0.78,
            "r_action_effective": 0.10,
            "r_inaction_effective": 0.78,
            "decision_reversibility": 0.4,
            "regret_intensity": 0.6,
            "regret_balance": 0.68,  # strongly inaction-dominant
            "dominant_type": "inaction",
            "signal_quality": 1.0,
        }
        adj = atom._compute_mechanism_adjustments(regret_state)
        assert adj.get("scarcity", 0.0) > 0
        assert adj.get("social_proof", 0.0) > 0

    def test_action_dominant_boosts_commitment(self):
        """Action-dominant regret → REGRET_MECHANISM_MAP boosts commitment."""
        atom = self._make_atom()
        regret_state = {
            "action_regret_raw": 0.80,
            "inaction_regret_raw": 0.20,
            "r_action": 0.78,
            "r_inaction": 0.15,
            "r_action_effective": 0.78,
            "r_inaction_effective": 0.15,
            "decision_reversibility": 0.2,
            "regret_intensity": 0.6,
            "regret_balance": -0.63,  # strongly action-dominant
            "dominant_type": "action",
            "signal_quality": 1.0,
        }
        adj = atom._compute_mechanism_adjustments(regret_state)
        assert adj.get("commitment", 0.0) > 0
        assert adj.get("authority", 0.0) > 0
        assert adj.get("scarcity", 0.0) < 0  # suppressed for action-dominant

    def test_high_reversibility_action_regret_reduces_adjustment(self):
        """High reversibility moderates action-regret-driven adjustments."""
        atom = self._make_atom()
        low_rev_state = {
            "action_regret_raw": 0.80, "inaction_regret_raw": 0.20,
            "r_action": 0.78, "r_inaction": 0.15,
            "r_action_effective": 0.78, "r_inaction_effective": 0.15,
            "decision_reversibility": 0.20,
            "regret_intensity": 0.6, "regret_balance": -0.63,
            "dominant_type": "action", "signal_quality": 1.0,
        }
        high_rev_state = dict(low_rev_state)
        high_rev_state["decision_reversibility"] = 0.85

        low_rev_adj = atom._compute_mechanism_adjustments(low_rev_state)
        high_rev_adj = atom._compute_mechanism_adjustments(high_rev_state)

        # High reversibility should reduce the absolute magnitude of the
        # action-regret-driven commitment boost
        assert abs(high_rev_adj.get("commitment", 0.0)) < abs(low_rev_adj.get("commitment", 0.0))
