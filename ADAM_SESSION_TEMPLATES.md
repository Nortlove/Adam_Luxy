# ADAM Session Templates
## Ready-to-Use Starting Points for Claude Code Sessions

**Purpose**: Copy these templates to start each session type correctly  
**Version**: 1.0  
**Date**: January 20, 2026

---

# HOW TO USE

1. Find the template matching your session type
2. Copy the "SESSION START" block into your Claude Code session
3. Load the listed documents
4. Follow the session structure

---

# TEMPLATE 1: Schema Setup Session

## Use For
- Phase 1 Sessions 1.1-1.2 (Neo4j Schema)
- Any schema modification work

## SESSION START
```
I'm implementing ADAM Neo4j schemas.

CONTEXT:
- I've loaded the Integration Bridge FINAL (schema sections)
- I've loaded the relevant entity specifications

TODAY'S GOAL:
Create Neo4j migration scripts for [Core/Amazon/iHeart] entities

DEPENDENCIES MET:
- Neo4j 5.x instance running
- Connection verified

PLEASE HELP ME:
1. Review the schema requirements from the loaded specs
2. Create the migration .cypher files
3. Include all indexes and constraints
4. Verify with test queries
```

## Documents to Load
- `ADAM_MASTER_IMPLEMENTATION_PACKAGE.md` (for context)
- `ADAM_Integration_Bridge_FINAL.md` (schema sections)
- Entity-specific spec (iHeart, Amazon, or Enhancement as needed)

## Expected Outputs
```
adam/infrastructure/neo4j/migrations/
├── 001_core_schema.cypher
├── 002_amazon_schema.cypher
├── 003_iheart_schema.cypher
└── 004_indexes.cypher
```

---

# TEMPLATE 2: Core Component Session

## Use For
- Phase 2 all sessions (Blackboard, Gradient Bridge, etc.)
- Any single-component implementation

## SESSION START
```
I'm implementing ADAM Enhancement #[XX]: [Component Name]

CONTEXT:
- I've loaded Enhancement #[XX] COMPLETE specification
- I've loaded relevant sections from the Integration Bridge

DEPENDENCIES MET:
[List dependencies and confirm they're implemented]

TODAY'S GOAL:
Implement the complete [Component Name] including:
- Pydantic models
- Core service
- Neo4j interactions
- API endpoints
- Unit tests

PLEASE HELP ME:
1. Create the directory structure
2. Implement models first
3. Implement the service
4. Add tests
5. Verify integration points
```

## Documents to Load
- `ADAM_MASTER_IMPLEMENTATION_PACKAGE.md`
- Enhancement #XX COMPLETE spec
- `ADAM_Integration_Bridge_FINAL.md` (component section)
- `ADAM_IMPLEMENTATION_COMPANION.md` (if need code patterns)

## Expected Outputs
```
adam/[category]/[component]/
├── __init__.py
├── models.py
├── service.py
├── [additional files per spec]
└── tests/
    └── test_[component].py
```

---

# TEMPLATE 3: iHeart Implementation Session

## Use For
- Phase 5 Sessions 5.1-5.5 (iHeart Ad Network)
- Any iHeart-specific work

## SESSION START
```
I'm implementing ADAM iHeart Ad Network Integration

CONTEXT:
- I've loaded the iHeart Ad Network Integration COMPLETE spec
- I've loaded the Integration Bridge Addendum for iHeart
- Phase 1-4 components are implemented

TODAY'S GOAL:
Implement [specific iHeart component]:
- [Data models / Ad Decision Service / Outcome Processing / etc.]

LATENCY REQUIREMENT:
Ad decision must complete in <100ms P95

PLEASE HELP ME:
1. Review the spec requirements
2. Implement the component
3. Ensure latency budget is met
4. Connect to Gradient Bridge for learning signals
5. Add comprehensive tests
```

## Documents to Load
- `ADAM_iHeart_Ad_Network_Integration_COMPLETE.md`
- `ADAM_Integration_Bridge_Addendum_iHeart.md`
- `ADAM_WPP_iHeart_Platform_Alignment.md` (for shared models)

## Expected Outputs
```
adam/platform/iheart/
├── models/
│   ├── station.py
│   ├── content.py
│   └── advertising.py
├── services/
│   ├── content_analysis.py
│   └── station_learning.py
├── ad_decision/
│   ├── service.py
│   └── response_builder.py
└── api/
    └── endpoints.py
```

---

# TEMPLATE 4: Amazon Pipeline Session

## Use For
- Phase 1 Sessions 1.3-1.4 (Amazon Data Pipeline)
- Amazon data processing work

