# ADAM Pilot — Next-Month Plan (2026-04-29 onward)

**Status as of write**: 22 commits this session; 409 tests passing across Phase 0.1+ surface; all 16 simulation-derived tasks shipped (substrate-complete). External-integration items await Chris-driven conversations.

**Working hypothesis on launch date**: aggressive case 4-5 weeks (late May 2026); conservative case 6-8 weeks (early-to-mid June 2026). Driven by external-dependency clearance, NOT by additional code work.

---

## Section 1 — Where we are today

### What's in code (HEAD = `4534cfd`)

| Layer | Module(s) | Commits |
|---|---|---|
| **L3 architectural override** | `campaign_orchestrator._select_mechanisms` | `bf69274` |
| **Synthetic measurement** | `synthetic_ab_simulation`, `causal_conformal` | `105ee4a` `362dd9f` |
| **Pilot 2 demo artifact** | `mechanism_rotation` | `9f5a36d` |
| **Loop B (HMT v0.1)** | `dialogue_ledger/` (4 modules) | `6f4f945` `6fdb76d` `d7fbb44` |
| **Differentiator** | `chain_rendering` | `437d055` |
| **Tier 2 compounders** | `mechanism_taxonomy_runtime`, `online_learning_substrate`, `page_attentional_posture_substrate` | `6ae506e` `968aaab` `dbf3532` |
| **Negative-outcome substrate** | `negative_outcome_adapters` | `e5e6d95` |
| **Multi-horizon adjudication** | `multi_horizon_adjudication` | `b07cc5e` |
| **Agency dashboard payload** | `agency_dashboard` | `dd00435` |
| **Pre-pilot smoke test** | `tests/integration/test_pre_pilot_smoke` | `4534cfd` |
| **Phase 0.1 Day 1-3 wiring** | chain modulation + contribution ingestion + A14 counter + e2e smoke | `cf399d3` `3a7109e` `fec2c40` `b3fb29b` |
| **M4 Aura migration** | applied to production Aura via Path A backfill (24 prior migrations marked) + 029 ts_propensity index | (operational, no commit) |

### Documents shipped

- `docs/PILOT_PRE_REGISTERED_ANALYSIS_PLAN.md` (`7d20aa6`)
- `docs/PILOT_FAILURE_MODE_RUNBOOK.md` (`e5cd56e`)
- `docs/PILOT_REVIEWER_METHODOLOGY_BRIEF.md` (`407ac38`)
- This document

### What's NOT in code (external-dependency-bound)

| Item | Blocker | Driver |
|---|---|---|
| LUXY-specific negative-outcome adapter | Need LUXY's stack details (Stripe? Shopify? custom CRM?) | Becca → LUXY |
| LUXY pixel installation | LUXY web team scheduling | LUXY web team |
| StackAdapt write API permissions | Approval + key delivery to Becca | Becca → StackAdapt |
| Webhook configuration with StackAdapt | Production endpoint registration | Chris + Becca |
| Creative QA gauntlet | Agency-of-record approval pipeline | Becca → agency creative team |
| LUXY baseline conversion rate | Becca pulls from StackAdapt historical | Becca |
| Third-party statistical reviewer | Outreach + scheduling | Chris |
| 2-arm vs 2×2 factorial decision | Budget envelope review | Chris + Becca + LUXY |

---

## Section 2 — Pilot launch criteria

Before live spend, ALL of these must be true:

1. **Pre-registered analysis plan locked + published** (OSF or AsPredicted)
   - LUXY baseline conversion rate confirmed → power calc finalized
   - 2-arm vs 2×2 factorial decision made
   - Third-party statistical reviewer signed off
   - Published externally with timestamp

2. **Operational integration verified**
   - StackAdapt write API working (segment push validated against synthetic audience)
   - Webhook end-to-end tested (synthetic conversion event flows through)
   - LUXY pixel installed + firing (synthetic page load triggers conversion event)
   - Creative QA pipeline rehearsed (creative pulled + variant swap tested)

