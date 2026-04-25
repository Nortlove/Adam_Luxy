/**
 * DeviationContext — renders the structural state of the deviation
 * underlying a horizon adjudication. Parallel in shape to
 * DirectiveSubstance: structural fields rendered as labeled
 * measurements, no interpretive prose composed by the rendering layer.
 *
 * The operator's task on a horizon-source recommendation is JUDGMENT —
 * was the system right, was the operator right, or is the evidence
 * inconclusive — not authorship of a new proposal. This panel surfaces
 * what they're judging:
 *   - The system's recommended choice at decide time.
 *   - The operator's actual choice (the deviation).
 *   - How long has elapsed since the deviation was logged.
 *   - The operator's stated rationale at decide time (operator-authored,
 *     attributed) — surfaced as their recorded hypothesis, not as
 *     interpretation. A2 honesty: the rationale was the operator's
 *     decision-time claim; rendering it preserves the original frame.
 *
 * Rendered only for source="horizon_adjudication" with deviation_context
 * populated. Returns null otherwise — no empty containers.
 */

import { ArrowRight, Clock, MessageSquare, User } from "lucide-react";

import type { RecommendationDetail } from "@/lib/types";
import { Badge } from "@/components/ui/badge";

export function DeviationContextPanel({
  recommendation,
}: {
  recommendation: RecommendationDetail;
}) {
  if (recommendation.source !== "horizon_adjudication") {
    return null;
  }
  const ctx = recommendation.deviation_context;
  if (!ctx) {
    return null;
  }

  return (
    <section className="rounded-lg border border-amber-300/50 bg-amber-50/40 p-5 dark:border-amber-800/50 dark:bg-amber-950/20">
      <header className="mb-4 flex items-center justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold tracking-tight">
            Deviation under judgment
          </h3>
          <p className="mt-0.5 text-xs text-muted-foreground">
            Structural state of the deviation. Verdict gates Loop B
            theory update.
          </p>
        </div>
        <Badge
          variant="outline"
          className="border-amber-500 text-amber-700 dark:text-amber-400 text-[10px] uppercase tracking-wide"
        >
          source · horizon ready
        </Badge>
      </header>

      <dl className="grid gap-x-6 gap-y-3 text-sm sm:grid-cols-2">
        <Row label="Deviation ID">
          <code className="rounded bg-muted px-1.5 py-0.5 font-mono text-xs">
            {ctx.deviation_id}
          </code>
        </Row>

        <Row label="Choice diff">
          <span className="flex items-center gap-2">
            <ChoiceChip label="system" value={ctx.system_choice} muted />
            <ArrowRight className="size-3 text-muted-foreground" />
            <ChoiceChip label="operator" value={ctx.user_choice ?? "—"} />
          </span>
        </Row>

        <Row label="Time elapsed">
          <span className="flex items-center gap-1.5">
            <Clock className="size-3 text-muted-foreground" />
            <span className="font-mono">
              {ctx.days_elapsed.toFixed(1)} days
            </span>
            <span className="text-xs text-muted-foreground">
              (window: {ctx.horizon_window_days.toFixed(0)} days, class:{" "}
              {ctx.horizon_class})
            </span>
          </span>
        </Row>

        {ctx.rationale_class && (
          <Row label="Rationale class">
            <span className="font-mono text-xs">{ctx.rationale_class}</span>
          </Row>
        )}
      </dl>

      {ctx.stated_rationale && (
        <div className="mt-5 border-t border-amber-200/40 pt-4 dark:border-amber-800/30">
          <div className="mb-2 flex items-center gap-2">
            <MessageSquare className="size-4 text-muted-foreground" />
            <h4 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              Operator rationale at decide time
            </h4>
            <Badge
              variant="outline"
              className="text-[10px] uppercase tracking-wide"
            >
              <User className="mr-1 size-2.5" />
              operator-authored
            </Badge>
          </div>
          <blockquote className="border-l-2 border-amber-400/40 pl-3 italic leading-relaxed text-foreground/90">
            {ctx.stated_rationale}
          </blockquote>
          <p className="mt-2 text-xs text-muted-foreground">
            Recorded as a hypothesis at the time of deviation, not as a
            learning. The verdict below tests it against realized outcome.
          </p>
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
      <dt className="w-32 shrink-0 text-xs uppercase tracking-wide text-muted-foreground">
        {label}
      </dt>
      <dd className="flex-1">{children}</dd>
    </div>
  );
}

function ChoiceChip({
  label,
  value,
  muted = false,
}: {
  label: string;
  value: string;
  muted?: boolean;
}) {
  return (
    <span
      className={`flex items-center gap-1.5 rounded px-1.5 py-0.5 ${
        muted ? "bg-muted text-muted-foreground" : "bg-amber-200/40 text-foreground dark:bg-amber-900/30"
      }`}
    >
      <span className="text-[9px] uppercase tracking-wide opacity-70">
        {label}
      </span>
      <code className="font-mono text-xs">{value}</code>
    </span>
  );
}
