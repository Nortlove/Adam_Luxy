"""S6.2 — predicate registry + evaluator + composition tests.

Pin: @cell_predicate registers; duplicate name raises; evaluator
composes multiplicative boosts/dampens + additive diversity
(clipped); fail-soft on predicate exceptions; latency budget.
"""
import random
import time

import pytest

from adam.cells.evaluator import (
    CombinedModulation,
    CreativeModulation,
    _PREDICATE_REGISTRY,
    _clear_registry_for_testing,
    apply_cell_modulation,
    cell_predicate,
    evaluate_predicates,
    get_registered_predicates,
)
from adam.cells.features import CellFeatureSet
from adam.cells.taxonomy import (
    ConversionStage,
    RegulatoryFocus,
    ValenceArousalQuadrant,
)
from adam.cold_start.models.enums import ArchetypeID


def _make_features(**overrides):
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


@pytest.fixture
def isolated_registry():
    """Save and restore the registry around each test for hermetic
    isolation. Snapshot the seed predicates from package import,
    then clear, then restore at teardown."""
    snapshot = list(_PREDICATE_REGISTRY)
    _clear_registry_for_testing()
    yield
    _clear_registry_for_testing()
    _PREDICATE_REGISTRY.extend(snapshot)


# ---------------------------------------------------------------------------
# Registry + decorator
# ---------------------------------------------------------------------------

class TestRegistry:

    def test_decorator_registers_function(self, isolated_registry):
        @cell_predicate(name="t_pred_1")
        def _pred(features):
            return None
        assert "t_pred_1" in get_registered_predicates()

    def test_get_registered_predicates_returns_names(self, isolated_registry):
        @cell_predicate(name="t_pred_a")
        def _a(features):
            return None

        @cell_predicate(name="t_pred_b")
        def _b(features):
            return None
        names = get_registered_predicates()
        assert "t_pred_a" in names
        assert "t_pred_b" in names

    def test_duplicate_name_raises_at_decoration_time(self, isolated_registry):
        @cell_predicate(name="t_dup")
        def _first(features):
            return None
        with pytest.raises(ValueError, match="Duplicate predicate name"):
            @cell_predicate(name="t_dup")
            def _second(features):
                return None


# ---------------------------------------------------------------------------
# Evaluator semantics
# ---------------------------------------------------------------------------

class TestEvaluatorSemantics:

    def test_empty_registry_returns_neutral(self, isolated_registry):
        result = evaluate_predicates(_make_features())
        assert result.is_neutral
        assert result.fired_predicates == []

    def test_single_predicate_fire(self, isolated_registry):
        @cell_predicate(name="t_single")
        def _p(features):
            return CreativeModulation(
                predicate_name="t_single",
                cell_id=features.cell_id,
                creative_class_boosts={"scarcity": 1.5},
                reason="test",
            )
        result = evaluate_predicates(_make_features())
        assert result.fired_predicates == ["t_single"]
        assert result.class_boosts["scarcity"] == 1.5
        assert "test" in result.reasons

    def test_multiple_boosts_combine_multiplicatively(self, isolated_registry):
        @cell_predicate(name="t_a")
        def _a(features):
            return CreativeModulation(
                predicate_name="t_a", cell_id=features.cell_id,
                creative_class_boosts={"scarcity": 1.5},
            )

        @cell_predicate(name="t_b")
        def _b(features):
            return CreativeModulation(
                predicate_name="t_b", cell_id=features.cell_id,
                creative_class_boosts={"scarcity": 1.3},
            )
        result = evaluate_predicates(_make_features())
        # 1.5 × 1.3 = 1.95
        assert abs(result.class_boosts["scarcity"] - 1.95) < 1e-9

    def test_multiple_dampens_combine_multiplicatively(self, isolated_registry):
        @cell_predicate(name="t_a")
        def _a(features):
            return CreativeModulation(
                predicate_name="t_a", cell_id=features.cell_id,
                creative_class_dampens={"reciprocity": 0.7},
            )

        @cell_predicate(name="t_b")
        def _b(features):
            return CreativeModulation(
                predicate_name="t_b", cell_id=features.cell_id,
                creative_class_dampens={"reciprocity": 0.9},
            )
        result = evaluate_predicates(_make_features())
        assert abs(result.class_dampens["reciprocity"] - 0.63) < 1e-9

    def test_diversity_adjustment_additive_and_clipped(self, isolated_registry):
        @cell_predicate(name="t_div_a")
        def _a(features):
            return CreativeModulation(
                predicate_name="t_div_a", cell_id=features.cell_id,
                diversity_adjustment=0.4,
            )

        @cell_predicate(name="t_div_b")
        def _b(features):
            return CreativeModulation(
                predicate_name="t_div_b", cell_id=features.cell_id,
                diversity_adjustment=0.8,  # would push to 1.2 → clip
            )
        result = evaluate_predicates(_make_features())
        assert result.diversity_adjustment == 1.0

    def test_diversity_adjustment_clips_negative_floor(self, isolated_registry):
        @cell_predicate(name="t_neg_a")
        def _a(features):
            return CreativeModulation(
                predicate_name="t_neg_a", cell_id=features.cell_id,
                diversity_adjustment=-0.6,
            )

        @cell_predicate(name="t_neg_b")
        def _b(features):
            return CreativeModulation(
                predicate_name="t_neg_b", cell_id=features.cell_id,
                diversity_adjustment=-0.8,  # → -1.4 → clip to -1.0
            )
        result = evaluate_predicates(_make_features())
        assert result.diversity_adjustment == -1.0

    def test_predicate_returning_none_is_skipped(self, isolated_registry):
        @cell_predicate(name="t_none")
        def _p(features):
            return None
        result = evaluate_predicates(_make_features())
        assert result.is_neutral
        assert result.fired_predicates == []

    def test_predicate_exception_skipped_others_continue(self, isolated_registry):
        @cell_predicate(name="t_raises")
        def _bad(features):
            raise RuntimeError("predicate bug")

        @cell_predicate(name="t_good")
        def _good(features):
            return CreativeModulation(
                predicate_name="t_good", cell_id=features.cell_id,
                creative_class_boosts={"authority": 1.2},
            )
        result = evaluate_predicates(_make_features())
        # Bad predicate skipped; good predicate fired.
        assert "t_raises" not in result.fired_predicates
        assert "t_good" in result.fired_predicates
        assert result.class_boosts["authority"] == 1.2

    def test_combined_modulation_is_neutral_property(self):
        cm = CombinedModulation(
            cell_id="x", fired_predicates=[], class_boosts={},
            class_dampens={}, diversity_adjustment=0.0, reasons=[],
        )
        assert cm.is_neutral

        cm2 = CombinedModulation(
            cell_id="x", fired_predicates=["p"], class_boosts={"a": 1.5},
            class_dampens={}, diversity_adjustment=0.0, reasons=[],
        )
        assert not cm2.is_neutral


