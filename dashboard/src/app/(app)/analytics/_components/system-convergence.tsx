"use client";

/**
 * System Convergence — Front-end B first-slice render.
 *
 * Internal superadmin view. Shows the cross-archetype state of
 * Enhancement #33's retargeting learning:
 *
 *   - top_converged: cells where rank_score (mean × confidence) is
 *     above threshold AND sample_count is above the floor. These are
 *     the "we know this works" entries.
 *
 *   - cross_archetype_patterns: mechanisms winning across multiple
 *     archetypes — platform-level signals.
 *
 *   - novel_findings: cells with accumulating but not-yet-validated
 *     evidence, each with an operator note classifying its state.
 *
 * This surface deliberately shows internal taxonomy (archetype /
 * barrier / mechanism slugs, α/β, sample counts). It is never rendered
 * to a client. A10 vocabulary discipline: the words here are
 * internal-appropriate ("convergence", "posterior", "novel finding",
 * "platform signal") and do not drift toward management-UI framing.
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
import type {
  AdvertiserSummary,
  ConvergedCell,
  CrossArchetypePattern,
  NovelFinding,
  SystemConvergenceResponse,
} from "@/lib/types";

function humanize(value: string): string {
  if (!value) return "—";
  return value
    .split("_")
    .map((w) => (w.length ? w[0].toUpperCase() + w.slice(1) : ""))
    .join(" ");
}

function pct(v: number): string {
  return `${(v * 100).toFixed(1)}%`;
}

export function SystemConvergenceView() {
  const [data, setData] = useState<SystemConvergenceResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const res = await fetch(
          "/api/analytics/system-convergence",
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
        const json = (await res.json()) as SystemConvergenceResponse;
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
        <AlertTitle>Could not load system convergence</AlertTitle>
        <AlertDescription>{error}</AlertDescription>
      </Alert>
    );
  }
  if (loading || !data) {
    return (
      <Card className="border-dashed">
        <CardContent className="py-6 text-center text-sm text-muted-foreground">
          Loading convergence state…
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <AdvertisersCard advertisers={data.advertisers} examined={data.cells_examined} />
      {data.cross_archetype_patterns.length > 0 && (
        <CrossArchetypePatternsCard patterns={data.cross_archetype_patterns} />
      )}
      <ConvergedCellsCard converged={data.top_converged} />
      {data.novel_findings.length > 0 && (
        <NovelFindingsCard novel={data.novel_findings} />
      )}
      {data.cells_examined === 0 && (
        <Card className="border-dashed">
          <CardHeader>
            <CardTitle>No accumulated evidence yet</CardTitle>
            <CardDescription>
              The retargeting cascade has not recorded enough posterior
              updates for any (archetype, barrier, mechanism) cell.
              Convergence state will populate as outcomes flow through
              the learning loop.
            </CardDescription>
          </CardHeader>
        </Card>
      )}
    </div>
  );
}

function AdvertisersCard({
  advertisers,
  examined,
}: {
  advertisers: AdvertiserSummary[];
  examined: number;
}) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base">Advertiser coverage</CardTitle>
        <CardDescription>
          Posterior cells examined across all active advertisers.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <dl className="grid grid-cols-2 gap-4 text-sm md:grid-cols-4">
          <Stat label="Advertisers" value={advertisers.length.toString()} />
          <Stat label="Cells examined" value={examined.toString()} />
          <Stat
            label="Total observations"
            value={advertisers
              .reduce((a, v) => a + v.total_observations, 0)
              .toString()}
          />
          <Stat
            label="Converged cells"
            value={advertisers
              .reduce((a, v) => a + v.top_converged_cell_count, 0)
              .toString()}
          />
        </dl>
      </CardContent>
    </Card>
  );
}

function ConvergedCellsCard({ converged }: { converged: ConvergedCell[] }) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base">Converged cells</CardTitle>
        <CardDescription>
          (archetype × barrier × mechanism) cells where rank score
          (mean × confidence) crossed threshold and sample count cleared
          the floor. Ranked by rank score descending.
        </CardDescription>
      </CardHeader>
      <CardContent>
        {converged.length === 0 ? (
          <p className="py-4 text-sm text-muted-foreground">
            No cells have crossed the convergence threshold yet.
          </p>
        ) : (
          <div className="flex flex-col gap-1">
            <div className="grid grid-cols-[1fr_1fr_1fr_4rem_4rem_4rem_4rem] items-center gap-2 border-b border-border/60 px-2 pb-1 text-[10px] uppercase text-muted-foreground">
              <span>Archetype</span>
              <span>Barrier</span>
              <span>Mechanism</span>
              <span className="text-right">Mean</span>
              <span className="text-right">Conf</span>
              <span className="text-right">N</span>
              <span className="text-right">Rank</span>
            </div>
            {converged.map((c) => (
              <div
                key={`${c.archetype}:${c.barrier}:${c.mechanism}`}
                className="grid grid-cols-[1fr_1fr_1fr_4rem_4rem_4rem_4rem] items-center gap-2 rounded px-2 py-1 text-sm hover:bg-muted/50"
              >
                <span className="truncate">{humanize(c.archetype)}</span>
                <span className="truncate text-muted-foreground">
                  {humanize(c.barrier)}
                </span>
                <span className="truncate font-medium">
                  {humanize(c.mechanism)}
                </span>
                <span className="text-right font-mono tabular-nums">
                  {pct(c.mean)}
                </span>
                <span className="text-right font-mono tabular-nums text-muted-foreground">
                  {pct(c.confidence)}
                </span>
                <span className="text-right font-mono tabular-nums text-muted-foreground">
                  {c.sample_count}
                </span>
                <span className="text-right font-mono tabular-nums font-semibold">
                  {c.rank_score.toFixed(3)}
                </span>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function CrossArchetypePatternsCard({
  patterns,
}: {
  patterns: CrossArchetypePattern[];
}) {
  return (
    <Card className="border-l-4 border-l-emerald-500">
      <CardHeader className="pb-2">
        <CardTitle className="text-base">
          Cross-archetype platform signals
        </CardTitle>
        <CardDescription>
          Mechanisms winning across multiple archetypes. Stronger
          priors for new campaigns than any single-archetype converged
          cell.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-2">
        {patterns.map((p, i) => (
          <div
            key={`${p.mechanism}:${i}`}
            className="rounded-md border border-border/60 bg-muted/20 px-3 py-2 text-sm"
          >
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span className="font-semibold">
                {humanize(p.mechanism)}
              </span>
              <div className="flex items-center gap-3 font-mono text-xs text-muted-foreground">
                <span>mean {pct(p.mean_across_archetypes)}</span>
                <span>n {p.total_sample_count}</span>
                {p.barrier && <span>on {humanize(p.barrier)}</span>}
              </div>
            </div>
            <div className="mt-1 flex flex-wrap gap-1">
              {p.archetypes.map((a) => (
                <Badge key={a} variant="outline" className="text-[10px]">
                  {humanize(a)}
                </Badge>
              ))}
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

function NovelFindingsCard({ novel }: { novel: NovelFinding[] }) {
  return (
    <Card className="border-l-4 border-l-amber-500">
      <CardHeader className="pb-2">
        <CardTitle className="text-base">Novel findings</CardTitle>
        <CardDescription>
          Cells with accumulating but not-yet-validated evidence. Each
          note classifies what the system sees — useful for deciding
          whether to push more impressions through or suppress.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-2">
        {novel.map((n) => (
          <div
            key={`${n.archetype}:${n.barrier}:${n.mechanism}`}
            className="rounded-md border border-border/60 px-3 py-2 text-sm"
          >
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span className="font-medium">
                {humanize(n.archetype)} ·{" "}
                <span className="text-muted-foreground">
                  {humanize(n.barrier)}
                </span>{" "}
                →{" "}
                <span className="font-semibold">
                  {humanize(n.mechanism)}
                </span>
              </span>
              <div className="flex items-center gap-3 font-mono text-xs text-muted-foreground">
                <span>mean {pct(n.mean)}</span>
                <span>conf {pct(n.confidence)}</span>
                <span>n {n.sample_count}</span>
              </div>
            </div>
            <p className="mt-1 text-xs italic text-muted-foreground">
              {n.note}
            </p>
          </div>
        ))}
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
