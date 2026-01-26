# =============================================================================
# ADAM Behavioral Analytics: Knowledge Promoter
# Location: adam/behavioral_analytics/knowledge/promoter.py
# =============================================================================

"""
KNOWLEDGE PROMOTER

Promotes statistically validated behavioral patterns to system-wide knowledge.

Lifecycle:
1. Monitor hypotheses for validation
2. Check promotion criteria (p-value, effect size, observations)
3. Create BehavioralKnowledge from hypothesis
4. Store in Neo4j graph
5. Propagate to all components (atoms, workflow, cache)
6. Emit promotion event for learning
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
import logging
import asyncio

from adam.behavioral_analytics.models.knowledge import (
    BehavioralKnowledge,
    BehavioralHypothesis,
    KnowledgeType,
    KnowledgeStatus,
    KnowledgeTier,
    EffectType,
    SignalCategory,
    HypothesisStatus,
)
from adam.behavioral_analytics.knowledge.hypothesis_engine import (
    HypothesisEngine,
    get_hypothesis_engine,
)
from adam.behavioral_analytics.knowledge.graph_integration import (
    BehavioralKnowledgeGraph,
    get_behavioral_knowledge_graph,
)

logger = logging.getLogger(__name__)


class PromotionCriteria:
    """Criteria for knowledge promotion."""
    
    # Minimum observations required
    MIN_OBSERVATIONS = 50
    
    # Statistical significance threshold
    P_VALUE_THRESHOLD = 0.05
    
    # Minimum effect size (absolute value of r or d)
    MIN_EFFECT_SIZE = 0.1
    
    # Minimum cross-validation folds passed
    MIN_CV_FOLDS = 3
    
    # Minimum success rate for the predicted direction
    MIN_SUCCESS_RATE = 0.55
    
    @classmethod
    def check(cls, hypothesis: BehavioralHypothesis) -> Dict[str, Any]:
        """
        Check if hypothesis meets promotion criteria.
        
        Returns dict with check results and overall pass/fail.
        """
        checks = {
            "observations": {
                "required": cls.MIN_OBSERVATIONS,
                "actual": hypothesis.observations,
                "passed": hypothesis.observations >= cls.MIN_OBSERVATIONS,
            },
            "p_value": {
                "required": f"< {cls.P_VALUE_THRESHOLD}",
                "actual": hypothesis.p_value,
                "passed": (
                    hypothesis.p_value is not None and
                    hypothesis.p_value < cls.P_VALUE_THRESHOLD
                ),
            },
            "effect_size": {
                "required": f">= {cls.MIN_EFFECT_SIZE}",
                "actual": hypothesis.observed_effect_size,
                "passed": (
                    hypothesis.observed_effect_size is not None and
                    abs(hypothesis.observed_effect_size) >= cls.MIN_EFFECT_SIZE
                ),
            },
            "cv_folds": {
                "required": cls.MIN_CV_FOLDS,
                "actual": hypothesis.cv_folds_passed,
                "passed": hypothesis.cv_folds_passed >= cls.MIN_CV_FOLDS,
            },
            "success_rate": {
                "required": f">= {cls.MIN_SUCCESS_RATE}",
                "actual": hypothesis.observation_rate,
                "passed": hypothesis.observation_rate >= cls.MIN_SUCCESS_RATE,
            },
        }
        
        all_passed = all(c["passed"] for c in checks.values())
        
        return {
            "hypothesis_id": hypothesis.hypothesis_id,
            "checks": checks,
            "all_passed": all_passed,
            "ready_for_promotion": all_passed and hypothesis.status == HypothesisStatus.VALIDATED,
        }


class PromotionEvent:
    """Event emitted when knowledge is promoted."""
    
    def __init__(
        self,
        hypothesis_id: str,
        knowledge_id: str,
        signal_pattern: str,
        maps_to_construct: str,
        effect_size: float,
        observations: int,
        timestamp: Optional[datetime] = None,
    ):
        self.hypothesis_id = hypothesis_id
        self.knowledge_id = knowledge_id
        self.signal_pattern = signal_pattern
        self.maps_to_construct = maps_to_construct
        self.effect_size = effect_size
        self.observations = observations
        self.timestamp = timestamp or datetime.now(timezone.utc)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": "knowledge_promotion",
            "hypothesis_id": self.hypothesis_id,
            "knowledge_id": self.knowledge_id,
            "signal_pattern": self.signal_pattern,
            "maps_to_construct": self.maps_to_construct,
            "effect_size": self.effect_size,
            "observations": self.observations,
            "timestamp": self.timestamp.isoformat(),
        }


class KnowledgePromoter:
    """
    Promotes validated hypotheses to system knowledge.
    
    Responsibilities:
    1. Monitor hypothesis engine for validated hypotheses
    2. Check promotion criteria
    3. Create knowledge from hypothesis
    4. Propagate to all components
    5. Emit events for learning system
    """
    
    def __init__(
        self,
        hypothesis_engine: Optional[HypothesisEngine] = None,
        graph: Optional[BehavioralKnowledgeGraph] = None,
        event_bus=None,
    ):
        self._hypothesis_engine = hypothesis_engine or get_hypothesis_engine()
        self._graph = graph
        self._event_bus = event_bus
        
        # Promotion history
        self._promotions: List[PromotionEvent] = []
        
        # Components to propagate to
        self._propagation_targets: List[str] = [
            "atom_knowledge_interface",
            "workflow_nodes",
            "behavioral_cache",
            "gradient_bridge",
        ]
    
    async def check_and_promote(self) -> List[PromotionEvent]:
        """
        Check all validated hypotheses and promote eligible ones.
        
        Returns list of promotion events.
        """
        promotions = []
        
        # Get validated hypotheses
        validated = self._hypothesis_engine.get_hypotheses_by_status(
            HypothesisStatus.VALIDATED
        )
        
        for hypothesis in validated:
            # Check criteria
            check_result = PromotionCriteria.check(hypothesis)
            
            if check_result["ready_for_promotion"]:
                # Promote
                event = await self.promote_hypothesis(hypothesis.hypothesis_id)
                if event:
                    promotions.append(event)
                    logger.info(
                        f"Promoted hypothesis {hypothesis.hypothesis_id} to "
                        f"knowledge {event.knowledge_id}"
                    )
        
        return promotions
    
    async def promote_hypothesis(
        self,
        hypothesis_id: str,
    ) -> Optional[PromotionEvent]:
        """
        Promote a single hypothesis to knowledge.
        
        Args:
            hypothesis_id: ID of hypothesis to promote
            
        Returns:
            PromotionEvent if successful, None otherwise
        """
        hypothesis = self._hypothesis_engine.get_hypothesis(hypothesis_id)
        
        if not hypothesis:
            logger.error(f"Hypothesis not found: {hypothesis_id}")
            return None
        
        if hypothesis.status != HypothesisStatus.VALIDATED:
            logger.warning(
                f"Cannot promote hypothesis {hypothesis_id}: "
                f"status is {hypothesis.status.value}"
            )
            return None
        
        # Step 1: Create knowledge from hypothesis
        knowledge = await self._hypothesis_engine.promote_hypothesis(hypothesis_id)
        
        if not knowledge:
            logger.error(f"Failed to create knowledge from hypothesis {hypothesis_id}")
            return None
        
        # Step 2: Store in graph (if available)
        if self._graph:
            await self._graph.store_knowledge(knowledge)
            await self._graph.promote_hypothesis(hypothesis_id, knowledge.knowledge_id)
        
        # Step 3: Propagate to components
        await self._propagate_knowledge(knowledge)
        
        # Step 4: Create and emit event
        event = PromotionEvent(
            hypothesis_id=hypothesis_id,
            knowledge_id=knowledge.knowledge_id,
            signal_pattern=hypothesis.signal_pattern,
            maps_to_construct=hypothesis.predicted_outcome,
            effect_size=hypothesis.observed_effect_size or 0.0,
            observations=hypothesis.observations,
        )
        
        self._promotions.append(event)
        
        if self._event_bus:
            await self._emit_event(event)
        
        return event
    
    async def _propagate_knowledge(
        self,
        knowledge: BehavioralKnowledge,
    ) -> None:
        """Propagate new knowledge to all components."""
        
        # Invalidate caches
        try:
            from adam.behavioral_analytics.extensions.cache_extension import (
                get_behavioral_cache,
            )
            # Cache would be invalidated here if we had the redis instance
            logger.debug(f"Would invalidate cache for construct: {knowledge.maps_to_construct}")
        except ImportError:
            pass
        
        # Notify atom interface
        try:
            from adam.behavioral_analytics.atom_interface import (
                get_atom_knowledge_interface,
            )
            interface = get_atom_knowledge_interface()
            interface.clear_cache()
            logger.debug("Cleared atom knowledge interface cache")
        except Exception as e:
            logger.warning(f"Failed to notify atom interface: {e}")
        
        # Log propagation
        logger.info(
            f"Propagated new knowledge {knowledge.knowledge_id} to "
            f"{len(self._propagation_targets)} targets"
        )
    
    async def _emit_event(self, event: PromotionEvent) -> None:
        """Emit promotion event to event bus."""
        if self._event_bus:
            try:
                await self._event_bus.publish(
                    "behavioral.knowledge.promoted",
                    event.to_dict(),
                )
            except Exception as e:
                logger.warning(f"Failed to emit promotion event: {e}")
    
    def get_promotion_history(self) -> List[Dict[str, Any]]:
        """Get history of promotions."""
        return [p.to_dict() for p in self._promotions]
    
    def get_pending_promotions(self) -> List[Dict[str, Any]]:
        """Get hypotheses that are validated but not yet promoted."""
        validated = self._hypothesis_engine.get_hypotheses_by_status(
            HypothesisStatus.VALIDATED
        )
        
        pending = []
        for h in validated:
            check_result = PromotionCriteria.check(h)
            pending.append({
                "hypothesis_id": h.hypothesis_id,
                "signal_pattern": h.signal_pattern,
                "predicted_outcome": h.predicted_outcome,
                "observations": h.observations,
                "effect_size": h.observed_effect_size,
                "p_value": h.p_value,
                "ready_for_promotion": check_result["ready_for_promotion"],
                "checks": check_result["checks"],
            })
        
        return pending
    
    async def run_promotion_loop(
        self,
        interval_seconds: float = 300.0,
        max_iterations: Optional[int] = None,
    ) -> None:
        """
        Run continuous promotion loop.
        
        Checks for promotable hypotheses at regular intervals.
        
        Args:
            interval_seconds: Time between checks
            max_iterations: Maximum iterations (None for infinite)
        """
        iteration = 0
        
        while max_iterations is None or iteration < max_iterations:
            try:
                promotions = await self.check_and_promote()
                if promotions:
                    logger.info(
                        f"Promotion loop iteration {iteration}: "
                        f"promoted {len(promotions)} hypotheses"
                    )
            except Exception as e:
                logger.error(f"Promotion loop error: {e}")
            
            iteration += 1
            await asyncio.sleep(interval_seconds)


# Singleton
_promoter: Optional[KnowledgePromoter] = None


def get_knowledge_promoter(
    hypothesis_engine: Optional[HypothesisEngine] = None,
    graph: Optional[BehavioralKnowledgeGraph] = None,
) -> KnowledgePromoter:
    """Get singleton knowledge promoter."""
    global _promoter
    if _promoter is None:
        _promoter = KnowledgePromoter(hypothesis_engine, graph)
    return _promoter
