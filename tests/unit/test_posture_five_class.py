"""Pin Slice 22 — Phase 2 5-class posture taxonomy + labeling schema.

Per directive lines 173-180 + line 967-969 (Phase 2 deliverable).
Slice 22 ships the SCHEMA + LABELING substrate; trained head is
multi-session sibling.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock

import pytest

from adam.intelligence.posture_five_class import (
    ATTENTIONAL_SIGNATURE,
    BRIDGE_CONFIDENCE,
    BRIDGE_THREE_TO_FIVE,
    FIVE_CLASS_POSTURES,
    POSTURE_INFORMATION_FORAGING,
    POSTURE_LEISURE_BROWSING,
    POSTURE_SOCIAL_CONSUMPTION,
    POSTURE_TASK_COMPLETION,
    POSTURE_TRANSACTIONAL_COMPARISON,
    PageLabelEntry,
    PostureDistribution,
    bridge_three_to_five_class,
    count_labels_corpus,
    load_labeled_pages,
    one_hot_from_label,
    persist_page_label,
)


# -----------------------------------------------------------------------------
# Canonical 5-class enumeration
# -----------------------------------------------------------------------------


def test_five_canonical_classes_match_directive():
    """Directive lines 173-180 enumerate exactly these 5."""
    expected = {
        "INFORMATION_FORAGING",
        "TASK_COMPLETION",
        "LEISURE_BROWSING",
        "SOCIAL_CONSUMPTION",
        "TRANSACTIONAL_COMPARISON",
    }
    assert set(FIVE_CLASS_POSTURES) == expected
    assert len(FIVE_CLASS_POSTURES) == 5


def test_attentional_signatures_provided_for_every_class():
    """The partner-facing 'why' vocabulary requires a description
    per class (directive line 178)."""
    for cls in FIVE_CLASS_POSTURES:
        assert cls in ATTENTIONAL_SIGNATURE
        assert len(ATTENTIONAL_SIGNATURE[cls]) > 30  # non-trivial


def test_individual_class_constants_match_tuple():
    """Module-level constants align with the canonical tuple."""
    assert POSTURE_INFORMATION_FORAGING in FIVE_CLASS_POSTURES
    assert POSTURE_TASK_COMPLETION in FIVE_CLASS_POSTURES
    assert POSTURE_LEISURE_BROWSING in FIVE_CLASS_POSTURES
    assert POSTURE_SOCIAL_CONSUMPTION in FIVE_CLASS_POSTURES
    assert POSTURE_TRANSACTIONAL_COMPARISON in FIVE_CLASS_POSTURES


# -----------------------------------------------------------------------------
# Bridge from 3-state substrate
# -----------------------------------------------------------------------------


def test_bridge_three_state_returns_valid_5class():
    """Every 3-state input maps to a valid 5-class label."""
    for three_class in (
        "blend_compatible", "vigilance_activating", "neutral", "unknown",
    ):
        five, conf = bridge_three_to_five_class(three_class)
        assert five in FIVE_CLASS_POSTURES
        assert 0.0 <= conf <= 1.0


def test_bridge_confidence_capped_at_low():
    """The bridge confidence ceiling is BRIDGE_CONFIDENCE — operator
    should not trust the bridge for high-precision decisions."""
    five, conf = bridge_three_to_five_class("blend_compatible")
    assert conf <= BRIDGE_CONFIDENCE


def test_bridge_confidence_clamped_by_input():
    """Lower input confidence → lower bridge confidence (never exceeds
    the input)."""
    five, conf = bridge_three_to_five_class(
        "blend_compatible", three_class_confidence=0.10,
    )
    assert conf <= 0.10


def test_bridge_unknown_input_returns_default():
    """Unrecognized 3-state label → default 5-class fallback."""
    five, conf = bridge_three_to_five_class("not_a_3state_label")
    assert five in FIVE_CLASS_POSTURES


def test_bridge_vigilance_maps_to_research_or_comparison():
    """Vigilance-activating posture → research or comparison
    semantically (directive's vigilance attentional signature)."""
    five, _ = bridge_three_to_five_class("vigilance_activating")
    assert five in (
        POSTURE_INFORMATION_FORAGING,
        POSTURE_TRANSACTIONAL_COMPARISON,
    )


# -----------------------------------------------------------------------------
# PostureDistribution + one_hot_from_label
# -----------------------------------------------------------------------------


def test_one_hot_distribution_sums_to_one():
    """One-hot distribution at any class sums to 1.0."""
    for cls in FIVE_CLASS_POSTURES:
        dist = one_hot_from_label(cls)
        total = sum(dist.as_vector())
        assert total == pytest.approx(1.0)


def test_one_hot_argmax_returns_label():
    """argmax on one-hot at class C returns C."""
    for cls in FIVE_CLASS_POSTURES:
        dist = one_hot_from_label(cls)
        assert dist.argmax_class() == cls


def test_one_hot_unknown_label_returns_uniform():
    """Unrecognized label → uniform 1/5 distribution."""
    dist = one_hot_from_label("not_a_class")
    vec = dist.as_vector()
    for v in vec:
        assert v == pytest.approx(0.20)


def test_distribution_argmax_picks_max_class():
    dist = PostureDistribution(
        information_foraging=0.10,
        task_completion=0.50,
        leisure_browsing=0.10,
        social_consumption=0.20,
        transactional_comparison=0.10,
    )
    assert dist.argmax_class() == POSTURE_TASK_COMPLETION


def test_distribution_frozen():
    dist = one_hot_from_label(POSTURE_LEISURE_BROWSING)
    with pytest.raises((AttributeError, Exception)):
        dist.task_completion = 0.99  # type: ignore[misc]


def test_distribution_vector_ordering_matches_tuple():
    """as_vector() returns components in the order of
    FIVE_CLASS_POSTURES — required by downstream cascade consumers."""
    dist = PostureDistribution(
        information_foraging=0.1,
        task_completion=0.2,
        leisure_browsing=0.3,
        social_consumption=0.4,
        transactional_comparison=0.0,
    )
    vec = dist.as_vector()
    assert vec[0] == 0.1  # INFORMATION_FORAGING is first per tuple
    assert vec[1] == 0.2  # TASK_COMPLETION
    assert vec[2] == 0.3  # LEISURE_BROWSING
    assert vec[3] == 0.4  # SOCIAL_CONSUMPTION
    assert vec[4] == 0.0  # TRANSACTIONAL_COMPARISON


# -----------------------------------------------------------------------------
# PageLabelEntry validation
# -----------------------------------------------------------------------------


def test_page_label_entry_validates_canonical_label():
    entry = PageLabelEntry(
        url="https://luxy.example/blog",
        label="LEISURE_BROWSING",
    )
    assert entry.label == POSTURE_LEISURE_BROWSING


def test_page_label_entry_normalizes_case():
    entry = PageLabelEntry(
        url="https://x", label="leisure_browsing",
    )
    assert entry.label == POSTURE_LEISURE_BROWSING


def test_page_label_entry_rejects_non_canonical_label():
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        PageLabelEntry(url="https://x", label="not_a_class")


def test_page_label_entry_rejects_extra_fields():
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        PageLabelEntry(
            url="https://x",
            label=POSTURE_LEISURE_BROWSING,
            unknown_field=42,  # type: ignore[call-arg]
        )


def test_page_label_entry_confidence_range():
    """confidence ∈ [0, 1]."""
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        PageLabelEntry(
            url="https://x", label=POSTURE_LEISURE_BROWSING,
            confidence=1.5,
        )


# -----------------------------------------------------------------------------
# Persistence round-trip (with fakes)
# -----------------------------------------------------------------------------


class _FakeRecord:
    def __init__(self, data: Dict[str, Any]) -> None:
        self._data = data

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)


