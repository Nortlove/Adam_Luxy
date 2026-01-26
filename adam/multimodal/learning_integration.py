# =============================================================================
# ADAM Enhancement #16: Multimodal Fusion Learning Integration
# Location: adam/multimodal/learning_integration.py
# =============================================================================

"""
MULTIMODAL FUSION LEARNING INTEGRATION

CRITICAL GAP IDENTIFIED: #16 had ZERO learning mentions.

This module makes Multimodal Fusion a full learning participant by:
1. Tracking which modality combinations are most predictive
2. Learning optimal fusion weights from outcomes
3. Validating cross-modal correlations against conversions
4. Updating modality importance based on empirical evidence
5. Detecting modality-specific drift

Multimodal fusion combines:
- Voice/Audio signals (arousal, emotion, prosody)
- Text signals (sentiment, intent, personality cues)
- Behavioral signals (clicks, scrolls, hesitation)
- Psychological signals (from AoT atoms)

Without learning, we fuse these with static weights that never improve.
"""

from typing import Dict, List, Optional, Any, Set, Tuple
from datetime import datetime, timezone
from enum import Enum
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
# MODALITY DEFINITIONS
# =============================================================================

class Modality(str, Enum):
    """The modalities that can be fused."""
    
    VOICE = "voice"              # Audio-derived signals
    TEXT = "text"                # Text-derived signals
    BEHAVIORAL = "behavioral"    # Click/scroll/timing signals
    PSYCHOLOGICAL = "psychological"  # AoT-derived signals
    VISUAL = "visual"            # Visual attention signals (future)
    CONTEXTUAL = "contextual"    # Time, location, device signals


class FusionMethod(str, Enum):
    """Methods for fusing modality signals."""
    
    WEIGHTED_AVERAGE = "weighted_average"
    ATTENTION_BASED = "attention_based"
    LEARNED_EMBEDDING = "learned_embedding"
    HIERARCHICAL = "hierarchical"
    LATE_FUSION = "late_fusion"
    EARLY_FUSION = "early_fusion"


# =============================================================================
# FUSION PREDICTION MODELS
# =============================================================================

class ModalityContribution(BaseModel):
    """A single modality's contribution to a fusion."""
    
    modality: Modality
    
    # What the modality provided
    signal_value: float
    confidence: float = Field(ge=0.0, le=1.0)
    
    # Weight used in fusion
    fusion_weight: float = Field(ge=0.0, le=1.0)
    
    # Prediction from this modality alone
    unimodal_prediction: float
    
    # Sources
    source_signals: List[str] = Field(default_factory=list)


class FusionPrediction(BaseModel):
    """A prediction made by the multimodal fusion system."""
    
    prediction_id: str = Field(default_factory=lambda: f"fuse_{uuid.uuid4().hex[:12]}")
    
    # Context
    user_id: str
    decision_id: str
    
    # Fusion configuration
    fusion_method: FusionMethod
    modalities_used: List[Modality]
    
    # Individual modality contributions
    modality_contributions: Dict[Modality, ModalityContribution] = Field(default_factory=dict)
    
    # Fused prediction
    fused_prediction: float
    fusion_confidence: float = Field(ge=0.0, le=1.0)
    
    # Diagnostics
    agreement_score: float = 0.0  # How much modalities agree
    dominant_modality: Optional[Modality] = None
    
    # Timing
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Resolution
    resolved: bool = False
    actual_outcome: Optional[float] = None
    prediction_error: Optional[float] = None


class ModalityEffectiveness(BaseModel):
    """Learned effectiveness of a modality."""
    
    modality: Modality
    
    # Accuracy metrics
    predictions_made: int = 0
    correct_predictions: int = 0
    unimodal_accuracy: float = Field(default=0.5, ge=0.0, le=1.0)
    
    # Contribution to fusion
    avg_fusion_weight: float = 0.2
    optimal_weight: float = 0.2  # Learned optimal weight
    
    # Context-specific effectiveness
    context_effectiveness: Dict[str, float] = Field(default_factory=dict)
    # e.g., {"high_arousal": 0.8, "cold_start": 0.3}
    
    # Correlation with other modalities
    synergies: Dict[str, float] = Field(default_factory=dict)
    antagonisms: Dict[str, float] = Field(default_factory=dict)
    
    # Trend
    recent_accuracy: float = 0.5
    accuracy_trend: str = "stable"


