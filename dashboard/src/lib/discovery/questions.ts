/**
 * Discovery question architecture — Phases 1–4.
 *
 * Grounded in the question specification from
 * ADAM_HUMAN_MACHINE_TEAMING_FOUNDATION.md and the reverse-engineered
 * question architecture (Ogilvy DO Brief, Jobs-to-be-Done, IAB RFP,
 * StoryBrand, Neumeier Brand Gap, Play Bigger, Stengel "Grow",
 * Amplitude North Star).
 *
 * Each question carries:
 *   - mode — which elicitation primitive renders it
 *   - domain — the DialogueDomain it feeds in the cascade
 *   - criticality — critical (cannot skip), important, inferable
 *   - rationale — WHY the system needs this answer (visible to user)
 *
 * Phase 5–8 questions (category, creative, media, gates) are scoped
 * for the multi-tenant expansion in Phase C of the platform build.
 */

export type DiscoveryMode =
  | "forced_pair"
  | "timed_pair"
  | "k_afc"
  | "story"
  | "freeform_long"
  | "freeform_short";

export type DiscoveryCriticality = "critical" | "important" | "inferable";

export type DiscoveryQuestion = {
  id: string;
  phase: 1 | 2 | 3 | 4;
  mode: DiscoveryMode;
  prompt: string;
  rationale: string; // WHY the system needs this — shown to user
  domain: string; // DialogueDomain
  criticality: DiscoveryCriticality;
  options?: { id: string; label: string; description?: string }[];
  deadlineMs?: number; // only for timed_pair
  minChars?: number; // only for story / freeform_long
};

export type DiscoveryPhase = {
  n: 1 | 2 | 3 | 4;
  name: string;
  tagline: string;
  description: string;
};

export const DISCOVERY_PHASES: DiscoveryPhase[] = [
  {
    n: 1,
    name: "Brand Discovery",
    tagline: "who are you?",
    description:
      "Anchors the brand-side of the bilateral cascade. Personality, promise, proof, and the one word you want to own.",
  },
  {
    n: 2,
    name: "Audience Hypothesis",
    tagline: "who do you think you serve?",
    description:
      "Jobs-to-be-done, struggling moments, psychological profile — not demographics. Every answer seeds buyer-side construct weights.",
  },
  {
    n: 3,
    name: "Campaign Objective",
    tagline: "what does winning look like?",
    description:
      "The North Star, the guardrails, the horizon. Sets the reward function the learning loop optimizes against.",
  },
  {
    n: 4,
    name: "First-Party Data",
    tagline: "what do you know about your customers?",
    description:
      "CRM, reviews, product copy, past campaigns, call transcripts — the raw material the platform turns into buyer-side annotations.",
  },
];

