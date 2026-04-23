import { ApiError, api } from "@/lib/api";
import type {
  DecayReport,
  DeviationHorizonResponse,
  WhyLibraryResponse,
} from "@/lib/types";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { PageHeader } from "@/components/page-header";
import { DecayReportView } from "./_components/decay-report";
import { HorizonsView } from "./_components/horizons";
import { WhyLibraryView } from "./_components/why-library";
import { AdjudicateButton } from "./_components/adjudicate-button";
import { MechanismEffectivenessView } from "./_components/mechanism-effectiveness";
import { SubjectInspectionView } from "./_components/subject-inspection";

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
  const [decay, horizons, whyLib] = await Promise.all([
    fetchOrNull<DecayReport>("/api/dashboard/decay/report"),
    fetchOrNull<DeviationHorizonResponse>(
      "/api/dashboard/deviations/horizons",
    ),
    fetchOrNull<WhyLibraryResponse>("/api/dashboard/why-library"),
  ]);

  return (
    <div className="flex flex-col gap-6 p-6">
      <PageHeader
        title="Learning"
        description="Task 33 Decay Adjudicator output and multi-horizon adjudication progress on deviations. Where Loop A (analytics) and Loop B (teaming) cross-pollinate."
      />

      <Tabs defaultValue="mechanisms" className="flex flex-col gap-4">
        <TabsList>
          <TabsTrigger value="mechanisms">Mechanism Effectiveness</TabsTrigger>
          <TabsTrigger value="subject">Subject Inspection</TabsTrigger>
          <TabsTrigger value="decay">Decay Adjudicator</TabsTrigger>
          <TabsTrigger value="horizons">
            Adjudication Horizons
            {isHorizons(horizons) && horizons.ready_count > 0 && (
              <span className="ml-1 rounded-full bg-emerald-500 px-1.5 py-0.5 text-[10px] font-semibold text-white">
                {horizons.ready_count}
              </span>
            )}
          </TabsTrigger>
          <TabsTrigger value="why">
            Why Library
            {isWhy(whyLib) && whyLib.total > 0 && (
              <span className="ml-1 rounded-full bg-amber-500 px-1.5 py-0.5 text-[10px] font-semibold text-white">
                {whyLib.total}
              </span>
            )}
          </TabsTrigger>
        </TabsList>

        <TabsContent value="mechanisms">
          <MechanismEffectivenessView />
        </TabsContent>

        <TabsContent value="subject">
          <SubjectInspectionView />
        </TabsContent>

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

        <TabsContent value="horizons" className="flex flex-col gap-4">
          <AdjudicateButton
            readyCount={
              isHorizons(horizons) ? horizons.ready_count : 0
            }
          />
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

        <TabsContent value="why">
          {whyLib === null ? (
            <ErrorAlert
              status={0}
              message="Could not reach the dashboard API."
            />
          ) : "error" in whyLib ? (
            <ErrorAlert status={whyLib.status} message={whyLib.error} />
          ) : (
            <WhyLibraryView data={whyLib} />
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

function isWhy(x: unknown): x is WhyLibraryResponse {
  return (
    typeof x === "object" &&
    x !== null &&
    "entries" in x &&
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
        {message}
        {status ? ` (HTTP ${status})` : ""}
      </AlertDescription>
    </Alert>
  );
}
