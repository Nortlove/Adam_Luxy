# ADAM Integration Bridge: Complete Implementation Guide
## Definitive Gap Resolution & Claude Code Implementation Reference

**Document Purpose**: Bridge the Emergent Intelligence Architecture to all 31 ADAM enhancement specifications, providing explicit integration hooks, implementation order, and file references for seamless Claude Code/Cursor development.

**Version**: 1.0 FINAL  
**Date**: January 2026  
**Status**: Production Implementation Ready  
**Classification**: Master Integration Reference

---

# CRITICAL INSTRUCTIONS FOR CLAUDE CODE

## How to Use This Document

This Integration Bridge works in conjunction with three primary architecture documents:

| Document | Size | Purpose |
|----------|------|---------|
| `ADAM_EMERGENT_INTELLIGENCE_ARCHITECTURE.md` | 144KB | Philosophical foundation, Neo4j schema, discovery engine |
| `ADAM_IMPLEMENTATION_COMPANION.md` | 67KB | Pydantic models, Kafka events, LangGraph workflow |
| `ADAM_IMPLEMENTATION_COMPANION_PART2.md` | 82KB | Cache service, learning propagator, FastAPI layer |

**This Integration Bridge document (ADAM_Integration_Bridge_FINAL.md)** provides:
1. Explicit integration hooks for all 31 enhancement specifications
2. Implementation dependency graph and build order
3. File references for deep-dive specifications
4. Code patterns that connect components
5. Validation checklists for each integration point

## Implementation Protocol

**MANDATORY SEQUENCE FOR EACH COMPONENT:**

```
1. READ this Integration Bridge section for the component
2. UNDERSTAND the integration points listed
3. REFERENCE the deep-dive spec file (provided) for full details
4. IMPLEMENT using patterns from the three architecture documents
5. VALIDATE using the checklist provided
6. CONNECT to dependent components via Kafka events and Neo4j
```

**NEVER build a component in isolation. Every component must:**
- Emit learning signals to the Gradient Bridge
- Read/write psychological constructs from/to Neo4j
- Publish state changes to the Kafka Event Bus
- Integrate with the Blackboard shared state
- Expose Prometheus metrics

---

# PART 1: IMPLEMENTATION DEPENDENCY GRAPH

## 1.1 Build Order (Critical Path)

The following build order respects all dependencies and ensures no component is built before its prerequisites:

```
PHASE 0: INFRASTRUCTURE FOUNDATION (Weeks 1-4)
═══════════════════════════════════════════════
│
├─► Neo4j Graph Database Setup
│   └─► Schema from ADAM_EMERGENT_INTELLIGENCE_ARCHITECTURE.md Section 1.2
│
├─► Kafka Event Bus (#31 partial)
│   └─► Event contracts from ADAM_IMPLEMENTATION_COMPANION.md Part 2
│
├─► Redis Multi-Level Cache (#31 partial)
│   └─► Cache service from ADAM_IMPLEMENTATION_COMPANION_PART2.md Part 5
│
└─► Prometheus/Grafana Observability (#26)
    └─► Metrics from ADAM_IMPLEMENTATION_COMPANION.md Part 4

PHASE 1: SIGNAL CAPTURE & STORAGE (Weeks 5-8)
═══════════════════════════════════════════════
│
├─► #08 Signal Aggregation Pipeline [P0]
│   └─► Supraliminal capture, Flink processing
│
├─► #21 Embedding Infrastructure [P0]
│   └─► Vector storage, domain-tuned models
│
├─► #02 Blackboard Architecture [P0]
│   └─► Shared state zones, event pub/sub
│
└─► #19 Identity Resolution [P1]
    └─► Cross-platform ID linking

PHASE 2: PSYCHOLOGICAL INTELLIGENCE CORE (Weeks 9-14)
═══════════════════════════════════════════════════════
│
├─► #04 Atom of Thought DAG [P0]
│   └─► Psychological reasoning atoms
│
├─► #03 Meta-Learning Orchestration [P0]
│   └─► Routing decisions, Thompson Sampling
│
├─► #05 Verification Layer [P0]
│   └─► Consistency checks, calibration
│
├─► #06 Gradient Bridge [P0]
│   └─► Learning signal propagation
│
├─► #13 Cold Start Strategy [P0]
│   └─► New user bootstrapping
│
└─► #27 Extended Constructs [P1]
    └─► NFC, Self-Monitoring, Decision Style

PHASE 3: CONTENT & MATCHING (Weeks 15-18)
═════════════════════════════════════════
│
├─► #14 Brand Intelligence Library [P1]
│   └─► Brand psychological profiles
│
├─► #15 Copy Generation [P0]
│   └─► Personality-matched messaging
│
├─► #07 Voice/Audio Processing [P1]
│   └─► Audio features, prosody
│
└─► #16 Multimodal Fusion [P1]
    └─► Cross-modal signal integration

PHASE 4: JOURNEY & OPTIMIZATION (Weeks 19-22)
═════════════════════════════════════════════
│
├─► #10 Journey Tracking [P0]
│   └─► State machine, transitions
│
├─► #12 A/B Testing Infrastructure [P0]
│   └─► Hypothesis validation
│
├─► Gap23 Temporal Pattern Learning [P1]
│   └─► Life event detection, prediction
│
└─► #09 Latency-Optimized Inference [P0]
    └─► Sub-100ms decision paths

PHASE 5: ENTERPRISE & PLATFORM (Weeks 23-28)
════════════════════════════════════════════
│
├─► #18 Explanation Generation [P1]
│   └─► Decision transparency
│
├─► #28 WPP Ad Desk Integration [P0]
│   └─► OpenRTB, programmatic
│
├─► Gap20 Model Monitoring [P0]
│   └─► Drift detection
│
├─► Gap25 Adversarial Robustness [P1]
│   └─► Fraud detection
│
├─► #30 Feature Store [P1]
│   └─► Real-time serving
│
└─► #11 Psychological Validity Testing [P1]
    └─► Scientific validation
```

## 1.2 Component Dependency Matrix

Every row component depends on column components marked with ●:

```
                          │02│03│04│05│06│07│08│09│10│12│13│14│15│16│18│19│21│27│28│30│31│
──────────────────────────┼──┼──┼──┼──┼──┼──┼──┼──┼──┼──┼──┼──┼──┼──┼──┼──┼──┼──┼──┼──┼──┤
#02 Blackboard            │  │  │  │  │  │  │  │  │  │  │  │  │  │  │  │  │  │  │  │  │● │
#03 Meta-Learning         │● │  │  │  │● │  │  │  │  │  │  │  │  │  │  │  │  │  │  │  │● │
#04 Atom of Thought       │● │● │  │  │● │  │  │  │  │  │  │  │  │  │  │  │● │  │  │  │● │
#05 Verification          │● │  │● │  │● │  │  │  │  │  │  │  │  │  │  │  │  │  │  │  │  │
#06 Gradient Bridge       │● │  │  │  │  │  │  │  │  │  │  │  │  │  │  │  │  │  │  │  │● │
#07 Voice Processing      │● │  │  │  │● │  │● │  │  │  │  │  │  │  │  │  │● │  │  │  │● │
#08 Signal Aggregation    │● │  │  │  │● │  │  │  │  │  │  │  │  │  │  │  │  │  │  │  │● │
#09 Inference Engine      │● │● │● │  │  │  │  │  │  │  │● │  │  │  │  │  │  │  │  │● │● │
#10 Journey Tracking      │● │  │  │  │● │  │● │  │  │  │  │  │  │  │  │● │  │  │  │  │● │
#12 A/B Testing           │● │  │  │  │● │  │  │  │● │  │  │  │  │  │  │  │  │  │  │  │● │
#13 Cold Start            │● │● │  │  │● │  │  │  │  │  │  │  │  │  │  │  │  │  │  │● │● │
#14 Brand Intelligence    │● │  │  │  │● │  │  │  │  │  │  │  │  │  │  │  │● │  │  │  │  │
#15 Copy Generation       │● │  │  │  │● │  │  │  │● │  │● │● │  │  │  │  │  │● │  │  │  │
#16 Multimodal Fusion     │● │  │  │  │● │● │● │  │  │  │  │  │  │  │  │  │● │  │  │  │● │
#18 Explanation           │● │  │  │  │  │  │  │● │● │  │  │● │  │  │  │  │  │  │  │  │  │
#19 Identity Resolution   │● │  │  │  │● │  │● │  │  │  │  │  │  │  │  │  │  │  │  │  │  │
#27 Extended Constructs   │● │  │  │  │● │  │● │  │● │  │  │  │● │  │  │  │  │  │  │  │  │
#28 WPP Ad Desk           │● │  │  │  │● │  │  │  │● │  │  │● │● │  │  │● │  │  │  │  │  │
#30 Feature Store         │● │  │  │  │● │  │● │  │  │  │  │  │  │  │  │  │● │  │  │  │● │
Gap20 Model Monitoring    │  │● │  │  │  │  │  │  │  │  │  │  │  │  │  │  │● │  │  │  │  │
Gap23 Temporal Patterns   │● │  │  │  │● │  │● │  │● │  │  │  │  │  │  │● │● │  │  │  │● │
Gap25 Adversarial         │● │  │  │  │● │  │● │  │  │  │  │  │  │  │  │● │● │  │  │  │  │
```

---

# PART 2: SIGNAL CAPTURE INTEGRATION (#08)

## 2.1 Integration Point Summary

**Source Specification**: `/mnt/project/ADAM_Enhancement_08_COMPLETE.md` (158KB)

**Critical Role**: This is ADAM's sensory nervous system. Before any psychological inference can occur, raw behavioral signals must be collected, normalized, aggregated, and transformed into actionable features.

## 2.2 How It Connects to Emergent Architecture

The Emergent Intelligence Architecture references "supraliminal signals" and "implicit intelligence" but does not detail the capture infrastructure. Enhancement #08 provides:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    SIGNAL CAPTURE → EMERGENT ARCHITECTURE                   │
│                                                                             │
│   Enhancement #08                        Emergent Architecture              │
│   ═══════════════                        ════════════════════               │
│                                                                             │
│   ┌──────────────┐                       ┌──────────────────┐              │
│   │ Flink Stream │ ──────────────────►   │ SupraliminalSignals │           │
│   │ Processing   │   Transforms to       │ Pydantic Model     │           │
│   └──────────────┘                       └──────────────────┘              │
│          │                                        │                         │
│          │                                        │                         │
│   ┌──────────────┐                       ┌──────────────────┐              │
│   │ Keystroke    │ ──────────────────►   │ KeystrokeDynamics  │           │
│   │ Processor    │   Populates           │ (mouse, scroll)    │           │
│   └──────────────┘                       └──────────────────┘              │
│          │                                        │                         │
│          ▼                                        ▼                         │
│   ┌──────────────┐                       ┌──────────────────┐              │
│   │ Feature      │ ──────────────────►   │ GraphService.      │           │
│   │ Engineering  │   Writes to           │ update_behavioral_ │           │
│   └──────────────┘                       │ signature()        │           │
│                                          └──────────────────┘              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 2.3 Required Code Additions

### In Pydantic Models (add to ADAM_IMPLEMENTATION_COMPANION.md models):

```python
# =============================================================================
# SIGNAL CAPTURE MODELS - Integration with Enhancement #08
# =============================================================================

class SignalCategory(str, Enum):
    """Primary signal categories aligned with psychological relevance."""
    # Explicit behavioral signals
    BEHAVIORAL = "behavioral"
    NAVIGATIONAL = "navigational"
    TRANSACTIONAL = "transactional"
    
    # Implicit behavioral signals (supraliminal)
    KINEMATIC = "kinematic"      # Mouse, scroll, touch dynamics
    TEMPORAL = "temporal"        # Timing patterns, hesitations
    RHYTHMIC = "rhythmic"        # Session patterns, chronotype
    
    # Content signals
    CONTENT = "content"
    LINGUISTIC = "linguistic"
    
    # Context signals
    CONTEXTUAL = "contextual"
    SITUATIONAL = "situational"


class RawSignal(BaseModel):
    """Raw signal from capture pipeline."""
    signal_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    session_id: str
    timestamp: datetime
    category: SignalCategory
    signal_type: str
    
    # Raw values
    raw_value: Dict[str, Any]
    
    # Capture metadata
    source: str  # "web_sdk", "mobile_sdk", "server"
    confidence: float = Field(ge=0, le=1)
    latency_ms: float


class SignalWindow(BaseModel):
    """Aggregated signals over a time window."""
    window_id: str
    user_id: str
    window_start: datetime
    window_end: datetime
    window_type: str  # "tumbling", "sliding", "session"
    
    # Aggregated features
    features: Dict[str, float]
    signal_count: int
    categories_present: List[SignalCategory]
    
    # Quality metrics
    completeness_score: float
    freshness_score: float


class PsychologicalFeature(BaseModel):
    """Psychological feature derived from signals."""
    feature_id: str
    user_id: str
    timestamp: datetime
    
    feature_name: str
    feature_value: float
    confidence: float
    
    # Provenance
    source_signals: List[str]  # signal_ids
    derivation_method: str
    
    # Psychological mapping
    construct_relevance: Dict[str, float]  # construct_id -> relevance score
```

