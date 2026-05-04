# CLAUDE_CODE_DIRECTIVE_INTEGRATED_V3_REWRITE.md

**Internal Designation:** v3.1 (operating as canonical v3 going forward)
**Supersedes:** `CLAUDE_CODE_DIRECTIVE_FULL_BUILD_VERSION2.md` (v3, original)
**Formally Retires:** v2 (clinical-trial directive, superseded by v3)
**Effective Date:** 2026-05-04
**Author of Record:** Chris Nocera, CTO, INFORMATIV Group
**Execution Surface:** Claude Code (Cursor IDE) on `feature/hmt-dashboard` branch and successors
**Compute:** Mac Studio 96-core (local v3 Phase 1) + Fly.io / Upstash Redis (pilot infra)
**Pilot of Record:** LUXY Ride, $30K/week through StackAdapt, friendly-CMO mandate
**Baseline Test Suite:** 4380+ tests passing on `feature/hmt-dashboard` HEAD; zero regressions tolerated
**Branch Discipline:** All Phase A wrap-out commits (Slices 1–35+) are immutable; never amend, never rebase

---

## PART 0 — DIRECTIVE PREAMBLE

### 0.1 Scope and Supersession

This document is the canonical operational directive for the ADAM/INFORMATIV AI build agent for the next 12–16 weeks of execution. It supersedes v3 (`CLAUDE_CODE_DIRECTIVE_FULL_BUILD_VERSION2.md`) in its entirety. The eight discipline-anchored work-streams (1.A particle-physics blind analysis with Gross-Vitells LEE; 1.B Free-Wilson SAR; 1.C MRA / GENIE3 / dynGENIE3 / CMap mediator inference; 1.D H∞ robust control wrapping Kelly bid sizing; 1.E funnel-MPC receding-horizon scheduler with prescribed-performance bounds; 1.F PK/PD frequency model with Hill / Mager-Jusko / Dayneka-Garg-Jusko; 1.G Daw two-system arbitration; 1.H persistent homology of trajectory space) and the Phase 2 governance bundle (independent DMC; blinded analysis; CONSORT-AI / SPIRIT-AI reporting; pharmacovigilance with PRR + ROR + IC + EBGM with DuMouchel MGPS shrinkage + tree-based scan statistics; basket-trial cross-tenant information-borrowing) are preserved in mandate but re-decomposed in this rewrite to expose substrate dependencies that were not visible when v3 was originally drafted.

Slice commits and inline documentation continue to use **`v3-`** nomenclature for traceability. The "v3.1" designation is a header-only artifact for distinguishing this rewrite from the document it replaces; it is **not** a separate version stream.

### 0.2 The Two Prior Research Outputs Are Inputs, Not Subjects of Re-Litigation

Two prior research outputs flow into this directive as accepted architecture:

1. **Constrained mindset map / per-brand standardized onboarding / mimicry-vs-solve copy strategy / DSP-signal-to-cell classifier / methodological validation.**
2. **StackAdapt API exploitation / permanent data-capture-and-learning pipeline / cell-classified retargeting / latency budget integration.**

Their conclusions are settled. This directive's job is to translate them into Claude Code slice-level build sequencing. Do not re-derive. Do not propose alternatives. Do not surface their architectural decisions as audit findings.

### 0.3 Anti-Drift Discipline (Non-Negotiable)

**Status reporting.** When Claude Code reports the status of a slice, it reports one of exactly five states: `NOT_STARTED`, `IN_PROGRESS`, `BLOCKED`, `READY_FOR_REVIEW`, `CLOSED`. Each state report must include: (a) the slice ID; (b) the commit SHA, if any; (c) the test-suite delta (tests added, tests removed, tests passing, tests failing); (d) the next concrete action with the named file or function; (e) any open questions, expressed as numbered items with the explicit phrase "QUESTION:".

**Surfacing uncertainty.** When Claude Code is uncertain about an architectural choice, an interface boundary, or a test-design question, it does not guess. It writes a numbered "QUESTION:" block at the top of the next status report and stops at the next clean commit boundary. Chris pastes the questions to Claude Proper for resolution.

**Never guess at architecture.** If a slice prompt is ambiguous, Claude Code asks. The prompt-loop overhead is cheap; rebuilding a slice on a wrong premise is expensive. The asymmetry favors asking.

**Persistent context.** Claude Code maintains a single file at `docs/MEMORY.md` (see Appendix E). Every session begins with reading `MEMORY.md`. Every session ends with appending a dated entry: slices touched, commits landed, open questions raised, hand-off pointer to the next session. The EVE handoff pattern (Appendix E) is mandatory at the end of every working session.

**Commit discipline (one slice = one commit).**
- Conventional-commit format: `<type>(<scope>): <slice-id> <description>`. Example: `feat(retargeting): S8.4 wire pixel postback round-trip e2e`.
- Allowed types: `feat`, `fix`, `test`, `refactor`, `docs`, `chore`, `perf`, `build`. Never `wip`. Never multi-type.
- One slice ⇒ one commit. Never bundle two slices into one commit. If a slice grows past ~400 lines of net change, split it; do not pack.
- **Never amend committed slices.** If something is wrong, ship a follow-up slice with `fix(...): S<n>.f1 <correction>`.
- **Never rebase shipped work.** The branch history is an audit trail.
- Every commit body must include: slice ID, predecessor slice IDs that close as a result, test-suite delta line, and a one-line "Why this slice now" justification.

**Test discipline (non-negotiable).**
- Every slice must pass the full test suite before commit. Baseline is 4380+ tests passing on `feature/hmt-dashboard` HEAD.
- Every new piece of code ships with new tests. No exceptions for "trivial" changes — trivial changes are exactly where regressions hide.
- Failed tests block commit. There is no `--no-verify`. There is no "I'll fix it next slice." If a slice's work breaks a test that should still pass, the slice is not done.
- New test files live under `tests/<area>/<slice-id>_<descriptor>_test.py`. Parametrized regression tests over historical bugs (see Slice 61644a9 collision-check pattern, 42 unit tests including parametrized regression over 16 historical collisions) are the canonical pattern.

### 0.4 Claude Proper vs Claude Code — Working Pattern

This directive enforces a strict separation of roles:

- **Claude Proper (claude.ai)** is Chris's architectural interlocutor. Chris discusses architecture, methodology, sequencing, and decision points with Claude Proper. Claude Proper writes prompts that Claude Code executes. Claude Proper **never modifies code directly**, only writes prompts.
- **Claude Code (Cursor IDE)** is the execution surface. Claude Code reads prompts from Claude Proper, executes them, runs tests, commits, and reports status as artifacts (status report, test output, diff summary, commit SHA list) that Chris pastes back to Claude Proper for evaluation. Claude Code **never makes architectural decisions**, only executes.

Both Claudes must respect this pattern.

When Claude Code encounters a decision that would require architectural judgment beyond the scope of the prompt — which interface to expose, which protocol seam to plug into, whether to extend an existing class versus adding a new one, whether a fixture rotation strategy belongs in this slice or the next — it stops, raises a `QUESTION:`, and waits. It does not invent.

When Claude Proper is asked by Chris to write a prompt for Claude Code, it writes a prompt that is concrete, scoped to a single slice (or a tightly bounded micro-sequence within a slice), names the files to touch, names the tests to add, names the commit message, and names the success criterion. It does not write prompts that say "decide the best approach."

### 0.5 Acknowledged Technical Debt (Do Not Surface as Findings)

The following are known and intentionally deferred. Claude Code does **not** surface these as audit findings later, does not append them to drift logs, does not propose impromptu remediation slices for them. They are tracked in this directive and will be re-opened on schedule.

