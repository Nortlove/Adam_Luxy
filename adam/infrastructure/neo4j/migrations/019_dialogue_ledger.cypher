// =============================================================================
// ADAM Migration 019: Dialogue Ledger (Human-Machine Teaming / Loop B)
//
// Schema for the Dialogue Ledger described in
// ADAM_HUMAN_MACHINE_TEAMING_FOUNDATION.md §9.2. This captures every
// human-system exchange (claims, deviations, outcomes, calibration)
// as typed nodes/relationships in Neo4j so Loop B (teaming) can feed
// the same Inferential Learning Agent that Loop A (analytics) uses.
//
// Core principle (HMT Rule 12): user self-reports are HYPOTHESES, not
// learnings. Every Claim enters with status=hypothesis. Promotion to
// a validated learning requires instrumentation + horizon completion +
// causal adjudication — the LearningStatus transitions below encode
// exactly that lifecycle.
// =============================================================================


// =============================================================================
// CONSTRAINTS — uniqueness keys
// =============================================================================

// DialogueUser — the partner driving the platform (Chris during pilot,
// agency planner / brand operator later). Single-tenant pilot uses the
// well-known id "user:chris" stamped by the dashboard auth stub.
CREATE CONSTRAINT dialogue_user_pk IF NOT EXISTS
FOR (u:DialogueUser) REQUIRE u.id IS UNIQUE;

// Claim — any assertion the user makes (preference, forecast, override
// rationale, confident statement). Enters with status=hypothesis.
CREATE CONSTRAINT claim_pk IF NOT EXISTS
FOR (c:Claim) REQUIRE c.id IS UNIQUE;

// Deviation — a specific override event: the user chose something
// other than the system's recommendation.
CREATE CONSTRAINT deviation_pk IF NOT EXISTS
FOR (d:Deviation) REQUIRE d.id IS UNIQUE;

// Outcome — the observed downstream result attached to a Claim or
// Deviation for causal adjudication once the horizon passes.
CREATE CONSTRAINT outcome_pk IF NOT EXISTS
FOR (o:Outcome) REQUIRE o.id IS UNIQUE;

// CalibrationEntry — per-event calibration data point (stated
// confidence, machine prior, outcome-once-observed) used to build a
// per-user-per-domain Brier curve.
CREATE CONSTRAINT calibration_entry_pk IF NOT EXISTS
FOR (ce:CalibrationEntry) REQUIRE ce.id IS UNIQUE;

// DialogueDomain — a bounded knowledge domain within which calibration
// is tracked separately. Examples: "audience_sizing", "creative_voice",
// "mechanism_selection", "budget_pacing".
CREATE CONSTRAINT dialogue_domain_pk IF NOT EXISTS
FOR (dd:DialogueDomain) REQUIRE dd.name IS UNIQUE;

// WhyLibraryEntry — validated bias pattern with trigger, bias class,
// and countermeasure. Queried at decision time for pre-emptive
// defensive reasoning.
CREATE CONSTRAINT why_library_entry_pk IF NOT EXISTS
FOR (wl:WhyLibraryEntry) REQUIRE wl.id IS UNIQUE;


// =============================================================================
// INDEXES — access patterns
// =============================================================================

// Claims by user (history view)
CREATE INDEX claim_user_idx IF NOT EXISTS
FOR (c:Claim) ON (c.user_id);

// Claims by status (learning-lifecycle filter)
CREATE INDEX claim_status_idx IF NOT EXISTS
FOR (c:Claim) ON (c.status);

// Claims by domain (per-domain calibration)
CREATE INDEX claim_domain_idx IF NOT EXISTS
FOR (c:Claim) ON (c.domain);

// Claims by timestamp (time-series queries)
CREATE INDEX claim_timestamp_idx IF NOT EXISTS
FOR (c:Claim) ON (c.created_at);

// Claims by elicitation mode (analyze which modes produced useful data)
CREATE INDEX claim_mode_idx IF NOT EXISTS
FOR (c:Claim) ON (c.elicitation_mode);

// Deviations by user
CREATE INDEX deviation_user_idx IF NOT EXISTS
FOR (d:Deviation) ON (d.user_id);

// Deviations pending adjudication (horizon-expiry scan)
CREATE INDEX deviation_adjudication_idx IF NOT EXISTS
FOR (d:Deviation) ON (d.adjudication_status);

// Outcomes by horizon for the adjudication sweep
CREATE INDEX outcome_horizon_idx IF NOT EXISTS
FOR (o:Outcome) ON (o.horizon_ends_at);

// Calibration entries by user and domain
CREATE INDEX calibration_user_domain_idx IF NOT EXISTS
FOR (ce:CalibrationEntry) ON (ce.user_id, ce.domain);

// WhyLibrary by trigger pattern (fast retrieval at recommendation time)
CREATE INDEX why_library_trigger_idx IF NOT EXISTS
FOR (wl:WhyLibraryEntry) ON (wl.trigger_pattern);

// WhyLibrary by scope (user / brand / category / platform)
CREATE INDEX why_library_scope_idx IF NOT EXISTS
FOR (wl:WhyLibraryEntry) ON (wl.scope);


// =============================================================================
// NODE DEFINITIONS (documented via example inserts — MERGE-safe)
// =============================================================================

// DialogueUser node shape:
//   id: string (unique, e.g. "user:chris")
//   email: string
//   display_name: string
//   role: "superadmin" | "admin" | "planner" | "viewer" | ...
//   created_at: datetime
//   rational_experiential_preference: float (REI proxy, 0..1, optional)
//   trust_mode_default: "observer" | "explain" | "notify" | "delegate" | "autopilot"

