"""S6.2 — CellFeatureSet schema tests."""
import pytest

from adam.cells.features import CellFeatureSet
from adam.cells.taxonomy import (
    ConversionStage,
    RegulatoryFocus,
    ValenceArousalQuadrant,
)
from adam.cold_start.models.enums import ArchetypeID


class TestCellFeatureSetSchema:

    def test_default_construction_with_required_fields(self):
        """Required fields (the 6 cell-tuple-axis fields + cell_id)
        construct with safe optional defaults across all other slots."""
        fs = CellFeatureSet(
            cell_id="ANALYST_TC_INT_PROM_Q1",
            archetype=ArchetypeID.ANALYST,
            posture="TASK_COMPLETION",
            journey=ConversionStage.INTENDING,
            regulatory_focus=RegulatoryFocus.PROMOTION,
            valence_arousal=ValenceArousalQuadrant.Q1_EXCITED,
        )
        assert fs.cell_id == "ANALYST_TC_INT_PROM_Q1"
        assert fs.fomo_score == 0.0
        assert fs.psych_ownership_proxy == 0.0
        assert fs.depletion_proxy == 0.0
        assert fs.compensatory_consumption_pattern is False
        assert fs.compensatory_detection_confidence == 0.5
        assert fs.maximizer_tendency_posterior_mean == 0.5
        assert fs.maximizer_tendency_posterior_strength == 10.0
        assert fs.cascade_attentional_posture is None
        assert fs.activated_frames == frozenset()

    def test_full_construction_all_fields(self):
        fs = CellFeatureSet(
            cell_id="CONNECTOR_SC_EVA_NEUT_Q2",
            archetype=ArchetypeID.CONNECTOR,
            posture="SOCIAL_CONSUMPTION",
            journey=ConversionStage.EVALUATING,
            regulatory_focus=RegulatoryFocus.NEUTRAL,
            valence_arousal=ValenceArousalQuadrant.Q2_CONTENTED,
            valence=0.4, arousal=0.3,
            cognitive_load_estimate=0.6,
            persuasion_knowledge_activation=0.7,
            confidence_persuasion_knowledge=0.85,
            activated_frames=frozenset({"social_proof", "scarcity"}),
            fomo_score=0.55,
            psych_ownership_proxy=0.4,
            depletion_proxy=0.3,
            session_position_seconds=900.0,
            browsing_momentum=0.7,
            compensatory_consumption_pattern=True,
            compensatory_detection_confidence=0.85,
            cohort_mechanism_priors={"social_proof": 0.72, "liking": 0.65},
            maximizer_tendency_posterior_mean=0.7,
            maximizer_tendency_posterior_strength=25.0,
            cascade_attentional_posture="blend_compatible",
            aggregated_at="2026-05-07T22:00:00+00:00",
        )
        assert fs.cohort_mechanism_priors["social_proof"] == 0.72
        assert fs.activated_frames == frozenset({"social_proof", "scarcity"})

    def test_frozen_dataclass_invariant(self):
        """Predicates must not mutate features."""
        import dataclasses
        fs = CellFeatureSet(
            cell_id="x", archetype=ArchetypeID.ANALYST,
            posture="TASK_COMPLETION",
            journey=ConversionStage.UNAWARE,
            regulatory_focus=RegulatoryFocus.NEUTRAL,
            valence_arousal=ValenceArousalQuadrant.Q4_WITHDRAWN,
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            fs.fomo_score = 0.99  # type: ignore[misc]

    def test_orthogonal_cascade_posture_field_typed_separately_from_5class(self):
        """Pin Q18 orthogonality: cascade_attentional_posture is a
        separate field from posture (5-class). Both can be populated
        independently with non-overlapping values."""
        fs = CellFeatureSet(
            cell_id="x", archetype=ArchetypeID.ANALYST,
            posture="TASK_COMPLETION",  # 5-class value
            journey=ConversionStage.UNAWARE,
            regulatory_focus=RegulatoryFocus.NEUTRAL,
            valence_arousal=ValenceArousalQuadrant.Q4_WITHDRAWN,
            cascade_attentional_posture="vigilance_activating",  # 4-class value
        )
        # 5-class and 4-class values are totally different vocabularies.
        assert fs.posture == "TASK_COMPLETION"
        assert fs.cascade_attentional_posture == "vigilance_activating"
