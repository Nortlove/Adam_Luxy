"use client";

/**
 * Q.2.B — cohort discovery panel for /discovery surface.
 *
 * Reuses Q.2.A's per-cohort-outcome-correlation endpoint with
 * /discovery framing: emphasizes which cohorts F.2 has detected and
 * which compensatory pattern flagged. Tabular drill-down per cohort
 * showing dominant_mechanism, mechanism orientation, compensatory
 * flag, sample size, confidence label.
 *
 * Different framing than the /analytics panel: /discovery is the
 * operator's window into what the system has DISCOVERED about user
 * cohorts; /analytics is the performance surface.
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

const ORIENTATION_LABEL: Record<MechanismOrientation, string> = {
  affiliative: "Affiliative",
  transactional: "Transactional",
  mixed: "Mixed",
};

const CONFIDENCE_LABEL: Record<CohortConfidence, string> = {
  high_confidence: "High",
  partial_evidence: "Partial",
  uninformative: "Uninformative",
};

export function CohortDiscoveryPanel() {
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
          "/api/analytics/per-cohort-outcome-correlation",
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
  }, []);

  if (error) {
    return (
      <Alert variant="destructive">
        <AlertTitle>Could not load cohort discovery</AlertTitle>
        <AlertDescription>{error}</AlertDescription>
      </Alert>
    );
  }
  if (loading || !data) {
    return (
      <Card className="border-dashed">
        <CardContent className="py-6 text-center text-sm text-muted-foreground">
          Loading cohort discovery state…
        </CardContent>
      </Card>
    );
  }

  if (data.data_source_state === "empty") {
    return (
      <EmptyState
        title="No cohorts discovered yet"
        description="F.2's compensatory-detection pipeline runs offline against UserCohort nodes. This panel populates after the first batch lands cohort assignments in Neo4j."
      />
    );
  }

  const compensatoryCount = data.cohorts.filter((c) => c.compensatory_flag)
    .length;

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <div className="flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
          <span>
            {data.cohorts.length} cohort
            {data.cohorts.length === 1 ? "" : "s"} discovered
          </span>
          <span>· {compensatoryCount} compensatory-flagged</span>
        </div>
        <DataSourceStateBadge state={data.data_source_state} />
      </div>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">Discovered cohorts</CardTitle>
          <CardDescription>
            Each cohort emerged from Louvain community detection on the
            BRAND_RESPONDS_TO graph. Mechanism orientation classifies the
            cohort&rsquo;s dominant Cialdini-mechanism profile against
            F.2&rsquo;s compensatory-consumption indicators.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {data.cohorts.length === 0 ? (
            <p className="py-4 text-sm text-muted-foreground">
              No cohorts in current state.
            </p>
          ) : (
            <div className="flex flex-col gap-1">
              <div className="grid grid-cols-[1fr_1fr_5rem_5rem_5rem_5rem] items-center gap-2 border-b border-border/60 px-2 pb-1 text-[10px] uppercase text-muted-foreground">
                <span>Cohort</span>
                <span>Dominant mechanism</span>
                <span className="text-right">Orient</span>
                <span className="text-right">N</span>
                <span className="text-right">Comp</span>
                <span className="text-right">Conf</span>
              </div>
              {data.cohorts.map((c) => (
                <div
                  key={c.cohort_id}
                  className="grid grid-cols-[1fr_1fr_5rem_5rem_5rem_5rem] items-center gap-2 rounded px-2 py-1 text-sm hover:bg-muted/50"
                >
                  <span className="truncate font-mono text-xs">
                    {c.cohort_id}
                  </span>
                  <span className="truncate font-mono text-xs">
                    {c.dominant_mechanism}
                  </span>
                  <span className="text-right">
                    <Badge variant="outline" className="text-[10px]">
                      {ORIENTATION_LABEL[c.mechanism_orientation]}
                    </Badge>
                  </span>
                  <span className="text-right font-mono tabular-nums">
                    {c.sample_size.toLocaleString()}
                  </span>
                  <span className="text-right">
                    {c.compensatory_flag ? (
                      <Badge variant="default" className="text-[10px]">
                        yes
                      </Badge>
                    ) : (
                      <span className="text-muted-foreground">—</span>
                    )}
                  </span>
                  <span className="text-right text-xs text-muted-foreground">
                    {CONFIDENCE_LABEL[c.confidence_label]}
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
