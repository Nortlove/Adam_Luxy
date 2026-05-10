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

/**
 * RecommendationSource — the discriminator that identifies where a
 * recommendation originated. The list view uses this to render priority
 * order and the decide action routes by source:
 *   - "dcil": DCIL directive from inferential / theory-grounded path.
 *     Authoritative. Carries i², expected_lift_pct, rollback_conditions.
 *     Decide routes to /api/v2/admin/.../directives/{id}/approve|block.
 *   - "horizon_adjudication": Loop B horizon expired — an operator-
 *     deviated recommendation has reached its horizon window and is
 *     ready to adjudicate (system_right / user_right / indeterminate).
 *     Decide routes to the causal adjudicator.
 *   - "chain_attribution": Loop A FAILING cell with negative
 *     `unexplained` residual. Reserved for when the Loop A horizon
 *     adjudicator pipeline lights up post-pilot; not produced today.
 *   - "threshold": Correlational A1 fallback (CPA / CTR / zero-conv
 *     generators). Tracked under THRESHOLD_GENERATORS_AS_FALLBACK in the
 *     A14 registry. Retired when DCIL achieves ≥1 directive per active
 *     campaign per week sustained.
 */
export type RecommendationSource =
  | "dcil"
  | "horizon_adjudication"
  | "chain_attribution"
  | "threshold";

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
  // Defaults to "threshold" on the wire for backward compat with the
  // existing rule-based generators; "dcil" is the inferential path.
  source: RecommendationSource;
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

/**
 * DeviationContext — structural state of the deviation underlying a
 * horizon adjudication. Surfaced first-class on RecommendationDetail
 * (not derived from claim strings) so the UI can render the operator's
 * judgment task as the structural state it actually is.
 */
export type DeviationContext = {
  deviation_id: string;
  system_choice: string;
  user_choice: string | null;
  days_elapsed: number;
  horizon_window_days: number;
  horizon_class: string;
  stated_rationale: string | null;
  rationale_class: string | null;
};

