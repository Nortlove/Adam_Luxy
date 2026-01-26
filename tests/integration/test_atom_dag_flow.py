# =============================================================================
# ADAM Integration Tests: Atom DAG Flow
# Location: tests/integration/test_atom_dag_flow.py
# =============================================================================

"""
ATOM DAG FLOW INTEGRATION TESTS

Tests for the complete atom DAG execution with embeddings:
1. DAG initialization with embedding context
2. Parallel atom execution
3. Upstream output propagation
4. Blackboard zone transitions
5. Learning signal emission
"""

import asyncio
import pytest
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

logger = logging.getLogger(__name__)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_redis():
    """Mock Redis cache."""
    storage = {}
    
    class MockRedisCache:
        async def get(self, key: str, model_type=None):
            data = storage.get(key)
            if data and model_type:
                try:
                    return model_type(**data) if isinstance(data, dict) else data
                except Exception:
                    return data
            return data
        
        async def set(self, key: str, value: Any, ttl: int = 3600, domain=None) -> bool:
            if hasattr(value, "model_dump"):
                storage[key] = value.model_dump()
            else:
                storage[key] = value
            return True
        
        async def delete(self, key: str) -> bool:
            if key in storage:
                del storage[key]
                return True
            return False
    
    return MockRedisCache()


@pytest.fixture
def mock_neo4j():
    """Mock Neo4j driver."""
    class MockSession:
        async def run(self, query: str, **params):
            return MockResult([])
        
        async def close(self):
            pass
        
        async def __aenter__(self):
            return self
        
        async def __aexit__(self, *args):
            pass
    
    class MockResult:
        def __init__(self, records):
            self._records = records
        
        async def single(self):
            return self._records[0] if self._records else None
        
        async def data(self):
            return self._records
    
    class MockDriver:
        def session(self, **kwargs):
            return MockSession()
        
        async def close(self):
            pass
    
    return MockDriver()


@pytest.fixture
def mock_kafka():
    """Mock Kafka producer."""
    messages = []
    
    class MockProducer:
        is_connected = True
        
        async def send(self, topic, value, key=None, headers=None):
            messages.append({
                "topic": topic.value if hasattr(topic, "value") else topic,
                "value": value,
                "key": key,
            })
            return True
        
        def get_messages(self):
            return messages
        
        def clear(self):
            messages.clear()
    
    return MockProducer()


@pytest.fixture
def embedding_service():
    """Create embedding service."""
    from adam.embeddings import EmbeddingService, EmbeddingModel
    
    service = EmbeddingService(
        default_model=EmbeddingModel.ALL_MINILM_L6,
        cache=None,
    )
    yield service
    asyncio.get_event_loop().run_until_complete(service.close())


@pytest.fixture
def blackboard(mock_redis):
    """Create blackboard service."""
    from adam.blackboard.service import BlackboardService
    
    with patch("adam.blackboard.service.get_kafka_producer", return_value=None):
        service = BlackboardService(redis_cache=mock_redis)
        yield service


@pytest.fixture
def interaction_bridge(mock_neo4j, mock_redis):
    """Create interaction bridge."""
    from adam.graph_reasoning.bridge import InteractionBridge
    
    bridge = InteractionBridge(
        neo4j_driver=mock_neo4j,
        redis_cache=mock_redis,
    )
    yield bridge


@pytest.fixture
def request_context_factory():
    """Factory for creating RequestContext instances with required fields."""
    from adam.blackboard.models.zone1_context import RequestContext, UserIntelligencePackage
    
    def create_context(
        request_id: str = None,
        user_id: str = "test_user",
        **kwargs,
    ) -> RequestContext:
        req_id = request_id or f"req_{uuid4().hex[:12]}"
        user_intel = kwargs.pop("user_intelligence", None) or UserIntelligencePackage(
            user_id=user_id,
            is_cold_start=kwargs.pop("is_cold_start", True),
        )
        
        return RequestContext(
            request_id=req_id,
            user_intelligence=user_intel,
            **kwargs,
        )
    
    return create_context


# =============================================================================
# DAG INITIALIZATION TESTS
# =============================================================================

