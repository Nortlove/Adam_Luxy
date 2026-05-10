/**
 * Q.2.B BFF — proxies loop dispatch rates query to FastAPI with the
 * server-side bearer token.
 */

import { NextResponse } from "next/server";
import { ApiError, apiFetch } from "@/lib/api";
import type { LoopDispatchRatesResponse } from "@/lib/types";

export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  const url = new URL(request.url);
  const search = url.searchParams.toString();
  const path = `/api/dashboard/learning/loop-dispatch-rates${search ? `?${search}` : ""}`;

  try {
    const data = await apiFetch<LoopDispatchRatesResponse>(path);
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
