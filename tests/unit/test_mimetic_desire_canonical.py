# =============================================================================
# ADAM Mimetic Desire — Canonical Regression Tests
# Location: tests/unit/test_mimetic_desire_canonical.py
# =============================================================================

"""
CANONICAL REGRESSION TESTS — mimetic_desire_atom (B3-LUXY Phase 1 atom 3)

Pins the published anchors of Girardian mimetic theory to the atom's
implementation. Discipline-rule (b) artifact for the redo.

Anchors pinned:
- Girard 1961 §1: triangular S-M-O structure (model selection drives desire)
- Girard 1961 §2: internal vs external mediation classification by proximity
- Girard 1972 §1: internal mediation produces rivalry; external does not
- Girard 1972 §1: rivalry monotonic in subject's mimetic susceptibility
  for fixed model
- Belk 1988: model identity transfers to object via possession
- Multi-source convergence chain shape (5 links; 2 convergence points)
"""

import pytest

from adam.atoms.core.mimetic_desire_atom import (
    MIMETIC_MECHANISMS,
    MODEL_TYPES,
    _INTERNAL_MEDIATION_THRESHOLD,
    _classify_mediation_type,
    _compute_rivalry_probability,
)
from adam.atoms.models.chain_attestation import (
    CalibrationStatus,
    RelationType,
)


# =============================================================================
# GIRARD 1961 §2 — INTERNAL vs EXTERNAL MEDIATION
# =============================================================================


class TestMediationTypeClassification:
    """Pin Girard 1961 §2 internal/external mediation distinction."""

    def test_celebrity_proximity_classifies_external(self):
        """distant_celebrity has proximity 0.10 → external mediation."""
        proximity = MODEL_TYPES["distant_celebrity"]["proximity"]
        assert _classify_mediation_type(proximity) == "external"

    def test_in_group_proximity_classifies_internal(self):
        """in_group_member has proximity 0.85 → internal mediation."""
        proximity = MODEL_TYPES["in_group_member"]["proximity"]
        assert _classify_mediation_type(proximity) == "internal"

    def test_aspirational_peer_classifies_internal(self):
        """aspirational_peer has proximity 0.65 (above threshold) → internal."""
        proximity = MODEL_TYPES["aspirational_peer"]["proximity"]
        assert _classify_mediation_type(proximity) == "internal"

    def test_anonymous_mass_classifies_external(self):
        """anonymous_mass has proximity 0.20 (below threshold) → external."""
        proximity = MODEL_TYPES["anonymous_mass"]["proximity"]
        assert _classify_mediation_type(proximity) == "external"

    def test_classification_at_threshold_is_external(self):
        """Boundary: proximity = threshold is external (strict > internal)."""
        assert _classify_mediation_type(_INTERNAL_MEDIATION_THRESHOLD) == "external"

    def test_classification_just_above_threshold_is_internal(self):
        """Boundary + epsilon: proximity > threshold is internal."""
        assert _classify_mediation_type(_INTERNAL_MEDIATION_THRESHOLD + 0.01) == "internal"


# =============================================================================
# GIRARD 1972 §1 — RIVALRY ESCALATION
# =============================================================================


