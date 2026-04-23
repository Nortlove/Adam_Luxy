/**
 * Next.js route handler — proxies the per-subject unified-puzzle
 * inference to the FastAPI backend with the server-side bearer token.
 *
 * Client component `subject-inspection.tsx` fetches
 * `/api/learning/subject/{userId}`; this handler forwards to the backend's
 * `/api/v1/signals/user/{userId}/puzzle` which runs
 * `adam.retargeting.engines.unified_puzzle.infer_person()` — a JOINT
 * inference across all 6 nonconscious signals + bilateral edges +
 * trajectory analysis into one PersonState.
 *
 * Thin. Business logic lives in the backend. This handler's only job is
 * to keep the bearer token off the browser.
 */

import { NextResponse } from "next/server";
import { ApiError, apiFetch } from "@/lib/api";
import type { PersonState } from "@/lib/types";

export const dynamic = "force-dynamic";

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ userId: string }> },
) {
  const { userId } = await params;
  if (!userId) {
    return NextResponse.json({ error: "userId required" }, { status: 400 });
  }

  try {
    const data = await apiFetch<PersonState>(
      `/api/v1/signals/user/${encodeURIComponent(userId)}/puzzle`,
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
