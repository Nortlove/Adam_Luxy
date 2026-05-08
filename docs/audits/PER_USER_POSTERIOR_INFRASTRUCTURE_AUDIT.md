# Per-User Posterior Infrastructure Audit
## Slice ID: W.2.0
## Session: 2026-05-08 (continuation)
## Predecessor: e0f0e52 (W.1 — 5 substrate channels wired)
## Audit type: Read-only inspection (A.1.0 + A.2.0 + S6.2.0 + W.0 precedents)
## Branch: feature/hmt-dashboard

---

## §1 Executive Summary

Per-user posterior infrastructure is **substantially built but architecturally incomplete for W.2's two accessor signatures.** The Bayesian update pipeline (`apply_per_user_posterior_modulation` at `adam/intelligence/per_user_posterior_modulation.py:93`) is operational and already wired into `bilateral_cascade.py:3270`. The storage layer (`BuyerUncertaintyProfile` at `adam/intelligence/information_value.py:401` + `graph_cache.get_buyer_profile` at `adam/api/stackadapt/graph_cache.py:941`) provides sync access with Redis read-through/write-through (90-day TTL). The event-driven update path is wired through `outcome_handler._update_buyer_profile` at `adam/core/learning/outcome_handler.py:2520` and fires on conversion/click/engagement/impression/bounce events (weights 1.0/0.3/0.2/0.1/0.05).

**The gap is targeted and discrete:** (a) per-user **archetype assignment is NOT stored** anywhere (`BuyerUncertaintyProfile` has no `archetype` field; Neo4j User nodes have no `archetype` property; archetype detection at `service.py:720` is request-scoped and not persisted by buyer_id); (b) **maximizer_tendency is NOT in UNCERTAINTY_DIMENSIONS** (`information_value.py:113-136`), so no per-user Beta posterior is tracked for that trait — A.2's `ARCHETYPE_MAXIMIZER_PRIORS` stays at the archetype level, never bridged to per-user state. Recommended decomposition: **W.2 splits into 3 sub-slices** (W.2a archetype storage + cold-start auto-derivation; W.2b maximizer_tendency Beta wiring into BuyerUncertaintyProfile; W.2c the two accessor closures in `adam/cells/accessors.py` + `production_aggregator()` activation). 4 QUESTION-and-stop concerns surfaced, all about W.2-scope architecture decisions Claude Proper should adjudicate before sub-slices ship.

---

## §2 Pass 1 — per_user_posterior_modulation pipeline state

**EXISTS as a named pipeline.** Module: `adam/intelligence/per_user_posterior_modulation.py`. Entry point: `apply_per_user_posterior_modulation(mechanism_scores, buyer_id, graph_cache, mixing_weight=0.30)` at line 93.

- **Architecture**: online per-bid modulation using empirical-Bayes shrinkage. Formula at lines 13-18:
    `final_score = base_score + (stability · w) · (personal_affinity − base_score)`
  where `personal_affinity = mean(user_alignment[d] for d in mech.primary_dims)` and `stability = aggregate_confidence ∈ [0, 1]`.
- **Inputs**: `mechanism_scores` (cascade L1–L3 + cohort/posture modulation outputs); `buyer_id`; `graph_cache` (must expose `get_buyer_profile`); `mixing_weight` (default `MIXING_WEIGHT_DEFAULT = 0.30` at line 87).
- **Outputs**: modulated `Dict[str, float]` mechanism_scores, clipped to `[SCORE_FLOOR, SCORE_CEILING] = [0.0, 1.0]` (lines 89-90, 248-251).
- **Persistence**: pipeline does NOT persist; it READS from `graph_cache.get_buyer_profile(buyer_id)` and applies shrinkage in-place. Persistence is a separate concern (Pass 7).
- **Cold-start bypass**: line 140 `if profile.total_interactions < MIN_OBSERVATIONS_FOR_MODULATION (=2): return mechanism_scores` — new buyers stay on cohort prior.
- **Already wired into cascade**: `bilateral_cascade.py:3265-3287` calls it after synergy check + posture modulation but before cohort prior boost. Soft-fail try/except at line 3286.

