# ADAM Platform Architecture Audit

> Last Updated: February 5, 2026

## Overview

**ADAM** (AI-Driven Asset & Decision Manager) is an enterprise psychological personalization platform for advertising optimization. The codebase contains **426+ Python files** across multiple module domains.

---

## Architecture Summary

### Core Architecture Pattern

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              ADAM Container                                 │
│                        (adam/core/container.py)                             │
│                    Unified Dependency Injection Root                        │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
         ┌────────────────────────────┼────────────────────────────┐
         ▼                            ▼                            ▼
┌─────────────────┐      ┌─────────────────────┐      ┌─────────────────────┐
│  Infrastructure │      │    Core Services    │      │  V3 Cognitive       │
│  (Phase 1)      │      │    (Phase 2)        │      │  Layers (Phase 4)   │
├─────────────────┤      ├─────────────────────┤      ├─────────────────────┤
│ • Neo4j Driver  │      │ • BlackboardService │      │ • EmergenceEngine   │
│ • Redis Cache   │      │ • InteractionBridge │      │ • CausalDiscovery   │
│ • Kafka Producer│      │ • MetaLearner       │      │ • TemporalDynamics  │
└─────────────────┘      │ • GradientBridge    │      │ • MetaCognitive     │
                         │ • Verification      │      │ • NarrativeSession  │
                         │ • ColdStart         │      │ • MechanismInteract │
                         └─────────────────────┘      └─────────────────────┘
                                      │
         ┌────────────────────────────┼────────────────────────────┐
         ▼                            ▼                            ▼
┌─────────────────┐      ┌─────────────────────┐      ┌─────────────────────┐
│  Reasoning      │      │  Behavioral         │      │  Workflow           │
│  (Phase 3)      │      │  Analytics (Phase 5)│      │  (Phase 6)          │
├─────────────────┤      ├─────────────────────┤      ├─────────────────────┤
│ • AtomDAG       │      │ • AnalyticsEngine   │      │ • HolisticWorkflow  │
│ • HolisticSynth │      │ • LearningBridge    │      │ • DecisionRouter    │
└─────────────────┘      │ • KnowledgeGraph    │      └─────────────────────┘
                         │ • HypothesisEngine  │
                         │ • KnowledgePromoter │
                         └─────────────────────┘
