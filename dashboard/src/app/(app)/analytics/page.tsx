import { ApiError, api } from "@/lib/api";
import type { AnalyticsSummary } from "@/lib/types";
import { formatInt, formatPercent, formatUsd } from "@/lib/format";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { PageHeader } from "@/components/page-header";

export const metadata = {
  title: "Analytics · INFORMATIV",
};

export const dynamic = "force-dynamic";

type FetchState =
  | { kind: "ok"; data: AnalyticsSummary }
  | { kind: "api-error"; status: number; message: string }
  | { kind: "unreachable"; message: string };

async function loadSummary(): Promise<FetchState> {
  try {
    const data = await api.get<AnalyticsSummary>(
      "/api/dashboard/analytics/summary",
    );
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

export default async function AnalyticsPage() {
  const state = await loadSummary();

  return (
    <div className="flex flex-col gap-6 p-6">
      <PageHeader
        title="Daily Analytics"
        description="Live StackAdapt totals joined with bilateral-cascade intelligence from Neo4j."
      />
      {state.kind === "ok" ? (
        <SummaryView data={state.data} />
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

function SummaryView({ data }: { data: AnalyticsSummary }) {
  const lastUpdated = new Date(data.last_updated);

  return (
    <>
      {data.stackadapt_source === "unavailable" ? (
        <Alert>
          <AlertTitle>StackAdapt unreachable</AlertTitle>
          <AlertDescription>
            {data.stackadapt_reason ??
              "Set STACKADAPT_GRAPHQL_KEY on the backend to see live totals."}
          </AlertDescription>
        </Alert>
      ) : null}

      {data.graph_source === "unavailable" ? (
        <Alert>
          <AlertTitle>Neo4j unreachable</AlertTitle>
          <AlertDescription>
            Bilateral-cascade intelligence unavailable. Check NEO4J_* env on the
            backend.
          </AlertDescription>
        </Alert>
      ) : null}

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <StatCard
          title="Campaigns"
          value={`${data.campaigns_live} live`}
          caption={`${data.campaigns_total} total`}
        />
        <StatCard
          title="Spend"
          value={formatUsd(data.total_spend_usd)}
          caption={
            data.advertiser_name
              ? `advertiser: ${data.advertiser_name}`
              : undefined
          }
        />
        <StatCard
          title="Impressions"
          value={formatInt(data.total_impressions)}
          caption={`${formatInt(data.total_clicks)} clicks · CTR ${formatPercent(data.overall_ctr)}`}
        />
        <StatCard
          title="Conversions"
          value={formatInt(data.total_conversions)}
          caption={
            data.overall_cpa_usd
              ? `CPA ${formatUsd(data.overall_cpa_usd)}`
              : undefined
          }
        />
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Bilateral cascade intelligence</CardTitle>
          <CardDescription>
            Live from Neo4j. The edge evidence is the platform&rsquo;s
            operative prior.
          </CardDescription>
        </CardHeader>
        <CardContent className="grid grid-cols-2 gap-4 text-sm md:grid-cols-4">
          <Stat
            label="BRAND_CONVERTED edges"
            value={formatInt(data.edges_in_graph)}
          />
          <Stat
            label="Archetypes"
            value={formatInt(data.active_archetypes)}
          />
          <Stat
            label="CTR (all campaigns)"
            value={formatPercent(data.overall_ctr)}
          />
          <Stat
            label="ROAS"
            value={data.overall_roas ? data.overall_roas.toFixed(2) : "—"}
          />
        </CardContent>
      </Card>

      <p className="text-xs text-muted-foreground">
        Last updated {lastUpdated.toLocaleString()}
      </p>
    </>
  );
}

function StatCard({
  title,
  value,
  caption,
}: {
  title: string;
  value: string;
  caption?: string;
}) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardDescription>{title}</CardDescription>
        <CardTitle className="text-2xl font-semibold">{value}</CardTitle>
      </CardHeader>
      {caption ? (
        <CardContent className="pt-0 text-xs text-muted-foreground">
          {caption}
        </CardContent>
      ) : null}
    </Card>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-xs uppercase text-muted-foreground">{label}</div>
      <div className="text-base font-semibold">{value}</div>
    </div>
  );
}
