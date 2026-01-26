# ADAM Enhancement #20 v3 Supplement
## Advanced Atom of Thought Monitoring: Emergence, Causation & Dynamics

**Version**: 3.0 Supplement  
**Date**: January 2026  
**Status**: Extension of Enhancement #20 v2.0  
**Foundation**: Enhancement #04 v3 (Advanced Atom of Thought)  
**Dependency**: Enhancement #20 v2.0 COMPLETE

---

## PREFACE: WHY THIS SUPPLEMENT EXISTS

Enhancement #20 v2.0 provides comprehensive monitoring for the 10 intelligence sources and their fusion. However, Enhancement #04 v3 introduces **six new cognitive layers** that require dedicated monitoring:

| v3 Layer | What It Does | Why It Needs Monitoring |
|----------|--------------|------------------------|
| **Emergence Engine** | Discovers novel psychological constructs | Need to track discovery rate, validation success, false positive rate |
| **Causal Discovery** | Learns causal relationships | Causal graphs can become stale or invalid |
| **Temporal Dynamics** | Predicts psychological trajectories | Trajectory predictions can drift |
| **Mechanism Interactions** | Models mechanism synergies | Interaction coefficients can shift |
| **Session Narrative** | Tracks psychological story arcs | Narrative detection accuracy can degrade |
| **Meta-Cognitive** | Monitors reasoning quality | Calibration and explanation quality can drift |

This supplement extends #20 v2.0 with monitoring for these v3 components.

---

# SECTION A: EXTENDED DRIFT TAXONOMY

## A.1 Six Additional Drift Dimensions

The v3 architecture adds six new drift dimensions to the original eight:

```python
"""
ADAM Enhancement #20 v3 Supplement: Extended Drift Taxonomy
Six additional drift dimensions for the v3 cognitive layers.
"""

from enum import Enum
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
import numpy as np


class V3DriftDimension(str, Enum):
    """
    Six new drift dimensions introduced by AoT v3.
    These extend the original 8 dimensions from v2.0.
    """
    
    # Emergence Layer drift
    EMERGENCE_DRIFT = "emergence_drift"
    
    # Causal Discovery drift
    CAUSAL_DRIFT = "causal_drift"
    
    # Temporal Dynamics drift
    TRAJECTORY_DRIFT = "trajectory_drift"
    
    # Mechanism Interaction drift
    INTERACTION_DRIFT = "interaction_drift"
    
    # Session Narrative drift
    NARRATIVE_DRIFT = "narrative_drift"
    
    # Meta-Cognitive drift
    METACOGNITIVE_DRIFT = "metacognitive_drift"


V3_DRIFT_DESCRIPTIONS = {
    V3DriftDimension.EMERGENCE_DRIFT: """
        The Emergence Engine's ability to discover valid novel constructs degrades.
        
        Symptoms:
        - Discovery rate drops below baseline
        - Validation rate for emergent insights falls
        - False positive rate (invalid constructs promoted) increases
        - Time-to-promotion increases significantly
        
        Detection:
        - Track discovery_rate, validation_rate, false_positive_rate
        - Monitor construct promotion pipeline health
        - Compare emergent construct performance vs established constructs
        
        Impact: 
        - System stops generating proprietary psychological knowledge
        - Competitive moat erodes over time
        - Missing novel insights that could improve targeting
    """,
    
    V3DriftDimension.CAUSAL_DRIFT: """
        The Causal Discovery Layer's causal graph becomes stale or invalid.
        
        Symptoms:
        - Causal edge confidence scores drop
        - Counterfactual predictions become inaccurate
        - Intervention recommendations stop improving outcomes
        - New data violates existing causal structure
        
        Detection:
        - Track causal_edge_confidence, counterfactual_accuracy
        - A/B test intervention recommendations
        - Monitor causal graph stability metrics
        
        Impact:
        - System confuses correlation with causation
        - Intervention recommendations become ineffective
        - "What would change my mind" explanations become unreliable
    """,
    
    V3DriftDimension.TRAJECTORY_DRIFT: """
        Temporal Dynamics trajectory predictions become inaccurate.
        
        Symptoms:
        - Trajectory prediction MAE increases
        - Phase transition detection misses or false alarms
        - Momentum estimates become unreliable
        - State extrapolation errors grow
        
        Detection:
        - Track prediction_mae, phase_transition_f1
        - Monitor momentum estimation accuracy
        - Compare predicted vs actual state evolution
        
        Impact:
        - System can't anticipate psychological state changes
        - Intervention timing optimization fails
        - "Where user is going" insights become unreliable
    """,
    
    V3DriftDimension.INTERACTION_DRIFT: """
        Mechanism Interaction coefficients shift or become unreliable.
        
        Symptoms:
        - Interaction coefficient estimates destabilize
        - Mechanism combination recommendations underperform
        - Synergy/interference patterns change
        - Theoretical interactions no longer match empirical
        
        Detection:
        - Track coefficient_stability, recommendation_lift
        - Monitor empirical vs theoretical interaction alignment
        - A/B test mechanism combinations
        
        Impact:
        - Suboptimal mechanism combinations selected
        - Synergies missed, interferences not avoided
        - Mechanism selection becomes less effective
    """,
    
    V3DriftDimension.NARRATIVE_DRIFT: """
        Session Narrative detection accuracy degrades.
        
        Symptoms:
        - Act detection accuracy falls
        - Tension prediction errors increase
        - Intervention timing recommendations become suboptimal
        - Narrative-to-outcome correlation weakens
        
        Detection:
        - Track act_detection_f1, tension_prediction_mae
        - Monitor intervention_timing_lift
        - Compare narrative predictions to actual session outcomes
        
        Impact:
        - Intervention timing optimization fails
        - Session understanding becomes superficial
        - "Where in the journey" insights become unreliable
    """,
    
    V3DriftDimension.METACOGNITIVE_DRIFT: """
        Meta-Cognitive Layer quality degrades.
        
        Symptoms:
        - Calibration ECE increases (confidence/accuracy mismatch)
        - Reasoning traces become less explanatory
        - "What would change my mind" becomes less accurate
        - Uncertainty decomposition becomes unreliable
        
        Detection:
        - Track calibration_ece, explanation_quality_score
        - Monitor counterfactual trigger accuracy
        - Survey-based explanation satisfaction (if available)
        
        Impact:
        - Confidence scores become unreliable
        - System can't explain its reasoning
        - Can't identify what would change predictions
    """
}


# Response matrix for v3 drift dimensions
V3_DRIFT_RESPONSE_MATRIX: Dict[V3DriftDimension, Dict[str, str]] = {
    V3DriftDimension.EMERGENCE_DRIFT: {
        "warning": "Increase emergence detection thresholds, review recent discoveries",
        "critical": "Pause construct promotion, manual review of pipeline",
        "emergency": "Disable emergence engine, use only established constructs"
    },
    V3DriftDimension.CAUSAL_DRIFT: {
        "warning": "Flag causal edges for re-validation, increase evidence threshold",
        "critical": "Freeze causal graph updates, re-run discovery on recent data",
        "emergency": "Disable causal reasoning, fall back to correlational"
    },
    V3DriftDimension.TRAJECTORY_DRIFT: {
        "warning": "Widen prediction confidence intervals, increase observation requirements",
        "critical": "Shorten prediction horizons, use conservative momentum estimates",
        "emergency": "Disable trajectory prediction, use point-in-time only"
    },
    V3DriftDimension.INTERACTION_DRIFT: {
        "warning": "Increase interaction coefficient uncertainty, require more evidence",
        "critical": "Fall back to theoretical interactions only",
        "emergency": "Disable interaction modeling, use single mechanisms"
    },
    V3DriftDimension.NARRATIVE_DRIFT: {
        "warning": "Widen act boundaries, use conservative tension estimates",
        "critical": "Simplify narrative model, reduce act granularity",
        "emergency": "Disable narrative tracking, use simple session timing"
    },
    V3DriftDimension.METACOGNITIVE_DRIFT: {
        "warning": "Apply confidence calibration correction, flag explanations for review",
        "critical": "Enable conservative calibration mode, simplified explanations",
        "emergency": "Disable meta-cognitive features, basic predictions only"
    }
}
```

---

# SECTION B: EMERGENCE ENGINE MONITORING

## B.1 Emergence Health Models