## SESSION START
```
I'm implementing ADAM Amazon Dataset Processing Pipeline

CONTEXT:
- I've loaded the Amazon Dataset Processing Specification
- Neo4j schemas for Amazon entities are deployed

TODAY'S GOAL:
Implement the Amazon review processing pipeline:
- Data ingestion
- Linguistic feature extraction
- Big Five inference
- Archetype clustering

DATA SOURCE:
Amazon 1.2B+ verified purchase reviews
[Note if using sample data vs full dataset]

PLEASE HELP ME:
1. Implement the ingestion service
2. Implement feature extraction
3. Implement Big Five inference
4. Implement archetype clustering
5. Create the AmazonCorpusClient for WPP
```

## Documents to Load
- `ADAM_Amazon_Dataset_Processing_Specification.md`
- `ADAM_Enhancement_28_WPP_Ad_Desk_*_v2_COMPLETE.md` (AmazonCorpusClient interface)

## Expected Outputs
```
adam/data/amazon/
├── __init__.py
├── models.py
├── ingestion.py
├── features.py
├── inference.py
├── archetypes.py
└── corpus_client.py
```

---

# TEMPLATE 5: WPP Ad Desk Session

## Use For
- Phase 5 Sessions 5.6-5.10 (WPP Ad Desk)
- WPP-specific implementation

## SESSION START
```
I'm implementing ADAM WPP Ad Desk Enhancement #28

CONTEXT:
- I've loaded Enhancement #28 COMPLETE spec
- I've loaded the WPP-iHeart Platform Alignment
- iHeart integration is implemented
- Amazon pipeline provides the AmazonCorpusClient

TODAY'S GOAL:
Implement [specific WPP product]:
- Product-to-Inventory Match / Sequential Persuasion / Supply-Path Optimization

PLEASE HELP ME:
1. Review the product specification
2. Implement using shared models where applicable
3. Connect to psychological intelligence layer
4. Ensure cross-platform compatibility
5. Add tests
```

## Documents to Load
- `ADAM_Enhancement_28_WPP_Ad_Desk_*_v2_COMPLETE.md`
- `ADAM_WPP_iHeart_Platform_Alignment.md`
- `ADAM_Amazon_Dataset_Processing_Specification.md` (for AmazonCorpusClient)

## Expected Outputs
```
adam/platform/wpp/
├── __init__.py
├── products/
│   ├── inventory_match.py
│   ├── sequential.py
│   └── supply_path.py
├── adapter.py
└── api/
    └── endpoints.py
```

---

# TEMPLATE 6: Cross-Platform Session

## Use For
- Phase 5 Sessions 5.11-5.12 (Cross-Platform Integration)
- Any work involving both iHeart and WPP

## SESSION START
```
I'm implementing ADAM Cross-Platform Integration

CONTEXT:
- I've loaded the WPP-iHeart Platform Alignment spec
- Both iHeart and WPP integrations exist
- Identity Resolution (#19) is implemented

TODAY'S GOAL:
Implement cross-platform services:
- Unified profile service
- Mechanism effectiveness merging
- Journey state synchronization

KEY PRINCIPLE:
One user, one profile, shared across platforms

PLEASE HELP ME:
1. Implement shared models
2. Implement cross-platform profile service
3. Implement mechanism merging with platform weights
4. Implement journey synchronization
5. Test cross-platform scenarios
```

## Documents to Load
- `ADAM_WPP_iHeart_Platform_Alignment.md`
- `ADAM_Enhancement_19_COMPLETE.md`
- `ADAM_Integration_Bridge_Addendum_iHeart.md`

## Expected Outputs
```
adam/platform/shared/
├── __init__.py
├── models.py
├── profile_service.py
├── mechanism_merging.py
└── journey_sync.py
```

---

# TEMPLATE 7: Learning & Validation Session

## Use For
- Phase 6 all sessions
- A/B Testing, Validity, Meta-Learning, Monitoring

## SESSION START
```
I'm implementing ADAM Enhancement #[XX]: [Learning Component]

CONTEXT:
- I've loaded Enhancement #[XX] COMPLETE spec
- Gradient Bridge (#06) is implemented
- Platform integrations feed learning signals

TODAY'S GOAL:
Implement [A/B Testing / Validity / Meta-Learning / Monitoring]:
- Core service
- Integration with Gradient Bridge
- [Component-specific features]

PLEASE HELP ME:
1. Review the spec
2. Implement the service
3. Connect to Gradient Bridge
4. Ensure signals from both platforms are handled
5. Add tests
```

## Documents to Load
- Enhancement #XX COMPLETE spec
- `ADAM_Enhancement_06_Gradient_Bridge_COMPLETE.md` (integration points)

