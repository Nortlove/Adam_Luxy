"""S6.2 — CellFeaturesAggregator tests.

Pin: aggregator returns a valid CellFeatureSet with all fields populated;
each substrate fetch failure absorbs into a per-source default; bid-time
latency under target. The aggregator NEVER propagates exceptions.
"""
import random
import time
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from adam.cells.aggregator import (
    CellFeaturesAggregator,
    default_aggregator,
)
from adam.cells.features import CellFeatureSet
from adam.cells.taxonomy import (
    ConversionStage,
    RegulatoryFocus,
    ValenceArousalQuadrant,
)
from adam.cold_start.models.enums import ArchetypeID


def _make_aggregator(**overrides):
    """Build an aggregator with safe-default accessors, allowing
    per-test overrides."""
    base = dict(
        archetype_accessor=lambda buyer_id: ArchetypeID.ANALYST,
        posture_accessor=lambda url_hash: "TASK_COMPLETION",
        journey_accessor=lambda buyer_id: ConversionStage.INTENDING,
        priming_accessor=lambda url_hash: SimpleNamespace(
            valence=0.5, arousal=0.7,
            cognitive_load_estimate=0.4,
            regulatory_focus_priming="promotion",
            persuasion_knowledge_activation=0.3,
            confidence_persuasion_knowledge=0.7,
            activated_frames=("scarcity", "social_proof"),
        ),
        mindstate_accessor=lambda buyer_id, url_hash: SimpleNamespace(
            fomo_score=0.6,
            psych_ownership_proxy=0.4,
            depletion_proxy=0.5,
            session_position_seconds=600.0,
            browsing_momentum=0.7,
        ),
        cohort_accessor=lambda buyer_id: (True, 0.85),
        maximizer_prior_accessor=lambda buyer_id, arch: (0.65, 22.0),
        cascade_tier_accessor=None,
    )
    base.update(overrides)
    return CellFeaturesAggregator(**base)


class TestHappyPath:

    def test_aggregate_populates_all_fields(self):
        agg = _make_aggregator()
        fs = agg.aggregate(buyer_id="u1", url_hash="h1")
        assert isinstance(fs, CellFeatureSet)
        assert fs.archetype == ArchetypeID.ANALYST
        assert fs.posture == "TASK_COMPLETION"
        assert fs.journey == ConversionStage.INTENDING
        assert fs.regulatory_focus == RegulatoryFocus.PROMOTION
        assert fs.valence_arousal == ValenceArousalQuadrant.Q1_EXCITED
        assert fs.fomo_score == 0.6
        assert fs.psych_ownership_proxy == 0.4
        assert fs.depletion_proxy == 0.5
        assert fs.compensatory_consumption_pattern is True
        assert fs.compensatory_detection_confidence == 0.85
        assert fs.maximizer_tendency_posterior_mean == 0.65
        assert fs.persuasion_knowledge_activation == 0.3
        assert fs.confidence_persuasion_knowledge == 0.7
        assert "scarcity" in fs.activated_frames
        # cell_id resolved via F.1 constructor
        assert fs.cell_id == "ANALYST_TC_INT_PROM_Q1"

    def test_cascade_tier_accessor_populates_when_provided(self):
        agg = _make_aggregator(
            cascade_tier_accessor=lambda buyer_id, url_hash: "blend_compatible",
        )
        fs = agg.aggregate(buyer_id="u1", url_hash="h1")
        assert fs.cascade_attentional_posture == "blend_compatible"

    def test_cascade_tier_default_none_when_no_accessor(self):
        agg = _make_aggregator()
        fs = agg.aggregate(buyer_id="u1", url_hash="h1")
        assert fs.cascade_attentional_posture is None

    def test_enable_timing_populates_aggregated_at(self):
        agg = _make_aggregator()
        agg._enable_timing = True
        fs = agg.aggregate(buyer_id="u1", url_hash="h1")
        assert fs.aggregated_at is not None
        # ISO8601 with timezone
        assert "T" in fs.aggregated_at and "+" in fs.aggregated_at


