# =============================================================================
# ADAM Infrastructure: Circuit Breaker with Graceful Degradation
# Location: adam/infrastructure/resilience/circuit_breaker.py
# =============================================================================

"""
CIRCUIT BREAKER WITH GRACEFUL DEGRADATION

Implements the Circuit Breaker pattern for Neo4j, Redis, Kafka, and other
external dependencies. This prevents cascade failures and enables graceful
degradation when services are unavailable.

States:
- CLOSED: Normal operation, requests pass through
- OPEN: Service unavailable, fail fast with fallback
- HALF_OPEN: Testing if service recovered

Features:
- Exponential backoff for retry intervals
- Configurable failure thresholds per service
- Graceful degradation with fallback values
- Metrics emission for observability
- Async-native implementation

Reference: Nygard (2007) "Release It!" - Circuit Breaker Pattern
"""

from typing import Dict, Optional, Any, Callable, TypeVar, Generic
from datetime import datetime, timedelta
from enum import Enum
from functools import wraps
from dataclasses import dataclass, field
import asyncio
import logging
import time

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

T = TypeVar('T')


# =============================================================================
# CIRCUIT BREAKER STATE
# =============================================================================

class CircuitState(str, Enum):
    """Circuit breaker states."""
    CLOSED = "closed"       # Normal operation
    OPEN = "open"           # Failing fast
    HALF_OPEN = "half_open" # Testing recovery


@dataclass
class CircuitBreakerConfig:
    """Configuration for a circuit breaker."""
    
    # Name of the service/dependency
    name: str
    
    # Number of failures before opening circuit
    failure_threshold: int = 5
    
    # Number of successes needed to close from half-open
    success_threshold: int = 3
    
    # Time to wait before testing recovery (seconds)
    recovery_timeout: float = 30.0
    
    # Exponential backoff factor for recovery timeout
    backoff_factor: float = 2.0
    
    # Maximum recovery timeout (seconds)
    max_recovery_timeout: float = 300.0
    
    # Timeout for individual calls (seconds)
    call_timeout: float = 5.0
    
    # Whether to track slow calls as partial failures
    slow_call_threshold: float = 2.0
    slow_call_rate_threshold: float = 0.5


@dataclass
class CircuitBreakerState:
    """Runtime state for a circuit breaker."""
    
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: Optional[datetime] = None
    opened_at: Optional[datetime] = None
    current_recovery_timeout: float = 30.0
    
    # Metrics
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    rejected_calls: int = 0
    slow_calls: int = 0


# =============================================================================
# CIRCUIT BREAKER
# =============================================================================

