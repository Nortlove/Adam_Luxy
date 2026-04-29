"""Tests for Spine #11 — LUXY Negative-Outcome Adapter.

Pins per directive Section 2 (Spine #11):
    1. RawPixelEvent requires non-empty sapid (the join key is sacred)
    2. Classification priority: conversion > micro > censoring > click >
       view > non-viewable
    3. CLICK_BOUNCED on dwell < threshold OR explicit bounce flag
    4. CLICK_QUALIFIED on dwell ≥ threshold without bounce
    5. VIEWED_ENGAGED requires viewable + dwell + scroll all OK
    6. VIEWED_DISENGAGED for viewable but dwell or scroll insufficient
    7. IMPRESSION_NON_VIEWABLE for non-viewable views
    8. sapid round-trip linkage works (register → lookup → resolve)
    9. Unknown sapid returns None (round-trip failure handling)
   10. route_outcome_to_posterior calls Spine #1 BONG update with the
       registered feature vector
   11. CONVERSION updates posterior in positive direction; CLICK_BOUNCED
       updates in negative direction
   12. Non-viewable outcome leaves posterior natural params unchanged
"""

from __future__ import annotations

import pytest

from adam.intelligence.spine.spine_1_n_of_1_engine import (
    USER_POSTERIOR_DIM,
    init_user_posterior,
)
from adam.intelligence.spine.spine_11_negative_outcome_adapter import (
    DEFAULT_DWELL_BOUNCED_SECONDS,
    DEFAULT_DWELL_ENGAGED_SECONDS,
    DEFAULT_SCROLL_ENGAGED_FRACTION,
    OutcomeEvent,
    RawPixelEvent,
    build_outcome_event,
    classify_pixel_event,
    lookup_sapid,
    register_sapid_for_decision,
    reset_sapid_registry,
    route_outcome_to_posterior,
    sapid_registry_size,
)


@pytest.fixture(autouse=True)
def _reset_registry():
    reset_sapid_registry()
    yield
    reset_sapid_registry()


def _make_feature_vector(active_dim: int = 0, value: float = 1.0) -> list:
    """Helper: feature vector with a single non-zero dim."""
    x = [0.0] * USER_POSTERIOR_DIM
    x[active_dim] = value
    return x


# -----------------------------------------------------------------------------
# RawPixelEvent validation
# -----------------------------------------------------------------------------


class TestRawPixelEventValidation:

    def test_sapid_required(self):
        with pytest.raises(ValueError, match="sapid"):
            RawPixelEvent(sapid="", event_type="view")

    def test_whitespace_only_sapid_rejected(self):
        with pytest.raises(ValueError, match="sapid"):
            RawPixelEvent(sapid="   ", event_type="view")

    def test_valid_construction(self):
        e = RawPixelEvent(
            sapid="sa_abc123",
            event_type="view",
            dwell_seconds=10.0,
            scroll_fraction=0.5,
            viewable=True,
        )
        assert e.sapid == "sa_abc123"


# -----------------------------------------------------------------------------
# Classification — priority order
# -----------------------------------------------------------------------------


class TestClassificationPriority:

    def test_conversion_takes_priority_over_everything(self):
        e = RawPixelEvent(
            sapid="x", event_type="view",
            is_conversion=True,
            bounced=True,  # would otherwise mark as bounced
            dwell_seconds=0.1,
        )
        outcome, _ = classify_pixel_event(e)
        assert outcome == "CONVERSION"

    def test_micro_conversion_priority(self):
        e = RawPixelEvent(
            sapid="x", event_type="click",
            is_micro_conversion=True,
        )
        outcome, _ = classify_pixel_event(e)
        assert outcome == "MICRO_CONVERSION"

    def test_audience_aged_out_priority_over_click_or_view(self):
        e = RawPixelEvent(
            sapid="x", event_type="view",
            audience_aged_out=True,
            viewable=True, dwell_seconds=10.0,
        )
        outcome, _ = classify_pixel_event(e)
        assert outcome == "AUDIENCE_AGED_OUT"

    def test_frequency_cap_priority(self):
        e = RawPixelEvent(
            sapid="x", event_type="view",
            frequency_cap_fired=True,
        )
        outcome, _ = classify_pixel_event(e)
        assert outcome == "FREQUENCY_FATIGUE_FIRED"


