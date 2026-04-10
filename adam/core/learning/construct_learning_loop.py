"""
Construct Learning Loop — The Compounding Flywheel Integration.

Connects the Gradient Bridge (outcome processing) to the Bayesian Fusion Engine
(construct posterior updates). This is the mechanism that makes
"every campaign make the next campaign better."

Flow:
  1. GradientBridgeService.process_outcome() fires a learning signal
  2. This module receives the signal and extracts construct-level data
  3. BayesianFusionEngine updates posteriors on all three edge types
  4. Updated posteriors persist to Neo4j for next-request use
  5. Flywheel metrics are tracked

Integration:
  - Call `process_construct_learning()` from GradientBridgeService._propagate_signals()
  - Or call directly with a CampaignOutcome from any learning entry point

AUTHORITATIVE SOURCE: taxonomy/Construct_Taxonomy_v2_COMPLETE.md (Part IV)
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Optional

from adam.intelligence.bayesian_fusion import (
    BayesianFusionEngine,
    CampaignOutcome,
    EdgeType,
    OutcomeType,
    UpdateResult,
    get_bayesian_fusion_engine,
)
from adam.intelligence.construct_taxonomy import (
    TEMPORAL_STABILITY_CONFIG,
    TemporalStability,
    get_all_constructs,
)

logger = logging.getLogger(__name__)


# =============================================================================
# LEARNING SIGNAL ADAPTER
# =============================================================================

@dataclass
class ConstructLearningSignal:
    """A learning signal enriched with construct-level data."""
    decision_id: str
    request_id: str
    user_id: str
    outcome_type: str
    outcome_value: float
    mechanism_used: Optional[str] = None

    # Construct scores at time of decision
    user_construct_scores: dict[str, float] = field(default_factory=dict)
    ad_construct_scores: dict[str, float] = field(default_factory=dict)
    peer_construct_scores: dict[str, float] = field(default_factory=dict)
    ecosystem_construct_scores: dict[str, float] = field(default_factory=dict)

    # Context
    asin: Optional[str] = None
    product_category: str = ""

    # Attribution weights from Gradient Bridge
    atom_credits: dict[str, float] = field(default_factory=dict)


# =============================================================================
# CONSTRUCT LEARNING LOOP
# =============================================================================

class ConstructLearningLoop:
    """
    The Compounding Flywheel: learns at the psychological construct level.

    "Google, Meta, and Amazon predict what you'll buy based on what you've
    already done. We predict what you'll buy based on who you are."

    This class implements the construct-level learning that powers this
    differentiator. Each campaign outcome updates Bayesian posteriors for
    every construct pair involved in the decision.
    """

    def __init__(
        self,
        neo4j_driver=None,
        fusion_engine: Optional[BayesianFusionEngine] = None,
    ):
        self._engine = fusion_engine or get_bayesian_fusion_engine(neo4j_driver)
        self._all_constructs = get_all_constructs()
        self._total_signals_processed = 0
        self._total_edges_updated = 0
        self._persist_interval = 100  # Persist to Neo4j every N signals

    def process_construct_learning(
        self, signal: ConstructLearningSignal
    ) -> list[UpdateResult]:
        """
        Process a construct learning signal through the Bayesian fusion engine.

        This is the main entry point called from the Gradient Bridge.
        """
        start_time = time.monotonic()

        # Determine which edge types to update based on available data
        edge_types = []
        if signal.ad_construct_scores:
            edge_types.append(EdgeType.BRAND_CONVERTED)
        if signal.peer_construct_scores:
            edge_types.append(EdgeType.PEER_INFLUENCED)
        if signal.ecosystem_construct_scores:
            edge_types.append(EdgeType.ECOSYSTEM_CONVERTED)

        if not edge_types:
            # Fall back to brand-converted with whatever ad data we have
            edge_types = [EdgeType.BRAND_CONVERTED]

        # Map outcome type
        outcome_type_map = {
            "conversion": OutcomeType.CONVERSION,
            "click": OutcomeType.CLICK,
            "engagement": OutcomeType.ENGAGEMENT,
            "view": OutcomeType.VIEW,
            "add_to_cart": OutcomeType.ADD_TO_CART,
            "purchase": OutcomeType.PURCHASE,
        }
        outcome_type = outcome_type_map.get(
            signal.outcome_type, OutcomeType.CONVERSION
        )

        # Create CampaignOutcome
        outcome = CampaignOutcome(
            campaign_id=signal.decision_id,
            user_id=signal.user_id,
            asin=signal.asin,
            outcome_type=outcome_type,
            outcome_value=signal.outcome_value,
            timestamp=time.time(),
            user_construct_scores=signal.user_construct_scores,
            ad_construct_scores=signal.ad_construct_scores,
            peer_construct_scores=signal.peer_construct_scores,
            ecosystem_construct_scores=signal.ecosystem_construct_scores,
            edge_types=edge_types,
            product_category=signal.product_category,
        )

        # Process through fusion engine
        results = self._engine.process_outcome(outcome)

        # Track metrics
        self._total_signals_processed += 1
        self._total_edges_updated += len(results)

        # Periodic persistence to Neo4j
        if self._total_signals_processed % self._persist_interval == 0:
            persisted = self._engine.persist_to_neo4j()
            logger.info(
                f"Construct learning: persisted {persisted} edges after "
                f"{self._total_signals_processed} signals"
            )

        elapsed_ms = (time.monotonic() - start_time) * 1000
        if elapsed_ms > 50:
            logger.warning(
                f"Construct learning took {elapsed_ms:.1f}ms for signal "
                f"{signal.decision_id}"
            )

        return results

    def from_gradient_bridge_outcome(
        self,
        decision_id: str,
        request_id: str,
        user_id: str,
        outcome_type: str,
        outcome_value: float,
        atom_outputs: Optional[dict[str, Any]] = None,
        mechanism_used: Optional[str] = None,
        ad_context: Optional[dict[str, Any]] = None,
    ) -> list[UpdateResult]:
        """
        Adapter: Convert Gradient Bridge outcome data to construct learning signal.

        Call this from GradientBridgeService.process_outcome() to integrate
        construct-level learning into the existing pipeline.
        """
        ad_context = ad_context or {}

        # Extract construct vectors from ad_context
        construct_vectors = ad_context.get("construct_vectors", {})
        user_scores = construct_vectors.get("user_edge", {})
        ad_scores = construct_vectors.get("brand", {})
        peer_scores = construct_vectors.get("peer", {})
        eco_scores = construct_vectors.get("ecosystem", {})

        # If no construct vectors, try dimensional_priors as fallback
        if not user_scores:
            user_scores = ad_context.get("dimensional_priors", {})

        signal = ConstructLearningSignal(
            decision_id=decision_id,
            request_id=request_id,
            user_id=user_id,
            outcome_type=outcome_type,
            outcome_value=outcome_value,
            mechanism_used=mechanism_used,
            user_construct_scores=user_scores,
            ad_construct_scores=ad_scores,
            peer_construct_scores=peer_scores,
            ecosystem_construct_scores=eco_scores,
        )

        return self.process_construct_learning(signal)

    def get_flywheel_metrics(self) -> dict[str, Any]:
        """Get the compounding flywheel metrics."""
        engine_metrics = self._engine.get_flywheel_metrics()
        return {
            "total_signals_processed": self._total_signals_processed,
            "total_edges_updated": self._total_edges_updated,
            "avg_edges_per_signal": (
                self._total_edges_updated / max(1, self._total_signals_processed)
            ),
            **engine_metrics,
        }

    def force_persist(self) -> int:
        """Force persistence of all cached posteriors to Neo4j."""
        return self._engine.persist_to_neo4j()


# =============================================================================
# SINGLETON ACCESS
# =============================================================================

_loop_instance: Optional[ConstructLearningLoop] = None


def get_construct_learning_loop(
    neo4j_driver=None,
) -> ConstructLearningLoop:
    """Get or create the singleton ConstructLearningLoop."""
    global _loop_instance
    if _loop_instance is None:
        _loop_instance = ConstructLearningLoop(neo4j_driver)
    return _loop_instance
