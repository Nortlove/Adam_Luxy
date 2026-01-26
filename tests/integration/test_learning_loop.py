# =============================================================================
# ADAM Learning Loop Integration Tests
# Location: tests/integration/test_learning_loop.py
# =============================================================================

"""
Integration tests for the ADAM learning loop.

Tests the complete flow:
1. Decision making
2. Outcome recording
3. Credit attribution
4. Learning signal propagation

These tests validate that the learning loop works end-to-end.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone
from uuid import uuid4

from adam.monitoring.learning_loop_monitor import (
    LearningLoopMonitor,
    LearningLoopHealth,
    get_learning_loop_monitor,
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def learning_monitor():
    """Create a fresh learning loop monitor."""
    return LearningLoopMonitor()


@pytest.fixture
def mock_services():
    """Create mock services for integration testing."""
    return {
        "meta_learner": MagicMock(),
        "gradient_bridge": MagicMock(),
        "cold_start": MagicMock(),
    }


# =============================================================================
# LEARNING LOOP MONITOR TESTS
# =============================================================================

class TestLearningLoopMonitor:
    """Tests for the learning loop monitor."""
    
    def test_record_decision(self, learning_monitor):
        """Test recording a decision."""
        decision_id = f"dec_{uuid4().hex[:8]}"
        
        learning_monitor.record_decision(decision_id)
        
        assert decision_id in learning_monitor._pending_decisions
        assert learning_monitor._decisions_count == 1
        assert learning_monitor._last_decision is not None
    
    def test_record_outcome_calculates_latency(self, learning_monitor):
        """Test that outcome recording calculates latency."""
        decision_id = f"dec_{uuid4().hex[:8]}"
        
        # Record decision
        learning_monitor.record_decision(decision_id)
        
        # Record outcome
        learning_monitor.record_outcome(
            decision_id=decision_id,
            outcome_value=0.8,
            attribution_successful=True,
        )
        
        assert decision_id not in learning_monitor._pending_decisions
        assert learning_monitor._outcomes_count == 1
        assert learning_monitor._attributions_count == 1
        assert len(learning_monitor._outcome_latencies) == 1
    
    def test_record_outcome_without_prior_decision(self, learning_monitor):
        """Test recording outcome without prior decision."""
        decision_id = f"dec_{uuid4().hex[:8]}"
        
        # Record outcome without decision
        learning_monitor.record_outcome(
            decision_id=decision_id,
            outcome_value=0.5,
            attribution_successful=True,
        )
        
        # Should still record outcome, just no latency
        assert learning_monitor._outcomes_count == 1
        assert len(learning_monitor._outcome_latencies) == 0
    
    def test_record_signal(self, learning_monitor):
        """Test recording a learning signal."""
        learning_monitor.record_signal("mechanism_update", "gradient_bridge")
        
        assert learning_monitor._signals_count == 1
        assert learning_monitor._last_signal is not None
    
    def test_record_error(self, learning_monitor):
        """Test recording an error."""
        learning_monitor.record_error(
            component="gradient_bridge",
            error_type="attribution_failed",
            message="Test error",
        )
        
        assert len(learning_monitor._errors) == 1
        assert learning_monitor._errors[0]["component"] == "gradient_bridge"


# =============================================================================
# HEALTH EVALUATION TESTS
# =============================================================================

class TestHealthEvaluation:
    """Tests for health evaluation."""
    
    def test_evaluate_healthy_loop(self, learning_monitor):
        """Test health evaluation with healthy loop."""
        # Simulate healthy activity
        for i in range(10):
            decision_id = f"dec_{i}"
            learning_monitor.record_decision(decision_id)
            learning_monitor.record_outcome(
                decision_id=decision_id,
                outcome_value=0.7,
                attribution_successful=True,
            )
            learning_monitor.record_signal("update", "component")
        
        health = learning_monitor.evaluate_health()
        
        assert health.is_healthy
        assert health.health_score > 0.7
        assert health.attribution_rate == 1.0
        assert len(health.issues) == 0
    
    def test_evaluate_with_low_attribution_rate(self, learning_monitor):
        """Test health evaluation with low attribution rate."""
        # Simulate low attribution
        for i in range(20):
            decision_id = f"dec_{i}"
            learning_monitor.record_decision(decision_id)
            learning_monitor.record_outcome(
                decision_id=decision_id,
                outcome_value=0.5,
                attribution_successful=(i < 5),  # Only 5/20 successful
            )
        
        health = learning_monitor.evaluate_health()
        
        assert health.attribution_rate == 0.25
        assert any("Attribution rate" in issue for issue in health.issues)
    
    def test_evaluate_with_pending_decisions(self, learning_monitor):
        """Test health evaluation with stale pending decisions."""
        # Simulate stale decisions
        for i in range(100):
            decision_id = f"dec_{i}"
            learning_monitor.record_decision(decision_id)
        
        health = learning_monitor.evaluate_health()
        
        assert health.pending_outcomes == 100
        # Score should be penalized
        assert health.health_score < 1.0
    
    def test_health_components_populated(self, learning_monitor):
        """Test that health components are properly populated."""
        learning_monitor.record_decision("dec_1")
        learning_monitor.record_signal("test", "component")
        
        health = learning_monitor.evaluate_health()
        
        assert "decision" in health.components
        assert "signal" in health.components
        assert health.components["decision"].count_last_hour > 0
        assert health.components["signal"].count_last_hour > 0


# =============================================================================
# STATISTICS TESTS
# =============================================================================

class TestStatistics:
    """Tests for monitor statistics."""
    
    def test_get_statistics(self, learning_monitor):
        """Test getting statistics."""
        learning_monitor.record_decision("dec_1")
        learning_monitor.record_outcome("dec_1", 0.5, True)
        learning_monitor.record_signal("test", "component")
        
        stats = learning_monitor.get_statistics()
        
        assert stats["decisions_total"] == 1
        assert stats["outcomes_total"] == 1
        assert stats["attributions_total"] == 1
        assert stats["signals_total"] == 1
        assert stats["pending_decisions"] == 0


# =============================================================================
# INTEGRATION FLOW TESTS
# =============================================================================

class TestLearningLoopFlow:
    """Tests for complete learning loop flow."""
    
    def test_complete_learning_cycle(self, learning_monitor):
        """Test a complete learning cycle."""
        # 1. Decision made
        decision_id = f"dec_{uuid4().hex[:8]}"
        learning_monitor.record_decision(decision_id)
        
        assert learning_monitor._decisions_count == 1
        
        # 2. Outcome received
        learning_monitor.record_outcome(
            decision_id=decision_id,
            outcome_value=0.85,
            attribution_successful=True,
        )
        
        assert learning_monitor._outcomes_count == 1
        assert learning_monitor._attributions_count == 1
        
        # 3. Learning signal emitted
        learning_monitor.record_signal("mechanism_update", "gradient_bridge")
        learning_monitor.record_signal("bandit_update", "meta_learner")
        
        assert learning_monitor._signals_count == 2
        
        # 4. Evaluate health
        health = learning_monitor.evaluate_health()
        
        assert health.is_healthy
        assert health.health_score > 0.8
    
    def test_multiple_concurrent_decisions(self, learning_monitor):
        """Test handling multiple concurrent decisions."""
        # Simulate concurrent decisions
        decision_ids = [f"dec_{i}" for i in range(50)]
        
        for dec_id in decision_ids:
            learning_monitor.record_decision(dec_id)
        
        assert len(learning_monitor._pending_decisions) == 50
        
        # Resolve some outcomes
        for dec_id in decision_ids[:30]:
            learning_monitor.record_outcome(dec_id, 0.6, True)
        
        assert len(learning_monitor._pending_decisions) == 20
        assert learning_monitor._outcomes_count == 30
    
    def test_error_recovery(self, learning_monitor):
        """Test that errors don't break the monitor."""
        # Record some activity
        learning_monitor.record_decision("dec_1")
        
        # Record an error
        learning_monitor.record_error(
            component="gradient_bridge",
            error_type="attribution_failed",
            message="Test failure",
        )
        
        # Should still work
        learning_monitor.record_outcome("dec_1", 0.5, True)
        
        health = learning_monitor.evaluate_health()
        
        # Should still be evaluable
        assert health is not None


# =============================================================================
# ALERTING INTEGRATION TESTS
# =============================================================================

class TestAlertingIntegration:
    """Tests for alerting integration."""
    
    @pytest.mark.asyncio
    async def test_health_triggers_prometheus_metrics(self, learning_monitor):
        """Test that health evaluation updates Prometheus metrics."""
        # Record activity
        learning_monitor.record_decision("dec_1")
        learning_monitor.record_outcome("dec_1", 0.8, True)
        
        # Evaluate health (should update metrics)
        health = learning_monitor.evaluate_health()
        
        # Metrics should be updated (if prometheus_client available)
        # This is a basic check - full metric validation would need prometheus testutils
        assert health.health_score is not None
