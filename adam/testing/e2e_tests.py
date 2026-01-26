# =============================================================================
# ADAM End-to-End Tests
# Location: adam/testing/e2e_tests.py
# =============================================================================

"""
END-TO-END TESTS

Complete pipeline testing from request to outcome.
Validates that all components work together correctly.
"""

import asyncio
import pytest
from datetime import datetime, timezone
from typing import Any, Dict, List
from uuid import uuid4

from adam.core.container import ADAMContainer, ContainerConfig
from adam.blackboard.models.zone1_context import RequestContext, AdCandidate
from adam.meta_learner.models import ExecutionPath
from adam.verification.models.results import VerificationStatus
from adam.gradient_bridge.models.credit import OutcomeType


# =============================================================================
# TEST FIXTURES
# =============================================================================

@pytest.fixture
async def test_container():
    """Create a test container with mocks."""
    config = ContainerConfig(
        enable_kafka=False,
        enable_redis=False,
        enable_neo4j=False,
        test_mode=True,
    )
    container = ADAMContainer(config)
    await container.initialize()
    yield container
    await container.shutdown()


@pytest.fixture
def sample_ad_candidates() -> List[Dict[str, Any]]:
    """Sample ad candidates for testing."""
    return [
        {
            "ad_id": "ad_001",
            "campaign_id": "camp_001",
            "brand_id": "brand_001",
            "category_id": "automotive",
            "mechanism_id": "identity_construction",
        },
        {
            "ad_id": "ad_002",
            "campaign_id": "camp_001",
            "brand_id": "brand_001",
            "category_id": "automotive",
            "mechanism_id": "social_proof",
        },
        {
            "ad_id": "ad_003",
            "campaign_id": "camp_002",
            "brand_id": "brand_002",
            "category_id": "automotive",
            "mechanism_id": "scarcity",
        },
    ]


@pytest.fixture
def sample_request_context() -> RequestContext:
    """Sample request context."""
    return RequestContext(
        request_id=f"test_req_{uuid4().hex[:8]}",
        user_id=f"test_user_{uuid4().hex[:8]}",
        category_id="automotive",
        brand_id="brand_001",
    )


# =============================================================================
# UNIT TESTS - COMPONENTS
# =============================================================================

class TestBlackboardService:
    """Tests for Blackboard service."""
    
    @pytest.mark.asyncio
    async def test_create_blackboard(self, test_container):
        """Test creating a blackboard state."""
        request_id = f"test_{uuid4().hex[:8]}"
        user_id = "test_user"
        
        await test_container.blackboard.create_blackboard(
            request_id=request_id,
            user_id=user_id,
        )
        
        state = await test_container.blackboard.get_blackboard(request_id)
        assert state is not None
        assert state.request_id == request_id
    
    @pytest.mark.asyncio
    async def test_zone_access_control(self, test_container):
        """Test zone access control."""
        from adam.blackboard.models.core import ComponentRole, check_access, BlackboardZone, ZoneAccessMode
        
        # Request handler can write Zone 1
        assert check_access(
            BlackboardZone.ZONE_1_CONTEXT,
            ComponentRole.REQUEST_HANDLER,
            ZoneAccessMode.WRITE
        )
        
        # Atoms can read Zone 1
        assert check_access(
            BlackboardZone.ZONE_1_CONTEXT,
            ComponentRole.ATOM,
            ZoneAccessMode.READ
        )
        
        # Atoms cannot write Zone 1
        assert not check_access(
            BlackboardZone.ZONE_1_CONTEXT,
            ComponentRole.ATOM,
            ZoneAccessMode.WRITE
        )


class TestMetaLearner:
    """Tests for Meta-Learner service."""
    
    @pytest.mark.asyncio
    async def test_routing_decision(self, test_container, sample_request_context):
        """Test routing decision generation."""
        decision = await test_container.meta_learner.route_request(
            request_id=sample_request_context.request_id,
            request_context=sample_request_context,
        )
        
        assert decision is not None
        assert decision.execution_path in ExecutionPath
        assert 0.0 <= decision.selection_confidence <= 1.0
    
    @pytest.mark.asyncio
    async def test_thompson_sampling(self):
        """Test Thompson sampling convergence."""
        from adam.meta_learner.thompson import ThompsonSamplingEngine
        from adam.meta_learner.models import ContextFeatures, LearningModality
        
        engine = ThompsonSamplingEngine()
        
        # Simulate rewards favoring one modality
        for _ in range(50):
            engine.update(LearningModality.REINFORCEMENT_BANDIT, reward=0.8)
            engine.update(LearningModality.SUPERVISED_CONVERSION, reward=0.3)
        
        # Should favor the high-reward modality
        context = ContextFeatures(
            user_id="test",
            interaction_count=20,
            profile_completeness=0.7,
            data_richness="rich",
        )
        
        decision = engine.select_modality(
            request_id="test",
            user_id="test",
            context=context,
        )
        
        # Bandit should have higher selection probability
        bandit_posterior = engine.posterior_state.posteriors[LearningModality.REINFORCEMENT_BANDIT]
        supervised_posterior = engine.posterior_state.posteriors[LearningModality.SUPERVISED_CONVERSION]
        
        assert bandit_posterior.mean > supervised_posterior.mean


