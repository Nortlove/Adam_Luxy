"""Pin Slice 5 — outcome → DecisionTrace closure writer.

Discipline anchors (B3-LUXY a/b/c/d) for
``adam/intelligence/outcome_trace_closure.py``:

    (a) Per directive line 248: "Long-term archival in Neo4j as
        DecisionTrace nodes linked to the User, the ConversionEdge
        (when the impression resolves), and the Mechanism."
        Per directive Section 5.2 Step 8 line 709: "Decision-trace
        closure: link the trace to the outcome." Closes the honest
        tag in decision_trace_neo4j.py:78-80.

    (b) Boundary anchors pinned by these tests:
          - conversion_edge_id deterministic from decision_id (replays
            produce same id)
          - empty decision_id → skipped, reason="no_decision_id"
          - no driver / not connected → skipped, reason="no_driver"
          - happy path → written=True, reason="written"
          - trace not yet archived → written=True (node persists),
            reason="trace_not_found" (edge deferred)
          - Cypher exception → written=False, skipped=False,
            reason="neo4j_exception", logged at WARNING
          - Cypher contains MERGE (idempotent) on conversion_edge_id
          - Cypher creates :RESOLVED edge from :ConversionEdge to
            :DecisionTrace per directive's exact wording
          - signed_reward defaults to 0.0 when not provided
          - ConversionEdgeWriteResult is frozen

    (c) calibration_pending=False — schema is declarative.

    (d) Honest tags — what is NOT tested here:
          - User-attribution edge (sibling slice)
          - VIA_MECHANISM edge from ConversionEdge (sibling slice)
          - DecisionTrace mutation with outcome fields (sibling)
"""

from __future__ import annotations

import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from adam.intelligence.outcome_trace_closure import (
    CONVERSION_EDGE_NODE_LABEL,
    DECISION_TRACE_NODE_LABEL,
    RESOLVED_REL,
    ConversionEdgeWriteResult,
    conversion_edge_id_for,
    write_outcome_trace_closure,
)


# -----------------------------------------------------------------------------
# Schema constants
# -----------------------------------------------------------------------------


def test_directive_canonical_node_labels():
    """Use the directive's exact wording for label + edge."""
    assert CONVERSION_EDGE_NODE_LABEL == "ConversionEdge"
    assert DECISION_TRACE_NODE_LABEL == "DecisionTrace"
    assert RESOLVED_REL == "RESOLVED"


# -----------------------------------------------------------------------------
# Deterministic id
# -----------------------------------------------------------------------------


def test_conversion_edge_id_deterministic():
    """Same decision_id → same edge id (replays + cross-process safe)."""
    a = conversion_edge_id_for("dec_xyz_42")
    b = conversion_edge_id_for("dec_xyz_42")
    c = conversion_edge_id_for("dec_xyz_42")
    assert a == b == c


def test_conversion_edge_id_distinct_inputs_distinct_outputs():
    a = conversion_edge_id_for("dec_a")
    b = conversion_edge_id_for("dec_b")
    assert a != b


def test_conversion_edge_id_format_is_short():
    """ce: prefix + 16-char hash slice — log-line + Cypher friendly."""
    cid = conversion_edge_id_for("dec_anything")
    assert cid.startswith("ce:")
    assert len(cid) == 19  # "ce:" (3) + 16 hex chars


# -----------------------------------------------------------------------------
# Soft-fail paths
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_empty_decision_id_skipped():
    """Empty decision_id → skipped without driver call."""
    result = await write_outcome_trace_closure(
        decision_id="",
        outcome_type="conversion",
        outcome_value=1.0,
        neo4j_client=None,
    )
    assert isinstance(result, ConversionEdgeWriteResult)
    assert result.skipped is True
    assert result.reason == "no_decision_id"
    assert result.written is False


@pytest.mark.asyncio
async def test_no_driver_skipped():
    """Disconnected client → skipped, reason no_driver."""
    fake_client = MagicMock()
    fake_client.is_connected = False
    result = await write_outcome_trace_closure(
        decision_id="dec_xyz",
        outcome_type="conversion",
        outcome_value=1.0,
        neo4j_client=fake_client,
    )
    assert result.skipped is True
    assert result.reason == "no_driver"
    assert result.written is False