```python
"""
ADAM Enhancement #20 v3: Emergence Engine Monitoring
Tracks the health and effectiveness of novel construct discovery.
"""

from __future__ import annotations
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
from enum import Enum
import numpy as np

from pydantic import BaseModel, Field


class EmergenceType(str, Enum):
    """Types of emergent intelligence (from #04 v3)."""
    NOVEL_CONSTRUCT = "novel_construct"
    CAUSAL_RELATIONSHIP = "causal_relationship"
    MECHANISM_INTERACTION = "mechanism_interaction"
    TEMPORAL_PATTERN = "temporal_pattern"
    COHORT_DYNAMIC = "cohort_dynamic"
    THEORY_BOUNDARY = "theory_boundary"
    ANOMALY = "anomaly"


class EmergentInsightStatus(str, Enum):
    """Lifecycle status of an emergent insight."""
    DISCOVERED = "discovered"        # Just found
    VALIDATING = "validating"        # Being tested
    PROMOTED = "promoted"            # Became a construct
    DEPRECATED = "deprecated"        # Found to be invalid
    ARCHIVED = "archived"            # No longer active


class EmergentInsightMetrics(BaseModel):
    """Metrics for a single emergent insight."""
    
    insight_id: str
    emergence_type: EmergenceType
    status: EmergentInsightStatus
    
    # Discovery metrics
    discovered_at: datetime
    cross_source_pattern: str
    initial_confidence: float = Field(ge=0.0, le=1.0)
    
    # Validation metrics
    validation_attempts: int = Field(ge=0)
    validation_successes: int = Field(ge=0)
    validation_rate: float = Field(ge=0.0, le=1.0)
    
    # Promotion metrics
    promoted_at: Optional[datetime] = None
    days_to_promotion: Optional[float] = None
    
    # Performance metrics (post-promotion)
    prediction_lift: Optional[float] = None
    usage_count: int = Field(ge=0, default=0)
    
    class Config:
        use_enum_values = True


class EmergenceEngineHealth(BaseModel):
    """
    Comprehensive health metrics for the Emergence Engine.
    """
    
    timestamp: datetime
    
    # Discovery metrics
    total_insights_discovered: int = Field(ge=0)
    insights_discovered_24h: int = Field(ge=0)
    insights_discovered_7d: int = Field(ge=0)
    discovery_rate_trend: str = Field(
        pattern="^(increasing|stable|decreasing)$"
    )
    
    # Per-type breakdown
    discoveries_by_type: Dict[str, int] = Field(default_factory=dict)
    
    # Validation metrics
    insights_in_validation: int = Field(ge=0)
    avg_validation_rate: float = Field(ge=0.0, le=1.0)
    validation_rate_trend: str = Field(
        pattern="^(increasing|stable|decreasing)$"
    )
    
    # Promotion metrics
    total_promoted: int = Field(ge=0)
    promoted_24h: int = Field(ge=0)
    promoted_7d: int = Field(ge=0)
    avg_days_to_promotion: float = Field(ge=0.0)
    promotion_rate: float = Field(ge=0.0, le=1.0)  # promoted / validated
    
    # Quality metrics
    false_positive_rate: float = Field(ge=0.0, le=1.0)  # deprecated / promoted
    avg_promoted_insight_lift: float = Field(default=0.0)  # Avg prediction improvement
    
    # Active construct health
    active_emergent_constructs: int = Field(ge=0)
    constructs_deprecated_7d: int = Field(ge=0)
    construct_churn_rate: float = Field(ge=0.0, le=1.0)
    
    # Overall health
    health_score: float = Field(ge=0.0, le=1.0)
    health_status: str = Field(pattern="^(healthy|degraded|unhealthy|critical)$")
    issues: List[str] = Field(default_factory=list)
    
    class Config:
        use_enum_values = True


class EmergenceEngineMonitor:
    """
    Monitors the Emergence Engine for drift and health issues.
    
    Key monitoring areas:
    1. Discovery rate and quality
    2. Validation pipeline health
    3. Promoted construct performance
    4. False positive / deprecation rate
    """
    
    # Health thresholds
    MIN_DISCOVERY_RATE_WEEKLY = 3      # At least 3 discoveries per week
    MIN_VALIDATION_RATE = 0.40         # 40% of discoveries should validate
    MAX_FALSE_POSITIVE_RATE = 0.20     # Max 20% of promoted insights deprecated
    MIN_PROMOTED_LIFT = 0.05           # Promoted insights should add 5% lift
    MAX_DAYS_TO_PROMOTION = 30         # Should promote within 30 days
    MAX_CONSTRUCT_CHURN = 0.10         # Max 10% construct churn per week
    
    def __init__(
        self,
        emergence_engine: 'EmergenceEngine',
        metrics_client: Optional[Any] = None,
        event_bus: Optional[Any] = None
    ):
        self.emergence_engine = emergence_engine
        self.metrics = metrics_client
        self.event_bus = event_bus
        
        # Historical tracking
        self._discovery_history: List[Tuple[datetime, EmergenceType]] = []
        self._validation_history: List[Tuple[datetime, str, bool]] = []
        self._promotion_history: List[Tuple[datetime, str, float]] = []
        self._deprecation_history: List[Tuple[datetime, str, str]] = []
        
        # Insight tracking
        self._active_insights: Dict[str, EmergentInsightMetrics] = {}
    
    async def record_discovery(
        self,
        insight_id: str,
        emergence_type: EmergenceType,
        cross_source_pattern: str,
        initial_confidence: float
    ) -> None:
        """Record a new emergent insight discovery."""
        
        now = datetime.utcnow()
        
        self._discovery_history.append((now, emergence_type))
        
        self._active_insights[insight_id] = EmergentInsightMetrics(
            insight_id=insight_id,
            emergence_type=emergence_type,
            status=EmergentInsightStatus.DISCOVERED,
            discovered_at=now,
            cross_source_pattern=cross_source_pattern,
            initial_confidence=initial_confidence,
            validation_attempts=0,
            validation_successes=0,
            validation_rate=0.0
        )
        
        # Emit metrics
        if self.metrics:
            await self.metrics.increment(
                "adam.emergence.discoveries_total",
                tags={"type": emergence_type.value}
            )
    
    async def record_validation_attempt(
        self,
        insight_id: str,
        success: bool
    ) -> None:
        """Record a validation attempt for an insight."""
        
        now = datetime.utcnow()
        
        self._validation_history.append((now, insight_id, success))
        
        if insight_id in self._active_insights:
            insight = self._active_insights[insight_id]
            insight.validation_attempts += 1
            if success:
                insight.validation_successes += 1
            insight.validation_rate = (
                insight.validation_successes / insight.validation_attempts
            )
            insight.status = EmergentInsightStatus.VALIDATING
        
        # Emit metrics
        if self.metrics:
            await self.metrics.increment(
                "adam.emergence.validations_total",
                tags={"success": str(success).lower()}
            )
    
    async def record_promotion(
        self,
        insight_id: str,
        prediction_lift: float
    ) -> None:
        """Record an insight being promoted to a construct."""
        
        now = datetime.utcnow()
        
        self._promotion_history.append((now, insight_id, prediction_lift))
        
        if insight_id in self._active_insights:
            insight = self._active_insights[insight_id]
            insight.status = EmergentInsightStatus.PROMOTED
            insight.promoted_at = now
            insight.days_to_promotion = (
                (now - insight.discovered_at).total_seconds() / 86400
            )
            insight.prediction_lift = prediction_lift
        
        # Emit metrics
        if self.metrics:
            await self.metrics.increment("adam.emergence.promotions_total")
            await self.metrics.gauge(
                "adam.emergence.promotion_lift",
                prediction_lift,
                tags={"insight_id": insight_id}
            )
    
    async def record_deprecation(
        self,
        insight_id: str,
        reason: str
    ) -> None:
        """Record an insight or construct being deprecated."""
        
        now = datetime.utcnow()
        
        self._deprecation_history.append((now, insight_id, reason))
        
        if insight_id in self._active_insights:
            insight = self._active_insights[insight_id]
            insight.status = EmergentInsightStatus.DEPRECATED
        
        # Emit metrics
        if self.metrics:
            await self.metrics.increment(
                "adam.emergence.deprecations_total",
                tags={"reason": reason}
            )
    
    async def get_emergence_health(self) -> EmergenceEngineHealth:
        """Get comprehensive Emergence Engine health metrics."""
        
        now = datetime.utcnow()
        
        # Calculate time windows
        cutoff_24h = now - timedelta(hours=24)
        cutoff_7d = now - timedelta(days=7)
        cutoff_30d = now - timedelta(days=30)
        
        # Discovery metrics
        discoveries_24h = sum(
            1 for ts, _ in self._discovery_history 
            if ts > cutoff_24h
        )
        discoveries_7d = sum(
            1 for ts, _ in self._discovery_history 
            if ts > cutoff_7d
        )
        
        # Discovery by type
        discoveries_by_type = defaultdict(int)
        for ts, etype in self._discovery_history:
            if ts > cutoff_7d:
                discoveries_by_type[etype.value] += 1
        
        # Discovery trend
        old_discoveries = sum(
            1 for ts, _ in self._discovery_history
            if cutoff_7d - timedelta(days=7) < ts <= cutoff_7d
        )
        if discoveries_7d > old_discoveries * 1.1:
            discovery_trend = "increasing"
        elif discoveries_7d < old_discoveries * 0.9:
            discovery_trend = "decreasing"
        else:
            discovery_trend = "stable"
        
        # Validation metrics
        insights_validating = sum(
            1 for i in self._active_insights.values()
            if i.status == EmergentInsightStatus.VALIDATING
        )
        
        validation_rates = [
            i.validation_rate for i in self._active_insights.values()
            if i.validation_attempts >= 10
        ]
        avg_validation_rate = np.mean(validation_rates) if validation_rates else 0.5
        
        # Promotion metrics
        promotions_24h = sum(
            1 for ts, _, _ in self._promotion_history
            if ts > cutoff_24h
        )
        promotions_7d = sum(
            1 for ts, _, _ in self._promotion_history
            if ts > cutoff_7d
        )
        
        days_to_promotion = [
            i.days_to_promotion for i in self._active_insights.values()
            if i.days_to_promotion is not None
        ]
        avg_days_to_promotion = np.mean(days_to_promotion) if days_to_promotion else 0.0
        
        # Promotion rate
        total_validated = sum(
            1 for i in self._active_insights.values()
            if i.validation_attempts >= 50
        )
        total_promoted = sum(
            1 for i in self._active_insights.values()
            if i.status == EmergentInsightStatus.PROMOTED
        )
        promotion_rate = total_promoted / max(total_validated, 1)
        
        # False positive rate
        deprecations_post_promotion = sum(
            1 for i in self._active_insights.values()
            if (i.status == EmergentInsightStatus.DEPRECATED and 
                i.promoted_at is not None)
        )
        false_positive_rate = deprecations_post_promotion / max(total_promoted, 1)
        
        # Lift metrics
        lifts = [
            i.prediction_lift for i in self._active_insights.values()
            if i.prediction_lift is not None
        ]
        avg_lift = np.mean(lifts) if lifts else 0.0
        
        # Active constructs
        active_constructs = sum(
            1 for i in self._active_insights.values()
            if i.status == EmergentInsightStatus.PROMOTED
        )
        
        deprecations_7d = sum(
            1 for ts, _, _ in self._deprecation_history
            if ts > cutoff_7d
        )
        construct_churn = deprecations_7d / max(active_constructs, 1)
        
        # Identify issues
        issues = []
        
        if discoveries_7d < self.MIN_DISCOVERY_RATE_WEEKLY:
            issues.append(f"Low discovery rate: {discoveries_7d}/week")
        
        if avg_validation_rate < self.MIN_VALIDATION_RATE:
            issues.append(f"Low validation rate: {avg_validation_rate:.1%}")
        
        if false_positive_rate > self.MAX_FALSE_POSITIVE_RATE:
            issues.append(f"High false positive rate: {false_positive_rate:.1%}")
        
        if avg_lift < self.MIN_PROMOTED_LIFT and total_promoted > 5:
            issues.append(f"Low promoted insight lift: {avg_lift:.1%}")
        
        if avg_days_to_promotion > self.MAX_DAYS_TO_PROMOTION and days_to_promotion:
            issues.append(f"Slow promotion pipeline: {avg_days_to_promotion:.1f} days")
        
        if construct_churn > self.MAX_CONSTRUCT_CHURN:
            issues.append(f"High construct churn: {construct_churn:.1%}/week")
        
        # Calculate health score
        health_components = [
            min(1.0, discoveries_7d / self.MIN_DISCOVERY_RATE_WEEKLY),
            min(1.0, avg_validation_rate / self.MIN_VALIDATION_RATE),
            1.0 - min(1.0, false_positive_rate / self.MAX_FALSE_POSITIVE_RATE),
            min(1.0, avg_lift / self.MIN_PROMOTED_LIFT) if total_promoted > 5 else 0.5,
            1.0 - min(1.0, construct_churn / self.MAX_CONSTRUCT_CHURN)
        ]
        health_score = np.mean(health_components)
        
        # Determine status
        if health_score >= 0.8 and len(issues) == 0:
            health_status = "healthy"
        elif health_score >= 0.6 and len(issues) <= 1:
            health_status = "degraded"
        elif health_score >= 0.4:
            health_status = "unhealthy"
        else:
            health_status = "critical"
        
        return EmergenceEngineHealth(
            timestamp=now,
            total_insights_discovered=len(self._active_insights),
            insights_discovered_24h=discoveries_24h,
            insights_discovered_7d=discoveries_7d,
            discovery_rate_trend=discovery_trend,
            discoveries_by_type=dict(discoveries_by_type),
            insights_in_validation=insights_validating,
            avg_validation_rate=avg_validation_rate,
            validation_rate_trend="stable",  # Simplified
            total_promoted=total_promoted,
            promoted_24h=promotions_24h,
            promoted_7d=promotions_7d,
            avg_days_to_promotion=avg_days_to_promotion,
            promotion_rate=promotion_rate,
            false_positive_rate=false_positive_rate,
            avg_promoted_insight_lift=avg_lift,
            active_emergent_constructs=active_constructs,
            constructs_deprecated_7d=deprecations_7d,
            construct_churn_rate=construct_churn,
            health_score=health_score,
            health_status=health_status,
            issues=issues
        )
    
    async def detect_emergence_drift(self) -> Optional['DriftAlert']:
        """Detect drift in the Emergence Engine."""
        
        health = await self.get_emergence_health()
        
        # Check for critical drift conditions
        drift_detected = False
        drift_severity = "warning"
        drift_details = {}
        
        if health.discovery_rate_trend == "decreasing" and health.insights_discovered_7d < self.MIN_DISCOVERY_RATE_WEEKLY:
            drift_detected = True
            drift_details["discovery_rate_drift"] = {
                "current": health.insights_discovered_7d,
                "threshold": self.MIN_DISCOVERY_RATE_WEEKLY
            }
        
        if health.false_positive_rate > self.MAX_FALSE_POSITIVE_RATE * 1.5:
            drift_detected = True
            drift_severity = "critical"
            drift_details["false_positive_drift"] = {
                "current": health.false_positive_rate,
                "threshold": self.MAX_FALSE_POSITIVE_RATE
            }
        
        if health.construct_churn_rate > self.MAX_CONSTRUCT_CHURN * 2:
            drift_detected = True
            drift_severity = "critical"
            drift_details["construct_churn_drift"] = {
                "current": health.construct_churn_rate,
                "threshold": self.MAX_CONSTRUCT_CHURN
            }
        
        if drift_detected:
            return {
                "drift_dimension": V3DriftDimension.EMERGENCE_DRIFT.value,
                "severity": drift_severity,
                "health_score": health.health_score,
                "details": drift_details,
                "recommended_action": V3_DRIFT_RESPONSE_MATRIX[
                    V3DriftDimension.EMERGENCE_DRIFT
                ][drift_severity]
            }
        
        return None
```

---

# SECTION C: CAUSAL DISCOVERY MONITORING

## C.1 Causal Graph Health Models

