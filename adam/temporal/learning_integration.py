# =============================================================================
# ADAM Enhancement #23 (Gap 23): Temporal Pattern Learning Integration
# Location: adam/temporal/learning_integration.py
# =============================================================================

"""
TEMPORAL PATTERN LEARNING INTEGRATION

CRITICAL GAP IDENTIFIED: #23 had ZERO learning mentions.

This module makes Temporal Pattern Learning a full learning participant by:
1. Validating timing predictions against actual outcomes
2. Learning optimal contact timing per user
3. Updating life event detection accuracy
4. Learning decision stage progression patterns
5. Tracking cyclical pattern effectiveness

Temporal patterns detect:
- Life events (moving, job change, baby, etc.)
- Decision stages (awareness, consideration, decision)
- Optimal timing (best hour, day, week to contact)
- Cyclical patterns (weekly, monthly, seasonal)

Without learning, we detect patterns but never know if they're right.
"""

from typing import Dict, List, Optional, Any, Set, Tuple
from datetime import datetime, timezone, timedelta
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
# TEMPORAL PATTERN DEFINITIONS
# =============================================================================

class LifeEventType(str, Enum):
    """Types of life events we can detect."""
    
    MOVING = "moving"
    JOB_CHANGE = "job_change"
    NEW_BABY = "new_baby"
    MARRIAGE = "marriage"
    DIVORCE = "divorce"
    GRADUATION = "graduation"
    RETIREMENT = "retirement"
    HEALTH_CHANGE = "health_change"
    FINANCIAL_CHANGE = "financial_change"
    NONE_DETECTED = "none_detected"


class DecisionStage(str, Enum):
    """Decision stage in the customer journey."""
    
    UNAWARE = "unaware"
    AWARE = "aware"
    CONSIDERATION = "consideration"
    EVALUATION = "evaluation"
    DECISION = "decision"
    POST_PURCHASE = "post_purchase"


class TimingPrediction(BaseModel):
    """A timing prediction that can be validated."""
    
    prediction_id: str = Field(default_factory=lambda: f"time_{uuid.uuid4().hex[:12]}")
    
    # Context
    user_id: str
    decision_id: str
    
    # What we predicted
    predicted_optimal_hour: Optional[int] = None  # 0-23
    predicted_optimal_day: Optional[int] = None   # 0-6 (Mon-Sun)
    predicted_life_event: Optional[LifeEventType] = None
    predicted_decision_stage: Optional[DecisionStage] = None
    
    # Confidence
    timing_confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    life_event_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    stage_confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    
    # Actual timing when prediction was made
    actual_hour: int
    actual_day: int
    
    # Was this the optimal timing according to our prediction?
    is_predicted_optimal: bool = False
    
    # Resolution
    resolved: bool = False
    outcome_value: Optional[float] = None
    timing_was_correct: Optional[bool] = None


class TimingEffectiveness(BaseModel):
    """Learned effectiveness of a timing slot."""
    
    hour: int  # 0-23
    day: int   # 0-6
    
    # Effectiveness
    impressions: int = 0
    conversions: int = 0
    conversion_rate: float = 0.0
    
    # Relative to baseline
    lift_vs_baseline: float = 0.0
    
    # User-specific override
    user_specific_rates: Dict[str, float] = Field(default_factory=dict)


class LifeEventEffectiveness(BaseModel):
    """Learned effectiveness of life event detection."""
    
    event_type: LifeEventType
    
    # Detection accuracy
    times_predicted: int = 0
    times_confirmed: int = 0
    precision: float = 0.5
    
    # Impact on conversion
    conversion_lift: float = 0.0
    avg_confidence_when_correct: float = 0.5


class DecisionStageEffectiveness(BaseModel):
    """Learned effectiveness of decision stage prediction."""
    
    stage: DecisionStage
    
    # Accuracy
    times_predicted: int = 0
    times_correct: int = 0
    accuracy: float = 0.5
    
    # Stage transition rates
    transition_to: Dict[str, float] = Field(default_factory=dict)


# =============================================================================
# TEMPORAL LEARNING BRIDGE
# =============================================================================

