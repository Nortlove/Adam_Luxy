# =============================================================================
# ADAM Latency Management
# Location: adam/performance/latency.py
# =============================================================================

"""
LATENCY MANAGEMENT

Latency budgets, tracking, and optimization.
"""

import logging
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from enum import Enum

from pydantic import BaseModel, Field
from prometheus_client import Histogram, Counter

logger = logging.getLogger(__name__)


# =============================================================================
# METRICS
# =============================================================================

LATENCY_HISTOGRAM = Histogram(
    "adam_component_latency_ms",
    "Component latency in milliseconds",
    ["component", "path"],
    buckets=[5, 10, 25, 50, 100, 250, 500, 1000, 2500],
)

BUDGET_EXCEEDED_COUNTER = Counter(
    "adam_latency_budget_exceeded_total",
    "Number of times latency budget was exceeded",
    ["component"],
)


# =============================================================================
# EXECUTION PATHS
# =============================================================================

class ExecutionPath(str, Enum):
    """Execution paths with different latency profiles."""
    
    FAST = "fast"           # <50ms - Cached/precomputed only
    STANDARD = "standard"   # <100ms - Normal processing
    REASONING = "reasoning" # <500ms - Full atom DAG
    EXPLORATION = "exploration"  # <1000ms - Full exploration


# Default latency budgets per path (milliseconds)
PATH_BUDGETS = {
    ExecutionPath.FAST: 50,
    ExecutionPath.STANDARD: 100,
    ExecutionPath.REASONING: 500,
    ExecutionPath.EXPLORATION: 1000,
}

# Component budgets (percentage of total)
COMPONENT_BUDGETS = {
    "graph_lookup": 0.15,
    "cache_check": 0.05,
    "blackboard_init": 0.05,
    "meta_learner": 0.10,
    "atom_dag": 0.40,
    "verification": 0.10,
    "gradient_bridge": 0.10,
    "response_build": 0.05,
}


# =============================================================================
# LATENCY BUDGET
# =============================================================================

class LatencyBudget(BaseModel):
    """Budget for request processing."""
    
    path: ExecutionPath = Field(default=ExecutionPath.STANDARD)
    total_budget_ms: float = Field(default=100.0)
    
    # Component budgets
    component_budgets: Dict[str, float] = Field(default_factory=dict)
    
    # Spent so far
    spent_ms: float = Field(default=0.0)
    component_spent: Dict[str, float] = Field(default_factory=dict)
    
    # Started
    start_time: Optional[float] = None
    
    def initialize(self) -> "LatencyBudget":
        """Initialize budget with component allocations."""
        self.total_budget_ms = PATH_BUDGETS.get(self.path, 100)
        self.component_budgets = {
            comp: self.total_budget_ms * pct
            for comp, pct in COMPONENT_BUDGETS.items()
        }
        self.start_time = time.perf_counter()
        return self
    
    @property
    def remaining_ms(self) -> float:
        """Remaining budget in ms."""
        return max(0, self.total_budget_ms - self.spent_ms)
    
    @property
    def elapsed_ms(self) -> float:
        """Elapsed time since start."""
        if self.start_time is None:
            return 0.0
        return (time.perf_counter() - self.start_time) * 1000
    
    def get_component_budget(self, component: str) -> float:
        """Get budget for a component."""
        return self.component_budgets.get(component, 10.0)
    
    def get_component_remaining(self, component: str) -> float:
        """Get remaining budget for a component."""
        budget = self.get_component_budget(component)
        spent = self.component_spent.get(component, 0.0)
        return max(0, budget - spent)
    
    def record_component(self, component: str, duration_ms: float) -> None:
        """Record time spent in a component."""
        self.component_spent[component] = (
            self.component_spent.get(component, 0.0) + duration_ms
        )
        self.spent_ms += duration_ms
        
        # Check if exceeded
        budget = self.get_component_budget(component)
        if self.component_spent[component] > budget:
            BUDGET_EXCEEDED_COUNTER.labels(component=component).inc()
            logger.warning(
                f"Component {component} exceeded budget: "
                f"{self.component_spent[component]:.1f}ms > {budget:.1f}ms"
            )
    
    def is_exceeded(self) -> bool:
        """Check if total budget exceeded."""
        return self.elapsed_ms > self.total_budget_ms
    
    def should_skip_component(self, component: str) -> bool:
        """Check if we should skip a component to meet budget."""
        # If we've exceeded 80% of budget, skip non-critical components
        if self.elapsed_ms > self.total_budget_ms * 0.8:
            non_critical = ["verification", "gradient_bridge"]
            if component in non_critical:
                return True
        return False


# =============================================================================
# LATENCY TRACKER
# =============================================================================

@dataclass
class ComponentTiming:
    """Timing for a single component."""
    
    component: str
    start_ms: float
    end_ms: Optional[float] = None
    duration_ms: Optional[float] = None
    
    def finish(self) -> None:
        self.end_ms = time.perf_counter() * 1000
        self.duration_ms = self.end_ms - self.start_ms


class LatencyTracker:
    """
    Track latency across components.
    """
    
    def __init__(self, request_id: str, path: ExecutionPath = ExecutionPath.STANDARD):
        self.request_id = request_id
        self.path = path
        self.budget = LatencyBudget(path=path).initialize()
        
        self.timings: List[ComponentTiming] = []
        self.current_component: Optional[ComponentTiming] = None
    
    @asynccontextmanager
    async def track(self, component: str):
        """Context manager for tracking component latency."""
        timing = ComponentTiming(
            component=component,
            start_ms=time.perf_counter() * 1000,
        )
        self.current_component = timing
        
        try:
            yield self.budget.get_component_remaining(component)
        finally:
            timing.finish()
            self.timings.append(timing)
            self.budget.record_component(component, timing.duration_ms or 0)
            
            # Record to Prometheus
            LATENCY_HISTOGRAM.labels(
                component=component,
                path=self.path.value,
            ).observe(timing.duration_ms or 0)
            
            self.current_component = None
    
    def get_summary(self) -> Dict[str, Any]:
        """Get latency summary."""
        return {
            "request_id": self.request_id,
            "path": self.path.value,
            "total_ms": self.budget.elapsed_ms,
            "budget_ms": self.budget.total_budget_ms,
            "exceeded": self.budget.is_exceeded(),
            "components": {
                t.component: t.duration_ms
                for t in self.timings
            },
        }
    
    def log_summary(self) -> None:
        """Log latency summary."""
        summary = self.get_summary()
        
        if summary["exceeded"]:
            logger.warning(
                f"Request {self.request_id} exceeded budget: "
                f"{summary['total_ms']:.1f}ms > {summary['budget_ms']:.1f}ms"
            )
        else:
            logger.debug(
                f"Request {self.request_id} completed in "
                f"{summary['total_ms']:.1f}ms (budget: {summary['budget_ms']:.1f}ms)"
            )
