# =============================================================================
# ADAM Temporal Self — Canonical Regression Tests
# Location: tests/unit/test_temporal_self_canonical.py
# =============================================================================

"""
CANONICAL REGRESSION TESTS — temporal_self (B3-LUXY Phase 1 atom 5)

Pins the published anchors of Parfit 1984 personal identity, Hershfield
2011 future self-continuity, and Laibson 1997 hyperbolic discounting
to the atom's implementation.

Anchors pinned:
- Parfit 1984 §3: continuity is gradient; regime classification is
  discrete around critical thresholds.
- Hershfield 2011 (FSCS): high temporal_horizon → high continuity.
- Hershfield et al. 2011: bridging interventions when category future-
  relevance is high but user continuity is low.
- Laibson 1997 §2: hyperbolic discount rate inversely related to
  continuity (k = 1 − continuity).
- Bartels & Urminsky 2011: regime predicts mechanism-preference
  patterns.
"""

import pytest

from adam.atoms.core.temporal_self import (
    CATEGORY_TEMPORAL,
    CONTINUITY_MECHANISMS,
    _HIGH_CONTINUITY_THRESHOLD,
    _LOW_CONTINUITY_THRESHOLD,
    _classify_regime,
    _compute_continuity,
    _compute_hyperbolic_discount,
    _resolve_category_temporal,
)
from adam.atoms.models.chain_attestation import (
    CalibrationStatus,
    RelationType,
)


# =============================================================================
# HERSHFIELD 2011 — CONTINUITY DERIVATION
# =============================================================================


class TestContinuityDerivation:
    """Pin Hershfield 2011 FSCS structural properties on the
    NDF-derived continuity scalar."""

    def test_no_signal_returns_baseline(self):
        """No NDF signal + no category boost → 0.5 baseline."""
        c = _compute_continuity({}, has_signal=False, category_boost=0.0)
        assert c == pytest.approx(0.5)

    def test_high_temporal_horizon_increases_continuity(self):
        """High TH → high continuity (Hershfield 2011 primary indicator)."""
        low_th = _compute_continuity(
            {"temporal_horizon": 0.0}, has_signal=True, category_boost=0.0
        )
        high_th = _compute_continuity(
            {"temporal_horizon": 1.0}, has_signal=True, category_boost=0.0
        )
        assert high_th > low_th

    def test_high_arousal_seeking_decreases_continuity(self):
        """High AS → low continuity (thrill-seeking is present-focused)."""
        low_as = _compute_continuity(
            {"arousal_seeking": 0.0}, has_signal=True, category_boost=0.0
        )
        high_as = _compute_continuity(
            {"arousal_seeking": 1.0}, has_signal=True, category_boost=0.0
        )
        assert high_as < low_as

    def test_high_cognitive_engagement_increases_continuity(self):
        """High CE → high continuity (deliberation considers future)."""
        low_ce = _compute_continuity(
            {"cognitive_engagement": 0.0}, has_signal=True, category_boost=0.0
        )
        high_ce = _compute_continuity(
            {"cognitive_engagement": 1.0}, has_signal=True, category_boost=0.0
        )
        assert high_ce > low_ce

    def test_continuity_clamped_to_valid_range(self):
        """continuity ∈ [0.05, 0.95] for any input combination."""
        # Maximally positive inputs
        psy_max = {
            "temporal_horizon": 1.0,
            "cognitive_engagement": 1.0,
            "arousal_seeking": 0.0,
            "approach_avoidance": 0.0,
        }
        c = _compute_continuity(psy_max, has_signal=True, category_boost=0.5)
        assert 0.05 <= c <= 0.95

        # Maximally negative inputs
        psy_min = {
            "temporal_horizon": 0.0,
            "cognitive_engagement": 0.0,
            "arousal_seeking": 1.0,
            "approach_avoidance": 1.0,
        }
        c = _compute_continuity(psy_min, has_signal=True, category_boost=-0.5)
        assert 0.05 <= c <= 0.95

    def test_category_boost_applied(self):
        """Category continuity_boost shifts the scalar."""
        baseline = _compute_continuity({}, has_signal=False, category_boost=0.0)
        boosted = _compute_continuity({}, has_signal=False, category_boost=0.2)
        assert boosted > baseline


