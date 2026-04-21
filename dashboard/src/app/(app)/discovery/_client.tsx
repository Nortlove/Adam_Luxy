"use client";

import { useEffect, useState } from "react";

import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";

import { MoodProbe } from "@/components/elicitation";
import { DiscoveryFlow } from "@/components/discovery/flow";
import { DataSourcesPanel } from "@/components/discovery/data-sources";
import {
  DISCOVERY_PHASES,
  questionsForPhase,
} from "@/lib/discovery/questions";

export function DiscoveryClient() {
  const [tab, setTab] = useState<"p1" | "p2" | "p3" | "p4">("p1");
  const [sessionId, setSessionId] = useState<string>("");
  const [moodIndex, setMoodIndex] = useState<number | null>(null);
  const [moodSet, setMoodSet] = useState<boolean>(false);

  useEffect(() => {
    setSessionId(
      `discovery-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    );
  }, []);

  function phaseFromTab(t: string): 1 | 2 | 3 | 4 {
    return (Number(t.slice(1)) as 1 | 2 | 3 | 4) ?? 1;
  }

  return (
    <div className="flex flex-col gap-4">
      {!moodSet && sessionId && (
        <div>
          <Alert className="mb-3">
            <AlertTitle>Quick mood read before you start</AlertTitle>
            <AlertDescription>
              A one-click affective check so subsequent answers can be
              covariate-adjusted. Takes about two seconds.
            </AlertDescription>
          </Alert>
          <MoodProbe
            sessionId={sessionId}
            onComplete={(v) => {
              setMoodIndex(v);
              setMoodSet(true);
            }}
          />
        </div>
      )}

      <Tabs
        value={tab}
        onValueChange={(v) => setTab(v as typeof tab)}
        className="flex flex-col gap-4"
      >
        <TabsList className="flex flex-wrap">
          {DISCOVERY_PHASES.map((p) => (
            <TabsTrigger key={p.n} value={`p${p.n}`}>
              <span className="mr-1 text-xs text-muted-foreground">
                {p.n}
              </span>
              {p.name}
              {p.n < 4 && (
                <span className="ml-1 text-[10px] text-muted-foreground">
                  · {questionsForPhase(p.n as 1 | 2 | 3 | 4).length} q
                </span>
              )}
            </TabsTrigger>
          ))}
        </TabsList>

        {DISCOVERY_PHASES.map((p) => (
          <TabsContent key={p.n} value={`p${p.n}`}>
            {p.n === 4 ? (
              <DataSourcesPanel
                sessionId={sessionId}
                moodIndex={moodIndex}
              />
            ) : (
              <DiscoveryFlow
                phase={p.n as 1 | 2 | 3}
                sessionId={sessionId}
                moodIndex={moodIndex}
                onChangePhase={(next) =>
                  setTab(`p${next}` as typeof tab)
                }
              />
            )}
          </TabsContent>
        ))}
      </Tabs>
    </div>
  );
}
