import Link from "next/link";
import { ArrowRight, Lightbulb } from "lucide-react";

import { ApiError, api } from "@/lib/api";
import type {
  RecommendationListResponse,
  RecommendationSummary,
} from "@/lib/types";
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
import { SourceBadge } from "@/components/source-badge";

export const metadata = {
  title: "Recommendations · INFORMATIV",
};

export const dynamic = "force-dynamic";

type FetchState =
  | { kind: "ok"; data: RecommendationListResponse }
  | { kind: "api-error"; status: number; message: string }
  | { kind: "unreachable"; message: string };

async function loadRecommendations(): Promise<FetchState> {
  try {
    const data = await api.get<RecommendationListResponse>(
      "/api/dashboard/recommendations",
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

export default async function RecommendationsPage() {
  const state = await loadRecommendations();

  return (
    <div className="flex flex-col gap-6 p-6">
      <PageHeader
        title="Recommendations"
        description="Plan-before-patch. Every proposal is rendered with its Confident / Uncertain / Possibly-Wrong decomposition so you can reason alongside the system, not against it."
      />
      {state.kind === "ok" ? (
        <ListView data={state.data} />
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

function ListView({ data }: { data: RecommendationListResponse }) {
  return (
    <>
      {data.source === "unavailable" ? (
        <Alert>
          <AlertTitle>No live source</AlertTitle>
          <AlertDescription>
            {data.source_note ??
              "StackAdapt must be reachable to generate live recommendations."}
          </AlertDescription>
        </Alert>
      ) : data.source_note ? (
        <p className="text-sm text-muted-foreground">{data.source_note}</p>
      ) : null}

      {data.recommendations.length === 0 ? (
        <Card className="border-dashed">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Lightbulb className="size-5 text-amber-500" />
              Nothing to review right now
            </CardTitle>
            <CardDescription>
              Either your campaigns are running within expected ranges, or
              the generator thresholds need tuning. This list refreshes as
              performance drifts and new conditions trigger proposals.
            </CardDescription>
          </CardHeader>
        </Card>
      ) : (
        <div className="grid gap-4 lg:grid-cols-2">
          {data.recommendations.map((r) => (
            <RecommendationCard key={r.id} r={r} />
          ))}
        </div>
      )}
    </>
  );
}

function RecommendationCard({ r }: { r: RecommendationSummary }) {
  // Threshold-source recommendations are A14 fallback — visually muted
  // so DCIL directives in the same queue read as the priority items.
  // The visual difference is intentional, not decorative: it implements
  // the Pinker override surface (memory wins where memory has fired).
  const isFallback = r.source === "threshold";
  return (
    <Link href={`/recommendations/${encodeURIComponent(r.id)}`}>
      <Card
        className={`h-full transition-colors hover:bg-muted/40 ${
          isFallback ? "border-dashed bg-muted/20" : ""
        }`}
      >
        <CardHeader>
          <div className="mb-2 flex items-center gap-2">
            <SourceBadge source={r.source} />
            <Badge variant="outline">{r.type.replace(/_/g, " ")}</Badge>
          </div>
          <CardTitle className="flex items-center justify-between gap-3 text-base">
            <span className="flex-1 leading-snug">{r.title}</span>
          </CardTitle>
          <CardDescription>{r.summary}</CardDescription>
        </CardHeader>
        <CardContent className="flex items-center justify-between pt-0 text-xs text-muted-foreground">
          <div className="flex gap-3">
            {r.campaign_name && <span>campaign: {r.campaign_name}</span>}
            <span>horizon: {r.expected_horizon_class}</span>
          </div>
          <ArrowRight className="size-4" />
        </CardContent>
      </Card>
    </Link>
  );
}