**Implication for W.2**: the modulation _pipeline_ doesn't need building; it's the substrate-fetch path FOR W.2's two accessors that's missing. `apply_per_user_posterior_modulation` reads `BuyerUncertaintyProfile.constructs[dim].mean` per-dimension; W.2's accessors return single scalar/tuple shapes that S6.2's CellFeatureSet wants (archetype enum value, maximizer_tendency Beta as `(α, β)` tuple).

---

## §3 Pass 2 — Archetype assignment storage

**NOT STORED PER-USER as `(buyer_id) → ArchetypeID`.** Inspection across all candidate sites:

- **`BuyerUncertaintyProfile` (information_value.py:401)**: has `buyer_id`, `total_interactions`, `total_conversions`, `last_updated_ts`, `constructs` dict, `bong_posterior`. **No `archetype` field.**
- **Neo4j User node**: `grep -nE "User.*archetype|MERGE.*User|u\.archetype" adam/` returns zero functional matches. The User node persists `cohort_id` + `cohort_score` (per F.2 `persist_cohort_assignments` at `cohort_discovery.py:519`) but no archetype property.
- **Redis**: `_load_buyer_profile_from_redis` at `graph_cache.py:909` deserializes `BuyerUncertaintyProfile.from_dict` — which doesn't include archetype either (`to_dict` at line 570-590 emits buyer_id + total_interactions + total_conversions + constructs + bong_posterior_b64 only).
- **In-process**: `_buyer_profiles: Dict[str, Any]` at `graph_cache.py:88` keyed on buyer_id; values are `BuyerUncertaintyProfile` instances. No archetype attribute exposed.
- **Detection IS implemented**: `ColdStartService.detect_archetype_for_user_with_priors` at `service.py:720` calls `archetype_detector.detect_archetype(trait_estimates, age_bracket, gender, content_types_consumed)` returning `ArchetypeMatchResult` with `matched_archetype: ArchetypeID` + `confidence`. Available since A.2.0/A.2 audit lineage. **But this result is NOT persisted to per-user state.** It feeds back into the cold-start strategy selection within the same request and discards.

**Cold-start at bid time**: `BuyerUncertaintyProfile.__post_init__` at line 432 initializes `constructs` with `ConstructPosterior()` defaults (Beta(2,2) per dimension via DEFAULT_ALPHA/DEFAULT_BETA at lines 332-333) regardless of archetype. `from_archetype_priors` classmethod at line 593 EXISTS but is **never called** from `get_buyer_profile`. So even if archetype detection had run elsewhere, it wouldn't influence the buyer profile created at bid time.

**Implication for W.2**: the archetype_accessor S6.2 expects MUST persist archetype somewhere readable at bid time. Three options surface in §11.

---

## §4 Pass 3 — Maximizer posterior storage

**NOT STORED.** `maximizer_tendency` is **NOT in `UNCERTAINTY_DIMENSIONS`** (information_value.py:113-136 lists 20 dimensions: 7 core edge + 13 extended; `maximizer_tendency` absent — and the explicit note at line 137-144 distinguishes "buyer-side trait list" from "bilateral interaction scores"). So `BuyerUncertaintyProfile.constructs` never carries a Beta posterior for it.

- **A.2 surface**: `ARCHETYPE_MAXIMIZER_PRIORS: Dict[ArchetypeID, BetaDistribution]` at `cold_start/priors/maximizer_tendency.py:184` populated by `derive_maximizer_beta_priors(ARCHETYPE_DEFINITIONS)` at line 103. Accessor `get_maximizer_tendency_prior(archetype_id) → BetaDistribution` at line 189.
- **W.0 §7 finding confirmed**: this is the ONLY surface; no per-user posterior bridge exists.
- **What needs to be built**: an archetype-to-per-user-Beta bridge that (a) takes a buyer's assigned archetype, (b) materializes the matching A.2 Beta as a `ConstructPosterior(alpha=A.2_alpha, beta=A.2_beta)` on the buyer's profile, (c) accumulates bid-evidence updates over time, and (d) retrieves `(α, β)` tuple shape S6.2's `MaximizerPriorAccessor` expects (`tuple[float, float]` per `aggregator.py:46-47`).

