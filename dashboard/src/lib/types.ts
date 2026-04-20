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
