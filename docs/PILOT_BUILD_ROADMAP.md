# ADAM Pilot — Comprehensive Build Roadmap (Next Month) — v2

**Status today** (HEAD `e47e068`): 22 commits this session shipped Phase 0.1+ substrate; 409 tests passing; 16 simulation-derived tasks complete.

**Why v2**: The earlier simulation scored 16 items but did NOT enumerate the complete possibility set. This revision enumerates ALL possible build items (~70 across 8 layers), re-runs the simulation scoring on items previously omitted, and orders the final roadmap by **(a) simulation priority + (b) dependency graph + (c) build efficiency**.

**Working hypothesis**: aggressive 4-week launch achievable with 6 parallel workstreams; conservative 6-8 weeks if any external blocker slips a week. End-of-month definition: **system at full power**, not "minimum viable."

---

## Section 0 — Daily Mindset Protocol

**This section is read FIRST every work session. It is the recurring re-orientation that prevents drift.**

The orientation document (`ADAM_AGENT_ORIENTATION.md`) is the canonical drift defense — load it every session before this. This protocol is the build-specific application: what drift looks like during pilot construction, and the specific anchors that hold.

### 0.1 — Pre-session loading order (every session, no exceptions)

```
1. ADAM_AGENT_ORIENTATION.md            (drift discipline, 15 antipatterns)
2. ADAM_THEORETICAL_FOUNDATION.md       (Bargh-lineage frame)
3. ADAM_HUMAN_MACHINE_TEAMING_FOUNDATION.md  (Loop B)
4. CLAUDE.md                            (engineering conventions)
5. memory/MEMORY.md                     (auto-loaded)
6. docs/PILOT_BUILD_ROADMAP.md (this)   ← Section 0, then today's items in Section 5
7. The user's specific request          ← read LAST so it lands in the established frame
```

If load order is broken, the request lands in the default lens. If load order is held, the request lands in the correct frame. This is non-negotiable.

### 0.2 — Re-anchor on the stakes (read aloud at session start)

> The pilot has $30K/week, ~12 weeks runway, friendly partner with prior trust. **This is NOT "succeed or fail with no margin."** It IS "build for full power, ship honestly, defer launch when any criterion is RED." The friendly runway is for building correctly, not for compressing past correctness.
>
> The system at full power means every Phase 0.1 substrate is wired, full methodology stack (M2/M3/M6 + plant model + distribution-calibrated thresholds) is active, Loop B v0.2 is complete, agency dashboard is rendered with cognitive vocabulary, LUXY integrations are live, and pilot launch is decided on data not optimism.
>
> The discipline IS the differentiator. Foundation §7 rule 11 holds: the fitness function IS the ethics. Selection is amoral. The reward signal designs the system's character. Every commit either honors that or erodes it.

### 0.3 — Drift signals specific to build work (catch them at the keystroke)

Watch for these. When felt, STOP, reread Part IX of the orientation document, and self-check.

| Signal | Likely drift | Recovery action |
|---|---|---|
| **"Velocity sensation"** — moving fast, build green | Using cached patterns, not thinking | Slow down. Run the Section 0.5 self-check. |
| **"Obvious component shape"** — what I'm writing feels obvious | Default-pattern-matching | Stop. Ask: is this cognition or scaffolding? |
| **English fluency in service modules** | Composing prose where structure should be | Replace with templated rendering from structured input |
| **"Generic"** appears in own thinking | Reaching for industry default | There is no generic in ADAM. Substitute the cognitive primitive. |
| **Pre-pruning before scoring** | Cutting items based on implicit framing before enumerating | List the complete possibility set FIRST, then score, then prune |
| **"Chris is busy, I'll just build"** | The drift itself | This document is here so the frame holds when Chris is busy. Read it. |
| **Justification assembly in advance of commit** | Drift dressed for approval | Stop. Rewrite the diff before the commit message. |
| **Reaching for a sophistication item to feel productive** | Confusing rigor with theatre | Ask: does this item help Pilot 1, compound to Pilot 2-5, or is it methodology theatre? |
| **Defaulting to "graceful degradation"** | Engineering virtue that contaminates inferential systems | If the gracefulness silently consumes simulated/proxy data into the learning loop, REJECT it |
| **Composing English in a generator function** | Hand-crafted "AI says" prose where atom traces should be | Refactor to render structured input |

### 0.4 — Discipline rules binding today (every commit must honor)

Eight non-negotiable rules. Each commit checks against them.

1. **Foundation §7 rule 11** — fitness function IS the ethics. Negative-outcome instrumentation must flow before live spend. Asymmetric selection silently optimizes toward exploitation.

2. **HMT discipline rule 12** — every user assertion is HYPOTHESIS at write time. Promotion requires instrumentation + horizon completion + causal adjudication. Pydantic + service-layer both enforce.

3. **Vocabulary discipline at every layer** — backend, frontend, payload keys, communication templates. Cognitive vocabulary, NOT programmatic-DSP vocabulary. "Construct chain" not "reasoning explanation"; "uncertainty panel" not "confidence scores"; "rotation events" not "campaign updates"; "session mood" not "user sentiment."

4. **A14 retirement triggers** — every calibration-pending coefficient gets an A14 flag with a specific retirement trigger named at creation. The Prometheus counter (`fec2c40`) tracks accumulation. Public dashboard displays progress toward retirement. Without retirement, the discipline becomes theatre.

