// =============================================================================
// ADAM Migration 021: Autopilot settings + Decay-adjudicator output
//
// Adds the autopilot-mode configuration per DialogueUser (five-mode
// trust curve with per-decision-class overrides, HMT Foundation
// §10.4) plus the DecayCohort nodes that Task 33 writes when it
// classifies ad-recipient users into CONTINUE / RESTART / ABANDON
// buckets.
// =============================================================================


// =============================================================================
// CONSTRAINTS
// =============================================================================

// One autopilot setting per DialogueUser (singleton per user).
CREATE CONSTRAINT autopilot_setting_pk IF NOT EXISTS
FOR (a:AutopilotSetting) REQUIRE a.user_id IS UNIQUE;

// DecayCohort — the result of one run of Task 33 for a given
// campaign at a given date. Stored for audit trail; the dashboard
// reads the most recent cohort per campaign.
CREATE CONSTRAINT decay_cohort_pk IF NOT EXISTS
FOR (dc:DecayCohort) REQUIRE dc.id IS UNIQUE;


// =============================================================================
// INDEXES
// =============================================================================

// DecayCohorts by campaign (most recent first)
CREATE INDEX decay_cohort_campaign_idx IF NOT EXISTS
FOR (dc:DecayCohort) ON (dc.campaign_id);

// DecayCohorts by run date
CREATE INDEX decay_cohort_created_idx IF NOT EXISTS
FOR (dc:DecayCohort) ON (dc.created_at);


// =============================================================================
// NODE DEFINITIONS (documented shape)
// =============================================================================

// AutopilotSetting node shape:
//   user_id: string (FK DialogueUser.id, unique)
//   mode: "observer" | "explain" | "notify" | "delegate" | "autopilot"
//   creative_gate: "approve" | "notify" | "auto"
//   bid_gate: "approve" | "notify" | "auto"
//   audience_gate: "approve" | "notify" | "auto"
//   budget_gate: "approve" | "notify" | "auto"
//   kill_gate: "approve" | "notify" | "auto"
//   campaigns_at_current_mode: int (count since last mode change)
//   successful_at_current_mode: int (count of recommendations accepted
//     without subsequent override-reversal — graduation signal)
//   last_graduated_at: datetime | null
//   updated_at: datetime

// DecayCohort node shape:
//   id: string (UUID)
//   campaign_id: string
//   created_at: datetime
//   run_date: date
//   total_users: int
//   continue_count: int
//   restart_count: int
//   abandon_count: int
//   zero_data_count: int (users with too few impressions to classify)
//   advertiser_avg_cpa: float | null
//   cohort_summary_json: string (detailed breakdown for the dashboard)
//   task_version: string (e.g. "task_33.v1")


// =============================================================================
// SEED — default autopilot setting for Chris (user:chris) as user-zero
// =============================================================================

MERGE (u:DialogueUser {id: "user:chris"})
MERGE (a:AutopilotSetting {user_id: "user:chris"})
  ON CREATE SET a.mode = "explain",
                a.creative_gate = "approve",
                a.bid_gate = "approve",
                a.audience_gate = "notify",
                a.budget_gate = "approve",
                a.kill_gate = "approve",
                a.campaigns_at_current_mode = 0,
                a.successful_at_current_mode = 0,
                a.last_graduated_at = null,
                a.updated_at = datetime()
MERGE (u)-[:HAS_AUTOPILOT_SETTING]->(a);