```

---

## Module Inventory

### 1. adam/core/ - Core Infrastructure
**Status: ACTIVE** | **Usage: HIGH**

| Component | File | Purpose | Dependencies |
|-----------|------|---------|--------------|
| `ADAMContainer` | `container.py` | DI container, initializes all services | All modules |
| `Infrastructure` | `dependencies.py` | FastAPI DI, singletons | Neo4j, Redis |
| `LearningComponents` | `dependencies.py` | Learning component manager | All learning modules |

**Submodules:**
- `adam/core/learning/` - Universal learning interfaces
  - `universal_learning_interface.py` - Base learning contracts
  - `component_integrations.py` - Pre-built learning integrations
  - `atom_learning_integrations.py` - Atom-specific learning
  - `orchestrator_learning_integration.py` - Campaign-level learning
  - `learned_priors_integration.py` - Bayesian prior injection
  - `thompson_warmstart.py` - Thompson Sampling warmstart

- `adam/core/synthesis/` - Decision synthesis
  - `holistic_decision_synthesizer.py` - Multi-source decision synthesis

---

### 2. adam/api/ - API Layer
**Status: ACTIVE** | **Usage: HIGH**

| Endpoint Group | File | Routes | Purpose |
|----------------|------|--------|---------|
| Decision API | `decision/router.py` | `/api/v1/decisions` | Main ad decision endpoint |
| Behavioral API | `behavioral/` | Multiple | Desktop/media behavioral endpoints |
| Health API | `health/router.py` | `/health` | Health checks |
| Monitoring API | `monitoring/router.py` | `/metrics` | Prometheus metrics |
| Learning API | `learning_endpoints.py` | Learning routes | Learning signal endpoints |
| Emergence API | `emergence_endpoints.py` | Emergence routes | Emergence discovery |

---

### 3. adam/atoms/ - Atom of Thought DAG
**Status: ACTIVE** | **Usage: HIGH**

**10 Atoms in DAG:**
| Atom | Class | Level | Purpose |
|------|-------|-------|---------|
| UserState | `UserStateAtom` | 1 | Foundation - current psychological state |
| ReviewIntelligence | `ReviewIntelligenceAtom` | 1b | Review corpus-based priors |
| PersonalityExpression | `PersonalityExpressionAtom` | 2 | Big Five expression in context |
| RegulatoryFocus | `RegulatoryFocusAtom` | 2 | Promotion vs prevention |
| ConstrualLevel | `ConstrualLevelAtom` | 2 | Abstract vs concrete |
| BrandPersonality | `BrandPersonalityAtom` | 2b | Brand-as-Person matching |
| RelationshipIntelligence | `RelationshipIntelligenceAtom` | 2c | Consumer-brand relationship |
| MechanismActivation | `MechanismActivationAtom` | 3 | Which mechanisms to activate |
| MessageFraming | `MessageFramingAtom` | 4 | Message framing strategy |
| AdSelection | `AdSelectionAtom` | 5 | Final ad selection |
| ChannelSelection | `ChannelSelectionAtom` | 6 | iHeart channel targeting |

**DAG Execution:** `adam/atoms/dag.py` - Topological ordering with parallel execution

---

### 4. adam/orchestrator/ - Campaign Orchestration
**Status: ACTIVE** | **Usage: HIGH**

| Component | File | Purpose |
|-----------|------|---------|
| `CampaignOrchestrator` | `campaign_orchestrator.py` | Unified entry point for campaigns |
| `GraphIntelligence` | `graph_intelligence.py` | Neo4j graph intelligence queries |
| Models | `models.py` | Campaign analysis result models |

**Note:** `campaign_orchestrator.py` is very large (119K+ characters)

---

### 5. adam/platform/ - Platform Integrations
**Status: ACTIVE** | **Usage: HIGH**

| Platform | Directory | Purpose |
|----------|-----------|---------|
| iHeart | `platform/iheart/` | 175M+ audio listener integration |
| WPP | `platform/wpp/` | WPP Ad Desk intelligence |
| Constructs | `platform/constructs/` | Psychological construct service |
| Shared | `platform/shared/` | Cross-platform utilities |

**iHeart Models:**
- `Station`, `Track`, `Artist`, `Podcast`
- `ListeningSession`, `ListeningEvent`
- `AdDecision`, `AdCreative`, `Campaign`, `AdOutcome`

**WPP Components:**
- `WPPAdDeskService` - WPP integration
- `AmazonPriorService` - Amazon review priors

---

### 6. adam/intelligence/ - Intelligence Services
**Status: ACTIVE** | **Usage: HIGH**

**Core Services:**
| Service | File | Purpose |
|---------|------|---------|
| `EmergenceEngine` | `emergence_engine.py` | Novel construct discovery |
| `GraphEdgeService` | `graph_edge_service.py` | Graph relationship intelligence |
| `CohortDiscoveryService` | `cohort_discovery.py` | Behavioral cohort identification |
| `UnifiedPsychologicalIntelligence` | `unified_psychological_intelligence.py` | Combined psychological analysis |

**Submodules:**
- `intelligence/scrapers/` - Data collection (Amazon, Google, Oxylabs, Social)
- `intelligence/graph/` - Graph schema and queries
- `intelligence/learning/` - Learning integration
- `intelligence/storage/` - Insight storage
- `intelligence/knowledge_graph/` - Neo4j knowledge graph builders

---

### 7. adam/infrastructure/ - Infrastructure Layer
**Status: ACTIVE** | **Usage: HIGH**

| Component | Directory/File | Purpose |
|-----------|----------------|---------|
| Redis | `redis/cache.py` | `ADAMRedisCache` - distributed caching |
| Kafka | `kafka/` | Event streaming, learning signals |
| Neo4j | `neo4j/client.py` | Graph database connectivity |
| Prometheus | `prometheus/metrics.py` | `ADAMMetrics` - observability |
| Alerting | `alerting/` | Alert definitions and notifiers |
| Resilience | `resilience/circuit_breaker.py` | Circuit breaker pattern |

---

### 8. adam/blackboard/ - Shared State Architecture
**Status: ACTIVE** | **Usage: HIGH**

**5-Zone Architecture:**
| Zone | Models | Purpose |
|------|--------|---------|
| Zone 1 | `zone1_context.py` | Request context (read-only) |
| Zone 2 | `zone2_reasoning.py` | Atom reasoning spaces |
| Zone 3 | `zone3_synthesis.py` | Synthesis workspace |
| Zone 4 | `zone4_decision.py` | Decision state |
| Zone 5 | `zone5_learning.py` | Learning signals |

**Service:** `BlackboardService` - Redis-backed working memory

---

### 9. adam/cold_start/ - Cold Start Strategy
**Status: ACTIVE** | **Usage: HIGH**

**Components:**
- Hierarchical Priors (Population → Cluster → Demographic → Archetype)
- 8 Psychological Archetypes (Explorer, Achiever, Connector, Guardian, Analyst, Creator, Nurturer, Pragmatist)
- Thompson Sampling with Beta posteriors
- Progressive Profiling (6 user data tiers)

**Key Files:**
- `service.py` - `ColdStartService`
- `thompson/sampler.py` - `ThompsonSampler`
- `archetypes/detector.py` - `ArchetypeDetector`
- `priors/` - Population and Demographic priors

---

### 10. adam/behavioral_analytics/ - Behavioral Intelligence
**Status: ACTIVE** | **Usage: HIGH**

**Comprehensive System:**
- Implicit signal collection (touch, swipe, scroll, hesitation)
- Hypothesis testing for signal-outcome relationships
- Research knowledge seeding (150+ validated items)
- Knowledge promotion pipeline

**Key Components:**
- `BehavioralAnalyticsEngine` - Main orchestrator
- `HypothesisEngine` - Statistical testing
- `ResearchKnowledgeSeeder` - Research foundation
- `BehavioralKnowledgeGraph` - Neo4j storage
- 13 Behavioral Classifiers (purchase intent, emotional state, cognitive load, etc.)

---

### 11. adam/meta_learner/ - Meta-Learning Orchestration
**Status: ACTIVE** | **Usage: HIGH**

**8 Learning Modalities:**
1. SUPERVISED_CONVERSION
2. SUPERVISED_ENGAGEMENT
3. UNSUPERVISED_CLUSTERING
4. UNSUPERVISED_GRAPH_EMBEDDING
5. REINFORCEMENT_BANDIT
6. REINFORCEMENT_CONTEXTUAL_BANDIT
7. CAUSAL_INFERENCE
8. SELF_SUPERVISED_CONTRASTIVE

**3 Execution Paths:** Fast (<50ms), Reasoning (500ms-2s), Exploration (<100ms)

---

### 12. adam/gradient_bridge/ - Learning Signal Routing
**Status: ACTIVE** | **Usage: HIGH**

**Capabilities:**
- Multi-level credit attribution
- 40+ enriched psychological features
- Empirical priors for Claude
- Graph learning integration
- Real-time signal propagation (<100ms via Kafka)

---

### 13. adam/verification/ - Verification Layer
**Status: ACTIVE** | **Usage: HIGH**

**4-Layer Architecture:**
1. Consistency - Cross-atom logical coherence
2. Calibration - Historical calibration adjustment
3. Safety - Vulnerable population protection
4. Grounding - Neo4j graph verification

---

### 14. adam/graph_reasoning/ - Bidirectional Graph Fusion
**Status: ACTIVE** | **Usage: HIGH**

**Components:**
- 10 Intelligence Sources
- `InteractionBridge` - Bidirectional graph ↔ reasoning
- `ConflictResolutionEngine` - Handles source contradictions
- `UpdateTierController` - Manages update latency tiers

---

### 15. src/v3/ - V3 Cognitive Layers
**Status: ACTIVE** | **Usage: HIGH**

**6 Advanced Engines:**
| Engine | Purpose |
|--------|---------|
| `EmergenceEngine` | Novel construct discovery |
| `CausalDiscoveryEngine` | Causal relationship inference |
| `TemporalDynamicsEngine` | Psychological state evolution |
| `MetaCognitiveEngine` | "Thinking about thinking" |
| `NarrativeSessionEngine` | User journey narratives |
| `MechanismInteractionEngine` | Mechanism synergies/conflicts |

---

## Supporting Modules

### Active & Integrated
| Module | Status | Usage |
|--------|--------|-------|
| `adam/llm/` | ACTIVE | LLM client, prompts, fusion |
| `adam/monitoring/` | ACTIVE | Health, drift detection, metrics |
| `adam/demo/` | ACTIVE | Demo server and API |
| `adam/config/` | ACTIVE | Settings and configuration |
| `adam/workflows/` | ACTIVE | LangGraph-style workflows |
| `adam/output/` | ACTIVE | Copy generation, brand intelligence |
| `adam/data/` | ACTIVE | Amazon local database access |
| `adam/learning/` | ACTIVE | Emergence and mechanism interactions |
| `adam/signals/` | ACTIVE | Linguistic and nonconscious signals |
| `adam/embeddings/` | ACTIVE | Embedding generation and storage |
| `adam/user/` | ACTIVE | User journey, identity, cold start |
| `adam/temporal/` | ACTIVE | State trajectory, learning integration |
| `adam/features/` | ACTIVE | Feature store integration |
| `adam/multimodal/` | ACTIVE | Multimodal fusion service |
| `adam/coldstart/` | ACTIVE | Unified cold start learning |
| `adam/audio/` | ACTIVE | Audio/voice processing |
| `adam/identity/` | ACTIVE | Identity resolution (RampID, UID2) |
| `adam/privacy/` | ACTIVE | Privacy service |
| `adam/validity/` | ACTIVE | Validity checks |
| `adam/explanation/` | ACTIVE | Decision explanations |
| `adam/experimentation/` | ACTIVE | A/B testing framework |
| `adam/performance/` | ACTIVE | Fast path optimization |
| `adam/inference/` | ACTIVE | Inference engine |

### Stub Modules (Empty/Placeholder)
| Module | Status | Notes |
|--------|--------|-------|
| `adam/ad_desk/` | STUB | Only docstring |
| `adam/adversarial/` | STUB | Only docstring |
| `adam/mechanisms/` | STUB | Only docstring |
| `adam/observability/` | STUB | Only docstring |
| `adam/synthesis/` | STUB | Only docstring |
| `adam/testing/` | STUB | Only docstring |

---

### 16. adam/competitive/ - Competitive Intelligence (NEW - Feb 2026)
**Status: ACTIVE** | **Usage: HIGH**

| Component | File | Purpose |
|-----------|------|---------|
| `CompetitiveIntelligenceService` | `intelligence.py` | Analyzes competitor ads |
| `MechanismDetection` | `intelligence.py` | Detects Cialdini mechanisms |
| `CounterStrategy` | `intelligence.py` | Game-theory counter-strategies |

**Capabilities:**
- Detects persuasion mechanisms in competitor copy
- Infers target archetypes from competitor strategies  
- Identifies psychological vulnerabilities
- Generates counter-strategies

---

### 17. adam/integration/ - Service Integration (NEW - Feb 2026)
**Status: ACTIVE** | **Usage: HIGH**

| Component | File | Purpose |
|-----------|------|---------|
| `DecisionEnrichmentService` | `decision_enrichment.py` | Pre/post decision enrichment |
| `EnrichedContext` | `decision_enrichment.py` | Identity + competitive context |

---

### 18. New Intelligence Services (Feb 2026)
**Status: ACTIVE** | **Usage: HIGH**

| Service | File | Purpose |
|---------|------|---------|
| `HelpfulVoteIntelligence` | `helpful_vote_intelligence.py` | Templates from reviews |
| `BrandCopyAnalyzer` | `brand_copy_intelligence.py` | Cialdini + Aaker |
| `JourneyIntelligenceService` | `journey_intelligence.py` | Co-purchase patterns |
| `AtomIntelligenceInjector` | `atom_intelligence_injector.py` | Pre-inject intelligence |
| `GraphPatternPersistence` | `pattern_persistence.py` | Neo4j persistence |

---

### 19. Enhanced Workflows (Feb 2026)

| Component | File | Purpose |
|-----------|------|---------|
| `SynergyOrchestrator` | `synergy_orchestrator.py` | Cross-system coordination |

---

### 20. Unified Learning Hub (Feb 2026)

| Component | File | Purpose |
|-----------|------|---------|
| `UnifiedLearningHub` | `unified_learning_hub.py` | Single signal router |
| `UnifiedSignalType` | `unified_learning_hub.py` | Standardized signals |

---

### 21. Enhanced API Endpoints (Feb 2026)

**Decision API** (`/api/v1/decisions`):
- New fields: `identifiers`, `competitor_ads`, `include_explanation`
- Response: `identity`, `explanation`, `competitive_insight`

**Intelligence API** (`/api/v1/intelligence`):
- `/brand-copy/analyze` - Cialdini + Aaker
- `/competitive/analyze` - Competitive landscape
- `/templates` - Persuasive templates
- `/journey/{asin}` - Purchase journeys

---

## External Packages (Top-Level)

| Package | Status | Integration |
|---------|--------|-------------|
| `flow_state/` | ACTIVE | Used by `unified_psychological_intelligence.py` |
| `need_detection/` | ACTIVE | Used by `unified_psychological_intelligence.py` |
| `psycholinguistic_graph2/` | ACTIVE | Used by `unified_psychological_intelligence.py` |

---

## Dependency Graph Issues

### CRITICAL: Missing Learning Integration Files
The following files are imported in `adam/core/container.py` but DO NOT EXIST:

| Import | Expected Location | Status |
|--------|-------------------|--------|
| `from adam.core.learning.event_bus import InMemoryEventBus` | `adam/core/learning/event_bus.py` | **MISSING** |
| `from adam.meta_learner.learning_integration import MetaLearnerLearning` | `adam/meta_learner/learning_integration.py` | **MISSING** |
| `from adam.gradient_bridge.learning_integration import GradientBridgeLearning` | `adam/gradient_bridge/learning_integration.py` | **MISSING** |
| `from adam.intelligence.emergence_engine import EmergenceEngineLearning` | Needs export | **MISSING EXPORT** |
| `from adam.behavioral_analytics.learning_integration import BehavioralAnalyticsLearning` | `adam/behavioral_analytics/learning_integration.py` | **MISSING** |

**Impact:** Learning signal routing initialization will fail with ImportError at startup. The container has try/except blocks that allow graceful degradation, but learning functionality will be impaired.

### Modules Defined But Never Imported
| Module | Directory | Status |
|--------|-----------|--------|
| `adam/ad_desk/` | Empty stub | Never imported by any production code |
| `adam/adversarial/` | Empty stub | Never imported by any production code |
| `adam/competitive/` | Empty stub | Never imported by any production code |
| `adam/observability/` | Empty stub | Never imported by any production code |
| `adam/synthesis/` | Empty stub | Never imported (note: `core/synthesis/` is active) |

### Self-Referencing Only (Not in Main Flow)
These modules are implemented but only reference themselves - not wired into the main decision flow:
- `adam/identity/` - Identity resolution implemented but not called from container
- `adam/explanation/` - Explanation service not in decision response flow
- `adam/experimentation/` - A/B framework not wired to decision API

---

## Initialization Flow

```
ADAMContainer.initialize()
├── Phase 1: Infrastructure
│   ├── Neo4j AsyncGraphDatabase.driver()
│   ├── ADAMRedisCache.connect()
│   └── get_kafka_producer()
│
├── Phase 2: Core Services
│   ├── BlackboardService(redis_cache)
│   ├── InteractionBridge(neo4j_driver, redis_cache)
│   ├── MetaLearnerService(blackboard, cache)
│   ├── GradientBridgeService(blackboard, bridge, cache)
│   ├── VerificationService(blackboard, bridge, cache)
│   └── get_cold_start_service()
│
├── Phase 3: Reasoning Components
│   ├── AtomDAG(blackboard, bridge)
│   └── HolisticDecisionSynthesizer(blackboard, verification, bridge)
│
├── Phase 4: V3 Cognitive Layers
│   ├── get_emergence_engine()
│   ├── get_causal_discovery_engine()
│   ├── get_temporal_dynamics_engine()
│   ├── get_metacognitive_engine()
│   ├── get_narrative_session_engine()
│   └── get_mechanism_interaction_engine()
│
├── Phase 5: Behavioral Analytics
│   ├── get_behavioral_knowledge_graph(neo4j_driver)
│   ├── get_hypothesis_engine()
│   ├── get_knowledge_promoter(hypothesis_engine, graph)
│   ├── get_behavioral_analytics_engine()
│   ├── get_behavioral_learning_bridge()
│   └── ResearchKnowledgeSeeder.seed_all_knowledge()
│
├── Phase 6: Workflow (deferred)
│
└── Phase 7: Learning Signal Routing  <-- BROKEN (missing files)
    ├── LearningSignalRouter(event_bus)
    └── register_component() for each learning-capable component