class FusionMethodEffectiveness(BaseModel):
    """Learned effectiveness of a fusion method."""
    
    method: FusionMethod
    
    # Performance
    predictions_made: int = 0
    mean_accuracy: float = 0.5
    
    # Context-specific performance
    best_contexts: List[str] = Field(default_factory=list)
    worst_contexts: List[str] = Field(default_factory=list)


# =============================================================================
# MULTIMODAL FUSION LEARNING BRIDGE
# =============================================================================

class MultimodalFusionLearningBridge(LearningCapableComponent):
    """
    Learning integration for Enhancement #16: Multimodal Fusion.
    
    This transforms Multimodal Fusion from a static combiner into
    a system that learns optimal fusion strategies from outcomes.
    """
    
    def __init__(
        self,
        fusion_engine,
        neo4j_driver,
        redis_client,
        event_bus
    ):
        self.fusion_engine = fusion_engine
        self.neo4j = neo4j_driver
        self.redis = redis_client
        self.event_bus = event_bus
        
        # Effectiveness tracking
        self.modality_effectiveness: Dict[Modality, ModalityEffectiveness] = {
            m: ModalityEffectiveness(modality=m) for m in Modality
        }
        self.method_effectiveness: Dict[FusionMethod, FusionMethodEffectiveness] = {
            m: FusionMethodEffectiveness(method=m) for m in FusionMethod
        }
        
        # Pending predictions
        self.pending_predictions: Dict[str, FusionPrediction] = {}
        
        # Quality tracking
        self._outcomes_processed: int = 0
        self._accuracy_history: List[Tuple[datetime, float]] = []
        
        # Learned fusion weights (updated from outcomes)
        self._learned_weights: Dict[Modality, float] = {
            Modality.VOICE: 0.2,
            Modality.TEXT: 0.25,
            Modality.BEHAVIORAL: 0.25,
            Modality.PSYCHOLOGICAL: 0.3,
            Modality.VISUAL: 0.0,
            Modality.CONTEXTUAL: 0.0,
        }
    
    @property
    def component_name(self) -> str:
        return "multimodal_fusion"
    
    @property
    def component_version(self) -> str:
        return "2.0"  # Now with learning
    
    # =========================================================================
    # FUSION REGISTRATION
    # =========================================================================
    
    async def register_fusion(
        self,
        decision_id: str,
        user_id: str,
        modality_signals: Dict[Modality, Dict[str, Any]],
        fusion_method: FusionMethod,
        fused_result: float,
        fusion_confidence: float
    ) -> FusionPrediction:
        """
        Register a fusion result for later learning.
        
        Called by the fusion engine after producing a fused signal.
        """
        
        # Build modality contributions
        contributions = {}
        for modality, signals in modality_signals.items():
            contributions[modality] = ModalityContribution(
                modality=modality,
                signal_value=signals.get("value", 0.5),
                confidence=signals.get("confidence", 0.5),
                fusion_weight=self._learned_weights.get(modality, 0.2),
                unimodal_prediction=signals.get("prediction", 0.5),
                source_signals=signals.get("sources", []),
            )
        
        # Compute agreement score
        unimodal_preds = [c.unimodal_prediction for c in contributions.values()]
        agreement = 1.0 - np.std(unimodal_preds) if unimodal_preds else 0.5
        
        # Find dominant modality
        if contributions:
            dominant = max(contributions.values(), key=lambda c: c.fusion_weight * c.confidence)
            dominant_modality = dominant.modality
        else:
            dominant_modality = None
        
        prediction = FusionPrediction(
            user_id=user_id,
            decision_id=decision_id,
            fusion_method=fusion_method,
            modalities_used=list(modality_signals.keys()),
            modality_contributions=contributions,
            fused_prediction=fused_result,
            fusion_confidence=fusion_confidence,
            agreement_score=agreement,
            dominant_modality=dominant_modality,
        )
        
        self.pending_predictions[decision_id] = prediction
        
        # Store in Redis
        await self.redis.setex(
            f"adam:fusion:prediction:{decision_id}",
            86400,
            prediction.json()
        )
        
        return prediction
    
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
        Learn from fusion outcome.
        
        This is where we discover:
        1. Which modalities were most predictive
        2. Which fusion method worked best
        3. How to update fusion weights
        """
        
        signals = []
        
        # Get pending prediction
        prediction = self.pending_predictions.pop(decision_id, None)
        if not prediction:
            cached = await self.redis.get(f"adam:fusion:prediction:{decision_id}")
            if cached:
                prediction = FusionPrediction.parse_raw(cached)
        
        if not prediction:
            return []
        
        self._outcomes_processed += 1
        
        # Resolve prediction
        prediction.resolved = True
        prediction.actual_outcome = outcome_value
        prediction.prediction_error = abs(prediction.fused_prediction - outcome_value)
        
        was_correct = prediction.prediction_error < 0.3
        self._accuracy_history.append((datetime.now(timezone.utc), 1.0 if was_correct else 0.0))
        
        # =====================================================================
        # LEARN MODALITY EFFECTIVENESS
        # =====================================================================
        
        modality_results = {}
        for modality, contribution in prediction.modality_contributions.items():
            unimodal_error = abs(contribution.unimodal_prediction - outcome_value)
            unimodal_correct = unimodal_error < 0.3
            
            # Update modality effectiveness
            eff = self.modality_effectiveness[modality]
            eff.predictions_made += 1
            if unimodal_correct:
                eff.correct_predictions += 1
            
            # EMA update
            alpha = 0.1
            eff.unimodal_accuracy = (1 - alpha) * eff.unimodal_accuracy + alpha * (1.0 if unimodal_correct else 0.0)
            
            modality_results[modality.value] = {
                "unimodal_correct": unimodal_correct,
                "unimodal_error": unimodal_error,
                "accuracy": eff.unimodal_accuracy,
            }
        
        # =====================================================================
        # UPDATE FUSION WEIGHTS
        # =====================================================================
        
        await self._update_fusion_weights(prediction, outcome_value)
        
        # =====================================================================
        # LEARN FUSION METHOD EFFECTIVENESS
        # =====================================================================
        
        method_eff = self.method_effectiveness[prediction.fusion_method]
        method_eff.predictions_made += 1
        method_eff.mean_accuracy = (
            (method_eff.mean_accuracy * (method_eff.predictions_made - 1) + 
             (1.0 if was_correct else 0.0)) / method_eff.predictions_made
        )
        
        # =====================================================================
        # EMIT LEARNING SIGNALS
        # =====================================================================
        
        # 1. Modality effectiveness signal
        signals.append(LearningSignal(
            signal_type=LearningSignalType.SIGNAL_QUALITY_UPDATED,
            source_component=self.component_name,
            decision_id=decision_id,
            payload={
                "modality_results": modality_results,
                "dominant_modality": prediction.dominant_modality.value if prediction.dominant_modality else None,
                "dominant_was_correct": modality_results.get(
                    prediction.dominant_modality.value if prediction.dominant_modality else "", {}
                ).get("unimodal_correct", False),
                "fusion_was_correct": was_correct,
                "agreement_score": prediction.agreement_score,
            },
            confidence=0.85,
            target_components=["gradient_bridge", "audio_processing", "signal_aggregation"]
        ))
        
        # 2. Fusion weight update signal
        signals.append(LearningSignal(
            signal_type=LearningSignalType.PRIOR_UPDATED,
            source_component=self.component_name,
            decision_id=decision_id,
            payload={
                "learned_weights": {m.value: w for m, w in self._learned_weights.items()},
                "outcome": outcome_value,
                "fusion_error": prediction.prediction_error,
            },
            confidence=0.8,
            target_components=["holistic_synthesizer", "meta_learner"]
        ))
        
        # 3. Cross-modal correlation signal (for emergence detection)
        if prediction.agreement_score < 0.5:  # Modalities disagreed
            signals.append(LearningSignal(
                signal_type=LearningSignalType.PATTERN_EMERGED,
                source_component=self.component_name,
                decision_id=decision_id,
                payload={
                    "pattern_type": "modality_disagreement",
                    "agreement_score": prediction.agreement_score,
                    "outcome": outcome_value,
                    "correct_modality": self._find_correct_modality(prediction, outcome_value),
                    "user_context": context.get("user_context", {}),
                },
                confidence=0.7,
                target_components=["atom_of_thought", "emergence_detector"]
            ))
        
        # Store validated prediction
        await self._store_validated_prediction(prediction)
        
        return signals
    
    async def _update_fusion_weights(
        self,
        prediction: FusionPrediction,
        outcome_value: float
    ) -> None:
        """Update fusion weights based on outcome."""
        
        # Credit assignment: modalities that predicted correctly get more weight
        learning_rate = 0.05
        
        for modality, contribution in prediction.modality_contributions.items():
            unimodal_error = abs(contribution.unimodal_prediction - outcome_value)
            
            # Performance relative to outcome
            # Lower error = higher credit
            credit = 1.0 - min(unimodal_error, 1.0)
            
            # Update weight
            current_weight = self._learned_weights.get(modality, 0.2)
            new_weight = current_weight + learning_rate * (credit - 0.5)
            
            # Bound weights
            new_weight = max(0.05, min(0.5, new_weight))
            
            self._learned_weights[modality] = new_weight
            self.modality_effectiveness[modality].optimal_weight = new_weight
        
        # Normalize weights to sum to 1
        total_weight = sum(self._learned_weights.values())
        if total_weight > 0:
            for modality in self._learned_weights:
                self._learned_weights[modality] /= total_weight
    
    def _find_correct_modality(
        self,
        prediction: FusionPrediction,
        outcome_value: float
    ) -> Optional[str]:
        """Find which modality was most correct."""
        
        best_modality = None
        best_error = 1.0
        
        for modality, contribution in prediction.modality_contributions.items():
            error = abs(contribution.unimodal_prediction - outcome_value)
            if error < best_error:
                best_error = error
                best_modality = modality.value
        
        return best_modality
    
    async def _store_validated_prediction(self, prediction: FusionPrediction) -> None:
        """Store validated prediction in Neo4j."""
        
        query = """
        CREATE (f:FusionPrediction {
            prediction_id: $prediction_id,
            decision_id: $decision_id,
            user_id: $user_id,
            fusion_method: $fusion_method,
            modalities_used: $modalities_used,
            fused_prediction: $fused_prediction,
            actual_outcome: $actual_outcome,
            prediction_error: $prediction_error,
            agreement_score: $agreement_score,
            validated_at: datetime()
        })
        """
        
        async with self.neo4j.session() as session:
            await session.run(
                query,
                prediction_id=prediction.prediction_id,
                decision_id=prediction.decision_id,
                user_id=prediction.user_id,
                fusion_method=prediction.fusion_method.value,
                modalities_used=[m.value for m in prediction.modalities_used],
                fused_prediction=prediction.fused_prediction,
                actual_outcome=prediction.actual_outcome,
                prediction_error=prediction.prediction_error,
                agreement_score=prediction.agreement_score,
            )
    
    # =========================================================================
    # CONSUMING LEARNING SIGNALS
    # =========================================================================
    
    async def on_learning_signal_received(
        self,
        signal: LearningSignal
    ) -> Optional[List[LearningSignal]]:
        """Process learning signals from other components."""
        
        if signal.signal_type == LearningSignalType.AUDIO_FEATURE_VALIDATED:
            # Audio component validated its features - update voice modality weight
            accuracy = signal.payload.get("mean_accuracy", 0.5)
            self._adjust_modality_trust(Modality.VOICE, accuracy)
        
        elif signal.signal_type == LearningSignalType.SIGNAL_ACCURACY_VALIDATED:
            # Signal aggregation validated its signals - update behavioral modality
            accuracy = signal.payload.get("mean_accuracy", 0.5)
            self._adjust_modality_trust(Modality.BEHAVIORAL, accuracy)
        
        elif signal.signal_type == LearningSignalType.ATOM_ATTRIBUTED:
            # Atoms were validated - update psychological modality
            accuracy = signal.payload.get("mean_accuracy", 0.5)
            self._adjust_modality_trust(Modality.PSYCHOLOGICAL, accuracy)
        
        elif signal.signal_type == LearningSignalType.DRIFT_DETECTED:
            # If drift in a modality, reduce its weight temporarily
            drift_source = signal.payload.get("source", "")
            if "voice" in drift_source.lower() or "audio" in drift_source.lower():
                self._learned_weights[Modality.VOICE] *= 0.8
            elif "text" in drift_source.lower():
                self._learned_weights[Modality.TEXT] *= 0.8
            elif "behavioral" in drift_source.lower():
                self._learned_weights[Modality.BEHAVIORAL] *= 0.8
        
        return None
    
    def _adjust_modality_trust(self, modality: Modality, accuracy: float) -> None:
        """Adjust modality weight based on external validation."""
        
        # If other component says this modality's source is accurate, boost it
        adjustment = (accuracy - 0.5) * 0.1  # -0.05 to +0.05
        
        current = self._learned_weights.get(modality, 0.2)
        new_weight = max(0.05, min(0.5, current + adjustment))
        self._learned_weights[modality] = new_weight
    
    def get_consumed_signal_types(self) -> Set[LearningSignalType]:
        return {
            LearningSignalType.AUDIO_FEATURE_VALIDATED,
            LearningSignalType.SIGNAL_ACCURACY_VALIDATED,
            LearningSignalType.ATOM_ATTRIBUTED,
            LearningSignalType.DRIFT_DETECTED,
            LearningSignalType.MECHANISM_EFFECTIVENESS_UPDATED,
        }
    
    # =========================================================================
    # ATTRIBUTION
    # =========================================================================
    
    async def get_learning_contribution(
        self,
        decision_id: str
    ) -> Optional[LearningContribution]:
        """Get this component's contribution to a decision."""
        
        cached = await self.redis.get(f"adam:fusion:prediction:{decision_id}")
        if not cached:
            return None
        
        prediction = FusionPrediction.parse_raw(cached)
        
        return LearningContribution(
            component_name=self.component_name,
            decision_id=decision_id,
            contribution_type="multimodal_fusion",
            contribution_value={
                "modalities_used": [m.value for m in prediction.modalities_used],
                "fusion_method": prediction.fusion_method.value,
                "fused_prediction": prediction.fused_prediction,
                "agreement_score": prediction.agreement_score,
                "dominant_modality": prediction.dominant_modality.value if prediction.dominant_modality else None,
            },
            confidence=prediction.fusion_confidence,
            reasoning_summary=f"Fused {len(prediction.modalities_used)} modalities with {prediction.agreement_score:.2f} agreement",
            evidence_sources=[m.value for m in prediction.modalities_used],
            weight=0.25  # Fusion contributes ~25% to decisions
        )
    
    # =========================================================================
    # QUALITY METRICS
    # =========================================================================
    
    async def get_learning_quality_metrics(self) -> LearningQualityMetrics:
        """Get quality metrics."""
        
        # Overall fusion accuracy
        if self._accuracy_history:
            recent = [a for _, a in self._accuracy_history[-100:]]
            accuracy = np.mean(recent)
        else:
            accuracy = 0.5
        
        # Per-modality health
        modality_health = {
            m.value: eff.unimodal_accuracy 
            for m, eff in self.modality_effectiveness.items()
            if eff.predictions_made > 0
        }
        
        return LearningQualityMetrics(
            component_name=self.component_name,
            signals_emitted=self._outcomes_processed * 3,  # 3 signals per outcome
            outcomes_processed=self._outcomes_processed,
            prediction_accuracy=accuracy,
            prediction_accuracy_trend=self._compute_trend(),
            attribution_coverage=min(len(modality_health) / 4, 1.0),  # Target: 4 modalities
            last_learning_update=datetime.now(timezone.utc),
            upstream_dependencies=["audio_processing", "signal_aggregation", "atom_of_thought"],
            downstream_consumers=["holistic_synthesizer", "gradient_bridge"],
            integration_health=0.85 if self._outcomes_processed > 0 else 0.5
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
        """Inject user-specific fusion priors."""
        
        # User-specific modality preferences
        modality_prefs = priors.get("modality_preferences", {})
        for modality_str, weight in modality_prefs.items():
            try:
                modality = Modality(modality_str)
                self._learned_weights[modality] = weight
            except ValueError:
                pass
        
        await self.redis.setex(
            f"adam:fusion:priors:{user_id}",
            3600,
            modality_prefs
        )
    
    async def validate_learning_health(self) -> Tuple[bool, List[str]]:
        """Validate learning health."""
        
        issues = []
        
        if self._outcomes_processed == 0:
            issues.append("No fusion outcomes processed")
        
        # Check modality balance
        active_modalities = sum(
            1 for eff in self.modality_effectiveness.values()
            if eff.predictions_made > 10
        )
        if active_modalities < 2:
            issues.append(f"Only {active_modalities} modalities active (need >= 2)")
        
        # Check for stuck weights
        weights = list(self._learned_weights.values())
        if max(weights) > 0.6:
            issues.append("Fusion weights too concentrated on one modality")
        
        return len(issues) == 0, issues
    
    # =========================================================================
    # WEIGHT ACCESS FOR FUSION ENGINE
    # =========================================================================
    
    def get_learned_weights(self) -> Dict[str, float]:
        """Get current learned weights for the fusion engine."""
        
        return {m.value: w for m, w in self._learned_weights.items()}
    
    def get_optimal_method(self, context: Dict[str, Any]) -> FusionMethod:
        """Get optimal fusion method for context."""
        
        # Based on learned method effectiveness
        best_method = FusionMethod.WEIGHTED_AVERAGE  # Default
        best_accuracy = 0.0
        
        for method, eff in self.method_effectiveness.items():
            if eff.predictions_made >= 10 and eff.mean_accuracy > best_accuracy:
                best_accuracy = eff.mean_accuracy
                best_method = method
        
        return best_method
