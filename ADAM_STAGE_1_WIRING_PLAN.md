# ADAM Stage 1 Wiring Plan — Pre-Launch Execution

**Date:** 2026-04-15
**Path:** I (wire first, launch second)
**Goal:** Bring the highest-leverage stranded work online before the LUXY campaign build begins, so the campaign runs on the full designed inferential architecture rather than the current rump.
**Source passes:** B (page intelligence), C (atom triage + second DAG deep-dive), D (retargeting triage).
**Status:** Plan. Execution in progress.

## 1. Scope

Stage 1 is ~7 focused wiring items across two tracks. All items are *reading-plus-wiring* against code that already exists, not new design. None of them require a Becca GraphQL key.

### Track A — Atom wiring (touches `adam/atoms/dag.py`)

Extend the live DAG by importing 6 orphan atoms + coherence_optimization. The orchestration layer (`adam/atoms/orchestration/*`) stays stranded for Stage 1; we are not wiring the second DAG here.

| # | Atom | Level | Why |
|---|---|---|---|
| 1 | `MimeticDesireAtom` | L2 (construct-level) | Dominant luxury mechanism |
| 2 | `BrandPersonalityAtom` | L2 | Core primitive; feeds mechanism/copy/station |
| 3 | `NarrativeIdentityAtom` | L2 | Identity-framing for luxury |
| 4 | `RegretAnticipationAtom` | L2 | Critical for high-value decision framing |
| 5 | `AutonomyReactanceAtom` | L2 | Backfire prevention — load-bearing for luxury audiences |
| 6 | `CoherenceOptimizationAtom` | L3 (post-fusion) | Must ship with Stage 1 to resolve cross-atom conflicts the other 5 will produce |

**Rationale for "Stage 1 = 6 atoms, not all 16":** wiring the full 16 at once raises the risk of DAG topology errors and latency breaches. Stage 1 is the minimum-viable subset for the LUXY campaign. Stages 2-4 can wire the remaining 10 atoms post-launch, once the 14+6 DAG is running cleanly.

### Track B — Infrastructure wiring (touches multiple files)

1. **`learning_loop.py` → `outcome_handler.py` step 13** — Enhancement #33's therapeutic learning loop. Imports live `prior_manager`, `sequences`, `diagnostics`, `enums`, `learning` models. Single call site to add in `process_outcome`.
2. **`page_edge_bridge.compute_page_edge_shift()` → `bilateral_cascade.py`** — Pass B finding. Replaces "page modulates mechanism" with "page shifts buyer position before mechanism scoring." Requires reading the cascade's current page-modulation site first.
3. **`stackadapt_api_exporter.py` → callable service** — Pass D finding. Tier 1 Campaign Orchestrator. Needs a thin wrapper service and (optionally) a POST `/api/v1/campaigns/export` endpoint. Does NOT require Becca's GraphQL key — it produces JSON and CSV files that can be handed off OR fed to a GraphQL client once the key is available.
4. **`recalibration.py` → `main.py` startup + `outcome_handler.py` threshold trigger** — Operationally urgent. Prevents `composite_alignment` from drifting back to the Session 34-2 inversion.

## 2. Execution Order and Estimated Effort

Each item's risk, effort, and dependencies:

| # | Item | Risk | Effort | Depends on | Unblocks |
|---|---|---|---|---|---|
| B1 | learning_loop → outcome_handler | Low | 30 min | Nothing | Enhancement #33 learning path |
| B2 | page_edge_bridge → cascade | Med | 2-3 hours | Reading `bilateral_cascade.py` | Bargh-correct page intelligence |
| A1-A6 | 6 atoms + coherence_optimization → dag.py | Med-High | 3-4 hours | Reading `dag.py` DAG construction + MechanismActivation fusion | Full Stage 1 atom set |
| B3 | stackadapt_api_exporter → service | Low-Med | 2 hours | Reading the rest of `stackadapt_api_exporter.py` | Tier 1 campaign orchestration |
| B4 | recalibration → main.py + outcome_handler | Med | 1.5 hours | Reading `recalibration.py` | Operational drift prevention |