class TestFailSoft:
    """Each substrate fetch failure must absorb into a per-source
    default; aggregation never propagates exceptions."""

    def _mk_raising(self):
        def _raise(*args, **kwargs):
            raise RuntimeError("substrate fetch failed")
        return _raise

    def test_archetype_failure_defaults_to_pragmatist(self):
        agg = _make_aggregator(archetype_accessor=self._mk_raising())
        fs = agg.aggregate(buyer_id="u1", url_hash="h1")
        assert fs.archetype == ArchetypeID.PRAGMATIST

    def test_posture_failure_defaults_to_information_foraging(self):
        agg = _make_aggregator(posture_accessor=self._mk_raising())
        fs = agg.aggregate(buyer_id="u1", url_hash="h1")
        assert fs.posture == "INFORMATION_FORAGING"

    def test_journey_failure_defaults_to_unaware(self):
        agg = _make_aggregator(journey_accessor=self._mk_raising())
        fs = agg.aggregate(buyer_id="u1", url_hash="h1")
        assert fs.journey == ConversionStage.UNAWARE

    def test_priming_failure_defaults_to_neutral_priming(self):
        agg = _make_aggregator(priming_accessor=self._mk_raising())
        fs = agg.aggregate(buyer_id="u1", url_hash="h1")
        assert fs.regulatory_focus == RegulatoryFocus.NEUTRAL
        assert fs.valence == 0.0
        assert fs.arousal == 0.5
        assert fs.persuasion_knowledge_activation == 0.0

    def test_mindstate_failure_defaults_mindstate_fields(self):
        """Schema-evolution note: pre-M.1, mindstate-fetch failure
        defaulted ALL mindstate fields to 0 (mindstate was the only
        path). Post-M.1, fomo_score has an inline aggregator-side
        compute path (Q31) that produces valid values from priming
        inputs even when mindstate fetch fails. The other 2 mindstate
        composites (psych_ownership_proxy, depletion_proxy) still
        default to 0 because M.2/M.3 are deferred per Q29=BETA.

        With this fixture's priming (arousal=0.7, scarcity in
        activated_frames, regulatory_focus_priming="promotion"),
        the inline fomo compute produces 0.7 × 1.0 × 1.2 = 0.84.
        """
        agg = _make_aggregator(mindstate_accessor=self._mk_raising())
        fs = agg.aggregate(buyer_id="u1", url_hash="h1")
        # M.1 inline compute fires even when mindstate fetch fails.
        assert fs.fomo_score == pytest.approx(0.84)
        # M.2/M.3 deferred — these still default to 0 when mindstate fails.
        assert fs.psych_ownership_proxy == 0.0
        assert fs.depletion_proxy == 0.0
        assert fs.browsing_momentum == 0.5

    def test_cohort_failure_defaults_to_false_neutral(self):
        agg = _make_aggregator(cohort_accessor=self._mk_raising())
        fs = agg.aggregate(buyer_id="u1", url_hash="h1")
        assert fs.compensatory_consumption_pattern is False
        assert fs.compensatory_detection_confidence == 0.5

    def test_maximizer_failure_defaults_to_archetype_prior_mean(self):
        agg = _make_aggregator(maximizer_prior_accessor=self._mk_raising())
        fs = agg.aggregate(buyer_id="u1", url_hash="h1")
        assert fs.maximizer_tendency_posterior_mean == 0.5
        assert fs.maximizer_tendency_posterior_strength == 10.0

    def test_cascade_tier_failure_defaults_to_none(self):
        agg = _make_aggregator(cascade_tier_accessor=self._mk_raising())
        fs = agg.aggregate(buyer_id="u1", url_hash="h1")
        assert fs.cascade_attentional_posture is None

    def test_all_failures_returns_valid_cell_feature_set(self):
        """Aggregator with EVERY substrate accessor raising still
        returns a valid CellFeatureSet — never propagates exceptions
        to bid-time path."""
        raising = self._mk_raising()
        agg = CellFeaturesAggregator(
            archetype_accessor=raising,
            posture_accessor=raising,
            journey_accessor=raising,
            priming_accessor=raising,
            mindstate_accessor=raising,
            cohort_accessor=raising,
            maximizer_prior_accessor=raising,
            cascade_tier_accessor=raising,
        )
        fs = agg.aggregate(buyer_id="u1", url_hash="h1")
        assert isinstance(fs, CellFeatureSet)
        assert fs.archetype == ArchetypeID.PRAGMATIST
        assert fs.posture == "INFORMATION_FORAGING"
        assert fs.journey == ConversionStage.UNAWARE
        assert fs.regulatory_focus == RegulatoryFocus.NEUTRAL
        # Cell ID still resolves (all-defaults tuple is valid in
        # F.1 taxonomy).
        assert fs.cell_id


class TestPagePrimingSignatureConfidenceExtraction:
    """B's PagePrimingSignature uses a confidence_per_dimension dict
    pattern. Aggregator must extract persuasion_knowledge confidence
    from either the direct attribute OR the dict."""

    def test_extract_from_direct_attribute(self):
        priming = SimpleNamespace(
            valence=0.0, arousal=0.5, cognitive_load_estimate=0.5,
            regulatory_focus_priming="neutral",
            persuasion_knowledge_activation=0.4,
            confidence_persuasion_knowledge=0.78,  # direct attribute
            activated_frames=(),
        )
        agg = _make_aggregator(priming_accessor=lambda url_hash: priming)
        fs = agg.aggregate(buyer_id="u1", url_hash="h1")
        assert fs.confidence_persuasion_knowledge == 0.78

    def test_extract_from_confidence_per_dimension_dict(self):
        priming = SimpleNamespace(
            valence=0.0, arousal=0.5, cognitive_load_estimate=0.5,
            regulatory_focus_priming="neutral",
            persuasion_knowledge_activation=0.4,
            confidence_per_dimension={
                "persuasion_knowledge_activation": 0.82,
            },
            activated_frames=(),
        )
        agg = _make_aggregator(priming_accessor=lambda url_hash: priming)
        fs = agg.aggregate(buyer_id="u1", url_hash="h1")
        assert fs.confidence_persuasion_knowledge == 0.82


class TestLatencyBudget:

    def test_aggregate_p99_under_8ms(self):
        """10,000 random aggregations; p99 < 8ms (the spec's
        target)."""
        agg = _make_aggregator()
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
        assert p99 < 8000, (
            f"p99 latency {p99:.1f}μs exceeds 8ms aggregator budget"
        )


class TestDefaultFactory:

    def test_default_aggregator_returns_valid_aggregator(self):
        agg = default_aggregator()
        assert isinstance(agg, CellFeaturesAggregator)
        fs = agg.aggregate(buyer_id="u1", url_hash="h1")
        # Default factory uses neutral defaults.
        assert fs.archetype == ArchetypeID.PRAGMATIST
        assert fs.posture == "INFORMATION_FORAGING"
        assert fs.journey == ConversionStage.UNAWARE
        assert fs.regulatory_focus == RegulatoryFocus.NEUTRAL
        assert fs.cell_id == "PRAGMATIST_IF_UNA_NEUT_Q4"
