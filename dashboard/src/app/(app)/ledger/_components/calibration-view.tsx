import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import type {
  CalibrationResponse,
  DomainCalibration,
} from "@/lib/types";
import { formatInt } from "@/lib/format";

export function CalibrationView({ data }: { data: CalibrationResponse }) {
  if (data.source === "unavailable") {
    return (
      <Alert>
        <AlertTitle>Calibration unavailable</AlertTitle>
        <AlertDescription>
          {data.source_note ?? "Neo4j must be reachable to compute calibration."}
        </AlertDescription>
      </Alert>
    );
  }

  if (data.domains.length === 0) {
    return (
      <>
        <Card className="border-dashed">
          <CardHeader>
            <CardTitle>No calibration data yet</CardTitle>
            <CardDescription>
              Start making claims (Sandbox tab) and the per-domain profile
              will populate — activity counts, recallability breakdown, and
              latency averages first, with Brier-scored calibration curves
              activating once outcomes have been observed and adjudicated.
            </CardDescription>
          </CardHeader>
        </Card>
        <TrainingCTA />
      </>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      {data.source_note && (
        <p className="text-sm text-muted-foreground">{data.source_note}</p>
      )}
      <TrainingCTA />
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {data.domains.map((d) => (
          <DomainCard key={d.domain} d={d} />
        ))}
      </div>
    </div>
  );
}

function TrainingCTA() {
  return (
    <Alert>
      <AlertTitle>Take the calibration training</AlertTitle>
      <AlertDescription>
        Ten binary forecasts with live Brier scoring (Tetlock/Mellers
        protocol). Trains you to produce calibrated probability estimates
        rather than round numbers.{" "}
        <a
          href="/calibration"
          className="font-medium text-foreground underline-offset-4 hover:underline"
        >
          Start the training →
        </a>
      </AlertDescription>
    </Alert>
  );
}

function DomainCard({ d }: { d: DomainCalibration }) {
  const tacitPct =
    d.total_claims > 0
      ? Math.round((d.fluent_recall_count / d.total_claims) * 100)
      : 0;
  const confabPct =
    d.total_claims > 0
      ? Math.round((d.absent_recall_count / d.total_claims) * 100)
      : 0;
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base capitalize">
          {d.domain.replace(/_/g, " ")}
        </CardTitle>
        <CardDescription>
          {formatInt(d.total_claims)} claim
          {d.total_claims === 1 ? "" : "s"} in this domain
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-3 text-sm">
        <RecallBar
          label="Fluent (tacit)"
          count={d.fluent_recall_count}
          total={d.total_claims}
          colorClass="bg-emerald-500"
        />
        <RecallBar
          label="Hesitant"
          count={d.hesitant_recall_count}
          total={d.total_claims}
          colorClass="bg-amber-500"
        />
        <RecallBar
          label="Absent (watch)"
          count={d.absent_recall_count}
          total={d.total_claims}
          colorClass="bg-rose-500"
        />

        <dl className="mt-2 grid grid-cols-2 gap-3 border-t pt-3 text-xs">
          <div>
            <dt className="text-muted-foreground">Avg latency</dt>
            <dd className="tabular-nums">
              {d.avg_latency_ms != null
                ? `${Math.round(d.avg_latency_ms)} ms`
                : "—"}
            </dd>
          </div>
          <div>
            <dt className="text-muted-foreground">Validated</dt>
            <dd className="tabular-nums">
              {d.validated_count} / {d.total_claims}
            </dd>
          </div>
          <div>
            <dt className="text-muted-foreground">Brier</dt>
            <dd className="tabular-nums">
              {d.brier_score != null ? d.brier_score.toFixed(3) : "—"}
            </dd>
          </div>
          <div>
            <dt className="text-muted-foreground">Tacit rate</dt>
            <dd className="tabular-nums">{tacitPct}%</dd>
          </div>
        </dl>

        {confabPct > 40 && d.total_claims >= 3 && (
          <Alert variant="destructive">
            <AlertTitle>High absent-recall rate</AlertTitle>
            <AlertDescription>
              {confabPct}% of claims in this domain failed the
              recallability probe. Future claims in this domain will be
              weighted more skeptically.
            </AlertDescription>
          </Alert>
        )}
      </CardContent>
    </Card>
  );
}

function RecallBar({
  label,
  count,
  total,
  colorClass,
}: {
  label: string;
  count: number;
  total: number;
  colorClass: string;
}) {
  const pct = total > 0 ? (count / total) * 100 : 0;
  return (
    <div>
      <div className="mb-1 flex items-center justify-between text-xs">
        <span className="text-muted-foreground">{label}</span>
        <span className="tabular-nums">{count}</span>
      </div>
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
        <div
          className={`h-full ${colorClass}`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}
