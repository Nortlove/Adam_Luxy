# =============================================================================
# ADAM Alert Manager
# Location: adam/infrastructure/alerting/manager.py
# =============================================================================

"""
ALERT MANAGER

Evaluates alert conditions and manages alert lifecycle.

Responsibilities:
1. Evaluate alert conditions against metrics
2. Track alert state (pending, firing, resolved)
3. Prevent alert storms (cooldown, grouping)
4. Route alerts to appropriate notifiers
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set
import json

from adam.infrastructure.alerting.alert_definitions import (
    AlertDefinition,
    AlertCondition,
    AlertSeverity,
    ADAM_ALERTS,
)

logger = logging.getLogger(__name__)

try:
    from prometheus_client import Counter, Gauge, Histogram, REGISTRY
    
    def _get_or_create_counter(name: str, description: str, labelnames=None) -> Counter:
        """Get existing counter or create new one."""
        try:
            if labelnames:
                return Counter(name, description, labelnames)
            return Counter(name, description)
        except ValueError:
            return REGISTRY._names_to_collectors.get(name)
    
    def _get_or_create_gauge(name: str, description: str, labelnames=None) -> Gauge:
        """Get existing gauge or create new one."""
        try:
            if labelnames:
                return Gauge(name, description, labelnames)
            return Gauge(name, description)
        except ValueError:
            return REGISTRY._names_to_collectors.get(name)
    
    ALERTS_FIRED = _get_or_create_counter(
        'adam_alerts_fired_total',
        'Total number of alerts fired',
        ['alert_name', 'severity']
    )
    ALERTS_RESOLVED = _get_or_create_counter(
        'adam_alerts_resolved_total',
        'Total number of alerts resolved',
        ['alert_name', 'severity']
    )
    ACTIVE_ALERTS = _get_or_create_gauge(
        'adam_active_alerts',
        'Number of currently active alerts',
        ['severity']
    )
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False


class AlertState(str, Enum):
    """State of an alert."""
    PENDING = "pending"    # Condition met but duration not exceeded
    FIRING = "firing"      # Alert is active
    RESOLVED = "resolved"  # Condition no longer met


@dataclass
class ActiveAlert:
    """An active or recently resolved alert."""
    definition: AlertDefinition
    state: AlertState
    first_triggered: datetime
    last_triggered: datetime
    last_value: float
    labels: Dict[str, str] = field(default_factory=dict)
    resolved_at: Optional[datetime] = None
    notification_count: int = 0
    
    @property
    def duration(self) -> timedelta:
        """How long the alert has been active."""
        end = self.resolved_at or datetime.now(timezone.utc)
        return end - self.first_triggered
    
    @property
    def is_firing(self) -> bool:
        """Check if alert is currently firing."""
        return self.state == AlertState.FIRING
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "name": self.definition.name,
            "description": self.definition.description,
            "severity": self.definition.severity.value,
            "state": self.state.value,
            "first_triggered": self.first_triggered.isoformat(),
            "last_triggered": self.last_triggered.isoformat(),
            "last_value": self.last_value,
            "labels": self.labels,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "duration_seconds": self.duration.total_seconds(),
            "runbook_url": self.definition.runbook_url,
        }


class AlertManager:
    """
    Manages alert evaluation and notification.
    
    The AlertManager:
    1. Periodically evaluates all alert conditions
    2. Maintains state for active alerts
    3. Routes alerts to configured notifiers
    4. Implements cooldown to prevent spam
    """
    
    def __init__(
        self,
        metrics_provider: Optional[Callable[[str, Dict[str, str]], float]] = None,
        check_interval_seconds: int = 30,
    ):
        """
        Initialize the alert manager.
        
        Args:
            metrics_provider: Function to get metric values
            check_interval_seconds: How often to evaluate alerts
        """
        self._metrics_provider = metrics_provider or self._default_metrics_provider
        self._check_interval = check_interval_seconds
        
        # Alert state
        self._active_alerts: Dict[str, ActiveAlert] = {}
        self._pending_alerts: Dict[str, datetime] = {}  # name -> first_seen
        self._cooldowns: Dict[str, datetime] = {}  # name -> last_notified
        
        # Notifiers
        self._notifiers: List[Any] = []
        
        # Background task
        self._monitoring_task: Optional[asyncio.Task] = None
        
        # Alert history (recent)
        self._alert_history: List[ActiveAlert] = []
        self._max_history = 100
    
    def add_notifier(self, notifier: Any) -> None:
        """Add a notifier to receive alerts."""
        self._notifiers.append(notifier)
        logger.info(f"Added notifier: {notifier.__class__.__name__}")
    
    def _default_metrics_provider(
        self,
        metric_name: str,
        labels: Dict[str, str],
    ) -> Optional[float]:
        """
        Default metrics provider using Prometheus client.
        
        Override this for testing or custom metrics sources.
        """
        # In production, this would query Prometheus
        # For now, return None to skip evaluation
        return None
    
    async def evaluate_alert(
        self,
        alert_def: AlertDefinition,
    ) -> Optional[ActiveAlert]:
        """
        Evaluate a single alert condition.
        
        Returns:
            ActiveAlert if condition is met, None otherwise
        """
        # Get metric value
        value = self._metrics_provider(alert_def.metric_name, alert_def.labels)
        
        if value is None:
            # No data available
            if alert_def.condition == AlertCondition.ABSENCE:
                # Absence of data triggers the alert
                condition_met = True
                value = 0.0
            else:
                return None
        else:
            # Evaluate condition
            condition_met = self._evaluate_condition(alert_def, value)
        
        now = datetime.now(timezone.utc)
        alert_key = f"{alert_def.name}:{json.dumps(alert_def.labels, sort_keys=True)}"
        
        if condition_met:
            # Check if already tracking this alert
            if alert_key in self._pending_alerts:
                first_seen = self._pending_alerts[alert_key]
                duration = (now - first_seen).total_seconds()
                
                if duration >= alert_def.duration_seconds:
                    # Duration exceeded, fire alert
                    return self._fire_alert(alert_def, alert_key, first_seen, value)
            else:
                # Start tracking
                self._pending_alerts[alert_key] = now
                logger.debug(f"Alert {alert_def.name} pending, tracking...")
        else:
            # Condition not met, resolve if firing
            if alert_key in self._pending_alerts:
                del self._pending_alerts[alert_key]
            
            if alert_key in self._active_alerts:
                return self._resolve_alert(alert_key)
        
        return None
    
    def _evaluate_condition(
        self,
        alert_def: AlertDefinition,
        value: float,
    ) -> bool:
        """Evaluate if alert condition is met."""
        if alert_def.condition == AlertCondition.THRESHOLD_ABOVE:
            return value > alert_def.threshold
        
        elif alert_def.condition == AlertCondition.THRESHOLD_BELOW:
            return value < alert_def.threshold
        
        elif alert_def.condition == AlertCondition.RATE_OF_CHANGE:
            # Would need previous value for rate of change
            # For now, treat threshold as absolute change
            return abs(value) > abs(alert_def.threshold)
        
        elif alert_def.condition == AlertCondition.CUSTOM:
            if alert_def.custom_evaluator:
                return alert_def.custom_evaluator({"value": value})
            return False
        
        elif alert_def.condition == AlertCondition.ABSENCE:
            # Absence is handled in evaluate_alert
            return False
        
        return False
    
    def _fire_alert(
        self,
        alert_def: AlertDefinition,
        alert_key: str,
        first_seen: datetime,
        value: float,
    ) -> ActiveAlert:
        """Fire an alert."""
        now = datetime.now(timezone.utc)
        
        if alert_key in self._active_alerts:
            # Update existing alert
            alert = self._active_alerts[alert_key]
            alert.last_triggered = now
            alert.last_value = value
            return alert
        
        # Create new alert
        alert = ActiveAlert(
            definition=alert_def,
            state=AlertState.FIRING,
            first_triggered=first_seen,
            last_triggered=now,
            last_value=value,
            labels=alert_def.labels.copy(),
        )
        
        self._active_alerts[alert_key] = alert
        
        # Remove from pending
        if alert_key in self._pending_alerts:
            del self._pending_alerts[alert_key]
        
        # Record metrics
        if PROMETHEUS_AVAILABLE:
            ALERTS_FIRED.labels(
                alert_name=alert_def.name,
                severity=alert_def.severity.value,
            ).inc()
            ACTIVE_ALERTS.labels(severity=alert_def.severity.value).inc()
        
        logger.warning(
            f"Alert FIRING: {alert_def.name} - {alert_def.description} "
            f"(value={value}, threshold={alert_def.threshold})"
        )
        
        # Notify if not in cooldown
        asyncio.create_task(self._notify_alert(alert, "firing"))
        
        return alert
    
    def _resolve_alert(self, alert_key: str) -> ActiveAlert:
        """Resolve an alert."""
        alert = self._active_alerts[alert_key]
        alert.state = AlertState.RESOLVED
        alert.resolved_at = datetime.now(timezone.utc)
        
        # Move to history
        self._alert_history.append(alert)
        if len(self._alert_history) > self._max_history:
            self._alert_history = self._alert_history[-self._max_history:]
        
        del self._active_alerts[alert_key]
        
        # Record metrics
        if PROMETHEUS_AVAILABLE:
            ALERTS_RESOLVED.labels(
                alert_name=alert.definition.name,
                severity=alert.definition.severity.value,
            ).inc()
            ACTIVE_ALERTS.labels(severity=alert.definition.severity.value).dec()
        
        logger.info(
            f"Alert RESOLVED: {alert.definition.name} "
            f"(duration={alert.duration.total_seconds():.0f}s)"
        )
        
        # Notify resolution
        asyncio.create_task(self._notify_alert(alert, "resolved"))
        
        return alert
    
    async def _notify_alert(self, alert: ActiveAlert, event: str) -> None:
        """Send alert to all notifiers."""
        alert_key = f"{alert.definition.name}:{json.dumps(alert.definition.labels, sort_keys=True)}"
        
        # Check cooldown for firing events
        if event == "firing":
            last_notified = self._cooldowns.get(alert_key)
            if last_notified:
                elapsed = (datetime.now(timezone.utc) - last_notified).total_seconds()
                if elapsed < alert.definition.cooldown_seconds:
                    logger.debug(f"Alert {alert.definition.name} in cooldown, skipping notification")
                    return
        
        # Notify all notifiers
        for notifier in self._notifiers:
            try:
                await notifier.notify(alert, event)
                alert.notification_count += 1
            except Exception as e:
                logger.error(f"Notifier {notifier.__class__.__name__} failed: {e}")
        
        # Update cooldown
        self._cooldowns[alert_key] = datetime.now(timezone.utc)
    
    async def evaluate_all(self) -> List[ActiveAlert]:
        """Evaluate all alert conditions."""
        results = []
        
        for alert_def in ADAM_ALERTS:
            try:
                result = await self.evaluate_alert(alert_def)
                if result:
                    results.append(result)
            except Exception as e:
                logger.error(f"Failed to evaluate alert {alert_def.name}: {e}")
        
        return results
    
    async def start_monitoring(self) -> None:
        """Start background alert monitoring."""
        async def monitor_loop():
            while True:
                try:
                    await self.evaluate_all()
                except Exception as e:
                    logger.error(f"Alert evaluation error: {e}")
                await asyncio.sleep(self._check_interval)
        
        self._monitoring_task = asyncio.create_task(monitor_loop())
        logger.info(f"Started alert monitoring (interval={self._check_interval}s)")
    
    async def stop_monitoring(self) -> None:
        """Stop background alert monitoring."""
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
            self._monitoring_task = None
            logger.info("Stopped alert monitoring")
    
    # =========================================================================
    # QUERY METHODS
    # =========================================================================
    
    def get_active_alerts(self) -> List[ActiveAlert]:
        """Get all currently firing alerts."""
        return list(self._active_alerts.values())
    
    def get_active_alerts_by_severity(
        self,
        severity: AlertSeverity,
    ) -> List[ActiveAlert]:
        """Get active alerts of a specific severity."""
        return [
            a for a in self._active_alerts.values()
            if a.definition.severity == severity
        ]
    
    def get_critical_alerts(self) -> List[ActiveAlert]:
        """Get all critical alerts."""
        return self.get_active_alerts_by_severity(AlertSeverity.CRITICAL)
    
    def get_alert_history(
        self,
        limit: int = 50,
    ) -> List[ActiveAlert]:
        """Get recent alert history."""
        return self._alert_history[-limit:]
    
    def get_alert_summary(self) -> Dict[str, Any]:
        """Get summary of alert status."""
        active = self.get_active_alerts()
        
        by_severity = {
            "critical": len([a for a in active if a.definition.severity == AlertSeverity.CRITICAL]),
            "warning": len([a for a in active if a.definition.severity == AlertSeverity.WARNING]),
            "info": len([a for a in active if a.definition.severity == AlertSeverity.INFO]),
        }
        
        return {
            "total_active": len(active),
            "by_severity": by_severity,
            "alerts": [a.to_dict() for a in active],
            "pending_count": len(self._pending_alerts),
            "history_count": len(self._alert_history),
        }
    
    def is_healthy(self) -> bool:
        """Check if there are no critical alerts."""
        return len(self.get_critical_alerts()) == 0


# =============================================================================
# SINGLETON
# =============================================================================

_manager: Optional[AlertManager] = None


def get_alert_manager() -> AlertManager:
    """Get the singleton alert manager."""
    global _manager
    if _manager is None:
        _manager = AlertManager()
    return _manager
