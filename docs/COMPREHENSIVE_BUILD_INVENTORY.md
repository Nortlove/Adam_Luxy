# ADAM Platform — Comprehensive Build Inventory

**Date:** 2026-04-29 (session-close, late evening)
**Author:** Compiled in the foreground after parallel-fork attempts were rate-limited server-side.
**Purpose:** Canonical reference of what is built so future sessions do not rebuild what exists. Chris's directive: "we shouldn't still be having things problem 24hrs after rebuilding things we already have... ensure that the new things we are building are being written in such a way that they will functioning seamlessly with the existing builds."

**Read this document FIRST every session, before writing any new code.**

---

## How to use this document

1. **Before building any new module**, search this file for the concept (e.g., "cohort", "fluency", "posture").
2. **If a module exists** that already does the thing, EXTEND or WIRE — do not rebuild.
3. **If the concept is missing entirely**, that is a real gap. Confirm by grepping the codebase before writing new code.
4. **For every new module**, identify the decision-time consumer FIRST (per Appendix E rule A). If no consumer exists, do not ship.
5. **Integration is first-class.** Every new module must declare what data shape it produces and which existing module consumes it. The platform fails when subsystems silo.

This document is pass-1. Sections marked `⚠ DEPTH-2 NEEDED` are surface-summary only; they need a deeper per-module read in a follow-up session before being treated as exhaustive.

---

## Surface-area summary

**1,008 Python files** across **56 top-level subsystems** totaling **~478,000 LOC** in `adam/`.

| Subsystem | Files | LOC | Wired status |
|---|---:|---:|---|
| `adam/intelligence/` | 287 | 157,791 | core production-wired hub |
| `adam/api/` | 65 | 26,837 | production HTTP surface |
| `adam/atoms/` | 48 | 26,313 | 30-atom DAG (production) |
| `adam/behavioral_analytics/` | 43 | 26,545 | mixed wired / data libraries |
| `adam/retargeting/` | 77 | 24,824 | engines, partial wiring |
| `adam/demo/` | 28 | 20,506 | DEMO-only |
| `adam/core/` | 22 | 19,441 | production core (learning, container) |
| `adam/platform/` | 59 | 13,012 | delivery adapters + blueprints |
| `adam/corpus/` | 34 | 9,035 | annotation + Neo4j ingestion |
| `adam/orchestrator/` | 12 | 8,752 | master decision graph (campaign_orchestrator: 2,570 LOC) |
| `adam/embeddings/` | 13 | 8,178 | vector embeddings |
| `adam/infrastructure/` | 26 | 7,952 | prometheus, neo4j client, resilience, redis |
| `adam/dsp/` | 15 | 7,660 | DSP integrations |
| `adam/data/` | 14 | 6,905 | data loaders (amazon, etc.) |
| `adam/workflows/` | 8 | 6,809 | LangGraph workflows (synergy_orchestrator, holistic_decision, etc.) |
| `adam/cold_start/` | 23 | 6,207 | Thompson sampling, archetype priors |
| `adam/fusion/` | 8 | 4,485 | fusion / prior_extraction |
| `adam/signals/` | 10 | 4,433 | nonconscious capture, linguistic |
| `adam/graph_reasoning/` | 11 | 4,862 | InteractionBridge, query_executor |
| `adam/identity/` | 21 | 3,951 | identity stability + resolution |
| `adam/integrations/` | 13 | 3,343 | StackAdapt + base adapter |
| `adam/gradient_bridge/` | 8 | 3,373 | credit attribution + signal_package |
| `adam/ml/` | 7 | 3,752 | ML primitives |
| `adam/blackboard/` | 10 | 2,882 | context blackboard with zones |
| `adam/output/` | 8 | 3,103 | output handling |
| `adam/services/` | 7 | 2,587 | bandit, archetype, brand_library, competitive_intel, graph_intelligence, temporal_patterns |
| `adam/meta_learner/` | 6 | 2,576 | meta-learner service |
| `adam/testing/` | 5 | 2,667 | e2e, integration_test_runner, synthetic_data_framework |
| `adam/verification/` | 11 | 2,405 | layers (calibration, consistency, grounding, safety) |
| `adam/user/` | 13 | 2,207 | cold_start, identity, journey, signal_aggregation |
| `adam/monitoring/` | 8 | 3,193 | monitoring router + checks |
| `adam/audio/` | 5 | 1,426 | audio integrations |
| `adam/temporal/` | 3 | 1,289 | state_trajectory, learning_integration |
| `adam/podcast/` | 4 | 1,265 | podcast integrations |
| `adam/features/` | 4 | 1,202 | feature engineering |
| `adam/llm/` | 5 | 1,199 | LLM client primitives |
| `adam/experimentation/` | 5 | 1,183 | experimentation service (mSPRT?) |
| `adam/multimodal/` | 4 | 1,128 | multimodal |
| `adam/config/` | 3 | 1,105 | settings |
| `adam/validity/` | 4 | 1,077 | validity checks |
| `adam/segments/` | 2 | 847 | segments |
| `adam/competitive/` | 2 | 791 | competitive |
| `adam/observability/` | 4 | 744 | observability primitives |
| `adam/inference/` | 3 | 674 | inference service |
| `adam/explanation/` | 3 | 551 | explanation surface |
| `adam/synthesis/` | 2 | 515 | streaming_synthesis |
| `adam/simulation/` | 2 | 523 | simulation engine |
| `adam/privacy/` | 3 | 486 | privacy primitives |
| `adam/integration/` | 2 | 455 | integration |
| `adam/performance/` | 6 | 1,423 | performance |
| `adam/creative/` | 3 | 1,157 | creative |
| `adam/ops/` | 8 | 3,373 | ops_intelligence + executors |
| `adam/coldstart/` | 2 | 31 | (NEAR-EMPTY — separate from cold_start, investigate) |
| `adam/sdk/` | 0 | 0 | (EMPTY — placeholder) |
| `adam/mechanisms/` | 1 | 2 | (EMPTY — placeholder) |
| `adam/ad_desk/` | 1 | 2 | (EMPTY — placeholder) |
| `adam/adversarial/` | 1 | 2 | (EMPTY — placeholder) |
| `adam/main.py` | 1 | ~250 | FastAPI startup (registers ~25 routers + 3 schedulers) |

---

## Production wiring graph (main.py — confirmed at startup)

**Routers registered in `adam/main.py`:**
- `decision_router` — `adam/api/decision/router.py`
- `intelligence_router` — `adam/api/intelligence/router.py`
- `iheart_router` — iHeartMedia integration router
- `wpp_router` — WPP integration router
- `stackadapt_router` — `adam/api/stackadapt/router.py` (the live bid path)
- `stackadapt_webhook_router` — `adam/api/stackadapt/webhook.py` (postbacks)
- `universal_router` — `adam/api/universal/router.py`
- `retargeting_router` — `adam/api/retargeting/router.py`
- `signals_router` — `adam/api/signals/router.py`
- `dashboard_router` — `adam/api/dashboard/router.py` (partner UI backend)
- `ops_router` — ops endpoints
- `monitoring_router` — `adam/api/monitoring/router.py`
- `learning_router` — `adam/api/learning_endpoints.py`
- `metrics_router` — `adam/api/metrics_endpoint.py`
- `health_router` — `adam/api/health/router.py`
- `admin_auth_router`, `admin_org_router`, `admin_campaign_router`, `admin_client_router` — admin surface

**Schedulers started at app startup:**
- `start_crawl_scheduler` — `adam/intelligence/page_crawl_scheduler.py`
- `start_strengthening_scheduler` — `adam/intelligence/daily/scheduler.py` (the 39 daily tasks)
- `start_ops_intelligence` — `adam/ops/intelligence.py`

**Initial state hydration on startup:**
- `bootstrap_pilot_data()` — `adam/api/admin/services/pilot_bootstrap.py`
- `initialize_system_sampler()` — `adam/core/learning/thompson_warmstart.py`
- `load_graph_archetype_priors()` — `adam/api/stackadapt/bilateral_cascade.py`
- `load_graph_dimension_priors()` — `adam/intelligence/information_value.py`
- `load_weights_from_gradient_field()` — `adam/intelligence/decision_probability.py`

---

## Daily Strengthening + DCIL Pipeline (39 scheduled tasks, all in `adam/intelligence/daily/`)

| Task | Module | Purpose |
|---|---|---|
| 01 | `task_01_competitive_intel.py` | Competitive intelligence |
| 02 | `task_02_publisher_drift.py` | Publisher drift detection |
| 03 | `task_03_news_cycle.py` | News cycle ambient state |
| 04 | `task_04_fatigue.py` | Fatigue detection |
| 05 | `task_05_review_refresh.py` | Reviews ingestion |
| 06 | `task_06_cultural_calendar.py` | Cultural calendar |
| 07 | `task_07_social_sentiment.py` | Social sentiment |
| 08 | `task_08_gradient_recompute.py` | Gradient field recompute |
| 09 | `task_09_brand_positioning.py` | Brand positioning |
| 10 | `task_10_temperature.py` | Category temperature |
| 11 | `task_11_inventory_discovery.py` | Inventory discovery |
| 12 | `task_12_taxonomy_builder.py` | Taxonomy builder |
| 13 | `task_13_reaction_collection.py` | Reaction collection |
| 14 | `task_14_ctv_enrichment.py` | CTV enrichment |
| 15 | `task_15_self_teaching.py` | Self-teaching |
| 16 | `task_16_page_gradients.py` | Page gradient fields |
| 17 | `task_17_copy_evolution.py` | Copy evolution |
| 18 | `task_18_recalibration.py` | composite_alignment recalibration |
| 19 | `task_19_resonance_evolution.py` | Resonance evolution |
| 20 | `task_20_quality_audit.py` | Learning quality audit |
| 21 | `task_21_tensor_archetypes.py` | Tensor archetypes |
| 22 | `task_22_causal_mediation.py` | Causal mediation analysis |
| 23 | `task_23_dsp_performance_pull.py` | DSP performance pull |
| 24 | `task_24_performance_normalizer.py` | Performance normalizer |
| 25 | `task_25_hypothesis_testing.py` | Hypothesis testing |
| 26 | `task_26_bilateral_analysis.py` | Bilateral analysis |
| 27 | `task_27_scope_determination.py` | Scope determination (I²) |
| 28 | `task_28_directive_generation.py` | Directive generation |
| 29 | `task_29_coherence_validation.py` | Coherence validation |
| 29.5 | `task_29_5_dcil_bridge_sync.py` | DCIL bridge sync (Loop β closure) |
| 29.6 | `task_29_6_horizon_adjudicator.py` | Horizon adjudicator (Loop γ auto-path) |
| 29.7 | `task_29_7_buyer_metaphor_scoring.py` | F1: buyer review metaphor scoring |
| 29.8 | `task_29_8_brand_metaphor_scoring.py` | F2: brand product copy metaphor scoring |
| 30 | `task_30_execution.py` | Campaign execution |
| 31 | `task_31_tier_reporting.py` | Tier A/B/C reporting |
| 32 | `task_32_rollback_monitor.py` | Rollback monitor |
| 33 | `task_33_decay_adjudicator.py` | Decay adjudicator (CONTINUE/RESTART/ABANDON) |
| **34** | **`task_34_hierarchical_bayes_refit.py`** | **Nightly HB refit (shipped 2026-04-29)** |
| **35** | **`task_35_causal_forest_fit.py`** | **Weekly CF fit (shipped 2026-04-29)** |

---

## 30-atom DAG (`adam/atoms/core/` — 33 atom files)

The DAG runs as production substrate. Per memory: "9 of 30 atoms have novel primitives; 17 are theory-in-docstring/boilerplate-in-impl wrappers." B3-LUXY brought 9 LUXY-load-bearing atoms to canonical-formula compliance.

