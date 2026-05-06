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
from adam.priming.pipeline import (
    FetchedPage,
    PipelineResult,
    batch_process_urls,
    map_profile_to_signature,
    profile_url_to_signature,
    url_to_hash,
)
from adam.priming.feature_store import (
    CascadeMetrics,
    InMemoryL2Backend,
    InMemoryL3Backend,
    L2Backend,
    L3Backend,
    PagePrimingSignatureStore,
)

__all__ = [
    # signature
    "PagePrimingSignature",
    "RegulatoryFocus",
    "SIGNATURE_DIMENSIONS",
    "SIGNATURE_VERSION_V1",
    "neutral_signature",
    # pipeline
    "FetchedPage",
    "PipelineResult",
    "batch_process_urls",
    "map_profile_to_signature",
    "profile_url_to_signature",
    "url_to_hash",
    # feature store
    "CascadeMetrics",
    "InMemoryL2Backend",
    "InMemoryL3Backend",
    "L2Backend",
    "L3Backend",
    "PagePrimingSignatureStore",
]
