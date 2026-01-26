# =============================================================================
# ADAM Health Monitoring Service
# Location: adam/monitoring/health_service.py
# =============================================================================

"""
HEALTH MONITORING SERVICE

Aggregates health from all ADAM components.

Provides:
1. Component health checks
2. System health aggregation
3. Health history tracking
4. Dependency health
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS
# =============================================================================

class HealthStatus(str, Enum):
    """Component health status."""
    
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class ComponentType(str, Enum):
    """Types of components."""
    
    INFRASTRUCTURE = "infrastructure"
    CORE_SERVICE = "core_service"
    REASONING = "reasoning"
    LEARNING = "learning"
    PLATFORM = "platform"


# =============================================================================
# MODELS
# =============================================================================

class ComponentHealth(BaseModel):
    """Health of a single component."""
    
    component_name: str
    component_type: ComponentType
    
    # Status
    status: HealthStatus = Field(default=HealthStatus.UNKNOWN)
    
    # Metrics
    latency_ms: float = Field(ge=0.0, default=0.0)
    error_rate: float = Field(ge=0.0, le=1.0, default=0.0)
    throughput_rps: float = Field(ge=0.0, default=0.0)
    
    # Dependencies
    dependencies: List[str] = Field(default_factory=list)
    dependency_health: Dict[str, HealthStatus] = Field(default_factory=dict)
    
    # Details
    details: Dict[str, Any] = Field(default_factory=dict)
    
    # Timing
    last_check: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    check_duration_ms: float = Field(ge=0.0, default=0.0)


class SystemHealth(BaseModel):
    """Overall system health."""
    
    health_id: str = Field(
        default_factory=lambda: f"health_{uuid4().hex[:8]}"
    )
    
    # Overall status
    status: HealthStatus = Field(default=HealthStatus.UNKNOWN)
    health_score: float = Field(ge=0.0, le=1.0, default=1.0)
    
    # Component health
    components: Dict[str, ComponentHealth] = Field(default_factory=dict)
    
    # Summary
    healthy_count: int = Field(default=0, ge=0)
    degraded_count: int = Field(default=0, ge=0)
    unhealthy_count: int = Field(default=0, ge=0)
    
    # Issues
    issues: List[str] = Field(default_factory=list)
    
    # Timing
    checked_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    total_check_duration_ms: float = Field(ge=0.0, default=0.0)


# =============================================================================
# HEALTH CHECK FUNCTIONS
# =============================================================================

class HealthCheck:
    """Base health check."""
    
    def __init__(
        self,
        name: str,
        component_type: ComponentType,
        dependencies: Optional[List[str]] = None,
    ):
        self.name = name
        self.component_type = component_type
        self.dependencies = dependencies or []
    
    async def check(self) -> ComponentHealth:
        """Run health check."""
        raise NotImplementedError


class Neo4jHealthCheck(HealthCheck):
    """Health check for Neo4j."""
    
    def __init__(self, driver=None):
        super().__init__(
            name="neo4j",
            component_type=ComponentType.INFRASTRUCTURE,
        )
        self.driver = driver
    
    async def check(self) -> ComponentHealth:
        start = datetime.now(timezone.utc)
        
        try:
            if self.driver:
                async with self.driver.session() as session:
                    result = await session.run("RETURN 1")
                    await result.single()
                
                status = HealthStatus.HEALTHY
            else:
                status = HealthStatus.UNKNOWN
        except Exception as e:
            logger.error(f"Neo4j health check failed: {e}")
            status = HealthStatus.UNHEALTHY
        
        duration = (datetime.now(timezone.utc) - start).total_seconds() * 1000
        
        return ComponentHealth(
            component_name=self.name,
            component_type=self.component_type,
            status=status,
            latency_ms=duration,
            last_check=datetime.now(timezone.utc),
            check_duration_ms=duration,
        )


class RedisHealthCheck(HealthCheck):
    """Health check for Redis."""
    
    def __init__(self, cache=None):
        super().__init__(
            name="redis",
            component_type=ComponentType.INFRASTRUCTURE,
        )
        self.cache = cache
    
    async def check(self) -> ComponentHealth:
        start = datetime.now(timezone.utc)
        
        try:
            if self.cache and hasattr(self.cache, 'client') and self.cache.client:
                await self.cache.client.ping()
                status = HealthStatus.HEALTHY
            else:
                status = HealthStatus.UNKNOWN
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            status = HealthStatus.UNHEALTHY
        
        duration = (datetime.now(timezone.utc) - start).total_seconds() * 1000
        
        return ComponentHealth(
            component_name=self.name,
            component_type=self.component_type,
            status=status,
            latency_ms=duration,
            last_check=datetime.now(timezone.utc),
            check_duration_ms=duration,
        )


class BlackboardHealthCheck(HealthCheck):
    """Health check for Blackboard."""
    
    def __init__(self, blackboard=None):
        super().__init__(
            name="blackboard",
            component_type=ComponentType.CORE_SERVICE,
            dependencies=["redis"],
        )
        self.blackboard = blackboard
    
    async def check(self) -> ComponentHealth:
        start = datetime.now(timezone.utc)
        status = HealthStatus.HEALTHY if self.blackboard else HealthStatus.UNKNOWN
        duration = (datetime.now(timezone.utc) - start).total_seconds() * 1000
        
        return ComponentHealth(
            component_name=self.name,
            component_type=self.component_type,
            status=status,
            dependencies=self.dependencies,
            last_check=datetime.now(timezone.utc),
            check_duration_ms=duration,
        )


class MetaLearnerHealthCheck(HealthCheck):
    """Health check for Meta-Learner."""
    
    def __init__(self, meta_learner=None):
        super().__init__(
            name="meta_learner",
            component_type=ComponentType.REASONING,
            dependencies=["blackboard", "redis"],
        )
        self.meta_learner = meta_learner
    
    async def check(self) -> ComponentHealth:
        start = datetime.now(timezone.utc)
        status = HealthStatus.HEALTHY if self.meta_learner else HealthStatus.UNKNOWN
        duration = (datetime.now(timezone.utc) - start).total_seconds() * 1000
        
        return ComponentHealth(
            component_name=self.name,
            component_type=self.component_type,
            status=status,
            dependencies=self.dependencies,
            last_check=datetime.now(timezone.utc),
            check_duration_ms=duration,
        )


class AtomDAGHealthCheck(HealthCheck):
    """Health check for Atom DAG."""
    
    def __init__(self, atom_dag=None):
        super().__init__(
            name="atom_dag",
            component_type=ComponentType.REASONING,
            dependencies=["blackboard", "neo4j"],
        )
        self.atom_dag = atom_dag
    
    async def check(self) -> ComponentHealth:
        start = datetime.now(timezone.utc)
        status = HealthStatus.HEALTHY if self.atom_dag else HealthStatus.UNKNOWN
        duration = (datetime.now(timezone.utc) - start).total_seconds() * 1000
        
        return ComponentHealth(
            component_name=self.name,
            component_type=self.component_type,
            status=status,
            dependencies=self.dependencies,
            last_check=datetime.now(timezone.utc),
            check_duration_ms=duration,
        )


class GradientBridgeHealthCheck(HealthCheck):
    """Health check for Gradient Bridge."""
    
    def __init__(self, gradient_bridge=None):
        super().__init__(
            name="gradient_bridge",
            component_type=ComponentType.LEARNING,
            dependencies=["blackboard", "redis", "neo4j"],
        )
        self.gradient_bridge = gradient_bridge
    
    async def check(self) -> ComponentHealth:
        start = datetime.now(timezone.utc)
        status = HealthStatus.HEALTHY if self.gradient_bridge else HealthStatus.UNKNOWN
        duration = (datetime.now(timezone.utc) - start).total_seconds() * 1000
        
        return ComponentHealth(
            component_name=self.name,
            component_type=self.component_type,
            status=status,
            dependencies=self.dependencies,
            last_check=datetime.now(timezone.utc),
            check_duration_ms=duration,
        )


# =============================================================================
# HEALTH MONITORING SERVICE
# =============================================================================

class HealthMonitoringService:
    """
    Service for monitoring system health.
    """
    
    def __init__(self, container=None):
        self.container = container
        self.health_checks: List[HealthCheck] = []
        self.history: List[SystemHealth] = []
        self.last_health: Optional[SystemHealth] = None
        
        self._setup_checks()
    
    def _setup_checks(self) -> None:
        """Set up health checks."""
        if self.container:
            self.health_checks = [
                Neo4jHealthCheck(self.container.neo4j_driver),
                RedisHealthCheck(self.container.redis_cache),
                BlackboardHealthCheck(self.container.blackboard),
                MetaLearnerHealthCheck(self.container.meta_learner),
                AtomDAGHealthCheck(self.container.atom_dag),
                GradientBridgeHealthCheck(self.container.gradient_bridge),
            ]
        else:
            # Default checks without container
            self.health_checks = [
                Neo4jHealthCheck(),
                RedisHealthCheck(),
                BlackboardHealthCheck(),
                MetaLearnerHealthCheck(),
                AtomDAGHealthCheck(),
                GradientBridgeHealthCheck(),
            ]
    
    async def check_all(self) -> SystemHealth:
        """Run all health checks."""
        start = datetime.now(timezone.utc)
        
        system_health = SystemHealth()
        
        # Run all checks in parallel
        tasks = [check.check() for check in self.health_checks]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Health check failed: {result}")
                continue
            
            if isinstance(result, ComponentHealth):
                system_health.components[result.component_name] = result
                
                if result.status == HealthStatus.HEALTHY:
                    system_health.healthy_count += 1
                elif result.status == HealthStatus.DEGRADED:
                    system_health.degraded_count += 1
                elif result.status == HealthStatus.UNHEALTHY:
                    system_health.unhealthy_count += 1
                    system_health.issues.append(
                        f"{result.component_name} is unhealthy"
                    )
        
        # Compute overall status
        if system_health.unhealthy_count > 0:
            system_health.status = HealthStatus.UNHEALTHY
        elif system_health.degraded_count > 0:
            system_health.status = HealthStatus.DEGRADED
        elif system_health.healthy_count > 0:
            system_health.status = HealthStatus.HEALTHY
        else:
            system_health.status = HealthStatus.UNKNOWN
        
        # Compute health score
        total = len(system_health.components)
        if total > 0:
            system_health.health_score = (
                system_health.healthy_count + 0.5 * system_health.degraded_count
            ) / total
        
        # Timing
        system_health.total_check_duration_ms = (
            datetime.now(timezone.utc) - start
        ).total_seconds() * 1000
        system_health.checked_at = datetime.now(timezone.utc)
        
        # Store
        self.last_health = system_health
        self.history.append(system_health)
        
        # Keep only last 100
        if len(self.history) > 100:
            self.history = self.history[-100:]
        
        return system_health
    
    def get_component_health(
        self,
        component_name: str,
    ) -> Optional[ComponentHealth]:
        """Get health of a specific component."""
        if self.last_health and component_name in self.last_health.components:
            return self.last_health.components[component_name]
        return None
    
    def get_health_history(
        self,
        limit: int = 10,
    ) -> List[SystemHealth]:
        """Get health history."""
        return self.history[-limit:]
    
    def is_healthy(self) -> bool:
        """Check if system is healthy."""
        if not self.last_health:
            return False
        return self.last_health.status == HealthStatus.HEALTHY
    
    async def wait_for_healthy(
        self,
        timeout_seconds: int = 60,
        check_interval_seconds: int = 5,
    ) -> bool:
        """Wait for system to become healthy."""
        start = datetime.now(timezone.utc)
        deadline = start + timedelta(seconds=timeout_seconds)
        
        while datetime.now(timezone.utc) < deadline:
            health = await self.check_all()
            if health.status == HealthStatus.HEALTHY:
                return True
            
            await asyncio.sleep(check_interval_seconds)
        
        return False
