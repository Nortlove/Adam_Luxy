import { ApiError, api } from "@/lib/api";
import type {
  DecayReport,
  DeviationHorizonResponse,
} from "@/lib/types";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { PageHeader } from "@/components/page-header";
import { DecayReportView } from "./_components/decay-report";
import { HorizonsView } from "./_components/horizons";

export const metadata = {
  title: "Learning · INFORMATIV",
};

export const dynamic = "force-dynamic";

async function fetchOrNull<T>(path: string) {
  try {
    return await api.get<T>(path);
  } catch (err) {
    if (err instanceof ApiError) {
      return { error: err.message, status: err.status };
    }
    return null;
  }
}

export default async function LearningPage() {
  const [decay, horizons] = await Promise.all([
    fetchOrNull<DecayReport>("/api/dashboard/decay/report"),
    fetchOrNull<DeviationHorizonResponse>(
      "/api/dashboard/deviations/horizons",
    ),
  ]);

  return (
    <div className="flex flex-col gap-6 p-6">
      <PageHeader
        title="Learning"
        description="Task 33 Decay Adjudicator output and multi-horizon adjudication progress on deviations. Where Loop A (analytics) and Loop B (teaming) cross-pollinate."
      />

      <Tabs defaultValue="decay" className="flex flex-col gap-4">
        <TabsList>
          <TabsTrigger value="decay">Decay Adjudicator</TabsTrigger>
          <TabsTrigger value="horizons">
            Adjudication Horizons
            {isHorizons(horizons) && horizons.ready_count > 0 && (
              <span className="ml-1 rounded-full bg-emerald-500 px-1.5 py-0.5 text-[10px] font-semibold text-white">
                {horizons.ready_count}
              </span>
            )}
          </TabsTrigger>
        </TabsList>

        <TabsContent value="decay">
          {decay === null ? (
            <ErrorAlert
              status={0}
              message="Could not reach the dashboard API."
            />
          ) : "error" in decay ? (
            <ErrorAlert status={decay.status} message={decay.error} />
          ) : (
            <DecayReportView report={decay} />
          )}
        </TabsContent>

        <TabsContent value="horizons">
          {horizons === null ? (
            <ErrorAlert
              status={0}
              message="Could not reach the dashboard API."
            />
          ) : "error" in horizons ? (
            <ErrorAlert status={horizons.status} message={horizons.error} />
          ) : (
            <HorizonsView data={horizons} />
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}

function isHorizons(x: unknown): x is DeviationHorizonResponse {
  return (
    typeof x === "object" &&
    x !== null &&
    "horizons" in x &&
    "ready_count" in (x as object)
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
        {message}
        {status ? ` (HTTP ${status})` : ""}
      </AlertDescription>
    </Alert>
  );
}
