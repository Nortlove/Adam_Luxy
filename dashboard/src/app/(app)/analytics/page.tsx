import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { PageHeader } from "@/components/page-header";

export const metadata = {
  title: "Analytics · INFORMATIV",
};

export default function AnalyticsPage() {
  return (
    <div className="flex flex-col gap-6 p-6">
      <PageHeader
        title="Daily Analytics"
        description="Causal narrative dashboards. Pulls from Tasks 23–32. Hypothesis-tested. Horizon-aware."
      />
      <div className="grid gap-4 md:grid-cols-2">
        <Card className="border-dashed">
          <CardHeader>
            <CardTitle>Coming in Week 1–2</CardTitle>
            <CardDescription>
              Per-campaign daily pull, mechanism-level ROI, archetype
              performance, scope-determined learnings.
            </CardDescription>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground">
            Wires directly to existing Task 23 (DSP performance pull) and
            Task 26 (bilateral analysis) outputs — no new backend work, just
            a rendering layer.
          </CardContent>
        </Card>
        <Card className="border-dashed">
          <CardHeader>
            <CardTitle>Causal narrative (Week 3–4)</CardTitle>
            <CardDescription>
              Not charts. Stories with a posterior. &quot;CPA moved +12% this
              week; 73% attributable to mechanism rotation in the
              Conscientious-Optimizer archetype; horizon: 14-day stable.&quot;
            </CardDescription>
          </CardHeader>
        </Card>
      </div>
    </div>
  );
}
