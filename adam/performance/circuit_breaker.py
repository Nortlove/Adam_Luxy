# =============================================================================
# ADAM Circuit Breaker
# Location: adam/performance/circuit_breaker.py
# =============================================================================

"""
CIRCUIT BREAKER

Prevent cascade failures by failing fast when dependencies are unhealthy.
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, Optional

from prometheus_client import Counter, Gauge

logger = logging.getLogger(__name__)


# =============================================================================
# METRICS
# =============================================================================

CIRCUIT_STATE = Gauge(
    "adam_circuit_breaker_state",
    "Circuit breaker state (0=closed, 1=open, 2=half-open)",
    ["circuit"],
)

CIRCUIT_TRIPS = Counter(
    "adam_circuit_breaker_trips_total",
    "Circuit breaker trips",
    ["circuit"],
)


# =============================================================================
# CIRCUIT STATES
# =============================================================================

class CircuitState(str, Enum):
    """Circuit breaker states."""
    
    CLOSED = "closed"       # Normal operation
    OPEN = "open"           # Failing fast
    HALF_OPEN = "half_open" # Testing recovery


@dataclass
class CircuitStats:
    """Statistics for a circuit breaker."""
    
    success_count: int = 0
    failure_count: int = 0
    last_failure_time: Optional[float] = None
    last_success_time: Optional[float] = None
    
    # Window tracking
    window_start: float = field(default_factory=time.time)
    window_failures: int = 0
    
    def record_success(self) -> None:
        self.success_count += 1
        self.last_success_time = time.time()
    
    def record_failure(self) -> None:
        self.failure_count += 1
        self.last_failure_time = time.time()
        self.window_failures += 1
    
    def reset_window(self) -> None:
        self.window_start = time.time()
        self.window_failures = 0
    
    @property
    def failure_rate(self) -> float:
        total = self.success_count + self.failure_count
        if total == 0:
            return 0.0
        return self.failure_count / total


# =============================================================================
# CIRCUIT BREAKER
# =============================================================================

class CircuitBreaker:
    """
    Circuit breaker for graceful degradation.
    
    Usage:
        breaker = CircuitBreaker("neo4j")
        
        async with breaker.protect():
            result = await neo4j.query(...)
    """
    
    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        half_open_max_calls: int = 3,
        window_size: float = 60.0,
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls
        self.window_size = window_size
        
        self._state = CircuitState.CLOSED
        self._stats = CircuitStats()
        self._half_open_calls = 0
        self._lock = asyncio.Lock()
        
        CIRCUIT_STATE.labels(circuit=name).set(0)
    
    @property
    def state(self) -> CircuitState:
        return self._state
    
    @property
    def is_closed(self) -> bool:
        return self._state == CircuitState.CLOSED
    
    @property
    def is_open(self) -> bool:
        return self._state == CircuitState.OPEN
    
    async def protect(self):
        """Context manager for protected calls."""
        return _CircuitContext(self)
    
    async def call(
        self,
        func: Callable,
        *args,
        fallback: Optional[Callable] = None,
        **kwargs,
    ) -> Any:
        """
        Execute a function with circuit breaker protection.
        """
        async with self.protect():
            try:
                # Check if we should allow the call
                if not await self._should_allow():
                    if fallback:
                        return await fallback(*args, **kwargs)
                    raise CircuitOpenError(f"Circuit {self.name} is open")
                
                # Execute
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)
                
                # Record success
                await self._record_success()
                
                return result
                
            except CircuitOpenError:
                raise
            except Exception as e:
                await self._record_failure()
                raise
    
    async def _should_allow(self) -> bool:
        """Check if call should be allowed."""
        async with self._lock:
            if self._state == CircuitState.CLOSED:
                return True
            
            if self._state == CircuitState.OPEN:
                # Check if recovery timeout passed
                if self._stats.last_failure_time:
                    elapsed = time.time() - self._stats.last_failure_time
                    if elapsed >= self.recovery_timeout:
                        self._transition_to(CircuitState.HALF_OPEN)
                        return True
                return False
            
            if self._state == CircuitState.HALF_OPEN:
                # Allow limited calls in half-open
                if self._half_open_calls < self.half_open_max_calls:
                    self._half_open_calls += 1
                    return True
                return False
            
            return False
    
    async def _record_success(self) -> None:
        """Record a successful call."""
        async with self._lock:
            self._stats.record_success()
            
            if self._state == CircuitState.HALF_OPEN:
                # Check if we should close
                if self._half_open_calls >= self.half_open_max_calls:
                    self._transition_to(CircuitState.CLOSED)
                    self._half_open_calls = 0
    
    async def _record_failure(self) -> None:
        """Record a failed call."""
        async with self._lock:
            self._stats.record_failure()
            
            # Check window
            now = time.time()
            if now - self._stats.window_start > self.window_size:
                self._stats.reset_window()
            
            if self._state == CircuitState.CLOSED:
                # Check if we should open
                if self._stats.window_failures >= self.failure_threshold:
                    self._transition_to(CircuitState.OPEN)
            
            elif self._state == CircuitState.HALF_OPEN:
                # Any failure in half-open goes back to open
                self._transition_to(CircuitState.OPEN)
                self._half_open_calls = 0
    
    def _transition_to(self, new_state: CircuitState) -> None:
        """Transition to a new state."""
        old_state = self._state
        self._state = new_state
        
        # Update metric
        state_value = {"closed": 0, "open": 1, "half_open": 2}
        CIRCUIT_STATE.labels(circuit=self.name).set(state_value[new_state.value])
        
        if new_state == CircuitState.OPEN:
            CIRCUIT_TRIPS.labels(circuit=self.name).inc()
        
        logger.info(
            f"Circuit {self.name} transitioned: {old_state.value} → {new_state.value}"
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """Get circuit breaker statistics."""
        return {
            "name": self.name,
            "state": self._state.value,
            "success_count": self._stats.success_count,
            "failure_count": self._stats.failure_count,
            "failure_rate": self._stats.failure_rate,
            "window_failures": self._stats.window_failures,
            "last_failure": self._stats.last_failure_time,
        }


class _CircuitContext:
    """Context manager for circuit breaker."""
    
    def __init__(self, breaker: CircuitBreaker):
        self.breaker = breaker
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None and exc_type is not CircuitOpenError:
            await self.breaker._record_failure()
        elif exc_type is None:
            await self.breaker._record_success()
        return False


class CircuitOpenError(Exception):
    """Raised when circuit is open."""
    pass
