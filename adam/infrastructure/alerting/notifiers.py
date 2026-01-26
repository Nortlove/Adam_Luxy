# =============================================================================
# ADAM Alert Notifiers
# Location: adam/infrastructure/alerting/notifiers.py
# =============================================================================

"""
ALERT NOTIFIERS

Send alerts to various notification channels.

Supported channels:
- Slack: Webhook-based notifications
- Email: SMTP-based notifications
- Webhook: Generic HTTP POST
- Log: Structured logging (default)
"""

import asyncio
import logging
import json
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Try to import aiohttp for async HTTP
try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False

# Try to import smtplib for email
try:
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    SMTP_AVAILABLE = True
except ImportError:
    SMTP_AVAILABLE = False


class Notifier(ABC):
    """Abstract base class for alert notifiers."""
    
    @abstractmethod
    async def notify(self, alert: Any, event: str) -> bool:
        """
        Send an alert notification.
        
        Args:
            alert: The ActiveAlert object
            event: Event type ("firing" or "resolved")
            
        Returns:
            True if notification was sent successfully
        """
        pass
    
    def format_message(self, alert: Any, event: str) -> str:
        """Format alert message for notification."""
        severity_emoji = {
            "critical": "🚨",
            "warning": "⚠️",
            "info": "ℹ️",
        }
        
        emoji = severity_emoji.get(alert.definition.severity.value, "")
        status = "FIRING" if event == "firing" else "RESOLVED"
        
        message = f"{emoji} [{status}] {alert.definition.name}\n\n"
        message += f"**Description**: {alert.definition.description}\n"
        message += f"**Severity**: {alert.definition.severity.value.upper()}\n"
        message += f"**Value**: {alert.last_value:.4f} (threshold: {alert.definition.threshold})\n"
        message += f"**Duration**: {alert.duration.total_seconds():.0f} seconds\n"
        
        if alert.definition.runbook_url:
            message += f"\n📖 Runbook: {alert.definition.runbook_url}"
        
        return message


class LogNotifier(Notifier):
    """
    Notifier that logs alerts using structured logging.
    
    This is the default notifier and should always be enabled.
    """
    
    def __init__(self, logger_name: str = "adam.alerts"):
        self._logger = logging.getLogger(logger_name)
    
    async def notify(self, alert: Any, event: str) -> bool:
        """Log the alert."""
        log_data = {
            "event": "alert",
            "alert_name": alert.definition.name,
            "alert_event": event,
            "severity": alert.definition.severity.value,
            "description": alert.definition.description,
            "value": alert.last_value,
            "threshold": alert.definition.threshold,
            "duration_seconds": alert.duration.total_seconds(),
            "labels": alert.labels,
        }
        
        if event == "firing":
            if alert.definition.severity.value == "critical":
                self._logger.critical(json.dumps(log_data))
            else:
                self._logger.warning(json.dumps(log_data))
        else:
            self._logger.info(json.dumps(log_data))
        
        return True


class SlackNotifier(Notifier):
    """
    Notifier that sends alerts to Slack via webhook.
    
    Configuration via environment:
    - ADAM_SLACK_WEBHOOK_URL: Slack incoming webhook URL
    - ADAM_SLACK_CHANNEL: Optional channel override
    """
    
    def __init__(
        self,
        webhook_url: Optional[str] = None,
        channel: Optional[str] = None,
    ):
        self.webhook_url = webhook_url or os.getenv("ADAM_SLACK_WEBHOOK_URL")
        self.channel = channel or os.getenv("ADAM_SLACK_CHANNEL")
        
        if not self.webhook_url:
            logger.warning("Slack webhook URL not configured")
    
    async def notify(self, alert: Any, event: str) -> bool:
        """Send alert to Slack."""
        if not self.webhook_url or not AIOHTTP_AVAILABLE:
            return False
        
        # Build Slack message
        color = {
            "critical": "#FF0000",  # Red
            "warning": "#FFA500",   # Orange
            "info": "#0000FF",      # Blue
        }.get(alert.definition.severity.value, "#808080")
        
        status = "🔥 FIRING" if event == "firing" else "✅ RESOLVED"
        
        payload = {
            "attachments": [{
                "color": color,
                "title": f"{status}: {alert.definition.name}",
                "text": alert.definition.description,
                "fields": [
                    {
                        "title": "Severity",
                        "value": alert.definition.severity.value.upper(),
                        "short": True,
                    },
                    {
                        "title": "Value",
                        "value": f"{alert.last_value:.4f}",
                        "short": True,
                    },
                    {
                        "title": "Threshold",
                        "value": str(alert.definition.threshold),
                        "short": True,
                    },
                    {
                        "title": "Duration",
                        "value": f"{alert.duration.total_seconds():.0f}s",
                        "short": True,
                    },
                ],
                "footer": "ADAM Alert System",
                "ts": int(datetime.now(timezone.utc).timestamp()),
            }]
        }
        
        if self.channel:
            payload["channel"] = self.channel
        
        if alert.definition.runbook_url:
            payload["attachments"][0]["fields"].append({
                "title": "Runbook",
                "value": alert.definition.runbook_url,
                "short": False,
            })
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.webhook_url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as response:
                    if response.status == 200:
                        logger.debug(f"Sent Slack notification for {alert.definition.name}")
                        return True
                    else:
                        logger.error(f"Slack notification failed: {response.status}")
                        return False
        except Exception as e:
            logger.error(f"Failed to send Slack notification: {e}")
            return False


