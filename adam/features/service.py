# =============================================================================
# ADAM Feature Store Service
# Location: adam/features/service.py
# =============================================================================

"""
FEATURE STORE SERVICE

Unified feature serving and management.
"""

import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from neo4j import AsyncDriver

from adam.features.models import (
    FeatureType,
    FeatureScope,
    AggregationType,
    FeatureDefinition,
    FeatureValue,
    FeatureSet,
)
from adam.infrastructure.redis import ADAMRedisCache

logger = logging.getLogger(__name__)


# =============================================================================
# NEO4J CYPHER QUERIES FOR FEATURE PERSISTENCE
# =============================================================================

QUERY_PERSIST_FEATURE = """
// Persist or update a feature value
MATCH (u:User {user_id: $entity_id})
MERGE (f:FeatureValue {feature_id: $feature_id, entity_id: $entity_id})
ON CREATE SET
    f.value = $value,
    f.value_type = $value_type,
    f.created_at = datetime(),
    f.updated_at = datetime(),
    f.version = 1,
    f.source = $source
ON MATCH SET
    f.value = $value,
    f.updated_at = datetime(),
    f.version = f.version + 1,
    f.source = $source
MERGE (u)-[:HAS_FEATURE]->(f)
RETURN f
"""

QUERY_GET_FEATURES = """
// Get all features for an entity
MATCH (u:User {user_id: $entity_id})-[:HAS_FEATURE]->(f:FeatureValue)
WHERE f.feature_id IN $feature_ids OR $feature_ids = []
RETURN f.feature_id AS feature_id,
       f.value AS value,
       f.value_type AS value_type,
       f.updated_at AS updated_at,
       f.version AS version,
       f.source AS source
"""

QUERY_BATCH_PERSIST_FEATURES = """
// Batch persist features
UNWIND $features AS feat
MATCH (u:User {user_id: feat.entity_id})
MERGE (f:FeatureValue {feature_id: feat.feature_id, entity_id: feat.entity_id})
ON CREATE SET
    f.value = feat.value,
    f.value_type = feat.value_type,
    f.created_at = datetime(),
    f.updated_at = datetime(),
    f.version = 1,
    f.source = feat.source
ON MATCH SET
    f.value = feat.value,
    f.updated_at = datetime(),
    f.version = f.version + 1,
    f.source = feat.source
MERGE (u)-[:HAS_FEATURE]->(f)
RETURN count(f) AS persisted_count
"""

QUERY_GET_FEATURE_HISTORY = """
// Get feature value history (requires versioned storage)
MATCH (u:User {user_id: $entity_id})-[:HAS_FEATURE]->(f:FeatureValue {feature_id: $feature_id})
OPTIONAL MATCH (f)-[:PREVIOUS_VERSION]->(prev:FeatureValue)
RETURN f.value AS current_value,
       f.updated_at AS current_timestamp,
       f.version AS current_version,
       collect(prev {.value, .updated_at, .version}) AS history
"""

QUERY_REGISTER_FEATURE_DEFINITION = """
// Persist feature definition
MERGE (d:FeatureDefinition {feature_id: $feature_id})
ON CREATE SET
    d.name = $name,
    d.feature_type = $feature_type,
    d.scope = $scope,
    d.default_value = $default_value,
    d.dimensions = $dimensions,
    d.aggregation = $aggregation,
    d.time_window_seconds = $time_window_seconds,
    d.created_at = datetime()
ON MATCH SET
    d.name = $name,
    d.feature_type = $feature_type,
    d.scope = $scope,
    d.default_value = $default_value,
    d.dimensions = $dimensions,
    d.aggregation = $aggregation,
    d.time_window_seconds = $time_window_seconds,
    d.updated_at = datetime()
RETURN d
"""

QUERY_AGGREGATE_FEATURE_STATS = """
// Get aggregate statistics for a feature across users
MATCH (f:FeatureValue {feature_id: $feature_id})
WHERE f.value IS NOT NULL
RETURN f.feature_id AS feature_id,
       count(f) AS user_count,
       avg(toFloat(f.value)) AS mean_value,
       stdev(toFloat(f.value)) AS std_value,
       min(toFloat(f.value)) AS min_value,
       max(toFloat(f.value)) AS max_value
"""


