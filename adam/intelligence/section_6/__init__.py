# =============================================================================
# Section 6 — Offline Learning Engine (Claude API as the Slow Brain)
# =============================================================================
"""Per directive Section 6 (lines 738-806) + Spine #12. The offline
pipeline runs at four cadences (daily / weekly / monthly / quarterly)
and produces hierarchical priors, taxonomies, hypotheses, and
mechanism inventory updates that flow back into the online cascade.

This module ships the MONTHLY (corpus mechanism re-discovery) and
QUARTERLY (hierarchical prior reconciliation) cadence substrates.
The DAILY + WEEKLY cadences are wired elsewhere (Task 36 nightly
HMC reconcile, Task 40 dual-eval rewarm, Task 43 label-gen).

Per the 2026-05-02 wrap-out hard-stop criterion (iii): "Section 6
cadences have run end-to-end once on the LUXY corpus" — this
module's calibration run produces the artifact that closes the
criterion.
"""

from adam.intelligence.section_6.corpus_rediscovery import (
    CorpusRediscoveryResult,
    MechanismProposal,
    PrimaryMetaphorProposal,
    rediscover_from_corpus,
)
from adam.intelligence.section_6.hierarchical_reconcile import (
    HierarchicalReconciliationResult,
    PriorLevel,
    reconcile_hierarchy,
)

__all__ = [
    "CorpusRediscoveryResult",
    "MechanismProposal",
    "PrimaryMetaphorProposal",
    "rediscover_from_corpus",
    "HierarchicalReconciliationResult",
    "PriorLevel",
    "reconcile_hierarchy",
]
