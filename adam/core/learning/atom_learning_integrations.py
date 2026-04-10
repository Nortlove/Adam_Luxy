# =============================================================================
# ADAM Atom Learning Integrations
# Location: adam/core/learning/atom_learning_integrations.py
# =============================================================================

"""
ATOM LEARNING INTEGRATIONS

This module provides LearningCapableComponent implementations for all
individual ADAM atoms, ensuring they fully participate in the deep
learning architecture.

Each atom integration:
1. Emits learning signals when predictions are made
2. Receives outcome feedback and updates posteriors
3. Tracks prediction accuracy over time
4. Participates in credit attribution
5. Reports quality metrics

Atoms integrated:
- UserStateAtom
- PersonalityExpressionAtom
- RegulatoryFocusAtom
- ConstrualLevelAtom
- BrandPersonalityAtom
- RelationshipIntelligenceAtom
- MechanismActivationAtom
- MessageFramingAtom
- AdSelectionAtom
- ChannelSelectionAtom
"""

from typing import Dict, List, Optional, Any, Set, Tuple
from datetime import datetime, timezone, timedelta
from pydantic import BaseModel, Field
import logging
from collections import defaultdict

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
# BASE ATOM LEARNING INTEGRATION
# =============================================================================

class BaseAtomLearningIntegration(LearningCapableComponent):
    """
    Base class for all atom learning integrations.
    
    Provides common functionality:
    - Prediction tracking
    - Outcome processing
    - Accuracy computation
    - Signal emission
    - Posterior updates
    """
    
    def __init__(self, atom_instance, atom_name: str):
        self.atom = atom_instance
        self._atom_name = atom_name
        
        # Prediction tracking
        self._predictions: Dict[str, Dict[str, Any]] = {}
        self._outcomes_processed: int = 0
        self._signals_emitted: int = 0
        
        # Accuracy tracking
        self._accuracy_history: List[Tuple[datetime, float]] = []
        self._accuracy_by_context: Dict[str, List[float]] = defaultdict(list)
        
        # Posterior state (for Bayesian updates)
        self._posterior_alpha: Dict[str, float] = defaultdict(lambda: 1.0)
        self._posterior_beta: Dict[str, float] = defaultdict(lambda: 1.0)
    
    @property
    def component_name(self) -> str:
        return f"atom_{self._atom_name}"
    
    @property
    def component_version(self) -> str:
        return "1.0"
    
    async def register_prediction(
        self,
        decision_id: str,
        prediction: Dict[str, Any],
        confidence: float,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Register a prediction for later learning."""
        self._predictions[decision_id] = {
            "prediction": prediction,
            "confidence": confidence,
            "context": context or {},
            "timestamp": datetime.now(timezone.utc),
        }
    
    async def on_outcome_received(
        self,
        decision_id: str,
        outcome_type: str,
        outcome_value: float,
        context: Dict[str, Any],
    ) -> List[LearningSignal]:
        """Learn from outcome feedback."""
        signals = []
        
        # Get stored prediction
        pred_data = self._predictions.pop(decision_id, None)
        if not pred_data:
            return signals
        
        self._outcomes_processed += 1
        prediction = pred_data["prediction"]
        predicted_confidence = pred_data["confidence"]
        pred_context = pred_data["context"]
        
        # Compute accuracy
        accuracy = self._compute_accuracy(prediction, outcome_value, outcome_type)
        
        # Track accuracy
        self._accuracy_history.append((datetime.now(timezone.utc), accuracy))
        
        # Track by context keys
        for key, value in pred_context.items():
            context_key = f"{key}:{value}"
            self._accuracy_by_context[context_key].append(accuracy)
        
        # Update posteriors (Bayesian update)
        await self._update_posteriors(prediction, outcome_value, accuracy)
        
        # Emit prediction validation signal
        signals.append(LearningSignal(
            signal_type=LearningSignalType.PREDICTION_VALIDATED if accuracy > 0.5 else LearningSignalType.PREDICTION_FAILED,
            source_component=self.component_name,
            decision_id=decision_id,
            payload={
                "atom_name": self._atom_name,
                "prediction": prediction,
                "outcome": outcome_value,
                "accuracy": accuracy,
                "predicted_confidence": predicted_confidence,
                "calibration_error": abs(predicted_confidence - accuracy),
            },
            confidence=accuracy,
            priority=LearningSignalPriority.MEDIUM,
            target_components=["gradient_bridge", "meta_learner"],
        ))
        
        self._signals_emitted += 1
        
        # Emit calibration signal if significant miscalibration
        calibration_error = abs(predicted_confidence - accuracy)
        if calibration_error > 0.2:
            signals.append(LearningSignal(
                signal_type=LearningSignalType.CALIBRATION_UPDATED,
                source_component=self.component_name,
                decision_id=decision_id,
                payload={
                    "atom_name": self._atom_name,
                    "calibration_error": calibration_error,
                    "direction": "overconfident" if predicted_confidence > accuracy else "underconfident",
                },
                confidence=0.8,
                priority=LearningSignalPriority.LOW,
            ))
            self._signals_emitted += 1
        
        return signals
    
    def _compute_accuracy(
        self,
        prediction: Dict[str, Any],
        outcome_value: float,
        outcome_type: str,
    ) -> float:
        """Compute accuracy of prediction vs outcome."""
        # Default: use predicted_value if available
        if "predicted_value" in prediction:
            error = abs(prediction["predicted_value"] - outcome_value)
            return max(0.0, 1.0 - error)
        
        # For binary outcomes
        if "predicted_success" in prediction:
            predicted = 1.0 if prediction["predicted_success"] else 0.0
            return 1.0 if abs(predicted - outcome_value) < 0.5 else 0.0
        
        # Default: moderate accuracy
        return 0.5
    
    async def _update_posteriors(
        self,
        prediction: Dict[str, Any],
        outcome_value: float,
        accuracy: float,
    ) -> None:
        """Update Bayesian posteriors based on outcome."""
        # Get prediction key (what we predicted)
        pred_key = prediction.get("key", "default")
        
        # Bayesian update: treat outcome as success/failure
        success = outcome_value > 0.5
        
        if success:
            self._posterior_alpha[pred_key] += 1
        else:
            self._posterior_beta[pred_key] += 1
    
    async def on_learning_signal_received(
        self,
        signal: LearningSignal,
    ) -> Optional[List[LearningSignal]]:
        """Handle incoming learning signals."""
        # Atoms can learn from other atoms' signals
        if signal.signal_type == LearningSignalType.PATTERN_EMERGED:
            # Update internal patterns based on discovered patterns
            await self._incorporate_pattern(signal.payload)
        
        if signal.signal_type == LearningSignalType.PRIOR_UPDATED:
            # Incorporate prior updates from Thompson Sampling
            await self._incorporate_prior_update(signal.payload)
        
        return None
    
    async def _incorporate_pattern(self, pattern_data: Dict[str, Any]) -> None:
        """Incorporate discovered patterns into atom logic."""
        # Override in subclasses for pattern-specific learning
        pass
    
    async def _incorporate_prior_update(self, prior_data: Dict[str, Any]) -> None:
        """Incorporate prior updates from learning system."""
        # Override in subclasses for prior-specific learning
        pass
    
    def get_consumed_signal_types(self) -> Set[LearningSignalType]:
        return {
            LearningSignalType.PATTERN_EMERGED,
            LearningSignalType.PRIOR_UPDATED,
            LearningSignalType.MECHANISM_EFFECTIVENESS_UPDATED,
        }
    
    async def get_learning_contribution(
        self,
        decision_id: str,
    ) -> Optional[LearningContribution]:
        """Report this atom's contribution to a decision."""
        pred_data = self._predictions.get(decision_id)
        if not pred_data:
            return None
        
        return LearningContribution(
            component_name=self.component_name,
            decision_id=decision_id,
            contribution_type="atom_prediction",
            contribution_value=pred_data["prediction"],
            confidence=pred_data["confidence"],
            reasoning_summary=f"{self._atom_name} atom prediction",
            weight=pred_data["confidence"],
        )
    
    async def get_learning_quality_metrics(self) -> LearningQualityMetrics:
        """Report learning quality metrics."""
        # Compute recent accuracy
        recent_accuracy = 0.5
        if self._accuracy_history:
            recent = [a for t, a in self._accuracy_history if t > datetime.now(timezone.utc) - timedelta(hours=24)]
            if recent:
                recent_accuracy = sum(recent) / len(recent)
        
        return LearningQualityMetrics(
            component_name=self.component_name,
            signals_emitted=self._signals_emitted,
            outcomes_processed=self._outcomes_processed,
            prediction_accuracy=recent_accuracy,
            attribution_coverage=1.0 if self._outcomes_processed > 0 else 0.0,
            last_learning_update=self._accuracy_history[-1][0] if self._accuracy_history else None,
            upstream_dependencies=["context_providers"],
            downstream_consumers=["gradient_bridge", "meta_learner"],
            integration_health=1.0 if self._outcomes_processed > 0 else 0.5,
        )
    
    async def inject_priors(self, user_id: str, priors: Dict[str, Any]) -> None:
        """Inject priors for a specific user."""
        for key, value in priors.items():
            if isinstance(value, dict) and "alpha" in value and "beta" in value:
                self._posterior_alpha[f"{user_id}:{key}"] = value["alpha"]
                self._posterior_beta[f"{user_id}:{key}"] = value["beta"]
    
    async def validate_learning_health(self) -> Tuple[bool, List[str]]:
        """Validate learning health."""
        issues = []
        
        if self._outcomes_processed == 0:
            issues.append("No outcomes processed yet")
        
        if self._accuracy_history:
            recent = [a for t, a in self._accuracy_history if t > datetime.now(timezone.utc) - timedelta(hours=1)]
            if recent and sum(recent) / len(recent) < 0.3:
                issues.append("Low recent accuracy")
        
        return len(issues) == 0, issues


# =============================================================================
# PERSONALITY EXPRESSION ATOM INTEGRATION
# =============================================================================

class PersonalityExpressionAtomLearning(BaseAtomLearningIntegration):
    """
    Learning integration for PersonalityExpressionAtom.
    
    Learns:
    - Which Big Five trait combinations lead to engagement
    - How personality expression affects mechanism effectiveness
    - Personality-response correlations
    """
    
    def __init__(self, atom_instance):
        super().__init__(atom_instance, "personality_expression")
        
        # Trait effectiveness tracking
        self._trait_outcomes: Dict[str, List[float]] = defaultdict(list)
    
    def _compute_accuracy(
        self,
        prediction: Dict[str, Any],
        outcome_value: float,
        outcome_type: str,
    ) -> float:
        """Compute accuracy for personality predictions."""
        # Check if predicted dominant trait was effective
        if "dominant_trait" in prediction and "predicted_effectiveness" in prediction:
            predicted_eff = prediction["predicted_effectiveness"]
            return 1.0 - abs(predicted_eff - outcome_value)
        
        return super()._compute_accuracy(prediction, outcome_value, outcome_type)
    
    async def _update_posteriors(
        self,
        prediction: Dict[str, Any],
        outcome_value: float,
        accuracy: float,
    ) -> None:
        """Update trait effectiveness posteriors."""
        await super()._update_posteriors(prediction, outcome_value, accuracy)
        
        # Track outcomes by trait
        if "dominant_trait" in prediction:
            trait = prediction["dominant_trait"]
            self._trait_outcomes[trait].append(outcome_value)


# =============================================================================
# REGULATORY FOCUS ATOM INTEGRATION
# =============================================================================

class RegulatoryFocusAtomLearning(BaseAtomLearningIntegration):
    """
    Learning integration for RegulatoryFocusAtom.
    
    Learns:
    - When promotion vs prevention focus is more effective
    - Focus-context interactions
    - Optimal focus for different user segments
    """
    
    def __init__(self, atom_instance):
        super().__init__(atom_instance, "regulatory_focus")
        
        # Focus effectiveness tracking
        self._promotion_outcomes: List[float] = []
        self._prevention_outcomes: List[float] = []
    
    def _compute_accuracy(
        self,
        prediction: Dict[str, Any],
        outcome_value: float,
        outcome_type: str,
    ) -> float:
        """Compute accuracy for focus predictions."""
        if "predicted_focus" in prediction:
            # Check if predicted focus aligned with outcome
            focus = prediction["predicted_focus"]
            # Promotion focus should correlate with high outcomes
            if focus == "promotion":
                return outcome_value
            else:
                return 1.0 - outcome_value
        
        return super()._compute_accuracy(prediction, outcome_value, outcome_type)
    
    async def _update_posteriors(
        self,
        prediction: Dict[str, Any],
        outcome_value: float,
        accuracy: float,
    ) -> None:
        """Update focus effectiveness posteriors."""
        await super()._update_posteriors(prediction, outcome_value, accuracy)
        
        if "predicted_focus" in prediction:
            if prediction["predicted_focus"] == "promotion":
                self._promotion_outcomes.append(outcome_value)
            else:
                self._prevention_outcomes.append(outcome_value)


# =============================================================================
# CONSTRUAL LEVEL ATOM INTEGRATION
# =============================================================================

class ConstrualLevelAtomLearning(BaseAtomLearningIntegration):
    """
    Learning integration for ConstrualLevelAtom.
    
    Learns:
    - When abstract vs concrete messaging works better
    - Construal-context interactions
    - Optimal construal levels per archetype
    """
    
    def __init__(self, atom_instance):
        super().__init__(atom_instance, "construal_level")
        
        # Construal effectiveness tracking
        self._high_construal_outcomes: List[float] = []
        self._low_construal_outcomes: List[float] = []
    
    async def _update_posteriors(
        self,
        prediction: Dict[str, Any],
        outcome_value: float,
        accuracy: float,
    ) -> None:
        """Update construal effectiveness posteriors."""
        await super()._update_posteriors(prediction, outcome_value, accuracy)
        
        if "construal_level" in prediction:
            level = prediction["construal_level"]
            if level > 0.5:
                self._high_construal_outcomes.append(outcome_value)
            else:
                self._low_construal_outcomes.append(outcome_value)


# =============================================================================
# BRAND PERSONALITY ATOM INTEGRATION
# =============================================================================

class BrandPersonalityAtomLearning(BaseAtomLearningIntegration):
    """
    Learning integration for BrandPersonalityAtom.
    
    Learns:
    - Brand personality-consumer archetype alignment
    - Which brand dimensions drive engagement
    - Brand-mechanism synergies
    """
    
    def __init__(self, atom_instance):
        super().__init__(atom_instance, "brand_personality")
        
        # Brand dimension effectiveness
        self._dimension_outcomes: Dict[str, List[float]] = defaultdict(list)
        self._brand_archetype_outcomes: Dict[str, Dict[str, List[float]]] = defaultdict(lambda: defaultdict(list))
    
    async def _update_posteriors(
        self,
        prediction: Dict[str, Any],
        outcome_value: float,
        accuracy: float,
    ) -> None:
        """Update brand personality posteriors."""
        await super()._update_posteriors(prediction, outcome_value, accuracy)
        
        # Track by brand dimension
        if "dominant_dimension" in prediction:
            dim = prediction["dominant_dimension"]
            self._dimension_outcomes[dim].append(outcome_value)
        
        # Track brand-archetype combinations
        if "brand_id" in prediction and "target_archetype" in prediction:
            brand = prediction["brand_id"]
            archetype = prediction["target_archetype"]
            self._brand_archetype_outcomes[brand][archetype].append(outcome_value)


# =============================================================================
# RELATIONSHIP INTELLIGENCE ATOM INTEGRATION
# =============================================================================

class RelationshipIntelligenceAtomLearning(BaseAtomLearningIntegration):
    """
    Learning integration for RelationshipIntelligenceAtom.
    
    Learns:
    - Which relationship types respond to which mechanisms
    - Relationship depth and messaging effectiveness
    - Relationship-brand fit patterns
    """
    
    def __init__(self, atom_instance):
        super().__init__(atom_instance, "relationship_intelligence")
        
        # Relationship type effectiveness
        self._relationship_outcomes: Dict[str, List[float]] = defaultdict(list)
        self._relationship_mechanism_outcomes: Dict[str, Dict[str, List[float]]] = defaultdict(lambda: defaultdict(list))
    
    async def _update_posteriors(
        self,
        prediction: Dict[str, Any],
        outcome_value: float,
        accuracy: float,
    ) -> None:
        """Update relationship posteriors."""
        await super()._update_posteriors(prediction, outcome_value, accuracy)
        
        if "relationship_type" in prediction:
            rel_type = prediction["relationship_type"]
            self._relationship_outcomes[rel_type].append(outcome_value)
            
            if "selected_mechanism" in prediction:
                mech = prediction["selected_mechanism"]
                self._relationship_mechanism_outcomes[rel_type][mech].append(outcome_value)


# =============================================================================
# MECHANISM ACTIVATION ATOM INTEGRATION
# =============================================================================

class MechanismActivationAtomLearning(BaseAtomLearningIntegration):
    """
    Learning integration for MechanismActivationAtom.
    
    Learns:
    - Mechanism effectiveness by context
    - Mechanism combinations (synergies)
    - Mechanism-archetype effectiveness
    """
    
    def __init__(self, atom_instance):
        super().__init__(atom_instance, "mechanism_activation")
        
        # Mechanism effectiveness
        self._mechanism_outcomes: Dict[str, List[float]] = defaultdict(list)
        self._mechanism_archetype_outcomes: Dict[str, Dict[str, List[float]]] = defaultdict(lambda: defaultdict(list))
        self._synergy_outcomes: Dict[Tuple[str, str], List[float]] = defaultdict(list)
    
    async def on_outcome_received(
        self,
        decision_id: str,
        outcome_type: str,
        outcome_value: float,
        context: Dict[str, Any],
    ) -> List[LearningSignal]:
        """Learn which mechanisms were effective."""
        signals = await super().on_outcome_received(decision_id, outcome_type, outcome_value, context)
        
        pred_data = self._predictions.get(decision_id)
        if pred_data and "selected_mechanisms" in pred_data.get("prediction", {}):
            mechanisms = pred_data["prediction"]["selected_mechanisms"]
            
            # Emit mechanism effectiveness signal
            signals.append(LearningSignal(
                signal_type=LearningSignalType.MECHANISM_EFFECTIVENESS_UPDATED,
                source_component=self.component_name,
                decision_id=decision_id,
                payload={
                    "mechanisms": mechanisms,
                    "outcome": outcome_value,
                    "context": context,
                },
                confidence=0.8,
                priority=LearningSignalPriority.HIGH,
                target_components=["gradient_bridge", "thompson_sampler"],
            ))
            self._signals_emitted += 1
        
        return signals
    
    async def _update_posteriors(
        self,
        prediction: Dict[str, Any],
        outcome_value: float,
        accuracy: float,
    ) -> None:
        """Update mechanism posteriors."""
        await super()._update_posteriors(prediction, outcome_value, accuracy)
        
        if "selected_mechanisms" in prediction:
            for mech in prediction["selected_mechanisms"]:
                self._mechanism_outcomes[mech].append(outcome_value)
            
            # Track synergies
            mechs = prediction["selected_mechanisms"]
            if len(mechs) >= 2:
                for i in range(len(mechs)):
                    for j in range(i + 1, len(mechs)):
                        pair = tuple(sorted([mechs[i], mechs[j]]))
                        self._synergy_outcomes[pair].append(outcome_value)
        
        if "target_archetype" in prediction and "selected_mechanisms" in prediction:
            archetype = prediction["target_archetype"]
            for mech in prediction["selected_mechanisms"]:
                self._mechanism_archetype_outcomes[mech][archetype].append(outcome_value)


# =============================================================================
# MESSAGE FRAMING ATOM INTEGRATION
# =============================================================================

class MessageFramingAtomLearning(BaseAtomLearningIntegration):
    """
    Learning integration for MessageFramingAtom.
    
    Learns:
    - Which frames (gain vs loss) work for which contexts
    - Frame-archetype effectiveness
    - Frame-mechanism combinations
    """
    
    def __init__(self, atom_instance):
        super().__init__(atom_instance, "message_framing")
        
        self._frame_outcomes: Dict[str, List[float]] = defaultdict(list)
        self._frame_archetype_outcomes: Dict[str, Dict[str, List[float]]] = defaultdict(lambda: defaultdict(list))
    
    async def _update_posteriors(
        self,
        prediction: Dict[str, Any],
        outcome_value: float,
        accuracy: float,
    ) -> None:
        """Update framing posteriors."""
        await super()._update_posteriors(prediction, outcome_value, accuracy)
        
        if "selected_frame" in prediction:
            frame = prediction["selected_frame"]
            self._frame_outcomes[frame].append(outcome_value)
            
            if "target_archetype" in prediction:
                archetype = prediction["target_archetype"]
                self._frame_archetype_outcomes[frame][archetype].append(outcome_value)


# =============================================================================
# AD SELECTION ATOM INTEGRATION
# =============================================================================

class AdSelectionAtomLearning(BaseAtomLearningIntegration):
    """
    Learning integration for AdSelectionAtom.
    
    Learns:
    - Which ad formats work for which contexts
    - Ad-archetype effectiveness
    - Creative element performance
    """
    
    def __init__(self, atom_instance):
        super().__init__(atom_instance, "ad_selection")
        
        self._format_outcomes: Dict[str, List[float]] = defaultdict(list)
        self._creative_outcomes: Dict[str, List[float]] = defaultdict(list)
    
    async def _update_posteriors(
        self,
        prediction: Dict[str, Any],
        outcome_value: float,
        accuracy: float,
    ) -> None:
        """Update ad selection posteriors."""
        await super()._update_posteriors(prediction, outcome_value, accuracy)
        
        if "selected_format" in prediction:
            fmt = prediction["selected_format"]
            self._format_outcomes[fmt].append(outcome_value)
        
        if "creative_id" in prediction:
            creative = prediction["creative_id"]
            self._creative_outcomes[creative].append(outcome_value)


# =============================================================================
# CHANNEL SELECTION ATOM INTEGRATION
# =============================================================================

class ChannelSelectionAtomLearning(BaseAtomLearningIntegration):
    """
    Learning integration for ChannelSelectionAtom.
    
    Learns:
    - Which channels work for which archetypes
    - Channel-daypart effectiveness
    - Channel-format synergies
    """
    
    def __init__(self, atom_instance):
        super().__init__(atom_instance, "channel_selection")
        
        self._channel_outcomes: Dict[str, List[float]] = defaultdict(list)
        self._channel_daypart_outcomes: Dict[str, Dict[str, List[float]]] = defaultdict(lambda: defaultdict(list))
        self._channel_archetype_outcomes: Dict[str, Dict[str, List[float]]] = defaultdict(lambda: defaultdict(list))
    
    async def _update_posteriors(
        self,
        prediction: Dict[str, Any],
        outcome_value: float,
        accuracy: float,
    ) -> None:
        """Update channel selection posteriors."""
        await super()._update_posteriors(prediction, outcome_value, accuracy)
        
        if "selected_channel" in prediction:
            channel = prediction["selected_channel"]
            self._channel_outcomes[channel].append(outcome_value)
            
            if "daypart" in prediction:
                daypart = prediction["daypart"]
                self._channel_daypart_outcomes[channel][daypart].append(outcome_value)
            
            if "target_archetype" in prediction:
                archetype = prediction["target_archetype"]
                self._channel_archetype_outcomes[channel][archetype].append(outcome_value)


# =============================================================================
# USER STATE ATOM INTEGRATION
# =============================================================================

class UserStateAtomLearning(BaseAtomLearningIntegration):
    """
    Learning integration for UserStateAtom.
    
    Learns:
    - User state predictions and their accuracy
    - State transitions and patterns
    - State-effectiveness correlations
    """
    
    def __init__(self, atom_instance):
        super().__init__(atom_instance, "user_state")
        
        self._state_outcomes: Dict[str, List[float]] = defaultdict(list)
        self._state_transitions: Dict[Tuple[str, str], int] = defaultdict(int)
    
    async def _update_posteriors(
        self,
        prediction: Dict[str, Any],
        outcome_value: float,
        accuracy: float,
    ) -> None:
        """Update user state posteriors."""
        await super()._update_posteriors(prediction, outcome_value, accuracy)
        
        if "predicted_state" in prediction:
            state = prediction["predicted_state"]
            self._state_outcomes[state].append(outcome_value)


# =============================================================================
# FACTORY FUNCTION
# =============================================================================

def create_atom_learning_integration(atom_instance, atom_type: str) -> BaseAtomLearningIntegration:
    """
    Factory function to create the appropriate learning integration for an atom.
    
    Args:
        atom_instance: The atom instance to wrap
        atom_type: Type of atom (e.g., "personality_expression", "regulatory_focus")
    
    Returns:
        Appropriate learning integration wrapper
    """
    integrations = {
        "personality_expression": PersonalityExpressionAtomLearning,
        "regulatory_focus": RegulatoryFocusAtomLearning,
        "construal_level": ConstrualLevelAtomLearning,
        "brand_personality": BrandPersonalityAtomLearning,
        "relationship_intelligence": RelationshipIntelligenceAtomLearning,
        "mechanism_activation": MechanismActivationAtomLearning,
        "message_framing": MessageFramingAtomLearning,
        "ad_selection": AdSelectionAtomLearning,
        "channel_selection": ChannelSelectionAtomLearning,
        "user_state": UserStateAtomLearning,
    }
    
    integration_class = integrations.get(atom_type, BaseAtomLearningIntegration)
    return integration_class(atom_instance)


# =============================================================================
# ATOM LEARNING REGISTRY
# =============================================================================

class AtomLearningRegistry:
    """
    Registry for all atom learning integrations.
    
    Manages:
    - Registration of atoms with learning capability
    - Routing of outcomes to appropriate atoms
    - Aggregation of learning signals
    - Health monitoring
    """
    
    def __init__(self):
        self._integrations: Dict[str, BaseAtomLearningIntegration] = {}
        self._decision_atoms: Dict[str, List[str]] = defaultdict(list)
    
    def register_atom(self, atom_instance, atom_type: str) -> BaseAtomLearningIntegration:
        """Register an atom for learning."""
        integration = create_atom_learning_integration(atom_instance, atom_type)
        self._integrations[integration.component_name] = integration
        logger.info(f"Registered atom learning integration: {integration.component_name}")
        return integration
    
    def track_decision(self, decision_id: str, atom_names: List[str]) -> None:
        """Track which atoms contributed to a decision."""
        self._decision_atoms[decision_id] = atom_names
    
    async def process_outcome(
        self,
        decision_id: str,
        outcome_type: str,
        outcome_value: float,
        context: Dict[str, Any],
    ) -> List[LearningSignal]:
        """Route outcome to all participating atoms."""
        all_signals = []
        
        # Get atoms that participated in this decision
        atom_names = self._decision_atoms.pop(decision_id, [])
        
        for atom_name in atom_names:
            integration = self._integrations.get(f"atom_{atom_name}")
            if integration:
                signals = await integration.on_outcome_received(
                    decision_id, outcome_type, outcome_value, context
                )
                all_signals.extend(signals)
        
        return all_signals
    
    async def get_aggregate_metrics(self) -> Dict[str, LearningQualityMetrics]:
        """Get quality metrics for all registered atoms."""
        metrics = {}
        for name, integration in self._integrations.items():
            metrics[name] = await integration.get_learning_quality_metrics()
        return metrics
    
    async def validate_all_health(self) -> Dict[str, Tuple[bool, List[str]]]:
        """Validate health of all atom learning integrations."""
        health = {}
        for name, integration in self._integrations.items():
            health[name] = await integration.validate_learning_health()
        return health


# Singleton registry
_atom_learning_registry: Optional[AtomLearningRegistry] = None


def get_atom_learning_registry() -> AtomLearningRegistry:
    """Get the singleton atom learning registry."""
    global _atom_learning_registry
    if _atom_learning_registry is None:
        _atom_learning_registry = AtomLearningRegistry()
    return _atom_learning_registry
