"use client";

/**
 * Q.2.B — per-cohort outcome correlation panel.
 *
 * Cohorts classified as affiliative / transactional / mixed via F.2's
 * COMPENSATORY_MECHANISM_INDICATORS + COMPENSATORY_TRANSACTIONAL_NEGATIVES.
 * Confidence label maps to F.2's three-bucket calibration
 * (high_confidence / partial_evidence / uninformative).
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
import type {
  CohortConfidence,
  MechanismOrientation,
  PerCohortOutcomeCorrelationResponse,
} from "@/lib/types";

function pct(v: number): string {
  return `${(v * 100).toFixed(1)}%`;
}

const ORIENTATION_VARIANT: Record<
  MechanismOrientation,
  { label: string; className: string }
> = {
  affiliative: {
    label: "Affiliative",
    className:
      "border-blue-300 bg-blue-100 text-blue-900 dark:border-blue-800 dark:bg-blue-950/40 dark:text-blue-200",
  },
  transactional: {
    label: "Transactional",
    className:
      "border-purple-300 bg-purple-100 text-purple-900 dark:border-purple-800 dark:bg-purple-950/40 dark:text-purple-200",
  },
  mixed: {
    label: "Mixed",
    className: "border-border bg-muted text-muted-foreground",
  },
};

const CONFIDENCE_LABEL: Record<CohortConfidence, string> = {
  high_confidence: "High confidence",
  partial_evidence: "Partial evidence",
  uninformative: "Uninformative",
};

export function PerCohortOutcomeCorrelationPanel({
  days = 30,
}: {
  days?: number;
}) {
  const [data, setData] =
    useState<PerCohortOutcomeCorrelationResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const res = await fetch(
          `/api/analytics/per-cohort-outcome-correlation?days=${days}`,
          { cache: "no-store" },
        );
        if (!res.ok) {
          const body = (await res.json().catch(() => null)) as
            | { error?: string }
            | null;
          throw new Error(body?.error ?? `Request failed (HTTP ${res.status})`);
        }
        const json =
          (await res.json()) as PerCohortOutcomeCorrelationResponse;
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
        <AlertTitle>Could not load per-cohort outcome correlation</AlertTitle>
        <AlertDescription>{error}</AlertDescription>
      </Alert>
    );
  }
  if (loading || !data) {
    return (
      <Card className="border-dashed">
        <CardContent className="py-6 text-center text-sm text-muted-foreground">
          Loading per-cohort outcome correlation…
        </CardContent>
      </Card>
    );
  }

  if (data.data_source_state === "empty") {
    return (
      <EmptyState
        title="No cohorts populated"
        description="UserCohort nodes haven't been written to Neo4j yet. Cohort discovery runs offline; this panel populates after the first F.2 cohort-discovery batch lands."
      />
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-end">
        <DataSourceStateBadge state={data.data_source_state} />
      </div>
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">Cohorts × outcome</CardTitle>
          <CardDescription>
            Mechanism orientation per F.2 vocabulary. Compensatory flag
            indicates affiliative dominance + transactional weakness
            simultaneously satisfied per Mead 2010 / Loh 2021.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {data.cohorts.length === 0 ? (
            <p className="py-4 text-sm text-muted-foreground">
              No cohorts found.
            </p>
          ) : (
            <div className="flex flex-col gap-2">
              {data.cohorts.map((c) => {
                const v = ORIENTATION_VARIANT[c.mechanism_orientation];
                return (
                  <div
                    key={c.cohort_id}
                    className="rounded-md border border-border/60 px-3 py-2 text-sm"
                  >
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <span className="font-mono text-xs">{c.cohort_id}</span>
                      <div className="flex items-center gap-2">
                        <Badge
                          variant="outline"
                          className={`text-[10px] ${v.className}`}
                        >
                          {v.label}
                        </Badge>
                        {c.compensatory_flag && (
                          <Badge variant="default" className="text-[10px]">
                            compensatory
                          </Badge>
                        )}
                        <Badge variant="outline" className="text-[10px]">
                          {CONFIDENCE_LABEL[c.confidence_label]}
                        </Badge>
                      </div>
                    </div>
                    <div className="mt-1 flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
                      <span>
                        dominant:{" "}
                        <span className="font-mono">
                          {c.dominant_mechanism}
                        </span>
                      </span>
                      <span>n = {c.sample_size.toLocaleString()}</span>
                      <span>conv {pct(c.conversion_rate)}</span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