3. **Negative-outcome instrumentation flowing**
   - LUXY refund/complaint events route to OutcomeHandler
   - At least one synthetic refund test event end-to-end through production

4. **Failure-mode runbook rehearsed** (Week 4 of pre-launch)
   - All 7 failure modes injected synthetically
   - Decision tree responses match runbook
   - LUXY communication templates drafted

5. **Pre-pilot smoke test green in CI**
   - `tests/integration/test_pre_pilot_smoke.py` passes
   - All Phase 0.1+ unit tests pass

6. **Pre-registered mechanism rotation commitments registered**
   - At least 1 falsifiable rotation commitment in `RotationRegistry`
   - Public commitment timestamp + rationale + trigger condition

7. **Production deployment to Railway**
   - Latest code deployed
   - Health-check endpoints green
   - Prometheus metrics flowing

---

## Section 3 — Week-by-week plan

### Week 1 (2026-04-29 to 2026-05-05) — Kickoff conversations

**Goal**: Get every external dependency moving in parallel. Don't wait for one to clear before starting the next.

#### Chris-driven (sequential or parallel)

- [ ] **Day 1**: Becca call — share the four documents, walk through the 16 tasks shipped, set expectations on the 8 external items. **Outcome**: aligned operational owner per item.
- [ ] **Day 1-2**: LUXY stack-discovery call (Becca runs, Chris attends).
  - Confirm payment provider (Stripe? Shopify? custom?)
  - Confirm CRM stack
  - Confirm refund/complaint event accessibility
  - **Outcome**: enough info for me to pick or build the LUXY-specific negative-outcome adapter
- [ ] **Day 1-3**: LUXY web team — pixel install scheduling.
  - Pixel code spec → LUXY web team
  - Confirm install date target
  - **Outcome**: pixel install on calendar
- [ ] **Day 2**: LUXY baseline conversion rate request.
  - Becca pulls 90-day historical CTR + conversion rate from StackAdapt
  - **Outcome**: numbers to plug into the pre-registered analysis plan's power calc
- [ ] **Day 2**: StackAdapt write API permissions request.
  - Becca submits to StackAdapt
  - **Outcome**: API token delivery target date
- [ ] **Day 3-4**: Third-party statistical reviewer outreach.
  - Reach out to 2-3 candidates with the methodology brief
  - **Outcome**: reviewer scheduled for Week 3
- [ ] **Day 4-5**: Budget + 2-arm-vs-2×2 decision call (Chris + Becca + LUXY).
  - Review pilot budget envelope
  - Decide: 2-arm or 2×2 factorial?
  - **Outcome**: control-arm spec locked

#### My parallel work (Chris-unblocking)

- [ ] **Day 1-2**: Wire `online_learning_substrate` into `_select_mechanisms` scoring path.
  - Cascade reads fresh LinkPosteriors at decision time per task #30 substrate
  - Modulator form + bounds (e.g., [0.7, 1.3]) per the substrate's documentation
  - A14 flag for the bounds choice
  - Tests: cascade scores demonstrably differ when posteriors update mid-stream
- [ ] **Day 2-3**: Wire `mechanism_taxonomy_runtime.tag_decision` into `_select_mechanisms` so every decision stamps its category onto metadata.
  - Outcome handler reads the tag at outcome time → routes to TaxonomyConditionalAccumulator
- [ ] **Day 3-4**: Wire `multi_horizon_adjudication.register_conversion` into OutcomeHandler.
  - When a conversion outcome fires, register a cohort in the adjudicator
  - Tests pinned
- [ ] **Day 4-5**: Wire `page_attentional_posture_substrate.record` into the page intelligence pipeline.
  - Whenever a page profile is computed, record an observation
  - Substrate compounds through pilot

**End of Week 1 deliverable**: 4 substrate items wired into production paths. External conversations all kicked off.

---

### Week 2 (2026-05-06 to 2026-05-12) — Receiving + adapter work

