"use client";

/**
 * Freeform text input — short (single-line) or long (multi-line).
 * Records a Claim with elicitation_mode=freeform. Not one of the
 * four HMT primitives but needed for open-ended Discovery questions
 * (e.g. "your brand's unique one-sentence promise") where no
 * forced-choice structure applies.
 */

import { useRef, useState, useTransition } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
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

export type FreeformTextProps = {
  prompt: string;
  domain: string;
  helpText?: string;
  variant: "short" | "long";
  minChars?: number;
  onComplete?: (text: string) => void;
  sessionId?: string;
  moodIndex?: number | null;
};

export function FreeformText(props: FreeformTextProps) {
  const minChars = props.minChars ?? (props.variant === "short" ? 8 : 30);
  const openedAt = useRef<number>(0);
  const [value, setValue] = useState("");
  const [phase, setPhase] = useState<"idle" | "submitted">("idle");
  const [pending, startTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);

  function handleFocus() {
    if (openedAt.current === 0) openedAt.current = Date.now();
  }

  function handleSubmit() {
    if (value.trim().length < minChars) {
      setError(`At least ${minChars} characters, please.`);
      return;
    }
    const totalMs = openedAt.current > 0 ? Date.now() - openedAt.current : 0;
    startTransition(async () => {
      const result = await submitClaim({
        text: value.trim(),
        elicitation_mode: "freeform",
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
          <CardDescription>Your answer is in the Dialogue Ledger as a hypothesis.</CardDescription>
        </CardHeader>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">{props.prompt}</CardTitle>
        {props.helpText && <CardDescription>{props.helpText}</CardDescription>}
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        <Label htmlFor="freeform-input" className="sr-only">
          Your answer
        </Label>
        {props.variant === "short" ? (
          <Input
            id="freeform-input"
            value={value}
            onFocus={handleFocus}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleSubmit();
              }
            }}
          />
        ) : (
          <Textarea
            id="freeform-input"
            value={value}
            onFocus={handleFocus}
            onChange={(e) => setValue(e.target.value)}
            rows={5}
          />
        )}
        <div className="flex items-center justify-between text-xs text-muted-foreground">
          <span>
            {value.length} / {minChars}+ chars
          </span>
          <Button onClick={handleSubmit} disabled={pending}>
            {pending ? "Saving…" : "Save & continue"}
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