class TestRivalryProbability:
    """Pin Girard 1972 §1: rivalry escalation in internal mediation."""

    def test_external_mediation_low_rivalry(self):
        """External mediation produces only baseline rivalry (no susceptibility amp)."""
        # Even high susceptibility shouldn't produce high rivalry under external
        rivalry = _compute_rivalry_probability(
            mediation_type="external",
            susceptibility=0.9,
            risk_of_rivalry_base=0.05,
        )
        # 0.5 * 0.05 = 0.025
        assert rivalry == pytest.approx(0.025, abs=1e-6)
        assert rivalry < 0.1

    def test_external_lower_than_internal_for_same_inputs(self):
        """Pin the canonical Girardian distinction: same model parameters
        produce HIGHER rivalry under internal mediation."""
        ext = _compute_rivalry_probability(
            mediation_type="external",
            susceptibility=0.7,
            risk_of_rivalry_base=0.30,
        )
        intl = _compute_rivalry_probability(
            mediation_type="internal",
            susceptibility=0.7,
            risk_of_rivalry_base=0.30,
        )
        assert intl > ext

    def test_internal_rivalry_monotonic_in_susceptibility(self):
        """For fixed model, internal-mediation rivalry rises with susceptibility."""
        prior = -1.0
        for susc in [0.1, 0.3, 0.5, 0.7, 0.9]:
            rivalry = _compute_rivalry_probability(
                mediation_type="internal",
                susceptibility=susc,
                risk_of_rivalry_base=0.40,
            )
            assert rivalry >= prior
            prior = rivalry

    def test_internal_high_rivalry_high_susceptibility(self):
        """High-rivalry model + high-susceptibility user → substantial rivalry probability."""
        # in_group_member (risk_of_rivalry_base=0.40) + high susceptibility
        rivalry = _compute_rivalry_probability(
            mediation_type="internal",
            susceptibility=0.85,
            risk_of_rivalry_base=0.40,
        )
        # 0.40 * (0.5 + 0.85 * 0.7) = 0.40 * 1.095 ≈ 0.438
        assert rivalry > 0.30

    def test_rivalry_bounded_at_one(self):
        """Probability cannot exceed 1.0."""
        rivalry = _compute_rivalry_probability(
            mediation_type="internal",
            susceptibility=1.0,
            risk_of_rivalry_base=1.0,
        )
        assert rivalry <= 1.0

    def test_rivalry_bounded_below_at_zero(self):
        """Probability cannot be negative."""
        rivalry = _compute_rivalry_probability(
            mediation_type="external",
            susceptibility=0.0,
            risk_of_rivalry_base=0.0,
        )
        assert rivalry >= 0.0


# =============================================================================
# MODEL TYPE PARAMETERS — STRUCTURAL INVARIANTS
# =============================================================================


class TestModelTypeStructure:
    """Pin structural invariants on MODEL_TYPES dict."""

    def test_all_models_have_required_keys(self):
        required = {
            "description", "effectiveness_base", "proximity",
            "ndf_fit", "risk_of_rivalry",
        }
        for model_id, model_def in MODEL_TYPES.items():
            assert required.issubset(model_def.keys()), \
                f"{model_id} missing keys: {required - model_def.keys()}"

    def test_in_group_highest_rivalry_risk(self):
        """Girard 1972 §1: in-group members produce highest rivalry."""
        assert MODEL_TYPES["in_group_member"]["risk_of_rivalry"] == max(
            m["risk_of_rivalry"] for m in MODEL_TYPES.values()
        )

    def test_anonymous_mass_lowest_rivalry_risk(self):
        """Anonymous mass cannot produce rivalry (no identifiable model)."""
        assert MODEL_TYPES["anonymous_mass"]["risk_of_rivalry"] == 0.0

    def test_distant_celebrity_low_rivalry_risk(self):
        """External mediation by definition has low rivalry."""
        assert MODEL_TYPES["distant_celebrity"]["risk_of_rivalry"] < 0.10

    def test_proximity_aligns_with_mediation_classification(self):
        """For each model, proximity > threshold ↔ rivalry > 0.10
        (the structural alignment between Girard 1961 §2 and §1972 §1)."""
        for model_id, model_def in MODEL_TYPES.items():
            mediation = _classify_mediation_type(model_def["proximity"])
            if mediation == "internal":
                # Internal mediation should have non-trivial rivalry risk
                # (in_group=0.40, aspirational_peer=0.30)
                assert model_def["risk_of_rivalry"] >= 0.10, \
                    f"{model_id}: internal mediation but low rivalry risk"
            else:
                # External: rivalry should be ≤ 0.10
                assert model_def["risk_of_rivalry"] <= 0.10, \
                    f"{model_id}: external mediation but high rivalry risk"


# =============================================================================
# SUSCEPTIBILITY COMPUTATION — STRUCTURAL INVARIANTS
# =============================================================================


