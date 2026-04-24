# Pilot Backlog — Tiered by Performance Impact

**Generated 2026-04-25.** Prioritization overlay on top of the committed
12-week pilot plan (`project_pilot_execution_plan.md`). Ranks remaining
work by whether it moves:

- **Pilot success criterion 1** — prediction quality (theory materializes
  at rates meaningfully better than correlational alternatives)
- **Pilot success criterion 2** — learning-loop closure (adjudication
  updates theory; failures visible and tracked)
- **Pilot success criterion 3** — client surface (interpretable,
  actionable report)

Tier 1 items move criteria 1 or 2. Tier 2 helps at the margin. Tier 3
is surface-only — mandatory for pilot ship, not for pilot performance.

**Status markers.** `✓` shipped · `↺` shipped with an A14 flag active
(see `a14_compromises.py`) · `·` open.

---

## Tier 1 — Active focus

### From the 12-week plan

1. **Graph-traversal helpers for inferential-chain attribution** (weeks 8-9)
   - Walk `ACTIVATES` / `CREATES_RECEPTIVITY_TO` / `REQUIRES` edges on
     the PsychologicalConstruct subgraph (migration 028) and weight
     each edge by its contribution to the residual on failing cells.
   - Retires `a14_compromises.INFERENTIAL_CHAIN_ATTRIBUTION_EMPTY`.
   - Closes the learning loop back from adjudication to theory
     refinement. Without this, every failing cell's residual stays as
     `unexplained` and the ILA has nothing specific to update on.
2. **Atom-level telemetry for `EvidenceTrace`** — *shipped in part*.
   - `chain_depth` populated from the traversal built in #10 when a
     chain_reader is injected (`7454143` / this commit).
   - `processing_depth_distribution` populated from optional
     `RealizedOutcomes.processing_depth_counts` (this commit).
   - `atom_activation_counts`, `source_diversity` — still open; requires
     atom-DAG telemetry plumbing that's out of scope for this slice.
   - Scope 3 plant-model refactor shipped: route fractions derive from
     expected processing-depth distributions per posture band composed
     with a P(convert|depth) proxy. `POSTURE_ONLY_ROUTE_SPLIT` is
     retired and **replaced by** `DEPTH_PRIOR_UNVALIDATED` — full
     retirement requires the two Tier 2 items below.
3. **task_23-32 DCIL ownership coupling**
   - Interim-look execution substrate for the plant model's
     `SequentialAdjudicator`. Without this, the learning loop never
     closes on any cadence shorter than horizon-complete.
   - Blocker flagged in the 2026-04-22/23 handoff; still open.
4. **#7 MV — 5 remaining Claude-scored page features** — *scoring substrate shipped this commit; storage + cascade wiring remain*
   - ✓ Scoring substrate: `adam/intelligence/pages/claude_feature_scoring.py`
     with `PageFeatureBundle` + `score_page_features()` producing all
     five in one Claude call (register, primary_metaphor_density +
     8-axis vector, goal_activation_profile across
     `GOAL_TAXONOMY` keys, temporal_horizon_induction,
     processing_fluency).
   - ✓ `ArticleObservation` extended with the 5 optional feature fields
     + confidence pairs, validators enforced.
   - · Neo4j migration 029 — add properties to Author / Publication /
     Section / Topic / Article nodes + indexes for the new features.
   - · Welford posterior updates in `entity_graph.py` Cypher — author /
     publication / section rollups analogous to attentional_posture.
   - · Cascade consumption in `page_edge_bridge.py` — shift matrices
     per feature that thread into the 20-dim bilateral activation.
   - · Ingestion pipeline wiring — call `score_page_features()` during
     article ingest so the fields populate.

### From the attention-inversion platform core (promoted into Tier 1)

5. **`blend_fit` creative parameterization**
   - Implication #1 of `project_attention_inversion_platform_core.md`.
   - Every creative carries a `blend_fit` parameter that scores how
     continuously the creative reads within the context it ships into.
     Drives selection pressure toward blend-and-fulfill creatives over
     attention-grabbing ones.
6. **Mechanism-taxonomy split: blend-compatible vs vigilance-activating**
   - Implication #2 of `project_attention_inversion_platform_core.md`.
   - Partitions the mechanism taxonomy so selection can be
     posture-conditional at the mechanism level, not just at the
     creative level. Blend-compatible mechanisms route through the
     autopilot path; vigilance-activating mechanisms route through the
     attention path (and carry the regret-correlation flag).

**Why 5 and 6 are in Tier 1.** Items 1-4 make the existing fitness
landscape cleaner. Items 5-6 reshape the landscape itself — they
change which creatives and mechanisms even enter selection. Under
Dawkins rule #11 from the theoretical foundation ("the fitness
function IS the ethics"), reshaping the landscape dominates cleaning
it. These two were originally scheduled post-front-end A/B/C; 2026-04-25
decision promoted them to active focus.

---

