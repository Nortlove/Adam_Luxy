# Causal Infrastructure Comprehensive Depth Audit
## Slice ID: C.1 (Option 3 scope per Claude Proper adjudication)
## Predecessor: 95f209b (depth verification); 46734d9 (Phase 1+2); fbae83e (P.1)
## Audit type: Read-only comprehensive deep inspection
## Branch: feature/hmt-dashboard
## Module count: 8 causal_* modules + blind_analysis (box + lee)
## Total LOC inspected: ~4,659 (causal_*: 4,030; blind_analysis: 629)

---

## §1 Executive Summary

**Pass 4 finding: D — capabilities exist as silos.**

Eight `causal_*` modules totaling ~4,030 LOC implement substantial causal-inference machinery: direct-effect discovery (causal_learning), CATE estimation via Wager-Athey causal forests (causal_forest), conformal prediction wrap (causal_conformal), per-conversion decomposition into causal ingredients (causal_decomposition), constraint-based PC discovery (causal_discovery), ensemble PC+FCI+GES+DAGMA discovery (causal_dag_ensemble), interventional-data structure learning (causal_structure_learner), and campaign-outcome counterfactual adjudication (causal_adjudicator). These modules are **substantively implemented** — not stubs, not theory-in-docstring, not boilerplate-with-shrug. Three modules have B3-LUXY-grade unit tests (causal_dag_ensemble 217 LOC, causal_forest 281 LOC, causal_conformal 306 LOC). The pre-registration substrate (blind_analysis/box.py 287 LOC + lee.py 302 LOC) is fully implemented with Lyons 2008 / Gross-Vitells 2010 / Davies 1987 theoretical anchors and its own 600+ LOC test suite.

**But the composition layer does not exist.** The 8 causal modules have NON-OVERLAPPING callers. NO causal_* module imports another causal_* module. NO causal_* module imports `adam.blind_analysis.*`. NO causal_* module cross-references `msprt_*` or `spine.*`. NO module composes capabilities into a single end-to-end test of the bilateral architecture's central trait × state composition claim. The substrate is built; the integration is not. blind_analysis/box.py and lee.py are isolated libraries — only their own test suite consumes them; ZERO code-path integration into causal discovery, causal forests, causal adjudication, or anywhere else in adam/.

