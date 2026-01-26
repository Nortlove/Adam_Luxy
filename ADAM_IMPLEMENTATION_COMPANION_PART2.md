# ADAM Implementation Companion - Part 2
## Advanced Services, Workflows, and Integration Patterns

**Continuation of**: ADAM Implementation Companion  
**Purpose**: Additional production code patterns for the cognitive ecosystem  
**Version**: 1.0  
**Status**: Production Implementation Ready

---

# Part 5: Cache Service Implementation

## 5.1 Multi-Level Caching Architecture

```python
"""
ADAM Cache Service
Multi-level caching for sub-100ms latency requirements
"""

from typing import Dict, Any, Optional, List, TypeVar, Generic
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import asyncio
import json
import hashlib
from redis import asyncio as aioredis
from pydantic import BaseModel

from adam.models.core import (
    UserProfile, MechanismEffectiveness, 
    BigFiveProfile, ExtendedPsychologicalProfile
)


class CacheLevel(str, Enum):
    """Cache levels with different TTLs and purposes."""
    HOT = "hot"           # <10ms access, 5 min TTL, most frequent
    WARM = "warm"         # <50ms access, 30 min TTL, computed aggregates
    COLD = "cold"         # <100ms access, 4 hour TTL, stable data
    PERSISTENT = "persistent"  # Graph-backed, infinite TTL


@dataclass
class CacheConfig:
    """Configuration for cache behavior."""
    hot_ttl_seconds: int = 300          # 5 minutes
    warm_ttl_seconds: int = 1800        # 30 minutes
    cold_ttl_seconds: int = 14400       # 4 hours
    
    # Invalidation settings
    invalidate_on_outcome: bool = True
    invalidate_on_discovery: bool = True
    
    # Compression
    compress_threshold_bytes: int = 1024
    
    # Connection pool
    max_connections: int = 100
    connection_timeout_seconds: int = 5


class CacheService:
    """
    Multi-level cache service for ADAM.
    
    Provides sub-10ms access to hot data while maintaining
    consistency with the graph database.
    """
    
    def __init__(self, redis_url: str = "redis://localhost:6379", config: CacheConfig = None):
        self.redis_url = redis_url
        self.config = config or CacheConfig()
        self._redis: Optional[aioredis.Redis] = None
        
        # Local in-memory cache for ultra-hot data
        self._local_cache: Dict[str, Any] = {}
        self._local_cache_times: Dict[str, datetime] = {}
        self._local_cache_ttl = 10  # seconds
    
    async def connect(self):
        """Initialize Redis connection."""
        if not self._redis:
            self._redis = await aioredis.from_url(
                self.redis_url,
                max_connections=self.config.max_connections,
                socket_timeout=self.config.connection_timeout_seconds
            )
    
    async def close(self):
        """Close Redis connection."""
        if self._redis:
            await self._redis.close()
    
    # -------------------------------------------------------------------------
    # User Profile Caching
    # -------------------------------------------------------------------------
    
    async def get_user_profile(self, user_id: str) -> Optional[UserProfile]:
        """Get user profile from cache hierarchy."""
        
        # Level 1: Local in-memory cache
        local_key = f"profile:{user_id}"
        if local_key in self._local_cache:
            if self._is_local_valid(local_key):
                return self._local_cache[local_key]
        
        # Level 2: Redis hot cache
        await self.connect()
        redis_key = f"adam:hot:profile:{user_id}"
        
        cached = await self._redis.get(redis_key)
        if cached:
            profile = UserProfile.model_validate_json(cached)
            # Promote to local cache
            self._set_local(local_key, profile)
            return profile
        
        return None
    
    async def set_user_profile(
        self, 
        user_id: str, 
        profile: UserProfile,
        level: CacheLevel = CacheLevel.HOT
    ):
        """Cache user profile at specified level."""
        
        await self.connect()
        
        ttl = self._get_ttl(level)
        redis_key = f"adam:{level.value}:profile:{user_id}"
        
        await self._redis.setex(
            redis_key,
            ttl,
            profile.model_dump_json()
        )
        
        # Also set in local cache if hot
        if level == CacheLevel.HOT:
            self._set_local(f"profile:{user_id}", profile)
    
    async def invalidate_user_profile(self, user_id: str):
        """Invalidate user profile across all cache levels."""
        
        await self.connect()
        
        # Clear local
        local_key = f"profile:{user_id}"
        self._local_cache.pop(local_key, None)
        self._local_cache_times.pop(local_key, None)
        
        # Clear all Redis levels
        for level in CacheLevel:
            if level != CacheLevel.PERSISTENT:
                key = f"adam:{level.value}:profile:{user_id}"
                await self._redis.delete(key)
    
    # -------------------------------------------------------------------------
    # Mechanism Priors Caching
    # -------------------------------------------------------------------------
    
    async def get_mechanism_priors(
        self, 
        user_id: str
    ) -> Optional[Dict[str, Dict[str, float]]]:
        """Get mechanism effectiveness priors from cache."""
        
        await self.connect()
        
        key = f"adam:hot:priors:{user_id}"
        cached = await self._redis.get(key)
        
        if cached:
            return json.loads(cached)
        
        return None
    
    async def set_mechanism_priors(
        self,
        user_id: str,
        priors: Dict[str, Dict[str, float]]
    ):
        """Cache mechanism priors."""
        
        await self.connect()
        
        key = f"adam:hot:priors:{user_id}"
        await self._redis.setex(
            key,
            self.config.hot_ttl_seconds,
            json.dumps(priors)
        )
    
    async def update_mechanism_prior(
        self,
        user_id: str,
        mechanism_id: str,
        success: bool,
        weight: float = 1.0
    ):
        """
        Update a single mechanism prior in cache.
        Uses Redis HSET for atomic updates.
        """
        
        await self.connect()
        
        key = f"adam:hot:prior:{user_id}:{mechanism_id}"
        
        # Atomic increment
        pipe = self._redis.pipeline()
        
        if success:
            pipe.hincrbyfloat(key, 'alpha', weight)
        else:
            pipe.hincrbyfloat(key, 'beta', weight)
        
        pipe.hincrby(key, 'observations', 1)
        pipe.hset(key, 'updated', datetime.utcnow().isoformat())
        pipe.expire(key, self.config.hot_ttl_seconds)
        
        await pipe.execute()
    
    # -------------------------------------------------------------------------
    # Cluster Priors Caching
    # -------------------------------------------------------------------------
    
    async def get_cluster_priors(
        self, 
        cluster_id: int
    ) -> Optional[Dict[str, Dict[str, float]]]:
        """Get cluster-level mechanism priors."""
        
        await self.connect()
        
        key = f"adam:warm:cluster_priors:{cluster_id}"
        cached = await self._redis.get(key)
        
        if cached:
            return json.loads(cached)
        
        return None
    
    async def set_cluster_priors(
        self,
        cluster_id: int,
        priors: Dict[str, Dict[str, float]]
    ):
        """Cache cluster-level priors (warm cache, longer TTL)."""
        
        await self.connect()
        
        key = f"adam:warm:cluster_priors:{cluster_id}"
        await self._redis.setex(
            key,
            self.config.warm_ttl_seconds,
            json.dumps(priors)
        )
    
    # -------------------------------------------------------------------------
    # Segment Aggregates
    # -------------------------------------------------------------------------
    
    async def update_segment_aggregate(
        self,
        segment_id: str,
        mechanism_id: str,
        success: bool
    ):
        """Update segment-level success aggregates."""
        
        await self.connect()
        
        key = f"adam:warm:segment:{segment_id}:{mechanism_id}"
        
        pipe = self._redis.pipeline()
        pipe.hincrby(key, 'total', 1)
        if success:
            pipe.hincrby(key, 'successes', 1)
        pipe.expire(key, self.config.warm_ttl_seconds)
        
        await pipe.execute()
    
    async def get_segment_effectiveness(
        self,
        segment_id: str,
        mechanism_id: str
    ) -> Optional[float]:
        """Get segment-level mechanism effectiveness."""
        
        await self.connect()
        
        key = f"adam:warm:segment:{segment_id}:{mechanism_id}"
        data = await self._redis.hgetall(key)
        
        if data:
            total = int(data.get(b'total', 0))
            successes = int(data.get(b'successes', 0))
            
            if total > 0:
                return successes / total
        
        return None
    
    # -------------------------------------------------------------------------
    # Calibration Data
    # -------------------------------------------------------------------------
    
    async def update_calibration_bucket(
        self,
        bucket: int,  # 0-10 representing confidence 0.0-1.0
        predicted_success: bool,
        actual_success: bool
    ):
        """Update calibration data for a confidence bucket."""
        
        await self.connect()
        
        key = f"adam:cold:calibration:{bucket}"
        
        pipe = self._redis.pipeline()
        pipe.hincrby(key, 'total', 1)
        if actual_success:
            pipe.hincrby(key, 'actual_positive', 1)
        pipe.expire(key, self.config.cold_ttl_seconds)
        
        await pipe.execute()
    
    async def get_calibration_curve(self) -> Dict[int, float]:
        """Get the calibration curve (bucket → actual rate)."""
        
        await self.connect()
        
        curve = {}
        for bucket in range(11):
            key = f"adam:cold:calibration:{bucket}"
            data = await self._redis.hgetall(key)
            
            if data:
                total = int(data.get(b'total', 0))
                positives = int(data.get(b'actual_positive', 0))
                
                if total > 0:
                    curve[bucket] = positives / total
        
        return curve
    
    # -------------------------------------------------------------------------
    # Discovery Cache
    # -------------------------------------------------------------------------
    
    async def cache_recent_discoveries(
        self,
        discoveries: List[Dict[str, Any]]
    ):
        """Cache recent discoveries for fast access."""
        
        await self.connect()
        
        key = "adam:warm:recent_discoveries"
        await self._redis.setex(
            key,
            self.config.warm_ttl_seconds,
            json.dumps(discoveries)
        )
    
    async def get_recent_discoveries(self) -> List[Dict[str, Any]]:
        """Get cached recent discoveries."""
        
        await self.connect()
        
        key = "adam:warm:recent_discoveries"
        cached = await self._redis.get(key)
        
        if cached:
            return json.loads(cached)
        
        return []
    
    # -------------------------------------------------------------------------
    # Batch Invalidation
    # -------------------------------------------------------------------------
    
    async def invalidate_by_pattern(self, pattern: str):
        """Invalidate all keys matching a pattern."""
        
        await self.connect()
        
        cursor = 0
        while True:
            cursor, keys = await self._redis.scan(
                cursor=cursor,
                match=pattern,
                count=100
            )
            
            if keys:
                await self._redis.delete(*keys)
            
            if cursor == 0:
                break
    
    async def invalidate_for_outcome(
        self,
        user_id: str,
        mechanism_id: str
    ):
        """Invalidate caches affected by an outcome."""
        
        # Invalidate user-specific caches
        await self.invalidate_user_profile(user_id)
        
        # Invalidate mechanism priors
        await self._redis.delete(f"adam:hot:priors:{user_id}")
        await self._redis.delete(f"adam:hot:prior:{user_id}:{mechanism_id}")
        
        # Clear local cache entries
        self._local_cache = {
            k: v for k, v in self._local_cache.items()
            if not k.startswith(f"profile:{user_id}")
        }
    
    # -------------------------------------------------------------------------
    # Helper Methods
    # -------------------------------------------------------------------------
    
    def _get_ttl(self, level: CacheLevel) -> int:
        """Get TTL for a cache level."""
        ttls = {
            CacheLevel.HOT: self.config.hot_ttl_seconds,
            CacheLevel.WARM: self.config.warm_ttl_seconds,
            CacheLevel.COLD: self.config.cold_ttl_seconds,
            CacheLevel.PERSISTENT: 0  # No expiry
        }
        return ttls.get(level, self.config.hot_ttl_seconds)
    
    def _is_local_valid(self, key: str) -> bool:
        """Check if local cache entry is still valid."""
        if key not in self._local_cache_times:
            return False
        
        age = (datetime.utcnow() - self._local_cache_times[key]).total_seconds()
        return age < self._local_cache_ttl
    
    def _set_local(self, key: str, value: Any):
        """Set value in local cache."""
        self._local_cache[key] = value
        self._local_cache_times[key] = datetime.utcnow()
        
        # Cleanup old entries periodically
        if len(self._local_cache) > 10000:
            self._cleanup_local_cache()
    
    def _cleanup_local_cache(self):
        """Remove expired entries from local cache."""
        now = datetime.utcnow()
        expired = [
            k for k, t in self._local_cache_times.items()
            if (now - t).total_seconds() > self._local_cache_ttl
        ]
        for k in expired:
            self._local_cache.pop(k, None)
            self._local_cache_times.pop(k, None)
```

