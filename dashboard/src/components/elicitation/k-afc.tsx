"use client";

/**
 * KAFC — k-alternative forced choice.
 *
 * Pick one from k options. Per HMT Foundation §8.3 — useful when
 * binary is too coarse, e.g. "which of these four customer
 * descriptions matches your best-performing segment?" Logs the
 * chosen id as a Claim with elicitation_mode=k_afc.
 */

import { useRef, useState, useTransition } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";

import { submitClaim } from "@/app/(app)/ledger/actions";

export type KAFCOption = {
  id: string;
  label: string;
  description?: string;
};

export type KAFCProps = {
  question: string;
  domain: string;
  options: KAFCOption[];
  onComplete?: (choice: string) => void;
  sessionId?: string;
  moodIndex?: number | null;
};

export function KAFC(props: KAFCProps) {
  const startedAt = useRef(Date.now());
  const [pending, startTransition] = useTransition();
  const [chosen, setChosen] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  function choose(optionId: string, optionLabel: string) {
    if (chosen) return;
    setChosen(optionId);
    const latencyMs = Date.now() - startedAt.current;

    startTransition(async () => {
      const result = await submitClaim({
        text: `${props.question} → ${optionLabel}`,
        elicitation_mode: "k_afc",
        domain: props.domain,
        latency_ms: latencyMs,
        frame: "neutral",
        session_id: props.sessionId,
        mood_index: props.moodIndex ?? null,
      });
      if (!result.ok) {
        setError(`Failed to record (${result.status}). ${result.message}`);
        setChosen(null);
        return;
      }
      props.onComplete?.(optionId);
    });
  }

  if (chosen && !error) {
    return (
      <Card className="border-emerald-200 dark:border-emerald-900">
        <CardHeader>
          <CardTitle className="text-base">Recorded</CardTitle>
          <CardDescription>
            Your choice is logged in the Dialogue Ledger as a hypothesis.
          </CardDescription>
        </CardHeader>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">{props.question}</CardTitle>
        <CardDescription>
          Pick the one that feels closest. You can always revisit — everything
          you answer here enters the ledger as a hypothesis.
        </CardDescription>
      </CardHeader>
      <CardContent className="grid gap-3 md:grid-cols-2">
        {props.options.map((o) => (
          <button
            key={o.id}
            type="button"
            onClick={() => choose(o.id, o.label)}
            disabled={pending}
            className="flex flex-col gap-1 rounded-lg border border-border bg-card p-4 text-left transition-colors hover:border-primary hover:bg-primary/5 disabled:cursor-not-allowed disabled:opacity-50"
          >
            <span className="text-sm font-semibold leading-snug">{o.label}</span>
            {o.description && (
              <span className="text-xs text-muted-foreground">
                {o.description}
              </span>
            )}
          </button>
        ))}
        {error && (
          <Alert variant="destructive" className="md:col-span-2">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}
      </CardContent>
    </Card>
  );
}
