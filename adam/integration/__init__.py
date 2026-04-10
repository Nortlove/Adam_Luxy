# =============================================================================
# ADAM Integration Module
# Location: adam/integration/__init__.py
# =============================================================================

"""
INTEGRATION MODULE

Provides integration services that wire together ADAM's components:

- Decision Enrichment: Identity + Competitive + Explanation
- Service Orchestration: Cross-component coordination
"""

from .decision_enrichment import (
    DecisionEnrichmentService,
    EnrichedContext,
    EnrichedDecision,
    IdentifierData,
    get_decision_enrichment,
)

__all__ = [
    "DecisionEnrichmentService",
    "EnrichedContext",
    "EnrichedDecision",
    "IdentifierData",
    "get_decision_enrichment",
]
