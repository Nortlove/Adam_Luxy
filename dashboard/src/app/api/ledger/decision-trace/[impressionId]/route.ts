/**
 * Q.2.B BFF — proxies decision-trace lookup to FastAPI with the
 * server-side bearer token.
 *
 * impressionId is decoded then re-encoded for symmetry with the
 * recommendations [id] handling pattern.
 */

import { NextResponse } from "next/server";
import { ApiError, apiFetch } from "@/lib/api";
import type { DecisionTraceDetailResponse } from "@/lib/types";

export const dynamic = "force-dynamic";

export async function GET(
  _request: Request,
  context: { params: Promise<{ impressionId: string }> },
) {
  const { impressionId } = await context.params;
  const safeId = encodeURIComponent(decodeURIComponent(impressionId));
  const path = `/api/dashboard/ledger/decision-trace/${safeId}`;

  try {
    const data = await apiFetch<DecisionTraceDetailResponse>(path);
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
        error: err instanceof Error ? err.message : "Unknown proxy error",
      },
      { status: 502 },
    );
  }
}
