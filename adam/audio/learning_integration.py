# =============================================================================
# ADAM Enhancement #07: Audio Learning Integration
# Location: adam/audio/learning_integration.py
# =============================================================================

"""
AUDIO LEARNING INTEGRATION

This module makes Voice/Audio Processing (#07) a full participant in
ADAM's learning ecosystem.

CRITICAL INSIGHT:
Audio is 40% of consumption in screenless environments. The audio signals
ARE nonconscious indicators - arousal from voice prosody, emotional state
from pitch patterns, personality inference from speaking style.

These signals must:
1. Be validated against outcomes (Did high arousal predict conversion?)
2. Update the Nonconscious Analytics source in #01
3. Contribute to the Gradient Bridge for credit attribution
4. Learn which audio features are predictive for which users

WITHOUT THIS, audio is a one-way pipe that never improves.
"""

from typing import Dict, List, Optional, Any, Set, Tuple
from datetime import datetime, timezone
from pydantic import BaseModel, Field
import numpy as np
import uuid
import logging

from adam.core.learning.universal_learning_interface import (
    LearningCapableComponent,
    LearningSignal,
    LearningSignalType,
    LearningContribution,
    LearningQualityMetrics,
)

logger = logging.getLogger(__name__)


# =============================================================================
# AUDIO PREDICTION MODELS
# =============================================================================

class AudioPrediction(BaseModel):
    """A prediction made based on audio features."""
    
    prediction_id: str = Field(default_factory=lambda: f"apred_{uuid.uuid4().hex[:12]}")
    
    # Audio source
    stream_id: str
    chunk_id: str
    user_id: str
    
    # What we measured
    arousal_detected: float = Field(ge=0.0, le=1.0)
    valence_detected: float = Field(ge=-1.0, le=1.0)
    personality_inferred: Dict[str, float] = Field(default_factory=dict)
    priming_effect: Optional[str] = None
    
    # What we predicted
    prediction_type: str  # e.g., "arousal_predicts_action"
    predicted_outcome: float
    confidence: float = Field(ge=0.0, le=1.0)
    
    # Context
    decision_id: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Resolution
    resolved: bool = False
    actual_outcome: Optional[float] = None
    prediction_error: Optional[float] = None


class AudioFeatureEffectiveness(BaseModel):
    """Effectiveness of an audio feature for prediction."""
    
    feature_name: str
    
    # Effectiveness metrics
    predictions_made: int = 0
    correct_predictions: int = 0
    accuracy: float = Field(default=0.5, ge=0.0, le=1.0)
    
    # Effect size
    effect_size: float = 0.0
    
    # Context-specific effectiveness
    context_effectiveness: Dict[str, float] = Field(default_factory=dict)
    # e.g., {"podcast": 0.7, "music": 0.5, "news": 0.8}
    
    # Trend
    recent_accuracy: float = 0.5
    accuracy_trend: str = "stable"


# =============================================================================
# AUDIO LEARNING BRIDGE
# =============================================================================

