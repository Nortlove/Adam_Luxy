"use client";

/**
 * Elicitation Sandbox — live demos of the four generators.
 *
 * Every interaction lands as a real Claim in Neo4j. The point is to
 * make the elicitation primitives tangible: timed forced pairs,
 * story prompts, recallability probes, mood probes.
 */

import { useEffect, useState } from "react";
import { RefreshCw } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";

import {
  ForcedPair,
  MoodProbe,
  RecallabilityProbe,
  StoryPrompt,
  TimedPair,
} from "@/components/elicitation";

export function Sandbox() {
  const [sessionId, setSessionId] = useState<string>("");
  const [moodIndex, setMoodIndex] = useState<number | null>(null);
  const [nonce, setNonce] = useState(0);

  useEffect(() => {
    setSessionId(`sandbox-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`);
  }, []);

  function reset() {
    setNonce((n) => n + 1);
  }

  return (
    <div className="flex flex-col gap-6">
      <Card>
        <CardHeader>
          <CardTitle className="text-base">About the Sandbox</CardTitle>
          <CardDescription>
            Every widget below writes a real Claim to the Dialogue
            Ledger. The four primitives — binary forced-choice, timed
            forced-choice, story prompt, recallability probe — are the
            building blocks of the rest of the platform&rsquo;s
            elicitation surface. Test them here to see how each one
            feels and what data each one actually produces.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex items-center gap-3 text-xs text-muted-foreground">
          <span>
            session: <code>{sessionId || "—"}</code>
          </span>
          {moodIndex !== null && (
            <span>
              mood index: <code>{moodIndex}</code>
            </span>
          )}
          <span className="ml-auto">
            <Button variant="ghost" size="sm" onClick={reset}>
              <RefreshCw className="mr-1 size-3" />
              reset widgets
            </Button>
          </span>
        </CardContent>
      </Card>

      <section>
        <SectionHeader
          title="1. Mood probe (session start)"
          subtitle="Three-option affective read. Covariate-adjusts every subsequent claim in the session."
        />
        <MoodProbe
          key={`mood-${nonce}`}
          sessionId={sessionId}
          onComplete={(v) => setMoodIndex(v)}
        />
      </section>

      <Separator />

      <section>
        <SectionHeader
          title="2. Forced pair — leisurely binary"
          subtitle="Untimed. Use when preference contamination risk is moderate."
        />
        <ForcedPair
          key={`forced-${nonce}`}
          question="Which statement feels closer to your best customer?"
          domain="audience_hypothesis"
          sessionId={sessionId}
          moodIndex={moodIndex}
          optionA={{
            id: "detail_oriented",
            label:
              "Careful, detail-oriented — reads the fine print before deciding",
            description:
              "The kind of customer who researches thoroughly, wants guarantees, and avoids surprises.",
          }}
          optionB={{
            id: "experience_first",
            label:
              "Experience-first — trusts the brand&rsquo;s reputation and decides fast",
            description:
              "The kind of customer who picks based on how the brand feels, not the specs.",
          }}
        />
      </section>

      <Separator />

      <section>
        <SectionHeader
          title="3. Timed pair — gut-check with countdown"
          subtitle="3-second countdown forces Type 1 response. Latency is logged as a fluency signal."
        />
        <TimedPair
          key={`timed-${nonce}`}
          question="Does this audience respond to authority or to social proof?"
          domain="mechanism_selection"
          sessionId={sessionId}
          moodIndex={moodIndex}
          deadlineMs={3000}
          optionA={{ id: "authority", label: "Authority" }}
          optionB={{ id: "social_proof", label: "Social proof" }}
        />
      </section>

      <Separator />

      <section>
        <SectionHeader
          title="4. Story prompt — episodic recall"
          subtitle="A specific remembered instance extracts the pattern-detail System 2 hand-waves."
        />
        <StoryPrompt
          key={`story-${nonce}`}
          prompt="Tell me about the best campaign you ever ran — and specifically why you think it worked."
          domain="creative_voice"
          sessionId={sessionId}
          moodIndex={moodIndex}
        />
      </section>

      <Separator />

      <section>
        <SectionHeader
          title="5. Recallability probe — anti-confabulation"
          subtitle="Follow a confident claim with a recalled instance. Fluency is the signal."
        />
        <RecallabilityProbe
          key={`recall-${nonce}`}
          parentClaim="Luxury audiences respond better to understatement than to hard sell."
          domain="creative_voice"
          sessionId={sessionId}
          moodIndex={moodIndex}
        />
      </section>
    </div>
  );
}

function SectionHeader({
  title,
  subtitle,
}: {
  title: string;
  subtitle: string;
}) {
  return (
    <div className="mb-3">
      <h3 className="text-base font-semibold tracking-tight">{title}</h3>
      <p className="text-xs text-muted-foreground">{subtitle}</p>
    </div>
  );
}
