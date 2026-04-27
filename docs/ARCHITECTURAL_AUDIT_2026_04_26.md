# ADAM Architectural Audit — 2026-04-26

**Scope.** Deep audit covering: customer-product-ad fit determination; state vs trait modeling and state×trait combination; language modeling pipeline; learning loop wiring and outcome attribution; day-1 readiness for the LUXY pilot; whether the architecture supports causal-not-correlational learning.

**Method.** Five parallel deep-dive agents, each reading a distinct subsystem against the platform's stated commitments (orientation document, theoretical foundation, HMT foundation). Reports synthesized below; full per-agent findings in §10.

**Bar.** Peer-review-grade. Distinguishes architecture-as-described from architecture-as-running.

---

## §0. CANONICAL DIRECTION FRAMING (added 2026-04-26 PM after handoff documents reviewed)

After the audit was first written, Chris directed: "anything weaker than what's proposed in the three handoff documents (`newer directions.md`, `Concept toward Retargeting.md`, `Deepening moat through adjacent-field science 4-23.md`) is deprecated; what's described in those documents IS the direction." This reframes how every finding below should be read.

**Reframed reading rule:**

| Finding category | What it means in the canonical-direction frame |
|---|---|
| A pattern flagged as "weak / additive / correlational / formula-based" | **Deprecated.** A weaker version of what the documents specify. Has a successor named in the documents. |
| A primitive flagged as "orphaned / unwired / built-but-unused" | **Canonical primitive awaiting wiring.** Built deliberately to replace its deprecated counterpart. Wiring is the work. |
| A "structural bug" (typo, missing module, FK gate, etc.) | **Real bug, direction-independent.** Fix regardless. |

**What's been wired since this audit was first written (2026-04-26 PM same day):**

| Commit | Item | Audit-finding before | Status now |
|---|---|---|---|
| `cebec5e` | StackAdapt `campaignDelivery` substrate query | Schema-drifted; per-campaign metrics zero | Resolved — real metrics flowing |
| `8228a76` | Next 16 detail-page double-encoding | Page returned 404 on every encoded id | Resolved — 200 with source-aware rendering |
| `f11711c` | task_23 same Campaign.stats bug | DCIL data input hollow | Resolved — snapshots have real per-campaign metrics |
| `f1be5e3` | `register_consumer` → `register_component` | 6 consumers silently degraded | Resolved — fan-out restored |
| `e637c37` | `adam.infrastructure.redis_client` shim | 8 DCIL tasks ImportError; persistence layer dropped to memory dicts | Resolved — DCIL persistence is real across restarts |
| `b4765c7` | Trilateral page-conditioned query as L3 canonical path | Cascade ran additive page-shift + formulas (Doc 1 explicit "DON'T do this") | Wired — trilateral fires when page profile exists; additive path A14-flagged for retirement |
| `9c66fb3` | ClaudeArgumentEngine as `CopyGenerationService` canonical emission | Copy emitted from f-string templates (industry-default; bilateral moat invisible) | Wired — engine fires when archetype+edges+API key all present; templates A14-flagged for retirement |

The remaining findings below should be read with this progress in mind.

---

## §1. Executive cut — what the system actually is, today

ADAM has **three learning loops in different states of closure**. The headline narrative ("the system gets stronger with every outcome") is true of one of them.

| Loop | Status | What it does |
|---|---|---|
| α — Live decision → BayesianPrior + RESPONDS_TO + gradient → next cascade | **CLOSED, working** | Population reinforcement of mechanism effectiveness per archetype-category cell. Updates fire on every webhook conversion event; archetype-prior cache invalidates; next decision sees updated priors. |
| β — DCIL daily tasks → operator-reviewed directives → execution | **STRUCTURALLY BROKEN** | Three independent failures: `redis_client` module missing (8 DCIL tasks ImportError); `dcil_bridge.sync_directives_to_postgres()` orphaned (zero callers); `management.db.campaigns` empty (FK gate blocks insert). Even with task_23 substrate just patched, the chain dies at three points before reaching the dashboard. |
| γ — Operator deviation → horizon adjudication → WhyLibraryEntry → defensive prior | **WIRED-BUT-UNFED, partly A5-correlational** | Operator path (Slice D2) ships and persists Outcome+WhyLibraryEntry. Auto-adjudication has no scheduler call site. The auto-evaluators that DO exist are A5 antipatterns (before/after metric comparison → verdict) with honest labeling, but they feed defensive priors that influence subsequent decisions. |

**The decision path Chris probably believes runs is not the decision path that runs.** Production LUXY traffic enters through `/api/v1/stackadapt/creative-intelligence` and traverses the 5-Level Bilateral Cascade (`bilateral_cascade.py`) — a formula-table mechanism scorer with empirically-fit weights. The 30-atom DAG (the construct-level cognitive engine — UserState, MimeticDesire, AutonomyReactance, PersuasionPharmacology, …) is **dead code on the live path**. The atom DAG fires only from `demo/*` routes and the `CampaignOrchestrator` they call.

