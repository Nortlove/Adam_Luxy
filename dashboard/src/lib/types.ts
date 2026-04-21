/**
 * API response types — mirrors adam/api/dashboard/models.py.
 *
 * When the shape lands on more surfaces we'll generate this from the
 * FastAPI OpenAPI schema. For v1 keeping types inline is lighter.
 */

export type CampaignSummary = {
  id: string;
  name: string;
  channel_type: string | null;
  group_name: string | null;
  status: string | null;
  impressions: number;
  clicks: number;
  conversions: number;
  spend_usd: number;
  ctr: number;
  cpa_usd: number | null;
  roas: number | null;
};

export type StackAdaptSource = {
  source: "live" | "unavailable";
  reason: string | null;
  advertiser_name: string | null;
};

export type CampaignListResponse = {
  campaigns: CampaignSummary[];
  total: number;
  stackadapt: StackAdaptSource;
};

export type AnalyticsSummary = {
  campaigns_total: number;
  campaigns_live: number;
  total_impressions: number;
  total_clicks: number;
  total_conversions: number;
  total_spend_usd: number;
  overall_ctr: number;
  overall_cpa_usd: number | null;
  overall_roas: number | null;
  active_archetypes: number;
  edges_in_graph: number;
  advertiser_name: string | null;
  stackadapt_source: "live" | "unavailable";
  stackadapt_reason: string | null;
  graph_source: "live" | "unavailable";
  last_updated: string;
};

export type CurrentUser = {
  id: string;
  email: string;
  display_name: string;
  role: string;
};

// =============================================================================
// Recommendations — Uncertainty Panel + plan-before-patch
// =============================================================================

export type RecommendationType =
  | "creative_rotate"
  | "mechanism_shift"
  | "budget_shift"
  | "pause_campaign"
  | "resume_campaign"
  | "archetype_reweight"
  | "audience_expand"
  | "other";

export type RecommendationStatus =
  | "pending"
  | "accepted"
  | "modified"
  | "rejected"
  | "expired";

export type HorizonClass = "hours" | "days" | "weeks" | "months";

export type DecisionKind = "accept" | "modify" | "reject";

export type RationaleClass =
  | "idiosyncratic"
  | "missing_context"
  | "model_wrong";

export type RecommendationAlternative = {
  id: string;
  label: string;
  description: string;
  predicted_outcome: string | null;
};

export type ConfidentClaim = {
  claim: string;
  sources: string[];
  strength: number;
};

export type UncertainClaim = {
  claim: string;
  missing: string;
  would_reduce: string | null;
};

export type PossiblyWrongClaim = {
  claim: string;
  conflicting_signal: string;
  alternative: string | null;
};

export type UncertaintyBreakdown = {
  confident: ConfidentClaim[];
  uncertain: UncertainClaim[];
  possibly_wrong: PossiblyWrongClaim[];
};

export type RecommendationSummary = {
  id: string;
  type: RecommendationType;
  title: string;
  summary: string;
  campaign_id: string | null;
  campaign_name: string | null;
  preferred_choice: string;
  expected_horizon_class: HorizonClass;
  status: RecommendationStatus;
  created_at: string;
};

export type UserDecisionResponse = {
  id: string;
  user_id: string;
  recommendation_id: string;
  kind: DecisionKind;
  chosen_alternative: string | null;
  rationale_class: RationaleClass | null;
  rationale_text: string | null;
  claim_id: string | null;
  created_at: string;
};

export type RecommendationDetail = RecommendationSummary & {
  alternatives: RecommendationAlternative[];
  evidence: UncertaintyBreakdown;
  decisions: UserDecisionResponse[];
};

export type RecommendationListResponse = {
  recommendations: RecommendationSummary[];
  total: number;
  source: "live" | "synthetic" | "unavailable";
  source_note: string | null;
};

export type UserDecisionRequest = {
  kind: DecisionKind;
  chosen_alternative?: string | null;
  rationale_class?: RationaleClass | null;
  rationale_text?: string | null;
};

// =============================================================================
// Dialogue Ledger — Claims / Deviations / Calibration
// =============================================================================

export type ElicitationMode =
  | "forced_pair"
  | "timed_pair"
  | "k_afc"
  | "rank_order"
  | "story"
  | "counter_example"
  | "recallability"
  | "scenario"
  | "spies"
  | "four_point"
  | "freeform";

export type ClaimStatus =
  | "hypothesis"
  | "captured"
  | "instrumented"
  | "testing"
  | "validated_user_right"
  | "validated_system_right"
  | "indeterminate"
  | "retired";

export type Frame = "gain" | "loss" | "neutral";

export type Recallability = "fluent" | "hesitant" | "absent";

