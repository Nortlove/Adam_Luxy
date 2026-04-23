// =============================================================================
// ADAM Migration 024: Public Label Translation Layer
//
// Infrastructure for translating internal taxonomy (archetype slugs,
// therapeutic mechanism names, barrier categories, construct dimensions,
// trajectory labels) into client-facing language that does NOT reveal
// the methodology underneath.
//
// Why this exists (Chris, 2026-04-22):
//
//   "By way of explaining, this can be powerful and very specific. By way
//    of numbers and getting into our nodes and graph, no, we don't want to
//    give that away."
//
//   The strategic premise: a client (or their agency, or their competitor)
//   who sees our internal taxonomy could reverse-engineer the cascade.
//   They would not be able to rebuild the 1B-review-backed posteriors or
//   the Enhancement #33/#34/#36 machinery, but the TAXONOMY itself —
//   knowing we classify reader states into specific archetypes with
//   specific barriers resolved by specific therapeutic mechanisms — is a
//   map someone else could use to aim a competing build. The client
//   surface must render reports in outcome language that could have come
//   from any good consultancy; what distinguishes us stays in Chris's
//   internal surface and in the actual serving decisions.
//
// Design commitments:
//
//   - Learnable over time. Usage counters + feedback fields + draft /
//     approved / archived status so labels can evolve from practice.
//     Labels are not a compile-time constant; they are graph state.
//
//   - Per-advertiser overrides. The same internal archetype can present
//     under different public labels for different advertisers (LUXY's
//     "Reliability-first traveler" may not be the right phrasing for a
//     future luxury skincare client). Default context provides the
//     baseline; advertiser-scoped PublicLabels override when present.
//
//   - Approval-gated. A PublicLabel in status="draft" must be approved
//     before it's rendered on a client surface. Prevents a half-written
//     label from leaking to a client report.
//
//   - Backfill-compatible. The render path falls back to the internal
//     slug with a "[unreviewed]" marker if a PublicLabel is missing; the
//     marker is a signal for internal operators to complete the mapping.
//     Client surfaces refuse to render unreviewed labels.
// =============================================================================


// =============================================================================
// CONSTRAINTS
// =============================================================================

CREATE CONSTRAINT public_label_pk IF NOT EXISTS
FOR (l:PublicLabel) REQUIRE l.id IS UNIQUE;


// =============================================================================
// INDEXES
// =============================================================================

// Lookup pattern: given (internal_kind, internal_id, context),
// find the applicable PublicLabel. Context falls back from
// advertiser-scoped to "default".
CREATE INDEX public_label_lookup_idx IF NOT EXISTS
FOR (l:PublicLabel) ON (l.internal_kind, l.internal_id, l.context);

// Secondary lookup by internal_id alone (when listing all labels for an
// internal entity across contexts — admin view).
CREATE INDEX public_label_internal_id_idx IF NOT EXISTS
FOR (l:PublicLabel) ON (l.internal_id);

// Status filter for rendering (only "approved" labels render externally).
CREATE INDEX public_label_status_idx IF NOT EXISTS
FOR (l:PublicLabel) ON (l.status);

// Usage count for label-improvement analytics.
CREATE INDEX public_label_usage_idx IF NOT EXISTS
FOR (l:PublicLabel) ON (l.usage_count);


// =============================================================================
// NODE DEFINITIONS (documented shape)
// =============================================================================

