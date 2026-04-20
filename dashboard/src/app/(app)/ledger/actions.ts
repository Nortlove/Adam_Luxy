"use server";

/**
 * Server actions for the Dialogue Ledger. Kept alongside the ledger
 * route so elicitation components can call them from anywhere in the
 * app without exposing the server-side Bearer token.
 */

import { revalidatePath } from "next/cache";
import { ApiError, api } from "@/lib/api";
import type {
  ClaimCreateRequest,
  ClaimResponse,
} from "@/lib/types";

export type SubmitClaimResult =
  | { ok: true; claim: ClaimResponse }
  | { ok: false; status: number; message: string };

export async function submitClaim(
  request: ClaimCreateRequest,
): Promise<SubmitClaimResult> {
  try {
    const claim = await api.post<ClaimResponse>(
      "/api/dashboard/ledger/claims",
      request,
    );
    revalidatePath("/ledger");
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