```

---

## User Defined Namespaces
- [Leave blank - user populates]

---

## Recommendations

### High Priority (Blocking Issues)
1. **Create missing learning integration files:** ✅ RESOLVED (Feb 2026)
   - Created `adam/core/learning/unified_learning_hub.py` (consolidates dual routers)
   - Learning signals now route correctly via Kafka + direct calls

2. **Export EmergenceEngineLearning** - Still pending

### Medium Priority (Architectural Cleanup)
3. **Remove or implement stub modules:**
   - `adam/ad_desk/` - Still stub
   - `adam/adversarial/` - Still stub
   - `adam/competitive/` - ✅ IMPLEMENTED (Feb 2026) - Full competitive intelligence
   - `adam/observability/` - Still stub
   - `adam/synthesis/` - Still stub

4. **Wire identity service** ✅ COMPLETED (Feb 2026) - Via `DecisionEnrichmentService`

5. **Add explanation service** ✅ COMPLETED (Feb 2026) - Via `DecisionEnrichmentService`

### Low Priority (Technical Debt)
6. **Refactor large files:**
   - `adam/orchestrator/campaign_orchestrator.py` (119K+ chars)

7. **Standardize __init__.py exports** across all modules

8. **Add type hints** to all public interfaces

### New Recommendations (Feb 2026)
9. **Import Neo4j patterns** after re-ingestion completes ⏳ PENDING
   - Run `scripts/import_reingestion_to_neo4j.py`

10. **Activate Graph Maintenance** periodically ⏳ PENDING
    - Run GDS algorithms for emergence detection
    - Use `GraphMaintenanceService`

11. **Complete re-ingestion for all 33 categories** 🔄 IN PROGRESS
    - Status: 8/33 categories complete (87M reviews, 115K templates)
    - Running: `scripts/run_full_reingestion.py`

---

## Intelligence Pipeline (NEW - Feb 2026)

### Pipeline Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    ADAM INTELLIGENCE PIPELINE                               │
└─────────────────────────────────────────────────────────────────────────────┘

Step 1: RE-INGESTION (run_full_reingestion.py)
   └── Process ~1B Amazon reviews
   └── Extract helpful vote patterns
   └── Build effectiveness matrix
   └── Status: 8/33 categories (87M reviews)

Step 2: IMPORT TO NEO4J (import_reingestion_to_neo4j.py)
   └── Store templates in graph
   └── Create effectiveness relationships
   └── Status: PENDING (waiting for Step 1)

Step 3: ENHANCED RE-INGESTION (enhanced_reingestion_with_archetypes.py)
   └── Deep archetype detection per review
   └── 500+ linguistic markers
   └── Multi-archetype effectiveness
   └── Status: PENDING

Step 4: BUILD INDEX (build_aggregated_effectiveness_index.py)
   └── Combine all category matrices
   └── Create fast lookup tables (<5ms)
   └── Universal mechanism detection
   └── Status: PENDING

Step 5: GRAPH ALGORITHMS (activate_graph_algorithms.py)
   └── PageRank for influence
   └── Community detection for clusters
   └── Centrality for bridge mechanisms
   └── Status: PENDING
```

