# Maximizer/Satisficer Fragmentation Audit

**Slice ID:** A.1.0
**Session:** 2026-05-07 (continuation; A.0 → A.1.0 → A.1)
**Predecessor:** `cf41115` (A.0 — `docs/MINDSET_COVERAGE_GAP_ASSESSMENT_2026_05_07.md`)
**Audit type:** Read-only inspection (S2 retargeting audit precedent — commit `48f7e4e`)
**Branch:** `feature/hmt-dashboard`

---

## §1 Executive Summary

The maximizer/satisficer construct is fragmented across **eight distinct named forms** in 30 files. Headline counts:

| Variant | Hits | Files | Role |
|---|---:|---:|---|
| `decision_maximizer` | 19 | 8 | dominant Python-identifier form (2 full ConstructDefinition entries) |
| `maximizer_tendency` | 7 | 4 | second form (1 dataclass field, 3 service-layer dicts) |
| `MAXIMIZING_TENDENCY` / `maximizing_tendency` | 1 | 1 | cold_start enum value |
| `dm_maximizer` | 1 | 1 | construct_taxonomy.py `Domain 8` member |
| `dm_satisficer` | 1 | 1 | construct_taxonomy.py `Domain 8` member (sibling of `dm_maximizer`) |
| `decision_style` (Neo4j NODE-NAME property) | 1 | 1 | migration `005` `:PersonalityDimension` seed |
| `decision_style` (CATEGORICAL-BUCKET variable name) | **683** (separate namespace; do NOT conflate) | many | system-level decision-strategy categorical (NOT the bipolar trait) |
| `"satisficing"` / `"maximizing"` (categorical-value strings) | 42 + 25 = 67 | many | values of the categorical-bucket variable above |

**Critical disambiguation surfaced by audit:** the string `decision_style` is used in TWO semantically-different namespaces.
1. As the `name` property of the `:PersonalityDimension {dimension_id: 'dim_cog_decision_style'}` Neo4j node — single bipolar trait dimension (Schwartz-grade construct).
2. As a **categorical-bucket variable** holding values like `"system1_intuitive"`, `"system2_deliberate"`, `"satisficing"`, `"maximizing"`, `"gut_instinct"`, `"recognition_based"`, `"affect_driven"`, `"deliberative_reflective"`, `"analytical_systematic"`, etc. — a domain-typed enum-style variable used in 600+ call sites across `adam/demo/`, `adam/intelligence/`, `adam/orchestrator/`, `adam/workflows/`. THIS NAMESPACE IS NOT THE BIPOLAR TRAIT and **must not be renamed by A.1**.

**Critical structural finding:** `dim_cog_decision_style` Neo4j node has **0 READ_BY sites** in the codebase. The construct is queried/used everywhere via the *Python-identifier* names (`decision_maximizer`, `maximizer_tendency`, `dm_maximizer`/`dm_satisficer`) — not via Neo4j queries against the seeded node. The Neo4j seed is **dormant**: it persists the academic dimension but no live code path retrieves it.

**Recommended A.1 strategy** (detailed in §8): consolidate Python-identifier sites to canonical `maximizer_tendency`. Keep the Neo4j `dimension_id` stable (low blast radius — 0 readers means renaming is wasted churn). Add Schwartz academic_grounding + scale_anchor properties to the seeded node. Leave the 683 categorical-bucket `decision_style` sites alone (separate namespace). Leave `construct_taxonomy.py:653-654` bipolar `dm_maximizer`/`dm_satisficer` split intact (intentional academic-faithful bipolar representation).

**Test surface for A.1:** 1 file (`tests/test_e2e_integration.py`), 1 hit, and that hit is on the **categorical-bucket** `decision_style` namespace — not the bipolar trait — so A.1 may have **zero test-file changes** if the consolidation is scoped per §8.

---

## §2 Pass 1 — Migration 005 schema for `dim_cog_decision_style`

**File:** `adam/infrastructure/neo4j/migrations/005_seed_personality_dimensions.cypher`

**Lines 147–159 (full MERGE block, verbatim):**