### Kafka Event Contracts (add to events):

```python
class SignalReceivedEvent(ADAMEvent):
    """Emitted when raw signal is received."""
    event_type: str = "signal.received"
    
    signal_id: str
    user_id: str
    category: SignalCategory
    signal_type: str
    timestamp: datetime


class FeatureExtractedEvent(ADAMEvent):
    """Emitted when psychological feature is extracted from signals."""
    event_type: str = "signal.feature_extracted"
    
    feature_id: str
    user_id: str
    feature_name: str
    feature_value: float
    confidence: float
    source_signal_count: int


class SignalAnomalyDetectedEvent(ADAMEvent):
    """Emitted when signal anomaly detected (potential fraud or unusual behavior)."""
    event_type: str = "signal.anomaly_detected"
    
    user_id: str
    anomaly_type: str
    severity: str
    details: Dict[str, Any]
```

### LangGraph Integration Point:

```python
# In the decision workflow, add signal retrieval node:

async def retrieve_recent_signals(state: DecisionState) -> DecisionState:
    """
    Retrieve recent signals for the user.
    
    This node pulls the latest signal windows and extracted features
    from the Signal Aggregation Pipeline (#08) to inform reasoning.
    """
    user_id = state["user_id"]
    
    # Get recent signal windows (last 5 minutes)
    signal_windows = await signal_service.get_recent_windows(
        user_id=user_id,
        window_count=3,
        include_features=True
    )
    
    # Extract supraliminal indicators
    supraliminal = extract_supraliminal_summary(signal_windows)
    
    return {
        **state,
        "signal_windows": signal_windows,
        "supraliminal_signals": supraliminal,
        "signal_confidence": compute_signal_confidence(signal_windows)
    }
```

## 2.4 Validation Checklist

Before marking Signal Capture as complete, verify:

- [ ] Flink pipeline processes 100K+ signals/second
- [ ] Keystroke dynamics captured with millisecond precision
- [ ] Scroll/mouse movement captured at 10-50ms resolution
- [ ] Signal windows properly aggregated (tumbling, sliding, session)
- [ ] Psychological features derived from signals
- [ ] Events emitted to Kafka for downstream components
- [ ] Signals written to Neo4j BehavioralSignature nodes
- [ ] Supraliminal signals available in Blackboard state
- [ ] Prometheus metrics exposed (signal_count, latency, anomalies)

---

# PART 3: BLACKBOARD ARCHITECTURE INTEGRATION (#02)

## 3.1 Integration Point Summary

**Source Specification**: `/mnt/project/ADAM_Enhancement_02_Shared_State_Blackboard_Architecture_v2_COMPLETE.md` (340KB)

**Critical Role**: The Blackboard is ADAM's working memory during request processing. All components read from and write to shared state zones.

## 3.2 Zone Architecture Mapping

The Emergent Architecture's LangGraph workflow must map to Blackboard zones:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         BLACKBOARD ZONE ARCHITECTURE                        │
│                                                                             │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                      ZONE 1: REQUEST CONTEXT                        │   │
│   │                                                                     │   │
│   │   Written by: API Gateway, retrieve_user_profile node               │   │
│   │   Read by: All subsequent nodes                                     │   │
│   │                                                                     │   │
│   │   • user_id, content_id, ad_candidate_ids                          │   │
│   │   • request_timestamp, session_id                                  │   │
│   │   • graph_context_snapshot (from Neo4j)                            │   │
│   │   • hot_priors (from Redis cache)                                  │   │
│   │                                                                     │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                      ZONE 2: ATOM WORKSPACES                        │   │
│   │                                                                     │   │
│   │   Written by: Individual AoT atoms                                  │   │
│   │   Read by: Synthesis node, Verification node                        │   │
│   │                                                                     │   │
│   │   • regulatory_focus_output: {orientation, confidence, evidence}   │   │
│   │   • construal_level_output: {level, confidence, evidence}          │   │
│   │   • mechanism_activation_output: {mechanisms, activations}         │   │
│   │   • personality_expression_output: {active_traits, modulations}    │   │
│   │   • cognitive_load_output: {load_level, capacity_remaining}        │   │
│   │                                                                     │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                      ZONE 3: SYNTHESIS WORKSPACE                    │   │
│   │                                                                     │   │
│   │   Written by: reason_about_mechanisms, generate_recommendation      │   │
│   │   Read by: Verification, finalize_decision                          │   │
│   │                                                                     │   │
│   │   • atom_outputs_merged: Dict[atom_name, output]                   │   │
│   │   • conflicts_detected: List[Conflict]                             │   │
│   │   • resolution_applied: Optional[Resolution]                       │   │
│   │   • synthesis_confidence: float                                    │   │
│   │                                                                     │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                      ZONE 4: DECISION STATE                         │   │
│   │                                                                     │   │
│   │   Written by: finalize_decision                                     │   │
│   │   Read by: Learning propagator, Explanation generator               │   │
│   │                                                                     │   │
│   │   • selected_ad_id: str                                            │   │
│   │   • decision_confidence: float                                     │   │
│   │   • atom_contributions: Dict[atom_name, contribution_weight]       │   │
│   │   • mechanism_attributions: Dict[mechanism_id, attribution]        │   │
│   │   • reasoning_trace: List[ReasoningStep]                           │   │
│   │                                                                     │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                      ZONE 5: LEARNING SIGNALS                       │   │
│   │                                                                     │   │
│   │   Written by: All nodes (accumulated)                               │   │
│   │   Read by: LearningPropagator, Gradient Bridge                      │   │
│   │                                                                     │   │
│   │   • per_atom_predictions: Dict[atom_name, prediction]              │   │
│   │   • component_latencies: Dict[component, latency_ms]               │   │
│   │   • meta_learner_routing_data: RoutingDecision                     │   │
│   │   • signals_for_gradient_bridge: List[LearningSignal]              │   │
│   │                                                                     │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 3.3 Required Code Additions

### Blackboard Service Integration:

```python
# =============================================================================
# BLACKBOARD SERVICE - Integration Layer
# =============================================================================

from typing import Dict, Any, Optional
from datetime import datetime
from redis import asyncio as aioredis
import json

class BlackboardZone(str, Enum):
    """Blackboard zones for organized state management."""
    REQUEST_CONTEXT = "request_context"
    ATOM_WORKSPACES = "atom_workspaces"
    SYNTHESIS_WORKSPACE = "synthesis_workspace"
    DECISION_STATE = "decision_state"
    LEARNING_SIGNALS = "learning_signals"


class BlackboardService:
    """
    Shared state management for ADAM request processing.
    
    Implements zone-based state organization with Redis backing
    for cross-component communication during a single request.
    """
    
    def __init__(self, redis: aioredis.Redis):
        self._redis = redis
        self._request_ttl = 300  # 5 minutes
    
    def _key(self, request_id: str, zone: BlackboardZone) -> str:
        return f"blackboard:{request_id}:{zone.value}"
    
    async def initialize_request(
        self,
        request_id: str,
        user_id: str,
        context: Dict[str, Any]
    ) -> None:
        """Initialize blackboard for a new request."""
        # Zone 1: Request Context
        await self._redis.hset(
            self._key(request_id, BlackboardZone.REQUEST_CONTEXT),
            mapping={
                "user_id": user_id,
                "request_id": request_id,
                "timestamp": datetime.utcnow().isoformat(),
                "context": json.dumps(context)
            }
        )
        await self._redis.expire(
            self._key(request_id, BlackboardZone.REQUEST_CONTEXT),
            self._request_ttl
        )
        
        # Initialize other zones as empty
        for zone in [
            BlackboardZone.ATOM_WORKSPACES,
            BlackboardZone.SYNTHESIS_WORKSPACE,
            BlackboardZone.DECISION_STATE,
            BlackboardZone.LEARNING_SIGNALS
        ]:
            await self._redis.hset(
                self._key(request_id, zone),
                "_initialized",
                datetime.utcnow().isoformat()
            )
            await self._redis.expire(self._key(request_id, zone), self._request_ttl)
    
    async def write_atom_output(
        self,
        request_id: str,
        atom_name: str,
        output: Dict[str, Any]
    ) -> None:
        """Write atom output to Zone 2."""
        await self._redis.hset(
            self._key(request_id, BlackboardZone.ATOM_WORKSPACES),
            atom_name,
            json.dumps(output)
        )
    
    async def read_all_atom_outputs(
        self,
        request_id: str
    ) -> Dict[str, Dict[str, Any]]:
        """Read all atom outputs from Zone 2."""
        raw = await self._redis.hgetall(
            self._key(request_id, BlackboardZone.ATOM_WORKSPACES)
        )
        return {
            k.decode(): json.loads(v.decode())
            for k, v in raw.items()
            if k.decode() != "_initialized"
        }
    
    async def write_decision(
        self,
        request_id: str,
        decision: Dict[str, Any]
    ) -> None:
        """Write final decision to Zone 4."""
        await self._redis.hset(
            self._key(request_id, BlackboardZone.DECISION_STATE),
            mapping={k: json.dumps(v) if isinstance(v, (dict, list)) else str(v) 
                    for k, v in decision.items()}
        )
    
    async def append_learning_signal(
        self,
        request_id: str,
        signal: Dict[str, Any]
    ) -> None:
        """Append learning signal to Zone 5."""
        signal_id = f"signal_{datetime.utcnow().timestamp()}"
        await self._redis.hset(
            self._key(request_id, BlackboardZone.LEARNING_SIGNALS),
            signal_id,
            json.dumps(signal)
        )
    
    async def get_learning_signals(
        self,
        request_id: str
    ) -> List[Dict[str, Any]]:
        """Get all learning signals from Zone 5."""
        raw = await self._redis.hgetall(
            self._key(request_id, BlackboardZone.LEARNING_SIGNALS)
        )
        return [
            json.loads(v.decode())
            for k, v in raw.items()
            if k.decode() != "_initialized"
        ]
```

### LangGraph Workflow Integration:

```python
# Update DecisionState to include blackboard reference
class DecisionState(TypedDict):
    """State passed through the decision workflow."""
    # Request identification
    request_id: str
    user_id: str
    
    # Blackboard reference (for zone access)
    blackboard: BlackboardService
    
    # Zone 1: Context (populated by first nodes)
    user_profile: Optional[UserProfile]
    mechanism_priors: Optional[Dict[str, MechanismEffectiveness]]
    graph_context: Optional[Dict[str, Any]]
    signal_windows: Optional[List[SignalWindow]]
    supraliminal_signals: Optional[SupraliminalSignals]
    
    # Zone 2: Atom outputs (populated by AoT atoms)
    atom_outputs: Dict[str, Dict[str, Any]]
    
    # Zone 3: Synthesis (populated by synthesis node)
    reasoning: Optional[str]
    synthesis_confidence: float
    
    # Zone 4: Decision (populated by final node)
    recommendation: Optional[MechanismRecommendation]
    decision: Optional[AdDecision]
    
    # Zone 5: Learning signals (accumulated)
    learning_signals: List[Dict[str, Any]]
    
    # Workflow control
    needs_verification: bool
    verification_passed: bool
```

## 3.4 Validation Checklist

- [ ] All five Blackboard zones properly initialized per request
- [ ] Zone 1 populated with user context and graph snapshot
- [ ] Zone 2 receives outputs from all AoT atoms
- [ ] Zone 3 captures synthesis workspace with conflict detection
- [ ] Zone 4 contains complete decision with attributions
- [ ] Zone 5 accumulates learning signals throughout request
- [ ] Redis TTL prevents stale data accumulation
- [ ] Cross-component reads work correctly
- [ ] Prometheus metrics for zone operations

---

# PART 4: ATOM OF THOUGHT DAG INTEGRATION (#04)

## 4.1 Integration Point Summary

**Source Specification**: `/mnt/project/ADAM_Enhancement_04_v3_Advanced_Atom_of_Thought.md` (107KB)

**Critical Role**: The psychological reasoning architecture that decomposes decisions into specialized atoms with dependency relationships.

## 4.2 DAG Structure with Prior Injection