## Tier 2 — Meaningful but marginal (deferred until Tier 1 ships)

0. **ProcessingDepth external-prior validation** (retires `DEPTH_PRIOR_UNVALIDATED` slice 1 of 2)
   - Validate the 4-level ProcessingDepth enum thresholds (<1.0s /
     <2.5s / <5.0s / ≥5.0s) on ADAM pilot data. Check whether
     ADAM's cells cluster near the thresholds (threshold-sensitivity
     signal) or spread uniformly (thresholds arbitrary for our data).
   - Validate the per-posture-band `_EXPECTED_DEPTH_BY_POSTURE_BAND`
     distributions against observed per-cell distributions.
   - Validate the `_RELATIVE_P_CONVERT_BY_DEPTH` proxy against
     observed conversion rates per depth bucket.
   - Adjust priors / thresholds where they diverge.
0a. **Per-cell processing-depth priors** (retires `DEPTH_PRIOR_UNVALIDATED` slice 2 of 2)
   - Replace per-posture-band `_EXPECTED_DEPTH_BY_POSTURE_BAND` with
     cell-level priors informed by upstream page intelligence
     (Layer-11 processing-depth dimension).
   - Depends on: #7 MV features landing page-side processing-depth
     substrate (Tier 1 item 4).

1. **Publisher metadata trinity + bid-request categoricals**
   - Rest of #7 MV. Feeds the Claude-scored features from Tier 1
     item 4; without them the features run on weaker priors. Medium
     because single-article evidence still exercises the features.
2. **#6 theory-validation partition view**
   - Surface on top of `AdjudicatorOutput`. Makes theory failure
     visible to humans and the ILA. Doesn't itself predict better;
     the adjudicator data exists without it but no one is reading it.
3. **Task 32 rollback with hysteretic partition bands**
   - Safety: prevents bad rollbacks when cells straddle partition
     boundaries. Protects performance, doesn't add it.
4. **#1 full adjudication re-closure**
   - "Mechanical once adjudicator has rec-class track records" — closes
     an audit gap.
5. **Attention-inversion platform-core implications 3 and 5**
   - #3 — `processing_depth` as critical fitness-function instrument.
     Overlaps with Tier 1 item 2 (`processing_depth_distribution` on
     `EvidenceTrace`); whether this needs separate work depends on how
     item 2 lands.
   - #5 — regret signals as attention-route diagnostic. Feeds the
     adjudicator's route-split attribution; second-order.

---

## Tier 3 — Pilot ship surface / nice-to-have

1. **#5 PublicLabel governance**
   - Client-facing language for SPIES distributions. The machine is
     identical with or without it; matters for LUXY-facing report, not
     for internal performance.
2. **Pilot report pack (weeks 11-12)**
   - Pre-reg hashes + `ProjectedImpact` predicates + adjudicator
     outputs + theory-validation partition snapshot + **A14 active
     compromises block** (via `format_a14_compromises_for_report()`,
     already shipped in `e3a6ebd`).
3. **#3 conformal-wrapped cell reporting**
   - Conformal wrap is already live on the plant-model posterior; the
     "reporting replacing observation-count" work is a surface change.
4. **Deployment: migrations 023-028 + backfills**
   - Binary — must happen before live data flows, but doesn't improve
     any internal calculation.
   - Migrations to apply on Aura: 023 (page entities), 025 (CLT), 026
     (attentional_posture), 027 (RecommendationClass), 028
     (inferential-chain).
   - Scripts to run: `backfill_page_entities.py`,
     `verify_page_entities.py`.

---

## Cross-cutting dependencies (not slices; enable Tier 1)

- **External psychometrician hire.** 0.25 FTE, 12-20 weeks. Begin week
  1 for month 4-5 delivery. Retires the
  "HB without psychometric validation" compromise tracked in the pilot
  plan memory (not in the A14 runtime registry).
- **Attention-inversion implication #4 already partially shipped.**
  Attentional-posture dimension on page side landed with `ba39535`.
  Further surface (beyond weighting into the cascade) pending.

---

## Retirement map — Tier 1 items ↔ A14 flags

| Tier 1 item | A14 flag it retires |
|---|---|
| 1. Graph-traversal helpers | ✓ `INFERENTIAL_CHAIN_ATTRIBUTION_EMPTY` (shipped `7f27c95`) |
| 2. Scope 3 depth-conditioned routes | ↺ `POSTURE_ONLY_ROUTE_SPLIT` → replaced by `DEPTH_PRIOR_UNVALIDATED` (shipped this commit); full retirement needs Tier 2 items 0 + 0a |
| 3. task_23-32 coupling | (none — unblocks execution) |
| 4. #7 MV features | (none directly — feeds inputs; enables Tier 2 #0a) |
| 5. blend_fit | (none — new primitive) |
| 6. Mechanism taxonomy split | (none — new structure) |

Items 5 and 6 don't retire existing flags — they add architectural
primitives that were absent from the 12-week plan.