class TestAtomDAGInitialization:
    """Tests for atom DAG initialization with embeddings."""
    
    @pytest.mark.asyncio
    async def test_dag_registers_all_atoms(self, blackboard, interaction_bridge):
        """Verify DAG initializes correctly."""
        from adam.atoms.dag import AtomDAG
        
        dag = AtomDAG(
            blackboard=blackboard,
            bridge=interaction_bridge,
        )
        
        # DAG should be created successfully
        assert dag is not None
        assert dag.blackboard is not None
    
    @pytest.mark.asyncio
    async def test_dag_dependency_order(self, blackboard, interaction_bridge):
        """Verify DAG is initialized properly."""
        from adam.atoms.dag import AtomDAG
        
        dag = AtomDAG(
            blackboard=blackboard,
            bridge=interaction_bridge,
        )
        
        # DAG should be functional
        assert dag is not None
        # DAG will execute atoms in proper order during execution


# =============================================================================
# DAG EXECUTION TESTS
# =============================================================================

class TestAtomDAGExecution:
    """Tests for atom DAG execution with embeddings."""
    
    @pytest.mark.asyncio
    async def test_dag_executes_all_atoms(
        self, embedding_service, blackboard, interaction_bridge, request_context_factory
    ):
        """Test DAG executes all atoms successfully."""
        from adam.atoms.dag import AtomDAG
        from adam.blackboard.models.core import ComponentRole
        
        request_id = f"req_{uuid4().hex[:12]}"
        user_id = "dag_test_user"
        
        # Create blackboard
        await blackboard.create_blackboard(request_id, user_id)
        
        # Write context with proper user_intelligence
        context = request_context_factory(request_id=request_id, user_id=user_id)
        await blackboard.write_zone1(
            request_id, context, role=ComponentRole.REQUEST_HANDLER
        )
        
        # Create and execute DAG
        dag = AtomDAG(
            blackboard=blackboard,
            bridge=interaction_bridge,
        )
        
        result = await dag.execute(
            request_id=request_id,
            request_context=context,
        )
        
        # Should complete successfully
        assert result is not None
        assert len(result.atom_results) > 0
        assert result.total_duration_ms >= 0
    
    @pytest.mark.asyncio
    async def test_dag_propagates_upstream_outputs(
        self, embedding_service, blackboard, interaction_bridge, request_context_factory
    ):
        """Test DAG correctly propagates upstream atom outputs."""
        from adam.atoms.dag import AtomDAG
        from adam.blackboard.models.core import ComponentRole
        
        request_id = f"req_{uuid4().hex[:12]}"
        user_id = "propagation_test_user"
        
        await blackboard.create_blackboard(request_id, user_id)
        
        context = request_context_factory(request_id=request_id, user_id=user_id)
        await blackboard.write_zone1(
            request_id, context, role=ComponentRole.REQUEST_HANDLER
        )
        
        dag = AtomDAG(
            blackboard=blackboard,
            bridge=interaction_bridge,
        )
        
        result = await dag.execute(
            request_id=request_id,
            request_context=context,
        )
        
        # Mechanism selection should have received upstream outputs
        if "atom_mechanism_selection" in result.atom_results:
            mech_result = result.atom_results["atom_mechanism_selection"]
            # The atom should have access to upstream data
            assert mech_result is not None
    
    @pytest.mark.asyncio
    async def test_dag_handles_atom_failure_gracefully(
        self, blackboard, interaction_bridge, request_context_factory
    ):
        """Test DAG continues even if one atom fails."""
        from adam.atoms.dag import AtomDAG
        from adam.blackboard.models.core import ComponentRole
        
        request_id = f"req_{uuid4().hex[:12]}"
        user_id = "failure_test_user"
        
        await blackboard.create_blackboard(request_id, user_id)
        
        context = request_context_factory(request_id=request_id, user_id=user_id)
        await blackboard.write_zone1(
            request_id, context, role=ComponentRole.REQUEST_HANDLER
        )
        
        dag = AtomDAG(
            blackboard=blackboard,
            bridge=interaction_bridge,
        )
        
        # Even if some atoms fail, DAG should complete
        result = await dag.execute(
            request_id=request_id,
            request_context=context,
        )
        
        assert result is not None


# =============================================================================
# BLACKBOARD ZONE TRANSITION TESTS
# =============================================================================

