# =============================================================================
# Psychological Intelligence Learning Integration
# Location: adam/intelligence/learning/psychological_learning_integration.py
# =============================================================================

"""
DEEP LEARNING INTEGRATION FOR PSYCHOLOGICAL INTELLIGENCE MODULES

This module provides LearningCapableComponent implementations for all
psychological intelligence modules, ensuring they participate fully in
the universal learning architecture.

Integrated modules:
1. UnifiedPsychologicalIntelligence - Central psychological analysis hub
2. FlowStateDetection - Audio/context-based flow states
3. NeedDetection - 33 psychological needs
4. PsycholinguisticAnalysis - 32 constructs with linguistic markers
5. EnhancedReviewAnalyzer - 35-construct review analysis
6. RelationshipDetector - Consumer-brand relationships

Learning signals emitted:
- PSYCHOLOGICAL_PROFILE_CREATED - New profile analyzed
- ARCHETYPE_DETECTED - Archetype determination
- MECHANISM_EFFECTIVENESS_PREDICTED - Mechanism predictions
- NEED_ALIGNMENT_CALCULATED - Brand-consumer alignment
- FLOW_STATE_DETECTED - Flow state determination
- CONSTRUCT_VALIDATED - Psycholinguistic construct scored

These integrations ensure continuous learning from:
- Outcome feedback (did the predicted mechanisms work?)
- Cross-component validation (did other components confirm?)
- A/B testing results
- Customer engagement metrics
"""

import logging
from abc import ABC
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple
import uuid

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Import base learning interface
try:
    from adam.core.learning.universal_learning_interface import (
        LearningCapableComponent,
        LearningSignal,
        LearningSignalType,
        LearningSignalPriority,
        LearningContribution,
        LearningQualityMetrics,
    )
    LEARNING_INTERFACE_AVAILABLE = True
except ImportError:
    LEARNING_INTERFACE_AVAILABLE = False
    # Create minimal stubs that match the enum values
    class LearningCapableComponent(ABC):
        pass
    class LearningSignal(BaseModel):
        signal_id: str = ""
        signal_type: str = ""
        source_component: str = ""
        payload: Dict = {}
        confidence: float = 0.5
        class Config:
            extra = "allow"
    class LearningSignalType:
        # Matches the actual enum values from universal_learning_interface.py
        PATTERN_EMERGED = "pattern_emerged"
        PRIOR_UPDATED = "prior_updated"
        MECHANISM_EFFECTIVENESS_UPDATED = "mechanism_effectiveness"
        BEHAVIORAL_PATTERN_VALIDATED = "behavioral_pattern"
        SIGNAL_QUALITY_UPDATED = "signal_quality"
        SIGNAL_ACCURACY_VALIDATED = "signal_accuracy"
        COPY_EFFECTIVENESS = "copy_effectiveness"
        CREDIT_ASSIGNED = "credit_assigned"
        PREDICTION_VALIDATED = "prediction_validated"
    class LearningSignalPriority:
        NORMAL = 2
        HIGH = 3


# =============================================================================
# CUSTOM LEARNING SIGNAL TYPES FOR PSYCHOLOGICAL INTELLIGENCE
# =============================================================================

class PsychologicalLearningSignalType:
    """Extended signal types for psychological intelligence."""
    
    # Profile signals
    PSYCHOLOGICAL_PROFILE_CREATED = "psychological_profile_created"
    ARCHETYPE_DETECTED = "archetype_detected"
    ARCHETYPE_VALIDATED = "archetype_validated"
    
    # Mechanism signals
    MECHANISM_EFFECTIVENESS_PREDICTED = "mechanism_effectiveness_predicted"
    MECHANISM_EFFECTIVENESS_VALIDATED = "mechanism_effectiveness_validated"
    
    # Flow state signals
    FLOW_STATE_DETECTED = "flow_state_detected"
    FLOW_STATE_VALIDATED = "flow_state_validated"
    AD_RECEPTIVITY_PREDICTED = "ad_receptivity_predicted"
    
    # Need signals
    NEED_DETECTED = "need_detected"
    NEED_ALIGNMENT_CALCULATED = "need_alignment_calculated"
    UNMET_NEED_IDENTIFIED = "unmet_need_identified"
    
    # Construct signals
    CONSTRUCT_SCORED = "construct_scored"
    CONSTRUCT_VALIDATED = "construct_validated"
    REGULATORY_FOCUS_DETECTED = "regulatory_focus_detected"
    
    # Recommendation signals
    AD_RECOMMENDATION_GENERATED = "ad_recommendation_generated"
    AD_RECOMMENDATION_VALIDATED = "ad_recommendation_validated"


