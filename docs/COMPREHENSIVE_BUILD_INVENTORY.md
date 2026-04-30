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
