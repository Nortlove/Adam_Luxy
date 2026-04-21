"use client";

/**
 * Autopilot settings — five-mode trust curve with per-decision-class
 * overrides. Per HMT Foundation §10.4 and Part 7: the modes
 * progressively hand autonomy to ADAM; kill_switch never auto-runs,
 * by design.
 */

import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";
import { Check } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";

import type {
  AutopilotMode,
  AutopilotSettings,
  GateKind,
} from "@/lib/types";
import { updateAutopilot } from "../actions";

const MODES: {
  id: AutopilotMode;
  name: string;
  summary: string;
  gates: Record<
    "creative_gate" | "bid_gate" | "audience_gate" | "budget_gate" | "kill_gate",
    GateKind
  >;
}[] = [
  {
    id: "observer",
    name: "Observer",
    summary: "Approve everything. ADAM proposes, you commit.",
    gates: {
      creative_gate: "approve",
      bid_gate: "approve",
      audience_gate: "approve",
      budget_gate: "approve",
      kill_gate: "approve",
    },
  },
  {
    id: "explain",
    name: "Explain",
    summary:
      "Approve almost everything; audience changes notified instead of gated.",
    gates: {
      creative_gate: "approve",
      bid_gate: "approve",
      audience_gate: "notify",
      budget_gate: "approve",
      kill_gate: "approve",
    },
  },
  {
    id: "notify",
    name: "Notify",
    summary:
      "Bid moves run auto. Creative and audience changes are notified; budget + kill still gated.",
    gates: {
      creative_gate: "notify",
      bid_gate: "auto",
      audience_gate: "notify",
      budget_gate: "approve",
      kill_gate: "approve",
    },
  },
  {
    id: "delegate",
    name: "Delegate",
    summary:
      "Most decisions auto. Budget shifts notified; kill switch still approved.",
    gates: {
      creative_gate: "notify",
      bid_gate: "auto",
      audience_gate: "auto",
      budget_gate: "notify",
      kill_gate: "approve",
    },
  },
  {
    id: "autopilot",
    name: "Autopilot",
    summary:
      "ADAM runs the campaign. Kill switch is still yours — never delegated.",
    gates: {
      creative_gate: "auto",
      bid_gate: "auto",
      audience_gate: "auto",
      budget_gate: "auto",
      kill_gate: "approve",
    },
  },
];

const GATE_LABELS: Record<GateKind, { label: string; tone: string }> = {
  approve: { label: "Approve", tone: "text-rose-600 dark:text-rose-400" },
  notify: { label: "Notify", tone: "text-amber-600 dark:text-amber-400" },
  auto: { label: "Auto", tone: "text-emerald-600 dark:text-emerald-400" },
};

export function AutopilotPanel({ current }: { current: AutopilotSettings }) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);
  const [lastApplied, setLastApplied] = useState<AutopilotMode>(current.mode);

  function switchTo(mode: AutopilotMode) {
    setError(null);
    startTransition(async () => {
      const result = await updateAutopilot({ mode });
      if (!result.ok) {
        setError(`Failed (${result.status}). ${result.message}`);
        return;
      }
      setLastApplied(mode);
      router.refresh();
    });
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          Autopilot
          <Badge variant="secondary" className="capitalize">
            {current.mode}
          </Badge>
        </CardTitle>
        <CardDescription>
          Five-mode trust curve with per-decision-class overrides. Kill
          switch is never delegated — by design.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <div className="grid gap-3 lg:grid-cols-5">
          {MODES.map((m) => (
            <ModeCard
              key={m.id}
              mode={m}
              active={current.mode === m.id}
              applied={lastApplied === m.id}
              disabled={pending}
              onSelect={() => switchTo(m.id)}
            />
          ))}
        </div>

        <div className="grid gap-3 rounded-lg border bg-muted/30 p-3 text-sm md:grid-cols-5">
          <GatePill label="Creative" gate={current.creative_gate} />
          <GatePill label="Bid" gate={current.bid_gate} />
          <GatePill label="Audience" gate={current.audience_gate} />
          <GatePill label="Budget" gate={current.budget_gate} />
          <GatePill label="Kill switch" gate={current.kill_gate} />
        </div>

        <div className="grid grid-cols-3 gap-3 text-xs text-muted-foreground">
          <div>
            <span className="uppercase">Campaigns at current mode</span>
            <div className="text-sm text-foreground">
              {current.campaigns_at_current_mode}
            </div>
          </div>
          <div>
            <span className="uppercase">Successful at current mode</span>
            <div className="text-sm text-foreground">
              {current.successful_at_current_mode}
            </div>
          </div>
          <div>
            <span className="uppercase">Last graduated</span>
            <div className="text-sm text-foreground">
              {current.last_graduated_at
                ? new Date(current.last_graduated_at).toLocaleDateString()
                : "—"}
            </div>
          </div>
        </div>

        {error && (
          <Alert variant="destructive">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        <Alert>
          <AlertDescription className="text-xs">
            <strong>Graduation is explicit and opt-in</strong> (HMT Rule 17).
            Switching to Autopilot is always one click; switching back is
            one click too. Auto mode <em>tightens</em> safety rules rather
            than loosening them — kill switch stays approve-only in every
            mode.
          </AlertDescription>
        </Alert>
      </CardContent>
    </Card>
  );
}

function ModeCard({
  mode,
  active,
  applied,
  disabled,
  onSelect,
}: {
  mode: (typeof MODES)[number];
  active: boolean;
  applied: boolean;
  disabled: boolean;
  onSelect: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onSelect}
      disabled={disabled || active}
      className={
        "flex flex-col gap-2 rounded-lg border p-3 text-left transition-colors disabled:cursor-not-allowed " +
        (active
          ? "border-primary bg-primary/5"
          : "border-border hover:border-primary hover:bg-primary/5")
      }
    >
      <div className="flex items-center justify-between">
        <span className="text-sm font-semibold">{mode.name}</span>
        {active && <Check className="size-4 text-primary" />}
      </div>
      <p className="text-xs leading-snug text-muted-foreground">{mode.summary}</p>
      {applied && !active && (
        <Badge variant="outline" className="text-[10px]">just applied</Badge>
      )}
    </button>
  );
}

function GatePill({ label, gate }: { label: string; gate: GateKind }) {
  const g = GATE_LABELS[gate];
  return (
    <div className="flex flex-col gap-1">
      <span className="text-xs uppercase text-muted-foreground">{label}</span>
      <span className={`text-sm font-semibold ${g.tone}`}>{g.label}</span>
    </div>
  );
}
