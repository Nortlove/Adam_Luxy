"""Pin Slice 9 — LUXY goal-state inventory (Spine #5 substrate).

Discipline anchors (B3-LUXY a/b/c/d) for
``adam/intelligence/goal_state_inventory.py``:

    (a) Citations: directive Phase 6 line 1059; Spine #5 line 216
        ("12-15 active goal states") + line 793 (LUXY-specific
        examples). Names follow the directive verbatim where given.

    (b) Boundary anchors pinned by these tests:
          - inventory size in [12, 15] (directive band)
          - directive-named goal states all present
          - every state has all required attributes
          - mechanism_priors keys are in MECHANISM_TAXONOMY
          - posture_compatibility keys are recognized postures
          - primary_metaphor is one of LUXY's 5
          - keyword list non-empty per state
          - posture / mechanism values in [0, 1]
          - lookup helpers idempotent
          - posture-filter helper returns expected subsets
          - metaphor-filter helper returns expected subsets
          - Pydantic round-trip preserves all fields
          - validators reject malformed inputs

    (c) calibration_pending=True. All numeric values are conservative
        defaults; A14 flag PHASE_6_GOAL_STATE_INVENTORY_PRIORS_PILOT_PENDING.

    (d) Honest tags — what is NOT tested here (named successors):
          - Generative model q(goal_state | a, s, c) (Spine #5)
          - Free-energy decomposition (Spine #5)
          - Empirical recalibration of priors (sibling)
          - Cross-vertical generalization (sibling)
          - Neo4j writeback (sibling)
"""

from __future__ import annotations

import pytest

from adam.intelligence.goal_state_inventory import (
    GoalState,
    LUXYPrimaryMetaphor,
    get_goal_state,
    goal_state_ids,
    goal_states_for_posture,
    goal_states_with_metaphor,
    list_goal_states,
)
from adam.intelligence.mechanism_taxonomy import MECHANISM_TAXONOMY
from adam.intelligence.page_attentional_posture_substrate import (
    POSTURE_BLEND,
    POSTURE_NEUTRAL,
    POSTURE_VIGILANCE,
)


# Directive-named goal states (line 216 + line 793)
_DIRECTIVE_NAMED_STATES = {
    "commute_readiness",
    "expense_management",
    "comparative_research",
    "social_positioning",
    "status_display",
    "time_pressure",
    "time_recovery",
    "trip_planning",
    "professional_encounter_preparation",
    "anxiety_reduction",
}


# -----------------------------------------------------------------------------
# Inventory size + directive coverage
# -----------------------------------------------------------------------------


def test_inventory_size_in_directive_band():
    """Directive Spine #5 line 216: '~12-15 active goal states'."""
    states = list_goal_states()
    assert 12 <= len(states) <= 15, (
        f"directive Spine #5 line 216 specifies ~12-15 goal states; "
        f"got {len(states)}"
    )


def test_directive_named_states_all_present():
    """Every directive-named goal state in the inventory."""
    actual_ids = set(goal_state_ids())
    missing = _DIRECTIVE_NAMED_STATES - actual_ids
    assert not missing, f"directive-named states missing: {missing}"


def test_inventory_ids_unique():
    ids = goal_state_ids()
    assert len(ids) == len(set(ids))


def test_inventory_ids_sorted():
    """list_goal_states / goal_state_ids return deterministic order."""
    ids_a = goal_state_ids()
    ids_b = [g.id for g in list_goal_states()]
    assert ids_a == sorted(ids_a)
    assert ids_a == ids_b


# -----------------------------------------------------------------------------
# Per-state schema correctness
# -----------------------------------------------------------------------------


