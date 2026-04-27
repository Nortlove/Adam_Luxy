"""Pin F1 + F2 daily runners that activate the F3 cascade wire.

Discipline anchors:
    - Soft-fail at every layer. Missing Neo4j / Claude API key /
      malformed reviews / scoring exceptions all return TaskResult
      with appropriate status, NEVER raise.
    - Skip-if-fresh gate prevents redundant Claude calls when a
      buyer's bundle already has confidence ≥ 0.5.
    - Per-run caps bound Claude API spend.
    - Tasks register cleanly in the scheduler (trip-wire on registration
      drift).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from adam.intelligence.brand_copy_metaphor_scoring import BrandCopyMetaphorBundle
from adam.intelligence.buyer_metaphor_scoring import BuyerMetaphorBundle
from adam.intelligence.daily.task_29_7_buyer_metaphor_scoring import (
    BuyerMetaphorScoringTask,
)
from adam.intelligence.daily.task_29_8_brand_metaphor_scoring import (
    BrandMetaphorScoringTask,
)
from adam.intelligence.pages.claude_feature_scoring import (
    PRIMARY_METAPHOR_AXIS_NAMES,
)


_NUM_AXES = len(PRIMARY_METAPHOR_AXIS_NAMES)


# =============================================================================
# Task identity / registration
# =============================================================================


def test_buyer_task_name_is_canonical():
    """Pin the canonical name string. Other systems may key on this
    (metrics, dashboard health endpoint, scheduler registry)."""
    assert BuyerMetaphorScoringTask().name == "buyer_metaphor_scoring"


def test_brand_task_name_is_canonical():
    assert BrandMetaphorScoringTask().name == "brand_metaphor_scoring"


def test_brand_task_runs_weekly():
    """F2 cadence: brand copy changes infrequently. Pin weekly
    cadence so a future refactor can't silently flip it to daily
    and burn Claude spend."""
    assert BrandMetaphorScoringTask().frequency_hours == 24 * 7


def test_buyer_task_runs_at_06_utc():
    """F1 cadence: 06:00 UTC, after nightly cascade fits."""
    assert BuyerMetaphorScoringTask().schedule_hours == [6]


def test_both_tasks_register_in_scheduler():
    """Trip-wire: F1 + F2 must remain registered. A future contributor
    deleting either registration is caught here."""
    import adam.intelligence.daily.scheduler as sched
    sched._task_registry = {}
    registry = sched.get_task_registry()
    task_names = {t.name for t in registry.values()} if isinstance(
        registry, dict,
    ) else {t.name for t in registry}
    assert "buyer_metaphor_scoring" in task_names
    assert "brand_metaphor_scoring" in task_names


# =============================================================================
# F1 (buyer) runner — soft-fail paths
# =============================================================================


@pytest.mark.asyncio
async def test_buyer_no_neo4j_driver_returns_failed():
    task = BuyerMetaphorScoringTask()
    with patch(
        "adam.core.dependencies.get_neo4j_driver",
        side_effect=ConnectionError("no neo4j"),
    ):
        result = await task.execute()
    assert result.success is False
    assert "neo4j" in result.details["error"].lower()


@pytest.mark.asyncio
async def test_buyer_no_api_key_returns_failed():
    task = BuyerMetaphorScoringTask()
    fake_client = MagicMock()
    fake_client.api_key = None
    with patch(
        "adam.core.dependencies.get_neo4j_driver",
        return_value=MagicMock(),
    ), patch(
        "adam.llm.client.ClaudeClient", return_value=fake_client,
    ):
        result = await task.execute()
    assert result.success is False
    assert "api_key" in result.details["error"].lower()


@pytest.mark.asyncio
async def test_buyer_no_reviews_returns_success_with_zero_processed():
    """Empty Neo4j result = 'no signal yet' = success. Pre-pilot phase
    is the canonical empty state."""
    task = BuyerMetaphorScoringTask()
    fake_driver = MagicMock()
    fake_session = MagicMock()
    fake_driver.session.return_value.__enter__ = MagicMock(return_value=fake_session)
    fake_driver.session.return_value.__exit__ = MagicMock(return_value=None)
    fake_session.run = MagicMock(return_value=[])
    fake_client = MagicMock()
    fake_client.api_key = "sk-test"

    with patch(
        "adam.core.dependencies.get_neo4j_driver", return_value=fake_driver,
    ), patch(
        "adam.llm.client.ClaudeClient", return_value=fake_client,
    ):
        result = await task.execute()
    assert result.success is True
    assert result.items_processed == 0


# =============================================================================
# F1 happy path — scores reviews + persists per-buyer bundle
# =============================================================================


def _review_record(buyer_id: str, text: str, review_id: str = "r1"):
    rec = MagicMock()
    rec.get = MagicMock(side_effect=lambda k:
        {"buyer_id": buyer_id, "text": text, "review_id": review_id}.get(k))
    return rec


@pytest.mark.asyncio
async def test_buyer_happy_path_scores_and_persists():
    task = BuyerMetaphorScoringTask()

    # Two reviews from same buyer
    records = [
        _review_record("b1", "Warm welcoming staff. Felt at home.", "r1"),
        _review_record("b1", "Felt close-knit and cared for.", "r2"),
    ]
    fake_driver = MagicMock()
    fake_session = MagicMock()
    fake_driver.session.return_value.__enter__ = MagicMock(return_value=fake_session)
    fake_driver.session.return_value.__exit__ = MagicMock(return_value=None)
    fake_session.run = MagicMock(return_value=records)

    fake_client = MagicMock()
    fake_client.api_key = "sk-test"
    fake_client.complete_structured = AsyncMock(return_value={
        "primary_metaphor": {
            "density": 0.6,
            "axes": {n: 0.5 for n in PRIMARY_METAPHOR_AXIS_NAMES},
            "confidence": 0.75,
        }
    })

    captured_bundles = []

    def fake_put(bundle, **kwargs):
        captured_bundles.append(bundle)
        return True

    with patch(
        "adam.core.dependencies.get_neo4j_driver", return_value=fake_driver,
    ), patch(
        "adam.llm.client.ClaudeClient", return_value=fake_client,
    ), patch(
        "adam.intelligence.metaphor_storage.get_buyer_metaphor_bundle",
        return_value=None,  # no existing fresh bundle
    ), patch(
        "adam.intelligence.metaphor_storage.put_buyer_metaphor_bundle",
        side_effect=fake_put,
    ):
        result = await task.execute()

    assert result.success is True
    assert result.items_processed == 1  # one buyer
    assert result.items_stored == 1
    assert len(captured_bundles) == 1
    assert captured_bundles[0].buyer_id == "b1"
    assert captured_bundles[0].confidence > 0


@pytest.mark.asyncio
async def test_buyer_skips_if_fresh_bundle_exists():
    """Fresh bundle exists (confidence ≥ 0.5) → skip Claude call."""
    task = BuyerMetaphorScoringTask()

    records = [_review_record("b1", "real review text", "r1")]
    fake_driver = MagicMock()
    fake_session = MagicMock()
    fake_driver.session.return_value.__enter__ = MagicMock(return_value=fake_session)
    fake_driver.session.return_value.__exit__ = MagicMock(return_value=None)
    fake_session.run = MagicMock(return_value=records)

    fake_client = MagicMock()
    fake_client.api_key = "sk-test"
    fake_client.complete_structured = AsyncMock(side_effect=AssertionError(
        "Claude must NOT be called when fresh bundle exists"
    ))

    fresh_bundle = BuyerMetaphorBundle(
        primary_metaphor_axes=[0.5] * _NUM_AXES,
        metaphor_density=0.5, confidence=0.7,  # ≥ 0.5 threshold
        buyer_id="b1",
    )

    with patch(
        "adam.core.dependencies.get_neo4j_driver", return_value=fake_driver,
    ), patch(
        "adam.llm.client.ClaudeClient", return_value=fake_client,
    ), patch(
        "adam.intelligence.metaphor_storage.get_buyer_metaphor_bundle",
        return_value=fresh_bundle,
    ):
        result = await task.execute()

    assert result.success is True
    assert result.details["buyers_skipped_fresh"] == 1
    assert result.details["buyers_scored"] == 0


@pytest.mark.asyncio
async def test_buyer_handles_scoring_exception_per_buyer():
    """One buyer's scoring exception doesn't crash the whole run.
    Other buyers still process; error count surfaces in details."""
    task = BuyerMetaphorScoringTask()

    records = [
        _review_record("b1", "good review text", "r1"),
        _review_record("b2", "another review", "r2"),
    ]
    fake_driver = MagicMock()
    fake_session = MagicMock()
    fake_driver.session.return_value.__enter__ = MagicMock(return_value=fake_session)
    fake_driver.session.return_value.__exit__ = MagicMock(return_value=None)
    fake_session.run = MagicMock(return_value=records)

    fake_client = MagicMock()
    fake_client.api_key = "sk-test"

    # First call raises; second succeeds
    call_count = {"n": 0}

    async def selective_score(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise RuntimeError("simulated scoring failure")
        return {
            "primary_metaphor": {
                "density": 0.5,
                "axes": {n: 0.5 for n in PRIMARY_METAPHOR_AXIS_NAMES},
                "confidence": 0.7,
            }
        }

    fake_client.complete_structured = AsyncMock(side_effect=selective_score)

    with patch(
        "adam.core.dependencies.get_neo4j_driver", return_value=fake_driver,
    ), patch(
        "adam.llm.client.ClaudeClient", return_value=fake_client,
    ), patch(
        "adam.intelligence.metaphor_storage.get_buyer_metaphor_bundle",
        return_value=None,
    ), patch(
        "adam.intelligence.metaphor_storage.put_buyer_metaphor_bundle",
        return_value=True,
    ):
        result = await task.execute()

    # Run completes (doesn't raise) and at least one buyer scored
    assert result.items_processed == 2


# =============================================================================
# F2 (brand) runner — soft-fail paths
# =============================================================================


@pytest.mark.asyncio
async def test_brand_no_neo4j_driver_returns_failed():
    task = BrandMetaphorScoringTask()
    with patch(
        "adam.core.dependencies.get_neo4j_driver",
        side_effect=ConnectionError("no neo4j"),
    ):
        result = await task.execute()
    assert result.success is False


@pytest.mark.asyncio
async def test_brand_no_api_key_returns_failed():
    task = BrandMetaphorScoringTask()
    fake_client = MagicMock()
    fake_client.api_key = None
    with patch(
        "adam.core.dependencies.get_neo4j_driver",
        return_value=MagicMock(),
    ), patch(
        "adam.llm.client.ClaudeClient", return_value=fake_client,
    ):
        result = await task.execute()
    assert result.success is False
    assert "api_key" in result.details["error"].lower()


@pytest.mark.asyncio
async def test_brand_no_products_returns_zero_processed():
    task = BrandMetaphorScoringTask()
    fake_driver = MagicMock()
    fake_session = MagicMock()
    fake_driver.session.return_value.__enter__ = MagicMock(return_value=fake_session)
    fake_driver.session.return_value.__exit__ = MagicMock(return_value=None)
    fake_session.run = MagicMock(return_value=[])
    fake_client = MagicMock()
    fake_client.api_key = "sk-test"
    with patch(
        "adam.core.dependencies.get_neo4j_driver", return_value=fake_driver,
    ), patch(
        "adam.llm.client.ClaudeClient", return_value=fake_client,
    ):
        result = await task.execute()
    assert result.success is True
    assert result.items_processed == 0


# =============================================================================
# F2 happy path — scores brand copy + persists
# =============================================================================


def _product_record(asin: str, title: str = "", description: str = ""):
    rec = MagicMock()
    rec.get = MagicMock(side_effect=lambda k:
        {"asin": asin, "title": title, "features": "",
         "description": description, "brand_id": "luxy"}.get(k))
    return rec


@pytest.mark.asyncio
async def test_brand_happy_path_scores_and_persists():
    task = BrandMetaphorScoringTask()

    records = [_product_record(
        "lux_luxy_ride",
        title="LUXY Ride: Bespoke chauffeur service",
        description="Discreet luxury for those who choose the journey",
    )]
    fake_driver = MagicMock()
    fake_session = MagicMock()
    fake_driver.session.return_value.__enter__ = MagicMock(return_value=fake_session)
    fake_driver.session.return_value.__exit__ = MagicMock(return_value=None)
    fake_session.run = MagicMock(return_value=records)

    fake_client = MagicMock()
    fake_client.api_key = "sk-test"
    fake_client.complete_structured = AsyncMock(return_value={
        "primary_metaphor": {
            "density": 0.7,
            "axes": {n: 0.6 for n in PRIMARY_METAPHOR_AXIS_NAMES},
            "confidence": 0.8,
        }
    })

    captured = []

    def fake_put(bundle, **kwargs):
        captured.append(bundle)
        return True

    with patch(
        "adam.core.dependencies.get_neo4j_driver", return_value=fake_driver,
    ), patch(
        "adam.llm.client.ClaudeClient", return_value=fake_client,
    ), patch(
        "adam.intelligence.metaphor_storage.get_brand_metaphor_bundle",
        return_value=None,
    ), patch(
        "adam.intelligence.metaphor_storage.put_brand_metaphor_bundle",
        side_effect=fake_put,
    ):
        result = await task.execute()

    assert result.success is True
    assert result.items_processed == 1
    assert result.items_stored == 1
    assert len(captured) == 1
    assert captured[0].asin == "lux_luxy_ride"
    assert captured[0].confidence > 0


@pytest.mark.asyncio
async def test_brand_skips_if_fresh_bundle_exists():
    task = BrandMetaphorScoringTask()

    records = [_product_record("lux_luxy_ride", title="LUXY")]
    fake_driver = MagicMock()
    fake_session = MagicMock()
    fake_driver.session.return_value.__enter__ = MagicMock(return_value=fake_session)
    fake_driver.session.return_value.__exit__ = MagicMock(return_value=None)
    fake_session.run = MagicMock(return_value=records)

    fake_client = MagicMock()
    fake_client.api_key = "sk-test"
    fake_client.complete_structured = AsyncMock(side_effect=AssertionError(
        "Claude must NOT be called for fresh bundle"
    ))

    fresh_bundle = BrandCopyMetaphorBundle(
        primary_metaphor_axes=[0.5] * _NUM_AXES,
        metaphor_density=0.5, confidence=0.6,
        asin="lux_luxy_ride", brand_id="luxy",
    )

    with patch(
        "adam.core.dependencies.get_neo4j_driver", return_value=fake_driver,
    ), patch(
        "adam.llm.client.ClaudeClient", return_value=fake_client,
    ), patch(
        "adam.intelligence.metaphor_storage.get_brand_metaphor_bundle",
        return_value=fresh_bundle,
    ):
        result = await task.execute()

    assert result.success is True
    assert result.details["brands_skipped_fresh"] == 1
    assert result.details["brands_scored"] == 0
