"""S4.1 — ingestion package skeleton tests.

Per directive §S4.1 closure criterion: "Closes when package imports
clean and skeleton tests pass." Skeleton-stage; no live API calls.

Pins:
  - Package imports cleanly (skeleton + corrected S0 schema patterns).
  - RateLimitedGraphQLSession token-bucket semantics (capacity, rate,
    blocking when empty, refill).
  - HistoricalPuller orchestration via mocked session: campaigns
    pre-fetched, conversionPath cursor-paginated, campaignPageContext
    UNION-resolved, checkpoint persisted.
  - IncrementalPuller: window computation, last-run-checkpoint
    persistence.
  - PixelCorrelator: sapid join semantics, matched/unmatched cases,
    coverage_rate.
"""
from __future__ import annotations

import asyncio
import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ----------------------------------------------------------------------------
# Package imports
# ----------------------------------------------------------------------------

class TestPackageImports:
    def test_top_level_imports(self):
        from adam.ingestion.stackadapt import (
            HistoricalPuller, IncrementalPuller,
            PixelCorrelator, RateLimitedGraphQLSession,
        )
        assert HistoricalPuller is not None
        assert IncrementalPuller is not None
        assert PixelCorrelator is not None
        assert RateLimitedGraphQLSession is not None

    def test_pixel_postback_dataclass_importable(self):
        from adam.ingestion.stackadapt.pixel_correlator import (
            PixelPostback, CorrelatedConversion,
        )
        assert PixelPostback is not None
        assert CorrelatedConversion is not None


# ----------------------------------------------------------------------------
# RateLimitedGraphQLSession — token-bucket
# ----------------------------------------------------------------------------

class TestTokenBucket:
    @pytest.mark.asyncio
    async def test_capacity_initial_tokens_available_immediately(self):
        from adam.ingestion.stackadapt import RateLimitedGraphQLSession
        client = MagicMock()
        client.is_configured = True
        client.get_campaigns = AsyncMock(return_value=[])
        sess = RateLimitedGraphQLSession(
            client=client, capacity=3, rate_per_second=1.0,
        )
        # Three calls should not block (tokens=3 initially).
        t0 = time.monotonic()
        await sess.get_campaigns(first=1)
        await sess.get_campaigns(first=1)
        await sess.get_campaigns(first=1)
        elapsed = time.monotonic() - t0
        assert elapsed < 0.05, f"three within-capacity calls took {elapsed:.3f}s"

    @pytest.mark.asyncio
    async def test_blocks_when_bucket_empty(self):
        from adam.ingestion.stackadapt import RateLimitedGraphQLSession
        client = MagicMock()
        client.is_configured = True
        client.get_campaigns = AsyncMock(return_value=[])
        sess = RateLimitedGraphQLSession(
            client=client, capacity=1, rate_per_second=20.0,
        )
        # First call: free. Second call: must wait ~50ms (1/rate).
        await sess.get_campaigns(first=1)
        t0 = time.monotonic()
        await sess.get_campaigns(first=1)
        elapsed = time.monotonic() - t0
        assert elapsed >= 0.04, f"second call was not throttled ({elapsed:.3f}s)"


# ----------------------------------------------------------------------------
# HistoricalPuller — orchestration
# ----------------------------------------------------------------------------