@pytest.mark.parametrize("state", list_goal_states(), ids=lambda s: s.id)
class TestPerStateSchema:

    def test_required_fields_populated(self, state):
        assert state.id
        assert state.name
        assert state.description

    def test_keywords_non_empty(self, state):
        """Every state has at least 3 keywords (priors for Spine #5
        generative-model trainer)."""
        assert len(state.keywords) >= 3

    def test_posture_compatibility_keys_recognized(self, state):
        for key in state.posture_compatibility.keys():
            assert key in {POSTURE_BLEND, POSTURE_NEUTRAL, POSTURE_VIGILANCE}

    def test_posture_values_in_unit_range(self, state):
        for value in state.posture_compatibility.values():
            assert 0.0 <= value <= 1.0

    def test_mechanism_priors_keys_in_taxonomy(self, state):
        for key in state.mechanism_priors.keys():
            assert key in MECHANISM_TAXONOMY

    def test_mechanism_priors_values_in_unit_range(self, state):
        for value in state.mechanism_priors.values():
            assert 0.0 <= value <= 1.0

    def test_primary_metaphor_in_luxy_inventory(self, state):
        assert state.primary_metaphor in {
            LUXYPrimaryMetaphor.CONTAINMENT,
            LUXYPrimaryMetaphor.RELIABILITY_AS_WEIGHT,
            LUXYPrimaryMetaphor.FORWARD_MOTION,
            LUXYPrimaryMetaphor.STATUS_AS_VERTICALITY,
            LUXYPrimaryMetaphor.TIME_AS_RESOURCE,
        }


# -----------------------------------------------------------------------------
# Lookup helpers
# -----------------------------------------------------------------------------


def test_get_goal_state_returns_canonical():
    state = get_goal_state("commute_readiness")
    assert state is not None
    assert state.id == "commute_readiness"


def test_get_goal_state_unknown_returns_none():
    assert get_goal_state("not_a_real_goal") is None


def test_get_goal_state_idempotent():
    """Two consecutive lookups return the same instance."""
    a = get_goal_state("anxiety_reduction")
    b = get_goal_state("anxiety_reduction")
    assert a is b


# -----------------------------------------------------------------------------
# Filter helpers
# -----------------------------------------------------------------------------


def test_goal_states_for_blend_posture_includes_anxiety_reduction():
    """anxiety_reduction has posture_compatibility[BLEND]=0.7 — should pass
    the default 0.5 threshold."""
    blend_compatible = goal_states_for_posture(POSTURE_BLEND)
    ids = {g.id for g in blend_compatible}
    assert "anxiety_reduction" in ids


def test_goal_states_for_vigilance_posture_includes_comparative_research():
    """comparative_research is research-mode → POSTURE_VIGILANCE strong."""
    vigilance_compatible = goal_states_for_posture(POSTURE_VIGILANCE)
    ids = {g.id for g in vigilance_compatible}
    assert "comparative_research" in ids
    assert "time_pressure" in ids


def test_goal_states_for_posture_threshold_filters():
    """Higher threshold → fewer states pass."""
    low_threshold = goal_states_for_posture(POSTURE_BLEND, threshold=0.0)
    high_threshold = goal_states_for_posture(POSTURE_BLEND, threshold=0.95)
    assert len(low_threshold) >= len(high_threshold)


def test_goal_states_for_unknown_posture_returns_empty():
    """No state has compatibility for an unrecognized posture key."""
    out = goal_states_for_posture("not_a_posture")
    assert out == []


def test_goal_states_with_containment_metaphor_includes_anxiety_reduction():
    """anxiety_reduction's primary metaphor is CONTAINMENT (safe space)."""
    out = goal_states_with_metaphor(LUXYPrimaryMetaphor.CONTAINMENT)
    ids = {g.id for g in out}
    assert "anxiety_reduction" in ids


def test_goal_states_with_status_metaphor_includes_status_display():
    out = goal_states_with_metaphor(LUXYPrimaryMetaphor.STATUS_AS_VERTICALITY)
    ids = {g.id for g in out}
    assert "status_display" in ids
    assert "social_positioning" in ids


def test_goal_states_with_time_metaphor_includes_time_pressure():
    out = goal_states_with_metaphor(LUXYPrimaryMetaphor.TIME_AS_RESOURCE)
    ids = {g.id for g in out}
    assert "time_pressure" in ids
    assert "time_recovery" in ids


def test_goal_states_with_unknown_metaphor_returns_empty():
    out = goal_states_with_metaphor("not_a_metaphor")
    assert out == []


