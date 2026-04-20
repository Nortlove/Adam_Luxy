"use client";

/**
 * TimedPair — binary paired comparison with a visible countdown.
 *
 * Forces Type 1 (fast, autonomous) responding by limiting working
 * memory. Use when the target is tacit / intuitive knowledge
 * vulnerable to System 2 confabulation. Per HMT Foundation §8.2,
 * §6 Principle 2. Response latency is logged alongside the choice.
 */

import { useEffect, useRef, useState, useTransition } from "react";
import { Timer } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";

import { submitClaim } from "@/app/(app)/ledger/actions";

export type TimedPairProps = {
  question: string;
  domain: string;
  optionA: { id: string; label: string };
  optionB: { id: string; label: string };
  deadlineMs?: number; // default 3000
  onComplete?: (choice: string | null) => void;
  sessionId?: string;
  moodIndex?: number | null;
};

type Phase = "ready" | "live" | "submitted" | "timeout";

export function TimedPair(props: TimedPairProps) {
  const deadlineMs = props.deadlineMs ?? 3000;
  const startedAt = useRef<number>(0);
  const [phase, setPhase] = useState<Phase>("ready");
  const [remaining, setRemaining] = useState(deadlineMs);
  const [chosen, setChosen] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, startTransition] = useTransition();

  useEffect(() => {
    if (phase !== "live") return;
    const start = startedAt.current;
    const interval = setInterval(() => {
      const elapsed = Date.now() - start;
      const left = Math.max(0, deadlineMs - elapsed);
      setRemaining(left);
      if (left <= 0) {
        clearInterval(interval);
        setPhase("timeout");
        recordTimeout(deadlineMs);
      }
    }, 40);
    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [phase]);

  function start() {
    startedAt.current = Date.now();
    setRemaining(deadlineMs);
    setPhase("live");
    setError(null);
  }

  function handleChoose(choiceId: string, choiceLabel: string) {
    if (phase !== "live") return;
    const latencyMs = Date.now() - startedAt.current;
    setChosen(choiceId);
    setPhase("submitted");
    startTransition(async () => {
      const result = await submitClaim({
        text: `${props.question} → ${choiceLabel}`,
        elicitation_mode: "timed_pair",
        domain: props.domain,
        latency_ms: latencyMs,
        frame: "neutral",
        session_id: props.sessionId,
        mood_index: props.moodIndex ?? null,
      });
      if (!result.ok) {
        setError(`Failed to record (${result.status}). ${result.message}`);
        setPhase("live");
        setChosen(null);
        return;
      }
      props.onComplete?.(choiceId);
    });
  }

  function recordTimeout(latencyMs: number) {
    startTransition(async () => {
      await submitClaim({
        text: `${props.question} → (no response within ${deadlineMs}ms)`,
        elicitation_mode: "timed_pair",
        domain: props.domain,
        latency_ms: latencyMs,
        frame: "neutral",
        session_id: props.sessionId,
        mood_index: props.moodIndex ?? null,
      });
    });
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center justify-between gap-2 text-base">
          <span>{props.question}</span>
          <span className="flex items-center gap-1 text-xs font-normal text-muted-foreground">
            <Timer className="size-3" />
            {phase === "live" ? `${(remaining / 1000).toFixed(1)}s` : `${(deadlineMs / 1000).toFixed(0)}s`}
          </span>
        </CardTitle>
        <CardDescription>
          Gut-check only. Pick fast — the fast answer is usually the
          true one.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        {phase === "ready" && (
          <Button onClick={start} className="w-fit">
            I&rsquo;m ready — start the clock
          </Button>
        )}

        {phase === "live" && (
          <>
            <CountdownBar remaining={remaining} total={deadlineMs} />
            <div className="grid gap-3 md:grid-cols-2">
              <TimedButton
                label={props.optionA.label}
                onSelect={() =>
                  handleChoose(props.optionA.id, props.optionA.label)
                }
              />
              <TimedButton
                label={props.optionB.label}
                onSelect={() =>
                  handleChoose(props.optionB.id, props.optionB.label)
                }
              />
            </div>
          </>
        )}

        {phase === "submitted" && (
          <Alert>
            <AlertDescription>
              Recorded. {pending ? "Saving…" : "Latency logged alongside your choice."}
            </AlertDescription>
          </Alert>
        )}

        {phase === "timeout" && (
          <Alert>
            <AlertDescription>
              No response within {deadlineMs}ms — logged as &ldquo;no
              response.&rdquo; Try again if you want another read.
            </AlertDescription>
          </Alert>
        )}

        {error && (
          <Alert variant="destructive">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}
      </CardContent>
    </Card>
  );
}

function CountdownBar({
  remaining,
  total,
}: {
  remaining: number;
  total: number;
}) {
  const pct = Math.max(0, Math.min(100, (remaining / total) * 100));
  return (
    <div className="h-1 w-full overflow-hidden rounded-full bg-muted">
      <div
        className="h-full bg-primary transition-[width] duration-75 ease-linear"
        style={{ width: `${pct}%` }}
      />
    </div>
  );
}

function TimedButton({
  label,
  onSelect,
}: {
  label: string;
  onSelect: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onSelect}
      className="flex items-center justify-center rounded-lg border-2 border-primary bg-primary/5 p-6 text-center text-base font-semibold transition-colors hover:bg-primary hover:text-primary-foreground"
    >
      {label}
    </button>
  );
}