# =============================================================================
# PARFIT 1984 §3 — DISCRETE REGIME CLASSIFICATION
# =============================================================================


class TestRegimeClassification:
    """Pin Parfit 1984 §3 gradient → discrete regime structure."""

    def test_high_continuity_classifies_high_regime(self):
        assert _classify_regime(0.80) == "high_continuity"
        assert _classify_regime(_HIGH_CONTINUITY_THRESHOLD + 0.01) == "high_continuity"

    def test_low_continuity_classifies_low_regime(self):
        assert _classify_regime(0.20) == "low_continuity"
        assert _classify_regime(_LOW_CONTINUITY_THRESHOLD - 0.01) == "low_continuity"

    def test_moderate_continuity_classifies_moderate_regime(self):
        assert _classify_regime(0.50) == "moderate_continuity"

    def test_classification_at_high_threshold_is_moderate(self):
        """Boundary: continuity = high_threshold is moderate (strict > for high)."""
        assert _classify_regime(_HIGH_CONTINUITY_THRESHOLD) == "moderate_continuity"

    def test_classification_at_low_threshold_is_moderate(self):
        """Boundary: continuity = low_threshold is moderate (strict < for low)."""
        assert _classify_regime(_LOW_CONTINUITY_THRESHOLD) == "moderate_continuity"

    def test_regime_is_discrete_step_function(self):
        """Pin the regime-switch behavior: small continuity change at the
        threshold produces a regime jump."""
        below = _classify_regime(_HIGH_CONTINUITY_THRESHOLD - 0.001)
        above = _classify_regime(_HIGH_CONTINUITY_THRESHOLD + 0.001)
        assert below != above
        assert below == "moderate_continuity"
        assert above == "high_continuity"


# =============================================================================
# LAIBSON 1997 / FREDERICK 2002 — HYPERBOLIC DISCOUNT RATE
# =============================================================================


class TestHyperbolicDiscount:
    """Pin Laibson 1997 hyperbolic discount k = 1 − continuity."""

    def test_high_continuity_low_discount(self):
        """High continuity → low discount rate (patient)."""
        assert _compute_hyperbolic_discount(0.9) == pytest.approx(0.1, abs=1e-9)

    def test_low_continuity_high_discount(self):
        """Low continuity → high discount rate (impatient)."""
        assert _compute_hyperbolic_discount(0.1) == pytest.approx(0.9, abs=1e-9)

    def test_perfect_continuity_zero_discount(self):
        """continuity = 1 → discount = 0 (rational, no time preference)."""
        assert _compute_hyperbolic_discount(1.0) == pytest.approx(0.0)

    def test_zero_continuity_max_discount(self):
        """continuity = 0 → discount = 1 (maximally impatient)."""
        assert _compute_hyperbolic_discount(0.0) == pytest.approx(1.0)

    def test_discount_monotonically_decreasing_in_continuity(self):
        """Higher continuity → lower discount rate."""
        prior = float("inf")
        for c in [0.0, 0.2, 0.5, 0.8, 1.0]:
            d = _compute_hyperbolic_discount(c)
            assert d <= prior
            prior = d

    def test_discount_bounded(self):
        """Discount ∈ [0, 1] for any continuity ∈ [0, 1]."""
        for c in [0.0, 0.5, 1.0]:
            d = _compute_hyperbolic_discount(c)
            assert 0.0 <= d <= 1.0


# =============================================================================
# CATEGORY TEMPORAL PROFILES
# =============================================================================


class TestCategoryTemporal:
    """Pin per-category future_relevance and continuity_boost values."""

    def test_financial_high_future_relevance(self):
        profile = _resolve_category_temporal("Financial")
        assert profile["future_relevance"] >= 0.85

    def test_entertainment_low_future_relevance(self):
        profile = _resolve_category_temporal("Entertainment")
        assert profile["future_relevance"] <= 0.20

    def test_unknown_category_returns_neutral_profile(self):
        profile = _resolve_category_temporal("UnknownCategory")
        assert profile["future_relevance"] == pytest.approx(0.5)
        assert profile["continuity_boost"] == pytest.approx(0.0)

    def test_empty_category_returns_neutral_profile(self):
        profile = _resolve_category_temporal("")
        assert profile["future_relevance"] == pytest.approx(0.5)

    def test_case_insensitive_lookup(self):
        upper = _resolve_category_temporal("HEALTH")
        lower = _resolve_category_temporal("health")
        title = _resolve_category_temporal("Health")
        assert upper["future_relevance"] == lower["future_relevance"] == title["future_relevance"]

    def test_partial_match_lookup(self):
        """Category lookups match if the canonical key is a substring."""
        # "Personal Finance" should match "Financial"
        # (current implementation uses key.lower() in cat.lower())
        # Actually our implementation checks `cat_key.lower() in cat_lower`
        # So "Financial" key → matches when category contains "financial"
        profile = _resolve_category_temporal("Personal Financial Services")
        assert profile["future_relevance"] >= 0.85


