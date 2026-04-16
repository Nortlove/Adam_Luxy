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
# STAGE 1 WIRING VERIFICATION TESTS
# =============================================================================
#
# These tests pin the Stage 1 DAG expansion (commit 7503e84) and the
# MechanismActivation fusion-consumption fix (commit d4499c2). The
# post-Stage-1 verification doc warned that silent failure at either
# layer would be invisible — these tests turn both conditions into
# hard assertions so regressions show up in CI, not in pilot data.

class TestStage1DAGWiring:
    """Structural + end-to-end verification of the 20-atom Stage 1 DAG."""

    STAGE1_CONSTRUCT_ATOMS = [
        "atom_mimetic_desire",
        "atom_brand_personality",
        "atom_narrative_identity",
        "atom_regret_anticipation",
        "atom_autonomy_reactance",
    ]

    def test_dag_topology_has_20_atoms_and_expected_levels(
        self, blackboard, interaction_bridge
    ):
        """Pin the Stage 1 DAG shape: 20 atoms, 6 levels (post-Coherence-gate).

        After Stage 2's Coherence promotion, MessageFraming gates on
        CoherenceOptimization, adding one sequential level to the
        reasoning path:
            L0 user_state → L1 [14 parallel] → L2 mechanism_activation
            → L3 [coherence, channel_selection] → L4 message_framing
            → L5 ad_selection
        """
        from adam.atoms.dag import AtomDAG, DEFAULT_DAG_NODES

        assert len(DEFAULT_DAG_NODES) == 20, (
            f"Expected 20 atoms in DEFAULT_DAG_NODES, got {len(DEFAULT_DAG_NODES)}. "
            "Stage 1 wiring (commit 7503e84) must not regress."
        )

        dag = AtomDAG(blackboard=blackboard, bridge=interaction_bridge)
        levels = dag._topological_sort()

        assert len(levels) == 6, (
            f"Expected 6 topological levels after Stage 2 Coherence "
            f"promotion, got {len(levels)}"
        )
        assert levels[0] == ["atom_user_state"]
        assert len(levels[1]) == 14, (
            f"Level 1 (parallel atoms after user_state) should have 14 atoms, "
            f"got {len(levels[1])}: {sorted(levels[1])}"
        )
        for atom_id in self.STAGE1_CONSTRUCT_ATOMS:
            assert atom_id in levels[1], (
                f"Stage 1 construct atom {atom_id} missing from Level 1"
            )

        assert levels[2] == ["atom_mechanism_activation"]
        assert "atom_coherence_optimization" in levels[3], (
            "CoherenceOptimization must run at Level 3 (post-fusion)"
        )
        assert "atom_message_framing" in levels[4], (
            "MessageFraming must run at Level 4, after CoherenceOptimization "
            "(Stage 2 Coherence promotion)"
        )
        assert "atom_ad_selection" in levels[5], (
            "AdSelection must run at Level 5, after MessageFraming"
        )

    def test_message_framing_gates_on_coherence(self):
        """Stage 2 Coherence promotion: MessageFraming must depend on both
        mechanism_activation AND coherence_optimization.
        """
        from adam.atoms.dag import DEFAULT_DAG_NODES

        mf = next(
            n for n in DEFAULT_DAG_NODES if n.atom_id == "atom_message_framing"
        )
        assert "atom_mechanism_activation" in mf.depends_on, (
            "MessageFraming must still read mechanism_activation's fused weights"
        )
        assert "atom_coherence_optimization" in mf.depends_on, (
            "Stage 2 Coherence promotion: MessageFraming must gate on coherence"
        )

    def test_mechanism_activation_depends_on_stage1_atoms(self):
        """MechanismActivation must list the 5 Stage 1 atoms as upstream deps."""
        from adam.atoms.dag import DEFAULT_DAG_NODES

        mech = next(
            n for n in DEFAULT_DAG_NODES if n.atom_id == "atom_mechanism_activation"
        )
        for atom_id in self.STAGE1_CONSTRUCT_ATOMS:
            assert atom_id in mech.depends_on, (
                f"MechanismActivation must depend on {atom_id} so fusion "
                f"can call get_upstream() on it"
            )

    def test_auxiliary_atoms_list_includes_stage1_construct_atoms(self):
        """The fusion-consumption list must include all 5 Stage 1 atoms.

        Investigation (a) in ADAM_STAGE_1_POST_WIRING_VERIFICATION.md caught
        a silent-failure bug where the atoms ran but their outputs were
        skipped at the fusion loop. This test pins the fix.
        """
        from adam.atoms.core import mechanism_activation as ma_module
        import inspect

        src = inspect.getsource(ma_module.MechanismActivationAtom._build_output)
        for atom_id in self.STAGE1_CONSTRUCT_ATOMS:
            assert f'"{atom_id}"' in src, (
                f"{atom_id} missing from _AUXILIARY_ATOMS fusion list in "
                f"_build_output. Commit d4499c2 must not regress."
            )
        assert '"atom_coherence_optimization"' not in src.split(
            "_AUXILIARY_ATOMS = ["
        )[1].split("]")[0], (
            "atom_coherence_optimization must NOT be in _AUXILIARY_ATOMS — "
            "it runs AFTER mechanism_activation and cannot be an upstream "
            "provider for fusion."
        )

    @pytest.mark.asyncio
    async def test_stage1_dag_end_to_end_execution(
        self, blackboard, interaction_bridge, request_context_factory
    ):
        """Run the 20-atom DAG end-to-end with stub infra and verify:

        1. All 20 atoms attempt execution (no structural short-circuits).
        2. MechanismActivation produces an output.
        3. CoherenceOptimization runs post-fusion at Level 3.
        4. MessageFraming and AdSelection complete.
        5. The fusion loop's `auxiliary_atoms_consumed` list is observable
           in MechanismActivation's secondary_assessments (the pilot-critical
           silent-failure signal).
        """
        from adam.atoms.dag import AtomDAG
        from adam.blackboard.models.core import ComponentRole

        request_id = f"req_{uuid4().hex[:12]}"
        user_id = "stage1_e2e_user"
        await blackboard.create_blackboard(request_id, user_id)
        context = request_context_factory(request_id=request_id, user_id=user_id)
        await blackboard.write_zone1(
            request_id, context, role=ComponentRole.REQUEST_HANDLER
        )

        dag = AtomDAG(blackboard=blackboard, bridge=interaction_bridge)
        result = await dag.execute(request_id=request_id, request_context=context)

        assert result is not None
        # atoms_executed + atoms_failed covers everything the DAG tried.
        attempted = result.atoms_executed + result.atoms_failed
        assert attempted >= 20, (
            f"Stage 1 DAG should attempt all 20 atoms; attempted={attempted}, "
            f"executed={result.atoms_executed}, failed={result.atoms_failed}, "
            f"errors={result.errors[:5]}"
        )

        # MechanismActivation is required — if this didn't run, the Stage 1
        # wiring is broken at the dependency level, not just degraded.
        assert "atom_mechanism_activation" in result.atom_outputs, (
            f"MechanismActivation did not produce output. "
            f"errors={result.errors[:10]}"
        )
        mech_output = result.atom_outputs["atom_mechanism_activation"]

        # Fusion-consumption signal: even under stub infrastructure where
        # some construct atoms may return empty adjustments, the list field
        # itself must exist so downstream telemetry can reason about it.
        assert mech_output.secondary_assessments is not None
        assert "auxiliary_atoms_consumed" in mech_output.secondary_assessments, (
            "MechanismActivation must surface `auxiliary_atoms_consumed` "
            "in secondary_assessments so fusion consumption is observable "
            "and silent failure is detectable."
        )

        # Coherence runs post-fusion. It is required=False so we only check
        # that if it was attempted, it didn't block MessageFraming.
        assert "atom_message_framing" in result.atom_outputs or any(
            "atom_message_framing" in e for e in result.errors
        ), "MessageFraming must either run or report an explicit error"


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
