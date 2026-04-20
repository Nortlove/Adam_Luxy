"use client";

/**
 * MoodProbe — fast two-alternative affective check at session start.
 *
 * Indexes affective state so subsequent elicitations in the session
 * can be covariate-adjusted. Per HMT Foundation §6 Principle 3 —
 * bias and mood are first-class contaminants that must be
 * instrumented, not ignored. A single low-friction two-option click
 * stores a mood_index in {-1, 0, 1} that rides along with later
 * claims.
 */

import { useRef, useState, useTransition } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";

import { submitClaim } from "@/app/(app)/ledger/actions";

const OPTIONS = [
  { id: "low", label: "Low energy / pessimistic", value: -1 },
  { id: "neutral", label: "Level / neither", value: 0 },
  { id: "high", label: "High energy / optimistic", value: 1 },
] as const;

export type MoodProbeProps = {
  sessionId: string;
  onComplete?: (moodIndex: number) => void;
};

export function MoodProbe(props: MoodProbeProps) {
  const startedAt = useRef(Date.now());
  const [pending, startTransition] = useTransition();
  const [chosen, setChosen] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  function choose(value: number, label: string) {
    if (chosen !== null) return;
    setChosen(value);
    const latencyMs = Date.now() - startedAt.current;

    startTransition(async () => {
      const result = await submitClaim({
        text: `Session-start mood: ${label}`,
        elicitation_mode: "timed_pair",
        domain: "mood",
        latency_ms: latencyMs,
        frame: "neutral",
        session_id: props.sessionId,
        mood_index: value,
      });
      if (!result.ok) {
        setError(`Failed to record (${result.status}). ${result.message}`);
        setChosen(null);
        return;
      }
      props.onComplete?.(value);
    });
  }

  if (chosen !== null && !error) {
    return (
      <Card className="border-dashed">
        <CardHeader>
          <CardTitle className="text-base">Mood indexed</CardTitle>
          <CardDescription>
            Subsequent elicitations this session will be
            covariate-adjusted against this mood reading.
          </CardDescription>
        </CardHeader>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Quick read</CardTitle>
        <CardDescription>
          Which of these is closest to your current state? Fast answer
          only — this becomes a covariate for every claim today.
        </CardDescription>
      </CardHeader>
      <CardContent className="grid gap-3 md:grid-cols-3">
        {OPTIONS.map((o) => (
          <button
            key={o.id}
            type="button"
            onClick={() => choose(o.value, o.label)}
            disabled={pending}
            className="flex items-center justify-center rounded-lg border border-border bg-card p-4 text-center text-sm font-medium transition-colors hover:border-primary hover:bg-primary/5 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {o.label}
          </button>
        ))}
        {error && (
          <Alert variant="destructive" className="md:col-span-3">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}
      </CardContent>
    </Card>
  );
}