// Claim node shape:
//   id: string
//   user_id: string
//   text: string (raw assertion)
//   elicitation_mode: "forced_pair" | "timed_pair" | "story" | "recallability" |
//                     "k_afc" | "rank_order" | "counter_example" | "scenario" |
//                     "spies" | "four_point"
//   stated_confidence: float (0..1, optional — user's self-reported confidence)
//   latency_ms: int (response latency — signal for Type 1 vs Type 2)
//   frame: "gain" | "loss" | "neutral"
//   domain: string (e.g. "audience_sizing")
//   status: "hypothesis"  ← always starts here (HMT Rule 12)
//   created_at: datetime
//   session_id: string (for cross-session consistency analysis)
//   mood_index: float (from session-start mood probe, for covariate adjustment)
//   recallability: "fluent" | "hesitant" | "absent" | null
//     ← populated when a RecallabilityProbe follows the claim

// LearningStatus node shape (linked 1:1 from Claim via :HAS_STATUS):
//   claim_id: string
//   current: "captured" | "instrumented" | "testing" |
//            "validated_user_right" | "validated_system_right" |
//            "indeterminate" | "retired"
//   transitioned_at: datetime
//   reason: string (human-readable transition reason)
//   horizon_ends_at: datetime (when causal adjudication becomes eligible)
//   evidence_strength: float (posterior / Brier-weighted)

// Deviation node shape:
//   id: string
//   user_id: string
//   recommendation_id: string (the AI recommendation that was overridden)
//   system_choice: string (what ADAM recommended)
//   user_choice: string (what the human picked instead)
//   system_counterfactual: map (stored predicted outcomes under ADAM's choice)
//   stated_rationale: string (user's "why" — also a HYPOTHESIS, not truth)
//   rationale_class: "idiosyncratic" | "missing_context" | "model_wrong" | null
//     ← populated post-adjudication, not at capture time
//   adjudication_status: "pending" | "testing" | "adjudicated"
//   adjudication_outcome: "user_right" | "system_right" | "indeterminate" | null
//   created_at: datetime
//   adjudicated_at: datetime | null
//   horizon_class: "hours" | "days" | "weeks" | "months"
//     ← expected time-to-causal-signal; no adjudication before horizon_ends_at

// Outcome node shape:
//   id: string
//   observation: map (raw downstream metrics at the horizon)
//   horizon_ends_at: datetime
//   observed_at: datetime
//   attributed_to: "user_choice" | "system_choice" | "shared" | "confounded"
//   confidence: float (0..1, causal-test confidence)

// CalibrationEntry node shape:
//   id: string
//   user_id: string
//   domain: string
//   stated_confidence: float (user's self-reported confidence at claim time)
//   machine_prior: float (ADAM's prior at the same time)
//   outcome: 0 | 1 | null (until observed)
//   brier_contribution: float | null (squared error once outcome is in)
//   created_at: datetime
//   resolved_at: datetime | null

// WhyLibraryEntry node shape:
//   id: string
//   trigger_pattern: string (the situation that evokes the bias)
//   bias_class: "anchoring" | "availability" | "recency" | "familiarity" |
//               "anecdotal_weighting" | "status_quo" | "confirmation" |
//               "hindsight" | "framing" | "other"
//   evidence_strength: float (how well-supported this entry is)
//   scope: "user" | "brand" | "category" | "platform"
//   scope_id: string (user-id / brand-id / category-id / null for platform)
//   countermeasure: string (canonical defensive reasoning shown to the user)
//   supporting_deviation_ids: list<string> (which Deviations produced this)
//   warning_posterior_mean: float (track whether the warning itself is
//     well-calibrated — sometimes users would have been fine to deviate)
//   warning_posterior_observations: int
//   created_at: datetime
//   last_validated_at: datetime
//   retired_at: datetime | null


// =============================================================================
// SEED REFERENCE DATA — core dialogue domains
// =============================================================================

MERGE (dd:DialogueDomain {name: "audience_sizing"})
  SET dd.description = "Estimates of how large a target audience is, how fast it depletes, reach forecasts",
      dd.typical_horizon_class = "weeks";

MERGE (dd:DialogueDomain {name: "mechanism_selection"})
  SET dd.description = "Which mechanism (archetype × persuasion technique) to deploy for a given context",
      dd.typical_horizon_class = "weeks";

MERGE (dd:DialogueDomain {name: "creative_voice"})
  SET dd.description = "Tone, register, claim phrasing, primary metaphor selection for a creative",
      dd.typical_horizon_class = "days";

MERGE (dd:DialogueDomain {name: "budget_pacing"})
  SET dd.description = "Daily budget allocation, channel split, flight shaping",
      dd.typical_horizon_class = "hours";

MERGE (dd:DialogueDomain {name: "archetype_hypothesis"})
  SET dd.description = "Hypotheses about which archetypes a brand serves and which to suppress",
      dd.typical_horizon_class = "months";

MERGE (dd:DialogueDomain {name: "barrier_interpretation"})
  SET dd.description = "Interpretation of what specific user barriers (price, trust, relevance) mean for retargeting",
      dd.typical_horizon_class = "weeks";


// =============================================================================
// SEED DIALOGUE USER — Chris as user zero
// =============================================================================

MERGE (u:DialogueUser {id: "user:chris"})
  SET u.email = coalesce(u.email, "chris@informativgroup.com"),
      u.display_name = coalesce(u.display_name, "Chris Nocera"),
      u.role = "superadmin",
      u.trust_mode_default = "explain",
      u.created_at = coalesce(u.created_at, datetime());
