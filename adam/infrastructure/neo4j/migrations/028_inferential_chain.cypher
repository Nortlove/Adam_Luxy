// =============================================================================
// ADAM Migration 028: Inferential Chain Substrate (SCM-native)
// =============================================================================
// Materializes the inferential chain that makes ADAM an inferential system
// rather than a correlational one (ADAM_THEORETICAL_FOUNDATION.md §4.3):
//
//     "The graph must store the theoretical edges — (UncertaintyIntolerance)
//     -[:CAUSES_NEED_FOR]->(Closure), (Closure)-[:SATISFIED_BY]->(Authority),
//     (HighCognitiveEngagement)-[:REQUIRES]->(SubstantiveEvidence) — as
//     first-class entities, not just the effectiveness edges..."
//
// This migration adds:
//   - PsychologicalConstruct label for buyer-side psychological constructs
//     (uncertainty_intolerance, need_for_closure, cognitive_engagement, etc.)
//   - ACTIVATES relationship between constructs (construct → construct causal
//     link, with strength + citation + notes)
//   - CREATES_RECEPTIVITY_TO from PsychologicalConstruct to CognitiveMechanism
//     (which constructs make which mechanisms work, with effectiveness +
//     citation + context)
//   - REQUIRES from CognitiveMechanism to PsychologicalConstruct (prerequisite
//     constructs that must be co-active for the mechanism to work as claimed)
//
// These are THEORETICAL edges grounded in peer-reviewed literature, distinct
// from effectiveness edges learned from campaign outcomes. The distinction
// matters because an outcome either confirms or disconfirms a specific
// theoretical link, not just a cell-level score (Foundation §4.4).
//
// Each theoretical edge carries a `citation` property — the canonical
// reference anchoring the claim. Edges without citations are drift (A6:
// template-string pattern libraries).
//
// Scope of this migration: schema only. PsychologicalConstruct and edge
// type declarations. No seed data — constructs materialize on first upsert
// via the Python helper module. The pilot seeds a handful of canonical
// chain examples; the full 441-construct taxonomy is post-pilot work.
//
// This migration composes with existing CognitiveMechanism nodes from
// migration 004 (not replacing them).
// =============================================================================


// =============================================================================
// CONSTRAINTS — uniqueness keys
// =============================================================================

// PsychologicalConstruct — one node per canonical construct identifier.
// construct_id is slug-form (e.g., "uncertainty_intolerance", "need_for_closure")
// for readable graph browsing and stable downstream references.
CREATE CONSTRAINT inferential_construct_pk IF NOT EXISTS
FOR (c:PsychologicalConstruct) REQUIRE c.construct_id IS UNIQUE;


// =============================================================================
// INDEXES — access patterns
// =============================================================================

CREATE INDEX inferential_construct_name_idx IF NOT EXISTS
FOR (c:PsychologicalConstruct) ON (c.name);

CREATE INDEX inferential_construct_domain_idx IF NOT EXISTS
FOR (c:PsychologicalConstruct) ON (c.domain);


// =============================================================================
// NODE DEFINITIONS (documented shape)
// =============================================================================

// -------- PsychologicalConstruct --------
// construct_id: string              — slug form (e.g., "need_for_closure")
// name: string                      — display name (e.g., "Need for Closure")
// description: string               — plain-English statement of what the
//                                     construct is and when it is active
// domain: string                    — coarse taxonomy domain (e.g.,
//                                     "motivational", "cognitive_control",
//                                     "affect", "identity"); cross-referenced
//                                     with the 20+ domain taxonomy in
//                                     adam/intelligence/construct_taxonomy.py
// research_basis: string            — canonical citation grounding the
//                                     construct's existence as a named
//                                     psychological phenomenon
// first_seen: datetime              — when upserted
// last_updated: datetime            — last property write
// observation_count: int            — times seen in buyer profiles
//                                     (accrues across usage)


// =============================================================================
// RELATIONSHIP DEFINITIONS (documented shape; Cypher is schemaless)
// =============================================================================

// -------- (:PsychologicalConstruct)-[:ACTIVATES]->(:PsychologicalConstruct)
// strength: float [0, 1]            — how strongly the source activates the
//                                     target in the general population; 1.0
//                                     is "always co-activates", 0.0 is
//                                     "never activates" (edges with 0.0 are
//                                     absent rather than recorded)
// citation: string                  — canonical literature citation
// context: string                   — when the activation holds (e.g.,
//                                     "under time pressure", "general")
// notes: string                     — additional provenance
// evidence_count: int               — outcome-derived support accumulated
//                                     over time (0 at first upsert; updated
//                                     by the Inferential Learning Agent's
//                                     HYPOTHESIZE/VALIDATE cycle, post-pilot)
// first_seen: datetime
// last_updated: datetime

// -------- (:PsychologicalConstruct)-[:CREATES_RECEPTIVITY_TO]->(:CognitiveMechanism)
// effectiveness: float [0, 1]       — how strongly having the construct
//                                     active makes the mechanism work
// citation: string
// context: string                   — when receptivity applies (e.g.,
//                                     "high_cognitive_engagement required")
// notes: string
// evidence_count: int               — outcome-derived support
// first_seen: datetime
// last_updated: datetime

// -------- (:CognitiveMechanism)-[:REQUIRES]->(:PsychologicalConstruct)
// Expresses a prerequisite: the mechanism is only claimed to work as
// theorized when the named construct is co-active. Example: Authority
// requires HighCognitiveEngagement (otherwise peripheral-route processing
// bypasses the authority signal).
//
// citation: string
// notes: string
// first_seen: datetime


// =============================================================================
// NO SEED DATA
// =============================================================================
// PsychologicalConstruct nodes and theoretical edges materialize via the
// Python upsert path in adam/intelligence/recommendation_class/inferential_chain.py.
// Pilot-era seeding commits a handful of canonical chain examples as
// pre-registration-style code-committed claims; the full 441+ construct
// taxonomy is post-pilot work.
