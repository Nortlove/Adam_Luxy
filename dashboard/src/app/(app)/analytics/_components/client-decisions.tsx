"use client";

/**
 * Client Decisions Audit — Front-end B internal surface.
 *
 * Renders every client-rec acknowledge/decline event captured by the
 * Front-end A persistence flow, joined with its Deviation +
 * adjudication status where applicable. This is the operator's window
 * into what clients are doing with the recommendations the system
 * generates — trust-calibration signal, decline-pattern surfacing,
 * pending-adjudication visibility.
 *
 * Internal only. Shows full decision text, latency, feedback, and
 * adjudication outcomes — never rendered on client-facing surfaces.
 */

import { useEffect, useState } from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { CheckCircle2, XCircle, Clock, HelpCircle } from "lucide-react";
import type {
  ClientDecisionAuditEntry,
  ClientDecisionAuditResponse,
  ClientDecisionAuditSummary,
} from "@/lib/types";

function pct(v: number): string {
  return `${(v * 100).toFixed(1)}%`;
}

function formatRelative(iso: string): string {
  const ts = new Date(iso);
  if (Number.isNaN(ts.getTime())) return "—";
  return ts.toLocaleString(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

export function ClientDecisionsView() {
  const [data, setData] = useState<ClientDecisionAuditResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const res = await fetch(
          "/api/analytics/client-decisions?limit=100",
          { cache: "no-store" },
        );
        if (!res.ok) {
          const body = (await res.json().catch(() => null)) as
            | { error?: string }
            | null;
          throw new Error(
            body?.error ?? `Request failed (HTTP ${res.status})`,
          );
        }
        const json = (await res.json()) as ClientDecisionAuditResponse;
        if (!cancelled) setData(json);
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Unknown error");
          setData(null);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, []);

  if (error) {
    return (
      <Alert variant="destructive">
        <AlertTitle>Could not load client-decisions audit</AlertTitle>
        <AlertDescription>{error}</AlertDescription>
      </Alert>
    );
  }
  if (loading || !data) {
    return (
      <Card className="border-dashed">
        <CardContent className="py-6 text-center text-sm text-muted-foreground">
          Loading client decisions…
        </CardContent>
      </Card>
    );
  }

  if (data.summary.total_decisions === 0) {
    return (
      <Card className="border-dashed">
        <CardHeader>
          <CardTitle>No client decisions yet</CardTitle>
          <CardDescription>
            When advertisers click Approve or Decline on a
            recommendation in the client report, the decision lands
            here with full audit trail — latency, feedback, and
            adjudication state for declines that entered the causal
            pipeline.
          </CardDescription>
        </CardHeader>
      </Card>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <SummaryCard summary={data.summary} />
      <DecisionsTable entries={data.entries} />
    </div>
  );
}

function SummaryCard({ summary }: { summary: ClientDecisionAuditSummary }) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base">Decision audit summary</CardTitle>
        <CardDescription>
          Every acknowledge / decline event clients have produced. Decline
          + feedback becomes a Claim. Decline alone becomes a Deviation
          that enters the causal adjudicator at horizon expiry.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <dl className="grid grid-cols-2 gap-4 text-sm md:grid-cols-4">
          <Stat label="Total decisions" value={summary.total_decisions.toString()} />
          <Stat label="Acceptance rate" value={pct(summary.acceptance_rate)} />
          <Stat label="Declines w/ feedback" value={summary.declines_with_feedback.toString()} />
          <Stat label="Pending adjudication" value={summary.pending_adjudication.toString()} />
        </dl>
        <dl className="mt-4 grid grid-cols-2 gap-4 text-sm md:grid-cols-4">
          <Stat
            label="Acknowledge"
            value={summary.acknowledge_count.toString()}
            icon={<CheckCircle2 className="size-4 text-emerald-500" />}
          />
          <Stat
            label="Decline"
            value={summary.decline_count.toString()}
            icon={<XCircle className="size-4 text-rose-500" />}
          />
          <Stat
            label="Adjudicated · system right"
            value={summary.adjudicated_system_right.toString()}
          />
          <Stat
            label="Adjudicated · user right"
            value={summary.adjudicated_user_right.toString()}
          />
        </dl>
      </CardContent>
    </Card>
  );
}

