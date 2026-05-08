"""W.1 accessor factory tests.

Pin: each of 5 accessor factories returns a closure with the
expected S6.2 signature; cold-start returns S6.2 neutral default;
exceptions inside source modules absorb to neutral default.

Q21: no asyncio.run in any accessor — all paths sync.
Q23: cold-start standardized at the wrapper seam.
"""
import threading
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from adam.cells.accessors import (
    JOURNEY_DEFAULT_CATEGORY,
    make_cascade_tier_accessor,
    make_cohort_accessor,
    make_journey_accessor,
    make_posture_accessor,
    make_priming_accessor,
)
from adam.cells.taxonomy import ConversionStage


# ---------------------------------------------------------------------------
# cohort_accessor (direct-call)
# ---------------------------------------------------------------------------

class TestCohortAccessor:

    def test_direct_call_returns_tuple(self):
        gc = MagicMock()
        gc.get_cohort_compensatory_flag.return_value = (True, 0.85)
        acc = make_cohort_accessor(gc)
        assert acc("buyer_xyz") == (True, 0.85)
        gc.get_cohort_compensatory_flag.assert_called_once_with("buyer_xyz")

    def test_unknown_buyer_returns_neutral_default(self):
        """F.2's get_cohort_compensatory_flag returns (False, 0.50)
        for unknown buyers — direct binding preserves this."""
        gc = MagicMock()
        gc.get_cohort_compensatory_flag.return_value = (False, 0.50)
        acc = make_cohort_accessor(gc)
        assert acc("unknown_buyer") == (False, 0.50)

    def test_fail_soft_on_graph_cache_exception(self):
        gc = MagicMock()
        gc.get_cohort_compensatory_flag.side_effect = RuntimeError("Neo4j down")
        acc = make_cohort_accessor(gc)
        assert acc("u") == (False, 0.50)


# ---------------------------------------------------------------------------
# posture_accessor (lightweight adapter)
# ---------------------------------------------------------------------------

class TestPostureAccessor:

    def test_returns_label_for_known_url(self):
        clf = MagicMock()
        clf.predict.return_value = ["SOCIAL_CONSUMPTION"]
        acc = make_posture_accessor(clf)
        assert acc("https://example.com/x") == "SOCIAL_CONSUMPTION"
        clf.predict.assert_called_once_with(["https://example.com/x"])

    def test_empty_prediction_falls_back_to_default(self):
        clf = MagicMock()
        clf.predict.return_value = []
        acc = make_posture_accessor(clf)
        assert acc("h") == "INFORMATION_FORAGING"

    def test_falsy_prediction_falls_back_to_default(self):
        clf = MagicMock()
        clf.predict.return_value = [""]
        acc = make_posture_accessor(clf)
        assert acc("h") == "INFORMATION_FORAGING"

    def test_unfit_classifier_fails_soft(self):
        """URLPostureClassifier raises RuntimeError('Call fit() first')
        when not trained — must fail-soft to default."""
        clf = MagicMock()
        clf.predict.side_effect = RuntimeError("Call fit() first")
        acc = make_posture_accessor(clf)
        assert acc("h") == "INFORMATION_FORAGING"


# ---------------------------------------------------------------------------
# priming_accessor (sync-only adapter)
# ---------------------------------------------------------------------------

class TestPrimingAccessor:

    def test_l1_hit_returns_signature(self):
        from adam.priming.signature import PagePrimingSignature
        sig = PagePrimingSignature(
            url_hash="h1", valence=0.5, arousal=0.7,
            regulatory_focus_priming="promotion",
            cognitive_load_estimate=0.4,
            activated_frames=("scarcity",),
        )
        l1 = MagicMock()
        l1.get.return_value = sig
        store = SimpleNamespace(_l1=l1, _l3=None)
        acc = make_priming_accessor(store)
        assert acc("h1") is sig

    def test_l3_hit_when_l1_miss(self):
        from adam.priming.signature import PagePrimingSignature
        sig = PagePrimingSignature(
            url_hash="h2", valence=0.0, arousal=0.5,
            regulatory_focus_priming="neutral",
            cognitive_load_estimate=0.5,
            activated_frames=(),
        )
        l1 = MagicMock()
        l1.get.return_value = None
        l3 = MagicMock()
        l3.get.return_value = sig.to_feature_store_row()
        store = SimpleNamespace(_l1=l1, _l3=l3)
        acc = make_priming_accessor(store)
        loaded = acc("h2")
        assert loaded.url_hash == "h2"
        assert loaded.regulatory_focus_priming == "neutral"

    def test_cold_miss_returns_neutral_signature(self):
        l1 = MagicMock()
        l1.get.return_value = None
        store = SimpleNamespace(_l1=l1, _l3=None)
        acc = make_priming_accessor(store)
        result = acc("cold_url_hash")
        assert result is not None
        assert result.url_hash == "cold_url_hash"

    def test_empty_url_hash_returns_none(self):
        store = SimpleNamespace(_l1=MagicMock(), _l3=None)
        acc = make_priming_accessor(store)
        assert acc("") is None

    def test_fail_soft_on_l1_exception(self):
        l1 = MagicMock()
        l1.get.side_effect = RuntimeError("LRU corrupted")
        store = SimpleNamespace(_l1=l1, _l3=None)
        acc = make_priming_accessor(store)
        assert acc("h") is None


# ---------------------------------------------------------------------------
# cascade_tier_accessor (lightweight adapter)
# ---------------------------------------------------------------------------

