# =============================================================================
# ADAM v3: Emergence Engine
# Location: src/v3/emergence/engine.py
# =============================================================================

"""
EMERGENCE ENGINE

Discovers novel psychological constructs from cross-source patterns.

Emergence Types:
- NOVEL_CONSTRUCT: New psychological construct not in literature
- CAUSAL_RELATIONSHIP: Previously unknown causal link
- MECHANISM_INTERACTION: Unexpected mechanism combination effect
- TEMPORAL_PATTERN: Time-based behavioral signature
- COHORT_DYNAMIC: Self-organizing user group behavior
- THEORY_BOUNDARY: Edge case revealing theory limits
- ANOMALY: Unexplained deviation requiring investigation

Promotion Criteria:
- 50+ validation attempts
- 65%+ success rate
- Cross-source confirmation
"""

from typing import List, Dict, Any, Optional, Tuple, Set
from datetime import datetime, timedelta
from enum import Enum
from pydantic import BaseModel, Field
import logging
import uuid
import numpy as np

logger = logging.getLogger(__name__)


class EmergenceType(str, Enum):
    """Types of emergent intelligence."""
    NOVEL_CONSTRUCT = "novel_construct"
    CAUSAL_RELATIONSHIP = "causal_relationship"
    MECHANISM_INTERACTION = "mechanism_interaction"
    TEMPORAL_PATTERN = "temporal_pattern"
    COHORT_DYNAMIC = "cohort_dynamic"
    THEORY_BOUNDARY = "theory_boundary"
    ANOMALY = "anomaly"


class EmergenceStatus(str, Enum):
    """Status of an emergent insight in the lifecycle."""
    DETECTED = "detected"           # Just discovered
    VALIDATING = "validating"       # Under validation
    PROMOTED = "promoted"           # Passed validation, integrated
    REJECTED = "rejected"           # Failed validation
    DEPRECATED = "deprecated"       # Replaced by better model


class CrossSourcePattern(BaseModel):
    """A pattern detected across multiple intelligence sources."""
    
    pattern_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:12])
    source_signatures: Dict[str, str] = Field(default_factory=dict)
    signal_correlation: float = Field(ge=-1.0, le=1.0, default=0.0)
    occurrence_count: int = Field(ge=1, default=1)
    affected_users: int = Field(ge=0, default=0)
    first_seen: datetime = Field(default_factory=datetime.utcnow)
    last_seen: datetime = Field(default_factory=datetime.utcnow)
    
    description: str = ""
    hypothesis: str = ""


class EmergentInsight(BaseModel):
    """A discovered emergent insight."""
    
    insight_id: str = Field(default_factory=lambda: f"ei_{uuid.uuid4().hex[:12]}")
    emergence_type: EmergenceType
    status: EmergenceStatus = EmergenceStatus.DETECTED
    
    # Pattern details
    cross_source_pattern: CrossSourcePattern
    sources_involved: List[str] = Field(default_factory=list)
    
    # Confidence and validation
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    validation_attempts: int = Field(ge=0, default=0)
    validation_successes: int = Field(ge=0, default=0)
    
    # Theoretical grounding
    theoretical_basis: Optional[str] = None
    extends_theory: Optional[str] = None
    contradicts_theory: Optional[str] = None
    
    # Practical impact
    predicted_lift: float = Field(ge=0.0, default=0.0)
    actual_lift: Optional[float] = None
    
    # Metadata
    discovered_at: datetime = Field(default_factory=datetime.utcnow)
    promoted_at: Optional[datetime] = None
    
    @property
    def validation_rate(self) -> float:
        """Validation success rate."""
        if self.validation_attempts == 0:
            return 0.0
        return self.validation_successes / self.validation_attempts
    
    @property
    def is_promotable(self) -> bool:
        """Whether insight meets promotion criteria."""
        return (
            self.validation_attempts >= 50 and
            self.validation_rate >= 0.65
        )