**The state×trait coupling Chris's frame requires is not what the substrate computes.** At every load-bearing combination site — `personality_expression.py:437` (`base + context_mod + state_mod`), `page_edge_bridge.py:362` (`shifted = raw + page_delta`), `decision_probability.py` (linear logit), cascade L3 mechanism scoring (linear weighted sum across dimensions) — state and trait combine **additively**. Twelve hardcoded interaction-pair adjustments at `bilateral_cascade.py:1086-1095` cap at ±8% — present, but small, on top of the additive main effects that dominate. The Bargh×Pinker×Ridley dynamic-competition motif is asserted in docs and not implemented at the substrate. `gradient_fields.interaction_terms` ARE computed (with R²-improvement gating) but **consumed only for lift estimation, never in `compute_decision_probability` or in cascade L3 scoring**. The single place non-additive structure is captured is dead-ended for in-decision use.

**Bilateral is real at the substrate, collapsed at the surface.** Bilateral pairing is implemented at L3 of the cascade (`BRAND_CONVERTED` edges carrying 20 alignment dimensions, empirically fit). But the partner-visible output — the actual ad copy — is generated by a four-template f-string library (`copy_generation/service.py:83-451`). `MECHANISM_TEMPLATES` is hardcoded English with `_gain_hook` returning `f"Discover the benefits of {product}."` and `_loss_hook` returning `f"Don't miss out on {product}."`. Bilateral evidence informs scalar parameters (`gain_emphasis`, `urgency_level`); the final string is template-composed and consults neither buyer-side review language nor brand voice. The genuinely bilateral path (`ClaudeArgumentEngine`) is implemented and orphaned.