class TestCascadeTierAccessor:

    def test_high_blend_profile_returns_blend_compatible(self):
        # Per categorize_posture: conf >= 0.40 + posture <= -0.20 → blend
        cache = MagicMock()
        cache.lookup.return_value = SimpleNamespace(
            attentional_posture=-0.5,
            attentional_posture_confidence=0.7,
        )
        acc = make_cascade_tier_accessor(cache)
        assert acc("u", "h") == "blend_compatible"

    def test_high_vigilance_profile_returns_vigilance_activating(self):
        cache = MagicMock()
        cache.lookup.return_value = SimpleNamespace(
            attentional_posture=0.5,
            attentional_posture_confidence=0.7,
        )
        acc = make_cascade_tier_accessor(cache)
        assert acc("u", "h") == "vigilance_activating"

    def test_low_confidence_returns_unknown(self):
        cache = MagicMock()
        cache.lookup.return_value = SimpleNamespace(
            attentional_posture=0.5,
            attentional_posture_confidence=0.1,  # below 0.40 floor
        )
        acc = make_cascade_tier_accessor(cache)
        assert acc("u", "h") == "unknown"

    def test_no_profile_returns_none(self):
        cache = MagicMock()
        cache.lookup.return_value = None
        acc = make_cascade_tier_accessor(cache)
        assert acc("u", "h") is None

    def test_empty_url_hash_returns_none(self):
        cache = MagicMock()
        acc = make_cascade_tier_accessor(cache)
        assert acc("u", "") is None
        cache.lookup.assert_not_called()

    def test_fail_soft_on_cache_exception(self):
        cache = MagicMock()
        cache.lookup.side_effect = RuntimeError("Redis timeout")
        acc = make_cascade_tier_accessor(cache)
        assert acc("u", "h") is None


# ---------------------------------------------------------------------------
# journey_accessor (coordinator wrapper)
# ---------------------------------------------------------------------------

class TestJourneyAccessor:

    def test_unknown_buyer_returns_unaware(self):
        """Q23 sentinel: unknown buyer + sentinel category → cold-start
        UNAWARE per S6.2 default."""
        svc = SimpleNamespace(_journeys={})
        acc = make_journey_accessor(svc)
        assert acc("unknown_buyer") == ConversionStage.UNAWARE

    def test_known_buyer_returns_mapped_conversion_stage(self):
        from adam.user.journey.models import (
            JourneyStage, JourneyState, UserJourney,
        )
        # Populate the sentinel-keyed slot directly to simulate
        # populated journeys.
        state = JourneyState(
            user_id="buyer_x",
            category=JOURNEY_DEFAULT_CATEGORY,
            stage=JourneyStage.READY_TO_BUY,  # → "intending"
        )
        journey = UserJourney(
            user_id="buyer_x",
            category=JOURNEY_DEFAULT_CATEGORY,
            current_state=state,
        )
        svc = SimpleNamespace(_journeys={
            f"buyer_x:{JOURNEY_DEFAULT_CATEGORY}": journey,
        })
        acc = make_journey_accessor(svc)
        assert acc("buyer_x") == ConversionStage.INTENDING

    @pytest.mark.parametrize("stage_in,expected_stage_out", [
        # Sample of canonical 13-stage → 6-stage mapping per
        # to_conversion_stage at adam/user/journey/models.py:50-64
        ("UNAWARE", ConversionStage.UNAWARE),
        ("AWARE", ConversionStage.CURIOUS),
        ("CONSIDERING", ConversionStage.EVALUATING),
        ("DECIDING", ConversionStage.INTENDING),
        ("CHURNING", ConversionStage.STALLED),
        ("PURCHASED", ConversionStage.CONVERTED),
    ])
    def test_journey_stage_mapping_round_trip(
        self, stage_in, expected_stage_out,
    ):
        from adam.user.journey.models import (
            JourneyStage, JourneyState, UserJourney,
        )
        state = JourneyState(
            user_id="b", category=JOURNEY_DEFAULT_CATEGORY,
            stage=JourneyStage[stage_in],
        )
        journey = UserJourney(
            user_id="b", category=JOURNEY_DEFAULT_CATEGORY,
            current_state=state,
        )
        svc = SimpleNamespace(_journeys={
            f"b:{JOURNEY_DEFAULT_CATEGORY}": journey,
        })
        acc = make_journey_accessor(svc)
        assert acc("b") == expected_stage_out

    def test_empty_buyer_id_returns_unaware(self):
        svc = SimpleNamespace(_journeys={})
        acc = make_journey_accessor(svc)
        assert acc("") == ConversionStage.UNAWARE

    def test_fail_soft_on_service_exception(self):
        # Service object that raises when _journeys is accessed.
        class BrokenService:
            @property
            def _journeys(self):
                raise RuntimeError("dict access broken")
        acc = make_journey_accessor(BrokenService())
        assert acc("u") == ConversionStage.UNAWARE

    def test_custom_default_category(self):
        """Caller may override the sentinel for plumbing/test purposes."""
        from adam.user.journey.models import (
            JourneyStage, JourneyState, UserJourney,
        )
        state = JourneyState(
            user_id="b", category="custom_cat",
            stage=JourneyStage.AWARE,
        )
        journey = UserJourney(
            user_id="b", category="custom_cat",
            current_state=state,
        )
        svc = SimpleNamespace(_journeys={"b:custom_cat": journey})
        acc = make_journey_accessor(svc, default_category="custom_cat")
        assert acc("b") == ConversionStage.CURIOUS
