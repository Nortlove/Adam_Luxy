# =============================================================================
# ADAM Alerting System
# Location: adam/infrastructure/alerting/__init__.py
# =============================================================================

"""
ADAM ALERTING SYSTEM

Provides proactive notification when system health degrades.

Components:
- AlertDefinition: Defines conditions that trigger alerts
- AlertManager: Evaluates conditions and manages alert state
- Notifiers: Send alerts to various channels (Slack, email, webhook)
"""

from adam.infrastructure.alerting.alert_definitions import (
    AlertDefinition,
    AlertSeverity,
    AlertCondition,
    ADAM_ALERTS,
)
from adam.infrastructure.alerting.manager import (
    AlertManager,
    AlertState,
    ActiveAlert,
    get_alert_manager,
)
from adam.infrastructure.alerting.notifiers import (
    Notifier,
    SlackNotifier,
    WebhookNotifier,
    EmailNotifier,
    LogNotifier,
)

__all__ = [
    # Definitions
    "AlertDefinition",
    "AlertSeverity",
    "AlertCondition",
    "ADAM_ALERTS",
    # Manager
    "AlertManager",
    "AlertState",
    "ActiveAlert",
    "get_alert_manager",
    # Notifiers
    "Notifier",
    "SlackNotifier",
    "WebhookNotifier",
    "EmailNotifier",
    "LogNotifier",
]
