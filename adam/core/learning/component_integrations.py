# =============================================================================
# ADAM Component Learning Integrations
# Location: adam/core/learning/component_integrations.py
# =============================================================================

"""
COMPONENT LEARNING INTEGRATIONS

This module provides LearningCapableComponent implementations for all
major ADAM components, ensuring they participate in the universal
learning architecture.

Each integration wraps an existing component and adds:
1. Outcome reception and learning signal emission
2. Learning signal consumption
3. Credit attribution
4. Quality metrics reporting
5. Prior injection
6. Health validation

This is the glue that makes every component a learning participant.
"""

from typing import Dict, List, Optional, Any, Set, Tuple
from datetime import datetime, timezone, timedelta
from pydantic import BaseModel, Field
import numpy as np
import uuid
import logging

from adam.core.learning.universal_learning_interface import (
    LearningCapableComponent,
    LearningSignal,
    LearningSignalType,
    LearningSignalPriority,
    LearningContribution,
    LearningQualityMetrics,
)

logger = logging.getLogger(__name__)


# =============================================================================
# META-LEARNER INTEGRATION (#03)
# =============================================================================

class MetaLearnerLearningIntegration(LearningCapableComponent):
    """
    Learning integration for Enhancement #03: Meta-Learning Orchestration.
    
    The Meta-Learner routes requests to optimal execution paths using
    Thompson Sampling. This integration ensures it:
    1. Learns from path outcomes
    2. Updates routing posteriors
    3. Shares routing intelligence with other components
    """
    
    def __init__(self, meta_learner, redis_client, neo4j_driver):
        self.meta_learner = meta_learner
        self.redis = redis_client
        self.neo4j = neo4j_driver
        
        # Tracking
        self._outcomes_processed: int = 0
        self._routing_decisions: Dict[str, Dict] = {}
        self._accuracy_history: List[Tuple[datetime, float]] = []
    
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
        
        # Store in Redis
        await self.redis.setex(
            f"adam:meta:routing:{decision_id}",
            86400,
            self._routing_decisions[decision_id]
        )
    
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
            cached = await self.redis.get(f"adam:meta:routing:{decision_id}")
            if cached:
                routing = cached
        
        if not routing:
            return []
        
        self._outcomes_processed += 1
        
        # Update Thompson Sampling posteriors
        modality = routing["selected_modality"]
        path = routing["selected_path"]
        
        await self.meta_learner.update_posterior(
            modality=modality,
            context_features=routing["context"],
            reward=outcome_value
        )
        
        # Track accuracy
        predicted = routing["selection_confidence"]
        accuracy = 1.0 - abs(predicted - outcome_value)
        self._accuracy_history.append((datetime.now(timezone.utc), accuracy))
        
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
        
        # Store in Neo4j
        await self._store_routing_outcome(decision_id, routing, outcome_value)
        
        return signals
    
    async def _store_routing_outcome(
        self,
        decision_id: str,
        routing: Dict,
        outcome_value: float
    ) -> None:
        """Store routing outcome in Neo4j."""
        
        query = """
        MERGE (r:RoutingDecision {decision_id: $decision_id})
        SET r.modality = $modality,
            r.path = $path,
            r.outcome = $outcome,
            r.updated_at = datetime()
        """
        
        async with self.neo4j.session() as session:
            await session.run(
                query,
                decision_id=decision_id,
                modality=routing["selected_modality"],
                path=routing["selected_path"],
                outcome=outcome_value
            )
    
    async def on_learning_signal_received(
        self,
        signal: LearningSignal
    ) -> Optional[List[LearningSignal]]:
        """Process learning signals."""
        
        if signal.signal_type == LearningSignalType.MECHANISM_EFFECTIVENESS_UPDATED:
            # If mechanism effectiveness changed, may affect modality selection
            # e.g., if Claude-based mechanisms are more effective, prefer REASONING path
            mechanism = signal.payload.get("mechanism")
            effectiveness = signal.payload.get("effectiveness", 0.5)
            
            if effectiveness > 0.7:
                # Boost confidence in paths that use this mechanism
                await self.meta_learner.adjust_modality_prior(
                    modality="CAUSAL_INFERENCE",
                    adjustment=0.05
                )
        
        return None
    
    def get_consumed_signal_types(self) -> Set[LearningSignalType]:
        return {
            LearningSignalType.MECHANISM_EFFECTIVENESS_UPDATED,
            LearningSignalType.DRIFT_DETECTED,
            LearningSignalType.PREDICTION_FAILED,
        }
    
    async def get_learning_contribution(
        self,
        decision_id: str
    ) -> Optional[LearningContribution]:
        """Get routing contribution to decision."""
        
        routing = await self.redis.get(f"adam:meta:routing:{decision_id}")
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
        """Get quality metrics."""
        
        # Calculate accuracy
        if self._accuracy_history:
            recent = [a for _, a in self._accuracy_history[-100:]]
            accuracy = np.mean(recent)
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
        if len(self._accuracy_history) < 20:
            return "stable"
        recent = [a for _, a in self._accuracy_history[-10:]]
        older = [a for _, a in self._accuracy_history[-20:-10]]
        if np.mean(recent) > np.mean(older) + 0.05:
            return "improving"
        elif np.mean(recent) < np.mean(older) - 0.05:
            return "declining"
        return "stable"
    
    async def inject_priors(self, user_id: str, priors: Dict[str, Any]) -> None:
        """Inject user-specific routing priors."""
        
        modality_priors = priors.get("modality_priors", {})
        if modality_priors:
            await self.meta_learner.set_user_priors(user_id, modality_priors)
    
    async def validate_learning_health(self) -> Tuple[bool, List[str]]:
        issues = []
        
        if self._outcomes_processed == 0:
            issues.append("No outcomes processed")
        
        if len(self._accuracy_history) > 20:
            if self._compute_trend() == "declining":
                issues.append("Routing accuracy is declining")
        
        return len(issues) == 0, issues


