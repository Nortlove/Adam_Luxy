# =============================================================================
# ADAM Graph Edge Service Tests
# Location: tests/unit/test_graph_edge_service.py
# =============================================================================

"""
Unit tests for the Graph Edge Service.

Tests:
1. Mechanism synergy computation
2. Archetype transfer queries
3. Learning path attribution
4. Causal path discovery
5. Research domain backing
6. Temporal sequence mining
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from adam.intelligence.graph_edge_service import (
    GraphEdgeService,
    MechanismSynergy,
    ArchetypeMechanismPrior,
    LearningPathAttribution,
    CausalPath,
    ResearchDomainBacking,
    get_graph_edge_service,
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def graph_edge_service():
    """Create a GraphEdgeService with no driver (uses defaults)."""
    return GraphEdgeService(neo4j_driver=None)


@pytest.fixture
def mock_neo4j_driver():
    """Create a mock Neo4j driver."""
    driver = MagicMock()
    session = AsyncMock()
    driver.session.return_value.__aenter__ = AsyncMock(return_value=session)
    driver.session.return_value.__aexit__ = AsyncMock(return_value=None)
    return driver, session


# =============================================================================
# SYNERGY TESTS
# =============================================================================

class TestMechanismSynergies:
    """Tests for mechanism synergy computation."""
    
    @pytest.mark.asyncio
    async def test_get_default_synergies_for_automatic_evaluation(
        self,
        graph_edge_service,
    ):
        """Test that default synergies are returned for known mechanisms."""
        synergies = await graph_edge_service.get_mechanism_synergies(
            "automatic_evaluation"
        )
        
        assert len(synergies) > 0
        
        # Check for known synergy
        attention_synergy = next(
            (s for s in synergies if s.target_mechanism == "attention_dynamics"),
            None
        )
        assert attention_synergy is not None
        assert attention_synergy.relationship_type == "synergy"
        assert attention_synergy.synergy_multiplier > 1.0
    
    @pytest.mark.asyncio
    async def test_get_default_synergies_for_unknown_mechanism(
        self,
        graph_edge_service,
    ):
        """Test that empty list is returned for unknown mechanisms."""
        synergies = await graph_edge_service.get_mechanism_synergies(
            "unknown_mechanism"
        )
        
        assert synergies == []
    
    @pytest.mark.asyncio
    async def test_compute_synergy_adjusted_scores(
        self,
        graph_edge_service,
    ):
        """Test that synergy adjustments are applied correctly."""
        base_scores = {
            "automatic_evaluation": 0.8,  # Strong
            "attention_dynamics": 0.5,    # Should get boosted
            "identity_construction": 0.6,  # Should get penalized
            "embodied_cognition": 0.4,
        }
        
        adjusted = await graph_edge_service.compute_synergy_adjusted_scores(
            base_scores
        )
        
        # attention_dynamics should be boosted (synergizes with automatic_evaluation)
        assert adjusted["attention_dynamics"] > base_scores["attention_dynamics"]
        
        # identity_construction should be penalized (antagonizes automatic_evaluation)
        assert adjusted["identity_construction"] < base_scores["identity_construction"]
    
    @pytest.mark.asyncio
    async def test_synergy_filtering_by_context(
        self,
        graph_edge_service,
    ):
        """Test that synergies can be filtered by context."""
        synergies = await graph_edge_service.get_mechanism_synergies(
            "automatic_evaluation",
            context={"context": "initial_exposure"},
        )
        
        # Should include synergy with attention_dynamics (context matches)
        matching = [s for s in synergies if s.target_mechanism == "attention_dynamics"]
        assert len(matching) > 0


# =============================================================================
# ARCHETYPE TRANSFER TESTS
# =============================================================================

class TestArchetypeTransfer:
    """Tests for archetype-based cold start transfer."""
    
    @pytest.mark.asyncio
    async def test_get_default_archetype_priors(
        self,
        graph_edge_service,
    ):
        """Test that default priors are returned for known archetypes."""
        priors = await graph_edge_service.get_archetype_mechanism_priors(
            "analytical_deliberator"
        )
        
        assert len(priors) > 0
        
        # Check for known prior
        construal_prior = next(
            (p for p in priors if p.mechanism_name == "temporal_construal"),
            None
        )
        assert construal_prior is not None
        assert construal_prior.success_rate > 0.5
    
    @pytest.mark.asyncio
    async def test_get_priors_for_unknown_archetype(
        self,
        graph_edge_service,
    ):
        """Test that empty list is returned for unknown archetypes."""
        priors = await graph_edge_service.get_archetype_mechanism_priors(
            "unknown_archetype"
        )
        
        assert priors == []
    
    @pytest.mark.asyncio
    async def test_archetype_priors_have_required_fields(
        self,
        graph_edge_service,
    ):
        """Test that all priors have required fields."""
        priors = await graph_edge_service.get_archetype_mechanism_priors(
            "social_validator"
        )
        
        for prior in priors:
            assert prior.archetype_id == "social_validator"
            assert prior.mechanism_name
            assert 0 <= prior.success_rate <= 1
            assert 0 <= prior.confidence <= 1
            assert prior.sample_size >= 0


# =============================================================================
# CAUSAL PATH TESTS
# =============================================================================

class TestCausalPaths:
    """Tests for causal path discovery."""
    
    @pytest.mark.asyncio
    async def test_find_default_causal_paths(
        self,
        graph_edge_service,
    ):
        """Test that default causal paths are returned."""
        paths = await graph_edge_service.find_causal_paths(
            target_outcome="conversion"
        )
        
        assert len(paths) > 0
        
        # Check path structure
        first_path = paths[0]
        assert len(first_path.path_nodes) > 0
        assert first_path.path_strength > 0
        assert first_path.controllable_trigger
        assert first_path.target_outcome == "conversion"
    
    @pytest.mark.asyncio
    async def test_causal_paths_ordered_by_strength(
        self,
        graph_edge_service,
    ):
        """Test that paths are ordered by strength."""
        paths = await graph_edge_service.find_causal_paths("conversion")
        
        if len(paths) > 1:
            for i in range(len(paths) - 1):
                assert paths[i].path_strength >= paths[i + 1].path_strength


# =============================================================================
# RESEARCH BACKING TESTS
# =============================================================================

class TestResearchBacking:
    """Tests for research domain backing."""
    
    @pytest.mark.asyncio
    async def test_get_default_research_backing(
        self,
        graph_edge_service,
    ):
        """Test that default research backing is returned."""
        backings = await graph_edge_service.get_research_backing(
            "regulatory_focus"
        )
        
        assert len(backings) > 0
        
        first = backings[0]
        assert first.mechanism_name == "regulatory_focus"
        assert first.research_domain
        assert first.effect_size > 0
        assert first.confidence_tier >= 1
    
    @pytest.mark.asyncio
    async def test_research_backing_for_unknown_mechanism(
        self,
        graph_edge_service,
    ):
        """Test that empty list is returned for unknown mechanisms."""
        backings = await graph_edge_service.get_research_backing(
            "unknown_mechanism"
        )
        
        assert backings == []


# =============================================================================
# TEMPORAL SEQUENCE TESTS
# =============================================================================

class TestTemporalSequences:
    """Tests for temporal sequence mining."""
    
    @pytest.mark.asyncio
    async def test_find_default_sequences(
        self,
        graph_edge_service,
    ):
        """Test that default sequences are returned."""
        sequences = await graph_edge_service.find_effective_sequences(
            target_outcome="conversion"
        )
        
        assert len(sequences) > 0
        
        first = sequences[0]
        assert "sequence" in first
        assert len(first["sequence"]) > 0
        assert first["support"] > 0
        assert first["target_outcome"] == "conversion"


# =============================================================================
# COMPREHENSIVE INSIGHTS TESTS
# =============================================================================

class TestComprehensiveInsights:
    """Tests for comprehensive edge insights."""
    
    @pytest.mark.asyncio
    async def test_get_comprehensive_insights(
        self,
        graph_edge_service,
    ):
        """Test getting comprehensive insights."""
        insights = await graph_edge_service.get_comprehensive_edge_insights(
            user_id="test_user",
            mechanism_name="social_proof",
        )
        
        assert "timestamp" in insights
        assert "user_id" in insights
        assert "mechanism" in insights
        assert "synergies" in insights
        assert "causal_paths" in insights
        assert "effective_sequences" in insights


# =============================================================================
# SINGLETON TESTS
# =============================================================================

class TestSingleton:
    """Tests for singleton pattern."""
    
    def test_get_graph_edge_service_returns_same_instance(self):
        """Test that get_graph_edge_service returns singleton."""
        service1 = get_graph_edge_service()
        service2 = get_graph_edge_service()
        
        assert service1 is service2
    
    def test_clear_caches(self, graph_edge_service):
        """Test that caches can be cleared."""
        # Populate cache
        graph_edge_service._synergy_cache["test"] = []
        graph_edge_service._archetype_cache["test"] = []
        
        # Clear
        graph_edge_service.clear_caches()
        
        assert len(graph_edge_service._synergy_cache) == 0
        assert len(graph_edge_service._archetype_cache) == 0
