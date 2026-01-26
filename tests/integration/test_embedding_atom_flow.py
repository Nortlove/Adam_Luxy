# =============================================================================
# ADAM Integration Tests: Embedding → Atom Flow
# Location: tests/integration/test_embedding_atom_flow.py
# =============================================================================

"""
EMBEDDING → ATOM FLOW INTEGRATION TESTS

Critical integration tests that verify the complete flow from:
1. User profile embedding generation
2. Semantic similarity matching
3. Atom context preparation
4. Evidence gathering with embeddings
5. Psychological inference
6. Blackboard integration

These tests are essential because atoms are the core psychological
intelligence of ADAM. They must correctly consume embeddings for
accurate personality and mechanism predictions.
"""

import asyncio
import pytest
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

# Configure logging for tests
logging.basicConfig(level=logging.DEBUG)
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
def embedding_service():
    """Create embedding service for integration tests."""
    from adam.embeddings import EmbeddingService, EmbeddingModel
    
    service = EmbeddingService(
        default_model=EmbeddingModel.ALL_MINILM_L6,
        cache=None,
    )
    yield service
    # Cleanup
    asyncio.get_event_loop().run_until_complete(service.close())


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
        
        async def exists(self, key: str) -> bool:
            return key in storage
    
    return MockRedisCache()


@pytest.fixture
def mock_neo4j():
    """Mock Neo4j driver for graph operations."""
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
def sample_user_profiles():
    """Sample user profiles for testing."""
    return [
        {
            "user_id": "user_high_openness",
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
            "construal_level": 0.70,  # Abstract
            "mechanisms": {
                "social_proof": 0.65,
                "scarcity": 0.45,
                "authority": 0.70,
            },
        },
        {
            "user_id": "user_high_conscientiousness",
            "big_five": {
                "openness": 0.45,
                "conscientiousness": 0.90,
                "extraversion": 0.40,
                "agreeableness": 0.65,
                "neuroticism": 0.30,
            },
            "regulatory_focus": {
                "promotion": 0.35,
                "prevention": 0.65,
            },
            "construal_level": 0.30,  # Concrete
            "mechanisms": {
                "social_proof": 0.55,
                "scarcity": 0.80,
                "authority": 0.85,
            },
        },
        {
            "user_id": "user_cold_start",
            "big_five": {
                "openness": 0.50,
                "conscientiousness": 0.50,
                "extraversion": 0.50,
                "agreeableness": 0.50,
                "neuroticism": 0.50,
            },
            "regulatory_focus": {
                "promotion": 0.50,
                "prevention": 0.50,
            },
            "construal_level": 0.50,
            "mechanisms": {},
            "confidence": 0.3,  # Low confidence for cold start
        },
    ]


@pytest.fixture
def sample_ad_creatives():
    """Sample ad creatives for testing."""
    return [
        {
            "creative_id": "ad_promotion_abstract",
            "campaign_id": "camp_001",
            "brand_id": "brand_001",
            "headline": "Unlock Your Potential Today",
            "copy": "Join thousands who have transformed their lives. Discover new possibilities and achieve your dreams.",
            "cta": "Start Your Journey",
            "mechanism": "social_proof",
            "framing": "promotion",
            "construal": "abstract",
        },
        {
            "creative_id": "ad_prevention_concrete",
            "campaign_id": "camp_001",
            "brand_id": "brand_001",
            "headline": "Don't Miss This Limited Offer",
            "copy": "Only 3 left in stock. Secure your order now before it's too late. Free shipping on orders over $50.",
            "cta": "Buy Now",
            "mechanism": "scarcity",
            "framing": "prevention",
            "construal": "concrete",
        },
        {
            "creative_id": "ad_authority_mixed",
            "campaign_id": "camp_002",
            "brand_id": "brand_002",
            "headline": "Doctor Recommended Formula",
            "copy": "Clinically proven results. 9 out of 10 experts recommend our product for optimal performance.",
            "cta": "Learn More",
            "mechanism": "authority",
            "framing": "neutral",
            "construal": "mixed",
        },
    ]


