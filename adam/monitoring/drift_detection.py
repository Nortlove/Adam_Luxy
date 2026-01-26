# =============================================================================
# ADAM Drift Detection Service (#20)
# Location: adam/monitoring/drift_detection.py
# =============================================================================

"""
MODEL MONITORING & DRIFT DETECTION

Enhancement #20: Multi-source intelligence observability.

Detects 8 types of drift:
1. Input distribution drift
2. Prediction distribution drift
3. Performance metric drift
4. Intelligence source drift
5. Psychological construct drift
6. Fusion quality drift
7. Learning signal drift
8. Adversarial pattern drift
"""

import time
from collections import deque
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

try:
    import structlog
    logger = structlog.get_logger(__name__)
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

try:
    from prometheus_client import Counter, Gauge, Histogram
    DRIFT_DETECTED = Counter(
        'adam_drift_detected_total',
        'Drift detections',
        ['drift_type', 'severity']
    )
    DRIFT_SCORE = Gauge(
        'adam_drift_score',
        'Current drift score',
        ['drift_type']
    )
    MONITORING_LATENCY = Histogram(
        'adam_monitoring_check_seconds',
        'Time to run drift check',
        ['check_type']
    )
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False


class DriftType(str, Enum):
    """Types of drift to monitor."""
    INPUT_DISTRIBUTION = "input_distribution"
    PREDICTION_DISTRIBUTION = "prediction_distribution"
    PERFORMANCE_METRIC = "performance_metric"
    INTELLIGENCE_SOURCE = "intelligence_source"
    PSYCHOLOGICAL_CONSTRUCT = "psychological_construct"
    FUSION_QUALITY = "fusion_quality"
    LEARNING_SIGNAL = "learning_signal"
    ADVERSARIAL_PATTERN = "adversarial_pattern"