1. **Spec-only `MicroStateDetector` at bid time.** Replaced architecturally by page-priming-signature lookup (Substrate work-stream **S3**). Live user-state detection is explicitly deferred to v3 Phase 1 sub-work-stream **2.E.S1** (post-impression telemetry from Enhancement #08 Signal Aggregation).
2. **Enhancements #10, #02, #07, page-priming at 5–25% shipped.** State × Trait audit findings. Their completion is the explicit subject of Substrate work-streams S3 (page-priming), S6/S7 (cell classifier consuming State × Trait features), and S8 (retargeting v0 consuming journey-state machine).
3. **Enhancement #09 100ms p99 five-tier fallback.** Existing budget. The cell-classifier + journey-state lookup + retargeting orchestrator + bilateral mechanism deployment lookup + timing-recommendation function compose **inside** this envelope; tier-by-tier latency allocation is fixed in the operational architecture document and must not be re-litigated mid-build.
4. **Synthetic-URL labeling exercise.** 4-rater worksheet on hold pending Slice 0 (real-URL extraction). The 80 synthetic candidates from `round_3_diversification_candidates.jsonl` are **not** to be relabeled or repaired; that file is being replaced wholesale.
5. **Inbound-only StackAdapt data architecture.** No outbound webhooks. URL-macro correlation pattern (`sapid={SA_POSTBACK_ID}`) is the click-attribution mechanism. Do not propose webhook-based alternatives.
6. **Claude API in offline pipeline only.** Never in real-time inference path. Every architectural proposal that places an LLM call in a bid-time path is an audit finding *against itself* and must be rejected at prompt-write time.
7. **Bilateral architecture per-archetype sequential mechanism deployment as documentation.** Encoded today in `INFORMATIV — Bilateral Psycholinguistic Advertising Intelligence System.md` as documentation, not as queryable data. Slice S2/S8 extracts these into queryable structures (one-time data-extraction effort, scoped in S8.2).
8. **Cross-tenant prior infrastructure has no second tenant yet.** Stand up against synthetic second-tenant in S9; live cross-tenant gates wait until Gate G8.

---

## PART 1 — SLICE 0: STACKADAPT HISTORICAL URL EXTRACTION (DAYS, IMMEDIATE)

### 1.0 Purpose and Framing

Slice 0 is a **one-shot extraction script** Chris will run to fix the synthetic-URL problem and unblock the 4-rater labeling exercise. It is **not** the substrate ingestion pipeline (that is S4). It is a fast, narrow tool whose only job is to produce a JSONL file of real served URLs from LUXY's StackAdapt history that the 4-rater worksheet can consume.

**Effort estimate:** 8–16 hours of Claude Code work, plus Chris's time to validate the auth handshake and skim the output for face-validity before sending to raters. Calendar: 1–3 days end-to-end.

**Why this is the very first slice:** the held-out gate (criterion ii) is reopened pending real-URL labels; without real URLs the classifier retrain is gated; without classifier retrain the substrate-blocking v3 Phase 1 sub-work-streams are gated. Slice 0 unwedges the entire critical path.

### 1.1 Authentication Setup Verification

**Pre-flight check (Chris executes; Claude Code surfaces if it fails):**

The StackAdapt GraphQL API requires a **GraphQL-specific API key**, distinct from the legacy REST key, per StackAdapt's GraphQL migration (rolled out by partners including Supermetrics on 2025-05-13; Funnel.io migration FAQ confirms REST sunsetting by end of 2025; AgencyAnalytics integration requires explicit "GraphQL Key" selection). Chris must verify with the LUXY StackAdapt account manager that the key in the LUXY environment is a GraphQL key, not a REST key.

Claude Code's first action in Slice 0 is to run a no-op introspection query against the GraphQL endpoint:

```graphql
query IntrospectionPing { __schema { queryType { name } } }
```

If this returns a 401, 403, or "old REST API key not supported" envelope, Claude Code halts immediately and surfaces:

> **AUTH FAILURE — ACTION REQUIRED.** The configured StackAdapt API key did not authenticate against the GraphQL endpoint. Per StackAdapt's GraphQL migration, REST keys are not interoperable with GraphQL endpoints. Please verify with the LUXY StackAdapt account manager that the issued key is a GraphQL/GQL key. Slice 0 is blocked pending resolution.

No retry loop, no automatic key rotation, no fallback to REST. Halt and surface.

### 1.2 The Q1 DeliveryReportImpressionLevel Query

Slice 0 uses one query, parameterized. Place this template in `adam/integrations/stackadapt/queries/q1_delivery_report.graphql`:

```graphql
query Q1_DeliveryReportImpressionLevel(
  $advertiserIds: [ID!]!
  $dateFrom: Date!
  $dateTo: Date!
  $cursor: String
  $pageSize: Int = 500
) {
  deliveryReportImpressionLevel(
    advertiserIds: $advertiserIds
    dateFrom: $dateFrom
    dateTo: $dateTo
    breakdowns: [DAY, CREATIVE_ID, CAMPAIGN_ID, DEVICE_TYPE, GEO, DOMAIN, IAB_CATEGORY, CONTENT_LANGUAGE]
    after: $cursor
    first: $pageSize
  ) {
    pageInfo { hasNextPage endCursor }
    asyncStatus { __typename ... on Outcome { jobId } ... on Progress { jobId etaSeconds } }
    edges {
      node {
        day
        creativeId
        campaignId
        deviceType
        geoKey
        domain
        url
        iabCategory
        contentLanguage
        impressions
        clicks
        conversions
        spend
      }
    }
  }
}
```

**Notes for Claude Code:**
- Field names follow StackAdapt's GraphQL schema. If field names differ at the live endpoint (StackAdapt has been adding fields under the new GraphQL surface — Supermetrics' integration release notes call out new metric sections including publisher, demographic, video-completion, audience, and conversion path that were previously unavailable under REST), Claude Code does an introspection-first walk to confirm field availability before issuing the query, and surfaces any field rename as a `QUESTION:` block.
- `breakdowns` enum values are the canonical names; if the schema uses different enum casing, surface and resolve.
- `pageSize` is bounded by the per-page record cap (~100–1000). Default to 500. If a page returns 0 nodes with `hasNextPage = true`, treat as transient and retry per §1.3.

### 1.3 Pagination, Backoff, and the UNION Outcome|Progress Async Pattern

**Cursor-based pagination loop with checkpointing.**

```
state = load_checkpoint("artifacts/luxy_historical/_checkpoint.json")
cursor = state.cursor or null
fetched = state.fetched or []
loop:
    response = await execute(Q1, advertiserIds, dateFrom, dateTo, cursor, 500)
    if response.asyncStatus is Progress:
        await poll_until_outcome(jobId, max_wait=30min, base_interval=5s, max_interval=15s)
    extend fetched with response.edges
    save_checkpoint(cursor=response.pageInfo.endCursor, fetched=fetched)
    if not response.pageInfo.hasNextPage: break
    cursor = response.pageInfo.endCursor
```

**Rate-limit handling (exponential backoff with jitter on HTTP 429 or rate-limit envelopes):**
- Base delay: 500ms.
- Max delay: 60s.
- Max attempts per page: 7.
- Jitter: full jitter (Marc Brooker / AWS pattern) — `delay = random(0, min(max, base * 2^attempt))`.
- After 7 failures on the same cursor, save checkpoint and exit with status `RATE_LIMIT_EXHAUSTED`.

**UNION Outcome|Progress async pattern.** When the response's `asyncStatus` discriminant is `Progress`, poll the `jobId` at intervals starting at 5s, capped at 15s, with bounded total wait of 30 minutes per page. If 30 minutes elapses without `Outcome`, save checkpoint and exit with status `ASYNC_TIMEOUT_EXIT`. Do not block the script forever.

**Reuse, do not recreate.** `adam/integrations/stackadapt/graphql_client.py` and `adam/integrations/stackadapt/adapter.py` already exist. Slice 0 wires through these modules. If the existing client lacks cursor pagination or async polling helpers, add them as small additions to the client (still within Slice 0; they are reused by S4) — do not write a parallel client.

### 1.4 Output Format

**Path:** `artifacts/luxy_historical/luxy_served_urls_<YYYY-MM-DD>.jsonl`

**One JSONL row per (creative_id, campaign_id, day, device_type, geo_key, domain) tuple, with fields:**

```json
{
  "day": "2025-11-12",
  "creative_id": "cr_8847221",
  "campaign_id": "cmp_338112",
  "device_type": "DESKTOP",
  "geo_key": "US-NY-NewYork",
  "domain": "thehustle.co",
  "url": "https://thehustle.co/business/founders-guide-q4",
  "iab_category": "IAB3-3",
  "content_language": "en",
  "impressions": 412,
  "clicks": 7,
  "conversions": 0,
  "spend_usd": 4.87
}
```

**Derived URL set.** After the per-row JSONL lands, Claude Code emits a second artifact at `artifacts/luxy_historical/luxy_served_urls_<YYYY-MM-DD>.unique_urls.jsonl` containing the deduplicated URL list with HTTP-HEAD validation:

```json
{
  "url": "https://thehustle.co/business/founders-guide-q4",
  "domain": "thehustle.co",
  "head_status": 200,
  "served_impression_total": 1284,
  "served_domain_count": 1,
  "iab_categories": ["IAB3-3"],
  "validated_live": true
}
```

HTTP HEAD with 5-second timeout, single attempt; non-200 responses (including timeouts, DNS failures, 404, 410, 451, redirect chains > 3 hops) flag `validated_live = false`. Do not crawl content — HEAD only. Do not follow redirects more than 3 hops. Do not authenticate.

### 1.5 Validation Step

Slice 0 emits a third artifact at `artifacts/luxy_historical/luxy_served_urls_<YYYY-MM-DD>.summary.md` with:

- Total domains served (count of unique `domain`).
- Total URLs in the dedup set; total `validated_live = true`; total `validated_live = false`.
- Distribution of impressions per domain; flag any domain with **< 10 served impressions** as `low-confidence inventory`.
- IAB category histogram.
- Content language histogram.
- Device-type histogram.
- Per-archetype URL bucket: a coarse pass mapping URLs into the five LUXY archetype-target-mix buckets (Status Seeker, Careful Truster, Easy Decider, Skeptical Analyst, Disillusioned) using the existing ContentProfiler offline output if available, or domain-level priors otherwise. This is **not** classifier output; it is a face-validity check before the 4-rater worksheet is generated.

### 1.6 Failure-Mode Handling (Explicit)

| Failure | Response |
|---|---|
| Auth error on introspection ping | Halt; surface `AUTH FAILURE — ACTION REQUIRED` as in §1.1. |
| 429 rate limit, < 7 attempts | Exponential backoff with full jitter; retry. |
| 429 rate limit, ≥ 7 attempts | Save checkpoint; exit with `RATE_LIMIT_EXHAUSTED`; surface to Chris. |
| `Progress` async never resolves within 30 min | Save checkpoint with last `jobId`; exit with `ASYNC_TIMEOUT_EXIT`; surface to Chris. |
| Cursor returns `null` or invalid | Save state; exit with `CURSOR_INVALID`; surface to Chris with the offending cursor value. |
| Schema field not found on introspection | Halt; surface as `QUESTION:` block listing missing fields and proposed fallback breakdowns. Do not silently drop. |
| HTTP HEAD validation fails for > 30% of URLs | Continue but flag in summary; do not halt — staleness is expected on a 365-day window. |
| Less than 200 unique validated live URLs after pull | Continue, but write `INSUFFICIENT_INVENTORY` flag in summary; surface to Chris, who may extend the date window or relax filters before re-running. |

### 1.7 Success Criterion

Slice 0 closes when all three are true:

1. `artifacts/luxy_historical/luxy_served_urls_<YYYY-MM-DD>.unique_urls.jsonl` exists with **≥ 200 unique validated-live URLs** spanning **≥ 30 unique domains**, with class diversity (≥ 3 of the 5 LUXY archetype-target-mix buckets represented in the coarse face-validity pass).
2. The summary `.md` artifact exists and reports no `INSUFFICIENT_INVENTORY` flag.
3. Slice 0 commit lands as `feat(stackadapt): S0 historical URL extraction one-shot` with the three artifacts committed under `artifacts/luxy_historical/` and the queue-marker file `artifacts/luxy_historical/READY_FOR_RATER_WORKSHEET.flag` written.

### 1.8 Integration With 4-Rater Labeling Reset

The Slice 0 output **replaces** `round_3_diversification_candidates.jsonl` as the source of truth for the 4-rater worksheet. Claude Proper consumes the `unique_urls.jsonl` artifact and regenerates the worksheet (this is a Claude Proper task, not Claude Code). Slice 0 is closed when the queue marker is written; the worksheet regeneration is the first action in **Substrate work-stream S1**.

---

## PART 2 — DEPENDENCY GRAPH AND WORK-STREAM RE-DECOMPOSITION

The original v3 eight-work-stream taxonomy is preserved in mandate. This part re-decomposes those mandates plus the substrate work-streams into ~14 named units, each tagged for substrate-blocking status, predecessors, successors, slice-count estimate, and critical-path designation.

**Legend:**
- `SB` = Substrate-Blocking (cannot start until named substrate work closes).
- `SI` = Substrate-Independent (can ship in parallel with substrate work).
- `CP` = Critical-Path.
- `NCP` = Non-Critical-Path (concurrency available).

### 2.1 Substrate Work-Streams

| ID | Name | Type | Predecessors | Successors | Slice Est. | CP/NCP |
|---|---|---|---|---|---|---|
| **S0** | StackAdapt Historical URL Extraction (one-shot) | SI | — | S1 | 1 | CP |
| **S1** | Real URL Validation + 4-Rater Labeling Pipeline Reset | SI | S0 | S6, S7 | 4 | CP |
| **S2** | Retargeting Substrate Audit | SI | — | S8 | 2 | CP |
| **S3** | Page-Priming-Signature Substrate | SI | — | S6, S7 | 6 | NCP (parallel with S1) |
| **S4** | StackAdapt Historical Pull Permanent Pipeline | SI | (S0 unblocks; S0 is independent) | S5, S6, S7, 1.D.SB | 8 | CP |
| **S5** | Permanent Data-Capture-and-Learning Pipeline Wiring | SI | S4 | S9, S10, 1.C.SB, 1.H.SB | 6 | CP |
| **S6** | Cell Classifier v0 (Rule-Based) | SB on S1 | S1, S3, S4 | S8, 1.B.SB, 1.E.SB, 1.G.SB | 5 | CP |
| **S7** | Cell Classifier v1 (Calibrated Probabilistic) | SB on S6 | S6, S5 | S9, S10, 1.B.SB, 1.G.SB | 5 | NCP (parallel with S8) |
| **S8** | Retargeting v0 (Pre-Pilot Ship) | SB on S2, S6 | S2, S6 | LUXY Ad-Serve, S9, 1.C.SB | 7 | CP |
| **S9** | Retargeting v1 (Pilot Weeks 1–8) | SB on S8 | S8, S7, S5 | S10, 1.F.SB | 8 | CP |
| **S10** | Retargeting v2 (Asymptote) | SB on S9 | S9 | v3 Phase 2 Ramp | 10 | NCP |

### 2.2 v3 Phase 1 Discipline-Anchored Sub-Work-Streams