### Pipeline Scripts

| Script | Purpose | Status |
|--------|---------|--------|
| `scripts/run_full_pipeline.py` | Master orchestrator | ✅ Ready |
| `scripts/run_full_reingestion.py` | Process all reviews | 🔄 Running |
| `scripts/import_reingestion_to_neo4j.py` | Store in graph DB | ✅ Ready |
| `scripts/enhanced_reingestion_with_archetypes.py` | Deep archetype detection | ✅ Ready |
| `scripts/build_aggregated_effectiveness_index.py` | Build fast lookup index | ✅ Ready |
| `scripts/activate_graph_algorithms.py` | Run GDS algorithms | ✅ Ready |

### To Run Complete Pipeline

```bash
# Check current status
python scripts/run_full_pipeline.py --status

# Run everything (waits for re-ingestion if needed)
python scripts/run_full_pipeline.py --all

# Or run individual steps
python scripts/run_full_pipeline.py --step import
python scripts/run_full_pipeline.py --step enhanced
python scripts/run_full_pipeline.py --step index
python scripts/run_full_pipeline.py --step algorithms
```

### LangGraph Enhancements (Feb 2026)

The `SynergyOrchestrator` has been enhanced with:

1. **Competitive Intelligence Node** - Analyzes competitor ads
2. **Deep Archetype Detection Node** - 500+ linguistic markers
3. **Personalized Template Selection** - Context-aware ranking
4. **Enhanced Decision Synthesis** - Multi-source fusion with boosts

