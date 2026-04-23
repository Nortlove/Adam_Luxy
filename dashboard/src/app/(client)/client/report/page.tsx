import { ApiError, api } from "@/lib/api";
import type { ClientReport } from "@/lib/types";
import {
  formatInt,
  formatPercent,
  formatUsd,
} from "@/lib/format";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { PageHeader } from "@/components/page-header";
import { ClientReportView } from "./_components/client-report-view";

export const metadata = {
  title: "Report · INFORMATIV",
};

export const dynamic = "force-dynamic";

type FetchState =
  | { kind: "ok"; data: ClientReport }
  | { kind: "api-error"; status: number; message: string }
  | { kind: "unreachable"; message: string };

async function loadReport(): Promise<FetchState> {
  try {
    const data = await api.get<ClientReport>(
      "/api/dashboard/client/report?advertiser_id=luxy_ride",
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

export default async function ClientReportPage() {
  const state = await loadReport();

  return (
    <div className="mx-auto flex w-full max-w-5xl flex-col gap-6 p-6">
      <PageHeader
        title="Report"
        description="Performance and audience intelligence summary. Updated from live learning."
      />

      {state.kind === "ok" ? (
        <ClientReportView report={state.data} />
      ) : state.kind === "api-error" ? (
        <Alert variant="destructive">
          <AlertTitle>Report unavailable</AlertTitle>
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
