# =============================================================================
# ADAM Performance Service
# Location: adam/performance/service.py
# =============================================================================

"""
PERFORMANCE SERVICE

Unified service for performance optimization.
"""

import logging
from typing import Any, Dict, Optional

from adam.performance.latency import (
    LatencyBudget,
    LatencyTracker,
    ExecutionPath,
)
from adam.performance.fast_path import (
    FastPathRouter,
    FastPathCriteria,
    FastPathDecision,
)
from adam.performance.cache_manager import (
    MultiLevelCacheManager,
    CacheConfig,
)
from adam.performance.circuit_breaker import CircuitBreaker

logger = logging.getLogger(__name__)


class PerformanceService:
    """
    Unified performance optimization service.
    
    Provides:
    - Fast path routing
    - Multi-level caching
    - Latency tracking
    - Circuit breakers
    """
    
    def __init__(
        self,
        redis_cache=None,
        graph_service=None,
    ):
        # Fast path router
        self.fast_path = FastPathRouter(
            cache=redis_cache,
            criteria=FastPathCriteria(),
        )
        
        # Cache manager
        self.cache = MultiLevelCacheManager(
            redis_cache=redis_cache,
            graph_service=graph_service,
        )
        
        # Circuit breakers for dependencies
        self.breakers = {
            "neo4j": CircuitBreaker("neo4j", failure_threshold=5),
            "redis": CircuitBreaker("redis", failure_threshold=3),
            "kafka": CircuitBreaker("kafka", failure_threshold=5),
            "claude": CircuitBreaker("claude", failure_threshold=3, recovery_timeout=60),
        }
        
        # Active trackers
        self._active_trackers: Dict[str, LatencyTracker] = {}
    
    # =========================================================================
    # REQUEST HANDLING
    # =========================================================================
    
    async def optimize_request(
        self,
        request_id: str,
        user_id: str,
        request_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Optimize a request for performance.
        
        Returns optimization decisions including:
        - Execution path
        - Cached data available
        - Circuit breaker states
        """
        
        # Route through fast path
        path_decision = await self.fast_path.route(user_id, request_context)
        
        # Create latency tracker
        tracker = LatencyTracker(request_id, path_decision.selected_path)
        self._active_trackers[request_id] = tracker
        
        # Warm cache if needed
        if not path_decision.use_fast_path:
            await self.cache.warm_user(user_id)
        
        return {
            "request_id": request_id,
            "path": path_decision.selected_path.value,
            "use_fast_path": path_decision.use_fast_path,
            "path_reason": path_decision.reason,
            "budget_ms": tracker.budget.total_budget_ms,
            "cached_profile": path_decision.cached_profile,
            "cached_mechanisms": path_decision.cached_mechanisms,
            "breaker_states": self._get_breaker_states(),
        }
    
    async def execute_with_optimization(
        self,
        request_id: str,
        user_id: str,
        request_context: Dict[str, Any],
        executor,
    ) -> Dict[str, Any]:
        """
        Execute a request with full performance optimization.
        """
        
        # Get optimization
        opt = await self.optimize_request(request_id, user_id, request_context)
        
        # Execute based on path
        if opt["use_fast_path"]:
            # Fast path execution
            decision = FastPathDecision(
                use_fast_path=True,
                selected_path=ExecutionPath.FAST,
                reason=opt["path_reason"],
                cached_profile=opt["cached_profile"],
                cached_mechanisms=opt["cached_mechanisms"],
            )
            result = await self.fast_path.execute_fast_path(decision, request_context)
        else:
            # Standard execution with tracking
            tracker = self._active_trackers.get(request_id)
            
            if tracker:
                async with tracker.track("full_execution"):
                    result = await executor(request_context, tracker)
            else:
                result = await executor(request_context, None)
        
        # Finalize tracking
        await self.finalize_request(request_id)
        
        return result
    
    async def finalize_request(
        self,
        request_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Finalize a request and get latency summary."""
        
        tracker = self._active_trackers.pop(request_id, None)
        if tracker:
            tracker.log_summary()
            return tracker.get_summary()
        return None
    
    # =========================================================================
    # LATENCY TRACKING
    # =========================================================================
    
    def get_tracker(self, request_id: str) -> Optional[LatencyTracker]:
        """Get latency tracker for a request."""
        return self._active_trackers.get(request_id)
    
    async def track_component(
        self,
        request_id: str,
        component: str,
    ):
        """Get context manager for tracking a component."""
        tracker = self._active_trackers.get(request_id)
        if tracker:
            return tracker.track(component)
        
        # Return dummy context manager if no tracker
        return _DummyContext()
    
    # =========================================================================
    # CIRCUIT BREAKERS
    # =========================================================================
    
    def get_breaker(self, name: str) -> Optional[CircuitBreaker]:
        """Get circuit breaker by name."""
        return self.breakers.get(name)
    
    def _get_breaker_states(self) -> Dict[str, str]:
        """Get all circuit breaker states."""
        return {
            name: breaker.state.value
            for name, breaker in self.breakers.items()
        }
    
    # =========================================================================
    # CACHING
    # =========================================================================
    
    async def get_cached(
        self,
        key: str,
        key_type: str = "generic",
    ) -> Optional[Any]:
        """Get from multi-level cache."""
        return await self.cache.get(key, key_type)
    
    async def set_cached(
        self,
        key: str,
        value: Any,
        key_type: str = "generic",
        ttl: Optional[int] = None,
    ) -> None:
        """Set in multi-level cache."""
        await self.cache.set(key, value, key_type, ttl)
    
    # =========================================================================
    # STATS
    # =========================================================================
    
    def get_stats(self) -> Dict[str, Any]:
        """Get performance statistics."""
        return {
            "cache": self.cache.get_stats(),
            "breakers": {
                name: breaker.get_stats()
                for name, breaker in self.breakers.items()
            },
            "active_requests": len(self._active_trackers),
        }


class _DummyContext:
    """Dummy context manager when no tracker."""
    
    async def __aenter__(self):
        return float("inf")  # Unlimited budget
    
    async def __aexit__(self, *args):
        return False