**Total estimated effort: 9-11 hours of focused work across ~4-6 sessions.** Stage 1 is tractable and can plausibly land in 2-3 days of focused work.

**Recommended execution order:**

1. **B1 first** — lowest risk, fastest, unblocks the Enhancement #33 learning loop immediately. Proof the wiring approach works before anything larger.
2. **B4 next** — operational urgency. Prevents silent quality drift. Short.
3. **B2** — the Bargh-correct page architecture. Medium effort; changes the cascade's mechanism-scoring semantics so it needs careful testing but is the highest-impact single change.
4. **A1-A6** — the atom wiring. Longest and most disruptive; should happen after the infrastructure items are in place so we have a clean substrate to add atoms into.
5. **B3** — Tier 1 campaign orchestrator service. Lowest urgency because it doesn't affect the decision path; it produces campaign configurations. Can happen last in Stage 1, or slip to Stage 1.5 if the session budget runs out.

## 3. What is explicitly NOT in Stage 1

- **The `adam/atoms/orchestration/` second DAG layer** (dag_executor + construct_dag + langgraph_feedback). 2,116 lines. Separate larger effort, Stage 3 or later.
- **The remaining 10 orphan atoms** (interoceptive_style, mimetic_desire variants, motivational_conflict, persuasion_pharmacology, query_order, relationship_intelligence, signal_credibility, strategic_awareness, strategic_timing, temporal_self, cooperative_framing). Stages 2-4.
- **`evolutionary_engine.py`** — the hypothesize-test-learn-at-speed system. Needs design sign-off on exploration-budget allocation before wiring. Stage 4.
- **`dimensionality_compressor`, `graph_embeddings`, `temporal_dynamics`, `tensor_decomposition`, `prospect_theory`, `annotation_quality`, `causal_mediation`** — Pass D findings. Stage 2-3 infrastructure improvements.

## 4. Commit Discipline

Each wiring item commits independently with:
- A commit message that names the item (e.g., *"fix: Wire Enhancement #33 learning_loop into outcome_handler step 13"*)
- A verification section in the message (what smoke test was run, what the expected behavior is)
- A reference to the audit pass that identified the orphan
- The `Co-Authored-By` line for traceability

No batch commits. Each wiring item is reviewable in isolation so rollback is surgical if anything breaks.

## 5. Success Criteria

Stage 1 is complete when:

- [ ] The 6 Stage 1 atoms are imported by `dag.py` and registered at the correct DAG levels.
- [ ] `MechanismActivationAtom` (already live) knows how to fuse evidence from the 6 new atoms (may need updates).
- [ ] `coherence_optimization` runs post-fusion and resolves any conflicts the new atoms produce.
- [ ] The end-to-end decision latency stays within the current budget (<50ms for the fast path, <500ms for the reasoning path).
- [ ] `outcome_handler.py`'s step 13 calls the Enhancement #33 learning loop.
- [ ] `bilateral_cascade.py` calls `compute_page_edge_shift()` and computes mechanism scores against the page-shifted alignment instead of applying page modulation as a post-hoc multiplier.
- [ ] `stackadapt_api_exporter` is callable via either a service or an API endpoint and produces a complete campaign package for LUXY.
- [ ] `recalibration` runs on a weekly schedule and can be triggered by edge-count threshold from `outcome_handler`.
- [ ] A synthetic end-to-end decision test passes against the expanded DAG.
- [ ] Prometheus metrics are updated to show the new decision_mode distribution, new atom activity, and recalibration run status.

## 6. What happens after Stage 1

Once Stage 1 lands, the campaign build can proceed on top of the expanded architecture. The LUXY campaign will run with:

- 20 atoms in the DAG (14 original + 6 Stage 1), including the Bargh-correct brand/identity/regret/reactance atoms.
- Page intelligence that shifts buyer position before mechanism scoring (not modulates afterward).
- Enhancement #33 learning loop closed from outcome through hierarchical priors.
- Automated recalibration preventing composite_alignment drift.
- A Tier 1 campaign orchestrator that produces complete StackAdapt packages.

Stages 2-4 continue after launch, each one adding more of the stranded capabilities without blocking the campaign.