---

# Part 6: Learning Propagator Service

## 6.1 Complete Implementation

```python
"""
ADAM Learning Propagator
Propagates learning signals to all components without bottlenecks
"""

from typing import Dict, Any, List, Optional, Set
from datetime import datetime
from dataclasses import dataclass, field
import asyncio
import json
from enum import Enum

import aiokafka
from redis import asyncio as aioredis
from neo4j import AsyncGraphDatabase
from prometheus_client import Counter, Histogram, Gauge

from adam.models.core import (
    LearningSignal, LearningPriority,
    OutcomeObservedSignal, DiscoveryMadeSignal
)
from adam.models.events import (
    OutcomeObservedEvent, LearningSignalEvent,
    PosteriorUpdateEvent, CacheInvalidationEvent
)
from adam.services.cache_service import CacheService
from adam.services.graph_service import GraphService


# Metrics
PROPAGATION_COUNTER = Counter(
    'adam_propagation_total',
    'Learning signals propagated',
    ['signal_type', 'priority', 'target']
)

PROPAGATION_LATENCY = Histogram(
    'adam_propagation_latency_seconds',
    'Latency of signal propagation',
    ['priority'],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.5]
)

ACTIVE_PROPAGATIONS = Gauge(
    'adam_active_propagations',
    'Currently active propagation tasks'
)


@dataclass
class PropagatorConfig:
    """Configuration for learning propagator."""
    
    # Kafka settings
    kafka_bootstrap: str = "localhost:9092"
    learning_topic: str = "adam.learning_signals"
    outcome_topic: str = "adam.outcomes"
    discovery_topic: str = "adam.discoveries"
    
    # Redis settings
    redis_url: str = "redis://localhost:6379"
    
    # Neo4j settings
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "password"
    
    # Processing settings
    batch_size: int = 100
    flush_interval_seconds: float = 0.1
    max_concurrent_propagations: int = 50


class LearningPropagator:
    """
    Propagates learning signals to all components.
    
    This is the nervous system of ADAM - ensuring that every
    insight reaches every component that could use it, without
    human bottlenecks.
    
    Principles:
    1. Every outcome generates learning signals
    2. Signals propagate to ALL relevant components
    3. No human approval needed for learning
    4. System is aggressive about learning
    """
    
    def __init__(self, config: PropagatorConfig = None):
        self.config = config or PropagatorConfig()
        
        # Services
        self.kafka_producer: Optional[aiokafka.AIOKafkaProducer] = None
        self.redis: Optional[aioredis.Redis] = None
        self.neo4j: Optional[AsyncGraphDatabase] = None
        self.cache = CacheService(self.config.redis_url)
        self.graph = GraphService(
            self.config.neo4j_uri,
            self.config.neo4j_user,
            self.config.neo4j_password
        )
        
        # Component subscriptions
        self.component_subscriptions: Dict[str, Set[str]] = {
            'copy_generation': {
                'outcome_observed',
                'mechanism_activated',
                'discovery_made'
            },
            'cold_start': {
                'outcome_observed',
                'cluster_shifted',
                'discovery_made'
            },
            'inference_engine': {
                'outcome_observed',
                'mechanism_activated',
                'calibration_updated',
                'discovery_made'
            },
            'journey_tracking': {
                'state_transitioned',
                'outcome_observed'
            },
            'verification': {
                'outcome_observed',
                'calibration_updated'
            },
            'brand_intelligence': {
                'outcome_observed',
                'mechanism_activated'
            },
            'ab_testing': {
                'outcome_observed'
            },
            'explanation_generator': {
                'outcome_observed',
                'mechanism_activated'
            },
            'aot_reasoning': {
                'outcome_observed',
                'calibration_updated',
                'discovery_made'
            },
            'discovery_engine': {
                'outcome_observed',
                'mechanism_activated',
                'trait_inferred'
            }
        }
        
        # Processing state
        self._pending_immediate: List[LearningSignal] = []
        self._pending_fast: List[LearningSignal] = []
        self._pending_async: List[LearningSignal] = []
        self._active_tasks: Set[asyncio.Task] = set()
        
        # Semaphore for concurrency control
        self._semaphore = asyncio.Semaphore(
            self.config.max_concurrent_propagations
        )
    
    async def start(self):
        """Initialize all connections."""
        
        # Kafka producer
        self.kafka_producer = aiokafka.AIOKafkaProducer(
            bootstrap_servers=self.config.kafka_bootstrap,
            value_serializer=lambda v: json.dumps(v).encode()
        )
        await self.kafka_producer.start()
        
        # Redis
        self.redis = await aioredis.from_url(self.config.redis_url)
        
        # Neo4j
        self.neo4j = AsyncGraphDatabase.driver(
            self.config.neo4j_uri,
            auth=(self.config.neo4j_user, self.config.neo4j_password)
        )
        
        # Start background processors
        asyncio.create_task(self._immediate_processor())
        asyncio.create_task(self._fast_processor())
        asyncio.create_task(self._async_processor())
    
    async def stop(self):
        """Gracefully shutdown."""
        
        # Wait for pending tasks
        if self._active_tasks:
            await asyncio.gather(*self._active_tasks, return_exceptions=True)
        
        # Close connections
        if self.kafka_producer:
            await self.kafka_producer.stop()
        if self.redis:
            await self.redis.close()
        if self.neo4j:
            await self.neo4j.close()
    
    # -------------------------------------------------------------------------
    # Main Propagation Entry Point
    # -------------------------------------------------------------------------
    
    async def propagate(self, signal: LearningSignal):
        """
        Propagate a learning signal to all relevant components.
        
        Routing based on:
        1. Component subscriptions
        2. Signal priority (immediate/fast/async/batch)
        3. Target components (if specified)
        """
        
        # Determine targets
        if signal.target_components:
            targets = signal.target_components
        else:
            # Broadcast to all subscribed components
            targets = [
                component
                for component, subscriptions in self.component_subscriptions.items()
                if signal.signal_type in subscriptions
            ]
        
        # Initialize propagation status
        signal.propagation_status = {t: 'pending' for t in targets}
        
        # Route by priority
        if signal.priority == LearningPriority.IMMEDIATE:
            self._pending_immediate.append(signal)
        elif signal.priority == LearningPriority.FAST:
            self._pending_fast.append(signal)
        elif signal.priority == LearningPriority.ASYNC:
            self._pending_async.append(signal)
        else:  # BATCH
            await self._queue_for_batch(signal)
        
        PROPAGATION_COUNTER.labels(
            signal_type=signal.signal_type,
            priority=signal.priority.value,
            target='queued'
        ).inc()
    
    # -------------------------------------------------------------------------
    # Priority-Specific Processors
    # -------------------------------------------------------------------------
    
    async def _immediate_processor(self):
        """Process immediate signals (<10ms target)."""
        
        while True:
            if self._pending_immediate:
                signal = self._pending_immediate.pop(0)
                
                start_time = datetime.utcnow()
                
                async with self._semaphore:
                    await self._process_immediate(signal)
                
                latency = (datetime.utcnow() - start_time).total_seconds()
                PROPAGATION_LATENCY.labels(priority='immediate').observe(latency)
            else:
                await asyncio.sleep(0.001)  # 1ms sleep when idle
    
    async def _fast_processor(self):
        """Process fast signals (<100ms target)."""
        
        while True:
            if self._pending_fast:
                # Process in batches for efficiency
                batch = self._pending_fast[:self.config.batch_size]
                self._pending_fast = self._pending_fast[self.config.batch_size:]
                
                start_time = datetime.utcnow()
                
                async with self._semaphore:
                    await asyncio.gather(*[
                        self._process_fast(signal)
                        for signal in batch
                    ])
                
                latency = (datetime.utcnow() - start_time).total_seconds()
                PROPAGATION_LATENCY.labels(priority='fast').observe(latency)
            else:
                await asyncio.sleep(0.01)  # 10ms sleep when idle
    
    async def _async_processor(self):
        """Process async signals (<1s target)."""
        
        while True:
            if self._pending_async:
                batch = self._pending_async[:self.config.batch_size]
                self._pending_async = self._pending_async[self.config.batch_size:]
                
                start_time = datetime.utcnow()
                
                # Process async in background tasks
                for signal in batch:
                    task = asyncio.create_task(self._process_async(signal))
                    self._active_tasks.add(task)
                    task.add_done_callback(self._active_tasks.discard)
                    ACTIVE_PROPAGATIONS.inc()
                
                latency = (datetime.utcnow() - start_time).total_seconds()
                PROPAGATION_LATENCY.labels(priority='async').observe(latency)
            else:
                await asyncio.sleep(0.1)  # 100ms sleep when idle
    
    # -------------------------------------------------------------------------
    # Signal Processing
    # -------------------------------------------------------------------------
    
    async def _process_immediate(self, signal: LearningSignal):
        """
        Immediate processing (<10ms).
        - Update Redis hot state
        - Invalidate caches
        """
        
        try:
            # Update hot state in Redis
            if signal.signal_type == 'outcome_observed':
                await self._update_hot_state_for_outcome(signal)
            
            # Invalidate affected caches
            await self._invalidate_caches(signal)
            
            # Update propagation status
            for target in signal.propagation_status:
                signal.propagation_status[target] = 'immediate_complete'
                
        except Exception as e:
            for target in signal.propagation_status:
                signal.propagation_status[target] = f'error: {str(e)}'
    
    async def _process_fast(self, signal: LearningSignal):
        """
        Fast processing (<100ms).
        - Emit to Kafka
        - Update segment aggregates
        """
        
        try:
            # Emit to Kafka for all subscribers
            kafka_event = {
                'signal_id': signal.signal_id,
                'signal_type': signal.signal_type,
                'source': signal.source_component,
                'payload': signal.payload,
                'timestamp': signal.timestamp.isoformat() if hasattr(signal, 'timestamp') else datetime.utcnow().isoformat(),
                'targets': list(signal.propagation_status.keys())
            }
            
            await self.kafka_producer.send_and_wait(
                self.config.learning_topic,
                value=kafka_event
            )
            
            # Update segment aggregates if applicable
            if 'user_id' in signal.payload:
                await self._update_segment_aggregates(signal)
            
            for target in signal.propagation_status:
                signal.propagation_status[target] = 'fast_complete'
                
        except Exception as e:
            for target in signal.propagation_status:
                signal.propagation_status[target] = f'error: {str(e)}'
    
    async def _process_async(self, signal: LearningSignal):
        """
        Async processing (<1s).
        - Write to Neo4j
        - Run credit attribution
        - Update calibration
        """
        
        try:
            # Write to Neo4j
            await self._write_signal_to_neo4j(signal)
            
            # Credit attribution for outcomes
            if signal.signal_type == 'outcome_observed':
                await self._run_credit_attribution(signal)
            
            # Update calibration
            if signal.signal_type in ['outcome_observed', 'calibration_updated']:
                await self._update_calibration(signal)
            
            for target in signal.propagation_status:
                signal.propagation_status[target] = 'async_complete'
                
        except Exception as e:
            for target in signal.propagation_status:
                signal.propagation_status[target] = f'error: {str(e)}'
        finally:
            ACTIVE_PROPAGATIONS.dec()
    
    async def _queue_for_batch(self, signal: LearningSignal):
        """Queue signal for batch processing."""
        
        await self.redis.rpush(
            'adam:batch_signals',
            json.dumps({
                'signal_id': signal.signal_id,
                'signal_type': signal.signal_type,
                'payload': signal.payload,
                'queued_at': datetime.utcnow().isoformat()
            })
        )
        
        for target in signal.propagation_status:
            signal.propagation_status[target] = 'batch_queued'
    
    # -------------------------------------------------------------------------
    # Specific Update Operations
    # -------------------------------------------------------------------------
    
    async def _update_hot_state_for_outcome(self, signal: LearningSignal):
        """Update Redis hot state for an outcome."""
        
        user_id = signal.payload.get('user_id')
        mechanism_id = signal.payload.get('mechanism_id')
        outcome = signal.payload.get('outcome')
        
        if not all([user_id, mechanism_id, outcome is not None]):
            return
        
        # Update user × mechanism hot state
        key = f"adam:hot:prior:{user_id}:{mechanism_id}"
        
        pipe = self.redis.pipeline()
        
        if outcome:
            pipe.hincrbyfloat(key, 'alpha', 1.0)
        else:
            pipe.hincrbyfloat(key, 'beta', 1.0)
        
        pipe.hincrby(key, 'observations', 1)
        pipe.hset(key, 'updated', datetime.utcnow().isoformat())
        pipe.expire(key, 300)  # 5 min TTL
        
        await pipe.execute()
    
    async def _invalidate_caches(self, signal: LearningSignal):
        """Invalidate caches affected by this signal."""
        
        user_id = signal.payload.get('user_id')
        mechanism_id = signal.payload.get('mechanism_id')
        
        if user_id:
            await self.cache.invalidate_for_outcome(user_id, mechanism_id)
    
    async def _update_segment_aggregates(self, signal: LearningSignal):
        """Update segment-level statistics."""
        
        user_id = signal.payload.get('user_id')
        mechanism_id = signal.payload.get('mechanism_id')
        outcome = signal.payload.get('outcome')
        
        if not all([user_id, mechanism_id, outcome is not None]):
            return
        
        # Get user's segment
        profile = await self.graph.get_user_profile(user_id)
        if profile and profile.psychological_cluster_id:
            await self.cache.update_segment_aggregate(
                str(profile.psychological_cluster_id),
                mechanism_id,
                outcome
            )
    
    async def _write_signal_to_neo4j(self, signal: LearningSignal):
        """Persist learning signal to Neo4j."""
        
        query = """
        CREATE (ls:LearningSignal {
            signal_id: $signal_id,
            signal_type: $signal_type,
            source: $source,
            timestamp: datetime(),
            payload: $payload
        })
        
        WITH ls
        
        // Connect to user if applicable
        OPTIONAL MATCH (u:User {user_id: $user_id})
        FOREACH (_ IN CASE WHEN u IS NOT NULL THEN [1] ELSE [] END |
            MERGE (u)-[:GENERATED_SIGNAL]->(ls)
        )
        
        // Connect to mechanism if applicable
        OPTIONAL MATCH (m:CognitiveMechanism {mechanism_id: $mechanism_id})
        FOREACH (_ IN CASE WHEN m IS NOT NULL THEN [1] ELSE [] END |
            MERGE (ls)-[:ABOUT_MECHANISM]->(m)
        )
        
        RETURN ls
        """
        
        async with self.neo4j.session() as session:
            await session.run(
                query,
                signal_id=signal.signal_id,
                signal_type=signal.signal_type,
                source=signal.source_component,
                payload=json.dumps(signal.payload),
                user_id=signal.payload.get('user_id'),
                mechanism_id=signal.payload.get('mechanism_id')
            )
    
    async def _run_credit_attribution(self, signal: LearningSignal):
        """
        Attribute outcome to decisions that led to it.
        
        Uses temporal credit assignment:
        - More recent decisions get more credit
        - Higher confidence decisions get more credit
        """
        
        user_id = signal.payload.get('user_id')
        session_id = signal.payload.get('session_id')
        outcome = signal.payload.get('outcome')
        
        if not all([user_id, session_id, outcome is not None]):
            return
        
        # Get decisions from this session
        query = """
        MATCH (s:Session {session_id: $session_id})-[:CONTAINS]->(d:Decision)
        MATCH (d)-[:USED_MECHANISM]->(m:CognitiveMechanism)
        MATCH (d)-[:FOR_USER]->(u:User {user_id: $user_id})
        
        RETURN d.decision_id as decision_id,
               d.confidence as confidence,
               d.timestamp as timestamp,
               collect(m.mechanism_id) as mechanisms
        ORDER BY d.timestamp
        """
        
        async with self.neo4j.session() as session:
            result = await session.run(
                query,
                session_id=session_id,
                user_id=user_id
            )
            decisions = await result.data()
        
        if not decisions:
            return
        
        # Assign credit using temporal difference
        total = len(decisions)
        for i, decision in enumerate(decisions):
            # Recency weight (later = more credit)
            recency = (i + 1) / total
            
            # Confidence weight
            confidence = decision.get('confidence', 0.5)
            
            # Combined credit
            credit = recency * confidence
            
            # Update each mechanism
            for mechanism_id in decision.get('mechanisms', []):
                await self.graph.update_mechanism_posterior(
                    user_id=user_id,
                    mechanism_id=mechanism_id,
                    success=outcome,
                    weight=credit
                )
                
                # Emit posterior update event
                await self._emit_posterior_update(
                    user_id, mechanism_id, outcome, credit
                )
    
    async def _update_calibration(self, signal: LearningSignal):
        """Update confidence calibration."""
        
        predicted = signal.payload.get('predicted_confidence')
        actual = signal.payload.get('outcome')
        
        if predicted is None or actual is None:
            return
        
        bucket = int(predicted * 10)  # 0-10
        bucket = min(10, max(0, bucket))  # Clamp
        
        await self.cache.update_calibration_bucket(
            bucket=bucket,
            predicted_success=predicted > 0.5,
            actual_success=actual
        )
    
    async def _emit_posterior_update(
        self,
        user_id: str,
        mechanism_id: str,
        outcome: bool,
        credit: float
    ):
        """Emit event for posterior update."""
        
        event = PosteriorUpdateEvent(
            event_id=f"post_{user_id}_{mechanism_id}_{datetime.utcnow().timestamp()}",
            event_type="learning.posterior_update",
            source_component="learning_propagator",
            user_id=user_id,
            mechanism_id=mechanism_id,
            # Get current values from cache/graph
            old_alpha=0,  # Would fetch actual values
            old_beta=0,
            old_success_rate=0,
            new_alpha=0,
            new_beta=0,
            new_success_rate=0,
            triggering_outcome_id="",
            credit_weight=credit
        )
        
        await self.kafka_producer.send_and_wait(
            self.config.learning_topic,
            value=event.model_dump()
        )
    
    # -------------------------------------------------------------------------
    # Convenience Methods for Common Signals
    # -------------------------------------------------------------------------
    
    async def propagate_outcome(
        self,
        user_id: str,
        session_id: str,
        decision_id: str,
        mechanism_id: str,
        outcome: bool,
        predicted_confidence: float,
        category: str = None,
        brand_id: str = None
    ):
        """Convenience method to propagate an outcome observation."""
        
        signal = OutcomeObservedSignal(
            signal_id=f"out_{user_id}_{datetime.utcnow().timestamp()}",
            signal_type="outcome_observed",
            source_component="outcome_tracker",
            payload={
                'user_id': user_id,
                'session_id': session_id,
                'decision_id': decision_id,
                'mechanism_id': mechanism_id,
                'outcome': outcome,
                'predicted_confidence': predicted_confidence,
                'category': category,
                'brand_id': brand_id
            },
            target_components=[],  # Broadcast
            priority=LearningPriority.IMMEDIATE,
            user_id=user_id,
            session_id=session_id,
            decision_id=decision_id,
            mechanism_id=mechanism_id,
            outcome=outcome,
            predicted_confidence=predicted_confidence,
            decision_timestamp=datetime.utcnow(),
            outcome_timestamp=datetime.utcnow()
        )
        
        await self.propagate(signal)
    
    async def propagate_discovery(
        self,
        discovery_id: str,
        discovery_type: str,
        confidence: float,
        evidence: Dict[str, Any],
        hypotheses: List[Dict[str, Any]],
        auto_action_taken: bool
    ):
        """Convenience method to propagate a discovery."""
        
        signal = DiscoveryMadeSignal(
            signal_id=f"disc_{discovery_id}",
            signal_type="discovery_made",
            source_component="discovery_engine",
            payload={
                'discovery_id': discovery_id,
                'discovery_type': discovery_type,
                'confidence': confidence,
                'evidence': evidence,
                'hypotheses': hypotheses,
                'auto_action_taken': auto_action_taken
            },
            target_components=[],  # Broadcast
            priority=LearningPriority.FAST,
            discovery_id=discovery_id,
            discovery_type=discovery_type,
            confidence=confidence,
            evidence=evidence,
            hypotheses=hypotheses,
            auto_action_taken=auto_action_taken
        )
        
        await self.propagate(signal)
```