**Atoms (sorted alphabetically, 33 files):**
- `ad_selection.py`
- `ambiguity_attitude.py`
- `autonomy_reactance.py`
- `base.py` *(BaseAtom abstract class)*
- `brand_personality.py`
- `channel_selection.py`
- `cognitive_load.py`
- `coherence_optimization.py`
- `construal_level.py`
- `construct_resolver.py`
- `cooperative_framing.py`
- `decision_entropy.py`
- `dsp_integration.py`
- `information_asymmetry.py`
- `interoceptive_style.py`
- `mechanism_activation.py` *(terminal node — emits final mechanism_scores)*
- `mechanism_registry.py`
- `message_framing.py`
- `mimetic_desire_atom.py`
- `motivational_conflict.py`
- `narrative_identity.py`
- `personality_expression.py`
- `persuasion_pharmacology.py`
- `predictive_error.py`
- `query_order.py`
- `regret_anticipation.py`
- `regulatory_focus.py`
- `relationship_intelligence.py`
- `review_intelligence.py`
- `signal_credibility.py`
- `strategic_awareness.py`
- `strategic_timing.py`
- `temporal_self.py`
- `user_state.py`

**DAG infrastructure** (`adam/atoms/`):
- `dag/` (subdir) — DAG infrastructure (referenced as `from adam.atoms.dag import AtomDAG`)
- `models/chain_attestation.py` — ChainAttestation primitive
- `orchestration/construct_dag.py` — construct DAG
- `orchestration/dag_executor.py` — executor
- `orchestration/langgraph_feedback.py` — LangGraph feedback
- `emergence_detector.py` — top-level emergence detector

⚠ DEPTH-2 NEEDED: per-atom B3-LUXY compliance status (which 9 are canonical, which 21 are still wrappers). Memory records the decision; per-atom verification needs a follow-up read.

---

## Spine modules (`adam/intelligence/spine/`)

After the 2026-04-29 cleanup commits (`9b6f192` + `1538e6b`), only 4 spine modules remain — the rest were duplicates of existing infrastructure and were deleted.

| Module | Purpose | Wired status |
|---|---|---|
| `phase_8_stackadapt_integration.py` | SapidRoundTripMonitor + assign_holdout + decay_identity_stability | Singleton accessor wired; sapid resolution wired (commit `d5d9f54`); decay_identity_stability NOT WIRED to a daily task |
| `phase_9_pre_launch.py` | mSPRT + pre-registration + sim framework | Substrate present; wired status DEPTH-2 NEEDED |
| `phase_10_launch_sequence.py` | 8 RED-criteria + LaunchPhase progression | `run_launch_gate_evaluation()` runner shipped 2026-04-29 (`d5d9f54`); no caller yet (would be a daily task or admin endpoint) |
| `spine_9_kelly_bid.py` | Kelly-fraction bid sizing | Wired status DEPTH-2 NEEDED |

---

## Cascade modulation chain (the bid-time decision path)

