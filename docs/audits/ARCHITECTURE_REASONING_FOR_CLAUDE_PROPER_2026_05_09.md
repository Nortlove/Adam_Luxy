# ADAM Architecture Reasoning Memo for Claude Proper
## Slice ID: Architecture Reasoning 2026-05-09
## Predecessor: PLATFORM_SYSTEM_DEEP_DIVE_2026_05_09.md (Phase 1 inventory)
## Audience: Claude Proper (architectural decision support)
## Audit type: Read-only architectural inspection
## Scope: Railway deployment + frontend + interpret-learn-test-change loop + reporting
## Branch: feature/hmt-dashboard

---

## §1 Executive Summary for Claude Proper

This memo is **the reasoning layer above Phase 1's inventory**. Phase 1 (`PLATFORM_SYSTEM_DEEP_DIVE_2026_05_09.md`, ~7,400 words / 22 sections) catalogued WHAT exists across the platform — file paths, line numbers, operational ratings, deferred work. Phase 2 (this memo) explains WHY it's built that way, what constraints shaped it, what patterns recur, what's still pivot-able vs locked in, and what architectural questions Chris would benefit from your direct input on.

You should read Phase 1 first as the substrate map. Phase 2 then equips you to make recommendations that follow the existing grain of the system rather than fighting it. The four focus areas Chris named — **Railway-deployed platform**, **frontend system**, **interpret-learn-test-change loop**, **reporting structure** — are the consumer-facing surface of a substrate that is unusually deep. The deepest finding from Phase 1 (§21 honest assessment + §6 package structure): the platform is *substrate-rich and consumer-thin*. Vast operational substrate exists in `adam/` (30+ Atom of Thought modules at `adam/atoms/core/`, the LangGraph workflows layer with `synergy_orchestrator.py` at 2,690 LOC and `holistic_decision_workflow.py` at 1,636 LOC, ~10 distinct learning systems wired through a 2,873-line `OutcomeHandler` at `adam/core/learning/outcome_handler.py:31`, a substantial causal-inference layer at `adam/intelligence/causal_*.py`, etc.) — and a comparatively thin set of consumer-facing surfaces actually exposes that substrate to operators. The bilateral cascade decides cell-conditionally; the dashboard does not yet reveal cell-conditional outcomes. The OutcomeHandler runs 10+ learning sub-updates per conversion; the `learning/` route in the dashboard exposes a small subset.

The architectural question Chris is wrestling with is **how to close the iteration loop**: the system needs to interpret what's happening on the active LUXY campaign, learn from it, test changes, and determine HOW and WHAT to change — and right now the substrate to do this is largely built, but the consumer-facing decision-making surface (frontend + reporting) doesn't yet expose the substrate's outputs in a form an operator can act on. The four focus areas are not coequal — the loop and the reporting are gating, the frontend is the operator's window into them, and Railway is the execution context that constrains all three. Recommend reading the four areas in this order: §4 (loop) → §5 (reporting) → §3 (frontend) → §2 (Railway). The §6 cross-cutting synthesis and §7 architectural questions are where your input has highest leverage.

---

## §2 Focus Area 1 — Railway-deployed platform

### §2.1 What's built

The Railway deployment is **a single-process FastAPI service** specified by `railway.toml:23` (`startCommand = "uvicorn adam.main:create_app --host 0.0.0.0 --port 8000 --workers 1 --timeout-keep-alive 30 --timeout-graceful-shutdown 10"`), built from `deployment/Dockerfile` via NIXPACKS, deployed alongside a Railway-managed Redis service (per `deployment/DEPLOY_RAILWAY.md` Step 3). Application state lives in three external systems: **Neo4j Aura** (`neo4j+s://...databases.neo4j.io`, free-tier instance, currently paused per session investigation), **Redis** (Railway plugin in production; in-process LRU caches as L1 in front), and **process-local Python singletons** (per the `railway.toml:25-30` and `adam/main.py:47-65` multi-worker guardrail: `ThompsonSampler`, `GraphIntelligenceCache`, `_ARCHETYPE_MECHANISM_PRIORS`, `BuyerUncertaintyProfile` registry).