**Construct accessibility (Bargh's primed-construct mechanism) is not represented.** No file, class, or graph node represents "construct X is currently accessible at strength Y in this user's momentary cognition" separate from chronic trait values. The platform has chronic dimensions plus a single 20-dim page-shift vector that gets **added to trait** (collapsing the very distinction Bargh's frame requires). `theory_schema.py:108-228` defines 14 nodes labeled `PsychologicalState` — they are NDF threshold poles, i.e., trait-like. The vocabulary actively obscures the trait-vs-state distinction.

**Primary metaphor — the foundation's load-bearing mechanism — is implemented on the page side only and dead-ends.**
- Page-side scorer: real, Lakoff-grounded, 8 axes (`claude_feature_scoring.py:80-89, 319-392`)
- Buyer-side review annotation: scores zero of the 8 axes
- Brand-copy-side annotation: scores zero of the 8 axes
- Bilateral edge dimensions: no metaphor dimension
- Creative-side scorer: not implemented (only the dataclass shape exists in `blend_fit.py:98-100`)
- `compute_blend_fit`: implemented, **zero callers**

The mechanism Chris's foundation document calls "neural-substrate-level intervention" is downstream-dark.

---

## §2. Day-1 honest verdict for LUXY pilot

**What works:** decisions get made; outcomes get ingested; one of three learning loops closes. The 6.74M LUXY edges in Aura DO drive the cascade L3 mechanism scoring (with empirically-fit v6 weights including 11 sign-corrected dimensions). Cascade returns mechanism preferences, NDF profile, gradient priorities. Webhook captures conversions with HMAC + dedup, three-tier decision-context recovery, and tuple-level metadata (archetype, mechanism_sent, secondary_mechanism, edge_dimensions, gradient_priorities, barrier_diagnosed). When a conversion lands, BayesianPrior nodes update and the archetype-prior cache invalidates so the next cascade sees fresher numbers.

**What does NOT demonstrate the platform's narrative:**
- The construct-chain reasoning the foundation describes ("prevention focus → need for closure → authority") **is not materialized as a structured object at the live decision**. The atoms that would carry it are off-path. The cascade L3 produces scalar mechanism scores plus appended English strings in `result.reasoning` (A4 antipattern).
- The state×trait dynamic competition motif **is not implemented at the substrate combination sites** — additive throughout.
- The attention-inversion principle **is not enforced in selection** — `MECHANISM_TAXONOMY.{BLEND_COMPATIBLE, VIGILANCE_ACTIVATING}` exists but is unconsumed; selection is blind to whether a sampled mechanism activates vigilance or blends.
- The bilateral moat **is not visible at the surface** — copy is industry-default templates.
- The primary metaphor mechanism **is page-side only**; buyer-side, brand-side, and creative-side metaphor signal don't exist.
- DCIL Loop β **doesn't deliver directives to the operator** — three structural breaks.
- WhyLibraryEntries that DO get created derive from before/after verdicts (A5) and shape downstream priors.
- Per-user automatized memory overrides (Pinker dual-mechanism) **not implemented** — every decision re-derives from edges.

**Truthful one-line for partners or investors:** ADAM has a closed across-population reinforcement loop on its core BayesianPrior / RESPONDS_TO axis. The platform's deeper commitments — construct-chain reasoning, state×trait interaction, attention-inversion enforcement, bilateral creative output — are scaffolded but not yet conducting signal at the production surface.

This is not a launch-blocking finding. It is a **narrative-vs-implementation calibration**. Chris will need to decide which gaps are launch-blockers and which are post-pilot work.

---

## §3. Tier A — load-bearing concerns ranked by structural impact

### A1. Two parallel decision paths; the cognitive one is dead code on production

**Finding.** Production LUXY traffic flows: `POST /api/v1/stackadapt/creative-intelligence` → `CreativeIntelligenceService.get_creative_intelligence()` → `run_bilateral_cascade()` → cascade L1-L4. The 30-atom DAG (`atoms/dag.py`, atoms in `atoms/core/`) is invoked only by `CampaignOrchestrator._execute_atom_dag` (`campaign_orchestrator.py:716-877`), and `CampaignOrchestrator.analyze_campaign` is reached only from `demo/*` routes, `meta_learner/service.py`, `core/learning/orchestrator_learning_integration.py`, `retargeting/engines/diagnostic_reasoner.py`. **None of these is on the StackAdapt request path.**

**Why it matters.** The atoms with the strongest inferential grounding — `MimeticDesireAtom` (Girardian model selection with rivalry-risk penalty, `mimetic_desire_atom.py:190-225`), `AutonomyReactanceAtom` (theory-grounded coerciveness threshold, `autonomy_reactance.py:54-160`), `PersuasionPharmacologyAtom` (PK/PD-style absorption), `RegulatoryFocusAtom` (Higgins promotion/prevention assessment) — they exist, they're tested, they're not invoked. `MechanismActivationAtom._apply_edge_dimension_scoring` (`mechanism_activation.py:1696-1748`) literally **duplicates** the cascade L3 scoring formulas (`bilateral_cascade.py:961-1038`). When the foundation says "the inferential chain that produced 0.73 exists in the code's logic but is never materialized in the output," this is the literal architectural shape of that gap. The chain exists IN THE ATOMS; the decision is made BY THE CASCADE; the two never meet.

**Cited.** `adam/api/stackadapt/router.py:79-175` (entry); `adam/api/stackadapt/service.py:123-315` (handler); `adam/api/stackadapt/bilateral_cascade.py:2224-2339` (cascade); `adam/atoms/dag.py:107-415, 472-508` (DAG); `adam/orchestrator/campaign_orchestrator.py:716-877` (orphan caller).

### A2. State and trait couple additively across the substrate

**Finding.** At every load-bearing combination site:
- `personality_expression.py:437` — `expressed = min(1.0, max(0.0, base + context_mod + state_mod))`. File docstring claims "state-trait interaction (current state × stable traits)." **The math is additive.** Antipattern A4 + theoretical-frame violation in the same line.
- `compute_decision_probability` (`adam/intelligence/decision_probability.py:367-485`) — `P = σ(Σ wᵢ · match_i + Σ wⱼ · edge_congruenceⱼ + bias)`. Linear logit. Page modulates each match term as multiplicative gain `[0.75x, 1.25x]` per dimension — first-order modulation, no cross-terms.
- `bilateral_cascade.py:961-1038` — mechanism scores from edge dimensions are linear weighted sums (e.g., `authority = 0.30·construal_fit + 0.20·persuasion_conf + 0.15·(1-emotional) + 0.15·cognitive_load_tolerance + 0.10·information_seeking + 0.10·(1-autonomy_reactance)`).
- `page_edge_bridge.py:362` — `shifted[dim] = raw + page_delta`. Page (state) added to trait. Documented as "Bargh-correct" but mathematically `state + trait` shift, then linear scoring.

The 12 hardcoded interaction pairs at `bilateral_cascade.py:1086-1095` are present and theoretically motivated, but cap at ±8% adjustment on top of dominant additive main effects.

`gradient_fields.py:165-168, 304-369` computes proper second-order interaction terms via OLS with R²-improvement gating (only kept if ΔR² > 0.005). **These interaction terms are consumed only at `gradient_fields.py:540-552` for expected-lift estimation.** Grep for `gradient.interaction_terms` outside `gradient_fields.py` returns zero hits. **The single piece of code that captures non-additive structure is dead-ended for in-decision use.**

**Why it matters.** This IS the failure mode the theoretical foundation §2.5 names. The platform's deepest commitment — that ADAM operationalizes the dynamic-competition motif (Bargh × Pinker × Ridley × Dawkins) — is asserted in claims-in-comments and contradicted by the math at the load-bearing combination sites.

### A3. Construct accessibility (Bargh's primed-construct surface) is absent

**Finding.** Searches for `primed_construct`, `construct_priming`, `chronic_accessibility` return zero hits. Bargh's auto-motive model requires a representation of which constructs are currently primed at which strength, separately from chronic trait values. The platform's proxies:
- `goal_activation.py` — page-derived "goal scores" (closest analog; Bargh-correct in structure but not in scope — represents page-activated goals, not a full primed-construct accessibility surface)
- `page_edge_bridge.py:362` — collapses page activation into a 20-dim shift vector that gets ADDED to the buyer's trait dimensions. Treats page activation as a temporary trait modification rather than as a separate accessibility surface that interacts with traits.
- `theory_schema.py:108-228` — labeled `PsychologicalState` but defined as NDF threshold poles. **Mislabel that propagates into `_determine_active_states` (`graph/zero_shot_transfer.py:53`) and into `chains.active_states` rendering.**

**Why it matters.** Until there is a primed-construct surface separate from chronic trait values, the platform cannot honestly claim to operationalize the Bargh frame at the moment-to-moment timescale. The "states" in the schema are traits.

### A4. Primary metaphor — load-bearing per the foundation, dead-ended in implementation

**Finding.**

| Where | Status |
|---|---|
| Page-side scorer (`claude_feature_scoring.py:80-89, 319-392`) | **Implemented.** 8 axes, Lakoff-grounded, density + axis profile + confidence |
| Storage on Author/Publication/Article/Section/Topic nodes (`entity_graph.py:313-385`) | **Implemented.** |
| Buyer-side review annotation | **Zero metaphor scoring.** `prompt_templates.py` scores none of the 8 axes |
| Brand-copy-side annotation | **Zero metaphor scoring.** |
| Bilateral edge dimension | **No metaphor dimension** in the 27-dim alignment edge |
| Creative-side scorer | **Not implemented.** Only dataclass shape exists in `blend_fit.py:98-100` |
| `compute_blend_fit` | **Implemented; zero production callers.** Cosine similarity over 8-axis profile rescaled by both confidences (`blend_fit.py:273-282`) |
| `MECHANISM_TEMPLATES` (copy emitter) | **Does not encode metaphor.** |
| Retargeting prompt (`argument_generation.py:73-115`) | **Does not name metaphor as a generation constraint.** |

**Why it matters.** The foundation document treats primary metaphor as load-bearing (§2.4); MEMORY entries treat it as Chris's own doctoral research output. Of all gaps surfaced, this is the one most directly contradicted by the architectural narrative. The page-side scorer is real; everything downstream of it is silent.

### A5. DCIL pipeline (Loop β) cannot deliver directives — three independent failures

**Finding.**

1. **`adam.infrastructure.redis_client` module does not exist.** 20 importers (8 DCIL tasks, dcil_bridge, deployment_service, etc.) call `from adam.infrastructure.redis_client import get_redis`. The module file is missing. Every Redis touch from these tasks raises `ImportError`. Tasks 23, 25, 27, 28, 29, 32 are silently no-op'ing their persistence layer.

2. **`dcil_bridge.sync_directives_to_postgres` is orphaned.** Defined at `adam/api/admin/services/dcil_bridge.py:27`. Zero callers across `adam/` and `scripts/`. The bridge from Redis (Task 28 output) → Postgres `dcil_directives` table (dashboard input) is unbuilt. Validated directives sit in Redis until eviction; the dashboard recommendation queue stays empty for DCIL source.

3. **`management.db.campaigns` table is empty.** `dcil_directives.campaign_id` has FK to `campaigns(id)`. Live StackAdapt campaigns are not registered in management.db. Even if (1) and (2) were fixed, every directive insert would fail FK constraint.

**Why it matters.** Slice A1/B/D1/D2/D3 work shipped this week depends on `dcil_directives` having rows. The full chain is broken at three points before the dashboard ever sees content. **Patching task_23 (which I did this session) only restores the data input; it does not close the chain.** Three more independent fixes are required.

---

## §4. Tier B — system does the right thing for the wrong reason or with insufficient evidence

### B1. Bilateral architecture collapses at the partner-visible surface

**Finding.** Bilateral pairing is implemented at L3 of the cascade. `compute_brand_buyer_edge` (`match_calculators.py:663-1079`) consumes both sides and computes 27+ alignment dimensions; v6 weights at `:945-975` are empirically fit to LUXY data with sign corrections (11 dimensions inverted from intuitive direction).

The actual emitted copy is a four-template f-string library:
- `_gain_hook` returns `f"Discover the benefits of {product}."`
- `_loss_hook` returns `f"Don't miss out on {product}."`
- `_abstract_body` returns `"Experience the difference and transform your approach."`
- `MECHANISM_TEMPLATES` (`copy_generation/service.py:83-100`): hardcoded f-string lookup keyed on mechanism name
- `TONE_MODIFIERS` (`:103-120`): four-key dict of power-words

A14 antipattern A1 (rule-based generator) + A4 (hand-composed epistemic surface) + A10 ("Don't miss out... limited time only!" management-tool vocabulary) in a single file.

`ConstructCreativeEngine` exists (`construct_creative_engine.py:128-265`) and converts construct activations to a `CreativeSpec`, but **flattens the spec back to the same Layer-1 parameters via `to_copy_params`** (`:100-121`). Bilateral signal influences scalar floats; the final string is template-composed.

`ClaudeArgumentEngine` (`retargeting/engines/claude_argument_engine.py:77-200`) is the only place a generative model receives the full bilateral edge dict, archetype, diagnosed barrier, and touch history and returns headline + body + CTA + factual_claim. **Zero callers.** The `__init__.py:28` claims `CopyGenerationService` "delegates to ClaudeArgumentEngine"; that delegation is aspirational.

**Why it matters.** The bilateral moat — buyer psychology from reviews, seller psychology from brand copy, alignment between them as the operative signal — is invisible at the surface a partner or end-user encounters. ADAM ships LUXY with copy that is psychology-grounded *in mechanism choice* (correctly bilateral) wrapped in industry-default copy templates (unilateral, hand-composed).

### B2. Causal adjudicator is A5 antipattern feeding defensive priors

**Finding.** `adam/intelligence/causal_adjudicator.py:121, 135, 184, 237, 250` — three evaluators (`_evaluate_pause_campaign`, `_evaluate_zero_conversions`, `_evaluate_low_ctr`) compute before/after metric deltas and route to verdicts:
- `if cpa_then is not None and cpa_now < cpa_then * 0.7` → "user_right"
- `if cpa_now / advertiser_avg_cpa_now >= 3.0` → "system_right"
- `if convs_now > 0` → "user_right"
- `if ctr_now > ctr_then * 1.5` → "user_right"

Module docstring (`:10-14`) acknowledges: *"v1 makes a directional adjudication — real causal-inference would require holdouts."* Outcome nodes are written with `confidence=0.6`. Honest labeling.

**The Outcome nodes feed `WhyLibraryEntry` generation (`:635-638`).** WhyLibraryEntries are intended to act as defensive priors for future cascade decisions. So an A5-derived verdict materializes into a prior that influences subsequent decisions. **The correlational verdict has direct downstream causal-decision impact.**

A3 (text-blob Claim) compounds this: at `:543-552`, the "before" snapshot is regex-extracted from a natural-language string in `evidence_json.confident[].claim`. Comment at `:541-544`: *"Future: store a structured snapshot at decision time."* The Claim model lacks `test_definition`, so the adjudicator parses prose to recover comparison values.

**Why it matters.** This is rule #11 (the fitness function IS the ethics) at risk. The system selects against patterns that didn't recover *under whatever confounding was present* — indistinguishable from patterns the system was right to flag. Holdout-aware adjudication or operator-only adjudication for high-stakes patterns is the structurally correct fix; the operator path is shipped, but the auto path's verdicts still feed priors.

### B3. Processing-depth weighting is a magnitude multiplier, not a route classifier

**Finding.** `outcome_handler.py:142-184` classifies depth from viewability_seconds (weight=0.05 for unprocessed). Passed to Thompson (`:350`), Theory Learner (`:424`), Buyer profile (`:589`).

**The depth weight enters as a magnitude multiplier on `success`, not as a route classifier.** A click conversion under unprocessed (likely accidental tap) and a click conversion under deep engagement get the same *direction* of credit, only differing in *magnitude*. `signed_reward` (`:89-97`) does not stack processing_depth into its sign — comment at `:92-96` flags this as an open trade-off.

**Why it matters.** The platform's commitment per `project_attention_inversion_platform_core.md` — "outcome attribution must distinguish AUTOPILOT-route conversion from ATTENTION-route conversion" — is **not architecturally enforced**. A creative that grabs accidental taps via attention-trapping accumulates positive evidence at lower magnitude, but still positive evidence. Selection pressure does not yet differentiate the two routes. The blend-vs-vigilance mechanism taxonomy (`MECHANISM_TAXONOMY` exists, unconsumed) is the architectural complement to this fix.

### B4. Pinker memory-overrides-rules dynamic absent at the per-user timescale

**Finding.** L1/L2 are "memory" (accumulated population posteriors); L3 edges are "raw evidence"; the override is a fixed blend ratio (`l3_edge_prior_blend`, default likely 0.7), **not a reinforcement-driven dynamic balance**. The system has no machinery for "this archetype-category cell has been reinforced enough that memorized response now beats edge-derivation." Every decision re-derives from edges with no memorized shortcut.

The cascade composes correctly at the population level (Thompson, gradient fields, BayesianPrior), accumulates correctly per-user (BuyerUncertaintyProfile + BONG, 90-day Redis TTL), but **does not exhibit the dynamic competition between productive derivation and memorized response** that Pinker's lens demands.

**Why it matters.** The foundation §6 Pinker lens flags this as an open architectural question. It is one of the three timescales the platform claims to operate at; the other two close. This one is partially served by within-user posteriors but lacks the override mechanic.

### B5. The "27 dimensions" headline is a 20-dimension runtime

**Finding.** Code splits into 7 core + 13 extended = **20 dimensions** consumed in scoring (`bilateral_cascade.py:826-850`, `mechanism_activation.py:1297` "20-dim parity"). The "27" appears in marketing surfaces (`partner_api.py:1889`, `psychological_arbitrage.py:17`) but is not the runtime number. `compute_brand_buyer_edge` (`match_calculators.py:1028-1078`) returns 27 alignment fields including per-mechanism scores (which are not dimensions, they're mechanism outputs). The "27 dimensions" claim aggregates per-side annotation fields you'd need to score across user+peer+ad sides PLUS reasoning-tier constructs that aren't in any prompt — not the operative join count.

**Why it matters.** This is a vocabulary discipline issue more than a structural one, but it propagates into partner-facing materials and creates calibration risk in conversations.

---

## §5. Tier C — cleanup-deferrable but worth tracking

- **Three "learning" packages**: `adam/core/learning/` (canonical), `adam/learning/` (only `mechanism_interactions` actively imported), `adam/intelligence/learning/` (entirely orphaned). Naming chaos compounds drift surface.
- **Two `LearningSignalRouter` classes** with same name — one in `core/learning/universal_learning_interface.py:449`, one in `core/learning/signal_router.py:35`. `dependencies.py:223` imports the universal one but calls `register_consumer` which exists on neither (root cause of the "Learning components partially initialized" warning; see below).
- **Two cold-start packages**: `adam/cold_start/` (full active package) vs `adam/coldstart/` (singular legacy with only `unified_learning.py`).
- **Three construct ontologies**: `intelligence/construct_taxonomy.py` (claims 441 / 35 domains) vs `platform/constructs/models.py` (Pydantic, 12 domains) vs `intelligence/domain_taxonomy.py`.
- **Migration runner never invoked from startup**. `infrastructure/neo4j/migration_runner.py:run_migrations` has no caller in main.py / dependencies.py. Direct cause of empty SYNERGIZES_WITH/ANTAGONIZES (zero edges in Aura). 004_seed_mechanisms.cypher and 027_recommendation_class.cypher need manual invocation.
- **`register_consumer` AttributeError silently degrades 6 consumers** — they're constructed but never registered with the signal router (`dependencies.py:517` calls a method that exists on neither LearningSignalRouter class). Posteriors update because Thompson sampler is its own singleton; broader fan-out is dead.
- **3 task files exist but not scheduler-registered**: task_16 (page_gradients), task_17 (copy_evolution), task_33 (decay_adjudicator). Callable from dashboard on-demand; don't fire daily.
- **`recommendation_class/` 12-module primitive is orphan**. The deliverable of structural weakness #4. Migration `027_recommendation_class.cypher` exists but never runs; no external production caller.
- **Multiple state/page system duplication**: `reader_position` (impression_state_resolver) vs `page_profile` (page_intelligence) running simultaneously with comparison instrumentation but no resolution (`bilateral_cascade.py:1850-1888`).
- **Stale test**: `tests/integration/test_full_system.py:222` asserts `len(DEFAULT_DAG_NODES) == 14`; production has 30. Test would fail or has been silently skipped.
- **Hardcoded API key fallback** at `adam/integrations/stackadapt_monitor.py:82`. Should rely on env var only.

---

## §6. Day-1 closure map for the LUXY pilot

For the system to behave on Day-1 in the manner the foundation document describes, here are the gaps grouped by how blocking they are.

### Tier 0 — already closed today

✓ Bilateral cascade L3 fires for LUXY (6.74M edges available, BayesianPrior nodes, RESPONDS_TO populated by daily evolution)
✓ Webhook + outcome handler + BayesianPrior update loop is closed
✓ 90-day buyer profile cache (within-user lifetime)
✓ Population-level posteriors (Thompson, gradient fields)
✓ Goal activation model (page → goals → mechanism modulation), Bargh-correct, with three-level Bayesian learner
✓ Operator-led horizon adjudication (Slice D2)
✓ task_23 substrate (just patched — per-campaign metrics now real)

### Tier 1 — recommended pre-pilot closures

These are the items that, if left open, mean the pilot demonstrates LESS than the foundation document claims.

1. **Wire the construct atoms into the production decision path** (or, alternatively, document that the atoms are research surfaces and the cascade L3 formulas are the production decisioner). Status quo creates a partner-facing risk if anyone asks "is mimetic desire or autonomy reactance considered for this LUXY decision?" — the answer for live traffic today is no.
2. **Replace at least the topmost copy emitter with `ClaudeArgumentEngine` for first-touch placements** — even one bilateral-informed copy path on the production surface validates the moat claim. Today's copy is `"Discover the benefits of LUXY Ride. Built with quality materials and expert design. Learn more now - limited time only!"` from f-string templates; this is industry-default output with archetype-shaped scalars.
3. **Implement at least one of: state×trait interaction at the `compute_decision_probability` site, OR consume `gradient_fields.interaction_terms` in cascade L3 scoring.** The interaction signal is computed and discarded; one of these two paths needs to actually affect a decision number.
4. **Close DCIL Loop β** — three independent fixes: create/restore `adam.infrastructure.redis_client` module, wire `dcil_bridge.sync_directives_to_postgres` into the daily scheduler (task_29 → task_29.5 bridge → task_30), populate `management.db.campaigns` from StackAdapt at startup. Without these, the dashboard recommendation queue stays empty for DCIL source even after operator review work shipped this week.
5. **Fix `register_consumer` → `register_component`** at `dependencies.py:517`. Six consumers (cold_start_learning, multimodal, feature_store, temporal, verification, emergence_detector) are silently unregistered with the signal router. This is a one-line fix with broad fan-out impact.
6. **Invoke the migration runner from startup OR document manual invocation as a deployment step.** Empty SYNERGIZES_WITH/ANTAGONIZES means Portfolio optimization at `outcome_handler.py:568` writes into a graph layer that no decision path is reading.

### Tier 2 — in-flight or post-pilot

- Construct accessibility surface (Bargh primed-construct representation distinct from chronic trait)
- Buyer-side and brand-copy-side primary metaphor scoring
- Creative-side metaphor scorer (closes `compute_blend_fit`)
- `MECHANISM_TAXONOMY` blend-vs-vigilance split → consumed in selection
- Auto-adjudication scheduler call site (Loop γ closure; structurally hard because of A5 risk)
- `bilateral_ok` proxy → typed grounding evidence propagation through cascade → atom-DAG → outcome-handler
- Pinker memory-overrides-rules per-user dynamic
- Three "learning" packages consolidation
- Stale `test_14_atoms` test (or DAG fixed at 30 in test fixtures)
- WhyLibraryEntry corroboration mechanic (`warning_posterior_observations` increment instead of new-entry-per-corroboration)

---

## §7. Causal-vs-correlational architecture compliance

A direct read against the orientation document's antipatterns and the theoretical foundation's commitments.

| Commitment | Status | Evidence |
|---|---|---|
| Inferential, not correlational | **Partial.** Substrate edge dimensions are empirically fit (genuinely inferential at dimension level). Mechanism scoring is linear weighted sum (additive, not interactive). 12 hardcoded interaction-pair adjustments cap at ±8%. | `bilateral_cascade.py:961-1095` |
| Bilateral | **Real at L3, broken at L1/L2/L4, broken at copy** | `match_calculators.py:663-1079` (real); `bilateral_cascade.py:1379-1441` (L4 ad-side only); `copy_generation/service.py:83-451` (templates) |
| Three-timescale | **Population + lifetime closed, moment partial, no Pinker memory-rules** | Population: Thompson + gradient. Lifetime: BuyerUncertaintyProfile. Moment: goal activation real, StateTrajectoryModeler orphan. Pinker dynamic: not implemented. |
| State × trait interaction | **Asserted in docs, additive in math** | `personality_expression.py:437`; `decision_probability.py:367-485`; `bilateral_cascade.py:961-1038`; `page_edge_bridge.py:362` |
| Construct accessibility (Bargh) | **Not represented as first-class concept** | Zero hits for `primed_construct`/`construct_priming`/`chronic_accessibility`; `theory_schema.py:108-228` mislabels traits as states |
| Attention-inversion | **Mechanism taxonomy split exists but unconsumed; processing-depth as multiplier not classifier** | `mechanism_taxonomy.py:74-150`; `outcome_handler.py:142-184` |
| Primary metaphor | **Page-side scorer real; everything else dead-ended** | `claude_feature_scoring.py:80-89, 319-392`; everything downstream |
| A5 (before/after labeled causal) | **Active in causal_adjudicator with honest labeling** | `causal_adjudicator.py:121, 135, 184, 237, 250` |
| A4 (hand-composed epistemic surface) | **Active in copy_generation; cascade reasoning strings** | `copy_generation/service.py:83-120, 412-451`; `bilateral_cascade.py:1363-1371` |
| A1 (rule-based recommendation) | **Active in copy_generation MECHANISM_TEMPLATES; threshold generators (A14-flagged)** | `copy_generation/service.py:83-451`; `dashboard/service.py:361-657` |

---

## §8. Architectural concerns ranked by foundation-narrative-vs-implementation gap

Where the codebase narrative most diverges from production reality:

1. **Construct atoms exist; they're not invoked at production decision time.** (A1, B1)
2. **State × trait combination is additive across the substrate, not interactive.** Foundation §2.5 names this as the correlational failure mode.
3. **Primary metaphor is page-side only; the load-bearing mechanism per foundation §2.4 is downstream-dark.**
4. **Bilateral cascade output reaches partners as f-string-template copy.**
5. **Causal adjudicator's A5 verdicts feed defensive priors that influence subsequent decisions.**
6. **Construct accessibility (Bargh) has no first-class representation.**
7. **DCIL Loop β cannot close — three independent structural breaks.**
8. **Processing-depth weighting biases magnitude not direction; attention-trapping mechanisms accumulate positive evidence.**

---

## §9. What this audit does NOT cover

- **Verification of Aura graph contents.** The audit assumes the documented edge counts (6.74M LUXY, 11.8K airline, 1.9M GranularType nodes) exist in Aura. Per session findings, Neo4j labels `:Deviation`, `:Recommendation`, `:Outcome`, `:WhyLibraryEntry` are absent locally; whether they exist on Aura needs separate verification.
- **Test coverage gaps.** Beyond the stale `test_14_atoms` and the new substrate regression tests added this session, the broader test surface was not audited.
- **Performance / latency profile.** The latency budgeting (`LATENCY_TOTAL_MS=120`, etc.) and prefetch budget were not exercised.
- **Privacy / consent / identity-graph correctness.** `adam/identity/`, `adam/privacy/` — not audited in this pass.
- **End-user (consumer) UI vs reporting (agency) UI vs superadmin UI** — Chris flagged front-end legibility as a separate phase; the audit focuses on backend / decision / learning architecture.

---

## §10. Per-agent reports (full citations preserved)

The five agent reports are reproduced below in full. Each is independently grep-able by file path or claim.

### §10.1 Fit-Determination Flow Audit

[See `Agent 1` output — content in conversation transcript]
Top concerns from this slice: (a) Two parallel mechanism-selection systems with no shared output, only one of which is live (cascade L3 vs 30-atom DAG; the live path duplicates atom code); (b) Construct-chain reasoning is composed English in `result.reasoning`, not structured; (c) Bilateral split breaks at copy generation despite L3 preserving it.

### §10.2 State vs Trait Architecture Audit

Top concerns: (a) State and trait coupled additively at `personality_expression.py:437`, `page_edge_bridge.py:362`, `compute_decision_probability` linear logit; gradient interaction terms computed but discarded for in-decision use; (b) Construct accessibility absent as a first-class concept; (c) Three-timescale claim partially fulfilled (population + lifetime closed; moment partial; Pinker memory-rules absent).

### §10.3 Language Modeling Pipeline Audit

Top concerns: (a) Primary metaphor is one-sided (page) primitive — buyer-side, brand-copy-side, bilateral-edge, creative-side metaphor signal all absent; (b) Actual copy emitter is four-template f-string library (A1 + A4 + A10 in one file); (c) Three load-bearing primitives shipped as orphans behind A14 flags (compute_blend_fit, MECHANISM_TAXONOMY, score_page_features).

### §10.4 Learning Loop Audit

Top concerns: (a) `bilateral_ok` proxy at `campaign_orchestrator.py:790-804` accepts L1/L2-only chains as GROUNDED, opening all posterior paths; (b) Auto-adjudication is A5 by mechanism with honest labeling, but Outcome nodes feed defensive priors; (c) "Learning loop" is structurally three loops in different states of closure — only Loop α closed.

### §10.5 Wiring & Day-1 Readiness Audit

Top 5 day-1 wiring concerns (ranked):
1. `adam.infrastructure.redis_client` module missing — 8 DCIL tasks ImportError on every Redis touch
2. dcil_bridge orphaned — DCIL output never reaches `dcil_directives` table
3. `management.db.campaigns` empty — FK gate blocks directive insert
4. `register_consumer` AttributeError silently degrades 6 consumers
5. 30-atom DAG bypassed on production path — atoms are demo/research surface

---

## §11. Suggested next moves

These are findings, not actions. Chris will direct what to attack first. For prioritization purposes, here is how the items map to "ship-blocker / pre-pilot / post-pilot":

**Ship-blockers (only if the goal is for Day-1 to demonstrate the foundation's claims, not just to ship):**
- Fix `register_consumer` typo — 1-line fix; 6 consumers come online (Tier 1 #5)
- Wire `redis_client` (one canonical module) — unblocks 8 DCIL tasks (Tier 1 #4 part 1)
- Wire `dcil_bridge` into scheduler + populate `management.db.campaigns` (Tier 1 #4 parts 2-3)
- Either route production traffic through the 30-atom DAG OR document the cascade L3 path as the production decisioner (Tier 1 #1) — the second is faster but reframes the platform narrative

**Pre-pilot if appetite exists:**
- One bilateral-informed copy path live (Tier 1 #2): wire `ClaudeArgumentEngine` into `CopyGenerationService` for first-touch placements
- Consume `gradient_fields.interaction_terms` in cascade L3 OR add interaction terms at `compute_decision_probability` (Tier 1 #3)
- Migration runner invoked at startup (Tier 1 #6)

**Post-pilot, in scheduled order per Tier 1 backlog:**
- Construct accessibility surface (B-tier)
- Buyer-side + brand-copy-side metaphor scoring (A4)
- Creative-side metaphor scorer (closes blend_fit)
- MECHANISM_TAXONOMY consumed in selection
- Auto-adjudication scheduler with holdout-aware reasoning
- `bilateral_ok` typed-grounding-evidence propagation
- Pinker memory-overrides-rules per-user dynamic
- Three-learning-packages consolidation

---

**End of audit.**

This document is a snapshot at 2026-04-26. Code changes from this session (cebec5e, 8228a76, f11711c) are reflected in findings. Items flagged as orphaned were verified by grep at audit time; verify before acting.