```cypher
MERGE (d:PersonalityDimension {dimension_id: 'dim_cog_decision_style'})
SET d.name = 'decision_style',
    d.full_name = 'Decision Style',
    d.domain = 'cognitive_style',
    d.dimension_type = 'style',
    d.description = 'Preference for maximizing (finding the best option) vs satisficing (finding a good enough option).',
    d.low_description = 'Satisficer - accepts good enough options',
    d.high_description = 'Maximizer - seeks the optimal choice',
    d.measurement_method = 'behavioral_inference',
    d.ad_relevance = 'Maximizers need comparison information. Satisficers respond to quick, confident recommendations.',
    d.population_mean = 0.5,
    d.population_std = 0.15,
    d.created_at = datetime();
```

**Property list (12 properties + key):**

| # | Property | Value | Notes |
|---|---|---|---|
| key | `dimension_id` | `'dim_cog_decision_style'` | UNIQUE constraint per migration `001` |
| 1 | `name` | `'decision_style'` | INDEXED per migration `002:54` — collides lexically with the categorical-bucket variable name (see §1 disambiguation) |
| 2 | `full_name` | `'Decision Style'` | display |
| 3 | `domain` | `'cognitive_style'` | INDEXED per migration `002:57` |
| 4 | `dimension_type` | `'style'` | INDEXED per migration `002:60` |
| 5 | `description` | `'Preference for maximizing (finding the best option) vs satisficing (finding a good enough option).'` | bipolar definition |
| 6 | `low_description` | `'Satisficer - accepts good enough options'` | low-pole anchor |
| 7 | `high_description` | `'Maximizer - seeks the optimal choice'` | high-pole anchor |
| 8 | `measurement_method` | `'behavioral_inference'` | inference mode tag |
| 9 | `ad_relevance` | `'Maximizers need comparison information. Satisficers respond to quick, confident recommendations.'` | actionable copy |
| 10 | `population_mean` | `0.5` | Beta prior mean |
| 11 | `population_std` | `0.15` | Beta prior std |
| 12 | `created_at` | `datetime()` | timestamp |

**Constraints / indexes referencing PersonalityDimension** (from Pass 1b):
- `001_core_constraints.cypher:20` — `FOR (d:PersonalityDimension) REQUIRE d.dimension_id IS UNIQUE` (prevents duplicate seeds)
- `002_core_indexes.cypher:54` — `FOR (d:PersonalityDimension) ON (d.name)` (text index on name)
- `002_core_indexes.cypher:57` — `FOR (d:PersonalityDimension) ON (d.domain)`
- `002_core_indexes.cypher:60` — `FOR (d:PersonalityDimension) ON (d.dimension_type)`

**Properties absent from current schema** (per Schwartz et al. 2002 grounding requirement):
- `academic_grounding` — Schwartz citation not present
- `scale_min`, `scale_max` — explicit numeric range absent
- `scale_anchor_low`, `scale_anchor_high` — labeled anchors absent (low_description/high_description partially serve this role but are not the canonical anchor properties)
- `added_in` — slice-ID provenance absent

A.1 must add these without breaking the existing 12 properties.

---

## §3 Pass 2 — `dim_cog_decision_style` ID cross-references

Total hits: **3** (across `adam/`, `tests/`, `docs/`, `scripts/`, `artifacts/`).

| File | Line | Category | Snippet |
|---|---:|---|---|
| `adam/infrastructure/neo4j/migrations/005_seed_personality_dimensions.cypher` | 147 | **WRITE_BY** | `MERGE (d:PersonalityDimension {dimension_id: 'dim_cog_decision_style'})` |
| `docs/MEMORY.md` | 182 | **REFERENCE** (descriptive — Q7 surface in EVE block I authored prior turn) | `1. Complete list of 7 fragmentation sites with current local naming (recorded in Q7 surface for reference: ...005_seed_personality_dimensions.cypher:148 decision_style / dim_cog_decision_style;...)` |
| `docs/MEMORY.md` | 183 | **REFERENCE** (descriptive — Q7 surface in EVE block I authored prior turn) | `2. Migration 005's dim_cog_decision_style schema handling — keep stable dimension_id with new name, or rename dimension_id too...` |