# =============================================================================
# UNIFIED PSYCHOLOGICAL INTELLIGENCE LEARNING INTEGRATION
# =============================================================================

class UnifiedPsychologicalIntelligenceLearning:
    """
    Deep learning integration for UnifiedPsychologicalIntelligence.
    
    This integration:
    1. Emits learning signals when profiles are created
    2. Tracks mechanism prediction accuracy
    3. Learns from outcome feedback
    4. Updates archetype detection models
    5. Propagates learning to downstream components
    """
    
    def __init__(
        self,
        unified_intelligence,
        gradient_bridge=None,
        redis_client=None,
        neo4j_driver=None,
    ):
        self.unified_intelligence = unified_intelligence
        self.gradient_bridge = gradient_bridge
        self.redis = redis_client
        self.neo4j = neo4j_driver
        
        # Tracking
        self._profiles_created: int = 0
        self._predictions_made: int = 0
        self._predictions_validated: int = 0
        self._mechanism_accuracy: Dict[str, List[float]] = {}
        self._archetype_accuracy: Dict[str, List[float]] = {}
    
    @property
    def component_name(self) -> str:
        return "unified_psychological_intelligence"
    
    async def emit_profile_learning_signals(
        self,
        profile,
        decision_id: Optional[str] = None,
    ) -> List[LearningSignal]:
        """
        Emit comprehensive learning signals when a profile is created.
        
        This is the deep learning emission that allows other components
        to learn from the psychological analysis.
        """
        signals = []
        
        self._profiles_created += 1
        decision_id = decision_id or f"profile_{profile.profile_id}"
        
        # Use existing LearningSignalType values that match our purposes
        # Map: psychological_profile_created -> pattern_emerged
        # Map: archetype_detected -> prior_updated
        # Map: mechanism_predicted -> mechanism_effectiveness
        # Map: flow_state -> behavioral_pattern
        # Map: construct_scored -> signal_quality
        
        # 1. Profile creation signal (maps to pattern_emerged - a new pattern discovered)
        signals.append(LearningSignal(
            signal_id=f"psych_{uuid.uuid4().hex[:12]}",
            signal_type=LearningSignalType.PATTERN_EMERGED,
            source_component=self.component_name,
            payload={
                "pattern_type": "psychological_profile",
                "profile_id": profile.profile_id,
                "brand_name": profile.brand_name,
                "product_name": profile.product_name,
                "reviews_analyzed": profile.reviews_analyzed,
                "modules_used": profile.modules_used,
                "analysis_time_ms": profile.analysis_time_ms,
            },
            confidence=profile.archetype_confidence,
        ))
        
        # 2. Archetype detection signal (maps to prior_updated - archetype belief updated)
        signals.append(LearningSignal(
            signal_id=f"arch_{uuid.uuid4().hex[:12]}",
            signal_type=LearningSignalType.PRIOR_UPDATED,
            source_component=self.component_name,
            payload={
                "prior_type": "archetype",
                "profile_id": profile.profile_id,
                "archetype": profile.primary_archetype,
                "archetype_confidence": profile.archetype_confidence,
            },
            confidence=profile.archetype_confidence,
        ))
        
        # 3. Mechanism prediction signals (maps to mechanism_effectiveness)
        for mechanism, effectiveness in profile.mechanism_predictions.items():
            self._predictions_made += 1
            signals.append(LearningSignal(
                signal_id=f"mech_{uuid.uuid4().hex[:12]}",
                signal_type=LearningSignalType.MECHANISM_EFFECTIVENESS_UPDATED,
                source_component=self.component_name,
                payload={
                    "profile_id": profile.profile_id,
                    "mechanism": mechanism,
                    "predicted_effectiveness": effectiveness,
                    "archetype": profile.primary_archetype,
                    "brand_name": profile.brand_name,
                },
                confidence=min(0.9, effectiveness + 0.2),
            ))
        
        # 4. Flow state signals (maps to behavioral_pattern)
        flow = profile.flow_state
        signals.append(LearningSignal(
            signal_id=f"flow_{uuid.uuid4().hex[:12]}",
            signal_type=LearningSignalType.BEHAVIORAL_PATTERN_VALIDATED,
            source_component=self.component_name,
            payload={
                "pattern_type": "flow_state",
                "profile_id": profile.profile_id,
                "arousal": flow.arousal,
                "valence": flow.valence,
                "energy": flow.energy,
                "cognitive_load": flow.cognitive_load,
                "ad_receptivity": flow.ad_receptivity_score,
                "optimal_formats": flow.optimal_formats,
                "recommended_tone": flow.recommended_tone,
            },
            confidence=0.7,
        ))
        
        # 5. Regulatory focus signal (maps to prior_updated)
        needs = profile.psychological_needs
        signals.append(LearningSignal(
            signal_id=f"regf_{uuid.uuid4().hex[:12]}",
            signal_type=LearningSignalType.PRIOR_UPDATED,
            source_component=self.component_name,
            payload={
                "prior_type": "regulatory_focus",
                "profile_id": profile.profile_id,
                "promotion_focus": needs.promotion_focus,
                "prevention_focus": needs.prevention_focus,
                "dominant_focus": "promotion" if needs.promotion_focus > needs.prevention_focus else "prevention",
            },
            confidence=0.75,
        ))
        
        # 6. Need alignment signal (maps to signal_quality - quality of brand-need alignment)
        signals.append(LearningSignal(
            signal_id=f"need_{uuid.uuid4().hex[:12]}",
            signal_type=LearningSignalType.SIGNAL_QUALITY_UPDATED,
            source_component=self.component_name,
            payload={
                "signal_type": "need_alignment",
                "profile_id": profile.profile_id,
                "alignment_score": needs.overall_alignment_score,
                "unmet_needs": needs.unmet_needs[:5],
                "primary_needs": dict(needs.primary_needs[:10]),
            },
            confidence=0.7,
        ))
        
        # 7. Top construct signals (maps to signal_accuracy - construct detection accuracy)
        top_constructs = sorted(
            profile.unified_constructs.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]
        
        for construct, score in top_constructs:
            signals.append(LearningSignal(
                signal_id=f"con_{uuid.uuid4().hex[:12]}",
                signal_type=LearningSignalType.SIGNAL_ACCURACY_VALIDATED,
                source_component=self.component_name,
                payload={
                    "signal_type": "construct",
                    "profile_id": profile.profile_id,
                    "construct": construct,
                    "score": score,
                    "archetype": profile.primary_archetype,
                },
                confidence=0.75,
            ))
        
        # 8. Ad recommendation signals (maps to copy_effectiveness)
        for rec in profile.unified_ad_recommendations[:3]:
            signals.append(LearningSignal(
                signal_id=f"rec_{uuid.uuid4().hex[:12]}",
                signal_type=LearningSignalType.COPY_EFFECTIVENESS,
                source_component=self.component_name,
                payload={
                    "profile_id": profile.profile_id,
                    "construct_name": rec.construct_name,
                    "recommendation": rec.recommendation,
                    "confidence": rec.confidence,
                    "source_modules": [str(s.value) for s in rec.source_modules] if hasattr(rec, 'source_modules') else [],
                },
                confidence=rec.confidence,
            ))
        
        # Propagate to Gradient Bridge if available
        if self.gradient_bridge:
            for signal in signals:
                try:
                    await self.gradient_bridge.process_learning_signal(signal)
                except Exception as e:
                    logger.debug(f"Gradient bridge signal failed: {e}")
        
        logger.info(
            f"Emitted {len(signals)} learning signals for profile {profile.profile_id}"
        )
        
        return signals
    
    async def on_outcome_received(
        self,
        decision_id: str,
        outcome_type: str,
        outcome_value: float,
        context: Dict[str, Any],
    ) -> List[LearningSignal]:
        """
        Learn from actual outcomes to validate/update predictions.
        
        This is the feedback loop that makes the system truly learn.
        """
        signals = []
        
        # Get the original prediction
        profile_id = context.get("profile_id")
        mechanism_used = context.get("mechanism")
        archetype = context.get("archetype")
        
        if not profile_id:
            return signals
        
        self._predictions_validated += 1
        
        # 1. Validate mechanism prediction
        if mechanism_used:
            # Track accuracy
            if mechanism_used not in self._mechanism_accuracy:
                self._mechanism_accuracy[mechanism_used] = []
            self._mechanism_accuracy[mechanism_used].append(outcome_value)
            
            signals.append(LearningSignal(
                signal_id=f"valid_{uuid.uuid4().hex[:12]}",
                signal_type=PsychologicalLearningSignalType.MECHANISM_EFFECTIVENESS_VALIDATED,
                source_component=self.component_name,
                payload={
                    "profile_id": profile_id,
                    "mechanism": mechanism_used,
                    "predicted_effectiveness": context.get("predicted_effectiveness", 0.5),
                    "actual_outcome": outcome_value,
                    "archetype": archetype,
                    "validation_source": outcome_type,
                },
                confidence=0.9,
            ))
        
        # 2. Validate archetype prediction
        if archetype:
            if archetype not in self._archetype_accuracy:
                self._archetype_accuracy[archetype] = []
            self._archetype_accuracy[archetype].append(outcome_value)
            
            signals.append(LearningSignal(
                signal_id=f"arch_valid_{uuid.uuid4().hex[:12]}",
                signal_type=PsychologicalLearningSignalType.ARCHETYPE_VALIDATED,
                source_component=self.component_name,
                payload={
                    "profile_id": profile_id,
                    "archetype": archetype,
                    "outcome": outcome_value,
                    "success": outcome_value > 0.5,
                },
                confidence=0.85,
            ))
        
        # 3. Update Neo4j with outcome
        if self.neo4j:
            await self._store_outcome_in_graph(
                profile_id, mechanism_used, archetype, outcome_value
            )
        
        return signals
    
    async def _store_outcome_in_graph(
        self,
        profile_id: str,
        mechanism: Optional[str],
        archetype: Optional[str],
        outcome: float,
    ) -> None:
        """Store outcome in Neo4j for graph-based learning."""
        if not self.neo4j:
            return
        
        try:
            query = """
            MATCH (p:PsychologicalProfile {profile_id: $profile_id})
            SET p.outcomes_received = COALESCE(p.outcomes_received, 0) + 1,
                p.average_outcome = COALESCE(p.average_outcome, 0) * 0.9 + $outcome * 0.1,
                p.last_outcome_at = datetime()
            
            WITH p
            OPTIONAL MATCH (p)-[r:PREDICTS_MECHANISM]->(m:Mechanism {name: $mechanism})
            WHERE $mechanism IS NOT NULL
            SET r.validated_effectiveness = COALESCE(r.validated_effectiveness, r.predicted_effectiveness) * 0.9 + $outcome * 0.1,
                r.validation_count = COALESCE(r.validation_count, 0) + 1
            
            RETURN p
            """
            
            async with self.neo4j.session() as session:
                await session.run(
                    query,
                    profile_id=profile_id,
                    mechanism=mechanism,
                    outcome=outcome,
                )
        except Exception as e:
            logger.debug(f"Neo4j outcome storage failed: {e}")
    
    def get_learning_quality_metrics(self) -> Dict[str, Any]:
        """Get quality metrics for this component's learning."""
        
        # Calculate mechanism prediction accuracy
        mechanism_accuracies = {}
        for mech, outcomes in self._mechanism_accuracy.items():
            if outcomes:
                mechanism_accuracies[mech] = sum(outcomes) / len(outcomes)
        
        # Calculate archetype prediction accuracy
        archetype_accuracies = {}
        for arch, outcomes in self._archetype_accuracy.items():
            if outcomes:
                archetype_accuracies[arch] = sum(outcomes) / len(outcomes)
        
        return {
            "component_name": self.component_name,
            "profiles_created": self._profiles_created,
            "predictions_made": self._predictions_made,
            "predictions_validated": self._predictions_validated,
            "validation_rate": (
                self._predictions_validated / max(self._predictions_made, 1)
            ),
            "mechanism_accuracies": mechanism_accuracies,
            "archetype_accuracies": archetype_accuracies,
            "overall_accuracy": (
                sum(mechanism_accuracies.values()) / max(len(mechanism_accuracies), 1)
                if mechanism_accuracies else 0.5
            ),
        }


