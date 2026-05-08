# Retargeting Orchestrator Creative-Selection Audit

## Slice ID: S6.2.0
## Session: 2026-05-07 (continuation)
## Predecessor: 1c49a75 (F.2 / S6 keystone closed)
## Audit type: Read-only inspection (A.1.0 + A.2.0 precedents)
## Branch: feature/hmt-dashboard

---

## §1 Executive Summary

**Two parallel decision paths produce creative parameters at bid time, and they do not currently meet.** The "creative selection" surface in `adam/retargeting/` (78 files, ~25.6k LOC) is owned by `TherapeuticSequenceOrchestrator` (`adam/retargeting/engines/sequence_orchestrator.py:66`), which constructs a `TherapeuticTouch` (mechanism + scaffold + page cluster + creative_strategy dict) for the post-non-conversion adaptive loop. Separately, the **bid-time** creative path runs through `adam/api/stackadapt/bilateral_cascade.py:run_bilateral_cascade` (`bilateral_cascade.py:2707`) which builds a `CreativeIntelligence` dataclass (`bilateral_cascade.py:126`) consumed by `CreativeIntelligenceService.get_creative_intelligence` (`service.py:151`) and rendered to the StackAdapt response by `_format_response` (`service.py:527`). **`TherapeuticTouch` is NOT consumed by `adam/api/stackadapt/`** (verified: zero matches for `TherapeuticTouch` under that path). The two paths share data only through `Neo4j` posteriors and the `HierarchicalPriorManager` — they do not chain.

