/**
 * Next.js route handler — proxies the client's acknowledge/decline on a
 * recommendation to the FastAPI backend, carrying the server-side bearer
 * token so the client never sees it.
 *
 * Backend idempotency: re-clicks return the prior decision rather than
 * creating duplicates, so the UI can be optimistic without worrying
 * about double-writes.
 */

import { NextResponse } from "next/server";
import { ApiError, apiFetch } from "@/lib/api";
import type {
  ClientRecommendationDecisionRequest,
  ClientRecommendationDecisionResponse,
} from "@/lib/types";

export const dynamic = "force-dynamic";

export async function POST(
  request: Request,
  { params }: { params: Promise<{ recId: string }> },
) {
  const { recId } = await params;
  if (!recId) {
    return NextResponse.json(
      { error: "recId required" },
      { status: 400 },
    );
  }

  let body: ClientRecommendationDecisionRequest;
  try {
    body = (await request.json()) as ClientRecommendationDecisionRequest;
  } catch {
    return NextResponse.json(
      { error: "Invalid JSON body" },
      { status: 400 },
    );
  }

  try {
    const data = await apiFetch<ClientRecommendationDecisionResponse>(
      `/api/dashboard/client/recommendations/${encodeURIComponent(
        recId,
      )}/decide`,
      { method: "POST", body },
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