The Emergent Architecture references AoT but doesn't detail the DAG structure or how learned priors are injected:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      ATOM OF THOUGHT DAG WITH PRIORS                        │
│                                                                             │
│   ┌─────────────────┐                                                       │
│   │   USER STATE    │◄─── Hot priors injected from cache                   │
│   │   (root atom)   │     • Recent mechanism success rates                 │
│   │                 │     • Trait confidence scores                        │
│   └────────┬────────┘     • Category effect sizes                          │
│            │                                                                │
│            │ DEPENDENCY: State affects all downstream atoms                 │
│            │                                                                │
│   ┌────────┴────────┬──────────────────┬──────────────────┐                │
│   │                 │                  │                  │                 │
│   ▼                 ▼                  ▼                  ▼                 │
│ ┌─────────┐   ┌─────────┐   ┌─────────────┐   ┌────────────────┐           │
│ │REGULAT- │   │CONSTRUAL│   │ COGNITIVE   │   │ AROUSAL/       │           │
│ │ORY      │   │ LEVEL   │   │ LOAD        │   │ APPROACH-      │           │
│ │FOCUS    │   │         │   │             │   │ AVOIDANCE      │           │
│ │         │   │         │   │             │   │                │           │
│ │Prior:   │   │Prior:   │   │Prior:       │   │Prior:          │           │
│ │user RF  │   │category │   │time-of-day  │   │initial signal  │           │
│ │history  │   │norms    │   │patterns     │   │trajectory      │           │
│ └────┬────┘   └────┬────┘   └──────┬──────┘   └───────┬────────┘           │
│      │             │               │                  │                     │
│      └─────────────┴───────┬───────┴──────────────────┘                     │
│                            │                                                │
│                            ▼                                                │
│                  ┌─────────────────────┐                                    │
│                  │ PERSONALITY         │◄─── User mechanism priors:        │
│                  │ EXPRESSION          │     "Openness works 72% for this  │
│                  │ (state-modulated)   │      user with promotion focus"   │
│                  └──────────┬──────────┘                                    │
│                             │                                               │
│                             ▼                                               │
│                  ┌─────────────────────┐                                    │
│                  │ MECHANISM           │◄─── From graph learning:          │
│                  │ ACTIVATION          │     "mimetic_desire effectiveness │
│                  │                     │      = 0.68 for this user"        │
│                  └──────────┬──────────┘                                    │
│                             │                                               │
│                             ▼                                               │
│                  ┌─────────────────────┐                                    │
│                  │ AD SELECTION        │◄─── Category effect priors:       │
│                  │ & SYNTHESIS         │     "Electronics + scarcity       │
│                  │                     │      = 1.3x expected lift"        │
│                  └─────────────────────┘                                    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 4.3 Required Code Additions

### Atom Definition with Prior Injection:

```python
# =============================================================================
# ATOM OF THOUGHT - Individual Atom Implementations
# =============================================================================

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from pydantic import BaseModel

class AtomInput(BaseModel):
    """Input to an AoT atom."""
    user_profile: UserProfile
    graph_context: Dict[str, Any]
    signal_context: Optional[SupraliminalSignals]
    
    # Injected priors from learning
    mechanism_priors: Dict[str, MechanismEffectiveness]
    category_priors: Dict[str, float]
    calibration_curves: Dict[str, List[Tuple[float, float]]]
    
    # Upstream atom outputs (for dependent atoms)
    upstream_outputs: Dict[str, Dict[str, Any]]


class AtomOutput(BaseModel):
    """Output from an AoT atom."""
    atom_name: str
    
    # Primary output
    result: Dict[str, Any]
    confidence: float
    
    # Evidence and reasoning
    evidence: List[str]
    reasoning_trace: str
    
    # For learning
    prediction: Optional[float]  # What this atom predicts about outcome
    features_used: List[str]


class PsychologicalAtom(ABC):
    """Base class for Atom of Thought psychological reasoning atoms."""
    
    def __init__(self, atom_name: str, dependencies: List[str]):
        self.atom_name = atom_name
        self.dependencies = dependencies  # Names of atoms this depends on
    
    @abstractmethod
    async def process(self, input: AtomInput) -> AtomOutput:
        """Process input and produce atom output."""
        pass
    
    def inject_priors(self, input: AtomInput) -> Dict[str, float]:
        """
        Extract relevant priors for this atom from the input.
        
        This is where learned knowledge from the graph influences
        the atom's reasoning.
        """
        # Subclasses override to extract relevant priors
        return {}


class RegulatoryFocusAtom(PsychologicalAtom):
    """
    Determines user's current regulatory focus orientation.
    
    Uses:
    - User's historical RF patterns (from graph)
    - Current state signals (from supraliminal)
    - Content context priming effects
    """
    
    def __init__(self):
        super().__init__(
            atom_name="regulatory_focus",
            dependencies=["user_state"]  # Depends on state assessment
        )
    
    def inject_priors(self, input: AtomInput) -> Dict[str, float]:
        """Extract RF-specific priors."""
        priors = {}
        
        # User's historical promotion/prevention ratio
        if "regulatory_focus_promotion" in input.mechanism_priors:
            priors["promotion_prior"] = input.mechanism_priors[
                "regulatory_focus_promotion"
            ].success_rate
        
        if "regulatory_focus_prevention" in input.mechanism_priors:
            priors["prevention_prior"] = input.mechanism_priors[
                "regulatory_focus_prevention"
            ].success_rate
        
        return priors
    
    async def process(self, input: AtomInput) -> AtomOutput:
        """Assess current regulatory focus."""
        priors = self.inject_priors(input)
        
        # Get state from upstream
        state_output = input.upstream_outputs.get("user_state", {})
        arousal_level = state_output.get("arousal", 0.5)
        
        # Determine focus based on signals + priors + state
        promotion_signals = self._extract_promotion_signals(input)
        prevention_signals = self._extract_prevention_signals(input)
        
        # Bayesian update with priors
        promotion_score = self._bayesian_update(
            prior=priors.get("promotion_prior", 0.5),
            evidence=promotion_signals
        )
        prevention_score = self._bayesian_update(
            prior=priors.get("prevention_prior", 0.5),
            evidence=prevention_signals
        )
        
        # High arousal amplifies current focus
        if arousal_level > 0.7:
            if promotion_score > prevention_score:
                promotion_score *= 1.2
            else:
                prevention_score *= 1.2
        
        # Determine orientation
        if promotion_score > prevention_score + 0.15:
            orientation = "promotion"
            confidence = min(0.95, (promotion_score - prevention_score) / 0.5)
        elif prevention_score > promotion_score + 0.15:
            orientation = "prevention"
            confidence = min(0.95, (prevention_score - promotion_score) / 0.5)
        else:
            orientation = "balanced"
            confidence = 0.5
        
        return AtomOutput(
            atom_name=self.atom_name,
            result={
                "orientation": orientation,
                "promotion_score": promotion_score,
                "prevention_score": prevention_score
            },
            confidence=confidence,
            evidence=[f"promotion_signals: {len(promotion_signals)}", 
                     f"prevention_signals: {len(prevention_signals)}"],
            reasoning_trace=f"RF assessment: {orientation} (conf: {confidence:.2f})",
            prediction=promotion_score if orientation == "promotion" else prevention_score,
            features_used=["arousal", "signal_context", "mechanism_priors"]
        )
    
    def _extract_promotion_signals(self, input: AtomInput) -> List[float]:
        """Extract signals indicating promotion focus."""
        signals = []
        if input.signal_context:
            # Fast approach movements indicate promotion
            if input.signal_context.mouse_dynamics:
                if input.signal_context.mouse_dynamics.approach_tendency > 0.6:
                    signals.append(0.8)
            # Low hesitation indicates promotion
            if input.signal_context.keystroke_dynamics:
                if input.signal_context.keystroke_dynamics.hesitation_ratio < 0.3:
                    signals.append(0.7)
        return signals
    
    def _extract_prevention_signals(self, input: AtomInput) -> List[float]:
        """Extract signals indicating prevention focus."""
        signals = []
        if input.signal_context:
            # High deliberation indicates prevention
            if input.signal_context.scroll_behavior:
                if input.signal_context.scroll_behavior.deliberation_index > 0.6:
                    signals.append(0.7)
        return signals
    
    def _bayesian_update(self, prior: float, evidence: List[float]) -> float:
        """Simple Bayesian update with evidence."""
        if not evidence:
            return prior
        likelihood = sum(evidence) / len(evidence)
        # Simplified update
        posterior = (prior * likelihood) / (
            prior * likelihood + (1 - prior) * (1 - likelihood)
        )
        return posterior


class MechanismActivationAtom(PsychologicalAtom):
    """
    Determines which cognitive mechanisms to activate.
    
    Uses learned effectiveness from graph:
    - User-specific mechanism success rates
    - Category-mechanism effectiveness
    - Current state modulation
    """
    
    def __init__(self):
        super().__init__(
            atom_name="mechanism_activation",
            dependencies=["regulatory_focus", "construal_level", "personality_expression"]
        )
    
    async def process(self, input: AtomInput) -> AtomOutput:
        """Select mechanisms to activate."""
        # Get all mechanism priors for this user
        mechanism_scores = {}
        
        for mechanism_type in MechanismType:
            if mechanism_type == MechanismType.EMERGENT:
                continue
            
            # Base score from user-specific prior
            prior = input.mechanism_priors.get(mechanism_type.value)
            if prior:
                base_score = prior.success_rate * prior.confidence
            else:
                # Fall back to category prior
                base_score = input.category_priors.get(mechanism_type.value, 0.5)
            
            # Modulate by upstream atom outputs
            rf_output = input.upstream_outputs.get("regulatory_focus", {})
            if rf_output.get("orientation") == "promotion":
                if mechanism_type in [MechanismType.MIMETIC_DESIRE, 
                                      MechanismType.IDENTITY_CONSTRUCTION]:
                    base_score *= 1.2
            elif rf_output.get("orientation") == "prevention":
                if mechanism_type in [MechanismType.AUTOMATIC_EVALUATION]:
                    base_score *= 1.2
            
            mechanism_scores[mechanism_type.value] = min(1.0, base_score)
        
        # Select top mechanisms
        sorted_mechanisms = sorted(
            mechanism_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        activated = [m for m, s in sorted_mechanisms[:3] if s > 0.4]
        
        return AtomOutput(
            atom_name=self.atom_name,
            result={
                "activated_mechanisms": activated,
                "mechanism_scores": mechanism_scores,
                "primary_mechanism": activated[0] if activated else None
            },
            confidence=sorted_mechanisms[0][1] if sorted_mechanisms else 0.5,
            evidence=[f"{m}: {s:.2f}" for m, s in sorted_mechanisms[:5]],
            reasoning_trace=f"Activated: {activated}",
            prediction=sorted_mechanisms[0][1] if sorted_mechanisms else 0.5,
            features_used=list(mechanism_scores.keys())
        )
```

### DAG Executor:

```python
class AtomDAGExecutor:
    """
    Executes the Atom of Thought DAG respecting dependencies.
    
    Atoms are executed in topological order, with outputs from
    upstream atoms available to downstream atoms.
    """
    
    def __init__(self, atoms: List[PsychologicalAtom]):
        self.atoms = {atom.atom_name: atom for atom in atoms}
        self._build_execution_order()
    
    def _build_execution_order(self):
        """Build topological execution order."""
        # Simple topological sort
        visited = set()
        order = []
        
        def visit(name):
            if name in visited:
                return
            visited.add(name)
            atom = self.atoms.get(name)
            if atom:
                for dep in atom.dependencies:
                    visit(dep)
                order.append(name)
        
        for name in self.atoms:
            visit(name)
        
        self.execution_order = order
    
    async def execute(
        self,
        user_profile: UserProfile,
        graph_context: Dict[str, Any],
        signal_context: Optional[SupraliminalSignals],
        mechanism_priors: Dict[str, MechanismEffectiveness],
        category_priors: Dict[str, float],
        calibration_curves: Dict[str, List[Tuple[float, float]]],
        blackboard: BlackboardService,
        request_id: str
    ) -> Dict[str, AtomOutput]:
        """Execute all atoms in dependency order."""
        outputs: Dict[str, AtomOutput] = {}
        
        for atom_name in self.execution_order:
            atom = self.atoms.get(atom_name)
            if not atom:
                continue
            
            # Build input with upstream outputs
            atom_input = AtomInput(
                user_profile=user_profile,
                graph_context=graph_context,
                signal_context=signal_context,
                mechanism_priors=mechanism_priors,
                category_priors=category_priors,
                calibration_curves=calibration_curves,
                upstream_outputs={
                    dep: outputs[dep].result 
                    for dep in atom.dependencies 
                    if dep in outputs
                }
            )
            
            # Execute atom
            output = await atom.process(atom_input)
            outputs[atom_name] = output
            
            # Write to Blackboard Zone 2
            await blackboard.write_atom_output(
                request_id=request_id,
                atom_name=atom_name,
                output=output.dict()
            )
        
        return outputs
```

## 4.4 Validation Checklist

- [ ] All 7 psychological atoms implemented
- [ ] DAG dependencies correctly modeled
- [ ] Priors injected from graph learning into each atom
- [ ] Atoms write outputs to Blackboard Zone 2
- [ ] Upstream outputs available to downstream atoms
- [ ] Confidence calibration applied to atom outputs
- [ ] Learning signals include atom predictions
- [ ] Execution order respects dependencies
- [ ] Prometheus metrics for atom latencies

---

# PART 5: A/B TESTING INFRASTRUCTURE INTEGRATION (#12)

## 5.1 Integration Point Summary

**Source Specification**: `/mnt/project/ADAM_Enhancement_12_COMPLETE.md` (158KB)

**Critical Role**: The Discovery Engine's hypothesis testing depends on proper A/B testing statistical framework. Without this, we cannot validate emergent constructs.

## 5.2 How It Connects to Discovery Engine