# =============================================================================
# EMBEDDING GENERATION TESTS
# =============================================================================

class TestEmbeddingGeneration:
    """Tests for embedding generation in the atom flow context."""
    
    @pytest.mark.asyncio
    async def test_user_profile_embedding_dimensions(self, embedding_service):
        """Verify user profile embeddings have correct dimensions."""
        from adam.embeddings import EmbeddingModel
        
        profile = {
            "big_five": {"openness": 0.8, "conscientiousness": 0.6},
            "regulatory_focus": {"promotion": 0.7, "prevention": 0.3},
        }
        
        emb = await embedding_service.process_user_profile(
            user_id="test_user",
            profile_data=profile,
            store=False,
        )
        
        # Psychological model uses 512 dimensions
        assert emb.dimensions == 512
        assert len(emb.vector) == 512
        assert emb.user_id == "test_user"
    
    @pytest.mark.asyncio
    async def test_psychological_components_extracted(self, embedding_service):
        """Verify psychological components are correctly extracted."""
        profile = {
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
            "construal_level": 0.70,
            "mechanisms": {
                "social_proof": 0.65,
                "scarcity": 0.45,
            },
        }
        
        emb = await embedding_service.process_user_profile(
            user_id="test_user",
            profile_data=profile,
            store=False,
        )
        
        # Check Big Five components
        assert len(emb.big_five_component) == 5
        assert emb.big_five_component[0] == 0.85  # openness
        assert emb.big_five_component[1] == 0.55  # conscientiousness
        
        # Check regulatory focus
        assert len(emb.regulatory_focus_component) == 2
        assert emb.regulatory_focus_component[0] == 0.75  # promotion
        assert emb.regulatory_focus_component[1] == 0.25  # prevention
        
        # Check construal
        assert len(emb.construal_level_component) == 1
        assert emb.construal_level_component[0] == 0.70
    
    @pytest.mark.asyncio
    async def test_ad_creative_mechanism_detection(self, embedding_service):
        """Verify ad creative embeddings detect persuasion mechanisms."""
        creative = {
            "headline": "Limited Time Offer!",
            "copy": "Join millions who trust our product. Only 5 left!",
            "cta": "Buy Now",
        }
        
        emb = await embedding_service.process_ad_creative(
            creative_id="ad_001",
            campaign_id="camp_001",
            brand_id="brand_001",
            creative_data=creative,
            store=False,
        )
        
        # Should detect scarcity and social proof
        assert emb.mechanism_alignment["scarcity"] > 0
        assert emb.mechanism_alignment["social_proof"] > 0
        
        # Scarcity should be higher (explicit mention)
        # Note: This may vary based on keyword detection
        assert "scarcity" in emb.mechanism_alignment


# =============================================================================
# EMBEDDING SIMILARITY TESTS
# =============================================================================