**BONG posterior dimension list**: per `_user_alignment_from_bong` at `per_user_posterior_modulation.py:159-187`, the BONG updater iterates `updater.dimension_names`. `MECHANISM_DIMENSION_MAP` at lines 53-72 lists which dims each Cialdini mechanism's `personal_affinity` reads from. None reference `maximizer_tendency`. So adding maximizer_tendency to UNCERTAINTY_DIMENSIONS would NOT automatically wire into BONG; the BONG updater's `dimension_names` would also need extension OR the maximizer_tendency Beta would live as a non-BONG side field on the profile.

**Implication for W.2**: maximizer_prior_accessor needs a NEW per-user storage slot (either as a 21st UNCERTAINTY_DIMENSIONS entry, or a sibling field `maximizer_posterior: ConstructPosterior` on `BuyerUncertaintyProfile`). Each option has trade-offs (Q26 in §11).

---

## §5 Pass 4 — Bayesian update trigger inventory

**EVENT-DRIVEN UPDATE PATH IS WIRED.** Trigger source: outcome events arrive at the StackAdapt webhook (`adam/api/stackadapt/webhook.py`) and route through `outcome_handler.handle_outcome` → `_update_buyer_profile` at `outcome_handler.py:820, 2520`.

- **Update path**: `_update_buyer_profile` builds `edge_dimensions: Dict[str, float]` from outcome metadata (`alignment_scores` + atom outputs, lines 2547-2603), then calls `graph_cache.update_buyer_profile(buyer_id, edge_dimensions, signal_type, processing_depth_weight)` at line 2605.
- **Storage update**: `graph_cache.update_buyer_profile` at `graph_cache.py:967-990` calls `profile.update_from_edge(edge_dimensions, signal_type, processing_depth_weight)` then `_save_buyer_profile_to_redis(buyer_id, profile)`.
- **Per-event weights** at `information_value.py:518-524`: `conversion=1.0`, `click=0.3`, `engagement=0.2`, `impression=0.1`, `bounce=0.05`. Multiplied by `processing_depth_weight` (Enhancement #34) for unprocessed-impression dampening.
- **Update math** at `information_value.py:368-372`: `posterior.update(observed, weight)` does `alpha += observed * weight; beta += (1 - observed) * weight`. Standard Beta-Bernoulli conjugate update.
- **BONG correlated update**: lines 534-562 also feeds the multivariate Gaussian if BONG is initialized.
- **Time-based decay**: NOT implemented. Posteriors monotonically tighten over time. S5.5 nightly retrain (Pass 8) is the intended decay mechanism.

**Implication for W.2**: the trigger infrastructure for `maximizer_tendency` updates can plug into the same path — `outcome_handler._update_buyer_profile` would need to extract a `maximizer_tendency` signal from outcome metadata (e.g., from a `maximizer_signal` atom output) and pass it through `edge_dimensions`. **OR** maximizer_tendency could be derived from existing dimensions (e.g., as a function of `decision_entropy` + `cognitive_load_tolerance` + `information_seeking`) without needing its own observation channel. Q26 covers this.

For archetype reassignment events (Pass 2), no event-driven path exists today. S5.5 nightly retrain would be the natural reassignment trigger; until then, archetype is fixed per buyer.

---

## §6 Pass 5 — Cold-start fallback wiring

**Currently uniform Beta(2,2) defaults** regardless of archetype. `BuyerUncertaintyProfile.__post_init__` at `information_value.py:432-436` initializes every UNCERTAINTY_DIMENSION with `ConstructPosterior()` (Beta(2,2)). `from_archetype_priors` classmethod at line 593-631 EXISTS to apply archetype-informed priors but is **not invoked** by `get_buyer_profile` at `graph_cache.py:941-965` — that path goes Redis → in-memory create → return, bypassing any archetype enrichment.

For W.2's two accessors, cold-start scenarios:

**archetype_accessor cold-start**:
- Q24=(β) requires a real archetype, not just PRAGMATIST default.
- Detection at bid time has no `trait_estimates` (those come from accumulated profile evidence). Available bid-stream signals: `geo` / `device` / `time_of_day` / IAB context — but `archetype_detector.detect_archetype` (detector.py:70) does NOT consume IAB or device; it consumes `trait_estimates`, `behavioral_signals`, `age_bracket`, `gender`, `content_types_consumed`. So cold-start detection at bid time would yield uniform priors in `_score_by_traits` (line 152) → undifferentiated archetype scores → low confidence → effectively returning a near-uniform best-archetype.
- Three plausible paths (Q25):
  - (i) Bid-time return PRAGMATIST default; persist no archetype; deferred-detection on first non-cold event when metadata arrives.
  - (ii) Run reduced-input detection at bid time (geo/device/time only — would require extending `archetype_detector` or building a parallel bid-stream-only detector).
  - (iii) Pre-seed archetypes during onboarding/landing (out of bid hot path entirely).

**maximizer_prior_accessor cold-start**:
- Without archetype, return literature-default Beta (e.g., Beta(2,2) uninformative, or per-population mean from A.2 priors aggregated).
- With archetype, return `ARCHETYPE_MAXIMIZER_PRIORS[archetype]` directly (`get_maximizer_tendency_prior(archetype)`, A.2 surface).
- Once bid evidence accumulates, return updated `(α, β)` from the per-user Beta (which W.2b builds).

**Implication**: cold-start path for archetype is the most consequential design choice. Path (i) is the cleanest fit for the hot path but means archetype-conditioned predicates (e.g., `high_maximizer_comparison`) effectively don't fire on Tier 0/1 buyers. Path (ii) requires extending the detector. Path (iii) is out of scope for cells/.

---

## §7 Pass 6 — Archetype → maximizer derivation order

**Hard dependency**: maximizer_tendency Beta prior IS parameterized by archetype (`get_maximizer_tendency_prior(archetype_id)` at `maximizer_tendency.py:189`). For a buyer with no archetype, no archetype-conditional Beta can be returned — only a uniform fallback.

- (i) **Bid-time access ordering**: S6.2's aggregator already calls `archetype = self._archetype(buyer_id)` BEFORE `self._maximizer(buyer_id, archetype)` (`aggregator.py:118-119, 138-139`). The accessor signature `maximizer_prior_accessor(buyer_id, archetype) → tuple[float, float]` makes the dependency explicit at the type level. **W.2 doesn't need to enforce ordering** — S6.2 already does.
- (ii) **State combinations** in storage layer:
  - Archetype + maximizer both stored: ideal returning-buyer state.
  - Archetype only: cold-start path before first conversion fires. Maximizer derived on-the-fly from `ARCHETYPE_MAXIMIZER_PRIORS[archetype]`.
  - Maximizer only (no archetype): impossible by construction if W.2b derives maximizer from archetype on assignment.
  - Neither: zero-state cold-start. Both accessors return defaults.
- (iii) **Wiring approach**: W.2b's storage initialization should be triggered by archetype assignment — when archetype gets persisted, also materialize the per-user maximizer Beta from the matching A.2 prior. This eliminates "archetype only" as a special case at access time; the maximizer accessor always finds either a real per-user Beta or falls back to the A.2 prior keyed on the archetype it was just handed.

**Implication for W.2 sub-slice ordering**: W.2a (archetype storage) MUST precede W.2b (maximizer storage). W.2c (accessors) can ship simultaneously with W.2b since both accessor closures are thin wrappers over storage reads.

---

## §8 Pass 7 — Storage write-back architecture

**Current architecture**: in-memory dict + Redis read-through/write-through. NOT Neo4j-persisted for buyer profiles.

- **In-memory L1**: `_buyer_profiles: Dict[str, Any]` at `graph_cache.py:88`. Direct attribute access.
- **Redis L2**: `_load_buyer_profile_from_redis` at line 909, `_save_buyer_profile_to_redis` at line 924, `_BUYER_PROFILE_TTL = 90 days` at line 885 (`60 * 60 * 24 * 90`). Key prefix `_BUYER_PROFILE_PREFIX` (per the buyer_profile namespace).
- **Write-through cadence**: every `update_buyer_profile` call writes to Redis (`graph_cache.py:988`) via `_save_buyer_profile_to_redis(buyer_id, profile)` after the in-memory `update_from_edge` call. Fire-and-forget; soft-fail at line 936-937.
- **Read latency**: in-memory hit is dict lookup (microseconds). Redis miss + load is a single `r.get(key)` + JSON deserialize + `BuyerUncertaintyProfile.from_dict` (sub-millisecond typical).
- **Write latency**: `r.setex(key, TTL, json.dumps(...))` after JSON serialize. Sub-millisecond.

**Compatibility with Q22 latency budget** (W.1 revised <15ms aggregator p99): yes. Reading the buyer profile is L1-fast; cold lookups go through Redis at sub-millisecond. The risk is Redis latency spikes — handled by soft-fail returning empty dict (`graph_cache.py:1062-1063`).

**Compatibility with Q24=(β) full build**: yes. The conversion-event-driven update path (Pass 4) already writes to Redis on every outcome event. Adding maximizer_tendency to the dimensions tracked there is a one-line change to UNCERTAINTY_DIMENSIONS + adding the dimension to outcome_handler's edge_dimensions extraction.

**No Neo4j durability for buyer profiles**: buyer state lives in Redis with 90-day TTL. If Redis loses state, profiles cold-start back to defaults. Q24=(β) full build doesn't strictly require Neo4j durability for pilot, but a Neo4j sink for offline analysis (S5.5 nightly retrain) would help. Surface as Q28 below.

---

## §9 Pass 8 — S5.5/S5.6 iteration loop alignment

**S5.5 + S5.6 NOT BUILT.** Confirmed by `grep -rnE "S5\.5|S5\.6|nightly_retrain|ADWIN" adam/`: zero matches in `adam/`; matches only in `docs/CLAUDE CODE DIRECTIVE v3.1.md:472-478` (specification) and `docs/governance/DMC_CHARTER_DRAFT.md:57, 110` (gating reference). No code, no Cron job, no ADWIN implementation.

- **S5.5 spec** (directive line 472): "Cron-driven; retrains classifiers, refits Cognitive Learning Engine posteriors over the last 90 days, regenerates IPSW-corrected sampling weights, snapshots checkpoints."
- **S5.6 spec** (directive line 474): "Bifet-Gavaldà ADWIN on per-(cell, archetype) conversion-rate streams; drift triggers a structured alert + a nightly recalibration flag."

**Compatibility check for W.2's per-user posterior infrastructure**:
- **Aggregation feasibility**: `BuyerUncertaintyProfile.to_dict` at `information_value.py:570-590` emits `{buyer_id, total_interactions, total_conversions, constructs: {dim: {alpha, beta}}, bong_posterior_b64}`. A nightly job can iterate Redis keys with the buyer_profile prefix, deserialize each, and aggregate `(alpha, beta)` per dimension across the population. **No structural blockers.**
- **Per-(cell, archetype) ADWIN streams**: S5.6 needs per-cell-per-archetype conversion rate streams. Cell ID resolution is at bid time (`construct_cell_id` from F.1). An outcome event that records `(cell_id, archetype, outcome)` would feed S5.6 directly. Currently no such event sink exists; outcome_handler updates buyer profiles but doesn't tag with cell_id. **Mild structural concern**: W.2's archetype storage needs to be readable at outcome time as well as bid time so the outcome event can be tagged. Both Redis and in-memory paths support this.
- **Re-derivation under drift**: S5.6 drift triggers MAY require resetting posteriors or re-running archetype detection. W.2's storage layer should expose a "reset" path (clear per-user state OR force re-derivation from priors). Not strictly W.2 scope — flag for future S5.6 work.

**Implication for W.2**: no architectural redesign required. W.2 should expose archetype as a readable field on `BuyerUncertaintyProfile` so outcome events can tag with it; otherwise, the existing Redis-based architecture composes cleanly with S5.5/S5.6 future work.

---

## §10 Recommended W.2 Slice Sequence

**Recommend SPLIT into 3 sub-slices** (W.2a → W.2b → W.2c), shipped in order. Single combined slice is feasible but would be ~1500 LOC (storage + cold-start + dimension extension + accessor wiring + tests across 5 modules) — splitting reduces the per-slice review surface and lets each sub-slice ship its own EVE handoff.

### W.2a — Archetype storage on BuyerUncertaintyProfile + cold-start auto-derivation

**Scope (~300 LOC + tests)**:
- Add `archetype: Optional[ArchetypeID] = None` field to `BuyerUncertaintyProfile` at `adam/intelligence/information_value.py:401`.
- Update `to_dict` (line 570) + `from_dict` (line 633) to round-trip the field.
- Wire `from_archetype_priors` (line 593) into `get_buyer_profile` at `graph_cache.py:941` — when creating a new profile, if cold-start archetype detection has produced a result, use `from_archetype_priors`; otherwise fall back to current uniform default.
- Add `set_buyer_archetype(buyer_id, archetype)` write path on `GraphIntelligenceCache` for explicit assignment from upstream archetype-detection consumers.
- Cold-start adjudication per Q25 (see §11) determines whether bid-time triggers detection or returns PRAGMATIST.

**Tests**: schema round-trip; cold-start + assignment paths; backward-compat deserialization of pre-W.2a Redis entries (no archetype field).

### W.2b — Maximizer_tendency Beta wiring

**Scope (~250 LOC + tests)**:
- Add `maximizer_tendency` to UNCERTAINTY_DIMENSIONS list (the simplest path; alternative is a sibling field, see Q26).
- On `BuyerUncertaintyProfile` instantiation when archetype is known, initialize `constructs["maximizer_tendency"] = ConstructPosterior(alpha=arch_prior.alpha, beta=arch_prior.beta)` from `ARCHETYPE_MAXIMIZER_PRIORS[archetype]`.
- Extend `outcome_handler._update_buyer_profile` to extract `maximizer_tendency_signal` from outcome metadata when present (atom output OR derived from `decision_entropy`/`cognitive_load_tolerance`/`information_seeking` per Q26).
- BONG dimension extension OR side-field wiring per Q26 adjudication.

**Tests**: Beta initialization from archetype prior; update from synthetic conversion event; A.2 prior round-trip across all 8 archetypes.

### W.2c — Accessor closures + production_aggregator activation

**Scope (~150 LOC + tests)** — the W.1-pattern wiring slice:
- Add `make_archetype_accessor(graph_cache)` to `adam/cells/accessors.py`:
  ```python
  def archetype_accessor(buyer_id):
      try:
          profile = graph_cache.get_buyer_profile(buyer_id)
          if profile and profile.archetype:
              return profile.archetype
      except Exception: pass
      return ArchetypeID.PRAGMATIST
  ```
- Add `make_maximizer_prior_accessor(graph_cache)`:
  ```python
  def maximizer_prior_accessor(buyer_id, archetype):
      try:
          profile = graph_cache.get_buyer_profile(buyer_id)
          if profile and "maximizer_tendency" in profile.constructs:
              p = profile.constructs["maximizer_tendency"]
              return (p.alpha, p.beta)
      except Exception: pass
      # Fall back to archetype prior
      try:
          from adam.cold_start.priors.maximizer_tendency import (
              get_maximizer_tendency_prior,
          )
          beta = get_maximizer_tendency_prior(archetype)
          return (beta.alpha, beta.beta)
      except Exception:
          return (0.5, 10.0)
  ```
- Wire both into `production_aggregator()` at `adam/cells/aggregator.py:251` replacing the W.2-deferred lambda stubs.
- Tests: direct-call path; cold-start fallback to archetype prior; cold-start fallback to literature default; full apply_cell_modulation round-trip with archetype-conditioned predicates firing.

**After W.2c lands**: 7 of 7 substrate channels are wired (cohort + cascade_tier real data; posture + priming + journey wired-but-cold per W.1; archetype + maximizer real data via W.2). Mindstate (M.0/M.1+) remains the only deferred channel. 4 of 6 seed predicates fire on real data (compensatory_cohort_social_consumption + persuasion-resistance + maximizer-comparison + the W.1 ones).

---

## §11 QUESTION-and-stop Concerns

**Q25 — Cold-start archetype detection at bid time.** Per §6: bid-time archetype detection has no `trait_estimates` and `archetype_detector.detect_archetype` doesn't consume bid-stream-only signals (geo/device/time/IAB). Three options:
- (i) Bid-time returns PRAGMATIST default; archetype gets persisted on first NON-cold event (e.g., first conversion arrives via webhook → outcome_handler triggers detection from accumulated metadata → assigns archetype). Minimal scope; archetype-conditioned predicates don't fire on Tier 0/1 buyers.
- (ii) Build a bid-stream-only archetype detector (geo/device/time/IAB → archetype prior). Substantial scope; new detector module.
- (iii) Pre-seed archetypes during onboarding/landing flow (outside bid hot path). Requires upstream integration; out of W.2 scope.

**Recommend (i) for W.2a** — minimal-scope, ships the storage layer + auto-fill-on-event path; (ii) becomes a future slice if pilot shows archetype-conditioned predicate fire rate is too low.

**Q26 — Where to store maximizer_tendency Beta and how to update it.** Per §4: maximizer_tendency is a TRAIT not an alignment dimension. Two storage options:
- (α) Add to UNCERTAINTY_DIMENSIONS (simplest; reuses `constructs` dict and the entire update_from_edge path; requires extending BONG dimension list to keep the BONG and constructs in sync, OR explicitly noting that maximizer_tendency is constructs-only and bypasses BONG).
- (β) Add a sibling field `maximizer_posterior: Optional[ConstructPosterior]` on `BuyerUncertaintyProfile`; W.2b adds dedicated read/update accessors. Cleaner separation but more code; outcome_handler needs a separate update path.

**Update signal sourcing**: maximizer_tendency outcome signal isn't directly observable from a conversion event. Two sub-options:
- (γ) Derive from `decision_entropy` + `cognitive_load_tolerance` + `information_seeking` (high values → maximizer-like behavior). Heuristic substrate (NOT load-bearing — Schwartz et al. 2002 lineage).
- (δ) Add an explicit `maximizer_tendency_signal` slot to the outcome metadata schema; populated by a future MaximizerSignalAtom that reads behavioral telemetry (multi-tab comparison, time-on-comparison-page).

**Recommend (α) + (γ)** for W.2b — simplest path that ships per-user maximizer state on existing infrastructure; (β)/(δ) become refinements if pilot shows the proxy signal is too noisy.

**Q27 — Archetype reassignment policy.** Once archetype is assigned, is it FIXED or REASSESSED as evidence accumulates? Options:
- (i) FIXED first-assignment. Reassessment only via S5.5 nightly retrain. Simplest; pilot-stable.
- (ii) Periodic reassessment (e.g., every 100 conversions) using accumulated `BuyerUncertaintyProfile.constructs` as `trait_estimates` input to `archetype_detector`. Adaptive; risk of churn.
- (iii) Continuous Bayesian update on archetype probability distribution (each archetype has a prior probability; conversion evidence updates a categorical distribution; argmax determines assignment).

**Recommend (i) for W.2a**. (ii)/(iii) are future S5.5/S5.6 territory.

**Q28 — Neo4j durability for buyer profiles (forward-look only).** Current architecture is Redis-only with 90-day TTL. Q24=(β) full build doesn't strictly require Neo4j durability for pilot, but S5.5 nightly retrain will want a durable historical record for IPSW recomputation across windows longer than Redis TTL. **Not a W.2 blocker** — surface for future work. Recommend W.2 ships Redis-only; S5.5 adds Neo4j sink when it lands.

---

## §12 Audit closure

W.2.0 ships the audit memo. Zero code changes; zero test changes; ~5,644 tests passing unchanged. The per-user posterior infrastructure surface is in better shape than expected — the modulation pipeline, storage backend, event-driven update path, and Redis write-through are all operational. The two W.2-scope gaps (archetype storage, maximizer Beta wiring) are discrete and architecturally clean to close. Audit-first discipline paid for itself again: the Q26 storage-vs-sibling-field decision and the Q25 cold-start path adjudication would both have been late-discovery surprises if I'd jumped straight to implementation.

Awaits Claude Proper prompt for **W.2a** (archetype storage + cold-start auto-derivation per Q25=(i) recommended adjudication). W.2b and W.2c follow in that order. After W.2c ships, only mindstate (M.0/M.1+) remains as a substrate-channel gap before pilot launch.

**Hand-off pointer**: branch `feature/hmt-dashboard` @ HEAD post-W.2.0 commit. **16 slices closed total** (13 implementation + 3 audits — S6.2.0 + W.0 + W.2.0).
