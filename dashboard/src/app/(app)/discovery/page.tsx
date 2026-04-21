import { DiscoveryClient } from "./_client";
import { PageHeader } from "@/components/page-header";

export const metadata = {
  title: "Discovery · INFORMATIV",
};

export const dynamic = "force-dynamic";

export default function DiscoveryPage() {
  return (
    <div className="flex flex-col gap-6 p-6">
      <PageHeader
        title="Discovery"
        description="The question dance. Brand, audience, goal, and first-party data — rendered as elicitation primitives that write to the Dialogue Ledger as hypotheses."
      />
      <DiscoveryClient />
    </div>
  );
}
