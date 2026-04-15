# ADAM Page Intelligence Review (Pass B)

**Date:** 2026-04-15
**Scope:** The eight `page_*` modules in `adam/intelligence/`, their import wiring, and the architectural status of the live page intelligence pathway.
**Supplement to:** `ADAM_INTEGRATION_AUDIT_2026-04-15.md` (specifically Section 6, which flagged `page_edge_bridge.py` as orphan + directly relevant to the upcoming page intelligence build).

## Executive Summary

**Headline:** The page intelligence pathway in ADAM is substantial, live, and correctly architected — *except for one specific gap*. Seven of the eight page-* modules are live and composed into a working pipeline. The eighth, `page_edge_bridge.py`, is orphaned but represents exactly the architectural fix the Bargh frame demands and is not reimplemented anywhere else.

**Conclusion:** **Do not build a new page intelligence system.** The existing pathway does ~90% of what is needed — crawling, profiling, Redis caching, similarity indexing, evidence querying, gradient computation. The missing 10% is a specific wiring change: `page_edge_bridge.compute_page_edge_shift()` needs to be called by the bilateral cascade so that the buyer's position in edge-dimension space is *shifted* by the page's priming effect *before* mechanism scoring, rather than the current pattern of scoring mechanisms first and multiplying by a page modulation factor afterward. This is a small code change that closes a specific theoretical gap, not a greenfield build.

**The correct next action for page intelligence is to resurrect `page_edge_bridge.py` and wire it into `bilateral_cascade.py`,** which changes the architecture from "page modulates mechanism" (correlational) to "page shifts buyer position, then mechanisms are scored against the shifted position" (inferential). The orphaned file contains a theory-grounded shift matrix already; the work is wiring and verification, not design.

## 1. The Live Page Intelligence Pathway

### 1.1 Entry points and call graph

| Module | Importers | Role |
|---|---|---|
| `page_intelligence.py` | **22** (main.py via crawl scheduler, bilateral_cascade, stackadapt service, universal router, ctv_intelligence, domain_taxonomy, impression_state_resolver, realtime_decision_engine, url_intelligence, 5 daily tasks, several scripts, a test) | The hub. Contains `PagePsychologicalProfile`, `PageInventoryTracker`, `PageProfiler`, `PageIntelligenceCache`, `PageCrawlOrchestrator`, `profile_page_content()`, domain/URL-pattern/full-page three-tier cache. Redis-backed. This IS the page intelligence system. |
| `page_crawl_scheduler.py` | **4** (main.py, outcome_handler, prediction_engine, one test) | Background crawler. Bi-daily windows at 6 AM ET / 6 PM ET. Per-domain rate limiting, robots.txt compliance, exponential backoff. Three crawl passes: NLP markers → DOM structure → deep LLM profiling (top 500). Priority queue for conversion-triggered deep crawls. |
| `page_similarity_index.py` | **3** (crawl scheduler, prediction engine, one test) | Cosine similarity on 20-dim edge space. When a converting page is scored, finds K nearest pages for bid-boost whitelisting. Implements the active discovery loop: `conversion → crawl → score → find_similar → bid-boost → more conversions`. |
| `page_conditioned_query.py` | **1** (`bilateral_cascade.py`) | "Trilateral evidence engine." Queries the 6.7M bilateral edges for conversions where the buyer was in a psychological state similar to what the page creates. Filters on 3-5 signature dimensions where the page deviates most from neutral, with TTL-cached results per `(signature_hash, category)`. |
| `page_edge_scoring.py` | **7** (ctv_intelligence, daily.base, impression_state_resolver, page_intelligence, url_intelligence, 2 scripts) | "Full-width 20-dimension extraction." Scores pages directly on all 20 edge dimensions via three tiers: graph priors (from bilateral edges) → full-width text extraction → NDF fallback. Replaces the old 7-dim NDF bottleneck. |
| `page_gradient_fields.py` | **4** (outcome_handler, causal_decomposition, daily.task_16, one test) | Page-side equivalent of buyer-side gradient fields. Computes `∂P(conversion)/∂(page_dimension)` per `(mechanism, barrier)` cell via logistic regression on ≥50 observations. Tells `PlacementOptimizer` which page dimensions amplify which mechanism-barrier combinations. |
| `deep_page_scoring.py` | **1** (page_intelligence) | Ten enhancement techniques for page scoring: negation-aware dependency scoring, sentence-transformer semantic NDF, collocation disambiguation, prospect theory frame detection, psychological arc extraction, discourse relation scanning, Claude structured LLM profiling, etc. Feeds results back into `PagePsychologicalProfile`. |
| `page_edge_bridge.py` | **0** | **ORPHAN. See Section 2.** |

