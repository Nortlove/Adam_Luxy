"use client";

/**
 * Renders a Discovery question using the right elicitation primitive
 * based on question.mode. Encapsulates the dispatch so the flow
 * component doesn't need to know about the underlying toolkit.
 */

import type { DiscoveryQuestion } from "@/lib/discovery/questions";
import {
  ForcedPair,
  KAFC,
  StoryPrompt,
  TimedPair,
} from "@/components/elicitation";
import { FreeformText } from "./freeform-text";

export type QuestionRendererProps = {
  question: DiscoveryQuestion;
  sessionId: string;
  moodIndex: number | null;
  onComplete: () => void;
};

export function QuestionRenderer({
  question,
  sessionId,
  moodIndex,
  onComplete,
}: QuestionRendererProps) {
  switch (question.mode) {
    case "forced_pair": {
      if (!question.options || question.options.length < 2) {
        return <UnconfiguredNote id={question.id} />;
      }
      const [a, b] = question.options;
      return (
        <ForcedPair
          question={question.prompt}
          domain={question.domain}
          sessionId={sessionId}
          moodIndex={moodIndex}
          optionA={a}
          optionB={b}
          onComplete={() => onComplete()}
        />
      );
    }

    case "timed_pair": {
      if (!question.options || question.options.length < 2) {
        return <UnconfiguredNote id={question.id} />;
      }
      const [a, b] = question.options;
      return (
        <TimedPair
          question={question.prompt}
          domain={question.domain}
          sessionId={sessionId}
          moodIndex={moodIndex}
          optionA={a}
          optionB={b}
          deadlineMs={question.deadlineMs}
          onComplete={() => onComplete()}
        />
      );
    }

    case "k_afc": {
      if (!question.options || question.options.length < 2) {
        return <UnconfiguredNote id={question.id} />;
      }
      return (
        <KAFC
          question={question.prompt}
          domain={question.domain}
          options={question.options}
          sessionId={sessionId}
          moodIndex={moodIndex}
          onComplete={() => onComplete()}
        />
      );
    }

    case "story":
      return (
        <StoryPrompt
          prompt={question.prompt}
          domain={question.domain}
          sessionId={sessionId}
          moodIndex={moodIndex}
          minChars={question.minChars}
          onComplete={() => onComplete()}
        />
      );

    case "freeform_short":
      return (
        <FreeformText
          prompt={question.prompt}
          domain={question.domain}
          sessionId={sessionId}
          moodIndex={moodIndex}
          variant="short"
          minChars={question.minChars}
          onComplete={() => onComplete()}
        />
      );

    case "freeform_long":
      return (
        <FreeformText
          prompt={question.prompt}
          domain={question.domain}
          sessionId={sessionId}
          moodIndex={moodIndex}
          variant="long"
          minChars={question.minChars}
          onComplete={() => onComplete()}
        />
      );

    default:
      return <UnconfiguredNote id={question.id} />;
  }
}

function UnconfiguredNote({ id }: { id: string }) {
  return (
    <div className="rounded-lg border border-dashed bg-muted/20 p-4 text-sm text-muted-foreground">
      Question <code>{id}</code> is missing configuration (expected options
      or valid mode).
    </div>
  );
}
