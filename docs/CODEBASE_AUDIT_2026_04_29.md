# ADAM Codebase Audit — Existing vs Directive Gap Analysis

**Date:** 2026-04-29
**Audit driver:** ~12,000 lines of "spine" substrate I built in parallel to existing infrastructure. This document maps what already exists, what's wired to production, and what's the real gap.

**Bottom line:** The directive's 13-spine substrate is **substantially already built (~30,000+ lines across the 13 conceptual primitives + 150KB+ of admin/dashboard infrastructure + 95% complete StackAdapt integration)**. The work is in **wiring**, not building. Roughly 50-70% of substrate is currently disconnected from the production orchestrator.

---

## Section 0a — THE CRITICAL FINDING

**The cascade currently uses CACHED MECHANISM SCORES (archive priors), NOT per-user BONG posteriors.**

This is the directive's central N-of-1 claim. Per directive Principle 1 + Section 3: "Every component of the build must compose with this unit of analysis [the single user, not the campaign]." Per Spine #1 spec: "Top-two Thompson sampling (TTTS) over the posterior on best-arm-for-this-user."

**What exists:**
- `bong.py` (735 lines, production-wired) — full BONG natural-parameter posteriors per user
- `outcome_handler.py` calls bong updates on every outcome → posteriors ARE updating
- `cold_start/thompson/sampler.py` — Thompson sampler exists

**What's wired:**
- bong posteriors flow OUT to `information_value.py` and `barrier_diagnostic.py`
- outcomes flow IN to bong (updates work)

**What's NOT wired:**
- The bilateral cascade does NOT read per-user BONG posteriors at decision time. It reads pre-loaded mechanism scores from `graph_cache.py` (archive priors, not user-adaptive).

**Why this matters:** The directive's market-differentiating claim ("ADAM treats each user as their own clinical-trial subject") is currently aspirational, not operational. We have N-of-1 INPUTS (outcomes update posteriors) but the OUTPUT path doesn't read those posteriors per user. The cascade serves population-level archive priors with within-cohort variation.

**This is the single highest-leverage wire to close.** Closing it converts the platform from "smarter contextual targeting" to "true per-user N-of-1 inference" — the directive's foundational differentiator.

**Action:** Wire `bong.get_bong_updater().get_posterior(user_id)` into `bilateral_cascade.compute_creative_intelligence()` so per-user posterior modulates mechanism_scores at decision time. This is a focused change, not a rebuild.

---

## Section 0b — Existing major subsystems the orchestrator wires

The production decision path (`adam/orchestrator/campaign_orchestrator.py`, 2,570 lines) imports:

- `adam.intelligence.unified_intelligence_service` — top-level intelligence aggregator
- `adam.intelligence.review_orchestrator` — review-corpus orchestration
- `adam.intelligence.chain_rendering` — Spine #6 narrative renderer ✓
- `adam.intelligence.online_learning_substrate` — Spine #7 LinkPosterior reads ✓
- `adam.api.stackadapt.bilateral_cascade` (2,955 lines) — Spine #4 production cascade ✓
- `adam.api.stackadapt.graph_cache` — graph caching layer
- `adam.atoms.dag.AtomDAG` — **30-atom cognitive DAG, production-wired** ✓
- `adam.atoms.core.base.BaseAtom` — atom base class
- `adam.cold_start.thompson.sampler.get_thompson_sampler` — **Thompson sampler, production** ✓
- `adam.cold_start.service.get_cold_start_service` — cold-start orchestration ✓
- `adam.blackboard.service.get_blackboard_service` — context blackboard ✓
- `adam.blackboard.memory_blackboard.get_memory_blackboard`
- `adam.meta_learner.service.get_meta_learner` — meta-learning ✓
- `adam.gradient_bridge.service.GradientBridgeService` — credit assignment ✓
- `adam.graph_reasoning.bridge.interaction_bridge.InteractionBridge` — graph reasoning ✓
- `adam.fusion.prior_extraction.get_prior_extraction_service` — bilateral edge priors ✓
- `adam.core.learning.theory_learner.get_theory_learner` — theory learning ✓
- `adam.core.decision_mode` — decision mode policy
- `adam.core.container.get_container` — DI container
- `adam.infrastructure.neo4j.client.get_neo4j_client` — Neo4j wired ✓
- `adam.infrastructure.prometheus.metrics` — metrics
- `adam.retargeting.engines.prior_manager.get_prior_manager` — retargeting priors

