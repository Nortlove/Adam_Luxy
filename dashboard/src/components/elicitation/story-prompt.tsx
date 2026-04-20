"use client";

/**
 * StoryPrompt — free-text episodic recall.
 *
 * Anchors the user in a specific remembered instance rather than an
 * abstract generalization. Per HMT Foundation §8.5 — episodic recall
 * beats semantic restatement; stories carry detail that aggregates
 * don't. Tracks time-to-first-keystroke and total time as proxy
 * signals for fluency.
 */

import { useRef, useState, useTransition } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";

import { submitClaim } from "@/app/(app)/ledger/actions";

export type StoryPromptProps = {
  prompt: string;
  domain: string;
  helpText?: string;
  onComplete?: (text: string) => void;
  sessionId?: string;
  moodIndex?: number | null;
  minChars?: number;
};

export function StoryPrompt(props: StoryPromptProps) {
  const minChars = props.minChars ?? 30;
  const openedAt = useRef<number>(0);
  const firstKeyAt = useRef<number | null>(null);
  const [value, setValue] = useState("");
  const [phase, setPhase] = useState<"idle" | "submitted">("idle");
  const [pending, startTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);

  function handleFocus() {
    if (openedAt.current === 0) {
      openedAt.current = Date.now();
    }
  }

  function handleChange(e: React.ChangeEvent<HTMLTextAreaElement>) {
    if (firstKeyAt.current === null && openedAt.current > 0) {
      firstKeyAt.current = Date.now();
    }
    setValue(e.target.value);
  }

  function handleSubmit() {
    if (value.trim().length < minChars) {
      setError(
        `Minimum ${minChars} characters — we want the detail, not the summary.`,
      );
      return;
    }
    const totalMs =
      openedAt.current > 0 ? Date.now() - openedAt.current : 0;
    startTransition(async () => {
      const result = await submitClaim({
        text: value.trim(),
        elicitation_mode: "story",
        domain: props.domain,
        latency_ms: totalMs,
        frame: "neutral",
        session_id: props.sessionId,
        mood_index: props.moodIndex ?? null,
      });
      if (!result.ok) {
        setError(`Failed to record (${result.status}). ${result.message}`);
        return;
      }
      setPhase("submitted");
      props.onComplete?.(value.trim());
    });
  }

  if (phase === "submitted") {
    return (
      <Card className="border-emerald-200 dark:border-emerald-900">
        <CardHeader>
          <CardTitle className="text-base">Logged</CardTitle>
          <CardDescription>
            Your story is in the Dialogue Ledger with the full latency
            trace — the time you took to start, and total time to submit.
          </CardDescription>
        </CardHeader>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">{props.prompt}</CardTitle>
        <CardDescription>
          {props.helpText ??
            "A specific instance you remember — not a general rule. The details are what we need."}
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        <Label htmlFor="story-text" className="sr-only">
          Your story
        </Label>
        <Textarea
          id="story-text"
          value={value}
          onFocus={handleFocus}
          onChange={handleChange}
          rows={6}
          placeholder="The specific case. When, who, what happened, and why you think it turned out the way it did."
        />
        <div className="flex items-center justify-between text-xs text-muted-foreground">
          <span>
            {value.length} / {minChars}+ chars
          </span>
          <Button onClick={handleSubmit} disabled={pending}>
            {pending ? "Saving…" : "Save to ledger"}
          </Button>
        </div>
        {error && (
          <Alert variant="destructive">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}
      </CardContent>
    </Card>
  );
}