class WebhookNotifier(Notifier):
    """
    Notifier that sends alerts to a generic HTTP webhook.
    
    Useful for integrating with:
    - PagerDuty
    - Opsgenie
    - Custom alerting systems
    
    Configuration via environment:
    - ADAM_ALERT_WEBHOOK_URL: Webhook URL
    - ADAM_ALERT_WEBHOOK_SECRET: Optional shared secret for auth
    """
    
    def __init__(
        self,
        webhook_url: Optional[str] = None,
        secret: Optional[str] = None,
        custom_headers: Optional[Dict[str, str]] = None,
    ):
        self.webhook_url = webhook_url or os.getenv("ADAM_ALERT_WEBHOOK_URL")
        self.secret = secret or os.getenv("ADAM_ALERT_WEBHOOK_SECRET")
        self.custom_headers = custom_headers or {}
        
        if not self.webhook_url:
            logger.warning("Alert webhook URL not configured")
    
    async def notify(self, alert: Any, event: str) -> bool:
        """Send alert to webhook."""
        if not self.webhook_url or not AIOHTTP_AVAILABLE:
            return False
        
        payload = {
            "event": event,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "alert": {
                "name": alert.definition.name,
                "description": alert.definition.description,
                "severity": alert.definition.severity.value,
                "condition": alert.definition.condition.value,
                "metric": alert.definition.metric_name,
                "threshold": alert.definition.threshold,
                "value": alert.last_value,
                "labels": alert.labels,
                "duration_seconds": alert.duration.total_seconds(),
                "first_triggered": alert.first_triggered.isoformat(),
                "runbook_url": alert.definition.runbook_url,
            },
            "source": "adam_platform",
        }
        
        headers = {
            "Content-Type": "application/json",
            **self.custom_headers,
        }
        
        if self.secret:
            headers["X-Alert-Secret"] = self.secret
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.webhook_url,
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as response:
                    if response.status in (200, 201, 202, 204):
                        logger.debug(f"Sent webhook notification for {alert.definition.name}")
                        return True
                    else:
                        logger.error(f"Webhook notification failed: {response.status}")
                        return False
        except Exception as e:
            logger.error(f"Failed to send webhook notification: {e}")
            return False


