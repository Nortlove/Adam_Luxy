/**
 * Q.2.B — small badge indicating the data_source_state of a Cut B
 * reporting surface. Visualizes substrate-vs-data wiring state honestly
 * so the operator sees Aura/Redis presence at a glance.
 *
 * States:
 *   - populated: green — data flowing
 *   - partial:   amber — substrate wired, some sources missing
 *   - empty:     muted — substrate wired, no observations yet
 *   - found:     green — single-record lookup hit
 *   - not_found: muted — single-record lookup miss
 */

import { Badge } from "@/components/ui/badge";

export type DataSourceStateBadgeProps = {
  state: "populated" | "partial" | "empty" | "found" | "not_found";
};

const VARIANT_BY_STATE: Record<
  DataSourceStateBadgeProps["state"],
  { label: string; className: string }
> = {
  populated: {
    label: "Populated",
    className:
      "border-emerald-300 bg-emerald-100 text-emerald-900 dark:border-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-200",
  },
  partial: {
    label: "Partial",
    className:
      "border-amber-300 bg-amber-100 text-amber-900 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-200",
  },
  empty: {
    label: "Empty",
    className:
      "border-border bg-muted text-muted-foreground",
  },
  found: {
    label: "Found",
    className:
      "border-emerald-300 bg-emerald-100 text-emerald-900 dark:border-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-200",
  },
  not_found: {
    label: "Not found",
    className:
      "border-border bg-muted text-muted-foreground",
  },
};

export function DataSourceStateBadge({ state }: DataSourceStateBadgeProps) {
  const v = VARIANT_BY_STATE[state];
  return (
    <Badge variant="outline" className={`text-[10px] uppercase ${v.className}`}>
      {v.label}
    </Badge>
  );
}
