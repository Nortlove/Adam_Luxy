"""Pin Spine #13 Defensive Reasoning renderer (directive 386-402, 849-859).

Tests pin:
  * 5-layer render produces decision_id, one_liner, counterfactual,
    decomposition, confidence, provenance.
  * One-liner includes chosen_mechanism, posture_class when present,
    expected utility, runner-up phrase when alternatives present.
  * One-liner uses "neutral page posture" when posture_class is None.
  * Counterfactual present when alternatives non-empty; None otherwise.
  * Counterfactual references the top alternative + score gap.
  * Decomposition mirrors trace.chain_of_reasoning entries verbatim.
  * Confidence layer "available" when CI fields in user_posterior_snapshot;
    "not_available" when missing.
  * Provenance links built from user_id when present; None when not.
  * one_liner_uses_metaphor_inventory honest tag stays False
    (calibration-pending until Phase 6 line 1059 ships).
  * load_and_render integrates with Redis (preferred) and Neo4j
    (fallback) storage substrates.
  * load_and_render returns None when neither storage has the trace.
  * Render is JSON-serializable end-to-end.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import pytest

from adam.intelligence.decision_trace import (
    AlternativeCandidate,
    DecisionTrace,
    build_decision_trace,
)
from adam.intelligence.defensive_reasoning_renderer import (
    ConfidenceLayer,
    DefensiveReasoningRender,
    ProvenanceLayer,
    load_and_render,
    render_defensive_reasoning,
)


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------


def _trace_with_alternatives(
    decision_id: str = "dec-1",
    user_id: str = "user-7",
    posture_class: Optional[str] = "blend_compatible",
    user_posterior_snapshot: Optional[Dict[str, float]] = None,
) -> DecisionTrace:
    return build_decision_trace(
        decision_id=decision_id,
        user_id=user_id,
        chosen_creative_id="creative-a",
        chosen_mechanism="automatic_evaluation",
        chosen_score=0.71,
        score_components={
            "pragmatic": 0.5, "fluency": 0.15, "epistemic": 0.06,
        },
        alternatives=[
            AlternativeCandidate(
                creative_id="alt-1", mechanism="social_proof",
                posterior_score=0.62, propensity_under_TS=0.18,
            ),
            AlternativeCandidate(
                creative_id="alt-2", mechanism="authority",
                posterior_score=0.55, propensity_under_TS=0.10,
            ),
        ],
        posture_class=posture_class,
        posture_confidence=0.78 if posture_class else None,
        user_posterior_snapshot=user_posterior_snapshot or {"archetype": 1.0},
        timestamp=datetime(2026, 5, 1, 12, 0, 0, tzinfo=timezone.utc),
    )


def _trace_no_alternatives() -> DecisionTrace:
    return build_decision_trace(
        decision_id="dec-no-alt",
        user_id="user-9",
        chosen_creative_id="creative-x",
        chosen_mechanism="linguistic_framing",
        chosen_score=0.5,
        alternatives=[],  # empty
        timestamp=datetime(2026, 5, 1, 12, 0, 0, tzinfo=timezone.utc),
    )


# -----------------------------------------------------------------------------
# render_defensive_reasoning — layer-by-layer
# -----------------------------------------------------------------------------


def test_render_returns_decision_id():
    trace = _trace_with_alternatives()
    rendered = render_defensive_reasoning(trace)
    assert rendered.decision_id == trace.decision_id


def test_one_liner_includes_chosen_mechanism():
    trace = _trace_with_alternatives()
    rendered = render_defensive_reasoning(trace)
    assert "automatic_evaluation" in rendered.one_liner


def test_one_liner_includes_posture_class_when_available():
    trace = _trace_with_alternatives(posture_class="blend_compatible")
    rendered = render_defensive_reasoning(trace)
    assert "blend_compatible" in rendered.one_liner


def test_one_liner_uses_neutral_phrase_when_posture_missing():
    trace = _trace_with_alternatives(posture_class=None)
    rendered = render_defensive_reasoning(trace)
    assert "neutral page posture" in rendered.one_liner


def test_one_liner_includes_expected_utility():
    trace = _trace_with_alternatives()
    rendered = render_defensive_reasoning(trace)
    # chosen_score=0.71 → "0.710" in the formatted string
    assert "0.710" in rendered.one_liner


def test_one_liner_includes_runner_up_when_alternatives_present():
    trace = _trace_with_alternatives()
    rendered = render_defensive_reasoning(trace)
    # Top alternative has highest posterior_score (alt-1 at 0.62)
    assert "social_proof" in rendered.one_liner
    assert "0.620" in rendered.one_liner


def test_one_liner_omits_runner_up_when_no_alternatives():
    trace = _trace_no_alternatives()
    rendered = render_defensive_reasoning(trace)
    assert "runner-up" not in rendered.one_liner


def test_metaphor_inventory_flag_stays_false():
    """Honest tag: until Phase 6 metaphor inventory ships (directive
    line 1059), the one-liner uses raw mechanism names."""
    trace = _trace_with_alternatives()
    rendered = render_defensive_reasoning(trace)
    assert rendered.one_liner_uses_metaphor_inventory is False


# -----------------------------------------------------------------------------
# Counterfactual layer
# -----------------------------------------------------------------------------


def test_counterfactual_present_when_alternatives_exist():
    trace = _trace_with_alternatives()
    rendered = render_defensive_reasoning(trace)
    assert rendered.counterfactual is not None
    assert "social_proof" in rendered.counterfactual  # the top alt


def test_counterfactual_none_when_no_alternatives():
    trace = _trace_no_alternatives()
    rendered = render_defensive_reasoning(trace)
    assert rendered.counterfactual is None


def test_counterfactual_references_score_gap():
    """The counterfactual layer should describe how much the chosen
    mechanism beat the top alternative by."""
    trace = _trace_with_alternatives()
    rendered = render_defensive_reasoning(trace)
    # chosen=0.71, top_alt=0.62, gap=0.09
    assert "0.090" in rendered.counterfactual


def test_counterfactual_picks_top_alternative_not_first():
    """When alternatives are not sorted by score, renderer picks the
    one with highest posterior_score, not list-order first."""
    trace = build_decision_trace(
        decision_id="dec-unsorted",
        user_id="u",
        chosen_creative_id="c",
        chosen_mechanism="m",
        chosen_score=1.0,
        alternatives=[
            AlternativeCandidate(
                creative_id="low", mechanism="m_low",
                posterior_score=0.3, propensity_under_TS=0.1,
            ),
            AlternativeCandidate(
                creative_id="high", mechanism="m_high",
                posterior_score=0.8, propensity_under_TS=0.5,
            ),
        ],
    )
    rendered = render_defensive_reasoning(trace)
    assert "m_high" in rendered.counterfactual
    assert "m_low" not in rendered.counterfactual


# -----------------------------------------------------------------------------
# Decomposition layer
# -----------------------------------------------------------------------------


def test_decomposition_mirrors_chain_of_reasoning_entries():
    trace = _trace_with_alternatives()
    rendered = render_defensive_reasoning(trace)
    assert len(rendered.decomposition) == len(trace.chain_of_reasoning.entries)
    for rendered_e, trace_e in zip(
        rendered.decomposition, trace.chain_of_reasoning.entries,
    ):
        assert rendered_e.name == trace_e.name
        assert rendered_e.contribution == trace_e.contribution
        assert rendered_e.pct_of_total == trace_e.pct_of_total


def test_decomposition_empty_when_no_score_components():
    """A trace with no chain_of_reasoning entries → empty decomposition
    (not synthesized placeholder)."""
    trace = build_decision_trace(
        decision_id="dec-empty",
        user_id="u",
        chosen_creative_id="c",
        chosen_mechanism="m",
        chosen_score=0.5,
    )
    rendered = render_defensive_reasoning(trace)
    assert rendered.decomposition == []


# -----------------------------------------------------------------------------
# Confidence layer
# -----------------------------------------------------------------------------


def test_confidence_not_available_when_no_ci_data():
    trace = _trace_with_alternatives()  # snapshot has only "archetype" marker
    rendered = render_defensive_reasoning(trace)
    assert rendered.confidence.status == "not_available"
    assert rendered.confidence.ci_lower is None
    assert rendered.confidence.ci_upper is None


def test_confidence_available_when_ci_fields_present():
    trace = _trace_with_alternatives(
        user_posterior_snapshot={
            "ci_lower_90": 0.45,
            "ci_upper_90": 0.78,
            "point_estimate": 0.62,
            "cohort_pooled_estimate": 0.55,
        },
    )
    rendered = render_defensive_reasoning(trace)
    assert rendered.confidence.status == "available"
    assert rendered.confidence.ci_lower == pytest.approx(0.45)
    assert rendered.confidence.ci_upper == pytest.approx(0.78)
    assert rendered.confidence.ci_level == 0.90
    assert rendered.confidence.point_estimate == pytest.approx(0.62)
    assert rendered.confidence.cohort_pooled_estimate == pytest.approx(0.55)


def test_confidence_partial_data_still_available():
    """Some CI fields present without all 4 → still available status."""
    trace = _trace_with_alternatives(
        user_posterior_snapshot={"point_estimate": 0.62},
    )
    rendered = render_defensive_reasoning(trace)
    assert rendered.confidence.status == "available"
    assert rendered.confidence.point_estimate == pytest.approx(0.62)
    assert rendered.confidence.ci_lower is None


# -----------------------------------------------------------------------------
# Provenance layer
# -----------------------------------------------------------------------------


def test_provenance_links_built_from_user_id():
    trace = _trace_with_alternatives(user_id="user-42")
    rendered = render_defensive_reasoning(trace)
    assert rendered.provenance.user_history_link == (
        "/users/user-42/posterior_history"
    )
    assert "user-42" in rendered.provenance.cohort_state_link


def test_provenance_priors_link_when_archetype_marker_present():
    trace = _trace_with_alternatives(
        user_id="user-42",
        user_posterior_snapshot={"archetype": 1.0},
    )
    rendered = render_defensive_reasoning(trace)
    assert rendered.provenance.priors_link is not None
    assert "user-42" in rendered.provenance.priors_link


def test_provenance_links_none_when_no_user_id():
    trace = build_decision_trace(
        decision_id="dec-no-user",
        user_id="",
        chosen_creative_id="c",
        chosen_mechanism="m",
        chosen_score=0.5,
    )
    rendered = render_defensive_reasoning(trace)
    assert rendered.provenance.user_history_link is None
    assert rendered.provenance.cohort_state_link is None


def test_provenance_elicitation_link_stays_none():
    """Until Loop B 6-mode set ships, elicitation_link stays None.
    Honest tag: no fabricated link."""
    trace = _trace_with_alternatives()
    rendered = render_defensive_reasoning(trace)
    assert rendered.provenance.elicitation_link is None


# -----------------------------------------------------------------------------
# JSON round-trip
# -----------------------------------------------------------------------------


def test_render_serializes_to_json():
    trace = _trace_with_alternatives()
    rendered = render_defensive_reasoning(trace)
    blob = rendered.model_dump_json()
    parsed = json.loads(blob)
    assert parsed["decision_id"] == trace.decision_id
    assert "one_liner" in parsed
    assert "decomposition" in parsed
    assert "confidence" in parsed
    assert "provenance" in parsed


def test_render_round_trips_via_pydantic():
    trace = _trace_with_alternatives()
    rendered = render_defensive_reasoning(trace)
    blob = rendered.model_dump_json()
    rehydrated = DefensiveReasoningRender.model_validate_json(blob)
    assert rehydrated.decision_id == rendered.decision_id
    assert rehydrated.one_liner == rendered.one_liner
    assert len(rehydrated.decomposition) == len(rendered.decomposition)


# -----------------------------------------------------------------------------
# load_and_render — integration with storage substrates
# -----------------------------------------------------------------------------


class _FakeAsyncRedis:
    def __init__(self) -> None:
        self.kv: Dict[str, str] = {}
        self.lists: Dict[str, List[str]] = {}

    async def set(self, key: str, value: str, ex: Optional[int] = None) -> None:
        self.kv[key] = value

    async def get(self, key: str) -> Optional[str]:
        return self.kv.get(key)

    async def lpush(self, key: str, *values: Any) -> int:
        self.lists.setdefault(key, [])
        for v in values:
            self.lists[key].insert(0, str(v))
        return len(self.lists[key])

    async def ltrim(self, key: str, start: int, stop: int) -> None:
        if key in self.lists:
            self.lists[key] = self.lists[key][start: stop + 1]

    async def lrange(self, key: str, start: int, stop: int) -> List[str]:
        items = self.lists.get(key, [])
        if stop == -1:
            return items[start:]
        return items[start: stop + 1]

    async def expire(self, key: str, seconds: int) -> None:
        return None


class _FakeNeo4jSession:
    def __init__(self, traces: Dict[str, str]) -> None:
        self._traces = traces

    async def __aenter__(self) -> "_FakeNeo4jSession":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None

    async def run(self, cypher: str, **params: Any) -> Any:
        did = params.get("decision_id")
        payload = self._traces.get(did) if did else None

        class _R:
            async def single(self_inner) -> Any:
                if payload is None:
                    return None

                class _Rec:
                    def get(self_rec, key, default=None):
                        if key == "payload_json":
                            return payload
                        return default

                return _Rec()

            def __aiter__(self_inner):
                async def _g():
                    return
                    yield  # noqa
                return _g()

        return _R()


class _FakeAsyncNeo4jDriver:
    def __init__(self) -> None:
        self.traces: Dict[str, str] = {}

    def session(self) -> _FakeNeo4jSession:
        return _FakeNeo4jSession(self.traces)


async def test_load_and_render_via_redis():
    """Redis-only path: load_trace returns the trace; renderer runs."""
    from adam.intelligence.decision_trace_store import store_trace

    redis = _FakeAsyncRedis()
    trace = _trace_with_alternatives(decision_id="dec-redis")
    await store_trace(trace, redis)

    rendered = await load_and_render(
        "dec-redis", redis_client=redis, neo4j_driver=None,
    )
    assert rendered is not None
    assert rendered.decision_id == "dec-redis"
    assert rendered.counterfactual is not None


async def test_load_and_render_falls_back_to_neo4j():
    """Redis miss → fall back to Neo4j."""
    redis = _FakeAsyncRedis()  # empty
    neo4j = _FakeAsyncNeo4jDriver()
    trace = _trace_with_alternatives(decision_id="dec-neo4j")
    neo4j.traces["dec-neo4j"] = trace.model_dump_json()

    rendered = await load_and_render(
        "dec-neo4j", redis_client=redis, neo4j_driver=neo4j,
    )
    assert rendered is not None
    assert rendered.decision_id == "dec-neo4j"


async def test_load_and_render_returns_none_when_not_found():
    """Neither storage has the trace → None."""
    redis = _FakeAsyncRedis()
    neo4j = _FakeAsyncNeo4jDriver()
    rendered = await load_and_render(
        "never-stored", redis_client=redis, neo4j_driver=neo4j,
    )
    assert rendered is None


async def test_load_and_render_no_clients_returns_none():
    rendered = await load_and_render(
        "dec-x", redis_client=None, neo4j_driver=None,
    )
    assert rendered is None


async def test_load_and_render_redis_preferred_over_neo4j():
    """When BOTH have the trace, Redis is consulted first (hot path)."""
    from adam.intelligence.decision_trace_store import store_trace

    redis = _FakeAsyncRedis()
    neo4j = _FakeAsyncNeo4jDriver()

    redis_trace = _trace_with_alternatives(
        decision_id="dec-both", user_id="redis-user",
    )
    neo4j_trace = _trace_with_alternatives(
        decision_id="dec-both", user_id="neo4j-user",
    )

    await store_trace(redis_trace, redis)
    neo4j.traces["dec-both"] = neo4j_trace.model_dump_json()

    rendered = await load_and_render(
        "dec-both", redis_client=redis, neo4j_driver=neo4j,
    )
    # Redis path won → user_history_link uses redis_trace's user_id
    assert rendered is not None
    assert "redis-user" in rendered.provenance.user_history_link


# -----------------------------------------------------------------------------
# Sub-model schemas pinned
# -----------------------------------------------------------------------------


def test_confidence_layer_extra_forbidden():
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        ConfidenceLayer(unknown_field=1)  # type: ignore[call-arg]


def test_provenance_layer_extra_forbidden():
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        ProvenanceLayer(unknown_field="x")  # type: ignore[call-arg]


def test_render_extra_forbidden():
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        DefensiveReasoningRender(
            decision_id="d",
            one_liner="x",
            unknown_field=1,  # type: ignore[call-arg]
        )