// PublicLabel node shape:
//   id: string                  — format "label:{kind}:{internal_id}:{context}"
//   internal_kind: string       — "archetype" | "mechanism" | "barrier" |
//                                 "trajectory" | "communication_style" |
//                                 "construct_dimension" (extensible)
//   internal_id: string         — internal slug (e.g., "careful_truster")
//   context: string             — "default" OR "advertiser:{id}" OR
//                                 "vertical:{name}". Resolution order:
//                                 advertiser → vertical → default.
//   label: string               — the client-facing phrase
//   description: string | null  — longer-form explanation used when a
//                                 report needs context-rich copy (e.g.,
//                                 hover explanations). Client-safe.
//   status: string              — "draft" | "approved" | "archived".
//                                 Only "approved" renders to clients.
//   rationale: string | null    — internal-only note explaining WHY this
//                                 is the right label. Never rendered.
//   created_at: datetime
//   updated_at: datetime
//   created_by: string | null   — DialogueUser.id (tracks authorship)
//   approved_by: string | null  — DialogueUser.id of the approver
//   approved_at: datetime | null
//   usage_count: int            — incremented each time the label is
//                                 rendered in a client-facing artifact.
//                                 Low usage_count after N reports is a
//                                 signal the label may not be landing.
//   feedback_positive: int      — if/when client-side feedback is captured
//   feedback_negative: int


// =============================================================================
// RELATIONSHIPS (documented shape)
// =============================================================================

// (:Archetype)-[:HAS_PUBLIC_LABEL]->(:PublicLabel {context: "default"})
// (:Archetype)-[:HAS_PUBLIC_LABEL]->(:PublicLabel {context: "advertiser:luxy_ride"})
// (:Mechanism)-[:HAS_PUBLIC_LABEL]->(:PublicLabel {context: "default"})
// (:Barrier)-[:HAS_PUBLIC_LABEL]->(:PublicLabel {context: "default"})
//
// At render time the service queries for an advertiser-scoped label
// first; if none or if status != "approved", falls back to default.
// If no approved label exists at any level, rendering is blocked and
// an internal warning is emitted.


// =============================================================================
// SEED — LUXY archetype public labels (default context, approved)
//
// Source: Chris Nocera approval 2026-04-22.
// Reasoning retained in rationale field so future operators know why
// each label was chosen.
// =============================================================================

MERGE (l:PublicLabel {id: "label:archetype:careful_truster:default"})
  ON CREATE SET
    l.internal_kind = "archetype",
    l.internal_id = "careful_truster",
    l.context = "default",
    l.label = "Reliability-first traveler",
    l.description = "Customers who prioritize proven dependability and consistent service over novelty or status.",
    l.status = "approved",
    l.rationale = "Emphasizes behavior (reliability preference) rather than personality construct (trust orientation). Safe for client-facing use.",
    l.created_at = datetime(),
    l.updated_at = datetime(),
    l.approved_at = datetime(),
    l.approved_by = "user:chris",
    l.usage_count = 0,
    l.feedback_positive = 0,
    l.feedback_negative = 0;

MERGE (l:PublicLabel {id: "label:archetype:status_seeker:default"})
  ON CREATE SET
    l.internal_kind = "archetype",
    l.internal_id = "status_seeker",
    l.context = "default",
    l.label = "Premium-experience buyer",
    l.description = "Customers who choose elevated service tiers to signal quality and taste.",
    l.status = "approved",
    l.rationale = "Frames by what they buy, not why (avoiding 'status-signaling' psychology terminology).",
    l.created_at = datetime(),
    l.updated_at = datetime(),
    l.approved_at = datetime(),
    l.approved_by = "user:chris",
    l.usage_count = 0,
    l.feedback_positive = 0,
    l.feedback_negative = 0;

MERGE (l:PublicLabel {id: "label:archetype:easy_decider:default"})
  ON CREATE SET
    l.internal_kind = "archetype",
    l.internal_id = "easy_decider",
    l.context = "default",
    l.label = "Convenience-first booker",
    l.description = "Customers who minimize decision time and favor low-friction booking flows.",
    l.status = "approved",
    l.rationale = "Behavioral framing; no personality-test language.",
    l.created_at = datetime(),
    l.updated_at = datetime(),
    l.approved_at = datetime(),
    l.approved_by = "user:chris",
    l.usage_count = 0, l.feedback_positive = 0, l.feedback_negative = 0;

