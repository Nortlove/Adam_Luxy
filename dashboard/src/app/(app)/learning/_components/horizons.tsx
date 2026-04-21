import Link from "next/link";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import type {
  DeviationHorizon,
  DeviationHorizonResponse,
  HorizonStatus,
} from "@/lib/types";

export function HorizonsView({ data }: { data: DeviationHorizonResponse }) {
  if (data.total === 0) {
    return (
      <Card className="border-dashed">
        <CardHeader>
          <CardTitle>No deviations to adjudicate</CardTitle>
          <CardDescription>
            When you reject or modify a recommendation, it becomes a
            Deviation with a horizon_class. The causal-adjudication
            pipeline waits for the horizon window to close before ruling
            user-right / system-right / indeterminate.
          </CardDescription>
        </CardHeader>
      </Card>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      {data.ready_count > 0 && (
        <Alert>
          <AlertTitle>
            {data.ready_count} deviation{data.ready_count === 1 ? "" : "s"} ready for adjudication
          </AlertTitle>
          <AlertDescription>
            The horizon window has closed. These deviations can be
            causally tested against the observed outcome. v1 flags them
            here; the actual adjudication runs when Loop A outcome data
            is wired through.
          </AlertDescription>
        </Alert>
      )}

      <div className="grid gap-3">
        {data.horizons.map((h) => (
          <HorizonRow key={h.deviation_id} h={h} />
        ))}
      </div>
    </div>
  );
}

function HorizonRow({ h }: { h: DeviationHorizon }) {
  const totalDays = h.days_elapsed + h.days_remaining;
  const pct = totalDays > 0 ? (h.days_elapsed / totalDays) * 100 : 100;
  const clampedPct = Math.max(0, Math.min(100, pct));

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center justify-between gap-2 text-sm">
          <Link
            href={`/recommendations/${encodeURIComponent(h.recommendation_id)}`}
            className="truncate hover:underline"
          >
            {h.recommendation_id.replace(/^rec:/, "")}
          </Link>
          <StatusBadge status={h.status} outcome={h.adjudication_outcome} />
        </CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-2 text-xs">
        <div>
          horizon: <span className="font-semibold">{h.horizon_class}</span>{" "}
          · {h.days_elapsed.toFixed(1)}d elapsed ·{" "}
          {h.days_remaining > 0
            ? `${h.days_remaining.toFixed(1)}d until adjudication window closes`
            : "window closed"}
        </div>
        <div className="h-1 w-full overflow-hidden rounded-full bg-muted">
          <div
            className={progressColorForStatus(h.status)}
            style={{ width: `${clampedPct}%`, height: "100%" }}
          />
        </div>
        <div className="flex justify-between text-muted-foreground">
          <span>created {new Date(h.created_at).toLocaleDateString()}</span>
          <span>
            window closes{" "}
            {new Date(h.horizon_ends_at).toLocaleDateString()}
          </span>
        </div>
      </CardContent>
    </Card>
  );
}

function StatusBadge({
  status,
  outcome,
}: {
  status: HorizonStatus;
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
  const map: Record<HorizonStatus, { variant: "default" | "secondary" | "destructive" | "outline"; label: string }> = {
    too_early: { variant: "outline", label: "too early" },
    in_progress: { variant: "outline", label: "in progress" },
    ready: { variant: "default", label: "ready" },
    adjudicated: { variant: "secondary", label: "adjudicated" },
  };
  const { variant, label } = map[status];
  return <Badge variant={variant}>{label}</Badge>;
}

function progressColorForStatus(status: HorizonStatus): string {
  switch (status) {
    case "ready":
      return "bg-emerald-500 h-full";
    case "adjudicated":
      return "bg-primary h-full";
    case "in_progress":
      return "bg-amber-500 h-full";
    default:
      return "bg-muted-foreground/40 h-full";
  }
}