class AudioLearningBridge(LearningCapableComponent):
    """
    Integrates Audio Processing (#07) with ADAM's learning ecosystem.
    
    Key responsibilities:
    1. Track audio feature → outcome correlations
    2. Validate arousal/valence predictions against conversions
    3. Learn personality inference accuracy
    4. Update priming effect models
    5. Feed validated signals to Nonconscious Analytics
    """
    
    def __init__(
        self,
        neo4j_driver,
        redis_client,
        event_bus
    ):
        self.neo4j = neo4j_driver
        self.redis = redis_client
        self.event_bus = event_bus
        
        # Feature effectiveness tracking
        self.feature_effectiveness: Dict[str, AudioFeatureEffectiveness] = {}
        
        # Pending predictions
        self.pending_predictions: Dict[str, List[AudioPrediction]] = {}
        
        # Quality tracking
        self._outcomes_processed: int = 0
        self._predictions_validated: int = 0
        self._accuracy_history: List[Tuple[datetime, float]] = []
    
    @property
    def component_name(self) -> str:
        return "audio_processing"
    
    @property
    def component_version(self) -> str:
        return "2.1"  # Updated with learning
    
    # =========================================================================
    # PREDICTION REGISTRATION
    # =========================================================================
    
    async def register_audio_contribution(
        self,
        decision_id: str,
        user_id: str,
        audio_analysis: Dict[str, Any]
    ) -> None:
        """
        Register audio analysis that contributed to a decision.
        """
        
        predictions = []
        
        # Create prediction for arousal-based outcome
        if "arousal" in audio_analysis:
            arousal = audio_analysis["arousal"]
            prediction = AudioPrediction(
                stream_id=audio_analysis.get("stream_id", "unknown"),
                chunk_id=audio_analysis.get("chunk_id", "unknown"),
                user_id=user_id,
                arousal_detected=arousal,
                prediction_type="arousal_predicts_action",
                predicted_outcome=self._arousal_to_prediction(arousal),
                confidence=audio_analysis.get("arousal_confidence", 0.6),
                decision_id=decision_id,
            )
            predictions.append(prediction)
        
        # Create prediction for valence-based outcome
        if "valence" in audio_analysis:
            valence = audio_analysis["valence"]
            prediction = AudioPrediction(
                stream_id=audio_analysis.get("stream_id", "unknown"),
                chunk_id=audio_analysis.get("chunk_id", "unknown"),
                user_id=user_id,
                valence_detected=valence,
                prediction_type="valence_predicts_sentiment",
                predicted_outcome=self._valence_to_prediction(valence),
                confidence=audio_analysis.get("valence_confidence", 0.5),
                decision_id=decision_id,
            )
            predictions.append(prediction)
        
        # Create prediction for priming effect
        if "priming_effect" in audio_analysis:
            prediction = AudioPrediction(
                stream_id=audio_analysis.get("stream_id", "unknown"),
                chunk_id=audio_analysis.get("chunk_id", "unknown"),
                user_id=user_id,
                priming_effect=audio_analysis["priming_effect"],
                prediction_type=f"priming_{audio_analysis['priming_effect']}_effective",
                predicted_outcome=audio_analysis.get("priming_strength", 0.6),
                confidence=audio_analysis.get("priming_confidence", 0.5),
                decision_id=decision_id,
            )
            predictions.append(prediction)
        
        self.pending_predictions[decision_id] = predictions
        
        # Store for persistence
        await self.redis.setex(
            f"adam:audio:predictions:{decision_id}",
            86400,
            [p.json() for p in predictions]
        )
    
    def _arousal_to_prediction(self, arousal: float) -> float:
        """Convert arousal level to outcome prediction."""
        
        # Higher arousal generally predicts action
        # But too high can indicate stress/rejection
        if arousal > 0.85:
            return 0.6  # High arousal may overwhelm
        elif arousal > 0.6:
            return 0.75  # Optimal arousal for action
        elif arousal > 0.4:
            return 0.5  # Moderate arousal
        else:
            return 0.35  # Low arousal may indicate disengagement
    
    def _valence_to_prediction(self, valence: float) -> float:
        """Convert valence to outcome prediction."""
        
        # Positive valence generally predicts positive response
        return (valence + 1) / 2  # Map [-1, 1] to [0, 1]
    
    # =========================================================================
    # LEARNING FROM OUTCOMES
    # =========================================================================
    
    async def on_outcome_received(
        self,
        decision_id: str,
        outcome_type: str,
        outcome_value: float,
        context: Dict[str, Any]
    ) -> List[LearningSignal]:
        """
        Learn from an outcome by validating audio predictions.
        """
        
        learning_signals = []
        
        # Get pending predictions
        predictions = self.pending_predictions.pop(decision_id, [])
        
        if not predictions:
            cached = await self.redis.get(f"adam:audio:predictions:{decision_id}")
            if cached:
                predictions = [AudioPrediction.parse_raw(p) for p in cached]
        
        if not predictions:
            return []
        
        self._outcomes_processed += 1
        
        # Validate each prediction
        validated_results = []
        for prediction in predictions:
            prediction.resolved = True
            prediction.actual_outcome = outcome_value
            prediction.prediction_error = abs(prediction.predicted_outcome - outcome_value)
            
            was_correct = prediction.prediction_error < 0.3
            
            # Update feature effectiveness
            await self._update_feature_effectiveness(
                feature_name=prediction.prediction_type,
                was_correct=was_correct,
                context=context.get("content_type", "unknown")
            )
            
            validated_results.append({
                "prediction_type": prediction.prediction_type,
                "was_correct": was_correct,
                "error": prediction.prediction_error,
            })
            
            self._predictions_validated += 1
        
        # Track accuracy
        accuracy = np.mean([1.0 if r["was_correct"] else 0.0 for r in validated_results])
        self._accuracy_history.append((datetime.now(timezone.utc), accuracy))
        
        # 1. Emit audio feature validation signal
        learning_signals.append(LearningSignal(
            signal_type=LearningSignalType.AUDIO_FEATURE_VALIDATED,
            source_component=self.component_name,
            decision_id=decision_id,
            payload={
                "features_validated": len(predictions),
                "validation_results": validated_results,
                "mean_accuracy": accuracy,
            },
            confidence=0.8,
            target_components=["nonconscious_analytics", "gradient_bridge", "multimodal_fusion"]
        ))
        
        # 2. Emit signal to update Nonconscious Analytics source
        # This is critical - audio features ARE nonconscious signals
        arousal_predictions = [p for p in predictions if "arousal" in p.prediction_type]
        if arousal_predictions:
            arousal_accuracy = np.mean([
                1.0 - p.prediction_error for p in arousal_predictions
            ])
            learning_signals.append(LearningSignal(
                signal_type=LearningSignalType.BEHAVIORAL_PATTERN_VALIDATED,
                source_component=self.component_name,
                decision_id=decision_id,
                payload={
                    "pattern_type": "audio_arousal",
                    "accuracy": arousal_accuracy,
                    "sample_size": len(arousal_predictions),
                    "should_update_nonconscious": True,
                },
                confidence=0.75,
                target_components=["nonconscious_analytics", "graph_reasoning"]
            ))
        
        # 3. Emit priming effect validation
        priming_predictions = [p for p in predictions if "priming" in p.prediction_type]
        if priming_predictions:
            for pred in priming_predictions:
                learning_signals.append(LearningSignal(
                    signal_type=LearningSignalType.BEHAVIORAL_PATTERN_VALIDATED,
                    source_component=self.component_name,
                    decision_id=decision_id,
                    payload={
                        "pattern_type": "audio_priming",
                        "priming_effect": pred.priming_effect,
                        "was_effective": pred.prediction_error < 0.3,
                        "effect_size": 1.0 - pred.prediction_error,
                    },
                    confidence=0.7,
                    target_components=["priming_model", "creative_matching"]
                ))
        
        # Store validated predictions in Neo4j
        await self._store_validated_predictions(predictions)
        
        return learning_signals
    
    async def _update_feature_effectiveness(
        self,
        feature_name: str,
        was_correct: bool,
        context: str
    ) -> None:
        """Update effectiveness tracking for a feature."""
        
        if feature_name not in self.feature_effectiveness:
            self.feature_effectiveness[feature_name] = AudioFeatureEffectiveness(
                feature_name=feature_name
            )
        
        eff = self.feature_effectiveness[feature_name]
        
        # Update counts
        eff.predictions_made += 1
        if was_correct:
            eff.correct_predictions += 1
        
        # Update accuracy (EMA)
        alpha = 0.1
        eff.accuracy = (1 - alpha) * eff.accuracy + alpha * (1.0 if was_correct else 0.0)
        
        # Update context-specific effectiveness
        if context not in eff.context_effectiveness:
            eff.context_effectiveness[context] = 0.5
        eff.context_effectiveness[context] = (
            (1 - alpha) * eff.context_effectiveness[context] +
            alpha * (1.0 if was_correct else 0.0)
        )
        
        # Update trend
        old_accuracy = eff.accuracy
        eff.recent_accuracy = eff.correct_predictions / eff.predictions_made
        if eff.recent_accuracy > old_accuracy + 0.05:
            eff.accuracy_trend = "improving"
        elif eff.recent_accuracy < old_accuracy - 0.05:
            eff.accuracy_trend = "declining"
        else:
            eff.accuracy_trend = "stable"
    
    async def _store_validated_predictions(
        self,
        predictions: List[AudioPrediction]
    ) -> None:
        """Store validated predictions in Neo4j."""
        
        query = """
        UNWIND $predictions as pred
        CREATE (p:AudioPrediction {
            prediction_id: pred.prediction_id,
            prediction_type: pred.prediction_type,
            stream_id: pred.stream_id,
            arousal_detected: pred.arousal_detected,
            predicted_outcome: pred.predicted_outcome,
            actual_outcome: pred.actual_outcome,
            prediction_error: pred.prediction_error,
            validated_at: datetime()
        })
        """
        
        async with self.neo4j.session() as session:
            await session.run(
                query,
                predictions=[{
                    "prediction_id": p.prediction_id,
                    "prediction_type": p.prediction_type,
                    "stream_id": p.stream_id,
                    "arousal_detected": p.arousal_detected,
                    "predicted_outcome": p.predicted_outcome,
                    "actual_outcome": p.actual_outcome,
                    "prediction_error": p.prediction_error,
                } for p in predictions]
            )
    
    # =========================================================================
    # CONSUMING LEARNING SIGNALS
    # =========================================================================
    
    async def on_learning_signal_received(
        self,
        signal: LearningSignal
    ) -> Optional[List[LearningSignal]]:
        """Process learning signals from other components."""
        
        if signal.signal_type == LearningSignalType.MECHANISM_EFFECTIVENESS_UPDATED:
            # If mechanism effectiveness changed, may affect which audio features matter
            # e.g., if Identity Construction became more effective, personality inference matters more
            mechanism = signal.payload.get("mechanism")
            if mechanism == "identity_construction":
                # Boost importance of personality inference features
                if "personality_inference" in self.feature_effectiveness:
                    self.feature_effectiveness["personality_inference"].effect_size *= 1.1
        
        elif signal.signal_type == LearningSignalType.DRIFT_DETECTED:
            # If drift detected in audio features, reset tracking
            drift_source = signal.payload.get("source")
            if drift_source == "audio":
                for eff in self.feature_effectiveness.values():
                    eff.accuracy_trend = "recalibrating"
        
        return None
    
    def get_consumed_signal_types(self) -> Set[LearningSignalType]:
        return {
            LearningSignalType.MECHANISM_EFFECTIVENESS_UPDATED,
            LearningSignalType.DRIFT_DETECTED,
            LearningSignalType.CALIBRATION_UPDATED,
        }
    
    # =========================================================================
    # ATTRIBUTION
    # =========================================================================
    
    async def get_learning_contribution(
        self,
        decision_id: str
    ) -> Optional[LearningContribution]:
        """Get this component's contribution to a decision."""
        
        predictions_data = await self.redis.get(f"adam:audio:predictions:{decision_id}")
        
        if not predictions_data:
            return None
        
        predictions = [AudioPrediction.parse_raw(p) for p in predictions_data]
        
        # Compute contribution weight based on feature effectiveness
        weights = []
        for pred in predictions:
            eff = self.feature_effectiveness.get(pred.prediction_type)
            if eff:
                weights.append(eff.accuracy)
            else:
                weights.append(0.5)
        
        mean_weight = np.mean(weights) if weights else 0.5
        
        return LearningContribution(
            component_name=self.component_name,
            decision_id=decision_id,
            contribution_type="audio_analysis",
            contribution_value={
                "features_provided": len(predictions),
                "feature_types": list(set(p.prediction_type for p in predictions)),
                "arousal_detected": predictions[0].arousal_detected if predictions else None,
            },
            confidence=np.mean([p.confidence for p in predictions]) if predictions else 0.5,
            reasoning_summary=f"Provided {len(predictions)} audio features with {mean_weight:.2f} effectiveness",
            evidence_sources=[p.stream_id for p in predictions],
            weight=mean_weight
        )
    
    # =========================================================================
    # QUALITY METRICS
    # =========================================================================
    
    async def get_learning_quality_metrics(self) -> LearningQualityMetrics:
        """Get quality metrics for this component."""
        
        # Calculate overall accuracy
        if self.feature_effectiveness:
            mean_accuracy = np.mean([
                f.accuracy for f in self.feature_effectiveness.values()
            ])
        else:
            mean_accuracy = 0.5
        
        return LearningQualityMetrics(
            component_name=self.component_name,
            signals_emitted=self._predictions_validated,
            outcomes_processed=self._outcomes_processed,
            prediction_accuracy=mean_accuracy,
            prediction_accuracy_trend=self._compute_accuracy_trend(),
            attribution_coverage=min(len(self.feature_effectiveness) / 5, 1.0),
            last_learning_update=datetime.now(timezone.utc),
            upstream_dependencies=["audio_pipeline"],
            downstream_consumers=[
                "nonconscious_analytics", "gradient_bridge",
                "multimodal_fusion", "priming_model"
            ],
            integration_health=0.9 if self._outcomes_processed > 0 else 0.5
        )
    
    def _compute_accuracy_trend(self) -> str:
        if len(self._accuracy_history) < 10:
            return "stable"
        
        recent = [a for _, a in self._accuracy_history[-5:]]
        older = [a for _, a in self._accuracy_history[-10:-5]]
        
        if np.mean(recent) > np.mean(older) + 0.05:
            return "improving"
        elif np.mean(recent) < np.mean(older) - 0.05:
            return "declining"
        return "stable"
    
    async def inject_priors(self, user_id: str, priors: Dict[str, Any]) -> None:
        """Inject priors for audio processing."""
        
        # User-specific feature weights
        feature_weights = priors.get("audio_feature_weights", {})
        await self.redis.setex(
            f"adam:audio:weights:{user_id}",
            3600,
            feature_weights
        )
    
    async def validate_learning_health(self) -> Tuple[bool, List[str]]:
        """Validate learning health."""
        
        issues = []
        
        if self._outcomes_processed == 0:
            issues.append("No outcomes processed yet")
        
        if len(self.feature_effectiveness) < 3:
            issues.append(f"Only {len(self.feature_effectiveness)} features tracked (target: 5+)")
        
        declining = [
            f.feature_name for f in self.feature_effectiveness.values()
            if f.accuracy_trend == "declining"
        ]
        if declining:
            issues.append(f"Declining features: {declining}")
        
        return len(issues) == 0, issues