**READ_BY sites: 0.** No code in `adam/`, `tests/`, or `scripts/` queries by `dim_cog_decision_style` as a string. The Neo4j seed is dormant from a code-consumer perspective.

**Implication for A.1:** renaming the `dimension_id` would touch zero Python call sites. The dimension_id-rename blast radius is purely (a) the seed migration itself, and (b) any external Neo4j operator queries that currently use the ID interactively (unobservable from this audit; could exist in cypher notebooks / Neo4j Browser saved queries / external tooling).

---

## §4 Pass 3 — Named-variant cross-references

### §4.1 `decision_maximizer` (19 hits, 8 files — the dominant variant)

| File | Line | Class | Snippet |
|---|---:|---|---|
| `adam/intelligence/unified_construct_integration.py` | 152 | (d) string-literal-key | `"decision_maximizer": {` |
| `adam/intelligence/enhanced_review_analyzer.py` | 172 | (d) list-of-construct-keys | `"decision_maximizer", "decision_regret", "decision_overload",` |
| `adam/intelligence/enhanced_review_analyzer.py` | 320 | (a) construct-definition body | `"decision_maximizer": {  # Maximizer vs Satisficer` |
| `adam/intelligence/enhanced_review_analyzer.py` | 923 | (d) string-literal-key in dict | `"decision_maximizer": 0.20,` |
| `adam/intelligence/enhanced_review_analyzer.py` | 951 | (d) string-literal-key in dict | `"decision_maximizer": 0.25,` |
| `adam/intelligence/knowledge_graph/populate_psychological_graph.py` | 320 | (d) related_constructs key | `related_constructs={"info_holistic_analytic": 0.4, "decision_maximizer": 0.35},` |
| `adam/intelligence/knowledge_graph/populate_psychological_graph.py` | 397 | (d) related_constructs key | `related_constructs={"decision_maximizer": -0.35, "cognitive_psp": -0.25},` |
| `adam/intelligence/knowledge_graph/populate_psychological_graph.py` | 463 | (a) ConstructDefinition body | `"decision_maximizer": ConstructDefinition(` |
| `adam/intelligence/knowledge_graph/populate_psychological_graph.py` | 464 | (a) ConstructDefinition `id=` | `id="decision_maximizer",` |
| `adam/intelligence/knowledge_graph/populate_psychological_graph.py` | 491 | (d) related_constructs key | `related_constructs={"decision_maximizer": 0.4, ...}` |
| `adam/intelligence/knowledge_graph/populate_psychological_graph.py` | 506 | (d) related_constructs key | `related_constructs={"decision_maximizer": 0.35, ...}` |
| `adam/intelligence/knowledge_graph/populate_psychological_graph.py` | 712 | (d) related_constructs key | `related_constructs={"decision_maximizer": 0.4, ...}` |
| `adam/intelligence/knowledge_graph/populate_psychological_graph.py` | 744 | (d) related_constructs key | `related_constructs={"decision_maximizer": 0.3, ...}` |
| `adam/intelligence/knowledge_graph/persuasion_susceptibility_graph.py` | 508 | (d) string-literal-key in dict | `"decision_maximizer": 0.50,  # Maximizers have higher tolerance` |
| `adam/intelligence/knowledge_graph/persuasion_susceptibility_graph.py` | 556 | (d) string-literal-key in dict | `"decision_maximizer": 0.35,  # Maximizers compare prices` |
| `adam/corpus/pipeline/liwc_scorer.py` | 279 | (d) string-literal-key in dict | `"decision_maximizer": round(maximizer, 3),` |
| `adam/data/amazon/enhanced_ingestion.py` | 100 | (c) dataclass field | `decision_maximizer: float = 0.0` |
| `adam/data/amazon/enhanced_ingestion.py` | 323 | (d) string-literal mapping | `"decision_maximizer": "decision_maximizer",` |
| `adam/data/amazon/enhanced_ingestion.py` | 396 | (c) attribute access | `analysis.motivation_achievement + analysis.decision_maximizer` |

