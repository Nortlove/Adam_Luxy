"use client";

import { useEffect, useMemo, useRef, useState, useTransition } from "react";
import {
  ArrowRight,
  CheckCircle2,
  RefreshCw,
  Target,
  XCircle,
} from "lucide-react";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";

import {
  BRIER_BINS,
  CALIBRATION_SCENARIOS,
  brierScore,
  type CalibrationScenario,
} from "@/lib/calibration/scenarios";
import { recordCalibrationClaim } from "./actions";

type ScenarioRecord = {
  scenario: CalibrationScenario;
  userProbability: number;
  brier: number;
  correctDirection: boolean;
};

export function CalibrationTraining() {
  const [sessionId, setSessionId] = useState<string>("");
  const [index, setIndex] = useState(0);
  const [answered, setAnswered] = useState<ScenarioRecord[]>([]);
  const [selectedBin, setSelectedBin] = useState<number | null>(null);
  const [revealed, setRevealed] = useState<boolean>(false);
  const [pending, startTransition] = useTransition();
  const startedAt = useRef<number>(Date.now());

  useEffect(() => {
    setSessionId(
      `calibration-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    );
  }, []);

  // Reset per-question state when advancing.
  useEffect(() => {
    setSelectedBin(null);
    setRevealed(false);
    startedAt.current = Date.now();
  }, [index]);

  const scenario: CalibrationScenario | undefined =
    CALIBRATION_SCENARIOS[index];
  const done = index >= CALIBRATION_SCENARIOS.length;

  const avgBrier = useMemo(() => {
    if (answered.length === 0) return null;
    return answered.reduce((s, r) => s + r.brier, 0) / answered.length;
  }, [answered]);

  const correctDirectionCount = useMemo(
    () => answered.filter((r) => r.correctDirection).length,
    [answered],
  );

  function commit() {
    if (!scenario || selectedBin === null) return;
    const probability = BRIER_BINS[selectedBin].value;
    const brier = brierScore(probability, scenario.actual_outcome);
    const correctDirection =
      scenario.actual_outcome === "true" ? probability >= 0.5 : probability <= 0.5;
    const latencyMs = Date.now() - startedAt.current;

    startTransition(async () => {
      await recordCalibrationClaim({
        scenarioId: scenario.id,
        category: scenario.category,
        prompt: scenario.prompt,
        userProbability: probability,
        actualOutcome: scenario.actual_outcome,
        brierContribution: brier,
        latencyMs,
        sessionId,
      });
      setAnswered((a) => [
        ...a,
        {
          scenario,
          userProbability: probability,
          brier,
          correctDirection,
        },
      ]);
      setRevealed(true);
    });
  }

  function next() {
    setIndex((i) => i + 1);
  }

  function reset() {
    setAnswered([]);
    setIndex(0);
    setSelectedBin(null);
    setRevealed(false);
    setSessionId(
      `calibration-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    );
  }

  if (done) {
    return (
      <div className="flex flex-col gap-6">
        <SessionSummary
          records={answered}
          avgBrier={avgBrier}
          correctDirectionCount={correctDirectionCount}
        />
        <Button onClick={reset} className="w-fit">
          <RefreshCw className="mr-1 size-4" />
          Run again
        </Button>
      </div>
    );
  }

  if (!scenario) return null;

  return (
    <div className="flex flex-col gap-4">
      <ProgressBar
        index={index}
        total={CALIBRATION_SCENARIOS.length}
        avgBrier={avgBrier}
      />

      <Card>
        <CardHeader>
          <div className="mb-1 flex items-center gap-2">
            <Badge variant="outline" className="text-[10px] uppercase">
              {scenario.category.replace(/_/g, " ")}
            </Badge>
            <span className="text-xs text-muted-foreground">
              Question {index + 1} of {CALIBRATION_SCENARIOS.length}
            </span>
          </div>
          <CardTitle className="text-base leading-snug">
            {scenario.prompt}
          </CardTitle>
          <CardDescription>{scenario.context}</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          <div>
            <div className="mb-2 text-xs uppercase text-muted-foreground">
              How likely is this TRUE?
            </div>
            <div className="grid grid-cols-11 gap-1">
              {BRIER_BINS.map((b, i) => (
                <button
                  key={b.id}
                  type="button"
                  onClick={() => !revealed && setSelectedBin(i)}
                  disabled={revealed}
                  className={
                    "rounded-md border px-1 py-2 text-xs font-semibold transition-colors disabled:cursor-not-allowed " +
                    (selectedBin === i
                      ? "border-primary bg-primary text-primary-foreground"
                      : "border-border hover:border-primary")
                  }
                >
                  {b.label}
                </button>
              ))}
            </div>
            <div className="mt-1 flex justify-between text-[10px] text-muted-foreground">
              <span>certainly false</span>
              <span>coin flip</span>
              <span>certainly true</span>
            </div>
          </div>

          {!revealed && (
            <Button
              onClick={commit}
              disabled={selectedBin === null || pending}
              className="w-fit"
            >
              {pending ? "Saving…" : "Commit estimate"}
            </Button>
          )}

          {revealed && (
            <RevealCard
              scenario={scenario}
              userProbability={BRIER_BINS[selectedBin!].value}
              onNext={next}
              isLast={index + 1 >= CALIBRATION_SCENARIOS.length}
            />
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function ProgressBar({
  index,
  total,
  avgBrier,
}: {
  index: number;
  total: number;
  avgBrier: number | null;
}) {
  const pct = Math.round((index / total) * 100);
  return (
    <div>
      <div className="mb-1 flex items-center justify-between text-xs text-muted-foreground">
        <span>
          {index} / {total}
        </span>
        <span>
          {avgBrier != null
            ? `avg brier: ${avgBrier.toFixed(3)}`
            : "brier: —"}
        </span>
      </div>
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
        <div
          className="h-full bg-primary transition-[width] duration-300"
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

function RevealCard({
  scenario,
  userProbability,
  onNext,
  isLast,
}: {
  scenario: CalibrationScenario;
  userProbability: number;
  onNext: () => void;
  isLast: boolean;
}) {
  const outcomeBool = scenario.actual_outcome === "true";
  const correctDirection =
    (outcomeBool && userProbability >= 0.5) ||
    (!outcomeBool && userProbability <= 0.5);
  const brier = brierScore(userProbability, scenario.actual_outcome);

  return (
    <div
      className={
        "flex flex-col gap-3 rounded-lg border p-4 " +
        (correctDirection
          ? "border-emerald-200 bg-emerald-50/40 dark:border-emerald-900 dark:bg-emerald-950/20"
          : "border-rose-200 bg-rose-50/40 dark:border-rose-900 dark:bg-rose-950/20")
      }
    >
      <div className="flex items-center gap-2 text-sm font-semibold">
        {correctDirection ? (
          <CheckCircle2 className="size-4 text-emerald-600 dark:text-emerald-400" />
        ) : (
          <XCircle className="size-4 text-rose-600 dark:text-rose-400" />
        )}
        {correctDirection
          ? `Right direction — actual: ${scenario.actual_outcome.toUpperCase()}`
          : `Other direction — actual: ${scenario.actual_outcome.toUpperCase()}`}
      </div>

      <div className="text-sm">{scenario.explanation}</div>

      <div className="grid grid-cols-3 gap-2 text-xs">
        <div>
          <div className="uppercase text-muted-foreground">Your estimate</div>
          <div className="text-sm font-semibold">
            {(userProbability * 100).toFixed(0)}% true
          </div>
        </div>
        <div>
          <div className="uppercase text-muted-foreground">Actual</div>
          <div className="text-sm font-semibold capitalize">
            {scenario.actual_outcome}
          </div>
        </div>
        <div>
          <div className="uppercase text-muted-foreground">Brier</div>
          <div className="text-sm font-semibold">{brier.toFixed(3)}</div>
        </div>
      </div>

      <div className="text-[10px] text-muted-foreground">
        Source: {scenario.source}
      </div>

      <div className="flex justify-end">
        <Button onClick={onNext}>
          {isLast ? "See session summary" : "Next question"}
          <ArrowRight className="ml-1 size-4" />
        </Button>
      </div>
    </div>
  );
}

function SessionSummary({
  records,
  avgBrier,
  correctDirectionCount,
}: {
  records: ScenarioRecord[];
  avgBrier: number | null;
  correctDirectionCount: number;
}) {
  const bierTier =
    avgBrier == null
      ? "incomplete"
      : avgBrier < 0.1
        ? "superforecaster tier (< 0.10)"
        : avgBrier < 0.18
          ? "well-calibrated (0.10–0.18)"
          : avgBrier < 0.25
            ? "calibrated with room (0.18–0.25)"
            : "needs practice (> 0.25)";

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Target className="size-5 text-primary" />
          Session summary
        </CardTitle>
        <CardDescription>
          Tetlock's benchmark: superforecaster-tier on geopolitical binaries
          is ~0.14. Lower is better.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <div className="grid grid-cols-3 gap-3">
          <div>
            <div className="text-xs uppercase text-muted-foreground">
              Average Brier
            </div>
            <div className="text-2xl font-semibold tabular-nums">
              {avgBrier?.toFixed(3) ?? "—"}
            </div>
          </div>
          <div>
            <div className="text-xs uppercase text-muted-foreground">
              Right direction
            </div>
            <div className="text-2xl font-semibold tabular-nums">
              {correctDirectionCount} / {records.length}
            </div>
          </div>
          <div>
            <div className="text-xs uppercase text-muted-foreground">Tier</div>
            <div className="text-sm font-semibold">{bierTier}</div>
          </div>
        </div>

        <Alert>
          <AlertTitle>Logged to the Dialogue Ledger</AlertTitle>
          <AlertDescription>
            Every answer wrote a Claim with stated_confidence ={" "}
            <em>your probability estimate</em> and domain ={" "}
            <em>calibration.{"{category}"}</em>. Per-domain calibration
            surfaces on the Ledger page will populate as you train.
          </AlertDescription>
        </Alert>

        <div className="flex flex-col gap-2 rounded-lg border bg-muted/20 p-3 text-xs">
          <div className="text-sm font-semibold">Per-question breakdown</div>
          {records.map((r) => (
            <div
              key={r.scenario.id}
              className="grid grid-cols-[1fr_90px_90px_70px] gap-2 border-t pt-2"
            >
              <div className="line-clamp-1 text-foreground">
                {r.scenario.prompt}
              </div>
              <div>
                you: {(r.userProbability * 100).toFixed(0)}% true
              </div>
              <div>
                actual:{" "}
                <span className="font-semibold uppercase">
                  {r.scenario.actual_outcome}
                </span>
              </div>
              <div className="tabular-nums">brier {r.brier.toFixed(3)}</div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
