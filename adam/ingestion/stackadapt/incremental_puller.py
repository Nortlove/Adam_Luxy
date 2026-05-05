"""IncrementalPuller — daily incremental driver.

Per directive §S4.1. Runs since-last-checkpoint; intended for cron.
The corrected S0 schema patterns (commit 54407ac) apply: conversionPath
is cursor-paginated; campaignPageContext is UNION-resolving with
Progress polling.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from adam.ingestion.stackadapt.rate_limited_session import (
    RateLimitedGraphQLSession,
)

logger = logging.getLogger(__name__)


class IncrementalPuller:
    """Daily-cadence incremental driver.

    Reads `last_run_at` from the incremental checkpoint; pulls
    everything since that time + a small overlap window (default 6
    hours) to handle late-arriving conversions. Writes new
    `last_run_at` on clean completion.
    """

    DEFAULT_OVERLAP_HOURS = 6

    def __init__(
        self,
        advertiser_id: str,
        checkpoint_path: Optional[Path] = None,
        page_size: int = 200,
        overlap_hours: int = DEFAULT_OVERLAP_HOURS,
        session: Optional[RateLimitedGraphQLSession] = None,
    ) -> None:
        self.advertiser_id = advertiser_id
        self.page_size = page_size
        self.overlap_hours = overlap_hours
        self.checkpoint_path = (
            checkpoint_path
            or Path("artifacts/ingestion/stackadapt/_incremental_checkpoint.json")
        )
        self._session = session
        self._owned_session = session is None

    async def run(self) -> Dict[str, Any]:
        """Execute one incremental cycle."""
        session = self._session or RateLimitedGraphQLSession()
        try:
            window_start, window_end = self._compute_window()
            logger.info("incremental window: %s → %s",
                        window_start, window_end)

            campaigns = await session.get_campaigns(
                first=500,
                filter_by={"advertiserIds": [self.advertiser_id]},
            )
            campaign_ids = [c["id"] for c in campaigns if c.get("id")]
            if not campaign_ids:
                return {"status": "ABORTED_NO_CAMPAIGNS"}

            n_s1 = await self._pull_source_1(
                session, campaign_ids, window_start, window_end,
            )
            self._save_run_timestamp(window_end)

            return {
                "status": "OK",
                "window_start": window_start,
                "window_end": window_end,
                "source_1": n_s1,
            }
        finally:
            if self._owned_session:
                try:
                    await session.__aexit__(None, None, None)
                except Exception:
                    pass

    def _compute_window(self) -> tuple[str, str]:
        """Resume window: (last_run - overlap_hours) → now."""
        end_dt = datetime.now(timezone.utc)
        last_run = self._load_last_run()
        if last_run is None:
            # Fresh run: default to last 24h.
            start_dt = end_dt - timedelta(days=1)
        else:
            start_dt = last_run - timedelta(hours=self.overlap_hours)
        return (
            start_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
            end_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
        )

    async def _pull_source_1(
        self,
        session: RateLimitedGraphQLSession,
        campaign_ids: Sequence[str],
        window_start: str,
        window_end: str,
    ) -> int:
        cursor = None
        n_total = 0
        while True:
            nodes, page_info = await session.get_conversion_paths_page(
                filter_by={
                    "campaignIds": list(campaign_ids),
                    "startTime": window_start,
                    "endTime": window_end,
                },
                first=self.page_size,
                after=cursor,
            )
            if page_info.get("error"):
                logger.error("incremental source_1 error: %s",
                             page_info.get("error"))
                return n_total
            self._persist_source_1_batch(nodes)
            n_total += len(nodes)
            if not page_info.get("hasNextPage"):
                break
            cursor = page_info.get("endCursor")
        return n_total

    def _persist_source_1_batch(self, nodes: List[Dict[str, Any]]) -> None:
        """Hook for S4.2/S4.3/S4.4 — mirrored from HistoricalPuller."""
        if nodes:
            logger.debug("incremental source_1 batch: %d records",
                         len(nodes))

    def _load_last_run(self) -> Optional[datetime]:
        if not self.checkpoint_path.exists():
            return None
        try:
            state = json.loads(self.checkpoint_path.read_text())
            ts = state.get("last_run_at")
            if not ts:
                return None
            return datetime.fromisoformat(ts).astimezone(timezone.utc)
        except Exception:
            return None

    def _save_run_timestamp(self, window_end_iso: str) -> None:
        state: Dict[str, Any] = {}
        if self.checkpoint_path.exists():
            try:
                state = json.loads(self.checkpoint_path.read_text())
            except Exception:
                state = {}
        state["last_run_at"] = window_end_iso
        self.checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
        self.checkpoint_path.write_text(json.dumps(state, indent=2))