### §4.2 `maximizer_tendency` (7 hits, 4 files)

| File | Line | Class | Snippet |
|---|---:|---|---|
| `adam/intelligence/unified_psychological_intelligence.py` | 197 | (c) dataclass field | `maximizer_tendency: float = 0.5` |
| `adam/intelligence/unified_psychological_intelligence.py` | 1207 | (d) string-literal-key in dict | `"maximizer_tendency": 0.25,` |
| `adam/platform/constructs/service.py` | 95 | (d) string-literal-key in dict | `"maximizer_tendency": 0.65,` |
| `adam/platform/constructs/service.py` | 115 | (d) string-literal-key in dict | `"maximizer_tendency": 0.78,` |
| `adam/platform/constructs/service.py` | 269 | (d) tuple mapping | `"maximizer_tendency": ("decision_making", "maximizer_tendency"),` |
| `adam/platform/constructs/models.py` | 193 | (c) dataclass field | `maximizer_tendency: ConstructScore = Field(default_factory=ConstructScore)` |
| `adam/platform/constructs/models.py` | 209 | (c) attribute access | `"comparison_tools": self.maximizer_tendency.value > 0.6,` |

### §4.3 `MAXIMIZING_TENDENCY` / `maximizing_tendency` (1 hit, 1 file)

| File | Line | Class | Snippet |
|---|---:|---|---|
| `adam/cold_start/models/enums.py` | 147 | (c) enum member + value | `MAXIMIZING_TENDENCY = "maximizing_tendency"` |

### §4.4 `dm_maximizer` (1 hit, 1 file)

| File | Line | Class | Snippet |
|---|---:|---|---|
| `adam/intelligence/construct_taxonomy.py` | 653 | (d) construct dict key + (a) display name | `"dm_maximizer": _c("dm_maximizer", _D8, "Maximizer Tendency", temporal_stability=_TR, inference_tractability=_HI),` |

### §4.5 `dm_satisficer` (1 hit, 1 file)

| File | Line | Class | Snippet |
|---|---:|---|---|
| `adam/intelligence/construct_taxonomy.py` | 654 | (d) construct dict key + (a) display name | `"dm_satisficer": _c("dm_satisficer", _D8, "Satisficer Tendency", temporal_stability=_TR, inference_tractability=_HI),` |

### §4.6 `"Maximizer Tendency"` / `"Satisficer Tendency"` (display strings — 1 each, both at construct_taxonomy.py:653-654, already counted in §4.4/§4.5)

### §4.7 `decision_style` — categorical-bucket variable (683 hits — DO NOT TOUCH)

These are NOT the bipolar trait. They're a categorical-bucket variable used in the system1/system2/maximizing/satisficing/etc. namespace. Sample to disambiguate:

```python
# adam/demo/stackadapt_demo.py:825-829 — categorical assignment
decision_style = "system2_deliberate"
decision_style = "system1_intuitive"
decision_style = "mixed"

# adam/demo/api.py:5056 — categorical lookup
decision_style, confidence = priors.get_dominant_decision_style(archetype)

# adam/intelligence/atom_intelligence_injector.py:746 — archetype-to-style mapping
"pragmatist": "satisficing",
```

This is a **separate namespace** from the bipolar trait. **Do NOT rename in A.1.** Documented in §1 disambiguation.

### §4.8 `"satisficing"` / `"maximizing"` (categorical-value strings — 42 + 25 hits — DO NOT TOUCH for trait-rename purposes)

These are values of the categorical-bucket variable above, not occurrences of the bipolar trait. Examples:

```python
# adam/intelligence/empirical_psychology_framework.py:714,772 — DecisionStyleDimension entries
"satisficing": DecisionStyleDimension(name="satisficing", ...)
"maximizing": DecisionStyleDimension(name="maximizing", ...)

# adam/atoms/core/construct_resolver.py:71,75 — categorical weights
"satisficing": 0.40,
"maximizing": 0.95,

# adam/dsp/models.py:271 — DSP enum
MAXIMIZING = "maximizing"
```

