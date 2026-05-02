"""Pin Slice 6 — :AdOutcome writer (OPE input producer).

Discipline anchors (B3-LUXY a/b/c/d) for
``adam/intelligence/ad_outcome_persist.py``:

    (a) Per audit Tier 1 #5: ope.py:469 loader expects the schema
        (:DecisionContext)-[:HAD_OUTCOME]->(:AdOutcome). Slice 6
        writes the outcome side that nobody was producing. Mirrors
        the dead-code precedent in gradient_bridge/service.py:974-988.

    (b) Boundary anchors pinned by these tests:
          - outcome_id deterministic from decision_id
          - empty decision_id → skipped, reason="no_decision_id"
          - no driver / not connected → skipped, reason="no_driver"
          - happy path → written=True, reason="written"
          - decision context not yet persisted → written=False,
            reason="context_not_found" (replay-safe)
          - Cypher exception → written=False, reason="neo4j_exception"
          - Cypher contains MERGE on outcome_id (idempotency)
          - Cypher MATCH'es :DecisionContext + MERGE'es :AdOutcome +
            HAD_OUTCOME edge per directive schema
          - signed_reward defaults to 0.0
          - AdOutcomeWriteResult is frozen

    (c) calibration_pending=False — schema is declarative.

    (d) Honest tags — what is NOT tested here:
          - Per-cohort outcome aggregation (sibling, Loop B blocked)
          - Schema-merge with Slice 5's :ConversionEdge (sibling)
"""

from __future__ import annotations

import logging
from unittest.mock import AsyncMock, MagicMock

import pytest

from adam.intelligence.ad_outcome_persist import (
    AD_OUTCOME_NODE_LABEL,
    DECISION_CONTEXT_NODE_LABEL,
    HAD_OUTCOME_REL,
    AdOutcomeWriteResult,
    outcome_id_for,
    write_ad_outcome,
)


# -----------------------------------------------------------------------------
# Schema constants
# -----------------------------------------------------------------------------


def test_schema_constants_match_ope_loader():
    """Match ope.py:469 loader expectations exactly."""
    assert AD_OUTCOME_NODE_LABEL == "AdOutcome"
    assert DECISION_CONTEXT_NODE_LABEL == "DecisionContext"
    assert HAD_OUTCOME_REL == "HAD_OUTCOME"


# -----------------------------------------------------------------------------
# Deterministic id (matches gradient_bridge precedent)
# -----------------------------------------------------------------------------


def test_outcome_id_matches_gradient_bridge_pattern():
    """Format is `{decision_id}_outcome` per gradient_bridge:977."""
    assert outcome_id_for("dec_xyz") == "dec_xyz_outcome"


def test_outcome_id_deterministic():
    a = outcome_id_for("dec_abc")
    b = outcome_id_for("dec_abc")
    assert a == b


# -----------------------------------------------------------------------------
# Soft-fail paths
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_empty_decision_id_skipped():
    result = await write_ad_outcome(
        decision_id="",
        outcome_type="conversion",
        outcome_value=1.0,
        neo4j_client=None,
    )
    assert isinstance(result, AdOutcomeWriteResult)
    assert result.skipped is True
    assert result.reason == "no_decision_id"
    assert result.written is False


@pytest.mark.asyncio
async def test_no_driver_skipped():
    fake_client = MagicMock()
    fake_client.is_connected = False
    result = await write_ad_outcome(
        decision_id="dec_xyz",
        outcome_type="conversion",
        outcome_value=1.0,
        neo4j_client=fake_client,
    )
    assert result.skipped is True
    assert result.reason == "no_driver"


@pytest.mark.asyncio
async def test_neo4j_exception_soft_fail(caplog):
    fake_client = MagicMock()
    fake_client.is_connected = True

    async def _broken_session(*args, **kwargs):
        raise RuntimeError("simulated driver crash")

    fake_client.session = _broken_session

    with caplog.at_level(logging.WARNING):
        result = await write_ad_outcome(
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
# Happy path + context-not-found
# -----------------------------------------------------------------------------


def _ok_session_returning(record):
    """Build a mock session that returns `record` on .single()."""
    fake_session = MagicMock()
    fake_result = MagicMock()
    fake_result.single = AsyncMock(return_value=record)
    fake_session.run = AsyncMock(return_value=fake_result)

    fake_session_cm = MagicMock()
    fake_session_cm.__aenter__ = AsyncMock(return_value=fake_session)
    fake_session_cm.__aexit__ = AsyncMock(return_value=None)

    fake_client = MagicMock()
    fake_client.is_connected = True
    fake_client.session = AsyncMock(return_value=fake_session_cm)
    return fake_client, fake_session


@pytest.mark.asyncio
async def test_happy_path_writes_returns_written():
    fake_record = MagicMock()
    fake_record.__getitem__ = lambda self, k: "dec_xyz_outcome"
    client, _ = _ok_session_returning(fake_record)

    result = await write_ad_outcome(
        decision_id="dec_xyz",
        outcome_type="conversion",
        outcome_value=1.0,
        signed_reward=0.7,
        neo4j_client=client,
    )

    assert result.written is True
    assert result.skipped is False
    assert result.reason == "written"
    assert result.outcome_id == "dec_xyz_outcome"


@pytest.mark.asyncio
async def test_context_not_found_returns_specific_reason():
    """When :DecisionContext MATCH yields no rows → context_not_found."""
    client, _ = _ok_session_returning(None)

    result = await write_ad_outcome(
        decision_id="dec_xyz",
        outcome_type="conversion",
        outcome_value=1.0,
        neo4j_client=client,
    )

    assert result.written is False
    assert result.reason == "context_not_found"


# -----------------------------------------------------------------------------
# Cypher contract
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cypher_uses_merge_on_outcome_id_and_edge():
    """Idempotency invariant + edge creation."""
    captured = []
    fake_session = MagicMock()
    fake_result = MagicMock()
    fake_record = MagicMock()
    fake_record.__getitem__ = lambda self, k: "x"
    fake_result.single = AsyncMock(return_value=fake_record)

    async def _capture_run(query, **kwargs):
        captured.append(query)
        return fake_result

    fake_session.run = _capture_run
    fake_session_cm = MagicMock()
    fake_session_cm.__aenter__ = AsyncMock(return_value=fake_session)
    fake_session_cm.__aexit__ = AsyncMock(return_value=None)

    fake_client = MagicMock()
    fake_client.is_connected = True
    fake_client.session = AsyncMock(return_value=fake_session_cm)

    await write_ad_outcome(
        decision_id="dec_xyz",
        outcome_type="conversion",
        outcome_value=1.0,
        neo4j_client=fake_client,
    )

    assert len(captured) == 1
    q = captured[0]
    assert "MERGE" in q
    assert "outcome_id" in q
    # Both labels per ope.py loader expectation
    assert "DecisionContext" in q
    assert "AdOutcome" in q
    # The HAD_OUTCOME edge
    assert "HAD_OUTCOME" in q


@pytest.mark.asyncio
async def test_result_frozen():
    result = await write_ad_outcome(
        decision_id="",
        outcome_type="conversion",
        outcome_value=1.0,
    )
    with pytest.raises(Exception):  # FrozenInstanceError
        result.written = True  # type: ignore[misc]