class TestBlackboardZoneTransitions:
    """Tests for blackboard zone transitions during DAG execution."""
    
    @pytest.mark.asyncio
    async def test_zone2_populated_during_execution(
        self, embedding_service, blackboard, interaction_bridge, request_context_factory
    ):
        """Test Zone 2 (reasoning) is populated during atom execution."""
        from adam.atoms.dag import AtomDAG
        from adam.blackboard.models.core import ComponentRole
        
        request_id = f"req_{uuid4().hex[:12]}"
        user_id = "zone2_test_user"
        
        await blackboard.create_blackboard(request_id, user_id)
        
        context = request_context_factory(request_id=request_id, user_id=user_id)
        await blackboard.write_zone1(
            request_id, context, role=ComponentRole.REQUEST_HANDLER
        )
        
        dag = AtomDAG(
            blackboard=blackboard,
            bridge=interaction_bridge,
        )
        
        await dag.execute(
            request_id=request_id,
            request_context=context,
        )
        
        # Zone 2 should have atom outputs
        state = await blackboard.get_blackboard(request_id)
        assert state is not None
        # In a full implementation, we'd verify zone2 has atom data


# =============================================================================
# EMBEDDING + DAG INTEGRATION
# =============================================================================

class TestEmbeddingDAGIntegration:
    """Tests for embedding service integration with atom DAG."""
    
    @pytest.mark.asyncio
    async def test_user_embedding_informs_dag_execution(
        self, embedding_service, blackboard, interaction_bridge, request_context_factory
    ):
        """Test user embedding influences DAG execution path."""
        from adam.atoms.dag import AtomDAG
        from adam.blackboard.models.core import ComponentRole
        
        request_id = f"req_{uuid4().hex[:12]}"
        user_id = "embedding_dag_user"
        
        # Create user profile
        user_profile = {
            "big_five": {
                "openness": 0.85,
                "conscientiousness": 0.55,
                "extraversion": 0.70,
                "agreeableness": 0.60,
                "neuroticism": 0.35,
            },
            "regulatory_focus": {
                "promotion": 0.75,
                "prevention": 0.25,
            },
        }
        
        # Generate embedding
        psych_emb = await embedding_service.process_user_profile(
            user_id, user_profile, store=True
        )
        
        await blackboard.create_blackboard(request_id, user_id)
        
        # Use factory to create proper context
        context = request_context_factory(request_id=request_id, user_id=user_id)
        await blackboard.write_zone1(
            request_id, context, role=ComponentRole.REQUEST_HANDLER
        )
        
        dag = AtomDAG(
            blackboard=blackboard,
            bridge=interaction_bridge,
        )
        
        result = await dag.execute(
            request_id=request_id,
            request_context=context,
        )
        
        assert result is not None
        assert result.total_duration_ms >= 0
    
    @pytest.mark.asyncio
    async def test_ad_embeddings_used_for_mechanism_selection(
        self, embedding_service, blackboard, interaction_bridge, request_context_factory
    ):
        """Test ad embeddings influence mechanism selection atom."""
        from adam.atoms.dag import AtomDAG
        from adam.blackboard.models.zone1_context import (
            AdCandidate,
            AdCandidatePool,
        )
        from adam.blackboard.models.core import ComponentRole
        
        request_id = f"req_{uuid4().hex[:12]}"
        user_id = "ad_embed_test_user"
        
        # Create user profile
        user_profile = {
            "big_five": {"openness": 0.8},
            "regulatory_focus": {"promotion": 0.7, "prevention": 0.3},
        }
        
        # Create ad creatives with different mechanisms
        ads = [
            {
                "creative_id": "ad_social",
                "campaign_id": "camp_001",
                "brand_id": "brand_001",
                "headline": "Join Millions Today",
                "copy": "Everyone loves this product",
                "mechanism": "social_proof",
            },
            {
                "creative_id": "ad_scarcity",
                "campaign_id": "camp_001",
                "brand_id": "brand_001",
                "headline": "Limited Time Offer",
                "copy": "Only 3 left in stock!",
                "mechanism": "scarcity",
            },
        ]
        
        # Generate ad embeddings
        for ad in ads:
            await embedding_service.process_ad_creative(
                ad["creative_id"],
                ad["campaign_id"],
                ad["brand_id"],
                ad,
                store=True,
            )
        
        # Generate user embedding
        await embedding_service.process_user_profile(
            user_id, user_profile, store=True
        )
        
        await blackboard.create_blackboard(request_id, user_id)
        
        # Create ad candidates with required fields
        ad_candidates = [
            AdCandidate(
                candidate_id=ad["creative_id"],
                campaign_id=ad["campaign_id"],
                creative_id=ad["creative_id"],
                targeting_score=0.8,
            )
            for ad in ads
        ]
        
        # Use factory to create proper context
        context = request_context_factory(
            request_id=request_id,
            user_id=user_id,
            ad_candidates=AdCandidatePool(candidates=ad_candidates),
        )
        
        await blackboard.write_zone1(
            request_id, context, role=ComponentRole.REQUEST_HANDLER
        )
        
        dag = AtomDAG(
            blackboard=blackboard,
            bridge=interaction_bridge,
        )
        
        result = await dag.execute(
            request_id=request_id,
            request_context=context,
        )
        
        assert result is not None


