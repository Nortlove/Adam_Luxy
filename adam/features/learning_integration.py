# =============================================================================
# ADAM Feature Store Learning Integration
# Location: adam/features/learning_integration.py
# =============================================================================

"""
FEATURE STORE LEARNING INTEGRATION

Bridges the Feature Store with the learning system.

Learning Responsibilities:
1. Validate feature predictions against outcomes
2. Learn feature importance from outcome correlations
3. Detect feature drift
4. Update feature priors from outcomes

Reference: Enhancement #30 Feature Store
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

from pydantic import BaseModel, Field

from adam.core.learning.universal_learning_interface import (
    LearningCapableComponent,
    LearningSignal,
    LearningSignalType,
    LearningContribution,
    LearningQualityMetrics,
)

logger = logging.getLogger(__name__)


class FeatureImportance(BaseModel):
    """Learned importance of a feature."""
    
    feature_id: str
    importance_score: float = Field(ge=0.0, le=1.0, default=0.5)
    correlation_with_outcome: float = Field(ge=-1.0, le=1.0, default=0.0)
    sample_size: int = Field(ge=0, default=0)
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class FeatureDriftAlert(BaseModel):
    """Alert for detected feature drift."""
    
    feature_id: str
    drift_type: str  # "distribution", "correlation", "availability"
    severity: str  # "low", "medium", "high"
    current_value: float
    expected_value: float
    detected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class FeatureStoreLearningBridge(LearningCapableComponent):
    """
    Learning integration for Feature Store.
    
    Makes the Feature Store a learning participant by:
    1. Tracking feature correlations with outcomes
    2. Learning feature importance
    3. Detecting feature drift
    4. Updating feature priors
    """
    
    def __init__(
        self,
        feature_store,
        redis_client=None,
        event_bus=None,
    ):
        self.feature_store = feature_store
        self.redis = redis_client
        self.event_bus = event_bus
        
        # Learned feature importance
        self._feature_importance: Dict[str, FeatureImportance] = {}
        
        # Drift detection
        self._feature_baselines: Dict[str, Dict[str, float]] = {}
        self._drift_alerts: List[FeatureDriftAlert] = []
        
        # Tracking
        self._outcomes_processed: int = 0
        self._features_updated: int = 0
    
    @property
    def component_name(self) -> str:
        return "feature_store"
    
    @property
    def component_version(self) -> str:
        return "2.0"
    
    async def on_outcome_received(
        self,
        decision_id: str,
        outcome_type: str,
        outcome_value: float,
        context: Dict[str, Any],
    ) -> List[LearningSignal]:
        """Process outcome and update feature importance."""
        
        signals = []
        self._outcomes_processed += 1
        
        # Get features used in decision
        user_id = context.get("user_id")
        features_used = context.get("features_used", {})
        
        if not user_id or not features_used:
            return signals
        
        # Update importance for each feature
        for feature_id, feature_value in features_used.items():
            importance = self._feature_importance.get(feature_id)
            if not importance:
                importance = FeatureImportance(feature_id=feature_id)
                self._feature_importance[feature_id] = importance
            
            # Update correlation (exponential moving average)
            # Positive outcome with high feature value = positive correlation
            normalized_value = feature_value if isinstance(feature_value, float) else 0.5
            correlation_signal = (outcome_value - 0.5) * (normalized_value - 0.5) * 4
            
            old_corr = importance.correlation_with_outcome
            importance.correlation_with_outcome = old_corr * 0.95 + correlation_signal * 0.05
            importance.sample_size += 1
            importance.last_updated = datetime.now(timezone.utc)
            
            # Update importance score based on correlation strength
            importance.importance_score = min(1.0, abs(importance.correlation_with_outcome) + 0.3)
            
            self._features_updated += 1
        
        # Check for drift
        drift_alerts = await self._check_feature_drift(features_used)
        
        # Emit signals
        if self._outcomes_processed % 100 == 0:  # Every 100 outcomes
            # Emit importance update signal
            top_features = sorted(
                self._feature_importance.values(),
                key=lambda f: f.importance_score,
                reverse=True,
            )[:10]
            
            signals.append(LearningSignal(
                signal_type=LearningSignalType.SIGNAL_QUALITY_UPDATED,
                source_component=self.component_name,
                decision_id=decision_id,
                payload={
                    "feature_importance_updated": True,
                    "top_features": [
                        {"id": f.feature_id, "importance": f.importance_score}
                        for f in top_features
                    ],
                },
                confidence=0.8,
                target_components=["meta_learner", "holistic_synthesizer"],
            ))
        
        # Emit drift alerts
        for alert in drift_alerts:
            signals.append(LearningSignal(
                signal_type=LearningSignalType.FEEDBACK_RECEIVED,
                source_component=self.component_name,
                decision_id=decision_id,
                payload={
                    "drift_detected": True,
                    "feature_id": alert.feature_id,
                    "drift_type": alert.drift_type,
                    "severity": alert.severity,
                },
                confidence=0.7,
                target_components=["monitoring", "gradient_bridge"],
            ))
        
        return signals
    
    async def _check_feature_drift(
        self,
        features: Dict[str, Any],
    ) -> List[FeatureDriftAlert]:
        """Check for feature drift."""
        alerts = []
        
        for feature_id, value in features.items():
            if not isinstance(value, (int, float)):
                continue
            
            # Initialize baseline if not present
            if feature_id not in self._feature_baselines:
                self._feature_baselines[feature_id] = {
                    "mean": value,
                    "count": 1,
                    "sum_sq": value ** 2,
                }
                continue
            
            baseline = self._feature_baselines[feature_id]
            old_mean = baseline["mean"]
            old_count = baseline["count"]
            
            # Update running statistics
            new_count = old_count + 1
            new_mean = old_mean + (value - old_mean) / new_count
            baseline["mean"] = new_mean
            baseline["count"] = new_count
            baseline["sum_sq"] += value ** 2
            
            # Calculate variance
            if new_count > 10:
                variance = (baseline["sum_sq"] / new_count) - (new_mean ** 2)
                std = variance ** 0.5 if variance > 0 else 0.01
                
                # Check if current value is significantly different
                z_score = abs(value - new_mean) / std if std > 0 else 0
                
                if z_score > 3:  # More than 3 standard deviations
                    severity = "high" if z_score > 5 else "medium"
                    alert = FeatureDriftAlert(
                        feature_id=feature_id,
                        drift_type="distribution",
                        severity=severity,
                        current_value=value,
                        expected_value=new_mean,
                    )
                    alerts.append(alert)
                    self._drift_alerts.append(alert)
        
        return alerts
    
    async def on_learning_signal_received(
        self,
        signal: LearningSignal,
    ) -> Optional[List[LearningSignal]]:
        """Process learning signals from other components."""
        
        if signal.signal_type == LearningSignalType.MECHANISM_EFFECTIVENESS_UPDATED:
            # Update feature priors based on mechanism effectiveness
            mechanism_id = signal.payload.get("mechanism_id")
            effectiveness = signal.payload.get("effectiveness", 0.5)
            
            # Features correlated with this mechanism should be boosted
            feature_id = f"mechanism_{mechanism_id}"
            if feature_id in self._feature_importance:
                self._feature_importance[feature_id].importance_score = (
                    self._feature_importance[feature_id].importance_score * 0.9 +
                    effectiveness * 0.1
                )
        
        return None
    
    def get_consumed_signal_types(self) -> Set[LearningSignalType]:
        return {
            LearningSignalType.MECHANISM_EFFECTIVENESS_UPDATED,
            LearningSignalType.PRIOR_UPDATED,
        }
    
    async def get_learning_contribution(
        self,
        decision_id: str,
    ) -> Optional[LearningContribution]:
        """Get feature store contribution to decision."""
        
        return LearningContribution(
            component_name=self.component_name,
            decision_id=decision_id,
            contribution_type="feature_serving",
            contribution_value={
                "features_tracked": len(self._feature_importance),
                "top_features": [
                    f.feature_id for f in sorted(
                        self._feature_importance.values(),
                        key=lambda x: x.importance_score,
                        reverse=True,
                    )[:5]
                ],
            },
            confidence=0.8,
            reasoning_summary="Served psychological and behavioral features",
            weight=0.15,
        )
    
    async def get_learning_quality_metrics(self) -> LearningQualityMetrics:
        """Get quality metrics."""
        
        return LearningQualityMetrics(
            component_name=self.component_name,
            signals_emitted=self._outcomes_processed // 100,
            outcomes_processed=self._outcomes_processed,
            prediction_accuracy=0.75,  # Would be computed from actual predictions
            attribution_coverage=len(self._feature_importance) / 100,  # Fraction of features tracked
            last_learning_update=datetime.now(timezone.utc),
            upstream_dependencies=["behavioral_analytics", "psychological_inference"],
            downstream_consumers=["meta_learner", "atom_of_thought"],
            integration_health=0.85 if self._outcomes_processed > 0 else 0.5,
        )
    
    async def inject_priors(self, user_id: str, priors: Dict[str, Any]) -> None:
        """Inject feature priors for a user."""
        
        for feature_id, prior_value in priors.items():
            if feature_id not in self._feature_importance:
                self._feature_importance[feature_id] = FeatureImportance(
                    feature_id=feature_id,
                )
            self._feature_importance[feature_id].importance_score = prior_value
    
    async def validate_learning_health(self) -> Tuple[bool, List[str]]:
        """Validate learning health."""
        
        issues = []
        
        if self._outcomes_processed == 0:
            issues.append("No outcomes processed yet")
        
        if len(self._drift_alerts) > 10:
            issues.append(f"{len(self._drift_alerts)} drift alerts in queue")
        
        # Check for stale features
        stale_count = sum(
            1 for f in self._feature_importance.values()
            if (datetime.now(timezone.utc) - f.last_updated).total_seconds() > 86400
        )
        if stale_count > len(self._feature_importance) * 0.5:
            issues.append(f"{stale_count} features are stale (not updated in 24h)")
        
        return len(issues) == 0, issues
    
    def get_feature_importance(self) -> List[FeatureImportance]:
        """Get learned feature importance, sorted by importance."""
        return sorted(
            self._feature_importance.values(),
            key=lambda f: f.importance_score,
            reverse=True,
        )
