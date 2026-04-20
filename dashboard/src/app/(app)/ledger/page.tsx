import { ApiError, api } from "@/lib/api";
import type {
  CalibrationResponse,
  ClaimListResponse,
  DeviationListResponse,
} from "@/lib/types";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { PageHeader } from "@/components/page-header";
import { ClaimsTable } from "./_components/claims-table";
import { DeviationsTable } from "./_components/deviations-table";
import { CalibrationView } from "./_components/calibration-view";
import { Sandbox } from "./_components/sandbox";

export const metadata = {
  title: "Dialogue Ledger · INFORMATIV",
};

export const dynamic = "force-dynamic";

async function fetchOrNull<T>(path: string): Promise<T | { error: string; status: number } | null> {
  try {
    return await api.get<T>(path);
  } catch (err) {
    if (err instanceof ApiError) {
      return { error: err.message, status: err.status };
    }
    return null;
  }
}

export default async function LedgerPage() {
  const [claims, deviations, calibration] = await Promise.all([
    fetchOrNull<ClaimListResponse>("/api/dashboard/ledger/claims?limit=100"),
    fetchOrNull<DeviationListResponse>("/api/dashboard/ledger/deviations?limit=100"),
    fetchOrNull<CalibrationResponse>("/api/dashboard/ledger/calibration"),
  ]);

  return (
    <div className="flex flex-col gap-6 p-6">
      <PageHeader
        title="Dialogue Ledger"
        description="Every claim, deviation, and calibration event. User self-reports enter as hypotheses; learnings appear only after causal adjudication."
      />

      <Tabs defaultValue="claims" className="flex flex-col gap-4">
        <TabsList>
          <TabsTrigger value="claims">
            Claims{" "}
            {isList(claims) ? <Count n={claims.total} /> : null}
          </TabsTrigger>
          <TabsTrigger value="deviations">
            Deviations{" "}
            {isDeviations(deviations) ? <Count n={deviations.total} /> : null}
          </TabsTrigger>
          <TabsTrigger value="calibration">Calibration</TabsTrigger>
          <TabsTrigger value="sandbox">Sandbox</TabsTrigger>
        </TabsList>

        <TabsContent value="claims">
          {claims === null ? (
            <Unreachable />
          ) : "error" in claims ? (
            <ErrorAlert status={claims.status} message={claims.error} />
          ) : (
            <ClaimsTable claims={claims.claims} />
          )}
        </TabsContent>

        <TabsContent value="deviations">
          {deviations === null ? (
            <Unreachable />
          ) : "error" in deviations ? (
            <ErrorAlert status={deviations.status} message={deviations.error} />
          ) : (
            <DeviationsTable deviations={deviations.deviations} />
          )}
        </TabsContent>

        <TabsContent value="calibration">
          {calibration === null ? (
            <Unreachable />
          ) : "error" in calibration ? (
            <ErrorAlert
              status={calibration.status}
              message={calibration.error}
            />
          ) : (
            <CalibrationView data={calibration} />
          )}
        </TabsContent>

        <TabsContent value="sandbox">
          <Sandbox />
        </TabsContent>
      </Tabs>
    </div>
  );
}

function Count({ n }: { n: number }) {
  return (
    <span className="ml-1 rounded-full bg-muted px-1.5 py-0.5 text-[10px] tabular-nums">
      {n}
    </span>
  );
}

function isList(x: unknown): x is ClaimListResponse {
  return (
    typeof x === "object" &&
    x !== null &&
    "claims" in x &&
    "total" in (x as object)
  );
}

function isDeviations(x: unknown): x is DeviationListResponse {
  return (
    typeof x === "object" &&
    x !== null &&
    "deviations" in x &&
    "total" in (x as object)
  );
}

function ErrorAlert({
  status,
  message,
}: {
  status: number;
  message: string;
}) {
  return (
    <Alert variant="destructive">
      <AlertTitle>API error</AlertTitle>
      <AlertDescription>
        {message} (HTTP {status})
      </AlertDescription>
    </Alert>
  );
}

function Unreachable() {
  return (
    <Alert variant="destructive">
      <AlertTitle>Backend unreachable</AlertTitle>
      <AlertDescription>
        Could not reach the dashboard API. Check the backend is running and
        NEXT_PUBLIC_API_BASE_URL is set correctly.
      </AlertDescription>
    </Alert>
  );
}
