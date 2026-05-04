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
- Active slice: **S0 (BLOCKED on QUESTION 3 — schema mismatch with directive §1.2)**
- Last commit on branch: `9936cf6 chore(directive): v3.1 transition — add directive + MEMORY.md, remove superseded plan/directive docs`
- Test suite baseline: 4380+ passing (per directive Part 0; no code touched in this session)
- Open QUESTIONs: **3** (see `docs/S0_SCHEMA_MISMATCH_REPORT_2026_05_04.md`)
- Critical-path next slice: **S0** — §1.1 pre-flight introspection ping PASSED; §1.2 Q1 field `deliveryReportImpressionLevel` non-existent in live schema; awaiting Claude Proper directive amendment

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
