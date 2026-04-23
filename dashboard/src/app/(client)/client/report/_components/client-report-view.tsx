"use client";

/**
 * ClientReportView — report-style render of the advertiser-facing payload.
 *
 * Discipline:
 *
 *   - NO internal taxonomy reaches this render. Every string comes from
 *     the backend's PublicLabelService-translated payload or from safe
 *     public performance metrics.
 *
 *   - NOT a dashboard: single-column, prose-heavy, executive feel.
 *     Cards act as section containers, not data tiles.
 *
 *   - Active recommendations use one-click acknowledgment. Explanation
 *     is rich natural language; no posteriors, no sample counts, no
 *     methodology jargon. Per Chris directive (2026-04-22):
 *     "very specific by way of explaining, but not by way of numbers
 *      and nodes and graph."
 *
 *   - missing_labels is an internal diagnostic only. It renders here as
 *     a subtle dev-visible banner for Chris during pilot; once role-
 *     scoping lands, it's suppressed for non-superadmin roles entirely.
 */

import { useMemo, useRef, useState } from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { CheckCircle2, Loader2, Sparkles, TrendingUp } from "lucide-react";
import {
  formatInt,
  formatPercent,
  formatUsd,
} from "@/lib/format";
import { Textarea } from "@/components/ui/textarea";
import type {
  ClientMessageObservation,
  ClientRecommendation,
  ClientRecommendationDecisionRequest,
  ClientRecommendationDecisionResponse,
  ClientReport,
  ClientSegmentHighlight,
} from "@/lib/types";

export function ClientReportView({ report }: { report: ClientReport }) {
  return (
    <div className="flex flex-col gap-6">
      <ReportMeta report={report} />
      {report.data_source_notes.length > 0 && (
        <DataSourceNotes notes={report.data_source_notes} />
      )}
      <PerformanceHeadline report={report} />
      {report.segment_highlights.length > 0 && (
        <SegmentHighlights highlights={report.segment_highlights} />
      )}
      {report.message_observations.length > 0 && (
        <MessageObservations observations={report.message_observations} />
      )}
      {report.recommendations.length > 0 && (
        <Recommendations
          initial={report.recommendations}
          advertiserId={report.advertiser_id}
        />
      )}
      {/* Internal-only diagnostic — suppress once role-scoping lands */}
      {report.missing_labels.length > 0 && (
        <MissingLabelsWarning missing={report.missing_labels} />
      )}
    </div>
  );
}

function ReportMeta({ report }: { report: ClientReport }) {
  const generated = new Date(report.generated_at);
  return (
    <Card className="border-none bg-muted/40 shadow-none">
      <CardHeader className="py-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex flex-col">
            <span className="text-xs uppercase text-muted-foreground">
              Advertiser
            </span>
            <span className="text-base font-semibold">
              {report.advertiser_name ?? report.advertiser_id}
            </span>
          </div>
          <div className="flex flex-col text-right">
            <span className="text-xs uppercase text-muted-foreground">
              Generated
            </span>
            <span className="text-sm font-medium">
              {/* Pin locale: server (Node's default) and client (browser's
                  locale) produce different strings with `undefined` and
                  trigger a React hydration mismatch. */}
              {generated.toLocaleString("en-US", {
                dateStyle: "medium",
                timeStyle: "short",
              })}
            </span>
          </div>
        </div>
      </CardHeader>
    </Card>
  );
}

function DataSourceNotes({ notes }: { notes: string[] }) {
  return (
    <Alert className="border-amber-500/40 bg-amber-500/5">
      <AlertTitle>Coverage note</AlertTitle>
      <AlertDescription>
        <ul className="mt-1 list-disc pl-5 text-sm">
          {notes.map((n, i) => (
            <li key={i}>{n}</li>
          ))}
        </ul>
      </AlertDescription>
    </Alert>
  );
}

function PerformanceHeadline({ report }: { report: ClientReport }) {
  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-base">Performance</CardTitle>
        <CardDescription>
          {report.campaigns_live} of {report.campaigns_total} campaigns
          currently active.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <dl className="grid grid-cols-2 gap-4 text-sm sm:grid-cols-3 lg:grid-cols-6">
          <Stat label="Impressions" value={formatInt(report.impressions)} />
          <Stat label="Clicks" value={formatInt(report.clicks)} />
          <Stat label="Conversions" value={formatInt(report.conversions)} />
          <Stat label="CTR" value={formatPercent(report.ctr)} />
          <Stat label="CPA" value={formatUsd(report.cpa_usd)} />
          <Stat label="Spend" value={formatUsd(report.spend_usd)} />
        </dl>
      </CardContent>
    </Card>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs uppercase text-muted-foreground">{label}</dt>
      <dd className="text-lg font-semibold tabular-nums">{value}</dd>
    </div>
  );
}

