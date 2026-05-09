# LUXY Pilot Campaign Data Access Audit
## Slice ID: P.0
## Session: 2026-05-08 (continuation)
## Predecessor: 0ad0919 (M.1 — pilot path operational)
## Audit type: Read-only inspection (no production queries; counts + shapes only)
## Branch: feature/hmt-dashboard

---

## §1 Executive Summary

LUXY pilot data access is **substantially constrained by a permanent
structural limit established in the prior S0 audit** (`docs/S0_HANDOFF_2026_05_04.md`):
**StackAdapt does not populate served-impression-URL granularity for
the LUXY pilot account.** This was empirically established against
the live API and documented as "not a bug to route around; it is a
permanent constraint of the data we get from this DSP for this pilot"
(S0_HANDOFF §5, line 500).

Per-source state at S0 (2026-05-04, 365-day extraction window):
- `conversion_path`: 6 unique URLs (single-page funnel — `luxyride.com/ride-details` with UTM variants)
- `pixel_postback`: **N/A** (no impression-time pixel log shipped on LUXY pilot)
- `campaign_page_context`: **0 rows** (StackAdapt does not populate this for LUXY)
- 202 publisher domains observed in `conversionPath` records but with **no URL captured**

This constraint was established BEFORE S6.2 + W chain + M.1 wiring shipped — meaning
the data-access surface for LUXY is unchanged by anything in the post-S0 work. The
post-S0 chain (S6.2 → M.1) added cell-conditional decisioning capability but did
NOT change what StackAdapt exposes for the active campaign.

**Per-analysis feasibility distribution (Pass 8):**
- **Feasible**: 1 (ANALYSIS-C — `cold_start_archetype_mapper` sanity check; uses synthetic input distributions, no API access needed)
- **Partially Feasible**: 3 (ANALYSIS-A FOMO subset against 6 known URLs; ANALYSIS-B compensatory if cohorts exist in Neo4j; ANALYSIS-F cohort outcome correlation if both cohort + conversion data exist)
- **Infeasible**: 2 (ANALYSIS-D cell-tuple cross-reference — blocked by missing page-context data; ANALYSIS-E FOMO outcome correlation — blocked by missing impression-level URL granularity)

**Recommended first analysis (§10):** **ANALYSIS-C** — `cold_start_archetype_mapper`
sanity check via synthetic geo/device/time/IAB distributions. Small effort
(~50 LOC test), zero external data dependencies, validates that the W.2a mapper
isn't degenerate (assigning everyone the same archetype) before pilot launch
exercises it.

**5 QUESTION-and-stop concerns surfaced (Q32-Q36)** — see §11. The most
consequential is **Q35**: the S0 permanent-constraint finding STRUCTURALLY blocks
ANALYSIS-D + ANALYSIS-E. No new credential or access provisioning can resolve it
without standing up parallel pixel-impression-tracking infrastructure ourselves
(S0 candidate path 1).

---

## §2 Pass 1 — Campaign state inventory

### Confirmed from in-repo / prior audit
- **Advertiser ID**: 122463 (per `docs/S0_HANDOFF_2026_05_04.md:182`)
- **LUXY campaigns visible**: 12 (per `S0_HANDOFF:183`)
- **Service domain whitelist**: `https://luxyride.com`, `https://www.luxyride.com` per `adam/config/settings.py:212`
- **Campaign-specific persona constants**: `adam/constants.py:43` (LUXY Ride campaign-specific personas → graph archetypes)
- **Empirical archetype data**: 754 converted LUXY Ride bilateral edges per `adam/constants.py:306-312` (Session 34-2 data)
- **Pre-S6.2 baseline**: the cascade was running pre-S6.2 baseline retargeting against the active campaign; no cell-conditional creative selection, no predicate firing. The S6.2 → M.1 chain just shipped today (2026-05-08).

### NOT recoverable from in-repo (config-not-in-repo, ops-side question)
- Campaign **current state** (active / paused / ended) — requires StackAdapt API call
- Campaign **launch date** — not surfaced in any in-repo artifact
- **Approximate bid volume served to date** — surfaced indirectly: S0 found 285 raw conversion-path rows over a 365-day window, with `luxyride.com` at impression weight 1213 (`S0_HANDOFF:202`). This is a lower bound on aggregate impressions; total served volume is much higher.

### Date range of available historical data
- 365-day window successfully pulled at S0 (2026-05-04). Range was therefore 2025-05-04 → 2026-05-04 at that time. Identical pull today would yield 2025-05-08 → 2026-05-08 — but per the S0 structural-bias finding, the URL surface would still be 6 single-funnel URLs.

