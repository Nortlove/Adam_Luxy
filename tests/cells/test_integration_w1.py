"""W.1 integration tests — production_aggregator + cascade swap.

Pin: production_aggregator constructs cleanly with or without
underlying singletons; aggregate() returns CellFeatureSet with
W.1-substrate fields populated when sources available; bilateral
cascade integration block uses production_aggregator (not
default_aggregator).
"""
import inspect
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from adam.cells import (
    CellFeaturesAggregator,
    apply_cell_modulation,
    evaluate_predicates,
    production_aggregator,
)
from adam.cells.taxonomy import ConversionStage
from adam.cold_start.models.enums import ArchetypeID


# ---------------------------------------------------------------------------
# production_aggregator factory
# ---------------------------------------------------------------------------

class TestProductionAggregatorFactory:

    def test_returns_aggregator_instance(self):
        agg = production_aggregator()
        assert isinstance(agg, CellFeaturesAggregator)

    def test_aggregate_returns_valid_cell_feature_set(self):
        agg = production_aggregator()
        fs = agg.aggregate(buyer_id="u_test", url_hash="h_test")
        # Cell tuple axes always populate.
        assert fs.cell_id
        assert fs.archetype == ArchetypeID.PRAGMATIST  # W.2-deferred default
        assert fs.journey == ConversionStage.UNAWARE  # sentinel cold-start

    def test_explicit_classifier_activates_posture_wiring(self):
        clf = MagicMock()
        clf.predict.return_value = ["TRANSACTIONAL_COMPARISON"]
        agg = production_aggregator(posture_classifier=clf)
        fs = agg.aggregate(buyer_id="u", url_hash="https://example.com/x")
        assert fs.posture == "TRANSACTIONAL_COMPARISON"

    def test_explicit_priming_store_activates_priming_wiring(self):
        from adam.priming.signature import PagePrimingSignature
        sig = PagePrimingSignature(
            url_hash="h", valence=-0.3, arousal=0.8,
            regulatory_focus_priming="prevention",
            cognitive_load_estimate=0.6,
            activated_frames=("scarcity", "loss_aversion"),
        )
        l1 = MagicMock()
        l1.get.return_value = sig
        store = SimpleNamespace(_l1=l1, _l3=None)
        agg = production_aggregator(priming_store=store)
        fs = agg.aggregate(buyer_id="u", url_hash="h")
        # Priming substrate flows into derived cell features.
        assert fs.valence == -0.3
        assert fs.arousal == 0.8
        from adam.cells.taxonomy import RegulatoryFocus
        assert fs.regulatory_focus == RegulatoryFocus.PREVENTION

    def test_explicit_journey_service_activates_journey_wiring(self):
        from adam.user.journey.models import (
            JourneyStage, JourneyState, UserJourney,
        )
        from adam.cells.accessors import JOURNEY_DEFAULT_CATEGORY
        state = JourneyState(
            user_id="u", category=JOURNEY_DEFAULT_CATEGORY,
            stage=JourneyStage.COMPARING,  # → "evaluating"
        )
        journey = UserJourney(
            user_id="u", category=JOURNEY_DEFAULT_CATEGORY,
            current_state=state,
        )
        svc = SimpleNamespace(
            _journeys={f"u:{JOURNEY_DEFAULT_CATEGORY}": journey},
        )
        agg = production_aggregator(journey_service=svc)
        fs = agg.aggregate(buyer_id="u", url_hash="h")
        assert fs.journey == ConversionStage.EVALUATING

    def test_explicit_graph_cache_activates_cohort_wiring(self):
        gc = MagicMock()
        gc.get_cohort_compensatory_flag.return_value = (True, 0.85)
        agg = production_aggregator(graph_cache=gc)
        fs = agg.aggregate(buyer_id="u", url_hash="h")
        assert fs.compensatory_consumption_pattern is True
        assert fs.compensatory_detection_confidence == 0.85

    def test_explicit_page_intel_cache_activates_cascade_tier_wiring(self):
        cache = MagicMock()
        cache.lookup.return_value = SimpleNamespace(
            attentional_posture=0.5,
            attentional_posture_confidence=0.7,
        )
        agg = production_aggregator(page_intel_cache=cache)
        fs = agg.aggregate(buyer_id="u", url_hash="h")
        assert fs.cascade_attentional_posture == "vigilance_activating"

    def test_w2_deferred_accessors_at_neutral_defaults(self):
        """Q24 = (β) full build → W.2: archetype + maximizer_prior
        remain at neutral defaults until W.2 ships."""
        agg = production_aggregator()
        fs = agg.aggregate(buyer_id="u", url_hash="h")
        assert fs.archetype == ArchetypeID.PRAGMATIST
        assert fs.maximizer_tendency_posterior_mean == 0.5
        assert fs.maximizer_tendency_posterior_strength == 10.0

    def test_mindstate_deferred_to_m_chain(self):
        """Q20 deferred: mindstate composites stay at 0.0 defaults
        until M.0/M.1+ ships."""
        agg = production_aggregator()
        fs = agg.aggregate(buyer_id="u", url_hash="h")
        assert fs.fomo_score == 0.0
        assert fs.psych_ownership_proxy == 0.0
        assert fs.depletion_proxy == 0.0


# ---------------------------------------------------------------------------
# Bilateral cascade integration site swap
# ---------------------------------------------------------------------------