export const DISCOVERY_QUESTIONS: DiscoveryQuestion[] = [
  // ============================================================
  // Phase 1 — Brand Discovery
  // ============================================================
  {
    id: "brand.exists_beyond_money",
    phase: 1,
    mode: "freeform_long",
    prompt: "Why does your brand exist beyond making money?",
    rationale:
      "Anchors the archetype prior at L1 of the bilateral cascade. Brands that know this answer in a sentence consistently out-perform brands that don't.",
    domain: "archetype_hypothesis",
    criticality: "critical",
    minChars: 40,
  },
  {
    id: "brand.personality_forced_pair_1",
    phase: 1,
    mode: "timed_pair",
    prompt: "If your brand were a person, which feels closer?",
    rationale:
      "Seeds the brand-side Big Five posteriors. Binary forced-choice is more reliable than Likert; timed forces a gut-read not a marketing answer.",
    domain: "archetype_hypothesis",
    criticality: "important",
    deadlineMs: 3000,
    options: [
      { id: "conscientious", label: "Disciplined, careful, reliable" },
      { id: "open", label: "Curious, imaginative, unconventional" },
    ],
  },
  {
    id: "brand.personality_forced_pair_2",
    phase: 1,
    mode: "timed_pair",
    prompt: "And between these two?",
    rationale:
      "Second axis of the Big Five-adjacent brand profile. Runs as a separate timed binary to avoid anchoring from the first pair.",
    domain: "archetype_hypothesis",
    criticality: "important",
    deadlineMs: 3000,
    options: [
      { id: "warm", label: "Warm, relational, close" },
      { id: "sharp", label: "Precise, independent, professional" },
    ],
  },
  {
    id: "brand.one_sentence_promise",
    phase: 1,
    mode: "freeform_short",
    prompt: "What is the single-sentence promise only you can make?",
    rationale:
      "Defines the unique-value axis that drives L3 edge generation. If you can't say it in a sentence, neither can your customer.",
    domain: "archetype_hypothesis",
    criticality: "critical",
    minChars: 15,
  },
  {
    id: "brand.not_for",
    phase: 1,
    mode: "freeform_long",
    prompt: "Who is your brand NOT for?",
    rationale:
      "Defines suppress-archetypes. Negative targeting matters as much as positive — without this, the system can waste spend on audiences that will actively reject your brand.",
    domain: "archetype_hypothesis",
    criticality: "critical",
    minChars: 30,
  },
  {
    id: "brand.emotion_after",
    phase: 1,
    mode: "k_afc",
    prompt: "What emotion do you want someone to feel after interacting with your brand?",
    rationale:
      "Directly seeds target EmotionalState priors. The system will emphasize mechanisms that evoke this family.",
    domain: "creative_voice",
    criticality: "important",
    options: [
      { id: "confidence", label: "Confidence — they made the right call" },
      { id: "pride", label: "Pride — associated with status or quality" },
      { id: "relief", label: "Relief — a real problem is handled" },
      { id: "excitement", label: "Excitement — anticipation of something new" },
      { id: "belonging", label: "Belonging — they're part of something" },
      { id: "control", label: "Control — they feel in command" },
    ],
  },
  {
    id: "brand.best_campaign_story",
    phase: 1,
    mode: "story",
    prompt: "Tell me about the best campaign you ever ran and exactly why it worked.",
    rationale:
      "Episodic recall beats semantic generalization. Specifics carry tacit knowledge the system can extract — which mechanism, which audience, which timing.",
    domain: "creative_voice",
    criticality: "important",
    minChars: 80,
  },
  {
    id: "brand.contrarian_belief",
    phase: 1,
    mode: "freeform_long",
    prompt: "What's a belief you hold that most of your category disagrees with?",
    rationale:
      "Differentiation signal. The contrarian angle is usually the creative wedge — and if the system doesn't know it, it will default to category conventions.",
    domain: "creative_voice",
    criticality: "inferable",
    minChars: 30,
  },

  // ============================================================
  // Phase 2 — Audience Hypothesis
  // ============================================================
  {
    id: "audience.jtbd",
    phase: 2,
    mode: "freeform_long",
    prompt:
      "When a customer 'hires' your product, what job are they trying to get done?",
    rationale:
      "Christensen's Jobs-to-be-Done frame. Replaces demographic targeting with functional goal targeting — which is how the auto-motive model actually works.",
    domain: "barrier_interpretation",
    criticality: "critical",
    minChars: 40,
  },
  {
    id: "audience.struggling_moment",
    phase: 2,
    mode: "freeform_long",
    prompt: "What's the 'struggling moment' that pushes someone to look for you?",
    rationale:
      "Triggers goal-activation priming. If we know the struggling moment, the platform can place ads where that moment is being activated nonconsciously.",
    domain: "barrier_interpretation",
    criticality: "critical",
    minChars: 30,
  },
  {
    id: "audience.trait_forced_pair",
    phase: 2,
    mode: "timed_pair",
    prompt: "Best customers: which of these feels more like them?",
    rationale:
      "Seeds trait posteriors. Timed so you answer from pattern-match memory, not category-positioning narrative.",
    domain: "audience_sizing",
    criticality: "important",
    deadlineMs: 3000,
    options: [
      { id: "deliberate", label: "Careful, researches before buying" },
      { id: "intuitive", label: "Moves fast on gut when something feels right" },
    ],
  },
  {
    id: "audience.mindset",
    phase: 2,
    mode: "k_afc",
    prompt:
      "What mindset are they in when they're most receptive to you?",
    rationale:
      "Maps to Mindset node weights and CREATES_MINDSET edge priors. Mindset targeting routes the campaign to contexts where the audience is pre-primed.",
    domain: "audience_sizing",
    criticality: "important",
    options: [
      {
        id: "seeking",
        label: "Seeking — actively looking for a solution",
      },
      {
        id: "curious",
        label: "Curious — exploring, open to options",
      },
      {
        id: "anxious",
        label: "Anxious — concerned about a problem",
      },
      {
        id: "aspirational",
        label: "Aspirational — imagining a better version of themselves",
      },
      {
        id: "frustrated",
        label: "Frustrated — tired of what they're using now",
      },
    ],
  },
  {
    id: "audience.purchase_trigger",
    phase: 2,
    mode: "k_afc",
    prompt: "What usually triggers the actual purchase?",
    rationale:
      "Temporal and contextual priming signal. Drives time-slot targeting and moment-of-receptivity bid modulation.",
    domain: "barrier_interpretation",
    criticality: "important",
    options: [
      { id: "event", label: "Life event (move, birthday, new job, etc.)" },
      { id: "seasonal", label: "Seasonal or calendar moment" },
      { id: "competitor_fail", label: "A competitor just failed them" },
      { id: "social", label: "Someone in their network talked about us" },
      { id: "budget", label: "A budget opened up" },
      { id: "other", label: "Other / I'd have to think" },
    ],
  },
  {
    id: "audience.three_best_customers",
    phase: 2,
    mode: "story",
    prompt:
      "Describe your three best customers — who they are, why they stayed, and what they have in common.",
    rationale:
      "Concrete anchors for archetype validation. Used as seed cohort for lookalike generation and as ground-truth for the buyer-side annotation layer.",
    domain: "audience_sizing",
    criticality: "important",
    minChars: 120,
  },
  {
    id: "audience.fear_of_losing",
    phase: 2,
    mode: "freeform_short",
    prompt: "What is your customer afraid of losing?",
    rationale:
      "Loss-frame input. Prospect theory says losses are valued ~2x gains — knowing the specific loss lets us choose between gain-frame and loss-frame creative.",
    domain: "barrier_interpretation",
    criticality: "important",
    minChars: 15,
  },
  {
    id: "audience.transformation",
    phase: 2,
    mode: "freeform_short",
    prompt: "What transformation do they want to achieve?",
    rationale:
      "Aspirational-state target. Goal-fulfillment stimulus selection runs from this answer — the ad presents itself as the affordance that completes their goal.",
    domain: "barrier_interpretation",
    criticality: "important",
    minChars: 15,
  },

  // ============================================================
  // Phase 3 — Campaign Objective & Success Definition
  // ============================================================
  {
    id: "objective.primary_behavior",
    phase: 3,
    mode: "k_afc",
    prompt: "What's the one behavior change this campaign must produce?",
    rationale:
      "Defines the reward signal for Thompson sampling. One and only one primary conversion event drives the optimization loop — everything else is secondary.",
    domain: "mechanism_selection",
    criticality: "critical",
    options: [
      { id: "purchase", label: "Purchase / booking" },
      { id: "lead", label: "Qualified lead / form fill" },
      { id: "signup", label: "Free signup / account creation" },
      { id: "visit", label: "Site visit / content view" },
      { id: "awareness", label: "Unaided awareness lift" },
      { id: "reactivation", label: "Reactivation of lapsed user" },
    ],
  },
  {
    id: "objective.cpa_targets",
    phase: 3,
    mode: "freeform_short",
    prompt:
      "What CPA would make this a win, a home-run, and a disaster? (e.g., win $80, home-run $50, disaster $200)",
    rationale:
      "Three-tier thresholds for the rollback monitor and for autopilot graduation. Without these the system can't know when to escalate to human review.",
    domain: "budget_pacing",
    criticality: "critical",
    minChars: 8,
  },
  {
    id: "objective.decision_window",
    phase: 3,
    mode: "k_afc",
    prompt: "What's the decision window from first exposure to conversion?",
    rationale:
      "Attribution window + credit-attribution horizon. Tight windows favor last-touch; long windows need full path attribution.",
    domain: "mechanism_selection",
    criticality: "critical",
    options: [
      { id: "same_day", label: "Same-day (impulse)" },
      { id: "one_week", label: "Within a week" },
      { id: "one_month", label: "Within a month" },
      { id: "one_quarter", label: "Within a quarter" },
      { id: "longer", label: "Longer / complex B2B cycle" },
    ],
  },
  {
    id: "objective.bad_outcome",
    phase: 3,
    mode: "freeform_long",
    prompt:
      "What does a bad outcome look like beyond low CVR — brand damage, wrong customers, PR risk?",
    rationale:
      "Backfire penalty signal. The system needs to know what to avoid, not just what to maximize — otherwise the reward function will optimize in ways that cost you.",
    domain: "mechanism_selection",
    criticality: "critical",
    minChars: 30,
  },
  {
    id: "objective.risk_appetite",
    phase: 3,
    mode: "timed_pair",
    prompt: "Gut read: is this a pilot or a bet-the-quarter campaign?",
    rationale:
      "Risk-appetite calibration. Scales the exploration bonus in Thompson sampling — conservative posture uses 0.5x, aggressive learning uses 2-3x.",
    domain: "mechanism_selection",
    criticality: "important",
    deadlineMs: 3000,
    options: [
      {
        id: "pilot",
        label: "Pilot — I'd rather learn than win big right now",
      },
      {
        id: "bet_big",
        label: "Bet-big — we need this one to land",
      },
    ],
  },
  {
    id: "objective.incremental",
    phase: 3,
    mode: "forced_pair",
    prompt: "Is this campaign incremental, or replacing something?",
    rationale:
      "Incrementality testing requirement. If replacing, we need a holdout cell to measure actual lift over baseline — otherwise we can't distinguish correlation from cause.",
    domain: "mechanism_selection",
    criticality: "important",
    options: [
      {
        id: "incremental",
        label: "Purely additive — new spend, new channel",
      },
      {
        id: "replacing",
        label: "Replacing or reallocating existing spend",
      },
    ],
  },
  {
    id: "objective.downstream",
    phase: 3,
    mode: "freeform_short",
    prompt:
      "What's the downstream event after the conversion pixel fires that actually matters to the business?",
    rationale:
      "Long-horizon reinforcement signal. The pixel event is a proxy; LTV, repeat purchase, or activation is the real target. If we know both, we can optimize for actual value, not vanity conversions.",
    domain: "mechanism_selection",
    criticality: "important",
    minChars: 15,
  },
];