class PatternDetector:
    """Detects patterns across intelligence sources."""
    
    # Minimum correlation to consider as pattern
    CORRELATION_THRESHOLD = 0.3
    
    # Minimum occurrences to report
    OCCURRENCE_THRESHOLD = 5
    
    def __init__(self):
        self._pattern_cache: Dict[str, CrossSourcePattern] = {}
    
    def detect_correlation_pattern(
        self,
        source_a: str,
        signal_a: List[float],
        source_b: str,
        signal_b: List[float],
    ) -> Optional[CrossSourcePattern]:
        """Detect correlation between two source signals."""
        if len(signal_a) != len(signal_b) or len(signal_a) < 10:
            return None
        
        correlation = float(np.corrcoef(signal_a, signal_b)[0, 1])
        
        if abs(correlation) < self.CORRELATION_THRESHOLD:
            return None
        
        pattern_key = f"{source_a}:{source_b}"
        
        if pattern_key in self._pattern_cache:
            pattern = self._pattern_cache[pattern_key]
            pattern.occurrence_count += 1
            pattern.last_seen = datetime.utcnow()
            # Update correlation with exponential moving average
            pattern.signal_correlation = 0.9 * pattern.signal_correlation + 0.1 * correlation
        else:
            pattern = CrossSourcePattern(
                source_signatures={source_a: "signal_a", source_b: "signal_b"},
                signal_correlation=correlation,
                description=f"Correlation between {source_a} and {source_b}",
            )
            self._pattern_cache[pattern_key] = pattern
        
        if pattern.occurrence_count >= self.OCCURRENCE_THRESHOLD:
            return pattern
        
        return None
    
    def detect_co_occurrence_pattern(
        self,
        source_events: Dict[str, List[datetime]],
        window_seconds: float = 60.0
    ) -> Optional[CrossSourcePattern]:
        """Detect co-occurrence of events across sources."""
        sources = list(source_events.keys())
        if len(sources) < 2:
            return None
        
        co_occurrences = 0
        window = timedelta(seconds=window_seconds)
        
        # Check all pairs
        for i, source_a in enumerate(sources):
            for source_b in sources[i+1:]:
                events_a = source_events[source_a]
                events_b = source_events[source_b]
                
                for event_a in events_a:
                    for event_b in events_b:
                        if abs((event_a - event_b).total_seconds()) <= window_seconds:
                            co_occurrences += 1
        
        if co_occurrences < self.OCCURRENCE_THRESHOLD:
            return None
        
        return CrossSourcePattern(
            source_signatures={s: "event_time" for s in sources},
            occurrence_count=co_occurrences,
            description=f"Co-occurrence across {len(sources)} sources within {window_seconds}s",
        )


