import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { PageHeader } from "@/components/page-header";

export const metadata = {
  title: "Campaigns · INFORMATIV",
};

export default function CampaignsPage() {
  return (
    <div className="flex flex-col gap-6 p-6">
      <PageHeader
        title="Campaigns"
        description="Active campaigns with live performance and bilateral-cascade intelligence."
      />
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center justify-between">
              <span>LUXY Ride · Pilot</span>
              <Badge variant="secondary">Live</Badge>
            </CardTitle>
            <CardDescription>Luxury transport · bilateral alignment 0.81</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-3 gap-4 text-sm">
              <Stat label="Spent" value="$53K" />
              <Stat label="CPA" value="$1,131" />
              <Stat label="Archetypes" value="10" />
            </div>
          </CardContent>
        </Card>
        <Card className="border-dashed">
          <CardHeader>
            <CardTitle className="text-muted-foreground">Pending integration</CardTitle>
            <CardDescription>
              Live StackAdapt data + bilateral cascade pulled from Tasks 23–26.
              Wiring in progress.
            </CardDescription>
          </CardHeader>
        </Card>
      </div>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-xs text-muted-foreground">{label}</div>
      <div className="text-lg font-semibold">{value}</div>
    </div>
  );
}