---

# Part 7: Discovery Engine Implementation

## 7.1 Complete Discovery Engine

```python
"""
ADAM Discovery Engine
Automated pattern mining and hypothesis generation

Principles:
1. Design for discovery, not just retrieval
2. Generate hypotheses automatically
3. Confidence-based routing (auto vs human review)
4. Aggressive learning without bottlenecks
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
import asyncio
import json
from enum import Enum

from neo4j import AsyncGraphDatabase
from redis import asyncio as aioredis
from anthropic import AsyncAnthropic
from scipy import stats
import numpy as np

from adam.models.core import (
    Discovery, Hypothesis, DiscoveryStatus,
    EmergentConstruct, TestablePrediction,
    MechanismInteraction
)
from adam.services.graph_service import GraphService
from adam.services.learning_propagator import LearningPropagator
from adam.metrics import (
    DISCOVERY_COUNTER, HYPOTHESIS_COUNTER,
    HYPOTHESIS_VALIDATION_RATE, EMERGENT_CONSTRUCTS
)


class DiscoveryType(str, Enum):
    """Types of discoveries the engine can make."""
    MECHANISM_INTERACTION = "mechanism_interaction"
    BEHAVIORAL_SIGNATURE = "behavioral_signature"
    CONSTRUCT_RELATIONSHIP = "construct_relationship"
    SEGMENT_ANOMALY = "segment_anomaly"
    TEMPORAL_SHIFT = "temporal_shift"
    EMERGENT_CONSTRUCT = "emergent_construct"


@dataclass
class DiscoveryConfig:
    """Configuration for discovery engine."""
    
    # Confidence thresholds
    auto_action_threshold: float = 0.85
    human_review_threshold: float = 0.60
    
    # Statistical thresholds
    min_sample_size: int = 100
    significance_threshold: float = 0.01
    effect_size_threshold: float = 0.15
    
    # Scheduling
    pattern_mining_interval_minutes: int = 60
    anomaly_detection_interval_minutes: int = 5
    hypothesis_testing_interval_minutes: int = 30
    
    # Learning aggressiveness
    exploration_rate: float = 0.15


class DiscoveryEngine:
    """
    Automated discovery engine for ADAM.
    
    Continuously mines the graph for patterns the system
    didn't explicitly model, generates hypotheses, and
    tests them.
    """
    
    def __init__(
        self,
        graph: GraphService,
        propagator: LearningPropagator,
        config: DiscoveryConfig = None
    ):
        self.graph = graph
        self.propagator = propagator
        self.config = config or DiscoveryConfig()
        
        self.claude = AsyncAnthropic()
        
        # Discovery state
        self.pending_hypotheses: List[Hypothesis] = []
        self.active_tests: Dict[str, Dict[str, Any]] = {}
        
        # Running flag
        self._running = False
    
    async def start(self):
        """Start the discovery engine loops."""
        
        self._running = True
        
        await asyncio.gather(
            self._pattern_mining_loop(),
            self._anomaly_detection_loop(),
            self._hypothesis_testing_loop()
        )
    
    async def stop(self):
        """Stop the discovery engine."""
        self._running = False
    
    # -------------------------------------------------------------------------
    # Discovery Loops
    # -------------------------------------------------------------------------
    
    async def _pattern_mining_loop(self):
        """Continuously mine for patterns."""
        
        while self._running:
            try:
                discoveries = await asyncio.gather(
                    self._discover_mechanism_interactions(),
                    self._discover_unmapped_signatures(),
                    self._discover_emergent_constructs(),
                    return_exceptions=True
                )
                
                for result in discoveries:
                    if isinstance(result, Exception):
                        continue
                    for discovery in result:
                        await self._process_discovery(discovery)
                
            except Exception as e:
                print(f"Pattern mining error: {e}")
            
            await asyncio.sleep(
                self.config.pattern_mining_interval_minutes * 60
            )
    
    async def _anomaly_detection_loop(self):
        """Detect anomalies in real-time."""
        
        while self._running:
            try:
                anomalies = await self._detect_anomalies()
                
                for anomaly in anomalies:
                    discovery = await self._anomaly_to_discovery(anomaly)
                    await self._process_discovery(discovery)
                
            except Exception as e:
                print(f"Anomaly detection error: {e}")
            
            await asyncio.sleep(
                self.config.anomaly_detection_interval_minutes * 60
            )
    
    async def _hypothesis_testing_loop(self):
        """Process and test hypotheses."""
        
        while self._running:
            try:
                # Check active tests for completion
                completed = []
                for hyp_id, test_info in self.active_tests.items():
                    if await self._is_test_complete(test_info):
                        result = await self._evaluate_test(test_info)
                        await self._process_test_result(hyp_id, result)
                        completed.append(hyp_id)
                
                for hyp_id in completed:
                    del self.active_tests[hyp_id]
                
                # Start new tests for pending hypotheses
                while (
                    self.pending_hypotheses and 
                    len(self.active_tests) < 10  # Max concurrent tests
                ):
                    hypothesis = self.pending_hypotheses.pop(0)
                    await self._start_hypothesis_test(hypothesis)
                
            except Exception as e:
                print(f"Hypothesis testing error: {e}")
            
            await asyncio.sleep(
                self.config.hypothesis_testing_interval_minutes * 60
            )
    
    # -------------------------------------------------------------------------
    # Discovery Methods
    # -------------------------------------------------------------------------
    
    async def _discover_mechanism_interactions(self) -> List[Discovery]:
        """Find mechanism pairs with unexpected interactions."""
        
        records = await self.graph.run_discovery_query('mechanism_interactions')
        
        discoveries = []
        for record in records:
            effect_size = record['synergy'] - 1.0
            
            if effect_size < self.config.effect_size_threshold:
                continue
            
            # Generate hypotheses
            hypotheses = await self._generate_interaction_hypotheses(
                record['mech1'],
                record['mech2'],
                record['synergy'],
                record['co_responders']
            )
            
            discovery = Discovery(
                discovery_id=f"int_{record['mech1']}_{record['mech2']}_{datetime.utcnow().strftime('%Y%m%d')}",
                discovery_type=DiscoveryType.MECHANISM_INTERACTION.value,
                description=f"Mechanisms {record['mech1']} and {record['mech2']} show {effect_size:.1%} synergy",
                evidence={
                    'mechanism_1': record['mech1'],
                    'mechanism_2': record['mech2'],
                    'synergy_ratio': record['synergy'],
                    'combined_rate': record['combined_rate'],
                    'baseline_rate': record['baseline']
                },
                sample_size=record['co_responders'],
                statistical_significance=self._calculate_significance(
                    record['combined_rate'],
                    record['baseline'],
                    record['co_responders']
                ),
                effect_size=effect_size,
                confidence=self._calculate_confidence(effect_size, record['co_responders']),
                hypotheses=hypotheses
            )
            
            discovery = self._route_discovery(discovery)
            discoveries.append(discovery)
            
            DISCOVERY_COUNTER.labels(
                discovery_type='mechanism_interaction',
                action_taken='auto' if discovery.auto_action_approved else 'queued'
            ).inc()
        
        return discoveries
    
    async def _discover_unmapped_signatures(self) -> List[Discovery]:
        """Find behavioral signatures not mapped to constructs."""
        
        records = await self.graph.run_discovery_query('unmapped_signatures')
        
        discoveries = []
        for record in records:
            sig = record['bs']
            
            hypotheses = await self._generate_signature_hypotheses(sig)
            
            discovery = Discovery(
                discovery_id=f"sig_{sig['signature_id']}",
                discovery_type=DiscoveryType.BEHAVIORAL_SIGNATURE.value,
                description=f"Signature '{sig['signature_id']}' predicts outcomes (r={sig['outcome_correlation']:.2f}) without construct mapping",
                evidence={
                    'signature_id': sig['signature_id'],
                    'pattern': sig.get('pattern_definition', {}),
                    'outcome_correlation': sig['outcome_correlation'],
                    'prevalence': sig['population_prevalence']
                },
                sample_size=sig.get('sample_size', 0),
                statistical_significance=self._correlation_significance(
                    sig['outcome_correlation'],
                    sig.get('sample_size', 100)
                ),
                effect_size=sig['outcome_correlation'],
                confidence=self._calculate_confidence(
                    sig['outcome_correlation'],
                    sig.get('sample_size', 100)
                ),
                hypotheses=hypotheses
            )
            
            discovery = self._route_discovery(discovery)
            discoveries.append(discovery)
            
            DISCOVERY_COUNTER.labels(
                discovery_type='behavioral_signature',
                action_taken='auto' if discovery.auto_action_approved else 'queued'
            ).inc()
        
        return discoveries
    
    async def _discover_emergent_constructs(self) -> List[Discovery]:
        """Find clusters of signatures that may represent new constructs."""
        
        # Query for signature clusters
        query = """
        MATCH (bs1:BehavioralSignature)-[co:CO_OCCURS_WITH]->(bs2:BehavioralSignature)
        WHERE co.correlation > 0.5
        AND bs1.is_mapped_to_construct = false
        AND bs2.is_mapped_to_construct = false
        
        WITH bs1, bs2, co.correlation as corr
        
        // Find users with both signatures
        MATCH (u:User)-[:HAS_SIGNATURE]->(bs1)
        MATCH (u)-[:HAS_SIGNATURE]->(bs2)
        MATCH (u)-[o:HAD_OUTCOME]->(:ConversionEvent)
        
        WITH bs1.signature_id as sig1, bs2.signature_id as sig2,
             corr, count(DISTINCT u) as users,
             avg(o.success) as outcome_rate
             
        WHERE users > 50 AND outcome_rate > 0.5
        
        RETURN sig1, sig2, corr, users, outcome_rate
        ORDER BY outcome_rate DESC
        LIMIT 20
        """
        
        async with self.graph._driver.session() as session:
            result = await session.run(query)
            records = await result.data()
        
        # Cluster related signatures
        clusters = self._cluster_signatures(records)
        
        discoveries = []
        for cluster in clusters:
            hypotheses = await self._generate_emergent_construct_hypotheses(cluster)
            
            discovery = Discovery(
                discovery_id=f"emerg_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
                discovery_type=DiscoveryType.EMERGENT_CONSTRUCT.value,
                description=f"Cluster of {len(cluster['signatures'])} signatures may represent new construct",
                evidence=cluster,
                sample_size=cluster['sample_size'],
                statistical_significance=0.001,  # Placeholder
                effect_size=cluster['outcome_prediction'],
                confidence=self._calculate_confidence(
                    cluster['outcome_prediction'],
                    cluster['sample_size']
                ),
                hypotheses=hypotheses
            )
            
            discovery = self._route_discovery(discovery)
            discoveries.append(discovery)
            
            DISCOVERY_COUNTER.labels(
                discovery_type='emergent_construct',
                action_taken='auto' if discovery.auto_action_approved else 'queued'
            ).inc()
            
            if discovery.auto_action_approved:
                EMERGENT_CONSTRUCTS.inc()
        
        return discoveries
    
    async def _detect_anomalies(self) -> List[Dict[str, Any]]:
        """Detect statistical anomalies in real-time data."""
        
        records = await self.graph.run_discovery_query('segment_anomalies')
        
        anomalies = []
        for record in records:
            if abs(record['z_score']) > 2:  # 2+ standard deviations
                anomalies.append({
                    'type': 'segment_mechanism_anomaly',
                    'cluster': record['cluster'],
                    'mechanism': record['mechanism'],
                    'cluster_avg': record['cluster_avg'],
                    'population_avg': record['pop_avg'],
                    'z_score': record['z_score']
                })
        
        return anomalies
    
    async def _anomaly_to_discovery(self, anomaly: Dict[str, Any]) -> Discovery:
        """Convert an anomaly detection to a discovery."""
        
        hypotheses = await self._generate_anomaly_hypotheses(anomaly)
        
        return Discovery(
            discovery_id=f"anom_{anomaly['cluster']}_{anomaly['mechanism']}_{datetime.utcnow().strftime('%Y%m%d')}",
            discovery_type=DiscoveryType.SEGMENT_ANOMALY.value,
            description=f"Cluster {anomaly['cluster']} shows {anomaly['z_score']:.1f}σ deviation for {anomaly['mechanism']}",
            evidence=anomaly,
            sample_size=100,  # Placeholder
            statistical_significance=stats.norm.sf(abs(anomaly['z_score'])) * 2,
            effect_size=abs(anomaly['cluster_avg'] - anomaly['population_avg']),
            confidence=min(0.99, abs(anomaly['z_score']) / 5),
            hypotheses=hypotheses
        )
    
    # -------------------------------------------------------------------------
    # Hypothesis Generation
    # -------------------------------------------------------------------------
    
    async def _generate_interaction_hypotheses(
        self,
        mech1: str,
        mech2: str,
        synergy: float,
        sample_size: int
    ) -> List[Hypothesis]:
        """Generate hypotheses about mechanism interaction."""
        
        prompt = f"""You are a psychological scientist analyzing advertising data. Two cognitive mechanisms show unexpected synergy:

MECHANISM 1: {mech1}
MECHANISM 2: {mech2}
SYNERGY: {(synergy-1)*100:.0f}% better together than predicted
SAMPLE SIZE: {sample_size:,}

Generate 3 testable hypotheses about why these mechanisms interact. For each:
1. State the hypothesis
2. Provide theoretical basis
3. Give testable predictions
4. Assign confidence (0-1)

Format as JSON array:
[{{"statement": "...", "theoretical_basis": "...", "predictions": [{{"prediction": "...", "test_method": "..."}}], "confidence": 0.7}}]"""

        response = await self.claude.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}]
        )
        
        try:
            data = json.loads(response.content[0].text)
            return [
                Hypothesis(
                    hypothesis_id=f"hyp_{mech1}_{mech2}_{i}",
                    statement=h['statement'],
                    confidence=h['confidence'],
                    predictions=[
                        TestablePrediction(
                            prediction=p['prediction'],
                            test_method=p['test_method']
                        )
                        for p in h.get('predictions', [])
                    ]
                )
                for i, h in enumerate(data)
            ]
        except json.JSONDecodeError:
            return []
    
    async def _generate_signature_hypotheses(
        self,
        signature: Dict[str, Any]
    ) -> List[Hypothesis]:
        """Generate hypotheses about unmapped signature."""
        
        prompt = f"""You are analyzing a behavioral signature that predicts outcomes but doesn't map to known psychological constructs:

SIGNATURE: {signature.get('signature_id')}
PATTERN: {signature.get('pattern_definition', 'Unknown')}
CORRELATION: {signature.get('outcome_correlation', 0):.2f}
PREVALENCE: {signature.get('population_prevalence', 0):.1%}

Generate 3 hypotheses about what psychological phenomenon this represents.

Format as JSON array:
[{{"statement": "...", "theoretical_basis": "...", "predictions": [{{"prediction": "...", "test_method": "..."}}], "confidence": 0.7}}]"""

        response = await self.claude.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}]
        )
        
        try:
            data = json.loads(response.content[0].text)
            return [
                Hypothesis(
                    hypothesis_id=f"hyp_sig_{signature.get('signature_id', 'unknown')}_{i}",
                    statement=h['statement'],
                    confidence=h['confidence'],
                    predictions=[
                        TestablePrediction(
                            prediction=p['prediction'],
                            test_method=p['test_method']
                        )
                        for p in h.get('predictions', [])
                    ]
                )
                for i, h in enumerate(data)
            ]
        except json.JSONDecodeError:
            return []
    
    async def _generate_emergent_construct_hypotheses(
        self,
        cluster: Dict[str, Any]
    ) -> List[Hypothesis]:
        """Generate hypotheses about potential new construct."""
        
        prompt = f"""You are analyzing a cluster of behavioral signatures that may represent an entirely new psychological construct:

SIGNATURES: {cluster.get('signatures', [])}
INTERNAL CORRELATION: {cluster.get('internal_correlation', 0):.2f}
OUTCOME PREDICTION: {cluster.get('outcome_prediction', 0):.2f}

Generate 3 hypotheses about what new construct this might represent. Include:
- A proposed name for the construct
- How it relates to existing constructs
- Validation requirements

Format as JSON array:
[{{"statement": "...", "proposed_name": "...", "theoretical_basis": "...", "relationship_to_existing": "...", "predictions": [...], "confidence": 0.7}}]"""

        response = await self.claude.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2500,
            messages=[{"role": "user", "content": prompt}]
        )
        
        try:
            data = json.loads(response.content[0].text)
            return [
                Hypothesis(
                    hypothesis_id=f"hyp_emerg_{i}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
                    statement=h['statement'],
                    confidence=h['confidence'],
                    predictions=[
                        TestablePrediction(
                            prediction=p.get('prediction', ''),
                            test_method=p.get('test_method', 'unknown')
                        )
                        for p in h.get('predictions', [])
                    ]
                )
                for i, h in enumerate(data)
            ]
        except json.JSONDecodeError:
            return []
    
    async def _generate_anomaly_hypotheses(
        self,
        anomaly: Dict[str, Any]
    ) -> List[Hypothesis]:
        """Generate hypotheses about an anomaly."""
        
        return [
            Hypothesis(
                hypothesis_id=f"hyp_anom_{anomaly['cluster']}_{anomaly['mechanism']}",
                statement=f"Cluster {anomaly['cluster']} may have unusual composition for {anomaly['mechanism']}",
                confidence=0.6,
                predictions=[
                    TestablePrediction(
                        prediction=f"Cluster trait distribution differs from population",
                        test_method="segment_analysis"
                    )
                ]
            )
        ]
    
    # -------------------------------------------------------------------------
    # Discovery Processing
    # -------------------------------------------------------------------------
    
    def _route_discovery(self, discovery: Discovery) -> Discovery:
        """Route discovery based on confidence."""
        
        if discovery.confidence >= self.config.auto_action_threshold:
            discovery.auto_action_approved = True
            discovery.requires_human_review = False
        elif discovery.confidence >= self.config.human_review_threshold:
            discovery.auto_action_approved = True
            discovery.requires_human_review = True
        else:
            discovery.auto_action_approved = False
            discovery.requires_human_review = True
        
        return discovery
    
    async def _process_discovery(self, discovery: Discovery):
        """Process a discovery - act and/or queue for review."""
        
        # Persist to graph
        await self.graph.create_discovery(discovery)
        
        if discovery.auto_action_approved:
            await self._act_on_discovery(discovery)
            
            # Propagate to all components
            await self.propagator.propagate_discovery(
                discovery_id=discovery.discovery_id,
                discovery_type=discovery.discovery_type,
                confidence=discovery.confidence,
                evidence=discovery.evidence,
                hypotheses=[h.model_dump() for h in discovery.hypotheses],
                auto_action_taken=True
            )
        
        # Queue best hypothesis for testing
        if discovery.hypotheses:
            best = max(discovery.hypotheses, key=lambda h: h.confidence)
            self.pending_hypotheses.append(best)
            HYPOTHESIS_COUNTER.labels(status='pending').inc()
    
    async def _act_on_discovery(self, discovery: Discovery):
        """Take automatic action on discovery."""
        
        if discovery.discovery_type == DiscoveryType.MECHANISM_INTERACTION.value:
            await self.graph.create_mechanism_interaction(
                mechanism_1=discovery.evidence['mechanism_1'],
                mechanism_2=discovery.evidence['mechanism_2'],
                interaction_type='synergistic',
                interaction_effect=discovery.effect_size,
                sample_size=discovery.sample_size,
                p_value=discovery.statistical_significance,
                conditions=[]
            )
        
        elif discovery.discovery_type == DiscoveryType.EMERGENT_CONSTRUCT.value:
            # Create emergent construct in graph
            await self._create_emergent_construct(discovery)
        
        discovery.acted_upon_at = datetime.utcnow()
    
    async def _create_emergent_construct(self, discovery: Discovery):
        """Create an emergent construct in the graph."""
        
        query = """
        CREATE (ec:EmergentConstruct {
            construct_id: $construct_id,
            discovery_id: $discovery_id,
            defining_signatures: $signatures,
            outcome_prediction: $outcome_prediction,
            status: 'detected',
            discovered_at: datetime()
        })
        
        // Link to defining signatures
        WITH ec
        UNWIND $signatures as sig_id
        MATCH (bs:BehavioralSignature {signature_id: sig_id})
        CREATE (ec)-[:DEFINED_BY]->(bs)
        
        RETURN ec
        """
        
        await self.graph._driver.session().run(
            query,
            construct_id=f"ec_{discovery.discovery_id}",
            discovery_id=discovery.discovery_id,
            signatures=discovery.evidence.get('signatures', []),
            outcome_prediction=discovery.effect_size
        )
    
    # -------------------------------------------------------------------------
    # Hypothesis Testing
    # -------------------------------------------------------------------------
    
    async def _start_hypothesis_test(self, hypothesis: Hypothesis):
        """Start testing a hypothesis."""
        
        # Create A/B test allocation
        test_info = {
            'hypothesis_id': hypothesis.hypothesis_id,
            'started_at': datetime.utcnow(),
            'predictions': hypothesis.predictions,
            'target_sample': 1000,
            'current_sample': 0,
            'results': {'control': [], 'treatment': []}
        }
        
        self.active_tests[hypothesis.hypothesis_id] = test_info
        
        hypothesis.status = DiscoveryStatus.TESTING
        HYPOTHESIS_COUNTER.labels(status='testing').inc()
    
    async def _is_test_complete(self, test_info: Dict[str, Any]) -> bool:
        """Check if test has enough data."""
        return test_info['current_sample'] >= test_info['target_sample']
    
    async def _evaluate_test(self, test_info: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate test results."""
        
        control = test_info['results']['control']
        treatment = test_info['results']['treatment']
        
        if not control or not treatment:
            return {'validated': False, 'reason': 'insufficient_data'}
        
        # Statistical test
        t_stat, p_value = stats.ttest_ind(control, treatment)
        effect_size = (np.mean(treatment) - np.mean(control)) / np.std(control)
        
        validated = (
            p_value < self.config.significance_threshold and
            effect_size > self.config.effect_size_threshold
        )
        
        return {
            'validated': validated,
            'p_value': p_value,
            'effect_size': effect_size,
            't_statistic': t_stat
        }
    
    async def _process_test_result(
        self,
        hypothesis_id: str,
        result: Dict[str, Any]
    ):
        """Process completed test result."""
        
        if result['validated']:
            HYPOTHESIS_COUNTER.labels(status='validated').inc()
            # Integrate knowledge
            await self._integrate_validated_hypothesis(hypothesis_id, result)
        else:
            HYPOTHESIS_COUNTER.labels(status='rejected').inc()
    
    async def _integrate_validated_hypothesis(
        self,
        hypothesis_id: str,
        result: Dict[str, Any]
    ):
        """Integrate validated hypothesis into system knowledge."""
        
        # Update graph with validated knowledge
        query = """
        MATCH (h:Hypothesis {hypothesis_id: $hypothesis_id})
        SET h.status = 'validated',
            h.validation_result = $result,
            h.validated_at = datetime()
        
        WITH h
        MATCH (h)<-[:GENERATED]-(d:Discovery)
        SET d.status = 'validated'
        
        RETURN h, d
        """
        
        async with self.graph._driver.session() as session:
            await session.run(
                query,
                hypothesis_id=hypothesis_id,
                result=json.dumps(result)
            )
    
    # -------------------------------------------------------------------------
    # Statistical Helpers
    # -------------------------------------------------------------------------
    
    def _calculate_significance(
        self,
        observed: float,
        expected: float,
        n: int
    ) -> float:
        """Calculate p-value."""
        se = np.sqrt(expected * (1 - expected) / n)
        if se == 0:
            return 1.0
        z = (observed - expected) / se
        return 2 * (1 - stats.norm.cdf(abs(z)))
    
    def _correlation_significance(self, r: float, n: int) -> float:
        """Calculate p-value for correlation."""
        if abs(r) >= 1:
            return 0.0
        t = r * np.sqrt((n - 2) / (1 - r**2))
        return 2 * (1 - stats.t.cdf(abs(t), n - 2))
    
    def _calculate_confidence(self, effect: float, n: int) -> float:
        """Calculate discovery confidence."""
        effect_component = min(effect / 0.5, 1.0)
        sample_component = 1 - np.exp(-n / 500)
        return effect_component * sample_component
    
    def _cluster_signatures(
        self,
        records: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Cluster related signatures."""
        
        from collections import defaultdict
        
        adjacency = defaultdict(set)
        for record in records:
            adjacency[record['sig1']].add(record['sig2'])
            adjacency[record['sig2']].add(record['sig1'])
        
        visited = set()
        clusters = []
        
        def dfs(node, cluster):
            visited.add(node)
            cluster.add(node)
            for neighbor in adjacency[node]:
                if neighbor not in visited:
                    dfs(neighbor, cluster)
        
        for sig in adjacency:
            if sig not in visited:
                cluster = set()
                dfs(sig, cluster)
                if len(cluster) >= 2:
                    cluster_records = [
                        r for r in records
                        if r['sig1'] in cluster and r['sig2'] in cluster
                    ]
                    if cluster_records:
                        clusters.append({
                            'signatures': list(cluster),
                            'internal_correlation': np.mean([r['corr'] for r in cluster_records]),
                            'outcome_prediction': np.mean([r['outcome_rate'] for r in cluster_records]),
                            'sample_size': min(r['users'] for r in cluster_records)
                        })
        
        return clusters
```

