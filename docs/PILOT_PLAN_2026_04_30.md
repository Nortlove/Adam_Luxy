# Pilot Plan (Adjusted) — 2026-04-30

**Supersedes** for "what to build next" purposes:
- `project_pilot_audit_2026_04_28.md` (the 13-must-have audit)
- `docs/PILOT_BACKLOG.md` (Tier 1 active focus)

**Built on top of** the inventory at `docs/COMPREHENSIVE_BUILD_INVENTORY.md` (1,579 lines) which catalogs what already exists across the 1,008-file codebase.

**Adjustment driver:** Substantial substrate is built. Of the 13 audit must-haves, ~9 have core substrate already shipped — the remaining work is INTEGRATION, not from-scratch building. The 6 wires shipped on 2026-04-29 closed orphan-wire gaps that overlapped several audit items.

**Original timeline:** 5-6 weeks → pilot launch 2026-06-02 to 2026-06-09
**Adjusted timeline:** ~3-4 weeks → pilot launch on or near **2026-05-22 to 2026-05-29**, with the 2-3 week long pole (Weakness #4 plant model adjudicator extension) the dominant constraint. Tighter timeline ONLY because most other items shrink from "build" to "wire/verify/install."

---

## Section 1 — Current state of the 13 must-have items

Each item below cites the existing module path and what specifically remains.

### Item 1 — Orchestrator wiring callsite + contribution-data ingestion producer
**Substrate:** `adam/intelligence/per_atom_contribution.py` (561 LOC) + `per_atom_contribution_ingestion.py` (196 LOC)
**Wiring confirmed:** `outcome_handler.py:447-450` imports `per_atom_contribution_ingestion` — outcome-time producer is wired ✓
**Remaining:** verify the orchestrator-side READ path consumes per-atom contribution; smoke-test with real outcomes
**Effort estimate:** 0.5 day (verification + integration test)

### Item 2 — M4 Aura migration + smoke test + A14 scaffolding
**Substrate:** M4 OPE shipped (`adam/intelligence/ope.py` 663 LOC) + `policy_gate()` + `scripts/run_policy_gate.py` (shipped 2026-04-29)
**A14 scaffolding:** `recommendation_class/a14_compromises.py` + `format_a14_compromises_for_report()` ✓
**Remaining:** Aura migrations 023-028 application + end-to-end smoke test
**Effort estimate:** 1 day (migration script + smoke run + verification)

### Item 3 — blend_fit creative parameterization
**Substrate:** `adam/intelligence/blend_fit.py` (413 LOC) — `compute_blend_fit()` + `BlendFitDecomposition` ✓
**Remaining (per `PILOT_BACKLOG.md` Tier 1 #5):**
- Creative-side feature scorer (mirror of `pages/claude_feature_scoring.py`)
- Selection integration — mechanism selector calls `compute_blend_fit` to weight creative candidates
- Learned weights — post-pilot calibration
**Effort estimate:** 2-3 days (scorer + selection wire; calibration deferred post-pilot)

### Item 4 — Mechanism-taxonomy split (blend-compatible vs vigilance-activating)
**Substrate:** `adam/intelligence/mechanism_taxonomy.py` (375 LOC) + `mechanism_taxonomy_runtime.py` (315) ✓
**Cascade integration:** Already used in cascade via `processing_depth_router.gate_mechanism_scores` (the C2 gate). F5 `blend_vigilance_weighting.py` (139 LOC) wired in cascade.
**Remaining (per `PILOT_BACKLOG.md` Tier 1 #6):**
- Selection integration — `mechanism_selector` consults taxonomy by posture band (currently per posture only, not per mechanism category)
- Adjudicator regret diagnostic — pair `regret_correlation_prior` with observed regret
- Plant-model route-split refinement
**Effort estimate:** 2-3 days

### Item 5 — M2 Causal Forests activation
**Substrate:** `adam/intelligence/causal_forest.py` (483 LOC) + `Task 35` causal forest weekly fit (shipped 2026-04-29 commit `ec8c489`)
**Remaining:**
- Install `econml` library on production environment (verified NOT installed locally — `python3 -c "import econml"` fails)
- Run Task 35 against Aura first time + diagnostics
- Confirm CATE writes to Neo4j
**Effort estimate:** 1 day (lib install + first run + verification)

### Item 6 — attentional_posture page-side dimension expansion
**Substrate:** `adam/intelligence/page_attentional_posture_substrate.py` (398 LOC) — `PageAttentionalPostureAccumulator` + `categorize_posture()` ✓
**Cascade integration:** Read by `outcome_handler.py:478-505` (outcome side). NOT yet read by cascade at decision time.
**Remaining:**
- Wire `categorize_posture(page_profile.attentional_posture, page_profile.attentional_posture_confidence)` into cascade C2 router as new input (this was prepared but not committed in this session — pending the proper survey)
- Expand observation accumulation (per audit "expansion needed")
**Effort estimate:** 1-2 days

### Item 7 — processing_depth fitness-function wiring verification + completion
**Substrate:** `adam/intelligence/processing_depth_router.py` (314 LOC) — `predict_processing_depth_heuristic` + fluency floor (shipped 2026-04-29 commit `329bc8b`)
**Producer side:** `adam/retargeting/engines/processing_depth.py` (179 LOC) — POST-impression depth from viewability seconds
**Remaining:**
- Verify producer wiring: where do `processing_depth_distribution` observations come from at outcome time?
- Per-cell processing-depth priors (Tier 2 #0a in backlog) — replace `_EXPECTED_DEPTH_BY_POSTURE_BAND` with cell-level priors
**Effort estimate:** 1-2 days for producer verification; per-cell priors defer to pilot data calibration

### Item 8 — M3 Hierarchical Bayes activation
**Substrate:** `adam/intelligence/hierarchical_bayes.py` (512 LOC) + `Task 34` nightly HB refit (shipped 2026-04-29 commit `ec8c489`)
**Remaining:**
- Install `pymc` + `numpyro` on production (verified NOT installed locally)
- Run Task 34 against Aura first time + diagnostics
- Verify BayesianPrior nodes update + cascade L2 reads them
**Effort estimate:** 1 day (lib install + first run + verification)

### Item 9 — M6 CAI activation
**Substrate (5 modules):**
- `argument_constitution.py` (485) — source-of-truth text
- `constitutional_loop.py` (523) — generate→critique→revise loop
- `cai_cross_family_critic.py` (616) — cross-family critique
- `argument_ranking.py` (165) — `rank_variants_via_claude` production gate (B4)
- `argument_cache.py` (294) — cascade hot-path cache
**Wiring confirmed:** `output/copy_generation/service.py:439` consumes `rank_variants_via_claude` ✓
**Remaining:**
- Verify cascade → copy_generation → CAI ranking flow end-to-end
- Run B3 cache pre-warm
**Effort estimate:** 1 day (verification + smoke test)

### Item 10 — Weakness #4 outcome-observation wiring (slice 5 + plant model + adjudicator extension) — LONG POLE
**Substrate:**
- `recommendation_class/plant_model.py` ✓
- `recommendation_class/adjudicator.py` (uses `PlantModel` at line 315) ✓
- 4 of 5 scaffolding slices done per audit
**Remaining:**
- Slice 5 of scaffolding
- Plant model adjudicator extension (the 2-3 week core)
- Per-cell calibration on real outcomes
**Effort estimate:** 2-3 weeks — **DOMINATES THE TIMELINE**

### Item 11 — Weakness #6 convergence thresholds + regret-weighted rank
**Substrate:** unclear — needs grep
**Remaining:** Distribution-calibrated thresholds + regret-weighted ranking
**Effort estimate:** 2-3 days

### Item 12 — Weakness #3 observation-count proxy fix (depends on Item 7)
**Substrate:** unclear — needs grep
**Remaining:** Replace observation-count with processing-depth-weighted volume
**Effort estimate:** 1 day after Item 7 lands

### Item 13 — Weakness #1 re-adjudicate pending Outcome nodes
**Substrate:** `causal_adjudicator.py` (919 LOC) ✓ + Task 29.6 horizon adjudicator scheduled ✓
**Remaining:** Free rider on Item 10 — runs once plant model complete
**Effort estimate:** 0.5 day

### Item 14 — Weakness #2 non-atomic Neo4j writes (15-minute fix)
**Substrate:** wherever multi-statement Cypher is used without `tx.run` transaction wrapping
**Remaining:** Find + wrap
**Effort estimate:** 0.5 day (grep + fix)

### Item 15 — Per-atom contribution dashboard + A14 dashboard
**Substrate:** `format_a14_compromises_for_report()` ✓ exists in `recommendation_class/__init__.py`
**Remaining:**
- Per-atom contribution dashboard endpoint + UI
- A14 dashboard endpoint surfacing active flags
**Effort estimate:** 1-2 days

### Item 16 — Deployment to Railway + Becca handoff
**Substrate:** Railway + Aura already running per memory; needs redeploy with April 15-16 changes
**Remaining:**
- Apply migrations 023-028 to Aura
- Run backfill scripts (`backfill_page_entities.py`, `verify_page_entities.py`)
- Redeploy + StackAdapt token activation + Becca handoff
**Effort estimate:** 1 day

---

## Section 2 — Total adjusted effort

| Phase | Items | Effort |
|---|---|---:|
| **Phase A — Lib install + first runs** (M2 + M3 unblocked) | 5, 8 | 2 days |
| **Phase B — Verify + smoke-test existing wires** | 1, 9 | 1.5 days |
| **Phase C — Extend posture/depth into cascade** | 6, 7 | 3 days |
| **Phase D — Quick fixes** | 11, 12, 14 | 4 days |
| **Phase E — Tier 1 selection wires** | 3, 4 | 5 days |
| **Phase F — Operational** | 2, 16 | 2 days |
| **Phase G — Dashboard surface** | 15 | 2 days |
| **Phase H — Long pole (parallel where possible)** | 10, 13 | 14-21 days |
| **Total (sequential)** | | 33-40 days |
| **Total (Phase H runs in parallel from Day 1)** | | **~21-25 days** |

Realistic pilot launch: **2026-05-22 to 2026-05-29** (vs original 2026-06-02 to 2026-06-09).

The compression is real but conditional on (a) econml + pymc install going smoothly, (b) Aura migrations applying clean, (c) the 6 cascade wires shipped 2026-04-29 actually firing correctly under real traffic.

---

## Section 3 — Today's session-start alignment proposal

Per the session-start alignment cadence memory: **propose plan + cite existing code + name gap + how we know we're done.**

### What I think we're doing today

**Phase A — unblock M2 + M3 by getting econml + pymc + numpyro installed and running Tasks 34/35 against Aura for the first time.**

This is the cheapest item with the highest leverage. Tasks 34 and 35 were SHIPPED yesterday but they raise `LibsMissingError` until the libs install. Without them running, `BayesianPrior` nodes stay frozen and the cascade L2 keeps reading stale priors.

### What existing infrastructure covers this

- `adam/intelligence/hierarchical_bayes.py` (512 LOC) — `run_nightly_hierarchical_refit()` ready
- `adam/intelligence/causal_forest.py` (483 LOC) — `run_weekly_causal_forest_fit()` ready
- `adam/intelligence/daily/task_34_hierarchical_bayes_refit.py` — scheduled
- `adam/intelligence/daily/task_35_causal_forest_fit.py` — scheduled (with cell-discovery)
- `requirements.txt` (or equivalent) — verify it pins compatible versions

### What I think the gap is

1. Verify libs are listed in the dependency manifest (requirements.txt or pyproject.toml)
2. If not, add them with version pins from the canonical handoff
3. Install locally
4. Run Task 34 + Task 35 once manually against Aura to verify they work end-to-end
5. Address any schema/missing-prereq issues that surface

### What's NOT in this session

- Plant model long-pole work (Item 10) — separate track
- Cascade modulation chain extensions (we just did that yesterday)
- Front-end work
- Strategic discussion (route to Claude proper if it comes up)

### How we'll know we're done

- `python3 -c "import pymc, numpyro, econml; print('all libs present')"` succeeds
- Manually run Task 34 — observes BayesianPrior nodes update on Aura, `r_hat_max < 1.05`, no divergences
- Manually run Task 35 — observes CATE writes to Neo4j for at least one cell with sufficient sample size
- Cascade L2 query confirms it reads the new posteriors

### Confirm or correct

Before I move at velocity:
- Is Phase A (M2/M3 lib install + first runs) the right starting point, or do you want to start somewhere else (e.g., the long-pole plant-model track, the deployment Item 16, or one of the cascade extension items 6/7)?
- Are M3 (PyMC + NumPyro) and M2 (econml) the canonical libraries we want, or should I check the handoff for alternatives?
- Do we have Aura write access from this environment, or does the first-run need to happen in the Railway deploy environment with the production credentials?

Once you confirm or redirect, I move at velocity per the autonomous-execution memory.
