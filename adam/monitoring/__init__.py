# =============================================================================
# ADAM Monitoring System
# Location: adam/monitoring/__init__.py
# =============================================================================

"""
ADAM MONITORING SYSTEM

Provides continuous monitoring and validation for ADAM components.

Components:
- LearningLoopMonitor: Validates learning loop health
- SystemHealthAggregator: Aggregates health across components
- SyntheticTester: Runs synthetic tests periodically
"""

from adam.monitoring.learning_loop_monitor import (
    LearningLoopMonitor,
    LearningLoopHealth,
    get_learning_loop_monitor,
)
from adam.monitoring.system_health import (
    SystemHealthAggregator,
    SystemHealthReport,
    get_system_health_aggregator,
)
from adam.monitoring.synthetic_tester import (
    SyntheticTester,
    SyntheticTestResult,
    SyntheticTestSuite,
    TestType,
    TestResult,
    get_synthetic_tester,
)

__all__ = [
    # Learning Loop
    "LearningLoopMonitor",
    "LearningLoopHealth",
    "get_learning_loop_monitor",
    # System Health
    "SystemHealthAggregator",
    "SystemHealthReport",
    "get_system_health_aggregator",
    # Synthetic Testing
    "SyntheticTester",
    "SyntheticTestResult",
    "SyntheticTestSuite",
    "TestType",
    "TestResult",
    "get_synthetic_tester",
]
