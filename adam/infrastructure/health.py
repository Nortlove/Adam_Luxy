# =============================================================================
# ADAM Health Monitoring Infrastructure
# Location: adam/infrastructure/health.py
# =============================================================================

"""
HEALTH MONITORING

Provides health checks and dependency monitoring for ADAM components.

Features:
- Dependency availability tracking
- Health check aggregation
- Metrics integration
- Graceful degradation support
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Callable, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps

logger = logging.getLogger(__name__)

try:
    from prometheus_client import Gauge, Counter
    
    DEPENDENCY_STATUS = Gauge(
        'adam_dependency_status',
        'Status of ADAM dependencies (1=healthy, 0=unhealthy)',
        ['dependency_name']
    )
    DEPENDENCY_FAILURES = Counter(
        'adam_dependency_failures_total',
        'Total dependency check failures',
        ['dependency_name']
    )
    COMPONENT_HEALTH = Gauge(
        'adam_component_health',
        'Health status of ADAM components (1=healthy, 0=unhealthy)',
        ['component_name']
    )
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False


class HealthStatus(str, Enum):
    """Health status values."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class DependencyHealth:
    """Health status of a single dependency."""
    name: str
    status: HealthStatus
    last_check: datetime
    last_success: Optional[datetime] = None
    error_message: Optional[str] = None
    check_latency_ms: float = 0.0
    consecutive_failures: int = 0


@dataclass
class ComponentHealth:
    """Health status of an ADAM component."""
    name: str
    status: HealthStatus
    dependencies: Dict[str, DependencyHealth] = field(default_factory=dict)
    metrics: Dict[str, Any] = field(default_factory=dict)
    last_check: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    @property
    def is_healthy(self) -> bool:
        """Check if component is healthy."""
        return self.status == HealthStatus.HEALTHY
    
    @property
    def unhealthy_dependencies(self) -> List[str]:
        """Get list of unhealthy dependencies."""
        return [
            name for name, dep in self.dependencies.items()
            if dep.status == HealthStatus.UNHEALTHY
        ]


class DependencyMonitor:
    """
    Monitors health of external dependencies.
    
    Use this to track the availability of optional services like
    Redis, Neo4j, Kafka, and external APIs.
    """
    
    def __init__(self, component_name: str):
        self.component_name = component_name
        self._dependencies: Dict[str, DependencyHealth] = {}
        self._check_functions: Dict[str, Callable] = {}
        self._check_interval_seconds: int = 60
        self._monitoring_task: Optional[asyncio.Task] = None
    
    def register_dependency(
        self,
        name: str,
        check_fn: Callable[[], bool],
        critical: bool = False,
    ) -> None:
        """
        Register a dependency to monitor.
        
        Args:
            name: Dependency name (e.g., "redis", "neo4j")
            check_fn: Function that returns True if healthy
            critical: If True, component is unhealthy when this fails
        """
        self._check_functions[name] = check_fn
        self._dependencies[name] = DependencyHealth(
            name=name,
            status=HealthStatus.UNKNOWN,
            last_check=datetime.now(timezone.utc),
        )
        logger.debug(f"Registered dependency: {name}")
    
    async def check_dependency(self, name: str) -> DependencyHealth:
        """Check health of a single dependency."""
        if name not in self._check_functions:
            return DependencyHealth(
                name=name,
                status=HealthStatus.UNKNOWN,
                last_check=datetime.now(timezone.utc),
                error_message=f"Dependency {name} not registered",
            )
        
        check_fn = self._check_functions[name]
        start_time = datetime.now(timezone.utc)
        
        try:
            # Run check (may be sync or async)
            if asyncio.iscoroutinefunction(check_fn):
                result = await check_fn()
            else:
                result = check_fn()
            
            latency_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            
            if result:
                health = DependencyHealth(
                    name=name,
                    status=HealthStatus.HEALTHY,
                    last_check=start_time,
                    last_success=start_time,
                    check_latency_ms=latency_ms,
                    consecutive_failures=0,
                )
                
                if PROMETHEUS_AVAILABLE:
                    DEPENDENCY_STATUS.labels(dependency_name=name).set(1)
            else:
                prev = self._dependencies.get(name)
                health = DependencyHealth(
                    name=name,
                    status=HealthStatus.UNHEALTHY,
                    last_check=start_time,
                    last_success=prev.last_success if prev else None,
                    error_message="Check returned False",
                    check_latency_ms=latency_ms,
                    consecutive_failures=(prev.consecutive_failures + 1) if prev else 1,
                )
                
                if PROMETHEUS_AVAILABLE:
                    DEPENDENCY_STATUS.labels(dependency_name=name).set(0)
                    DEPENDENCY_FAILURES.labels(dependency_name=name).inc()
                    
        except Exception as e:
            latency_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            prev = self._dependencies.get(name)
            
            health = DependencyHealth(
                name=name,
                status=HealthStatus.UNHEALTHY,
                last_check=start_time,
                last_success=prev.last_success if prev else None,
                error_message=str(e),
                check_latency_ms=latency_ms,
                consecutive_failures=(prev.consecutive_failures + 1) if prev else 1,
            )
            
            if PROMETHEUS_AVAILABLE:
                DEPENDENCY_STATUS.labels(dependency_name=name).set(0)
                DEPENDENCY_FAILURES.labels(dependency_name=name).inc()
            
            logger.warning(f"Dependency {name} check failed: {e}")
        
        self._dependencies[name] = health
        return health
    
    async def check_all(self) -> Dict[str, DependencyHealth]:
        """Check all registered dependencies."""
        tasks = [
            self.check_dependency(name)
            for name in self._check_functions
        ]
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        
        return self._dependencies.copy()
    
    def get_health(self, name: str) -> Optional[DependencyHealth]:
        """Get cached health for a dependency."""
        return self._dependencies.get(name)
    
    def get_all_health(self) -> Dict[str, DependencyHealth]:
        """Get cached health for all dependencies."""
        return self._dependencies.copy()
    
    def is_available(self, name: str) -> bool:
        """Check if a dependency is available (healthy or unknown)."""
        health = self._dependencies.get(name)
        if not health:
            return True  # Assume available if not tracked
        return health.status in (HealthStatus.HEALTHY, HealthStatus.UNKNOWN)
    
    async def start_monitoring(self, interval_seconds: int = 60) -> None:
        """Start background health monitoring."""
        self._check_interval_seconds = interval_seconds
        
        async def monitor_loop():
            while True:
                try:
                    await self.check_all()
                except Exception as e:
                    logger.error(f"Health monitoring error: {e}")
                await asyncio.sleep(self._check_interval_seconds)
        
        self._monitoring_task = asyncio.create_task(monitor_loop())
        logger.info(f"Started health monitoring for {self.component_name}")
    
    async def stop_monitoring(self) -> None:
        """Stop background health monitoring."""
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
            self._monitoring_task = None
            logger.info(f"Stopped health monitoring for {self.component_name}")
    
    def get_component_health(self) -> ComponentHealth:
        """Get overall component health."""
        unhealthy = [
            name for name, dep in self._dependencies.items()
            if dep.status == HealthStatus.UNHEALTHY
        ]
        
        if not unhealthy:
            status = HealthStatus.HEALTHY
        elif len(unhealthy) < len(self._dependencies):
            status = HealthStatus.DEGRADED
        else:
            status = HealthStatus.UNHEALTHY
        
        health = ComponentHealth(
            name=self.component_name,
            status=status,
            dependencies=self._dependencies.copy(),
        )
        
        if PROMETHEUS_AVAILABLE:
            COMPONENT_HEALTH.labels(component_name=self.component_name).set(
                1 if status == HealthStatus.HEALTHY else 0
            )
        
        return health