```
┌─────────────────────────────────────────────────────────────────────────────┐
│              DISCOVERY ENGINE → A/B TESTING INTEGRATION                     │
│                                                                             │
│   Discovery Engine                          A/B Testing (#12)               │
│   ════════════════                          ═══════════════════             │
│                                                                             │
│   ┌────────────────┐                       ┌────────────────────┐          │
│   │ Pattern Miner  │                       │ Experiment         │          │
│   │ detects new    │──── Creates ────────► │ Definition         │          │
│   │ signature      │                       │ (hypothesis test)  │          │
│   └────────────────┘                       └────────────────────┘          │
│          │                                          │                       │
│          │                                          │                       │
│   ┌────────────────┐                       ┌────────────────────┐          │
│   │ Hypothesis     │                       │ Traffic            │          │
│   │ Generator      │──── Configures ─────► │ Allocation         │          │
│   │ (Claude)       │                       │ (Thompson Sampling)│          │
│   └────────────────┘                       └────────────────────┘          │
│          │                                          │                       │
│          │                                          │                       │
│   ┌────────────────┐                       ┌────────────────────┐          │
│   │ Validation     │◄─── Results from ──── │ Statistical        │          │
│   │ (effect size,  │                       │ Analysis           │          │
│   │  significance) │                       │ (sequential tests) │          │
│   └────────────────┘                       └────────────────────┘          │
│          │                                                                  │
│          ▼                                                                  │
│   ┌────────────────┐                                                       │
│   │ Knowledge      │                                                       │
│   │ Integration    │                                                       │
│   │ (Neo4j update) │                                                       │
│   └────────────────┘                                                       │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 5.3 Required Code Additions

### Experiment Models:

```python
# =============================================================================
# A/B TESTING - Integration with Discovery Engine
# =============================================================================

class ExperimentType(str, Enum):
    """Types of experiments in ADAM."""
    MECHANISM_EFFECTIVENESS = "mechanism_effectiveness"
    COPY_VARIANT = "copy_variant"
    TIMING_OPTIMIZATION = "timing_optimization"
    EMERGENT_CONSTRUCT = "emergent_construct"
    HYPOTHESIS_VALIDATION = "hypothesis_validation"


class ExperimentStatus(str, Enum):
    """Experiment lifecycle status."""
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class StatisticalMethod(str, Enum):
    """Statistical methods for experiment analysis."""
    FREQUENTIST = "frequentist"
    BAYESIAN = "bayesian"
    SEQUENTIAL = "sequential"
    MULTI_ARMED_BANDIT = "multi_armed_bandit"


class Experiment(BaseModel):
    """A/B experiment definition."""
    experiment_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str
    experiment_type: ExperimentType
    status: ExperimentStatus = ExperimentStatus.DRAFT
    
    # Hypothesis (from Discovery Engine)
    hypothesis_id: Optional[str] = None
    null_hypothesis: str
    alternative_hypothesis: str
    
    # Variants
    control_variant: str
    treatment_variants: List[str]
    
    # Traffic allocation
    traffic_percentage: float = Field(ge=0, le=100, default=10.0)
    allocation_method: str = "random"  # "random", "stratified", "thompson"
    
    # Statistical configuration
    statistical_method: StatisticalMethod = StatisticalMethod.BAYESIAN
    minimum_detectable_effect: float = 0.05
    significance_level: float = 0.05
    statistical_power: float = 0.8
    
    # Sample size
    required_sample_size: Optional[int] = None
    current_sample_size: int = 0
    
    # Targeting (which users see this experiment)
    targeting_criteria: Dict[str, Any] = Field(default_factory=dict)
    
    # Timing
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    
    # Results
    results: Optional[Dict[str, Any]] = None
    winner: Optional[str] = None
    
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ExperimentAssignment(BaseModel):
    """Assignment of a user to an experiment variant."""
    assignment_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    experiment_id: str
    user_id: str
    variant: str
    assigned_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Outcome tracking
    outcome_observed: bool = False
    outcome_value: Optional[float] = None
    outcome_time: Optional[datetime] = None


class ExperimentResult(BaseModel):
    """Statistical results of an experiment."""
    experiment_id: str
    analysis_time: datetime = Field(default_factory=datetime.utcnow)
    
    # Per-variant metrics
    variant_metrics: Dict[str, Dict[str, float]]
    # e.g., {"control": {"conversions": 100, "sample": 1000, "rate": 0.10}, ...}
    
    # Statistical significance
    p_value: Optional[float] = None
    confidence_interval: Optional[Tuple[float, float]] = None
    
    # Effect size
    effect_size: float
    effect_size_ci: Tuple[float, float]
    
    # Bayesian results (if applicable)
    posterior_probability_best: Optional[Dict[str, float]] = None
    expected_loss: Optional[Dict[str, float]] = None
    
    # Decision
    is_significant: bool
    recommended_action: str  # "continue", "stop_winner", "stop_no_effect"
    winner: Optional[str] = None
```

### A/B Testing Service:

```python
class ABTestingService:
    """
    A/B Testing service for experiment management.
    
    Integrates with:
    - Discovery Engine: Creates experiments from hypotheses
    - Inference Engine: Provides variant assignments
    - Gradient Bridge: Receives outcome data
    """
    
    def __init__(
        self,
        graph_service: GraphService,
        cache_service: CacheService,
        kafka_producer: KafkaProducer
    ):
        self.graph = graph_service
        self.cache = cache_service
        self.kafka = kafka_producer
    
    async def create_from_hypothesis(
        self,
        hypothesis: Hypothesis
    ) -> Experiment:
        """
        Create an experiment from a Discovery Engine hypothesis.
        
        This is the bridge between emergent pattern detection
        and rigorous statistical validation.
        """
        # Determine experiment parameters from hypothesis type
        if hypothesis.hypothesis_type == "mechanism_interaction":
            experiment_type = ExperimentType.MECHANISM_EFFECTIVENESS
            control = "no_interaction"
            treatments = [hypothesis.hypothesis_id]
        elif hypothesis.hypothesis_type == "emergent_construct":
            experiment_type = ExperimentType.EMERGENT_CONSTRUCT
            control = "existing_targeting"
            treatments = [f"emergent_{hypothesis.hypothesis_id}"]
        else:
            experiment_type = ExperimentType.HYPOTHESIS_VALIDATION
            control = "baseline"
            treatments = [hypothesis.hypothesis_id]
        
        # Calculate required sample size
        sample_size = self._calculate_sample_size(
            baseline_rate=0.05,  # Assume 5% baseline conversion
            mde=0.10,  # 10% minimum detectable effect
            alpha=0.05,
            power=0.8
        )
        
        experiment = Experiment(
            name=f"Hypothesis Test: {hypothesis.mechanism_id or hypothesis.signature_id}",
            description=hypothesis.description,
            experiment_type=experiment_type,
            hypothesis_id=hypothesis.hypothesis_id,
            null_hypothesis=f"No effect from {hypothesis.hypothesis_id}",
            alternative_hypothesis=hypothesis.description,
            control_variant=control,
            treatment_variants=treatments,
            required_sample_size=sample_size,
            traffic_percentage=10.0,  # Start with 10% traffic
            statistical_method=StatisticalMethod.BAYESIAN
        )
        
        # Store in Neo4j
        await self.graph.create_experiment(experiment)
        
        # Emit event
        await self.kafka.send(
            "experiments",
            ExperimentCreatedEvent(
                experiment_id=experiment.experiment_id,
                hypothesis_id=hypothesis.hypothesis_id,
                experiment_type=experiment_type.value
            )
        )
        
        return experiment
    
    async def get_variant_assignment(
        self,
        experiment_id: str,
        user_id: str
    ) -> ExperimentAssignment:
        """
        Get or create variant assignment for a user.
        
        Uses deterministic hashing for consistency.
        """
        # Check cache first
        cached = await self.cache.get_experiment_assignment(
            experiment_id, user_id
        )
        if cached:
            return cached
        
        # Get experiment
        experiment = await self.graph.get_experiment(experiment_id)
        if not experiment or experiment.status != ExperimentStatus.ACTIVE:
            return None
        
        # Deterministic assignment using hash
        hash_input = f"{experiment_id}:{user_id}"
        hash_value = int(hashlib.md5(hash_input.encode()).hexdigest(), 16)
        
        # Check if user is in experiment traffic
        if (hash_value % 100) >= experiment.traffic_percentage:
            return None  # User not in experiment
        
        # Assign to variant
        all_variants = [experiment.control_variant] + experiment.treatment_variants
        variant_index = hash_value % len(all_variants)
        variant = all_variants[variant_index]
        
        assignment = ExperimentAssignment(
            experiment_id=experiment_id,
            user_id=user_id,
            variant=variant
        )
        
        # Cache assignment
        await self.cache.set_experiment_assignment(assignment)
        
        # Store in graph
        await self.graph.create_experiment_assignment(assignment)
        
        return assignment
    
    async def record_outcome(
        self,
        assignment_id: str,
        outcome_value: float
    ) -> None:
        """Record outcome for an experiment assignment."""
        # Update assignment
        await self.graph.update_experiment_outcome(
            assignment_id=assignment_id,
            outcome_value=outcome_value,
            outcome_time=datetime.utcnow()
        )
        
        # Get assignment for experiment_id
        assignment = await self.graph.get_assignment(assignment_id)
        
        # Check if we should analyze
        experiment = await self.graph.get_experiment(assignment.experiment_id)
        if experiment.current_sample_size >= experiment.required_sample_size:
            await self._run_analysis(experiment)
    
    async def _run_analysis(self, experiment: Experiment) -> ExperimentResult:
        """Run statistical analysis on experiment."""
        # Get all outcomes
        outcomes = await self.graph.get_experiment_outcomes(experiment.experiment_id)
        
        # Group by variant
        variant_outcomes = {}
        for outcome in outcomes:
            if outcome.variant not in variant_outcomes:
                variant_outcomes[outcome.variant] = []
            variant_outcomes[outcome.variant].append(outcome.outcome_value)
        
        # Run Bayesian analysis
        if experiment.statistical_method == StatisticalMethod.BAYESIAN:
            result = self._bayesian_analysis(variant_outcomes)
        else:
            result = self._frequentist_analysis(variant_outcomes)
        
        # Store result
        await self.graph.store_experiment_result(result)
        
        # If significant, notify Discovery Engine
        if result.is_significant and result.winner:
            await self.kafka.send(
                "discoveries",
                HypothesisValidatedEvent(
                    hypothesis_id=experiment.hypothesis_id,
                    experiment_id=experiment.experiment_id,
                    effect_size=result.effect_size,
                    is_validated=True
                )
            )
        
        return result
    
    def _bayesian_analysis(
        self,
        variant_outcomes: Dict[str, List[float]]
    ) -> ExperimentResult:
        """Bayesian analysis of experiment outcomes."""
        import numpy as np
        from scipy import stats
        
        # Calculate posterior for each variant
        posteriors = {}
        for variant, outcomes in variant_outcomes.items():
            conversions = sum(1 for o in outcomes if o > 0)
            total = len(outcomes)
            
            # Beta posterior (assuming Beta(1,1) prior)
            alpha = 1 + conversions
            beta = 1 + (total - conversions)
            posteriors[variant] = (alpha, beta)
        
        # Monte Carlo estimation of probability best
        n_samples = 10000
        samples = {}
        for variant, (alpha, beta) in posteriors.items():
            samples[variant] = np.random.beta(alpha, beta, n_samples)
        
        # Probability each variant is best
        prob_best = {}
        for variant in samples:
            is_best = np.ones(n_samples, dtype=bool)
            for other_variant, other_samples in samples.items():
                if other_variant != variant:
                    is_best &= (samples[variant] > other_samples)
            prob_best[variant] = np.mean(is_best)
        
        # Find winner
        best_variant = max(prob_best, key=prob_best.get)
        is_significant = prob_best[best_variant] > 0.95
        
        # Calculate effect size (relative to control)
        control_outcomes = variant_outcomes.get("control", [])
        treatment_outcomes = variant_outcomes.get(best_variant, [])
        
        control_rate = np.mean(control_outcomes) if control_outcomes else 0
        treatment_rate = np.mean(treatment_outcomes) if treatment_outcomes else 0
        
        if control_rate > 0:
            effect_size = (treatment_rate - control_rate) / control_rate
        else:
            effect_size = 0
        
        return ExperimentResult(
            experiment_id="",  # Will be set by caller
            variant_metrics={
                variant: {
                    "conversions": sum(1 for o in outcomes if o > 0),
                    "sample": len(outcomes),
                    "rate": np.mean(outcomes)
                }
                for variant, outcomes in variant_outcomes.items()
            },
            effect_size=effect_size,
            effect_size_ci=(effect_size * 0.8, effect_size * 1.2),  # Simplified
            posterior_probability_best=prob_best,
            is_significant=is_significant,
            recommended_action="stop_winner" if is_significant else "continue",
            winner=best_variant if is_significant else None
        )
    
    def _calculate_sample_size(
        self,
        baseline_rate: float,
        mde: float,
        alpha: float = 0.05,
        power: float = 0.8
    ) -> int:
        """Calculate required sample size per variant."""
        from scipy import stats
        
        p1 = baseline_rate
        p2 = baseline_rate * (1 + mde)
        
        pooled_p = (p1 + p2) / 2
        
        z_alpha = stats.norm.ppf(1 - alpha / 2)
        z_power = stats.norm.ppf(power)
        
        n = (
            2 * pooled_p * (1 - pooled_p) * (z_alpha + z_power) ** 2
        ) / (p2 - p1) ** 2
        
        return int(np.ceil(n))