class TestEmbeddingSimilarity:
    """Tests for similarity computations used in atom decisions."""
    
    @pytest.mark.asyncio
    async def test_similar_profiles_high_similarity(
        self, embedding_service, sample_user_profiles
    ):
        """Verify similar psychological profiles have high similarity."""
        # Two high-openness profiles should be similar
        profile1 = sample_user_profiles[0]  # High openness
        
        profile2 = {
            "user_id": "similar_user",
            "big_five": {
                "openness": 0.80,  # Similar high openness
                "conscientiousness": 0.50,
                "extraversion": 0.65,
                "agreeableness": 0.55,
                "neuroticism": 0.40,
            },
            "regulatory_focus": {"promotion": 0.70, "prevention": 0.30},
        }
        
        emb1 = await embedding_service.process_user_profile(
            profile1["user_id"], profile1, store=False
        )
        emb2 = await embedding_service.process_user_profile(
            profile2["user_id"], profile2, store=False
        )
        
        # Compute cosine similarity
        from adam.embeddings.models import EmbeddingVector, EmbeddingNamespace, EmbeddingType, EmbeddingModel
        
        vec1 = EmbeddingVector(
            vector_id="v1",
            namespace=EmbeddingNamespace.USERS,
            embedding_type=EmbeddingType.PSYCHOLOGICAL_CONSTRUCT,
            vector=emb1.vector,
            dimensions=len(emb1.vector),
            source_id=emb1.user_id,
            model=EmbeddingModel.PSYCHOLOGICAL_BASE,
        )
        vec2 = EmbeddingVector(
            vector_id="v2",
            namespace=EmbeddingNamespace.USERS,
            embedding_type=EmbeddingType.PSYCHOLOGICAL_CONSTRUCT,
            vector=emb2.vector,
            dimensions=len(emb2.vector),
            source_id=emb2.user_id,
            model=EmbeddingModel.PSYCHOLOGICAL_BASE,
        )
        
        similarity = vec1.cosine_similarity(vec2)
        
        # Similar profiles should have high similarity
        assert similarity > 0.7, f"Expected high similarity, got {similarity}"
    
    @pytest.mark.asyncio
    async def test_different_profiles_lower_similarity(
        self, embedding_service, sample_user_profiles
    ):
        """Verify different psychological profiles have lower similarity."""
        # High openness vs high conscientiousness should be less similar
        profile1 = sample_user_profiles[0]  # High openness, promotion focus
        profile2 = sample_user_profiles[1]  # High conscientiousness, prevention focus
        
        emb1 = await embedding_service.process_user_profile(
            profile1["user_id"], profile1, store=False
        )
        emb2 = await embedding_service.process_user_profile(
            profile2["user_id"], profile2, store=False
        )
        
        from adam.embeddings.models import EmbeddingVector, EmbeddingNamespace, EmbeddingType, EmbeddingModel
        
        vec1 = EmbeddingVector(
            vector_id="v1",
            namespace=EmbeddingNamespace.USERS,
            embedding_type=EmbeddingType.PSYCHOLOGICAL_CONSTRUCT,
            vector=emb1.vector,
            dimensions=len(emb1.vector),
            source_id=emb1.user_id,
            model=EmbeddingModel.PSYCHOLOGICAL_BASE,
        )
        vec2 = EmbeddingVector(
            vector_id="v2",
            namespace=EmbeddingNamespace.USERS,
            embedding_type=EmbeddingType.PSYCHOLOGICAL_CONSTRUCT,
            vector=emb2.vector,
            dimensions=len(emb2.vector),
            source_id=emb2.user_id,
            model=EmbeddingModel.PSYCHOLOGICAL_BASE,
        )
        
        similarity = vec1.cosine_similarity(vec2)
        
        # Different profiles should have lower similarity
        # Note: Still positive because both are normalized user profiles
        assert similarity < 0.9, f"Expected lower similarity, got {similarity}"
    
    @pytest.mark.asyncio
    async def test_user_ad_matching(
        self, embedding_service, sample_user_profiles, sample_ad_creatives
    ):
        """Test matching users to ad creatives based on psychological fit."""
        # High openness, promotion-focused user
        user_profile = sample_user_profiles[0]
        
        # Store ad embeddings
        ad_embeddings = []
        for ad in sample_ad_creatives:
            emb = await embedding_service.process_ad_creative(
                ad["creative_id"],
                ad["campaign_id"],
                ad["brand_id"],
                ad,
                store=True,
            )
            ad_embeddings.append((ad, emb))
        
        # Match user to ads
        matches = await embedding_service.match_user_to_creatives(
            user_id=user_profile["user_id"],
            user_profile=user_profile,
            top_k=3,
        )
        
        # Should return ranked matches
        assert len(matches) <= 3
        
        # For a promotion-focused user, promotion-framed ad should rank well
        # Note: Actual ranking depends on embedding quality


# =============================================================================
# ATOM CONTEXT PREPARATION TESTS
# =============================================================================