# ---------------------------------------------------------------------------
# apply_cell_modulation
# ---------------------------------------------------------------------------

class TestApplyCellModulation:

    def test_neutral_modulation_returns_copy_unchanged(self):
        ms = {"social_proof": 0.7, "scarcity": 0.5}
        modulation = CombinedModulation(
            cell_id="x", fired_predicates=[], class_boosts={},
            class_dampens={}, diversity_adjustment=0.0, reasons=[],
        )
        result = apply_cell_modulation(ms, modulation)
        assert result == ms
        # Returns a new dict, not the same reference.
        assert result is not ms

    def test_boost_multiplies_matching_mechanism(self):
        ms = {"scarcity": 0.6, "authority": 0.5}
        modulation = CombinedModulation(
            cell_id="x", fired_predicates=["p"],
            class_boosts={"scarcity": 1.5}, class_dampens={},
            diversity_adjustment=0.0, reasons=[],
        )
        result = apply_cell_modulation(ms, modulation)
        assert abs(result["scarcity"] - 0.9) < 1e-9
        assert result["authority"] == 0.5  # unchanged

    def test_dampen_multiplies_matching_mechanism(self):
        ms = {"reciprocity": 0.4}
        modulation = CombinedModulation(
            cell_id="x", fired_predicates=["p"], class_boosts={},
            class_dampens={"reciprocity": 0.7},
            diversity_adjustment=0.0, reasons=[],
        )
        result = apply_cell_modulation(ms, modulation)
        assert abs(result["reciprocity"] - 0.28) < 1e-9

    def test_boost_for_unknown_mechanism_silently_ignored(self):
        """Predicates may emit boosts for mechanisms the cascade
        didn't compute. That's a no-op (not an error)."""
        ms = {"social_proof": 0.7}
        modulation = CombinedModulation(
            cell_id="x", fired_predicates=["p"],
            class_boosts={"unknown_mechanism": 1.5}, class_dampens={},
            diversity_adjustment=0.0, reasons=[],
        )
        result = apply_cell_modulation(ms, modulation)
        assert "unknown_mechanism" not in result
        assert result == ms


# ---------------------------------------------------------------------------
# Latency budget — full registry from package import
# ---------------------------------------------------------------------------

class TestLatencyBudget:

    def test_evaluate_predicates_p99_under_5ms(self):
        """With the full seed predicate registry loaded by package
        import (6 seed predicates), evaluator p99 < 5ms over 10,000
        random feature sets."""
        rng = random.Random(2026)
        archetypes = list(ArchetypeID)
        postures = [
            "INFORMATION_FORAGING", "TASK_COMPLETION",
            "LEISURE_BROWSING", "SOCIAL_CONSUMPTION",
            "TRANSACTIONAL_COMPARISON",
        ]
        stages = list(ConversionStage)
        regs = list(RegulatoryFocus)
        quadrants = list(ValenceArousalQuadrant)

        latencies_us = []
        for _ in range(10000):
            fs = _make_features(
                archetype=rng.choice(archetypes),
                posture=rng.choice(postures),
                journey=rng.choice(stages),
                regulatory_focus=rng.choice(regs),
                valence_arousal=rng.choice(quadrants),
                fomo_score=rng.random(),
                psych_ownership_proxy=rng.random(),
                depletion_proxy=rng.random(),
                persuasion_knowledge_activation=rng.random(),
                confidence_persuasion_knowledge=rng.random(),
                maximizer_tendency_posterior_mean=rng.random(),
                compensatory_consumption_pattern=rng.choice([True, False]),
                compensatory_detection_confidence=rng.random(),
            )
            t0 = time.perf_counter()
            evaluate_predicates(fs)
            latencies_us.append((time.perf_counter() - t0) * 1_000_000)
        latencies_us.sort()
        p99 = latencies_us[int(len(latencies_us) * 0.99)]
        assert p99 < 5000, (
            f"evaluate_predicates p99 latency {p99:.1f}μs exceeds 5ms budget"
        )
