# =============================================================================
# ADAM Alerting Service
# Location: adam/monitoring/alerting.py
# =============================================================================

"""
ALERTING SERVICE

Manages alerts, notifications, and automated responses.

Features:
1. Multi-channel notifications (Slack, PagerDuty, email)
2. Alert escalation
3. Alert fatigue prevention
4. Automated response actions
"""

import logging
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field

from adam.monitoring.drift_detection import DriftAlert, DriftSeverity, DriftStatus

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS
# =============================================================================

class NotificationChannel(str, Enum):
    """Notification channels."""
    
    SLACK = "slack"
    PAGERDUTY = "pagerduty"
    EMAIL = "email"
    WEBHOOK = "webhook"
    LOG = "log"


class AlertPriority(str, Enum):
    """Alert priority for routing."""
    
    P1 = "p1"  # Page immediately
    P2 = "p2"  # Alert within 15 minutes
    P3 = "p3"  # Alert within 1 hour
    P4 = "p4"  # Daily digest
    P5 = "p5"  # Weekly summary


class AutomatedAction(str, Enum):
    """Automated response actions."""
    
    NONE = "none"
    LOG_ONLY = "log_only"
    INCREASE_MONITORING = "increase_monitoring"
    ENABLE_FALLBACK = "enable_fallback"
    REDUCE_TRAFFIC = "reduce_traffic"
    DISABLE_COMPONENT = "disable_component"
    TRIGGER_ROLLBACK = "trigger_rollback"


# =============================================================================
# MODELS
# =============================================================================

class AlertRule(BaseModel):
    """Alert routing rule."""
    
    rule_id: str = Field(default_factory=lambda: f"rule_{uuid4().hex[:8]}")
    name: str
    description: str
    
    # Matching
    severity_match: List[DriftSeverity] = Field(default_factory=list)
    component_match: List[str] = Field(default_factory=list)
    
    # Routing
    priority: AlertPriority
    channels: List[NotificationChannel]
    
    # Automation
    automated_action: AutomatedAction = Field(default=AutomatedAction.LOG_ONLY)
    
    # Timing
    cooldown_minutes: int = Field(default=15, ge=0)
    
    # Active
    is_active: bool = Field(default=True)


class Notification(BaseModel):
    """A notification to be sent."""
    
    notification_id: str = Field(
        default_factory=lambda: f"notif_{uuid4().hex[:12]}"
    )
    
    # Alert reference
    alert_id: str
    
    # Channel
    channel: NotificationChannel
    
    # Content
    title: str
    message: str
    priority: AlertPriority
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    # Status
    sent: bool = Field(default=False)
    sent_at: Optional[datetime] = None
    
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class AlertAggregate(BaseModel):
    """Aggregated alerts for fatigue prevention."""
    
    aggregate_id: str = Field(
        default_factory=lambda: f"agg_{uuid4().hex[:8]}"
    )
    
    # Grouping key
    component: str
    severity: DriftSeverity
    
    # Aggregated alerts
    alert_ids: List[str] = Field(default_factory=list)
    count: int = Field(default=0, ge=0)
    
    # Timing
    first_seen: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    last_seen: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    
    # Notification
    notified: bool = Field(default=False)


# =============================================================================
# DEFAULT ALERT RULES
# =============================================================================

DEFAULT_ALERT_RULES = [
    AlertRule(
        name="critical_drift",
        description="Critical drift requires immediate attention",
        severity_match=[DriftSeverity.CRITICAL],
        priority=AlertPriority.P1,
        channels=[NotificationChannel.PAGERDUTY, NotificationChannel.SLACK],
        automated_action=AutomatedAction.ENABLE_FALLBACK,
        cooldown_minutes=5,
    ),
    AlertRule(
        name="high_drift",
        description="High drift requires investigation",
        severity_match=[DriftSeverity.HIGH],
        priority=AlertPriority.P2,
        channels=[NotificationChannel.SLACK],
        automated_action=AutomatedAction.INCREASE_MONITORING,
        cooldown_minutes=15,
    ),
    AlertRule(
        name="medium_drift",
        description="Medium drift for awareness",
        severity_match=[DriftSeverity.MEDIUM],
        priority=AlertPriority.P3,
        channels=[NotificationChannel.SLACK],
        automated_action=AutomatedAction.LOG_ONLY,
        cooldown_minutes=60,
    ),
    AlertRule(
        name="low_drift",
        description="Low drift for daily digest",
        severity_match=[DriftSeverity.LOW],
        priority=AlertPriority.P4,
        channels=[NotificationChannel.EMAIL],
        automated_action=AutomatedAction.LOG_ONLY,
        cooldown_minutes=1440,  # 24 hours
    ),
]