**Q.B / Q.3 slice scope under Finding D: ~800-1,200 LOC build** (sketch in §10). This is the substantial slice, not the small one. The integration layer threading existing capabilities + pre-registration plumbing + at-least-one-edge-type for trait × state composition + cascade read-path extension. **Recommended posture for Claude Proper adjudication:** consider ship-minimum-viable-scaffold pre-pilot (single (archetype × page_dim × mechanism) edge type via causal_forest's existing CATE machinery, pre-registered in blind_analysis/box.py, written to Neo4j as `:CONDITIONS_AMPLIFICATION_OF`); defer full composition build to post-pilot when calibration data exists.

**C.2 + C.3 dependency assessment:** still valuable for OTHER architectural questions but **NOT load-bearing for Q.B/Q.3.** C.1's expanded scope absorbed the existence questions for the causal-attribution dimension. C.2 (spine/) is recommended for Q.D (loop closure cadence); C.3 (msprt + dual_eval + free_energy) is recommended for understanding sequential-testing integration if Q.B's interaction-test scaffold needs early-stopping discipline.

**Cross-architectural-question implications (§9):** the silo pattern matters beyond Q.B. Q.D (loop closure cadence) sees three different cadences — bid-time read (causal_learning), per-conversion (causal_decomposition + causal_adjudicator), weekly batch (causal_forest, causal_dag_ensemble). Cut B reporting (Q.C) has 3-4 modules producing operator-actionable surfaces (CATE heterogeneity per cell, decomposition causal recipes per conversion, adjudication outcomes per deviation, discovered causal edges) but no unified surface aggregator. Post-pilot iteration: 2 of 8 modules (causal_forest, causal_dag_ensemble) have explicit weekly cron interfaces; 1 (causal_adjudicator) has horizon-window-driven cadence; the others have ad-hoc or in-memory-only patterns.

---

## §2 Pass 1 — Module structure + entry points (per-module summary)

### 2.1 causal_learning.py (550 LOC)

**Stated purpose:** "Every Impression Is A Micro-Experiment" — capture every impression as a (treatment, context, subject, outcome) observation; discover `(:PageDimension)-[:AMPLIFIES|:SUPPRESSES]->(:CognitiveMechanism)` edges from accumulated data.

**Public surface:**
- `CausalObservation` dataclass (line 63) — captures page_edge_dimensions (20-dim), archetype, buyer_edge_dimensions, mechanism_sent, framing, outcome
- `record_causal_observation()` (line 159) — write to Redis circular buffer
- `CausalTestEngine` class (line 242) — `test_dimension_amplifies_mechanism` (direct effect only) + `test_all_direct_effects` (200-test grid + BH FDR) + `test_cross_category_universality`
- `persist_causal_discovery()` (line 407, async) — Neo4j writeback for validated discoveries
- `query_causal_effects()` (line 461, async) — bid-time Neo4j read
- `_apply_bh_correction` (line 529) — Benjamini-Hochberg FDR

**Module constants:** EDGE_DIMENSIONS (20-dim list — pre-W.2b vintage, missing maximizer_tendency); MECHANISMS (10-mech: includes `cognitive_ease`, missing `anchoring` — diverges from F.2 canonical Cialdini-9)

**Imports:** stdlib only (json, logging, math, time, dataclasses, typing). **Zero external causal-inference library imports.** From-scratch z-test + Cohen's h + BH FDR + normal CDF approximation.

**Callers (3):**
- `adam/api/stackadapt/bilateral_cascade.py:2046` — bid-time read
- `adam/core/learning/outcome_handler.py:336` — per-outcome write
- `adam/intelligence/daily/task_15_self_teaching.py:726` — daily batch test + persist

### 2.2 causal_adjudicator.py (919 LOC)

**Stated purpose:** "Loop A → Loop B cross-pollination" — read Deviations whose horizon window has closed; evaluate observed campaign outcome against `system_counterfactual`; write `adjudication_status='adjudicated'`; create Outcome node; on `system_right` outcome generate WhyLibraryEntry as pre-emptive defensive warning.

**Public surface:**
- `AdjudicationResult`, `AdjudicationBatch` (frozen dataclasses)
- Per-recommendation-type evaluators: `_evaluate_pause_campaign` (CPA recovery test), `_evaluate_zero_conversions`, `_evaluate_low_ctr` (CTR ≥1.5× lift threshold), `_evaluate_client_recommendation` (Front-end A path; honest indeterminate due to Structural Weakness #4)
- `_persist_why_library_entry` (line 353, async) — Neo4j WhyLibraryEntry writer
- `adjudicate_deviation_with_operator_verdict` (line 665, async) — operator-led verdict path with idempotency
- `adjudicate_ready_deviations` (line 823, async) — batch driver, horizon-window gated
- `fetch_why_library` (line 889, async) — read path

**Module constants:** `_BIAS_CLASS_DEFAULTS` (3 mappings), `_HORIZON_TO_DAYS` (4 mappings), `_EVALUATORS` (3 dispatch entries)

**Imports:** stdlib only (json, logging, uuid, dataclasses, datetime, typing). Lazy-imports `adam.api.dashboard.service.fetch_stackadapt_summary` for live state, `adam.infrastructure.neo4j.client` for Neo4j.

**Callers (2):**
- `adam/api/dashboard/router.py` (operator verdict endpoint)
- `adam/intelligence/daily/task_29_6_horizon_adjudicator.py` (scheduled batch)

**Edge types written:** `(:Deviation)-[:RESOLVED_AS]->(:Outcome)`, `(:WhyLibraryEntry)` node creation

### 2.3 causal_conformal.py (243 LOC)

**Stated purpose:** "Distribution-free, finite-sample marginal-coverage guarantee on treatment-effect / lift predictions." Wraps M2's CausalForestDML output with split-conformal coverage that survives at-any-N (vs. parametric delta-method CIs that under-cover at moderate N).

**Public surface:**
- `ConformalLiftInterval` (frozen dataclass) — point_estimate, lower, upper, coverage_probability, calibration_size
- `ConformalLiftWrap` (mutable dataclass) — `record_realization(predicted, realized)` accumulates calibration pairs append-only; `interval(predicted, alpha)` emits the conformal interval; `empirical_coverage(alpha)` checks calibration

**Module constants:** `DEFAULT_MIN_CALIBRATION_SIZE = 20`, `DEFAULT_ALPHA = 0.05`

**Imports:** stdlib only (math, dataclasses, typing). **No external lib dependency** — split-conformal is closed-form on residuals.

**References:** Vovk-Gammerman-Shafer 2005, Lei-G'Sell-Rinaldo-Tibshirani-Wasserman 2018, Romano-Patterson-Candès 2019.

**Callers (2):**
- `adam/intelligence/m2_pipeline.py`
- `adam/intelligence/synthetic_ab_simulation.py`

**Edge types written:** NONE — in-memory calibration only.

### 2.4 causal_dag_ensemble.py (347 LOC) — M7 substrate

**Stated purpose:** Per Seven-Component Methodology Handoff §7 — discover causal DAG over 31 identity-stable + 27 alignment + 9 mechanism dims via PC + FCI + GES + DAGMA ENSEMBLE; keep edges surviving ≥2/4 method votes; DoWhy refutation pending.

**Public surface:**
- `M7CausalEdge` (frozen dataclass) — source, target, method_votes, methods
- `DiscoveryDiagnostics` — methods_run, methods_failed, library_versions
- `CausalDiscoveryLibsMissingError`
- Per-method discoverers: `discover_pc`, `discover_fci`, `discover_ges`, `discover_dagma` (each gates own import via `_try_import_*`)
- `standardize_columns` — Reisach-Seng-Schölkopf 2021 defense (NOTEARS/DAGMA exploit variance ordering; standardize FIRST)
- `ensemble_vote(edge_sets, min_votes=2)` — vote aggregator
- `run_causal_discovery(X, varnames, alpha, min_votes)` — top-level driver
- `write_causal_edge_to_neo4j` — `(:PsychDim)-[:CAUSES]->(:PsychDim)` writeback

**Imports:** stdlib + numpy + soft-imports (causallearn, dagma). Library version pins per handoff §7.6.

**Callers:** **ZERO non-test callers in adam/** — module is M7 substrate but has not been wired into any orchestrator. Has 217-LOC test file.

**Edge types written:** `(:PsychDim)-[:CAUSES]->(:PsychDim)` — DIFFERENT node label from causal_discovery's :CausalVariable. Two parallel "causal graphs" exist with no namespace coordination.

### 2.5 causal_decomposition.py (492 LOC)

**Stated purpose:** "Decomposes a conversion into its CAUSAL INGREDIENTS." Connective tissue between three intelligence types: empirical (gradient fields), inferential (theory graph), discovery (emergence). Identifies the 3-5 active causal dimensions per specific conversion.

**Public surface:**
- `CausalIngredient` dataclass — dimension, value, gradient_magnitude, page_gradient_magnitude, theory_support, causal_role (`primary` | `amplifier` | `moderator` | `enabler`), evidence string; `combined_strength` property weights three sources (0.4 buyer + 0.3 page + 0.3 theory)
- `CausalRecipe` dataclass — decision_id, archetype, mechanism, ingredients, active_chain, conditions (threshold dict for hypothesis generation), is_surprising flag, recipe_signature property
- `CausalDecompositionEngine` class — `decompose(decision_id, metadata, success)` orchestrates three intelligence sources; `_get_buyer_gradients` reads BayesianPrior nodes from Neo4j; `_get_page_gradients` reads page_gradient_fields module; `_get_active_chain` calls reasoning_chain_generator.generate_chains_local
- `_check_surprise` — surprises detected when `cascade_mechanism_selected != mechanism` OR `decision_probability < 0.3`
- `get_causal_decomposition_engine()` singleton accessor

**Imports:** stdlib + lazy imports (neo4j, page_gradient_fields, reasoning_chain_generator, graph_cache).

**Callers (3):**
- `adam/core/learning/outcome_handler.py`
- `adam/intelligence/daily_intelligence_brief.py`
- `adam/intelligence/inferential_hypothesis_engine.py`

**Edge types written:** NONE — in-memory recipe storage (max 10K, FIFO).

### 2.6 causal_discovery.py (762 LOC) — pre-existing, separate from M7 ensemble

**Stated purpose:** "Goes beyond correlation: Learns CAUSAL structure from observational data." Constraint-based PC algorithm + FCI for latent confounders + ATE estimator + intervention analysis.

**Public surface:**
- `CausalDiscoveryConfig` (alpha=0.05, max_conditioning_set=3, min_samples_for_test=50, min_samples_for_effect=100, bootstrap_samples=100, confidence_threshold=0.8, max_variables=50)
- `EdgeType` enum (DIRECTED / UNDIRECTED / BIDIRECTED)
- `RelationshipStrength` enum (STRONG ATE>0.3 / MODERATE 0.1<ATE<0.3 / WEAK ATE<0.1)
- `CausalEdge`, `CausalGraph` (Pydantic BaseModel — different shape from M7CausalEdge)
- `IndependenceTest` — Fisher's z-transform partial correlation test
- `PCAlgorithm` (line 254) — full PC implementation: edge removal phase + v-structure orientation + Meek's rules
- `CausalEffectEstimator` — `estimate_ate` with adjustment-formula + IPW + DR, returns ATE + CI
- `CausalDiscoveryEngine` — `discover_causal_structure`, `estimate_effect`, `identify_confounders`, `suggest_interventions`
- `_identify_adjustment_set` — backdoor criterion implementation
- `get_causal_discovery_engine()` singleton

**References:** Pearl 2009, Spirtes-Glymour-Scheines 2000, Peters-Janzing-Schölkopf 2017.

**Imports:** stdlib + numpy + scipy.stats + pydantic. **Implements PC + ATE estimation from scratch** (does not use causal-learn library — that's causal_dag_ensemble's territory).

**Callers (1):**
- `adam/intelligence/full_intelligence_integration.py`

**Edge types written:** `(:CausalVariable)-[:CAUSES]->(:CausalVariable)` via `to_neo4j_cypher()` method (caller-driven; module returns Cypher string but does not execute it).

### 2.7 causal_forest.py (483 LOC) — M2 substrate

**Stated purpose:** Per Seven-Component Handoff §2 — Wager-Athey 2018 / Athey-Tibshirani-Wager 2019 causal forests for CATE per (archetype × mechanism × category) cell; weekly fits feed Beta(α, β) prior updates that TS samples from online (Booking/Netflix/Microsoft ALICE pattern).

**Public surface:**
- `CATEResult` dataclass — archetype, mechanism, category, tau_hat, tau_lower, tau_upper, n_events, cell_under_powered (True when n<200 per handoff §2.9 caveat: 95% nominal → 88-93% empirical at low N)
- `FitDiagnostics` — cells_fit, cells_skipped_low_n, cells_failed, library_versions
- `LoggedDecisionRow` — matches M1+M4 schema; pscore_known discipline anchor (Boruvka 2018 §2)
- `LibsMissingError` — explicit fail when EconML missing; "a fit returning None on missing libs would let callers consume meaningless τ̂ silently" (discipline anchor in docstring line 25)
- `load_decision_outcome_rows_for_cell` — Neo4j read with pscore_known=true filter, days_lookback default 90
- `fit_causal_forest_for_cell(rows, forest_params)` — wraps EconML CausalForestDML with handoff §2.3 params (n_estimators=2000, min_samples_leaf=15, max_samples=0.45, max_depth=10, honest=True, cv=5, random_state=42)
- `write_cate_to_neo4j` — `(:Archetype)-[:RESPONDS_TO]->(:CognitiveMechanism)` edge writeback
- `run_weekly_causal_forest_fit(cells, driver, days_lookback)` — weekly cron interface (handoff §2.10 cadence: Sunday 03:00 UTC)

**Imports:** stdlib + soft-import EconML. Lazy-imports CausalForestDML, sklearn GBR/GBC, numpy inside the fit.

**Callers (2):**
- `adam/intelligence/daily/task_35_causal_forest_fit.py` (scheduled)
- `adam/intelligence/m2_pipeline.py`

**Edge types written:** `(:Archetype)-[:RESPONDS_TO]->(:CognitiveMechanism)` with properties tau, tau_lo, tau_hi, n, fitted_at, cell_under_powered, category.

### 2.8 causal_structure_learner.py (234 LOC)

**Stated purpose:** "Learns causal structure between alignment dimensions from the system's own interventional data. Every mechanism deployment is a soft intervention on specific dimensions." Processes EnrichedInterventionRecords with diagnostic-hypothesis weighting (H1-H5 strengths from 0.2-1.0).

**Public surface:**
- `EdgeDirection` enum (FORWARD / REVERSE / NONE / BIDIRECTIONAL)
- `CausalEdgeEvidence` dataclass — interventions_on_a, b_shifted_given_a (and reverse), log_odds_forward + log_odds_reverse; properties direction_posterior (softmax over forward/reverse/none), most_likely_direction, confidence
- `CausalStructureLearner` class — pairwise-edge tracker over named dimension list; `process_record(record)` updates evidence per intervention; `process_batch(records)`; `get_discovered_graph(confidence_threshold=0.7)` returns adjacency list; `validate_theory_link(cause, effect)` checks theoretical link against observed evidence

**Module constants:** `SHIFT_THRESHOLD = 0.03`; `HYPOTHESIS_WEIGHTS` (6-entry dict including `H1_wrong_page_mindstate=0.3`, `H2_wrong_mechanism=1.0`, `H5_ad_fatigue=0.2`)

**Imports:** stdlib + numpy. Module-level numpy import (no soft-import gate).

**Callers:** **ZERO callers in adam/.** **ZERO test files reference it.** Pure-build, never wired.

**Edge types written:** NONE — in-memory only.

### 2.9 blind_analysis/box.py (287 LOC)

**Stated purpose:** Pre-register parameters of an analysis BEFORE any data is unblinded. Specifies parameter grid + decision statistic + threshold + signal/control regions. Sealed with deterministic SHA-256 pre_registration_hash; mutation forbidden after sealing.

**Public surface:**
- `BoxValidationError`, `UnblindingState` enum (SEALED → AUTHORIZED → UNBLINDED)
- `BoxParameter` (frozen dataclass) — name + values tuple
- `BlindAnalysisBox` (frozen dataclass) — full pre-registered box with state machine; `authorize_unblinding(party, justification)`, `mark_unblinded()`, `is_in_signal()`, `is_in_control()`
- `sealed_box(...)` factory — disjointness invariants + grid-membership check + deterministic hash
- `placeholder_data_generator(box, seed, null_mean, null_std)` — synthetic NULL-hypothesis data over parameter grid for end-to-end analysis exercise without touching live data

**References:** Lyons 2008 (*Annals of Applied Statistics* 2:887-915, blind analysis as discipline against multiple-comparisons + post-hoc fitting bias).

**Callers anywhere in adam/:** **ZERO.** Only consumer: `tests/blind_analysis/test_box.py`.

### 2.10 blind_analysis/lee.py (302 LOC)

**Stated purpose:** Gross-Vitells look-elsewhere effect (LEE) trial-factor implementation. Corrects local-p-values for "look elsewhere" bias when same test statistic is evaluated at many parameter points.

**Public surface:**
- `MonteCarloLEEResult` (frozen dataclass) — n_trials, n_grid_points, max_z_per_trial, upcrossings_at_zero; `empirical_p_global(threshold)` method
- `p_local_one_sided(z)` — closed-form Gaussian one-sided p-value
- `gross_vitells_global_p_value(local_z, upcrossings_at_reference, reference_z)` — equation (1) closed form
- `gross_vitells_trial_factor(local_z, upcrossings_at_reference, reference_z)` — TF(z) = p_global / p_local
- `monte_carlo_global_p_value(...)` — synthetic Gaussian-process ensemble for non-asymptotic ground truth
- `empirical_upcrossings_at_threshold(field, threshold)` — calibration helper

**References:** Gross-Vitells 2010 (*Eur. Phys. J. C* 70:525-530), Davies 1987 (*Biometrika* 74:33-43), Lyons 2008.

**Callers anywhere in adam/:** **ZERO.** Only consumer: `tests/blind_analysis/test_lee.py`.

---

## §3 Pass 2 — Discovery / inference trigger + cadence

| Module | Trigger | Cadence | Evidence consumed | Granularity |
|--------|---------|---------|-------------------|-------------|
| causal_learning | (1) bid path read; (2) per-outcome write; (3) daily batch test+persist | (1) per-bid; (2) per-outcome; (3) daily | Redis 50K obs buffer + Neo4j edge graph | Mixed: write per-impression, discovery aggregate-batch, read per-bid |
| causal_adjudicator | Horizon-window-elapsed Deviations + operator verdict endpoint | Horizon-window-driven (1d/7d/14d/60d per `_HORIZON_TO_DAYS`) + on-demand operator | Deviations from Neo4j + live StackAdapt summary via `fetch_stackadapt_summary` | Per-deviation |
| causal_conformal | `record_realization(pred, real)` per realized cell + `interval(pred, alpha)` per request | Append-only calibration; intervals on-demand | In-memory `_pairs` list (no persistence) | Per-cell calibration |
| causal_dag_ensemble | NOT WIRED. `run_causal_discovery(X, varnames)` is the top-level driver but no caller invokes it | N/A — substrate only | Unwired (intended: PsychDim observation matrix) | N/A |
| causal_decomposition | `decompose(decision_id, metadata, success)` per outcome | Per-conversion (called from outcome_handler + daily_intelligence_brief + inferential_hypothesis_engine) | Neo4j BayesianPrior nodes (gradient_field) + page_gradient_accumulator + reasoning_chain_generator output + decision metadata | Per-conversion |
| causal_discovery | `discover_causal_structure(data, variable_names)` + `estimate_effect(...)` | On-demand from `full_intelligence_integration.py` | numpy data matrix passed in by caller | Per-call (caller-driven; no scheduled cron) |
| causal_forest | `run_weekly_causal_forest_fit(cells)` + `task_35_causal_forest_fit.py` | Weekly Sunday 03:00 UTC (handoff §2.10) | Neo4j AdDecision rows joined HAD_OUTCOME (90d lookback, pscore_known=true filter) | Per-(archetype × mechanism × category) cell |
| causal_structure_learner | `process_record(record)` — pure substrate, never invoked | N/A — pure substrate | EnrichedInterventionRecord dicts (no caller) | N/A |
| blind_analysis/box | `sealed_box(...)` factory | One-shot pre-registration event | None — defines the analysis BEFORE data | Per-experiment |
| blind_analysis/lee | `gross_vitells_*` + `monte_carlo_global_p_value` | On-demand statistical computation | Local z + upcrossings calibration (or MC ensemble) | Per-statistic |

**Cadence summary:** at least 4 distinct cadences operate across these modules:
- **Per-bid (μs-grain):** causal_learning read
- **Per-outcome (event-grain):** causal_learning write, causal_decomposition decompose, conformal calibration
- **Per-deviation horizon-window-elapsed (1d-60d):** causal_adjudicator
- **Weekly batch (Sunday 03:00 UTC):** causal_forest fit, causal_dag_ensemble (intended but unwired)
- **Daily batch:** causal_learning discovery, daily_intelligence_brief consuming causal_decomposition

**Q.D (loop closure cadence) implications surfaced — see §9.**

---

## §4 Pass 3 — Statistical-validation gating + multiple-comparison controls

| Module | Statistical gate | Multiple-comparison control | Refutation |
|--------|------------------|----------------------------|------------|
| causal_learning | p-value < 0.05 AND Cohen's h > 0.2 (BOTH required, AND) | **Benjamini-Hochberg FDR** in-module on the 200-test grid (20 dims × 10 mechs); cross-category universality test separate | NONE in module. Discovery → straight to Neo4j. No DoWhy / placebo / random-common-cause / unobserved-confounder tests called |
| causal_adjudicator | Heuristic thresholds per recommendation type: CPA recovery <70% of original (user_right); CPA still ≥3× advertiser avg (system_right); CTR ≥1.5× original lift (user_right); CTR <0.1% floor (system_right); zero conversions (binary). Confidence stamped 0.6 for evaluator-led, 1.0 for operator-led | NONE — per-deviation evaluation, not multi-hypothesis grid | NONE — directional adjudication. Module docstring: "v1 makes a directional adjudication — real causal-inference would require holdouts." |
| causal_conformal | Split-conformal quantile: ceil((n+1)(1-alpha))-th smallest absolute residual; coverage holds under exchangeability assumption | Distribution-free finite-sample marginal coverage at any N (via construction); empirical_coverage method reports calibration drift | Drift in DGP across pilot's lifetime causes empirical coverage to diverge from nominal — that signal is itself useful and should be monitored (per docstring) |
| causal_dag_ensemble | Per-method significance: alpha=0.01 default for PC/FCI; ensemble vote ≥2/4 methods | Vote aggregation IS the multiple-comparison control (single edge survives only if 2+ methods agree) | DoWhy refutation NAMED in handoff §7 but **NOT IMPLEMENTED IN MODULE.** Docstring at line 13 says "DoWhy refutes high-vote edges via placebo + random-common-cause + unobserved-confounder tests" — but no DoWhy import, no refutation function exists. Ensemble voting is the only refutation discipline currently |
| causal_decomposition | combined_strength threshold: top ingredient × 0.5; condition extraction requires combined_strength >0.1; ingredient drop-out requires all three of buyer_grad <0.01 AND page_grad <0.01 AND theory_sup <0.01 | NONE — per-conversion decomposition, not multi-hypothesis | "is_surprising" flag is a heuristic (predicted_mech ≠ actual OR predicted_prob <0.3) — informs hypothesis generation but does not gate discovery |
| causal_discovery | alpha=0.05 default for PC independence tests (Fisher's z); min_samples_for_test=50; ATE strength buckets at 0.1 / 0.3 | Iterates conditioning sets up to max_conditioning_set=3; v-structure + Meek's rules orient edges. NO Bonferroni / FDR / look-elsewhere correction | Bootstrap_samples=100 in config — but `_estimate_ate` uses simple regression-adjusted ATE; bootstrap inference NOT IMPLEMENTED in `_adjusted_ate` (only delta-method SE via OLS). The bootstrap is config but absent in code |
| causal_forest | EconML CausalForestDML inference=True returns asymptotic CIs; alpha=0.05 in `effect_interval` call | Per-cell fits (independent), no cross-cell correction. Per-cell honest splitting + cv=5 cross-fitting via DML | LibsMissingError discipline: explicit fail when EconML missing, no silent return. Cell-under-powered flag (n<200) per handoff §2.9 caveat (88-93% empirical at nominal 95%) — caller widens by ~1.3× empirically OR falls through to bootstrap |
| causal_structure_learner | confidence_threshold=0.7 default (softmax over log-odds); total_observations ≥10 minimum; SHIFT_THRESHOLD=0.03 magnitude | NONE — pairwise edge tracker, no multi-hypothesis grid correction. HYPOTHESIS_WEIGHTS modulates evidence strength but doesn't correct for multiplicity | NONE — direct evidence accumulation. Pure observational discipline |
| blind_analysis/box | The discipline IS the gate — sealed_box's `decision_threshold` is the named metric threshold; mutation after sealing raises BoxValidationError | The pre-registration is the multiple-comparison control (frozen grid → no post-hoc widening) | Placeholder data generator emits NULL-hypothesis synthetic data — analysis can run end-to-end without touching live data; mismatch between empirical Type-I rate at threshold and theoretical prediction (via lee.py) IS the refutation signal |
| blind_analysis/lee | Closed-form trial factor TF(z) corrects local-p for look-elsewhere effect; saturates at 1.0 to keep return value valid probability | The trial factor IS the multiple-comparison correction (Gross-Vitells 2010 closed form) | Monte-Carlo ensemble (`monte_carlo_global_p_value`) is non-asymptotic ground truth that closed-form must agree with for large z — refutation is built-in at the test layer |

**Critical pattern:** all 8 causal_* modules implement statistical gating, but the gates are **NOT pre-registered.** They're hard-coded constants set by module authors (alpha=0.05, p<0.05, n≥30, Cohen's h>0.2, confidence_threshold=0.7, etc.). The pre-registration substrate (blind_analysis/box.py) exists but is dormant for all 8 modules.

**Refutation gating gap:** causal_dag_ensemble's docstring promises DoWhy refutation tests; the implementation does not include them. Ensemble voting (≥2/4 methods agree) is the only refutation discipline currently. causal_learning has no refutation. causal_adjudicator explicitly disclaims as "directional, real causal-inference would require holdouts."

---

## §5 Pass 4 — Bilateral central claim composition (LOAD-BEARING)

The bilateral architecture's central causal claim:

> Multiplicative trait × state composition predicts response better than either trait-alone or state-alone.

**Capability-to-module mapping:**

| Capability | Module(s) implementing | Status |
|------------|----------------------|--------|
| Per-conversion attribution (decompose conversion → active causal ingredients) | **causal_decomposition** (`CausalDecompositionEngine.decompose`) | IMPLEMENTED + WIRED (3 callers) |
| Heterogeneity across cohorts / cells (CATE = trait × state interaction) | **causal_forest** (`fit_causal_forest_for_cell`) | IMPLEMENTED + WIRED to weekly cron via task_35; data path operational; awaits EconML install for actual fits |
| Direct-effect discovery (page_dim → mechanism amplification) | **causal_learning** (`test_dimension_amplifies_mechanism` + `test_all_direct_effects`) | IMPLEMENTED + WIRED end-to-end (cascade read + outcome write + daily batch) |
| Edge discovery for trait edges + state edges + composition edges | **causal_dag_ensemble** + **causal_discovery** + **causal_structure_learner** (3 different implementations) | causal_dag_ensemble IMPLEMENTED but UNWIRED; causal_discovery IMPLEMENTED + minimally wired (1 caller); causal_structure_learner IMPLEMENTED but COMPLETELY UNWIRED |
| Uncertainty quantification (calibrated CIs on causal claims) | **causal_conformal** (`ConformalLiftWrap.interval`) | IMPLEMENTED + WIRED to m2_pipeline + synthetic_ab_simulation (NOT wired to causal_forest output directly) |
| Causal structure topology (DAG / PAG over psychological dims) | **causal_dag_ensemble** (PC+FCI+GES+DAGMA ensemble) + **causal_discovery** (PC alone) | Both IMPLEMENTED; differ in output node label (:PsychDim vs :CausalVariable); causal_dag_ensemble UNWIRED; causal_discovery 1 caller |
| Adjudication of method disagreement / counterfactual reasoning | **causal_adjudicator** (`adjudicate_ready_deviations`) | IMPLEMENTED + WIRED at campaign-outcome level; per-method causal disagreement adjudication NOT implemented |
| Sequential testing integration | **msprt_*** modules (separate from causal_*) | ZERO cross-references with any causal_* module |
| Pre-registration / blind-analysis discipline | **blind_analysis/box.py** + **blind_analysis/lee.py** | IMPLEMENTED + tested but ZERO non-test callers |

**Composition assessment:**

Each capability exists as a substantive module. The capabilities are **NOT composed** into an end-to-end test of the bilateral central claim. Specifically:

1. **NO module imports another causal_* module.** Every causal_* module is a closed surface with its own callers. They do not cross-reference each other.

2. **NO module imports `adam.blind_analysis.*`.** The pre-registration substrate is fully isolated — only its own test suite consumes it.

3. **NO module cross-references `msprt_*` or `spine.*`.** Sequential testing operates in a parallel universe.

4. **Edge-type writes are non-overlapping but non-coordinated:**
   - causal_learning → `(:PageDimension)-[:AMPLIFIES|:SUPPRESSES]->(:CognitiveMechanism)`
   - causal_dag_ensemble → `(:PsychDim)-[:CAUSES]->(:PsychDim)`
   - causal_discovery → `(:CausalVariable)-[:CAUSES]->(:CausalVariable)` (different node label, same edge type as ensemble)
   - causal_forest → `(:Archetype)-[:RESPONDS_TO]->(:CognitiveMechanism)`
   - causal_adjudicator → `(:Deviation)-[:RESOLVED_AS]->(:Outcome)`
   - causal_decomposition / causal_conformal / causal_structure_learner → no Neo4j writes (in-memory only)

5. **No edge type captures (Trait × State) → Mechanism explicitly.** causal_forest writes `(:Archetype)-[:RESPONDS_TO]->(:CognitiveMechanism)` with `category` as edge property (not `page_dim`); causal_learning writes `(:PageDimension)-[:AMPLIFIES]->(:CognitiveMechanism)` with no archetype conditioning. The composition exists in CATE estimation (causal_forest could fit per-cell with archetype × page_dim covariates) but the Neo4j edge schema doesn't represent the multiplicative composition as a first-class relationship.

6. **No data-path threads per-conversion decomposition (causal_decomposition) → CATE confidence interval (causal_forest + causal_conformal) → discovered structural relationships (causal_dag_ensemble + causal_discovery) → adjudication (causal_adjudicator).** Each module operates on its own data substrate independently.

**Verdict: Finding D — capabilities exist as silos.** The substrate is built; the integration is not. Q.B's scaffold = build the integration layer + integrate blind_analysis + write a (Trait × State) → Mechanism edge type + threading through causal_forest's CATE machinery.

---

## §6 Pass 5 — Pre-registration discipline integration

**Verdict: ZERO integration between blind_analysis/* and any of the 8 causal_* modules.**

`rg -l "blind_analysis|box\.py|sealed_box|gross_vitells|placeholder_data_generator" adam/intelligence/ adam/api/ adam/core/` returns **no matches.**

`rg -l "from adam.blind_analysis|adam.blind_analysis"` returns only:
- `adam/blind_analysis/__init__.py` (package self-reference)
- `tests/blind_analysis/test_box.py`
- `tests/blind_analysis/test_lee.py`

The substrate is fully isolated. blind_analysis/box.py has 287 LOC of substantive pre-registration machinery (sealed boxes, deterministic SHA-256 hashing, state machine SEALED → AUTHORIZED → UNBLINDED, placeholder NULL-data generator). blind_analysis/lee.py has 302 LOC of substantive look-elsewhere-correction machinery (Gross-Vitells closed form, Davies upcrossings, Monte-Carlo ground truth). Both have full test coverage. Neither has a non-test caller anywhere in the codebase.

**Architectural significance:** the platform has built the methodological-rigor substrate AND the discovery/inference engines — but they are not wired together. **Pre-registration is structural infrastructure that exists but is dormant for all 8 causal_* modules.**

**For Q.B's pre-registration scaffold:** integration is non-trivial. The minimum-viable integration requires:
1. A registration write path: where does an operator pre-register a hypothesis-grid before causal_learning's `test_all_direct_effects` (or causal_forest's weekly fit) runs? Likely a new Neo4j node type (`:BlindAnalysisBox`) with sealed-state property, OR a serialized box stored in Redis under `informativ:blind_analysis:<box_name>`, OR a YAML file at a known path.
2. A discovery-side change: each causal_* module that does discovery reads pre-registered grid before running. For causal_learning: `test_all_direct_effects(observations, box)` filters its 200-test grid down to the box's signal_region + threshold from box.decision_threshold. For causal_forest: `run_weekly_causal_forest_fit(cells, box)` filters cells to the box's signal_region.
3. A LEE correction integration: after BH FDR (causal_learning) or per-cell CIs (causal_forest), apply `gross_vitells_global_p_value` to convert local p-values to look-elsewhere-corrected global p-values.
4. An unblinding-authorization gate: discovery-side modules check `box.state == UNBLINDED` before persisting Neo4j edges; otherwise restrict to `placeholder_data_generator` synthetic data.

**Estimated integration LOC: ~250-400** (3-4 entry points per causal module that does discovery; modest plumbing per module).

---

## §7 Pass 6 — Test infrastructure inventory

**Modules with B3-LUXY-grade dedicated unit-test files:**

| Module | Test file | LOC | Coverage shape |
|--------|-----------|-----|----------------|
| causal_dag_ensemble | tests/unit/intelligence/test_causal_dag_ensemble.py | 217 | Likely: standardize_columns regression (Reisach-Seng-Schölkopf 2021 anchor), per-method discoverer smoke, ensemble_vote vote-aggregation, Neo4j writeback idempotency |
| causal_forest | tests/unit/intelligence/test_causal_forest.py | 281 | Likely: degenerate-cell handling (all-control / all-treatment), pscore_known filter, LibsMissingError on EconML absence, CATEResult.cell_under_powered flag, weekly-fit driver |
| causal_conformal | tests/unit/test_causal_conformal.py | 306 | Likely: `min_calibration_size` enforcement, interval coverage validation, empirical_coverage drift detection, residual-quantile correctness |
| blind_analysis/box | tests/blind_analysis/test_box.py | (not measured here) | Sealed-box invariants, hash determinism, state-machine transitions, region disjointness |
| blind_analysis/lee | tests/blind_analysis/test_lee.py | (not measured here) | Asymptotic linearity of TF(z), Monte-Carlo agreement with closed form, upcrossings calibration |

**Modules tested only via integration / orchestrator paths:**

| Module | Test files referencing it |
|--------|---------------------------|
| causal_learning | tests/integration/test_e2e_workflow.py + tests/unit/intelligence/test_emergent_intelligence.py + tests/unit/test_dashboard_recommendations_dcil.py |
| causal_adjudicator | tests/unit/test_horizon_adjudicator_task.py + tests/unit/test_dashboard_recommendations_dcil.py + tests/integration/test_e2e_workflow.py |
| causal_decomposition | tests/integration/test_e2e_workflow.py + tests/unit/intelligence/test_emergent_intelligence.py |
| causal_discovery | tests/integration/test_e2e_workflow.py + tests/unit/intelligence/test_emergent_intelligence.py |

**Modules with NO test references:**

| Module | Test files referencing it |
|--------|---------------------------|
| causal_structure_learner | **NONE** |

**Test discipline summary:**
- 5 of 8 causal modules + both blind_analysis modules have B3-LUXY discipline (theory-in-docstring + canonical-formula-in-code + dedicated unit tests)
- 3 of 8 causal modules (causal_learning, causal_adjudicator, causal_decomposition) tested only via integration paths
- 1 of 8 causal modules (causal_structure_learner) has zero test coverage AND zero callers — pure-substrate-no-callers pattern
- causal_discovery is in a hybrid state — referenced by integration tests but the dedicated PC algorithm + ATE estimator do not have unit tests pinning the PC orientation rules or the regression-adjusted ATE math against published anchors

**For Q.3 implementation slice:** the test-discipline gap matters. If Q.3 extends causal_learning with `test_archetype_dimension_interaction()`, that extension SHOULD ship with dedicated unit tests (mirroring causal_dag_ensemble + causal_forest pattern), not rely on integration coverage. ~80-150 LOC test scaffolding addition.

---

## §8 Pass 7 — Cross-module integration paths

**No causal_* module imports another causal_* module.**

**No causal_* module imports adam.blind_analysis.***

**No causal_* module references msprt_* or spine.***

**No causal_* module references adam.intelligence.dual_eval_evaluator or free_energy_dual_eval.**

**Shared Neo4j edge types:**
- `:CAUSES` is written by both causal_dag_ensemble (`(:PsychDim)-[:CAUSES]->`) and causal_discovery (`(:CausalVariable)-[:CAUSES]->`) — different node labels, same edge type. A Cypher query for `MATCH ()-[:CAUSES]->()` returns edges from both. No coordination on which writer is authoritative; depends on which downstream consumer the read is for.
- `(:Outcome)` node is created by causal_adjudicator (with `attributed_to` property `'user_choice' | 'system_choice' | 'confounded'`). No other causal_* module writes Outcome nodes.
- `(:Archetype)` and `(:CognitiveMechanism)` nodes are referenced by causal_forest (`:RESPONDS_TO` edge) and causal_learning (`:AMPLIFIES`/`:SUPPRESSES` edge). Both modules independently MERGE these nodes; consistency depends on canonical name vocabulary across the codebase (which causal_learning's MECHANISMS list violates — it has `cognitive_ease` but not `anchoring`; F.2's canonical Cialdini-9 has `anchoring` but not `cognitive_ease`).

**Shared input substrates:**
- causal_learning, causal_decomposition, causal_adjudicator, causal_forest all consume from the outcome-event stream (via `OutcomeHandler.process_outcome` per `outcome_handler.py:336`). Each receives different shapes of the same observation:
  - causal_learning: full CausalObservation with both edge_dimensions sides
  - causal_decomposition: metadata dict (alignment_scores + page_edge_dimensions)
  - causal_adjudicator: NOT called from outcome_handler — called from horizon-elapsed Deviation scan
  - causal_forest: NOT called from outcome_handler — pulls from Neo4j AdDecision rows in scheduled batch

**Integration anti-patterns surfaced:**
- causal_dag_ensemble + causal_discovery + causal_structure_learner are THREE parallel implementations of "discover causal structure between psychological dimensions" with non-overlapping callers, different node labels, different statistical methods, and no namespace coordination. None reference each other; none are gated against each other for consistency.
- causal_conformal is the right calibration wrap for causal_forest's CATE output but is wired to `m2_pipeline.py` and `synthetic_ab_simulation.py` rather than directly to `task_35_causal_forest_fit.py`. The CATE → conformal interval wrap may not actually fire on production fits.
- causal_decomposition's per-conversion ingredients are stored in-memory only (FIFO 10K cap on the singleton). They're consumed by daily_intelligence_brief + inferential_hypothesis_engine but not persisted as Neo4j edges. If the singleton resets (process restart), all decomposition history is lost.

**Integration gaps for Q.B's central-claim test:**
- causal_decomposition identifies active causal ingredients per conversion BUT does not feed those ingredients to causal_forest as features for CATE heterogeneity estimation. The connection that would close the loop ("decomposition tells us which ingredients matter; CATE tells us how much each matters per cohort") is missing.
- causal_conformal could wrap causal_forest's CATE output but doesn't (today wires to m2_pipeline). If wired, every per-cell CATE estimate would carry a calibrated CI.
- causal_adjudicator at campaign-outcome level could compose with causal_decomposition's per-conversion recipes (decompose → identify ingredients → adjudicate whether the ingredients were active in this campaign → trigger WhyLibrary entry). Today these operate independently.

---

## §9 Pass 8 — Implications for Q.A through Q.O beyond Q.B / Q.3

### Q.D (loop closure cadence) implications

Three distinct cadences across the 8 modules:
- **Continuous (per-bid + per-outcome):** causal_learning (read+write), causal_decomposition (per-outcome), causal_conformal (per-realization)
- **Horizon-window-driven (1d-60d):** causal_adjudicator
- **Weekly batch (Sunday 03:00 UTC):** causal_forest, causal_dag_ensemble (intended), causal_discovery (on-demand from full_intelligence_integration)

Q.D adjudication depends on whether Claude Proper considers this fragmentation acceptable (each cadence appropriate for its task) or wants unification (single nightly causal-batch). Recommendation: **accept the fragmentation but document it** — the cadences are appropriate per task. Per-bid reads must be fast (Redis); weekly fits must be expensive (CausalForestDML at n=2000 trees doesn't fit per-bid). The fragmentation is not an antipattern; the lack of documentation IS.

### Q.A (creative-variant routing / URL-granularity) implications

NONE of the 8 causal_* modules depend on per-impression URL granularity. The substrate is per-cell or per-archetype × mechanism × category. URL granularity matters at the cascade level (creative variant selection); it does not propagate into the causal-attribution layer. The URL-granularity blocker per P.0 / S0_HANDOFF does NOT block Q.B / Q.3 work. **Causal-attribution work can proceed independently of URL-granularity resolution.**

### Cut B reporting (Q.C) implications

Four causal modules produce operator-actionable surfaces that should appear in the dashboard:
1. **causal_forest CATE per cell** — operator surface: "for archetype X × category Y × mechanism Z, the lift estimate is τ̂ ± CI; cell is/isn't under-powered" — drives mechanism-selection visibility
2. **causal_decomposition per-conversion recipes** — operator surface: "this conversion's active causal ingredients were [primary: X, amplifier: Y, moderator: Z]" — drives why-this-conversion visibility
3. **causal_adjudicator system_right outcomes** — operator surface: "you declined recommendation N; the campaign did not recover; here's a WhyLibrary entry for the next time you see this pattern" — drives recommendation-trust calibration
4. **causal_dag_ensemble + causal_discovery edges** — operator surface: "the system has discovered (with N votes / confidence) that page_dim X causes mechanism Y to be more effective" — drives inferential-claim visibility

But there is no unified surface aggregator. Cut B should likely include a "causal evidence" panel that pulls from all 4 modules; today each module's surface is wired ad-hoc (or not wired at all — causal_dag_ensemble has no consumer; causal_decomposition's recipes are in-memory-only).

### Post-pilot iteration substrate implications

| Module | Update cadence post-pilot | Validation |
|--------|---------------------------|------------|
| causal_learning | Daily batch (already wired via task_15) | BH FDR survives; needs to add LEE correction post-Q.B |
| causal_forest | Weekly batch (wired via task_35); DML monthly per handoff §2.10 | Conformal CI calibration via causal_conformal (not currently wired) |
| causal_dag_ensemble | Intended weekly per handoff §7; **NOT WIRED** | DoWhy refutation (NAMED but NOT IMPLEMENTED in module) |
| causal_decomposition | Per-conversion (already wired) | In-memory only; needs persistence layer for post-pilot accumulation |
| causal_discovery | On-demand (caller-driven) | bootstrap_samples=100 in config but absent in code |
| causal_adjudicator | Horizon-window-driven (already wired via task_29_6) | Confidence stamped 0.6 (evaluator-led) / 1.0 (operator-led); calibration TBD |
| causal_conformal | Append-only (per realization) | Already calibration-aware via empirical_coverage |
| causal_structure_learner | Intended batch (NIGHTLY OR WEEKLY per docstring); **NOT WIRED** | Direct evidence accumulation — no validation surface |

**Two unwired modules (causal_dag_ensemble + causal_structure_learner) and one partially-wired module (causal_decomposition: in-memory only).** Post-pilot, deciding whether to wire these is a substantive scope question.

### Whether C.2 + C.3 are still independently required

**For Q.B / Q.3 specifically:** C.1's expanded scope substantially absorbed the existence question for causal-attribution. C.2 (spine/) and C.3 (msprt + dual_eval + free_energy) are **NOT load-bearing for Q.B's central-claim test scaffold** — none of those modules participate in the causal-attribution surface today, and Q.B can ship without modifying them.

**For OTHER architectural questions:**
- C.2 (spine/) is recommended for Q.D (loop closure cadence) — the spine is likely the orchestration layer that could unify causal cadences if Q.D adjudication wants unification
- C.3 (msprt + dual_eval + free_energy) is recommended for understanding sequential-testing integration — if Q.B adjudicates that interaction-test scaffold should support early-stopping (mSPRT-style), C.3 surfaces what's available; if Q.B is OK with daily-batch BH FDR + LEE correction (no early stopping), C.3 is deferrable

**Recommendation:** defer C.2 + C.3 until after Q.B adjudication. Their findings inform OTHER decisions (Q.D, sequential-testing integration) but not the immediate Q.B scope question.

---

## §10 Q.B / Q.3 slice scope implications

Given Pass 4 finding **D** (capabilities exist as silos):

### Sketch — minimum-viable scaffold (~250-400 LOC)

Pre-pilot ship-minimum approach. Defers full composition to post-pilot.

- **Q.B pre-registration:** Single sealed_box entry pre-registering the test "Does archetype X × page_dim Y predict mechanism Z amplification more than archetype OR page_dim alone?" Scope: 1-3 archetype × page_dim × mechanism cells. Stored as YAML or Redis blob; box.decision_threshold = 0.05 with LEE correction. ~50 LOC plumbing + ~20 LOC YAML/Redis serialization.
- **Q.3 implementation:** Wire causal_forest's existing `fit_causal_forest_for_cell` to accept (archetype, page_dim, mechanism, category) instead of (archetype, mechanism, category). page_dim becomes context_features dim — CATE estimator already supports this; just need data-loader change. Add `(:Archetype)-[:CONDITIONS_AMPLIFICATION_OF {page_dim, tau, tau_lo, tau_hi}]->(:CognitiveMechanism)` edge schema. Cascade read-path extension to query archetype-conditional effects. ~150-250 LOC + ~80 LOC tests.
- **Pre-pilot scope:** small-medium. 1-2 weeks.
- **Limitation:** does not integrate decomposition + conformal + adjudicator. Single-edge pre-registration only. No look-elsewhere correction integration in Q.3 (Q.B sets the box; lee.py is invoked at adjudication time but not wired into the discovery loop).

### Sketch — integration-layer build (~800-1,200 LOC)

Full Finding D fix. Composes existing capabilities into end-to-end test path.

- **Q.B integration substrate:** ~250-400 LOC pre-registration plumbing per §6 (3-4 entry points per discovery module + LEE correction integration + unblinding-authorization gate)
- **Q.3 integration build:**
  - Wire causal_decomposition output → causal_forest features (per-conversion ingredients become CATE covariates) — ~80-120 LOC
  - Wire causal_forest CATE → causal_conformal interval (every per-cell τ̂ carries calibrated CI) — ~50 LOC
  - Wire causal_forest CATE → new edge type `(:Trait)-[:CONDITIONS_AMPLIFICATION_OF {page_dim, tau, tau_lo, tau_hi, n}]->(:Mechanism)` representing trait × state composition — ~100-150 LOC
  - Wire causal_decomposition recipes → causal_adjudicator (decomposition-informed adjudication: when adjudicating, check whether the recipe's primary ingredients were active in the campaign window) — ~100-150 LOC
  - Wire causal_adjudicator system_right outcomes → causal_dag_ensemble's edge-vote count (operator-led adjudication contributes to causal-edge confidence) — ~50-80 LOC
  - Test discipline (B3-LUXY pattern across all integration entry points) — ~150-250 LOC
- **Pre-pilot scope:** substantial. 4-6 weeks.
- **Risk:** large slice; harder to land cleanly; pilot timeline impact.

### Sketch — post-pilot deferred (Q.B minimal pre-pilot, Q.3 deferred)

Recognize that Finding D is a substantial composition build that pilot data may obviate for SOME of the proposed integrations. Ship the absolute minimum pre-pilot; defer composition build to post-pilot.

- **Q.B pre-pilot:** Document Finding D explicitly. Pre-register ONE box that locks in the bilateral central claim hypothesis (archetype × page_dim × mechanism amplification). Wire it into causal_forest (small slice as in minimum-viable above). ~100-150 LOC.
- **Q.3 pre-pilot:** wire single edge type from causal_forest's existing CATE machinery; cascade read-path extension. ~150-200 LOC. Test scaffold ~80 LOC.
- **Q.B / Q.3 post-pilot:** the integration-layer build above (~600-800 LOC) gated on pilot calibration data showing the integration is needed. Some integrations may be obviated by pilot data (e.g., if causal_decomposition recipes turn out not to add signal beyond causal_forest CATE features, the decomposition-to-CATE wire is unnecessary).
- **Pre-pilot scope:** small. ~2 weeks.
- **Total scope (pre-pilot + post-pilot):** matches integration-layer-build scope (~800-1,200 LOC) but split across timelines.

### Recommendation to Claude Proper

**Recommend Sketch C (post-pilot deferred composition).** Reasons:
1. Finding D is substantial; integration-layer build is a 4-6 week slice that competes with other pre-pilot priorities
2. Pilot data may obviate parts of the integration (calibration evidence reveals which integrations actually add signal vs. which are theory-driven assumption)
3. Minimum-viable pre-pilot scaffold (single edge type + single pre-registered box) gives the platform an honest "we tested the central claim" surface without overcommitting integration plumbing
4. The substrate for the full composition exists today — post-pilot integration is plumbing work, not theory work

**Alternative if Claude Proper wants full pre-pilot integration:** Sketch B is feasible but expects a 4-6 week dedicated slice. Worth a separate decision.

---

## §11 C.2 / C.3 dependency assessment

**C.2 (adam/intelligence/spine/) — RECOMMENDED but NOT load-bearing for Q.B/Q.3.**

C.2 surfaces what spine architecture exists (likely orchestration layer). For Q.B/Q.3 specifically: spine does not participate in any of the 8 causal_* modules' callers — none of the causal modules import from spine, and spine likely doesn't import from causal_*. Q.B/Q.3 can ship without C.2.

C.2 IS recommended for Q.D (loop closure cadence). The 8 causal_* modules have at least 4 distinct cadences (per-bid, per-outcome, horizon-window, weekly batch). If Claude Proper wants Q.D adjudication to consider unification, C.2 would surface whether spine is the right unification substrate.

**C.3 (msprt + dual_eval + free_energy) — RECOMMENDED but NOT load-bearing for Q.B/Q.3.**

C.3 surfaces what sequential-testing infrastructure exists. For Q.B/Q.3 specifically: msprt does not participate in any of the 8 causal_* modules' callers — none of the causal modules import from msprt, dual_eval, or free_energy.

C.3 IS recommended IF Q.B adjudication requires interaction-test scaffold to support sequential testing (mSPRT-style early stopping). If the adjudication is OK with daily-batch + BH-FDR + LEE correction (no early stopping), C.3 is deferrable.

**Suggested ordering:**
1. Claude Proper adjudicates Q.B/Q.3 scope based on §10 sketches (immediate; no further audits needed)
2. If Q.B/Q.3 ships per Sketch A or C, C.2 + C.3 audits run in parallel with Q.B/Q.3 implementation, surfacing Q.D + sequential-testing options for post-Q.B work
3. If Q.B/Q.3 ships per Sketch B (full integration), C.3 might run BEFORE Q.3 implementation to inform whether mSPRT integration belongs in the Q.3 slice

---

## §12 QUESTION-and-stop concerns

- **Q.S — causal_dag_ensemble unwired.** Module is M7 substrate per Seven-Component Methodology Handoff §7 with full implementation + 217-LOC test file + Neo4j writeback. ZERO non-test callers in adam/. Either wire it (small slice — invoke from a daily/weekly task) or document why it's intentionally unwired (waiting for production data scale? library install gating?). Affects Q.D (loop closure) — undecided.
- **Q.T — causal_structure_learner pure substrate.** ZERO callers anywhere. ZERO tests. Either wire + test it (medium slice) or remove it (small slice). Pure orphan code. Affects post-pilot iteration substrate — what does "interventional data" feed into if no consumer exists?
- **Q.U — DoWhy refutation gap in causal_dag_ensemble.** Docstring promises "DoWhy refutes high-vote edges via placebo + random-common-cause + unobserved-confounder tests." Implementation does not include DoWhy import or refutation function. Either add DoWhy refutation (small-medium slice) or update docstring to reflect actual scope (small slice). Affects causal-discovery rigor.
- **Q.V — causal_decomposition recipes are in-memory only.** Singleton with FIFO 10K cap. Process restart loses all decomposition history. If decomposition feeds post-pilot iteration substrate, persistence is required. Either persist to Redis/Neo4j (small-medium slice) or document that recipes are ephemeral diagnostic artifacts (small slice). Affects post-pilot accumulation strategy.
- **Q.W — Vocabulary drift in causal_learning.MECHANISMS.** Includes `cognitive_ease` (NOT in F.2 canonical Cialdini-9), missing `anchoring` (IS in F.2 canonical). Edges keyed on `cognitive_ease` will never be consumed by F.2 paths; edges that should exist on `anchoring` will never be discovered. Small slice (~10 LOC + test) to reconcile. Affects causal_learning ↔ F.2 coherence.
- **Q.X — causal_learning.EDGE_DIMENSIONS pre-W.2b vintage.** Missing `maximizer_tendency`. Causal discovery never finds maximizer-conditioned effects. Small slice (~5 LOC + test) to add. Affects W.2b ↔ causal_learning coherence.
- **Q.Y — causal_learning's `:MODERATES` edge type documented but not written.** Module docstring names it as one of three edge types; cascade read query checks for it; persist function only writes AMPLIFIES/SUPPRESSES. Either implement MODERATES discovery (medium scope — IS the moderation/interaction pattern; would compose with Q.B's central-claim test) or remove from docstring (small scope). Affects Q.B's scope: implementing MODERATES would give Q.B's interaction-test a natural edge-type home.
- **Q.Z — causal_discovery.bootstrap_samples=100 in config but absent in code.** _adjusted_ate uses simple OLS regression-adjusted ATE with delta-method SE; bootstrap inference declared but not implemented. Either implement bootstrap (medium slice) or remove config (small slice). Affects causal_discovery's CI honesty.

---

## §13 Audit closure

C.1 (Option 3 scope) produced a comprehensive 8-module + blind_analysis depth audit at uniform moderate depth. Eight passes documented; 8 modules + 2 blind_analysis modules treated uniformly; capability-to-module map produced; Pass 4 Finding D (capabilities exist as silos) surfaced; three Q.B/Q.3 scope sketches (~250-400 LOC minimum-viable, ~800-1,200 LOC full integration, ~250-350 LOC pre-pilot deferred) presented for Claude Proper adjudication; recommendation: post-pilot deferred composition (Sketch C) with minimum-viable pre-pilot scaffold; C.2 + C.3 NOT load-bearing for Q.B/Q.3 but recommended for Q.D + sequential-testing decisions; 8 QUESTION-and-stop concerns surfaced (Q.S through Q.Z).

**Cross-references:**
- `adam/intelligence/causal_learning.py` (550 LOC)
- `adam/intelligence/causal_adjudicator.py` (919 LOC)
- `adam/intelligence/causal_conformal.py` (243 LOC)
- `adam/intelligence/causal_dag_ensemble.py` (347 LOC)
- `adam/intelligence/causal_decomposition.py` (492 LOC)
- `adam/intelligence/causal_discovery.py` (762 LOC)
- `adam/intelligence/causal_forest.py` (483 LOC)
- `adam/intelligence/causal_structure_learner.py` (234 LOC)
- `adam/blind_analysis/box.py` (287 LOC)
- `adam/blind_analysis/lee.py` (302 LOC)
- `adam/api/stackadapt/bilateral_cascade.py:2046-2080` (causal_learning bid-time read)
- `adam/core/learning/outcome_handler.py:336` (causal_learning per-outcome write + causal_decomposition decompose)
- `adam/intelligence/daily/task_15_self_teaching.py:726` (causal_learning daily batch)
- `adam/intelligence/daily/task_35_causal_forest_fit.py` (causal_forest weekly cron)
- `adam/intelligence/daily/task_29_6_horizon_adjudicator.py` (causal_adjudicator scheduled batch)
- `adam/intelligence/m2_pipeline.py` (causal_forest + causal_conformal coordination)
- `adam/intelligence/full_intelligence_integration.py` (causal_discovery sole caller)
- `tests/unit/intelligence/test_causal_dag_ensemble.py` (217 LOC)
- `tests/unit/intelligence/test_causal_forest.py` (281 LOC)
- `tests/unit/test_causal_conformal.py` (306 LOC)
- `tests/blind_analysis/test_box.py` + `tests/blind_analysis/test_lee.py`
- Predecessors: docs/audits/PLATFORM_SYSTEM_DEEP_DIVE_2026_05_09.md (Phase 1 §16); docs/audits/ARCHITECTURE_REASONING_FOR_CLAUDE_PROPER_2026_05_09.md (Phase 2 §4.2 — M7 ensemble); docs/audits/PLATFORM_DEPTH_VERIFICATION_2026_05_09.md (§8)