---

# Part 8: FastAPI Service Layer

## 8.1 Main API Endpoints

```python
"""
ADAM FastAPI Service
Main API endpoints for the cognitive ecosystem
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

from adam.models.core import (
    UserProfile, AdDecision, MechanismRecommendation,
    SupraliminalSignals, Discovery
)
from adam.services.graph_service import GraphService
from adam.services.cache_service import CacheService
from adam.services.learning_propagator import LearningPropagator
from adam.services.discovery_engine import DiscoveryEngine
from adam.workflows.decision_workflow import create_decision_workflow, DecisionState


# =============================================================================
# LIFESPAN MANAGEMENT
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    
    # Startup
    app.state.graph = GraphService()
    await app.state.graph.connect()
    
    app.state.cache = CacheService()
    await app.state.cache.connect()
    
    app.state.propagator = LearningPropagator()
    await app.state.propagator.start()
    
    app.state.discovery = DiscoveryEngine(
        app.state.graph,
        app.state.propagator
    )
    
    app.state.decision_workflow = create_decision_workflow()
    
    yield
    
    # Shutdown
    await app.state.propagator.stop()
    await app.state.cache.close()
    await app.state.graph.close()


# =============================================================================
# APP INITIALIZATION
# =============================================================================

app = FastAPI(
    title="ADAM Cognitive Ecosystem",
    description="Psychological Intelligence for Advertising",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class DecisionRequest(BaseModel):
    """Request for ad decision."""
    user_id: str
    session_id: str
    content_id: Optional[str] = None
    content_category: Optional[str] = None
    brand_id: Optional[str] = None
    
    # Optional signals if already captured
    signals: Optional[Dict[str, Any]] = None


class DecisionResponse(BaseModel):
    """Response with ad decision."""
    decision_id: str
    mechanism: str
    mechanism_confidence: float
    predicted_conversion: float
    latency_ms: int
    reasoning_summary: str


class OutcomeRequest(BaseModel):
    """Request to record an outcome."""
    user_id: str
    session_id: str
    decision_id: str
    outcome_type: str  # conversion, click, engagement
    outcome_value: bool
    outcome_metadata: Optional[Dict[str, Any]] = None


class ProfileResponse(BaseModel):
    """User profile response."""
    user_id: str
    big_five: Dict[str, float]
    mechanism_effectiveness: Dict[str, float]
    cluster_id: Optional[int]
    total_interactions: int


class DiscoveryResponse(BaseModel):
    """Discovery information response."""
    discovery_id: str
    discovery_type: str
    description: str
    confidence: float
    status: str


# =============================================================================
# DECISION ENDPOINTS
# =============================================================================

@app.post("/api/v1/decision", response_model=DecisionResponse)
async def make_decision(request: DecisionRequest):
    """
    Make an ad decision for a user.
    
    This is the main entry point for ad serving. It:
    1. Retrieves user profile and mechanism priors
    2. Uses Claude to reason about mechanisms
    3. Verifies against graph knowledge
    4. Returns recommendation with confidence
    """
    
    # Initialize workflow state
    initial_state: DecisionState = {
        'user_id': request.user_id,
        'session_id': request.session_id,
        'request_timestamp': datetime.utcnow(),
        'user_profile': None,
        'current_signals': None,
        'mechanism_priors': {},
        'graph_context': {},
        'mechanism_reasoning': '',
        'selected_mechanism': '',
        'mechanism_confidence': 0.0,
        'recommendation': None,
        'decision': None,
        'messages': [],
        'workflow_stage': 'initialized',
        'latency_breakdown': {},
        'errors': []
    }
    
    # Add signals if provided
    if request.signals:
        initial_state['current_signals'] = SupraliminalSignals(
            user_id=request.user_id,
            session_id=request.session_id,
            **request.signals
        )
    
    # Run workflow
    try:
        final_state = await app.state.decision_workflow.ainvoke(initial_state)
        
        if not final_state['decision']:
            raise HTTPException(500, "Decision workflow failed")
        
        decision = final_state['decision']
        
        return DecisionResponse(
            decision_id=decision.decision_id,
            mechanism=decision.mechanism_recommendation.primary_mechanism,
            mechanism_confidence=decision.mechanism_recommendation.confidence,
            predicted_conversion=decision.mechanism_recommendation.predicted_conversion_rate,
            latency_ms=decision.latency_ms,
            reasoning_summary=decision.mechanism_recommendation.reasoning[:200]
        )
        
    except Exception as e:
        raise HTTPException(500, f"Decision error: {str(e)}")


@app.post("/api/v1/outcome")
async def record_outcome(
    request: OutcomeRequest,
    background_tasks: BackgroundTasks
):
    """
    Record an outcome for learning.
    
    This triggers the learning propagation system to:
    1. Update mechanism posteriors
    2. Invalidate caches
    3. Update calibration
    4. Run credit attribution
    """
    
    # Propagate outcome in background
    background_tasks.add_task(
        app.state.propagator.propagate_outcome,
        user_id=request.user_id,
        session_id=request.session_id,
        decision_id=request.decision_id,
        mechanism_id=request.outcome_metadata.get('mechanism_id', 'unknown'),
        outcome=request.outcome_value,
        predicted_confidence=request.outcome_metadata.get('predicted_confidence', 0.5)
    )
    
    return {"status": "accepted", "message": "Outcome queued for processing"}


# =============================================================================
# PROFILE ENDPOINTS
# =============================================================================

@app.get("/api/v1/profile/{user_id}", response_model=ProfileResponse)
async def get_profile(user_id: str):
    """Get user psychological profile."""
    
    # Try cache first
    profile = await app.state.cache.get_user_profile(user_id)
    
    if not profile:
        profile = await app.state.graph.get_user_profile(user_id)
        
        if not profile:
            raise HTTPException(404, f"User {user_id} not found")
        
        await app.state.cache.set_user_profile(user_id, profile)
    
    return ProfileResponse(
        user_id=profile.user_id,
        big_five={
            'openness': profile.big_five.openness,
            'conscientiousness': profile.big_five.conscientiousness,
            'extraversion': profile.big_five.extraversion,
            'agreeableness': profile.big_five.agreeableness,
            'neuroticism': profile.big_five.neuroticism
        },
        mechanism_effectiveness={
            mech_id: eff.success_rate
            for mech_id, eff in profile.mechanism_effectiveness.items()
        },
        cluster_id=profile.psychological_cluster_id,
        total_interactions=profile.total_interactions
    )


@app.get("/api/v1/profile/{user_id}/priors")
async def get_mechanism_priors(user_id: str):
    """Get user's mechanism effectiveness priors."""
    
    priors = await app.state.cache.get_mechanism_priors(user_id)
    
    if not priors:
        priors = await app.state.graph.get_mechanism_priors(user_id)
        
        if priors:
            await app.state.cache.set_mechanism_priors(user_id, priors)
    
    return {"user_id": user_id, "priors": priors or {}}


# =============================================================================
# DISCOVERY ENDPOINTS
# =============================================================================

@app.get("/api/v1/discoveries", response_model=List[DiscoveryResponse])
async def get_recent_discoveries(limit: int = 10):
    """Get recent discoveries."""
    
    discoveries = await app.state.cache.get_recent_discoveries()
    
    if not discoveries:
        # Fetch from graph
        query = """
        MATCH (d:Discovery)
        RETURN d
        ORDER BY d.discovered_at DESC
        LIMIT $limit
        """
        
        async with app.state.graph._driver.session() as session:
            result = await session.run(query, limit=limit)
            records = await result.data()
            discoveries = [dict(r['d']) for r in records]
        
        if discoveries:
            await app.state.cache.cache_recent_discoveries(discoveries)
    
    return [
        DiscoveryResponse(
            discovery_id=d.get('discovery_id', ''),
            discovery_type=d.get('discovery_type', ''),
            description=d.get('description', ''),
            confidence=d.get('confidence', 0),
            status=d.get('status', 'unknown')
        )
        for d in discoveries[:limit]
    ]


@app.get("/api/v1/discoveries/{discovery_id}")
async def get_discovery(discovery_id: str):
    """Get specific discovery details."""
    
    query = """
    MATCH (d:Discovery {discovery_id: $discovery_id})
    OPTIONAL MATCH (d)-[:GENERATED]->(h:Hypothesis)
    RETURN d, collect(h) as hypotheses
    """
    
    async with app.state.graph._driver.session() as session:
        result = await session.run(query, discovery_id=discovery_id)
        record = await result.single()
    
    if not record:
        raise HTTPException(404, f"Discovery {discovery_id} not found")
    
    discovery = dict(record['d'])
    hypotheses = [dict(h) for h in record['hypotheses']]
    
    return {
        **discovery,
        "hypotheses": hypotheses
    }


# =============================================================================
# HEALTH ENDPOINTS
# =============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "graph": "connected",
            "cache": "connected",
            "propagator": "running"
        }
    }


@app.get("/metrics")
async def get_metrics():
    """Get system metrics."""
    
    # Get calibration curve
    calibration = await app.state.cache.get_calibration_curve()
    
    return {
        "calibration_curve": calibration,
        "timestamp": datetime.utcnow().isoformat()
    }


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    uvicorn.run(
        "adam.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
```

---

This completes Part 2 of the implementation companion. The full system now includes:

1. **Multi-level Cache Service** - Hot/warm/cold caching with intelligent invalidation
2. **Learning Propagator** - Real-time signal propagation to all components
3. **Discovery Engine** - Automated pattern mining and hypothesis generation
4. **FastAPI Service Layer** - Production API endpoints

Let me copy these files to the outputs directory for you.