def with_fallback(fallback_value: Any, log_warning: bool = True):
    """
    Decorator that provides a fallback value when a dependency is unavailable.
    
    Usage:
        @with_fallback(default_value)
        async def method_requiring_dependency(self):
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                if log_warning:
                    logger.warning(
                        f"{func.__name__} failed, using fallback: {e}"
                    )
                return fallback_value
        return wrapper
    return decorator


# =============================================================================
# GLOBAL HEALTH REGISTRY
# =============================================================================

class HealthRegistry:
    """
    Global registry for component health monitoring.
    
    Provides centralized health status for the entire ADAM platform.
    """
    
    _instance: Optional["HealthRegistry"] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._monitors: Dict[str, DependencyMonitor] = {}
        return cls._instance
    
    def register_monitor(self, monitor: DependencyMonitor) -> None:
        """Register a component's dependency monitor."""
        self._monitors[monitor.component_name] = monitor
    
    def get_monitor(self, component_name: str) -> Optional[DependencyMonitor]:
        """Get a component's dependency monitor."""
        return self._monitors.get(component_name)
    
    async def check_all_health(self) -> Dict[str, ComponentHealth]:
        """Check health of all registered components."""
        results = {}
        for name, monitor in self._monitors.items():
            await monitor.check_all()
            results[name] = monitor.get_component_health()
        return results
    
    def get_platform_health(self) -> Dict[str, Any]:
        """Get overall platform health status."""
        components = {
            name: monitor.get_component_health()
            for name, monitor in self._monitors.items()
        }
        
        unhealthy = [
            name for name, health in components.items()
            if health.status == HealthStatus.UNHEALTHY
        ]
        
        degraded = [
            name for name, health in components.items()
            if health.status == HealthStatus.DEGRADED
        ]
        
        if unhealthy:
            overall_status = HealthStatus.UNHEALTHY
        elif degraded:
            overall_status = HealthStatus.DEGRADED
        else:
            overall_status = HealthStatus.HEALTHY
        
        return {
            "status": overall_status.value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "components": {
                name: {
                    "status": health.status.value,
                    "unhealthy_dependencies": health.unhealthy_dependencies,
                }
                for name, health in components.items()
            },
            "unhealthy_components": unhealthy,
            "degraded_components": degraded,
        }


def get_health_registry() -> HealthRegistry:
    """Get the global health registry."""
    return HealthRegistry()
