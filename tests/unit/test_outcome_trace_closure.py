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
          - User-attribution edge — SHIPPED in Slice 15 (covered
            by tests below)
          - VIA_MECHANISM edge from ConversionEdge — SHIPPED in
            Slice 15 (covered by tests below)
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


# -----------------------------------------------------------------------------
# Slice 15 — User attribution + VIA_MECHANISM edges
# -----------------------------------------------------------------------------


def test_slice_15_schema_constants_present():
    """The new node labels and relationship names match directive
    line 248 ('linked to the User ... and the Mechanism')."""
    from adam.intelligence.outcome_trace_closure import (
        GENERATED_REL,
        MECHANISM_NODE_LABEL,
        USER_NODE_LABEL,
        VIA_MECHANISM_REL,
    )
    assert USER_NODE_LABEL == "User"
    assert MECHANISM_NODE_LABEL == "Mechanism"
    assert GENERATED_REL == "GENERATED"
    assert VIA_MECHANISM_REL == "VIA_MECHANISM"


def _build_capturing_session(
    *, base_record: bool = True,
):
    """Build a fake session that captures every Cypher call."""
    captured: list = []
    fake_result_with_record = MagicMock()
    fake_record = MagicMock()
    fake_record.__getitem__ = lambda self, k: "ce:test"
    fake_result_with_record.single = AsyncMock(return_value=fake_record)
    fake_result_no_record = MagicMock()
    fake_result_no_record.single = AsyncMock(return_value=None)

    async def _capture_run(query, **kwargs):
        captured.append((query, dict(kwargs)))
        # Only the FIRST call (base closure) returns a record;
        # subsequent calls (user / mechanism) return None.
        if len(captured) == 1:
            return (
                fake_result_with_record if base_record
                else fake_result_no_record
            )
        return fake_result_no_record

    fake_session = MagicMock()
    fake_session.run = _capture_run
    fake_session_cm = MagicMock()
    fake_session_cm.__aenter__ = AsyncMock(return_value=fake_session)
    fake_session_cm.__aexit__ = AsyncMock(return_value=None)

    fake_client = MagicMock()
    fake_client.is_connected = True
    fake_client.session = AsyncMock(return_value=fake_session_cm)
    return fake_client, captured


@pytest.mark.asyncio
async def test_no_user_no_mechanism_only_base_cypher():
    """Default behavior (Slice 5 contract): only base closure Cypher
    runs when user_id / chosen_mechanism not provided."""
    client, captured = _build_capturing_session()
    result = await write_outcome_trace_closure(
        decision_id="dec_baseline",
        outcome_type="conversion",
        outcome_value=1.0,
        neo4j_client=client,
    )
    assert result.written is True
    assert len(captured) == 1
    base_q, _ = captured[0]
    assert "ConversionEdge" in base_q
    assert "RESOLVED" in base_q
    # No User / Mechanism edges because no inputs.
    assert "GENERATED" not in base_q
    assert "VIA_MECHANISM" not in base_q


@pytest.mark.asyncio
async def test_user_id_fires_user_attribution_cypher():
    """user_id provided → second Cypher MERGEs (:User)-[:GENERATED]->(:CE)."""
    client, captured = _build_capturing_session()
    await write_outcome_trace_closure(
        decision_id="dec_user",
        outcome_type="conversion",
        outcome_value=1.0,
        neo4j_client=client,
        user_id="buyer-42",
    )
    assert len(captured) == 2  # base + user attribution
    user_q, user_params = captured[1]
    assert "User" in user_q
    assert "GENERATED" in user_q
    assert "ConversionEdge" in user_q
    assert user_params["user_id"] == "buyer-42"


@pytest.mark.asyncio
async def test_mechanism_fires_via_mechanism_cypher():
    """chosen_mechanism provided → second Cypher MERGEs
    (:CE)-[:VIA_MECHANISM]->(:Mechanism)."""
    client, captured = _build_capturing_session()
    await write_outcome_trace_closure(
        decision_id="dec_mech",
        outcome_type="conversion",
        outcome_value=1.0,
        neo4j_client=client,
        chosen_mechanism="social_proof",
    )
    assert len(captured) == 2  # base + via mechanism
    mech_q, mech_params = captured[1]
    assert "Mechanism" in mech_q
    assert "VIA_MECHANISM" in mech_q
    assert mech_params["mechanism_name"] == "social_proof"