MERGE (l:PublicLabel {id: "label:archetype:explorer:default"})
  ON CREATE SET
    l.internal_kind = "archetype",
    l.internal_id = "explorer",
    l.context = "default",
    l.label = "First-time luxury customer",
    l.description = "Customers newly engaging with premium travel service.",
    l.status = "approved",
    l.rationale = "Describes the customer's journey stage rather than the underlying novelty-seeking construct.",
    l.created_at = datetime(),
    l.updated_at = datetime(),
    l.approved_at = datetime(),
    l.approved_by = "user:chris",
    l.usage_count = 0, l.feedback_positive = 0, l.feedback_negative = 0;

MERGE (l:PublicLabel {id: "label:archetype:prevention_planner:default"})
  ON CREATE SET
    l.internal_kind = "archetype",
    l.internal_id = "prevention_planner",
    l.context = "default",
    l.label = "Risk-aware planner",
    l.description = "Customers who prefer clear assurances and explicit cancellation / safety policies before booking.",
    l.status = "approved",
    l.rationale = "Generalizes the regulatory-focus construct into a neutral decision-style descriptor.",
    l.created_at = datetime(),
    l.updated_at = datetime(),
    l.approved_at = datetime(),
    l.approved_by = "user:chris",
    l.usage_count = 0, l.feedback_positive = 0, l.feedback_negative = 0;

MERGE (l:PublicLabel {id: "label:archetype:reliable_cooperator:default"})
  ON CREATE SET
    l.internal_kind = "archetype",
    l.internal_id = "reliable_cooperator",
    l.context = "default",
    l.label = "Professional repeat rider",
    l.description = "Business-travel-oriented customers who book on a recurring professional pattern.",
    l.status = "approved",
    l.rationale = "Behavioral + role-based; does not reveal conscientiousness construct.",
    l.created_at = datetime(),
    l.updated_at = datetime(),
    l.approved_at = datetime(),
    l.approved_by = "user:chris",
    l.usage_count = 0, l.feedback_positive = 0, l.feedback_negative = 0;

MERGE (l:PublicLabel {id: "label:archetype:trusting_loyalist:default"})
  ON CREATE SET
    l.internal_kind = "archetype",
    l.internal_id = "trusting_loyalist",
    l.context = "default",
    l.label = "Long-term loyal customer",
    l.description = "Customers with extended tenure and strong brand affinity.",
    l.status = "approved",
    l.rationale = "Behavior over time; no psychological construct reference.",
    l.created_at = datetime(),
    l.updated_at = datetime(),
    l.approved_at = datetime(),
    l.approved_by = "user:chris",
    l.usage_count = 0, l.feedback_positive = 0, l.feedback_negative = 0;

MERGE (l:PublicLabel {id: "label:archetype:dependable_loyalist:default"})
  ON CREATE SET
    l.internal_kind = "archetype",
    l.internal_id = "dependable_loyalist",
    l.context = "default",
    l.label = "Frequent repeat booker",
    l.description = "High-frequency customers with consistent usage patterns.",
    l.status = "approved",
    l.rationale = "Describes cadence, not loyalty-construct internals.",
    l.created_at = datetime(),
    l.updated_at = datetime(),
    l.approved_at = datetime(),
    l.approved_by = "user:chris",
    l.usage_count = 0, l.feedback_positive = 0, l.feedback_negative = 0;

MERGE (l:PublicLabel {id: "label:archetype:consensus_seeker:default"})
  ON CREATE SET
    l.internal_kind = "archetype",
    l.internal_id = "consensus_seeker",
    l.context = "default",
    l.label = "Group-decision coordinator",
    l.description = "Customers coordinating travel for multiple parties (families, events, teams).",
    l.status = "approved",
    l.rationale = "Describes the role, not the social-influence susceptibility construct.",
    l.created_at = datetime(),
    l.updated_at = datetime(),
    l.approved_at = datetime(),
    l.approved_by = "user:chris",
    l.usage_count = 0, l.feedback_positive = 0, l.feedback_negative = 0;


// =============================================================================
// SEED — Therapeutic mechanism public labels (message-style descriptors)
// =============================================================================

