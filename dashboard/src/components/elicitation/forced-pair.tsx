"use client";

/**
 * ForcedPair — binary paired comparison, untimed.
 *
 * Use when preference contamination risk is moderate and the user
 * can afford to consider both options. For tacit / intuitive
 * judgments where System 2 deliberation would invite confabulation,
 * use TimedPair instead. Per HMT Foundation §8.1 and §6 Principle 1.
 */

import { useRef, useState, useTransition } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";

import { submitClaim } from "@/app/(app)/ledger/actions";

export type ForcedPairProps = {
  question: string;
  domain: string;
  optionA: { id: string; label: string; description?: string };
  optionB: { id: string; label: string; description?: string };
  onComplete?: (choice: string) => void;
  sessionId?: string;
  moodIndex?: number | null;
};

export function ForcedPair(props: ForcedPairProps) {
  const startedAt = useRef(Date.now());
  const [pending, startTransition] = useTransition();
  const [chosen, setChosen] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  function handleChoose(choiceId: string, choiceLabel: string) {
    if (chosen) return;
    setChosen(choiceId);
    const latencyMs = Date.now() - startedAt.current;

    startTransition(async () => {
      const result = await submitClaim({
        text: `${props.question} → ${choiceLabel}`,
        elicitation_mode: "forced_pair",
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
      props.onComplete?.(choiceId);
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
          Pick one. Both are valid — we care which one feels closer.
        </CardDescription>
      </CardHeader>
      <CardContent className="grid gap-3 md:grid-cols-2">
        <PairOption
          option={props.optionA}
          disabled={pending}
          onSelect={() =>
            handleChoose(props.optionA.id, props.optionA.label)
          }
        />
        <PairOption
          option={props.optionB}
          disabled={pending}
          onSelect={() =>
            handleChoose(props.optionB.id, props.optionB.label)
          }
        />
        {error && (
          <Alert variant="destructive" className="md:col-span-2">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}
      </CardContent>
    </Card>
  );
}

function PairOption({
  option,
  disabled,
  onSelect,
}: {
  option: ForcedPairProps["optionA"];
  disabled: boolean;
  onSelect: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onSelect}
      disabled={disabled}
      className="flex flex-col gap-2 rounded-lg border border-border bg-card p-4 text-left transition-colors hover:border-primary hover:bg-primary/5 disabled:cursor-not-allowed disabled:opacity-50"
    >
      <span className="text-sm font-semibold leading-snug">{option.label}</span>
      {option.description && (
        <span className="text-xs text-muted-foreground">
          {option.description}
        </span>
      )}
    </button>
  );
}