```

## 5.4 Validation Checklist

- [ ] Experiments created from Discovery Engine hypotheses
- [ ] Deterministic user-to-variant assignment
- [ ] Bayesian analysis calculates probability best
- [ ] Sequential testing enables early stopping
- [ ] Effect size calculated with confidence intervals
- [ ] Results stored in Neo4j for learning
- [ ] Events emitted for hypothesis validation
- [ ] Thompson Sampling for traffic allocation
- [ ] Prometheus metrics for experiment status

---

# PART 6: COLD START STRATEGY INTEGRATION (#13)

## 6.1 Integration Point Summary

**Source Specifications**: 
- `/mnt/project/ADAM_Enhancement_13_Cold_Start_Strategy_COMPLETE.md` (112KB)
- `/mnt/project/ADAM_Enhancement_13_Cold_Start_Strategy_Part2_COMPLETE.md` (152KB)
- `/mnt/project/ADAM_Enhancement_13_Cold_Start_Strategy_Part3_COMPLETE.md` (46KB)

**Critical Role**: Every new user starts as a "cold" user. This system bootstraps psychological profiles using hierarchical Bayesian priors until sufficient data accumulates.

## 6.2 User Data Tiers

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         USER DATA TIER PROGRESSION                          │
│                                                                             │
│   TIER 0: ANONYMOUS                                                         │
│   ════════════════                                                          │
│   • No user ID                                                              │
│   • Only contextual signals (time, content, device)                         │
│   • Use population priors + content-based inference                         │
│   • Strategy: Contextual Inference                                          │
│                                                                             │
│   TIER 1: IDENTIFIED (< 3 interactions)                                     │
│   ══════════════════════════════════════                                    │
│   • Have user ID, minimal behavioral data                                   │
│   • Use archetype matching from initial signals                             │
│   • Strategy: Archetype Bootstrap                                           │
│                                                                             │
│   TIER 2: EMERGING (3-10 interactions)                                      │
│   ═════════════════════════════════════                                     │
│   • Building individual profile                                             │
│   • Blend archetype priors with observed data                               │
│   • Strategy: Bayesian Profile Building                                     │
│                                                                             │
│   TIER 3: ESTABLISHED (10-50 interactions)                                  │
│   ══════════════════════════════════════════                                │
│   • Reliable individual profile                                             │
│   • Individual priors dominate cluster priors                               │
│   • Strategy: Individual Optimization                                       │
│                                                                             │
│   TIER 4: RICH (50+ interactions)                                           │
│   ══════════════════════════════════                                        │
│   • High-confidence profile                                                 │
│   • Full mechanism effectiveness known                                      │
│   • Strategy: Personalized with Exploration                                 │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 6.3 Required Code Additions

### Cold Start Service Integration:

```python
# =============================================================================
# COLD START - Integration with Emergent Architecture
# =============================================================================

class UserDataTier(str, Enum):
    """User data availability tiers."""
    ANONYMOUS = "anonymous"      # Tier 0: No ID
    IDENTIFIED = "identified"   # Tier 1: <3 interactions
    EMERGING = "emerging"       # Tier 2: 3-10 interactions
    ESTABLISHED = "established" # Tier 3: 10-50 interactions
    RICH = "rich"               # Tier 4: 50+ interactions


class ColdStartStrategy(str, Enum):
    """Strategies for different data tiers."""
    CONTEXTUAL_INFERENCE = "contextual_inference"
    ARCHETYPE_BOOTSTRAP = "archetype_bootstrap"
    BAYESIAN_PROFILE_BUILDING = "bayesian_profile_building"
    INDIVIDUAL_OPTIMIZATION = "individual_optimization"
    PERSONALIZED_EXPLORATION = "personalized_exploration"


class ArchetypeCluster(BaseModel):
    """Psychological archetype cluster for cold start."""
    cluster_id: str
    name: str
    description: str
    
    # Cluster centroid (psychological profile)
    big_five_centroid: BigFiveProfile
    regulatory_focus_tendency: str  # "promotion", "prevention", "balanced"
    construal_tendency: str  # "abstract", "concrete", "mixed"
    
    # Mechanism effectiveness priors for this cluster
    mechanism_priors: Dict[str, MechanismEffectiveness]
    
    # Cluster statistics
    user_count: int
    average_conversion_rate: float
    
    # Matching signals (used for archetype assignment)
    matching_signals: Dict[str, Tuple[float, float]]  # signal -> (mean, std)


class ColdStartService:
    """
    Cold start profile bootstrapping service.
    
    Integrates with:
    - GraphService: Gets/sets user profiles
    - CacheService: Caches archetype priors
    - AtomDAGExecutor: Injects priors into atoms
    """
    
    def __init__(
        self,
        graph: GraphService,
        cache: CacheService,
        kafka: KafkaProducer
    ):
        self.graph = graph
        self.cache = cache
        self.kafka = kafka
        
        # Archetype clusters (loaded from graph at startup)
        self._archetypes: Dict[str, ArchetypeCluster] = {}
    
    async def initialize(self):
        """Load archetype clusters from graph."""
        self._archetypes = await self.graph.get_all_archetypes()
    
    async def get_user_tier(self, user_id: Optional[str]) -> UserDataTier:
        """Determine user's data tier."""
        if not user_id:
            return UserDataTier.ANONYMOUS
        
        interaction_count = await self.graph.get_user_interaction_count(user_id)
        
        if interaction_count < 3:
            return UserDataTier.IDENTIFIED
        elif interaction_count < 10:
            return UserDataTier.EMERGING
        elif interaction_count < 50:
            return UserDataTier.ESTABLISHED
        else:
            return UserDataTier.RICH
    
    async def get_strategy(self, tier: UserDataTier) -> ColdStartStrategy:
        """Get cold start strategy for tier."""
        strategy_map = {
            UserDataTier.ANONYMOUS: ColdStartStrategy.CONTEXTUAL_INFERENCE,
            UserDataTier.IDENTIFIED: ColdStartStrategy.ARCHETYPE_BOOTSTRAP,
            UserDataTier.EMERGING: ColdStartStrategy.BAYESIAN_PROFILE_BUILDING,
            UserDataTier.ESTABLISHED: ColdStartStrategy.INDIVIDUAL_OPTIMIZATION,
            UserDataTier.RICH: ColdStartStrategy.PERSONALIZED_EXPLORATION
        }
        return strategy_map[tier]
    
    async def bootstrap_profile(
        self,
        user_id: Optional[str],
        context: Dict[str, Any],
        signals: Optional[SupraliminalSignals] = None
    ) -> Tuple[UserProfile, Dict[str, MechanismEffectiveness]]:
        """
        Bootstrap psychological profile for cold start user.
        
        Returns profile and mechanism priors appropriate for data tier.
        """
        tier = await self.get_user_tier(user_id)
        strategy = await self.get_strategy(tier)
        
        if strategy == ColdStartStrategy.CONTEXTUAL_INFERENCE:
            return await self._contextual_inference(context)
        
        elif strategy == ColdStartStrategy.ARCHETYPE_BOOTSTRAP:
            return await self._archetype_bootstrap(user_id, context, signals)
        
        elif strategy == ColdStartStrategy.BAYESIAN_PROFILE_BUILDING:
            return await self._bayesian_profile_building(user_id, context, signals)
        
        elif strategy == ColdStartStrategy.INDIVIDUAL_OPTIMIZATION:
            return await self._individual_optimization(user_id)
        
        else:  # PERSONALIZED_EXPLORATION
            return await self._personalized_exploration(user_id)
    
    async def _contextual_inference(
        self,
        context: Dict[str, Any]
    ) -> Tuple[UserProfile, Dict[str, MechanismEffectiveness]]:
        """
        Infer profile from context only (Tier 0).
        
        Uses population priors modulated by contextual factors.
        """
        # Start with population priors
        population_priors = await self.cache.get_population_priors()
        
        # Modulate by context
        time_of_day = context.get("time_of_day")
        content_category = context.get("content_category")
        device_type = context.get("device_type")
        
        # Apply contextual adjustments
        mechanism_priors = {}
        for mechanism, prior in population_priors.items():
            adjusted = self._apply_contextual_adjustment(
                prior, time_of_day, content_category, device_type
            )
            mechanism_priors[mechanism] = adjusted
        
        # Create anonymous profile with population defaults
        profile = UserProfile(
            user_id="anonymous",
            big_five=BigFiveProfile(
                openness=0.5, conscientiousness=0.5, extraversion=0.5,
                agreeableness=0.5, neuroticism=0.5
            ),
            regulatory_focus=RegulatoryFocusState(
                promotion_strength=0.5, prevention_strength=0.5
            ),
            construal_level=ConstrualLevel.MIXED,
            data_tier=UserDataTier.ANONYMOUS,
            profile_confidence=0.3
        )
        
        return profile, mechanism_priors
    
    async def _archetype_bootstrap(
        self,
        user_id: str,
        context: Dict[str, Any],
        signals: Optional[SupraliminalSignals]
    ) -> Tuple[UserProfile, Dict[str, MechanismEffectiveness]]:
        """
        Assign user to archetype cluster (Tier 1).
        
        Uses initial signals to find best-matching archetype.
        """
        # Score each archetype
        archetype_scores = {}
        for archetype_id, archetype in self._archetypes.items():
            score = self._score_archetype_match(archetype, context, signals)
            archetype_scores[archetype_id] = score
        
        # Select best archetype
        best_archetype_id = max(archetype_scores, key=archetype_scores.get)
        best_archetype = self._archetypes[best_archetype_id]
        
        # Create profile from archetype centroid
        profile = UserProfile(
            user_id=user_id,
            big_five=best_archetype.big_five_centroid,
            regulatory_focus=RegulatoryFocusState(
                promotion_strength=0.7 if best_archetype.regulatory_focus_tendency == "promotion" else 0.3,
                prevention_strength=0.7 if best_archetype.regulatory_focus_tendency == "prevention" else 0.3
            ),
            construal_level=ConstrualLevel(best_archetype.construal_tendency.upper()),
            cluster_id=best_archetype_id,
            data_tier=UserDataTier.IDENTIFIED,
            profile_confidence=0.5
        )
        
        # Store archetype assignment
        await self.graph.assign_user_to_archetype(user_id, best_archetype_id)
        
        return profile, best_archetype.mechanism_priors
    
    async def _bayesian_profile_building(
        self,
        user_id: str,
        context: Dict[str, Any],
        signals: Optional[SupraliminalSignals]
    ) -> Tuple[UserProfile, Dict[str, MechanismEffectiveness]]:
        """
        Build profile with Bayesian updates (Tier 2).
        
        Blends archetype priors with observed data.
        """
        # Get current profile from graph
        current_profile = await self.graph.get_user_profile(user_id)
        
        # Get archetype priors (if assigned)
        archetype_id = current_profile.cluster_id if current_profile else None
        if archetype_id and archetype_id in self._archetypes:
            archetype = self._archetypes[archetype_id]
            archetype_priors = archetype.mechanism_priors
        else:
            archetype_priors = await self.cache.get_population_priors()
        
        # Get observed effectiveness
        observed = await self.graph.get_user_mechanism_priors(user_id)
        
        # Bayesian blend (more weight to observed as data grows)
        blended_priors = {}
        for mechanism in MechanismType:
            if mechanism == MechanismType.EMERGENT:
                continue
            
            archetype_prior = archetype_priors.get(mechanism.value)
            observed_prior = observed.get(mechanism.value)
            
            if observed_prior and observed_prior.evidence_count > 0:
                # Weighted average based on evidence count
                obs_weight = min(0.8, observed_prior.evidence_count / 10)
                arch_weight = 1 - obs_weight
                
                blended = MechanismEffectiveness(
                    mechanism_id=mechanism.value,
                    success_rate=(
                        archetype_prior.success_rate * arch_weight +
                        observed_prior.success_rate * obs_weight
                    ) if archetype_prior else observed_prior.success_rate,
                    confidence=(archetype_prior.confidence * arch_weight +
                               observed_prior.confidence * obs_weight
                              ) if archetype_prior else observed_prior.confidence,
                    evidence_count=observed_prior.evidence_count
                )
            else:
                blended = archetype_prior
            
            if blended:
                blended_priors[mechanism.value] = blended
        
        # Update profile tier
        if current_profile:
            current_profile.data_tier = UserDataTier.EMERGING
            current_profile.profile_confidence = 0.6
        
        return current_profile, blended_priors
    
    async def _individual_optimization(
        self,
        user_id: str
    ) -> Tuple[UserProfile, Dict[str, MechanismEffectiveness]]:
        """
        Use individual profile (Tier 3).
        
        Individual priors dominate.
        """
        profile = await self.graph.get_user_profile(user_id)
        mechanism_priors = await self.graph.get_user_mechanism_priors(user_id)
        
        profile.data_tier = UserDataTier.ESTABLISHED
        profile.profile_confidence = 0.8
        
        return profile, mechanism_priors
    
    async def _personalized_exploration(
        self,
        user_id: str
    ) -> Tuple[UserProfile, Dict[str, MechanismEffectiveness]]:
        """
        Full personalization with exploration (Tier 4).
        
        May include exploration for mechanisms not yet tried.
        """
        profile = await self.graph.get_user_profile(user_id)
        mechanism_priors = await self.graph.get_user_mechanism_priors(user_id)
        
        # Add exploration bonus to under-tried mechanisms
        for mechanism in MechanismType:
            if mechanism == MechanismType.EMERGENT:
                continue
            
            prior = mechanism_priors.get(mechanism.value)
            if prior and prior.evidence_count < 20:
                # Thompson sampling exploration bonus
                exploration_bonus = 0.1 * (1 - prior.evidence_count / 20)
                prior.success_rate = min(0.95, prior.success_rate + exploration_bonus)
        
        profile.data_tier = UserDataTier.RICH
        profile.profile_confidence = 0.9
        
        return profile, mechanism_priors
    
    def _score_archetype_match(
        self,
        archetype: ArchetypeCluster,
        context: Dict[str, Any],
        signals: Optional[SupraliminalSignals]
    ) -> float:
        """Score how well a user matches an archetype."""
        score = 0.0
        
        for signal_name, (mean, std) in archetype.matching_signals.items():
            # Check if we have this signal
            value = None
            if signal_name in context:
                value = context[signal_name]
            elif signals:
                value = getattr(signals, signal_name, None)
            
            if value is not None:
                # Score based on distance from archetype mean
                z_score = abs(value - mean) / (std + 0.01)
                signal_score = max(0, 1 - z_score / 3)
                score += signal_score
        
        return score
