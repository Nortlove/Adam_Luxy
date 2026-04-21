"use server";

import { revalidatePath } from "next/cache";
import { ApiError, api } from "@/lib/api";
import type { AdjudicationBatchResponse } from "@/lib/types";

export type AdjudicateResult =
  | { ok: true; batch: AdjudicationBatchResponse }
  | { ok: false; status: number; message: string };

export async function runAdjudicateReady(): Promise<AdjudicateResult> {
  try {
    const batch = await api.post<AdjudicationBatchResponse>(
      "/api/dashboard/deviations/adjudicate-ready",
    );
    revalidatePath("/learning");
    revalidatePath("/ledger");
    return { ok: true, batch };
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