class _FakeAsyncResult:
    def __init__(self, rows: List[Dict[str, Any]]) -> None:
        self._rows = list(rows)

    async def single(self) -> Optional[_FakeRecord]:
        return _FakeRecord(self._rows[0]) if self._rows else None

    async def data(self) -> List[Dict[str, Any]]:
        return list(self._rows)


class _FakeAsyncSession:
    def __init__(self, driver):
        self._driver = driver

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return None

    async def run(self, cypher: str, **params: Any) -> _FakeAsyncResult:
        self._driver.calls.append((cypher, dict(params)))
        if cypher.strip().startswith("MERGE (l:PostureLabel"):
            self._driver.records[params["url"]] = dict(params)
            return _FakeAsyncResult([])
        if "RETURN count(l)" in cypher:
            n = len(self._driver.records)
            classes = {r["label"] for r in self._driver.records.values()}
            return _FakeAsyncResult([
                {"n_labels": n, "n_classes_covered": len(classes)}
            ])
        if "RETURN l.url" in cypher:
            rows = list(self._driver.records.values())
            rows.sort(key=lambda r: r.get("labeled_at_ts", 0.0), reverse=True)
            return _FakeAsyncResult(rows[:int(params.get("limit", 1000))])
        return _FakeAsyncResult([])