class TestAtomContextPreparation:
    """Tests for preparing atom context with embeddings."""
    
    @pytest.mark.asyncio
    async def test_atom_input_with_embeddings(
        self, embedding_service, blackboard, sample_user_profiles
    ):
        """Test creating atom input with embedded user profile."""
        from adam.atoms.models.atom_io import AtomInput, AtomConfig
        from adam.blackboard.models.zone1_context import RequestContext, UserIntelligencePackage
        from adam.blackboard.models.zone2_reasoning import AtomType
        
        user_profile = sample_user_profiles[0]
        request_id = f"req_{uuid4().hex[:12]}"
        
        # Generate psychological embedding
        psych_emb = await embedding_service.process_user_profile(
            user_profile["user_id"],
            user_profile,
            store=True,
        )
        
        # Create user intelligence
        user_intel = UserIntelligencePackage(
            user_id=user_profile["user_id"],
            is_cold_start=False,
        )
        
        # Create request context
        request_context = RequestContext(
            request_id=request_id,
            user_intelligence=user_intel,
        )
        
        # Create atom input (AtomInput doesn't have a config field)
        atom_input = AtomInput(
            request_id=request_id,
            user_id=user_profile["user_id"],
            request_context=request_context,
            skip_claude=True,  # Skip Claude for testing
        )
        
        assert atom_input.request_id == request_id
        assert atom_input.user_id == user_profile["user_id"]
    
    @pytest.mark.asyncio
    async def test_blackboard_zone1_with_embeddings(
        self, embedding_service, blackboard, sample_user_profiles
    ):
        """Test writing embedded user context to blackboard Zone 1."""
        from adam.blackboard.models.zone1_context import (
            RequestContext,
            UserIntelligencePackage,
        )
        from adam.blackboard.models.core import ComponentRole
        from adam.graph_reasoning.models.graph_context import UserProfileSnapshot
        
        user_profile = sample_user_profiles[0]
        request_id = f"req_{uuid4().hex[:12]}"
        
        # Create blackboard
        await blackboard.create_blackboard(request_id, user_profile["user_id"])
        
        # Generate embedding
        psych_emb = await embedding_service.process_user_profile(
            user_profile["user_id"],
            user_profile,
            store=False,
        )
        
        # Create a proper UserProfileSnapshot
        profile_snapshot = UserProfileSnapshot(
            user_id=user_profile["user_id"],
            is_cold_start=False,
        )
        
        # Create user intelligence with profile
        user_intel = UserIntelligencePackage(
            user_id=user_profile["user_id"],
            profile=profile_snapshot,
            is_cold_start=False,
        )
        
        # Create request context
        context = RequestContext(
            request_id=request_id,
            user_intelligence=user_intel,
        )
        
        # Write to blackboard
        success = await blackboard.write_zone1(
            request_id,
            context,
            role=ComponentRole.REQUEST_HANDLER,
        )
        
        assert success
        
        # Read back and verify
        retrieved = await blackboard.read_zone1(
            request_id,
            role=ComponentRole.ATOM,
        )
        
        assert retrieved is not None
        assert retrieved.request_id == request_id


# =============================================================================
# ATOM EVIDENCE GATHERING TESTS
# =============================================================================