MERGE (l:PublicLabel {id: "label:mechanism:evidence_proof:default"})
  ON CREATE SET
    l.internal_kind = "mechanism", l.internal_id = "evidence_proof",
    l.context = "default",
    l.label = "verified-reliability messaging",
    l.description = "Messaging that foregrounds concrete evidence of consistent service quality.",
    l.status = "approved",
    l.rationale = "Describes the output style, not the scaffolding / epistemic-authority mechanism underneath.",
    l.created_at = datetime(), l.updated_at = datetime(), l.approved_at = datetime(),
    l.approved_by = "user:chris", l.usage_count = 0,
    l.feedback_positive = 0, l.feedback_negative = 0;

MERGE (l:PublicLabel {id: "label:mechanism:narrative_transportation:default"})
  ON CREATE SET
    l.internal_kind = "mechanism", l.internal_id = "narrative_transportation",
    l.context = "default",
    l.label = "story-driven messaging",
    l.description = "Messaging built around a customer experience narrative.",
    l.status = "approved",
    l.rationale = "No reference to Green & Brock transportation theory.",
    l.created_at = datetime(), l.updated_at = datetime(), l.approved_at = datetime(),
    l.approved_by = "user:chris", l.usage_count = 0,
    l.feedback_positive = 0, l.feedback_negative = 0;

MERGE (l:PublicLabel {id: "label:mechanism:social_proof_matched:default"})
  ON CREATE SET
    l.internal_kind = "mechanism", l.internal_id = "social_proof_matched",
    l.context = "default",
    l.label = "similar-customer testimonials",
    l.description = "Messaging that presents testimonials from customers who closely match the target segment.",
    l.status = "approved",
    l.rationale = "Describes format; does not reveal Bandura modeling or matched-exemplar mechanism.",
    l.created_at = datetime(), l.updated_at = datetime(), l.approved_at = datetime(),
    l.approved_by = "user:chris", l.usage_count = 0,
    l.feedback_positive = 0, l.feedback_negative = 0;

MERGE (l:PublicLabel {id: "label:mechanism:autonomy_restoration:default"})
  ON CREATE SET
    l.internal_kind = "mechanism", l.internal_id = "autonomy_restoration",
    l.context = "default",
    l.label = "choice-centric messaging",
    l.description = "Messaging that emphasizes the customer's options and control over the booking flow.",
    l.status = "approved",
    l.rationale = "Describes the copy style; no reference to SDT autonomy restoration.",
    l.created_at = datetime(), l.updated_at = datetime(), l.approved_at = datetime(),
    l.approved_by = "user:chris", l.usage_count = 0,
    l.feedback_positive = 0, l.feedback_negative = 0;

MERGE (l:PublicLabel {id: "label:mechanism:construal_shift:default"})
  ON CREATE SET
    l.internal_kind = "mechanism", l.internal_id = "construal_shift",
    l.context = "default",
    l.label = "long-term-value messaging",
    l.description = "Messaging that frames the purchase in terms of longer-horizon benefits.",
    l.status = "approved",
    l.rationale = "Describes framing direction, not construal-level theory.",
    l.created_at = datetime(), l.updated_at = datetime(), l.approved_at = datetime(),
    l.approved_by = "user:chris", l.usage_count = 0,
    l.feedback_positive = 0, l.feedback_negative = 0;

MERGE (l:PublicLabel {id: "label:mechanism:anxiety_resolution:default"})
  ON CREATE SET
    l.internal_kind = "mechanism", l.internal_id = "anxiety_resolution",
    l.context = "default",
    l.label = "reassurance messaging",
    l.description = "Messaging that directly addresses the customer's top pre-booking concerns.",
    l.status = "approved",
    l.rationale = "Plain-language; does not reveal barrier diagnosis vocabulary.",
    l.created_at = datetime(), l.updated_at = datetime(), l.approved_at = datetime(),
    l.approved_by = "user:chris", l.usage_count = 0,
    l.feedback_positive = 0, l.feedback_negative = 0;

