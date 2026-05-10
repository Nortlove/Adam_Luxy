"use client";

/**
 * Q.2.B — recommendation cell-context panel.
 *
 * Composes onto the [id] drill-down view to show cell-conditional
 * substrate context for the underlying decision (cluster, archetype,
 * predicates fired, modulations applied).
 *
 * RecommendationDetail does NOT currently expose impression_id linkage
 * to the underlying DecisionTrace — sibling slice required (Q.2.A.bis).
 * Until that lands, this panel renders an empty-state explaining the
 * dependency. When the linkage exists, this panel will fetch the
 * decision-trace and render a compact summary.
 */

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

export function RecommendationCellContextPanel({
  impressionId,
}: {
  impressionId: string | null | undefined;
}) {
  // The recommendation API doesn't expose impression_id today, so this
  // panel renders the empty-state by default. When Q.2.A.bis ships
  // recommendation→impression linkage, the parent will pass impressionId
  // and this panel will swap to a fetch+render path against
  // /api/ledger/decision-trace/{impressionId}.
  if (!impressionId) {
    return (
      <Card className="border-dashed">
        <CardHeader>
          <CardTitle className="text-base">Cell context</CardTitle>
          <CardDescription>
            Cell context unavailable for this recommendation.{" "}
            <span className="font-mono">RecommendationDetail</span> doesn&rsquo;t
            expose <span className="font-mono">impression_id</span> linkage to
            the underlying <span className="font-mono">DecisionTrace</span>.
            A sibling slice (Q.2.A.bis) wires the linkage; this panel
            populates once that lands.
          </CardDescription>
        </CardHeader>
        <CardContent />
      </Card>
    );
  }

  // When impressionId is available (post-Q.2.A.bis), this would render
  // a compact DecisionTraceDetailView pulling /api/ledger/decision-trace/{id}.
  // Linking out is the simpler v1 — operator clicks through to the
  // ledger lookup with the id pre-filled.
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base">Cell context</CardTitle>
        <CardDescription>
          This recommendation traces back to impression{" "}
          <span className="font-mono">{impressionId}</span>. Open in the
          Dialogue Ledger for the full per-decision audit trail.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <a
          className="text-sm underline underline-offset-2"
          href={`/ledger?impression_id=${encodeURIComponent(impressionId)}`}
        >
          Open trace in Ledger →
        </a>
      </CardContent>
    </Card>
  );
}