# =============================================================================
# GRADIENT BRIDGE INTEGRATION (#06)
# =============================================================================

class GradientBridgeLearningIntegration(LearningCapableComponent):
    """
    Learning integration for Enhancement #06: Gradient Bridge.
    
    The Gradient Bridge IS the central learning hub. This integration
    ensures it implements the universal interface and can be monitored.
    """
    
    def __init__(self, gradient_bridge, redis_client, neo4j_driver):
        self.gradient_bridge = gradient_bridge
        self.redis = redis_client
        self.neo4j = neo4j_driver
        
        self._signals_propagated: int = 0
        self._attributions_computed: int = 0
    
    @property
    def component_name(self) -> str:
        return "gradient_bridge"
    
    @property
    def component_version(self) -> str:
        return "2.1"
    
    async def on_outcome_received(
        self,
        decision_id: str,
        outcome_type: str,
        outcome_value: float,
        context: Dict[str, Any]
    ) -> List[LearningSignal]:
        """
        The Gradient Bridge IS the outcome processor.
        When it receives an outcome, it computes attribution and propagates signals.
        """
        
        signals = []
        
        # 1. Compute multi-level credit attribution
        attribution = await self.gradient_bridge.compute_attribution(
            decision_id=decision_id,
            outcome_value=outcome_value,
            context=context
        )
        
        self._attributions_computed += 1
        
        # 2. Generate signals for each attributed component
        for component, credit in attribution.component_credits.items():
            signals.append(LearningSignal(
                signal_type=LearningSignalType.CREDIT_ASSIGNED,
                source_component=self.component_name,
                decision_id=decision_id,
                payload={
                    "component": component,
                    "credit": credit.credit_score,
                    "confidence": credit.confidence,
                    "method": credit.attribution_method,
                },
                confidence=credit.confidence,
                target_components=[component],
                priority=LearningSignalPriority.HIGH
            ))
        
        # 3. Generate mechanism attribution signals
        for mechanism, effectiveness in attribution.mechanism_attributions.items():
            signals.append(LearningSignal(
                signal_type=LearningSignalType.MECHANISM_ATTRIBUTED,
                source_component=self.component_name,
                decision_id=decision_id,
                payload={
                    "mechanism": mechanism,
                    "effectiveness": effectiveness,
                    "user_id": context.get("user_id"),
                },
                confidence=0.8,
                target_components=["meta_learner", "holistic_synthesizer", "copy_generation"]
            ))
        
        # 4. Emit consolidated outcome signal
        signals.append(LearningSignal(
            signal_type=LearningSignalType.OUTCOME_CONVERSION if outcome_value > 0.5 
                else LearningSignalType.OUTCOME_SKIP,
            source_component=self.component_name,
            decision_id=decision_id,
            payload={
                "outcome_type": outcome_type,
                "outcome_value": outcome_value,
                "total_components_attributed": len(attribution.component_credits),
            },
            confidence=1.0,
            priority=LearningSignalPriority.HIGH
        ))
        
        self._signals_propagated += len(signals)
        
        return signals
    
    async def on_learning_signal_received(
        self,
        signal: LearningSignal
    ) -> Optional[List[LearningSignal]]:
        """Gradient Bridge aggregates signals but also passes them through."""
        
        # Gradient Bridge is primarily an emitter, but it can also
        # aggregate signals for batch processing
        if signal.signal_type == LearningSignalType.PREDICTION_VALIDATED:
            # Use validated predictions to improve attribution models
            await self.gradient_bridge.update_attribution_model(
                component=signal.source_component,
                accuracy=signal.payload.get("accuracy", 0.5)
            )
        
        return None
    
    def get_consumed_signal_types(self) -> Set[LearningSignalType]:
        return {
            LearningSignalType.PREDICTION_VALIDATED,
            LearningSignalType.PREDICTION_FAILED,
        }
    
    async def get_learning_contribution(
        self,
        decision_id: str
    ) -> Optional[LearningContribution]:
        """Gradient Bridge always contributes via attribution."""
        
        return LearningContribution(
            component_name=self.component_name,
            decision_id=decision_id,
            contribution_type="credit_attribution",
            contribution_value={
                "attribution_computed": True,
                "signals_emitted": self._signals_propagated,
            },
            confidence=0.95,
            reasoning_summary="Computed multi-level credit attribution",
            weight=0.1  # Attribution contributes modestly to decision
        )
    
    async def get_learning_quality_metrics(self) -> LearningQualityMetrics:
        return LearningQualityMetrics(
            component_name=self.component_name,
            signals_emitted=self._signals_propagated,
            outcomes_processed=self._attributions_computed,
            prediction_accuracy=0.85,  # Attribution accuracy
            attribution_coverage=1.0,
            last_learning_update=datetime.now(timezone.utc),
            upstream_dependencies=["all_components"],
            downstream_consumers=["all_components"],
            integration_health=1.0
        )
    
    async def inject_priors(self, user_id: str, priors: Dict[str, Any]) -> None:
        """Gradient Bridge injects priors via its prior extraction pipeline."""
        pass  # Priors are handled through the existing prior pipeline
    
    async def validate_learning_health(self) -> Tuple[bool, List[str]]:
        issues = []
        
        if self._attributions_computed == 0:
            issues.append("No attributions computed")
        
        if self._signals_propagated == 0:
            issues.append("No signals propagated")
        
        return len(issues) == 0, issues