# -----------------------------------------------------------------------------
# Pydantic schema validators
# -----------------------------------------------------------------------------


def test_validator_rejects_unknown_posture_key():
    with pytest.raises(ValueError, match="posture_compatibility"):
        GoalState(
            id="bad", name="bad", description="bad",
            posture_compatibility={"not_a_posture": 0.5},
            mechanism_priors={},
            primary_metaphor=LUXYPrimaryMetaphor.CONTAINMENT,
        )


def test_validator_rejects_out_of_range_posture_value():
    with pytest.raises(ValueError, match="posture_compatibility"):
        GoalState(
            id="bad", name="bad", description="bad",
            posture_compatibility={POSTURE_BLEND: 1.5},
            mechanism_priors={},
            primary_metaphor=LUXYPrimaryMetaphor.CONTAINMENT,
        )


def test_validator_rejects_unknown_mechanism_key():
    with pytest.raises(ValueError, match="MECHANISM_TAXONOMY"):
        GoalState(
            id="bad", name="bad", description="bad",
            posture_compatibility={POSTURE_BLEND: 0.5},
            mechanism_priors={"not_a_mechanism": 0.5},
            primary_metaphor=LUXYPrimaryMetaphor.CONTAINMENT,
        )


def test_validator_rejects_unknown_metaphor():
    with pytest.raises(ValueError, match="primary_metaphor"):
        GoalState(
            id="bad", name="bad", description="bad",
            posture_compatibility={POSTURE_BLEND: 0.5},
            mechanism_priors={},
            primary_metaphor="fabricated_metaphor",
        )


# -----------------------------------------------------------------------------
# Pydantic round-trip
# -----------------------------------------------------------------------------


def test_pydantic_round_trip_preserves_state():
    state = get_goal_state("anxiety_reduction")
    assert state is not None
    serialized = state.model_dump_json()
    restored = GoalState.model_validate_json(serialized)
    assert restored.id == state.id
    assert restored.name == state.name
    assert restored.posture_compatibility == state.posture_compatibility
    assert restored.mechanism_priors == state.mechanism_priors
    assert restored.primary_metaphor == state.primary_metaphor
    assert restored.keywords == state.keywords


# -----------------------------------------------------------------------------
# Slice 12 — Neo4j writeback / reload
# -----------------------------------------------------------------------------


from typing import Any, Dict, List, Optional
from unittest.mock import patch

from adam.intelligence.goal_state_inventory import (
    load_all_goal_states_from_neo4j,
    load_goal_state_from_neo4j,
    write_all_goal_states_to_neo4j,
    write_goal_state_to_neo4j,
)


class _FakeRecord:
    def __init__(self, data: Dict[str, Any]) -> None:
        self._data = data

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)


class _FakeAsyncResult:
    def __init__(self, rows: List[Dict[str, Any]]) -> None:
        self._rows = list(rows)

    async def single(self) -> Optional[_FakeRecord]:
        if not self._rows:
            return None
        return _FakeRecord(self._rows[0])

    def __aiter__(self):
        async def _gen():
            for r in self._rows:
                yield _FakeRecord(r)
        return _gen()


class _FakeAsyncSession:
    def __init__(self, driver: "_FakeNeo4jDriver") -> None:
        self._driver = driver

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None

    async def run(self, cypher: str, **params: Any) -> _FakeAsyncResult:
        self._driver.calls.append((cypher, dict(params)))
        norm = cypher.strip()
        if norm.startswith("MERGE (g:GoalState"):
            self._driver.states[params["goal_state_id"]] = dict(params)
            return _FakeAsyncResult([])
        if norm.startswith("MATCH (g:GoalState {goal_state_id"):
            cid = params["goal_state_id"]
            row = self._driver.states.get(cid)
            return _FakeAsyncResult([row] if row else [])
        if norm.startswith("MATCH (g:GoalState)"):
            return _FakeAsyncResult(list(self._driver.states.values()))
        return _FakeAsyncResult([])


class _FakeNeo4jDriver:
    def __init__(self) -> None:
        self.states: Dict[str, Dict[str, Any]] = {}
        self.calls: List = []

    def session(self) -> _FakeAsyncSession:
        return _FakeAsyncSession(self)


