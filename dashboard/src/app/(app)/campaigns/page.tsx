import { ApiError, api } from "@/lib/api";
import type { CampaignListResponse } from "@/lib/types";
import { formatInt, formatPercent, formatStatus, formatUsd } from "@/lib/format";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { PageHeader } from "@/components/page-header";

export const metadata = {
  title: "Campaigns · INFORMATIV",
};

// Ensure this page always runs dynamically — it reflects live StackAdapt data.
export const dynamic = "force-dynamic";

type FetchState =
  | { kind: "ok"; data: CampaignListResponse }
  | { kind: "api-error"; status: number; message: string }
  | { kind: "unreachable"; message: string };

async function loadCampaigns(): Promise<FetchState> {
  try {
    const data = await api.get<CampaignListResponse>("/api/dashboard/campaigns");
    return { kind: "ok", data };
  } catch (err) {
    if (err instanceof ApiError) {
      return { kind: "api-error", status: err.status, message: err.message };
    }
    return {
      kind: "unreachable",
      message: err instanceof Error ? err.message : "Unknown error",
    };
  }
}

export default async function CampaignsPage() {
  const state = await loadCampaigns();

  return (
    <div className="flex flex-col gap-6 p-6">
      <PageHeader
        title="Campaigns"
        description="Live StackAdapt campaigns with impressions, spend, and conversion performance."
      />
      {state.kind === "ok" ? (
        <CampaignsView data={state.data} />
      ) : state.kind === "api-error" ? (
        <Alert variant="destructive">
          <AlertTitle>API error</AlertTitle>
          <AlertDescription>
            {state.message} (HTTP {state.status})
          </AlertDescription>
        </Alert>
      ) : (
        <Alert variant="destructive">
          <AlertTitle>Backend unreachable</AlertTitle>
          <AlertDescription>{state.message}</AlertDescription>
        </Alert>
      )}
    </div>
  );
}

function CampaignsView({ data }: { data: CampaignListResponse }) {
  const stackadapt = data.stackadapt;

  return (
    <>
      {stackadapt.source === "unavailable" ? (
        <Alert>
          <AlertTitle>StackAdapt unreachable</AlertTitle>
          <AlertDescription>
            {stackadapt.reason ??
              "StackAdapt GraphQL is not configured. Set STACKADAPT_GRAPHQL_KEY on the backend to see live campaigns."}
          </AlertDescription>
        </Alert>
      ) : stackadapt.advertiser_name ? (
        <p className="text-sm text-muted-foreground">
          Advertiser: <strong>{stackadapt.advertiser_name}</strong> ·{" "}
          {data.total} campaign{data.total === 1 ? "" : "s"}
        </p>
      ) : null}

      {data.campaigns.length === 0 ? (
        <Card className="border-dashed">
          <CardHeader>
            <CardTitle>No campaigns</CardTitle>
            <CardDescription>
              {stackadapt.source === "live"
                ? "StackAdapt is connected but returned no campaigns for this advertiser."
                : "Configure StackAdapt to see live campaign data here."}
            </CardDescription>
          </CardHeader>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {data.campaigns.map((c) => (
            <Card key={c.id}>
              <CardHeader>
                <CardTitle className="flex items-center justify-between gap-2 text-base">
                  <span className="truncate">{c.name}</span>
                  <Badge variant={isLive(c.status) ? "default" : "secondary"}>
                    {formatStatus(c.status)}
                  </Badge>
                </CardTitle>
                <CardDescription>
                  {[c.channel_type, c.group_name].filter(Boolean).join(" · ") ||
                    "—"}
                </CardDescription>
              </CardHeader>
              <CardContent>
                <dl className="grid grid-cols-3 gap-3 text-sm">
                  <Stat label="Spend" value={formatUsd(c.spend_usd)} />
                  <Stat
                    label="Impressions"
                    value={formatInt(c.impressions)}
                  />
                  <Stat label="Clicks" value={formatInt(c.clicks)} />
                  <Stat label="CTR" value={formatPercent(c.ctr)} />
                  <Stat
                    label="Conversions"
                    value={formatInt(c.conversions)}
                  />
                  <Stat label="CPA" value={formatUsd(c.cpa_usd)} />
                </dl>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs uppercase text-muted-foreground">{label}</dt>
      <dd className="text-sm font-semibold">{value}</dd>
    </div>
  );
}

function isLive(status: string | null): boolean {
  if (!status) return false;
  const u = status.toUpperCase();
  return u === "ACTIVE" || u === "LIVE" || u === "RUNNING";
}
