# MEMORY.md — Claude Code Session Persistence

> **THE DIRECTIVE.** The single canonical operational directive for this build is:
> **`docs/CLAUDE CODE DIRECTIVE v3.1.md`** (effective 2026-05-04, supersedes v3, formally retires v2).
>
> **No other roadmap, plan, phase, sequence, or directive document carries authority.** Past drift to alternative roadmap documents cost months. The proliferation pattern (multiple plan files surviving alongside the directive) is the drift mechanism. See "Removal Candidates" section below for the documents that compete with v3.1 for authority and should be deleted to prevent re-drift.
>
> Operating discipline + theoretical foundation + audit-memo references compose with the directive — they are NOT roadmap docs and are preserved.

---

## Operating Pattern (Directive §0.4)

- **Claude Proper (claude.ai)** writes prompts. Never modifies code directly.
- **Claude Code (this surface, in Cursor IDE)** executes. Never makes architectural decisions. Raises `QUESTION:` and stops when ambiguous.
- **Chris** arbitrates. Pastes status reports back to Claude Proper.

## Session Discipline (Directive §0.3)

- One slice = one commit. Conventional-commit format. Never amend, never rebase, never bundle, never `--no-verify`.
- 4380+ test baseline; failed tests block commits; new code ships with new tests.
- Status reports use exactly five states: `NOT_STARTED` / `IN_PROGRESS` / `BLOCKED` / `READY_FOR_REVIEW` / `CLOSED`.
- Every commit body: slice ID, predecessor slices closed, test-suite delta, one-line "why this slice now."
- Every session ends with an EVE block (Executed / Verified / Expected-next).

---

## Session Index

- 2026-05-04 — session #001 (this session: directive read, MEMORY.md created)

## Current State