5. **No LLM-composed prose at any rendering layer** — chain rendering, dashboard payload, communication templates, runbook responses, panel claim text — ALL templated from structured data. Never generated. Test coverage anchors this (e.g., `TestNoLLMComposedText`).

6. **Verification before layering** — Chris drives ≥1 verification touch per week (smoke test run, commit diff read, staging dashboard exercised). Stacked unverified commits past 5 = drift signal; pause and surface.

7. **Per-commit antipattern audit** — every commit message names which of A1-A15 the diff touches and how each was held or honestly violated. "None applicable" is rarely true; itself a drift signal.

8. **Build correct, ship honest, defer launch when any criterion is RED** — not "compress at all costs." Friendly runway is for correctness, not for haste.

### 0.5 — Pre-commit self-check (every commit, before `git commit`)

Adapted from orientation Part VII. Apply EVERY time:

- [ ] **What cognitive mechanism does this commit embody?** If "none — just plumbing," is plumbing the right scope? Plumbing is fine; "feature" without mechanism isn't.
- [ ] **Where does this commit's content originate?** Atom state? Graph query? Templated from structured input? **Composed prose?** Composed prose is drift; rewrite.
- [ ] **What test pins the load-bearing claim?** "It builds" is not pinning. A test that asserts the structural property IS pinning.
- [ ] **What antipatterns is this commit at risk of?** Name them (A1-A15). State how each was held.
- [ ] **What A14 flag does this commit add or retire?** Every calibration-pending coefficient gets one. Every retirement names what's empirical now.
- [ ] **Is the vocabulary discipline maintained at every layer touched?** Check the diff for "dashboard," "recommend," "settings," "approval," "user-friendly."
- [ ] **Did Chris verify the previous commit before I built this one?** If no, and unverified commits ≥ 5, pause and surface for verification.
- [ ] **Could a hostile due-diligence reader challenge any claim in this diff?** If yes, soften or strengthen the claim per actual evidence.

### 0.6 — Today's focus protocol

Each work session, before opening any file:

1. **Read this Section 0 in full.** Not skim — read.
2. **Read the WEEK in Section 5 corresponding to today's calendar week.**
3. **Pick the next unblocked item from that week's list.** "Unblocked" means: dependencies (Section 3) are met; external info (Section 7 / E1-E8) has arrived if needed.
4. **Name the antipattern most at risk for THIS specific item.** Write it in the task description before starting.
5. **Identify the A14 flag(s) this commit will create.** Write the retirement trigger before writing code.
6. **Commit your intent to one focused commit.** Not "I'll do these 3 things"; "I will ship this one item."
7. **Build. Test. Self-check (0.5). Commit.**

If at any step the work expands beyond the planned item: STOP. Re-read Section 0.3. Decide if expansion is genuine necessity or drift toward "this will be fine, just build."

### 0.7 — When in doubt — DO NOT DEFAULT

Per orientation Part X. The instinct to fill gaps with defaults caused the prior drift. The instinct still arrives during build work — recognized and resisted is the discipline.

When uncertain whether a pattern is correct:

1. **Do not fill the gap with a default.** Default is the failure mode. Gap is information; default is noise.
2. **Name the unsureness specifically.** "I'm unsure whether X should be atom-derived or composed because [specific reason]." Not "I'm not sure about this."
3. **Ask Chris.** Even small questions. Cost of asking is seconds; cost of drifting is hours to weeks to a whole branch.
4. **If Chris is unavailable, state both options in the commit message and route the decision to him.** Do not pick silently. The silent pick IS the drift.

### 0.8 — Session-close ritual

At session end, before stopping:

1. **Did I hold the eight discipline rules in 0.4?** If not, name where slipped.
2. **Did every commit pass the 0.5 self-check?** Re-read the commit messages — could a hostile reader find drift hidden in them?
3. **What's the next session's first action?** Write it explicitly so next session opens with clarity.
4. **Update the roadmap if any item is complete.** Section 5 reflects current state.

### 0.9 — Mid-session reorientation (when drift is suspected)

If you notice during the session:
- The work is taking longer than expected because scope expanded
- The commits feel "fine" but the discipline rules feel less sharp
- Several commits stacked without Chris's verification
- A "this will be fine, I'll flag in the commit message" thought arrived

**Stop. Take 5 minutes.** Re-read Sections 0.2 (stakes), 0.3 (drift signals), and 0.4 (discipline rules). Ask: is the work I'm about to ship from cognition or from the cached pattern? If the answer is unclear, defer the commit, write a note, surface to Chris.

The friendly runway is the gift that lets us stop and re-orient. Don't burn it on rushed commits.

### 0.10 — Specific drift signals for this pilot

Beyond the orientation's general A1-A15, drift signals specific to ADAM pilot construction:

- **"This score is more sophisticated"** — sophistication ≠ pilot value. The simulation scoring (Section 2) is the priority anchor; sophistication beyond simulation rank is theatre.
- **"This will save time later"** — the friendly runway means later has time. Build correct now.
- **"The reviewer won't notice"** — if the reviewer wouldn't notice, neither will the empirical data. Cut the line; ship correct.
- **"I'll wire this fancy thing into the cascade scoring"** — wiring scoring changes are architecturally consequential. Substrate ships independently of wiring; wiring ships only after Chris approves the scoring change.
- **"I'll handle the Aura migration / production deploy quickly"** — operational actions against production warrant explicit authorization. Always.
- **"The synthetic test is enough"** — synthetic tests anchor the substrate. Pre-launch smoke test in production is what catches integration drift. Both required.

