# =============================================================================
# ADAM Regulatory Focus — Canonical Regression Tests
# Location: tests/unit/test_regulatory_focus_canonical.py
# =============================================================================

"""
CANONICAL REGRESSION TESTS — regulatory_focus (B3-LUXY Phase 2 atom 9)

Pins Higgins 1997 §4 ORTHOGONALITY of promotion and prevention dimensions,
Higgins et al. 2001 RFQ proxy structure, and Higgins 2000 regulatory fit
amplification.

Anchors pinned:
- Higgins 1997 §4: promotion and prevention orthogonal (high-on-both
  possible)
- Higgins et al. 2001 §3-§4: RFQ scales correlate weakly (between-
  scale independence)
- Higgins 2000: matched framing → amplifier > 1; mismatched → < 1
- Yerkes-Dodson: high arousal shifts toward prevention
"""

import pytest

from adam.atoms.core.regulatory_focus import (
    BIG_FIVE_TO_PREVENTION,
    BIG_FIVE_TO_PROMOTION,
    RFQ_MECHANISM_MAP,
    _DOMINANCE_THRESHOLD,
    _FIT_MATCH_AMPLIFIER,
    _FIT_MISMATCH_AMPLIFIER,
    _FIT_NEUTRAL_AMPLIFIER,
    _apply_arousal_shift,
    _classify_dominant_focus,
    _compute_regulatory_fit,
    _compute_rfq_scores_orthogonal,
)
from adam.atoms.models.chain_attestation import (
    CalibrationStatus,
    RelationType,
)


# =============================================================================
# HIGGINS 1997 §4 — ORTHOGONALITY
# =============================================================================


class TestRFQOrthogonality:
    """Pin Higgins 1997 §4 + Higgins et al. 2001 RFQ orthogonal structure."""

    def test_no_signal_returns_neutral_baseline(self):
        promo, prev = _compute_rfq_scores_orthogonal({}, has_signal=False)
        assert promo == pytest.approx(0.5)
        assert prev == pytest.approx(0.5)

    def test_high_extraversion_increases_promotion(self):
        """High extraversion → high promotion (Higgins et al. 2001 §3)."""
        low = _compute_rfq_scores_orthogonal(
            {"extraversion": 0.0, "openness": 0.5, "conscientiousness": 0.5,
             "agreeableness": 0.5, "neuroticism": 0.5},
            has_signal=True,
        )[0]
        high = _compute_rfq_scores_orthogonal(
            {"extraversion": 1.0, "openness": 0.5, "conscientiousness": 0.5,
             "agreeableness": 0.5, "neuroticism": 0.5},
            has_signal=True,
        )[0]
        assert high > low

    def test_high_neuroticism_increases_prevention(self):
        """High neuroticism → high prevention (Higgins et al. 2001 §4)."""
        low = _compute_rfq_scores_orthogonal(
            {"extraversion": 0.5, "openness": 0.5, "conscientiousness": 0.5,
             "agreeableness": 0.5, "neuroticism": 0.0},
            has_signal=True,
        )[1]
        high = _compute_rfq_scores_orthogonal(
            {"extraversion": 0.5, "openness": 0.5, "conscientiousness": 0.5,
             "agreeableness": 0.5, "neuroticism": 1.0},
            has_signal=True,
        )[1]
        assert high > low

    def test_orthogonality_high_on_both_possible(self):
        """KEY Higgins 1997 §4 pin: a user can be HIGH ON BOTH
        promotion AND prevention (chronic dual-focus). The two
        dimensions are NOT mutually exclusive."""
        # High extraversion (→ promotion) + high conscientiousness (→ prevention)
        big_five = {
            "extraversion": 0.95,
            "openness": 0.85,
            "conscientiousness": 0.95,
            "agreeableness": 0.5,
            "neuroticism": 0.85,
        }
        promo, prev = _compute_rfq_scores_orthogonal(big_five, has_signal=True)
        # Both should be elevated above baseline (canonical orthogonality)
        assert promo > 0.6
        assert prev > 0.6

    def test_orthogonality_low_on_both_possible(self):
        """Conversely: a user can be LOW on both (chronic dis-engagement)."""
        big_five = {
            "extraversion": 0.05,
            "openness": 0.10,
            "conscientiousness": 0.10,
            "agreeableness": 0.5,
            "neuroticism": 0.05,
        }
        promo, prev = _compute_rfq_scores_orthogonal(big_five, has_signal=True)
        assert promo < 0.4
        assert prev < 0.4

    def test_scores_clamped(self):
        """Promotion and prevention scores ∈ [0.05, 0.95]."""
        big_five_max = {
            "extraversion": 1.0, "openness": 1.0, "conscientiousness": 1.0,
            "agreeableness": 1.0, "neuroticism": 1.0,
        }
        promo, prev = _compute_rfq_scores_orthogonal(big_five_max, has_signal=True)
        assert 0.05 <= promo <= 0.95
        assert 0.05 <= prev <= 0.95

    def test_promotion_coefficient_signs_canonical(self):
        """Direction-of-effect pin (Higgins et al. 2001 §3):
        extraversion + openness positive, neuroticism negative."""
        assert BIG_FIVE_TO_PROMOTION["extraversion"] > 0
        assert BIG_FIVE_TO_PROMOTION["openness"] > 0
        assert BIG_FIVE_TO_PROMOTION["neuroticism"] < 0

    def test_prevention_coefficient_signs_canonical(self):
        """Direction-of-effect pin (Higgins et al. 2001 §4):
        conscientiousness + neuroticism positive, openness/extraversion negative or low."""
        assert BIG_FIVE_TO_PREVENTION["conscientiousness"] > 0
        assert BIG_FIVE_TO_PREVENTION["neuroticism"] > 0
        assert BIG_FIVE_TO_PREVENTION["openness"] < 0