---

## §3 Pass 2 — StackAdapt API access surface

### GraphQL client
- **Module**: `adam/integrations/stackadapt/graphql_client.py:62` (`StackAdaptGraphQLClient` class)
- **Endpoint**: `https://api.stackadapt.com/graphql` (override via `STACKADAPT_GRAPHQL_ENDPOINT` env var) — `graphql_client.py:51-54`
- **Auth**: Bearer token from `STACKADAPT_API_KEY` or `STACKADAPT_GRAPHQL_KEY` env vars — `graphql_client.py:57-59`
- **Rate-limit handling**: `_query_with_retry` with full-jitter exponential backoff, max 7 attempts, base 500ms, cap 60s — `graphql_client.py:96-158`
- **Async**: all query methods are `async def`; non-trivial work to bridge to sync analysis scripts

### Available methods (inventoried from `graphql_client.py`)
| Line | Method | Purpose |
|------|--------|---------|
| 160 | `get_conversion_paths_page` | Source 1 — conversionPath records (URL granularity ONLY at conversion-page level, per S0 finding) |
| 242 | `get_campaign_page_context_page` | Source 3 — campaignPageContext (returned 0 rows for LUXY per S0) |
| 377 | `get_campaigns` | List campaigns by advertiser |
| 433 | `get_campaign` | Single-campaign detail |
| 490 | `get_campaign_performance` | Aggregate performance metrics |
| 558 | `get_conversion_events` | Conversion event stream |
| 633 | `get_domain_performance` | Per-domain aggregate (the 202-domain coverage gap surfaced here) |
| 695 | `list_ads` | Creative inventory |
| 762 | `create_creative_by_url` | Mutation — push creative |
| 853 | `create_audience` | Mutation — create audience segment |
| 893 | `add_users_to_audience` | Mutation — segment population |

### Critical access constraints (from S0 + RETARGETING_AUDIT)
- **No `touchpoints[]` array** on `conversionPath` — `S0_HANDOFF:475` schema correction. Only `conversionStats.conversionUrl` is exposed (single conversion-page URL per record).
- **No advertiser filter on `ConversionPathFilters`** — caller must pre-fetch LUXY campaign IDs and filter by campaign — `S0_HANDOFF:480`.
- **`campaignPageContext` returns 0 rows for LUXY** — `S0_HANDOFF:500`. This is the structural blocker for any impression-level URL retrospective.
- **No outbound webhooks from StackAdapt** — per session memory; we are inbound-only consumer.

### Latency / freshness
- Retrospective query latency depends on time window + pagination depth. S0's 365-day extraction completed (volumes documented in §2 above) but exact wall-clock latency wasn't recorded in S0_HANDOFF.
- Data freshness window: not explicitly surfaced in repo; StackAdapt typically has multi-hour to ~24h attribution lag for conversion events.

---

## §4 Pass 3 — Neo4j historical state

### What COULD exist (counts + existence — no production queries run)

**UserCohort node schema** (`adam/intelligence/cohort_discovery.py:38-54` post-W.2a):
```python
@dataclass
class UserCohort:
    cohort_id: str
    size: int
    sample_members: List[str]
    dominant_mechanisms: List[str]
    mechanism_effectiveness: Dict[str, float]
    psychological_centroid: Dict[str, float]
    discovered_at: datetime
    # W.2a additions:
    compensatory_consumption_pattern: bool = False
    compensatory_detection_confidence: float = 0.5
```

### Whether `discover_cohorts` ran during the LUXY campaign window
- `discover_cohorts` is async at `cohort_discovery.py:172-274` and uses Neo4j GDS Louvain over the User → CognitiveMechanism `RESPONDS_TO` graph
- Whether it ran against LUXY production data — **unknown without querying Neo4j**
- If it ran, cohorts would have been persisted via `persist_cohort_assignments` (`cohort_discovery.py:474+`)
- W.2a's `compensatory_consumption_pattern` field is BACKWARD-COMPATIBLE on legacy cohort entries (defaults to False per W.2a Pass C finding) — so legacy cohorts in Neo4j (if any) deserialize cleanly post-W.2a

