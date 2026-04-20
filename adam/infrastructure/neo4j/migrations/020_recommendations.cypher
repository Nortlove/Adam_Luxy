// =============================================================================
// ADAM Migration 020: Recommendations + Deviation shape
//
// Schema for AI recommendations rendered to the human partner in the
// dashboard, along with the concrete Deviation events that record when
// the user picks something other than ADAM's preferred choice.
//
// Follows ADAM_HUMAN_MACHINE_TEAMING_FOUNDATION.md §7.1 (self-uncertainty
// decomposition) and §11.5 (deviation-hypothesis lifecycle). Deviations
// are stored as HYPOTHESES about causation — their stated_rationale is
// a user claim, not a learning, until the horizon passes and the
// Inferential Learning Agent adjudicates the outcome.
// =============================================================================


// =============================================================================
// CONSTRAINTS
// =============================================================================

// Recommendation — a structured AI-generated proposal for an action
// on a campaign (creative rotation, mechanism shift, budget move, pause,
// etc.), carrying full uncertainty decomposition + alternatives +
// counterfactuals.
CREATE CONSTRAINT recommendation_pk IF NOT EXISTS
FOR (r:Recommendation) REQUIRE r.id IS UNIQUE;

// UserDecision — the record of how the user responded to a
// Recommendation. Stored separately from Recommendation itself so
// multiple decisions over time (accept, then later modify) produce
// distinct nodes.
CREATE CONSTRAINT user_decision_pk IF NOT EXISTS
FOR (d:UserDecision) REQUIRE d.id IS UNIQUE;


// =============================================================================
// INDEXES
// =============================================================================

// Recommendations by user (list view for the dashboard)
CREATE INDEX recommendation_user_idx IF NOT EXISTS
FOR (r:Recommendation) ON (r.user_id);

// Recommendations by status (pending-only filter on the dashboard)
CREATE INDEX recommendation_status_idx IF NOT EXISTS
FOR (r:Recommendation) ON (r.status);

// Recommendations by target campaign
CREATE INDEX recommendation_campaign_idx IF NOT EXISTS
FOR (r:Recommendation) ON (r.campaign_id);

// Recommendations by created_at (time-ordered listing)
CREATE INDEX recommendation_created_idx IF NOT EXISTS
FOR (r:Recommendation) ON (r.created_at);

// UserDecisions by user
CREATE INDEX user_decision_user_idx IF NOT EXISTS
FOR (d:UserDecision) ON (d.user_id);

// UserDecisions by recommendation (for fast join on recommendation detail)
CREATE INDEX user_decision_rec_idx IF NOT EXISTS
FOR (d:UserDecision) ON (d.recommendation_id);

// UserDecisions by kind (accept / modify / reject)
CREATE INDEX user_decision_kind_idx IF NOT EXISTS
FOR (d:UserDecision) ON (d.kind);


// =============================================================================
// NODE DEFINITIONS (documented shape)
// =============================================================================

// Recommendation node shape:
//   id: string
//   user_id: string (the user who should review this recommendation)
//   campaign_id: string | null (StackAdapt id when campaign-scoped)
//   campaign_name: string | null
//   type: "creative_rotate" | "mechanism_shift" | "budget_shift" |
//         "pause_campaign" | "resume_campaign" | "archetype_reweight" |
//         "audience_expand" | "other"
//   title: string (short human-readable summary)
//   summary: string (one-paragraph description of the proposal)
//   preferred_choice: string (id of the recommended alternative)
//   alternatives: JSON array of { id, label, description, predicted_outcome }
//   evidence: JSON with keys:
//     confident:      [ { claim, sources: [string], strength: float } ]
//     uncertain:      [ { claim, missing: string, would_reduce: string } ]
//     possibly_wrong: [ { claim, conflicting_signal: string, alternative: string } ]
//   expected_horizon_class: "hours" | "days" | "weeks" | "months"
//   status: "pending" | "accepted" | "modified" | "rejected" | "expired"
//   created_at: datetime
//   resolved_at: datetime | null

// UserDecision node shape:
//   id: string
//   user_id: string
//   recommendation_id: string
//   kind: "accept" | "modify" | "reject"
//   chosen_alternative: string | null (preferred_choice for accept, custom for modify)
//   modified_fields: JSON | null (only for kind=modify)
//   rationale_class: "idiosyncratic" | "missing_context" | "model_wrong" | null
//     — set by the user when rejecting/modifying; stored as a HYPOTHESIS
//       per HMT Rule 12 until causally adjudicated at horizon expiry
//   rationale_text: string | null (user's freeform "why")
//   claim_id: string | null (link to a Claim node with the rationale content)
//   created_at: datetime


// =============================================================================
// SEED — no reference data needed; recommendations are generated dynamically
// from live campaign state by the dashboard service.
// =============================================================================
