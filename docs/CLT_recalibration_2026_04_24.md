# CLT Recalibration — 2026-04-24

**Status:** Applied. Pilot integrity fix, shipped before LUXY outcome claims.
**Branch:** `feature/hmt-dashboard`
**Scope:** Construal Level Theory effect sizes in ADAM's knowledge base, priors,
and Neo4j-durable research-domain backing.

## Summary

ADAM's operational effect size for Construal Level Theory (CLT) matching has
been recalibrated from the uncorrected meta-analytic Hedges' g = 0.475
(Trope & Liberman lineage; 111 studies) to the pre-registered d = 0.276.

The corrected value is ADAM's operational prior wherever CLT matching effects
propagate into priors, recommendation weighting, message-framing computation,
or effect-size reporting. The published value (0.475) is retained in each
touched location as `published_g` / `published_g_comment` for transparency.

## Why

Published effect sizes in social and behavioral psychology are systematically
inflated by publication bias, selective reporting, questionable research
practices, and file-drawer effects. CLT is no exception:

- **Schimmack (2022)** replicability-index analyses of CLT replications show
  the published effect is significantly inflated relative to the bias-adjusted
  estimate.
- **Maier et al. (2023)** RoBMA multiverse meta-analyses converge on roughly
  30–42% of the published CLT effect surviving publication-bias correction.
- **Pre-registered** CLT studies report d ≈ 0.276 — materially smaller than the
  meta-analytic pool but robust against the bias mechanisms above.

Operating on uncorrected priors in a pilot that makes claims to a paying
client is an integrity risk. A recalibration that we initiate before claims
are made is auditable. A recalibration forced by external critique after
claims are made is not.

## What changed

### New utility

- **`adam/core/learning/effect_size_correction.py`**
  `PublicationBiasCorrectedEffect` dataclass, `d_to_success_probability` mapping,
  `to_beta_prior` conversion, and pre-computed `CLT_MATCHING_EFFECT` constant
  holding the full provenance (published_g, corrected_d, correction_method,
  study count, citations). Reusable for the other 8 mechanisms post-pilot.

### Neo4j migration

- **`adam/infrastructure/neo4j/migrations/025_clt_recalibration_2026_04_24.cypher`**
  Updates `ResearchDomain {name: 'temporal_targeting'}` and
  `TemporalPattern {pattern_id: 'construal_awareness' | 'construal_decision'}`
  nodes originally seeded by migration 016. Each node gains a `published_g`
  field (for transparency), a `correction_method` field, and a timestamp.

### Source-file updates

Literal `effect_size = 0.475` references updated to `0.276` with provenance
comments pointing to `CLT_MATCHING_EFFECT`. Docstrings and in-code comments
updated to cite the pre-registered value and the correction rationale.

Affected files (full list):

- `adam/behavioral_analytics/knowledge/advertising_psychology_seeder.py`
- `adam/behavioral_analytics/classifiers/temporal_targeting.py`
- `adam/behavioral_analytics/models/advertising_psychology.py`
- `adam/behavioral_analytics/atom_interface.py`
- `adam/intelligence/graph_edge_service.py`
- `adam/workflows/holistic_decision_workflow.py`
- `adam/gradient_bridge/models/signals.py`
- `adam/dsp/strategy_generation.py`
- `adam/dsp/construct_registry.py`
- `need_detection/alignment_analyzer.py`
- `need_detection/__init__.py`

Migration 016 is left untouched (historical record); migration 025 is the
correction.

## What has NOT changed

- **`adam/atoms/core/construal_level.py`** — the atom's internal logic is
  threshold-based (composite_distance > 0.6 → abstract, < 0.4 → concrete)
  with confidence scaling. It does not use the effect-size coefficient
  internally, so no recalibration is needed in the atom itself. Downstream
  consumers of the atom's output do use CLT effect sizes to weight its
  influence on mechanism selection — those consumers receive corrected
  values via this migration.

- **The other 8 mechanism effect sizes** (regulatory_focus, social_proof,
  scarcity, authority, reciprocity, mimetic_desire, identity_construction,
  loss_aversion_framing). These almost certainly suffer similar publication-
  bias inflation. Recalibration is deferred to post-pilot using the same
  `PublicationBiasCorrectedEffect` utility and staged alongside external
  psychometric validation of the 27 dimensions.

## Composition with the pilot plan

The recalibrated CLT priors feed directly into weakness #4's RecommendationClass
plant-model priors (pilot weeks 5–7). Without this correction, plant-model
projections built on CLT would be roughly 42% overstated, violating the
fitness-function-is-ethics commitment (Foundation §2.5, rule 11): selection is
amoral, and if the reinforcement signal is trained on inflated priors, the
system will evolve toward whatever produces the inflated-prior-consistent
number. The recalibration is a prerequisite for honest adjudication.

## Alignment with discipline rules

- **Rule 2 (inferential vs correlational):** the corrected prior is a declared
  compromise with a named successor — it will be further refined as
  construct-specific publication-bias-corrected meta-analyses become
  available or pre-registered replications accumulate.
- **Rule 10 (academic bar):** the correction reports the published value
  alongside the corrected value and names the correction method; nothing
  hides behind a single number.
- **Rule 11 (fitness function is ethics):** uncorrected priors corrupt the
  reinforcement signal. Correcting them is architectural hygiene, not a
  marketing move.

## References

- Trope, Y. & Liberman, N. (2010). Construal level theory of psychological
  distance. *Psychological Review*, 117(2), 440–463.
- Schimmack, U. (2022). The replicability index (R-index).
- Maier, M., Bartoš, F., & Wagenmakers, E.-J. (2023). Robust Bayesian
  meta-analysis (RoBMA) in R.
- Chambers, C. (2019). *The Seven Deadly Sins of Psychology*. (On
  pre-registration as protection against publication bias.)
