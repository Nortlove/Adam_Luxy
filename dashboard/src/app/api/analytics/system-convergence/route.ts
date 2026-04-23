/**
 * Next.js route handler — proxies system-convergence query to FastAPI
 * with the server-side bearer token. Internal surface; no client-facing
 * exposure.
 */

import { NextResponse } from "next/server";
import { ApiError, apiFetch } from "@/lib/api";
import type { SystemConvergenceResponse } from "@/lib/types";

export const dynamic = "force-dynamic";

export async function GET() {
  try {
    const data = await apiFetch<SystemConvergenceResponse>(
      "/api/dashboard/system/convergence",
    );
    return NextResponse.json(data);
  } catch (err) {
    if (err instanceof ApiError) {
      return NextResponse.json(
        { error: err.message, status: err.status, payload: err.payload },
        { status: err.status },
      );
    }
    return NextResponse.json(
      {
        error:
          err instanceof Error ? err.message : "Unknown proxy error",
      },
      { status: 502 },
    );
  }
}
