"""RateLimitedGraphQLSession — token-bucket-paced wrapper over the
existing `StackAdaptGraphQLClient`.

Per directive §S4.1 + §1.3 ("reuse, do not recreate"). The existing
client already has `_query_with_retry` (full-jitter exponential
backoff per S0 commit 54407ac); this wrapper ADDS a token-bucket
rate limiter on top so the permanent ingestion pipeline (S4)
respects sustained-throughput limits in addition to burst limits.

The wrapper is intentionally thin — it composes the existing client
rather than reimplementing transport. The token bucket lives at the
session level so all per-page calls within one historical-pull run
share rate-limit budget.

Token-bucket semantics:
  - `capacity` tokens (default 10).
  - Refill rate `rate_per_second` tokens/sec (default 5).
  - Each query consumes 1 token.
  - If 0 tokens available, async-waits for the next refill tick.
  - Pure asyncio; no threads.

S0 commit 54407ac established the corrected schema patterns:
  - conversionPath returns Connection (cursor-paginated)
  - campaignPageContext returns UNION (Outcome | Progress, polled)
  - DateRangeInput uses {from, to}
  - Enums: dataType ∈ {GRAPH, TABLE}; granularity ∈ {DAILY, ...,
    WEEKLY, TOTAL}.
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional, Tuple

from adam.integrations.stackadapt.graphql_client import (
    StackAdaptGraphQLClient,
)

logger = logging.getLogger(__name__)


class RateLimitedGraphQLSession:
    """Composes a StackAdaptGraphQLClient with token-bucket rate
    limiting at the session level.

    Use as an async context manager:
        async with RateLimitedGraphQLSession() as session:
            nodes, page_info = await session.get_conversion_paths_page(
                filter_by={...}, first=200,
            )

    Or pass an existing client in (for shared-client patterns):
        client = StackAdaptGraphQLClient(api_key=...)
        session = RateLimitedGraphQLSession(client=client)
    """

    def __init__(
        self,
        client: Optional[StackAdaptGraphQLClient] = None,
        capacity: int = 10,
        rate_per_second: float = 5.0,
    ) -> None:
        self._client = client or StackAdaptGraphQLClient()
        self._capacity = float(capacity)
        self._rate_per_second = float(rate_per_second)
        self._tokens = float(capacity)
        self._last_refill = time.monotonic()
        self._lock = asyncio.Lock()
        self._owns_client = client is None

    async def __aenter__(self) -> "RateLimitedGraphQLSession":
        return self

    async def __aexit__(self, *args: Any) -> None:
        if self._owns_client:
            try:
                await self._client._client.aclose()
            except Exception:
                pass

    async def _acquire_token(self) -> None:
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_refill
            self._tokens = min(
                self._capacity,
                self._tokens + elapsed * self._rate_per_second,
            )
            self._last_refill = now
            if self._tokens >= 1.0:
                self._tokens -= 1.0
                return
            wait_seconds = (1.0 - self._tokens) / self._rate_per_second
        await asyncio.sleep(wait_seconds)
        async with self._lock:
            self._tokens = max(0.0, self._tokens - 1.0)
            self._last_refill = time.monotonic()

    @property
    def is_configured(self) -> bool:
        return self._client.is_configured

    # -------- thin pass-through to the corrected S0 helpers --------

    async def get_conversion_paths_page(
        self,
        filter_by: Dict[str, Any],
        first: int = 200,
        after: Optional[str] = None,
    ) -> Tuple[List[Dict], Dict[str, Any]]:
        """Rate-limited wrapper for the corrected conversionPath
        cursor-pagination helper (S0 54407ac)."""
        await self._acquire_token()
        return await self._client.get_conversion_paths_page(
            filter_by=filter_by, first=first, after=after,
        )

    async def get_campaign_page_context_page(
        self,
        advertiser_id: str,
        date_from: str,
        date_to: str,
        first: int = 200,
        after: Optional[str] = None,
    ) -> Tuple[List[Dict], Dict[str, Any]]:
        """Rate-limited wrapper for the corrected campaignPageContext
        UNION-resolving helper (S0 54407ac, includes Progress polling)."""
        await self._acquire_token()
        return await self._client.get_campaign_page_context_page(
            advertiser_id=advertiser_id,
            date_from=date_from, date_to=date_to,
            first=first, after=after,
        )

    async def get_campaigns(
        self,
        first: int = 100,
        after: Optional[str] = None,
        filter_by: Optional[Dict[str, Any]] = None,
    ) -> List[Dict]:
        """Rate-limited wrapper for campaign discovery."""
        await self._acquire_token()
        return await self._client.get_campaigns(
            first=first, after=after, filter_by=filter_by,
        )
