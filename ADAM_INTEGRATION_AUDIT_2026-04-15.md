# ADAM Integration Audit — 2026-04-15

**Purpose:** Ground-truth map of what is wired, what is orphaned, and what duplicates what in the ADAM codebase. Produced before a period of build work on the full LUXY campaign, to prevent the creation of the sixteenth orphan module.

**Method:** Scanned all 857 Python files under `adam/` for `from adam.*` and `import adam.*` references. Built a reachability graph: for each module, counted how many other files in `adam/` (plus `scripts/`, `tests/`, `bin/`) import it. Modules with zero importers are classified as orphaned. Caveats: the script catches top-level and nested grep-visible imports but misses dynamic imports via `importlib`, plugin discovery, and string-based module loading. The orphan count is therefore a lower bound on deadness — anything reported here as orphaned is almost certainly not reached by static import chains, though it might still be invoked via a dynamic mechanism I have not traced.

## 1. Headline Numbers

| Metric | Count |
|---|---|
| Total `.py` files in `adam/` | **857** |
| Reached by at least one other file (live) | **587** (68.5%) |
| Orphaned (zero importers after scripts/tests rescue) | **224** (26.1%) |
| Rescued by test/script imports only (live via non-adam callers) | **46** (5.4%) |

**One-line summary:** roughly one in four files in `adam/` is not imported by anything else in the codebase. That is not a normal ratio for a mature system — it indicates accumulated parallel implementations and incomplete refactors.

Top orphan areas:

| Area | Orphaned modules |
|---|---|
| `adam.intelligence` | 36 |
| `adam.retargeting` | 21 |
| `adam.atoms` | 20 |
| `adam.corpus` | 15 |
| `adam.platform` | 11 |
| `adam.api` | 10 |
| `adam.identity` | 9 |
| `adam.integrations` | 8 |
| `adam.demo` | 7 |
| `adam.core` | 5 |

## 2. The Single Most Important Finding

**The DAG has 14 atoms, not 30+. Sixteen atom files exist in the filesystem but are not imported anywhere.**

`adam/atoms/dag.py:31-45` imports exactly these 14 atom classes:

`UserState`, `PersonalityExpression`, `RegulatoryFocus`, `ConstrualLevel`, `MechanismActivation`, `MessageFraming`, `AdSelection`, `ChannelSelection`, `ReviewIntelligence`, `CognitiveLoad`, `DecisionEntropy`, `InformationAsymmetry`, `PredictiveError`, `AmbiguityAttitude`.

The sixteen atom files that exist under `adam/atoms/core/` but are imported by nothing:

`autonomy_reactance`, `brand_personality`, `coherence_optimization`, `cooperative_framing`, `interoceptive_style`, `mimetic_desire_atom`, `motivational_conflict`, `narrative_identity`, `persuasion_pharmacology`, `query_order`, `regret_anticipation`, `relationship_intelligence`, `signal_credibility`, `strategic_awareness`, `strategic_timing`, `temporal_self`.

**Three possibilities**, each with different implications:

1. **They are unfinished work** — written as drafts, never completed, never wired. Delete or finish.
2. **They are dynamically registered via a plugin mechanism I did not find** — possible but unlikely, since the DAG imports them statically. Verify.
3. **They are legacy atoms superseded by the current 14** — retire them with a tombstone.

**Cross-check against `memory/MEMORY.md`**, which explicitly claims *"30+ Atom of Thought (AoT) psychological reasoning modules in DAG."* The memory is wrong — or at best, partially true at the filesystem level and false at the runtime level. This is exactly the pattern the theoretical foundation warns about: claims that look impressive from a file count but do not survive contact with the import graph.

**Action required:** for each of the 16 orphan atoms, one of: delete (confirmed dead), wire into the DAG (confirmed useful), or tombstone (kept for reference but explicitly marked unused). This should be one focused decision pass before any new atom is written.

## 3. Duplicate Clusters Resolved