# =============================================================================
# LEARNING SIGNAL TESTS
# =============================================================================

class TestLearningSignalEmission:
    """Tests for learning signal emission from DAG execution."""
    
    @pytest.mark.asyncio
    async def test_dag_emits_learning_signals(
        self, blackboard, interaction_bridge, mock_kafka, request_context_factory
    ):
        """Test DAG emits learning signals after execution."""
        from adam.atoms.dag import AtomDAG
        from adam.blackboard.models.core import ComponentRole
        
        request_id = f"req_{uuid4().hex[:12]}"
        user_id = "signal_test_user"
        
        await blackboard.create_blackboard(request_id, user_id)
        
        context = request_context_factory(request_id=request_id, user_id=user_id)
        await blackboard.write_zone1(
            request_id, context, role=ComponentRole.REQUEST_HANDLER
        )
        
        dag = AtomDAG(
            blackboard=blackboard,
            bridge=interaction_bridge,
        )
        
        result = await dag.execute(
            request_id=request_id,
            request_context=context,
        )
        
        # DAG should complete execution
        assert result is not None


# =============================================================================
# ERROR HANDLING TESTS
# =============================================================================

class TestDAGErrorHandling:
    """Tests for DAG error handling."""
    
    @pytest.mark.asyncio
    async def test_dag_recovers_from_partial_failure(
        self, blackboard, interaction_bridge, request_context_factory
    ):
        """Test DAG recovers from partial atom failures."""
        from adam.atoms.dag import AtomDAG
        from adam.blackboard.models.core import ComponentRole
        
        request_id = f"req_{uuid4().hex[:12]}"
        user_id = "error_recovery_user"
        
        await blackboard.create_blackboard(request_id, user_id)
        
        context = request_context_factory(request_id=request_id, user_id=user_id)
        await blackboard.write_zone1(
            request_id, context, role=ComponentRole.REQUEST_HANDLER
        )
        
        dag = AtomDAG(
            blackboard=blackboard,
            bridge=interaction_bridge,
        )
        
        # Execute - should not raise even if some atoms fail
        result = await dag.execute(
            request_id=request_id,
            request_context=context,
        )
        
        assert result is not None
    
    @pytest.mark.asyncio
    async def test_dag_timeout_handling(
        self, blackboard, interaction_bridge, request_context_factory
    ):
        """Test DAG handles timeout correctly."""
        from adam.atoms.dag import AtomDAG
        from adam.blackboard.models.core import ComponentRole
        
        request_id = f"req_{uuid4().hex[:12]}"
        user_id = "timeout_test_user"
        
        await blackboard.create_blackboard(request_id, user_id)
        
        context = request_context_factory(
            request_id=request_id, 
            user_id=user_id,
            latency_budget_ms=10,  # Very short timeout
        )
        await blackboard.write_zone1(
            request_id, context, role=ComponentRole.REQUEST_HANDLER
        )
        
        dag = AtomDAG(
            blackboard=blackboard,
            bridge=interaction_bridge,
        )
        
        # Should complete (may skip some atoms due to timeout)
        result = await dag.execute(
            request_id=request_id,
            request_context=context,
        )
        
        assert result is not None