class EmailNotifier(Notifier):
    """
    Notifier that sends alerts via email.
    
    Configuration via environment:
    - ADAM_SMTP_HOST: SMTP server hostname
    - ADAM_SMTP_PORT: SMTP port (default 587)
    - ADAM_SMTP_USER: SMTP username
    - ADAM_SMTP_PASSWORD: SMTP password
    - ADAM_ALERT_EMAIL_FROM: From address
    - ADAM_ALERT_EMAIL_TO: Comma-separated recipient list
    """
    
    def __init__(
        self,
        smtp_host: Optional[str] = None,
        smtp_port: Optional[int] = None,
        smtp_user: Optional[str] = None,
        smtp_password: Optional[str] = None,
        from_addr: Optional[str] = None,
        to_addrs: Optional[List[str]] = None,
    ):
        self.smtp_host = smtp_host or os.getenv("ADAM_SMTP_HOST")
        self.smtp_port = smtp_port or int(os.getenv("ADAM_SMTP_PORT", "587"))
        self.smtp_user = smtp_user or os.getenv("ADAM_SMTP_USER")
        self.smtp_password = smtp_password or os.getenv("ADAM_SMTP_PASSWORD")
        self.from_addr = from_addr or os.getenv("ADAM_ALERT_EMAIL_FROM", "alerts@adam-platform.local")
        
        to_env = os.getenv("ADAM_ALERT_EMAIL_TO", "")
        self.to_addrs = to_addrs or [a.strip() for a in to_env.split(",") if a.strip()]
        
        if not self.smtp_host:
            logger.warning("SMTP host not configured")
    
    async def notify(self, alert: Any, event: str) -> bool:
        """Send alert via email."""
        if not self.smtp_host or not self.to_addrs or not SMTP_AVAILABLE:
            return False
        
        # Build email
        status = "FIRING" if event == "firing" else "RESOLVED"
        subject = f"[{alert.definition.severity.value.upper()}] {status}: {alert.definition.name}"
        
        body = self.format_message(alert, event)
        body = body.replace("**", "")  # Remove markdown
        
        msg = MIMEMultipart()
        msg["From"] = self.from_addr
        msg["To"] = ", ".join(self.to_addrs)
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))
        
        # Send in thread pool (SMTP is blocking)
        loop = asyncio.get_event_loop()
        try:
            await loop.run_in_executor(None, self._send_email, msg)
            logger.debug(f"Sent email notification for {alert.definition.name}")
            return True
        except Exception as e:
            logger.error(f"Failed to send email notification: {e}")
            return False
    
    def _send_email(self, msg: MIMEMultipart) -> None:
        """Send email via SMTP (blocking)."""
        with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
            server.starttls()
            if self.smtp_user and self.smtp_password:
                server.login(self.smtp_user, self.smtp_password)
            server.send_message(msg)


class CompositeNotifier(Notifier):
    """
    Notifier that sends to multiple channels.
    
    Useful for routing different severity levels to different channels.
    """
    
    def __init__(self):
        self._notifiers: Dict[str, List[Notifier]] = {
            "critical": [],
            "warning": [],
            "info": [],
            "all": [],  # Receive all alerts
        }
    
    def add_notifier(
        self,
        notifier: Notifier,
        severities: Optional[List[str]] = None,
    ) -> None:
        """
        Add a notifier for specific severities.
        
        Args:
            notifier: The notifier to add
            severities: List of severities to notify (None = all)
        """
        if severities is None:
            self._notifiers["all"].append(notifier)
        else:
            for sev in severities:
                if sev in self._notifiers:
                    self._notifiers[sev].append(notifier)
    
    async def notify(self, alert: Any, event: str) -> bool:
        """Send to all applicable notifiers."""
        severity = alert.definition.severity.value
        
        # Collect applicable notifiers
        notifiers = set(self._notifiers["all"])
        notifiers.update(self._notifiers.get(severity, []))
        
        # Notify all
        results = await asyncio.gather(*[
            n.notify(alert, event) for n in notifiers
        ], return_exceptions=True)
        
        # Return True if any succeeded
        return any(r is True for r in results)


def create_default_notifier() -> CompositeNotifier:
    """
    Create a composite notifier with default configuration.
    
    Reads configuration from environment variables.
    """
    composite = CompositeNotifier()
    
    # Always add log notifier
    composite.add_notifier(LogNotifier())
    
    # Add Slack if configured
    if os.getenv("ADAM_SLACK_WEBHOOK_URL"):
        slack = SlackNotifier()
        composite.add_notifier(slack, ["critical", "warning"])
    
    # Add webhook if configured
    if os.getenv("ADAM_ALERT_WEBHOOK_URL"):
        webhook = WebhookNotifier()
        composite.add_notifier(webhook)
    
    # Add email if configured
    if os.getenv("ADAM_SMTP_HOST") and os.getenv("ADAM_ALERT_EMAIL_TO"):
        email = EmailNotifier()
        composite.add_notifier(email, ["critical"])
    
    return composite
