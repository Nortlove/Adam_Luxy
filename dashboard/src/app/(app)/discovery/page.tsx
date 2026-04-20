import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { PageHeader } from "@/components/page-header";

export const metadata = {
  title: "Discovery · INFORMATIV",
};

const PHASES = [
  { n: 1, name: "Brand Discovery", status: "Pending" },
  { n: 2, name: "Audience Hypothesis", status: "Pending" },
  { n: 3, name: "Campaign Objective", status: "Pending" },
  { n: 4, name: "First-Party Data Ingestion", status: "Pending" },
  { n: 5, name: "Category & Competitive Context", status: "Future" },
  { n: 6, name: "Creative Constraints & Brand Safety", status: "Future" },
  { n: 7, name: "Media & Budget Reality", status: "Future" },
  { n: 8, name: "Launch Gates & Collaboration Contract", status: "Future" },
];

export default function DiscoveryPage() {
  return (
    <div className="flex flex-col gap-6 p-6">
      <PageHeader
        title="Discovery"
        description="The question dance. Eight phases mapping brand, audience, goal, and data onto the bilateral cascade."
      />
      <div className="grid gap-3">
        {PHASES.map((phase) => (
          <Card key={phase.n}>
            <CardHeader className="flex flex-row items-center justify-between gap-4 space-y-0">
              <div>
                <CardTitle className="text-base">
                  Phase {phase.n} · {phase.name}
                </CardTitle>
                <CardDescription>
                  {phase.status === "Future"
                    ? "Scheduled for Weeks 7–8 after foundation lands."
                    : "Awaiting question-architecture implementation."}
                </CardDescription>
              </div>
              <span className="text-xs uppercase text-muted-foreground">
                {phase.status}
              </span>
            </CardHeader>
          </Card>
        ))}
      </div>
    </div>
  );
}
