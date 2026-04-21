"use client";

/**
 * Phase 4 — First-Party Data Ingestion.
 *
 * v1 captures user-declared data availability as metadata Claims
 * (one Claim per source type). Actual file upload + parsing lands in
 * a later iteration — for the pilot, the declaration alone is
 * already valuable (it tells the platform which capabilities to
 * unlock and where to focus cold-start priors).
 */

import { useState } from "react";
import {
  CheckCircle2,
  CircleDashed,
  FileText,
  Upload,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Alert, AlertDescription } from "@/components/ui/alert";

import {
  DATA_SOURCES,
  type DataSourceDefinition,
} from "@/lib/discovery/questions";
import { submitClaim } from "@/app/(app)/ledger/actions";

type ConsentScope =
  | "targeting_only"
  | "training_allowed"
  | "modeling_only"
  | "reporting_only";

export function DataSourcesPanel({
  sessionId,
  moodIndex,
}: {
  sessionId: string;
  moodIndex: number | null;
}) {
  const [declared, setDeclared] = useState<Record<string, boolean>>({});

  return (
    <div className="flex flex-col gap-4">
      <Alert>
        <AlertDescription>
          Each declaration below writes a metadata Claim to the Dialogue
          Ledger with your stated volume and consent scope. Actual parsing
          and ingestion runs as a separate process once the pilot pipeline
          is live — this step tells the platform what&rsquo;s available and
          under what terms.
        </AlertDescription>
      </Alert>
      <div className="grid gap-4 md:grid-cols-2">
        {DATA_SOURCES.map((src) => (
          <DataSourceCard
            key={src.id}
            src={src}
            declared={!!declared[src.id]}
            onDeclared={() => setDeclared((m) => ({ ...m, [src.id]: true }))}
            sessionId={sessionId}
            moodIndex={moodIndex}
          />
        ))}
      </div>
    </div>
  );
}

function DataSourceCard({
  src,
  declared,
  onDeclared,
  sessionId,
  moodIndex,
}: {
  src: DataSourceDefinition;
  declared: boolean;
  onDeclared: () => void;
  sessionId: string;
  moodIndex: number | null;
}) {
  const [open, setOpen] = useState(false);
  const [volume, setVolume] = useState("");
  const [location, setLocation] = useState("");
  const [consent, setConsent] = useState<ConsentScope | "">("");
  const [notes, setNotes] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function declare() {
    setError(null);
    if (!volume.trim() || !consent) {
      setError("Volume and consent scope are required.");
      return;
    }
    setPending(true);
    const text = [
      `[${src.id}] declared`,
      `volume: ${volume.trim()}`,
      `consent: ${consent}`,
      location.trim() && `location: ${location.trim()}`,
      notes.trim() && `notes: ${notes.trim()}`,
    ]
      .filter(Boolean)
      .join(" · ");

    const result = await submitClaim({
      text,
      elicitation_mode: "freeform",
      domain: "first_party_data",
      frame: "neutral",
      session_id: sessionId,
      mood_index: moodIndex,
    });
    setPending(false);

    if (!result.ok) {
      setError(`Failed to record (${result.status}). ${result.message}`);
      return;
    }
    onDeclared();
    setOpen(false);
  }

  return (
    <Card className={declared ? "border-emerald-200 dark:border-emerald-900" : ""}>
      <CardHeader>
        <CardTitle className="flex items-center justify-between gap-2 text-base">
          <span className="flex items-center gap-2">
            {declared ? (
              <CheckCircle2 className="size-5 text-emerald-600 dark:text-emerald-400" />
            ) : (
              <CircleDashed className="size-5 text-muted-foreground" />
            )}
            {src.label}
          </span>
          <span className="text-xs font-normal text-emerald-700 dark:text-emerald-400">
            {src.liftEstimate}
          </span>
        </CardTitle>
        <CardDescription>{src.description}</CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-3 text-sm">
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <FileText className="size-3" />
          <span>Unlocks: {src.unlocks}</span>
        </div>

        {!open && !declared && (
          <Button variant="secondary" onClick={() => setOpen(true)}>
            <Upload className="mr-1 size-4" />
            Declare availability
          </Button>
        )}

        {declared && (
          <Alert>
            <AlertDescription>
              Declared. The platform will treat this source as available per
              your stated consent scope.
            </AlertDescription>
          </Alert>
        )}

        {open && !declared && (
          <div className="flex flex-col gap-3 rounded-md border bg-muted/30 p-3">
            <div>
              <Label htmlFor={`vol-${src.id}`}>
                Volume (e.g., &ldquo;2,400 reviews,&rdquo; &ldquo;6 months of calls&rdquo;)
              </Label>
              <Input
                id={`vol-${src.id}`}
                value={volume}
                onChange={(e) => setVolume(e.target.value)}
              />
            </div>
            <div>
              <Label htmlFor={`loc-${src.id}`}>
                Where it lives (S3 bucket, URL, Drive folder — optional)
              </Label>
              <Input
                id={`loc-${src.id}`}
                value={location}
                onChange={(e) => setLocation(e.target.value)}
              />
            </div>
            <div>
              <Label htmlFor={`consent-${src.id}`}>Consent scope</Label>
              <Select
                value={consent}
                onValueChange={(v) => setConsent(v as ConsentScope)}
              >
                <SelectTrigger id={`consent-${src.id}`}>
                  <SelectValue placeholder="Pick a scope" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="targeting_only">
                    Targeting only — don&rsquo;t use for model training
                  </SelectItem>
                  <SelectItem value="training_allowed">
                    Training allowed — use for global model updates
                  </SelectItem>
                  <SelectItem value="modeling_only">
                    Modeling only — analyze but don&rsquo;t target from it
                  </SelectItem>
                  <SelectItem value="reporting_only">
                    Reporting only — read-only for analytics
                  </SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label htmlFor={`notes-${src.id}`}>Notes (optional)</Label>
              <Textarea
                id={`notes-${src.id}`}
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                rows={2}
              />
            </div>
            {error && (
              <Alert variant="destructive">
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}
            <div className="flex justify-end gap-2">
              <Button variant="ghost" onClick={() => setOpen(false)}>
                Cancel
              </Button>
              <Button onClick={declare} disabled={pending}>
                {pending ? "Saving…" : "Record declaration"}
              </Button>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
