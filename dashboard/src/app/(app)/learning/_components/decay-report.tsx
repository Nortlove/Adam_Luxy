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
  CampaignDecayClassification,
  DecayAction,
  DecayReport,
} from "@/lib/types";
import { formatUsd } from "@/lib/format";

export function DecayReportView({ report }: { report: DecayReport }) {
  return (
    <div className="flex flex-col gap-4">
      {report.source === "unavailable" ? (
        <Alert>
          <AlertTitle>Task 33 could not run</AlertTitle>
          <AlertDescription>
            {report.source_note ??
              "StackAdapt must be reachable to classify decay."}
          </AlertDescription>
        </Alert>
      ) : (
        <p className="text-sm text-muted-foreground">
          Run {report.run_id.slice(0, 18)}… · task {report.task_version} ·
          last run {new Date(report.run_date).toLocaleString()}
        </p>
      )}

      {report.source_note && report.source === "live" && (
        <Alert>
          <AlertDescription>{report.source_note}</AlertDescription>
        </Alert>
      )}

      {report.campaigns.length === 0 ? (
        <Card className="border-dashed">
          <CardHeader>
            <CardTitle>No campaigns to classify</CardTitle>
            <CardDescription>
              Task 33 runs per campaign. When StackAdapt has live campaigns
              to adjudicate, they&rsquo;ll appear here as CONTINUE / RESTART
              / ABANDON / MONITOR recommendations.
            </CardDescription>
          </CardHeader>
        </Card>
      ) : (
        <div className="grid gap-4">
          {report.campaigns.map((c) => (
            <CampaignDecayCard key={c.campaign_id} c={c} />
          ))}
        </div>
      )}

      <Alert>
        <AlertTitle>About the three-way split</AlertTitle>
        <AlertDescription>
          CONTINUE: healthy · RESTART: rotate mechanism before declaring
          non-response · ABANDON: only after mechanism-shift has failed
          (not reached in v1 — requires rotation history) · MONITOR: not
          enough impressions yet. ABANDON is deliberately gated behind
          evidence per the HMT foundation&rsquo;s inferential-vs-correlational
          rule.
        </AlertDescription>
      </Alert>
    </div>
  );
}

function CampaignDecayCard({ c }: { c: CampaignDecayClassification }) {
  return (
    <Card className={cardBorderForAction(c.recommended_action)}>
      <CardHeader>
        <CardTitle className="flex items-center justify-between gap-3 text-base">
          <span className="truncate">{c.campaign_name}</span>
          <ActionBadge action={c.recommended_action} />
        </CardTitle>
        <CardDescription>{c.rationale}</CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        <div className="grid grid-cols-2 gap-3 text-sm md:grid-cols-4">
          <Stat
            label="Campaign CPA"
            value={c.campaign_cpa != null ? formatUsd(c.campaign_cpa) : "—"}
          />
          <Stat
            label="Advertiser avg CPA"
            value={
              c.advertiser_avg_cpa != null
                ? formatUsd(c.advertiser_avg_cpa)
                : "—"
            }
          />
          <Stat
            label="CPA multiple"
            value={
              c.campaign_cpa != null &&
              c.advertiser_avg_cpa != null &&
              c.advertiser_avg_cpa > 0
                ? `${(c.campaign_cpa / c.advertiser_avg_cpa).toFixed(2)}×`
                : "—"
            }
          />
          <Stat label="Users classified" value={c.total_users.toString()} />
        </div>
        {c.flags.length > 0 && (
          <div className="flex flex-wrap items-center gap-1 text-xs">
            <span className="uppercase text-muted-foreground">Flags:</span>
            {c.flags.map((f) => (
              <Badge key={f} variant="outline" className="text-[10px]">
                {f.replace(/_/g, " ")}
              </Badge>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function ActionBadge({ action }: { action: DecayAction }) {
  const map: Record<DecayAction, { variant: "default" | "secondary" | "destructive" | "outline"; label: string }> = {
    continue: { variant: "default", label: "CONTINUE" },
    monitor: { variant: "outline", label: "MONITOR" },
    restart: { variant: "secondary", label: "RESTART" },
    abandon: { variant: "destructive", label: "ABANDON" },
  };
  const { variant, label } = map[action];
  return <Badge variant={variant}>{label}</Badge>;
}

function cardBorderForAction(action: DecayAction): string {
  switch (action) {
    case "restart":
      return "border-amber-200 dark:border-amber-900";
    case "abandon":
      return "border-rose-200 dark:border-rose-900";
    case "continue":
      return "";
    default:
      return "border-dashed";
  }
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-xs uppercase text-muted-foreground">{label}</div>
      <div className="text-sm font-semibold">{value}</div>
    </div>
  );
}
