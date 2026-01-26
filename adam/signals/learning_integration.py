# =============================================================================
# ADAM Enhancement #08: Signal Aggregation Learning Integration
# Location: adam/signals/learning_integration.py
# =============================================================================

"""
SIGNAL AGGREGATION LEARNING INTEGRATION

This module makes the Signal Aggregation Pipeline (#08) a full participant
in ADAM's learning ecosystem.

CRITICAL INSIGHT: Signals are the raw sensory input to ADAM. If we don't
learn which signals are accurate and which are noise, we're feeding garbage
into every downstream decision.

This module provides:
1. Signal accuracy tracking - Did this signal predict the outcome correctly?
2. Signal source quality - Which sources are reliable?
3. Supraliminal signal validation - Are hesitation patterns actually predictive?
4. Feature importance learning - Which derived features matter?
5. Cross-signal correlation discovery - Which signal combinations are synergistic?
"""

from typing import Dict, List, Optional, Any, Set, Tuple
from datetime import datetime, timezone, timedelta
from enum import Enum
from pydantic import BaseModel, Field
from collections import defaultdict
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
# SIGNAL ACCURACY TRACKING
# =============================================================================

class SignalPrediction(BaseModel):
    """A prediction made based on a signal."""
    
    prediction_id: str = Field(default_factory=lambda: f"pred_{uuid.uuid4().hex[:12]}")
    signal_id: str
    signal_type: str
    signal_source: str
    signal_value: Any
    
    # What we predicted
    predicted_outcome: str  # e.g., "high_arousal_increases_conversion"
    predicted_value: float
    confidence: float = Field(ge=0.0, le=1.0)
    
    # Context
    user_id: str
    decision_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Resolution (filled when outcome observed)
    resolved: bool = False
    actual_outcome: Optional[float] = None
    prediction_error: Optional[float] = None
    resolved_at: Optional[datetime] = None


class SignalSourceQuality(BaseModel):
    """Quality metrics for a signal source."""
    
    source_id: str
    source_type: str
    
    # Accuracy metrics
    predictions_made: int = 0
    correct_predictions: int = 0
    accuracy: float = Field(default=0.5, ge=0.0, le=1.0)
    
    # Calibration (does confidence match accuracy?)
    mean_confidence: float = 0.5
    calibration_error: float = 0.0  # Lower is better
    
    # Reliability
    availability: float = 1.0  # How often is this source available
    latency_p50_ms: float = 0.0
    latency_p99_ms: float = 0.0
    
    # Trend
    recent_accuracy: float = 0.5  # Last 100 predictions
    accuracy_trend: str = "stable"  # improving, stable, declining
    
    # Last update
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    @property
    def trust_score(self) -> float:
        """Overall trust score for this source."""
        return (
            self.accuracy * 0.4 +
            (1 - self.calibration_error) * 0.2 +
            self.availability * 0.2 +
            self.recent_accuracy * 0.2
        )


class SupraliminalSignalValidation(BaseModel):
    """Validation of supraliminal (nonconscious) signals."""
    
    signal_category: str  # e.g., "hesitation_pattern", "scroll_velocity"
    
    # Validation stats
    validations: int = 0
    confirmed_predictions: int = 0
    
    # Psychological validity
    theoretical_grounding: str = ""  # e.g., "Yerkes-Dodson arousal theory"
    empirical_validity: float = Field(default=0.5, ge=0.0, le=1.0)
    
    # Effect sizes
    effect_size_mean: float = 0.0
    effect_size_std: float = 0.0
    
    # Boundary conditions (where does this signal NOT work?)
    boundary_conditions: List[str] = Field(default_factory=list)


class FeatureImportance(BaseModel):
    """Importance of a derived feature."""
    
    feature_name: str
    feature_category: str
    
    # Importance metrics
    importance_score: float = Field(default=0.0, ge=0.0, le=1.0)
    shap_value_mean: float = 0.0
    
    # Predictive power
    univariate_auc: float = 0.5
    marginal_lift: float = 0.0
    
    # Stability
    importance_stability: float = 1.0  # Does importance change over time?
    
    # Interactions
    synergistic_features: Dict[str, float] = Field(default_factory=dict)
    antagonistic_features: Dict[str, float] = Field(default_factory=dict)


# =============================================================================
# SIGNAL LEARNING BRIDGE
# =============================================================================

