# =============================================================================
# Latency Budget — Request-Scoped Timeout Tracking
# Location: adam/infrastructure/resilience/latency_budget.py
# =============================================================================

"""
Tracks remaining time budget for a single request.

The 120ms SLA means every component must cooperate: prefetch gets 40ms,
cascade gets 60ms, DAG gets the remainder. If prefetch takes 35ms, cascade
inherits 5ms of slack. If cascade blows its budget, DAG returns partial.

Usage:
    budget = LatencyBudget(total_ms=120)

    # Each component checks + allocates
    prefetch_timeout = budget.allocate("prefetch", max_ms=40)
    ...do prefetch within prefetch_timeout seconds...

    cascade_timeout = budget.allocate("cascade", max_ms=60)
    ...do cascade within cascade_timeout seconds...

    if budget.has_budget:
        dag_timeout = budget.remaining_seconds
        ...run DAG...
    else:
        ...return partial results...
"""

import logging
import time
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class LatencyBudget:
    """Request-scoped latency budget tracker.

    Thread-safe for single-request use (no shared state between requests).
    """

    def __init__(self, total_ms: float = 120.0, reserve_ms: float = 10.0):
        """
        Args:
            total_ms: Total budget for the request (default 120ms SLA).
            reserve_ms: Reserved for serialization/response overhead.
        """
        self._total_ms = total_ms
        self._reserve_ms = reserve_ms
        self._start = time.monotonic()
        self._allocations: Dict[str, float] = {}

    @property
    def elapsed_ms(self) -> float:
        """Milliseconds elapsed since budget creation."""
        return (time.monotonic() - self._start) * 1000

    @property
    def remaining_ms(self) -> float:
        """Milliseconds remaining (including reserve)."""
        return max(0.0, self._total_ms - self.elapsed_ms)

    @property
    def usable_ms(self) -> float:
        """Milliseconds remaining minus reserve (available for work)."""
        return max(0.0, self._total_ms - self._reserve_ms - self.elapsed_ms)

    @property
    def remaining_seconds(self) -> float:
        """Seconds remaining (for asyncio.wait_for timeout parameter)."""
        return self.usable_ms / 1000.0

    @property
    def has_budget(self) -> bool:
        """True if there's usable time remaining."""
        return self.usable_ms > 1.0  # At least 1ms

    def allocate(self, component: str, max_ms: float) -> float:
        """Allocate time to a component, returning timeout in seconds.

        Returns min(max_ms, remaining usable budget) converted to seconds.
        If no budget remains, returns 0.001 (1ms — effectively immediate timeout).

        Args:
            component: Name for logging/metrics
            max_ms: Maximum time this component should take

        Returns:
            Timeout in seconds for use with asyncio.wait_for()
        """
        available = self.usable_ms
        allocated_ms = min(max_ms, available)

        if allocated_ms < 1.0:
            logger.warning(
                "Budget exhausted: %s requested %.0fms but only %.1fms available "
                "(elapsed=%.0fms, total=%.0fms)",
                component, max_ms, available, self.elapsed_ms, self._total_ms,
            )
            allocated_ms = 1.0  # Minimum 1ms to avoid zero-timeout

        self._allocations[component] = allocated_ms
        timeout_seconds = allocated_ms / 1000.0

        logger.debug(
            "Budget allocated: %s=%.0fms (%.0fms remaining of %.0fms)",
            component, allocated_ms, available - allocated_ms, self._total_ms,
        )

        return timeout_seconds

    @property
    def summary(self) -> Dict[str, float]:
        """Budget usage summary for logging/metrics."""
        return {
            "total_ms": self._total_ms,
            "elapsed_ms": round(self.elapsed_ms, 1),
            "remaining_ms": round(self.remaining_ms, 1),
            "reserve_ms": self._reserve_ms,
            "allocations": dict(self._allocations),
        }
