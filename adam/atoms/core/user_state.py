# =============================================================================
# ADAM UserStateAtom
# Location: adam/atoms/core/user_state.py
# =============================================================================

"""
USER STATE ATOM

Assesses the user's current psychological state by fusing evidence from
multiple intelligence sources. This is the first atom in the DAG and provides
foundational state information for downstream atoms.

State dimensions assessed:
- Current arousal level (low/medium/high)
- Cognitive load (available capacity)
- Emotional valence (positive/negative)
- Engagement level (focused/distracted)
- Temporal pressure (relaxed/rushed)

Psychological Foundation:
- Yerkes-Dodson Law: Arousal-performance relationship
- Cognitive Load Theory: Limited processing capacity affects decision quality
- Affect-as-information: Emotional state biases judgments
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from adam.atoms.core.base import BaseAtom
from adam.atoms.models.evidence import (
    IntelligenceEvidence,
    MultiSourceEvidence,
    FusionResult,
    EvidenceStrength,
)
from adam.atoms.models.atom_io import AtomInput, AtomOutput
from adam.blackboard.models.zone2_reasoning import AtomType
from adam.graph_reasoning.models.intelligence_sources import (
    IntelligenceSourceType,
    ConfidenceSemantics,
)

logger = logging.getLogger(__name__)


# =============================================================================
# USER STATE MODELS
# =============================================================================

class ArousalLevel(BaseModel):
    """Current arousal level assessment."""
    
    level: float = Field(ge=0.0, le=1.0, description="0=calm, 1=highly aroused")
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    
    # Contributing signals
    behavioral_indicators: List[str] = Field(default_factory=list)
    physiological_signals: Dict[str, float] = Field(default_factory=dict)


class CognitiveLoad(BaseModel):
    """Current cognitive load assessment."""
    
    load: float = Field(ge=0.0, le=1.0, description="0=low load, 1=high load")
    available_capacity: float = Field(ge=0.0, le=1.0, default=0.5)
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    
    # Context
    multitasking_detected: bool = Field(default=False)
    task_complexity: str = Field(default="medium")


class EmotionalValence(BaseModel):
    """Current emotional valence assessment."""
    
    valence: float = Field(ge=-1.0, le=1.0, description="-1=negative, 1=positive")
    intensity: float = Field(ge=0.0, le=1.0, default=0.5)
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    
    # Detected emotions
    primary_emotion: Optional[str] = None
    secondary_emotions: List[str] = Field(default_factory=list)


class EngagementState(BaseModel):
    """Current engagement level assessment."""
    
    engagement: float = Field(ge=0.0, le=1.0, description="0=disengaged, 1=highly engaged")
    attention_quality: float = Field(ge=0.0, le=1.0, default=0.5)
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    
    # Behavioral indicators
    session_depth: int = Field(default=0, ge=0)
    interaction_rate: float = Field(ge=0.0, default=0.0)


class TemporalPressure(BaseModel):
    """Perceived time pressure assessment."""
    
    pressure: float = Field(ge=0.0, le=1.0, description="0=relaxed, 1=rushed")
    decision_urgency: float = Field(ge=0.0, le=1.0, default=0.5)
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    
    # Context
    time_of_day: Optional[str] = None
    day_of_week: Optional[str] = None


class UserStateAssessment(BaseModel):
    """Complete user state assessment."""
    
    user_id: str
    
    # State components
    arousal: ArousalLevel
    cognitive_load: CognitiveLoad
    emotional_valence: EmotionalValence
    engagement: EngagementState
    temporal_pressure: TemporalPressure
    
    # Overall state summary
    overall_receptivity: float = Field(
        ge=0.0, le=1.0,
        description="Overall receptivity to messaging"
    )
    recommended_message_complexity: str = Field(default="medium")
    
    # Timing
    assessed_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    
    # Confidence
    overall_confidence: float = Field(ge=0.0, le=1.0, default=0.5)


# =============================================================================
# USER STATE ATOM
# =============================================================================

class UserStateAtom(BaseAtom):
    """
    Atom for assessing current user psychological state.
    
    This is the first atom in the DAG and provides foundational
    state information used by downstream atoms.
    
    Intelligence Sources Used:
    - NONCONSCIOUS_SIGNALS: Behavioral patterns revealing hidden states
    - TEMPORAL_PATTERNS: Time-based state variations
    - COHORT_ORGANIZATION: Similar user state patterns
    - GRAPH_EMERGENCE: Historical state trajectories
    
    Psychological Foundation:
    - Yerkes-Dodson Law: Optimal arousal varies by task complexity
    - Cognitive Load Theory: Working memory limitations affect processing
    - Affect-as-information: Emotional states bias judgment
    """
    
    ATOM_TYPE = AtomType.USER_STATE
    ATOM_NAME = "user_state"
    TARGET_CONSTRUCT = "user_psychological_state"
    
    REQUIRED_SOURCES = [
        IntelligenceSourceType.NONCONSCIOUS_SIGNALS,
    ]
    
    OPTIONAL_SOURCES = [
        IntelligenceSourceType.TEMPORAL_PATTERNS,
        IntelligenceSourceType.COHORT_ORGANIZATION,
        IntelligenceSourceType.GRAPH_EMERGENCE,
    ]
    
    async def _query_construct_specific(
        self,
        source: IntelligenceSourceType,
        atom_input: AtomInput,
    ) -> Optional[IntelligenceEvidence]:
        """Query construct-specific sources for user state."""
        
        if source == IntelligenceSourceType.NONCONSCIOUS_SIGNALS:
            return await self._query_behavioral_state(atom_input)
        elif source == IntelligenceSourceType.TEMPORAL_PATTERNS:
            return await self._query_temporal_state(atom_input)
        elif source == IntelligenceSourceType.COHORT_ORGANIZATION:
            return await self._query_cohort_state(atom_input)
        elif source == IntelligenceSourceType.GRAPH_EMERGENCE:
            return await self._query_graph_state(atom_input)
        
        return None
    
    async def _query_behavioral_state(
        self,
        atom_input: AtomInput,
    ) -> Optional[IntelligenceEvidence]:
        """
        Query behavioral signals for current psychological state.
        
        Nonconscious signals reveal:
        - Arousal through interaction velocity
        - Engagement through session depth
        - Cognitive load through decision latency
        """
        user_intel = atom_input.request_context.user_intelligence
        
        # Initialize state values
        arousal = 0.5
        engagement = 0.5
        cognitive_load = 0.5
        confidence = 0.4
        indicators = []
        
        # Check real-time arousal signal
        if user_intel.current_arousal is not None:
            arousal = user_intel.current_arousal
            confidence = max(confidence, 0.6)
            indicators.append(f"arousal_signal:{arousal:.2f}")
        
        # Check session engagement
        if user_intel.session_engagement is not None:
            engagement = user_intel.session_engagement
            confidence = max(confidence, 0.55)
            indicators.append(f"session_engagement:{engagement:.2f}")
        
        # Infer cognitive load from cold start status
        if user_intel.is_cold_start:
            cognitive_load = 0.6  # Higher load for unfamiliar context
            indicators.append("cold_start_user")
        
        # Determine overall state
        if arousal > 0.7 and engagement > 0.6:
            state = "high_activation"
            reasoning = "High arousal with strong engagement - user is actively focused"
        elif arousal < 0.3 and engagement < 0.4:
            state = "low_activation"
            reasoning = "Low arousal and engagement - user may be passively browsing"
        else:
            state = "moderate_activation"
            reasoning = "Balanced arousal and engagement"
        
        return IntelligenceEvidence(
            source_type=IntelligenceSourceType.NONCONSCIOUS_SIGNALS,
            construct=self.TARGET_CONSTRUCT,
            assessment=state,
            assessment_value=arousal,
            confidence=confidence,
            confidence_semantics=ConfidenceSemantics.SIGNAL_STRENGTH,
            strength=EvidenceStrength.MODERATE if confidence > 0.5 else EvidenceStrength.WEAK,
            reasoning=reasoning,
            metadata={
                "arousal": arousal,
                "engagement": engagement,
                "cognitive_load": cognitive_load,
                "indicators": indicators,
            },
        )
    
    async def _query_temporal_state(
        self,
        atom_input: AtomInput,
    ) -> Optional[IntelligenceEvidence]:
        """
        Query temporal patterns for state variations.
        
        Time-based factors:
        - Time of day affects alertness and cognitive capacity
        - Session depth indicates decision stage
        - Day of week affects mindset (work vs leisure)
        """
        session = atom_input.request_context.session_context
        
        if not session:
            return None
        
        # Session depth indicates decision stage
        session_depth = session.decisions_in_session
        
        # Time-based assessment
        current_hour = datetime.now().hour
        
        # Morning (6-12): Higher cognitive capacity
        # Afternoon (12-17): Post-lunch dip, variable
        # Evening (17-22): Relaxed, more receptive to emotional appeals
        # Night (22-6): Low cognitive capacity
        
        if 6 <= current_hour < 12:
            time_state = "morning_focus"
            cognitive_capacity = 0.7
            arousal_modifier = 0.1
        elif 12 <= current_hour < 14:
            time_state = "post_lunch_dip"
            cognitive_capacity = 0.4
            arousal_modifier = -0.1
        elif 14 <= current_hour < 17:
            time_state = "afternoon_recovery"
            cognitive_capacity = 0.6
            arousal_modifier = 0.0
        elif 17 <= current_hour < 22:
            time_state = "evening_relaxed"
            cognitive_capacity = 0.5
            arousal_modifier = -0.05
        else:
            time_state = "late_night"
            cognitive_capacity = 0.3
            arousal_modifier = -0.15
        
        # Session depth affects urgency
        if session_depth <= 1:
            decision_stage = "exploring"
            temporal_pressure = 0.3
        elif session_depth >= 5:
            decision_stage = "deciding"
            temporal_pressure = 0.7
        else:
            decision_stage = "evaluating"
            temporal_pressure = 0.5
        
        return IntelligenceEvidence(
            source_type=IntelligenceSourceType.TEMPORAL_PATTERNS,
            construct=self.TARGET_CONSTRUCT,
            assessment=f"{time_state}_{decision_stage}",
            assessment_value=cognitive_capacity,
            confidence=0.55,
            confidence_semantics=ConfidenceSemantics.TEMPORAL_ADJUSTED,
            strength=EvidenceStrength.MODERATE,
            reasoning=f"Time: {time_state}, Decision stage: {decision_stage}",
            metadata={
                "cognitive_capacity": cognitive_capacity,
                "temporal_pressure": temporal_pressure,
                "arousal_modifier": arousal_modifier,
                "session_depth": session_depth,
                "hour": current_hour,
            },
        )
    
    async def _query_cohort_state(
        self,
        atom_input: AtomInput,
    ) -> Optional[IntelligenceEvidence]:
        """
        Query cohort patterns for typical states.
        
        Users in similar cohorts tend to have similar state patterns.
        """
        try:
            context = await self.bridge.query_executor.get_user_cohort(
                atom_input.user_id
            )
            
            if context and context.cohort:
                cohort = context.cohort
                
                # Extract typical state for this cohort
                typical_arousal = cohort.typical_states.get("arousal", 0.5) if hasattr(cohort, 'typical_states') else 0.5
                typical_engagement = cohort.typical_states.get("engagement", 0.5) if hasattr(cohort, 'typical_states') else 0.5
                
                return IntelligenceEvidence(
                    source_type=IntelligenceSourceType.COHORT_ORGANIZATION,
                    construct=self.TARGET_CONSTRUCT,
                    assessment=cohort.cohort_name,
                    assessment_value=cohort.cluster_purity,
                    confidence=min(0.7, cohort.cluster_purity),
                    confidence_semantics=ConfidenceSemantics.CLUSTER_PURITY,
                    strength=EvidenceStrength.MODERATE if cohort.cluster_size > 100 else EvidenceStrength.WEAK,
                    support_count=cohort.cluster_size,
                    reasoning=f"User in cohort '{cohort.cohort_name}' with typical state patterns",
                    metadata={
                        "typical_arousal": typical_arousal,
                        "typical_engagement": typical_engagement,
                    },
                )
        except Exception as e:
            logger.debug(f"Cohort state query failed: {e}")
        
        return None
    
    async def _query_graph_state(
        self,
        atom_input: AtomInput,
    ) -> Optional[IntelligenceEvidence]:
        """
        Query graph for historical state patterns.
        """
        user_intel = atom_input.request_context.user_intelligence
        
        if user_intel.state_history:
            history = user_intel.state_history
            
            # Calculate rolling averages
            avg_arousal = sum(s.arousal for s in history.states[-5:]) / min(5, len(history.states)) if history.states else 0.5
            avg_engagement = sum(s.engagement for s in history.states[-5:]) / min(5, len(history.states)) if history.states else 0.5
            
            return IntelligenceEvidence(
                source_type=IntelligenceSourceType.GRAPH_EMERGENCE,
                construct=self.TARGET_CONSTRUCT,
                assessment="historical_baseline",
                assessment_value=avg_arousal,
                confidence=0.6,
                confidence_semantics=ConfidenceSemantics.STATISTICAL,
                strength=self._trial_count_to_strength(len(history.states)),
                support_count=len(history.states),
                reasoning=f"Historical average from {len(history.states)} observations",
                metadata={
                    "avg_arousal": avg_arousal,
                    "avg_engagement": avg_engagement,
                    "observation_count": len(history.states),
                },
            )
        
        return None
    
    async def _build_output(
        self,
        atom_input: AtomInput,
        evidence: MultiSourceEvidence,
        fusion_result: FusionResult,
    ) -> AtomOutput:
        """Build user state output from fused evidence."""
        
        # Extract values from evidence and fusion
        arousal_value = 0.5
        cognitive_load_value = 0.5
        valence_value = 0.0
        engagement_value = 0.5
        temporal_pressure_value = 0.5
        
        # Aggregate from evidence sources
        for source_type, evi in evidence.evidence.items():
            if evi.metadata:
                if "arousal" in evi.metadata:
                    arousal_value = evi.metadata["arousal"]
                if "cognitive_load" in evi.metadata:
                    cognitive_load_value = evi.metadata["cognitive_load"]
                if "engagement" in evi.metadata:
                    engagement_value = evi.metadata["engagement"]
                if "temporal_pressure" in evi.metadata:
                    temporal_pressure_value = evi.metadata["temporal_pressure"]
                if "cognitive_capacity" in evi.metadata:
                    # Invert capacity to load
                    cognitive_load_value = 1.0 - evi.metadata["cognitive_capacity"]
        
        # Build state components
        arousal = ArousalLevel(
            level=arousal_value,
            confidence=fusion_result.confidence,
        )
        
        cognitive_load = CognitiveLoad(
            load=cognitive_load_value,
            available_capacity=1.0 - cognitive_load_value,
            confidence=fusion_result.confidence,
        )
        
        emotional_valence = EmotionalValence(
            valence=valence_value,
            intensity=abs(valence_value),
            confidence=fusion_result.confidence * 0.8,  # Less confident about valence
        )
        
        engagement = EngagementState(
            engagement=engagement_value,
            attention_quality=engagement_value * 0.9,
            confidence=fusion_result.confidence,
        )
        
        temporal_pressure = TemporalPressure(
            pressure=temporal_pressure_value,
            decision_urgency=temporal_pressure_value,
            confidence=fusion_result.confidence,
        )
        
        # Calculate overall receptivity
        # High receptivity: moderate arousal + low cognitive load + positive valence + high engagement
        receptivity = (
            (1.0 - abs(arousal_value - 0.5) * 2) * 0.2 +  # Moderate arousal best
            (1.0 - cognitive_load_value) * 0.3 +           # Lower load = more receptive
            ((valence_value + 1) / 2) * 0.2 +              # Positive = more receptive
            engagement_value * 0.3                          # Higher engagement = more receptive
        )
        
        # Determine message complexity
        if cognitive_load_value > 0.7:
            complexity = "simple"
        elif cognitive_load_value < 0.3 and engagement_value > 0.6:
            complexity = "complex"
        else:
            complexity = "medium"
        
        # Build assessment model
        assessment = UserStateAssessment(
            user_id=atom_input.user_id,
            arousal=arousal,
            cognitive_load=cognitive_load,
            emotional_valence=emotional_valence,
            engagement=engagement,
            temporal_pressure=temporal_pressure,
            overall_receptivity=min(1.0, max(0.0, receptivity)),
            recommended_message_complexity=complexity,
            overall_confidence=fusion_result.confidence,
        )
        
        # Map state to mechanism recommendations
        # High arousal → attention_dynamics, scarcity (capture attention)
        # Low cognitive load → identity_construction (can process abstract)
        # Positive valence → promotion mechanisms
        recommended_mechanisms = []
        mechanism_weights = {}
        
        if arousal_value > 0.6:
            recommended_mechanisms.append("attention_dynamics")
            recommended_mechanisms.append("scarcity")
            mechanism_weights["attention_dynamics"] = 0.7
            mechanism_weights["scarcity"] = 0.6
        
        if cognitive_load_value < 0.4:
            recommended_mechanisms.append("identity_construction")
            mechanism_weights["identity_construction"] = 0.65
        
        if valence_value > 0.2:
            recommended_mechanisms.append("gain_framing")
            mechanism_weights["gain_framing"] = 0.6
        elif valence_value < -0.2:
            recommended_mechanisms.append("loss_framing")
            mechanism_weights["loss_framing"] = 0.6
        
        if not recommended_mechanisms:
            recommended_mechanisms = ["automatic_evaluation"]
            mechanism_weights["automatic_evaluation"] = 0.5
        
        return AtomOutput(
            atom_id=self.config.atom_id,
            atom_type=self.ATOM_TYPE,
            request_id=atom_input.request_id,
            fusion_result=fusion_result,
            primary_assessment=fusion_result.assessment,
            assessment_value=receptivity,
            secondary_assessments={
                "arousal": arousal_value,
                "cognitive_load": cognitive_load_value,
                "valence": valence_value,
                "engagement": engagement_value,
                "temporal_pressure": temporal_pressure_value,
                "recommended_complexity": complexity,
                "state_assessment": assessment.model_dump(),
            },
            recommended_mechanisms=recommended_mechanisms,
            mechanism_weights=mechanism_weights,
            inferred_states={
                "arousal_level": arousal_value,
                "cognitive_load": cognitive_load_value,
                "emotional_valence": valence_value,
                "engagement_level": engagement_value,
                "overall_receptivity": receptivity,
            },
            overall_confidence=fusion_result.confidence,
            evidence_package=evidence,
            sources_queried=len(evidence.sources_queried),
            claude_used=fusion_result.claude_used,
        )