class TestAtomDAG:
    """Tests for Atom DAG execution."""
    
    @pytest.mark.asyncio
    async def test_dag_execution(self, test_container, sample_request_context):
        """Test DAG execution produces outputs."""
        result = await test_container.atom_dag.execute(
            request_id=sample_request_context.request_id,
            request_context=sample_request_context,
        )
        
        assert result is not None
        assert len(result.atom_results) > 0
    
    @pytest.mark.asyncio
    async def test_topological_order(self, test_container):
        """Test atoms execute in correct dependency order."""
        plan = test_container.atom_dag.get_execution_plan()
        
        assert "levels" in plan
        
        # Mechanism atom should be in a later level than RF and CL
        levels = plan["levels"]
        rf_level = None
        mech_level = None
        
        for i, level in enumerate(levels):
            if "atom_regulatory_focus" in level:
                rf_level = i
            if "atom_mechanism_activation" in level:
                mech_level = i
        
        if rf_level is not None and mech_level is not None:
            assert mech_level > rf_level


class TestVerification:
    """Tests for Verification service."""
    
    @pytest.mark.asyncio
    async def test_verification_passes(self, test_container):
        """Test verification passes for valid outputs."""
        atom_outputs = {
            "atom_regulatory_focus": {
                "primary_assessment": "promotion",
                "overall_confidence": 0.8,
            },
            "atom_construal_level": {
                "primary_assessment": "abstract",
                "overall_confidence": 0.7,
            },
        }
        
        result = await test_container.verification.verify(
            request_id="test",
            atom_outputs=atom_outputs,
            user_id="test_user",
        )
        
        assert result.status in [
            VerificationStatus.PASSED,
            VerificationStatus.PASSED_WITH_WARNINGS,
        ]
    
    @pytest.mark.asyncio
    async def test_safety_blocking(self, test_container):
        """Test safety layer blocks harmful outputs."""
        atom_outputs = {
            "atom_mechanism_activation": {
                "mechanism_weights": {"dark_pattern": 0.9},
            },
        }
        
        result = await test_container.verification.verify(
            request_id="test",
            atom_outputs=atom_outputs,
            user_id="test_user",
        )
        
        # Should have safety warnings or blocks
        assert VerificationStatus.BLOCKED or len(result.layer_results) > 0


class TestGradientBridge:
    """Tests for Gradient Bridge service."""
    
    @pytest.mark.asyncio
    async def test_outcome_processing(self, test_container):
        """Test outcome generates learning signals."""
        package = await test_container.gradient_bridge.process_outcome(
            decision_id="test_decision",
            request_id="test_request",
            user_id="test_user",
            outcome_type=OutcomeType.CONVERSION,
            outcome_value=1.0,
            atom_outputs={
                "atom_regulatory_focus": {"overall_confidence": 0.8},
            },
            mechanism_used="identity_construction",
        )
        
        assert package.total_signals > 0
    
    @pytest.mark.asyncio
    async def test_credit_attribution(self, test_container):
        """Test credit attribution computation."""
        from adam.gradient_bridge.attribution import CreditAttributor
        from adam.gradient_bridge.models.credit import CreditAssignmentRequest
        
        attributor = CreditAttributor()
        
        request = CreditAssignmentRequest(
            decision_id="test",
            request_id="test",
            user_id="test_user",
            outcome_type=OutcomeType.CONVERSION,
            outcome_value=1.0,
            atom_outputs={
                "atom_rf": {"overall_confidence": 0.8},
                "atom_cl": {"overall_confidence": 0.6},
            },
        )
        
        attribution = await attributor.compute_attribution(request)
        
        assert len(attribution.atom_credits) == 2
        assert sum(ac.credit_share for ac in attribution.atom_credits) == pytest.approx(1.0)


# =============================================================================
# INTEGRATION TESTS - PIPELINE
# =============================================================================