- Active branch: `feature/hmt-dashboard`
- Active slice: **Session #004 CLOSED** (8 slices shipped + EVE handoff `e85b4d0` + this standdown-record commit)
- Last commit on branch: this commit (close session #004 EVE handoff record)
- Test suite: ~4831+ passing (added +133 across session #004's 8 slices); 9 pre-existing failures unchanged
- Open QUESTIONs: QUESTION 4 still standing (S1 gate-failed); next conversation adjudicates G1 pivot
- Critical-path next: **G1-pivot adjudication in next conversation** (paste `docs/S0_HANDOFF_2026_05_04.md` + operational architecture doc per Closing Block)
- Standstill items (resume after Claude Proper adjudication / amended slice prompts): S1 build, directive-amendment slice, S0 G1-pivot architecture, S8 build (audit signed off pending Chris review per S2 closure criterion)

### Architecturally consequential carry-forward (session #004 → next)

**S2 audit collapsed S8's scope.** The retargeting substrate audit (`docs/RETARGETING_AUDIT_2026_05_04.md`) found Surface 5 (decision-time cascade) 100% shipped — `BidComposer` / `CarryoverCorrectionStrategy` / `WashoutModel` Protocols + default implementations + registry-pattern adapter swap all live in `adam/intelligence/v3_interfaces.py`. The bilateral cascade (Surface 3) is a 3909-line L1→L2→L3 implementation already in production with TTTS propensity-logged primary selection, page-shift integration, and chain-attestation primitive. The journey-state machine (Surface 1) and TherapeuticTouch/TherapeuticSequence models (Surface 2) are both ~70-80% shipped. The `PixelCorrelator` (Surface 4) just shipped in S4.1 (`a2c9124`). **Net:** S8 reduces from "build retargeting v0" to "wire `RetargetingOrchestrator` that registers as a `BidComposer` adapter via the existing Slice 24 seam, composing journey-state + cell classifier + page-priming + sequence selection + bilateral cascade L3 + chain-attestation, with shadow-mode logging via Slice 35." Every other piece exists. This is the architecturally consequential framing the next session should authorize against.
- Substrate-blocked deferred (per directive): S3.2-S3.6 (URL corpus dependent), S4.2-S4.8 (Iceberg/Neo4j/Postgres + IPSW + e2e + live backfill), S5/S6/S7/S8/S9/S10 chain, 1.A.SB.1 / 1.B.SB.1 / 1.C.SB.1 / 1.D.SB.1 / 1.E.SB.1 / 1.F.SB.1 / 1.G.SB.1 / 1.H.SB.1 (all SB items)
- Substrate-independent v3 Phase 1 items remaining for next session(s): 1.A.SI.2 (Gross-Vitells LEE — depends on 1.A.SI.1 just shipped), 1.B.SI.1, 1.C.SI.1, 1.D.SI.1, 1.E.SI.1, 1.F.SI.1, 1.G.SI.1, 1.H.SI.1

## Critical Path (Directive Part 2)

```
S0 → S1 → S6 → S8 → Gate G3 (LUXY ad-serving begins)
                ↑
S2 → ──────────┘
S3, S4, S5 in parallel; v3 Phase 1 SI sub-work-streams fill compute
```

## Gates (Directive Part 8 — never auto-traversed; surface to Chris for each)

- **G0** Slice 0 closed; `READY_FOR_RATER_WORKSHEET.flag` written → unlocks S1
- **G1** Criterion (ii): macro-AUC ≥ 0.50 AND top-1 ≥ 0.40 on domain-isolated held-out → unlocks S6 + posture-dependent SB sub-work-streams
- **G2** Retargeting audit signed off → unlocks S8 build
- **G3** S8 ships + Pixel round-trip validated + p99 latency met + shadow-mode logging operational → unlocks LUXY ad-serving
- **G4–G8** see directive Part 8

---

## Acknowledged Technical Debt — DO NOT Surface as Findings (Directive §0.5)

These are tracked, intentionally deferred, and will be re-opened on schedule. Do not append them to drift logs, do not propose impromptu remediation:

1. Spec-only `MicroStateDetector` at bid time — replaced by page-priming-signature lookup (S3); live user-state deferred to **2.E.S1** (post-impression telemetry from Enhancement #08).
2. Enhancements #10 / #02 / #07 / page-priming at 5–25% shipped — completion is the explicit subject of S3, S6/S7, S8.
3. Enhancement #09 100ms p99 five-tier fallback — fixed envelope; do not re-litigate mid-build.
4. Synthetic-URL labeling exercise on hold — **`round_3_diversification_candidates.jsonl` to be replaced wholesale by S0 output, NOT relabeled or repaired**.
5. Inbound-only StackAdapt data architecture — `sapid={SA_POSTBACK_ID}` URL-macro pattern; no outbound webhooks.
6. Claude API in offline pipeline only — never in real-time inference path.
7. Bilateral mechanism deployment as documentation today — S8.2 extracts to queryable structures (one-time).
8. Cross-tenant prior infrastructure has no second tenant yet — synthetic in S9; live waits until Gate G8.

---

## Theoretical / Operating References (Preserved — compose with the directive)

These are NOT roadmap docs. The directive's rigor is anchored against these:

- `ADAM_AGENT_ORIENTATION.md` — antipattern catalog (A1–A15), keystroke-discipline checks
- `ADAM_THEORETICAL_FOUNDATION.md` — Bargh-lineage (automated nonconscious goal pursuit, correlation-vs-inference, two-sided bilateral architecture)
- `ADAM_HUMAN_MACHINE_TEAMING_FOUNDATION.md` — partner-side cognition; user-self-reports-as-hypotheses; joint cognitive system as unit of analysis
- `ADAM_CORE_PHILOSOPHY.md` — platform philosophy
- `docs/ADAM_DEVELOPMENT_GUARDRAILS.md` — guardrails
- (Methodology substance previously held in `docs/handoff/Seven-Component...pdf` is now encoded directly in v3.1 — Howard-Ramdas confidence sequences §S9.8, IPSW Item J §S4.6, BONG §S7.2, AR(1) per-user §S9.4, EBGM/MGPS §G.3, Hill / Mager-Jusko / Dayneka-Garg-Jusko §1.F, Gross-Vitells LEE §1.A, Daw two-system §1.G, etc.)

## Audit Memos Cited by the Directive (Preserved)

- `docs/CRITERION_II_STATUS_CORRECTION_2026_05_02.md` — directive Appendix F line 1005
- `docs/STATE_DETECTION_AUDIT_2026_05_03.md` — produced 2026-05-03; subsumed by directive's S3 reframe + 2.E.S1 deferral; preserved for historical context

---

## Competing-Authority Doc Purge — Completed 2026-05-04

Structural defense against re-drift. Past pattern: surviving alternative plans drove sequencing of pilot work toward CUT items ("Directive is the ONLY roadmap" rule, origin 2026-04-30, re-confirmed 2026-05-04).

**Removed (24 files + 2 directories):**

- Top-level alternative plans / session scaffolding (15 files): `ADAM_COMPREHENSIVE_AUDIT.md`, `ADAM_EXECUTION_PLAN.md`, `ADAM_REBUILD_MASTER_PLAN.md`, `ADAM_SESSION_RESTORE.md`, `ADAM_SESSION_STATE.md`, `ADAM_SESSION_TEMPLATES.md`, `ADAM_STAGE_1_POST_WIRING_VERIFICATION.md`, `ADAM_STAGE_1_WIRING_PLAN.md`, `ADAM_STRATEGIC_FOUNDATION.md`, `ADAM_UNDERUTILIZATION_AUDIT.md`, `ADAM_VERIFICATION_LOG.md`, `CRASH_RECOVERY.md`, `INGESTION_PLAN_AND_POSITION.md`, `RESUME_STATE.md`, `SESSION_WORK_SUMMARY.md`
- `docs/` competing directive/plan files (4 files): `docs/CLAUDE_CODE_DIRECTIVE_FULL_BUILD.md` (prior directive), `docs/COMPREHENSIVE_BUILD_INVENTORY.md`, `docs/PHASE 1 & PHASE 2.md`, `docs/PHASE_TRANSITION_MODEL.md`
- Borderline historical audit/verification (2 files): `ADAM_INTEGRATION_AUDIT_2026-04-15.md`, `ADAM_Integration_Bridge_ReVerification_Report.md`
- Directories: `central_plan/` (entire — was 0 tracked, fully untracked), `docs/handoff/` (entire — including the methodology canon PDF; substance now encoded in v3.1 directly)

**Tracked deletions (8) staged in git index awaiting commit; untracked deletions (16+ files in central_plan/, 5 in docs/handoff/, 13 top-level/docs untracked) gone permanently.**

**Forward rule:** never write another roadmap/plan/sequence/phase document. Slice work happens in commits per directive §0.3, not in plan files. EVE handoffs go in this MEMORY.md only.

---

## Per-Session Append (newest at bottom)

### Session 2026-05-04 — session #004 — Parallel-execution discipline: 8 slices shipped

**EVE Handoff:**

- **E (Executed):** 8 slices closed, in ship-cleanest-first order:
  1. `38496bf` **G.1 DMC charter draft** — 5-page docs/governance/DMC_CHARTER_DRAFT.md (authority, composition, blinding, stopping rules, conflict-of-interest, meeting cadence; references DuMouchel 1999 / Howard-Ramdas 2021 / Johari-Pekelis-Walsh 2017 / CONSORT-AI 2020 / SPIRIT-AI 2020)
  2. `5cf4a87` **G.4 CONSORT-AI + SPIRIT-AI templates** — docs/reporting/{CONSORT,SPIRIT}_AI_TEMPLATE.md, fill-in-as-data-accumulates with cross-document linkages enforcing pre-spec ↔ results ↔ governance triangle
  3. `d6f8815` **G.3 pharmacovigilance schema** — adam/pharmacovigilance/{__init__,schema}.py + tests with PRR/ROR/IC/IC025/EBGM-naive computations + (creative × cohort × posture × cell) grain pin (28 tests)
  4. `cc16e81` **S0 Handoff Consolidation** — docs/S0_HANDOFF_2026_05_04.md per Chris's spec; full Coverage Gap (all 202 publisher domains) preserved verbatim; paste-target for next-conversation G1-pivot adjudication
  5. `2df66d5` **S3.1 PagePrimingSignature** — adam/priming/{__init__,signature}.py + tests; frozen dataclass with §S3.1 dimensions verbatim, range invariants enforced, feature-store row round-trip, neutral_signature cold-miss fallback (31 tests)
  6. `a2c9124` **S4.1 ingestion package skeleton** — adam/ingestion/stackadapt/{rate_limited_session, historical_puller, incremental_puller, pixel_correlator}.py using corrected S0 schema patterns from 54407ac; PixelPostback + CorrelatedConversion + coverage_rate (13 tests)
  7. `48f7e4e` **S2 retargeting substrate audit** — docs/RETARGETING_AUDIT_2026_05_04.md; read-only inspection of 5 surfaces; net finding "S8 = wire RetargetingOrchestrator that registers as BidComposer adapter via existing Slice 24 seam — every other piece exists"
  8. `c55a4b3` **1.A.SI.1 blind-analysis box** — adam/blind_analysis/{__init__,box}.py + tests; SHA-256 pre-registration hash, SEALED→AUTHORIZED→UNBLINDED state machine gated by CTO authorization per G.1 §3, deterministic placeholder data generator (19 tests). Substrate for 1.A.SI.2 (Gross-Vitells LEE).

  **Total: +133 tests** all passing. Test suite ~4831+ baseline.

- **V (Verified):**
  - All 8 slice tests pass independently and in batch (133/133).
  - 9 pre-existing failures unchanged (TestCampaignDocs + test_dag_has_14_atoms — confirmed pre-existing on baseline `9159758` in session #003).
  - No regressions on existing stackadapt tests (88/88 still pass — ran spot check after extending graphql_client.py in S0 #003 session; S4.1 reuses the same client without modification).
  - Each commit body follows directive Appendix D format (slice ID, predecessors closed, test-suite delta, why this slice now, body content).
  - Working tree clean at standdown except for this MEMORY.md update (uncommitted; picked up by next slice's commit per Appendix E pattern, OR by an explicit chore commit at session boundary — Chris's call).

- **E (Expected next session):**
  - **Primary** — next conversation adjudicates G1 pivot per `docs/S0_HANDOFF_2026_05_04.md` Closing Block. Expected attached input: that document + the operational architecture doc (StackAdapt API exploitation / permanent learning pipeline / cell-classified retargeting / substrate audit-and-build) named in the Closing Block.
  - **Secondary parallel work-stream remaining for compute-fill** if Chris wants more autonomous SI ship-runs:
    - 1.A.SI.2 Gross-Vitells LEE trial-factor (now unblocked by 1.A.SI.1 shipped this session)
    - 1.B.SI.1 / 1.C.SI.1 / 1.D.SI.1 / 1.E.SI.1 / 1.F.SI.1 / 1.G.SI.1 / 1.H.SI.1 (independent of each other)
  - **Held until adjudication:** S1 build, S8 build, directive-amendment slice, G1-pivot architecture.

- **Open QUESTIONs:** QUESTION 4 (S1 entry-condition gate-failed) still standing. No new QUESTIONs from session #004 work — all 8 slices either shipped clean or surfaced findings into their summary artifacts.

- **Hand-off pointer:** Branch `feature/hmt-dashboard` at `c55a4b3`. 8 slices shipped this session beyond the standdown anchor `0a17bab`. Working tree clean except docs/MEMORY.md (this update). Five-artifact handoff list canonical for next-conversation paste:
  1. `docs/S0_HANDOFF_2026_05_04.md` (consolidated; all 202 Coverage Gap domains preserved)
  2. `docs/RETARGETING_AUDIT_2026_05_04.md` (S2 audit; informs S8 sequencing)
  3. `docs/governance/DMC_CHARTER_DRAFT.md` (governance scaffold)
  4. `docs/reporting/{CONSORT,SPIRIT}_AI_TEMPLATE.md` (pre-spec ↔ results triangle)
  5. The corrected schema patterns embedded in `adam/integrations/stackadapt/graphql_client.py` and inherited by S4.1 + S0 CLI.

- **Procedural lesson re-confirmed:** all session-#004 commits used proper Appendix D format with predecessor-closure list + test-suite delta. No `git stash` operations were attempted (avoiding the session-#003 pop-without-list-check trap by simply not invoking stash at all this session).

---

### Session 2026-05-04 — session #003 — S0 amended slice CLOSED (commit 54407ac)

**EVE Handoff:**

- **E (Executed):**
  - Phase 1 (audit): introspected ConversionPathFilters / AdFilters / CampaignFilters / DateRangeInput / enum types; audited pixel infrastructure; located LUXY advertiser ID (`122463`); added `STACKADAPT_ADVERTISER_ID=122463` to `.env` (gitignored).
  - Phase 2 (client extension): added 3 methods to `adam/integrations/stackadapt/graphql_client.py` per §1.3 ("small additions to existing client") — `_query_with_retry`, `get_conversion_paths_page`, `get_campaign_page_context_page`. Schema-corrected from directive's stale assumptions: conversionPath has NO touchpoints (single conversionUrl per record); DateRangeInput uses `{from, to}`; enums are `{GRAPH, TABLE}` and `{DAILY, ..., WEEKLY}`; `groupBy` is not a Query.adDelivery arg.
  - **Source 3 reframe:** directive's `adDelivery` domain rotation does NOT work against live schema (AdDeliveryRecord has no domain field, no `groupBy` arg). `campaignPageContext` IS the population-level URL surface (`CampaignPageContextRecord.url` verified) — Source 3 reframed; documented in client docstring + commit body + summary artifact.
  - Phase 3 (CLI): wrote `tools/stackadapt_historical_extract.py` (~440 lines) — orchestrates 3 sources, dedup + HEAD validation, URLPostureClassifier diversity audit, 7-section summary, machine-readable flag.
  - Phase 4 (tests): 6 test files in `tests/integrations/stackadapt/` covering pagination + jitter retry + UNION resolution + pixel-audit semantics + diversity-gate verdicts (parametrized over threshold) + summary-section invariants + flag-format + semantic consistency. **42 tests, all passing.**
  - Phase 5 (live run): executed against LUXY production GraphQL (key in .env). 12 LUXY campaigns visible. 285 conversion-path raw rows → **only 6 unique URLs** (all variants of `https://luxyride.com/ride-details` with UTM tags). Source 3 returned 0 (Progress polled 5×; resolved to empty Outcome). Diversity gate FAILED (5/5 classes below 30 minimum). **Coverage Gap section captured 200+ publisher domains** (CNN, foxnews, ESPN, CBS Sports, Cleveland Clinic, Hulu/DirectTV bundles, etc.) where ads served but no URL captured — the S4 ingestion-pipeline target list.
  - Phase 6 (commit): `54407ac feat(stackadapt): S0 amended schema-grounded URL extraction with multi-source provenance and diversity gate` — 14 files, +2369. Per §I single-slice closure; ready/gate_grade/calibration_grade/posture_diversity_inadequate all written to flag.

- **V (Verified):**
  - §1.1 introspection ping PASS.
  - §1.2 schema mismatch fully resolved by introspection-driven query rewrite.
  - URL classifier checkpoint located at `artifacts/posture_classifier/posture_classifier_n100_1777759342.jsonl`.
  - All 6 unique URLs HTTP HEAD validated 200.
  - Diversity audit run on the 6 URLs: all classified as `INFORMATION_FORAGING` by the round-3 default-to-INFO bias (consistent with the documented checkpoint behavior).
  - Per directive §I criteria, S0 closed: all 3 sources ran (Source 2 N/A documented), all 4 artifacts at canonical paths, flag written with valid key=value, test suite green.
  - 9 pre-existing test failures (TestCampaignDocs against `campaigns/ridelux_v6/*` JSON files + test_dag_has_14_atoms) confirmed PRE-EXISTING on baseline `9159758` — unaffected by S0 work.

- **E (Expected next session):**
  - **S1 begins.** S1.1 (worksheet generator) must read `READY_FOR_RATER_WORKSHEET.flag` as its first action. Current flag content: `ready=false, gate_grade=false, calibration_grade=true, posture_diversity_inadequate=true`. Per binding amendment S1 must STOP and surface a QUESTION naming the under-served classes (all 5) and per-class counts (INFO=6, others=0).
  - Chris adjudicates: (a) corpus expansion strategy (e.g., supplement from RSS feeds per round-3 history; pull from another LUXY-adjacent advertiser if any; manually augment with marketing-page URLs); (b) accept calibration_grade for S1 tooling iteration only; (c) other.
  - **Directive amendment slice** `docs(directive): v3.1 §1.2/§1.4/§1.5 schema-amendment` is the next standalone slice to capture the schema corrections in directive text so S4 inherits the corrected spec.

- **Open QUESTIONs:** none for S0 (closed); QUESTION-on-flag is S1's responsibility to surface when its first action runs.

- **Hand-off pointer:** S0 closed at `54407ac`. Coverage Gap section in summary names the S4 ingestion-pipeline scope concretely (200+ domains). Branch ready for S1.

- **Procedural gotcha (record for future sessions):** `git stash pop` without confirming the top stash is yours can apply someone else's pre-existing stash to your working tree. The pre-existing `stash@{0}: On 2026-01-26-fxqi: Pre-inferential-intelligence uncommitted work` was popped accidentally during a regression-isolation step; required surgical `git checkout HEAD -- <each file>` to restore 43 files while preserving my work in `graphql_client.py` + untracked `tools/` + `tests/integrations/`. Lesson: **`git stash list` BEFORE `git stash pop`**; if a top stash isn't from this session, do not pop it.

---

### Session 2026-05-04 — session #002 — S0 §1.1 ping + schema mismatch surfaced

**EVE Handoff:**

- **E (Executed):**
  - Per Chris instruction "go forward and follow the instruction": ran §1.1 introspection ping live against `https://api.stackadapt.com/graphql` using existing `StackAdaptGraphQLClient` (no parallel client per §1.3). PASS — `queryType.name = Query`, 60 query fields enumerable.
  - Three rounds of schema introspection: (R1) confirm `deliveryReportImpressionLevel` exists/not-exists; (R2) probe args + return types of all four `*Delivery` candidates + `AdDeliveryPayload` shape + scan for url/page/site/host/inventory naming; (R3) probe `conversionPath` + `campaignPageContext` to find URL-bearing surfaces.
  - Wrote `docs/S0_SCHEMA_MISMATCH_REPORT_2026_05_04.md` — self-contained artifact for Claude Proper with: §1.1 PASS confirmation, the field-name gap (Q1 field non-existent), the four real `*Delivery` fields' actual signatures, the only URL-bearing cursor-paginated surface (`conversionPath`), three schema-grounded paths α/β/γ, and recommendation of γ.

- **V (Verified):**
  - Auth: `STACKADAPT_GRAPHQL_KEY` (64 chars) loaded from `.env`; `is_configured` is a `@property` (not a method — caught and corrected during round 1).
  - Field-name gap: `Query.deliveryReportImpressionLevel` returns `{}` from introspection. Real fields: `adDelivery / advertiserDelivery / campaignDelivery / campaignGroupDelivery` — all share args `(dataType, date, filterBy, granularity)`, none take `breakdowns/after/first`, none expose URL-level row granularity. `conversionPath` is the only Relay-cursor-paginated URL-bearing field.
  - No code committed; no tests run; no slice closure claimed. State = BLOCKED per §0.3.

- **E (Expected next session):**
  - Chris pastes `docs/S0_SCHEMA_MISMATCH_REPORT_2026_05_04.md` into Claude Proper.
  - Claude Proper adjudicates between Path α (conversionPath-based — biased to bottom-of-funnel), Path β (adDelivery + campaignPageContext — depends on unconfirmed field shape), Path γ (directive amendment — slowest, cleanest).
  - Claude Proper writes amended S0 prompt; Claude Code executes the amendment.
  - Optional interim: Claude Proper may authorize a calibration-only Path α run in parallel with the amendment cycle (must be flagged calibration-only, not for G1 closure).

- **Open QUESTIONs:**
  - **QUESTION 3:** Which path (α / β / γ) for S0 against the live StackAdapt GraphQL schema? Decision criterion includes posture-class representativeness for downstream G1 closure.

- **Binding amendment from Chris (2026-05-04, mid-session):** S0 §1.5/§1.7 + S1 §1.8 entry-condition amended with **posture-class diversity audit**. After URL extraction completes, S0 runs ContentProfiler offline pass against `unique_urls.jsonl`, emits per-posture-class counts in summary, and writes `posture_diversity_inadequate=true|false` key=value into `READY_FOR_RATER_WORKSHEET.flag`. If true, S1.1 stops and surfaces a QUESTION before producing the rater worksheet. Per-class minimum: 30 URLs (5-class total minimum: 150). `INFORMATION_FORAGING` and `LEISURE_BROWSING` are the empirically most-at-risk classes (round-3 held-out: 49/50 collapsed to INFO_FORAGING because other classes lacked calibration evidence) — and exactly the two classes Path α's conversion bias would systematically under-sample. ContentProfiler verified to exist at `adam/platform/intelligence/content_profiler.py:56`; 5-class taxonomy canonical names confirmed at `adam/intelligence/posture_five_class.py:106`. Full amendment text in `docs/S0_SCHEMA_MISMATCH_REPORT_2026_05_04.md` "Binding Amendment" section.

- **Hand-off pointer:** S0 BLOCKED at field-name gap + diversity-gate amendment binding. Schema-mismatch report (now including binding amendment) at `docs/S0_SCHEMA_MISMATCH_REPORT_2026_05_04.md`. No code work pending Claude Proper adjudication of QUESTION 3.

**Mid-session resolutions from Chris (2026-05-04):**
- **Canonical-classifier resolution:** `URLPostureClassifier` (`adam/intelligence/posture_five_class.py`) is canonical for the diversity audit. NOT ContentProfiler-direct. The round-3-pre-rotation checkpoint caveat (held-out macro-AUC 0.7980, top-1 0.22, 49/50 collapsed to INFO_FORAGING) must be inscribed in the S0 emitted summary artifact. Diversity-gate bias is conservative-for-purpose: a firing gate ⇒ inadequate corpus (high confidence); a passing gate ⇒ minimum-bar cleared but per-class counts carry classifier-default-to-INFO bias.
- **Three constraints binding the not-yet-issued amended S0 prompt** (Claude Proper must incorporate ALL three):
  1. **Hybrid γ + α-as-calibration** — Path γ (directive amendment against real schema) is the primary path; Path α (conversionPath-based pull) is authorized in parallel as a **calibration-only artifact**, NOT for G1 closure. Calibration-only flag must be on every output.
  2. **Posture-class diversity audit using URLPostureClassifier** with round-3-checkpoint caveat per the binding amendment.
  3. **Multi-source provenance with `source` field on every row** of the emitted JSONL — every row carries the data source (e.g., `"source": "stackadapt.conversionPath.touchpoint"`, `"source": "stackadapt.adDelivery+campaignPageContext"`, etc.) so downstream consumers can stratify by source and re-evaluate without re-deriving.

**Standdown state:** Claude Code is at hard standdown until the amended S0 prompt arrives from Claude Proper. No autonomous S0 work; QUESTION 3 + the three binding constraints adjudicated via Claude Proper.

---

### Session 2026-05-04 — session #001 — directive transition

**EVE Handoff:**

- **E (Executed):**
  - Read `docs/CLAUDE CODE DIRECTIVE v3.1.md` end-to-end (1020 lines).
  - Acknowledged operating model: Claude-Proper-writes / Claude-Code-executes / Chris-arbitrates.
  - Created this `docs/MEMORY.md` per directive Appendix E with v3.1-only flag, operating-pattern summary, session index, current-state block, critical-path graph, gate list, technical-debt list, theoretical-reference list, audit-memo list, this EVE block.
  - Migrated relevant pointers from user-level memory (`~/.claude/projects/-Users-chrisnocera-Sites-adam-platform/memory/MEMORY.md`) into the canonical references section.
  - Updated user-level MEMORY.md "LOAD FIRST" block to point to v3.1 (was: `CLAUDE_CODE_DIRECTIVE_FULL_BUILD.md`) and to point to `docs/MEMORY.md` as the slice-level EVE log.
  - Executed competing-authority doc purge (Chris-authorized, all 4 categories): 8 tracked files `git rm`'d (staged for commit), 13 untracked top-level/docs files removed, `central_plan/` directory removed wholesale (was 0 tracked), `docs/handoff/` directory removed wholesale (5 untracked files including the methodology canon PDF — substance now encoded directly in v3.1).
  - Updated this MEMORY.md's "Theoretical / Operating References" section to remove the docs/handoff PDF pointer and reflect that the methodology substance is now in v3.1 directly.

- **V (Verified):**
  - Confirmed `docs/MEMORY.md` did not previously exist (no overwrite).
  - Confirmed S0 pre-flight (LUXY GraphQL key verification) is Chris-executed; will not begin S0 autonomously.
  - Confirmed last commit on `feature/hmt-dashboard` is `61644a9`; baseline test count per directive is 4380+.
  - Verified all 24 file removals + 2 directory removals landed (post-deletion existence-check loop produced zero "STILL EXISTS" lines).

- **E (Expected next session):**
  - Chris-executed S0 pre-flight (verify LUXY StackAdapt API key is GraphQL-not-REST with the LUXY account manager).
  - Once pre-flight lands, await Claude Proper's first slice prompt (S0).
  - First S0 action when prompted: GraphQL introspection ping at `adam/integrations/stackadapt/graphql_client.py`. Halt-and-surface on auth failure per directive §1.1; no auto-retry, no fallback to REST.

- **Open QUESTIONs:** none.

- **Hand-off pointer:** Branch `feature/hmt-dashboard` at `9936cf6`. Awaiting (a) Chris-executed S0 pre-flight, (b) Claude Proper's first S0 slice prompt. The cleanup commit `9936cf6` landed cleanly: 10 files changed (+1160/-4928); 8 tracked deletions + 2 doc additions (the v3.1 directive + this MEMORY.md). Remaining untracked filesystem deletions (15 top-level files, 2 docs files, central_plan/ directory, docs/handoff/ directory) were `rm`'d in the same operator pass — no commit needed for those. User-level memory (`~/.claude/projects/.../memory/`) updated: LOAD-FIRST block + reference_directive_full_build.md + reference_seven_component_methodology_handoff.md all re-anchored on v3.1.
