"use client";

/**
 * Mechanism Effectiveness view — renders what Enhancement #33's 5-level
 * hierarchical retargeting learning has accumulated.
 *
 * When an archetype is selected alone, shows barrier prevalence for that
 * archetype. When archetype + barrier are both selected, shows the Beta
 * posterior on every therapeutic mechanism for that cell — mean efficacy,
 * credible-interval width, sample count.
 *
 * Client component because the user picks archetype and barrier
 * interactively; each selection drives a fresh fetch through the Next.js
 * proxy route at `/api/learning/mechanism-effectiveness` (server-side
 * bearer token is injected there).
 *
 * Discipline: not a Likert disguise (A7) — the mechanism posterior is a
 * real probability with real width. The UI renders both the mean and the
 * sample count explicitly so low-N estimates don't read as equally
 * trustworthy as high-N estimates.
 */

import { useEffect, useMemo, useState } from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  BARRIER_CATEGORIES,
  LUXY_ARCHETYPES,
  type MechanismEffectivenessResponse,
  type MechanismPosterior,
} from "@/lib/types";

const DEFAULT_ARCHETYPE = "careful_truster";

function humanize(value: string): string {
  return value
    .split("_")
    .map((w) => (w.length ? w[0].toUpperCase() + w.slice(1) : ""))
    .join(" ");
}

