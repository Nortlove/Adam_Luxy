// Migration: :UserPosterior node — long-term storage for per-user
//            within-subject posterior profiles. Phase 1 deliverable
//            from CLAUDE_CODE_DIRECTIVE_FULL_BUILD.md.
// Date: 2026-04-30
// Component: Spine #1 — per-user N-of-1 hierarchical Bayesian engine
//
// Purpose:
//   The directive specifies "Storage schema in Neo4j (UserPosterior
//   node), Redis hot cache." UserPosteriorManager (retargeting/engines/
//   repeated_measures.py) already has L1 (memory) + L2 (Redis); this
//   migration adds the L3 (Neo4j) schema the manager's docstring
//   declares but never implemented.
//
// Why long-term Neo4j storage matters:
//   * HMC offline reconcile (Phase 1 deliverable) reads the long-term
//     posteriors and runs full HMC to refine them, writes back. Without
//     a queryable Neo4j tier, HMC reconcile has nowhere to read from
//     at scale.
//   * Variational batch reconcile (Phase 1 deliverable) needs the same
//     long-term tier.
//   * Recovery: Redis evictions don't lose history.
//   * Cross-user analyses (Phase 3 cohort discovery, Phase 5 hierarchical
//     prior pipeline) need a queryable per-user posterior store.
//
// Schema:
//   :UserPosterior { user_id, brand_id, archetype_id, posterior_json,
//                    total_touches, total_reward, last_updated_ts,
//                    schema_version }
//   Indexed on (user_id, brand_id) for fast point-lookup; the
//   posterior payload itself is stored as JSON to avoid schema drift
//   between the Pydantic model evolution and the Neo4j node schema.
//   Pydantic owns the shape; Neo4j is the durable store.
//
// Idempotency:
//   CREATE INDEX IF NOT EXISTS — safe to re-run.
//
// Rollback:
//   DROP INDEX user_posterior_user_brand;
//   DROP INDEX user_posterior_last_updated;
//   MATCH (up:UserPosterior) DETACH DELETE up;

// -----------------------------------------------------------------------
// 1. Index on (user_id, brand_id) — primary lookup key.
//    Composite index so the manager's get_user_profile call site can
//    resolve in a single query.
// -----------------------------------------------------------------------
CREATE INDEX user_posterior_user_brand IF NOT EXISTS
FOR (up:UserPosterior) ON (up.user_id, up.brand_id);

// -----------------------------------------------------------------------
// 2. Index on last_updated_ts — for HMC reconcile to find stale
//    posteriors that need refresh. The reconcile cadence (per Phase
//    Section 3.5) reads posteriors with last_updated < cutoff.
// -----------------------------------------------------------------------
CREATE INDEX user_posterior_last_updated IF NOT EXISTS
FOR (up:UserPosterior) ON (up.last_updated_ts);

// -----------------------------------------------------------------------
// 3. Verification query — counts existing :UserPosterior nodes (zero
//    on first apply; non-zero after the manager starts persisting).
// -----------------------------------------------------------------------
MATCH (up:UserPosterior)
RETURN count(up) AS total_user_posteriors;
