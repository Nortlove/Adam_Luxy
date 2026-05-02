"""Pin Spine #6 producer — sync emit + async drain + cascade wiring.

Tests pin:
  * In-memory log: emit + drain round-trip preserves order;
    bounded capacity evicts oldest when full; thread-safe under
    concurrent emit; eviction counter increments.
  * Singleton: get_log returns same instance; reset_for_tests gives
    fresh log; emit() routes through singleton; soft-fail on log
    exception.
  * build_trace_from_cascade:
      - chosen_mechanism / chosen_score / user_id / archetype copied
      - chosen_creative_id placeholder uses mechanism_proxy: prefix
      - alternatives populated from mechanism_scores (excluding chosen)
      - alternatives count capped at max_alternatives
      - propensity_under_TS for each arm matches
        epsilon_floor_mix(pi_from_argmax_scores(scores))
      - chosen p_t passed through is consistent with
        epsilon_floor_mix on the chosen arm
      - Empty mechanism_scores → empty alternatives (no exception)
      - Cascade output without mechanism_scores attribute → no exception
  * drain_to_storage:
      - Drains pending traces; returns (n_drained, n_redis_ok, n_neo4j_ok)
      - Per-trace storage failure does NOT abort batch
      - No clients → drained but zero writes
      - Empty log → (0, 0, 0)
  * Cascade smoke: run_bilateral_cascade emits a trace into the log.
"""

from __future__ import annotations

import threading
from typing import Any, Dict, List, Optional
from unittest.mock import patch

import pytest

from adam.intelligence.decision_trace import DecisionTrace
from adam.intelligence.decision_trace_emitter import (
    DEFAULT_MAX_ALTERNATIVES,
    EPSILON_FLOOR,
    InMemoryDecisionTraceLog,
    build_trace_from_cascade,
    drain_to_storage,
    emit,
    get_log,
    reset_for_tests,
)
from adam.intelligence.mrt_logging import (
    epsilon_floor_mix,
    pi_from_argmax_scores,
)


def setup_function() -> None:
    reset_for_tests()


# -----------------------------------------------------------------------------
# Synthetic cascade output (mirrors CreativeIntelligence shape)
# -----------------------------------------------------------------------------


class _FakeCreativeIntelligence:
    """Minimal duck-typed cascade result for tests."""

    def __init__(
        self,
        mechanism_scores: Optional[Dict[str, float]] = None,
        primary_mechanism: str = "social_proof",
    ) -> None:
        self.mechanism_scores = dict(mechanism_scores or {})
        self.primary_mechanism = primary_mechanism


def _example_trace_dict() -> Dict[str, Any]:
    """Minimal kwargs for build_trace_from_cascade."""
    return {
        "decision_id": "dec-1",
        "user_id": "user-7",
        "archetype": "achiever",
        "category": "luxury",
        "cascade_result": _FakeCreativeIntelligence(
            mechanism_scores={
                "social_proof": 0.9,
                "authority": 0.6,
                "scarcity": 0.4,
                "reciprocity": 0.3,
            },
        ),
        "chosen_mechanism": "social_proof",
        "p_t": 0.985,  # close to 1 - ε + ε/4 = 0.985
    }


# -----------------------------------------------------------------------------
# InMemoryDecisionTraceLog
# -----------------------------------------------------------------------------


def test_log_emit_drain_round_trip_preserves_order():
    log = InMemoryDecisionTraceLog()
    traces = []
    for i in range(5):
        kw = _example_trace_dict()
        kw["decision_id"] = f"dec-{i}"
        traces.append(build_trace_from_cascade(**kw))
        log.emit(traces[-1])

    drained = log.drain(max_items=10)
    assert len(drained) == 5
    assert [t.decision_id for t in drained] == [
        f"dec-{i}" for i in range(5)
    ]
    assert len(log) == 0