**Goal**: External info starts flowing back. Build receivers for what arrives.

#### My work (responsive to Week 1's external clearance)

- [ ] **Day 6-7**: LUXY-specific negative-outcome adapter.
  - Subclass appropriate base (Stripe / Shopify / GenericJSON) per Week 1 stack discovery
  - Wire to default registry
  - Tests against synthetic LUXY-shaped payloads
- [ ] **Day 7-8**: LUXY pixel handler (client-side + server-side).
  - Client-side JS that fires on conversion + return-visit events
  - Server-side route that ingests + routes to `multi_horizon_adjudication.record_return_visit`
  - HMAC validation if Becca wires the pixel through StackAdapt
- [ ] **Day 8-9**: Power calc finalization.
  - LUXY baseline conversion rate from Becca → `n_per_arm` calculation
  - Update `PILOT_PRE_REGISTERED_ANALYSIS_PLAN.md` with finalized numbers
  - 2-arm vs 2×2 decision flowed in
- [ ] **Day 9-10**: First mechanism rotation commitment registered.
  - Specific rotation: e.g., "Day 21 of pilot, careful_truster × prevention pages, authority → brand_trust_evidence when bilateral edge count crosses 50 conversions"
  - Public statement drafted; internal RotationRegistry registered
  - Becca shares with LUXY for buy-in
- [ ] **Day 10**: First-pass cascade modulation by online learning substrate verified end-to-end.
  - Run the orchestrator's full path with a known LinkPosterior shift
  - Confirm mechanism_scores reflect the shift

#### Chris-driven

- [ ] **Day 6-7**: Reviewer scheduled (target: Week 3 engagement, 2-2.5 hours)
- [ ] **Day 7**: Pixel install on `luxyride.com` (LUXY web team)
- [ ] **Day 8-10**: StackAdapt write API token received + tested via Becca's segment-push smoke test
- [ ] **Day 10**: Creative QA gauntlet kickoff (agency-of-record + LUXY brand team)

**End of Week 2 deliverable**: LUXY-specific adapters in code. Pixel installed. Power calc finalized. First rotation commitment registered. StackAdapt write API live.

---

### Week 3 (2026-05-13 to 2026-05-19) — Synthesis + reviewer + dry-run prep

**Goal**: Lock the pre-registered plan. Reviewer signs off. Production-equivalent staging fully tested.

#### Chris-driven

- [ ] **Day 11-12**: Third-party statistical reviewer engagement (2-2.5 hour billable).
  - Reviewer reads pre-registered plan + methodology brief + key commit diffs
  - 1-hour Q&A
  - Reviewer drafts signed memo
  - **Outcome**: signed-off plan OR amendments to make
- [ ] **Day 12-13**: Amendments cycle (if reviewer named any).
  - Update analysis plan
  - Re-circulate for sign-off if material
- [ ] **Day 13-14**: Pre-registered analysis plan published externally.
  - OSF or AsPredicted submission
  - Public timestamp on the methodology
- [ ] **Day 14**: Production deployment to Railway.
  - All Phase 0.1+ commits + integration wiring
  - Health checks + Prometheus metrics flowing
  - Smoke test green in production
- [ ] **Day 15**: Staging dry-run with Becca.
  - Walk through the agency-facing dashboard payload
  - Run a synthetic decision through the full production pipeline
  - Confirm the dashboard's data is what Becca expects to show LUXY

#### My parallel work

- [ ] **Day 11-12**: Frontend rendering of the agency dashboard payload (if Chris wants it before launch).
  - Static HTML template OR a lightweight React app that consumes `agency_dashboard.build_agency_dashboard_payload` JSON
  - Vocabulary discipline at the display layer (not just the backend)
  - **Decision point for Chris**: is this needed pre-launch, or post-launch?
- [ ] **Day 13-14**: Failure-mode runbook Week-4 rehearsal preparation.
  - Synthetic injection scripts for each of the 7 failure modes
  - Time-to-detection + time-to-decision targets per the runbook