export type RecommendationDetail = RecommendationSummary & {
  alternatives: RecommendationAlternative[];
  evidence: UncertaintyBreakdown;
  decisions: UserDecisionResponse[];

  // Structural fields populated for source="dcil". Carried first-class so
  // the UI can render them as derived views without parsing claim strings.
  directive_id: string | null;
  parameter: string | null;
  current_value: unknown;
  proposed_value: unknown;
  i_squared: number | null;
  expected_lift_pct: number | null;
  generator_confidence: number | null;
  rollback_conditions: string[];

  // Upstream-authored narrative — surfaced with explicit attribution
  // ("directive narrative — generator-authored") so it is not mistaken
  // for a derived view of atom state. The directive generator's
  // string-flattening of structured evidence is upstream A4 drift to
  // retire post-pilot at the source.
  directive_rationale: string | null;
  directive_bilateral_evidence: string | null;

  // Populated for source="horizon_adjudication". UI renders a
  // DeviationContext panel from this field, parallel to how DCIL recs
  // render DirectiveSubstance from their structural fields.
  deviation_context: DeviationContext | null;
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

// =============================================================================
// Mechanism Effectiveness (Front-end A — Learning surface)
// =============================================================================

/**
 * Beta posterior on a (therapeutic mechanism | archetype, barrier) cell.
 * Produced by Enhancement #33's 5-level hierarchical retargeting learning.
 *
 *   mean = alpha / (alpha + beta) is the current best-estimate of barrier-
 *   resolution probability. Render with confidence: at low sample_count the
 *   posterior is wide and the point-estimate is unreliable. confidence
 *   grows with sample_count per the platform's confidence model.
 */
export type MechanismPosterior = {
  mean: number;
  alpha: number;
  beta: number;
  sample_count: number;
  confidence: number;
};

export type MechanismEffectivenessResponse = {
  global_stats: Record<string, unknown>;
  posteriors: Record<string, MechanismPosterior> | null;
  barrier_prevalence: Record<string, number> | null;
  archetype_id: string | null;
  barrier: string | null;
};

// Canonical LUXY archetype slugs (mirrors ALL_ARCHETYPES in adam/constants.py).
// Single-tenant pilot surface; Front-end B will query the live archetype list
// when multi-tenant lands.
export const LUXY_ARCHETYPES: readonly string[] = [
  "careful_truster",
  "status_seeker",
  "easy_decider",
  "explorer",
  "prevention_planner",
  "reliable_cooperator",
  "trusting_loyalist",
  "dependable_loyalist",
  "consensus_seeker",
] as const;

// Canonical barrier categories (mirrors BARRIER_CATEGORIES in constants.py).
export const BARRIER_CATEGORIES: readonly string[] = [
  "trust_deficit",
  "regulatory_mismatch",
  "processing_overload",
  "emotional_disconnect",
  "price_friction",
  "relevance_gap",
  "attention_shortage",
  "autonomy_threat",
  "negativity_block",
  "ambiguity_intolerance",
] as const;

// =============================================================================
// Subject Inspection (Front-end A — cascade-state renderer per person)
//
// Mirrors adam/retargeting/engines/unified_puzzle.py PersonState.to_dict().
// Each field is a named output of the unified-puzzle inference —
// joint, not marginal — consumed directly by the render. No composed
// English; the narrative originates from the backend.
// =============================================================================

export type SubjectTrajectory =
  | "approaching"
  | "stalled"
  | "retreating"
  | "converting"
  | "converted"
  | "dormant"
  | "unknown"
  | string; // tolerant to future additions

export type SubjectResponseType =
  | "engager"
  | "builder"
  | "ad_averse"
  | "rejector"
  | "unknown"
  | string;

export type SubjectCommunicationStyle =
  | "reassuring"
  | "aspirational"
  | "efficient"
  | "peer"
  | string;

export type PersonState = {
  // Identity
  user_id: string;
  archetype: string;

  // Narrative (backend-composed, NOT hand-composed in the client)
  narrative: string;

  // Psychological state
  dominant_barrier: string;
  barrier_confidence: number;
  barrier_is_somatic: boolean;
  barrier_is_cognitive: boolean;
  barrier_is_contextual: boolean;

  // Engagement trajectory
  trajectory: SubjectTrajectory;
  trajectory_velocity: number;

  // Readiness
  conversion_probability: number;
  touches_remaining: number;
  receptive_now: boolean;

  // Response pattern
  response_type: SubjectResponseType;
  clicks_ads: boolean;
  responds_to_organic: boolean;

  // Interaction-effect archetype (population-scale)
  interaction_archetype: string;
  interaction_archetype_confidence: number;
  suppress: boolean;
  suppress_reason: string;

  // Optimal action (seller-side response to buyer-side barrier)
  recommended_mechanism: string;
  mechanism_rationale: string;
  prediction_error_level: number;
  communication_style: SubjectCommunicationStyle;
  should_continue: boolean;
  continue_reason: string;

  // Meta
  evidence_quality: number;
  sessions_observed: number;
  last_updated: number;
};

// =============================================================================
// System Convergence (Front-end B — internal superadmin surface)
//
// Cross-archetype roll-up of retargeting learning state. Internal only
// — references raw taxonomy (archetype / barrier / mechanism slugs,
// posterior numerics) deliberately. Never consumed on client surfaces.
// =============================================================================

export type ConvergedCell = {
  archetype: string;
  barrier: string;
  mechanism: string;
  mean: number;
  sample_count: number;
  confidence: number;
  alpha: number;
  beta: number;
  rank_score: number;
};

export type CrossArchetypePattern = {
  mechanism: string;
  archetypes: string[];
  barrier: string | null;
  mean_across_archetypes: number;
  total_sample_count: number;
};

export type NovelFinding = {
  archetype: string;
  barrier: string;
  mechanism: string;
  mean: number;
  sample_count: number;
  confidence: number;
  note: string;
};

export type AdvertiserSummary = {
  advertiser_id: string;
  advertiser_name: string | null;
  total_cells_with_evidence: number;
  top_converged_cell_count: number;
  total_observations: number;
};

export type SystemConvergenceResponse = {
  top_converged: ConvergedCell[];
  novel_findings: NovelFinding[];
  cross_archetype_patterns: CrossArchetypePattern[];
  advertisers: AdvertiserSummary[];
  cells_examined: number;
  generated_at: string;
};

// =============================================================================
// Client Decisions Audit (Front-end B — internal audit of client acknowledge
// / decline events + their adjudication state). Internal only.
// =============================================================================

export type ClientDecisionAuditEntry = {
  decision_id: string;
  decision_kind: "acknowledge" | "decline";
  decided_at: string;
  latency_ms: number | null;
  feedback_text: string | null;
  rec_id: string;
  rec_headline: string;
  advertiser_id: string | null;
  deviation_id: string | null;
  adjudication_status: string | null;
  adjudication_outcome: string | null;
  outcome_observation: string | null;
};

export type ClientDecisionAuditSummary = {
  total_decisions: number;
  acknowledge_count: number;
  decline_count: number;
  declines_with_feedback: number;
  pending_adjudication: number;
  adjudicated_system_right: number;
  adjudicated_user_right: number;
  adjudicated_indeterminate: number;
  acceptance_rate: number;
};

export type ClientDecisionAuditResponse = {
  summary: ClientDecisionAuditSummary;
  entries: ClientDecisionAuditEntry[];
  generated_at: string;
};

// =============================================================================
// Client Report (Front-end A — advertiser-facing surface)
//
// Mirrors adam/api/dashboard/models.py ClientReportResponse. Every
// string reaching the client comes from our PublicLabelService or from
// safe performance metrics. Internal taxonomy (archetype / mechanism /
// barrier slugs, posteriors, construct dimensions, trajectory labels)
// never appears here.
// =============================================================================

export type ClientSegmentHighlight = {
  segment_label: string;
  observation: string;
};

export type ClientMessageObservation = {
  observation: string;
};

export type ClientRecommendationStatus =
  | "pending"
  | "acknowledged"
  | "declined";

export type ClientRecommendation = {
  id: string;
  headline: string;
  rationale: string;
  projected_impact: string | null;
  confirm_label: string;
  requires_acknowledgment: boolean;
  status: ClientRecommendationStatus;
};

export type ClientRecommendationDecisionRequest = {
  kind: "acknowledge" | "decline";
  advertiser_id: string;
  headline: string;
  rationale: string;
  confirm_label: string;
  projected_impact?: string | null;
  feedback_text?: string | null;
  latency_ms?: number | null;
};

export type ClientRecommendationDecisionResponse = {
  id: string;
  recommendation_id: string;
  kind: "acknowledge" | "decline";
  created_at: string;
  claim_id: string | null;
  deviation_id: string | null;
};

export type ClientReport = {
  advertiser_id: string;
  advertiser_name: string | null;
  period_start: string | null;
  period_end: string;
  generated_at: string;

  impressions: number;
  clicks: number;
  conversions: number;
  spend_usd: number;
  ctr: number;
  cpa_usd: number | null;
  roas: number | null;
  campaigns_live: number;
  campaigns_total: number;

  segment_highlights: ClientSegmentHighlight[];
  message_observations: ClientMessageObservation[];
  recommendations: ClientRecommendation[];

  data_source_notes: string[];

  // Internal-only diagnostic — do NOT render on client-facing surfaces.
  // Populated when a PublicLabel is missing for a referenced entity.
  missing_labels: string[];
};

// =============================================================================
// Multi-tenant shell
// =============================================================================

export type TenantStatus = "active" | "paused" | "suspended" | "archived";

export type PartnerKind =
  | "superadmin"
  | "agency"
  | "independent"
  | "direct_brand";

export type TenantWorkspace = {
  id: string;
  advertiser_id: string;
  name: string;
  purpose: string | null;
  status: TenantStatus;
  created_at: string;
};

export type TenantAdvertiser = {
  id: string;
  partner_id: string;
  name: string;
  category: string | null;
  stackadapt_advertiser_id: string | null;
  status: TenantStatus;
  created_at: string;
  workspaces: TenantWorkspace[];
};

export type TenantPartner = {
  id: string;
  name: string;
  kind: PartnerKind;
  white_label_name: string | null;
  billing_email: string | null;
  status: TenantStatus;
  created_at: string;
  advertisers: TenantAdvertiser[];
};

export type TenantHierarchyResponse = {
  partners: TenantPartner[];
  total_partners: number;
  total_advertisers: number;
  total_workspaces: number;
};

export type UserMembership = {
  user_id: string;
  role: "superadmin" | "partner_admin" | "advertiser_admin" | "viewer";
  partner: TenantPartner | null;
  advertiser: TenantAdvertiser | null;
};

// =============================================================================
// Q.2.A — Cut B reporting response types
// Mirrors adam/api/dashboard/models.py Q.2.A section.
// =============================================================================

export type DataSourceState = "populated" | "empty" | "partial";
export type TraceLookupState = "found" | "not_found" | "partial";

export type ClusterMetrics = {
  cluster_id: string;
  impression_count: number;
  share_of_total: number;
};

export type PredicateMetrics = {
  predicate_name: string;
  fire_count: number;
  fire_rate: number;
  dormant: boolean;
};

export type PerClusterFireRateResponse = {
  clusters: ClusterMetrics[];
  predicates: PredicateMetrics[];
  total_impressions: number;
  window_start: string;
  window_end: string;
  data_source_state: DataSourceState;
};

export type ArchetypeMetrics = {
  archetype_id: string;
  impression_count: number;
  conversion_count: number;
  conversion_rate: number;
  cold_start_share: number;
};

export type PerArchetypePerformanceResponse = {
  archetypes: ArchetypeMetrics[];
  total_impressions: number;
  window_start: string;
  window_end: string;
  data_source_state: DataSourceState;
};

export type MechanismOrientation = "affiliative" | "transactional" | "mixed";
export type CohortConfidence =
  | "high_confidence"
  | "partial_evidence"
  | "uninformative";

export type CohortMetrics = {
  cohort_id: string;
  dominant_mechanism: string;
  mechanism_orientation: MechanismOrientation;
  compensatory_flag: boolean;
  sample_size: number;
  conversion_rate: number;
  confidence_label: CohortConfidence;
};

export type PerCohortOutcomeCorrelationResponse = {
  cohorts: CohortMetrics[];
  window_start: string;
  window_end: string;
  data_source_state: DataSourceState;
};

export type DispatchMethodMetrics = {
  method_name: string;
  dispatch_count: number;
  last_dispatch_at: string | null;
  dormant: boolean;
};

export type LoopDispatchRatesResponse = {
  dispatch_methods: DispatchMethodMetrics[];
  total_outcomes_processed: number;
  data_source_state: DataSourceState;
};

export type PredicateFiring = {
  predicate_name: string;
  fired: boolean;
  score: number | null;
  threshold: number | null;
};

export type ModulationDetail = {
  mechanism: string;
  score_before: number;
  score_after: number;
  source: string;
};

export type DecisionTraceDetailResponse = {
  impression_id: string;
  timestamp: string;
  buyer_id_anonymized: string;
  cell_id: string | null;
  cluster_id: string | null;
  archetype: string | null;
  cohort_id: string | null;
  posture_class: string | null;
  journey_stage: string | null;
  regulatory_focus: string | null;
  predicates_fired: PredicateFiring[];
  modulations_applied: ModulationDetail[];
  chosen_creative_id: string | null;
  chosen_creative_cluster: string | null;
  why_explanation: string | null;
  data_source_state: TraceLookupState;
};
