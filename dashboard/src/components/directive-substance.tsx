/**
 * DirectiveSubstance — renders the structural fields of a DCIL directive
 * as a derived view, not as composed interpretation. Per orientation A4:
 * the panel surfaces what is structurally true (parameter, value diff,
 * i², expected lift, generator confidence, rollback conditions) with
 * structural labels. It does NOT compose interpretive prose like
 * "i² is low so this proposal generalizes" — interpretation is the
 * operator's, not the rendering layer's.
 *
 * Rendered only for source="dcil" recommendations and only when at least
 * one structural field is populated. Threshold-source recommendations
 * carry no directive substance — their evidence panel IS their substance.
 */

import { ArrowRight, ShieldAlert } from "lucide-react";

import type { RecommendationDetail } from "@/lib/types";
import { Badge } from "@/components/ui/badge";

export function DirectiveSubstance({
  recommendation,
}: {
  recommendation: RecommendationDetail;
}) {
  if (recommendation.source !== "dcil") {
    return null;
  }

  const hasStructural =
    recommendation.parameter !== null ||
    recommendation.current_value !== null ||
    recommendation.proposed_value !== null ||
    recommendation.i_squared !== null ||
    recommendation.expected_lift_pct !== null ||
    recommendation.generator_confidence !== null ||
    recommendation.rollback_conditions.length > 0;

  if (!hasStructural) {
    return null;
  }

  return (
    <section className="rounded-lg border border-primary/30 bg-primary/5 p-5">
      <header className="mb-4 flex items-center justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold tracking-tight">
            Directive substance
          </h3>
          <p className="mt-0.5 text-xs text-muted-foreground">
            Structural fields from the DCIL directive. Each value is a
            measurement, not an interpretation.
          </p>
        </div>
        <Badge variant="outline" className="text-[10px] uppercase tracking-wide">
          source · DCIL
        </Badge>
      </header>

      <dl className="grid gap-x-6 gap-y-3 text-sm sm:grid-cols-2">
        {recommendation.parameter && (
          <Row label="Parameter">
            <code className="rounded bg-muted px-1.5 py-0.5 font-mono text-xs">
              {recommendation.parameter}
            </code>
          </Row>
        )}

        {(recommendation.current_value !== null ||
          recommendation.proposed_value !== null) && (
          <Row label="Value change">
            <span className="flex items-center gap-2">
              <ValueChip value={recommendation.current_value} muted />
              <ArrowRight className="size-3 text-muted-foreground" />
              <ValueChip value={recommendation.proposed_value} />
            </span>
          </Row>
        )}

        {recommendation.i_squared !== null && (
          <Row label="i² (heterogeneity)">
            <span className="font-mono">
              {recommendation.i_squared.toFixed(0)}%
            </span>
          </Row>
        )}

        {recommendation.expected_lift_pct !== null && (
          <Row label="Expected lift">
            <span className="font-mono">
              {recommendation.expected_lift_pct >= 0 ? "+" : ""}
              {recommendation.expected_lift_pct.toFixed(1)}%
            </span>
          </Row>
        )}

        {recommendation.generator_confidence !== null && (
          <Row label="Generator confidence">
            <span className="font-mono">
              {recommendation.generator_confidence.toFixed(2)}
            </span>
          </Row>
        )}
      </dl>

      {recommendation.rollback_conditions.length > 0 && (
        <div className="mt-5 border-t border-primary/20 pt-4">
          <div className="mb-2 flex items-center gap-2">
            <ShieldAlert className="size-4 text-amber-600 dark:text-amber-400" />
            <h4 className="text-xs font-semibold uppercase tracking-wide text-amber-700 dark:text-amber-400">
              Rollback conditions
            </h4>
          </div>
          <p className="mb-2 text-xs text-muted-foreground">
            Forward statements declared by the generator: this directive is
            wrong if any of these conditions fires after execution.
            Adjudicated at horizon expiry.
          </p>
          <ul className="flex flex-col gap-1.5 text-sm">
            {recommendation.rollback_conditions.map((c, i) => (
              <li key={i} className="flex items-start gap-2">
                <span className="mt-1 size-1.5 shrink-0 rounded-full bg-amber-500" />
                <span>{c}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}

function Row({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex items-baseline gap-3">
      <dt className="w-40 shrink-0 text-xs uppercase tracking-wide text-muted-foreground">
        {label}
      </dt>
      <dd className="flex-1">{children}</dd>
    </div>
  );
}

function ValueChip({
  value,
  muted = false,
}: {
  value: unknown;
  muted?: boolean;
}) {
  const formatted = formatValue(value);
  return (
    <code
      className={`rounded px-1.5 py-0.5 font-mono text-xs ${
        muted
          ? "bg-muted text-muted-foreground"
          : "bg-primary/10 text-foreground"
      }`}
    >
      {formatted}
    </code>
  );
}

function formatValue(value: unknown): string {
  if (value === null || value === undefined) return "—";
  if (typeof value === "number")
    return Number.isInteger(value)
      ? value.toLocaleString()
      : value.toLocaleString(undefined, { maximumFractionDigits: 4 });
  if (typeof value === "string") return value;
  if (typeof value === "boolean") return value ? "true" : "false";
  if (Array.isArray(value))
    return "[" + value.map((v) => formatValue(v)).join(", ") + "]";
  if (typeof value === "object")
    return Object.entries(value as Record<string, unknown>)
      .map(([k, v]) => `${k}=${formatValue(v)}`)
      .join(", ");
  return String(value);
}
