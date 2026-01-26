# =============================================================================
# ADAM Test Configuration
# Location: tests/conftest.py
# =============================================================================

"""
PYTEST CONFIGURATION

Central test fixtures shared across all test modules.

Fixture Categories:
1. Infrastructure - Mock Redis, Neo4j, Kafka
2. Core Services - Blackboard, Meta-Learner, Gradient Bridge
3. Atoms - Base fixtures for atom testing
4. Platform - iHeart, WPP test contexts
5. User Data - Sample user profiles, signals

Usage:
    def test_decision_flow(blackboard, meta_learner, atom_dag):
        # All services injected as fixtures
        pass
"""

import asyncio
import pytest
from datetime import datetime, timezone
from typing import Any, Dict, Generator, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

# =============================================================================
# PYTEST CONFIGURATION
# =============================================================================

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# =============================================================================
# 1. INFRASTRUCTURE FIXTURES
# =============================================================================

@pytest.fixture
def mock_redis():
    """
    Mock Redis cache for testing without real Redis.
    
    Provides in-memory storage that mimics ADAMRedisCache behavior.
    """
    storage: Dict[str, Any] = {}
    
    class MockRedisCache:
        async def get(self, key: str, model_type=None) -> Optional[Any]:
            data = storage.get(key)
            if data and model_type:
                try:
                    return model_type(**data) if isinstance(data, dict) else data
                except Exception:
                    return data
            return data
        
        async def set(
            self,
            key: str,
            value: Any,
            ttl: int = 3600,
            domain=None,
        ) -> bool:
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
        
        async def count_pattern(self, pattern: str) -> int:
            import fnmatch
            count = 0
            for key in storage:
                if fnmatch.fnmatch(key, pattern.replace("*", "**")):
                    count += 1
            return count
        
        def clear(self):
            storage.clear()
    
    return MockRedisCache()


@pytest.fixture
def mock_neo4j():
    """
    Mock Neo4j driver for testing without real database.
    
    Provides minimal graph operations for testing.
    """
    nodes: Dict[str, Dict] = {}
    relationships: List[Dict] = []
    
    class MockSession:
        async def run(self, query: str, **params) -> "MockResult":
            return MockResult([])
        
        async def close(self):
            pass
        
        async def __aenter__(self):
            return self
        
        async def __aexit__(self, *args):
            await self.close()
    
    class MockResult:
        def __init__(self, records: List[Dict]):
            self._records = records
        
        async def single(self) -> Optional[Dict]:
            return self._records[0] if self._records else None
        
        async def data(self) -> List[Dict]:
            return self._records
        
        def __aiter__(self):
            return iter(self._records)
    
    class MockDriver:
        def session(self, **kwargs) -> MockSession:
            return MockSession()
        
        async def close(self):
            pass
        
        def add_node(self, node_id: str, labels: List[str], properties: Dict):
            nodes[node_id] = {"labels": labels, "properties": properties}
        
        def add_relationship(
            self, start_id: str, end_id: str, rel_type: str, properties: Dict = None
        ):
            relationships.append({
                "start": start_id,
                "end": end_id,
                "type": rel_type,
                "properties": properties or {},
            })
    
    return MockDriver()