- [ ] **Day 15**: Sniff test the entire pipeline against a 1-hour synthetic flight.
  - 1000 synthetic decisions through the production-equivalent pipeline
  - Verify dashboard payload, attention-inversion diagonals, multi-horizon adjudication all populate

**End of Week 3 deliverable**: signed-off pre-registered plan published externally. Production deployed. Staging dry-run with Becca complete.

---

### Week 4 (2026-05-20 to 2026-05-26) — Final week + pilot launch decision

**Goal**: Launch criteria all green. Ready to make the go/no-go call.

#### Day-by-day

- [ ] **Day 16**: Failure-mode runbook rehearsal (1 day, all 7 modes).
  - Inject each mode synthetically
  - Time-to-detection + time-to-decision recorded
  - Communication templates drafted
  - Drift from runbook → revise runbook before launch
- [ ] **Day 17**: Final pre-launch smoke test in production.
  - All accumulators reset to clean state
  - Run `tests/integration/test_pre_pilot_smoke.py` against production endpoints (with synthetic data)
- [ ] **Day 18**: LUXY pre-launch sign-off.
  - Becca presents the agency-facing dashboard preview to LUXY
  - LUXY confirms the pilot scope + budget + creative
- [ ] **Day 19**: Internal go/no-go call (Chris + Becca).
  - Walk through the 7 launch criteria one by one
  - Each must be GREEN
  - Any RED → defer launch, address blocker
- [ ] **Day 20**: PILOT LAUNCH (if green).
  - Audience pushed to StackAdapt
  - Webhook live
  - Pixel firing
  - Dashboards live
  - First commitment registered
  - Becca + Chris on-watch for Day 1
- [ ] **Day 21-22**: Day 1-2 of live flight, intensive monitoring.
  - Hourly check-ins per failure-mode runbook
  - Any drift → rapid response per runbook

**End of Week 4 deliverable (aggressive case)**: PILOT LIVE.

If launch criteria not all green: defer 1-2 weeks (Week 5-6) to address remaining blockers. Most likely blockers: LUXY pixel install delay, StackAdapt API delay, reviewer scheduling delay.

---

## Section 4 — Decision points + responsibilities

### Decisions Chris owns

| Decision | When | Inputs |
|---|---|---|
| 2-arm vs 2×2 factorial | Week 1 Day 4-5 | Pilot budget envelope; statistical sufficiency |
| Reviewer selection (which candidate) | Week 1 Day 4-5 | 2-3 candidate quotes; CV match for stat methodology |
| First rotation commitment specifics | Week 2 Day 9-10 | Bilateral edge corpus signal-density per archetype |
| Frontend dashboard pre-launch yes/no | Week 3 Day 11 | Becca's pitch readiness; LUXY's expected first-impression |
| Pilot launch go/no-go | Week 4 Day 19 | All 7 launch criteria green |

### Decisions Becca owns

| Decision | When | Inputs |
|---|---|---|
| LUXY stack-discovery agenda | Week 1 Day 1 | Operational checklist |
| LUXY baseline conversion rate confirmation | Week 1 Day 2 | StackAdapt 90-day pull |
| Creative variant priority order | Week 2 Day 10 | Brand team feedback; bilateral cascade output |
| LUXY communication during failure modes | Per runbook §1-7 | Failure-mode runbook templates |

### Decisions LUXY owns

| Decision | When | Inputs |
|---|---|---|
| Pilot budget envelope confirmation | Week 1 Day 4-5 | Internal LUXY budget cycle |
| Pre-registered mechanism rotation buy-in | Week 2 Day 9-10 | Becca walkthrough |
| Pre-launch sign-off | Week 4 Day 18 | Dashboard preview from Becca |

---

## Section 5 — Risk register

### High-likelihood / high-impact