class FeatureRegistry:
    """Registry of feature definitions."""
    
    def __init__(self):
        self._definitions: Dict[str, FeatureDefinition] = {}
        self._register_psychological_features()
    
    def _register_psychological_features(self) -> None:
        """Register standard psychological features."""
        
        psychological_features = [
            FeatureDefinition(
                feature_id="big_five_openness",
                name="Big Five: Openness",
                feature_type=FeatureType.FLOAT,
                scope=FeatureScope.USER,
                default_value=0.5,
            ),
            FeatureDefinition(
                feature_id="big_five_conscientiousness",
                name="Big Five: Conscientiousness",
                feature_type=FeatureType.FLOAT,
                scope=FeatureScope.USER,
                default_value=0.5,
            ),
            FeatureDefinition(
                feature_id="big_five_extraversion",
                name="Big Five: Extraversion",
                feature_type=FeatureType.FLOAT,
                scope=FeatureScope.USER,
                default_value=0.5,
            ),
            FeatureDefinition(
                feature_id="big_five_agreeableness",
                name="Big Five: Agreeableness",
                feature_type=FeatureType.FLOAT,
                scope=FeatureScope.USER,
                default_value=0.5,
            ),
            FeatureDefinition(
                feature_id="big_five_neuroticism",
                name="Big Five: Neuroticism",
                feature_type=FeatureType.FLOAT,
                scope=FeatureScope.USER,
                default_value=0.5,
            ),
            FeatureDefinition(
                feature_id="regulatory_focus_promotion",
                name="Regulatory Focus: Promotion",
                feature_type=FeatureType.FLOAT,
                scope=FeatureScope.USER,
                default_value=0.5,
            ),
            FeatureDefinition(
                feature_id="regulatory_focus_prevention",
                name="Regulatory Focus: Prevention",
                feature_type=FeatureType.FLOAT,
                scope=FeatureScope.USER,
                default_value=0.5,
            ),
            FeatureDefinition(
                feature_id="construal_level",
                name="Construal Level",
                feature_type=FeatureType.FLOAT,
                scope=FeatureScope.USER,
                default_value=0.5,
            ),
            FeatureDefinition(
                feature_id="mechanism_embedding",
                name="Mechanism Embedding",
                feature_type=FeatureType.VECTOR,
                scope=FeatureScope.USER,
                dimensions=64,
            ),
            FeatureDefinition(
                feature_id="engagement_rate_7d",
                name="7-Day Engagement Rate",
                feature_type=FeatureType.FLOAT,
                scope=FeatureScope.USER,
                aggregation=AggregationType.MEAN,
                time_window_seconds=7 * 24 * 3600,
            ),
        ]
        
        for feat in psychological_features:
            self._definitions[feat.feature_id] = feat
    
    def register(self, definition: FeatureDefinition) -> None:
        """Register a feature definition."""
        self._definitions[definition.feature_id] = definition
    
    def get(self, feature_id: str) -> Optional[FeatureDefinition]:
        """Get a feature definition."""
        return self._definitions.get(feature_id)
    
    def list_all(self) -> List[FeatureDefinition]:
        """List all feature definitions."""
        return list(self._definitions.values())


class FeatureServer:
    """Real-time feature serving."""
    
    def __init__(
        self,
        registry: FeatureRegistry,
        cache: Optional[ADAMRedisCache] = None,
    ):
        self.registry = registry
        self.cache = cache
        
        # In-memory feature store (production: Redis + DB)
        self._store: Dict[str, Dict[str, FeatureValue]] = {}
    
    async def get_features(
        self,
        entity_id: str,
        feature_ids: List[str],
    ) -> FeatureSet:
        """Get features for an entity."""
        
        start = time.perf_counter()
        
        features = {}
        freshness = {}
        now = datetime.now(timezone.utc)
        
        for feature_id in feature_ids:
            # Check cache first
            cache_key = f"feature:{entity_id}:{feature_id}"
            
            if self.cache:
                cached = await self.cache.get(cache_key)
                if cached:
                    features[feature_id] = cached["value"]
                    ts = datetime.fromisoformat(cached["timestamp"])
                    freshness[feature_id] = (now - ts).total_seconds()
                    continue
            
            # Check store
            entity_features = self._store.get(entity_id, {})
            if feature_id in entity_features:
                fv = entity_features[feature_id]
                features[feature_id] = fv.value
                freshness[feature_id] = (now - fv.timestamp).total_seconds()
            else:
                # Use default
                definition = self.registry.get(feature_id)
                if definition and definition.default_value is not None:
                    features[feature_id] = definition.default_value
                    freshness[feature_id] = float("inf")
        
        duration = (time.perf_counter() - start) * 1000
        
        return FeatureSet(
            entity_id=entity_id,
            features=features,
            feature_ids=list(features.keys()),
            freshness=freshness,
            retrieval_duration_ms=duration,
        )
    
    async def set_feature(
        self,
        entity_id: str,
        feature_id: str,
        value: Any,
    ) -> FeatureValue:
        """Set a feature value."""
        
        fv = FeatureValue(
            feature_id=feature_id,
            entity_id=entity_id,
            value=value,
        )
        
        # Store
        if entity_id not in self._store:
            self._store[entity_id] = {}
        self._store[entity_id][feature_id] = fv
        
        # Cache
        if self.cache:
            await self.cache.set(
                f"feature:{entity_id}:{feature_id}",
                {"value": value, "timestamp": fv.timestamp.isoformat()},
                ttl=3600,
            )
        
        return fv


