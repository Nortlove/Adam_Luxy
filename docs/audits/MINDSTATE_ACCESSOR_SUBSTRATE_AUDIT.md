# Mindstate Accessor Substrate Audit
## Slice ID: M.0
## Session: 2026-05-08 (continuation)
## Predecessor: b1c9922 (W.2c — W chain closed pre-mindstate)
## Audit type: Read-only inspection
## Branch: feature/hmt-dashboard

---

## §1 Executive Summary

The mindstate substrate gap is **larger** than W.0 Q20 articulated, but the **fix path is smaller** than W.0 Q20 implied. Two findings reframe the pilot launch decision:

1. **`extract_mindstate_vector` is NEVER called from the bid path.** The function exists at `adam/retargeting/resonance/mindstate_vector.py:71` but is invoked only from `adam/core/learning/outcome_handler.py:929` and `:1223` (post-conversion learning paths). The bilateral cascade contains zero `PageMindstateVector(` constructions; only two comment references at `adam/api/stackadapt/bilateral_cascade.py:2537` and `:2898`. **No PageMindstateVector instance ever flows through the bid-time path.** W.2c's `mindstate_accessor=lambda buyer_id, url_hash: None` lambda stub is **structurally honest** about this — there's nothing to wire to.

2. **The C+D `@property` derivations live in the wrong architectural location.** They're defined on `PageMindstateVector` (`adam/retargeting/resonance/models.py:200, 236, 282`) but their inputs come from sources OTHER than the page profile that `extract_mindstate_vector` consumes. The W.0 Q20 framing said "orchestrator-populated fields aren't populated by extract_mindstate_vector" — true, but more deeply, **the orchestrator-populated fields don't have a producer anywhere in the bid-time path**. They were specified anticipating a separate population step that was never built. The cells aggregator (`adam/cells/aggregator.py:142-161`) reads composite properties via `getattr(mindstate, "fomo_score", 0.0) or 0.0` from a mindstate that's always None — so the composites silently default to 0.0 and the FOMO + ownership predicates silently never fire.

**Per-composite outcomes (Pass 4 mapping):**

| Composite | Inputs | Outcome | Reason |
|---|---|---|---|
| `fomo_score` | arousal × scarcity_frame × regulatory_focus_modifier | **OUTCOME-A** | All 3 inputs already on PagePrimingSignature (W.1-wired). No PMV reconstruction needed — derive directly in aggregator. ~30 LOC fix. |
| `depletion_proxy` | cognitive_load × session_position_normalized | **OUTCOME-A** | cognitive_load_estimate on PagePrimingSignature (W.1-wired); session_position via SessionStateTracker singleton (`adam/intelligence/session_state.py:309`) — exists, not yet bid-cascade-wired. ~80 LOC. |
| `psych_ownership_proxy` | touch_density × dwell_normalized × presentness | **OUTCOME-C** | touch_count + dwell_seconds require new per-user-per-brand telemetry surface — not cached at bid time anywhere. Substantial substrate-side build. |

**Pilot launch sequencing recommendation: OPTION BETA — ship M.1 (fomo aggregator-side derivation) pre-pilot; defer M.2 (depletion wire) and M.3 (ownership substrate build) to post-pilot iteration.** Rationale in §9.