### 0.11 — Discipline anchor — three sentences

When this whole protocol feels like too much to read mid-session, repeat these three sentences:

> ADAM is the Bargh-lineage cognitive architecture for advertising. Every commit either honors that or erodes it. The fitness function IS the ethics — selection pressure is amoral and will reinforce whatever the reward signal rewards, including exploitation, unless the system is architected to resist.

If the work in progress is consistent with all three sentences, continue. If any sentence is in tension with the work, stop and re-read Section 0.

---

## Section 1 — Complete possibility set

Enumerated across 8 layers. **[S]** = shipped this session. **[W]** = wiring needed atop shipped substrate. **[N]** = not built. Items not previously simulated marked with **[NEW]**.

### Layer 1 — Cognition (decision-time)

1. **L3 override at cascade** [S] — `bf69274`
2. **M2 Causal Forests + Conformal** — conformal layer [S] `362dd9f`; econml install + production fit [N]
3. **M3 Hierarchical Bayes (PyMC non-centered)** [N] **[NEW]**
4. **M6 Constitutional AI cross-family critic** [N] **[NEW]**
5. **Online learning substrate (cascade-time LinkPosterior read)** — substrate [S] `968aaab`; cascade wiring [W]
6. **Mechanism-taxonomy runtime (decision-time tagging)** — substrate [S] `6ae506e`; cascade wiring [W]
7. **Page attentional posture substrate** — substrate [S] `dbf3532`; pipeline wiring [W]
8. **Plant model + adjudicator extension (Weakness #4)** [N] **[NEW]**
9. **Weakness #6 distribution-calibrated thresholds + regret-weighted rank** [N] **[NEW]**
10. **Construct-chain rendering** — substrate [S] `437d055`; orchestrator response wiring [W]
11. **Cascade trilateral query (page-conditioned mechanism)** — partially exists in `bilateral_cascade.py`
12. **Mechanism interaction effects beyond marginal** [N] **[NEW]** — interaction-term scoring per Foundation §2.5 (Ridley dynamic-competition)
13. **Cohort-based decision policies (non-stationary)** [N] **[NEW]** — cohort-conditional cascade
14. **Bayesian counterfactual analysis at decision time** [N] **[NEW]** — for "what if we had recommended X instead" trace

### Layer 2 — Outcome processing

15. **Negative-outcome adapter substrate** [S] `e5e6d95`; LUXY-specific adapter [N] (external dep)
16. **Multi-horizon adjudication substrate** [S] `b07cc5e`; outcome-handler wiring [W]
17. **Multi-horizon brand-equity proxy metric** [N] **[NEW]** — beyond just return-rate
18. **Discordance detection + alerting** [N] **[NEW]** — Prometheus alerting on multi-horizon discordance
19. **Per-atom contribution ingestion producer** [S] `3a7109e`
20. **Outcome handler chain-attestation routing** [S] `b60f727`

### Layer 3 — Loop B (HMT)

21. **Dialogue Ledger schema + service** [S] `6f4f945`
22. **4 elicitation generators (v0.1: ForcedPair, TimedPair, StoryPrompt, RecallabilityProbe)** [S] `6fdb76d`
23. **Uncertainty Panel renderer + mood probe** [S] `d7fbb44`
24. **6 more elicitation generators (v0.2: kAFC, RankOrder, CounterExample, Scenario, SPIES, FourPoint)** [N] **[NEW]**
25. **Why Library structured collection** [N] **[NEW]**
26. **Calibration Journal (per-user-per-domain Brier)** [N] **[NEW]**
27. **Deviation lifecycle (HumanDeviation + adjudication)** [N] **[NEW]**
28. **Protocol Meta-Learner** [N] **[NEW]**
29. **Loop B → analytics loop cross-pollination** [N] **[NEW]** — HMT §9.3 surfacing
30. **Defensive reasoning surfacing at recommendation time** [N] **[NEW]** — Why Library queried per recommendation

### Layer 4 — Measurement infrastructure

31. **Synthetic A/B simulation with planted lift** [S] `105ee4a`
32. **Conformal lift wrap** [S] `362dd9f`
33. **Per-atom contribution measurement framework** [S] in `b60f727` + tracker
34. **Holdout discipline (test/control split spec)** [N] **[NEW]** — pre-registered analysis-plan §2 covers; runtime enforcement [N]
35. **Per-archetype lift heterogeneity reporting** [N] **[NEW]**
36. **Per-cell sample-size adequacy tracker** [N] **[NEW]**
37. **Sequential analysis with early-stopping** [N] **[NEW]**
38. **Multiple-comparison correction framework** [N] **[NEW]** — Bonferroni / Benjamini-Hochberg
39. **A14 retirement-trigger Prometheus counter** [S] `fec2c40`

### Layer 5 — Pre-registered artifacts

40. **Mechanism rotation pre-reg substrate** [S] `9f5a36d`
41. **First mechanism rotation commitment registered** [N] (operational, Week 2-3)
42. **Pre-registered analysis plan v0.1 DRAFT** [S] `7d20aa6`
43. **Pre-reg locked + power calc finalized** [N] (Week 2 after baseline confirmed)
44. **Pre-reg published externally (OSF / AsPredicted)** [N] (Week 3)

### Layer 6 — Agency-facing layer

45. **Agency dashboard JSON aggregator** [S] `dd00435`
46. **Agency dashboard frontend rendering** [N] **[NEW]**
47. **Mechanism rotation graph artifact ("the single graph that wins Pilot 2")** [N] **[NEW]**
48. **Uncertainty Panel UI rendering** [N] **[NEW]**
49. **Loop B elicitation UI (4 v0.1 modes rendered)** [N] **[NEW]**
50. **Loop B elicitation UI (6 v0.2 modes rendered)** [N] **[NEW]**
51. **A14 retirement-trigger public dashboard** [N] **[NEW]**
52. **Per-atom contribution dashboard** [N] **[NEW]**
53. **Becca's daily standup view** [N] **[NEW]**
54. **LUXY's read-only access tier** [N] **[NEW]**

### Layer 7 — External integrations

55. **LUXY stack discovery** [N] (Becca-driven, Week 1)
56. **LUXY-specific negative-outcome adapter** [N] (my follow-up to 55)
57. **LUXY pixel install on luxyride.com** [N] (LUXY web team, Week 1-2)
58. **LUXY pixel handler (client + server)** [N] (my follow-up to 57)
59. **StackAdapt write API permissions** [N] (Becca, Week 1-2)
60. **StackAdapt webhook configuration** [N] (Chris + Becca, Week 1-2)
61. **Creative QA gauntlet rehearsal** [N] (Becca + agency, Week 2)
62. **Third-party statistical reviewer engagement** [N] (Chris, Week 1-3)
63. **LUXY baseline conversion-rate confirmation** [N] (Becca, Week 1)
64. **2-arm vs 2×2 factorial decision** [N] (Chris + Becca + LUXY, Week 1)

### Layer 8 — Operational + governance

65. **Pre-pilot smoke test framework** [S] `4534cfd`
66. **Production deployment to Railway** [N] (Week 3)
67. **CI/CD pipeline for new wirings** [N] **[NEW]** — extend existing CI
68. **Failure-mode runbook** [S] `e5cd56e`
69. **Failure-mode runbook rehearsal Week 4** [N] (Week 4)
70. **Incident response procedures** [N] **[NEW]** — beyond runbook
71. **M4 Aura migration applied** [S] (operational, Path A backfill)
72. **Schema reconciliation audit (Path B follow-up)** [N] **[NEW]** — defer post-pilot but acknowledged
73. **Pilot launch decision** [N] (Week 4 if green)
74. **Amendments log discipline** [S] (in pre-reg plan + runbook)
75. **Drift-watch automated checks** [N] **[NEW]** — pre-commit hook scanning for antipattern violations

**Total**: 75 items. **22 shipped this session** + **6 wired-needed (W)** + **47 not-built (N)** + 5 [NEW] previously not in simulation.

---

## Section 2 — Simulation scoring on items not previously simulated

Re-running the simulation framework (scenarios A-F from earlier analysis) on items I had cut without scoring. Keeps the same impact ratings (CRITICAL=5, HIGH=3, MEDIUM=2, LOW=1) and probability weights.

### Scenarios (recap)

| | Scenario | Probability |
|---|---|---|
| A | Strong baseline lift | 18% |
| B | Modest lift, high noise | 32% |
| C | Discovery — mixed results | 27% |
| D | Backfire | 18% |
| E | Market shift | 35% |
| F | Becca actively engages | 75% |

### Items previously cut, now scored

| Item | A | B | C | D | E | F | Weighted impact |
|---|---|---|---|---|---|---|---|
| **M3 Hierarchical Bayes** | 1 | 3 | 3 | 1 | 2 | 1 | 3.71 |
| **M6 Constitutional AI cross-family** | 1 | 1 | 2 | 3 | 1 | 2 | 3.13 |
| **Plant model + adjudicator extension** | 2 | 3 | 4 | 2 | 2 | 2 | 4.69 |
| **Weakness #6 distribution-calibrated thresholds** | 1 | 4 | 2 | 2 | 4 | 1 | 4.79 |
| **Loop B v0.2 (6 more elicitation modes)** | 1 | 2 | 2 | 1 | 1 | 4 | 4.40 |
| **Why Library structured collection** | 1 | 2 | 3 | 4 | 2 | 4 | 5.66 |
| **Calibration Journal (per-user Brier)** | 1 | 2 | 2 | 2 | 2 | 4 | 4.51 |
| **Deviation lifecycle** | 1 | 3 | 4 | 4 | 3 | 5 | 6.96 |
| **Protocol Meta-Learner** | 1 | 2 | 3 | 1 | 2 | 4 | 4.51 |
| **Cross-pollination Loop A↔B** | 1 | 3 | 4 | 3 | 3 | 4 | 5.97 |
| **Defensive reasoning at rec time** | 1 | 2 | 3 | 4 | 2 | 5 | 6.36 |
| **Mechanism interaction effects beyond marginal** | 2 | 4 | 4 | 2 | 2 | 1 | 4.91 |
| **Cohort-based non-stationary decision policies** | 1 | 2 | 3 | 2 | 4 | 1 | 4.06 |
| **Bayesian counterfactual analysis at decision time** | 1 | 2 | 3 | 2 | 2 | 3 | 4.27 |
| **Multi-horizon brand-equity proxy** | 1 | 3 | 3 | 5 | 3 | 2 | 5.83 |
| **Discordance detection + alerting** | 1 | 2 | 2 | 5 | 2 | 2 | 4.36 |
| **Per-archetype lift heterogeneity reporting** | 2 | 4 | 5 | 2 | 2 | 3 | 5.91 |
| **Per-cell sample-size adequacy tracker** | 1 | 4 | 3 | 1 | 2 | 1 | 3.61 |
| **Sequential analysis with early-stopping** | 1 | 3 | 2 | 2 | 2 | 1 | 3.34 |
| **Multiple-comparison correction framework** | 1 | 3 | 3 | 1 | 1 | 1 | 2.84 |
| **Agency dashboard frontend** | 2 | 3 | 3 | 3 | 3 | 5 | 6.97 |
| **Mechanism rotation graph artifact** | 4 | 3 | 3 | 3 | 3 | 5 | 7.71 |
| **Uncertainty Panel UI** | 2 | 3 | 3 | 3 | 3 | 5 | 6.97 |
| **Loop B elicitation UI** | 1 | 2 | 2 | 2 | 2 | 5 | 5.41 |
| **A14 retirement-trigger public dashboard** | 1 | 2 | 2 | 3 | 1 | 3 | 4.16 |
| **Becca's daily standup view** | 1 | 3 | 3 | 3 | 3 | 5 | 6.41 |
| **CI/CD pipeline for new wirings** | 2 | 3 | 2 | 3 | 2 | 1 | 3.59 |
| **Drift-watch automated checks** | 1 | 1 | 1 | 2 | 1 | 1 | 2.06 |
| **Schema reconciliation audit (Path B)** | 1 | 1 | 1 | 1 | 1 | 1 | 1.85 |

### Combined ranking (all simulated items)

Top 25 by weighted impact:

| Rank | Item | Weighted impact | Status |
|---|---|---|---|
| 1 | Loop B v0.1 | 8.17 | [S] |
| 2 | **Mechanism rotation graph artifact** | 7.71 | [N] |
| 3 | **Agency dashboard frontend** | 6.97 | [N] |
| 3 | **Uncertainty Panel UI** | 6.97 | [N] |
| 5 | **Deviation lifecycle** | 6.96 | [N] |
| 6 | **Becca's daily standup view** | 6.41 | [N] |
| 7 | **Defensive reasoning at recommendation time** | 6.36 | [N] |
| 8 | Pre-registered + 3rd-party review | ~6.15 | [DRAFT] |
| 9 | Construct-chain rendering | 5.97 | [W] |
| 9 | **Cross-pollination Loop A↔B** | 5.97 | [N] |
| 11 | **Per-archetype lift heterogeneity reporting** | 5.91 | [N] |
| 12 | **Multi-horizon brand-equity proxy** | 5.83 | [N] |
| 13 | M2 + Conformal | 5.81 | [partial] |
| 14 | **Why Library** | 5.66 | [N] |
| 15 | Per-decision online learning substrate | 5.56 | [W] |
| 16 | **Loop B elicitation UI** | 5.41 | [N] |
| 17 | Multi-horizon adjudication | 5.13 | [W] |
| 18 | L3 override | 5.01 | [S] |
| 19 | Synthetic A/B sim | ~5.00 | [S] |
| 20 | **Mechanism interaction effects beyond marginal** | 4.91 | [N] |
| 21 | **Weakness #6 distribution-calibrated thresholds** | 4.79 | [N] |
| 22 | **Plant model + adjudicator extension** | 4.69 | [N] |
| 23 | **Calibration Journal** | 4.51 | [N] |
| 23 | **Protocol Meta-Learner** | 4.51 | [N] |
| 25 | Negative-outcome instrumentation | 4.38 | [W external] |

### What re-scoring revealed

**Frontend/visualization items dominate the top of the ranking.** I previously buried these under "Tier 3 credibility wrapper." With scenario F (Becca engagement) at 75% probability and scenario A/B/C/D/E all ranking these as HIGH/CRITICAL for Becca's pitch, frontend rendering items are actually as load-bearing as the cognition layer.

**Deviation lifecycle (HumanDeviation + adjudication) was severely under-weighted.** It's #5 overall when properly scored. Without it, Becca's overrides during pilot are anecdotal — system doesn't learn from them. Foundation §7 rule 11 + HMT §11.5 both lean on it.

**Why Library + Defensive reasoning are tied — they pair.** Both score ~6.0. Why Library is the structured store; defensive reasoning is the rendering at decision time. They ship together as one capability, not separately.

**Per-archetype lift heterogeneity reporting is high-value at low N.** Foundation §2 prediction is per-archetype variance; reporting it correctly is the difference between "ADAM works" (vague) and "ADAM works for Careful Truster on prevention pages with these specific edge counts" (defensible).

**M3 Hierarchical Bayes scored lower than I cut it for.** Confirmed: defer until ≥1000 conversions per pool. But build the substrate so activation is flip-switch.

**Mechanism interaction effects beyond marginal scored higher than expected.** Foundation §2.5 (Ridley dynamic-competition) names this; it could meaningfully change the cascade scoring quality.

---

## Section 3 — Dependency graph

Build sequence respects what depends on what:

```
SUBSTRATE LAYER (mostly shipped) ──► WIRING LAYER ──► METHODOLOGY LAYER ──► FRONTEND LAYER ──► PRE-LAUNCH LAYER

Phase 0.1+ shipped substrate                     │
    │                                            │
    ├──► A1 Online learning wiring               │
    ├──► A2 Taxonomy tagging wiring              │
    ├──► A3 Multi-horizon wiring          ┐      │
    ├──► A4 Page posture wiring           │      │
    └──► A5 Construct-chain at response   │      │
                                          │      │
                                          ▼      │
       ┌────────────────────── B1 econml install + M2 fit
       │                       B2 M3 PyMC (gated on data)
       │                       B3 M6 cross-family
       │                       B4 Plant model + adjudicator
       │                       B5 Weakness #6 thresholds
       │
       │
       ▼
LOOP B v0.2 EXPANSION (depends on Dialogue Ledger schema [SHIPPED])
       │
       ├── C4 Deviation lifecycle ──┐
       │                            ├── C2 Why Library ──┐
       │                            │                    ├── Defensive reasoning at rec time
       │                            ▼                    ▼
       │                            C3 Calibration Journal
       │                            │
       │                            ▼
       │                       C1 6 v0.2 elicitation modes
       │                            │
       │                            ▼
       │                       C5 Protocol Meta-Learner
       │
       ▼
FRONTEND LAYER (depends on agency_dashboard JSON [SHIPPED] + above wirings)
       │
       ├── D1 Agency dashboard frontend
       ├── D2 Mechanism rotation graph artifact
       ├── D3 Uncertainty Panel UI
       └── D4 Loop B elicitation UI
                  │
                  ▼
                  A14 retirement-trigger public dashboard
                  Per-atom contribution dashboard
                  Becca's daily standup view
                  LUXY read-only access tier

PRE-LAUNCH LAYER (depends on most everything above)
       ├── F1 Pre-reg locked + published
       ├── F2 First rotation commitment registered
       ├── F3 Failure-mode runbook rehearsal
       ├── F4 Production deployment
       └── F5 PILOT LAUNCH

EXTERNAL TRACK (Chris-driven, runs parallel to all of above)
       ├── E1 LUXY stack discovery
       ├── E2 Pixel install
       ├── E3-E4 StackAdapt API + webhook
       ├── E5 Creative QA
       ├── E6 Reviewer engagement
       ├── E7 Baseline conversion rate
       └── E8 Factorial decision
```

### Critical-path items (block downstream)

1. **A1-A5 wirings** — block frontend (D1) from rendering meaningful data
2. **C4 Deviation lifecycle** — blocks C2 (Why Library) and Defensive reasoning
3. **B1 econml install** — blocks B5 (distribution-calibrated thresholds use M2 outputs)
4. **E1 LUXY stack discovery** — blocks E2 (LUXY adapter) and E5 (LUXY-specific webhook tests)
5. **E6 Reviewer engagement** — blocks F1 (pre-reg lock + publication)
6. **F1 Pre-reg published** — blocks F5 (launch decision; pre-reg must precede go-live)

### Items that DON'T block anything (can defer if needed)

- **Schema reconciliation audit** (75) — post-pilot follow-on
- **Drift-watch automated checks** (75) — Phase 2 governance
- **Multiple-comparison correction framework** (38) — needed at analysis time, not at build time
- **CI/CD pipeline extensions** (67) — exists in usable form
- **Sequential analysis early-stopping** (37) — can analyze fixed-N then add later

---

## Section 4 — Build efficiency order

Within dependency-allowed flexibility, group items that share infrastructure:

### Group 1 — Cascade wiring batch (Week 1, Days 1-5)
**Shared touch**: `_select_mechanisms`, `OutcomeHandler.process_outcome`, page intelligence pipeline

- A1: Online learning wiring
- A2: Taxonomy tagging wiring
- A3: Multi-horizon wiring
- A4: Page posture wiring
- A5: Construct-chain at orchestrator response

**Efficiency**: build a SINGLE integration test that exercises all 5 wirings simultaneously; commit per wiring but the integration test catches all-at-once.

### Group 2 — Methodology activation batch (Week 1-3)
**Shared touch**: external libraries + Neo4j writeback paths

- B1: econml install + M2 fit (3-4 days; gates on test infra)
- B2: M3 PyMC (5-7 days; substrate, activation gated on N)
- B3: M6 cross-family (4-6 days; Anthropic + OpenAI API keys)
- B4: Plant model + adjudicator (LONG POLE, 7-10 days)
- B5: Weakness #6 thresholds (4-5 days; depends on B1)

**Efficiency**: B1 + B3 can run in parallel (different lib stacks); B4 long pole runs Week 2-3; B5 starts Week 3 once B1 outputs flow.

### Group 3 — Loop B v0.2 batch (Week 2-3)
**Shared touch**: Dialogue Ledger service + elicitation pattern

- C4: Deviation lifecycle (5-7 days; foundational for C2)
- C2: Why Library (4-5 days; depends on C4)
- C3: Calibration Journal (4-5 days; parallel to C4)
- C1: 6 v0.2 elicitation modes (6-8 days; group by 2-3 per commit; parallel to others)
- C5: Protocol Meta-Learner (5-7 days; depends on C1+C3)

**Efficiency**: C4 ships first (others depend); C2 + C3 parallel after; C1 can start anytime (independent); C5 last.

### Group 4 — Frontend batch (Week 2-3)
**Shared touch**: dashboard framework, JSON consumption, vocabulary discipline

- D1: Agency dashboard frontend (6-8 days; framework first then sections)
- D2: Mechanism rotation graph artifact (3-4 days; embedded in D1)
- D3: Uncertainty Panel UI (3-4 days; embedded in D1)
- D4: Loop B elicitation UI (5-7 days; separate UI but same framework)

**Efficiency**: D1 framework first, then D2 + D3 + D4 as components.

### Group 5 — External integration receivers (Week 1-2 as info arrives)

- LUXY-specific adapter (E1 follow-up, 1-2 days)
- Pixel handler (E2 follow-up, 2-3 days)
- Power calc finalization (E7 follow-up, 0.5 day)
- Pre-reg amendments (E6 follow-up, 1 day if reviewer flags)

**Efficiency**: build as info lands; don't pre-build speculatively.

### Group 6 — Pre-launch artifacts (Week 3-4)

- F1, F2, F3, F4, F5 — sequenced per `PILOT_NEXT_MONTH_PLAN.md`

**Efficiency**: F1 + F2 parallel; F3 day-bound; F4 atomic; F5 the gate.

---

## Section 5 — Final ordered roadmap

Combining simulation priority + dependencies + efficiency. Numbered by build order (not by simulation rank — those are the priority anchors).

### Week 1 (Days 1-5)

**Wiring batch (Group 1)** — block frontend from rendering meaningful data:
1. A1 Cascade integration of online_learning_substrate (#15 in sim ranking)
2. A2 Cascade integration of mechanism_taxonomy_runtime (#28 in sim)
3. A3 Outcome-handler integration of multi_horizon_adjudication (#17 in sim)
4. A4 Page intelligence integration of page_attentional_posture (Tier 2 compounder)
5. A5 Construct-chain at orchestrator response (#9 in sim — high-impact differentiator)

**Methodology activation start (Group 2)**:
6. B1 start: econml install + initial CausalForestDML activation (#13 in sim)
7. B3 start (parallel): M6 Constitutional AI cross-family setup

**External kickoff (Group 5)**:
8. Chris drives E1, E2, E3, E5, E6, E7, E8 conversations

**Commits expected**: 6-8.

### Week 2 (Days 6-10)

**Methodology continuation**:
9. B1 finish: M2 production fit + cron job
10. B3 finish: M6 cross-family critic
11. B2 start: M3 PyMC substrate
12. B4 start: Plant model substrate (long pole)

**Loop B v0.2 start (Group 3)**:
13. C4: Deviation lifecycle (FOUNDATIONAL — others depend)

**External integration receivers (Group 5 follow-up)**:
14. LUXY-specific adapter (after E1 returns info)
15. Pixel handler client + server (after E2 install)

**Power calc + factorial decision lock**:
16. E7 follow-up: power calc finalized in pre-reg plan
17. E8 follow-up: factorial decision documented

**Commits expected**: 8-12.

### Week 3 (Days 11-15)

**Loop B v0.2 continuation**:
18. C2: Why Library (depends on C4)
19. C3: Calibration Journal (parallel)
20. C1 start: 2 v0.2 elicitation modes (kAFC + RankOrder)
21. C5 start: Protocol Meta-Learner substrate

**Methodology continuation**:
22. B2 finish: M3 PyMC activation gate
23. B4 continuation: Plant model adjudicator
24. B5 start: Weakness #6 thresholds (uses M2 outputs)

**Frontend start (Group 4)**:
25. D1 framework: agency dashboard skeleton
26. D2: Mechanism rotation graph artifact
27. D3: Uncertainty Panel UI

**Reviewer engagement + pre-reg lock**:
28. E6 follow-up: reviewer engagement → amendments → publication
29. F1: Pre-reg locked + published externally
30. F4: Production deployment

**Commits expected**: 10-14.

### Week 4 (Days 16-20)

**Final builds**:
31. C1 finish: remaining 4 v0.2 elicitation modes
32. C5 finish: Protocol Meta-Learner
33. B4 finish: Plant model adjudicator complete
34. B5 finish: Weakness #6 thresholds active
35. D1 finish: Agency dashboard frontend complete
36. D4: Loop B elicitation UI

**Defensive reasoning + supplementary frontend**:
37. **Defensive reasoning at recommendation time** (Why Library queried) — high-impact (#7 in sim)
38. **Cross-pollination Loop A↔B** — pairs validated claims across loops (#9 in sim)
39. **Multi-horizon brand-equity proxy** — beyond return-rate (#12 in sim)
40. **Per-archetype lift heterogeneity reporting** — analytical infrastructure (#11 in sim)
41. **A14 retirement-trigger public dashboard** — discipline visible
42. **Becca's daily standup view** — operational dashboard

**Pre-launch sequence**:
43. F2: First mechanism rotation commitment registered
44. F3: Failure-mode runbook rehearsal (Day 16)
45. Final smoke test (Day 17)
46. LUXY pre-launch sign-off (Day 18)
47. F5: Pilot launch decision (Day 19)
48. **PILOT LAUNCH** (Day 20 if green)

**Commits expected**: 12-15.

---

## Section 6 — Optional / post-pilot items (not in critical path)

Items that score well but don't block pilot launch:

- **Cohort-based non-stationary decision policies** (Layer 1) — Phase 2; needs cross-cohort data
- **Bayesian counterfactual at decision time** (Layer 1) — research-level; sequence after pilot
- **Mechanism interaction effects beyond marginal** (Layer 1) — material to scoring quality but adds complexity; Phase 2
- **Multiple-comparison correction framework** (Layer 4) — analysis-time only, not build-time
- **Sequential analysis with early-stopping** (Layer 4) — fixed-N is fine for pilot
- **LUXY's read-only access tier** (Layer 6) — operational permission; can ship any time
- **Drift-watch automated checks** (Layer 8) — pre-commit hook; nice-to-have governance
- **Schema reconciliation audit (Path B)** (Layer 8) — post-pilot debt cleanup

---

## Section 7 — Total scope + realistic capacity

**Build items total**: 45 net-new (counting wirings + methodology + Loop B + frontend + external receivers + supplementary frontend) over 4 weeks.

**Realistic commit volume**: 50-65 commits over 4 weeks (sustainable at 12-16 commits/week).

**Long-pole items**:
1. **B4 Plant model + adjudicator** (7-10 days) — start Week 2, finish Week 4
2. **D1 Agency dashboard frontend** (6-8 days) — framework Week 3, sections through Week 4
3. **B2 M3 PyMC** (5-7 days) — substrate only, activation gated on N

**Capacity buffer**: ~10-15% of capacity reserved for unexpected work (test fixes, integration surprises, reviewer amendments).

---

## Section 8 — Definition of "system at full power" (revised)

Per the table below: every item in the complete possibility set is either **shipped**, **wired**, **built**, **live**, **rehearsed**, or **decided** by end of month.

Items intentionally deferred (post-pilot):
- M3 PyMC ACTIVATION (substrate built, gated on N)
- Cohort-based non-stationary decision policies
- Bayesian counterfactual at decision time
- Mechanism interaction beyond marginal
- LUXY read-only access tier (operational)
- Drift-watch automated pre-commit hooks
- Schema reconciliation Path B audit

These are NOT in critical path; flag as Phase 2.

---

## Section 9 — Discipline anchors (unchanged from v1)

Throughout the month, on every commit:

1. Vocabulary discipline at every layer (cognitive, not programmatic-DSP)
2. A14 retirement triggers named at creation; tracked publicly via Prometheus
3. No LLM-composed prose at any rendering layer
4. Foundation §7 rule 11 non-negotiable: negative-outcome flowing before live spend
5. HMT discipline rule 12: every user assertion is HYPOTHESIS at write time
6. Verification before layering: Chris drives ≥1 verification touch per week
7. Per-commit antipattern audit (A1-A15)

---

## Section 10 — Reference

In load order every session:

1. `ADAM_AGENT_ORIENTATION.md`
2. `ADAM_THEORETICAL_FOUNDATION.md`
3. `ADAM_HUMAN_MACHINE_TEAMING_FOUNDATION.md`
4. `CLAUDE.md`
5. `memory/MEMORY.md`

For pilot:

6. `docs/PILOT_PRE_REGISTERED_ANALYSIS_PLAN.md`
7. `docs/PILOT_FAILURE_MODE_RUNBOOK.md`
8. `docs/PILOT_REVIEWER_METHODOLOGY_BRIEF.md`
9. `docs/PILOT_NEXT_MONTH_PLAN.md` — operational scaffold
10. **THIS DOCUMENT** — comprehensive build roadmap v2

---

## Section 11 — Executive summary (revised)

The original simulation scored 16 items. The complete possibility set is **75 items** across 8 layers. Re-running the simulation framework on the previously-omitted items reveals that **frontend/visualization items dominate the top of the ranking** (Mechanism rotation graph, Agency dashboard frontend, Uncertainty Panel UI, Becca's daily standup view), and **Deviation lifecycle was severely under-weighted** (now ranked #5 overall) because it powers the Loop B learning loop.

The revised 4-week build delivers **45 net-new items** (atop the 22 shipped this session): 5 cascade-layer wirings + 5 full-methodology activations + 5 Loop B v0.2 expansions + 4 frontend renderings + 6 supplementary frontend/analytics + 8 external integration receivers + 5 pre-launch artifacts + 7 high-impact items previously cut. Total: **~67 items live by end of month**.

Build order respects: simulation priority + dependency graph + build efficiency. Critical path: cascade wirings (Week 1) → methodology + Loop B foundational items (Week 2) → frontend + reviewer + pre-reg lock (Week 3) → final synthesis + rehearsal + LAUNCH (Week 4).

**Aggressive launch target end of May 2026; conservative early-to-mid June.** The discipline IS the differentiator. Build correct, ship honest, defer launch when any criterion is RED.

**HEAD: `e47e068`**. Onward.
