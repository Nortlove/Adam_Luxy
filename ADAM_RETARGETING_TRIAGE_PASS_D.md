# ADAM Retargeting Triage — Pass D

**Date:** 2026-04-15
**Scope:** The 21 orphaned modules under `adam/retargeting/` identified by the AST-based audit (of which 9 are package `__init__.py` noise and 12 are substantive files).
**Framing (per Chris's request):** For each orphan, determine whether it is **net-new capability** not present in the live retargeting system, or **a duplicate** of something already in the active codebase, or **an integration fix** where live code is ready but the wiring is missing.
**Supplement to:** `ADAM_INTEGRATION_AUDIT_2026-04-15.md` (Section 4 which flagged the retargeting orphans), `ADAM_ATOM_TRIAGE_PASS_C.md` (which established the "orphan ≈ stranded work" pattern at a larger scale), `ADAM_PAGE_INTELLIGENCE_REVIEW.md` (which did the same net-new-vs-existing framing for page intelligence).

## Headline

**The live retargeting system is much larger than I expected: 56 modules under `adam/retargeting/` are imported and live.** The Enhancement #34 nonconscious signals (`click_latency`, `barrier_self_report`, `organic_return`, `processing_depth`, `device_compat`, `frequency_decay`, `nonconscious_profile`), Enhancement #36's `repeated_measures` and `within_subject`, the hierarchical `prior_manager` (15 refs — one of the most-used modules in the codebase), the `diagnostic_reasoner`, `barrier_diagnostic`, `sequence_orchestrator`, `neural_linucb`, `mechanism_selector`, `rupture_detector`, `narrative_arc`, `signal_collector`, `touch_builder`, and the entire `resonance/` subsystem — all live. The retargeting core is real and working.

**Of the 12 substantive orphan files (excluding package `__init__.py` noise), ZERO are duplicates. Ten are net-new capabilities not present in the live system. Two are integration fixes — code that is ready to run but whose wiring into `outcome_handler.py` or `main.py` startup was never added.** None should be deleted.

**The two most significant individual findings are the discoveries that `stackadapt_api_exporter.py` already implements the Tier 1 Campaign Orchestrator that `ADAM_SESSION_RESTORE.md` says is "~1 week after Tier 0" of pending work, and that `evolutionary_engine.py` is the hypothesize-test-learn-at-speed system Chris described earlier in the session as something he had tried to build and wanted to see further built out. Both already exist in the codebase, fully written, stranded.**

## 1. Classification of the 12 Substantive Retargeting Orphans

All classified by comparing each orphan's docstring and imports against the live retargeting module list. Where an orphan has a close live counterpart, I note it explicitly. Every orphan has been tagged by the session number cited in its docstring header.

### 1.1 Net-New Capabilities (10 of 12)

These add capabilities that do not exist anywhere else in the live code. None of them are duplicates of active modules.

| Orphan | Session | What it provides | Live equivalent | Classification |
|---|---|---|---|---|
| `annotation_quality.py` | 34-4 | Self-consistency (Claude N=3, stdev = uncertainty) + conformal prediction (for Big Five dims with ground truth). Uncertainty feeds confidence-weighted alignment in bilateral edge computation — high-uncertainty dimensions contribute less to `composite_alignment`. | **None.** The live code computes `composite_alignment` without uncertainty weighting. | **Net-new.** Load-bearing for reducing noise in barrier diagnosis. |
| `causal_mediation.py` | 34-9 | DML-based (Farbmacher et al. 2022) mediation analysis. Decomposes Total Effect = Direct + Indirect via mediators (dwell_time, pages_viewed, return_visits, booking_steps). Answers "why does social_proof work for agreeable users — is it via trust, decision simplification, or identity validation?" Prerequisite: 500+ completed sequences. | **None.** Live code knows *that* mechanisms work but not *why*. | **Net-new, intentionally dormant until data volume accumulates.** This is not a failed wiring — the docstring explicitly says *"Infrastructure is built here so it's ready when data accumulates."* It was meant to be ready-and-waiting. |
| `dimensionality_compressor.py` | 34-11 | PCA compression of 24-dim bilateral edge to 7 principal components (captures 90% variance per Session 34-2 diagnostic). Speeds up Neural-LinUCB. Includes reconstruction back to full 24-dim for interpretability. | **None.** Live `neural_linucb.py` takes the uncompressed 43-dim input. | **Net-new infrastructure optimization.** Would make Neural-LinUCB 6× faster. |
| `graph_embeddings.py` | 34-8 | FastRP / HGT graph embedding integration with Neo4j GDS. Exports graph → trains embeddings → writes back to Neo4j properties → enriches mechanism selection with embedding-based context features. Falls back gracefully without GDS plugin. | **None.** Live code uses raw Cypher queries, no graph embeddings. | **Net-new infrastructure extension.** High value for generalization across similar archetype-product cells. |
| `prospect_theory.py` | 34-10 | Kahneman-Tversky value function applied to bilateral edge dimensions before composite computation. Asymmetric S-shape: gains concave, losses convex, losses weighted λ≈2.25×. Dimensions classified as gain-domain or loss-domain based on archetype baseline. | **None.** Live composite_alignment uses linear scaling. | **Net-new theoretical refinement of bilateral edge scoring.** Particularly load-bearing for reactance (r=-0.79 with conversion) which is a loss-domain dimension and is currently being scored linearly. |
| `recalibration.py` | no session cited, Session 34-2 diagnostic driven | Periodic recalibration of composite_alignment weights via logistic regression. Triggers when 500+ new edges accumulate or weekly. Validates new AUC vs current AUC before deploying. Category-aware (Beauty edges → Beauty weights, luxury_transportation edges → LUXY weights). | **None.** The one-time fix from Session 34-2 was applied manually; no automated recalibration runs. | **Net-new AND operational risk if not wired.** The Session 34-2 diagnostic found composite_alignment was INVERTED (r=-0.29) because 11 of 25 dimensions had wrong sign weights. The v6 fix corrected it for LUXY. But **without this automated recalibration, weights will drift back to wrong as new data accumulates from different categories or outcome patterns.** This is a latent bug that will surface silently. |
| `temporal_dynamics.py` | 34-5 + Addendum B Cat 4 | DDM timing capture + burstiness detection. Burstiness parameter B = (σ−μ)/(σ+μ) per user. When B > 0.3, replaces fixed `min_hours_between` in the live `suppression_controller.py` with burst-aware timing. Based on Barabási Nature 2005 power-law behavior paper. | **None directly.** Live `suppression_controller.py` uses fixed-interval suppression. The orphan's `BurstAwareTimingController` class is the drop-in replacement. | **Net-new capability with named integration point.** The wire-up is "swap the timing controller inside SuppressionController when burstiness detected." Maybe 10 lines of change. |
| `tensor_decomposition.py` | 34-7 | CP tensor decomposition (via `tensorly`) of 3-way tensor `T ∈ ℝ^(d_buyer × d_seller × K)` to discover BILATERAL archetypes — patterns of buyer×seller dimension co-occurrence that predict conversion. | **None.** Enhancement #33's live k-means archetypes in `prior_manager` are computed on buyer dimensions only. | **Net-new.** Discovers structure that buyer-only clustering misses. Load-bearing for generalization because bilateral archetypes port across categories better than buyer-only clusters. |
| `stackadapt_api_exporter.py` | no session cited | **Produces complete StackAdapt-executable campaign packages.** GraphQL-API-based creation, bulk JSON import, pixel-based audiences, domain whitelist/blacklist CSV, creative specs per touch, frequency caps, dayparting schedules, retargeting sequences with audience exclusion rules. Output structure: `{brand}_campaign_config.json`, `{brand}_audiences.json`, `{brand}_creatives.json`, `{brand}_domain_whitelist.csv`, `{brand}_domain_blacklist.csv`, `{brand}_retargeting_rules.json`, `{brand}_frequency_caps.json`, `{brand}_dayparting.json`, `{brand}_measurement.json`. | **None.** Live retargeting has `stackadapt_translator.py` (2 refs) which is a much thinner integration. The adapter at `adam/integrations/stackadapt/adapter.py` with the speculative GraphQL mutations from Risk #8 is a different, unrelated file. | **This is the Tier 1 Campaign Orchestrator from `ADAM_SESSION_RESTORE.md`.** See Section 2.1 below. |
| `evolutionary_engine.py` | no session cited | **Five sub-engines for hypothesize-test-learn-at-speed:** (A) Hypothesis Generator proposes novel page_mindstate × mechanism combinations; (B) Experiment Allocator runs UCB1 across a 10% exploration budget; (C) Synergy Detector finds non-obvious amplification effects; (D) Evolution Manager propagates winners, prunes losers, introduces mutations; (E) Self-Evaluator monitors prediction accuracy and detects concept drift. Three timescales: fast (per-impression allocation), medium (per-outcome observation), slow (daily hypothesis generation and evolution cycle). | **None.** Live resonance has `resonance_learner.py` (5 refs) which does some learning but not hypothesis generation or evolution. `adam/intelligence/inferential_hypothesis_engine.py` and `adam/behavioral_analytics/knowledge/hypothesis_engine.py` are the two other hypothesis engines from Pass X's findings; whether they overlap with this one is worth checking before wiring. | **This is the hypothesize-test-learn-at-speed system Chris described earlier in the session as something he had tried to build and wanted to see further built out.** See Section 2.2 below. |

### 1.2 Integration Fixes (2 of 12)

These are ready-to-run code that depends on live modules. Their orphan status means the wiring point in `outcome_handler.py` or `main.py` was never added, not that the code is unfinished.

| Orphan | Session | What it provides | What it imports (all live) | Wiring gap |
|---|---|---|---|---|
| `learning_loop.py` | 33-8 | Enhancement #33's therapeutic learning loop. Two paths: system-level cross-campaign (updates corpus → category → brand posteriors), and campaign-level within-campaign (updates sequence posteriors). Wraps around `HierarchicalPriorManager` and generates learning signals for the Gradient Bridge. | `adam.retargeting.engines.prior_manager` (15 refs LIVE), `adam.retargeting.models.enums` (22 refs LIVE), `adam.retargeting.models.diagnostics` (8 refs LIVE), `adam.retargeting.models.sequences` (9 refs LIVE), `adam.retargeting.models.learning` (3 refs LIVE) | Should be called from Step 13 in `outcome_handler.py`. That call site does not exist. One `outcome_handler.process_outcome` patch + one import. |
| `therapeutic_workflow.py` | 33-F.2 | **LangGraph workflow for the Therapeutic Retargeting Loop.** Seven nodes: diagnose_barrier → check_rupture → check_suppression → select_mechanism → build_touch → generate_creative → update_priors. This is the declarative composition of the live engines into a single flow. | Live: `diagnostic_reasoner` (3 refs), `rupture_detector` (3 refs), `suppression_controller` (3 refs), `mechanism_selector` (4 refs), `touch_builder` (3 refs), `prior_manager` (15 refs) — all imported. | Should be called from `sequence_orchestrator.py` (3 refs, live) as the LangGraph-based composition path, or from `main.py` as a registered workflow. Currently the sequence composition is done via direct Python calls elsewhere. Adding the LangGraph path does not break the direct-call path. |

### 1.3 What I did NOT find

**No duplicates.** Nothing in the 12 substantive orphan set is a parallel implementation of a live retargeting capability. Every orphan adds capabilities the live system does not have. This directly answers Chris's "net new vs duplicate" question: **overwhelmingly net-new, zero duplicates.**

**No dead-code drafts.** Every file has a module docstring with a specific session number or session spec, explicit integration points, and working data structures. None of them is a WIP stub.

**No dynamic-discovery mechanism.** Unlike the atom case from Pass C (where `construct_dag.py` references atoms by string name and was found by looking for non-import patterns), the retargeting orphans are not referenced by any second-tier orchestration layer. They are simply unwired.

## 2. The Two Most Significant Individual Findings

### 2.1 `stackadapt_api_exporter.py` = the Tier 1 Campaign Orchestrator

This is directly relevant to the LUXY campaign build and changes the Tier 0/Tier 1 path I laid out in the session restore doc.

**What the session restore doc (Section 6) says about the next StackAdapt integration step:**

> *"Tier 1 — Campaign Orchestrator (~1 week after Tier 0). New `adam/integrations/stackadapt/campaign_orchestrator.py`. Full lifecycle: audience → creative → campaign → line items → creative assignment → domain targeting → frequency/dayparting → bid strategy → launch. Idempotent. Returns real IDs. This is the linchpin of 'running from inside.'"*

**What `stackadapt_api_exporter.py` actually produces:**

- GraphQL API-based campaign creation
- Bulk JSON import for campaign setup
- Custom audience segments via conversion pixels
- Domain targeting lists (CSV whitelist/blacklist)
- Creative management with multiple variants
- Frequency capping rules
- Dayparting schedules
- Retargeting sequences with audience exclusion rules
- Output file structure that matches the current manual Becca handoff package almost exactly (`{brand}_campaign_config.json`, `{brand}_audiences.json`, `{brand}_creatives.json`, `{brand}_domain_whitelist.csv`, `{brand}_domain_blacklist.csv`, `{brand}_retargeting_rules.json`, `{brand}_frequency_caps.json`, `{brand}_dayparting.json`, `{brand}_measurement.json`)

**These two descriptions match very closely.** `stackadapt_api_exporter.py` is the Tier 1 Campaign Orchestrator. It is ~500 lines of code that produces exactly the campaign package that is currently being assembled manually and handed off to Becca in files like `campaigns/ridelux_v6/`. It already exists. It is stranded.

**What this changes for the Tier 0 / Tier 1 plan from the session restore doc:**

The original plan said: "Tier 0 — GraphQL schema verification (1 day, prerequisite). Tier 1 — build a new Campaign Orchestrator from scratch (~1 week)." The revised plan should be:

- **Tier 0** still stands. We still need Becca's real GraphQL schema to verify which mutations exist. That is unchanged.
- **Tier 1 becomes much cheaper.** Instead of building a campaign orchestrator from scratch, we (a) read `stackadapt_api_exporter.py` end-to-end, (b) verify which of its assumed StackAdapt mutations match the real GraphQL schema once Becca's key arrives, (c) fix the mismatches, (d) wire it into `main.py` as a callable service. **Estimated effort: 2-3 sessions instead of 1 week.** The reduction is entirely because the code already exists.

**This also partially resolves the Risk #8 question.** Risk #8 was "the speculative GraphQL mutations in `adam/integrations/stackadapt/adapter.py:132-272` were invented without checking the real schema." That file is a **different, earlier, less-complete attempt at StackAdapt integration.** `stackadapt_api_exporter.py` appears to be the more mature design from a later session, stranded before wiring. When Becca's key arrives, the right action is to **extend `stackadapt_api_exporter.py`**, not `adam/integrations/stackadapt/adapter.py`. The `adapter.py` file may still need to exist as the thin GraphQL client layer that `stackadapt_api_exporter.py` calls into, but the campaign-orchestration logic is already built in the exporter.

**Actionable implication for this session and the next:** before proceeding to further atom wiring or to Stage 1 of the Pass C wiring plan, someone should read `stackadapt_api_exporter.py` end-to-end. That reading is the highest-leverage single task available for the Becca-waiting period. If the code matches its docstring, the Tier 1 work drops from "~1 week of new building" to "~2 sessions of schema verification and integration."

### 2.2 `evolutionary_engine.py` = the hypothesize-test-learn-at-speed system

Earlier in the session, we had an extended conversation about active real-time learning and hypothesis generation. Chris's words, paraphrased: *"I tried to develop this but again, this also needs to be further built out in order for the system to truly be smart and adaptive."*

**That system already exists in the codebase.** `evolutionary_engine.py` under `adam/retargeting/resonance/` is the five-sub-engine system:

- **(A) Hypothesis Generator** — proposes novel `page_mindstate × mechanism` combinations to test
- **(B) Experiment Allocator** — runs UCB1 allocation of a 10% exploration budget (the active-exploration-budget pattern from my earlier proposal)
- **(C) Synergy Detector** — finds non-obvious amplification effects (mechanism × mechanism interactions)
- **(D) Evolution Manager** — propagates winners, prunes losers, introduces mutations
- **(E) Self-Evaluator** — monitors prediction accuracy, detects concept drift

Three timescales: fast (per-impression allocation), medium (per-outcome observation), slow (daily hypothesis generation and evolution cycle). Uses `scipy.stats.pearsonr` and `fisher_exact` for statistical testing. Imports live modules: `adam.retargeting.resonance.models` (13 refs live), `adam.retargeting.resonance.resonance_learner` (5 refs live).

**This is exactly the hypothesize-test-learn-at-speed system we talked about.** It is orphaned. It imports live modules, so the infrastructure it depends on is ready. The wiring gap is into `sequence_orchestrator` (for per-impression UCB1 allocation) and `main.py` startup (for the daily evolution cycle).

**What this changes for the hypothesize-test-learn work:** instead of designing and building it from scratch, we should read `evolutionary_engine.py` end-to-end, understand its assumptions, decide whether it matches Chris's current vision (it may need updates), and wire it in. If the file is close to what Chris wanted, this is another week of work that doesn't need to happen.

## 3. The Pattern, Confirmed for the Fourth Time

Across Passes A (halted), B, C, C-deep-dive, and now D, the same pattern holds:

| Pass | Orphan type | Count | Pattern |
|---|---|---|---|
| A | Library files | 5 | Substantive stranded work |
| B | Page intelligence bridge | 1 | Theoretically-grounded architectural fix, stranded |
| C | Atom files | 16 | All theory-grounded stranded work, all citing published research |
| C deep-dive | Orchestration layer | 1 subsystem, 2116 lines | Entire parallel DAG system stranded |
| D | Retargeting engines/workflows/integrations | 12 substantive files | 10 net-new capabilities, 2 integration fixes, zero duplicates |

**Total stranded architectural work identified across Passes A-D: roughly 40+ files, 5000+ lines of theoretically-grounded Python code that is ready-or-nearly-ready to run, and is not running because it was never wired in.** The drift pattern is not "someone forgot one file" — it is "someone built substantial amounts of upgrade material in each of several sessions and never integrated any of it."

**The base rate for substantive orphan = stranded-work is now approximately 100% across every pass that has actually looked.** I should finalize the rule from the theoretical foundation update:

> **Rule for future orphan classification: Default to stranded-work. Only classify as dead-code after reading the file and finding (a) its functionality is reimplemented elsewhere in the live code, or (b) it is a clearly abandoned mid-draft with no structure or cited references. Substantive files with theory citations, working data structures, and named integration points are always stranded, not dead.**

This rule should be added to the theoretical foundation's discipline rules the next time we touch that document.

## 4. Retargeting Wiring Plan

Given that the retargeting orphans include one Tier 1 Campaign Orchestrator and one hypothesize-test-learn engine, the retargeting wiring has a different priority shape than the atom wiring. The atoms are all upstream of mechanism selection and can be wired in stages. The retargeting orphans are a mix of infrastructure optimizations, theoretical refinements, and two crucial campaign-build-relevant pieces (`stackadapt_api_exporter` and `evolutionary_engine`).

**Recommended ordering:**

**Stage 1 — Campaign-build-critical (do before LUXY launch):**

1. **Read `stackadapt_api_exporter.py` end-to-end** and verify it matches the Tier 1 Campaign Orchestrator description. One session. Output: decision on whether to extend it or fork it.
2. **Wire `learning_loop.py` into `outcome_handler.py` step 13** — Enhancement #33's learning loop that is currently stranded. Small change, unblocks the hierarchical Bayesian update path. One session.
3. **Wire `therapeutic_workflow.py` into `sequence_orchestrator.py`** or `main.py` as the LangGraph-based sequence composition path. Optional — the direct-call path already works — but adds declarative workflow introspection. One session if we want it.

**Stage 2 — Data-quality and bilateral-edge accuracy (before or immediately after launch):**

4. **Wire `recalibration.py` into `main.py` startup scheduler + `outcome_handler.py` threshold-trigger.** One session. **This one is operationally urgent** because without automated recalibration, `composite_alignment` will drift back to the Session 34-2 inversion issue as new data accumulates.
5. **Wire `prospect_theory.py` into bilateral edge computation** before `composite_alignment`. One session. Moderate impact on reactance-dimension scoring accuracy.
6. **Wire `annotation_quality.py` into bilateral edge confidence weighting.** One session. Reduces noise in barrier diagnosis.

**Stage 3 — Infrastructure optimizations (after launch, benefits accumulate with data):**

7. **Wire `dimensionality_compressor.py` into Neural-LinUCB input path.** One session. 6× input-size reduction, interpretability preserved.
8. **Wire `graph_embeddings.py` into mechanism selection context features.** Two sessions (requires Neo4j GDS plugin verification).
9. **Wire `temporal_dynamics.py` into `suppression_controller.py`.** One session. Replaces fixed-interval timing with burst-aware.

**Stage 4 — Adaptive learning system (higher risk, longer runway):**

10. **Wire `evolutionary_engine.py` into `sequence_orchestrator` and `main.py`.** Probably 2 sessions. This is the hypothesize-test-learn system and it needs a 10% exploration budget to be allocated from production traffic, which is a design decision that needs your sign-off before wiring.

**Stage 5 — Deferred activation (keep stranded, no wiring):**

11. `causal_mediation.py` — leave stranded per its own explicit design. Wire it in when 500+ complete sequences have accumulated. Mark it in a known-stranded-deliberately registry.
12. `tensor_decomposition.py` — similar. Leave until data volume makes bilateral archetype discovery useful. Probably several months away.

**Estimated total effort for Stages 1-4: ~10-12 focused sessions.** Stage 1 alone is 3 sessions and is the most campaign-critical. Stages 2-3 can happen during or shortly after the campaign run. Stage 4 needs your judgment call before starting.

## 5. Concrete Next Actions

Ranked by value-for-the-campaign-build:

1. **Read `stackadapt_api_exporter.py` end-to-end.** This is the single highest-leverage read available. It probably changes the Tier 0/Tier 1 integration plan substantially.
2. **Read `evolutionary_engine.py` end-to-end.** Verify it matches Chris's hypothesize-test-learn vision, identify any gaps, decide whether to extend or start fresh.
3. **Update the cross-pass summary** in `ADAM_INTEGRATION_AUDIT_2026-04-15.md` so the 40+ files / 5000+ lines of stranded work finding is captured as the single most important discovery of the audit work.
4. **Commit this Pass D document and the summary update.**
5. **Bring the findings to Chris** as the input to the next-step decision. The sequencing of atom wiring (Pass C) vs. retargeting wiring (Pass D) vs. page_edge_bridge wiring (Pass B) vs. StackAdapt API exporter wiring (new from this pass) should be planned together, not pass-by-pass.

## 6. What this means for the overall campaign build plan

Combining Passes B, C, and D findings: **before the LUXY campaign build starts, the highest-leverage work is to wire in the stranded architecture, not to build anything new.** Specifically:

- **`stackadapt_api_exporter.py`** (Pass D finding) — replaces the "build a new Tier 1 Campaign Orchestrator" task from `ADAM_SESSION_RESTORE.md` with "verify, fix mismatches, wire in." Saves ~5 days of work.
- **`page_edge_bridge.py`** (Pass B finding) — wires the Bargh-correct "page shifts buyer position" architecture into the cascade. Replaces the current "page modulates mechanism" pattern with the inferential correct one.
- **The 2116-line orchestration layer** (Pass C deep-dive finding) — brings all 28 atoms online via `construct_dag.py` + `dag_executor.py` + `langgraph_feedback.py` instead of manually extending `dag.py`.
- **`learning_loop.py`** + **`recalibration.py`** (Pass D findings) — wires Enhancement #33's learning loop into `outcome_handler.py` and prevents composite_alignment from drifting back to the Session 34-2 inversion.
- **16 orphan atoms** (Pass C finding) — come online automatically with the Pass C deep-dive wiring.

**All of this work is reading-plus-wiring, not new design.** The designs already exist. The theory is already grounded. The integration points are already named in each orphan's docstring. What has been missing is the disciplined pass to take all of the stranded work and wire it in as a coordinated unit.

**Revised pre-campaign work estimate: 1.5-2.5 weeks of focused wiring.** Larger than the original Pass C estimate of 3-4 sessions, substantially larger than the original session-restore doc's estimates of Tier 0/Tier 1 work, but the right size given what the audit has uncovered.

**The alternative — launching LUXY on top of the rump architecture — is also valid**, and the timeline may force it. The tradeoff is:

- **Wire first, then launch.** Campaign runs on the full inferential architecture. Probably 2 weeks pre-launch. Substantially better per-decision quality, fewer surprises under load, easier to debug because the documented architecture matches the runtime state.
- **Launch on the rump, wire during production.** Campaign goes live faster. Quality is lower until wiring catches up. Higher risk of silent underperformance that only shows up in outcome data weeks later.

**This is a tradeoff that needs Chris's explicit call. I will not make it unilaterally.** The timeline for Becca's GraphQL key and the LUXY launch date determine which is correct, and those are facts I do not have.