```

## 6.4 LangGraph Integration:

```python
# Add cold start node to workflow

async def bootstrap_cold_start(state: DecisionState) -> DecisionState:
    """
    Bootstrap profile for cold start users.
    
    This node runs early in the workflow to ensure
    appropriate priors are available for all atoms.
    """
    cold_start = state.get("cold_start_service")
    user_id = state.get("user_id")
    context = state.get("context", {})
    signals = state.get("supraliminal_signals")
    
    # Get bootstrapped profile and priors
    profile, mechanism_priors = await cold_start.bootstrap_profile(
        user_id=user_id,
        context=context,
        signals=signals
    )
    
    return {
        **state,
        "user_profile": profile,
        "mechanism_priors": mechanism_priors,
        "user_tier": profile.data_tier,
        "cold_start_strategy": await cold_start.get_strategy(profile.data_tier)
    }
```

## 6.5 Validation Checklist

- [ ] User tier correctly determined from interaction count
- [ ] Anonymous users get contextual inference
- [ ] New users assigned to archetype clusters
- [ ] Archetype assignment stored in Neo4j
- [ ] Bayesian blending for emerging users
- [ ] Exploration bonus for rich users
- [ ] Cold start priors injected into AoT atoms
- [ ] Tier transitions trigger events
- [ ] Prometheus metrics for tier distribution

---

# PART 7: COPY GENERATION INTEGRATION (#15)

## 7.1 Integration Point Summary

**Source Specification**: `/mnt/project/ADAM_Enhancement_15_Personality_Matched_Copy_Generation_COMPLETE.md` (246KB)

**Critical Role**: This is ADAM's value delivery point—the personality-matched messaging that achieves 40-50% conversion lifts.

## 7.2 Copy Generation Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         COPY GENERATION FLOW                                │
│                                                                             │
│   Inputs from Other Components:                                             │
│   ═════════════════════════════                                             │
│                                                                             │
│   #02 Blackboard ──────► Zone 4 Decision: selected mechanisms               │
│   #10 Journey ─────────► Current journey state                              │
│   #13 Cold Start ──────► User personality profile                           │
│   #14 Brand Intelligence► Brand voice constraints                           │
│   #04 AoT ─────────────► Construal level, regulatory focus                  │
│                                                                             │
│   Copy Generation Process:                                                  │
│   ═══════════════════════                                                   │
│                                                                             │
│   ┌────────────────┐    ┌────────────────┐    ┌────────────────┐           │
│   │ Trait-Message  │───►│ Template       │───►│ Claude         │           │
│   │ Mapping        │    │ Selection      │    │ Generation     │           │
│   └────────────────┘    └────────────────┘    └────────────────┘           │
│          │                     │                     │                      │
│          ▼                     ▼                     ▼                      │
│   ┌────────────────┐    ┌────────────────┐    ┌────────────────┐           │
│   │ Personality    │    │ Thompson       │    │ Brand Voice    │           │
│   │ Mapping        │    │ Sampling       │    │ Enforcement    │           │
│   └────────────────┘    └────────────────┘    └────────────────┘           │
│                                                                             │
│   Output:                                                                   │
│   ═══════                                                                   │
│                                                                             │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │ Generated Copy:                                                     │  │
│   │ • Headline: "Discover Your Perfect Sound" (high openness)          │  │
│   │ • Body: "Explore premium audio..." (promotion framing)             │  │
│   │ • CTA: "Start Free Trial" (low commitment, abstract)               │  │
│   │                                                                     │  │
│   │ Audio Parameters (if voice):                                       │  │
│   │ • Speaking rate: 1.1x (matches conscientiousness)                  │  │
│   │ • Pitch variation: medium (matches extraversion)                   │  │
│   │ • Pauses: natural (matches content type)                           │  │
│   └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 7.3 Required Code Additions

### Copy Request/Response Models:

```python
# =============================================================================
# COPY GENERATION - Integration Models
# =============================================================================

class CopyRequestSource(str, Enum):
    """Source triggering copy generation."""
    AD_DECISION = "ad_decision"
    PREVIEW = "preview"
    A_B_TEST = "a_b_test"
    BATCH = "batch"


class CopyFormat(str, Enum):
    """Output format for copy."""
    TEXT_ONLY = "text_only"
    AUDIO_SCRIPT = "audio_script"
    SSML = "ssml"
    HTML = "html"


class CopyRequest(BaseModel):
    """Request for personality-matched copy generation."""
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source: CopyRequestSource
    
    # User context (from decision workflow)
    user_profile: UserProfile
    mechanism_activations: List[MechanismActivation]
    journey_state: Optional[str] = None
    
    # Brand context (from Brand Intelligence #14)
    brand_id: str
    brand_voice: Optional[Dict[str, Any]] = None
    
    # Product/ad context
    product_id: str
    product_attributes: Dict[str, Any]
    ad_format: str  # "banner", "audio", "video"
    
    # Copy constraints
    max_headline_length: int = 50
    max_body_length: int = 150
    required_elements: List[str] = Field(default_factory=list)
    
    # Output format
    format: CopyFormat = CopyFormat.TEXT_ONLY
    
    # Latency tier
    latency_requirement_ms: int = 100


class GeneratedCopy(BaseModel):
    """Generated personality-matched copy."""
    copy_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    request_id: str
    
    # Generated content
    headline: str
    body: str
    cta: str
    
    # Audio parameters (if applicable)
    audio_params: Optional[Dict[str, Any]] = None
    ssml: Optional[str] = None
    
    # Generation metadata
    template_used: Optional[str] = None
    generation_method: str  # "claude", "template", "cached"
    latency_ms: float
    
    # Psychological targeting
    personality_match_score: float
    mechanisms_addressed: List[str]
    trait_adaptations: Dict[str, str]
    
    # For learning
    expected_effectiveness: float
    confidence: float


class CopyPerformance(BaseModel):
    """Performance tracking for generated copy."""
    copy_id: str
    
    # Outcome
    impressions: int = 0
    clicks: int = 0
    conversions: int = 0
    
    # Calculated metrics
    ctr: float = 0.0
    conversion_rate: float = 0.0
    
    # Attribution
    personality_lift: Optional[float] = None  # Lift vs. generic copy
    mechanism_attribution: Dict[str, float] = Field(default_factory=dict)
```

### Copy Generation Service:

```python
class CopyGenerationService:
    """
    Personality-matched copy generation service.
    
    Integrates with:
    - Blackboard: Gets decision context
    - Brand Intelligence: Gets brand constraints
    - Cold Start: Gets user profile
    - Journey Tracking: Gets journey state
    - Gradient Bridge: Reports performance
    """
    
    def __init__(
        self,
        claude_client: Anthropic,
        graph: GraphService,
        cache: CacheService,
        brand_intelligence: BrandIntelligenceService,
        kafka: KafkaProducer
    ):
        self.claude = claude_client
        self.graph = graph
        self.cache = cache
        self.brand = brand_intelligence
        self.kafka = kafka
        
        # Template cache
        self._templates: Dict[str, CopyTemplate] = {}
    
    async def generate(self, request: CopyRequest) -> GeneratedCopy:
        """Generate personality-matched copy."""
        start_time = datetime.utcnow()
        
        # Check cache first (for repeat requests)
        cache_key = self._build_cache_key(request)
        cached = await self.cache.get_generated_copy(cache_key)
        if cached:
            return cached
        
        # Get brand voice constraints
        brand_voice = request.brand_voice or await self.brand.get_brand_voice(
            request.brand_id
        )
        
        # Determine generation method based on latency requirement
        if request.latency_requirement_ms < 50:
            # Template-based only
            copy = await self._generate_from_template(request, brand_voice)
        elif request.latency_requirement_ms < 100:
            # Try template, fall back to Claude
            copy = await self._generate_with_fallback(request, brand_voice)
        else:
            # Full Claude generation
            copy = await self._generate_with_claude(request, brand_voice)
        
        # Calculate latency
        copy.latency_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        # Cache result
        await self.cache.set_generated_copy(cache_key, copy)
        
        # Store in graph for learning
        await self.graph.store_generated_copy(copy)
        
        # Emit event
        await self.kafka.send(
            "copy_generation",
            CopyGeneratedEvent(
                copy_id=copy.copy_id,
                request_id=request.request_id,
                generation_method=copy.generation_method,
                latency_ms=copy.latency_ms
            )
        )
        
        return copy
    
    async def _generate_with_claude(
        self,
        request: CopyRequest,
        brand_voice: Dict[str, Any]
    ) -> GeneratedCopy:
        """Generate copy using Claude with personality matching."""
        # Build personality-aware prompt
        prompt = self._build_generation_prompt(request, brand_voice)
        
        # Call Claude
        response = await self.claude.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}]
        )
        
        # Parse response
        content = response.content[0].text
        headline, body, cta = self._parse_copy_response(content)
        
        # Calculate personality match
        match_score = self._calculate_personality_match(
            request.user_profile, headline, body, cta
        )
        
        return GeneratedCopy(
            request_id=request.request_id,
            headline=headline,
            body=body,
            cta=cta,
            generation_method="claude",
            personality_match_score=match_score,
            mechanisms_addressed=[m.mechanism_id for m in request.mechanism_activations],
            trait_adaptations=self._get_trait_adaptations(request.user_profile),
            expected_effectiveness=match_score * 0.8,
            confidence=0.7
        )
    
    def _build_generation_prompt(
        self,
        request: CopyRequest,
        brand_voice: Dict[str, Any]
    ) -> str:
        """Build personality-aware generation prompt."""
        profile = request.user_profile
        
        # Trait descriptions
        trait_instructions = []
        
        if profile.big_five.openness > 0.7:
            trait_instructions.append(
                "User is high in Openness: Use creative, imaginative language. "
                "Emphasize novelty, unique features, and aesthetic appeal."
            )
        elif profile.big_five.openness < 0.3:
            trait_instructions.append(
                "User is low in Openness: Use straightforward, practical language. "
                "Emphasize reliability, proven results, and traditional values."
            )
        
        if profile.big_five.conscientiousness > 0.7:
            trait_instructions.append(
                "User is high in Conscientiousness: Include specific details, "
                "numbers, and quality indicators. Emphasize reliability."
            )
        
        if profile.big_five.extraversion > 0.7:
            trait_instructions.append(
                "User is high in Extraversion: Use energetic, enthusiastic language. "
                "Emphasize social benefits and excitement."
            )
        elif profile.big_five.extraversion < 0.3:
            trait_instructions.append(
                "User is low in Extraversion: Use calm, thoughtful language. "
                "Emphasize personal benefits and quiet satisfaction."
            )
        
        # Regulatory focus framing
        if profile.regulatory_focus.promotion_strength > 0.6:
            frame_instruction = (
                "Frame message around GAINS and ACHIEVEMENTS: "
                "what they will gain, accomplish, or become."
            )
        elif profile.regulatory_focus.prevention_strength > 0.6:
            frame_instruction = (
                "Frame message around SECURITY and PROTECTION: "
                "what they will avoid losing, protect, or maintain."
            )
        else:
            frame_instruction = "Use balanced framing with both gains and security."
        
        # Construal level
        if profile.construal_level == ConstrualLevel.ABSTRACT:
            construal_instruction = (
                "Use ABSTRACT language: focus on 'why' and broader meaning, "
                "values, and identity implications."
            )
        else:
            construal_instruction = (
                "Use CONCRETE language: focus on 'how' and specific features, "
                "practical steps, and immediate benefits."
            )
        
        # Mechanism-specific instructions
        mechanism_instructions = []
        for activation in request.mechanism_activations:
            if activation.mechanism_id == "mimetic_desire":
                mechanism_instructions.append(
                    "Include social proof: what others are doing/choosing."
                )
            elif activation.mechanism_id == "scarcity":
                mechanism_instructions.append(
                    "Create urgency: limited availability or time."
                )
            elif activation.mechanism_id == "identity_construction":
                mechanism_instructions.append(
                    "Connect to identity: who they are or want to become."
                )
        
        # Brand voice
        brand_instruction = f"""
        Brand voice requirements:
        - Tone: {brand_voice.get('tone', 'professional')}
        - Vocabulary level: {brand_voice.get('vocabulary', 'general')}
        - Prohibited words: {brand_voice.get('prohibited', [])}
        """
        
        prompt = f"""Generate advertising copy for this product/service.

PRODUCT: {request.product_attributes.get('name', 'Product')}
DESCRIPTION: {request.product_attributes.get('description', '')}
KEY BENEFITS: {request.product_attributes.get('benefits', [])}

PERSONALITY TARGETING:
{chr(10).join(trait_instructions)}

FRAMING:
{frame_instruction}

LANGUAGE STYLE:
{construal_instruction}

PSYCHOLOGICAL MECHANISMS TO LEVERAGE:
{chr(10).join(mechanism_instructions)}

{brand_instruction}

CONSTRAINTS:
- Headline: max {request.max_headline_length} characters
- Body: max {request.max_body_length} characters
- Required elements: {request.required_elements}

Generate copy in this exact format:
HEADLINE: [headline text]
BODY: [body text]
CTA: [call to action text]
"""
        return prompt
    
    def _get_trait_adaptations(
        self,
        profile: UserProfile
    ) -> Dict[str, str]:
        """Get trait-specific adaptations applied."""
        adaptations = {}
        
        if profile.big_five.openness > 0.7:
            adaptations["openness"] = "creative_language"
        elif profile.big_five.openness < 0.3:
            adaptations["openness"] = "practical_language"
        
        if profile.big_five.conscientiousness > 0.7:
            adaptations["conscientiousness"] = "detailed_specifics"
        
        if profile.regulatory_focus.promotion_strength > 0.6:
            adaptations["regulatory_focus"] = "promotion_framing"
        elif profile.regulatory_focus.prevention_strength > 0.6:
            adaptations["regulatory_focus"] = "prevention_framing"
        
        if profile.construal_level == ConstrualLevel.ABSTRACT:
            adaptations["construal"] = "abstract_why"
        else:
            adaptations["construal"] = "concrete_how"
        
        return adaptations