```python
"""
ADAM Enhancement #20 v3: Causal Discovery Monitoring
Tracks the health and validity of the causal graph and counterfactual reasoning.
"""

from __future__ import annotations
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass, field
from collections import defaultdict
from enum import Enum
import numpy as np

from pydantic import BaseModel, Field


class CausalRelationType(str, Enum):
    """Types of causal relationships (from #04 v3)."""
    DIRECT_CAUSE = "direct_cause"
    MEDIATED = "mediated"
    CONFOUNDED = "confounded"
    COLLIDER = "collider"
    BIDIRECTIONAL = "bidirectional"
    NO_RELATIONSHIP = "no_relationship"


class CausalEdgeHealth(BaseModel):
    """Health metrics for a single causal edge."""
    
    cause: str
    effect: str
    relation_type: CausalRelationType
    
    # Evidence strength
    temporal_evidence: float = Field(ge=0.0, le=1.0)
    statistical_evidence: float = Field(ge=0.0, le=1.0)
    interventional_evidence: float = Field(ge=0.0, le=1.0)
    mechanistic_evidence: float = Field(ge=0.0, le=1.0)
    
    # Overall edge metrics
    edge_strength: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    
    # Stability metrics
    confidence_7d_ago: Optional[float] = None
    confidence_trend: str = Field(
        pattern="^(increasing|stable|decreasing)$",
        default="stable"
    )
    
    # Validation metrics
    validation_tests: int = Field(ge=0, default=0)
    validation_successes: int = Field(ge=0, default=0)
    last_validated: Optional[datetime] = None
    
    # Health assessment
    is_stale: bool = False
    needs_revalidation: bool = False
    
    class Config:
        use_enum_values = True


class CounterfactualAccuracyMetrics(BaseModel):
    """Accuracy metrics for counterfactual reasoning."""
    
    timestamp: datetime
    
    # Overall accuracy
    total_counterfactuals_evaluated: int = Field(ge=0)
    accurate_predictions: int = Field(ge=0)
    accuracy_rate: float = Field(ge=0.0, le=1.0)
    
    # By intervention type
    accuracy_by_intervention: Dict[str, float] = Field(default_factory=dict)
    
    # Confidence calibration
    calibration_ece: float = Field(ge=0.0, le=1.0)  # Expected Calibration Error
    overconfident_rate: float = Field(ge=0.0, le=1.0)
    underconfident_rate: float = Field(ge=0.0, le=1.0)
    
    # Trend
    accuracy_trend: str = Field(
        pattern="^(improving|stable|degrading)$"
    )


class CausalGraphHealth(BaseModel):
    """
    Comprehensive health metrics for the Causal Discovery Layer.
    """
    
    timestamp: datetime
    
    # Graph structure metrics
    total_nodes: int = Field(ge=0)
    total_edges: int = Field(ge=0)
    graph_density: float = Field(ge=0.0, le=1.0)
    avg_path_length: float = Field(ge=0.0)
    
    # Edge health
    healthy_edges: int = Field(ge=0)
    degraded_edges: int = Field(ge=0)
    stale_edges: int = Field(ge=0)
    avg_edge_confidence: float = Field(ge=0.0, le=1.0)
    
    # Evidence quality
    edges_with_interventional_evidence: int = Field(ge=0)
    interventional_coverage: float = Field(ge=0.0, le=1.0)
    avg_evidence_strength: float = Field(ge=0.0, le=1.0)
    
    # Counterfactual reasoning health
    counterfactual_accuracy: float = Field(ge=0.0, le=1.0)
    counterfactual_calibration_ece: float = Field(ge=0.0, le=1.0)
    
    # Intervention recommendation health
    intervention_recommendations_24h: int = Field(ge=0)
    intervention_success_rate: float = Field(ge=0.0, le=1.0)
    
    # Staleness
    edges_needing_revalidation: int = Field(ge=0)
    avg_edge_age_days: float = Field(ge=0.0)
    
    # Overall health
    health_score: float = Field(ge=0.0, le=1.0)
    health_status: str = Field(pattern="^(healthy|degraded|unhealthy|critical)$")
    issues: List[str] = Field(default_factory=list)


class CausalDiscoveryMonitor:
    """
    Monitors the Causal Discovery Layer for health and drift.
    
    Key monitoring areas:
    1. Causal graph structure and edge validity
    2. Counterfactual reasoning accuracy
    3. Intervention recommendation effectiveness
    4. Evidence staleness and revalidation needs
    """
    
    # Health thresholds
    MIN_EDGE_CONFIDENCE = 0.50           # Minimum confidence for healthy edge
    MAX_STALE_EDGE_RATE = 0.20           # Max 20% stale edges
    MIN_INTERVENTIONAL_COVERAGE = 0.30   # At least 30% edges have interventional evidence
    MIN_COUNTERFACTUAL_ACCURACY = 0.60   # 60% counterfactual accuracy
    MAX_CALIBRATION_ECE = 0.15           # Max 15% calibration error
    MIN_INTERVENTION_SUCCESS = 0.55      # 55% intervention recommendation success
    MAX_EDGE_AGE_DAYS = 30               # Edges older than 30 days need revalidation
    
    def __init__(
        self,
        causal_engine: 'CausalDiscoveryEngine',
        metrics_client: Optional[Any] = None,
        event_bus: Optional[Any] = None
    ):
        self.causal_engine = causal_engine
        self.metrics = metrics_client
        self.event_bus = event_bus
        
        # Tracking
        self._counterfactual_evaluations: List[Tuple[datetime, float, bool]] = []
        self._intervention_outcomes: List[Tuple[datetime, str, bool]] = []
        self._edge_validations: Dict[Tuple[str, str], List[Tuple[datetime, bool]]] = defaultdict(list)
    
    async def record_counterfactual_evaluation(
        self,
        predicted_outcome: float,
        actual_outcome: float,
        confidence: float
    ) -> None:
        """Record a counterfactual prediction evaluation."""
        
        now = datetime.utcnow()
        
        # Determine if prediction was accurate (within 0.1 or correct direction)
        accurate = (
            abs(predicted_outcome - actual_outcome) < 0.1 or
            (predicted_outcome > 0.5) == (actual_outcome > 0.5)
        )
        
        self._counterfactual_evaluations.append((now, confidence, accurate))
        
        # Emit metrics
        if self.metrics:
            await self.metrics.increment(
                "adam.causal.counterfactual_evaluations_total",
                tags={"accurate": str(accurate).lower()}
            )
    
    async def record_intervention_outcome(
        self,
        intervention_type: str,
        success: bool
    ) -> None:
        """Record the outcome of an intervention recommendation."""
        
        now = datetime.utcnow()
        
        self._intervention_outcomes.append((now, intervention_type, success))
        
        # Emit metrics
        if self.metrics:
            await self.metrics.increment(
                "adam.causal.intervention_outcomes_total",
                tags={
                    "type": intervention_type,
                    "success": str(success).lower()
                }
            )
    
    async def record_edge_validation(
        self,
        cause: str,
        effect: str,
        validated: bool
    ) -> None:
        """Record an edge validation result."""
        
        now = datetime.utcnow()
        
        self._edge_validations[(cause, effect)].append((now, validated))
        
        # Emit metrics
        if self.metrics:
            await self.metrics.increment(
                "adam.causal.edge_validations_total",
                tags={"validated": str(validated).lower()}
            )
    
    def _assess_edge_health(
        self,
        edge: 'CausalEdge'
    ) -> CausalEdgeHealth:
        """Assess health of a single causal edge."""
        
        now = datetime.utcnow()
        
        # Get validation history
        validations = self._edge_validations.get((edge.cause, edge.effect), [])
        
        validation_tests = len(validations)
        validation_successes = sum(1 for _, v in validations if v)
        
        # Determine staleness
        if validations:
            last_validated = max(ts for ts, _ in validations)
            days_since_validation = (now - last_validated).days
            is_stale = days_since_validation > self.MAX_EDGE_AGE_DAYS
        else:
            last_validated = None
            is_stale = True  # Never validated = stale
        
        # Needs revalidation if stale or low confidence
        needs_revalidation = is_stale or edge.confidence < self.MIN_EDGE_CONFIDENCE
        
        return CausalEdgeHealth(
            cause=edge.cause,
            effect=edge.effect,
            relation_type=edge.relation_type,
            temporal_evidence=edge.temporal_evidence,
            statistical_evidence=edge.statistical_evidence,
            interventional_evidence=edge.interventional_evidence,
            mechanistic_evidence=edge.mechanistic_evidence,
            edge_strength=edge.edge_strength,
            confidence=edge.confidence,
            validation_tests=validation_tests,
            validation_successes=validation_successes,
            last_validated=last_validated,
            is_stale=is_stale,
            needs_revalidation=needs_revalidation
        )
    
    def _calculate_counterfactual_metrics(self) -> CounterfactualAccuracyMetrics:
        """Calculate counterfactual reasoning accuracy metrics."""
        
        now = datetime.utcnow()
        cutoff_7d = now - timedelta(days=7)
        
        # Filter to recent evaluations
        recent = [
            (ts, conf, acc) for ts, conf, acc in self._counterfactual_evaluations
            if ts > cutoff_7d
        ]
        
        if not recent:
            return CounterfactualAccuracyMetrics(
                timestamp=now,
                total_counterfactuals_evaluated=0,
                accurate_predictions=0,
                accuracy_rate=0.5,
                calibration_ece=0.1,
                overconfident_rate=0.0,
                underconfident_rate=0.0,
                accuracy_trend="stable"
            )
        
        # Calculate accuracy
        total = len(recent)
        accurate = sum(1 for _, _, acc in recent if acc)
        accuracy_rate = accurate / total
        
        # Calculate calibration
        bins = defaultdict(list)
        for _, conf, acc in recent:
            bin_idx = int(conf * 10)
            bins[bin_idx].append(1.0 if acc else 0.0)
        
        ece = 0.0
        for bin_idx, outcomes in bins.items():
            expected = bin_idx / 10 + 0.05  # Bin midpoint
            actual = np.mean(outcomes)
            ece += abs(expected - actual) * len(outcomes) / total
        
        # Over/under confident
        overconfident = sum(
            1 for _, conf, acc in recent if conf > 0.7 and not acc
        ) / max(total, 1)
        underconfident = sum(
            1 for _, conf, acc in recent if conf < 0.3 and acc
        ) / max(total, 1)
        
        # Trend (compare to previous week)
        cutoff_14d = now - timedelta(days=14)
        older = [
            (ts, conf, acc) for ts, conf, acc in self._counterfactual_evaluations
            if cutoff_14d < ts <= cutoff_7d
        ]
        
        if older:
            older_accuracy = sum(1 for _, _, acc in older if acc) / len(older)
            if accuracy_rate > older_accuracy + 0.05:
                trend = "improving"
            elif accuracy_rate < older_accuracy - 0.05:
                trend = "degrading"
            else:
                trend = "stable"
        else:
            trend = "stable"
        
        return CounterfactualAccuracyMetrics(
            timestamp=now,
            total_counterfactuals_evaluated=total,
            accurate_predictions=accurate,
            accuracy_rate=accuracy_rate,
            calibration_ece=ece,
            overconfident_rate=overconfident,
            underconfident_rate=underconfident,
            accuracy_trend=trend
        )
    
    async def get_causal_graph_health(self) -> CausalGraphHealth:
        """Get comprehensive Causal Graph health metrics."""
        
        now = datetime.utcnow()
        
        # Get graph from engine
        graph = self.causal_engine.causal_graph
        
        # Structure metrics
        total_nodes = len(graph.nodes)
        total_edges = len(graph.edges)
        max_edges = total_nodes * (total_nodes - 1) / 2 if total_nodes > 1 else 1
        density = total_edges / max_edges if max_edges > 0 else 0.0
        
        # Assess each edge
        edge_health_list = []
        for (cause, effect), edge in graph.edges.items():
            edge_health = self._assess_edge_health(edge)
            edge_health_list.append(edge_health)
        
        if edge_health_list:
            healthy_edges = sum(
                1 for eh in edge_health_list 
                if eh.confidence >= self.MIN_EDGE_CONFIDENCE and not eh.is_stale
            )
            degraded_edges = sum(
                1 for eh in edge_health_list
                if eh.confidence >= self.MIN_EDGE_CONFIDENCE * 0.7 and not eh.is_stale and 
                   eh.confidence < self.MIN_EDGE_CONFIDENCE
            )
            stale_edges = sum(1 for eh in edge_health_list if eh.is_stale)
            avg_confidence = np.mean([eh.confidence for eh in edge_health_list])
            
            # Evidence quality
            with_interventional = sum(
                1 for eh in edge_health_list if eh.interventional_evidence > 0.3
            )
            interventional_coverage = with_interventional / total_edges if total_edges > 0 else 0
            avg_evidence = np.mean([
                (eh.temporal_evidence + eh.statistical_evidence + 
                 eh.interventional_evidence + eh.mechanistic_evidence) / 4
                for eh in edge_health_list
            ])
            
            edges_needing_revalidation = sum(
                1 for eh in edge_health_list if eh.needs_revalidation
            )
        else:
            healthy_edges = 0
            degraded_edges = 0
            stale_edges = 0
            avg_confidence = 0.0
            with_interventional = 0
            interventional_coverage = 0.0
            avg_evidence = 0.0
            edges_needing_revalidation = 0
        
        # Counterfactual metrics
        cf_metrics = self._calculate_counterfactual_metrics()
        
        # Intervention outcomes
        cutoff_24h = now - timedelta(hours=24)
        recent_interventions = [
            (ts, t, s) for ts, t, s in self._intervention_outcomes
            if ts > cutoff_24h
        ]
        intervention_count = len(recent_interventions)
        intervention_success = (
            sum(1 for _, _, s in recent_interventions if s) / intervention_count
            if intervention_count > 0 else 0.5
        )
        
        # Identify issues
        issues = []
        
        stale_rate = stale_edges / max(total_edges, 1)
        if stale_rate > self.MAX_STALE_EDGE_RATE:
            issues.append(f"High stale edge rate: {stale_rate:.1%}")
        
        if interventional_coverage < self.MIN_INTERVENTIONAL_COVERAGE:
            issues.append(f"Low interventional coverage: {interventional_coverage:.1%}")
        
        if cf_metrics.accuracy_rate < self.MIN_COUNTERFACTUAL_ACCURACY:
            issues.append(f"Low counterfactual accuracy: {cf_metrics.accuracy_rate:.1%}")
        
        if cf_metrics.calibration_ece > self.MAX_CALIBRATION_ECE:
            issues.append(f"Poor counterfactual calibration: ECE={cf_metrics.calibration_ece:.2f}")
        
        if intervention_success < self.MIN_INTERVENTION_SUCCESS and intervention_count > 10:
            issues.append(f"Low intervention success: {intervention_success:.1%}")
        
        # Calculate health score
        health_components = [
            min(1.0, avg_confidence / self.MIN_EDGE_CONFIDENCE),
            1.0 - min(1.0, stale_rate / self.MAX_STALE_EDGE_RATE),
            min(1.0, interventional_coverage / self.MIN_INTERVENTIONAL_COVERAGE),
            min(1.0, cf_metrics.accuracy_rate / self.MIN_COUNTERFACTUAL_ACCURACY),
            1.0 - min(1.0, cf_metrics.calibration_ece / self.MAX_CALIBRATION_ECE)
        ]
        health_score = np.mean(health_components)
        
        # Determine status
        if health_score >= 0.8 and len(issues) == 0:
            health_status = "healthy"
        elif health_score >= 0.6 and len(issues) <= 1:
            health_status = "degraded"
        elif health_score >= 0.4:
            health_status = "unhealthy"
        else:
            health_status = "critical"
        
        return CausalGraphHealth(
            timestamp=now,
            total_nodes=total_nodes,
            total_edges=total_edges,
            graph_density=density,
            avg_path_length=2.5,  # Simplified
            healthy_edges=healthy_edges,
            degraded_edges=degraded_edges,
            stale_edges=stale_edges,
            avg_edge_confidence=avg_confidence,
            edges_with_interventional_evidence=with_interventional,
            interventional_coverage=interventional_coverage,
            avg_evidence_strength=avg_evidence,
            counterfactual_accuracy=cf_metrics.accuracy_rate,
            counterfactual_calibration_ece=cf_metrics.calibration_ece,
            intervention_recommendations_24h=intervention_count,
            intervention_success_rate=intervention_success,
            edges_needing_revalidation=edges_needing_revalidation,
            avg_edge_age_days=15.0,  # Simplified
            health_score=health_score,
            health_status=health_status,
            issues=issues
        )
```

---

# SECTION D: TEMPORAL DYNAMICS MONITORING

## D.1 Trajectory Prediction Health

