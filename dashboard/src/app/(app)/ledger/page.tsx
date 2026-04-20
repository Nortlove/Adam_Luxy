import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { PageHeader } from "@/components/page-header";

export const metadata = {
  title: "Dialogue Ledger · INFORMATIV",
};

export default function LedgerPage() {
  return (
    <div className="flex flex-col gap-6 p-6">
      <PageHeader
        title="Dialogue Ledger"
        description="Every claim, deviation, and calibration event. User self-reports enter as hypotheses; learnings appear only after causal adjudication."
      />
      <div className="grid gap-4 md:grid-cols-3">
        <Card className="border-dashed">
          <CardHeader>
            <CardTitle>Claims</CardTitle>
            <CardDescription>
              Timestamp, elicitation mode, stated confidence, current
              learning status.
            </CardDescription>
          </CardHeader>
        </Card>
        <Card className="border-dashed">
          <CardHeader>
            <CardTitle>Deviations</CardTitle>
            <CardDescription>
              Every override of an AI recommendation — with the stated
              rationale, counterfactual, and adjudication outcome once the
              horizon passes.
            </CardDescription>
          </CardHeader>
        </Card>
        <Card className="border-dashed">
          <CardHeader>
            <CardTitle>Calibration</CardTitle>
            <CardDescription>
              Per-domain Brier score. Track your forecasting accuracy and
              watch it improve over time.
            </CardDescription>
          </CardHeader>
        </Card>
      </div>
    </div>
  );
}