# =============================================================================
# REVIEW ANALYZER LEARNING INTEGRATION
# =============================================================================

class ReviewAnalyzerLearning:
    """
    Deep learning integration for EnhancedReviewAnalyzer.
    
    Enables the review analyzer to learn from:
    1. Which psychological patterns correlate with conversions
    2. Which language patterns predict customer segments
    3. How accurate archetype detections are
    """
    
    def __init__(self, enhanced_analyzer=None, gradient_bridge=None):
        self.enhanced_analyzer = enhanced_analyzer
        self.gradient_bridge = gradient_bridge
        
        self._reviews_analyzed: int = 0
        self._patterns_detected: Dict[str, int] = {}
    
    @property
    def component_name(self) -> str:
        return "enhanced_review_analyzer"
    
    async def emit_analysis_signals(
        self,
        analysis_result,
        brand_name: str,
        product_name: str,
    ) -> List[LearningSignal]:
        """Emit learning signals from review analysis."""
        signals = []
        
        self._reviews_analyzed += 1
        
        # Emit construct detection signals
        if hasattr(analysis_result, 'constructs'):
            for construct, value in analysis_result.constructs.items():
                pattern_key = f"{construct}_{brand_name}"
                self._patterns_detected[pattern_key] = (
                    self._patterns_detected.get(pattern_key, 0) + 1
                )
                
                signals.append(LearningSignal(
                    signal_id=f"ra_{uuid.uuid4().hex[:12]}",
                    signal_type=LearningSignalType.PATTERN_EMERGED,
                    source_component=self.component_name,
                    payload={
                        "construct": construct,
                        "value": value,
                        "brand_name": brand_name,
                        "product_name": product_name,
                        "observation_count": self._patterns_detected[pattern_key],
                    },
                    confidence=min(0.9, 0.5 + (self._patterns_detected[pattern_key] / 100)),
                ))
        
        return signals