class TestClassificationClick:

    def test_click_with_explicit_bounce(self):
        e = RawPixelEvent(
            sapid="x", event_type="click",
            bounced=True, dwell_seconds=10.0,  # dwell ignored when bounced
        )
        outcome, diag = classify_pixel_event(e)
        assert outcome == "CLICK_BOUNCED"
        assert "bounced" in diag["reason"]

    def test_click_short_dwell_is_bounce(self):
        """Click + dwell < threshold → CLICK_BOUNCED."""
        e = RawPixelEvent(
            sapid="x", event_type="click",
            dwell_seconds=DEFAULT_DWELL_BOUNCED_SECONDS - 0.1,
        )
        outcome, _ = classify_pixel_event(e)
        assert outcome == "CLICK_BOUNCED"

    def test_click_qualified_long_dwell(self):
        e = RawPixelEvent(
            sapid="x", event_type="click",
            dwell_seconds=DEFAULT_DWELL_ENGAGED_SECONDS + 5,
        )
        outcome, _ = classify_pixel_event(e)
        assert outcome == "CLICK_QUALIFIED"

    def test_click_no_dwell_signal_is_bounce(self):
        """Conservative: click with no dwell info → bounce."""
        e = RawPixelEvent(sapid="x", event_type="click")
        outcome, _ = classify_pixel_event(e)
        assert outcome == "CLICK_BOUNCED"


class TestClassificationView:

    def test_non_viewable_view(self):
        e = RawPixelEvent(
            sapid="x", event_type="view",
            viewable=False,
        )
        outcome, _ = classify_pixel_event(e)
        assert outcome == "IMPRESSION_NON_VIEWABLE"

    def test_viewable_engaged(self):
        e = RawPixelEvent(
            sapid="x", event_type="view",
            viewable=True,
            dwell_seconds=DEFAULT_DWELL_ENGAGED_SECONDS + 1,
            scroll_fraction=DEFAULT_SCROLL_ENGAGED_FRACTION + 0.1,
        )
        outcome, _ = classify_pixel_event(e)
        assert outcome == "VIEWED_ENGAGED"

    def test_viewable_disengaged_short_dwell(self):
        e = RawPixelEvent(
            sapid="x", event_type="view",
            viewable=True,
            dwell_seconds=1.0,  # below threshold
            scroll_fraction=0.5,
        )
        outcome, _ = classify_pixel_event(e)
        assert outcome == "VIEWED_DISENGAGED"

    def test_viewable_disengaged_low_scroll(self):
        e = RawPixelEvent(
            sapid="x", event_type="view",
            viewable=True,
            dwell_seconds=DEFAULT_DWELL_ENGAGED_SECONDS + 5,
            scroll_fraction=0.05,  # below threshold
        )
        outcome, _ = classify_pixel_event(e)
        assert outcome == "VIEWED_DISENGAGED"


class TestClassificationFallthrough:

    def test_unrecognized_event_type_conservative_non_viewable(self):
        e = RawPixelEvent(sapid="x", event_type="weird_event")
        outcome, _ = classify_pixel_event(e)
        assert outcome == "IMPRESSION_NON_VIEWABLE"


# -----------------------------------------------------------------------------
# sapid round-trip
# -----------------------------------------------------------------------------


