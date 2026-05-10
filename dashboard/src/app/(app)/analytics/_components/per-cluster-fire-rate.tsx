"use client";

/**
 * Q.2.B — per-cluster fire-rate panel.
 *
 * Two surfaces:
 *   - Cluster impression count + share-of-total (Becca's 5-creative pool)
 *   - Predicate fire rate with dormant flagging (M.0 substrate firing)
 *
 * Empty-state when no traces in window. Partial-state when traces
 * present but no predicate fires (chain_of_reasoning empty).
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
import type { PerClusterFireRateResponse } from "@/lib/types";

function pct(v: number): string {
  return `${(v * 100).toFixed(1)}%`;
}

export function PerClusterFireRatePanel({ days = 7 }: { days?: number }) {
  const [data, setData] = useState<PerClusterFireRateResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const res = await fetch(
          `/api/analytics/per-cluster-fire-rate?days=${days}`,
          { cache: "no-store" },
        );
        if (!res.ok) {
          const body = (await res.json().catch(() => null)) as
            | { error?: string }
            | null;
          throw new Error(body?.error ?? `Request failed (HTTP ${res.status})`);
        }
        const json = (await res.json()) as PerClusterFireRateResponse;
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
        <AlertTitle>Could not load per-cluster fire rate</AlertTitle>
        <AlertDescription>{error}</AlertDescription>
      </Alert>
    );
  }
  if (loading || !data) {
    return (
      <Card className="border-dashed">
        <CardContent className="py-6 text-center text-sm text-muted-foreground">
          Loading per-cluster fire rate…
        </CardContent>
      </Card>
    );
  }

  if (data.data_source_state === "empty") {
    return (
      <EmptyState
        title="No traces in window"
        description={`No decision traces archived for the last ${days} day${days === 1 ? "" : "s"}. This panel populates once the cascade emits traces and the drain task lands them in Neo4j.`}
      />
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <div className="text-xs text-muted-foreground">
          {data.total_impressions.toLocaleString()} impressions ·{" "}
          window {new Date(data.window_start).toLocaleDateString()} →{" "}
          {new Date(data.window_end).toLocaleDateString()}
        </div>
        <DataSourceStateBadge state={data.data_source_state} />
      </div>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">Cluster impression share</CardTitle>
          <CardDescription>
            Each cluster aggregates creative variants by stripping the
            <span className="font-mono"> _N </span>suffix. Shares sum to 100%.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {data.clusters.length === 0 ? (
            <p className="py-4 text-sm text-muted-foreground">
              No clusters found in this window.
            </p>
          ) : (
            <div className="flex flex-col gap-1">
              <div className="grid grid-cols-[1fr_6rem_6rem] items-center gap-2 border-b border-border/60 px-2 pb-1 text-[10px] uppercase text-muted-foreground">
                <span>Cluster</span>
                <span className="text-right">Impressions</span>
                <span className="text-right">Share</span>
              </div>
              {data.clusters.map((c) => (
                <div
                  key={c.cluster_id}
                  className="grid grid-cols-[1fr_6rem_6rem] items-center gap-2 rounded px-2 py-1 text-sm hover:bg-muted/50"
                >
                  <span className="truncate font-medium">{c.cluster_id}</span>
                  <span className="text-right font-mono tabular-nums">
                    {c.impression_count.toLocaleString()}
                  </span>
                  <span className="text-right font-mono tabular-nums text-muted-foreground">
                    {pct(c.share_of_total)}
                  </span>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">
            Predicate fire rates
            {data.data_source_state === "partial" ? (
              <Badge variant="outline" className="ml-2 text-[10px] uppercase">
                substrate dormant
              </Badge>
            ) : null}
          </CardTitle>
          <CardDescription>
            Per-predicate firing rate across all impressions in window. Dormant
            predicates either haven&rsquo;t encountered triggering inputs or
            their producer isn&rsquo;t wired into the bid path yet.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col gap-1">
            <div className="grid grid-cols-[1fr_5rem_5rem_5rem] items-center gap-2 border-b border-border/60 px-2 pb-1 text-[10px] uppercase text-muted-foreground">
              <span>Predicate</span>
              <span className="text-right">Fires</span>
              <span className="text-right">Rate</span>
              <span className="text-right">State</span>
            </div>
            {data.predicates.map((p) => (
              <div
                key={p.predicate_name}
                className="grid grid-cols-[1fr_5rem_5rem_5rem] items-center gap-2 rounded px-2 py-1 text-sm hover:bg-muted/50"
              >
                <span className="truncate font-mono text-xs">
                  {p.predicate_name}
                </span>
                <span className="text-right font-mono tabular-nums">
                  {p.fire_count.toLocaleString()}
                </span>
                <span className="text-right font-mono tabular-nums text-muted-foreground">
                  {pct(p.fire_rate)}
                </span>
                <span className="text-right">
                  {p.dormant ? (
                    <Badge variant="outline" className="text-[10px]">
                      dormant
                    </Badge>
                  ) : (
                    <Badge variant="default" className="text-[10px]">
                      firing
                    </Badge>
                  )}
                </span>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