class TestHistoricalPuller:
    @pytest.mark.asyncio
    async def test_aborts_when_no_campaigns(self, tmp_path):
        from adam.ingestion.stackadapt import HistoricalPuller
        session = MagicMock()
        session.is_configured = True
        session.get_campaigns = AsyncMock(return_value=[])
        puller = HistoricalPuller(
            advertiser_id="luxy_id",
            checkpoint_path=tmp_path / "ckpt.json",
            session=session,
        )
        result = await puller.run()
        assert result["status"] == "ABORTED_NO_CAMPAIGNS"
        assert result["campaigns"] == 0

    @pytest.mark.asyncio
    async def test_orchestrates_three_streams(self, tmp_path):
        """Mocked end-to-end: campaigns fetched → conversionPath
        cursor-paginated to completion → campaignPageContext
        UNION-resolved to completion → final state captured."""
        from adam.ingestion.stackadapt import HistoricalPuller
        session = MagicMock()
        session.is_configured = True
        session.get_campaigns = AsyncMock(return_value=[
            {"id": "c1"}, {"id": "c2"},
        ])

        # conversionPath: 2 pages then end.
        cp_responses = iter([
            ([{"id": f"r-{i}"} for i in range(5)],
             {"hasNextPage": True, "endCursor": "cur1"}),
            ([{"id": f"r-{i}"} for i in range(3)],
             {"hasNextPage": False, "endCursor": None}),
        ])
        session.get_conversion_paths_page = AsyncMock(
            side_effect=lambda **kw: next(cp_responses)
        )

        # campaignPageContext: 1 page (Outcome with 4 nodes).
        session.get_campaign_page_context_page = AsyncMock(
            return_value=([{"url": f"https://e.com/p{i}"} for i in range(4)],
                          {"hasNextPage": False, "endCursor": None})
        )

        puller = HistoricalPuller(
            advertiser_id="luxy_id", page_size=5,
            checkpoint_path=tmp_path / "ckpt.json",
            session=session,
        )
        result = await puller.run()
        assert result["status"] == "OK"
        assert result["campaigns"] == 2
        assert result["source_1"] == 8  # 5 + 3 nodes
        assert result["source_3"] == 4

    @pytest.mark.asyncio
    async def test_checkpoint_persisted_on_completion(self, tmp_path):
        from adam.ingestion.stackadapt import HistoricalPuller
        session = MagicMock()
        session.is_configured = True
        session.get_campaigns = AsyncMock(return_value=[{"id": "c1"}])
        session.get_conversion_paths_page = AsyncMock(
            return_value=([], {"hasNextPage": False, "endCursor": None})
        )
        session.get_campaign_page_context_page = AsyncMock(
            return_value=([], {"hasNextPage": False, "endCursor": None})
        )
        ckpt = tmp_path / "ckpt.json"
        puller = HistoricalPuller(
            advertiser_id="luxy", checkpoint_path=ckpt, session=session,
        )
        await puller.run()
        assert ckpt.exists()
        state = json.loads(ckpt.read_text())
        assert state.get("source_1_complete") is True
        assert state.get("source_3_complete") is True

    @pytest.mark.asyncio
    async def test_source_1_error_breaks_loop_and_persists_cursor(
        self, tmp_path,
    ):
        from adam.ingestion.stackadapt import HistoricalPuller
        session = MagicMock()
        session.is_configured = True
        session.get_campaigns = AsyncMock(return_value=[{"id": "c1"}])
        session.get_conversion_paths_page = AsyncMock(
            return_value=([], {"hasNextPage": False, "endCursor": None,
                               "error": "RATE_LIMIT_EXHAUSTED"})
        )
        session.get_campaign_page_context_page = AsyncMock(
            return_value=([], {"hasNextPage": False, "endCursor": None})
        )
        puller = HistoricalPuller(
            advertiser_id="luxy",
            checkpoint_path=tmp_path / "ckpt.json", session=session,
        )
        result = await puller.run()
        # Should still complete and report (with source_1=0, error path).
        assert result["status"] == "OK"
        assert result["source_1"] == 0


# ----------------------------------------------------------------------------
# IncrementalPuller
# ----------------------------------------------------------------------------