# =============================================================================
# HIGGINS 1997 §4 — DOMINANCE CLASSIFICATION
# =============================================================================


class TestDominanceClassification:
    def test_promotion_dominant_when_promotion_higher(self):
        assert _classify_dominant_focus(promotion=0.8, prevention=0.3) == "promotion"

    def test_prevention_dominant_when_prevention_higher(self):
        assert _classify_dominant_focus(promotion=0.3, prevention=0.8) == "prevention"

    def test_balanced_when_close(self):
        """Below threshold (0.15) → balanced."""
        assert _classify_dominant_focus(promotion=0.6, prevention=0.5) == "balanced"
        assert _classify_dominant_focus(promotion=0.5, prevention=0.5) == "balanced"

    def test_balanced_when_high_on_both(self):
        """High-on-both → balanced (chronic dual-focus, no clear dominance)."""
        assert _classify_dominant_focus(promotion=0.85, prevention=0.85) == "balanced"

    def test_balanced_when_low_on_both(self):
        """Low-on-both → balanced (chronic dis-engagement)."""
        assert _classify_dominant_focus(promotion=0.20, prevention=0.20) == "balanced"


# =============================================================================
# HIGGINS 2000 — REGULATORY FIT
# =============================================================================


class TestRegulatoryFit:
    """Pin Higgins 2000 framing-focus matching."""

    def test_promotion_gain_match(self):
        status, amp = _compute_regulatory_fit("promotion", "gain")
        assert status == "matched"
        assert amp == _FIT_MATCH_AMPLIFIER

    def test_prevention_loss_match(self):
        status, amp = _compute_regulatory_fit("prevention", "loss")
        assert status == "matched"
        assert amp == _FIT_MATCH_AMPLIFIER

    def test_promotion_loss_mismatch(self):
        status, amp = _compute_regulatory_fit("promotion", "loss")
        assert status == "mismatched"
        assert amp == _FIT_MISMATCH_AMPLIFIER
        assert amp < 1.0

    def test_prevention_gain_mismatch(self):
        status, amp = _compute_regulatory_fit("prevention", "gain")
        assert status == "mismatched"
        assert amp == _FIT_MISMATCH_AMPLIFIER

    def test_no_framing_returns_neutral(self):
        status, amp = _compute_regulatory_fit("promotion", None)
        assert status == "neutral"
        assert amp == _FIT_NEUTRAL_AMPLIFIER

    def test_balanced_focus_returns_neutral(self):
        status, amp = _compute_regulatory_fit("balanced", "gain")
        assert status == "neutral"
        assert amp == _FIT_NEUTRAL_AMPLIFIER

    def test_unknown_framing_returns_neutral(self):
        status, amp = _compute_regulatory_fit("promotion", "neither")
        assert status == "neutral"

    def test_amplifier_constants_canonical(self):
        """Higgins 2000 pins: matched > 1; mismatched < 1; neutral = 1."""
        assert _FIT_MATCH_AMPLIFIER > 1.0
        assert _FIT_MISMATCH_AMPLIFIER < 1.0
        assert _FIT_NEUTRAL_AMPLIFIER == pytest.approx(1.0)


