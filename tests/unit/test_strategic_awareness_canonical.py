# =============================================================================
# ADAM Strategic Awareness — Canonical Regression Tests
# Location: tests/unit/test_strategic_awareness_canonical.py
# =============================================================================

"""
CANONICAL REGRESSION TESTS — strategic_awareness (B3-LUXY Phase 1 atom 4)

Pins the published anchors of Friestad & Wright 1994 PKM + Wegener et
al. 2004 Flexible Correction Model to the atom's implementation.

Anchors pinned:
- Friestad & Wright 1994 §2: PK as knowledge structure with dispositional
  baseline.
- Friestad & Wright 1994 §3: PK is experience-learned (FEEDBACK LOOP).
- Friestad & Wright 1994 §4: detection is mechanism-selective.
- Wegener et al. 2004 §2: detection produces correction (not reversal);
  effectiveness multiplier ∈ (0, 1].
- High-PK overcorrection penalty (Wegener) for very-high-PK users.
"""

import math

import pytest

from adam.atoms.core.strategic_awareness import (
    MECHANISM_DETECTABILITY,
    NDF_TO_PKM,
    _PKM_EXPOSURE_RATE,
    _PKM_MAX_AMPLIFIER,
    _WEGENER_HIGH_PK_THRESHOLD,
    _WEGENER_OVERCORRECTION_PENALTY,
    _apply_exposure_feedback,
    _compute_baseline_pk,
    _compute_correction_effect,
    _compute_detection_probability,
)
from adam.atoms.models.chain_attestation import (
    CalibrationStatus,
    RelationType,
)


# =============================================================================
# FRIESTAD & WRIGHT 1994 §2 — DISPOSITIONAL BASELINE
# =============================================================================


class TestBaselinePK:
    """Pin §2 dispositional-baseline structure."""

    def test_no_signal_returns_default_baseline(self):
        """No NDF signal → 0.5 baseline PK."""
        assert _compute_baseline_pk({}, has_signal=False) == pytest.approx(0.5)

    def test_high_cognitive_engagement_increases_pk(self):
        """High CE → higher PK (critical thinkers detect more)."""
        low_ce = _compute_baseline_pk({"cognitive_engagement": 0.0}, has_signal=True)
        high_ce = _compute_baseline_pk({"cognitive_engagement": 1.0}, has_signal=True)
        assert high_ce > low_ce

    def test_high_uncertainty_tolerance_decreases_pk(self):
        """High UT → lower PK (tolerance of uncertainty → less scrutiny)."""
        low_ut = _compute_baseline_pk({"uncertainty_tolerance": 0.0}, has_signal=True)
        high_ut = _compute_baseline_pk({"uncertainty_tolerance": 1.0}, has_signal=True)
        assert high_ut < low_ut

    def test_baseline_pk_clamped_to_valid_range(self):
        """PK ∈ [0.10, 0.95] for any input combination."""
        # Maximally amplifying inputs
        psy = {
            "cognitive_engagement": 1.0,
            "social_calibration": 1.0,
            "uncertainty_tolerance": 0.0,
            "approach_avoidance": 0.0,
            "status_sensitivity": 1.0,
        }
        pk = _compute_baseline_pk(psy, has_signal=True)
        assert 0.10 <= pk <= 0.95


# =============================================================================
# FRIESTAD & WRIGHT 1994 §3 — EXPERIENCE-LEARNED FEEDBACK LOOP
# =============================================================================


class TestExposureFeedback:
    """Pin §3 feedback-loop: PK amplifies with exposure count."""

    def test_first_exposure_no_amplification(self):
        """exposure_count = 1 → effective_pk = baseline_pk."""
        assert _apply_exposure_feedback(0.5, 1) == pytest.approx(0.5)

    def test_zero_or_negative_exposure_no_amplification(self):
        """Defensive: 0 or negative → baseline returned."""
        assert _apply_exposure_feedback(0.5, 0) == pytest.approx(0.5)
        assert _apply_exposure_feedback(0.5, -3) == pytest.approx(0.5)

    def test_repeat_exposure_amplifies_pk(self):
        """exposure_count > 1 → effective_pk > baseline_pk."""
        baseline = 0.5
        for n in [2, 5, 10, 20]:
            effective = _apply_exposure_feedback(baseline, n)
            assert effective > baseline

    def test_pk_amplification_monotonic(self):
        """PK amplification non-decreasing in exposure_count."""
        baseline = 0.5
        prior = -1.0
        for n in [1, 2, 3, 5, 10, 50, 200]:
            effective = _apply_exposure_feedback(baseline, n)
            assert effective >= prior
            prior = effective

    def test_pk_amplification_bounded_above(self):
        """PK amplification cannot exceed 0.95 ceiling
        nor _PKM_MAX_AMPLIFIER multiplier of baseline."""
        baseline = 0.5
        effective = _apply_exposure_feedback(baseline, 100000)
        assert effective <= 0.95
        # Multiplier cap: 1.5x baseline = 0.75, but 0.95 ceiling kicks in
        # for sufficiently high baselines. For 0.5 baseline, 1.5x = 0.75 < 0.95.
        assert effective <= baseline * _PKM_MAX_AMPLIFIER + 1e-6


