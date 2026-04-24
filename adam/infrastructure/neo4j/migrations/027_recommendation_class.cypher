// =============================================================================
// ADAM Migration 027: RecommendationClass + ProjectedImpactClaim
// =============================================================================
// Promotes the RecommendationClass primitive from Python-only data model to
// durable Neo4j entity with an accumulating track record across firings.
//
// Per ADAM_THEORETICAL_FOUNDATION.md §2.5 and
// project_weakness_4_recommendation_class_primitive.md: a RecommendationClass
// is a structured causal hypothesis identified by the tuple
//   (advertiser_id, archetype_id, mechanism, context_posture_band, horizon_band)
// Every recommendation ADAM emits is an instance of a class. The class
// accumulates ProjectedImpactClaim receipts (pre-registered predicates
// committed before observation) + realized-distribution records (recorded
// at horizon completion) + residual-divergence posterior updates that feed
// back into the Inferential Learning Agent.
//
// Scope of this migration: schema-only. RecommendationClass and
// ProjectedImpactClaim node shapes; the MAKES_CLAIM relationship. No seed
// data — classes materialize on first observation via the upsert path in
// adam/intelligence/recommendation_class/graph.py.
//
// This migration respects the frame-correction discipline (2026-04-24):
// field names are ADAM-native, informed by but not named after ICH E9(R1)
// regulatory vocabulary. See project_pilot_execution_plan.md for the
// native → E9 mapping.
// =============================================================================


// =============================================================================
// CONSTRAINTS — uniqueness keys
// =============================================================================

// RecommendationClass — one node per (advertiser, archetype, mechanism,
// context_posture_band, horizon_band) tuple. The id is deterministic —
// SHA-256 prefix of the canonical tuple slug (see graph.py:recommendation_class_id).
CREATE CONSTRAINT rec_class_pk IF NOT EXISTS
FOR (rc:RecommendationClass) REQUIRE rc.id IS UNIQUE;

// ProjectedImpactClaim — one node per pre-registered claim. The
// content_hash is the deterministic SHA-256 over canonical JSON of the
// substantive claim content; uniqueness prevents double-recording the
// same pre-registration.
CREATE CONSTRAINT rec_class_claim_pk IF NOT EXISTS
FOR (pc:ProjectedImpactClaim) REQUIRE pc.id IS UNIQUE;

CREATE CONSTRAINT rec_class_claim_content_hash_unique IF NOT EXISTS
FOR (pc:ProjectedImpactClaim) REQUIRE pc.content_hash IS UNIQUE;


// =============================================================================
// INDEXES — access patterns
// =============================================================================

CREATE INDEX rec_class_advertiser_idx IF NOT EXISTS
FOR (rc:RecommendationClass) ON (rc.advertiser_id);

CREATE INDEX rec_class_archetype_idx IF NOT EXISTS
FOR (rc:RecommendationClass) ON (rc.archetype_id);

CREATE INDEX rec_class_mechanism_idx IF NOT EXISTS
FOR (rc:RecommendationClass) ON (rc.mechanism);

CREATE INDEX rec_class_posture_band_idx IF NOT EXISTS
FOR (rc:RecommendationClass) ON (rc.context_posture_band);

CREATE INDEX rec_class_horizon_band_idx IF NOT EXISTS
FOR (rc:RecommendationClass) ON (rc.horizon_band);

CREATE INDEX rec_class_observation_count_idx IF NOT EXISTS
FOR (rc:RecommendationClass) ON (rc.observation_count);

// ProjectedImpactClaim access patterns: by the class it belongs to and by time.
CREATE INDEX rec_class_claim_class_idx IF NOT EXISTS
FOR (pc:ProjectedImpactClaim) ON (pc.recommendation_class_id);

CREATE INDEX rec_class_claim_created_at_idx IF NOT EXISTS
FOR (pc:ProjectedImpactClaim) ON (pc.created_at);

CREATE INDEX rec_class_claim_horizon_idx IF NOT EXISTS
FOR (pc:ProjectedImpactClaim) ON (pc.horizon_days);


// =============================================================================
// NODE DEFINITIONS (documented shape; Cypher is schemaless)
// =============================================================================

// -------- RecommendationClass --------
// id: string                            — format "rec_class:{16-hex of SHA-256
//                                         over canonical identity slug}".
//                                         Deterministic from the 5-tuple.
// advertiser_id: string                 — FK to advertiser / tenant identity
// archetype_id: string                  — HB latent-class id (k-means label in
//                                         slice 4 pre-commit transition)
// mechanism: string                     — one of ADAM's mechanism identifiers
// context_posture_band: string          — discretized attentional posture
//                                         bucket (e.g., "autopilot_high",
//                                         "neutral", "vigilance_low")
// horizon_band: string                  — discretized time-to-outcome bucket
//                                         (e.g., "immediate", "short",
//                                         "medium", "long")
// observation_count: int                — total firings observed
// first_seen: datetime                  — first upsert
// last_seen: datetime                   — most recent upsert
// last_updated: datetime                — last property write
//
// Additional posterior properties accrue over later slices (plant-model
// predictive posterior, realized-distribution summaries, residual-
// divergence decomposition, parameterization-sensitivity record). Slice 2
// establishes the identity and counter; the track record math lands in
// the plant-model slice (weeks 5-7).


// -------- ProjectedImpactClaim --------
// id: string                            — format "claim:{claim_id}:{content_hash-prefix}"
// claim_id: string                      — human-readable identifier from
//                                         ProjectedImpact.claim_id
// recommendation_class_id: string       — FK RecommendationClass.id
// content_hash: string                  — SHA-256 hex over canonical JSON
//                                         of the substantive ProjectedImpact
//                                         content (pre-registration receipt)
// substantive_content_json: string      — canonical JSON serialization of
//                                         the claim's substantive content
//                                         (priming_condition, audience_scope,
//                                         goal_fulfillment_outcome,
//                                         competing_activations,
//                                         audience_summary, horizon_days).
//                                         Stored as string to preserve exact
//                                         content addressing; queries against
//                                         specific fields happen via the
//                                         recommendation_class_id FK path
//                                         rather than JSON-path queries.
// horizon_days: int                     — horizon for adjudication schedule
// created_at: datetime                  — when the claim was registered
//                                         (should equal or precede commit
//                                         time of the git hash that
//                                         introduced the claim file)
// adjudicated: bool                     — default false; set true when the
//                                         plant model's adjudicator has
//                                         produced a verdict at horizon
//                                         completion. Slice in weeks 8-9.


// =============================================================================
// RELATIONSHIPS (documented shape)
// =============================================================================

// (:RecommendationClass)-[:MAKES_CLAIM {recorded_at: datetime}]->(:ProjectedImpactClaim)
//   Every claim belongs to exactly one RecommendationClass.
//   recorded_at captures when the relationship was written (may differ
//   slightly from ProjectedImpactClaim.created_at due to write latency).


// =============================================================================
// NO SEED DATA
// =============================================================================
// Classes and claims materialize lazily via the upsert / record path in
// adam/intelligence/recommendation_class/graph.py. No seeding.
