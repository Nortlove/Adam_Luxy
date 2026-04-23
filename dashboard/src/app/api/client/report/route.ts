/**
 * Next.js route handler — proxies the client report request to the
 * FastAPI backend with the server-side bearer token.
 */

import { NextResponse } from "next/server";
import { ApiError, apiFetch } from "@/lib/api";
import type { ClientReport } from "@/lib/types";

export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  const incoming = new URL(request.url);
  const advertiserId = incoming.searchParams.get("advertiser_id") ?? "";

  const outgoing = new URLSearchParams();
  if (advertiserId) outgoing.set("advertiser_id", advertiserId);
  const query = outgoing.toString();
  const path =
    `/api/dashboard/client/report` + (query ? `?${query}` : "");

  try {
    const data = await apiFetch<ClientReport>(path);
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