/**
 * First-party data source types rendered in Phase 4. Each carries
 * the actual lift estimate the HMT foundation §11.5 specifies — the
 * ladder approach where we show the expected capability gain per
 * upload, so the ask is economic, not mandatory.
 */
export type DataSourceDefinition = {
  id: string;
  label: string;
  description: string;
  liftEstimate: string;
  unlocks: string;
  accepts?: string; // file MIME hint
};

export const DATA_SOURCES: DataSourceDefinition[] = [
  {
    id: "crm_export",
    label: "CRM export (CSV)",
    description:
      "Customer records with purchase history, LTV, lifecycle stage. Anonymized or hashed is fine.",
    liftEstimate: "+18% targeting precision",
    unlocks: "per-user Thompson posteriors, 6-level hierarchy",
    accepts: ".csv,text/csv",
  },
  {
    id: "reviews",
    label: "Customer reviews corpus",
    description:
      "500+ reviews ideally — your site, Amazon, Trustpilot, G2. The primary buyer-side psycholinguistic annotation source.",
    liftEstimate: "+27-dimension buyer annotation",
    unlocks: "bilateral edge generation at L3 of the cascade",
    accepts: ".csv,.json,.txt",
  },
  {
    id: "product_copy",
    label: "Product copy / PDPs",
    description:
      "Your own product description pages, spec sheets, landing copy. Used to generate the brand-side annotation.",
    liftEstimate: "+seller-side 27-dim annotation",
    unlocks: "L3 edge generation (brand-side)",
    accepts: ".html,.txt,.md,.json",
  },
  {
    id: "sales_calls",
    label: "Sales call transcripts",
    description:
      "The goldmine for JTBD struggling moments and barrier detection. Whisper-transcribed audio or text export.",
    liftEstimate: "+barrier self-report accuracy (Signal 2)",
    unlocks: "barrier-aware retargeting sequences",
    accepts: ".txt,.json,.vtt,.srt",
  },
  {
    id: "past_campaigns",
    label: "Past campaign performance",
    description:
      "Previous creative + targeting + outcome rows. Warm-starts the mechanism-effectiveness registry.",
    liftEstimate: "+mechanism registry cold-start avoided",
    unlocks: "seeded archetype × mechanism priors",
    accepts: ".csv,.json",
  },
  {
    id: "pixel_sdk",
    label: "INFORMATIV pixel / telemetry SDK",
    description:
      "Install the telemetry script on your site to capture the six nonconscious signals (click latency, processing depth, barrier self-report, etc).",
    liftEstimate: "+6 nonconscious signals (Enhancement #34)",
    unlocks: "click-latency, processing-depth, frequency-decay detection",
  },
  {
    id: "email_engagement",
    label: "Email list + engagement profile",
    description: "List size, open/click rates, segmentation. Retargeting seed + lookalike base.",
    liftEstimate: "+repeat-measures per-user calibration",
    unlocks: "within-subject learning (Enhancement #36)",
    accepts: ".csv",
  },
  {
    id: "support_tickets",
    label: "Support tickets / live chat transcripts",
    description: "Barrier self-report corpus. Feeds directly into the barrier-detection engine.",
    liftEstimate: "+barrier-class coverage",
    unlocks: "proactive-barrier retargeting",
    accepts: ".csv,.json,.txt",
  },
];

/**
 * Helper to get questions for a specific phase.
 */
export function questionsForPhase(phase: 1 | 2 | 3 | 4): DiscoveryQuestion[] {
  return DISCOVERY_QUESTIONS.filter((q) => q.phase === phase);
}