class TestCascadeIntegrationSwap:
    """Pin the bilateral_cascade integration block uses
    production_aggregator (not default_aggregator)."""

    def _cascade_source(self):
        from adam.api.stackadapt import bilateral_cascade
        return inspect.getsource(bilateral_cascade)

    def test_imports_production_aggregator(self):
        src = self._cascade_source()
        assert "production_aggregator" in src

    def test_does_not_import_default_aggregator(self):
        """W.1 swap removes the default_aggregator import + call."""
        src = self._cascade_source()
        # The S6.2 integration block previously imported
        # default_aggregator. The W.1 swap replaces with
        # production_aggregator. Pin the absence to catch any
        # accidental revert.
        assert "default_aggregator" not in src

    def test_calls_production_aggregator(self):
        src = self._cascade_source()
        assert "production_aggregator()" in src

    def test_s62_integration_block_still_present(self):
        """The integration block markers from S6.2 should still
        be present — W.1 swaps the aggregator factory only."""
        src = self._cascade_source()
        assert "S6.2 CELL-CONDITIONAL CREATIVE-SELECTION MODULATION" in src
        assert "Cell-conditional modulation skipped:" in src


# ---------------------------------------------------------------------------
# End-to-end predicate firing on populated W.1 substrate
# ---------------------------------------------------------------------------

class TestEndToEndPredicateFire:
    """With W.1 substrate populated via explicit accessors,
    predicates fire and modulation flows through apply_cell_modulation."""

    def test_compensatory_predicate_fires_with_real_cohort_data(self):
        """Cohort flag True + SOCIAL_CONSUMPTION posture →
        compensatory_cohort_social_consumption predicate fires."""
        gc = MagicMock()
        gc.get_cohort_compensatory_flag.return_value = (True, 0.85)
        clf = MagicMock()
        clf.predict.return_value = ["SOCIAL_CONSUMPTION"]
        agg = production_aggregator(graph_cache=gc, posture_classifier=clf)
        fs = agg.aggregate(buyer_id="u", url_hash="h")
        modulation = evaluate_predicates(fs)
        assert "compensatory_cohort_social_consumption" in modulation.fired_predicates
        # liking + unity boosted; anchoring + loss_aversion dampened.
        assert modulation.class_boosts.get("liking") == 1.4
        assert modulation.class_boosts.get("unity") == 1.4

    def test_persuasion_resistance_predicate_fires_with_priming_data(self):
        """High persuasion-knowledge activation + confidence in
        PagePrimingSignature → high_persuasion_knowledge_skepticism_dampener
        predicate fires."""
        from adam.priming.signature import PagePrimingSignature
        sig = PagePrimingSignature(
            url_hash="h", valence=0.0, arousal=0.5,
            regulatory_focus_priming="neutral",
            cognitive_load_estimate=0.5,
            activated_frames=(),
            persuasion_knowledge_activation=0.7,
            confidence_per_dimension={
                "persuasion_knowledge_activation": 0.85,
            },
        )
        l1 = MagicMock()
        l1.get.return_value = sig
        store = SimpleNamespace(_l1=l1, _l3=None)
        agg = production_aggregator(priming_store=store)
        fs = agg.aggregate(buyer_id="u", url_hash="h")
        modulation = evaluate_predicates(fs)
        assert (
            "high_persuasion_knowledge_skepticism_dampener"
            in modulation.fired_predicates
        )

    def test_apply_cell_modulation_round_trip_on_real_substrate(self):
        gc = MagicMock()
        gc.get_cohort_compensatory_flag.return_value = (True, 0.85)
        clf = MagicMock()
        clf.predict.return_value = ["SOCIAL_CONSUMPTION"]
        agg = production_aggregator(graph_cache=gc, posture_classifier=clf)
        fs = agg.aggregate(buyer_id="u", url_hash="h")
        modulation = evaluate_predicates(fs)

        ms = {
            "liking": 0.5, "unity": 0.5,
            "anchoring": 0.6, "loss_aversion": 0.6,
            "social_proof": 0.5,
        }
        modulated = apply_cell_modulation(ms, modulation)
        # Boosted: liking 0.5 × 1.4 = 0.7; unity 0.5 × 1.4 = 0.7
        assert abs(modulated["liking"] - 0.7) < 1e-9
        assert abs(modulated["unity"] - 0.7) < 1e-9
        # Dampened: anchoring 0.6 × 0.85 = 0.51; loss_aversion 0.6 × 0.85
        assert abs(modulated["anchoring"] - 0.51) < 1e-9
        assert abs(modulated["loss_aversion"] - 0.51) < 1e-9
        # Untouched: social_proof
        assert modulated["social_proof"] == 0.5


# ---------------------------------------------------------------------------
# Latency budget (Q22 revised: 12-15ms acceptable)
# ---------------------------------------------------------------------------

class TestProductionAggregatorLatency:

    def test_p99_under_15ms(self):
        """Q22-revised budget: aggregator p99 < 15ms over 10,000
        random aggregations. With explicit mock accessors (no
        Neo4j/Redis), should be well under."""
        import random
        import time

        gc = MagicMock()
        gc.get_cohort_compensatory_flag.return_value = (False, 0.5)
        cache = MagicMock()
        cache.lookup.return_value = None
        svc = SimpleNamespace(_journeys={})
        agg = production_aggregator(
            graph_cache=gc, page_intel_cache=cache, journey_service=svc,
        )

        rng = random.Random(2026)
        latencies_us = []
        for _ in range(10000):
            t0 = time.perf_counter()
            agg.aggregate(
                buyer_id=f"u{rng.randint(1, 1000)}",
                url_hash=f"h{rng.randint(1, 1000)}",
            )
            latencies_us.append((time.perf_counter() - t0) * 1_000_000)
        latencies_us.sort()
        p99 = latencies_us[int(len(latencies_us) * 0.99)]
        assert p99 < 15000, (
            f"p99 latency {p99:.1f}μs exceeds Q22-revised 15ms budget"
        )