class Neo4jFeatureStorage:
    """
    Neo4j offline storage for features.
    
    Provides durable persistence for feature values with:
    - Versioning and history
    - Batch operations
    - Aggregate statistics
    
    Reference: Enhancement #30 Feature Store - Offline Storage
    """
    
    def __init__(self, neo4j_driver: AsyncDriver):
        self.neo4j = neo4j_driver
    
    async def persist_feature(
        self,
        entity_id: str,
        feature_id: str,
        value: Any,
        value_type: str = "float",
        source: str = "system",
    ) -> bool:
        """Persist a single feature value to Neo4j."""
        try:
            async with self.neo4j.session() as session:
                await session.run(
                    QUERY_PERSIST_FEATURE,
                    entity_id=entity_id,
                    feature_id=feature_id,
                    value=value,
                    value_type=value_type,
                    source=source,
                )
            return True
        except Exception as e:
            logger.error(f"Failed to persist feature {feature_id}: {e}")
            return False
    
    async def batch_persist_features(
        self,
        features: List[Dict[str, Any]],
    ) -> int:
        """
        Batch persist multiple features.
        
        Args:
            features: List of dicts with entity_id, feature_id, value, value_type, source
        
        Returns:
            Number of features persisted
        """
        try:
            async with self.neo4j.session() as session:
                result = await session.run(
                    QUERY_BATCH_PERSIST_FEATURES,
                    features=features,
                )
                record = await result.single()
                return record["persisted_count"] if record else 0
        except Exception as e:
            logger.error(f"Failed to batch persist features: {e}")
            return 0
    
    async def get_features(
        self,
        entity_id: str,
        feature_ids: Optional[List[str]] = None,
    ) -> Dict[str, FeatureValue]:
        """Get features from Neo4j offline storage."""
        try:
            async with self.neo4j.session() as session:
                result = await session.run(
                    QUERY_GET_FEATURES,
                    entity_id=entity_id,
                    feature_ids=feature_ids or [],
                )
                records = await result.data()
                
                features = {}
                for record in records:
                    features[record["feature_id"]] = FeatureValue(
                        feature_id=record["feature_id"],
                        entity_id=entity_id,
                        value=record["value"],
                    )
                return features
        except Exception as e:
            logger.error(f"Failed to get features from Neo4j: {e}")
            return {}
    
    async def get_feature_history(
        self,
        entity_id: str,
        feature_id: str,
    ) -> Dict[str, Any]:
        """Get feature value history."""
        try:
            async with self.neo4j.session() as session:
                result = await session.run(
                    QUERY_GET_FEATURE_HISTORY,
                    entity_id=entity_id,
                    feature_id=feature_id,
                )
                record = await result.single()
                if record:
                    return dict(record)
                return {}
        except Exception as e:
            logger.error(f"Failed to get feature history: {e}")
            return {}
    
    async def persist_feature_definition(
        self,
        definition: FeatureDefinition,
    ) -> bool:
        """Persist a feature definition to Neo4j."""
        try:
            async with self.neo4j.session() as session:
                await session.run(
                    QUERY_REGISTER_FEATURE_DEFINITION,
                    feature_id=definition.feature_id,
                    name=definition.name,
                    feature_type=definition.feature_type.value,
                    scope=definition.scope.value,
                    default_value=definition.default_value,
                    dimensions=definition.dimensions,
                    aggregation=definition.aggregation.value if definition.aggregation else None,
                    time_window_seconds=definition.time_window_seconds,
                )
            return True
        except Exception as e:
            logger.error(f"Failed to persist feature definition: {e}")
            return False
    
    async def get_feature_stats(
        self,
        feature_id: str,
    ) -> Dict[str, Any]:
        """Get aggregate statistics for a feature across all users."""
        try:
            async with self.neo4j.session() as session:
                result = await session.run(
                    QUERY_AGGREGATE_FEATURE_STATS,
                    feature_id=feature_id,
                )
                record = await result.single()
                if record:
                    return dict(record)
                return {}
        except Exception as e:
            logger.error(f"Failed to get feature stats: {e}")
            return {}