```python
"""
ADAM Enhancement #20 v3: Temporal Dynamics Monitoring
Tracks trajectory prediction accuracy and phase transition detection.
"""

from __future__ import annotations
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
from enum import Enum
import numpy as np

from pydantic import BaseModel, Field


class TrajectoryPhase(str, Enum):
    """Phases of psychological state trajectory (from #04 v3)."""
    STABLE = "stable"
    RISING = "rising"
    FALLING = "falling"
    OSCILLATING = "oscillating"
    TRANSITION = "transition"


class TrajectoryPredictionMetrics(BaseModel):
    """Metrics for trajectory prediction accuracy."""
    
    timestamp: datetime
    construct: str
    
    # Prediction horizon
    horizon_seconds: float
    
    # Accuracy metrics
    predictions_evaluated: int = Field(ge=0)
    mae: float = Field(ge=0.0)  # Mean Absolute Error
    rmse: float = Field(ge=0.0)  # Root Mean Square Error
    direction_accuracy: float = Field(ge=0.0, le=1.0)  # Did we predict correct direction?
    
    # Confidence calibration
    confidence_correlation: float = Field(ge=-1.0, le=1.0)  # Confidence vs accuracy correlation
    
    # Trend
    accuracy_trend: str = Field(
        pattern="^(improving|stable|degrading)$"
    )


class PhaseTransitionDetectionMetrics(BaseModel):
    """Metrics for phase transition detection quality."""
    
    timestamp: datetime
    
    # Detection performance
    true_positives: int = Field(ge=0)
    false_positives: int = Field(ge=0)
    false_negatives: int = Field(ge=0)
    
    # Rates
    precision: float = Field(ge=0.0, le=1.0)
    recall: float = Field(ge=0.0, le=1.0)
    f1_score: float = Field(ge=0.0, le=1.0)
    
    # Timing accuracy
    avg_detection_lead_time_seconds: float  # How early we detect
    detection_time_std: float  # Consistency of lead time
    
    # By phase type
    f1_by_phase: Dict[str, float] = Field(default_factory=dict)


class TemporalDynamicsHealth(BaseModel):
    """
    Comprehensive health metrics for the Temporal Dynamics Engine.
    """
    
    timestamp: datetime
    
    # Active tracking
    active_trajectories: int = Field(ge=0)
    constructs_tracked: int = Field(ge=0)
    avg_trajectory_length: float = Field(ge=0.0)  # In observations
    
    # Trajectory prediction health
    avg_prediction_mae: float = Field(ge=0.0)
    avg_direction_accuracy: float = Field(ge=0.0, le=1.0)
    prediction_confidence_calibration: float = Field(ge=-1.0, le=1.0)
    
    # Per-construct breakdown
    construct_prediction_accuracy: Dict[str, float] = Field(default_factory=dict)
    
    # Momentum estimation health
    momentum_estimation_error: float = Field(ge=0.0)
    velocity_accuracy: float = Field(ge=0.0, le=1.0)
    
    # Phase transition detection
    phase_transition_f1: float = Field(ge=0.0, le=1.0)
    avg_transition_lead_time_seconds: float
    
    # Extrapolation health
    short_term_accuracy: float = Field(ge=0.0, le=1.0)  # 10 second horizon
    medium_term_accuracy: float = Field(ge=0.0, le=1.0)  # 30 second horizon
    long_term_accuracy: float = Field(ge=0.0, le=1.0)  # 60 second horizon
    
    # Overall health
    health_score: float = Field(ge=0.0, le=1.0)
    health_status: str = Field(pattern="^(healthy|degraded|unhealthy|critical)$")
    issues: List[str] = Field(default_factory=list)


class TemporalDynamicsMonitor:
    """
    Monitors the Temporal Dynamics Engine for accuracy and drift.
    
    Key monitoring areas:
    1. Trajectory prediction accuracy by horizon
    2. Phase transition detection quality
    3. Momentum estimation accuracy
    4. Per-construct performance
    """
    
    # Health thresholds
    MAX_PREDICTION_MAE = 0.15            # Maximum acceptable MAE
    MIN_DIRECTION_ACCURACY = 0.65        # Minimum direction prediction accuracy
    MIN_PHASE_F1 = 0.60                  # Minimum F1 for phase detection
    MIN_SHORT_TERM_ACCURACY = 0.75       # 10-second predictions
    MIN_MEDIUM_TERM_ACCURACY = 0.60      # 30-second predictions
    MIN_LONG_TERM_ACCURACY = 0.50        # 60-second predictions
    TARGET_LEAD_TIME_SECONDS = 5.0       # Target phase detection lead time
    
    def __init__(
        self,
        temporal_engine: 'TemporalDynamicsEngine',
        metrics_client: Optional[Any] = None
    ):
        self.temporal_engine = temporal_engine
        self.metrics = metrics_client
        
        # Tracking
        self._predictions: Dict[str, List[Tuple[datetime, float, float, float]]] = defaultdict(list)
        # (timestamp, predicted, actual, confidence)
        
        self._phase_detections: List[Tuple[datetime, TrajectoryPhase, bool, float]] = []
        # (timestamp, phase, was_correct, lead_time)
    
    async def record_trajectory_prediction(
        self,
        construct: str,
        horizon_seconds: float,
        predicted_value: float,
        actual_value: float,
        confidence: float
    ) -> None:
        """Record a trajectory prediction for evaluation."""
        
        now = datetime.utcnow()
        
        key = f"{construct}_{horizon_seconds}"
        self._predictions[key].append((now, predicted_value, actual_value, confidence))
        
        # Prune old data
        cutoff = now - timedelta(days=7)
        self._predictions[key] = [
            p for p in self._predictions[key] if p[0] > cutoff
        ]
        
        # Calculate error
        error = abs(predicted_value - actual_value)
        
        # Emit metrics
        if self.metrics:
            await self.metrics.gauge(
                "adam.temporal.prediction_error",
                error,
                tags={"construct": construct, "horizon": str(horizon_seconds)}
            )
    
    async def record_phase_transition_detection(
        self,
        detected_phase: TrajectoryPhase,
        actual_phase: TrajectoryPhase,
        lead_time_seconds: float
    ) -> None:
        """Record a phase transition detection for evaluation."""
        
        now = datetime.utcnow()
        
        was_correct = detected_phase == actual_phase
        
        self._phase_detections.append((
            now, detected_phase, was_correct, lead_time_seconds
        ))
        
        # Prune old data
        cutoff = now - timedelta(days=7)
        self._phase_detections = [
            p for p in self._phase_detections if p[0] > cutoff
        ]
        
        # Emit metrics
        if self.metrics:
            await self.metrics.increment(
                "adam.temporal.phase_detections_total",
                tags={
                    "phase": detected_phase.value,
                    "correct": str(was_correct).lower()
                }
            )
    
    def _calculate_prediction_metrics(
        self,
        construct: str,
        horizon: float
    ) -> TrajectoryPredictionMetrics:
        """Calculate prediction metrics for a construct/horizon combination."""
        
        now = datetime.utcnow()
        
        key = f"{construct}_{horizon}"
        predictions = self._predictions.get(key, [])
        
        if len(predictions) < 10:
            return TrajectoryPredictionMetrics(
                timestamp=now,
                construct=construct,
                horizon_seconds=horizon,
                predictions_evaluated=len(predictions),
                mae=0.15,  # Prior
                rmse=0.20,
                direction_accuracy=0.5,
                confidence_correlation=0.0,
                accuracy_trend="stable"
            )
        
        # Calculate metrics
        errors = [abs(p - a) for _, p, a, _ in predictions]
        mae = np.mean(errors)
        rmse = np.sqrt(np.mean([e**2 for e in errors]))
        
        # Direction accuracy (did we predict increase/decrease correctly?)
        direction_correct = sum(
            1 for i in range(1, len(predictions))
            if (predictions[i][1] > predictions[i-1][1]) == 
               (predictions[i][2] > predictions[i-1][2])
        )
        direction_accuracy = direction_correct / max(len(predictions) - 1, 1)
        
        # Confidence correlation
        confidences = [c for _, _, _, c in predictions]
        accuracies = [1.0 - min(1.0, e / 0.5) for e in errors]  # Convert error to accuracy
        if len(confidences) > 5 and np.std(confidences) > 0:
            confidence_correlation = np.corrcoef(confidences, accuracies)[0, 1]
        else:
            confidence_correlation = 0.0
        
        # Trend
        if len(predictions) >= 50:
            recent_mae = np.mean(errors[-25:])
            older_mae = np.mean(errors[:25])
            if recent_mae < older_mae * 0.9:
                trend = "improving"
            elif recent_mae > older_mae * 1.1:
                trend = "degrading"
            else:
                trend = "stable"
        else:
            trend = "stable"
        
        return TrajectoryPredictionMetrics(
            timestamp=now,
            construct=construct,
            horizon_seconds=horizon,
            predictions_evaluated=len(predictions),
            mae=mae,
            rmse=rmse,
            direction_accuracy=direction_accuracy,
            confidence_correlation=confidence_correlation,
            accuracy_trend=trend
        )
    
    def _calculate_phase_detection_metrics(self) -> PhaseTransitionDetectionMetrics:
        """Calculate phase transition detection metrics."""
        
        now = datetime.utcnow()
        
        if len(self._phase_detections) < 10:
            return PhaseTransitionDetectionMetrics(
                timestamp=now,
                true_positives=0,
                false_positives=0,
                false_negatives=0,
                precision=0.5,
                recall=0.5,
                f1_score=0.5,
                avg_detection_lead_time_seconds=0.0,
                detection_time_std=0.0
            )
        
        # Calculate metrics
        true_positives = sum(1 for _, _, correct, _ in self._phase_detections if correct)
        false_positives = sum(1 for _, _, correct, _ in self._phase_detections if not correct)
        # Simplified: assume FN = FP for now (would need ground truth comparison)
        false_negatives = false_positives
        
        precision = true_positives / max(true_positives + false_positives, 1)
        recall = true_positives / max(true_positives + false_negatives, 1)
        f1 = 2 * precision * recall / max(precision + recall, 0.001)
        
        # Lead time
        lead_times = [lt for _, _, correct, lt in self._phase_detections if correct]
        avg_lead_time = np.mean(lead_times) if lead_times else 0.0
        lead_time_std = np.std(lead_times) if len(lead_times) > 1 else 0.0
        
        # Per-phase F1 (simplified)
        f1_by_phase = {}
        for phase in TrajectoryPhase:
            phase_detections = [
                (c, lt) for _, p, c, lt in self._phase_detections 
                if p == phase
            ]
            if phase_detections:
                phase_correct = sum(1 for c, _ in phase_detections if c)
                f1_by_phase[phase.value] = phase_correct / len(phase_detections)
        
        return PhaseTransitionDetectionMetrics(
            timestamp=now,
            true_positives=true_positives,
            false_positives=false_positives,
            false_negatives=false_negatives,
            precision=precision,
            recall=recall,
            f1_score=f1,
            avg_detection_lead_time_seconds=avg_lead_time,
            detection_time_std=lead_time_std,
            f1_by_phase=f1_by_phase
        )
    
    async def get_temporal_dynamics_health(self) -> TemporalDynamicsHealth:
        """Get comprehensive Temporal Dynamics health metrics."""
        
        now = datetime.utcnow()
        
        # Active tracking from engine
        active_trajectories = len(self.temporal_engine.session_trajectories)
        constructs_tracked = len(set(
            construct for session in self.temporal_engine.session_trajectories.values()
            for construct in session.keys()
        ))
        
        # Calculate prediction metrics for different horizons
        horizons = [10.0, 30.0, 60.0]
        constructs = ["arousal", "engagement", "decision_conflict", "purchase_intent"]
        
        all_maes = []
        all_direction_accuracies = []
        construct_accuracy = {}
        
        for construct in constructs:
            construct_maes = []
            for horizon in horizons:
                metrics = self._calculate_prediction_metrics(construct, horizon)
                if metrics.predictions_evaluated > 0:
                    all_maes.append(metrics.mae)
                    all_direction_accuracies.append(metrics.direction_accuracy)
                    construct_maes.append(metrics.mae)
            
            if construct_maes:
                construct_accuracy[construct] = 1.0 - np.mean(construct_maes)
        
        avg_mae = np.mean(all_maes) if all_maes else 0.15
        avg_direction_accuracy = np.mean(all_direction_accuracies) if all_direction_accuracies else 0.5
        
        # Per-horizon accuracy
        short_term = self._calculate_prediction_metrics("engagement", 10.0)
        medium_term = self._calculate_prediction_metrics("engagement", 30.0)
        long_term = self._calculate_prediction_metrics("engagement", 60.0)
        
        # Phase detection
        phase_metrics = self._calculate_phase_detection_metrics()
        
        # Identify issues
        issues = []
        
        if avg_mae > self.MAX_PREDICTION_MAE:
            issues.append(f"High prediction MAE: {avg_mae:.3f}")
        
        if avg_direction_accuracy < self.MIN_DIRECTION_ACCURACY:
            issues.append(f"Low direction accuracy: {avg_direction_accuracy:.1%}")
        
        if phase_metrics.f1_score < self.MIN_PHASE_F1:
            issues.append(f"Low phase detection F1: {phase_metrics.f1_score:.2f}")
        
        if short_term.direction_accuracy < self.MIN_SHORT_TERM_ACCURACY:
            issues.append(f"Poor short-term predictions: {short_term.direction_accuracy:.1%}")
        
        # Calculate health score
        health_components = [
            1.0 - min(1.0, avg_mae / self.MAX_PREDICTION_MAE),
            min(1.0, avg_direction_accuracy / self.MIN_DIRECTION_ACCURACY),
            min(1.0, phase_metrics.f1_score / self.MIN_PHASE_F1),
            min(1.0, short_term.direction_accuracy / self.MIN_SHORT_TERM_ACCURACY)
        ]
        health_score = np.mean(health_components)
        
        # Determine status
        if health_score >= 0.8 and len(issues) == 0:
            health_status = "healthy"
        elif health_score >= 0.6 and len(issues) <= 1:
            health_status = "degraded"
        elif health_score >= 0.4:
            health_status = "unhealthy"
        else:
            health_status = "critical"
        
        return TemporalDynamicsHealth(
            timestamp=now,
            active_trajectories=active_trajectories,
            constructs_tracked=constructs_tracked,
            avg_trajectory_length=50.0,  # Simplified
            avg_prediction_mae=avg_mae,
            avg_direction_accuracy=avg_direction_accuracy,
            prediction_confidence_calibration=short_term.confidence_correlation,
            construct_prediction_accuracy=construct_accuracy,
            momentum_estimation_error=0.05,  # Simplified
            velocity_accuracy=0.7,  # Simplified
            phase_transition_f1=phase_metrics.f1_score,
            avg_transition_lead_time_seconds=phase_metrics.avg_detection_lead_time_seconds,
            short_term_accuracy=short_term.direction_accuracy,
            medium_term_accuracy=medium_term.direction_accuracy,
            long_term_accuracy=long_term.direction_accuracy,
            health_score=health_score,
            health_status=health_status,
            issues=issues
        )
```

---

# SECTION E: MECHANISM INTERACTION MONITORING

## E.1 Interaction Coefficient Health

