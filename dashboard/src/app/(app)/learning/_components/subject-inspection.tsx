"use client";

/**
 * Subject Inspection — renders the unified-puzzle PersonState for one
 * subject. The backend's `infer_person()` performs a JOINT inference over
 * all available evidence (the 6 nonconscious signals from Enhancement #34,
 * the trajectory from Enhancement #36 repeated-measures, the bilateral
 * alignment edges, the archetype posteriors from Enhancement #33), and
 * produces a single coherent PersonState. We render that state.
 *
 * Structural commitments (orientation discipline):
 *
 *   - Bilateral split (A12): the "Buyer side" (barrier + response
 *     pattern + interaction archetype) and the "Seller side"
 *     (recommended mechanism + communication style + prediction-error
 *     level) are rendered side-by-side with an alignment measure
 *     (evidence_quality × barrier_confidence) between.
 *
 *   - Three-timescale rendering (A9): Moment (current barrier + touch),
 *     Lifetime (this subject's trajectory + touches observed), and
 *     Population (interaction archetype + suppression flag) are
 *     rendered as distinct temporal lenses rather than a single
 *     flat profile.
 *
 *   - No composed English in generators (A4): the `narrative` string
 *     comes verbatim from `unified_puzzle.infer_person()`. The
 *     mechanism_rationale likewise. This client renders them; it does
 *     not synthesize new prose.
 *
 *   - Likert avoidance (A7): continuous probabilities rendered with
 *     explicit confidence and sample counts, not ordinal categories.
 */

import { useState } from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { PersonState } from "@/lib/types";

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

