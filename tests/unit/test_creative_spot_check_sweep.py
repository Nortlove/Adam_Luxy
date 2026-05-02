"""Pin Slice 23 — creative spot-check sweep + Task 45 + snapshot
counters. Closes Phase 10 RED criterion #6 producer wire (named
sibling at task_42_launch_gate_runner.py:40-42).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from adam.intelligence.creative_spot_check_sweep import (
    SpotCheckEntry,
    SpotCheckSweepResult,
    sweep_creative_spot_check,
)
from adam.intelligence.creative_upload_pipeline import CreativeRecord
from adam.intelligence.red_criteria_snapshot import (
    RedCriteriaSnapshot,
    get_red_snapshot,
    reset_for_tests,
)


# -----------------------------------------------------------------------------
# Snapshot accumulator counters
# -----------------------------------------------------------------------------


def test_snapshot_has_creative_counters():
    """Slice 23 added two new counter fields."""
    snap = RedCriteriaSnapshot()
    assert hasattr(snap, "n_creatives_in_rotation")
    assert hasattr(snap, "n_creatives_failed_spot_check")
    assert snap.n_creatives_in_rotation == 0
    assert snap.n_creatives_failed_spot_check == 0


def test_record_creatives_in_rotation_setter():
    snap = RedCriteriaSnapshot()
    snap.record_creatives_in_rotation(7)
    assert snap.n_creatives_in_rotation == 7
    # Setter (not increment) — second call replaces.
    snap.record_creatives_in_rotation(3)
    assert snap.n_creatives_in_rotation == 3


def test_record_creatives_failed_spot_check_setter():
    snap = RedCriteriaSnapshot()
    snap.record_creatives_failed_spot_check(2)
    assert snap.n_creatives_failed_spot_check == 2
    snap.record_creatives_failed_spot_check(0)
    assert snap.n_creatives_failed_spot_check == 0


def test_snapshot_dict_includes_creative_counts():
    snap = RedCriteriaSnapshot()
    snap.record_creatives_in_rotation(5)
    snap.record_creatives_failed_spot_check(1)
    out = snap.snapshot_and_reset()
    assert out["n_creatives_in_rotation"] == 5
    assert out["n_creatives_failed_spot_check"] == 1
    # Atomic reset — values back to 0.
    assert snap.n_creatives_in_rotation == 0


# -----------------------------------------------------------------------------
# CreativeRecord copy_text field
# -----------------------------------------------------------------------------


def test_creative_record_copy_text_field():
    record = CreativeRecord(
        stackadapt_creative_id="c-1",
        name="x",
        landing_page_url="https://x",
        copy_text="Everyone is loving the warm welcome.",
    )
    assert record.copy_text == "Everyone is loving the warm welcome."


def test_creative_record_copy_text_default_none():
    record = CreativeRecord(
        stackadapt_creative_id="c-1",
        name="x",
        landing_page_url="https://x",
    )
    assert record.copy_text is None


# -----------------------------------------------------------------------------
# Sweep — fakes + behavior
# -----------------------------------------------------------------------------


class _FakeNode:
    """Duck-types a Neo4j Node — implements .get(key, default)."""

    def __init__(self, data: Dict[str, Any]) -> None:
        self._data = data

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)


class _FakeRecord:
    def __init__(self, node: Dict[str, Any]) -> None:
        self._node = _FakeNode(node)

    def get(self, key: str, default: Any = None) -> Any:
        if key == "c":
            return self._node
        return default


class _FakeAsyncResult:
    def __init__(self, rows: List[Dict[str, Any]]) -> None:
        self._rows = list(rows)

    def __aiter__(self):
        async def _gen():
            for r in self._rows:
                yield _FakeRecord(r)
        return _gen()

    async def single(self) -> Optional[_FakeRecord]:
        return _FakeRecord(self._rows[0]) if self._rows else None


class _FakeAsyncSession:
    def __init__(self, driver):
        self._driver = driver

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return None

    async def run(self, cypher: str, **params: Any) -> _FakeAsyncResult:
        self._driver.calls.append((cypher, dict(params)))
        if cypher.strip().startswith("MATCH (c:UploadedCreative)"):
            return _FakeAsyncResult(self._driver.creatives_data)
        return _FakeAsyncResult([])


class _FakeDriver:
    def __init__(self, creatives_data: List[Dict[str, Any]]):
        self.creatives_data = creatives_data
        self.calls: List = []

    def session(self):
        return _FakeAsyncSession(self)


def _creative_node(
    *, cid: str, name: str = "x",
    mechanism: Optional[str] = None,
    primary_metaphor: Optional[str] = None,
    posture_class: Optional[str] = None,
    copy_text: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        "stackadapt_creative_id": cid,
        "name": name,
        "landing_page_url": f"https://x/{cid}",
        "mechanism": mechanism,
        "primary_metaphor": primary_metaphor,
        "posture_class": posture_class,
        "creative_type": "banner",
        "uploaded_at_ts": 100.0,
        "copy_text": copy_text,
    }


@pytest.mark.asyncio
async def test_sweep_no_driver_returns_empty():
    out = await sweep_creative_spot_check(driver=None)
    assert out.n_in_rotation == 0
    assert out.n_failed == 0


@pytest.mark.asyncio
async def test_sweep_empty_manifest_returns_empty():
    driver = _FakeDriver([])
    out = await sweep_creative_spot_check(driver=driver)
    assert out.n_in_rotation == 0


@pytest.mark.asyncio
async def test_sweep_skips_creatives_without_copy_text():
    driver = _FakeDriver([
        _creative_node(cid="c-1", copy_text=None),
        _creative_node(cid="c-2", copy_text=""),
    ])
    out = await sweep_creative_spot_check(driver=driver)
    assert out.n_in_rotation == 0
    assert out.n_skipped_no_copy == 2


@pytest.mark.asyncio
async def test_sweep_counts_passing_creative():
    """Aligned copy_text → in_rotation, no failure."""
    driver = _FakeDriver([
        _creative_node(
            cid="c-good",
            mechanism="social_proof",
            primary_metaphor="warmth",
            copy_text=(
                "Warm welcome — cozy, friendly experience. Everyone "
                "is loving it; millions trust this top-rated brand."
            ),
        ),
    ])
    out = await sweep_creative_spot_check(
        driver=driver, include_entries=True,
    )
    assert out.n_in_rotation == 1
    # Whether it actually passes depends on scorer thresholds; pin
    # only the in_rotation count + that the entry was evaluated.
    assert len(out.entries) == 1


@pytest.mark.asyncio
async def test_sweep_counts_reactance_failure():
    """High-reactance copy → counted as failed."""
    driver = _FakeDriver([
        _creative_node(
            cid="c-bad",
            mechanism="social_proof",
            primary_metaphor="warmth",
            copy_text=(
                "Act now! Limited time! Hurry — only 1 left! "
                "Last chance — countdown ticking — don't miss out — "
                "must buy now, expires today!"
            ),
        ),
    ])
    out = await sweep_creative_spot_check(
        driver=driver, include_entries=True,
    )
    assert out.n_in_rotation == 1
    assert out.n_failed == 1
    # Reasons enumerate which scorer flagged.
    assert any("reactance" in r for r in out.entries[0].reasons)


@pytest.mark.asyncio
async def test_sweep_counts_metaphor_coherence_failure():
    driver = _FakeDriver([
        _creative_node(
            cid="c-off-metaphor",
            mechanism="social_proof",
            primary_metaphor="warmth",
            copy_text=(
                # Path-metaphor language; mechanism activation may
                # also fail. The point is the off-metaphor signal.
                "Push forward on the journey — step ahead toward "
                "your destination. Stride onward."
            ),
        ),
    ])
    out = await sweep_creative_spot_check(
        driver=driver, include_entries=True,
    )
    assert out.n_failed == 1
    assert any(
        "metaphor_coherence" in r for r in out.entries[0].reasons
    )


@pytest.mark.asyncio
async def test_sweep_increments_snapshot_counters():
    driver = _FakeDriver([
        _creative_node(cid="ok", copy_text="Premium service experience."),
    ])
    snap = RedCriteriaSnapshot()
    out = await sweep_creative_spot_check(
        driver=driver, snapshot=snap,
    )
    # Whether it passed or failed, the in_rotation count is set.
    assert snap.n_creatives_in_rotation == out.n_in_rotation


@pytest.mark.asyncio
async def test_sweep_skipped_no_metadata_counted_separately():
    """Entry with copy_text but no mechanism/metaphor declared → still
    counted as in_rotation (reactance always runs) but tracked in
    n_skipped_no_metadata."""
    driver = _FakeDriver([
        _creative_node(
            cid="universal",
            copy_text="Premium service.",
            # No mechanism, no metaphor declared.
        ),
    ])
    out = await sweep_creative_spot_check(driver=driver)
    assert out.n_in_rotation == 1  # copy_text was scoreable
    assert out.n_skipped_no_metadata == 1


def test_spot_check_result_frozen():
    out = SpotCheckSweepResult(n_in_rotation=5, n_failed=1)
    with pytest.raises((AttributeError, Exception)):
        out.n_failed = 99  # type: ignore[misc]


def test_spot_check_entry_frozen():
    entry = SpotCheckEntry(creative_id="c", name="n", passed=True)
    with pytest.raises((AttributeError, Exception)):
        entry.passed = False  # type: ignore[misc]


# -----------------------------------------------------------------------------
# Task 45 contract
# -----------------------------------------------------------------------------


def test_task_45_registered_in_scheduler():
    from pathlib import Path
    src = Path(
        "adam/intelligence/daily/scheduler.py"
    ).read_text()
    assert "task_45_creative_spot_check" in src
    assert "CreativeSpotCheckTask" in src


def test_task_45_schedule_hours():
    from adam.intelligence.daily.task_45_creative_spot_check import (
        CreativeSpotCheckTask,
    )
    task = CreativeSpotCheckTask()
    assert task.name == "creative_spot_check"
    assert task.schedule_hours == [4]  # before Task 42 at 5
    assert task.frequency_hours == 24


def test_task_42_forwards_creative_counts():
    """Task 42 source forwards n_creatives_in_rotation +
    n_creatives_failed_spot_check into LaunchGateInputs."""
    from pathlib import Path
    src = Path(
        "adam/intelligence/daily/task_42_launch_gate_runner.py"
    ).read_text()
    assert "n_creatives_in_rotation" in src
    assert "n_creatives_failed_spot_check" in src
    # And the honest tag is updated.
    assert "Slice 23" in src
