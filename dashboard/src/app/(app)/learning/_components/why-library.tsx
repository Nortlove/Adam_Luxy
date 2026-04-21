import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ShieldAlert } from "lucide-react";
import type { WhyLibraryEntry, WhyLibraryResponse } from "@/lib/types";

export function WhyLibraryView({ data }: { data: WhyLibraryResponse }) {
  if (data.total === 0) {
    return (
      <Card className="border-dashed">
        <CardHeader>
          <CardTitle>The Why Library is empty</CardTitle>
          <CardDescription>
            Validated bias patterns surface here as the Inferential
            Adjudicator turns deviations into learnings. Each entry is a
            pre-emptive defensive warning the system shows the next time a
            similar pattern fires — protecting you from repeating a known
            failure mode.
          </CardDescription>
        </CardHeader>
      </Card>
    );
  }

  return (
    <div className="grid gap-3">
      {data.entries.map((e) => (
        <WhyLibraryCard key={e.id} entry={e} />
      ))}
    </div>
  );
}

function WhyLibraryCard({ entry }: { entry: WhyLibraryEntry }) {
  const strengthPct = Math.round(entry.evidence_strength * 100);
  return (
    <Card className="border-l-4 border-l-amber-500">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center justify-between gap-2 text-base">
          <span className="flex items-center gap-2">
            <ShieldAlert className="size-4 text-amber-600 dark:text-amber-400" />
            <span className="truncate">{entry.trigger_pattern}</span>
          </span>
          <Badge variant="outline" className="text-[10px] uppercase">
            {entry.bias_class.replace(/_/g, " ")}
          </Badge>
        </CardTitle>
        <CardDescription>{entry.countermeasure}</CardDescription>
      </CardHeader>
      <CardContent className="grid grid-cols-4 gap-3 text-xs">
        <div>
          <div className="uppercase text-muted-foreground">Scope</div>
          <div className="text-sm font-semibold">{entry.scope}</div>
        </div>
        <div>
          <div className="uppercase text-muted-foreground">Evidence</div>
          <div className="text-sm font-semibold">{strengthPct}%</div>
        </div>
        <div>
          <div className="uppercase text-muted-foreground">Observations</div>
          <div className="text-sm font-semibold">
            {entry.warning_posterior_observations}
          </div>
        </div>
        <div>
          <div className="uppercase text-muted-foreground">Created</div>
          <div className="text-sm font-semibold">
            {new Date(entry.created_at).toLocaleDateString()}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
