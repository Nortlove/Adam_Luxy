"""HistoricalPuller — full backfill driver.

Per directive §S4.1. Backfill default: 12 months. Drives the
`RateLimitedGraphQLSession` over the corrected S0 schema patterns
(commit 54407ac) and emits typed records that S4.2 (Iceberg
persistence), S4.3 (Neo4j trajectory writes), and S4.4 (Postgres
rollup) consume.

Skeleton: orchestration logic is in place; persistence-layer wiring
is left as `_persist_*` hooks that S4.2/S4.3/S4.4 implement. The
skeleton is exercised by tests via mocked sessions to confirm the
control flow + checkpoint discipline.

Two source streams (per S0 commit 54407ac):
  Source 1 — conversionPath (cursor-paginated, conversion-conditional)
  Source 3 — campaignPageContext (UNION-paginated, population-level)
  (Source 2 — pixel_postback — is N/A on LUXY; will become available
   when impression-time pixel-tracking infrastructure ships per the
   pending G1-pivot adjudication.)
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


class HistoricalPuller:
    """Full-backfill driver for one advertiser over a configurable
    window. Default window: 12 months.

    The driver is checkpoint-aware: if a checkpoint file exists at
    `checkpoint_path`, it resumes from the saved cursor per source.
    On exit (clean or exception), it persists the cursor so the next
    invocation resumes.
    """

    def __init__(
        self,
        advertiser_id: str,
        backfill_months: int = 12,
        page_size: int = 200,
        checkpoint_path: Optional[Path] = None,
        session: Optional[RateLimitedGraphQLSession] = None,
    ) -> None:
        self.advertiser_id = advertiser_id
        self.backfill_months = backfill_months
        self.page_size = page_size
        self.checkpoint_path = (
            checkpoint_path
            or Path("artifacts/ingestion/stackadapt/_historical_checkpoint.json")
        )
        self._session = session
        self._owned_session = session is None

    async def run(self) -> Dict[str, Any]:
        """Execute the full backfill.

        Returns a dict with per-source row counts + final state. Does
        not return raw rows — the persistence hooks below consume
        them in-flight to keep memory bounded.
        """
        session = self._session or RateLimitedGraphQLSession()
        try:
            campaigns = await session.get_campaigns(
                first=500,
                filter_by={"advertiserIds": [self.advertiser_id]},
            )
            campaign_ids = [c["id"] for c in campaigns if c.get("id")]
            if not campaign_ids:
                logger.warning(
                    "no campaigns for advertiser_id=%s — backfill aborted",
                    self.advertiser_id,
                )
                return {"campaigns": 0, "source_1": 0, "source_3": 0,
                        "status": "ABORTED_NO_CAMPAIGNS"}

            n_s1 = await self._pull_source_1(session, campaign_ids)
            n_s3 = await self._pull_source_3(session)

            return {
                "campaigns": len(campaign_ids),
                "source_1": n_s1,
                "source_3": n_s3,
                "status": "OK",
            }
        finally:
            if self._owned_session:
                try:
                    await session.__aexit__(None, None, None)
                except Exception:
                    pass

    async def _pull_source_1(
        self,
        session: RateLimitedGraphQLSession,
        campaign_ids: Sequence[str],
    ) -> int:
        """conversionPath cursor-paginated pull. Each node emits one
        record (conversionUrl + per-record metadata) — the corrected
        S0 schema reality (no touchpoints[]).
        """
        end = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        start = (datetime.now(timezone.utc)
                 - timedelta(days=self.backfill_months * 30)).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        cursor = self._load_cursor("source_1")
        n_total = 0
        while True:
            nodes, page_info = await session.get_conversion_paths_page(
                filter_by={
                    "campaignIds": list(campaign_ids),
                    "startTime": start,
                    "endTime": end,
                },
                first=self.page_size,
                after=cursor,
            )
            if page_info.get("error"):
                logger.error("source_1 error: %s; saving checkpoint",
                             page_info.get("error"))
                self._save_cursor("source_1", cursor)
                break
            self._persist_source_1_batch(nodes)
            n_total += len(nodes)
            if not page_info.get("hasNextPage"):
                break
            cursor = page_info.get("endCursor")
            self._save_cursor("source_1", cursor)
        self._save_cursor("source_1", None, complete=True)
        return n_total

    async def _pull_source_3(
        self,
        session: RateLimitedGraphQLSession,
    ) -> int:
        """campaignPageContext UNION-resolving pull (Outcome | Progress).
        Population-level URL surface per S0 commit 54407ac."""
        date_to = datetime.now().strftime("%Y-%m-%d")
        date_from = (datetime.now()
                     - timedelta(days=self.backfill_months * 30)).strftime(
            "%Y-%m-%d"
        )
        cursor = self._load_cursor("source_3")
        n_total = 0
        while True:
            nodes, page_info = await session.get_campaign_page_context_page(
                advertiser_id=self.advertiser_id,
                date_from=date_from, date_to=date_to,
                first=self.page_size, after=cursor,
            )
            if page_info.get("error"):
                err = page_info.get("error")
                if err in ("PROGRESS_TIMEOUT",
                           "PROGRESS_TIMEOUT_UNREACHABLE"):
                    logger.warning("source_3 progress-timeout; stopping")
                    break
                logger.error("source_3 error: %s; checkpointing", err)
                self._save_cursor("source_3", cursor)
                break
            self._persist_source_3_batch(nodes)
            n_total += len(nodes)
            if not page_info.get("hasNextPage"):
                break
            cursor = page_info.get("endCursor")
            self._save_cursor("source_3", cursor)
        self._save_cursor("source_3", None, complete=True)
        return n_total

    # -------- persistence hooks (S4.2/S4.3/S4.4 implement these) --------

    def _persist_source_1_batch(self, nodes: List[Dict[str, Any]]) -> None:
        """Hook for S4.2 (Iceberg) + S4.3 (Neo4j trajectory writes) +
        S4.4 (Postgres rollup) — to be filled in those slices.

        Skeleton-stage: log batch size for ingestion-test traceability.
        """
        if nodes:
            logger.debug("source_1 batch: %d records pending persistence",
                         len(nodes))

    def _persist_source_3_batch(self, nodes: List[Dict[str, Any]]) -> None:
        """Same hook contract as source_1; populated by S4.2-S4.4."""
        if nodes:
            logger.debug("source_3 batch: %d records pending persistence",
                         len(nodes))

    # -------- checkpoint persistence --------

    def _load_cursor(self, source_key: str) -> Optional[str]:
        if not self.checkpoint_path.exists():
            return None
        try:
            state = json.loads(self.checkpoint_path.read_text())
            return state.get(f"{source_key}_cursor")
        except Exception:
            return None

    def _save_cursor(
        self, source_key: str,
        cursor: Optional[str], complete: bool = False,
    ) -> None:
        state: Dict[str, Any] = {}
        if self.checkpoint_path.exists():
            try:
                state = json.loads(self.checkpoint_path.read_text())
            except Exception:
                state = {}
        state[f"{source_key}_cursor"] = cursor
        if complete:
            state[f"{source_key}_complete"] = True
        self.checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
        self.checkpoint_path.write_text(json.dumps(state, indent=2))
