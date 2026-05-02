"""Pin Original-Slice-A — page_url field on DecisionTrace.

Audit 2026-05-01 found the cascade had page_url in scope but
discarded it when building the trace; Slice 19's dual_eval_evaluator
+ Slice B (companion label-generation task) both depend on
page_url being persisted.

Tests pin:
    * DecisionTrace.page_url field exists with Optional[str] = None
    * build_decision_trace + build_trace_from_cascade thread the
      kwarg through cleanly
    * Cascade source threads page_url at the build_trace_from_cascade
      call site
    * Neo4j archive Cypher persists page_url as a first-class scalar
      (so Cypher filters don't need to parse payload_json)
    * Default None preserved when caller has no page (anonymous /
      non-page bid context)
    * Pydantic validation accepts None and any string (no schema
      surprises)
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from adam.intelligence.decision_trace import (
    DecisionTrace,
    build_decision_trace,
)


# -----------------------------------------------------------------------------
# Schema field contract
# -----------------------------------------------------------------------------


def test_decision_trace_carries_page_url_field():
    """DecisionTrace must expose page_url: Optional[str] = None."""
    trace = DecisionTrace(
        decision_id="dec_x",
        user_id="u_x",
        timestamp=datetime.now(timezone.utc),
        chosen_creative_id="cid_x",
        chosen_mechanism="curiosity",
        chosen_score=0.5,
    )
    assert hasattr(trace, "page_url")
    assert trace.page_url is None  # default


def test_decision_trace_page_url_assignable():
    trace = DecisionTrace(
        decision_id="dec_x",
        user_id="u_x",
        timestamp=datetime.now(timezone.utc),
        chosen_creative_id="cid_x",
        chosen_mechanism="curiosity",
        chosen_score=0.5,
        page_url="https://example.com/article",
    )
    assert trace.page_url == "https://example.com/article"


def test_decision_trace_page_url_round_trips_through_json():
    """Pydantic round-trip preserves page_url."""
    trace = DecisionTrace(
        decision_id="dec_x",
        user_id="u_x",
        timestamp=datetime.now(timezone.utc),
        chosen_creative_id="cid_x",
        chosen_mechanism="curiosity",
        chosen_score=0.5,
        page_url="https://example.com/article",
    )
    json_str = trace.model_dump_json()
    rehydrated = DecisionTrace.model_validate_json(json_str)
    assert rehydrated.page_url == "https://example.com/article"


# -----------------------------------------------------------------------------
# build_decision_trace builder
# -----------------------------------------------------------------------------


def test_builder_threads_page_url():
    trace = build_decision_trace(
        decision_id="dec_x",
        user_id="u_x",
        chosen_creative_id="cid_x",
        chosen_mechanism="curiosity",
        chosen_score=0.5,
        page_url="https://luxy-relevant.example/booking",
    )
    assert trace.page_url == "https://luxy-relevant.example/booking"


def test_builder_default_none_preserved():
    """No page_url passed → trace.page_url stays None."""
    trace = build_decision_trace(
        decision_id="dec_x",
        user_id="u_x",
        chosen_creative_id="cid_x",
        chosen_mechanism="curiosity",
        chosen_score=0.5,
    )
    assert trace.page_url is None


# -----------------------------------------------------------------------------
# build_trace_from_cascade signature
# -----------------------------------------------------------------------------


def test_build_trace_from_cascade_accepts_page_url_kwarg():
    """The cascade-emit helper must accept page_url and thread it onto the trace."""
    import inspect

    from adam.intelligence.decision_trace_emitter import build_trace_from_cascade

    sig = inspect.signature(build_trace_from_cascade)
    assert "page_url" in sig.parameters, (
        "build_trace_from_cascade lost page_url kwarg — Original-"
        "Slice-A wire is broken; cascade can no longer thread page "
        "context onto the trace."
    )


# -----------------------------------------------------------------------------
# Cascade source-text wire pin
# -----------------------------------------------------------------------------


def test_cascade_threads_page_url_to_emitter():
    """Cascade must pass page_url=page_url at the build_trace_from_cascade
    call site — guards against silent regression to dropping the URL.
    """
    src = Path("adam/api/stackadapt/bilateral_cascade.py").read_text()
    # The arg must appear inside a build_trace_from_cascade(...) call —
    # the simplest robust pin is the literal "page_url=page_url"
    # substring (matches the kwarg passing pattern at the call site).
    assert "page_url=page_url" in src, (
        "Cascade lost page_url=page_url at the trace-build call site. "
        "Slice 19 dual_eval_evaluator + Slice B daily label-gen task "
        "depend on page_url reaching the trace."
    )


# -----------------------------------------------------------------------------
# Neo4j archive Cypher pin
# -----------------------------------------------------------------------------


def test_archive_cypher_persists_page_url():
    """Archive Cypher must SET d.page_url so Cypher filters can use it."""
    from adam.intelligence.decision_trace_neo4j import _ARCHIVE_CYPHER

    assert "d.page_url = $page_url" in _ARCHIVE_CYPHER, (
        "Archive Cypher dropped d.page_url — Cypher queries on the "
        "Neo4j archive will need to parse payload_json instead, which "
        "is slow + brittle."
    )


@pytest.mark.asyncio
async def test_archive_writer_passes_page_url():
    """archive_trace_to_neo4j must pass trace.page_url to the Cypher run."""
    from unittest.mock import AsyncMock, MagicMock

    from adam.intelligence.decision_trace_neo4j import archive_trace_to_neo4j

    captured = {}

    async def _capture_run(query, **kwargs):
        captured.update(kwargs)
        return MagicMock()

    fake_session = MagicMock()
    fake_session.run = _capture_run
    fake_session_cm = MagicMock()
    fake_session_cm.__aenter__ = AsyncMock(return_value=fake_session)
    fake_session_cm.__aexit__ = AsyncMock(return_value=None)
    fake_driver = MagicMock()
    fake_driver.session = MagicMock(return_value=fake_session_cm)

    trace = DecisionTrace(
        decision_id="dec_x",
        user_id="u_x",
        timestamp=datetime.now(timezone.utc),
        chosen_creative_id="cid_x",
        chosen_mechanism="curiosity",
        chosen_score=0.5,
        page_url="https://example.com/page",
    )

    await archive_trace_to_neo4j(trace, fake_driver)

    assert "page_url" in captured
    assert captured["page_url"] == "https://example.com/page"


@pytest.mark.asyncio
async def test_archive_writer_passes_none_when_no_page_url():
    """When the cascade had no page (anonymous bid), page_url=None
    flows through to the Cypher cleanly."""
    from unittest.mock import AsyncMock, MagicMock

    from adam.intelligence.decision_trace_neo4j import archive_trace_to_neo4j

    captured = {}

    async def _capture_run(query, **kwargs):
        captured.update(kwargs)
        return MagicMock()

    fake_session = MagicMock()
    fake_session.run = _capture_run
    fake_session_cm = MagicMock()
    fake_session_cm.__aenter__ = AsyncMock(return_value=fake_session)
    fake_session_cm.__aexit__ = AsyncMock(return_value=None)
    fake_driver = MagicMock()
    fake_driver.session = MagicMock(return_value=fake_session_cm)

    trace = DecisionTrace(
        decision_id="dec_x",
        user_id="u_x",
        timestamp=datetime.now(timezone.utc),
        chosen_creative_id="cid_x",
        chosen_mechanism="curiosity",
        chosen_score=0.5,
        # page_url omitted → None
    )

    await archive_trace_to_neo4j(trace, fake_driver)

    assert "page_url" in captured
    assert captured["page_url"] is None