class _FakeDriver:
    def __init__(self):
        self.records: Dict[str, Dict[str, Any]] = {}
        self.calls: List = []

    def session(self):
        return _FakeAsyncSession(self)


@pytest.mark.asyncio
async def test_persist_page_label_no_driver_returns_false():
    entry = PageLabelEntry(
        url="https://x", label=POSTURE_LEISURE_BROWSING,
    )
    assert await persist_page_label(entry, driver=None) is False


@pytest.mark.asyncio
async def test_persist_load_round_trip():
    driver = _FakeDriver()
    entry = PageLabelEntry(
        url="https://luxy.example/comparison",
        label=POSTURE_TRANSACTIONAL_COMPARISON,
        labeler="chris",
        notes="head-to-head review page",
    )
    assert await persist_page_label(entry, driver=driver) is True
    loaded = await load_labeled_pages(driver, limit=10)
    assert len(loaded) == 1
    assert loaded[0].url == "https://luxy.example/comparison"
    assert loaded[0].label == POSTURE_TRANSACTIONAL_COMPARISON
    assert loaded[0].labeler == "chris"


@pytest.mark.asyncio
async def test_persist_idempotent_on_url():
    driver = _FakeDriver()
    e1 = PageLabelEntry(url="https://x", label=POSTURE_LEISURE_BROWSING)
    e2 = PageLabelEntry(url="https://x", label=POSTURE_TASK_COMPLETION)
    await persist_page_label(e1, driver=driver)
    await persist_page_label(e2, driver=driver)
    # Same URL → MERGE updates in place; only one record.
    loaded = await load_labeled_pages(driver, limit=10)
    assert len(loaded) == 1
    assert loaded[0].label == POSTURE_TASK_COMPLETION


@pytest.mark.asyncio
async def test_count_labels_corpus_no_driver_returns_zeros():
    out = await count_labels_corpus(driver=None)
    assert out == {"n_labels": 0, "n_classes_covered": 0}


@pytest.mark.asyncio
async def test_count_labels_corpus_returns_totals():
    driver = _FakeDriver()
    await persist_page_label(
        PageLabelEntry(url="a", label=POSTURE_LEISURE_BROWSING),
        driver=driver,
    )
    await persist_page_label(
        PageLabelEntry(url="b", label=POSTURE_TASK_COMPLETION),
        driver=driver,
    )
    await persist_page_label(
        PageLabelEntry(url="c", label=POSTURE_TASK_COMPLETION),
        driver=driver,
    )
    out = await count_labels_corpus(driver=driver)
    assert out["n_labels"] == 3
    assert out["n_classes_covered"] == 2