class TestSapidRoundTrip:

    def test_register_and_lookup(self):
        x = _make_feature_vector(active_dim=3, value=2.5)
        register_sapid_for_decision(
            sapid="sa_abc",
            decision_id="d:1",
            user_id="u:1",
            feature_vector=x,
        )
        result = lookup_sapid("sa_abc")
        assert result is not None
        decision_id, user_id, fv = result
        assert decision_id == "d:1"
        assert user_id == "u:1"
        assert fv == x

    def test_lookup_unknown_returns_none(self):
        assert lookup_sapid("never_registered") is None

    def test_registry_size(self):
        assert sapid_registry_size() == 0
        for i in range(5):
            register_sapid_for_decision(
                sapid=f"sa_{i}", decision_id=f"d:{i}",
                user_id=f"u:{i}", feature_vector=_make_feature_vector(),
            )
        assert sapid_registry_size() == 5

    def test_reset_clears(self):
        register_sapid_for_decision(
            "sa_a", "d:a", "u:a", _make_feature_vector(),
        )
        assert sapid_registry_size() == 1
        reset_sapid_registry()
        assert sapid_registry_size() == 0


# -----------------------------------------------------------------------------
# build_outcome_event
# -----------------------------------------------------------------------------


class TestBuildOutcomeEvent:

    def test_known_sapid_resolves_to_outcome_event(self):
        register_sapid_for_decision(
            "sa_abc", "d:1", "u:1", _make_feature_vector(),
        )
        raw = RawPixelEvent(sapid="sa_abc", event_type="view",
                            is_conversion=True)
        outcome = build_outcome_event(raw)
        assert outcome is not None
        assert outcome.outcome_class == "CONVERSION"
        assert outcome.user_id == "u:1"
        assert outcome.decision_id == "d:1"

    def test_unknown_sapid_returns_none(self):
        raw = RawPixelEvent(sapid="never_registered", event_type="view")
        outcome = build_outcome_event(raw)
        assert outcome is None

    def test_diagnostic_carries_reason(self):
        register_sapid_for_decision(
            "sa_x", "d:x", "u:x", _make_feature_vector(),
        )
        raw = RawPixelEvent(
            sapid="sa_x", event_type="view",
            viewable=True, dwell_seconds=2.0, scroll_fraction=0.05,
        )
        outcome = build_outcome_event(raw)
        assert outcome is not None
        assert "reason" in outcome.classification_diagnostic
        assert outcome.classification_diagnostic["reason"]


# -----------------------------------------------------------------------------
# OutcomeEvent validation
# -----------------------------------------------------------------------------


class TestOutcomeEventValidation:

    def test_unknown_outcome_class_rejected(self):
        with pytest.raises(ValueError, match="not in known vocabulary"):
            OutcomeEvent(
                sapid="x", outcome_class="ARBITRARY",
                user_id="u", decision_id="d",
            )


# -----------------------------------------------------------------------------
# Routing to posterior — end-to-end
# -----------------------------------------------------------------------------


