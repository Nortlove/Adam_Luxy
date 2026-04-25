/**
 * SourceBadge — visual marker for a recommendation's source. Lets the
 * operator distinguish DCIL directives (theory-grounded, authoritative)
 * from threshold-generator output (correlational A1 fallback —
 * THRESHOLD_GENERATORS_AS_FALLBACK in the A14 registry) at a glance.
 *
 * Discipline: the badge labels the source, it does not interpret quality.
 * "DCIL" and "threshold" are factual identifiers. The operator's reading
 * of what those mean is informed by the orientation, not by the badge
 * composing prose.
 */

import type { RecommendationSource } from "@/lib/types";
import { Badge } from "@/components/ui/badge";

export function SourceBadge({ source }: { source: RecommendationSource }) {
  if (source === "dcil") {
    return (
      <Badge className="bg-primary text-primary-foreground hover:bg-primary/90">
        DCIL
      </Badge>
    );
  }
  if (source === "chain_attribution") {
    return (
      <Badge className="bg-amber-600 text-white hover:bg-amber-700">
        chain attribution
      </Badge>
    );
  }
  // source === "threshold" — A14 fallback. Visually muted so the operator
  // sees it as lower-priority than DCIL directives in the queue.
  return (
    <Badge variant="outline" className="border-dashed text-muted-foreground">
      threshold · A14 fallback
    </Badge>
  );
}