Every one of these is real, sized, in production. The spine I built does not touch any of these.

---

## Section 1 — Spine-by-spine: existing vs directive vs my duplicate

### Spine #1 — N-of-1 BONG hierarchical Bayesian engine

**Existing (production-wired, ~1,406 lines):**
- `adam/intelligence/bong.py` (735) — `BONGPosterior`, `BONGUpdater`, `get_bong_updater()`. Multivariate Gaussian posteriors with diagonal+low-rank precision, natural-parameter updates O(d), enables Thompson sampling + information-value bidding. **PRODUCTION-WIRED** (outcome_handler, information_value, barrier_diagnostic).
- `adam/intelligence/bong_promotion.py` (159) — promotion gate via empirical win-rate; ≥1,000 updates × ≥50 individuals × ≥15% mechanism-disagreement × win-rate threshold. **PRODUCTION-WIRED**.
- `adam/intelligence/hierarchical_bayes.py` (512) — PyMC + NumPyro non-centered partial pooling across (archetype × mechanism × category) cells, M3 substrate. `run_nightly_hierarchical_refit()` ready. **NOT WIRED** (M3 follow-on; nightly Airflow DAG pending).

**My duplicate:** `spine/spine_1_n_of_1_engine.py` (530 lines) — pure-Python BONG reference, redundant.

**Action:** **Keep existing. Delete my spine_1.** Wire `run_nightly_hierarchical_refit` into a scheduled job (1-line addition).

---

### Spine #2 — Within-subject scheduler with washout + carryover + MRT

**Existing (production-wired, ~1,354 lines):**
- `adam/intelligence/mechanism_taxonomy.py` (375) — 9 cognitive mechanisms partitioned BLEND_COMPATIBLE / VIGILANCE_ACTIVATING per Foundation §2 attention-inversion. Literature-anchored regret-correlation priors. **PRODUCTION-WIRED**.
- `adam/intelligence/mechanism_taxonomy_runtime.py` (315) — `tag_decision()`, `TaxonomyConditionalAccumulator`, `matched_vs_mismatched_diagonals()` test interface for attention-inversion validation by Week 8. **PRODUCTION-WIRED**.
- `adam/intelligence/mrt_logging.py` (532) — full MRT substrate: ε-greedy floor mixer (ε=0.02), p_t logging at decision time (Boruvka 2018 discipline), Avro-compatible MRTDecisionRecord. **PRODUCTION-WIRED** in `bilateral_cascade.py`.
- `adam/intelligence/mrt_producer.py` (132) — Kafka-ready producer; pilot path uses in-memory log. **PRODUCTION-WIRED**.

**My duplicate:** `spine/spine_2_within_subject_scheduler.py` (410 lines) — washout/carryover/ABAB. Existing has all of this PLUS MRT + p_t logging.

**Action:** **Keep existing. Delete my spine_2.** Verify ABAB scheduling exists in existing or add it as a small extension to existing files.

---

### Spine #3 — Bilateral causal edge + cross-category transfer

**Existing (~4,492 lines, mostly NOT production-wired):**
- `adam/intelligence/causal_forest.py` (483) — EconML CausalForestDML wrapper, weekly Sunday 03:00 UTC fit. **NOT WIRED** (m2_pipeline internal only).
- `adam/intelligence/causal_conformal.py` (243) — distribution-free conformal lift wrap. **NOT WIRED** (lib-gated).
- `adam/intelligence/causal_discovery.py` (762) — PC algorithm + FCI + ATE computation, full causal-graph engine. **NOT WIRED**.
- `adam/intelligence/causal_decomposition.py` (492) — decomposes single conversion into 3-5 causal ingredients. **NOT WIRED**.
- `adam/intelligence/causal_dag_ensemble.py` (347) — M7 ensemble: PC + FCI + GES + DAGMA voting + DoWhy refutation. **NOT WIRED**.
- `adam/intelligence/causal_adjudicator.py` (919) — Loop A→B cross-pollination, observed vs counterfactual, WhyLibrary writes. **NOT WIRED**.
- `adam/intelligence/causal_learning.py` (550) — micro-experiment framework. **NOT WIRED**.
- `adam/intelligence/causal_structure_learner.py` (234) — interventional structure learning, batch nightly. **NOT WIRED**.
- `adam/intelligence/m2_pipeline.py` (392) — M2 fit-and-calibrate bridge with A14 flag emission. **INTERNAL** (lib-gated).

