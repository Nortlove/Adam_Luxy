# Retargeting Substrate Audit — 2026-05-04

**Slice:** S2 (read-only inspection per directive §S2)
**Branch:** `feature/hmt-dashboard` HEAD as of audit
**Auditor:** Claude Code (read-only; no code modifications)
**Deliverable:** This document
**Sign-off:** Pending Chris review per directive §S2 closure criterion ("audit doc exists, signed off by Chris, S8 slice list updated with concrete predecessor closures")

---

## Executive Summary

| # | Surface                                          | Shipped status | Plug-in seam for S8                               |
|---|--------------------------------------------------|----------------|---------------------------------------------------|
| 1 | Journey-state machine (Enh #10)                  | **~70%**       | `JourneyTrackingService` lookup by user_id        |
| 2 | `SequenceStep` models (Enh #28)                  | **~80%**       | `TherapeuticTouch` / `TherapeuticSequence`        |
| 3 | Bilateral per-archetype mechanism deployment     | **~50% (code) + 100% (docs)** | `bilateral_cascade.py` L1/L2/L3 + sequences extraction (S8.2) |
| 4 | Pixel-tracking integration                       | **~60%** (conversion-side only) | `webhook.py` postback handler + `pixel_correlator.py` (S4.1) |
| 5 | Decision-time cascade (Slice 24 seams)           | **100%**       | `BidComposer` / `CarryoverCorrectionStrategy` / `WashoutModel` Protocols + registry |

**Headline finding:** the substrate for S8 is more complete than the directive's "build retargeting v0" framing implies. The Slice 24 protocol seams (Surface 5) are fully shipped with default implementations + registry-pattern adapter swap. The bilateral cascade (Surface 3) is a 3909-line L1→L2→L3 implementation already in production. What's missing for S8 is mostly **integration**: wire the journey-state lookup + sequence-decision-node + bilateral-cascade output into a `RetargetingOrchestrator` that registers as a `BidComposer` adapter via the existing seam.

The pixel-tracking surface has the same gap surfaced by S0: **no impression-time URL log on the LUXY pilot.** Conversion-side webhook (`receive_conversion`) is fully wired; impression-side is the S4 ingestion-pipeline scope.

---

## Surface 1 — Journey-State Machine (Enhancement #10)

### Shipped status: ~70%

**Files:**
- `adam/user/journey/models.py` — Pydantic models
- `adam/user/journey/service.py` — `JourneyTrackingService`

**Models present:**
- `JourneyStage` (enum, line 19) — staged-funnel enum
- `to_conversion_stage(journey_stage)` (line 67) — conversion-stage mapping helper
- `DecisionUrgency` (enum, line 77)
- `JourneyState` (BaseModel, line 87) — the per-user state record
- `JourneyTransition` (BaseModel, line 116) — state transition record
- `UserJourney` (BaseModel, line 141) — full per-user journey aggregate

**Service:**
- `JourneyTrackingService` (line 79) — service surface for state read/write
- `get_journey_tracking_service()` (line 302) — singleton accessor

**Queryable by user_id and timestamp?** Service exists with `get_journey_tracking_service()` singleton accessor, and `UserJourney` aggregate suggests user-id-keyed read paths. **Confirmed queryable shape; specific async signatures need read in S8 design phase.**

**Gap:** the `MicroPsychologicalState` reframe per directive §S3 (page-priming-signature replaces spec-only MicroStateDetector at bid time) means journey state is one of two state inputs to the retargeting decision, not the only one. S8 design must treat journey state as one branch of `CellStateContext` (S8.1), not the entire context.

**Recommended S8 plug-in points:**
- `JourneyTrackingService.get_or_create_for_user(user_id)` → returns the current `UserJourney` for the bid-time context.
- `UserJourney.current_stage()` → feeds `CellStateContext` per S8.1.
- Transition emission: `JourneyTransition` records become `TrajectoryEvent` rows per S8.5.

---

## Surface 2 — `SequenceStep` Models (Enhancement #28)

### Shipped status: ~80%

**Files:**
- `adam/retargeting/models/sequences.py` — sequence + touch models
- `adam/retargeting/models/within_subject.py` — within-subject crossover models
- `adam/retargeting/models/intervention_record.py` — intervention records
- `adam/retargeting/models/site_profiles.py` — site profile models
- `adam/retargeting/models/telemetry.py` — telemetry models

**Models present (`sequences.py`):**
- `TherapeuticTouch` (BaseModel, line 30) — per-touch model (the directive's `SequenceStep` concept under a different name)
- `TherapeuticSequence` (BaseModel, line 134) — full sequence (the canonical per-archetype plan from `INFORMATIV — Bilateral Psycholinguistic Advertising Intelligence System .md`)
- `SequenceDecisionNode` (BaseModel, line 259) — branching decision-point in the sequence

**Naming note:** the directive's Enh #28 names the concept "SequenceStep"; the in-code naming is "TherapeuticTouch" / "TherapeuticSequence". The semantics align with the directive's intent (the Bilateral System's sequential mechanism deployment per archetype). **No name-translation slice is needed**; downstream code can import `TherapeuticTouch as SequenceStep` if literal directive naming is required.

**Persistence:** Pydantic BaseModels — serializable, but not yet bound to a persistence layer. Currently in-memory; S8.2 wires the per-archetype sequences from the bilateral doc into `adam/bilateral/sequences.yaml` + typed loader per directive.

**Relationships to Creative / Campaign / BilateralEdge:**
- `TherapeuticTouch` likely carries creative_id, campaign_id reference fields (need read at S8 design phase).
- `BilateralEdge` connection: in-code via `adam/api/stackadapt/bilateral_cascade.py` (Surface 3); the `TherapeuticSequence` is the consumer of the cascade's `level3` bilateral edge output.

**Recommended S8 plug-in point:**
- `MechanismDeploymentPlan` per S8.2 = a `TherapeuticSequence` instance per archetype, loaded from `adam/bilateral/sequences.yaml` (extracted from the bilateral doc as a one-time effort).

---

## Surface 3 — Bilateral Per-Archetype Mechanism Deployment

### Shipped status: ~50% (code) + 100% (documentation)

**Documentation source:**
- `INFORMATIV — Bilateral Psycholinguistic Advertising Intelligence System .md` — 263 lines at the repo root. Encodes the per-archetype sequential mechanism deployment (Status Seeker / Careful Truster / Easy Decider / Skeptical Analyst / Disillusioned).

**Production-code implementation:**
- `adam/api/stackadapt/bilateral_cascade.py` — **3909 lines** — the L1→L2→L3 bilateral cascade.

**Key entry points in `bilateral_cascade.py`:**
- `_select_primary_with_logged_propensity` (line 45) — TTTS top-two propensity-logging primary-mechanism selector
- `level1_archetype_prior(archetype)` (line 629) — L1 archetype-priors by name
- `level2_category_posterior(...)` (line 662) — L2 category-conditioned posterior
- `_query_trilateral_evidence_sync` (line 810) — L3 bilateral-edge query (the directive's L3 cascade)
- `_compute_page_shift_for_cascade` (line 880) — page-conditioning at decision time
- `extract_chain_attestations_from_atom_outputs` (line 994) — chain-attestation per the B3-LUXY discipline rule
- `apply_chain_attestations_to_mechanism_scores` (line 1030) — scoring application
- Helpers: `derive_framing_from_edges`, `derive_construal_from_edges`, `derive_tone_from_edges`, `derive_urgency_from_edges`, `derive_social_proof_density`, `derive_emotional_intensity`, `derive_mechanism_from_ad_profile`, `derive_lift_from_composite`

**Status:** the cascade is LIVE — the L1/L2/L3 logic, the TTTS propensity-logged primary selection, the page-shift integration, and the chain-attestation primitive are all in production. What is NOT yet structured-for-extraction is the per-archetype canonical sequences (which currently live in the documentation file as prose/tables).

**Recommended S8.2 plug-in:**
- One-time data-extraction effort: parse `INFORMATIV — Bilateral Psycholinguistic Advertising Intelligence System .md` for the 5 per-archetype canonical sequences → emit as `adam/bilateral/sequences.yaml` with a typed loader.
- The output of L3 (`_query_trilateral_evidence_sync`) becomes one input to `MechanismDeploymentPlan` selection at S8.3.

**Effort estimate for S8.2 (per directive):** 1.5d — round-trips through tests with sequence-order assertions for all 5 archetypes.

---

## Surface 4 — Pixel-Tracking Integration

### Shipped status: ~60% (conversion side fully wired; impression side is S4 scope)

**Inbound conversion webhook (LIVE):**
- `adam/api/stackadapt/webhook.py` (POST `/api/v1/stackadapt/webhook/conversion` per the file header):
  - `_LRUSet` (line 68) — event_id deduplication
  - `_verify_signature` (line 104) — HMAC-SHA256 auth per directive §0.5
  - `_validate_request` (line 110) + `_check_duplicate` (line 163) — security middleware
  - `_get_outcome_handler` (line 246) — singleton accessor for the 18-path learning consumer
  - `_lookup_decision_context_neo4j` (line 257) — Neo4j-backed decision-context lookup by `decision_id`
  - `PixelEvent` (BaseModel, line 348) — single-event payload
  - `BatchPixelEvents` (line 363) — batch payload
  - `WebhookResponse` (line 369) + `WebhookHealthResponse` (line 378)
  - `receive_conversion` (line 398) — single-event endpoint
  - `receive_conversions_batch` (line 530) — batch endpoint
  - `webhook_health` (line 616) — health check

**Attribution bridge (LIVE):**
- `adam/api/stackadapt/attribution_bridge.py`:
  - `validate_attribution_chain` (line 38)
  - `simulate_conversion_flow` (line 105)

**`sapid={SA_POSTBACK_ID}` URL-macro correlation (NEW per S4.1, just landed in commit `a2c9124`):**
- `adam/ingestion/stackadapt/pixel_correlator.py` — `PixelCorrelator` class joins inbound `PixelPostback` to last-served impression by `sapid`.
- `PixelPostback` + `CorrelatedConversion` frozen dataclasses defined.
- Lookup is injectable (`LookupFn`) for S4.4's Postgres rollup to bind to.
- `coverage_rate(results)` helper for the §S8.7 join-diagnostics surface.

**Critical gap (re-confirmed by S0 live extraction):**
There is **no impression-time pixel log** for the LUXY pilot. The webhook receives CONVERSION events only. URL granularity at impression-fire time is not captured anywhere in the current production stack — this is the §S0_HANDOFF Section 5 finding ("StackAdapt is not populating page-context data for our pilot account; this is a permanent constraint of the data we get from this DSP for this pilot"). This gap is the specific blocker that the next-conversation G1-pivot adjudication must address.

**Recommended S8 plug-in points:**
- S8.4 (`pixel postback wiring end-to-end`) = wire the `PixelPostback` ingestion through `webhook.py` → `PixelCorrelator.correlate_one()` → join to last-served impression via S4.4's Postgres lookup → emit `TrajectoryEvent` per S8.5.
- The sapid round-trip itself is currently functional via the conversion-event webhook; what S8.4 adds is the **correlation step** (sapid → impression record), not the receiver.

---

## Surface 5 — Decision-Time Cascade (Slice 24 Seams)

### Shipped status: 100%

**Protocol seams (all in `adam/intelligence/v3_interfaces.py`):**

| Protocol                       | Default Implementation         | Register fn                              | Get-active fn                          |
|--------------------------------|--------------------------------|------------------------------------------|----------------------------------------|
| `BidComposer` (line 86)        | `_DefaultKellyBidComposer` (127) | `register_bid_composer` (362)            | `get_active_bid_composer` (358)        |
| `CarryoverCorrectionStrategy` (229) | `_DefaultCarryoverStrategy` (249) | `register_carryover_strategy` (378)      | `get_active_carryover_strategy` (374)  |
| `WashoutModel` (284)           | `_DefaultWashoutModel` (304)   | `register_washout_model` (396)           | `get_active_washout_model` (392)       |

**Test-isolation helper:**
- `reset_to_defaults_for_tests()` (line 408) — resets all three registries to defaults for test runs.

**Slice 35 shadow-mode bidder (`shadow_bidder.py`):**
- `ShadowBidRecord` (BaseModel, line 123) — dual-persistence record (alongside DecisionTrace per directive Appendix F).
- `ShadowBidSubmitResult` (line 141) — submit result envelope.
- `_capture_active_composer_name` (line 182) — captures which composer adapter is registered for the audit trail.
- `submit_shadow_bid` (line 197) — async shadow-bid submission.
- `submit_shadow_bid_sync` (line 291) — sync wrapper.
- `load_shadow_bid` (line 373) — read-back accessor.

**DecisionCache (`decision_cache.py`):**
- `DecisionContext` (line 38) — per-decision context record
- `DecisionCache` (line 207) — cache surface
- `get_decision_cache()` (line 455) — singleton accessor
- Decision-id-keyed entry; webhook `_lookup_decision_context_neo4j` consumes this for cross-event attribution.

**Recommended S8 plug-in point:**
- `RetargetingOrchestrator` (the directive's missing piece) = a class that:
  1. Reads `JourneyTrackingService` for current state (Surface 1).
  2. Reads cell classifier output (S6) and `URLPostureClassifier` output (S0/S3.1) for `CellStateContext`.
  3. Selects next `TherapeuticTouch` from the per-archetype `TherapeuticSequence` (Surface 2 + Surface 3 sequences.yaml).
  4. Uses `bilateral_cascade.py`'s L3 evidence + chain-attestation for mechanism scoring.
  5. Implements the `BidComposer` Protocol via composition.
  6. Registers itself via `register_bid_composer(orchestrator)` at startup, conditional on a feature flag.
  7. Logs every decision via `submit_shadow_bid()` (Slice 35) + `DecisionCache.persist()` for the dual-persistence audit trail.

The `RetargetingOrchestrator` IS the entire S8 build — every other piece exists.

---

## Composite Recommendations for S8 Slice Plan Refinement

The directive's S8 has 7 slices (S8.1–S8.7). With the substrate audit complete, the predecessor-closure list per slice can be made more concrete:

| S8 slice                          | Substrate predecessor              | Status |
|-----------------------------------|------------------------------------|--------|
| S8.1 `CellStateContext` composite | Surface 1 `JourneyTrackingService` + cell classifier (S6, blocked) + page-priming (S3, partial via S3.1) | Partial — cell classifier blocked |
| S8.2 sequences.yaml extraction   | Surface 3 doc + Surface 2 `TherapeuticSequence` model | **READY** — pure data-extraction effort |
| S8.3 deterministic next-touch     | S8.2 + Surface 3 `bilateral_cascade.py` L3 | Ready once S8.2 lands |
| S8.4 pixel postback wiring        | Surface 4 webhook + S4.1 `PixelCorrelator` | Ready (PixelCorrelator just shipped) |
| S8.5 `TrajectoryEvent` logging    | Surface 1 `JourneyTransition` + Surface 4 correlator + Stage C event bus (S4.5, blocked) | Partial — Stage C bus blocked |
| S8.6 validation harness           | All of S8.1-S8.5 + S0 historical corpus | Blocked — needs S0 G1 corpus pivot |
| S8.7 sandbox round-trip + Slice 35 | Surface 4 + Surface 5 shadow_bidder | **READY** — both already shipped |

**Net assessment:** S8.2, S8.4, and S8.7 are READY (independent of the G1 pivot). S8.1, S8.3, S8.5, S8.6 carry blockers that resolve as S6 / S4.5 / S3.2-S3.6 close. The G1-pivot adjudication in the next conversation determines the corpus-side blockers.

---

## Closure (per directive §S2 success criterion)

- **Audit document exists:** ✓ (this file).
- **Sign-off pending:** Chris review.
- **S8 slice list updated with concrete predecessor closures:** ✓ (composite recommendations table above).

**Standdown per §S2 mandate:** No code modification performed during this audit. Will not begin S8 build until Chris signs off and Claude Proper issues the S8.1 prompt.

---

## Sign-off Addendum — 2026-05-11

**Operator:** Chris Nocera, CTO & Co-Founder, INFORMATIV Group.
**Sign-off:** G2 closed per directive Part 8. S8 build authorized to proceed.

### Current-state S8 predecessor table (refinement of 2026-05-04 composite recommendations table)

Per `HANDOFF_TO_NEW_THREAD_2026_05_11.md` §5 / §6 / §13, three rows in the 2026-05-04 composite recommendations table reflected substrate state that has advanced since the audit was written. The table below corrects those rows for the post-2026-05-11 build window; the remaining rows are restated unchanged.

| S8 slice | Substrate predecessor | Status as of 2026-05-11 |
|---|---|---|
| S8.1 CellStateContext composite | `JourneyTrackingService` + S6 substrate (F.1 `1988a8d` + S6.2 `78dcbec`) + S3 priming | **READY** — 1d |
| S8.2 `sequences.yaml` extraction | Bilateral doc + `TherapeuticSequence` model (Surface 2) | **READY** — 1-1.5d |
| S8.3 deterministic next-touch | S8.2 + `bilateral_cascade.py` L3 (Surface 3) | **Ready once S8.2 lands** — 1d |
| S8.4 pixel postback wiring | `webhook.py` (Surface 4) + `PixelCorrelator` (`a2c9124`) | **READY** — 1-1.5d |
| S8.5 `TrajectoryEvent` logging | `JourneyTransition` + correlator + S4.5 Stage C event bus | **Defers to S9** per directive substrate-blocking sequence; pre-pilot uses the existing `decision_trace` channel |
| S8.6 validation harness | S8.1-S8.4 + G1.path4 corpus (`57e43bf`) + Becca analytics | **READY** — 1-1.5d |
| S8.7 sandbox round-trip + Slice 35 | Surface 4 + Surface 5 `shadow_bidder` | **READY** — 1-1.5d |

### Substrate-state changes since 2026-05-04

1. **Cell classifier substrate shipped.** F.1 cell taxonomy (`1988a8d`), F.2 compensatory cohort detection (`1c49a75`), S6.2 `CellFeatureSet` + `@cell_predicate` evaluator + Path A integration in `bilateral_cascade.py` (`78dcbec`), W chain substrate accessors (`e0f0e52`, `60b1ac0`, `bdd24a0`, `b1c9922`), M.1 aggregator-side `fomo` derivation (`0ad0919`). S8.1 no longer cell-classifier-blocked.

2. **G1 closed via Path 4** at commit `57e43bf` (macro-AUC 0.788, top-1 0.46 on the held-out fixture) — a class-balanced retrain on the existing posture corpus, not the Slice-0 real-URL extraction. The P.0/P.1 corpus-pivot conversation referenced in the 2026-05-04 audit's S8.6 row was held; URL granularity surfaced via P.0 (`64b6daa`) and was addressed via P.1 cold-start mapper (`b85cce3`) plus inventory (`fbae83e`). S8.6 no longer corpus-blocked.

3. **S8.5 deferral made explicit.** Per directive §0.5 (acknowledged tech debt) + the substrate-blocking sequence, full `TrajectoryEvent` logging defers to S9. Pre-pilot S8 uses the existing `decision_trace` channel as the interim observability path. Not a remediation gap; an architectural deferral.

### G2 closure declaration

Per directive Part 8 Gate G2 ("Retargeting audit reports signed off by Chris"):
- ✓ Audit document exists (this file).
- ✓ Signed off by Chris (this addendum).
- ✓ S8 slice list updated with concrete predecessor closures (table above).

**G2 closed 2026-05-11. S8 build authorized to proceed. Next slice: S8.2 (sequences.yaml extraction) per handoff §6 item 3.**
