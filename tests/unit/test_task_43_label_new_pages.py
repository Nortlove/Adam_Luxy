"""Pin Task 43 — daily Claude API label generation for new DecisionTrace pages.

Original-Slice-B closes the autonomous label-accumulation loop:

    Day N — production cascade emits DecisionTraces with page_url
    Day N 02:00 UTC — Task 43 fires (this task)
    Day N 03:00 UTC — Task 40 retrains on the larger labeled set

Tests pin:
    * Task name + schedule (02 UTC daily, before Task 40 at 03)
    * No-driver path → skipped (not failure)
    * No-new-pages path → success with outcome=no_new_pages
    * Unconfigured generator (no API key) → skipped without failing
    * Pages found + labels generated → labels persisted
    * scan Cypher uses page_url IS NOT NULL filter (no payload_json
      parsing) — depends on Original-Slice-A's first-class field
    * scan Cypher excludes already-labeled URLs (no double-labeling)
    * Task registered in scheduler
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from adam.intelligence.daily.task_43_label_new_pages import (
    LabelNewPagesTask,
    _SCAN_NEW_PAGES_CYPHER,
)


# -----------------------------------------------------------------------------
# Schedule contract + registration
# -----------------------------------------------------------------------------


def test_task_name():
    task = LabelNewPagesTask()
    assert task.name == "label_new_pages"


def test_schedule_02_utc_before_task_40():
    """02 UTC slot — before Task 40 (03:00) so retrain sees new labels."""
    task = LabelNewPagesTask()
    assert task.schedule_hours == [2]
    assert task.frequency_hours == 24


def test_task_registered_in_scheduler():
    from adam.intelligence.daily.scheduler import (
        _register_all_tasks,
        get_task_registry,
    )
    _register_all_tasks()
    registry = get_task_registry()
    assert "label_new_pages" in registry


# -----------------------------------------------------------------------------
# Scan Cypher contract pins
# -----------------------------------------------------------------------------


def test_scan_cypher_filters_on_first_class_page_url():
    """The scan must use d.page_url (Original-Slice-A's first-class
    scalar) — not parse payload_json. Verified by direct field reference.
    """
    assert "d.page_url" in _SCAN_NEW_PAGES_CYPHER
    assert "payload_json" not in _SCAN_NEW_PAGES_CYPHER
    # Filter excludes empty / null values
    assert "IS NOT NULL" in _SCAN_NEW_PAGES_CYPHER


def test_scan_cypher_excludes_already_labeled_urls():
    """Anti-double-labeling — the scan must filter out URLs that
    already have a :GoalStateLabel."""
    # Either a NOT EXISTS pattern or a left-anti-join — accept either.
    assert (
        "NOT EXISTS" in _SCAN_NEW_PAGES_CYPHER
        or "OPTIONAL MATCH" in _SCAN_NEW_PAGES_CYPHER
    )
    assert "GoalStateLabel" in _SCAN_NEW_PAGES_CYPHER


def test_scan_cypher_returns_distinct():
    """Many traces may share the same page_url — DISTINCT prevents
    duplicate labeling for the same URL within a single run."""
    assert "DISTINCT" in _SCAN_NEW_PAGES_CYPHER


def test_scan_cypher_has_lookback_cutoff():
    """Cutoff parameter caps the scan to a recent window."""
    assert "$cutoff_ts" in _SCAN_NEW_PAGES_CYPHER
    assert "d.timestamp" in _SCAN_NEW_PAGES_CYPHER


def test_scan_cypher_has_limit():
    """Limit parameter caps the per-run page count."""
    assert "$limit" in _SCAN_NEW_PAGES_CYPHER
    assert "LIMIT" in _SCAN_NEW_PAGES_CYPHER


# -----------------------------------------------------------------------------
# Soft-fail paths
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_no_driver_skipped():
    task = LabelNewPagesTask()
    with patch(
        "adam.core.dependencies.get_infrastructure",
        new=AsyncMock(return_value=MagicMock(neo4j_driver=None, neo4j=None)),
    ):
        result = await task.execute()
    assert result.success is True
    assert result.details.get("skipped") == "no_neo4j_driver"


@pytest.mark.asyncio
async def test_no_new_pages_succeeds_with_cold_start_outcome():
    """Empty scan → success with outcome=no_new_pages."""
    task = LabelNewPagesTask()
    fake_driver = _fake_driver_returning_pages([])
    fake_infra = MagicMock(neo4j_driver=fake_driver, neo4j=fake_driver)
    with patch(
        "adam.core.dependencies.get_infrastructure",
        new=AsyncMock(return_value=fake_infra),
    ):
        result = await task.execute()
    assert result.success is True
    assert result.details.get("outcome") == "no_new_pages"
    assert result.details.get("n_new_pages") == 0


@pytest.mark.asyncio
async def test_unconfigured_generator_skipped_not_failure():
    """No ANTHROPIC_API_KEY → skipped without failing the task."""
    task = LabelNewPagesTask()
    fake_driver = _fake_driver_returning_pages(
        ["https://example.com/page1"]
    )
    fake_infra = MagicMock(neo4j_driver=fake_driver, neo4j=fake_driver)

    with patch(
        "adam.core.dependencies.get_infrastructure",
        new=AsyncMock(return_value=fake_infra),
    ), patch(
        "adam.intelligence.goal_state_label_generator."
        "GoalStateLabelGenerator.is_configured",
        return_value=False,
    ):
        result = await task.execute()

    assert result.success is True
    assert result.details.get("outcome") == "skipped_unconfigured"
    assert result.details.get("n_new_pages") == 1


# -----------------------------------------------------------------------------
# Happy path — labels generated and persisted
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_labels_generated_and_persisted():
    """Pages scanned + labels generated + persisted → details surface counts."""
    from adam.intelligence.goal_state_label_generator import GoalStateLabel

    task = LabelNewPagesTask()
    fake_driver = _fake_driver_returning_pages([
        "https://example.com/p1",
        "https://example.com/p2",
    ])
    fake_infra = MagicMock(neo4j_driver=fake_driver, neo4j=fake_driver)

    fake_labels = [
        GoalStateLabel(
            label_id=f"label-{i}",
            page_url=f"https://example.com/p{i+1}",
            page_features={},
            active_goal_state_ids=["commute_readiness"],
            confidence=0.85,
        )
        for i in range(2)
    ]

    with patch(
        "adam.core.dependencies.get_infrastructure",
        new=AsyncMock(return_value=fake_infra),
    ), patch(
        "adam.intelligence.goal_state_label_generator."
        "GoalStateLabelGenerator.is_configured",
        return_value=True,
    ), patch(
        "adam.intelligence.goal_state_label_generator."
        "GoalStateLabelGenerator.generate_labels_bulk",
        return_value=fake_labels,
    ), patch(
        "adam.intelligence.goal_state_label_generator."
        "persist_label_to_neo4j",
        new=AsyncMock(return_value=True),
    ):
        result = await task.execute()

    assert result.success is True
    assert result.details["n_new_pages"] == 2
    assert result.details["n_labels_generated"] == 2
    assert result.details["n_labels_persisted"] == 2
    assert result.details["outcome"] == "persisted"
    assert result.items_processed == 2
    assert result.items_stored == 2


# -----------------------------------------------------------------------------
# Test helper — fake driver returning a page list
# -----------------------------------------------------------------------------


def _fake_driver_returning_pages(page_urls):
    """Build a driver whose session.run yields records with .get('page_url')."""
    fake_records = []
    for url in page_urls:
        rec = MagicMock()
        rec.get = MagicMock(return_value=url)
        fake_records.append(rec)

    class _FakeAsyncIterator:
        def __init__(self, items):
            self._items = list(items)
            self._idx = 0

        def __aiter__(self):
            return self

        async def __anext__(self):
            if self._idx >= len(self._items):
                raise StopAsyncIteration
            item = self._items[self._idx]
            self._idx += 1
            return item

    fake_session = MagicMock()
    fake_session.run = AsyncMock(return_value=_FakeAsyncIterator(fake_records))

    fake_session_cm = MagicMock()
    fake_session_cm.__aenter__ = AsyncMock(return_value=fake_session)
    fake_session_cm.__aexit__ = AsyncMock(return_value=None)

    fake_driver = MagicMock()
    fake_driver.session = MagicMock(return_value=fake_session_cm)
    return fake_driver
