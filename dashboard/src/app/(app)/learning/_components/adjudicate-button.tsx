"use client";

import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";
import { Brain, CheckCircle2, AlertCircle } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";

import { runAdjudicateReady } from "../actions";

export function AdjudicateButton({ readyCount }: { readyCount: number }) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();
  const [result, setResult] = useState<{
    type: "ok" | "error";
    message: string;
    counts?: {
      adjudicated: number;
      user_right: number;
      system_right: number;
      indeterminate: number;
    };
  } | null>(null);

  function trigger() {
    setResult(null);
    startTransition(async () => {
      const res = await runAdjudicateReady();
      if (!res.ok) {
        setResult({
          type: "error",
          message: `Failed (${res.status}). ${res.message}`,
        });
        return;
      }
      const counts = {
        adjudicated: res.batch.adjudicated.length,
        user_right: res.batch.adjudicated.filter(
          (a) => a.outcome === "user_right",
        ).length,
        system_right: res.batch.adjudicated.filter(
          (a) => a.outcome === "system_right",
        ).length,
        indeterminate: res.batch.adjudicated.filter(
          (a) => a.outcome === "indeterminate",
        ).length,
      };
      setResult({
        type: "ok",
        message:
          counts.adjudicated === 0
            ? "Nothing to adjudicate right now."
            : `Adjudicated ${counts.adjudicated} deviation${counts.adjudicated === 1 ? "" : "s"}.`,
        counts,
      });
      router.refresh();
    });
  }

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold">
            Run Inferential Adjudicator
          </h3>
          <p className="text-xs text-muted-foreground">
            {readyCount > 0
              ? `${readyCount} deviation${readyCount === 1 ? "" : "s"} ready for adjudication.`
              : "No ready deviations. Adjudicator runs only on horizon-expired deviations."}
          </p>
        </div>
        <Button onClick={trigger} disabled={pending || readyCount === 0}>
          <Brain className="mr-1 size-4" />
          {pending ? "Adjudicating…" : "Run now"}
        </Button>
      </div>

      {result?.type === "ok" && (
        <Alert>
          <CheckCircle2 className="size-4" />
          <AlertTitle>{result.message}</AlertTitle>
          {result.counts && result.counts.adjudicated > 0 && (
            <AlertDescription>
              user_right: {result.counts.user_right} · system_right:{" "}
              {result.counts.system_right} · indeterminate:{" "}
              {result.counts.indeterminate}. WhyLibrary entries created for
              every system_right outcome.
            </AlertDescription>
          )}
        </Alert>
      )}

      {result?.type === "error" && (
        <Alert variant="destructive">
          <AlertCircle className="size-4" />
          <AlertTitle>Failed</AlertTitle>
          <AlertDescription>{result.message}</AlertDescription>
        </Alert>
      )}
    </div>
  );
}