export function SubjectInspectionView() {
  const [input, setInput] = useState<string>("");
  const [state, setState] = useState<PersonState | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(false);

  async function submit(e?: React.FormEvent) {
    e?.preventDefault();
    const trimmed = input.trim();
    if (!trimmed) return;
    setLoading(true);
    setError(null);
    setState(null);
    try {
      const res = await fetch(
        `/api/learning/subject/${encodeURIComponent(trimmed)}`,
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
      const json = (await res.json()) as PersonState;
      setState(json);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Subject lookup</CardTitle>
          <CardDescription>
            Enter a visitor id to render the joint unified-puzzle inference
            — all nonconscious signals, bilateral alignment, trajectory,
            and archetype posteriors considered simultaneously. This is
            one coherent cascade state, not six marginal views.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form
            onSubmit={submit}
            className="flex items-end gap-3"
          >
            <div className="flex-1">
              <label className="text-xs uppercase text-muted-foreground">
                Visitor id
              </label>
              <Input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="e.g., visitor_abc123"
                autoComplete="off"
                autoCapitalize="off"
                autoCorrect="off"
                spellCheck={false}
              />
            </div>
            <Button type="submit" disabled={loading || !input.trim()}>
              {loading ? "Inferring…" : "Render state"}
            </Button>
          </form>
        </CardContent>
      </Card>

      {error && (
        <Alert variant="destructive">
          <AlertTitle>Could not render subject state</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {state && !loading && !error && <PersonStateView state={state} />}
    </div>
  );
}

function PersonStateView({ state }: { state: PersonState }) {
  return (
    <div className="flex flex-col gap-4">
      <IdentityHeader state={state} />
      {state.narrative && <NarrativeCard narrative={state.narrative} />}
      <BilateralSplit state={state} />
      <ThreeTimescale state={state} />
      <DecisionCard state={state} />
    </div>
  );
}

function IdentityHeader({ state }: { state: PersonState }) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="flex flex-wrap items-center gap-2 text-base">
          <span className="font-mono">{state.user_id || "—"}</span>
          {state.archetype && (
            <Badge variant="outline">{humanize(state.archetype)}</Badge>
          )}
          {state.suppress && (
            <Badge
              variant="outline"
              className="border-rose-500/60 text-rose-600 dark:text-rose-400"
            >
              Suppress · {humanize(state.suppress_reason || "")}
            </Badge>
          )}
        </CardTitle>
        <CardDescription>
          Evidence quality {pct(state.evidence_quality)} · sessions{" "}
          observed {state.sessions_observed} · conversion probability{" "}
          {pct(state.conversion_probability)}
        </CardDescription>
      </CardHeader>
    </Card>
  );
}

function NarrativeCard({ narrative }: { narrative: string }) {
  return (
    <Card className="border-l-4 border-l-primary">
      <CardHeader className="pb-2">
        <CardTitle className="text-base">Joint-inference narrative</CardTitle>
        <CardDescription>
          Backend-composed summary of the puzzle state. Rendered as-is —
          no client-side English composition.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <p className="whitespace-pre-line text-sm leading-relaxed">
          {narrative}
        </p>
      </CardContent>
    </Card>
  );
}

function BilateralSplit({ state }: { state: PersonState }) {
  const alignment =
    state.barrier_confidence * state.evidence_quality;
  const barrierKind = state.barrier_is_somatic
    ? "somatic"
    : state.barrier_is_cognitive
      ? "cognitive"
      : state.barrier_is_contextual
        ? "contextual"
        : "unspecified";

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base">Bilateral cascade state</CardTitle>
        <CardDescription>
          Buyer-side barrier and response pattern · seller-side mechanism
          response · alignment = barrier_confidence × evidence_quality.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 gap-3 md:grid-cols-[1fr_auto_1fr]">
          <div className="rounded-md border border-border/60 p-3">
            <div className="mb-2 text-xs uppercase text-muted-foreground">
              Buyer side
            </div>
            <Row label="Dominant barrier" value={humanize(state.dominant_barrier)} />
            <Row label="Barrier kind" value={humanize(barrierKind)} />
            <Row
              label="Barrier confidence"
              value={pct(state.barrier_confidence)}
              mono
            />
            <Row
              label="Response type"
              value={humanize(state.response_type)}
            />
            <Row
              label="Clicks ads"
              value={state.clicks_ads ? "yes" : "no"}
            />
            <Row
              label="Responds to organic"
              value={state.responds_to_organic ? "yes" : "no"}
            />
          </div>

          <div className="flex flex-col items-center justify-center self-stretch px-2">
            <div className="flex flex-col items-center gap-1 rounded-md border border-primary/30 bg-primary/5 px-3 py-2 text-xs">
              <span className="uppercase text-muted-foreground">
                Alignment
              </span>
              <span className="font-mono text-sm font-semibold tabular-nums">
                {pct(alignment)}
              </span>
            </div>
          </div>

          <div className="rounded-md border border-border/60 p-3">
            <div className="mb-2 text-xs uppercase text-muted-foreground">
              Seller side
            </div>
            <Row
              label="Recommended mechanism"
              value={humanize(state.recommended_mechanism)}
            />
            <Row
              label="Communication style"
              value={humanize(state.communication_style)}
            />
            <Row
              label="Prediction error level"
              value={state.prediction_error_level.toFixed(2)}
              mono
            />
            {state.mechanism_rationale && (
              <div className="mt-2 text-xs text-muted-foreground">
                <span className="uppercase">Rationale</span>
                <p className="mt-1 whitespace-pre-line text-xs leading-relaxed text-foreground/80">
                  {state.mechanism_rationale}
                </p>
              </div>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function ThreeTimescale({ state }: { state: PersonState }) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base">Three-timescale state</CardTitle>
        <CardDescription>
          Moment · lifetime (this subject) · population (interaction
          archetype). Each lens is a distinct temporal scope; together
          they characterize the state across the three scales the
          reinforcement mechanism operates at.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
          <TimescaleColumn
            label="Moment"
            rows={[
              ["Receptive now", state.receptive_now ? "yes" : "no"],
              ["Dominant barrier", humanize(state.dominant_barrier)],
              ["Next touch", humanize(state.recommended_mechanism)],
            ]}
          />
          <TimescaleColumn
            label="Lifetime"
            rows={[
              ["Trajectory", humanize(state.trajectory)],
              [
                "Trajectory velocity",
                state.trajectory_velocity.toFixed(2),
              ],
              [
                "Touches remaining",
                state.touches_remaining.toFixed(1),
              ],
              ["Sessions observed", String(state.sessions_observed)],
            ]}
          />
          <TimescaleColumn
            label="Population"
            rows={[
              ["Archetype", humanize(state.archetype) || "—"],
              [
                "Interaction archetype",
                humanize(state.interaction_archetype) || "—",
              ],
              [
                "Interaction confidence",
                pct(state.interaction_archetype_confidence),
              ],
              [
                "Suppress",
                state.suppress
                  ? `yes · ${humanize(state.suppress_reason || "")}`
                  : "no",
              ],
            ]}
          />
        </div>
      </CardContent>
    </Card>
  );
}

function TimescaleColumn({
  label,
  rows,
}: {
  label: string;
  rows: Array<[string, string]>;
}) {
  return (
    <div className="rounded-md border border-border/60 p-3">
      <div className="mb-2 text-xs uppercase text-muted-foreground">
        {label}
      </div>
      <div className="flex flex-col gap-1">
        {rows.map(([k, v]) => (
          <div
            key={k}
            className="grid grid-cols-2 items-baseline gap-2 text-sm"
          >
            <span className="text-xs text-muted-foreground">{k}</span>
            <span className="text-sm font-medium">{v}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function DecisionCard({ state }: { state: PersonState }) {
  const cls = state.should_continue
    ? "border-l-emerald-500"
    : "border-l-rose-500";
  return (
    <Card className={`border-l-4 ${cls}`}>
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center justify-between text-base">
          <span>
            {state.should_continue ? "Continue" : "Release"}
          </span>
          <Badge variant="outline" className="text-[10px] uppercase">
            {state.should_continue ? "keep dosing" : "stop dosing"}
          </Badge>
        </CardTitle>
        <CardDescription>
          {state.continue_reason || "No rationale supplied."}
        </CardDescription>
      </CardHeader>
    </Card>
  );
}

function Row({
  label,
  value,
  mono = false,
}: {
  label: string;
  value: string;
  mono?: boolean;
}) {
  return (
    <div className="mt-1 grid grid-cols-2 items-baseline gap-2 text-sm">
      <span className="text-xs text-muted-foreground">{label}</span>
      <span
        className={`text-sm font-medium ${mono ? "font-mono tabular-nums" : ""}`}
      >
        {value || "—"}
      </span>
    </div>
  );
}