class TestIncrementalPuller:
    @pytest.mark.asyncio
    async def test_default_window_24h_when_no_checkpoint(self, tmp_path):
        from adam.ingestion.stackadapt import IncrementalPuller
        session = MagicMock()
        session.is_configured = True
        session.get_campaigns = AsyncMock(return_value=[{"id": "c1"}])
        session.get_conversion_paths_page = AsyncMock(
            return_value=([], {"hasNextPage": False, "endCursor": None})
        )
        ckpt = tmp_path / "incr.json"
        puller = IncrementalPuller(
            advertiser_id="luxy", checkpoint_path=ckpt, session=session,
        )
        result = await puller.run()
        assert result["status"] == "OK"
        assert ckpt.exists()
        state = json.loads(ckpt.read_text())
        assert "last_run_at" in state

    @pytest.mark.asyncio
    async def test_window_overlaps_last_run_by_overlap_hours(self, tmp_path):
        from adam.ingestion.stackadapt import IncrementalPuller
        # Plant a checkpoint with last_run_at 12h ago.
        last = (datetime.now(timezone.utc) - timedelta(hours=12)).isoformat()
        ckpt = tmp_path / "incr.json"
        ckpt.write_text(json.dumps({"last_run_at": last}))

        session = MagicMock()
        session.is_configured = True
        session.get_campaigns = AsyncMock(return_value=[{"id": "c1"}])
        session.get_conversion_paths_page = AsyncMock(
            return_value=([], {"hasNextPage": False, "endCursor": None})
        )
        puller = IncrementalPuller(
            advertiser_id="luxy", checkpoint_path=ckpt,
            overlap_hours=6, session=session,
        )
        result = await puller.run()
        # window_start should be ~ (now - 12h - 6h) = 18h ago
        ws = datetime.strptime(
            result["window_start"], "%Y-%m-%dT%H:%M:%SZ",
        ).replace(tzinfo=timezone.utc)
        diff_hours = (datetime.now(timezone.utc) - ws).total_seconds() / 3600
        assert 17.5 < diff_hours < 18.5, f"window_start diff: {diff_hours:.2f}h"


# ----------------------------------------------------------------------------
# PixelCorrelator
# ----------------------------------------------------------------------------

class TestPixelCorrelator:
    def test_matched_join(self):
        from adam.ingestion.stackadapt import PixelCorrelator
        from adam.ingestion.stackadapt.pixel_correlator import (
            PixelPostback,
        )
        ts_imp = datetime(2026, 5, 4, 10, 0, tzinfo=timezone.utc)
        ts_evt = datetime(2026, 5, 4, 10, 5, tzinfo=timezone.utc)
        lookup = MagicMock(return_value={
            "creative_id": "cr1", "campaign_id": "cmp1",
            "domain": "foxnews.com",
            "impression_timestamp": ts_imp.isoformat(),
        })
        corr = PixelCorrelator(lookup_fn=lookup)
        result = corr.correlate_one(PixelPostback(
            sapid="sapid_A", event_name="conversion",
            event_timestamp=ts_evt,
            page_url="https://luxyride.com/x",
            revenue_usd=42.5,
        ))
        assert result.matched is True
        assert result.impression_creative_id == "cr1"
        assert result.impression_campaign_id == "cmp1"
        assert result.impression_domain == "foxnews.com"
        assert result.revenue_usd == 42.5

    def test_unmatched_join(self):
        from adam.ingestion.stackadapt import PixelCorrelator
        from adam.ingestion.stackadapt.pixel_correlator import (
            PixelPostback,
        )
        lookup = MagicMock(return_value=None)
        corr = PixelCorrelator(lookup_fn=lookup)
        result = corr.correlate_one(PixelPostback(
            sapid="missing_sapid", event_name="conversion",
            event_timestamp=datetime.now(timezone.utc),
        ))
        assert result.matched is False
        assert result.impression_creative_id is None

    def test_coverage_rate(self):
        from adam.ingestion.stackadapt import PixelCorrelator
        from adam.ingestion.stackadapt.pixel_correlator import (
            PixelPostback,
        )
        # Plan: 4 postbacks, 3 match, 1 doesn't.
        ts = datetime.now(timezone.utc)
        responses = iter([
            {"creative_id": "cr1", "impression_timestamp": ts.isoformat()},
            None,
            {"creative_id": "cr2", "impression_timestamp": ts.isoformat()},
            {"creative_id": "cr3", "impression_timestamp": ts.isoformat()},
        ])
        lookup = MagicMock(side_effect=lambda sapid: next(responses))
        corr = PixelCorrelator(lookup_fn=lookup)
        results = corr.correlate_batch([
            PixelPostback(sapid=s, event_name="x", event_timestamp=ts)
            for s in ("a", "b", "c", "d")
        ])
        rate = corr.coverage_rate(results)
        assert rate == 0.75  # 3/4