export function MechanismEffectivenessView() {
  const [archetype, setArchetype] = useState<string>(DEFAULT_ARCHETYPE);
  const [barrier, setBarrier] = useState<string>("");
  const [data, setData] = useState<MechanismEffectivenessResponse | null>(
    null,
  );
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(false);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const params = new URLSearchParams();
        if (archetype) params.set("archetype_id", archetype);
        if (barrier) params.set("barrier", barrier);
        const res = await fetch(
          `/api/learning/mechanism-effectiveness?${params.toString()}`,
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
        const json = (await res.json()) as MechanismEffectivenessResponse;
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
  }, [archetype, barrier]);

  return (
    <div className="flex flex-col gap-4">
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Learning lens</CardTitle>
          <CardDescription>
            Pick an archetype to see which barriers are prevalent for that
            audience. Add a barrier to see the Beta posterior on every
            therapeutic mechanism the system has tried for that cell —
            mean efficacy, credible-interval width, and how many
            observations back the estimate.
          </CardDescription>
        </CardHeader>
        <CardContent className="grid grid-cols-1 gap-3 md:grid-cols-2">
          <div className="flex flex-col gap-1">
            <label className="text-xs uppercase text-muted-foreground">
              Archetype
            </label>
            <Select
              value={archetype}
              onValueChange={(v) => setArchetype(v ?? DEFAULT_ARCHETYPE)}
            >
              <SelectTrigger className="w-full">
                <SelectValue placeholder="Select archetype" />
              </SelectTrigger>
              <SelectContent>
                {LUXY_ARCHETYPES.map((a) => (
                  <SelectItem key={a} value={a}>
                    {humanize(a)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-xs uppercase text-muted-foreground">
              Barrier (optional)
            </label>
            <Select
              value={barrier || "__none__"}
              onValueChange={(v) =>
                setBarrier(!v || v === "__none__" ? "" : v)
              }
            >
              <SelectTrigger className="w-full">
                <SelectValue placeholder="All barriers (show prevalence)" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="__none__">
                  All barriers — show prevalence
                </SelectItem>
                {BARRIER_CATEGORIES.map((b) => (
                  <SelectItem key={b} value={b}>
                    {humanize(b)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {error && (
        <Alert variant="destructive">
          <AlertTitle>Could not load posteriors</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {loading && !error && (
        <Card className="border-dashed">
          <CardContent className="py-6 text-center text-sm text-muted-foreground">
            Loading posteriors…
          </CardContent>
        </Card>
      )}

      {data && !loading && !error && (
        <MechanismResults data={data} />
      )}
    </div>
  );
}

function MechanismResults({
  data,
}: {
  data: MechanismEffectivenessResponse;
}) {
  const hasBarrierPrevalence =
    data.barrier_prevalence &&
    Object.keys(data.barrier_prevalence).length > 0;
  const hasPosteriors =
    data.posteriors && Object.keys(data.posteriors).length > 0;

  return (
    <div className="flex flex-col gap-4">
      <GlobalStatsCard data={data} />
      {hasBarrierPrevalence && (
        <BarrierPrevalenceCard
          prevalence={data.barrier_prevalence!}
          archetype={data.archetype_id ?? ""}
        />
      )}
      {hasPosteriors && (
        <MechanismPosteriorsCard
          posteriors={data.posteriors!}
          archetype={data.archetype_id ?? ""}
          barrier={data.barrier ?? ""}
        />
      )}
      {!hasBarrierPrevalence && !hasPosteriors && (
        <Card className="border-dashed">
          <CardHeader>
            <CardTitle>No posterior evidence yet</CardTitle>
            <CardDescription>
              The hierarchical learning has not accumulated enough
              observations for this cell. Evidence will populate as touches
              are delivered and outcomes are observed. Cold-start
              estimates inherit from the corpus + category priors until
              then.
            </CardDescription>
          </CardHeader>
        </Card>
      )}
    </div>
  );
}

function GlobalStatsCard({
  data,
}: {
  data: MechanismEffectivenessResponse;
}) {
  const entries = Object.entries(data.global_stats ?? {}).filter(
    ([, v]) => v !== null && v !== undefined,
  );
  if (entries.length === 0) return null;
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base">Hierarchy state</CardTitle>
        <CardDescription>
          Global stats from the 5-level prior manager (corpus → category →
          brand → campaign → sequence).
        </CardDescription>
      </CardHeader>
      <CardContent>
        <dl className="grid grid-cols-2 gap-3 text-sm md:grid-cols-4">
          {entries.map(([k, v]) => (
            <div key={k}>
              <dt className="text-xs uppercase text-muted-foreground">
                {humanize(k)}
              </dt>
              <dd className="text-sm font-semibold">{String(v)}</dd>
            </div>
          ))}
        </dl>
      </CardContent>
    </Card>
  );
}

function BarrierPrevalenceCard({
  prevalence,
  archetype,
}: {
  prevalence: Record<string, number>;
  archetype: string;
}) {
  const sorted = useMemo(
    () =>
      Object.entries(prevalence).sort(
        ([, a], [, b]) => (b as number) - (a as number),
      ),
    [prevalence],
  );
  const max = Math.max(...sorted.map(([, v]) => v), 0.0001);
  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-base">
          Barrier prevalence · {humanize(archetype)}
        </CardTitle>
        <CardDescription>
          How frequently each barrier is diagnosed for this archetype,
          aggregated across observed touches. Highest-prevalence barriers
          are where the retargeting cascade spends most of its adaptive
          learning budget.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-2">
        {sorted.map(([barrier, value]) => {
          const width = Math.max(4, (value / max) * 100);
          return (
            <div key={barrier} className="grid grid-cols-[12rem_1fr_4rem] items-center gap-3 text-sm">
              <span className="truncate">{humanize(barrier)}</span>
              <div className="h-2 rounded-full bg-muted">
                <div
                  className="h-2 rounded-full bg-primary"
                  style={{ width: `${width}%` }}
                />
              </div>
              <span className="text-right font-mono tabular-nums">
                {(value * 100).toFixed(1)}%
              </span>
            </div>
          );
        })}
      </CardContent>
    </Card>
  );
}

function MechanismPosteriorsCard({
  posteriors,
  archetype,
  barrier,
}: {
  posteriors: Record<string, MechanismPosterior>;
  archetype: string;
  barrier: string;
}) {
  // Sort by posterior mean × confidence descending — prioritizes both
  // predicted effectiveness AND strength of evidence behind the estimate.
  const ranked = useMemo(
    () =>
      Object.entries(posteriors).sort(
        ([, a], [, b]) => b.mean * b.confidence - a.mean * a.confidence,
      ),
    [posteriors],
  );
  const strongest = ranked[0]?.[0];

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-base">
          Mechanism posteriors · {humanize(archetype)} × {humanize(barrier)}
        </CardTitle>
        <CardDescription>
          Beta posteriors on every therapeutic mechanism the cascade has
          tried for this cell. Ranked by posterior mean × confidence — so
          high-evidence wins outrank lucky low-N means. The strongest cell
          shapes the first-touch prior for this archetype under this
          barrier.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-2">
        {ranked.map(([mechanism, p]) => (
          <PosteriorRow
            key={mechanism}
            name={mechanism}
            posterior={p}
            isStrongest={mechanism === strongest}
          />
        ))}
      </CardContent>
    </Card>
  );
}

function PosteriorRow({
  name,
  posterior,
  isStrongest,
}: {
  name: string;
  posterior: MechanismPosterior;
  isStrongest: boolean;
}) {
  const meanPct = Math.round(posterior.mean * 100);
  const confidencePct = Math.round(posterior.confidence * 100);

  return (
    <div
      className={
        "grid grid-cols-[14rem_1fr_6rem_6rem_6rem] items-center gap-3 rounded-md px-2 py-2 text-sm " +
        (isStrongest
          ? "bg-emerald-500/10 ring-1 ring-emerald-500/40"
          : "")
      }
    >
      <span className="flex items-center gap-2 truncate">
        {isStrongest && (
          <Badge
            variant="outline"
            className="border-emerald-500/60 text-[10px] uppercase text-emerald-600 dark:text-emerald-400"
          >
            Strongest
          </Badge>
        )}
        <span className="truncate">{humanize(name)}</span>
      </span>
      <div className="h-2 rounded-full bg-muted">
        <div
          className="h-2 rounded-full bg-primary"
          style={{ width: `${Math.max(2, meanPct)}%` }}
        />
      </div>
      <span className="text-right font-mono tabular-nums">
        {(posterior.mean * 100).toFixed(1)}%
      </span>
      <span className="text-right font-mono tabular-nums text-muted-foreground">
        n = {posterior.sample_count}
      </span>
      <span className="text-right font-mono tabular-nums text-muted-foreground">
        conf {confidencePct}%
      </span>
    </div>
  );
}