The FastAPI app at `adam/main.py:332` registers ~20 routers including `dashboard_router`, `stackadapt_router`, `stackadapt_webhook_router`, `decision_router`, `intelligence_router`, `iheart_router`, `wpp_router`, `universal_router`, `retargeting_router`, `signals_router`, `negative_outcomes_router`, `monitoring_router`, `learning_router`, `metrics_router`, `health_router`, plus admin routers (`admin_auth`, `admin_org`, `admin_campaign`, `admin_client`). Lifespan startup at `adam/main.py:40-65` runs Neo4j migrations (idempotent via `migration_runner`), initializes `LearningComponents` singleton, and seeds `CustomerArchetype` + `CognitiveMechanism` schema nodes if missing (per Audit #4 fix). Production env vars at `deployment/.env.production` cover application identity, API keys, CORS origins, Neo4j connection, Redis connection, Anthropic Claude API, StackAdapt credentials (advertiser ID, API key, pixel ID, webhook secret), explicit latency budget knobs (`LATENCY_TOTAL_MS=120`, `RESERVE_MS=10`, `PREFETCH_MS=40`, `CASCADE_MS=60`, `DAG_MS=80`), and retargeting thresholds (`MAX_TOUCHES=7`, `REACTANCE=0.85`, `CTR_FLOOR=0.0003`).

### §2.2 Why it's built this way

**Single-worker constraint is the dominant architectural commitment.** Inference: from the explicit `railway.toml:25-30` comment + `adam/main.py:47-65` runtime guardrail, the team chose process-local singletons over a shared-state backend (Redis posteriors or sticky routing) for the learning loop. Reading: ThompsonSampler posteriors, `GraphIntelligenceCache` Neo4j+Redis read-through state, `_ARCHETYPE_MECHANISM_PRIORS`, and `BuyerUncertaintyProfile` registry are all updated in-process; multi-worker would silently diverge. The chosen tradeoff: **simplicity + correctness now**, at the cost of vertical-scaling-only until shared-state lands. The `adam/main.py:60-64` warning is loud (`logger.critical`); the constraint is honored. Inference: this decision is consistent with the audit-first / fail-soft pattern across the codebase — bias toward not-being-wrong over being-faster.

**Push-not-pull StackAdapt integration** (per `campaigns/ridelux_v6/STACKADAPT_INTEGRATION_ARCHITECTURE.md:7-17`): "StackAdapt does NOT support calling an external API per impression. The integration model is push, not pull: we push intelligence INTO StackAdapt via GraphQL, not StackAdapt pulling from us at bid time. This changes our architecture from 'real-time per-impression decisioning' to **pre-computed psychological campaigns with continuous learning**." This is a load-bearing constraint that shapes everything: the Railway service is NOT in StackAdapt's bid-time hot path; it's an offline/near-real-time intelligence engine that pushes campaign config + learns from postback events.

**Aura Free Tier choice** (per `deployment/DEPLOY_RAILWAY.md:24-30`): "Free tier (200K nodes, 1 database — plenty for pilot)". Inference: deliberate cost-minimization for pilot; assumes single-customer scale; the auto-pause behavior I encountered this session is a known cost of that choice. Aura instance `3181c986` returns NXDOMAIN when paused — the platform's bid path has graceful degradation around this (per `graph_cache.py` fail-soft on driver acquisition) but learning loops that depend on RESPONDS_TO edge writes go silent during the pause.

**Latency budget articulated in env vars** (`LATENCY_TOTAL_MS=120` etc.) — Inference: the team committed to performance budgeting *as configuration*, not just as code comments. This is a pattern Chris would benefit from applying further: Q22's revised aggregator p99 budget (8ms → 12-15ms) lives in `tests/cells/test_aggregator_fomo.py:p99` test assertions but should probably also live in env-var-configurable thresholds for production tuning.

### §2.3 Patterns + anti-patterns

**Patterns recurring in the Railway/runtime layer:**
- *Idempotent migrations on startup* (`adam/main.py:94-111`, `migration_runner`): MERGE-based Neo4j operations safe to re-run; non-blocking on failure (logs warning, doesn't crash startup).
- *Soft-fail at infrastructure boundary*: `Infrastructure.initialize()` failures in non-production fall back to mock infrastructure (`adam/main.py:80-85`). Production raises.
- *Singleton with lifecycle management*: `Infrastructure.get_instance()`, `LearningComponents.get_instance()` — startup initializes, shutdown cleans up; the `lifespan` async context manager owns ordering.
- *Schema-existence MERGE on startup* (`adam/main.py:124+`): `CustomerArchetype` + `CognitiveMechanism` ensured to exist so RESPONDS_TO updates don't silently match zero rows. This is a *pattern of defense against silent learning-loop breakage* worth replicating elsewhere.
- *Health endpoint as Railway contract*: `/health` is the restart-decision input. Liveness vs readiness distinction not surfaced — Inference: the team is okay with conflating them at pilot scale.

**Anti-patterns avoided:**
- No multi-worker scale-out before shared-state backend (the `WEB_CONCURRENCY` guardrail is explicit).
- No sync database calls in async handlers (the priming feature store at `adam/priming/feature_store.py:158` is async; W.1's sync adapter at `adam/cells/accessors.py:make_priming_accessor` reaches into `_l1` LRU directly to avoid `asyncio.run` per Q21).
- No production deployment without explicit env-var configuration (all secrets are `<<REPLACE_WITH_*>>` placeholders in the template; nothing leaks).

**Anti-patterns present:**
- *Sprawling router registration*: 20 routers at `adam/main.py:451-553` with no clear hierarchy. Inference: organic growth; refactoring opportunity but not pilot-blocking.
- *Tight coupling between FastAPI app and learning components*: `LearningComponents.get_instance(infra)` is a global singleton; testing requires per-test reset or full app construction. Inference: the test suite works around this rather than fixing it.

### §2.4 Constraints

**Explicit constraints:**
- `--workers 1` MANDATORY (singletons; documented).
- 70ms total bid budget per directive (decomposed in env vars).
- Aura Free Tier: 200K node cap, single database, auto-pause after inactivity.
- Railway-managed Redis: connection via plugin env vars (`REDIS_HOST`, `REDIS_PORT`, `REDIS_PASSWORD`).
- Anthropic API rate limits (Claude Sonnet 4 model; 60s timeout per `CLAUDE_TIMEOUT=60`).

**Emergent constraints surfaced this session:**
- Aura paused → DNS NXDOMAIN → bid path soft-fails to defaults; learning loop conversion-event update path silently no-ops.
- Dev environment cannot reach production Aura without env-var override (default `bolt://localhost:7687` per `deployment/.env.production:75`).
- Local Neo4j Desktop runs the brand-side / review-corpus DBMS; buyer-side cohort data lives only in Aura.
- Per Phase 1 §5 audit chain: M.0 finding that `extract_mindstate_vector` lives in outcome_handler learning paths only — the bid path constructs no PageMindstateVector. M.1 closed this for fomo; depletion + ownership remain dormant per Q29=BETA.

### §2.5 Open architectural questions

1. **Shared-state backend for the learning singletons** — the `--workers 1` guardrail is "until shared-state lands." Should this land before pilot scale or post-pilot? Tradeoff: building Redis-backed posteriors / sticky routing now adds complexity but unlocks horizontal scale; deferring keeps simplicity but caps throughput at one Railway dyno.
2. **Aura tier upgrade timing** — Free-tier auto-pause is a learning-loop break risk. Upgrade to a paid tier with no auto-pause before pilot? Cost vs reliability tradeoff.
3. **Should the Railway service be one app or split?** Currently 20 routers in one FastAPI app. Splitting by domain (cascade-decisioner / dashboard-BFF / webhook-receiver / admin) would isolate failure modes and let each scale independently — but multiplies deployment complexity and breaks the singleton model.
4. **Latency budget enforcement** — `LATENCY_TOTAL_MS=120` is configured but I see no runtime kill-switch that hard-cuts a request at the budget. Does the cascade voluntarily honor it (graceful degradation) or hard-enforce it (timeout-driven)? Reading the cascade would clarify.

### §2.6 Optionality vs lock-in

**Locked in:**
- Single-worker process model (architectural commitment encoded in env-var guardrail + singleton design across 4+ subsystems; reversing requires building Redis-backed shared state for ThompsonSampler + GraphIntelligenceCache + posteriors).
- Push-not-pull StackAdapt model (constraint imposed by StackAdapt; not pivot-able).
- FastAPI + Pydantic + uvicorn stack (deeply embedded; ~150 modules import this stack).
- Neo4j as graph store of record (RESPONDS_TO + ConversionEdge + DecisionTrace + UserCohort schemas; cypher queries throughout; switching to a different graph DB would be a massive refactor).
- Redis as L2 cache + posterior store (BuyerUncertaintyProfile JSON serialization at `graph_cache.py:_save_buyer_profile_to_redis`; 90-day TTL).

**Pivot-able:**
- Railway as the deployment target (Dockerfile is generic; AWS scripts exist at `deployment/aws-setup.sh`; could move to ECS/Fargate or Kubernetes without code changes).
- Aura Free vs paid tier (configuration choice).
- Worker count (when shared-state lands).
- Router organization (refactoring without breaking API contracts is feasible).
- StackAdapt as DSP (the integration is contained at `adam/api/stackadapt/`; other DSPs could mount sibling routers — `adam/dsp/` shell already exists).

---

## §3 Focus Area 2 — Frontend system

### §3.1 What's built

**A Next.js 16 + React 19 dashboard at `dashboard/`** with three top-level route groups (`dashboard/src/app/`):
- `(app)/` — operator-facing app: 8 routes (`analytics`, `calibration`, `campaigns`, `discovery`, `learning`, `ledger`, `recommendations`, `settings`)
- `(client)/client/` — client-facing: `report` route
- `api/` — Next.js BFF API routes (proxy layer to the FastAPI backend)

Stack per `dashboard/package.json`: Next 16.2.4, React 19.2.4, Tailwind 4, shadcn 4.3.1, @base-ui/react 1.4.1, @tanstack/react-query 5.99.2 (data fetching), Zustand 5.0.12 (state), recharts 3.8.1 (visualization), cmdk 1.1.1 (command palette), date-fns. Build via pnpm; types generated from FastAPI's OpenAPI spec via `pnpm gen:types` (target: `${OPENAPI_URL:-http://localhost:8000/openapi.json}` → `src/lib/api-types.gen.ts`). The BFF pattern is concrete: `dashboard/src/app/api/learning/mechanism-effectiveness/route.ts` proxies browser calls to the FastAPI `/api/dashboard/learning/mechanism-effectiveness` endpoint with `Authorization` headers added server-side.

The FastAPI dashboard router at `adam/api/dashboard/router.py:80` (`prefix="/api/dashboard"`) exposes ~30+ endpoints organized by concern: `/health`, `/me`, `/campaigns`, `/analytics/summary`, `/tenants/me`, `/tenants/hierarchy`, `/settings/autopilot` (GET + PUT), `/decay/report`, `/why-library`, `/recommendations`, `/ledger/deviations`, `/ledger/calibration`, `/ledger/claims`, `/agency-view-a`, plus larger blocks for system-insights, client-decisions, client-report, and recommendation-decision endpoints. Service modules sit alongside the router: `system_insights_service.py`, `client_decisions_service.py`, `client_report_service.py`, `service.py`, `auth.py`. The learning sub-routes have dedicated subcomponents in the dashboard: `dashboard/src/app/(app)/learning/_components/` includes `why-library.tsx`, `horizons.tsx`, `decay-report.tsx`, `subject-inspection.tsx`, `mechanism-effectiveness.tsx`, `adjudicate-button.tsx`. The `ledger/` route has `calibration-view.tsx`, `claims-table.tsx`, `sandbox.tsx`, `deviations-table.tsx`. Discovery + elicitation UIs live separately at `dashboard/src/components/discovery/` and `dashboard/src/components/elicitation/`.

### §3.2 Why it's built this way

**Next.js BFF pattern over direct browser-to-FastAPI calls** — Inference: lets server-side code add Authorization headers (per `route.ts` files), keeps API keys out of browser, and gives a place to do response shaping for UI. This is a deliberate choice over a thin SPA + direct CORS-enabled API. The pattern matches industry-standard "BFF for security" reasoning.

**OpenAPI-generated TypeScript types** (`pnpm gen:types`) — Inference: keeps types in sync between Python Pydantic models and TypeScript without hand-maintenance. The generation target is configurable (`OPENAPI_URL` env var) so the dashboard can target local-dev or production schemas. This is a healthy pattern that prevents API drift; underused elsewhere in the platform (the StackAdapt GraphQL types appear hand-coded based on file names like `models.py`).

**Modern stack choices (Next 16 / React 19 / Tailwind 4 / shadcn 4)** — Inference: the team picked the most current production-stable versions when this branch was created. shadcn (component library) over Material-UI or Chakra suggests preference for headless-component flexibility; Zustand over Redux suggests preference for minimal-boilerplate state.

**Route organization by concern, not by data type** — `analytics`, `calibration`, `campaigns`, `discovery`, `learning`, `ledger`, `recommendations`, `settings` reflect operator workflows (what the operator is doing) rather than data tables (`/users`, `/cohorts`, `/cells`). Inference: the team is building toward a *narrative-driven operator console* rather than a *CRUD admin panel*. This is consistent with Chris's directive about interpret-learn-test-change-loop framing.

**Recommendation queue as a first-class route with `[id]/decide` action** — Inference: the system is designed to surface its own proposed campaign changes to a human approver, who clicks `decide` to apply or reject. This is the **operator-in-the-loop** model — automation proposes, human disposes. Aligns with Chris's discipline rules about not auto-shipping changes that the operator hasn't sanctioned.

### §3.3 Patterns + anti-patterns

**Patterns:**
- *BFF proxy with hand-shaped routes per backend endpoint* (`route.ts` files in `dashboard/src/app/api/`): each route is small, explicit, no automatic passthrough. Tradeoff: more files to maintain, but type safety + auth handling is per-route.
- *Server-side actions* (`actions.ts` per route): leverages Next 16 Server Actions for mutation calls. Inference: keeps mutation logic on the server side rather than client-side fetch + state update.
- *`_components/` private subdirectory per route*: Next.js convention; co-locates route-specific UI with its page. Healthy organization.
- *Recharts for visualization* — declarative React-friendly charting; consistent across `analytics`, `learning`, `ledger`.
- *@tanstack/react-query for data fetching* — caching + optimistic updates + background refresh built-in. Standard for modern React data apps.

**Anti-patterns possibly present (warrants verification):**
- *Limited test coverage on the dashboard itself* — no `dashboard/__tests__/` or similar visible; Inference: the testing investment is on the Python backend (5,897 tests) not the React UI.
- *Two tenant types in the same app (operator + client)* — `(app)` and `(client)` route groups share the same Next deployment. Inference: deliberate to keep deployment simple; risk: operator-only routes accidentally accessible to client tenants if auth middleware misfires. The `auth.py` in `adam/api/dashboard/` likely handles this but warrants explicit per-route audit.

### §3.4 Constraints

- **Backend API contract** — frontend can only show what `/api/dashboard/*` exposes. Phase 1 §7 noted "what's MISSING is cell-conditional configuration UI in the campaigns route (audience-as-cells, predicate selection per campaign, threshold tuning, decision-trace observability per campaign)." Adding these requires coordinated FastAPI endpoint additions + dashboard route updates — they don't exist independently.
- **Single-process FastAPI server** — every dashboard request hits the same uvicorn worker that serves bid-time cascade requests. Heavy dashboard queries (e.g., decision-trace exports) compete for the same process; if a dashboard query is slow, it blocks bid-time latency budgets.
- **Aura connection state** — many dashboard queries (cohort views, decision-trace history, learning posterior state) read from Neo4j. When Aura is paused, the dashboard surfaces empty states or errors rather than meaningful data.
- **Operator authentication model** — the `admin_*` routers at `adam/main.py:548-551` (`admin_auth`, `admin_org`, `admin_campaign`, `admin_client`) suggest a multi-tenant org model. Inference: the dashboard supports per-tenant access control but the implementation depth needs verification.

### §3.5 Open architectural questions

1. **Should the dashboard be its own Railway service?** Currently the Next dashboard is a separate codebase but probably shares the FastAPI backend's Railway deployment for the API layer. Splitting Next to its own Railway service (or Vercel) would isolate dashboard load from bid-path load. Tradeoff: deployment complexity vs latency-budget protection.
2. **Cell-conditional UI extension scope** — Phase 1 §13 itemized 6 missing campaign-creation features (audience-as-cells; creative variant assignment per cell; budget allocation across cells; predicate selection per campaign; cold-start fallback config; decision-trace observability toggle). Should these ship as one slice or sequenced? Architecturally: do they share data models (probably) or can each be independent (some)?
3. **Operator vs client view boundary** — what does a LUXY-side viewer see vs what does an INFORMATIV operator see? The `(client)/client/report/` route exists but the per-route auth/scoping logic warrants explicit specification.
4. **Real-time updates** — the dashboard appears to use polling via React Query rather than WebSockets/SSE. For decision-trace observability "what just fired in the last second," polling has latency. Architecturally: is this acceptable for pilot, or should real-time event streaming be added?
5. **Decision-trace exposure granularity** — should the dashboard show per-impression decision traces (high cardinality, deep introspection) or per-cell aggregates (low cardinality, summary view) or both? This is a UX question with architectural consequences (data volume + storage).

### §3.6 Optionality vs lock-in

**Locked in:**
- Next.js as the framework (deeply embedded; switching to Remix or SvelteKit would be a rewrite).
- shadcn component library (UI primitives are shadcn-shaped; would require re-skinning for a different lib).
- BFF proxy pattern (every existing route follows it; consistency has value).
- pnpm as package manager.

**Pivot-able:**
- Specific UI routes / screens (each is a single-file component or small directory; adding/reorganizing routes is cheap).
- Visualization library (recharts could be swapped for another chart lib at the component level).
- State management (Zustand is locally scoped; can layer Redux or other if needed without ripping out).
- Hosting target (Next can deploy to Vercel, Netlify, Railway, or self-hosted with no code change).
- Server Actions vs API route preference (both supported; can mix per use case).

---

## §4 Focus Area 3 — Interpret-learn-test-change loop

### §4.1 What's built

This is the most architecturally significant area Chris named — the **closed loop from observation → interpretation → learning → testing → change determination → change application**. The platform's substrate for this loop is unusually deep.

**Observation surface:** every served impression goes through `run_bilateral_cascade` at `adam/api/stackadapt/bilateral_cascade.py` and produces a `DecisionTrace` record (per `adam/intelligence/decision_trace_emitter.py`, Spine #6). The trace includes the chosen creative, the chosen mechanism, all alternatives' propensities (computed via ε-floor-mixed argmax + epsilon_floor_mix), the cell features, the predicate firings, the modulations applied. The trace is emitted synchronously to an in-memory log; an async drainer flushes to Redis (hot tier; `decision_trace_store.py`) and Neo4j (long-term archival; `decision_trace_neo4j.py:DecisionTrace` node with `MADE_DECISION`, `USED_MECHANISM` edges). Conversion events arrive via the `POST /api/v1/stackadapt/webhook/conversion` endpoint at `adam/api/stackadapt/webhook.py` (HMAC-SHA256 + event_id deduplication). The webhook dispatches to `OutcomeHandler.process_outcome()` at `adam/core/learning/outcome_handler.py:43`. The outcome closure (`adam/intelligence/outcome_trace_closure.py`) writes the `(:ConversionEdge)-[:RESOLVED]->(:DecisionTrace)` edge in Neo4j, joining the (decision, outcome) pair for OPE estimators (`adam/intelligence/ope.py` per code references).

**Interpretation surface:** the cascade itself is interpretation — substrate signals (archetype, cohort, posture, priming, mindstate composites, maximizer posterior) compose into mechanism scores via the 5-level bilateral cascade. The cells/predicates layer (S6.2 + W chain + M.1) further conditions creative selection on cell features. The Atom of Thought DAG (30+ atoms at `adam/atoms/core/`) provides decision-time cognitive reasoning that hangs off cascade output. The `causal_decomposition.py:CausalRecipe` engine identifies "the 3-5 dimensions that were the ACTIVE CAUSAL INGREDIENTS" of a specific conversion (cross-disciplinary inspiration: gene expression analysis identifies which genes are "turned on" in a specific cell state).

**Learning surface:** `OutcomeHandler.process_outcome()` at `adam/core/learning/outcome_handler.py:43` is the central hub — a 2,873-line dispatcher that routes each conversion event to ~10 sub-update paths: `_update_thompson` (Thompson sampling Beta posteriors); `_update_meta_orchestrator` (strategy weights); `_update_neo4j_attribution` (graph-side attribution); `_update_graph_rewriter` (rule effectiveness); `_route_to_learning_hub` (UnifiedLearningHub for all 30 atoms); `_update_theory_learner` (construct-level posteriors); `_update_dsp_learning` (DSP impression learning); `_update_ml_ensemble` (ensemble weights); `_update_cognitive_learning` (psychological learning integration); `_update_page_context_learning`; `_update_mechanism_interactions`; `_update_buyer_profile` (per-user posterior modulation via `graph_cache.update_buyer_profile`); `_update_bilateral_edge_evidence`. Plus `_process_chain_attestations` for atom-level per-link feedback. The W.2.0 audit confirmed `per_user_posterior_modulation` (`adam/intelligence/per_user_posterior_modulation.py:93`) is the empirical-Bayes shrinkage path that updates `BuyerUncertaintyProfile.constructs` Beta posteriors; F.2 added `cohort_discovery.detect_compensatory_consumption_pattern` to populate cohort-side flags. `causal_learning.py` treats every impression as a micro-experiment and discovers `(:PageDimension)-[:AMPLIFIES|:SUPPRESSES|:MODERATES]->(:CognitiveMechanism)` Neo4j edges from observed evidence.

**Testing surface:** sequential probability ratio testing via `adam/intelligence/msprt_campaign_monitor.py` + `msprt_outcome_aggregation.py`. Causal-attribution scaffolding via `causal_adjudicator.py`, `causal_conformal.py`, `causal_dag_ensemble.py` (PC + FCI + GES + DAGMA voting + DoWhy refutation), `causal_decomposition.py`, `causal_discovery.py`, `causal_forest.py`, `causal_structure_learner.py`. Blind-analysis discipline via `adam/blind_analysis/box.py` (parameter-grid blinding before unblinding — the publication-trap defense Reisach-Seng-Schölkopf 2021 identified). Validity layer at `adam/validity/checks.py`. Verification layers (calibration / consistency / grounding / safety) at `adam/verification/`. Red-criteria launch-gate snapshot at `adam/intelligence/red_criteria_snapshot.py` accumulates window counts (bid count, decision-trace emission count, latency p99 ring buffer) for daily Task 42 to evaluate against gate criteria.

**Change-determination surface:** the dashboard's `/api/dashboard/recommendations` endpoint (and the `(app)/recommendations/[id]/decide` route) is the operator-facing surface where the system proposes changes. The proposals come from learning loop outputs — UnifiedLearningHub + DefensiveReasoning renderer (`adam/intelligence/defensive_reasoning.py` + `defensive_reasoning_renderer.py`) + Why Library (`adam/intelligence/why_library.py`). The autopilot setting (`/settings/autopilot`) likely controls how aggressively the system applies changes without operator approval — Inference from endpoint name; full reading of `service.py` would confirm.

**Change-application surface:** the StackAdapt write API. Per `STACKADAPT_INTEGRATION_ARCHITECTURE.md:48-52`: "Weekly Optimizer (learns → adapts) → Updated creatives, paused losers, boosted winners." The Railway service computes desired changes; pushes them to StackAdapt via GraphQL mutations; StackAdapt's DCO engine then serves updated creative.

### §4.2 Why it's built this way

**Centralized OutcomeHandler over distributed event sourcing** — Inference from `adam/core/learning/outcome_handler.py:43-820` structure: the team chose a single 2,873-line dispatcher that explicitly enumerates each learning sub-update over a pub/sub-style event bus where consumers subscribe independently. Tradeoff: explicit dispatch is easier to reason about (you can see every learning system that responds to a conversion) but creates a god-object with high coupling. The `webhook.py` docstring explicitly enumerates 10 systems updated per conversion — that's the dispatch contract. The `UnifiedLearningHub` (`adam/core/learning/unified_learning_hub.py`) sits beneath OutcomeHandler as a partial decoupling: atoms register handlers with the hub rather than OutcomeHandler knowing each atom directly.

**Decision trace as both hot Redis and long-term Neo4j** (per `decision_trace_emitter.py:13-21`): "Hot trace cache in Redis ... Long-term archival in Neo4j." The two-tier choice: Redis serves the demo-loop window (fast retrieval; bounded by TTL); Neo4j carries audit + analytics queries beyond the Redis window. This is the standard hot/cold split for high-volume event data.

**Synchronous emit + asynchronous drain** (per `decision_trace_emitter.py:25-35`): the cascade is sync; storage is async; coupling them directly forces `asyncio.run` from sync context (broken if event loop already running) or fire-and-forget create_task (orphaned tasks). The pattern: sync `emit()` writes to in-memory log; offline `drain_to_storage()` flushes to Redis + Neo4j. This is the same Q21-pattern surfaced in W.1's priming adapter — *no asyncio.run in sync hot paths; pre-cache or post-drain instead*. Worth cataloguing as a system-wide architectural rule.

**Causal learning as discovery, not assertion** (per `causal_learning.py:18-26`): "Validated discoveries become graph edges: (:PageDimension)-[:AMPLIFIES {strength, p_value, n}]->(:CognitiveMechanism). These edges are DISCOVERED from data, not programmed." The cascade reads them at bid time. Inference: this is an explicit anti-hardcoded-theory commitment — the system bootstraps from theory (Cialdini mechanisms, Higgins regulatory focus, etc.) but updates from evidence. Aligns with Chris's "causal understandings, not just iterative ML" directive.

**Operator-in-the-loop with autopilot toggle** — Inference from `/settings/autopilot` GET + PUT endpoints: the system has a configurable autonomy level. Operator can review-then-approve every change, OR delegate certain change classes to autopilot. This is more mature than either pure-automation or pure-manual; matches the "AI proposes, human disposes" pattern that's becoming standard for high-stakes ML systems.

**M7 ensemble for causal DAG discovery** (per `causal_dag_ensemble.py:1-26`): "discover the causal DAG over the 31 identity-stable + 27 alignment + 9 mechanism dims via an ENSEMBLE of methods (PC, FCI, GES, DAGMA), keeping edges that survive ≥2/4 methods. DoWhy refutes high-vote edges via placebo + random-common-cause + unobserved-confounder tests." Discipline anchor: "ALWAYS standardizes inputs before running. A silent unstandardized fit is the publication-trap the test suite pins against." Inference: deep methodological rigor. The team has built defenses against publication-trap failure modes (Reisach et al. 2021 NOTEARS variance-ordering exploit) directly into the code.

### §4.3 Patterns + anti-patterns

**Patterns:**
- *Sync emit + async drain* for hot-path event capture (decision_trace_emitter, mrt_producer, red_criteria_snapshot). Pattern is repeated; worth catalogue + linting.
- *Theory-in-docstring + canonical-formula-in-code + regression-tests-pinning-published-anchors* — the B3-LUXY discipline rule (per `MEMORY.md` user memory). Atoms ship with academic citation in the docstring AND the canonical formula in the implementation AND a test that pins values against published anchors.
- *Empirical-Bayes shrinkage as the unified personalization primitive* — `per_user_posterior_modulation` is the canonical pattern for per-user posterior updates (Beta-conjugate, signal-type-weighted, processing-depth-scaled).
- *Discovery as graph edges, not as feature vectors* — `causal_learning.py` writes Neo4j edges; `causal_dag_ensemble.py` writes typed `(PsychDim)-[:CAUSES]->(PsychDim)` edges. The platform's interpretive substrate IS the graph; queries are first-class.
- *Defensive reasoning + why library* — every consequential decision can produce a human-readable "why" explanation (`why_library.py`, `defensive_reasoning_renderer.py`). Aligns with operator-in-the-loop model.
- *Pre-registered blind analysis* (`adam/blind_analysis/box.py`): parameter grid is blinded before unblinding — defends against post-hoc parameter shopping.
- *Pharmacovigilance-style disproportionality monitoring* (`adam/pharmacovigilance/`): EB05 > 2 per Almenoff/EFSPI for safety signals on negative outcomes.
- *Multiple causal methods voting* (M7 ensemble): no single method wins; consensus required.

**Anti-patterns the loop avoids:**
- *Hardcoded effect sizes* — replaced by causal discovery + posterior updates.
- *Single-method causal inference* — replaced by ensemble + refutation.
- *Single-update pattern hardcoded into bid path* — replaced by OutcomeHandler dispatch + UnifiedLearningHub registration.
- *Direct asyncio.run in sync paths* — replaced by sync-emit-async-drain pattern.

**Anti-patterns possibly present:**
- *OutcomeHandler god-object* — 2,873 lines with ~13 sub-update methods. Inference: refactor opportunity (could become a registry of handlers + dispatcher), but complexity is substantive (each sub-update is a real learning system with dependencies).
- *Implicit ordering in sub-update sequence* — does `_update_thompson` need to fire before `_update_buyer_profile`? Comments at `outcome_handler.py:391-409` suggest yes, with explicit reasoning. But the order is implicit in the Python source order, not declared as a dependency graph. Risk: refactoring could silently break ordering.

### §4.4 Constraints

**Explicit constraints:**
- **Push-not-pull StackAdapt** — change application is bounded by StackAdapt's GraphQL write rate limits + StackAdapt's creative review turnaround time. Real-time per-impression change is impossible; segment-refresh and creative-variant rotation cadences are minutes-to-hours-to-days respectively.
- **Single-worker singletons** — per-user posteriors live in process; survive restart via Redis flush+reload; do not propagate across workers (which is why workers=1).
- **70ms total bid budget** — limits how much interpretation can happen in the bid hot path. Atoms that take >5ms run in async post-bid path or as offline batch.

**Emergent constraints surfaced in audits:**
- **PageMindstateVector never constructed at bid time** (M.0 finding) — the @property derivations on PMV (fomo_score, psych_ownership_proxy, depletion_proxy) only fire in outcome_handler learning paths, not in bid path. M.1 closed this for fomo via aggregator-side bypass; depletion + ownership remain dormant.
- **StackAdapt URL-granularity blocker** (S0_HANDOFF + P.0 audits): served-impression-URL granularity is NOT populated by StackAdapt for the LUXY account. Blocks per-URL outcome attribution; constrains ANALYSIS-D (cell-tuple cross-reference) and ANALYSIS-E (FOMO outcome correlation).
- **5-class vs 4-class posture vocabulary** (Q18, S6.2.0 audit): `FIVE_CLASS_POSTURES` (cells side) and 4-class `attentional_posture` (cascade side) are orthogonal — the 5-class describes WHAT cognitive activity; 4-class describes HOW MUCH attentional allocation. Both flow into the loop independently.

### §4.5 Open architectural questions

These are the most consequential questions Chris would benefit from your input on:

1. **How does the loop close from outcome → posterior → cell → predicate → creative-variant?** End-to-end, what is the latency from a conversion event arriving at the webhook to a corresponding creative-variant change being live in StackAdapt? Today: webhook → OutcomeHandler → posterior updates (sync within process; ~ms); push to StackAdapt write API (offline batch; minutes to hours per `STACKADAPT_INTEGRATION_ARCHITECTURE.md:48-52` "Weekly Optimizer"); StackAdapt review queue (days for new creative; near-instant for variant routing). The loop is *closed* but *slow*. Architectural question: what's the right cadence target, and where are the bottlenecks worth optimizing?

2. **Per-cell vs per-archetype vs per-cohort attribution** — when a conversion fires, which posteriors should update? Currently `_update_buyer_profile` updates the per-user posterior; `_update_thompson` updates archetype-level Thompson sampling; `_update_neo4j_attribution` updates the graph edge. The cell layer (S6.2) doesn't directly receive posterior updates today (predicates are deterministic functions of CellFeatureSet, not learned). Architectural question: should cell-conditional decisions become learned (predicates with weights that update from outcomes) or remain deterministic rules?

3. **Causal claim test infrastructure for the bilateral architecture** — the bilateral architecture's central causal claim is that *multiplicative trait × state composition predicts response better than either trait-alone or state-alone*. Phase 1 §16 noted this doesn't yet have a pre-registered test scaffold. Architectural question: should this scaffold ship pre-pilot (for thesis validation) or rely on post-pilot data + S5.5 nightly retrain to generate the test? The tradeoff: pre-pilot scaffold is methodological discipline but adds work; post-pilot leaves the central claim un-tested for the first month.

4. **OutcomeHandler refactor timing** — the 2,873-line god-object works but is brittle. Splitting into a registry-of-handlers + dispatcher would make adding new learning sub-updates safer (current pattern: open OutcomeHandler, find the right place, add a sub-update method, update the dispatch loop). Question: is this refactor worth doing pre-pilot (when nothing depends on the structure) or post-pilot (when iteration adds many new sub-updates)?

5. **Autopilot autonomy level for pilot** — the `/settings/autopilot` endpoint exists but the default + recommended setting for a brand-new pilot isn't visible to me. Architectural question: should pilot launch with full operator-in-the-loop (every change requires approval) or with autopilot enabled for low-risk change classes (e.g., variant rotation within an approved pool) and operator-in-the-loop for high-risk classes (e.g., pausing campaigns, budget reallocation)?

6. **Decision trace at impression-grain vs aggregate-grain** — the cascade emits a per-impression DecisionTrace; storage is hot Redis + cold Neo4j. At pilot scale (~10K-100K impressions/day) per-impression traces are manageable; at 1M+/day they're expensive. Question: what's the scaling strategy? Option A: aggregate to per-cell decision summaries with sample traces; Option B: keep per-impression but expire fast; Option C: per-impression for a sliding window + aggregate for long-tail.

### §4.6 Optionality vs lock-in

**Locked in:**
- Webhook → OutcomeHandler → multiple sub-update dispatch (the 10-system enumeration in webhook.py docstring is the contract).
- Decision trace as the canonical observation record (pervasive across modules; OPE estimators depend on it; Neo4j queries depend on it).
- Empirical-Bayes shrinkage as the per-user posterior update primitive.
- `(:DecisionTrace)-[:USED_MECHANISM]->(:Mechanism)` and `(:ConversionEdge)-[:RESOLVED]->(:DecisionTrace)` Neo4j schemas.
- BONG multivariate Gaussian for cross-dimension correlation modeling.
- Causal discovery as Neo4j edge writeback (PageDimension AMPLIFIES Mechanism).

**Pivot-able:**
- Specific predicate logic in cells/predicates/ (registered via decorator; trivial to add/remove).
- Specific causal methods in the M7 ensemble (PC + FCI + GES + DAGMA — could add or substitute methods).
- Operator-in-the-loop vs autopilot toggle (configuration, not code).
- DecisionTrace storage tiers (hot/cold split is configurable; could add warm tier or change TTLs).
- Specific atoms in the AoT DAG (atoms are decorator-registered; adding a new atom is bounded).
- Webhook event format (controlled by us per `webhook.py` validation).

---

## §5 Focus Area 4 — Reporting structure

### §5.1 What's built

Reporting is split across **infrastructure-grade observability** (Prometheus + structured logging) and **operator-grade dashboards** (the Next dashboard's `analytics`, `learning`, `ledger`, `recommendations`, `discovery`, `calibration`, `settings` routes).

**Infrastructure observability:**
- `adam/infrastructure/prometheus/` — Prometheus metrics surface; the cascade emits counters and histograms.
- `adam/intelligence/red_criteria_snapshot.py` — in-process accumulator for the launch-gate runner's window counts: bid count, decision-trace emission count, latency p99 (bounded ring buffer of recent N samples). Per `red_criteria_snapshot.py:5-16`: "the launch decision could not be evidenced from inside the system" before this; now the cascade increments per-event and a Daily Task 42 reads + resets per cycle.
- `adam/infrastructure/alerting/` — alerting surface.
- `adam/observability/` — wider observability layer.
- `adam/monitoring/` — runtime monitoring.
- `/api/v1/monitoring/health`, `/health/{component}`, `/drift`, `/alerts`, `/alerts/{alert_id}/acknowledge`, `/alerts/{alert_id}/resolve`, `/metrics/summary` endpoints at `adam/api/monitoring/router.py`.

**Operator-grade dashboard reporting** (per `adam/api/dashboard/router.py:80+` route inventory):
- `/health` — component-level health
- `/me` — current user
- `/campaigns` — campaign list
- `/analytics/summary` — analytics summary
- `/tenants/me`, `/tenants/hierarchy` — tenancy
- `/settings/autopilot` — autonomy level
- `/decay/report` — decay report (Inference: posterior decay over time?)
- `/why-library` — `Why Library` for explanation lookup
- `/recommendations` — recommendation queue
- `/ledger/deviations` — deviations from expected behavior
- `/ledger/calibration` — calibration drift
- `/ledger/claims` — claims log
- `/agency-view-a` — agency-facing view
- Plus larger blocks for system-insights (`system_insights_service.py`), client-decisions (`client_decisions_service.py`), client-report (`client_report_service.py`).

**Frontend dashboard surfaces** that consume these:
- `(app)/learning/_components/` — `why-library.tsx`, `horizons.tsx`, `decay-report.tsx`, `subject-inspection.tsx`, `mechanism-effectiveness.tsx`, `adjudicate-button.tsx`. Operators can inspect per-subject (per-buyer) learning state, see mechanism effectiveness across cohorts, view decay reports, look up explanations from the Why Library.
- `(app)/ledger/_components/` — `calibration-view.tsx`, `claims-table.tsx`, `sandbox.tsx`, `deviations-table.tsx`. The "ledger" is the audit-trail surface — every consequential claim the system made, calibration vs reality, deviations.
- `(app)/analytics/_components/` — system convergence + client decisions.
- `(app)/recommendations/[id]/` — per-recommendation drill-down with `decide` action.

**Decision trace observability paths** (per Phase 1 §15 grep):
- `adam/intelligence/decision_trace_emitter.py` — per-impression emit + drain
- `adam/intelligence/decision_trace_neo4j.py` — long-term storage + cypher analytics
- `adam/intelligence/outcome_trace_closure.py` — joining decision + outcome
- `adam/intelligence/daily/task_38_decision_trace_drain.py` — daily drain task
- `adam/intelligence/defensive_reasoning_renderer.py` — render defensive reasoning per decision

### §5.2 Why it's built this way

**Two-tier reporting (infrastructure + operator)** — Inference: the team distinguishes between *system health metrics* (Prometheus, alerts, latency p99 — for the SRE/devops perspective) and *decisioning metrics* (cohort effectiveness, predicate fire rates, calibration drift — for the campaign operator perspective). The two have different cadences (infra is real-time; operator is per-decision or per-day) and different consumers.

**"Ledger" framing for audit trail** — Inference: the choice of "ledger" over "audit log" or "event store" is deliberate. A ledger implies *consequential entries with provenance* — each row is something the system claimed or did, with calibration vs reality, deviations from expected, all queryable. This frame supports the operator-in-the-loop model: the operator reviews the ledger, sees what the system has been claiming, can sandbox proposed changes, can mark deviations as expected vs concerning.

**Why Library as a first-class surface** — every decision can be explained; explanations are stored and looked up. Inference: aligns with Chris's directive about causal understandings — the system isn't a black box; every recommendation has a "why" the operator can read.

**Decay report as a recurring endpoint** — Inference: the system tracks how its claims decay over time (do mechanism effectiveness estimates degrade as the mechanism is over-served? Do cohort definitions drift as user behavior shifts?). This is the precursor to drift detection (S5.6 ADWIN) and nightly retrain (S5.5).

**Calibration view in the ledger** — Inference: the system commits to calibration discipline (how often are its 70%-confidence predictions actually right ~70% of the time?). Calibration drift = the system's internal posteriors are no longer reflecting reality, and require either retrain or methodology change.

### §5.3 Patterns + anti-patterns

**Patterns:**
- *Service module per route concern* (`system_insights_service.py`, `client_decisions_service.py`, `client_report_service.py`): keeps router thin, business logic testable.
- *Pydantic response models* (`DashboardHealthResponse`, `CampaignListResponse`, `AnalyticsSummary`, `UserMembership`, `TenantHierarchyResponse`, `AutopilotSettings`, `DecayReport`, `WhyLibraryResponse`, `RecommendationListResponse`, `DeviationListResponse`, `CalibrationResponse`, `ClaimListResponse`): every endpoint declares a return type; OpenAPI generation works from these.
- *Decision-trace drain as scheduled task* (`daily/task_38_decision_trace_drain.py`): bounded latency in hot path; full archival happens offline.
- *Per-component health* (`/health/{component}`): operators can see which subsystem is degraded without parsing logs.

**Anti-patterns possibly present:**
- *Per-cell reporting absent* — Phase 1 §12 noted: per-cell impression count, per-predicate fire rate, per-archetype performance distribution, per-cohort outcome correlation, per-creative-variant performance per cell are NOT in the current dashboard route inventory. The substrate emits them (DecisionTrace has cell_id; predicate fire is logged); the UI doesn't yet expose them. This is the core gap that blocks the iteration loop closing.
- *Limited streaming/real-time exposure* — polling-based React Query pattern means "what's happening right now" has a polling-interval delay. For a system whose substrate runs at sub-100ms decisioning, the operator's window into the system is much coarser.

### §5.4 Constraints

- **Storage volume scaling** — per-impression DecisionTraces in Neo4j scale with traffic. At pilot (~10K-100K/day) this is fine; at production scale needs aggregation or expiration policy.
- **Aura connection** — when paused, dashboard surfaces empty states. Reporting that depends on long-term Neo4j queries (calibration over weeks, deviations over months) goes blind.
- **Operator cognitive load** — the dashboard could surface every metric the system computes; it doesn't, because operators can't act on too many signals. Reporting design is also UX design.
- **Latency-budget contention** — heavy dashboard queries (e.g., decision-trace exports across millions of rows) compete with bid-path latency in the same uvicorn worker.
- **Push-not-pull StackAdapt** — outcomes arrive at our webhook; we don't query StackAdapt for "what served?" beyond the postback information. Per the S0_HANDOFF URL-granularity blocker, even the postback doesn't include served-impression-URL granularity. This constrains what reporting can show about impression-URL performance.

### §5.5 Open architectural questions

1. **What's the minimum viable cell-conditional reporting for pilot?** Phase 1 §12 lists 9 reporting surfaces needed (per-cell impression count, per-predicate fire rate, per-archetype performance distribution, per-cohort outcome correlation, per-creative-variant performance per cell, aggregator latency distribution, predicate evaluator latency distribution, decision-trace observability, drift detection signals). Building all 9 is a substantial effort; building zero leaves pilot blind. Architectural question: which 3-5 are pilot-blocking?

2. **Reporting cadence — real-time, near-real-time, or batch?** Bid decisions are real-time (~50ms); current reporting appears polling-based (seconds to minutes lag). Should the operator see the firing of `high_fomo_promotion` predicate within seconds of it firing, or is daily aggregation enough? Tradeoff: real-time costs (WebSocket / SSE infrastructure; higher Neo4j read load) vs operator value (faster iteration vs information overload).

3. **Ledger vs analytics distinction** — currently `ledger/` shows deviations + calibration + claims; `analytics/` shows summary + system-convergence + client-decisions. Are these the right buckets? Or should there be a dedicated "iteration loop" surface that combines both with explicit "what did we just learn → what should we change → here's the proposed change → approve/reject" workflow?

4. **Causal-attribution view** — should there be a dedicated UI for "this conversion happened; here are the 3-5 active causal ingredients per `causal_decomposition.py`; here's the do-calculus chain per `decision_trace_neo4j.py:78`"? This is the operator-facing surface for the bilateral architecture's causal claim. Architectural question: build now or post-pilot?

5. **Reporting destination beyond dashboard** — should there be email digests, Slack notifications, BI tool exports (CSV / Snowflake / BigQuery)? The current operator model is "operator opens dashboard"; alternatives push notifications to operators. Tradeoff: more channels = more operator surface area to manage; fewer channels = operator must check.

### §5.6 Optionality vs lock-in

**Locked in:**
- Prometheus as metrics layer.
- Neo4j as long-term DecisionTrace store (cypher queries depend on this).
- React Query polling pattern in the dashboard.
- Specific Pydantic response models (changing them requires coordinated frontend updates).
- "Ledger" / "Why Library" / "Recommendations" route names (used in URLs, presumably bookmarked by operators).

**Pivot-able:**
- Specific metrics computed (adding new Prometheus counters is cheap).
- Specific dashboard routes / components (each is a single React file; refactoring is bounded).
- Reporting cadence per metric (config choice).
- BI tool integration (external systems can query Neo4j + Redis + the FastAPI APIs).
- Email/Slack notification layer (additive; doesn't break existing surfaces).

---

## §6 Cross-cutting synthesis

**The four areas compose into a single system commitment:** the platform is built as an **operator-in-the-loop intelligence engine that pushes pre-computed campaign intelligence into StackAdapt and learns from postback events.** Railway hosts the engine; the dashboard is the operator's window into it; the loop is the engine's cognitive core; reporting is what the loop exposes for the operator to act on.

**Where one area constrains another:**

- **Reporting gaps cap loop closure.** The substrate (cells, predicates, posteriors, causal discovery) decides cell-conditionally and learns from outcomes — but if the dashboard doesn't expose per-cell outcomes, the operator can't *interpret* what's happening, can't *test* whether predicate threshold changes help, can't *determine* what to change. The loop's interpret/test/determine phases are gated by reporting. **This is the highest-leverage architectural commitment for the next sprint.**

- **Frontend constraints constrain change-application surface.** Even if the loop computes "raise the FOMO predicate threshold from 0.7 to 0.65," if the campaigns route doesn't have a "predicate threshold tuning per campaign" UI (Phase 1 §13 missing piece), the change can't be applied through the dashboard — it requires a code change + deploy. This makes iteration slow.

- **Railway single-worker constraint constrains learning-loop scale.** All posterior updates and Thompson sampling state live in one process. At pilot volume this is fine; at scale, one missed conversion event (process restart) loses in-process learning state until Redis flush+reload. The shared-state backend is a Phase-2 commitment.

- **StackAdapt push-not-pull model constrains the loop's cadence.** The loop can compute changes in milliseconds; applying them to live serving is bounded by StackAdapt's GraphQL write rate limits + creative review queue (days for new creative). The loop is *closed but slow*; the architectural choice is whether to live with that latency for pilot or build a parallel pixel-impression layer to bypass StackAdapt's creative-review bottleneck (substantial out-of-pilot-chain engineering).

- **Aura connectivity constrains both reporting and learning.** When Aura is paused, the dashboard goes empty + the loop's per-conversion graph updates fail soft (logged, not retried). This is a single point of failure with operational consequences. Free-tier auto-pause was a cost choice that made sense pre-traffic; needs revisiting at pilot launch.

**Where investments would have leverage across multiple areas:**

1. **A unified per-cell observability layer** would simultaneously: (a) close the loop's interpret phase by surfacing per-cell outcomes; (b) fill the dashboard's missing cell-conditional reporting routes; (c) give the loop's test phase a measurement framework (A/B per cell becomes possible); (d) let the change-determination phase propose cell-specific changes with evidence. Phase 1 §21 named this as the #1 gap. Architecturally: this is a single backend slice (per-cell metric aggregation in Redis / Neo4j) + a dashboard slice (new `/analytics/cells` route + components).

2. **Pre-registered causal claim test scaffold** would simultaneously: (a) make the bilateral architecture's central thesis (multiplicative trait × state composition) testable at pilot; (b) give the loop's test phase a methodologically-rigorous comparison framework; (c) feed the ledger's calibration view with claim-vs-reality data; (d) inform whether to keep the multiplicative form or revise it post-pilot. Architecturally: leverages the existing M7 causal ensemble + blind-analysis box + validity layer; primarily new orchestration code that pre-registers test parameters and runs the comparison.

3. **A "what-just-happened" real-time decision-trace stream** to the operator would simultaneously: (a) collapse the polling-interval delay in reporting; (b) make the loop's interpret phase immediate; (c) give the operator confidence the loop is actually firing predicates on real bid data; (d) expose latency or correctness regressions immediately rather than per-day-batch. Architecturally: a WebSocket / SSE channel from the FastAPI webhook receiver / decision_trace emitter to the dashboard, with a small in-memory buffer.

4. **Autopilot policy per change-class** would simultaneously: (a) reduce operator cognitive load (high-volume low-risk changes don't need approval); (b) tighten the loop (autopilot-eligible changes apply faster); (c) preserve operator control over high-risk changes; (d) generate data for "which change classes are safe to autopilot" iteration. Architecturally: extension of the existing `/settings/autopilot` endpoint + per-change-class taxonomy.

---

## §7 Architectural questions Claude Proper should weigh in on

Direct list of decisions where your architectural advice has highest leverage. Each framed with the tradeoffs.

1. **Should creative-variant routing live in our infrastructure or stay in StackAdapt's review-gated cadence for pilot?**
   - In our infra: millisecond-fresh cell-conditional routing per impression; bypasses StackAdapt's review queue; requires standing up a parallel pixel-impression layer (substantial engineering).
   - StackAdapt-native: works within their model; constrained to variant-pool refresh cadence (days for new creative review); first month of pilot will see only StackAdapt's DCO doing variant selection inside the variant pool we push.

2. **Should causal-claim test scaffolding ship pre-pilot or rely on post-pilot iteration?**
   - Pre-pilot: methodological discipline; first pilot data validates/refutes the bilateral architecture's central claim with proper testing infrastructure; adds scope before launch.
   - Post-pilot: faster to launch; first month is "did anything happen" rather than "is the multiplicative composition right"; risk of post-hoc test design being motivated by the data we saw.

3. **Should the dashboard expose decision-trace at impression-grain or cell/cohort grain?**
   - Impression-grain: deepest introspection; operator can see "this specific bid fired predicate X with score Y"; high cardinality + high storage; UI needs filtering/search to be useful.
   - Cell/cohort grain: low cardinality; aggregated view; loses the "what just happened" specificity but easier to reason about; faster to build.
   - Both: best operator experience; doubles the work.

4. **Should the OutcomeHandler refactor (god-object → registry-of-handlers) ship pre-pilot, mid-pilot, or post-pilot?**
   - Pre-pilot: no production users yet; refactor risk is low; future learning sub-updates land cleaner.
   - Mid-pilot: operational pressure to add learning sub-updates as pilot data surfaces opportunities; refactor under pressure is risky.
   - Post-pilot: production-tested code refactored later; refactor risk distributed; classic technical-debt accrual.

5. **Should Aura tier upgrade happen before pilot or once pilot traffic justifies it?**
   - Before: avoids auto-pause learning-loop break risk; predictable cost.
   - After: cost-deferred; pilot may not need higher tier if traffic stays low; risk of pause during critical pilot moment.

6. **Should the Railway service split into multiple deployments (cascade-decisioner / dashboard-BFF / webhook-receiver / admin) or stay as one process?**
   - Split: isolates failure modes; each service can scale independently; loses singleton model (requires shared-state backend).
   - One process: matches singleton model; simpler ops; one slow request can starve others.

7. **What's the minimum viable cell-conditional reporting set for pilot?** Phase 1 §12 listed 9 surfaces; building all is substantial. Three plausible cuts:
   - Cut A (minimum): per-cell impression count + per-predicate fire rate + decision-trace observability. ~3 dashboard routes + 3 backend endpoints. Pilot launches with operator visibility into "is the substrate firing on real bids."
   - Cut B (medium): A + per-archetype performance distribution + per-cohort outcome correlation. ~5 routes + 5 endpoints. Pilot launches with attribution-class visibility.
   - Cut C (full): A + B + per-creative-variant per cell + aggregator latency + evaluator latency + drift detection. ~9 routes + 9 endpoints. Pilot launches with full iteration-loop instrumentation.

8. **What's the right autopilot default for pilot?**
   - All-manual: operator approves every change; safest; slowest iteration.
   - All-autopilot for pre-approved change classes (variant rotation in pool, predicate threshold tuning within bounds): faster iteration; trust required.
   - Per-change-class taxonomy: explicit per-change-class autopilot toggle; most configurable; needs taxonomy design upfront.

9. **Should the platform pre-deploy the W chain + M.1 wiring against the live LUXY campaign before pilot launch, or launch the campaign as-is and rely on substrate to activate when StackAdapt postback events flow?** The W chain + M.1 shipped during this session has not been deployed against the active campaign yet. Architecturally: the substrate would be inert against the campaign until we push code + redeploy Railway + restart the FastAPI service. The campaign's existing pixel + postback configuration would carry through automatically; the cascade would start consuming new substrate signals on the first conversion event after redeploy.

10. **Causal discovery: continuous online vs scheduled batch?** `causal_learning.py` treats every impression as a micro-experiment but the AMPLIFIES/SUPPRESSES/MODERATES edges presumably need statistical significance thresholds before becoming Neo4j edges. Architecturally: do we discover continuously (every N impressions, recompute) or batch-discover (nightly/weekly, run M7 ensemble + DoWhy refutation, write graph)? Tradeoff: continuous gives faster adaptation but risks false-positive edges; batch gives statistical rigor but slower adaptation.

---

## §8 Memo closure

This memo equips Claude Proper with the architectural reasoning above Phase 1's inventory. The four focus areas Chris named — Railway / frontend / loop / reporting — compose into a coherent system commitment: an operator-in-the-loop intelligence engine that pushes pre-computed psychological campaign intelligence into StackAdapt and learns from postback events. The substrate is unusually deep; the consumer-facing surface is comparatively thin; the iteration loop is closed end-to-end but cadence-bounded by StackAdapt's review-gated serving model and reporting-gated by dashboard surfaces that don't yet expose per-cell outcomes.

The highest-leverage architectural commitment for the next sprint is **a unified per-cell observability layer that simultaneously closes the loop's interpret phase, fills the dashboard's missing cell-conditional reporting, and gives the loop's test phase a measurement framework.** §7 lists 10 architectural questions where your input would have direct effect on next-sprint sequencing.

Phase 1 + this memo together should be sufficient context for you to recommend forward direction without re-discovering the system. If specific subsystems need deeper inspection, the audit-first discipline catalogued in Phase 1 §5 is the established pattern: scoped read-only audit memo → adjudication → implementation slice → EVE handoff → tests pinning invariants. New audit slices can be requested by name (e.g., "Q.0.bis frontend deep-dive" or "causal-attribution-infrastructure audit") and they'll follow the same shape.

End of memo.