These belong to the categorical-bucket namespace per §4.7. **Do NOT rename in A.1.** A separate refactor (out of scope) could consolidate the categorical-bucket namespace if needed.

### §4.9 `decisional_maximization` (0 hits) — Schwartz subscale not implemented

### §4.10 `alternative_search` (1 hit, 1 file — likely UNRELATED)

| File | Line | Class | Snippet |
|---|---:|---|---|
| `adam/atoms/core/query_order.py` | 94 | (f) false positive — `alternative_search` here is a query-strategy enum value, NOT the Schwartz "alternative search" subscale | `"alternative_search": {` |

Audit excludes this site from rename scope.

### §4.11 `decision_difficulty` (0 hits) — Schwartz subscale not implemented

---

## §5 Pass 4 — Test surface

Single test file matched: `tests/test_e2e_integration.py`

| File | Hit count | What the hit asserts |
|---|---:|---|
| `tests/test_e2e_integration.py` | 1 (line 248) | Asserts a model fallback returns a key named `decision_style` in its prediction dict — this is the **categorical-bucket variable** namespace (per §4.7), NOT the bipolar trait. The test is testing structural completeness of the model output, not the trait. **Do NOT modify in A.1.** |

**Test-update count for A.1 trait-rename: 0** (assuming A.1 stays scoped to the bipolar trait sites and does not touch the categorical-bucket namespace, per §1 + §8).

If A.1 chooses to introduce new tests for `maximizer_tendency` consolidation invariants (e.g., "all canonical Python-identifier sites use `maximizer_tendency` as the key"), those would be additions, not updates.

---

## §6 Pass 5 — Downstream migration references

Total migrations in `adam/infrastructure/neo4j/migrations/`: **26** (`001_core_constraints.cypher` through `030_user_posterior_storage.cypher`, with gaps at 011–014).

### §6.1 Migrations that touch `:PersonalityDimension`

