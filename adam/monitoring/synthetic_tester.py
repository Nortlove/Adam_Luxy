# =============================================================================
# ADAM Synthetic Test Runner
# Location: adam/monitoring/synthetic_tester.py
# =============================================================================

"""
SYNTHETIC TEST RUNNER

Continuously validates ADAM system health through synthetic requests.

Capabilities:
1. Periodic synthetic decision requests
2. End-to-end latency measurement
3. Learning signal verification
4. Component health validation

Use cases:
- Production health monitoring
- Performance regression detection
- Integration validation
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Any, Callable, Dict, List, Optional
from uuid import uuid4
from enum import Enum

logger = logging.getLogger(__name__)

try:
    from prometheus_client import Counter, Histogram, Gauge
    
    SYNTHETIC_REQUESTS = Counter(
        'adam_synthetic_requests_total',
        'Total synthetic test requests',
        ['test_type', 'result']
    )
    SYNTHETIC_LATENCY = Histogram(
        'adam_synthetic_latency_seconds',
        'Synthetic test latency',
        ['test_type'],
        buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0]
    )
    SYNTHETIC_HEALTH = Gauge(
        'adam_synthetic_health',
        'Synthetic test health score (0-1)'
    )
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False


class TestType(str, Enum):
    """Types of synthetic tests."""
    DECISION_FLOW = "decision_flow"
    LEARNING_LOOP = "learning_loop"
    HEALTH_CHECK = "health_check"
    MECHANISM_ACTIVATION = "mechanism_activation"


class TestResult(str, Enum):
    """Test result status."""
    PASSED = "passed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    SKIPPED = "skipped"


@dataclass
class SyntheticTestResult:
    """Result of a synthetic test."""
    test_type: TestType
    result: TestResult
    latency_ms: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    error_message: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "test_type": self.test_type.value,
            "result": self.result.value,
            "latency_ms": self.latency_ms,
            "timestamp": self.timestamp.isoformat(),
            "error_message": self.error_message,
            "details": self.details,
        }


@dataclass
class SyntheticTestSuite:
    """Collection of synthetic test results."""
    results: List[SyntheticTestResult] = field(default_factory=list)
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    
    @property
    def passed_count(self) -> int:
        return len([r for r in self.results if r.result == TestResult.PASSED])
    
    @property
    def failed_count(self) -> int:
        return len([r for r in self.results if r.result == TestResult.FAILED])
    
    @property
    def health_score(self) -> float:
        if not self.results:
            return 1.0
        return self.passed_count / len(self.results)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "results": [r.to_dict() for r in self.results],
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "passed_count": self.passed_count,
            "failed_count": self.failed_count,
            "health_score": self.health_score,
        }


class SyntheticTester:
    """
    Runs synthetic tests to validate system health.
    
    The tester:
    1. Periodically sends synthetic requests
    2. Validates responses
    3. Measures latency
    4. Reports health metrics
    """
    
    def __init__(
        self,
        test_interval_seconds: int = 60,
        timeout_seconds: float = 5.0,
    ):
        self._test_interval = test_interval_seconds
        self._timeout = timeout_seconds
        
        # Test functions
        self._tests: Dict[TestType, Callable] = {}
        
        # Results history
        self._results_history: List[SyntheticTestResult] = []
        self._max_history = 1000
        
        # Current state
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._last_suite: Optional[SyntheticTestSuite] = None
        
        # Register default tests
        self._register_default_tests()
    
    def _register_default_tests(self) -> None:
        """Register default synthetic tests."""
        self.register_test(TestType.HEALTH_CHECK, self._test_health_check)
        self.register_test(TestType.DECISION_FLOW, self._test_decision_flow)
        self.register_test(TestType.LEARNING_LOOP, self._test_learning_loop)
    
    def register_test(
        self,
        test_type: TestType,
        test_fn: Callable[[], bool],
    ) -> None:
        """Register a synthetic test."""
        self._tests[test_type] = test_fn
        logger.debug(f"Registered synthetic test: {test_type.value}")
    
    # =========================================================================
    # DEFAULT TESTS
    # =========================================================================
    
    async def _test_health_check(self) -> SyntheticTestResult:
        """Test basic health check endpoint."""
        start = time.time()
        
        try:
            from adam.monitoring.system_health import get_system_health_aggregator
            
            aggregator = get_system_health_aggregator()
            liveness = await aggregator.check_liveness()
            
            latency_ms = (time.time() - start) * 1000
            
            if liveness.get("status") == "ok":
                return SyntheticTestResult(
                    test_type=TestType.HEALTH_CHECK,
                    result=TestResult.PASSED,
                    latency_ms=latency_ms,
                )
            else:
                return SyntheticTestResult(
                    test_type=TestType.HEALTH_CHECK,
                    result=TestResult.FAILED,
                    latency_ms=latency_ms,
                    error_message="Health check returned non-ok status",
                )
                
        except Exception as e:
            latency_ms = (time.time() - start) * 1000
            return SyntheticTestResult(
                test_type=TestType.HEALTH_CHECK,
                result=TestResult.FAILED,
                latency_ms=latency_ms,
                error_message=str(e),
            )
    
    async def _test_decision_flow(self) -> SyntheticTestResult:
        """Test decision flow (without actual decision making)."""
        start = time.time()
        
        try:
            # Test that key services can be imported and instantiated
            from adam.meta_learner.service import MetaLearnerService
            from adam.cold_start.service import ColdStartService
            
            # Verify services can be retrieved
            cold_start = ColdStartService()
            stats = cold_start.get_statistics()
            
            latency_ms = (time.time() - start) * 1000
            
            return SyntheticTestResult(
                test_type=TestType.DECISION_FLOW,
                result=TestResult.PASSED,
                latency_ms=latency_ms,
                details={"cold_start_stats": stats},
            )
            
        except Exception as e:
            latency_ms = (time.time() - start) * 1000
            return SyntheticTestResult(
                test_type=TestType.DECISION_FLOW,
                result=TestResult.FAILED,
                latency_ms=latency_ms,
                error_message=str(e),
            )
    
    async def _test_learning_loop(self) -> SyntheticTestResult:
        """Test learning loop health."""
        start = time.time()
        
        try:
            from adam.monitoring.learning_loop_monitor import get_learning_loop_monitor
            
            monitor = get_learning_loop_monitor()
            health = monitor.get_health()
            
            latency_ms = (time.time() - start) * 1000
            
            if health.is_healthy:
                return SyntheticTestResult(
                    test_type=TestType.LEARNING_LOOP,
                    result=TestResult.PASSED,
                    latency_ms=latency_ms,
                    details={
                        "health_score": health.health_score,
                        "pending_outcomes": health.pending_outcomes,
                    },
                )
            else:
                return SyntheticTestResult(
                    test_type=TestType.LEARNING_LOOP,
                    result=TestResult.FAILED,
                    latency_ms=latency_ms,
                    error_message="; ".join(health.issues),
                    details={
                        "health_score": health.health_score,
                        "issues": health.issues,
                    },
                )
                
        except Exception as e:
            latency_ms = (time.time() - start) * 1000
            return SyntheticTestResult(
                test_type=TestType.LEARNING_LOOP,
                result=TestResult.FAILED,
                latency_ms=latency_ms,
                error_message=str(e),
            )
    
    # =========================================================================
    # RUNNING TESTS
    # =========================================================================
    
    async def run_test(self, test_type: TestType) -> SyntheticTestResult:
        """Run a single synthetic test."""
        if test_type not in self._tests:
            return SyntheticTestResult(
                test_type=test_type,
                result=TestResult.SKIPPED,
                latency_ms=0,
                error_message=f"Test {test_type.value} not registered",
            )
        
        test_fn = self._tests[test_type]
        
        try:
            result = await asyncio.wait_for(
                test_fn(),
                timeout=self._timeout,
            )
        except asyncio.TimeoutError:
            result = SyntheticTestResult(
                test_type=test_type,
                result=TestResult.TIMEOUT,
                latency_ms=self._timeout * 1000,
                error_message=f"Test timed out after {self._timeout}s",
            )
        except Exception as e:
            result = SyntheticTestResult(
                test_type=test_type,
                result=TestResult.FAILED,
                latency_ms=0,
                error_message=str(e),
            )
        
        # Record metrics
        if PROMETHEUS_AVAILABLE:
            SYNTHETIC_REQUESTS.labels(
                test_type=test_type.value,
                result=result.result.value,
            ).inc()
            SYNTHETIC_LATENCY.labels(test_type=test_type.value).observe(
                result.latency_ms / 1000
            )
        
        # Store in history
        self._results_history.append(result)
        if len(self._results_history) > self._max_history:
            self._results_history = self._results_history[-self._max_history:]
        
        return result
    
    async def run_all_tests(self) -> SyntheticTestSuite:
        """Run all registered synthetic tests."""
        suite = SyntheticTestSuite()
        
        for test_type in self._tests:
            result = await self.run_test(test_type)
            suite.results.append(result)
        
        suite.completed_at = datetime.now(timezone.utc)
        self._last_suite = suite
        
        # Update health metric
        if PROMETHEUS_AVAILABLE:
            SYNTHETIC_HEALTH.set(suite.health_score)
        
        logger.info(
            f"Synthetic test suite: {suite.passed_count}/{len(suite.results)} passed "
            f"(health={suite.health_score:.2%})"
        )
        
        return suite
    
    # =========================================================================
    # CONTINUOUS TESTING
    # =========================================================================
    
    async def start(self) -> None:
        """Start continuous synthetic testing."""
        if self._running:
            return
        
        self._running = True
        
        async def test_loop():
            while self._running:
                try:
                    await self.run_all_tests()
                except Exception as e:
                    logger.error(f"Synthetic test error: {e}")
                await asyncio.sleep(self._test_interval)
        
        self._task = asyncio.create_task(test_loop())
        logger.info(f"Started synthetic testing (interval={self._test_interval}s)")
    
    async def stop(self) -> None:
        """Stop continuous testing."""
        self._running = False
        
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        
        logger.info("Stopped synthetic testing")
    
    # =========================================================================
    # RESULTS ACCESS
    # =========================================================================
    
    def get_last_suite(self) -> Optional[SyntheticTestSuite]:
        """Get the most recent test suite."""
        return self._last_suite
    
    def get_recent_results(
        self,
        limit: int = 50,
        test_type: Optional[TestType] = None,
    ) -> List[SyntheticTestResult]:
        """Get recent test results."""
        results = self._results_history
        
        if test_type:
            results = [r for r in results if r.test_type == test_type]
        
        return results[-limit:]
    
    def get_health_score(self) -> float:
        """Get current synthetic test health score."""
        if self._last_suite:
            return self._last_suite.health_score
        return 1.0
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get synthetic testing statistics."""
        recent = self._results_history[-100:] if self._results_history else []
        
        passed = len([r for r in recent if r.result == TestResult.PASSED])
        failed = len([r for r in recent if r.result == TestResult.FAILED])
        timeout = len([r for r in recent if r.result == TestResult.TIMEOUT])
        
        return {
            "running": self._running,
            "test_interval_seconds": self._test_interval,
            "registered_tests": list(self._tests.keys()),
            "total_results": len(self._results_history),
            "recent_passed": passed,
            "recent_failed": failed,
            "recent_timeout": timeout,
            "recent_health": passed / len(recent) if recent else 1.0,
            "last_run": self._last_suite.completed_at.isoformat() if self._last_suite else None,
        }


# =============================================================================
# SINGLETON
# =============================================================================

_tester: Optional[SyntheticTester] = None


def get_synthetic_tester() -> SyntheticTester:
    """Get the singleton synthetic tester."""
    global _tester
    if _tester is None:
        _tester = SyntheticTester()
    return _tester