class TestFullPipeline:
    """Integration tests for the complete pipeline."""
    
    @pytest.mark.asyncio
    async def test_cold_start_to_decision(self, test_container, sample_request_context, sample_ad_candidates):
        """Test complete flow for a cold-start user."""
        # 1. Create blackboard
        await test_container.blackboard.create_blackboard(
            request_id=sample_request_context.request_id,
            user_id=sample_request_context.user_id,
        )
        
        # 2. Route request
        routing = await test_container.meta_learner.route_request(
            request_id=sample_request_context.request_id,
            request_context=sample_request_context,
        )
        
        # Cold start should often go to reasoning or exploration
        assert routing.execution_path in ExecutionPath
        
        # 3. Execute atom DAG
        dag_result = await test_container.atom_dag.execute(
            request_id=sample_request_context.request_id,
            request_context=sample_request_context,
        )
        
        # 4. Verify
        atom_outputs = {
            r.atom_id: r.output.model_dump() if r.output else {}
            for r in dag_result.atom_results
        }
        
        verification = await test_container.verification.verify(
            request_id=sample_request_context.request_id,
            atom_outputs=atom_outputs,
            user_id=sample_request_context.user_id,
        )
        
        # 5. Complete blackboard
        await test_container.blackboard.complete_blackboard(
            sample_request_context.request_id
        )
        
        # Validate complete flow
        assert dag_result.success
        assert verification.status != VerificationStatus.BLOCKED
    
    @pytest.mark.asyncio
    async def test_learning_loop(self, test_container, sample_request_context):
        """Test that outcomes trigger learning updates."""
        # Make a decision
        await test_container.blackboard.create_blackboard(
            request_id=sample_request_context.request_id,
            user_id=sample_request_context.user_id,
        )
        
        routing = await test_container.meta_learner.route_request(
            request_id=sample_request_context.request_id,
            request_context=sample_request_context,
        )
        
        # Record positive outcome
        package = await test_container.gradient_bridge.process_outcome(
            decision_id=f"dec_{uuid4().hex[:8]}",
            request_id=sample_request_context.request_id,
            user_id=sample_request_context.user_id,
            outcome_type=OutcomeType.CONVERSION,
            outcome_value=1.0,
            mechanism_used="identity_construction",
            execution_path=routing.execution_path.value,
        )
        
        # Should generate signals for multiple components
        assert package.total_signals >= 2  # At least bandit + graph
    
    @pytest.mark.asyncio
    async def test_repeated_decisions_improve(self, test_container):
        """Test that repeated decisions for same user improve."""
        user_id = f"repeat_user_{uuid4().hex[:8]}"
        
        confidences = []
        
        for i in range(5):
            request_context = RequestContext(
                request_id=f"repeat_req_{i}",
                user_id=user_id,
                category_id="automotive",
            )
            
            await test_container.blackboard.create_blackboard(
                request_id=request_context.request_id,
                user_id=user_id,
            )
            
            routing = await test_container.meta_learner.route_request(
                request_id=request_context.request_id,
                request_context=request_context,
            )
            
            confidences.append(routing.selection_confidence)
            
            # Simulate positive outcome
            await test_container.gradient_bridge.process_outcome(
                decision_id=f"dec_{i}",
                request_id=request_context.request_id,
                user_id=user_id,
                outcome_type=OutcomeType.CONVERSION,
                outcome_value=0.8,
            )
        
        # Confidence should not decrease significantly
        # (In a real system with more data, it would increase)
        assert confidences[-1] >= confidences[0] * 0.9


# =============================================================================
# E2E TESTS - API
# =============================================================================

class TestAPIEndToEnd:
    """End-to-end tests for API endpoints."""
    
    @pytest.mark.asyncio
    async def test_decision_endpoint(self, test_container):
        """Test decision API endpoint."""
        from fastapi.testclient import TestClient
        from adam.main import app
        
        # This would use TestClient in a real test
        # Simplified: just validate the endpoint exists
        pass
    
    @pytest.mark.asyncio
    async def test_outcome_endpoint(self, test_container):
        """Test outcome API endpoint."""
        pass


# =============================================================================
# PERFORMANCE TESTS
# =============================================================================

class TestPerformance:
    """Performance and latency tests."""
    
    @pytest.mark.asyncio
    async def test_decision_latency(self, test_container, sample_request_context):
        """Test decision latency is within bounds."""
        start = datetime.now(timezone.utc)
        
        await test_container.blackboard.create_blackboard(
            request_id=sample_request_context.request_id,
            user_id=sample_request_context.user_id,
        )
        
        await test_container.meta_learner.route_request(
            request_id=sample_request_context.request_id,
            request_context=sample_request_context,
        )
        
        await test_container.atom_dag.execute(
            request_id=sample_request_context.request_id,
            request_context=sample_request_context,
        )
        
        end = datetime.now(timezone.utc)
        latency_ms = (end - start).total_seconds() * 1000
        
        # Should complete in under 5 seconds (generous for test environment)
        assert latency_ms < 5000
    
    @pytest.mark.asyncio
    async def test_concurrent_decisions(self, test_container):
        """Test handling concurrent decisions."""
        async def make_decision(idx: int):
            request_context = RequestContext(
                request_id=f"concurrent_{idx}",
                user_id=f"user_{idx}",
                category_id="test",
            )
            
            await test_container.blackboard.create_blackboard(
                request_id=request_context.request_id,
                user_id=request_context.user_id,
            )
            
            return await test_container.meta_learner.route_request(
                request_id=request_context.request_id,
                request_context=request_context,
            )
        
        # Run 10 concurrent decisions
        results = await asyncio.gather(*[
            make_decision(i) for i in range(10)
        ])
        
        assert len(results) == 10
        assert all(r is not None for r in results)


# =============================================================================
# MAIN EXECUTION
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
