# =============================================================================
# ADAM Behavioral Analytics Learning Integration
# Location: adam/behavioral_analytics/learning_integration.py
# =============================================================================

"""
BEHAVIORAL ANALYTICS LEARNING INTEGRATION

Provides the learning integration wrapper for the Behavioral Analytics engine.

The Behavioral Analytics engine processes nonconscious signals (touch, gaze,
keystroke dynamics, etc.) to infer psychological states. This integration
ensures it participates in the universal learning architecture.

Key capabilities:
1. Learn which behavioral signals predict outcomes
2. Update signal weights based on validated predictions
3. Share behavioral insights with other components
4. Track classifier accuracy over time
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


class BehavioralAnalyticsLearning(LearningCapableComponent):
    """
    Learning integration for Behavioral Analytics.
    
    Integrates the 13 behavioral classifiers with the learning system:
    - Purchase Intent Classifier
    - Emotional State Classifier
    - Cognitive Load Classifier
    - Decision Confidence Classifier
    - Personality Inferencer
    - Advertising Effectiveness Classifier
    - Approach/Avoidance Detector
    - Cognitive State Estimator
    - Regulatory Focus Detector
    - Evolutionary Motive Detector
    - Memory Optimizer
    - Moral Foundations Targeting
    - Temporal Targeting
    
    Each classifier's predictions are validated against outcomes
    and weights are updated accordingly.
    """
    
    def __init__(self, behavioral_engine):
        """
        Initialize with the behavioral analytics engine.
        
        Args:
            behavioral_engine: The BehavioralAnalyticsEngine instance
        """
        self._engine = behavioral_engine
        
        # Tracking
        self._outcomes_processed: int = 0
        self._classifier_accuracy: Dict[str, List[float]] = {}
        self._signal_contributions: Dict[str, List[float]] = {}
        
        # Classifiers we track (Phase 6: All 13 classifiers now wired)
        self._classifiers = [
            # Core classifiers
            "purchase_intent",
            "emotional_state", 
            "cognitive_load",
            "decision_confidence",
            "personality",
            "advertising_effectiveness",
            # Advanced classifiers (Phase 6: Previously unwired)
            "evolutionary_motive",
            "moral_foundations",
            "memory_optimization",
            "approach_avoidance",
            "temporal_targeting",
            "cognitive_state",
            "regulatory_focus",
            "advertising_effectiveness",
            "approach_avoidance",
            "cognitive_state",
            "regulatory_focus",
            "evolutionary_motive",
            "memory",
            "moral_foundations",
            "temporal",
        ]
        
        logger.info("BehavioralAnalyticsLearning integration initialized")
    
    @property
    def component_name(self) -> str:
        return "behavioral_analytics"
    
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
        """
        Learn from behavioral prediction outcomes.
        
        Validates each classifier's prediction against the actual outcome
        and updates accuracy tracking.
        """
        
        signals = []
        self._outcomes_processed += 1
        
        # Get the behavioral analysis that was used for this decision
        behavioral_context = context.get("behavioral_analysis", {})
        
        if not behavioral_context:
            return []
        
        # Validate each classifier's prediction
        validations = {}
        for classifier in self._classifiers:
            prediction_key = f"{classifier}_prediction"
            if prediction_key in behavioral_context:
                predicted = behavioral_context[prediction_key]
                
                # Calculate accuracy (how close prediction was to outcome)
                if isinstance(predicted, (int, float)):
                    accuracy = 1.0 - abs(predicted - outcome_value)
                    
                    # Track accuracy
                    if classifier not in self._classifier_accuracy:
                        self._classifier_accuracy[classifier] = []
                    self._classifier_accuracy[classifier].append(accuracy)
                    
                    # Keep bounded
                    if len(self._classifier_accuracy[classifier]) > 500:
                        self._classifier_accuracy[classifier] = self._classifier_accuracy[classifier][-250:]
                    
                    validations[classifier] = {
                        "predicted": predicted,
                        "actual": outcome_value,
                        "accuracy": accuracy,
                    }
        
        if validations:
            # 1. Emit classifier validation signal
            signals.append(LearningSignal(
                signal_type=LearningSignalType.BEHAVIORAL_PATTERN_VALIDATED,
                source_component=self.component_name,
                decision_id=decision_id,
                payload={
                    "classifier_validations": validations,
                    "mean_accuracy": sum(v["accuracy"] for v in validations.values()) / len(validations),
                    "classifiers_validated": len(validations),
                },
                confidence=0.8,
                target_components=["gradient_bridge", "meta_learner"]
            ))
        
        # 2. Track signal contributions
        signal_weights = context.get("behavioral_signal_weights", {})
        for signal_name, weight in signal_weights.items():
            if signal_name not in self._signal_contributions:
                self._signal_contributions[signal_name] = []
            
            # Contribution = weight * outcome (positive outcomes reinforce)
            contribution = weight * outcome_value
            self._signal_contributions[signal_name].append(contribution)
        
        # 3. Emit signal effectiveness update if we have enough data
        if len(self._signal_contributions) > 0:
            top_signals = self._get_top_signals()
            if top_signals:
                signals.append(LearningSignal(
                    signal_type=LearningSignalType.SIGNAL_QUALITY_UPDATED,
                    source_component=self.component_name,
                    decision_id=decision_id,
                    payload={
                        "top_signals": top_signals,
                        "signal_count": len(self._signal_contributions),
                    },
                    confidence=0.7,
                    target_components=["gradient_bridge", "hypothesis_engine"]
                ))
        
        logger.debug(
            f"Behavioral analytics processed outcome for {decision_id}: "
            f"{len(validations)} classifiers validated"
        )
        
        return signals
    
    def _get_top_signals(self) -> Dict[str, float]:
        """Get the top contributing signals."""
        scores = {}
        for signal_name, contributions in self._signal_contributions.items():
            if len(contributions) >= 10:
                scores[signal_name] = sum(contributions[-50:]) / len(contributions[-50:])
        
        # Return top 5
        sorted_signals = sorted(scores.items(), key=lambda x: -x[1])
        return dict(sorted_signals[:5])
    
    async def on_learning_signal_received(
        self,
        signal: LearningSignal
    ) -> Optional[List[LearningSignal]]:
        """
        Process learning signals from other components.
        
        Behavioral analytics can adjust signal weights based on
        mechanism effectiveness updates from other components.
        """
        
        if signal.signal_type == LearningSignalType.MECHANISM_EFFECTIVENESS_UPDATED:
            # If certain mechanisms are more effective, adjust related signal weights
            mechanism = signal.payload.get("mechanism")
            effectiveness = signal.payload.get("effectiveness", 0.5)
            
            # Signal-mechanism mappings
            signal_mechanism_map = {
                "scarcity": ["response_latency", "cognitive_load"],
                "social_proof": ["eye_tracking", "dwell_time"],
                "authority": ["scroll_depth", "engagement_time"],
                "urgency": ["click_speed", "purchase_intent"],
            }
            
            related_signals = signal_mechanism_map.get(mechanism, [])
            if related_signals and hasattr(self._engine, 'adjust_signal_weights'):
                try:
                    await self._engine.adjust_signal_weights(
                        signals=related_signals,
                        adjustment=effectiveness - 0.5  # -0.5 to 0.5 adjustment
                    )
                except Exception as e:
                    logger.debug(f"Failed to adjust signal weights: {e}")
        
        return None
    
    def get_consumed_signal_types(self) -> Set[LearningSignalType]:
        return {
            LearningSignalType.MECHANISM_EFFECTIVENESS_UPDATED,
            LearningSignalType.PRIOR_UPDATED,
            LearningSignalType.DRIFT_DETECTED,
        }
    
    async def get_learning_contribution(
        self,
        decision_id: str
    ) -> Optional[LearningContribution]:
        """Get behavioral analytics contribution to decision."""
        
        # We contributed if any classifiers were active
        active_classifiers = [c for c in self._classifiers if c in self._classifier_accuracy]
        
        if not active_classifiers:
            return None
        
        return LearningContribution(
            component_name=self.component_name,
            decision_id=decision_id,
            contribution_type="behavioral_inference",
            contribution_value={
                "classifiers_active": active_classifiers,
            },
            confidence=0.75,
            reasoning_summary=f"Inferred psychological state via {len(active_classifiers)} behavioral classifiers",
            weight=0.25  # Behavioral analytics contributes ~25% to decision
        )
    
    async def get_learning_quality_metrics(self) -> LearningQualityMetrics:
        """Get quality metrics for behavioral analytics."""
        
        # Calculate overall classifier accuracy
        if self._classifier_accuracy:
            all_accuracies = []
            for accuracies in self._classifier_accuracy.values():
                all_accuracies.extend(accuracies[-100:])
            mean_accuracy = sum(all_accuracies) / len(all_accuracies) if all_accuracies else 0.5
        else:
            mean_accuracy = 0.5
        
        return LearningQualityMetrics(
            component_name=self.component_name,
            outcomes_processed=self._outcomes_processed,
            prediction_accuracy=mean_accuracy,
            prediction_accuracy_trend=self._compute_trend(),
            attribution_coverage=len(self._classifier_accuracy) / len(self._classifiers),
            last_learning_update=datetime.now(timezone.utc),
            upstream_dependencies=["behavioral_signals", "session_data"],
            downstream_consumers=["atom_of_thought", "holistic_synthesizer", "ad_selection"],
            integration_health=0.85
        )
    
    def _compute_trend(self) -> str:
        """Compute accuracy trend across classifiers."""
        if not self._classifier_accuracy:
            return "stable"
        
        # Get combined recent vs older accuracy
        recent_all = []
        older_all = []
        
        for accuracies in self._classifier_accuracy.values():
            if len(accuracies) >= 20:
                recent_all.extend(accuracies[-10:])
                older_all.extend(accuracies[-20:-10])
        
        if not recent_all or not older_all:
            return "stable"
        
        recent_avg = sum(recent_all) / len(recent_all)
        older_avg = sum(older_all) / len(older_all)
        
        if recent_avg > older_avg + 0.05:
            return "improving"
        elif recent_avg < older_avg - 0.05:
            return "declining"
        return "stable"
    
    async def inject_priors(self, user_id: str, priors: Dict[str, Any]) -> None:
        """Inject user-specific behavioral priors."""
        
        behavioral_priors = priors.get("behavioral_priors", {})
        if behavioral_priors and hasattr(self._engine, 'set_user_priors'):
            try:
                await self._engine.set_user_priors(user_id, behavioral_priors)
            except Exception as e:
                logger.debug(f"Failed to inject behavioral priors: {e}")
    
    async def validate_learning_health(self) -> Tuple[bool, List[str]]:
        """Validate learning health."""
        issues = []
        
        if self._outcomes_processed == 0:
            issues.append("No outcomes processed yet")
        
        # Check for poorly performing classifiers
        for classifier, accuracies in self._classifier_accuracy.items():
            if len(accuracies) >= 20:
                recent_accuracy = sum(accuracies[-20:]) / 20
                if recent_accuracy < 0.4:
                    issues.append(f"Classifier {classifier} has low accuracy: {recent_accuracy:.2f}")
        
        return len(issues) == 0, issues
    
    def get_classifier_stats(self) -> Dict[str, Any]:
        """Get detailed stats for each classifier."""
        stats = {}
        for classifier in self._classifiers:
            accuracies = self._classifier_accuracy.get(classifier, [])
            stats[classifier] = {
                "samples": len(accuracies),
                "recent_accuracy": sum(accuracies[-20:]) / 20 if len(accuracies) >= 20 else None,
                "overall_accuracy": sum(accuracies) / len(accuracies) if accuracies else None,
            }
        return stats