**Observation from the call graph:** the pathway has both the upstream infrastructure (crawl scheduler, profiler, cache) *and* the downstream consumers (bilateral cascade, outcome handler, prediction engine, causal decomposition). It is not a half-built system — it is end-to-end. `outcome_handler.py` specifically imports both `page_crawl_scheduler` (to trigger conversion-driven priority crawls) and `page_gradient_fields` (to update the gradient learning from outcomes). The learning loop for page intelligence is wired.

### 1.2 What the live pathway actually does at decision time

Reading the module docstrings and imports end to end, this is the sequence:

1. **At app startup**, `main.py` loads the `page_crawl_scheduler`, which initializes the crawl background task. The scheduler reads from `PageInventoryTracker` (populated by bid requests over time) and queues pages by impression volume, staleness, drift velocity, and confidence.

2. **Continuously in the background**, the crawl scheduler fetches pages in bi-daily windows, runs three passes (NLP markers → DOM → deep LLM for the top 500), produces a `PagePsychologicalProfile`, and caches it in Redis keyed by domain, URL-pattern, and full URL.

3. **At bid time (<50ms)**, the `bilateral_cascade.py` receives a decision request with a page URL or context. It looks up the page profile from the three-tier cache (`PageIntelligenceCache`), then:
   - Calls `page_conditioned_query` to find bilateral edges where the buyer was in a similar psychological state — this is the "trilateral evidence" lookup.
   - Receives a `PageConditionedEvidence` result telling it what mechanisms actually converted when buyers were in this kind of state.
   - Computes mechanism scores, **then multiplies by a page modulation factor derived from the page profile**. (This is the step `page_edge_bridge` was written to replace.)
   - Returns creative intelligence to the decision router.

4. **After the outcome arrives via webhook**, the `outcome_handler` updates `page_gradient_fields` with the observation and triggers a priority crawl of similar pages via `page_similarity_index`. The learning loop closes.

**This is a well-architected inferential page intelligence pathway.** The vast majority of the work I was going to propose for the page-build phase is already built and running. The active discovery loop (convert → crawl similar → bid-boost) is real. The trilateral evidence query is real. The gradient learning is real. The only thing missing is the one specific theoretical fix in `page_edge_bridge.py`.

## 2. The `page_edge_bridge.py` Gap

### 2.1 What the module does and why it matters

The module's own docstring states the problem and the fix explicitly. Quoting:

> *"Currently, the bilateral cascade computes mechanism scores from edge dimensions (the 20-dim alignment between buyer and product), then AFTERWARDS applies page modulation as a multiplier. **This is wrong.** The page doesn't just modify mechanisms — it shifts the BUYER'S POSITION in the 20-dimensional psychological space BEFORE they encounter the ad."*

And then:

> *"A financial anxiety article doesn't just 'open loss_aversion channel' — it repositions the reader along multiple edge dimensions:*
>
> - *regulatory_fit: shifts toward prevention (reader primed for safety)*
> - *persuasion_susceptibility: increases (anxiety makes people more persuadable)*
> - *autonomy_reactance: decreases (anxious people seek guidance)*
> - *loss_aversion_intensity: increases (threat-primed reader weighs losses 3x)*
> - *social_proof_sensitivity: increases (uncertain reader looks to peers)*
> - *cognitive_load_tolerance: decreases (anxiety consumes bandwidth)*
> - *temporal_discounting: shifts to immediate (threat feels urgent)*
> - *decision_entropy: increases (anxiety creates decision paralysis)*"

**This is the Bargh-correct move at the architectural level.** In the foundation doc's vocabulary: the page is not a modifier applied to a mechanism score; the page is an environmental prime that activates goal structures which reposition the buyer in psychological space before any mechanism evaluation happens. Scoring mechanisms first and then multiplying by a "page factor" treats the page as a correction to an already-computed answer. Repositioning the buyer and then scoring mechanisms against the shifted position treats the page as a *cause* of the buyer's current psychological state.

The difference is the difference between correlational ad tech and inferential ad tech, applied to the specific question of how page context should affect mechanism selection.

### 2.2 What `page_edge_bridge.py` actually contains

The file is substantial and theory-grounded:

- **`_SHIFT_MATRIX`** — a list of `(page_ndf_dimension, edge_dimension, weight, direction)` tuples. Each entry is derived from a specific published theoretical framework cited in the docstring: Regulatory Focus Theory (Higgins), Construal Level Theory (Trope & Liberman), Elaboration Likelihood Model (Petty & Cacioppo), Prospect Theory (Kahneman & Tversky), Social Impact Theory (Latané), Reactance Theory (Brehm), Terror Management Theory (Greenberg). The shifts are not heuristics — they are predictions from established psychological theory.

- **`_EXTENDED_SHIFT_RULES`** — additional shift vectors for specific non-NDF page signals: Prospect Theory frame detection, endowment effect, publisher authority, remaining cognitive bandwidth, breaking news, CTV immersion. Each rule cites the theoretical basis in the surrounding comments.

- **`compute_page_edge_shift(page_ndf, page_profile_fields)`** — takes a 7-dim NDF vector and optional extended fields, returns a 20-dim shift vector mapping each edge dimension → shift value (typically −0.3 to +0.3). Clean function signature.

- **Mentioned but not yet implemented in the portion I read** (lines 100-180): the downstream integration hooks — gradient field priorities, information value updates, decision probability, copy generation direction — are noted in the docstring as places the shift vector should also feed into. These may or may not have implementation in the rest of the file that I have not yet read.

### 2.3 Why it is orphaned

Three possibilities, ordered by likelihood:

1. **It was written in a session that did not include the wiring work.** The author designed the module, wrote the shift matrix, wrote the compute function, and either ran out of time or handed off to a subsequent session that never landed. This is the most common version of the drift pattern.

2. **An earlier session tried to wire it in and hit a downstream incompatibility.** Possible if the cascade was structurally not ready to consume shift vectors at the time. Less likely because the cascade has had many substantial updates since.

3. **Someone decided it was the wrong design and abandoned it, but forgot to delete it.** Unlikely because the docstring is strident about why the design is correct, and because no alternative implementation of the same idea exists elsewhere in the codebase (I grepped for `compute_page_edge_shift`, `_SHIFT_MATRIX`, and `page_shifted_alignment` — zero hits outside this file).

The most likely interpretation is #1, which means the module is stranded work, not dead code, and resurrection is the correct action.

## 3. The Wiring Change Required

Conceptually minimal, but has to touch both `bilateral_cascade.py` and `page_edge_bridge.py` with care.

### 3.1 Current cascade behavior (from memory + grep, unverified)

I have not read `bilateral_cascade.py` in full for this pass. From the page_conditioned_query integration point at `bilateral_cascade.py:1090` (which I saw in the grep output) and the module's 1956-line size (flagged earlier in the session), the cascade:

1. Takes a decision request with buyer context and ad context.
2. Fetches the page profile from `PageIntelligenceCache`.
3. Calls `page_conditioned_query` for trilateral evidence.
4. Computes mechanism scores from the buyer's edge alignment.
5. Applies a page modulation factor (the "wrong" step).
6. Returns the top mechanism with its score.

The exact form of step 5 needs verification before the wiring change — it may already be a multiplier on each mechanism score, or it may be a multiplier on the composite alignment score, or something in between.

### 3.2 The architectural fix

The fix is structural:

1. After fetching the page profile (step 2), call `compute_page_edge_shift(page_profile.ndf, page_profile.extended_fields)`.
2. Apply the resulting shift vector to the buyer's edge alignment to produce a `page_shifted_alignment`.
3. Compute mechanism scores against the `page_shifted_alignment` instead of the raw alignment.
4. Eliminate step 5 entirely. The page effect is now captured in the shifted position, not in a post-hoc multiplier.

### 3.3 What the correct shift semantics should be

This needs a design decision and I flag it as the one design-content item in Pass B:

**Option A — Additive shift.** `shifted[dim] = raw[dim] + shift[dim]`, clipped to `[0, 1]`. This is the simplest and is what the shift matrix appears to be parameterized for (shifts are "typically −0.3 to +0.3").

**Option B — Multiplicative or ratio-based shift.** `shifted[dim] = raw[dim] × (1 + shift[dim])`, clipped.

**Option C — Soft clipping via sigmoid composition.** `shifted[dim] = sigmoid(logit(raw[dim]) + shift[dim])`. More theoretically correct for values bounded in `[0, 1]` because it prevents saturation pile-ups at the boundaries and respects the unbounded-log-odds structure of probability-like scores.

My recommendation is **Option C (sigmoid composition)** for the theoretically correct version, with a fallback to Option A if the current edge dimensions are not treated as probability-like scores. The choice needs to be made after reading the rest of `page_edge_bridge.py` and the bilateral cascade to understand the numerical conventions they use.