export type ClaimCreateRequest = {
  text: string;
  elicitation_mode: ElicitationMode;
  domain: string;
  stated_confidence?: number | null;
  latency_ms?: number | null;
  frame?: Frame;
  session_id?: string | null;
  mood_index?: number | null;
  recallability?: Recallability | null;
};

export type ClaimResponse = {
  id: string;
  user_id: string;
  text: string;
  elicitation_mode: ElicitationMode;
  domain: string;
  stated_confidence: number | null;
  latency_ms: number | null;
  frame: Frame;
  status: ClaimStatus;
  recallability: Recallability | null;
  created_at: string;
};

export type ClaimListResponse = {
  claims: ClaimResponse[];
  total: number;
};

export type DeviationSummary = {
  id: string;
  user_id: string;
  recommendation_id: string;
  system_choice: string;
  user_choice: string | null;
  stated_rationale: string | null;
  rationale_class: RationaleClass | null;
  adjudication_status: "pending" | "testing" | "adjudicated";
  adjudication_outcome:
    | "user_right"
    | "system_right"
    | "indeterminate"
    | null;
  horizon_class: HorizonClass;
  created_at: string;
};

export type DeviationListResponse = {
  deviations: DeviationSummary[];
  total: number;
};

export type DomainCalibration = {
  domain: string;
  total_claims: number;
  fluent_recall_count: number;
  hesitant_recall_count: number;
  absent_recall_count: number;
  avg_latency_ms: number | null;
  validated_count: number;
  brier_score: number | null;
};

export type CalibrationResponse = {
  domains: DomainCalibration[];
  source: "live" | "unavailable";
  source_note: string | null;
};

// =============================================================================
// Autopilot settings + Decay report + Horizons
// =============================================================================

export type AutopilotMode =
  | "observer"
  | "explain"
  | "notify"
  | "delegate"
  | "autopilot";

export type GateKind = "approve" | "notify" | "auto";

export type AutopilotSettings = {
  user_id: string;
  mode: AutopilotMode;
  creative_gate: GateKind;
  bid_gate: GateKind;
  audience_gate: GateKind;
  budget_gate: GateKind;
  kill_gate: GateKind;
  campaigns_at_current_mode: number;
  successful_at_current_mode: number;
  last_graduated_at: string | null;
  updated_at: string;
};

export type AutopilotUpdateRequest = {
  mode: AutopilotMode;
  creative_gate?: GateKind;
  bid_gate?: GateKind;
  audience_gate?: GateKind;
  budget_gate?: GateKind;
  kill_gate?: GateKind;
};

export type DecayAction = "continue" | "restart" | "abandon" | "monitor";

export type CampaignDecayClassification = {
  campaign_id: string;
  campaign_name: string;
  total_users: number;
  continue_count: number;
  restart_count: number;
  abandon_count: number;
  zero_data_count: number;
  advertiser_avg_cpa: number | null;
  campaign_cpa: number | null;
  flags: string[];
  recommended_action: DecayAction;
  rationale: string;
};

export type DecayReport = {
  run_id: string;
  run_date: string;
  task_version: string;
  campaigns: CampaignDecayClassification[];
  total_users_classified: number;
  overall_abandon_rate: number;
  source: "live" | "unavailable";
  source_note: string | null;
};

export type HorizonStatus =
  | "too_early"
  | "in_progress"
  | "ready"
  | "adjudicated";

export type DeviationHorizon = {
  deviation_id: string;
  recommendation_id: string;
  horizon_class: HorizonClass;
  created_at: string;
  horizon_ends_at: string;
  days_elapsed: number;
  days_remaining: number;
  status: HorizonStatus;
  adjudication_outcome:
    | "user_right"
    | "system_right"
    | "indeterminate"
    | null;
};

export type DeviationHorizonResponse = {
  horizons: DeviationHorizon[];
  total: number;
  ready_count: number;
};

// =============================================================================
// Causal Adjudicator + Why Library
// =============================================================================

export type AdjudicationResult = {
  deviation_id: string;
  recommendation_id: string;
  outcome: "user_right" | "system_right" | "indeterminate";
  rationale: string;
  why_library_entry_id: string | null;
  metric_observed: string | null;
  metric_value_before: number | null;
  metric_value_after: number | null;
};

export type AdjudicationBatchResponse = {
  adjudicated: AdjudicationResult[];
  skipped_too_early: number;
  skipped_no_data: number;
  skipped_already_done: number;
};

export type WhyLibraryEntry = {
  id: string;
  trigger_pattern: string;
  bias_class: string;
  evidence_strength: number;
  scope: "user" | "brand" | "category" | "platform";
  scope_id: string | null;
  countermeasure: string;
  supporting_deviation_ids: string[];
  warning_posterior_mean: number;
  warning_posterior_observations: number;
  created_at: string;
  last_validated_at: string | null;
  retired_at: string | null;
};

export type WhyLibraryResponse = {
  entries: WhyLibraryEntry[];
  total: number;
};