| ID | Original v3 WS | Type | Predecessors | Slice Est. | CP/NCP |
|---|---|---|---|---|---|
| **1.A.SI.1** | Particle-physics blind analysis box construction | SI | — | 4 | NCP |
| **1.A.SI.2** | Gross-Vitells LEE trial-factor implementation | SI | 1.A.SI.1 | 3 | NCP |
| **1.A.SB.1** | Blind analysis applied to live signal claims | SB | S5, 1.A.SI.2 | 3 | NCP |
| **1.B.SI.1** | Free-Wilson decomposition + conformal prediction bands (offline) | SI | — | 5 | NCP |
| **1.B.SB.1** | Cell-tagged creative variants ingest | SB | S6, 1.B.SI.1 | 3 | NCP |
| **1.C.SI.1** | MRA / GENIE3 / dynGENIE3 / CMap mediator inference (offline) | SI | — | 6 | NCP |
| **1.C.SB.1** | Decision-time mediator-conditioned bid | SB | S8, 1.C.SI.1 | 4 | NCP |
| **1.D.SI.1** | H∞ robust-control derivation (offline) | SI | — | 5 | NCP |
| **1.D.SB.1** | Kelly-fraction calibration with cell-level priors | SB | S4, 1.D.SI.1 | 4 | NCP |
| **1.E.SI.1** | Funnel-MPC formulation + receding-horizon solver | SI | — | 5 | NCP |
| **1.E.SB.1** | Prescribed-performance bound calibration | SB | S6, 1.E.SI.1 | 3 | NCP |
| **1.F.SI.1** | Hill / Mager-Jusko / Dayneka-Garg-Jusko model implementations | SI | — | 5 | NCP |
| **1.F.SB.1** | Per-user PK/PD calibration (per-user AR(1) coupling) | SB | S9, 1.F.SI.1 | 4 | NCP |
| **1.G.SI.1** | Daw two-system arbitration model | SI | — | 4 | NCP |
| **1.G.SB.1** | Processing-mode signal integration (cell + journey-state) | SB | S6, S7, 1.G.SI.1 | 3 | NCP |
| **1.H.SI.1** | Persistent-homology offline pipeline | SI | — | 5 | NCP |
| **1.H.SB.1** | Trajectory-pattern detection on live event log | SB | S5, 1.H.SI.1 | 4 | NCP |
| **2.E.S1** | Live user-state detection from post-impression telemetry (Enhancement #08) | SB | S5 | 6 | NCP (v3 Phase 1 late) |

### 2.3 Phase 2 Governance Pre-Work

| ID | Name | Type | Predecessors | Slice Est. |
|---|---|---|---|---|
| **G.1** | DMC Charter draft (5 pp) | SI | — | 1 |
| **G.2** | OSF Pre-Registration | SI | S2 audit findings | 1 |
| **G.3** | Pharmacovigilance Dashboard Schema | SI | — | 2 |
| **G.4** | CONSORT-AI / SPIRIT-AI Reporting Template | SI | — | 1 |

### 2.4 Critical-Path Visualization

```
S0 ──▶ S1 ──┬──▶ S6 ──▶ S7 ─┐
            │                ├──▶ S9 ──▶ S10 ──▶ Phase-2 Ramp
S2 ────────┼──▶ S8 ──┬──────┘
            │         │
S3 ────────┘         │
                     ▼
              LUXY Ad-Serve (Gate G3)
S4 ──▶ S5 ──────────────────▶ (feeds S9, S10, and all v3 Phase 1 SB sub-work-streams)
```

The genuine concurrency surface: **S0/S1/S2/S3/S4 all run in parallel from day one.** S0 is critical-path-fastest. S2 (audit) is critical-path-fastest after S0 because it gates S8. S3 and S4 do not gate retargeting v0; they gate cell classifier and downstream learning. v3 Phase 1 SI sub-work-streams (1.A.SI through 1.H.SI) all run in parallel with substrate work — they are precisely the work to fill compute when substrate is in flight.

### 2.5 Concurrency Strategy

- **Days 1–3:** Slice 0; Slice S2.1 (audit prompt drafted); Slice S3.1 (PagePrimingSignature data class scaffolded); Slice S4.1 (ingestion package skeleton); Slice G.1 (DMC charter draft started).
- **Days 4–14:** Slice 0 closes → S1 begins; S2 closes → S8 begins build; S3, S4 progress; v3 Phase 1 SI sub-work-streams begin in parallel (compute-fill on Mac Studio).
- **Weeks 3–6:** S6 closes → S8 wires cell classifier; S4 backfill running; S5 wiring begins.
- **Weeks 6–8:** S8 ships → Gate G3 → LUXY ad-serving begins; S9 build begins concurrently with pilot week 1 data accumulation.
- **Weeks 8–16:** S9 ships at week 8; S10 + v3 Phase 1 SB sub-work-streams proceed in parallel with pilot serve.

---

## PART 3 — SUBSTRATE WORK-STREAMS

### S0 — StackAdapt Historical URL Extraction
Detailed in Part 1.

### S1 — Real URL Validation and 4-Rater Labeling Pipeline Reset

**Mandate:** Close hard-stop criterion (ii) — the 5-class posture classifier macro-AUC ≥ 0.50 AND top-1 ≥ 0.40 against the genuinely-held-out fixture — by replacing the synthetic-URL training corpus with real URLs, generating the 4-rater labeling worksheet, distributing to raters, consolidating, retraining, and running the held-out evaluator.

**Honest framing.** Calendar time ≈ 2–3 weeks dominated by rater-labeling latency, **not** by code. The code work is on the order of 2–4 days. Do not optimize the code path past where it is gated by humans.

**Slice decomposition:**

- **S1.1 — Worksheet regeneration (Claude Proper task; Claude Code ingest).** Claude Proper consumes `artifacts/luxy_historical/luxy_served_urls_<date>.unique_urls.jsonl` and regenerates the rater worksheet at `artifacts/labeling/round_4_real_urls_<date>.xlsx`. Claude Code's slice is to wire the JSONL → worksheet generator at `tools/labeling/generate_rater_worksheet.py`, run it, commit the worksheet. *Effort: 4h. Closes when worksheet exists and a smoke-test fixture rater labels 5 rows successfully.*

- **S1.2 — Rater distribution and consolidation pipeline.** Slice ships `tools/labeling/consolidate_rater_responses.py` that ingests four returned worksheets, computes Krippendorff's α per dimension, surfaces inter-rater disagreement above a threshold (0.667 by default — the standard "tentative-conclusion" floor in content-analysis literature), and emits a consolidated label set at `artifacts/labeling/round_4_consolidated_<date>.jsonl`. *Effort: 1d. Closes when synthetic 4-rater fixture is consolidated correctly with the test-suite α regression check.*

- **S1.3 — Retraining wired to consolidated labels.** Slice retrains the 5-class posture classifier head against `round_4_consolidated_<date>.jsonl`, with **domain-isolated** held-out fixture (per the permanent-isolation rule landed in commit 4b94591). The held-out fixture rotation must respect the rule: no domain in the held-out set may appear in train. *Effort: 1d. Closes when training run completes with a saved checkpoint at `artifacts/checkpoints/posture_classifier_round4_<date>.pt`.*

- **S1.4 — Held-out gate evaluation.** Run the held-out evaluator against the round-4 checkpoint; emit `artifacts/evaluation/posture_round4_<date>.json` with macro-AUC, top-1, per-class AUC, confusion matrix. **Gate G1 closes if and only if macro-AUC ≥ 0.50 AND top-1 ≥ 0.40 against the genuinely-held-out fixture.** If the gate does not close, surface as `BLOCKED` and stop; do not retrain on the held-out data, do not loosen the gate, do not propose an alternative classifier head without explicit Claude Proper instruction. *Effort: 4h plus rater latency.*

**Success criterion (work-stream-level):** Gate G1 closed; `artifacts/evaluation/posture_round4_<date>.json` records pass; tests in `tests/posture/round4_gate_test.py` parametrize over the gate threshold and hard-fail if regenerated checkpoints fall below.

### S2 — Retargeting Substrate Audit

**Mandate:** Audit the five surfaces involved in retargeting before any v0 build. The audit is a **read-only inspection**; no code is written outside the audit document.

**The five-surface audit (single Claude Code prompt):**

1. **Journey-state machine (Enhancement #10).** What is shipped? What states exist? What transitions? Where does it live in the repo? Is it queryable by user_id and timestamp, or only by event hook?
2. **`SequenceStep` models (Enhancement #28).** What's the data model? Is it a persistence-backed table, an in-memory class, or spec-only? What relationships connect it to Creative, Campaign, BilateralEdge?
3. **Bilateral-system per-archetype mechanism deployment.** Encoded as documentation in `INFORMATIV — Bilateral Psycholinguistic Advertising Intelligence System.md`, or as queryable structures? If documentation only, file paths and data extraction effort estimate.
4. **Pixel-tracking integration.** What's wired in `pixel_client.py`? URL-macro `sapid={SA_POSTBACK_ID}` correlation pattern — is the inbound postback handler stood up? What's the persistence path?
5. **Decision-time cascade.** Reading from Slice 24 wrap-out, what's the actual decision-time path through `BidComposer` → `CarryoverCorrectionStrategy` → `WashoutModel`? Where would a `RetargetingOrchestrator` plug in?

**Deliverable:** `docs/RETARGETING_AUDIT_2026_05_<DD>.md`, formatted with one section per surface, each section containing: shipped status (% complete), file paths, key types/classes, gaps, recommended Slice S8 plug-in points.

**Slices:**
- **S2.1 — Audit prompt run (Claude Code reads and reports).** *Effort: 1d. Closes when audit doc lands.*
- **S2.2 — Audit findings → S8 slice plan refinement (Claude Proper task; Claude Code stub).** *Effort: 0.5d.*

**Success criterion:** `docs/RETARGETING_AUDIT_2026_05_<DD>.md` exists, signed off by Chris, and the S8 slice list is updated with concrete predecessor closures.

### S3 — Page-Priming-Signature Substrate

**Mandate:** The **architectural reframe** established in conversation: page-priming-signature lookup at bid time replaces the spec-only `MicroStateDetector` at bid time. This is the substrate that lets the cell classifier consume context-of-impression signals without putting any user-state-detection logic in the bid path. Live user-state detection at bid time is **explicitly deferred** to **2.E.S1** (post-impression telemetry from Enhancement #08 Signal Aggregation), and that deferral is non-negotiable here.

**Slice decomposition:**

- **S3.1 — `PagePrimingSignature` data class.** Define at `adam/priming/signature.py`:
  ```python
  @dataclass(frozen=True)
  class PagePrimingSignature:
      url_hash: str
      valence: float                       # [-1, 1]
      arousal: float                       # [0, 1]
      regulatory_focus_priming: Literal["promotion", "prevention", "neutral"]
      cognitive_load_estimate: float       # [0, 1]
      activated_frames: tuple[str, ...]    # canonical frame IDs
      confidence_per_dimension: dict[str, float]
      computed_at: datetime
      signature_version: str
  ```
  Plus serialization to/from Feature Store row format. *Effort: 0.5d. Closes when type, serialization, and round-trip tests pass.*

- **S3.2 — Offline page analysis pipeline.** Wire the existing `ContentProfiler` (8 NDF dimensions + mechanisms + emotions + segments) to emit `PagePrimingSignature` records. Pipeline runs offline in batch over the URL set produced by S0 (and ongoing by S4). Output to Feature Store via Enhancement #30 row-write API. *Effort: 2d. Closes when 200+ URLs from S0 have signatures persisted.*

- **S3.3 — Feature Store integration for sub-5ms bid-time lookup.** Use the L1 in-process LRU + L2 Redis Cluster + L3 Memcached cascade (Enhancement #31). Lookup key is `url_hash`; cold-miss fallback path emits a synthetic neutral signature with `confidence_per_dimension` floored at 0 across all dimensions, so the cascade never blocks. *Effort: 1d. Closes when p99 lookup latency on a 10k-URL synthetic load is < 5ms with realistic L1 hit rates.*

- **S3.4 — Cascade integration: cell classifier consumes page-priming alongside posture.** The cell classifier's input vector grows by the page-priming feature block. Posture and page-priming are separate inputs; do not fuse them prematurely. *Effort: 1d.*

- **S3.5 — Held-out evaluation parallel to posture classifier.** Domain-isolated held-out fixture for page-priming. Reuse the round-4 domain-isolation rule. *Effort: 0.5d.*

- **S3.6 — Explicit deferral marker.** Add `docs/DEFERRED/2.E.S1_LIVE_USER_STATE.md` documenting that live user-state detection is **2.E.S1**, **not** S3, and listing the post-impression-telemetry inputs (Enhancement #08 Signal Aggregation outputs) it will consume. *Effort: 1h.*

**Success criterion:** Cell classifier accepts page-priming features; cold-miss fallback validated; held-out fixture passes; deferral marker committed.

### S4 — StackAdapt Historical Pull Permanent Pipeline

**Mandate:** The **permanent ingestion pipeline** as distinct from S0's one-shot script. Builds the substrate that S5, S6, S7, S9, S10, and 1.D.SB.1 consume.

**Slice decomposition:**

- **S4.1 — Ingestion package skeleton.** Create `adam/ingestion/stackadapt/` containing:
  - `historical_puller.py` — full backfill driver (12-month default).
  - `incremental_puller.py` — daily incremental driver.
  - `pixel_correlator.py` — `sapid={SA_POSTBACK_ID}` URL-macro click-attribution joiner.
  - `rate_limited_session.py` — `RateLimitedGraphQLSession` with token-bucket pacing, exponential backoff, async-Outcome polling (lifted from S0 helpers).
  *Effort: 1d. Closes when package imports clean and skeleton tests pass.*

- **S4.2 — Iceberg/Parquet persistence layer.** Land raw records to Apache Iceberg (Parquet under the hood) for time-travel queries; partition by `(day, advertiser_id)`. Schema registry under `adam/ingestion/stackadapt/schemas/`. *Effort: 1.5d.*

- **S4.3 — Neo4j trajectory writes.** Wire trajectory edges into the existing graph schema (ProductDescription nodes, ad-side annotations, conversion edges, BayesianPrior nodes already exist). Each impression-conversion sequence becomes a path in the graph. *Effort: 1.5d.*

- **S4.4 — Postgres rollup.** Daily/weekly/monthly rollups for the analytic surface. *Effort: 1d.*

- **S4.5 — Stage C event emission to materialized event log.** Every persisted impression and pixel postback emits a typed event onto a Kafka topic (`adam.ingestion.stage_c`). This is the firehose S5 consumes. *Effort: 1d.*

- **S4.6 — IPSW-aware sampling job.** Stratified random sampling over IAB × device × daypart for population-representative training data, plus conversion over-sampling at calibrated multiplier for class-balanced classifier training. The IPSW step (Imbens 1992 / Wooldridge 1999 — and per the survey-weighted regression literature, estimating the sampling scores yields more efficient IPW estimators than using known scores; we follow that result) is applied at every downstream causal-inference and effect-estimation step. Top-two Thompson sampling consumes IPSW-corrected posteriors, **not** raw enriched posteriors. *Effort: 1d.*

- **S4.7 — End-to-end ingestion test on synthetic StackAdapt response payloads.** Synthetic UNION Outcome|Progress payloads, synthetic 429 envelopes, synthetic empty-page edge cases. *Effort: 1d.*

- **S4.8 — Closure: full 12-month backfill on LUXY + daily incremental green for 7 consecutive days.** *Effort: dominated by API time, not code time.*

**Success criterion:** 12-month backfill committed to Iceberg; daily incremental green for 7 days; Stage C events flowing; IPSW sampler producing weighted training fixtures.

### S5 — Permanent Data-Capture-and-Learning Pipeline Wiring

**Mandate:** Wire four downstream consumers to the Stage C event firehose so that every impression and conversion contributes to learning at the correct cadence.

**Slice decomposition:**

- **S5.1 — Cognitive Learning Engine event consumer.** Reads Stage C events; updates per-archetype × per-cell per-mechanism posteriors via the Bayesian update API. *Effort: 1.5d.*

- **S5.2 — Gradient Bridge integration.** Stage C events feed batch gradient updates to any model that participates in the gradient bridge (currently posture classifier, page-priming model when fine-tuned, cell classifier v1). *Effort: 1d.*

- **S5.3 — Cross-Tenant Learner gate evaluation infrastructure.** The CrossTenantLearner gate is **stood up but not opened** — it consumes Stage C events from a single tenant, evaluates whether information-borrowing would meet the basket-trial cross-tenant criteria (per 2.E basket-trial mandate), and stages priors that *would* be borrowed if a second tenant existed. Synthetic second-tenant fixture in tests. *Effort: 1.5d.*

- **S5.4 — Per-user N-of-1 hierarchical Bayesian engine: `WithinSubjectTrial` event consumer.** Each user's 4–8 touch sequence, per the within-subject crossover protocol (Item K of accepted decisions), is itself an experimental design. The engine consumes Stage C touch events, fits a per-user posterior with hierarchical pooling toward the per-archetype × per-cell prior, and emits per-user trajectory state back into the Feature Store. *Effort: 1.5d.*

- **S5.5 — Nightly batch training job.** Cron-driven; retrains classifiers, refits Cognitive Learning Engine posteriors over the last 90 days, regenerates IPSW-corrected sampling weights, snapshots checkpoints. *Effort: 1d.*

- **S5.6 — ADWIN drift detection on per-cell outcome rates.** Bifet-Gavaldà ADWIN (Adaptive Windowing) on per-(cell, archetype) conversion-rate streams; drift triggers a structured alert + a nightly recalibration flag. *Effort: 1d.*

- **S5.7 — Synthetic-event injection tests.** Verify all four downstream consumers receive events at correct cadence; verify ADWIN triggers on injected drift; verify within-subject trial state mutates correctly under a known touch sequence. *Effort: 1d.*

**Success criterion:** All four consumers wired; nightly training green; ADWIN drift detector operational; synthetic-injection tests pass.

### S6 — Cell Classifier v0 (Rule-Based)

**Mandate:** Operational mindset cell taxonomy from the parallel research output operationalized as a deterministic rule-based classifier consuming StackAdapt bid-stream signals plus page-priming signature plus posture. **Posture-blocking:** does not start until Gate G1 closes (criterion ii against held-out gate).

**Slice decomposition:**

- **S6.1 — Cell taxonomy ingestion.** Translate the constrained mindset map's cell taxonomy from research output into a queryable schema at `adam/cells/taxonomy.py`. Each cell has: ID, name, parent archetype(s), defining feature predicates, expected base-rate priors. *Effort: 1d.*

- **S6.2 — Rule-based classifier from DSP-signal-to-cell mapping.** Decision-tree-style ruleset; deterministic; explicit per-cell preconditions; tie-breaking by cell-base-rate prior. *Effort: 1.5d.*

- **S6.3 — Held-out evaluation.** Held-out-by-domain for URL-template features; held-out-by-archetype for archetype-specific behavior. *Effort: 1d.*

- **S6.4 — Latency budget allocation.** Cell classifier v0 must close in **≤ 18ms p99** within Enhancement #09's 100ms p99 envelope (allocation: 5ms page-priming Feature Store lookup; 18ms cell classifier; 12ms journey-state lookup; 25ms retargeting orchestrator including bilateral mechanism deployment lookup; 10ms timing-recommendation; ≤ 30ms headroom for tier-1/tier-2 fallback). *Effort: 0.5d benchmark.*

- **S6.5 — Closure.** Held-out validation passing; latency budget met. *Effort: 0.5d sign-off.*

**Success criterion:** Held-out validation gates pass; p99 ≤ 18ms; v0 deployed behind feature flag.

### S7 — Cell Classifier v1 (Calibrated Probabilistic)

**Mandate:** Probabilistic upgrade from v0 with confidence calibration and per-user posterior accumulation. Consumed by S9 retargeting v1.

**Slice decomposition:**

- **S7.1 — Probabilistic classifier head.** Multinomial logistic with platt-scaled or isotonic calibration; calibration error reported per cell. *Effort: 2d.*

- **S7.2 — Per-user posterior accumulation via BONG online updates.** Bayesian Online Natural Gradient (BONG) per-user posterior over cell membership; updates on each impression. *Effort: 1.5d.*

- **S7.3 — IPSW corrections at every reported metric.** All cell-conditional conversion rates, lift estimates, and within-subject treatment-effect estimates are IPSW-corrected. *Effort: 1d.*

- **S7.4 — Calibration plots.** Reliability diagrams; expected-vs-observed cell-conditional conversion rates; held-out calibration error report. *Effort: 0.5d.*

**Success criterion:** Calibration error within target; per-user posterior accumulation tested under synthetic touch sequences; v1 deployed behind shadow-mode flag for A/B against v0.

### S8 — Retargeting v0 (Pre-Pilot Ship — MUST SHIP BEFORE LUXY AD-SERVING)

**Mandate:** Differentiated retargeting from day one. Naive frequency-cap is the explicit floor; v0 must demonstrably exceed it. The pilot value proposition rests on this.

**Slice decomposition:**

- **S8.1 — Decision-time composition: cell-classifier output + journey-state output → `CellStateContext`.** Composite type at `adam/retargeting/context.py`. *Effort: 1d.*

- **S8.2 — Bilateral-system per-archetype canonical sequences as queryable data.** One-time data extraction from `INFORMATIV — Bilateral Psycholinguistic Advertising Intelligence System.md` into `adam/bilateral/sequences.yaml` and a typed loader. The Careful Truster 4-touch sequence, the Status Seeker, the Easy Decider, the Skeptical Analyst, the Disillusioned per-archetype sequences each become a typed `MechanismDeploymentPlan`. *Effort: 1.5d. Closes when all five archetype plans round-trip through tests with sequence-order assertions.*

- **S8.3 — Deterministic next-touch selection.** Given `CellStateContext` and the canonical sequence, deterministically select the next touch. Fixed timing curves per archetype × journey-state from cohort priors. *Effort: 1d.*

- **S8.4 — Pixel postback wiring end-to-end.** URL-macro `sapid={SA_POSTBACK_ID}` correlation; inbound postback handler persists `PixelPostback` rows; correlator joins to last-served impression by `sapid`. *Effort: 1.5d.*

- **S8.5 — `TrajectoryEvent` logging.** Every served touch + every postback emits a `TrajectoryEvent` to the Stage C log. *Effort: 0.5d.*

- **S8.6 — Validation harness: fluid-retargeting touches vs naive same-creative baseline.** Offline harness against historical backfill simulating both arms. *Effort: 1d.*

- **S8.7 — Sandbox round-trip test + Slice 35 shadow-mode integration.** End-to-end test in StackAdapt sandbox confirms Pixel round-trip; Careful Truster sequence fires in correct order on test user; p99 decision-time latency within Enhancement #09 tier-2 budget; Slice 35 `StackAdapt shadow-mode bidder wire` records every decision as `ShadowBidRecord` + `DecisionTrace` dual-persistence. *Effort: 1.5d.*

**Success criterion (Gate G3):** All sandbox tests green; Pixel round-trip validated with real `sapid` macro; latency budget met; shadow-mode logging operational; ready for LUXY ad-serve start.

### S9 — Retargeting v1 (During Pilot Weeks 1–8)

**Mandate:** Per-user posterior; top-two Thompson sampling; ε-randomized first-touch; AR(1) per-user carryover; ADWIN drift; cross-tenant gate stood up against synthetic second-tenant.

**Slice decomposition:**

- **S9.1 — Per-user posterior via BONG (consumed from S7.2).** *Effort: 1d.*
- **S9.2 — Top-two Thompson sampling with β = 0.3.** Russo's top-two; β = 0.3 default per the parallel research output. Consumes IPSW-corrected posteriors per Item J. *Effort: 1d.*
- **S9.3 — ε-randomized first-touch (ε = 0.15).** First touch in any user trajectory is ε-randomized for propensity-score identification. *Effort: 0.5d.*
- **S9.4 — AR(1) carryover at per-user level via Slice 24 `CarryoverCorrectionStrategy` seam.** The default adapter from Slice 24 is replaced by `PerUserAR1Carryover`; registry-pattern swap, soft-fail back-compat preserved. *Effort: 1d.*
- **S9.5 — IPSW corrections wired through `BidComposer` protocol seam (Slice 24).** *Effort: 1d.*
- **S9.6 — ADWIN drift detection (consumed from S5.6).** *Effort: 0.5d.*
- **S9.7 — Cross-tenant gate stood up against synthetic second-tenant.** Synthetic second-tenant fixture; gate-evaluation runs nightly; gate remains closed (no actual borrow) but produces would-borrow priors for inspection. *Effort: 1.5d.*
- **S9.8 — Always-valid sequential test against v0 baseline.** Howard-Ramdas confidence sequences (time-uniform, nonparametric, nonasymptotic; *Annals of Statistics* 2021); Johari-Pekelis-Walsh always-valid mixture SPRT for continuous-monitoring safety; Waudby-Smith-Ramdas e-process supplementary checks. Lindon-Malek 2022 references included where their tightening applies. Calibration validation alongside. *Effort: 1.5d.*

**Success criterion:** v1 demonstrates lift over v0 on IPSW-corrected weighted-conversion-rate under always-valid sequential testing without premature termination.

### S10 — Retargeting v2 (Asymptote)

**Mandate:** Full bilateral per-archetype sequential mechanism deployment integrated; hierarchical-pooling parameter learning; trajectory-pattern priors fully populated; cross-tenant priors integrated when Gate G8 opens; auto-archetype-boundary-adjustment.

**Slice decomposition:**

- **S10.1 — Full bilateral mechanism deployment with mid-sequence branching.** *Effort: 2d.*
- **S10.2 — Hierarchical-pooling parameter learning across users within archetype.** *Effort: 2d.*
- **S10.3 — Trajectory-pattern priors fully populated from persistent-homology output (1.H.SB.1).** *Effort: 1.5d.*
- **S10.4 — Cross-tenant priors integrated (gate-conditional).** *Effort: 1.5d.*
- **S10.5 — Auto-archetype-boundary-adjustment.** Detect when a user's posterior cell membership crosses an archetype boundary; emit re-classification event. *Effort: 1.5d.*
- **S10.6 — IPSW-corrected weighted-conversion-rate lift validation over v1.** *Effort: 1d.*
- **S10.7 — Cross-tenant prior cold-start improvement validation (gate-conditional, Gate G8).** *Effort: 1.5d.*

**Success criterion:** Significant lift over v1 on IPSW-corrected weighted-conversion-rate; cross-tenant priors provide measurable cold-start improvement when Gate G8 opens.

---

## PART 4 — V3 PHASE 1 WORK-STREAMS RE-DECOMPOSED

For each original v3 Phase 1 work-stream, decomposition into substrate-independent (SI) and substrate-blocking (SB) sub-work-streams. SI sub-work-streams ship in parallel with substrate work and fill compute on the Mac Studio.

### 1.A — Particle-Physics Blind Analysis with Gross-Vitells LEE

**Mandate preserved:** Blind-analysis discipline (signal box defined before unblinding), with Gross-Vitells trial-factor correction for the look-elsewhere effect (Gross & Vitells 2010, *Eur. Phys. J. C* 70:525–530; trial factor estimated from Davies' result, asymptotically linear in fixed-mass significance). The application: when scanning over many candidate creative × cell × cohort × posture combinations for "interestingly large" lift, the LEE correction prevents the field from declaring spurious local excesses as platform-level discoveries.

- **1.A.SI.1 — Blind-analysis box construction.** Define analysis-box parameters before any data is unblinded. Pre-registered. Placeholder data generators for blinding. *Effort: 2d.*
- **1.A.SI.2 — Gross-Vitells LEE trial-factor implementation.** Closed-form implementation of the Gross-Vitells trial factor; Monte Carlo cross-check on synthetic Gaussian processes. Tests parametrized on known asymptotic linearity in significance. *Effort: 2d.*
- **1.A.SB.1 — Blind analysis applied to live signal claims.** Operates on Stage C event stream once it is producing pilot data. Substrate-blocked on S5. *Slice decomposition deferred until S5 closes.*

### 1.B — Free-Wilson SAR

**Mandate preserved:** Free-Wilson decomposition treats each creative as a sum of substituent contributions (headline element, hero-image element, CTA framing, color palette, cell-targeting tag). SAR analysis identifies which substituents drive lift per cell. Conformal prediction bands quantify uncertainty per substituent contribution.

- **1.B.SI.1 — Free-Wilson decomposition + conformal prediction bands (offline).** Offline pipeline against historical creative library; conformal coverage validated. *Effort: 4d.*
- **1.B.SB.1 — Cell-tagged creative variants ingest.** Substrate-blocked on S6 (cell classifier v0). *Deferred.*

### 1.C — MRA / GENIE3 / dynGENIE3 / CMap Mediator Inference

**Mandate preserved:** Multivariate mediator inference identifies which intermediate variables (page-priming, dwell-time, prior-touch counts, archetype × cell interaction) mediate the bid → conversion path. GENIE3 and dynGENIE3 (Huynh-Thu et al.) for static and dynamic gene-regulatory-network-style mediator inference; Connectivity Map (CMap)-style perturbational matching for cross-creative similarity.

- **1.C.SI.1 — Offline mediator inference pipeline.** GENIE3 / dynGENIE3 on historical Stage C data; CMap-style signature matching across creatives. *Effort: 5d.*
- **1.C.SB.1 — Decision-time mediator-conditioned bid.** Substrate-blocked on S8 (retargeting v0 + propensity logging). *Deferred.*

### 1.D — H∞-Wrapped Kelly

**Mandate preserved:** Kelly bid-fraction sizing wrapped in an H∞ robust-control loop. H∞ provides the worst-case bound on bid trajectory under model misspecification; Kelly provides the growth-optimal fraction under correctly-specified expected reward. Cell-level expected-reward priors come from the historical backfill.

- **1.D.SI.1 — H∞ derivation (offline).** State-space formulation; H∞ controller synthesis; LMI-based numerical solution. *Effort: 4d.*
- **1.D.SB.1 — Kelly-fraction calibration with cell-level priors.** Substrate-blocked on S4 (historical backfill producing cell-level expected-reward priors). *Deferred.*

### 1.E — Funnel-MPC Receding-Horizon Scheduler with Prescribed-Performance Bounds

**Mandate preserved:** Model-Predictive Control over the funnel state (impressions remaining in budget × time remaining × cohort progression toward conversion). Receding-horizon scheduler with prescribed-performance bounds (Bechlioulis-Rovithakis style) ensures funnel-rate stays inside an envelope.

- **1.E.SI.1 — MPC formulation + receding-horizon solver.** *Effort: 4d.*
- **1.E.SB.1 — Prescribed-performance bound calibration.** Substrate-blocked on S6. *Deferred.*

### 1.F — PK/PD Frequency Model

**Mandate preserved:** Pharmacokinetic / pharmacodynamic modeling of ad exposure as a "drug." Hill-equation dose-response per creative; Mager-Jusko indirect-response models for creative effects with delay; Dayneka-Garg-Jusko four basic indirect-response model variants for inhibition/stimulation × production/elimination dynamics.

- **1.F.SI.1 — Model implementations.** Hill, Mager-Jusko, Dayneka-Garg-Jusko all four variants. Validated against canonical synthetic PK/PD profiles. *Effort: 4d.*
- **1.F.SB.1 — Per-user PK/PD calibration.** Substrate-blocked on S9 (per-user AR(1) carryover). *Deferred.*

### 1.G — Daw Two-System Arbitration

**Mandate preserved:** Daw, Niv, Dayan two-system arbitration between model-free (heuristic, habit-driven) and model-based (systematic, deliberative) processing. The cell-classifier + journey-state metadata serves as the heuristic-vs-systematic processing-mode signal feeding the arbitrator.

- **1.G.SI.1 — Two-system arbitration model.** *Effort: 3d.*
- **1.G.SB.1 — Processing-mode signal integration.** Substrate-blocked on S6 + S7. *Deferred.*

### 1.H — Persistent Homology of Trajectory Space

**Mandate preserved:** Topological data analysis on the user-trajectory manifold; persistent homology identifies stable clusters and trajectory-pattern motifs that survive across scales.

- **1.H.SI.1 — Offline persistent-homology pipeline.** Vietoris-Rips on trajectory embeddings; persistence diagrams; barcode generation. *Effort: 4d.*
- **1.H.SB.1 — Trajectory-pattern detection on live event log.** Substrate-blocked on S5 (Stage C trajectory event stream). *Deferred.*

### 2.E — Live User-State Detection from Post-Impression Telemetry (renamed)

**Mandate (new):** Replaces the spec-only `MicroStateDetector` at bid time. Operates on post-impression telemetry from Enhancement #08 Signal Aggregation. Substrate-blocked on S5.

- **2.E.S1 — Slice decomposition deferred until S5 closes.** Trigger: S5.7 synthetic-event injection tests pass and Stage C signal-aggregation surface is stable.

---

## PART 5 — V3 PHASE 2 GOVERNANCE PRE-WORK

These are pre-pilot drafting deliverables. They ship before live data, even though they activate later.

### G.1 — DMC Charter Draft (5-page document)

`docs/governance/DMC_CHARTER_DRAFT.md`. Sections:

1. **Authority.** The Data Monitoring Committee has authority to recommend pause, modification, or termination of any cell × cohort arm based on safety/efficacy signals. INFORMATIV CTO retains decision authority; DMC recommendations are advisory but documented.
2. **Composition and voting rules.** 3 members: one independent statistical methodologist, one independent advertising-domain expert, one INFORMATIV-internal but firewalled (Chris Nocera does not sit on DMC). Majority-vote recommendations.
3. **Blinding discipline.** DMC reviews unblinded data; the build team does not. Blinding starts at criterion-(ii) gate closure.
4. **Stopping rules.** Harm boundary (defined per-cell adverse-outcome rate, e.g., negative-creative-effect EBGM lower 5th percentile crossing threshold); futility boundary; efficacy boundary (always-valid sequential test threshold).
5. **Conflict-of-interest policy.** Disclosed annually; financial interest in advertisers, DSPs, or competing platforms recorded.
6. **Meeting cadence.** Monthly during pilot; weekly during Phase 2 ramp; ad-hoc on alert.

### G.2 — OSF Pre-Registration

Pre-registration filed on Open Science Framework before Gate G3 (LUXY ad-serving begins). Required elements:

- Primary endpoint: IPSW-corrected weighted conversion rate (fluid retargeting v0 → v1 → v2 vs naive frequency-cap baseline).
- Secondary endpoints: per-cell lift; per-archetype lift; AR(1) carryover-corrected per-user effect estimates.
- IPSW-corrected analyses pre-specified.
- Sequential-testing plan pre-specified: Howard-Ramdas confidence sequences for primary endpoint; Johari-Pekelis-Walsh mixture SPRT for binary comparison; Waudby-Smith e-process for sensitivity.
- ε-exploration-rate pre-specified: ε = 0.15 default, with adaptive reduction schedule documented.
- Component-ablation factorial pre-specified: cell-classifier on/off × journey-state on/off × per-user posterior on/off.

### G.3 — Pharmacovigilance Dashboard Schema

The schema is fixed pre-pilot; data populates post-pilot.

`adam/pharmacovigilance/schema.py`. Per-cell `(creative × cohort × posture × cell)` rows with:

- **PRR** — Proportional Reporting Ratio.
- **ROR** — Reporting Odds Ratio.
- **IC** — Information Component (with IC025 lower 5th percentile threshold).
- **EBGM** — Empirical Bayes Geometric Mean with **DuMouchel MGPS shrinkage** (DuMouchel 1999, *Amer. Stat.* 53:170–190; DuMouchel & Pregibon 2001 KDD '01) — two-gamma mixture prior; EBGM is the exponential of the expectation of log(RR), shrinking small-count cells toward the average reporting ratio (~1.0). EB05 lower 5th percentile is the operational signal threshold (signal if EB05 > 2 by Almenoff/EFSPI convention).
- **Tree-based scan statistics** — Kulldorff-style scan over the (creative × cohort × posture × cell) hierarchy for signal localization.

### G.4 — CONSORT-AI / SPIRIT-AI Reporting Template

`docs/reporting/CONSORT_AI_TEMPLATE.md` and `docs/reporting/SPIRIT_AI_TEMPLATE.md` — pre-formatted documents Chris fills in as data accumulates. CONSORT-AI extension for AI interventions (Liu et al. 2020 *Nat Med*); SPIRIT-AI extension for protocol pre-specification (Cruz Rivera et al. 2020 *Nat Med*).

---

## PART 6 — INTEGRATION SEAMS WITH PHASE A WRAP-OUT

Slices 24 / 27 / 35 from Phase A wrap-out are the integration points. Substrate work-streams plug in via the registry pattern, soft-fail back-compat preserved.

| Phase A Seam | Substrate Plug-In | Notes |
|---|---|---|
| **Slice 24 `BidComposer` protocol seam** | Cell-classified bid composition (S6/S7 → S8/S9) | Default adapter remains in place; `CellClassifiedBidComposer` registers as a named adapter; feature-flag controls swap. |
| **Slice 24 `CarryoverCorrectionStrategy` protocol seam** | AR(1) carryover at per-user level (S9.4) | Default `NaiveCarryover` swapped for `PerUserAR1Carryover`. |
| **Slice 24 `WashoutModel` protocol seam** | Inter-touch timing recommendation (S8.3) | Default replaced by per-archetype × per-journey-state timing curves. |
| **Slice 27 protocol-replacement regression net** | Sentinel-behavior tests through new substrate components | Every protocol swap above is exercised by Slice 27's regression net at real call sites. New sentinels added as substrate components ship. |
| **Slice 35 StackAdapt shadow-mode bidder wire** | Live-decision logging for retargeting v0 (S8.7) | Registry-honored; dual-persistence `ShadowBidRecord` + `DecisionTrace` continues; v0 logs every decision in shadow mode for the first week post-Gate-G3. |

**Discipline:** No substrate work-stream introduces a new protocol seam if a Slice-24/27/35 seam already exists for the relevant boundary. The wrap-out interfaces are the canonical integration points.

---

## PART 7 — FAILURE-MODE PLAYBOOK

| Risk | Detection | Response |
|---|---|---|
| **StackAdapt rate limits tighter than assumed** | S0/S4 rate-limit-exhausted exits; nightly incremental falling behind. | Reduce `pageSize` from 500 to 200; increase max delay from 60s to 180s; surface to Chris to negotiate higher quota with StackAdapt account manager. Do not parallelize keys without explicit instruction (TOS risk). |
| **Reporting granularity coarser than impression-level** | Q1 returns only daily aggregates per creative, not impression-level. | Fall back to `DeliveryReport` daily-aggregate query; surface limitation explicitly; impression-level features (per-impression page-priming) are degraded to creative-day averages with confidence flag. |
| **Pixel-postback attribution coverage imperfect** | `sapid` correlation rate < 80% at S8.7. | Run join diagnostics; surface unmatched-postback rate by domain × creative × day; do not infer untrackable conversions; report attribution coverage in every dashboard. |
| **Within-subject crossover assumptions violated** (e.g., severe carryover beyond AR(1)) | S9.8 always-valid sequential test residual diagnostics show structured autocorrelation. | Extend washout intervals; consider AR(2) extension as a guarded slice; do not silently relax the protocol. |
| **Cell classifier confidence collapses (everything classifies into one cell)** | S7.4 calibration plots; one cell with > 70% of mass. | Halt v1 deployment; rerun S6/S7 from a domain-isolated bootstrap; investigate feature collapse (Feature Store cold-miss flooding); never push a degenerate classifier behind the live feature flag. |
| **Retargeting trajectory thrashes (too aggressive exploration)** | Per-user posterior variance not contracting over touches; v0/v1 lift gap not opening. | Reduce ε from 0.15 to 0.10 per pre-registration adaptive-reduction schedule; do not exceed pre-registered bounds without amending OSF pre-registration. |
| **Carryover model misspecification** | AR(1) residuals show structure; ADWIN drift triggers correlate with touch density. | Surface to Chris; do not auto-extend model order — that is an architectural decision. |
| **Cross-tenant prior contamination** | Synthetic second-tenant fixture shows information bleed-through that violates the basket-trial gate. | Halt cross-tenant gate evaluation; never open Gate G8; investigate. |
| **Pixel-postback latency biasing learning signals** | Postback latency distribution has a heavy tail beyond the within-day window. | Add latency-aware weighting to trajectory event timestamps; do not drop late postbacks; do not silently truncate. |
| **Validation under continuous monitoring tempts premature conclusions** | Always-valid sequential test crosses boundary early; pressure to declare. | Honor the always-valid framework — that is exactly what it protects against. Do **not** apply a fixed-n test on top to "double-check." Do not unblind early. DMC adjudicates per G.1 stopping rules. |

---

## PART 8 — DECISION POINTS AND HARD-STOP GATES

Claude Code surfaces each gate to Chris **before** proceeding past. No gate is auto-traversed.

| Gate | Closes When | Unlocks |
|---|---|---|
| **G0** | Slice 0 closed; `READY_FOR_RATER_WORKSHEET.flag` written. | S1 begins. |
| **G1** | Criterion (ii) closes against held-out gate: macro-AUC ≥ 0.50 AND top-1 ≥ 0.40 on domain-isolated held-out fixture. | Posture-dependent v3 Phase 1 sub-work-streams begin (1.B.SB, 1.E.SB, 1.G.SB); S6 begins. |
| **G2** | Retargeting audit reports (`docs/RETARGETING_AUDIT_2026_05_<DD>.md`) signed off by Chris. | S8 build begins. |
| **G3** | S8 ships + Pixel round-trip validated in StackAdapt sandbox + p99 latency budget met + shadow-mode logging operational. | LUXY ad-serving begins. |
| **G4** | 4 weeks of pilot serve data accumulated; ADWIN baseline-stable. | S9 build begins. |
| **G5** | 8 weeks of pilot data + cross-tenant infrastructure stable against synthetic second-tenant. | S10 build begins. |
| **G6** | Substrate work-streams S4 / S5 / S6 / S7 / S8 / S9 / S10 complete. | All v3 Phase 1 substrate-blocking sub-work-streams begin. |
| **G7** | All v3 Phase 1 work-streams complete + DMC charter signed + OSF pre-registration filed. | v3 Phase 2 ramp begins. |
| **G8** | v3 Phase 2 ramp complete + first PSUR (Periodic Safety Update Report) delivered. | Cross-tenant client onboarding begins; cross-tenant priors integrated live (S10.7). |

---

## PART 9 — APPENDICES

### Appendix A — GraphQL Query Templates (Q1, Q2, Q3, Q4)

**Q1 — DeliveryReportImpressionLevel** — see Part 1 §1.2.

**Q2 — CreativeMetadata** (for Free-Wilson decomposition input):
```graphql
query Q2_CreativeMetadata($advertiserIds: [ID!]!, $cursor: String) {
  creatives(advertiserIds: $advertiserIds, after: $cursor, first: 200) {
    pageInfo { hasNextPage endCursor }
    edges { node {
      id name campaignId headline ctaText
      heroImageUrl colorPaletteHex variantTags
      createdAt status
    } }
  }
}
```

**Q3 — ConversionPath** (for trajectory reconstruction):
```graphql
query Q3_ConversionPath(
  $advertiserIds: [ID!]!
  $dateFrom: Date!
  $dateTo: Date!
  $cursor: String
) {
  conversionPaths(
    advertiserIds: $advertiserIds
    dateFrom: $dateFrom
    dateTo: $dateTo
    after: $cursor
    first: 200
  ) {
    pageInfo { hasNextPage endCursor }
    edges { node {
      conversionId userKey conversionTimestamp
      touchpoints { creativeId campaignId touchTimestamp domain url sapid }
      revenueUsd
    } }
  }
}
```

**Q4 — AudienceSegmentDelivery** (for per-cohort posterior priors):
```graphql
query Q4_AudienceSegmentDelivery(
  $advertiserIds: [ID!]!
  $dateFrom: Date!
  $dateTo: Date!
  $cursor: String
) {
  audienceSegmentDelivery(
    advertiserIds: $advertiserIds
    dateFrom: $dateFrom
    dateTo: $dateTo
    breakdowns: [SEGMENT_ID, DAY, DEVICE_TYPE]
    after: $cursor
    first: 500
  ) {
    pageInfo { hasNextPage endCursor }
    edges { node {
      segmentId day deviceType
      impressions clicks conversions spend
    } }
  }
}
```

### Appendix B — Bash Commands for Build Operations

```bash
# Slice 0 ingestion (one-shot)
python -m adam.tools.stackadapt_historical_extract \
  --advertiser-id "$LUXY_ADVERTISER_ID" \
  --date-from "$(date -d '365 days ago' +%Y-%m-%d)" \
  --date-to "$(date +%Y-%m-%d)" \
  --output artifacts/luxy_historical/

# S4 backfill (permanent pipeline)
python -m adam.ingestion.stackadapt.historical_puller \
  --advertiser-id "$LUXY_ADVERTISER_ID" \
  --backfill-months 12 \
  --persist iceberg+neo4j+postgres

# S4 incremental (cron)
python -m adam.ingestion.stackadapt.incremental_puller \
  --advertiser-id "$LUXY_ADVERTISER_ID" \
  --since-checkpoint

# IPSW sampler
python -m adam.sampling.ipsw_sampler \
  --strata iab,device,daypart \
  --conversion-oversample-multiplier 5 \
  --output artifacts/training_fixtures/

# Posture classifier retrain (S1.3)
python -m adam.classifiers.posture.train \
  --labels artifacts/labeling/round_4_consolidated_<date>.jsonl \
  --held-out-by domain \
  --checkpoint-out artifacts/checkpoints/

# Held-out evaluation (S1.4 / Gate G1)
python -m adam.classifiers.posture.evaluate \
  --checkpoint artifacts/checkpoints/posture_classifier_round4_<date>.pt \
  --gate-macro-auc 0.50 --gate-top1 0.40 \
  --report artifacts/evaluation/

# Cell classifier v0 train (S6)
python -m adam.cells.classifier_v0.train \
  --rules adam/cells/taxonomy.py \
  --features-page-priming on \
  --features-posture on

# Retargeting v0 sandbox round-trip (S8.7)
python -m adam.retargeting.v0.sandbox_e2e \
  --sandbox stackadapt --pixel-roundtrip --archetype careful_truster
```

### Appendix C — File-Path Conventions

```
adam/
  bilateral/
    sequences.yaml                  # S8.2 extracted per-archetype plans
    mechanism_deployment.py
  cells/
    taxonomy.py                     # S6.1
    classifier_v0/
    classifier_v1/
  classifiers/
    posture/
  ingestion/
    stackadapt/
      historical_puller.py          # S4.1
      incremental_puller.py         # S4.1
      pixel_correlator.py           # S4.1
      rate_limited_session.py       # S4.1
      schemas/                      # S4.2
      queries/                      # graphql files
  integrations/
    stackadapt/
      adapter.py                    # exists
      graphql_client.py             # exists
      pixel_client.py               # exists
  pharmacovigilance/
    schema.py                       # G.3
  priming/
    signature.py                    # S3.1
    pipeline.py                     # S3.2
  retargeting/
    context.py                      # S8.1
    v0/                             # S8
    v1/                             # S9
    v2/                             # S10
  sampling/
    ipsw_sampler.py                 # S4.6
artifacts/
  luxy_historical/                  # S0/S4 output
  labeling/                         # rater worksheets + consolidated
  checkpoints/
  evaluation/
  training_fixtures/
docs/
  MEMORY.md                         # session persistence
  RETARGETING_AUDIT_2026_05_<DD>.md # S2
  DEFERRED/2.E.S1_LIVE_USER_STATE.md
  governance/DMC_CHARTER_DRAFT.md   # G.1
  reporting/CONSORT_AI_TEMPLATE.md  # G.4
  reporting/SPIRIT_AI_TEMPLATE.md   # G.4
tests/
  <area>/<slice-id>_<descriptor>_test.py
tools/
  labeling/
    generate_rater_worksheet.py     # S1.1
    consolidate_rater_responses.py  # S1.2
  stackadapt_historical_extract.py  # S0
```

### Appendix D — Commit-Message Conventions

```
<type>(<scope>): <slice-id> <imperative-mood description>

Body:
- Slice ID: S<n>.<m>
- Predecessors closed by this commit: [list]
- Test-suite delta: +<added> / -<removed> / =<total passing>
- Why this slice now: <one-line justification>
```

**Examples:**
```
feat(stackadapt): S0 historical URL extraction one-shot

- Slice ID: S0
- Predecessors closed: G0
- Test-suite delta: +14 / -0 / =4394
- Why this slice now: unblocks 4-rater labeling and criterion (ii) gate
```

```
test(retargeting): S8.7 sandbox round-trip + shadow-mode integration

- Slice ID: S8.7
- Predecessors closed: S8.1–S8.6
- Test-suite delta: +28 / -0 / =4486
- Why this slice now: Gate G3 prerequisite, LUXY ad-serve unblock
```

### Appendix E — MEMORY.md and EVE Handoff Pattern

`docs/MEMORY.md` is a single file Claude Code reads at session start and appends to at session end.

**Structure:**

```markdown
# MEMORY.md — Claude Code Session Persistence

## Session Index
- 2026-05-04 (session #001)
- 2026-05-05 (session #002)
- ...

## Current State
- Active branch: feature/hmt-dashboard
- Active slice: S0 (IN_PROGRESS)
- Last commit: <SHA> "feat(stackadapt): S0..."
- Test suite: 4380 passing
- Open QUESTIONS: [link to most recent status report]

## Per-Session Append (newest at bottom)

### Session 2026-05-04
**EVE Handoff:**
- E (Executed): drafted adam/tools/stackadapt_historical_extract.py skeleton; ran introspection ping (passed).
- V (Verified): introspection returned __schema; auth confirmed.
- E (Expected next session): wire Q1 query template; pagination loop; checkpointing.
- Open QUESTIONS: none.
- Hand-off pointer: continue at adam/tools/stackadapt_historical_extract.py line 47.
```

The **EVE pattern** (Executed / Verified / Expected-next) is the minimum entry. Every session ends with an EVE block. Every session begins by reading the last EVE block.

### Appendix F — What Survives, What Gets Wrapped, What Gets Replaced

| Item | Status | Notes |
|---|---|---|
| StackAdapt GraphQL client (`graphql_client.py`) | **Survives** | Extended in S0/S4 with cursor pagination + async-Outcome polling helpers. |
| StackAdapt adapter (`adapter.py`) | **Survives** | Used by S4 ingestion package. |
| Pixel client (`pixel_client.py`) | **Survives** | Used by S8.4 postback wiring. |
| Neo4j graph schema | **Survives** | S4.3 adds trajectory edges. |
| FastAPI app | **Survives** | New endpoints added per slice. |
| Redis Feature Store (Enh #30) | **Survives** | S3.3 adds page-priming-signature surface. |
| Redis L1/L2/L3 caching cascade (Enh #31) | **Survives** | Page-priming lookups inherit it. |
| Kafka topics | **Survives** | S4.5 adds `adam.ingestion.stage_c`. |
| LangGraph orchestration | **Survives** | New nodes per slice. |
| Claude API offline | **Survives** | Constraint reaffirmed: never in real-time inference. |
| Slice 24 `BidComposer` seam | **Survives, plugged** | Cell-classified composer registers as adapter. |
| Slice 24 `CarryoverCorrectionStrategy` seam | **Survives, plugged** | AR(1) per-user adapter swapped in S9.4. |
| Slice 24 `WashoutModel` seam | **Survives, plugged** | Per-archetype × journey-state timing curves swap in via S8.3. |
| Slice 27 protocol-replacement regression net | **Survives, extended** | New sentinels per substrate component. |
| Slice 35 shadow-mode bidder wire | **Survives, plugged** | S8.7 logs every v0 decision. |
| Held-out fixture rotation rule (commit 4b94591) | **Survives, enforced** | Domain-isolation rule applies to S1.3, S3.5, S6.3, S7.4. |
| Collision check (commit 61644a9) | **Survives, enforced** | 42 unit tests + 16 historical regressions; new collisions append. |
| Spec-only `MicroStateDetector` at bid time | **Replaced** | By page-priming-signature lookup (S3); live user-state deferred to 2.E.S1. |
| Synthetic `round_3_diversification_candidates.jsonl` | **Replaced** | By `luxy_served_urls_<date>.unique_urls.jsonl` from S0. |
| Phase 9 simulation (5-arch × 2-horizon, commit 14f3d9f) | **Survives (CLOSED)** | Hard-stop criterion (i) closed; do not re-open. |
| Section 6 cadences end-to-end on LUXY corpus (commit 53253c8) | **Survives (CLOSED)** | Hard-stop criterion (iii) closed; do not re-open. |
| Hard-stop criterion (ii) (5-class posture macro-AUC ≥ 0.50, top-1 ≥ 0.40) | **REOPENED** | LOOCV inflation surfaced by held-out evaluator; closes via S1.4 against domain-isolated fixture. |
| v2 (clinical-trial directive) | **Retired** | Formally retired by this directive. |
| v3 original | **Replaced** | This rewrite is canonical. |

---

## CLOSING DISCIPLINE

This directive is the contract. Claude Code reads it; Claude Proper writes prompts against it; Chris arbitrates. Three rules govern every working session:

1. **Slice discipline.** One slice, one commit, one success criterion. No bundling, no shortcuts, no amendments.
2. **Gate discipline.** Gates G0–G8 are surfaced explicitly; never auto-traversed; Chris signs each off.
3. **Test discipline.** 4380+ baseline; no regressions; new code ships with new tests; failed tests block commits.

The platform under construction is a bilateral psycholinguistic intelligence system whose architecture rests on decades of methodological lineage (Yale Bargh; LISREL; Cronbach; IRT; pharmacogenomic design; PK/PD modeling; medicinal chemistry SAR; particle-physics blind analysis; sequential analysis). The directive's rigor must match the architecture's. When in doubt, slow down and ask. The asymmetric cost of the prompt-loop overhead versus a wrong-premise rebuild is the central operational fact this directive enforces.

**End of directive.**