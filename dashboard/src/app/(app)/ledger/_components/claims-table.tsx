import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { ClaimResponse } from "@/lib/types";

export function ClaimsTable({ claims }: { claims: ClaimResponse[] }) {
  if (claims.length === 0) {
    return (
      <Card className="border-dashed">
        <CardHeader>
          <CardTitle>No claims yet</CardTitle>
          <CardDescription>
            Every elicitation — forced pair, timed pair, story prompt,
            recallability probe — records here as a hypothesis. Run one
            from the Sandbox tab to see the shape.
          </CardDescription>
        </CardHeader>
      </Card>
    );
  }

  return (
    <div className="overflow-hidden rounded-lg border">
      <table className="w-full text-sm">
        <thead className="bg-muted/50 text-xs uppercase text-muted-foreground">
          <tr>
            <th className="px-3 py-2 text-left font-medium">When</th>
            <th className="px-3 py-2 text-left font-medium">Mode</th>
            <th className="px-3 py-2 text-left font-medium">Domain</th>
            <th className="px-3 py-2 text-left font-medium">Text</th>
            <th className="px-3 py-2 text-left font-medium">Latency</th>
            <th className="px-3 py-2 text-left font-medium">Status</th>
          </tr>
        </thead>
        <tbody>
          {claims.map((c) => (
            <tr key={c.id} className="border-t">
              <td className="px-3 py-2 align-top text-xs text-muted-foreground">
                {new Date(c.created_at).toLocaleString()}
              </td>
              <td className="px-3 py-2 align-top">
                <Badge variant="outline" className="text-xs">
                  {c.elicitation_mode.replace(/_/g, " ")}
                </Badge>
              </td>
              <td className="px-3 py-2 align-top text-xs">{c.domain}</td>
              <td className="px-3 py-2 align-top">
                <div className="line-clamp-3 max-w-xl">{c.text}</div>
                {c.recallability && (
                  <div className="mt-1 text-xs text-muted-foreground">
                    recallability: {c.recallability}
                  </div>
                )}
              </td>
              <td className="px-3 py-2 align-top text-xs tabular-nums">
                {c.latency_ms != null ? `${c.latency_ms} ms` : "—"}
              </td>
              <td className="px-3 py-2 align-top">
                <StatusBadge status={c.status} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const variant = status.startsWith("validated_user")
    ? "default"
    : status.startsWith("validated_system")
      ? "secondary"
      : status === "retired"
        ? "outline"
        : "outline";
  return (
    <Badge variant={variant} className="text-[10px]">
      {status.replace(/_/g, " ")}
    </Badge>
  );
}