# =============================================================================
# YERKES-DODSON — AROUSAL SHIFT
# =============================================================================


class TestArousalShift:
    def test_no_arousal_no_shift(self):
        promo, prev = _apply_arousal_shift(0.6, 0.4, arousal=None)
        assert promo == 0.6
        assert prev == 0.4

    def test_low_arousal_no_shift(self):
        """Below 0.7 threshold → no shift."""
        promo, prev = _apply_arousal_shift(0.6, 0.4, arousal=0.5)
        assert promo == 0.6
        assert prev == 0.4

    def test_high_arousal_shifts_toward_prevention(self):
        """Above 0.7 → promotion ↓, prevention ↑."""
        promo_orig, prev_orig = 0.6, 0.4
        promo, prev = _apply_arousal_shift(promo_orig, prev_orig, arousal=0.9)
        assert promo < promo_orig
        assert prev > prev_orig

    def test_extreme_arousal_clamped(self):
        """Even extreme arousal can't push scores out of [0.05, 0.95]."""
        promo, prev = _apply_arousal_shift(0.6, 0.9, arousal=1.0)
        assert prev <= 0.95


# =============================================================================
# CHAIN ATTESTATION — STRUCTURAL & A14-FLAG INVARIANTS
# =============================================================================


class TestRegulatoryFocusChainAttestation:
    """Pin the orthogonal-parallel chain shape (5 links; L1+L2 PARALLEL,
    L3+L4 PINNED)."""

    def _make_atom_with_state(self, ad_framing=None, arousal=None, big_five=None):
        from unittest.mock import MagicMock
        from adam.atoms.core.regulatory_focus import RegulatoryFocusAtom

        atom = RegulatoryFocusAtom(blackboard=MagicMock(), bridge=MagicMock())

        atom_input = MagicMock()
        # Mock the request_context.user_intelligence chain
        user_intel = MagicMock()
        user_intel.current_arousal = arousal
        if big_five:
            profile = MagicMock()
            bf = MagicMock()
            bf.extraversion = big_five.get("extraversion", 0.5)
            bf.openness = big_five.get("openness", 0.5)
            bf.conscientiousness = big_five.get("conscientiousness", 0.5)
            bf.agreeableness = big_five.get("agreeableness", 0.5)
            bf.neuroticism = big_five.get("neuroticism", 0.5)
            profile.big_five = bf
            user_intel.profile = profile
        else:
            user_intel.profile = None
        atom_input.request_context.user_intelligence = user_intel
        atom_input.ad_context = {"ad_framing": ad_framing}
        atom_input.request_id = "req_test"

        rfq_state = atom._compute_rfq_state(atom_input)
        adjustments = atom._compute_mechanism_adjustments(rfq_state)
        return atom, atom_input, rfq_state, adjustments

    def test_chain_has_five_links(self):
        atom, atom_input, state, adj = self._make_atom_with_state()
        attestation = atom._build_chain_attestation(atom_input, state, adj)
        assert len(attestation.chain) == 5

    def test_chain_relation_type_sequence(self):
        atom, atom_input, state, adj = self._make_atom_with_state()
        attestation = atom._build_chain_attestation(atom_input, state, adj)
        expected = [
            RelationType.MODULATED_BY,  # L1: Big Five → RFQ promo (PARALLEL)
            RelationType.MODULATED_BY,  # L2: Big Five → RFQ prev (PARALLEL)
            RelationType.PRODUCES,       # L3: RFQ → dominant_focus (PINNED orthogonal)
            RelationType.PRODUCES,       # L4: focus × framing → fit (PINNED Higgins 2000)
            RelationType.PRODUCES,       # L5: fit × focus → adjustments
        ]
        actual = [link.relation_type for link in attestation.chain]
        assert actual == expected

    def test_l1_targets_promotion_l2_targets_prevention(self):
        """Pin the parallel orthogonal structure: L1 → promotion, L2 → prevention.
        These are PARALLEL inputs to L3 (not sequential)."""
        atom, atom_input, state, adj = self._make_atom_with_state()
        attestation = atom._build_chain_attestation(atom_input, state, adj)
        assert "promotion" in attestation.chain[0].target_construct
        assert "prevention" in attestation.chain[1].target_construct

    def test_chain_pinned_at_canonical_steps(self):
        """L3 (Higgins 1997 §4 orthogonal classification) and L4
        (Higgins 2000 regulatory fit) are PINNED."""
        atom, atom_input, state, adj = self._make_atom_with_state(
            big_five={"extraversion": 0.8, "openness": 0.8,
                      "conscientiousness": 0.3, "agreeableness": 0.5, "neuroticism": 0.3}
        )
        attestation = atom._build_chain_attestation(atom_input, state, adj)
        statuses = [link.calibration_status for link in attestation.chain]
        assert statuses[2] == CalibrationStatus.PINNED  # L3
        assert statuses[3] == CalibrationStatus.PINNED  # L4
        assert statuses[0] == CalibrationStatus.PILOT_PENDING
        assert statuses[1] == CalibrationStatus.PILOT_PENDING
        assert statuses[4] == CalibrationStatus.PILOT_PENDING

    def test_chain_provenance_lists_a14_flags(self):
        atom, atom_input, state, adj = self._make_atom_with_state()
        attestation = atom._build_chain_attestation(atom_input, state, adj)
        flags = set(attestation.provenance.a14_flags_active)
        assert "HIGGINS_RFQ_PILOT_PENDING" in flags
        assert "AROUSAL_RFQ_SHIFT_PILOT_PENDING" in flags
        assert "HIGGINS_DOMINANCE_THRESHOLD_PILOT_PENDING" in flags
        assert "REGULATORY_FIT_AMPLIFIER_PILOT_PENDING" in flags
        assert "RFQ_MECHANISM_MAPPINGS_PILOT_PENDING" in flags

    def test_chain_links_have_canonical_citations(self):
        atom, atom_input, state, adj = self._make_atom_with_state()
        attestation = atom._build_chain_attestation(atom_input, state, adj)
        for link in attestation.chain:
            assert link.citation
            assert "Higgins" in link.citation or "Avnet" in link.citation \
                or "Crowe" in link.citation, \
                f"Link missing canonical citation: {link.citation}"