```python
"""
ADAM Enhancement #20 v3: Mechanism Interaction Monitoring
Tracks interaction coefficient stability and combination effectiveness.
"""

from __future__ import annotations
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass
from collections import defaultdict
from enum import Enum
import numpy as np

from pydantic import BaseModel, Field


class InteractionType(str, Enum):
    """Types of mechanism interactions (from #04 v3)."""
    SYNERGISTIC = "synergistic"
    ADDITIVE = "additive"
    SUBADDITIVE = "subadditive"
    INTERFERING = "interfering"
    CONDITIONAL = "conditional"
    SATURATING = "saturating"


class InteractionCoefficientHealth(BaseModel):
    """Health metrics for a single interaction coefficient."""
    
    mechanisms: Tuple[str, str]
    interaction_type: InteractionType
    
    # Current estimate
    coefficient: float
    confidence: float = Field(ge=0.0, le=1.0)
    sample_size: int = Field(ge=0)
    
    # Stability metrics
    coefficient_7d_ago: Optional[float] = None
    coefficient_30d_ago: Optional[float] = None
    stability_score: float = Field(ge=0.0, le=1.0)  # Higher = more stable
    
    # Validation
    empirical_vs_theoretical_gap: Optional[float] = None  # If theoretical exists
    last_validated: Optional[datetime] = None
    
    # Health
    is_reliable: bool = True
    needs_more_data: bool = False
    
    class Config:
        use_enum_values = True


class MechanismCombinationMetrics(BaseModel):
    """Performance metrics for mechanism combinations."""
    
    mechanisms: List[str]
    
    # Usage
    usage_count_24h: int = Field(ge=0)
    usage_count_7d: int = Field(ge=0)
    
    # Performance
    conversion_rate: float = Field(ge=0.0, le=1.0)
    avg_lift_vs_single: float  # Lift compared to best single mechanism
    
    # Comparison to expectation
    expected_effect: float  # Based on interaction coefficients
    actual_effect: float
    prediction_error: float
    
    # Trend
    performance_trend: str = Field(
        pattern="^(improving|stable|degrading)$"
    )


class MechanismInteractionHealth(BaseModel):
    """
    Comprehensive health metrics for Mechanism Interaction Engine.
    """
    
    timestamp: datetime
    
    # Interaction coefficients tracked
    total_interactions_tracked: int = Field(ge=0)
    synergistic_interactions: int = Field(ge=0)
    interfering_interactions: int = Field(ge=0)
    
    # Stability
    stable_coefficients: int = Field(ge=0)
    unstable_coefficients: int = Field(ge=0)
    avg_coefficient_stability: float = Field(ge=0.0, le=1.0)
    
    # Prediction accuracy
    combination_prediction_accuracy: float = Field(ge=0.0, le=1.0)
    avg_prediction_error: float = Field(ge=0.0)
    
    # Recommendation effectiveness
    recommendation_usage_rate: float = Field(ge=0.0, le=1.0)
    recommendation_lift: float  # Lift when recommendations are followed
    
    # Coverage
    mechanism_pairs_with_data: int = Field(ge=0)
    total_possible_pairs: int = Field(ge=0)
    coverage_rate: float = Field(ge=0.0, le=1.0)
    
    # Overall health
    health_score: float = Field(ge=0.0, le=1.0)
    health_status: str = Field(pattern="^(healthy|degraded|unhealthy|critical)$")
    issues: List[str] = Field(default_factory=list)


class MechanismInteractionMonitor:
    """
    Monitors the Mechanism Interaction Engine for health and drift.
    
    Key monitoring areas:
    1. Interaction coefficient stability
    2. Combination prediction accuracy
    3. Recommendation effectiveness
    4. Empirical vs theoretical alignment
    """
    
    # Health thresholds
    MIN_COEFFICIENT_STABILITY = 0.70     # Coefficient should be 70% stable
    MAX_PREDICTION_ERROR = 0.15          # Max 15% prediction error
    MIN_RECOMMENDATION_LIFT = 0.05       # Recommendations should add 5% lift
    MIN_COVERAGE_RATE = 0.50             # At least 50% of pairs should have data
    MIN_SAMPLE_SIZE = 100                # Minimum samples for reliable coefficient
    MAX_EMPIRICAL_THEORETICAL_GAP = 0.20 # Max 20% gap from theory
    
    def __init__(
        self,
        interaction_engine: 'MechanismInteractionEngine',
        metrics_client: Optional[Any] = None
    ):
        self.interaction_engine = interaction_engine
        self.metrics = metrics_client
        
        # Coefficient history
        self._coefficient_history: Dict[Tuple[str, str], List[Tuple[datetime, float]]] = defaultdict(list)
        
        # Combination outcomes
        self._combination_outcomes: List[Tuple[datetime, Tuple[str, ...], float, float]] = []
        # (timestamp, mechanisms, expected_effect, actual_effect)
        
        # Recommendation tracking
        self._recommendations: List[Tuple[datetime, List[str], bool, float]] = []
        # (timestamp, mechanisms, was_followed, outcome)
    
    async def record_coefficient_observation(
        self,
        mechanism_a: str,
        mechanism_b: str,
        coefficient: float
    ) -> None:
        """Record an interaction coefficient observation."""
        
        now = datetime.utcnow()
        
        key = tuple(sorted([mechanism_a, mechanism_b]))
        self._coefficient_history[key].append((now, coefficient))
        
        # Prune old data
        cutoff = now - timedelta(days=90)
        self._coefficient_history[key] = [
            c for c in self._coefficient_history[key] if c[0] > cutoff
        ]
        
        # Emit metrics
        if self.metrics:
            await self.metrics.gauge(
                "adam.interaction.coefficient",
                coefficient,
                tags={"mechanism_a": mechanism_a, "mechanism_b": mechanism_b}
            )
    
    async def record_combination_outcome(
        self,
        mechanisms: Tuple[str, ...],
        expected_effect: float,
        actual_effect: float
    ) -> None:
        """Record the outcome of a mechanism combination."""
        
        now = datetime.utcnow()
        
        self._combination_outcomes.append((now, mechanisms, expected_effect, actual_effect))
        
        # Prune
        cutoff = now - timedelta(days=30)
        self._combination_outcomes = [
            c for c in self._combination_outcomes if c[0] > cutoff
        ]
        
        # Emit metrics
        if self.metrics:
            error = abs(expected_effect - actual_effect)
            await self.metrics.gauge(
                "adam.interaction.prediction_error",
                error,
                tags={"mechanism_count": str(len(mechanisms))}
            )
    
    async def record_recommendation_outcome(
        self,
        recommended_mechanisms: List[str],
        was_followed: bool,
        outcome_lift: float
    ) -> None:
        """Record whether a recommendation was followed and its outcome."""
        
        now = datetime.utcnow()
        
        self._recommendations.append((now, recommended_mechanisms, was_followed, outcome_lift))
        
        # Prune
        cutoff = now - timedelta(days=30)
        self._recommendations = [
            r for r in self._recommendations if r[0] > cutoff
        ]
        
        # Emit metrics
        if self.metrics:
            await self.metrics.increment(
                "adam.interaction.recommendations_total",
                tags={"followed": str(was_followed).lower()}
            )
    
    def _assess_coefficient_health(
        self,
        mechanism_pair: Tuple[str, str]
    ) -> InteractionCoefficientHealth:
        """Assess health of a single interaction coefficient."""
        
        now = datetime.utcnow()
        
        history = self._coefficient_history.get(mechanism_pair, [])
        
        if len(history) < 5:
            return InteractionCoefficientHealth(
                mechanisms=mechanism_pair,
                interaction_type=InteractionType.ADDITIVE,
                coefficient=1.0,
                confidence=0.3,
                sample_size=len(history),
                stability_score=0.5,
                is_reliable=False,
                needs_more_data=True
            )
        
        # Current coefficient
        recent = [c for ts, c in history if ts > now - timedelta(days=7)]
        current = np.mean([c for _, c in recent]) if recent else history[-1][1]
        
        # Historical coefficients
        old_7d = [c for ts, c in history if now - timedelta(days=14) < ts <= now - timedelta(days=7)]
        coef_7d_ago = np.mean([c for _, c in old_7d]) if old_7d else None
        
        old_30d = [c for ts, c in history if now - timedelta(days=60) < ts <= now - timedelta(days=30)]
        coef_30d_ago = np.mean([c for _, c in old_30d]) if old_30d else None
        
        # Stability (coefficient of variation)
        all_coefs = [c for _, c in history]
        if len(all_coefs) > 1 and np.mean(all_coefs) != 0:
            cv = np.std(all_coefs) / abs(np.mean(all_coefs))
            stability = max(0, 1.0 - cv)  # Lower CV = higher stability
        else:
            stability = 0.5
        
        # Determine interaction type
        if current > 1.1:
            interaction_type = InteractionType.SYNERGISTIC
        elif current > 0.9:
            interaction_type = InteractionType.ADDITIVE
        elif current > 0.5:
            interaction_type = InteractionType.SUBADDITIVE
        else:
            interaction_type = InteractionType.INTERFERING
        
        # Check theoretical
        theoretical = self.interaction_engine.THEORETICAL_INTERACTIONS.get(mechanism_pair)
        if theoretical:
            theoretical_coef = theoretical.get("coefficient", 1.0)
            gap = abs(current - theoretical_coef)
        else:
            gap = None
        
        # Reliability
        is_reliable = len(history) >= self.MIN_SAMPLE_SIZE and stability >= self.MIN_COEFFICIENT_STABILITY
        
        return InteractionCoefficientHealth(
            mechanisms=mechanism_pair,
            interaction_type=interaction_type,
            coefficient=current,
            confidence=min(1.0, len(history) / self.MIN_SAMPLE_SIZE),
            sample_size=len(history),
            coefficient_7d_ago=coef_7d_ago,
            coefficient_30d_ago=coef_30d_ago,
            stability_score=stability,
            empirical_vs_theoretical_gap=gap,
            is_reliable=is_reliable,
            needs_more_data=len(history) < self.MIN_SAMPLE_SIZE
        )
    
    async def get_mechanism_interaction_health(self) -> MechanismInteractionHealth:
        """Get comprehensive Mechanism Interaction health metrics."""
        
        now = datetime.utcnow()
        
        # Get all tracked interactions from engine
        interactions = self.interaction_engine.interactions
        
        total_tracked = len(interactions)
        
        # Assess each interaction
        coefficient_health = {
            pair: self._assess_coefficient_health(pair)
            for pair in self._coefficient_history.keys()
        }
        
        synergistic = sum(
            1 for h in coefficient_health.values()
            if h.interaction_type == InteractionType.SYNERGISTIC
        )
        interfering = sum(
            1 for h in coefficient_health.values()
            if h.interaction_type == InteractionType.INTERFERING
        )
        
        stable = sum(1 for h in coefficient_health.values() if h.stability_score >= self.MIN_COEFFICIENT_STABILITY)
        unstable = sum(1 for h in coefficient_health.values() if h.stability_score < self.MIN_COEFFICIENT_STABILITY)
        
        avg_stability = np.mean([h.stability_score for h in coefficient_health.values()]) if coefficient_health else 0.5
        
        # Prediction accuracy
        if self._combination_outcomes:
            errors = [abs(exp - act) for _, _, exp, act in self._combination_outcomes]
            avg_error = np.mean(errors)
            accuracy = 1.0 - min(1.0, avg_error / 0.5)
        else:
            avg_error = 0.15
            accuracy = 0.5
        
        # Recommendation effectiveness
        cutoff_7d = now - timedelta(days=7)
        recent_recs = [r for r in self._recommendations if r[0] > cutoff_7d]
        
        if recent_recs:
            followed = [r for r in recent_recs if r[2]]
            not_followed = [r for r in recent_recs if not r[2]]
            
            usage_rate = len(followed) / len(recent_recs)
            
            if followed and not_followed:
                followed_lift = np.mean([r[3] for r in followed])
                not_followed_lift = np.mean([r[3] for r in not_followed])
                rec_lift = followed_lift - not_followed_lift
            else:
                rec_lift = 0.05  # Default
        else:
            usage_rate = 0.5
            rec_lift = 0.05
        
        # Coverage
        mechanisms = ["loss_aversion", "scarcity", "social_proof", "authority", "reciprocity"]
        total_pairs = len(mechanisms) * (len(mechanisms) - 1) // 2
        pairs_with_data = len([h for h in coefficient_health.values() if h.sample_size >= 10])
        coverage = pairs_with_data / max(total_pairs, 1)
        
        # Identify issues
        issues = []
        
        if avg_stability < self.MIN_COEFFICIENT_STABILITY:
            issues.append(f"Low coefficient stability: {avg_stability:.1%}")
        
        if avg_error > self.MAX_PREDICTION_ERROR:
            issues.append(f"High prediction error: {avg_error:.1%}")
        
        if rec_lift < self.MIN_RECOMMENDATION_LIFT and len(recent_recs) > 20:
            issues.append(f"Low recommendation lift: {rec_lift:.1%}")
        
        if coverage < self.MIN_COVERAGE_RATE:
            issues.append(f"Low coverage: {coverage:.1%}")
        
        # Calculate health score
        health_components = [
            min(1.0, avg_stability / self.MIN_COEFFICIENT_STABILITY),
            1.0 - min(1.0, avg_error / self.MAX_PREDICTION_ERROR),
            min(1.0, coverage / self.MIN_COVERAGE_RATE),
            min(1.0, rec_lift / self.MIN_RECOMMENDATION_LIFT) if rec_lift > 0 else 0.5
        ]
        health_score = np.mean(health_components)
        
        # Determine status
        if health_score >= 0.8 and len(issues) == 0:
            health_status = "healthy"
        elif health_score >= 0.6 and len(issues) <= 1:
            health_status = "degraded"
        elif health_score >= 0.4:
            health_status = "unhealthy"
        else:
            health_status = "critical"
        
        return MechanismInteractionHealth(
            timestamp=now,
            total_interactions_tracked=total_tracked,
            synergistic_interactions=synergistic,
            interfering_interactions=interfering,
            stable_coefficients=stable,
            unstable_coefficients=unstable,
            avg_coefficient_stability=avg_stability,
            combination_prediction_accuracy=accuracy,
            avg_prediction_error=avg_error,
            recommendation_usage_rate=usage_rate,
            recommendation_lift=rec_lift,
            mechanism_pairs_with_data=pairs_with_data,
            total_possible_pairs=total_pairs,
            coverage_rate=coverage,
            health_score=health_score,
            health_status=health_status,
            issues=issues
        )
```

---

# SECTION F: SESSION NARRATIVE MONITORING

## F.1 Narrative Detection Health

