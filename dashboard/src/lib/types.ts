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