class FeatureStoreService:
    """
    Unified feature store service.
    
    Architecture:
    1. In-memory store: Fastest, volatile
    2. Redis cache: Fast, semi-durable
    3. Neo4j storage: Durable, queryable
    
    Write-through: Updates go to all tiers
    Read hierarchy: Memory → Redis → Neo4j → Default
    """
    
    def __init__(
        self,
        cache: Optional[ADAMRedisCache] = None,
        neo4j_driver: Optional[AsyncDriver] = None,
    ):
        self.registry = FeatureRegistry()
        self.server = FeatureServer(self.registry, cache)
        self.offline_storage = Neo4jFeatureStorage(neo4j_driver) if neo4j_driver else None
    
    async def get_user_features(
        self,
        user_id: str,
        feature_ids: Optional[List[str]] = None,
    ) -> FeatureSet:
        """Get features for a user."""
        
        if feature_ids is None:
            # Default psychological features
            feature_ids = [
                "big_five_openness",
                "big_five_conscientiousness",
                "big_five_extraversion",
                "big_five_agreeableness",
                "big_five_neuroticism",
                "regulatory_focus_promotion",
                "regulatory_focus_prevention",
                "construal_level",
            ]
        
        return await self.server.get_features(user_id, feature_ids)
    
    async def update_user_features(
        self,
        user_id: str,
        features: Dict[str, Any],
        persist_to_neo4j: bool = True,
    ) -> List[FeatureValue]:
        """
        Update multiple features for a user.
        
        Write-through architecture:
        1. Update in-memory store
        2. Update Redis cache
        3. Persist to Neo4j (optional, for durability)
        """
        results = []
        for feature_id, value in features.items():
            fv = await self.server.set_feature(user_id, feature_id, value)
            results.append(fv)
        
        # Persist to Neo4j for durability
        if persist_to_neo4j and self.offline_storage:
            batch = [
                {
                    "entity_id": user_id,
                    "feature_id": feature_id,
                    "value": value,
                    "value_type": self._infer_value_type(value),
                    "source": "feature_store",
                }
                for feature_id, value in features.items()
            ]
            await self.offline_storage.batch_persist_features(batch)
        
        return results
    
    def _infer_value_type(self, value: Any) -> str:
        """Infer the value type for storage."""
        if isinstance(value, float):
            return "float"
        elif isinstance(value, int):
            return "integer"
        elif isinstance(value, bool):
            return "boolean"
        elif isinstance(value, list):
            return "vector"
        elif isinstance(value, str):
            return "string"
        else:
            return "unknown"
    
    async def register_feature(
        self,
        feature_id: str,
        name: str,
        feature_type: FeatureType,
        scope: FeatureScope,
        persist_to_neo4j: bool = True,
        **kwargs,
    ) -> FeatureDefinition:
        """Register a new feature."""
        
        definition = FeatureDefinition(
            feature_id=feature_id,
            name=name,
            feature_type=feature_type,
            scope=scope,
            **kwargs,
        )
        
        self.registry.register(definition)
        
        # Persist definition to Neo4j
        if persist_to_neo4j and self.offline_storage:
            await self.offline_storage.persist_feature_definition(definition)
        
        return definition
    
    async def sync_from_neo4j(
        self,
        user_id: str,
        feature_ids: Optional[List[str]] = None,
    ) -> int:
        """
        Sync features from Neo4j to in-memory/Redis.
        
        Useful for:
        - Cold start after restart
        - Recovering from cache eviction
        - Cross-instance consistency
        
        Returns:
            Number of features synced
        """
        if not self.offline_storage:
            return 0
        
        try:
            neo4j_features = await self.offline_storage.get_features(user_id, feature_ids)
            
            for feature_id, fv in neo4j_features.items():
                await self.server.set_feature(user_id, feature_id, fv.value)
            
            return len(neo4j_features)
        except Exception as e:
            logger.error(f"Failed to sync from Neo4j: {e}")
            return 0
    
    async def get_feature_stats(
        self,
        feature_id: str,
    ) -> Dict[str, Any]:
        """
        Get aggregate statistics for a feature.
        
        Useful for:
        - Monitoring feature drift
        - Understanding feature distributions
        - Quality checks
        """
        if not self.offline_storage:
            return {}
        
        return await self.offline_storage.get_feature_stats(feature_id)
    
    async def get_feature_history(
        self,
        user_id: str,
        feature_id: str,
    ) -> Dict[str, Any]:
        """
        Get historical values for a feature.
        
        Useful for:
        - Tracking feature evolution
        - Debugging
        - Temporal analysis
        """
        if not self.offline_storage:
            return {}
        
        return await self.offline_storage.get_feature_history(user_id, feature_id)
    
    async def batch_persist_to_neo4j(
        self,
        user_features: Dict[str, Dict[str, Any]],
    ) -> int:
        """
        Batch persist features for multiple users.
        
        Args:
            user_features: Dict of user_id -> Dict of feature_id -> value
        
        Returns:
            Total features persisted
        """
        if not self.offline_storage:
            return 0
        
        batch = []
        for user_id, features in user_features.items():
            for feature_id, value in features.items():
                batch.append({
                    "entity_id": user_id,
                    "feature_id": feature_id,
                    "value": value,
                    "value_type": self._infer_value_type(value),
                    "source": "batch_persist",
                })
        
        return await self.offline_storage.batch_persist_features(batch)
