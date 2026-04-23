/**
 * Next.js route handler — proxies the mechanism-effectiveness query to the
 * FastAPI backend with the server-side bearer token.
 *
 * The client component `mechanism-effectiveness.tsx` fetches `/api/learning/
 * mechanism-effectiveness?archetype_id=...&barrier=...` from the browser;
 * that hits this handler; this handler forwards to the backend's
 * `/api/dashboard/learning/mechanism-effectiveness` with `Authorization:
 * Bearer <INFORMATIV_API_TOKEN>`. The bearer token never reaches the
 * browser.
 *
 * Thin — no business logic here. If the backend needs tenant scoping or
 * additional filtering, that lands in the FastAPI endpoint, not here.
 */

import { NextResponse } from "next/server";
import { ApiError, apiFetch } from "@/lib/api";
import type { MechanismEffectivenessResponse } from "@/lib/types";

export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  const incoming = new URL(request.url);
  const archetype = incoming.searchParams.get("archetype_id") ?? "";
  const barrier = incoming.searchParams.get("barrier") ?? "";

  const outgoing = new URLSearchParams();
  if (archetype) outgoing.set("archetype_id", archetype);
  if (barrier) outgoing.set("barrier", barrier);
  const query = outgoing.toString();
  const path =
    `/api/dashboard/learning/mechanism-effectiveness` +
    (query ? `?${query}` : "");

  try {
    const data = await apiFetch<MechanismEffectivenessResponse>(path);
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