# =============================================================================
# FRIESTAD & WRIGHT 1994 §4 — MECHANISM-SELECTIVE DETECTION
# =============================================================================


class TestDetectionProbability:
    """Pin §4 mechanism-selective detection structure."""

    def test_low_detectability_low_detection(self):
        """Low-detectability mechanism (storytelling 0.20) → low detection
        even at moderate PK."""
        # storytelling detectability = 0.20
        det = _compute_detection_probability(pk_level=0.5, mechanism_detectability=0.20)
        # 0.20 * (0.3 + 0.5*0.7) = 0.20 * 0.65 = 0.13
        assert det == pytest.approx(0.13, abs=1e-6)

    def test_high_detectability_high_detection(self):
        """High-detectability mechanism (urgency 0.90) → high detection."""
        det = _compute_detection_probability(pk_level=0.7, mechanism_detectability=0.90)
        # 0.90 * (0.3 + 0.7*0.7) = 0.90 * 0.79 = 0.711
        assert det == pytest.approx(0.711, abs=1e-3)

    def test_detection_monotonic_in_pk_for_fixed_mechanism(self):
        """For fixed mechanism, detection rises with PK."""
        prior = -1.0
        for pk in [0.1, 0.3, 0.5, 0.7, 0.9]:
            det = _compute_detection_probability(pk, mechanism_detectability=0.5)
            assert det >= prior
            prior = det

    def test_detection_monotonic_in_detectability_for_fixed_pk(self):
        """For fixed PK, detection rises with mechanism detectability."""
        prior = -1.0
        for det_level in [0.1, 0.3, 0.5, 0.7, 0.9]:
            det = _compute_detection_probability(pk_level=0.5, mechanism_detectability=det_level)
            assert det >= prior
            prior = det

    def test_detection_bounded(self):
        """P(detect) ∈ [0.05, 0.95]."""
        for pk in [0.0, 0.1, 0.5, 0.9, 1.0]:
            for d in [0.0, 0.1, 0.5, 0.9, 1.0]:
                det = _compute_detection_probability(pk, d)
                assert 0.05 <= det <= 0.95

    def test_low_pk_still_detects_overt_mechanisms(self):
        """Low-PK users still detect very overt mechanisms (urgency 0.90)
        — Friestad & Wright 1994 §4: salience of cue affects detection
        independent of PK."""
        det = _compute_detection_probability(pk_level=0.1, mechanism_detectability=0.90)
        # 0.90 * (0.3 + 0.1*0.7) = 0.90 * 0.37 = 0.333
        assert det > 0.30


# =============================================================================
# WEGENER 2004 — FLEXIBLE CORRECTION MODEL
# =============================================================================


class TestWegenerFlexibleCorrection:
    """Pin Wegener et al. 2004 §2 flexible correction structure."""

    def test_zero_detection_no_correction(self):
        """detection_probability = 0 → effectiveness_multiplier = 1.0."""
        eff = _compute_correction_effect(detection_prob=0.0, pk_level=0.5)
        assert eff == pytest.approx(1.0)

    def test_correction_monotonic_in_detection(self):
        """For fixed PK, correction effect grows with detection_probability
        → effectiveness_multiplier decreases."""
        prior = float("inf")
        for det in [0.0, 0.2, 0.5, 0.8, 1.0]:
            eff = _compute_correction_effect(det, pk_level=0.7)
            assert eff <= prior
            prior = eff

    def test_correction_monotonic_in_pk(self):
        """For fixed detection, higher PK → stronger correction
        (overcorrection per Wegener). effectiveness_multiplier decreases."""
        prior = float("inf")
        for pk in [0.0, 0.3, 0.5, 0.7, 1.0]:
            eff = _compute_correction_effect(detection_prob=0.6, pk_level=pk)
            assert eff <= prior
            prior = eff

    def test_max_detection_max_pk_strong_correction(self):
        """Detection = 1, PK = 1 → strong correction (Wegener overcorrection)."""
        eff = _compute_correction_effect(detection_prob=1.0, pk_level=1.0)
        # 1.0 - 1.0 * (0.3 + 1.0*0.4) = 1.0 - 0.7 = 0.3
        assert eff == pytest.approx(0.3, abs=1e-6)

    def test_effectiveness_bounded(self):
        """Effectiveness multiplier ∈ (0, 1] — never reverses, only corrects."""
        for det in [0.0, 0.5, 1.0]:
            for pk in [0.0, 0.5, 1.0]:
                eff = _compute_correction_effect(det, pk)
                assert 0.05 <= eff <= 1.0