# =============================================================================
# CHAIN ATTESTATION — STRUCTURAL & A14-FLAG INVARIANTS
# =============================================================================


class TestTemporalSelfChainAttestation:
    """Pin the regime-switch chain shape (5 links; L2 is regime classification)."""

    def _make_atom_with_state(self, continuity_target=0.8, category=""):
        from unittest.mock import MagicMock, patch
        from adam.atoms.core.temporal_self import TemporalSelfAtom

        atom = TemporalSelfAtom(blackboard=MagicMock(), bridge=MagicMock())
        atom_input = MagicMock()
        atom_input.ad_context = {"category": category}
        atom_input.request_id = "req_test"

        with patch(
            "adam.atoms.core.temporal_self.PsychologicalConstructResolver"
        ) as mock_psy_class:
            mock_psy = MagicMock()
            mock_psy.has_any = True
            # Map continuity_target back to NDF dims that produce it
            # (approximately) — easier is to just override the result
            psy_dict = {
                "temporal_horizon": continuity_target,
                "cognitive_engagement": continuity_target,
                "arousal_seeking": 1.0 - continuity_target,
                "approach_avoidance": 1.0 - continuity_target,
            }
            mock_psy.as_full_construct_dict = MagicMock(return_value=psy_dict)
            mock_psy_class.return_value = mock_psy
            temporal_state = atom._compute_temporal_state(atom_input)

        adjustments = atom._compute_mechanism_adjustments(temporal_state)
        return atom, atom_input, temporal_state, adjustments

    def test_chain_has_five_links(self):
        atom, atom_input, state, adj = self._make_atom_with_state()
        attestation = atom._build_chain_attestation(atom_input, state, adj)
        assert len(attestation.chain) == 5

    def test_chain_relation_type_sequence(self):
        """Pin the regime-switch chain shape:
        MODULATED_BY, PRODUCES (regime), PRODUCES (discount), MODULATED_BY, PRODUCES."""
        atom, atom_input, state, adj = self._make_atom_with_state()
        attestation = atom._build_chain_attestation(atom_input, state, adj)

        expected = [
            RelationType.MODULATED_BY,  # L1: dispositional × category → continuity
            RelationType.PRODUCES,       # L2: continuity → regime (REGIME SWITCH)
            RelationType.PRODUCES,       # L3: continuity → discount_rate
            RelationType.MODULATED_BY,  # L4: regime × discount → preferences
            RelationType.PRODUCES,       # L5: regime × category → adjustments
        ]
        actual = [link.relation_type for link in attestation.chain]
        assert actual == expected

    def test_l2_target_construct_encodes_regime(self):
        """L2 target_construct names the regime ('regime_high_continuity', etc.)
        — the regime-switch is observable in the chain output."""
        atom_high, _, state_high, adj_high = self._make_atom_with_state(continuity_target=0.95)
        atom_low, _, state_low, adj_low = self._make_atom_with_state(continuity_target=0.05)

        from unittest.mock import MagicMock
        atom_input = MagicMock()
        atom_input.request_id = "req_test"

        attestation_high = atom_high._build_chain_attestation(atom_input, state_high, adj_high)
        attestation_low = atom_low._build_chain_attestation(atom_input, state_low, adj_low)

        l2_high = attestation_high.chain[1]
        l2_low = attestation_low.chain[1]

        assert "high_continuity" in l2_high.target_construct
        assert "low_continuity" in l2_low.target_construct
        # The two chains route to different downstream regimes — observable
        # as different target_construct names in L2.
        assert l2_high.target_construct != l2_low.target_construct

    def test_chain_provenance_lists_all_a14_flags(self):
        atom, atom_input, state, adj = self._make_atom_with_state()
        attestation = atom._build_chain_attestation(atom_input, state, adj)
        flags = set(attestation.provenance.a14_flags_active)
        assert "TEMPORAL_SELF_NDF_COEFFICIENTS_PILOT_PENDING" in flags
        assert "CATEGORY_TEMPORAL_PROFILES_PILOT_PENDING" in flags
        assert "CONTINUITY_REGIME_THRESHOLDS_PILOT_PENDING" in flags
        assert "HYPERBOLIC_DISCOUNT_FORM_PILOT_PENDING" in flags
        assert "CONTINUITY_MECHANISM_ADJUSTMENT_MAGNITUDES_PILOT_PENDING" in flags

    def test_chain_links_have_canonical_citations(self):
        atom, atom_input, state, adj = self._make_atom_with_state()
        attestation = atom._build_chain_attestation(atom_input, state, adj)
        canonical_authors = {
            "Parfit", "Hershfield", "Frederick", "Laibson", "Bartels", "Mazur"
        }
        for link in attestation.chain:
            assert link.citation
            assert any(a in link.citation for a in canonical_authors), \
                f"Link missing canonical citation: {link.citation}"

    def test_pinned_links_at_canonical_steps(self):
        """L2 (Parfit regime classification) and L3 (Laibson hyperbolic
        discount) are PINNED. L1, L4, L5 are PILOT_PENDING."""
        atom, atom_input, state, adj = self._make_atom_with_state()
        attestation = atom._build_chain_attestation(atom_input, state, adj)
        statuses = [link.calibration_status for link in attestation.chain]
        assert statuses[0] == CalibrationStatus.PILOT_PENDING  # L1
        assert statuses[1] == CalibrationStatus.PINNED          # L2 Parfit
        assert statuses[2] == CalibrationStatus.PINNED          # L3 Laibson
        assert statuses[3] == CalibrationStatus.PILOT_PENDING  # L4
        assert statuses[4] == CalibrationStatus.PILOT_PENDING  # L5

    def test_l5_target_construct_signals_bridging(self):
        """L5 target_construct names 'bridging_mechanism_adjustments' when
        Hershfield bridging fires (low continuity + high future relevance);
        otherwise 'mechanism_adjustments'."""
        # Low continuity + Financial (future_relevance 0.95) → bridging
        from unittest.mock import MagicMock
        atom, _, state_bridging, adj_bridging = self._make_atom_with_state(
            continuity_target=0.10, category="Financial"
        )
        atom_input = MagicMock()
        atom_input.request_id = "req_test"
        attestation_bridging = atom._build_chain_attestation(
            atom_input, state_bridging, adj_bridging
        )
        l5_bridging = attestation_bridging.chain[4]
        assert "bridging" in l5_bridging.target_construct

        # High continuity (no bridging needed) → standard target
        atom2, _, state_standard, adj_standard = self._make_atom_with_state(
            continuity_target=0.85, category="Financial"
        )
        attestation_standard = atom2._build_chain_attestation(
            atom_input, state_standard, adj_standard
        )
        l5_standard = attestation_standard.chain[4]
        assert "bridging" not in l5_standard.target_construct


