# LUXY Ride Pilot — Readiness Checklist

## Brand
- **Brand**: LUXY Ride (luxyride.com)
- **Category**: Luxury Ground Transportation
- **Flight**: March 31 – April 29, 2026 (30 days)
- **Daily Budget**: $225
- **Channel**: Native (StackAdapt)

---

## Infrastructure

| Component | Status | Detail |
|-----------|--------|--------|
| Neo4j | RUNNING | 3,103 LUXY Ride bilateral edges, 52.8M total graph elements |
| Redis | RUNNING | 14 cache domains including RETARGETING (1h TTL) |
| FastAPI Production App | READY | Port 8000, all routes registered |
| BONG Population Priors | EXPORTED | `data/bong_population_priors.npz` from 200K edges, rank-13, calibration correction 1.302 applied |
| Intervention Record Storage | READY | JSONLine at `data/intervention_records/enriched_interventions.jsonl` |

## Data Foundation

| Data | Status | Detail |
|------|--------|--------|
| Bilateral Edges | 3,103 | LUXY Ride specific, 20 alignment dimensions per edge |
| Buyer Archetypes | 5 | careful_truster, status_seeker, easy_decider, skeptical_analyst, disillusioned |
| Research Effect Sizes | 42 | Calibrated with 0.62 lab-to-production factor |
| Mechanism Observation Models | 16 | 20-dim unit-normalized vectors per mechanism |
| BONG Calibration | OVERCONFIDENT | Correction applied: covariance inflated 1.302x. 14 active dims, 6 dead dims. |
| Dead Dimensions | 6 identified | brand_trust_fit, anchor_susceptibility_match, reactance_fit, linguistic_style_matching, mental_simulation_resonance, involvement_weight_modifier |

## System Components (All Tested)

### Core Inference
| Component | Test Status | Location |
|-----------|-------------|----------|
| AtomDAG (30+ reasoning atoms) | Operational | `adam/atoms/dag.py` |
| Bilateral Cascade (5-level) | Operational | `adam/api/stackadapt/bilateral_cascade.py` |
| Thompson Sampling | Operational | `adam/retargeting/engines/mechanism_selector.py` |
| HierarchicalPriorManager (6-level) | Operational | `adam/retargeting/engines/prior_manager.py` |

### BONG Multivariate Posteriors
| Component | Test Status | Location |
|-----------|-------------|----------|
| BONGUpdater (diagonal + low-rank) | 38/38 pass | `adam/intelligence/bong.py` |
| BuyerUncertaintyProfile (dual representation) | Integrated | `adam/intelligence/information_value.py` |
| Information Value (BONG joint entropy) | Operational | `adam/intelligence/information_value.py` |
| conditional_shift() | Operational | `adam/intelligence/bong.py` |
| propagated_barrier_impact() | Operational | `adam/intelligence/bong.py` |

### Diagnostic Reasoning
| Component | Test Status | Location |
|-----------|-------------|----------|
| DiagnosticReasoner (5-hypothesis) | 52/52 pass | `adam/retargeting/engines/diagnostic_reasoner.py` |
| Constraint graph (frustrated pairs, reactance, PKM, stage) | Operational | `adam/retargeting/engines/diagnostic_reasoner.py` |
| Polar opposite page switching | Operational | `adam/retargeting/engines/diagnostic_reasoner.py` |