### 3.4 What verifying the wiring change requires

- **Read the rest of `page_edge_bridge.py`** (I read lines 1-280 in this pass; the full file continues past that).
- **Read `bilateral_cascade.py` end-to-end** to understand the current mechanism-scoring path and the current page-modulation step.
- **Verify the 20-dim edge conventions** — are they bounded in `[0, 1]`? Logit-like? What does `0.5` mean?
- **Decide the shift composition semantics** (Option A/B/C above).
- **Write the wiring patch** — probably 10-30 lines of actual code change in `bilateral_cascade.py` plus whatever small adjustments `page_edge_bridge.py` needs to integrate cleanly.
- **Test the patch** against a synthetic decision to verify the shifted-alignment path produces different mechanism recommendations than the unshifted-plus-multiplier path.

**Estimated effort:** one focused session for reading and design; one focused session for implementation and testing. Two sessions total, not a multi-week project.

## 4. What This Means for the Campaign Build

1. **Do not build a new page intelligence module.** The existing `page_intelligence.py` + `page_edge_scoring.py` + `page_gradient_fields.py` + `page_conditioned_query.py` + `page_similarity_index.py` + `page_crawl_scheduler.py` + `deep_page_scoring.py` infrastructure is what the campaign build needs. It is end-to-end, live, and learning from outcomes.

2. **Do resurrect `page_edge_bridge.py`.** Wire `compute_page_edge_shift()` into the bilateral cascade so that page priming repositions the buyer's edge alignment before mechanism scoring. This is the single highest-leverage page intelligence change available and it requires two sessions of focused work, not a new build.

3. **Do not treat the 7 live page modules as disposable.** They represent substantial sunk work, much of it theoretically sophisticated (the three-tier extraction hierarchy in `page_edge_scoring`, the trilateral evidence engine in `page_conditioned_query`, the gradient field computation in `page_gradient_fields`). Future campaign build work should extend these, not replace them.

4. **The `ADAM_INTEGRATION_AUDIT_2026-04-15.md` recommendation to "read `page_edge_bridge.py` before writing new page intelligence code"** (Section 6) is validated by this pass. The orphan was not just dead code — it was a stranded architectural fix. The audit's instinct to pause was correct.

5. **The audit report should be updated** with a note that Pass B confirmed page_edge_bridge is stranded-work (not dead code) and that the proper response is integration, not deletion.

## 5. Notes for Future Passes

- **Pass C (atom triage)** should be read through the same lens this Pass B did: some of the 16 orphan atoms will be dead drafts, some will be stranded architectural fixes like `page_edge_bridge`. The triage should distinguish between them rather than treating them uniformly.
- **The `retargeting/integrations/stackadapt_api_exporter.py` orphan** flagged in Section 4 of the audit deserves a similar Pass B treatment before any Tier 0/Tier 1 StackAdapt integration work. The same pattern may hold — it may be a stranded architectural fix, not dead code.
- **Verify with a single grep** after each Pass B-style investigation that the orphan's key symbols/functions/classes do not exist elsewhere in the codebase. In this case I verified `compute_page_edge_shift` is unique to `page_edge_bridge.py`. That grep is what distinguishes "truly stranded" from "reimplemented under a different name."

## 6. Concrete Next Actions

Ranked by immediate value for the campaign build:

1. **Read the rest of `page_edge_bridge.py`** (lines 280-end). One session, ~45 min. Output: full understanding of what the module provides and any downstream hooks it assumes.
2. **Read `bilateral_cascade.py`** end-to-end, focusing on the page-modulation step and the mechanism-scoring path. One session, ~1 hour given file size (1956 lines). Output: the specific lines to patch.
3. **Design the shift composition** (Option A/B/C) and produce a small design note, maybe 1-2 paragraphs. 15 minutes.
4. **Implement the wiring change** in `bilateral_cascade.py` to call `compute_page_edge_shift()` before mechanism scoring. One focused session. Output: a committable patch.
5. **Write an end-to-end smoke test** that exercises the new path and verifies the shifted-alignment produces different mechanism recommendations than the unshifted-plus-multiplier path. Same session as #4.
6. **Consult with Chris before committing** because this changes the semantics of every decision the cascade produces, and the change is exactly the kind of thing that could cause subtle behavioral shifts in ways outcome data would eventually surface but initial diffs would not.

Estimated total to land the fix: 2-3 sessions. The campaign build can proceed with this wiring in place and be built on top of a Bargh-correct page intelligence pathway, which is meaningfully better than building on top of the current "page modulates mechanism" pathway.