**File:** `adam/api/stackadapt/bilateral_cascade.py` (~3,100 LOC after this session's wires)

The order in which `result.mechanism_scores` is shaped per request — **this is the canonical integration spine for decision-time intelligence**:

1. **L1 archetype prior** — `level1_archetype_prior(archetype)` from cached priors
2. **L2 category posterior** — `level2_category_posterior(archetype, category, graph_cache, result)` reads BayesianPrior nodes
3. **L3 bilateral edges** — `level3_bilateral_edges(asin, archetype, graph_cache, ...)` reads edge_aggregates + ProductDescription; calls trilateral page-conditioned query when page_edge_dimensions provided; falls back to ADDITIVE_PAGE_SHIFT path (A14 flagged)
4. **L4 inferential transfer** — `level4_inferential_transfer(asin, archetype, graph_cache, result)` for low-edge-count products
5. **Mechanism hint application** — segment_id mechanism hint applied at low cascade levels
6. **Context modulation** — `apply_context_modulation(result, device, time_of_day, iab_category, page_url, ...)` modifies scores by environmental + goal context
7. **Synergy check** — `check_mechanism_synergy(result, archetype)` boosts mechanisms with archetype-synergy
8. **Per-user posterior modulation** — `apply_per_user_posterior_modulation(scores, buyer_id, graph_cache)` (shipped commit `0f5483e`) — empirical-Bayes shrinkage from cohort prior toward user's BONG posterior
9. **Cohort prior boost** — `apply_cohort_priors(scores, buyer_id, graph_cache)` (shipped commit `4dd5455`) — cohort-mechanism-effectiveness boost
10. **Predictive curiosity bonus** — `predictive_processing.get_curiosity_score(buyer_id, ad_features)` per mechanism (shipped commit `6f921a7` after relocation from realtime_decision_engine)
11. **Trilateral epistemic bonus** — `apply_trilateral_epistemic_bonus(scores, buyer_id, page_edge_dimensions, graph_cache)` (shipped commit `6458606`)
12. **F5 blend/vigilance weighting** — `apply_blend_vigilance_weighting(scores)` (attention-inversion enforcement)
13. **C2 processing-depth route gate** — `route_mechanism_scores_by_predicted_depth(scores, page_profile, device_type)` reads cognitive_load + bandwidth + competition + processing_mode + processing_fluency; gates vigilance mechanisms when depth low (fluency floor shipped commit `329bc8b`)
14. **M1 ε-floor sampler** — `_select_primary_with_logged_propensity(...)` Boruvka 2018 §2 — final action selection with logged propensity for WCLS/OPE validity

**Integration discipline going forward:**
- New decision-time modulators should slot into this chain at the appropriate stage
- Each modulator must declare: shape of input, shape of output, soft-fail behavior
- Mutating `result.mechanism_scores` is the canonical contract — that dict feeds the ε-floor sampler which feeds the bid response

---

## graph_cache as the integration backbone (`adam/api/stackadapt/graph_cache.py`)

`GraphIntelligenceCache` is the sync read surface for cascade decision-time queries. Singleton via `get_graph_cache()`. Adding new decision-time data sources should add a method to this class and surface it via the cascade.

**Cached state (each with refresh policy):**
- mechanism synergies + antagonisms (static after load)
- mechanism names
- BayesianPrior nodes (refreshed every 15 min — written by HB refit Task 34)
- category-graph intel
- product profiles (per ASIN)
- edge aggregates (per ASIN×archetype)
- gradient fields (per archetype:category) — written by Task 8
- buyer profiles (`BuyerUncertaintyProfile` per buyer_id, with Redis read-through)
- **cohort priors (per buyer_id, 30-min TTL)** — added 2026-04-29 commit `4dd5455`

**Public API (every method that the cascade or other consumers call):**
- `get_all_mechanism_confidences(category, archetype)`
- `get_universal_mechanism_priors(archetype)`
- `get_similar_categories(category, archetype)`
- `get_category_deviation(category, archetype)`
- `get_edge_aggregates(asin, archetype)`
- `get_product_profile(asin)`
- `get_gradient_field(archetype, category)`
- `get_buyer_profile(buyer_id)`
- `update_buyer_profile(buyer_id, edge_dimensions, signal_type, processing_depth_weight)`
- `get_cohort_priors(buyer_id)` — 2026-04-29 addition
- `get_health()`
- `refresh()`

---

## Outcome handler integration map (`adam/core/learning/outcome_handler.py`)

Production outcome write path. `handle_outcome(outcome_event)` receives webhook-derived events and dispatches updates across the system. Imports include:
- `bong.get_bong_updater()` — updates per-user BONG posteriors
- `causal_decomposition.get_causal_decomposition_engine()` — decomposes outcomes
- `causal_learning.record_causal_observation()` — records causal observations
- `cognitive_learning_system` — learning system updates
- `counterfactual_learner.get_counterfactual_learner()` — counterfactual logging
- `counterfactual_tracker.get_counterfactual_tracker()` — counterfactual tracking
- `goal_activation` — goal activation updates
- `gradient_fields` — gradient updates
- `inferential_hypothesis_engine` — hypothesis updates
- `information_value.load_graph_dimension_priors()` — IV updates
- `knowledge_propagation.get_knowledge_network()` — propagates outcomes through knowledge network
- `mechanism_taxonomy_runtime` — per-(mechanism_category × page_attentional_posture) outcome counts
- `multi_horizon_adjudication` — horizon-based adjudication
- `page_gradient_fields.get_page_gradient_accumulator()` — page gradient updates
- `per_atom_contribution_ingestion` — per-atom contribution ingestion (LUXY-specific contribution tracking)
- `prediction_engine.get_prediction_engine()` — prediction engine update

⚠ DEPTH-2 NEEDED: per-import full mapping of outcome → which-state-changes-where.

---

## adam/intelligence/ — top-level inventory (157 files)

⚠ DEPTH-2 NEEDED for per-module purpose. Below is the file list so future sessions can grep.

**Substantive modules (subset — not exhaustive):**

### Per-user posteriors / Bayesian
- `bong.py` — Bayesian Online Natural Gradient (BONG) per-user multivariate Gaussian posteriors
- `bong_promotion.py` — promotion criteria for BONG posterior maturity
- `hierarchical_bayes.py` — PyMC + NumPyro non-centered partial pooling; `run_nightly_hierarchical_refit()` is the canonical refit (Task 34 wraps)
- `predictive_processing.py` — `PredictiveProcessingEngine`, `BeliefState`, `CuriosityEngine`, `FreeEnergyCalculator`
- `bayesian_fusion.py` — Bayesian fusion primitive
- `information_value.py` — `BuyerUncertaintyProfile`, `compute_information_value`, `load_graph_dimension_priors`
- `gradient_fields.py` — `GradientField`, `GradientIntelligence`, `compute_optimization_priorities`

### Causal inference
- `causal_forest.py` — EconML CausalForestDML wrapper; `run_weekly_causal_forest_fit()` (Task 35 wraps)
- `causal_conformal.py` — distribution-free conformal lift wrap (lib-gated)
- `causal_discovery.py` — PC/FCI algorithms + ATE
- `causal_decomposition.py` — single-conversion decomposition
- `causal_dag_ensemble.py` — M7 ensemble (PC + FCI + GES + DAGMA + DoWhy)
- `causal_adjudicator.py` — Loop A→B cross-pollination, WhyLibrary writes
- `causal_learning.py` — micro-experiment framework
- `causal_structure_learner.py` — interventional structure learning
- `m2_pipeline.py` — M2 causal pipeline orchestrator
- `ope.py` — IPS, SNIPS, DR, SwitchDR, DRos, MIPS + `policy_gate()` (handoff §4.4)

### Page intelligence
- `page_intelligence.py` — page profiler
- `page_attentional_posture_substrate.py` — categorical posture (blend/vigilance/neutral) + Bayesian shrinkage
- `page_conditioned_query.py` — trilateral evidence query (filter 6.7M edges by page-state)
- `page_crawl_scheduler.py` — async page crawl + scheduler started in main.py
- `page_edge_bridge.py` — page-shift fallback path (A14 ADDITIVE_PAGE_SHIFT_FALLBACK)
- `page_edge_scoring.py` — full-width edge scoring
- `page_gradient_fields.py` — page-level gradient accumulator
- `page_similarity_index.py` — page similarity
- `processing_depth_router.py` — C2 depth predictor + route gate
- `pages/claude_feature_scoring.py` — Claude-driven feature scoring (register, primary metaphor, goal, temporal, fluency)
- `pages/entity_graph.py` — page entity graph
- `impression_state_resolver.py` — composes bid-request signals into reader position

### Cohort + non-stationarity
- `cohort_discovery.py` — Louvain community detection + cohort metadata
- `cohort_modulation.py` — cohort-prior boost adapter (NEW 2026-04-29)
- `mechanism_rotation.py` — rotation registry
- `online_learning_substrate.py` — LinkPosterior reads
- `mechanism_taxonomy.py` — canonical taxonomy (BLEND_COMPATIBLE/VIGILANCE_ACTIVATING)
- `mechanism_taxonomy_runtime.py` — per-(mechanism_category × posture) outcome counts

### Trilateral / metaphor / argument constitution
- `trilateral_epistemic.py` — buyer × page × mechanism epistemic value + cascade adapter
- `metaphor_alignment.py` — primary-metaphor alignment
- `metaphor_storage.py` — metaphor scoring storage
- `creative_metaphor_scoring.py` — creative metaphor scoring
- `brand_copy_metaphor_scoring.py` — brand copy metaphor (Task 29.8)
- `buyer_metaphor_scoring.py` — buyer review metaphor (Task 29.7)
- `argument_constitution.py` — argument constitution
- `argument_cache.py` — argument cache
- `argument_ranking.py` — `rank_variants_via_claude()`
- `constitutional_loop.py` — `run_constitutional_loop()`, `CAIResult`
- `cai_cross_family_critic.py` — CAI cross-family critique

### Defensive reasoning / WhyLibrary / chain rendering
- `why_library.py` — in-process WhyLibrary (`WhyEntry`, `record_why`, `query_why_for_recommendation`)
- `defensive_reasoning.py` — partner-facing defensive reasoning view
- `chain_rendering.py` — narrative chain renderer (Spine #6)
- `counterfactual_tracker.py` — counterfactual tracking
- `counterfactual_learner.py` — counterfactual learning
- `counterfactual_mechanisms.py` — counterfactual mechanisms

### Decision-time + propensity logging
- `realtime_decision_engine.py` — `compute_persuasion_decision()` (parallel to cascade; output goes into `persuasion_intelligence` API response field)
- `mrt_logging.py` — MRT logging
- `mrt_producer.py` — MRT singleton producer
- `decision_probability.py` — decision probability weights

### Information value / per-user
- `per_user_posterior_modulation.py` — N-of-1 cascade modulator (NEW 2026-04-29)
- `per_atom_contribution.py` — per-atom contribution
- `per_atom_contribution_ingestion.py` — ingestion of per-atom contribution

### Negative outcomes / recommendation_class
- `negative_outcome_adapters.py` — Stripe / Shopify / GenericJSON negative outcome adapters; `NegativeOutcomeAdapterRegistry.dispatch` now records sapid resolution (2026-04-29)
- `recommendation_class/` (subdir) — `adjudicator`, `archetype_compression`, `chain_attribution`, `conformal`, `graph`, `inferential_chain`, `plant_model`, `pre_registration`, `processing_depth_priors`, `projected_impact`, `sequential_schedule`, `a14_compromises`

### Inferential learning + knowledge propagation
- `inferential_learning_agent.py` — 6-level theory builder (OBSERVE → VALIDATE → HYPOTHESIZE → DESIGN → APPLY)
- `inferential_hypothesis_engine.py` — hypothesis engine
- `knowledge_propagation.py` — Hebbian-like cross-system propagation network
- `cognitive_learning_system.py` — cognitive learning system
- `prediction_engine.py` — prediction engine

### Goal / activation / brand
- `goal_activation.py` — goal activation
- `blend_fit.py` — blend fit primitive
- `blend_vigilance_weighting.py` — F5 attention-inversion weighting
- `brand_copy_extractor.py`, `brand_copy_intelligence.py`, `brand_persuasion_analyzer.py`, `brand_trait_extraction.py`

### Multi-horizon
- `multi_horizon_adjudication.py` — horizon-based adjudication

### Subdirectories
- `intelligence/daily/` — 39 scheduled tasks (above)
- `intelligence/spine/` — 4 spine modules (above)
- `intelligence/recommendation_class/` — Weakness #4 RecommendationClass primitive (12 files)
- `intelligence/campaign_intelligence/` — DCIL pipeline (audit_log, coherence_validator, config, directive_generator, execution_engine, generalizability, hypothesis_battery, models)
- `intelligence/dialogue_ledger/` — HMT v0.1 (elicitation, mood_probe, service, uncertainty_panel, models)
- `intelligence/graph/` — gds_runtime, reasoning_chain_generator, theory_schema, unified_psychological_schema, zero_shot_transfer
- `intelligence/knowledge_graph/` — brand_graph_builder, persuasion_susceptibility_graph, populate_psychological_graph, review_graph_builder, review_learnings_embedder
- `intelligence/relationship/` — detector, graph_builder, models, patterns, schema
- `intelligence/scrapers/` — amazon_playwright, amazon_reviews, base, brand_positioning_analyzer, enterprise_scraper, google_reviews, oxylabs_ai_client, oxylabs_client, product_page, social_scraper, unified_scraper, aggregator
- `intelligence/pages/` — claude_feature_scoring, entity_graph
- `intelligence/learning/` — psychological_learning_integration
- `intelligence/models/` — brand_personality, customer_intelligence
- `intelligence/outcome_simulation/` — theory_based_simulator
- `intelligence/pattern_discovery/` — brand_pattern_learner
- `intelligence/review_intelligence/` — base_extractor, machine_integration, orchestrator, extractors/
- `intelligence/sources/` — empty (placeholder)
- `intelligence/storage/` — empty (placeholder)

⚠ DEPTH-2 NEEDED: full per-module imports/imported-by mapping. ~80 of the 157 top-level intelligence files lack 1-line descriptions in this pass.

---

## Cascade master orchestrator (`adam/orchestrator/campaign_orchestrator.py` — 2,570 LOC)

**adam.* imports (confirmed via grep — there are also lazy/inline imports inside functions):**
- `adam.api.stackadapt.bilateral_cascade.run_bilateral_cascade`
- `adam.api.stackadapt.graph_cache.get_graph_cache`
- `adam.atoms.core.base.BaseAtom`
- `adam.atoms.dag.AtomDAG`
- `adam.blackboard.memory_blackboard`
- `adam.blackboard.service.get_blackboard_service`
- `adam.cold_start.models.enums.{CognitiveMechanism, ArchetypeID}`
- `adam.cold_start.service.get_cold_start_service`
- `adam.cold_start.thompson.sampler.get_thompson_sampler`
- `adam.core.container.get_container`
- `adam.core.decision_mode`
- `adam.core.learning.theory_learner.get_theory_learner`
- `adam.fusion.prior_extraction.get_prior_extraction_service`
- `adam.gradient_bridge.models.{credit, signals}`
- `adam.gradient_bridge.service.GradientBridgeService`
- `adam.graph_reasoning.bridge.interaction_bridge.InteractionBridge`
- `adam.intelligence.chain_rendering`
- `adam.intelligence.online_learning_substrate`
- `adam.intelligence.review_orchestrator.get_review_orchestrator`
- `adam.intelligence.unified_intelligence_service`
- `adam.meta_learner.{models, service}`
- `adam.orchestrator.{graph_intelligence, intelligence_prefetch, models}`
- `adam.retargeting.engines.prior_manager.get_prior_manager`

**Companion files in `adam/orchestrator/`:**
- `graph_intelligence.py` (1,044 LOC) — graph intelligence aggregator
- `intelligence_prefetch.py` (1,213 LOC) — intelligence pre-fetch service
- `models.py` (518 LOC) — orchestrator models

⚠ DEPTH-2 NEEDED: trace the exact decision graph stages within campaign_orchestrator (currently just have its imports).

---

## Retargeting engines (`adam/retargeting/engines/` — 30+ engines)

**The retargeting subsystem is large (77 files, 24,824 LOC).** Engines I've confirmed:

- `barrier_diagnostic.py` — barrier diagnosis
- `barrier_self_report.py` — barrier self-report
- `causal_mediation.py` — causal mediation analyzer (Task 22 consumer)
- `claude_argument_engine.py` — Claude argument generation
- `click_latency.py` — click latency
- `device_compat.py` — device compatibility
- `diagnostic_reasoner.py` — diagnostic reasoner
- `dimensionality_compressor.py` — dimensionality compressor
- `frequency_decay.py` — frequency decay
- `frustration.py` — frustration detector
- `graph_embeddings.py` — graph embeddings
- `impression_classifier.py` — impression classifier
- `intervention_emitter.py` — intervention emitter
- `learning_dimensions.py` — learning dimensions
- `learning_loop.py` — retargeting learning loop
- `mechanism_observation_models.py` — mechanism observation models
- `mechanism_selector.py` — mechanism selector
- `narrative_arc.py` — narrative arc
- `neural_linucb.py` — neural LinUCB bandit
- `nonconscious_profile.py` — nonconscious profile
- `options_framework.py` — options framework
- `organic_return.py` — organic return
- `prior_manager.py` — prior manager (orchestrator imports this)
- `processing_depth.py` — POST-impression processing depth (extends C2 with viewability)
- `prospect_theory.py` — prospect theory engine
- `puzzle_solver.py` — puzzle solver
- `recalibration.py` — recalibration
- `rupture_detector.py` — rupture detection (confrontation/withdrawal/decay)
- `mechanism_adme.py` — pharmacokinetic ADME for mechanisms
- `channel_capacity.py` — channel capacity

⚠ DEPTH-2 NEEDED: which retargeting engines are wired into the orchestrator vs orphan substrate.

---

## Platform delivery (`adam/platform/`)

### `adam/platform/delivery/` (delivery adapters)
- `base.py` — `BaseDeliveryAdapter` ABC + `SegmentPayload`, `CreativeGuidancePayload`, `DeliveryResult`, `DeliveryMetrics`
- `factory.py` — `ADAPTER_REGISTRY` + `create_adapter(adapter_type, ...)` (consumed by `adam/platform/blueprints/engine.py:247`)
- `dsp_adapter.py` — DV360, TradeDesk, **two StackAdapt classes**:
  - `StackAdaptAdapter` (deprecated REST; kept reachable via `'stackadapt_legacy_rest'` alias)
  - `StackAdaptGraphQLDeliveryAdapter` (NEW 2026-04-29; bridges BaseDeliveryAdapter ↔ canonical GraphQL adapter; registered as `'stackadapt'`)
- `audio_adapter.py` — Megaphone, Triton, SpotifyAdStudio
- `ssp_adapter.py` — Magnite, Prebid

### `adam/platform/blueprints/`
- `engine.py` — blueprint engine (calls `create_adapter`)
- `registry.py` — blueprint registry
- `router.py` — blueprint router

### `adam/integrations/stackadapt/` (canonical GraphQL surface)
- `adapter.py` — `StackAdaptAdapter(BasePlatformAdapter)` — GraphQL CreateAudience / CreateNativeAd / CreateCampaign mutations. THIS is the canonical write surface; `StackAdaptGraphQLDeliveryAdapter` wraps this.
- `graphql_client.py` — `StackAdaptGraphQLClient` — schema-corrected 2026-04-29 (CampaignConnection edges/node pattern, CampaignFilters, etc.)
- `data_taxonomy_client.py` — Data Taxonomy client

### `adam/integrations/base/`
- `adapter.py` — `BasePlatformAdapter` ABC + `PlatformCredentials`, `AdapterMode`, `SyncedSegment`, `SyncedCreative`, `CampaignConfig`, `PlatformCampaign`, `PlatformMetrics`

---

## Dashboard surface (`adam/api/dashboard/`)

- `router.py` — endpoints (consumes `adam.intelligence.causal_adjudicator.fetch_why_library` for `/why-library`; consumes other intelligence/ services)
- `service.py` — dashboard service
- `auth.py` — dashboard auth (`DashboardUser`, `require_user`)
- `models.py` — dashboard pydantic models
- `client_decisions_service.py` — client decisions
- `client_report_service.py` — client reports
- `system_insights_service.py` — system insights

⚠ DEPTH-2 NEEDED: every endpoint route + intelligence/ consumption graph.

---

## Admin surface (`adam/api/admin/`)

- `routers/auth_router.py`, `routers/org_router.py`, `routers/campaign_router.py`, `routers/client_router.py`
- `services/pilot_bootstrap.py` — bootstraps pilot data on startup
- `models/{user, domain, organization, campaign, creative, archetype, directive, tracker, report}.py`
- `migrations/002_seed_super_admin.py`
- `auth.py`, `db.py`, `dependencies.py`

---

## Cold start (`adam/cold_start/` — 23 files)

- `service.py` — `get_cold_start_service`
- `thompson/sampler.py` — `get_thompson_sampler` (production Thompson sampler)
- `archetypes/` — 8 archetype priors with differentiated Beta priors
- `priors/` — prior management
- `models/enums.py` — `CognitiveMechanism`, `ArchetypeID`
- `learning/`, `events/`, `cache/`, `workflow/`, `api/`

**Note:** `adam/coldstart/` (no underscore) exists separately with 2 files (~31 LOC). Investigate whether this is a stale rename — `cold_start` is the canonical version per orchestrator imports.

---

## Core learning (`adam/core/learning/`)

- `outcome_handler.py` — production outcome write path (mapped above)
- `construct_learning_loop.py` — construct learning loop
- `theory_learner.py` — `get_theory_learner` (consumed by orchestrator + main)
- `thompson_warmstart.py` — `initialize_system_sampler` (called at startup)
- `unified_learning_hub.py` — unified learning hub
- `effect_size_correction.py` — effect-size correction (consumed by stackadapt service)
- `signal_router.py` — signal routing
- `event_bus.py` — event bus
- `quality_audit.py` — quality audit
- `atom_learning_integrations.py`, `component_integrations.py`, `learned_priors_integration.py`, `orchestrator_learning_integration.py`, `universal_learning_interface.py`

---

## Workflows (`adam/workflows/` — 8 files, 6,809 LOC)

- `synergy_orchestrator.py` (1,017 LOC) — synergy orchestrator (LangGraph?)
- `holistic_decision_workflow.py` (520 LOC) — holistic decision workflow
- `dsp_impression_workflow.py` (269 LOC) — DSP impression workflow
- `intelligence_prefetch_nodes.py` (154 LOC) — intelligence prefetch nodes
- `unified_intelligence_node.py` (135 LOC) — unified intelligence node
- `susceptibility_intelligence_node.py` (187 LOC) — susceptibility intelligence
- `config.py` (86 LOC)

⚠ DEPTH-2 NEEDED: which workflows are production-wired vs experimental/legacy.

---

## Front-end + Deployment (per memory)

- **Railway** — production server LIVE per April session memory. Currently configured for the website + APIs.
- **Neo4j Aura** — production graph DB LIVE.
- **Front-end:** v4 built; v5 design spec exists at `website_v4_design_spec.md` (not yet built per memory). Includes GSAP ScrollTrigger, investor v6 infographics, custom cursor, clip-path reveals.
- **StackAdapt deployment:** Becca operates within StackAdapt agency; needs redeployment with April 15-16 changes per memory.

⚠ DEPTH-2 NEEDED: actual current state of the deployed front-end vs the design spec; whether any TypeScript/React code lives in this repo.

---

## This session's commits (2026-04-29 — what was shipped today)

In commit-time order:
1. `9b6f192` — chore(spine): delete duplicate spine modules (10 spine modules + tests)
2. `1538e6b` — chore(spine): delete spine_8_epistemic_bonus duplicate
3. `0f5483e` — feat(cascade): Track 2 — wire per-user BONG posteriors into cascade (the directive's central N-of-1 differentiator)
4. `ec8c489` — feat(scheduler): Tasks 34 + 35 — schedule HB nightly refit + CF weekly fit
5. `88b55a9` — feat(realtime): wire predictive_processing curiosity bonus (later relocated)
6. `6458606` — feat(cascade): wire trilateral_epistemic_value as bounded mechanism bonus
7. `bf8f953` — feat(ci): scripts/run_policy_gate.py — invocable handoff §4.4 gate
8. `6f921a7` — fix(cascade): relocate predictive curiosity wire from realtime engine to cascade (drift correction — original wire had no downstream consumer)
9. `4dd5455` — feat(cascade): wire cohort priors into cascade (Item 1 of 5)
10. `329bc8b` — feat(cascade): wire fluency floor as decision-time hard constraint (Item 2)
11. (Item 3 skipped with rationale — WhyLibrary cascade-side wire would lack structured signal)
12. `9649941` — feat(platform): activate StackAdapt write paths via GraphQL adapter (Item 4, initial — had duplication)
13. `d5d9f54` — feat(spine): Phase D sub-items 1+3 — sapid wire + 8-RED aggregator runner (Item 5, partial — sub-items 2/4/5 skipped with rationale)
14. `2ee9522` — fix(platform): eliminate CreateAudience mutation duplication (audit-driven correction)

**Test count:** 2,596 → 2,696 (+100 net new regression tests, all green).

---

## Integration patterns to honor going forward

1. **Decision-time consumers come first.** Per Appendix E rule (A): no measurement without an immediate decision-time consumer. Every new module must declare its consumer BEFORE the first commit. The 2026-04-29 commit `88b55a9` shipped a wire whose output had zero consumers in the codebase — caught and corrected by `6f921a7` after a grep audit. This is the failure mode to prevent.

2. **The cascade is the canonical decision-time integration spine.** New decision-time intelligence should slot into `run_bilateral_cascade` at the appropriate stage in the modulation chain (see "Cascade modulation chain" section above). Mutating `result.mechanism_scores` is the contract — that dict feeds the ε-floor sampler which feeds the bid response.

3. **graph_cache is the sync read backbone.** New decision-time data sources should add a method to `GraphIntelligenceCache` and surface it via the cascade. Async-only sources need a sync bridge (see `cohort_modulation.py` for the canonical pattern).

4. **outcome_handler is the canonical outcome-time write path.** New learning loops should plug into outcome_handler's dispatch list, not run as separate event listeners that bypass it.

5. **Daily scheduler is the canonical batch-job surface.** New batch jobs (refit, recompute, audit) should be registered as a `DailyStrengtheningTask` subclass and added to `_register_all_tasks()` in `adam/intelligence/daily/scheduler.py`.

6. **Discipline rule (B3-LUXY a/b/c/d) on every new module:**
   - (a) Canonical formula citation in code + paper:section reference
   - (b) Regression tests pinning published anchors / known boundaries
   - (c) calibration_pending=True flag where constants aren't pilot-derived
   - (d) Honest tag where (a)+(b)+(c) aren't fully met — wrappers stay tagged as "theory-in-docstring"

7. **Default to deletion when ambiguous.** If a wire has no clear decision-time consumer, do not ship it — delete the substrate or skip with rationale. See Item 3 (causal_adjudicator → WhyLibrary) skip from this session for the canonical pattern.

8. **Survey BEFORE building.** Every new module starts with a grep across the codebase for existing implementations of the concept. Cost of a 30-second survey is one message; cost of duplication is days of disconnected substrate (see the 19-commit duplication this session opened with).

---

## Known gaps for tomorrow's deeper read (DEPTH-2)

The following sections of this document are surface-summary only and need a per-module read to be exhaustive:

1. **adam/intelligence/ per-module purpose** — ~80 of 157 top-level files lack a 1-line description here. Worst case, grep returns enough; best case, a focused read pass fills in.
2. **Per-atom B3-LUXY compliance** — which 9 of 30 atoms have canonical formulas + tests vs which 21 are still wrappers. Memory records the decision; per-atom verification needed.
3. **adam/orchestrator/campaign_orchestrator.py decision graph stages** — the 2,570-LOC orchestrator's actual stage-by-stage flow.
4. **adam/api/dashboard/router.py endpoint inventory** — every route + every intelligence/ consumption.
5. **adam/retargeting/engines/ wired-vs-orphan map** — 30+ engines; which are consumed by the orchestrator?
6. **adam/workflows/ production-vs-experimental status** — the 1,017-LOC `synergy_orchestrator.py` and siblings need verification.
7. **adam/services/ — wrappers vs independents** — bandit, archetype, brand_library, etc.
8. **adam/user/ vs adam/cold_start/ vs adam/identity/** — three subsystems with overlapping concerns; clear ownership map needed.
9. **adam/coldstart/ (no underscore) vs adam/cold_start/** — investigate the two-directory situation.
10. **Orphan modules across the codebase** — every .py file with zero adam.* consumers in production paths.
11. **Two-StackAdaptAdapter clean-up status** — confirmed mapped above; verify no other StackAdapt stragglers.
12. **adam/experimentation/** — does it contain mSPRT? (audit doc flagged as a verification gap)
13. **adam/identity/** vs `phase_8.decay_identity_stability` — schema for identity_stability needs design (deferred from Item 5 sub-item 2 this session).

---

## Anti-rebuild discipline checklist (use BEFORE writing any new module)

```
[ ] Grep the codebase for the concept:
    rg -t py "concept_name" adam/

[ ] Search this inventory document:
    grep -i "concept_name" docs/COMPREHENSIVE_BUILD_INVENTORY.md

[ ] If a module exists for the concept:
    [ ] Read its public API
    [ ] Read its tests
    [ ] Decide: extend, wire, or honestly skip

[ ] If extending an existing module is the right call, prefer that over building new

[ ] If building new IS the right call:
    [ ] Identify the decision-time consumer FIRST
    [ ] Verify the consumer exists via grep
    [ ] Declare integration shape: what input, what output, who reads it
    [ ] Apply discipline rule (a/b/c/d)
    [ ] Write the regression test pinning the integration contract
```

---

## How this document gets updated

- After every session, append the session's commits to "This session's commits" with their integration impact.
- When a DEPTH-2-NEEDED section gets a deeper read, replace the surface summary with the per-module detail.
- When a wire ships, update the relevant subsystem section to mark the integration as wired.
- Treat this document as canonical — if it's wrong, fix it; don't work around it.

---

# APPENDIX A — DEEP MODULE INVENTORY (per-module purpose strings)

**Methodology:** Direct reads of every Python file's docstring across the codebase. LOC and one-line purpose for each. Compiled 2026-04-29/30 after the agent-fork approach hit server-side rate limits — this was generated from local file reads, the only reliable approach.

## A.1 — `adam/intelligence/` top-level (157 modules)

### Per-user posteriors / Bayesian
| Module | LOC | Purpose |
|---|---:|---|
| `bong.py` | 735 | Multivariate Gaussian posteriors with diagonal + low-rank precision (BONG) |
| `bong_promotion.py` | 159 | Tracks criteria for promoting BONG from additive to authoritative |
| `hierarchical_bayes.py` | 512 | PyMC + NumPyro non-centered partial pooling — Handoff §3.2 |
| `predictive_processing.py` | 622 | PredictiveProcessingEngine + BeliefState + CuriosityEngine + FreeEnergyCalculator |
| `bayesian_fusion.py` | 528 | Bayesian Fusion Engine — The Compounding Flywheel |
| `information_value.py` | 991 | BuyerUncertaintyProfile + Information Value Bidding |
| `gradient_fields.py` | 727 | Psychological Gradient Fields — ∂P(conv)/∂align_dim per cell |
| `per_user_posterior_modulation.py` | 270 | Cascade N-of-1 posterior modulator (NEW 2026-04-29) |
| `cohort_modulation.py` | 118 | Cohort-prior boost adapter for cascade (NEW 2026-04-29) |
| `decision_probability.py` | 602 | Decision Probability Engine — Core Equation |

### Causal inference (Seven-Component §2)
| Module | LOC | Purpose |
|---|---:|---|
| `causal_forest.py` | 483 | EconML CausalForestDML; `run_weekly_causal_forest_fit()` (Task 35 wraps) |
| `causal_conformal.py` | 243 | Distribution-free conformal lift wrap (lib-gated) |
| `causal_discovery.py` | 762 | PC/FCI algorithms + ATE |
| `causal_decomposition.py` | 492 | Decomposes a conversion into causal ingredients |
| `causal_dag_ensemble.py` | 347 | M7 ensemble: PC + FCI + GES + DAGMA + DoWhy refutation |
| `causal_adjudicator.py` | 919 | Loop A→B; reads horizon-closed Deviations; writes WhyLibraryEntry |
| `causal_learning.py` | 550 | Every Impression Is A Micro-Experiment |
| `causal_structure_learner.py` | 234 | Learns causal structure between alignment dimensions |
| `m2_pipeline.py` | 392 | M2 causal pipeline orchestrator |
| `ope.py` | 663 | IPS, SNIPS, DR, SwitchDR, DRos, MIPS + `policy_gate()` (handoff §4.4) |

### Page intelligence + processing depth + posture
| Module | LOC | Purpose |
|---|---:|---|
| `page_intelligence.py` | 2161 | Page-Level Psychological Intelligence (largest non-cascade module) |
| `page_attentional_posture_substrate.py` | 398 | Categorical posture (blend/vigilance/neutral) + Bayesian shrinkage |
| `page_conditioned_query.py` | 764 | Trilateral evidence engine — filter 6.7M edges by page-state |
| `page_crawl_scheduler.py` | 944 | Async page crawl (started in main.py at startup) |
| `page_edge_bridge.py` | 724 | Page → Edge bridge (A14 ADDITIVE_PAGE_SHIFT_FALLBACK fallback path) |
| `page_edge_scoring.py` | 679 | Full-Width Page Edge Scoring (20-dim) |
| `page_gradient_fields.py` | 217 | Per-page-dim conversion impact accumulator |
| `page_similarity_index.py` | 223 | Find pages with similar psychological fields |
| `processing_depth_router.py` | 314 | C2 depth predictor + route gate (FLUENCY FLOOR added 2026-04-29) |
| `impression_state_resolver.py` | 566 | Composes bid-request signals into reader position |
| `landing_page_barrier_detector.py` | 230 | Landing page barrier detection |
| `luxy_page_populator.py` | 241 | Hand-curated 73-URL × 6-pattern LUXY page population |
| `url_intelligence.py` | 545 | Maximum signal from every URL |

### Cohort + non-stationarity + mechanism taxonomy
| Module | LOC | Purpose |
|---|---:|---|
| `cohort_discovery.py` | 587 | Louvain community detection + cohort metadata (extended 2026-04-29) |
| `mechanism_rotation.py` | 551 | Pre-registered mechanism rotation |
| `online_learning_substrate.py` | 177 | Per-decision online learning (LinkPosterior) |
| `mechanism_taxonomy.py` | 375 | BLEND_COMPATIBLE / VIGILANCE_ACTIVATING canonical taxonomy |
| `mechanism_taxonomy_runtime.py` | 315 | Per-(mechanism × posture) outcome counts |

### Trilateral / metaphor / argument constitution
| Module | LOC | Purpose |
|---|---:|---|
| `trilateral_epistemic.py` | 256 | Buyer × page × mechanism epistemic value + cascade adapter |
| `metaphor_alignment.py` | 184 | Buyer-natural metaphor frame alignment |
| `metaphor_storage.py` | 204 | Cascade hot path metaphor bundle storage |
| `creative_metaphor_scoring.py` | 463 | Sprint F primary-metaphor track |
| `brand_copy_metaphor_scoring.py` | 277 | Brand copy metaphor scoring (F2 — Task 29.8) |
| `buyer_metaphor_scoring.py` | 310 | Buyer review metaphor scoring (F1 — Task 29.7) |
| `argument_constitution.py` | 485 | Source-of-truth text driving CAI critique-revise |
| `argument_cache.py` | 294 | Cascade hot-path argument cache |
| `argument_ranking.py` | 165 | B4 production gate — RANKING operating mode |
| `constitutional_loop.py` | 523 | Generate→critique→revise CAI loop offline |
| `cai_cross_family_critic.py` | 616 | CAI cross-family critique |

### Defensive reasoning / WhyLibrary / chain rendering / counterfactual
| Module | LOC | Purpose |
|---|---:|---|
| `why_library.py` | 430 | WhyEntry + record_why + query_why_for_recommendation (in-process) |
| `defensive_reasoning.py` | 359 | Partner-facing defensive reasoning view |
| `chain_rendering.py` | 495 | Construct-chain narrative renderer (Spine #6) |
| `counterfactual_tracker.py` | 206 | Per-impression counterfactual tracking ("if we hadn't shown X…") |
| `counterfactual_learner.py` | 193 | Counterfactual learning — estimate effect for non-deployed mechanisms |
| `counterfactual_mechanisms.py` | 172 | Counterfactual mechanism analysis |

### Decision-time + propensity logging + MRT
| Module | LOC | Purpose |
|---|---:|---|
| `realtime_decision_engine.py` | 580 | `compute_persuasion_decision()` parallel path (output → response metadata) |
| `mrt_logging.py` | 532 | Seven-Component §1.2 MRT propensity logging |
| `mrt_producer.py` | 132 | MRT singleton producer (cascade calls into this) |
| `evidence_grading.py` | 503 | OPE/WCLS/CF effect-size grading |
| `synthetic_ab_simulation.py` | 664 | Synthetic A/B with planted treatment effect |
| `dimension_compressor.py` | 173 | Reduce 25 alignment dims → 7 PCs |

### Per-atom contribution + plant-model
| Module | LOC | Purpose |
|---|---:|---|
| `per_atom_contribution.py` | 561 | Per-atom contribution measurement (B3-LUXY Phase 3 deliverable 3) |
| `per_atom_contribution_ingestion.py` | 196 | Per-atom contribution ingestion (consumed by main.py) |

### Outcomes + recommendations
| Module | LOC | Purpose |
|---|---:|---|
| `negative_outcome_adapters.py` | 533 | Stripe/Shopify/Generic negative outcome adapters (sapid wire NEW 2026-04-29) |
| `multi_horizon_adjudication.py` | 426 | Short- vs long-horizon outcome adjudication |
| `deviation_lifecycle.py` | 80 | Deviation lifecycle states (per directive Section 8.1) |

### Inferential learning + knowledge propagation
| Module | LOC | Purpose |
|---|---:|---|
| `inferential_learning_agent.py` | 943 | 6-level theory builder (OBSERVE → VALIDATE → HYPOTHESIZE → DESIGN → APPLY) |
| `inferential_hypothesis_engine.py` | 559 | Generate, test, validate, transfer inferential hypotheses |
| `knowledge_propagation.py` | 979 | Hebbian-style cross-system propagation network |
| `cognitive_learning_system.py` | 993 | ADAM cognitive learning system |
| `prediction_engine.py` | 443 | Validated causal hypotheses → predict where conversion will occur |
| `goal_activation.py` | 1211 | Nonconscious Goal Activation Model — Active Learning System |

### Brand / customer / review intelligence (large set — many shared with corpus side)
| Module | LOC | Purpose |
|---|---:|---|
| `brand_copy_extractor.py` | 562 | Brand copy intelligence extractor |
| `brand_copy_intelligence.py` | 621 | Brand copy intelligence aggregator |
| `brand_persuasion_analyzer.py` | 685 | Brand persuasion analyzer |
| `brand_trait_extraction.py` | 1051 | ADAM brand trait extraction framework |
| `customer_ad_alignment.py` | 879 | Customer-Advertisement Alignment Service |
| `customer_influence_graph.py` | 527 | Customer Influence Graph |
| `customer_types.py` | 844 | Purchase-Predictive Customer Type System |
| `granular_type_detector.py` | 627 | Granular customer type detector |
| `granular_type_enrichment.py` | 653 | Granular type enrichment service |
| `helpful_vote_intelligence.py` | 569 | Helpful vote intelligence |
| `helpful_vote_weighting.py` | 555 | Helpful vote weighted learning |
| `review_analyzer.py` | 677 | Psychological analyzer for customer reviews |
| `review_orchestrator.py` | 536 | Review intelligence orchestrator |
| `review_learnings_service.py` | 1093 | Review learnings service |
| `unified_review_aggregator.py` | 689 | Unified review aggregator |
| `enhanced_review_analyzer.py` | 1184 | Enhanced psychological analyzer (35 constructs from #27) |
| `deep_review_analyzer.py` | 665 | Deep review psychological analysis |
| `claude_summarizer.py` | 399 | Claude-powered review intelligence summarization |
| `database_review_matcher.py` | 403 | Database-backed review matcher |
| `smart_review_matcher.py` | 727 | Smart review matcher |
| `asin_review_matcher.py` | 506 | ASIN-based review matcher |
| `hierarchical_product_matcher.py` | 650 | Hierarchical product matcher |
| `product_analyzer.py` | 723 | Claude-powered product understanding |
| `deep_product_analyzer.py` | 1054 | Deep product page psychological analysis |
| `deep_page_scoring.py` | 968 | Deep page psychology scoring |
| `unified_product_intelligence.py` | 1010 | Unified product intelligence |
| `purchase_journey_analyzer.py` | 656 | Purchase journey analyzer |
| `journey_intelligence.py` | 686 | Journey intelligence |
| `unified_review_aggregator.py` | 689 | Unified review aggregator |
| `corpus_builder.py` | 531 | Deep review corpus builder |
| `annotation_engine.py` | 328 | Deep bilateral annotation engine |
| `complete_psychological_analyzer.py` | 424 | ADAM complete psychological analyzer |
| `unified_psychological_intelligence.py` | 1927 | Unified psychological intelligence — Central Integration Hub |
| `unified_construct_integration.py` | 543 | Unified construct integration |
| `unified_intelligence_service.py` | 876 | Unified Intelligence Service — three-layer Bayesian fusion (orchestrator imports this) |

### Frameworks (large reference modules)
| Module | LOC | Purpose |
|---|---:|---|
| `psychological_frameworks.py` | 2378 | ADAM psychological frameworks |
| `psychological_frameworks_extended.py` | 1894 | ADAM psychological frameworks extended |
| `empirical_psychology_framework.py` | 1891 | Empirical psychology framework |
| `advertisement_psychology_framework.py` | 1601 | Advertisement & brand psychology framework |
| `deep_psycholinguistic_framework.py` | 1672 | Deep psycholinguistic analysis framework |
| `construct_taxonomy.py` | 1587 | ADAM Psychological Construct Taxonomy v2.0 |
| `persuasion_susceptibility.py` | 1328 | ADAM persuasion susceptibility framework |
| `temporal_psychology.py` | 768 | Temporal psychology module |
| `financial_psychology.py` | 727 | ADAM financial psychology intelligence |
| `domain_taxonomy.py` | 950 | Domain taxonomy & hierarchical psychological intelligence |

### Other intelligence modules
| Module | LOC | Purpose |
|---|---:|---|
| `agency_dashboard.py` | 388 | Agency-facing dashboard JSON payload aggregator |
| `amazon_data_registry.py` | 484 | Amazon data registry |
| `atom_intelligence_injector.py` | 875 | Atom intelligence injector |
| `attribution_intelligence.py` | 811 | Attribution intelligence module |
| `bidirectional_bridge.py` | 505 | Bidirectional bridge |
| `blend_fit.py` | 413 | Blend fit primitive (attention-inversion implication #1) |
| `blend_vigilance_weighting.py` | 139 | F5 cascade weighting (attention-inversion implication #2) |
| `campaign_ingestion.py` | 1276 | External Campaign Analytics Ingestion Process (ECAIP) |
| `campaign_report.py` | 281 | Campaign performance report generator |
| `campaign_simulator.py` | 426 | Pre-campaign performance simulation |
| `channel_capacity.py` | 311 | Channel capacity × message complexity matching |
| `clv_model.py` | 419 | Long-horizon CLV piece of E3 |
| `complete_psychological_analyzer.py` | 424 | Complete psychological analyzer |
| `construct_matching.py` | 843 | ADAM construct matching engine |
| `context_intelligence.py` | 741 | Context intelligence module |
| `cross_platform_validation.py` | 746 | Cross-platform validation module |
| `ctv_intelligence.py` | 775 | CTV (connected TV) content intelligence |
| `daily_intelligence_brief.py` | 241 | Daily intelligence brief generator |
| `deep_archetype_detection.py` | 1925 | Deep archetype detection system |
| `emergence_engine.py` | 1209 | Emergence engine |
| `exposure_response.py` | 400 | Exposure-response model — therapeutic window |
| `expanded_type_integration.py` | 519 | Expanded type integration service |
| `full_intelligence_integration.py` | 846 | Full intelligence integration |
| `graph_construct_service.py` | 625 | Graph construct service — runtime construct graph interface |
| `graph_edge_service.py` | 911 | Graph edge intelligence service |
| `graph_maintenance.py` | 540 | Graph maintenance & intelligence activation |
| `heterogeneous_gnn.py` | 278 | M5 GNN — replace 27 hand-engineered dims with learned (handoff §5) |
| `historical_data_reprocessor.py` | 1010 | Historical data reprocessor |
| `integration_service.py` | 474 | Maximum impact intelligence integration service |
| `langgraph_alignment_integration.py` | 863 | LangGraph alignment integration |
| `mechanism_adme.py` | 359 | Pharmacokinetic mechanism profiles |
| `mmm_model.py` | 293 | Channel-ROI piece of E3 (MMM) |
| `ndf_extractor.py` | 503 | Nonconscious Decision Fingerprint (NDF) extractor |
| `persuadability_intelligence.py` | 708 | Persuadability intelligence module |
| `persuasive_patterns.py` | 661 | Persuasive pattern extractor |
| `psychological_arbitrage.py` | 234 | Psychological arbitrage scoring |
| `public_labels.py` | 371 | Translates internal taxonomy to public-facing labels |
| `reaction_intelligence.py` | 610 | Audience reaction intelligence |
| `segment_depletion.py` | 241 | Segment depletion detector |
| `session_state.py` | 313 | Session psychological state estimation |

## A.2 — `adam/intelligence/` subdirectories

### `intelligence/daily/` — 39 scheduled tasks (above; full list in main inventory)

### `intelligence/spine/` — 4 modules (above)

### `intelligence/recommendation_class/` — Weakness #4 RecommendationClass primitive (12 files)
- `a14_compromises.py` — A14 calibration-pending compromises
- `adjudicator.py` — RecommendationClass adjudicator
- `archetype_compression.py` — archetype compression
- `chain_attribution.py` — chain attribution
- `conformal.py` — conformal prediction
- `graph.py` — RecommendationClass graph
- `inferential_chain.py` — inferential chain
- `plant_model.py` — plant model (long-pole pilot dependency per memory)
- `pre_registration.py` — pre-registration
- `processing_depth_priors.py` — processing depth priors
- `projected_impact.py` — projected impact
- `sequential_schedule.py` — sequential schedule

### `intelligence/campaign_intelligence/` — DCIL pipeline (8 files)
- `audit_log.py` — DCIL audit log
- `coherence_validator.py` — coherence validation (Task 29)
- `config.py` — DCIL config
- `directive_generator.py` — directive generation (Task 28)
- `execution_engine.py` — campaign execution (Task 30)
- `generalizability.py` — generalizability scoring
- `hypothesis_battery.py` — hypothesis battery (Task 25)
- `models.py` — DCIL pydantic models

### `intelligence/dialogue_ledger/` — HMT v0.1 (5 files)
- `elicitation.py` — 4 elicitation format generators
- `mood_probe.py` — mood probe
- `service.py` — dialogue ledger service
- `uncertainty_panel.py` — uncertainty panel rendering
- `models.py` — HMT pydantic models

### `intelligence/graph/` — 5 files
- `gds_runtime.py` — Neo4j GDS runtime service
- `reasoning_chain_generator.py` — reasoning chain generator
- `theory_schema.py` — theory schema
- `unified_psychological_schema.py` — unified psychological schema
- `zero_shot_transfer.py` — zero-shot transfer

### `intelligence/knowledge_graph/` — 5 files
- `brand_graph_builder.py`
- `persuasion_susceptibility_graph.py`
- `populate_psychological_graph.py`
- `review_graph_builder.py`
- `review_learnings_embedder.py`

### `intelligence/relationship/` — 5 files (detector, graph_builder, models, patterns, schema)

### `intelligence/scrapers/` — 12 files (amazon_playwright, amazon_reviews, base, brand_positioning_analyzer, enterprise_scraper, google_reviews, oxylabs_ai_client, oxylabs_client, product_page, social_scraper, unified_scraper, aggregator)

### `intelligence/pages/` — 2 files (claude_feature_scoring, entity_graph)

### `intelligence/learning/` — 1 file (psychological_learning_integration)

### `intelligence/models/` — 2 files (brand_personality, customer_intelligence)

### `intelligence/outcome_simulation/` — 1 file (theory_based_simulator)

### `intelligence/pattern_discovery/` — 1 file (brand_pattern_learner)

### `intelligence/review_intelligence/` — orchestrator + base_extractor + extractors/ subdir

### `intelligence/sources/` + `intelligence/storage/` — empty placeholders

---

## A.3 — `adam/atoms/` (33 atoms + DAG infra)

### B3-LUXY canonical atoms (9, verified by `canonical, B3-LUXY` docstring tag)
1. `ambiguity_attitude.py` (632 LOC) — Phase 2 atom 8 (Ellsberg)
2. `autonomy_reactance.py` (741 LOC) — Phase 0
3. `mimetic_desire_atom.py` (711 LOC) — Phase 1 atom 3
4. `persuasion_pharmacology.py` (861 LOC) — Phase 1 atom 2 (ADME-style)
5. `regret_anticipation.py` (735 LOC) — Phase 2 atom 7 (Loomes & Sugden)
6. `regulatory_focus.py` (812 LOC) — Phase 2 atom 9 (Higgins)
7. `signal_credibility.py` (762 LOC) — Phase 2 atom 6 (Spence signaling)
8. `strategic_awareness.py` (681 LOC) — Phase 1 atom 4
9. `temporal_self.py` (687 LOC) — Phase 1 atom 5

### Other atoms (24, wrapper-status pending B3-LUXY-style canonical refits)
- `ad_selection.py` (777) — AD SELECTION ATOM (terminal-adjacent; integrates with mechanism_activation)
- `brand_personality.py` (557)
- `channel_selection.py` (301)
- `cognitive_load.py` (299)
- `coherence_optimization.py` (361)
- `construal_level.py` (302)
- `construct_resolver.py` (726) — psychological construct resolver
- `cooperative_framing.py` (270)
- `decision_entropy.py` (268)
- `dsp_integration.py` (348) — DSP graph intelligence integration layer
- `information_asymmetry.py` (323)
- `interoceptive_style.py` (236)
- `mechanism_activation.py` (2627) — TERMINAL ATOM, emits final mechanism_scores (largest atom by far)
- `mechanism_registry.py` (338) — mechanism effectiveness registry
- `message_framing.py` (684)
- `motivational_conflict.py` (290)
- `narrative_identity.py` (347)
- `personality_expression.py` (538)
- `predictive_error.py` (262)
- `query_order.py` (339)
- `relationship_intelligence.py` (1132)
- `review_intelligence.py` (363) — atom-side review intelligence
- `strategic_timing.py` (301)
- `user_state.py` (598)

### Atom DAG infrastructure
- `dag.py` (808 LOC) — `AtomDAG` execution engine
- `emergence_detector.py` (778 LOC) — emergence detection engine
- `intelligence_sources.py` (425 LOC) — 10 intelligence sources used by AtomDAG atoms
- `models/atom_io.py` (249) — atom input/output models
- `models/chain_attestation.py` (438) — `ChainAttestation` typed evidence
- `models/evidence.py` (301) — intelligence evidence models
- `orchestration/construct_dag.py` (489) — taxonomy-domain → atom mapping
- `orchestration/dag_executor.py` (1082) — enhanced DAG executor with LangGraph
- `orchestration/langgraph_feedback.py` (545) — LangGraph ↔ AoT bidirectional feedback
- `review_intelligence_source.py` (819) — review intelligence source

---

## A.4 — `adam/api/` (9 routers + admin + admin services)

### `api/stackadapt/` (8 modules — production bid path)
- `attribution_bridge.py` (161) — webhook → outcome handler attribution
- `bilateral_cascade.py` (3110) — main cascade (modulation chain)
- `decision_cache.py` (367) — links decisions to outcomes
- `graph_cache.py` (1101) — `GraphIntelligenceCache` sync read backbone
- `models.py` (556) — request/response pydantic models
- `router.py` (203) — FastAPI router
- `service.py` (1317) — `CreativeIntelligenceService`
- `webhook.py` (609) — outcome webhook (HMAC + dedup + dispatch)

### `api/dashboard/` (7 modules)
- `auth.py` (65) — pilot hard-coded user
- `client_decisions_service.py` (527) — client acknowledge/decline persistence
- `client_report_service.py` (549) — client report assembly
- `models.py` (891) — HMT dashboard pydantic models
- `router.py` (1792) — endpoints (very large)
- `service.py` (1783) — fetches live StackAdapt data
- `system_insights_service.py` (289) — Enhancement #33 retargeting learning aggregation

### `api/decision/router.py` (1615) — DECISION API
### `api/intelligence/router.py` (794) — INTELLIGENCE API
### `api/universal/router.py` (3290) — UNIVERSAL INTELLIGENCE API ⚠ **largest router in repo**
### `api/fusion/router.py` (418), `api/health/router.py` (526), `api/monitoring/router.py` (321)
### `api/signals/router.py` (374) — site telemetry ingestion
### `api/behavioral/desktop_router.py` (453) + `media_router.py` (485)
### `api/auth/middleware.py` (79) — API key auth

### `api/admin/` (24 files, 3044 LOC) — full RBAC admin surface
- `auth.py` (127), `db.py` (405) PostgreSQL, `dependencies.py` (93)
- `routers/auth_router.py`, `org_router.py`, `campaign_router.py`, `client_router.py`
- `services/pilot_bootstrap.py` (called at startup)
- `models/{user, organization, domain, campaign, creative, archetype, directive, tracker, report}.py`
- `migrations/002_seed_super_admin.py`

---

## A.5 — `adam/orchestrator/` (12 modules, 8752 LOC)

- `campaign_orchestrator.py` (2570) — master orchestrator
- `graph_intelligence.py` (1044) — graph intelligence layer
- `intelligence_prefetch.py` (1213) — intelligence prefetch service
- `models.py` (518) — orchestrator pydantic models

### `orchestrator/adaptive/` — **self-evolving brain (6 modules, ~3300 LOC) — substantial subsystem**
- `episodic_memory.py` (716) — Cross-Session Retrieval-Augmented Reasoning
- `graph_rewriter.py` (409) — Adaptive Graph Rewriter
- `meta_orchestrator.py` (445) — Meta-Orchestrator (orchestrator of orchestrators)
- `neural_routing.py` (696) — Neural Attention Routing (LangGraph extension)
- `runtime_edges.py` (376) — Runtime edge factory
- `self_improvement.py` (691) — Recursive Self-Improvement Engine

---

## A.6 — `adam/core/` (22 files, 19441 LOC)

### `core/learning/` (15 modules)
- `outcome_handler.py` (2818) — production outcome write path (largest core module)
- `learned_priors_integration.py` (3886) — ⚠ **largest core file by far**
- `unified_learning_hub.py` (799)
- `theory_learner.py` (837) — construct-level learning from outcomes
- `universal_learning_interface.py` (717)
- `quality_audit.py` (992)
- `thompson_warmstart.py` (486) — called at startup
- `effect_size_correction.py` (502) — consumed by stackadapt service
- `event_bus.py` (365)
- `signal_router.py` (281)
- `construct_learning_loop.py` (253)
- `atom_learning_integrations.py` (879)
- `component_integrations.py` (1433)
- `orchestrator_learning_integration.py` (470)
- `learning/__init__.py` (52) — note: explains "FOUR learning-named packages" hierarchy

### `core/` top-level
- `container.py` (937) — DI container
- `decision_mode.py` (410) — Epistemic Status of Intelligence Produced by ADAM
- `dependencies.py` (1246) — DI registry (large)
- `outcome_types.py` (322) — `OutcomeType` enum + reward semantics

### `core/synthesis/` (referenced but not detailed here)

---

## A.7 — `adam/platform/` (delivery + blueprints)

### `platform/delivery/` (5 modules)
- `base.py` (139) — `BaseDeliveryAdapter` ABC
- `factory.py` (97) — `ADAPTER_REGISTRY` + `create_adapter()`
- `dsp_adapter.py` (468) — DV360, TradeDesk, two StackAdapt classes (deprecated REST + new GraphQL bridge)
- `audio_adapter.py` (178) — Megaphone, Triton, SpotifyAdStudio
- `ssp_adapter.py` (177) — Magnite, Prebid

### `platform/blueprints/` (3 modules)
- `engine.py` (363) — blueprint engine (calls `create_adapter` at line 247)
- `registry.py` (341) — blueprint registry
- `router.py` (140) — blueprint API router

---

## A.8 — `adam/integrations/` (13 files — ⚠ THREE StackAdapt files at this level)

### `integrations/base/`
- `base/adapter.py` (359) — `BasePlatformAdapter` ABC + `PlatformCredentials`, `AdapterMode`, `SyncedSegment`, `SyncedCreative`

### `integrations/stackadapt/` (canonical GraphQL surface)
- `adapter.py` (359) — `StackAdaptAdapter(BasePlatformAdapter)` — GraphQL mutations
- `graphql_client.py` (326) — `StackAdaptGraphQLClient` (schema-corrected 2026-04-29)
- `data_taxonomy_client.py` (309)
- `outcome_mapper.py` (153) — webhook event → outcome mapping (consumed by webhook.py)
- `taxonomy_generator.py` (661) — INFORMATIV audience taxonomy generator

### `integrations/` top-level (multiple StackAdapt files at this level — review for dedup)
- `stackadapt_graphql.py` (588) — older GraphQL integration layer (uses `X-AUTHORIZATION` header — legacy, ZERO callers)
- `stackadapt_monitor.py` (341) — StackAdapt campaign monitor

### `integrations/audioboom/` 
- `adapter.py` (225) — Audioboom platform adapter

---

## A.9 — `adam/retargeting/` (77 files, 24824 LOC) — ⚠ Large, sophisticated retargeting subsystem

### `retargeting/engines/` (30+ engines)
- `barrier_diagnostic.py` (895) — conversion barrier diagnostic engine
- `barrier_self_report.py` (336) — extracts barrier from post-click behavior
- `causal_mediation.py` (330) — causal mediation analysis (Task 22 consumer)
- `claude_argument_engine.py` (479) — Claude argument generation
- `click_latency.py` (210) — approach-avoidance conflict from click latency
- `device_compat.py` (154) — processing-mode → mechanism effectiveness
- `diagnostic_reasoner.py` (1358) — diagnostic deduction engine
- `dimensionality_compressor.py` (253) — Information Bottleneck / PCA profile compression
- `frequency_decay.py` (146) — reactance onset via Bayesian changepoint
- `frustration.py` (215) — frustration score from bilateral alignment
- `graph_embeddings.py` (234) — Neo4j GDS embeddings
- `impression_classifier.py` (257) — non-click outcome classifier
- `intervention_emitter.py` (119) — emits enriched intervention records
- `learning_dimensions.py` (483) — 8 dimensions of learning
- `learning_loop.py` (431) — retargeting learning loop
- `mechanism_observation_models.py` (200) — 16 therapeutic mechanisms × 20-dim observation vectors
- `mechanism_selector.py` (529) — Bayesian mechanism selection
- `narrative_arc.py` (268) — episodic story structure for sequences
- `neural_linucb.py` (474) — Neural LinUCB bandit
- `nonconscious_profile.py` (317) — 6 nonconscious behavioral signals composite
- `options_framework.py` (320) — TTM-based options
- `organic_return.py` (136) — internal motivation detection
- `prior_manager.py` (663) — 5-Level Hierarchical Bayesian Prior Manager (orchestrator imports)
- `processing_depth.py` (179) — POST-impression depth (extends C2 with viewability)
- `prospect_theory.py` (222) — prospect theory value function
- `puzzle_solver.py` (699) — per-person experiment solver (treats each user as unique experiment)
- `recalibration.py` (472) — periodic recalibration of composite alignment weights
- `repeated_measures.py` (1177) — ⚠ **WITHIN-SUBJECT REPEATED MEASURES — this is Spine #2**
- `rupture_detector.py` (353) — confrontation/withdrawal/decay detection
- `sequence_orchestrator.py` (785) — therapeutic sequence orchestrator (brain of retargeting)
- `signal_collector.py` (640) — site telemetry → nonconscious signal accumulator
- `signal_processors.py` (311) — preprocessing for stage classification + barrier diagnosis
- `stage_classifier.py` (238) — TTM-derived conversion stage classifier
- `suppression_controller.py` (206) — when to STOP retargeting
- `temporal_dynamics.py` (301) — retargeting timing optimization
- `tensor_decomposition.py` (358) — CP decomposition for archetype discovery
- `touch_builder.py` (294) — TherapeuticTouch from diagnosis + narrative position
- `unified_puzzle.py` (786) — ONE model, ALL signals simultaneously
- `annotation_quality.py` (339) — annotation quality via self-consistency + conformal

### `retargeting/resonance/` — RESONANCE ENGINEERING SUBSYSTEM (12 files) — ⚠ Parallel architecture
- `browsing_momentum.py` (247) — compound priming from multiple page visits
- `cold_start.py` (284) — theory-driven mechanism ideal vectors
- `competitive_displacement.py` (259) — detects competitive ad environments
- `creative_adaptation.py` (178) — lightweight creative adaptation at impression-time (<5ms)
- `creative_adapter.py` (248) — real-time creative adaptation to page context
- `evolutionary_engine.py` (668) — active self-improvement
- `mindstate_vector.py` (190) — `PageMindstateVector` from `PagePsychologicalProfile`
- `models.py` (246) — resonance data models
- `placement_optimizer.py` (364) — dynamic placement optimization
- `resonance_cache.py` (142) — Redis-backed resonance cache
- `resonance_gradient.py` (125) — ∂P(conv)/∂page_mindstate per mechanism
- `resonance_learner.py` (307) — closed-loop resonance learning
- `resonance_model.py` (369) — `R(buyer, seller, page) = base × resonance_multiplier`

### `retargeting/integrations/` — StackAdapt translator + exporter
- `stackadapt_api_exporter.py` (653) — produces StackAdapt-executable campaign configs
- `stackadapt_translator.py` (297) — therapeutic sequences → StackAdapt configs

### `retargeting/models/` — diagnostic_assessment, diagnostics, enums, intervention_record, learning, sequences, site_profiles, telemetry, within_subject

### `retargeting/prompts/` — argument_generation
### `retargeting/schema/` — queries (Cypher templates)
### `retargeting/workflows/therapeutic_workflow.py` (257) — LangGraph therapeutic loop
### `retargeting/personality_mechanism_matrix.py` (70), `research_priors.py` (339), `api.py` (439), `events.py` (51)

---

## A.10 — `adam/cold_start/` (23 files, 6207 LOC)

- `service.py` (1398) — main cold start service
- `unified_learning.py` (787) — unified cold start learning
- `__init__.py` (213) — cold start strategy
- `archetypes/definitions.py` (384) — 8 research-grounded archetype definitions
- `archetypes/detector.py` (292) — archetype detection
- `cache/prior_cache.py` (234) — Redis prior cache
- `events/contracts.py` (188) — event contracts
- `learning/gradient_bridge.py` (252) — integration with Gradient Bridge
- `models/archetypes.py` (251), `decisions.py` (217), `enums.py` (162), `priors.py` (426), `user.py` (262)
- `priors/demographic.py` (254) — demographic priors
- `priors/population.py` (220) — population-level priors
- `thompson/sampler.py` (310) — Thompson sampling

### NOTE: `adam/coldstart/` (no underscore, 31 LOC) — separate empty/abandoned directory. Investigate for deletion.

---

## A.11 — `adam/blackboard/` (10 files, 2882 LOC) — 5-zone shared-state architecture

- `service.py` (612) — blackboard service
- `memory_blackboard.py` (371) — in-memory blackboard
- `models/core.py` (307) — core blackboard models
- `models/zone1_context.py` (242) — request context
- `models/zone2_reasoning.py` (446) — atom reasoning spaces
- `models/zone3_synthesis.py` (327) — synthesis workspace
- `models/zone4_decision.py` (207) — decision state
- `models/zone5_learning.py` (281) — learning signals

---

## A.12 — `adam/embeddings/` (13 files, 8178 LOC)

- `service.py` (790) — embedding service
- `pipeline.py` (885) — embedding pipelines
- `generator.py` (832) — embedding generator
- `models.py` (636) — embedding models
- `pgvector.py` (738) — pgvector backend
- `store.py` (784) — vector store
- `monitoring.py` (554) — embedding monitoring dashboard
- `maintenance.py` (685) — embedding maintenance
- `finetuning/dataset.py` (687), `pipeline.py` (700), `trainer.py` (636) — fine-tuning subsystem

---

## A.13 — `adam/graph_reasoning/` (11 files, 4862 LOC)

- `bridge/interaction_bridge.py` (794) — `InteractionBridge` (orchestrator imports)
- `bridge/context_queries.py` (1240) — context query executor
- `bridge/bidirectional_integration.py` (498)
- `conflict_resolution.py` (492)
- `models/intelligence_sources.py` (573) — the 10 intelligence sources
- `models/graph_context.py` (402)
- `models/reasoning_output.py` (364)
- `update_tiers.py` (350)

---

## A.14 — `adam/workflows/` (8 files, 6809 LOC) — LangGraph workflows

- `synergy_orchestrator.py` (2690) — ⚠ **largest workflow file**
- `holistic_decision_workflow.py` (1636)
- `dsp_impression_workflow.py` (692)
- `intelligence_prefetch_nodes.py` (662)
- `susceptibility_intelligence_node.py` (540)
- `unified_intelligence_node.py` (379)
- `config.py` (209)

---

## A.15 — `adam/services/` (7 files, 2587 LOC)

- `archetype_service.py` (492)
- `bandit_service.py` (418)
- `brand_library.py` (256)
- `competitive_intel.py` (300)
- `graph_intelligence.py` (681)
- `temporal_patterns.py` (362)

---

## A.16 — `adam/dsp/` (15 files, 7660 LOC) — DSP enrichment engine

- `construct_registry.py` (919) — psychological construct registry
- `dimension_inference.py` (607)
- `edge_registry.py` (1153) — causal/inferential edge registry
- `ethical_boundary.py` (170)
- `graph_population.py` (522) — Neo4j graph population
- `graph_state_inference.py` (609) — graph-based state inference
- `graph_type_inference.py` (424)
- `inventory_scoring.py` (219)

---

## A.17 — `adam/output/` (8 files, 3103 LOC)

- `copy_generation/service.py` (2045) — ⚠ copy generation service (large)
- `copy_generation/copy_learner.py` (347) — learns which copy params work
- `copy_generation/models.py` (171)
- `brand_intelligence/service.py` (329), `models.py` (140)

---

## A.18 — `adam/ops/` (8 files, 3373 LOC) — autonomous ops + StackAdapt executor

- `autonomous.py` (533) — makes decisions and acts without human
- `intelligence.py` (647) — `start_ops_intelligence` (called at startup, hourly)
- `intelligence_report.py` (557) — actionable StackAdapt optimization instructions every 4 hours
- `smart_optimizer.py` (621) — campaign brain
- `campaign_actions.py` (292) — translates recommendations → executable changes
- `stackadapt_executor.py` (312) — executes approved campaign changes via GraphQL
- `router.py` (411) — ops API endpoints

---

## A.19 — Other large subsystems (one-line each)

### `adam/identity/` (21 files, 3951 LOC) — Cross-platform identity resolution
- `service.py` (332) — main identity resolution
- `graph/neo4j_graph.py` (498) — Neo4j-backed identity graph
- `household/resolver.py` (340)
- `matching/deterministic.py` (170), `probabilistic.py` (273)
- `partners/iheart.py` (211), `rampid.py` (215), `uid2.py` (220)
- `privacy/bloom_filter.py` (236), `differential_privacy.py` (306)

### `adam/data/amazon/` (8+ files) — Amazon data ingestion
- `client.py` (804), `ingestion.py` (708), `enhanced_ingestion.py` (627), `loader.py` (574), `indexer.py` (645), `features.py` (448), `cross_domain_pipeline.py` (487), `media_product_graph.py` (831)

### `adam/signals/` (10 files, 4433 LOC)
- `linguistic/service.py` (658), `nonconscious/analysis.py` (698), `capture.py` (651), `service.py` (619), `models.py` (585)
- `learning_integration.py` (752)

### `adam/temporal/` (3 files) — `state_trajectory.py` (580), `learning_integration.py` (662)

### `adam/fusion/` (8 files, 4485 LOC) — Corpus intelligence fusion (4 layers)
- `prior_extraction.py` (987) — Layer 1
- `creative_patterns.py` (673) — Layer 2
- `platform_calibration.py` (489) — Layer 3
- `bidirectional_learning.py` (565) — Layer 4
- `resonance_index.py` (645) — Persuasion Resonance Index (Layer 5)
- `product_intelligence.py` (512), `models.py` (574)

### `adam/gradient_bridge/` (8 files, 3373 LOC) — Cross-component learning signals
- `service.py` (1267), `attribution.py` (897) — credit attribution
- `models/credit.py` (229), `features.py` (281), `signals.py` (426)

### `adam/meta_learner/` (6 files, 2576 LOC)
- `service.py` (733) — meta-learner service
- `neural_thompson.py` (555), `thompson.py` (365)
- `models.py` (510)

### `adam/ml/` (7 files, 3752 LOC) — Custom AI models
- `foundation_model.py` (853) — ADAM foundation model
- `training_pipeline.py` (868)
- `online_learner.py` (751) — online RL from ad outcomes
- `ndf_predictor.py` (439), `hybrid_extractor.py` (425), `weak_supervisor.py` (381)

### `adam/monitoring/` (8 files, 3193 LOC)
- `learning_metrics.py` (551), `synthetic_tester.py` (461), `alerting.py` (464), `health_service.py` (451), `drift_detection.py` (416), `learning_loop_monitor.py` (410), `system_health.py` (388)

### `adam/infrastructure/` (26 files, 7952 LOC) — Kafka, Redis, Neo4j client, Prometheus, alerting, resilience, health

### `adam/behavioral_analytics/` (43 files, 26545 LOC) — large reference subsystem; classifiers + knowledge + extensions
- `atom_interface.py` (1317) — Atom of Thought interface for behavioral analytics

### `adam/corpus/` (34 files, 9035 LOC) — annotation corpus + Neo4j ingestion
- `edge_builders/match_calculators.py` (1221) — match score calculators (Phases 5-7)
- `annotators/{ad_side, base, dual, prompt_templates}.py`

### `adam/segments/engine.py` (836) — psychological segment engine

### `adam/experimentation/` (5 files, 1183 LOC) — A/B testing
- `service.py` (398), `analysis.py` (339), `assignment.py` (235), `models.py` (174)

### `adam/verification/` (11 files, 2405 LOC) — 4-layer verification
- `service.py` (493), `learning_integration.py` (639)
- `layers/calibration.py`, `consistency.py`, `grounding.py`, `safety.py`

### `adam/validity/` (4 files) — psychological validity checks
- `checks.py` (511), `service.py` (300), `models.py` (214)

### `adam/testing/` — e2e_tests, integration_test_runner (1159), simulation, synthetic_data_framework (827)

### Smaller subsystems
- `adam/audio/` (5 files) — audio service + SSML
- `adam/podcast/` (4 files) — host briefings + intelligence + matching
- `adam/multimodal/` (4 files)
- `adam/synthesis/streaming_synthesis.py` (513)
- `adam/simulation/engine.py` (522)
- `adam/competitive/intelligence.py` (752)
- `adam/performance/` — cache_manager, circuit_breaker, fast_path, latency
- `adam/privacy/` — privacy service
- `adam/creative/` — construct_creative_engine (645), personality_creative (504)
- `adam/explanation/` — explanation generation
- `adam/inference/engine.py` (503) — latency-optimized inference engine
- `adam/llm/` — Claude client + fusion + prompts + service
- `adam/observability/` — correlation, debug, tracing
- `adam/features/` — feature store
- `adam/integration/decision_enrichment.py` (426)

---

# APPENDIX B — STACKADAPT INTEGRATION FULL MAP

There are FOUR places "StackAdapt" appears in the codebase. Map of all of them:

1. **`adam/api/stackadapt/`** — 8 modules. Production HTTP surface (router, webhook, service, bilateral_cascade, graph_cache, decision_cache, attribution_bridge, models). This is the LIVE BID PATH.

2. **`adam/integrations/stackadapt/`** — 5 modules (CANONICAL). GraphQL adapter + GraphQL client + data taxonomy + outcome mapper + taxonomy generator. This is the canonical write surface that wraps the GraphQL API.

3. **`adam/integrations/stackadapt_graphql.py` (588 LOC) + `stackadapt_monitor.py` (341 LOC)** — top-level files at integrations/. The graphql one uses LEGACY `X-AUTHORIZATION` header pattern with ZERO callers in the codebase. **Candidate for deletion.** The monitor.py status is unverified.

4. **`adam/platform/delivery/dsp_adapter.py`** — Two StackAdapt classes:
   - `StackAdaptAdapter` — DEPRECATED REST adapter (kept reachable as `stackadapt_legacy_rest`)
   - `StackAdaptGraphQLDeliveryAdapter` — NEW 2026-04-29; thin bridge from `BaseDeliveryAdapter` to `integrations/stackadapt/adapter.py.StackAdaptAdapter`

5. **`adam/retargeting/integrations/stackadapt_api_exporter.py` + `stackadapt_translator.py`** — Therapeutic-sequence → StackAdapt-config translation (separate from #1-4 — concerned with retargeting sequence export, not bid path).

6. **`adam/ops/stackadapt_executor.py`** — Ops-layer executor that runs approved campaign changes via GraphQL. Reads `STACKADAPT_API_KEY` env.

**The GraphQL token added to `.env` 2026-04-29** is read by:
- `integrations/stackadapt/graphql_client.py` (reads `STACKADAPT_API_KEY` OR `STACKADAPT_GRAPHQL_KEY`) ✓
- `integrations/stackadapt_graphql.py` (reads `STACKADAPT_GRAPHQL_KEY` only — but ZERO callers, so irrelevant)
- `ops/stackadapt_executor.py` (reads `STACKADAPT_API_KEY` only)
- `platform/delivery/dsp_adapter.py.StackAdaptGraphQLDeliveryAdapter.configure()` (reads BOTH names)

**Discipline going forward:** all new StackAdapt write code goes through `integrations/stackadapt/adapter.py` (the canonical wrapper). The factory `'stackadapt'` entry resolves to the GraphQL bridge. The legacy paths exist for backward compat only.

---

# APPENDIX C — CRITICAL CROSS-CUTTING OBSERVATIONS

These are integration-fragility surfaces that were not visible in the first pass:

1. **TWO cold-start subsystems exist:**
   - `adam/cold_start/` (23 files, 6207 LOC) — canonical, orchestrator imports from here
   - `adam/coldstart/` (2 files, 31 LOC) — empty/abandoned, candidate for deletion
   - `adam/user/cold_start/` — yet ANOTHER cold-start surface (archetypes.py 344, service.py 386). Overlap with `adam/cold_start/`.

2. **TWO Thompson samplers:**
   - `adam/cold_start/thompson/sampler.py` (310 LOC) — production Thompson sampler (orchestrator imports)
   - `adam/meta_learner/thompson.py` (365) + `neural_thompson.py` (555) — meta-learner Thompson variants

3. **TWO outcome handlers (?):**
   - `adam/core/learning/outcome_handler.py` (2818 LOC) — production canonical
   - `adam/api/stackadapt/webhook.py` (609 LOC) calls into `core/learning/outcome_handler.handle_outcome` so they ARE wired correctly. But it's worth verifying the full event path.

4. **MULTIPLE learning packages** per `core/learning/__init__.py`: "FOUR learning-named packages serving distinct roles":
   - `adam/core/learning/` — the canonical
   - `adam/intelligence/learning/` — psychological learning integration
   - `adam/cold_start/learning/` — cold start learning
   - `adam/retargeting/engines/learning_loop.py` + `learning_dimensions.py` — retargeting learning
   - PLUS `adam/services/bandit_service.py` and `adam/meta_learner/`

5. **Resonance Engineering subsystem** (`adam/retargeting/resonance/`, 12 files) is a parallel architecture with its own resonance_model + resonance_learner + creative_adapter. This needs explicit reconciliation with the cascade modulation chain — does the cascade consume resonance signals, or is resonance a downstream layer?

6. **Self-evolving brain** (`adam/orchestrator/adaptive/`, 6 modules ~3300 LOC) — episodic memory + neural routing + self-improvement + meta-orchestrator + graph rewriter. NOT yet referenced in this session's wires. Substantial substrate; needs investigation for production wiring status.

7. **Foundation model** (`adam/ml/foundation_model.py`, 853 LOC) — "ADAM Foundation Model — Our Own AI Model." Status unknown; needs verification.

8. **Universal API** (`adam/api/universal/router.py`, 3290 LOC) — largest router in the repo. Function unknown from this pass.

9. **Workflow surface** (`adam/workflows/`, 8 files, 6809 LOC) — Holistic decision workflow + Synergy orchestrator + DSP impression workflow. May parallel campaign_orchestrator in places.

10. **Behavioral analytics** (`adam/behavioral_analytics/`, 43 files, 26545 LOC) — `atom_interface.py` (1317) is large; classifiers cover advertising_effectiveness, approach_avoidance, cognitive_load, cognitive_state_estimator, decision_confidence, emotional_state. Distinguishing data libraries from active decision-time primitives needs DEPTH-3 read.

---

# APPENDIX D — INTEGRATION RULES (codified)

When building NEW code, observe these integration patterns to avoid silos:

## D.1 — Decision-time work belongs in the cascade

If your work modulates which mechanism gets selected, the wire goes into `bilateral_cascade.run_bilateral_cascade()` between L4 (inferential transfer) and the final ε-floor sampler. Insert at the appropriate stage in the modulation chain (per Section "Cascade modulation chain"). Mutate `result.mechanism_scores`. Soft-fail any error to identity-passthrough. Add a `result.reasoning.append(...)` line for observability.

## D.2 — Outcome-time work belongs in outcome_handler

If your work updates state on conversion / click / refund / regret events, your update goes into `adam/core/learning/outcome_handler.py`. Add an import for your update function in `handle_outcome()`. Do not run as a separate event listener that bypasses `outcome_handler` — that creates a silo.

## D.3 — Sync-readable state belongs in graph_cache

If decision-time code needs to read your data, your data lives in `GraphIntelligenceCache`. Add a method, document its TTL, document its read-through fallback. Async-only sources need a sync bridge (see `cohort_modulation.py` for the canonical pattern).

## D.4 — Batch jobs belong in the daily scheduler

If your work is a periodic recompute / refit / audit, register it as a `DailyStrengtheningTask` in `adam/intelligence/daily/` and add to `_register_all_tasks()` in `scheduler.py`. Pick the right schedule_hours + frequency_hours.

## D.5 — Atom DAG work plugs in via construct_dag

New atoms inherit from `BaseAtom` (`adam/atoms/core/base.py`), register their dependencies in `adam/atoms/orchestration/construct_dag.py`, emit a `ChainAttestation` if they produce mechanism evidence. Terminal node is `mechanism_activation.py`.

## D.6 — Platform writes go through factory + integrations/stackadapt

New DSP write paths inherit from `BaseDeliveryAdapter`, register in `ADAPTER_REGISTRY` in `adam/platform/delivery/factory.py`. StackAdapt-specific writes wrap `adam/integrations/stackadapt/adapter.py` rather than redefining mutations.

## D.7 — Blackboard for atom-shared state

If atoms need to share intermediate state, write to one of the 5 blackboard zones (zone1_context / zone2_reasoning / zone3_synthesis / zone4_decision / zone5_learning). Don't pass state through ad-hoc mechanisms.

## D.8 — Gradient Bridge for cross-component credit

Cross-component learning signals route through `adam/gradient_bridge/`. Use `GradientBridgeService` + `SignalPackage` + `LearningSignal`. The orchestrator already wires this.

---

# APPENDIX E — AGGRESSIVE NEXT-SESSION READS (DEPTH-3)

When time permits, the following files merit deep reads to fill remaining gaps:

1. `adam/orchestrator/campaign_orchestrator.py` (2570 LOC) — full decision graph stages
2. `adam/api/dashboard/router.py` (1792 LOC) — every endpoint + intelligence/ consumer
3. `adam/api/universal/router.py` (3290 LOC) — what does Universal API serve?
4. `adam/api/decision/router.py` (1615 LOC) — decision endpoints
5. `adam/orchestrator/adaptive/self_improvement.py` (691 LOC) + `meta_orchestrator.py` (445) — production wiring status of self-evolving brain
6. `adam/workflows/synergy_orchestrator.py` (2690 LOC) + `holistic_decision_workflow.py` (1636) — overlap with campaign_orchestrator?
7. `adam/output/copy_generation/service.py` (2045 LOC) — copy generation production wiring
8. `adam/core/learning/learned_priors_integration.py` (3886 LOC) — what does this actually do?
9. `adam/core/learning/outcome_handler.py` (2818 LOC) — full per-update mapping
10. `adam/atoms/core/mechanism_activation.py` (2627 LOC) — terminal atom logic
11. `adam/api/stackadapt/bilateral_cascade.py` (3110 LOC) — just verify post-session wire integrity
12. `adam/intelligence/page_intelligence.py` (2161 LOC) — page profiler internals
13. `adam/intelligence/unified_psychological_intelligence.py` (1927 LOC) — central integration hub
14. `adam/intelligence/deep_archetype_detection.py` (1925 LOC)
15. `adam/intelligence/psychological_frameworks.py` (2378 LOC)

These are the largest files; reading them gives the densest understanding-per-token.
