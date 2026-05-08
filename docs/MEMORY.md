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
- Active slice: **Session #005 CLOSED** (4 slices shipped + 1 docs follow-up + 2 EVE handoff record commits)
- Last commit on branch: this commit (close session #005 EVE handoff record — append)
- Test suite: 4999 passing (added +168 across session #005's 4 slices: +49 / +31 / +49 / +39); 9 pre-existing failures + 5 skipped unchanged
- Open QUESTIONs: QUESTION 4 still standing (S1 gate-failed); QUESTIONs 6/7/8 surfaced this session as discoveries (held-area boundary, schema-collision rediscovery via parallel-client near-miss, 4-vs-5-class taxonomy question feeding QUESTION 4) — all routed to Claude Proper, none addressed in code; next conversation adjudicates G1 pivot
- Critical-path next: **G1-pivot adjudication in next conversation** (paste `docs/S0_HANDOFF_2026_05_04.md` + operational architecture doc per Closing Block)
- Standstill items (resume after Claude Proper adjudication / amended slice prompts): S1 build, directive-amendment slice, S0 G1-pivot architecture, S8 build (audit signed off pending Chris review per S2 closure criterion)

### Architecturally consequential carry-forward (session #004 → next, still standing)

**S2 audit collapsed S8's scope.** The retargeting substrate audit (`docs/RETARGETING_AUDIT_2026_05_04.md`) found Surface 5 (decision-time cascade) 100% shipped — `BidComposer` / `CarryoverCorrectionStrategy` / `WashoutModel` Protocols + default implementations + registry-pattern adapter swap all live in `adam/intelligence/v3_interfaces.py`. The bilateral cascade (Surface 3) is a 3909-line L1→L2→L3 implementation already in production with TTTS propensity-logged primary selection, page-shift integration, and chain-attestation primitive. The journey-state machine (Surface 1) and TherapeuticTouch/TherapeuticSequence models (Surface 2) are both ~70-80% shipped. The `PixelCorrelator` (Surface 4) just shipped in S4.1 (`a2c9124`). **Net:** S8 reduces from "build retargeting v0" to "wire `RetargetingOrchestrator` that registers as a `BidComposer` adapter via the existing Slice 24 seam, composing journey-state + cell classifier + page-priming + sequence selection + bilateral cascade L3 + chain-attestation, with shadow-mode logging via Slice 35." Every other piece exists. This is the architecturally consequential framing the next session should authorize against.
- Substrate-blocked deferred (per directive): S3.2-S3.6 (URL corpus dependent), S4.2-S4.8 (Iceberg/Neo4j/Postgres + IPSW + e2e + live backfill), S5/S6/S7/S8/S9/S10 chain, 1.A.SB.1 / 1.B.SB.1 / 1.C.SB.1 / 1.D.SB.1 / 1.E.SB.1 / 1.F.SB.1 / 1.G.SB.1 / 1.H.SB.1 (all SB items)
- Substrate-independent v3 Phase 1 items remaining for next session(s): 1.B.SI.1, 1.C.SI.1, 1.D.SI.1, 1.H.SI.1 (1.A.SI.2 + 1.G.SI.1 + 1.F.SI.1 + 1.E.SI.1 closed in session #005)

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

### Session 2026-05-05/06 — session #005 — Compute-fill ship-cleanest-first: 4 substrate-independent v3 Phase 1 SI slices shipped + 1 docs follow-up

**EVE Handoff:**

- **E (Executed):** 4 slices closed, in ship-cleanest-first order (smallest spec / cleanest dependencies first), plus a docs follow-up on the fourth:
  1. `b39c18e` **1.A.SI.2 Gross-Vitells LEE trial-factor** — adam/blind_analysis/lee.py + tests; closed-form `gross_vitells_global_p_value` / `gross_vitells_trial_factor` per Gross & Vitells 2010 eq. (1) with Davies 1987 asymptotic upcrossings; Monte-Carlo cross-check via squared-exponential Gaussian random field on a 1-d grid (`monte_carlo_global_p_value`, n_trials=10_000 ensemble matches closed-form at z=2.5 within 3 standard errors). 49 tests including the directive's specific parametrization target — asymptotic linearity (TF − 1) / z → ⟨N⟩ * √(2π) at large z — exercised at 20 (z, N) combinations. Composes with §1.A.SI.1 sealed-box pre-registration via TestIntegrationWithSealedBox.
  2. `ae2e1fc` **1.G.SI.1 Daw uncertainty-weighted arbitration** — adam/two_system/{__init__,arbitration}.py + tests; Bayesian inverse-variance arbitration of model-free (cached, habit-driven) vs model-based (deliberative, simulated) Q-value estimates per Daw, Niv, Dayan 2005 *Nat. Neurosci.* 8:1704-1711. `arbitrate_with_processing_mode_prior` is the seam §1.G.SB.1 will plug into once S6 + S7 close — λ=0.5 linear blend between inverse-variance MB-weight and exogenous prior in [0, 1]. `softmax_action_selection` provides Boltzmann policy with max-subtraction stability. 31 tests including end-to-end composition where the systematic prior can FLIP action preference when MF and MB systems disagree (the behavioral signature SB.1 will calibrate against).
  3. `b75e904` **1.F.SI.1 Hill / Dayneka-Garg-Jusko PK/PD** — adam/pkpd/{__init__, hill, indirect_response}.py + tests; closed-form Hill / Emax sigmoid + the four canonical Dayneka-Garg-Jusko 1993 *J. Pharmacokinet. Biopharm.* 21:457-478 indirect-response model variants (inhibit input/output × stimulate input/output) integrated via scipy LSODA. Analytical-steady-state cross-checks at saturating c → numerical match within 1e-4 relative. 49 tests including delayed step-off response showing IRM-family signature lag behavior. A14 PILOT_PENDING flags MECHANISM_PHARMACOLOGY_LITERATURE_MIDPOINTS_PILOT_PENDING + TOLERANCE_RATE_EXPONENTIAL_PILOT_PENDING bind at the 1.F.SB.1 stage (substrate-blocked on S9), not here.
  4. `8dd4c0b` **1.E.SI.1 Funnel-MPC formulation + receding-horizon solver** — adam/funnel_mpc/{__init__, formulation, solver}.py + tests; `PrescribedPerformanceEnvelope` per Bechlioulis & Rovithakis 2008 IEEE TAC 53:2090-2099 eq. (2) with strict-interior `contains()` (open-set semantics); `FunnelMPCProblem` per Camacho & Bordons 2007 *Model Predictive Control* (Springer 2nd ed., Ch. 2) generic over (state_dim, control_dim) with `rollout` / `cost` primitives; `solve_mpc_step` using scipy.optimize.minimize SLSQP with state-inequality constraints converted to ≥ 0 form; `simulate_receding_horizon` with optional warm-start. 39 tests including CLOSED-LOOP DISTURBANCE-RECOVERY (one-time unmodeled state kick at t=5 absorbed by re-optimization — the receding-horizon principle's central robustness claim) and PPC envelope wired as state constraint via the canonical Funnel-MPC use case. Mayne et al. 2000 *Automatica* 36:789-814 named for the consumer's V_f / terminal-set choice that determines closed-loop stability.
  5. `41fc66f` **1.E.SI.1.docs A14 flag forward-reference block** — adam/funnel_mpc/__init__.py docstring; adds an "ACTIVE A14 CALIBRATION-PENDING FLAGS" block naming `FUNNEL_CONTROL_CALIBRATION_PILOT_PENDING` per QUESTION 5 resolution. Single construct-level flag with heterogeneous payload (envelope tuple per cell × cohort + global cost weights + global horizon); precedent established by `MECHANISM_PHARMACOLOGY_LITERATURE_MIDPOINTS_PILOT_PENDING`. "Control" rather than "dynamics" naming deliberate — dynamics f(x, u, k) explicitly excluded from flag scope. Doc-only change, zero source-code coupling.

  **Total: +168 tests** all passing across the four slices (49 + 31 + 49 + 39). Test suite at 4999 passing.

- **V (Verified):**
  - All 4 slice tests pass independently and in batch (168/168).
  - 9 pre-existing failures unchanged (TestCampaignDocs * 8 + test_dag_has_14_atoms) — confirmed before session start (4831 baseline) and after each commit (4880 → 4911 → 4960 → 4999 → 4999 after docs follow-up).
  - 5 skipped unchanged across the session.
  - PYTHONPATH=/Users/chrisnocera/Sites/adam-platform required for pytest collection (otherwise pytest hits 215 ModuleNotFoundError on `adam.*` collection — environment-only, not a regression). This is the local-dev invocation pattern; project pyproject.toml has `testpaths = ["tests"]` but no `pythonpath` setting.
  - Each commit body follows directive Appendix D format established by session #004 (slice ID, predecessors closed, test-suite delta, why this slice now, Module / Tests / Composition / References / Co-Author trailer).
  - Staged set verified by `git diff --stat --cached` before each commit (1.A.SI.2: 3 files; 1.G.SI.1: 4 files including tests/two_system/__init__.py; 1.F.SI.1: 6 files including tests/pkpd/__init__.py; 1.E.SI.1: 6 files including tests/funnel_mpc/__init__.py; 1.E.SI.1.docs: 1 file). No leakage from working-tree untracked files.

- **E (Expected next session):**
  - **Primary** — next conversation still adjudicates G1 pivot per `docs/S0_HANDOFF_2026_05_04.md` Closing Block. The hold from session #004 is unchanged by this session's compute-fill work. **QUESTIONs 6/7/8 surfaced this session compose with the existing G1-pivot adjudication context — see "Open QUESTIONs" + "Procedural notes" below.**
  - **Secondary parallel work-stream remaining for compute-fill** if Chris wants more autonomous SI ship-runs:
    - 1.B.SI.1 (Free-Wilson decomposition + conformal prediction bands)
    - 1.C.SI.1 (MRA / GENIE3 / dynGENIE3 / CMap mediator inference)
    - 1.D.SI.1 (H∞ robust-control derivation)
    - 1.H.SI.1 (Persistent-homology offline pipeline)
  - **Held until adjudication:** S1 build, S8 build, directive-amendment slice, G1-pivot architecture (all unchanged from session #004).

- **Open QUESTIONs:**
  - **QUESTION 4** (S1 entry-condition gate-failed) still standing — unchanged from session #004.
  - **QUESTION 5** (A14 flag-naming for Funnel-MPC) — RESOLVED in session via `41fc66f`. Decision: Option 1 single construct-level flag, name `FUNNEL_CONTROL_CALIBRATION_PILOT_PENDING`, heterogeneous-payload precedent confirmed via `MECHANISM_PHARMACOLOGY_LITERATURE_MIDPOINTS_PILOT_PENDING`.
  - **QUESTION 6** (NEW — held-area boundary case): a script for IRR labeling pulls (`pull_luxy_candidate_urls_for_irr.py`) was surfaced mid-session as a candidate for execution. Audited as **S1.1 work** (rater-worksheet generation pipeline), which is held pending Claude Proper adjudication of QUESTION 4. **Routed to Claude Proper, not executed in code. The audit response itself was the slice work.**
  - **QUESTION 7** (NEW — schema-collision rediscovery via parallel-client near-miss): the same script's `CAMPAIGN_URLS_QUERY` uses `campaign(id) { deliveryReport(dimensions: [URL, DOMAIN], ...) }` which **does not exist in the live StackAdapt schema** (rediscovery of session #003's S0 schema-mismatch finding). The corrected schema is already implemented at `tools/stackadapt_historical_extract.py` (commit `54407ac`) using `conversionPath` + `campaignPageContext` per directive §1.3 *"Reuse, do not recreate."* Routed to Claude Proper as a script-redesign question.
  - **QUESTION 8** (NEW — 4-vs-5-class taxonomy question feeding QUESTION 4): the same script samples 4 of 5 canonical posture classes (omits `INFORMATION_FORAGING`). G1 gate criterion (ii) is macro-AUC ≥ 0.50 AND top-1 ≥ 0.40 across all five classes per `adam/intelligence/posture_five_class.py:106` (`FIVE_CLASS_POSTURES`). A retrain on a 4-class corpus cannot evaluate against the 5-class gate (per-class AUC for the missing class is undefined). Routed to Claude Proper as a G1-pivot architecture question.

- **Hand-off pointer:** Branch `feature/hmt-dashboard` at `41fc66f` (4 slices + 1 docs follow-up shipped this session beyond the standdown anchor `2df2822`); this EVE-append commit follows. Working tree clean except this MEMORY.md update (picked up by the standdown record commit per Appendix E pattern). Four new top-level packages introduced this session: `adam/blind_analysis/lee.py` (extends existing), `adam/two_system/` (new), `adam/pkpd/` (new), `adam/funnel_mpc/` (new). Test directories created at `tests/blind_analysis/test_lee.py`, `tests/two_system/`, `tests/pkpd/`, `tests/funnel_mpc/`.

- **Procedural notes:**
  - The opener's §4 compute-fill authorization scoped this session cleanly — four slices shipped without reaching for any architecturally-blocked work.
  - The discipline rule *"If a prompt instruction would cause work in any of the four held areas, stop and surface as a QUESTION"* was triggered exactly once (the IRR script — QUESTIONs 6/7/8) and honored: no script execution, no file write, no production-API call. The audit response was the slice. This is the discipline rule operating as designed.
  - The 1.F.SI.1 first pytest run had 4 tolerance failures (numerical → analytical agreement at c=1000 × IC_50 was ~0.15%, my tolerance was 0.1%). All four were resolved by switching two saturation tests to mathematical-limit concentrations (1e5 / 1e6 × half-max → ~1e-4 agreement) and accepting rel=1e-2 on the dynamic step-off test (LSODA integrator residual at ~7 time constants). Tolerance discipline noted in the commit body.
  - 1.E.SI.1 passed 39/39 on first pytest pass — no tolerance loosening needed. The math + test conditions held.
  - A14 flag-binding decision finalized this session: A14 PILOT_PENDING flags **may** be forward-referenced at SI.1 in the module docstring (per `41fc66f`'s Funnel-MPC pattern), but the runtime `CalibrationStatus.PILOT_PENDING` binding still lands at SB.1 in the calibrated production atom. The forward-reference is documentation-only and creates the audit trail SB.1 prompt-author can follow. Earlier slices (1.A.SI.2, 1.G.SI.1) did not forward-reference; 1.F.SI.1 forward-referenced two flags inline in the commit body's Composition section but not in the module docstring; 1.E.SI.1 forward-referenced via the `1.E.SI.1.docs` follow-up. The pattern is now established for future SI.1 slices.

---

### Session 2026-05-08 — W.0 substrate accessor wiring audit landed (read-only memo)

**EVE Handoff:**

- **Executed:** W.0 read-only audit. Ten-pass inspection of the 6 substrate accessors S6.2's `CellFeaturesAggregator` needs wired (replacing `default_aggregator()` neutral-defaults at `bilateral_cascade.py:2882`) producing tracked memo at `docs/audits/SUBSTRATE_ACCESSOR_WIRING_AUDIT.md` (~3,783 words / 19 ##-level sections: 5-line header block + §1 Executive Summary + §2-§9 per-accessor passes + §10 latency budget + §11 wiring approach inventory + §12 W.1+ recommended sequence + §13 QUESTION-and-stop concerns + §14 closure). Audit-then-implement pattern matching A.1.0 + A.2.0 + S6.2.0 precedents. Zero code changes; zero test changes.

- **Wiring approach distribution (Pass 11 inventory):**
  - **(a) Direct-call: 1** — `cohort_accessor` (F.2's `get_cohort_compensatory_flag` matches S6.2's expected signature exactly).
  - **(b) Lightweight adapter: 3** — `posture_accessor`, `priming_accessor`, `cascade_tier_accessor` (5-line lambdas/wrappers for minor signature mismatches).
  - **(c) Coordinator wrapper: 1** — `journey_accessor` (20-50 line wrapper because journey state lives across multiple modules and ConversionStage mapping needs explicit composition with `to_conversion_stage`).
  - **(d) Build-the-accessor: 3** — `archetype_accessor`, `mindstate_accessor`, `maximizer_prior_accessor` (don't exist as single function calls today; W.1+ must construct from existing pieces).

- **Recommended W.1+ slice sequence (4 slices estimated per §12):**
  - W.1: bundle direct-call (cohort) + lightweight adapters (posture, priming, cascade_tier)
  - W.2: journey coordinator wrapper
  - W.3: archetype + maximizer build-the-accessor interims (pilot stubs vs full constructions)
  - W.4: mindstate build-the-accessor (potentially split per Q20 — see scope-expansion finding below)

- **5 QUESTION-and-stop concerns surfaced for Claude Proper adjudication:**
  - **Q20 — mindstate C+D orchestrator field population (MOST CONSEQUENTIAL).** The C+D-derived mindstate properties (`fomo_score`, `psych_ownership_proxy`, `depletion_proxy`) **do not fire on real bid data without a separate substrate-fetch path**. `extract_mindstate_vector` does not populate the orchestrator-side fields the C+D properties depend on, and some of those fields (`touch_count`, `dwell_seconds`, `session_position_seconds`) come from session-telemetry surfaces that don't exist as cached bid-time accessors today. **Half the seed predicates (3 of 6 — high_fomo_promotion, high_fomo_prevention, high_psych_ownership_endowment_reinforce, plus depletion-keyed predicates if added later) are dead-letter until Q20 is resolved.** W.4 may need to split (W.4a extraction-only at defaults; W.4b session-telemetry layer).
  - **Q21 — asyncio.run in sync hot path.** Some accessor paths require crossing async/sync boundaries; calling `asyncio.run` in the bid hot path is a latency disaster. Adjudication needed: pre-run async work into a sync cache, or convert the aggregator integration block to run within an async context.
  - **Q22 — <8ms aggregator p99 budget exceeded by sum-of-accessors estimate.** Per-accessor latency estimates summed exceed S6.2's <8ms target. Adjudication: revise budget upward (move time from elsewhere in the 25ms retargeting slot), introduce parallel-fetch via `asyncio.gather`, or accept that some accessors must be cached more aggressively.
  - **Q23 — default category for journey_accessor.** The journey state machine's cold-start behavior may not return UNAWARE (S6.2's neutral default); some flows return `None` and others return a different starting stage. Adjudication: standardize cold-start to UNAWARE in the wrapper, or revise S6.2's neutral default policy.
  - **Q24 — archetype pilot stub vs full build.** A per-user archetype accessor doesn't exist as a single function. Pilot can stub with PRAGMATIST default for all users (matches S6.2's neutral default; predicates that condition on archetype don't fire) or W.3 can build a real accessor wrapping the cold-start archetype detection. Adjudication: pilot urgency vs predicate-fire-rate tradeoff.

- **Pre-flight findings:**
  - All 9 inspection points populated for each of 6 accessors (Pass 1-7 in §2-§8) plus optional cascade_tier_accessor (Pass 8 in §9).
  - Latency-budget accounting (§10): per-accessor estimates derived from existing benchmarks where present + estimates otherwise. Sum exceeds 8ms — this is the Q22 concern.
  - Wiring approach inventory (§11): classification table with rationale per accessor.

- **Verified:**
  - Memo present at expected path (`docs/audits/SUBSTRATE_ACCESSOR_WIRING_AUDIT.md`); 32KB; all 19 sections present per spec.
  - Zero tracked files modified by audit fork (only the new untracked memo file in working tree).
  - All claims in memo cite `path:line` references throughout per audit discipline rule.
  - Full pytest unchanged (no code changes; baseline 5,598 passing remains intact).

- **Architectural decision history note:** The audit-first discipline keeps paying for itself. Q20 (mindstate dead-letter) would have been a substantial pre-pilot disappointment if discovered after wiring 4 slices and noticing predicates still don't fire. Q22 (latency budget overrun) would have manifested as production p99 spikes if discovered post-wiring. Q24 (archetype pilot stub vs full build) is a scope decision that affects W.3 sizing — better adjudicated before W.3 starts. The audit makes the W.1+ sequence shippable on real findings rather than assumptions.

- **Expected next:** **W.1 first wire slice** — likely the direct-call + lightweight adapter bundle (cohort + posture + priming + cascade_tier per §12 W.1) since those have no QUESTION-and-stop blockers. W.2 (journey wrapper) and W.3 (archetype + maximizer build) need Q23 + Q24 adjudication before shipping. **W.4 (mindstate) is gated by Q20** — Chris must adjudicate scope (extraction-only with defaults vs full session-telemetry layer build) before W.4 can ship. Awaits Claude Proper prompt incorporating Q20-Q24 adjudications + W.1 scope confirmation.

- **Hand-off pointer:** Branch `feature/hmt-dashboard` @ HEAD post-W.0 commit. **14 slices closed total** (12 implementation + 2 audits — S6.2.0 + W.0). Working tree carries this MEMORY.md update + the new audit memo + `docs/PLATFORM_INVENTORY_2026_05_07.md` still untracked from earlier sessions. Substrate-accessor wiring is the next core-path work; W.1 is the next implementation slice.

---

### Session 2026-05-07 — S6.2 cell-conditional creative-selection: predicate evaluator + cell_features aggregator + Path A integration landed; **S6 SUBSTRATE NOW OPERATIONAL**

**EVE Handoff:**

- **Executed:** S6.2 — cell-conditional creative-selection slice. Five components shipped: (1) `CellFeatureSet` frozen-dataclass schema with 18 fields covering all S6 substrate (cell tuple axes + B priming + C/D mindstate composites + E/F.2 cohort signals + A.2 maximizer Beta posterior + Q18-orthogonal cascade attentional posture) at `adam/cells/features.py`; (2) `CellFeaturesAggregator` class with dependency-injected accessors + per-source fail-soft defaults + `default_aggregator()` factory at `adam/cells/aggregator.py`; (3) `@cell_predicate` decorator + `_PREDICATE_REGISTRY` + `evaluate_predicates` evaluator with multiplicative boost / multiplicative dampen / additive-clipped diversity composition + `apply_cell_modulation` Path-A bridge at `adam/cells/evaluator.py`; (4) 6 seed predicates across 5 module files (`fomo_predicates`, `ownership_predicates`, `maximizer_predicates`, `persuasion_resistance_predicates`, `compensatory_predicates`) at `adam/cells/predicates/`; (5) Path A fail-soft integration block in `adam/api/stackadapt/bilateral_cascade.py` between line 2881 (existing posture × mechanism modulation end) and line 2883 (existing fluency floor start), parallel structural template to `apply_posture_modulation`. Test suite: **5,598 passing** (+62 net from S6.2: +99 cells/ tests minus 37 F.1 tests already counted; 0 regressions).

- **🔑 S6 SUBSTRATE NOW OPERATIONAL.** S6.2 is the **first bid-time consumer of the entire B/C/D/E/F.2 substrate stack** (the substrate-not-yet-consumed gap S6.2.0 audit identified is now closed at the framework level). 12 implementation slices total + 1 audit (A.0 + A.1.0 + A.1 + A.2.0 + A.2 + B + C + D + E + F.1 + F.2 + S6.2.0 + S6.2). Pilot path framework fully wired; substrate accessor wiring (live archetype / posture / journey / priming / mindstate accessors replacing default_aggregator's neutral defaults) is incremental future work — flag this in the "Important caveat" below.

- **Q16/Q17/Q18/Q19 adjudications baked in:**
  - **Q16=combined**: aggregator + evaluator + integration shipped together in one slice (the evaluator is meaningless without aggregator coordination).
  - **Q17=Path A only**: integrated into `bilateral_cascade.run_bilateral_cascade` (inference side); Path B (`TherapeuticTouch` adaptive loop) untouched. Path A and Path B continue meeting only at the Neo4j posterior layer.
  - **Q18=orthogonal (Pass C resolution)**: cascade's 4-class posture is `{blend_compatible, vigilance_activating, neutral, unknown}` from `categorize_posture` at `adam/intelligence/page_attentional_posture_substrate.py:101` — derived from `attentional_posture` float ∈ [−1, +1] (blend↔vigilance allocation) + confidence floor. Semantically ORTHOGONAL to the 5-class FIVE_CLASS_POSTURES (5-class = WHAT cognitive activity; 4-class = HOW MUCH attentional allocation in blend/vigilance mode). Both surfaced as separate `CellFeatureSet` fields (`posture` for 5-class, `cascade_attentional_posture: Optional[str]` for 4-class). Audit memo's `HIGH/MID/LOW/UNKNOWN` characterization was paraphrased — actual labels documented in EVE for future readers.
  - **Q19=α**: Python `@cell_predicate(name=...)` decorator with module-level `_PREDICATE_REGISTRY`. No DSL, no YAML, no parser. Authoring surface is code-reviewed Python.

- **Integration seam (a) BEFORE per audit §5 recommendation**: S6.2 modulator inserted at `adam/api/stackadapt/bilateral_cascade.py:2882` — between the posture × mechanism modulation block (ends 2881) and the hard fluency floor (starts 2883). Same fail-soft try/except template, lazy imports, modulates `result.mechanism_scores`, logs to `result.reasoning`. Ordering rationale: S6.2 sees the posture-modulated baseline; the fluency floor still drops LOW posture×mechanism compatibility AFTER S6.2's boosts (so predicates can't bypass eligibility filtering). Integration block test (`test_inserted_after_posture_modulation_block`) pins the ordering invariant.

- **Pilot interpretation pin: `creative_class` ↔ Cialdini mechanism IDs.** For pilot, the "class" identifier in `CreativeModulation.creative_class_boosts` / `creative_class_dampens` maps directly to Cialdini mechanism IDs (`scarcity`, `social_proof`, `authority`, `loss_aversion`, `reciprocity`, `commitment_consistency`, `liking`, `unity`, `anchoring`) — the granularity the bilateral cascade's `result.mechanism_scores` consumes downstream. `apply_cell_modulation` multiplies matching mechanism_scores by boosts/dampens; classes not in mechanism_scores are silently no-op. Post-pilot may introduce a creative-class layer atop mechanisms; until then this direct mapping keeps the integration thin and the predicates concrete. Pinned in `evaluator.py` module docstring.

- **Pre-flight findings:**
  - Pass A (F.1 cell taxonomy operational): cell_count == 2,880; canonical example "ANALYST_TC_INT_PROM_Q1" resolves correctly.
  - Pass B (F.2 cohort detection operational): `detect_compensatory_consumption_pattern` returns expected (True, 0.85) on canonical positive case.
  - Pass C (Q18 orthogonality determination): cascade 4-class is **orthogonal** to 5-class posture (different vocabulary, different semantic axis — see Q18 above). Proceed per CASE Orthogonal branch.
  - Pass D (substrate access paths): all 7 access paths confirmed (archetype via per_user_posterior_modulation, posture via posture_classifier, journey via to_conversion_stage, PagePrimingSignature surface, PageMindstateVector surface, get_cohort_compensatory_flag, A.2 maximizer prior). Aggregator uses dependency injection — production wiring deferred to follow-up slice; default_aggregator() ships with neutral-default accessors.
  - Pass E (test harness): mock-based tests/unit/ pattern from F.2 reused; cells/ tests use `SimpleNamespace` + dependency-injected accessors for aggregator tests, no Neo4j/Redis.

- **Verified:**
  - Smoke-test 5-pattern verification: 6 seed predicates registered ✅; high_fomo_promotion fires on positive case + boosts scarcity 1.5× ✅; neutral feature set fires nothing → is_neutral=True ✅; apply_cell_modulation multiplies matching mechanisms (0.6 × 1.5 = 0.9; 0.4 × 0.7 = 0.28); unrelated mechanism untouched ✅; default_aggregator round-trip → cell_id "PRAGMATIST_IF_UNA_NEUT_Q4" ✅.
  - Schema tests (4): default construction, full construction, frozen invariant, Q18-orthogonality field separation.
  - Aggregator tests (15): happy path with all fields populated; cascade_tier optional; enable_timing populates ISO timestamp; **9 fail-soft tests** (one per substrate accessor + the all-failing case); 2 PagePrimingSignature confidence-extraction tests (direct attribute + dict pattern); p99 latency < 8ms over 10,000 random aggregations; default_aggregator factory round-trip.
  - Evaluator tests (16): `@cell_predicate` registers; duplicate name raises at decoration; `get_registered_predicates` returns names; empty-registry yields neutral; single predicate fires; multiplicative boost composition (1.5 × 1.3 = 1.95); multiplicative dampen composition (0.7 × 0.9 = 0.63); additive diversity clipped to [-1, +1] both ceiling and floor; predicate returning None skipped; predicate exception fail-soft (other predicates continue); `is_neutral` property; `apply_cell_modulation` neutral-pass-through, boost, dampen, unknown-mechanism-ignored; full-registry p99 < 5ms over 10,000 random feature sets.
  - Predicate tests (15): each of 6 seed predicates has positive case + 1-3 negative cases (no-fire conditions).
  - Integration tests (7): block presence in cascade source; lazy imports of `apply_cell_modulation` / `default_aggregator` / `evaluate_predicates`; fail-soft try/except template; `is_neutral` guard; **ordering invariant pin (S6.2 sits between posture × mechanism modulation and hard fluency floor)**; default_aggregator → evaluator → apply round-trip on neutral substrate (no fire); positive case (high FOMO + promotion) round-trip pins scarcity 0.6 × 1.5 = 0.9 and reciprocity 0.4 × 0.7 = 0.28.
  - Full pytest suite: 5,598 passed / 9 pre-existing failures unchanged (TestCampaignDocs ×8 + test_dag_has_14_atoms ×1) / 5 skipped. **Zero regressions on any unrelated surface.**

- **⚠️ Important caveat — substrate accessor wiring still pending.** The integration block uses `default_aggregator()` which returns NEUTRAL defaults for all substrate signals. Until follow-up slices wire real accessors (per_user_posterior_modulation for archetype; posture_classifier for posture; journey state machine for ConversionStage; priming Feature Store for PagePrimingSignature; mindstate cache for PageMindstateVector; A.2 maximizer prior accessor; F.2 graph_cache.get_cohort_compensatory_flag — only this last one is trivially wirable from the cascade's existing scope), the seed predicates rarely fire on real bid data. **The framework is operational; the substrate-accessor pilot wiring is incremental future work.** This is honest pre-pilot ship — predicates exist, integration is wired, fail-soft pattern guarantees no operational regression. Once accessors are wired, predicates start firing and modulation becomes live.

- **Architectural decision history closed:** A→F.2 built the substrate (signals + cell taxonomy + cohort detection); S6.2.0 audited the consumer surface; S6.2 ships the consumer (aggregator + evaluator + Path A integration). The substrate-without-consumer pattern that v3.1 directive's anti-drift discipline exists to prevent has been closed at the framework level.

- **Expected next:** Either (a) **Substrate-accessor wiring** — replace `default_aggregator()` in the cascade integration block with a production `cascade_aggregator()` that wires real accessors. Predicate fire rate increases; pilot path becomes live in the substantive sense. Likely 1-3 slices depending on whether accessors are wired all-at-once or incrementally per substrate signal. Or (b) **D.bis** (canonical EMOTION_KEYWORDS / MECHANISM_KEYWORDS extension + signature_version V2→V3 + 2 deferred mindstate derivations: loneliness_compensatory_flag + parasocial_priming_score — restores cohort-level/mindstate-level compensatory signal symmetry; complements existing predicates). Or (c) **Pilot launch + iteration loop**. All legitimate next moves; Chris adjudicates. The S6 framework is shipped and operational at the integration level.

- **Hand-off pointer:** Branch `feature/hmt-dashboard` @ HEAD post-S6.2 commit. **13 slices closed total** (12 implementation + 1 audit). Working tree carries this MEMORY.md update + `docs/PLATFORM_INVENTORY_2026_05_07.md` still untracked from earlier sessions. Pilot path framework fully wired; substrate accessor wiring is the next incremental work.

---

### Session 2026-05-07 — S6.2.0 retargeting orchestrator creative-selection audit landed (read-only memo)

**EVE Handoff:**

- **Executed:** S6.2.0 read-only audit. Six-pass inspection of `adam/retargeting/` orchestrator surface producing tracked memo at `docs/audits/RETARGETING_ORCHESTRATOR_CREATIVE_SELECTION_AUDIT.md` (~4,013 words / 407 lines / 14 sections: 9 numbered §-sections + 5 sub-headings under §8). Audit-then-implement pattern matching A.1.0 + A.2.0 precedents (commits c237e4b + 9a2fc84). Zero code changes; zero test changes; the memo is the entire deliverable.

- **Recommended integration seam: (a) BEFORE.** Per audit §5: insert as a new fail-soft modulator inside `run_bilateral_cascade` at `bilateral_cascade.py` ~line 2870, parallel to the existing `apply_posture_modulation` (which is the structural template). Minimizes coupling; matches an established pattern; preserves the existing creative-selection logic downstream.

- **4 QUESTION-and-stop concerns surfaced for Claude Proper adjudication before S6.2 ships:**
  - **Q16 — substrate-not-yet-consumed scope.** S6.2 is not just a predicate evaluator — it is the **first consumer of the entire B/C/D/E/F.2 substrate stack at bid time**. Verified by grep: zero bid-time consumers of `PageMindstateVector.fomo_score | psych_ownership_proxy | depletion_proxy`, `PagePrimingSignature.persuasion_knowledge_activation`, `UserCohort.compensatory_consumption_pattern`, `get_cohort_compensatory_flag`, OR `PagePrimingSignature` itself anywhere in `adam/api/`, `adam/intelligence/bid_composer.py`, `adam/intelligence/kelly_bid_sizing.py`, or `adam/retargeting/`. Two adjudication options: (i) S6.2 owns substrate-fetch coordination via a new `cell_features` aggregator AND the predicate evaluator (single combined slice); (ii) split S6.2 into S6.2a substrate-fetch + S6.2b predicate-evaluator slices. Audit recommends (i) for cohesion; Chris adjudicates.
  - **Q17 — parallel-path reconciliation.** `TherapeuticTouch` does NOT flow into `adam/api/stackadapt/`. Path A (bid-time bilateral_cascade) and Path B (post-non-conversion adaptive therapeutic loop) run in parallel and meet only via Neo4j-persisted posteriors. S6.2 lives on Path A; how (and whether) the predicate evaluator interacts with Path B's TherapeuticTouch sequence selection needs explicit decision before scope freeze.
  - **Q18 — posture cardinality mismatch.** F.1 cells use 5-class `FIVE_CLASS_POSTURES` (INFORMATION_FORAGING / TASK_COMPLETION / LEISURE_BROWSING / SOCIAL_CONSUMPTION / TRANSACTIONAL_COMPARISON). The bid-time cascade reads a 4-class HIGH/MID/LOW/UNKNOWN posture vocabulary in `apply_posture_modulation`. Either S6.2 maps between them at the seam, or the cascade adopts the 5-class vocabulary for cell-conditional paths. Surface for Claude Proper because it affects whether the cell tuple constructor's existing `posture` axis can be fed directly from the cascade's current posture signal.
  - **Q19 — predicate authoring surface.** Python decorator-based predicates (programmer-authored, code-reviewed) vs YAML/JSON DSL (analyst-authored, hot-reloadable) vs hybrid. Affects who owns predicate evolution post-pilot and how predicates are versioned alongside cell taxonomy.

- **Other key audit findings:**
  - Decision boundary call graph mapped (§2): bid-time entry → bilateral_cascade.run_bilateral_cascade → mechanism_scores → bid response. The "creative selection" function in the orchestrator turns out to be mechanism + bid composition, not a discrete creative-id picker — clarifies what S6.2 is actually conditioning.
  - Current-selector input inventory (§3): selector consumes archetype, posture (4-class), mechanism_effectiveness from cohort priors, mechanism_scores from cascade L1-L3 — but NONE of B/C/D/E/F.2's substrate. This is the substrate-not-yet-consumed finding that drives Q16.
  - Downstream consumers + output contract (§4): mechanism_scores dict flows into bid composer + Kelly bid sizing + decision-trace emitter. S6.2's output must remain `Dict[str, float]`-shape-compatible to plug in at the BEFORE seam without contract changes.
  - Test surface (§6): regression invariants in `tests/unit/test_bilateral_cascade.py` and `tests/unit/test_cohort_modulation.py` pin specific input-output behavior the BEFORE-seam integration must preserve.
  - Latency budget (§7): current retargeting selector consumes well under 25ms; S6.2 has substantial headroom in the same slot for predicate evaluation. F.1 (4μs) + F.2 (<1ms) leave room for ~15ms+ of predicate work before encroaching on adjacent slots.

- **Verified:**
  - Memo present at expected path (`docs/audits/RETARGETING_ORCHESTRATOR_CREATIVE_SELECTION_AUDIT.md`); 4,013 words; all 9 numbered §-sections present.
  - Zero tracked files modified by audit fork (only the new untracked memo file in working tree).
  - Zero code changes; zero test changes; pytest count unchanged at 5,535 passing.
  - Claims in memo cite `path:line` references throughout, per audit discipline rule.

- **Architectural decision history note:** This is the first audit slice since A.2.0 (commit `9a2fc84`) used the audit-first pattern. The substrate-not-yet-consumed finding (Q16) is exactly the kind of structural insight the audit-first discipline is meant to surface — building S6.2 against an assumed substrate pipeline that doesn't actually exist would have been a substantial waste. The discipline paid for itself in this slice.

- **Expected next: S6.2 predicate evaluator implementation.** Awaits Claude Proper prompt incorporating audit findings — specifically: (1) confirmed BEFORE-seam choice from §5 (audit-recommended); (2) Q16 split-vs-combined adjudication (audit-recommended: combined `cell_features` aggregator + predicate evaluator); (3) Q17 Path A / Path B interaction explicit decision; (4) Q18 posture-cardinality mapping decision; (5) Q19 predicate-authoring-surface decision. After S6.2 lands, the substrate built across A→F.2 will FINALLY be consumed at bid time — closing the substrate-without-consumer gap the v3.1 directive's anti-drift discipline exists to prevent.

- **Hand-off pointer:** Branch `feature/hmt-dashboard` @ HEAD post-S6.2.0 commit. **12 slices closed total** (11 substrate + 1 audit). Working tree carries this MEMORY.md update + the new audit memo + `docs/PLATFORM_INVENTORY_2026_05_07.md` still untracked from earlier sessions. Pilot path remains fully unblocked; S6.2 is the next core-path slice.

---

### Session 2026-05-07 — F.2 / S6.1 (2 of 2) — compensatory_consumption_pattern detection + bid-time accessor landed; **S6 KEYSTONE CLOSED**

**EVE Handoff:**

- **Executed:** F.2 / S6.1 (2 of 2 — cohort-side; closes S6 keystone) — `detect_compensatory_consumption_pattern` two-criterion heuristic detection function in `adam/intelligence/cohort_discovery.py` + 5 module-level constants (COMPENSATORY_MECHANISM_INDICATORS, COMPENSATORY_TRANSACTIONAL_NEGATIVES, COMPENSATORY_AFFILIATIVE_DOMINANCE_THRESHOLD=0.50, COMPENSATORY_TRANSACTIONAL_WEAKNESS_THRESHOLD=0.40, COMPENSATORY_MIN_COHORT_SIZE_FOR_HIGH_CONFIDENCE=200) + integration into `discover_cohorts` and `_get_default_cohorts` pipelines + `persist_cohort_assignments` cypher write extended to persist E's two new fields + `get_cohort_compensatory_flag(buyer_id) -> tuple[bool, float]` sibling accessor in `adam/api/stackadapt/graph_cache.py` with parallel TTL cache (30 min) mirroring `get_cohort_priors` pattern + 33 new tests across 2 files (`tests/unit/test_compensatory_detection.py` + `tests/unit/test_graph_cache_cohort_compensatory.py`) + 1 stale-test update (E's `test_default_cohort_pipeline_produces_safe_defaults` renamed to `test_default_cohort_pipeline_populates_new_fields` — F.2 wires detection into the default-cohort path per spec, so the pre-F.2 "always (False, 0.5)" assertion legitimately evolved to "valid type + range" invariants). Test suite: **5,535 passing** (+32 net from F.2: +33 new − 0 regressions; the 1 stale E test was an in-slice schema-evolution update, not a regression).

- **🔑 S6 KEYSTONE CLOSED.** 11 slices total (A.0 + A.1.0 + A.1 + A.2.0 + A.2 + B + C + D + E + F.1 + F.2). All preparation slices and the keystone closed. **Pilot path fully unblocked.**

- **Q14.B=(β) baked in:** Sibling accessor `get_cohort_compensatory_flag` (NOT extending `get_cohort_priors` return type, NOT encoding flag in mechanism_effectiveness_json blob). Clean separation between mechanism-effectiveness scalars (`Dict[str, float]`) and cohort-level boolean flag (`tuple[bool, float]`). Existing `get_cohort_priors` callers continue working unchanged. New cache `self._cohort_compensatory_flags` parallels `self._cohort_priors` with the same 30-min TTL.

- **Pass A finding (cypher extension required):** `persist_cohort_assignments` cypher writes only specific UserCohort fields via SET enumeration. F.2 extended both the metadata-payload comprehension AND the `cohort_query` SET clause to include `compensatory_consumption_pattern` and `compensatory_detection_confidence`. Cypher write extension is part of F.2's scope per the spec ("F.2 must extend the cypher write to persist the new fields"). Backward-compat: pre-F.2 cohort nodes lacking these properties read as None at the bid-time accessor → return (False, 0.50) neutral default via the explicit `isinstance(raw_flag, bool)` / `isinstance(raw_conf, (int, float))` guards.

- **Pass B finding:** Cialdini mechanism IDs in `adam/intelligence/mechanism_vocab.py:152-165` match spec exactly — social_proof, liking, unity (affiliative — COMPENSATORY_MECHANISM_INDICATORS); anchoring, scarcity, loss_aversion (transactional negatives); plus authority, reciprocity, commitment, curiosity for the broader vocabulary.

- **Pass C finding:** `get_cohort_priors` at `graph_cache.py:996` confirmed unchanged from Q13. F.2 added the parallel `get_cohort_compensatory_flag` method without touching the existing accessor.

- **Pass D finding:** F.1 cell taxonomy substrate operational (2,880 cells loaded; canonical example "ANALYST_TC_INT_PROM_Q1" resolves correctly). F.2 doesn't touch `adam/cells/`.

- **Verified:**
  - Smoke-test 9-pattern detection verification: empty mechanisms → (False, 0.50) ✅; pure affiliative + low transactional + size 300 → (True, 0.85) ✅; same with size 100 (undersample) → (True, 0.65) ✅; affiliative-only → (False, 0.65) ✅; transactional-weak only → (False, 0.65) ✅; neither criterion → (False, 0.50) ✅; missing transactional mechanism defaults to 0.5 → (True, 0.85) ✅; determinism (same input twice) ✅; default-cohort populated values consistent with direct function call ✅.
  - Smoke-test 4-pattern accessor verification: empty buyer_id → (False, 0.50) ✅; no driver → (False, 0.50) ✅; driver returns flag → (True, 0.85) ✅; pre-F.2 None fields → (False, 0.50) backward-compat ✅.
  - Detection logic (Tests 1-9): all six two-criterion combinations + missing-mechanism handling + determinism + heuristic caveat docstring pin.
  - Boundary semantics (Test 7 ×4 sub-cases): exactly-at-threshold behavior pinned for each of three thresholds (`>=` for affiliative, strict `<` for transactional, `>=` for size).
  - Constants tunability (Test 17): all 5 module-level constants pinned at spec defaults.
  - Pipeline integration (Tests 10-11 in default-cohort variant + payload variant): default cohorts populate new fields after detection runs; `persist_cohort_assignments` source contains both `uc.compensatory_consumption_pattern = c.compensatory_consumption_pattern` and `uc.compensatory_detection_confidence = c.compensatory_detection_confidence` SET clauses.
  - Bid-time accessor (Tests 12-15): returns flag for known buyer; returns neutral default for empty / no-driver / pre-F.2-None cases; cache TTL respected (cache-hit path doesn't touch driver; expired entry triggers re-query); p99 latency on cached path < 1ms over 10,000 calls.
  - Cache coherence (Test 16): `get_cohort_priors` cache and `get_cohort_compensatory_flags` cache are independent dicts on the same buyer_id key — pin for Q14.B=(β) sibling-accessor design.
  - Zero-regression on F.1 (Test 19): cell taxonomy + canonical example "ANALYST_TC_INT_PROM_Q1" still resolves; CELL_TAXONOMY count == 2,880.
  - Zero-regression on existing `get_cohort_priors` (Test 18): signature `(self, buyer_id) -> Dict` unchanged; F.2 only ADDS the sibling accessor.
  - Heuristic caveat docstring pinned (Test 20): "HEURISTIC SUBSTRATE" + "not load-bearing" + "Cialdini" all present in detect function docstring; future readers cannot promote to load-bearing without breaking the test.
  - 1 stale E test updated (`test_default_cohort_pipeline_produces_safe_defaults` → `test_default_cohort_pipeline_populates_new_fields`): pre-F.2 asserted always-defaults; post-F.2 asserts valid type + range invariants. Same schema-evolution pattern as B's V1→V2 update of test_signature.py.
  - Full pytest suite: 5,535 passed / 9 pre-existing failures unchanged (TestCampaignDocs ×8 + test_dag_has_14_atoms ×1) / 5 skipped — **zero regressions on any unrelated surface; the 1-test diff vs pre-F.2 baseline is the in-slice schema-evolution update, not a regression**.

- **Loneliness/Compensatory at COHORT level (§3 Block A #5) status: PARTIAL → COMPLETE.** Schema slot now populated by detection logic; bid-time access wired; persistence cypher extended. Together with C/D's mindstate-level FOMO + psych_ownership + depletion (and the deferred D.bis loneliness_compensatory_flag + parasocial_priming_score), the platform has the full cohort-prior + mindstate-level signal stack for compensatory consumption — minus the deferred D.bis vocabulary work which the keystone closure makes safe to ship next.

- **Architectural decision history closed:** A/B/C/D added side-channel substrate fields on existing structures (Page-Mindstate-Vector, Page-Priming-Signature, archetype priors). E added a cohort-level schema slot. F.1 shipped the static cell taxonomy + tuple constructor. F.2 shipped the cohort-side detection + bid-time accessor. The full S6 stack is now substrate-complete; S6.2 (predicate evaluator) consumes it.

- **Expected next:** Either (a) **D.bis** (canonical EMOTION_KEYWORDS / MECHANISM_KEYWORDS extension + signature_version V2→V3 + 2 deferred mindstate derivations: loneliness_compensatory_flag + parasocial_priming_score — restores the symmetry between cohort-level and mindstate-level compensatory signal stacks); or (b) **S6.2** (predicate evaluator that consumes B's persuasion_knowledge_activation, C+D's mindstate composites, E+F.2's cohort flag, and the F.1 cell taxonomy to drive cell-conditioned creative selection — the actual decision-time consumer that makes all of A/B/C/D/E/F substrate worth its bytes). Both legitimate next moves; Chris adjudicates sequencing.

- **Hand-off pointer:** Branch `feature/hmt-dashboard` @ HEAD post-F.2 commit. **11 slices closed total**; S6 keystone closed. Working tree carries this MEMORY.md update + `docs/PLATFORM_INVENTORY_2026_05_07.md` still untracked from earlier sessions. Pilot path fully unblocked.

---

### Session 2026-05-07 — F.1 / S6.1 (1 of 2) — cell taxonomy + tuple constructor landed (substrate-side keystone)

**EVE Handoff:**

- **Executed:** F.1 / S6.1 (1 of 2 — substrate-side) — `adam/cells/taxonomy.py` (5-axis static enumeration: 8 archetype × 5 posture × 6 conversion_stage × 3 regulatory_focus × 4 valence_arousal_quadrant = **2,880 cells**) + `adam/cells/constructor.py` (compute_valence_arousal_quadrant + construct_cell_id + get_cell_for_bid + parent-cell synthesis for pruning routing) + `adam/cells/__init__.py` (public API surface) + new test directory `tests/cells/` with `test_taxonomy.py` (16 tests covering enumeration, public accessors, frozen invariant, axis coverage, canonical example pin) + `test_constructor.py` (21 tests covering quadrant boundaries, construct_cell_id contract, get_cell_for_bid + parent routing, latency budget, full 2,880-cell coverage, zero-regression on A.2/B/C/D/E surfaces). Test suite: **5,503 passing** (+37 from F.1, exceeding the planned +20 with parametrize-style expansions of the 20 spec test cases).

- **Q15=(β) adjudication baked in:** Cell axis cardinality is **2,880, NOT the spec's original 1,920**, because the journey axis uses `ConversionStage` (6 values: UNAWARE / CURIOUS / EVALUATING / INTENDING / STALLED / CONVERTED) at `adam/retargeting/models/enums.py:21` rather than a 4-state Rubicon enum. Pre-flight Pass A.3 surfaced that the spec's "JourneyState (4 canonical values)" assumption doesn't match the codebase: actual `JourneyState` at `adam/user/journey/models.py:87` is a Pydantic BaseModel container; actual canonical journey enum is `JourneyStage` (13 values); established Enhancement-#33 collapsing maps to `ConversionStage` (6 values) via `to_conversion_stage` at `adam/user/journey/models.py:67`. Q15=(β) chose ConversionStage (6) over JourneyStage (13) and over inventing a new Rubicon-4 enum because: (a) already canonical in retargeting engine since Enhancement #33; (b) post-purchase JourneyStage values aren't distinct cell-conditional surfaces for ad selection; (c) avoids parallel-collapsing technical debt; (d) Heckhausen-Gollwitzer 1987 theoretical lineage cited in references but not re-implemented. Bid-time callers passing raw `JourneyStage` use `ConversionStage(to_conversion_stage(stage))` per the constructor docstring.

- **CRITICAL ARCHITECTURAL CONSTRAINT (per gap assessment §6 Step 1):** Cell axes are STATIC. B's `persuasion_knowledge_activation`, C+D's three composite states (`fomo_score`, `psych_ownership_proxy`, `depletion_proxy`), and E's `compensatory_consumption_pattern` are **features-on-cells**, NOT cell axes. They are predicate inputs that S6.2's rule-based classifier (a future slice) will use to select WITHIN-cell creative behavior. Adding them to the tuple axis would inflate the space to 2,880 × 3 × 3 × 3 × 3 × 2 = 466,560 cells, which fails the practicality bar.

- **Verified:**
  - Pre-flight Pass A: all 5 substrate access paths confirmed: ArchetypeID (8) at `adam/cold_start/models/enums.py:90`; FIVE_CLASS_POSTURES (5) at `adam/intelligence/posture_five_class.py:113`; ConversionStage (6) at `adam/retargeting/models/enums.py:21` per Q15=(β) instead of nonexistent JourneyState-4; PagePrimingSignature.regulatory_focus_priming (3) confirmed via prior B/C slices; valence + arousal already on PagePrimingSignature.
  - Pre-flight Pass B: graph_cache.get_cohort_priors path at `adam/api/stackadapt/graph_cache.py:996` unchanged from Q13 finding (F.2's domain; F.1 doesn't touch).
  - Pre-flight Pass C: 2,880 cells × ~120 bytes ≈ 350 KB at module import — trivially feasible.
  - Pre-flight Pass D: `cell_id` token exists in two unrelated namespaces (`adam/intelligence/simulation/sweep.py` simulation cells; `adam/pharmacovigilance/schema.py` signal cells); both use different ID formats and live in different modules — no functional collision in the new `adam/cells/` namespace.
  - Smoke-test 7-pattern verification: cell count == 2,880 ✅; canonical example "ANALYST_TC_INT_PROM_Q1" constructs from spec inputs ✅; round-trip get_cell_for_bid preserves all 5 axes ✅; quadrant boundary semantics correct for all 5 patterns (4 interiors + at-threshold ties downward) ✅; full 2,880-cell enumeration in 1.7ms total ✅; p99 latency 4μs over 10,000 random calls (target < 2,000μs — **500× under budget**) ✅; pruned-cell routing → "EXPLORER_IF_PARENT" ✅.
  - Taxonomy tests (16): cell count = 2,880 (Test 1); cell_ids unique (Test 2); every axis tuple appears exactly once (Test 3); cell_id format = 5 underscore-delimited parts (Test 4); all default is_active=True at import (Test 5); get_cell raises KeyError on unknown ID (Test 6); get_active_cells = full 2,880 frozen set (Test 7); get_parent_cell_id format pinned (Test 8); parent count = 40 = 8 × 5 (Test 9, EXPECTED_PARENT_CELL_COUNT); Cell frozen mutation rejected (Test 10); all 5 axis enums covered (Test 11 ×5).
  - Constructor tests (21): quadrant 5 boundary patterns + threshold constants pinned (Test 12 ×6); construct_cell_id round-trip canonical example (Test 13) + axis preservation (Test 14); full 2,880-tuple iteration without exception (Test 18); get_cell_for_bid returns Cell + matches axes (Test 15); pruned-cell parent routing with frozen-replace fixture (Tests 16 + 20 combined); p99 latency < 2ms over 10,000 random calls (Test 17); zero-regression pinned on 5 prior-slice surfaces — A.2 ArchetypeID enum, B PagePrimingSignature V2 dimensions, C+D PageMindstateVector composite states + DEPLETION_THRESHOLD_SECONDS, E UserCohort schema slot, G1.path4 FIVE_CLASS_POSTURES (Test 19 ×5).
  - Full pytest suite: 5,503 passed / 9 pre-existing failures unchanged (TestCampaignDocs ×8 + test_dag_has_14_atoms ×1) / 5 skipped — **zero regressions on any unrelated surface**.

- **Substrate consumption pattern established for downstream consumers** (S6.2 predicate evaluator, retargeting orchestrator, funnel_mpc creative selection): bid-time `get_cell_for_bid(archetype, posture, conversion_stage, regulatory_focus, valence, arousal) -> Cell` returns either an active cell or a synthesized parent cell. Parent cells synthesize lazily from the cell_id format `{archetype}_{posture}_PARENT` with neutral defaults on collapsed dimensions (UNAWARE / NEUTRAL / Q2_CONTENTED). Pruning is offline; bid-time evaluation is fast.

- **Architectural decision (continued from C/D/E):** Cell space remains STATIC at 2,880 — feature signals layer on top via S6.2 predicates rather than expanding the tuple. Same architectural pattern: B/C/D added side-channel substrate fields, E added a cohort-level slot, F.1 ships the cell space that S6.2 will conditionally evaluate against.

- **Expected next:** **F.2 / S6.1 (2 of 2)** — cohort detection logic populating E's deferred `compensatory_consumption_pattern` flag. Detection inputs: `UserCohort.dominant_mechanisms` + `mechanism_effectiveness` (per Q13 finding that the originally-spec'd three-criterion telemetry inputs don't exist as cohort-level aggregations; F.2 uses what `cohort_discovery` actually produces). Bid-time access shape: F.2 adjudicates between (a) extending `get_cohort_priors` return type, (b) adding sibling accessor `get_cohort_compensatory_flag`, or (c) encoding the flag/confidence in `mechanism_effectiveness_json` with reserved key. After F.2: D.bis (canonical EMOTION_KEYWORDS / MECHANISM_KEYWORDS extension + signature_version V2→V3 + 2 deferred mindstate derivations: loneliness_compensatory_flag + parasocial_priming_score). After D.bis: S6.2 predicate evaluator (the rule-based classifier that consumes B/C/D mindstate features + E/F.2 cohort flag against the F.1 cell space).

- **Hand-off pointer:** Branch `feature/hmt-dashboard` @ HEAD post-F.1 commit. Sessions A (5 slices) + B (1) + C (1) + D (1) + E (1) + F.1 (1) closed = **10 slices total**; S6.1 is half-closed (substrate-side keystone landed; cohort-side detection F.2 next). Working tree carries this MEMORY.md update + `docs/PLATFORM_INVENTORY_2026_05_07.md` still untracked from earlier.

---

### Session 2026-05-07 — E / S6-prep.4 — UserCohort compensatory_consumption_pattern schema slot landed (detection + wiring deferred to F)

**EVE Handoff:**

- **Executed:** E / S6-prep.4 — `compensatory_consumption_pattern: bool = False` + `compensatory_detection_confidence: float = 0.5` schema slot on `UserCohort` dataclass at `adam/intelligence/cohort_discovery.py:37`. Schema-only scope per Q13 adjudication (Q13.A=(β) schema-only + Q13.B=(δ) defer wiring to F). Two new `@dataclass` fields with safe defaults + docstring marker pinning F as the consumer + new test file `tests/unit/test_user_cohort_compensatory_schema.py` covering 9 unique tests (16 with parametrize expansions). Test suite: **5,466 passing** (+16 from E).

- **Q13 adjudication baked in:** Detection logic, offline-pipeline cypher write extension, AND bid-time access wiring (graph_cache.get_cohort_priors return-type extension OR new sibling accessor) ALL DEFERRED to F / S6.1 (the consumer slice — cells condition on the flag and dictate both the detection algorithm AND the access shape). Pre-flight surfaced that cohort discovery uses Louvain community detection over RESPONDS_TO mechanism edges (NOT HMM-over-behavior); per-session behavioral telemetry (posture / browsing_momentum / hour-of-day) is NOT currently aggregated to the cohort level; bid-time access via `graph_cache.get_cohort_priors` returns `Dict[str, float]` which doesn't accommodate booleans. Building speculative detection against a non-existent aggregation surface + speculative bid-time wiring against a contract F may need to redesign would be exactly the substrate-without-consumer pattern v3.1 discipline avoids.

- **Verified:**
  - Pre-flight Pass A: `UserCohort` `@dataclass` at `adam/intelligence/cohort_discovery.py:37` with 7 fields (cohort_id, size, sample_members, dominant_mechanisms, mechanism_effectiveness, psychological_centroid, discovered_at) — unchanged from Q13 finding.
  - Pre-flight Pass B: `compensatory_consumption` token absent from adam/, tests/, docs/ — no naming collision.
  - Pre-flight Pass C: `persist_cohort_assignments` (`adam/intelligence/cohort_discovery.py:474`) writes only `size` + `mechanism_effectiveness_json` to UserCohort node via explicit cypher field enumeration. There is no full UserCohort load-from-Neo4j function — cohorts reconstruct from `discover_cohorts` each run. Cypher write extension is part of F's deferred offline-pipeline work; until F lands, new fields silently drop on cypher persist BY DESIGN at the schema-only stage. Test scope adapted to in-memory `dataclasses.asdict()` round-trip — the canonical path that exists today.
  - Smoke-test 6-pattern verification: defaults applied (False, 0.5) ✅; explicit construction (True, 0.85) ✅; asdict produces correct keys ✅; **dict round-trip preserves new fields ✅; legacy dict (no new keys) deserializes with safe defaults ✅; `dataclasses.fields()` introspection confirms types + defaults ✅.
  - Schema acceptance + defaults (Tests 1-2): both fields construct correctly; defaults False / 0.5 applied.
  - In-memory round-trip (Tests 3-4): `dataclasses.asdict()` ↔ `UserCohort(**dict)` preserves new field values; legacy 7-field dict deserializes with safe defaults — backward-compat verified.
  - Range-invariant convention (Tests 5-6, parametrized): `[0, 1]` range exercised via 5 in-range cases; out-of-range values pass through (plain `@dataclass`, no validator — convention pinned, not enforcement).
  - Zero-regression (Tests 7-9): pre-E `UserCohort` 7-field construction unchanged; `_get_default_cohorts` fallback produces 3 cohorts each carrying new fields with safe defaults (existing pipeline not broken); singleton factory `get_cohort_discovery_service` still works.
  - Schema slot pinned (Tests 10-11): `dataclasses.fields()` introspection asserts `compensatory_consumption_pattern: bool = False` + `compensatory_detection_confidence: float = 0.5`; class source contains `S6-prep.4` + `F / S6.1` markers — F-consumer-revision surfaces explicitly via this test if defaults / types change.
  - Full pytest suite: 5,466 passed / 9 pre-existing failures unchanged (TestCampaignDocs ×8 + test_dag_has_14_atoms ×1) / 5 skipped — **zero regressions on any unrelated surface**.

- **Loneliness/Compensatory at COHORT level remains PARTIAL** until F's detection ships, but the **schema slot is ready** to receive F-populated values without further UserCohort dataclass changes. Together with C's mindstate-level FOMO + D's depletion + the deferred D.bis loneliness_compensatory_flag (post-keystone), the platform will eventually have both cohort-prior AND mindstate-level signals for compensatory consumption.

- **Architectural decision:** Schema-only at this stage avoids three speculative architectural commitments F should make: (1) detection algorithm choice (literature-grounded behavioral signature aggregation vs. existing-mechanism-effectiveness proxy); (2) cypher-write extension shape (separate property vs. extending mechanism_effectiveness_json blob); (3) bid-time access contract (extend `get_cohort_priors` return type vs. new sibling accessor vs. encode in JSON blob). F decides all three based on cell-conditioning requirements.

- **Expected next:** **F / S6.1 — cell taxonomy keystone. The destination.** All preparation slices closed (A.0 + A.1.0 + A.1 + A.2.0 + A.2 + B + C + D + E = 9 slices). S6 mandate per directive §3 S6 unblocked since G1.path4 closed at 57e43bf. F consumes: maximizer_tendency archetype Beta priors (A.2), persuasion_knowledge_activation page-priming field (B), 3 mindstate composite states (C+D: fomo_score, psych_ownership_proxy, depletion_proxy), and the compensatory_consumption_pattern cohort schema slot (E) — F decides detection + wiring for the cohort flag based on cell-conditioning requirements. **D.bis** (canonical EMOTION_KEYWORDS / MECHANISM_KEYWORDS extension + signature_version V2→V3 + 2 deferred mindstate derivations: loneliness_compensatory_flag + parasocial_priming_score) sequenced **post-keystone** per Q12 + Q13 adjudication (the keystone defines the final shape that vocabulary needs to support).

- **Hand-off pointer:** Branch `feature/hmt-dashboard` @ HEAD post-E commit. Sessions A (5 slices) + B (1) + C (1) + D (1) + E (1) closed = 9 preparation slices total. Working tree carries this MEMORY.md update + the prior-turn `docs/PLATFORM_INVENTORY_2026_05_07.md` still untracked. **F / S6.1 keystone next** — D.bis sequenced post-keystone.

---

### Session 2026-05-07 — D / S6-prep.3b — depletion_proxy composite state landed (D.bis deferred)

**EVE Handoff:**

- **Executed:** D / S6-prep.3b — `depletion_proxy` derived composite state on `PageMindstateVector`. 3 new orchestrator-populated dataclass fields (`session_position_seconds: float = 0.0`, `posture_class: str = ""`, `browsing_momentum: float = 0.5`) + 1 `@property` derivation (`depletion_proxy = cognitive_load × min(1.0, session_position_seconds / DEPLETION_THRESHOLD_SECONDS)`) + 1 module-level tunable constant (`DEPLETION_THRESHOLD_SECONDS = 1800.0` with explicit replication-crisis caveat block) + new test file `tests/retargeting/test_mindstate_composite_states_d.py` covering 17 unique tests (45 parametrize expansions for 59 total). Test suite: **5,450 passing** (+59 from D).

- **Q12.A=(γ) DEFERRED to D.bis:** `loneliness_compensatory_flag` and `parasocial_priming_score` derivations PUSHED. Pre-flight Pass C surfaced that emotion_loneliness, emotion_warmth, and creator_content frame are not present in the canonical EMOTION_KEYWORDS / MECHANISM_KEYWORDS dictionaries. Per "no canonical invention" discipline, derivations whose inputs would require new vocabulary cannot ship until the vocabulary lands. D.bis = canonical-vocabulary extension (EMOTION_KEYWORDS += loneliness, warmth; MECHANISM_KEYWORDS += creator_content) + signature_version bump V2 → V3 + the two deferred derivations.

- **Q12.B=✅ CASE B engaged:** `cognitive_velocity` lives in the decision-time atoms layer (`adam/atoms/core/`), NOT on the bid-time PageMindstateVector substrate. CASE A (load × velocity × position) is therefore unavailable on the bid-time substrate; CASE B (load × position) is the bid-time-substrate-correct formula. CASE A may supersede in a future slice when cognitive_velocity surfaces on bid-time substrate.

- **Verified:**
  - Pre-flight Pass A: C derivations still resolve correctly (smoke: fomo_score=0.96 promotion+scarcity+arousal0.8; psych_ownership_proxy=1.0 heavy-touch present-focus). C arithmetic preserved.
  - Pre-flight Pass B: `cognitive_load` already on PMV at line 73 (default 0.5); `session_position_seconds` was NOT — added as new field with default 0.0.
  - Pre-flight Pass C: `cognitive_velocity` confirmed atoms-layer-only (lives in decision-time aggregator, not bid-time substrate). CASE B engaged correctly.
  - Smoke-test 7-pattern verification: default→0.0 ✅; high-load early(300s)→0.1333 ✅; high-load threshold(1800s)→0.8 ✅; saturation beyond threshold→0.8 ✅; zero load→0.0 ✅; coexistence with C derivations (fomo=0.84/psych_own=0.5/depletion=0.3 same PMV) ✅; new field defaults verified ✅.
  - Bid-time latency: p99 < 1ms over 10,000 randomly-parameterized instances for ALL THREE derivations combined (in practice microseconds — cached-field arithmetic).
  - Three-way trait × state composability test: ANALYST × FOMO × HIGH-DEPLETION > ANALYST × FOMO × LOW-DEPLETION (matching FOMO inputs; only depletion differs) — pins multiplicative composition across trait + 2 states.
  - Replication-crisis caveat pinned in test (`test_replication_crisis_caveat_pinned_in_docstring`): docstring must contain "REPLICATION-CRISIS CAVEAT" + reference to Hagger 2016 RRR / Carter & McCullough 2014. Future readers cannot promote depletion_proxy to load-bearing without breaking this test.
  - Zero-regression: pre-D `PageMindstateVector` fields untouched; `to_numpy()` 32-dim projection unchanged (new fields are side-channel derivation inputs only); pre-D PMV construction defaults preserved.
  - Full pytest suite: 5,450 passed / 9 pre-existing failures unchanged (TestCampaignDocs ×8 + test_dag_has_14_atoms ×1) / 5 skipped — **zero regressions on any unrelated surface**.

- **One PARTIALLY-COVERED gap from gap assessment §3 Block H now CLOSED (with explicit replication caveat):** Self-control depletion operational signature now surfaceable on bid-time substrate. Substrate is intentionally a HEURISTIC PROXY, not a load-bearing academic claim — caveat docstring + caveat test both pin this discipline.

- **Tunable calibration constant:** `DEPLETION_THRESHOLD_SECONDS = 1800.0` (30 minutes). Calibration choice informed by session-engagement research; pilot data through `per_user_posterior_modulation` will tighten.

- **Architectural decision (continued from C):** new fields are side-channel derivation inputs — NOT part of the 32-dim resonance vector. `to_numpy()` projection unchanged across A/B/C/D series.

- **Expected next:** Either (a) Session D.bis — canonical-vocabulary extension (loneliness, warmth, creator_content) + signature_version V2→V3 + loneliness_compensatory_flag + parasocial_priming_score derivations; or (b) Session E / S6-prep.4 — cohort emission flag (`compensatory_consumption_pattern`); or (c) Session F / S6.1 — cell taxonomy keystone. Sequence per Claude Proper.

- **Hand-off pointer:** Branch `feature/hmt-dashboard` @ HEAD post-D commit. Sessions A (5 slices) + B (1) + C (1) + D (1) closed. Working tree carries this MEMORY.md update + the prior-turn `docs/PLATFORM_INVENTORY_2026_05_07.md` still untracked. D.bis/E/F/G await Claude Proper prompts in sequence.

---

### Session 2026-05-07 — C / S6-prep.3a — fomo_score + psych_ownership_proxy composite states landed

**EVE Handoff:**

- **Executed:** C / S6-prep.3a — `fomo_score` + `psych_ownership_proxy` derived composite states on `PageMindstateVector` (commit `fd1a95a`). 4 new dataclass fields populated from PagePrimingSignature + retargeting state at orchestrator input-assembly time (`scarcity_frame_present`, `regulatory_focus_priming`, `touch_count`, `dwell_seconds`) + 2 `@property` derivations + 5 module-level tunable constants + 173 tests (including parametrized fuzz: 30 FOMO × 125 ownership combinations covering full input space). Test suite: **5,391 passing** (+173 from C).

- **Verified:**
  - Pre-flight Pass A: class is `PageMindstateVector` (not `MindstateVector`) at `adam/retargeting/resonance/models.py:55`; plain `@dataclass` → used `@property` (not Pydantic computed_field).
  - Pre-flight Pass B: inputs cached + accessible (`emotional_arousal` as field; `temporal_horizon` via `ndf_activations` dict; `regulatory_focus_priming`/`scarcity_frame_present`/`touch_count`/`dwell_seconds` added as new fields per slice spec adaptation).
  - Pre-flight Pass C: canonical scarcity name is `"scarcity"` per `MECHANISM_KEYWORDS` (`adam/platform/intelligence/content_profiler.py:35`) and `_PREVENTION_MECHS` frozenset (`adam/priming/pipeline.py:148`); `activated_frames` populated from `mechanisms[:5]` per `pipeline.py:227`. `FOMO_SCARCITY_FRAME_NAME = "scarcity"`.
  - Pre-flight Pass D: `touch_count` + `dwell_seconds` widely used in `adam/retargeting/engines/` but NOT centralized; per slice spec, added as new fields with safe defaults — orchestrator populates at input assembly.
  - Smoke-test 7-pattern verification: default 0.0 ✅; promotion+scarcity+arousal=0.8 → 0.96 ✅; prevention same arousal → 0.64 (< promotion) ✅; clipping at 1.0 ✅; heavy-touch present-focus → 1.0 ✅; future-focus 5× degradation → 0.2 ✅; cold-start → 0.0 ✅.
  - Bid-time latency: p99 < 1ms over 10,000 randomly-parameterized instances (both derivations together; in practice microseconds — cached-field arithmetic).
  - Trait × state composability test: ANALYST × promotion-amplified FOMO > ANALYST × neutral FOMO — pins multiplicative architecture.
  - Zero-regression: pre-C `PageMindstateVector` fields untouched; `to_numpy()` 32-dim projection unchanged (new fields are side-channel derivation inputs only).
  - Full pytest suite: 5,391 passed / 9 pre-existing failures unchanged / 5 skipped — **zero regressions**.

- **Two PARTIALLY-COVERED gaps from gap assessment now CLOSED:**
  - §3 Block A #6 (FOMO) — Cialdini scarcity + Pham-Higgins regulatory-fit + Przybylski FOMO grounding via `fomo_score = arousal × scarcity_indicator × regulatory_focus_modifier`
  - §3 Block I #33 (Psychological Ownership) — Pierce-Kostova-Dirks ownership + Kahneman-Knetsch-Thaler endowment grounding via `psych_ownership_proxy = touch_density × dwell_normalized × presentness`

- **Tunable constants surfaced as the calibration interface:**
  - `FOMO_REGULATORY_PROMOTION_MODIFIER = 1.2`, `FOMO_REGULATORY_PREVENTION_MODIFIER = 0.8`, `FOMO_REGULATORY_NEUTRAL_MODIFIER = 1.0`
  - `FOMO_SCARCITY_FRAME_NAME = "scarcity"`
  - `PSYCH_OWNERSHIP_DECAY_WINDOW_DAYS = 7.0`, `PSYCH_OWNERSHIP_TARGET_DWELL_SECONDS = 60.0`
  All calibration choices informed by literature but NOT load-bearing citations; pilot data through `per_user_posterior_modulation` will tighten them.

- **Architectural decision:** new fields are side-channel derivation inputs — NOT part of the 32-dim resonance vector. `to_numpy()` projection unchanged; new fields populate from orchestrator input assembly when bid-time derivations are needed.

- **Expected next:** Session D / S6-prep.3b — `depletion_proxy` + `loneliness_compensatory_flag` + `parasocial_priming_score` derived composite states (3 more derivations, same pattern). Awaits Claude Proper prompt with derivation specs.

- **Hand-off pointer:** Branch `feature/hmt-dashboard` @ `fd1a95a`. Sessions A (5 slices) + B (1) + C (1) closed. Working tree carries this MEMORY.md update + the prior-turn `docs/PLATFORM_INVENTORY_2026_05_07.md` still untracked. D/E/F await Claude Proper prompts in sequence.

---

### Session 2026-05-07 — B / S6-prep.2 — persuasion_knowledge_activation page-side dimension landed

**EVE Handoff:**

- **Executed:** B / S6-prep.2 add `persuasion_knowledge_activation` field to `PagePrimingSignature` (commit `831e49a`). Schema extension V1 → V2 (1 new field + range invariant + serialization round-trip + neutral_signature update + SIGNATURE_DIMENSIONS tuple grows 5→6) + heuristic extractor `compute_persuasion_knowledge_activation` in `content_profiler.py` with 3 cue families (explicit disclosure markers ×14, salesy diction ×14, aggressive persuasion language density-normalized) + `ContentProfiler.profile()` output emits `"persuasion_knowledge": {"activation", "confidence"}` block + `map_profile_to_signature` mapper integration with backward-compat default (0.0, 0.5) when block absent + 30 new tests. Test suite: **5,218 passing** (+30 from B).

- **Verified:**
  - Pre-flight Pass A: PagePrimingSignature located at `adam/priming/signature.py:58` (frozen dataclass, NOT Pydantic v2; uses `confidence_per_dimension` dict pattern → followed dict pattern).
  - Pre-flight Pass B: `content_profiler.py` ContentProfiler.profile() returns dict with `ndf_profile/segments/constructs/mechanisms/confidence/emotions`; mapper at `adam/priming/pipeline.py:192:map_profile_to_signature` consumes that dict.
  - Pre-flight Pass C: Feature Store cascade serialization backward-compat verified — `from_feature_store_row` defaults missing field to 0.0; legacy v1 entries preserve their v1 version string.
  - Pre-flight Pass D: `persuasion_knowledge` IS already used in `adam/atoms/core/{autonomy_reactance.py, strategic_awareness.py}` as a USER-STATE dict key (decision-time tracking), NOT a page-side dataclass field. Different namespace; no naming collision with new `persuasion_knowledge_activation` page-side field. Atom-side construct and page-side construct are conceptually related (both track persuasion-knowledge activation) but architecturally separate (atom-side is per-user state at decision time; page-side is per-URL static feature in priming cascade).
  - Smoke-test results: paid-promo (1 #ad cue) → score=0.300, conf=0.85 ✅; editorial → score=0.000, conf=0.50 ✅; 3-disclosure-marker → score=0.600 (capped at family limit 0.60), conf=0.85 ✅; salesy → score=0.500, conf=0.65 ✅.
  - Backward-compat (Test 4): legacy v1 cached row deserializes with `persuasion_knowledge_activation=0.0` and `signature_version="page_priming_v1"` preserved.
  - Cascade round-trip (Test 11): `PagePrimingSignatureStore` L2 path preserves new field correctly.
  - Pipeline integration (Test 13): profile dict with `persuasion_knowledge` block flows end-to-end; mapper defaults (0.0, 0.5) when block absent.
  - Zero-regression (Test 14): all pre-A.2 fields retain values; new field takes default; neutral_signature includes new field at floor.
  - 3 schema-evolution updates in `tests/priming/test_signature.py` (test_minimal_construction, test_signature_dimensions_pinned, test_neutral_signature_carries_canonical_version) — legitimate shape pins that the V1→V2 schema upgrade invalidated; updated to pin V2 / new dimension list. NOT zero-regression failures (these are intended pins of the schema constants, which legitimately evolved).
  - Full pytest suite: 5,218 passed / 9 pre-existing failures unchanged (TestCampaignDocs ×8 + test_dag_has_14_atoms ×1) / 5 skipped — **zero regressions on any unrelated surface**.

- **Heuristic extractor calibration** (compute_persuasion_knowledge_activation):
  - Family 1 (explicit disclosure markers, 14 cues): each → +0.30; family capped 0.60
  - Family 2 (salesy diction, 14 cues): each → +0.10; family capped 0.30
  - Family 3 (aggressive persuasion language): density per 100 words; saturates at 6.0/100 → 0.20 contribution
  - Confidence: 0.85 if explicit detected; 0.65 if salesy/aggressive ≥ 0.10; 0.50 otherwise
  - Calibration choices are heuristic informed by Friestad-Wright PKM but NOT load-bearing academic citations; pilot data may tighten weights via downstream slices.

- **Friestad-Wright PKM PARTIALLY-COVERED gap from gap assessment §3 Block F #25 is now CLOSED** — page-priming has a named dimension for ad-format-cue-driven persuasion-knowledge activation; required substrate input for S6.1 cell classifier cells conditioned on persuasion-resistance disposition.

- **Expected next:** Session C / S6-prep.3a — `fomo_score` + `psych_ownership_proxy` added to `mindstate_vector`. Awaits Claude Proper prompt with derivation specs (FOMO from arousal + scarcity_frame + regulatory_focus; psych_ownership from retargeting touch_count + dwell + temporal_horizon).

- **Hand-off pointer:** Branch `feature/hmt-dashboard` @ `831e49a`. Sessions A (5 slices) + B (1 slice) closed. Working tree carries this MEMORY.md update + the prior-turn `docs/PLATFORM_INVENTORY_2026_05_07.md` still untracked-pending. Sessions C/D/E/F await Claude Proper prompts in sequence.

---

### Session 2026-05-07 — A.2 maximizer_tendency Beta prior differentiation — keystone landed

**EVE Handoff:**

- **Executed:** A.2 maximizer_tendency Beta prior differentiation across 8 Jung archetypes via z-score derivation (commit `c090037`). New module `adam/cold_start/priors/maximizer_tendency.py` (162 lines) with pure derivation function `derive_maximizer_beta_priors(profiles) -> Dict[ArchetypeID, BetaDistribution]`, module-level registry `ARCHETYPE_MAXIMIZER_PRIORS` populated at import, accessor `get_maximizer_tendency_prior(archetype_id)`. Integration pattern parallels `ARCHETYPE_MECHANISM_PRIORS` (per-archetype Beta priors keyed by ArchetypeID, single-construct level). Updated `adam/cold_start/priors/__init__.py` to export the new surface. **+18 tests** all passing. Test suite **5,188 passing**.

- **Verified:**
  - Pre-flight Pass A: migration 032 slot AVAILABLE; migration 031 (A.1) confirmed present.
  - Pre-flight Pass B: audit-cited profile spot-checks all match (ANALYST C=0.80, NURTURER A=0.90, GUARDIAN N=0.65); audit values current at HEAD `9a2fc84`.
  - Pre-flight Pass C: cold_start prior surface located; integration pattern is `ARCHETYPE_MECHANISM_PRIORS` precedent (per-archetype Beta-prior registry); no Neo4j migration needed (Schwartz academic_grounding already in migration 031 from A.1; A.2 priors are Python-only at the cold_start engine layer).
  - Live derivation results: ANALYST highest (mean 0.6078), GUARDIAN second (0.5744), ACHIEVER third (0.5672); CREATOR/PRAGMATIST middle; EXPLORER/NURTURER/CONNECTOR low (NURTURER lower than audit-predicted "moderate" because high A=0.90 carries strong negative weight per Schwartz; academically defensible).
  - Differentiation max-min = **0.2169** (above 0.20 invariant floor).
  - Top-3 = {ANALYST, GUARDIAN, ACHIEVER} = the audit's expected_core set exactly (no swap needed).
  - Trait × state posterior update test (Test 9) passes: ANALYST + PRAGMATIST both move upward on 5 successes; PRAGMATIST's absolute Δ > ANALYST's (lower-prior posterior absorbs more evidence shift per identical observation count) — pins the multiplicative trait × state architecture.
  - Zero-regression on `ARCHETYPE_TRAIT_PROFILES`, `POPULATION_TRAIT_PRIORS`, `ARCHETYPE_MECHANISM_PRIORS` confirmed.
  - Full pytest suite: 5,188 passed / 9 pre-existing failures unchanged / 5 skipped — **zero regressions**.

- **Live derivation table** (per-archetype Beta priors for `maximizer_tendency`):

  | Archetype | α | β | mean = α/(α+β) | α+β |
  |---|---:|---:|---:|---:|
  | ANALYST | 6.0780 | 3.9220 | 0.6078 | 10.0 |
  | GUARDIAN | 5.7444 | 4.2556 | 0.5744 | 10.0 |
  | ACHIEVER | 5.6719 | 4.3281 | 0.5672 | 10.0 |
  | CREATOR | 4.9754 | 5.0246 | 0.4975 | 10.0 |
  | PRAGMATIST | 4.8190 | 5.1810 | 0.4819 | 10.0 |
  | EXPLORER | 4.5119 | 5.4881 | 0.4512 | 10.0 |
  | NURTURER | 4.2856 | 5.7144 | 0.4286 | 10.0 |
  | CONNECTOR | 3.9094 | 6.0906 | 0.3909 | 10.0 |

- **Q11 chain closed:** Q11.A (β engine-empirical reference) implemented as `ENGINE_EMPIRICAL_POPULATION` constants matching audit §6.1 within 1e-9. Q11.B (Schwartz weights {O: +0.20, C: +0.40, A: -0.20, N: +0.20}, E dropped) implemented as `SCHWARTZ_MAXIMIZER_WEIGHTS` with sum-of-absolute-values=1.0 invariant. Q11.C (n=10) implemented as `PRIOR_STRENGTH=10.0` invariant.

- **Maximizer/satisficer PARTIAL-COVERED gap from gap assessment §3 Block D #21 is now CLOSED.** Each cold-start user gets archetype-conditioned maximizer_tendency Beta prior at zero bid-time cost; subsequent bid observations update the posterior multiplicatively per the trait × state architecture demonstrated in Test 9.

- **Expected next:** Session B — S6-prep.2 page-side schema extension. Add `persuasion_knowledge_activation` field to `PagePrimingSignature`. Awaits Claude Proper prompt with field spec, range/default, mapper rule for `content_profiler.py`, and cascade integration policy.

- **Hand-off pointer:** Branch `feature/hmt-dashboard` @ `c090037`. A.0 + A.1.0 + A.1 + A.2.0 + A.2 closed. Session A complete (5 slices: gap-assessment doc + audit + consolidation refactor + profile audit + Beta prior differentiation). Session B awaits Claude Proper. Working tree carries this MEMORY.md update + the prior-turn `docs/PLATFORM_INVENTORY_2026_05_07.md` still untracked-pending.

---

### Session 2026-05-07 — A.2.0 audit-slice — cold_start archetype profiles & scale convention memo landed

**EVE Handoff:**

- **Executed:** A.2.0 cold_start archetype profiles audit (commit `9a2fc84`). Four-pass read-only inspection of `adam/cold_start/archetypes/definitions.py` + supporting type modules (`priors.py`, `archetypes.py`). Memo committed at `docs/audits/COLD_START_ARCHETYPE_PROFILES_AUDIT.md` (~3.3k words, 379 lines, 24 KB; §1 Executive Summary + §2 Pass 1 schema + §3 Pass 2 profile extraction + §4 Pass 3 scale convention + §5 Pass 4 anchoring + §6 Recommended A.2 derivation anchor + §7 Q11.A–C surfaced + §8 Closure). Zero code changes; zero test changes; **5,170 tests passing** unchanged.

- **Verified:** Memo present at expected path; all four passes documented; §6 recommended-anchor section completed with engine-empirical (μ, σ) per trait + Schwartz weight formula + predicted per-archetype Beta priors; §7 surfaced **3 QUESTION-and-stop concerns** (Q11.A reference population for z-score; Q11.B Schwartz trait-correlate weight formula; Q11.C Beta-prior pseudo-count strength); no other repo files modified; full pytest suite passes (5,170 passed / 9 pre-existing failures unchanged: TestCampaignDocs ×8 + test_dag_has_14_atoms ×1 / 5 skipped).

- **Three architectural findings surfaced for A.2's reference:**
  1. **Scale convention NORMALIZED_0_TO_1 is validator-enforced** by `Field(ge=0.0, le=1.0)` on `GaussianDistribution.mean` — not just empirical pattern. A.2's z-score derivation input domain is locked at the type level.
  2. **Profile anchoring is POPULATION-ANCHORED IN INTENT but with internal-engine convention shifted below literature.** Per-trait engine-empirical means fall 0.04–0.11 BELOW Chris's literature-rescaled reference across all five Big Five (e.g., C engine-avg 0.6313 vs literature-rescaled 0.74). Engine appears to use a 0.5-centered convention with archetype values expressed as deviations from 0.5, rather than against literature-rescaled Costa-McCrae norms. Direction of differentiation matches literature qualitatively (C/A elevated, N suppressed), but absolute scale differs.
  3. **Schema is clean for A.2 consumption:** all 8 archetypes have all 5 Big Five dimensions; standard 5-factor model (no NEO-PI-R facet decomposition); `GaussianDistribution` uses VARIANCE not STD (A.2 must use `computed_field .std` = `sqrt(variance)`); variance discipline binary (0.02 for defining traits, 0.03 for non-defining); trait names exactly match Big Five canonical.

- **Engine-empirical (μ, σ) per Big Five trait** (audit-recommended z-score reference per Q11.A=(β)):
  - O: μ=0.6250, σ=0.1604
  - C: μ=0.6313, σ=0.1607
  - E: μ=0.5563, σ=0.1675
  - A: μ=0.6188, σ=0.1416
  - N: μ=0.4313, σ=0.1130

- **Audit-suggested Schwartz trait-correlate weight formula** (Q11.B for Claude Proper): `maximizer_z = +0.20·z(O) + 0.40·z(C) + 0.05·z(E) − 0.15·z(A) + 0.40·z(N)`. Logistic-converted to μ_max ∈ (0, 1); α = μ_max·n, β = (1 − μ_max)·n with audit-suggested n=10 (Q11.C).

- **Predicted differentiation pattern** (illustrative, n=10): GUARDIAN highest maximizer prior (high N + high C + low O); ANALYST high (high C, deliberate); ACHIEVER moderate-high; CREATOR / NURTURER / PRAGMATIST moderate; EXPLORER / CONNECTOR low (low C + low N + high social orientation). Pattern is plausible per Schwartz literature.

- **Expected next:** A.2 maximizer_tendency Beta prior differentiation. Awaits Claude Proper prompt incorporating audit findings — specifically: (1) Q11.A reference population from §6 (audit recommends β engine empirical), (2) Q11.B Schwartz trait-correlate weight formula source + normalization, (3) Q11.C Beta-prior pseudo-count strength, (4) any further QUESTION-and-stop concerns from §7 that need adjudication. A.2 implementation should be a pure function `derive_maximizer_beta_priors(profiles) -> Dict[ArchetypeID, BetaDistribution]` per §6.5; tests pin per-archetype Beta priors against §6.4 illustrative table.

- **Hand-off pointer:** Branch `feature/hmt-dashboard` @ `9a2fc84`. A.0 + A.1.0 + A.1 + A.2.0 closed. A.2 awaits Claude Proper adjudication of Q11.A–C + execution prompt with locked decisions. Working tree carries this MEMORY.md update + the prior-turn `docs/PLATFORM_INVENTORY_2026_05_07.md` still untracked-pending.

---

### Session 2026-05-07 — A.1 consolidation refactor — maximizer_tendency canonical landed

**EVE Handoff:**

- **Executed:** A.1 consolidation refactor (commit `8a7ef23`). New migration `031_update_decision_style_dim.cypher` (28 lines, `MATCH…SET` pattern, Schwartz 2002 academic_grounding + scale anchors + provenance). Enum rename `MAXIMIZING_TENDENCY = "maximizing_tendency"` → `MAXIMIZER_TENDENCY = "maximizer_tendency"` (full unconditional per Pass A IN_MEMORY result). 6 file string-literal renames per audit §8.4 (19 hits of `"decision_maximizer"` → `"maximizer_tendency"`). New invariant-pinning test file with **17 tests**. Test suite **5,170 passing** (+17 from A.1).

- **Verified:**
  - Pre-flight Pass A persistence check: 1 hit total for `"maximizing_tendency"`, only at declaration site (no PERSISTED hits, no IN_MEMORY consumers); UNCONDITIONAL full rename authorized.
  - Pre-flight Pass B audit-citation freshness: all `§8.4` cited lines verified current at HEAD `c237e4b`.
  - Pre-flight Pass C migration slot: `031_*.cypher` slot confirmed available.
  - Post-rename: zero `"decision_maximizer"` string literals in `adam/.py` source (Test 1); zero `MAXIMIZING_TENDENCY` identifiers in `adam/.py` source (Test 2); 29 `maximizer_tendency` hits (7 pre-existing canonical + 22 newly-renamed); all 7 edited files syntax-clean (py_compile ✅).
  - Migration 031 statics: file present (Test 3); SET clause has expected new properties (Test 4); MATCH…SET pattern (Test 5); does NOT override any of migration 005's 11 preserved properties (Test 6 — parametrized over `full_name, domain, dimension_type, description, low_description, high_description, measurement_method, ad_relevance, population_mean, population_std, created_at`); cold_start enum has renamed identifier with renamed value (Test 7).
  - construct_taxonomy.py bipolar `dm_maximizer`/`dm_satisficer` split untouched per Q10.D. `empirical_psychology_framework.py` `"satisficing"`/`"maximizing"` categorical entries untouched per Q10.F. 683 categorical-bucket `decision_style` sites untouched per Q10.E. Already-canonical sites in `unified_psychological_intelligence.py` + `constructs/service.py` + `constructs/models.py` untouched (no churn). Migration 005 never amended per Q10.C.
  - Full pytest suite: 5,170 passed / 9 pre-existing failures unchanged / 5 skipped — **zero regressions**.

- **Static-analysis adaptation noted:** Tests 3–5 were specced as live-Neo4j-execution tests; no existing migration test harness in `tests/` (verified pre-commit). Adapted to static-analysis pattern (parse migration cypher text + assert content invariants). This pins migration correctness at file level without requiring live Neo4j; database-level idempotency is provided by the `MATCH…SET` pattern itself (verified in Test 5).

- **Expected next:** A.2 revised S6-prep.1 — 8 Jung-archetype Beta prior differentiation against the now-renamed `maximizer_tendency` PersonalityDimension. Awaits Claude Proper prompt with Beta priors mapped to the cold_start engine's actual 8 archetypes (`EXPLORER, ACHIEVER, CONNECTOR, GUARDIAN, ANALYST, CREATOR, NURTURER, PRAGMATIST`) per Q7.C=(α). The archetype-trait-profile schema in `adam/cold_start/archetypes/definitions.py` should provide the Big Five Gaussian distributions that anchor the Beta-prior mapping for `maximizer_tendency`.

- **Hand-off pointer:** Branch `feature/hmt-dashboard` @ `8a7ef23`. A.0 + A.1.0 + A.1 closed. A.2 awaits Claude Proper prompt. Working tree carries this MEMORY.md update + the prior-turn `docs/PLATFORM_INVENTORY_2026_05_07.md` still untracked-pending.

---

### Session 2026-05-07 — A.1.0 audit-slice — maximizer/satisficer fragmentation memo landed

**EVE Handoff:**

- **Executed:** A.1.0 audit-slice (commit `c237e4b`). Six-pass read-only inspection of maximizer/satisficer construct distribution across codebase. Memo committed at `docs/audits/MAXIMIZER_FRAGMENTATION_AUDIT.md` (~3.5k words, 426 lines, 30 KB; §1 Executive Summary + §2 Pass 1 Migration 005 schema + §3 Pass 2 ID cross-references + §4 Pass 3 named-variant cross-references + §5 Pass 4 test surface + §6 Pass 5 downstream migrations + §7 Pass 6 construct_taxonomy.py role + §8 Recommended A.1 Scope + §9 Audit closure). Created `docs/audits/` directory. Zero code changes; zero test changes; **5,153 tests passing** unchanged.

- **Verified:** Memo present at expected path; all six passes documented; §8 recommended-scope section completed with 7 adjudication points (Q10.A–G) for Claude Proper; no other repo files modified; full pytest suite passes (5,153 passed / 9 pre-existing failures unchanged: TestCampaignDocs ×8 + test_dag_has_14_atoms ×1 / 5 skipped).

- **Two architectural surprises surfaced** beyond the Q7 surface that A.1 must respect:
  1. **Namespace disambiguation**: `decision_style` is used in TWO semantically-different namespaces — bipolar TRAIT (1 hit, the Neo4j seed) vs categorical-bucket VARIABLE (683 hits across demo/intelligence/orchestrator/workflows holding values like 'system1_intuitive', 'satisficing', etc.). A.1 scope = trait namespace only; bucket-namespace is out-of-scope.
  2. **Dormant Neo4j seed**: `dim_cog_decision_style` has ZERO READ_BY sites in the codebase. The construct is queried/used everywhere via Python-identifier names (`decision_maximizer` ×19, `maximizer_tendency` ×7) — not via Neo4j queries. Implication: keeping `dimension_id` stable in A.1 has zero downside.

- **Audit-recommended A.1 scope** (subject to Claude Proper adjudication of Q10.A–G):
  - Canonical name: `maximizer_tendency`
  - `dimension_id` strategy: option (i) keep stable
  - Migration mechanics: option (β) new migration `031` with `MATCH...SET`
  - `construct_taxonomy.py` bipolar `dm_maximizer`/`dm_satisficer` split: leave intact (academically faithful to Schwartz Maximization Scale)
  - Categorical-bucket namespace (683 hits) + `"satisficing"`/`"maximizing"` categorical values (67 hits): NOT in A.1 scope
  - Enum rename: `MAXIMIZING_TENDENCY` → `MAXIMIZER_TENDENCY` + value `"maximizing_tendency"` → `"maximizer_tendency"`, pending persistence-layer check
  - Estimated commit-LOC delta: +50 to +100 lines, 7 file edits + 1 new migration; zero existing test edits required

- **Per-site rename plan** (memo §8.4): 19 `decision_maximizer` hits across 8 files become `maximizer_tendency`; 1 `MAXIMIZING_TENDENCY` enum hit becomes `MAXIMIZER_TENDENCY`; 7 already-canonical `maximizer_tendency` sites unchanged. No `dm_maximizer`/`dm_satisficer` changes (intentional bipolar split). No `decision_style` (variable) changes.

- **Expected next:** A.1 consolidation refactor. Awaits Claude Proper prompt incorporating audit findings — specifically: (1) Q10.A canonical-name confirmation, (2) Q10.B `dimension_id` strategy, (3) Q10.C migration mechanics, (4) Q10.D bipolar-split disposition, (5) Q10.E + Q10.F namespace-scope confirmations, (6) Q10.G enum-value rename + persistence-layer check authorization.

- **Hand-off pointer:** Branch `feature/hmt-dashboard` @ `c237e4b`. A.0 + A.1.0 closed. A.1 awaits adjudication. Working tree carries this MEMORY.md update + the prior-turn `docs/PLATFORM_INVENTORY_2026_05_07.md` still untracked-pending.

---

### Session 2026-05-07 — A.0 docs-slice — gap-assessment artifact landed

**EVE Handoff:**

- **Executed:** A.0 docs-slice (commit `cf41115`). Added `docs/MINDSET_COVERAGE_GAP_ASSESSMENT_2026_05_07.md` as tracked repo artifact (403 lines, 7,679 words, 59 KB; §1 Executive Summary through §7 Practicality Filter Disposition Table plus Caveats). Zero code changes; zero test changes; **5,153 tests passing** unchanged.

- **Verified:** Document present at spec-expected path; full markdown structure intact (§1, §2, §3 Coverage Matrix Blocks A–F, §4 Trait × State Deep-Dive, §5 Academic Substrate, §6 Operationalization Path 8-step S6.1 spec, §7 Practicality Table, Caveats); no other repo files modified; full pytest suite passes (5,153 passed / 9 pre-existing failures unchanged: TestCampaignDocs ×8 + test_dag_has_14_atoms ×1 / 5 skipped).

- **Pre-flight resolution chain** (recorded across QUESTIONs 6/7/8/9):
  - Q6: constrained mindset map source absent (S6.1 surface) — superseded by gap-assessment ship
  - Q7: S6-prep.1 multi-trigger (existing `decision_style` PersonalityDimension at migration `005:148`; 7-site fragmentation; cold_start engine uses 8 Jung archetypes not 10 / 5; gap-assessment doc absent) — adjudicated as: A.0 ships doc → A.1 consolidates 7 sites → A.2 revised priors against engine's 8 Jung archetypes
  - Q8: A.0 prompt placeholder `[FULL CONTENT FROM THE ARTIFACT...]` — resolved by Chris pre-staging file in working tree
  - Q9: filename mismatch (`docs/ADAM:INFORMATIV Mindset Coverage Gap Assessment.md` → `docs/MINDSET_COVERAGE_GAP_ASSESSMENT_2026_05_07.md`) — Chris adjudicated (a) authorize plain `mv`; rename complete; spec-expected path now the canonical location

- **Expected next:** A.1 consolidation refactor — `decision_style` → `maximizer_tendency` rename across 7 fragmentation sites per Q7.A=(c) + Q7.B=(ii). For A.1 pre-flight, **the prompt should specify**:
  1. Complete list of 7 fragmentation sites with current local naming (recorded in Q7 surface for reference: `005_seed_personality_dimensions.cypher:148` `decision_style` / `dim_cog_decision_style`; `adam/cold_start/models/enums.py:147` `MAXIMIZING_TENDENCY = "maximizing_tendency"`; `adam/intelligence/unified_psychological_intelligence.py:197` `maximizer_tendency: float`; `adam/intelligence/construct_taxonomy.py:653-654` `dm_maximizer` + `dm_satisficer`; `adam/intelligence/empirical_psychology_framework.py:714,772` `"satisficing"` + `"maximizing"`; `adam/intelligence/unified_construct_integration.py:152` `"decision_maximizer"`; `adam/intelligence/historical_data_reprocessor.py:977` + `langgraph_alignment_integration.py:347` `"satisficing"` decision style)
  2. Migration `005`'s `dim_cog_decision_style` schema handling — keep stable `dimension_id` with new `name`, or rename `dimension_id` too (touches index/constraint surface)
  3. Test-update strategy for any tests pinning the old names

- **Hand-off pointer:** Branch `feature/hmt-dashboard` @ `cf41115`. A.0 closed. A.1 pre-flight will surface as soon as the consolidation-rules prompt arrives. Working tree carries this MEMORY.md update + the prior-turn `docs/PLATFORM_INVENTORY_2026_05_07.md` still untracked-pending.

---

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
