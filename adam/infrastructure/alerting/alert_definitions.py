# =============================================================================
# ADAM Alert Definitions
# Location: adam/infrastructure/alerting/alert_definitions.py
# =============================================================================

"""
ALERT DEFINITIONS

Defines the conditions that trigger alerts in ADAM.

Each alert has:
- Name: Unique identifier
- Condition: When to fire
- Severity: critical, warning, info
- Description: Human-readable explanation
- Runbook: Link to remediation steps
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from datetime import timedelta


class AlertSeverity(str, Enum):
    """Alert severity levels."""
    CRITICAL = "critical"  # Requires immediate attention
    WARNING = "warning"    # Should be investigated soon
    INFO = "info"          # Informational, no action needed


class AlertCondition(str, Enum):
    """Types of alert conditions."""
    THRESHOLD_ABOVE = "threshold_above"
    THRESHOLD_BELOW = "threshold_below"
    RATE_OF_CHANGE = "rate_of_change"
    ABSENCE = "absence"  # No data received
    CUSTOM = "custom"


@dataclass
class AlertDefinition:
    """
    Definition of an alert condition.
    
    Attributes:
        name: Unique alert name (e.g., "DecisionLatencyHigh")
        description: Human-readable description
        severity: Alert severity level
        condition: Type of condition
        metric_name: Prometheus metric to evaluate
        threshold: Threshold value for comparison
        duration_seconds: How long condition must persist
        labels: Metric labels to filter on
        runbook_url: Link to remediation documentation
        notify_channels: Which channels to notify
        cooldown_seconds: Minimum time between alerts
    """
    name: str
    description: str
    severity: AlertSeverity
    condition: AlertCondition
    metric_name: str
    threshold: float
    duration_seconds: int = 300  # 5 minutes default
    labels: Dict[str, str] = field(default_factory=dict)
    runbook_url: Optional[str] = None
    notify_channels: List[str] = field(default_factory=lambda: ["default"])
    cooldown_seconds: int = 600  # 10 minutes default
    custom_evaluator: Optional[Callable[[Dict[str, Any]], bool]] = None
    
    def __post_init__(self):
        """Validate alert definition."""
        if self.condition == AlertCondition.CUSTOM and not self.custom_evaluator:
            raise ValueError(f"Alert {self.name}: CUSTOM condition requires custom_evaluator")


# =============================================================================
# ADAM ALERT DEFINITIONS
# =============================================================================

ADAM_ALERTS: List[AlertDefinition] = [
    # -------------------------------------------------------------------------
    # DECISION LATENCY ALERTS
    # -------------------------------------------------------------------------
    AlertDefinition(
        name="DecisionLatencyWarning",
        description="Decision latency p99 is elevated (>200ms)",
        severity=AlertSeverity.WARNING,
        condition=AlertCondition.THRESHOLD_ABOVE,
        metric_name="adam_decision_latency_seconds",
        threshold=0.200,  # 200ms
        duration_seconds=300,
        runbook_url="/docs/runbooks/decision-latency.md",
    ),
    AlertDefinition(
        name="DecisionLatencyCritical",
        description="Decision latency p99 is critically high (>500ms)",
        severity=AlertSeverity.CRITICAL,
        condition=AlertCondition.THRESHOLD_ABOVE,
        metric_name="adam_decision_latency_seconds",
        threshold=0.500,  # 500ms
        duration_seconds=300,
        runbook_url="/docs/runbooks/decision-latency.md",
    ),
    
    # -------------------------------------------------------------------------
    # LEARNING LOOP ALERTS
    # -------------------------------------------------------------------------
    AlertDefinition(
        name="LearningLoopStalled",
        description="No learning signals received for 10 minutes",
        severity=AlertSeverity.CRITICAL,
        condition=AlertCondition.ABSENCE,
        metric_name="adam_learning_signals_total",
        threshold=0,
        duration_seconds=600,
        runbook_url="/docs/runbooks/learning-loop.md",
    ),
    AlertDefinition(
        name="OutcomeAttributionLow",
        description="Outcome attribution rate dropped below 80%",
        severity=AlertSeverity.WARNING,
        condition=AlertCondition.THRESHOLD_BELOW,
        metric_name="adam_outcome_attribution_rate",
        threshold=0.80,
        duration_seconds=900,
        runbook_url="/docs/runbooks/learning-loop.md",
    ),
    
    # -------------------------------------------------------------------------
    # MECHANISM EFFECTIVENESS ALERTS
    # -------------------------------------------------------------------------
    AlertDefinition(
        name="MechanismEffectivenessDrop",
        description="Mechanism effectiveness dropped below 30%",
        severity=AlertSeverity.WARNING,
        condition=AlertCondition.THRESHOLD_BELOW,
        metric_name="adam_mechanism_effectiveness",
        threshold=0.30,
        duration_seconds=1800,  # 30 minutes
        runbook_url="/docs/runbooks/mechanism-effectiveness.md",
    ),
    AlertDefinition(
        name="AllMechanismsUnderperforming",
        description="All mechanisms below 40% effectiveness",
        severity=AlertSeverity.CRITICAL,
        condition=AlertCondition.THRESHOLD_BELOW,
        metric_name="adam_mechanism_effectiveness_avg",
        threshold=0.40,
        duration_seconds=1800,
        runbook_url="/docs/runbooks/mechanism-effectiveness.md",
    ),
    
    # -------------------------------------------------------------------------
    # DEPENDENCY HEALTH ALERTS
    # -------------------------------------------------------------------------
    AlertDefinition(
        name="Neo4jUnavailable",
        description="Neo4j connection failed",
        severity=AlertSeverity.CRITICAL,
        condition=AlertCondition.THRESHOLD_BELOW,
        metric_name="adam_dependency_status",
        threshold=1,
        duration_seconds=60,
        labels={"dependency_name": "neo4j"},
        runbook_url="/docs/runbooks/neo4j.md",
    ),
    AlertDefinition(
        name="RedisUnavailable",
        description="Redis connection failed",
        severity=AlertSeverity.CRITICAL,
        condition=AlertCondition.THRESHOLD_BELOW,
        metric_name="adam_dependency_status",
        threshold=1,
        duration_seconds=60,
        labels={"dependency_name": "redis"},
        runbook_url="/docs/runbooks/redis.md",
    ),
    AlertDefinition(
        name="KafkaUnavailable",
        description="Kafka connection failed",
        severity=AlertSeverity.WARNING,
        condition=AlertCondition.THRESHOLD_BELOW,
        metric_name="adam_dependency_status",
        threshold=1,
        duration_seconds=120,
        labels={"dependency_name": "kafka"},
        runbook_url="/docs/runbooks/kafka.md",
    ),
    
    # -------------------------------------------------------------------------
    # CACHE PERFORMANCE ALERTS
    # -------------------------------------------------------------------------
    AlertDefinition(
        name="CacheHitRateLow",
        description="Cache hit rate dropped below 50%",
        severity=AlertSeverity.WARNING,
        condition=AlertCondition.THRESHOLD_BELOW,
        metric_name="adam_cache_hit_rate",
        threshold=0.50,
        duration_seconds=300,
        runbook_url="/docs/runbooks/cache.md",
    ),
    
    # -------------------------------------------------------------------------
    # MODEL DRIFT ALERTS
    # -------------------------------------------------------------------------
    AlertDefinition(
        name="ModelDriftDetected",
        description="Model drift score exceeded threshold",
        severity=AlertSeverity.WARNING,
        condition=AlertCondition.THRESHOLD_ABOVE,
        metric_name="adam_drift_score",
        threshold=0.30,
        duration_seconds=3600,  # 1 hour
        runbook_url="/docs/runbooks/drift.md",
    ),
    AlertDefinition(
        name="SevereDriftDetected",
        description="Severe model drift detected (>0.5)",
        severity=AlertSeverity.CRITICAL,
        condition=AlertCondition.THRESHOLD_ABOVE,
        metric_name="adam_drift_score",
        threshold=0.50,
        duration_seconds=1800,
        runbook_url="/docs/runbooks/drift.md",
    ),
    
    # -------------------------------------------------------------------------
    # THROUGHPUT ALERTS
    # -------------------------------------------------------------------------
    AlertDefinition(
        name="DecisionThroughputDrop",
        description="Decision throughput dropped >50% from baseline",
        severity=AlertSeverity.WARNING,
        condition=AlertCondition.RATE_OF_CHANGE,
        metric_name="adam_decisions_total",
        threshold=-0.50,  # 50% drop
        duration_seconds=300,
        runbook_url="/docs/runbooks/throughput.md",
    ),
    
    # -------------------------------------------------------------------------
    # ERROR RATE ALERTS
    # -------------------------------------------------------------------------
    AlertDefinition(
        name="HighErrorRate",
        description="Error rate exceeded 5%",
        severity=AlertSeverity.WARNING,
        condition=AlertCondition.THRESHOLD_ABOVE,
        metric_name="adam_error_rate",
        threshold=0.05,
        duration_seconds=300,
        runbook_url="/docs/runbooks/errors.md",
    ),
    AlertDefinition(
        name="CriticalErrorRate",
        description="Error rate exceeded 20%",
        severity=AlertSeverity.CRITICAL,
        condition=AlertCondition.THRESHOLD_ABOVE,
        metric_name="adam_error_rate",
        threshold=0.20,
        duration_seconds=120,
        runbook_url="/docs/runbooks/errors.md",
    ),
]


def get_alert_by_name(name: str) -> Optional[AlertDefinition]:
    """Get an alert definition by name."""
    for alert in ADAM_ALERTS:
        if alert.name == name:
            return alert
    return None


def get_alerts_by_severity(severity: AlertSeverity) -> List[AlertDefinition]:
    """Get all alerts of a given severity."""
    return [a for a in ADAM_ALERTS if a.severity == severity]


def get_critical_alerts() -> List[AlertDefinition]:
    """Get all critical alerts."""
    return get_alerts_by_severity(AlertSeverity.CRITICAL)
