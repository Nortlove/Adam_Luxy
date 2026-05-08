# Substrate Accessor Wiring Audit
## Slice ID: W.0
## Session: 2026-05-07 (continuation)
## Predecessor: 78dcbec (S6.2 framework operational)
## Audit type: Read-only inspection (A.1.0 + A.2.0 + S6.2.0 precedents)
## Branch: feature/hmt-dashboard

---

## §1 Executive Summary

S6.2 shipped `CellFeaturesAggregator` at `adam/cells/aggregator.py:51` with eight dependency-injected accessor parameters; the bilateral cascade integration block at `adam/api/stackadapt/bilateral_cascade.py:2882` currently uses `default_aggregator()` returning neutral defaults. **None of the eight accessor type aliases at `adam/cells/aggregator.py:41-48` matches an existing production callable as a one-line direct-call pass.** The wiring distribution is:

- **(a) direct-call: 1** — `cohort_accessor` (F.2's `get_cohort_compensatory_flag` is an exact-match sync method).
- **(b) lightweight adapter: 3** — `posture_accessor`, `priming_accessor`, `cascade_tier_accessor`. Each requires <10 lines of glue (sync/async bridging, url-vs-list shape, lookup-then-categorize composition).
- **(c) coordinator wrapper: 1** — `journey_accessor`. Async `get_journey(user_id, category)` returns `UserJourney` with `JourneyStage` (13-class), needs sync bridge + fabricated `category` context + 13→6 mapping via `to_conversion_stage` at `adam/user/journey/models.py:67`.
- **(d) build-the-accessor: 3** — `archetype_accessor` (no `(buyer_id) → ArchetypeID` direct surface exists), `mindstate_accessor` (existing `extract_mindstate_vector` consumes a `PagePsychologicalProfile` not a `(buyer_id, url_hash)` tuple, AND the C+D-derived properties depend on orchestrator-populated fields that are NOT set by the existing extractor), and `maximizer_prior_accessor` (only `get_maximizer_tendency_prior(archetype_id) → BetaDistribution` exists — no per-user posterior surface, and the return type is wrong shape).

**Total slice estimate: 4 W.1+ slices** if grouped by wiring complexity (W.1: direct-call + adapters; W.2: journey coordinator; W.3: archetype + mindstate accessor builds; W.4: maximizer per-user posterior accessor or interim collapse-to-prior). **5 QUESTION-and-stop concerns surfaced for Claude Proper adjudication** — see §13. The most consequential is Q20 (mindstate_accessor scope expansion: C+D orchestrator-populated fields are not set anywhere bid-time-reachable today; substrate-fetch wiring may need a parallel "C+D field population" sub-slice before predicates can fire usefully).

---

## §2 Pass 1 — archetype_accessor

1. **Module location.** `adam/cold_start/archetypes/detector.py:31` (class `ArchetypeDetector`); singleton at `adam/cold_start/archetypes/detector.py:287` (`get_archetype_detector`); orchestration at `adam/cold_start/service.py:59` (`ColdStartService`). Per-buyer state lives on `BuyerUncertaintyProfile` at `adam/intelligence/information_value.py` (see §3 of S6.2.0 audit memo).
2. **Function/method signature.** `ArchetypeDetector.detect_archetype(trait_estimates, behavioral_signals, age_bracket, gender, content_types_consumed) → ArchetypeMatchResult` at `adam/cold_start/archetypes/detector.py:70-77`. **This is an inference call, not a buyer-keyed accessor.**
3. **Return type.** `ArchetypeMatchResult` (carries `matched_archetype: ArchetypeID` + confidence + per-archetype scores), not raw `ArchetypeID`.
4. **Bid-time latency.** Inference path is sub-millisecond if traits already estimated (multiplicative scoring across 8 archetypes). Cold path that requires trait estimation is unmeasured but likely 1-5ms.
5. **Caching behavior.** No buyer→archetype cache exists. `BuyerUncertaintyProfile` cache at `graph_cache._buyer_profiles` (`adam/api/stackadapt/graph_cache.py:88`) carries Beta posteriors per dimension but does NOT carry an `archetype_id` field (verified: `grep -nE "primary_archetype|inferred_archetype|user_archetype|self\.archetype" adam/intelligence/information_value.py` returns zero matches in BuyerUncertaintyProfile fields).
6. **Cold-start behavior.** No buyer→archetype assignment exists for cold buyers; `ArchetypeDetector.detect_archetype` with no inputs returns the first archetype (uniform prior tie-broken by `max()` ordering). The S6.2 default is `ArchetypeID.PRAGMATIST` (per `aggregator.py:103`) — an opinionated choice that diverges from `ArchetypeDetector`'s output for empty inputs.
7. **Fallback behavior.** If archetype detector raises, S6.2 falls back to `PRAGMATIST` per the `_fetch_with_default` wrapper at `aggregator.py:233`. Production-correct for fail-soft.
8. **Divergence from S6.2 expected shape.** S6.2 expects `ArchetypeAccessor = Callable[[str], ArchetypeID]` (`aggregator.py:41`). No callable with that signature exists. The closest production surface is `ColdStartService.archetype_detector.detect_archetype(...)` which (a) takes structured signal inputs not buyer_id, (b) returns `ArchetypeMatchResult` not `ArchetypeID`. Persisted per-user archetype lives only on Neo4j edge properties (`user_archetype` filter in `graph_cache.py:656`) — not on `BuyerUncertaintyProfile`.
9. **Recommended wiring approach: (d) build-the-accessor.** W.1+ must construct the accessor from existing pieces. Recommended composition: (i) check `BuyerUncertaintyProfile` for a NEW `primary_archetype: Optional[ArchetypeID]` field (which itself needs a write path on profile updates — likely a follow-up slice); (ii) if absent, query Neo4j for `User.user_archetype` if persisted there; (iii) if absent, fall back to `ArchetypeID.PRAGMATIST` neutral default. Building the field + write path adds substantial scope; for pilot a stub returning `PRAGMATIST` (matching S6.2's current default) preserves operational behavior and pushes the build to a follow-up.

---

## §3 Pass 2 — posture_accessor

1. **Module location.** `adam/intelligence/posture_classifier.py:122` (`URLPostureClassifier`), with class-balanced trainer added 2026-05-06; artifact load at `posture_classifier.py:450` (`load_classifier_artifact(path) → URLPostureClassifier`).
2. **Function/method signature.** `URLPostureClassifier.predict(urls: List[str]) → List[str]` at `posture_classifier.py:224-229`. Classifier instance method, not module-level function.
3. **Return type.** `List[str]` of labels (one of `FIVE_CLASS_POSTURES` strings). Single-URL predict requires `predict([url])[0]`.
4. **Bid-time latency.** TF-IDF tokenize + transform + multinomial logreg predict — sub-millisecond per URL on a warm classifier. Artifact-load cost is one-time at process start.
5. **Caching behavior.** No URL→posture cache. Classifier instance must be loaded once and reused (`load_classifier_artifact` reads pickle/joblib + is not cheap).
6. **Cold-start behavior.** Predictions always return a label; "cold" in the sense of an untrained classifier raises `RuntimeError("Call fit() first")` at `posture_classifier.py:215-216` — not a runtime cold-start, that's an init-time error.
7. **Fallback behavior.** Classifier raises on missing fit OR when URLs list is empty (sklearn vectorizer behavior). For runtime fail-soft, S6.2 aggregator's `_fetch_with_default` wraps it.
8. **Divergence from S6.2 expected shape.** S6.2 expects `PostureAccessor = Callable[[str], str]` (`aggregator.py:42`). Actual surface is `(List[str]) → List[str]`. Also: S6.2 parameter name is `url_hash` but the cascade integration passes `page_url or ""` (per `bilateral_cascade.py:2882` integration block) — actual passed value is the URL, name is misleading.
9. **Recommended wiring approach: (b) lightweight adapter.** Plus a one-time singleton-load helper:
   ```python
   _classifier_singleton = None
   def get_posture_accessor(artifact_path: str) -> Callable[[str], str]:
       global _classifier_singleton
       if _classifier_singleton is None:
           _classifier_singleton = load_classifier_artifact(artifact_path)
       return lambda url: _classifier_singleton.predict([url])[0]
   ```
   Total: ~7 lines including import. Artifact path is the operational unknown — needs decision on which trained checkpoint to load (latest? pinned-version?).

---

## §4 Pass 3 — journey_accessor

1. **Module location.** `adam/user/journey/service.py:79` (`JourneyTrackingService`), singleton at `service.py:302`. Models at `adam/user/journey/models.py`. ConversionStage mapping at `models.py:67` (`to_conversion_stage`).
2. **Function/method signature.** `async JourneyTrackingService.get_journey(user_id: str, category: str) → Optional[UserJourney]` at `service.py:93-97`.
3. **Return type.** `Optional[UserJourney]` — async return; caller must `await` and handle `None`. `UserJourney.current_state.stage` is `JourneyStage` (13-value enum at `models.py:19-43`), NOT `ConversionStage` (6-value enum at `adam/retargeting/models/enums.py:21`).
4. **Bid-time latency.** In-memory dict + Redis fallback; sub-millisecond for cached, ~5-10ms for Redis lookup.
5. **Caching behavior.** L1 in-process `_journeys: Dict[str, UserJourney]` keyed `f"{user_id}:{category}"` (`service.py:91`); L2 Redis under `journey:{user_id}:{category}` (`service.py:106`).
6. **Cold-start behavior.** `get_journey` returns `None` for unknown buyers. `get_or_create_journey` (`service.py:114`) creates a new journey at `JourneyStage.UNAWARE` — but this is a write path and shouldn't fire from the bid-time aggregator.
7. **Fallback behavior.** Returns `None` on miss. Production aggregator must map `None → ConversionStage.UNAWARE` (matches S6.2's neutral default at `aggregator.py:113`).
8. **Divergence from S6.2 expected shape.** S6.2 expects `JourneyAccessor = Callable[[str], ConversionStage]` (`aggregator.py:43`). Actual surface diverges on THREE axes: (i) async vs sync; (ii) takes `(user_id, category)` not `(buyer_id)` — the `category` parameter has no obvious bid-time provenance and may need to be derived from campaign metadata or fixed to a sentinel; (iii) returns `Optional[UserJourney]` not `ConversionStage` — needs `to_conversion_stage(journey.current_state.stage)` mapping which itself returns a string not a `ConversionStage` enum (verified at `models.py:67-74`: returns `str` from a fixed mapping dict).
9. **Recommended wiring approach: (c) coordinator wrapper.** Sketch (~25 lines):
   ```python
   def make_journey_accessor(journey_service, default_category: str) -> Callable[[str], ConversionStage]:
       def accessor(buyer_id: str) -> ConversionStage:
           import asyncio
           journey = asyncio.run(journey_service.get_journey(buyer_id, default_category))
           if journey is None:
               return ConversionStage.UNAWARE
           stage_str = to_conversion_stage(journey.current_state.stage)
           try:
               return ConversionStage(stage_str)
           except ValueError:
               return ConversionStage.UNAWARE
       return accessor
   ```
   `asyncio.run()` in a sync hot path is suboptimal — Q21 below. The `default_category` parameter requires Claude Proper adjudication on what value to fix it to (per-campaign? sentinel? lookup from cascade context?).

---

## §5 Pass 4 — priming_accessor

1. **Module location.** `adam/priming/feature_store.py:129` (`PagePrimingSignatureStore`); url-to-hash converter at `adam/priming/pipeline.py:96` (`url_to_hash`); `PagePrimingSignature` dataclass at `adam/priming/signature.py`.
2. **Function/method signature.** `async PagePrimingSignatureStore.get(url_hash: str) → PagePrimingSignature` at `feature_store.py:158`. Always returns a signature (neutral fallback on cold miss).
3. **Return type.** `PagePrimingSignature` (frozen dataclass, V2 schema includes `persuasion_knowledge_activation` per B / commit `831e49a`).
4. **Bid-time latency.** Per S3.3 spec: <5ms p99 with cascade L1+L2+L3. Cold miss returns `neutral_signature(url_hash)` synchronously without I/O.
5. **Caching behavior.** L1 LRU (capacity 1000 default; `feature_store.py:144`) + L2 async Redis backend + L3 sync Memcached backend, with promote-to-L1 on hit.
6. **Cold-start behavior.** `neutral_signature(url_hash)` returned synchronously — populated with floor values (valence=0, arousal=0, regulatory_focus_priming="neutral", cognitive_load_estimate=0, activated_frames=tuple()).
7. **Fallback behavior.** Always returns a `PagePrimingSignature` (neutral on cold miss); never raises in normal operation. Backend errors are logged but cascade continues.
8. **Divergence from S6.2 expected shape.** S6.2 expects `PrimingAccessor = Callable[[str], Any]` (`aggregator.py:44`) — note the `Any` return, so V2 schema match isn't a divergence concern. The divergences are: (i) async vs sync; (ii) S6.2's parameter `url_hash` is the right name and shape (matches `PagePrimingSignatureStore.get`'s `url_hash`), but the cascade integration block passes `page_url or ""` not a hash — wiring must apply `url_to_hash(page_url)` at the seam.
9. **Recommended wiring approach: (b) lightweight adapter.** Sync bridge + url-hash conversion (~8 lines):
   ```python
   def make_priming_accessor(store: PagePrimingSignatureStore) -> Callable[[str], PagePrimingSignature]:
       import asyncio
       def accessor(url: str) -> PagePrimingSignature:
           url_hash = url_to_hash(url)
           return asyncio.run(store.get(url_hash))
       return accessor
   ```
   Same `asyncio.run()` concern as journey_accessor (Q21).

---

## §6 Pass 5 — mindstate_accessor

1. **Module location.** Schema at `adam/retargeting/resonance/models.py:55` (`PageMindstateVector`). Extractor at `adam/retargeting/resonance/mindstate_vector.py:71` (`extract_mindstate_vector`).
2. **Function/method signature.** `extract_mindstate_vector(page_profile: Any, url: str = "", domain: str = "") → PageMindstateVector` at `mindstate_vector.py:71-75`. Sync.
3. **Return type.** `PageMindstateVector` (frozen dataclass, 32 dimensions + C+D orchestrator-populated fields per commits `fd1a95a` + `14b9d73`).
4. **Bid-time latency.** Sub-millisecond — pure dict-merging + dataclass construction.
5. **Caching behavior.** No cache. PageMindstateVector is constructed each call from a `PagePsychologicalProfile`.
6. **Cold-start behavior.** With no profile, function would crash on `getattr(profile, ...)` — needs caller-side None check. Default values built into PageMindstateVector dataclass yield 0.0 for all derived properties.
7. **Fallback behavior.** Raises if `page_profile` is None and not a dict (no None-guard). S6.2 aggregator wraps with `_fetch_with_default(..., None)` then handles None at field-extraction with `getattr(mindstate, "field", default) if mindstate else default`.
8. **Divergence from S6.2 expected shape.** S6.2 expects `MindstateAccessor = Callable[[str, str], Any]` (i.e., `(buyer_id, url_hash) → PageMindstateVector`) at `aggregator.py:45`. **Major divergence:** existing `extract_mindstate_vector(page_profile, url, domain)` takes a profile object directly, not a buyer_id+url_hash tuple. Plus: **the C+D-derived properties (`fomo_score`, `psych_ownership_proxy`, `depletion_proxy`) depend on orchestrator-populated fields (`scarcity_frame_present`, `regulatory_focus_priming`, `touch_count`, `dwell_seconds`, `session_position_seconds`) which `extract_mindstate_vector` does NOT set** — it only populates the 32 base dimensions. Those orchestrator fields take their dataclass defaults (`False`, `"neutral"`, `0`, `0.0`, `0.0`) — yielding `fomo_score = 0.0` and `psych_ownership_proxy = 0.0` regardless of real bid-stream signals.
9. **Recommended wiring approach: (d) build-the-accessor.** This is the largest scope expansion in W. The build requires:
   (i) Locate where `PagePsychologicalProfile` is fetched at bid time (likely `get_page_intelligence_cache().lookup(page_url)` per `page_intelligence.py:643`).
   (ii) Compose with `extract_mindstate_vector(profile, page_url, domain)`.
   (iii) **Populate C+D orchestrator fields from bid-stream signals** — this is the missing bridge. `scarcity_frame_present` should derive from PagePrimingSignature.activated_frames; `regulatory_focus_priming` is on PagePrimingSignature; `touch_count` and `dwell_seconds` need to come from the buyer's session telemetry (likely a Redis cache or BuyerUncertaintyProfile field that doesn't exist yet); `session_position_seconds` is session-aged time which may also be uncached. **Without this population step, all C+D-keyed predicates (fomo, psych ownership, depletion) are dead-letter — they will not fire on real bid data.**
   See Q20 below — this is the most consequential unsurfaced complexity in W.0.

---

## §7 Pass 6 — cohort_accessor

1. **Module location.** `adam/api/stackadapt/graph_cache.py:1080` (`get_cohort_compensatory_flag`).
2. **Function/method signature.** `GraphIntelligenceCache.get_cohort_compensatory_flag(self, buyer_id: str) → Tuple[bool, float]` at `graph_cache.py:1080`. Sync.
3. **Return type.** `Tuple[bool, float]` — exact match to S6.2's `CohortAccessor`.
4. **Bid-time latency.** Cached at `_cohort_compensatory_flags` dict (`graph_cache.py:97`); `<1ms` cached path per F.2 spec; uncached path is one Neo4j query.
5. **Caching behavior.** L1 in-process dict keyed by `buyer_id`; L2 Neo4j MATCH on `(:User)-[:BELONGS_TO]->(:Cohort)`; TTL via `_COHORT_COMPENSATORY_FLAG_TTL` (per F.2 spec).
6. **Cold-start behavior.** Returns `(False, 0.50)` for unknown buyers per F.2's backward-compat default.
7. **Fallback behavior.** Returns `(False, 0.50)` on Neo4j errors / missing edges. Never raises.
8. **Divergence from S6.2 expected shape.** S6.2 expects `CohortAccessor = Callable[[str], Tuple[bool, float]]` (`aggregator.py:46`). **Exact match.** Only nuance: the method is bound to a `GraphIntelligenceCache` instance, so wiring needs to pass `instance.get_cohort_compensatory_flag` not the unbound method.
9. **Recommended wiring approach: (a) direct-call.** One-line pass:
   ```python
   cohort_accessor = graph_cache_instance.get_cohort_compensatory_flag
   ```

---

## §8 Pass 7 — maximizer_prior_accessor

1. **Module location.** `adam/cold_start/priors/maximizer_tendency.py:184` (`ARCHETYPE_MAXIMIZER_PRIORS` dict); accessor at `maximizer_tendency.py:189` (`get_maximizer_tendency_prior`).
2. **Function/method signature.** `get_maximizer_tendency_prior(archetype_id: ArchetypeID) → BetaDistribution` at `maximizer_tendency.py:189-204`. Sync. **Single argument** (archetype only — no buyer_id).
3. **Return type.** `BetaDistribution` (alpha, beta) object — NOT `tuple[float, float]`.
4. **Bid-time latency.** Dict lookup — nanoseconds.
5. **Caching behavior.** `ARCHETYPE_MAXIMIZER_PRIORS` is a module-level dict computed once at import via `derive_maximizer_beta_priors(ARCHETYPE_DEFINITIONS)`. Always-warm.
6. **Cold-start behavior.** Always returns a prior (8 archetypes × 1 prior each = 8 entries). No buyer-conditional cold-start because there's no per-user posterior.
7. **Fallback behavior.** Raises `KeyError` if `archetype_id` is not in `ARCHETYPE_MAXIMIZER_PRIORS` (e.g., if a new ArchetypeID enum value is added without updating the prior derivation).
8. **Divergence from S6.2 expected shape.** S6.2 expects `MaximizerPriorAccessor = Callable[[str, ArchetypeID], Tuple[float, float]]` returning `(posterior_mean, posterior_strength)` per the `CellFeatureSet` field comment at `features.py:69-73`. Two divergences: (i) signature takes `(buyer_id, archetype)` not `(archetype_id)` — the buyer_id is meant to allow per-user posterior lookup which **doesn't exist anywhere in the codebase** (verified: zero matches for "maximizer_tendency_posterior" or "user_maximizer" outside the cells/ files); (ii) return type is `tuple[float, float]` not `BetaDistribution` — would need `(prior.alpha / (prior.alpha + prior.beta), prior.alpha + prior.beta)` derivation.
9. **Recommended wiring approach: (d) build-the-accessor (interim collapse-to-prior is acceptable for pilot).** Two paths:
   - **Pilot-acceptable interim:** Lambda that ignores buyer_id and collapses to archetype prior:
     ```python
     def maximizer_prior_accessor(buyer_id: str, archetype: ArchetypeID) -> tuple[float, float]:
         prior = get_maximizer_tendency_prior(archetype)
         return (prior.alpha / (prior.alpha + prior.beta), prior.alpha + prior.beta)
     ```
     This loses per-user adaptation (everyone of archetype X gets the same maximizer score) but unblocks the predicate flow. Per-user posterior surface can land in a follow-up.
   - **Full per-user posterior build:** Add a `maximizer_tendency_posterior` field to `BuyerUncertaintyProfile`, write path on conversion outcomes, read path here. Substantial scope (~50-100 LOC + tests + Redis schema migration). Defer post-pilot.

---

## §9 Pass 8 — cascade_tier_accessor (optional)

1. **Module location.** `adam/intelligence/page_attentional_posture_substrate.py:101` (`categorize_posture`); page intelligence cache at `adam/intelligence/page_intelligence.py:643` (`PageIntelligenceCache.lookup`); cache singleton at `page_intelligence.py:2157` (`get_page_intelligence_cache`).
2. **Function/method signature.** `categorize_posture(posture_float: float, posture_confidence: float) → str` at `page_attentional_posture_substrate.py:101`. PLUS `PageIntelligenceCache.lookup(page_url: str) → Optional[PagePsychologicalProfile]` at `page_intelligence.py:643`.
3. **Return type.** `categorize_posture` returns one of `{blend_compatible, vigilance_activating, neutral, unknown}` strings (per Q18 orthogonality finding from S6.2 Pass C — see EVE block 78dcbec).
4. **Bid-time latency.** Sub-millisecond — three float comparisons.
5. **Caching behavior.** No cache on `categorize_posture` itself; `PageIntelligenceCache` carries the underlying `attentional_posture` float + confidence (`page_intelligence.py:300-301`).
6. **Cold-start behavior.** Profile is `None` for unknown URLs → return `"unknown"` (matches S6.2's `cascade_attentional_posture: Optional[str] = None` neutral default).
7. **Fallback behavior.** Profile-missing path returns `None` from cache lookup; the wiring layer must convert to `"unknown"` or `None` per S6.2's contract.
8. **Divergence from S6.2 expected shape.** S6.2 expects `CascadeTierAccessor = Callable[[str, str], Optional[str]]` at `aggregator.py:48` — i.e., `(buyer_id, url_hash) → Optional[str]`. Divergences: (i) buyer_id is unused (cascade tier is a page-level signal not a buyer-level one); (ii) the underlying cache lookup is by `page_url` not `url_hash` — same naming-vs-actual confusion as priming_accessor.
9. **Recommended wiring approach: (b) lightweight adapter.** Compose lookup + categorize:
   ```python
   def make_cascade_tier_accessor(page_cache) -> Callable[[str, str], Optional[str]]:
       def accessor(buyer_id: str, url: str) -> Optional[str]:
           profile = page_cache.lookup(url)
           if profile is None:
               return None
           return categorize_posture(
               getattr(profile, "attentional_posture", 0.0) or 0.0,
               getattr(profile, "attentional_posture_confidence", 0.0) or 0.0,
           )
       return accessor
   ```
   ~9 lines. **Recommendation: WIRE FOR PILOT.** Adds an orthogonal feature (blend vs vigilance attentional mode) at near-zero cost; S6.2 already has the field slot ready; downstream predicates can condition on it (none of the 6 seed predicates do today, but it's an easy iteration target).

---

## §10 Pass 9 — Latency budget accounting

S6.2 aggregator targets <8ms p99. Per-accessor expected contributions (best-effort estimate; no end-to-end benchmarks yet):

| Accessor | Expected p99 latency | Source path |
|---|---|---|
| archetype_accessor | <0.5ms (stub) / 5-10ms (full Neo4j read) | dict lookup vs Neo4j |
| posture_accessor | <2ms | TF-IDF + logreg predict on 1 URL |
| journey_accessor | <1ms cached / 5-10ms Redis miss + asyncio.run overhead | L1 dict + Redis |
| priming_accessor | <5ms p99 | per S3.3 spec |
| mindstate_accessor | <1ms (extraction itself) — but full chain incl. profile lookup unknown | dict construction |
| cohort_accessor | <1ms cached | per F.2 spec |
| maximizer_prior_accessor | <0.1ms | dict lookup |
| cascade_tier_accessor | <1ms | profile lookup + 3 comparisons |

**Sum of expected p99: ~16-22ms.** This **exceeds the <8ms target** even before considering `asyncio.run()` overhead in journey/priming wrappers. **Q22 below.** Mitigation options: (a) parallelize accessor calls (asyncio.gather across all async accessors + sync-thread for sync ones); (b) pre-warm caches at session start; (c) revise the <8ms target upward (the cascade's existing modulators don't have published latency figures either, so the budget may be revisable).

`asyncio.run()` invoked twice per bid (for journey + priming) creates a new event loop each call, which is documented to be measurably expensive (1-3ms per invocation in modern Python). For the sync-cascade-context wiring, an `asyncio.new_event_loop()` + `loop.run_until_complete()` pattern with a process-wide event loop reused via `asyncio.set_event_loop()` is cheaper but still suboptimal. The clean answer is to make S6.2's aggregator itself async — but that changes the cascade integration block at `bilateral_cascade.py:2882` which is sync.

---

## §11 Pass 10 — Wiring approach inventory

| # | Accessor | Approach | LOC est. | Notes |
|---|---|---|---|---|
| 1 | archetype_accessor | (d) build (or pilot stub) | 30-100 | Stub returning PRAGMATIST is 1 line; full per-buyer surface is ~100 LOC + Neo4j writes + tests |
| 2 | posture_accessor | (b) adapter | ~7 | Singleton-load + lambda; artifact path needs decision |
| 3 | journey_accessor | (c) wrapper | ~25 | Async/sync bridge + category fabrication + 13→6 mapping |
| 4 | priming_accessor | (b) adapter | ~8 | Async/sync bridge + url_to_hash |
| 5 | mindstate_accessor | (d) build | 50-150 | Profile lookup + extraction + **C+D orchestrator field population (the big unknown)** |
| 6 | cohort_accessor | (a) direct | 1 | Method handle pass |
| 7 | maximizer_prior_accessor | (d) interim | ~5 | Collapse-to-prior 5 lines; full per-user build deferred post-pilot |
| 8 | cascade_tier_accessor | (b) adapter | ~9 | Profile lookup + categorize_posture |

**Total wiring LOC (pilot-acceptable interim): ~135-155.** With full builds for archetype + mindstate: 240-410 LOC across all accessors. Test surface adds another ~150-300 LOC.

---

## §12 Recommended W.1+ Slice Sequence

**W.1 — Direct-call + adapters (cohort + posture + priming + cascade_tier).** ~25 LOC + ~30 LOC tests. 4 accessors wired in one slice. All are independent (different modules, different concerns) but small — bundling them into one slice avoids slice-overhead. Risk: low (each is a thin glue layer around well-defined existing surfaces). After W.1, 4 of 8 accessors are operational.

**W.2 — journey_accessor coordinator wrapper (~25 LOC + ~40 LOC tests).** Single slice for the journey wrapper because it carries two adjudication concerns (default category + asyncio.run cost — see Q21) that benefit from focused review. After W.2, 5 of 8 accessors operational.

**W.3 — Pilot interim stubs for archetype + maximizer_prior_accessor (~10 LOC + ~20 LOC tests).** Both unblock the predicate flow with degenerate values (PRAGMATIST always; archetype-prior collapses for maximizer). Honestly tagged in EVE as interim. After W.3, 7 of 8 accessors operational with predicates fireable for non-mindstate-derived predicates.

**W.4 — mindstate_accessor build + C+D orchestrator field population (50-150 LOC + ~80 LOC tests).** The big slice. Needs an upstream architectural decision (Q20) about where the orchestrator-populated fields come from at bid time. Could split further (W.4a: extraction-only mindstate accessor with C+D fields at defaults; W.4b: C+D field population from session telemetry). After W.4, all 8 accessors operational; FOMO/ownership/depletion predicates fire on real signals.

**Optional W.5 — Full per-user posterior surfaces for archetype + maximizer.** Replaces the W.3 pilot stubs with persisted per-user state. Substantial scope; recommend deferring to post-pilot iteration unless predicate fire data shows interim degenerate behavior is hurting differentiation.

---

## §13 QUESTION-and-stop Concerns

**Q20 — mindstate C+D orchestrator field population scope.** The C+D-derived properties (`fomo_score`, `psych_ownership_proxy`, `depletion_proxy`) **do not fire on real bid data without a separate substrate-fetch path** that populates `scarcity_frame_present`, `regulatory_focus_priming`, `touch_count`, `dwell_seconds`, `session_position_seconds`. None of those fields are populated by `extract_mindstate_vector` (`mindstate_vector.py:71`). Some (regulatory_focus_priming, scarcity_frame_present) can be derived from PagePrimingSignature's `regulatory_focus_priming` + `activated_frames`. Others (touch_count, dwell_seconds, session_position_seconds) are session-telemetry signals that need a separate cache or BuyerUncertaintyProfile field that doesn't exist today. **Adjudication options:** (i) treat C+D fields as "session-state" features that must be wired through a session-telemetry layer (substantial scope, possibly its own audit slice); (ii) compute them from PagePrimingSignature fields where possible and accept defaults for the session-telemetry-derived ones (degraded but functional); (iii) defer C+D predicates to post-pilot and ship W.1-W.3 + a stub W.4a that yields all C+D properties at 0.0. Most consequential adjudication in W.

**Q21 — `asyncio.run()` in sync hot path.** Two accessors (journey, priming) are async. The cascade integration block at `bilateral_cascade.py:2882` is sync. Per-call `asyncio.run()` is documented to be 1-3ms per invocation. Two invocations per bid pushes the aggregator past the <8ms target. **Adjudication options:** (i) use `asyncio.new_event_loop()` + reused process-wide loop (cheaper but adds module-level state); (ii) wrap the entire S6.2 aggregator path in async and make the cascade integration block async too (touches more code); (iii) accept the latency cost and revise the <8ms budget upward.

**Q22 — <8ms aggregator p99 budget.** Sum of expected per-accessor p99 latencies is 16-22ms (§10), exceeding the <8ms target by 2-3×. Either parallelize via asyncio.gather (requires async aggregator — see Q21), pre-warm caches aggressively, or revise the budget. **Adjudication options:** (i) async-rewrite the aggregator + parallelize; (ii) revise budget to match measured reality with first ship + iterate; (iii) trim accessor set for pilot (e.g., defer mindstate + cascade_tier).

**Q23 — Default category for journey_accessor.** `JourneyTrackingService.get_journey(user_id, category)` requires a category parameter. Bid-stream context may have a campaign category, a creative category, or no category at all. **Adjudication options:** (i) fix to a sentinel ("__bid_default__") and rely on Redis cache misses to fall through to UNAWARE; (ii) thread campaign-category through cascade context to the aggregator (requires plumbing); (iii) lookup all categories for the user and aggregate.

**Q24 — archetype_accessor: pilot stub vs full build.** Stub returning PRAGMATIST collapses all users to one archetype, eliminating archetype-conditional predicate differentiation. Full build adds Neo4j writes, schema migration, and a write path on profile updates. **Adjudication options:** (i) ship pilot stub + a follow-up post-pilot build; (ii) implement minimal Neo4j read-only path (no write surface yet) that reads `User.user_archetype` if present and falls back to PRAGMATIST; (iii) implement full read+write path immediately.

---

## §14 Audit closure

W.0 closed. 13 slices total (12 implementation + S6.2.0 audit) + this audit memo. Branch HEAD `78dcbec` unchanged; only the new memo file in working tree. All claims cite `path:line`. §12 sequences W.1+ as 4 substantive slices (W.1 bundle, W.2 journey wrapper, W.3 archetype+maximizer interims, W.4 mindstate build with optional split). §13 surfaces 5 QUESTION-and-stop concerns for Claude Proper adjudication before W.1+ ships — Q20 (mindstate C+D field population) is the largest scope finding and should be adjudicated first since it shapes W.4. Awaiting Claude Proper W.1 prompt incorporating Q20-Q24 adjudications.
