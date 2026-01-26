# ADAM Enhancement #02: Shared State Blackboard Architecture
## Enterprise-Grade Working Memory for Real-Time Psychological Intelligence

**Version**: 2.0 COMPLETE  
**Date**: January 2026  
**Priority**: P0 - Foundational Infrastructure  
**Estimated Implementation**: 10 person-weeks  
**Dependencies**: #01 (Bidirectional Graph-Reasoning Fusion), #31 (Caching & Real-Time Inference)  
**Dependents**: ALL reasoning components (#03-#06, #10, #15, #04 Atom of Thought)  
**File Size**: ~200KB (Enterprise Production-Ready)

---

## Table of Contents

### SECTION A: STRATEGIC OVERVIEW
1. [Executive Summary](#executive-summary)
2. [The Problem: Isolated Component State](#the-problem-isolated-component-state)
3. [The Solution: Blackboard Architecture](#the-solution-blackboard-architecture)
4. [Integration Architecture](#integration-architecture)

### SECTION B: PYDANTIC MODELS - CORE STATE
5. [Blackboard Core Models](#blackboard-core-models)
6. [Request Context Models](#request-context-models)
7. [User Intelligence Package](#user-intelligence-package)
8. [State × Trait Framework](#state-trait-framework)

### SECTION C: PYDANTIC MODELS - REASONING SPACES
9. [Atom Reasoning Space Models](#atom-reasoning-space-models)
10. [Mechanism-Specific Spaces](#mechanism-specific-spaces)
11. [Synthesis Workspace Models](#synthesis-workspace-models)
12. [Decision State Models](#decision-state-models)

### SECTION D: PYDANTIC MODELS - INTELLIGENCE SOURCES
13. [Ten Intelligence Source Models](#ten-intelligence-source-models)
14. [Source Contribution Tracking](#source-contribution-tracking)
15. [Cross-Source Correlation Models](#cross-source-correlation-models)

### SECTION E: PYDANTIC MODELS - LEARNING & SIGNALS
16. [Learning Signal Models](#learning-signal-models)
17. [Attribution Context Models](#attribution-context-models)
18. [Outcome Recording Models](#outcome-recording-models)

### SECTION F: REDIS IMPLEMENTATION
19. [Multi-Zone Redis Architecture](#multi-zone-redis-architecture)
20. [Connection Pool Management](#connection-pool-management)
21. [Serialization Strategy](#serialization-strategy)
22. [TTL & Eviction Policies](#ttl-eviction-policies)
23. [Pub/Sub Event Layer](#pubsub-event-layer)

### SECTION G: BLACKBOARD SERVICE
24. [BlackboardService Core](#blackboardservice-core)
25. [Zone Manager Implementation](#zone-manager-implementation)
26. [State Transition Engine](#state-transition-engine)
27. [Conflict Resolution](#conflict-resolution)
28. [Concurrent Access Control](#concurrent-access-control)

### SECTION H: EVENT BUS INTEGRATION
29. [Blackboard Event Definitions](#blackboard-event-definitions)
30. [State Change Events](#state-change-events)
31. [Component Coordination Events](#component-coordination-events)
32. [Learning Signal Routing](#learning-signal-routing)

### SECTION I: LANGGRAPH INTEGRATION
33. [Blackboard-Aware Node Pattern](#blackboard-aware-node-pattern)
34. [State Injection Strategy](#state-injection-strategy)
35. [Cross-Node Communication](#cross-node-communication)
36. [Workflow State Binding](#workflow-state-binding)

### SECTION J: NEO4J SCHEMA
37. [State Persistence Nodes](#state-persistence-nodes)
38. [Session History Graph](#session-history-graph)
39. [Reasoning Trace Persistence](#reasoning-trace-persistence)
40. [Temporal Query Patterns](#temporal-query-patterns)

### SECTION K: FASTAPI ENDPOINTS
41. [State Query API](#state-query-api)
42. [Admin & Debug API](#admin-debug-api)
43. [Health & Metrics API](#health-metrics-api)

### SECTION L: PROMETHEUS METRICS
44. [State Access Metrics](#state-access-metrics)
45. [Zone Health Metrics](#zone-health-metrics)
46. [Latency Distribution Metrics](#latency-distribution-metrics)

### SECTION M: TESTING & OPERATIONS
47. [Unit Test Suite](#unit-test-suite)
48. [Integration Tests](#integration-tests)
49. [Load & Stress Testing](#load-stress-testing)
50. [Implementation Timeline](#implementation-timeline)
51. [Success Metrics](#success-metrics)

---

# SECTION A: STRATEGIC OVERVIEW

## Executive Summary

### The Core Problem

ADAM's components currently operate with **isolated state**. Each LangGraph node processes its input and produces output without real-time awareness of:
- What other atoms have discovered
- What psychological patterns are emerging across sources
- What the current session's intelligence trajectory looks like
- How to coordinate reasoning without redundant computation

This isolation creates three critical failures:

1. **Redundant Reasoning**: Multiple atoms detect the same psychological signal independently
2. **Inconsistent Context**: Later components receive stale information from earlier ones
3. **Lost Coordination**: No mechanism for atoms to "talk to each other" during execution

### The Solution: Blackboard Architecture

The Blackboard pattern (classic AI architecture from HEARSAY-II speech recognition) provides:

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                         BLACKBOARD ARCHITECTURE PRINCIPLE                               │
│                                                                                         │
│   "Multiple specialized knowledge sources collaboratively build a solution             │
│    by reading from and writing to a shared working memory (the blackboard)."           │
│                                                                                         │
│   ┌─────────────────────────────────────────────────────────────────────────────────┐   │
│   │                          SHARED BLACKBOARD (Redis)                              │   │
│   │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌───────────┐ │   │
│   │  │   Request   │ │    Atom     │ │  Synthesis  │ │  Decision   │ │  Learning │ │   │
│   │  │   Context   │ │  Reasoning  │ │  Workspace  │ │    State    │ │  Signals  │ │   │
│   │  │   (Zone 1)  │ │   Spaces    │ │   (Zone 3)  │ │   (Zone 4)  │ │  (Zone 5) │ │   │
│   │  │             │ │   (Zone 2)  │ │             │ │             │ │           │ │   │
│   │  └──────┬──────┘ └──────┬──────┘ └──────┬──────┘ └──────┬──────┘ └─────┬─────┘ │   │
│   │         │               │               │               │               │       │   │
│   │         └───────────────┴───────────────┴───────────────┴───────────────┘       │   │
│   │                                         │                                        │   │
│   │                              Event Bus (Pub/Sub)                                 │   │
│   │                                         │                                        │   │
│   └─────────────────────────────────────────┼────────────────────────────────────────┘   │
│                                             │                                            │
│     ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐          │
│     │   Atom    │  │   Atom    │  │   Atom    │  │ Synthesis │  │ Decision  │          │
│     │ (Reg Foc) │  │ (Constr)  │  │ (Pers)    │  │   Node    │  │   Node    │          │
│     └─────┬─────┘  └─────┬─────┘  └─────┬─────┘  └─────┬─────┘  └─────┬─────┘          │
│           │              │              │              │              │                 │
│           │   Subscribe: atom.complete  │              │              │                 │
│           │   Write: Zone 2 (own space) │              │              │                 │
│           │   Read: Zone 1, Zone 2*     │   Subscribe: atom.complete  │                 │
│           │              │              │   Write: Zone 3             │                 │
│           │              │              │   Read: Zone 1, 2, 3        │                 │
│           └──────────────┴──────────────┴──────────────┴──────────────┘                 │
│                                                                                         │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

### Why This Matters for ADAM

ADAM's psychological intelligence requires **coordinated reasoning across multiple specialized components**:

| Component Type | What It Needs | What Blackboard Provides |
|----------------|---------------|--------------------------|
| **Regulatory Focus Atom** | Other atoms' arousal detection | Real-time read from Zone 2 |
| **Construal Level Atom** | User's cognitive load state | Shared state injection |
| **Persuasion Mechanism Atom** | Trait-state interaction | State × Trait snapshot |
| **Synthesis Node** | All atom traces, confidence evolution | Complete Zone 2 visibility |
| **Decision Node** | Historical patterns, current context | Combined Zone 1-4 access |
| **Meta-Learner** | Component performance signals | Zone 5 learning aggregation |
| **Gradient Bridge** | Cross-component attribution | Event-based signal flow |

### Expected Impact

| Metric | Without Blackboard | With Blackboard | Improvement |
|--------|-------------------|-----------------|-------------|
| **Token Efficiency** | Redundant context passing | Shared state access | 30-40% fewer tokens |
| **Reasoning Coherence** | Atoms produce conflicting signals | Pre-coordinated reasoning | 15-25% fewer conflicts |
| **Latency** | Sequential state fetching | Parallel zone access | 20-30% faster |
| **Learning Signal Completeness** | Fragmented attribution | Unified signal aggregation | 40% more attribution coverage |
| **Cross-Component Awareness** | None during execution | Real-time pub/sub | Full visibility |

---

## The Problem: Isolated Component State

### Current Architecture Limitations

```
CURRENT ADAM INFORMATION FLOW (ISOLATED):

Request → [LangGraph State Dict] → [Node 1] → [Node 2] → [Node 3] → Response
                ↓                    ↓           ↓           ↓
          (passed explicit)     (isolated)  (isolated)  (isolated)

Problems:
• Node 2 doesn't know what Node 1 discovered until explicit state pass
• Node 1 can't adjust based on Node 2's preliminary findings
• Synthesis receives only final outputs, not reasoning evolution
• Learning signals are scattered across components
• No "shared understanding" during request processing
```

### Concrete Example: Arousal Detection

**Without Blackboard:**
```python
# Atom 1: Regulatory Focus detects high arousal from behavior patterns
regulatory_atom_output = {
    "focus": "prevention",  # User is risk-averse
    "arousal_detected": True,  # But this stays in this atom's output
    "confidence": 0.82
}

# Atom 2: Construal Level runs with NO knowledge of high arousal
construal_atom_output = {
    "level": "abstract",  # Recommends abstract messaging
    "confidence": 0.75
    # But abstract messaging may be WRONG for high-arousal users!
}

# Synthesis: Receives conflicting signals
# Has to spend tokens figuring out the conflict
# Prevention + Abstract is psychologically inconsistent
```

**With Blackboard:**
```python
# Atom 1: Writes arousal detection to shared state immediately
await blackboard.write_zone2(
    request_id=request_id,
    atom_id="regulatory_focus",
    preliminary_signal={
        "type": "arousal_detection",
        "value": "high",
        "confidence": 0.85,
        "behavioral_evidence": ["rapid_clicks", "short_dwell"]
    }
)

# Atom 2: Reads shared state BEFORE reasoning
arousal_signal = await blackboard.read_preliminary_signals(
    request_id=request_id,
    signal_type="arousal_detection"
)

if arousal_signal and arousal_signal.value == "high":
    # Adjust construal reasoning for high-arousal context
    construal_strategy = "concrete"  # Match arousal with concrete messaging
    
# Synthesis: Receives PRE-COORDINATED signals
# No conflict resolution needed - atoms already aligned
```

### Information Gaps by Component

| Component | Critical Information Need | Current Source | Gap |
|-----------|---------------------------|----------------|-----|
| **Regulatory Focus Atom** | User's emotional baseline | Graph query (stale) | No real-time arousal state |
| **Construal Level Atom** | Cognitive load indicators | None | No cross-atom coordination |
| **Temporal Processing Atom** | Session trajectory | Session log (async) | No real-time journey state |
| **Mechanism Selection** | Which mechanisms already detected | None | Redundant detection |
| **Synthesis** | Reasoning traces, not just outputs | Final outputs only | Lost intermediate reasoning |
| **Decision** | Confidence evolution over time | Final confidence only | No calibration data |
| **Meta-Learner** | Component-level performance | Batch metrics | No real-time signals |
| **Gradient Bridge** | Attribution-ready context | Fragmented | Incomplete attribution |

---

## The Solution: Blackboard Architecture

### Five-Zone Architecture

The Blackboard is divided into **five logical zones**, each with specific access patterns, TTLs, and purposes:

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                              BLACKBOARD ZONE ARCHITECTURE                               │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                         │
│  ZONE 1: REQUEST CONTEXT                                                                │
│  ━━━━━━━━━━━━━━━━━━━━━━                                                                 │
│  • Access: Read-only for all components                                                 │
│  • Writers: Request ingestion only (once)                                               │
│  • TTL: Request duration + 5 minutes                                                    │
│  • Contents: User profile, content context, ad candidates, graph-derived priors         │
│                                                                                         │
│  ZONE 2: ATOM REASONING SPACES                                                          │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━                                                            │
│  • Access: Write by owning atom, read by synthesis + optionally other atoms             │
│  • Writers: Each atom writes to its own namespace                                       │
│  • TTL: Request duration + 30 minutes (for learning)                                    │
│  • Contents: Preliminary signals, confidence evolution, reasoning traces, final output  │
│  • Subzones: 9 mechanism-specific spaces + 10 intelligence source spaces                │
│                                                                                         │
│  ZONE 3: SYNTHESIS WORKSPACE                                                            │
│  ━━━━━━━━━━━━━━━━━━━━━━━━                                                               │
│  • Access: Write by synthesis, read by decision + learners                              │
│  • Writers: Synthesis node only                                                         │
│  • TTL: Request duration + 1 hour (for attribution)                                     │
│  • Contents: Atom aggregation, conflict resolution log, mechanism weights, final rec    │
│                                                                                         │
│  ZONE 4: DECISION STATE                                                                 │
│  ━━━━━━━━━━━━━━━━━━━━━━                                                                 │
│  • Access: Write by decision, read by all                                               │
│  • Writers: Decision node only                                                          │
│  • TTL: Session duration + 24 hours (for outcome attribution)                           │
│  • Contents: Final decision, serving details, latency budget used, fallback tier        │
│                                                                                         │
│  ZONE 5: LEARNING SIGNALS                                                               │
│  ━━━━━━━━━━━━━━━━━━━━━━━                                                                │
│  • Access: Write by all components, read by Gradient Bridge + Meta-Learner              │
│  • Writers: Any component can emit signals                                              │
│  • TTL: 72 hours (for delayed attribution)                                              │
│  • Contents: Component outputs, performance metrics, outcome attributions               │
│                                                                                         │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

### Zone Access Matrix

| Zone | Request Handler | Atoms | Synthesis | Decision | Meta-Learner | Gradient Bridge |
|------|-----------------|-------|-----------|----------|--------------|-----------------|
| **Zone 1** | Write (once) | Read | Read | Read | Read | Read |
| **Zone 2** | - | Read/Write (own) | Read (all) | - | Read | Read |
| **Zone 3** | - | - | Read/Write | Read | Read | Read |
| **Zone 4** | - | - | - | Read/Write | Read | Read |
| **Zone 5** | Write | Write | Write | Write | Read/Write | Read/Write |

### Key Design Principles

1. **Immutable Request Context**: Zone 1 is set once and never modified during request processing
2. **Namespaced Writing**: Each atom writes only to its own Zone 2 namespace
3. **Progressive Enrichment**: Each zone builds on the previous (1 → 2 → 3 → 4 → 5)
4. **Event-Driven Coordination**: State changes trigger pub/sub events for reactive components
5. **TTL-Based Lifecycle**: Each zone has appropriate TTL for its purpose
6. **Serialization Consistency**: All state uses Pydantic models with JSON serialization

---

## Integration Architecture

### Integration with Enhancement #01 (Graph-Reasoning Fusion)

Enhancement #01 provides the **Interaction Bridge** between Claude's reasoning and Neo4j. The Blackboard complements this:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    BLACKBOARD + GRAPH FUSION INTEGRATION                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   NEO4J GRAPH                    BLACKBOARD                 CLAUDE REASONING│
│   ━━━━━━━━━━━                    ━━━━━━━━━━                 ━━━━━━━━━━━━━━━ │
│                                                                             │
│   ┌──────────────┐         ┌──────────────────┐        ┌──────────────────┐ │
│   │ UserProfile  │────────▶│  Zone 1: Request │───────▶│   Atom Nodes     │ │
│   │ Mechanisms   │  Hydrate│      Context     │ Inject │  (Psychological  │ │
│   │ State History│         └──────────────────┘        │   Reasoning)     │ │
│   └──────────────┘                                     └────────┬─────────┘ │
│         ▲                                                       │           │
│         │                  ┌──────────────────┐                 │           │
│         │                  │  Zone 2: Atom    │◀────────────────┘           │
│         │                  │  Reasoning Spaces│  Write Traces               │
│         │                  └────────┬─────────┘                             │
│         │                           │                                       │
│         │                  ┌────────▼─────────┐                             │
│         │                  │  Zone 3: Synth   │◀─── Synthesis Node          │
│         │                  │    Workspace     │                             │
│         │                  └────────┬─────────┘                             │
│         │                           │                                       │
│         │                  ┌────────▼─────────┐                             │
│         │                  │  Zone 4: Decision│◀─── Decision Node           │
│         │                  │      State       │                             │
│         │                  └────────┬─────────┘                             │
│         │                           │                                       │
│         │                  ┌────────▼─────────┐                             │
│         │ Persist          │  Zone 5: Learning│──▶ Gradient Bridge (#06)    │
│         │ via #01          │     Signals      │                             │
│         │ Interaction      └──────────────────┘                             │
│         │ Bridge                    │                                       │
│         └───────────────────────────┘                                       │
│                                                                             │
│   Key Integration Points:                                                   │
│   • Graph → Zone 1: User profile hydration at request start                 │
│   • Zone 2 → Graph: Reasoning traces persisted via #01 Interaction Bridge   │
│   • Zone 5 → Graph: Learning signals update user state in graph             │
│   • Zone 4 → Graph: Decision outcomes for attribution                       │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Integration with Enhancement #31 (Caching & Real-Time Inference)

Enhancement #31 provides the Event Bus and Cache coordination. The Blackboard uses these:

```python
# Blackboard uses #31's Event Bus for cross-component coordination
from adam.infrastructure.event_bus import EventBusProducer, EventBusConsumer
from adam.infrastructure.cache import CacheCoordinator

# Zone changes emit events via #31's typed event system
class BlackboardEventEmitter:
    def __init__(self, event_bus: EventBusProducer):
        self.event_bus = event_bus
    
    async def emit_atom_complete(self, request_id: str, atom_id: str):
        await self.event_bus.publish(
            topic="blackboard.atom.complete",
            event=AtomCompleteEvent(
                request_id=request_id,
                atom_id=atom_id,
                timestamp=datetime.utcnow()
            )
        )

# Blackboard cache layer uses #31's multi-level cache
class BlackboardCache:
    def __init__(self, cache_coordinator: CacheCoordinator):
        self.cache = cache_coordinator
        # Zone 1-4 in L1 (hot), Zone 5 in L2 (warm)
```

### Integration with Enhancement #04 (Atom of Thought)

Enhancement #04 defines the 10 intelligence sources that the Blackboard must support:

```python
# Blackboard Zone 2 provides dedicated spaces for each intelligence source
INTELLIGENCE_SOURCES = [
    "claude_reasoning",        # Claude's explicit psychological analysis
    "empirical_patterns",      # Statistically discovered behavioral patterns
    "nonconscious_signals",    # Supraliminal data (keystroke, scroll, dwell)
    "graph_emergence",         # Graph-derived relational insights
    "bandit_posteriors",       # Thompson sampling learned effectiveness
    "meta_learner",            # Routing intelligence across sources
    "mechanism_trajectories",  # Historical mechanism effectiveness
    "temporal_patterns",       # Time-based behavioral patterns
    "cross_domain_transfer",   # Knowledge transfer across domains
    "cohort_organization",     # Cohort-level psychological patterns
]

# Zone 2 subzones for each source
for source in INTELLIGENCE_SOURCES:
    blackboard.create_source_space(
        request_id=request_id,
        source_id=source
    )
```

### Integration with Enhancement #06 (Gradient Bridge)

The Blackboard's Zone 5 feeds directly into Gradient Bridge for attribution:

```python
# Zone 5 learning signals are consumed by Gradient Bridge
class GradientBridgeBlackboardConsumer:
    async def process_learning_signal(self, signal: LearningSignal):
        # Signal contains full attribution context from Blackboard
        attribution_context = AttributionContext(
            request_id=signal.request_id,
            decision_id=signal.decision_id,
            # Zone 1-4 snapshot for complete context
            request_context=signal.zone1_snapshot,
            atom_outputs=signal.zone2_summary,
            synthesis_output=signal.zone3_summary,
            decision_output=signal.zone4_snapshot,
            # Outcome data
            outcome_type=signal.outcome_type,
            outcome_value=signal.outcome_value,
            delay_seconds=signal.observation_delay
        )
        
        await self.gradient_bridge.route_attribution(attribution_context)
```

---


# SECTION B: PYDANTIC MODELS - CORE STATE

## Blackboard Core Models

### Blackboard Configuration

```python
"""
ADAM Enhancement #02: Blackboard Configuration Models
Enterprise-grade configuration for shared state architecture.
"""

from enum import Enum
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, validator
from datetime import timedelta


class BlackboardZone(str, Enum):
    """Blackboard zone identifiers."""
    REQUEST_CONTEXT = "zone1_request_context"
    ATOM_REASONING = "zone2_atom_reasoning"
    SYNTHESIS_WORKSPACE = "zone3_synthesis_workspace"
    DECISION_STATE = "zone4_decision_state"
    LEARNING_SIGNALS = "zone5_learning_signals"


class ZoneAccessLevel(str, Enum):
    """Access level for zone operations."""
    NONE = "none"
    READ = "read"
    WRITE = "write"
    READ_WRITE = "read_write"


class BlackboardZoneConfig(BaseModel):
    """Configuration for a single blackboard zone."""
    
    zone: BlackboardZone = Field(
        ...,
        description="Zone identifier"
    )
    
    redis_prefix: str = Field(
        ...,
        description="Redis key prefix for this zone"
    )
    
    default_ttl_seconds: int = Field(
        ...,
        ge=60,
        le=604800,  # Max 7 days
        description="Default TTL for entries in this zone"
    )
    
    max_entry_size_bytes: int = Field(
        default=1048576,  # 1MB
        ge=1024,
        description="Maximum size of a single entry"
    )
    
    enable_pubsub: bool = Field(
        default=True,
        description="Whether to emit pub/sub events for this zone"
    )
    
    pubsub_channel_pattern: str = Field(
        default="blackboard.{zone}.{event}",
        description="Pub/sub channel pattern for events"
    )
    
    enable_persistence: bool = Field(
        default=False,
        description="Whether to persist zone data to Neo4j"
    )
    
    compression_enabled: bool = Field(
        default=False,
        description="Whether to compress large entries"
    )
    
    compression_threshold_bytes: int = Field(
        default=10240,  # 10KB
        description="Minimum size before compression"
    )


class BlackboardConfig(BaseModel):
    """Complete blackboard configuration."""
    
    # Redis connection
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL"
    )
    
    redis_pool_size: int = Field(
        default=20,
        ge=5,
        le=100,
        description="Redis connection pool size"
    )
    
    redis_timeout_seconds: float = Field(
        default=5.0,
        ge=0.1,
        le=30.0,
        description="Redis operation timeout"
    )
    
    # Zone configurations
    zones: Dict[BlackboardZone, BlackboardZoneConfig] = Field(
        default_factory=lambda: {
            BlackboardZone.REQUEST_CONTEXT: BlackboardZoneConfig(
                zone=BlackboardZone.REQUEST_CONTEXT,
                redis_prefix="bb:z1:req:",
                default_ttl_seconds=600,  # 10 minutes
                enable_persistence=False,
                compression_enabled=False
            ),
            BlackboardZone.ATOM_REASONING: BlackboardZoneConfig(
                zone=BlackboardZone.ATOM_REASONING,
                redis_prefix="bb:z2:atom:",
                default_ttl_seconds=1800,  # 30 minutes
                enable_persistence=True,  # Persist reasoning traces
                compression_enabled=True
            ),
            BlackboardZone.SYNTHESIS_WORKSPACE: BlackboardZoneConfig(
                zone=BlackboardZone.SYNTHESIS_WORKSPACE,
                redis_prefix="bb:z3:synth:",
                default_ttl_seconds=3600,  # 1 hour
                enable_persistence=True,
                compression_enabled=True
            ),
            BlackboardZone.DECISION_STATE: BlackboardZoneConfig(
                zone=BlackboardZone.DECISION_STATE,
                redis_prefix="bb:z4:dec:",
                default_ttl_seconds=86400,  # 24 hours
                enable_persistence=True,
                compression_enabled=False
            ),
            BlackboardZone.LEARNING_SIGNALS: BlackboardZoneConfig(
                zone=BlackboardZone.LEARNING_SIGNALS,
                redis_prefix="bb:z5:learn:",
                default_ttl_seconds=259200,  # 72 hours
                enable_persistence=True,
                compression_enabled=True
            ),
        }
    )
    
    # Event bus configuration
    event_bus_topic_prefix: str = Field(
        default="adam.blackboard",
        description="Kafka topic prefix for blackboard events"
    )
    
    # Neo4j persistence
    neo4j_uri: str = Field(
        default="bolt://localhost:7687",
        description="Neo4j connection URI"
    )
    
    neo4j_batch_size: int = Field(
        default=100,
        ge=10,
        le=1000,
        description="Batch size for Neo4j persistence"
    )
    
    neo4j_flush_interval_seconds: float = Field(
        default=5.0,
        ge=1.0,
        le=60.0,
        description="Interval for flushing to Neo4j"
    )
    
    # Metrics
    enable_metrics: bool = Field(
        default=True,
        description="Whether to collect Prometheus metrics"
    )
    
    metrics_prefix: str = Field(
        default="adam_blackboard",
        description="Prometheus metric prefix"
    )


class ComponentAccessConfig(BaseModel):
    """Access configuration for a specific component."""
    
    component_id: str = Field(
        ...,
        description="Unique component identifier"
    )
    
    component_type: str = Field(
        ...,
        description="Component type (atom, synthesis, decision, learner)"
    )
    
    zone_access: Dict[BlackboardZone, ZoneAccessLevel] = Field(
        ...,
        description="Access level for each zone"
    )
    
    allowed_atom_spaces: Optional[List[str]] = Field(
        default=None,
        description="For Zone 2: which atom spaces this component can access"
    )
    
    rate_limit_reads_per_second: Optional[int] = Field(
        default=None,
        description="Optional rate limit for reads"
    )
    
    rate_limit_writes_per_second: Optional[int] = Field(
        default=None,
        description="Optional rate limit for writes"
    )


# Pre-configured access profiles for common components
ATOM_ACCESS_PROFILE = ComponentAccessConfig(
    component_id="atom_template",
    component_type="atom",
    zone_access={
        BlackboardZone.REQUEST_CONTEXT: ZoneAccessLevel.READ,
        BlackboardZone.ATOM_REASONING: ZoneAccessLevel.READ_WRITE,  # Own space only
        BlackboardZone.SYNTHESIS_WORKSPACE: ZoneAccessLevel.NONE,
        BlackboardZone.DECISION_STATE: ZoneAccessLevel.NONE,
        BlackboardZone.LEARNING_SIGNALS: ZoneAccessLevel.WRITE,
    }
)

SYNTHESIS_ACCESS_PROFILE = ComponentAccessConfig(
    component_id="synthesis",
    component_type="synthesis",
    zone_access={
        BlackboardZone.REQUEST_CONTEXT: ZoneAccessLevel.READ,
        BlackboardZone.ATOM_REASONING: ZoneAccessLevel.READ,  # All atom spaces
        BlackboardZone.SYNTHESIS_WORKSPACE: ZoneAccessLevel.READ_WRITE,
        BlackboardZone.DECISION_STATE: ZoneAccessLevel.NONE,
        BlackboardZone.LEARNING_SIGNALS: ZoneAccessLevel.WRITE,
    }
)

DECISION_ACCESS_PROFILE = ComponentAccessConfig(
    component_id="decision",
    component_type="decision",
    zone_access={
        BlackboardZone.REQUEST_CONTEXT: ZoneAccessLevel.READ,
        BlackboardZone.ATOM_REASONING: ZoneAccessLevel.NONE,
        BlackboardZone.SYNTHESIS_WORKSPACE: ZoneAccessLevel.READ,
        BlackboardZone.DECISION_STATE: ZoneAccessLevel.READ_WRITE,
        BlackboardZone.LEARNING_SIGNALS: ZoneAccessLevel.WRITE,
    }
)

META_LEARNER_ACCESS_PROFILE = ComponentAccessConfig(
    component_id="meta_learner",
    component_type="learner",
    zone_access={
        BlackboardZone.REQUEST_CONTEXT: ZoneAccessLevel.READ,
        BlackboardZone.ATOM_REASONING: ZoneAccessLevel.READ,
        BlackboardZone.SYNTHESIS_WORKSPACE: ZoneAccessLevel.READ,
        BlackboardZone.DECISION_STATE: ZoneAccessLevel.READ,
        BlackboardZone.LEARNING_SIGNALS: ZoneAccessLevel.READ_WRITE,
    }
)

GRADIENT_BRIDGE_ACCESS_PROFILE = ComponentAccessConfig(
    component_id="gradient_bridge",
    component_type="learner",
    zone_access={
        BlackboardZone.REQUEST_CONTEXT: ZoneAccessLevel.READ,
        BlackboardZone.ATOM_REASONING: ZoneAccessLevel.READ,
        BlackboardZone.SYNTHESIS_WORKSPACE: ZoneAccessLevel.READ,
        BlackboardZone.DECISION_STATE: ZoneAccessLevel.READ,
        BlackboardZone.LEARNING_SIGNALS: ZoneAccessLevel.READ_WRITE,
    }
)
```

### Blackboard Entry Models

```python
"""
ADAM Enhancement #02: Blackboard Entry Models
Base models for all blackboard entries with metadata tracking.
"""

from datetime import datetime
from typing import Optional, Dict, Any, Generic, TypeVar
from pydantic import BaseModel, Field
from pydantic.generics import GenericModel
import uuid


T = TypeVar('T')


class BlackboardMetadata(BaseModel):
    """Metadata attached to every blackboard entry."""
    
    entry_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique entry identifier"
    )
    
    request_id: str = Field(
        ...,
        description="Request this entry belongs to"
    )
    
    zone: BlackboardZone = Field(
        ...,
        description="Zone this entry resides in"
    )
    
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Entry creation timestamp"
    )
    
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Last update timestamp"
    )
    
    version: int = Field(
        default=1,
        ge=1,
        description="Entry version for optimistic locking"
    )
    
    writer_component: str = Field(
        ...,
        description="Component that created/updated this entry"
    )
    
    ttl_seconds: int = Field(
        ...,
        ge=60,
        description="Time-to-live in seconds"
    )
    
    size_bytes: int = Field(
        default=0,
        ge=0,
        description="Serialized size in bytes"
    )
    
    compressed: bool = Field(
        default=False,
        description="Whether the data is compressed"
    )
    
    checksum: Optional[str] = Field(
        default=None,
        description="Data integrity checksum"
    )
    
    correlation_id: Optional[str] = Field(
        default=None,
        description="For tracing across components"
    )
    
    parent_entry_id: Optional[str] = Field(
        default=None,
        description="For hierarchical entries"
    )


class BlackboardEntry(GenericModel, Generic[T]):
    """Generic wrapper for all blackboard entries."""
    
    metadata: BlackboardMetadata = Field(
        ...,
        description="Entry metadata"
    )
    
    data: T = Field(
        ...,
        description="Entry payload"
    )
    
    class Config:
        arbitrary_types_allowed = True


class BlackboardWriteResult(BaseModel):
    """Result of a blackboard write operation."""
    
    success: bool = Field(
        ...,
        description="Whether the write succeeded"
    )
    
    entry_id: str = Field(
        ...,
        description="Entry ID that was written"
    )
    
    version: int = Field(
        ...,
        description="New version number"
    )
    
    redis_key: str = Field(
        ...,
        description="Redis key where data was stored"
    )
    
    write_latency_ms: float = Field(
        ...,
        ge=0,
        description="Write operation latency"
    )
    
    event_published: bool = Field(
        default=False,
        description="Whether a pub/sub event was emitted"
    )
    
    error: Optional[str] = Field(
        default=None,
        description="Error message if write failed"
    )


class BlackboardReadResult(GenericModel, Generic[T]):
    """Result of a blackboard read operation."""
    
    found: bool = Field(
        ...,
        description="Whether the entry was found"
    )
    
    entry: Optional[BlackboardEntry[T]] = Field(
        default=None,
        description="The entry if found"
    )
    
    redis_key: str = Field(
        ...,
        description="Redis key that was queried"
    )
    
    read_latency_ms: float = Field(
        ...,
        ge=0,
        description="Read operation latency"
    )
    
    cache_hit: bool = Field(
        default=False,
        description="Whether this was served from local cache"
    )
    
    error: Optional[str] = Field(
        default=None,
        description="Error message if read failed"
    )
```

---

## Request Context Models

### Zone 1: Request Context

```python
"""
ADAM Enhancement #02: Zone 1 - Request Context Models
Immutable context established at request start.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple
from pydantic import BaseModel, Field, validator
from enum import Enum


class RequestSource(str, Enum):
    """Source of the ad serving request."""
    IHEART_AUDIO = "iheart_audio"
    IHEART_DISPLAY = "iheart_display"
    WPP_AD_DESK = "wpp_ad_desk"
    PROGRAMMATIC = "programmatic"
    DIRECT_API = "direct_api"
    INTERNAL_TEST = "internal_test"


class ContentType(str, Enum):
    """Type of content being consumed."""
    AUDIO_PODCAST = "audio_podcast"
    AUDIO_MUSIC = "audio_music"
    AUDIO_NEWS = "audio_news"
    AUDIO_LIVE = "audio_live"
    VIDEO = "video"
    DISPLAY = "display"
    NATIVE = "native"


class DeviceType(str, Enum):
    """User's device type."""
    MOBILE_IOS = "mobile_ios"
    MOBILE_ANDROID = "mobile_android"
    DESKTOP = "desktop"
    TABLET = "tablet"
    SMART_SPEAKER = "smart_speaker"
    CONNECTED_TV = "connected_tv"
    CAR = "car"


class UserIdentifiers(BaseModel):
    """User identification context."""
    
    user_id: str = Field(
        ...,
        description="ADAM internal user ID"
    )
    
    iheart_user_id: Optional[str] = Field(
        default=None,
        description="iHeart platform user ID"
    )
    
    device_id: Optional[str] = Field(
        default=None,
        description="Device identifier"
    )
    
    session_id: str = Field(
        ...,
        description="Current session identifier"
    )
    
    household_id: Optional[str] = Field(
        default=None,
        description="Household grouping ID"
    )
    
    identity_confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Confidence in identity resolution"
    )
    
    is_known_user: bool = Field(
        default=False,
        description="Whether user has established profile"
    )
    
    profile_age_days: Optional[int] = Field(
        default=None,
        ge=0,
        description="Days since first observation"
    )


class ContentContext(BaseModel):
    """Context about current content being consumed."""
    
    content_id: str = Field(
        ...,
        description="Content identifier"
    )
    
    content_type: ContentType = Field(
        ...,
        description="Type of content"
    )
    
    content_title: Optional[str] = Field(
        default=None,
        description="Content title for context"
    )
    
    content_genre: Optional[str] = Field(
        default=None,
        description="Genre classification"
    )
    
    content_mood: Optional[str] = Field(
        default=None,
        description="Detected mood/energy level"
    )
    
    content_duration_seconds: Optional[int] = Field(
        default=None,
        ge=0,
        description="Total content duration"
    )
    
    playback_position_seconds: Optional[int] = Field(
        default=None,
        ge=0,
        description="Current playback position"
    )
    
    is_premium_content: bool = Field(
        default=False,
        description="Whether this is premium content"
    )
    
    content_language: str = Field(
        default="en",
        description="Content language"
    )
    
    topic_tags: List[str] = Field(
        default_factory=list,
        description="Content topic tags"
    )


class AdCandidateInfo(BaseModel):
    """Information about a single ad candidate."""
    
    ad_id: str = Field(
        ...,
        description="Ad creative identifier"
    )
    
    campaign_id: str = Field(
        ...,
        description="Campaign identifier"
    )
    
    advertiser_id: str = Field(
        ...,
        description="Advertiser identifier"
    )
    
    brand_name: Optional[str] = Field(
        default=None,
        description="Brand name"
    )
    
    ad_format: str = Field(
        ...,
        description="Ad format (audio_30s, display_300x250, etc.)"
    )
    
    creative_tone: Optional[str] = Field(
        default=None,
        description="Creative tone classification"
    )
    
    call_to_action: Optional[str] = Field(
        default=None,
        description="Primary CTA"
    )
    
    target_mechanisms: List[str] = Field(
        default_factory=list,
        description="Mechanisms this creative was designed for"
    )
    
    floor_cpm: Optional[float] = Field(
        default=None,
        ge=0,
        description="Minimum CPM"
    )
    
    priority_score: Optional[float] = Field(
        default=None,
        ge=0,
        le=1,
        description="Campaign priority"
    )


class GraphDerivedPriors(BaseModel):
    """Priors derived from Neo4j graph at request time."""
    
    # Big Five personality priors
    openness_prior: Tuple[float, float] = Field(
        default=(0.5, 0.2),
        description="(mean, std) for Openness"
    )
    conscientiousness_prior: Tuple[float, float] = Field(
        default=(0.5, 0.2),
        description="(mean, std) for Conscientiousness"
    )
    extraversion_prior: Tuple[float, float] = Field(
        default=(0.5, 0.2),
        description="(mean, std) for Extraversion"
    )
    agreeableness_prior: Tuple[float, float] = Field(
        default=(0.5, 0.2),
        description="(mean, std) for Agreeableness"
    )
    neuroticism_prior: Tuple[float, float] = Field(
        default=(0.5, 0.2),
        description="(mean, std) for Neuroticism"
    )
    
    # Mechanism effectiveness priors (Thompson sampling)
    mechanism_priors: Dict[str, Tuple[float, float]] = Field(
        default_factory=dict,
        description="Prior (alpha, beta) for each mechanism"
    )
    
    # Recent state trajectory
    recent_states: List[Dict[str, Any]] = Field(
        default_factory=list,
        max_items=10,
        description="Last N psychological state observations"
    )
    
    # Confidence in priors
    profile_confidence: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Overall confidence in profile priors"
    )
    
    observations_count: int = Field(
        default=0,
        ge=0,
        description="Number of observations backing these priors"
    )
    
    last_interaction_at: Optional[datetime] = Field(
        default=None,
        description="Last interaction timestamp"
    )


class RequestContext(BaseModel):
    """
    Zone 1: Complete request context.
    Set once at request start, read-only for all components.
    """
    
    # Request identification
    request_id: str = Field(
        ...,
        description="Unique request identifier"
    )
    
    request_timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Request received timestamp"
    )
    
    request_source: RequestSource = Field(
        ...,
        description="Source of the request"
    )
    
    # User context
    user: UserIdentifiers = Field(
        ...,
        description="User identification context"
    )
    
    # Content context
    content: ContentContext = Field(
        ...,
        description="Current content context"
    )
    
    # Device context
    device_type: DeviceType = Field(
        ...,
        description="User's device"
    )
    
    device_os_version: Optional[str] = Field(
        default=None,
        description="OS version"
    )
    
    # Ad candidates
    ad_candidates: List[AdCandidateInfo] = Field(
        ...,
        min_items=1,
        description="Candidate ads to choose from"
    )
    
    # Graph-derived context
    graph_priors: GraphDerivedPriors = Field(
        default_factory=GraphDerivedPriors,
        description="Priors from Neo4j graph"
    )
    
    # Temporal context
    local_hour: int = Field(
        ...,
        ge=0,
        le=23,
        description="User's local hour"
    )
    
    local_day_of_week: int = Field(
        ...,
        ge=0,
        le=6,
        description="User's local day (0=Monday)"
    )
    
    is_weekend: bool = Field(
        default=False,
        description="Whether it's user's weekend"
    )
    
    # Session context
    session_depth: int = Field(
        default=1,
        ge=1,
        description="How many requests in this session"
    )
    
    session_duration_seconds: int = Field(
        default=0,
        ge=0,
        description="Session duration so far"
    )
    
    previous_ad_ids: List[str] = Field(
        default_factory=list,
        description="Ads shown earlier in session"
    )
    
    # Latency budget
    latency_budget_ms: int = Field(
        default=100,
        ge=10,
        le=5000,
        description="Maximum latency for this request"
    )
    
    # Feature flags
    enable_full_reasoning: bool = Field(
        default=True,
        description="Whether to use full atom reasoning"
    )
    
    fallback_tier_allowed: int = Field(
        default=4,
        ge=1,
        le=4,
        description="Lowest fallback tier allowed (1=full, 4=default)"
    )
    
    enable_learning_signals: bool = Field(
        default=True,
        description="Whether to emit learning signals"
    )
    
    @validator('ad_candidates')
    def validate_candidates(cls, v):
        if len(v) > 50:
            raise ValueError("Too many ad candidates (max 50)")
        return v
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
```

---

## User Intelligence Package

### Psychological Profile Snapshot

```python
"""
ADAM Enhancement #02: User Intelligence Package
Comprehensive psychological snapshot for reasoning context.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple
from pydantic import BaseModel, Field
from enum import Enum


class TraitConfidenceLevel(str, Enum):
    """Confidence level in trait estimate."""
    HIGH = "high"        # >50 observations, consistent
    MEDIUM = "medium"    # 10-50 observations
    LOW = "low"          # <10 observations
    INFERRED = "inferred"  # Derived from related signals
    UNKNOWN = "unknown"   # No data


class BigFiveProfile(BaseModel):
    """Big Five personality trait profile."""
    
    openness: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Openness to Experience (0-1 normalized)"
    )
    openness_confidence: TraitConfidenceLevel = Field(
        default=TraitConfidenceLevel.UNKNOWN
    )
    
    conscientiousness: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Conscientiousness (0-1 normalized)"
    )
    conscientiousness_confidence: TraitConfidenceLevel = Field(
        default=TraitConfidenceLevel.UNKNOWN
    )
    
    extraversion: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Extraversion (0-1 normalized)"
    )
    extraversion_confidence: TraitConfidenceLevel = Field(
        default=TraitConfidenceLevel.UNKNOWN
    )
    
    agreeableness: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Agreeableness (0-1 normalized)"
    )
    agreeableness_confidence: TraitConfidenceLevel = Field(
        default=TraitConfidenceLevel.UNKNOWN
    )
    
    neuroticism: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Neuroticism (0-1 normalized)"
    )
    neuroticism_confidence: TraitConfidenceLevel = Field(
        default=TraitConfidenceLevel.UNKNOWN
    )
    
    # Profile metadata
    last_updated: datetime = Field(
        default_factory=datetime.utcnow
    )
    
    observation_count: int = Field(
        default=0,
        ge=0
    )
    
    profile_stability: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="How stable traits have been over time"
    )


class MechanismSensitivity(BaseModel):
    """User's sensitivity to specific persuasion mechanisms."""
    
    mechanism_id: str = Field(
        ...,
        description="Mechanism identifier"
    )
    
    # Thompson sampling posterior
    alpha: float = Field(
        default=1.0,
        ge=0.1,
        description="Success count + prior"
    )
    
    beta: float = Field(
        default=1.0,
        ge=0.1,
        description="Failure count + prior"
    )
    
    # Derived metrics
    mean_effectiveness: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Expected effectiveness (alpha / (alpha + beta))"
    )
    
    confidence_interval_width: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="95% CI width"
    )
    
    # Historical performance
    total_exposures: int = Field(
        default=0,
        ge=0
    )
    
    total_conversions: int = Field(
        default=0,
        ge=0
    )
    
    recent_trend: str = Field(
        default="stable",
        description="improving/stable/declining"
    )
    
    # Context modifiers
    context_modifiers: Dict[str, float] = Field(
        default_factory=dict,
        description="Effectiveness modifiers by context"
    )


class UserIntelligencePackage(BaseModel):
    """
    Comprehensive user intelligence snapshot.
    Combines all known information about the user.
    """
    
    user_id: str = Field(
        ...,
        description="User identifier"
    )
    
    snapshot_timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="When this snapshot was created"
    )
    
    # Personality profile
    personality: BigFiveProfile = Field(
        ...,
        description="Big Five personality traits"
    )
    
    # Mechanism sensitivities
    mechanism_sensitivities: Dict[str, MechanismSensitivity] = Field(
        default_factory=dict,
        description="Sensitivity to each mechanism"
    )
    
    # Psychological constructs
    regulatory_focus_tendency: Optional[str] = Field(
        default=None,
        description="promotion/prevention/balanced"
    )
    
    construal_level_tendency: Optional[str] = Field(
        default=None,
        description="abstract/concrete/context-dependent"
    )
    
    temporal_orientation: Optional[str] = Field(
        default=None,
        description="future/present/past oriented"
    )
    
    risk_tolerance: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Risk tolerance (0=averse, 1=seeking)"
    )
    
    # Behavioral patterns
    engagement_patterns: Dict[str, float] = Field(
        default_factory=dict,
        description="Engagement by content type"
    )
    
    peak_activity_hours: List[int] = Field(
        default_factory=list,
        description="Hours of peak activity"
    )
    
    preferred_ad_formats: List[str] = Field(
        default_factory=list,
        description="Historically effective ad formats"
    )
    
    # Value and lifecycle
    lifetime_value_estimate: Optional[float] = Field(
        default=None,
        ge=0,
        description="Estimated LTV"
    )
    
    lifecycle_stage: str = Field(
        default="unknown",
        description="new/developing/mature/declining"
    )
    
    churn_risk: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Estimated churn probability"
    )
    
    # Data quality
    profile_completeness: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Fraction of profile attributes known"
    )
    
    total_observations: int = Field(
        default=0,
        ge=0,
        description="Total behavioral observations"
    )
    
    days_since_first_seen: int = Field(
        default=0,
        ge=0
    )
    
    # Cohort memberships
    cohort_ids: List[str] = Field(
        default_factory=list,
        description="Psychological cohorts this user belongs to"
    )
    
    # Cross-domain transfer
    transfer_domains: Dict[str, float] = Field(
        default_factory=dict,
        description="Knowledge transfer confidence by domain"
    )
```

---

## State × Trait Framework

### Real-Time State Modeling

```python
"""
ADAM Enhancement #02: State × Trait Framework
Combines stable traits with momentary psychological states.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from enum import Enum


class ArousalLevel(str, Enum):
    """Current arousal state."""
    VERY_LOW = "very_low"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    VERY_HIGH = "very_high"


class ValenceLevel(str, Enum):
    """Current emotional valence."""
    VERY_NEGATIVE = "very_negative"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    POSITIVE = "positive"
    VERY_POSITIVE = "very_positive"


class CognitiveLoadLevel(str, Enum):
    """Current cognitive load."""
    MINIMAL = "minimal"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    OVERLOADED = "overloaded"


class AttentionState(str, Enum):
    """Current attention state."""
    FOCUSED = "focused"
    ENGAGED = "engaged"
    PASSIVE = "passive"
    DISTRACTED = "distracted"
    DISENGAGED = "disengaged"


class MomentaryState(BaseModel):
    """
    User's momentary psychological state.
    Changes rapidly based on current context and behavior.
    """
    
    # Affective dimensions
    arousal: ArousalLevel = Field(
        default=ArousalLevel.MODERATE,
        description="Current arousal level"
    )
    arousal_confidence: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0
    )
    
    valence: ValenceLevel = Field(
        default=ValenceLevel.NEUTRAL,
        description="Current emotional valence"
    )
    valence_confidence: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0
    )
    
    # Cognitive dimensions
    cognitive_load: CognitiveLoadLevel = Field(
        default=CognitiveLoadLevel.MODERATE,
        description="Current cognitive load"
    )
    cognitive_load_confidence: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0
    )
    
    attention: AttentionState = Field(
        default=AttentionState.ENGAGED,
        description="Current attention state"
    )
    attention_confidence: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0
    )
    
    # Motivational dimensions
    goal_orientation: str = Field(
        default="mixed",
        description="Current goal orientation (achievement/avoidance/mixed)"
    )
    
    regulatory_mode: str = Field(
        default="unknown",
        description="Current regulatory mode (locomotion/assessment/unknown)"
    )
    
    # Behavioral signals (from nonconscious data)
    click_velocity: Optional[float] = Field(
        default=None,
        ge=0,
        description="Clicks per minute"
    )
    
    scroll_pattern: Optional[str] = Field(
        default=None,
        description="Scroll pattern (fast_scan/slow_read/jump/smooth)"
    )
    
    dwell_time_trend: Optional[str] = Field(
        default=None,
        description="Dwell time trend (increasing/stable/decreasing)"
    )
    
    # Temporal context
    session_fatigue: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Estimated session fatigue"
    )
    
    time_pressure: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Detected time pressure"
    )
    
    # State metadata
    state_timestamp: datetime = Field(
        default_factory=datetime.utcnow
    )
    
    signals_used: List[str] = Field(
        default_factory=list,
        description="Signals used to infer this state"
    )
    
    state_stability: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="How stable this state has been"
    )


class StateTraitInteraction(BaseModel):
    """
    Models how current state interacts with stable traits.
    Key insight: The SAME trait manifests differently based on state.
    """
    
    # Trait being modulated
    trait_name: str = Field(
        ...,
        description="Which trait is being modulated"
    )
    
    base_trait_value: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Stable trait value"
    )
    
    # State modulation
    state_modulator: str = Field(
        ...,
        description="Which state is modulating"
    )
    
    modulation_direction: str = Field(
        ...,
        description="amplify/suppress/shift"
    )
    
    modulation_magnitude: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Strength of modulation"
    )
    
    # Effective value
    effective_trait_value: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Trait value after state modulation"
    )
    
    # Confidence
    interaction_confidence: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0
    )
    
    # Evidence
    supporting_evidence: List[str] = Field(
        default_factory=list
    )


class StateTraitSnapshot(BaseModel):
    """
    Complete State × Trait snapshot for decision making.
    This is what atoms and synthesis use for psychological targeting.
    """
    
    request_id: str = Field(
        ...,
        description="Request this snapshot belongs to"
    )
    
    user_id: str = Field(
        ...,
        description="User identifier"
    )
    
    snapshot_timestamp: datetime = Field(
        default_factory=datetime.utcnow
    )
    
    # Stable traits
    traits: BigFiveProfile = Field(
        ...,
        description="Stable personality traits"
    )
    
    # Momentary state
    current_state: MomentaryState = Field(
        ...,
        description="Current psychological state"
    )
    
    # State × Trait interactions
    interactions: List[StateTraitInteraction] = Field(
        default_factory=list,
        description="Active state-trait interactions"
    )
    
    # Effective psychological profile (traits modulated by state)
    effective_profile: Dict[str, float] = Field(
        default_factory=dict,
        description="Effective trait values after state modulation"
    )
    
    # Mechanism recommendations (based on state × trait)
    recommended_mechanisms: List[str] = Field(
        default_factory=list,
        description="Mechanisms likely effective given current state × trait"
    )
    
    # Mechanisms to avoid
    avoid_mechanisms: List[str] = Field(
        default_factory=list,
        description="Mechanisms likely to backfire"
    )
    
    # Overall targeting confidence
    targeting_confidence: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Confidence in targeting recommendations"
    )
    
    # Attribution context
    state_sources: List[str] = Field(
        default_factory=list,
        description="Intelligence sources contributing to state"
    )
    
    trait_sources: List[str] = Field(
        default_factory=list,
        description="Intelligence sources contributing to traits"
    )
```


# SECTION C: PYDANTIC MODELS - REASONING SPACES

## Atom Reasoning Space Models

### Zone 2: Atom Workspace Foundation

```python
"""
ADAM Enhancement #02: Zone 2 - Atom Reasoning Space Models
Workspaces for psychological reasoning atoms.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple
from pydantic import BaseModel, Field, validator
from enum import Enum
import uuid


class AtomStatus(str, Enum):
    """Atom execution status."""
    PENDING = "pending"
    INITIALIZING = "initializing"
    REASONING = "reasoning"
    SYNTHESIZING = "synthesizing"
    COMPLETE = "complete"
    ERROR = "error"
    TIMEOUT = "timeout"
    SKIPPED = "skipped"


class AtomType(str, Enum):
    """Types of reasoning atoms."""
    # Core psychological mechanism atoms
    REGULATORY_FOCUS = "regulatory_focus"
    CONSTRUAL_LEVEL = "construal_level"
    TEMPORAL_FRAMING = "temporal_framing"
    SOCIAL_PROOF = "social_proof"
    SCARCITY = "scarcity"
    AUTHORITY = "authority"
    RECIPROCITY = "reciprocity"
    COMMITMENT_CONSISTENCY = "commitment_consistency"
    LOSS_AVERSION = "loss_aversion"
    
    # Meta-level atoms
    PERSONALITY_INFERENCE = "personality_inference"
    STATE_DETECTION = "state_detection"
    MECHANISM_SELECTION = "mechanism_selection"
    
    # Specialized atoms
    VOICE_PERSONALITY = "voice_personality"
    NONCONSCIOUS_SIGNAL = "nonconscious_signal"
    TEMPORAL_PATTERN = "temporal_pattern"


class PreliminarySignal(BaseModel):
    """
    Early detection signal from an atom.
    Published to blackboard during reasoning for cross-atom coordination.
    """
    
    signal_id: str = Field(
        default_factory=lambda: str(uuid.uuid4())
    )
    
    signal_type: str = Field(
        ...,
        description="Type of signal (arousal_detection, mechanism_match, etc.)"
    )
    
    signal_value: Any = Field(
        ...,
        description="Signal value (type depends on signal_type)"
    )
    
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence in this signal"
    )
    
    timestamp: datetime = Field(
        default_factory=datetime.utcnow
    )
    
    evidence: List[str] = Field(
        default_factory=list,
        description="Evidence supporting this signal"
    )
    
    source_atom: str = Field(
        ...,
        description="Atom that produced this signal"
    )
    
    # For cross-atom coordination
    requires_attention: bool = Field(
        default=False,
        description="Whether other atoms should pay attention to this"
    )
    
    attention_reason: Optional[str] = Field(
        default=None,
        description="Why this needs attention"
    )
    
    supersedes_signal_id: Optional[str] = Field(
        default=None,
        description="Previous signal this supersedes"
    )


class ConfidenceEvolution(BaseModel):
    """Tracks how confidence evolved during reasoning."""
    
    timestamp: datetime = Field(
        default_factory=datetime.utcnow
    )
    
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0
    )
    
    reason: str = Field(
        ...,
        description="Why confidence changed"
    )
    
    evidence_delta: Optional[str] = Field(
        default=None,
        description="New evidence that changed confidence"
    )


class AlternativeHypothesis(BaseModel):
    """An alternative interpretation the atom considered."""
    
    hypothesis: str = Field(
        ...,
        description="The alternative interpretation"
    )
    
    initial_probability: float = Field(
        ...,
        ge=0.0,
        le=1.0
    )
    
    final_probability: float = Field(
        ...,
        ge=0.0,
        le=1.0
    )
    
    rejection_reason: Optional[str] = Field(
        default=None,
        description="Why this was rejected (if applicable)"
    )
    
    supporting_evidence: List[str] = Field(
        default_factory=list
    )
    
    contradicting_evidence: List[str] = Field(
        default_factory=list
    )


class AtomReasoningTrace(BaseModel):
    """Detailed trace of atom reasoning for learning and debugging."""
    
    # Input summary
    input_context_summary: str = Field(
        ...,
        description="Summary of input context used"
    )
    
    # Reasoning steps
    reasoning_steps: List[str] = Field(
        default_factory=list,
        description="Key reasoning steps"
    )
    
    # Evidence considered
    evidence_for: List[str] = Field(
        default_factory=list,
        description="Evidence supporting conclusion"
    )
    
    evidence_against: List[str] = Field(
        default_factory=list,
        description="Evidence against conclusion"
    )
    
    # Key insights
    key_insights: List[str] = Field(
        default_factory=list,
        description="Important insights discovered"
    )
    
    # Uncertainties
    remaining_uncertainties: List[str] = Field(
        default_factory=list,
        description="Uncertainties that couldn't be resolved"
    )
    
    # Self-assessment
    self_assessed_quality: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Atom's assessment of reasoning quality"
    )
    
    # Claude token usage
    tokens_used: Optional[int] = Field(
        default=None,
        ge=0
    )
    
    # Latency breakdown
    latency_context_ms: Optional[float] = Field(
        default=None
    )
    latency_reasoning_ms: Optional[float] = Field(
        default=None
    )
    latency_output_ms: Optional[float] = Field(
        default=None
    )


class AtomOutput(BaseModel):
    """Final output from an atom."""
    
    # Primary determination
    determination: str = Field(
        ...,
        description="Primary output (e.g., 'promotion', 'concrete', etc.)"
    )
    
    # Scores
    primary_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Primary score for the determination"
    )
    
    secondary_scores: Dict[str, float] = Field(
        default_factory=dict,
        description="Scores for alternative determinations"
    )
    
    # Confidence
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence in determination"
    )
    
    # Evidence summary
    evidence_summary: List[str] = Field(
        default_factory=list,
        description="Key evidence for determination"
    )
    
    # Mechanism recommendations
    mechanism_recommendation: Optional[str] = Field(
        default=None,
        description="Recommended mechanism based on analysis"
    )
    
    mechanism_confidence: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0
    )
    
    # State × Trait interaction identified
    state_trait_interaction: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Identified state-trait interaction"
    )
    
    # Flags for downstream
    requires_synthesis_attention: bool = Field(
        default=False,
        description="Unusual finding needing synthesis review"
    )
    
    attention_reason: Optional[str] = Field(
        default=None
    )
    
    conflicts_with: List[str] = Field(
        default_factory=list,
        description="Other atoms this may conflict with"
    )


class AtomReasoningSpace(BaseModel):
    """
    Zone 2: Complete workspace for a single atom.
    Each atom writes to its own namespace, synthesis reads all.
    """
    
    # Identification
    atom_id: str = Field(
        ...,
        description="Atom identifier"
    )
    
    atom_type: AtomType = Field(
        ...,
        description="Type of atom"
    )
    
    request_id: str = Field(
        ...,
        description="Request this belongs to"
    )
    
    # Status
    status: AtomStatus = Field(
        default=AtomStatus.PENDING,
        description="Current execution status"
    )
    
    # Timing
    created_at: datetime = Field(
        default_factory=datetime.utcnow
    )
    
    started_at: Optional[datetime] = Field(
        default=None,
        description="When reasoning started"
    )
    
    completed_at: Optional[datetime] = Field(
        default=None,
        description="When reasoning completed"
    )
    
    # Preliminary signals (published during reasoning)
    preliminary_signals: List[PreliminarySignal] = Field(
        default_factory=list,
        description="Signals published during reasoning"
    )
    
    # Confidence evolution
    confidence_evolution: List[ConfidenceEvolution] = Field(
        default_factory=list,
        description="How confidence changed during reasoning"
    )
    
    # Alternative hypotheses
    alternative_hypotheses: List[AlternativeHypothesis] = Field(
        default_factory=list,
        description="Alternatives considered"
    )
    
    # Cross-atom observations (what this atom read from others)
    observed_signals: List[str] = Field(
        default_factory=list,
        description="Signal IDs read from other atoms"
    )
    
    # Final output
    output: Optional[AtomOutput] = Field(
        default=None,
        description="Final atom output"
    )
    
    # Reasoning trace
    reasoning_trace: Optional[AtomReasoningTrace] = Field(
        default=None,
        description="Detailed reasoning trace"
    )
    
    # Error information
    error_message: Optional[str] = Field(
        default=None,
        description="Error message if status is ERROR"
    )
    
    error_details: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Detailed error information"
    )
    
    # Performance metrics
    latency_ms: Optional[float] = Field(
        default=None,
        ge=0,
        description="Total atom latency"
    )
    
    tokens_used: Optional[int] = Field(
        default=None,
        ge=0,
        description="Claude tokens used"
    )
    
    # Version for optimistic locking
    version: int = Field(
        default=1,
        ge=1
    )
    
    def is_complete(self) -> bool:
        """Check if atom has finished processing."""
        return self.status in [
            AtomStatus.COMPLETE,
            AtomStatus.ERROR,
            AtomStatus.TIMEOUT,
            AtomStatus.SKIPPED
        ]
    
    def duration_ms(self) -> Optional[float]:
        """Calculate execution duration."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds() * 1000
        return None
```

---

## Mechanism-Specific Spaces

### Regulatory Focus Atom Space

```python
"""
ADAM Enhancement #02: Mechanism-Specific Atom Spaces
Specialized workspaces for each psychological mechanism.
"""


class RegulatoryFocusOutput(BaseModel):
    """Output specific to Regulatory Focus atom."""
    
    # Primary determination
    focus: str = Field(
        ...,
        description="promotion/prevention/neutral"
    )
    
    # Dimensional scores
    promotion_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Promotion focus strength"
    )
    
    prevention_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Prevention focus strength"
    )
    
    # Evidence
    promotion_evidence: List[str] = Field(
        default_factory=list
    )
    
    prevention_evidence: List[str] = Field(
        default_factory=list
    )
    
    # State interaction
    arousal_modulation: Optional[str] = Field(
        default=None,
        description="How arousal affects this focus"
    )
    
    # Messaging recommendations
    recommended_framing: str = Field(
        default="neutral",
        description="gain/loss/neutral framing"
    )
    
    recommended_language: List[str] = Field(
        default_factory=list,
        description="Language elements to use"
    )
    
    avoid_language: List[str] = Field(
        default_factory=list,
        description="Language elements to avoid"
    )


class ConstrualLevelOutput(BaseModel):
    """Output specific to Construal Level atom."""
    
    # Primary determination
    level: str = Field(
        ...,
        description="abstract/concrete/mixed"
    )
    
    # Dimensional scores
    abstract_score: float = Field(
        ...,
        ge=0.0,
        le=1.0
    )
    
    concrete_score: float = Field(
        ...,
        ge=0.0,
        le=1.0
    )
    
    # Psychological distance dimensions
    temporal_distance: str = Field(
        default="moderate",
        description="near/moderate/far"
    )
    
    social_distance: str = Field(
        default="moderate",
        description="close/moderate/distant"
    )
    
    spatial_distance: str = Field(
        default="moderate",
        description="proximal/moderate/distal"
    )
    
    hypothetical_distance: str = Field(
        default="moderate",
        description="certain/moderate/unlikely"
    )
    
    # Messaging recommendations
    recommended_specificity: str = Field(
        default="moderate",
        description="high_detail/moderate/big_picture"
    )
    
    recommended_examples: bool = Field(
        default=True,
        description="Whether to use concrete examples"
    )
    
    recommended_benefits: str = Field(
        default="both",
        description="functional/emotional/both"
    )


class TemporalFramingOutput(BaseModel):
    """Output specific to Temporal Framing atom."""
    
    # Primary determination
    orientation: str = Field(
        ...,
        description="future/present/past"
    )
    
    # Dimensional scores
    future_orientation: float = Field(
        ...,
        ge=0.0,
        le=1.0
    )
    
    present_orientation: float = Field(
        ...,
        ge=0.0,
        le=1.0
    )
    
    past_orientation: float = Field(
        ...,
        ge=0.0,
        le=1.0
    )
    
    # Time horizon
    preferred_time_horizon: str = Field(
        default="medium",
        description="immediate/short/medium/long"
    )
    
    # Urgency sensitivity
    urgency_receptiveness: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0
    )
    
    # Messaging recommendations
    recommended_timeframe: str = Field(
        default="medium",
        description="now/soon/later/someday"
    )
    
    use_deadlines: bool = Field(
        default=False
    )
    
    use_future_benefits: bool = Field(
        default=True
    )
    
    use_past_success: bool = Field(
        default=False
    )


class SocialProofOutput(BaseModel):
    """Output specific to Social Proof atom."""
    
    # Primary determination
    susceptibility: str = Field(
        ...,
        description="high/moderate/low/resistant"
    )
    
    susceptibility_score: float = Field(
        ...,
        ge=0.0,
        le=1.0
    )
    
    # Reference group preferences
    preferred_reference_groups: List[str] = Field(
        default_factory=list,
        description="peer/expert/celebrity/aspirational"
    )
    
    # Social proof types
    testimonial_effectiveness: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0
    )
    
    statistics_effectiveness: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0
    )
    
    endorsement_effectiveness: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0
    )
    
    # Messaging recommendations
    recommended_proof_type: str = Field(
        default="statistics",
        description="testimonial/statistics/endorsement/crowd"
    )
    
    reference_group_to_use: Optional[str] = Field(
        default=None
    )
    
    specificity_level: str = Field(
        default="moderate",
        description="vague/moderate/specific"
    )


class ScarcityOutput(BaseModel):
    """Output specific to Scarcity atom."""
    
    # Primary determination
    susceptibility: str = Field(
        ...,
        description="high/moderate/low/resistant"
    )
    
    susceptibility_score: float = Field(
        ...,
        ge=0.0,
        le=1.0
    )
    
    # Scarcity types
    quantity_scarcity_effectiveness: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0
    )
    
    time_scarcity_effectiveness: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0
    )
    
    exclusivity_effectiveness: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0
    )
    
    # Reactance risk
    reactance_risk: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Risk of psychological reactance"
    )
    
    # Messaging recommendations
    recommended_scarcity_type: str = Field(
        default="time",
        description="quantity/time/exclusivity/none"
    )
    
    intensity_level: str = Field(
        default="moderate",
        description="subtle/moderate/strong"
    )
    
    use_countdown: bool = Field(
        default=False
    )
    
    use_stock_indicator: bool = Field(
        default=False
    )


class LossAversionOutput(BaseModel):
    """Output specific to Loss Aversion atom."""
    
    # Primary determination
    loss_aversion_level: str = Field(
        ...,
        description="high/moderate/low"
    )
    
    loss_aversion_score: float = Field(
        ...,
        ge=0.0,
        le=1.0
    )
    
    # Loss vs gain framing
    loss_frame_effectiveness: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0
    )
    
    gain_frame_effectiveness: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0
    )
    
    # Risk domain
    risk_domain_sensitivity: Dict[str, float] = Field(
        default_factory=dict,
        description="Sensitivity by domain (financial, social, etc.)"
    )
    
    # Messaging recommendations
    recommended_framing: str = Field(
        default="balanced",
        description="loss/gain/balanced"
    )
    
    loss_intensity: str = Field(
        default="moderate",
        description="mild/moderate/strong"
    )
    
    use_FOMO: bool = Field(
        default=False
    )


class MechanismAtomSpaces(BaseModel):
    """Container for all mechanism-specific atom spaces."""
    
    request_id: str = Field(
        ...,
        description="Request identifier"
    )
    
    # Core mechanism spaces
    regulatory_focus: Optional[AtomReasoningSpace] = Field(
        default=None
    )
    regulatory_focus_output: Optional[RegulatoryFocusOutput] = Field(
        default=None
    )
    
    construal_level: Optional[AtomReasoningSpace] = Field(
        default=None
    )
    construal_level_output: Optional[ConstrualLevelOutput] = Field(
        default=None
    )
    
    temporal_framing: Optional[AtomReasoningSpace] = Field(
        default=None
    )
    temporal_framing_output: Optional[TemporalFramingOutput] = Field(
        default=None
    )
    
    social_proof: Optional[AtomReasoningSpace] = Field(
        default=None
    )
    social_proof_output: Optional[SocialProofOutput] = Field(
        default=None
    )
    
    scarcity: Optional[AtomReasoningSpace] = Field(
        default=None
    )
    scarcity_output: Optional[ScarcityOutput] = Field(
        default=None
    )
    
    loss_aversion: Optional[AtomReasoningSpace] = Field(
        default=None
    )
    loss_aversion_output: Optional[LossAversionOutput] = Field(
        default=None
    )
    
    # Additional mechanism spaces would follow same pattern...
    
    def get_completed_atoms(self) -> List[str]:
        """Get list of completed atom types."""
        completed = []
        for field_name in [
            'regulatory_focus', 'construal_level', 'temporal_framing',
            'social_proof', 'scarcity', 'loss_aversion'
        ]:
            space = getattr(self, field_name)
            if space and space.is_complete():
                completed.append(field_name)
        return completed
    
    def get_all_preliminary_signals(self) -> List[PreliminarySignal]:
        """Collect all preliminary signals from all atoms."""
        signals = []
        for field_name in [
            'regulatory_focus', 'construal_level', 'temporal_framing',
            'social_proof', 'scarcity', 'loss_aversion'
        ]:
            space = getattr(self, field_name)
            if space:
                signals.extend(space.preliminary_signals)
        return signals
```

---

## Synthesis Workspace Models

### Zone 3: Synthesis Workspace

```python
"""
ADAM Enhancement #02: Zone 3 - Synthesis Workspace Models
Workspace for aggregating atom outputs and producing recommendations.
"""


class SynthesisStatus(str, Enum):
    """Synthesis execution status."""
    WAITING_FOR_ATOMS = "waiting_for_atoms"
    AGGREGATING = "aggregating"
    RESOLVING_CONFLICTS = "resolving_conflicts"
    SYNTHESIZING = "synthesizing"
    COMPLETE = "complete"
    ERROR = "error"
    TIMEOUT = "timeout"


class AtomAggregation(BaseModel):
    """Aggregated view of a single atom's output."""
    
    atom_type: AtomType = Field(
        ...,
        description="Which atom"
    )
    
    status: AtomStatus = Field(
        ...,
        description="Atom completion status"
    )
    
    determination: Optional[str] = Field(
        default=None,
        description="Atom's primary determination"
    )
    
    confidence: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0
    )
    
    mechanism_recommendation: Optional[str] = Field(
        default=None
    )
    
    requires_attention: bool = Field(
        default=False
    )
    
    conflicts_with: List[str] = Field(
        default_factory=list
    )
    
    key_evidence: List[str] = Field(
        default_factory=list
    )


class ConflictDetection(BaseModel):
    """Detected conflict between atoms."""
    
    conflict_id: str = Field(
        default_factory=lambda: str(uuid.uuid4())
    )
    
    atom_a: str = Field(
        ...,
        description="First conflicting atom"
    )
    
    atom_b: str = Field(
        ...,
        description="Second conflicting atom"
    )
    
    conflict_type: str = Field(
        ...,
        description="Type of conflict"
    )
    
    conflict_description: str = Field(
        ...,
        description="Description of the conflict"
    )
    
    severity: str = Field(
        default="moderate",
        description="low/moderate/high"
    )
    
    # Atom positions
    atom_a_position: str = Field(
        ...,
        description="Atom A's determination"
    )
    
    atom_b_position: str = Field(
        ...,
        description="Atom B's determination"
    )
    
    # Evidence comparison
    atom_a_evidence_strength: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0
    )
    
    atom_b_evidence_strength: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0
    )


class ConflictResolution(BaseModel):
    """Resolution of a detected conflict."""
    
    conflict_id: str = Field(
        ...,
        description="Which conflict this resolves"
    )
    
    resolution_strategy: str = Field(
        ...,
        description="Strategy used (weighted_average, prioritize, context_dependent, etc.)"
    )
    
    resolved_determination: str = Field(
        ...,
        description="The resolved determination"
    )
    
    resolution_confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0
    )
    
    reasoning: str = Field(
        ...,
        description="Why this resolution was chosen"
    )
    
    # Which atom "won" (if applicable)
    favored_atom: Optional[str] = Field(
        default=None
    )
    
    favor_reason: Optional[str] = Field(
        default=None
    )


class MechanismWeight(BaseModel):
    """Weight assigned to a mechanism in the synthesis."""
    
    mechanism_id: str = Field(
        ...,
        description="Mechanism identifier"
    )
    
    raw_weight: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Weight before normalization"
    )
    
    normalized_weight: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Weight after normalization"
    )
    
    contributing_atoms: List[str] = Field(
        default_factory=list,
        description="Atoms that contributed to this weight"
    )
    
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0
    )
    
    # Historical calibration
    historical_effectiveness: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0
    )
    
    calibration_adjustment: float = Field(
        default=0.0,
        ge=-0.5,
        le=0.5,
        description="Adjustment based on historical data"
    )


class SynthesizedRecommendation(BaseModel):
    """Final synthesized recommendation."""
    
    # Primary recommendation
    primary_mechanism: str = Field(
        ...,
        description="Recommended primary mechanism"
    )
    
    primary_mechanism_weight: float = Field(
        ...,
        ge=0.0,
        le=1.0
    )
    
    # Secondary mechanisms
    secondary_mechanisms: List[Tuple[str, float]] = Field(
        default_factory=list,
        description="Secondary mechanisms with weights"
    )
    
    # Avoid list
    mechanisms_to_avoid: List[str] = Field(
        default_factory=list,
        description="Mechanisms to avoid"
    )
    
    avoid_reasons: Dict[str, str] = Field(
        default_factory=dict,
        description="Reasons for avoiding each mechanism"
    )
    
    # Psychological profile for copy generation
    psychological_profile: Dict[str, Any] = Field(
        default_factory=dict,
        description="Profile for copy generation"
    )
    
    # Targeting parameters
    regulatory_framing: str = Field(
        default="balanced",
        description="gain/loss/balanced"
    )
    
    construal_specificity: str = Field(
        default="moderate",
        description="abstract/concrete/moderate"
    )
    
    temporal_emphasis: str = Field(
        default="present",
        description="past/present/future"
    )
    
    social_proof_type: Optional[str] = Field(
        default=None
    )
    
    urgency_level: str = Field(
        default="low",
        description="none/low/moderate/high"
    )
    
    # Overall confidence
    recommendation_confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0
    )
    
    # Attribution-ready context
    key_evidence: List[str] = Field(
        default_factory=list
    )
    
    key_uncertainties: List[str] = Field(
        default_factory=list
    )


class SynthesisWorkspace(BaseModel):
    """
    Zone 3: Complete synthesis workspace.
    Aggregates atom outputs, resolves conflicts, produces recommendation.
    """
    
    # Identification
    request_id: str = Field(
        ...,
        description="Request identifier"
    )
    
    # Status
    status: SynthesisStatus = Field(
        default=SynthesisStatus.WAITING_FOR_ATOMS
    )
    
    # Timing
    created_at: datetime = Field(
        default_factory=datetime.utcnow
    )
    
    started_at: Optional[datetime] = Field(
        default=None
    )
    
    completed_at: Optional[datetime] = Field(
        default=None
    )
    
    # Atom tracking
    atoms_expected: List[str] = Field(
        default_factory=list,
        description="Atom types expected"
    )
    
    atoms_received: List[str] = Field(
        default_factory=list,
        description="Atom types received"
    )
    
    atoms_pending: List[str] = Field(
        default_factory=list,
        description="Atom types still pending"
    )
    
    # Atom aggregations
    atom_aggregations: Dict[str, AtomAggregation] = Field(
        default_factory=dict,
        description="Aggregated view of each atom"
    )
    
    # Atom consistency matrix
    atom_consistency_matrix: Dict[str, Dict[str, float]] = Field(
        default_factory=dict,
        description="Pairwise consistency scores"
    )
    
    # Conflict management
    detected_conflicts: List[ConflictDetection] = Field(
        default_factory=list
    )
    
    conflict_resolutions: List[ConflictResolution] = Field(
        default_factory=list
    )
    
    # Mechanism weights
    mechanism_weights: Dict[str, MechanismWeight] = Field(
        default_factory=dict
    )
    
    # Final recommendation
    recommendation: Optional[SynthesizedRecommendation] = Field(
        default=None
    )
    
    # Synthesis trace (for learning)
    synthesis_reasoning: List[str] = Field(
        default_factory=list,
        description="Key synthesis reasoning steps"
    )
    
    # Error handling
    error_message: Optional[str] = Field(
        default=None
    )
    
    # Performance
    latency_ms: Optional[float] = Field(
        default=None
    )
    
    tokens_used: Optional[int] = Field(
        default=None
    )
    
    # Version
    version: int = Field(
        default=1,
        ge=1
    )
```

---

## Decision State Models

### Zone 4: Decision State

```python
"""
ADAM Enhancement #02: Zone 4 - Decision State Models
Final decision state and serving details.
"""


class DecisionTier(str, Enum):
    """Tier of decision made."""
    FULL_REASONING = "tier_1_full"
    ARCHETYPE_MATCH = "tier_2_archetype"
    CACHED_DECISION = "tier_3_cached"
    DEFAULT_FALLBACK = "tier_4_default"


class DecisionStatus(str, Enum):
    """Decision execution status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETE = "complete"
    FALLBACK = "fallback"
    ERROR = "error"


class SelectedAd(BaseModel):
    """Information about the selected ad."""
    
    ad_id: str = Field(
        ...,
        description="Selected ad identifier"
    )
    
    campaign_id: str = Field(
        ...,
        description="Campaign identifier"
    )
    
    advertiser_id: str = Field(
        ...,
        description="Advertiser identifier"
    )
    
    # Selection reasoning
    selection_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Score for this ad"
    )
    
    mechanism_match_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="How well ad matches recommended mechanism"
    )
    
    # Predicted performance
    predicted_ctr: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0
    )
    
    predicted_conversion_rate: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0
    )
    
    predicted_engagement: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0
    )
    
    # Alternatives considered
    alternatives_count: int = Field(
        default=0,
        ge=0
    )
    
    rank_among_alternatives: int = Field(
        default=1,
        ge=1
    )


class LatencyBudgetUsage(BaseModel):
    """How the latency budget was used."""
    
    total_budget_ms: int = Field(
        ...,
        ge=0,
        description="Total budget allocated"
    )
    
    total_used_ms: float = Field(
        ...,
        ge=0,
        description="Total time used"
    )
    
    # Breakdown
    context_assembly_ms: float = Field(
        default=0,
        ge=0
    )
    
    atom_reasoning_ms: float = Field(
        default=0,
        ge=0
    )
    
    synthesis_ms: float = Field(
        default=0,
        ge=0
    )
    
    decision_ms: float = Field(
        default=0,
        ge=0
    )
    
    copy_generation_ms: float = Field(
        default=0,
        ge=0
    )
    
    overhead_ms: float = Field(
        default=0,
        ge=0
    )
    
    # Budget compliance
    within_budget: bool = Field(
        default=True
    )
    
    budget_exceeded_by_ms: Optional[float] = Field(
        default=None
    )


class ServingDetails(BaseModel):
    """Details about how the ad will be served."""
    
    # Copy customization
    personalized_copy: Optional[str] = Field(
        default=None,
        description="Personalized ad copy if generated"
    )
    
    personalization_applied: bool = Field(
        default=False
    )
    
    personalization_elements: List[str] = Field(
        default_factory=list,
        description="Which elements were personalized"
    )
    
    # Creative variant
    creative_variant_id: Optional[str] = Field(
        default=None
    )
    
    # Targeting context (for impression tracking)
    mechanism_used: str = Field(
        ...,
        description="Primary mechanism applied"
    )
    
    psychological_match_confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0
    )
    
    # A/B test participation
    experiment_ids: List[str] = Field(
        default_factory=list
    )
    
    treatment_groups: Dict[str, str] = Field(
        default_factory=dict
    )


class DecisionState(BaseModel):
    """
    Zone 4: Complete decision state.
    Final decision and serving details.
    """
    
    # Identification
    request_id: str = Field(
        ...,
        description="Request identifier"
    )
    
    decision_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique decision identifier"
    )
    
    # Status
    status: DecisionStatus = Field(
        default=DecisionStatus.PENDING
    )
    
    decision_tier: Optional[DecisionTier] = Field(
        default=None,
        description="Which tier was used"
    )
    
    # Timing
    created_at: datetime = Field(
        default_factory=datetime.utcnow
    )
    
    completed_at: Optional[datetime] = Field(
        default=None
    )
    
    # Selected ad
    selected_ad: Optional[SelectedAd] = Field(
        default=None
    )
    
    # Serving details
    serving_details: Optional[ServingDetails] = Field(
        default=None
    )
    
    # Latency tracking
    latency_budget: Optional[LatencyBudgetUsage] = Field(
        default=None
    )
    
    # Fallback info (if tier > 1)
    fallback_reason: Optional[str] = Field(
        default=None,
        description="Why fallback was used"
    )
    
    fallback_from_tier: Optional[int] = Field(
        default=None,
        description="Which tier we fell back from"
    )
    
    # Synthesis summary (from Zone 3)
    primary_mechanism: Optional[str] = Field(
        default=None
    )
    
    mechanism_confidence: Optional[float] = Field(
        default=None
    )
    
    psychological_profile_summary: Dict[str, Any] = Field(
        default_factory=dict
    )
    
    # For outcome attribution
    attribution_context: Dict[str, Any] = Field(
        default_factory=dict,
        description="Context needed for outcome attribution"
    )
    
    # Error handling
    error_message: Optional[str] = Field(
        default=None
    )
    
    # Version
    version: int = Field(
        default=1,
        ge=1
    )
```


# SECTION D: PYDANTIC MODELS - INTELLIGENCE SOURCES

## Ten Intelligence Source Models

### Intelligence Source Framework

```python
"""
ADAM Enhancement #02: Zone 2 - Intelligence Source Models
Models for all 10 intelligence sources that feed into ADAM's reasoning.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple
from pydantic import BaseModel, Field
from enum import Enum
import uuid


class IntelligenceSourceType(str, Enum):
    """The 10 intelligence sources in ADAM."""
    CLAUDE_REASONING = "claude_reasoning"
    EMPIRICAL_PATTERNS = "empirical_patterns"
    NONCONSCIOUS_SIGNALS = "nonconscious_signals"
    GRAPH_EMERGENCE = "graph_emergence"
    BANDIT_POSTERIORS = "bandit_posteriors"
    META_LEARNER = "meta_learner"
    MECHANISM_TRAJECTORIES = "mechanism_trajectories"
    TEMPORAL_PATTERNS = "temporal_patterns"
    CROSS_DOMAIN_TRANSFER = "cross_domain_transfer"
    COHORT_ORGANIZATION = "cohort_organization"


class SourceStatus(str, Enum):
    """Status of an intelligence source for this request."""
    NOT_QUERIED = "not_queried"
    QUERYING = "querying"
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    TIMEOUT = "timeout"
    ERROR = "error"


class SourceContribution(BaseModel):
    """A single contribution from an intelligence source."""
    
    contribution_id: str = Field(
        default_factory=lambda: str(uuid.uuid4())
    )
    
    source: IntelligenceSourceType = Field(
        ...,
        description="Which source produced this"
    )
    
    # The contribution
    contribution_type: str = Field(
        ...,
        description="Type of contribution (trait_estimate, mechanism_score, etc.)"
    )
    
    target: str = Field(
        ...,
        description="What this contributes to (e.g., 'openness', 'scarcity_mechanism')"
    )
    
    value: Any = Field(
        ...,
        description="The contributed value"
    )
    
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0
    )
    
    # Evidence
    evidence: List[str] = Field(
        default_factory=list
    )
    
    evidence_count: int = Field(
        default=0,
        ge=0
    )
    
    # Recency
    data_age_seconds: Optional[int] = Field(
        default=None,
        ge=0,
        description="How old the underlying data is"
    )
    
    # For fusion
    weight_in_fusion: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0
    )
    
    timestamp: datetime = Field(
        default_factory=datetime.utcnow
    )


class ClaudeReasoningSource(BaseModel):
    """Intelligence from Claude's explicit psychological reasoning."""
    
    source_type: IntelligenceSourceType = Field(
        default=IntelligenceSourceType.CLAUDE_REASONING
    )
    
    status: SourceStatus = Field(
        default=SourceStatus.NOT_QUERIED
    )
    
    # Contributions
    contributions: List[SourceContribution] = Field(
        default_factory=list
    )
    
    # Claude-specific metadata
    model_version: str = Field(
        default="claude-3-sonnet"
    )
    
    tokens_used: Optional[int] = Field(
        default=None
    )
    
    prompt_cached: bool = Field(
        default=False
    )
    
    reasoning_depth: str = Field(
        default="standard",
        description="shallow/standard/deep"
    )
    
    latency_ms: Optional[float] = Field(
        default=None
    )


class EmpiricalPatternsSource(BaseModel):
    """Intelligence from statistically discovered behavioral patterns."""
    
    source_type: IntelligenceSourceType = Field(
        default=IntelligenceSourceType.EMPIRICAL_PATTERNS
    )
    
    status: SourceStatus = Field(
        default=SourceStatus.NOT_QUERIED
    )
    
    contributions: List[SourceContribution] = Field(
        default_factory=list
    )
    
    # Pattern metadata
    patterns_matched: int = Field(
        default=0,
        ge=0
    )
    
    strongest_pattern: Optional[str] = Field(
        default=None
    )
    
    pattern_confidence: Optional[float] = Field(
        default=None
    )
    
    # Model metadata
    model_id: Optional[str] = Field(
        default=None
    )
    
    model_last_trained: Optional[datetime] = Field(
        default=None
    )
    
    training_samples: Optional[int] = Field(
        default=None
    )


class NonconsciousSignalsSource(BaseModel):
    """Intelligence from supraliminal behavioral data."""
    
    source_type: IntelligenceSourceType = Field(
        default=IntelligenceSourceType.NONCONSCIOUS_SIGNALS
    )
    
    status: SourceStatus = Field(
        default=SourceStatus.NOT_QUERIED
    )
    
    contributions: List[SourceContribution] = Field(
        default_factory=list
    )
    
    # Signal types captured
    signals_captured: Dict[str, bool] = Field(
        default_factory=lambda: {
            "click_pattern": False,
            "scroll_behavior": False,
            "dwell_time": False,
            "hover_patterns": False,
            "reading_speed": False,
            "interaction_sequence": False,
            "temporal_rhythm": False,
            "attention_flow": False
        }
    )
    
    # Signal quality
    signal_strength: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0
    )
    
    noise_ratio: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0
    )
    
    # Derived states
    inferred_arousal: Optional[str] = Field(
        default=None
    )
    
    inferred_attention: Optional[str] = Field(
        default=None
    )
    
    inferred_cognitive_load: Optional[str] = Field(
        default=None
    )


class GraphEmergenceSource(BaseModel):
    """Intelligence from graph-derived relational insights."""
    
    source_type: IntelligenceSourceType = Field(
        default=IntelligenceSourceType.GRAPH_EMERGENCE
    )
    
    status: SourceStatus = Field(
        default=SourceStatus.NOT_QUERIED
    )
    
    contributions: List[SourceContribution] = Field(
        default_factory=list
    )
    
    # Graph query metadata
    nodes_traversed: int = Field(
        default=0,
        ge=0
    )
    
    relationships_analyzed: int = Field(
        default=0,
        ge=0
    )
    
    query_latency_ms: Optional[float] = Field(
        default=None
    )
    
    # Emergent patterns
    emergent_patterns: List[str] = Field(
        default_factory=list
    )
    
    community_insights: List[str] = Field(
        default_factory=list
    )
    
    temporal_patterns: List[str] = Field(
        default_factory=list
    )


class BanditPosteriorsSource(BaseModel):
    """Intelligence from Thompson sampling learned effectiveness."""
    
    source_type: IntelligenceSourceType = Field(
        default=IntelligenceSourceType.BANDIT_POSTERIORS
    )
    
    status: SourceStatus = Field(
        default=SourceStatus.NOT_QUERIED
    )
    
    contributions: List[SourceContribution] = Field(
        default_factory=list
    )
    
    # Posterior distributions
    posteriors: Dict[str, Tuple[float, float]] = Field(
        default_factory=dict,
        description="Mechanism -> (alpha, beta) posteriors"
    )
    
    # Sampling info
    samples_drawn: int = Field(
        default=0,
        ge=0
    )
    
    exploration_bonus: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0
    )
    
    # Recommended action
    recommended_mechanism: Optional[str] = Field(
        default=None
    )
    
    recommendation_confidence: Optional[float] = Field(
        default=None
    )


class MetaLearnerSource(BaseModel):
    """Intelligence from the meta-learner routing system."""
    
    source_type: IntelligenceSourceType = Field(
        default=IntelligenceSourceType.META_LEARNER
    )
    
    status: SourceStatus = Field(
        default=SourceStatus.NOT_QUERIED
    )
    
    contributions: List[SourceContribution] = Field(
        default_factory=list
    )
    
    # Routing decisions
    source_weights: Dict[str, float] = Field(
        default_factory=dict,
        description="Weight assigned to each source"
    )
    
    routing_strategy: str = Field(
        default="balanced",
        description="Strategy used for this request"
    )
    
    # Performance predictions
    predicted_accuracy: Optional[float] = Field(
        default=None
    )
    
    predicted_latency_ms: Optional[float] = Field(
        default=None
    )
    
    # Learning signals
    should_update_routing: bool = Field(
        default=False
    )


class MechanismTrajectoriesSource(BaseModel):
    """Intelligence from historical mechanism effectiveness."""
    
    source_type: IntelligenceSourceType = Field(
        default=IntelligenceSourceType.MECHANISM_TRAJECTORIES
    )
    
    status: SourceStatus = Field(
        default=SourceStatus.NOT_QUERIED
    )
    
    contributions: List[SourceContribution] = Field(
        default_factory=list
    )
    
    # Trajectory data
    mechanism_trends: Dict[str, str] = Field(
        default_factory=dict,
        description="Mechanism -> trend (improving/stable/declining)"
    )
    
    mechanism_velocities: Dict[str, float] = Field(
        default_factory=dict,
        description="Rate of change in effectiveness"
    )
    
    # Context dependencies
    context_modifiers: Dict[str, Dict[str, float]] = Field(
        default_factory=dict,
        description="Mechanism -> context -> modifier"
    )
    
    # Time-based patterns
    time_of_day_effects: Dict[str, Dict[int, float]] = Field(
        default_factory=dict,
        description="Mechanism -> hour -> effectiveness modifier"
    )


class TemporalPatternsSource(BaseModel):
    """Intelligence from time-based behavioral patterns."""
    
    source_type: IntelligenceSourceType = Field(
        default=IntelligenceSourceType.TEMPORAL_PATTERNS
    )
    
    status: SourceStatus = Field(
        default=SourceStatus.NOT_QUERIED
    )
    
    contributions: List[SourceContribution] = Field(
        default_factory=list
    )
    
    # Temporal context
    user_timezone: Optional[str] = Field(
        default=None
    )
    
    local_hour: Optional[int] = Field(
        default=None
    )
    
    day_type: str = Field(
        default="weekday",
        description="weekday/weekend/holiday"
    )
    
    # Patterns detected
    activity_pattern: Optional[str] = Field(
        default=None,
        description="morning_person/night_owl/midday_active/consistent"
    )
    
    session_pattern: Optional[str] = Field(
        default=None,
        description="binge/regular/sporadic"
    )
    
    # Temporal predictions
    expected_session_length: Optional[int] = Field(
        default=None,
        description="Expected remaining session length in seconds"
    )
    
    optimal_ad_timing: Optional[str] = Field(
        default=None,
        description="now/wait/soon"
    )


class CrossDomainTransferSource(BaseModel):
    """Intelligence from knowledge transfer across domains."""
    
    source_type: IntelligenceSourceType = Field(
        default=IntelligenceSourceType.CROSS_DOMAIN_TRANSFER
    )
    
    status: SourceStatus = Field(
        default=SourceStatus.NOT_QUERIED
    )
    
    contributions: List[SourceContribution] = Field(
        default_factory=list
    )
    
    # Transfer domains
    source_domains: List[str] = Field(
        default_factory=list,
        description="Domains knowledge is transferred from"
    )
    
    target_domain: Optional[str] = Field(
        default=None,
        description="Current domain"
    )
    
    # Transfer confidence
    transfer_validity: Dict[str, float] = Field(
        default_factory=dict,
        description="Domain -> transfer validity score"
    )
    
    # Transferred insights
    transferred_traits: Dict[str, float] = Field(
        default_factory=dict,
        description="Trait -> transferred value"
    )
    
    transferred_mechanism_scores: Dict[str, float] = Field(
        default_factory=dict,
        description="Mechanism -> transferred effectiveness"
    )


class CohortOrganizationSource(BaseModel):
    """Intelligence from cohort-level psychological patterns."""
    
    source_type: IntelligenceSourceType = Field(
        default=IntelligenceSourceType.COHORT_ORGANIZATION
    )
    
    status: SourceStatus = Field(
        default=SourceStatus.NOT_QUERIED
    )
    
    contributions: List[SourceContribution] = Field(
        default_factory=list
    )
    
    # Cohort memberships
    cohort_ids: List[str] = Field(
        default_factory=list
    )
    
    primary_cohort: Optional[str] = Field(
        default=None
    )
    
    cohort_membership_confidence: Dict[str, float] = Field(
        default_factory=dict
    )
    
    # Cohort characteristics
    cohort_profiles: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict,
        description="Cohort -> profile attributes"
    )
    
    # Cohort-based recommendations
    cohort_mechanism_preferences: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="Cohort -> preferred mechanisms"
    )


class IntelligenceSourcesSnapshot(BaseModel):
    """
    Complete snapshot of all 10 intelligence sources for a request.
    This is stored in Zone 2 and used for fusion.
    """
    
    request_id: str = Field(
        ...,
        description="Request identifier"
    )
    
    snapshot_timestamp: datetime = Field(
        default_factory=datetime.utcnow
    )
    
    # All 10 sources
    claude_reasoning: ClaudeReasoningSource = Field(
        default_factory=ClaudeReasoningSource
    )
    
    empirical_patterns: EmpiricalPatternsSource = Field(
        default_factory=EmpiricalPatternsSource
    )
    
    nonconscious_signals: NonconsciousSignalsSource = Field(
        default_factory=NonconsciousSignalsSource
    )
    
    graph_emergence: GraphEmergenceSource = Field(
        default_factory=GraphEmergenceSource
    )
    
    bandit_posteriors: BanditPosteriorsSource = Field(
        default_factory=BanditPosteriorsSource
    )
    
    meta_learner: MetaLearnerSource = Field(
        default_factory=MetaLearnerSource
    )
    
    mechanism_trajectories: MechanismTrajectoriesSource = Field(
        default_factory=MechanismTrajectoriesSource
    )
    
    temporal_patterns: TemporalPatternsSource = Field(
        default_factory=TemporalPatternsSource
    )
    
    cross_domain_transfer: CrossDomainTransferSource = Field(
        default_factory=CrossDomainTransferSource
    )
    
    cohort_organization: CohortOrganizationSource = Field(
        default_factory=CohortOrganizationSource
    )
    
    # Aggregated metrics
    sources_queried: int = Field(
        default=0,
        ge=0,
        le=10
    )
    
    sources_available: int = Field(
        default=0,
        ge=0,
        le=10
    )
    
    total_contributions: int = Field(
        default=0,
        ge=0
    )
    
    # Fusion readiness
    fusion_ready: bool = Field(
        default=False
    )
    
    def get_available_sources(self) -> List[IntelligenceSourceType]:
        """Get list of sources with available data."""
        available = []
        for source_type in IntelligenceSourceType:
            source = getattr(self, source_type.value)
            if source.status == SourceStatus.AVAILABLE:
                available.append(source_type)
        return available
    
    def get_all_contributions(self) -> List[SourceContribution]:
        """Collect all contributions from all sources."""
        contributions = []
        for source_type in IntelligenceSourceType:
            source = getattr(self, source_type.value)
            contributions.extend(source.contributions)
        return contributions
```

---

## Source Contribution Tracking

```python
"""
ADAM Enhancement #02: Source Contribution Tracking
Track how each source contributes to final decisions.
"""


class ContributionAggregation(BaseModel):
    """Aggregated contribution from a source to a target."""
    
    target: str = Field(
        ...,
        description="What is being contributed to"
    )
    
    source_contributions: Dict[IntelligenceSourceType, SourceContribution] = Field(
        default_factory=dict
    )
    
    # Fusion result
    fused_value: Any = Field(
        ...,
        description="Value after fusion"
    )
    
    fused_confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0
    )
    
    # Source weights in fusion
    source_weights: Dict[IntelligenceSourceType, float] = Field(
        default_factory=dict
    )
    
    # Dominant source
    dominant_source: Optional[IntelligenceSourceType] = Field(
        default=None
    )
    
    dominant_weight: Optional[float] = Field(
        default=None
    )
    
    # Agreement metrics
    source_agreement: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="How much sources agreed"
    )
    
    conflicts_detected: int = Field(
        default=0,
        ge=0
    )


class SourceContributionTracker(BaseModel):
    """
    Tracks all source contributions for attribution and learning.
    This is crucial for the Gradient Bridge.
    """
    
    request_id: str = Field(
        ...,
        description="Request identifier"
    )
    
    # Contribution aggregations by target
    trait_contributions: Dict[str, ContributionAggregation] = Field(
        default_factory=dict,
        description="Contributions to trait estimates"
    )
    
    mechanism_contributions: Dict[str, ContributionAggregation] = Field(
        default_factory=dict,
        description="Contributions to mechanism scores"
    )
    
    state_contributions: Dict[str, ContributionAggregation] = Field(
        default_factory=dict,
        description="Contributions to state estimates"
    )
    
    # Overall source performance
    source_availability: Dict[IntelligenceSourceType, bool] = Field(
        default_factory=dict
    )
    
    source_latencies: Dict[IntelligenceSourceType, float] = Field(
        default_factory=dict
    )
    
    source_contribution_counts: Dict[IntelligenceSourceType, int] = Field(
        default_factory=dict
    )
    
    # Entropy and balance
    contribution_entropy: float = Field(
        default=0.0,
        ge=0.0,
        description="Shannon entropy of source contributions"
    )
    
    is_balanced: bool = Field(
        default=True,
        description="Whether contributions are well-balanced"
    )
    
    # For attribution
    decision_chain: List[str] = Field(
        default_factory=list,
        description="Chain of decisions influenced by sources"
    )
```

---

# SECTION E: PYDANTIC MODELS - LEARNING & SIGNALS

## Learning Signal Models

### Zone 5: Learning Signals

```python
"""
ADAM Enhancement #02: Zone 5 - Learning Signal Models
Models for cross-component learning signals.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List, Union
from pydantic import BaseModel, Field
from enum import Enum
import uuid


class LearningSignalType(str, Enum):
    """Types of learning signals."""
    # Outcome signals
    CONVERSION_OUTCOME = "conversion_outcome"
    ENGAGEMENT_OUTCOME = "engagement_outcome"
    REVENUE_OUTCOME = "revenue_outcome"
    RETENTION_OUTCOME = "retention_outcome"
    
    # Behavioral signals
    CLICK_THROUGH = "click_through"
    DWELL_TIME = "dwell_time"
    SCROLL_DEPTH = "scroll_depth"
    INTERACTION_SEQUENCE = "interaction_sequence"
    
    # Psychological signals
    PERSONALITY_VALIDATION = "personality_validation"
    STATE_TRANSITION = "state_transition"
    CONSTRUCT_ACTIVATION = "construct_activation"
    MECHANISM_EFFECTIVENESS = "mechanism_effectiveness"
    
    # System signals
    MODEL_PREDICTION = "model_prediction"
    CONFIDENCE_CALIBRATION = "confidence_calibration"
    LATENCY_MEASUREMENT = "latency_measurement"
    ERROR_OCCURRENCE = "error_occurrence"


class SignalPriority(str, Enum):
    """Priority for processing signals."""
    CRITICAL = "critical"  # Process immediately
    HIGH = "high"          # Process within seconds
    NORMAL = "normal"      # Process within minutes
    LOW = "low"            # Batch processing OK


class OutcomeType(str, Enum):
    """Types of outcomes for attribution."""
    CONVERSION = "conversion"
    CLICK = "click"
    ENGAGEMENT = "engagement"
    SKIP = "skip"
    IGNORE = "ignore"
    NEGATIVE = "negative"  # Ad blocked, complained, etc.


class LearningSignal(BaseModel):
    """
    A learning signal emitted by any component.
    Consumed by Gradient Bridge and Meta-Learner.
    """
    
    signal_id: str = Field(
        default_factory=lambda: str(uuid.uuid4())
    )
    
    signal_type: LearningSignalType = Field(
        ...,
        description="Type of signal"
    )
    
    priority: SignalPriority = Field(
        default=SignalPriority.NORMAL
    )
    
    # Source identification
    source_component: str = Field(
        ...,
        description="Component that emitted this signal"
    )
    
    request_id: str = Field(
        ...,
        description="Request this relates to"
    )
    
    decision_id: Optional[str] = Field(
        default=None,
        description="Decision this relates to"
    )
    
    user_id: str = Field(
        ...,
        description="User this relates to"
    )
    
    # Signal content
    signal_value: Any = Field(
        ...,
        description="The signal value"
    )
    
    signal_confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0
    )
    
    # Context
    context: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional context"
    )
    
    # Timing
    timestamp: datetime = Field(
        default_factory=datetime.utcnow
    )
    
    event_timestamp: Optional[datetime] = Field(
        default=None,
        description="When the underlying event occurred"
    )
    
    delay_seconds: Optional[float] = Field(
        default=None,
        ge=0,
        description="Delay between decision and signal"
    )
    
    # Attribution hints
    attributed_to: List[str] = Field(
        default_factory=list,
        description="Components/sources to attribute to"
    )
    
    attribution_weights: Dict[str, float] = Field(
        default_factory=dict,
        description="Attribution weight per component"
    )


class OutcomeSignal(BaseModel):
    """Specialized signal for conversion/engagement outcomes."""
    
    signal_id: str = Field(
        default_factory=lambda: str(uuid.uuid4())
    )
    
    # Identification
    request_id: str = Field(
        ...,
        description="Original request"
    )
    
    decision_id: str = Field(
        ...,
        description="Decision that led to this"
    )
    
    user_id: str = Field(
        ...,
        description="User"
    )
    
    ad_id: str = Field(
        ...,
        description="Ad that was served"
    )
    
    # Outcome
    outcome_type: OutcomeType = Field(
        ...,
        description="What happened"
    )
    
    outcome_value: Optional[float] = Field(
        default=None,
        description="Numeric value (e.g., revenue)"
    )
    
    outcome_timestamp: datetime = Field(
        default_factory=datetime.utcnow
    )
    
    # Delay tracking
    decision_timestamp: datetime = Field(
        ...,
        description="When the decision was made"
    )
    
    delay_seconds: float = Field(
        ...,
        ge=0,
        description="Seconds between decision and outcome"
    )
    
    # Context at decision time (snapshot)
    mechanism_used: str = Field(
        ...,
        description="Mechanism applied"
    )
    
    mechanism_confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0
    )
    
    psychological_profile: Dict[str, Any] = Field(
        default_factory=dict,
        description="Profile at decision time"
    )
    
    decision_tier: str = Field(
        ...,
        description="Which tier was used"
    )
    
    # Intelligence source contributions
    source_contributions: Dict[str, float] = Field(
        default_factory=dict,
        description="Which sources contributed"
    )
    
    # For counterfactual analysis
    alternative_mechanisms: List[str] = Field(
        default_factory=list,
        description="Other mechanisms considered"
    )
    
    predicted_outcome: Optional[float] = Field(
        default=None,
        description="What we predicted"
    )


class MechanismEffectivenessSignal(BaseModel):
    """Signal specifically for mechanism effectiveness learning."""
    
    signal_id: str = Field(
        default_factory=lambda: str(uuid.uuid4())
    )
    
    # Identification
    user_id: str = Field(...),
    mechanism_id: str = Field(...),
    request_id: str = Field(...),
    
    # Outcome
    was_effective: bool = Field(
        ...,
        description="Whether mechanism worked"
    )
    
    effectiveness_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Degree of effectiveness"
    )
    
    # Context
    user_state_at_decision: Dict[str, Any] = Field(
        default_factory=dict
    )
    
    user_traits_at_decision: Dict[str, float] = Field(
        default_factory=dict
    )
    
    content_context: Dict[str, Any] = Field(
        default_factory=dict
    )
    
    temporal_context: Dict[str, Any] = Field(
        default_factory=dict
    )
    
    # For Bayesian updating
    prior_alpha: float = Field(
        ...,
        ge=0.1,
        description="Prior alpha before this observation"
    )
    
    prior_beta: float = Field(
        ...,
        ge=0.1,
        description="Prior beta before this observation"
    )
    
    # Timestamp
    timestamp: datetime = Field(
        default_factory=datetime.utcnow
    )


class ConfidenceCalibrationSignal(BaseModel):
    """Signal for calibrating prediction confidence."""
    
    signal_id: str = Field(
        default_factory=lambda: str(uuid.uuid4())
    )
    
    # What was predicted
    prediction_type: str = Field(
        ...,
        description="Type of prediction (trait, mechanism, outcome)"
    )
    
    prediction_target: str = Field(
        ...,
        description="What was being predicted"
    )
    
    predicted_value: Any = Field(
        ...,
        description="Predicted value"
    )
    
    predicted_confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0
    )
    
    # What actually happened
    actual_value: Any = Field(
        ...,
        description="Actual value"
    )
    
    was_correct: bool = Field(
        ...,
        description="Whether prediction was correct"
    )
    
    error_magnitude: Optional[float] = Field(
        default=None,
        description="How far off the prediction was"
    )
    
    # Source tracking
    source_component: str = Field(
        ...,
        description="Component that made prediction"
    )
    
    contributing_sources: List[str] = Field(
        default_factory=list
    )
    
    # Timing
    prediction_timestamp: datetime = Field(...)
    
    verification_timestamp: datetime = Field(
        default_factory=datetime.utcnow
    )


class LearningSignalBatch(BaseModel):
    """Batch of learning signals for efficient processing."""
    
    batch_id: str = Field(
        default_factory=lambda: str(uuid.uuid4())
    )
    
    signals: List[LearningSignal] = Field(
        default_factory=list
    )
    
    outcome_signals: List[OutcomeSignal] = Field(
        default_factory=list
    )
    
    mechanism_signals: List[MechanismEffectivenessSignal] = Field(
        default_factory=list
    )
    
    calibration_signals: List[ConfidenceCalibrationSignal] = Field(
        default_factory=list
    )
    
    # Batch metadata
    batch_timestamp: datetime = Field(
        default_factory=datetime.utcnow
    )
    
    signal_count: int = Field(
        default=0,
        ge=0
    )
    
    time_range_start: Optional[datetime] = Field(
        default=None
    )
    
    time_range_end: Optional[datetime] = Field(
        default=None
    )
```

---

## Attribution Context Models

```python
"""
ADAM Enhancement #02: Attribution Context Models
Complete context for outcome attribution.
"""


class AttributionContext(BaseModel):
    """
    Complete context needed for outcome attribution.
    Snapshot of all zones at decision time.
    """
    
    # Identification
    attribution_id: str = Field(
        default_factory=lambda: str(uuid.uuid4())
    )
    
    request_id: str = Field(...)
    decision_id: str = Field(...)
    user_id: str = Field(...)
    
    # Zone snapshots
    zone1_snapshot: Dict[str, Any] = Field(
        default_factory=dict,
        description="Request context at decision time"
    )
    
    zone2_summary: Dict[str, Any] = Field(
        default_factory=dict,
        description="Atom outputs summary"
    )
    
    zone3_summary: Dict[str, Any] = Field(
        default_factory=dict,
        description="Synthesis output summary"
    )
    
    zone4_snapshot: Dict[str, Any] = Field(
        default_factory=dict,
        description="Decision details"
    )
    
    # Intelligence source contributions
    source_contributions: Dict[str, SourceContribution] = Field(
        default_factory=dict
    )
    
    source_weights: Dict[str, float] = Field(
        default_factory=dict
    )
    
    # Decision details
    mechanism_used: str = Field(...)
    mechanism_confidence: float = Field(...)
    
    ad_selected: str = Field(...)
    ad_selection_score: float = Field(...)
    
    decision_tier: str = Field(...)
    
    # Psychological state
    user_traits: Dict[str, float] = Field(
        default_factory=dict
    )
    
    user_state: Dict[str, Any] = Field(
        default_factory=dict
    )
    
    state_trait_interactions: List[Dict[str, Any]] = Field(
        default_factory=list
    )
    
    # Timing
    decision_timestamp: datetime = Field(...)
    
    context_age_ms: float = Field(
        default=0,
        ge=0,
        description="How old the context was at decision time"
    )
    
    # For gradient routing
    components_to_update: List[str] = Field(
        default_factory=list,
        description="Components that should receive gradient"
    )
    
    gradient_weights: Dict[str, float] = Field(
        default_factory=dict,
        description="Weight for each component's gradient"
    )


class AttributionResult(BaseModel):
    """Result of attribution analysis."""
    
    attribution_id: str = Field(...)
    
    # Outcome
    outcome_type: OutcomeType = Field(...)
    outcome_value: Optional[float] = Field(default=None)
    
    # Attribution scores
    component_attributions: Dict[str, float] = Field(
        default_factory=dict,
        description="Component -> attribution score"
    )
    
    source_attributions: Dict[str, float] = Field(
        default_factory=dict,
        description="Source -> attribution score"
    )
    
    mechanism_attribution: float = Field(
        ...,
        ge=0.0,
        le=1.0
    )
    
    # Confidence in attribution
    attribution_confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0
    )
    
    # Method used
    attribution_method: str = Field(
        default="shapley",
        description="Method used for attribution"
    )
    
    # Counterfactual analysis
    counterfactual_estimates: Dict[str, float] = Field(
        default_factory=dict,
        description="What would have happened with other choices"
    )
    
    # Learning actions taken
    gradients_emitted: List[str] = Field(
        default_factory=list
    )
    
    posteriors_updated: List[str] = Field(
        default_factory=list
    )
    
    # Timestamp
    attribution_timestamp: datetime = Field(
        default_factory=datetime.utcnow
    )
```


# SECTION F: REDIS IMPLEMENTATION

## Multi-Zone Redis Architecture

### Redis Key Schema

```python
"""
ADAM Enhancement #02: Redis Implementation
Enterprise-grade Redis backend for Blackboard.
"""

from typing import Optional, Dict, Any, List, Type, TypeVar
from pydantic import BaseModel
from datetime import datetime, timedelta
import asyncio
import json
import hashlib
import zlib
import redis.asyncio as redis
from redis.asyncio.connection import ConnectionPool
from contextlib import asynccontextmanager
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=BaseModel)


class RedisKeySchema:
    """
    Redis key schema for all blackboard zones.
    
    Key Format: bb:{zone}:{request_id}:{component}:{entry_type}
    
    Examples:
    - bb:z1:req:abc123:context          # Zone 1 request context
    - bb:z2:atom:abc123:regulatory_focus:output  # Zone 2 atom output
    - bb:z2:atom:abc123:regulatory_focus:signals # Zone 2 preliminary signals
    - bb:z2:src:abc123:claude_reasoning  # Zone 2 intelligence source
    - bb:z3:synth:abc123:workspace       # Zone 3 synthesis workspace
    - bb:z4:dec:abc123:state             # Zone 4 decision state
    - bb:z5:learn:abc123:signals         # Zone 5 learning signals
    """
    
    # Zone prefixes
    ZONE1_PREFIX = "bb:z1:req"
    ZONE2_ATOM_PREFIX = "bb:z2:atom"
    ZONE2_SOURCE_PREFIX = "bb:z2:src"
    ZONE3_PREFIX = "bb:z3:synth"
    ZONE4_PREFIX = "bb:z4:dec"
    ZONE5_PREFIX = "bb:z5:learn"
    
    # Pub/Sub channels
    PUBSUB_ATOM_COMPLETE = "bb:events:atom:complete"
    PUBSUB_SYNTHESIS_COMPLETE = "bb:events:synthesis:complete"
    PUBSUB_DECISION_COMPLETE = "bb:events:decision:complete"
    PUBSUB_LEARNING_SIGNAL = "bb:events:learning:signal"
    PUBSUB_STATE_UPDATE = "bb:events:state:update"
    
    @classmethod
    def zone1_key(cls, request_id: str) -> str:
        """Key for Zone 1 request context."""
        return f"{cls.ZONE1_PREFIX}:{request_id}:context"
    
    @classmethod
    def zone2_atom_key(cls, request_id: str, atom_type: str, entry_type: str = "space") -> str:
        """Key for Zone 2 atom reasoning space."""
        return f"{cls.ZONE2_ATOM_PREFIX}:{request_id}:{atom_type}:{entry_type}"
    
    @classmethod
    def zone2_atom_signals_key(cls, request_id: str, atom_type: str) -> str:
        """Key for Zone 2 atom preliminary signals."""
        return f"{cls.ZONE2_ATOM_PREFIX}:{request_id}:{atom_type}:signals"
    
    @classmethod
    def zone2_source_key(cls, request_id: str, source_type: str) -> str:
        """Key for Zone 2 intelligence source."""
        return f"{cls.ZONE2_SOURCE_PREFIX}:{request_id}:{source_type}"
    
    @classmethod
    def zone2_sources_snapshot_key(cls, request_id: str) -> str:
        """Key for Zone 2 complete sources snapshot."""
        return f"{cls.ZONE2_SOURCE_PREFIX}:{request_id}:snapshot"
    
    @classmethod
    def zone3_key(cls, request_id: str) -> str:
        """Key for Zone 3 synthesis workspace."""
        return f"{cls.ZONE3_PREFIX}:{request_id}:workspace"
    
    @classmethod
    def zone4_key(cls, request_id: str) -> str:
        """Key for Zone 4 decision state."""
        return f"{cls.ZONE4_PREFIX}:{request_id}:state"
    
    @classmethod
    def zone5_signals_key(cls, request_id: str) -> str:
        """Key for Zone 5 learning signals list."""
        return f"{cls.ZONE5_PREFIX}:{request_id}:signals"
    
    @classmethod
    def zone5_outcome_key(cls, request_id: str) -> str:
        """Key for Zone 5 outcome signals."""
        return f"{cls.ZONE5_PREFIX}:{request_id}:outcomes"
    
    @classmethod
    def zone5_attribution_key(cls, request_id: str) -> str:
        """Key for Zone 5 attribution context."""
        return f"{cls.ZONE5_PREFIX}:{request_id}:attribution"
    
    @classmethod
    def request_index_key(cls, request_id: str) -> str:
        """Key for index of all keys for a request (for cleanup)."""
        return f"bb:index:{request_id}"
    
    @classmethod
    def get_zone_from_key(cls, key: str) -> Optional[str]:
        """Extract zone from a key."""
        if key.startswith(cls.ZONE1_PREFIX):
            return "zone1"
        elif key.startswith(cls.ZONE2_ATOM_PREFIX) or key.startswith(cls.ZONE2_SOURCE_PREFIX):
            return "zone2"
        elif key.startswith(cls.ZONE3_PREFIX):
            return "zone3"
        elif key.startswith(cls.ZONE4_PREFIX):
            return "zone4"
        elif key.startswith(cls.ZONE5_PREFIX):
            return "zone5"
        return None
```

---

## Connection Pool Management

```python
"""
ADAM Enhancement #02: Redis Connection Pool
High-performance connection pooling with health monitoring.
"""


class RedisPoolManager:
    """
    Manages Redis connection pools with health monitoring.
    """
    
    def __init__(self, config: BlackboardConfig):
        self.config = config
        self._pools: Dict[str, ConnectionPool] = {}
        self._clients: Dict[str, redis.Redis] = {}
        self._health_status: Dict[str, bool] = {}
        self._lock = asyncio.Lock()
        
    async def initialize(self):
        """Initialize connection pools."""
        # Main pool for read/write operations
        self._pools["main"] = ConnectionPool.from_url(
            self.config.redis_url,
            max_connections=self.config.redis_pool_size,
            decode_responses=False,  # Handle bytes for compression
            socket_timeout=self.config.redis_timeout_seconds,
            socket_connect_timeout=self.config.redis_timeout_seconds,
            retry_on_timeout=True,
            health_check_interval=30
        )
        
        # Pub/sub pool (separate to avoid blocking)
        self._pools["pubsub"] = ConnectionPool.from_url(
            self.config.redis_url,
            max_connections=10,
            decode_responses=True,
            socket_timeout=self.config.redis_timeout_seconds
        )
        
        # Create clients
        self._clients["main"] = redis.Redis(connection_pool=self._pools["main"])
        self._clients["pubsub"] = redis.Redis(connection_pool=self._pools["pubsub"])
        
        # Verify connections
        await self._verify_connections()
        
        logger.info(f"Redis pools initialized with {self.config.redis_pool_size} connections")
    
    async def _verify_connections(self):
        """Verify all pools are working."""
        for name, client in self._clients.items():
            try:
                await client.ping()
                self._health_status[name] = True
                logger.info(f"Redis pool '{name}' verified")
            except Exception as e:
                self._health_status[name] = False
                logger.error(f"Redis pool '{name}' failed: {e}")
                raise
    
    def get_client(self, pool_name: str = "main") -> redis.Redis:
        """Get a Redis client from the specified pool."""
        if pool_name not in self._clients:
            raise ValueError(f"Unknown pool: {pool_name}")
        return self._clients[pool_name]
    
    @property
    def main_client(self) -> redis.Redis:
        """Get the main Redis client."""
        return self._clients["main"]
    
    @property
    def pubsub_client(self) -> redis.Redis:
        """Get the pub/sub Redis client."""
        return self._clients["pubsub"]
    
    async def health_check(self) -> Dict[str, bool]:
        """Check health of all pools."""
        for name, client in self._clients.items():
            try:
                await client.ping()
                self._health_status[name] = True
            except Exception:
                self._health_status[name] = False
        return self._health_status.copy()
    
    async def get_pool_stats(self) -> Dict[str, Any]:
        """Get statistics for all pools."""
        stats = {}
        for name, pool in self._pools.items():
            stats[name] = {
                "max_connections": pool.max_connections,
                "created_connections": pool._created_connections if hasattr(pool, '_created_connections') else 'N/A',
                "available_connections": len(pool._available_connections) if hasattr(pool, '_available_connections') else 'N/A'
            }
        return stats
    
    async def close(self):
        """Close all connections and pools."""
        for client in self._clients.values():
            await client.close()
        for pool in self._pools.values():
            await pool.disconnect()
        logger.info("Redis pools closed")
```

---

## Serialization Strategy

```python
"""
ADAM Enhancement #02: Serialization Strategy
Efficient serialization with optional compression.
"""


class BlackboardSerializer:
    """
    Handles serialization and deserialization of blackboard entries.
    Supports compression for large entries.
    """
    
    COMPRESSION_HEADER = b"ZLIB:"
    
    def __init__(self, config: BlackboardZoneConfig):
        self.config = config
    
    def serialize(self, model: BaseModel) -> bytes:
        """
        Serialize a Pydantic model to bytes.
        Optionally compresses if above threshold.
        """
        # Serialize to JSON
        json_str = model.json()
        json_bytes = json_str.encode('utf-8')
        
        # Check if compression should be applied
        if (self.config.compression_enabled and 
            len(json_bytes) > self.config.compression_threshold_bytes):
            compressed = zlib.compress(json_bytes, level=6)
            # Only use compression if it actually saves space
            if len(compressed) < len(json_bytes) * 0.9:
                return self.COMPRESSION_HEADER + compressed
        
        return json_bytes
    
    def deserialize(self, data: bytes, model_class: Type[T]) -> T:
        """
        Deserialize bytes to a Pydantic model.
        Handles compressed and uncompressed data.
        """
        # Check for compression header
        if data.startswith(self.COMPRESSION_HEADER):
            compressed_data = data[len(self.COMPRESSION_HEADER):]
            json_bytes = zlib.decompress(compressed_data)
        else:
            json_bytes = data
        
        # Parse JSON and create model
        json_str = json_bytes.decode('utf-8')
        return model_class.parse_raw(json_str)
    
    def calculate_checksum(self, data: bytes) -> str:
        """Calculate MD5 checksum for data integrity."""
        return hashlib.md5(data).hexdigest()
    
    def is_compressed(self, data: bytes) -> bool:
        """Check if data is compressed."""
        return data.startswith(self.COMPRESSION_HEADER)
    
    def get_size_info(self, model: BaseModel) -> Dict[str, int]:
        """Get size information for a model."""
        json_bytes = model.json().encode('utf-8')
        
        result = {
            "json_size": len(json_bytes),
            "compressed_size": None,
            "compression_ratio": None
        }
        
        if self.config.compression_enabled:
            compressed = zlib.compress(json_bytes, level=6)
            result["compressed_size"] = len(compressed)
            result["compression_ratio"] = len(compressed) / len(json_bytes)
        
        return result


class SerializerFactory:
    """Factory for creating zone-specific serializers."""
    
    def __init__(self, config: BlackboardConfig):
        self.config = config
        self._serializers: Dict[BlackboardZone, BlackboardSerializer] = {}
        
        # Create serializers for each zone
        for zone, zone_config in config.zones.items():
            self._serializers[zone] = BlackboardSerializer(zone_config)
    
    def get_serializer(self, zone: BlackboardZone) -> BlackboardSerializer:
        """Get serializer for a specific zone."""
        return self._serializers[zone]
```

---

## TTL & Eviction Policies

```python
"""
ADAM Enhancement #02: TTL Management
Time-to-live management with automatic cleanup.
"""


class TTLManager:
    """
    Manages TTL for blackboard entries.
    Handles automatic cleanup and TTL extension.
    """
    
    # Default TTLs by zone (in seconds)
    DEFAULT_TTLS = {
        BlackboardZone.REQUEST_CONTEXT: 600,        # 10 minutes
        BlackboardZone.ATOM_REASONING: 1800,        # 30 minutes
        BlackboardZone.SYNTHESIS_WORKSPACE: 3600,   # 1 hour
        BlackboardZone.DECISION_STATE: 86400,       # 24 hours
        BlackboardZone.LEARNING_SIGNALS: 259200,    # 72 hours
    }
    
    def __init__(self, config: BlackboardConfig, redis_client: redis.Redis):
        self.config = config
        self.redis = redis_client
    
    def get_ttl(self, zone: BlackboardZone, custom_ttl: Optional[int] = None) -> int:
        """Get TTL for a zone, optionally with custom override."""
        if custom_ttl is not None:
            return custom_ttl
        
        zone_config = self.config.zones.get(zone)
        if zone_config:
            return zone_config.default_ttl_seconds
        
        return self.DEFAULT_TTLS.get(zone, 3600)
    
    async def set_with_ttl(
        self, 
        key: str, 
        value: bytes, 
        zone: BlackboardZone,
        custom_ttl: Optional[int] = None
    ) -> bool:
        """Set a value with appropriate TTL."""
        ttl = self.get_ttl(zone, custom_ttl)
        return await self.redis.setex(key, ttl, value)
    
    async def extend_ttl(
        self, 
        key: str, 
        extension_seconds: int
    ) -> bool:
        """Extend the TTL of an existing key."""
        current_ttl = await self.redis.ttl(key)
        if current_ttl > 0:
            new_ttl = current_ttl + extension_seconds
            return await self.redis.expire(key, new_ttl)
        return False
    
    async def get_remaining_ttl(self, key: str) -> int:
        """Get remaining TTL for a key."""
        return await self.redis.ttl(key)
    
    async def cleanup_request(self, request_id: str):
        """
        Clean up all keys associated with a request.
        Uses the request index to find all keys.
        """
        index_key = RedisKeySchema.request_index_key(request_id)
        keys = await self.redis.smembers(index_key)
        
        if keys:
            # Delete all keys in a pipeline
            async with self.redis.pipeline(transaction=True) as pipe:
                for key in keys:
                    pipe.delete(key)
                pipe.delete(index_key)
                await pipe.execute()
            
            logger.info(f"Cleaned up {len(keys)} keys for request {request_id}")
    
    async def register_key(self, request_id: str, key: str):
        """Register a key in the request index for cleanup."""
        index_key = RedisKeySchema.request_index_key(request_id)
        await self.redis.sadd(index_key, key)
        # Set TTL on index slightly longer than max zone TTL
        await self.redis.expire(index_key, 259200 + 3600)  # 73 hours
```

---

## Pub/Sub Event Layer

```python
"""
ADAM Enhancement #02: Pub/Sub Event Layer
Redis pub/sub for real-time event coordination.
"""


class BlackboardEventType(str, Enum):
    """Types of blackboard events."""
    ATOM_STARTED = "atom.started"
    ATOM_SIGNAL = "atom.signal"
    ATOM_COMPLETE = "atom.complete"
    ATOM_ERROR = "atom.error"
    
    SYNTHESIS_STARTED = "synthesis.started"
    SYNTHESIS_COMPLETE = "synthesis.complete"
    SYNTHESIS_ERROR = "synthesis.error"
    
    DECISION_STARTED = "decision.started"
    DECISION_COMPLETE = "decision.complete"
    DECISION_ERROR = "decision.error"
    
    LEARNING_SIGNAL = "learning.signal"
    OUTCOME_RECEIVED = "outcome.received"
    
    STATE_UPDATE = "state.update"
    ZONE_UPDATE = "zone.update"


class BlackboardEvent(BaseModel):
    """Event emitted on blackboard state changes."""
    
    event_id: str = Field(
        default_factory=lambda: str(uuid.uuid4())
    )
    
    event_type: BlackboardEventType = Field(
        ...,
        description="Type of event"
    )
    
    request_id: str = Field(
        ...,
        description="Request this event relates to"
    )
    
    zone: BlackboardZone = Field(
        ...,
        description="Zone that changed"
    )
    
    component: str = Field(
        ...,
        description="Component that triggered the event"
    )
    
    timestamp: datetime = Field(
        default_factory=datetime.utcnow
    )
    
    # Event-specific payload
    payload: Dict[str, Any] = Field(
        default_factory=dict
    )


class PubSubManager:
    """
    Manages pub/sub for blackboard events.
    Enables reactive component coordination.
    """
    
    def __init__(self, redis_client: redis.Redis, config: BlackboardConfig):
        self.redis = redis_client
        self.config = config
        self._pubsub: Optional[redis.client.PubSub] = None
        self._handlers: Dict[str, List[callable]] = {}
        self._running = False
        self._listener_task: Optional[asyncio.Task] = None
    
    async def start(self):
        """Start the pub/sub listener."""
        self._pubsub = self.redis.pubsub()
        self._running = True
        
        # Subscribe to all blackboard channels
        channels = [
            RedisKeySchema.PUBSUB_ATOM_COMPLETE,
            RedisKeySchema.PUBSUB_SYNTHESIS_COMPLETE,
            RedisKeySchema.PUBSUB_DECISION_COMPLETE,
            RedisKeySchema.PUBSUB_LEARNING_SIGNAL,
            RedisKeySchema.PUBSUB_STATE_UPDATE,
        ]
        
        await self._pubsub.subscribe(*channels)
        
        # Start listener loop
        self._listener_task = asyncio.create_task(self._listen_loop())
        logger.info("Pub/sub listener started")
    
    async def stop(self):
        """Stop the pub/sub listener."""
        self._running = False
        if self._listener_task:
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass
        
        if self._pubsub:
            await self._pubsub.unsubscribe()
            await self._pubsub.close()
        
        logger.info("Pub/sub listener stopped")
    
    async def _listen_loop(self):
        """Main listener loop."""
        while self._running:
            try:
                message = await self._pubsub.get_message(
                    ignore_subscribe_messages=True,
                    timeout=1.0
                )
                
                if message and message['type'] == 'message':
                    await self._handle_message(message)
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in pub/sub listener: {e}")
                await asyncio.sleep(1)
    
    async def _handle_message(self, message: Dict):
        """Handle a received message."""
        channel = message['channel']
        data = message['data']
        
        if isinstance(data, bytes):
            data = data.decode('utf-8')
        
        try:
            event = BlackboardEvent.parse_raw(data)
            
            # Call registered handlers
            handlers = self._handlers.get(channel, []) + self._handlers.get('*', [])
            for handler in handlers:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(event)
                    else:
                        handler(event)
                except Exception as e:
                    logger.error(f"Error in event handler: {e}")
                    
        except Exception as e:
            logger.error(f"Error parsing event: {e}")
    
    def register_handler(self, channel: str, handler: callable):
        """Register a handler for a channel."""
        if channel not in self._handlers:
            self._handlers[channel] = []
        self._handlers[channel].append(handler)
    
    async def publish(self, event: BlackboardEvent):
        """Publish an event."""
        # Determine channel based on event type
        channel = self._get_channel_for_event(event.event_type)
        
        # Serialize and publish
        data = event.json()
        await self.redis.publish(channel, data)
        
        logger.debug(f"Published event {event.event_type} to {channel}")
    
    def _get_channel_for_event(self, event_type: BlackboardEventType) -> str:
        """Map event type to channel."""
        if event_type in [
            BlackboardEventType.ATOM_STARTED,
            BlackboardEventType.ATOM_SIGNAL,
            BlackboardEventType.ATOM_COMPLETE,
            BlackboardEventType.ATOM_ERROR
        ]:
            return RedisKeySchema.PUBSUB_ATOM_COMPLETE
        elif event_type in [
            BlackboardEventType.SYNTHESIS_STARTED,
            BlackboardEventType.SYNTHESIS_COMPLETE,
            BlackboardEventType.SYNTHESIS_ERROR
        ]:
            return RedisKeySchema.PUBSUB_SYNTHESIS_COMPLETE
        elif event_type in [
            BlackboardEventType.DECISION_STARTED,
            BlackboardEventType.DECISION_COMPLETE,
            BlackboardEventType.DECISION_ERROR
        ]:
            return RedisKeySchema.PUBSUB_DECISION_COMPLETE
        elif event_type in [
            BlackboardEventType.LEARNING_SIGNAL,
            BlackboardEventType.OUTCOME_RECEIVED
        ]:
            return RedisKeySchema.PUBSUB_LEARNING_SIGNAL
        else:
            return RedisKeySchema.PUBSUB_STATE_UPDATE
    
    async def publish_atom_complete(
        self, 
        request_id: str, 
        atom_type: str,
        success: bool,
        confidence: Optional[float] = None
    ):
        """Convenience method for publishing atom completion."""
        event = BlackboardEvent(
            event_type=BlackboardEventType.ATOM_COMPLETE if success else BlackboardEventType.ATOM_ERROR,
            request_id=request_id,
            zone=BlackboardZone.ATOM_REASONING,
            component=atom_type,
            payload={
                "atom_type": atom_type,
                "success": success,
                "confidence": confidence
            }
        )
        await self.publish(event)
    
    async def publish_synthesis_complete(
        self,
        request_id: str,
        success: bool,
        mechanism: Optional[str] = None
    ):
        """Convenience method for publishing synthesis completion."""
        event = BlackboardEvent(
            event_type=BlackboardEventType.SYNTHESIS_COMPLETE if success else BlackboardEventType.SYNTHESIS_ERROR,
            request_id=request_id,
            zone=BlackboardZone.SYNTHESIS_WORKSPACE,
            component="synthesis",
            payload={
                "success": success,
                "recommended_mechanism": mechanism
            }
        )
        await self.publish(event)
    
    async def publish_decision_complete(
        self,
        request_id: str,
        decision_id: str,
        ad_id: str,
        tier: str
    ):
        """Convenience method for publishing decision completion."""
        event = BlackboardEvent(
            event_type=BlackboardEventType.DECISION_COMPLETE,
            request_id=request_id,
            zone=BlackboardZone.DECISION_STATE,
            component="decision",
            payload={
                "decision_id": decision_id,
                "ad_id": ad_id,
                "tier": tier
            }
        )
        await self.publish(event)
```


# SECTION G: BLACKBOARD SERVICE

## BlackboardService Core

### Main Service Implementation

```python
"""
ADAM Enhancement #02: BlackboardService Core
Enterprise-grade service for blackboard operations.
"""

from typing import Optional, Dict, Any, List, Type, TypeVar, Generic
from pydantic import BaseModel
from datetime import datetime, timedelta
import asyncio
import logging
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=BaseModel)


class BlackboardService:
    """
    Main service for all blackboard operations.
    Provides type-safe access to all zones with proper access control.
    """
    
    def __init__(
        self,
        config: BlackboardConfig,
        pool_manager: RedisPoolManager,
        serializer_factory: SerializerFactory,
        ttl_manager: TTLManager,
        pubsub_manager: PubSubManager,
        metrics_collector: Optional['BlackboardMetrics'] = None
    ):
        self.config = config
        self.pool_manager = pool_manager
        self.serializer_factory = serializer_factory
        self.ttl_manager = ttl_manager
        self.pubsub = pubsub_manager
        self.metrics = metrics_collector
        
        self._redis = pool_manager.main_client
        self._zone_managers: Dict[BlackboardZone, 'ZoneManager'] = {}
        
    async def initialize(self):
        """Initialize the blackboard service."""
        # Create zone managers
        for zone in BlackboardZone:
            self._zone_managers[zone] = ZoneManager(
                zone=zone,
                config=self.config.zones[zone],
                redis=self._redis,
                serializer=self.serializer_factory.get_serializer(zone),
                ttl_manager=self.ttl_manager,
                pubsub=self.pubsub,
                metrics=self.metrics
            )
        
        # Start pub/sub listener
        await self.pubsub.start()
        
        logger.info("BlackboardService initialized")
    
    async def close(self):
        """Close the blackboard service."""
        await self.pubsub.stop()
        await self.pool_manager.close()
        logger.info("BlackboardService closed")
    
    # ==================== Zone 1: Request Context ====================
    
    async def create_request_context(
        self,
        request_context: RequestContext,
        ttl_override: Optional[int] = None
    ) -> BlackboardWriteResult:
        """
        Create request context for a new request.
        This is called once at request start.
        """
        return await self._zone_managers[BlackboardZone.REQUEST_CONTEXT].write(
            request_id=request_context.request_id,
            key_suffix="context",
            data=request_context,
            ttl_override=ttl_override,
            emit_event=True
        )
    
    async def get_request_context(
        self,
        request_id: str
    ) -> Optional[RequestContext]:
        """Get request context for a request."""
        result = await self._zone_managers[BlackboardZone.REQUEST_CONTEXT].read(
            request_id=request_id,
            key_suffix="context",
            model_class=RequestContext
        )
        return result.entry.data if result.found else None
    
    # ==================== Zone 2: Atom Reasoning ====================
    
    async def create_atom_space(
        self,
        request_id: str,
        atom_type: AtomType,
        initial_state: Optional[AtomReasoningSpace] = None
    ) -> BlackboardWriteResult:
        """Create a reasoning space for an atom."""
        space = initial_state or AtomReasoningSpace(
            atom_id=f"{atom_type.value}_{request_id[:8]}",
            atom_type=atom_type,
            request_id=request_id,
            status=AtomStatus.PENDING,
            created_at=datetime.utcnow()
        )
        
        return await self._zone_managers[BlackboardZone.ATOM_REASONING].write(
            request_id=request_id,
            key_suffix=f"{atom_type.value}:space",
            data=space,
            emit_event=True
        )
    
    async def update_atom_space(
        self,
        request_id: str,
        atom_type: AtomType,
        updates: Dict[str, Any]
    ) -> BlackboardWriteResult:
        """Update an atom's reasoning space."""
        # Read current state
        current = await self.get_atom_space(request_id, atom_type)
        if not current:
            raise ValueError(f"Atom space not found: {atom_type.value}")
        
        # Apply updates
        updated_data = current.dict()
        updated_data.update(updates)
        updated_data['version'] = current.version + 1
        updated_data['updated_at'] = datetime.utcnow()
        
        updated_space = AtomReasoningSpace(**updated_data)
        
        result = await self._zone_managers[BlackboardZone.ATOM_REASONING].write(
            request_id=request_id,
            key_suffix=f"{atom_type.value}:space",
            data=updated_space,
            emit_event=True
        )
        
        # Emit specific events based on status changes
        if 'status' in updates:
            if updates['status'] == AtomStatus.COMPLETE:
                await self.pubsub.publish_atom_complete(
                    request_id=request_id,
                    atom_type=atom_type.value,
                    success=True,
                    confidence=updated_space.output.confidence if updated_space.output else None
                )
            elif updates['status'] == AtomStatus.ERROR:
                await self.pubsub.publish_atom_complete(
                    request_id=request_id,
                    atom_type=atom_type.value,
                    success=False
                )
        
        return result
    
    async def get_atom_space(
        self,
        request_id: str,
        atom_type: AtomType
    ) -> Optional[AtomReasoningSpace]:
        """Get an atom's reasoning space."""
        result = await self._zone_managers[BlackboardZone.ATOM_REASONING].read(
            request_id=request_id,
            key_suffix=f"{atom_type.value}:space",
            model_class=AtomReasoningSpace
        )
        return result.entry.data if result.found else None
    
    async def get_all_atom_spaces(
        self,
        request_id: str,
        atom_types: Optional[List[AtomType]] = None
    ) -> Dict[AtomType, AtomReasoningSpace]:
        """Get all atom spaces for a request."""
        if atom_types is None:
            atom_types = list(AtomType)
        
        spaces = {}
        for atom_type in atom_types:
            space = await self.get_atom_space(request_id, atom_type)
            if space:
                spaces[atom_type] = space
        
        return spaces
    
    async def publish_preliminary_signal(
        self,
        request_id: str,
        atom_type: AtomType,
        signal: PreliminarySignal
    ) -> BlackboardWriteResult:
        """Publish a preliminary signal from an atom."""
        # Store signal in atom's signal list
        key = RedisKeySchema.zone2_atom_signals_key(request_id, atom_type.value)
        
        # Append to list
        serialized = signal.json()
        await self._redis.rpush(key, serialized)
        await self._redis.expire(key, self.config.zones[BlackboardZone.ATOM_REASONING].default_ttl_seconds)
        
        # Also update the atom space
        space = await self.get_atom_space(request_id, atom_type)
        if space:
            space.preliminary_signals.append(signal)
            await self.update_atom_space(
                request_id=request_id,
                atom_type=atom_type,
                updates={'preliminary_signals': [s.dict() for s in space.preliminary_signals]}
            )
        
        # Emit event for cross-atom coordination
        await self.pubsub.publish(BlackboardEvent(
            event_type=BlackboardEventType.ATOM_SIGNAL,
            request_id=request_id,
            zone=BlackboardZone.ATOM_REASONING,
            component=atom_type.value,
            payload=signal.dict()
        ))
        
        return BlackboardWriteResult(
            success=True,
            entry_id=signal.signal_id,
            version=1,
            redis_key=key,
            write_latency_ms=0,
            event_published=True
        )
    
    async def get_preliminary_signals(
        self,
        request_id: str,
        signal_type: Optional[str] = None,
        from_atoms: Optional[List[AtomType]] = None
    ) -> List[PreliminarySignal]:
        """Get preliminary signals, optionally filtered."""
        signals = []
        
        atom_types = from_atoms or list(AtomType)
        for atom_type in atom_types:
            key = RedisKeySchema.zone2_atom_signals_key(request_id, atom_type.value)
            raw_signals = await self._redis.lrange(key, 0, -1)
            
            for raw in raw_signals:
                signal = PreliminarySignal.parse_raw(raw)
                if signal_type is None or signal.signal_type == signal_type:
                    signals.append(signal)
        
        return signals
    
    # ==================== Zone 2: Intelligence Sources ====================
    
    async def update_intelligence_source(
        self,
        request_id: str,
        source_type: IntelligenceSourceType,
        source_data: BaseModel
    ) -> BlackboardWriteResult:
        """Update an intelligence source's data."""
        return await self._zone_managers[BlackboardZone.ATOM_REASONING].write(
            request_id=request_id,
            key_suffix=f"src:{source_type.value}",
            data=source_data,
            emit_event=False
        )
    
    async def get_intelligence_sources_snapshot(
        self,
        request_id: str
    ) -> Optional[IntelligenceSourcesSnapshot]:
        """Get complete intelligence sources snapshot."""
        result = await self._zone_managers[BlackboardZone.ATOM_REASONING].read(
            request_id=request_id,
            key_suffix="src:snapshot",
            model_class=IntelligenceSourcesSnapshot
        )
        return result.entry.data if result.found else None
    
    async def save_intelligence_sources_snapshot(
        self,
        snapshot: IntelligenceSourcesSnapshot
    ) -> BlackboardWriteResult:
        """Save complete intelligence sources snapshot."""
        return await self._zone_managers[BlackboardZone.ATOM_REASONING].write(
            request_id=snapshot.request_id,
            key_suffix="src:snapshot",
            data=snapshot,
            emit_event=True
        )
    
    # ==================== Zone 3: Synthesis Workspace ====================
    
    async def create_synthesis_workspace(
        self,
        request_id: str,
        expected_atoms: List[AtomType]
    ) -> BlackboardWriteResult:
        """Create synthesis workspace for a request."""
        workspace = SynthesisWorkspace(
            request_id=request_id,
            status=SynthesisStatus.WAITING_FOR_ATOMS,
            atoms_expected=[a.value for a in expected_atoms],
            atoms_pending=[a.value for a in expected_atoms]
        )
        
        return await self._zone_managers[BlackboardZone.SYNTHESIS_WORKSPACE].write(
            request_id=request_id,
            key_suffix="workspace",
            data=workspace,
            emit_event=True
        )
    
    async def update_synthesis_workspace(
        self,
        request_id: str,
        updates: Dict[str, Any]
    ) -> BlackboardWriteResult:
        """Update synthesis workspace."""
        current = await self.get_synthesis_workspace(request_id)
        if not current:
            raise ValueError(f"Synthesis workspace not found: {request_id}")
        
        updated_data = current.dict()
        updated_data.update(updates)
        updated_data['version'] = current.version + 1
        
        updated_workspace = SynthesisWorkspace(**updated_data)
        
        result = await self._zone_managers[BlackboardZone.SYNTHESIS_WORKSPACE].write(
            request_id=request_id,
            key_suffix="workspace",
            data=updated_workspace,
            emit_event=True
        )
        
        # Emit completion event if complete
        if updates.get('status') == SynthesisStatus.COMPLETE:
            mechanism = None
            if updated_workspace.recommendation:
                mechanism = updated_workspace.recommendation.primary_mechanism
            await self.pubsub.publish_synthesis_complete(
                request_id=request_id,
                success=True,
                mechanism=mechanism
            )
        
        return result
    
    async def get_synthesis_workspace(
        self,
        request_id: str
    ) -> Optional[SynthesisWorkspace]:
        """Get synthesis workspace."""
        result = await self._zone_managers[BlackboardZone.SYNTHESIS_WORKSPACE].read(
            request_id=request_id,
            key_suffix="workspace",
            model_class=SynthesisWorkspace
        )
        return result.entry.data if result.found else None
    
    # ==================== Zone 4: Decision State ====================
    
    async def create_decision_state(
        self,
        request_id: str
    ) -> BlackboardWriteResult:
        """Create decision state for a request."""
        state = DecisionState(
            request_id=request_id,
            status=DecisionStatus.PENDING
        )
        
        return await self._zone_managers[BlackboardZone.DECISION_STATE].write(
            request_id=request_id,
            key_suffix="state",
            data=state,
            emit_event=True
        )
    
    async def update_decision_state(
        self,
        request_id: str,
        updates: Dict[str, Any]
    ) -> BlackboardWriteResult:
        """Update decision state."""
        current = await self.get_decision_state(request_id)
        if not current:
            raise ValueError(f"Decision state not found: {request_id}")
        
        updated_data = current.dict()
        updated_data.update(updates)
        updated_data['version'] = current.version + 1
        
        updated_state = DecisionState(**updated_data)
        
        result = await self._zone_managers[BlackboardZone.DECISION_STATE].write(
            request_id=request_id,
            key_suffix="state",
            data=updated_state,
            emit_event=True
        )
        
        # Emit completion event if complete
        if updates.get('status') == DecisionStatus.COMPLETE:
            await self.pubsub.publish_decision_complete(
                request_id=request_id,
                decision_id=updated_state.decision_id,
                ad_id=updated_state.selected_ad.ad_id if updated_state.selected_ad else "unknown",
                tier=updated_state.decision_tier.value if updated_state.decision_tier else "unknown"
            )
        
        return result
    
    async def get_decision_state(
        self,
        request_id: str
    ) -> Optional[DecisionState]:
        """Get decision state."""
        result = await self._zone_managers[BlackboardZone.DECISION_STATE].read(
            request_id=request_id,
            key_suffix="state",
            model_class=DecisionState
        )
        return result.entry.data if result.found else None
    
    # ==================== Zone 5: Learning Signals ====================
    
    async def emit_learning_signal(
        self,
        signal: LearningSignal
    ) -> BlackboardWriteResult:
        """Emit a learning signal."""
        key = RedisKeySchema.zone5_signals_key(signal.request_id)
        
        # Append to list
        serialized = signal.json()
        await self._redis.rpush(key, serialized)
        await self._redis.expire(
            key, 
            self.config.zones[BlackboardZone.LEARNING_SIGNALS].default_ttl_seconds
        )
        
        # Emit event for Gradient Bridge
        await self.pubsub.publish(BlackboardEvent(
            event_type=BlackboardEventType.LEARNING_SIGNAL,
            request_id=signal.request_id,
            zone=BlackboardZone.LEARNING_SIGNALS,
            component=signal.source_component,
            payload=signal.dict()
        ))
        
        if self.metrics:
            self.metrics.learning_signal_emitted(signal.signal_type.value)
        
        return BlackboardWriteResult(
            success=True,
            entry_id=signal.signal_id,
            version=1,
            redis_key=key,
            write_latency_ms=0,
            event_published=True
        )
    
    async def emit_outcome_signal(
        self,
        outcome: OutcomeSignal
    ) -> BlackboardWriteResult:
        """Emit an outcome signal for attribution."""
        key = RedisKeySchema.zone5_outcome_key(outcome.request_id)
        
        serialized = outcome.json()
        await self._redis.rpush(key, serialized)
        await self._redis.expire(
            key,
            self.config.zones[BlackboardZone.LEARNING_SIGNALS].default_ttl_seconds
        )
        
        # Emit event
        await self.pubsub.publish(BlackboardEvent(
            event_type=BlackboardEventType.OUTCOME_RECEIVED,
            request_id=outcome.request_id,
            zone=BlackboardZone.LEARNING_SIGNALS,
            component="outcome_collector",
            payload=outcome.dict()
        ))
        
        if self.metrics:
            self.metrics.outcome_received(outcome.outcome_type.value)
        
        return BlackboardWriteResult(
            success=True,
            entry_id=outcome.signal_id,
            version=1,
            redis_key=key,
            write_latency_ms=0,
            event_published=True
        )
    
    async def save_attribution_context(
        self,
        attribution: AttributionContext
    ) -> BlackboardWriteResult:
        """Save attribution context for later processing."""
        return await self._zone_managers[BlackboardZone.LEARNING_SIGNALS].write(
            request_id=attribution.request_id,
            key_suffix="attribution",
            data=attribution,
            emit_event=False
        )
    
    async def get_attribution_context(
        self,
        request_id: str
    ) -> Optional[AttributionContext]:
        """Get attribution context."""
        result = await self._zone_managers[BlackboardZone.LEARNING_SIGNALS].read(
            request_id=request_id,
            key_suffix="attribution",
            model_class=AttributionContext
        )
        return result.entry.data if result.found else None
    
    async def get_learning_signals(
        self,
        request_id: str,
        signal_type: Optional[LearningSignalType] = None
    ) -> List[LearningSignal]:
        """Get learning signals for a request."""
        key = RedisKeySchema.zone5_signals_key(request_id)
        raw_signals = await self._redis.lrange(key, 0, -1)
        
        signals = []
        for raw in raw_signals:
            signal = LearningSignal.parse_raw(raw)
            if signal_type is None or signal.signal_type == signal_type:
                signals.append(signal)
        
        return signals
    
    # ==================== Cross-Zone Operations ====================
    
    async def get_complete_request_state(
        self,
        request_id: str
    ) -> Dict[str, Any]:
        """Get complete state across all zones for a request."""
        state = {
            'request_id': request_id,
            'timestamp': datetime.utcnow().isoformat(),
            'zones': {}
        }
        
        # Zone 1
        context = await self.get_request_context(request_id)
        state['zones']['zone1_request_context'] = context.dict() if context else None
        
        # Zone 2 - Atoms
        atoms = await self.get_all_atom_spaces(request_id)
        state['zones']['zone2_atoms'] = {
            k.value: v.dict() for k, v in atoms.items()
        }
        
        # Zone 2 - Sources
        sources = await self.get_intelligence_sources_snapshot(request_id)
        state['zones']['zone2_sources'] = sources.dict() if sources else None
        
        # Zone 3
        synthesis = await self.get_synthesis_workspace(request_id)
        state['zones']['zone3_synthesis'] = synthesis.dict() if synthesis else None
        
        # Zone 4
        decision = await self.get_decision_state(request_id)
        state['zones']['zone4_decision'] = decision.dict() if decision else None
        
        # Zone 5
        signals = await self.get_learning_signals(request_id)
        state['zones']['zone5_signals'] = [s.dict() for s in signals]
        
        attribution = await self.get_attribution_context(request_id)
        state['zones']['zone5_attribution'] = attribution.dict() if attribution else None
        
        return state
    
    async def cleanup_request(
        self,
        request_id: str
    ):
        """Clean up all state for a request."""
        await self.ttl_manager.cleanup_request(request_id)
        logger.info(f"Cleaned up request: {request_id}")
    
    async def health_check(self) -> Dict[str, Any]:
        """Check health of blackboard service."""
        redis_health = await self.pool_manager.health_check()
        pool_stats = await self.pool_manager.get_pool_stats()
        
        return {
            'status': 'healthy' if all(redis_health.values()) else 'degraded',
            'redis_pools': redis_health,
            'pool_stats': pool_stats,
            'pubsub_running': self.pubsub._running
        }
```

---

## Zone Manager Implementation

```python
"""
ADAM Enhancement #02: Zone Manager
Manages operations within a single zone.
"""


class ZoneManager(Generic[T]):
    """
    Manages all operations for a single blackboard zone.
    Provides type-safe read/write with proper serialization.
    """
    
    def __init__(
        self,
        zone: BlackboardZone,
        config: BlackboardZoneConfig,
        redis: redis.Redis,
        serializer: BlackboardSerializer,
        ttl_manager: TTLManager,
        pubsub: PubSubManager,
        metrics: Optional['BlackboardMetrics'] = None
    ):
        self.zone = zone
        self.config = config
        self.redis = redis
        self.serializer = serializer
        self.ttl_manager = ttl_manager
        self.pubsub = pubsub
        self.metrics = metrics
    
    def _build_key(self, request_id: str, key_suffix: str) -> str:
        """Build Redis key for this zone."""
        return f"{self.config.redis_prefix}{request_id}:{key_suffix}"
    
    async def write(
        self,
        request_id: str,
        key_suffix: str,
        data: T,
        ttl_override: Optional[int] = None,
        emit_event: bool = True
    ) -> BlackboardWriteResult:
        """Write data to this zone."""
        start_time = datetime.utcnow()
        key = self._build_key(request_id, key_suffix)
        
        try:
            # Serialize
            serialized = self.serializer.serialize(data)
            
            # Check size limit
            if len(serialized) > self.config.max_entry_size_bytes:
                raise ValueError(
                    f"Entry size {len(serialized)} exceeds limit {self.config.max_entry_size_bytes}"
                )
            
            # Get TTL
            ttl = self.ttl_manager.get_ttl(self.zone, ttl_override)
            
            # Write with TTL
            await self.redis.setex(key, ttl, serialized)
            
            # Register key for cleanup
            await self.ttl_manager.register_key(request_id, key)
            
            # Calculate latency
            latency_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            # Emit event if configured
            event_published = False
            if emit_event and self.config.enable_pubsub:
                await self.pubsub.publish(BlackboardEvent(
                    event_type=BlackboardEventType.ZONE_UPDATE,
                    request_id=request_id,
                    zone=self.zone,
                    component=key_suffix,
                    payload={'key': key}
                ))
                event_published = True
            
            # Record metrics
            if self.metrics:
                self.metrics.record_write(
                    zone=self.zone.value,
                    latency_ms=latency_ms,
                    size_bytes=len(serialized),
                    compressed=self.serializer.is_compressed(serialized)
                )
            
            return BlackboardWriteResult(
                success=True,
                entry_id=key,
                version=getattr(data, 'version', 1),
                redis_key=key,
                write_latency_ms=latency_ms,
                event_published=event_published
            )
            
        except Exception as e:
            logger.error(f"Error writing to zone {self.zone.value}: {e}")
            latency_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            if self.metrics:
                self.metrics.record_error(zone=self.zone.value, operation='write')
            
            return BlackboardWriteResult(
                success=False,
                entry_id="",
                version=0,
                redis_key=key,
                write_latency_ms=latency_ms,
                error=str(e)
            )
    
    async def read(
        self,
        request_id: str,
        key_suffix: str,
        model_class: Type[T]
    ) -> BlackboardReadResult[T]:
        """Read data from this zone."""
        start_time = datetime.utcnow()
        key = self._build_key(request_id, key_suffix)
        
        try:
            # Read from Redis
            raw_data = await self.redis.get(key)
            
            latency_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            if raw_data is None:
                if self.metrics:
                    self.metrics.record_read(
                        zone=self.zone.value,
                        latency_ms=latency_ms,
                        hit=False
                    )
                
                return BlackboardReadResult(
                    found=False,
                    entry=None,
                    redis_key=key,
                    read_latency_ms=latency_ms
                )
            
            # Deserialize
            data = self.serializer.deserialize(raw_data, model_class)
            
            # Build metadata
            metadata = BlackboardMetadata(
                request_id=request_id,
                zone=self.zone,
                writer_component="unknown",  # Would need to store this
                ttl_seconds=await self.ttl_manager.get_remaining_ttl(key),
                size_bytes=len(raw_data),
                compressed=self.serializer.is_compressed(raw_data)
            )
            
            entry = BlackboardEntry(
                metadata=metadata,
                data=data
            )
            
            if self.metrics:
                self.metrics.record_read(
                    zone=self.zone.value,
                    latency_ms=latency_ms,
                    hit=True,
                    size_bytes=len(raw_data)
                )
            
            return BlackboardReadResult(
                found=True,
                entry=entry,
                redis_key=key,
                read_latency_ms=latency_ms
            )
            
        except Exception as e:
            logger.error(f"Error reading from zone {self.zone.value}: {e}")
            latency_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            if self.metrics:
                self.metrics.record_error(zone=self.zone.value, operation='read')
            
            return BlackboardReadResult(
                found=False,
                entry=None,
                redis_key=key,
                read_latency_ms=latency_ms,
                error=str(e)
            )
    
    async def delete(
        self,
        request_id: str,
        key_suffix: str
    ) -> bool:
        """Delete data from this zone."""
        key = self._build_key(request_id, key_suffix)
        result = await self.redis.delete(key)
        return result > 0
    
    async def exists(
        self,
        request_id: str,
        key_suffix: str
    ) -> bool:
        """Check if data exists in this zone."""
        key = self._build_key(request_id, key_suffix)
        return await self.redis.exists(key) > 0
```

---

## State Transition Engine

```python
"""
ADAM Enhancement #02: State Transition Engine
Manages valid state transitions for blackboard entries.
"""


class StateTransitionError(Exception):
    """Raised when an invalid state transition is attempted."""
    pass


class AtomStateTransitions:
    """Valid state transitions for atoms."""
    
    VALID_TRANSITIONS = {
        AtomStatus.PENDING: [AtomStatus.INITIALIZING, AtomStatus.SKIPPED],
        AtomStatus.INITIALIZING: [AtomStatus.REASONING, AtomStatus.ERROR, AtomStatus.TIMEOUT],
        AtomStatus.REASONING: [AtomStatus.SYNTHESIZING, AtomStatus.COMPLETE, AtomStatus.ERROR, AtomStatus.TIMEOUT],
        AtomStatus.SYNTHESIZING: [AtomStatus.COMPLETE, AtomStatus.ERROR, AtomStatus.TIMEOUT],
        AtomStatus.COMPLETE: [],  # Terminal state
        AtomStatus.ERROR: [],     # Terminal state
        AtomStatus.TIMEOUT: [],   # Terminal state
        AtomStatus.SKIPPED: [],   # Terminal state
    }
    
    @classmethod
    def validate_transition(cls, current: AtomStatus, target: AtomStatus) -> bool:
        """Check if transition is valid."""
        valid_targets = cls.VALID_TRANSITIONS.get(current, [])
        return target in valid_targets
    
    @classmethod
    def assert_transition(cls, current: AtomStatus, target: AtomStatus):
        """Assert transition is valid or raise error."""
        if not cls.validate_transition(current, target):
            raise StateTransitionError(
                f"Invalid atom state transition: {current.value} -> {target.value}"
            )


class SynthesisStateTransitions:
    """Valid state transitions for synthesis."""
    
    VALID_TRANSITIONS = {
        SynthesisStatus.WAITING_FOR_ATOMS: [SynthesisStatus.AGGREGATING, SynthesisStatus.ERROR, SynthesisStatus.TIMEOUT],
        SynthesisStatus.AGGREGATING: [SynthesisStatus.RESOLVING_CONFLICTS, SynthesisStatus.SYNTHESIZING, SynthesisStatus.ERROR],
        SynthesisStatus.RESOLVING_CONFLICTS: [SynthesisStatus.SYNTHESIZING, SynthesisStatus.ERROR],
        SynthesisStatus.SYNTHESIZING: [SynthesisStatus.COMPLETE, SynthesisStatus.ERROR, SynthesisStatus.TIMEOUT],
        SynthesisStatus.COMPLETE: [],
        SynthesisStatus.ERROR: [],
        SynthesisStatus.TIMEOUT: [],
    }
    
    @classmethod
    def validate_transition(cls, current: SynthesisStatus, target: SynthesisStatus) -> bool:
        valid_targets = cls.VALID_TRANSITIONS.get(current, [])
        return target in valid_targets


class DecisionStateTransitions:
    """Valid state transitions for decisions."""
    
    VALID_TRANSITIONS = {
        DecisionStatus.PENDING: [DecisionStatus.PROCESSING, DecisionStatus.FALLBACK, DecisionStatus.ERROR],
        DecisionStatus.PROCESSING: [DecisionStatus.COMPLETE, DecisionStatus.FALLBACK, DecisionStatus.ERROR],
        DecisionStatus.FALLBACK: [DecisionStatus.COMPLETE, DecisionStatus.ERROR],
        DecisionStatus.COMPLETE: [],
        DecisionStatus.ERROR: [],
    }
    
    @classmethod
    def validate_transition(cls, current: DecisionStatus, target: DecisionStatus) -> bool:
        valid_targets = cls.VALID_TRANSITIONS.get(current, [])
        return target in valid_targets


class StateTransitionEngine:
    """
    Manages state transitions across all blackboard entities.
    Ensures only valid transitions occur.
    """
    
    def __init__(self, blackboard_service: BlackboardService):
        self.blackboard = blackboard_service
    
    async def transition_atom(
        self,
        request_id: str,
        atom_type: AtomType,
        target_status: AtomStatus,
        additional_updates: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Transition an atom to a new state with validation.
        """
        current_space = await self.blackboard.get_atom_space(request_id, atom_type)
        if not current_space:
            raise ValueError(f"Atom space not found: {atom_type.value}")
        
        # Validate transition
        AtomStateTransitions.assert_transition(current_space.status, target_status)
        
        # Build updates
        updates = {'status': target_status}
        
        # Add timestamps based on transition
        if target_status == AtomStatus.REASONING:
            updates['started_at'] = datetime.utcnow()
        elif target_status in [AtomStatus.COMPLETE, AtomStatus.ERROR, AtomStatus.TIMEOUT]:
            updates['completed_at'] = datetime.utcnow()
        
        if additional_updates:
            updates.update(additional_updates)
        
        # Perform update
        result = await self.blackboard.update_atom_space(
            request_id=request_id,
            atom_type=atom_type,
            updates=updates
        )
        
        return result.success
    
    async def transition_synthesis(
        self,
        request_id: str,
        target_status: SynthesisStatus,
        additional_updates: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Transition synthesis to a new state."""
        current = await self.blackboard.get_synthesis_workspace(request_id)
        if not current:
            raise ValueError(f"Synthesis workspace not found: {request_id}")
        
        SynthesisStateTransitions.validate_transition(current.status, target_status)
        
        updates = {'status': target_status}
        
        if target_status == SynthesisStatus.AGGREGATING:
            updates['started_at'] = datetime.utcnow()
        elif target_status == SynthesisStatus.COMPLETE:
            updates['completed_at'] = datetime.utcnow()
        
        if additional_updates:
            updates.update(additional_updates)
        
        result = await self.blackboard.update_synthesis_workspace(
            request_id=request_id,
            updates=updates
        )
        
        return result.success
    
    async def transition_decision(
        self,
        request_id: str,
        target_status: DecisionStatus,
        additional_updates: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Transition decision to a new state."""
        current = await self.blackboard.get_decision_state(request_id)
        if not current:
            raise ValueError(f"Decision state not found: {request_id}")
        
        DecisionStateTransitions.validate_transition(current.status, target_status)
        
        updates = {'status': target_status}
        
        if target_status == DecisionStatus.COMPLETE:
            updates['completed_at'] = datetime.utcnow()
        
        if additional_updates:
            updates.update(additional_updates)
        
        result = await self.blackboard.update_decision_state(
            request_id=request_id,
            updates=updates
        )
        
        return result.success
```

---

## Conflict Resolution

```python
"""
ADAM Enhancement #02: Conflict Resolution
Handles conflicts in blackboard state.
"""


class ConflictType(str, Enum):
    """Types of conflicts that can occur."""
    CONCURRENT_WRITE = "concurrent_write"
    VERSION_MISMATCH = "version_mismatch"
    STALE_DATA = "stale_data"
    INCONSISTENT_STATE = "inconsistent_state"


class ConflictResolutionStrategy(str, Enum):
    """Strategies for resolving conflicts."""
    LAST_WRITE_WINS = "last_write_wins"
    FIRST_WRITE_WINS = "first_write_wins"
    MERGE = "merge"
    REJECT = "reject"


class ConflictInfo(BaseModel):
    """Information about a detected conflict."""
    
    conflict_type: ConflictType
    key: str
    current_version: int
    attempted_version: int
    current_timestamp: datetime
    attempted_timestamp: datetime
    resolution_strategy: ConflictResolutionStrategy
    resolved: bool
    resolution_details: Optional[str] = None


class ConflictResolver:
    """
    Resolves conflicts in blackboard state.
    Uses optimistic locking with configurable resolution strategies.
    """
    
    def __init__(
        self,
        redis: redis.Redis,
        default_strategy: ConflictResolutionStrategy = ConflictResolutionStrategy.LAST_WRITE_WINS
    ):
        self.redis = redis
        self.default_strategy = default_strategy
    
    async def write_with_version_check(
        self,
        key: str,
        data: bytes,
        expected_version: int,
        new_version: int,
        ttl: int,
        strategy: Optional[ConflictResolutionStrategy] = None
    ) -> Tuple[bool, Optional[ConflictInfo]]:
        """
        Write data with version checking for optimistic locking.
        """
        strategy = strategy or self.default_strategy
        
        # Use Redis transaction for atomic check-and-set
        async with self.redis.pipeline(transaction=True) as pipe:
            try:
                # Watch the key
                await pipe.watch(key)
                
                # Get current version
                current_data = await self.redis.get(key)
                current_version = 0
                current_timestamp = datetime.utcnow()
                
                if current_data:
                    # Parse to get version (assuming JSON with 'version' field)
                    try:
                        import json
                        parsed = json.loads(current_data)
                        current_version = parsed.get('version', 0)
                        if 'updated_at' in parsed:
                            current_timestamp = datetime.fromisoformat(parsed['updated_at'])
                    except:
                        pass
                
                # Check for version conflict
                if current_version != expected_version:
                    conflict = ConflictInfo(
                        conflict_type=ConflictType.VERSION_MISMATCH,
                        key=key,
                        current_version=current_version,
                        attempted_version=expected_version,
                        current_timestamp=current_timestamp,
                        attempted_timestamp=datetime.utcnow(),
                        resolution_strategy=strategy,
                        resolved=False
                    )
                    
                    # Apply resolution strategy
                    if strategy == ConflictResolutionStrategy.LAST_WRITE_WINS:
                        # Proceed with write
                        pipe.multi()
                        pipe.setex(key, ttl, data)
                        await pipe.execute()
                        conflict.resolved = True
                        conflict.resolution_details = "Last write wins - overwrote existing"
                        return True, conflict
                    
                    elif strategy == ConflictResolutionStrategy.REJECT:
                        conflict.resolution_details = "Write rejected due to version mismatch"
                        return False, conflict
                    
                    else:
                        # First write wins or merge require special handling
                        conflict.resolution_details = f"Strategy {strategy.value} not implemented for this case"
                        return False, conflict
                
                # No conflict - proceed with write
                pipe.multi()
                pipe.setex(key, ttl, data)
                await pipe.execute()
                return True, None
                
            except redis.WatchError:
                # Key was modified during transaction
                conflict = ConflictInfo(
                    conflict_type=ConflictType.CONCURRENT_WRITE,
                    key=key,
                    current_version=0,
                    attempted_version=expected_version,
                    current_timestamp=datetime.utcnow(),
                    attempted_timestamp=datetime.utcnow(),
                    resolution_strategy=strategy,
                    resolved=False,
                    resolution_details="Concurrent modification detected"
                )
                return False, conflict
```

---

## Concurrent Access Control

```python
"""
ADAM Enhancement #02: Concurrent Access Control
Manages concurrent access to blackboard state.
"""


class DistributedLock:
    """
    Distributed lock using Redis for coordinating access.
    """
    
    def __init__(
        self,
        redis: redis.Redis,
        lock_name: str,
        timeout: float = 10.0,
        blocking_timeout: float = 5.0
    ):
        self.redis = redis
        self.lock_name = f"bb:lock:{lock_name}"
        self.timeout = timeout
        self.blocking_timeout = blocking_timeout
        self._lock_value: Optional[str] = None
    
    async def acquire(self) -> bool:
        """Acquire the lock."""
        self._lock_value = str(uuid.uuid4())
        
        # Try to acquire with timeout
        end_time = datetime.utcnow() + timedelta(seconds=self.blocking_timeout)
        
        while datetime.utcnow() < end_time:
            acquired = await self.redis.set(
                self.lock_name,
                self._lock_value,
                nx=True,
                ex=int(self.timeout)
            )
            
            if acquired:
                return True
            
            await asyncio.sleep(0.1)
        
        return False
    
    async def release(self) -> bool:
        """Release the lock."""
        if not self._lock_value:
            return False
        
        # Use Lua script for atomic check-and-delete
        lua_script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("del", KEYS[1])
        else
            return 0
        end
        """
        
        result = await self.redis.eval(lua_script, 1, self.lock_name, self._lock_value)
        self._lock_value = None
        return result == 1
    
    async def extend(self, additional_time: float) -> bool:
        """Extend the lock timeout."""
        if not self._lock_value:
            return False
        
        # Verify we still own the lock and extend
        lua_script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("expire", KEYS[1], ARGV[2])
        else
            return 0
        end
        """
        
        new_timeout = int(self.timeout + additional_time)
        result = await self.redis.eval(
            lua_script, 1, self.lock_name, self._lock_value, new_timeout
        )
        return result == 1


@asynccontextmanager
async def blackboard_lock(
    redis: redis.Redis,
    lock_name: str,
    timeout: float = 10.0
):
    """Context manager for distributed locking."""
    lock = DistributedLock(redis, lock_name, timeout)
    
    acquired = await lock.acquire()
    if not acquired:
        raise TimeoutError(f"Could not acquire lock: {lock_name}")
    
    try:
        yield lock
    finally:
        await lock.release()


class AccessController:
    """
    Controls access to blackboard zones based on component permissions.
    """
    
    def __init__(self, config: BlackboardConfig):
        self.config = config
        self._access_profiles: Dict[str, ComponentAccessConfig] = {}
    
    def register_component(self, access_config: ComponentAccessConfig):
        """Register a component's access configuration."""
        self._access_profiles[access_config.component_id] = access_config
    
    def check_access(
        self,
        component_id: str,
        zone: BlackboardZone,
        operation: str  # 'read' or 'write'
    ) -> bool:
        """Check if component has access for operation on zone."""
        profile = self._access_profiles.get(component_id)
        if not profile:
            return False
        
        access_level = profile.zone_access.get(zone, ZoneAccessLevel.NONE)
        
        if operation == 'read':
            return access_level in [ZoneAccessLevel.READ, ZoneAccessLevel.READ_WRITE]
        elif operation == 'write':
            return access_level in [ZoneAccessLevel.WRITE, ZoneAccessLevel.READ_WRITE]
        
        return False
    
    def assert_access(
        self,
        component_id: str,
        zone: BlackboardZone,
        operation: str
    ):
        """Assert access or raise PermissionError."""
        if not self.check_access(component_id, zone, operation):
            raise PermissionError(
                f"Component '{component_id}' does not have {operation} access to {zone.value}"
            )
```


# SECTION H: EVENT BUS INTEGRATION

## Blackboard Event Definitions

### Kafka Event Integration

```python
"""
ADAM Enhancement #02: Kafka Event Bus Integration
Integration with Enhancement #31's Event Bus infrastructure.
"""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum
import uuid


class BlackboardKafkaTopic(str, Enum):
    """Kafka topics for blackboard events."""
    ATOM_EVENTS = "adam.blackboard.atom"
    SYNTHESIS_EVENTS = "adam.blackboard.synthesis"
    DECISION_EVENTS = "adam.blackboard.decision"
    LEARNING_EVENTS = "adam.blackboard.learning"
    STATE_EVENTS = "adam.blackboard.state"
    AUDIT_EVENTS = "adam.blackboard.audit"


class BlackboardKafkaEvent(BaseModel):
    """
    Base Kafka event for blackboard state changes.
    Follows Enhancement #31 event contract patterns.
    """
    
    # Event metadata
    event_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique event identifier"
    )
    
    event_type: str = Field(
        ...,
        description="Event type (atom.complete, synthesis.start, etc.)"
    )
    
    event_version: str = Field(
        default="1.0",
        description="Event schema version"
    )
    
    timestamp: datetime = Field(
        default_factory=datetime.utcnow
    )
    
    # Correlation
    request_id: str = Field(
        ...,
        description="Request this event relates to"
    )
    
    correlation_id: Optional[str] = Field(
        default=None,
        description="For tracing across services"
    )
    
    causation_id: Optional[str] = Field(
        default=None,
        description="Event that caused this event"
    )
    
    # Source
    source_component: str = Field(
        ...,
        description="Component that generated this event"
    )
    
    source_zone: str = Field(
        ...,
        description="Blackboard zone"
    )
    
    # Payload
    payload: Dict[str, Any] = Field(
        default_factory=dict
    )
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


# ==================== Atom Events ====================

class AtomStartedEvent(BlackboardKafkaEvent):
    """Event emitted when an atom starts reasoning."""
    event_type: str = "atom.started"
    
    class Payload(BaseModel):
        atom_type: str
        atom_id: str
        expected_duration_ms: Optional[int] = None


class AtomSignalEvent(BlackboardKafkaEvent):
    """Event emitted when an atom publishes a preliminary signal."""
    event_type: str = "atom.signal"
    
    class Payload(BaseModel):
        atom_type: str
        signal_type: str
        signal_value: Any
        confidence: float
        requires_attention: bool = False


class AtomCompletedEvent(BlackboardKafkaEvent):
    """Event emitted when an atom completes."""
    event_type: str = "atom.completed"
    
    class Payload(BaseModel):
        atom_type: str
        atom_id: str
        status: str  # complete, error, timeout
        determination: Optional[str] = None
        confidence: Optional[float] = None
        latency_ms: float
        tokens_used: Optional[int] = None


# ==================== Synthesis Events ====================

class SynthesisStartedEvent(BlackboardKafkaEvent):
    """Event emitted when synthesis starts."""
    event_type: str = "synthesis.started"
    
    class Payload(BaseModel):
        atoms_received: List[str]
        atoms_pending: List[str]


class SynthesisConflictEvent(BlackboardKafkaEvent):
    """Event emitted when synthesis detects conflicts."""
    event_type: str = "synthesis.conflict"
    
    class Payload(BaseModel):
        conflict_count: int
        conflicts: List[Dict[str, Any]]
        resolution_strategy: str


class SynthesisCompletedEvent(BlackboardKafkaEvent):
    """Event emitted when synthesis completes."""
    event_type: str = "synthesis.completed"
    
    class Payload(BaseModel):
        status: str
        primary_mechanism: Optional[str] = None
        mechanism_confidence: Optional[float] = None
        conflicts_resolved: int = 0
        latency_ms: float


# ==================== Decision Events ====================

class DecisionStartedEvent(BlackboardKafkaEvent):
    """Event emitted when decision processing starts."""
    event_type: str = "decision.started"
    
    class Payload(BaseModel):
        synthesis_mechanism: str
        ad_candidates_count: int
        latency_budget_ms: int


class DecisionCompletedEvent(BlackboardKafkaEvent):
    """Event emitted when decision completes."""
    event_type: str = "decision.completed"
    
    class Payload(BaseModel):
        decision_id: str
        ad_id: str
        tier: str
        mechanism_used: str
        predicted_effectiveness: Optional[float] = None
        latency_ms: float
        within_budget: bool


# ==================== Learning Events ====================

class LearningSignalEmittedEvent(BlackboardKafkaEvent):
    """Event emitted when a learning signal is recorded."""
    event_type: str = "learning.signal"
    
    class Payload(BaseModel):
        signal_type: str
        signal_id: str
        source_component: str
        priority: str


class OutcomeReceivedEvent(BlackboardKafkaEvent):
    """Event emitted when an outcome is received."""
    event_type: str = "learning.outcome"
    
    class Payload(BaseModel):
        outcome_type: str
        outcome_value: Optional[float] = None
        decision_id: str
        delay_seconds: float
        mechanism_used: str
```

---

## State Change Events

```python
"""
ADAM Enhancement #02: State Change Event Producer
Produces events for all state changes to Kafka.
"""


class BlackboardEventProducer:
    """
    Produces Kafka events for blackboard state changes.
    Integrates with Enhancement #31's Event Bus infrastructure.
    """
    
    def __init__(
        self,
        kafka_producer: 'TypedKafkaProducer',  # From Enhancement #31
        config: BlackboardConfig
    ):
        self.producer = kafka_producer
        self.config = config
        self._topic_prefix = config.event_bus_topic_prefix
    
    def _get_topic(self, event_type: str) -> str:
        """Get Kafka topic for event type."""
        if event_type.startswith("atom."):
            return f"{self._topic_prefix}.atom"
        elif event_type.startswith("synthesis."):
            return f"{self._topic_prefix}.synthesis"
        elif event_type.startswith("decision."):
            return f"{self._topic_prefix}.decision"
        elif event_type.startswith("learning."):
            return f"{self._topic_prefix}.learning"
        else:
            return f"{self._topic_prefix}.state"
    
    async def produce_event(
        self,
        event: BlackboardKafkaEvent,
        key: Optional[str] = None
    ):
        """Produce an event to Kafka."""
        topic = self._get_topic(event.event_type)
        
        # Use request_id as key for ordering
        message_key = key or event.request_id
        
        await self.producer.produce(
            topic=topic,
            key=message_key,
            value=event.json()
        )
    
    # Convenience methods for common events
    
    async def emit_atom_started(
        self,
        request_id: str,
        atom_type: str,
        atom_id: str,
        correlation_id: Optional[str] = None
    ):
        """Emit atom started event."""
        event = AtomStartedEvent(
            request_id=request_id,
            correlation_id=correlation_id,
            source_component=atom_type,
            source_zone=BlackboardZone.ATOM_REASONING.value,
            payload={
                "atom_type": atom_type,
                "atom_id": atom_id
            }
        )
        await self.produce_event(event)
    
    async def emit_atom_completed(
        self,
        request_id: str,
        atom_type: str,
        atom_id: str,
        status: str,
        determination: Optional[str] = None,
        confidence: Optional[float] = None,
        latency_ms: float = 0,
        tokens_used: Optional[int] = None,
        correlation_id: Optional[str] = None
    ):
        """Emit atom completed event."""
        event = AtomCompletedEvent(
            request_id=request_id,
            correlation_id=correlation_id,
            source_component=atom_type,
            source_zone=BlackboardZone.ATOM_REASONING.value,
            payload={
                "atom_type": atom_type,
                "atom_id": atom_id,
                "status": status,
                "determination": determination,
                "confidence": confidence,
                "latency_ms": latency_ms,
                "tokens_used": tokens_used
            }
        )
        await self.produce_event(event)
    
    async def emit_synthesis_completed(
        self,
        request_id: str,
        status: str,
        primary_mechanism: Optional[str] = None,
        mechanism_confidence: Optional[float] = None,
        conflicts_resolved: int = 0,
        latency_ms: float = 0,
        correlation_id: Optional[str] = None
    ):
        """Emit synthesis completed event."""
        event = SynthesisCompletedEvent(
            request_id=request_id,
            correlation_id=correlation_id,
            source_component="synthesis",
            source_zone=BlackboardZone.SYNTHESIS_WORKSPACE.value,
            payload={
                "status": status,
                "primary_mechanism": primary_mechanism,
                "mechanism_confidence": mechanism_confidence,
                "conflicts_resolved": conflicts_resolved,
                "latency_ms": latency_ms
            }
        )
        await self.produce_event(event)
    
    async def emit_decision_completed(
        self,
        request_id: str,
        decision_id: str,
        ad_id: str,
        tier: str,
        mechanism_used: str,
        latency_ms: float,
        within_budget: bool,
        correlation_id: Optional[str] = None
    ):
        """Emit decision completed event."""
        event = DecisionCompletedEvent(
            request_id=request_id,
            correlation_id=correlation_id,
            source_component="decision",
            source_zone=BlackboardZone.DECISION_STATE.value,
            payload={
                "decision_id": decision_id,
                "ad_id": ad_id,
                "tier": tier,
                "mechanism_used": mechanism_used,
                "latency_ms": latency_ms,
                "within_budget": within_budget
            }
        )
        await self.produce_event(event)
    
    async def emit_learning_signal(
        self,
        request_id: str,
        signal: LearningSignal,
        correlation_id: Optional[str] = None
    ):
        """Emit learning signal event."""
        event = LearningSignalEmittedEvent(
            request_id=request_id,
            correlation_id=correlation_id,
            source_component=signal.source_component,
            source_zone=BlackboardZone.LEARNING_SIGNALS.value,
            payload={
                "signal_type": signal.signal_type.value,
                "signal_id": signal.signal_id,
                "source_component": signal.source_component,
                "priority": signal.priority.value
            }
        )
        await self.produce_event(event)
    
    async def emit_outcome_received(
        self,
        outcome: OutcomeSignal,
        correlation_id: Optional[str] = None
    ):
        """Emit outcome received event."""
        event = OutcomeReceivedEvent(
            request_id=outcome.request_id,
            correlation_id=correlation_id,
            source_component="outcome_collector",
            source_zone=BlackboardZone.LEARNING_SIGNALS.value,
            payload={
                "outcome_type": outcome.outcome_type.value,
                "outcome_value": outcome.outcome_value,
                "decision_id": outcome.decision_id,
                "delay_seconds": outcome.delay_seconds,
                "mechanism_used": outcome.mechanism_used
            }
        )
        await self.produce_event(event)
```

---

## Component Coordination Events

```python
"""
ADAM Enhancement #02: Component Coordination via Events
Event-driven coordination between components.
"""


class ComponentCoordinator:
    """
    Coordinates components using blackboard events.
    Enables reactive patterns where components respond to state changes.
    """
    
    def __init__(
        self,
        blackboard_service: BlackboardService,
        event_producer: BlackboardEventProducer,
        pubsub_manager: PubSubManager
    ):
        self.blackboard = blackboard_service
        self.producer = event_producer
        self.pubsub = pubsub_manager
        
        # Register coordination handlers
        self._setup_handlers()
    
    def _setup_handlers(self):
        """Set up event handlers for coordination."""
        # When atom completes, check if all atoms are done
        self.pubsub.register_handler(
            RedisKeySchema.PUBSUB_ATOM_COMPLETE,
            self._handle_atom_complete
        )
        
        # When synthesis completes, trigger decision
        self.pubsub.register_handler(
            RedisKeySchema.PUBSUB_SYNTHESIS_COMPLETE,
            self._handle_synthesis_complete
        )
        
        # When decision completes, trigger learning
        self.pubsub.register_handler(
            RedisKeySchema.PUBSUB_DECISION_COMPLETE,
            self._handle_decision_complete
        )
    
    async def _handle_atom_complete(self, event: BlackboardEvent):
        """Handle atom completion - check if ready for synthesis."""
        request_id = event.request_id
        
        # Get synthesis workspace
        workspace = await self.blackboard.get_synthesis_workspace(request_id)
        if not workspace:
            return
        
        # Update atoms received
        atom_type = event.payload.get('atom_type')
        if atom_type and atom_type not in workspace.atoms_received:
            workspace.atoms_received.append(atom_type)
            if atom_type in workspace.atoms_pending:
                workspace.atoms_pending.remove(atom_type)
            
            await self.blackboard.update_synthesis_workspace(
                request_id=request_id,
                updates={
                    'atoms_received': workspace.atoms_received,
                    'atoms_pending': workspace.atoms_pending
                }
            )
        
        # Check if all atoms are done
        if len(workspace.atoms_pending) == 0:
            logger.info(f"All atoms complete for request {request_id}, synthesis can proceed")
            
            # Emit coordination event
            await self.pubsub.publish(BlackboardEvent(
                event_type=BlackboardEventType.STATE_UPDATE,
                request_id=request_id,
                zone=BlackboardZone.SYNTHESIS_WORKSPACE,
                component="coordinator",
                payload={"ready_for_synthesis": True}
            ))
    
    async def _handle_synthesis_complete(self, event: BlackboardEvent):
        """Handle synthesis completion - trigger decision."""
        request_id = event.request_id
        
        if event.payload.get('success'):
            logger.info(f"Synthesis complete for {request_id}, decision can proceed")
            
            # Get synthesis recommendation
            workspace = await self.blackboard.get_synthesis_workspace(request_id)
            if workspace and workspace.recommendation:
                # Update decision state with synthesis info
                await self.blackboard.update_decision_state(
                    request_id=request_id,
                    updates={
                        'primary_mechanism': workspace.recommendation.primary_mechanism,
                        'mechanism_confidence': workspace.recommendation.recommendation_confidence
                    }
                )
    
    async def _handle_decision_complete(self, event: BlackboardEvent):
        """Handle decision completion - set up learning."""
        request_id = event.request_id
        
        # Build attribution context
        decision = await self.blackboard.get_decision_state(request_id)
        if not decision:
            return
        
        # Collect zone snapshots for attribution
        attribution_context = await self._build_attribution_context(request_id)
        await self.blackboard.save_attribution_context(attribution_context)
        
        logger.info(f"Attribution context saved for {request_id}")
    
    async def _build_attribution_context(
        self,
        request_id: str
    ) -> AttributionContext:
        """Build complete attribution context from all zones."""
        # Get all state
        context = await self.blackboard.get_request_context(request_id)
        atoms = await self.blackboard.get_all_atom_spaces(request_id)
        synthesis = await self.blackboard.get_synthesis_workspace(request_id)
        decision = await self.blackboard.get_decision_state(request_id)
        sources = await self.blackboard.get_intelligence_sources_snapshot(request_id)
        
        # Build attribution context
        return AttributionContext(
            request_id=request_id,
            decision_id=decision.decision_id if decision else "",
            user_id=context.user.user_id if context else "",
            zone1_snapshot=context.dict() if context else {},
            zone2_summary={
                k.value: {
                    'determination': v.output.determination if v.output else None,
                    'confidence': v.output.confidence if v.output else None
                }
                for k, v in atoms.items()
            },
            zone3_summary=synthesis.dict() if synthesis else {},
            zone4_snapshot=decision.dict() if decision else {},
            mechanism_used=decision.primary_mechanism if decision else "",
            mechanism_confidence=decision.mechanism_confidence if decision else 0.0,
            ad_selected=decision.selected_ad.ad_id if decision and decision.selected_ad else "",
            ad_selection_score=decision.selected_ad.selection_score if decision and decision.selected_ad else 0.0,
            decision_tier=decision.decision_tier.value if decision and decision.decision_tier else "",
            decision_timestamp=decision.completed_at or datetime.utcnow(),
            source_contributions={
                s.value: c.dict() for s, c in 
                (sources.get_all_contributions() if sources else [])
            } if sources else {}
        )


class AtomCoordinator:
    """
    Coordinates parallel atom execution.
    Enables atoms to observe and react to each other.
    """
    
    def __init__(
        self,
        blackboard_service: BlackboardService,
        pubsub_manager: PubSubManager
    ):
        self.blackboard = blackboard_service
        self.pubsub = pubsub_manager
        self._signal_handlers: Dict[str, List[callable]] = {}
    
    def register_signal_handler(
        self,
        signal_type: str,
        handler: callable
    ):
        """Register a handler for a specific signal type."""
        if signal_type not in self._signal_handlers:
            self._signal_handlers[signal_type] = []
        self._signal_handlers[signal_type].append(handler)
    
    async def observe_signals(
        self,
        request_id: str,
        signal_types: List[str],
        timeout_seconds: float = 5.0
    ) -> List[PreliminarySignal]:
        """
        Observe signals from other atoms within timeout.
        Used by atoms that want to coordinate with others.
        """
        observed = []
        end_time = datetime.utcnow() + timedelta(seconds=timeout_seconds)
        
        while datetime.utcnow() < end_time:
            signals = await self.blackboard.get_preliminary_signals(
                request_id=request_id,
                signal_type=None
            )
            
            new_signals = [
                s for s in signals 
                if s.signal_type in signal_types and s.signal_id not in [o.signal_id for o in observed]
            ]
            
            if new_signals:
                observed.extend(new_signals)
                
                # Call handlers
                for signal in new_signals:
                    handlers = self._signal_handlers.get(signal.signal_type, [])
                    for handler in handlers:
                        await handler(signal)
            
            await asyncio.sleep(0.1)
        
        return observed
    
    async def wait_for_signal(
        self,
        request_id: str,
        signal_type: str,
        timeout_seconds: float = 5.0
    ) -> Optional[PreliminarySignal]:
        """Wait for a specific signal type."""
        signals = await self.observe_signals(
            request_id=request_id,
            signal_types=[signal_type],
            timeout_seconds=timeout_seconds
        )
        return signals[0] if signals else None
```

---

## Learning Signal Routing

```python
"""
ADAM Enhancement #02: Learning Signal Routing
Routes learning signals to appropriate consumers.
"""


class LearningSignalRouter:
    """
    Routes learning signals to Gradient Bridge and other consumers.
    Integrates with Enhancement #06 (Gradient Bridge).
    """
    
    def __init__(
        self,
        blackboard_service: BlackboardService,
        event_producer: BlackboardEventProducer,
        gradient_bridge: Optional['GradientBridge'] = None  # From Enhancement #06
    ):
        self.blackboard = blackboard_service
        self.producer = event_producer
        self.gradient_bridge = gradient_bridge
        
        # Signal type to consumer mapping
        self._consumers: Dict[LearningSignalType, List[callable]] = {}
    
    def register_consumer(
        self,
        signal_type: LearningSignalType,
        consumer: callable
    ):
        """Register a consumer for a signal type."""
        if signal_type not in self._consumers:
            self._consumers[signal_type] = []
        self._consumers[signal_type].append(consumer)
    
    async def route_signal(self, signal: LearningSignal):
        """Route a learning signal to all registered consumers."""
        # Store in blackboard
        await self.blackboard.emit_learning_signal(signal)
        
        # Produce to Kafka
        await self.producer.emit_learning_signal(
            request_id=signal.request_id,
            signal=signal
        )
        
        # Route to specific consumers
        consumers = self._consumers.get(signal.signal_type, [])
        for consumer in consumers:
            try:
                if asyncio.iscoroutinefunction(consumer):
                    await consumer(signal)
                else:
                    consumer(signal)
            except Exception as e:
                logger.error(f"Error in signal consumer: {e}")
        
        # Route to Gradient Bridge if available
        if self.gradient_bridge and signal.signal_type in [
            LearningSignalType.CONVERSION_OUTCOME,
            LearningSignalType.ENGAGEMENT_OUTCOME,
            LearningSignalType.MECHANISM_EFFECTIVENESS
        ]:
            await self._route_to_gradient_bridge(signal)
    
    async def _route_to_gradient_bridge(self, signal: LearningSignal):
        """Route signal to Gradient Bridge for attribution."""
        # Get attribution context
        attribution_context = await self.blackboard.get_attribution_context(
            signal.request_id
        )
        
        if attribution_context and self.gradient_bridge:
            await self.gradient_bridge.process_outcome(
                signal=signal,
                context=attribution_context
            )
    
    async def route_outcome(self, outcome: OutcomeSignal):
        """Route an outcome signal."""
        # Store in blackboard
        await self.blackboard.emit_outcome_signal(outcome)
        
        # Produce to Kafka
        await self.producer.emit_outcome_received(outcome)
        
        # Convert to learning signal and route
        learning_signal = LearningSignal(
            signal_type=LearningSignalType.CONVERSION_OUTCOME if outcome.outcome_type == OutcomeType.CONVERSION else LearningSignalType.ENGAGEMENT_OUTCOME,
            priority=SignalPriority.HIGH,
            source_component="outcome_collector",
            request_id=outcome.request_id,
            decision_id=outcome.decision_id,
            user_id=outcome.user_id,
            signal_value=outcome.outcome_value,
            signal_confidence=1.0,
            delay_seconds=outcome.delay_seconds
        )
        
        await self.route_signal(learning_signal)
    
    async def batch_route(self, batch: LearningSignalBatch):
        """Route a batch of signals."""
        # Process regular signals
        for signal in batch.signals:
            await self.route_signal(signal)
        
        # Process outcome signals
        for outcome in batch.outcome_signals:
            await self.route_outcome(outcome)
        
        # Process mechanism signals
        for mech_signal in batch.mechanism_signals:
            signal = LearningSignal(
                signal_type=LearningSignalType.MECHANISM_EFFECTIVENESS,
                priority=SignalPriority.NORMAL,
                source_component="mechanism_evaluator",
                request_id=mech_signal.request_id,
                user_id=mech_signal.user_id,
                signal_value={
                    "mechanism_id": mech_signal.mechanism_id,
                    "was_effective": mech_signal.was_effective,
                    "effectiveness_score": mech_signal.effectiveness_score
                }
            )
            await self.route_signal(signal)
```


# SECTION I: LANGGRAPH INTEGRATION

## Blackboard-Aware Node Pattern

```python
"""
ADAM Enhancement #02: LangGraph Integration
Patterns for blackboard-aware LangGraph nodes.
"""

from typing import Optional, Dict, Any, Callable, Awaitable
from langgraph.graph import StateGraph
from pydantic import BaseModel
import functools


class BlackboardAwareState(BaseModel):
    """
    Base state class for blackboard-aware LangGraph workflows.
    """
    
    # Request identification
    request_id: str
    user_id: str
    
    # Blackboard reference (not serialized)
    blackboard_service: Optional[Any] = None
    
    # Current zone states (optional caching)
    request_context: Optional[RequestContext] = None
    state_trait_snapshot: Optional[StateTraitSnapshot] = None
    
    # Processing state
    current_stage: str = "initialized"
    errors: List[str] = []
    
    class Config:
        arbitrary_types_allowed = True


def blackboard_node(
    zone_reads: List[BlackboardZone] = None,
    zone_writes: List[BlackboardZone] = None,
    component_name: str = "unknown"
):
    """
    Decorator for blackboard-aware LangGraph nodes.
    Handles automatic state injection and result writing.
    """
    def decorator(func: Callable[[BlackboardAwareState], Awaitable[BlackboardAwareState]]):
        @functools.wraps(func)
        async def wrapper(state: BlackboardAwareState) -> BlackboardAwareState:
            blackboard = state.blackboard_service
            
            if blackboard is None:
                raise ValueError("Blackboard service not available in state")
            
            # Pre-fetch required zone data
            if zone_reads:
                if BlackboardZone.REQUEST_CONTEXT in zone_reads:
                    if not state.request_context:
                        state.request_context = await blackboard.get_request_context(
                            state.request_id
                        )
            
            # Execute the node function
            try:
                result = await func(state)
                return result
            except Exception as e:
                state.errors.append(f"{component_name}: {str(e)}")
                raise
        
        return wrapper
    return decorator


class BlackboardNodeFactory:
    """
    Factory for creating blackboard-aware LangGraph nodes.
    """
    
    def __init__(self, blackboard_service: BlackboardService):
        self.blackboard = blackboard_service
    
    def create_atom_node(
        self,
        atom_type: AtomType,
        reasoning_func: Callable
    ):
        """Create a node for an atom."""
        
        @blackboard_node(
            zone_reads=[BlackboardZone.REQUEST_CONTEXT, BlackboardZone.ATOM_REASONING],
            zone_writes=[BlackboardZone.ATOM_REASONING],
            component_name=atom_type.value
        )
        async def atom_node(state: BlackboardAwareState) -> BlackboardAwareState:
            # Create atom space
            await self.blackboard.create_atom_space(
                request_id=state.request_id,
                atom_type=atom_type,
                component=atom_type.value
            )
            
            # Update status to reasoning
            await self.blackboard.update_atom_space(
                request_id=state.request_id,
                atom_type=atom_type,
                updates={
                    'status': AtomStatus.REASONING,
                    'started_at': datetime.utcnow()
                },
                component=atom_type.value
            )
            
            # Execute reasoning
            output, trace = await reasoning_func(
                state.request_context,
                state.state_trait_snapshot,
                self.blackboard,
                state.request_id
            )
            
            # Complete atom
            await self.blackboard.complete_atom(
                request_id=state.request_id,
                atom_type=atom_type,
                output=output,
                trace=trace,
                component=atom_type.value
            )
            
            return state
        
        return atom_node
    
    def create_synthesis_node(
        self,
        synthesis_func: Callable
    ):
        """Create the synthesis node."""
        
        @blackboard_node(
            zone_reads=[BlackboardZone.REQUEST_CONTEXT, BlackboardZone.ATOM_REASONING],
            zone_writes=[BlackboardZone.SYNTHESIS_WORKSPACE],
            component_name="synthesis"
        )
        async def synthesis_node(state: BlackboardAwareState) -> BlackboardAwareState:
            # Get all atom outputs
            atom_spaces = await self.blackboard.get_all_atom_spaces(state.request_id)
            
            # Create synthesis workspace
            expected_atoms = [at.value for at in AtomType]
            await self.blackboard.create_synthesis_workspace(
                request_id=state.request_id,
                expected_atoms=expected_atoms
            )
            
            # Execute synthesis
            recommendation = await synthesis_func(
                state.request_context,
                atom_spaces,
                self.blackboard,
                state.request_id
            )
            
            # Complete synthesis
            await self.blackboard.complete_synthesis(
                request_id=state.request_id,
                recommendation=recommendation
            )
            
            return state
        
        return synthesis_node
    
    def create_decision_node(
        self,
        decision_func: Callable
    ):
        """Create the decision node."""
        
        @blackboard_node(
            zone_reads=[BlackboardZone.REQUEST_CONTEXT, BlackboardZone.SYNTHESIS_WORKSPACE],
            zone_writes=[BlackboardZone.DECISION_STATE],
            component_name="decision"
        )
        async def decision_node(state: BlackboardAwareState) -> BlackboardAwareState:
            # Get synthesis recommendation
            workspace = await self.blackboard.get_synthesis_workspace(state.request_id)
            
            # Create decision state
            await self.blackboard.create_decision_state(state.request_id)
            
            # Execute decision
            selected_ad, serving_details, latency, tier = await decision_func(
                state.request_context,
                workspace.recommendation,
                self.blackboard,
                state.request_id
            )
            
            # Complete decision
            await self.blackboard.complete_decision(
                request_id=state.request_id,
                selected_ad=selected_ad,
                serving_details=serving_details,
                latency_budget=latency,
                tier=tier
            )
            
            return state
        
        return decision_node
```

---

## State Injection Strategy

```python
"""
ADAM Enhancement #02: State Injection
Strategies for injecting blackboard state into LangGraph.
"""


class StateInjector:
    """
    Injects blackboard state into LangGraph workflows.
    """
    
    def __init__(self, blackboard_service: BlackboardService):
        self.blackboard = blackboard_service
    
    async def inject_request_context(
        self,
        state: BlackboardAwareState
    ) -> BlackboardAwareState:
        """Inject Zone 1 request context into state."""
        context = await self.blackboard.get_request_context(state.request_id)
        if context:
            state.request_context = context
        return state
    
    async def inject_state_trait_snapshot(
        self,
        state: BlackboardAwareState
    ) -> BlackboardAwareState:
        """
        Build and inject State × Trait snapshot.
        Combines graph priors with current state.
        """
        context = state.request_context
        if not context:
            return state
        
        # Build traits from graph priors
        traits = BigFiveProfile(
            openness=context.graph_priors.openness_prior[0],
            conscientiousness=context.graph_priors.conscientiousness_prior[0],
            extraversion=context.graph_priors.extraversion_prior[0],
            agreeableness=context.graph_priors.agreeableness_prior[0],
            neuroticism=context.graph_priors.neuroticism_prior[0],
            profile_stability=context.graph_priors.profile_confidence
        )
        
        # Get current state (would come from nonconscious signals in real implementation)
        current_state = MomentaryState()
        
        # Build snapshot
        snapshot = StateTraitSnapshot(
            request_id=state.request_id,
            user_id=context.user.user_id,
            traits=traits,
            current_state=current_state,
            effective_profile={
                "openness": traits.openness,
                "conscientiousness": traits.conscientiousness,
                "extraversion": traits.extraversion,
                "agreeableness": traits.agreeableness,
                "neuroticism": traits.neuroticism
            }
        )
        
        state.state_trait_snapshot = snapshot
        return state
    
    async def inject_preliminary_signals(
        self,
        state: BlackboardAwareState,
        for_atom: AtomType
    ) -> List[PreliminarySignal]:
        """
        Get relevant preliminary signals for an atom.
        Enables cross-atom coordination.
        """
        # Get all signals except from this atom
        all_signals = await self.blackboard.get_preliminary_signals(
            state.request_id,
            atom_type=None
        )
        
        # Filter out this atom's own signals
        return [s for s in all_signals if s.source_atom != for_atom.value]


class WorkflowStateBuilder:
    """
    Builds initial state for LangGraph workflows.
    """
    
    def __init__(
        self,
        blackboard_service: BlackboardService,
        state_injector: StateInjector
    ):
        self.blackboard = blackboard_service
        self.injector = state_injector
    
    async def build_initial_state(
        self,
        request_id: str,
        user_id: str,
        request_context: RequestContext
    ) -> BlackboardAwareState:
        """Build initial state for a workflow."""
        
        # Initialize Zone 1
        await self.blackboard.initialize_request(request_id, request_context)
        
        # Create state
        state = BlackboardAwareState(
            request_id=request_id,
            user_id=user_id,
            blackboard_service=self.blackboard,
            request_context=request_context,
            current_stage="initialized"
        )
        
        # Inject State × Trait snapshot
        state = await self.injector.inject_state_trait_snapshot(state)
        
        return state
```

---

## Workflow State Binding

```python
"""
ADAM Enhancement #02: Workflow State Binding
Binds blackboard state to LangGraph workflow execution.
"""


def create_adam_workflow(
    blackboard_service: BlackboardService,
    atom_reasoning_funcs: Dict[AtomType, Callable],
    synthesis_func: Callable,
    decision_func: Callable
) -> StateGraph:
    """
    Create the main ADAM LangGraph workflow with blackboard integration.
    """
    
    # Create node factory
    node_factory = BlackboardNodeFactory(blackboard_service)
    
    # Create workflow
    workflow = StateGraph(BlackboardAwareState)
    
    # Add initialization node
    async def init_node(state: BlackboardAwareState) -> BlackboardAwareState:
        state.current_stage = "atoms"
        return state
    
    workflow.add_node("initialize", init_node)
    
    # Add atom nodes
    for atom_type, reasoning_func in atom_reasoning_funcs.items():
        node = node_factory.create_atom_node(atom_type, reasoning_func)
        workflow.add_node(f"atom_{atom_type.value}", node)
    
    # Add synthesis node
    synthesis_node = node_factory.create_synthesis_node(synthesis_func)
    workflow.add_node("synthesis", synthesis_node)
    
    # Add decision node
    decision_node = node_factory.create_decision_node(decision_func)
    workflow.add_node("decision", decision_node)
    
    # Add edges
    workflow.set_entry_point("initialize")
    
    # Initialize -> All atoms (parallel)
    for atom_type in atom_reasoning_funcs.keys():
        workflow.add_edge("initialize", f"atom_{atom_type.value}")
    
    # All atoms -> Synthesis
    for atom_type in atom_reasoning_funcs.keys():
        workflow.add_edge(f"atom_{atom_type.value}", "synthesis")
    
    # Synthesis -> Decision
    workflow.add_edge("synthesis", "decision")
    
    return workflow.compile()


class WorkflowExecutor:
    """
    Executes LangGraph workflows with blackboard management.
    """
    
    def __init__(
        self,
        workflow: StateGraph,
        blackboard_service: BlackboardService,
        state_builder: WorkflowStateBuilder
    ):
        self.workflow = workflow
        self.blackboard = blackboard_service
        self.state_builder = state_builder
    
    async def execute(
        self,
        request_id: str,
        user_id: str,
        request_context: RequestContext
    ) -> Dict[str, Any]:
        """Execute workflow for a request."""
        
        # Build initial state
        initial_state = await self.state_builder.build_initial_state(
            request_id=request_id,
            user_id=user_id,
            request_context=request_context
        )
        
        try:
            # Execute workflow
            final_state = await self.workflow.ainvoke(initial_state)
            
            # Get final decision
            decision = await self.blackboard.get_decision_state(request_id)
            
            return {
                "success": True,
                "decision": decision.dict() if decision else None,
                "errors": final_state.errors
            }
            
        except Exception as e:
            # Record error
            return {
                "success": False,
                "decision": None,
                "errors": [str(e)]
            }
        
        finally:
            # Save attribution context for learning
            await self._save_attribution_context(request_id)
    
    async def _save_attribution_context(self, request_id: str):
        """Save attribution context from all zones."""
        snapshot = await self.blackboard.get_full_request_snapshot(request_id)
        
        decision = await self.blackboard.get_decision_state(request_id)
        if not decision:
            return
        
        context = AttributionContext(
            request_id=request_id,
            decision_id=decision.decision_id,
            user_id=snapshot['zones']['zone1_request_context'].get('user', {}).get('user_id', ''),
            zone1_snapshot=snapshot['zones']['zone1_request_context'],
            zone2_summary=snapshot['zones']['zone2_atoms'],
            zone3_summary=snapshot['zones']['zone3_synthesis'],
            zone4_snapshot=snapshot['zones']['zone4_decision'],
            mechanism_used=decision.primary_mechanism or "unknown",
            mechanism_confidence=decision.mechanism_confidence or 0,
            decision_timestamp=decision.completed_at or datetime.utcnow()
        )
        
        await self.blackboard.save_attribution_context(context, "workflow_executor")
```


# SECTION J: NEO4J SCHEMA

## State Persistence Nodes

```python
"""
ADAM Enhancement #02: Neo4j Schema
Graph schema for persisting blackboard state.
"""


# ============================================================================
# NEO4J NODE SCHEMAS
# ============================================================================

NEO4J_BLACKBOARD_SCHEMA = """
// ============================================================================
// BLACKBOARD SESSION NODES
// ============================================================================

// BlackboardSession - Represents a complete request processing session
CREATE CONSTRAINT blackboard_session_id IF NOT EXISTS
FOR (s:BlackboardSession) REQUIRE s.session_id IS UNIQUE;

// Schema for BlackboardSession node
// (:BlackboardSession {
//     session_id: String,           -- Same as request_id
//     user_id: String,
//     started_at: DateTime,
//     completed_at: DateTime,
//     duration_ms: Float,
//     decision_tier: String,
//     outcome_type: String,         -- Set when outcome received
//     outcome_value: Float,
//     success: Boolean
// })

// ============================================================================
// ZONE STATE SNAPSHOTS
// ============================================================================

// RequestContextSnapshot - Persisted Zone 1 state
CREATE CONSTRAINT request_context_id IF NOT EXISTS
FOR (r:RequestContextSnapshot) REQUIRE r.snapshot_id IS UNIQUE;

// (:RequestContextSnapshot {
//     snapshot_id: String,
//     request_id: String,
//     user_id: String,
//     content_id: String,
//     content_type: String,
//     device_type: String,
//     session_depth: Integer,
//     latency_budget_ms: Integer,
//     captured_at: DateTime
// })

// AtomReasoningSnapshot - Persisted Zone 2 atom state
CREATE CONSTRAINT atom_snapshot_id IF NOT EXISTS
FOR (a:AtomReasoningSnapshot) REQUIRE a.snapshot_id IS UNIQUE;

// (:AtomReasoningSnapshot {
//     snapshot_id: String,
//     request_id: String,
//     atom_type: String,
//     status: String,
//     determination: String,
//     primary_score: Float,
//     confidence: Float,
//     latency_ms: Float,
//     tokens_used: Integer,
//     started_at: DateTime,
//     completed_at: DateTime
// })

// SynthesisSnapshot - Persisted Zone 3 state
CREATE CONSTRAINT synthesis_snapshot_id IF NOT EXISTS
FOR (s:SynthesisSnapshot) REQUIRE s.snapshot_id IS UNIQUE;

// (:SynthesisSnapshot {
//     snapshot_id: String,
//     request_id: String,
//     status: String,
//     primary_mechanism: String,
//     mechanism_confidence: Float,
//     atoms_used: List<String>,
//     conflicts_detected: Integer,
//     conflicts_resolved: Integer,
//     latency_ms: Float,
//     completed_at: DateTime
// })

// DecisionSnapshot - Persisted Zone 4 state
CREATE CONSTRAINT decision_snapshot_id IF NOT EXISTS
FOR (d:DecisionSnapshot) REQUIRE d.decision_id IS UNIQUE;

// (:DecisionSnapshot {
//     decision_id: String,
//     request_id: String,
//     user_id: String,
//     ad_id: String,
//     campaign_id: String,
//     mechanism_used: String,
//     mechanism_confidence: Float,
//     decision_tier: String,
//     total_latency_ms: Float,
//     within_budget: Boolean,
//     completed_at: DateTime
// })

// ============================================================================
// LEARNING SIGNAL NODES
// ============================================================================

// LearningSignalNode - Persisted learning signal
CREATE CONSTRAINT learning_signal_id IF NOT EXISTS
FOR (l:LearningSignalNode) REQUIRE l.signal_id IS UNIQUE;

// (:LearningSignalNode {
//     signal_id: String,
//     request_id: String,
//     decision_id: String,
//     user_id: String,
//     signal_type: String,
//     signal_value: String,  -- JSON encoded
//     confidence: Float,
//     source_component: String,
//     timestamp: DateTime
// })

// OutcomeNode - Persisted outcome
CREATE CONSTRAINT outcome_id IF NOT EXISTS
FOR (o:OutcomeNode) REQUIRE o.outcome_id IS UNIQUE;

// (:OutcomeNode {
//     outcome_id: String,
//     request_id: String,
//     decision_id: String,
//     user_id: String,
//     ad_id: String,
//     outcome_type: String,
//     outcome_value: Float,
//     delay_seconds: Float,
//     mechanism_used: String,
//     outcome_timestamp: DateTime
// })

// ============================================================================
// REASONING TRACE NODES
// ============================================================================

// ReasoningTraceNode - Persisted reasoning trace for learning
CREATE CONSTRAINT reasoning_trace_id IF NOT EXISTS
FOR (r:ReasoningTraceNode) REQUIRE r.trace_id IS UNIQUE;

// (:ReasoningTraceNode {
//     trace_id: String,
//     request_id: String,
//     atom_type: String,
//     input_summary: String,
//     reasoning_steps: List<String>,
//     evidence_for: List<String>,
//     evidence_against: List<String>,
//     key_insights: List<String>,
//     self_assessed_quality: Float,
//     tokens_used: Integer
// })

// ============================================================================
// RELATIONSHIPS
// ============================================================================

// Session relationships
// (BlackboardSession)-[:HAS_CONTEXT]->(RequestContextSnapshot)
// (BlackboardSession)-[:HAS_ATOM_REASONING]->(AtomReasoningSnapshot)
// (BlackboardSession)-[:HAS_SYNTHESIS]->(SynthesisSnapshot)
// (BlackboardSession)-[:HAS_DECISION]->(DecisionSnapshot)
// (BlackboardSession)-[:HAS_OUTCOME]->(OutcomeNode)

// User relationships
// (User)-[:HAD_SESSION]->(BlackboardSession)
// (User)-[:RECEIVED_AD]->(DecisionSnapshot)
// (User)-[:PRODUCED_OUTCOME]->(OutcomeNode)

// Atom relationships
// (AtomReasoningSnapshot)-[:CONTRIBUTED_TO]->(SynthesisSnapshot)
// (AtomReasoningSnapshot)-[:HAS_TRACE]->(ReasoningTraceNode)

// Decision relationships
// (SynthesisSnapshot)-[:INFORMED]->(DecisionSnapshot)
// (DecisionSnapshot)-[:SELECTED]->(Ad)
// (DecisionSnapshot)-[:USED_MECHANISM]->(PsychologicalMechanism)

// Learning relationships
// (DecisionSnapshot)-[:PRODUCED_SIGNAL]->(LearningSignalNode)
// (DecisionSnapshot)-[:HAD_OUTCOME]->(OutcomeNode)
// (OutcomeNode)-[:ATTRIBUTED_TO]->(PsychologicalMechanism)

// ============================================================================
// INDEXES
// ============================================================================

CREATE INDEX blackboard_session_user IF NOT EXISTS
FOR (s:BlackboardSession) ON (s.user_id);

CREATE INDEX blackboard_session_time IF NOT EXISTS
FOR (s:BlackboardSession) ON (s.started_at);

CREATE INDEX decision_snapshot_user IF NOT EXISTS
FOR (d:DecisionSnapshot) ON (d.user_id);

CREATE INDEX decision_snapshot_time IF NOT EXISTS
FOR (d:DecisionSnapshot) ON (d.completed_at);

CREATE INDEX outcome_decision IF NOT EXISTS
FOR (o:OutcomeNode) ON (o.decision_id);

CREATE INDEX learning_signal_type IF NOT EXISTS
FOR (l:LearningSignalNode) ON (l.signal_type);
"""
```

---

## Session History Graph

```python
"""
ADAM Enhancement #02: Neo4j Session Persistence
Service for persisting blackboard sessions to Neo4j.
"""

from neo4j import AsyncGraphDatabase
from typing import Optional, Dict, Any, List
import json


class BlackboardNeo4jPersistence:
    """
    Persists blackboard state to Neo4j for historical analysis.
    """
    
    def __init__(self, uri: str, username: str, password: str):
        self.driver = AsyncGraphDatabase.driver(uri, auth=(username, password))
    
    async def close(self):
        await self.driver.close()
    
    async def persist_session(
        self,
        request_id: str,
        snapshot: Dict[str, Any]
    ):
        """Persist a complete session to Neo4j."""
        async with self.driver.session() as session:
            await session.execute_write(
                self._persist_session_tx,
                request_id,
                snapshot
            )
    
    @staticmethod
    async def _persist_session_tx(tx, request_id: str, snapshot: Dict[str, Any]):
        """Transaction for persisting session."""
        zones = snapshot.get('zones', {})
        
        # Create BlackboardSession node
        context = zones.get('zone1_request_context', {})
        decision = zones.get('zone4_decision', {})
        
        await tx.run("""
            MERGE (s:BlackboardSession {session_id: $request_id})
            SET s.user_id = $user_id,
                s.started_at = datetime($started_at),
                s.completed_at = datetime($completed_at),
                s.decision_tier = $decision_tier,
                s.success = $success
        """, {
            'request_id': request_id,
            'user_id': context.get('user', {}).get('user_id', ''),
            'started_at': snapshot.get('timestamp', ''),
            'completed_at': decision.get('completed_at', ''),
            'decision_tier': decision.get('decision_tier', ''),
            'success': decision.get('status') == 'complete'
        })
        
        # Create RequestContextSnapshot
        if context:
            await tx.run("""
                MATCH (s:BlackboardSession {session_id: $request_id})
                MERGE (r:RequestContextSnapshot {snapshot_id: $snapshot_id})
                SET r.request_id = $request_id,
                    r.user_id = $user_id,
                    r.content_id = $content_id,
                    r.content_type = $content_type,
                    r.device_type = $device_type,
                    r.session_depth = $session_depth
                MERGE (s)-[:HAS_CONTEXT]->(r)
            """, {
                'request_id': request_id,
                'snapshot_id': f"ctx_{request_id}",
                'user_id': context.get('user', {}).get('user_id', ''),
                'content_id': context.get('content', {}).get('content_id', ''),
                'content_type': context.get('content', {}).get('content_type', ''),
                'device_type': context.get('device_type', ''),
                'session_depth': context.get('session_depth', 1)
            })
        
        # Create AtomReasoningSnapshots
        atoms = zones.get('zone2_atoms', {})
        for atom_type, atom_data in atoms.items():
            if atom_data:
                await tx.run("""
                    MATCH (s:BlackboardSession {session_id: $request_id})
                    MERGE (a:AtomReasoningSnapshot {snapshot_id: $snapshot_id})
                    SET a.request_id = $request_id,
                        a.atom_type = $atom_type,
                        a.status = $status,
                        a.determination = $determination,
                        a.confidence = $confidence,
                        a.latency_ms = $latency_ms
                    MERGE (s)-[:HAS_ATOM_REASONING]->(a)
                """, {
                    'request_id': request_id,
                    'snapshot_id': f"atom_{atom_type}_{request_id}",
                    'atom_type': atom_type,
                    'status': atom_data.get('status', ''),
                    'determination': atom_data.get('output', {}).get('determination', ''),
                    'confidence': atom_data.get('output', {}).get('confidence', 0),
                    'latency_ms': atom_data.get('latency_ms', 0)
                })
        
        # Create SynthesisSnapshot
        synthesis = zones.get('zone3_synthesis', {})
        if synthesis:
            await tx.run("""
                MATCH (s:BlackboardSession {session_id: $request_id})
                MERGE (syn:SynthesisSnapshot {snapshot_id: $snapshot_id})
                SET syn.request_id = $request_id,
                    syn.status = $status,
                    syn.primary_mechanism = $primary_mechanism,
                    syn.mechanism_confidence = $mechanism_confidence,
                    syn.latency_ms = $latency_ms
                MERGE (s)-[:HAS_SYNTHESIS]->(syn)
            """, {
                'request_id': request_id,
                'snapshot_id': f"synth_{request_id}",
                'status': synthesis.get('status', ''),
                'primary_mechanism': synthesis.get('recommendation', {}).get('primary_mechanism', ''),
                'mechanism_confidence': synthesis.get('recommendation', {}).get('recommendation_confidence', 0),
                'latency_ms': synthesis.get('latency_ms', 0)
            })
        
        # Create DecisionSnapshot
        if decision:
            await tx.run("""
                MATCH (s:BlackboardSession {session_id: $request_id})
                MERGE (d:DecisionSnapshot {decision_id: $decision_id})
                SET d.request_id = $request_id,
                    d.user_id = $user_id,
                    d.ad_id = $ad_id,
                    d.mechanism_used = $mechanism_used,
                    d.decision_tier = $decision_tier,
                    d.total_latency_ms = $total_latency_ms,
                    d.within_budget = $within_budget
                MERGE (s)-[:HAS_DECISION]->(d)
            """, {
                'request_id': request_id,
                'decision_id': decision.get('decision_id', ''),
                'user_id': context.get('user', {}).get('user_id', ''),
                'ad_id': decision.get('selected_ad', {}).get('ad_id', ''),
                'mechanism_used': decision.get('primary_mechanism', ''),
                'decision_tier': decision.get('decision_tier', ''),
                'total_latency_ms': decision.get('latency_budget', {}).get('total_used_ms', 0),
                'within_budget': decision.get('latency_budget', {}).get('within_budget', True)
            })
    
    async def persist_outcome(
        self,
        outcome: OutcomeSignal
    ):
        """Persist an outcome to Neo4j."""
        async with self.driver.session() as session:
            await session.execute_write(
                self._persist_outcome_tx,
                outcome
            )
    
    @staticmethod
    async def _persist_outcome_tx(tx, outcome: OutcomeSignal):
        """Transaction for persisting outcome."""
        await tx.run("""
            MATCH (d:DecisionSnapshot {decision_id: $decision_id})
            MERGE (o:OutcomeNode {outcome_id: $outcome_id})
            SET o.request_id = $request_id,
                o.decision_id = $decision_id,
                o.user_id = $user_id,
                o.ad_id = $ad_id,
                o.outcome_type = $outcome_type,
                o.outcome_value = $outcome_value,
                o.delay_seconds = $delay_seconds,
                o.mechanism_used = $mechanism_used,
                o.outcome_timestamp = datetime($outcome_timestamp)
            MERGE (d)-[:HAD_OUTCOME]->(o)
            
            WITH o
            MATCH (s:BlackboardSession {session_id: $request_id})
            SET s.outcome_type = $outcome_type,
                s.outcome_value = $outcome_value
        """, {
            'outcome_id': outcome.signal_id,
            'request_id': outcome.request_id,
            'decision_id': outcome.decision_id,
            'user_id': outcome.user_id,
            'ad_id': outcome.ad_id,
            'outcome_type': outcome.outcome_type.value,
            'outcome_value': outcome.outcome_value,
            'delay_seconds': outcome.delay_seconds,
            'mechanism_used': outcome.mechanism_used,
            'outcome_timestamp': outcome.outcome_timestamp.isoformat()
        })
```

---

## Temporal Query Patterns

```python
"""
ADAM Enhancement #02: Neo4j Query Patterns
Query patterns for blackboard historical analysis.
"""


class BlackboardQueryPatterns:
    """
    Common query patterns for blackboard historical data.
    """
    
    @staticmethod
    def get_user_session_history(user_id: str, limit: int = 100) -> str:
        """Get a user's session history."""
        return """
            MATCH (s:BlackboardSession {user_id: $user_id})
            OPTIONAL MATCH (s)-[:HAS_DECISION]->(d:DecisionSnapshot)
            OPTIONAL MATCH (s)-[:HAS_OUTCOME]->(o:OutcomeNode)
            RETURN s, d, o
            ORDER BY s.started_at DESC
            LIMIT $limit
        """
    
    @staticmethod
    def get_mechanism_effectiveness_over_time(mechanism_id: str) -> str:
        """Get mechanism effectiveness over time."""
        return """
            MATCH (d:DecisionSnapshot {mechanism_used: $mechanism_id})
            OPTIONAL MATCH (d)-[:HAD_OUTCOME]->(o:OutcomeNode)
            RETURN 
                date(d.completed_at) as decision_date,
                count(d) as total_decisions,
                count(CASE WHEN o.outcome_type IN ['conversion', 'engagement'] THEN 1 END) as successful,
                avg(o.outcome_value) as avg_value
            ORDER BY decision_date
        """
    
    @staticmethod
    def get_atom_performance_analysis() -> str:
        """Analyze atom performance across sessions."""
        return """
            MATCH (a:AtomReasoningSnapshot)
            RETURN 
                a.atom_type as atom_type,
                count(a) as total_executions,
                avg(a.latency_ms) as avg_latency,
                avg(a.confidence) as avg_confidence,
                percentileDisc(a.latency_ms, 0.95) as p95_latency
            ORDER BY atom_type
        """
    
    @staticmethod
    def get_decision_tier_distribution() -> str:
        """Get distribution of decision tiers."""
        return """
            MATCH (d:DecisionSnapshot)
            RETURN 
                d.decision_tier as tier,
                count(d) as count,
                avg(d.total_latency_ms) as avg_latency,
                sum(CASE WHEN d.within_budget THEN 1 ELSE 0 END) as within_budget_count
            ORDER BY tier
        """
    
    @staticmethod
    def get_learning_signal_summary(time_window_hours: int = 24) -> str:
        """Get summary of learning signals."""
        return """
            MATCH (l:LearningSignalNode)
            WHERE l.timestamp > datetime() - duration({hours: $hours})
            RETURN 
                l.signal_type as signal_type,
                count(l) as count,
                avg(l.confidence) as avg_confidence
            ORDER BY count DESC
        """
    
    @staticmethod
    def get_attribution_chain(decision_id: str) -> str:
        """Get the full attribution chain for a decision."""
        return """
            MATCH (d:DecisionSnapshot {decision_id: $decision_id})
            OPTIONAL MATCH (s:BlackboardSession)-[:HAS_DECISION]->(d)
            OPTIONAL MATCH (s)-[:HAS_CONTEXT]->(ctx:RequestContextSnapshot)
            OPTIONAL MATCH (s)-[:HAS_ATOM_REASONING]->(a:AtomReasoningSnapshot)
            OPTIONAL MATCH (s)-[:HAS_SYNTHESIS]->(syn:SynthesisSnapshot)
            OPTIONAL MATCH (d)-[:HAD_OUTCOME]->(o:OutcomeNode)
            RETURN s, ctx, collect(a) as atoms, syn, d, o
        """
```

---

# SECTION K: FASTAPI ENDPOINTS

## State Query API

```python
"""
ADAM Enhancement #02: FastAPI Endpoints
REST API for blackboard operations.
"""

from fastapi import FastAPI, HTTPException, Depends, Query, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import Optional, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


# Create FastAPI app
app = FastAPI(
    title="ADAM Blackboard API",
    description="API for ADAM's Shared State Blackboard Architecture",
    version="2.0.0"
)


# Dependency for blackboard service
async def get_blackboard() -> BlackboardService:
    """Dependency injection for blackboard service."""
    # This would be configured at app startup
    from adam.blackboard import blackboard_service
    return blackboard_service


# ============================================================================
# ZONE 1: REQUEST CONTEXT ENDPOINTS
# ============================================================================

@app.get("/api/v1/blackboard/requests/{request_id}/context")
async def get_request_context(
    request_id: str,
    blackboard: BlackboardService = Depends(get_blackboard)
):
    """Get the request context for a request."""
    context = await blackboard.get_request_context(request_id)
    if not context:
        raise HTTPException(status_code=404, detail="Request context not found")
    return context.dict()


# ============================================================================
# ZONE 2: ATOM REASONING ENDPOINTS
# ============================================================================

@app.get("/api/v1/blackboard/requests/{request_id}/atoms")
async def get_all_atoms(
    request_id: str,
    blackboard: BlackboardService = Depends(get_blackboard)
):
    """Get all atom reasoning spaces for a request."""
    atoms = await blackboard.get_all_atom_spaces(request_id)
    return {k.value: v.dict() for k, v in atoms.items()}


@app.get("/api/v1/blackboard/requests/{request_id}/atoms/{atom_type}")
async def get_atom_space(
    request_id: str,
    atom_type: str,
    blackboard: BlackboardService = Depends(get_blackboard)
):
    """Get a specific atom's reasoning space."""
    try:
        at = AtomType(atom_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid atom type: {atom_type}")
    
    space = await blackboard.get_atom_space(request_id, at)
    if not space:
        raise HTTPException(status_code=404, detail="Atom space not found")
    return space.dict()


@app.get("/api/v1/blackboard/requests/{request_id}/signals")
async def get_preliminary_signals(
    request_id: str,
    atom_type: Optional[str] = Query(None),
    signal_type: Optional[str] = Query(None),
    blackboard: BlackboardService = Depends(get_blackboard)
):
    """Get preliminary signals from atoms."""
    at = None
    if atom_type:
        try:
            at = AtomType(atom_type)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid atom type: {atom_type}")
    
    signals = await blackboard.get_preliminary_signals(
        request_id=request_id,
        atom_type=at,
        signal_type=signal_type
    )
    return [s.dict() for s in signals]


# ============================================================================
# ZONE 3: SYNTHESIS ENDPOINTS
# ============================================================================

@app.get("/api/v1/blackboard/requests/{request_id}/synthesis")
async def get_synthesis_workspace(
    request_id: str,
    blackboard: BlackboardService = Depends(get_blackboard)
):
    """Get the synthesis workspace for a request."""
    workspace = await blackboard.get_synthesis_workspace(request_id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Synthesis workspace not found")
    return workspace.dict()


# ============================================================================
# ZONE 4: DECISION ENDPOINTS
# ============================================================================

@app.get("/api/v1/blackboard/requests/{request_id}/decision")
async def get_decision_state(
    request_id: str,
    blackboard: BlackboardService = Depends(get_blackboard)
):
    """Get the decision state for a request."""
    decision = await blackboard.get_decision_state(request_id)
    if not decision:
        raise HTTPException(status_code=404, detail="Decision state not found")
    return decision.dict()


# ============================================================================
# ZONE 5: LEARNING SIGNALS ENDPOINTS
# ============================================================================

@app.get("/api/v1/blackboard/requests/{request_id}/learning-signals")
async def get_learning_signals(
    request_id: str,
    signal_type: Optional[str] = Query(None),
    blackboard: BlackboardService = Depends(get_blackboard)
):
    """Get learning signals for a request."""
    st = None
    if signal_type:
        try:
            st = LearningSignalType(signal_type)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid signal type: {signal_type}")
    
    signals = await blackboard.get_learning_signals(request_id, st)
    return [s.dict() for s in signals]


@app.get("/api/v1/blackboard/requests/{request_id}/attribution")
async def get_attribution_context(
    request_id: str,
    blackboard: BlackboardService = Depends(get_blackboard)
):
    """Get attribution context for a request."""
    context = await blackboard.get_attribution_context(request_id)
    if not context:
        raise HTTPException(status_code=404, detail="Attribution context not found")
    return context.dict()


# ============================================================================
# CROSS-ZONE ENDPOINTS
# ============================================================================

@app.get("/api/v1/blackboard/requests/{request_id}/snapshot")
async def get_full_snapshot(
    request_id: str,
    blackboard: BlackboardService = Depends(get_blackboard)
):
    """Get a complete snapshot of all zones for a request."""
    snapshot = await blackboard.get_full_request_snapshot(request_id)
    return snapshot
```

---

## Admin & Debug API

```python
"""
ADAM Enhancement #02: Admin & Debug Endpoints
"""

# ============================================================================
# ADMIN ENDPOINTS
# ============================================================================

@app.delete("/api/v1/blackboard/requests/{request_id}")
async def cleanup_request(
    request_id: str,
    blackboard: BlackboardService = Depends(get_blackboard)
):
    """Clean up all data for a request."""
    await blackboard.cleanup_request(request_id)
    return {"status": "cleaned", "request_id": request_id}


@app.get("/api/v1/blackboard/admin/pool-stats")
async def get_pool_stats(
    blackboard: BlackboardService = Depends(get_blackboard)
):
    """Get Redis pool statistics."""
    stats = await blackboard.pool.get_pool_stats()
    return stats


@app.get("/api/v1/blackboard/admin/zone-config")
async def get_zone_config(
    blackboard: BlackboardService = Depends(get_blackboard)
):
    """Get zone configurations."""
    return {
        zone.value: config.dict()
        for zone, config in blackboard.config.zones.items()
    }


# ============================================================================
# DEBUG ENDPOINTS
# ============================================================================

@app.get("/api/v1/blackboard/debug/requests/{request_id}/keys")
async def get_request_keys(
    request_id: str,
    blackboard: BlackboardService = Depends(get_blackboard)
):
    """Get all Redis keys for a request (debug)."""
    index_key = RedisKeySchema.request_index_key(request_id)
    keys = await blackboard.pool.main_client.smembers(index_key)
    return {
        "request_id": request_id,
        "key_count": len(keys),
        "keys": [k.decode() if isinstance(k, bytes) else k for k in keys]
    }


@app.get("/api/v1/blackboard/debug/requests/{request_id}/ttls")
async def get_request_ttls(
    request_id: str,
    blackboard: BlackboardService = Depends(get_blackboard)
):
    """Get TTLs for all keys of a request (debug)."""
    index_key = RedisKeySchema.request_index_key(request_id)
    keys = await blackboard.pool.main_client.smembers(index_key)
    
    ttls = {}
    for key in keys:
        key_str = key.decode() if isinstance(key, bytes) else key
        ttl = await blackboard.pool.main_client.ttl(key_str)
        ttls[key_str] = ttl
    
    return ttls


@app.post("/api/v1/blackboard/debug/simulate-atom")
async def simulate_atom_completion(
    request_id: str,
    atom_type: str,
    determination: str,
    confidence: float = Query(ge=0, le=1),
    blackboard: BlackboardService = Depends(get_blackboard)
):
    """Simulate an atom completion (debug/testing)."""
    try:
        at = AtomType(atom_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid atom type: {atom_type}")
    
    # Create atom space
    await blackboard.create_atom_space(request_id, at, "debug")
    
    # Complete with simulated output
    output = AtomOutput(
        determination=determination,
        primary_score=confidence,
        confidence=confidence,
        evidence_summary=["Simulated for testing"]
    )
    
    result = await blackboard.complete_atom(
        request_id=request_id,
        atom_type=at,
        output=output,
        component="debug"
    )
    
    return result.dict()
```

---

## Health & Metrics API

```python
"""
ADAM Enhancement #02: Health & Metrics Endpoints
"""

# ============================================================================
# HEALTH ENDPOINTS
# ============================================================================

@app.get("/api/v1/blackboard/health")
async def health_check(
    blackboard: BlackboardService = Depends(get_blackboard)
):
    """Check blackboard service health."""
    pool_health = await blackboard.pool.health_check()
    
    all_healthy = all(pool_health.values())
    
    return {
        "status": "healthy" if all_healthy else "degraded",
        "components": {
            "redis_pools": pool_health
        },
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/api/v1/blackboard/health/live")
async def liveness_probe():
    """Kubernetes liveness probe."""
    return {"status": "alive"}


@app.get("/api/v1/blackboard/health/ready")
async def readiness_probe(
    blackboard: BlackboardService = Depends(get_blackboard)
):
    """Kubernetes readiness probe."""
    try:
        pool_health = await blackboard.pool.health_check()
        if all(pool_health.values()):
            return {"status": "ready"}
        raise HTTPException(status_code=503, detail="Redis pools not healthy")
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


# ============================================================================
# METRICS ENDPOINT
# ============================================================================

@app.get("/api/v1/blackboard/metrics")
async def get_metrics(
    blackboard: BlackboardService = Depends(get_blackboard)
):
    """Get blackboard metrics summary."""
    if not blackboard.metrics:
        raise HTTPException(status_code=501, detail="Metrics not enabled")
    
    return blackboard.metrics.get_summary()
```

---

# SECTION L: PROMETHEUS METRICS

## State Access Metrics

```python
"""
ADAM Enhancement #02: Prometheus Metrics
Comprehensive metrics for blackboard monitoring.
"""

from prometheus_client import Counter, Histogram, Gauge, Summary
from typing import Optional
import time


class BlackboardMetrics:
    """
    Prometheus metrics for blackboard operations.
    """
    
    def __init__(self, prefix: str = "adam_blackboard"):
        self.prefix = prefix
        
        # ====================================================================
        # OPERATION COUNTERS
        # ====================================================================
        
        self.operations_total = Counter(
            f"{prefix}_operations_total",
            "Total blackboard operations",
            ["zone", "operation", "status"]
        )
        
        self.events_published_total = Counter(
            f"{prefix}_events_published_total",
            "Total events published",
            ["event_type", "zone"]
        )
        
        self.learning_signals_total = Counter(
            f"{prefix}_learning_signals_total",
            "Total learning signals emitted",
            ["signal_type"]
        )
        
        # ====================================================================
        # LATENCY HISTOGRAMS
        # ====================================================================
        
        self.operation_latency = Histogram(
            f"{prefix}_operation_latency_seconds",
            "Operation latency in seconds",
            ["zone", "operation"],
            buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0]
        )
        
        self.zone_read_latency = Histogram(
            f"{prefix}_zone_read_latency_seconds",
            "Zone read latency",
            ["zone"],
            buckets=[0.0005, 0.001, 0.005, 0.01, 0.025, 0.05]
        )
        
        self.zone_write_latency = Histogram(
            f"{prefix}_zone_write_latency_seconds",
            "Zone write latency",
            ["zone"],
            buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1]
        )
        
        # ====================================================================
        # SIZE HISTOGRAMS
        # ====================================================================
        
        self.entry_size_bytes = Histogram(
            f"{prefix}_entry_size_bytes",
            "Size of blackboard entries in bytes",
            ["zone"],
            buckets=[100, 500, 1000, 5000, 10000, 50000, 100000, 500000]
        )
        
        # ====================================================================
        # GAUGES
        # ====================================================================
        
        self.active_requests = Gauge(
            f"{prefix}_active_requests",
            "Number of active requests in blackboard"
        )
        
        self.redis_pool_connections = Gauge(
            f"{prefix}_redis_pool_connections",
            "Redis pool connection count",
            ["pool", "state"]
        )
        
        # ====================================================================
        # ATOM METRICS
        # ====================================================================
        
        self.atom_executions_total = Counter(
            f"{prefix}_atom_executions_total",
            "Total atom executions",
            ["atom_type", "status"]
        )
        
        self.atom_latency = Histogram(
            f"{prefix}_atom_latency_seconds",
            "Atom execution latency",
            ["atom_type"],
            buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0]
        )
        
        self.atom_confidence = Histogram(
            f"{prefix}_atom_confidence",
            "Atom output confidence distribution",
            ["atom_type"],
            buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
        )
        
        # ====================================================================
        # SYNTHESIS METRICS
        # ====================================================================
        
        self.synthesis_latency = Histogram(
            f"{prefix}_synthesis_latency_seconds",
            "Synthesis execution latency",
            buckets=[0.05, 0.1, 0.25, 0.5, 1.0, 2.5]
        )
        
        self.synthesis_conflicts = Histogram(
            f"{prefix}_synthesis_conflicts",
            "Number of conflicts in synthesis",
            buckets=[0, 1, 2, 3, 5, 10]
        )
        
        # ====================================================================
        # DECISION METRICS
        # ====================================================================
        
        self.decision_tier = Counter(
            f"{prefix}_decision_tier_total",
            "Decision tier distribution",
            ["tier"]
        )
        
        self.decision_latency = Histogram(
            f"{prefix}_decision_latency_seconds",
            "Total decision latency",
            buckets=[0.01, 0.025, 0.05, 0.075, 0.1, 0.15, 0.2]
        )
        
        self.latency_budget_utilization = Histogram(
            f"{prefix}_latency_budget_utilization",
            "Fraction of latency budget used",
            buckets=[0.1, 0.25, 0.5, 0.75, 0.9, 1.0, 1.25, 1.5]
        )
    
    # ========================================================================
    # RECORDING METHODS
    # ========================================================================
    
    def record_read(
        self,
        zone: BlackboardZone,
        latency_ms: float,
        cache_hit: bool
    ):
        """Record a read operation."""
        self.operations_total.labels(
            zone=zone.value,
            operation="read",
            status="hit" if cache_hit else "miss"
        ).inc()
        
        self.zone_read_latency.labels(zone=zone.value).observe(latency_ms / 1000)
    
    def record_write(
        self,
        zone: BlackboardZone,
        latency_ms: float,
        size_bytes: int
    ):
        """Record a write operation."""
        self.operations_total.labels(
            zone=zone.value,
            operation="write",
            status="success"
        ).inc()
        
        self.zone_write_latency.labels(zone=zone.value).observe(latency_ms / 1000)
        self.entry_size_bytes.labels(zone=zone.value).observe(size_bytes)
    
    def record_error(
        self,
        zone: BlackboardZone,
        operation: str
    ):
        """Record an error."""
        self.operations_total.labels(
            zone=zone.value,
            operation=operation,
            status="error"
        ).inc()
    
    def record_event_published(
        self,
        event_type: str,
        zone: BlackboardZone
    ):
        """Record an event publication."""
        self.events_published_total.labels(
            event_type=event_type,
            zone=zone.value
        ).inc()
    
    def record_learning_signal(
        self,
        signal_type: LearningSignalType
    ):
        """Record a learning signal."""
        self.learning_signals_total.labels(
            signal_type=signal_type.value
        ).inc()
    
    def record_atom_execution(
        self,
        atom_type: AtomType,
        status: AtomStatus,
        latency_ms: float,
        confidence: Optional[float] = None
    ):
        """Record atom execution metrics."""
        self.atom_executions_total.labels(
            atom_type=atom_type.value,
            status=status.value
        ).inc()
        
        self.atom_latency.labels(atom_type=atom_type.value).observe(latency_ms / 1000)
        
        if confidence is not None:
            self.atom_confidence.labels(atom_type=atom_type.value).observe(confidence)
    
    def record_synthesis(
        self,
        latency_ms: float,
        conflicts: int
    ):
        """Record synthesis metrics."""
        self.synthesis_latency.observe(latency_ms / 1000)
        self.synthesis_conflicts.observe(conflicts)
    
    def record_decision(
        self,
        tier: DecisionTier,
        latency_ms: float,
        budget_ms: int
    ):
        """Record decision metrics."""
        self.decision_tier.labels(tier=tier.value).inc()
        self.decision_latency.observe(latency_ms / 1000)
        self.latency_budget_utilization.observe(latency_ms / budget_ms)
    
    def get_summary(self) -> dict:
        """Get a summary of metrics (for API endpoint)."""
        # This would typically be read from Prometheus,
        # but we can provide a simple summary here
        return {
            "status": "metrics_enabled",
            "prefix": self.prefix
        }
```


# SECTION M: TESTING & OPERATIONS

## Unit Test Suite

```python
"""
ADAM Enhancement #02: Unit Tests
Comprehensive unit tests for blackboard components.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
import json


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def blackboard_config():
    """Create test blackboard configuration."""
    return BlackboardConfig(
        redis_url="redis://localhost:6379/15",  # Test database
        redis_pool_size=5,
        redis_timeout_seconds=1.0
    )


@pytest.fixture
async def mock_redis():
    """Create mock Redis client."""
    mock = AsyncMock()
    mock.get = AsyncMock(return_value=None)
    mock.setex = AsyncMock(return_value=True)
    mock.delete = AsyncMock(return_value=1)
    mock.exists = AsyncMock(return_value=0)
    mock.sadd = AsyncMock(return_value=1)
    mock.smembers = AsyncMock(return_value=set())
    mock.expire = AsyncMock(return_value=True)
    mock.ttl = AsyncMock(return_value=300)
    mock.ping = AsyncMock(return_value=True)
    mock.rpush = AsyncMock(return_value=1)
    mock.lrange = AsyncMock(return_value=[])
    return mock


@pytest.fixture
def sample_request_context():
    """Create sample request context."""
    return RequestContext(
        request_id="test_req_001",
        request_timestamp=datetime.utcnow(),
        request_source=RequestSource.INTERNAL_TEST,
        user=UserIdentifiers(
            user_id="user_001",
            session_id="session_001",
            is_known_user=True
        ),
        content=ContentContext(
            content_id="content_001",
            content_type=ContentType.AUDIO_PODCAST
        ),
        device_type=DeviceType.MOBILE_IOS,
        ad_candidates=[
            AdCandidateInfo(
                ad_id="ad_001",
                campaign_id="camp_001",
                advertiser_id="adv_001",
                ad_format="audio_30s"
            )
        ],
        local_hour=14,
        local_day_of_week=2
    )


@pytest.fixture
def sample_atom_output():
    """Create sample atom output."""
    return AtomOutput(
        determination="promotion",
        primary_score=0.75,
        confidence=0.82,
        evidence_summary=["User showed approach behavior", "Content is positive"],
        mechanism_recommendation="social_proof"
    )


# ============================================================================
# PYDANTIC MODEL TESTS
# ============================================================================

class TestPydanticModels:
    """Test Pydantic model validation."""
    
    def test_request_context_validation(self, sample_request_context):
        """Test RequestContext validation."""
        assert sample_request_context.request_id == "test_req_001"
        assert sample_request_context.user.user_id == "user_001"
        assert len(sample_request_context.ad_candidates) == 1
    
    def test_request_context_invalid_candidates(self):
        """Test that too many candidates raises error."""
        with pytest.raises(ValueError):
            RequestContext(
                request_id="test",
                request_source=RequestSource.INTERNAL_TEST,
                user=UserIdentifiers(user_id="u1", session_id="s1"),
                content=ContentContext(content_id="c1", content_type=ContentType.AUDIO_PODCAST),
                device_type=DeviceType.MOBILE_IOS,
                ad_candidates=[
                    AdCandidateInfo(
                        ad_id=f"ad_{i}",
                        campaign_id="c1",
                        advertiser_id="a1",
                        ad_format="audio_30s"
                    ) for i in range(51)  # 51 > 50 limit
                ],
                local_hour=12,
                local_day_of_week=1
            )
    
    def test_atom_output_validation(self, sample_atom_output):
        """Test AtomOutput validation."""
        assert sample_atom_output.determination == "promotion"
        assert 0 <= sample_atom_output.confidence <= 1
    
    def test_atom_status_transitions(self):
        """Test valid and invalid status transitions."""
        engine = StateTransitionEngine()
        
        # Valid transitions
        assert engine.validate_atom_transition(AtomStatus.PENDING, AtomStatus.INITIALIZING)
        assert engine.validate_atom_transition(AtomStatus.REASONING, AtomStatus.COMPLETE)
        
        # Invalid transitions
        assert not engine.validate_atom_transition(AtomStatus.COMPLETE, AtomStatus.PENDING)
        assert not engine.validate_atom_transition(AtomStatus.ERROR, AtomStatus.REASONING)
    
    def test_preliminary_signal_creation(self):
        """Test PreliminarySignal creation."""
        signal = PreliminarySignal(
            signal_type="arousal_detection",
            signal_value="high",
            confidence=0.85,
            evidence=["rapid_clicks", "short_dwell"],
            source_atom="regulatory_focus",
            requires_attention=True,
            attention_reason="High arousal may affect construal"
        )
        
        assert signal.signal_id is not None
        assert signal.requires_attention is True


# ============================================================================
# REDIS KEY SCHEMA TESTS
# ============================================================================

class TestRedisKeySchema:
    """Test Redis key generation."""
    
    def test_zone1_key(self):
        """Test Zone 1 key generation."""
        key = RedisKeySchema.zone1_key("req_001")
        assert key == "bb:z1:req:req_001:context"
    
    def test_zone2_atom_key(self):
        """Test Zone 2 atom key generation."""
        key = RedisKeySchema.zone2_atom_key("req_001", "regulatory_focus", "space")
        assert key == "bb:z2:atom:req_001:regulatory_focus:space"
    
    def test_zone5_signals_key(self):
        """Test Zone 5 signals key generation."""
        key = RedisKeySchema.zone5_signals_key("req_001")
        assert key == "bb:z5:learn:req_001:signals"
    
    def test_get_zone_from_key(self):
        """Test zone extraction from key."""
        assert RedisKeySchema.get_zone_from_key("bb:z1:req:x:context") == "zone1"
        assert RedisKeySchema.get_zone_from_key("bb:z2:atom:x:y:space") == "zone2"
        assert RedisKeySchema.get_zone_from_key("bb:z3:synth:x:workspace") == "zone3"
        assert RedisKeySchema.get_zone_from_key("bb:z4:dec:x:state") == "zone4"
        assert RedisKeySchema.get_zone_from_key("bb:z5:learn:x:signals") == "zone5"
        assert RedisKeySchema.get_zone_from_key("unknown:key") is None


# ============================================================================
# SERIALIZATION TESTS
# ============================================================================

class TestSerialization:
    """Test serialization and deserialization."""
    
    def test_serialize_without_compression(self, blackboard_config, sample_request_context):
        """Test serialization without compression."""
        zone_config = blackboard_config.zones[BlackboardZone.REQUEST_CONTEXT]
        serializer = BlackboardSerializer(zone_config)
        
        serialized = serializer.serialize(sample_request_context)
        
        assert isinstance(serialized, bytes)
        assert not serializer.is_compressed(serialized)
    
    def test_serialize_with_compression(self, blackboard_config):
        """Test serialization with compression for large data."""
        zone_config = BlackboardZoneConfig(
            zone=BlackboardZone.ATOM_REASONING,
            redis_prefix="test:",
            default_ttl_seconds=300,
            compression_enabled=True,
            compression_threshold_bytes=100
        )
        serializer = BlackboardSerializer(zone_config)
        
        # Create large model
        large_trace = AtomReasoningTrace(
            input_context_summary="x" * 1000,
            reasoning_steps=["step " * 100 for _ in range(10)],
            evidence_for=["evidence " * 50 for _ in range(20)]
        )
        
        serialized = serializer.serialize(large_trace)
        
        # Should be compressed
        assert serializer.is_compressed(serialized)
    
    def test_roundtrip_serialization(self, blackboard_config, sample_request_context):
        """Test serialize then deserialize."""
        zone_config = blackboard_config.zones[BlackboardZone.REQUEST_CONTEXT]
        serializer = BlackboardSerializer(zone_config)
        
        # Create entry wrapper
        entry = BlackboardEntry(
            metadata=BlackboardMetadata(
                request_id="test",
                zone=BlackboardZone.REQUEST_CONTEXT,
                writer_component="test",
                ttl_seconds=300
            ),
            data=sample_request_context
        )
        
        serialized = serializer.serialize(entry)
        deserialized = serializer.deserialize(serialized, BlackboardEntry[RequestContext])
        
        assert deserialized.data.request_id == sample_request_context.request_id
        assert deserialized.data.user.user_id == sample_request_context.user.user_id


# ============================================================================
# ZONE MANAGER TESTS
# ============================================================================

class TestZoneManager:
    """Test ZoneManager operations."""
    
    @pytest.mark.asyncio
    async def test_write_operation(self, mock_redis, blackboard_config, sample_request_context):
        """Test write operation."""
        zone_config = blackboard_config.zones[BlackboardZone.REQUEST_CONTEXT]
        serializer = BlackboardSerializer(zone_config)
        ttl_manager = TTLManager(blackboard_config, mock_redis)
        pubsub = MagicMock()
        pubsub.publish = AsyncMock()
        
        manager = ZoneManager(
            zone=BlackboardZone.REQUEST_CONTEXT,
            config=zone_config,
            redis_client=mock_redis,
            serializer=serializer,
            ttl_manager=ttl_manager,
            pubsub=pubsub
        )
        
        result = await manager.write(
            request_id="test_001",
            entry_key="context",
            data=sample_request_context,
            component="test"
        )
        
        assert result.success is True
        assert result.entry_id is not None
        mock_redis.setex.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_read_not_found(self, mock_redis, blackboard_config):
        """Test read operation when entry not found."""
        zone_config = blackboard_config.zones[BlackboardZone.REQUEST_CONTEXT]
        serializer = BlackboardSerializer(zone_config)
        ttl_manager = TTLManager(blackboard_config, mock_redis)
        pubsub = MagicMock()
        
        manager = ZoneManager(
            zone=BlackboardZone.REQUEST_CONTEXT,
            config=zone_config,
            redis_client=mock_redis,
            serializer=serializer,
            ttl_manager=ttl_manager,
            pubsub=pubsub
        )
        
        result = await manager.read(
            request_id="nonexistent",
            entry_key="context",
            model_class=RequestContext
        )
        
        assert result.found is False
        assert result.entry is None


# ============================================================================
# STATE TRANSITION TESTS
# ============================================================================

class TestStateTransitions:
    """Test state transition validation."""
    
    def test_valid_atom_transitions(self):
        """Test all valid atom transitions."""
        valid_paths = [
            [AtomStatus.PENDING, AtomStatus.INITIALIZING, AtomStatus.REASONING, AtomStatus.COMPLETE],
            [AtomStatus.PENDING, AtomStatus.INITIALIZING, AtomStatus.REASONING, AtomStatus.ERROR],
            [AtomStatus.PENDING, AtomStatus.SKIPPED],
        ]
        
        for path in valid_paths:
            for i in range(len(path) - 1):
                assert StateTransitionEngine.validate_atom_transition(path[i], path[i+1])
    
    def test_invalid_atom_transitions(self):
        """Test invalid atom transitions raise errors."""
        with pytest.raises(StateTransitionError):
            StateTransitionEngine.assert_atom_transition(
                AtomStatus.COMPLETE,
                AtomStatus.REASONING,
                "Cannot transition from terminal state"
            )
    
    def test_synthesis_transitions(self):
        """Test synthesis transitions."""
        assert StateTransitionEngine.validate_synthesis_transition(
            SynthesisStatus.WAITING_FOR_ATOMS,
            SynthesisStatus.AGGREGATING
        )
        assert not StateTransitionEngine.validate_synthesis_transition(
            SynthesisStatus.COMPLETE,
            SynthesisStatus.SYNTHESIZING
        )
```

---

## Integration Tests

```python
"""
ADAM Enhancement #02: Integration Tests
Tests with real Redis and simulated workflows.
"""

import pytest
import asyncio
from datetime import datetime


@pytest.fixture
async def real_blackboard_service():
    """Create real blackboard service for integration tests."""
    config = BlackboardConfig(
        redis_url="redis://localhost:6379/15",  # Test database
        redis_pool_size=5
    )
    
    pool_manager = RedisPoolManager(config)
    await pool_manager.initialize()
    
    serializer_factory = SerializerFactory(config)
    ttl_manager = TTLManager(config, pool_manager.main_client)
    pubsub_manager = PubSubManager(pool_manager.pubsub_client, config)
    await pubsub_manager.start()
    
    service = BlackboardService(
        config=config,
        pool_manager=pool_manager,
        serializer_factory=serializer_factory,
        ttl_manager=ttl_manager,
        pubsub_manager=pubsub_manager
    )
    await service.initialize()
    
    yield service
    
    # Cleanup
    await service.shutdown()


@pytest.mark.integration
class TestBlackboardIntegration:
    """Integration tests requiring real Redis."""
    
    @pytest.mark.asyncio
    async def test_full_request_lifecycle(self, real_blackboard_service):
        """Test complete request lifecycle through all zones."""
        blackboard = real_blackboard_service
        request_id = f"test_{datetime.utcnow().timestamp()}"
        
        try:
            # Zone 1: Initialize request
            context = RequestContext(
                request_id=request_id,
                request_source=RequestSource.INTERNAL_TEST,
                user=UserIdentifiers(user_id="test_user", session_id="test_session"),
                content=ContentContext(content_id="content_1", content_type=ContentType.AUDIO_PODCAST),
                device_type=DeviceType.MOBILE_IOS,
                ad_candidates=[
                    AdCandidateInfo(ad_id="ad_1", campaign_id="c1", advertiser_id="a1", ad_format="audio_30s")
                ],
                local_hour=12,
                local_day_of_week=2
            )
            
            result = await blackboard.initialize_request(request_id, context)
            assert result.success
            
            # Verify Zone 1
            retrieved_context = await blackboard.get_request_context(request_id)
            assert retrieved_context is not None
            assert retrieved_context.request_id == request_id
            
            # Zone 2: Create and complete atoms
            for atom_type in [AtomType.REGULATORY_FOCUS, AtomType.CONSTRUAL_LEVEL]:
                await blackboard.create_atom_space(request_id, atom_type, "test")
                
                output = AtomOutput(
                    determination="test_determination",
                    primary_score=0.8,
                    confidence=0.85,
                    evidence_summary=["test evidence"]
                )
                
                await blackboard.complete_atom(
                    request_id=request_id,
                    atom_type=atom_type,
                    output=output,
                    component="test"
                )
            
            # Verify Zone 2
            atoms = await blackboard.get_all_atom_spaces(request_id)
            assert len(atoms) >= 2
            
            # Zone 3: Create synthesis
            await blackboard.create_synthesis_workspace(
                request_id=request_id,
                expected_atoms=["regulatory_focus", "construal_level"]
            )
            
            recommendation = SynthesizedRecommendation(
                primary_mechanism="social_proof",
                primary_mechanism_weight=0.7,
                recommendation_confidence=0.82,
                regulatory_framing="gain"
            )
            
            await blackboard.complete_synthesis(request_id, recommendation)
            
            # Verify Zone 3
            synthesis = await blackboard.get_synthesis_workspace(request_id)
            assert synthesis is not None
            assert synthesis.recommendation.primary_mechanism == "social_proof"
            
            # Zone 4: Create decision
            await blackboard.create_decision_state(request_id)
            
            selected_ad = SelectedAd(
                ad_id="ad_1",
                campaign_id="c1",
                advertiser_id="a1",
                selection_score=0.9,
                mechanism_match_score=0.85
            )
            
            serving_details = ServingDetails(
                mechanism_used="social_proof",
                psychological_match_confidence=0.82
            )
            
            latency_budget = LatencyBudgetUsage(
                total_budget_ms=100,
                total_used_ms=75,
                within_budget=True
            )
            
            await blackboard.complete_decision(
                request_id=request_id,
                selected_ad=selected_ad,
                serving_details=serving_details,
                latency_budget=latency_budget,
                tier=DecisionTier.FULL_REASONING
            )
            
            # Verify Zone 4
            decision = await blackboard.get_decision_state(request_id)
            assert decision is not None
            assert decision.selected_ad.ad_id == "ad_1"
            
            # Zone 5: Emit learning signal
            signal = LearningSignal(
                signal_type=LearningSignalType.MECHANISM_EFFECTIVENESS,
                source_component="test",
                request_id=request_id,
                user_id="test_user",
                signal_value={"mechanism": "social_proof", "effective": True},
                signal_confidence=0.9
            )
            
            await blackboard.emit_learning_signal(signal, "test")
            
            # Verify full snapshot
            snapshot = await blackboard.get_full_request_snapshot(request_id)
            assert snapshot['zones']['zone1_request_context'] is not None
            assert len(snapshot['zones']['zone2_atoms']) >= 2
            assert snapshot['zones']['zone3_synthesis'] is not None
            assert snapshot['zones']['zone4_decision'] is not None
            
        finally:
            # Cleanup
            await blackboard.cleanup_request(request_id)
    
    @pytest.mark.asyncio
    async def test_cross_atom_signal_coordination(self, real_blackboard_service):
        """Test that atoms can read each other's preliminary signals."""
        blackboard = real_blackboard_service
        request_id = f"test_signals_{datetime.utcnow().timestamp()}"
        
        try:
            # Atom 1 publishes signal
            signal = PreliminarySignal(
                signal_type="arousal_detection",
                signal_value="high",
                confidence=0.85,
                evidence=["rapid_clicks"],
                source_atom="regulatory_focus",
                requires_attention=True,
                attention_reason="May affect construal level"
            )
            
            await blackboard.publish_preliminary_signal(
                request_id=request_id,
                atom_type=AtomType.REGULATORY_FOCUS,
                signal=signal,
                component="regulatory_focus"
            )
            
            # Atom 2 reads signal
            signals = await blackboard.get_preliminary_signals(request_id)
            
            assert len(signals) == 1
            assert signals[0].signal_type == "arousal_detection"
            assert signals[0].signal_value == "high"
            assert signals[0].requires_attention is True
            
        finally:
            await blackboard.cleanup_request(request_id)
```

---

## Load & Stress Testing

```python
"""
ADAM Enhancement #02: Load Testing
Performance and stress tests for blackboard.
"""

import pytest
import asyncio
import time
from datetime import datetime
import statistics


@pytest.mark.load
class TestBlackboardLoad:
    """Load tests for blackboard performance."""
    
    @pytest.mark.asyncio
    async def test_concurrent_writes(self, real_blackboard_service):
        """Test concurrent write performance."""
        blackboard = real_blackboard_service
        num_requests = 100
        
        async def write_request(i: int):
            request_id = f"load_test_{i}_{datetime.utcnow().timestamp()}"
            context = RequestContext(
                request_id=request_id,
                request_source=RequestSource.INTERNAL_TEST,
                user=UserIdentifiers(user_id=f"user_{i}", session_id=f"session_{i}"),
                content=ContentContext(content_id=f"content_{i}", content_type=ContentType.AUDIO_PODCAST),
                device_type=DeviceType.MOBILE_IOS,
                ad_candidates=[
                    AdCandidateInfo(ad_id=f"ad_{i}", campaign_id="c1", advertiser_id="a1", ad_format="audio_30s")
                ],
                local_hour=12,
                local_day_of_week=2
            )
            
            start = time.time()
            result = await blackboard.initialize_request(request_id, context)
            latency = (time.time() - start) * 1000
            
            # Cleanup
            await blackboard.cleanup_request(request_id)
            
            return result.success, latency
        
        # Run concurrent writes
        start_time = time.time()
        results = await asyncio.gather(*[write_request(i) for i in range(num_requests)])
        total_time = time.time() - start_time
        
        # Analyze results
        successes = sum(1 for success, _ in results if success)
        latencies = [lat for _, lat in results]
        
        assert successes == num_requests, f"Only {successes}/{num_requests} succeeded"
        
        print(f"\nLoad Test Results:")
        print(f"  Total requests: {num_requests}")
        print(f"  Total time: {total_time:.2f}s")
        print(f"  Throughput: {num_requests/total_time:.1f} req/s")
        print(f"  Latency - Mean: {statistics.mean(latencies):.2f}ms")
        print(f"  Latency - P50: {statistics.median(latencies):.2f}ms")
        print(f"  Latency - P95: {sorted(latencies)[int(0.95*len(latencies))]:.2f}ms")
        print(f"  Latency - P99: {sorted(latencies)[int(0.99*len(latencies))]:.2f}ms")
        
        # Performance assertions
        assert statistics.mean(latencies) < 50, "Mean latency should be under 50ms"
        assert sorted(latencies)[int(0.95*len(latencies))] < 100, "P95 latency should be under 100ms"
    
    @pytest.mark.asyncio
    async def test_full_workflow_latency(self, real_blackboard_service):
        """Test latency of full workflow through all zones."""
        blackboard = real_blackboard_service
        num_iterations = 20
        latencies = []
        
        for i in range(num_iterations):
            request_id = f"workflow_test_{i}_{datetime.utcnow().timestamp()}"
            start = time.time()
            
            try:
                # Zone 1
                context = RequestContext(
                    request_id=request_id,
                    request_source=RequestSource.INTERNAL_TEST,
                    user=UserIdentifiers(user_id="user", session_id="session"),
                    content=ContentContext(content_id="content", content_type=ContentType.AUDIO_PODCAST),
                    device_type=DeviceType.MOBILE_IOS,
                    ad_candidates=[
                        AdCandidateInfo(ad_id="ad", campaign_id="c", advertiser_id="a", ad_format="audio_30s")
                    ],
                    local_hour=12,
                    local_day_of_week=2
                )
                await blackboard.initialize_request(request_id, context)
                
                # Zone 2 - Multiple atoms
                for atom_type in [AtomType.REGULATORY_FOCUS, AtomType.CONSTRUAL_LEVEL, AtomType.TEMPORAL_FRAMING]:
                    await blackboard.create_atom_space(request_id, atom_type, "test")
                    output = AtomOutput(determination="test", primary_score=0.8, confidence=0.85, evidence_summary=[])
                    await blackboard.complete_atom(request_id, atom_type, output, None, "test")
                
                # Zone 3
                await blackboard.create_synthesis_workspace(request_id, ["reg", "con", "temp"])
                rec = SynthesizedRecommendation(primary_mechanism="test", primary_mechanism_weight=0.8, recommendation_confidence=0.85)
                await blackboard.complete_synthesis(request_id, rec)
                
                # Zone 4
                await blackboard.create_decision_state(request_id)
                selected = SelectedAd(ad_id="ad", campaign_id="c", advertiser_id="a", selection_score=0.9, mechanism_match_score=0.8)
                serving = ServingDetails(mechanism_used="test", psychological_match_confidence=0.85)
                latency_budget = LatencyBudgetUsage(total_budget_ms=100, total_used_ms=50, within_budget=True)
                await blackboard.complete_decision(request_id, selected, serving, latency_budget, DecisionTier.FULL_REASONING)
                
                total_latency = (time.time() - start) * 1000
                latencies.append(total_latency)
                
            finally:
                await blackboard.cleanup_request(request_id)
        
        print(f"\nFull Workflow Latency:")
        print(f"  Iterations: {num_iterations}")
        print(f"  Mean: {statistics.mean(latencies):.2f}ms")
        print(f"  P95: {sorted(latencies)[int(0.95*len(latencies))]:.2f}ms")
        
        assert statistics.mean(latencies) < 100, "Full workflow should complete under 100ms"
```

---

## Implementation Timeline

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                     ENHANCEMENT #02 IMPLEMENTATION TIMELINE                             │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                         │
│  PHASE 1: FOUNDATION (Weeks 1-2)                                                        │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━                                                        │
│  □ Core Pydantic models implementation                                                  │
│  □ Redis key schema and connection pool                                                 │
│  □ Serialization with compression support                                               │
│  □ TTL management and cleanup                                                           │
│  □ Unit tests for all models                                                            │
│                                                                                         │
│  PHASE 2: BLACKBOARD SERVICE (Weeks 3-4)                                               │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━                                                  │
│  □ ZoneManager implementation for all zones                                             │
│  □ BlackboardService core methods                                                       │
│  □ State transition validation                                                          │
│  □ Conflict resolution                                                                  │
│  □ Concurrent access control                                                            │
│  □ Integration tests with Redis                                                         │
│                                                                                         │
│  PHASE 3: EVENT INTEGRATION (Weeks 5-6)                                                │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━                                                    │
│  □ Redis pub/sub event layer                                                            │
│  □ Kafka event bus integration (#31)                                                    │
│  □ Event publisher implementation                                                       │
│  □ Learning signal router                                                               │
│  □ Event-driven coordination tests                                                      │
│                                                                                         │
│  PHASE 4: LANGGRAPH INTEGRATION (Weeks 7-8)                                            │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━                                                 │
│  □ Blackboard-aware node pattern                                                        │
│  □ State injection strategy                                                             │
│  □ Workflow state binding                                                               │
│  □ Cross-node communication                                                             │
│  □ Full workflow integration tests                                                      │
│                                                                                         │
│  PHASE 5: PERSISTENCE & API (Weeks 9-10)                                               │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━                                                   │
│  □ Neo4j schema implementation                                                          │
│  □ Session persistence service                                                          │
│  □ FastAPI endpoints                                                                    │
│  □ Prometheus metrics                                                                   │
│  □ Load testing and optimization                                                        │
│  □ Production deployment preparation                                                    │
│                                                                                         │
│  DEPENDENCIES:                                                                          │
│  • Enhancement #01 (Bidirectional Graph-Reasoning Fusion) - Required for Zone 1 priors │
│  • Enhancement #31 (Caching & Real-Time Inference) - Required for Event Bus            │
│                                                                                         │
│  DELIVERABLES:                                                                          │
│  ✓ Complete Pydantic model library                                                      │
│  ✓ BlackboardService with full zone support                                             │
│  ✓ Redis implementation with pub/sub                                                    │
│  ✓ Kafka event integration                                                              │
│  ✓ LangGraph workflow integration                                                       │
│  ✓ Neo4j persistence layer                                                              │
│  ✓ REST API endpoints                                                                   │
│  ✓ Prometheus metrics                                                                   │
│  ✓ Comprehensive test suite                                                             │
│                                                                                         │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Success Metrics

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                           SUCCESS METRICS & TARGETS                                     │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                         │
│  PERFORMANCE METRICS                                                                    │
│  ━━━━━━━━━━━━━━━━━━━                                                                   │
│  │ Metric                        │ Target        │ Measurement                      │  │
│  ├───────────────────────────────┼───────────────┼──────────────────────────────────┤  │
│  │ Zone read latency (P50)       │ < 2ms         │ Prometheus histogram             │  │
│  │ Zone read latency (P95)       │ < 10ms        │ Prometheus histogram             │  │
│  │ Zone write latency (P50)      │ < 5ms         │ Prometheus histogram             │  │
│  │ Zone write latency (P95)      │ < 20ms        │ Prometheus histogram             │  │
│  │ Full workflow latency         │ < 100ms       │ End-to-end measurement           │  │
│  │ Throughput                    │ > 1000 req/s  │ Load test                        │  │
│  │ Event publish latency         │ < 5ms         │ Pub/sub timing                   │  │
│                                                                                         │
│  RELIABILITY METRICS                                                                    │
│  ━━━━━━━━━━━━━━━━━━━━                                                                  │
│  │ Metric                        │ Target        │ Measurement                      │  │
│  ├───────────────────────────────┼───────────────┼──────────────────────────────────┤  │
│  │ Operation success rate        │ > 99.9%       │ Success/total counter            │  │
│  │ Data consistency              │ 100%          │ Checksum verification            │  │
│  │ TTL accuracy                  │ ±5 seconds    │ TTL tracking                     │  │
│  │ Event delivery                │ > 99.9%       │ Kafka acknowledgments            │  │
│                                                                                         │
│  PSYCHOLOGICAL INTELLIGENCE IMPACT                                                      │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━                                                       │
│  │ Metric                        │ Target        │ Measurement                      │  │
│  ├───────────────────────────────┼───────────────┼──────────────────────────────────┤  │
│  │ Token efficiency improvement  │ 30-40%        │ Before/after comparison          │  │
│  │ Atom conflict reduction       │ 15-25%        │ Synthesis conflict count         │  │
│  │ Cross-atom coordination rate  │ > 80%         │ Signal observation rate          │  │
│  │ Attribution completeness      │ > 90%         │ Attribution context coverage     │  │
│  │ Learning signal capture       │ > 95%         │ Signal emission rate             │  │
│                                                                                         │
│  OPERATIONAL METRICS                                                                    │
│  ━━━━━━━━━━━━━━━━━━━━                                                                  │
│  │ Metric                        │ Target        │ Measurement                      │  │
│  ├───────────────────────────────┼───────────────┼──────────────────────────────────┤  │
│  │ Redis pool utilization        │ < 70%         │ Connection gauge                 │  │
│  │ Memory usage per request      │ < 50KB        │ Entry size histogram             │  │
│  │ Cleanup effectiveness         │ 100%          │ No orphan keys                   │  │
│  │ Neo4j write latency           │ < 100ms       │ Persistence timing               │  │
│                                                                                         │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

---

# CONCLUSION

## Summary

Enhancement #02 provides ADAM with a **Shared State Blackboard Architecture** that transforms isolated component processing into coordinated psychological reasoning. This specification delivers:

### Core Capabilities

1. **Five-Zone State Architecture**
   - Zone 1: Immutable request context
   - Zone 2: Atom reasoning spaces + 10 intelligence sources
   - Zone 3: Synthesis workspace with conflict resolution
   - Zone 4: Decision state with full attribution context
   - Zone 5: Learning signals for continuous improvement

2. **Real-Time Cross-Component Coordination**
   - Atoms can publish preliminary signals for others to observe
   - Synthesis sees reasoning traces, not just final outputs
   - Event-driven pub/sub enables reactive components

3. **Enterprise-Grade Implementation**
   - Complete Pydantic models for type safety
   - Redis backend with compression and TTL management
   - Kafka event bus integration
   - Neo4j persistence for historical analysis
   - Prometheus metrics for monitoring

4. **LangGraph Integration**
   - Blackboard-aware node patterns
   - Automatic state injection
   - Workflow state binding

### Living System Litmus Test

| Criterion | How Enhancement #02 Satisfies |
|-----------|------------------------------|
| **Learning Input** | Zone 5 captures all outcomes and signals; Attribution context enables gradient routing |
| **Learning Output** | Persisted reasoning traces improve future decisions; Mechanism effectiveness updates |
| **Psychological Grounding** | State × Trait framework; 10 intelligence sources; Mechanism-specific atom outputs |
| **Cross-Component Synergy** | Preliminary signals enable coordination; Event bus broadcasts state changes |
| **Growth Trajectory** | More data → better priors → better predictions → better outcomes → more data |

### Integration Points

- **Enhancement #01**: Provides graph priors for Zone 1; Receives reasoning traces for persistence
- **Enhancement #04**: 10 intelligence source models; Atom reasoning space structure
- **Enhancement #06**: Zone 5 learning signals feed Gradient Bridge
- **Enhancement #31**: Event Bus and cache coordination

This specification establishes the **shared memory foundation** that enables ADAM's components to function as a unified psychological intelligence system rather than isolated processing nodes.

---

## Appendix A: File Structure

```
adam/
├── blackboard/
│   ├── __init__.py
│   ├── config.py                    # BlackboardConfig, ZoneConfig
│   ├── models/
│   │   ├── __init__.py
│   │   ├── core.py                  # BlackboardEntry, Metadata, Results
│   │   ├── zone1_request.py         # RequestContext, UserIdentifiers
│   │   ├── zone2_atoms.py           # AtomReasoningSpace, AtomOutput
│   │   ├── zone2_mechanisms.py      # Mechanism-specific outputs
│   │   ├── zone2_sources.py         # Intelligence source models
│   │   ├── zone3_synthesis.py       # SynthesisWorkspace, Recommendation
│   │   ├── zone4_decision.py        # DecisionState, SelectedAd
│   │   ├── zone5_learning.py        # LearningSignal, OutcomeSignal
│   │   └── state_trait.py           # State × Trait framework
│   ├── redis/
│   │   ├── __init__.py
│   │   ├── keys.py                  # RedisKeySchema
│   │   ├── pool.py                  # RedisPoolManager
│   │   ├── serialization.py         # BlackboardSerializer
│   │   ├── ttl.py                   # TTLManager
│   │   └── pubsub.py                # PubSubManager
│   ├── service/
│   │   ├── __init__.py
│   │   ├── blackboard_service.py    # Main BlackboardService
│   │   ├── zone_manager.py          # ZoneManager
│   │   ├── state_transitions.py     # StateTransitionEngine
│   │   ├── conflict_resolution.py   # ConflictResolver
│   │   └── access_control.py        # AccessController
│   ├── events/
│   │   ├── __init__.py
│   │   ├── definitions.py           # Kafka event models
│   │   ├── publisher.py             # BlackboardEventPublisher
│   │   └── router.py                # LearningSignalRouter
│   ├── langgraph/
│   │   ├── __init__.py
│   │   ├── patterns.py              # Blackboard-aware node pattern
│   │   ├── state_injection.py       # StateInjector
│   │   └── workflow.py              # WorkflowExecutor
│   ├── persistence/
│   │   ├── __init__.py
│   │   ├── neo4j_schema.py          # Schema definitions
│   │   ├── neo4j_service.py         # BlackboardNeo4jPersistence
│   │   └── queries.py               # BlackboardQueryPatterns
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes.py                # FastAPI endpoints
│   │   └── dependencies.py          # Dependency injection
│   └── metrics/
│       ├── __init__.py
│       └── prometheus.py            # BlackboardMetrics
├── tests/
│   └── blackboard/
│       ├── test_models.py
│       ├── test_redis.py
│       ├── test_service.py
│       ├── test_integration.py
│       └── test_load.py
```

---

## Appendix B: Configuration Reference

```yaml
# blackboard_config.yaml

blackboard:
  redis:
    url: "redis://localhost:6379/0"
    pool_size: 20
    timeout_seconds: 5.0
  
  zones:
    zone1_request_context:
      redis_prefix: "bb:z1:req:"
      default_ttl_seconds: 600
      max_entry_size_bytes: 1048576
      enable_pubsub: true
      enable_persistence: false
      compression_enabled: false
    
    zone2_atom_reasoning:
      redis_prefix: "bb:z2:atom:"
      default_ttl_seconds: 1800
      max_entry_size_bytes: 1048576
      enable_pubsub: true
      enable_persistence: true
      compression_enabled: true
      compression_threshold_bytes: 10240
    
    zone3_synthesis_workspace:
      redis_prefix: "bb:z3:synth:"
      default_ttl_seconds: 3600
      max_entry_size_bytes: 1048576
      enable_pubsub: true
      enable_persistence: true
      compression_enabled: true
      compression_threshold_bytes: 10240
    
    zone4_decision_state:
      redis_prefix: "bb:z4:dec:"
      default_ttl_seconds: 86400
      max_entry_size_bytes: 524288
      enable_pubsub: true
      enable_persistence: true
      compression_enabled: false
    
    zone5_learning_signals:
      redis_prefix: "bb:z5:learn:"
      default_ttl_seconds: 259200
      max_entry_size_bytes: 1048576
      enable_pubsub: true
      enable_persistence: true
      compression_enabled: true
      compression_threshold_bytes: 5120
  
  event_bus:
    topic_prefix: "adam.blackboard"
    
  neo4j:
    uri: "bolt://localhost:7687"
    batch_size: 100
    flush_interval_seconds: 5.0
  
  metrics:
    enabled: true
    prefix: "adam_blackboard"
```

---

**Document Version**: 2.0 COMPLETE  
**Total Lines**: ~10,300  
**Status**: Enterprise Production-Ready  
**Last Updated**: January 2026


