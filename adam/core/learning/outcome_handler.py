#!/usr/bin/env python3
"""
OUTCOME HANDLER — Closes the Learning Loop
===========================================

When an outcome arrives (click, conversion, bounce, etc.), this handler:

1. Retrieves the prediction context from the persist step
2. Computes prediction error (predicted_effectiveness vs actual)
3. Updates Thompson Sampling posteriors (Beta distribution update)
4. Updates the meta-orchestrator (which strategy worked)
5. Updates the graph rewriter (which rules helped)
6. Updates Neo4j with outcome attribution edges
7. Updates the ML hybrid extractor ensemble weights
8. Routes learning signals to all 30 atoms via UnifiedLearningHub

This is Phase 4 of the Post-Ingestion Master Plan:
    predict → decide → observe → reason → improve

The system gets STRONGER with every outcome it observes.
"""

import logging
import time
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


class OutcomeHandler:
    """
    Processes outcomes and routes learning signals to all system components.
    
    This is the SINGLE entry point for outcome processing. All outcomes
    (from API callbacks, Kafka events, or batch processing) flow through here.
    """
    
    def __init__(self):
        self._outcomes_processed = 0
        self._total_updates = 0
    
    async def process_outcome(
        self,
        decision_id: str,
        outcome_type: str,  # "conversion", "click", "engagement", "bounce", "skip"
        outcome_value: float = 1.0,  # 0-1 scale
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Process an outcome and update all learning systems.
        
        Args:
            decision_id: ID of the original decision
            outcome_type: Type of outcome observed
            outcome_value: Outcome value (1.0 = full success, 0.0 = failure)
            metadata: Additional outcome metadata
            
        Returns:
            Summary of all updates performed
        """
        start = time.time()
        metadata = metadata or {}
        
        success = outcome_type in ("conversion", "click", "engagement") and outcome_value > 0.5
        
        results = {
            "decision_id": decision_id,
            "outcome_type": outcome_type,
            "success": success,
            "updates": {},
        }
        
        # =====================================================================
        # 1. UPDATE THOMPSON SAMPLING POSTERIORS
        # =====================================================================
        try:
            results["updates"]["thompson"] = await self._update_thompson(
                decision_id, success, metadata
            )
        except Exception as e:
            logger.warning(f"Thompson update failed: {e}")
            results["updates"]["thompson"] = {"error": str(e)}
        
        # =====================================================================
        # 2. UPDATE META-ORCHESTRATOR (which strategy worked)
        # =====================================================================
        try:
            results["updates"]["meta_orchestrator"] = await self._update_meta_orchestrator(
                decision_id, success, outcome_value, metadata
            )
        except Exception as e:
            logger.warning(f"Meta-orchestrator update failed for {decision_id}: {e}")
            results["updates"]["meta_orchestrator"] = {"error": str(e)}
        
        # =====================================================================
        # 3. UPDATE NEO4J OUTCOME ATTRIBUTION
        # =====================================================================
        try:
            results["updates"]["neo4j"] = await self._update_neo4j_attribution(
                decision_id, outcome_type, outcome_value, metadata
            )
        except Exception as e:
            logger.warning(f"Neo4j attribution update failed for {decision_id}: {e}")
            results["updates"]["neo4j"] = {"error": str(e)}
        
        # =====================================================================
        # 4. UPDATE GRAPH REWRITER (which rules helped)
        # =====================================================================
        try:
            results["updates"]["graph_rewriter"] = await self._update_graph_rewriter(
                decision_id, success, metadata
            )
        except Exception as e:
            logger.warning(f"Graph rewriter update failed for {decision_id}: {e}")
            results["updates"]["graph_rewriter"] = {"error": str(e)}
        
        # =====================================================================
        # 5. ROUTE TO UNIFIED LEARNING HUB (reaches all atoms)
        # =====================================================================
        try:
            results["updates"]["learning_hub"] = await self._route_to_learning_hub(
                decision_id, outcome_type, outcome_value, success, metadata
            )
        except Exception as e:
            logger.warning(f"Learning hub routing failed: {e}")
        
        # =====================================================================
        # 6. UPDATE ML ENSEMBLE WEIGHTS
        # =====================================================================
        try:
            results["updates"]["ml_ensemble"] = await self._update_ml_ensemble(
                decision_id, success, metadata
            )
        except Exception as e:
            logger.warning(f"ML ensemble update failed for {decision_id}: {e}")
            results["updates"]["ml_ensemble"] = {"error": str(e)}
        
        # =====================================================================
        # 7. CONSTRUCT-LEVEL LEARNING (Theory Learner)
        #
        # This is the new inferential intelligence layer. When outcomes arrive,
        # we update the theoretical link strengths — learning which causal
        # theories in the graph are empirically validated by real outcomes.
        #
        # Unlike Thompson Sampling (archetype → mechanism), this learns at
        # the deeper construct level (psychological_state → need → mechanism).
        # =====================================================================
        try:
            results["updates"]["theory_learner"] = await self._update_theory_learner(
                decision_id, success, outcome_value, metadata
            )
        except Exception as e:
            logger.warning(f"Theory learner update failed for {decision_id}: {e}")
            results["updates"]["theory_learner"] = {"error": str(e)}
        
        elapsed = (time.time() - start) * 1000
        results["processing_time_ms"] = elapsed
        
        self._outcomes_processed += 1
        self._total_updates += sum(1 for v in results["updates"].values() if "error" not in str(v))
        
        logger.info(
            f"Outcome processed: decision={decision_id}, "
            f"type={outcome_type}, success={success}, "
            f"updates={len(results['updates'])}, "
            f"time={elapsed:.0f}ms"
        )
        
        return results
    
    async def _update_thompson(
        self,
        decision_id: str,
        success: bool,
        metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Update Thompson Sampling posteriors with outcome."""
        from adam.cold_start.thompson.sampler import get_thompson_sampler
        from adam.cold_start.models.enums import ArchetypeID, CognitiveMechanism
        
        sampler = get_thompson_sampler()
        
        archetype = metadata.get("archetype", "")
        mechanisms = metadata.get("mechanisms_applied", [])
        
        updates = 0
        failed = []
        for mech_name in mechanisms:
            try:
                sampler.update(
                    archetype=archetype,
                    mechanism=mech_name,
                    success=success,
                )
                updates += 1
            except Exception as e:
                failed.append({"mechanism": mech_name, "error": str(e)})
                logger.warning(f"Thompson update failed for {archetype}/{mech_name}: {e}")
                continue
        
        if failed:
            logger.warning(f"Thompson: {len(failed)}/{len(mechanisms)} mechanism updates failed")
        
        return {"posteriors_updated": updates}
    
    async def _update_meta_orchestrator(
        self,
        decision_id: str,
        success: bool,
        quality_score: float,
        metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Update meta-orchestrator strategy posteriors."""
        from adam.orchestrator.adaptive.meta_orchestrator import (
            MetaOrchestrator, WorkflowStrategy, ContextSignature,
        )
        
        meta = MetaOrchestrator()
        strategy_name = metadata.get("meta_strategy", "deep_reasoning")
        
        try:
            strategy = WorkflowStrategy(strategy_name)
        except ValueError:
            strategy = WorkflowStrategy.DEEP_REASONING
        
        context = ContextSignature(
            archetype_known=bool(metadata.get("archetype")),
            brand_awareness=metadata.get("brand_awareness", 0.5),
        )
        
        meta.record_outcome(
            strategy=strategy,
            context=context,
            success=success,
            quality_score=quality_score,
        )
        
        return {"strategy_updated": strategy_name}
    
    async def _update_neo4j_attribution(
        self,
        decision_id: str,
        outcome_type: str,
        outcome_value: float,
        metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Create outcome attribution edges in Neo4j."""
        from adam.intelligence.graph.gds_runtime import get_gds_service
        
        gds = get_gds_service()
        mechanisms = metadata.get("mechanisms_applied", [])
        archetype = metadata.get("archetype", "")
        
        edges_created = 0
        for i, mech in enumerate(mechanisms):
            # Multi-touch attribution: first-touch gets most credit
            weight = outcome_value * (1.0 - i * 0.2)
            
            success = gds.create_outcome_attribution_edge(
                mechanism=mech,
                outcome_type=outcome_type,
                attribution_weight=max(0.1, weight),
                position=i,
                archetype_context=archetype,
            )
            if success:
                edges_created += 1
        
        # Also create mechanism synergy edges if multiple mechanisms used
        if len(mechanisms) >= 2 and outcome_value > 0.6:
            for i in range(len(mechanisms)):
                for j in range(i + 1, len(mechanisms)):
                    gds.create_mechanism_synergy_edge(
                        mechanism1=mechanisms[i],
                        mechanism2=mechanisms[j],
                        synergy_score=outcome_value,
                        combined_lift=outcome_value * 0.5,
                        context=archetype,
                    )
                    edges_created += 1
        
        return {"attribution_edges_created": edges_created}
    
    async def _update_graph_rewriter(
        self,
        decision_id: str,
        success: bool,
        metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Update graph rewriter rule effectiveness."""
        from adam.orchestrator.adaptive.graph_rewriter import AdaptiveGraphRewriter
        
        rewriter = AdaptiveGraphRewriter()
        rules_applied = metadata.get("graph_rewrites", {}).get("rules_applied", [])
        
        if rules_applied:
            rewriter.record_outcome(rules_applied, success)
            return {"rules_updated": len(rules_applied)}
        
        return {"rules_updated": 0}
    
    async def _route_to_learning_hub(
        self,
        decision_id: str,
        outcome_type: str,
        outcome_value: float,
        success: bool,
        metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Route outcome to unified learning hub for all-system updates."""
        from adam.core.learning.unified_learning_hub import (
            get_unified_learning_hub,
            UnifiedLearningSignal,
            UnifiedSignalType,
        )
        
        hub = get_unified_learning_hub()
        
        signal = UnifiedLearningSignal(
            signal_type=(
                UnifiedSignalType.OUTCOME_SUCCESS if success
                else UnifiedSignalType.OUTCOME_FAILURE
            ),
            source_component="outcome_handler",
            archetype=metadata.get("archetype", ""),
            mechanism=metadata.get("mechanisms_applied", ["unknown"])[0] if metadata.get("mechanisms_applied") else "unknown",
            confidence=outcome_value,
            payload={
                "decision_id": decision_id,
                "outcome_type": outcome_type,
                "outcome_value": outcome_value,
                "mechanisms_applied": metadata.get("mechanisms_applied", []),
                "ndf_profile": metadata.get("ndf_profile", {}),
                "alignment_score": metadata.get("alignment_score", 0.0),
                "meta_strategy": metadata.get("meta_strategy", ""),
                "product_category": metadata.get("product_category", ""),
            },
        )
        
        await hub.process_signal(signal)
        
        return {"signal_routed": True}
    
    async def _update_theory_learner(
        self,
        decision_id: str,
        success: bool,
        outcome_value: float,
        metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Update theoretical link strengths based on outcome.
        
        This is construct-level learning: the system learns which causal
        theories (PsychologicalState → PsychologicalNeed → CognitiveMechanism)
        are empirically validated by real outcomes.
        
        The inferential chains used for the decision are retrieved from the
        metadata (cached at decision time), and each theoretical link in
        each chain gets a Bayesian update.
        """
        from adam.core.learning.theory_learner import get_theory_learner
        
        learner = get_theory_learner()
        
        # Get the inferential chains from metadata
        inferential_chains = metadata.get("inferential_chains", [])
        
        if not inferential_chains:
            # Try to load from Redis cache (chains are cached with atom outputs)
            try:
                from adam.core.container import get_container
                container = get_container()
                cache_key = f"adam:atom_outputs:{decision_id}"
                cached = await container.redis_cache.get(cache_key)
                if cached:
                    mech_output = cached.get("atom_mechanism_activation", {})
                    if isinstance(mech_output, dict):
                        inferential_chains = (
                            mech_output.get("secondary_assessments", {}).get("inferential_chains", [])
                            or mech_output.get("inferential_chains", [])
                        )
            except Exception as e:
                logger.debug(f"Failed to load chains from cache: {e}")
        
        if not inferential_chains:
            return {"skipped": True, "reason": "no_inferential_chains"}
        
        # Process all chains
        result = learner.process_all_chains_for_decision(
            inferential_chains=inferential_chains,
            decision_id=decision_id,
            success=success,
            outcome_value=outcome_value,
        )
        
        # Periodically push updates to Neo4j (every 50 outcomes)
        if learner.stats["total_outcomes"] % 50 == 0 and learner.stats["total_outcomes"] > 0:
            try:
                from adam.core.container import get_container
                container = get_container()
                if hasattr(container, '_neo4j_driver') and container._neo4j_driver:
                    with container._neo4j_driver.session() as session:
                        updated = learner.update_neo4j_link_strengths(session)
                        result["neo4j_links_updated"] = updated
            except Exception as e:
                logger.debug(f"Periodic Neo4j update failed: {e}")
        
        # Add theory learner stats
        result["learner_stats"] = learner.stats
        
        return result
    
    async def _update_ml_ensemble(
        self,
        decision_id: str,
        success: bool,
        metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Update ML ensemble weights based on outcome."""
        if not metadata.get("ml_available", False):
            return {"skipped": True}
        
        from adam.ml.hybrid_extractor import get_hybrid_extractor
        
        extractor = get_hybrid_extractor()
        
        # Get predictions from metadata
        ndf_profile = metadata.get("ndf_profile", {})
        predicted = sum(ndf_profile.values()) / max(len(ndf_profile), 1)
        
        extractor.update_weights(
            outcome_success=success,
            rule_prediction=predicted,
            ml_prediction=metadata.get("ml_ndf_agreement", 0.5),
        )
        
        return {"ensemble_updated": True}
    
    @property
    def stats(self) -> Dict[str, int]:
        """Get handler statistics."""
        return {
            "outcomes_processed": self._outcomes_processed,
            "total_updates": self._total_updates,
        }


# =============================================================================
# SINGLETON
# =============================================================================

_outcome_handler: Optional[OutcomeHandler] = None


def get_outcome_handler() -> OutcomeHandler:
    """Get or create the singleton outcome handler."""
    global _outcome_handler
    if _outcome_handler is None:
        _outcome_handler = OutcomeHandler()
    return _outcome_handler


async def handle_outcome(
    decision_id: str,
    outcome_type: str,
    outcome_value: float = 1.0,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Convenience function to process an outcome.
    
    This is the RECOMMENDED entry point for outcome processing.
    Call this from API endpoints, Kafka consumers, or batch processors.
    
    Example:
        from adam.core.learning.outcome_handler import handle_outcome
        
        result = await handle_outcome(
            decision_id="dec_123",
            outcome_type="conversion",
            outcome_value=1.0,
            metadata={"archetype": "achiever", "mechanisms_applied": ["authority"]}
        )
    """
    handler = get_outcome_handler()
    return await handler.process_outcome(
        decision_id=decision_id,
        outcome_type=outcome_type,
        outcome_value=outcome_value,
        metadata=metadata,
    )
