"""S6.2 — seed predicate fire-condition tests.

Each seed predicate gets a positive case (fires when condition met)
and at least one negative case (does NOT fire when condition not met).
"""
import pytest

from adam.cells.evaluator import CreativeModulation
from adam.cells.features import CellFeatureSet
from adam.cells.predicates.compensatory_predicates import (
    compensatory_cohort_social_consumption,
)
from adam.cells.predicates.fomo_predicates import (
    high_fomo_prevention,
    high_fomo_promotion,
)
from adam.cells.predicates.maximizer_predicates import (
    high_maximizer_comparison,
)
from adam.cells.predicates.ownership_predicates import (
    high_psych_ownership,
)
from adam.cells.predicates.persuasion_resistance_predicates import (
    high_persuasion_knowledge,
)
from adam.cells.taxonomy import (
    ConversionStage,
    RegulatoryFocus,
    ValenceArousalQuadrant,
)
from adam.cold_start.models.enums import ArchetypeID


def _features(**overrides):
    base = dict(
        cell_id="ANALYST_TC_INT_PROM_Q1",
        archetype=ArchetypeID.ANALYST,
        posture="TASK_COMPLETION",
        journey=ConversionStage.INTENDING,
        regulatory_focus=RegulatoryFocus.PROMOTION,
        valence_arousal=ValenceArousalQuadrant.Q1_EXCITED,
    )
    base.update(overrides)
    return CellFeatureSet(**base)


# ---------------------------------------------------------------------------
# FOMO predicates
# ---------------------------------------------------------------------------

class TestHighFomoPromotion:

    def test_fires_on_high_fomo_promotion(self):
        result = high_fomo_promotion(_features(
            fomo_score=0.85,
            regulatory_focus=RegulatoryFocus.PROMOTION,
        ))
        assert isinstance(result, CreativeModulation)
        assert result.predicate_name == "high_fomo_promotion"
        assert result.creative_class_boosts.get("scarcity") == 1.5
        assert result.creative_class_dampens.get("reciprocity") == 0.7

    def test_does_not_fire_on_low_fomo(self):
        assert high_fomo_promotion(_features(
            fomo_score=0.4,
            regulatory_focus=RegulatoryFocus.PROMOTION,
        )) is None

    def test_does_not_fire_on_prevention_focus(self):
        assert high_fomo_promotion(_features(
            fomo_score=0.85,
            regulatory_focus=RegulatoryFocus.PREVENTION,
        )) is None


class TestHighFomoPrevention:

    def test_fires_on_high_fomo_prevention(self):
        result = high_fomo_prevention(_features(
            fomo_score=0.8,
            regulatory_focus=RegulatoryFocus.PREVENTION,
        ))
        assert isinstance(result, CreativeModulation)
        assert result.creative_class_boosts.get("loss_aversion") == 1.4
        assert result.creative_class_dampens.get("scarcity") == 0.8

    def test_does_not_fire_on_promotion_focus(self):
        assert high_fomo_prevention(_features(
            fomo_score=0.8,
            regulatory_focus=RegulatoryFocus.PROMOTION,
        )) is None


# ---------------------------------------------------------------------------
# Ownership predicate
# ---------------------------------------------------------------------------

class TestHighPsychOwnership:

    def test_fires_on_high_ownership(self):
        result = high_psych_ownership(_features(psych_ownership_proxy=0.7))
        assert isinstance(result, CreativeModulation)
        assert result.creative_class_boosts.get("commitment_consistency") == 1.4

    def test_does_not_fire_on_low_ownership(self):
        assert high_psych_ownership(_features(psych_ownership_proxy=0.3)) is None


# ---------------------------------------------------------------------------
# Maximizer predicate
# ---------------------------------------------------------------------------

class TestHighMaximizerComparison:

    def test_fires_on_maximizer_with_comparison_posture(self):
        result = high_maximizer_comparison(_features(
            maximizer_tendency_posterior_mean=0.75,
            posture="TRANSACTIONAL_COMPARISON",
        ))
        assert isinstance(result, CreativeModulation)
        assert result.creative_class_boosts.get("authority") == 1.4

    def test_does_not_fire_without_comparison_posture(self):
        assert high_maximizer_comparison(_features(
            maximizer_tendency_posterior_mean=0.75,
            posture="TASK_COMPLETION",
        )) is None

    def test_does_not_fire_on_low_maximizer(self):
        assert high_maximizer_comparison(_features(
            maximizer_tendency_posterior_mean=0.4,
            posture="TRANSACTIONAL_COMPARISON",
        )) is None


# ---------------------------------------------------------------------------
# Persuasion-resistance predicate
# ---------------------------------------------------------------------------

class TestHighPersuasionKnowledge:

    def test_fires_on_high_pkm(self):
        result = high_persuasion_knowledge(_features(
            persuasion_knowledge_activation=0.7,
            confidence_persuasion_knowledge=0.85,
        ))
        assert isinstance(result, CreativeModulation)
        assert result.creative_class_boosts.get("authority") == 1.4
        assert result.creative_class_dampens.get("scarcity") == 0.7

    def test_does_not_fire_on_low_pkm_activation(self):
        assert high_persuasion_knowledge(_features(
            persuasion_knowledge_activation=0.3,
            confidence_persuasion_knowledge=0.85,
        )) is None

    def test_does_not_fire_on_low_pkm_confidence(self):
        """High activation but low-confidence reading → skip
        (uncertain whether the consumer is actually persuasion-savvy)."""
        assert high_persuasion_knowledge(_features(
            persuasion_knowledge_activation=0.7,
            confidence_persuasion_knowledge=0.4,
        )) is None


# ---------------------------------------------------------------------------
# Compensatory cohort predicate
# ---------------------------------------------------------------------------

class TestCompensatoryCohortSocialConsumption:

    def test_fires_on_compensatory_cohort_social_consumption(self):
        result = compensatory_cohort_social_consumption(_features(
            posture="SOCIAL_CONSUMPTION",
            compensatory_consumption_pattern=True,
            compensatory_detection_confidence=0.85,
        ))
        assert isinstance(result, CreativeModulation)
        assert result.creative_class_boosts.get("liking") == 1.4
        assert result.creative_class_boosts.get("unity") == 1.4

    def test_does_not_fire_without_social_consumption_posture(self):
        assert compensatory_cohort_social_consumption(_features(
            posture="TASK_COMPLETION",
            compensatory_consumption_pattern=True,
            compensatory_detection_confidence=0.85,
        )) is None

    def test_does_not_fire_with_flag_false(self):
        assert compensatory_cohort_social_consumption(_features(
            posture="SOCIAL_CONSUMPTION",
            compensatory_consumption_pattern=False,
            compensatory_detection_confidence=0.85,
        )) is None

    def test_does_not_fire_on_low_confidence(self):
        assert compensatory_cohort_social_consumption(_features(
            posture="SOCIAL_CONSUMPTION",
            compensatory_consumption_pattern=True,
            compensatory_detection_confidence=0.50,
        )) is None