## Expected Outputs
```
adam/learning/[component]/
├── __init__.py
├── models.py
├── service.py
└── [component-specific files]
```

---

# TEMPLATE 8: Performance Optimization Session

## Use For
- Phase 7 all sessions
- Latency, Caching, Observability

## SESSION START
```
I'm implementing ADAM Performance Enhancement #[XX]: [Component]

CONTEXT:
- I've loaded Enhancement #[XX] COMPLETE spec
- Core system is implemented
- Baseline performance measured

TODAY'S GOAL:
Optimize [Latency / Caching / Observability]:
- [Component-specific goals]

PERFORMANCE TARGET:
- All production paths <100ms P95
- Cache hit rate >80%
- Full psychological trace capture

PLEASE HELP ME:
1. Review the spec
2. Implement optimizations
3. Measure improvement
4. Ensure no functionality regression
5. Add performance tests
```

## Documents to Load
- Enhancement #XX COMPLETE spec
- Baseline performance data (if available)

## Expected Outputs
```
adam/infrastructure/[component]/
├── __init__.py
├── [component files]
└── benchmarks/
```

---

# TEMPLATE 9: Integration Testing Session

## Use For
- Phase 8 all sessions
- E2E Testing, Load Testing, Production Readiness

## SESSION START
```
I'm implementing ADAM Integration Tests

CONTEXT:
- All components are implemented
- I've loaded the Integration Bridge FINAL
- Individual components pass unit tests

TODAY'S GOAL:
Create and run [E2E / Performance / Resilience] tests:
- [Specific test scenarios]

PLEASE HELP ME:
1. Design test scenarios
2. Implement test harness
3. Run tests
4. Analyze results
5. Fix any issues found
```

## Documents to Load
- `ADAM_MASTER_IMPLEMENTATION_PACKAGE.md` (checklists)
- `ADAM_Integration_Bridge_FINAL.md` (expected flows)

## Expected Outputs
```
adam/tests/
├── e2e/
│   ├── test_iheart_flow.py
│   ├── test_wpp_flow.py
│   └── test_cross_platform.py
├── performance/
│   ├── load_test.py
│   └── latency_benchmark.py
└── resilience/
    └── test_failures.py
```

---

# TEMPLATE 10: Specification Completion Session

## Use For
- Phase 0 all sessions
- Completing #01, #04, #27, etc.

## SESSION START
```
I'm completing ADAM Enhancement #[XX] specification

CONTEXT:
- I've loaded the existing partial spec(s)
- I understand the ADAM architecture from the Integration Bridge

TODAY'S GOAL:
Create a COMPLETE specification for #[XX] that includes:
- Complete Pydantic models
- Neo4j schema
- Service interfaces
- API endpoints
- Kafka events
- Prometheus metrics
- Testing framework
- Implementation timeline

QUALITY BAR:
Must match the quality of existing COMPLETE specs (see #26 as example)

PLEASE HELP ME:
1. Review existing partial spec(s)
2. Identify gaps
3. Write complete models
4. Write complete service specs
5. Add all integration points
6. Create implementation timeline
```

## Documents to Load
- Existing partial spec(s) for component
- `ADAM_Integration_Bridge_FINAL.md`
- One exemplary COMPLETE spec for reference (e.g., Gap26)

## Expected Output
- `ADAM_Enhancement_[XX]_[Name]_COMPLETE.md` (~80-150KB)

---

# QUICK REFERENCE: Which Template?

| Phase | Sessions | Template |
|-------|----------|----------|
| Phase 0 | 0.1-0.8 | Template 10: Specification Completion |
| Phase 1 | 1.1-1.2 | Template 1: Schema Setup |
| Phase 1 | 1.3-1.4 | Template 4: Amazon Pipeline |
| Phase 1 | 1.5-1.6 | Template 3: iHeart (data model only) |
| Phase 1 | 1.7-1.8 | Template 2: Core Component |
| Phase 2 | All | Template 2: Core Component |
| Phase 3 | All | Template 2: Core Component |
| Phase 4 | All | Template 2: Core Component |
| Phase 5 | 5.1-5.5 | Template 3: iHeart Implementation |
| Phase 5 | 5.6-5.10 | Template 5: WPP Ad Desk |
| Phase 5 | 5.11-5.12 | Template 6: Cross-Platform |
| Phase 6 | All | Template 7: Learning & Validation |
| Phase 7 | All | Template 8: Performance Optimization |
| Phase 8 | All | Template 9: Integration Testing |

---

**END OF SESSION TEMPLATES**
