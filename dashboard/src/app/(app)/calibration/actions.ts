"use server";

import { revalidatePath } from "next/cache";
import { ApiError, api } from "@/lib/api";
import type { ClaimResponse } from "@/lib/types";

export type RecordCalibrationClaimResult =
  | { ok: true; claim: ClaimResponse }
  | { ok: false; status: number; message: string };

/**
 * Record a calibration-training answer as a stated_confidence Claim
 * in the Dialogue Ledger. Enters with status=hypothesis like any
 * other claim but carries an explicit stated_confidence for later
 * Brier-score aggregation.
 */
export async function recordCalibrationClaim(args: {
  scenarioId: string;
  category: string;
  prompt: string;
  userProbability: number;
  actualOutcome: "true" | "false";
  brierContribution: number;
  latencyMs: number;
  sessionId: string;
}): Promise<RecordCalibrationClaimResult> {
  try {
    const text =
      `[calibration:${args.scenarioId}] stated ${(args.userProbability * 100).toFixed(0)}% · ` +
      `actual ${args.actualOutcome} · brier ${args.brierContribution.toFixed(3)} · ` +
      `"${args.prompt}"`;
    const claim = await api.post<ClaimResponse>(
      "/api/dashboard/ledger/claims",
      {
        text,
        elicitation_mode: "spies",
        domain: `calibration.${args.category}`,
        stated_confidence: args.userProbability,
        latency_ms: args.latencyMs,
        frame: "neutral",
        session_id: args.sessionId,
      },
    );
    return { ok: true, claim };
  } catch (err) {
    if (err instanceof ApiError) {
      return { ok: false, status: err.status, message: err.message };
    }
    return {
      ok: false,
      status: 0,
      message: err instanceof Error ? err.message : "Unknown error",
    };
  }
}

export async function refreshLedger() {
  revalidatePath("/ledger");
}
