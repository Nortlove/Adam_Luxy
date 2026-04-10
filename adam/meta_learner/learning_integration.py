# =============================================================================
# ADAM Meta-Learner Learning Integration
# Location: adam/meta_learner/learning_integration.py
# =============================================================================

"""
META-LEARNER LEARNING INTEGRATION

Provides the learning integration wrapper for the Meta-Learner component.

This module re-exports and adapts the comprehensive implementation from
adam.core.learning.component_integrations for use by the container.
"""

import logging
from typing import Dict, List, Optional, Any, Set, Tuple
from datetime import datetime, timezone

from adam.core.learning.universal_learning_interface import (
    LearningCapableComponent,
    LearningSignal,
    LearningSignalType,
    LearningSignalPriority,
    LearningContribution,
    LearningQualityMetrics,
)

logger = logging.getLogger(__name__)


class MetaLearnerLearning(LearningCapableComponent):
    """
    Learning integration for the Meta-Learner (#03).
    
    The Meta-Learner routes requests to optimal execution paths using
    Thompson Sampling. This integration ensures it:
    1. Learns from path outcomes
    2. Updates routing posteriors
    3. Shares routing intelligence with other components
    
    Designed to work with the existing meta_learner.service.
    """
    
    def __init__(self, meta_learner_service):
        """
        Initialize with the meta-learner service.
        
        Args:
            meta_learner_service: The MetaLearnerService instance from container
        """
        self._meta_learner = meta_learner_service
        
        # Tracking
        self._outcomes_processed: int = 0
        self._routing_decisions: Dict[str, Dict] = {}
        self._accuracy_history: List[Tuple[datetime, float]] = []
        
        logger.info("MetaLearnerLearning integration initialized")
    
    @property
    def component_name(self) -> str:
        return "meta_learner"
    
    @property
    def component_version(self) -> str:
        return "2.1"
    
    async def register_routing_decision(
        self,
        decision_id: str,
        user_id: str,
        context: Dict[str, Any],
        selected_modality: str,
        selected_path: str,
        selection_confidence: float
    ) -> None:
        """Register a routing decision for later learning."""
        
        self._routing_decisions[decision_id] = {
            "user_id": user_id,
            "context": context,
            "selected_modality": selected_modality,
            "selected_path": selected_path,
            "selection_confidence": selection_confidence,
            "timestamp": datetime.now(timezone.utc),
        }
        
        logger.debug(f"Routing decision registered: {decision_id} -> {selected_modality}")
    
    async def on_outcome_received(
        self,
        decision_id: str,
        outcome_type: str,
        outcome_value: float,
        context: Dict[str, Any]
    ) -> List[LearningSignal]:
        """Learn from routing outcome."""
        
        signals = []
        
        # Get routing decision
        routing = self._routing_decisions.pop(decision_id, None)
        
        if not routing:
            return []
        
        self._outcomes_processed += 1
        
        # Update Thompson Sampling posteriors if meta-learner supports it
        modality = routing["selected_modality"]
        path = routing["selected_path"]
        
        if hasattr(self._meta_learner, 'update_posterior'):
            try:
                await self._meta_learner.update_posterior(
                    modality=modality,
                    context_features=routing["context"],
                    reward=outcome_value
                )
            except Exception as e:
                logger.warning(f"Failed to update meta-learner posterior: {e}")
        
        # Track accuracy
        predicted = routing["selection_confidence"]
        accuracy = 1.0 - abs(predicted - outcome_value)
        self._accuracy_history.append((datetime.now(timezone.utc), accuracy))
        
        # Keep history bounded
        if len(self._accuracy_history) > 1000:
            self._accuracy_history = self._accuracy_history[-500:]
        
        # 1. Emit modality effectiveness signal
        signals.append(LearningSignal(
            signal_type=LearningSignalType.PRIOR_UPDATED,
            source_component=self.component_name,
            decision_id=decision_id,
            payload={
                "modality": modality,
                "path": path,
                "outcome": outcome_value,
                "context_features": routing["context"],
                "posterior_updated": True,
            },
            confidence=0.85,
            target_components=["gradient_bridge", "monitoring"]
        ))
        
        # 2. Emit routing intelligence for Holistic Synthesizer
        signals.append(LearningSignal(
            signal_type=LearningSignalType.CREDIT_ASSIGNED,
            source_component=self.component_name,
            decision_id=decision_id,
            payload={
                "routing_credit": 1.0 if outcome_value > 0.5 else 0.3,
                "modality_selected": modality,
                "path_selected": path,
            },
            confidence=0.8,
            target_components=["holistic_synthesizer"]
        ))
        
        logger.debug(f"Meta-learner processed outcome for {decision_id}: {outcome_value:.2f}")
        
        return signals
    
    async def on_learning_signal_received(
        self,
        signal: LearningSignal
    ) -> Optional[List[LearningSignal]]:
        """
        Process learning signals from other components.
        
        CRITICAL FIX (Phase 4): Now handles credit and outcome signals
        to update Thompson Sampling posteriors.
        """
        try:
            # ================================================================
            # CREDIT SIGNALS → Update Thompson Sampling
            # ================================================================
            if signal.signal_type == LearningSignalType.CREDIT_ASSIGNED:
                # Extract outcome value and execution path from signal
                decision_id = signal.decision_id or signal.payload.get("decision_id")
                outcome_value = signal.payload.get("outcome_value", signal.payload.get("signal_value", 0.5))
                execution_path = signal.payload.get("execution_path", "")
                modality_str = signal.payload.get("modality", signal.payload.get("meta_learner_modality"))
                
                if decision_id and hasattr(self._meta_learner, 'update_from_outcome'):
                    try:
                        # Map to LearningModality
                        from adam.meta_learner.models import LearningModality
                        try:
                            modality = LearningModality(modality_str) if modality_str else LearningModality.REINFORCEMENT_BANDIT
                        except (ValueError, TypeError):
                            modality = LearningModality.REINFORCEMENT_BANDIT
                        
                        await self._meta_learner.update_from_outcome(
                            decision_id=decision_id,
                            modality=modality,
                            reward=outcome_value,
                        )
                        logger.debug(f"Updated meta-learner Thompson Sampling from credit signal: {decision_id}")
                    except Exception as e:
                        logger.warning(f"Failed to update from credit signal: {e}")
            
            # ================================================================
            # OUTCOME SIGNALS → Update based on outcome type
            # ================================================================
            elif signal.signal_type in {
                LearningSignalType.OUTCOME_CONVERSION,
                LearningSignalType.OUTCOME_CLICK,
                LearningSignalType.OUTCOME_ENGAGEMENT,
            }:
                decision_id = signal.decision_id or signal.payload.get("decision_id")
                if decision_id:
                    # Map outcome type to reward value
                    reward_map = {
                        LearningSignalType.OUTCOME_CONVERSION: 1.0,
                        LearningSignalType.OUTCOME_CLICK: 0.7,
                        LearningSignalType.OUTCOME_ENGAGEMENT: 0.5,
                    }
                    outcome_value = reward_map.get(signal.signal_type, 0.5)
                    
                    # Check if we recorded this decision
                    if decision_id in self._routing_decisions:
                        routing = self._routing_decisions[decision_id]
                        # Update accuracy tracking
                        self._accuracy_history.append(
                            (datetime.now(timezone.utc).isoformat(), outcome_value)
                        )
                        logger.debug(f"Recorded outcome {signal.signal_type.value} for decision {decision_id}")
            
            # ================================================================
            # MECHANISM EFFECTIVENESS → Adjust modality priors
            # ================================================================
            elif signal.signal_type == LearningSignalType.MECHANISM_EFFECTIVENESS_UPDATED:
                mechanism = signal.payload.get("mechanism")
                effectiveness = signal.payload.get("effectiveness", 0.5)
                
                if effectiveness > 0.7 and hasattr(self._meta_learner, 'adjust_modality_prior'):
                    try:
                        await self._meta_learner.adjust_modality_prior(
                            modality="CAUSAL_INFERENCE",
                            adjustment=0.05
                        )
                    except Exception as e:
                        logger.debug(f"Failed to adjust modality prior: {e}")
            
            # ================================================================
            # PRIOR UPDATED → Sync with external updates
            # ================================================================
            elif signal.signal_type == LearningSignalType.PRIOR_UPDATED:
                arm_id = signal.payload.get("arm_updated", signal.payload.get("arm_id"))
                if arm_id:
                    logger.debug(f"Received prior update for arm: {arm_id}")
            
        except Exception as e:
            logger.error(f"Error processing signal {signal.signal_type}: {e}")
        
        return None
    
    def get_consumed_signal_types(self) -> Set[LearningSignalType]:
        return {
            # Attribution and credit signals (for Thompson Sampling updates)
            LearningSignalType.CREDIT_ASSIGNED,
            LearningSignalType.PRIOR_UPDATED,
            # Outcome signals (for modality effectiveness)
            LearningSignalType.OUTCOME_CONVERSION,
            LearningSignalType.OUTCOME_CLICK,
            LearningSignalType.OUTCOME_ENGAGEMENT,
            # Quality signals
            LearningSignalType.MECHANISM_EFFECTIVENESS_UPDATED,
            LearningSignalType.DRIFT_DETECTED,
            LearningSignalType.PREDICTION_FAILED,
        }
    
    async def get_learning_contribution(
        self,
        decision_id: str
    ) -> Optional[LearningContribution]:
        """Get routing contribution to decision."""
        
        routing = self._routing_decisions.get(decision_id)
        if not routing:
            return None
        
        return LearningContribution(
            component_name=self.component_name,
            decision_id=decision_id,
            contribution_type="routing_selection",
            contribution_value={
                "modality": routing["selected_modality"],
                "path": routing["selected_path"],
            },
            confidence=routing["selection_confidence"],
            reasoning_summary=f"Selected {routing['selected_modality']} modality via {routing['selected_path']} path",
            weight=0.3  # Routing contributes ~30% to decision quality
        )
    
    async def get_learning_quality_metrics(self) -> LearningQualityMetrics:
        """Get quality metrics for the meta-learner."""
        
        # Calculate accuracy from history
        if self._accuracy_history:
            recent = [a for _, a in self._accuracy_history[-100:]]
            accuracy = sum(recent) / len(recent)
        else:
            accuracy = 0.5
        
        return LearningQualityMetrics(
            component_name=self.component_name,
            outcomes_processed=self._outcomes_processed,
            prediction_accuracy=accuracy,
            prediction_accuracy_trend=self._compute_trend(),
            attribution_coverage=1.0,  # Routes all decisions
            last_learning_update=datetime.now(timezone.utc),
            upstream_dependencies=["blackboard", "graph_reasoning"],
            downstream_consumers=["atom_of_thought", "fast_path", "reasoning_path"],
            integration_health=0.9
        )
    
    def _compute_trend(self) -> str:
        """Compute accuracy trend."""
        if len(self._accuracy_history) < 20:
            return "stable"
        
        recent = [a for _, a in self._accuracy_history[-10:]]
        older = [a for _, a in self._accuracy_history[-20:-10]]
        
        recent_avg = sum(recent) / len(recent)
        older_avg = sum(older) / len(older)
        
        if recent_avg > older_avg + 0.05:
            return "improving"
        elif recent_avg < older_avg - 0.05:
            return "declining"
        return "stable"
    
    async def inject_priors(self, user_id: str, priors: Dict[str, Any]) -> None:
        """Inject user-specific routing priors."""
        
        modality_priors = priors.get("modality_priors", {})
        if modality_priors and hasattr(self._meta_learner, 'set_user_priors'):
            try:
                await self._meta_learner.set_user_priors(user_id, modality_priors)
            except Exception as e:
                logger.debug(f"Failed to inject priors: {e}")
    
    async def validate_learning_health(self) -> Tuple[bool, List[str]]:
        """Validate learning health."""
        issues = []
        
        if self._outcomes_processed == 0:
            issues.append("No outcomes processed yet")
        
        if len(self._accuracy_history) > 20:
            if self._compute_trend() == "declining":
                issues.append("Routing accuracy is declining")
        
        return len(issues) == 0, issues