class TestRouteOutcomeToPosterior:

    def test_conversion_updates_posterior_positively(self):
        x = _make_feature_vector(active_dim=0, value=1.0)
        register_sapid_for_decision("sa_c", "d:c", "u:c", x)
        outcome = OutcomeEvent(
            sapid="sa_c", outcome_class="CONVERSION",
            user_id="u:c", decision_id="d:c",
        )
        p0 = init_user_posterior(user_id="u:c")
        p1 = route_outcome_to_posterior(outcome, p0)
        # CONVERSION: weight 1.0, sign +1 → η[0] grows
        assert p1.precision_weighted_mean[0] > p0.precision_weighted_mean[0]
        assert p1.total_observations == p0.total_observations + 1
        assert p1.last_outcome_class == "CONVERSION"

    def test_click_bounced_updates_posterior_negatively(self):
        x = _make_feature_vector(active_dim=0, value=1.0)
        register_sapid_for_decision("sa_b", "d:b", "u:b", x)
        outcome = OutcomeEvent(
            sapid="sa_b", outcome_class="CLICK_BOUNCED",
            user_id="u:b", decision_id="d:b",
        )
        p0 = init_user_posterior(user_id="u:b")
        p1 = route_outcome_to_posterior(outcome, p0)
        # CLICK_BOUNCED: weight 0.7, sign -1 → η[0] decreases
        assert p1.precision_weighted_mean[0] < p0.precision_weighted_mean[0]

    def test_non_viewable_leaves_natural_params_unchanged(self):
        x = _make_feature_vector(active_dim=0, value=1.0)
        register_sapid_for_decision("sa_n", "d:n", "u:n", x)
        outcome = OutcomeEvent(
            sapid="sa_n", outcome_class="IMPRESSION_NON_VIEWABLE",
            user_id="u:n", decision_id="d:n",
        )
        p0 = init_user_posterior(user_id="u:n")
        p1 = route_outcome_to_posterior(outcome, p0)
        # Non-viewable: weight 0; natural params unchanged.
        assert p1.precision_weighted_mean == p0.precision_weighted_mean
        assert p1.precision_matrix_flat == p0.precision_matrix_flat
        # But observation count + last_class still update.
        assert p1.total_observations == p0.total_observations + 1

    def test_route_without_registry_lookup_raises(self):
        outcome = OutcomeEvent(
            sapid="never_registered", outcome_class="CONVERSION",
            user_id="u", decision_id="d",
        )
        p0 = init_user_posterior(user_id="u")
        with pytest.raises(ValueError, match="not in registry"):
            route_outcome_to_posterior(outcome, p0)

    def test_explicit_feature_vector_overrides_registry_lookup(self):
        # Register one feature vector; pass a different one explicitly.
        register_sapid_for_decision(
            "sa_e", "d:e", "u:e", _make_feature_vector(active_dim=0),
        )
        outcome = OutcomeEvent(
            sapid="sa_e", outcome_class="CONVERSION",
            user_id="u:e", decision_id="d:e",
        )
        p0 = init_user_posterior(user_id="u:e")
        # Pass dim-5 active feature vector explicitly
        explicit_x = _make_feature_vector(active_dim=5, value=1.0)
        p1 = route_outcome_to_posterior(outcome, p0, feature_vector=explicit_x)
        # η[5] should grow, not η[0]
        assert p1.precision_weighted_mean[5] > 0
        assert p1.precision_weighted_mean[0] == 0


# -----------------------------------------------------------------------------
# End-to-end: pixel event → classified → routed → updated posterior
# -----------------------------------------------------------------------------


class TestEndToEndPipeline:

    def test_full_pipeline_view_engaged(self):
        # 1. Register sapid at decision time.
        x = _make_feature_vector(active_dim=2, value=0.7)
        register_sapid_for_decision("sa_full", "d:full", "u:full", x)

        # 2. Pixel event arrives back.
        raw = RawPixelEvent(
            sapid="sa_full", event_type="view",
            viewable=True,
            dwell_seconds=DEFAULT_DWELL_ENGAGED_SECONDS + 5,
            scroll_fraction=DEFAULT_SCROLL_ENGAGED_FRACTION + 0.1,
        )

        # 3. Classify + build OutcomeEvent.
        outcome = build_outcome_event(raw)
        assert outcome is not None
        assert outcome.outcome_class == "VIEWED_ENGAGED"

        # 4. Route to posterior.
        p0 = init_user_posterior(user_id="u:full")
        p1 = route_outcome_to_posterior(outcome, p0)

        # 5. Posterior shifted.
        # VIEWED_ENGAGED: weight 0.3, sign +1 → η[2] grows by 0.3·1·1·0.7 = 0.21
        assert p1.precision_weighted_mean[2] == pytest.approx(0.21)

    def test_full_pipeline_with_unknown_sapid_drops_event(self):
        raw = RawPixelEvent(
            sapid="never_registered", event_type="view",
            is_conversion=True,
        )
        outcome = build_outcome_event(raw)
        # Unknown sapid → None; the orchestrator's round-trip-failure
        # counter increments and the event is dropped.
        assert outcome is None
