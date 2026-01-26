# =============================================================================
# ADAM Cohort Discovery Service Tests
# Location: tests/unit/test_cohort_discovery.py
# =============================================================================

"""
Unit tests for the Cohort Discovery Service.

Tests:
1. Cohort discovery with defaults
2. User cohort assignment
3. Cohort-level learning
4. Cohort boost computation
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from adam.intelligence.cohort_discovery import (
    CohortDiscoveryService,
    UserCohort,
    CohortMembership,
    CohortLearningSignal,
    get_cohort_discovery_service,
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def cohort_service():
    """Create a CohortDiscoveryService with no driver (uses defaults)."""
    return CohortDiscoveryService(neo4j_driver=None)


@pytest.fixture
def populated_cohort_service():
    """Create a service with pre-populated cohorts."""
    service = CohortDiscoveryService(neo4j_driver=None)
    
    # Add default cohorts
    service._cohorts = {
        "cohort_analytical": UserCohort(
            cohort_id="cohort_analytical",
            size=100,
            sample_members=["user_1", "user_2"],
            dominant_mechanisms=["temporal_construal", "anchoring"],
            mechanism_effectiveness={"temporal_construal": 0.65, "anchoring": 0.6},
        ),
        "cohort_social": UserCohort(
            cohort_id="cohort_social",
            size=150,
            sample_members=["user_3", "user_4"],
            dominant_mechanisms=["social_proof", "mimetic_desire"],
            mechanism_effectiveness={"social_proof": 0.7, "mimetic_desire": 0.65},
        ),
    }
    
    # Add user assignments
    service._user_cohorts = {
        "user_1": CohortMembership(
            user_id="user_1",
            cohort_id="cohort_analytical",
            membership_score=0.9,
        ),
        "user_3": CohortMembership(
            user_id="user_3",
            cohort_id="cohort_social",
            membership_score=0.85,
        ),
    }
    
    return service


# =============================================================================
# COHORT DISCOVERY TESTS
# =============================================================================

class TestCohortDiscovery:
    """Tests for cohort discovery."""
    
    @pytest.mark.asyncio
    async def test_discover_returns_default_cohorts(
        self,
        cohort_service,
    ):
        """Test that default cohorts are returned when no Neo4j."""
        cohorts = await cohort_service.discover_cohorts()
        
        assert len(cohorts) > 0
        
        # Check cohort structure
        first = cohorts[0]
        assert first.cohort_id
        assert first.size > 0
        assert len(first.dominant_mechanisms) > 0
    
    @pytest.mark.asyncio
    async def test_discovered_cohorts_stored(
        self,
        cohort_service,
    ):
        """Test that discovered cohorts are stored."""
        await cohort_service.discover_cohorts()
        
        # Should have cohorts in cache
        assert len(cohort_service._cohorts) > 0


# =============================================================================
# USER COHORT TESTS
# =============================================================================

class TestUserCohort:
    """Tests for user cohort assignment."""
    
    @pytest.mark.asyncio
    async def test_get_user_cohort_from_cache(
        self,
        populated_cohort_service,
    ):
        """Test getting user cohort from cache."""
        membership = await populated_cohort_service.get_user_cohort("user_1")
        
        assert membership is not None
        assert membership.user_id == "user_1"
        assert membership.cohort_id == "cohort_analytical"
        assert membership.membership_score == 0.9
    
    @pytest.mark.asyncio
    async def test_get_user_cohort_returns_none_for_unknown(
        self,
        populated_cohort_service,
    ):
        """Test that None is returned for unknown users."""
        membership = await populated_cohort_service.get_user_cohort("unknown_user")
        
        assert membership is None
    
    @pytest.mark.asyncio
    async def test_get_cohort_by_id(
        self,
        populated_cohort_service,
    ):
        """Test getting cohort by ID."""
        cohort = await populated_cohort_service.get_cohort("cohort_analytical")
        
        assert cohort is not None
        assert cohort.cohort_id == "cohort_analytical"
        assert cohort.size == 100


# =============================================================================
# COHORT LEARNING TESTS
# =============================================================================

class TestCohortLearning:
    """Tests for cohort-level learning."""
    
    @pytest.mark.asyncio
    async def test_aggregate_learning_signal(
        self,
        populated_cohort_service,
    ):
        """Test aggregating learning signal at cohort level."""
        signal = await populated_cohort_service.aggregate_learning_signal(
            user_id="user_1",
            mechanism_id="temporal_construal",
            outcome_value=0.8,
        )
        
        assert signal is not None
        assert signal.cohort_id == "cohort_analytical"
        assert signal.mechanism_id == "temporal_construal"
        assert signal.signal_type == "effectiveness_update"
    
    @pytest.mark.asyncio
    async def test_aggregate_updates_effectiveness(
        self,
        populated_cohort_service,
    ):
        """Test that aggregation updates cohort effectiveness."""
        original = populated_cohort_service._cohorts["cohort_analytical"].mechanism_effectiveness.get(
            "temporal_construal", 0.5
        )
        
        # Aggregate with high outcome
        await populated_cohort_service.aggregate_learning_signal(
            user_id="user_1",
            mechanism_id="temporal_construal",
            outcome_value=1.0,
        )
        
        new = populated_cohort_service._cohorts["cohort_analytical"].mechanism_effectiveness.get(
            "temporal_construal"
        )
        
        # Should have increased (learning rate 0.1)
        assert new > original
    
    @pytest.mark.asyncio
    async def test_aggregate_returns_none_for_unknown_user(
        self,
        populated_cohort_service,
    ):
        """Test that None is returned for users not in cohorts."""
        signal = await populated_cohort_service.aggregate_learning_signal(
            user_id="unknown_user",
            mechanism_id="social_proof",
            outcome_value=0.8,
        )
        
        assert signal is None


# =============================================================================
# COHORT BOOST TESTS
# =============================================================================

class TestCohortBoost:
    """Tests for cohort-based boosting."""
    
    @pytest.mark.asyncio
    async def test_get_cohort_boost(
        self,
        populated_cohort_service,
    ):
        """Test cohort boost is applied correctly."""
        base_scores = {
            "temporal_construal": 0.5,
            "anchoring": 0.5,
            "social_proof": 0.5,
        }
        
        boosted = await populated_cohort_service.get_cohort_boost(
            user_id="user_1",
            mechanism_scores=base_scores,
        )
        
        # temporal_construal should be boosted (cohort effectiveness > 0.5)
        assert boosted["temporal_construal"] > base_scores["temporal_construal"]
        
        # anchoring should be boosted (cohort effectiveness > 0.5)
        assert boosted["anchoring"] > base_scores["anchoring"]
    
    @pytest.mark.asyncio
    async def test_cohort_boost_returns_original_for_unknown_user(
        self,
        populated_cohort_service,
    ):
        """Test that original scores are returned for unknown users."""
        base_scores = {"social_proof": 0.5}
        
        boosted = await populated_cohort_service.get_cohort_boost(
            user_id="unknown_user",
            mechanism_scores=base_scores,
        )
        
        assert boosted == base_scores


# =============================================================================
# COHORT MECHANISM PRIORS TESTS
# =============================================================================

class TestCohortMechanismPriors:
    """Tests for cohort mechanism priors."""
    
    @pytest.mark.asyncio
    async def test_get_cohort_mechanism_priors(
        self,
        populated_cohort_service,
    ):
        """Test getting mechanism priors for a cohort."""
        priors = await populated_cohort_service.get_cohort_mechanism_priors(
            "cohort_analytical"
        )
        
        assert "temporal_construal" in priors
        assert priors["temporal_construal"] == 0.65
    
    @pytest.mark.asyncio
    async def test_get_priors_empty_for_unknown_cohort(
        self,
        populated_cohort_service,
    ):
        """Test that empty dict is returned for unknown cohorts."""
        priors = await populated_cohort_service.get_cohort_mechanism_priors(
            "unknown_cohort"
        )
        
        assert priors == {}


# =============================================================================
# STATISTICS TESTS
# =============================================================================

class TestStatistics:
    """Tests for service statistics."""
    
    def test_get_statistics(self, populated_cohort_service):
        """Test getting service statistics."""
        stats = populated_cohort_service.get_statistics()
        
        assert "cohorts_discovered" in stats
        assert "users_assigned" in stats
        assert "projection_active" in stats
        assert stats["cohorts_discovered"] == 2
        assert stats["users_assigned"] == 2


# =============================================================================
# SINGLETON TESTS
# =============================================================================

class TestSingleton:
    """Tests for singleton pattern."""
    
    def test_get_cohort_discovery_service_returns_same_instance(self):
        """Test that get_cohort_discovery_service returns singleton."""
        service1 = get_cohort_discovery_service()
        service2 = get_cohort_discovery_service()
        
        assert service1 is service2