```

## 7.4 Validation Checklist

- [ ] Copy request includes all required context
- [ ] Personality traits mapped to copy adaptations
- [ ] Regulatory focus determines gain/loss framing
- [ ] Construal level determines abstract/concrete language
- [ ] Mechanisms translated to copy elements
- [ ] Brand voice constraints enforced
- [ ] Latency tiers (template < Claude) work correctly
- [ ] Copy stored in Neo4j for learning
- [ ] Performance tracked back to copy variants
- [ ] Audio parameters generated for voice ads

---

# PART 8: ADDITIONAL COMPONENT INTEGRATIONS

## 8.1 Voice/Audio Processing (#07)

**Source**: `/mnt/project/ADAM_Enhancement_07_Voice_Audio_Processing_Pipeline_v2_COMPLETE.md` (127KB)

### Integration Points:

```python
# Add to SupraliminalSignals model:

class VoiceFeatures(BaseModel):
    """Voice features extracted from audio."""
    # Prosodic features
    speaking_rate: float  # words per minute
    pitch_mean: float
    pitch_variability: float
    
    # Affect indicators
    energy_level: float
    voice_quality: str  # "breathy", "creaky", "modal"
    
    # Authenticity signals
    filler_frequency: float
    hesitation_count: int
    
    # Emotional valence
    detected_emotion: str
    emotion_confidence: float


# Extend SupraliminalSignals:
class SupraliminalSignals(BaseModel):
    # ... existing fields ...
    voice_features: Optional[VoiceFeatures] = None
```

### Key Integration:
- Voice features feed into psychological state detection
- Audio affect informs arousal/approach-avoidance atoms
- Voice prosody used in audio ad generation (#15)

## 8.2 Brand Intelligence Library (#14)

**Source**: `/mnt/project/ADAM_Enhancement_14_Brand_Intelligence_Library_v3_COMPLETE.md` (206KB)

### Integration Points:

```python
class BrandProfile(BaseModel):
    """Brand psychological profile."""
    brand_id: str
    name: str
    
    # Brand personality (Aaker dimensions)
    sincerity: float
    excitement: float
    competence: float
    sophistication: float
    ruggedness: float
    
    # Brand archetype
    archetype: str  # "hero", "sage", "explorer", etc.
    
    # Voice parameters
    tone: str
    vocabulary_level: str
    prohibited_words: List[str]
    required_phrases: List[str]
    
    # Mechanism affinities
    mechanism_fit: Dict[str, float]  # which mechanisms work for this brand
```

### Key Integration:
- Brand profiles loaded for copy generation
- Brand-mechanism fit informs mechanism selection
- Brand voice constraints enforce consistency

## 8.3 Identity Resolution (#19)

**Source**: `/mnt/project/ADAM_Enhancement_19_COMPLETE.md` (98KB)

### Integration Points:

```python
class ResolvedIdentity(BaseModel):
    """Cross-platform resolved identity."""
    canonical_id: str  # ADAM's unified ID
    platform_ids: Dict[str, str]  # platform -> platform_id
    
    # Resolution confidence
    confidence: float
    resolution_method: str  # "deterministic", "probabilistic"
    
    # Household
    household_id: Optional[str] = None
    household_role: Optional[str] = None  # "primary", "secondary"
```

### Key Integration:
- Identity resolution runs before profile lookup
- Unified ID used across all components
- Household data informs targeting decisions

## 8.4 Explanation Generation (#18)

**Source**: `/mnt/project/ADAM_Enhancement_18_COMPLETE.md` (141KB)

### Integration Points:

```python
class DecisionExplanation(BaseModel):
    """Explanation of an ad decision."""
    decision_id: str
    
    # Audience-specific explanations
    user_explanation: str  # Simple, transparent
    advertiser_explanation: str  # Business-focused
    engineer_explanation: str  # Technical detail
    compliance_explanation: str  # Regulatory detail
    
    # Mechanism attribution
    mechanism_contributions: Dict[str, float]
    trait_influences: Dict[str, float]
    
    # Audit trail
    data_sources_used: List[str]
    reasoning_steps: List[str]
```

### Key Integration:
- Explanation generated post-decision
- Uses Blackboard Zone 4 decision state
- Stored for compliance and debugging

## 8.5 WPP Ad Desk Integration (#28)

**Source**: `/mnt/project/ADAM_Enhancement_28_WPP_Ad_Desk_Intelligence_Layer_v2_COMPLETE.md` (201KB)

### Integration Points:

```python
class BidRequest(BaseModel):
    """OpenRTB bid request with ADAM enrichment."""
    request_id: str
    
    # Standard OpenRTB fields
    imp: List[Dict[str, Any]]  # Impressions
    device: Dict[str, Any]
    user: Dict[str, Any]
    
    # ADAM enrichment
    adam_user_id: Optional[str] = None
    psychological_profile: Optional[UserProfile] = None
    mechanism_recommendations: Optional[List[MechanismRecommendation]] = None
    
    # Real-time context
    content_signals: Optional[Dict[str, Any]] = None


class BidResponse(BaseModel):
    """OpenRTB bid response with ADAM optimization."""
    request_id: str
    
    # Bid details
    bid_price: float
    creative_id: str
    
    # ADAM-generated creative
    ad_copy: Optional[GeneratedCopy] = None
    
    # Attribution
    decision_id: str  # For outcome tracking
```

### Key Integration:
- OpenRTB adapter translates to ADAM models
- Real-time bidding uses cached profiles
- Supply path optimization for cost efficiency

## 8.6 Model Monitoring (Gap20)

**Source**: `/mnt/project/ADAM_Gap20_Model_Monitoring_Drift_Detection.md` (71KB) + Supplement (67KB)

### Integration Points:

```python
class ModelPrediction(BaseModel):
    """Logged model prediction for monitoring."""
    prediction_id: str
    model_id: str
    model_version: str
    
    # Input features
    feature_vector: Dict[str, float]
    
    # Prediction
    prediction: Any
    confidence: float
    latency_ms: float
    
    # For drift detection
    timestamp: datetime


class DriftAlert(BaseModel):
    """Alert when model drift detected."""
    alert_id: str
    model_id: str
    drift_type: str  # "data", "concept", "label"
    severity: str
    
    # Detection details
    metric_name: str
    expected_value: float
    observed_value: float
    p_value: Optional[float] = None
```

### Key Integration:
- All model predictions logged for monitoring
- Drift detection runs continuously
- Alerts trigger retraining pipelines

## 8.7 Embedding Infrastructure (Gap21)

**Source**: `/mnt/project/ADAM_Gap21_Embedding_Infrastructure.md` (113KB) + Supplement (59KB)

### Integration Points:

```python
class EmbeddingRequest(BaseModel):
    """Request for embedding generation."""
    content: str
    modality: str  # "text", "audio", "behavior"
    domain: str  # "ad_copy", "user_query", etc.


class EmbeddingResult(BaseModel):
    """Generated embedding."""
    embedding: List[float]
    model_id: str
    dimension: int
    
    # Quality metadata
    confidence: float
```

### Key Integration:
- Embeddings used for semantic similarity
- Cross-modal alignment for audio-text matching
- Vector search for content retrieval

## 8.8 Temporal Pattern Learning (Gap23)

**Source**: `/mnt/project/ADAM_Gap23_Temporal_Pattern_Learning_COMPLETE.md` (130KB)

### Integration Points:

```python
class LifeEventDetection(BaseModel):
    """Detected life event from behavioral patterns."""
    user_id: str
    event_type: str  # "engagement", "pregnancy", "moving", etc.
    confidence: float
    
    # Detection details
    signals_used: List[str]
    detection_method: str
    
    # Timing
    estimated_event_date: Optional[datetime] = None
    detection_date: datetime


class DecisionStage(BaseModel):
    """User's stage in a decision journey."""
    user_id: str
    category: str  # Product category
    
    stage: str  # "unaware", "considering", "comparing", "ready"
    confidence: float
    
    # Progression
    time_in_stage: timedelta
    predicted_transition: Optional[str] = None
```

### Key Integration:
- Life events inform targeting relevance
- Decision stage affects copy generation
- Temporal patterns feed journey tracking

## 8.9 Adversarial Robustness (Gap25)

**Source**: `/mnt/project/ADAM_Gap25_Adversarial_Robustness_COMPLETE.md` (117KB)

### Integration Points:

```python
class FraudScore(BaseModel):
    """Fraud risk assessment."""
    user_id: str
    request_id: str
    
    # Scores
    overall_risk: float
    bot_probability: float
    signal_manipulation_probability: float
    
    # Decision
    action: str  # "allow", "challenge", "block"