class TemporalLearningBridge(LearningCapableComponent):
    """
    Learning integration for Gap 23: Temporal Pattern Learning.
    
    This transforms temporal pattern detection from passive observation
    into active learning that validates and improves predictions.
    """
    
    def __init__(
        self,
        temporal_engine,
        neo4j_driver,
        redis_client,
        event_bus
    ):
        self.temporal_engine = temporal_engine
        self.neo4j = neo4j_driver
        self.redis = redis_client
        self.event_bus = event_bus
        
        # Timing effectiveness (24 hours x 7 days matrix)
        self.timing_effectiveness: Dict[Tuple[int, int], TimingEffectiveness] = {}
        for hour in range(24):
            for day in range(7):
                self.timing_effectiveness[(hour, day)] = TimingEffectiveness(
                    hour=hour, day=day
                )
        
        # Life event effectiveness
        self.life_event_effectiveness: Dict[LifeEventType, LifeEventEffectiveness] = {
            e: LifeEventEffectiveness(event_type=e) for e in LifeEventType
        }
        
        # Decision stage effectiveness
        self.stage_effectiveness: Dict[DecisionStage, DecisionStageEffectiveness] = {
            s: DecisionStageEffectiveness(stage=s) for s in DecisionStage
        }
        
        # Pending predictions
        self.pending_predictions: Dict[str, TimingPrediction] = {}
        
        # Quality tracking
        self._outcomes_processed: int = 0
        self._timing_correct: int = 0
        self._life_events_confirmed: int = 0
    
    @property
    def component_name(self) -> str:
        return "temporal_patterns"
    
    @property
    def component_version(self) -> str:
        return "2.0"  # Now with learning
    
    # =========================================================================
    # TEMPORAL PREDICTION REGISTRATION
    # =========================================================================
    
    async def register_temporal_prediction(
        self,
        decision_id: str,
        user_id: str,
        predicted_optimal_hour: Optional[int] = None,
        predicted_optimal_day: Optional[int] = None,
        predicted_life_event: Optional[LifeEventType] = None,
        predicted_decision_stage: Optional[DecisionStage] = None,
        timing_confidence: float = 0.5,
        life_event_confidence: float = 0.0,
        stage_confidence: float = 0.5,
    ) -> TimingPrediction:
        """
        Register a temporal prediction for later validation.
        """
        
        now = datetime.now(timezone.utc)
        
        prediction = TimingPrediction(
            user_id=user_id,
            decision_id=decision_id,
            predicted_optimal_hour=predicted_optimal_hour,
            predicted_optimal_day=predicted_optimal_day,
            predicted_life_event=predicted_life_event,
            predicted_decision_stage=predicted_decision_stage,
            timing_confidence=timing_confidence,
            life_event_confidence=life_event_confidence,
            stage_confidence=stage_confidence,
            actual_hour=now.hour,
            actual_day=now.weekday(),
            is_predicted_optimal=(
                now.hour == predicted_optimal_hour and 
                now.weekday() == predicted_optimal_day
            ) if predicted_optimal_hour is not None else False,
        )
        
        self.pending_predictions[decision_id] = prediction
        
        await self.redis.setex(
            f"adam:temporal:prediction:{decision_id}",
            86400 * 7,  # 7 day TTL for temporal analysis
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
        Validate temporal predictions against outcomes.
        """
        
        signals = []
        
        # Get prediction
        prediction = self.pending_predictions.pop(decision_id, None)
        if not prediction:
            cached = await self.redis.get(f"adam:temporal:prediction:{decision_id}")
            if cached:
                prediction = TimingPrediction.parse_raw(cached)
        
        if not prediction:
            return []
        
        self._outcomes_processed += 1
        is_positive = outcome_value > 0.5
        
        # Resolve prediction
        prediction.resolved = True
        prediction.outcome_value = outcome_value
        
        # =====================================================================
        # VALIDATE TIMING PREDICTION
        # =====================================================================
        
        # Update timing effectiveness for the actual hour/day
        timing_key = (prediction.actual_hour, prediction.actual_day)
        timing_eff = self.timing_effectiveness[timing_key]
        timing_eff.impressions += 1
        if is_positive:
            timing_eff.conversions += 1
        timing_eff.conversion_rate = timing_eff.conversions / timing_eff.impressions
        
        # Check if our timing prediction was correct
        if prediction.is_predicted_optimal:
            prediction.timing_was_correct = is_positive
            if is_positive:
                self._timing_correct += 1
        
        # Compute lift vs. baseline
        baseline_rate = np.mean([
            t.conversion_rate for t in self.timing_effectiveness.values()
            if t.impressions >= 10
        ]) if any(t.impressions >= 10 for t in self.timing_effectiveness.values()) else 0.05
        
        if baseline_rate > 0:
            timing_eff.lift_vs_baseline = (timing_eff.conversion_rate - baseline_rate) / baseline_rate
        
        # =====================================================================
        # VALIDATE LIFE EVENT DETECTION
        # =====================================================================
        
        life_event_result = None
        if prediction.predicted_life_event and prediction.predicted_life_event != LifeEventType.NONE_DETECTED:
            event_eff = self.life_event_effectiveness[prediction.predicted_life_event]
            event_eff.times_predicted += 1
            
            # We can't directly validate life events from conversion,
            # but high confidence predictions with positive outcomes
            # are more likely correct
            if is_positive and prediction.life_event_confidence > 0.7:
                event_eff.times_confirmed += 1
                event_eff.avg_confidence_when_correct = (
                    event_eff.avg_confidence_when_correct * 0.9 +
                    prediction.life_event_confidence * 0.1
                )
                self._life_events_confirmed += 1
            
            event_eff.precision = event_eff.times_confirmed / event_eff.times_predicted
            
            # Conversion lift for this life event
            if event_eff.times_predicted >= 20:
                event_eff.conversion_lift = event_eff.times_confirmed / event_eff.times_predicted - baseline_rate
            
            life_event_result = {
                "event": prediction.predicted_life_event.value,
                "confidence": prediction.life_event_confidence,
                "outcome": outcome_value,
            }
        
        # =====================================================================
        # VALIDATE DECISION STAGE
        # =====================================================================
        
        stage_result = None
        if prediction.predicted_decision_stage:
            stage_eff = self.stage_effectiveness[prediction.predicted_decision_stage]
            stage_eff.times_predicted += 1
            
            # Check if outcome matches expected for this stage
            expected_outcomes = {
                DecisionStage.UNAWARE: 0.02,
                DecisionStage.AWARE: 0.05,
                DecisionStage.CONSIDERATION: 0.10,
                DecisionStage.EVALUATION: 0.20,
                DecisionStage.DECISION: 0.40,
                DecisionStage.POST_PURCHASE: 0.15,
            }
            
            expected = expected_outcomes.get(prediction.predicted_decision_stage, 0.05)
            stage_correct = (is_positive and expected > 0.15) or (not is_positive and expected < 0.15)
            
            if stage_correct:
                stage_eff.times_correct += 1
            stage_eff.accuracy = stage_eff.times_correct / stage_eff.times_predicted
            
            stage_result = {
                "stage": prediction.predicted_decision_stage.value,
                "confidence": prediction.stage_confidence,
                "was_correct": stage_correct,
            }
        
        # =====================================================================
        # EMIT LEARNING SIGNALS
        # =====================================================================
        
        # 1. Timing effectiveness signal
        signals.append(LearningSignal(
            signal_type=LearningSignalType.PRIOR_UPDATED,
            source_component=self.component_name,
            decision_id=decision_id,
            payload={
                "timing_validated": True,
                "hour": prediction.actual_hour,
                "day": prediction.actual_day,
                "conversion_rate": timing_eff.conversion_rate,
                "lift_vs_baseline": timing_eff.lift_vs_baseline,
                "was_predicted_optimal": prediction.is_predicted_optimal,
                "outcome": outcome_value,
            },
            confidence=0.85,
            target_components=["holistic_synthesizer", "meta_learner"]
        ))
        
        # 2. Life event validation signal
        if life_event_result:
            signals.append(LearningSignal(
                signal_type=LearningSignalType.BEHAVIORAL_PATTERN_VALIDATED,
                source_component=self.component_name,
                decision_id=decision_id,
                payload={
                    "pattern_type": "life_event",
                    **life_event_result,
                },
                confidence=0.7,
                target_components=["journey_tracker", "psychological_constructs"]
            ))
        
        # 3. Decision stage validation signal
        if stage_result:
            signals.append(LearningSignal(
                signal_type=LearningSignalType.STATE_TRANSITION_LEARNED,
                source_component=self.component_name,
                decision_id=decision_id,
                user_id=prediction.user_id,
                payload={
                    "stage_validation": stage_result,
                },
                confidence=0.75,
                target_components=["journey_tracker", "gradient_bridge"]
            ))
        
        # 4. Optimal timing discovery (if we found a high-performing slot)
        if timing_eff.lift_vs_baseline > 0.5 and timing_eff.impressions >= 50:
            signals.append(LearningSignal(
                signal_type=LearningSignalType.PATTERN_EMERGED,
                source_component=self.component_name,
                decision_id=decision_id,
                payload={
                    "pattern_type": "optimal_timing",
                    "hour": timing_eff.hour,
                    "day": timing_eff.day,
                    "lift": timing_eff.lift_vs_baseline,
                    "sample_size": timing_eff.impressions,
                },
                confidence=0.8,
                target_components=["holistic_synthesizer", "campaign_optimizer"]
            ))
        
        # Store in Neo4j
        await self._store_temporal_learning(prediction, timing_eff)
        
        return signals
    
    async def _store_temporal_learning(
        self,
        prediction: TimingPrediction,
        timing_eff: TimingEffectiveness
    ) -> None:
        """Store temporal learning in Neo4j."""
        
        query = """
        MERGE (t:TimingSlot {hour: $hour, day: $day})
        SET t.impressions = $impressions,
            t.conversions = $conversions,
            t.conversion_rate = $rate,
            t.lift_vs_baseline = $lift,
            t.updated_at = datetime()
        """
        
        async with self.neo4j.session() as session:
            await session.run(
                query,
                hour=timing_eff.hour,
                day=timing_eff.day,
                impressions=timing_eff.impressions,
                conversions=timing_eff.conversions,
                rate=timing_eff.conversion_rate,
                lift=timing_eff.lift_vs_baseline,
            )
    
    # =========================================================================
    # CONSUMING LEARNING SIGNALS
    # =========================================================================
    
    async def on_learning_signal_received(
        self,
        signal: LearningSignal
    ) -> Optional[List[LearningSignal]]:
        """Process learning signals."""
        
        if signal.signal_type == LearningSignalType.STATE_TRANSITION_LEARNED:
            # Update stage transition probabilities
            from_stage = signal.payload.get("from_state")
            to_stage = signal.payload.get("to_state")
            
            if from_stage and to_stage:
                try:
                    stage_enum = DecisionStage(from_stage)
                    stage_eff = self.stage_effectiveness[stage_enum]
                    
                    if to_stage not in stage_eff.transition_to:
                        stage_eff.transition_to[to_stage] = 0.0
                    stage_eff.transition_to[to_stage] = (
                        stage_eff.transition_to[to_stage] * 0.9 + 0.1
                    )
                except ValueError:
                    pass
        
        return None
    
    def get_consumed_signal_types(self) -> Set[LearningSignalType]:
        return {
            LearningSignalType.STATE_TRANSITION_LEARNED,
            LearningSignalType.MECHANISM_EFFECTIVENESS_UPDATED,
        }
    
    # =========================================================================
    # ATTRIBUTION
    # =========================================================================
    
    async def get_learning_contribution(
        self,
        decision_id: str
    ) -> Optional[LearningContribution]:
        """Get temporal contribution to decision."""
        
        cached = await self.redis.get(f"adam:temporal:prediction:{decision_id}")
        if not cached:
            return None
        
        prediction = TimingPrediction.parse_raw(cached)
        
        return LearningContribution(
            component_name=self.component_name,
            decision_id=decision_id,
            contribution_type="temporal_context",
            contribution_value={
                "predicted_optimal_hour": prediction.predicted_optimal_hour,
                "predicted_optimal_day": prediction.predicted_optimal_day,
                "is_predicted_optimal": prediction.is_predicted_optimal,
                "life_event": prediction.predicted_life_event.value if prediction.predicted_life_event else None,
                "decision_stage": prediction.predicted_decision_stage.value if prediction.predicted_decision_stage else None,
            },
            confidence=prediction.timing_confidence,
            reasoning_summary=f"Temporal context: hour={prediction.actual_hour}, day={prediction.actual_day}, optimal={prediction.is_predicted_optimal}",
            weight=0.15
        )
    
    # =========================================================================
    # QUALITY METRICS
    # =========================================================================
    
    async def get_learning_quality_metrics(self) -> LearningQualityMetrics:
        """Get quality metrics."""
        
        # Timing prediction accuracy
        if self._outcomes_processed > 0:
            timing_accuracy = self._timing_correct / self._outcomes_processed
        else:
            timing_accuracy = 0.5
        
        # Life event precision
        total_life_events = sum(
            e.times_predicted for e in self.life_event_effectiveness.values()
        )
        if total_life_events > 0:
            life_event_precision = sum(
                e.times_confirmed for e in self.life_event_effectiveness.values()
            ) / total_life_events
        else:
            life_event_precision = 0.5
        
        return LearningQualityMetrics(
            component_name=self.component_name,
            signals_emitted=self._outcomes_processed * 3,
            outcomes_processed=self._outcomes_processed,
            prediction_accuracy=(timing_accuracy + life_event_precision) / 2,
            attribution_coverage=0.8,
            last_learning_update=datetime.now(timezone.utc),
            upstream_dependencies=["signal_aggregation", "journey_tracker"],
            downstream_consumers=["holistic_synthesizer", "campaign_optimizer"],
            integration_health=0.85 if self._outcomes_processed > 0 else 0.5
        )
    
    async def inject_priors(self, user_id: str, priors: Dict[str, Any]) -> None:
        """Inject user-specific temporal priors."""
        
        # User's preferred timing
        preferred_hour = priors.get("preferred_hour")
        preferred_day = priors.get("preferred_day")
        
        if preferred_hour is not None and preferred_day is not None:
            timing_key = (preferred_hour, preferred_day)
            if timing_key in self.timing_effectiveness:
                eff = self.timing_effectiveness[timing_key]
                eff.user_specific_rates[user_id] = priors.get("user_conversion_rate", 0.1)
    
    async def validate_learning_health(self) -> Tuple[bool, List[str]]:
        """Validate learning health."""
        
        issues = []
        
        if self._outcomes_processed == 0:
            issues.append("No temporal outcomes processed")
        
        # Check timing coverage
        active_slots = sum(
            1 for t in self.timing_effectiveness.values()
            if t.impressions >= 10
        )
        if active_slots < 50:  # 168 total slots
            issues.append(f"Only {active_slots}/168 timing slots have sufficient data")
        
        return len(issues) == 0, issues
    
    # =========================================================================
    # OPTIMAL TIMING ACCESS
    # =========================================================================
    
    def get_optimal_timing(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Get optimal timing for a user or globally."""
        
        # Find best performing slots
        slots_with_data = [
            t for t in self.timing_effectiveness.values()
            if t.impressions >= 20
        ]
        
        if not slots_with_data:
            return {"hour": 12, "day": 2, "confidence": 0.3}  # Default: Wed noon
        
        # If user-specific data available
        if user_id:
            user_slots = [
                t for t in slots_with_data
                if user_id in t.user_specific_rates
            ]
            if user_slots:
                best = max(user_slots, key=lambda t: t.user_specific_rates[user_id])
                return {
                    "hour": best.hour,
                    "day": best.day,
                    "confidence": 0.8,
                    "source": "user_specific"
                }
        
        # Global best
        best = max(slots_with_data, key=lambda t: t.conversion_rate)
        return {
            "hour": best.hour,
            "day": best.day,
            "confidence": 0.6,
            "lift": best.lift_vs_baseline,
            "source": "global"
        }