```python
"""
ADAM Enhancement #20 v3: Session Narrative Monitoring
Tracks narrative detection accuracy and intervention timing effectiveness.
"""

from __future__ import annotations
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from collections import defaultdict
from enum import Enum
import numpy as np

from pydantic import BaseModel, Field


class NarrativeAct(str, Enum):
    """Acts in the session narrative (from #04 v3)."""
    ARRIVAL = "arrival"
    EXPLORATION = "exploration"
    CONSIDERATION = "consideration"
    CONFLICT = "conflict"
    RESOLUTION = "resolution"
    DECISION = "decision"
    POST_DECISION = "post_decision"


class NarrativeTension(str, Enum):
    """Tension states (from #04 v3)."""
    LOW = "low"
    RISING = "rising"
    PEAK = "peak"
    FALLING = "falling"
    RESOLVED = "resolved"


class ActDetectionMetrics(BaseModel):
    """Metrics for narrative act detection."""
    
    timestamp: datetime
    
    # Detection performance
    total_sessions_evaluated: int = Field(ge=0)
    correct_act_detections: int = Field(ge=0)
    accuracy: float = Field(ge=0.0, le=1.0)
    
    # Per-act breakdown
    precision_by_act: Dict[str, float] = Field(default_factory=dict)
    recall_by_act: Dict[str, float] = Field(default_factory=dict)
    f1_by_act: Dict[str, float] = Field(default_factory=dict)
    
    # Transition detection
    transition_detection_accuracy: float = Field(ge=0.0, le=1.0)
    avg_transition_detection_delay_seconds: float


class TensionPredictionMetrics(BaseModel):
    """Metrics for tension prediction accuracy."""
    
    timestamp: datetime
    
    # Tension level prediction
    tension_mae: float = Field(ge=0.0)
    tension_direction_accuracy: float = Field(ge=0.0, le=1.0)
    
    # Trajectory prediction
    trajectory_accuracy: float = Field(ge=0.0, le=1.0)
    peak_detection_f1: float = Field(ge=0.0, le=1.0)


class InterventionTimingMetrics(BaseModel):
    """Metrics for intervention timing effectiveness."""
    
    timestamp: datetime
    
    # Timing recommendations
    recommendations_made: int = Field(ge=0)
    recommendations_followed: int = Field(ge=0)
    
    # Effectiveness
    optimal_timing_lift: float  # Lift when optimal timing followed
    suboptimal_timing_penalty: float  # Penalty when timing ignored
    
    # Urgency calibration
    urgency_calibration_ece: float = Field(ge=0.0, le=1.0)


class SessionNarrativeHealth(BaseModel):
    """
    Comprehensive health metrics for Session Narrative Engine.
    """
    
    timestamp: datetime
    
    # Active tracking
    active_sessions: int = Field(ge=0)
    sessions_with_narrative: int = Field(ge=0)
    
    # Act detection
    act_detection_accuracy: float = Field(ge=0.0, le=1.0)
    avg_act_f1: float = Field(ge=0.0, le=1.0)
    transition_detection_accuracy: float = Field(ge=0.0, le=1.0)
    
    # Tension prediction
    tension_mae: float = Field(ge=0.0)
    tension_trajectory_accuracy: float = Field(ge=0.0, le=1.0)
    
    # Resolution prediction
    resolution_prediction_accuracy: float = Field(ge=0.0, le=1.0)
    resolution_confidence_calibration: float = Field(ge=0.0, le=1.0)
    
    # Intervention timing
    intervention_timing_lift: float
    timing_recommendation_accuracy: float = Field(ge=0.0, le=1.0)
    urgency_calibration_ece: float = Field(ge=0.0, le=1.0)
    
    # Narrative-to-outcome correlation
    narrative_outcome_correlation: float = Field(ge=-1.0, le=1.0)
    
    # Overall health
    health_score: float = Field(ge=0.0, le=1.0)
    health_status: str = Field(pattern="^(healthy|degraded|unhealthy|critical)$")
    issues: List[str] = Field(default_factory=list)


class SessionNarrativeMonitor:
    """
    Monitors the Session Narrative Engine for health and drift.
    
    Key monitoring areas:
    1. Act detection accuracy
    2. Tension prediction quality
    3. Resolution prediction accuracy
    4. Intervention timing effectiveness
    """
    
    # Health thresholds
    MIN_ACT_ACCURACY = 0.70              # 70% act detection accuracy
    MIN_ACT_F1 = 0.65                    # 65% F1 per act
    MAX_TENSION_MAE = 0.15               # Max 0.15 tension prediction error
    MIN_RESOLUTION_ACCURACY = 0.65       # 65% resolution prediction accuracy
    MIN_TIMING_LIFT = 0.10               # 10% lift from optimal timing
    MAX_URGENCY_ECE = 0.15               # Max 15% urgency calibration error
    
    def __init__(
        self,
        narrative_engine: 'SessionNarrativeEngine',
        metrics_client: Optional[Any] = None
    ):
        self.narrative_engine = narrative_engine
        self.metrics = metrics_client
        
        # Act detection tracking
        self._act_detections: List[Tuple[datetime, NarrativeAct, NarrativeAct]] = []
        # (timestamp, predicted_act, actual_act)
        
        # Tension predictions
        self._tension_predictions: List[Tuple[datetime, float, float]] = []
        # (timestamp, predicted_tension, actual_tension)
        
        # Resolution predictions
        self._resolution_predictions: List[Tuple[datetime, str, str, float]] = []
        # (timestamp, predicted_resolution, actual_resolution, confidence)
        
        # Intervention timing
        self._intervention_timing: List[Tuple[datetime, float, bool, float]] = []
        # (timestamp, recommended_urgency, was_followed, outcome_lift)
    
    async def record_act_detection(
        self,
        predicted_act: NarrativeAct,
        actual_act: NarrativeAct
    ) -> None:
        """Record an act detection for evaluation."""
        
        now = datetime.utcnow()
        
        self._act_detections.append((now, predicted_act, actual_act))
        
        # Prune
        cutoff = now - timedelta(days=7)
        self._act_detections = [a for a in self._act_detections if a[0] > cutoff]
        
        # Emit metrics
        if self.metrics:
            await self.metrics.increment(
                "adam.narrative.act_detections_total",
                tags={
                    "predicted": predicted_act.value,
                    "correct": str(predicted_act == actual_act).lower()
                }
            )
    
    async def record_tension_prediction(
        self,
        predicted_tension: float,
        actual_tension: float
    ) -> None:
        """Record a tension prediction for evaluation."""
        
        now = datetime.utcnow()
        
        self._tension_predictions.append((now, predicted_tension, actual_tension))
        
        # Prune
        cutoff = now - timedelta(days=7)
        self._tension_predictions = [t for t in self._tension_predictions if t[0] > cutoff]
    
    async def record_resolution_prediction(
        self,
        predicted_resolution: str,
        actual_resolution: str,
        confidence: float
    ) -> None:
        """Record a resolution prediction for evaluation."""
        
        now = datetime.utcnow()
        
        self._resolution_predictions.append((
            now, predicted_resolution, actual_resolution, confidence
        ))
        
        # Prune
        cutoff = now - timedelta(days=7)
        self._resolution_predictions = [r for r in self._resolution_predictions if r[0] > cutoff]
    
    async def record_intervention_timing(
        self,
        recommended_urgency: float,
        intervention_followed: bool,
        outcome_lift: float
    ) -> None:
        """Record intervention timing recommendation and outcome."""
        
        now = datetime.utcnow()
        
        self._intervention_timing.append((
            now, recommended_urgency, intervention_followed, outcome_lift
        ))
        
        # Prune
        cutoff = now - timedelta(days=7)
        self._intervention_timing = [t for t in self._intervention_timing if t[0] > cutoff]
    
    def _calculate_act_metrics(self) -> ActDetectionMetrics:
        """Calculate act detection metrics."""
        
        now = datetime.utcnow()
        
        if len(self._act_detections) < 20:
            return ActDetectionMetrics(
                timestamp=now,
                total_sessions_evaluated=len(self._act_detections),
                correct_act_detections=0,
                accuracy=0.5,
                transition_detection_accuracy=0.5,
                avg_transition_detection_delay_seconds=0.0
            )
        
        # Overall accuracy
        correct = sum(1 for _, pred, act in self._act_detections if pred == act)
        accuracy = correct / len(self._act_detections)
        
        # Per-act metrics
        precision_by_act = {}
        recall_by_act = {}
        f1_by_act = {}
        
        for act in NarrativeAct:
            # Precision: of times we predicted this act, how many were correct?
            predicted_as_act = [a for _, pred, _ in self._act_detections if pred == act]
            correct_predictions = [a for _, pred, actual in self._act_detections if pred == act and actual == act]
            precision = len(correct_predictions) / max(len(predicted_as_act), 1)
            
            # Recall: of times this was the actual act, how many did we detect?
            actual_act = [a for _, _, actual in self._act_detections if actual == act]
            detected = [a for _, pred, actual in self._act_detections if actual == act and pred == act]
            recall = len(detected) / max(len(actual_act), 1)
            
            f1 = 2 * precision * recall / max(precision + recall, 0.001)
            
            precision_by_act[act.value] = precision
            recall_by_act[act.value] = recall
            f1_by_act[act.value] = f1
        
        return ActDetectionMetrics(
            timestamp=now,
            total_sessions_evaluated=len(self._act_detections),
            correct_act_detections=correct,
            accuracy=accuracy,
            precision_by_act=precision_by_act,
            recall_by_act=recall_by_act,
            f1_by_act=f1_by_act,
            transition_detection_accuracy=accuracy * 0.9,  # Simplified
            avg_transition_detection_delay_seconds=2.0  # Simplified
        )
    
    async def get_session_narrative_health(self) -> SessionNarrativeHealth:
        """Get comprehensive Session Narrative health metrics."""
        
        now = datetime.utcnow()
        
        # Active sessions from engine
        active_sessions = len(self.narrative_engine.session_narratives)
        
        # Act detection metrics
        act_metrics = self._calculate_act_metrics()
        avg_f1 = np.mean(list(act_metrics.f1_by_act.values())) if act_metrics.f1_by_act else 0.5
        
        # Tension metrics
        if len(self._tension_predictions) > 10:
            tension_errors = [abs(pred - actual) for _, pred, actual in self._tension_predictions]
            tension_mae = np.mean(tension_errors)
            
            # Direction accuracy
            direction_correct = sum(
                1 for i in range(1, len(self._tension_predictions))
                if ((self._tension_predictions[i][1] > self._tension_predictions[i-1][1]) ==
                    (self._tension_predictions[i][2] > self._tension_predictions[i-1][2]))
            )
            trajectory_accuracy = direction_correct / max(len(self._tension_predictions) - 1, 1)
        else:
            tension_mae = 0.15
            trajectory_accuracy = 0.5
        
        # Resolution metrics
        if len(self._resolution_predictions) > 10:
            correct_resolutions = sum(
                1 for _, pred, actual, _ in self._resolution_predictions
                if pred == actual
            )
            resolution_accuracy = correct_resolutions / len(self._resolution_predictions)
            
            # Calibration
            bins = defaultdict(list)
            for _, pred, actual, conf in self._resolution_predictions:
                bin_idx = int(conf * 10)
                bins[bin_idx].append(1.0 if pred == actual else 0.0)
            
            ece = 0.0
            total = len(self._resolution_predictions)
            for bin_idx, outcomes in bins.items():
                expected = bin_idx / 10 + 0.05
                actual_rate = np.mean(outcomes)
                ece += abs(expected - actual_rate) * len(outcomes) / total
            
            resolution_calibration = 1.0 - ece
        else:
            resolution_accuracy = 0.5
            resolution_calibration = 0.5
        
        # Intervention timing
        if len(self._intervention_timing) > 10:
            followed = [t for t in self._intervention_timing if t[2]]
            not_followed = [t for t in self._intervention_timing if not t[2]]
            
            if followed and not_followed:
                timing_lift = np.mean([t[3] for t in followed]) - np.mean([t[3] for t in not_followed])
            else:
                timing_lift = 0.1
            
            timing_accuracy = len(followed) / len(self._intervention_timing)
            
            # Urgency calibration
            urgency_bins = defaultdict(list)
            for _, urgency, followed_flag, lift in self._intervention_timing:
                bin_idx = int(urgency * 10)
                urgency_bins[bin_idx].append(lift if followed_flag else 0)
            
            urgency_ece = 0.1  # Simplified
        else:
            timing_lift = 0.1
            timing_accuracy = 0.5
            urgency_ece = 0.15
        
        # Identify issues
        issues = []
        
        if act_metrics.accuracy < self.MIN_ACT_ACCURACY:
            issues.append(f"Low act detection accuracy: {act_metrics.accuracy:.1%}")
        
        if avg_f1 < self.MIN_ACT_F1:
            issues.append(f"Low average act F1: {avg_f1:.2f}")
        
        if tension_mae > self.MAX_TENSION_MAE:
            issues.append(f"High tension prediction error: {tension_mae:.3f}")
        
        if resolution_accuracy < self.MIN_RESOLUTION_ACCURACY:
            issues.append(f"Low resolution prediction: {resolution_accuracy:.1%}")
        
        if timing_lift < self.MIN_TIMING_LIFT and len(self._intervention_timing) > 20:
            issues.append(f"Low intervention timing lift: {timing_lift:.1%}")
        
        # Calculate health score
        health_components = [
            min(1.0, act_metrics.accuracy / self.MIN_ACT_ACCURACY),
            min(1.0, avg_f1 / self.MIN_ACT_F1),
            1.0 - min(1.0, tension_mae / self.MAX_TENSION_MAE),
            min(1.0, resolution_accuracy / self.MIN_RESOLUTION_ACCURACY),
            min(1.0, timing_lift / self.MIN_TIMING_LIFT) if timing_lift > 0 else 0.5
        ]
        health_score = np.mean(health_components)
        
        # Determine status
        if health_score >= 0.8 and len(issues) == 0:
            health_status = "healthy"
        elif health_score >= 0.6 and len(issues) <= 1:
            health_status = "degraded"
        elif health_score >= 0.4:
            health_status = "unhealthy"
        else:
            health_status = "critical"
        
        return SessionNarrativeHealth(
            timestamp=now,
            active_sessions=active_sessions,
            sessions_with_narrative=active_sessions,
            act_detection_accuracy=act_metrics.accuracy,
            avg_act_f1=avg_f1,
            transition_detection_accuracy=act_metrics.transition_detection_accuracy,
            tension_mae=tension_mae,
            tension_trajectory_accuracy=trajectory_accuracy,
            resolution_prediction_accuracy=resolution_accuracy,
            resolution_confidence_calibration=resolution_calibration,
            intervention_timing_lift=timing_lift,
            timing_recommendation_accuracy=timing_accuracy,
            urgency_calibration_ece=urgency_ece,
            narrative_outcome_correlation=0.6,  # Simplified
            health_score=health_score,
            health_status=health_status,
            issues=issues
        )
```

---

# SECTION G: META-COGNITIVE MONITORING

## G.1 Calibration and Explanation Health