**My duplicate:** `spine/spine_3_bilateral_edge.py` (470 lines) — pure-Python AIPW + transferability matrix. Existing has full DoWhy + EconML + DAGMA pipeline.

**Action:** **Keep existing. Delete my spine_3.** The real gap is **wiring causal_forest + causal_adjudicator → orchestrator** + scheduling weekly fit. Substrate is enormous; integration is the work.

---

### Spine #4 — Trilateral cascade + page posture + fluency floor

**Existing (~6,400 lines, partially production-wired):**
- `adam/api/stackadapt/bilateral_cascade.py` (2,955) — 5-level production cascade (archetype prior → category posterior → bilateral edge → inferential transfer → full atom); ε-floor mixed sampling; ts_propensity logged per handoff §1.1. **PRODUCTION-LIVE** at StackAdapt service endpoint.
- `adam/intelligence/page_attentional_posture_substrate.py` (398) — categorical posture layer with Bayesian shrinkage by author×publication×section, MIN_POSTURE_CONFIDENCE=0.40 threshold. "When we don't know, we don't categorize." **NOT WIRED**.
- `adam/intelligence/page_conditioned_query.py` (764) — trilateral evidence engine: filters 6.7M BRAND_CONVERTED edges on page-signature dimensions, 24h cache. **NOT WIRED**.
- `adam/intelligence/trilateral_epistemic.py` (122) — buyer × page × mechanism uncertainty composition. **NOT WIRED**.
- `adam/intelligence/page_intelligence.py` (2,161) — pre-indexed page profiles, 7-layer psych analysis, Redis-backed <2ms lookup. **PARTIAL** (singleton loaded, not orchestrator-invoked).

**My duplicate:** `spine/spine_4_trilateral_cascade.py` (380 lines) — 5 posture classes + compatibility matrix + hard fluency floor. Existing has the full production cascade plus richer page substrate.

**Action:** **Keep existing. Delete my spine_4.** Real gaps:
1. Wire `page_attentional_posture_substrate` into bilateral_cascade for trilateral conditioning
2. Wire `trilateral_epistemic.epistemic_value()` into score composition
3. Add explicit fluency floor as hard constraint (existing has soft scoring; floor as hard architectural cut may be a real extension)

---

### Spine #5 — Active-inference free-energy

**Existing (~910 lines, partially wired):**
- `adam/intelligence/predictive_processing.py` (622) — `PredictiveProcessingEngine`, `BeliefState`, `CuriosityEngine`, `FreeEnergyCalculator`. Full active-inference substrate. **NOT WIRED** (factory exists, singleton never called).
- `adam/intelligence/processing_depth_router.py` (288) — pre-impression depth predictor (PERIPHERAL/CENTRAL), gates BLEND_COMPATIBLE vs VIGILANCE_ACTIVATING mechanism eligibility. **PRODUCTION-WIRED** in bilateral_cascade.

**My duplicate:** `spine/spine_5_free_energy.py` (320 lines) — pure-Python KL + pragmatic term + softmax(-F). Existing is far richer.

