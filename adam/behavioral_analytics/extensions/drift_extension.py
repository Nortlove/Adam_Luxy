# =============================================================================
# ADAM Behavioral Analytics: Drift Detection Extension
# Location: adam/behavioral_analytics/extensions/drift_extension.py
# =============================================================================

"""
DRIFT DETECTION EXTENSION FOR BEHAVIORAL ANALYTICS

Extends the existing Drift Detection (#20) infrastructure with
behavioral-specific drift monitoring.

This extends rather than recreates - uses existing:
- DriftDetectionService
- DriftType enum (adds new types)
- DriftAlert structure
- Prometheus metrics
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from enum import Enum
import logging

from adam.monitoring.drift_detection import (
    DriftType,
    DriftSeverity,
    DriftAlert,
    DriftDetectionService,
)

try:
    from prometheus_client import Counter, Gauge, Histogram
    
    BEHAVIORAL_DRIFT_SCORE = Gauge(
        'adam_behavioral_drift_score',
        'Current behavioral signal drift score',
        ['signal_type']
    )
    BEHAVIORAL_FEATURE_DISTRIBUTION = Histogram(
        'adam_behavioral_feature_distribution',
        'Distribution of behavioral features',
        ['feature_name'],
        buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
    )
    BEHAVIORAL_SESSION_QUALITY = Gauge(
        'adam_behavioral_session_quality',
        'Quality score of behavioral sessions',
        ['device_type']
    )
    BEHAVIORAL_PREDICTIONS_TOTAL = Counter(
        'adam_behavioral_predictions_total',
        'Total behavioral predictions',
        ['prediction_type', 'outcome']
    )
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False

logger = logging.getLogger(__name__)


class BehavioralDriftType(str, Enum):
    """
    Behavioral-specific drift types.
    
    These extend the base DriftType enum with behavioral signal monitoring.
    """
    # Signal-level drift
    TOUCH_PRESSURE_DRIFT = "touch_pressure_drift"
    RESPONSE_LATENCY_DRIFT = "response_latency_drift"
    SWIPE_PATTERN_DRIFT = "swipe_pattern_drift"
    SCROLL_BEHAVIOR_DRIFT = "scroll_behavior_drift"
    SENSOR_PATTERN_DRIFT = "sensor_pattern_drift"
    
    # Model-level drift
    PURCHASE_INTENT_MODEL_DRIFT = "purchase_intent_model_drift"
    EMOTION_MODEL_DRIFT = "emotion_model_drift"
    PERSONALITY_MODEL_DRIFT = "personality_model_drift"
    
    # Population-level drift
    USER_BEHAVIOR_POPULATION_DRIFT = "user_behavior_population_drift"
    DEVICE_BEHAVIOR_DRIFT = "device_behavior_drift"


class BehavioralDriftDetector:
    """
    Behavioral signal drift detection.
    
    Extends DriftDetectionService with behavioral-specific monitoring.
    
    Monitors:
    1. Touch pressure distribution drift
    2. Response latency distribution drift
    3. Swipe pattern changes
    4. Behavioral model performance drift
    5. Population-level behavior shifts
    """
    
    # Behavioral-specific thresholds
    BEHAVIORAL_THRESHOLDS = {
        BehavioralDriftType.TOUCH_PRESSURE_DRIFT: 0.20,
        BehavioralDriftType.RESPONSE_LATENCY_DRIFT: 0.25,
        BehavioralDriftType.SWIPE_PATTERN_DRIFT: 0.20,
        BehavioralDriftType.SCROLL_BEHAVIOR_DRIFT: 0.25,
        BehavioralDriftType.SENSOR_PATTERN_DRIFT: 0.30,
        BehavioralDriftType.PURCHASE_INTENT_MODEL_DRIFT: 0.15,
        BehavioralDriftType.EMOTION_MODEL_DRIFT: 0.20,
        BehavioralDriftType.PERSONALITY_MODEL_DRIFT: 0.30,
        BehavioralDriftType.USER_BEHAVIOR_POPULATION_DRIFT: 0.20,
        BehavioralDriftType.DEVICE_BEHAVIOR_DRIFT: 0.25,
    }
    
    def __init__(
        self,
        base_detector: Optional[DriftDetectionService] = None,
        window_size: int = 1000,
    ):
        self._base_detector = base_detector or DriftDetectionService(
            window_size=window_size
        )
        self._window_size = window_size
        
        # Behavioral-specific windows
        self._behavioral_windows: Dict[BehavioralDriftType, Dict] = {
            dt: {"reference": [], "current": []} for dt in BehavioralDriftType
        }
        
        # Thresholds
        self._thresholds = dict(self.BEHAVIORAL_THRESHOLDS)
        
        # Feature baselines (learned from data)
        self._feature_baselines: Dict[str, Dict[str, float]] = {}
        
        logger.info("BehavioralDriftDetector initialized")
    
    def record_behavioral_observation(
        self,
        drift_type: BehavioralDriftType,
        value: float,
        feature_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Record a behavioral observation for drift monitoring.
        
        Args:
            drift_type: Type of behavioral drift to monitor
            value: Observation value
            feature_name: Optional feature name for detailed tracking
            metadata: Optional metadata
        """
        # Add to behavioral window
        window = self._behavioral_windows[drift_type]["current"]
        window.append(value)
        
        # Trim to window size
        if len(window) > self._window_size:
            window.pop(0)
        
        # Track feature distribution
        if feature_name and PROMETHEUS_AVAILABLE:
            BEHAVIORAL_FEATURE_DISTRIBUTION.labels(
                feature_name=feature_name
            ).observe(value)
        
        # Also record to base detector for unified monitoring
        self._base_detector.record_observation(
            DriftType.INPUT_DISTRIBUTION,
            value,
            {"behavioral_type": drift_type.value}
        )
    
    def set_behavioral_reference(
        self,
        drift_type: BehavioralDriftType,
        values: List[float],
    ) -> None:
        """
        Set reference distribution for behavioral drift comparison.
        
        Args:
            drift_type: Drift type
            values: Reference values
        """
        self._behavioral_windows[drift_type]["reference"] = list(values)[-self._window_size:]
    
    def record_session_features(
        self,
        session_features: Dict[str, float],
        device_type: str = "mobile",
    ) -> None:
        """
        Record behavioral features from a session.
        
        Maps features to appropriate drift types for monitoring.
        """
        feature_mapping = {
            "pressure_mean": BehavioralDriftType.TOUCH_PRESSURE_DRIFT,
            "pressure_std": BehavioralDriftType.TOUCH_PRESSURE_DRIFT,
            "response_latency_mean": BehavioralDriftType.RESPONSE_LATENCY_DRIFT,
            "response_latency_p50": BehavioralDriftType.RESPONSE_LATENCY_DRIFT,
            "velocity_mean": BehavioralDriftType.SWIPE_PATTERN_DRIFT,
            "directness_mean": BehavioralDriftType.SWIPE_PATTERN_DRIFT,
            "scroll_velocity_mean": BehavioralDriftType.SCROLL_BEHAVIOR_DRIFT,
            "magnitude_mean": BehavioralDriftType.SENSOR_PATTERN_DRIFT,
            "magnitude_std": BehavioralDriftType.SENSOR_PATTERN_DRIFT,
        }
        
        for feature_name, value in session_features.items():
            if feature_name in feature_mapping:
                drift_type = feature_mapping[feature_name]
                self.record_behavioral_observation(
                    drift_type,
                    value,
                    feature_name=feature_name
                )
        
        # Track session quality
        quality_score = self._calculate_session_quality(session_features)
        if PROMETHEUS_AVAILABLE:
            BEHAVIORAL_SESSION_QUALITY.labels(device_type=device_type).set(quality_score)
    
    def record_prediction_outcome(
        self,
        prediction_type: str,
        predicted: float,
        actual: float,
    ) -> None:
        """
        Record a prediction outcome for model drift monitoring.
        
        Args:
            prediction_type: Type of prediction (purchase_intent, emotion, etc.)
            predicted: Predicted value
            actual: Actual outcome
        """
        # Calculate prediction error
        error = abs(predicted - actual)
        
        # Map to drift type
        type_mapping = {
            "purchase_intent": BehavioralDriftType.PURCHASE_INTENT_MODEL_DRIFT,
            "emotional_arousal": BehavioralDriftType.EMOTION_MODEL_DRIFT,
            "personality": BehavioralDriftType.PERSONALITY_MODEL_DRIFT,
        }
        
        if prediction_type in type_mapping:
            drift_type = type_mapping[prediction_type]
            self.record_behavioral_observation(drift_type, error)
        
        # Track metrics
        if PROMETHEUS_AVAILABLE:
            outcome = "correct" if error < 0.2 else "incorrect"
            BEHAVIORAL_PREDICTIONS_TOTAL.labels(
                prediction_type=prediction_type,
                outcome=outcome
            ).inc()
    
    def check_behavioral_drift(
        self,
        drift_type: Optional[BehavioralDriftType] = None,
    ) -> List[DriftAlert]:
        """
        Check for behavioral drift and generate alerts.
        
        Args:
            drift_type: Optional specific type to check (all if None)
            
        Returns:
            List of new alerts
        """
        types_to_check = [drift_type] if drift_type else list(BehavioralDriftType)
        alerts = []
        
        for dt in types_to_check:
            windows = self._behavioral_windows[dt]
            reference = windows["reference"]
            current = windows["current"]
            
            if not reference or not current:
                continue
            
            # Calculate drift score
            score = self._calculate_drift_score(reference, current)
            threshold = self._thresholds.get(dt, 0.20)
            
            # Update metrics
            if PROMETHEUS_AVAILABLE:
                BEHAVIORAL_DRIFT_SCORE.labels(signal_type=dt.value).set(score)
            
            if score > threshold:
                severity = self._determine_severity(score, threshold)
                alert = self._create_alert(dt, score, threshold, severity)
                alerts.append(alert)
                
                logger.warning(
                    f"Behavioral drift detected: {dt.value}",
                    extra={
                        "score": score,
                        "threshold": threshold,
                        "severity": severity.value
                    }
                )
        
        return alerts
    
    def _calculate_drift_score(
        self,
        reference: List[float],
        current: List[float],
    ) -> float:
        """
        Calculate drift score using statistical distance.
        
        Uses normalized mean difference with variance adjustment.
        """
        if not reference or not current:
            return 0.0
        
        ref_mean = sum(reference) / len(reference)
        cur_mean = sum(current) / len(current)
        
        if ref_mean == 0:
            return min(1.0, abs(cur_mean))
        
        # Mean-based drift
        mean_drift = abs(cur_mean - ref_mean) / abs(ref_mean)
        
        # Variance-based drift (optional)
        ref_var = self._variance(reference)
        cur_var = self._variance(current)
        
        if ref_var > 0:
            var_drift = abs(cur_var - ref_var) / ref_var
        else:
            var_drift = 0.0
        
        # Combined score
        return min(1.0, 0.7 * mean_drift + 0.3 * var_drift)
    
    def _variance(self, values: List[float]) -> float:
        """Calculate variance."""
        if len(values) < 2:
            return 0.0
        mean = sum(values) / len(values)
        return sum((x - mean) ** 2 for x in values) / (len(values) - 1)
    
    def _determine_severity(self, score: float, threshold: float) -> DriftSeverity:
        """Determine alert severity based on score."""
        if score > threshold * 3:
            return DriftSeverity.CRITICAL
        elif score > threshold * 1.5:
            return DriftSeverity.WARNING
        else:
            return DriftSeverity.INFO
    
    def _create_alert(
        self,
        drift_type: BehavioralDriftType,
        score: float,
        threshold: float,
        severity: DriftSeverity,
    ) -> DriftAlert:
        """Create behavioral drift alert."""
        import uuid
        
        return DriftAlert(
            alert_id=f"behavioral_drift_{uuid.uuid4().hex[:8]}",
            drift_type=DriftType.INPUT_DISTRIBUTION,  # Map to base type
            severity=severity,
            score=score,
            threshold=threshold,
            message=f"Behavioral {drift_type.value}: {score:.2%} (threshold: {threshold:.2%})",
            details={
                "behavioral_drift_type": drift_type.value,
                "current_window_size": len(self._behavioral_windows[drift_type]["current"]),
                "reference_window_size": len(self._behavioral_windows[drift_type]["reference"]),
            },
        )
    
    def _calculate_session_quality(
        self,
        features: Dict[str, float],
    ) -> float:
        """Calculate quality score for a behavioral session."""
        quality = 0.5  # Base
        
        # Boost for rich signals
        if "touch_count" in features and features["touch_count"] > 10:
            quality += 0.1
        if "swipe_count" in features and features["swipe_count"] > 5:
            quality += 0.1
        if "scroll_event_count" in features and features["scroll_event_count"] > 10:
            quality += 0.1
        if "sample_count" in features and features["sample_count"] > 100:
            quality += 0.1
        
        # Reduce for sparse data
        feature_count = len(features)
        if feature_count < 5:
            quality -= 0.2
        
        return max(0.0, min(1.0, quality))
    
    def get_behavioral_health(self) -> Dict[str, Any]:
        """Get behavioral monitoring health status."""
        health = {
            "status": "healthy",
            "drift_scores": {},
            "alerts": [],
        }
        
        max_score = 0.0
        for dt in BehavioralDriftType:
            windows = self._behavioral_windows[dt]
            if windows["reference"] and windows["current"]:
                score = self._calculate_drift_score(
                    windows["reference"],
                    windows["current"]
                )
                health["drift_scores"][dt.value] = score
                max_score = max(max_score, score)
        
        if max_score > 0.5:
            health["status"] = "unhealthy"
        elif max_score > 0.25:
            health["status"] = "degraded"
        
        return health


# Singleton
_detector: Optional[BehavioralDriftDetector] = None


def get_behavioral_drift_detector(
    base_detector: Optional[DriftDetectionService] = None
) -> BehavioralDriftDetector:
    """Get singleton behavioral drift detector."""
    global _detector
    if _detector is None:
        _detector = BehavioralDriftDetector(base_detector)
    return _detector
