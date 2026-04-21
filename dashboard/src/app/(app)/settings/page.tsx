import { ApiError, api } from "@/lib/api";
import type { AutopilotSettings } from "@/lib/types";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { PageHeader } from "@/components/page-header";
import { getCurrentUser } from "@/lib/auth";
import { AutopilotPanel } from "./_components/autopilot-panel";

export const metadata = {
  title: "Settings · INFORMATIV",
};

export const dynamic = "force-dynamic";

async function loadAutopilot(): Promise<
  AutopilotSettings | { error: string; status: number } | null
> {
  try {
    return await api.get<AutopilotSettings>(
      "/api/dashboard/settings/autopilot",
    );
  } catch (err) {
    if (err instanceof ApiError) {
      return { error: err.message, status: err.status };
    }
    return null;
  }
}

export default async function SettingsPage() {
  const user = getCurrentUser();
  const autopilot = await loadAutopilot();

  return (
    <div className="flex flex-col gap-6 p-6">
      <PageHeader
        title="Settings"
        description="Account, autopilot trust curve, and backend connection."
      />

      {autopilot === null ? (
        <Alert variant="destructive">
          <AlertTitle>Backend unreachable</AlertTitle>
          <AlertDescription>
            Could not reach the dashboard API to load autopilot settings.
          </AlertDescription>
        </Alert>
      ) : "error" in autopilot ? (
        <Alert variant="destructive">
          <AlertTitle>API error</AlertTitle>
          <AlertDescription>
            {autopilot.error} (HTTP {autopilot.status})
          </AlertDescription>
        </Alert>
      ) : (
        <AutopilotPanel current={autopilot} />
      )}

      <Card>
        <CardHeader>
          <CardTitle>Account</CardTitle>
          <CardDescription>Single-tenant pilot · v1</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-3 text-sm">
          <Row label="Name" value={user.name} />
          <Row label="Email" value={user.email} />
          <Row label="Role" value={user.role} />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>API Connection</CardTitle>
          <CardDescription>
            Dashboard talks to the FastAPI backend via Bearer token.
          </CardDescription>
        </CardHeader>
        <CardContent className="grid gap-3 text-sm">
          <Row
            label="Backend"
            value={
              process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000"
            }
          />
          <Row
            label="Token"
            value={
              process.env.INFORMATIV_API_TOKEN
                ? "configured"
                : "missing — set INFORMATIV_API_TOKEN"
            }
          />
        </CardContent>
      </Card>
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="grid grid-cols-[120px_1fr] items-baseline gap-2">
      <span className="text-xs uppercase text-muted-foreground">{label}</span>
      <span className="font-mono text-sm">{value}</span>
    </div>
  );
}