@pytest.mark.asyncio
async def test_write_no_driver_returns_false():
    state = get_goal_state("anxiety_reduction")
    assert state is not None
    ok = await write_goal_state_to_neo4j(state, driver=None)
    assert ok is False


@pytest.mark.asyncio
async def test_write_then_load_round_trip_preserves_state():
    """Persisted nested fields (posture_compatibility, mechanism_priors,
    keywords) must round-trip through JSON serialization."""
    driver = _FakeNeo4jDriver()
    state = get_goal_state("anxiety_reduction")
    assert state is not None

    ok = await write_goal_state_to_neo4j(state, driver=driver)
    assert ok is True

    loaded = await load_goal_state_from_neo4j(state.id, driver=driver)
    assert loaded is not None
    assert loaded.id == state.id
    assert loaded.name == state.name
    assert loaded.description == state.description
    assert loaded.primary_metaphor == state.primary_metaphor
    assert loaded.posture_compatibility == state.posture_compatibility
    assert loaded.mechanism_priors == state.mechanism_priors
    assert loaded.keywords == state.keywords


@pytest.mark.asyncio
async def test_write_uses_merge_for_idempotence():
    """Re-writing the same state doesn't create a duplicate; cypher
    is MERGE-based."""
    driver = _FakeNeo4jDriver()
    state = get_goal_state("commute_readiness")
    assert state is not None

    await write_goal_state_to_neo4j(state, driver=driver)
    await write_goal_state_to_neo4j(state, driver=driver)

    # Only one state row stored regardless of write count
    assert len(driver.states) == 1
    # Cypher was MERGE (not CREATE)
    merge_calls = [c for c, _ in driver.calls if "MERGE" in c]
    assert len(merge_calls) == 2


@pytest.mark.asyncio
async def test_load_missing_returns_none():
    driver = _FakeNeo4jDriver()
    loaded = await load_goal_state_from_neo4j("not_in_neo4j", driver=driver)
    assert loaded is None


@pytest.mark.asyncio
async def test_load_no_driver_returns_none():
    loaded = await load_goal_state_from_neo4j("anxiety_reduction", driver=None)
    assert loaded is None


@pytest.mark.asyncio
async def test_load_empty_id_returns_none():
    driver = _FakeNeo4jDriver()
    loaded = await load_goal_state_from_neo4j("", driver=driver)
    assert loaded is None


@pytest.mark.asyncio
async def test_write_all_persists_full_inventory():
    """Bulk write seeds the entire LUXY inventory."""
    driver = _FakeNeo4jDriver()
    written = await write_all_goal_states_to_neo4j(driver=driver)
    assert written == len(list_goal_states())
    assert len(driver.states) == len(list_goal_states())


@pytest.mark.asyncio
async def test_write_all_no_driver_returns_zero():
    written = await write_all_goal_states_to_neo4j(driver=None)
    assert written == 0


@pytest.mark.asyncio
async def test_load_all_returns_full_inventory_after_write():
    driver = _FakeNeo4jDriver()
    await write_all_goal_states_to_neo4j(driver=driver)

    loaded = await load_all_goal_states_from_neo4j(driver=driver)
    assert len(loaded) == len(list_goal_states())
    loaded_ids = {s.id for s in loaded}
    expected_ids = {s.id for s in list_goal_states()}
    assert loaded_ids == expected_ids


@pytest.mark.asyncio
async def test_load_all_no_driver_returns_empty():
    out = await load_all_goal_states_from_neo4j(driver=None)
    assert out == []


@pytest.mark.asyncio
async def test_write_soft_fails_on_session_exception():
    """Cypher session raising → write returns False; never raises."""
    class _BrokenSession:
        async def __aenter__(self):
            raise RuntimeError("simulated cypher failure")
        async def __aexit__(self, *a, **kw):
            return None

    class _BrokenDriver:
        def session(self):
            return _BrokenSession()

    state = get_goal_state("commute_readiness")
    assert state is not None
    ok = await write_goal_state_to_neo4j(state, driver=_BrokenDriver())
    assert ok is False
