"""Pin KnowledgePropagationNetwork persistence — state survives restart.

Discipline anchors:
    - The network's TOPOLOGY (nodes + edges + transform_fn callables)
      is rebuilt fresh on init via _build_default_network. Persistence
      captures only the STATE that accumulates: per-node knowledge_state
      dicts, per-edge buffered signals, global counters.
    - Schema version mismatch returns the network in fresh-init state
      with topology only, not corrupted with partial overlays.
    - Soft-fail on Redis unavailable.
"""

from __future__ import annotations

import json
from unittest.mock import patch, MagicMock

from adam.intelligence.knowledge_propagation import (
    KnowledgePropagationNetwork,
    KnowledgeSignal,
    SignalType,
    _kpn_to_state_dict,
    _kpn_load_state_dict,
    _save_kpn_to_redis,
    _load_kpn_from_redis,
    maybe_persist_kpn,
)


def _populated_network() -> KnowledgePropagationNetwork:
    """Build a network with non-trivial state."""
    net = KnowledgePropagationNetwork()
    # Mutate node knowledge state
    if "thompson" in net.nodes:
        net.nodes["thompson"].knowledge_state["last_outcome"] = {"value": 0.42}
        net.nodes["thompson"].received_signals = 7
        net.nodes["thompson"].last_signal_time = 1700000000.0
    net._total_observations_processed = 42
    net._total_signals_propagated = 137
    net._cascade_depth_history = [3, 4, 5, 4, 3]
    return net


# -----------------------------------------------------------------------------
# State serialization round-trip
# -----------------------------------------------------------------------------


def test_state_dict_round_trip_preserves_node_state():
    src = _populated_network()
    state = _kpn_to_state_dict(src)

    dst = KnowledgePropagationNetwork()  # fresh; rebuilds topology
    _kpn_load_state_dict(dst, state)

    if "thompson" in dst.nodes:
        thompson = dst.nodes["thompson"]
        assert thompson.knowledge_state.get("last_outcome", {}).get("value") == 0.42
        assert thompson.received_signals == 7
        assert thompson.last_signal_time == 1700000000.0


def test_state_dict_round_trip_preserves_global_counters():
    src = _populated_network()
    state = _kpn_to_state_dict(src)

    dst = KnowledgePropagationNetwork()
    _kpn_load_state_dict(dst, state)

    assert dst._total_observations_processed == 42
    assert dst._total_signals_propagated == 137
    assert dst._cascade_depth_history == [3, 4, 5, 4, 3]


def test_state_dict_is_json_serializable():
    src = _populated_network()
    state = _kpn_to_state_dict(src)

    json_str = json.dumps(state, default=str)
    parsed = json.loads(json_str)

    dst = KnowledgePropagationNetwork()
    _kpn_load_state_dict(dst, parsed)

    assert dst._total_observations_processed == 42


def test_topology_rebuilt_fresh_state_overlaid():
    """Critical contract: the topology (nodes + edges + transform_fns)
    is REBUILT fresh on every init from _build_default_network.
    Persistence overlays state on top — does NOT serialize topology
    (transform_fns are callables, not state)."""
    src = _populated_network()
    state = _kpn_to_state_dict(src)

    dst = KnowledgePropagationNetwork()
    # dst has fresh topology after __init__
    fresh_node_count = len(dst.nodes)
    fresh_edge_count = sum(len(v) for v in dst.edges.values())
    assert fresh_node_count > 0  # _build_default_network ran
    assert fresh_edge_count > 0

    _kpn_load_state_dict(dst, state)

    # Topology unchanged after overlay; only state mutated
    assert len(dst.nodes) == fresh_node_count
    assert sum(len(v) for v in dst.edges.values()) == fresh_edge_count


# -----------------------------------------------------------------------------
# Schema version handling
# -----------------------------------------------------------------------------


def test_schema_version_mismatch_skips_load():
    """A future incompatible state must skip load — fresh-init topology
    is honest, not corrupted with partial overlays."""
    state = {
        "schema_version": 999,  # future
        "node_state": {"thompson": {"received_signals": 99}},
        "total_observations_processed": 99999,
    }

    network = KnowledgePropagationNetwork()
    _kpn_load_state_dict(network, state)

    # Nothing loaded
    assert network._total_observations_processed == 0
    if "thompson" in network.nodes:
        assert network.nodes["thompson"].received_signals == 0


# -----------------------------------------------------------------------------
# Redis save/load
# -----------------------------------------------------------------------------


def test_save_to_redis_writes_state():
    redis_mock = MagicMock()
    redis_mock.set = MagicMock()
    network = _populated_network()

    with patch(
        "adam.infrastructure.redis_client.get_redis", return_value=redis_mock,
    ):
        ok = _save_kpn_to_redis(network)

    assert ok is True
    redis_mock.set.assert_called_once()
    key, payload = redis_mock.set.call_args.args
    assert key == "adam:kpn:state:v1"
    parsed = json.loads(payload)
    assert parsed["total_observations_processed"] == 42


def test_save_to_redis_soft_fails_when_unavailable():
    with patch(
        "adam.infrastructure.redis_client.get_redis", return_value=None,
    ):
        network = _populated_network()
        ok = _save_kpn_to_redis(network)
    assert ok is False


def test_load_from_redis_restores_state():
    src = _populated_network()
    state_json = json.dumps(_kpn_to_state_dict(src), default=str)

    redis_mock = MagicMock()
    redis_mock.get = MagicMock(return_value=state_json)

    with patch(
        "adam.infrastructure.redis_client.get_redis", return_value=redis_mock,
    ):
        dst = KnowledgePropagationNetwork()
        ok = _load_kpn_from_redis(dst)

    assert ok is True
    assert dst._total_observations_processed == 42


def test_load_from_redis_returns_false_when_key_empty():
    redis_mock = MagicMock()
    redis_mock.get = MagicMock(return_value=None)

    with patch(
        "adam.infrastructure.redis_client.get_redis", return_value=redis_mock,
    ):
        dst = KnowledgePropagationNetwork()
        ok = _load_kpn_from_redis(dst)

    assert ok is False
    assert dst._total_observations_processed == 0


# -----------------------------------------------------------------------------
# Rate-limited persistence
# -----------------------------------------------------------------------------


def test_maybe_persist_at_cadence_boundary():
    """Cadence default 20 — _total_observations_processed==20 triggers
    save; ==1 does not."""
    save_calls = []

    def fake_save(net):
        save_calls.append(net._total_observations_processed)
        return True

    with patch(
        "adam.intelligence.knowledge_propagation._save_kpn_to_redis",
        side_effect=fake_save,
    ):
        net = KnowledgePropagationNetwork()
        net._total_observations_processed = 1
        maybe_persist_kpn(net)
        assert save_calls == []

        net._total_observations_processed = 20
        maybe_persist_kpn(net)
        assert save_calls == [20]

        net._total_observations_processed = 40
        maybe_persist_kpn(net)
        assert save_calls == [20, 40]


def test_maybe_persist_zero_total_is_noop():
    save_called = []

    with patch(
        "adam.intelligence.knowledge_propagation._save_kpn_to_redis",
        side_effect=lambda n: save_called.append(True),
    ):
        net = KnowledgePropagationNetwork()
        # _total_observations_processed = 0 by default
        maybe_persist_kpn(net)

    assert save_called == []
