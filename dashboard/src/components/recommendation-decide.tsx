"use client";

/**
 * Client component: Accept / Modify / Reject controls for a
 * recommendation. Captures deviation rationale per HMT Foundation
 * §11.5 — user rationale stored as a HYPOTHESIS, never auto-promoted
 * to a learning (Rule 12).
 */

import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";
import { Check, X, Wrench } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";

import { decideRecommendation } from "@/app/(app)/recommendations/actions";
import type {
  RecommendationDetail,
  DecisionKind,
  RationaleClass,
  UserDecisionRequest,
} from "@/lib/types";

type Mode = "idle" | "accept" | "modify" | "reject";

export function RecommendationDecide({ recommendation }: { recommendation: RecommendationDetail }) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();
  const [mode, setMode] = useState<Mode>("idle");
  const [chosen, setChosen] = useState<string | null>(null);
  const [rationaleClass, setRationaleClass] = useState<RationaleClass | null>(null);
  const [rationaleText, setRationaleText] = useState("");
  const [error, setError] = useState<string | null>(null);

  const alreadyDecided = recommendation.decisions.length > 0;

  if (alreadyDecided) {
    const latest = recommendation.decisions[0];
    return (
      <Alert>
        <AlertTitle>
          Decision recorded: {latest.kind}
          {latest.chosen_alternative ? ` → ${latest.chosen_alternative}` : ""}
        </AlertTitle>
        <AlertDescription>
          Logged at {new Date(latest.created_at).toLocaleString()}.
          {latest.rationale_text ? ` Your rationale: "${latest.rationale_text}"` : ""}
        </AlertDescription>
      </Alert>
    );
  }

  async function submit(kind: DecisionKind) {
    setError(null);
    const body: UserDecisionRequest = {
      kind,
      chosen_alternative:
        kind === "accept"
          ? recommendation.preferred_choice
          : kind === "modify"
            ? chosen
            : null,
      rationale_class: kind === "accept" ? null : rationaleClass,
      rationale_text: kind === "accept" ? null : (rationaleText || null),
    };

    if (kind === "modify" && !body.chosen_alternative) {
      setError("Pick which alternative you want to go with.");
      return;
    }

    startTransition(async () => {
      const result = await decideRecommendation(recommendation.id, body);
      if (!result.ok) {
        setError(
          `Failed to record decision (${result.status || "network"}). ${result.message}`,
        );
        return;
      }
      router.refresh();
    });
  }

  return (
    <div className="flex flex-col gap-4">
      {mode === "idle" && (
        <div className="flex flex-wrap gap-3">
          <Button
            onClick={() => {
              setMode("accept");
              submit("accept");
            }}
            disabled={pending}
          >
            <Check className="mr-1 size-4" /> Accept preferred
          </Button>
          <Button
            variant="secondary"
            onClick={() => setMode("modify")}
            disabled={pending}
          >
            <Wrench className="mr-1 size-4" /> Modify
          </Button>
          <Button
            variant="outline"
            onClick={() => setMode("reject")}
            disabled={pending}
          >
            <X className="mr-1 size-4" /> Reject
          </Button>
        </div>
      )}

      {mode === "modify" && (
        <DeviationForm
          title="Modify — pick a different alternative"
          alternatives={recommendation.alternatives}
          preferredId={recommendation.preferred_choice}
          chosen={chosen}
          setChosen={setChosen}
          rationaleClass={rationaleClass}
          setRationaleClass={setRationaleClass}
          rationaleText={rationaleText}
          setRationaleText={setRationaleText}
          onCancel={() => setMode("idle")}
          onSubmit={() => submit("modify")}
          pending={pending}
          submitLabel="Record modification"
        />
      )}

      {mode === "reject" && (
        <DeviationForm
          title="Reject — decline the recommendation"
          alternatives={[]}
          preferredId={recommendation.preferred_choice}
          chosen={null}
          setChosen={() => {}}
          rationaleClass={rationaleClass}
          setRationaleClass={setRationaleClass}
          rationaleText={rationaleText}
          setRationaleText={setRationaleText}
          onCancel={() => setMode("idle")}
          onSubmit={() => submit("reject")}
          pending={pending}
          submitLabel="Record rejection"
        />
      )}

      {error && (
        <Alert variant="destructive">
          <AlertTitle>Error</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}
    </div>
  );
}

function DeviationForm({
  title,
  alternatives,
  preferredId,
  chosen,
  setChosen,
  rationaleClass,
  setRationaleClass,
  rationaleText,
  setRationaleText,
  onCancel,
  onSubmit,
  pending,
  submitLabel,
}: {
  title: string;
  alternatives: RecommendationDetail["alternatives"];
  preferredId: string;
  chosen: string | null;
  setChosen: (v: string | null) => void;
  rationaleClass: RationaleClass | null;
  setRationaleClass: (v: RationaleClass | null) => void;
  rationaleText: string;
  setRationaleText: (v: string) => void;
  onCancel: () => void;
  onSubmit: () => void;
  pending: boolean;
  submitLabel: string;
}) {
  return (
    <div className="flex flex-col gap-4 rounded-lg border bg-muted/30 p-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold">{title}</h3>
        <Button variant="ghost" size="sm" onClick={onCancel} disabled={pending}>
          Cancel
        </Button>
      </div>

      {alternatives.length > 0 && (
        <div className="flex flex-col gap-2">
          <Label htmlFor="chosen-alternative">Alternative</Label>
          <Select
            value={chosen ?? ""}
            onValueChange={(v) => setChosen(v)}
          >
            <SelectTrigger id="chosen-alternative">
              <SelectValue placeholder="Pick an alternative" />
            </SelectTrigger>
            <SelectContent>
              {alternatives
                .filter((a) => a.id !== preferredId)
                .map((a) => (
                  <SelectItem key={a.id} value={a.id}>
                    {a.label}
                  </SelectItem>
                ))}
            </SelectContent>
          </Select>
        </div>
      )}

      <div className="flex flex-col gap-2">
        <Label htmlFor="rationale-class">
          Why? (optional but teaches the system)
        </Label>
        <Select
          value={rationaleClass ?? ""}
          onValueChange={(v) => setRationaleClass(v as RationaleClass)}
        >
          <SelectTrigger id="rationale-class">
            <SelectValue placeholder="Select a category" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="idiosyncratic">
              Personal preference — won&rsquo;t generalize
            </SelectItem>
            <SelectItem value="missing_context">
              Context the system didn&rsquo;t have
            </SelectItem>
            <SelectItem value="model_wrong">
              The recommendation is simply wrong
            </SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className="flex flex-col gap-2">
        <Label htmlFor="rationale-text">
          Your rationale (stored as a hypothesis — tested against outcome)
        </Label>
        <Textarea
          id="rationale-text"
          value={rationaleText}
          onChange={(e) => setRationaleText(e.target.value)}
          rows={4}
          placeholder="What does the system not know that you know?"
        />
        <p className="text-xs text-muted-foreground">
          This rationale enters the Dialogue Ledger as a hypothesis. It is
          tested against the actual outcome at horizon expiry — never
          auto-promoted to a learning.
        </p>
      </div>

      <div className="flex justify-end gap-2">
        <Button onClick={onSubmit} disabled={pending}>
          {pending ? "Saving…" : submitLabel}
        </Button>
      </div>
    </div>
  );
}