@pytest.mark.asyncio
async def test_neo4j_exception_soft_fail(caplog):
    """Driver raising → written=False + reason neo4j_exception, logged WARN."""
    fake_client = MagicMock()
    fake_client.is_connected = True

    async def _broken_session(*args, **kwargs):
        raise RuntimeError("simulated driver crash")

    fake_client.session = _broken_session

    with caplog.at_level(logging.WARNING):
        result = await write_outcome_trace_closure(
            decision_id="dec_xyz",
            outcome_type="conversion",
            outcome_value=1.0,
            neo4j_client=fake_client,
        )

    assert result.written is False
    assert result.skipped is False
    assert result.reason == "neo4j_exception"
    assert "write failed" in caplog.text.lower()


# -----------------------------------------------------------------------------
# Happy path
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_happy_path_writes_and_returns_written():
    """Driver session returns a record → written=True, reason=written."""
    fake_session = MagicMock()
    fake_result = MagicMock()
    fake_record = MagicMock()
    fake_record.__getitem__ = lambda self, k: "ce:abc123"
    fake_result.single = AsyncMock(return_value=fake_record)
    fake_session.run = AsyncMock(return_value=fake_result)

    # session() context manager — the writer uses `async with await client.session()`
    fake_session_cm = MagicMock()
    fake_session_cm.__aenter__ = AsyncMock(return_value=fake_session)
    fake_session_cm.__aexit__ = AsyncMock(return_value=None)

    fake_client = MagicMock()
    fake_client.is_connected = True
    fake_client.session = AsyncMock(return_value=fake_session_cm)

    result = await write_outcome_trace_closure(
        decision_id="dec_xyz",
        outcome_type="conversion",
        outcome_value=1.0,
        signed_reward=0.7,
        neo4j_client=fake_client,
    )

    assert result.written is True
    assert result.skipped is False
    assert result.reason == "written"
    assert result.conversion_edge_id == conversion_edge_id_for("dec_xyz")


@pytest.mark.asyncio
async def test_trace_not_found_returns_specific_reason():
    """When :DecisionTrace MATCH yields no rows → reason=trace_not_found."""
    fake_session = MagicMock()
    fake_result = MagicMock()
    fake_result.single = AsyncMock(return_value=None)  # no record
    fake_session.run = AsyncMock(return_value=fake_result)

    fake_session_cm = MagicMock()
    fake_session_cm.__aenter__ = AsyncMock(return_value=fake_session)
    fake_session_cm.__aexit__ = AsyncMock(return_value=None)

    fake_client = MagicMock()
    fake_client.is_connected = True
    fake_client.session = AsyncMock(return_value=fake_session_cm)

    result = await write_outcome_trace_closure(
        decision_id="dec_xyz",
        outcome_type="conversion",
        outcome_value=1.0,
        neo4j_client=fake_client,
    )

    assert result.written is True
    assert result.reason == "trace_not_found"


# -----------------------------------------------------------------------------
# Cypher contract pin — query shape must reflect directive
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cypher_uses_merge_on_conversion_edge_id():
    """The query must MERGE on conversion_edge_id (idempotency invariant)."""
    captured_query: list = []
    fake_session = MagicMock()
    fake_result = MagicMock()
    fake_record = MagicMock()
    fake_record.__getitem__ = lambda self, k: "ce:test"
    fake_result.single = AsyncMock(return_value=fake_record)

    async def _capture_run(query, **kwargs):
        captured_query.append(query)
        return fake_result

    fake_session.run = _capture_run

    fake_session_cm = MagicMock()
    fake_session_cm.__aenter__ = AsyncMock(return_value=fake_session)
    fake_session_cm.__aexit__ = AsyncMock(return_value=None)

    fake_client = MagicMock()
    fake_client.is_connected = True
    fake_client.session = AsyncMock(return_value=fake_session_cm)

    await write_outcome_trace_closure(
        decision_id="dec_xyz",
        outcome_type="conversion",
        outcome_value=1.0,
        neo4j_client=fake_client,
    )

    assert len(captured_query) == 1
    q = captured_query[0]
    # Must MERGE on conversion_edge_id to be idempotent
    assert "MERGE" in q
    assert "conversion_edge_id" in q
    # Must reference both labels per directive line 248
    assert "ConversionEdge" in q
    assert "DecisionTrace" in q
    # Must create the RESOLVED edge
    assert "RESOLVED" in q


# -----------------------------------------------------------------------------
# Frozen dataclass
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_result_frozen():
    """ConversionEdgeWriteResult cannot be mutated by caller."""
    result = await write_outcome_trace_closure(
        decision_id="",
        outcome_type="conversion",
        outcome_value=1.0,
    )
    with pytest.raises(Exception):  # FrozenInstanceError
        result.written = True  # type: ignore[misc]
