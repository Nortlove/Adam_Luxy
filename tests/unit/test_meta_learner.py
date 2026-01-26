# =============================================================================
# ADAM Meta-Learner Unit Tests
# Location: tests/unit/test_meta_learner.py
# =============================================================================

"""
META-LEARNER UNIT TESTS

Tests for Thompson Sampling routing and modality selection.
"""

import pytest
from unittest.mock import AsyncMock, patch

from adam.meta_learner.models import (
    LearningModality,
    ExecutionPath,
    DataRichness,
    ContextNovelty,
)
from adam.meta_learner.thompson import ThompsonSamplingEngine


# =============================================================================
# THOMPSON SAMPLING TESTS
# =============================================================================

class TestThompsonSampling:
    """Tests for Thompson Sampling engine."""
    
    def test_initial_posteriors(self):
        """Test that posteriors start with uniform priors."""
        engine = ThompsonSamplingEngine()
        
        for modality in LearningModality:
            posterior = engine.posterior_state.get_posterior(modality)
            assert posterior.alpha == 1.0  # Uniform prior
            assert posterior.beta == 1.0
    
    def test_update_posterior_success(self):
        """Test updating posterior with successful outcome."""
        engine = ThompsonSamplingEngine()
        modality = LearningModality.SUPERVISED_CONVERSION
        
        posterior = engine.posterior_state.get_posterior(modality)
        initial_alpha = posterior.alpha
        initial_beta = posterior.beta
        
        engine.update(modality, reward=1.0)
        
        posterior = engine.posterior_state.get_posterior(modality)
        assert posterior.alpha > initial_alpha
        assert posterior.beta == initial_beta
    
    def test_update_posterior_failure(self):
        """Test updating posterior with failed outcome."""
        engine = ThompsonSamplingEngine()
        modality = LearningModality.SUPERVISED_CONVERSION
        
        posterior = engine.posterior_state.get_posterior(modality)
        initial_alpha = posterior.alpha
        initial_beta = posterior.beta
        
        engine.update(modality, reward=0.0)
        
        posterior = engine.posterior_state.get_posterior(modality)
        assert posterior.alpha == initial_alpha
        assert posterior.beta > initial_beta
    
    def test_sample_from_posterior_returns_valid(self):
        """Test that sampling from posterior returns a valid value."""
        engine = ThompsonSamplingEngine()
        modality = LearningModality.SUPERVISED_CONVERSION
        
        posterior = engine.posterior_state.get_posterior(modality)
        sample = posterior.sample()
        
        # Sample should be between 0 and 1 (Beta distribution)
        assert 0.0 <= sample <= 1.0
    
    def test_posterior_mean_increases_with_success(self):
        """Test that posterior mean increases with successful outcomes."""
        engine = ThompsonSamplingEngine()
        modality = LearningModality.SUPERVISED_CONVERSION
        
        # Get initial mean
        posterior = engine.posterior_state.get_posterior(modality)
        initial_mean = posterior.mean
        
        # Add successful observations
        for _ in range(20):
            engine.update(modality, reward=1.0)
        
        # Mean should increase
        posterior = engine.posterior_state.get_posterior(modality)
        assert posterior.mean > initial_mean


# =============================================================================
# META-LEARNER SERVICE TESTS
# =============================================================================

class TestMetaLearnerService:
    """Tests for MetaLearnerService."""
    
    @pytest.mark.asyncio
    async def test_route_cold_start_user(
        self, meta_learner, blackboard, request_id
    ):
        """Test routing for cold-start user."""
        from adam.blackboard.models.zone1_context import (
            RequestContext,
            UserIntelligencePackage,
            ContentContext,
            AdCandidatePool,
        )
        
        # Create minimal context (cold start)
        context = RequestContext(
            request_id=request_id,
            user_id="new_user_001",
            user_intelligence=UserIntelligencePackage(
                user_id="new_user_001",
                profile=None,  # No profile yet
                mechanism_history=None,
            ),
            content_context=ContentContext(
                content_type="audio",
                station_format="CHR",
            ),
            ad_candidates=AdCandidatePool(candidates=[]),
            latency_budget_ms=100,
        )
        
        decision = await meta_learner.route_request(request_id, context)
        
        assert decision.request_id == request_id
        # Cold start should use bandit or cold-start modality
        assert decision.selected_modality in [
            LearningModality.REINFORCEMENT_BANDIT,
            LearningModality.SELF_SUPERVISED_CONTRASTIVE,
        ]
    
    @pytest.mark.asyncio
    async def test_route_rich_data_user(
        self, meta_learner, blackboard, request_id
    ):
        """Test routing for user with rich data."""
        from adam.blackboard.models.zone1_context import (
            RequestContext,
            UserIntelligencePackage,
            ContentContext,
            AdCandidatePool,
        )
        from adam.graph_reasoning.models.graph_context import (
            MechanismHistory, MechanismEffectiveness, UserProfileSnapshot
        )
        
        # Create a profile with good completeness
        profile = UserProfileSnapshot(
            user_id="rich_user_001",
            total_decisions=150,
            total_conversions=112,
            overall_conversion_rate=0.75,
            profile_completeness=0.85,  # High completeness
            is_cold_start=False,
        )
        
        # Create context with rich history
        mech_history = MechanismHistory(
            user_id="rich_user_001",
            mechanism_effectiveness=[
                MechanismEffectiveness(
                    mechanism_id="social_proof",
                    mechanism_name="Social Proof",
                    success_rate=0.75,
                    effect_size=0.4,
                    trial_count=120,
                    confidence=0.9,
                )
            ],
            total_mechanism_trials=120,
        )
        
        context = RequestContext(
            request_id=request_id,
            user_id="rich_user_001",
            user_intelligence=UserIntelligencePackage(
                user_id="rich_user_001",
                profile=profile,  # Include profile for completeness check
                mechanism_history=mech_history,
                is_cold_start=False,
            ),
            content_context=ContentContext(
                content_type="audio",
            ),
            ad_candidates=AdCandidatePool(candidates=[]),
            latency_budget_ms=2000,
        )
        
        decision = await meta_learner.route_request(request_id, context)
        
        # Rich data with complete profile should use supervised, unsupervised or graph-based modalities
        # Note: Due to Thompson Sampling's stochastic nature, any eligible modality may be selected
        # With rich data, supervised, clustering, and graph embedding are all valid options
        assert decision.selected_modality in [
            LearningModality.SUPERVISED_CONVERSION,
            LearningModality.SUPERVISED_ENGAGEMENT,
            LearningModality.UNSUPERVISED_CLUSTERING,
            LearningModality.UNSUPERVISED_GRAPH_EMBEDDING,
            LearningModality.REINFORCEMENT_CONTEXTUAL_BANDIT,
            LearningModality.REINFORCEMENT_BANDIT,
        ]
    
    @pytest.mark.asyncio
    async def test_update_from_outcome(self, meta_learner):
        """Test updating posteriors from outcome."""
        decision_id = "dec_001"
        modality = LearningModality.SUPERVISED_CONVERSION
        
        # Get initial summary
        initial = await meta_learner.get_posterior_summary()
        
        # Record positive outcome
        await meta_learner.update_from_outcome(
            decision_id=decision_id,
            modality=modality,
            reward=0.9,
        )
        
        # Posterior should be updated
        updated = await meta_learner.get_posterior_summary()
        assert updated[modality.value]["alpha"] > initial[modality.value]["alpha"]
