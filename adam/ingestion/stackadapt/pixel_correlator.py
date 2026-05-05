"""PixelCorrelator — sapid={SA_POSTBACK_ID} URL-macro joiner.

Per directive §S4.1 + §0.5 (inbound-only StackAdapt data plane;
sapid round-trip is the click-attribution mechanism). The correlator
joins inbound pixel postbacks (received by `adam/api/stackadapt/
webhook.py`) to the last-served impression by `sapid`.

Skeleton: shape + types + join semantics are implemented; the actual
Postgres/Redis lookup tables that S4.4 stands up are referenced by
the `_lookup_last_impression` hook. The join logic itself
(sapid-as-key, last-impression-by-timestamp) is testable via mocked
lookups.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PixelPostback:
    """Inbound pixel postback received by the webhook receiver."""
    sapid: str
    event_name: str
    event_timestamp: datetime
    page_url: Optional[str] = None
    revenue_usd: Optional[float] = None
    raw_payload: Optional[Dict[str, Any]] = None


@dataclass(frozen=True)
class CorrelatedConversion:
    """Result of joining a PixelPostback to its last-served impression."""
    sapid: str
    event_name: str
    event_timestamp: datetime
    page_url: Optional[str]
    revenue_usd: Optional[float]
    impression_creative_id: Optional[str]
    impression_campaign_id: Optional[str]
    impression_domain: Optional[str]
    impression_timestamp: Optional[datetime]
    matched: bool


# Type for the lookup hook: takes a sapid, returns the last-served
# impression record dict, or None if no match. S4.4's Postgres rollup
# implements this against the impression-side table.
LookupFn = Callable[[str], Optional[Dict[str, Any]]]


class PixelCorrelator:
    """Joins pixel postbacks to last-served impressions by sapid.

    Skeleton: the join semantics + result type are pinned. The actual
    lookup table (Postgres rollup populated by S4.4) is injected as a
    callable so this module is testable in isolation and S4.4 can swap
    the implementation without recompiling consumers.
    """

    def __init__(self, lookup_fn: LookupFn) -> None:
        self._lookup_fn = lookup_fn

    def correlate_one(
        self, postback: PixelPostback,
    ) -> CorrelatedConversion:
        """Single-postback correlation. Returns CorrelatedConversion
        with `matched=False` when no last-served impression is found
        for the sapid."""
        rec = self._lookup_fn(postback.sapid)
        if rec is None:
            return CorrelatedConversion(
                sapid=postback.sapid,
                event_name=postback.event_name,
                event_timestamp=postback.event_timestamp,
                page_url=postback.page_url,
                revenue_usd=postback.revenue_usd,
                impression_creative_id=None,
                impression_campaign_id=None,
                impression_domain=None,
                impression_timestamp=None,
                matched=False,
            )
        impression_ts = rec.get("impression_timestamp")
        if isinstance(impression_ts, str):
            try:
                impression_ts = datetime.fromisoformat(impression_ts)
            except ValueError:
                impression_ts = None
        return CorrelatedConversion(
            sapid=postback.sapid,
            event_name=postback.event_name,
            event_timestamp=postback.event_timestamp,
            page_url=postback.page_url,
            revenue_usd=postback.revenue_usd,
            impression_creative_id=rec.get("creative_id"),
            impression_campaign_id=rec.get("campaign_id"),
            impression_domain=rec.get("domain"),
            impression_timestamp=impression_ts,
            matched=True,
        )

    def correlate_batch(
        self, postbacks: List[PixelPostback],
    ) -> List[CorrelatedConversion]:
        """Batch correlation. Maintains input order; emits one result
        per input postback."""
        return [self.correlate_one(p) for p in postbacks]

    def coverage_rate(
        self, results: List[CorrelatedConversion],
    ) -> float:
        """Per directive §S8.7 risk register: pixel-postback
        attribution coverage rate. Surfaced for the join-diagnostics
        pipeline that S4.7 + S5.7 exercise."""
        if not results:
            return 0.0
        matched = sum(1 for r in results if r.matched)
        return matched / len(results)