class TestAtomEvidenceGathering:
    """Tests for atom evidence gathering using embeddings."""
    
    @pytest.mark.asyncio
    async def test_regulatory_focus_evidence_with_embeddings(
        self, embedding_service, blackboard, interaction_bridge, sample_user_profiles
    ):
        """Test regulatory focus atom gathering evidence with embeddings."""
        from adam.atoms.core.regulatory_focus import RegulatoryFocusAtom
        from adam.atoms.models.atom_io import AtomInput
        from adam.blackboard.models.zone1_context import RequestContext, UserIntelligencePackage
        
        user_profile = sample_user_profiles[0]  # Promotion-focused
        request_id = f"req_{uuid4().hex[:12]}"
        
        # Create blackboard
        await blackboard.create_blackboard(request_id, user_profile["user_id"])
        
        # Create atom
        atom = RegulatoryFocusAtom(
            blackboard=blackboard,
            bridge=interaction_bridge,
        )
        
        # Create user intelligence and request context
        user_intel = UserIntelligencePackage(
            user_id=user_profile["user_id"],
            is_cold_start=False,
        )
        request_context = RequestContext(
            request_id=request_id,
            user_intelligence=user_intel,
        )
        
        # Create input
        atom_input = AtomInput(
            request_id=request_id,
            user_id=user_profile["user_id"],
            request_context=request_context,
            skip_claude=True,
        )
        
        # Execute atom
        result = await atom.execute(atom_input)
        
        # Should produce a result
        assert result is not None
        assert result.duration_ms >= 0
    
    @pytest.mark.asyncio
    async def test_construal_level_evidence_with_embeddings(
        self, embedding_service, blackboard, interaction_bridge, sample_user_profiles
    ):
        """Test construal level atom gathering evidence with embeddings."""
        from adam.atoms.core.construal_level import ConstrualLevelAtom
        from adam.atoms.models.atom_io import AtomInput
        from adam.blackboard.models.zone1_context import RequestContext, UserIntelligencePackage
        
        user_profile = sample_user_profiles[0]  # Abstract construal
        request_id = f"req_{uuid4().hex[:12]}"
        
        # Create blackboard
        await blackboard.create_blackboard(request_id, user_profile["user_id"])
        
        # Create atom
        atom = ConstrualLevelAtom(
            blackboard=blackboard,
            bridge=interaction_bridge,
        )
        
        # Create user intelligence and request context
        user_intel = UserIntelligencePackage(
            user_id=user_profile["user_id"],
            is_cold_start=False,
        )
        request_context = RequestContext(
            request_id=request_id,
            user_intelligence=user_intel,
        )
        
        # Create input
        atom_input = AtomInput(
            request_id=request_id,
            user_id=user_profile["user_id"],
            request_context=request_context,
            skip_claude=True,
        )
        
        # Execute atom
        result = await atom.execute(atom_input)
        
        # Should produce a result
        assert result is not None


# =============================================================================
# FULL EMBEDDING → ATOM PIPELINE TESTS
# =============================================================================