class SignalLearningBridge(LearningCapableComponent):
    """
    Makes Signal Aggregation (#08) a full learning participant.
    
    This is the missing piece that transforms #08 from a
    passive pipeline into an active learning system.
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
        
        # In-memory caches
        self.source_quality: Dict[str, SignalSourceQuality] = {}
        self.feature_importance: Dict[str, FeatureImportance] = {}
        self.supraliminal_validation: Dict[str, SupraliminalSignalValidation] = {}
        
        # Pending predictions awaiting outcome
        self.pending_predictions: Dict[str, List[SignalPrediction]] = {}
        
        # Quality tracking
        self._outcomes_processed: int = 0
        self._signals_validated: int = 0
        self._accuracy_history: List[Tuple[datetime, float]] = []
    
    @property
    def component_name(self) -> str:
        return "signal_aggregation"
    
    @property
    def component_version(self) -> str:
        return "2.1"  # Updated with learning
    
    # =========================================================================
    # SIGNAL REGISTRATION
    # =========================================================================
    
    async def register_signal_contribution(
        self,
        decision_id: str,
        signals: List[Dict[str, Any]],
        derived_features: Dict[str, float]
    ) -> None:
        """
        Register signals and derived features that contributed to a decision.
        
        This creates the prediction records that will be validated
        when the outcome is observed.
        """
        
        predictions = []
        
        for signal in signals:
            # Create prediction for each signal
            prediction = SignalPrediction(
                signal_id=signal.get("signal_id", str(uuid.uuid4())),
                signal_type=signal.get("signal_type", "unknown"),
                signal_source=signal.get("source", "unknown"),
                signal_value=signal.get("value"),
                predicted_outcome=self._derive_prediction(signal),
                predicted_value=signal.get("psychological_weight", 0.5),
                confidence=signal.get("confidence", 0.5),
                user_id=signal.get("user_id", ""),
                decision_id=decision_id,
            )
            predictions.append(prediction)
        
        self.pending_predictions[decision_id] = predictions
        
        # Store in Redis for persistence
        await self.redis.setex(
            f"adam:signal:predictions:{decision_id}",
            86400,  # 24 hour TTL
            [p.json() for p in predictions]
        )
    
    def _derive_prediction(self, signal: Dict[str, Any]) -> str:
        """Derive what outcome this signal predicts."""
        
        signal_type = signal.get("signal_type", "")
        
        # Supraliminal signals
        if "hesitation" in signal_type.lower():
            return "hesitation_predicts_low_confidence_decision"
        elif "scroll_velocity" in signal_type.lower():
            value = signal.get("value", 0)
            if value > 0.7:
                return "high_scroll_velocity_predicts_low_engagement"
            else:
                return "low_scroll_velocity_predicts_high_engagement"
        elif "arousal" in signal_type.lower():
            value = signal.get("value", 0.5)
            if value > 0.7:
                return "high_arousal_predicts_action"
            else:
                return "low_arousal_predicts_consideration"
        
        # Default
        return f"signal_{signal_type}_contributes_to_outcome"
    
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
        Learn from an outcome by validating signal predictions.
        """
        
        learning_signals = []
        
        # Get pending predictions for this decision
        predictions = self.pending_predictions.pop(decision_id, [])
        
        if not predictions:
            # Try to load from Redis
            cached = await self.redis.get(f"adam:signal:predictions:{decision_id}")
            if cached:
                predictions = [SignalPrediction.parse_raw(p) for p in cached]
        
        if not predictions:
            return []  # No signals to validate
        
        self._outcomes_processed += 1
        
        # Validate each prediction
        for prediction in predictions:
            # Calculate prediction error
            prediction.resolved = True
            prediction.actual_outcome = outcome_value
            prediction.prediction_error = abs(prediction.predicted_value - outcome_value)
            prediction.resolved_at = datetime.now(timezone.utc)
            
            # Update source quality
            await self._update_source_quality(
                source_id=prediction.signal_source,
                source_type=prediction.signal_type,
                was_correct=(prediction.prediction_error < 0.3),
                confidence=prediction.confidence
            )
            
            # Update supraliminal validation if applicable
            if self._is_supraliminal(prediction.signal_type):
                await self._update_supraliminal_validation(
                    signal_category=prediction.signal_type,
                    was_correct=(prediction.prediction_error < 0.3),
                    effect_size=1.0 - prediction.prediction_error
                )
            
            self._signals_validated += 1
        
        # Generate learning signals
        
        # 1. Signal accuracy update
        accuracy_signal = LearningSignal(
            signal_type=LearningSignalType.SIGNAL_ACCURACY_VALIDATED,
            source_component=self.component_name,
            decision_id=decision_id,
            payload={
                "signals_validated": len(predictions),
                "mean_error": np.mean([p.prediction_error for p in predictions]),
                "source_updates": {
                    p.signal_source: (p.prediction_error < 0.3)
                    for p in predictions
                }
            },
            confidence=0.8,
            target_components=["atom_of_thought", "multimodal_fusion"]
        )
        learning_signals.append(accuracy_signal)
        
        # 2. Supraliminal validation signal
        supraliminal_preds = [p for p in predictions if self._is_supraliminal(p.signal_type)]
        if supraliminal_preds:
            supraliminal_signal = LearningSignal(
                signal_type=LearningSignalType.BEHAVIORAL_PATTERN_VALIDATED,
                source_component=self.component_name,
                decision_id=decision_id,
                payload={
                    "patterns_validated": len(supraliminal_preds),
                    "mean_accuracy": np.mean([
                        1.0 - p.prediction_error 
                        for p in supraliminal_preds
                    ]),
                    "pattern_updates": {
                        p.signal_type: (p.prediction_error < 0.3)
                        for p in supraliminal_preds
                    }
                },
                confidence=0.75,
                target_components=["nonconscious_analytics", "gradient_bridge"]
            )
            learning_signals.append(supraliminal_signal)
        
        # 3. Feature importance signal (if we have enough data)
        if self._outcomes_processed % 100 == 0:
            importance_signal = await self._compute_feature_importance_signal()
            if importance_signal:
                learning_signals.append(importance_signal)
        
        # Store validated predictions in Neo4j for analysis
        await self._store_validated_predictions(predictions)
        
        return learning_signals
    
    def _is_supraliminal(self, signal_type: str) -> bool:
        """Check if signal is supraliminal (nonconscious)."""
        supraliminal_types = [
            "hesitation", "scroll_velocity", "mouse_trajectory",
            "keystroke_timing", "micro_pause", "hover_duration",
            "return_visit_timing", "dwell_pattern"
        ]
        return any(s in signal_type.lower() for s in supraliminal_types)
    
    async def _update_source_quality(
        self,
        source_id: str,
        source_type: str,
        was_correct: bool,
        confidence: float
    ) -> None:
        """Update quality metrics for a signal source."""
        
        if source_id not in self.source_quality:
            self.source_quality[source_id] = SignalSourceQuality(
                source_id=source_id,
                source_type=source_type
            )
        
        quality = self.source_quality[source_id]
        
        # Update counts
        quality.predictions_made += 1
        if was_correct:
            quality.correct_predictions += 1
        
        # Update accuracy (exponential moving average)
        alpha = 0.1
        quality.accuracy = (1 - alpha) * quality.accuracy + alpha * (1.0 if was_correct else 0.0)
        
        # Update calibration error
        quality.mean_confidence = (1 - alpha) * quality.mean_confidence + alpha * confidence
        quality.calibration_error = abs(quality.accuracy - quality.mean_confidence)
        
        # Update recent accuracy (last 100)
        if quality.predictions_made > 100:
            quality.recent_accuracy = quality.correct_predictions / quality.predictions_made
        
        # Determine trend
        old_accuracy = quality.accuracy
        if quality.recent_accuracy > old_accuracy + 0.05:
            quality.accuracy_trend = "improving"
        elif quality.recent_accuracy < old_accuracy - 0.05:
            quality.accuracy_trend = "declining"
        else:
            quality.accuracy_trend = "stable"
        
        quality.last_updated = datetime.now(timezone.utc)
        
        # Update in Neo4j periodically
        if quality.predictions_made % 50 == 0:
            await self._persist_source_quality(quality)
    
    async def _update_supraliminal_validation(
        self,
        signal_category: str,
        was_correct: bool,
        effect_size: float
    ) -> None:
        """Update validation for supraliminal signals."""
        
        if signal_category not in self.supraliminal_validation:
            self.supraliminal_validation[signal_category] = SupraliminalSignalValidation(
                signal_category=signal_category
            )
        
        validation = self.supraliminal_validation[signal_category]
        validation.validations += 1
        if was_correct:
            validation.confirmed_predictions += 1
        
        # Update empirical validity
        alpha = 0.1
        validation.empirical_validity = (
            (1 - alpha) * validation.empirical_validity + 
            alpha * (1.0 if was_correct else 0.0)
        )
        
        # Update effect size estimates
        old_mean = validation.effect_size_mean
        validation.effect_size_mean = (
            (1 - alpha) * validation.effect_size_mean + 
            alpha * effect_size
        )
        validation.effect_size_std = (
            (1 - alpha) * validation.effect_size_std + 
            alpha * abs(effect_size - old_mean)
        )
    
    async def _persist_source_quality(self, quality: SignalSourceQuality) -> None:
        """Persist source quality to Neo4j."""
        
        query = """
        MERGE (s:SignalSource {source_id: $source_id})
        SET s.source_type = $source_type,
            s.predictions_made = $predictions_made,
            s.accuracy = $accuracy,
            s.calibration_error = $calibration_error,
            s.trust_score = $trust_score,
            s.last_updated = datetime()
        """
        
        async with self.neo4j.session() as session:
            await session.run(
                query,
                source_id=quality.source_id,
                source_type=quality.source_type,
                predictions_made=quality.predictions_made,
                accuracy=quality.accuracy,
                calibration_error=quality.calibration_error,
                trust_score=quality.trust_score
            )
    
    async def _store_validated_predictions(
        self,
        predictions: List[SignalPrediction]
    ) -> None:
        """Store validated predictions in Neo4j for analysis."""
        
        query = """
        UNWIND $predictions as pred
        CREATE (p:SignalPrediction {
            prediction_id: pred.prediction_id,
            signal_type: pred.signal_type,
            signal_source: pred.signal_source,
            decision_id: pred.decision_id,
            predicted_value: pred.predicted_value,
            actual_outcome: pred.actual_outcome,
            prediction_error: pred.prediction_error,
            resolved_at: datetime()
        })
        """
        
        async with self.neo4j.session() as session:
            await session.run(
                query,
                predictions=[p.dict() for p in predictions]
            )
    
    async def _compute_feature_importance_signal(self) -> Optional[LearningSignal]:
        """Compute feature importance from accumulated predictions."""
        
        # Query Neo4j for recent predictions
        query = """
        MATCH (p:SignalPrediction)
        WHERE p.resolved_at > datetime() - duration('P7D')
        RETURN p.signal_type as feature,
               avg(1.0 - p.prediction_error) as mean_accuracy,
               count(*) as sample_size
        ORDER BY mean_accuracy DESC
        """
        
        async with self.neo4j.session() as session:
            result = await session.run(query)
            records = await result.data()
        
        if not records:
            return None
        
        importance_updates = {}
        for record in records:
            if record["sample_size"] >= 10:  # Minimum sample
                importance_updates[record["feature"]] = record["mean_accuracy"]
        
        return LearningSignal(
            signal_type=LearningSignalType.SIGNAL_QUALITY_UPDATED,
            source_component=self.component_name,
            payload={
                "feature_importance": importance_updates,
                "sample_period_days": 7,
                "total_samples": sum(r["sample_size"] for r in records)
            },
            confidence=0.85,
            target_components=["meta_learner", "feature_store"]
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
            # If a mechanism's effectiveness changed, may affect which signals matter
            await self._update_signal_weights_for_mechanism(signal.payload)
        
        elif signal.signal_type == LearningSignalType.DRIFT_DETECTED:
            # If drift detected, may need to recalibrate signal sources
            await self._handle_drift_signal(signal.payload)
        
        return None  # No derivative signals
    
    def get_consumed_signal_types(self) -> Set[LearningSignalType]:
        """Signal types this component consumes."""
        return {
            LearningSignalType.MECHANISM_EFFECTIVENESS_UPDATED,
            LearningSignalType.DRIFT_DETECTED,
            LearningSignalType.CALIBRATION_UPDATED,
        }
    
    async def _update_signal_weights_for_mechanism(
        self,
        payload: Dict[str, Any]
    ) -> None:
        """Update signal weights based on mechanism effectiveness changes."""
        # When a mechanism becomes more/less effective, the signals
        # that predict its activation become more/less important
        pass  # Implementation based on specific mechanism
    
    async def _handle_drift_signal(self, payload: Dict[str, Any]) -> None:
        """Handle drift detection by recalibrating sources."""
        drift_source = payload.get("source")
        if drift_source in self.source_quality:
            # Reset accuracy tracking for drifted source
            self.source_quality[drift_source].accuracy_trend = "recalibrating"
            self.source_quality[drift_source].recent_accuracy = 0.5
    
    # =========================================================================
    # ATTRIBUTION
    # =========================================================================
    
    async def get_learning_contribution(
        self,
        decision_id: str
    ) -> Optional[LearningContribution]:
        """Get this component's contribution to a decision."""
        
        # Get registered signals for this decision
        predictions = await self.redis.get(f"adam:signal:predictions:{decision_id}")
        
        if not predictions:
            return None
        
        predictions = [SignalPrediction.parse_raw(p) for p in predictions]
        
        # Calculate aggregate contribution
        total_weight = sum(
            self.source_quality.get(p.signal_source, SignalSourceQuality(
                source_id=p.signal_source,
                source_type=p.signal_type
            )).trust_score
            for p in predictions
        )
        
        return LearningContribution(
            component_name=self.component_name,
            decision_id=decision_id,
            contribution_type="signal_aggregation",
            contribution_value={
                "signals_provided": len(predictions),
                "signal_types": list(set(p.signal_type for p in predictions)),
                "mean_confidence": np.mean([p.confidence for p in predictions]),
            },
            confidence=np.mean([p.confidence for p in predictions]),
            reasoning_summary=f"Provided {len(predictions)} signals with mean confidence {np.mean([p.confidence for p in predictions]):.2f}",
            evidence_sources=[p.signal_source for p in predictions],
            weight=min(total_weight / len(predictions), 1.0) if predictions else 0.0
        )
    
    # =========================================================================
    # QUALITY METRICS
    # =========================================================================
    
    async def get_learning_quality_metrics(self) -> LearningQualityMetrics:
        """Get quality metrics for this component's learning."""
        
        # Calculate overall accuracy
        if self.source_quality:
            mean_accuracy = np.mean([
                q.accuracy for q in self.source_quality.values()
            ])
            mean_calibration = np.mean([
                1 - q.calibration_error for q in self.source_quality.values()
            ])
        else:
            mean_accuracy = 0.5
            mean_calibration = 0.5
        
        return LearningQualityMetrics(
            component_name=self.component_name,
            signals_emitted=self._signals_validated,
            outcomes_processed=self._outcomes_processed,
            prediction_accuracy=mean_accuracy,
            prediction_accuracy_trend=self._compute_accuracy_trend(),
            attribution_coverage=min(
                len(self.source_quality) / 10,  # Target: 10 sources tracked
                1.0
            ),
            last_learning_update=datetime.now(timezone.utc),
            upstream_dependencies=[],
            downstream_consumers=[
                "atom_of_thought", "multimodal_fusion", 
                "nonconscious_analytics", "meta_learner"
            ],
            integration_health=mean_calibration
        )
    
    def _compute_accuracy_trend(self) -> str:
        """Compute overall accuracy trend."""
        
        if len(self._accuracy_history) < 2:
            return "stable"
        
        recent = [a for t, a in self._accuracy_history[-10:]]
        older = [a for t, a in self._accuracy_history[-20:-10]]
        
        if not older:
            return "stable"
        
        if np.mean(recent) > np.mean(older) + 0.05:
            return "improving"
        elif np.mean(recent) < np.mean(older) - 0.05:
            return "declining"
        return "stable"
    
    # =========================================================================
    # PRIOR INJECTION
    # =========================================================================
    
    async def inject_priors(
        self,
        user_id: str,
        priors: Dict[str, Any]
    ) -> None:
        """Inject priors for signal weighting."""
        
        # Store user-specific signal weights based on their history
        signal_weights = priors.get("signal_weights", {})
        await self.redis.setex(
            f"adam:signal:weights:{user_id}",
            3600,  # 1 hour TTL
            signal_weights
        )
    
    # =========================================================================
    # HEALTH CHECK
    # =========================================================================
    
    async def validate_learning_health(self) -> Tuple[bool, List[str]]:
        """Validate learning health."""
        
        issues = []
        
        # Check if we're processing outcomes
        if self._outcomes_processed == 0:
            issues.append("No outcomes processed yet")
        
        # Check source quality tracking
        if len(self.source_quality) < 3:
            issues.append(f"Only {len(self.source_quality)} sources tracked (target: 10+)")
        
        # Check for declining sources
        declining = [
            s.source_id for s in self.source_quality.values()
            if s.accuracy_trend == "declining"
        ]
        if declining:
            issues.append(f"Declining accuracy in sources: {declining}")
        
        # Check calibration
        poorly_calibrated = [
            s.source_id for s in self.source_quality.values()
            if s.calibration_error > 0.2
        ]
        if poorly_calibrated:
            issues.append(f"Poor calibration in sources: {poorly_calibrated}")
        
        return len(issues) == 0, issues