class DriftSeverity(str, Enum):
    """Severity levels for drift alerts."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class DriftAlert:
    """Alert for detected drift."""
    alert_id: str
    drift_type: DriftType
    severity: DriftSeverity
    
    score: float  # 0-1, higher = more drift
    threshold: float
    
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    
    detected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    acknowledged: bool = False


@dataclass
class DriftSnapshot:
    """Point-in-time drift measurements."""
    timestamp: datetime
    
    # Drift scores by type
    scores: Dict[DriftType, float] = field(default_factory=dict)
    
    # Active alerts
    alerts: List[DriftAlert] = field(default_factory=list)
    
    # Health status
    overall_health: str = "healthy"  # healthy, degraded, unhealthy


class DriftDetectionService:
    """
    Multi-source drift detection service.
    
    Enhancement #20: Model monitoring and psychological drift detection.
    
    Monitors 8 drift dimensions:
    - Input/output distributions
    - Performance metrics
    - Intelligence source quality
    - Psychological construct stability
    - Fusion quality
    - Learning signal health
    - Adversarial patterns
    
    Emits Alerts:
    - DRIFT_DETECTED: When drift exceeds threshold
    
    Metrics:
    - adam_drift_detected_total
    - adam_drift_score
    """
    
    # Default thresholds
    DEFAULT_THRESHOLDS = {
        DriftType.INPUT_DISTRIBUTION: 0.15,
        DriftType.PREDICTION_DISTRIBUTION: 0.10,
        DriftType.PERFORMANCE_METRIC: 0.20,
        DriftType.INTELLIGENCE_SOURCE: 0.25,
        DriftType.PSYCHOLOGICAL_CONSTRUCT: 0.15,
        DriftType.FUSION_QUALITY: 0.20,
        DriftType.LEARNING_SIGNAL: 0.25,
        DriftType.ADVERSARIAL_PATTERN: 0.05,
    }
    
    def __init__(
        self,
        gradient_bridge=None,
        window_size: int = 1000,
        check_interval_seconds: float = 60.0,
    ):
        self._gradient_bridge = gradient_bridge
        self._window_size = window_size
        self._check_interval = check_interval_seconds
        
        # Sliding windows for each drift type
        self._reference_windows: Dict[DriftType, deque] = {
            dt: deque(maxlen=window_size) for dt in DriftType
        }
        self._current_windows: Dict[DriftType, deque] = {
            dt: deque(maxlen=window_size) for dt in DriftType
        }
        
        # Thresholds
        self._thresholds = dict(self.DEFAULT_THRESHOLDS)
        
        # Alert history
        self._alerts: List[DriftAlert] = []
        self._alert_counter = 0
        
        # Last check time
        self._last_check: Dict[DriftType, float] = {}
        
        logger.info("DriftDetectionService initialized")
    
    def record_observation(
        self,
        drift_type: DriftType,
        value: float,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Record observation for drift monitoring.
        
        Args:
            drift_type: Type of observation
            value: Observation value
            metadata: Optional metadata
        """
        self._current_windows[drift_type].append(value)
    
    def set_reference(
        self,
        drift_type: DriftType,
        values: List[float],
    ) -> None:
        """
        Set reference distribution for drift comparison.
        
        Args:
            drift_type: Drift type
            values: Reference values
        """
        self._reference_windows[drift_type] = deque(values, maxlen=self._window_size)
    
    def check_drift(
        self,
        drift_type: Optional[DriftType] = None,
    ) -> List[DriftAlert]:
        """
        Check for drift and generate alerts.
        
        Args:
            drift_type: Optional specific type to check (all if None)
            
        Returns:
            List of new alerts
        """
        start = time.monotonic()
        
        types_to_check = [drift_type] if drift_type else list(DriftType)
        new_alerts = []
        
        for dt in types_to_check:
            score = self._calculate_drift_score(dt)
            threshold = self._thresholds.get(dt, 0.15)
            
            # Update metrics
            if PROMETHEUS_AVAILABLE:
                DRIFT_SCORE.labels(drift_type=dt.value).set(score)
            
            if score > threshold:
                severity = self._determine_severity(score, threshold)
                
                alert = self._create_alert(dt, score, threshold, severity)
                new_alerts.append(alert)
                self._alerts.append(alert)
                
                # Track metrics
                if PROMETHEUS_AVAILABLE:
                    DRIFT_DETECTED.labels(
                        drift_type=dt.value,
                        severity=severity.value
                    ).inc()
                
                logger.warning(
                    "drift_detected",
                    drift_type=dt.value,
                    score=score,
                    threshold=threshold,
                    severity=severity.value
                )
        
        # Track latency
        elapsed = time.monotonic() - start
        if PROMETHEUS_AVAILABLE:
            MONITORING_LATENCY.labels(check_type="drift").observe(elapsed)
        
        return new_alerts
    
    def _calculate_drift_score(self, drift_type: DriftType) -> float:
        """
        Calculate drift score using statistical distance.
        
        Uses Population Stability Index (PSI) approach.
        """
        reference = list(self._reference_windows.get(drift_type, []))
        current = list(self._current_windows.get(drift_type, []))
        
        if not reference or not current:
            return 0.0
        
        # Simple mean difference approach
        # In production, use PSI or KL divergence
        ref_mean = sum(reference) / len(reference)
        cur_mean = sum(current) / len(current)
        
        if ref_mean == 0:
            return abs(cur_mean)
        
        relative_change = abs(cur_mean - ref_mean) / abs(ref_mean)
        return min(1.0, relative_change)
    
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
        drift_type: DriftType,
        score: float,
        threshold: float,
        severity: DriftSeverity,
    ) -> DriftAlert:
        """Create drift alert."""
        self._alert_counter += 1
        
        return DriftAlert(
            alert_id=f"drift_{self._alert_counter:05d}",
            drift_type=drift_type,
            severity=severity,
            score=score,
            threshold=threshold,
            message=f"{drift_type.value} drift detected: {score:.2%} (threshold: {threshold:.2%})",
            details={
                "current_window_size": len(self._current_windows[drift_type]),
                "reference_window_size": len(self._reference_windows.get(drift_type, [])),
            },
        )
    
    def get_snapshot(self) -> DriftSnapshot:
        """
        Get current drift status snapshot.
        
        Returns:
            DriftSnapshot with all drift scores and alerts
        """
        scores = {}
        for dt in DriftType:
            scores[dt] = self._calculate_drift_score(dt)
        
        # Determine overall health
        max_score = max(scores.values()) if scores else 0.0
        if max_score > 0.5:
            health = "unhealthy"
        elif max_score > 0.2:
            health = "degraded"
        else:
            health = "healthy"
        
        # Get recent alerts
        recent_cutoff = datetime.now(timezone.utc) - timedelta(hours=1)
        recent_alerts = [
            a for a in self._alerts
            if a.detected_at > recent_cutoff and not a.acknowledged
        ]
        
        return DriftSnapshot(
            timestamp=datetime.now(timezone.utc),
            scores=scores,
            alerts=recent_alerts,
            overall_health=health,
        )
    
    def acknowledge_alert(self, alert_id: str) -> bool:
        """Acknowledge an alert."""
        for alert in self._alerts:
            if alert.alert_id == alert_id:
                alert.acknowledged = True
                return True
        return False
    
    def set_threshold(self, drift_type: DriftType, threshold: float) -> None:
        """Set custom threshold for drift type."""
        self._thresholds[drift_type] = threshold
    
    def get_health(self) -> Dict[str, Any]:
        """Get service health status."""
        snapshot = self.get_snapshot()
        return {
            "status": snapshot.overall_health,
            "drift_scores": {dt.value: s for dt, s in snapshot.scores.items()},
            "active_alerts": len([a for a in snapshot.alerts if not a.acknowledged]),
        }