| Migration | Touch type | Notes |
|---|---|---|
| `001_core_constraints.cypher:20` | constraint | `dimension_id IS UNIQUE` (live) |
| `002_core_indexes.cypher:54,57,60` | indexes | indexes on `name`, `domain`, `dimension_type` (live) |
| `005_seed_personality_dimensions.cypher` | seed | the `dim_cog_decision_style` MERGE at line 147 (the construct's only WRITE site) |
| `007_amazon_relationships.cypher:174` | comment-only | `]->(:PersonalityDimension)` appears inside a `/* ... */` cypher comment block describing planned relationships; no live MERGE/MATCH |
| `018_customer_intelligence.cypher:129–135` | comment-only | `// CustomerIntelligence relates to PersonalityDimension (from 005_seed_personality)` — `// HAS_CUSTOMER_PROFILE` comment description; no live MERGE/MATCH |

**No live downstream migration writes properties to or creates relationships from/to** the seeded `dim_cog_decision_style` node. Migrations 007 and 018 plan the relationship in commentary but do not execute it.

### §6.2 Migrations 026–030 (post-024 / post-025)

None reference PersonalityDimension. Listing for completeness:
- `026_attentional_posture.cypher`
- `027_recommendation_class.cypher`
- `028_inferential_chain.cypher`
- `029_add_ts_propensity_to_ad_decision.cypher`
- `030_user_posterior_storage.cypher`

A.1 may add a new migration `031_*.cypher` (next available number; `025` is already occupied by `025_clt_recalibration_2026_04_24.cypher`) to update the `dim_cog_decision_style` node's properties without breaking the existing seed.

---

## §7 Pass 6 — `construct_taxonomy.py` role

**File:** `adam/intelligence/construct_taxonomy.py`
**Lines inspected:** 600–700 (covering DOMAIN_7 PERSUASION + DOMAIN_8 DECISION_MAKING in full + start of DOMAIN_9)
**Maximizer/satisficer location:** lines 653–654 within `DOMAIN_8_DECISION_MAKING` (17-construct domain)

### §7.1 Schema

`DOMAIN_8_DECISION_MAKING` is a `Domain` instance with these top-level fields (extracted from inspection):

```python
DOMAIN_8_DECISION_MAKING = Domain(
    domain_id="decision_making",          # = _D8
    domain_name="Decision Making Style",
    scoring_side=_US,                     # user-side scoring
    construct_count=17,
    purpose="How individuals approach decisions.",
    primary_research="Schwartz et al. (2002), Cacioppo & Petty (1982), Kruglanski (1994)",
    constructs={
        "dm_system1": _c(...),
        "dm_system2": _c(...),
        "dm_effort": _c(...),
        "dm_maximizer": _c("dm_maximizer", _D8, "Maximizer Tendency",
                           temporal_stability=_TR, inference_tractability=_HI),
        "dm_satisficer": _c("dm_satisficer", _D8, "Satisficer Tendency",
                            temporal_stability=_TR, inference_tractability=_HI),
        "dm_confidence": _c(...),
        "dm_regret": _c(...),
        # ... 10 more constructs (involve, impulse, variety, loyalty, info_search, nfc) ...
    },
)
```

Per-construct `_c(...)` builder fields (inferred from invocation pattern): `(id, domain_id, display_name, temporal_stability, inference_tractability)`.

### §7.2 Architectural relationship to Neo4j seed

`construct_taxonomy.py` is a **parallel academic-grounding taxonomy** that:
- Cites Schwartz et al. (2002) directly in `primary_research`
- Maintains a 17-construct decision-making decomposition where maximizer and satisficer are SIBLING constructs (separate IDs `dm_maximizer` + `dm_satisficer`), NOT a single bipolar dimension
- Does NOT directly seed Neo4j (no `MERGE (:PersonalityDimension)` calls; no Cypher emission)
- Does NOT consume the Neo4j seed (no `dim_cog_decision_style` cross-reference)

**Relationship verdict:** parallel taxonomies; neither is upstream of the other. The Neo4j seed (migration `005`) collapses Schwartz's bipolar maximizer/satisficer into a single bipolar dimension `dim_cog_decision_style` with `low_description='Satisficer'` and `high_description='Maximizer'`. The construct_taxonomy keeps them as bipolar siblings — academically more faithful to Schwartz's original instrument (the Maximization Scale has separate maximizer-tendency and satisficer-tendency subscales).

**Implication for A.1:** these are NOT a fragmentation to be consolidated against each other. They're two architectural choices:
1. Neo4j: bipolar dimension (one scalar, two anchors).
2. construct_taxonomy: separate constructs (two scalars).

A.1's consolidation should leave both intact. They serve different purposes: Neo4j seed is the bid-time-queryable trait dimension; construct_taxonomy is the academic-decomposition reference. Renaming `dm_maximizer`/`dm_satisficer` would distort the academic faithfulness.

---

## §8 Recommended A.1 Scope

### §8.1 Canonical name

**Recommendation:** `maximizer_tendency`

Rationale:
- Already canonical in 4 files (`adam/intelligence/unified_psychological_intelligence.py` + `adam/platform/constructs/service.py` + `adam/platform/constructs/models.py`). Existing dataclass fields would NOT need to change.
- Schwartz et al. (2002) refers to "maximization tendency" / "maximizer tendency" — closer match to literature than "decision_maximizer" or "maximizing_tendency".
- "Tendency" suffix matches construct_taxonomy.py display names (`"Maximizer Tendency"` / `"Satisficer Tendency"`).
- Already approved by Chris's preference signal in Q7.A=(c).

**(Q10.A — confirm):** Adopt `maximizer_tendency` as canonical, OR consider `dm_maximizer_tendency` (composite of construct_taxonomy id-prefix + canonical name)?

### §8.2 `dim_cog_decision_style` strategy

**Recommendation: Option (i) — keep `dimension_id` stable; only rename `name` property + add Schwartz-grounding properties.**

Rationale:
- Pass 2 surfaced **0 READ_BY sites** for `dim_cog_decision_style`. Renaming the ID has zero benefit and the cost of (a) the rename itself, (b) any external Neo4j operator queries / saved Browser queries that reference the ID interactively (unobservable from this audit), (c) breaking the migration `001` UNIQUE constraint's idempotency unless the new migration explicitly handles the rename.
- Renaming the `name` property is also non-zero blast — it touches the `002:54` index — but the index is rebuilt on next startup; no schema migration needed beyond the seed update.
- New properties to ADD: `academic_grounding`, `scale_min`, `scale_max`, `scale_anchor_low`, `scale_anchor_high`, `added_in`. These are pure additions; safe.

**(Q10.B — confirm):** Adopt option (i)? OR option (ii) rename ID to `dim_cog_maximizer_tendency` for cleaner long-term naming? Audit recommends option (i).

### §8.3 Migration mechanics

The seed currently lives at `005:147`. Two options:

**Option (α) — In-place edit `005_seed_personality_dimensions.cypher`.** Convention for this repo's migration framework matters; if migrations are run only-once at startup and tracked via a migrations table, in-place edits will not re-apply on existing deployments. Risk: production environments retain old property values.

**Option (β) — New migration `031_update_decision_style_dim.cypher`.** Uses `MATCH ... SET` to update the existing node (the `dimension_id IS UNIQUE` constraint guarantees the MATCH finds exactly one). This is the safer pattern for live environments. Recommendation.

**(Q10.C — confirm):** Adopt option (β) — new migration `031`?

### §8.4 Per-site rename plan

| Site | Current form | A.1 action |
|---|---|---|
| `adam/infrastructure/neo4j/migrations/005:148` | `name = 'decision_style'` | Update via new migration `031` to `name = 'maximizer_tendency'` + add `academic_grounding`, `scale_min`, `scale_max`, `scale_anchor_low`, `scale_anchor_high`, `added_in` properties |
| `adam/cold_start/models/enums.py:147` | `MAXIMIZING_TENDENCY = "maximizing_tendency"` | Rename enum member to `MAXIMIZER_TENDENCY` and value to `"maximizer_tendency"`. **Inspect every `MAXIMIZING_TENDENCY` import + every `"maximizing_tendency"` string-literal use** before renaming the value (current Pass 3 inventory shows 1 hit total — minimal blast). |
| `adam/intelligence/unified_psychological_intelligence.py:197, 1207` | `maximizer_tendency: float = 0.5` and `"maximizer_tendency": 0.25` | **No change** — already canonical |
| `adam/platform/constructs/service.py:95, 115, 269` | `"maximizer_tendency": ...` | **No change** — already canonical |
| `adam/platform/constructs/models.py:193, 209` | `maximizer_tendency: ConstructScore = ...` | **No change** — already canonical |
| `adam/intelligence/unified_construct_integration.py:152` | `"decision_maximizer": {` | Rename to `"maximizer_tendency"` |
| `adam/intelligence/enhanced_review_analyzer.py:172, 320, 923, 951` | `"decision_maximizer"` (5 hits) | Rename to `"maximizer_tendency"` |
| `adam/intelligence/knowledge_graph/populate_psychological_graph.py:320, 397, 463, 464, 491, 506, 712, 744` | `"decision_maximizer"` / `id="decision_maximizer"` (8 hits) | Rename to `"maximizer_tendency"` |
| `adam/intelligence/knowledge_graph/persuasion_susceptibility_graph.py:508, 556` | `"decision_maximizer"` (2 hits) | Rename to `"maximizer_tendency"` |
| `adam/corpus/pipeline/liwc_scorer.py:279` | `"decision_maximizer": round(maximizer, 3)` | Rename to `"maximizer_tendency"` |
| `adam/data/amazon/enhanced_ingestion.py:100, 323, 396` | `decision_maximizer` (1 dataclass field, 1 mapping, 1 attribute) | Rename ALL THREE to `maximizer_tendency` |
| `adam/intelligence/construct_taxonomy.py:653, 654` | `dm_maximizer` + `dm_satisficer` siblings | **No change** — bipolar academic-faithful split, intentional per §7.2 |
| `adam/intelligence/empirical_psychology_framework.py:714, 772` | `"satisficing"` + `"maximizing"` DecisionStyleDimension entries | **No change** — categorical-bucket namespace (§4.8) |
| All ~683 `decision_style` + ~67 `"satisficing"`/`"maximizing"` categorical-bucket sites | (categorical-bucket variable / value) | **No change** — separate namespace per §1 + §4.7 + §4.8 |

**Total per-site touches: ~20 line changes** across **7 files** (cold_start enum + unified_construct_integration + enhanced_review_analyzer + populate_psychological_graph + persuasion_susceptibility_graph + liwc_scorer + enhanced_ingestion). Plus 1 new migration file. Plus ~2 unchanged-already-canonical files (constructs/service.py + constructs/models.py + unified_psychological_intelligence.py).

### §8.5 Schwartz academic_grounding content for migration `031`

```
academic_grounding: 'Schwartz, B., Ward, A., Monterosso, J., Lyubomirsky, S.,
                     White, K., & Lehman, D. R. (2002). Maximizing versus
                     satisficing: Happiness is a matter of choice. Journal of
                     Personality and Social Psychology, 83(5), 1178–1197.'
scale_min: 0.0
scale_max: 1.0
scale_anchor_low: 'satisficer (good-enough orientation)'
scale_anchor_high: 'maximizer (optimal-choice orientation)'
added_in: 'A.1'
```

### §8.6 Estimated test-update count

**0** existing test-file changes required (per §5).

If A.1 chooses to add invariant-pinning tests (e.g., "no `decision_maximizer` string literal in `adam/intelligence/`"), that's an addition.

### §8.7 Estimated commit-LOC delta

- New migration `031_update_decision_style_dim.cypher`: ~30 lines added
- 7 file edits, ~20 line changes total
- Optional new test file (invariant-pinning): ~50 lines
- **Total estimate: +50 to +100 line delta**

### §8.8 QUESTION-and-stop concerns surfaced for Claude Proper adjudication

| Q | Concern |
|---|---|
| **Q10.A** | Confirm canonical name: `maximizer_tendency` (audit recommendation) vs `dm_maximizer_tendency` vs other |
| **Q10.B** | Confirm migration strategy: option (i) keep `dim_cog_decision_style` ID stable, only rename `name` + add properties (audit recommendation) vs option (ii) rename ID too |
| **Q10.C** | Confirm migration mechanics: option (α) in-place edit `005` vs option (β) new migration `031` (audit recommendation) |
| **Q10.D** | Confirm `construct_taxonomy.py:653-654` `dm_maximizer`/`dm_satisficer` bipolar split is intentional and **NOT** a fragmentation site to consolidate (audit recommendation: leave intact per §7.2 academic-faithfulness argument) |
| **Q10.E** | Confirm `decision_style` categorical-bucket namespace (683 hits, §4.7) is **separate** from the bipolar trait and **NOT** in A.1 scope. (Out-of-scope refactor candidate for a future slice.) |
| **Q10.F** | Confirm `"satisficing"` / `"maximizing"` categorical-value strings (67 hits, §4.8) are categorical-bucket values **NOT** in A.1 scope. |
| **Q10.G** | If `MAXIMIZING_TENDENCY` enum is renamed (§8.4 row 2), should the enum value `"maximizing_tendency"` ALSO change to `"maximizer_tendency"`? Doing so could break any persisted state that uses the old value as a key. Audit recommendation: yes, rename both, but verify no persistence layer (Redis cache, Neo4j feature, cold_start checkpoint) holds the old value as a key. |

---

## §9 Audit closure

**Audit complete.** Memo committed for A.1 reference. Slice A.1.0 ships read-only. No code modifications. No file renames. No migration changes. No test changes.

**State at standdown:**
- Memo at `docs/audits/MAXIMIZER_FRAGMENTATION_AUDIT.md` (this file).
- Branch `feature/hmt-dashboard` HEAD unchanged: `cf41115` (A.0).
- Working tree carries this new file plus the prior-turn `docs/MEMORY.md` EVE-update + `docs/PLATFORM_INVENTORY_2026_05_07.md` (untracked).

**Next session (A.1):** Claude Proper adjudicates Q10.A–G. A.1 prompt issued with locked decisions. Claude Code executes the consolidation refactor per §8.4 plan with adjudicated parameters.

---

**End of audit.**
