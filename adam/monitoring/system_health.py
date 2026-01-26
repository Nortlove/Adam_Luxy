# =============================================================================
# ADAM System Health Aggregator
# Location: adam/monitoring/system_health.py
# =============================================================================

"""
SYSTEM HEALTH AGGREGATOR

Provides a unified view of ADAM platform health.

Aggregates:
- Component health (from HealthRegistry)
- Learning loop health
- Active alerts
- Key metrics
- Dependency status

Exposes health data for:
- API endpoints (/health, /health/detailed)
- Monitoring dashboards
- Alerting systems
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from enum import Enum

from adam.infrastructure.health import (
    HealthRegistry,
    HealthStatus,
    get_health_registry,
)

logger = logging.getLogger(__name__)


class SystemStatus(str, Enum):
    """Overall system status."""
    OPERATIONAL = "operational"
    DEGRADED = "degraded"
    PARTIAL_OUTAGE = "partial_outage"
    MAJOR_OUTAGE = "major_outage"


@dataclass
class ComponentStatus:
    """Status of a single component."""
    name: str
    status: HealthStatus
    dependencies: Dict[str, str] = field(default_factory=dict)
    metrics: Dict[str, float] = field(default_factory=dict)
    issues: List[str] = field(default_factory=list)
    last_check: Optional[datetime] = None


@dataclass
class SystemHealthReport:
    """Complete system health report."""
    status: SystemStatus
    timestamp: datetime
    uptime_seconds: float
    components: Dict[str, ComponentStatus] = field(default_factory=dict)
    active_alerts: List[Dict[str, Any]] = field(default_factory=list)
    learning_loop_health: Optional[Dict[str, Any]] = None
    key_metrics: Dict[str, float] = field(default_factory=dict)
    issues: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "status": self.status.value,
            "timestamp": self.timestamp.isoformat(),
            "uptime_seconds": self.uptime_seconds,
            "components": {
                name: {
                    "status": c.status.value,
                    "dependencies": c.dependencies,
                    "metrics": c.metrics,
                    "issues": c.issues,
                    "last_check": c.last_check.isoformat() if c.last_check else None,
                }
                for name, c in self.components.items()
            },
            "active_alerts": self.active_alerts,
            "learning_loop": self.learning_loop_health,
            "key_metrics": self.key_metrics,
            "issues": self.issues,
        }
    
    @property
    def is_healthy(self) -> bool:
        """Check if system is operational."""
        return self.status == SystemStatus.OPERATIONAL


class SystemHealthAggregator:
    """
    Aggregates health from all ADAM components.
    
    Provides:
    - Real-time health status
    - Historical health data
    - Health check endpoints
    - Dashboard data
    """
    
    def __init__(self):
        self._start_time = datetime.now(timezone.utc)
        self._health_registry = get_health_registry()
        
        # Alert manager (lazy import to avoid circular)
        self._alert_manager = None
        
        # Learning loop monitor (lazy import)
        self._learning_monitor = None
        
        # Last report
        self._last_report: Optional[SystemHealthReport] = None
        self._report_interval_seconds = 30
        
        # Background task
        self._monitoring_task: Optional[asyncio.Task] = None
    
    def _get_alert_manager(self):
        """Lazy load alert manager."""
        if self._alert_manager is None:
            try:
                from adam.infrastructure.alerting import get_alert_manager
                self._alert_manager = get_alert_manager()
            except ImportError:
                pass
        return self._alert_manager
    
    def _get_learning_monitor(self):
        """Lazy load learning monitor."""
        if self._learning_monitor is None:
            try:
                from adam.monitoring.learning_loop_monitor import get_learning_loop_monitor
                self._learning_monitor = get_learning_loop_monitor()
            except ImportError:
                pass
        return self._learning_monitor
    
    async def generate_report(self) -> SystemHealthReport:
        """Generate a complete health report."""
        now = datetime.now(timezone.utc)
        uptime = (now - self._start_time).total_seconds()
        
        issues = []
        components = {}
        
        # Get component health from registry
        try:
            component_health = await self._health_registry.check_all_health()
            
            for name, health in component_health.items():
                comp_issues = health.unhealthy_dependencies
                if comp_issues:
                    issues.extend([f"{name}: {dep} unavailable" for dep in comp_issues])
                
                components[name] = ComponentStatus(
                    name=name,
                    status=health.status,
                    dependencies={
                        d.name: d.status.value
                        for d in health.dependencies.values()
                    },
                    issues=comp_issues,
                    last_check=health.last_check,
                )
        except Exception as e:
            logger.error(f"Failed to get component health: {e}")
            issues.append(f"Health check error: {e}")
        
        # Get active alerts
        active_alerts = []
        alert_manager = self._get_alert_manager()
        if alert_manager:
            try:
                alerts = alert_manager.get_active_alerts()
                active_alerts = [a.to_dict() for a in alerts]
                
                # Add critical alerts to issues
                critical = [a for a in alerts if a.definition.severity.value == "critical"]
                for alert in critical:
                    issues.append(f"CRITICAL: {alert.definition.name}")
            except Exception as e:
                logger.error(f"Failed to get alerts: {e}")
        
        # Get learning loop health
        learning_health = None
        learning_monitor = self._get_learning_monitor()
        if learning_monitor:
            try:
                health = learning_monitor.get_health()
                learning_health = health.to_dict()
                
                if not health.is_healthy:
                    issues.extend(health.issues)
            except Exception as e:
                logger.error(f"Failed to get learning loop health: {e}")
        
        # Get key metrics
        key_metrics = await self._collect_key_metrics()
        
        # Determine overall status
        status = self._determine_status(components, active_alerts, issues)
        
        report = SystemHealthReport(
            status=status,
            timestamp=now,
            uptime_seconds=uptime,
            components=components,
            active_alerts=active_alerts,
            learning_loop_health=learning_health,
            key_metrics=key_metrics,
            issues=issues,
        )
        
        self._last_report = report
        return report
    
    async def _collect_key_metrics(self) -> Dict[str, float]:
        """Collect key metrics for the health report."""
        metrics = {}
        
        try:
            # Try to get metrics from Prometheus
            from prometheus_client import REGISTRY
            
            # Decision metrics
            for metric in REGISTRY.collect():
                if metric.name == "adam_decisions_total":
                    for sample in metric.samples:
                        if sample.name == "adam_decisions_total":
                            metrics["decisions_total"] = sample.value
                
                elif metric.name == "adam_learning_signals_total":
                    for sample in metric.samples:
                        if sample.name == "adam_learning_signals_total":
                            metrics["learning_signals_total"] = sample.value
                
                elif metric.name == "adam_cache_hit_rate":
                    for sample in metric.samples:
                        if sample.name == "adam_cache_hit_rate":
                            metrics["cache_hit_rate"] = sample.value
                
        except Exception as e:
            logger.debug(f"Could not collect Prometheus metrics: {e}")
        
        return metrics
    
    def _determine_status(
        self,
        components: Dict[str, ComponentStatus],
        alerts: List[Dict[str, Any]],
        issues: List[str],
    ) -> SystemStatus:
        """Determine overall system status."""
        # Count unhealthy components
        unhealthy = [c for c in components.values() if c.status == HealthStatus.UNHEALTHY]
        degraded = [c for c in components.values() if c.status == HealthStatus.DEGRADED]
        
        # Count critical alerts
        critical_alerts = [a for a in alerts if a.get("severity") == "critical"]
        
        if len(critical_alerts) >= 3 or len(unhealthy) >= 3:
            return SystemStatus.MAJOR_OUTAGE
        
        if len(critical_alerts) >= 1 or len(unhealthy) >= 1:
            return SystemStatus.PARTIAL_OUTAGE
        
        if len(degraded) >= 2 or len(issues) >= 3:
            return SystemStatus.DEGRADED
        
        return SystemStatus.OPERATIONAL
    
    # =========================================================================
    # SIMPLIFIED HEALTH CHECKS
    # =========================================================================
    
    async def check_liveness(self) -> Dict[str, Any]:
        """
        Simple liveness check.
        
        Returns immediately - just checks if the service is running.
        Used by: /health or /healthz
        """
        return {
            "status": "ok",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    
    async def check_readiness(self) -> Dict[str, Any]:
        """
        Readiness check with dependency verification.
        
        Checks critical dependencies are available.
        Used by: /health/ready
        """
        # Quick check of critical dependencies
        ready = True
        dependencies = {}
        
        try:
            platform_health = self._health_registry.get_platform_health()
            
            for comp_name, comp_status in platform_health.get("components", {}).items():
                if comp_status.get("status") == "unhealthy":
                    ready = False
                
                dependencies[comp_name] = comp_status.get("status", "unknown")
                
        except Exception as e:
            logger.error(f"Readiness check error: {e}")
            ready = False
        
        return {
            "ready": ready,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "dependencies": dependencies,
        }
    
    async def get_detailed_health(self) -> Dict[str, Any]:
        """
        Detailed health status.
        
        Full health report with all components, alerts, metrics.
        Used by: /health/detailed
        """
        report = await self.generate_report()
        return report.to_dict()
    
    # =========================================================================
    # MONITORING
    # =========================================================================
    
    async def start_monitoring(self, interval_seconds: int = 30) -> None:
        """Start background health monitoring."""
        self._report_interval_seconds = interval_seconds
        
        async def monitor_loop():
            while True:
                try:
                    await self.generate_report()
                except Exception as e:
                    logger.error(f"Health monitoring error: {e}")
                await asyncio.sleep(self._report_interval_seconds)
        
        self._monitoring_task = asyncio.create_task(monitor_loop())
        logger.info(f"Started system health monitoring (interval={interval_seconds}s)")
    
    async def stop_monitoring(self) -> None:
        """Stop background monitoring."""
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
            self._monitoring_task = None
            logger.info("Stopped system health monitoring")
    
    def get_last_report(self) -> Optional[SystemHealthReport]:
        """Get the most recent health report."""
        return self._last_report
    
    def get_uptime(self) -> float:
        """Get system uptime in seconds."""
        return (datetime.now(timezone.utc) - self._start_time).total_seconds()


# =============================================================================
# SINGLETON
# =============================================================================

_aggregator: Optional[SystemHealthAggregator] = None


def get_system_health_aggregator() -> SystemHealthAggregator:
    """Get the singleton system health aggregator."""
    global _aggregator
    if _aggregator is None:
        _aggregator = SystemHealthAggregator()
    return _aggregator
