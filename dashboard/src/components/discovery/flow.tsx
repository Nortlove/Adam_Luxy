"use client";

/**
 * Discovery Flow — guided phase-by-phase Q&A where each answered
 * question becomes a real Claim in the Dialogue Ledger.
 *
 * State machine per phase:
 *   - question index i in [0..questions.length]
 *   - on submit, advance to i+1
 *   - when i == questions.length, show phase-complete card
 *
 * Each question renders via QuestionRenderer, which dispatches to
 * the right elicitation primitive.
 */

import { useEffect, useMemo, useState } from "react";
import { ArrowLeft, ArrowRight, CheckCircle2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

import {
  DISCOVERY_PHASES,
  questionsForPhase,
  type DiscoveryQuestion,
  type PhaseNumber,
} from "@/lib/discovery/questions";
import { QuestionRenderer } from "./question-renderer";

export type DiscoveryFlowProps = {
  phase: PhaseNumber;
  sessionId: string;
  moodIndex: number | null;
  onChangePhase: (phase: PhaseNumber) => void;
};

export function DiscoveryFlow({
  phase,
  sessionId,
  moodIndex,
  onChangePhase,
}: DiscoveryFlowProps) {
  const phaseDef = useMemo(() => DISCOVERY_PHASES.find((p) => p.n === phase)!, [phase]);
  const questions = useMemo(() => questionsForPhase(phase), [phase]);

  const [index, setIndex] = useState(0);
  const [bump, setBump] = useState(0); // forces remount of current question after submit
  const current: DiscoveryQuestion | undefined = questions[index];

  // Reset index when phase changes.
  useEffect(() => {
    setIndex(0);
    setBump(0);
  }, [phase]);

  const isComplete = index >= questions.length;

  function handleComplete() {
    // Delay slightly so the user can see the recorded-confirmation card.
    setTimeout(() => {
      setIndex((i) => i + 1);
      setBump((b) => b + 1);
    }, 800);
  }

  function goBack() {
    if (index > 0) {
      setIndex((i) => i - 1);
      setBump((b) => b + 1);
    }
  }

  const nextPhase = DISCOVERY_PHASES.find((p) => p.n === phase + 1);

  return (
    <div className="flex flex-col gap-4">
      {/* Phase header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <Badge variant="secondary">Phase {phase} of 8</Badge>
            <h2 className="text-lg font-semibold tracking-tight">
              {phaseDef.name}
            </h2>
            <span className="text-sm text-muted-foreground">
              — {phaseDef.tagline}
            </span>
          </div>
          <p className="mt-1 text-sm text-muted-foreground">
            {phaseDef.description}
          </p>
        </div>
      </div>

      {/* Progress */}
      <div>
        <div className="flex items-center justify-between text-xs text-muted-foreground">
          <span>
            Question {Math.min(index + 1, questions.length)} of{" "}
            {questions.length}
          </span>
          <span>{Math.round(((isComplete ? questions.length : index) / questions.length) * 100)}%</span>
        </div>
        <div className="mt-1 h-1.5 w-full overflow-hidden rounded-full bg-muted">
          <div
            className="h-full bg-primary transition-[width] duration-300"
            style={{
              width: `${Math.round(((isComplete ? questions.length : index) / questions.length) * 100)}%`,
            }}
          />
        </div>
      </div>

      {/* Why this question matters — show before the question */}
      {current && (
        <Card className="border-l-4 border-l-primary bg-muted/30">
          <CardContent className="py-3 text-xs text-muted-foreground">
            <span className="font-medium uppercase tracking-wide">
              Why we ask:
            </span>{" "}
            {current.rationale}
          </CardContent>
        </Card>
      )}

      {/* Current question */}
      {current && (
        <QuestionRenderer
          key={`${current.id}-${bump}`}
          question={current}
          sessionId={sessionId}
          moodIndex={moodIndex}
          onComplete={handleComplete}
        />
      )}

      {/* Phase complete */}
      {isComplete && (
        <Card className="border-emerald-200 dark:border-emerald-900">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <CheckCircle2 className="size-5 text-emerald-600 dark:text-emerald-400" />
              Phase {phase} complete — {phaseDef.name}
            </CardTitle>
            <CardDescription>
              Every answer is now in the Dialogue Ledger as a hypothesis. The
              platform will start weaving them into the bilateral cascade
              immediately.
            </CardDescription>
          </CardHeader>
          {nextPhase && (
            <CardContent className="flex items-center justify-end gap-2">
              <Button
                onClick={() => onChangePhase(nextPhase.n as 1 | 2 | 3 | 4)}
              >
                Continue to Phase {nextPhase.n} — {nextPhase.name}
                <ArrowRight className="ml-1 size-4" />
              </Button>
            </CardContent>
          )}
          {!nextPhase && (
            <CardContent className="text-sm text-muted-foreground">
              You&rsquo;ve completed all four phases. Discovery answers can
              be revisited any time — open the Dialogue Ledger to review
              the full history.
            </CardContent>
          )}
        </Card>
      )}

      {/* Back button */}
      {index > 0 && !isComplete && (
        <div>
          <Button variant="ghost" size="sm" onClick={goBack}>
            <ArrowLeft className="mr-1 size-3" />
            previous question
          </Button>
        </div>
      )}
    </div>
  );
}
