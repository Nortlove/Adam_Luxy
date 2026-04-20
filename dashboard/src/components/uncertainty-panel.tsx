/**
 * Uncertainty Panel — the core visual primitive of the HMT architecture.
 *
 * For every AI recommendation, renders a structured breakdown of what
 * the system is confident about, what it's uncertain about, and what
 * it might be wrong about. Per HMT Foundation §7.1 and §11.1:
 * explanation is signal-level, not confidence-level. Rationale names
 * the edges, atoms, and evidence counts that produced the decision —
 * never a bare percentage.
 */

import { CheckCircle2, CircleHelp, AlertTriangle } from "lucide-react";
import type { UncertaintyBreakdown } from "@/lib/types";

export function UncertaintyPanel({ evidence }: { evidence: UncertaintyBreakdown }) {
  return (
    <div className="grid gap-4 lg:grid-cols-3">
      <Column
        title="Confident"
        icon={CheckCircle2}
        accent="text-emerald-600 dark:text-emerald-400"
        border="border-emerald-200 dark:border-emerald-900"
        description="Strong evidence. Not a belief — an observation."
      >
        {evidence.confident.length === 0 ? (
          <EmptyNote>No confident claims surfaced for this recommendation.</EmptyNote>
        ) : (
          <ul className="flex flex-col gap-3">
            {evidence.confident.map((c, i) => (
              <li key={i} className="text-sm">
                <div className="font-medium leading-snug">{c.claim}</div>
                {c.sources.length > 0 && (
                  <ul className="mt-1 flex flex-col gap-0.5 text-xs text-muted-foreground">
                    {c.sources.map((s, j) => (
                      <li key={j}>· {s}</li>
                    ))}
                  </ul>
                )}
              </li>
            ))}
          </ul>
        )}
      </Column>

      <Column
        title="Uncertain"
        icon={CircleHelp}
        accent="text-amber-600 dark:text-amber-400"
        border="border-amber-200 dark:border-amber-900"
        description="What's missing. The specific signal that would reduce the doubt."
      >
        {evidence.uncertain.length === 0 ? (
          <EmptyNote>No significant uncertainty flagged.</EmptyNote>
        ) : (
          <ul className="flex flex-col gap-3">
            {evidence.uncertain.map((u, i) => (
              <li key={i} className="text-sm">
                <div className="font-medium leading-snug">{u.claim}</div>
                <div className="mt-1 text-xs text-muted-foreground">
                  <span className="uppercase tracking-wide">missing:</span>{" "}
                  {u.missing}
                </div>
                {u.would_reduce && (
                  <div className="mt-1 text-xs text-muted-foreground">
                    <span className="uppercase tracking-wide">would reduce:</span>{" "}
                    {u.would_reduce}
                  </div>
                )}
              </li>
            ))}
          </ul>
        )}
      </Column>

      <Column
        title="Possibly wrong"
        icon={AlertTriangle}
        accent="text-rose-600 dark:text-rose-400"
        border="border-rose-200 dark:border-rose-900"
        description="Where the evidence disagrees with the recommendation."
      >
        {evidence.possibly_wrong.length === 0 ? (
          <EmptyNote>No conflicting signals detected.</EmptyNote>
        ) : (
          <ul className="flex flex-col gap-3">
            {evidence.possibly_wrong.map((p, i) => (
              <li key={i} className="text-sm">
                <div className="font-medium leading-snug">{p.claim}</div>
                <div className="mt-1 text-xs text-muted-foreground">
                  <span className="uppercase tracking-wide">conflicting signal:</span>{" "}
                  {p.conflicting_signal}
                </div>
                {p.alternative && (
                  <div className="mt-1 text-xs text-muted-foreground">
                    <span className="uppercase tracking-wide">alternative:</span>{" "}
                    {p.alternative}
                  </div>
                )}
              </li>
            ))}
          </ul>
        )}
      </Column>
    </div>
  );
}

function Column({
  title,
  icon: Icon,
  accent,
  border,
  description,
  children,
}: {
  title: string;
  icon: React.ComponentType<{ className?: string }>;
  accent: string;
  border: string;
  description: string;
  children: React.ReactNode;
}) {
  return (
    <div className={`rounded-lg border bg-card p-4 ${border}`}>
      <div className="mb-3 flex items-center gap-2">
        <Icon className={`size-4 ${accent}`} />
        <h3 className={`text-sm font-semibold ${accent}`}>{title}</h3>
      </div>
      <p className="mb-3 text-xs text-muted-foreground">{description}</p>
      {children}
    </div>
  );
}

function EmptyNote({ children }: { children: React.ReactNode }) {
  return (
    <p className="text-xs italic text-muted-foreground">{children}</p>
  );
}
