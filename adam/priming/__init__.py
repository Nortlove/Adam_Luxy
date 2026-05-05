"""Page-priming-signature substrate.

Per directive §S3 — replaces the spec-only `MicroStateDetector` at bid
time with a Feature-Store-backed page-priming-signature lookup. Live
user-state detection remains explicitly deferred to 2.E.S1 (post-
impression telemetry from Enhancement #08 Signal Aggregation).
"""
from adam.priming.signature import (
    PagePrimingSignature,
    RegulatoryFocus,
    SIGNATURE_DIMENSIONS,
    SIGNATURE_VERSION_V1,
    neutral_signature,
)

__all__ = [
    "PagePrimingSignature",
    "RegulatoryFocus",
    "SIGNATURE_DIMENSIONS",
    "SIGNATURE_VERSION_V1",
    "neutral_signature",
]
