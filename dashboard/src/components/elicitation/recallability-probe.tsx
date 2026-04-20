"use client";

/**
 * RecallabilityProbe — the anti-confabulation probe.
 *
 * Follows a confident claim with "can you remember a specific
 * instance?" The fluency of recall is the signal. Fluent episodic
 * recall → tacit knowledge, high weight. Abstract restatement →
 * hypothesis, low weight. Inability to recall → likely confabulation,
 * discount heavily. Per HMT Foundation §8.7, §7.4.
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Alert, AlertDescription } from "@/components/ui/alert";

import { submitClaim } from "@/app/(app)/ledger/actions";

export type RecallabilityProbeProps = {
  parentClaim: string;
  domain: string;
  onComplete?: (
    recallability: "fluent" | "hesitant" | "absent",
    instance: string | null,
  ) => void;
  sessionId?: string;
  moodIndex?: number | null;
};

export function RecallabilityProbe(props: RecallabilityProbeProps) {
  const openedAt = useRef<number>(0);
  const [instance, setInstance] = useState("");
  const [level, setLevel] = useState<
    "fluent" | "hesitant" | "absent" | null
  >(null);
  const [phase, setPhase] = useState<"idle" | "submitted">("idle");
  const [pending, startTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);

  function handleFocus() {
    if (openedAt.current === 0) {
      openedAt.current = Date.now();
    }
  }

  function handleSubmit() {
    if (!level) {
      setError("Pick how easily the instance came to mind.");
      return;
    }
    const totalMs =
      openedAt.current > 0 ? Date.now() - openedAt.current : 0;
    const text =
      level === "absent"
        ? `(no specific instance recalled for: ${props.parentClaim})`
        : instance.trim() ||
          `(instance: ${level} recall for: ${props.parentClaim})`;

    startTransition(async () => {
      const result = await submitClaim({
        text,
        elicitation_mode: "recallability",
        domain: props.domain,
        latency_ms: totalMs,
        frame: "neutral",
        recallability: level,
        session_id: props.sessionId,
        mood_index: props.moodIndex ?? null,
      });
      if (!result.ok) {
        setError(`Failed to record (${result.status}). ${result.message}`);
        return;
      }
      setPhase("submitted");
      props.onComplete?.(level, level === "absent" ? null : instance.trim());
    });
  }

  if (phase === "submitted") {
    return (
      <Card className="border-emerald-200 dark:border-emerald-900">
        <CardHeader>
          <CardTitle className="text-base">Recorded</CardTitle>
          <CardDescription>
            {level === "fluent" &&
              "Fluent recall — the parent claim is weighted as tacit knowledge."}
            {level === "hesitant" &&
              "Hesitant recall — weighted as a reasoned claim, not pattern-matched tacit knowledge."}
            {level === "absent" &&
              "No specific instance recalled — the parent claim is held as a low-weight hypothesis."}
          </CardDescription>
        </CardHeader>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">
          Recallability check
        </CardTitle>
        <CardDescription>
          You just asserted:{" "}
          <em className="text-foreground">&ldquo;{props.parentClaim}&rdquo;</em>.
          Can you think of a specific instance where you saw this?
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        <Label htmlFor="recall-instance">
          The specific case (if you can remember one)
        </Label>
        <Textarea
          id="recall-instance"
          value={instance}
          onFocus={handleFocus}
          onChange={(e) => setInstance(e.target.value)}
          rows={4}
          placeholder="When, who, what — whatever detail surfaces. If nothing specific comes to mind, select 'absent' below."
        />
        <div className="flex flex-col gap-2">
          <Label htmlFor="recall-level">How easily did it come to mind?</Label>
          <Select
            value={level ?? ""}
            onValueChange={(v) =>
              setLevel(v as "fluent" | "hesitant" | "absent")
            }
          >
            <SelectTrigger id="recall-level">
              <SelectValue placeholder="Pick one" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="fluent">
                Fluent — a specific case surfaced immediately
              </SelectItem>
              <SelectItem value="hesitant">
                Hesitant — I reconstructed it more than I recalled it
              </SelectItem>
              <SelectItem value="absent">
                Absent — I can&rsquo;t think of a specific instance
              </SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="flex justify-end">
          <Button onClick={handleSubmit} disabled={pending}>
            {pending ? "Saving…" : "Record"}
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