**Recommended seam: (a) BEFORE the existing creative selector — but specifically inside `run_bilateral_cascade` (the bid-time path), NOT inside `TherapeuticSequenceOrchestrator`.** S6.2 should add a cell-conditional predicate evaluator that runs after L1-L4 cascade levels resolve (so `result.primary_mechanism` and `result.mechanism_scores` exist) but BEFORE the chosen mechanism is logged via MRT propensity (`bilateral_cascade.py` ~line 3570). The evaluator narrows or re-weights `result.mechanism_scores` based on cell-conditional predicates over B/C/D/E/F.2 substrate. Existing context modulation, posture × mechanism modulation, synergy check, and DecisionTrace emission remain unchanged. **QUESTION-and-stop concerns surfaced for Claude Proper: 4** — substrate-not-yet-consumed scope (none of B/C/D/E/F.2 are read at bid time today, not just S6.2's cell predicates), parallel-path reconciliation (whether S6.2 should also wire into the TherapeuticTouch path), pruning ownership (F.1 left to "offline pass" that does not yet exist), and predicate authoring surface (rule-based DSL vs Python lambdas vs declarative YAML).

---

## §2 Pass 1 — Decision boundary call graph

### 2.1 Two parallel orchestrators

Two distinct top-level entry points produce creative parameters; they do not chain.

#### Path A — Bid-time cascade (operational, every StackAdapt impression)

```
StackAdapt webhook
  └─> CreativeIntelligenceService.get_creative_intelligence(segment_id, ..., page_url, buyer_id)
        adam/api/stackadapt/service.py:151
        ├─> assign_holdout(buyer_id) — directive Section 8.3 holdout discipline
        │     service.py:243-296 (5-10% bypass, no cascade)
        ├─> run_bilateral_cascade(segment_id, graph_cache, asin, ..., page_url, buyer_id)
        │     adam/api/stackadapt/bilateral_cascade.py:2707
        │     ├─> level1_archetype_prior(archetype)             # bilateral_cascade.py:629
        │     ├─> level2_category_posterior(...)                # bilateral_cascade.py:662
        │     ├─> level3_bilateral_edges(asin, archetype, ...)  # bilateral_cascade.py:1129
        │     ├─> level4_inferential_transfer(...)              # bilateral_cascade.py:1857 (fallback)
        │     ├─> apply_context_modulation(result, device, time, iab, page_url, ...)
        │     │     bilateral_cascade.py:1925
        │     ├─> check_mechanism_synergy(result, archetype)
        │     │     bilateral_cascade.py:2608
        │     ├─> apply_posture_modulation(mechanism_scores, posture)  # Phase 2
        │     │     bilateral_cascade.py:2862, intelligence/posture_modulation.py
        │     ├─> [MRT propensity logging — chosen_mech selected here, p_t logged]
        │     │     bilateral_cascade.py ~line 3550
        │     └─> emit_decision_trace(...)                       # Spine #6
        │           bilateral_cascade.py:3580
        └─> _format_response(cascade_result, copy_guidance, dsp_info, elapsed_ms)
              service.py:527
              # returns dict with: primary_mechanism, secondary_mechanism,
              # creative_parameters{framing, construal, tone, ...}, copy_guidance,
              # decision_id, segment_metadata, timing_ms
```

The bid-time path's "creative selection" output is `CreativeIntelligence` (a frozen-by-convention `@dataclass` at `bilateral_cascade.py:126`) carrying: `primary_mechanism: str`, `secondary_mechanism: str`, `framing: str`, `construal_level: str`, `social_proof_density: float`, `urgency_level: float`, `tone: str`, `emotional_intensity: float`, `copy_length: str`, `mechanism_scores: Dict[str, float]`, `bid_value: Optional[float]`, plus reasoning trace + refusal flags. **Selection is hybrid** — Bayesian/Thompson cascade (L1-L4) produces `mechanism_scores`, then rule-based modulators (context, posture, synergy) reweight them, then MRT propensity-aware sampling picks `primary_mechanism`.

#### Path B — Therapeutic post-non-conversion adaptive loop

```
TherapeuticSequenceOrchestrator (adam/retargeting/engines/sequence_orchestrator.py:66)
  ├─> create_sequence(user_id, brand_id, archetype_id, bilateral_edge, ...)
  │     sequence_orchestrator.py:144
  │     ├─> ConversionBarrierDiagnosticEngine.diagnose(...)
  │     │     barrier_diagnostic.py
  │     ├─> _apply_options_filter(diagnosis)         # sequence_orchestrator.py:222
  │     ├─> WithinSubjectDesigner.design_sequence(...)  # Enhancement #36
  │     └─> TouchBuilder.build(sequence_id, position=1, diagnosis, ...)
  │           adam/retargeting/engines/touch_builder.py:73
  │           # Constructs TherapeuticTouch with:
  │           #   - mechanism (from diagnosis.recommended_mechanism)
  │           #   - scaffold_level
  │           #   - target_page_cluster (5-class: analytical/emotional/social/transactional/aspirational)
  │           #   - target_page_mindstate (edge_dimensions dict)
  │           #   - creative_strategy (dict assembled by NarrativeArcBuilder.build_creative_context)
  │           #   - narrative_chapter / function / construal / processing_route
  │           #   - autonomy_language, opt_out_visible
  │           #   - timing constraints
  │           # Mechanism selection delegated to BayesianMechanismSelector via diagnostic engine
  │           # Page cluster: PlacementOptimizer.compute_ideal_mindstate population default,
  │           # overridden by per-user posterior if user has ≥2 obs (touch_builder.py:265)
  │
  └─> process_outcome_and_get_next(sequence_id, outcome, bilateral_edge, ...)
        sequence_orchestrator.py:262
        # 10-step adaptive loop: record outcome → update learning → check rupture
        # → check suppression → re-diagnose barrier → build next touch
```

`TherapeuticTouch` (`adam/retargeting/models/sequences.py`) is the path-B output. Selection is **rule-based + Bayesian** — barrier diagnosis determines mechanism via Thompson Sampling over `BayesianMechanismSelector` (`mechanism_selector.py:115`), then `TouchBuilder` rule-assembles the touch envelope.

### 2.2 Canonical seam vs peripheral

| Module | Role |
|---|---|
| `bilateral_cascade.py:run_bilateral_cascade` | **Canonical bid-time creative-selection seam** (every impression) |
| `service.py:CreativeIntelligenceService.get_creative_intelligence` | Bid-time API wrapper |
| `sequence_orchestrator.py:TherapeuticSequenceOrchestrator` | **Canonical post-non-conversion seam** (only fires after non-conversion) |
| `touch_builder.py:TouchBuilder.build` | Rule-based touch assembler within Path B |
| `mechanism_selector.py:BayesianMechanismSelector` | Thompson Sampling driver shared across paths via `HierarchicalPriorManager` |
| `barrier_diagnostic.py:ConversionBarrierDiagnosticEngine` | Diagnosis input to Path B mechanism selection |
| `placement_optimizer.py:PlacementOptimizer` | Page-cluster prescription used by Path B `TouchBuilder` |
| `resonance/resonance_learner.py`, `resonance_model.py`, `evolutionary_engine.py` | Learning-side (offline / outcome-time), NOT bid-time selectors |
| `rupture_detector.py`, `suppression_controller.py`, `narrative_arc.py`, `frustration.py` | Within-Path-B helpers — gates and assemblers, not selectors |
| `workflows/therapeutic_workflow.py` | Optional LangGraph wrapper around Path B; `generate_creative_node` (`therapeutic_workflow.py:172`) is a placeholder that builds a creative_spec dict — NOT a runtime creative selector |
| `integrations/stackadapt_translator.py`, `stackadapt_api_exporter.py` | Offline export tools (campaign/audience setup); NOT bid-time |

**Path A (bilateral_cascade) is where every StackAdapt impression resolves.** Path B is the TouchBuilder-driven post-non-conversion loop that produces TherapeuticTouches but those touches do not flow back into the bid-time response. The two paths share only `HierarchicalPriorManager` posteriors via Neo4j.

---

## §3 Pass 2 — Current selector input inventory

Inputs read by `run_bilateral_cascade` and downstream of it through `apply_context_modulation` + `apply_posture_modulation`:

| Field | Source module | Bid-time access | Latency | Cell-axis classification |
|---|---|---|---|---|
| `segment_id` | StackAdapt webhook | request param | ~0 | embeds **archetype** (cell axis #1) + mechanism_hint + category |
| `archetype` | parsed from `segment_id` via `_parse_segment_id` (`bilateral_cascade.py:3838`) | sync regex | ~0 | **cell axis #1** ✓ |
| `category` (product) | parsed from `segment_id` | sync regex | ~0 | OTHER (used for L2 posterior; not a cell axis) |
| `asin` | request param or campaign-default mapping | sync dict lookup | ~0 | OTHER (drives L3/L4 graph queries) |
| `device_type` | request param | sync | ~0 | OTHER (context modulation) |
| `time_of_day`, `day_of_week` | request param | sync | ~0 | OTHER (temporal modulation) |
| `iab_category` / `iab_categories` | request param | sync | ~0 | OTHER (inventory category) |
| `buyer_id` | request param | sync | ~0 | identity key (drives buyer_profile + cohort lookups) |
| `page_url` | request param | sync | ~0 | identity key (drives page_intelligence lookup) |
| `page_title`, `referrer`, `keywords` | request param | sync | ~0 | OTHER (inventory + impression-state resolution) |
| `bilateral_edge` (27-dim alignment) | `level3_bilateral_edges` via Neo4j graph query | async Neo4j | ~10-50ms | OTHER (the actual creative-derivation input — feeds derive_framing/construal/tone/etc.) |
| `mechanism_scores: Dict[str, float]` | composed by L1-L4 + chain attestations | — | — | OTHER (the selector's principal output before posture/synergy reweighting) |
| `posture_class` | `page_intelligence.lookup(page_url).attentional_posture` → `categorize_posture` (`bilateral_cascade.py:2849-2861`) | sync cached | <1ms | **cell axis #2** ✓ — but currently derived as 4-class HIGH/MID/LOW/UNKNOWN (`page_attentional_posture_substrate.categorize_posture`), NOT the 5-class `FIVE_CLASS_POSTURES` F.1 cells use |
| `posture_confidence`, `posture_vector` | same source | sync cached | <1ms | metadata |
| `bong_posterior` | `graph_cache.get_buyer_profile(buyer_id).bong_posterior` | sync cached | <1ms | OTHER (Bayesian posterior over mechanism response) |
| `goal_activation` | `goal_activation.get_goal_learner().get_hunt_recommendations(...)` | sync cached | <1ms | OTHER (goal-state selection) |
| `chain_attestations` | atom output bundles | sync per-decision | <1ms | OTHER (DCIL chain evidence) |
| `epsilon_floor`, `ts_propensity` | computed at MRT step | sync | <1ms | OTHER (propensity-aware sampling parameters) |

**Cell axes NOT currently read by the bid-time path:**
- `conversion_stage` (cell axis #3 — F.1 uses `ConversionStage` from `adam/retargeting/models/enums.py:21`). The cascade does NOT read journey state. `ConversionStage` is consumed by Path B only (`barrier_diagnostic.py`, `touch_builder.py`).
- `regulatory_focus_priming` (cell axis #4 — `PagePrimingSignature.regulatory_focus_priming`, B / S6-prep.2). PagePrimingSignature is **NOT consumed anywhere outside `adam/cells/` and `adam/priming/` itself** — verified via `grep` (zero matches in `adam/api/`, `adam/intelligence/bid_composer.py`, `adam/intelligence/kelly_bid_sizing.py`, `adam/retargeting/`).
- `valence` + `arousal` (cell axis #5 inputs). Same as above — PagePrimingSignature.valence/arousal not bid-time-read.

**Cell features NOT currently read by the bid-time path** (substrate-not-yet-consumed across the board):
- `PageMindstateVector.fomo_score` (C / S6-prep.3a) — zero bid-time consumers
- `PageMindstateVector.psych_ownership_proxy` (C / S6-prep.3a) — zero bid-time consumers
- `PageMindstateVector.depletion_proxy` (D / S6-prep.3b) — zero bid-time consumers
- `PagePrimingSignature.persuasion_knowledge_activation` (B / S6-prep.2) — zero bid-time consumers
- `UserCohort.compensatory_consumption_pattern` + `get_cohort_compensatory_flag` (E + F.2) — zero bid-time consumers (F.2's accessor exists but no caller invokes it)

**Posture cardinality mismatch surfaced for Claude Proper.** F.1's cell taxonomy uses the 5-class `FIVE_CLASS_POSTURES` from `posture_five_class.py:113` (INFORMATION_FORAGING / TASK_COMPLETION / LEISURE_BROWSING / SOCIAL_CONSUMPTION / TRANSACTIONAL_COMPARISON). The bilateral cascade reads a 4-class `categorize_posture` output (HIGH / MID / LOW / UNKNOWN) from `page_attentional_posture_substrate.categorize_posture` (`bilateral_cascade.py:2855`). These are different posture taxonomies. S6.2 needs to either map between them at the predicate evaluator boundary or surface the mismatch as a separate substrate slice.

---

## §4 Pass 3 — Downstream consumers + output contract

### 4.1 Bid-time path output (`run_bilateral_cascade` → service response)

`run_bilateral_cascade` returns `CreativeIntelligence` (`bilateral_cascade.py:126`). `CreativeIntelligenceService._format_response` (`service.py:527-590`) flattens it into:

```python
{
  "decision_id": str,
  "primary_mechanism": str,           # ci.primary_mechanism
  "secondary_mechanism": str,
  "creative_parameters": {            # ci.* + headline_strategy + cta_style
    "primary_mechanism": str,
    "framing": str,                   # gain | loss | mixed
    "construal_level": str,           # concrete | moderate | abstract
    "social_proof_density": float,
    "urgency_level": float,
    "tone": str,
    "emotional_intensity": float,
    "copy_length": str,
    "headline_strategy": str,
    "cta_style": str,
  },
  "copy_guidance": dict,              # built via _build_copy_guidance + _enrich_copy_guidance
  "evidence": dict,                   # cascade_level, edge_count, confidence, sample_size
  "mechanism_scores": Dict[str, float],
  "bid_value": Optional[float],
  "decision_path": str,
  "segment_metadata": dict,
  "timing_ms": float,
  "is_holdout": False,                # only present when bypass triggered
  "is_refused": False,                # only present when refused=True
}
```

**Downstream consumers:**
- The HTTP response itself (StackAdapt API caller — out-of-process).
- `decision_trace_emitter.emit(trace)` (`bilateral_cascade.py:3780`) — async drain to Redis (14d hot) + Neo4j (long-term).
- `red_criteria_snapshot.get_red_snapshot().record_bid()` (`bilateral_cascade.py:2739`) — RED-criteria denominator counter.
- `stackadapt_holdout_assignments_total` Prometheus counter (`service.py:253`).

**S6.2's output must remain dict-compatible with `_format_response`.** The simplest contract: S6.2 narrows or re-weights `result.mechanism_scores` (a dict the cascade already populates), then leaves `_format_response` untouched. If S6.2 also wants to surface "which cell drove this decision," add a single `cell_id: Optional[str]` field on `CreativeIntelligence` and surface it in the formatted response under a new `cell` block — backward-compatible (None when S6.2 doesn't apply or when cell predicates didn't fire).

### 4.2 Path B output (`TouchBuilder.build` → TherapeuticTouch)

Returns `TherapeuticTouch` (`adam/retargeting/models/sequences.py`). Consumed by:
- `TherapeuticSequence.touches_delivered.append(...)` — sequence state
- `_persist_sequence` → L2 Redis (`sequence_orchestrator.py:588`)
- `_record_outcome` (sequence_orchestrator.py) — outcome accounting
- `RetargetingLearningLoop.process_touch_outcome` — post-touch learning
- API responses for `/sequence/create` and `/sequence/{id}/next-touch` (`api.py:172, 197`)
- `stackadapt_translator.py` and `stackadapt_api_exporter.py` (offline export pipelines, NOT bid-time)

**`TherapeuticTouch` does NOT flow into `run_bilateral_cascade` or `_format_response`.** Verified by `grep`. The two paths share only Neo4j-persisted posteriors via `HierarchicalPriorManager`.

---

## §5 Pass 4 — Integration seam adjudication options

### 5.1 (a) BEFORE the existing creative selector

S6.2 runs as a **predicate evaluator inside `run_bilateral_cascade`**, after L1-L4 levels resolve and after `apply_context_modulation` / `apply_posture_modulation` have reweighted `mechanism_scores`, but BEFORE the MRT propensity step that picks `chosen_mech` (`bilateral_cascade.py` ~line 3550). The evaluator:

1. Constructs the cell tuple via `adam/cells/constructor.py:get_cell_for_bid(archetype, posture, conversion_stage, regulatory_focus, valence, arousal)` — but the substrate-fetch step needs to happen first (see §8).
2. Looks up cell-conditional predicates for the resolved `cell_id`.
3. Applies predicate-driven reweighting on `result.mechanism_scores` (multiplicative bands, similar to how `apply_posture_modulation` already operates).
4. Optionally surfaces the resolved `cell_id` on the `CreativeIntelligence` for downstream observation.

**Evidence FOR (a):**
- `mechanism_scores` is a dict the cascade already populates and modulators already reweight (`apply_posture_modulation` is the existing template).
- Existing fail-soft modulator pattern (try/except wrapping all stack-modifications in cascade) makes adding one more modulator low-risk.
- Backward-compat trivial: S6.2's modulator is a no-op when substrate unavailable.
- The cell tuple is fully constructible from data the cascade ALREADY consumes (archetype, posture) plus data already cached in upstream pipelines (PagePrimingSignature, journey state) — no new bid-time computation, just a few cached lookups.

**Evidence AGAINST (a):**
- The bilateral cascade is 3,909 LOC; adding more to it inflates the hot path.
- `conversion_stage` (cell axis #3) requires reading journey state, which the cascade does not currently access at bid time. Adding that lookup means crossing a new module boundary.
- The path-B `TouchBuilder` already reads diagnosis-derived `ConversionStage` and could conceivably consume cells too — picking (a) means cells improve bid-time only, not Path B.

### 5.2 (b) ALONGSIDE the existing creative selector

Both run; a controller compares/blends. Higher complexity. No clear win given the cascade's existing modulator pattern already provides the "alongside" structure (each modulator runs independently and reweights `mechanism_scores`). Pure-(b) seems redundant with what (a) already gives.

### 5.3 (c) REPLACING parts of the existing creative selector

Predicate evaluator subsumes `apply_context_modulation` + `apply_posture_modulation` + `check_mechanism_synergy`. **High disruption.** The existing modulators encode lots of accumulated calibration (Phase 2 line 971-973 posture × mechanism, Phase 8 holdout discipline, etc.). Replacing them risks regressing pinned behaviors documented across many prior commits. Not recommended for the keystone-consumer slice.

### 5.4 No pre-decision

Surface for Claude Proper. My read favors **(a)** strongly — it matches the existing modulator pattern and minimizes coupling — but Claude Proper may have view on whether S6.2 should also wire into Path B for symmetry.

---

## §6 Pass 5 — Test surface

### 6.1 Files mentioning `creative` / `Creative` / `TherapeuticTouch` in target test directories

| File | Hits | Description |
|---|---|---|
| `tests/integration/test_full_system.py` | several | Full bid-path integration; tests latency budget propagation through `run_bilateral_cascade` (lines 92-116). End-to-end test that S6.2 will need to extend for cell-conditional behavior. |
| `tests/integration/test_atom_dag_flow.py` | several | Atom DAG integration; `latency_budget_ms=10` short-budget test (line 816). |
| `tests/integration/test_embedding_atom_flow.py` | several | Embedding-pipeline atom flow. |
| `tests/integration/test_b1_stage2_signal_stash.py` | 1 | B1 Stage 2 mechanism_effectiveness_signal stash on `TherapeuticSequence` — only test importing `TherapeuticSequenceOrchestrator`. Pins that learning_loop output is stashed on the sequence. |

**No tests in `tests/retargeting/` or `tests/cells/` or `tests/intelligence/` currently exercise `creative`-keyword paths** (per `rg -lt py "creative" ...` returning empty across those three dirs). The retargeting tests under `tests/retargeting/` cover only `mindstate_composite_states` (C + D). The cells tests cover only F.1's taxonomy + constructor. The intelligence tests cover only the posture classifier.

### 6.2 Other relevant retargeting/cascade test surface (from broader repo grep)

- `tests/unit/test_creative_upload_pipeline.py` — campaign-setup creative ingestion (not bid-time selection).
- `tests/unit/test_creative_spot_check_sweep.py` — creative spot-check (calibration sweep, not bid-time).
- `tests/unit/test_creative_manifest_reconciliation.py` — manifest reconciliation (offline).
- `tests/unit/test_recommendation_class_cascade_wire.py` — cascade wiring for recommendation_class (deprecated per directive Phase 1 cuts).
- `tests/unit/test_cascade_correction_response.py` — cascade response shape.
- `tests/unit/test_cascade_mrt_wiring.py` — MRT propensity wiring inside the cascade.
- `tests/unit/test_decision_trace.py` + `test_decision_trace_page_url.py` — DecisionTrace emission shape.
- `tests/unit/intelligence/test_creative_metaphor_scoring.py` — metaphor scoring (cell-feature, not selector).
- `tests/unit/intelligence/test_blend_fit.py` — blend_fit creative parameter (cell-feature, not selector).

### 6.3 Regression invariants S6.2 must preserve at the chosen seam

If S6.2 lands at seam (a) inside `run_bilateral_cascade`:
- `CreativeIntelligence` dataclass fields and types remain unchanged (or only ADD `cell_id`).
- `mechanism_scores` stays `Dict[str, float]` with values in `[0, 1]`.
- `_format_response` output dict shape unchanged at top level.
- Latency budget enforcement (`test_full_system.py:test_cascade_degrades_on_budget`) continues to clamp work to budget.
- DecisionTrace emission contract preserved (`test_decision_trace*.py`).
- MRT propensity (`p_t`, `epsilon_floor`, `p_t_known`) still logged correctly (`test_cascade_mrt_wiring.py`).
- Holdout + refused paths still bypass cascade work (existing tests in `service.py:243-296`, `bilateral_cascade.py:328`).

### 6.4 End-to-end tests needing extension for cell-conditional coverage

- `tests/integration/test_full_system.py` — add cells-aware end-to-end run with at least 2 cell IDs producing different `mechanism_scores`.
- `tests/integration/test_atom_dag_flow.py` — verify cell selection participates in atom DAG when applicable.
- A new `tests/cells/test_predicate_evaluator.py` would house S6.2's unit tests for the evaluator itself.
- A new `tests/integration/test_cell_conditional_cascade.py` would house the seam-(a)-inside-cascade integration tests.

**Test-update count estimate:** ~6-8 existing tests need light updates (mostly to handle the new `cell_id` field if added to `CreativeIntelligence`); ~25-35 new tests for S6.2 itself (predicate evaluation, substrate-fetch coordination, fallback when substrate unavailable, latency, cache coherence).

---

## §7 Pass 6 — Latency budget accounting

### 7.1 Established budget

Per `LatencyBudget` (`adam/infrastructure/resilience/latency_budget.py:43`): **default total = 120ms**, reserve = 10ms (so usable ~110ms). This is the operational SLA the cascade is built to. The slice-spec gap-assessment numbers (5+18+12+25+10 = 70ms with 30ms headroom) describe a tighter sub-budget allocation, but the runtime LatencyBudget total is 120ms.

### 7.2 Current cascade latency observation

No existing benchmark test directly measures `run_bilateral_cascade` p99. The cascade tracks elapsed via `time.monotonic()` in `_request_count` / `_total_latency_ms` (`service.py:142`) but I did not find a pinned p99 assertion in `tests/`. The latency-budget tests (`test_full_system.py:92-116`) only verify the budget mechanism plumbs correctly, not absolute timing.

**Estimated current cascade composition** (from cascade structure, not measured):
- L1 archetype prior: <2ms (in-memory dict lookups + `level1_archetype_prior`)
- L2 category posterior: 2-10ms (one Neo4j query)
- L3 bilateral edges: 10-50ms (graph traversal — biggest single line item)
- L4 inferential transfer (only when L3 thin): another 10-30ms
- Context modulation + synergy + posture modulation + chain attestations: <5ms total (cached lookups)
- MRT propensity selection + DecisionTrace emit: <2ms (sync emit; async drain)

So the cascade dominantly spends time in L3/L4 (Neo4j). Modulators are cheap.

### 7.3 Where S6.2 latency sits

If S6.2 lands at seam (a) inside `run_bilateral_cascade`:
- `get_cell_for_bid` is 4μs p99 (F.1's Test 17).
- `get_cohort_compensatory_flag` is <1ms cached (F.2's Test 15).
- PagePrimingSignature lookup: should be cached in the priming Feature Store (S3.3).
- Journey-state lookup: needs verification — the bilateral cascade does not currently read journey state, so the cost of plumbing it in is the open question (estimate <2ms if cached, 5-15ms if it requires a Neo4j hop).
- Predicate evaluation itself: depends on architecture (rule-based DSL execution: <500μs for ~10 rules; Python lambdas: <100μs).

**Total S6.2 added latency budget request: ~3ms p99 if substrate is fully cached, ~10-15ms p99 if journey-state lookup hits Neo4j cold.** This fits comfortably inside the 120ms total — the cascade's existing 10-50ms L3 dominates.

**Allocation question for Claude Proper:** Should S6.2 latency live in the gap-assessment "18ms cell-classifier slot" or "25ms retargeting slot"? Functionally it's the cell-classifier slot (S6.2 IS the cell predicate evaluator). The runtime LatencyBudget total of 120ms makes the bookkeeping less critical than the gap-assessment numbers suggest.

---

## §8 Recommended S6.2 Scope

### 8.1 Recommended seam

**(a) BEFORE the existing creative selector — specifically inside `run_bilateral_cascade` at `bilateral_cascade.py` ~line 2870 (after `apply_posture_modulation`, before MRT propensity step).** Add as a new modulator function `apply_cell_conditional_predicates(result, cell_id, ...)` that fail-soft-wraps in try/except matching the existing modulator pattern (lines 2836-2870 for posture modulation are the structural template).

### 8.2 Predicate evaluator architecture options

**Recommended: rule-based DSL with declarative rule files.** Three architectural candidates:

- **(α) Rule-based with Python decorators.** Predicates registered as `@cell_predicate(cell_id_pattern="ANALYST_TC_*", priority=10)` decorated functions. Pros: type-safe, IDE-discoverable, easy to test. Cons: predicates live in Python source; non-engineers cannot author.
- **(β) Declarative YAML/JSON rule files.** Rule format like `{"cell": "ANALYST_TC_INT_*", "if": "depletion_proxy > 0.6", "then": {"social_proof": *0.8, "scarcity": *1.2}}`. Pros: data-side authoring, hot-reloadable, version-controllable separately. Cons: needs a parser + DSL spec + validation; harder to debug.
- **(γ) Compiled DAG.** Rules pre-compiled to a decision tree at module import. Pros: fastest execution. Cons: compilation cost + harder to extend.

**Recommended (α) for the first slice.** S6.2 ships ~5-10 predicates initially; Python decorators are the lowest-friction surface. (β) becomes attractive once rule count exceeds ~20-30 or when non-engineers need to author. (γ) only matters if predicate evaluation latency becomes a bottleneck (currently <500μs estimated).

### 8.3 Cell pruning surface handling

**Defer to a separate slice.** F.1 left "empirical-density pruning" as an offline pass that does not yet exist (`taxonomy.py:Cell.is_active` defaults `True`; no offline pruning pipeline emits `is_active=False`). The constructor at `constructor.py:_synthesize_parent_cell` handles parent routing when `is_active=False`, but nothing flips the flag yet.

S6.2 should:
- Treat all 2,880 cells as active (status quo).
- Surface a placeholder `prune_inactive_cells` function with a `NotImplementedError` plus docstring explaining the offline pipeline that needs to populate it.
- Defer the actual pruning pipeline to S6.3 or a sibling slice — it requires a cohort-population aggregator over (archetype, posture, conversion_stage, regulatory_focus, quadrant) cells that does not currently exist.

### 8.4 Substrate-fetch coordination

S6.2's predicate evaluator needs to fetch the cell-feature substrate (B/C/D/E/F.2 fields) at evaluation time. Two options:
- **(δ) Compose substrate inputs at the cascade boundary** (similar to how posture is composed at `bilateral_cascade.py:2849-2861`). Each substrate fetch wrapped in try/except → fail-soft to neutral default if upstream pipeline hasn't populated the field.
- **(ε) Expose a `get_cell_features(buyer_id, page_url, ...) -> CellFeatures` aggregator** in `adam/cells/` that pulls all substrate inputs in one place. Cleaner architecture; one cache to coordinate; one place to reason about substrate-fetch latency.

**Recommended (ε).** Cells own the cell-feature substrate as an architectural concept. The aggregator becomes the public API S6.2 (and any future cell consumer) calls.

### 8.5 Test-update count estimate

- ~6-8 light updates to existing tests (`test_full_system.py`, `test_cascade_*`, `test_decision_trace*`) for new `cell_id` field on `CreativeIntelligence` if added.
- ~10-15 new unit tests in `tests/cells/test_predicate_evaluator.py` (predicate registration, evaluation, cell-pattern matching, no-op when substrate unavailable, fail-soft behavior).
- ~5-10 new unit tests in `tests/cells/test_cell_features.py` (substrate aggregator).
- ~5-8 new integration tests in `tests/integration/test_cell_conditional_cascade.py` (end-to-end cascade with predicates firing).
- **Total: ~25-35 new tests, ~6-8 light updates.**

### 8.6 Commit-LOC delta estimate

- `adam/cells/predicates.py` (new): ~250 LOC — decorator infra + registry + evaluator + 5-10 initial predicates.
- `adam/cells/features.py` (new): ~200 LOC — substrate aggregator pulling B/C/D/E/F.2 fields with fail-soft defaults.
- `adam/api/stackadapt/bilateral_cascade.py` (edit): +50-80 LOC — new modulator function + import wiring.
- Optional `cell_id: Optional[str]` field on `CreativeIntelligence`: +5 LOC.
- Tests: ~600-900 LOC.
- Total commit: ~1,100-1,500 LOC. Comparable to F.1 (959 LOC) + F.2 (906 LOC).

### 8.7 QUESTION-and-stop concerns surfaced

**Q16 — Substrate-not-yet-consumed scope.** None of B/C/D/E/F.2's substrate fields are currently consumed at bid time (verified via grep across `adam/api/`, `adam/intelligence/bid_composer.py`, `adam/retargeting/`). S6.2 is not just adding cell predicates — it's the FIRST consumer of the entire B/C/D/E/F.2 substrate stack. This expands S6.2's effective scope beyond "predicate evaluator." Options: (i) S6.2 owns the substrate-fetch coordination via a `cell_features` aggregator (recommended in §8.4); (ii) split S6.2 into S6.2.1 (substrate-fetch coordinator) + S6.2.2 (predicate evaluator); (iii) ship substrate-fetch as a separate sibling slice and S6.2 consumes only the aggregator.

**Q17 — Parallel-path reconciliation.** TherapeuticTouch (Path B) and CreativeIntelligence (Path A) do not flow into each other. F.1 cells are constructible from inputs both paths have. Should S6.2 wire into Path B's `TouchBuilder` as well, or only Path A's `run_bilateral_cascade`? My read: **only Path A for S6.2** — Path A is the bid-time path that runs every impression; Path B fires only after non-conversion. But reconciliation may matter long-term.

**Q18 — Posture cardinality mismatch.** F.1 cells use 5-class FIVE_CLASS_POSTURES. Bid-time cascade reads 4-class HIGH/MID/LOW/UNKNOWN from `categorize_posture`. S6.2 needs to either (i) add a 5-class posture lookup at the cell-feature aggregator boundary (probably via a new `posture_classifier_5class` or remapping the posture intelligence cache) or (ii) defer 5-class posture to a separate slice and start with a coarser posture proxy. This decision changes which cells are reachable.

**Q19 — Predicate authoring surface.** §8.2 recommends Python decorators (α) for the first slice. Is that the right long-term surface, or should S6.2 ship the YAML DSL (β) directly to avoid migration churn? My read: ship (α) first; if predicate count grows past ~20, migrate to (β) in a sibling slice. But Chris may have view on data-side authoring requirements.

---

## §9 Audit closure

**State at standdown (2026-05-07):**
- Repo HEAD: `1c49a75` (F.2 / S6 keystone closed).
- Branch: `feature/hmt-dashboard`.
- Cells substrate consumers: zero (verified — `from adam.cells` returns no matches outside `adam/cells/` itself).
- B/C/D/E/F.2 cell-feature substrate consumers at bid time: zero across the board.
- Recommended seam: (a) inside `run_bilateral_cascade` at `bilateral_cascade.py` ~line 2870.
- Recommended architecture: rule-based decorators (α) + cell-features aggregator (ε).
- 4 QUESTION-and-stop concerns surfaced (Q16-Q19) for Claude Proper.

**Next step:** S6.2 prompt from Claude Proper that incorporates audit findings and adjudicates Q16-Q19. After Q16-Q19 close, S6.2 ships ~1,100-1,500 LOC with ~25-35 new tests + ~6-8 light updates to existing tests.

**Cross-reference precedents:**
- A.1.0 audit: `docs/audits/MAXIMIZER_FRAGMENTATION_AUDIT.md` (commit c237e4b).
- A.2.0 audit: `docs/audits/COLD_START_ARCHETYPE_PROFILES_AUDIT.md` (commit 9a2fc84).
- Gap assessment: `docs/MINDSET_COVERAGE_GAP_ASSESSMENT_2026_05_07.md` §6 Step 1.
- F.1 substrate: commit 1988a8d (`adam/cells/taxonomy.py`, `adam/cells/constructor.py`).
- F.2 substrate: commit 1c49a75 (`adam/intelligence/cohort_discovery.py:detect_compensatory_consumption_pattern`, `adam/api/stackadapt/graph_cache.py:get_cohort_compensatory_flag`).