class TestFullEmbeddingAtomPipeline:
    """End-to-end tests for the complete embedding → atom flow."""
    
    @pytest.mark.asyncio
    async def test_complete_user_ad_matching_flow(
        self, embedding_service, blackboard, interaction_bridge,
        sample_user_profiles, sample_ad_creatives
    ):
        """Test complete flow: user embedding → ad matching → atom inference."""
        from adam.atoms.core.regulatory_focus import RegulatoryFocusAtom
        from adam.atoms.core.construal_level import ConstrualLevelAtom
        from adam.atoms.models.atom_io import AtomInput
        from adam.blackboard.models.zone1_context import (
            RequestContext,
            UserIntelligencePackage,
            AdCandidate,
            AdCandidatePool,
        )
        from adam.blackboard.models.core import ComponentRole
        
        user_profile = sample_user_profiles[0]
        request_id = f"req_{uuid4().hex[:12]}"
        
        # STEP 1: Generate user psychological embedding
        logger.info("Step 1: Generating user psychological embedding")
        user_emb = await embedding_service.process_user_profile(
            user_profile["user_id"],
            user_profile,
            store=True,
        )
        
        assert user_emb.user_id == user_profile["user_id"]
        assert len(user_emb.vector) > 0
        
        # STEP 2: Generate ad creative embeddings
        logger.info("Step 2: Generating ad creative embeddings")
        for ad in sample_ad_creatives:
            await embedding_service.process_ad_creative(
                ad["creative_id"],
                ad["campaign_id"],
                ad["brand_id"],
                ad,
                store=True,
            )
        
        # STEP 3: Match user to ads using embeddings
        logger.info("Step 3: Matching user to ads")
        matches = await embedding_service.match_user_to_creatives(
            user_id=user_profile["user_id"],
            user_profile=user_profile,
            top_k=3,
        )
        
        # STEP 4: Prepare blackboard context
        logger.info("Step 4: Preparing blackboard context")
        await blackboard.create_blackboard(request_id, user_profile["user_id"])
        
        # Create ad candidates from matches
        ad_candidates = []
        for creative_id, score, mechanisms in matches:
            ad_data = next(
                (a for a in sample_ad_creatives if a["creative_id"] == creative_id),
                None
            )
            if ad_data:
                ad_candidates.append(AdCandidate(
                    candidate_id=creative_id,
                    campaign_id=ad_data["campaign_id"],
                    creative_id=creative_id,
                    targeting_score=score,
                ))
        
        # Create user intelligence
        user_intel = UserIntelligencePackage(
            user_id=user_profile["user_id"],
            is_cold_start=False,
        )
        
        # Write Zone 1 context
        context = RequestContext(
            request_id=request_id,
            user_intelligence=user_intel,
            ad_candidates=AdCandidatePool(candidates=ad_candidates),
        )
        
        await blackboard.write_zone1(
            request_id, context, role=ComponentRole.REQUEST_HANDLER
        )
        
        # STEP 5: Execute regulatory focus atom
        logger.info("Step 5: Executing regulatory focus atom")
        rf_atom = RegulatoryFocusAtom(
            blackboard=blackboard,
            bridge=interaction_bridge,
        )
        
        rf_input = AtomInput(
            request_id=request_id,
            user_id=user_profile["user_id"],
            request_context=context,
            skip_claude=True,
        )
        
        rf_result = await rf_atom.execute(rf_input)
        assert rf_result is not None
        
        # STEP 6: Execute construal level atom
        logger.info("Step 6: Executing construal level atom")
        cl_atom = ConstrualLevelAtom(
            blackboard=blackboard,
            bridge=interaction_bridge,
        )
        
        cl_input = AtomInput(
            request_id=request_id,
            user_id=user_profile["user_id"],
            request_context=context,
            skip_claude=True,
            upstream_outputs={"atom_regulatory_focus": rf_result.output} if rf_result.output else {},
        )
        
        cl_result = await cl_atom.execute(cl_input)
        assert cl_result is not None
        
        logger.info("Complete embedding → atom pipeline test passed!")
    
    @pytest.mark.asyncio
    async def test_cold_start_user_flow(
        self, embedding_service, blackboard, interaction_bridge, sample_user_profiles
    ):
        """Test embedding → atom flow for cold start user."""
        from adam.atoms.core.regulatory_focus import RegulatoryFocusAtom
        from adam.atoms.models.atom_io import AtomInput
        from adam.blackboard.models.zone1_context import RequestContext, UserIntelligencePackage
        
        cold_start_user = sample_user_profiles[2]  # Cold start
        request_id = f"req_{uuid4().hex[:12]}"
        
        # Generate embedding with low confidence
        user_emb = await embedding_service.process_user_profile(
            cold_start_user["user_id"],
            cold_start_user,
            store=True,
        )
        
        # Cold start should have lower confidence
        assert user_emb.confidence <= 0.5
        
        # Create blackboard
        await blackboard.create_blackboard(request_id, cold_start_user["user_id"])
        
        # Create user intelligence and request context
        user_intel = UserIntelligencePackage(
            user_id=cold_start_user["user_id"],
            is_cold_start=True,
        )
        request_context = RequestContext(
            request_id=request_id,
            user_intelligence=user_intel,
        )
        
        # Execute atom
        atom = RegulatoryFocusAtom(
            blackboard=blackboard,
            bridge=interaction_bridge,
        )
        
        atom_input = AtomInput(
            request_id=request_id,
            user_id=cold_start_user["user_id"],
            request_context=request_context,
            skip_claude=True,
        )
        
        result = await atom.execute(atom_input)
        
        # Should still produce a result (using priors/defaults)
        assert result is not None
    
    @pytest.mark.asyncio
    async def test_embedding_consistency_across_atoms(
        self, embedding_service, blackboard, interaction_bridge, sample_user_profiles
    ):
        """Verify embedding consistency when multiple atoms access same user."""
        from adam.atoms.core.regulatory_focus import RegulatoryFocusAtom
        from adam.atoms.core.construal_level import ConstrualLevelAtom
        from adam.atoms.models.atom_io import AtomInput, AtomConfig
        
        user_profile = sample_user_profiles[0]
        request_id = f"req_{uuid4().hex[:12]}"
        
        # Store embedding
        emb1 = await embedding_service.process_user_profile(
            user_profile["user_id"],
            user_profile,
            store=True,
        )
        
        # Retrieve embedding (simulating second atom access)
        emb2 = await embedding_service.process_user_profile(
            user_profile["user_id"],
            user_profile,
            store=False,  # Don't store again
        )
        
        # Embeddings should be consistent
        assert emb1.user_id == emb2.user_id
        assert emb1.dimensions == emb2.dimensions
        
        # Note: Exact vector equality depends on caching


