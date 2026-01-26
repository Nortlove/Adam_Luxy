# =============================================================================
# ADAM Learning Loop Monitor
# Location: adam/monitoring/learning_loop_monitor.py
# =============================================================================

"""
LEARNING LOOP MONITOR

Monitors the health of ADAM's learning loop to ensure:
1. Decisions are being made
2. Outcomes are being received
3. Learning signals are being processed
4. Credit attribution is working

Alerts when the learning loop stalls or degrades.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
from enum import Enum

logger = logging.getLogger(__name__)

try:
    from prometheus_client import Gauge, Counter, Histogram, REGISTRY
    
    def _get_or_create_gauge(name: str, description: str) -> Gauge:
        """Get existing gauge or create new one."""
        try:
            return Gauge(name, description)
        except ValueError:
            # Metric already exists, get it from registry
            for metric in REGISTRY.collect():
                if metric.name == name:
                    return REGISTRY._names_to_collectors.get(name)
            return Gauge(name, description)
    
    def _get_or_create_histogram(name: str, description: str, buckets) -> Histogram:
        """Get existing histogram or create new one."""
        try:
            return Histogram(name, description, buckets=buckets)
        except ValueError:
            return REGISTRY._names_to_collectors.get(name)
    
    LEARNING_LOOP_HEALTH = _get_or_create_gauge(
        'adam_learning_loop_health',
        'Overall learning loop health score (0-1)'
    )
    DECISIONS_WITHOUT_OUTCOMES = _get_or_create_gauge(
        'adam_decisions_without_outcomes',
        'Number of decisions awaiting outcomes'
    )
    OUTCOME_LATENCY = _get_or_create_histogram(
        'adam_outcome_latency_seconds',
        'Time between decision and outcome',
        buckets=[1, 5, 10, 30, 60, 300, 600, 1800, 3600]
    )
    ATTRIBUTION_COVERAGE = _get_or_create_gauge(
        'adam_attribution_coverage',
        'Percentage of outcomes with successful attribution'
    )
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False


class LoopComponent(str, Enum):
    """Components of the learning loop."""
    DECISION = "decision"
    OUTCOME = "outcome"
    ATTRIBUTION = "attribution"
    SIGNAL = "signal"


@dataclass
class ComponentMetrics:
    """Metrics for a single loop component."""
    component: LoopComponent
    count_last_hour: int = 0
    count_last_minute: int = 0
    last_event: Optional[datetime] = None
    error_count: int = 0
    avg_latency_ms: float = 0.0


@dataclass
class LearningLoopHealth:
    """Overall health of the learning loop."""
    is_healthy: bool
    health_score: float  # 0-1
    components: Dict[str, ComponentMetrics] = field(default_factory=dict)
    pending_outcomes: int = 0
    attribution_rate: float = 0.0
    avg_outcome_latency_seconds: float = 0.0
    issues: List[str] = field(default_factory=list)
    last_check: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "is_healthy": self.is_healthy,
            "health_score": self.health_score,
            "components": {
                name: {
                    "count_last_hour": c.count_last_hour,
                    "count_last_minute": c.count_last_minute,
                    "last_event": c.last_event.isoformat() if c.last_event else None,
                    "error_count": c.error_count,
                    "avg_latency_ms": c.avg_latency_ms,
                }
                for name, c in self.components.items()
            },
            "pending_outcomes": self.pending_outcomes,
            "attribution_rate": self.attribution_rate,
            "avg_outcome_latency_seconds": self.avg_outcome_latency_seconds,
            "issues": self.issues,
            "last_check": self.last_check.isoformat(),
        }


class LearningLoopMonitor:
    """
    Monitors the health of ADAM's learning loop.
    
    The learning loop:
    1. Request → Decision (Meta-Learner routes, Atoms reason)
    2. Decision → Outcome (User action observed)
    3. Outcome → Attribution (Gradient Bridge assigns credit)
    4. Attribution → Signals (Components update)
    
    This monitor ensures each step is functioning correctly.
    """
    
    def __init__(
        self,
        max_outcome_wait_seconds: int = 3600,  # 1 hour
        min_attribution_rate: float = 0.80,
        check_interval_seconds: int = 60,
    ):
        self._max_outcome_wait = max_outcome_wait_seconds
        self._min_attribution_rate = min_attribution_rate
        self._check_interval = check_interval_seconds
        
        # Track pending decisions awaiting outcomes
        self._pending_decisions: Dict[str, datetime] = {}
        self._max_pending = 10000
        
        # Rolling counters
        self._decisions_count = 0
        self._outcomes_count = 0
        self._attributions_count = 0
        self._signals_count = 0
        
        # Error tracking
        self._errors: List[Dict[str, Any]] = []
        self._max_errors = 100
        
        # Latency tracking
        self._outcome_latencies: List[float] = []
        self._max_latencies = 1000
        
        # Last events
        self._last_decision: Optional[datetime] = None
        self._last_outcome: Optional[datetime] = None
        self._last_attribution: Optional[datetime] = None
        self._last_signal: Optional[datetime] = None
        
        # Monitoring
        self._monitoring_task: Optional[asyncio.Task] = None
        self._current_health: Optional[LearningLoopHealth] = None
    
    # =========================================================================
    # EVENT RECORDING
    # =========================================================================
    
    def record_decision(self, decision_id: str) -> None:
        """Record a decision being made."""
        now = datetime.now(timezone.utc)
        
        # Track pending
        if len(self._pending_decisions) < self._max_pending:
            self._pending_decisions[decision_id] = now
        
        self._decisions_count += 1
        self._last_decision = now
        
        logger.debug(f"Recorded decision: {decision_id}")
    
    def record_outcome(
        self,
        decision_id: str,
        outcome_value: float,
        attribution_successful: bool = True,
    ) -> None:
        """Record an outcome being received."""
        now = datetime.now(timezone.utc)
        
        # Calculate latency
        if decision_id in self._pending_decisions:
            decision_time = self._pending_decisions.pop(decision_id)
            latency = (now - decision_time).total_seconds()
            
            self._outcome_latencies.append(latency)
            if len(self._outcome_latencies) > self._max_latencies:
                self._outcome_latencies = self._outcome_latencies[-self._max_latencies:]
            
            if PROMETHEUS_AVAILABLE:
                OUTCOME_LATENCY.observe(latency)
        
        self._outcomes_count += 1
        self._last_outcome = now
        
        if attribution_successful:
            self._attributions_count += 1
            self._last_attribution = now
        
        logger.debug(f"Recorded outcome for decision: {decision_id}")
    
    def record_signal(self, signal_type: str, component: str) -> None:
        """Record a learning signal being emitted."""
        self._signals_count += 1
        self._last_signal = datetime.now(timezone.utc)
    
    def record_error(
        self,
        component: str,
        error_type: str,
        message: str,
    ) -> None:
        """Record an error in the learning loop."""
        self._errors.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "component": component,
            "error_type": error_type,
            "message": message,
        })
        
        if len(self._errors) > self._max_errors:
            self._errors = self._errors[-self._max_errors:]
        
        logger.warning(f"Learning loop error: {component}/{error_type}: {message}")
    
    # =========================================================================
    # HEALTH EVALUATION
    # =========================================================================
    
    def evaluate_health(self) -> LearningLoopHealth:
        """Evaluate overall learning loop health."""
        now = datetime.now(timezone.utc)
        issues = []
        
        # Check for stale pending decisions
        stale_count = 0
        for decision_id, decision_time in list(self._pending_decisions.items()):
            age = (now - decision_time).total_seconds()
            if age > self._max_outcome_wait:
                stale_count += 1
                # Remove very old ones
                if age > self._max_outcome_wait * 2:
                    del self._pending_decisions[decision_id]
        
        if stale_count > 10:
            issues.append(f"{stale_count} decisions awaiting outcomes > {self._max_outcome_wait}s")
        
        # Check attribution rate
        attribution_rate = 0.0
        if self._outcomes_count > 0:
            attribution_rate = self._attributions_count / self._outcomes_count
        
        if attribution_rate < self._min_attribution_rate and self._outcomes_count > 10:
            issues.append(f"Attribution rate {attribution_rate:.1%} < {self._min_attribution_rate:.1%}")
        
        # Check for stalled components
        stall_threshold = timedelta(minutes=10)
        
        if self._last_decision:
            if now - self._last_decision > stall_threshold:
                issues.append(f"No decisions for {(now - self._last_decision).total_seconds():.0f}s")
        
        if self._last_signal:
            if now - self._last_signal > stall_threshold:
                issues.append(f"No learning signals for {(now - self._last_signal).total_seconds():.0f}s")
        
        # Calculate average outcome latency
        avg_latency = 0.0
        if self._outcome_latencies:
            avg_latency = sum(self._outcome_latencies) / len(self._outcome_latencies)
        
        # Calculate health score
        health_score = 1.0
        
        # Penalize for pending decisions
        pending_penalty = min(0.3, len(self._pending_decisions) / 1000 * 0.3)
        health_score -= pending_penalty
        
        # Penalize for low attribution rate
        if self._outcomes_count > 10:
            attr_penalty = max(0, (self._min_attribution_rate - attribution_rate) * 0.5)
            health_score -= attr_penalty
        
        # Penalize for issues
        health_score -= len(issues) * 0.1
        health_score = max(0, min(1, health_score))
        
        # Build component metrics
        components = {
            "decision": ComponentMetrics(
                component=LoopComponent.DECISION,
                count_last_hour=self._decisions_count,
                last_event=self._last_decision,
            ),
            "outcome": ComponentMetrics(
                component=LoopComponent.OUTCOME,
                count_last_hour=self._outcomes_count,
                last_event=self._last_outcome,
            ),
            "attribution": ComponentMetrics(
                component=LoopComponent.ATTRIBUTION,
                count_last_hour=self._attributions_count,
                last_event=self._last_attribution,
            ),
            "signal": ComponentMetrics(
                component=LoopComponent.SIGNAL,
                count_last_hour=self._signals_count,
                last_event=self._last_signal,
            ),
        }
        
        health = LearningLoopHealth(
            is_healthy=len(issues) == 0 and health_score > 0.7,
            health_score=health_score,
            components=components,
            pending_outcomes=len(self._pending_decisions),
            attribution_rate=attribution_rate,
            avg_outcome_latency_seconds=avg_latency,
            issues=issues,
        )
        
        # Update metrics
        if PROMETHEUS_AVAILABLE:
            LEARNING_LOOP_HEALTH.set(health_score)
            DECISIONS_WITHOUT_OUTCOMES.set(len(self._pending_decisions))
            ATTRIBUTION_COVERAGE.set(attribution_rate)
        
        self._current_health = health
        return health
    
    def get_health(self) -> LearningLoopHealth:
        """Get current or compute health."""
        if self._current_health is None:
            return self.evaluate_health()
        return self._current_health
    
    # =========================================================================
    # MONITORING
    # =========================================================================
    
    async def start_monitoring(self) -> None:
        """Start background health monitoring."""
        async def monitor_loop():
            while True:
                try:
                    self.evaluate_health()
                except Exception as e:
                    logger.error(f"Learning loop health check error: {e}")
                await asyncio.sleep(self._check_interval)
        
        self._monitoring_task = asyncio.create_task(monitor_loop())
        logger.info("Started learning loop monitoring")
    
    async def stop_monitoring(self) -> None:
        """Stop background monitoring."""
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
            self._monitoring_task = None
            logger.info("Stopped learning loop monitoring")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get monitoring statistics."""
        return {
            "decisions_total": self._decisions_count,
            "outcomes_total": self._outcomes_count,
            "attributions_total": self._attributions_count,
            "signals_total": self._signals_count,
            "pending_decisions": len(self._pending_decisions),
            "recent_errors": len(self._errors),
            "outcome_latencies_tracked": len(self._outcome_latencies),
        }


# =============================================================================
# SINGLETON
# =============================================================================

_monitor: Optional[LearningLoopMonitor] = None


def get_learning_loop_monitor() -> LearningLoopMonitor:
    """Get the singleton learning loop monitor."""
    global _monitor
    if _monitor is None:
        _monitor = LearningLoopMonitor()
    return _monitor
