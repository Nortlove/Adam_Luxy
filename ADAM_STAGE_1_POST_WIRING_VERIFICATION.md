# ADAM Stage 1 Post-Wiring Verification

**Date:** 2026-04-15
**Context:** Two cheap confidence investigations run after Stage 1 wiring completed (B1, B4 Stage 1+2, B3, B2 Stage 1, A1-A6), before starting the LUXY campaign build.
**Scope:** Verify the wiring actually produces the expected behavior rather than just looking correct at the topological level.
**Outcome:** Both investigations passed; one real bug caught and fixed; DAG structural overhead measured and confirmed within budget.

---

## Investigation (a) — MechanismActivation consumes the 5 new construct atoms

**Question:** Do the 5 new Stage 1 construct atoms (MimeticDesire, BrandPersonality, NarrativeIdentity, RegretAnticipation, AutonomyReactance) actually contribute to mechanism scoring, or do they run but have their outputs silently ignored?

**Method:** Read `adam/atoms/core/mechanism_activation.py` end-to-end for `get_upstream()` calls, then verify the fusion loop that iterates them.

**Initial finding (wrong):** `MechanismActivationAtom` only called `atom_input.get_upstream("atom_X")` for 5 hardcoded atom names (user_state, personality_expression, regulatory_focus, construal_level, review_intelligence). My first conclusion was that BOTH the 5 existing Enhancement #35 auxiliary atoms AND my 5 Stage 1 construct atoms were silently ignored at the fusion level.

**Corrected finding:** There is a generic fusion loop at `mechanism_activation.py:1121-1159` that iterates an `_AUXILIARY_ATOMS` list, calls `get_upstream()` for each, extracts `secondary_assessments["mechanism_adjustments"]`, and applies each adjustment confidence-weighted to the mechanism scores. The Enhancement #35 auxiliary atoms ARE consumed — I misread the fusion pattern on first pass.

**Real gap:** My 5 new Stage 1 atoms produce output in the same shape (verified: `mimetic_desire_atom.py:279-297` sets both `secondary_assessments["mechanism_adjustments"]` and `overall_confidence`), but they were not in the `_AUXILIARY_ATOMS` list, so the fusion loop skipped them.

**Fix:** Added 5 new atom IDs to `_AUXILIARY_ATOMS` in `mechanism_activation.py:1128`. One-list extension. Committed as `d4499c2`.

**What this means end-to-end:**

- `atom_mimetic_desire` now influences mechanism scoring via the Girardian MODEL_TYPES taxonomy — load-bearing for luxury aspiration.
- `atom_brand_personality` now influences scoring via Aaker Brand Personality dimensions — critical for brand-voice alignment.
- `atom_narrative_identity` now influences scoring via McAdams narrative themes — identity-transformation framing.
- `atom_regret_anticipation` now influences scoring via the action/inaction regret asymmetry.
- `atom_autonomy_reactance` now influences scoring via the reactance coerciveness model — backfire prevention for luxury audiences.

`atom_coherence_optimization` is **not** in `_AUXILIARY_ATOMS` because it runs at DAG Level 3 AFTER `mechanism_activation`. Its consumption is a separate wiring path (inspect mechanism_activation output and adjust post-hoc) tracked as a Stage 2 follow-up in commit `7503e84`.

**Value of this investigation:** The bug it caught would have been silent. The A1-A6 wiring was syntactically correct — 20 atoms running, DAG topology valid, dependencies declared — but the 5 new atoms' outputs would never have reached the fusion step. Without this investigation, every decision made on top of the expanded DAG would have looked like it used the new atoms but actually ignored them. This is the same `CURRENT_V6_WEIGHTS`-pattern silent-failure we specifically worked to eliminate.

---

## Investigation (b) — DAG structural latency on the expanded 20-atom path

**Question:** Does the 20-atom DAG stay within the latency budget (<50ms fast path, <500ms reasoning path)?

**Method:** Build the DAG with stub blackboard/bridge, run the topological sort, measure orchestration overhead, and analyze the level structure to identify sequential-wait changes versus pure parallel-width changes.

**Results:**

| Metric | 14-atom (pre-Stage-1) | 20-atom (post-Stage-1) | Delta |
|---|---|---|---|
| Topological levels | 5 | 5 | — |
| Max parallel width | 9 (Level 1) | 14 (Level 1) | +5 |
| Level 0 atoms | 1 | 1 | — |
| Level 1 atoms | 9 | 14 | +5 |
| Level 2 atoms | 1 | 1 | — |
| Level 3 atoms | 2 | 3 | +1 (coherence_optimization) |
| Level 4 atoms | 1 | 1 | — |
| DAG build + topological sort (1000 runs) | ~30μs | ~30μs | — |

**Key finding: level count is unchanged.** The Stage 1 expansion widens Level 1 but does not introduce a new sequential level. Since each level runs its atoms in parallel and waits for all of them before proceeding, the sequential critical-path length is:

```
critical_path ≈ max(Level_1_atom_latency) + mechanism_activation_latency
               + max(Level_3_atom_latency) + ad_selection_latency
```

Widening Level 1 from 9 atoms to 14 does NOT increase the critical path unless the extra atoms have higher individual latency than the existing Level 1 maximum, OR unless async I/O concurrency hits a resource bottleneck (Neo4j connection pool, Claude rate limits, etc.).

**Orchestration cost is negligible.** The DAG build + topological sort takes about 30μs per invocation — not the bottleneck. Per-atom call overhead is similarly small.

**Residual risk: Neo4j connection-pool saturation.** If the pool is tuned to ~9 concurrent queries (matching the old Level 1 width), the extra 5 atoms at Level 1 will queue and add serialization latency. Mitigation options, ranked by effort:

1. **Enlarge the Neo4j connection pool** (config change). Smallest intervention if the pool is the bottleneck.
2. **Add per-atom result caching** (code change in each atom's Neo4j query path). Amortizes repeated queries within a request.
3. **Push some new atoms to a reasoning-path level** (dag.py change — move them from Level 1 to a new Level 1.5 that runs only when the orchestrator requests the reasoning path). Moves them off the <50ms budget.
4. **Defer atoms with high latency to Stage 2** (dag.py rollback — remove specific atoms from DEFAULT_DAG_NODES until their Neo4j queries are cached or optimized). Last resort.

**What this investigation does NOT measure:** actual Neo4j query latency. That requires a real stack with real data. First-run verification against a live Neo4j should monitor Level 1 wall-clock time and the fast-path total to see whether the structural analysis above holds under load.

---

## Net result after both investigations

1. **Stage 1 wiring is functionally correct** — the 5 new construct atoms will contribute to mechanism scoring (fix committed in `d4499c2`).
2. **Stage 1 latency impact is structural-zero** — no new sequential levels; only parallel-width increase at Level 1.
3. **The LUXY campaign build can proceed on the 20-atom DAG** with reasonable confidence that the wiring is producing real decision differences.

Residual items to monitor during LUXY launch:

- First-run Neo4j connection-pool utilization under the 14-wide Level 1.
- `composite_alignment` drift detection via the weekly `task_18_recalibration` (see commits `2c782fa`, `207efdc`, `44769db`).
- Page-edge-shift stashing on decision results (`result.context_intelligence["page_edge_shift"]`) for retrospective validation of whether the shift predictions match outcome patterns.
- Enhancement #33 learning-loop signals being generated but not yet consumed by a downstream `TherapeuticSequence` field (tracked as Stage 2 follow-up in commit `c1ca185`).
