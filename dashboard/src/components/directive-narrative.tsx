/**
 * DirectiveNarrative — renders the upstream-authored prose carried on the
 * directive (rationale + bilateral_evidence). Visually distinct from
 * DirectiveSubstance and explicitly attributed as "generator-authored"
 * so the operator does not mistake it for a derived view of atom state.
 *
 * The directive generator currently emits English summaries
 * (rationale, bilateral_evidence) instead of structured evidence trace.
 * That is upstream A4 drift to retire at the source post-pilot
 * (`adam/intelligence/campaign_intelligence/directive_generator.py`),
 * NOT papered over here. We carry the strings forward unchanged with
 * explicit attribution. The honest move is making the upstream drift
 * legible at the visible surface, not laundering it into the
 * Confident/Uncertain/Possibly-Wrong slots where a future reader would
 * read it as derived.
 */

import { Quote } from "lucide-react";

import type { RecommendationDetail } from "@/lib/types";

export function DirectiveNarrative({
  recommendation,
}: {
  recommendation: RecommendationDetail;
}) {
  if (recommendation.source !== "dcil") {
    return null;
  }
  if (
    !recommendation.directive_rationale &&
    !recommendation.directive_bilateral_evidence
  ) {
    return null;
  }

  return (
    <section className="rounded-lg border border-dashed bg-muted/30 p-5">
      <header className="mb-3 flex items-center gap-2">
        <Quote className="size-4 text-muted-foreground" />
        <h3 className="text-sm font-semibold tracking-tight">
          Directive narrative
        </h3>
        <span className="ml-2 rounded bg-muted px-1.5 py-0.5 text-[10px] uppercase tracking-wide text-muted-foreground">
          generator-authored
        </span>
      </header>

      <p className="mb-4 text-xs text-muted-foreground">
        Upstream prose composed by the directive generator. Carried
        through unchanged and attributed; not a derived view of atom
        state. The structural facts that matter for the decision are
        in the panels above.
      </p>

      <div className="flex flex-col gap-3 text-sm">
        {recommendation.directive_rationale && (
          <NarrativeBlock
            label="Rationale"
            text={recommendation.directive_rationale}
          />
        )}
        {recommendation.directive_bilateral_evidence && (
          <NarrativeBlock
            label="Bilateral evidence"
            text={recommendation.directive_bilateral_evidence}
          />
        )}
      </div>
    </section>
  );
}

function NarrativeBlock({ label, text }: { label: string; text: string }) {
  return (
    <div>
      <div className="mb-1 text-xs uppercase tracking-wide text-muted-foreground">
        {label}
      </div>
      <blockquote className="border-l-2 border-muted-foreground/30 pl-3 italic leading-relaxed text-foreground/90">
        {text}
      </blockquote>
    </div>
  );
}