# =============================================================================
# REGIME-KEYED MECHANISM ADJUSTMENTS
# =============================================================================


class TestRegimeKeyedAdjustments:
    """Pin Bartels & Urminsky 2011: regime predicts mechanism preferences."""

    def _make_atom(self):
        from unittest.mock import MagicMock
        from adam.atoms.core.temporal_self import TemporalSelfAtom
        return TemporalSelfAtom(blackboard=MagicMock(), bridge=MagicMock())

    def _build_state(self, continuity, category=""):
        cat_profile = _resolve_category_temporal(category)
        return {
            "continuity": continuity,
            "regime": _classify_regime(continuity),
            "discount_rate": _compute_hyperbolic_discount(continuity),
            "category_future_relevance": cat_profile["future_relevance"],
            "category_continuity_boost": cat_profile["continuity_boost"],
            "signal_quality": 1.0,
        }

    def test_high_continuity_boosts_identity_construction(self):
        """High continuity → identity_construction boosted (invest in future-self)."""
        atom = self._make_atom()
        state = self._build_state(continuity=0.85)
        adj = atom._compute_mechanism_adjustments(state)
        assert adj.get("identity_construction", 0.0) > 0
        assert adj.get("commitment", 0.0) > 0

    def test_low_continuity_boosts_present_focused_mechanisms(self):
        """Low continuity → scarcity/attention/embodied boosted (present-focused)."""
        atom = self._make_atom()
        state = self._build_state(continuity=0.15)
        adj = atom._compute_mechanism_adjustments(state)
        assert adj.get("scarcity", 0.0) > 0
        assert adj.get("attention_dynamics", 0.0) > 0
        assert adj.get("embodied_cognition", 0.0) > 0

    def test_low_continuity_suppresses_temporal_construal(self):
        """Low continuity → temporal_construal suppressed
        (future framing won't work)."""
        atom = self._make_atom()
        state = self._build_state(continuity=0.15)
        adj = atom._compute_mechanism_adjustments(state)
        assert adj.get("temporal_construal", 0.0) < 0
        assert adj.get("commitment", 0.0) < 0

    def test_high_continuity_suppresses_scarcity(self):
        """High continuity → scarcity suppressed (urgency unnecessary)."""
        atom = self._make_atom()
        state = self._build_state(continuity=0.85)
        adj = atom._compute_mechanism_adjustments(state)
        assert adj.get("scarcity", 0.0) < 0


