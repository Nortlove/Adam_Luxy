# ADAM Enhancement #29: Platform Infrastructure Foundation
## Enterprise-Grade Infrastructure Substrate for Psychological Intelligence Platform

**Version**: 1.0 COMPLETE  
**Date**: January 2026  
**Priority**: P0 - Critical Foundation (Blocks All Other Enhancements)  
**Estimated Implementation**: 6 person-weeks  
**Dependencies**: None (this IS the foundation)  
**Dependents**: ALL other enhancements (#01-28, #30-31)  
**File Size**: ~120KB (Enterprise Production-Ready)

---

## Table of Contents

### SECTION A: STRATEGIC OVERVIEW
1. [Executive Summary](#executive-summary)
2. [Why Infrastructure First](#why-infrastructure-first)
3. [Architecture Overview](#architecture-overview)

### SECTION B: REDIS CLUSTER INFRASTRUCTURE
4. [Redis Architecture](#redis-architecture)
5. [Cluster Topology](#cluster-topology)
6. [ADAM Key Conventions](#adam-key-conventions)
7. [Lua Scripts for Atomic Operations](#lua-scripts)
8. [Connection Pooling](#connection-pooling)
9. [Persistence and Backup](#persistence-and-backup)

### SECTION C: KAFKA EVENT STREAMING
10. [Kafka Architecture](#kafka-architecture)
11. [Topic Definitions](#topic-definitions)
12. [Avro Schema Registry](#avro-schema-registry)
13. [Learning Signal Schemas](#learning-signal-schemas)
14. [Consumer Group Strategy](#consumer-group-strategy)
15. [Exactly-Once Semantics](#exactly-once-semantics)

### SECTION D: SERVICE MESH & API GATEWAY
16. [Linkerd Service Mesh](#linkerd-service-mesh)
17. [Kong API Gateway](#kong-api-gateway)
18. [Rate Limiting Strategy](#rate-limiting-strategy)
19. [Authentication & Authorization](#authentication)

### SECTION E: OBSERVABILITY STACK
20. [Prometheus Metrics](#prometheus-metrics)
21. [ADAM Custom Metrics](#adam-custom-metrics)
22. [Grafana Dashboards](#grafana-dashboards)
23. [Jaeger Distributed Tracing](#jaeger-tracing)
24. [Loki Log Aggregation](#loki-logging)
25. [Alerting Rules](#alerting-rules)

### SECTION F: KUBERNETES DEPLOYMENT
26. [Namespace Strategy](#namespace-strategy)
27. [Resource Quotas](#resource-quotas)
28. [Horizontal Pod Autoscaling](#hpa-configuration)
29. [ConfigMaps and Secrets](#configmaps-secrets)
30. [Network Policies](#network-policies)

### SECTION G: LOCAL DEVELOPMENT
31. [Docker Compose Environment](#docker-compose)
32. [Development Workflow](#development-workflow)

### SECTION H: IMPLEMENTATION & OPERATIONS
33. [Helm Charts](#helm-charts)
34. [Terraform Modules](#terraform-modules)
35. [CI/CD Pipeline](#cicd-pipeline)
36. [Implementation Timeline](#implementation-timeline)
37. [Success Metrics](#success-metrics)

---

# SECTION A: STRATEGIC OVERVIEW

## Executive Summary

### The Foundation Everything Depends On

Enhancement #29 is not just another component—it is the **substrate** upon which all 30+ ADAM components operate. Without this infrastructure:

- **Blackboard (#02)** has no Redis cluster to store shared state
- **Gradient Bridge (#06)** has no Kafka to propagate learning signals
- **Inference Engine (#09)** has no cache for sub-100ms decisions
- **WPP Ad Desk (#28)** has no event streaming for outcome learning

This specification provides **production-ready infrastructure** with complete configurations, not conceptual architecture.

### What This Specification Delivers

| Component | Purpose | Key Deliverable |
|-----------|---------|-----------------|
| **Redis Cluster** | Blackboard backend, caching, sessions | 6-node cluster config, Lua scripts, key conventions |
| **Kafka Cluster** | Learning signals, outcomes, events | Topic schemas, Avro registry, consumer groups |
| **Linkerd Mesh** | Service-to-service communication | mTLS, traffic policies, circuit breakers |
| **Kong Gateway** | External API management | Rate limiting, auth, ADAM-specific plugins |
| **Prometheus** | Metrics collection | ADAM psychological metrics, SLIs |
| **Grafana** | Visualization | Pre-built dashboards for all components |
| **Jaeger** | Distributed tracing | Trace context for psychological reasoning |
| **Loki** | Log aggregation | Structured logging patterns |
| **Kubernetes** | Orchestration | Helm charts, HPA, network policies |

### Critical Design Principles

1. **ADAM-Specific, Not Generic** - Every configuration is tuned for psychological intelligence workloads, not generic web apps
2. **Learning-First Architecture** - Kafka topics and Redis keys are designed around the Gradient Bridge learning loop
3. **Sub-100ms Real-Time** - Cache hierarchies and connection pools optimized for inference latency
4. **Psychological Observability** - Metrics capture mechanism activations, not just HTTP requests
5. **Local-Production Parity** - Docker Compose mirrors production topology exactly

---

## Why Infrastructure First

### The Dependency Chain

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                                                                                         │
│   WHY #29 MUST BE BUILT FIRST                                                          │
│                                                                                         │
│   Every component assumes infrastructure exists:                                        │
│                                                                                         │
│   #02 Blackboard:                                                                       │
│   ┌──────────────────────────────────────────────────────────────────────────────────┐ │
│   │ async def __init__(self, redis_cluster: RedisCluster):  # WHERE DOES THIS COME?  │ │
│   │     self.redis = redis_cluster                                                   │ │
│   └──────────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                         │
│   #06 Gradient Bridge:                                                                  │
│   ┌──────────────────────────────────────────────────────────────────────────────────┐ │
│   │ async def emit(self, signal: LearningSignal):                                    │ │
│   │     await self.kafka_producer.send(  # WHERE IS KAFKA CONFIGURED?               │ │
│   │         topic="adam.signals.learning",                                           │ │
│   │         value=signal.to_avro()                                                   │ │
│   │     )                                                                            │ │
│   └──────────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                         │
│   #09 Inference Engine:                                                                 │
│   ┌──────────────────────────────────────────────────────────────────────────────────┐ │
│   │ async def get_cached_profile(self, user_id: str):                                │ │
│   │     return await self.redis.get(f"adam:profile:{user_id}")  # WHAT KEY FORMAT?  │ │
│   └──────────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                         │
│   THIS SPECIFICATION ANSWERS ALL OF THESE                                              │
│                                                                                         │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

### What Happens Without #29

| Scenario | Problem | Impact |
|----------|---------|--------|
| Missing Redis config | Components implement inconsistent caching | Key collisions, cache invalidation failures |
| No Kafka schemas | Learning signals use ad-hoc formats | Schema evolution breaks consumers |
| No observability | Can't debug psychological reasoning | Black box decisions, no learning attribution |
| No service mesh | Components call each other directly | Cascading failures, no retry logic |

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                                                                                     │
│                           ADAM INFRASTRUCTURE ARCHITECTURE                                          │
│                                                                                                     │
│  ┌─────────────────────────────────────────────────────────────────────────────────────────────┐   │
│  │                                                                                             │   │
│  │   EXTERNAL LAYER                                                                            │   │
│  │   ═══════════════                                                                           │   │
│  │                                                                                             │   │
│  │   ┌─────────────────────────────────────────────────────────────────────────────────────┐  │   │
│  │   │                          KONG API GATEWAY                                           │  │   │
│  │   │   • Rate limiting (per-advertiser, per-endpoint)                                   │  │   │
│  │   │   • JWT/API Key authentication                                                      │  │   │
│  │   │   • Request transformation                                                          │  │   │
│  │   │   • Response caching                                                                │  │   │
│  │   └─────────────────────────────────────────────────────────────────────────────────────┘  │   │
│  │                                              │                                              │   │
│  └──────────────────────────────────────────────┼──────────────────────────────────────────────┘   │
│                                                 │                                                   │
│  ┌──────────────────────────────────────────────┼──────────────────────────────────────────────┐   │
│  │                                              │                                              │   │
│  │   SERVICE MESH LAYER (Linkerd)               │                                              │   │
│  │   ═══════════════════════════                │                                              │   │
│  │                                              ▼                                              │   │
│  │   ┌───────────────┐  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐              │   │
│  │   │ Bidirectional │  │  Blackboard   │  │Meta-Learning  │  │   Gradient    │              │   │
│  │   │    #01        │  │     #02       │  │    #03        │  │   Bridge #06  │              │   │
│  │   └───────┬───────┘  └───────┬───────┘  └───────┬───────┘  └───────┬───────┘              │   │
│  │           │                  │                  │                  │                       │   │
│  │           │    mTLS + Retry + Circuit Breaker + Load Balancing    │                       │   │
│  │           │                                                        │                       │   │
│  │   ┌───────┴──────────────────┴──────────────────┴──────────────────┴───────┐              │   │
│  │   │                        + 25 More ADAM Services                         │              │   │
│  │   └────────────────────────────────────────────────────────────────────────┘              │   │
│  │                                                                                            │   │
│  └────────────────────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                                     │
│  ┌─────────────────────────────────────────────────────────────────────────────────────────────┐   │
│  │                                                                                             │   │
│  │   DATA LAYER                                                                                │   │
│  │   ══════════                                                                                │   │
│  │                                                                                             │   │
│  │   ┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────┐               │   │
│  │   │    REDIS CLUSTER    │  │   KAFKA CLUSTER     │  │   NEO4J CLUSTER     │               │   │
│  │   │                     │  │                     │  │                     │               │   │
│  │   │ • Blackboard state  │  │ • Learning signals  │  │ • Graph database    │               │   │
│  │   │ • Feature cache     │  │ • Outcome events    │  │ • User profiles     │               │   │
│  │   │ • Session state     │  │ • CDC streams       │  │ • Mechanisms        │               │   │
│  │   │ • Hot priors        │  │ • Schema registry   │  │ • Decisions         │               │   │
│  │   │                     │  │                     │  │                     │               │   │
│  │   │ 6 nodes             │  │ 3 brokers           │  │ 3 nodes (existing)  │               │   │
│  │   │ 3 masters/3 replicas│  │ 3x replication      │  │                     │               │   │
│  │   └─────────────────────┘  └─────────────────────┘  └─────────────────────┘               │   │
│  │                                                                                             │   │
│  └─────────────────────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                                     │
│  ┌─────────────────────────────────────────────────────────────────────────────────────────────┐   │
│  │                                                                                             │   │
│  │   OBSERVABILITY LAYER                                                                       │   │
│  │   ═══════════════════                                                                       │   │
│  │                                                                                             │   │
│  │   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                      │   │
│  │   │ Prometheus  │  │  Grafana    │  │   Jaeger    │  │    Loki     │                      │   │
│  │   │             │  │             │  │             │  │             │                      │   │
│  │   │ • Metrics   │  │ • Dashboards│  │ • Traces    │  │ • Logs      │                      │   │
│  │   │ • Alerts    │  │ • Alerts    │  │ • Spans     │  │ • Queries   │                      │   │
│  │   │ • Recording │  │ • Reports   │  │ • Context   │  │ • Retention │                      │   │
│  │   └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘                      │   │
│  │                                                                                             │   │
│  └─────────────────────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                                     │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

# SECTION B: REDIS CLUSTER INFRASTRUCTURE

## Redis Architecture

### Why Redis for ADAM

Redis serves three critical functions in ADAM:

| Function | Component | Latency Requirement | Data Pattern |
|----------|-----------|---------------------|--------------|
| **Blackboard State** | #02 | <5ms | Write-heavy, pub/sub |
| **Feature Cache** | #09, #30 | <3ms | Read-heavy, TTL-based |
| **Hot Priors** | #03, #13 | <2ms | Read-heavy, frequent updates |

### Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Cluster vs. Sentinel** | Cluster | Horizontal scaling for 50K+ keys/sec |
| **Persistence** | RDB + AOF | Balance between recovery speed and durability |
| **Memory Policy** | volatile-lru | Preserve persistent keys, evict cached |
| **Key Prefix Strategy** | Hierarchical | Enables pattern-based operations |

---

## Cluster Topology

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                                                                                         │
│   REDIS CLUSTER TOPOLOGY (6 NODES)                                                     │
│                                                                                         │
│   ┌─────────────────────────────────────────────────────────────────────────────────┐  │
│   │                           HASH SLOT DISTRIBUTION                                │  │
│   │                                                                                 │  │
│   │   Slots 0-5460          Slots 5461-10922        Slots 10923-16383             │  │
│   │   ┌─────────────┐       ┌─────────────┐         ┌─────────────┐               │  │
│   │   │  MASTER-1   │       │  MASTER-2   │         │  MASTER-3   │               │  │
│   │   │             │       │             │         │             │               │  │
│   │   │ 16GB RAM    │       │ 16GB RAM    │         │ 16GB RAM    │               │  │
│   │   │ 4 vCPU      │       │ 4 vCPU      │         │ 4 vCPU      │               │  │
│   │   │             │       │             │         │             │               │  │
│   │   │ • Blackboard│       │ • Profiles  │         │ • Decisions │               │  │
│   │   │   state     │       │ • Features  │         │ • Sessions  │               │  │
│   │   │ • Pub/Sub   │       │ • Hot priors│         │ • Outcomes  │               │  │
│   │   └──────┬──────┘       └──────┬──────┘         └──────┬──────┘               │  │
│   │          │ replication         │ replication          │ replication          │  │
│   │          ▼                     ▼                      ▼                       │  │
│   │   ┌─────────────┐       ┌─────────────┐         ┌─────────────┐               │  │
│   │   │  REPLICA-1  │       │  REPLICA-2  │         │  REPLICA-3  │               │  │
│   │   │             │       │             │         │             │               │  │
│   │   │ 16GB RAM    │       │ 16GB RAM    │         │ 16GB RAM    │               │  │
│   │   │ 4 vCPU      │       │ 4 vCPU      │         │ 4 vCPU      │               │  │
│   │   │             │       │             │         │             │               │  │
│   │   │ Read-only   │       │ Read-only   │         │ Read-only   │               │  │
│   │   │ Failover    │       │ Failover    │         │ Failover    │               │  │
│   │   └─────────────┘       └─────────────┘         └─────────────┘               │  │
│   │                                                                                 │  │
│   └─────────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                         │
│   NODE PLACEMENT:                                                                       │
│   • Masters and replicas in different availability zones                               │
│   • Anti-affinity rules prevent master/replica on same host                            │
│                                                                                         │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

### Cluster Configuration

```python
# =============================================================================
# ADAM Enhancement #29: Redis Cluster Configuration
# Location: adam/infrastructure/redis/config.py
# =============================================================================

"""
Redis Cluster Configuration for ADAM Platform.

This configuration is optimized for:
1. Blackboard shared state with pub/sub
2. Feature cache with TTL eviction
3. Hot priors for real-time inference
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum


class RedisNodeRole(Enum):
    """Redis node roles in cluster."""
    MASTER = "master"
    REPLICA = "replica"


@dataclass
class RedisNodeConfig:
    """Configuration for a single Redis node."""
    node_id: str
    host: str
    port: int = 6379
    role: RedisNodeRole = RedisNodeRole.MASTER
    
    # Resource allocation
    max_memory_gb: int = 16
    max_memory_policy: str = "volatile-lru"
    
    # Slot range (for masters)
    slot_start: Optional[int] = None
    slot_end: Optional[int] = None
    
    # Replication (for replicas)
    master_node_id: Optional[str] = None


@dataclass
class RedisClusterConfig:
    """
    Complete Redis cluster configuration for ADAM.
    
    Topology: 3 masters + 3 replicas = 6 nodes
    Total capacity: 48GB usable (after replication overhead)
    Expected throughput: 100K+ ops/sec
    """
    
    # Cluster identification
    cluster_name: str = "adam-redis-cluster"
    environment: str = "production"
    
    # Node definitions
    nodes: List[RedisNodeConfig] = field(default_factory=lambda: [
        # Masters
        RedisNodeConfig(
            node_id="adam-redis-master-1",
            host="adam-redis-master-1.adam.svc.cluster.local",
            port=6379,
            role=RedisNodeRole.MASTER,
            max_memory_gb=16,
            slot_start=0,
            slot_end=5460,
        ),
        RedisNodeConfig(
            node_id="adam-redis-master-2",
            host="adam-redis-master-2.adam.svc.cluster.local",
            port=6379,
            role=RedisNodeRole.MASTER,
            max_memory_gb=16,
            slot_start=5461,
            slot_end=10922,
        ),
        RedisNodeConfig(
            node_id="adam-redis-master-3",
            host="adam-redis-master-3.adam.svc.cluster.local",
            port=6379,
            role=RedisNodeRole.MASTER,
            max_memory_gb=16,
            slot_start=10923,
            slot_end=16383,
        ),
        # Replicas
        RedisNodeConfig(
            node_id="adam-redis-replica-1",
            host="adam-redis-replica-1.adam.svc.cluster.local",
            port=6379,
            role=RedisNodeRole.REPLICA,
            max_memory_gb=16,
            master_node_id="adam-redis-master-1",
        ),
        RedisNodeConfig(
            node_id="adam-redis-replica-2",
            host="adam-redis-replica-2.adam.svc.cluster.local",
            port=6379,
            role=RedisNodeRole.REPLICA,
            max_memory_gb=16,
            master_node_id="adam-redis-master-2",
        ),
        RedisNodeConfig(
            node_id="adam-redis-replica-3",
            host="adam-redis-replica-3.adam.svc.cluster.local",
            port=6379,
            role=RedisNodeRole.REPLICA,
            max_memory_gb=16,
            master_node_id="adam-redis-master-3",
        ),
    ])
    
    # Persistence configuration
    persistence: Dict = field(default_factory=lambda: {
        "rdb": {
            "enabled": True,
            "save_rules": [
                {"seconds": 900, "changes": 1},      # Save if 1+ changes in 15 min
                {"seconds": 300, "changes": 10},     # Save if 10+ changes in 5 min
                {"seconds": 60, "changes": 10000},   # Save if 10K+ changes in 1 min
            ],
            "compression": True,
            "checksum": True,
        },
        "aof": {
            "enabled": True,
            "appendfsync": "everysec",  # Balance durability/performance
            "rewrite_percentage": 100,
            "rewrite_min_size_mb": 64,
        },
    })
    
    # Connection settings
    connection: Dict = field(default_factory=lambda: {
        "timeout_ms": 5000,
        "tcp_keepalive": 300,
        "tcp_backlog": 511,
    })
    
    # Cluster settings
    cluster: Dict = field(default_factory=lambda: {
        "node_timeout_ms": 15000,
        "replica_validity_factor": 10,
        "migration_barrier": 1,
        "require_full_coverage": False,  # Allow partial availability
    })


# =============================================================================
# REDIS.CONF TEMPLATE
# =============================================================================

REDIS_CONF_TEMPLATE = """
# =============================================================================
# ADAM Redis Configuration
# Generated for: {node_id}
# Role: {role}
# =============================================================================

# NETWORK
bind 0.0.0.0
port {port}
protected-mode no
tcp-backlog 511
timeout 0
tcp-keepalive 300

# GENERAL
daemonize no
supervised no
loglevel notice
logfile ""
databases 16

# MEMORY
maxmemory {max_memory}gb
maxmemory-policy {max_memory_policy}
maxmemory-samples 5

# PERSISTENCE - RDB
save 900 1
save 300 10
save 60 10000
stop-writes-on-bgsave-error yes
rdbcompression yes
rdbchecksum yes
dbfilename dump.rdb

# PERSISTENCE - AOF
appendonly yes
appendfilename "appendonly.aof"
appendfsync everysec
no-appendfsync-on-rewrite no
auto-aof-rewrite-percentage 100
auto-aof-rewrite-min-size 64mb

# CLUSTER
cluster-enabled yes
cluster-config-file nodes-{node_id}.conf
cluster-node-timeout 15000
cluster-replica-validity-factor 10
cluster-migration-barrier 1
cluster-require-full-coverage no

# SLOW LOG
slowlog-log-slower-than 10000
slowlog-max-len 128

# LATENCY MONITORING
latency-monitor-threshold 100

# ADVANCED
hash-max-ziplist-entries 512
hash-max-ziplist-value 64
list-max-ziplist-size -2
set-max-intset-entries 512
zset-max-ziplist-entries 128
zset-max-ziplist-value 64
activerehashing yes
client-output-buffer-limit normal 0 0 0
client-output-buffer-limit replica 256mb 64mb 60
client-output-buffer-limit pubsub 32mb 8mb 60
"""
```

---

## ADAM Key Conventions

### Key Namespace Design

```python
# =============================================================================
# ADAM Enhancement #29: Redis Key Conventions
# Location: adam/infrastructure/redis/keys.py
# =============================================================================

"""
ADAM Redis Key Conventions

All keys follow the pattern:
    adam:{domain}:{entity_type}:{entity_id}[:{sub_key}]

This enables:
1. Pattern-based queries (SCAN adam:profile:*)
2. Clear ownership (which component owns which keys)
3. TTL policies per domain
4. Cache invalidation by prefix
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional
from datetime import timedelta


class KeyDomain(Enum):
    """Top-level key domains in ADAM."""
    
    # Blackboard (#02) - Shared state for request processing
    BLACKBOARD = "blackboard"
    
    # Profile Cache - User psychological profiles
    PROFILE = "profile"
    
    # Feature Cache (#30) - Real-time feature serving
    FEATURE = "feature"
    
    # Decision Cache (#09) - Cached inference decisions
    DECISION = "decision"
    
    # Prior Cache (#03, #13) - Thompson Sampling priors
    PRIOR = "prior"
    
    # Session - User session state
    SESSION = "session"
    
    # Lock - Distributed locks
    LOCK = "lock"
    
    # Counter - Atomic counters
    COUNTER = "counter"
    
    # Pub/Sub Channels
    CHANNEL = "channel"


@dataclass
class KeyConfig:
    """Configuration for a key domain."""
    domain: KeyDomain
    default_ttl: Optional[timedelta]
    description: str
    examples: list


# =============================================================================
# KEY DOMAIN CONFIGURATIONS
# =============================================================================

KEY_CONFIGS = {
    KeyDomain.BLACKBOARD: KeyConfig(
        domain=KeyDomain.BLACKBOARD,
        default_ttl=timedelta(minutes=5),
        description="Shared state during request processing",
        examples=[
            "adam:blackboard:request:req_abc123",
            "adam:blackboard:request:req_abc123:trait_profile",
            "adam:blackboard:request:req_abc123:mechanism_activations",
        ]
    ),
    
    KeyDomain.PROFILE: KeyConfig(
        domain=KeyDomain.PROFILE,
        default_ttl=timedelta(hours=1),
        description="User psychological profiles (L2 cache)",
        examples=[
            "adam:profile:user:user_123",
            "adam:profile:user:user_123:big_five",
            "adam:profile:user:user_123:regulatory_focus",
            "adam:profile:user:user_123:embedding",
        ]
    ),
    
    KeyDomain.FEATURE: KeyConfig(
        domain=KeyDomain.FEATURE,
        default_ttl=timedelta(minutes=15),
        description="Real-time features for inference",
        examples=[
            "adam:feature:user:user_123:personality",
            "adam:feature:user:user_123:journey_state",
            "adam:feature:content:content_456:psychological",
            "adam:feature:ad:ad_789:mechanism_scores",
        ]
    ),
    
    KeyDomain.DECISION: KeyConfig(
        domain=KeyDomain.DECISION,
        default_ttl=timedelta(minutes=30),
        description="Cached inference decisions",
        examples=[
            "adam:decision:user:user_123:ad:ad_789",
            "adam:decision:context:ctx_hash_abc",
        ]
    ),
    
    KeyDomain.PRIOR: KeyConfig(
        domain=KeyDomain.PRIOR,
        default_ttl=timedelta(hours=24),
        description="Thompson Sampling priors (hot cache)",
        examples=[
            "adam:prior:mechanism:social_proof:user:user_123",
            "adam:prior:path:fast:context:ctx_hash",
            "adam:prior:archetype:quality_seeker:category:electronics",
        ]
    ),
    
    KeyDomain.SESSION: KeyConfig(
        domain=KeyDomain.SESSION,
        default_ttl=timedelta(hours=2),
        description="User session state",
        examples=[
            "adam:session:user:user_123",
            "adam:session:user:user_123:journey_position",
            "adam:session:user:user_123:impressions",
        ]
    ),
    
    KeyDomain.LOCK: KeyConfig(
        domain=KeyDomain.LOCK,
        default_ttl=timedelta(seconds=30),
        description="Distributed locks",
        examples=[
            "adam:lock:profile_update:user_123",
            "adam:lock:prior_update:mechanism:social_proof",
        ]
    ),
    
    KeyDomain.COUNTER: KeyConfig(
        domain=KeyDomain.COUNTER,
        default_ttl=None,  # Counters persist
        description="Atomic counters",
        examples=[
            "adam:counter:impressions:user:user_123:daily",
            "adam:counter:conversions:campaign:camp_456",
        ]
    ),
    
    KeyDomain.CHANNEL: KeyConfig(
        domain=KeyDomain.CHANNEL,
        default_ttl=None,  # Channels don't expire
        description="Pub/Sub channels",
        examples=[
            "adam:channel:blackboard:request:req_abc123",
            "adam:channel:learning:outcomes",
            "adam:channel:invalidation:profiles",
        ]
    ),
}


# =============================================================================
# KEY BUILDER
# =============================================================================

class ADAMKeyBuilder:
    """
    Builder for ADAM Redis keys.
    
    Ensures consistent key formatting across all components.
    
    Usage:
        key = ADAMKeyBuilder.profile_key("user_123")
        # Returns: "adam:profile:user:user_123"
        
        key = ADAMKeyBuilder.blackboard_key("req_abc", "trait_profile")
        # Returns: "adam:blackboard:request:req_abc:trait_profile"
    """
    
    @staticmethod
    def _build_key(*parts: str) -> str:
        """Build a Redis key from parts."""
        return ":".join(["adam"] + list(parts))
    
    # =========================================================================
    # BLACKBOARD KEYS (#02)
    # =========================================================================
    
    @classmethod
    def blackboard_key(cls, request_id: str, sub_key: Optional[str] = None) -> str:
        """Key for blackboard request state."""
        if sub_key:
            return cls._build_key("blackboard", "request", request_id, sub_key)
        return cls._build_key("blackboard", "request", request_id)
    
    @classmethod
    def blackboard_channel(cls, request_id: str) -> str:
        """Pub/Sub channel for blackboard updates."""
        return cls._build_key("channel", "blackboard", "request", request_id)
    
    # =========================================================================
    # PROFILE KEYS
    # =========================================================================
    
    @classmethod
    def profile_key(cls, user_id: str, sub_key: Optional[str] = None) -> str:
        """Key for user profile cache."""
        if sub_key:
            return cls._build_key("profile", "user", user_id, sub_key)
        return cls._build_key("profile", "user", user_id)
    
    @classmethod
    def profile_embedding_key(cls, user_id: str) -> str:
        """Key for user embedding vector."""
        return cls._build_key("profile", "user", user_id, "embedding")
    
    # =========================================================================
    # FEATURE KEYS (#30)
    # =========================================================================
    
    @classmethod
    def feature_key(
        cls, 
        entity_type: str, 
        entity_id: str, 
        feature_group: str
    ) -> str:
        """Key for feature cache."""
        return cls._build_key("feature", entity_type, entity_id, feature_group)
    
    @classmethod
    def user_feature_key(cls, user_id: str, feature_group: str) -> str:
        """Key for user features."""
        return cls.feature_key("user", user_id, feature_group)
    
    @classmethod
    def content_feature_key(cls, content_id: str, feature_group: str) -> str:
        """Key for content features."""
        return cls.feature_key("content", content_id, feature_group)
    
    # =========================================================================
    # DECISION KEYS (#09)
    # =========================================================================
    
    @classmethod
    def decision_key(cls, user_id: str, ad_id: str) -> str:
        """Key for cached decision."""
        return cls._build_key("decision", "user", user_id, "ad", ad_id)
    
    @classmethod
    def context_decision_key(cls, context_hash: str) -> str:
        """Key for context-based cached decision."""
        return cls._build_key("decision", "context", context_hash)
    
    # =========================================================================
    # PRIOR KEYS (#03, #13)
    # =========================================================================
    
    @classmethod
    def mechanism_prior_key(cls, mechanism: str, user_id: str) -> str:
        """Key for mechanism effectiveness prior."""
        return cls._build_key("prior", "mechanism", mechanism, "user", user_id)
    
    @classmethod
    def path_prior_key(cls, path: str, context_hash: str) -> str:
        """Key for execution path prior."""
        return cls._build_key("prior", "path", path, "context", context_hash)
    
    @classmethod
    def archetype_prior_key(cls, archetype: str, category: str) -> str:
        """Key for archetype category prior."""
        return cls._build_key("prior", "archetype", archetype, "category", category)
    
    # =========================================================================
    # SESSION KEYS (#10)
    # =========================================================================
    
    @classmethod
    def session_key(cls, user_id: str, sub_key: Optional[str] = None) -> str:
        """Key for user session."""
        if sub_key:
            return cls._build_key("session", "user", user_id, sub_key)
        return cls._build_key("session", "user", user_id)
    
    @classmethod
    def journey_position_key(cls, user_id: str) -> str:
        """Key for user journey position."""
        return cls._build_key("session", "user", user_id, "journey_position")
    
    # =========================================================================
    # LOCK KEYS
    # =========================================================================
    
    @classmethod
    def lock_key(cls, resource_type: str, resource_id: str) -> str:
        """Key for distributed lock."""
        return cls._build_key("lock", resource_type, resource_id)
    
    # =========================================================================
    # COUNTER KEYS
    # =========================================================================
    
    @classmethod
    def counter_key(
        cls, 
        metric: str, 
        entity_type: str, 
        entity_id: str, 
        period: str
    ) -> str:
        """Key for atomic counter."""
        return cls._build_key("counter", metric, entity_type, entity_id, period)
    
    @classmethod
    def impression_counter_key(cls, user_id: str, period: str = "daily") -> str:
        """Key for impression counter."""
        return cls.counter_key("impressions", "user", user_id, period)
    
    # =========================================================================
    # PATTERN BUILDERS (for SCAN operations)
    # =========================================================================
    
    @classmethod
    def pattern_all_profiles(cls) -> str:
        """Pattern for all user profiles."""
        return "adam:profile:user:*"
    
    @classmethod
    def pattern_user_keys(cls, user_id: str) -> str:
        """Pattern for all keys related to a user."""
        return f"adam:*:user:{user_id}*"
    
    @classmethod
    def pattern_blackboard_request(cls, request_id: str) -> str:
        """Pattern for all blackboard keys for a request."""
        return f"adam:blackboard:request:{request_id}*"
```

---

## Lua Scripts for Atomic Operations

```python
# =============================================================================
# ADAM Enhancement #29: Redis Lua Scripts
# Location: adam/infrastructure/redis/lua_scripts.py
# =============================================================================

"""
Redis Lua Scripts for ADAM Atomic Operations.

These scripts ensure atomic operations for:
1. Thompson Sampling prior updates
2. Blackboard state transitions
3. Feature cache with fallback
4. Rate limiting with sliding window
"""

# =============================================================================
# THOMPSON SAMPLING PRIOR UPDATE
# =============================================================================

LUA_THOMPSON_UPDATE = """
--[[
Atomic Thompson Sampling prior update.

Updates alpha/beta parameters of a Beta distribution prior
based on observed outcome (0 or 1).

Keys:
    KEYS[1] - Prior key (hash with alpha, beta, samples)
    
Args:
    ARGV[1] - Outcome (0 or 1)
    ARGV[2] - Weight (typically 1.0)
    ARGV[3] - TTL in seconds
    
Returns:
    JSON with updated alpha, beta, mean, samples
]]--

local key = KEYS[1]
local outcome = tonumber(ARGV[1])
local weight = tonumber(ARGV[2]) or 1.0
local ttl = tonumber(ARGV[3])

-- Get current values or initialize
local alpha = tonumber(redis.call('HGET', key, 'alpha')) or 1.0
local beta = tonumber(redis.call('HGET', key, 'beta')) or 1.0
local samples = tonumber(redis.call('HGET', key, 'samples')) or 0

-- Update based on outcome
if outcome == 1 then
    alpha = alpha + weight
else
    beta = beta + weight
end
samples = samples + 1

-- Calculate mean
local mean = alpha / (alpha + beta)

-- Store updated values
redis.call('HSET', key, 
    'alpha', alpha,
    'beta', beta,
    'samples', samples,
    'mean', mean,
    'updated_at', redis.call('TIME')[1]
)

-- Set TTL if provided
if ttl and ttl > 0 then
    redis.call('EXPIRE', key, ttl)
end

-- Return updated state
return cjson.encode({
    alpha = alpha,
    beta = beta,
    mean = mean,
    samples = samples
})
"""


# =============================================================================
# BLACKBOARD COMPARE-AND-SWAP
# =============================================================================

LUA_BLACKBOARD_CAS = """
--[[
Atomic compare-and-swap for blackboard state.

Only updates if current version matches expected version.
Used to prevent race conditions in concurrent updates.

Keys:
    KEYS[1] - Blackboard state key
    
Args:
    ARGV[1] - Expected version
    ARGV[2] - New value (JSON)
    ARGV[3] - TTL in seconds
    
Returns:
    1 if successful, 0 if version mismatch
]]--

local key = KEYS[1]
local expected_version = tonumber(ARGV[1])
local new_value = ARGV[2]
local ttl = tonumber(ARGV[3])

-- Get current version
local current_version = tonumber(redis.call('HGET', key, 'version')) or 0

-- Check version
if current_version ~= expected_version then
    return 0
end

-- Update with new version
local new_version = current_version + 1
redis.call('HSET', key, 
    'value', new_value,
    'version', new_version,
    'updated_at', redis.call('TIME')[1]
)

-- Set TTL
if ttl and ttl > 0 then
    redis.call('EXPIRE', key, ttl)
end

-- Publish update notification
redis.call('PUBLISH', key .. ':updates', new_version)

return 1
"""


# =============================================================================
# FEATURE CACHE WITH FALLBACK
# =============================================================================

LUA_FEATURE_GET_OR_COMPUTE = """
--[[
Get feature from cache or mark for computation.

If feature exists and is fresh, return it.
If missing or stale, set a computation lock and return nil.

Keys:
    KEYS[1] - Feature cache key
    KEYS[2] - Computation lock key
    
Args:
    ARGV[1] - Max age in seconds (freshness threshold)
    ARGV[2] - Lock TTL in seconds
    
Returns:
    Feature value if fresh, nil if needs computation
]]--

local cache_key = KEYS[1]
local lock_key = KEYS[2]
local max_age = tonumber(ARGV[1])
local lock_ttl = tonumber(ARGV[2])

-- Try to get cached value
local cached = redis.call('HGETALL', cache_key)
if #cached == 0 then
    -- Cache miss - try to acquire computation lock
    local acquired = redis.call('SET', lock_key, '1', 'NX', 'EX', lock_ttl)
    if acquired then
        return cjson.encode({status = 'compute', lock_acquired = true})
    else
        return cjson.encode({status = 'wait', lock_acquired = false})
    end
end

-- Check freshness
local created_at = tonumber(redis.call('HGET', cache_key, 'created_at')) or 0
local current_time = tonumber(redis.call('TIME')[1])
local age = current_time - created_at

if age > max_age then
    -- Stale - try to acquire lock for refresh
    local acquired = redis.call('SET', lock_key, '1', 'NX', 'EX', lock_ttl)
    if acquired then
        return cjson.encode({status = 'refresh', lock_acquired = true, stale_value = cached})
    else
        -- Return stale value while someone else refreshes
        return cjson.encode({status = 'stale', value = cached})
    end
end

-- Fresh cache hit
return cjson.encode({status = 'hit', value = cached})
"""


# =============================================================================
# SLIDING WINDOW RATE LIMITER
# =============================================================================

LUA_RATE_LIMIT = """
--[[
Sliding window rate limiter.

Tracks requests in a sorted set with timestamps as scores.
Removes expired entries and checks against limit.

Keys:
    KEYS[1] - Rate limit key (sorted set)
    
Args:
    ARGV[1] - Window size in seconds
    ARGV[2] - Max requests in window
    ARGV[3] - Current timestamp (microseconds)
    
Returns:
    JSON with allowed (bool), remaining, reset_at
]]--

local key = KEYS[1]
local window = tonumber(ARGV[1])
local max_requests = tonumber(ARGV[2])
local now = tonumber(ARGV[3])

-- Remove expired entries
local cutoff = now - (window * 1000000)
redis.call('ZREMRANGEBYSCORE', key, '-inf', cutoff)

-- Count current entries
local current = redis.call('ZCARD', key)

if current < max_requests then
    -- Add new entry
    redis.call('ZADD', key, now, now)
    redis.call('EXPIRE', key, window)
    
    return cjson.encode({
        allowed = true,
        remaining = max_requests - current - 1,
        reset_at = now + (window * 1000000)
    })
else
    -- Rate limited
    local oldest = redis.call('ZRANGE', key, 0, 0, 'WITHSCORES')[2]
    local reset_at = tonumber(oldest) + (window * 1000000)
    
    return cjson.encode({
        allowed = false,
        remaining = 0,
        reset_at = reset_at
    })
end
"""


# =============================================================================
# BATCH GET WITH PIPELINE
# =============================================================================

LUA_BATCH_GET = """
--[[
Batch get multiple keys with single round trip.

Keys:
    KEYS[1..n] - Keys to retrieve
    
Returns:
    JSON array of values (null for missing keys)
]]--

local results = {}
for i, key in ipairs(KEYS) do
    local value = redis.call('GET', key)
    results[i] = value
end
return cjson.encode(results)
"""


# =============================================================================
# SCRIPT REGISTRY
# =============================================================================

ADAM_LUA_SCRIPTS = {
    "thompson_update": LUA_THOMPSON_UPDATE,
    "blackboard_cas": LUA_BLACKBOARD_CAS,
    "feature_get_or_compute": LUA_FEATURE_GET_OR_COMPUTE,
    "rate_limit": LUA_RATE_LIMIT,
    "batch_get": LUA_BATCH_GET,
}
```

---

## Connection Pooling

```python
# =============================================================================
# ADAM Enhancement #29: Redis Connection Pool
# Location: adam/infrastructure/redis/pool.py
# =============================================================================

"""
Redis Connection Pool for ADAM Services.

Provides:
1. Connection pooling per service instance
2. Automatic cluster topology discovery
3. Read/write splitting
4. Health checking
5. Metrics integration
"""

from dataclasses import dataclass, field
from typing import Dict, Optional, List, Any
from datetime import datetime, timedelta
import asyncio
import logging

logger = logging.getLogger(__name__)


@dataclass
class ConnectionPoolConfig:
    """Configuration for Redis connection pool."""
    
    # Pool sizing
    min_connections: int = 10
    max_connections: int = 100
    
    # Timeouts
    connect_timeout_ms: int = 5000
    socket_timeout_ms: int = 5000
    
    # Retry configuration
    retry_attempts: int = 3
    retry_delay_ms: int = 100
    retry_backoff_multiplier: float = 2.0
    
    # Health checking
    health_check_interval_seconds: int = 30
    max_idle_time_seconds: int = 300
    
    # Read preference
    read_from_replicas: bool = True


@dataclass
class PoolMetrics:
    """Metrics for connection pool monitoring."""
    active_connections: int = 0
    idle_connections: int = 0
    total_connections_created: int = 0
    total_connections_closed: int = 0
    total_commands_sent: int = 0
    total_errors: int = 0
    average_latency_ms: float = 0.0
    p99_latency_ms: float = 0.0


class ADAMRedisPool:
    """
    Production Redis connection pool for ADAM services.
    
    Features:
    - Cluster-aware with automatic slot discovery
    - Read/write splitting (writes to master, reads from replicas)
    - Automatic failover detection
    - Lua script registration
    - Prometheus metrics export
    
    Usage:
        pool = ADAMRedisPool(config)
        await pool.initialize()
        
        # Simple operations
        await pool.set("key", "value")
        value = await pool.get("key")
        
        # Lua scripts
        result = await pool.execute_script("thompson_update", ["key"], [1, 1.0, 3600])
        
        # Pub/Sub
        await pool.publish("channel", "message")
    """
    
    def __init__(
        self,
        cluster_config: 'RedisClusterConfig',
        pool_config: Optional[ConnectionPoolConfig] = None,
        lua_scripts: Optional[Dict[str, str]] = None,
    ):
        self.cluster_config = cluster_config
        self.pool_config = pool_config or ConnectionPoolConfig()
        self.lua_scripts = lua_scripts or {}
        
        self._cluster = None
        self._script_shas: Dict[str, str] = {}
        self._metrics = PoolMetrics()
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize the connection pool."""
        from redis.asyncio.cluster import RedisCluster
        
        # Build startup nodes
        startup_nodes = [
            {"host": node.host, "port": node.port}
            for node in self.cluster_config.nodes
            if node.role.value == "master"
        ]
        
        # Create cluster connection
        self._cluster = RedisCluster(
            startup_nodes=startup_nodes,
            decode_responses=True,
            skip_full_coverage_check=True,
            read_from_replicas=self.pool_config.read_from_replicas,
            socket_timeout=self.pool_config.socket_timeout_ms / 1000,
            socket_connect_timeout=self.pool_config.connect_timeout_ms / 1000,
            retry_on_timeout=True,
            max_connections=self.pool_config.max_connections,
        )
        
        # Register Lua scripts
        for name, script in self.lua_scripts.items():
            sha = await self._cluster.script_load(script)
            self._script_shas[name] = sha
            logger.info(f"Registered Lua script: {name} (SHA: {sha[:8]}...)")
        
        self._initialized = True
        logger.info(f"Redis pool initialized with {len(startup_nodes)} master nodes")
    
    async def close(self) -> None:
        """Close all connections."""
        if self._cluster:
            await self._cluster.close()
        self._initialized = False
    
    # =========================================================================
    # BASIC OPERATIONS
    # =========================================================================
    
    async def get(self, key: str) -> Optional[str]:
        """Get a value by key."""
        self._metrics.total_commands_sent += 1
        return await self._cluster.get(key)
    
    async def set(
        self, 
        key: str, 
        value: str, 
        ttl: Optional[timedelta] = None
    ) -> bool:
        """Set a value with optional TTL."""
        self._metrics.total_commands_sent += 1
        if ttl:
            return await self._cluster.set(key, value, ex=int(ttl.total_seconds()))
        return await self._cluster.set(key, value)
    
    async def delete(self, key: str) -> int:
        """Delete a key."""
        self._metrics.total_commands_sent += 1
        return await self._cluster.delete(key)
    
    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        self._metrics.total_commands_sent += 1
        return bool(await self._cluster.exists(key))
    
    # =========================================================================
    # HASH OPERATIONS
    # =========================================================================
    
    async def hget(self, key: str, field: str) -> Optional[str]:
        """Get hash field."""
        self._metrics.total_commands_sent += 1
        return await self._cluster.hget(key, field)
    
    async def hset(self, key: str, field: str, value: str) -> int:
        """Set hash field."""
        self._metrics.total_commands_sent += 1
        return await self._cluster.hset(key, field, value)
    
    async def hgetall(self, key: str) -> Dict[str, str]:
        """Get all hash fields."""
        self._metrics.total_commands_sent += 1
        return await self._cluster.hgetall(key)
    
    async def hmset(self, key: str, mapping: Dict[str, str]) -> bool:
        """Set multiple hash fields."""
        self._metrics.total_commands_sent += 1
        return await self._cluster.hset(key, mapping=mapping)
    
    # =========================================================================
    # LUA SCRIPT EXECUTION
    # =========================================================================
    
    async def execute_script(
        self,
        script_name: str,
        keys: List[str],
        args: List[Any],
    ) -> Any:
        """
        Execute a registered Lua script.
        
        Args:
            script_name: Name of the registered script
            keys: KEYS array for the script
            args: ARGV array for the script
            
        Returns:
            Script result (decoded from JSON if applicable)
        """
        if script_name not in self._script_shas:
            raise ValueError(f"Unknown script: {script_name}")
        
        self._metrics.total_commands_sent += 1
        sha = self._script_shas[script_name]
        
        try:
            result = await self._cluster.evalsha(sha, len(keys), *keys, *args)
            return result
        except Exception as e:
            self._metrics.total_errors += 1
            logger.error(f"Script execution failed: {script_name}, error: {e}")
            raise
    
    # =========================================================================
    # PUB/SUB
    # =========================================================================
    
    async def publish(self, channel: str, message: str) -> int:
        """Publish message to channel."""
        self._metrics.total_commands_sent += 1
        return await self._cluster.publish(channel, message)
    
    async def subscribe(self, channel: str):
        """Subscribe to channel. Returns async generator."""
        pubsub = self._cluster.pubsub()
        await pubsub.subscribe(channel)
        return pubsub
    
    # =========================================================================
    # METRICS EXPORT
    # =========================================================================
    
    def get_metrics(self) -> PoolMetrics:
        """Get current pool metrics."""
        return self._metrics
    
    async def export_prometheus_metrics(self) -> Dict[str, float]:
        """Export metrics in Prometheus format."""
        return {
            "adam_redis_active_connections": self._metrics.active_connections,
            "adam_redis_idle_connections": self._metrics.idle_connections,
            "adam_redis_commands_total": self._metrics.total_commands_sent,
            "adam_redis_errors_total": self._metrics.total_errors,
            "adam_redis_latency_avg_ms": self._metrics.average_latency_ms,
            "adam_redis_latency_p99_ms": self._metrics.p99_latency_ms,
        }
```

---

## Persistence and Backup

```yaml
# =============================================================================
# ADAM Enhancement #29: Redis Backup Configuration
# Location: infrastructure/redis/backup-config.yaml
# =============================================================================

# Backup strategy for ADAM Redis cluster
backup:
  # RDB snapshots
  rdb:
    enabled: true
    schedule: "0 */4 * * *"  # Every 4 hours
    retention_days: 7
    storage:
      type: s3
      bucket: adam-redis-backups
      prefix: rdb/
      encryption: AES256
  
  # AOF backups (for point-in-time recovery)
  aof:
    enabled: true
    schedule: "0 * * * *"  # Hourly
    retention_days: 2
    storage:
      type: s3
      bucket: adam-redis-backups
      prefix: aof/
      encryption: AES256
  
  # Pre-backup validation
  validation:
    check_cluster_health: true
    check_replication_lag: true
    max_replication_lag_seconds: 10
  
  # Post-backup actions
  post_backup:
    verify_integrity: true
    notify_on_failure: true
    notification_channel: "#adam-alerts"

# Recovery procedures
recovery:
  # Point-in-time recovery
  pitr:
    enabled: true
    max_recovery_time_objective: "1 hour"
    
  # Disaster recovery
  dr:
    enabled: true
    target_region: us-west-2
    sync_interval_minutes: 60
```

---

# SECTION C: KAFKA EVENT STREAMING

## Kafka Architecture

### Why Kafka for ADAM

Kafka serves as the **nervous system** for ADAM's learning architecture:

| Function | Topic Pattern | Consumers |
|----------|---------------|-----------|
| **Learning Signals** | `adam.signals.*` | Meta-Learner, Gradient Bridge, All components |
| **Outcome Events** | `adam.outcomes.*` | Gradient Bridge, Analytics |
| **Profile Updates** | `adam.profiles.*` | Feature Store, Cache Invalidation |
| **CDC Streams** | `adam.cdc.*` | Neo4j sync, Audit |

### Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Message Format** | Avro + Schema Registry | Schema evolution, type safety |
| **Partitioning** | By user_id (consistent hash) | Maintain user event ordering |
| **Replication** | Factor of 3 | High availability |
| **Retention** | 7 days signals, 30 days outcomes | Balance storage vs. replay capability |

---

## Topic Definitions

```python
# =============================================================================
# ADAM Enhancement #29: Kafka Topic Definitions
# Location: adam/infrastructure/kafka/topics.py
# =============================================================================

"""
Kafka Topic Definitions for ADAM Platform.

Topics are organized by:
1. Learning signals (real-time component communication)
2. Outcome events (conversion, engagement tracking)
3. Profile updates (cache invalidation, sync)
4. System events (health, alerts)
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum


class TopicCategory(Enum):
    """Categories of Kafka topics in ADAM."""
    SIGNALS = "signals"
    OUTCOMES = "outcomes"
    PROFILES = "profiles"
    CDC = "cdc"
    SYSTEM = "system"


class CleanupPolicy(Enum):
    """Kafka cleanup policies."""
    DELETE = "delete"
    COMPACT = "compact"
    COMPACT_DELETE = "compact,delete"


@dataclass
class TopicConfig:
    """Configuration for a Kafka topic."""
    name: str
    category: TopicCategory
    partitions: int
    replication_factor: int = 3
    retention_ms: int = 604800000  # 7 days default
    cleanup_policy: CleanupPolicy = CleanupPolicy.DELETE
    
    # Message configuration
    max_message_bytes: int = 1048576  # 1MB
    
    # Compression
    compression_type: str = "lz4"
    
    # Schema
    key_schema: Optional[str] = None
    value_schema: str = ""
    
    description: str = ""


# =============================================================================
# LEARNING SIGNAL TOPICS
# =============================================================================

LEARNING_SIGNAL_TOPICS = [
    TopicConfig(
        name="adam.signals.learning",
        category=TopicCategory.SIGNALS,
        partitions=24,
        retention_ms=604800000,  # 7 days
        key_schema="string",  # component_id
        value_schema="adam.signals.LearningSignal",
        description="Cross-component learning signals from Gradient Bridge",
    ),
    
    TopicConfig(
        name="adam.signals.mechanism_activation",
        category=TopicCategory.SIGNALS,
        partitions=12,
        retention_ms=604800000,
        key_schema="string",  # user_id
        value_schema="adam.signals.MechanismActivation",
        description="Cognitive mechanism activation events",
    ),
    
    TopicConfig(
        name="adam.signals.decision",
        category=TopicCategory.SIGNALS,
        partitions=24,
        retention_ms=604800000,
        key_schema="string",  # request_id
        value_schema="adam.signals.Decision",
        description="Ad serving decisions with full context",
    ),
    
    TopicConfig(
        name="adam.signals.state_transition",
        category=TopicCategory.SIGNALS,
        partitions=12,
        retention_ms=604800000,
        key_schema="string",  # user_id
        value_schema="adam.signals.StateTransition",
        description="User journey state transitions",
    ),
    
    TopicConfig(
        name="adam.signals.prior_update",
        category=TopicCategory.SIGNALS,
        partitions=12,
        retention_ms=259200000,  # 3 days
        key_schema="string",  # prior_key
        value_schema="adam.signals.PriorUpdate",
        description="Thompson Sampling prior updates",
    ),
]


# =============================================================================
# OUTCOME TOPICS
# =============================================================================

OUTCOME_TOPICS = [
    TopicConfig(
        name="adam.outcomes.impressions",
        category=TopicCategory.OUTCOMES,
        partitions=48,  # High volume
        retention_ms=2592000000,  # 30 days
        key_schema="string",  # impression_id
        value_schema="adam.outcomes.Impression",
        description="Ad impression events",
    ),
    
    TopicConfig(
        name="adam.outcomes.clicks",
        category=TopicCategory.OUTCOMES,
        partitions=24,
        retention_ms=2592000000,
        key_schema="string",  # impression_id
        value_schema="adam.outcomes.Click",
        description="Ad click events",
    ),
    
    TopicConfig(
        name="adam.outcomes.conversions",
        category=TopicCategory.OUTCOMES,
        partitions=12,
        retention_ms=2592000000,
        key_schema="string",  # conversion_id
        value_schema="adam.outcomes.Conversion",
        description="Conversion events with attribution",
    ),
    
    TopicConfig(
        name="adam.outcomes.engagements",
        category=TopicCategory.OUTCOMES,
        partitions=24,
        retention_ms=2592000000,
        key_schema="string",  # engagement_id
        value_schema="adam.outcomes.Engagement",
        description="Engagement events (scroll, dwell, etc.)",
    ),
]


# =============================================================================
# PROFILE UPDATE TOPICS
# =============================================================================

PROFILE_TOPICS = [
    TopicConfig(
        name="adam.profiles.updates",
        category=TopicCategory.PROFILES,
        partitions=12,
        retention_ms=604800000,
        cleanup_policy=CleanupPolicy.COMPACT,
        key_schema="string",  # user_id
        value_schema="adam.profiles.ProfileUpdate",
        description="User profile updates (compacted)",
    ),
    
    TopicConfig(
        name="adam.profiles.invalidations",
        category=TopicCategory.PROFILES,
        partitions=12,
        retention_ms=86400000,  # 1 day
        key_schema="string",  # user_id
        value_schema="adam.profiles.Invalidation",
        description="Cache invalidation signals",
    ),
]


# =============================================================================
# CDC TOPICS (Change Data Capture from Neo4j)
# =============================================================================

CDC_TOPICS = [
    TopicConfig(
        name="adam.cdc.neo4j.users",
        category=TopicCategory.CDC,
        partitions=12,
        retention_ms=604800000,
        cleanup_policy=CleanupPolicy.COMPACT,
        key_schema="string",  # user_id
        value_schema="adam.cdc.UserChange",
        description="Neo4j User node changes",
    ),
    
    TopicConfig(
        name="adam.cdc.neo4j.mechanisms",
        category=TopicCategory.CDC,
        partitions=6,
        retention_ms=604800000,
        cleanup_policy=CleanupPolicy.COMPACT,
        key_schema="string",  # mechanism_id
        value_schema="adam.cdc.MechanismChange",
        description="Neo4j Mechanism node changes",
    ),
    
    TopicConfig(
        name="adam.cdc.neo4j.decisions",
        category=TopicCategory.CDC,
        partitions=24,
        retention_ms=2592000000,  # 30 days
        key_schema="string",  # decision_id
        value_schema="adam.cdc.DecisionRecord",
        description="Neo4j Decision records for audit",
    ),
]


# =============================================================================
# SYSTEM TOPICS
# =============================================================================

SYSTEM_TOPICS = [
    TopicConfig(
        name="adam.system.health",
        category=TopicCategory.SYSTEM,
        partitions=6,
        retention_ms=86400000,  # 1 day
        key_schema="string",  # service_id
        value_schema="adam.system.HealthStatus",
        description="Service health heartbeats",
    ),
    
    TopicConfig(
        name="adam.system.alerts",
        category=TopicCategory.SYSTEM,
        partitions=3,
        retention_ms=604800000,
        key_schema="string",  # alert_id
        value_schema="adam.system.Alert",
        description="System alerts and anomalies",
    ),
]


# =============================================================================
# ALL TOPICS
# =============================================================================

ALL_TOPICS = (
    LEARNING_SIGNAL_TOPICS + 
    OUTCOME_TOPICS + 
    PROFILE_TOPICS + 
    CDC_TOPICS + 
    SYSTEM_TOPICS
)


def get_topic_by_name(name: str) -> Optional[TopicConfig]:
    """Get topic configuration by name."""
    for topic in ALL_TOPICS:
        if topic.name == name:
            return topic
    return None


def get_topics_by_category(category: TopicCategory) -> List[TopicConfig]:
    """Get all topics in a category."""
    return [t for t in ALL_TOPICS if t.category == category]
```

---

## Avro Schema Registry

```python
# =============================================================================
# ADAM Enhancement #29: Avro Schema Definitions
# Location: adam/infrastructure/kafka/schemas.py
# =============================================================================

"""
Avro Schema Definitions for ADAM Kafka Topics.

Schemas are registered with Confluent Schema Registry.
Uses namespace 'adam' for all schemas.
"""

from typing import Dict

# =============================================================================
# LEARNING SIGNAL SCHEMA
# =============================================================================

LEARNING_SIGNAL_SCHEMA = {
    "type": "record",
    "name": "LearningSignal",
    "namespace": "adam.signals",
    "doc": "Cross-component learning signal propagated via Gradient Bridge",
    "fields": [
        {
            "name": "signal_id",
            "type": "string",
            "doc": "Unique identifier for the signal"
        },
        {
            "name": "source_component",
            "type": "string",
            "doc": "Component that emitted the signal (e.g., 'mechanism_detector')"
        },
        {
            "name": "source_entity_type",
            "type": "string",
            "doc": "Type of entity that triggered signal (e.g., 'user', 'decision')"
        },
        {
            "name": "source_entity_id",
            "type": "string",
            "doc": "ID of the triggering entity"
        },
        {
            "name": "signal_type",
            "type": {
                "type": "enum",
                "name": "SignalType",
                "symbols": [
                    "MECHANISM_ACTIVATION",
                    "STATE_TRANSITION",
                    "DECISION_MADE",
                    "OUTCOME_OBSERVED",
                    "PRIOR_UPDATE",
                    "CONFIDENCE_UPDATE",
                    "EMBEDDING_UPDATE"
                ]
            },
            "doc": "Type of learning signal"
        },
        {
            "name": "signal_data",
            "type": {
                "type": "map",
                "values": "string"
            },
            "doc": "Signal-specific data as key-value pairs"
        },
        {
            "name": "target_components",
            "type": {
                "type": "array",
                "items": "string"
            },
            "doc": "Components that should process this signal"
        },
        {
            "name": "confidence",
            "type": "double",
            "doc": "Confidence in the signal (0.0-1.0)"
        },
        {
            "name": "timestamp",
            "type": "long",
            "logicalType": "timestamp-millis",
            "doc": "When the signal was generated"
        },
        {
            "name": "trace_id",
            "type": ["null", "string"],
            "default": None,
            "doc": "Distributed trace ID for debugging"
        },
        {
            "name": "request_id",
            "type": ["null", "string"],
            "default": None,
            "doc": "Original request ID if applicable"
        }
    ]
}


# =============================================================================
# MECHANISM ACTIVATION SCHEMA
# =============================================================================

MECHANISM_ACTIVATION_SCHEMA = {
    "type": "record",
    "name": "MechanismActivation",
    "namespace": "adam.signals",
    "doc": "Record of cognitive mechanism activation",
    "fields": [
        {
            "name": "activation_id",
            "type": "string"
        },
        {
            "name": "user_id",
            "type": "string"
        },
        {
            "name": "mechanism_id",
            "type": {
                "type": "enum",
                "name": "CognitiveMechanism",
                "symbols": [
                    "AUTOMATIC_EVALUATION",
                    "WANTING_LIKING",
                    "EVOLUTIONARY_MOTIVE",
                    "LINGUISTIC_FRAMING",
                    "MIMETIC_DESIRE",
                    "EMBODIED_COGNITION",
                    "ATTENTION_DYNAMICS",
                    "IDENTITY_CONSTRUCTION",
                    "TEMPORAL_CONSTRUAL"
                ]
            }
        },
        {
            "name": "activation_strength",
            "type": "double",
            "doc": "Activation strength (0.0-1.0)"
        },
        {
            "name": "triggering_signals",
            "type": {
                "type": "array",
                "items": "string"
            },
            "doc": "Signals that triggered this activation"
        },
        {
            "name": "context",
            "type": {
                "type": "record",
                "name": "ActivationContext",
                "fields": [
                    {"name": "content_id", "type": ["null", "string"], "default": None},
                    {"name": "ad_id", "type": ["null", "string"], "default": None},
                    {"name": "session_id", "type": ["null", "string"], "default": None},
                    {"name": "journey_state", "type": ["null", "string"], "default": None}
                ]
            }
        },
        {
            "name": "predicted_effectiveness",
            "type": "double"
        },
        {
            "name": "timestamp",
            "type": "long",
            "logicalType": "timestamp-millis"
        }
    ]
}


# =============================================================================
# OUTCOME SCHEMAS
# =============================================================================

IMPRESSION_SCHEMA = {
    "type": "record",
    "name": "Impression",
    "namespace": "adam.outcomes",
    "doc": "Ad impression event",
    "fields": [
        {"name": "impression_id", "type": "string"},
        {"name": "user_id", "type": "string"},
        {"name": "ad_id", "type": "string"},
        {"name": "campaign_id", "type": "string"},
        {"name": "advertiser_id", "type": "string"},
        {
            "name": "decision_context",
            "type": {
                "type": "record",
                "name": "DecisionContext",
                "fields": [
                    {"name": "decision_id", "type": "string"},
                    {"name": "execution_path", "type": "string"},
                    {"name": "mechanism_scores", "type": {"type": "map", "values": "double"}},
                    {"name": "personality_match_score", "type": "double"},
                    {"name": "journey_state", "type": ["null", "string"], "default": None}
                ]
            }
        },
        {
            "name": "inventory",
            "type": {
                "type": "record",
                "name": "InventoryInfo",
                "fields": [
                    {"name": "publisher_id", "type": "string"},
                    {"name": "placement_id", "type": "string"},
                    {"name": "content_id", "type": ["null", "string"], "default": None},
                    {"name": "inventory_type", "type": "string"}
                ]
            }
        },
        {"name": "bid_price_cpm", "type": "double"},
        {"name": "win_price_cpm", "type": "double"},
        {"name": "viewability_predicted", "type": "double"},
        {"name": "timestamp", "type": "long", "logicalType": "timestamp-millis"}
    ]
}


CONVERSION_SCHEMA = {
    "type": "record",
    "name": "Conversion",
    "namespace": "adam.outcomes",
    "doc": "Conversion event with attribution",
    "fields": [
        {"name": "conversion_id", "type": "string"},
        {"name": "user_id", "type": "string"},
        {"name": "conversion_type", "type": "string"},  # "purchase", "signup", "lead"
        {"name": "conversion_value", "type": "double"},
        {
            "name": "attribution",
            "type": {
                "type": "record",
                "name": "Attribution",
                "fields": [
                    {"name": "attributed_impression_id", "type": ["null", "string"], "default": None},
                    {"name": "attributed_ad_id", "type": ["null", "string"], "default": None},
                    {"name": "attributed_mechanism", "type": ["null", "string"], "default": None},
                    {"name": "attribution_model", "type": "string"},  # "last_touch", "mechanism_weighted"
                    {"name": "confidence", "type": "double"}
                ]
            }
        },
        {
            "name": "touchpoints",
            "type": {
                "type": "array",
                "items": {
                    "type": "record",
                    "name": "Touchpoint",
                    "fields": [
                        {"name": "impression_id", "type": "string"},
                        {"name": "ad_id", "type": "string"},
                        {"name": "mechanism_activated", "type": ["null", "string"], "default": None},
                        {"name": "journey_state", "type": ["null", "string"], "default": None},
                        {"name": "timestamp", "type": "long", "logicalType": "timestamp-millis"}
                    ]
                }
            }
        },
        {"name": "timestamp", "type": "long", "logicalType": "timestamp-millis"}
    ]
}


# =============================================================================
# PROFILE UPDATE SCHEMA
# =============================================================================

PROFILE_UPDATE_SCHEMA = {
    "type": "record",
    "name": "ProfileUpdate",
    "namespace": "adam.profiles",
    "doc": "User profile update event",
    "fields": [
        {"name": "user_id", "type": "string"},
        {"name": "update_type", "type": "string"},  # "trait", "state", "embedding"
        {
            "name": "trait_updates",
            "type": ["null", {
                "type": "map",
                "values": "double"
            }],
            "default": None,
            "doc": "Updated trait values"
        },
        {
            "name": "state_updates",
            "type": ["null", {
                "type": "map",
                "values": "double"
            }],
            "default": None,
            "doc": "Updated state values"
        },
        {
            "name": "embedding_update",
            "type": ["null", {
                "type": "array",
                "items": "float"
            }],
            "default": None,
            "doc": "Updated embedding vector"
        },
        {"name": "confidence", "type": "double"},
        {"name": "source_signals", "type": {"type": "array", "items": "string"}},
        {"name": "timestamp", "type": "long", "logicalType": "timestamp-millis"}
    ]
}


# =============================================================================
# SCHEMA REGISTRY
# =============================================================================

ADAM_SCHEMAS: Dict[str, dict] = {
    "adam.signals.LearningSignal": LEARNING_SIGNAL_SCHEMA,
    "adam.signals.MechanismActivation": MECHANISM_ACTIVATION_SCHEMA,
    "adam.outcomes.Impression": IMPRESSION_SCHEMA,
    "adam.outcomes.Conversion": CONVERSION_SCHEMA,
    "adam.profiles.ProfileUpdate": PROFILE_UPDATE_SCHEMA,
}
```

---

## Consumer Group Strategy

```python
# =============================================================================
# ADAM Enhancement #29: Kafka Consumer Configuration
# Location: adam/infrastructure/kafka/consumers.py
# =============================================================================

"""
Kafka Consumer Group Strategy for ADAM.

Consumer groups are organized by:
1. Component ownership (each component owns its consumer group)
2. Processing requirements (real-time vs batch)
3. Isolation (failures in one group don't affect others)
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum


class ProcessingMode(Enum):
    """Consumer processing modes."""
    REAL_TIME = "real_time"      # Low latency, at-least-once
    BATCH = "batch"              # High throughput, exactly-once
    STREAMING = "streaming"      # Continuous, at-least-once


@dataclass
class ConsumerGroupConfig:
    """Configuration for a Kafka consumer group."""
    group_id: str
    topics: List[str]
    processing_mode: ProcessingMode
    
    # Consumer configuration
    max_poll_records: int = 500
    max_poll_interval_ms: int = 300000
    session_timeout_ms: int = 30000
    heartbeat_interval_ms: int = 10000
    
    # Offset management
    auto_offset_reset: str = "earliest"
    enable_auto_commit: bool = False
    
    # Parallelism
    num_consumers: int = 3
    
    # Component ownership
    owning_component: str = ""
    description: str = ""


# =============================================================================
# CONSUMER GROUP DEFINITIONS
# =============================================================================

CONSUMER_GROUPS = [
    # =========================================================================
    # GRADIENT BRIDGE (#06) - Central learning hub
    # =========================================================================
    ConsumerGroupConfig(
        group_id="adam-gradient-bridge",
        topics=[
            "adam.signals.learning",
            "adam.outcomes.impressions",
            "adam.outcomes.conversions",
        ],
        processing_mode=ProcessingMode.STREAMING,
        max_poll_records=1000,
        num_consumers=6,
        owning_component="gradient_bridge",
        description="Processes all learning signals and outcomes for cross-component attribution",
    ),
    
    # =========================================================================
    # META-LEARNER (#03) - Execution path optimization
    # =========================================================================
    ConsumerGroupConfig(
        group_id="adam-meta-learner",
        topics=[
            "adam.signals.learning",
            "adam.signals.prior_update",
        ],
        processing_mode=ProcessingMode.REAL_TIME,
        max_poll_records=500,
        num_consumers=3,
        owning_component="meta_learner",
        description="Updates Thompson Sampling priors based on outcomes",
    ),
    
    # =========================================================================
    # FEATURE STORE (#30) - Profile sync
    # =========================================================================
    ConsumerGroupConfig(
        group_id="adam-feature-store",
        topics=[
            "adam.profiles.updates",
            "adam.profiles.invalidations",
        ],
        processing_mode=ProcessingMode.REAL_TIME,
        max_poll_records=500,
        num_consumers=3,
        owning_component="feature_store",
        description="Keeps feature cache synchronized with profile updates",
    ),
    
    # =========================================================================
    # JOURNEY TRACKER (#10) - State transitions
    # =========================================================================
    ConsumerGroupConfig(
        group_id="adam-journey-tracker",
        topics=[
            "adam.signals.state_transition",
            "adam.outcomes.impressions",
        ],
        processing_mode=ProcessingMode.STREAMING,
        max_poll_records=500,
        num_consumers=3,
        owning_component="journey_tracker",
        description="Tracks user journey state based on engagement signals",
    ),
    
    # =========================================================================
    # COPY GENERATION (#15) - Effectiveness learning
    # =========================================================================
    ConsumerGroupConfig(
        group_id="adam-copy-generation",
        topics=[
            "adam.signals.learning",
            "adam.outcomes.conversions",
        ],
        processing_mode=ProcessingMode.BATCH,
        max_poll_records=1000,
        num_consumers=2,
        owning_component="copy_generation",
        description="Learns which copy variants perform best per segment",
    ),
    
    # =========================================================================
    # ANALYTICS (Batch processing)
    # =========================================================================
    ConsumerGroupConfig(
        group_id="adam-analytics-batch",
        topics=[
            "adam.outcomes.impressions",
            "adam.outcomes.clicks",
            "adam.outcomes.conversions",
            "adam.signals.decision",
        ],
        processing_mode=ProcessingMode.BATCH,
        max_poll_records=5000,
        max_poll_interval_ms=600000,  # 10 minutes
        num_consumers=2,
        owning_component="analytics",
        description="Batch processing for reporting and model training",
    ),
    
    # =========================================================================
    # CDC PROCESSOR - Neo4j sync
    # =========================================================================
    ConsumerGroupConfig(
        group_id="adam-cdc-processor",
        topics=[
            "adam.cdc.neo4j.users",
            "adam.cdc.neo4j.mechanisms",
            "adam.cdc.neo4j.decisions",
        ],
        processing_mode=ProcessingMode.STREAMING,
        max_poll_records=500,
        num_consumers=2,
        owning_component="cdc_processor",
        description="Processes Neo4j change data capture for downstream sync",
    ),
]


def get_consumer_group(group_id: str) -> Optional[ConsumerGroupConfig]:
    """Get consumer group configuration by ID."""
    for group in CONSUMER_GROUPS:
        if group.group_id == group_id:
            return group
    return None


def get_groups_for_component(component: str) -> List[ConsumerGroupConfig]:
    """Get all consumer groups owned by a component."""
    return [g for g in CONSUMER_GROUPS if g.owning_component == component]


# =============================================================================
# EXACTLY-ONCE SEMANTICS CONFIGURATION
# =============================================================================

EXACTLY_ONCE_CONFIG = {
    "producer": {
        "enable.idempotence": True,
        "acks": "all",
        "retries": 2147483647,  # Integer max
        "max.in.flight.requests.per.connection": 5,
        "transactional.id.prefix": "adam-",
    },
    "consumer": {
        "isolation.level": "read_committed",
        "enable.auto.commit": False,
    },
}


---

# SECTION D: SERVICE MESH & API GATEWAY

## Linkerd Service Mesh

### Why Linkerd for ADAM

Linkerd provides the **communication fabric** for ADAM's microservices:

| Feature | ADAM Use Case |
|---------|---------------|
| **mTLS** | Encrypt all inter-service traffic (psychological data!) |
| **Load Balancing** | EWMA for latency-sensitive inference paths |
| **Retries** | Automatic retry on transient failures |
| **Circuit Breakers** | Prevent cascade failures during load spikes |
| **Observability** | Golden metrics for all service pairs |

### Service Mesh Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                                                                                         │
│   LINKERD SERVICE MESH ARCHITECTURE                                                    │
│                                                                                         │
│   ┌─────────────────────────────────────────────────────────────────────────────────┐  │
│   │                                                                                 │  │
│   │                            CONTROL PLANE                                        │  │
│   │                                                                                 │  │
│   │   ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐               │  │
│   │   │   Destination   │  │   Identity      │  │   Proxy         │               │  │
│   │   │   Controller    │  │   Controller    │  │   Injector      │               │  │
│   │   │                 │  │                 │  │                 │               │  │
│   │   │ • Service       │  │ • mTLS certs    │  │ • Auto-inject   │               │  │
│   │   │   discovery     │  │ • SPIFFE IDs    │  │   sidecars      │               │  │
│   │   │ • Traffic split │  │ • Rotation      │  │ • Annotations   │               │  │
│   │   └─────────────────┘  └─────────────────┘  └─────────────────┘               │  │
│   │                                                                                 │  │
│   └─────────────────────────────────────────────────────────────────────────────────┘  │
│                                              │                                          │
│                                              │ mTLS Certificates                        │
│                                              ▼                                          │
│   ┌─────────────────────────────────────────────────────────────────────────────────┐  │
│   │                                                                                 │  │
│   │                            DATA PLANE (Per Pod)                                 │  │
│   │                                                                                 │  │
│   │   ┌─────────────────────────────────────────────────────────────────────────┐  │  │
│   │   │  ┌───────────┐                                          ┌───────────┐  │  │  │
│   │   │  │ Inference │                                          │ Gradient  │  │  │  │
│   │   │  │ Engine    │                                          │ Bridge    │  │  │  │
│   │   │  │ Pod       │                                          │ Pod       │  │  │  │
│   │   │  │           │                                          │           │  │  │  │
│   │   │  │ ┌───────┐ │    mTLS    ┌─────────┐    mTLS          │ ┌───────┐ │  │  │  │
│   │   │  │ │ App   │◄┼───────────►│ Linkerd │◄─────────────────┼►│ App   │ │  │  │  │
│   │   │  │ │       │ │            │ Proxy   │                   │ │       │ │  │  │  │
│   │   │  │ └───────┘ │            │         │                   │ └───────┘ │  │  │  │
│   │   │  │ ┌───────┐ │            │ • L7 LB │                   │ ┌───────┐ │  │  │  │
│   │   │  │ │Linkerd│ │            │ • Retry │                   │ │Linkerd│ │  │  │  │
│   │   │  │ │ Proxy │ │            │ • C.B.  │                   │ │ Proxy │ │  │  │  │
│   │   │  │ └───────┘ │            │ • Trace │                   │ └───────┘ │  │  │  │
│   │   │  └───────────┘            └─────────┘                   └───────────┘  │  │  │
│   │   │                                                                         │  │  │
│   │   └─────────────────────────────────────────────────────────────────────────┘  │  │
│   │                                                                                 │  │
│   └─────────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                         │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

### Linkerd Configuration

```python
# =============================================================================
# ADAM Enhancement #29: Linkerd Service Mesh Configuration
# Location: adam/infrastructure/linkerd/config.py
# =============================================================================

"""
Linkerd Service Mesh Configuration for ADAM Platform.

Provides:
1. mTLS encryption for all service-to-service traffic
2. Intelligent load balancing (EWMA for latency-sensitive paths)
3. Automatic retries with configurable budgets
4. Circuit breakers to prevent cascade failures
5. Golden metrics export to Prometheus
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum


class LoadBalancingAlgorithm(Enum):
    """Linkerd load balancing algorithms."""
    EWMA = "ewma"  # Exponentially Weighted Moving Average - latency-aware
    ROUND_ROBIN = "round_robin"
    PEAK_EWMA = "peak_ewma"  # More aggressive latency weighting


class RetryBudget(Enum):
    """Retry budget configurations."""
    AGGRESSIVE = "aggressive"  # 100% retry ratio, 10 retries/sec
    MODERATE = "moderate"      # 20% retry ratio, 5 retries/sec
    CONSERVATIVE = "conservative"  # 10% retry ratio, 2 retries/sec
    NONE = "none"  # No retries


@dataclass
class ServiceProfile:
    """
    Linkerd ServiceProfile configuration for an ADAM service.
    
    ServiceProfiles enable:
    - Per-route metrics and retries
    - Timeouts per endpoint
    - Traffic policies
    """
    service_name: str
    namespace: str = "adam"
    
    # Default timeout for all routes
    timeout: str = "30s"
    
    # Retry configuration
    retry_budget: RetryBudget = RetryBudget.MODERATE
    retryable_statuses: List[int] = field(default_factory=lambda: [502, 503, 504])
    
    # Load balancing
    load_balancing: LoadBalancingAlgorithm = LoadBalancingAlgorithm.EWMA
    
    # Routes with specific configurations
    routes: List['RouteConfig'] = field(default_factory=list)


@dataclass
class RouteConfig:
    """Configuration for a specific route in a ServiceProfile."""
    name: str
    condition_path_regex: str
    condition_method: str = "POST"
    
    # Override defaults
    timeout: Optional[str] = None
    is_retryable: bool = True
    
    # ADAM-specific
    is_inference_path: bool = False  # If True, use stricter latency budgets


# =============================================================================
# ADAM SERVICE PROFILES
# =============================================================================

ADAM_SERVICE_PROFILES = [
    # =========================================================================
    # INFERENCE ENGINE (#09) - Latency Critical
    # =========================================================================
    ServiceProfile(
        service_name="adam-inference-engine",
        namespace="adam",
        timeout="100ms",  # Strict for real-time
        retry_budget=RetryBudget.CONSERVATIVE,  # Retries add latency
        load_balancing=LoadBalancingAlgorithm.PEAK_EWMA,  # Aggressive latency
        routes=[
            RouteConfig(
                name="serve-ad-decision",
                condition_path_regex="/api/v1/decisions/serve",
                timeout="50ms",
                is_retryable=False,  # Too slow to retry
                is_inference_path=True,
            ),
            RouteConfig(
                name="get-profile",
                condition_path_regex="/api/v1/profiles/.*",
                timeout="30ms",
                is_retryable=True,
                is_inference_path=True,
            ),
        ],
    ),
    
    # =========================================================================
    # BLACKBOARD (#02) - Fast Shared State
    # =========================================================================
    ServiceProfile(
        service_name="adam-blackboard",
        namespace="adam",
        timeout="50ms",
        retry_budget=RetryBudget.MODERATE,
        load_balancing=LoadBalancingAlgorithm.EWMA,
        routes=[
            RouteConfig(
                name="read-state",
                condition_path_regex="/api/v1/state/.*",
                condition_method="GET",
                timeout="20ms",
                is_retryable=True,
            ),
            RouteConfig(
                name="write-state",
                condition_path_regex="/api/v1/state/.*",
                condition_method="POST",
                timeout="30ms",
                is_retryable=True,
            ),
            RouteConfig(
                name="subscribe",
                condition_path_regex="/api/v1/subscribe/.*",
                timeout="5s",  # Long poll
                is_retryable=False,
            ),
        ],
    ),
    
    # =========================================================================
    # GRADIENT BRIDGE (#06) - Learning Signals
    # =========================================================================
    ServiceProfile(
        service_name="adam-gradient-bridge",
        namespace="adam",
        timeout="500ms",  # Signal processing can be slower
        retry_budget=RetryBudget.AGGRESSIVE,  # Must not lose signals
        load_balancing=LoadBalancingAlgorithm.ROUND_ROBIN,
        routes=[
            RouteConfig(
                name="emit-signal",
                condition_path_regex="/api/v1/signals/emit",
                timeout="200ms",
                is_retryable=True,
            ),
            RouteConfig(
                name="query-signals",
                condition_path_regex="/api/v1/signals/query",
                condition_method="GET",
                timeout="1s",
                is_retryable=True,
            ),
        ],
    ),
    
    # =========================================================================
    # META-LEARNER (#03) - Thompson Sampling
    # =========================================================================
    ServiceProfile(
        service_name="adam-meta-learner",
        namespace="adam",
        timeout="200ms",
        retry_budget=RetryBudget.MODERATE,
        load_balancing=LoadBalancingAlgorithm.EWMA,
        routes=[
            RouteConfig(
                name="select-path",
                condition_path_regex="/api/v1/paths/select",
                timeout="50ms",
                is_retryable=True,
                is_inference_path=True,
            ),
            RouteConfig(
                name="update-prior",
                condition_path_regex="/api/v1/priors/update",
                timeout="100ms",
                is_retryable=True,
            ),
        ],
    ),
    
    # =========================================================================
    # FEATURE STORE (#30) - Real-Time Serving
    # =========================================================================
    ServiceProfile(
        service_name="adam-feature-store",
        namespace="adam",
        timeout="50ms",
        retry_budget=RetryBudget.CONSERVATIVE,
        load_balancing=LoadBalancingAlgorithm.PEAK_EWMA,
        routes=[
            RouteConfig(
                name="get-features",
                condition_path_regex="/api/v1/features/.*",
                condition_method="GET",
                timeout="10ms",  # Sub-10ms requirement
                is_retryable=True,
                is_inference_path=True,
            ),
            RouteConfig(
                name="batch-features",
                condition_path_regex="/api/v1/features/batch",
                timeout="30ms",
                is_retryable=True,
            ),
        ],
    ),
    
    # =========================================================================
    # AD DESK (#28) - WPP Integration
    # =========================================================================
    ServiceProfile(
        service_name="adam-ad-desk",
        namespace="adam",
        timeout="5s",  # Complex operations
        retry_budget=RetryBudget.MODERATE,
        load_balancing=LoadBalancingAlgorithm.EWMA,
        routes=[
            RouteConfig(
                name="match-inventory",
                condition_path_regex="/api/v2/match/.*",
                timeout="3s",
                is_retryable=True,
            ),
            RouteConfig(
                name="impression-decision",
                condition_path_regex="/api/v2/sequences/impression-decision",
                timeout="50ms",  # Real-time bidding
                is_retryable=False,
                is_inference_path=True,
            ),
        ],
    ),
]


# =============================================================================
# LINKERD YAML GENERATION
# =============================================================================

def generate_service_profile_yaml(profile: ServiceProfile) -> str:
    """Generate Linkerd ServiceProfile YAML for a service."""
    
    routes_yaml = ""
    for route in profile.routes:
        timeout = route.timeout or profile.timeout
        routes_yaml += f"""
  - name: {route.name}
    condition:
      method: {route.condition_method}
      pathRegex: {route.condition_path_regex}
    timeout: {timeout}
    isRetryable: {str(route.is_retryable).lower()}"""
    
    # Retry budget configuration
    retry_configs = {
        RetryBudget.AGGRESSIVE: "retryRatio: 1.0\nminRetriesPerSecond: 10\nttl: 30s",
        RetryBudget.MODERATE: "retryRatio: 0.2\nminRetriesPerSecond: 5\nttl: 30s",
        RetryBudget.CONSERVATIVE: "retryRatio: 0.1\nminRetriesPerSecond: 2\nttl: 30s",
        RetryBudget.NONE: "",
    }
    
    retry_yaml = retry_configs.get(profile.retry_budget, "")
    retry_section = f"""
  retryBudget:
    {retry_yaml}""" if retry_yaml else ""
    
    return f"""apiVersion: linkerd.io/v1alpha2
kind: ServiceProfile
metadata:
  name: {profile.service_name}.{profile.namespace}.svc.cluster.local
  namespace: {profile.namespace}
spec:
  routes:{routes_yaml}
{retry_section}
"""


# =============================================================================
# TRAFFIC SPLIT CONFIGURATION (Canary Deployments)
# =============================================================================

@dataclass
class TrafficSplit:
    """Traffic split configuration for canary deployments."""
    service_name: str
    namespace: str = "adam"
    
    # Weight distribution
    primary_weight: int = 90
    canary_weight: int = 10
    
    # Canary service suffix
    canary_suffix: str = "-canary"


def generate_traffic_split_yaml(split: TrafficSplit) -> str:
    """Generate Linkerd TrafficSplit YAML."""
    return f"""apiVersion: split.smi-spec.io/v1alpha3
kind: TrafficSplit
metadata:
  name: {split.service_name}-split
  namespace: {split.namespace}
spec:
  service: {split.service_name}
  backends:
  - service: {split.service_name}
    weight: {split.primary_weight}
  - service: {split.service_name}{split.canary_suffix}
    weight: {split.canary_weight}
"""
```

---

## Kong API Gateway

### Why Kong for ADAM

Kong serves as the **single entry point** for all external traffic:

| Feature | ADAM Use Case |
|---------|---------------|
| **Rate Limiting** | Per-advertiser, per-endpoint quotas |
| **Authentication** | API keys, JWT validation |
| **Request Transform** | Header injection, body modification |
| **Response Caching** | Cache profile lookups |
| **Analytics** | Traffic monitoring per client |

### Kong Configuration

```python
# =============================================================================
# ADAM Enhancement #29: Kong API Gateway Configuration
# Location: adam/infrastructure/kong/config.py
# =============================================================================

"""
Kong API Gateway Configuration for ADAM Platform.

Provides:
1. Rate limiting per advertiser/endpoint
2. API key and JWT authentication
3. Request/response transformation
4. Response caching for profile lookups
5. Traffic analytics and monitoring
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum


class RateLimitWindow(Enum):
    """Rate limit time windows."""
    SECOND = "second"
    MINUTE = "minute"
    HOUR = "hour"
    DAY = "day"


class AuthMethod(Enum):
    """Authentication methods."""
    API_KEY = "api_key"
    JWT = "jwt"
    OAUTH2 = "oauth2"
    NONE = "none"


@dataclass
class RateLimitConfig:
    """Rate limiting configuration for an endpoint."""
    window: RateLimitWindow
    limit: int
    
    # Apply per consumer (advertiser)
    per_consumer: bool = True
    
    # Fallback limit if consumer not identified
    anonymous_limit: Optional[int] = None


@dataclass
class RouteConfig:
    """Kong route configuration."""
    name: str
    path: str
    methods: List[str]
    
    # Target service
    service_host: str
    service_port: int = 80
    
    # Authentication
    auth_method: AuthMethod = AuthMethod.API_KEY
    
    # Rate limiting
    rate_limits: List[RateLimitConfig] = field(default_factory=list)
    
    # Caching
    cache_ttl_seconds: Optional[int] = None
    
    # Request transformation
    add_headers: Dict[str, str] = field(default_factory=dict)
    
    # ADAM-specific
    is_inference_path: bool = False
    requires_advertiser_context: bool = True


# =============================================================================
# ADAM ROUTE DEFINITIONS
# =============================================================================

ADAM_ROUTES = [
    # =========================================================================
    # INFERENCE API - Real-time ad serving
    # =========================================================================
    RouteConfig(
        name="inference-serve",
        path="/api/v1/decisions/serve",
        methods=["POST"],
        service_host="adam-inference-engine.adam.svc.cluster.local",
        service_port=8080,
        auth_method=AuthMethod.API_KEY,
        rate_limits=[
            RateLimitConfig(window=RateLimitWindow.SECOND, limit=1000),
            RateLimitConfig(window=RateLimitWindow.MINUTE, limit=50000),
        ],
        add_headers={"X-ADAM-Request-Type": "inference"},
        is_inference_path=True,
    ),
    
    RouteConfig(
        name="inference-batch",
        path="/api/v1/decisions/batch",
        methods=["POST"],
        service_host="adam-inference-engine.adam.svc.cluster.local",
        service_port=8080,
        auth_method=AuthMethod.API_KEY,
        rate_limits=[
            RateLimitConfig(window=RateLimitWindow.SECOND, limit=100),
            RateLimitConfig(window=RateLimitWindow.MINUTE, limit=5000),
        ],
    ),
    
    # =========================================================================
    # PROFILE API - User psychological profiles
    # =========================================================================
    RouteConfig(
        name="profile-get",
        path="/api/v1/profiles/{user_id}",
        methods=["GET"],
        service_host="adam-feature-store.adam.svc.cluster.local",
        service_port=8080,
        auth_method=AuthMethod.API_KEY,
        rate_limits=[
            RateLimitConfig(window=RateLimitWindow.SECOND, limit=500),
        ],
        cache_ttl_seconds=60,  # Cache profile lookups
    ),
    
    RouteConfig(
        name="profile-batch",
        path="/api/v1/profiles/batch",
        methods=["POST"],
        service_host="adam-feature-store.adam.svc.cluster.local",
        service_port=8080,
        auth_method=AuthMethod.API_KEY,
        rate_limits=[
            RateLimitConfig(window=RateLimitWindow.SECOND, limit=50),
        ],
    ),
    
    # =========================================================================
    # AD DESK API (#28) - WPP Integration
    # =========================================================================
    RouteConfig(
        name="ad-desk-match",
        path="/api/v2/match/{product_id}",
        methods=["GET", "POST"],
        service_host="adam-ad-desk.adam.svc.cluster.local",
        service_port=8080,
        auth_method=AuthMethod.JWT,
        rate_limits=[
            RateLimitConfig(window=RateLimitWindow.MINUTE, limit=100),
            RateLimitConfig(window=RateLimitWindow.HOUR, limit=2000),
        ],
        requires_advertiser_context=True,
    ),
    
    RouteConfig(
        name="ad-desk-sequence",
        path="/api/v2/sequences/*",
        methods=["GET", "POST"],
        service_host="adam-ad-desk.adam.svc.cluster.local",
        service_port=8080,
        auth_method=AuthMethod.JWT,
        rate_limits=[
            RateLimitConfig(window=RateLimitWindow.SECOND, limit=1000),  # Bid-time
        ],
        is_inference_path=True,
    ),
    
    RouteConfig(
        name="ad-desk-supply-path",
        path="/api/v2/supply-paths/*",
        methods=["GET", "POST"],
        service_host="adam-ad-desk.adam.svc.cluster.local",
        service_port=8080,
        auth_method=AuthMethod.JWT,
        rate_limits=[
            RateLimitConfig(window=RateLimitWindow.MINUTE, limit=500),
        ],
    ),
    
    # =========================================================================
    # LEARNING API - Outcome reporting
    # =========================================================================
    RouteConfig(
        name="outcomes-impression",
        path="/api/v1/outcomes/impressions",
        methods=["POST"],
        service_host="adam-gradient-bridge.adam.svc.cluster.local",
        service_port=8080,
        auth_method=AuthMethod.API_KEY,
        rate_limits=[
            RateLimitConfig(window=RateLimitWindow.SECOND, limit=5000),
            RateLimitConfig(window=RateLimitWindow.MINUTE, limit=200000),
        ],
    ),
    
    RouteConfig(
        name="outcomes-conversion",
        path="/api/v1/outcomes/conversions",
        methods=["POST"],
        service_host="adam-gradient-bridge.adam.svc.cluster.local",
        service_port=8080,
        auth_method=AuthMethod.API_KEY,
        rate_limits=[
            RateLimitConfig(window=RateLimitWindow.SECOND, limit=500),
        ],
    ),
    
    # =========================================================================
    # HEALTH & MONITORING
    # =========================================================================
    RouteConfig(
        name="health",
        path="/health",
        methods=["GET"],
        service_host="adam-gateway-health.adam.svc.cluster.local",
        service_port=8080,
        auth_method=AuthMethod.NONE,
        rate_limits=[],
        requires_advertiser_context=False,
    ),
    
    RouteConfig(
        name="metrics",
        path="/metrics",
        methods=["GET"],
        service_host="adam-gateway-metrics.adam.svc.cluster.local",
        service_port=8080,
        auth_method=AuthMethod.API_KEY,  # Internal only
        rate_limits=[],
        requires_advertiser_context=False,
    ),
]


# =============================================================================
# KONG DECLARATIVE CONFIGURATION GENERATOR
# =============================================================================

def generate_kong_config() -> str:
    """Generate Kong declarative configuration (YAML)."""
    
    services = []
    routes = []
    plugins = []
    
    for route in ADAM_ROUTES:
        # Service definition
        service_name = f"adam-{route.name}-service"
        services.append({
            "name": service_name,
            "url": f"http://{route.service_host}:{route.service_port}",
            "connect_timeout": 5000,
            "read_timeout": 30000 if not route.is_inference_path else 100,
            "write_timeout": 30000 if not route.is_inference_path else 100,
        })
        
        # Route definition
        routes.append({
            "name": route.name,
            "service": service_name,
            "paths": [route.path],
            "methods": route.methods,
            "strip_path": False,
            "preserve_host": True,
        })
        
        # Authentication plugin
        if route.auth_method != AuthMethod.NONE:
            plugins.append({
                "name": "key-auth" if route.auth_method == AuthMethod.API_KEY else "jwt",
                "route": route.name,
                "config": {
                    "key_names": ["X-API-Key", "apikey"],
                    "hide_credentials": True,
                } if route.auth_method == AuthMethod.API_KEY else {},
            })
        
        # Rate limiting plugins
        for rl in route.rate_limits:
            plugins.append({
                "name": "rate-limiting",
                "route": route.name,
                "config": {
                    f"{rl.window.value}": rl.limit,
                    "policy": "redis",
                    "redis_host": "adam-redis-master-1.adam.svc.cluster.local",
                    "redis_port": 6379,
                    "fault_tolerant": True,
                    "hide_client_headers": False,
                },
            })
        
        # Response caching
        if route.cache_ttl_seconds:
            plugins.append({
                "name": "proxy-cache",
                "route": route.name,
                "config": {
                    "strategy": "memory",
                    "content_type": ["application/json"],
                    "cache_ttl": route.cache_ttl_seconds,
                    "cache_control": True,
                },
            })
        
        # Request transformation
        if route.add_headers:
            plugins.append({
                "name": "request-transformer",
                "route": route.name,
                "config": {
                    "add": {
                        "headers": [f"{k}:{v}" for k, v in route.add_headers.items()]
                    }
                },
            })
    
    # Generate YAML
    import yaml
    config = {
        "_format_version": "3.0",
        "services": services,
        "routes": routes,
        "plugins": plugins,
    }
    
    return yaml.dump(config, default_flow_style=False, sort_keys=False)


# =============================================================================
# CONSUMER (ADVERTISER) CONFIGURATION
# =============================================================================

@dataclass
class AdvertiserConsumer:
    """Kong consumer configuration for an advertiser."""
    advertiser_id: str
    name: str
    
    # API key
    api_key: str
    
    # Custom rate limits (override defaults)
    custom_rate_limits: Dict[str, int] = field(default_factory=dict)
    
    # Tier determines base rate limits
    tier: str = "standard"  # standard, premium, enterprise


ADVERTISER_TIERS = {
    "standard": {
        "requests_per_second": 100,
        "requests_per_minute": 5000,
        "requests_per_hour": 100000,
    },
    "premium": {
        "requests_per_second": 500,
        "requests_per_minute": 25000,
        "requests_per_hour": 500000,
    },
    "enterprise": {
        "requests_per_second": 2000,
        "requests_per_minute": 100000,
        "requests_per_hour": 2000000,
    },
}
```

---

# SECTION E: OBSERVABILITY STACK

## Prometheus Metrics

### ADAM Metrics Philosophy

Observability for a psychological intelligence platform differs from generic web apps:

| Standard Metrics | ADAM Additions |
|------------------|----------------|
| Request latency | **Mechanism activation latency** |
| Error rate | **Psychological inference confidence** |
| Throughput | **Learning signal propagation rate** |
| Saturation | **Thompson Sampling update rate** |

### Prometheus Configuration

```python
# =============================================================================
# ADAM Enhancement #29: Prometheus Metrics Configuration
# Location: adam/infrastructure/prometheus/config.py
# =============================================================================

"""
Prometheus Metrics Configuration for ADAM Platform.

Defines:
1. Standard service metrics (RED method)
2. ADAM-specific psychological metrics
3. Learning loop metrics
4. Business outcome metrics
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum


class MetricType(Enum):
    """Prometheus metric types."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


@dataclass
class MetricDefinition:
    """Definition of a Prometheus metric."""
    name: str
    type: MetricType
    help: str
    labels: List[str] = field(default_factory=list)
    
    # Histogram buckets
    buckets: Optional[List[float]] = None


# =============================================================================
# STANDARD SERVICE METRICS (RED Method)
# =============================================================================

STANDARD_METRICS = [
    MetricDefinition(
        name="adam_http_requests_total",
        type=MetricType.COUNTER,
        help="Total HTTP requests",
        labels=["service", "method", "path", "status_code"],
    ),
    MetricDefinition(
        name="adam_http_request_duration_seconds",
        type=MetricType.HISTOGRAM,
        help="HTTP request latency",
        labels=["service", "method", "path"],
        buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
    ),
    MetricDefinition(
        name="adam_http_request_size_bytes",
        type=MetricType.HISTOGRAM,
        help="HTTP request size",
        labels=["service", "method", "path"],
        buckets=[100, 1000, 10000, 100000, 1000000],
    ),
    MetricDefinition(
        name="adam_http_response_size_bytes",
        type=MetricType.HISTOGRAM,
        help="HTTP response size",
        labels=["service", "method", "path"],
        buckets=[100, 1000, 10000, 100000, 1000000],
    ),
]


# =============================================================================
# ADAM PSYCHOLOGICAL METRICS
# =============================================================================

PSYCHOLOGICAL_METRICS = [
    # =========================================================================
    # MECHANISM ACTIVATION METRICS
    # =========================================================================
    MetricDefinition(
        name="adam_mechanism_activation_total",
        type=MetricType.COUNTER,
        help="Total mechanism activations",
        labels=["mechanism", "user_segment", "content_type"],
    ),
    MetricDefinition(
        name="adam_mechanism_activation_strength",
        type=MetricType.HISTOGRAM,
        help="Mechanism activation strength distribution",
        labels=["mechanism"],
        buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
    ),
    MetricDefinition(
        name="adam_mechanism_effectiveness",
        type=MetricType.GAUGE,
        help="Current mechanism effectiveness (Thompson Sampling mean)",
        labels=["mechanism", "user_segment", "category"],
    ),
    
    # =========================================================================
    # PSYCHOLOGICAL INFERENCE METRICS
    # =========================================================================
    MetricDefinition(
        name="adam_trait_inference_total",
        type=MetricType.COUNTER,
        help="Total trait inferences performed",
        labels=["trait", "inference_method"],
    ),
    MetricDefinition(
        name="adam_trait_inference_confidence",
        type=MetricType.HISTOGRAM,
        help="Confidence distribution of trait inferences",
        labels=["trait"],
        buckets=[0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 0.99],
    ),
    MetricDefinition(
        name="adam_state_detection_total",
        type=MetricType.COUNTER,
        help="Total state detections performed",
        labels=["state_type"],
    ),
    MetricDefinition(
        name="adam_arousal_level",
        type=MetricType.HISTOGRAM,
        help="Detected arousal level distribution",
        labels=["content_type", "time_of_day"],
        buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
    ),
    MetricDefinition(
        name="adam_construal_level",
        type=MetricType.HISTOGRAM,
        help="Detected construal level distribution",
        labels=["content_type", "journey_state"],
        buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
    ),
    
    # =========================================================================
    # MENTAL HEALTH SAFEGUARD METRICS
    # =========================================================================
    MetricDefinition(
        name="adam_vulnerability_exclusions_total",
        type=MetricType.COUNTER,
        help="Exclusions due to elevated vulnerability",
        labels=["risk_level", "excluded_mechanism"],
    ),
    MetricDefinition(
        name="adam_risk_score",
        type=MetricType.HISTOGRAM,
        help="Distribution of detected risk scores",
        labels=[],
        buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
    ),
]


# =============================================================================
# LEARNING LOOP METRICS
# =============================================================================

LEARNING_METRICS = [
    # =========================================================================
    # GRADIENT BRIDGE METRICS
    # =========================================================================
    MetricDefinition(
        name="adam_learning_signals_total",
        type=MetricType.COUNTER,
        help="Total learning signals emitted",
        labels=["source_component", "target_component", "signal_type"],
    ),
    MetricDefinition(
        name="adam_learning_signal_latency_seconds",
        type=MetricType.HISTOGRAM,
        help="Latency from event to signal emission",
        labels=["source_component"],
        buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0],
    ),
    MetricDefinition(
        name="adam_learning_signal_propagation_seconds",
        type=MetricType.HISTOGRAM,
        help="End-to-end signal propagation latency",
        labels=["source_component", "target_component"],
        buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 5.0, 10.0],
    ),
    
    # =========================================================================
    # THOMPSON SAMPLING METRICS
    # =========================================================================
    MetricDefinition(
        name="adam_thompson_updates_total",
        type=MetricType.COUNTER,
        help="Total Thompson Sampling prior updates",
        labels=["prior_type", "outcome"],
    ),
    MetricDefinition(
        name="adam_thompson_alpha",
        type=MetricType.GAUGE,
        help="Current Thompson Sampling alpha parameter",
        labels=["prior_type", "entity_id"],
    ),
    MetricDefinition(
        name="adam_thompson_beta",
        type=MetricType.GAUGE,
        help="Current Thompson Sampling beta parameter",
        labels=["prior_type", "entity_id"],
    ),
    MetricDefinition(
        name="adam_thompson_samples",
        type=MetricType.GAUGE,
        help="Total samples for Thompson Sampling prior",
        labels=["prior_type", "entity_id"],
    ),
    MetricDefinition(
        name="adam_exploration_rate",
        type=MetricType.GAUGE,
        help="Current exploration vs exploitation ratio",
        labels=["context_type"],
    ),
    
    # =========================================================================
    # META-LEARNER METRICS
    # =========================================================================
    MetricDefinition(
        name="adam_execution_path_selections_total",
        type=MetricType.COUNTER,
        help="Total execution path selections",
        labels=["selected_path", "context_type"],
    ),
    MetricDefinition(
        name="adam_path_regret",
        type=MetricType.GAUGE,
        help="Estimated regret for path selection",
        labels=["path"],
    ),
]


# =============================================================================
# BUSINESS OUTCOME METRICS
# =============================================================================

BUSINESS_METRICS = [
    MetricDefinition(
        name="adam_impressions_total",
        type=MetricType.COUNTER,
        help="Total ad impressions served",
        labels=["advertiser", "campaign", "mechanism"],
    ),
    MetricDefinition(
        name="adam_conversions_total",
        type=MetricType.COUNTER,
        help="Total conversions attributed",
        labels=["advertiser", "campaign", "mechanism", "attribution_model"],
    ),
    MetricDefinition(
        name="adam_conversion_value_dollars",
        type=MetricType.COUNTER,
        help="Total conversion value in dollars",
        labels=["advertiser", "campaign"],
    ),
    MetricDefinition(
        name="adam_conversion_rate",
        type=MetricType.GAUGE,
        help="Rolling conversion rate",
        labels=["advertiser", "campaign", "mechanism"],
    ),
    MetricDefinition(
        name="adam_cpm_dollars",
        type=MetricType.HISTOGRAM,
        help="CPM distribution",
        labels=["advertiser", "supply_path"],
        buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 50.0],
    ),
]


# =============================================================================
# INFRASTRUCTURE METRICS
# =============================================================================

INFRASTRUCTURE_METRICS = [
    # Redis
    MetricDefinition(
        name="adam_redis_commands_total",
        type=MetricType.COUNTER,
        help="Total Redis commands executed",
        labels=["command", "key_prefix"],
    ),
    MetricDefinition(
        name="adam_redis_latency_seconds",
        type=MetricType.HISTOGRAM,
        help="Redis command latency",
        labels=["command"],
        buckets=[0.0001, 0.0005, 0.001, 0.005, 0.01, 0.05, 0.1],
    ),
    
    # Kafka
    MetricDefinition(
        name="adam_kafka_messages_produced_total",
        type=MetricType.COUNTER,
        help="Total Kafka messages produced",
        labels=["topic"],
    ),
    MetricDefinition(
        name="adam_kafka_messages_consumed_total",
        type=MetricType.COUNTER,
        help="Total Kafka messages consumed",
        labels=["topic", "consumer_group"],
    ),
    MetricDefinition(
        name="adam_kafka_consumer_lag",
        type=MetricType.GAUGE,
        help="Kafka consumer lag (messages behind)",
        labels=["topic", "consumer_group", "partition"],
    ),
    
    # Neo4j
    MetricDefinition(
        name="adam_neo4j_queries_total",
        type=MetricType.COUNTER,
        help="Total Neo4j queries executed",
        labels=["query_type"],
    ),
    MetricDefinition(
        name="adam_neo4j_query_duration_seconds",
        type=MetricType.HISTOGRAM,
        help="Neo4j query duration",
        labels=["query_type"],
        buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0],
    ),
]


# =============================================================================
# ALL METRICS
# =============================================================================

ALL_METRICS = (
    STANDARD_METRICS +
    PSYCHOLOGICAL_METRICS +
    LEARNING_METRICS +
    BUSINESS_METRICS +
    INFRASTRUCTURE_METRICS
)
```

---

## Grafana Dashboards

### Dashboard Organization

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                                                                                         │
│   ADAM GRAFANA DASHBOARD HIERARCHY                                                     │
│                                                                                         │
│   ┌─────────────────────────────────────────────────────────────────────────────────┐  │
│   │  EXECUTIVE OVERVIEW                                                             │  │
│   │  • Business KPIs (conversions, revenue, ROI)                                   │  │
│   │  • System health summary                                                        │  │
│   │  • Advertiser performance                                                       │  │
│   └─────────────────────────────────────────────────────────────────────────────────┘  │
│                           │                                                             │
│           ┌───────────────┼───────────────┬───────────────┐                            │
│           ▼               ▼               ▼               ▼                            │
│   ┌───────────────┐ ┌───────────────┐ ┌───────────────┐ ┌───────────────┐             │
│   │ Psychological │ │  Learning     │ │ Infrastructure│ │  Service      │             │
│   │ Intelligence  │ │  Loop         │ │  Health       │ │  Performance  │             │
│   │               │ │               │ │               │ │               │             │
│   │ • Mechanism   │ │ • Signal flow │ │ • Redis       │ │ • Latency     │             │
│   │   activations │ │ • Thompson    │ │ • Kafka       │ │ • Error rates │             │
│   │ • Trait       │ │   updates     │ │ • Neo4j       │ │ • Throughput  │             │
│   │   inference   │ │ • Path regret │ │ • Linkerd     │ │ • Saturation  │             │
│   │ • State       │ │               │ │               │ │               │             │
│   │   detection   │ │               │ │               │ │               │             │
│   └───────────────┘ └───────────────┘ └───────────────┘ └───────────────┘             │
│           │               │               │               │                            │
│           ▼               ▼               ▼               ▼                            │
│   ┌───────────────────────────────────────────────────────────────────────────────┐   │
│   │                         COMPONENT DASHBOARDS                                   │   │
│   │                                                                                │   │
│   │  #01 Bidirectional  #02 Blackboard  #03 Meta-Learner  #06 Gradient Bridge    │   │
│   │  #09 Inference      #10 Journey     #15 Copy Gen      #28 Ad Desk            │   │
│   │  #29 Infrastructure #30 Feature Store  #31 Event Bus  ...                     │   │
│   └───────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                         │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

### Dashboard JSON Definition

```python
# =============================================================================
# ADAM Enhancement #29: Grafana Dashboard Definitions
# Location: adam/infrastructure/grafana/dashboards.py
# =============================================================================

"""
Grafana Dashboard Definitions for ADAM Platform.

Dashboards are organized by:
1. Executive Overview - Business KPIs
2. Psychological Intelligence - Mechanism/trait/state monitoring
3. Learning Loop - Signal propagation, Thompson Sampling
4. Infrastructure - Redis, Kafka, Neo4j health
5. Component-specific dashboards
"""

from typing import Dict, List, Any


# =============================================================================
# EXECUTIVE OVERVIEW DASHBOARD
# =============================================================================

EXECUTIVE_DASHBOARD = {
    "title": "ADAM Executive Overview",
    "uid": "adam-executive",
    "tags": ["adam", "executive", "kpi"],
    "refresh": "30s",
    "panels": [
        {
            "title": "Conversion Rate (24h)",
            "type": "stat",
            "gridPos": {"x": 0, "y": 0, "w": 6, "h": 4},
            "targets": [{
                "expr": "sum(rate(adam_conversions_total[24h])) / sum(rate(adam_impressions_total[24h]))",
                "legendFormat": "Conversion Rate"
            }],
            "fieldConfig": {
                "defaults": {
                    "unit": "percentunit",
                    "thresholds": {
                        "steps": [
                            {"value": 0, "color": "red"},
                            {"value": 0.01, "color": "yellow"},
                            {"value": 0.02, "color": "green"},
                        ]
                    }
                }
            }
        },
        {
            "title": "Total Revenue (24h)",
            "type": "stat",
            "gridPos": {"x": 6, "y": 0, "w": 6, "h": 4},
            "targets": [{
                "expr": "sum(increase(adam_conversion_value_dollars[24h]))",
                "legendFormat": "Revenue"
            }],
            "fieldConfig": {
                "defaults": {
                    "unit": "currencyUSD",
                }
            }
        },
        {
            "title": "Impressions/sec",
            "type": "timeseries",
            "gridPos": {"x": 0, "y": 4, "w": 12, "h": 8},
            "targets": [{
                "expr": "sum(rate(adam_impressions_total[5m]))",
                "legendFormat": "Impressions/sec"
            }],
        },
        {
            "title": "Mechanism Effectiveness",
            "type": "table",
            "gridPos": {"x": 12, "y": 0, "w": 12, "h": 12},
            "targets": [{
                "expr": "adam_mechanism_effectiveness",
                "format": "table",
                "instant": True,
            }],
            "transformations": [
                {"id": "sortBy", "options": {"sort": [{"field": "Value", "desc": True}]}}
            ],
        },
    ]
}


# =============================================================================
# PSYCHOLOGICAL INTELLIGENCE DASHBOARD
# =============================================================================

PSYCHOLOGICAL_DASHBOARD = {
    "title": "ADAM Psychological Intelligence",
    "uid": "adam-psychological",
    "tags": ["adam", "psychological", "mechanisms"],
    "refresh": "10s",
    "panels": [
        {
            "title": "Mechanism Activations by Type",
            "type": "timeseries",
            "gridPos": {"x": 0, "y": 0, "w": 12, "h": 8},
            "targets": [{
                "expr": "sum(rate(adam_mechanism_activation_total[5m])) by (mechanism)",
                "legendFormat": "{{mechanism}}"
            }],
        },
        {
            "title": "Activation Strength Distribution",
            "type": "heatmap",
            "gridPos": {"x": 12, "y": 0, "w": 12, "h": 8},
            "targets": [{
                "expr": "sum(rate(adam_mechanism_activation_strength_bucket[5m])) by (le, mechanism)",
                "legendFormat": "{{mechanism}} {{le}}"
            }],
        },
        {
            "title": "Trait Inference Confidence",
            "type": "timeseries",
            "gridPos": {"x": 0, "y": 8, "w": 12, "h": 8},
            "targets": [{
                "expr": "histogram_quantile(0.5, sum(rate(adam_trait_inference_confidence_bucket[5m])) by (le, trait))",
                "legendFormat": "{{trait}} p50"
            }],
        },
        {
            "title": "Vulnerability Exclusions",
            "type": "timeseries",
            "gridPos": {"x": 12, "y": 8, "w": 12, "h": 8},
            "targets": [{
                "expr": "sum(rate(adam_vulnerability_exclusions_total[5m])) by (risk_level)",
                "legendFormat": "Risk: {{risk_level}}"
            }],
            "alert": {
                "name": "High Vulnerability Exclusions",
                "conditions": [{
                    "evaluator": {"type": "gt", "params": [100]},
                    "operator": {"type": "and"},
                    "query": {"params": ["A", "5m", "now"]},
                }],
            }
        },
    ]
}


# =============================================================================
# LEARNING LOOP DASHBOARD
# =============================================================================

LEARNING_LOOP_DASHBOARD = {
    "title": "ADAM Learning Loop",
    "uid": "adam-learning",
    "tags": ["adam", "learning", "gradient-bridge"],
    "refresh": "10s",
    "panels": [
        {
            "title": "Learning Signal Flow",
            "type": "nodeGraph",
            "gridPos": {"x": 0, "y": 0, "w": 24, "h": 10},
            "description": "Visualization of learning signal propagation between components",
        },
        {
            "title": "Signal Latency",
            "type": "timeseries",
            "gridPos": {"x": 0, "y": 10, "w": 12, "h": 8},
            "targets": [{
                "expr": "histogram_quantile(0.99, sum(rate(adam_learning_signal_latency_seconds_bucket[5m])) by (le, source_component))",
                "legendFormat": "{{source_component}} p99"
            }],
        },
        {
            "title": "Thompson Sampling Updates",
            "type": "timeseries",
            "gridPos": {"x": 12, "y": 10, "w": 12, "h": 8},
            "targets": [{
                "expr": "sum(rate(adam_thompson_updates_total[5m])) by (outcome)",
                "legendFormat": "{{outcome}}"
            }],
        },
        {
            "title": "Path Selection Distribution",
            "type": "piechart",
            "gridPos": {"x": 0, "y": 18, "w": 8, "h": 8},
            "targets": [{
                "expr": "sum(increase(adam_execution_path_selections_total[1h])) by (selected_path)",
                "legendFormat": "{{selected_path}}"
            }],
        },
        {
            "title": "Exploration Rate",
            "type": "gauge",
            "gridPos": {"x": 8, "y": 18, "w": 8, "h": 8},
            "targets": [{
                "expr": "avg(adam_exploration_rate)",
                "legendFormat": "Exploration"
            }],
            "fieldConfig": {
                "defaults": {
                    "min": 0,
                    "max": 1,
                    "thresholds": {
                        "steps": [
                            {"value": 0, "color": "blue"},
                            {"value": 0.1, "color": "green"},
                            {"value": 0.3, "color": "yellow"},
                            {"value": 0.5, "color": "red"},
                        ]
                    }
                }
            }
        },
    ]
}


# =============================================================================
# INFRASTRUCTURE HEALTH DASHBOARD
# =============================================================================

INFRASTRUCTURE_DASHBOARD = {
    "title": "ADAM Infrastructure Health",
    "uid": "adam-infrastructure",
    "tags": ["adam", "infrastructure", "redis", "kafka", "neo4j"],
    "refresh": "10s",
    "panels": [
        # Redis Section
        {
            "title": "Redis Commands/sec",
            "type": "timeseries",
            "gridPos": {"x": 0, "y": 0, "w": 8, "h": 8},
            "targets": [{
                "expr": "sum(rate(adam_redis_commands_total[5m])) by (command)",
                "legendFormat": "{{command}}"
            }],
        },
        {
            "title": "Redis Latency p99",
            "type": "timeseries",
            "gridPos": {"x": 8, "y": 0, "w": 8, "h": 8},
            "targets": [{
                "expr": "histogram_quantile(0.99, sum(rate(adam_redis_latency_seconds_bucket[5m])) by (le))",
                "legendFormat": "p99"
            }],
        },
        
        # Kafka Section
        {
            "title": "Kafka Throughput",
            "type": "timeseries",
            "gridPos": {"x": 0, "y": 8, "w": 8, "h": 8},
            "targets": [
                {
                    "expr": "sum(rate(adam_kafka_messages_produced_total[5m])) by (topic)",
                    "legendFormat": "Produced: {{topic}}"
                },
                {
                    "expr": "sum(rate(adam_kafka_messages_consumed_total[5m])) by (topic)",
                    "legendFormat": "Consumed: {{topic}}"
                },
            ],
        },
        {
            "title": "Kafka Consumer Lag",
            "type": "timeseries",
            "gridPos": {"x": 8, "y": 8, "w": 8, "h": 8},
            "targets": [{
                "expr": "sum(adam_kafka_consumer_lag) by (consumer_group)",
                "legendFormat": "{{consumer_group}}"
            }],
            "alert": {
                "name": "High Consumer Lag",
                "conditions": [{
                    "evaluator": {"type": "gt", "params": [10000]},
                    "operator": {"type": "and"},
                    "query": {"params": ["A", "5m", "now"]},
                }],
            }
        },
        
        # Neo4j Section
        {
            "title": "Neo4j Query Latency",
            "type": "timeseries",
            "gridPos": {"x": 0, "y": 16, "w": 8, "h": 8},
            "targets": [{
                "expr": "histogram_quantile(0.99, sum(rate(adam_neo4j_query_duration_seconds_bucket[5m])) by (le, query_type))",
                "legendFormat": "{{query_type}} p99"
            }],
        },
    ]
}


# =============================================================================
# ALL DASHBOARDS
# =============================================================================

ALL_DASHBOARDS = [
    EXECUTIVE_DASHBOARD,
    PSYCHOLOGICAL_DASHBOARD,
    LEARNING_LOOP_DASHBOARD,
    INFRASTRUCTURE_DASHBOARD,
]
```

---

## Jaeger Distributed Tracing

```python
# =============================================================================
# ADAM Enhancement #29: Jaeger Tracing Configuration
# Location: adam/infrastructure/jaeger/config.py
# =============================================================================

"""
Jaeger Distributed Tracing Configuration for ADAM Platform.

Provides:
1. End-to-end trace visibility for psychological inference
2. Mechanism activation attribution
3. Learning signal correlation
4. Performance bottleneck identification
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class TracingConfig:
    """Jaeger tracing configuration."""
    
    # Service identification
    service_name: str
    
    # Sampling strategy
    sampling_type: str = "probabilistic"  # probabilistic, ratelimiting, const
    sampling_param: float = 0.1  # 10% of traces
    
    # Jaeger agent
    agent_host: str = "jaeger-agent.observability.svc.cluster.local"
    agent_port: int = 6831
    
    # Tags to propagate
    propagate_baggage: List[str] = field(default_factory=lambda: [
        "adam.request_id",
        "adam.user_id",
        "adam.advertiser_id",
        "adam.decision_id",
    ])
    
    # ADAM-specific span tags
    span_tags: Dict[str, str] = field(default_factory=dict)


# =============================================================================
# SERVICE TRACING CONFIGURATIONS
# =============================================================================

TRACING_CONFIGS = {
    "inference-engine": TracingConfig(
        service_name="adam-inference-engine",
        sampling_param=1.0,  # Trace ALL inference requests
        span_tags={
            "adam.component": "inference",
            "adam.tier": "real-time",
        },
    ),
    
    "gradient-bridge": TracingConfig(
        service_name="adam-gradient-bridge",
        sampling_param=0.1,  # 10% of signals
        span_tags={
            "adam.component": "learning",
            "adam.tier": "streaming",
        },
    ),
    
    "blackboard": TracingConfig(
        service_name="adam-blackboard",
        sampling_param=0.5,  # 50% - important for debugging
        span_tags={
            "adam.component": "state",
            "adam.tier": "real-time",
        },
    ),
    
    "feature-store": TracingConfig(
        service_name="adam-feature-store",
        sampling_param=0.1,
        span_tags={
            "adam.component": "features",
            "adam.tier": "real-time",
        },
    ),
    
    "ad-desk": TracingConfig(
        service_name="adam-ad-desk",
        sampling_param=0.5,
        span_tags={
            "adam.component": "ad-desk",
            "adam.tier": "batch",
        },
    ),
}


# =============================================================================
# ADAM-SPECIFIC SPAN CONVENTIONS
# =============================================================================

ADAM_SPAN_NAMES = {
    # Inference spans
    "serve_decision": "adam.inference.serve_decision",
    "get_profile": "adam.inference.get_profile",
    "select_mechanism": "adam.inference.select_mechanism",
    
    # Learning spans
    "emit_signal": "adam.learning.emit_signal",
    "process_signal": "adam.learning.process_signal",
    "update_prior": "adam.learning.update_prior",
    
    # Blackboard spans
    "read_state": "adam.blackboard.read_state",
    "write_state": "adam.blackboard.write_state",
    "subscribe_updates": "adam.blackboard.subscribe_updates",
    
    # Feature spans
    "get_features": "adam.features.get_features",
    "compute_features": "adam.features.compute_features",
    
    # Neo4j spans
    "neo4j_query": "adam.neo4j.query",
    "neo4j_write": "adam.neo4j.write",
    
    # Redis spans
    "redis_get": "adam.redis.get",
    "redis_set": "adam.redis.set",
    "redis_script": "adam.redis.script",
    
    # Kafka spans
    "kafka_produce": "adam.kafka.produce",
    "kafka_consume": "adam.kafka.consume",
}


# =============================================================================
# TRACE CONTEXT PROPAGATION
# =============================================================================

@dataclass
class ADAMTraceContext:
    """
    ADAM-specific trace context that propagates through requests.
    
    This enables:
    1. Correlation of inference decisions with outcomes
    2. Attribution of mechanism activations to conversions
    3. End-to-end visibility of learning signal flow
    """
    # Standard OpenTelemetry
    trace_id: str
    span_id: str
    
    # ADAM-specific baggage
    request_id: str
    user_id: Optional[str] = None
    advertiser_id: Optional[str] = None
    decision_id: Optional[str] = None
    
    # Mechanism tracking
    mechanisms_activated: List[str] = field(default_factory=list)
    
    # Journey tracking
    journey_state: Optional[str] = None
    
    def to_headers(self) -> Dict[str, str]:
        """Convert to HTTP headers for propagation."""
        headers = {
            "traceparent": f"00-{self.trace_id}-{self.span_id}-01",
            "X-ADAM-Request-ID": self.request_id,
        }
        if self.user_id:
            headers["X-ADAM-User-ID"] = self.user_id
        if self.advertiser_id:
            headers["X-ADAM-Advertiser-ID"] = self.advertiser_id
        if self.decision_id:
            headers["X-ADAM-Decision-ID"] = self.decision_id
        if self.mechanisms_activated:
            headers["X-ADAM-Mechanisms"] = ",".join(self.mechanisms_activated)
        if self.journey_state:
            headers["X-ADAM-Journey-State"] = self.journey_state
        return headers
```

---

## Alerting Rules

```yaml
# =============================================================================
# ADAM Enhancement #29: Prometheus Alerting Rules
# Location: infrastructure/prometheus/alerts.yaml
# =============================================================================

groups:
  # ===========================================================================
  # BUSINESS ALERTS - Executive visibility
  # ===========================================================================
  - name: adam-business
    rules:
      - alert: ConversionRateDropped
        expr: |
          (sum(rate(adam_conversions_total[1h])) / sum(rate(adam_impressions_total[1h]))) 
          < 
          (sum(rate(adam_conversions_total[24h] offset 1h)) / sum(rate(adam_impressions_total[24h] offset 1h))) * 0.8
        for: 30m
        labels:
          severity: critical
          team: business
        annotations:
          summary: "Conversion rate dropped >20% vs 24h baseline"
          description: "Current: {{ $value | humanizePercentage }}"
      
      - alert: ImpressionVolumeDropped
        expr: |
          sum(rate(adam_impressions_total[5m])) < 100
        for: 10m
        labels:
          severity: critical
          team: business
        annotations:
          summary: "Impression volume critically low"
          description: "Only {{ $value | humanize }} impressions/sec"

  # ===========================================================================
  # PSYCHOLOGICAL INTELLIGENCE ALERTS
  # ===========================================================================
  - name: adam-psychological
    rules:
      - alert: MechanismEffectivenessCollapsed
        expr: |
          adam_mechanism_effectiveness < 0.1
        for: 1h
        labels:
          severity: warning
          team: ml
        annotations:
          summary: "Mechanism {{ $labels.mechanism }} effectiveness very low"
          description: "Effectiveness: {{ $value | humanize }}"
      
      - alert: HighVulnerabilityExclusions
        expr: |
          sum(rate(adam_vulnerability_exclusions_total{risk_level="high"}[5m])) > 10
        for: 15m
        labels:
          severity: warning
          team: ml
        annotations:
          summary: "Elevated high-risk vulnerability exclusions"
          description: "{{ $value | humanize }}/sec being excluded"
      
      - alert: TraitInferenceConfidenceLow
        expr: |
          histogram_quantile(0.5, sum(rate(adam_trait_inference_confidence_bucket[5m])) by (le)) < 0.6
        for: 30m
        labels:
          severity: warning
          team: ml
        annotations:
          summary: "Trait inference confidence degraded"
          description: "Median confidence: {{ $value | humanize }}"

  # ===========================================================================
  # LEARNING LOOP ALERTS
  # ===========================================================================
  - name: adam-learning
    rules:
      - alert: LearningSignalBacklog
        expr: |
          sum(adam_kafka_consumer_lag{consumer_group=~"adam-gradient-bridge.*"}) > 50000
        for: 10m
        labels:
          severity: critical
          team: platform
        annotations:
          summary: "Learning signal processing backlog"
          description: "{{ $value | humanize }} messages behind"
      
      - alert: ThompsonSamplingStalled
        expr: |
          sum(rate(adam_thompson_updates_total[5m])) < 1
        for: 15m
        labels:
          severity: warning
          team: ml
        annotations:
          summary: "Thompson Sampling updates stalled"
          description: "No prior updates in 15 minutes"
      
      - alert: ExplorationRateTooHigh
        expr: |
          avg(adam_exploration_rate) > 0.5
        for: 1h
        labels:
          severity: warning
          team: ml
        annotations:
          summary: "Exploration rate unusually high"
          description: "Exploration at {{ $value | humanizePercentage }}"

  # ===========================================================================
  # INFRASTRUCTURE ALERTS
  # ===========================================================================
  - name: adam-infrastructure
    rules:
      # Redis
      - alert: RedisLatencyHigh
        expr: |
          histogram_quantile(0.99, sum(rate(adam_redis_latency_seconds_bucket[5m])) by (le)) > 0.01
        for: 5m
        labels:
          severity: critical
          team: platform
        annotations:
          summary: "Redis p99 latency exceeds 10ms"
          description: "Current p99: {{ $value | humanizeDuration }}"
      
      # Kafka
      - alert: KafkaConsumerLagHigh
        expr: |
          sum(adam_kafka_consumer_lag) by (consumer_group) > 10000
        for: 10m
        labels:
          severity: warning
          team: platform
        annotations:
          summary: "Kafka consumer {{ $labels.consumer_group }} falling behind"
          description: "Lag: {{ $value | humanize }} messages"
      
      # Neo4j
      - alert: Neo4jQueryLatencyHigh
        expr: |
          histogram_quantile(0.99, sum(rate(adam_neo4j_query_duration_seconds_bucket[5m])) by (le)) > 1
        for: 10m
        labels:
          severity: warning
          team: platform
        annotations:
          summary: "Neo4j p99 query latency exceeds 1s"
          description: "Current p99: {{ $value | humanizeDuration }}"

  # ===========================================================================
  # SERVICE HEALTH ALERTS
  # ===========================================================================
  - name: adam-services
    rules:
      - alert: InferenceLatencyHigh
        expr: |
          histogram_quantile(0.99, sum(rate(adam_http_request_duration_seconds_bucket{service="adam-inference-engine"}[5m])) by (le)) > 0.1
        for: 5m
        labels:
          severity: critical
          team: platform
        annotations:
          summary: "Inference p99 latency exceeds 100ms SLO"
          description: "Current p99: {{ $value | humanizeDuration }}"
      
      - alert: ServiceErrorRateHigh
        expr: |
          sum(rate(adam_http_requests_total{status_code=~"5.."}[5m])) by (service)
          / sum(rate(adam_http_requests_total[5m])) by (service) > 0.01
        for: 5m
        labels:
          severity: critical
          team: platform
        annotations:
          summary: "Service {{ $labels.service }} error rate >1%"
          description: "Error rate: {{ $value | humanizePercentage }}"
      
      - alert: FeatureStoreLatencyHigh
        expr: |
          histogram_quantile(0.99, sum(rate(adam_http_request_duration_seconds_bucket{service="adam-feature-store", path="/api/v1/features/*"}[5m])) by (le)) > 0.01
        for: 5m
        labels:
          severity: critical
          team: platform
        annotations:
          summary: "Feature store p99 exceeds 10ms SLO"
          description: "Current p99: {{ $value | humanizeDuration }}"
```

---

# SECTION F: KUBERNETES DEPLOYMENT

## Namespace Strategy

```yaml
# =============================================================================
# ADAM Enhancement #29: Kubernetes Namespace Configuration
# Location: infrastructure/kubernetes/namespaces.yaml
# =============================================================================

---
# Main ADAM namespace
apiVersion: v1
kind: Namespace
metadata:
  name: adam
  labels:
    name: adam
    istio-injection: disabled  # Using Linkerd instead
    linkerd.io/inject: enabled
---
# Observability stack
apiVersion: v1
kind: Namespace
metadata:
  name: adam-observability
  labels:
    name: adam-observability
---
# Data stores (Redis, Kafka)
apiVersion: v1
kind: Namespace
metadata:
  name: adam-data
  labels:
    name: adam-data
---
# CI/CD and tooling
apiVersion: v1
kind: Namespace
metadata:
  name: adam-tools
  labels:
    name: adam-tools
```

## Resource Quotas

```yaml
# =============================================================================
# ADAM Enhancement #29: Resource Quotas
# Location: infrastructure/kubernetes/quotas.yaml
# =============================================================================

---
apiVersion: v1
kind: ResourceQuota
metadata:
  name: adam-compute-quota
  namespace: adam
spec:
  hard:
    requests.cpu: "100"
    requests.memory: "200Gi"
    limits.cpu: "200"
    limits.memory: "400Gi"
    pods: "500"
    persistentvolumeclaims: "50"
---
apiVersion: v1
kind: ResourceQuota
metadata:
  name: adam-data-quota
  namespace: adam-data
spec:
  hard:
    requests.cpu: "50"
    requests.memory: "300Gi"  # Higher for Redis/Kafka
    limits.cpu: "100"
    limits.memory: "500Gi"
    pods: "100"
    persistentvolumeclaims: "100"
```

## Horizontal Pod Autoscaling

```python
# =============================================================================
# ADAM Enhancement #29: HPA Configuration
# Location: adam/infrastructure/kubernetes/hpa.py
# =============================================================================

"""
Horizontal Pod Autoscaler configurations for ADAM services.

Scaling strategies:
1. Inference services: Scale on latency, not just CPU
2. Learning services: Scale on Kafka lag
3. Feature services: Scale on request rate
"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class HPAConfig:
    """HPA configuration for an ADAM service."""
    service_name: str
    namespace: str = "adam"
    
    # Replica bounds
    min_replicas: int = 3
    max_replicas: int = 50
    
    # Scaling metrics
    target_cpu_percent: Optional[int] = None
    target_memory_percent: Optional[int] = None
    
    # Custom metrics
    custom_metrics: List[dict] = field(default_factory=list)
    
    # Behavior
    scale_up_stabilization_seconds: int = 30
    scale_down_stabilization_seconds: int = 300


ADAM_HPA_CONFIGS = [
    # =========================================================================
    # INFERENCE ENGINE - Scale on latency
    # =========================================================================
    HPAConfig(
        service_name="adam-inference-engine",
        min_replicas=5,
        max_replicas=100,
        target_cpu_percent=70,
        custom_metrics=[
            {
                "type": "Pods",
                "pods": {
                    "metric": {
                        "name": "adam_http_request_duration_seconds_p99"
                    },
                    "target": {
                        "type": "AverageValue",
                        "averageValue": "50m"  # 50ms target
                    }
                }
            }
        ],
        scale_up_stabilization_seconds=15,  # Fast scale up
    ),
    
    # =========================================================================
    # FEATURE STORE - Scale on request rate
    # =========================================================================
    HPAConfig(
        service_name="adam-feature-store",
        min_replicas=3,
        max_replicas=50,
        target_cpu_percent=60,
        custom_metrics=[
            {
                "type": "Pods",
                "pods": {
                    "metric": {
                        "name": "adam_http_requests_per_second"
                    },
                    "target": {
                        "type": "AverageValue",
                        "averageValue": "1000"
                    }
                }
            }
        ],
    ),
    
    # =========================================================================
    # GRADIENT BRIDGE - Scale on Kafka lag
    # =========================================================================
    HPAConfig(
        service_name="adam-gradient-bridge",
        min_replicas=3,
        max_replicas=20,
        custom_metrics=[
            {
                "type": "External",
                "external": {
                    "metric": {
                        "name": "kafka_consumergroup_lag",
                        "selector": {
                            "matchLabels": {
                                "consumergroup": "adam-gradient-bridge"
                            }
                        }
                    },
                    "target": {
                        "type": "Value",
                        "value": "1000"  # Scale up if lag > 1000
                    }
                }
            }
        ],
    ),
    
    # =========================================================================
    # BLACKBOARD - Scale on memory
    # =========================================================================
    HPAConfig(
        service_name="adam-blackboard",
        min_replicas=3,
        max_replicas=20,
        target_cpu_percent=70,
        target_memory_percent=80,
    ),
    
    # =========================================================================
    # AD DESK - Scale on CPU (batch processing)
    # =========================================================================
    HPAConfig(
        service_name="adam-ad-desk",
        min_replicas=2,
        max_replicas=20,
        target_cpu_percent=70,
        scale_down_stabilization_seconds=600,  # Slow scale down
    ),
]


def generate_hpa_yaml(config: HPAConfig) -> str:
    """Generate HPA YAML from config."""
    
    metrics = []
    
    if config.target_cpu_percent:
        metrics.append({
            "type": "Resource",
            "resource": {
                "name": "cpu",
                "target": {
                    "type": "Utilization",
                    "averageUtilization": config.target_cpu_percent
                }
            }
        })
    
    if config.target_memory_percent:
        metrics.append({
            "type": "Resource",
            "resource": {
                "name": "memory",
                "target": {
                    "type": "Utilization",
                    "averageUtilization": config.target_memory_percent
                }
            }
        })
    
    metrics.extend(config.custom_metrics)
    
    import yaml
    hpa = {
        "apiVersion": "autoscaling/v2",
        "kind": "HorizontalPodAutoscaler",
        "metadata": {
            "name": f"{config.service_name}-hpa",
            "namespace": config.namespace,
        },
        "spec": {
            "scaleTargetRef": {
                "apiVersion": "apps/v1",
                "kind": "Deployment",
                "name": config.service_name,
            },
            "minReplicas": config.min_replicas,
            "maxReplicas": config.max_replicas,
            "metrics": metrics,
            "behavior": {
                "scaleUp": {
                    "stabilizationWindowSeconds": config.scale_up_stabilization_seconds,
                    "policies": [
                        {"type": "Percent", "value": 100, "periodSeconds": 15},
                        {"type": "Pods", "value": 4, "periodSeconds": 15},
                    ],
                    "selectPolicy": "Max",
                },
                "scaleDown": {
                    "stabilizationWindowSeconds": config.scale_down_stabilization_seconds,
                    "policies": [
                        {"type": "Percent", "value": 10, "periodSeconds": 60},
                    ],
                },
            },
        },
    }
    
    return yaml.dump(hpa, default_flow_style=False)
```

---

# SECTION G: LOCAL DEVELOPMENT

## Docker Compose Environment

```yaml
# =============================================================================
# ADAM Enhancement #29: Docker Compose for Local Development
# Location: infrastructure/docker/docker-compose.yaml
# =============================================================================
#
# Provides complete local development environment matching production topology.
# 
# Usage:
#   docker-compose up -d          # Start all services
#   docker-compose logs -f adam   # Follow logs
#   docker-compose down -v        # Stop and clean up
#
# Services accessible at:
#   - Redis: localhost:6379
#   - Kafka: localhost:9092
#   - Neo4j: localhost:7474 (browser), 7687 (bolt)
#   - Prometheus: localhost:9090
#   - Grafana: localhost:3000
#   - Jaeger: localhost:16686
#

version: '3.8'

services:
  # ===========================================================================
  # REDIS CLUSTER (Simplified for local dev - single node)
  # ===========================================================================
  redis:
    image: redis:7.2-alpine
    container_name: adam-redis
    ports:
      - "6379:6379"
    command: redis-server --appendonly yes --maxmemory 2gb --maxmemory-policy volatile-lru
    volumes:
      - redis-data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  # ===========================================================================
  # KAFKA + ZOOKEEPER
  # ===========================================================================
  zookeeper:
    image: confluentinc/cp-zookeeper:7.5.0
    container_name: adam-zookeeper
    environment:
      ZOOKEEPER_CLIENT_PORT: 2181
      ZOOKEEPER_TICK_TIME: 2000
    volumes:
      - zookeeper-data:/var/lib/zookeeper/data
      - zookeeper-logs:/var/lib/zookeeper/log
    healthcheck:
      test: ["CMD", "nc", "-z", "localhost", "2181"]
      interval: 10s
      timeout: 5s
      retries: 5

  kafka:
    image: confluentinc/cp-kafka:7.5.0
    container_name: adam-kafka
    depends_on:
      zookeeper:
        condition: service_healthy
    ports:
      - "9092:9092"
      - "29092:29092"
    environment:
      KAFKA_BROKER_ID: 1
      KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://kafka:29092,PLAINTEXT_HOST://localhost:9092
      KAFKA_LISTENER_SECURITY_PROTOCOL_MAP: PLAINTEXT:PLAINTEXT,PLAINTEXT_HOST:PLAINTEXT
      KAFKA_INTER_BROKER_LISTENER_NAME: PLAINTEXT
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1
      KAFKA_TRANSACTION_STATE_LOG_MIN_ISR: 1
      KAFKA_TRANSACTION_STATE_LOG_REPLICATION_FACTOR: 1
      KAFKA_AUTO_CREATE_TOPICS_ENABLE: "true"
    volumes:
      - kafka-data:/var/lib/kafka/data
    healthcheck:
      test: ["CMD", "kafka-broker-api-versions", "--bootstrap-server", "localhost:9092"]
      interval: 10s
      timeout: 10s
      retries: 10

  # Schema Registry
  schema-registry:
    image: confluentinc/cp-schema-registry:7.5.0
    container_name: adam-schema-registry
    depends_on:
      kafka:
        condition: service_healthy
    ports:
      - "8081:8081"
    environment:
      SCHEMA_REGISTRY_HOST_NAME: schema-registry
      SCHEMA_REGISTRY_KAFKASTORE_BOOTSTRAP_SERVERS: kafka:29092
      SCHEMA_REGISTRY_LISTENERS: http://0.0.0.0:8081
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8081/subjects"]
      interval: 10s
      timeout: 5s
      retries: 5

  # ===========================================================================
  # NEO4J
  # ===========================================================================
  neo4j:
    image: neo4j:5.15.0-enterprise
    container_name: adam-neo4j
    ports:
      - "7474:7474"  # HTTP
      - "7687:7687"  # Bolt
    environment:
      NEO4J_AUTH: neo4j/adampassword
      NEO4J_ACCEPT_LICENSE_AGREEMENT: "yes"
      NEO4J_PLUGINS: '["apoc", "graph-data-science"]'
      NEO4J_dbms_memory_heap_initial__size: 1G
      NEO4J_dbms_memory_heap_max__size: 2G
      NEO4J_dbms_memory_pagecache_size: 1G
    volumes:
      - neo4j-data:/data
      - neo4j-logs:/logs
    healthcheck:
      test: ["CMD", "wget", "-q", "--spider", "http://localhost:7474"]
      interval: 10s
      timeout: 5s
      retries: 10

  # ===========================================================================
  # PROMETHEUS
  # ===========================================================================
  prometheus:
    image: prom/prometheus:v2.47.0
    container_name: adam-prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus/prometheus.yml:/etc/prometheus/prometheus.yml
      - ./prometheus/alerts.yaml:/etc/prometheus/alerts.yaml
      - prometheus-data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.enable-lifecycle'
    healthcheck:
      test: ["CMD", "wget", "-q", "--spider", "http://localhost:9090/-/healthy"]
      interval: 10s
      timeout: 5s
      retries: 5

  # ===========================================================================
  # GRAFANA
  # ===========================================================================
  grafana:
    image: grafana/grafana:10.2.0
    container_name: adam-grafana
    ports:
      - "3000:3000"
    environment:
      GF_SECURITY_ADMIN_USER: admin
      GF_SECURITY_ADMIN_PASSWORD: adamadmin
      GF_USERS_ALLOW_SIGN_UP: "false"
    volumes:
      - ./grafana/provisioning:/etc/grafana/provisioning
      - ./grafana/dashboards:/var/lib/grafana/dashboards
      - grafana-data:/var/lib/grafana
    depends_on:
      - prometheus
    healthcheck:
      test: ["CMD", "wget", "-q", "--spider", "http://localhost:3000/api/health"]
      interval: 10s
      timeout: 5s
      retries: 5

  # ===========================================================================
  # JAEGER
  # ===========================================================================
  jaeger:
    image: jaegertracing/all-in-one:1.51
    container_name: adam-jaeger
    ports:
      - "16686:16686"  # UI
      - "6831:6831/udp"  # Thrift compact (agent)
      - "14268:14268"  # HTTP collector
    environment:
      COLLECTOR_OTLP_ENABLED: "true"
    healthcheck:
      test: ["CMD", "wget", "-q", "--spider", "http://localhost:16686"]
      interval: 10s
      timeout: 5s
      retries: 5

  # ===========================================================================
  # KAFKA UI (Development convenience)
  # ===========================================================================
  kafka-ui:
    image: provectuslabs/kafka-ui:latest
    container_name: adam-kafka-ui
    ports:
      - "8080:8080"
    environment:
      KAFKA_CLUSTERS_0_NAME: adam-local
      KAFKA_CLUSTERS_0_BOOTSTRAPSERVERS: kafka:29092
      KAFKA_CLUSTERS_0_SCHEMAREGISTRY: http://schema-registry:8081
    depends_on:
      - kafka
      - schema-registry

  # ===========================================================================
  # REDIS COMMANDER (Development convenience)
  # ===========================================================================
  redis-commander:
    image: rediscommander/redis-commander:latest
    container_name: adam-redis-commander
    ports:
      - "8082:8081"
    environment:
      REDIS_HOSTS: local:redis:6379
    depends_on:
      - redis

volumes:
  redis-data:
  zookeeper-data:
  zookeeper-logs:
  kafka-data:
  neo4j-data:
  neo4j-logs:
  prometheus-data:
  grafana-data:

networks:
  default:
    name: adam-network
```

---

# SECTION H: IMPLEMENTATION & OPERATIONS

## Implementation Timeline

### Phase 1: Foundation (Weeks 1-2)

| Week | Focus | Deliverables |
|------|-------|--------------|
| 1 | Redis | Cluster config, key conventions, Lua scripts, connection pool |
| 1 | Local Dev | Docker Compose environment, README |
| 2 | Kafka | Topic definitions, Avro schemas, producer/consumer configs |
| 2 | Schema Registry | Schema registration, compatibility rules |

### Phase 2: Service Infrastructure (Weeks 3-4)

| Week | Focus | Deliverables |
|------|-------|--------------|
| 3 | Linkerd | ServiceProfiles for all services, traffic policies |
| 3 | Kong | Routes, rate limiting, authentication plugins |
| 4 | Kubernetes | Namespaces, quotas, HPA configs, network policies |
| 4 | Helm Charts | Base chart, service templates, values files |

### Phase 3: Observability (Weeks 5-6)

| Week | Focus | Deliverables |
|------|-------|--------------|
| 5 | Prometheus | Metric definitions, scrape configs, recording rules |
| 5 | Alerting | Alert rules for all categories |
| 6 | Grafana | All dashboards, provisioning configs |
| 6 | Jaeger | Tracing configs, context propagation library |

### Phase 4: Integration & Testing (Weeks 7-8)

| Week | Focus | Deliverables |
|------|-------|--------------|
| 7 | Integration | Connect all components, end-to-end smoke tests |
| 7 | Load Testing | Performance baselines for Redis, Kafka, Neo4j |
| 8 | Documentation | Operations runbooks, troubleshooting guides |
| 8 | CI/CD | GitHub Actions, deployment pipelines |

---

## Success Metrics

### Infrastructure SLIs

| Component | Metric | Target | Measurement |
|-----------|--------|--------|-------------|
| **Redis** | p99 latency | <5ms | Prometheus histogram |
| **Redis** | Availability | 99.99% | Uptime monitoring |
| **Kafka** | Consumer lag | <1000 messages | Kafka metrics |
| **Kafka** | Produce latency | <10ms | Producer metrics |
| **Kong** | Request latency | <10ms overhead | Gateway metrics |
| **Linkerd** | mTLS coverage | 100% | Mesh dashboard |

### Operational Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Mean Time to Detection (MTTD) | <5 minutes | Alert firing time |
| Mean Time to Recovery (MTTR) | <30 minutes | Incident duration |
| Change failure rate | <5% | Deployment success |
| Deployment frequency | Daily | CI/CD metrics |

### Business Impact

| Metric | Baseline | Target | Impact |
|--------|----------|--------|--------|
| Inference latency p99 | N/A | <100ms | Real-time ad serving |
| Learning signal delay | Hours | <10 seconds | Faster optimization |
| System availability | N/A | 99.95% | Reliable platform |
| Development velocity | N/A | 2x | Faster feature delivery |

---

## Testing Strategy

### Unit Tests

```python
# =============================================================================
# ADAM Enhancement #29: Infrastructure Test Suite
# Location: tests/infrastructure/
# =============================================================================

"""
Test suite for ADAM infrastructure components.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock


class TestRedisKeyBuilder:
    """Tests for ADAM Redis key conventions."""
    
    def test_profile_key_format(self):
        from adam.infrastructure.redis.keys import ADAMKeyBuilder
        
        key = ADAMKeyBuilder.profile_key("user_123")
        assert key == "adam:profile:user:user_123"
    
    def test_blackboard_key_with_subkey(self):
        from adam.infrastructure.redis.keys import ADAMKeyBuilder
        
        key = ADAMKeyBuilder.blackboard_key("req_abc", "trait_profile")
        assert key == "adam:blackboard:request:req_abc:trait_profile"
    
    def test_mechanism_prior_key(self):
        from adam.infrastructure.redis.keys import ADAMKeyBuilder
        
        key = ADAMKeyBuilder.mechanism_prior_key("social_proof", "user_456")
        assert key == "adam:prior:mechanism:social_proof:user:user_456"


class TestKafkaTopics:
    """Tests for Kafka topic configuration."""
    
    def test_learning_signal_topic_exists(self):
        from adam.infrastructure.kafka.topics import get_topic_by_name
        
        topic = get_topic_by_name("adam.signals.learning")
        assert topic is not None
        assert topic.partitions == 24
        assert topic.replication_factor == 3
    
    def test_outcome_topics_have_long_retention(self):
        from adam.infrastructure.kafka.topics import OUTCOME_TOPICS
        
        for topic in OUTCOME_TOPICS:
            assert topic.retention_ms >= 2592000000  # 30 days


class TestServiceProfiles:
    """Tests for Linkerd service profile configuration."""
    
    def test_inference_engine_has_strict_timeout(self):
        from adam.infrastructure.linkerd.config import ADAM_SERVICE_PROFILES
        
        inference = next(
            p for p in ADAM_SERVICE_PROFILES 
            if p.service_name == "adam-inference-engine"
        )
        assert inference.timeout == "100ms"
    
    def test_inference_paths_marked(self):
        from adam.infrastructure.linkerd.config import ADAM_SERVICE_PROFILES
        
        for profile in ADAM_SERVICE_PROFILES:
            for route in profile.routes:
                if route.is_inference_path:
                    # Inference paths should have short timeouts
                    timeout_ms = int(route.timeout.replace("ms", ""))
                    assert timeout_ms <= 100
```

### Integration Tests

```python
# =============================================================================
# Integration tests for infrastructure components
# =============================================================================

@pytest.mark.integration
class TestRedisIntegration:
    """Integration tests for Redis cluster."""
    
    @pytest.fixture
    async def redis_pool(self):
        from adam.infrastructure.redis.pool import ADAMRedisPool
        from adam.infrastructure.redis.config import RedisClusterConfig
        from adam.infrastructure.redis.lua_scripts import ADAM_LUA_SCRIPTS
        
        pool = ADAMRedisPool(
            cluster_config=RedisClusterConfig(),
            lua_scripts=ADAM_LUA_SCRIPTS,
        )
        await pool.initialize()
        yield pool
        await pool.close()
    
    async def test_thompson_update_script(self, redis_pool):
        """Test Thompson Sampling prior update."""
        result = await redis_pool.execute_script(
            "thompson_update",
            ["adam:test:prior:test1"],
            [1, 1.0, 3600],
        )
        
        import json
        data = json.loads(result)
        assert data["alpha"] == 2.0  # Started at 1, +1 for success
        assert data["beta"] == 1.0
        assert data["samples"] == 1


@pytest.mark.integration
class TestKafkaIntegration:
    """Integration tests for Kafka cluster."""
    
    async def test_learning_signal_roundtrip(self):
        """Test producing and consuming learning signal."""
        # Implementation would test full Kafka flow
        pass
```

---

## Revision History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | January 2026 | Initial enterprise-grade specification |

---

**END OF ENHANCEMENT #29: PLATFORM INFRASTRUCTURE FOUNDATION**
