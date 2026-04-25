import Link from "next/link";
import { notFound } from "next/navigation";
import { ArrowLeft, Check } from "lucide-react";

import { ApiError, api } from "@/lib/api";
import type { RecommendationDetail } from "@/lib/types";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { PageHeader } from "@/components/page-header";
import { UncertaintyPanel } from "@/components/uncertainty-panel";
import { RecommendationDecide } from "@/components/recommendation-decide";
import { DirectiveSubstance } from "@/components/directive-substance";
import { DirectiveNarrative } from "@/components/directive-narrative";
import { SourceBadge } from "@/components/source-badge";

export const dynamic = "force-dynamic";

type PageProps = {
  params: Promise<{ id: string }>;
};

async function loadRecommendation(id: string): Promise<RecommendationDetail | null> {
  try {
    return await api.get<RecommendationDetail>(
      `/api/dashboard/recommendations/${encodeURIComponent(id)}`,
    );
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) {
      return null;
    }
    throw err;
  }
}

export async function generateMetadata({ params }: PageProps) {
  const { id } = await params;
  const rec = await loadRecommendation(id).catch(() => null);
  return {
    title: rec ? `${rec.title} · INFORMATIV` : "Recommendation · INFORMATIV",
  };
}

export default async function RecommendationDetailPage({ params }: PageProps) {
  const { id } = await params;
  const rec = await loadRecommendation(id);
  if (!rec) {
    notFound();
  }

  return (
    <div className="flex flex-col gap-6 p-6">
      <div>
        <Link
          href="/recommendations"
          className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="size-4" />
          back to recommendations
        </Link>
      </div>

      <PageHeader title={rec.title} description={rec.summary} />

      <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
        <SourceBadge source={rec.source} />
        <Badge variant="outline">{rec.type.replace(/_/g, " ")}</Badge>
        <span>horizon: {rec.expected_horizon_class}</span>
        {rec.campaign_name && (
          <>
            <span>·</span>
            <span>campaign: {rec.campaign_name}</span>
          </>
        )}
        <span>·</span>
        <span>created {new Date(rec.created_at).toLocaleString()}</span>
      </div>

      {/* DIRECTIVE SUBSTANCE — structural fields for source="dcil" only.
          Rendered above "the plan" so the operator reads the structural
          state of the proposal before evaluating alternatives. Threshold-
          source recommendations skip this section (their evidence panel
          IS their substance). */}
      <DirectiveSubstance recommendation={rec} />

      {/* PLAN — preferred choice + alternatives (plan-before-patch) */}
      <section className="flex flex-col gap-3">
        <div>
          <h2 className="text-lg font-semibold tracking-tight">
            The plan
          </h2>
          <p className="text-sm text-muted-foreground">
            The preferred choice, annotated. Accept, modify, or reject — with
            reasons captured as hypotheses for later adjudication.
          </p>
        </div>
        <div className="grid gap-3 md:grid-cols-3">
          {rec.alternatives.map((alt) => {
            const isPreferred = alt.id === rec.preferred_choice;
            return (
              <Card
                key={alt.id}
                className={
                  isPreferred
                    ? "border-primary bg-primary/5"
                    : "border-dashed"
                }
              >
                <CardHeader>
                  <CardTitle className="flex items-center justify-between gap-2 text-base">
                    <span>{alt.label}</span>
                    {isPreferred && (
                      <Badge>
                        <Check className="mr-1 size-3" /> preferred
                      </Badge>
                    )}
                  </CardTitle>
                  <CardDescription>{alt.description}</CardDescription>
                </CardHeader>
                {alt.predicted_outcome && (
                  <CardContent className="pt-0 text-sm">
                    <div className="text-xs uppercase text-muted-foreground">
                      Predicted outcome
                    </div>
                    <div className="mt-1">{alt.predicted_outcome}</div>
                  </CardContent>
                )}
              </Card>
            );
          })}
        </div>
      </section>

      <Separator />

      {/* UNCERTAINTY PANEL — the core HMT surface */}
      <section className="flex flex-col gap-3">
        <div>
          <h2 className="text-lg font-semibold tracking-tight">
            Why — signal-level rationale
          </h2>
          <p className="text-sm text-muted-foreground">
            What the system is confident about, what it&rsquo;s uncertain
            about, and where the evidence disagrees with the recommendation.
            Signal-level, not a confidence percentage.
          </p>
        </div>
        <UncertaintyPanel evidence={rec.evidence} />
      </section>

      {/* DIRECTIVE NARRATIVE — upstream-authored prose carried with
          explicit attribution. Visually distinct from the structural
          panels above. Slice B carries upstream A4 honestly rather
          than papering over it; the source-side fix lives in
          adam/intelligence/campaign_intelligence/directive_generator.py
          (post-pilot). */}
      <DirectiveNarrative recommendation={rec} />

      <Separator />

      {/* DECIDE — accept / modify / reject with deviation capture */}
      <section className="flex flex-col gap-3">
        <div>
          <h2 className="text-lg font-semibold tracking-tight">
            Your decision
          </h2>
          <p className="text-sm text-muted-foreground">
            Deviations capture your rationale as a hypothesis — tested
            against the actual outcome at horizon expiry, never
            auto-promoted to a learning.
          </p>
        </div>
        <RecommendationDecide recommendation={rec} />

        {rec.decisions.length > 1 && (
          <div className="flex flex-col gap-2 rounded-lg border bg-muted/30 p-4">
            <h3 className="text-sm font-semibold">Decision history</h3>
            <ul className="flex flex-col gap-2">
              {rec.decisions.map((d) => (
                <li
                  key={d.id}
                  className="grid grid-cols-[80px_1fr] gap-2 text-xs"
                >
                  <span className="uppercase text-muted-foreground">{d.kind}</span>
                  <span>
                    {d.chosen_alternative ?? "—"} ·{" "}
                    {new Date(d.created_at).toLocaleString()}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </section>

      <Alert>
        <AlertTitle>Reminder</AlertTitle>
        <AlertDescription>
          Accept = commit. Modify = deviation with a specific alternative
          logged. Reject = deviation with no alternative. All three become
          training data for the interaction protocol.
        </AlertDescription>
      </Alert>
    </div>
  );
}