# =============================================================================
# END-TO-END
# =============================================================================


class TestRegulatoryFocusIntegration:
    def _make_atom(self):
        from unittest.mock import MagicMock
        from adam.atoms.core.regulatory_focus import RegulatoryFocusAtom
        return RegulatoryFocusAtom(blackboard=MagicMock(), bridge=MagicMock())

    def test_promotion_focus_with_gain_framing_amplified(self):
        """Promotion-dominant + gain framing → amplifier > 1 → larger
        magnitude adjustments."""
        atom = self._make_atom()
        rfq_state = {
            "promotion": 0.85, "prevention": 0.30,
            "promotion_effective": 0.85, "prevention_effective": 0.30,
            "arousal": None,
            "dominant_focus": "promotion",
            "ad_framing": "gain",
            "fit_status": "matched",
            "fit_amplifier": _FIT_MATCH_AMPLIFIER,
            "has_big_five": True,
        }
        adj = atom._compute_mechanism_adjustments(rfq_state)
        # Identity construction (promotion mech) should be elevated by amplifier
        assert adj.get("identity_construction", 0.0) > 0.20

    def test_prevention_focus_with_loss_framing_amplified(self):
        atom = self._make_atom()
        rfq_state = {
            "promotion": 0.30, "prevention": 0.85,
            "promotion_effective": 0.30, "prevention_effective": 0.85,
            "arousal": None,
            "dominant_focus": "prevention",
            "ad_framing": "loss",
            "fit_status": "matched",
            "fit_amplifier": _FIT_MATCH_AMPLIFIER,
            "has_big_five": True,
        }
        adj = atom._compute_mechanism_adjustments(rfq_state)
        assert adj.get("commitment", 0.0) > 0.20

    def test_mismatch_attenuates_adjustments(self):
        atom = self._make_atom()
        match_state = {
            "promotion": 0.85, "prevention": 0.30,
            "promotion_effective": 0.85, "prevention_effective": 0.30,
            "arousal": None, "dominant_focus": "promotion",
            "ad_framing": "gain", "fit_status": "matched",
            "fit_amplifier": _FIT_MATCH_AMPLIFIER, "has_big_five": True,
        }
        mismatch_state = dict(match_state)
        mismatch_state["ad_framing"] = "loss"
        mismatch_state["fit_status"] = "mismatched"
        mismatch_state["fit_amplifier"] = _FIT_MISMATCH_AMPLIFIER

        match_adj = atom._compute_mechanism_adjustments(match_state)
        mismatch_adj = atom._compute_mechanism_adjustments(mismatch_state)
        # Mismatched amplifier (<1) reduces magnitude
        assert match_adj["identity_construction"] > mismatch_adj["identity_construction"]