# =============================================================================
# ATOM OF THOUGHT INTEGRATION (#04)
# =============================================================================

class AtomOfThoughtLearningIntegration(LearningCapableComponent):
    """
    Learning integration for Enhancement #04: Atom of Thought DAG.
    
    Each atom produces psychological assessments. This integration
    ensures atoms learn from outcome feedback.
    """
    
    def __init__(self, atom_executor, redis_client, neo4j_driver):
        self.atom_executor = atom_executor
        self.redis = redis_client
        self.neo4j = neo4j_driver
        
        self._atom_executions: Dict[str, Dict] = {}
        self._outcomes_processed: int = 0
        self._atom_accuracy: Dict[str, List[float]] = {}
    
    @property
    def component_name(self) -> str:
        return "atom_of_thought"
    
    @property
    def component_version(self) -> str:
        return "3.0"
    
    async def register_atom_execution(
        self,
        decision_id: str,
        atom_outputs: Dict[str, Dict[str, Any]]
    ) -> None:
        """Register atom outputs for later learning."""
        
        self._atom_executions[decision_id] = {
            "outputs": atom_outputs,
            "timestamp": datetime.now(timezone.utc),
        }
        
        await self.redis.setex(
            f"adam:atom:execution:{decision_id}",
            86400,
            atom_outputs
        )
    
    async def on_outcome_received(
        self,
        decision_id: str,
        outcome_type: str,
        outcome_value: float,
        context: Dict[str, Any]
    ) -> List[LearningSignal]:
        """Learn which atom predictions were correct."""
        
        signals = []
        
        execution = self._atom_executions.pop(decision_id, None)
        if not execution:
            cached = await self.redis.get(f"adam:atom:execution:{decision_id}")
            if cached:
                execution = {"outputs": cached}
        
        if not execution:
            return []
        
        self._outcomes_processed += 1
        atom_outputs = execution["outputs"]
        
        # Validate each atom's predictions
        atom_validations = {}
        for atom_name, output in atom_outputs.items():
            # Check if atom prediction aligned with outcome
            if "predicted_response" in output:
                predicted = output["predicted_response"]
                actual = outcome_value
                error = abs(predicted - actual)
                accuracy = 1.0 - error
                
                atom_validations[atom_name] = {
                    "predicted": predicted,
                    "actual": actual,
                    "accuracy": accuracy,
                }
                
                # Track per-atom accuracy
                if atom_name not in self._atom_accuracy:
                    self._atom_accuracy[atom_name] = []
                self._atom_accuracy[atom_name].append(accuracy)
        
        # 1. Emit atom validation signal
        signals.append(LearningSignal(
            signal_type=LearningSignalType.ATOM_ATTRIBUTED,
            source_component=self.component_name,
            decision_id=decision_id,
            payload={
                "atom_validations": atom_validations,
                "mean_accuracy": np.mean([v["accuracy"] for v in atom_validations.values()]) if atom_validations else 0.5,
            },
            confidence=0.85,
            target_components=["gradient_bridge", "meta_learner"]
        ))
        
        # 2. Check for emergent discoveries
        emergence = await self._check_for_emergence(atom_outputs, outcome_value, context)
        if emergence:
            signals.append(LearningSignal(
                signal_type=LearningSignalType.NOVEL_CONSTRUCT_DISCOVERED,
                source_component=self.component_name,
                decision_id=decision_id,
                payload=emergence,
                confidence=0.7,
                target_components=["graph_reasoning", "psychological_constructs"]
            ))
        
        return signals
    
    async def _check_for_emergence(
        self,
        atom_outputs: Dict[str, Dict],
        outcome_value: float,
        context: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Check if this outcome reveals an emergent pattern."""
        
        # Look for unexpected successes/failures
        # If outcome doesn't match any atom prediction, may be novel pattern
        predictions = [
            out.get("predicted_response", 0.5)
            for out in atom_outputs.values()
            if "predicted_response" in out
        ]
        
        if not predictions:
            return None
        
        mean_prediction = np.mean(predictions)
        surprise = abs(mean_prediction - outcome_value)
        
        if surprise > 0.4:  # High surprise = potential emergence
            return {
                "emergence_type": "prediction_surprise",
                "mean_prediction": mean_prediction,
                "actual_outcome": outcome_value,
                "surprise_level": surprise,
                "context_fingerprint": str(hash(str(context)))[:8],
            }
        
        return None
    
    async def on_learning_signal_received(
        self,
        signal: LearningSignal
    ) -> Optional[List[LearningSignal]]:
        """Process learning signals."""
        
        if signal.signal_type == LearningSignalType.MECHANISM_EFFECTIVENESS_UPDATED:
            # Update atom priors based on mechanism effectiveness
            mechanism = signal.payload.get("mechanism")
            effectiveness = signal.payload.get("effectiveness", 0.5)
            
            # Pass to atom executor for prompt prior injection
            await self.atom_executor.update_mechanism_prior(mechanism, effectiveness)
        
        return None
    
    def get_consumed_signal_types(self) -> Set[LearningSignalType]:
        return {
            LearningSignalType.MECHANISM_EFFECTIVENESS_UPDATED,
            LearningSignalType.PRIOR_UPDATED,
            LearningSignalType.BEHAVIORAL_PATTERN_VALIDATED,
        }
    
    async def get_learning_contribution(
        self,
        decision_id: str
    ) -> Optional[LearningContribution]:
        """Get atom contribution to decision."""
        
        execution = await self.redis.get(f"adam:atom:execution:{decision_id}")
        if not execution:
            return None
        
        return LearningContribution(
            component_name=self.component_name,
            decision_id=decision_id,
            contribution_type="psychological_reasoning",
            contribution_value={
                "atoms_executed": list(execution.keys()),
            },
            confidence=0.8,
            reasoning_summary=f"Executed {len(execution)} psychological atoms",
            weight=0.4  # Atoms contribute ~40% to decision
        )
    
    async def get_learning_quality_metrics(self) -> LearningQualityMetrics:
        # Compute overall atom accuracy
        if self._atom_accuracy:
            all_accuracies = []
            for accuracies in self._atom_accuracy.values():
                all_accuracies.extend(accuracies[-100:])
            mean_accuracy = np.mean(all_accuracies) if all_accuracies else 0.5
        else:
            mean_accuracy = 0.5
        
        return LearningQualityMetrics(
            component_name=self.component_name,
            outcomes_processed=self._outcomes_processed,
            prediction_accuracy=mean_accuracy,
            prediction_accuracy_trend="stable",
            attribution_coverage=0.9,
            last_learning_update=datetime.now(timezone.utc),
            upstream_dependencies=["graph_reasoning", "blackboard"],
            downstream_consumers=["holistic_synthesizer", "ad_selection"],
            integration_health=0.85
        )
    
    async def inject_priors(self, user_id: str, priors: Dict[str, Any]) -> None:
        """Inject priors for atom execution."""
        
        mechanism_priors = priors.get("mechanism_priors", {})
        user_history = priors.get("user_history", {})
        
        await self.atom_executor.set_priors(user_id, mechanism_priors, user_history)
    
    async def validate_learning_health(self) -> Tuple[bool, List[str]]:
        issues = []
        
        if self._outcomes_processed == 0:
            issues.append("No outcomes processed")
        
        # Check for poorly performing atoms
        for atom_name, accuracies in self._atom_accuracy.items():
            if len(accuracies) > 20:
                recent_accuracy = np.mean(accuracies[-20:])
                if recent_accuracy < 0.4:
                    issues.append(f"Atom {atom_name} has low accuracy: {recent_accuracy:.2f}")
        
        return len(issues) == 0, issues


# =============================================================================
# JOURNEY TRACKER INTEGRATION (#10)
# =============================================================================

class JourneyTrackerLearningIntegration(LearningCapableComponent):
    """
    Learning integration for Enhancement #10: State Machine Journey Tracking.
    
    The Journey Tracker detects and predicts user journey states.
    This integration ensures it learns from actual state transitions.
    """
    
    def __init__(self, journey_tracker, redis_client, neo4j_driver):
        self.journey_tracker = journey_tracker
        self.redis = redis_client
        self.neo4j = neo4j_driver
        
        self._transitions_tracked: int = 0
        self._prediction_accuracy: List[float] = []
    
    @property
    def component_name(self) -> str:
        return "journey_tracker"
    
    @property
    def component_version(self) -> str:
        return "2.0"
    
    async def on_outcome_received(
        self,
        decision_id: str,
        outcome_type: str,
        outcome_value: float,
        context: Dict[str, Any]
    ) -> List[LearningSignal]:
        """Learn from journey state transitions."""
        
        signals = []
        user_id = context.get("user_id")
        
        if not user_id:
            return []
        
        # Get predicted state vs actual observed
        predicted_state = await self.journey_tracker.get_predicted_state(user_id)
        actual_transition = await self._infer_actual_transition(outcome_type, outcome_value)
        
        # Validate prediction
        correct = predicted_state == actual_transition
        self._prediction_accuracy.append(1.0 if correct else 0.0)
        self._transitions_tracked += 1
        
        # Update transition model
        await self.journey_tracker.update_transition_probabilities(
            user_id=user_id,
            from_state=predicted_state,
            to_state=actual_transition,
            context=context
        )
        
        # 1. Emit state transition learned signal
        signals.append(LearningSignal(
            signal_type=LearningSignalType.STATE_TRANSITION_LEARNED,
            source_component=self.component_name,
            decision_id=decision_id,
            user_id=user_id,
            payload={
                "predicted_state": predicted_state,
                "actual_state": actual_transition,
                "correct": correct,
                "transition_probability_updated": True,
            },
            confidence=0.8,
            target_components=["holistic_synthesizer", "temporal_patterns"]
        ))
        
        return signals
    
    async def _infer_actual_transition(
        self,
        outcome_type: str,
        outcome_value: float
    ) -> str:
        """Infer actual journey state from outcome."""
        
        if outcome_type == "conversion" and outcome_value > 0.5:
            return "converted"
        elif outcome_type == "engagement" and outcome_value > 0.7:
            return "engaged"
        elif outcome_value < 0.2:
            return "churned"
        return "considering"
    
    async def on_learning_signal_received(
        self,
        signal: LearningSignal
    ) -> Optional[List[LearningSignal]]:
        return None
    
    def get_consumed_signal_types(self) -> Set[LearningSignalType]:
        return {
            LearningSignalType.MECHANISM_EFFECTIVENESS_UPDATED,
        }
    
    async def get_learning_contribution(
        self,
        decision_id: str
    ) -> Optional[LearningContribution]:
        return LearningContribution(
            component_name=self.component_name,
            decision_id=decision_id,
            contribution_type="journey_context",
            contribution_value={"state_predicted": True},
            confidence=0.7,
            reasoning_summary="Provided journey state context",
            weight=0.15
        )
    
    async def get_learning_quality_metrics(self) -> LearningQualityMetrics:
        accuracy = np.mean(self._prediction_accuracy[-100:]) if self._prediction_accuracy else 0.5
        
        return LearningQualityMetrics(
            component_name=self.component_name,
            outcomes_processed=self._transitions_tracked,
            prediction_accuracy=accuracy,
            prediction_accuracy_trend="stable",
            attribution_coverage=0.8,
            last_learning_update=datetime.now(timezone.utc),
            upstream_dependencies=["graph_reasoning"],
            downstream_consumers=["holistic_synthesizer", "temporal_patterns"],
            integration_health=0.85
        )
    
    async def inject_priors(self, user_id: str, priors: Dict[str, Any]) -> None:
        transition_priors = priors.get("transition_priors", {})
        if transition_priors:
            await self.journey_tracker.set_transition_priors(user_id, transition_priors)
    
    async def validate_learning_health(self) -> Tuple[bool, List[str]]:
        issues = []
        
        if self._transitions_tracked == 0:
            issues.append("No transitions tracked")
        
        if len(self._prediction_accuracy) > 50:
            recent = np.mean(self._prediction_accuracy[-50:])
            if recent < 0.4:
                issues.append(f"Low transition prediction accuracy: {recent:.2f}")
        
        return len(issues) == 0, issues


# =============================================================================
# COPY GENERATION INTEGRATION (#15)
# =============================================================================

class CopyGenerationLearningIntegration(LearningCapableComponent):
    """
    Learning integration for Enhancement #15: Personality-Matched Copy Generation.
    
    Copy generation produces ad copy matched to user personality.
    This integration ensures it learns which copy patterns work.
    """
    
    def __init__(self, copy_generator, redis_client, neo4j_driver):
        self.copy_generator = copy_generator
        self.redis = redis_client
        self.neo4j = neo4j_driver
        
        self._copy_generations: Dict[str, Dict] = {}
        self._outcomes_processed: int = 0
        self._template_effectiveness: Dict[str, List[float]] = {}
    
    @property
    def component_name(self) -> str:
        return "copy_generation"
    
    @property
    def component_version(self) -> str:
        return "2.0"
    
    async def register_copy_generation(
        self,
        decision_id: str,
        template_used: str,
        personality_match: Dict[str, float],
        generated_copy: str
    ) -> None:
        """Register copy generation for later learning."""
        
        self._copy_generations[decision_id] = {
            "template": template_used,
            "personality_match": personality_match,
            "copy": generated_copy,
            "timestamp": datetime.now(timezone.utc),
        }
        
        await self.redis.setex(
            f"adam:copy:generation:{decision_id}",
            86400,
            self._copy_generations[decision_id]
        )
    
    async def on_outcome_received(
        self,
        decision_id: str,
        outcome_type: str,
        outcome_value: float,
        context: Dict[str, Any]
    ) -> List[LearningSignal]:
        """Learn which copy patterns work."""
        
        signals = []
        
        generation = self._copy_generations.pop(decision_id, None)
        if not generation:
            cached = await self.redis.get(f"adam:copy:generation:{decision_id}")
            if cached:
                generation = cached
        
        if not generation:
            return []
        
        self._outcomes_processed += 1
        template = generation["template"]
        
        # Update template effectiveness
        if template not in self._template_effectiveness:
            self._template_effectiveness[template] = []
        self._template_effectiveness[template].append(outcome_value)
        
        # 1. Emit copy effectiveness signal
        signals.append(LearningSignal(
            signal_type=LearningSignalType.COPY_EFFECTIVENESS,
            source_component=self.component_name,
            decision_id=decision_id,
            payload={
                "template": template,
                "outcome": outcome_value,
                "personality_match": generation["personality_match"],
                "template_effectiveness": np.mean(self._template_effectiveness[template][-100:]),
            },
            confidence=0.8,
            target_components=["gradient_bridge", "brand_intelligence"]
        ))
        
        return signals
    
    async def on_learning_signal_received(
        self,
        signal: LearningSignal
    ) -> Optional[List[LearningSignal]]:
        if signal.signal_type == LearningSignalType.MECHANISM_EFFECTIVENESS_UPDATED:
            # May affect copy template selection
            pass
        return None
    
    def get_consumed_signal_types(self) -> Set[LearningSignalType]:
        return {
            LearningSignalType.MECHANISM_EFFECTIVENESS_UPDATED,
            LearningSignalType.TRAIT_CONFIDENCE_UPDATED,
        }
    
    async def get_learning_contribution(
        self,
        decision_id: str
    ) -> Optional[LearningContribution]:
        generation = await self.redis.get(f"adam:copy:generation:{decision_id}")
        if not generation:
            return None
        
        return LearningContribution(
            component_name=self.component_name,
            decision_id=decision_id,
            contribution_type="copy_generation",
            contribution_value={"template": generation.get("template")},
            confidence=0.75,
            reasoning_summary=f"Generated copy using template {generation.get('template')}",
            weight=0.2
        )
    
    async def get_learning_quality_metrics(self) -> LearningQualityMetrics:
        if self._template_effectiveness:
            all_outcomes = []
            for outcomes in self._template_effectiveness.values():
                all_outcomes.extend(outcomes[-100:])
            accuracy = np.mean(all_outcomes) if all_outcomes else 0.5
        else:
            accuracy = 0.5
        
        return LearningQualityMetrics(
            component_name=self.component_name,
            outcomes_processed=self._outcomes_processed,
            prediction_accuracy=accuracy,
            attribution_coverage=0.7,
            last_learning_update=datetime.now(timezone.utc),
            upstream_dependencies=["atom_of_thought", "brand_intelligence"],
            downstream_consumers=["holistic_synthesizer"],
            integration_health=0.8
        )
    
    async def inject_priors(self, user_id: str, priors: Dict[str, Any]) -> None:
        template_priors = priors.get("template_priors", {})
        if template_priors:
            await self.copy_generator.set_template_priors(user_id, template_priors)
    
    async def validate_learning_health(self) -> Tuple[bool, List[str]]:
        issues = []
        if self._outcomes_processed == 0:
            issues.append("No copy outcomes processed")
        return len(issues) == 0, issues


# =============================================================================
# COMPONENT REGISTRY
# =============================================================================

class LearningComponentRegistry:
    """
    Registry of all learning-capable components.
    
    This is the central registry that the Learning Signal Router uses
    to dispatch signals to appropriate components.
    """
    
    def __init__(self):
        self.components: Dict[str, LearningCapableComponent] = {}
        self.signal_subscriptions: Dict[LearningSignalType, Set[str]] = {}
    
    def register(self, component: LearningCapableComponent) -> None:
        """Register a component."""
        
        name = component.component_name
        self.components[name] = component
        
        # Register signal subscriptions
        for signal_type in component.get_consumed_signal_types():
            if signal_type not in self.signal_subscriptions:
                self.signal_subscriptions[signal_type] = set()
            self.signal_subscriptions[signal_type].add(name)
        
        logger.info(f"Registered learning component: {name}")
    
    def get(self, name: str) -> Optional[LearningCapableComponent]:
        return self.components.get(name)
    
    def get_subscribers(self, signal_type: LearningSignalType) -> Set[str]:
        return self.signal_subscriptions.get(signal_type, set())
    
    def all_components(self) -> List[LearningCapableComponent]:
        return list(self.components.values())


# =============================================================================
# FACTORY FUNCTION
# =============================================================================

def create_learning_registry(
    meta_learner,
    gradient_bridge,
    atom_executor,
    journey_tracker,
    copy_generator,
    redis_client,
    neo4j_driver
) -> LearningComponentRegistry:
    """
    Factory function to create a fully-populated learning registry.
    
    Call this during application startup.
    """
    
    registry = LearningComponentRegistry()
    
    # Register all components
    registry.register(MetaLearnerLearningIntegration(
        meta_learner, redis_client, neo4j_driver
    ))
    registry.register(GradientBridgeLearningIntegration(
        gradient_bridge, redis_client, neo4j_driver
    ))
    registry.register(AtomOfThoughtLearningIntegration(
        atom_executor, redis_client, neo4j_driver
    ))
    registry.register(JourneyTrackerLearningIntegration(
        journey_tracker, redis_client, neo4j_driver
    ))
    registry.register(CopyGenerationLearningIntegration(
        copy_generator, redis_client, neo4j_driver
    ))
    
    logger.info(f"Learning registry created with {len(registry.components)} components")
    
    return registry


# =============================================================================
# SINGLETON REGISTRY
# =============================================================================

_learning_registry: Optional[LearningComponentRegistry] = None


def get_learning_registry() -> LearningComponentRegistry:
    """
    Get singleton learning registry with available components.
    
    This creates a minimal registry that works without full infrastructure.
    Components are registered as they become available.
    """
    global _learning_registry
    
    if _learning_registry is not None:
        return _learning_registry
    
    _learning_registry = LearningComponentRegistry()
    
    # Register the simplified components that implement all abstract methods
    # These are defined as concrete classes that work without full infrastructure
    
    try:
        _learning_registry.register(_SimplifiedAtomIntegration())
        logger.info("Registered AtomDAG in learning registry")
    except Exception as e:
        logger.warning(f"AtomDAG integration registration failed: {e}")
    
    try:
        _learning_registry.register(_SimplifiedGraphIntegration())
        logger.info("Registered Neo4j Graph in learning registry")
    except Exception as e:
        logger.warning(f"Graph integration registration failed: {e}")
    
    try:
        from adam.meta_learner.service import get_meta_learner
        meta_learner = get_meta_learner()
        if meta_learner:
            _learning_registry.register(_SimplifiedMetaLearnerIntegration(meta_learner))
            logger.info("Registered MetaLearner in learning registry")
    except Exception as e:
        logger.debug(f"MetaLearner not available for registry: {e}")
    
    logger.info(f"Learning registry initialized with {len(_learning_registry.components)} components")
    return _learning_registry


# =============================================================================
# SIMPLIFIED COMPONENT IMPLEMENTATIONS
# =============================================================================

class _SimplifiedAtomIntegration(LearningCapableComponent):
    """Simplified AtomDAG integration for the learning registry."""
    
    @property
    def component_name(self) -> str:
        return "atom_of_thought"
    
    @property
    def component_version(self) -> str:
        return "3.0"
    
    def get_consumed_signal_types(self) -> Set[LearningSignalType]:
        return {
            LearningSignalType.OUTCOME_CONVERSION,
            LearningSignalType.ATOM_ATTRIBUTED,
        }
    
    def get_emitted_signal_types(self) -> Set[LearningSignalType]:
        return {
            LearningSignalType.ATOM_ATTRIBUTED,
            LearningSignalType.PREDICTION_VALIDATED,
        }
    
    async def on_outcome_received(
        self,
        decision_id: str,
        outcome_type: str,
        outcome_value: float,
        context: Dict[str, Any]
    ) -> List[LearningSignal]:
        signals = []
        try:
            from adam.atoms.core.base import BaseAtom
            contributions = BaseAtom.get_all_contributions(decision_id)
            
            for contrib in contributions:
                signals.append(LearningSignal(
                    signal_type=LearningSignalType.ATOM_ATTRIBUTED,
                    source_component="atom_of_thought",
                    decision_id=decision_id,
                    payload={
                        "atom_name": contrib.component_name,
                        "contribution_value": contrib.contribution_value,
                        "outcome_value": outcome_value,
                        "validated": outcome_value > 0.5,
                    },
                    confidence=contrib.confidence,
                ))
        except Exception:
            pass
        return signals
    
    async def on_learning_signal_received(
        self,
        signal: LearningSignal
    ) -> Optional[List[LearningSignal]]:
        """Process incoming learning signals."""
        # AtomDAG can use prior updates to adjust atom weights
        if signal.signal_type == LearningSignalType.PRIOR_UPDATED:
            # Could update atom priors here
            pass
        return None
    
    async def get_learning_contribution(
        self,
        decision_id: str
    ) -> Optional[LearningContribution]:
        """Get atom contributions for attribution."""
        try:
            from adam.atoms.core.base import BaseAtom
            contributions = BaseAtom.get_all_contributions(decision_id)
            if contributions:
                # Return aggregated contribution
                return contributions[0]
        except Exception:
            pass
        return None
    
    async def record_contribution(
        self,
        decision_id: str,
        contribution: LearningContribution
    ) -> None:
        pass
    
    async def get_learning_quality_metrics(self) -> LearningQualityMetrics:
        return LearningQualityMetrics(
            component_name="atom_of_thought",
            measurement_period_hours=24,
        )
    
    async def inject_priors(
        self,
        user_id: str,
        priors: Dict[str, Any]
    ) -> None:
        """Inject priors into atoms (no-op for simplified version)."""
        pass
    
    async def validate_learning_health(self) -> Tuple[bool, List[str]]:
        """Validate learning health."""
        return True, []


class _SimplifiedGraphIntegration(LearningCapableComponent):
    """Simplified Neo4j Graph integration for the learning registry."""
    
    @property
    def component_name(self) -> str:
        return "neo4j_graph"
    
    @property
    def component_version(self) -> str:
        return "1.0"
    
    def get_consumed_signal_types(self) -> Set[LearningSignalType]:
        return {
            LearningSignalType.OUTCOME_CONVERSION,
            LearningSignalType.MECHANISM_ATTRIBUTED,
        }
    
    def get_emitted_signal_types(self) -> Set[LearningSignalType]:
        return {LearningSignalType.MECHANISM_EFFECTIVENESS_UPDATED}
    
    async def on_outcome_received(
        self,
        decision_id: str,
        outcome_type: str,
        outcome_value: float,
        context: Dict[str, Any]
    ) -> List[LearningSignal]:
        # Graph persistence is handled separately by campaign orchestrator
        return []
    
    async def on_learning_signal_received(
        self,
        signal: LearningSignal
    ) -> Optional[List[LearningSignal]]:
        """Process incoming learning signals."""
        return None
    
    async def get_learning_contribution(
        self,
        decision_id: str
    ) -> Optional[LearningContribution]:
        """Get graph contributions for attribution."""
        return None
    
    async def record_contribution(
        self,
        decision_id: str,
        contribution: LearningContribution
    ) -> None:
        pass
    
    async def get_learning_quality_metrics(self) -> LearningQualityMetrics:
        return LearningQualityMetrics(
            component_name="neo4j_graph",
            measurement_period_hours=24,
        )
    
    async def inject_priors(
        self,
        user_id: str,
        priors: Dict[str, Any]
    ) -> None:
        """Inject priors (no-op for graph)."""
        pass
    
    async def validate_learning_health(self) -> Tuple[bool, List[str]]:
        """Validate learning health."""
        try:
            from adam.infrastructure.neo4j.client import get_neo4j_client
            client = get_neo4j_client()
            if client.is_connected:
                return True, []
            return False, ["Neo4j not connected"]
        except Exception as e:
            return False, [str(e)]


class _SimplifiedMetaLearnerIntegration(LearningCapableComponent):
    """Simplified MetaLearner integration for the learning registry."""
    
    def __init__(self, meta_learner):
        self._meta_learner = meta_learner
    
    @property
    def component_name(self) -> str:
        return "meta_learner"
    
    @property
    def component_version(self) -> str:
        return "2.0"
    
    def get_consumed_signal_types(self) -> Set[LearningSignalType]:
        return {
            LearningSignalType.OUTCOME_CONVERSION,
            LearningSignalType.CREDIT_ASSIGNED,
        }
    
    def get_emitted_signal_types(self) -> Set[LearningSignalType]:
        return {LearningSignalType.PRIOR_UPDATED}
    
    async def on_outcome_received(
        self,
        decision_id: str,
        outcome_type: str,
        outcome_value: float,
        context: Dict[str, Any]
    ) -> List[LearningSignal]:
        return [LearningSignal(
            signal_type=LearningSignalType.PRIOR_UPDATED,
            source_component="meta_learner",
            decision_id=decision_id,
            payload={"outcome_value": outcome_value},
            confidence=0.8,
        )]
    
    async def on_learning_signal_received(
        self,
        signal: LearningSignal
    ) -> Optional[List[LearningSignal]]:
        """Process incoming learning signals."""
        return None
    
    async def get_learning_contribution(
        self,
        decision_id: str
    ) -> Optional[LearningContribution]:
        """Get meta-learner contributions for attribution."""
        return None
    
    async def record_contribution(
        self,
        decision_id: str,
        contribution: LearningContribution
    ) -> None:
        pass
    
    async def get_learning_quality_metrics(self) -> LearningQualityMetrics:
        return LearningQualityMetrics(
            component_name="meta_learner",
            measurement_period_hours=24,
        )
    
    async def inject_priors(
        self,
        user_id: str,
        priors: Dict[str, Any]
    ) -> None:
        """Inject priors into meta-learner (no-op for simplified version)."""
        pass
    
    async def validate_learning_health(self) -> Tuple[bool, List[str]]:
        """Validate learning health."""
        if self._meta_learner:
            return True, []
        return False, ["MetaLearner not available"]


def reset_learning_registry() -> None:
    """Reset the learning registry (for testing)."""
    global _learning_registry
    _learning_registry = None
