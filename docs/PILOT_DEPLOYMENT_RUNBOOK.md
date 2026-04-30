# LUXY Pilot Deployment Runbook — 2026-04-30

**Audience:** Chris + Becca (StackAdapt operator) + future deploy session.
**Purpose:** Repeatable steps to ship the current branch state to Railway + apply Aura migrations + verify pilot readiness.

This runbook is the operational artifact for **Audit Item 16** (Phase F). It assumes the code state at HEAD on `feature/hmt-dashboard` after this session's commits.

---

## Pre-deploy state at this commit

**What's deployed-ready:**
- 287 modules in `adam/intelligence/` + 30-atom DAG + cascade modulation chain (14 stages, all wired)
- M2 (causal_forest) + M3 (hierarchical_bayes) lib pins added to `requirements.txt` + `pyproject.toml`
- M4 schema migration (029) verified end-to-end via `scripts/smoke_test_phase_f_m4_schema.py`
- StackAdapt GraphQL adapter wired through factory (commit `9649941` + duplication-fix `2ee9522`)
- All 39 daily tasks register at startup (Tasks 34/35 added 2026-04-29)
- Policy gate CLI shipped (`scripts/run_policy_gate.py`)
- 2727 unit tests passing

**Known gaps (NOT pilot-blocking, documented for awareness):**
- Plant model adjudicator extension (Weakness #4 LONG POLE — separate slice)
- Per-cell `processing_depth_counts` aggregator (Tier 2 #0a — post-pilot calibration)
- LUXY's current campaigns are Display + CTV (no text creatives in API for `creative_feature_scoring`)
- Phase G dashboard endpoints (`/internal/contribution-state`, `/internal/argument-cache-state`, `/internal/posture-state`) — partner UI v5 work
- 10 of 11 multi-write Neo4j sites still non-atomic (pilot-critical one fixed in commit `9e90243`)

---

## Step 1 — Pre-deploy checklist

Run these in order from a clean checkout of the deploy branch.

### 1.1. Verify dependencies install cleanly

```bash
pip install --upgrade -r requirements.txt
python3 -c "import pymc, numpyro, econml, jax, statsmodels; print('all libs present')"
```

Expected: all five libs import. The pinned versions (numpyro<0.20, jax<0.5, statsmodels>=0.14.5) are compat-band — see commit `98900ec` rationale.

### 1.2. Run the M2 + M3 lib smoke

```bash
python3 scripts/smoke_test_m2_m3_libs.py
```

Expected exit: 0. Synthetic 24-cell hierarchical Bayes fit + 200-row causal forest fit both succeed. Does NOT touch Aura.

### 1.3. Run unit tests

```bash
python3 -m pytest tests/unit/ -q --no-cov
```

Expected: 2727+ passing, 3 skipped.

### 1.4. Verify Phase B (per-atom contribution + CAI) flows

```bash
python3 scripts/smoke_test_phase_b_contribution_and_cai.py
```

Expected exit: 0.

---

## Step 2 — Apply Aura migrations

**Critical:** Aura migrations are write operations. Run from a controlled environment (Railway shell or a one-off ops VM). Coordinate with Becca for the maintenance window.

### 2.1. Set production Aura env vars

```bash
export NEO4J_URI=neo4j+s://<aura-instance>.databases.neo4j.io
export NEO4J_USERNAME=neo4j
export NEO4J_PASSWORD=<aura-password>  # from Aura console
```

These come from the Aura console; the local `.env` points at `bolt://127.0.0.1:7687` (dev). DO NOT commit production values.

### 2.2. Dry-run migrations against Aura

```bash
python3 -m adam.infrastructure.neo4j.migration_runner --dry-run --database neo4j
```

Expected output: list of pending migrations. Per local-Neo4j run on 2026-04-30, only migration 029 (`add_ts_propensity_to_ad_decision`) was pending. Aura state may differ — investigate the diff before applying.

### 2.3. Apply migrations

```bash
python3 -m adam.infrastructure.neo4j.migration_runner --database neo4j
```

Expected: each pending migration applies. Migration 029 marks all existing `:AdDecision` rows as `pscore_known=false` (Boruvka 2018 §2 discipline — pre-M1 rows have no logged propensity) and creates indexes `ad_decision_user_created` + `ad_decision_pscore_known`.

### 2.4. Run the M4 schema smoke against Aura

```bash
python3 scripts/smoke_test_phase_f_m4_schema.py
```

Expected exit: 0. Verifies:
- Migration 029 applied
- Both indexes exist
- Synthetic `:DecisionContext` write+read with M4 fields succeeds
- `pscore_known=false` rows correctly EXCLUDED by OPE filter

If this fails, OPE/WCLS would silently return zero rows. Do not proceed.

---

## Step 3 — Railway deployment

### 3.1. Required env vars on Railway

Set these in Railway's project settings (NOT in repo):

| Var | Source | Notes |
|---|---|---|
| `NEO4J_URI` | Aura console | `neo4j+s://...databases.neo4j.io` |
| `NEO4J_USERNAME` | Aura console | typically `neo4j` |
| `NEO4J_PASSWORD` | Aura console | rotated quarterly |
| `REDIS_URL` | Railway add-on | Redis instance for cache |
| `ANTHROPIC_API_KEY` | Anthropic console | for Claude scoring (CAI loop, page features, creative features) |
| `STACKADAPT_API_KEY` | StackAdapt → Becca | bearer token, GraphQL write privileges |
| `STACKADAPT_GRAPHQL_KEY` | same | both names read by client (compat) |
| `STACKADAPT_GRAPHQL_ENDPOINT` | StackAdapt | `https://api.stackadapt.com/graphql` |
| `STACKADAPT_WEBHOOK_SECRET` | generate 32-byte hex | shared with Becca for webhook config |
| `STACKADAPT_WEBHOOK_DEDUP_TTL_SECONDS` | `172800` | 48h conservative dedup window |
| `ENVIRONMENT` | `production` | |
| `LOG_LEVEL` | `INFO` | |

### 3.2. Deploy

Push the deploy branch. Railway auto-builds via the existing pipeline. Verify in Railway logs:

- `[main]` `Daily Intelligence Strengthening scheduler queued`
- `[main]` `Page intelligence crawl scheduler started`
- `[main]` `Operations Intelligence Engine started`

### 3.3. Post-deploy health check

```bash
curl -H "X-API-Key: <internal-key>" https://<railway-url>/health/ready
```

Expected: `{"ready": true}` with `neo4j: connected`, `redis: connected`.

### 3.4. Post-deploy smoke

The deployed service runs the daily scheduler at 5-minute ticks. Tasks 34 (HB nightly refit) + 35 (CF weekly fit) run at their canonical schedule (02:00 + 03:00 UTC). On first tick, expect:

- Task 34 DRY: `cells_recovered` may be 0 if no observations exist yet — that's expected
- Task 35 DRY: `cells_discovered` may be 0 — expected pre-pilot

Nothing should error on lib import (M2/M3 libs are now installed).

---

## Step 4 — StackAdapt operator handoff (Becca)

### 4.1. Webhook configuration

Becca configures the StackAdapt conversion webhook to POST to:

```
https://<railway-url>/api/v1/stackadapt/webhook
```

With:
- `Authorization: Bearer <STACKADAPT_WEBHOOK_SECRET>` (HMAC-SHA256 — see `webhook.py:auth`)
- Event types: conversions + clicks (refunds optional but recommended)

### 4.2. Bid-time activation

The cascade is reachable at `/api/v1/stackadapt/creative` with the bid-request payload shape (see `adam/api/stackadapt/models.py`). Becca's bidding integration sends:

- `segment_id` — the LUXY archetype tag (e.g., `professionals_corporate`)
- `asin` — the LUXY product/listing ID
- `buyer_id` — StackAdapt postback ID
- `device_type`, `time_of_day`, `iab_category`, `page_url` — bid-request signals

Response includes `primary_mechanism`, `secondary_mechanism`, `mechanism_scores`, `framing`, `tone`, plus a `decision_id` for the outcome roundtrip.

### 4.3. Pixel-side: sapid registration

Every bid response carries `decision_id` (the sapid). Becca's pixel must echo this back on conversion events so the sapid round-trip rate stays ≥95% (Phase 10 RED criterion 8). The webhook already handles missing-sapid gracefully (records `unresolved`).

### 4.4. The DRAFT slot is real

Per the live-API smoke, LUXY's StackAdapt account already has a DRAFT campaign named `ZGM-Display-Prospecting-Informativ` — that's the slot Becca prepared for the integration. Move it from DRAFT → LIVE when:
- Steps 1-3 complete
- M4 smoke passes against production Aura
- Becca's webhook + bid endpoint handshake verified

---

## Step 5 — Monitoring + observability

### 5.1. Prometheus counters that should be live post-deploy

| Counter | Source | What healthy looks like |
|---|---|---|
| `a14_flag_active{atom_id, a14_flag}` | `_increment_a14_counter` in 4 modules (why_library, m2_pipeline, deviation_lifecycle, cai_cross_family_critic) | Increments per emission; cardinality bounded by atom_id × flag |
| `cascade_level_reached{level}` | `bilateral_cascade.py` | L3 dominates after warm-up; L1/L2 only on cold queries |
| `cascade_edge_count` | `bilateral_cascade.py` | 30+ edges typical for LUXY ASINs |
| `theory_update_source{source}` | `outcome_handler.py` + ingestion | Increments per outcome event |
| `mrt_propensity_logged_total` | `mrt_producer.py` | Should match cascade decision count + epsilon-floor sample rate |

### 5.2. OPE readiness check

After 24-48 hours of live traffic:

```cypher
MATCH (dc:DecisionContext)
WHERE dc.created_at >= timestamp() - 86400000  # last 24h
RETURN
  count(dc) AS total_decisions,
  sum(CASE WHEN dc.pscore_known = true THEN 1 ELSE 0 END) AS pscore_known_rows,
  avg(dc.ts_propensity) AS avg_p_t,
  avg(dc.epsilon_floor) AS avg_eps
```

Expected: `pscore_known_rows / total_decisions` ≈ 1.0 (every cascade decision logs its propensity). `avg_p_t` should sit in [0.02, 0.98] per the ε-floor + K=mechanism-count math.

### 5.3. Sapid round-trip rate

```python
from adam.intelligence.spine.phase_8_stackadapt_integration import get_default_monitor
m = get_default_monitor()
print(f"round_trip_rate: {m.round_trip_rate():.2%} (target ≥ 95%)")
```

If < 95% after 1 week, investigate: are pixel events arriving with the decision_id we stamped?

### 5.4. RED-criteria launch gate

After daily traffic accumulates, run:

```python
from adam.intelligence.spine.phase_10_launch_sequence import (
    LaunchGateInputs, run_launch_gate_evaluation,
)
inputs = LaunchGateInputs(
    n_decisions=<from prometheus>,
    n_floor_violations=<from monitor>,
    n_bids=<from prometheus>,
    n_traces_emitted=<from prometheus>,
    p99_latency_ms=<from prometheus>,
    msprt_decision=<from Phase 9 mSPRT>,
    cmo_review_disposition='comfortable',  # operator-set
    n_creatives_in_rotation=<from StackAdapt>,
    n_creatives_failed_spot_check=0,
    # sapid_round_trip_rate left None — runner reads from monitor
)
result = run_launch_gate_evaluation(inputs)
if result.any_triggered:
    print(f"LAUNCH DEFERRED: {result.triggered_criteria}")
```

Per Phase 10: ANY triggered criterion → DEFERRED.

---

## Step 6 — Rollback

If anything breaks post-deploy:

### 6.1. Code rollback

Revert to the previous Railway deploy via Railway dashboard. Production traffic falls back to the prior cascade state.

### 6.2. Aura schema rollback

Migration 029 is REVERSIBLE (per the migration's docstring):

```cypher
DROP INDEX ad_decision_user_created IF EXISTS;
DROP INDEX ad_decision_pscore_known IF EXISTS;
MATCH (d:AdDecision) REMOVE d.pscore_known;  // optional — leaving it set is harmless
```

DON'T drop migration 029's `:Migration` row unless you intend to re-run it later.

### 6.3. StackAdapt rollback

If the cascade is producing bad recommendations: pause the LUXY campaign in StackAdapt (Becca-side) and switch the bidding back to the prior non-INFORMATIV adapter. The pause is reversible.

---

## What's NOT in this runbook (anticipated future connections)

These pieces don't yet exist; the deployment chain has hooks ready for them:

1. **Partner UI v5** (`website_v4_design_spec.md`) — when shipped, will surface a14_flag_active counter + per-atom contribution + sapid round-trip rate as a partner-facing readout. The Prometheus counters are already live.

2. **`/internal/*` monitor endpoints** (Phase G) — will consume the same Prometheus counters this runbook describes. The data is flowing; the endpoints just need to expose it.

3. **Plant model adjudicator extension** (Weakness #4 LONG POLE) — when shipped, the cascade's `recommendation_class/adjudicator.py` will wire to live `processing_depth_counts` aggregates. Schema is ready; the aggregator is the gap.

4. **Image OCR / video transcription bridge** — for scoring LUXY's current Display + CTV creatives via `creative_feature_scoring`. Until built, blend_fit on real LUXY ads is not possible (no text creative in API). Per `feedback_use_live_data_never_simulate`, partial-real-data with synthesized text anchored to campaign theme is acceptable.

5. **Becca's operator dashboard** — currently the StackAdapt UI is the operator surface. A dedicated INFORMATIV operator dashboard would consolidate the items in §5.1-5.4 above.

---

## Done criterion for pilot launch

The runbook is complete + the LUXY DRAFT slot can move to LIVE when:

1. Step 1 checklist (lib install, smokes, tests) — green ✓
2. Step 2 (Aura migrations applied + M4 smoke) — green
3. Step 3 (Railway deploy + health check) — green
4. Step 4 (Becca handshake on webhook + bid endpoint) — verified
5. Step 5.4 RED-criteria launch gate evaluation — `any_triggered = false`
6. Chris-supervised first-day soak (10% budget, daily monitoring tick)