### Useful queries (DO NOT RUN — for §10 reference)
```cypher
// Count cohorts (would be the first sanity check)
MATCH (uc:UserCohort) RETURN count(*) AS n

// Date range of cohort discovery
MATCH (uc:UserCohort)
RETURN min(uc.updated_at) AS earliest, max(uc.updated_at) AS latest

// Per-cohort dominant mechanisms (validates F.2 detection inputs)
MATCH (uc:UserCohort)
RETURN uc.id, uc.size, uc.mechanism_effectiveness_json
ORDER BY uc.size DESC LIMIT 20

// User node count (population baseline)
MATCH (u:User) WHERE u.cohort_id IS NOT NULL RETURN count(*) AS n
```

### Compensatory pattern population
- Q20-correction (M.0 audit): `compensatory_consumption_pattern` would only be populated if F.2 ran post-shipping AND the buyer profiles persistence path wrote the new fields. Both unlikely for the LUXY active campaign window since F.2 just shipped (commit `1c49a75` — 2026-05-08).

---

## §5 Pass 4 — Redis / per_user_posterior_modulation state

### Storage shape
- **Redis key prefix**: `informativ:buyer:{buyer_id}` per `adam/api/stackadapt/graph_cache.py:884`
- **TTL**: 90 days per `graph_cache.py:885` (`60 * 60 * 24 * 90`)
- **Read path**: `get_buyer_profile` at `graph_cache.py:941+` — Redis read-through with in-process LRU + cold-miss fresh-profile creation
- **Profile shape**: `BuyerUncertaintyProfile` at `adam/intelligence/information_value.py:401` (post-W.2a + W.2b — has `archetype`, `archetype_assigned_at`, `archetype_reassigned`, `bids_since_archetype_assignment` fields)