```python
"""
ADAM Enhancement #20 v3: Meta-Cognitive Monitoring
Tracks calibration quality, explanation effectiveness, and reasoning consistency.
"""

from __future__ import annotations
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from collections import defaultdict
from enum import Enum
import numpy as np

from pydantic import BaseModel, Field


class ReasoningType(str, Enum):
    """Types of reasoning (from #04 v3)."""
    DEDUCTIVE = "deductive"
    INDUCTIVE = "inductive"
    ABDUCTIVE = "abductive"
    ANALOGICAL = "analogical"
    CAUSAL = "causal"


class CalibrationMetrics(BaseModel):
    """Detailed calibration metrics."""
    
    timestamp: datetime
    
    # Overall calibration
    expected_calibration_error: float = Field(ge=0.0, le=1.0)  # ECE
    maximum_calibration_error: float = Field(ge=0.0, le=1.0)  # MCE
    
    # Per-bin analysis
    calibration_by_bin: Dict[str, Dict[str, float]] = Field(default_factory=dict)
    # {bin: {expected, actual, count}}
    
    # Trends
    overconfident_rate: float = Field(ge=0.0, le=1.0)
    underconfident_rate: float = Field(ge=0.0, le=1.0)
    
    # Calibration trend
    ece_trend: str = Field(pattern="^(improving|stable|degrading)$")


class ExplanationQualityMetrics(BaseModel):
    """Metrics for explanation quality (if user feedback available)."""
    
    timestamp: datetime
    
    # Explanation coverage
    explanations_generated: int = Field(ge=0)
    explanations_with_feedback: int = Field(ge=0)
    
    # Quality scores (if feedback available)
    avg_helpfulness_score: Optional[float] = Field(ge=0.0, le=1.0, default=None)
    avg_accuracy_score: Optional[float] = Field(ge=0.0, le=1.0, default=None)
    
    # Reasoning type distribution
    reasoning_type_distribution: Dict[str, float] = Field(default_factory=dict)
    
    # Consistency
    explanation_consistency: float = Field(ge=0.0, le=1.0)  # Same input → same explanation?


class UncertaintyDecompositionMetrics(BaseModel):
    """Metrics for uncertainty decomposition quality."""
    
    timestamp: datetime
    
    # Decomposition coverage
    decompositions_generated: int = Field(ge=0)
    
    # Component accuracy (validated against outcomes)
    epistemic_accuracy: float = Field(ge=0.0, le=1.0)
    aleatoric_accuracy: float = Field(ge=0.0, le=1.0)
    model_uncertainty_accuracy: float = Field(ge=0.0, le=1.0)
    
    # Action recommendation accuracy
    recommended_action_success_rate: float = Field(ge=0.0, le=1.0)


class MetaCognitiveHealth(BaseModel):
    """
    Comprehensive health metrics for Meta-Cognitive Layer.
    """
    
    timestamp: datetime
    
    # Calibration health
    calibration_ece: float = Field(ge=0.0, le=1.0)
    calibration_mce: float = Field(ge=0.0, le=1.0)
    calibration_trend: str = Field(pattern="^(improving|stable|degrading)$")
    
    # Over/under confidence
    overconfident_rate: float = Field(ge=0.0, le=1.0)
    underconfident_rate: float = Field(ge=0.0, le=1.0)
    
    # Explanation health
    explanation_coverage: float = Field(ge=0.0, le=1.0)
    explanation_consistency: float = Field(ge=0.0, le=1.0)
    
    # "What would change my mind" accuracy
    counterfactual_trigger_accuracy: float = Field(ge=0.0, le=1.0)
    
    # Uncertainty decomposition
    uncertainty_decomposition_accuracy: float = Field(ge=0.0, le=1.0)
    recommended_action_success: float = Field(ge=0.0, le=1.0)
    
    # Reasoning trace health
    trace_completeness: float = Field(ge=0.0, le=1.0)
    evidence_attribution_accuracy: float = Field(ge=0.0, le=1.0)
    
    # Overall health
    health_score: float = Field(ge=0.0, le=1.0)
    health_status: str = Field(pattern="^(healthy|degraded|unhealthy|critical)$")
    issues: List[str] = Field(default_factory=list)


class MetaCognitiveMonitor:
    """
    Monitors the Meta-Cognitive Layer for health and drift.
    
    Key monitoring areas:
    1. Confidence calibration
    2. Explanation quality and consistency
    3. Uncertainty decomposition accuracy
    4. "What would change my mind" accuracy
    """
    
    # Health thresholds
    MAX_CALIBRATION_ECE = 0.08           # Max 8% Expected Calibration Error
    MAX_CALIBRATION_MCE = 0.20           # Max 20% Maximum Calibration Error
    MAX_OVERCONFIDENT_RATE = 0.15        # Max 15% overconfident predictions
    MIN_EXPLANATION_CONSISTENCY = 0.85   # 85% explanation consistency
    MIN_COUNTERFACTUAL_ACCURACY = 0.60   # 60% "what would change" accuracy
    MIN_DECOMPOSITION_ACCURACY = 0.65    # 65% uncertainty decomposition accuracy
    
    def __init__(
        self,
        metacognitive_engine: 'MetaCognitiveEngine',
        metrics_client: Optional[Any] = None
    ):
        self.metacognitive_engine = metacognitive_engine
        self.metrics = metrics_client
        
        # Calibration tracking
        self._predictions: List[Tuple[datetime, float, bool]] = []
        # (timestamp, confidence, was_correct)
        
        # Explanation tracking
        self._explanations: List[Tuple[datetime, str, str, Optional[float]]] = []
        # (timestamp, input_hash, explanation_hash, feedback_score)
        
        # Counterfactual tracking
        self._counterfactual_triggers: List[Tuple[datetime, List[str], List[str]]] = []
        # (timestamp, predicted_triggers, actual_triggers)
        
        # Uncertainty decomposition tracking
        self._decompositions: List[Tuple[datetime, str, str, bool]] = []
        # (timestamp, recommended_action, actual_action_taken, outcome_improved)
    
    async def record_prediction_outcome(
        self,
        confidence: float,
        was_correct: bool
    ) -> None:
        """Record a prediction outcome for calibration analysis."""
        
        now = datetime.utcnow()
        
        self._predictions.append((now, confidence, was_correct))
        
        # Prune
        cutoff = now - timedelta(days=7)
        self._predictions = [p for p in self._predictions if p[0] > cutoff]
        
        # Update engine's calibration
        self.metacognitive_engine.update_calibration(confidence, was_correct)
        
        # Emit metrics
        if self.metrics:
            await self.metrics.increment(
                "adam.metacognitive.predictions_total",
                tags={"correct": str(was_correct).lower()}
            )
    
    async def record_explanation(
        self,
        input_hash: str,
        explanation_hash: str,
        feedback_score: Optional[float] = None
    ) -> None:
        """Record an explanation for consistency tracking."""
        
        now = datetime.utcnow()
        
        self._explanations.append((now, input_hash, explanation_hash, feedback_score))
        
        # Prune
        cutoff = now - timedelta(days=7)
        self._explanations = [e for e in self._explanations if e[0] > cutoff]
    
    async def record_counterfactual_evaluation(
        self,
        predicted_triggers: List[str],
        actual_triggers: List[str]
    ) -> None:
        """Record evaluation of 'what would change my mind' predictions."""
        
        now = datetime.utcnow()
        
        self._counterfactual_triggers.append((now, predicted_triggers, actual_triggers))
        
        # Prune
        cutoff = now - timedelta(days=7)
        self._counterfactual_triggers = [
            c for c in self._counterfactual_triggers if c[0] > cutoff
        ]
    
    async def record_decomposition_outcome(
        self,
        recommended_action: str,
        actual_action_taken: str,
        outcome_improved: bool
    ) -> None:
        """Record outcome of uncertainty-based action recommendation."""
        
        now = datetime.utcnow()
        
        self._decompositions.append((
            now, recommended_action, actual_action_taken, outcome_improved
        ))
        
        # Prune
        cutoff = now - timedelta(days=7)
        self._decompositions = [d for d in self._decompositions if d[0] > cutoff]
    
    def _calculate_calibration_metrics(self) -> CalibrationMetrics:
        """Calculate detailed calibration metrics."""
        
        now = datetime.utcnow()
        
        if len(self._predictions) < 50:
            return CalibrationMetrics(
                timestamp=now,
                expected_calibration_error=0.1,
                maximum_calibration_error=0.2,
                overconfident_rate=0.1,
                underconfident_rate=0.1,
                ece_trend="stable"
            )
        
        # Bin predictions by confidence
        bins = defaultdict(list)
        for _, conf, correct in self._predictions:
            bin_idx = int(conf * 10)
            bins[bin_idx].append(1.0 if correct else 0.0)
        
        # Calculate ECE and MCE
        total = len(self._predictions)
        ece = 0.0
        mce = 0.0
        calibration_by_bin = {}
        
        for bin_idx, outcomes in bins.items():
            expected = bin_idx / 10 + 0.05  # Bin midpoint
            actual = np.mean(outcomes)
            gap = abs(expected - actual)
            
            ece += gap * len(outcomes) / total
            mce = max(mce, gap)
            
            calibration_by_bin[f"{bin_idx*10}-{(bin_idx+1)*10}%"] = {
                "expected": expected,
                "actual": actual,
                "count": len(outcomes)
            }
        
        # Over/under confident
        overconfident = sum(
            1 for _, conf, correct in self._predictions
            if conf > 0.7 and not correct
        ) / total
        
        underconfident = sum(
            1 for _, conf, correct in self._predictions
            if conf < 0.4 and correct
        ) / total
        
        # Trend (compare to previous week)
        cutoff_old = now - timedelta(days=14)
        cutoff_new = now - timedelta(days=7)
        
        old_preds = [(c, r) for ts, c, r in self._predictions if cutoff_old < ts <= cutoff_new]
        
        if len(old_preds) > 20:
            old_bins = defaultdict(list)
            for conf, correct in old_preds:
                bin_idx = int(conf * 10)
                old_bins[bin_idx].append(1.0 if correct else 0.0)
            
            old_ece = 0.0
            old_total = len(old_preds)
            for bin_idx, outcomes in old_bins.items():
                expected = bin_idx / 10 + 0.05
                actual = np.mean(outcomes)
                old_ece += abs(expected - actual) * len(outcomes) / old_total
            
            if ece < old_ece * 0.9:
                trend = "improving"
            elif ece > old_ece * 1.1:
                trend = "degrading"
            else:
                trend = "stable"
        else:
            trend = "stable"
        
        return CalibrationMetrics(
            timestamp=now,
            expected_calibration_error=ece,
            maximum_calibration_error=mce,
            calibration_by_bin=calibration_by_bin,
            overconfident_rate=overconfident,
            underconfident_rate=underconfident,
            ece_trend=trend
        )
    
    def _calculate_explanation_consistency(self) -> float:
        """Calculate explanation consistency (same input → same explanation)."""
        
        if len(self._explanations) < 10:
            return 0.85  # Prior
        
        # Group by input hash
        by_input = defaultdict(list)
        for _, input_hash, explanation_hash, _ in self._explanations:
            by_input[input_hash].append(explanation_hash)
        
        # Calculate consistency
        consistencies = []
        for input_hash, explanations in by_input.items():
            if len(explanations) > 1:
                # What fraction are the same as the most common?
                from collections import Counter
                most_common_count = Counter(explanations).most_common(1)[0][1]
                consistency = most_common_count / len(explanations)
                consistencies.append(consistency)
        
        return np.mean(consistencies) if consistencies else 0.85
    
    def _calculate_counterfactual_accuracy(self) -> float:
        """Calculate accuracy of 'what would change my mind' predictions."""
        
        if len(self._counterfactual_triggers) < 10:
            return 0.6  # Prior
        
        # For each evaluation, check overlap between predicted and actual triggers
        accuracies = []
        for _, predicted, actual in self._counterfactual_triggers:
            if actual:
                overlap = len(set(predicted) & set(actual))
                union = len(set(predicted) | set(actual))
                jaccard = overlap / max(union, 1)
                accuracies.append(jaccard)
        
        return np.mean(accuracies) if accuracies else 0.6
    
    async def get_metacognitive_health(self) -> MetaCognitiveHealth:
        """Get comprehensive Meta-Cognitive health metrics."""
        
        now = datetime.utcnow()
        
        # Calibration metrics
        calibration = self._calculate_calibration_metrics()
        
        # Explanation metrics
        explanation_consistency = self._calculate_explanation_consistency()
        explanation_coverage = min(1.0, len(self._explanations) / 100)  # Target 100 explanations
        
        # Counterfactual accuracy
        counterfactual_accuracy = self._calculate_counterfactual_accuracy()
        
        # Decomposition metrics
        if len(self._decompositions) > 10:
            # When recommendation was followed, did outcome improve?
            followed = [d for d in self._decompositions if d[1] == d[2]]
            success_rate = (
                sum(1 for d in followed if d[3]) / max(len(followed), 1)
                if followed else 0.5
            )
            decomposition_accuracy = success_rate
        else:
            decomposition_accuracy = 0.65
            success_rate = 0.65
        
        # Identify issues
        issues = []
        
        if calibration.expected_calibration_error > self.MAX_CALIBRATION_ECE:
            issues.append(f"High calibration error: ECE={calibration.expected_calibration_error:.2f}")
        
        if calibration.overconfident_rate > self.MAX_OVERCONFIDENT_RATE:
            issues.append(f"High overconfidence rate: {calibration.overconfident_rate:.1%}")
        
        if explanation_consistency < self.MIN_EXPLANATION_CONSISTENCY:
            issues.append(f"Low explanation consistency: {explanation_consistency:.1%}")
        
        if counterfactual_accuracy < self.MIN_COUNTERFACTUAL_ACCURACY:
            issues.append(f"Low counterfactual accuracy: {counterfactual_accuracy:.1%}")
        
        # Calculate health score
        health_components = [
            1.0 - min(1.0, calibration.expected_calibration_error / self.MAX_CALIBRATION_ECE),
            1.0 - min(1.0, calibration.overconfident_rate / self.MAX_OVERCONFIDENT_RATE),
            min(1.0, explanation_consistency / self.MIN_EXPLANATION_CONSISTENCY),
            min(1.0, counterfactual_accuracy / self.MIN_COUNTERFACTUAL_ACCURACY),
            min(1.0, decomposition_accuracy / self.MIN_DECOMPOSITION_ACCURACY)
        ]
        health_score = np.mean(health_components)
        
        # Determine status
        if health_score >= 0.8 and len(issues) == 0:
            health_status = "healthy"
        elif health_score >= 0.6 and len(issues) <= 1:
            health_status = "degraded"
        elif health_score >= 0.4:
            health_status = "unhealthy"
        else:
            health_status = "critical"
        
        return MetaCognitiveHealth(
            timestamp=now,
            calibration_ece=calibration.expected_calibration_error,
            calibration_mce=calibration.maximum_calibration_error,
            calibration_trend=calibration.ece_trend,
            overconfident_rate=calibration.overconfident_rate,
            underconfident_rate=calibration.underconfident_rate,
            explanation_coverage=explanation_coverage,
            explanation_consistency=explanation_consistency,
            counterfactual_trigger_accuracy=counterfactual_accuracy,
            uncertainty_decomposition_accuracy=decomposition_accuracy,
            recommended_action_success=success_rate,
            trace_completeness=0.95,  # Simplified
            evidence_attribution_accuracy=0.85,  # Simplified
            health_score=health_score,
            health_status=health_status,
            issues=issues
        )
```

---

# SECTION H: UNIFIED V3 HEALTH DASHBOARD

## H.1 Comprehensive v3 Health Aggregator