# =============================================================================
# CHAIN ATTESTATION — STRUCTURAL & A14-FLAG INVARIANTS
# =============================================================================


class TestStrategicAwarenessChainAttestation:
    """Pin the atom's chain-attestation emission shape (5 links with
    feedback loop at L2)."""

    def _make_atom_with_state(self, exposure_count=1):
        from unittest.mock import MagicMock, patch
        from adam.atoms.core.strategic_awareness import StrategicAwarenessAtom

        atom = StrategicAwarenessAtom(blackboard=MagicMock(), bridge=MagicMock())

        atom_input = MagicMock()
        atom_input.ad_context = {"exposure_count": exposure_count}
        atom_input.request_id = "req_test"

        with patch(
            "adam.atoms.core.strategic_awareness.PsychologicalConstructResolver"
        ) as mock_psy_class:
            mock_psy = MagicMock()
            mock_psy.has_any = True
            mock_psy.as_full_construct_dict = MagicMock(return_value={
                "cognitive_engagement": 0.7,
                "social_calibration": 0.5,
                "uncertainty_tolerance": 0.4,
                "approach_avoidance": 0.5,
                "status_sensitivity": 0.5,
            })
            mock_psy_class.return_value = mock_psy
            pk_state = atom._compute_pk_state(atom_input)

        adjustments = atom._compute_mechanism_adjustments(pk_state)
        return atom, atom_input, pk_state, adjustments

    def test_chain_has_five_links(self):
        atom, atom_input, pk_state, adj = self._make_atom_with_state()
        attestation = atom._build_chain_attestation(atom_input, pk_state, adj)
        assert len(attestation.chain) == 5

    def test_chain_relation_type_sequence(self):
        """Pin the feedback-loop chain shape:
        MODULATED_BY, AMPLIFIES (feedback), PRODUCES, THREATENS, MODULATED_BY."""
        atom, atom_input, pk_state, adj = self._make_atom_with_state()
        attestation = atom._build_chain_attestation(atom_input, pk_state, adj)

        expected = [
            RelationType.MODULATED_BY,  # L1: dispositional → baseline_pk
            RelationType.AMPLIFIES,      # L2: prior_exposure → effective_pk (FEEDBACK)
            RelationType.PRODUCES,       # L3: PK × detectability → detection_prob
            RelationType.THREATENS,      # L4: detection → effectiveness (Wegener)
            RelationType.MODULATED_BY,  # L5: effectiveness → adjustments
        ]
        actual = [link.relation_type for link in attestation.chain]
        assert actual == expected

    def test_chain_feedback_loop_link_marks_prior_only_when_no_repeat_exposure(self):
        """First-exposure case: L2's feedback link is from_prior_only=True
        (no actual prior exposure data to feed back from)."""
        atom, atom_input, pk_state, adj = self._make_atom_with_state(exposure_count=1)
        attestation = atom._build_chain_attestation(atom_input, pk_state, adj)
        l2 = attestation.chain[1]  # L2 is the feedback-loop link
        assert l2.from_prior_only is True

    def test_chain_feedback_loop_link_not_prior_only_with_repeat_exposure(self):
        """Multi-exposure case: L2 has actual data."""
        atom, atom_input, pk_state, adj = self._make_atom_with_state(exposure_count=5)
        attestation = atom._build_chain_attestation(atom_input, pk_state, adj)
        l2 = attestation.chain[1]
        assert l2.from_prior_only is False

    def test_chain_provenance_lists_all_a14_flags(self):
        atom, atom_input, pk_state, adj = self._make_atom_with_state()
        attestation = atom._build_chain_attestation(atom_input, pk_state, adj)
        flags = set(attestation.provenance.a14_flags_active)
        assert "NDF_TO_PKM_COEFFICIENTS_PILOT_PENDING" in flags
        assert "PKM_DETECTABILITY_LITERATURE_MIDPOINTS_PILOT_PENDING" in flags
        assert "PKM_EXPOSURE_FEEDBACK_RATE_PILOT_PENDING" in flags
        assert "WEGENER_OVERCORRECTION_PENALTY_PILOT_PENDING" in flags

    def test_chain_links_have_pk_citations(self):
        """Discipline rule (a) — every link cites Friestad & Wright or Wegener."""
        atom, atom_input, pk_state, adj = self._make_atom_with_state()
        attestation = atom._build_chain_attestation(atom_input, pk_state, adj)
        for link in attestation.chain:
            assert link.citation
            cite = link.citation
            assert any(
                marker in cite
                for marker in ["Friestad", "Wegener", "Campbell", "Stewart"]
            ), f"Link missing canonical citation: {cite}"

    def test_chain_pinned_at_wegener_link(self):
        """L4 (Wegener flexible correction) is PINNED. Other links
        PILOT_PENDING (their magnitudes are placeholders)."""
        atom, atom_input, pk_state, adj = self._make_atom_with_state()
        attestation = atom._build_chain_attestation(atom_input, pk_state, adj)
        statuses = [link.calibration_status for link in attestation.chain]
        assert statuses[3] == CalibrationStatus.PINNED  # L4 Wegener structure
        # Others are PILOT_PENDING placeholders
        assert statuses[0] == CalibrationStatus.PILOT_PENDING
        assert statuses[1] == CalibrationStatus.PILOT_PENDING
        assert statuses[2] == CalibrationStatus.PILOT_PENDING
        assert statuses[4] == CalibrationStatus.PILOT_PENDING


