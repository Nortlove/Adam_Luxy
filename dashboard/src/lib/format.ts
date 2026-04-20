/**
 * Display formatters. Keep these pure and trivial — no locale surprises.
 */

export function formatUsd(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) return "—";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: value >= 1000 ? 0 : 2,
  }).format(value);
}

export function formatInt(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) return "—";
  return new Intl.NumberFormat("en-US").format(Math.round(value));
}

export function formatPercent(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) return "—";
  // StackAdapt CTR is already a fraction (0.0013 = 0.13%)
  return `${(value * 100).toFixed(value * 100 < 1 ? 3 : 2)}%`;
}

export function formatStatus(status: string | null | undefined): string {
  if (!status) return "unknown";
  return status.toLowerCase().replace(/_/g, " ");
}
