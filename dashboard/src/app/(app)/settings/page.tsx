import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { PageHeader } from "@/components/page-header";
import { getCurrentUser } from "@/lib/auth";

export const metadata = {
  title: "Settings · INFORMATIV",
};

export default function SettingsPage() {
  const user = getCurrentUser();

  return (
    <div className="flex flex-col gap-6 p-6">
      <PageHeader
        title="Settings"
        description="Account and platform configuration."
      />
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