Ten duplicate pairs or clusters were visible from directory/filename analysis. The reachability data tells us which member is actually used:

### 3.1 Unambiguously-kill candidates (one member is orphan)

| Duplicate | Keep | Delete |
|---|---|---|
| `unified_product_intelligence` vs `unified_intelligence_service` | `unified_intelligence_service` (13 refs) | `unified_product_intelligence` (0 refs) |
| `unified_review_aggregator` vs `full_intelligence_integration` | `full_intelligence_integration` (3 refs) | `unified_review_aggregator` (0 refs) |
| `adam.coldstart` vs `adam.cold_start` | `adam.cold_start` (live) | `adam.coldstart` — only contains `unified_learning.py` and a 2.9GB priors JSON. Delete the Python file; keep the JSON if still loaded elsewhere (needs confirmation). |

### 3.2 Both-live, need human judgment

| Duplicate | Refs A | Refs B | What it likely means |
|---|---|---|---|
| `adam.intelligence.emergence_engine` vs `adam.learning.emergence_engine` | 2 | 1 | Both live but small. Likely one is a refactor of the other; consolidate to the more-used version. |
| `adam.meta_learner.thompson` vs `adam.cold_start.thompson.sampler` | 5 | 12 | **Probably NOT a true duplicate.** Different roles: meta-learner Thompson picks execution paths; cold-start Thompson picks mechanisms per archetype. Verify before consolidating. |
| `adam.intelligence.psychological_frameworks` vs `...frameworks_extended` | 1 | 1 | Both barely used. Classic "build then extend, never delete." Consolidate. |
| `adam.intelligence.review_orchestrator` vs `review_intelligence.orchestrator` | 4 | 1 | The flat one is more used. The sub-package version is probably a stalled refactor. Retire the sub-package version. |
| `adam.intelligence.unified_psychological_intelligence` vs `unified_construct_integration` | 2 | 4 | Both live, overlapping names. Need to read both to decide whether they do different things or the same thing. |
| `adam.intelligence.inferential_hypothesis_engine` vs `adam.behavioral_analytics.knowledge.hypothesis_engine` | 4 | 6 | **This is the "two hypothesis engines" drift I warned about earlier.** Both actively used. Neither dominates. They probably do overlapping work. Consolidation is required but needs a design pass to decide which frame to keep — the "inferential" one (aligned with the foundation's correlation-vs-inference thesis) or the "knowledge / behavioral" one (probably a Bayesian network over behavioral analytics constructs). My default recommendation is to read both and keep whichever is more Pinker-compliant (productive rule system with frame + slots), but this is a design decision Chris should make. |

### 3.3 Multi-version clusters

**Five `unified_*` modules in `adam.intelligence/`:**

| Module | Refs | Status |
|---|---|---|
| `unified_intelligence_service` | **13** | Dominant — keep as the primary |
| `unified_construct_integration` | 4 | Live, probably distinct purpose |
| `unified_psychological_intelligence` | 2 | Live, probably overlapping with one of the above |
| `unified_product_intelligence` | **0** | Orphan — delete |
| `unified_review_aggregator` | **0** | Orphan — delete |

**Five `deep_*` modules in `adam.intelligence/`:**

| Module | Refs | Status |
|---|---|---|
| `deep_product_analyzer` | 3 | Live |
| `deep_review_analyzer` | 3 | Live |
| `deep_archetype_detection` | 2 | Live |
| `deep_page_scoring` | 1 | Marginally live — worth checking |
| `deep_psycholinguistic_framework` | **0** | Orphan — delete |

**Four `learning/` directories:**

| Directory | Live? |
|---|---|
| `adam/core/learning/` | Live — hub for outcome handler, theory learner, signal router |
| `adam/learning/` | Partial — has orphans (`emergence_engine` nearly orphaned, `__init__` orphaned) |
| `adam/intelligence/learning/` | Orphan at package level — single file `psychological_learning_integration.py` |
| `adam/cold_start/learning/` | Partial — `gradient_bridge.py` orphaned |

**Conclusion:** `adam/core/learning/` is the canonical learning location. The other three are fragments of refactors-in-progress. They should either be merged into `adam/core/learning/` or deleted.

## 4. Retargeting — Enhancement #33 and #36 are Partially Orphaned

Memory asserts both enhancements are "COMPLETE." The reachability data says otherwise.

**21 orphaned files in `adam.retargeting/`:**

```
adam.retargeting.engines.annotation_quality
adam.retargeting.engines.causal_mediation
adam.retargeting.engines.dimensionality_compressor
adam.retargeting.engines.graph_embeddings
adam.retargeting.engines.learning_loop
adam.retargeting.engines.prospect_theory
adam.retargeting.engines.recalibration
adam.retargeting.engines.temporal_dynamics
adam.retargeting.engines.tensor_decomposition
adam.retargeting.events
adam.retargeting.integrations
adam.retargeting.integrations.stackadapt_api_exporter
adam.retargeting.models
adam.retargeting.prompts
adam.retargeting.resonance
adam.retargeting.resonance.evolutionary_engine
adam.retargeting.schema.queries
adam.retargeting.workflows
adam.retargeting.workflows.therapeutic_workflow
```

**The most concerning items on that list:**

- **`retargeting.integrations.stackadapt_api_exporter`** — an existing (but orphaned) StackAdapt integration module. Before we do any StackAdapt Tier 0/Tier 1 integration work, we should read this file and find out whether it is the basis to extend or the thing to delete. The current `adam/integrations/stackadapt/adapter.py` (with the speculative mutations I flagged in Risk #8) is probably a parallel implementation of what was already being attempted here.
- **`retargeting.workflows.therapeutic_workflow`** — the Enhancement #33 therapeutic sequence engine. If it is orphaned, the "therapeutic retargeting" work described in memory was never wired in.
- **`retargeting.engines.learning_loop`** — if the retargeting engine's own learning loop is orphaned, the "repeated measures / within-subject design" from Enhancement #36 is probably not running.
- **`retargeting.engines.causal_mediation`, `prospect_theory`, `tensor_decomposition`, `dimensionality_compressor`** — these read like theoretically-sound building blocks that were built, then never integrated.

**Action required:** before extending the retargeting system, audit what in `adam.retargeting/` is actually live. The ratio of live-to-orphan in this subtree is probably the worst in the codebase, and the claims in memory about Enhancement #33 and #36 completeness need to be rewritten to reflect what actually runs.

## 5. Intelligence Layer Orphans — The Full List

Thirty-six orphaned modules under `adam.intelligence/` after scripts/tests rescue:

**Likely dead, can be deleted:**

- `unified_product_intelligence.py` — superseded by `unified_intelligence_service`
- `unified_review_aggregator.py` — superseded by `full_intelligence_integration`
- `deep_psycholinguistic_framework.py` — one of the five deep_* that never caught on
- `empirical_psychology_framework.py` — probably superseded by `psychological_frameworks`
- `expanded_type_integration.py` — likely legacy from a type-system refactor
- `langgraph_alignment_integration.py` — a LangGraph extension that appears unused
- `historical_data_reprocessor.py` — offline reprocessing tool, may be intentional
- `claude_summarizer.py` — Claude summarization helper, may be intentional
- `corpus_builder.py` — corpus building tool
- `asin_review_matcher.py` — matching utility
- `daily.task_16_page_gradients` — unwired daily task
- `daily.task_17_copy_evolution` — unwired daily task
- `page_edge_bridge.py` — **particularly interesting** (see Section 6)

**Entire orphaned sub-packages:**

- `scrapers/` (the whole package __init__ is orphaned; several files inside are live but the top-level never gets imported as a package) — `oxylabs_ai_client`, `social_scraper`, `unified_scraper`, `brand_positioning_analyzer` all orphaned individually
- `review_intelligence/extractors/` — `google_local_extractor`, `twitter_mental_health_extractor`, `yelp_extractor`, and `base_extractor` all orphaned
- `relationship/` — `graph_builder`, `models`, `patterns` all orphaned; the whole subtree is dead
- `knowledge_graph/` package-level orphaned; `review_learnings_embedder` orphaned individually
- `pattern_discovery/` package-level orphaned
- `outcome_simulation/` package-level orphaned — though `theory_based_simulator.py` inside may be live via a different import chain
- `sources/` package-level orphaned
- `storage/` package-level orphaned
- `models/` package-level orphaned

**Interpretation:** The `adam/intelligence/` layer has the exact drift pattern the theoretical foundation predicted. Multiple parallel implementations of overlapping functionality, written in different sessions, never retired, with only a small core actively wired into the decision path.

## 6. `page_edge_bridge.py` and the Page Intelligence Gap

This deserves its own section because it is directly relevant to what we want to build next.

**`adam/intelligence/page_edge_bridge.py` is orphaned.** It exists, it is not imported by anything. The name strongly suggests it was designed to bridge page-level signals into the bilateral edge schema — exactly the work I proposed during the Becca-waiting period.

Before writing a new page intelligence extractor, **the first step must be to read `page_edge_bridge.py` and figure out whether it is the basis to extend, the thing to delete, or the evidence that someone already thought through the architecture of this problem and abandoned the implementation.**

Related orphans in the same area that should be read in the same pass:

- `adam/intelligence/page_intelligence.py` — live (not in the orphan list, has at least one importer)
- `adam/intelligence/page_crawl_scheduler.py` — live
- `adam/intelligence/page_similarity_index.py` — live
- `adam/intelligence/page_conditioned_query.py` — live
- `adam/intelligence/page_edge_scoring.py` — live
- `adam/intelligence/page_gradient_fields.py` — live
- `adam/intelligence/deep_page_scoring.py` — marginal (1 ref)
- `adam/intelligence/page_edge_bridge.py` — **ORPHAN**

**So we have SEVEN live page-* modules and one orphaned one.** The live ones are presumably fragments of work on page intelligence that was actually wired in. Before building new, I need to understand what the current live chain does — which of these seven is the primary, what they collectively produce, and where `page_edge_bridge.py` was supposed to fit. This is a focused-read task of maybe 8-10 files, probably doable in one session.

## 7. Hypothesis Engines, Revisited

Both hypothesis engines are live:

- `adam/intelligence/inferential_hypothesis_engine.py` — 4 references
- `adam/behavioral_analytics/knowledge/hypothesis_engine.py` — 6 references

Neither dominates. They do overlapping work. They were almost certainly written in different sessions under different framings. Consolidating them is a design decision that should be made before any new hypothesis-generation work is added, because adding a third implementation is exactly the failure pattern the theoretical foundation warns against.

**Recommendation for consolidation:** read both, keep whichever one is closer to the Pinker dual-mechanism architecture (productive rule system with frame-plus-slot templates), retire the other. The "inferential" name suggests that file is the one aligned with the theoretical foundation, but that is a guess from the name alone — verify by reading.

## 8. Cold-Start Location Sprawl

Three cold-start directories exist:

| Directory | Status |
|---|---|
| `adam/cold_start/` | **Canonical.** Has `service.py`, `thompson/sampler.py` (12 refs), `archetypes/detector.py`, proper Pydantic models, etc. |
| `adam/coldstart/` | **Legacy.** Only contains `__init__.py`, `unified_learning.py`, and a 2.9GB `complete_coldstart_priors.json`. The `.py` files are orphans. The JSON file may still be loaded by a separate path (the learned priors loader) — needs verification. |
| `adam/user/cold_start/` | Partial. Has `__pycache__` so it has been compiled. Contents unknown without further investigation. |

**Action required:** confirm `adam/coldstart/unified_learning.py` has nothing importing it (it is in the orphan list, so confirmed), decide fate of the 2.9GB priors JSON (move if still loaded; delete if not), delete the `adam/coldstart/` Python code. Investigate `adam/user/cold_start/` in a focused pass.

## 9. Actionable Consolidation List

Ordered by effort-to-impact ratio, lowest risk first:

### Tier 0 — Deletions safe to do immediately (low risk, removes noise)

1. Delete `adam/intelligence/unified_product_intelligence.py` (0 refs, orphan)
2. Delete `adam/intelligence/unified_review_aggregator.py` (0 refs, orphan)
3. Delete `adam/intelligence/deep_psycholinguistic_framework.py` (0 refs, orphan)
4. Delete `adam/intelligence/empirical_psychology_framework.py` (0 refs, orphan, likely superseded)
5. Delete `adam/intelligence/expanded_type_integration.py` (0 refs, orphan)
6. Delete `adam/intelligence/langgraph_alignment_integration.py` (0 refs, orphan)
7. Delete `adam/intelligence/daily/task_16_page_gradients.py` and `task_17_copy_evolution.py` (both orphaned daily tasks)
8. Delete the entire `adam/intelligence/relationship/graph_builder.py`, `models.py`, `patterns.py` if the relationship subtree is confirmed dead
9. Delete `adam/coldstart/unified_learning.py` and `__init__.py` (confirmed orphans, superseded by `adam/cold_start/`)
10. Delete or mark as test-only: `adam/intelligence/claude_summarizer.py`, `corpus_builder.py`, `asin_review_matcher.py`, `historical_data_reprocessor.py` — verify each is not a CLI tool before deleting

**Estimated time: one focused session.** All of these are safe because they are confirmed zero-import and the tests are passing without them being loaded. The risk is only that one of them is reached dynamically in a way grep cannot see, so each deletion should be followed by a quick test run to verify nothing breaks.

### Tier 1 — Decisions that need a read-first pass (medium risk, needs judgment)

11. **The 16 orphaned atoms.** For each, one of: delete, wire into DAG, tombstone. Requires reading the atom's docstring and deciding whether the construct it represents is load-bearing for ADAM's reasoning chain. This is where the foundation's construct taxonomy should be consulted — if an atom represents a construct the foundation claims is essential (e.g., `regret_anticipation`, `mimetic_desire`, `temporal_self`), it should probably be wired in, not deleted.
12. **The two hypothesis engines.** Read both. Keep the Pinker-compliant one. Retire the other.
13. **`page_edge_bridge.py` and the seven live page-* modules.** Read all eight. Understand what the current page intelligence pathway actually does. Decide whether to extend it or replace it before writing new page intelligence code.
14. **The 21 retargeting orphans.** Audit Enhancement #33 and #36 claims against reality. The `therapeutic_workflow`, `learning_loop`, and `stackadapt_api_exporter` orphans in particular need human decisions.

**Estimated time: two to three focused sessions.**

### Tier 2 — Architectural consolidation (higher risk, needs design work)

15. **Merge `adam/learning/`, `adam/intelligence/learning/`, `adam/cold_start/learning/` fragments into `adam/core/learning/`.** The canonical learning location is established; the fragments should converge on it. This is a non-trivial refactor because call sites in the fragments need to be redirected.
16. **Consolidate the five `unified_*` intelligence modules** — the three live ones — into either one module or a package with clear per-file responsibilities. Three live "unified" modules with overlapping names is confusing for future reads.
17. **Resolve the two-Thompson question.** `meta_learner.thompson` and `cold_start.thompson.sampler` may legitimately be different, but this needs to be verified and documented. If they are the same thing in two places, consolidate.

**Estimated time: one focused session per item.**

## 10. What This Means for "Building the Entire Campaign"

The user's stated next step is to build the entire LUXY campaign from inside ADAM once Becca's GraphQL key arrives. The findings in this audit have direct implications:

1. **Do not add new atoms before resolving the 16 orphan atoms.** The campaign build will involve creative generation, mechanism selection, and psychological reasoning. Every one of those steps consumes the atom DAG. Building against a DAG that is half-implemented at the file-system level but fully-implemented at the runtime level is confusing and will cause future sessions to misread the system's actual capabilities.

2. **Do not build new page intelligence before reading `page_edge_bridge.py` and the seven live page-* modules.** The campaign will need page-level priming signals for publisher inventory targeting. There is already a substantial amount of page intelligence code. Building a ninth page intelligence module when eight already exist is the exact failure pattern the foundation warns against.

3. **Do not build new StackAdapt integration before reading `retargeting/integrations/stackadapt_api_exporter.py`.** Risk #8 in the earlier audit flagged that `adam/integrations/stackadapt/adapter.py` contains speculative GraphQL mutations that were never verified against the real schema. The existence of an orphaned `stackadapt_api_exporter` in the retargeting layer suggests there was a prior attempt at this work that was abandoned. Whichever path we extend, we should understand both before touching code.

4. **Do not add a new hypothesis engine.** Use the existing two (consolidated) or neither (if what we need is theory-learner-driven rather than hypothesis-engine-driven, which is arguably more Pinker-correct anyway).

5. **The theoretical foundation's claim that "L3 bilateral edges override L1/L2 when available" assumes the cascade actually runs and the edges are populated.** The cascade code is live (`bilateral_cascade.py` is reached by the stackadapt service). But the warm-start pathway audit — "does ADAM develop memoized shortcuts for high-frequency cases?" — from the Dawkins/Pinker discussion has not been done, and should be part of the campaign build's preparation, because if memory is never accumulating per-user the inferential architecture is not what it claims to be.

## 11. The Prioritized Sequence I Recommend Next

Given that we want to build the campaign and also want to fix the issues this audit found, the honest sequence is:

**Pass 1 — Safe deletions (one session).** Tier 0 above. Removes 10+ confirmed-dead files. Low risk, reduces noise. Clears the ground before building.

**Pass 2 — Read the page pipeline (one session).** Read the eight page-* files. Produce a short supplemental note to this audit explaining what the live page intelligence pathway actually does. Decide whether to extend it or replace it.

**Pass 3 — Read the retargeting orphans (one session, possibly two).** The 21 orphans in `adam.retargeting/` are a serious gap between memory claims and reality. Read `stackadapt_api_exporter`, `therapeutic_workflow`, and `learning_loop` at minimum. Produce a short note on Enhancement #33/#36 actual completeness.

**Pass 4 — Atom triage (one session).** For each of the 16 orphan atoms, a delete/wire/tombstone decision. This is the one that will improve the theoretical foundation's claims the most — it will either validate "30+ atoms" by wiring the orphans in, or correct the claim to reflect the actual 14.

**Pass 5 — Build the campaign.** With the ground cleared, the existing code understood, and the major gaps named, the build itself is less likely to create the sixteenth orphan.

Estimated total time for Passes 1-4: roughly one week of focused sessions. The campaign build (Pass 5) then proceeds with an honest picture of what exists and what needs to be new.

## 12. What I Did Not Do in This Pass

- Read individual module contents for more than a handful of files. The audit is based on the import graph, not on understanding what each module actually does.
- Analyze dynamic import chains (importlib, plugin systems, entry points). Anything reached dynamically will appear orphaned to this audit. Follow-up passes should confirm specific orphans against dynamic registries if present.
- Verify whether daily-task orphans in `adam/intelligence/daily/` are registered via the scheduler. If the scheduler uses a registry pattern, some of these may be live via a mechanism the grep missed.
- Audit tests/ for orphans. The 46 "rescued by tests" files may themselves be dead — imported only by tests that are never run. A tests-reachability pass would be informative but is out of scope here.
- Check whether orphaned data files (JSON, pickle, CSV) are still referenced. Only Python files were audited.
- Verify git blame / last-touched dates on orphan files. Old orphans are likely dead; recently-touched orphans may be work-in-progress.

This audit is a starting point for consolidation work, not the final word. Further passes should refine the orphan classification against these gaps.