1. **LUXY web team pixel install delay** (likelihood: medium, impact: high)
   - **Mitigation**: kick off Day 1; escalation path through Becca + LUXY operational owner
   - **If realized**: defer multi-horizon adjudication endpoint to post-launch; primary endpoint unaffected

2. **Third-party stat reviewer scheduling delay** (likelihood: medium, impact: medium)
   - **Mitigation**: outreach to 2-3 candidates simultaneously; methodology brief ready Day 1
   - **If realized**: defer 1 week; pilot launch slips by same

3. **LUXY stack proves more complex than adapter substrate handles** (likelihood: low, impact: medium)
   - **Mitigation**: substrate already handles 3 common shapes; adding one custom adapter is ~1 day
   - **If realized**: build custom adapter Week 2

### Lower-likelihood / high-impact

4. **Pilot launch fails operational integration smoke test** (likelihood: low, impact: high)
   - **Mitigation**: pre-pilot smoke test runs in CI on every commit; rehearsal Week 4 catches before live spend
   - **If realized**: defer 1-2 weeks to fix; reduce launch risk

5. **Reviewer flags fundamental methodology issue** (likelihood: low, impact: high)
   - **Mitigation**: methodology brief explicitly invites pushback on conformal variant, multi-comparison, control-arm spec
   - **If realized**: amend pre-registered plan; re-circulate for sign-off; defer 1 week

### Medium-likelihood / medium-impact

6. **Becca's dashboard expectations differ from `agency_dashboard` payload structure** (likelihood: medium, impact: medium)
   - **Mitigation**: Day 15 staging dry-run with Becca surfaces this in advance
   - **If realized**: payload is JSON-flexible; rendering is the layer that adapts

7. **LUXY budget tightens, forcing 2-arm instead of 2×2** (likelihood: medium, impact: low)
   - **Mitigation**: pre-registered plan has 2-arm fallback specified
   - **If realized**: lock 2-arm; primary endpoint claim narrows but stays defensible

---

## Section 6 — Discipline anchors for the month

Per the orientation document (`ADAM_AGENT_ORIENTATION.md`), maintained throughout:

### Vocabulary at the partner interface

The agency dashboard payload uses cognitive vocabulary by design (`construct_chain` not "reasoning explanation", `uncertainty_panel` not "confidence scores"). The frontend (if built) and Becca's communications must NOT undo this. Every external touchpoint with LUXY uses cognitive vocabulary, not programmatic-DSP vocabulary.

### A14 retirement watch

The A14 retirement-trigger Prometheus counter (commit `fec2c40`) is live. As pilot data accumulates, the dashboard reads the counter to track which calibration-pending coefficients have crossed their retirement triggers. **Commit by Week 8 of pilot**: at least N flags retired publicly. Without retirement, the discipline becomes theatre.

### Amendments log discipline

Every change to the pre-registered analysis plan (post-publication) goes in the amendments log with reason. Every transparent change (audience swap, creative swap, market shift, A14 coefficient retirement) gets logged. Audit trail is the difference between defensible pilot and unfalsifiable claims.

### Loop B captures everything

Becca's interpretations during pilot ("this is a competitor launch", "this archetype seems off") become Loop B Claims (HMT discipline rule 12 — HYPOTHESIS at write time, not learning). Subsequent data tests them. Never let Becca's tacit knowledge become anecdote.

### Foundation §7 rule 11 hold

Selection is amoral; the fitness function IS the ethics. Negative-outcome instrumentation (refund/complaint/regret/churn) MUST be flowing before live spend. Without it, the system silently optimizes toward whatever maximizes immediate conversion regardless of downstream damage. **This is non-negotiable in the launch criteria.**

### Verification before layering

Per orientation Part XI rule 2: do not build commit N+1 on an unverified commit N. Through Weeks 1-3, Chris drives at least one verification touch per week — running the smoke test, reading commit diffs, exercising the staging dashboard.

### Drift watches per commit