class EmergenceEngine:
    """
    Discovers psychological constructs absent from individual sources.
    
    The engine:
    1. Monitors cross-source patterns
    2. Detects emergent phenomena
    3. Formulates hypotheses
    4. Validates through experimentation
    5. Promotes successful discoveries
    """
    
    # Promotion thresholds
    MIN_VALIDATION_ATTEMPTS = 50
    MIN_VALIDATION_RATE = 0.65
    
    def __init__(self):
        self.pattern_detector = PatternDetector()
        
        # Storage
        self._insights: Dict[str, EmergentInsight] = {}
        self._promoted_insights: Dict[str, EmergentInsight] = {}
        
        # Source registry
        self._known_sources = {
            "claude_reasoning",
            "empirical_patterns",
            "nonconscious_signals",
            "graph_emergence",
            "bandit_posterior",
            "meta_routing",
            "mechanism_trajectory",
            "temporal_patterns",
            "cross_domain",
            "cohort_emergent",
        }
        
        # Statistics
        self._patterns_detected = 0
        self._insights_generated = 0
        self._insights_promoted = 0
    
    async def analyze_for_emergence(
        self,
        sources: Dict[str, Any],
        context: Dict[str, Any]
    ) -> List[EmergentInsight]:
        """
        Analyze multi-source data for emergent patterns.
        
        Args:
            sources: Dict mapping source_name -> source_output
            context: Request context
            
        Returns:
            List of detected emergent insights
        """
        insights = []
        
        # 1. Check for mechanism interactions
        mechanism_insights = await self._detect_mechanism_interactions(sources, context)
        insights.extend(mechanism_insights)
        
        # 2. Check for novel constructs
        construct_insights = await self._detect_novel_constructs(sources, context)
        insights.extend(construct_insights)
        
        # 3. Check for theory boundaries
        boundary_insights = await self._detect_theory_boundaries(sources, context)
        insights.extend(boundary_insights)
        
        # 4. Check for anomalies
        anomaly_insights = await self._detect_anomalies(sources, context)
        insights.extend(anomaly_insights)
        
        # Store new insights
        for insight in insights:
            self._insights[insight.insight_id] = insight
            self._insights_generated += 1
        
        return insights
    
    async def _detect_mechanism_interactions(
        self,
        sources: Dict[str, Any],
        context: Dict[str, Any]
    ) -> List[EmergentInsight]:
        """Detect unexpected mechanism combination effects."""
        insights = []
        
        # Get mechanism activations from sources
        mechanism_signals = {}
        
        for source_name, source_output in sources.items():
            if hasattr(source_output, 'mechanism_weights'):
                for mech, weight in source_output.mechanism_weights.items():
                    if mech not in mechanism_signals:
                        mechanism_signals[mech] = {}
                    mechanism_signals[mech][source_name] = weight
        
        # Look for mechanisms with divergent source weights
        for mech, source_weights in mechanism_signals.items():
            if len(source_weights) >= 3:
                weights = list(source_weights.values())
                variance = float(np.var(weights))
                
                # High variance suggests interesting interaction
                if variance > 0.1:
                    pattern = CrossSourcePattern(
                        source_signatures=source_weights,
                        signal_correlation=0.0,
                        description=f"Divergent weights for mechanism {mech}",
                        hypothesis=f"Sources disagree on {mech} effectiveness - possible interaction effect",
                    )
                    
                    insight = EmergentInsight(
                        emergence_type=EmergenceType.MECHANISM_INTERACTION,
                        cross_source_pattern=pattern,
                        sources_involved=list(source_weights.keys()),
                        confidence=min(0.8, variance * 5),
                    )
                    insights.append(insight)
        
        return insights
    
    async def _detect_novel_constructs(
        self,
        sources: Dict[str, Any],
        context: Dict[str, Any]
    ) -> List[EmergentInsight]:
        """Detect potential new psychological constructs."""
        insights = []
        
        # Look for consistent signals not explained by known constructs
        # This is a simplified heuristic - full implementation would use ML
        
        unexplained_signals = {}
        
        for source_name, source_output in sources.items():
            if hasattr(source_output, 'unexplained_variance'):
                if source_output.unexplained_variance > 0.3:
                    unexplained_signals[source_name] = source_output.unexplained_variance
        
        if len(unexplained_signals) >= 2:
            avg_unexplained = np.mean(list(unexplained_signals.values()))
            
            if avg_unexplained > 0.25:
                pattern = CrossSourcePattern(
                    source_signatures=unexplained_signals,
                    signal_correlation=avg_unexplained,
                    description="High unexplained variance across sources",
                    hypothesis="Potential novel construct not captured by current models",
                )
                
                insight = EmergentInsight(
                    emergence_type=EmergenceType.NOVEL_CONSTRUCT,
                    cross_source_pattern=pattern,
                    sources_involved=list(unexplained_signals.keys()),
                    confidence=0.4,  # Low initial confidence for novel constructs
                    theoretical_basis="Systematic unexplained variance suggests missing factor",
                )
                insights.append(insight)
        
        return insights
    
    async def _detect_theory_boundaries(
        self,
        sources: Dict[str, Any],
        context: Dict[str, Any]
    ) -> List[EmergentInsight]:
        """Detect edge cases revealing theory limits."""
        insights = []
        
        # Check for prediction disagreements between theory-based sources
        theory_sources = ["claude_reasoning", "graph_emergence"]
        empirical_sources = ["empirical_patterns", "bandit_posterior"]
        
        theory_predictions = {}
        empirical_predictions = {}
        
        for source_name, source_output in sources.items():
            if hasattr(source_output, 'prediction'):
                if source_name in theory_sources:
                    theory_predictions[source_name] = source_output.prediction
                elif source_name in empirical_sources:
                    empirical_predictions[source_name] = source_output.prediction
        
        # Check for theory-empirical disagreement
        if theory_predictions and empirical_predictions:
            theory_mean = np.mean(list(theory_predictions.values()))
            empirical_mean = np.mean(list(empirical_predictions.values()))
            
            disagreement = abs(theory_mean - empirical_mean)
            
            if disagreement > 0.3:
                pattern = CrossSourcePattern(
                    source_signatures={
                        "theory_mean": str(theory_mean),
                        "empirical_mean": str(empirical_mean),
                    },
                    signal_correlation=-disagreement,
                    description=f"Theory-empirical disagreement: {disagreement:.2f}",
                    hypothesis="Theory may not generalize to this context",
                )
                
                insight = EmergentInsight(
                    emergence_type=EmergenceType.THEORY_BOUNDARY,
                    cross_source_pattern=pattern,
                    sources_involved=list(theory_predictions.keys()) + list(empirical_predictions.keys()),
                    confidence=min(0.9, disagreement * 2),
                    contradicts_theory="Current psychological model",
                )
                insights.append(insight)
        
        return insights
    
    async def _detect_anomalies(
        self,
        sources: Dict[str, Any],
        context: Dict[str, Any]
    ) -> List[EmergentInsight]:
        """Detect unexplained deviations."""
        insights = []
        
        # Check for outlier predictions
        predictions = {}
        for source_name, source_output in sources.items():
            if hasattr(source_output, 'confidence'):
                predictions[source_name] = source_output.confidence
        
        if len(predictions) >= 3:
            values = list(predictions.values())
            mean_val = np.mean(values)
            std_val = np.std(values)
            
            if std_val > 0:
                for source_name, value in predictions.items():
                    z_score = abs(value - mean_val) / std_val
                    
                    if z_score > 2.5:  # Strong outlier
                        pattern = CrossSourcePattern(
                            source_signatures={source_name: str(value)},
                            signal_correlation=0.0,
                            description=f"Outlier from {source_name}: z-score={z_score:.2f}",
                            hypothesis=f"{source_name} detecting something others miss, or miscalibrated",
                        )
                        
                        insight = EmergentInsight(
                            emergence_type=EmergenceType.ANOMALY,
                            cross_source_pattern=pattern,
                            sources_involved=[source_name],
                            confidence=0.5,
                        )
                        insights.append(insight)
        
        return insights
    
    async def validate_insight(
        self,
        insight_id: str,
        outcome: bool,
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Validate an insight with outcome data.
        
        Args:
            insight_id: ID of insight to validate
            outcome: Whether insight prediction was correct
            context: Additional validation context
            
        Returns:
            True if insight is now promoted
        """
        if insight_id not in self._insights:
            return False
        
        insight = self._insights[insight_id]
        insight.validation_attempts += 1
        
        if outcome:
            insight.validation_successes += 1
        
        insight.status = EmergenceStatus.VALIDATING
        
        # Check for promotion
        if insight.is_promotable:
            await self._promote_insight(insight)
            return True
        
        # Check for rejection (too many failures)
        if (insight.validation_attempts >= 30 and 
            insight.validation_rate < 0.4):
            insight.status = EmergenceStatus.REJECTED
        
        return False
    
    async def _promote_insight(self, insight: EmergentInsight) -> None:
        """Promote validated insight to production."""
        insight.status = EmergenceStatus.PROMOTED
        insight.promoted_at = datetime.utcnow()
        
        self._promoted_insights[insight.insight_id] = insight
        self._insights_promoted += 1
        
        logger.info(
            f"Promoted insight {insight.insight_id}: "
            f"{insight.emergence_type.value} with {insight.validation_rate:.1%} success rate"
        )
    
    def get_promoted_insights(
        self,
        emergence_type: Optional[EmergenceType] = None
    ) -> List[EmergentInsight]:
        """Get all promoted insights, optionally filtered by type."""
        insights = list(self._promoted_insights.values())
        
        if emergence_type:
            insights = [i for i in insights if i.emergence_type == emergence_type]
        
        return insights
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get engine statistics."""
        return {
            "patterns_detected": self._patterns_detected,
            "insights_generated": self._insights_generated,
            "insights_promoted": self._insights_promoted,
            "insights_pending": sum(
                1 for i in self._insights.values()
                if i.status == EmergenceStatus.VALIDATING
            ),
            "promotion_rate": (
                self._insights_promoted / max(1, self._insights_generated)
            ),
        }


# Singleton instance
_engine: Optional[EmergenceEngine] = None


def get_emergence_engine() -> EmergenceEngine:
    """Get singleton Emergence Engine."""
    global _engine
    if _engine is None:
        _engine = EmergenceEngine()
    return _engine