### What COULD exist (without production query)
- Approximate count of buyer profiles in Redis: unknown without `KEYS informativ:buyer:*` query (which is itself production-disrupting and should not run)
- Date range of last-updated timestamps: unknown without inspection
- **`profile.archetype` field expected None across all entries**: W.2a was shipped 2026-05-08 (commit `60b1ac0`); the cascade integration block writes archetype only on bid events AFTER W.2a deployment. Pre-existing buyer profiles in Redis from the active campaign window have `profile.archetype = None` (W.2a's `__post_init__` default per `information_value.py` schema extension). Post-W.2a-deployment bids will populate.
- **`profile.constructs["maximizer_tendency"]`**: W.2b shipped 2026-05-08 (commit `bdd24a0`). Pre-W.2b profiles get the construct via `__post_init__` (the dimension is now in `UNCERTAINTY_DIMENSIONS`), but at default Beta(2,2) — NOT the archetype-conditional prior. W.2b's `apply_archetype_maximizer_prior` only fires on archetype-assignment events post-deployment.

### Pre-existing posterior population
- 12+ outcome handlers in `adam/core/learning/outcome_handler.py:43-2520` update profile state on conversion events
- For the LUXY campaign window, any conversions that fired during the active period would have triggered `_update_buyer_profile` at `outcome_handler.py:2520` — which writes to constructs (the legacy 20-dim BetaPosteriors), NOT to W.2a/W.2b's new archetype + maximizer fields
- Net: pre-existing LUXY buyer profiles have **populated 20-dim Beta posteriors** but **None archetype + default Beta(2,2) maximizer**

---

## §6 Pass 5 — Decision trace + cascade log inventory

### Persistence layers
- **Redis hot store**: `decision_trace:{decision_id}` keys per `adam/intelligence/decision_trace_store.py:103` (`_PRIMARY_KEY_PREFIX`)
- **User secondary index**: `decision_trace_user_idx:{user_id}` Redis lists per `decision_trace_store.py:32`
- **Neo4j cold store**: `adam/intelligence/decision_trace_neo4j.py` (sibling persistence)
- **Cross-load helper**: `defensive_reasoning_renderer.py:356-378` (try Redis → fall back to Neo4j)

### Trace schema fields (`adam/intelligence/decision_trace.py:279+`)
- decision_id, user_id, timestamp, bid_request_id
- chosen_creative_id, chosen_mechanism, chosen_score
- alternatives (List[AlternativeCandidate])
- user_posterior_snapshot (Dict[str, float])
- page_posture_vector, posture_class, posture_confidence
- **page_url** (Optional[str]) — added at later commit per Original-Slice-A from session 2026-05-02
- bid_value, chain_of_reasoning, schema_version
- **NO cell_id field** in current schema (S6.2's CellFeatureSet flows through aggregator-side; it's not yet in the persisted DecisionTrace schema — S6.2 integration block at bilateral_cascade.py:2882 logs to `result.reasoning` but does not update DecisionTrace.cell_id)

### LUXY campaign window coverage
- **Likely sparse to absent**. DecisionTrace persistence requires:
  1. The cascade code path that emits traces deployed at the time of bidding
  2. Redis + Neo4j access for the persistence layer
  3. The decision_trace_store.save_trace() actively called during bidding
- Pre-S6.2 baseline retargeting may not have been emitting full DecisionTraces at scale — depends on prior infrastructure deployment state, which is not surfaced in-repo
- Per `RETARGETING_AUDIT_2026_05_04.md:23`: "no impression-time URL log on the LUXY pilot" — this includes the absence of impression-tied DecisionTraces with url granularity at scale
- **Recommendation**: do not assume DecisionTraces exist in Redis/Neo4j for the LUXY campaign window without first running a count query (Q33 surface)

---

## §7 Pass 6 — PagePrimingSignature historical cache

### Cache cascade
- **Module**: `adam/priming/feature_store.py:142+` — `PagePrimingSignatureStore`
- **L1 LRU**: in-memory dict, capacity 1000 default (`feature_store.py:144`); sync read
- **L2 async Redis**: read-through; not bid-time-accessible per Q21 (M.1 sync constraint)
- **L3 sync Memcached**: read-through fallback; bid-time-accessible

### Get path
- `async PagePrimingSignatureStore.get(url_hash)` at `feature_store.py:158-196`
- Always returns a signature (neutral fallback on cold miss); never None

### Schema version distribution
- V1 pre-B (5-dim signature): legacy entries
- V2 post-B/S6-prep.2 (6-dim with `persuasion_knowledge_activation`): post-2026-05-07 entries
- `from_dict` deserialization is backward-compat for both via `.get(default)` defaults per B's commit

### Coverage of LUXY campaign URLs
- Per S0 finding: only 6 unique URLs at conversion granularity (`luxyride.com/ride-details` with UTM variants)
- Coverage of those 6 URLs in priming cache: **unknown without inspection**. Likely populated if the priming pipeline ran on `luxyride.com` at any point; unknown for the 202 publisher domains observed in conversion paths (the publishers' specific URLs were not captured per S0)
- Coverage of publishers' SERVED URLs (the structural gap): **structurally absent** since served-URL granularity isn't exposed by StackAdapt for LUXY (S0 §5 permanent constraint)

---

## §8 Pass 7 — Outcome data accessibility

### Internal outcome handler
- **Entry point**: `adam/core/learning/outcome_handler.py:31` (`OutcomeHandler` class)
- **Webhook bridge**: `adam/api/stackadapt/webhook.py:43+` (`_outcome_handler` singleton with lazy init)
- **Process entry**: `OutcomeHandler.process_outcome` at `outcome_handler.py:43`
- **Update fan-out** (12+ paths, all async):
  - `_update_thompson` (line 1480)
  - `_update_meta_orchestrator` (line 1606)
  - `_update_neo4j_attribution` (line 1644)
  - `_update_graph_rewriter` (line 1712)
  - `_route_to_learning_hub` (line 1730)
  - `_update_theory_learner` (line 1772)
  - `_process_chain_attestations` (line 2001)
  - `_update_dsp_learning` (line 2119)
  - `_update_ml_ensemble` (line 2200)
  - `_update_cognitive_learning` (line 2233)
  - `_update_page_context_learning` (line 2307)
  - `_update_mechanism_interactions` (line 2421)
  - `_update_buyer_profile` (line 2520)
  - `_update_bilateral_edge_evidence` (line 2623)

### Outcome data dimensions accessible
| Dimension | Source | Granularity | Date range | Status |
|-----------|--------|-------------|------------|--------|
| Impression-level outcomes (click yes/no) | StackAdapt API + internal logs | Per-impression | Campaign window | **Blocked at impression-level URL granularity per S0** |
| Conversion attribution + latency | StackAdapt `get_conversion_events` + `outcome_handler` Neo4j writes | Per-conversion | Campaign window | **Available** (via API; subject to attribution lag) |
| Creative-level performance | StackAdapt `get_campaign_performance` + `list_ads` | Per-creative | Campaign window | **Available** |
| Cohort-level outcomes | Neo4j attribution joined with UserCohort assignments | Per-cohort | Whatever cohort discovery covered | **Conditional** on cohort discovery having run |
| User-level outcomes | StackAdapt + Neo4j User node aggregations | Per-user | Campaign window | **Available** for buyer_ids that received conversions; pre-W.2a archetype field will be None |

### S0 conversion path findings
- 285 raw conversion-path rows over 365 days (S0 §1)
- 6 unique conversion-page URLs, all `luxyride.com/ride-details` variants
- 202 publisher domains in records (these are the impression-side publisher hosts; URLs not captured)

---

## §9 Pass 8 — Analysis feasibility matrix

| ID | Analysis | Feasibility | Required sources | Effort | What it tells us | What it explicitly cannot |
|----|----------|-------------|------------------|--------|------------------|--------------------------|
| **A** | M.1 `compute_fomo_score` retrospective fire-rate | **Partially Feasible** | PagePrimingSignature cache (§7) for the 6 LUXY URLs + audience-segment metadata via StackAdapt API (§3) | Small (~50-100 LOC analysis script) | Validates `compute_fomo_score` produces non-degenerate fire rate on the available URL surface | Cannot validate fire rate on real served impression diversity (per S0 structural constraint) — only the 6 conversion URLs |
| **B** | F.2 `detect_compensatory_consumption_pattern` against existing UserCohorts | **Partially Feasible** | Neo4j UserCohort nodes (§4) — conditional on `discover_cohorts` having run | Small if cohorts exist (~50 LOC); medium if cohort discovery must run first (~hours) | Validates F.2 thresholds (POSTURE_CONCENTRATION_THRESHOLD=0.40, LOW_MOMENTUM_THRESHOLD=0.35, etc.) produce non-degenerate compensatory flag distribution | Cannot validate against real telemetry-aggregated inputs (per W.0 Q20 finding — the originally-spec'd telemetry inputs don't exist; F.2 uses Cialdini-mechanism-vocabulary proxy per Q26) |
| **C** | W.2a `cold_start_archetype_mapper` retrospective archetype distribution | **Feasible** | NONE (uses synthetic geo/device/time/IAB distributions) | Small (~50 LOC test) | Validates the mapper isn't degenerate (assigning everyone PRAGMATIST or some single archetype). Pin against reasonable archetype-distribution assumptions | Cannot validate against real bid-stream distribution without StackAdapt impression-level metadata access |
| **D** | F.1 cell-tuple cross-reference against historical bid contexts | **Infeasible** | Page-context data (campaign_page_context surface) | N/A | — | **Structurally blocked** by S0 finding: campaign_page_context returned 0 rows for LUXY |
| **E** | FOMO outcome correlation: do high-FOMO contexts show different historical outcomes? | **Infeasible** | Impression-level URL + outcome attribution | N/A | — | **Structurally blocked** by S0 finding: no impression-time URL granularity for LUXY |
| **F** | Cohort-level mechanism effectiveness retrospective: do affiliative-mechanism cohorts show different outcomes than transactional cohorts? | **Partially Feasible** | Neo4j UserCohort + conversion attribution joins | Medium (~150 LOC analysis script + cypher queries) | Correlation evidence on whether F.2's compensatory dichotomy maps onto outcome differences in historical data. CAVEAT: correlation only — no cell-conditional creative was served | Cannot establish causation; cannot disentangle from confounders (creative variation, time-of-day, segment composition) |

**Summary distribution**:
- Feasible: 1 (C)
- Partially Feasible: 3 (A, B, F)
- Infeasible: 2 (D, E)

---

## §10 Recommended retrospective analysis sequence

Effort-ordered from smallest, highest-confidence to largest, most-blocked:

### 1. ANALYSIS-C — `cold_start_archetype_mapper` sanity check (small; recommended first)
Synthetic input distribution test:
- Sample 10,000 random `(geo, device, hour_of_day, iab_category)` tuples from realistic distributions
- Run `map_cold_start_archetype` on each
- Assert the archetype distribution is non-degenerate (no single archetype claims >70%)
- Surfaces mapper degeneracy before pilot launch exercises it
- **No external data dependencies** → can run today without provisioning

### 2. ANALYSIS-A subset — FOMO score on the 6 known LUXY URLs (small)
- Pull the 6 `luxyride.com/ride-details` variants
- Run priming pipeline on each (or read from cache if populated)
- Compute `compute_fomo_score` for each
- Document fire rate (how many of 6 cross the >0.7 predicate threshold)
- **Effort**: ~50-100 LOC + brief StackAdapt API call to verify URLs still active
- **Caveat**: 6-URL sample is not representative of the broader served-URL surface (which is structurally inaccessible per S0)

### 3. ANALYSIS-B + ANALYSIS-F (medium; requires Neo4j access)
First confirm UserCohort nodes exist for the LUXY window (1 cypher query):
```cypher
MATCH (uc:UserCohort) RETURN count(*) AS cohort_count, min(uc.updated_at) AS earliest, max(uc.updated_at) AS latest
```
- If `cohort_count > 0` and the date range overlaps the LUXY campaign: proceed with B + F
- If `cohort_count = 0`: defer until cohort_discovery runs (separate operational decision)

### 4. Defer analyses D + E
Both are structurally blocked by S0's permanent-constraint finding. Re-evaluating
requires either:
- **Path 1 from S0**: standing up our own pixel-impression-tracking infrastructure (substantial engineering work; not a P-chain analysis slice)
- **Operational change at StackAdapt**: them populating page-context data for the LUXY account (out of our control)

Until one of those changes the data surface, D + E should be removed from the analysis backlog.

---

## §11 QUESTION-and-stop Concerns

### Q32 — StackAdapt GraphQL credentials state
- Per `graph_client.py:55-59`, the client reads `STACKADAPT_API_KEY` or `STACKADAPT_GRAPHQL_KEY` from env vars. S0's 2026-05-04 work successfully called the API, so credentials existed then.
- **Adjudication needed**: confirm credentials are still valid + present in the dev environment for retrospective queries (ANALYSIS-A subset + ANALYSIS-F's joins). If not, ANALYSIS-A's URL-validity check must be deferred or run via another path.

### Q33 — Neo4j production state queryability from dev
- ANALYSIS-B + ANALYSIS-F require running `MATCH` queries against Neo4j
- Whether the dev environment's Neo4j connection points at production OR a separate dev/staging instance is **not surfaced in-repo** (per `adam/api/stackadapt/graph_cache.py` connection logic which uses env-var-configured URI)
- **Adjudication needed**: whether retrospective Neo4j queries should run against production data (operational risk; potential disruption to active cascade) OR require an offline data extract first

### Q34 — Decision traces persisted for LUXY campaign window
- Per Pass 5: trace persistence depends on prior infrastructure deployment state which is not in-repo
- **Adjudication needed**: confirm with ops whether DecisionTrace records exist in Redis or Neo4j for the LUXY campaign window. If no traces exist, all trace-based analyses are blocked; the only retrospective signal is what's reconstructable from StackAdapt API responses + Neo4j cohort/posterior state

### Q35 — Permanent S0 constraint confirmed structurally blocking
- ANALYSIS-D + ANALYSIS-E are blocked by S0's finding of no served-impression-URL granularity for LUXY pilot
- **Adjudication needed**: explicit acknowledgment that retrospective predicate-firing analysis on real impression diversity is **infeasible without standing up parallel pixel-impression-tracking infrastructure**. This is a major scope item if the team wants the validation; it is NOT in the P-chain audit's scope

### Q36 — Pixel-impression-tracking infrastructure status
- S0 (2026-05-04) listed candidate path 1 as "stand up pixel-impression-tracking infrastructure ourselves"
- **Adjudication needed**: was any work toward path 1 completed since 2026-05-04? If yes, post-S0 impression data may be partially accessible and ANALYSIS-D + ANALYSIS-E partial-feasibility re-evaluation is warranted. If no, the structural blocker stands

---

## §12 Audit closure

P.0 produced a sober finding: the retrospective-analysis surface for the LUXY pilot
is substantially constrained by infrastructure conditions established at S0 (2026-05-04)
which the post-S0 implementation chain (S6.2 + W chain + M.1) did not change.

**The only zero-blocker analysis is ANALYSIS-C** (cold_start_archetype_mapper sanity
check via synthetic distributions). A few partials (A subset on 6 URLs, B + F if
Neo4j cohorts exist) are feasible if Q32-Q34 are favorably adjudicated. D and E are
structurally infeasible without infrastructure work outside the P-chain scope.

The recommended path forward is honest pilot launch with the substrate as-shipped
(M.1's 5/6 predicates firing on real bid data) rather than blocking pilot on
retrospective validation that the data surface cannot support.

**Hand-off pointer**: this memo at `docs/audits/LUXY_PILOT_CAMPAIGN_DATA_ACCESS_AUDIT.md`.
P.0 is read-only; no test surface change; no production data accessed during this audit.
Q32-Q36 await Claude Proper / Chris adjudication; ANALYSIS-C can ship as P.1 immediately
with no further adjudication needed.