def test_log_drain_respects_max_items():
    log = InMemoryDecisionTraceLog()
    for i in range(7):
        kw = _example_trace_dict()
        kw["decision_id"] = f"dec-{i}"
        log.emit(build_trace_from_cascade(**kw))
    first = log.drain(max_items=3)
    assert len(first) == 3
    assert len(log) == 4
    rest = log.drain(max_items=100)
    assert len(rest) == 4
    assert len(log) == 0


def test_log_capacity_evicts_oldest():
    """Bounded deque: when full, oldest is evicted on emit."""
    log = InMemoryDecisionTraceLog(capacity=3)
    for i in range(5):
        kw = _example_trace_dict()
        kw["decision_id"] = f"dec-{i}"
        log.emit(build_trace_from_cascade(**kw))
    assert len(log) == 3
    # Eviction counter incremented for the 2 evictions
    assert log.evictions == 2
    drained = log.drain(max_items=10)
    assert [t.decision_id for t in drained] == ["dec-2", "dec-3", "dec-4"]


def test_log_thread_safe_under_concurrent_emit():
    log = InMemoryDecisionTraceLog(capacity=10_000)
    n_threads = 8
    n_per_thread = 50

    def _worker(start: int) -> None:
        for i in range(n_per_thread):
            kw = _example_trace_dict()
            kw["decision_id"] = f"dec-t{start}-{i}"
            log.emit(build_trace_from_cascade(**kw))

    threads = [
        threading.Thread(target=_worker, args=(t,))
        for t in range(n_threads)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(log) == n_threads * n_per_thread
    drained = log.drain(max_items=100_000)
    # No duplicates lost / corrupted
    decision_ids = {t.decision_id for t in drained}
    assert len(decision_ids) == n_threads * n_per_thread


# -----------------------------------------------------------------------------
# Singleton
# -----------------------------------------------------------------------------


def test_singleton_returns_same_log():
    log_a = get_log()
    log_b = get_log()
    assert log_a is log_b


def test_reset_for_tests_gives_fresh_log():
    log_a = get_log()
    kw = _example_trace_dict()
    log_a.emit(build_trace_from_cascade(**kw))
    assert len(log_a) == 1

    reset_for_tests()
    log_b = get_log()
    assert log_b is not log_a
    assert len(log_b) == 0


def test_emit_routes_through_singleton():
    kw = _example_trace_dict()
    trace = build_trace_from_cascade(**kw)
    emit(trace)
    assert len(get_log()) == 1


def test_emit_soft_fails_on_log_exception():
    """A broken log singleton must not crash the cascade."""
    class _Broken:
        def emit(self, _trace: DecisionTrace) -> None:
            raise RuntimeError("simulated log failure")
    reset_for_tests(log=_Broken())  # type: ignore[arg-type]
    kw = _example_trace_dict()
    trace = build_trace_from_cascade(**kw)
    # Must not raise
    emit(trace)


# -----------------------------------------------------------------------------
# build_trace_from_cascade — propensity + shape correctness
# -----------------------------------------------------------------------------


def test_builder_copies_chosen_fields():
    kw = _example_trace_dict()
    trace = build_trace_from_cascade(**kw)
    assert trace.decision_id == "dec-1"
    assert trace.user_id == "user-7"
    assert trace.chosen_mechanism == "social_proof"
    assert trace.chosen_score == 0.9
    assert trace.chosen_creative_id == "mechanism_proxy:social_proof"


def test_builder_alternatives_count_capped():
    kw = _example_trace_dict()
    # 7 mechanisms total; chosen 1 + 6 alternatives — cap at default 5
    kw["cascade_result"] = _FakeCreativeIntelligence(
        mechanism_scores={
            "social_proof": 0.9, "authority": 0.8, "scarcity": 0.7,
            "reciprocity": 0.6, "consistency": 0.5, "liking": 0.4,
            "unity": 0.3,
        },
    )
    trace = build_trace_from_cascade(**kw)
    assert len(trace.alternatives) == DEFAULT_MAX_ALTERNATIVES
    # Sorted by score descending (excluding chosen)
    alt_scores = [alt.posterior_score for alt in trace.alternatives]
    assert alt_scores == sorted(alt_scores, reverse=True)


def test_builder_alternatives_excludes_chosen():
    kw = _example_trace_dict()
    trace = build_trace_from_cascade(**kw)
    alt_mechs = {alt.mechanism for alt in trace.alternatives}
    assert "social_proof" not in alt_mechs
    assert alt_mechs == {"authority", "scarcity", "reciprocity"}


def test_builder_alternative_propensities_match_epsilon_floor_mix():
    """Each alternative's propensity_under_TS must equal the
    epsilon_floor_mix(pi_from_argmax_scores) value for that arm."""
    kw = _example_trace_dict()
    scores = kw["cascade_result"].mechanism_scores
    expected_p_t = epsilon_floor_mix(
        pi_from_argmax_scores(scores), epsilon=EPSILON_FLOOR,
    )
    trace = build_trace_from_cascade(**kw)
    for alt in trace.alternatives:
        assert alt.propensity_under_TS == pytest.approx(
            expected_p_t[alt.mechanism], abs=1e-9,
        ), (
            f"alternative {alt.mechanism!r} propensity "
            f"{alt.propensity_under_TS} != expected "
            f"{expected_p_t[alt.mechanism]}"
        )


def test_builder_alternative_propensity_creative_proxy_prefix():
    kw = _example_trace_dict()
    trace = build_trace_from_cascade(**kw)
    for alt in trace.alternatives:
        assert alt.creative_id.startswith("mechanism_proxy:")


def test_builder_handles_empty_mechanism_scores():
    """No mechanism_scores → no alternatives, no exception."""
    kw = _example_trace_dict()
    kw["cascade_result"] = _FakeCreativeIntelligence(mechanism_scores={})
    trace = build_trace_from_cascade(**kw)
    assert trace.alternatives == []
    assert trace.chosen_mechanism == "social_proof"
    assert trace.chosen_score == 0.0  # not in empty scores


def test_builder_handles_missing_mechanism_scores_attribute():
    """Cascade result without mechanism_scores at all → no exception,
    empty alternatives."""
    class _Bare:
        pass
    kw = _example_trace_dict()
    kw["cascade_result"] = _Bare()
    trace = build_trace_from_cascade(**kw)
    assert trace.alternatives == []


def test_builder_propagates_posture_fields_when_provided():
    kw = _example_trace_dict()
    kw["page_posture_vector"] = [0.1, 0.2, -0.3]
    kw["posture_class"] = "blend_compatible"
    kw["posture_confidence"] = 0.78
    trace = build_trace_from_cascade(**kw)
    assert trace.page_posture_vector == [0.1, 0.2, -0.3]
    assert trace.posture_class == "blend_compatible"
    assert trace.posture_confidence == 0.78


def test_builder_max_alternatives_override():
    """max_alternatives parameter overrides the default cap."""
    kw = _example_trace_dict()
    kw["max_alternatives"] = 2
    trace = build_trace_from_cascade(**kw)
    assert len(trace.alternatives) == 2


# -----------------------------------------------------------------------------
# build_trace_from_cascade — confidence_snapshot merge (Slice 1)
# -----------------------------------------------------------------------------


def test_builder_merges_confidence_snapshot_into_user_posterior_snapshot():
    """confidence_snapshot keys flow into user_posterior_snapshot for the
    DR renderer (defensive_reasoning_renderer._render_confidence)."""
    kw = _example_trace_dict()
    kw["confidence_snapshot"] = {
        "point_estimate": 0.62,
        "ci_lower_90": 0.45,
        "ci_upper_90": 0.79,
    }
    trace = build_trace_from_cascade(**kw)
    snap = trace.user_posterior_snapshot
    assert snap["point_estimate"] == pytest.approx(0.62)
    assert snap["ci_lower_90"] == pytest.approx(0.45)
    assert snap["ci_upper_90"] == pytest.approx(0.79)
    # Archetype presence marker is preserved alongside.
    assert snap.get("archetype") == 1.0


def test_builder_preserves_snapshot_when_confidence_snapshot_omitted():
    """No confidence_snapshot → no CI keys added; existing surface
    (status="not_available" in renderer) preserved."""
    kw = _example_trace_dict()
    trace = build_trace_from_cascade(**kw)
    snap = trace.user_posterior_snapshot
    assert "ci_lower_90" not in snap
    assert "ci_upper_90" not in snap
    assert "point_estimate" not in snap


def test_builder_skips_non_numeric_snapshot_values():
    """Soft-fail: malformed values are skipped, not raised."""
    kw = _example_trace_dict()
    kw["confidence_snapshot"] = {
        "point_estimate": 0.5,
        "ci_lower_90": "not a number",
        "ci_upper_90": None,
    }
    trace = build_trace_from_cascade(**kw)
    snap = trace.user_posterior_snapshot
    assert snap["point_estimate"] == pytest.approx(0.5)
    assert "ci_lower_90" not in snap
    assert "ci_upper_90" not in snap


def test_builder_handles_empty_confidence_snapshot_dict():
    """Empty dict → no merge, no exception, archetype preserved."""
    kw = _example_trace_dict()
    kw["confidence_snapshot"] = {}
    trace = build_trace_from_cascade(**kw)
    assert "ci_lower_90" not in trace.user_posterior_snapshot
    assert trace.user_posterior_snapshot.get("archetype") == 1.0


def test_builder_handles_none_confidence_snapshot():
    """None (default) → no merge, no exception."""
    kw = _example_trace_dict()
    kw["confidence_snapshot"] = None
    trace = build_trace_from_cascade(**kw)
    assert "ci_lower_90" not in trace.user_posterior_snapshot


# -----------------------------------------------------------------------------
# build_trace_from_cascade — bid-composer wiring (Slice 2)
# -----------------------------------------------------------------------------


def test_builder_no_bong_or_posture_leaves_alternatives_unchanged():
    """Without bong_posterior + posture_class, AlternativeCandidate
    bid slots stay None (composer skipped)."""
    kw = _example_trace_dict()
    trace = build_trace_from_cascade(**kw)
    for alt in trace.alternatives:
        assert alt.fluency_score is None
        assert alt.mechanism_compatibility_score is None
        assert alt.epistemic_bonus is None
        assert alt.bid_value is None
    assert trace.bid_value is None


def test_builder_only_bong_no_posture_skips_composer():
    """Posture missing → composer skipped (the soft gate is on both
    inputs)."""
    kw = _example_trace_dict()
    kw["bong_posterior"] = "any_value"  # not None
    # posture_class stays None
    trace = build_trace_from_cascade(**kw)
    for alt in trace.alternatives:
        assert alt.fluency_score is None


def test_builder_only_posture_no_bong_skips_composer():
    """BONG missing → composer skipped (mirror condition)."""
    kw = _example_trace_dict()
    kw["posture_class"] = "POSTURE_BLEND"
    trace = build_trace_from_cascade(**kw)
    for alt in trace.alternatives:
        assert alt.fluency_score is None


def test_builder_with_bong_and_posture_invokes_composer():
    """When both are present, composer populates per-alternative slots
    (verified via fluency_score being non-None)."""
    from unittest.mock import patch

    import numpy as np

    from adam.intelligence.page_attentional_posture_substrate import POSTURE_BLEND

    class _FakeUpdater:
        def __init__(self) -> None:
            # social_proof maps to ['social_proof_sensitivity', 'mimetic_desire']
            self.dimension_names = [
                "social_proof_sensitivity", "mimetic_desire",
            ]
            self.prior_eta = np.zeros(2)

        def get_mean(self, _ind: object) -> np.ndarray:
            return np.array([0.6, 0.4])

        def get_per_dimension_variance(self, _ind: object) -> np.ndarray:
            return np.array([0.04, 0.04])

    kw = _example_trace_dict()
    kw["bong_posterior"] = object()  # opaque marker; fake updater ignores
    kw["posture_class"] = POSTURE_BLEND

    with patch(
        "adam.intelligence.bong.get_bong_updater",
        return_value=_FakeUpdater(),
    ):
        trace = build_trace_from_cascade(**kw)

    # Every alternative gets a fluency_score (= compatibility_prior)
    # for its mechanism × posture pair.
    assert all(
        alt.fluency_score is not None for alt in trace.alternatives
    )
    # The chosen mechanism's bid_value at the trace level is populated.
    assert trace.bid_value is not None


# -----------------------------------------------------------------------------
# drain_to_storage
# -----------------------------------------------------------------------------


class _FakeAsyncRedis:
    def __init__(self) -> None:
        self.kv: Dict[str, str] = {}
        self.lists: Dict[str, List[str]] = {}
        self.fail_set: bool = False

    async def set(self, key: str, value: str, ex: Optional[int] = None) -> None:
        if self.fail_set:
            raise RuntimeError("simulated set failure")
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


class _FakeAsyncSession:
    def __init__(self, driver: "_FakeAsyncNeo4j") -> None:
        self._driver = driver

    async def __aenter__(self) -> "_FakeAsyncSession":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None

    async def run(self, cypher: str, **params: Any) -> Any:
        if self._driver.fail_run:
            raise RuntimeError("simulated cypher failure")
        # Just record the call; no result needed for archive
        self._driver.calls.append((cypher, dict(params)))

        class _R:
            async def single(self_inner) -> None:
                return None

            def __aiter__(self_inner):
                async def _g():
                    return
                    yield  # noqa
                return _g()

        return _R()


class _FakeAsyncNeo4j:
    def __init__(self) -> None:
        self.calls: List = []
        self.fail_run: bool = False

    def session(self) -> _FakeAsyncSession:
        return _FakeAsyncSession(self)


async def test_drain_writes_to_redis_and_neo4j():
    reset_for_tests()
    for i in range(3):
        kw = _example_trace_dict()
        kw["decision_id"] = f"dec-{i}"
        emit(build_trace_from_cascade(**kw))

    redis = _FakeAsyncRedis()
    neo4j = _FakeAsyncNeo4j()
    drained, n_redis, n_neo4j = await drain_to_storage(
        redis_client=redis, neo4j_driver=neo4j,
    )
    assert drained == 3
    assert n_redis == 3
    assert n_neo4j == 3
    assert len(get_log()) == 0


async def test_drain_per_trace_redis_failure_does_not_abort_batch():
    reset_for_tests()
    for i in range(3):
        kw = _example_trace_dict()
        kw["decision_id"] = f"dec-{i}"
        emit(build_trace_from_cascade(**kw))

    redis = _FakeAsyncRedis()
    redis.fail_set = True  # every set raises
    neo4j = _FakeAsyncNeo4j()
    drained, n_redis, n_neo4j = await drain_to_storage(
        redis_client=redis, neo4j_driver=neo4j,
    )
    assert drained == 3
    assert n_redis == 0  # all Redis writes failed
    assert n_neo4j == 3  # Neo4j writes still succeeded


async def test_drain_no_clients_returns_zero_writes():
    reset_for_tests()
    kw = _example_trace_dict()
    emit(build_trace_from_cascade(**kw))
    drained, n_redis, n_neo4j = await drain_to_storage(
        redis_client=None, neo4j_driver=None,
    )
    assert drained == 1
    assert n_redis == 0
    assert n_neo4j == 0


async def test_drain_empty_log_returns_zero():
    reset_for_tests()
    drained, n_redis, n_neo4j = await drain_to_storage(
        redis_client=_FakeAsyncRedis(), neo4j_driver=_FakeAsyncNeo4j(),
    )
    assert (drained, n_redis, n_neo4j) == (0, 0, 0)


async def test_drain_max_items_caps_batch():
    reset_for_tests()
    for i in range(10):
        kw = _example_trace_dict()
        kw["decision_id"] = f"dec-{i}"
        emit(build_trace_from_cascade(**kw))
    drained, _, _ = await drain_to_storage(
        redis_client=_FakeAsyncRedis(),
        neo4j_driver=_FakeAsyncNeo4j(),
        max_items=4,
    )
    assert drained == 4
    # 6 traces remain in the log
    assert len(get_log()) == 6


# -----------------------------------------------------------------------------
# Cascade smoke — verify run_bilateral_cascade emits a trace
# -----------------------------------------------------------------------------


def test_run_bilateral_cascade_emits_decision_trace():
    """Smoke test: a cascade run with a buyer_id produces a trace
    in the in-memory log. The exact trace contents depend on cascade
    internals; we pin only that emission HAPPENED (one new trace)."""
    reset_for_tests()
    pre_count = len(get_log())

    from adam.api.stackadapt.bilateral_cascade import run_bilateral_cascade
    # Use a synthetic-archetype segment_id; the cascade returns a
    # CreativeIntelligence. Page url omitted, atom outputs not needed
    # for the L1/L2 fast path.
    result = run_bilateral_cascade(
        segment_id="informativ_achiever_t1",
        buyer_id="user-cascade-test",
    )
    assert result is not None

    post_count = len(get_log())
    assert post_count == pre_count + 1, (
        f"expected exactly 1 new trace emitted; "
        f"pre={pre_count} post={post_count}"
    )


def test_run_bilateral_cascade_emitted_trace_has_correct_user_id():
    reset_for_tests()
    from adam.api.stackadapt.bilateral_cascade import run_bilateral_cascade
    run_bilateral_cascade(
        segment_id="informativ_achiever_t1",
        buyer_id="user-cascade-test",
    )
    drained = get_log().drain(max_items=10)
    assert len(drained) == 1
    assert drained[0].user_id == "user-cascade-test"
    # Decision id includes the buyer_id slug per the wiring contract
    assert "user-cascade-test" in drained[0].decision_id


# -----------------------------------------------------------------------------
# Cascade smoke — Slice 5 posture wiring
# -----------------------------------------------------------------------------


def test_cascade_emits_trace_with_posture_when_page_profile_present():
    """Slice 5: when page_url resolves to a page_profile with non-zero
    attentional_posture_confidence, the emitted trace carries
    posture_class / posture_confidence / page_posture_vector."""
    reset_for_tests()

    from adam.intelligence.page_intelligence import PagePsychologicalProfile

    profile = PagePsychologicalProfile()
    profile.attentional_posture = -0.7  # blend
    profile.attentional_posture_confidence = 0.85  # above MIN_POSTURE_CONFIDENCE

    class _FakeCache:
        def lookup(self, _url: str):
            return profile

    from adam.api.stackadapt.bilateral_cascade import run_bilateral_cascade

    with patch(
        "adam.intelligence.page_intelligence.get_page_intelligence_cache",
        return_value=_FakeCache(),
    ):
        run_bilateral_cascade(
            segment_id="informativ_achiever_t1",
            buyer_id="user-posture-test",
            page_url="https://example.com/article",
        )

    drained = get_log().drain(max_items=10)
    assert len(drained) == 1
    trace = drained[0]
    # Posture wired through to the trace
    assert trace.posture_class == "blend_compatible"
    assert trace.posture_confidence == pytest.approx(0.85)
    assert trace.page_posture_vector == [pytest.approx(-0.7)]


def test_cascade_emits_trace_without_posture_when_no_page_url():
    """No page_url → posture lookup skipped → trace fields stay None."""
    reset_for_tests()
    from adam.api.stackadapt.bilateral_cascade import run_bilateral_cascade
    run_bilateral_cascade(
        segment_id="informativ_achiever_t1",
        buyer_id="user-no-posture",
        # no page_url
    )
    drained = get_log().drain(max_items=10)
    assert len(drained) == 1
    trace = drained[0]
    assert trace.posture_class is None
    assert trace.posture_confidence is None
    assert trace.page_posture_vector is None


# -----------------------------------------------------------------------------
# Slice C — resolved_creative_id kwarg on build_trace_from_cascade
# -----------------------------------------------------------------------------


def test_builder_uses_resolved_creative_id_when_provided():
    """When the cascade's Slice C lookup hit the manifest, the resolved
    stackadapt_creative_id replaces the mechanism_proxy placeholder."""
    kw = _example_trace_dict()
    kw["resolved_creative_id"] = "sa-creative-real-42"
    trace = build_trace_from_cascade(**kw)
    assert trace.chosen_creative_id == "sa-creative-real-42"
    # Sanity — the placeholder prefix is NOT used.
    assert "mechanism_proxy:" not in trace.chosen_creative_id


def test_builder_falls_back_to_placeholder_when_resolved_is_none():
    """No manifest hit → resolved_creative_id=None → placeholder stays."""
    kw = _example_trace_dict()
    kw["resolved_creative_id"] = None
    trace = build_trace_from_cascade(**kw)
    assert trace.chosen_creative_id == "mechanism_proxy:social_proof"


def test_builder_falls_back_to_placeholder_when_resolved_omitted():
    """Default behavior unchanged when caller doesn't pass the kwarg."""
    kw = _example_trace_dict()
    # No resolved_creative_id key at all.
    trace = build_trace_from_cascade(**kw)
    assert trace.chosen_creative_id == "mechanism_proxy:social_proof"


def test_builder_resolved_id_does_not_change_alternatives():
    """Slice C resolves only the chosen creative; alternatives keep
    placeholder ids by design (per-alternative resolution is sibling)."""
    kw = _example_trace_dict()
    kw["resolved_creative_id"] = "sa-creative-real-42"
    trace = build_trace_from_cascade(**kw)
    for alt in trace.alternatives:
        assert alt.creative_id.startswith("mechanism_proxy:")


def test_builder_empty_string_resolved_id_treated_as_no_resolution():
    """Empty string is falsy → builder falls back to placeholder.
    Defensive against accidental empty-string injection from a soft-
    failing lookup."""
    kw = _example_trace_dict()
    kw["resolved_creative_id"] = ""
    trace = build_trace_from_cascade(**kw)
    assert trace.chosen_creative_id == "mechanism_proxy:social_proof"


def test_cascade_emits_trace_without_posture_when_low_confidence():
    """page_profile with confidence=0 (no evidence) → posture skipped."""
    reset_for_tests()

    from adam.intelligence.page_intelligence import PagePsychologicalProfile

    profile = PagePsychologicalProfile()
    profile.attentional_posture = 0.0
    profile.attentional_posture_confidence = 0.0

    class _FakeCache:
        def lookup(self, _url: str):
            return profile

    from adam.api.stackadapt.bilateral_cascade import run_bilateral_cascade

    with patch(
        "adam.intelligence.page_intelligence.get_page_intelligence_cache",
        return_value=_FakeCache(),
    ):
        run_bilateral_cascade(
            segment_id="informativ_achiever_t1",
            buyer_id="user-zero-conf",
            page_url="https://example.com/article",
        )

    drained = get_log().drain(max_items=10)
    assert len(drained) == 1
    trace = drained[0]
    assert trace.posture_class is None
    assert trace.posture_confidence is None
    assert trace.page_posture_vector is None