**Action:** **Keep existing. Delete my spine_5.** Real gap: wire `predictive_processing_engine` singleton into `realtime_decision_engine` (1-line addition per the agent's finding).

---

### Spine #6 — DecisionTrace + propensity + off-policy

**Existing (~1,944 lines, mostly LIVE):**
- `adam/intelligence/chain_rendering.py` (495) — materializes inferential-chain artifacts; templated from ChainAttestation; calibration_status visible (PINNED vs PILOT_PENDING). **PRODUCTION-WIRED** in orchestrator + agency_dashboard.
- `adam/intelligence/counterfactual_tracker.py` (206) — counterfactual prediction per non-conversion; secondary learning signal extraction. **PRODUCTION-WIRED** in outcome_handler + daily_intelligence_brief.
- `adam/intelligence/realtime_decision_engine.py` (580) — single entry point fusing all intelligence into <12ms decision; 20-dim space; calendar/news/saturation modulation. **PRODUCTION-WIRED** in api/stackadapt/service.py.
- `adam/intelligence/ope.py` (663) — M4 OPE: IPS, SNIPS, DR, SwitchDR, DRos, MIPS; CI/CD gate per handoff §4.4. **NOT WIRED** as runtime gate yet.

**My duplicate:** `spine/spine_6_decision_trace.py` (410 lines) — DecisionTrace + closed-form TTTS propensity + IPS/SNIPS/DR. Existing has all of this in production.

**Action:** **Keep existing. Delete my spine_6.** Wire `ope.policy_gate()` into candidate-policy CI/CD stage.

---

### Spine #7 — Cohort discovery + non-stationary policy

**Existing (~1,270 lines, production-wired):**
- `adam/intelligence/cohort_discovery.py` (542) — Neo4j GDS Louvain community detection, `UserCohort`, `CohortMembership`, `CohortLearningSignal`. **WIRED to demo + intelligence/__init__.py exports.** Cascade rewire pending.
- `adam/intelligence/mechanism_rotation.py` (551) — pre-registered rotation substrate; immutable falsifiable hypotheses; trigger-firing on EDGE_COUNT_THRESHOLD / CATE_DIFFERENTIAL_THRESHOLD / CONFORMAL_INTERVAL_NON_OVERLAP. **PRODUCTION-WIRED** in agency_dashboard.
- `adam/intelligence/online_learning_substrate.py` (177) — per-decision LinkPosterior reads, geometric mean across theoretical chains. **PRODUCTION-WIRED** in orchestrator (line 1508).

**Plus Cold-Start system (`adam/cold_start/`) — full Thompson sampler:**
- `cold_start/thompson/sampler.py` — Thompson sampler **PRODUCTION-WIRED**
- `cold_start/archetypes/definitions.py` + `detector.py` — archetype detection
- `cold_start/service.py`, `cold_start/api/`, `cold_start/cache/`, `cold_start/events/`, `cold_start/learning/`, `cold_start/models/`, `cold_start/priors/`, `cold_start/unified_learning.py`, `cold_start/workflow/`

**My duplicate:** `spine/spine_7_cohort_policy.py` (280 lines) — SW-UCB + mortal-bandit. Existing has cohort discovery + rotation registry + Thompson sampler all in production.

**Action:** **Keep existing. Delete my spine_7.** Real gap: cohort-conditional cascade scoring (Louvain cohorts → cascade priors). SW-UCB is a candidate addition for true non-stationarity if existing rotation registry doesn't cover it.

---

### Spine #8 — Active-inference epistemic-value bid bonus

**Existing:** `adam/intelligence/inferential_learning_agent.py`, `adam/intelligence/decision_probability.py`, dual-control logic likely in `predictive_processing.py` + `realtime_decision_engine.py`. Need to drill in further.

**My duplicate:** `spine/spine_8_epistemic_bonus.py` (290 lines).

**Action:** **Pending agent-3 confirmation.** Likely deletion candidate.

---

### Spine #9 — Kelly-fraction bid sizing

**Existing:** No direct Kelly module found in initial survey. Bid sizing logic likely embedded in `realtime_decision_engine.py` or retargeting engines. Need to confirm.

**My duplicate:** `spine/spine_9_kelly_bid.py` (280 lines).

**Action:** **POSSIBLY KEEP** (only if existing doesn't cover Kelly). Verify before deletion.

---

### Spine #10 — Online Kalman state-space personalization

**Existing:** No direct Kalman module found. Drift modeling possibly in `bong.py` (state evolution) or `temporal_dynamics.py`. Need to confirm.

**My duplicate:** `spine/spine_10_kalman_personalization.py` (200 lines).

**Action:** **POSSIBLY KEEP** (smallest spine; if existing has no Kalman wrapper, this fills a real gap). Verify.

---

### Spine #11 — LUXY negative-outcome adapter

**Existing (~506 lines, substrate-ready):**
- `adam/intelligence/negative_outcome_adapters.py` (506) — `NormalizedNegativeOutcome`, `NegativeOutcomeAdapterProtocol`, GenericJSON / Stripe / Shopify adapters, `SyntheticNegativeOutcomeInjector`. **NOT YET WIRED** (LUXY stack integration is external dep).

**My duplicate:** `spine/spine_11_negative_outcome_adapter.py` (350 lines) — pixel handler + sapid round-trip.

**Action:** **Keep existing for adapter pattern. The sapid round-trip + `register_sapid_for_decision` from my spine #11 is genuinely additive** (existing doesn't have sapid linkage as a first-class structure). Migrate the sapid-registry to existing module.

---

### Spine #12 — Offline mechanism-discovery pipeline (Claude API as slow brain)

**Existing (~2,580 lines, 90% scaffold / 10% wired):**
- `adam/intelligence/corpus_builder.py` (~500) — `DeepReviewCorpusBuilder`. **NOT WIRED** to production routes.
- `adam/intelligence/argument_constitution.py` (~300) — `ArchetypeSlice`, `MechanismSlice`, `CONSTITUTION_VERSION`. **WIRED** (consumed by constitutional_loop).
- `adam/intelligence/constitutional_loop.py` (~400) — `run_constitutional_loop()`, `CAIResult`, heuristic scorers. **NOT WIRED** to cascade.
- `adam/intelligence/argument_cache.py` (~250) — `CachedArgument`, `get_cached_argument()`, `put_cached_argument()`. **READ PATH WIRED**, write path (M6) not connected.
- `adam/intelligence/argument_ranking.py` (~180) — `rank_variants_via_claude()` soft-fail wrapper. **NOT WIRED**.
- `adam/intelligence/mechanism_adme.py` (~200) — `ADMEProfile` pharmacokinetic models for mechanisms. **NOT WIRED** to scheduler.
- `adam/intelligence/cai_cross_family_critic.py` (~400) — I built this earlier in session. **NOT WIRED** to loop.
- `adam/intelligence/daily_intelligence_brief.py` (~350) — `generate_daily_brief()`. **NOT SCHEDULED**.
- `adam/intelligence/daily/` (41 files, 12 tasks) — `DailyStrengtheningTask`, `run_all_due_tasks()`. Infrastructure exists; **execution schedule undefined**.

**My duplicate:** `spine/spine_12_offline_discovery.py` (410 lines) — knockoff filter + reactance scorer + LUXY metaphor inventory.

**Action:**
- **Keep existing constitutional_loop + argument cache + cai_cross_family_critic.** The reactance-risk scorer in my spine_12 may be additive — verify against `retargeting/engines/rupture_detector.py` + `frustration.py`.
- **The 5 LUXY primary metaphors in my spine_12** may be additive — verify against `brand_copy_metaphor_scoring.py` + `metaphor_alignment.py` + `creative_metaphor_scoring.py`.
- **The real gap is wiring:** constitutional_loop → argument_cache → cascade read path. Cache writer is missing.

---

### Spine #13 — Partner surface (Defensive Reasoning + Loop B + demo)

**Existing (~150KB+ across 24 files, 80% UI/routing / 50% backend integration):**
- `adam/intelligence/defensive_reasoning.py` (~300) — `DefensiveReasoningView`, `render_defensive_reasoning()`. **PARTIAL** (via router only, not cascade).
- `adam/intelligence/agency_dashboard.py` (~350) — `build_agency_dashboard_payload()`. **WIRED** to dashboard service.
- `adam/intelligence/why_library.py` (~400) — `WhyEntry`, `store_why()`, `get_why()`; append-only structured reason store. **WIRED** at recommendation-display time.
- `adam/intelligence/chain_rendering.py` (~250) — pure-function templating. **WIRED** to dashboard + defensive reasoning.
- `adam/explanation/` (3 files) — `ExplanationService`, evidence rendering. **WIRED** to dashboard.
- **`adam/api/dashboard/` (8 files, 70KB+):** router (68K — 40+ endpoints: `/campaigns`, `/analytics`, `/claims`, `/recommendations`, `/ledger`); service (70K — `fetch_graph_intelligence()`, `generate_recommendations()`, `route_dcil_directive_decision()`); models (29K). **PRODUCTION-LIVE**.
- **`adam/api/admin/` (24 files, 50KB+):** auth, campaign mgmt, DB (PostgreSQL + SQLite fallback), 13 DB models (org, campaign, client, user, settings, archetype, creative, directive, domain, report, tracker), 4 routers (auth, campaign, client, org), 3 services (dcil_bridge, deployment, pilot_bootstrap). **PRODUCTION-LIVE**.
- Loop B elicitation in `adam/intelligence/dialogue_ledger/` — full 6-mode v0.2 shipped this session.

**My duplicate:** `spine/spine_13_partner_surface.py` (380 lines) — DR view + MechanismRotationGraph + 10-step CMO walkthrough.

**Action:**
- **Keep existing.** The dashboard + admin infrastructure is enormous (production-live, ~150KB).
- **The 10-step CMO walkthrough script** in my spine_13 is potentially additive — verify dashboard service.py doesn't already have a walkthrough flow.
- **The MechanismRotationGraph data structure** may be additive if dashboard doesn't have it yet.
- **Real gap:** wire `defensive_reasoning.py` into the cascade response (currently only accessible via dashboard query post-hoc).

---

## Section 2 — Additive infrastructure to keep (Chris-flagged)

Per Chris's note 2026-04-29: keep things even if they add a small amount of additional time, as long as they're additive.

### Heavy front-end + back-end
- `adam/sdk/desktop_sdk.js` — desktop SDK
- `adam/api/admin/` — full multi-tenant admin framework with auth, db, migrations, models for archetype/campaign/creative/directive/domain/organization/report/tracker/user, routers, services
- `adam/api/dashboard/` — client_decisions_service, client_report_service, system_insights_service, auth, router
- `adam/api/universal/` — universal router
- `adam/api/intelligence/` — intelligence API endpoint
- `adam/api/decision/` — decision API endpoint
- `adam/api/learning_endpoints.py`, `adam/api/metrics_endpoint.py`
- `adam/demo/static/` — demo dashboards (stackadapt_campaign_dashboard.html, etc.)

### Extensive learning engine
- `adam/intelligence/inferential_learning_agent.py`
- `adam/intelligence/cognitive_learning_system.py`
- `adam/intelligence/knowledge_propagation.py`
- `adam/intelligence/full_intelligence_integration.py`
- `adam/intelligence/learning/` directory
- `adam/learning/emergence_engine.py`, `adam/learning/mechanism_interactions.py`
- `adam/core/learning/theory_learner.py`
- `adam/meta_learner/` — Thompson + neural Thompson + service + learning_integration
- `adam/gradient_bridge/` — attribution + service + learning_integration
- `adam/cold_start/learning/`, `adam/cold_start/unified_learning.py`

### Self-adjusting / self-evolving "brain"
- 30 atoms in `adam/atoms/core/` covering: ad_selection, ambiguity_attitude, autonomy_reactance, brand_personality, channel_selection, cognitive_load, coherence_optimization, construal_level, construct_resolver, cooperative_framing, decision_entropy, dsp_integration, information_asymmetry, interoceptive_style, mechanism_activation, mechanism_registry, message_framing, mimetic_desire_atom, motivational_conflict, narrative_identity, personality_expression, persuasion_pharmacology, predictive_error, query_order, regret_anticipation, regulatory_focus, relationship_intelligence, review_intelligence, signal_credibility, strategic_awareness, strategic_timing, temporal_self, user_state
- `adam/atoms/dag.py` — atom DAG executor
- `adam/atoms/orchestration/construct_dag.py` + `dag_executor.py` + `langgraph_feedback.py`
- `adam/atoms/emergence_detector.py`
- `adam/atoms/intelligence_sources.py`

### SuperAdmin / Admin / campaign creation
- `adam/api/admin/services/dcil_bridge.py` — Decision Component Intelligence Layer bridge
- `adam/api/admin/services/deployment_service.py`
- `adam/api/admin/services/pilot_bootstrap.py` — pilot bootstrapping
- `adam/api/admin/routers/auth_router.py`, `campaign_router.py`, `client_router.py`, `org_router.py`
- `adam/api/admin/migrations/` — database migrations

### Other major subsystems
- `adam/blackboard/` — context blackboard architecture (memory_blackboard, service, zones)
- `adam/experimentation/` — assignment + analysis + service (A/B testing infrastructure)
- `adam/retargeting/engines/` — 38 specialized engines including claude_argument_engine, narrative_arc, prospect_theory, rupture_detector, neural_linucb, etc.
- `adam/fusion/` — bidirectional_learning, creative_patterns, prior_extraction, resonance_index
- `adam/ml/` — foundation_model, online_learner, training_pipeline
- `adam/signals/` — linguistic + nonconscious signal processors
- `adam/infrastructure/` — neo4j, kafka, prometheus, redis, alerting, resilience

---

## Section 3 — Real gaps (where directive truly extends what exists)

These are the items that warrant new substrate work because existing doesn't cover them:

### High-confidence real gaps

1. **Sapid round-trip linkage table.** Existing StackAdapt code has webhook + pixel handling but doesn't have an explicit `sapid → (decision_id, user_id, feature_vector)` registry as a first-class structure. My `spine_11.register_sapid_for_decision` + `SapidRoundTripMonitor` may be additive — but could be merged into existing `negative_outcome_adapters.py` instead of standalone.

2. **Hard fluency floor as architectural constraint.** Existing bilateral_cascade has soft scoring; whether it has a HARD floor that REMOVES candidates (not just downscores them) needs verification. If not present, this is a real Foundation §7 rule 11 extension.

3. **mSPRT campaign-level monitor.** Existing `experimentation/` has assignment + analysis + service but not specifically Wald-mSPRT for sequential probability ratio testing. May be additive (verify).

4. **8 RED-criteria launch-gate aggregation.** Existing pilot_bootstrap.py and deployment_service.py likely have launch-gate logic; my Phase 10 substrate may be additive as a structured check-set per directive Section 9 Phase 10.

5. **CMO walkthrough script (10 templated steps).** Existing dashboard has reports + decisions services; the structured walkthrough script with cognitive-vocabulary templated narrative may be additive as a new model in `api/dashboard/`.

### Medium-confidence gaps (need verification)

6. **Active-inference free-energy as decision-time scoring objective.** Existing `predictive_processing.py` has the engine but isn't called. Wiring is the gap, not building.

7. **Kalman state-space personalization wrapping BONG.** Need to check if `bong.py` already does state-space drift OR if `temporal_dynamics.py` covers this.

8. **Kelly-fraction bid sizing.** Need to check if existing bid sizing is honest about uncertainty (Kelly criterion specifically) or uses simpler heuristics.

9. **Knockoff-filter FDR control on interaction discovery.** Existing causal_discovery + causal_dag_ensemble may already do FDR. Verify.

### Low-confidence gaps (probably exist somewhere)

10. **Reactance-risk independent scorer.** May exist in retargeting/engines (rupture_detector.py? frustration.py?). Verify before keeping my version.

11. **Primary-metaphor inventory for LUXY.** Existing brand_copy_metaphor_scoring.py + metaphor_alignment.py + creative_metaphor_scoring.py likely cover this. Verify.

---

## Section 4 — Recommended action plan (prioritized for "build asap")

### Phase A: Cleanup (1-2 hours, high ROI)

A1. **Delete the 13 spine modules I built that fully duplicate existing.** Specifically delete from `adam/intelligence/spine/`:
- `spine_1_n_of_1_engine.py` (existing: bong.py + hierarchical_bayes.py)
- `spine_2_within_subject_scheduler.py` (existing: mechanism_taxonomy_runtime + mrt_*)
- `spine_3_bilateral_edge.py` (existing: causal_*.py + m2_pipeline.py)
- `spine_4_trilateral_cascade.py` (existing: bilateral_cascade.py + page_*.py + trilateral_epistemic.py)
- `spine_5_free_energy.py` (existing: predictive_processing.py + processing_depth_router.py)
- `spine_6_decision_trace.py` (existing: chain_rendering + counterfactual_tracker + ope.py + realtime_decision_engine)
- `spine_7_cohort_policy.py` (existing: cohort_discovery + mechanism_rotation + online_learning_substrate + cold_start)
- `spine_8_epistemic_bonus.py` (verify against inferential_learning_agent + predictive_processing)
- `spine_11_negative_outcome_adapter.py` (existing: negative_outcome_adapters.py)
- `spine_12_offline_discovery.py` (existing: corpus_builder + argument_constitution + daily_intelligence_brief + mechanism_adme + constitutional_loop)
- `spine_13_partner_surface.py` (existing: defensive_reasoning + agency_dashboard + why_library + chain_rendering)

A2. **KEEP these (if real gaps confirmed):**
- `phase_8_stackadapt_integration.py` — sapid round-trip + holdout (additive)
- `phase_9_pre_launch.py` — mSPRT (verify experimentation/ doesn't already do this)
- `phase_10_launch_sequence.py` — 8 RED-criteria aggregator (verify)
- `spine_9_kelly_bid.py` — Kelly bid sizing (verify)
- `spine_10_kalman_personalization.py` — Kalman wrapper (verify against bong.py)

A3. **Test files for deleted spines:** delete corresponding `tests/unit/spine/test_*.py`. Keep tests for additive items.

### Phase B: Verify gaps (1-2 hours)

B1. Check `experimentation/service.py` for mSPRT.
B2. Check `bong.py` for Kalman / state-space evolution (it already has natural-parameter updates; check for time-decay).
B3. Check `realtime_decision_engine.py` + `retargeting/engines/` for Kelly bid sizing.
B4. Check `retargeting/engines/rupture_detector.py` + `frustration.py` for reactance scoring.
B5. Check `brand_copy_metaphor_scoring.py` + `metaphor_alignment.py` for primary-metaphor inventory.
B6. Check `pilot_bootstrap.py` + `deployment_service.py` for launch-gate logic.

### Phase C: Wire what's not wired (THE REAL WORK; days, not weeks)

C1. **Wire `predictive_processing_engine` into `realtime_decision_engine.py`** (1 line per agent finding).
C2. **Wire `page_attentional_posture_substrate` into `bilateral_cascade.py`** for trilateral conditioning.
C3. **Wire `trilateral_epistemic.epistemic_value()` into score composition.**
C4. **Schedule `run_nightly_hierarchical_refit()` as a job.**
C5. **Schedule `run_weekly_causal_forest_fit()` as a job.**
C6. **Wire `ope.policy_gate()` into candidate-policy CI/CD stage.**
C7. **Wire `causal_adjudicator` → WhyLibrary reads into cascade's inferential layer.**
C8. **Wire cohort-conditional priors from `cohort_discovery` into bilateral_cascade.**
C9. **Add fluency floor as hard constraint in cascade** (if not present).
C10. **Activate StackAdapt write paths via the new GraphQL token** (just shipped GraphQL fix).

### Phase D: Real gaps (days)

D1. Add sapid round-trip registry to `negative_outcome_adapters.py` (or wherever fits best).
D2. Add `SapidRoundTripMonitor` to existing monitor or create as part of StackAdapt integration.
D3. Add 8 RED-criteria aggregator to `pilot_bootstrap.py` or `deployment_service.py`.
D4. Add structured CMO walkthrough script to `api/dashboard/` if not present.
D5. Add reactance-risk scorer if not present.

---

## Section 5 — Time estimate

Per Chris's reframe ("8-12 week plan we can actually get it all finished in 2 weeks"):

- **Phase A (cleanup):** 2-3 hours
- **Phase B (verify gaps):** 2-3 hours
- **Phase C (wiring):** 3-5 days (the real load-bearing work)
- **Phase D (additive gaps):** 2-3 days
- **Phase E (live API integration + smoke tests):** 1-2 days

**Total: ~10 working days = 2 weeks.** Matches Chris's reframe.

---

## Section 6 — Alignment proposal for next session

Per the new session-start alignment cadence rule, when we resume next:

**Proposal — TWO PARALLEL TRACKS:**

**Track 1 (cleanup; ~3 hours):**
- Phase A: Delete confirmed-duplicate spine modules (#1, #2, #3, #4, #5, #6, #7, #11, #12, #13).
- Phase B: Verify medium-confidence gaps (Spine #9 Kelly bid, #10 Kalman, mSPRT vs experimentation/, primary-metaphor inventory, reactance scorer, launch-gate aggregator).
- Output: definitive "real gap list" + spine modules deleted with one consolidated commit.

**Track 2 (the highest-leverage wire; ~1 day):**
- Wire per-user BONG posteriors into bilateral_cascade. This converts the system from "archive-prior-based cascade" to "true N-of-1 inference." Section 0a above.
- Concrete change: read `BONGUpdater.get_posterior(user_id)` inside `bilateral_cascade._select_primary_with_logged_propensity()` and modulate mechanism_scores per posterior.
- Test: synthetic user with biased outcome history → cascade output reflects that bias.

**Then:** Phase C (broader wiring of other disconnected substrate) and Phase D (real-gap fills) — days, not weeks.

**Not in scope this session:** writing new substrate beyond the BONG-wire, refactoring existing modules.

**Done criterion:**
1. Updated audit document with verified gap list ✓ (this doc when refined)
2. Spine modules deleted from filesystem
3. Per-user BONG posteriors flowing into cascade decision

---

## Section 7 — What this audit changes

Before this audit: 19 commits, ~12,000 lines of disconnected spine substrate, "cognitive spine fully built per directive" claim that was structurally true but operationally false.

After this audit: clear picture that:
- The directive is ~80% already built (~30,000+ lines of cognitive infrastructure existing)
- The work remaining is roughly 80% wiring, 20% real-gap-filling
- The single highest-leverage wire is per-user BONG posteriors → cascade
- The 2-week reframe Chris proposed is achievable

The cost of the duplication was opportunity cost (1 day of session work that should have been spent wiring), not architectural cost (the spine modules are deletable; nothing depended on them in production).

**This audit replaces my prior 19-commit "cognitive spine substrate complete" framing.** The substrate was already complete. What we have now is a wiring-and-gap-fill task list grounded in observed code, not a substrate-build task list.
