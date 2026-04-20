"use server";

/**
 * Server actions for recommendation decisions. Runs server-side so
 * the Bearer token stays off the client. Returns a plain object the
 * client component can branch on.
 */

import { revalidatePath } from "next/cache";
import { ApiError, api } from "@/lib/api";
import type {
  UserDecisionRequest,
  UserDecisionResponse,
} from "@/lib/types";

export type DecideResult =
  | { ok: true; decision: UserDecisionResponse }
  | { ok: false; status: number; message: string };

export async function decideRecommendation(
  recommendationId: string,
  request: UserDecisionRequest,
): Promise<DecideResult> {
  try {
    const decision = await api.post<UserDecisionResponse>(
      `/api/dashboard/recommendations/${encodeURIComponent(recommendationId)}/decide`,
      request,
    );
    revalidatePath(`/recommendations/${recommendationId}`);
    revalidatePath("/recommendations");
    return { ok: true, decision };
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