**Pass 6 hypothesis result: REJECTED with caveat.** Hypothesis was "fomo_score may already fire on real data via W.1 priming wiring." Reality: fomo_score's INPUTS are W.1-wired on PagePrimingSignature, but the COMPOSITE is consumed by the aggregator from a `mindstate` object that's always None. **fomo_score is structurally reachable in 30 LOC of aggregator-side computation but is not firing today.** This is the most consequential finding — pilot can ship 5/6 predicates firing (current state is actually 3/6, not the W.2c EVE's optimistic 5/6) with a tiny aggregator-side change rather than the substantial substrate-side build W.0 Q20 implied.

**3 QUESTION-and-stop concerns** for Claude Proper adjudication: (Q29) BETA vs GAMMA pilot adjudication; (Q30) the W.2c EVE's "5 of 6 fire on real data" framing was overcounted (real number is 3/6); (Q31) whether to revise C+D `@property` placement (move OFF PageMindstateVector and ONTO CellFeatureSet/aggregator) as a substrate-side simplification rather than continuing to populate orchestrator-populated PMV fields nobody writes to.

---

## §2 Pass 1 — PageMindstateVector construction at bid time

**Function signature.** `extract_mindstate_vector(page_profile: Any, url: str = "", domain: str = "") -> PageMindstateVector` at `adam/retargeting/resonance/mindstate_vector.py:71-93`.

**What it populates.** The 32-dim resonance vector fields:
- 20 `edge_dimensions` — from `page_profile.edge_dimensions` (line 101)
- 7 `ndf_activations` — from `page_profile.construct_activations` (line 107)
- `mechanism_susceptibility` — from `page_profile.mechanism_adjustments` (line 112)
- 5 environmental scalars (`emotional_valence`, `emotional_arousal`, `cognitive_load`, `publisher_authority`, `remaining_bandwidth`) — from `page_profile` direct attributes (lines 115-119)
- Metadata: `url_pattern`, `domain`, `confidence`, `scoring_tier`

**What it does NOT populate** (defaults to PageMindstateVector's per-field defaults):
- C-era orchestrator-populated fields: `scarcity_frame_present` (False), `regulatory_focus_priming` ("neutral"), `touch_count` (0), `dwell_seconds` (0.0)
- D-era orchestrator-populated fields: `session_position_seconds` (0.0), `posture_class` (""), `browsing_momentum` (0.5)

**All 3 C+D `@property` composite derivations evaluate to 0.0 on a freshly-extracted PMV** because their inputs are at the safe-defaults that yield zero (e.g., `scarcity_frame_present=False` → `fomo_score=0.0`).

**Bid-time call site.** **NONE.** Verified via:
- `rg -n "extract_mindstate_vector" adam/` returns matches only at `mindstate_vector.py:71` (definition), `outcome_handler.py:929`, `outcome_handler.py:1223` (both LEARNING paths, not bid-time).
- `grep -n "PageMindstateVector\|mindstate" adam/api/stackadapt/bilateral_cascade.py` returns 2 matches at lines 2537, 2898 — **both are comments**. Zero PMV constructions in cascade.

**Implication.** The bid path has access to the underlying `PagePsychologicalProfile` via `_get_page_intelligence_cache().lookup(page_url)` (used elsewhere in `bilateral_cascade.py` at the posture × mechanism modulation block) — so PMV reconstruction at bid time is **technically feasible** without any new infrastructure. But the bid path does not currently do it.

---

## §3 Pass 2 — Orchestrator-populated input field state

For each of the 7 C/D-era orchestrator-populated fields on PageMindstateVector, current bid-time population state:

| Field | Source spec | Bid-time populator? | Evidence |
|---|---|---|---|
| `scarcity_frame_present` | `"scarcity" in PagePrimingSignature.activated_frames` | **NONE** | `rg "scarcity_frame_present" adam/` — only models.py definition site. Zero writers anywhere. |
| `regulatory_focus_priming` | `PagePrimingSignature.regulatory_focus_priming` | **NONE** to PMV. PagePrimingSignature has it (W.1-wired); `cells/aggregator.py:238` reads it via `getattr(priming, "regulatory_focus_priming", "neutral")`. PMV never gets it transferred. |
| `touch_count` | retargeting per-user-per-brand telemetry | **NONE** at bid time. Used in `behavioral_analytics/engine.py:1141`, `multimodal_extension.py:226+358`, `gradient_bridge_integration.py:181` — all post-event/learning paths. No bid-time cached surface for per-user-per-brand touch counts. |
| `dwell_seconds` | retargeting per-user-per-brand telemetry | **NONE** at bid time. `engines/signal_processors.py:220-221` aggregates from sig.metadata (post-event). No bid-cached surface. |
| `session_position_seconds` | `SessionStateTracker.get_session(buyer_id).session_duration_seconds` | **NONE** to PMV. SessionStateTracker exists at `intelligence/session_state.py:180` with singleton `get_session_tracker()` at `:309`; cascade does NOT call it (verified `grep "session_tracker\|get_session_tracker" adam/api/stackadapt/bilateral_cascade.py` returns nothing). |
| `posture_class` | URLPostureClassifier 5-class taxonomy | **NONE** of the 5-class. Cascade uses `categorize_posture()` (the **4-class** `attentional_posture_substrate`, not the 5-class `FIVE_CLASS_POSTURES`) at `bilateral_cascade.py:3173, 3789` — writes into `_page_features["posture_class"]` and `_dual_page_features["posture_class"]` for downstream cell selection. **Vocabulary mismatch:** PMV docstring expects 5-class (per S6.2 Pass C orthogonality finding); cascade emits 4-class. Even if wired, would need transcoding. |
| `browsing_momentum` | `BrowsingMomentumTracker.get_momentum(buyer_id).score` | **NONE** to PMV. Tracker IS called in cascade (`bilateral_cascade.py:2542-2554`) — writes into `result.context_intelligence["browsing_momentum"]`, NOT into a PMV instance. So data is reachable at bid time, just not flowing into a PMV. |

**Confirmation of W.0 Q20:** correct that these fields aren't populated by `extract_mindstate_vector`. **Extends Q20:** they aren't populated by ANY bid-time code path. The W.0 framing implied the gap was an integration step missing from `extract_mindstate_vector`; the actual situation is that no bid-time PMV instance exists at all.

---

## §4 Pass 3 — Session-telemetry surface inventory

Session-level signals on the platform:

| Surface | Computed where | Cached where | Bid-time access? | Latency |
|---|---|---|---|---|
| `SessionState` (incl. `session_start`, `session_duration_seconds`) | `intelligence/session_state.py:180` (`SessionStateTracker.observe(buyer_id, ...)`) | In-process `_sessions: Dict[buyer_id, SessionState]` (line 188) — no Redis backing | **YES via `get_session_tracker().get_session(buyer_id) -> Optional[SessionState]`** at `intelligence/session_state.py:274`; sync, dict lookup. | <1μs. |
| `BrowsingMomentum` (`score`, `pages_in_session`, `confidence`) | `retargeting/resonance/browsing_momentum.py:71` (`BrowsingMomentumTracker.record_pageview`) | In-process `_sessions: Dict[buyer_id, BrowsingMomentum]` (line 87) | **YES via `get_browsing_momentum_tracker().get_momentum(buyer_id) -> Optional[BrowsingMomentum]`** at line 144; sync, dict lookup. | <1μs. **Already wired in cascade at line 2542-2554**, but writes to `result.context_intelligence` not into a PMV. |
| Per-user-per-brand `touch_count` | `behavioral_analytics/engine.py:1141`, `multimodal_extension.py:226+358` | NO bid-time cache; aggregated from event streams in post-conversion paths | **NO.** Would need: per-user-per-brand telemetry cached at bid time (Redis `touches:{buyer_id}:{brand_id}` pattern). New surface. | n/a — doesn't exist. |
| Per-user-per-brand `dwell_seconds` | `engines/signal_processors.py:220-221` (post-event aggregation) | NO bid-time cache | **NO.** Same situation as touch_count. | n/a. |
| `_dual_page_features["posture_class"]` (4-class attentional posture) | `bilateral_cascade.py:3789` via `categorize_posture()` | In-cascade local variable | **YES — already in cascade scope** but as 4-class vocabulary; would need 4→5 transcoding to feed PMV's `posture_class` field. | <1μs (already computed inline in cascade). |
| `PagePsychologicalProfile` (full) | `intelligence/page_intelligence.py` profile pipeline | `PageIntelligenceCache` singleton at `page_intelligence.py:2157` | **YES via `get_page_intelligence_cache().lookup(page_url)`**; sync. | <1ms (in-memory LRU). Already used at cascade line 3173+. |

**Implication.** Of the 7 PMV orchestrator-populated fields, 5 are reachable at bid time via existing in-process singletons (`scarcity_frame_present`/`regulatory_focus_priming` from PagePrimingSignature W.1-wired; `session_position_seconds` from SessionStateTracker; `browsing_momentum` from BrowsingMomentumTracker; `posture_class` from cascade-local computation if 4→5 transcoding adds). The 2 that are NOT reachable are `touch_count` and `dwell_seconds` — both need new per-user-per-brand telemetry surfaces.

---

## §5 Pass 4 — Composite-to-substrate mapping

### `fomo_score` — `arousal × scarcity_frame × regulatory_focus_modifier` (`models.py:200-233`)

| Input | Source per spec | Status | Notes |
|---|---|---|---|
| `emotional_arousal` | PMV field, populated by extract_mindstate_vector from page_profile | **AVAILABLE-CACHED** | PagePrimingSignature.arousal also has it; W.1-wired. |
| `scarcity_frame_present` | PMV orchestrator field | **DEFAULTED (False)** in current PMV; **AVAILABLE-COMPUTE** from PagePrimingSignature.activated_frames (1-line check). |
| `regulatory_focus_priming` | PMV orchestrator field | **DEFAULTED ("neutral")** in current PMV; **AVAILABLE-CACHED** on PagePrimingSignature directly. |

**Outcome: A.** All 3 inputs derivable from PagePrimingSignature (W.1-wired). No PMV reconstruction needed if computed in aggregator; ~30 LOC.

### `psych_ownership_proxy` — `touch_density × dwell_normalized × presentness` (`models.py:236-279`)

| Input | Source per spec | Status |
|---|---|---|
| `touch_count` | PMV orchestrator field | **MISSING** — no bid-time cached surface anywhere (Pass 3 confirmed). |
| `dwell_seconds` | PMV orchestrator field | **MISSING** — no bid-time cached surface. |
| `temporal_horizon` | PMV `ndf_activations["temporal_horizon"]`, populated by extract_mindstate_vector from page_profile | **AVAILABLE-COMPUTE** if PMV constructed at bid time (1 PMV reconstruction). |

**Outcome: C.** 2 of 3 inputs MISSING; substantial substrate-side build (per-user-per-brand telemetry surface).

### `depletion_proxy` — `cognitive_load × session_position_normalized` (`models.py:282-323`)

| Input | Source per spec | Status |
|---|---|---|
| `cognitive_load` | PMV field, populated by extract_mindstate_vector | **AVAILABLE-CACHED** on PagePrimingSignature.cognitive_load_estimate (W.1-wired); **AVAILABLE-COMPUTE** from page_profile via PMV reconstruction. |
| `session_position_seconds` | PMV orchestrator field | **AVAILABLE-COMPUTE** via `SessionStateTracker.get_session(buyer_id).session_duration_seconds`; singleton ready, not bid-cascade-wired. |

**Outcome: A.** Both inputs reachable; M.2 wires SessionStateTracker singleton + computes inline.

---

## §6 Pass 5 — depletion_proxy specific assessment

Per D commit `14b9d73` formula CASE B (`cognitive_load × session_position_normalized`):

- **`cognitive_load`**: PagePrimingSignature.cognitive_load_estimate exists and is W.1-wired (aggregator reads at `cells/aggregator.py:127-128`). Also reachable on PMV.cognitive_load if PMV constructed.
- **`session_position_seconds`**: NOT populated on any PMV today. SessionStateTracker singleton exists at `intelligence/session_state.py:309` with `get_session(buyer_id).session_duration_seconds` property; cascade does NOT use the tracker.

**M.2 wire**: ~80 LOC across (a) sync wrapper accessor `make_session_position_accessor(session_tracker)` following W.1 lightweight-adapter pattern; (b) production_aggregator wiring; (c) inline computation of `depletion_proxy = cognitive_load_estimate × min(1, session_position_seconds / 1800)` in `cells/aggregator.py` (replacing the `getattr(mindstate, "depletion_proxy", 0.0)` no-op read).

**Note**: NO seed predicate currently consumes depletion_proxy (predicate inventory at `cells/predicates/`: fomo, ownership, maximizer, persuasion-resistance, compensatory). M.2 ships dormant substrate unless paired with a depletion-keyed predicate-authoring slice. Recommend: defer M.2 until depletion-keyed predicate is requested by pilot iteration data.

---

## §7 Pass 6 — fomo_score specific assessment

**Hypothesis (per directive)**: fomo_score may already fire on real data because all inputs come from PagePrimingSignature which is W.1-wired.

**Result: REJECTED, with reframing.** The INPUTS are W.1-wired on PagePrimingSignature, but the COMPOSITE is computed as a `@property` on PageMindstateVector which is never constructed at bid time. The aggregator at `cells/aggregator.py:142-145` reads:

```python
fomo = (
    float(getattr(mindstate, "fomo_score", 0.0) or 0.0)
    if mindstate else 0.0
)
```

`mindstate` is None per W.2c stub → `fomo` is 0.0 → both FOMO predicates (`high_fomo_promotion` at `predicates/fomo_predicates.py:33`, `high_fomo_prevention` at `:60`, both gated on `features.fomo_score > 0.7`) **never fire on real data today**.

**M.1 fix (smallest possible scope, ~30 LOC)**: Add inline computation in `cells/aggregator.py` after `priming` is fetched (before the `mindstate` block):

```python
# M.1 — fomo_score from PagePrimingSignature (bypasses PMV @property)
if priming is not None:
    arousal = float(getattr(priming, "arousal", 0.5) or 0.5)
    activated = getattr(priming, "activated_frames", ()) or ()
    scarcity_present = "scarcity" in activated
    reg = getattr(priming, "regulatory_focus_priming", "neutral")
    modifier = (1.2 if reg == "promotion"
                else 0.8 if reg == "prevention" else 1.0)
    fomo = max(0.0, min(1.0, arousal * (1.0 if scarcity_present else 0.0) * modifier))
else:
    fomo = 0.0
```

This bypasses the dead PMV @property entirely. **All 3 inputs already cached** (W.1 priming_accessor at `cells/accessors.py:make_priming_accessor`). No new infrastructure. Predicate-fire-rate gain: 2 predicates (high_fomo_promotion + high_fomo_prevention) become live.

**Note: this validates a substrate-side simplification path** — Q31 in §11 surfaces whether to revise the architectural placement of C+D `@property` derivations (move OFF PMV onto CellFeatureSet aggregator) as the cleaner long-term shape.

---

## §8 Pass 7 — psych_ownership_proxy specific assessment

Per C commit `fd1a95a` formula `touch_density × dwell_normalized × presentness`:

- **`touch_count`**: not cached at bid time. Behavioral_analytics computes from event streams post-conversion (`engine.py:1141`, etc.). Building a per-user-per-brand bid-time cache requires new Redis surface (e.g., `touches:{buyer_id}:{brand_id}` keyed) + write-through from event ingestion + read at cascade entry. Substantial.
- **`dwell_seconds`**: same situation as touch_count. Aggregated from sig.metadata in `signal_processors.py:220-221` (post-event); no bid-time cached surface.
- **`temporal_horizon`** (NDF dim): on PagePsychologicalProfile.construct_activations; reachable at bid time via `get_page_intelligence_cache().lookup(page_url)`. AVAILABLE-COMPUTE (~15 LOC if PMV reconstruction added or inline-computed in aggregator).

**Outcome: C.** 2/3 inputs MISSING. M.3+ requires substantial substrate-side build for the per-user-per-brand telemetry surface. **Recommend deferral to post-pilot iteration** — pilot data informs whether the ownership predicate would meaningfully differentiate outcomes before substrate investment.

The 1 ownership predicate (`high_psych_ownership` at `predicates/ownership_predicates.py:27`, gated on `features.psych_ownership_proxy > 0.55`) stays dormant under deferral.

---

## §9 Pass 8 — Pilot launch sequencing options

### OPTION ALPHA — ship M.1 + M.2 + M.3 pre-pilot

**Pilot launches with 6/6 predicates firing.** Requires: M.1 (fomo aggregator-side) + M.2 (session-position wire + depletion aggregator-side, plus depletion-keyed predicate authoring) + M.3 (per-user-per-brand telemetry surface build for ownership). Off the table because M.3 is OUTCOME-C — substantial substrate work that exceeds typical pre-pilot timeline.

### OPTION BETA — ship M.1 only pre-pilot; defer M.2 + M.3 post-pilot

**Pilot launches with 5/6 predicates firing** (cohort + PKM + maximizer + 2 FOMO; ownership dormant). M.1 is ~30 LOC of pure aggregator-side computation against already-wired PagePrimingSignature inputs — extremely low risk, no new substrate, fully testable. M.2 (depletion) defers because no current predicate consumes it; post-pilot iteration adds depletion-keyed predicate + M.2 wire together. M.3 (ownership) defers pending pilot evidence of value vs the substrate cost.

### OPTION GAMMA — defer all M.1+ post-pilot

**Pilot launches with 3/6 predicates firing** (cohort + PKM + maximizer; both FOMO + ownership dormant). All M-chain work becomes iteration substrate informed by pilot data on whether mindstate composites meaningfully differentiate outcomes.

### Recommendation: **OPTION BETA**

Rationale:
- **M.1 is essentially free** (~30 LOC, fully aggregator-side, all inputs already wired). Cost-to-ship is dominated by the test surface (~10-15 tests pinning fomo computation correctness + integration into CellFeatureSet flow), not the implementation. Risk of regression is minimal — bypasses the dead PMV `@property`, doesn't touch any locked surface.
- **M.1 enables 2 predicates** (high_fomo_promotion + high_fomo_prevention). FOMO is a well-grounded substrate (Cialdini scarcity + Pham-Higgins regulatory fit + Przybylski FOMO) and the predicates are differentiation-meaningful for promotion-oriented vs prevention-oriented users at scarcity-framed pages.
- **M.2 deferral is rational** — no current depletion-keyed predicate exists; shipping dormant depletion substrate is premature.
- **M.3 deferral is rational** — substrate cost is substantial (per-user-per-brand telemetry build); pilot data should inform whether the ownership signal is worth the build.

**BETA achieves the pilot completeness improvement (3/6 → 5/6 firing) at lowest possible cost.** If pilot timing permits no slice at all, GAMMA is acceptable but loses the FOMO predicate signal value at trivial savings (M.1 is much cheaper than any prior W slice). If pilot scope explicitly favors thesis-validation completeness, ALPHA could substitute M.3 with a temporary stub (psych_ownership computed from temporal_horizon only, ignoring touch_count/dwell — partially-meaningful signal pending substrate build).

---

## §10 Recommended M.1 Slice Sequence

### M.1 (recommended pre-pilot)

**Scope**: aggregator-side fomo_score derivation in `adam/cells/aggregator.py`.

**Components**:
1. Replace the `mindstate.fomo_score` getattr at `cells/aggregator.py:142-145` with inline computation from `priming` (already in scope at line 116).
2. Pin the formula constants (`FOMO_REGULATORY_PROMOTION_MODIFIER = 1.2`, `..._PREVENTION_MODIFIER = 0.8`, `..._NEUTRAL_MODIFIER = 1.0`, `FOMO_SCARCITY_FRAME_NAME = "scarcity"`) — either import from `adam/retargeting/resonance/models.py:69-78` or shadow as aggregator-local constants for module independence.
3. Tests in `tests/cells/test_aggregator.py` (extend existing) covering: scarcity present + promotion + arousal=0.8 → fomo=0.96; prevention same → 0.64; neutral → 0.80; scarcity absent → 0.0; both FOMO predicates fire end-to-end on populated PagePrimingSignature.
4. Schema-evolution check: existing `test_w2c` integration tests assume `fomo_score = 0.0` cold-start; verify behavior preserved when priming is None.

**Estimated**: ~30 LOC implementation + ~10-15 tests. Single commit per Appendix D.

### M.2 (deferred post-pilot)

Defer until depletion-keyed predicate is authored (no current consumer). When ready: ~80 LOC adding `make_session_position_accessor` wrapper + production_aggregator wiring + inline depletion_proxy computation. Pilot data informs whether the depletion signal warrants the wiring + predicate.

### M.3 (deferred post-pilot, possibly indefinitely)

Substantial substrate-side build for per-user-per-brand touch_count + dwell_seconds telemetry surface. Pilot data informs whether the ownership predicate's signal differentiation justifies the substrate cost. May ultimately not ship if other substrate channels prove sufficient.

### Optional follow-up: Q31 architectural simplification

If Q31 (§11) is adjudicated favorably, a follow-up M.x slice could move the C+D `@property` derivations OFF `PageMindstateVector` and ONTO `CellFeatureSet` (or compute them in the aggregator directly). This would clean up the dead-letter PMV orchestrator-populated fields and consolidate the bid-time substrate access pattern. Not pilot-blocking; cleanup work.

---

## §11 QUESTION-and-stop Concerns

### Q29 — BETA vs GAMMA pilot adjudication

M.1 is low-cost (~30 LOC) but adds a slice to the pre-pilot sequence. GAMMA ships pilot at current state (3/6 predicates firing on real data) and treats M-chain entirely as iteration substrate. BETA ships pilot at 5/6 firing with one additional small slice. Adjudication criteria:
- **If pilot timing is the binding constraint** → GAMMA (no additional slice)
- **If thesis-validation completeness matters** → BETA (FOMO is a well-grounded substrate worth the small slice)
- **If iteration evidence is preferred over substrate up-front** → GAMMA (let pilot data inform whether FOMO predicates differentiate outcomes before adding substrate)

Audit recommends BETA on cost-benefit ratio (the cost is very small relative to the predicate-fire-rate gain), but the recommendation is weak — GAMMA is fully reasonable.

### Q30 — W.2c EVE substrate-firing inventory was overcounted

W.2c EVE at b1c9922 stated "5 of 6 seed predicates fire on real bid data after W.2c." The actual current state is **3 of 6**:
- ✅ `compensatory_cohort_social_consumption` (cohort + posture wired)
- ✅ `high_persuasion_knowledge_skepticism_dampener` (PKM via PagePrimingSignature W.1-wired)
- ✅ `high_maximizer_comparison` (W.2c archetype + maximizer wired) — **only when archetype is non-default AND maximizer-evidence is high; otherwise dormant**
- ❌ `high_fomo_promotion` (mindstate=None → fomo_score=0.0 → never > 0.7)
- ❌ `high_fomo_prevention` (same)
- ❌ `high_psych_ownership_endowment_reinforce` (mindstate=None → psych_ownership_proxy=0.0 → never > 0.55)

The W.2c EVE's "5 of 6" framing assumed fomo_score reads through the @property derivation on a real PMV. Reality: aggregator reads from a None mindstate → 0.0. **No code is broken, but the firing-rate accounting was optimistic.** This is informational — no remediation needed beyond M.0 surfacing it.

### Q31 — revise C+D @property placement (architectural simplification)

The C+D @property derivations live on `PageMindstateVector` in `adam/retargeting/resonance/models.py:200-323`, but they consume orchestrator-populated PMV fields that have no bid-time producer. The cleanest long-term architecture is:

- **Option (a) — keep PMV @property derivations, build the orchestrator-side population layer.** Substrate-heavy. Restores the originally-intended architecture.
- **Option (b) — move @property derivations OFF PMV, ONTO CellFeatureSet (or compute in aggregator).** Substrate-light. PMV reverts to its pre-C/D shape (32-dim resonance vector only). Composites become CellFeatureSet @property derivations or aggregator inline computations. **Closest to BETA's M.1 path.**
- **Option (c) — leave the derivations on PMV as documentation; compute them functionally in the aggregator wherever they're needed.** Compromise — preserves the original architectural intent without forcing PMV bid-time construction.

Adjudication: if BETA / M.1 ships, option (b) or (c) becomes operationally implicit (the aggregator ends up computing fomo_score directly, and the PMV @property becomes dead code). Worth surfacing as a deliberate architectural choice rather than letting it drift implicitly.

---

## §12 Audit closure

State at standdown:
- Memo present at `docs/audits/MINDSTATE_ACCESSOR_SUBSTRATE_AUDIT.md`.
- Zero code changes; zero test changes.
- HEAD: `b1c9922` (W.2c). 19 slices closed (16 implementation + 3 audits). M.0 makes 4 audits.
- Pilot launch sequencing: BETA recommended (ship M.1 only, ~30 LOC, enables 2 FOMO predicates → 5/6 fire); GAMMA fully acceptable if pilot timing is binding.
- 3 QUESTION-and-stop concerns surfaced (Q29 BETA-vs-GAMMA, Q30 inventory accounting correction, Q31 architectural simplification).

Awaits Claude Proper adjudication on Q29-Q31 + pilot launch sequencing decision (BETA / GAMMA / ALPHA-with-stub). If BETA, M.1 prompt follows; if GAMMA, pilot launch sequence and M-chain becomes iteration substrate.
