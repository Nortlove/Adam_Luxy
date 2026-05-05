"""Permanent StackAdapt ingestion pipeline (S4 substrate).

Per directive §S4 — distinct from S0's one-shot extraction. This
package is the long-lived ingestion driver that S5/S6/S7/S9/S10/1.D.SB
consume.

Modules:
  rate_limited_session — token-bucket-paced wrapper over the existing
                         StackAdaptGraphQLClient with the corrected
                         schema patterns from S0 commit 54407ac.
  historical_puller    — full backfill driver (12-month default).
  incremental_puller   — daily incremental driver (since-checkpoint).
  pixel_correlator     — sapid={SA_POSTBACK_ID} URL-macro joiner.
"""
from adam.ingestion.stackadapt.rate_limited_session import (
    RateLimitedGraphQLSession,
)
from adam.ingestion.stackadapt.historical_puller import HistoricalPuller
from adam.ingestion.stackadapt.incremental_puller import IncrementalPuller
from adam.ingestion.stackadapt.pixel_correlator import PixelCorrelator

__all__ = [
    "RateLimitedGraphQLSession",
    "HistoricalPuller",
    "IncrementalPuller",
    "PixelCorrelator",
]