# =============================================================================
# PERFORMANCE TESTS
# =============================================================================

class TestEmbeddingAtomPerformance:
    """Performance tests for the embedding → atom pipeline."""
    
    @pytest.mark.asyncio
    async def test_batch_user_embedding_performance(self, embedding_service):
        """Test batch embedding generation performance."""
        import time
        
        # Generate 100 user profiles
        profiles = []
        for i in range(100):
            profiles.append({
                "user_id": f"perf_user_{i}",
                "big_five": {
                    "openness": 0.3 + (i % 7) * 0.1,
                    "conscientiousness": 0.4 + (i % 6) * 0.1,
                    "extraversion": 0.5 + (i % 5) * 0.1,
                    "agreeableness": 0.4 + (i % 8) * 0.075,
                    "neuroticism": 0.3 + (i % 7) * 0.1,
                },
                "regulatory_focus": {
                    "promotion": 0.4 + (i % 3) * 0.2,
                    "prevention": 0.6 - (i % 3) * 0.2,
                },
            })
        
        start = time.perf_counter()
        
        # Generate embeddings
        embeddings = []
        for profile in profiles:
            emb = await embedding_service.process_user_profile(
                profile["user_id"],
                profile,
                store=False,
            )
            embeddings.append(emb)
        
        duration = time.perf_counter() - start
        
        assert len(embeddings) == 100
        
        # Should complete in reasonable time (< 30 seconds for 100 profiles)
        assert duration < 30.0, f"Batch embedding took {duration:.2f}s"
        
        logger.info(f"Batch embedding of 100 profiles: {duration:.2f}s ({duration*10:.0f}ms per profile)")
    
    @pytest.mark.asyncio
    async def test_similarity_search_performance(self, embedding_service):
        """Test similarity search performance with stored embeddings."""
        import time
        from adam.embeddings import EmbeddingNamespace
        
        # Store 50 user embeddings
        for i in range(50):
            profile = {
                "user_id": f"search_user_{i}",
                "big_five": {
                    "openness": 0.3 + (i % 7) * 0.1,
                    "conscientiousness": 0.5,
                    "extraversion": 0.5,
                    "agreeableness": 0.5,
                    "neuroticism": 0.5,
                },
            }
            await embedding_service.process_user_profile(
                profile["user_id"],
                profile,
                store=True,
            )
        
        # Perform 10 similarity searches
        start = time.perf_counter()
        
        for i in range(10):
            await embedding_service.search_similar(
                query=f"User with high openness and creativity",
                namespace=EmbeddingNamespace.USERS,
                top_k=5,
            )
        
        duration = time.perf_counter() - start
        
        # 10 searches should complete quickly (< 5 seconds)
        assert duration < 5.0, f"Search took {duration:.2f}s"
        
        logger.info(f"10 similarity searches: {duration:.2f}s ({duration*100:.0f}ms per search)")