function DecisionsTable({
  entries,
}: {
  entries: ClientDecisionAuditEntry[];
}) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base">Decision timeline</CardTitle>
        <CardDescription>
          Most recent first. Latency captured as Type-1 / Type-2 signal —
          fast decisions indicate tacit/confident, slow decisions
          indicate deliberation.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-2">
        {entries.map((e) => (
          <DecisionRow key={e.decision_id} entry={e} />
        ))}
      </CardContent>
    </Card>
  );
}

function DecisionRow({ entry }: { entry: ClientDecisionAuditEntry }) {
  const isAck = entry.decision_kind === "acknowledge";
  const accent = isAck ? "border-l-emerald-500" : "border-l-rose-500";
  return (
    <div className={`rounded-md border border-border/60 border-l-4 ${accent} px-3 py-2 text-sm`}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          {isAck ? (
            <Badge className="bg-emerald-500 text-white">
              <CheckCircle2 className="mr-1 size-3" />
              Acknowledged
            </Badge>
          ) : (
            <Badge variant="outline" className="border-rose-500/60 text-rose-600 dark:text-rose-400">
              <XCircle className="mr-1 size-3" />
              Declined
            </Badge>
          )}
          <span className="truncate font-medium">{entry.rec_headline}</span>
        </div>
        <div className="flex items-center gap-2 font-mono text-xs text-muted-foreground">
          {entry.latency_ms != null && (
            <span title="Time to decide from when the rec rendered">
              {entry.latency_ms < 1000
                ? `${entry.latency_ms}ms`
                : `${(entry.latency_ms / 1000).toFixed(1)}s`}
            </span>
          )}
          <span>{formatRelative(entry.decided_at)}</span>
        </div>
      </div>
      {entry.advertiser_id && (
        <div className="mt-1 text-xs text-muted-foreground">
          advertiser · <span className="font-mono">{entry.advertiser_id}</span>
        </div>
      )}
      {entry.feedback_text && (
        <div className="mt-2 rounded-md bg-muted/30 px-3 py-2 text-xs italic">
          "{entry.feedback_text}"
        </div>
      )}
      {!isAck && (
        <AdjudicationBadge
          status={entry.adjudication_status}
          outcome={entry.adjudication_outcome}
          observation={entry.outcome_observation}
        />
      )}
    </div>
  );
}

function AdjudicationBadge({
  status,
  outcome,
  observation,
}: {
  status: string | null;
  outcome: string | null;
  observation: string | null;
}) {
  if (status === null) return null;

  // Parse observation JSON if present to surface a short snippet.
  let rationale: string | null = null;
  if (observation) {
    try {
      const parsed = JSON.parse(observation) as {
        rationale?: string;
        pending_weakness?: string;
      };
      rationale = parsed.rationale ?? null;
    } catch {
      // Ignore malformed observations.
    }
  }

  if (status === "pending") {
    return (
      <div className="mt-2 flex items-start gap-2 text-xs text-muted-foreground">
        <Clock className="mt-0.5 size-3 shrink-0" />
        <span>
          Deviation pending adjudication — will be evaluated at horizon
          expiry.
        </span>
      </div>
    );
  }

  // Adjudicated.
  const outcomeKind =
    outcome === "user_right"
      ? "user right"
      : outcome === "system_right"
        ? "system right"
        : "indeterminate";
  const accent =
    outcome === "user_right"
      ? "text-emerald-600 dark:text-emerald-400"
      : outcome === "system_right"
        ? "text-amber-600 dark:text-amber-400"
        : "text-muted-foreground";
  const Icon =
    outcome === "user_right"
      ? CheckCircle2
      : outcome === "system_right"
        ? CheckCircle2
        : HelpCircle;

  return (
    <div className={`mt-2 flex items-start gap-2 text-xs ${accent}`}>
      <Icon className="mt-0.5 size-3 shrink-0" />
      <div>
        <span className="font-semibold uppercase">{outcomeKind}</span>
        {rationale && (
          <span className="ml-1 text-muted-foreground">· {rationale}</span>
        )}
      </div>
    </div>
  );
}

function Stat({
  label,
  value,
  icon,
}: {
  label: string;
  value: string;
  icon?: React.ReactNode;
}) {
  return (
    <div>
      <dt className="flex items-center gap-1 text-xs uppercase text-muted-foreground">
        {icon}
        <span>{label}</span>
      </dt>
      <dd className="text-lg font-semibold tabular-nums">{value}</dd>
    </div>
  );
}