MERGE (l:PublicLabel {id: "label:mechanism:scaffolding_reduction:default"})
  ON CREATE SET
    l.internal_kind = "mechanism", l.internal_id = "scaffolding_reduction",
    l.context = "default",
    l.label = "clarity-focused messaging",
    l.description = "Simplified messaging that reduces cognitive load during decision.",
    l.status = "approved",
    l.rationale = "Describes style; no reference to scaffolding framework.",
    l.created_at = datetime(), l.updated_at = datetime(), l.approved_at = datetime(),
    l.approved_by = "user:chris", l.usage_count = 0,
    l.feedback_positive = 0, l.feedback_negative = 0;


// =============================================================================
// SEED — Barrier public labels (for internal framing only; do NOT render
// barrier language directly to clients, but these labels exist so the
// report service can compose outcome-style sentences from them safely).
// =============================================================================

MERGE (l:PublicLabel {id: "label:barrier:trust_deficit:default"})
  ON CREATE SET
    l.internal_kind = "barrier", l.internal_id = "trust_deficit",
    l.context = "default",
    l.label = "hesitation about service dependability",
    l.description = "Customer signals suggest uncertainty about whether the service will deliver as promised.",
    l.status = "approved",
    l.rationale = "Describes the customer's pre-booking state neutrally; does not reveal internal barrier taxonomy.",
    l.created_at = datetime(), l.updated_at = datetime(), l.approved_at = datetime(),
    l.approved_by = "user:chris", l.usage_count = 0,
    l.feedback_positive = 0, l.feedback_negative = 0;

MERGE (l:PublicLabel {id: "label:barrier:price_friction:default"})
  ON CREATE SET
    l.internal_kind = "barrier", l.internal_id = "price_friction",
    l.context = "default",
    l.label = "price sensitivity",
    l.description = "Customer signals indicate the price is the leading consideration.",
    l.status = "approved",
    l.rationale = "Industry-standard language.",
    l.created_at = datetime(), l.updated_at = datetime(), l.approved_at = datetime(),
    l.approved_by = "user:chris", l.usage_count = 0,
    l.feedback_positive = 0, l.feedback_negative = 0;

MERGE (l:PublicLabel {id: "label:barrier:emotional_disconnect:default"})
  ON CREATE SET
    l.internal_kind = "barrier", l.internal_id = "emotional_disconnect",
    l.context = "default",
    l.label = "limited emotional engagement",
    l.description = "Customer is not feeling resonance with the brand's current messaging.",
    l.status = "approved",
    l.rationale = "General marketing language.",
    l.created_at = datetime(), l.updated_at = datetime(), l.approved_at = datetime(),
    l.approved_by = "user:chris", l.usage_count = 0,
    l.feedback_positive = 0, l.feedback_negative = 0;

MERGE (l:PublicLabel {id: "label:barrier:processing_overload:default"})
  ON CREATE SET
    l.internal_kind = "barrier", l.internal_id = "processing_overload",
    l.context = "default",
    l.label = "decision complexity",
    l.description = "Customer is encountering too much information to act confidently.",
    l.status = "approved",
    l.rationale = "Describes customer state, not cognitive load framework.",
    l.created_at = datetime(), l.updated_at = datetime(), l.approved_at = datetime(),
    l.approved_by = "user:chris", l.usage_count = 0,
    l.feedback_positive = 0, l.feedback_negative = 0;

MERGE (l:PublicLabel {id: "label:barrier:attention_shortage:default"})
  ON CREATE SET
    l.internal_kind = "barrier", l.internal_id = "attention_shortage",
    l.context = "default",
    l.label = "low current engagement",
    l.description = "Customer is not fully attentive to the current booking surface.",
    l.status = "approved",
    l.rationale = "General term.",
    l.created_at = datetime(), l.updated_at = datetime(), l.approved_at = datetime(),
    l.approved_by = "user:chris", l.usage_count = 0,
    l.feedback_positive = 0, l.feedback_negative = 0;


// Additional barrier / mechanism labels can be added as new migrations
// or via the forthcoming admin surface. The seed above covers the most
// frequently-surfaced values for the LUXY pilot.
