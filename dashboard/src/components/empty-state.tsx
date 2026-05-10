/**
 * Q.2.B — shared empty-state component for cell-conditional reporting
 * surfaces. Renders a dashed-border Card with title + description for
 * "no data yet" contexts.
 *
 * Used by all 5 Cut B panels (per-cluster fire rate, per-archetype
 * performance, per-cohort outcome correlation, loop dispatch rates,
 * decision-trace detail not_found state).
 */

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export type EmptyStateProps = {
  title?: string;
  description?: string;
  className?: string;
};

export function EmptyState({
  title = "No data yet",
  description = "Substrate is wired but no observations have flowed through yet. This panel will populate as decisions accumulate.",
  className,
}: EmptyStateProps) {
  return (
    <Card className={`border-dashed ${className ?? ""}`}>
      <CardHeader>
        <CardTitle className="text-base">{title}</CardTitle>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      <CardContent />
    </Card>
  );
}