class CircuitBreaker:
    """
    Circuit breaker for a single service/dependency.
    
    Usage:
        breaker = CircuitBreaker(CircuitBreakerConfig(name="neo4j"))
        
        try:
            result = await breaker.call(async_function, *args, **kwargs)
        except CircuitOpenError:
            # Use fallback
            result = fallback_value
    """
    
    def __init__(self, config: CircuitBreakerConfig):
        self.config = config
        self._state = CircuitBreakerState(
            current_recovery_timeout=config.recovery_timeout
        )
        self._lock = asyncio.Lock()
    
    @property
    def state(self) -> CircuitState:
        """Get current circuit state."""
        return self._state.state
    
    @property
    def is_closed(self) -> bool:
        """Check if circuit is closed (normal operation)."""
        return self._state.state == CircuitState.CLOSED
    
    @property
    def is_open(self) -> bool:
        """Check if circuit is open (failing fast)."""
        return self._state.state == CircuitState.OPEN
    
    async def call(
        self,
        func: Callable[..., T],
        *args,
        fallback: Optional[T] = None,
        **kwargs
    ) -> T:
        """
        Execute a call through the circuit breaker.
        
        Args:
            func: Async function to call
            *args: Arguments for func
            fallback: Value to return if circuit is open
            **kwargs: Keyword arguments for func
            
        Returns:
            Result of func or fallback
            
        Raises:
            CircuitOpenError: If circuit is open and no fallback provided
        """
        async with self._lock:
            self._state.total_calls += 1
            
            # Check if we should transition from OPEN to HALF_OPEN
            if self._state.state == CircuitState.OPEN:
                if self._should_attempt_recovery():
                    self._state.state = CircuitState.HALF_OPEN
                    self._state.success_count = 0
                    logger.info(f"Circuit {self.config.name}: OPEN -> HALF_OPEN")
                else:
                    self._state.rejected_calls += 1
                    logger.debug(f"Circuit {self.config.name}: rejecting call (OPEN)")
                    if fallback is not None:
                        return fallback
                    raise CircuitOpenError(self.config.name)
        
        # Execute the call
        start_time = time.time()
        try:
            result = await asyncio.wait_for(
                func(*args, **kwargs),
                timeout=self.config.call_timeout
            )
            duration = time.time() - start_time
            
            await self._on_success(duration)
            return result
            
        except asyncio.TimeoutError:
            await self._on_failure("timeout")
            if fallback is not None:
                return fallback
            raise
            
        except Exception as e:
            await self._on_failure(str(e))
            if fallback is not None:
                return fallback
            raise
    
    async def _on_success(self, duration: float) -> None:
        """Handle successful call."""
        async with self._lock:
            self._state.successful_calls += 1
            
            # Track slow calls
            if duration > self.config.slow_call_threshold:
                self._state.slow_calls += 1
            
            if self._state.state == CircuitState.HALF_OPEN:
                self._state.success_count += 1
                
                if self._state.success_count >= self.config.success_threshold:
                    # Close the circuit - service recovered
                    self._state.state = CircuitState.CLOSED
                    self._state.failure_count = 0
                    self._state.current_recovery_timeout = self.config.recovery_timeout
                    logger.info(f"Circuit {self.config.name}: HALF_OPEN -> CLOSED")
            
            elif self._state.state == CircuitState.CLOSED:
                # Reset failure count on success
                if self._state.failure_count > 0:
                    self._state.failure_count = max(0, self._state.failure_count - 1)
    
    async def _on_failure(self, reason: str) -> None:
        """Handle failed call."""
        async with self._lock:
            self._state.failed_calls += 1
            self._state.failure_count += 1
            self._state.last_failure_time = datetime.now()
            
            logger.warning(
                f"Circuit {self.config.name}: failure ({self._state.failure_count}/"
                f"{self.config.failure_threshold}) - {reason}"
            )
            
            if self._state.state == CircuitState.HALF_OPEN:
                # Revert to open on any failure during testing
                self._open_circuit()
                # Increase recovery timeout with backoff
                self._state.current_recovery_timeout = min(
                    self._state.current_recovery_timeout * self.config.backoff_factor,
                    self.config.max_recovery_timeout
                )
                logger.info(
                    f"Circuit {self.config.name}: HALF_OPEN -> OPEN "
                    f"(next recovery in {self._state.current_recovery_timeout}s)"
                )
            
            elif self._state.state == CircuitState.CLOSED:
                if self._state.failure_count >= self.config.failure_threshold:
                    self._open_circuit()
                    logger.warning(f"Circuit {self.config.name}: CLOSED -> OPEN")
    
    def _open_circuit(self) -> None:
        """Open the circuit."""
        self._state.state = CircuitState.OPEN
        self._state.opened_at = datetime.now()
        self._state.success_count = 0
    
    def _should_attempt_recovery(self) -> bool:
        """Check if we should attempt recovery from OPEN state."""
        if self._state.opened_at is None:
            return True
        
        elapsed = (datetime.now() - self._state.opened_at).total_seconds()
        return elapsed >= self._state.current_recovery_timeout
    
    def get_stats(self) -> Dict[str, Any]:
        """Get circuit breaker statistics."""
        return {
            "name": self.config.name,
            "state": self._state.state.value,
            "failure_count": self._state.failure_count,
            "success_count": self._state.success_count,
            "total_calls": self._state.total_calls,
            "successful_calls": self._state.successful_calls,
            "failed_calls": self._state.failed_calls,
            "rejected_calls": self._state.rejected_calls,
            "slow_calls": self._state.slow_calls,
            "current_recovery_timeout": self._state.current_recovery_timeout,
            "success_rate": (
                self._state.successful_calls / max(1, self._state.total_calls)
            ),
        }
    
    def reset(self) -> None:
        """Manually reset the circuit breaker."""
        self._state = CircuitBreakerState(
            current_recovery_timeout=self.config.recovery_timeout
        )
        logger.info(f"Circuit {self.config.name}: manually reset")


class CircuitOpenError(Exception):
    """Raised when circuit is open and no fallback is provided."""
    
    def __init__(self, service_name: str):
        self.service_name = service_name
        super().__init__(f"Circuit breaker open for {service_name}")


# =============================================================================
# CIRCUIT BREAKER REGISTRY
# =============================================================================

