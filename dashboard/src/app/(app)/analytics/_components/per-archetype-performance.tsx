"use client";

/**
 * Q.2.B — per-archetype performance panel.
 *
 * Renders 8-archetype × impression count + conversion rate +
 * cold-start share. Pre-pilot conversion_rate is 0.0 across the board
 * (ConversionEdge join not wired); panel surfaces this honestly via
 * data_source_state.
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
import { EmptyState } from "@/components/empty-state";
import { DataSourceStateBadge } from "@/components/data-source-state-badge";
import type { PerArchetypePerformanceResponse } from "@/lib/types";

function pct(v: number): string {
  return `${(v * 100).toFixed(1)}%`;
}

function humanize(s: string): string {
  return s
    .split("_")
    .map((w) => (w.length ? w[0].toUpperCase() + w.slice(1) : ""))
    .join(" ");
}

export function PerArchetypePerformancePanel({ days = 30 }: { days?: number }) {
  const [data, setData] = useState<PerArchetypePerformanceResponse | null>(
    null,
  );
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const res = await fetch(
          `/api/analytics/per-archetype-performance?days=${days}`,
          { cache: "no-store" },
        );
        if (!res.ok) {
          const body = (await res.json().catch(() => null)) as
            | { error?: string }
            | null;
          throw new Error(body?.error ?? `Request failed (HTTP ${res.status})`);
        }
        const json = (await res.json()) as PerArchetypePerformanceResponse;
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
        <AlertTitle>Could not load per-archetype performance</AlertTitle>
        <AlertDescription>{error}</AlertDescription>
      </Alert>
    );
  }
  if (loading || !data) {
    return (
      <Card className="border-dashed">
        <CardContent className="py-6 text-center text-sm text-muted-foreground">
          Loading per-archetype performance…
        </CardContent>
      </Card>
    );
  }

  if (data.data_source_state === "empty") {
    return (
      <EmptyState
        title="No traces in window"
        description={`No decision traces archived for the last ${days} days. This panel populates once cascade traces flow.`}
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
          <CardTitle className="text-base">
            Per-archetype performance distribution
          </CardTitle>
          <CardDescription>
            Conversion attribution requires <span className="font-mono">ConversionEdge</span>{" "}
            joins; pre-pilot rates show 0% across the board (data_source_state
            reports partial). Cold-start share tracks how often the archetype
            defaulted to <span className="font-mono">PRAGMATIST</span>.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {data.archetypes.length === 0 ? (
            <p className="py-4 text-sm text-muted-foreground">
              No archetype lookups available in this window. The archetype
              hook (<span className="font-mono">_archetype_lookup_for_user</span>)
              returns None until BuyerUncertaintyProfile join is wired.
            </p>
          ) : (
            <div className="flex flex-col gap-1">
              <div className="grid grid-cols-[1fr_5rem_5rem_5rem_5rem] items-center gap-2 border-b border-border/60 px-2 pb-1 text-[10px] uppercase text-muted-foreground">
                <span>Archetype</span>
                <span className="text-right">Impr</span>
                <span className="text-right">Conv</span>
                <span className="text-right">Conv%</span>
                <span className="text-right">Cold%</span>
              </div>
              {data.archetypes.map((a) => (
                <div
                  key={a.archetype_id}
                  className="grid grid-cols-[1fr_5rem_5rem_5rem_5rem] items-center gap-2 rounded px-2 py-1 text-sm hover:bg-muted/50"
                >
                  <span className="truncate font-medium">
                    {humanize(a.archetype_id)}
                  </span>
                  <span className="text-right font-mono tabular-nums">
                    {a.impression_count.toLocaleString()}
                  </span>
                  <span className="text-right font-mono tabular-nums">
                    {a.conversion_count.toLocaleString()}
                  </span>
                  <span className="text-right font-mono tabular-nums text-muted-foreground">
                    {pct(a.conversion_rate)}
                  </span>
                  <span className="text-right font-mono tabular-nums text-muted-foreground">
                    {pct(a.cold_start_share)}
                  </span>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