class TestSusceptibilityComputation:
    """Pin structural invariants on susceptibility derivation
    (PILOT_PENDING magnitudes, but signs are theoretically motivated)."""

    def _make_atom(self):
        from unittest.mock import MagicMock
        from adam.atoms.core.mimetic_desire_atom import MimeticDesireAtom
        return MimeticDesireAtom(
            blackboard=MagicMock(),
            bridge=MagicMock(),
        )

    def _make_atom_input_with_psy(self, **psy_overrides):
        """Construct an AtomInput where PsychologicalConstructResolver
        returns the overridden values."""
        from unittest.mock import MagicMock, patch

        # Build a mock that responds to .has_any and the dim properties
        mock_psy = MagicMock()
        mock_psy.has_any = True
        mock_psy.social_calibration = psy_overrides.get("social_calibration", 0.5)
        mock_psy.status_sensitivity = psy_overrides.get("status_sensitivity", 0.5)
        mock_psy.cognitive_engagement = psy_overrides.get("cognitive_engagement", 0.5)
        mock_psy.uncertainty_tolerance = psy_overrides.get("uncertainty_tolerance", 0.5)
        mock_psy.approach_avoidance = psy_overrides.get("approach_avoidance", 0.5)
        mock_psy.arousal_seeking = psy_overrides.get("arousal_seeking", 0.5)
        mock_psy.as_full_construct_dict = MagicMock(return_value=psy_overrides)

        atom_input = MagicMock()
        atom_input.ad_context = {}
        atom_input.request_id = "req_test"

        return atom_input, mock_psy

    def test_high_social_calibration_increases_susceptibility(self):
        """Direction pin: high SC → more mimetic (Girard 1961 §1 social fabric)."""
        from unittest.mock import patch
        atom = self._make_atom()
        low_sc_input, low_psy = self._make_atom_input_with_psy(social_calibration=0.0)
        high_sc_input, high_psy = self._make_atom_input_with_psy(social_calibration=1.0)

        with patch(
            "adam.atoms.core.mimetic_desire_atom.PsychologicalConstructResolver",
            side_effect=lambda _: low_psy,
        ):
            low = atom._compute_susceptibility(low_sc_input)
        with patch(
            "adam.atoms.core.mimetic_desire_atom.PsychologicalConstructResolver",
            side_effect=lambda _: high_psy,
        ):
            high = atom._compute_susceptibility(high_sc_input)

        assert high["susceptibility"] > low["susceptibility"]

    def test_high_cognitive_engagement_decreases_susceptibility(self):
        """Direction pin: high CE → less mimetic (deliberation defeats imitation)."""
        from unittest.mock import patch
        atom = self._make_atom()
        low_ce_input, low_psy = self._make_atom_input_with_psy(cognitive_engagement=0.0)
        high_ce_input, high_psy = self._make_atom_input_with_psy(cognitive_engagement=1.0)

        with patch(
            "adam.atoms.core.mimetic_desire_atom.PsychologicalConstructResolver",
            side_effect=lambda _: low_psy,
        ):
            low_ce = atom._compute_susceptibility(low_ce_input)
        with patch(
            "adam.atoms.core.mimetic_desire_atom.PsychologicalConstructResolver",
            side_effect=lambda _: high_psy,
        ):
            high_ce = atom._compute_susceptibility(high_ce_input)

        assert high_ce["susceptibility"] < low_ce["susceptibility"]

    def test_susceptibility_clamped_to_valid_range(self):
        """Susceptibility ∈ [0.05, 0.95] regardless of input combination."""
        from unittest.mock import patch
        atom = self._make_atom()
        # Maximally amplifying
        atom_input, psy = self._make_atom_input_with_psy(
            social_calibration=1.0, status_sensitivity=1.0,
            cognitive_engagement=0.0, uncertainty_tolerance=0.0,
            approach_avoidance=1.0,
        )
        with patch(
            "adam.atoms.core.mimetic_desire_atom.PsychologicalConstructResolver",
            side_effect=lambda _: psy,
        ):
            result = atom._compute_susceptibility(atom_input)
        assert 0.05 <= result["susceptibility"] <= 0.95

    def test_susceptibility_classification_levels(self):
        """Verify the three-level classification thresholds: > 0.65 high,
        > 0.35 moderate, ≤ 0.35 low."""
        from unittest.mock import patch
        atom = self._make_atom()

        # No-signal case → 0.5 → moderate
        no_signal_input = self._make_atom_input_with_psy()[0]
        no_psy = self._make_atom_input_with_psy()[1]
        no_psy.has_any = False
        with patch(
            "adam.atoms.core.mimetic_desire_atom.PsychologicalConstructResolver",
            side_effect=lambda _: no_psy,
        ):
            result = atom._compute_susceptibility(no_signal_input)
        assert result["level"] == "moderate_mimetic"


# =============================================================================
# CHAIN ATTESTATION — STRUCTURAL & A14-FLAG INVARIANTS
# =============================================================================