# =============================================================================
# HERSHFIELD 2011 — BRIDGING INTERVENTION
# =============================================================================


class TestHershfieldBridging:
    """Pin Hershfield et al. 2011 bridging-intervention behavior:
    low-continuity user in high-future-relevance category gets a boost
    to mechanisms that bridge the present-future gap."""

    def _make_atom(self):
        from unittest.mock import MagicMock
        from adam.atoms.core.temporal_self import TemporalSelfAtom
        return TemporalSelfAtom(blackboard=MagicMock(), bridge=MagicMock())

    def test_bridging_active_for_low_continuity_in_high_future_category(self):
        """Low continuity + Financial → embodied_cognition + identity_construction
        + social_proof get the Hershfield bridging boost."""
        atom = self._make_atom()
        # Low continuity in high-future-relevance category (financial, 0.95)
        state = {
            "continuity": 0.30,
            "regime": "low_continuity",
            "discount_rate": 0.70,
            "category_future_relevance": 0.95,
            "category_continuity_boost": 0.15,
            "signal_quality": 1.0,
        }
        adj = atom._compute_mechanism_adjustments(state)
        # Without bridging, embodied_cognition starts at 0.15 * intensity ≈ 0.18
        # With bridging, it gets +0.15 ON TOP → ≈ 0.33
        # We test that it's substantially elevated above the baseline regime adjustment
        assert adj.get("embodied_cognition", 0.0) > 0.20
        assert adj.get("identity_construction", 0.0) > 0.05

    def test_bridging_inactive_when_continuity_high(self):
        """High continuity in high-future category → no bridging needed
        (already future-oriented)."""
        atom = self._make_atom()
        state = {
            "continuity": 0.85,
            "regime": "high_continuity",
            "discount_rate": 0.15,
            "category_future_relevance": 0.95,
            "category_continuity_boost": 0.15,
            "signal_quality": 1.0,
        }
        adj = atom._compute_mechanism_adjustments(state)
        # high_continuity regime base for embodied_cognition is not specified;
        # without bridging, it stays at 0.0 (not in the high_continuity dict)
        # OR very low — definitely below the bridging-active threshold of 0.20
        assert adj.get("embodied_cognition", 0.0) < 0.10

    def test_bridging_inactive_for_low_future_relevance_category(self):
        """Low continuity but Entertainment (future_relevance 0.15) → no bridging."""
        atom = self._make_atom()
        state = {
            "continuity": 0.30,
            "regime": "low_continuity",
            "discount_rate": 0.70,
            "category_future_relevance": 0.15,
            "category_continuity_boost": -0.15,
            "signal_quality": 1.0,
        }
        adj = atom._compute_mechanism_adjustments(state)
        # embodied_cognition base for low_continuity is 0.15 * intensity ≈ 0.18
        # Without the +0.15 bridging boost, it stays around there
        # We test that it's NOT elevated to the bridging-active threshold
        assert adj.get("embodied_cognition", 0.0) < 0.25