# =============================================================================
# ALERTING SERVICE
# =============================================================================

class AlertingService:
    """
    Service for managing alerts and notifications.
    """
    
    def __init__(
        self,
        rules: Optional[List[AlertRule]] = None,
    ):
        self.rules = rules or DEFAULT_ALERT_RULES
        
        # Alert history
        self.alerts: Dict[str, DriftAlert] = {}
        self.notifications: List[Notification] = []
        self.aggregates: Dict[str, AlertAggregate] = {}
        
        # Cooldown tracking
        self.last_notified: Dict[str, datetime] = {}
        
        # Action handlers
        self.action_handlers: Dict[AutomatedAction, Callable] = {}
    
    def register_action_handler(
        self,
        action: AutomatedAction,
        handler: Callable,
    ) -> None:
        """Register a handler for an automated action."""
        self.action_handlers[action] = handler
    
    async def process_alert(
        self,
        alert: DriftAlert,
    ) -> List[Notification]:
        """
        Process an alert through the alerting pipeline.
        
        Returns list of notifications generated.
        """
        # Store alert
        self.alerts[alert.alert_id] = alert
        
        # Find matching rules
        matching_rules = self._find_matching_rules(alert)
        
        if not matching_rules:
            # Log only
            logger.info(f"Alert {alert.alert_id}: {alert.description}")
            return []
        
        # Check for fatigue (aggregation)
        if self._should_aggregate(alert):
            self._aggregate_alert(alert)
            return []
        
        notifications = []
        
        for rule in matching_rules:
            # Check cooldown
            if self._in_cooldown(rule, alert):
                continue
            
            # Create notifications
            for channel in rule.channels:
                notification = self._create_notification(alert, channel, rule.priority)
                notifications.append(notification)
            
            # Execute automated action
            if rule.automated_action != AutomatedAction.NONE:
                await self._execute_action(rule.automated_action, alert)
            
            # Update cooldown
            self.last_notified[f"{rule.rule_id}:{alert.component}"] = datetime.now(timezone.utc)
        
        # Send notifications
        for notification in notifications:
            await self._send_notification(notification)
        
        self.notifications.extend(notifications)
        return notifications
    
    async def acknowledge_alert(
        self,
        alert_id: str,
        acknowledged_by: str,
    ) -> bool:
        """Acknowledge an alert."""
        if alert_id not in self.alerts:
            return False
        
        self.alerts[alert_id].status = DriftStatus.ACKNOWLEDGED
        logger.info(f"Alert {alert_id} acknowledged by {acknowledged_by}")
        return True
    
    async def resolve_alert(
        self,
        alert_id: str,
        resolution_note: str,
        false_positive: bool = False,
    ) -> bool:
        """Resolve an alert."""
        if alert_id not in self.alerts:
            return False
        
        alert = self.alerts[alert_id]
        alert.status = DriftStatus.FALSE_POSITIVE if false_positive else DriftStatus.RESOLVED
        alert.resolved_at = datetime.now(timezone.utc)
        
        logger.info(f"Alert {alert_id} resolved: {resolution_note}")
        return True
    
    def get_active_alerts(self) -> List[DriftAlert]:
        """Get all active (unresolved) alerts."""
        return [
            a for a in self.alerts.values()
            if a.status not in [DriftStatus.RESOLVED, DriftStatus.FALSE_POSITIVE]
        ]
    
    def get_alert_summary(self) -> Dict[str, Any]:
        """Get summary of alert status."""
        active = self.get_active_alerts()
        return {
            "total_alerts": len(self.alerts),
            "active_alerts": len(active),
            "by_severity": {
                severity.value: sum(1 for a in active if a.severity == severity)
                for severity in DriftSeverity
            },
            "notifications_sent": sum(1 for n in self.notifications if n.sent),
        }
    
    def _find_matching_rules(self, alert: DriftAlert) -> List[AlertRule]:
        """Find rules matching an alert."""
        matching = []
        
        for rule in self.rules:
            if not rule.is_active:
                continue
            
            # Check severity match
            if rule.severity_match and alert.severity not in rule.severity_match:
                continue
            
            # Check component match
            if rule.component_match and alert.component not in rule.component_match:
                continue
            
            matching.append(rule)
        
        return matching
    
    def _in_cooldown(self, rule: AlertRule, alert: DriftAlert) -> bool:
        """Check if rule is in cooldown for this component."""
        key = f"{rule.rule_id}:{alert.component}"
        
        if key not in self.last_notified:
            return False
        
        elapsed = datetime.now(timezone.utc) - self.last_notified[key]
        return elapsed < timedelta(minutes=rule.cooldown_minutes)
    
    def _should_aggregate(self, alert: DriftAlert) -> bool:
        """Check if alert should be aggregated."""
        # Aggregate low-severity alerts from same component
        if alert.severity in [DriftSeverity.LOW, DriftSeverity.NONE]:
            return True
        return False
    
    def _aggregate_alert(self, alert: DriftAlert) -> None:
        """Add alert to aggregate."""
        key = f"{alert.component}:{alert.severity.value}"
        
        if key not in self.aggregates:
            self.aggregates[key] = AlertAggregate(
                component=alert.component,
                severity=alert.severity,
            )
        
        agg = self.aggregates[key]
        agg.alert_ids.append(alert.alert_id)
        agg.count += 1
        agg.last_seen = datetime.now(timezone.utc)
    
    def _create_notification(
        self,
        alert: DriftAlert,
        channel: NotificationChannel,
        priority: AlertPriority,
    ) -> Notification:
        """Create a notification for an alert."""
        return Notification(
            alert_id=alert.alert_id,
            channel=channel,
            title=f"[{alert.severity.value.upper()}] {alert.drift_type.value} Drift Detected",
            message=self._format_message(alert),
            priority=priority,
            metadata={
                "component": alert.component,
                "recommendations": alert.recommendations,
            },
        )
    
    def _format_message(self, alert: DriftAlert) -> str:
        """Format alert message."""
        lines = [
            f"**Component:** {alert.component}",
            f"**Type:** {alert.drift_type.value}",
            f"**Description:** {alert.description}",
            "",
            "**Recommendations:**",
        ]
        for rec in alert.recommendations:
            lines.append(f"- {rec}")
        
        return "\n".join(lines)
    
    async def _send_notification(self, notification: Notification) -> bool:
        """Send a notification."""
        try:
            if notification.channel == NotificationChannel.LOG:
                logger.warning(f"ALERT: {notification.title}\n{notification.message}")
            elif notification.channel == NotificationChannel.SLACK:
                # Would call Slack API
                logger.info(f"Would send Slack: {notification.title}")
            elif notification.channel == NotificationChannel.PAGERDUTY:
                # Would call PagerDuty API
                logger.info(f"Would page: {notification.title}")
            elif notification.channel == NotificationChannel.EMAIL:
                # Would send email
                logger.info(f"Would email: {notification.title}")
            
            notification.sent = True
            notification.sent_at = datetime.now(timezone.utc)
            return True
        
        except Exception as e:
            logger.error(f"Failed to send notification: {e}")
            return False
    
    async def _execute_action(
        self,
        action: AutomatedAction,
        alert: DriftAlert,
    ) -> bool:
        """Execute an automated action."""
        logger.info(f"Executing action {action.value} for alert {alert.alert_id}")
        
        if action in self.action_handlers:
            try:
                await self.action_handlers[action](alert)
                return True
            except Exception as e:
                logger.error(f"Action {action.value} failed: {e}")
                return False
        
        # Default implementations
        if action == AutomatedAction.LOG_ONLY:
            logger.info(f"Alert logged: {alert.description}")
        elif action == AutomatedAction.INCREASE_MONITORING:
            logger.info(f"Increased monitoring for {alert.component}")
        elif action == AutomatedAction.ENABLE_FALLBACK:
            logger.warning(f"Fallback enabled for {alert.component}")
        
        return True
