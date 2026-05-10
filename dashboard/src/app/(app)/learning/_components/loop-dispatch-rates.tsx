"use client";

/**
 * Q.2.B — loop dispatch rates panel.
 *
 * Renders the 14 OutcomeHandler dispatch methods × dispatch count +
 * last-dispatch timestamp. Dormant methods (count == 0) are visually
 * distinct so the operator can see at a glance which sub-update paths
 * have NOT fired since process start.
 */

import { useEffect, useState } from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/empty-state";
import { DataSourceStateBadge } from "@/components/data-source-state-badge";
import type { LoopDispatchRatesResponse } from "@/lib/types";

function formatRelative(iso: string | null): string {
  if (!iso) return "—";
  try {
    const d = new Date(iso);
    return d.toLocaleString();
  } catch {
    return "—";
  }
}

export function LoopDispatchRatesPanel({ days = 7 }: { days?: number }) {
  const [data, setData] = useState<LoopDispatchRatesResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const res = await fetch(
          `/api/learning/loop-dispatch-rates?days=${days}`,
          { cache: "no-store" },
        );
        if (!res.ok) {
          const body = (await res.json().catch(() => null)) as
            | { error?: string }
            | null;
          throw new Error(body?.error ?? `Request failed (HTTP ${res.status})`);
        }
        const json = (await res.json()) as LoopDispatchRatesResponse;
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
  }, [days]);

  if (error) {
    return (
      <Alert variant="destructive">
        <AlertTitle>Could not load loop dispatch rates</AlertTitle>
        <AlertDescription>{error}</AlertDescription>
      </Alert>
    );
  }
  if (loading || !data) {
    return (
      <Card className="border-dashed">
        <CardContent className="py-6 text-center text-sm text-muted-foreground">
          Loading loop dispatch rates…
        </CardContent>
      </Card>
    );
  }

  if (data.data_source_state === "empty") {
    return (
      <EmptyState
        title="No outcomes processed"
        description="OutcomeHandler hasn't been invoked since process start. Loop dispatch rates populate as outcomes flow through the learning loop."
      />
    );
  }

  const totalDispatches = data.dispatch_methods.reduce(
    (a, m) => a + m.dispatch_count,
    0,
  );

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <div className="text-xs text-muted-foreground">
          {data.total_outcomes_processed.toLocaleString()} outcomes ·{" "}
          {totalDispatches.toLocaleString()} sub-update dispatches across{" "}
          {data.dispatch_methods.length} methods
        </div>
        <DataSourceStateBadge state={data.data_source_state} />
      </div>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">
            OutcomeHandler dispatch breakdown
          </CardTitle>
          <CardDescription>
            Each row is one of the 14 sub-update methods invoked by{" "}
            <span className="font-mono">process_outcome</span>. Dormant
            methods either gate on metadata that hasn&rsquo;t arrived
            (e.g., <span className="font-mono">_update_dsp_learning</span>{" "}
            requires <span className="font-mono">source==&quot;dsp_impression&quot;</span>) or
            their feeding path isn&rsquo;t wired in this environment.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col gap-1">
            <div className="grid grid-cols-[1fr_5rem_5rem_1fr] items-center gap-2 border-b border-border/60 px-2 pb-1 text-[10px] uppercase text-muted-foreground">
              <span>Method</span>
              <span className="text-right">Count</span>
              <span className="text-right">State</span>
              <span>Last dispatch</span>
            </div>
            {data.dispatch_methods.map((m) => (
              <div
                key={m.method_name}
                className={`grid grid-cols-[1fr_5rem_5rem_1fr] items-center gap-2 rounded px-2 py-1 text-sm ${
                  m.dormant ? "opacity-60" : "hover:bg-muted/50"
                }`}
              >
                <span className="truncate font-mono text-xs">
                  {m.method_name}
                </span>
                <span className="text-right font-mono tabular-nums">
                  {m.dispatch_count.toLocaleString()}
                </span>
                <span className="text-right">
                  {m.dormant ? (
                    <Badge variant="outline" className="text-[10px]">
                      dormant
                    </Badge>
                  ) : (
                    <Badge variant="default" className="text-[10px]">
                      firing
                    </Badge>
                  )}
                </span>
                <span className="truncate text-xs text-muted-foreground">
                  {formatRelative(m.last_dispatch_at)}
                </span>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
