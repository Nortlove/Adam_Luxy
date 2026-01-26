# =============================================================================
# ADAM Performance Package (#09, #31)
# =============================================================================

"""
PERFORMANCE & LATENCY OPTIMIZATION

Infrastructure for sub-100ms decision latency.

Components:
- Fast path execution for simple decisions
- Multi-level caching
- Request coalescing
- Circuit breakers
- Latency budgets
"""

from adam.performance.latency import (
    LatencyBudget,
    LatencyTracker,
    ExecutionPath,
)
from adam.performance.fast_path import FastPathRouter
from adam.performance.cache_manager import MultiLevelCacheManager
from adam.performance.circuit_breaker import CircuitBreaker, CircuitState
from adam.performance.service import PerformanceService

__all__ = [
    # Latency
    "LatencyBudget",
    "LatencyTracker",
    "ExecutionPath",
    # Fast path
    "FastPathRouter",
    # Caching
    "MultiLevelCacheManager",
    # Circuit breaker
    "CircuitBreaker",
    "CircuitState",
    # Service
    "PerformanceService",
]
