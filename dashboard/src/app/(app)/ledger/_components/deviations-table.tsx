import Link from "next/link";
import {
  Card,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { DeviationSummary } from "@/lib/types";

export function DeviationsTable({ deviations }: { deviations: DeviationSummary[] }) {
  if (deviations.length === 0) {
    return (
      <Card className="border-dashed">
        <CardHeader>
          <CardTitle>No deviations yet</CardTitle>
          <CardDescription>
            Deviations appear here every time you modify or reject an AI
            recommendation. Each one carries the system&rsquo;s preferred
            choice, your choice, and your stated rationale — held as a
            hypothesis until the horizon passes.
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
            <th className="px-3 py-2 text-left font-medium">System chose</th>
            <th className="px-3 py-2 text-left font-medium">You chose</th>
            <th className="px-3 py-2 text-left font-medium">Rationale</th>
            <th className="px-3 py-2 text-left font-medium">Horizon</th>
            <th className="px-3 py-2 text-left font-medium">Adjudication</th>
          </tr>
        </thead>
        <tbody>
          {deviations.map((d) => (
            <tr key={d.id} className="border-t">
              <td className="px-3 py-2 align-top text-xs text-muted-foreground">
                {new Date(d.created_at).toLocaleString()}
              </td>
              <td className="px-3 py-2 align-top text-xs">
                <code className="rounded bg-muted px-1 py-0.5">
                  {d.system_choice}
                </code>
              </td>
              <td className="px-3 py-2 align-top text-xs">
                <code className="rounded bg-muted px-1 py-0.5">
                  {d.user_choice ?? "(rejected)"}
                </code>
              </td>
              <td className="px-3 py-2 align-top">
                <div className="text-sm">
                  {d.rationale_class && (
                    <Badge
                      variant="outline"
                      className="mr-2 text-[10px] uppercase"
                    >
                      {d.rationale_class.replace(/_/g, " ")}
                    </Badge>
                  )}
                  {d.stated_rationale ? (
                    <span className="line-clamp-2 max-w-md">
                      {d.stated_rationale}
                    </span>
                  ) : (
                    <span className="text-xs italic text-muted-foreground">
                      no rationale provided
                    </span>
                  )}
                </div>
              </td>
              <td className="px-3 py-2 align-top text-xs">
                {d.horizon_class}
              </td>
              <td className="px-3 py-2 align-top">
                <AdjudicationBadge
                  status={d.adjudication_status}
                  outcome={d.adjudication_outcome}
                />
                <div className="mt-1">
                  <Link
                    href={`/recommendations/${encodeURIComponent(d.recommendation_id)}`}
                    className="text-xs text-muted-foreground hover:text-foreground"
                  >
                    see recommendation →
                  </Link>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function AdjudicationBadge({
  status,
  outcome,
}: {
  status: string;
  outcome: string | null;
}) {
  if (status === "adjudicated" && outcome) {
    const variant =
      outcome === "user_right"
        ? "default"
        : outcome === "system_right"
          ? "secondary"
          : "outline";
    return <Badge variant={variant}>{outcome.replace(/_/g, " ")}</Badge>;
  }
  return (
    <Badge variant="outline" className="text-[10px]">
      {status}
    </Badge>
  );
}