```

### Key Integration:
- Fraud detection runs before ad decision
- Suspicious signals flagged
- Blocked traffic excluded from learning

---

# PART 9: UNIFIED FILE REFERENCE MATRIX

## 9.1 Quick Reference: Where to Find What

| What You Need | Primary File | Integration Bridge Section |
|---------------|--------------|---------------------------|
| Philosophical foundation | ADAM_EMERGENT_INTELLIGENCE_ARCHITECTURE.md | Part 1 |
| Neo4j schema | ADAM_EMERGENT_INTELLIGENCE_ARCHITECTURE.md §1.2 | Part 1 |
| Core Pydantic models | ADAM_IMPLEMENTATION_COMPANION.md Part 1 | Part 2-7 extend |
| Kafka events | ADAM_IMPLEMENTATION_COMPANION.md Part 2 | All parts extend |
| LangGraph workflow | ADAM_IMPLEMENTATION_COMPANION.md Part 3 | Part 3-6 extend |
| Cache service | ADAM_IMPLEMENTATION_COMPANION_PART2.md Part 5 | Part 2 |
| Learning propagator | ADAM_IMPLEMENTATION_COMPANION_PART2.md Part 6 | Part 5 |
| Discovery engine | ADAM_IMPLEMENTATION_COMPANION_PART2.md Part 7 | Part 5 |
| FastAPI layer | ADAM_IMPLEMENTATION_COMPANION_PART2.md Part 8 | Part 8 |
| Signal capture details | Enhancement #08 | Part 2 |
| Blackboard zones | Enhancement #02 | Part 3 |
| AoT atoms | Enhancement #04 | Part 4 |
| A/B testing | Enhancement #12 | Part 5 |
| Cold start | Enhancement #13 | Part 6 |
| Copy generation | Enhancement #15 | Part 7 |
| Voice processing | Enhancement #07 | Part 8.1 |
| Brand intelligence | Enhancement #14 | Part 8.2 |
| Identity resolution | Enhancement #19 | Part 8.3 |
| Explanations | Enhancement #18 | Part 8.4 |
| WPP integration | Enhancement #28 | Part 8.5 |
| Model monitoring | Gap20 + Supplement | Part 8.6 |
| Embeddings | Gap21 + Supplement | Part 8.7 |
| Temporal patterns | Gap23 | Part 8.8 |
| Adversarial robustness | Gap25 | Part 8.9 |

## 9.2 Implementation Checklist by Phase

### Phase 0: Infrastructure (Weeks 1-4)
- [ ] Neo4j cluster deployed with schema from Emergent Architecture §1.2
- [ ] Kafka cluster with topics from Implementation Companion Part 2
- [ ] Redis cluster with cache config from Implementation Companion Part2 §5
- [ ] Prometheus/Grafana with metrics from Implementation Companion Part 4
- [ ] Base Python project structure with Pydantic models

### Phase 1: Signal & Storage (Weeks 5-8)
- [ ] Signal Aggregation Pipeline (#08) - See Integration Bridge Part 2
- [ ] Embedding Infrastructure (Gap21) - See Integration Bridge Part 8.7
- [ ] Blackboard Architecture (#02) - See Integration Bridge Part 3
- [ ] Identity Resolution (#19) - See Integration Bridge Part 8.3

### Phase 2: Core Intelligence (Weeks 9-14)
- [ ] Atom of Thought DAG (#04) - See Integration Bridge Part 4
- [ ] Meta-Learning Orchestration (#03) - Reference Enhancement #03
- [ ] Verification Layer (#05) - Reference Enhancement #05
- [ ] Gradient Bridge (#06) - Reference Enhancement #06
- [ ] Cold Start Strategy (#13) - See Integration Bridge Part 6
- [ ] Extended Constructs (#27) - Reference Enhancement #27

### Phase 3: Content & Matching (Weeks 15-18)
- [ ] Brand Intelligence Library (#14) - See Integration Bridge Part 8.2
- [ ] Copy Generation (#15) - See Integration Bridge Part 7
- [ ] Voice/Audio Processing (#07) - See Integration Bridge Part 8.1
- [ ] Multimodal Fusion (#16) - Reference Enhancement #16

### Phase 4: Journey & Optimization (Weeks 19-22)
- [ ] Journey Tracking (#10) - Reference Enhancement #10
- [ ] A/B Testing Infrastructure (#12) - See Integration Bridge Part 5
- [ ] Temporal Pattern Learning (Gap23) - See Integration Bridge Part 8.8
- [ ] Latency-Optimized Inference (#09) - Reference Enhancement #09

### Phase 5: Enterprise & Platform (Weeks 23-28)
- [ ] Explanation Generation (#18) - See Integration Bridge Part 8.4
- [ ] WPP Ad Desk Integration (#28) - See Integration Bridge Part 8.5
- [ ] Model Monitoring (Gap20) - See Integration Bridge Part 8.6
- [ ] Adversarial Robustness (Gap25) - See Integration Bridge Part 8.9
- [ ] Feature Store (#30) - Reference Enhancement #30
- [ ] Psychological Validity Testing (#11) - Reference Enhancement #11

---

# PART 10: CLAUDE CODE OPERATIONAL GUIDE

## 10.1 Session Start Protocol

When beginning any implementation session in Claude Code/Cursor:

```
1. CONTEXT LOAD
   - Read this Integration Bridge for component overview
   - Read relevant section for current component
   - Load Emergent Architecture for philosophy/schema
   - Load Implementation Companion for code patterns

2. UNDERSTAND BEFORE CODE
   - Identify all dependencies from matrix (§1.2)
   - Verify dependent components exist
   - Understand integration points

3. IMPLEMENT WITH PATTERNS
   - Use Pydantic models from Companion
   - Use Kafka events from Companion
   - Follow LangGraph patterns from Companion
   - Add component-specific extensions per Bridge

4. VALIDATE
   - Check validation checklist for component
   - Verify Neo4j writes work
   - Verify Kafka events emit
   - Verify metrics exposed

5. INTEGRATE
   - Test with dependent components
   - Verify Blackboard state flows
   - Verify learning signals propagate
```

## 10.2 Common Integration Patterns

### Pattern 1: New Component Setup

```python
# Every new component follows this structure:

class ComponentService:
    def __init__(
        self,
        graph: GraphService,        # Always need graph
        cache: CacheService,        # Usually need cache
        kafka: KafkaProducer,       # Always need events
        blackboard: BlackboardService  # Need for request context
    ):
        self.graph = graph
        self.cache = cache
        self.kafka = kafka
        self.blackboard = blackboard
    
    async def process(self, request: ComponentRequest) -> ComponentResponse:
        # 1. Read from Blackboard
        context = await self.blackboard.read_zone(request.request_id, zone)
        
        # 2. Check cache
        cached = await self.cache.get(cache_key)
        if cached:
            return cached
        
        # 3. Read from graph
        data = await self.graph.query(...)
        
        # 4. Process
        result = self._process(data, context)
        
        # 5. Write to graph
        await self.graph.write(result)
        
        # 6. Write to Blackboard
        await self.blackboard.write_zone(request.request_id, zone, result)
        
        # 7. Emit event
        await self.kafka.send(topic, ComponentProcessedEvent(...))
        
        # 8. Cache result
        await self.cache.set(cache_key, result)
        
        return result
```

### Pattern 2: Learning Signal Emission

```python
# Every component that makes decisions should emit learning signals

async def emit_learning_signal(
    self,
    request_id: str,
    component_name: str,
    prediction: float,
    features_used: List[str]
):
    signal = LearningSignal(
        signal_id=str(uuid.uuid4()),
        source_component=component_name,
        timestamp=datetime.utcnow(),
        signal_type=LearningSignalType.PREDICTION,
        payload={
            "request_id": request_id,
            "prediction": prediction,
            "features": features_used
        }
    )
    
    # Add to Blackboard Zone 5
    await self.blackboard.append_learning_signal(request_id, signal.dict())
    
    # Emit to Kafka
    await self.kafka.send(
        "learning_signals",
        LearningSignalEvent(
            signal_id=signal.signal_id,
            source=component_name,
            prediction=prediction
        )
    )
```

### Pattern 3: Metrics Exposure

```python
# Every component exposes Prometheus metrics

from prometheus_client import Counter, Histogram, Gauge

COMPONENT_REQUESTS = Counter(
    'adam_component_requests_total',
    'Total component requests',
    ['component', 'status']
)

COMPONENT_LATENCY = Histogram(
    'adam_component_latency_seconds',
    'Component processing latency',
    ['component'],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0]
)

COMPONENT_CONFIDENCE = Histogram(
    'adam_component_confidence',
    'Component output confidence',
    ['component'],
    buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
)

# In component:
async def process(self, request):
    with COMPONENT_LATENCY.labels(component=self.name).time():
        result = await self._process(request)
    
    COMPONENT_REQUESTS.labels(component=self.name, status="success").inc()
    COMPONENT_CONFIDENCE.labels(component=self.name).observe(result.confidence)
    
    return result
```

## 10.3 Debugging Integration Issues

When components don't integrate correctly:

1. **Check Blackboard state**: Is data being written to correct zone?
2. **Check Kafka events**: Are events being emitted and consumed?
3. **Check Neo4j writes**: Are graph updates happening?
4. **Check cache invalidation**: Is stale data being served?
5. **Check dependency order**: Is dependent component initialized?

```python
# Debug helper
async def debug_integration_state(request_id: str):
    """Dump all integration state for debugging."""
    
    # Blackboard zones
    for zone in BlackboardZone:
        data = await blackboard.read_zone(request_id, zone)
        print(f"Zone {zone.value}: {json.dumps(data, indent=2)}")
    
    # Recent Kafka events
    events = await get_recent_events(request_id)
    print(f"Events: {json.dumps(events, indent=2)}")
    
    # Neo4j state
    graph_state = await graph.get_request_state(request_id)
    print(f"Graph: {json.dumps(graph_state, indent=2)}")
```

---

# PART 11: SUCCESS CRITERIA

## 11.1 Per-Component Success Metrics

| Component | Key Metric | Target | Measurement |
|-----------|------------|--------|-------------|
| Signal Capture | Throughput | 100K/sec | Flink metrics |
| Blackboard | Zone latency | <5ms | Redis metrics |
| AoT DAG | Atom latency | <20ms each | Prometheus |
| A/B Testing | Test velocity | 50+/week | Test count |
| Cold Start | Profile accuracy | >60% | Holdout validation |
| Copy Generation | Personality match | >0.7 | Scoring model |
| Identity Resolution | Match rate | >80% | Cross-platform |
| Overall Decision | E2E latency | <100ms | API metrics |

## 11.2 Integration Success Metrics

| Integration Point | Metric | Target |
|-------------------|--------|--------|
| Graph writes | Success rate | >99.9% |
| Kafka events | Delivery rate | >99.99% |
| Cache hit rate | Hot path | >90% |
| Learning signals | Propagation | All components |
| Cross-component | Data consistency | 100% |

## 11.3 Business Success Metrics

| Metric | Baseline | Target | Evidence |
|--------|----------|--------|----------|
| Conversion lift | 0% | 35%+ | A/B tests |
| Profile confidence | 30% | 80%+ | Validation set |
| Mechanism attribution | N/A | Clear attribution | Graph analysis |
| Emergent discoveries | 0 | 20+ | Discovery engine |

---

# APPENDIX A: ENHANCEMENT FILE QUICK REFERENCE

```
/mnt/project/
├── Core Architecture
│   ├── ADAM_MASTER_HANDOFF_v4.md (149KB) - Master overview
│   ├── ADAM_Engineering_Specification.md (97KB) - Original spec
│   └── ADAM_Cognitive_Learning_Engine_COMPLETE.md (114KB) - Learning engine
│
├── Reasoning Layer (#01-#06)
│   ├── ADAM_Enhancement_01_Bidirectional_Graph_Reasoning_Fusion.md
│   ├── ADAM_Enhancement_02_Shared_State_Blackboard_Architecture_v2_COMPLETE.md (340KB)
│   ├── ADAM_Enhancement_03_Meta_Learning_Orchestration_COMPLETE.md (112KB)
│   ├── ADAM_Enhancement_04_v3_Advanced_Atom_of_Thought.md (107KB)
│   ├── ADAM_Enhancement_05_Verification_Layer_COMPLETE.md (135KB)
│   └── ADAM_Enhancement_06_Gradient_Bridge_COMPLETE.md (212KB)
│
├── Signal & Processing (#07-#09)
│   ├── ADAM_Enhancement_07_Voice_Audio_Processing_Pipeline_v2_COMPLETE.md (127KB)
│   ├── ADAM_Enhancement_08_COMPLETE.md (158KB) - Signal aggregation
│   └── ADAM_Enhancement_09_Latency_Optimized_Inference_Engine_v2_COMPLETE.md (298KB)
│
├── Targeting & Optimization (#10-#16)
│   ├── ADAM_Enhancement_10_COMPLETE.md (206KB) - Journey tracking
│   ├── ADAM_Enhancement_11_Psychological_Validity_Testing_Framework_v2_COMPLETE.md
│   ├── ADAM_Enhancement_12_COMPLETE.md (158KB) - A/B testing
│   ├── ADAM_Enhancement_13_Cold_Start_Strategy_*.md (3 parts)
│   ├── ADAM_Enhancement_14_Brand_Intelligence_Library_v3_COMPLETE.md (206KB)
│   ├── ADAM_Enhancement_15_Personality_Matched_Copy_Generation_COMPLETE.md (246KB)
│   └── ADAM_Enhancement_16_Multimodal_Fusion_COMPLETE.md (70KB)
│
├── Enterprise (#17-#19, #27-#28)
│   ├── ADAM_Enhancement_17_Privacy_Consent_COMPLETE.md (121KB)
│   ├── ADAM_Enhancement_18_COMPLETE.md (141KB) - Explanations
│   ├── ADAM_Enhancement_19_COMPLETE.md (98KB) - Identity resolution
│   ├── ADAM_Enhancement_27_Extended_Psychological_Constructs.md (108KB)
│   └── ADAM_Enhancement_28_WPP_Ad_Desk_Intelligence_Layer_v2_COMPLETE.md (201KB)
│
├── Infrastructure (#29-#31)
│   ├── ADAM_Enhancement_29_Platform_Infrastructure_Foundation_COMPLETE.md (210KB)
│   ├── ADAM_Enhancement_30_Feature_Store_Real_Time_Serving_COMPLETE.md (98KB)
│   └── ADAM_Enhancement_31_Caching_Real_Time_Inference_COMPLETE.md (169KB)
│
├── Gap Closures (Gap20-Gap26)
│   ├── ADAM_Gap20_Model_Monitoring_Drift_Detection.md (71KB)
│   ├── ADAM_Gap21_Embedding_Infrastructure.md (113KB)
│   ├── ADAM_Gap23_Temporal_Pattern_Learning_COMPLETE.md (130KB)
│   ├── ADAM_Gap24_Multimodal_Reasoning_Fusion_COMPLETE.md (118KB)
│   ├── ADAM_Gap25_Adversarial_Robustness_COMPLETE.md (117KB)
│   └── ADAM_Gap26_Observability_Debugging_COMPLETE.md (72KB)
│
└── Supplements
    ├── ADAM_Enhancement_20_Supplement.md (67KB) - Monitoring additions
    └── ADAM_Enhancement_21_Supplement.md (59KB) - Embedding additions
```

---

**END OF ADAM INTEGRATION BRIDGE DOCUMENT**

**Document Statistics**:
- Total lines: ~3,200
- Components covered: 31
- Integration points detailed: 16
- Code examples: 25+
- Validation checklists: 9
- Reference matrices: 3

**Usage**: This document, combined with the three Emergent Intelligence Architecture documents, provides complete implementation guidance for ADAM. Reference the specific enhancement files only when deep-dive detail is needed for a particular component.
