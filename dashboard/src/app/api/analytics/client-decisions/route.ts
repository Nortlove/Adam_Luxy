/**
 * Next.js route handler — proxies the client-decisions audit query to
 * FastAPI with the server-side bearer token. Internal surface.
 */

import { NextResponse } from "next/server";
import { ApiError, apiFetch } from "@/lib/api";
import type { ClientDecisionAuditResponse } from "@/lib/types";

export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  const incoming = new URL(request.url);
  const limit = incoming.searchParams.get("limit") ?? "100";
  try {
    const data = await apiFetch<ClientDecisionAuditResponse>(
      `/api/dashboard/system/client-decisions?limit=${encodeURIComponent(limit)}`,
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