Each new commit during the month follows the Part VII self-check before commit:
- Name antipatterns touched (A1-A15)
- Cite paper:section for any binding claim
- A14 flag every calibration-pending coefficient with retirement trigger
- Vocabulary discipline (cognitive, not programmatic)
- No LLM-composed prose

---

## Section 7 — Calendar summary

### Week 1 (2026-04-29 to 2026-05-05)

External conversations kickoff. Chris drives 8 parallel tracks. My work: cascade integration of Tier 2 substrate into production paths.

**Commits expected**: 4-6 (cascade-integration commits)

### Week 2 (2026-05-06 to 2026-05-12)

External info flows back. LUXY adapter built. Pixel installed. Power calc finalized. First rotation commitment registered.

**Commits expected**: 3-5 (LUXY adapter + pixel handler + first commitment)

### Week 3 (2026-05-13 to 2026-05-19)

Reviewer engagement. Pre-registered plan locked + published. Production deployed. Staging dry-run with Becca.

**Commits expected**: 2-4 (deployment fixes + staging dry-run findings)

### Week 4 (2026-05-20 to 2026-05-26)

Failure-mode rehearsal. Final smoke test. LUXY sign-off. **Pilot launch decision**.

**Commits expected**: 1-3 (last-minute fixes from rehearsal findings)

### After launch

Weekly status with Becca. Daily monitoring per failure-mode runbook. Mid-pilot rotation event firing per pre-registered commitment(s). End-of-flight analysis runs the pre-registered primary + secondary endpoints + multi-horizon adjudication.

---

## Section 8 — What this plan ISN'T

**It isn't a guarantee of launch within the month.** It's a plan for launch within the month IF external dependencies clear quickly. If LUXY pixel install slips a week, launch slips a week. If reviewer scheduling slips, launch slips. The plan provides the framework; reality provides the dates.

**It isn't an exhaustive task list.** Edge cases will surface during external conversations. The runbook + orientation + analysis plan are the source-of-truth for HOW to handle them; this plan is the WHAT-and-WHEN scaffold.

**It isn't optimized for compression beyond honesty.** The aggressive case (4-week launch) requires every external dependency to clear without delays. The conservative case (6-8 week launch) is realistic if any single external dependency hits a 1-week delay. Per the orientation: build correct, ship honest. Not "compress at all costs."

**It isn't a substitute for the foundation, orientation, or HMT documents.** Those are loaded every session. This is operational scaffolding on top.

---

## Section 9 — Reference document index

In load order, every session:

1. `ADAM_AGENT_ORIENTATION.md` — drift discipline (load FIRST)
2. `ADAM_THEORETICAL_FOUNDATION.md` — Bargh-lineage frame
3. `ADAM_HUMAN_MACHINE_TEAMING_FOUNDATION.md` — Loop B / partnership
4. `CLAUDE.md` — engineering conventions
5. `memory/MEMORY.md` — session continuity index

For the month:

6. `docs/PILOT_PRE_REGISTERED_ANALYSIS_PLAN.md` — primary analysis plan (lock by Week 3)
7. `docs/PILOT_FAILURE_MODE_RUNBOOK.md` — operational decision trees
8. `docs/PILOT_REVIEWER_METHODOLOGY_BRIEF.md` — reviewer engagement packet
9. **THIS DOCUMENT** — week-by-week scaffold

---

## Section 10 — One-paragraph executive summary

Pre-pilot substrate is complete in code (22 commits this session, 409 tests, all 16 simulation-derived tasks). The remaining 4 weeks are operational: external integrations (LUXY stack discovery, pixel install, StackAdapt API, creative QA gauntlet, reviewer engagement), final substrate wiring into production paths, staging dry-run, failure-mode rehearsal, pilot launch decision. Aggressive launch target end of May 2026; conservative early-to-mid June. Launch criteria are 7 specific items, ALL green for go. Per orientation discipline: when in doubt, defer rather than launch with a red criterion. The discipline IS the differentiator.

**HEAD: `4534cfd`**.