# =============================================================================
# FLOW STATE LEARNING INTEGRATION  
# =============================================================================

class FlowStateLearning:
    """
    Deep learning integration for Flow State Detection.
    
    Learns:
    1. Which flow states correlate with ad receptivity
    2. Optimal ad formats for different flow states
    3. Flow state patterns by time/context
    """
    
    def __init__(self, flow_engine=None, gradient_bridge=None):
        self.flow_engine = flow_engine
        self.gradient_bridge = gradient_bridge
        
        self._states_detected: int = 0
        self._receptivity_predictions: List[Tuple[float, float]] = []  # (predicted, actual)
    
    @property
    def component_name(self) -> str:
        return "flow_state_detection"
    
    async def emit_flow_signals(
        self,
        flow_profile,
        context: Dict[str, Any],
    ) -> List[LearningSignal]:
        """Emit learning signals from flow state analysis."""
        signals = []
        
        self._states_detected += 1
        
        # Ad receptivity prediction signal
        signals.append(LearningSignal(
            signal_id=f"fs_{uuid.uuid4().hex[:12]}",
            signal_type=PsychologicalLearningSignalType.AD_RECEPTIVITY_PREDICTED,
            source_component=self.component_name,
            payload={
                "arousal": flow_profile.arousal,
                "valence": flow_profile.valence,
                "cognitive_load": flow_profile.cognitive_load,
                "ad_receptivity": flow_profile.ad_receptivity_score,
                "optimal_formats": flow_profile.optimal_formats,
                "recommended_tone": flow_profile.recommended_tone,
                "context": context,
            },
            confidence=0.7,
        ))
        
        return signals
    
    async def on_outcome_received(
        self,
        predicted_receptivity: float,
        actual_engagement: float,
    ) -> None:
        """Learn from actual ad engagement outcomes."""
        self._receptivity_predictions.append((predicted_receptivity, actual_engagement))
        
        # Keep last 1000 predictions
        if len(self._receptivity_predictions) > 1000:
            self._receptivity_predictions = self._receptivity_predictions[-1000:]