### Retargeting Engine
| Component | Test Status | Location |
|-----------|-------------|----------|
| TherapeuticSequenceOrchestrator | 81/81 pass | `adam/retargeting/engines/sequence_orchestrator.py` |
| TouchBuilder (page prescription) | Operational | `adam/retargeting/engines/touch_builder.py` |
| Within-Subject Design (Enhancement #36) | Operational | `adam/retargeting/engines/repeated_measures.py` |
| Per-user page×mechanism posteriors | Operational | `adam/retargeting/models/within_subject.py` |

### Resonance Engineering
| Component | Test Status | Location |
|-----------|-------------|----------|
| ResonanceModel (Stage A/B/C) | Operational | `adam/retargeting/resonance/resonance_model.py` |
| Buyer uncertainty epistemic bonus | Integrated | `adam/retargeting/resonance/resonance_model.py` |
| PlacementOptimizer | Operational | `adam/retargeting/resonance/placement_optimizer.py` |
| Per-touch StackAdapt site_targeting | Integrated | `adam/retargeting/integrations/stackadapt_translator.py` |

### Learning & Evolution
| Component | Test Status | Location |
|-----------|-------------|----------|
| CounterfactualLearner | 26/26 pass | `adam/intelligence/counterfactual_learner.py` |
| Trilateral epistemic value | Operational | `adam/intelligence/trilateral_epistemic.py` |
| BONG PromotionTracker | Operational | `adam/intelligence/bong_promotion.py` |
| CausalStructureLearner | Scaffold ready | `adam/intelligence/causal_structure_learner.py` |
| EnrichedInterventionRecord emitter | Operational | `adam/retargeting/engines/intervention_emitter.py` |
| Mechanism probability logging | Integrated | `adam/retargeting/engines/mechanism_selector.py` |
| 15-step OutcomeHandler | Operational | `adam/core/learning/outcome_handler.py` |

## StackAdapt Configuration

| Item | Status | Detail |
|------|--------|--------|
| Advertiser Account | PENDING | Need StackAdapt account setup |
| Universal Pixel | PENDING | Need pixel ID from StackAdapt |
| Audience Segments | READY | 5 archetypes defined in `luxy_ride_audiences.json` |
| Campaign Structure | READY | 5 campaign groups, sequential touches per archetype |
| Creative Briefs | READY | Per-archetype, per-mechanism creative direction |
| Domain Whitelist | READY | `luxy_ride_domain_whitelist.csv` |
| Domain Blacklist | READY | `luxy_ride_domain_blacklist.csv` |
| Frequency Caps | READY | `luxy_ride_frequency_caps.json` |
| Dayparting | READY | `luxy_ride_dayparting.json` |
| Measurement Pixels | READY | 4 conversion events defined in `luxy_ride_measurement.json` |
| API Endpoints | READY | Creative Intelligence API, Conversion Webhook, Segment Upload |

## Campaign Files (Canonical Location)

```
campaigns/ridelux_v6/
├── luxy_ride_campaign_config.json    # Master config (updated with unified system)
├── luxy_ride_audiences.json          # 5 archetype segments
├── luxy_ride_creatives.json          # Per-touch creative copy
├── luxy_ride_measurement.json        # Updated with unified system metrics
├── luxy_ride_retargeting_rules.json  # Sequential touch rules
├── luxy_ride_site_profiles.json      # 32-dim page mindstate profiles
├── luxy_ride_dayparting.json         # Hourly bid multipliers
├── luxy_ride_frequency_caps.json     # Per-archetype caps
├── luxy_ride_domain_whitelist.csv    # Approved domains
├── luxy_ride_domain_blacklist.csv    # Excluded domains
├── PILOT_READINESS_CHECKLIST.md      # This file
├── STACKADAPT_IMPLEMENTATION_GUIDE.md
├── STACKADAPT_SETUP_CHECKLIST.md
└── INFORMATIV_SYSTEM_ARCHITECTURE.md
```

## Partner Documentation

| Document | Location | Audience |
|----------|----------|----------|
| Deployment Overview | `docs/INFORMATIV_STACKADAPT_DEPLOYMENT_OVERVIEW.md` | StackAdapt team |
| System Technical Reference | `docs/INFORMATIV_SYSTEM_TECHNICAL_REFERENCE.md` | Internal / Technical partners |
| Partner Overview | `docs/INFORMATIV_OVERVIEW_FOR_PARTNERS.md` | Business partners |

## Pre-Flight Checklist

- [ ] StackAdapt advertiser account created
- [ ] Universal Pixel installed on luxyride.com
- [ ] 4 conversion events configured (site_visit, pricing_view, booking_start, booking_complete)
- [ ] Audience segments uploaded to StackAdapt
- [ ] Campaign structure imported
- [ ] Creative variants uploaded
- [ ] Webhook URL configured for conversion events
- [ ] API endpoint accessible from StackAdapt DCO
- [ ] Neo4j running with 3,103 LUXY Ride edges
- [ ] Redis running with BONG priors loaded
- [ ] Intervention record emitter active
- [ ] BONG PromotionTracker initialized
- [ ] Daily monitoring dashboard configured
