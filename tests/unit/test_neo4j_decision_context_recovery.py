"""Pin Neo4j decision-context recovery for late-arriving outcomes.

Discipline anchors:
    - When a conversion arrives after the in-memory cache TTL has
      expired (or the backend has restarted), the recovery path must
      reconstruct the FULL DecisionContext from the Neo4j durable
      storage — including the typed grounding evidence that gates
      posterior updates. Failing this means late-arriving outcomes
      fall back to legacy "all-true grounded" defaults regardless of
      the actual decision's bilateral-evidence quality.
    - The reconstruction must match the cache-hit reconstruction so
      the outcome handler sees the same gating regardless of which
      tier of recovery hit.
"""

from __future__ import annotations

import json
import time
from unittest.mock import patch, AsyncMock, MagicMock

import pytest

from adam.api.stackadapt.webhook import _lookup_decision_context_neo4j


def _neo4j_node_with_metadata(meta: dict) -> MagicMock:
    """Build a fake Neo4j node with metadata_json populated."""
    node = MagicMock()
    node.get = lambda key, default=None: {
        "metadata_json": json.dumps(meta),
        "archetype": meta.get("archetype", ""),
        "mechanism_sent": meta.get("mechanism_sent", ""),
        "cascade_level": meta.get("cascade_level", 1),
        "buyer_id": meta.get("buyer_id", ""),
        "segment_id": meta.get("segment_id", ""),
        "created_at": meta.get("decision_timestamp", time.time()),
    }.get(key, default)
    return node


@pytest.mark.asyncio
async def test_recovery_carries_typed_grounding_for_l3_decision():
    """A late-arriving outcome for an L3-grounded decision must
    recover with decision_mode='grounded' and the full grounding_
    evidence dict — including decision_path, cascade_level, edge_count.
    Without this, the outcome handler sees the legacy 'grounded'
    default with all-true links and the gate is bypassed."""
    meta = {
        "archetype": "connector",
        "mechanism_sent": "authority",
        "cascade_level": 3,
        "evidence_source": "bilateral_edges",
        "decision_mode": "grounded",
        "grounding_evidence": {
            "bilateral_edge_evidence_present": True,
            "atom_run_real": False,
            "theoretical_link_traversed": False,
            "decision_path": "stackadapt_creative_intelligence",
            "cascade_level": 3,
            "edge_count": 12317,
            "failure_reasons": [],
        },
        "decision_timestamp": time.time(),
    }
    node = _neo4j_node_with_metadata(meta)
    record = MagicMock()
    record.__getitem__ = lambda self, k: node

    session = MagicMock()
    session.run = AsyncMock(return_value=MagicMock(single=AsyncMock(return_value=record)))
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=None)

    driver = MagicMock()
    driver.session = lambda: session

    infra = MagicMock()
    infra.neo4j_driver = driver

    with patch(
        "adam.core.dependencies.get_infrastructure",
        new=AsyncMock(return_value=infra),
    ):
        ctx = await _lookup_decision_context_neo4j("dec_test_l3")

    assert ctx is not None
    assert ctx.decision_id == "dec_test_l3"
    assert ctx.archetype == "connector"
    assert ctx.cascade_level == 3
    assert ctx.decision_mode == "grounded"
    # Typed grounding evidence must round-trip through Neo4j
    assert ctx.grounding_evidence["bilateral_edge_evidence_present"] is True
    assert ctx.grounding_evidence["decision_path"] == "stackadapt_creative_intelligence"
    assert ctx.grounding_evidence["cascade_level"] == 3
    assert ctx.grounding_evidence["edge_count"] == 12317


@pytest.mark.asyncio
async def test_recovery_carries_typed_grounding_for_incomplete_decision():
    """The whole point of typed grounding: degraded decisions
    (cascade_level < 3) must recover as INCOMPLETE so the outcome
    handler skips posterior updates. Failing this means a late-
    arriving conversion for an L1/L2 fallback decision corrupts the
    BayesianPrior + RESPONDS_TO posteriors as if it had bilateral
    evidence."""
    meta = {
        "archetype": "connector",
        "mechanism_sent": "social_proof",
        "cascade_level": 2,
        "evidence_source": "category_posterior",
        "decision_mode": "incomplete",
        "grounding_evidence": {
            "bilateral_edge_evidence_present": False,
            "atom_run_real": False,
            "theoretical_link_traversed": False,
            "decision_path": "stackadapt_creative_intelligence",
            "cascade_level": 2,
            "edge_count": 0,
            "failure_reasons": ["cascade_level=2_below_l3_threshold"],
        },
        "decision_timestamp": time.time(),
    }
    node = _neo4j_node_with_metadata(meta)
    record = MagicMock()
    record.__getitem__ = lambda self, k: node

    session = MagicMock()
    session.run = AsyncMock(return_value=MagicMock(single=AsyncMock(return_value=record)))
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=None)

    driver = MagicMock()
    driver.session = lambda: session

    infra = MagicMock()
    infra.neo4j_driver = driver

    with patch(
        "adam.core.dependencies.get_infrastructure",
        new=AsyncMock(return_value=infra),
    ):
        ctx = await _lookup_decision_context_neo4j("dec_test_incomplete")

    assert ctx is not None
    assert ctx.decision_mode == "incomplete"
    assert ctx.grounding_evidence["bilateral_edge_evidence_present"] is False
    assert ctx.grounding_evidence["cascade_level"] == 2
    assert "cascade_level=2_below_l3_threshold" in ctx.grounding_evidence.get(
        "failure_reasons", []
    )


@pytest.mark.asyncio
async def test_recovery_legacy_metadata_falls_back_to_grounded():
    """Outcomes from decisions persisted BEFORE this typed-evidence
    shipped will have metadata without decision_mode /
    grounding_evidence keys. Recovery must default these to the
    legacy 'grounded' + all-true defaults — preserves legacy outcome
    handling for outcomes pre-dating this typed-evidence."""
    legacy_meta = {
        "archetype": "explorer",
        "mechanism_sent": "curiosity",
        "cascade_level": 3,
        "evidence_source": "bilateral_edges",
        "decision_timestamp": time.time(),
        # No decision_mode / grounding_evidence — legacy decision
    }
    node = _neo4j_node_with_metadata(legacy_meta)
    record = MagicMock()
    record.__getitem__ = lambda self, k: node

    session = MagicMock()
    session.run = AsyncMock(return_value=MagicMock(single=AsyncMock(return_value=record)))
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=None)

    driver = MagicMock()
    driver.session = lambda: session

    infra = MagicMock()
    infra.neo4j_driver = driver

    with patch(
        "adam.core.dependencies.get_infrastructure",
        new=AsyncMock(return_value=infra),
    ):
        ctx = await _lookup_decision_context_neo4j("dec_test_legacy")

    assert ctx is not None
    assert ctx.decision_mode == "grounded"  # legacy default
    assert ctx.grounding_evidence["bilateral_edge_evidence_present"] is True
    assert ctx.grounding_evidence["atom_run_real"] is True
    assert ctx.grounding_evidence["theoretical_link_traversed"] is True