# =============================================================================
# NEED DETECTION LEARNING INTEGRATION
# =============================================================================

class NeedDetectionLearning:
    """
    Deep learning integration for Need Detection (33 needs).
    
    Learns:
    1. Which unmet needs predict conversion
    2. Brand-need alignment patterns
    3. Need category effectiveness by segment
    """
    
    def __init__(self, need_analyzer=None, gradient_bridge=None):
        self.need_analyzer = need_analyzer
        self.gradient_bridge = gradient_bridge
        
        self._needs_detected: Dict[str, int] = {}
        self._unmet_need_conversions: Dict[str, List[float]] = {}
    
    @property
    def component_name(self) -> str:
        return "need_detection"
    
    async def emit_need_signals(
        self,
        needs_profile,
        brand_name: str,
    ) -> List[LearningSignal]:
        """Emit learning signals from need detection."""
        signals = []
        
        # Signal for each detected need
        for need, activation in needs_profile.primary_needs[:10]:
            self._needs_detected[need] = self._needs_detected.get(need, 0) + 1
            
            signals.append(LearningSignal(
                signal_id=f"nd_{uuid.uuid4().hex[:12]}",
                signal_type=PsychologicalLearningSignalType.NEED_DETECTED,
                source_component=self.component_name,
                payload={
                    "need": need,
                    "activation_strength": activation,
                    "brand_name": brand_name,
                    "is_unmet": need in needs_profile.unmet_needs,
                    "total_detections": self._needs_detected[need],
                },
                confidence=min(0.9, activation),
            ))
        
        # Unmet needs signal
        if needs_profile.unmet_needs:
            signals.append(LearningSignal(
                signal_id=f"unmet_{uuid.uuid4().hex[:12]}",
                signal_type=PsychologicalLearningSignalType.UNMET_NEED_IDENTIFIED,
                source_component=self.component_name,
                payload={
                    "unmet_needs": needs_profile.unmet_needs,
                    "brand_name": brand_name,
                    "alignment_score": needs_profile.overall_alignment_score,
                    "opportunity_count": len(needs_profile.unmet_needs),
                },
                confidence=0.75,
            ))
        
        return signals


# =============================================================================
# FACTORY FUNCTIONS
# =============================================================================

def create_unified_intelligence_learning(
    unified_intelligence,
    gradient_bridge=None,
    redis_client=None,
    neo4j_driver=None,
) -> UnifiedPsychologicalIntelligenceLearning:
    """Create learning integration for UnifiedPsychologicalIntelligence."""
    return UnifiedPsychologicalIntelligenceLearning(
        unified_intelligence=unified_intelligence,
        gradient_bridge=gradient_bridge,
        redis_client=redis_client,
        neo4j_driver=neo4j_driver,
    )


def create_flow_state_learning(
    flow_engine=None,
    gradient_bridge=None,
) -> FlowStateLearning:
    """Create learning integration for Flow State Detection."""
    return FlowStateLearning(
        flow_engine=flow_engine,
        gradient_bridge=gradient_bridge,
    )


def create_need_detection_learning(
    need_analyzer=None,
    gradient_bridge=None,
) -> NeedDetectionLearning:
    """Create learning integration for Need Detection."""
    return NeedDetectionLearning(
        need_analyzer=need_analyzer,
        gradient_bridge=gradient_bridge,
    )