```python
"""
ADAM Enhancement #20 v3: Unified Health Dashboard
Aggregates health from all v3 cognitive layers.
"""

from __future__ import annotations
from datetime import datetime
from typing import Dict, List, Optional, Any
import numpy as np

from pydantic import BaseModel, Field


class V3LayerHealth(BaseModel):
    """Health summary for a single v3 layer."""
    
    layer_name: str
    health_score: float = Field(ge=0.0, le=1.0)
    health_status: str
    primary_metric: str
    primary_metric_value: float
    issue_count: int = Field(ge=0)
    top_issue: Optional[str] = None


class V3HealthDashboard(BaseModel):
    """
    Unified dashboard for all v3 cognitive layer health.
    """
    
    timestamp: datetime
    
    # Per-layer health
    emergence_health: V3LayerHealth
    causal_health: V3LayerHealth
    temporal_health: V3LayerHealth
    interaction_health: V3LayerHealth
    narrative_health: V3LayerHealth
    metacognitive_health: V3LayerHealth
    
    # Aggregate metrics
    overall_v3_health_score: float = Field(ge=0.0, le=1.0)
    overall_v3_status: str = Field(pattern="^(healthy|degraded|unhealthy|critical)$")
    
    # Cross-layer issues
    layer_interaction_issues: List[str] = Field(default_factory=list)
    
    # Active drift alerts
    active_drift_alerts: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Recommended actions
    priority_actions: List[str] = Field(default_factory=list)


class V3HealthAggregator:
    """
    Aggregates health metrics from all v3 cognitive layers.
    """
    
    def __init__(
        self,
        emergence_monitor: 'EmergenceEngineMonitor',
        causal_monitor: 'CausalDiscoveryMonitor',
        temporal_monitor: 'TemporalDynamicsMonitor',
        interaction_monitor: 'MechanismInteractionMonitor',
        narrative_monitor: 'SessionNarrativeMonitor',
        metacognitive_monitor: 'MetaCognitiveMonitor'
    ):
        self.emergence = emergence_monitor
        self.causal = causal_monitor
        self.temporal = temporal_monitor
        self.interaction = interaction_monitor
        self.narrative = narrative_monitor
        self.metacognitive = metacognitive_monitor
    
    async def get_v3_health_dashboard(self) -> V3HealthDashboard:
        """Get unified v3 health dashboard."""
        
        now = datetime.utcnow()
        
        # Gather health from all layers
        emergence = await self.emergence.get_emergence_health()
        causal = await self.causal.get_causal_graph_health()
        temporal = await self.temporal.get_temporal_dynamics_health()
        interaction = await self.interaction.get_mechanism_interaction_health()
        narrative = await self.narrative.get_session_narrative_health()
        metacognitive = await self.metacognitive.get_metacognitive_health()
        
        # Create layer summaries
        layer_healths = [
            V3LayerHealth(
                layer_name="Emergence Engine",
                health_score=emergence.health_score,
                health_status=emergence.health_status,
                primary_metric="Discovery Rate (7d)",
                primary_metric_value=emergence.insights_discovered_7d,
                issue_count=len(emergence.issues),
                top_issue=emergence.issues[0] if emergence.issues else None
            ),
            V3LayerHealth(
                layer_name="Causal Discovery",
                health_score=causal.health_score,
                health_status=causal.health_status,
                primary_metric="Counterfactual Accuracy",
                primary_metric_value=causal.counterfactual_accuracy,
                issue_count=len(causal.issues),
                top_issue=causal.issues[0] if causal.issues else None
            ),
            V3LayerHealth(
                layer_name="Temporal Dynamics",
                health_score=temporal.health_score,
                health_status=temporal.health_status,
                primary_metric="Trajectory MAE",
                primary_metric_value=temporal.avg_prediction_mae,
                issue_count=len(temporal.issues),
                top_issue=temporal.issues[0] if temporal.issues else None
            ),
            V3LayerHealth(
                layer_name="Mechanism Interactions",
                health_score=interaction.health_score,
                health_status=interaction.health_status,
                primary_metric="Coefficient Stability",
                primary_metric_value=interaction.avg_coefficient_stability,
                issue_count=len(interaction.issues),
                top_issue=interaction.issues[0] if interaction.issues else None
            ),
            V3LayerHealth(
                layer_name="Session Narrative",
                health_score=narrative.health_score,
                health_status=narrative.health_status,
                primary_metric="Act Detection Accuracy",
                primary_metric_value=narrative.act_detection_accuracy,
                issue_count=len(narrative.issues),
                top_issue=narrative.issues[0] if narrative.issues else None
            ),
            V3LayerHealth(
                layer_name="Meta-Cognitive",
                health_score=metacognitive.health_score,
                health_status=metacognitive.health_status,
                primary_metric="Calibration ECE",
                primary_metric_value=metacognitive.calibration_ece,
                issue_count=len(metacognitive.issues),
                top_issue=metacognitive.issues[0] if metacognitive.issues else None
            )
        ]
        
        # Calculate overall v3 health
        # Weight by importance
        weights = {
            "Emergence Engine": 0.15,
            "Causal Discovery": 0.20,
            "Temporal Dynamics": 0.15,
            "Mechanism Interactions": 0.15,
            "Session Narrative": 0.15,
            "Meta-Cognitive": 0.20
        }
        
        overall_score = sum(
            h.health_score * weights[h.layer_name]
            for h in layer_healths
        )
        
        # Overall status
        unhealthy_layers = sum(
            1 for h in layer_healths
            if h.health_status in ["unhealthy", "critical"]
        )
        
        if overall_score >= 0.8 and unhealthy_layers == 0:
            overall_status = "healthy"
        elif overall_score >= 0.6 and unhealthy_layers <= 1:
            overall_status = "degraded"
        elif overall_score >= 0.4:
            overall_status = "unhealthy"
        else:
            overall_status = "critical"
        
        # Cross-layer issues
        cross_layer_issues = []
        
        # Check for correlated degradation
        if (emergence.health_status != "healthy" and 
            causal.health_status != "healthy"):
            cross_layer_issues.append(
                "Emergence and Causal layers both degraded - may indicate data quality issue"
            )
        
        if (temporal.health_status != "healthy" and
            narrative.health_status != "healthy"):
            cross_layer_issues.append(
                "Temporal and Narrative layers both degraded - session tracking may be compromised"
            )
        
        if metacognitive.health_status == "critical":
            cross_layer_issues.append(
                "Meta-Cognitive layer critical - all confidence scores unreliable"
            )
        
        # Collect drift alerts
        drift_alerts = []
        
        emergence_drift = await self.emergence.detect_emergence_drift()
        if emergence_drift:
            drift_alerts.append(emergence_drift)
        
        # Priority actions
        priority_actions = []
        
        # Sort layers by health (worst first)
        sorted_layers = sorted(layer_healths, key=lambda h: h.health_score)
        
        for layer in sorted_layers[:3]:  # Top 3 worst
            if layer.top_issue:
                priority_actions.append(
                    f"{layer.layer_name}: {layer.top_issue}"
                )
        
        return V3HealthDashboard(
            timestamp=now,
            emergence_health=layer_healths[0],
            causal_health=layer_healths[1],
            temporal_health=layer_healths[2],
            interaction_health=layer_healths[3],
            narrative_health=layer_healths[4],
            metacognitive_health=layer_healths[5],
            overall_v3_health_score=overall_score,
            overall_v3_status=overall_status,
            layer_interaction_issues=cross_layer_issues,
            active_drift_alerts=drift_alerts,
            priority_actions=priority_actions
        )
```

---

# SECTION I: PROMETHEUS METRICS FOR V3

## I.1 Extended Metrics Registry

```python
"""
ADAM Enhancement #20 v3: Prometheus Metrics for v3 Layers
"""

from prometheus_client import Counter, Gauge, Histogram, Summary


# ============================================================================
# EMERGENCE ENGINE METRICS
# ============================================================================

EMERGENCE_DISCOVERIES = Counter(
    "adam_emergence_discoveries_total",
    "Total emergent insights discovered",
    ["emergence_type"]
)

EMERGENCE_VALIDATIONS = Counter(
    "adam_emergence_validations_total",
    "Total validation attempts for emergent insights",
    ["result"]  # success, failure
)

EMERGENCE_PROMOTIONS = Counter(
    "adam_emergence_promotions_total",
    "Total insights promoted to constructs"
)

EMERGENCE_DEPRECATIONS = Counter(
    "adam_emergence_deprecations_total",
    "Total constructs deprecated",
    ["reason"]
)

EMERGENCE_HEALTH_SCORE = Gauge(
    "adam_emergence_health_score",
    "Emergence engine health score 0-1"
)

EMERGENCE_DISCOVERY_RATE = Gauge(
    "adam_emergence_discovery_rate_7d",
    "Discoveries in the last 7 days"
)

EMERGENCE_VALIDATION_RATE = Gauge(
    "adam_emergence_validation_rate",
    "Average validation rate for insights"
)

EMERGENCE_FALSE_POSITIVE_RATE = Gauge(
    "adam_emergence_false_positive_rate",
    "Rate of deprecated promoted insights"
)


# ============================================================================
# CAUSAL DISCOVERY METRICS
# ============================================================================

CAUSAL_GRAPH_NODES = Gauge(
    "adam_causal_graph_nodes_total",
    "Total nodes in causal graph"
)

CAUSAL_GRAPH_EDGES = Gauge(
    "adam_causal_graph_edges_total",
    "Total edges in causal graph"
)

CAUSAL_EDGE_CONFIDENCE = Histogram(
    "adam_causal_edge_confidence",
    "Distribution of causal edge confidence scores",
    buckets=[0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
)

CAUSAL_COUNTERFACTUAL_ACCURACY = Gauge(
    "adam_causal_counterfactual_accuracy",
    "Counterfactual reasoning accuracy"
)

CAUSAL_INTERVENTION_SUCCESS = Gauge(
    "adam_causal_intervention_success_rate",
    "Intervention recommendation success rate"
)

CAUSAL_HEALTH_SCORE = Gauge(
    "adam_causal_health_score",
    "Causal discovery health score 0-1"
)


# ============================================================================
# TEMPORAL DYNAMICS METRICS
# ============================================================================

TEMPORAL_ACTIVE_TRAJECTORIES = Gauge(
    "adam_temporal_active_trajectories",
    "Number of active state trajectories"
)

TEMPORAL_PREDICTION_ERROR = Histogram(
    "adam_temporal_prediction_error",
    "Trajectory prediction error distribution",
    ["construct", "horizon_seconds"],
    buckets=[0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.40, 0.50]
)

TEMPORAL_DIRECTION_ACCURACY = Gauge(
    "adam_temporal_direction_accuracy",
    "Trajectory direction prediction accuracy",
    ["construct"]
)

TEMPORAL_PHASE_DETECTION_F1 = Gauge(
    "adam_temporal_phase_detection_f1",
    "Phase transition detection F1 score"
)

TEMPORAL_HEALTH_SCORE = Gauge(
    "adam_temporal_health_score",
    "Temporal dynamics health score 0-1"
)


# ============================================================================
# MECHANISM INTERACTION METRICS
# ============================================================================

INTERACTION_COEFFICIENT = Gauge(
    "adam_interaction_coefficient",
    "Mechanism interaction coefficient",
    ["mechanism_a", "mechanism_b"]
)

INTERACTION_COEFFICIENT_STABILITY = Gauge(
    "adam_interaction_coefficient_stability",
    "Stability of interaction coefficient estimates"
)

INTERACTION_PREDICTION_ERROR = Gauge(
    "adam_interaction_prediction_error",
    "Average combination effect prediction error"
)

INTERACTION_RECOMMENDATION_LIFT = Gauge(
    "adam_interaction_recommendation_lift",
    "Lift from following mechanism combination recommendations"
)

INTERACTION_HEALTH_SCORE = Gauge(
    "adam_interaction_health_score",
    "Mechanism interaction health score 0-1"
)


# ============================================================================
# SESSION NARRATIVE METRICS
# ============================================================================

NARRATIVE_ACTIVE_SESSIONS = Gauge(
    "adam_narrative_active_sessions",
    "Sessions with active narrative tracking"
)

NARRATIVE_ACT_ACCURACY = Gauge(
    "adam_narrative_act_detection_accuracy",
    "Narrative act detection accuracy"
)

NARRATIVE_ACT_F1 = Gauge(
    "adam_narrative_act_f1",
    "F1 score per narrative act",
    ["act"]
)

NARRATIVE_TENSION_MAE = Gauge(
    "adam_narrative_tension_mae",
    "Tension prediction mean absolute error"
)

NARRATIVE_RESOLUTION_ACCURACY = Gauge(
    "adam_narrative_resolution_accuracy",
    "Resolution prediction accuracy"
)

NARRATIVE_TIMING_LIFT = Gauge(
    "adam_narrative_timing_lift",
    "Lift from optimal intervention timing"
)

NARRATIVE_HEALTH_SCORE = Gauge(
    "adam_narrative_health_score",
    "Session narrative health score 0-1"
)


# ============================================================================
# META-COGNITIVE METRICS
# ============================================================================

METACOGNITIVE_CALIBRATION_ECE = Gauge(
    "adam_metacognitive_calibration_ece",
    "Expected Calibration Error"
)

METACOGNITIVE_CALIBRATION_MCE = Gauge(
    "adam_metacognitive_calibration_mce",
    "Maximum Calibration Error"
)

METACOGNITIVE_OVERCONFIDENT_RATE = Gauge(
    "adam_metacognitive_overconfident_rate",
    "Rate of overconfident predictions"
)

METACOGNITIVE_EXPLANATION_CONSISTENCY = Gauge(
    "adam_metacognitive_explanation_consistency",
    "Explanation consistency score"
)

METACOGNITIVE_COUNTERFACTUAL_ACCURACY = Gauge(
    "adam_metacognitive_counterfactual_trigger_accuracy",
    "Accuracy of 'what would change my mind' predictions"
)

METACOGNITIVE_HEALTH_SCORE = Gauge(
    "adam_metacognitive_health_score",
    "Meta-cognitive layer health score 0-1"
)


# ============================================================================
# UNIFIED V3 METRICS
# ============================================================================

V3_OVERALL_HEALTH = Gauge(
    "adam_v3_overall_health_score",
    "Overall v3 cognitive layers health score"
)

V3_LAYER_HEALTH = Gauge(
    "adam_v3_layer_health_score",
    "Per-layer v3 health score",
    ["layer"]
)

V3_DRIFT_ALERTS = Gauge(
    "adam_v3_drift_alerts_active",
    "Number of active v3 drift alerts",
    ["dimension"]
)
```

---

# SECTION J: IMPLEMENTATION TIMELINE

## J.1 V3 Monitoring Implementation Roadmap

| Phase | Duration | Components | Deliverables |
|-------|----------|------------|--------------|
| **Phase 1** | Weeks 1-2 | Emergence Monitoring | EmergenceEngineMonitor, discovery/validation tracking, Prometheus metrics |
| **Phase 2** | Weeks 3-4 | Causal Monitoring | CausalDiscoveryMonitor, counterfactual accuracy tracking, edge health |
| **Phase 3** | Weeks 5-6 | Temporal Monitoring | TemporalDynamicsMonitor, trajectory/phase metrics |
| **Phase 4** | Week 7 | Interaction Monitoring | MechanismInteractionMonitor, coefficient stability |
| **Phase 5** | Week 8 | Narrative Monitoring | SessionNarrativeMonitor, act/tension metrics |
| **Phase 6** | Week 9 | Meta-Cognitive Monitoring | MetaCognitiveMonitor, calibration tracking |
| **Phase 7** | Week 10 | Integration | V3HealthAggregator, unified dashboard |
| **Phase 8** | Weeks 11-12 | Production | Alerting integration, Grafana dashboards, testing |

**Total: 12 weeks** (in parallel with #20 v2.0 implementation)

---

# SECTION K: SUCCESS METRICS

## K.1 V3 Monitoring KPIs

| Category | Metric | Target |
|----------|--------|--------|
| **Emergence** | Discovery rate drift detection latency | <24 hours |
| **Emergence** | False positive rate alert accuracy | >90% |
| **Causal** | Counterfactual accuracy degradation detection | <12 hours |
| **Causal** | Stale edge identification coverage | 100% |
| **Temporal** | Trajectory prediction drift detection | <6 hours |
| **Temporal** | Phase detection F1 monitoring coverage | 100% |
| **Interaction** | Coefficient instability detection | <24 hours |
| **Interaction** | Recommendation lift tracking coverage | >95% |
| **Narrative** | Act detection degradation detection | <12 hours |
| **Narrative** | Timing recommendation tracking | 100% |
| **Meta-Cognitive** | Calibration drift detection | <6 hours |
| **Meta-Cognitive** | Explanation consistency monitoring | 100% |
| **Overall** | V3 health dashboard latency | <5 seconds |
| **Overall** | Alert false positive rate | <10% |

---

## CONCLUSION

This v3 supplement extends Enhancement #20's monitoring capabilities to cover the six new cognitive layers introduced in Enhancement #04 v3:

1. **Emergence Engine Monitoring**: Tracks discovery rates, validation success, false positive rates, and construct churn
2. **Causal Discovery Monitoring**: Monitors causal graph health, counterfactual accuracy, and intervention effectiveness
3. **Temporal Dynamics Monitoring**: Tracks trajectory prediction accuracy and phase transition detection
4. **Mechanism Interaction Monitoring**: Monitors coefficient stability and combination effectiveness
5. **Session Narrative Monitoring**: Tracks act detection accuracy and intervention timing lift
6. **Meta-Cognitive Monitoring**: Monitors calibration quality and explanation consistency

Together with #20 v2.0, this provides complete observability for ADAM's advanced cognitive architecture.

---

*Enhancement #20 v3 Supplement COMPLETE. Integrates with #20 v2.0 for full monitoring coverage.*