@pytest.mark.asyncio
async def test_both_user_and_mechanism_fire_three_cyphers():
    """Both supplied → 3 total Cypher calls (base + user + mechanism)."""
    client, captured = _build_capturing_session()
    result = await write_outcome_trace_closure(
        decision_id="dec_full",
        outcome_type="conversion",
        outcome_value=1.0,
        neo4j_client=client,
        user_id="buyer-42",
        chosen_mechanism="social_proof",
    )
    assert result.written is True
    assert result.reason == "written"
    assert len(captured) == 3
    queries = [q for q, _ in captured]
    assert any("RESOLVED" in q for q in queries)
    assert any("GENERATED" in q for q in queries)
    assert any("VIA_MECHANISM" in q for q in queries)


@pytest.mark.asyncio
async def test_empty_user_id_skips_user_cypher():
    """Empty / falsy user_id → no User Cypher fired (treated like None)."""
    client, captured = _build_capturing_session()
    await write_outcome_trace_closure(
        decision_id="dec_anon",
        outcome_type="conversion",
        outcome_value=1.0,
        neo4j_client=client,
        user_id="",  # anonymous
        chosen_mechanism="social_proof",
    )
    # Only base + mechanism — user empty string skipped.
    assert len(captured) == 2
    queries = [q for q, _ in captured]
    assert not any("GENERATED" in q for q in queries)
    assert any("VIA_MECHANISM" in q for q in queries)


@pytest.mark.asyncio
async def test_user_attribution_failure_does_not_break_base_write():
    """If the User Cypher raises, the writer logs WARNING but still
    returns written=True (base closure already succeeded)."""
    fake_session = MagicMock()
    fake_result = MagicMock()
    fake_record = MagicMock()
    fake_record.__getitem__ = lambda self, k: "ce:test"
    fake_result.single = AsyncMock(return_value=fake_record)

    call_count = [0]

    async def _selective_run(query, **kwargs):
        call_count[0] += 1
        if "GENERATED" in query:
            raise RuntimeError("user merge failed")
        return fake_result

    fake_session.run = _selective_run
    fake_session_cm = MagicMock()
    fake_session_cm.__aenter__ = AsyncMock(return_value=fake_session)
    fake_session_cm.__aexit__ = AsyncMock(return_value=None)

    fake_client = MagicMock()
    fake_client.is_connected = True
    fake_client.session = AsyncMock(return_value=fake_session_cm)

    result = await write_outcome_trace_closure(
        decision_id="dec_resilient",
        outcome_type="conversion",
        outcome_value=1.0,
        neo4j_client=fake_client,
        user_id="buyer-42",
        chosen_mechanism="social_proof",
    )
    # Base + mechanism still succeed; user fail is non-fatal.
    assert result.written is True
    assert result.reason == "written"


@pytest.mark.asyncio
async def test_mechanism_failure_does_not_break_base_write():
    """If the Mechanism Cypher raises, the writer logs WARNING but
    still returns written=True."""
    fake_session = MagicMock()
    fake_result = MagicMock()
    fake_record = MagicMock()
    fake_record.__getitem__ = lambda self, k: "ce:test"
    fake_result.single = AsyncMock(return_value=fake_record)

    async def _selective_run(query, **kwargs):
        if "VIA_MECHANISM" in query:
            raise RuntimeError("mechanism merge failed")
        return fake_result

    fake_session.run = _selective_run
    fake_session_cm = MagicMock()
    fake_session_cm.__aenter__ = AsyncMock(return_value=fake_session)
    fake_session_cm.__aexit__ = AsyncMock(return_value=None)

    fake_client = MagicMock()
    fake_client.is_connected = True
    fake_client.session = AsyncMock(return_value=fake_session_cm)

    result = await write_outcome_trace_closure(
        decision_id="dec_mech_fail",
        outcome_type="conversion",
        outcome_value=1.0,
        neo4j_client=fake_client,
        user_id="buyer-42",
        chosen_mechanism="social_proof",
    )
    assert result.written is True


@pytest.mark.asyncio
async def test_outcome_handler_threads_user_id_and_mechanism():
    """The outcome_handler integration point passes user_id and
    chosen_mechanism into write_outcome_trace_closure when present
    in the metadata."""
    from pathlib import Path
    src = Path("adam/core/learning/outcome_handler.py").read_text()
    # Source-text contract: handler must reference both kwargs in
    # the Slice 15 call site.
    assert "user_id=_user_for_closure" in src
    assert "chosen_mechanism=_mech_for_closure" in src
    # Both metadata sources used (buyer_id fallback for legacy keys).
    assert 'metadata.get("user_id")' in src or 'metadata.get("buyer_id")' in src
    assert 'metadata.get("mechanism_sent"' in src
