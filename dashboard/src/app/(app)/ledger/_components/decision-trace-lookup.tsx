"use client";

/**
 * Q.2.B — decision-trace lookup form + result view.
 *
 * User enters an impression_id; submit fetches the decision-trace
 * detail. Empty input or not_found state renders the not-found
 * message; found state renders the DecisionTraceDetailView.
 *
 * Privacy guard: the response's buyer_id_anonymized is the only
 * buyer identifier exposed. No client-side reconstruction.
 */

import { FormEvent, useState } from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { EmptyState } from "@/components/empty-state";
import { DecisionTraceDetailView } from "./decision-trace-detail-view";
import type { DecisionTraceDetailResponse } from "@/lib/types";

export function DecisionTraceLookup() {
  const [impressionId, setImpressionId] = useState<string>("");
  const [submittedId, setSubmittedId] = useState<string | null>(null);
  const [data, setData] = useState<DecisionTraceDetailResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(false);

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const id = impressionId.trim();
    if (!id) return;
    setSubmittedId(id);
    setLoading(true);
    setError(null);
    setData(null);
    try {
      const res = await fetch(
        `/api/ledger/decision-trace/${encodeURIComponent(id)}`,
        { cache: "no-store" },
      );
      if (!res.ok) {
        const body = (await res.json().catch(() => null)) as
          | { error?: string }
          | null;
        throw new Error(body?.error ?? `Request failed (HTTP ${res.status})`);
      }
      const json = (await res.json()) as DecisionTraceDetailResponse;
      setData(json);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">Decision trace lookup</CardTitle>
          <CardDescription>
            Enter an <span className="font-mono">impression_id</span> to fetch
            the per-decision audit trail. Reads Redis hot first, Neo4j
            archive on miss. Buyer IDs are anonymized via SHA-256 prefix.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={onSubmit} className="flex flex-col gap-3">
            <div className="flex flex-col gap-2">
              <Label htmlFor="impression-id">Impression ID</Label>
              <Input
                id="impression-id"
                placeholder="e.g. dec_4f32b9..."
                value={impressionId}
                onChange={(e) => setImpressionId(e.target.value)}
                disabled={loading}
              />
            </div>
            <div>
              <Button type="submit" disabled={loading || !impressionId.trim()}>
                {loading ? "Looking up…" : "Lookup"}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>

      {error ? (
        <Alert variant="destructive">
          <AlertTitle>Lookup failed</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      ) : null}

      {!loading && submittedId && data?.data_source_state === "not_found" ? (
        <EmptyState
          title="Trace not found"
          description={`No decision trace for impression_id "${submittedId}" in Redis hot cache or Neo4j archive. The impression may be older than the Redis TTL and not yet drained, or the ID may be incorrect.`}
        />
      ) : null}

      {data && data.data_source_state !== "not_found" ? (
        <DecisionTraceDetailView trace={data} />
      ) : null}
    </div>
  );
}