New state fields:
- `competitor_ads` - For competitive analysis
- `user_review_text` - For deep archetype detection
- `competitive_intelligence` - Market saturation, counter-strategies
- `selected_templates` - Personalized, ranked templates

---

## Current Processing Status

### Re-ingestion Progress (as of Feb 5, 2026 15:22)

| Category | Reviews | Templates | Status |
|----------|---------|-----------|--------|
| All_Beauty | 701,528 | 1,015 | ✅ Complete |
| Appliances | 2,128,605 | 2,610 | ✅ Complete |
| Arts_Crafts_and_Sewing | 8,966,758 | 10,406 | ✅ Complete |
| Automotive | 19,955,450 | 13,428 | ✅ Complete |
| Baby_Products | 6,028,884 | 8,976 | ✅ Complete |
| Beauty_and_Personal_Care | 23,911,390 | 47,163 | ✅ Complete |
| CDs_and_Vinyl | 4,827,273 | 17,494 | ✅ Complete |
| Cell_Phones_and_Accessories | 20,812,945 | 14,814 | ✅ Complete |
| **TOTAL PROCESSED** | **87,332,833** | **115,906** | 8/33 |

### Remaining Categories (25)

Clothing_Shoes_and_Jewelry, Digital_Music, Electronics, Gift_Cards, 
Grocery_and_Gourmet_Food, Handmade_Products, Health_and_Household, 
Health_and_Personal_Care, Home_and_Kitchen, Industrial_and_Scientific, 
Kindle_Store, Magazine_Subscriptions, Movies_and_TV, Musical_Instruments, 
Office_Products, Patio_Lawn_and_Garden, Pet_Supplies, Software, 
Sports_and_Outdoors, Subscription_Boxes, Tools_and_Home_Improvement, 
Toys_and_Games, Unknown, Books, Fashion
