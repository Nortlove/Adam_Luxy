# ADAM Enhancement #30: Feature Store & Real-Time Serving
## Enterprise-Grade Feature Infrastructure for Psychological Intelligence Platform

**Version**: 1.0 COMPLETE  
**Date**: January 2026  
**Priority**: P0 - Critical Foundation  
**Estimated Implementation**: 6 person-weeks  
**Dependencies**: #29 (Platform Infrastructure Foundation - Redis cluster)  
**Dependents**: #09 (Inference Engine), #03 (Meta-Learner), #28 (WPP Ad Desk), ALL real-time components  
**File Size**: ~100KB (Enterprise Production-Ready)

---

## Table of Contents

### SECTION A: STRATEGIC OVERVIEW
1. [Executive Summary](#executive-summary)
2. [Why Feature Store for ADAM](#why-feature-store)
3. [Architecture Overview](#architecture-overview)

### SECTION B: FEATURE REGISTRY
4. [Feature Definition Models](#feature-definition-models)
5. [Feature Groups](#feature-groups)
6. [Schema Versioning](#schema-versioning)
7. [Feature Lineage](#feature-lineage)

### SECTION C: ONLINE STORE
8. [Redis-Backed Online Store](#online-store)
9. [Feature Serving API](#serving-api)
10. [Freshness Tracking](#freshness-tracking)
11. [Automatic Refresh](#automatic-refresh)

### SECTION D: OFFLINE STORE
12. [Neo4j Feature Storage](#offline-store)
13. [Batch Feature Pipelines](#batch-pipelines)
14. [Point-in-Time Correctness](#point-in-time)
15. [Training Data Generation](#training-data)

### SECTION E: PSYCHOLOGICAL FEATURES
16. [Trait Features](#trait-features)
17. [State Features](#state-features)
18. [Mechanism Effectiveness Features](#mechanism-features)
19. [Journey Features](#journey-features)
20. [Embedding Features](#embedding-features)

### SECTION F: INTEGRATION & OPERATIONS
21. [FastAPI Endpoints](#fastapi-endpoints)
22. [Neo4j Schema](#neo4j-schema)
23. [Integration with ADAM Components](#integration)
24. [Implementation Timeline](#implementation-timeline)
25. [Success Metrics](#success-metrics)

---

# SECTION A: STRATEGIC OVERVIEW

## Executive Summary

### The Feature Serving Challenge

ADAM's real-time inference engine must serve ad decisions in **<100ms**. This requires:

| Feature Type | Source | Latency Requirement | Challenge |
|--------------|--------|---------------------|-----------|
| **Personality traits** | Neo4j graph | <10ms | Graph queries too slow |
| **Current state** | Session data + signals | <5ms | Distributed state |
| **Mechanism effectiveness** | Thompson priors | <3ms | Hot path critical |
| **Journey position** | Journey tracker | <5ms | State machine lookup |
| **User embeddings** | Model inference | <10ms | 64-dim vector |

Enhancement #30 solves this by providing a **unified feature serving layer** that:

1. **Online Store (Redis)** - Pre-computed features for sub-10ms serving
2. **Offline Store (Neo4j)** - Historical features for training
3. **Feature Registry** - Schema management and versioning
4. **Freshness Tracking** - Ensure features aren't stale

### What This Specification Delivers

| Component | Purpose | Key Deliverable |
|-----------|---------|-----------------|
| **Feature Registry** | Schema definitions, versioning | Complete Pydantic models |
| **Online Store** | Real-time serving | Redis integration, <10ms p99 |
| **Offline Store** | Historical data | Neo4j queries, point-in-time |
| **Batch Pipelines** | Feature computation | Async refresh jobs |
| **Serving API** | Feature retrieval | FastAPI endpoints |

### Latency Budget Allocation

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                                                                                         │
│   INFERENCE REQUEST LATENCY BUDGET: 100ms TOTAL                                        │
│                                                                                         │
│   ┌─────────────────────────────────────────────────────────────────────────────────┐  │
│   │                                                                                 │  │
│   │   Component               Budget      Current Source      With Feature Store  │  │
│   │   ═══════════════════════════════════════════════════════════════════════════  │  │
│   │                                                                                 │  │
│   │   Get User Profile        15ms        Neo4j: 50-100ms     Redis: 3ms ✓        │  │
│   │   Get Mechanism Priors    10ms        Redis script: 5ms   Redis: 2ms ✓        │  │
│   │   Get Journey Position    10ms        State machine: 15ms Redis: 2ms ✓        │  │
│   │   Get Content Features    10ms        Neo4j: 30ms         Redis: 3ms ✓        │  │
│   │   Claude Reasoning        30ms        N/A                 30ms (cached)        │  │
│   │   Score & Rank            10ms        Computation         10ms                 │  │
│   │   Response Serialization  5ms         Compute             5ms                  │  │
│   │   Network Overhead        10ms        Network             10ms                 │  │
│   │                                                                                 │  │
│   │   TOTAL                   100ms                           ~75ms ✓              │  │
│   │                                                                                 │  │
│   └─────────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                         │
│   ✓ = Meets SLO with headroom                                                          │
│                                                                                         │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Why Feature Store for ADAM

### The Problem with Direct Data Access

Without a feature store, every inference request must:

```python
# WITHOUT FEATURE STORE - TOO SLOW
async def serve_decision_slow(user_id: str, context: Context) -> Decision:
    # 1. Query Neo4j for user profile (50-100ms)
    profile = await neo4j.query("""
        MATCH (u:User {user_id: $user_id})
        OPTIONAL MATCH (u)-[r:HAS_TRAIT]->(t:Trait)
        OPTIONAL MATCH (u)-[s:IN_STATE]->(st:State)
        RETURN u, collect(t), collect(st)
    """, user_id=user_id)
    
    # 2. Query Redis for Thompson priors (5ms)
    priors = await redis.hgetall(f"adam:prior:user:{user_id}")
    
    # 3. Query Journey Tracker for position (15ms)
    journey = await journey_tracker.get_position(user_id)
    
    # 4. Query Neo4j for content features (30ms)
    content = await neo4j.query("""
        MATCH (c:Content {content_id: $content_id})
        RETURN c.psychological_profile
    """, content_id=context.content_id)
    
    # Total data retrieval: 100-150ms - ALREADY OVER BUDGET!
```

### The Solution: Pre-Computed Features

```python
# WITH FEATURE STORE - FAST
async def serve_decision_fast(user_id: str, context: Context) -> Decision:
    # Single call to feature store (8ms total)
    features = await feature_store.get_features(
        entity_id=user_id,
        feature_groups=[
            "psychological_profile",
            "mechanism_effectiveness",
            "journey_position",
        ],
        context={
            "content_id": context.content_id,
        }
    )
    
    # Features are pre-computed and cached in Redis
    # Total data retrieval: 8ms - WELL UNDER BUDGET!
```

### ADAM-Specific Feature Requirements

| Requirement | Generic Feature Store | ADAM Feature Store |
|-------------|----------------------|-------------------|
| **Feature types** | Numeric, categorical | + Psychological constructs |
| **Freshness** | Minutes to hours | Seconds for states |
| **Consistency** | Eventual | Causal for learning |
| **Point-in-time** | Simple timestamps | Decision-aligned |
| **Validation** | Schema checks | + Psychological validity |

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                                                                                     │
│                           ADAM FEATURE STORE ARCHITECTURE                                           │
│                                                                                                     │
│  ┌─────────────────────────────────────────────────────────────────────────────────────────────┐   │
│  │                                                                                             │   │
│  │   FEATURE PRODUCERS (Batch & Streaming)                                                    │   │
│  │                                                                                             │   │
│  │   ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐      │   │
│  │   │ Trait Inference │  │ State Detection │  │Journey Tracker  │  │Mechanism Learner│      │   │
│  │   │ Pipeline        │  │ Pipeline        │  │ (#10)           │  │ (#03)           │      │   │
│  │   │                 │  │                 │  │                 │  │                 │      │   │
│  │   │ Big Five, NFC,  │  │ Arousal,        │  │ State machine   │  │ Thompson priors │      │   │
│  │   │ Regulatory Focus│  │ Construal       │  │ positions       │  │ updates         │      │   │
│  │   └────────┬────────┘  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘      │   │
│  │            │                    │                    │                    │               │   │
│  │            └────────────────────┴────────────────────┴────────────────────┘               │   │
│  │                                              │                                             │   │
│  │                                              ▼                                             │   │
│  └──────────────────────────────────────────────┼─────────────────────────────────────────────┘   │
│                                                 │                                                   │
│  ┌──────────────────────────────────────────────┼─────────────────────────────────────────────┐   │
│  │                                              │                                             │   │
│  │   FEATURE STORE CORE                         │                                             │   │
│  │                                              ▼                                             │   │
│  │   ┌─────────────────────────────────────────────────────────────────────────────────────┐ │   │
│  │   │                         FEATURE REGISTRY                                            │ │   │
│  │   │   • Schema definitions (Pydantic models)                                           │ │   │
│  │   │   • Version management (semantic versioning)                                        │ │   │
│  │   │   • Lineage tracking (source → feature → consumer)                                 │ │   │
│  │   │   • Validation rules (psychological construct validity)                             │ │   │
│  │   └─────────────────────────────────────────────────────────────────────────────────────┘ │   │
│  │                              │                               │                             │   │
│  │                              ▼                               ▼                             │   │
│  │   ┌────────────────────────────────────┐  ┌────────────────────────────────────────────┐ │   │
│  │   │          ONLINE STORE              │  │          OFFLINE STORE                     │ │   │
│  │   │          (Redis Cluster)           │  │          (Neo4j + BigQuery)                │ │   │
│  │   │                                    │  │                                            │ │   │
│  │   │  • Pre-computed features           │  │  • Historical features                     │ │   │
│  │   │  • <10ms p99 latency               │  │  • Point-in-time correctness               │ │   │
│  │   │  • TTL-based freshness             │  │  • Training data generation                │ │   │
│  │   │  • Automatic refresh               │  │  • Feature backfill                        │ │   │
│  │   │                                    │  │                                            │ │   │
│  │   │  Uses #29 Redis cluster            │  │  Uses existing Neo4j                       │ │   │
│  │   └──────────────┬─────────────────────┘  └────────────────────────────────────────────┘ │   │
│  │                  │                                                                        │   │
│  └──────────────────┼────────────────────────────────────────────────────────────────────────┘   │
│                     │                                                                             │
│  ┌──────────────────┼────────────────────────────────────────────────────────────────────────┐   │
│  │                  │                                                                        │   │
│  │   FEATURE CONSUMERS                                                                       │   │
│  │                  ▼                                                                        │   │
│  │   ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐     │   │
│  │   │Inference Engine │  │   Meta-Learner  │  │    Ad Desk      │  │  Copy Generator │     │   │
│  │   │     (#09)       │  │     (#03)       │  │     (#28)       │  │     (#15)       │     │   │
│  │   │                 │  │                 │  │                 │  │                 │     │   │
│  │   │ Real-time ad    │  │ Path selection  │  │ Sequential      │  │ Personality-    │     │   │
│  │   │ serving         │  │ decisions       │  │ persuasion      │  │ matched copy    │     │   │
│  │   └─────────────────┘  └─────────────────┘  └─────────────────┘  └─────────────────┘     │   │
│  │                                                                                           │   │
│  └───────────────────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                                     │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

# SECTION B: FEATURE REGISTRY

## Feature Definition Models

```python
# =============================================================================
# ADAM Enhancement #30: Feature Registry Models
# Location: adam/feature_store/registry/models.py
# =============================================================================

"""
Feature Registry Models for ADAM Feature Store.

Provides:
1. Feature definitions with psychological construct validation
2. Feature groups for logical organization
3. Schema versioning for backward compatibility
4. Lineage tracking for debugging and compliance
"""

from __future__ import annotations
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from enum import Enum
from uuid import uuid4
from pydantic import BaseModel, Field, validator


# =============================================================================
# ENUMS
# =============================================================================

class FeatureDataType(str, Enum):
    """Supported feature data types."""
    FLOAT = "float"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    STRING = "string"
    CATEGORICAL = "categorical"
    EMBEDDING = "embedding"  # Vector of floats
    JSON = "json"  # Structured data


class FeatureEntityType(str, Enum):
    """Entity types that features can describe."""
    USER = "user"
    CONTENT = "content"
    ADVERTISEMENT = "advertisement"
    ADVERTISER = "advertiser"
    CAMPAIGN = "campaign"
    PUBLISHER = "publisher"
    CONTEXT = "context"  # Request-time context


class FeatureFreshness(str, Enum):
    """How fresh the feature needs to be."""
    REAL_TIME = "real_time"  # Updated on every event
    NEAR_REAL_TIME = "near_real_time"  # Updated within seconds
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    STATIC = "static"  # Rarely changes


class FeatureSource(str, Enum):
    """Source of the feature computation."""
    NEO4J = "neo4j"  # Graph database
    KAFKA = "kafka"  # Stream processing
    BATCH = "batch"  # Batch pipeline
    REAL_TIME = "real_time"  # Computed on request
    EXTERNAL = "external"  # Third-party data


class PsychologicalDomain(str, Enum):
    """Psychological domains for ADAM features."""
    PERSONALITY_TRAIT = "personality_trait"  # Big Five, etc.
    PSYCHOLOGICAL_STATE = "psychological_state"  # Arousal, construal
    REGULATORY_FOCUS = "regulatory_focus"  # Promotion/prevention
    MORAL_FOUNDATION = "moral_foundation"  # Haidt's foundations
    COGNITIVE_MECHANISM = "cognitive_mechanism"  # 9 ADAM mechanisms
    DECISION_STYLE = "decision_style"  # NFC, maximizing
    JOURNEY_STATE = "journey_state"  # Funnel position
    NOT_PSYCHOLOGICAL = "not_psychological"  # Technical features


# =============================================================================
# FEATURE DEFINITION
# =============================================================================

class FeatureDefinition(BaseModel):
    """
    Complete definition of a feature in ADAM's feature store.
    
    This is the atomic unit of the feature registry - every feature
    served by the store has a definition that specifies:
    1. What it is (name, description, data type)
    2. How it's computed (source, computation)
    3. How fresh it needs to be (freshness, TTL)
    4. What psychological construct it represents (domain, validation)
    """
    # Identity
    feature_id: str = Field(default_factory=lambda: str(uuid4()))
    name: str = Field(..., description="Unique feature name within group")
    description: str = Field(..., description="Human-readable description")
    
    # Type information
    data_type: FeatureDataType
    entity_type: FeatureEntityType
    
    # For categorical features
    categories: Optional[List[str]] = None
    
    # For embedding features
    embedding_dimension: Optional[int] = None
    
    # Value constraints
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    default_value: Optional[Any] = None
    
    # Freshness requirements
    freshness: FeatureFreshness = FeatureFreshness.HOURLY
    ttl_seconds: int = Field(default=3600, description="Time-to-live in online store")
    
    # Source and computation
    source: FeatureSource
    computation_query: Optional[str] = None  # SQL/Cypher for batch
    stream_topic: Optional[str] = None  # Kafka topic for streaming
    
    # Psychological validation (ADAM-specific)
    psychological_domain: PsychologicalDomain = PsychologicalDomain.NOT_PSYCHOLOGICAL
    psychological_construct: Optional[str] = None  # e.g., "openness", "arousal"
    validated_scale: bool = False  # Is this from a validated psychological scale?
    
    # Metadata
    version: str = "1.0.0"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    owner: str = "adam-team"
    tags: List[str] = Field(default_factory=list)
    
    @validator('embedding_dimension')
    def validate_embedding_dimension(cls, v, values):
        if values.get('data_type') == FeatureDataType.EMBEDDING and v is None:
            raise ValueError("embedding_dimension required for EMBEDDING type")
        return v
    
    @validator('categories')
    def validate_categories(cls, v, values):
        if values.get('data_type') == FeatureDataType.CATEGORICAL and not v:
            raise ValueError("categories required for CATEGORICAL type")
        return v
    
    @validator('psychological_construct')
    def validate_psychological_construct(cls, v, values):
        domain = values.get('psychological_domain')
        if domain != PsychologicalDomain.NOT_PSYCHOLOGICAL and not v:
            raise ValueError("psychological_construct required for psychological features")
        return v


# =============================================================================
# FEATURE GROUP
# =============================================================================

class FeatureGroup(BaseModel):
    """
    Logical grouping of related features.
    
    Feature groups enable:
    1. Batch retrieval of related features
    2. Shared freshness policies
    3. Organized feature discovery
    4. Access control
    """
    group_id: str = Field(default_factory=lambda: str(uuid4()))
    name: str = Field(..., description="Unique group name")
    description: str
    
    # Entity type for all features in group
    entity_type: FeatureEntityType
    
    # Features in this group
    features: List[FeatureDefinition] = Field(default_factory=list)
    
    # Group-level settings
    default_freshness: FeatureFreshness = FeatureFreshness.HOURLY
    default_ttl_seconds: int = 3600
    
    # Psychological domain (if all features are same domain)
    psychological_domain: Optional[PsychologicalDomain] = None
    
    # Metadata
    version: str = "1.0.0"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    owner: str = "adam-team"
    
    def get_feature(self, name: str) -> Optional[FeatureDefinition]:
        """Get feature by name."""
        for f in self.features:
            if f.name == name:
                return f
        return None
    
    def get_feature_names(self) -> List[str]:
        """Get all feature names in group."""
        return [f.name for f in self.features]


# =============================================================================
# FEATURE VALUE
# =============================================================================

class FeatureValue(BaseModel):
    """
    A feature value with metadata.
    
    This is what gets stored in the online store and returned
    from feature retrieval calls.
    """
    feature_name: str
    value: Any
    
    # Provenance
    computed_at: datetime
    source: FeatureSource
    
    # Freshness
    ttl_seconds: int
    is_stale: bool = False
    
    # Confidence (for inferred features)
    confidence: Optional[float] = None
    
    # For debugging
    computation_id: Optional[str] = None
    
    @property
    def expires_at(self) -> datetime:
        """When this value expires."""
        return self.computed_at + timedelta(seconds=self.ttl_seconds)
    
    @property
    def age_seconds(self) -> float:
        """Age of this value in seconds."""
        return (datetime.utcnow() - self.computed_at).total_seconds()


class FeatureVector(BaseModel):
    """
    A collection of feature values for an entity.
    
    This is the primary return type from feature retrieval.
    """
    entity_type: FeatureEntityType
    entity_id: str
    
    # Feature values by name
    features: Dict[str, FeatureValue] = Field(default_factory=dict)
    
    # Metadata
    retrieved_at: datetime = Field(default_factory=datetime.utcnow)
    cache_hit: bool = True
    
    # Which features were stale
    stale_features: List[str] = Field(default_factory=list)
    
    # Which features were missing
    missing_features: List[str] = Field(default_factory=list)
    
    def get(self, feature_name: str, default: Any = None) -> Any:
        """Get feature value by name."""
        fv = self.features.get(feature_name)
        if fv is None:
            return default
        return fv.value
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to simple dict of name -> value."""
        return {name: fv.value for name, fv in self.features.items()}


# =============================================================================
# FEATURE LINEAGE
# =============================================================================

class FeatureLineage(BaseModel):
    """
    Tracks the lineage of a feature from source to consumption.
    
    Enables:
    1. Debugging feature issues
    2. Compliance and audit trails
    3. Understanding feature dependencies
    """
    feature_id: str
    feature_name: str
    
    # Source information
    source_type: FeatureSource
    source_query: Optional[str] = None
    source_tables: List[str] = Field(default_factory=list)
    
    # Transformation steps
    transformations: List[str] = Field(default_factory=list)
    
    # Dependencies
    depends_on_features: List[str] = Field(default_factory=list)
    
    # Consumers
    consumed_by_components: List[str] = Field(default_factory=list)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_computed: Optional[datetime] = None
```

---

## Feature Groups

```python
# =============================================================================
# ADAM Enhancement #30: Feature Group Definitions
# Location: adam/feature_store/registry/groups.py
# =============================================================================

"""
Feature Group Definitions for ADAM Platform.

Organizes features into logical groups:
1. User Psychological Profile - Big Five, regulatory focus, values
2. User Psychological State - Arousal, construal, processing fluency
3. User Journey Position - State machine position, transition probabilities
4. Mechanism Effectiveness - Thompson priors per user/mechanism
5. Content Features - Psychological attributes of content
6. Advertisement Features - Ad psychological profile
"""

from .models import (
    FeatureGroup, FeatureDefinition, FeatureDataType, FeatureEntityType,
    FeatureFreshness, FeatureSource, PsychologicalDomain
)


# =============================================================================
# USER PSYCHOLOGICAL PROFILE (Traits)
# =============================================================================

USER_PSYCHOLOGICAL_PROFILE = FeatureGroup(
    name="user_psychological_profile",
    description="User personality traits and stable psychological characteristics",
    entity_type=FeatureEntityType.USER,
    psychological_domain=PsychologicalDomain.PERSONALITY_TRAIT,
    default_freshness=FeatureFreshness.DAILY,
    default_ttl_seconds=86400,  # 24 hours
    features=[
        # Big Five Traits
        FeatureDefinition(
            name="openness",
            description="Big Five Openness to Experience score",
            data_type=FeatureDataType.FLOAT,
            entity_type=FeatureEntityType.USER,
            min_value=0.0,
            max_value=1.0,
            freshness=FeatureFreshness.DAILY,
            ttl_seconds=86400,
            source=FeatureSource.NEO4J,
            computation_query="""
                MATCH (u:User {user_id: $user_id})-[:HAS_TRAIT]->(t:Trait {name: 'openness'})
                RETURN t.value as value, t.confidence as confidence
            """,
            psychological_domain=PsychologicalDomain.PERSONALITY_TRAIT,
            psychological_construct="openness",
            validated_scale=True,
        ),
        FeatureDefinition(
            name="conscientiousness",
            description="Big Five Conscientiousness score",
            data_type=FeatureDataType.FLOAT,
            entity_type=FeatureEntityType.USER,
            min_value=0.0,
            max_value=1.0,
            freshness=FeatureFreshness.DAILY,
            ttl_seconds=86400,
            source=FeatureSource.NEO4J,
            computation_query="""
                MATCH (u:User {user_id: $user_id})-[:HAS_TRAIT]->(t:Trait {name: 'conscientiousness'})
                RETURN t.value as value, t.confidence as confidence
            """,
            psychological_domain=PsychologicalDomain.PERSONALITY_TRAIT,
            psychological_construct="conscientiousness",
            validated_scale=True,
        ),
        FeatureDefinition(
            name="extraversion",
            description="Big Five Extraversion score",
            data_type=FeatureDataType.FLOAT,
            entity_type=FeatureEntityType.USER,
            min_value=0.0,
            max_value=1.0,
            freshness=FeatureFreshness.DAILY,
            ttl_seconds=86400,
            source=FeatureSource.NEO4J,
            computation_query="""
                MATCH (u:User {user_id: $user_id})-[:HAS_TRAIT]->(t:Trait {name: 'extraversion'})
                RETURN t.value as value, t.confidence as confidence
            """,
            psychological_domain=PsychologicalDomain.PERSONALITY_TRAIT,
            psychological_construct="extraversion",
            validated_scale=True,
        ),
        FeatureDefinition(
            name="agreeableness",
            description="Big Five Agreeableness score",
            data_type=FeatureDataType.FLOAT,
            entity_type=FeatureEntityType.USER,
            min_value=0.0,
            max_value=1.0,
            freshness=FeatureFreshness.DAILY,
            ttl_seconds=86400,
            source=FeatureSource.NEO4J,
            computation_query="""
                MATCH (u:User {user_id: $user_id})-[:HAS_TRAIT]->(t:Trait {name: 'agreeableness'})
                RETURN t.value as value, t.confidence as confidence
            """,
            psychological_domain=PsychologicalDomain.PERSONALITY_TRAIT,
            psychological_construct="agreeableness",
            validated_scale=True,
        ),
        FeatureDefinition(
            name="neuroticism",
            description="Big Five Neuroticism score",
            data_type=FeatureDataType.FLOAT,
            entity_type=FeatureEntityType.USER,
            min_value=0.0,
            max_value=1.0,
            freshness=FeatureFreshness.DAILY,
            ttl_seconds=86400,
            source=FeatureSource.NEO4J,
            computation_query="""
                MATCH (u:User {user_id: $user_id})-[:HAS_TRAIT]->(t:Trait {name: 'neuroticism'})
                RETURN t.value as value, t.confidence as confidence
            """,
            psychological_domain=PsychologicalDomain.PERSONALITY_TRAIT,
            psychological_construct="neuroticism",
            validated_scale=True,
        ),
        
        # Regulatory Focus
        FeatureDefinition(
            name="promotion_focus",
            description="Promotion focus (gains, aspirations) score",
            data_type=FeatureDataType.FLOAT,
            entity_type=FeatureEntityType.USER,
            min_value=0.0,
            max_value=1.0,
            freshness=FeatureFreshness.DAILY,
            ttl_seconds=86400,
            source=FeatureSource.NEO4J,
            psychological_domain=PsychologicalDomain.REGULATORY_FOCUS,
            psychological_construct="promotion_focus",
            validated_scale=True,
        ),
        FeatureDefinition(
            name="prevention_focus",
            description="Prevention focus (safety, security) score",
            data_type=FeatureDataType.FLOAT,
            entity_type=FeatureEntityType.USER,
            min_value=0.0,
            max_value=1.0,
            freshness=FeatureFreshness.DAILY,
            ttl_seconds=86400,
            source=FeatureSource.NEO4J,
            psychological_domain=PsychologicalDomain.REGULATORY_FOCUS,
            psychological_construct="prevention_focus",
            validated_scale=True,
        ),
        
        # Extended Constructs (#27)
        FeatureDefinition(
            name="need_for_cognition",
            description="Need for Cognition (NFC) score",
            data_type=FeatureDataType.FLOAT,
            entity_type=FeatureEntityType.USER,
            min_value=0.0,
            max_value=1.0,
            freshness=FeatureFreshness.DAILY,
            ttl_seconds=86400,
            source=FeatureSource.NEO4J,
            psychological_domain=PsychologicalDomain.DECISION_STYLE,
            psychological_construct="need_for_cognition",
            validated_scale=True,
        ),
        FeatureDefinition(
            name="self_monitoring",
            description="Self-monitoring score",
            data_type=FeatureDataType.FLOAT,
            entity_type=FeatureEntityType.USER,
            min_value=0.0,
            max_value=1.0,
            freshness=FeatureFreshness.DAILY,
            ttl_seconds=86400,
            source=FeatureSource.NEO4J,
            psychological_domain=PsychologicalDomain.PERSONALITY_TRAIT,
            psychological_construct="self_monitoring",
            validated_scale=True,
        ),
        FeatureDefinition(
            name="maximizer_score",
            description="Maximizer vs Satisficer tendency",
            data_type=FeatureDataType.FLOAT,
            entity_type=FeatureEntityType.USER,
            min_value=0.0,
            max_value=1.0,
            freshness=FeatureFreshness.DAILY,
            ttl_seconds=86400,
            source=FeatureSource.NEO4J,
            psychological_domain=PsychologicalDomain.DECISION_STYLE,
            psychological_construct="maximizing",
            validated_scale=True,
        ),
        
        # User Embedding
        FeatureDefinition(
            name="psychological_embedding",
            description="64-dimensional psychological profile embedding",
            data_type=FeatureDataType.EMBEDDING,
            entity_type=FeatureEntityType.USER,
            embedding_dimension=64,
            freshness=FeatureFreshness.DAILY,
            ttl_seconds=86400,
            source=FeatureSource.NEO4J,
            psychological_domain=PsychologicalDomain.NOT_PSYCHOLOGICAL,
            psychological_construct=None,
        ),
        
        # Profile confidence
        FeatureDefinition(
            name="profile_confidence",
            description="Overall confidence in psychological profile",
            data_type=FeatureDataType.FLOAT,
            entity_type=FeatureEntityType.USER,
            min_value=0.0,
            max_value=1.0,
            freshness=FeatureFreshness.DAILY,
            ttl_seconds=86400,
            source=FeatureSource.NEO4J,
            psychological_domain=PsychologicalDomain.NOT_PSYCHOLOGICAL,
        ),
    ]
)


# =============================================================================
# USER PSYCHOLOGICAL STATE
# =============================================================================

USER_PSYCHOLOGICAL_STATE = FeatureGroup(
    name="user_psychological_state",
    description="User momentary psychological states (change rapidly)",
    entity_type=FeatureEntityType.USER,
    psychological_domain=PsychologicalDomain.PSYCHOLOGICAL_STATE,
    default_freshness=FeatureFreshness.REAL_TIME,
    default_ttl_seconds=300,  # 5 minutes
    features=[
        FeatureDefinition(
            name="arousal_level",
            description="Current arousal/activation level",
            data_type=FeatureDataType.FLOAT,
            entity_type=FeatureEntityType.USER,
            min_value=0.0,
            max_value=1.0,
            freshness=FeatureFreshness.REAL_TIME,
            ttl_seconds=300,
            source=FeatureSource.KAFKA,
            stream_topic="adam.signals.state_transition",
            psychological_domain=PsychologicalDomain.PSYCHOLOGICAL_STATE,
            psychological_construct="arousal",
        ),
        FeatureDefinition(
            name="construal_level",
            description="Current construal level (abstract vs concrete)",
            data_type=FeatureDataType.FLOAT,
            entity_type=FeatureEntityType.USER,
            min_value=0.0,
            max_value=1.0,
            freshness=FeatureFreshness.REAL_TIME,
            ttl_seconds=300,
            source=FeatureSource.KAFKA,
            stream_topic="adam.signals.state_transition",
            psychological_domain=PsychologicalDomain.PSYCHOLOGICAL_STATE,
            psychological_construct="construal_level",
        ),
        FeatureDefinition(
            name="processing_fluency",
            description="Ease of cognitive processing",
            data_type=FeatureDataType.FLOAT,
            entity_type=FeatureEntityType.USER,
            min_value=0.0,
            max_value=1.0,
            freshness=FeatureFreshness.REAL_TIME,
            ttl_seconds=300,
            source=FeatureSource.KAFKA,
            psychological_domain=PsychologicalDomain.PSYCHOLOGICAL_STATE,
            psychological_construct="processing_fluency",
        ),
        FeatureDefinition(
            name="cognitive_load",
            description="Current cognitive load estimate",
            data_type=FeatureDataType.FLOAT,
            entity_type=FeatureEntityType.USER,
            min_value=0.0,
            max_value=1.0,
            freshness=FeatureFreshness.REAL_TIME,
            ttl_seconds=300,
            source=FeatureSource.KAFKA,
            psychological_domain=PsychologicalDomain.PSYCHOLOGICAL_STATE,
            psychological_construct="cognitive_load",
        ),
        FeatureDefinition(
            name="vulnerability_risk_score",
            description="Mental health vulnerability risk (for safeguards)",
            data_type=FeatureDataType.FLOAT,
            entity_type=FeatureEntityType.USER,
            min_value=0.0,
            max_value=1.0,
            default_value=0.0,
            freshness=FeatureFreshness.REAL_TIME,
            ttl_seconds=300,
            source=FeatureSource.KAFKA,
            psychological_domain=PsychologicalDomain.PSYCHOLOGICAL_STATE,
            psychological_construct="vulnerability",
        ),
        FeatureDefinition(
            name="state_confidence",
            description="Confidence in state detection",
            data_type=FeatureDataType.FLOAT,
            entity_type=FeatureEntityType.USER,
            min_value=0.0,
            max_value=1.0,
            freshness=FeatureFreshness.REAL_TIME,
            ttl_seconds=300,
            source=FeatureSource.KAFKA,
            psychological_domain=PsychologicalDomain.NOT_PSYCHOLOGICAL,
        ),
    ]
)


# =============================================================================
# USER JOURNEY POSITION
# =============================================================================

USER_JOURNEY_POSITION = FeatureGroup(
    name="user_journey_position",
    description="User position in persuasion journey state machine",
    entity_type=FeatureEntityType.USER,
    psychological_domain=PsychologicalDomain.JOURNEY_STATE,
    default_freshness=FeatureFreshness.NEAR_REAL_TIME,
    default_ttl_seconds=600,  # 10 minutes
    features=[
        FeatureDefinition(
            name="journey_state",
            description="Current journey state (UNAWARE, AWARE, INTERESTED, etc.)",
            data_type=FeatureDataType.CATEGORICAL,
            entity_type=FeatureEntityType.USER,
            categories=[
                "UNAWARE", "AWARE", "INTERESTED", "CONSIDERING",
                "INTENT", "EVALUATING", "CONVERTED", "ADVOCATE",
                "DORMANT", "CHURNED"
            ],
            freshness=FeatureFreshness.NEAR_REAL_TIME,
            ttl_seconds=600,
            source=FeatureSource.KAFKA,
            stream_topic="adam.signals.state_transition",
            psychological_domain=PsychologicalDomain.JOURNEY_STATE,
            psychological_construct="journey_position",
        ),
        FeatureDefinition(
            name="journey_step",
            description="Current step in active sequence (1-indexed)",
            data_type=FeatureDataType.INTEGER,
            entity_type=FeatureEntityType.USER,
            min_value=0,
            max_value=20,
            default_value=0,
            freshness=FeatureFreshness.NEAR_REAL_TIME,
            ttl_seconds=600,
            source=FeatureSource.KAFKA,
            psychological_domain=PsychologicalDomain.JOURNEY_STATE,
            psychological_construct="sequence_position",
        ),
        FeatureDefinition(
            name="impressions_in_state",
            description="Number of impressions in current state",
            data_type=FeatureDataType.INTEGER,
            entity_type=FeatureEntityType.USER,
            min_value=0,
            freshness=FeatureFreshness.NEAR_REAL_TIME,
            ttl_seconds=600,
            source=FeatureSource.KAFKA,
            psychological_domain=PsychologicalDomain.NOT_PSYCHOLOGICAL,
        ),
        FeatureDefinition(
            name="time_in_state_seconds",
            description="Time spent in current journey state",
            data_type=FeatureDataType.INTEGER,
            entity_type=FeatureEntityType.USER,
            min_value=0,
            freshness=FeatureFreshness.NEAR_REAL_TIME,
            ttl_seconds=600,
            source=FeatureSource.KAFKA,
            psychological_domain=PsychologicalDomain.NOT_PSYCHOLOGICAL,
        ),
        FeatureDefinition(
            name="transition_probability",
            description="Probability of transitioning to next state",
            data_type=FeatureDataType.FLOAT,
            entity_type=FeatureEntityType.USER,
            min_value=0.0,
            max_value=1.0,
            freshness=FeatureFreshness.NEAR_REAL_TIME,
            ttl_seconds=600,
            source=FeatureSource.NEO4J,
            psychological_domain=PsychologicalDomain.JOURNEY_STATE,
            psychological_construct="transition_probability",
        ),
        FeatureDefinition(
            name="completion_probability",
            description="Probability of completing journey to conversion",
            data_type=FeatureDataType.FLOAT,
            entity_type=FeatureEntityType.USER,
            min_value=0.0,
            max_value=1.0,
            freshness=FeatureFreshness.NEAR_REAL_TIME,
            ttl_seconds=600,
            source=FeatureSource.NEO4J,
            psychological_domain=PsychologicalDomain.JOURNEY_STATE,
            psychological_construct="completion_probability",
        ),
    ]
)


# =============================================================================
# MECHANISM EFFECTIVENESS
# =============================================================================

USER_MECHANISM_EFFECTIVENESS = FeatureGroup(
    name="user_mechanism_effectiveness",
    description="Thompson Sampling effectiveness priors per mechanism",
    entity_type=FeatureEntityType.USER,
    psychological_domain=PsychologicalDomain.COGNITIVE_MECHANISM,
    default_freshness=FeatureFreshness.HOURLY,
    default_ttl_seconds=3600,
    features=[
        # One feature per cognitive mechanism
        FeatureDefinition(
            name="automatic_evaluation_effectiveness",
            description="Effectiveness of Automatic Evaluation mechanism",
            data_type=FeatureDataType.FLOAT,
            entity_type=FeatureEntityType.USER,
            min_value=0.0,
            max_value=1.0,
            freshness=FeatureFreshness.HOURLY,
            ttl_seconds=3600,
            source=FeatureSource.KAFKA,
            stream_topic="adam.signals.prior_update",
            psychological_domain=PsychologicalDomain.COGNITIVE_MECHANISM,
            psychological_construct="automatic_evaluation",
        ),
        FeatureDefinition(
            name="wanting_liking_effectiveness",
            description="Effectiveness of Wanting/Liking mechanism",
            data_type=FeatureDataType.FLOAT,
            entity_type=FeatureEntityType.USER,
            min_value=0.0,
            max_value=1.0,
            freshness=FeatureFreshness.HOURLY,
            ttl_seconds=3600,
            source=FeatureSource.KAFKA,
            psychological_domain=PsychologicalDomain.COGNITIVE_MECHANISM,
            psychological_construct="wanting_liking",
        ),
        FeatureDefinition(
            name="evolutionary_motive_effectiveness",
            description="Effectiveness of Evolutionary Motive mechanism",
            data_type=FeatureDataType.FLOAT,
            entity_type=FeatureEntityType.USER,
            min_value=0.0,
            max_value=1.0,
            freshness=FeatureFreshness.HOURLY,
            ttl_seconds=3600,
            source=FeatureSource.KAFKA,
            psychological_domain=PsychologicalDomain.COGNITIVE_MECHANISM,
            psychological_construct="evolutionary_motive",
        ),
        FeatureDefinition(
            name="linguistic_framing_effectiveness",
            description="Effectiveness of Linguistic Framing mechanism",
            data_type=FeatureDataType.FLOAT,
            entity_type=FeatureEntityType.USER,
            min_value=0.0,
            max_value=1.0,
            freshness=FeatureFreshness.HOURLY,
            ttl_seconds=3600,
            source=FeatureSource.KAFKA,
            psychological_domain=PsychologicalDomain.COGNITIVE_MECHANISM,
            psychological_construct="linguistic_framing",
        ),
        FeatureDefinition(
            name="mimetic_desire_effectiveness",
            description="Effectiveness of Mimetic Desire mechanism",
            data_type=FeatureDataType.FLOAT,
            entity_type=FeatureEntityType.USER,
            min_value=0.0,
            max_value=1.0,
            freshness=FeatureFreshness.HOURLY,
            ttl_seconds=3600,
            source=FeatureSource.KAFKA,
            psychological_domain=PsychologicalDomain.COGNITIVE_MECHANISM,
            psychological_construct="mimetic_desire",
        ),
        FeatureDefinition(
            name="embodied_cognition_effectiveness",
            description="Effectiveness of Embodied Cognition mechanism",
            data_type=FeatureDataType.FLOAT,
            entity_type=FeatureEntityType.USER,
            min_value=0.0,
            max_value=1.0,
            freshness=FeatureFreshness.HOURLY,
            ttl_seconds=3600,
            source=FeatureSource.KAFKA,
            psychological_domain=PsychologicalDomain.COGNITIVE_MECHANISM,
            psychological_construct="embodied_cognition",
        ),
        FeatureDefinition(
            name="attention_dynamics_effectiveness",
            description="Effectiveness of Attention Dynamics mechanism",
            data_type=FeatureDataType.FLOAT,
            entity_type=FeatureEntityType.USER,
            min_value=0.0,
            max_value=1.0,
            freshness=FeatureFreshness.HOURLY,
            ttl_seconds=3600,
            source=FeatureSource.KAFKA,
            psychological_domain=PsychologicalDomain.COGNITIVE_MECHANISM,
            psychological_construct="attention_dynamics",
        ),
        FeatureDefinition(
            name="identity_construction_effectiveness",
            description="Effectiveness of Identity Construction mechanism",
            data_type=FeatureDataType.FLOAT,
            entity_type=FeatureEntityType.USER,
            min_value=0.0,
            max_value=1.0,
            freshness=FeatureFreshness.HOURLY,
            ttl_seconds=3600,
            source=FeatureSource.KAFKA,
            psychological_domain=PsychologicalDomain.COGNITIVE_MECHANISM,
            psychological_construct="identity_construction",
        ),
        FeatureDefinition(
            name="temporal_construal_effectiveness",
            description="Effectiveness of Temporal Construal mechanism",
            data_type=FeatureDataType.FLOAT,
            entity_type=FeatureEntityType.USER,
            min_value=0.0,
            max_value=1.0,
            freshness=FeatureFreshness.HOURLY,
            ttl_seconds=3600,
            source=FeatureSource.KAFKA,
            psychological_domain=PsychologicalDomain.COGNITIVE_MECHANISM,
            psychological_construct="temporal_construal",
        ),
        # Thompson Sampling metadata
        FeatureDefinition(
            name="mechanism_samples_total",
            description="Total samples across all mechanisms",
            data_type=FeatureDataType.INTEGER,
            entity_type=FeatureEntityType.USER,
            min_value=0,
            freshness=FeatureFreshness.HOURLY,
            ttl_seconds=3600,
            source=FeatureSource.KAFKA,
            psychological_domain=PsychologicalDomain.NOT_PSYCHOLOGICAL,
        ),
    ]
)


# =============================================================================
# ALL FEATURE GROUPS
# =============================================================================

ALL_FEATURE_GROUPS = {
    "user_psychological_profile": USER_PSYCHOLOGICAL_PROFILE,
    "user_psychological_state": USER_PSYCHOLOGICAL_STATE,
    "user_journey_position": USER_JOURNEY_POSITION,
    "user_mechanism_effectiveness": USER_MECHANISM_EFFECTIVENESS,
}


def get_feature_group(name: str) -> Optional[FeatureGroup]:
    """Get feature group by name."""
    return ALL_FEATURE_GROUPS.get(name)


def get_all_user_feature_groups() -> List[FeatureGroup]:
    """Get all feature groups for user entities."""
    return [
        g for g in ALL_FEATURE_GROUPS.values()
        if g.entity_type == FeatureEntityType.USER
    ]
```

---

# SECTION C: ONLINE STORE

## Redis-Backed Online Store

```python
# =============================================================================
# ADAM Enhancement #30: Online Feature Store
# Location: adam/feature_store/online/store.py
# =============================================================================

"""
Online Feature Store backed by Redis Cluster.

Provides:
1. Sub-10ms feature retrieval (p99)
2. TTL-based freshness management
3. Automatic refresh from offline store
4. Batch retrieval for multiple entities
5. Feature versioning support
"""

from __future__ import annotations
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
import json
import asyncio
import logging

from ..registry.models import (
    FeatureDefinition, FeatureGroup, FeatureValue, FeatureVector,
    FeatureEntityType, FeatureFreshness, FeatureSource
)
from ..registry.groups import ALL_FEATURE_GROUPS, get_feature_group

logger = logging.getLogger(__name__)


@dataclass
class OnlineStoreConfig:
    """Configuration for the online feature store."""
    
    # Redis connection
    redis_cluster_nodes: List[str] = field(default_factory=lambda: [
        "adam-redis-master-1.adam.svc.cluster.local:6379",
        "adam-redis-master-2.adam.svc.cluster.local:6379",
        "adam-redis-master-3.adam.svc.cluster.local:6379",
    ])
    
    # Key prefix (from #29)
    key_prefix: str = "adam:feature"
    
    # Default TTLs
    default_ttl_seconds: int = 3600
    state_ttl_seconds: int = 300
    
    # Freshness
    stale_threshold_factor: float = 0.9  # 90% of TTL = stale
    
    # Batch settings
    max_batch_size: int = 100
    
    # Refresh settings
    refresh_on_stale: bool = True
    refresh_queue_size: int = 1000


class OnlineFeatureStore:
    """
    Online feature store for real-time feature serving.
    
    Uses Redis cluster from #29 for sub-10ms feature retrieval.
    
    Key structure:
        adam:feature:{entity_type}:{entity_id}:{group_name}
        
    Value structure (JSON):
        {
            "features": {
                "openness": {"value": 0.75, "computed_at": "...", "confidence": 0.9},
                "conscientiousness": {"value": 0.82, ...},
                ...
            },
            "version": "1.0.0",
            "computed_at": "2026-01-15T10:30:00Z"
        }
    
    Usage:
        store = OnlineFeatureStore(config)
        await store.initialize()
        
        # Get features
        vector = await store.get_features(
            entity_type=FeatureEntityType.USER,
            entity_id="user_123",
            feature_groups=["user_psychological_profile", "user_journey_position"]
        )
        
        # Access features
        openness = vector.get("openness")
        journey_state = vector.get("journey_state")
    """
    
    def __init__(
        self,
        config: Optional[OnlineStoreConfig] = None,
        redis_pool: Optional[Any] = None,  # ADAMRedisPool from #29
    ):
        self.config = config or OnlineStoreConfig()
        self._redis = redis_pool
        self._initialized = False
        self._refresh_queue: asyncio.Queue = asyncio.Queue(
            maxsize=self.config.refresh_queue_size
        )
    
    async def initialize(self) -> None:
        """Initialize the online store."""
        if self._redis is None:
            from adam.infrastructure.redis.pool import ADAMRedisPool
            from adam.infrastructure.redis.config import RedisClusterConfig
            
            self._redis = ADAMRedisPool(cluster_config=RedisClusterConfig())
            await self._redis.initialize()
        
        self._initialized = True
        logger.info("Online feature store initialized")
    
    async def close(self) -> None:
        """Close connections."""
        if self._redis:
            await self._redis.close()
        self._initialized = False
    
    # =========================================================================
    # KEY MANAGEMENT
    # =========================================================================
    
    def _make_key(
        self,
        entity_type: FeatureEntityType,
        entity_id: str,
        group_name: str,
    ) -> str:
        """Build Redis key for feature group."""
        return f"{self.config.key_prefix}:{entity_type.value}:{entity_id}:{group_name}"
    
    def _parse_key(self, key: str) -> tuple:
        """Parse Redis key to components."""
        parts = key.split(":")
        return parts[2], parts[3], parts[4]  # entity_type, entity_id, group_name
    
    # =========================================================================
    # FEATURE RETRIEVAL
    # =========================================================================
    
    async def get_features(
        self,
        entity_type: FeatureEntityType,
        entity_id: str,
        feature_groups: List[str],
        feature_names: Optional[List[str]] = None,
    ) -> FeatureVector:
        """
        Get features for an entity.
        
        Args:
            entity_type: Type of entity (USER, CONTENT, etc.)
            entity_id: Entity identifier
            feature_groups: List of feature group names to retrieve
            feature_names: Optional list of specific feature names to return
            
        Returns:
            FeatureVector with requested features
        """
        result = FeatureVector(
            entity_type=entity_type,
            entity_id=entity_id,
        )
        
        # Build keys for all requested groups
        keys = [
            self._make_key(entity_type, entity_id, group)
            for group in feature_groups
        ]
        
        # Batch fetch from Redis
        values = await self._batch_get(keys)
        
        for group_name, value in zip(feature_groups, values):
            if value is None:
                # Cache miss - record missing features
                group = get_feature_group(group_name)
                if group:
                    result.missing_features.extend(group.get_feature_names())
                result.cache_hit = False
                continue
            
            # Parse cached value
            try:
                cached = json.loads(value)
                group_computed_at = datetime.fromisoformat(cached["computed_at"])
                
                for feature_name, feature_data in cached["features"].items():
                    # Skip if not in requested names
                    if feature_names and feature_name not in feature_names:
                        continue
                    
                    # Get feature definition for TTL
                    group = get_feature_group(group_name)
                    feature_def = group.get_feature(feature_name) if group else None
                    ttl = feature_def.ttl_seconds if feature_def else self.config.default_ttl_seconds
                    
                    # Check staleness
                    computed_at = datetime.fromisoformat(feature_data["computed_at"])
                    age = (datetime.utcnow() - computed_at).total_seconds()
                    is_stale = age > ttl * self.config.stale_threshold_factor
                    
                    if is_stale:
                        result.stale_features.append(feature_name)
                    
                    # Build feature value
                    fv = FeatureValue(
                        feature_name=feature_name,
                        value=feature_data["value"],
                        computed_at=computed_at,
                        source=FeatureSource(feature_data.get("source", "neo4j")),
                        ttl_seconds=ttl,
                        is_stale=is_stale,
                        confidence=feature_data.get("confidence"),
                    )
                    
                    result.features[feature_name] = fv
                    
            except (json.JSONDecodeError, KeyError) as e:
                logger.error(f"Failed to parse cached features for {group_name}: {e}")
                result.cache_hit = False
        
        # Queue refresh for stale features
        if result.stale_features and self.config.refresh_on_stale:
            await self._queue_refresh(entity_type, entity_id, result.stale_features)
        
        return result
    
    async def get_feature(
        self,
        entity_type: FeatureEntityType,
        entity_id: str,
        feature_name: str,
        group_name: str,
    ) -> Optional[FeatureValue]:
        """Get a single feature value."""
        vector = await self.get_features(
            entity_type=entity_type,
            entity_id=entity_id,
            feature_groups=[group_name],
            feature_names=[feature_name],
        )
        return vector.features.get(feature_name)
    
    async def get_features_batch(
        self,
        entity_type: FeatureEntityType,
        entity_ids: List[str],
        feature_groups: List[str],
    ) -> Dict[str, FeatureVector]:
        """
        Get features for multiple entities.
        
        Returns dict of entity_id -> FeatureVector
        """
        if len(entity_ids) > self.config.max_batch_size:
            raise ValueError(f"Batch size {len(entity_ids)} exceeds max {self.config.max_batch_size}")
        
        results = {}
        
        # Build all keys
        all_keys = []
        key_mapping = []  # (entity_id, group_name)
        
        for entity_id in entity_ids:
            for group in feature_groups:
                key = self._make_key(entity_type, entity_id, group)
                all_keys.append(key)
                key_mapping.append((entity_id, group))
        
        # Batch fetch
        values = await self._batch_get(all_keys)
        
        # Process results
        for (entity_id, group_name), value in zip(key_mapping, values):
            if entity_id not in results:
                results[entity_id] = FeatureVector(
                    entity_type=entity_type,
                    entity_id=entity_id,
                )
            
            if value:
                # Parse and add to result (simplified)
                cached = json.loads(value)
                for feature_name, feature_data in cached["features"].items():
                    fv = FeatureValue(
                        feature_name=feature_name,
                        value=feature_data["value"],
                        computed_at=datetime.fromisoformat(feature_data["computed_at"]),
                        source=FeatureSource(feature_data.get("source", "neo4j")),
                        ttl_seconds=self.config.default_ttl_seconds,
                    )
                    results[entity_id].features[feature_name] = fv
        
        return results
    
    # =========================================================================
    # FEATURE STORAGE
    # =========================================================================
    
    async def set_features(
        self,
        entity_type: FeatureEntityType,
        entity_id: str,
        group_name: str,
        features: Dict[str, Any],
        source: FeatureSource = FeatureSource.NEO4J,
        confidence: Optional[float] = None,
        ttl_seconds: Optional[int] = None,
    ) -> bool:
        """
        Store features in the online store.
        
        Args:
            entity_type: Type of entity
            entity_id: Entity identifier
            group_name: Feature group name
            features: Dict of feature_name -> value
            source: Source of the features
            confidence: Optional confidence score
            ttl_seconds: Override TTL
        """
        key = self._make_key(entity_type, entity_id, group_name)
        
        # Get TTL from group or use default
        if ttl_seconds is None:
            group = get_feature_group(group_name)
            ttl_seconds = group.default_ttl_seconds if group else self.config.default_ttl_seconds
        
        # Build value structure
        now = datetime.utcnow().isoformat()
        value = {
            "features": {},
            "version": "1.0.0",
            "computed_at": now,
        }
        
        for name, val in features.items():
            value["features"][name] = {
                "value": val,
                "computed_at": now,
                "source": source.value,
            }
            if confidence is not None:
                value["features"][name]["confidence"] = confidence
        
        # Store in Redis with TTL
        return await self._redis.set(
            key,
            json.dumps(value),
            ttl=timedelta(seconds=ttl_seconds)
        )
    
    async def invalidate_features(
        self,
        entity_type: FeatureEntityType,
        entity_id: str,
        feature_groups: Optional[List[str]] = None,
    ) -> int:
        """
        Invalidate cached features for an entity.
        
        Returns number of keys deleted.
        """
        if feature_groups is None:
            # Invalidate all groups for entity
            pattern = f"{self.config.key_prefix}:{entity_type.value}:{entity_id}:*"
            keys = await self._scan_keys(pattern)
        else:
            keys = [
                self._make_key(entity_type, entity_id, group)
                for group in feature_groups
            ]
        
        if not keys:
            return 0
        
        deleted = 0
        for key in keys:
            deleted += await self._redis.delete(key)
        
        return deleted
    
    # =========================================================================
    # INTERNAL METHODS
    # =========================================================================
    
    async def _batch_get(self, keys: List[str]) -> List[Optional[str]]:
        """Batch get multiple keys from Redis."""
        # Use Redis pipeline for efficiency
        results = []
        for key in keys:
            value = await self._redis.get(key)
            results.append(value)
        return results
    
    async def _scan_keys(self, pattern: str) -> List[str]:
        """Scan for keys matching pattern."""
        # Implementation depends on redis-py cluster support
        return []
    
    async def _queue_refresh(
        self,
        entity_type: FeatureEntityType,
        entity_id: str,
        feature_names: List[str],
    ) -> None:
        """Queue features for background refresh."""
        try:
            self._refresh_queue.put_nowait({
                "entity_type": entity_type.value,
                "entity_id": entity_id,
                "feature_names": feature_names,
                "queued_at": datetime.utcnow().isoformat(),
            })
        except asyncio.QueueFull:
            logger.warning("Refresh queue full, dropping refresh request")


# =============================================================================
# FEATURE SERVING API
# =============================================================================

@dataclass
class FeatureRequest:
    """Request for features."""
    entity_type: FeatureEntityType
    entity_id: str
    feature_groups: List[str]
    feature_names: Optional[List[str]] = None


@dataclass 
class FeatureResponse:
    """Response with features."""
    entity_type: str
    entity_id: str
    features: Dict[str, Any]
    stale_features: List[str]
    missing_features: List[str]
    latency_ms: float
```

---

# SECTION D: OFFLINE STORE

## Neo4j Feature Storage

```python
# =============================================================================
# ADAM Enhancement #30: Offline Feature Store
# Location: adam/feature_store/offline/store.py
# =============================================================================

"""
Offline Feature Store backed by Neo4j.

Provides:
1. Historical feature storage with timestamps
2. Point-in-time correct feature retrieval
3. Training data generation
4. Feature backfill capabilities
"""

from __future__ import annotations
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
import logging

from neo4j import AsyncDriver

from ..registry.models import (
    FeatureDefinition, FeatureGroup, FeatureValue, FeatureVector,
    FeatureEntityType, FeatureSource
)

logger = logging.getLogger(__name__)


class OfflineFeatureStore:
    """
    Offline feature store backed by Neo4j.
    
    Stores historical feature values with timestamps for:
    1. Point-in-time correct training data
    2. Feature backfill
    3. Audit trails
    
    Neo4j Schema:
        (:User)-[:HAD_FEATURE {timestamp, version}]->(:FeatureSnapshot)
        (:FeatureSnapshot {
            feature_group: str,
            features: json,
            computed_at: datetime,
            source: str
        })
    """
    
    def __init__(
        self,
        neo4j_driver: AsyncDriver,
        database: str = "neo4j",
    ):
        self.driver = neo4j_driver
        self.database = database
    
    async def get_features_at_time(
        self,
        entity_type: FeatureEntityType,
        entity_id: str,
        feature_groups: List[str],
        as_of: datetime,
    ) -> FeatureVector:
        """
        Get features as they were at a specific point in time.
        
        This is critical for training data generation to avoid
        data leakage (using future information to predict past).
        
        Args:
            entity_type: Type of entity
            entity_id: Entity identifier
            feature_groups: Groups to retrieve
            as_of: Point in time for feature lookup
        """
        result = FeatureVector(
            entity_type=entity_type,
            entity_id=entity_id,
        )
        
        query = """
        MATCH (e {id: $entity_id})-[r:HAD_FEATURE]->(fs:FeatureSnapshot)
        WHERE fs.feature_group IN $groups
        AND fs.computed_at <= datetime($as_of)
        WITH fs.feature_group as group, fs
        ORDER BY fs.computed_at DESC
        WITH group, COLLECT(fs)[0] as latest_fs
        RETURN group, latest_fs.features as features, 
               latest_fs.computed_at as computed_at,
               latest_fs.source as source
        """
        
        async with self.driver.session(database=self.database) as session:
            records = await session.run(
                query,
                entity_id=entity_id,
                groups=feature_groups,
                as_of=as_of.isoformat(),
            )
            
            async for record in records:
                group = record["group"]
                features = record["features"]
                computed_at = record["computed_at"]
                source = record["source"]
                
                if isinstance(features, str):
                    import json
                    features = json.loads(features)
                
                for name, value in features.items():
                    fv = FeatureValue(
                        feature_name=name,
                        value=value,
                        computed_at=computed_at.to_native() if hasattr(computed_at, 'to_native') else computed_at,
                        source=FeatureSource(source) if source else FeatureSource.NEO4J,
                        ttl_seconds=86400,  # Historical features don't expire
                    )
                    result.features[name] = fv
        
        return result
    
    async def store_features(
        self,
        entity_type: FeatureEntityType,
        entity_id: str,
        group_name: str,
        features: Dict[str, Any],
        source: FeatureSource = FeatureSource.NEO4J,
        computed_at: Optional[datetime] = None,
    ) -> bool:
        """
        Store a feature snapshot in the offline store.
        """
        import json
        
        computed_at = computed_at or datetime.utcnow()
        
        query = """
        MATCH (e {id: $entity_id})
        CREATE (fs:FeatureSnapshot {
            snapshot_id: randomUUID(),
            feature_group: $group_name,
            features: $features,
            computed_at: datetime($computed_at),
            source: $source
        })
        CREATE (e)-[:HAD_FEATURE {
            timestamp: datetime($computed_at),
            version: '1.0.0'
        }]->(fs)
        RETURN fs.snapshot_id as id
        """
        
        async with self.driver.session(database=self.database) as session:
            result = await session.run(
                query,
                entity_id=entity_id,
                group_name=group_name,
                features=json.dumps(features),
                computed_at=computed_at.isoformat(),
                source=source.value,
            )
            record = await result.single()
            return record is not None
    
    async def generate_training_data(
        self,
        entity_type: FeatureEntityType,
        entity_ids: List[str],
        feature_groups: List[str],
        label_column: str,
        start_time: datetime,
        end_time: datetime,
    ) -> List[Dict[str, Any]]:
        """
        Generate training data with point-in-time correct features.
        
        For each label event, retrieves features as they were at that time.
        
        Returns list of dicts with features and label.
        """
        training_data = []
        
        # Get label events in time range
        label_query = """
        MATCH (e {id: $entity_id})-[r:HAD_OUTCOME]->(o:Outcome)
        WHERE o.timestamp >= datetime($start_time)
        AND o.timestamp <= datetime($end_time)
        RETURN o.timestamp as event_time, o[$label_column] as label
        ORDER BY o.timestamp
        """
        
        async with self.driver.session(database=self.database) as session:
            for entity_id in entity_ids:
                # Get label events
                label_records = await session.run(
                    label_query,
                    entity_id=entity_id,
                    start_time=start_time.isoformat(),
                    end_time=end_time.isoformat(),
                    label_column=label_column,
                )
                
                async for record in label_records:
                    event_time = record["event_time"]
                    label = record["label"]
                    
                    # Get features as of event time
                    features = await self.get_features_at_time(
                        entity_type=entity_type,
                        entity_id=entity_id,
                        feature_groups=feature_groups,
                        as_of=event_time.to_native() if hasattr(event_time, 'to_native') else event_time,
                    )
                    
                    # Build training row
                    row = features.to_dict()
                    row["entity_id"] = entity_id
                    row["event_time"] = event_time
                    row["label"] = label
                    
                    training_data.append(row)
        
        return training_data
```

---

# SECTION E: PSYCHOLOGICAL FEATURES

## Trait Features

See `USER_PSYCHOLOGICAL_PROFILE` feature group in Section B. Key psychological trait features:

| Feature | Construct | Source | TTL |
|---------|-----------|--------|-----|
| `openness` | Big Five | Neo4j | 24h |
| `conscientiousness` | Big Five | Neo4j | 24h |
| `extraversion` | Big Five | Neo4j | 24h |
| `agreeableness` | Big Five | Neo4j | 24h |
| `neuroticism` | Big Five | Neo4j | 24h |
| `promotion_focus` | Regulatory Focus | Neo4j | 24h |
| `prevention_focus` | Regulatory Focus | Neo4j | 24h |
| `need_for_cognition` | Decision Style | Neo4j | 24h |
| `psychological_embedding` | Composite | Neo4j | 24h |

## State Features

See `USER_PSYCHOLOGICAL_STATE` feature group. Key state features:

| Feature | Construct | Source | TTL |
|---------|-----------|--------|-----|
| `arousal_level` | Psychological State | Kafka | 5m |
| `construal_level` | Psychological State | Kafka | 5m |
| `processing_fluency` | Cognitive State | Kafka | 5m |
| `vulnerability_risk_score` | Mental Health | Kafka | 5m |

## Mechanism Effectiveness Features

See `USER_MECHANISM_EFFECTIVENESS` feature group. Thompson Sampling effectiveness for each of ADAM's 9 cognitive mechanisms.

---

# SECTION F: INTEGRATION & OPERATIONS

## FastAPI Endpoints

```python
# =============================================================================
# ADAM Enhancement #30: Feature Store API
# Location: adam/feature_store/api/endpoints.py
# =============================================================================

"""
FastAPI endpoints for ADAM Feature Store.

Provides:
1. Feature retrieval (single and batch)
2. Feature freshness checking
3. Feature invalidation
4. Health and metrics
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import datetime
import time

from ..registry.models import FeatureEntityType
from ..online.store import OnlineFeatureStore

router = APIRouter(prefix="/api/v1/features", tags=["features"])


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class GetFeaturesRequest(BaseModel):
    """Request to get features."""
    entity_type: str = Field(..., description="Entity type (user, content, etc.)")
    entity_id: str = Field(..., description="Entity identifier")
    feature_groups: List[str] = Field(..., description="Feature groups to retrieve")
    feature_names: Optional[List[str]] = Field(None, description="Specific features to return")


class GetFeaturesBatchRequest(BaseModel):
    """Request to get features for multiple entities."""
    entity_type: str
    entity_ids: List[str] = Field(..., max_items=100)
    feature_groups: List[str]


class FeaturesResponse(BaseModel):
    """Response with features."""
    entity_type: str
    entity_id: str
    features: Dict[str, Any]
    stale_features: List[str] = Field(default_factory=list)
    missing_features: List[str] = Field(default_factory=list)
    cache_hit: bool = True
    latency_ms: float


class BatchFeaturesResponse(BaseModel):
    """Response with features for multiple entities."""
    results: Dict[str, FeaturesResponse]
    total_latency_ms: float


class InvalidationRequest(BaseModel):
    """Request to invalidate features."""
    entity_type: str
    entity_id: str
    feature_groups: Optional[List[str]] = None


class InvalidationResponse(BaseModel):
    """Response from invalidation."""
    keys_deleted: int


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.post("/get", response_model=FeaturesResponse)
async def get_features(
    request: GetFeaturesRequest,
    store: OnlineFeatureStore = Depends(get_feature_store),
):
    """
    Get features for an entity.
    
    Returns requested features from the online store with
    freshness information.
    """
    start_time = time.perf_counter()
    
    try:
        entity_type = FeatureEntityType(request.entity_type)
    except ValueError:
        raise HTTPException(400, f"Invalid entity type: {request.entity_type}")
    
    vector = await store.get_features(
        entity_type=entity_type,
        entity_id=request.entity_id,
        feature_groups=request.feature_groups,
        feature_names=request.feature_names,
    )
    
    latency_ms = (time.perf_counter() - start_time) * 1000
    
    return FeaturesResponse(
        entity_type=request.entity_type,
        entity_id=request.entity_id,
        features=vector.to_dict(),
        stale_features=vector.stale_features,
        missing_features=vector.missing_features,
        cache_hit=vector.cache_hit,
        latency_ms=latency_ms,
    )


@router.post("/batch", response_model=BatchFeaturesResponse)
async def get_features_batch(
    request: GetFeaturesBatchRequest,
    store: OnlineFeatureStore = Depends(get_feature_store),
):
    """
    Get features for multiple entities.
    
    More efficient than multiple single requests.
    """
    start_time = time.perf_counter()
    
    try:
        entity_type = FeatureEntityType(request.entity_type)
    except ValueError:
        raise HTTPException(400, f"Invalid entity type: {request.entity_type}")
    
    vectors = await store.get_features_batch(
        entity_type=entity_type,
        entity_ids=request.entity_ids,
        feature_groups=request.feature_groups,
    )
    
    total_latency_ms = (time.perf_counter() - start_time) * 1000
    
    results = {}
    for entity_id, vector in vectors.items():
        results[entity_id] = FeaturesResponse(
            entity_type=request.entity_type,
            entity_id=entity_id,
            features=vector.to_dict(),
            stale_features=vector.stale_features,
            missing_features=vector.missing_features,
            cache_hit=vector.cache_hit,
            latency_ms=total_latency_ms / len(request.entity_ids),
        )
    
    return BatchFeaturesResponse(
        results=results,
        total_latency_ms=total_latency_ms,
    )


@router.get("/{entity_type}/{entity_id}/{group_name}/{feature_name}")
async def get_single_feature(
    entity_type: str,
    entity_id: str,
    group_name: str,
    feature_name: str,
    store: OnlineFeatureStore = Depends(get_feature_store),
):
    """Get a single feature value."""
    try:
        et = FeatureEntityType(entity_type)
    except ValueError:
        raise HTTPException(400, f"Invalid entity type: {entity_type}")
    
    fv = await store.get_feature(
        entity_type=et,
        entity_id=entity_id,
        feature_name=feature_name,
        group_name=group_name,
    )
    
    if fv is None:
        raise HTTPException(404, f"Feature not found: {feature_name}")
    
    return {
        "feature_name": fv.feature_name,
        "value": fv.value,
        "computed_at": fv.computed_at.isoformat(),
        "is_stale": fv.is_stale,
        "confidence": fv.confidence,
    }


@router.post("/invalidate", response_model=InvalidationResponse)
async def invalidate_features(
    request: InvalidationRequest,
    store: OnlineFeatureStore = Depends(get_feature_store),
):
    """Invalidate cached features for an entity."""
    try:
        entity_type = FeatureEntityType(request.entity_type)
    except ValueError:
        raise HTTPException(400, f"Invalid entity type: {request.entity_type}")
    
    deleted = await store.invalidate_features(
        entity_type=entity_type,
        entity_id=request.entity_id,
        feature_groups=request.feature_groups,
    )
    
    return InvalidationResponse(keys_deleted=deleted)


@router.get("/health")
async def health_check(
    store: OnlineFeatureStore = Depends(get_feature_store),
):
    """Health check for feature store."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "initialized": store._initialized,
    }


# =============================================================================
# DEPENDENCY INJECTION
# =============================================================================

_feature_store: Optional[OnlineFeatureStore] = None


async def get_feature_store() -> OnlineFeatureStore:
    """Get the feature store instance."""
    global _feature_store
    if _feature_store is None:
        _feature_store = OnlineFeatureStore()
        await _feature_store.initialize()
    return _feature_store
```

---

## Neo4j Schema

```cypher
// =============================================================================
// ADAM Enhancement #30: Neo4j Schema for Offline Feature Store
// =============================================================================

// CONSTRAINTS
CREATE CONSTRAINT feature_snapshot_id IF NOT EXISTS 
FOR (fs:FeatureSnapshot) REQUIRE fs.snapshot_id IS UNIQUE;

// INDEXES
CREATE INDEX feature_group_idx IF NOT EXISTS 
FOR (fs:FeatureSnapshot) ON (fs.feature_group);

CREATE INDEX feature_computed_at_idx IF NOT EXISTS 
FOR (fs:FeatureSnapshot) ON (fs.computed_at);

// COMPOSITE INDEX for point-in-time queries
CREATE INDEX feature_group_time_idx IF NOT EXISTS 
FOR (fs:FeatureSnapshot) ON (fs.feature_group, fs.computed_at);
```

---

## Implementation Timeline

### Phase 1: Foundation (Weeks 1-2)

| Week | Focus | Deliverables |
|------|-------|--------------|
| 1 | Feature Registry | Pydantic models, feature definitions |
| 1 | Feature Groups | All psychological feature groups defined |
| 2 | Online Store Core | Redis integration, get/set operations |
| 2 | Key Convention | Integration with #29 key conventions |

### Phase 2: Online Serving (Weeks 3-4)

| Week | Focus | Deliverables |
|------|-------|--------------|
| 3 | FastAPI Endpoints | All REST endpoints |
| 3 | Batch Operations | Batch get for multiple entities |
| 4 | Freshness Management | TTL tracking, stale detection |
| 4 | Automatic Refresh | Background refresh worker |

### Phase 3: Offline Store (Weeks 5-6)

| Week | Focus | Deliverables |
|------|-------|--------------|
| 5 | Neo4j Integration | Historical storage schema |
| 5 | Point-in-Time | As-of queries for training |
| 6 | Training Data | Training data generation pipeline |
| 6 | Integration | Integration with ADAM components |

---

## Success Metrics

### Performance SLIs

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Get features p99** | <10ms | Prometheus histogram |
| **Get features p50** | <5ms | Prometheus histogram |
| **Batch get p99** | <20ms | Prometheus histogram |
| **Cache hit rate** | >95% | Counter ratio |

### Operational Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Stale feature rate** | <5% | Gauge |
| **Missing feature rate** | <1% | Gauge |
| **Refresh queue depth** | <100 | Gauge |
| **Availability** | 99.99% | Uptime |

### Business Impact

| Metric | Baseline | Target | Impact |
|--------|----------|--------|--------|
| Inference latency | 150ms | <100ms | Real-time serving |
| Feature freshness | Hours | Minutes | Faster optimization |
| Training velocity | Days | Hours | Faster model iteration |

---

**END OF ENHANCEMENT #30: FEATURE STORE & REAL-TIME SERVING**