# =============================================================================
# STEALTH-AWARE MECHANISM ADJUSTMENTS
# =============================================================================


class TestStealthAwareAdjustments:
    """Pin the high-PK → stealth-vs-detected mechanism adjustment behavior."""

    def _make_atom(self):
        from unittest.mock import MagicMock
        from adam.atoms.core.strategic_awareness import StrategicAwarenessAtom
        return StrategicAwarenessAtom(blackboard=MagicMock(), bridge=MagicMock())

    def _build_pk_state(self, effective_pk):
        atom = self._make_atom()
        per_mechanism = {}
        for mech, det in MECHANISM_DETECTABILITY.items():
            det_prob = _compute_detection_probability(effective_pk, det)
            eff = _compute_correction_effect(det_prob, effective_pk)
            stealth = 1.0 - det_prob
            if effective_pk > _WEGENER_HIGH_PK_THRESHOLD:
                eff *= _WEGENER_OVERCORRECTION_PENALTY
                stealth *= _WEGENER_OVERCORRECTION_PENALTY
            per_mechanism[mech] = {
                "detectability": det,
                "detection_probability": det_prob,
                "effectiveness_multiplier": eff,
                "stealth_score": max(0.05, stealth),
            }
        return {
            "baseline_pk": effective_pk,
            "effective_pk": effective_pk,
            "exposure_count": 1,
            "per_mechanism": per_mechanism,
            "signal_quality": 1.0,
        }

    def test_high_pk_user_overt_mechanisms_penalized(self):
        """High-PK user → urgency / scarcity get negative adjustments."""
        atom = self._make_atom()
        pk_state = self._build_pk_state(effective_pk=0.85)
        adj = atom._compute_mechanism_adjustments(pk_state)
        assert adj["urgency"] < 0
        assert adj["scarcity"] < 0

    def test_high_pk_user_stealthy_mechanisms_boosted(self):
        """High-PK user → storytelling / embodied_cognition get positive
        adjustments (stealth alternatives)."""
        atom = self._make_atom()
        pk_state = self._build_pk_state(effective_pk=0.85)
        adj = atom._compute_mechanism_adjustments(pk_state)
        assert adj["storytelling"] > 0
        assert adj["embodied_cognition"] > 0

    def test_low_pk_user_minimal_adjustments(self):
        """Low-PK user → magnitude near zero (PK below 0.4 threshold)."""
        atom = self._make_atom()
        pk_state = self._build_pk_state(effective_pk=0.30)
        adj = atom._compute_mechanism_adjustments(pk_state)
        # All adjustments should be near zero
        for mech, value in adj.items():
            assert abs(value) < 0.05, \
                f"{mech}: low-PK should have minimal adjustment, got {value}"

    def test_adjustments_bounded(self):
        """All adjustments ∈ [-0.25, 0.25]."""
        atom = self._make_atom()
        for pk in [0.1, 0.5, 0.9]:
            pk_state = self._build_pk_state(effective_pk=pk)
            adj = atom._compute_mechanism_adjustments(pk_state)
            for mech, value in adj.items():
                assert -0.25 <= value <= 0.25