function SegmentHighlights({
  highlights,
}: {
  highlights: ClientSegmentHighlight[];
}) {
  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-base">
          <Sparkles className="size-4 text-primary" />
          Who your customers are
        </CardTitle>
        <CardDescription>
          Distinct customer segments active in this period, ranked by
          observed volume.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        {highlights.map((h, i) => (
          <div
            key={i}
            className="rounded-md border border-border/60 bg-background px-4 py-3"
          >
            <div className="flex items-center gap-2">
              <Badge variant="outline">{h.segment_label}</Badge>
            </div>
            <p className="mt-2 text-sm leading-relaxed">{h.observation}</p>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

function MessageObservations({
  observations,
}: {
  observations: ClientMessageObservation[];
}) {
  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-base">
          <TrendingUp className="size-4 text-primary" />
          What's working
        </CardTitle>
        <CardDescription>
          Observations from live campaign learning about which messaging
          approaches are landing with which customer segments.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        {observations.map((o, i) => (
          <p
            key={i}
            className="rounded-md border-l-2 border-primary/40 bg-muted/30 px-4 py-2 text-sm leading-relaxed"
          >
            {o.observation}
          </p>
        ))}
      </CardContent>
    </Card>
  );
}

function Recommendations({
  initial,
  advertiserId,
}: {
  initial: ClientRecommendation[];
  advertiserId: string;
}) {
  const [recs, setRecs] = useState<ClientRecommendation[]>(initial);

  const submit = async (
    rec: ClientRecommendation,
    kind: "acknowledge" | "decline",
    feedback_text: string | null,
    startedAtMs: number,
  ): Promise<void> => {
    const payload: ClientRecommendationDecisionRequest = {
      kind,
      advertiser_id: advertiserId,
      headline: rec.headline,
      rationale: rec.rationale,
      confirm_label: rec.confirm_label,
      projected_impact: rec.projected_impact,
      feedback_text,
      latency_ms: Math.max(0, Date.now() - startedAtMs),
    };
    const res = await fetch(
      `/api/client/recommendations/${encodeURIComponent(rec.id)}/decide`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      },
    );
    if (!res.ok) {
      const body = (await res.json().catch(() => null)) as
        | { error?: string }
        | null;
      throw new Error(
        body?.error ?? `Decide request failed (HTTP ${res.status})`,
      );
    }
    const data = (await res.json()) as ClientRecommendationDecisionResponse;
    setRecs((prev) =>
      prev.map((r) =>
        r.id === data.recommendation_id
          ? {
              ...r,
              status:
                data.kind === "acknowledge" ? "acknowledged" : "declined",
            }
          : r,
      ),
    );
  };

  const pending = useMemo(
    () => recs.filter((r) => r.status === "pending"),
    [recs],
  );

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-base">Recommended next moves</CardTitle>
        <CardDescription>
          Proposed actions based on what's working. Each will proceed on
          the stated timeline unless you decline. {pending.length}{" "}
          awaiting your review.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        {recs.map((r) => (
          <RecommendationCard key={r.id} rec={r} onSubmit={submit} />
        ))}
      </CardContent>
    </Card>
  );
}

type DeclineState =
  | { mode: "idle" }
  | { mode: "prompting"; startedAtMs: number; feedback: string }
  | { mode: "submitting" };

function RecommendationCard({
  rec,
  onSubmit,
}: {
  rec: ClientRecommendation;
  onSubmit: (
    rec: ClientRecommendation,
    kind: "acknowledge" | "decline",
    feedback_text: string | null,
    startedAtMs: number,
  ) => Promise<void>;
}) {
  const acknowledged = rec.status === "acknowledged";
  const declined = rec.status === "declined";
  const [busy, setBusy] = useState<false | "acknowledge" | "decline">(false);
  const [error, setError] = useState<string | null>(null);
  const [declineState, setDeclineState] = useState<DeclineState>({
    mode: "idle",
  });
  const mountedAtRef = useRef<number>(Date.now());

  const handleAcknowledge = async () => {
    setBusy("acknowledge");
    setError(null);
    try {
      await onSubmit(rec, "acknowledge", null, mountedAtRef.current);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setBusy(false);
    }
  };

  const handleOpenDeclinePrompt = () => {
    setDeclineState({
      mode: "prompting",
      startedAtMs: Date.now(),
      feedback: "",
    });
    setError(null);
  };

  const handleCancelDecline = () =>
    setDeclineState({ mode: "idle" });

  const handleSubmitDecline = async () => {
    if (declineState.mode !== "prompting") return;
    const { feedback, startedAtMs } = declineState;
    setDeclineState({ mode: "submitting" });
    setBusy("decline");
    setError(null);
    try {
      await onSubmit(
        rec,
        "decline",
        feedback.trim() ? feedback.trim() : null,
        startedAtMs,
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
      setDeclineState({
        mode: "prompting",
        startedAtMs,
        feedback,
      });
    } finally {
      setBusy(false);
    }
  };

  return (
    <div
      className={
        "rounded-md border px-4 py-3 " +
        (acknowledged
          ? "border-emerald-500/40 bg-emerald-500/5"
          : declined
            ? "border-rose-500/40 bg-rose-500/5 opacity-80"
            : "border-border/60 bg-background")
      }
    >
      <div className="flex flex-wrap items-start justify-between gap-2">
        <h3 className="text-sm font-semibold">{rec.headline}</h3>
        {acknowledged && (
          <Badge className="bg-emerald-500 text-white">
            <CheckCircle2 className="mr-1 size-3" />
            Acknowledged
          </Badge>
        )}
        {declined && <Badge variant="outline">Declined</Badge>}
      </div>
      <p className="mt-2 whitespace-pre-line text-sm leading-relaxed text-muted-foreground">
        {rec.rationale}
      </p>
      {rec.projected_impact && (
        <p className="mt-2 text-xs italic text-muted-foreground">
          {rec.projected_impact}
        </p>
      )}
      {error && (
        <p className="mt-2 text-xs text-rose-600 dark:text-rose-400">
          {error}
        </p>
      )}
      {rec.requires_acknowledgment &&
        !acknowledged &&
        !declined &&
        declineState.mode === "idle" && (
          <div className="mt-3 flex flex-wrap gap-2">
            <Button
              size="sm"
              onClick={handleAcknowledge}
              disabled={busy !== false}
            >
              {busy === "acknowledge" ? (
                <>
                  <Loader2 className="mr-1 size-3 animate-spin" />
                  Submitting…
                </>
              ) : (
                rec.confirm_label
              )}
            </Button>
            <Button
              size="sm"
              variant="outline"
              onClick={handleOpenDeclinePrompt}
              disabled={busy !== false}
            >
              Decline
            </Button>
          </div>
        )}
      {declineState.mode === "prompting" && (
        <div className="mt-3 flex flex-col gap-2 rounded-md border border-border/60 bg-muted/30 p-3">
          <label className="text-xs uppercase text-muted-foreground">
            Optional — what made you decline?
          </label>
          <Textarea
            value={declineState.feedback}
            onChange={(e) =>
              setDeclineState({
                ...declineState,
                feedback: e.target.value,
              })
            }
            placeholder="Context that makes this suggestion wrong right now — we'll use it to improve future recommendations."
            rows={3}
          />
          <div className="flex flex-wrap gap-2">
            <Button size="sm" onClick={handleSubmitDecline}>
              Submit decline
            </Button>
            <Button
              size="sm"
              variant="ghost"
              onClick={handleCancelDecline}
            >
              Cancel
            </Button>
          </div>
        </div>
      )}
      {declineState.mode === "submitting" && (
        <div className="mt-3 flex items-center gap-2 text-xs text-muted-foreground">
          <Loader2 className="size-3 animate-spin" />
          Recording decline…
        </div>
      )}
    </div>
  );
}

function MissingLabelsWarning({ missing }: { missing: string[] }) {
  return (
    <Alert
      variant="destructive"
      className="border-amber-500/40 bg-amber-500/5 text-amber-900 dark:text-amber-200"
    >
      <AlertTitle>
        Internal diagnostic — {missing.length} label{missing.length === 1 ? "" : "s"}{" "}
        missing
      </AlertTitle>
      <AlertDescription>
        <p className="text-sm">
          One or more internal entities were referenced in this report
          without an approved PublicLabel, so sections fell back. Author
          labels in Neo4j to restore full coverage.
        </p>
        <ul className="mt-2 list-disc pl-5 text-xs font-mono">
          {missing.map((m) => (
            <li key={m}>{m}</li>
          ))}
        </ul>
        <p className="mt-2 text-xs italic">
          This banner is internal-only and is suppressed for non-superadmin
          roles once role-scoping ships.
        </p>
      </AlertDescription>
    </Alert>
  );
}