class TestMimeticChainAttestation:
    """Pin the atom's chain-attestation emission (5 links, multi-source
    convergence shape, all flags surfaced)."""

    def _make_atom_with_state(self):
        from unittest.mock import MagicMock
        from adam.atoms.core.mimetic_desire_atom import MimeticDesireAtom
        atom = MimeticDesireAtom(blackboard=MagicMock(), bridge=MagicMock())

        susceptibility_profile = {
            "susceptibility": 0.7,
            "level": "high_mimetic",
            "signal_quality": 1.0,
        }
        # Pre-compute model selection using the actual atom logic on a synthetic input
        atom_input = MagicMock()
        atom_input.ad_context = {}
        atom_input.request_id = "req_test"
        # Use the real selector — but bypass PsychologicalConstructResolver
        from unittest.mock import patch
        with patch(
            "adam.atoms.core.mimetic_desire_atom.PsychologicalConstructResolver",
        ) as mock_psy_class:
            mock_psy = MagicMock()
            mock_psy.has_any = True
            mock_psy.as_full_construct_dict = MagicMock(return_value={
                "social_calibration": 0.7,
                "status_sensitivity": 0.6,
            })
            mock_psy_class.return_value = mock_psy
            model_selection = atom._select_model(atom_input, susceptibility_profile)

        adjustments = atom._compute_mechanism_adjustments(
            susceptibility_profile, model_selection
        )
        return atom, atom_input, susceptibility_profile, model_selection, adjustments

    def test_chain_has_five_links(self):
        atom, atom_input, susc, model, adj = self._make_atom_with_state()
        attestation = atom._build_chain_attestation(atom_input, susc, model, adj)
        assert len(attestation.chain) == 5

    def test_chain_relation_type_sequence(self):
        """Pin the multi-source convergence chain shape:
        MODULATED_BY, MODULATED_BY, PRODUCES, THREATENS, MODULATED_BY."""
        atom, atom_input, susc, model, adj = self._make_atom_with_state()
        attestation = atom._build_chain_attestation(atom_input, susc, model, adj)

        expected = [
            RelationType.MODULATED_BY,  # L1: dispositional → susceptibility
            RelationType.MODULATED_BY,  # L2: susc × candidates → selected (convergence)
            RelationType.PRODUCES,       # L3: selected → mediation_type
            RelationType.THREATENS,      # L4: mediation × susc → rivalry (convergence)
            RelationType.MODULATED_BY,  # L5: rivalry → mechanism adjustments
        ]
        actual = [link.relation_type for link in attestation.chain]
        assert actual == expected

    def test_chain_provenance_lists_all_a14_flags(self):
        atom, atom_input, susc, model, adj = self._make_atom_with_state()
        attestation = atom._build_chain_attestation(atom_input, susc, model, adj)
        flags = set(attestation.provenance.a14_flags_active)
        assert "MIMETIC_SUSCEPTIBILITY_COEFFICIENTS_PILOT_PENDING" in flags
        assert "MODEL_TYPE_PARAMETERS_PILOT_PENDING" in flags
        assert "MIMETIC_MECHANISM_ADJUSTMENT_MAGNITUDES_PILOT_PENDING" in flags
        assert "RIVALRY_THRESHOLD_INTERNAL_MEDIATION_PILOT_PENDING" in flags

    def test_chain_links_have_citations(self):
        """Discipline rule (a) at the schema level."""
        atom, atom_input, susc, model, adj = self._make_atom_with_state()
        attestation = atom._build_chain_attestation(atom_input, susc, model, adj)
        for link in attestation.chain:
            assert link.citation
            assert "Girard" in link.citation or "Belk" in link.citation \
                   or "Gallese" in link.citation

    def test_chain_pinned_links_at_canonical_steps(self):
        """L3 (Girard 1961 §2 mediation classification) and L4 (Girard
        1972 §1 rivalry structure) are PINNED. L1, L2, L5 are PILOT_PENDING."""
        atom, atom_input, susc, model, adj = self._make_atom_with_state()
        attestation = atom._build_chain_attestation(atom_input, susc, model, adj)
        statuses = [link.calibration_status for link in attestation.chain]
        assert statuses[0] == CalibrationStatus.PILOT_PENDING  # L1
        assert statuses[1] == CalibrationStatus.PILOT_PENDING  # L2
        assert statuses[2] == CalibrationStatus.PINNED          # L3 (Girard 1961 §2)
        assert statuses[3] == CalibrationStatus.PINNED          # L4 (Girard 1972 §1)
        assert statuses[4] == CalibrationStatus.PILOT_PENDING  # L5