class CircuitBreakerRegistry:
    """
    Registry for managing multiple circuit breakers.
    
    Usage:
        registry = CircuitBreakerRegistry()
        registry.register("neo4j", CircuitBreakerConfig(name="neo4j", failure_threshold=3))
        
        result = await registry.call("neo4j", async_neo4j_function, fallback={})
    """
    
    # Default configurations for common services
    DEFAULT_CONFIGS = {
        "neo4j": CircuitBreakerConfig(
            name="neo4j",
            failure_threshold=3,
            recovery_timeout=30.0,
            call_timeout=10.0,
        ),
        "redis": CircuitBreakerConfig(
            name="redis",
            failure_threshold=5,
            recovery_timeout=10.0,
            call_timeout=2.0,
        ),
        "kafka": CircuitBreakerConfig(
            name="kafka",
            failure_threshold=5,
            recovery_timeout=30.0,
            call_timeout=5.0,
        ),
        "llm": CircuitBreakerConfig(
            name="llm",
            failure_threshold=2,
            recovery_timeout=60.0,
            call_timeout=30.0,
        ),
    }
    
    def __init__(self):
        self._breakers: Dict[str, CircuitBreaker] = {}
        self._lock = asyncio.Lock()
    
    def register(
        self,
        name: str,
        config: Optional[CircuitBreakerConfig] = None,
    ) -> CircuitBreaker:
        """Register a circuit breaker."""
        if config is None:
            config = self.DEFAULT_CONFIGS.get(
                name,
                CircuitBreakerConfig(name=name)
            )
        
        breaker = CircuitBreaker(config)
        self._breakers[name] = breaker
        logger.info(f"Registered circuit breaker: {name}")
        return breaker
    
    def get(self, name: str) -> Optional[CircuitBreaker]:
        """Get a circuit breaker by name."""
        return self._breakers.get(name)
    
    def get_or_create(
        self,
        name: str,
        config: Optional[CircuitBreakerConfig] = None,
    ) -> CircuitBreaker:
        """Get or create a circuit breaker."""
        if name not in self._breakers:
            return self.register(name, config)
        return self._breakers[name]
    
    async def call(
        self,
        service_name: str,
        func: Callable[..., T],
        *args,
        fallback: Optional[T] = None,
        **kwargs
    ) -> T:
        """
        Execute a call through a registered circuit breaker.
        
        Args:
            service_name: Name of the service (must be registered)
            func: Async function to call
            *args: Arguments for func
            fallback: Value to return if circuit is open
            **kwargs: Keyword arguments for func
            
        Returns:
            Result of func or fallback
        """
        breaker = self.get_or_create(service_name)
        return await breaker.call(func, *args, fallback=fallback, **kwargs)
    
    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all circuit breakers."""
        return {name: breaker.get_stats() for name, breaker in self._breakers.items()}
    
    def get_health(self) -> Dict[str, Any]:
        """Get overall health status."""
        stats = self.get_all_stats()
        
        healthy = all(s["state"] == "closed" for s in stats.values())
        degraded = any(s["state"] == "half_open" for s in stats.values())
        unhealthy_services = [n for n, s in stats.items() if s["state"] == "open"]
        
        return {
            "healthy": healthy,
            "degraded": degraded,
            "unhealthy_services": unhealthy_services,
            "services": stats,
        }


# =============================================================================
# DECORATOR FOR CIRCUIT BREAKER PROTECTION
# =============================================================================

def circuit_protected(
    service_name: str,
    registry: Optional[CircuitBreakerRegistry] = None,
    fallback: Optional[Any] = None,
):
    """
    Decorator to protect a function with a circuit breaker.
    
    Usage:
        @circuit_protected("neo4j", fallback={})
        async def get_user_data(user_id: str) -> Dict:
            # Neo4j call here
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            reg = registry or _global_registry
            return await reg.call(service_name, func, *args, fallback=fallback, **kwargs)
        return wrapper
    return decorator


# =============================================================================
# GLOBAL REGISTRY
# =============================================================================

_global_registry: Optional[CircuitBreakerRegistry] = None


def get_circuit_breaker_registry() -> CircuitBreakerRegistry:
    """Get the global circuit breaker registry."""
    global _global_registry
    if _global_registry is None:
        _global_registry = CircuitBreakerRegistry()
        
        # Register default breakers
        for name in CircuitBreakerRegistry.DEFAULT_CONFIGS:
            _global_registry.register(name)
    
    return _global_registry


def get_circuit_breaker(name: str) -> CircuitBreaker:
    """Get a circuit breaker by name from the global registry."""
    return get_circuit_breaker_registry().get_or_create(name)
