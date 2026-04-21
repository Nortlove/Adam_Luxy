"use server";

import { revalidatePath } from "next/cache";
import { ApiError, api } from "@/lib/api";
import type {
  AutopilotSettings,
  AutopilotUpdateRequest,
} from "@/lib/types";

export type UpdateAutopilotResult =
  | { ok: true; settings: AutopilotSettings }
  | { ok: false; status: number; message: string };

export async function updateAutopilot(
  request: AutopilotUpdateRequest,
): Promise<UpdateAutopilotResult> {
  try {
    const settings = await api.put<AutopilotSettings>(
      "/api/dashboard/settings/autopilot",
      request,
    );
    revalidatePath("/settings");
    return { ok: true, settings };
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