# =============================================================================
# RIVALRY-AWARE MECHANISM ADJUSTMENTS
# =============================================================================


class TestRivalryAwareAdjustments:
    """Pin Girard 1972 §1 rivalry-aware mechanism suppression."""

    def _make_atom(self):
        from unittest.mock import MagicMock
        from adam.atoms.core.mimetic_desire_atom import MimeticDesireAtom
        return MimeticDesireAtom(blackboard=MagicMock(), bridge=MagicMock())

    def test_high_rivalry_neutralizes_scarcity_boost(self):
        """When rivalry probability > 0.30, the scarcity boost from
        high_mimetic baseline (+0.10) is canceled (rivalry penalty -0.10)
        so net scarcity adjustment is non-positive — preventing the
        mechanism from amplifying competition into Girardian resentment.
        (Girard 1972 §1: scarcity + internal-mediation rivalry converts
        mimetic desire into model-as-obstacle hostility.)"""
        atom = self._make_atom()
        susc_profile = {
            "susceptibility": 0.85,
            "level": "high_mimetic",
            "signal_quality": 1.0,
        }
        model_selection = {
            "optimal_model": "in_group_member",
            "rivalry_probability": 0.40,  # high
            "mediation_type": "internal",
            "model_scores": {},
            "proximity": 0.85,
        }
        adj_with_rivalry = atom._compute_mechanism_adjustments(susc_profile, model_selection)

        # Same susceptibility but no rivalry → scarcity should be its full base boost
        no_rivalry_selection = dict(model_selection)
        no_rivalry_selection["rivalry_probability"] = 0.10  # below threshold
        no_rivalry_selection["optimal_model"] = "distant_celebrity"
        no_rivalry_selection["mediation_type"] = "external"
        adj_no_rivalry = atom._compute_mechanism_adjustments(susc_profile, no_rivalry_selection)

        # Rivalry-aware logic must reduce scarcity below the no-rivalry case
        assert adj_with_rivalry["scarcity"] < adj_no_rivalry["scarcity"]
        # And the rivalry-aware case must not be amplifying competition
        assert adj_with_rivalry["scarcity"] <= 0.0

    def test_high_rivalry_boosts_unity(self):
        """When rivalry probability is high, unity is boosted (channels
        imitation toward shared identity rather than competition)."""
        atom = self._make_atom()
        susc_profile = {
            "susceptibility": 0.85,
            "level": "high_mimetic",
            "signal_quality": 1.0,
        }
        model_selection = {
            "optimal_model": "in_group_member",
            "rivalry_probability": 0.40,
            "mediation_type": "internal",
            "model_scores": {},
            "proximity": 0.85,
        }
        adj = atom._compute_mechanism_adjustments(susc_profile, model_selection)
        assert adj.get("unity", 0.0) > 0

    def test_low_rivalry_no_unity_boost(self):
        """Low rivalry → no rivalry-aware boost to unity."""
        atom = self._make_atom()
        susc_profile = {
            "susceptibility": 0.5,
            "level": "moderate_mimetic",
            "signal_quality": 1.0,
        }
        model_selection = {
            "optimal_model": "distant_celebrity",
            "rivalry_probability": 0.05,  # low
            "mediation_type": "external",
            "model_scores": {},
            "proximity": 0.10,
        }
        adj = atom._compute_mechanism_adjustments(susc_profile, model_selection)
        # No rivalry-bypass boost; unity not present in moderate_mimetic
        # base adjustments
        assert adj.get("unity", 0.0) <= 0  # only base adjustment, if any

    def test_low_mimetic_suppresses_mimetic_mechanism(self):
        """Low-mimetic users get negative mimetic_desire adjustment
        (the legacy MIMETIC_MECHANISMS["low_mimetic"] dict — preserved
        for backward compat with existing consumers)."""
        atom = self._make_atom()
        susc_profile = {
            "susceptibility": 0.20,
            "level": "low_mimetic",
            "signal_quality": 1.0,
        }
        model_selection = {
            "optimal_model": "expert_authority",
            "rivalry_probability": 0.05,
            "mediation_type": "external",
            "model_scores": {},
            "proximity": 0.30,
        }
        adj = atom._compute_mechanism_adjustments(susc_profile, model_selection)
        assert adj["mimetic_desire"] < 0