@pytest.fixture
def mock_kafka():
    """
    Mock Kafka producer for testing without real Kafka.
    
    Captures all sent messages for verification.
    """
    messages: List[Dict] = []
    
    class MockKafkaProducer:
        is_connected = True
        
        async def start(self):
            pass
        
        async def stop(self):
            pass
        
        async def send(
            self,
            topic,
            value: Dict,
            key: str = None,
            headers: Dict = None,
        ) -> bool:
            messages.append({
                "topic": topic.value if hasattr(topic, "value") else topic,
                "value": value,
                "key": key,
                "headers": headers,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
            return True
        
        async def send_event(self, topic, event, key=None) -> bool:
            return await self.send(
                topic,
                event.model_dump() if hasattr(event, "model_dump") else event,
                key,
            )
        
        async def emit_learning_signal(self, **kwargs) -> bool:
            messages.append({"type": "learning_signal", **kwargs})
            return True
        
        def get_messages(self, topic: str = None) -> List[Dict]:
            if topic:
                return [m for m in messages if m.get("topic") == topic]
            return messages
        
        def clear(self):
            messages.clear()
    
    return MockKafkaProducer()


# =============================================================================
# 2. CORE SERVICE FIXTURES
# =============================================================================

@pytest.fixture
def blackboard(mock_redis):
    """Blackboard service with mocked Redis."""
    from adam.blackboard.service import BlackboardService
    
    # Patch Kafka producer to avoid connection
    with patch("adam.blackboard.service.get_kafka_producer", return_value=None):
        service = BlackboardService(redis_cache=mock_redis)
        yield service


@pytest.fixture
def meta_learner(blackboard, mock_redis):
    """Meta-learner service with dependencies."""
    from adam.meta_learner.service import MetaLearnerService
    
    service = MetaLearnerService(
        blackboard=blackboard,
        cache=mock_redis,
    )
    yield service


@pytest.fixture
def gradient_bridge(blackboard, mock_redis, interaction_bridge):
    """Gradient bridge service with dependencies."""
    from adam.gradient_bridge.service import GradientBridgeService
    
    with patch("adam.gradient_bridge.service.get_kafka_producer", return_value=None):
        service = GradientBridgeService(
            blackboard=blackboard,
            bridge=interaction_bridge,
            cache=mock_redis,
        )
        yield service


@pytest.fixture
def interaction_bridge(mock_neo4j, mock_redis):
    """Interaction bridge for graph operations."""
    from adam.graph_reasoning.bridge import InteractionBridge
    
    bridge = InteractionBridge(
        neo4j_driver=mock_neo4j,
        redis_cache=mock_redis,
    )
    yield bridge


@pytest.fixture
def verification_service(blackboard, mock_neo4j):
    """Verification service."""
    from adam.verification.service import VerificationService
    
    service = VerificationService(
        blackboard=blackboard,
        neo4j_driver=mock_neo4j,
    )
    yield service


# =============================================================================
# 3. ATOM FIXTURES
# =============================================================================

@pytest.fixture
def user_intelligence_factory():
    """Factory for creating UserIntelligencePackage instances."""
    from adam.blackboard.models.zone1_context import UserIntelligencePackage
    
    def create_intelligence(user_id: str = "test_user_001", **kwargs) -> UserIntelligencePackage:
        return UserIntelligencePackage(
            user_id=user_id,
            is_cold_start=kwargs.get("is_cold_start", True),
            cold_start_tier=kwargs.get("cold_start_tier", "full"),
            sources_available=kwargs.get("sources_available", ["test"]),
        )
    
    return create_intelligence


@pytest.fixture
def request_context_factory(user_intelligence_factory):
    """Factory for creating RequestContext instances."""
    from adam.blackboard.models.zone1_context import RequestContext
    
    def create_context(
        request_id: str = None,
        user_id: str = "test_user_001",
        **kwargs,
    ) -> RequestContext:
        req_id = request_id or f"req_{uuid4().hex[:12]}"
        user_intel = kwargs.pop("user_intelligence", None) or user_intelligence_factory(user_id)
        
        return RequestContext(
            request_id=req_id,
            user_intelligence=user_intel,
            platform=kwargs.get("platform", "test"),
            latency_budget_ms=kwargs.get("latency_budget_ms", 500),
            debug_mode=kwargs.get("debug_mode", False),
        )
    
    return create_context


@pytest.fixture
def atom_config_factory():
    """Factory for creating AtomConfig instances."""
    from adam.atoms.models.atom_io import AtomConfig, AtomTier
    from adam.blackboard.models.zone2_reasoning import AtomType
    
    def create_config(
        atom_id: str = "test_atom",
        atom_type: AtomType = AtomType.REGULATORY_FOCUS,
        atom_name: str = "Test Atom",
        **kwargs,
    ) -> AtomConfig:
        return AtomConfig(
            atom_id=atom_id,
            atom_type=atom_type,
            atom_name=atom_name,
            tier=kwargs.get("tier", AtomTier.STANDARD),
            max_latency_ms=kwargs.get("max_latency_ms", 1000),
            use_claude_for_fusion=kwargs.get("use_claude_for_fusion", False),
        )
    
    return create_config


@pytest.fixture
def atom_input_factory(request_context_factory):
    """Factory for creating AtomInput instances."""
    from adam.atoms.models.atom_io import AtomInput
    
    def create_input(
        user_id: str = "test_user_001",
        request_id: str = None,
        skip_claude: bool = True,
        upstream_outputs: Dict = None,
        request_context = None,
        **kwargs,
    ) -> AtomInput:
        req_id = request_id or f"req_{uuid4().hex[:12]}"
        ctx = request_context or request_context_factory(request_id=req_id, user_id=user_id)
        
        return AtomInput(
            request_id=req_id,
            user_id=user_id,
            request_context=ctx,
            skip_claude=skip_claude,
            upstream_outputs=upstream_outputs or {},
            latency_budget_ms=kwargs.get("latency_budget_ms", 500),
            debug_mode=kwargs.get("debug_mode", False),
        )
    
    return create_input


@pytest.fixture
def regulatory_focus_atom(blackboard, interaction_bridge):
    """Regulatory focus atom instance."""
    from adam.atoms.core.regulatory_focus import RegulatoryFocusAtom
    
    atom = RegulatoryFocusAtom(
        blackboard=blackboard,
        bridge=interaction_bridge,
    )
    yield atom


@pytest.fixture
def construal_level_atom(blackboard, interaction_bridge):
    """Construal level atom instance."""
    from adam.atoms.core.construal_level import ConstrualLevelAtom
    
    atom = ConstrualLevelAtom(
        blackboard=blackboard,
        bridge=interaction_bridge,
    )
    yield atom


@pytest.fixture
def atom_dag(blackboard, interaction_bridge):
    """Full atom DAG instance."""
    from adam.atoms.dag import AtomDAG
    
    dag = AtomDAG(
        blackboard=blackboard,
        bridge=interaction_bridge,
    )
    yield dag


# =============================================================================
# 4. PLATFORM FIXTURES
# =============================================================================

@pytest.fixture
def iheart_context():
    """Sample iHeart request context."""
    return {
        "station_id": "KIIS-FM",
        "station_format": "CHR",
        "session_id": f"session_{uuid4().hex[:8]}",
        "listener_id": f"listener_{uuid4().hex[:8]}",
        "audio_features": {
            "tempo": 120,
            "energy": 0.8,
            "valence": 0.7,
        },
        "ad_slot": {
            "position": "mid_roll",
            "duration_seconds": 30,
        },
    }


@pytest.fixture
def wpp_context():
    """Sample WPP request context."""
    return {
        "campaign_id": f"camp_{uuid4().hex[:8]}",
        "brand_id": "brand_001",
        "creative_id": f"creative_{uuid4().hex[:8]}",
        "placement": "display",
        "device_type": "mobile",
        "geo": {
            "country": "US",
            "state": "CA",
        },
    }


@pytest.fixture
def iheart_service(blackboard, gradient_bridge, mock_redis):
    """iHeart ad service."""
    from adam.platform.iheart.service import iHeartAdService
    
    with patch("adam.platform.iheart.service.get_kafka_producer", return_value=None):
        service = iHeartAdService(
            blackboard=blackboard,
            gradient_bridge=gradient_bridge,
            cache=mock_redis,
        )
        yield service


# =============================================================================
# 5. USER DATA FIXTURES
# =============================================================================

@pytest.fixture
def sample_user_profile():
    """Sample user psychological profile."""
    return {
        "user_id": "test_user_001",
        "big_five": {
            "openness": 0.65,
            "conscientiousness": 0.58,
            "extraversion": 0.72,
            "agreeableness": 0.55,
            "neuroticism": 0.42,
        },
        "regulatory_focus": {
            "promotion": 0.62,
            "prevention": 0.38,
        },
        "construal_level": 0.55,  # Slightly abstract
        "mechanism_effectiveness": {
            "social_proof": 0.73,
            "scarcity": 0.65,
            "authority": 0.58,
        },
    }


@pytest.fixture
def sample_ad_candidates():
    """Sample ad candidates for testing."""
    from adam.blackboard.models.zone1_context import AdCandidate
    
    return [
        AdCandidate(
            ad_id="ad_001",
            campaign_id="camp_001",
            creative_id="creative_001",
            brand_id="brand_001",
            category_id="electronics",
            mechanism_id="social_proof",
        ),
        AdCandidate(
            ad_id="ad_002",
            campaign_id="camp_001",
            creative_id="creative_002",
            brand_id="brand_001",
            category_id="electronics",
            mechanism_id="scarcity",
        ),
        AdCandidate(
            ad_id="ad_003",
            campaign_id="camp_002",
            creative_id="creative_003",
            brand_id="brand_002",
            category_id="fashion",
            mechanism_id="authority",
        ),
    ]


@pytest.fixture
def sample_mechanism_history():
    """Sample mechanism history for a user."""
    return {
        "social_proof": {
            "mechanism_id": "social_proof",
            "trial_count": 45,
            "success_count": 33,
            "success_rate": 0.733,
            "last_used": datetime.now(timezone.utc).isoformat(),
        },
        "scarcity": {
            "mechanism_id": "scarcity",
            "trial_count": 28,
            "success_count": 18,
            "success_rate": 0.643,
            "last_used": datetime.now(timezone.utc).isoformat(),
        },
        "authority": {
            "mechanism_id": "authority",
            "trial_count": 15,
            "success_count": 9,
            "success_rate": 0.600,
            "last_used": datetime.now(timezone.utc).isoformat(),
        },
    }


# =============================================================================
# 6. NEW MODULE FIXTURES
# =============================================================================

@pytest.fixture
def cold_start_service(mock_redis, interaction_bridge):
    """Cold start service."""
    from adam.user.cold_start.service import ColdStartService
    
    service = ColdStartService(
        cache=mock_redis,
        bridge=interaction_bridge,
    )
    yield service


@pytest.fixture
def signal_aggregation_service(mock_redis):
    """Signal aggregation service."""
    from adam.user.signal_aggregation.service import SignalAggregationService
    
    with patch(
        "adam.user.signal_aggregation.service.get_kafka_producer",
        return_value=AsyncMock(),
    ):
        service = SignalAggregationService(cache=mock_redis)
        yield service


@pytest.fixture
def identity_service(mock_redis, interaction_bridge):
    """Identity resolution service."""
    from adam.user.identity.service import IdentityResolutionService
    
    service = IdentityResolutionService(
        cache=mock_redis,
        bridge=interaction_bridge,
    )
    yield service


@pytest.fixture
def validity_service(mock_redis):
    """Psychological validity service."""
    from adam.validity.service import PsychologicalValidityService
    
    service = PsychologicalValidityService(cache=mock_redis)
    yield service


@pytest.fixture
def embedding_service(mock_redis):
    """Embedding service."""
    from adam.embeddings.service import EmbeddingService
    
    service = EmbeddingService(cache=mock_redis)
    yield service


@pytest.fixture
def privacy_service(mock_redis):
    """Privacy service."""
    from adam.privacy.service import PrivacyService
    
    service = PrivacyService(cache=mock_redis)
    yield service


@pytest.fixture
def audio_service(mock_redis):
    """Audio service."""
    from adam.audio.service import AudioService
    
    service = AudioService(cache=mock_redis)
    yield service


@pytest.fixture
def feature_store(mock_redis):
    """Feature store service."""
    from adam.features.service import FeatureStoreService
    
    service = FeatureStoreService(cache=mock_redis)
    yield service


@pytest.fixture
def multimodal_service(mock_redis):
    """Multimodal fusion service."""
    from adam.multimodal.service import MultimodalService
    
    service = MultimodalService(cache=mock_redis)
    yield service


@pytest.fixture
def performance_service(mock_redis):
    """Performance service."""
    from adam.performance.service import PerformanceService
    
    service = PerformanceService(redis_cache=mock_redis)
    yield service


# =============================================================================
# 7. HELPER FIXTURES
# =============================================================================

@pytest.fixture
def request_id():
    """Generate a unique request ID."""
    return f"req_{uuid4().hex[:12]}"


@pytest.fixture
def user_id():
    """Generate a unique user ID."""
    return f"user_{uuid4().hex[:12]}"


@pytest.fixture
def decision_id():
    """Generate a unique decision ID."""
    return f"dec_{uuid4().hex[:12]}"


@pytest.fixture
def assert_signal_emitted(mock_kafka):
    """Helper to assert learning signals were emitted."""
    def _assert(signal_type: str, count: int = 1):
        matching = [
            m for m in mock_kafka.get_messages()
            if m.get("type") == signal_type or 
               m.get("value", {}).get("signal_type") == signal_type
        ]
        assert len(matching) >= count, (
            f"Expected at least {count} {signal_type} signals, "
            f"got {len(matching)}"
        )
    
    return _assert
