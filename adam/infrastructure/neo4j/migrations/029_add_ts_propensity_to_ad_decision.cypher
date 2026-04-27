// Migration: add ts_propensity + pscore_known to :AdDecision nodes
// Date: 2026-04-27
// Component: M4 (Seven-Component Methodological Upgrade Handoff §4)
//
// Purpose:
//   Add the per-decision propensity (logged at decision time per M1) as a
//   first-class property on :AdDecision so the OPE estimator suite (DR,
//   SNIPS, SNDR, SwitchDR, DRos, MIPS) can consume logged propensities
//   directly from the graph.
//
// Per the handoff §4.4:
//   'Schema migration is part of the deliverable: add ts_propensity to
//    :DECISION edges going forward; backfill where reconstructable, mark
//    pscore_known=false otherwise.'
//
// ADAM's actual graph topology uses :AdDecision NODES (not the handoff's
// nominal :DECISION edges). The migration target adapts accordingly. The
// propensity lives as a property on the node; pscore_known marks whether
// WCLS / OPE should include the row.
//
// Discipline anchor — historical rows:
//   Pre-M1 :AdDecision rows have NO recoverable propensity. Boruvka 2018
//   §2 + Bibaut 2024 establish that p_t reconstruction is statistically
//   invalid; small recording errors dominate bias. So historical rows
//   must be marked pscore_known=false and their ts_propensity / epsilon_
//   floor must REMAIN NULL — never set to a sentinel like 0.0. A
//   0.0 sentinel would silently poison AVG(ts_propensity), corrupt
//   1/p_t weight calculations with zero-division, and generally invite
//   the analytical bug the discipline anchor exists to prevent.
//
//   Downstream consumers (OPE, WCLS) MUST filter on pscore_known=true
//   BEFORE looking at ts_propensity. This migration enforces that
//   contract by leaving the propensity null when pscore_known=false.
//
// Idempotency:
//   Each statement uses MATCH ... WHERE ... IS NULL ... SET ... so
//   re-running is safe. Existing nodes with the field already set are
//   skipped.
//
// Rollback:
//   REMOVE n.pscore_known on :AdDecision; DROP INDEX ad_decision_user_created;
//   DROP INDEX ad_decision_pscore_known. Reverse is straightforward.

// -----------------------------------------------------------------------
// 1. Mark every existing :AdDecision as having unreconstructable
//    propensity. Pre-M1 rows have no logged p_t; reconstructing it
//    post-hoc is statistically invalid (Boruvka 2018 §2). pscore_known
//    is the discipline anchor that drives OPE/WCLS row filtering.
//
//    ts_propensity and epsilon_floor are intentionally LEFT NULL on
//    pre-M1 rows. Sentinels like 0.0 would silently corrupt downstream
//    aggregates and weight calculations.
// -----------------------------------------------------------------------
MATCH (d:AdDecision)
WHERE d.pscore_known IS NULL
SET d.pscore_known = false
RETURN count(d) AS rows_marked_unreconstructable;

// -----------------------------------------------------------------------
// 2. Index on (user_id, created_at) for cluster-robust SE computation
//    in WCLS. Cluster id = user_id (Boruvka 2018 §2 — never impression
//    id). created_at orders within-user decision points for the
//    decision_point_t counter. CREATE INDEX IF NOT EXISTS is idempotent
//    in Neo4j 5.x.
// -----------------------------------------------------------------------
CREATE INDEX ad_decision_user_created IF NOT EXISTS
FOR (d:AdDecision) ON (d.user_id, d.created_at);

// -----------------------------------------------------------------------
// 3. Index on pscore_known for fast OPE/WCLS row filtering. Most queries
//    that consume propensity start with `WHERE d.pscore_known = true`.
// -----------------------------------------------------------------------
CREATE INDEX ad_decision_pscore_known IF NOT EXISTS
FOR (d:AdDecision) ON (d.pscore_known);

// -----------------------------------------------------------------------
// 4. Verification query — run after migration. Returns a single row
//    with counts so the runner can confirm the migration applied.
// -----------------------------------------------------------------------
MATCH (d:AdDecision)
RETURN
    count(d) AS total_decisions,
    count(d.pscore_known) AS with_pscore_known,
    sum(CASE WHEN d.pscore_known = true THEN 1 ELSE 0 END) AS pscore_known_true,
    sum(CASE WHEN d.pscore_known = false THEN 1 ELSE 0 END) AS pscore_known_false,
    count(d.ts_propensity) AS with_ts_propensity_logged;
