"use client";

/**
 * Q.2.B — decision-trace detail view.
 *
 * Renders one DecisionTraceDetailResponse with all schema-gap-aware
 * fields gracefully nullable. Privacy guard: buyer_id is never rendered
 * in raw form — only the anonymized SHA-256 prefix from Q.2.A.
 */

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { DataSourceStateBadge } from "@/components/data-source-state-badge";
import type { DecisionTraceDetailResponse } from "@/lib/types";

function nullableText(v: string | null | undefined): string {
  return v && v.length > 0 ? v : "—";
}

export function DecisionTraceDetailView({
  trace,
}: {
  trace: DecisionTraceDetailResponse;
}) {
  return (
    <div className="flex flex-col gap-4">
      <Card>
        <CardHeader className="pb-2">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <CardTitle className="text-base">
                Trace {trace.impression_id}
              </CardTitle>
              <CardDescription>
                {new Date(trace.timestamp).toLocaleString()}
              </CardDescription>
            </div>
            <DataSourceStateBadge state={trace.data_source_state} />
          </div>
        </CardHeader>
        <CardContent className="grid grid-cols-2 gap-3 text-sm md:grid-cols-3">
          <Field label="Buyer (anonymized)" value={trace.buyer_id_anonymized} mono />
          <Field label="Cell ID" value={nullableText(trace.cell_id)} />
          <Field label="Cluster" value={nullableText(trace.cluster_id)} />
          <Field label="Archetype" value={nullableText(trace.archetype)} />
          <Field label="Cohort" value={nullableText(trace.cohort_id)} />
          <Field label="Posture class" value={nullableText(trace.posture_class)} />
          <Field label="Journey stage" value={nullableText(trace.journey_stage)} />
          <Field label="Regulatory focus" value={nullableText(trace.regulatory_focus)} />
          <Field
            label="Chosen creative"
            value={nullableText(trace.chosen_creative_id)}
            mono
          />
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">Predicate firings</CardTitle>
          <CardDescription>
            Per-predicate fired/not-fired with contribution score when
            available. Threshold is not carried on the trace today —
            shown as &mdash;.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {trace.predicates_fired.length === 0 ? (
            <p className="py-4 text-sm text-muted-foreground">
              No predicate-firing data on this trace.
            </p>
          ) : (
            <div className="flex flex-col gap-1">
              <div className="grid grid-cols-[1fr_5rem_5rem_5rem] items-center gap-2 border-b border-border/60 px-2 pb-1 text-[10px] uppercase text-muted-foreground">
                <span>Predicate</span>
                <span className="text-right">Fired</span>
                <span className="text-right">Score</span>
                <span className="text-right">Threshold</span>
              </div>
              {trace.predicates_fired.map((p) => (
                <div
                  key={p.predicate_name}
                  className="grid grid-cols-[1fr_5rem_5rem_5rem] items-center gap-2 rounded px-2 py-1 text-sm hover:bg-muted/50"
                >
                  <span className="truncate font-mono text-xs">
                    {p.predicate_name}
                  </span>
                  <span className="text-right">
                    {p.fired ? (
                      <Badge variant="default" className="text-[10px]">
                        yes
                      </Badge>
                    ) : (
                      <Badge variant="outline" className="text-[10px]">
                        no
                      </Badge>
                    )}
                  </span>
                  <span className="text-right font-mono tabular-nums text-muted-foreground">
                    {p.score == null ? "—" : p.score.toFixed(3)}
                  </span>
                  <span className="text-right font-mono tabular-nums text-muted-foreground">
                    {p.threshold == null ? "—" : p.threshold.toFixed(3)}
                  </span>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">Modulations applied</CardTitle>
          <CardDescription>
            Per-alternative score-before vs score-after for each candidate
            considered at decision time. Source identifies the alternative.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {trace.modulations_applied.length === 0 ? (
            <p className="py-4 text-sm text-muted-foreground">
              No modulation data on this trace.
            </p>
          ) : (
            <div className="flex flex-col gap-1">
              <div className="grid grid-cols-[1fr_6rem_6rem_2fr] items-center gap-2 border-b border-border/60 px-2 pb-1 text-[10px] uppercase text-muted-foreground">
                <span>Mechanism</span>
                <span className="text-right">Before</span>
                <span className="text-right">After</span>
                <span>Source</span>
              </div>
              {trace.modulations_applied.map((m, i) => (
                <div
                  key={`${m.mechanism}-${i}`}
                  className="grid grid-cols-[1fr_6rem_6rem_2fr] items-center gap-2 rounded px-2 py-1 text-sm hover:bg-muted/50"
                >
                  <span className="truncate font-mono text-xs">
                    {m.mechanism}
                  </span>
                  <span className="text-right font-mono tabular-nums">
                    {m.score_before.toFixed(3)}
                  </span>
                  <span className="text-right font-mono tabular-nums">
                    {m.score_after.toFixed(3)}
                  </span>
                  <span className="truncate text-xs text-muted-foreground">
                    {m.source}
                  </span>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {trace.why_explanation ? (
        <>
          <Separator />
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base">Why explanation</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm">{trace.why_explanation}</p>
            </CardContent>
          </Card>
        </>
      ) : null}
    </div>
  );
}

function Field({
  label,
  value,
  mono,
}: {
  label: string;
  value: string;
  mono?: boolean;
}) {
  return (
    <div>
      <div className="text-[10px] uppercase text-muted-foreground">{label}</div>
      <div className={`text-sm ${mono ? "font-mono" : ""}`}>{value}</div>
    </div>
  );
}
