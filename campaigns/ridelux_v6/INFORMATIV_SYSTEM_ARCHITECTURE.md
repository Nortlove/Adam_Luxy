# INFORMATIV System Architecture
## Complete Technical Architecture for the LUXY Ride Pilot

---

```
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                              ║
║                         INFORMATIV PLATFORM                                  ║
║                   Psychological Intelligence Engine                          ║
║                                                                              ║
║   "We don't target audiences. We engineer the conditions for                 ║
║    psychological resonance at the moment of impression."                     ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝


═══════════════════════════════════════════════════════════════════════════════
 LAYER 1: EXTERNAL INTERFACES
═══════════════════════════════════════════════════════════════════════════════

  ┌──────────────────┐      ┌───────────────────┐     ┌──────────────────────┐
  │   STACKADAPT     │     │   LUXY RIDE       │     │   INFORMATIV API     │
  │   DSP Platform   │     │   Website         │     │   Port 8000          │
  │                  │     │                   │     │                      │
  │  Sends:          │     │  Sends:           │     │  Serves:             │
  │  • Bid requests  │     │  • Pixel events   │     │  • /health           │
  │  • Impression    │     │  • Conversions    │     │  • /metrics          │
  │    notifications │     │  • Page visits    │     │  • /api/v1/decisions │
  │  • Conversion    │     │                   │     │  • /api/v1/stackadapt│
  │    webhooks      │     │  Via:             │     │  • /api/v1/universal │
  │                  │     │  Universal Pixel   │     │                      │
  │  Receives:       │     │  (sa-XXXXXXXX)    │     │  Auth: X-API-Key     │
  │  • Segment IDs   │     │                   │     │  Latency: <120ms     │
  │  • Creative copy │     │  Events:          │     │                      │
  │  • Bid guidance  │     │  • site_visit     │     │  Workers: 4          │
  │  • Domain lists  │     │  • pricing_view   │     │  (uvicorn + uvloop)  │
  │                  │     │  • booking_start  │     │                      │
  └────────┬─────────┘     │  • booking_done   │     └──────────┬───────────┘
           │               └─────────┬─────────┘                │
           │                         │                          │
           ▼                         ▼                          │
  ┌─────────────────────────────────────────────────┐            │
  │              WEBHOOK HANDLER                    │◄───────────┘
  │              /api/v1/stackadapt/webhook         │
  │                                                 │
  │  1. Validate HMAC-SHA256 signature              │
  │  2. Deduplicate by event_id                     │
  │  3. Map event → decision context                │
  │     Try 1: decision_id in event_args            │
  │     Try 2: buyer + segment lookup               │
  │     Try 3: Neo4j durable fallback               │
  │  4. Route to OutcomeHandler                     │
  │                                                 │
  │  Rate limited: IP-based sliding window          │
  └────────────────────┬────────────────────────────┘
                       │
                       ▼

═══════════════════════════════════════════════════════════════════════════════
 LAYER 2: BILATERAL INTELLIGENCE CASCADE
═══════════════════════════════════════════════════════════════════════════════

  When an impression opportunity arrives (or when generating creative),
  the system runs a 5-level cascade of increasing depth and evidence:

  ┌─────────────────────────────────────────────────────────────────────────┐
  │                                                                         │
  │   SEGMENT: informativ_corporate_executive_luxury_transportation_t1      │
  │                          │                                              │
  │              ┌───────────▼────────────┐                                 │
  │              │  SEGMENT PARSER        │                                 │
  │              │  archetype: careful_   │                                 │
  │              │    truster             │                                 │
  │              │  category: luxury_     │                                 │
  │              │    transportation      │                                 │
  │              │  ASIN: lux_luxy_ride   │                                 │
  │              └───────────┬────────────┘                                 │
  │                          │                                              │
  │   ┌──────────────────────▼───────────────────────┐                       │
  │   │                                              │                      │
  │   │  LEVEL 1: ARCHETYPE PRIOR         <2ms       │                      │
  │   │  ─────────────────────────────────────       │                      │
  │   │  In-memory archetype mechanism priors.       │                      │
  │   │  8 archetypes × 10 mechanisms = 80 cells.    │                      │
  │   │  Cold-start baseline. Confidence: 0.30       │                      │
  │   │                                              │                      │
  │   │  Output: authority (0.35), social_proof      │                      │
  │   │  (0.30), commitment (0.25)                   │                      │
  │   │                                              │                      │
  │   └──────────────────────┬───────────────────────┘                       │
  │                          │ + category data?                             │
  │   ┌──────────────────────▼───────────────────────┐                       │
  │   │                                              │                      │
  │   │  LEVEL 2: CATEGORY POSTERIOR      2-10ms     │                      │
  │   │  ─────────────────────────────────────       │                      │
  │   │  BayesianPrior nodes from Neo4j.             │                      │
  │   │  Category-specific mechanism effectiveness.  │                      │
  │   │  474 BayesianPrior nodes across categories.  │                      │
  │   │  Confidence: 0.50                            │                      │
  │   │                                              │                      │
  │   └──────────────────────┬───────────────────────┘                       │
  │                          │ + ASIN data?                                 │
  │   ┌──────────────────────▼───────────────────────┐                       │
  │   │                                              │                      │
  │   │  ★ LEVEL 3: BILATERAL EDGES       10-30ms    │                      │
  │   │  ─────────────────────────────────────       │                      │
  │   │  THE CORE INTELLIGENCE LAYER                 │                      │
  │   │                                              │                      │
  │   │  Queries BRAND_CONVERTED edges for this      │                      │
  │   │  ASIN × archetype. Each edge has 20          │                      │
  │   │  Claude-annotated psychological dimensions   │                      │
  │   │  from real buyer-product interactions.       │                      │
  │   │                                              │                      │
  │   │  LUXY Ride edges by archetype:               │                      │
  │   │    careful_truster:  283 edges               │                      │
  │   │    status_seeker:    192 edges               │                      │
  │   │    easy_decider:      37 edges               │                      │
  │   │                                              │                      │
  │   │  20 DIMENSIONS PER EDGE:                     │                      │
  │   │  ┌───────────────────────────────────────┐   │                      │
  │   │  │ Core 7:                               │   │                      │
  │   │  │  regulatory_fit        = -0.082       │   │                      │
  │   │  │  construal_fit         =  0.894       │   │                      │
  │   │  │  personality_alignment =  0.419       │   │                      │
  │   │  │  emotional_resonance   =  0.367       │   │                      │
  │   │  │  value_alignment       =  0.620       │   │                      │
  │   │  │  evolutionary_motive   =  0.520       │   │                      │
  │   │  │  linguistic_style      =  0.987       │   │                      │
  │   │  │                                       │   │                      │
  │   │  │ Extended 13 (Claude-annotated):       │    │                      │
  │   │  │  cognitive_load_tolerance = 0.817     │    │                      │
  │   │  │  social_proof_sensitivity = 0.195     │    │                      │
  │   │  │  autonomy_reactance       = 0.051     │    │                      │
  │   │  │  decision_entropy         = 0.213     │    │                      │
  │   │  │  loss_aversion_intensity  = 0.636     │    │                      │
  │   │  │  narrative_transport      = 0.382     │    │                      │
  │   │  │  mimetic_desire           = 0.280     │    │                      │
  │   │  │  brand_relationship_depth = 0.453     │    │                      │
  │   │  │  information_seeking      = 0.418     │    │                      │
  │   │  │  interoceptive_awareness  = 0.212     │    │                      │
  │   │  │  cooperative_framing_fit  = 0.437     │    │                      │
  │   │  │  persuasion_susceptibility= 1.000     │    │                      │
  │   │  │  temporal_discounting     = 0.434     │    │                      │
  │   │  └───────────────────────────────────────┘    │                      │
  │   │                                              │                      │
  │   │  Derives: framing (loss), construal          │                      │
  │   │  (abstract), tone (balanced),                │                      │
  │   │  mechanism (authority), lift (38.4%)          │                      │
  │   │  Confidence: 0.90                            │                      │
  │   │                                              │                      │
  │   └──────────────────────┬──────────────────────┘                       │
  │                          │                                              │
  │   ┌──────────────────────▼──────────────────────┐                       │
  │   │                                              │                      │
  │   │  LEVEL 4: INFERENTIAL TRANSFER    30-100ms  │                      │
  │   │  ─────────────────────────────────────       │                      │
  │   │  When L3 has insufficient edges (<10),       │                      │
  │   │  uses ProductDescription node + theory       │                      │
  │   │  graph for zero-shot mechanism inference.    │                      │
  │   │                                              │                      │
  │   └──────────────────────┬──────────────────────┘                       │
  │                          │                                              │
  │   OUTPUT: CreativeIntelligence                                          │
  │   ├── primary_mechanism: authority                                      │
  │   ├── framing: loss                                                     │
  │   ├── construal_level: abstract                                         │
  │   ├── tone: balanced                                                    │
  │   ├── edge_dimensions: {20 dimensions}                                  │
  │   ├── mechanism_scores: {10 mechanisms ranked}                          │
  │   ├── gradient_intelligence: {12 optimization vectors}                  │
  │   └── conversion_lift_pct: 38.4%                                        │
  │                                                                         │
  └─────────────────────────────────────────────────────────────────────────┘


═══════════════════════════════════════════════════════════════════════════════
 LAYER 3: INTELLIGENCE PREFETCH (11 sources)
═══════════════════════════════════════════════════════════════════════════════

  Runs BEFORE the Atom DAG. Queries Neo4j + corpus for all available
  intelligence on this buyer × product combination.

  ┌─────────────────────────────────────────────────────────────────────────┐
  │                                                                         │
  │  INTELLIGENCE PREFETCH SERVICE                                          │
  │  ─────────────────────────────                                          │
  │                                                                         │
  │  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐      │
  │  │ 1. Bilateral     │  │ 2. Mechanism     │  │ 3. NDF           │      │
  │  │    Edge Dims     │  │    Priors        │  │    Intelligence  │      │
  │  │                  │  │                  │  │                  │      │
  │  │ 20 dimensions    │  │ RESPONDS_TO      │  │ 7+1 compressed  │      │
  │  │ from L3 edges    │  │ edges per        │  │ dimensions      │      │
  │  │ per archetype    │  │ archetype        │  │ (fallback only) │      │
  │  └──────────────────┘  └──────────────────┘  └──────────────────┘      │
  │                                                                         │
  │  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐      │
  │  │ 4. Expanded      │  │ 5. Dimensional   │  │ 6. DSP Graph     │      │
  │  │    Customer Type │  │    Priors        │  │    Intelligence  │      │
  │  │                  │  │                  │  │                  │      │
  │  │ 7-dim buyer      │  │ 430+ corpus-     │  │ Empirical        │      │
  │  │ profile from     │  │ aggregated       │  │ effectiveness    │      │
  │  │ archetype        │  │ dimensions       │  │ + synergies      │      │
  │  └──────────────────┘  └──────────────────┘  └──────────────────┘      │
  │                                                                         │
  │  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐      │
  │  │ 7. Graph Type    │  │ 8. Corpus        │  │ 9. Theory        │      │
  │  │    Inference     │  │    Fusion        │  │    Chains        │      │
  │  │                  │  │                  │  │                  │      │
  │  │ 1.9M Granular    │  │ 941M review-     │  │ State→Need→      │      │
  │  │ Type traversal   │  │ derived priors   │  │ Mechanism        │      │
  │  │                  │  │                  │  │ causal chains    │      │
  │  └──────────────────┘  └──────────────────┘  └──────────────────┘      │
  │                                                                         │
  │  ┌──────────────────┐  ┌──────────────────┐                            │
  │  │ 10. GDS          │  │ 11. Discovered   │                            │
  │  │     Algorithms   │  │     Patterns     │                            │
  │  │                  │  │                  │                            │
  │  │ PageRank,        │  │ Brand pattern    │                            │
  │  │ Node Similarity, │  │ learner          │                            │
  │  │ Community Det.   │  │ discoveries      │                            │
  │  └──────────────────┘  └──────────────────┘                            │
  │                                                                         │
  │  OUTPUT: ad_context dict with all sources                               │
  │  Per-fetch timeout + circuit breaker protection                         │
  │  Budget-aware: skips slow sources when latency budget exhausted         │
  │                                                                         │
  └─────────────────────────────────────────────────────────────────────────┘


═══════════════════════════════════════════════════════════════════════════════
 LAYER 4: ATOM OF THOUGHT DAG (14 Psychological Reasoning Atoms)
═══════════════════════════════════════════════════════════════════════════════

  Each atom is a specialized psychological reasoner that produces
  a per-request assessment. Atoms run in parallel within levels.

  ┌─────────────────────────────────────────────────────────────────────────┐
  │                                                                         │
  │  LEVEL 0 ─────────────────────────────────────────────────────────      │
  │  ┌────────────────┐                                                     │
  │  │  USER STATE    │  Assesses arousal, cognitive load, emotional        │
  │  │                │  valence, engagement, temporal pressure.            │
  │  │  Foundation    │  All other atoms depend on this.                    │
  │  └───────┬────────┘                                                     │
  │          │                                                              │
  │  LEVEL 1 ──────────────── 9 atoms in parallel ───────────────────      │
  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐  │
  │  │ REGULATORY   │ │ CONSTRUAL    │ │ PERSONALITY  │ │ REVIEW       │  │
  │  │ FOCUS        │ │ LEVEL        │ │ EXPRESSION   │ │ INTELLIGENCE │  │
  │  │              │ │              │ │              │ │              │  │
  │  │ Promotion vs │ │ 4-distance   │ │ Big Five     │ │ Mechanism    │  │
  │  │ prevention   │ │ CLT (Trope   │ │ trait        │ │ predictions  │  │
  │  │ (Higgins)    │ │ & Liberman)  │ │ matching     │ │ from reviews │  │
  │  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘  │
  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐  │
  │  │ COGNITIVE    │ │ DECISION     │ │ INFORMATION  │ │ PREDICTIVE   │  │
  │  │ LOAD         │ │ ENTROPY      │ │ ASYMMETRY    │ │ ERROR        │  │
  │  │              │ │              │ │              │ │              │  │
  │  │ System 1/2   │ │ Shannon      │ │ Nelson good  │ │ Goldilocks   │  │
  │  │ filtering    │ │ entropy of   │ │ type (search │ │ surprise     │  │
  │  │ (Kahneman)   │ │ decision     │ │ /experience  │ │ zone         │  │
  │  │              │ │ (info theory)│ │ /credence)   │ │ (Friston)    │  │
  │  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘  │
  │  ┌──────────────┐                                                      │
  │  │ AMBIGUITY    │                                                      │
  │  │ ATTITUDE     │  Risk vs ambiguity preference (Ellsberg 1961)        │
  │  └──────────────┘                                                      │
  │          │                                                              │
  │  LEVEL 2 ─────────────────────────────────────────────────────────      │
  │  ┌──────────────────────────────────────────────────────────────┐      │
  │  │                MECHANISM ACTIVATION                          │      │
  │  │                                                              │      │
  │  │  THE CENTRAL ATOM — synthesizes all upstream assessments     │      │
  │  │                                                              │      │
  │  │  15 scoring layers (evidence-weighted blending):             │      │
  │  │  1. Graph-inferred (RESPONDS_TO edges)                      │      │
  │  │  2. Unified three-layer service                             │      │
  │  │  3. Static heuristic (fallback)                             │      │
  │  │  4. Auxiliary atom adjustments (5 atoms, confidence-weighted)│      │
  │  │  5. Extended framework adjustments                          │      │
  │  │  6. Susceptibility scoring                                  │      │
  │  │  7. NDF susceptibility (SKIPPED when edges available)       │      │
  │  │  8. Alignment + dimensional priors                          │      │
  │  │  9. Corpus fusion priors (941M reviews)                     │      │
  │  │  10. Edge dimension scoring (20-dim parity with L3)         │      │
  │  │  11. Information value weighting (uncertainty × gradient)    │      │
  │  │  12. Discovered patterns                                    │      │
  │  │  13. GDS intelligence                                       │      │
  │  │  14. Credit journey adjustments                             │      │
  │  │  15. Exploration flattening (cold buyers explore more)      │      │
  │  │                                                              │      │
  │  │  Output: ranked mechanisms + weights + confidence            │      │
  │  └──────────────────────────────────────────────────────────────┘      │
  │          │                                                              │
  │  LEVEL 3 ─────────────────────────────────────────────────────────      │
  │  ┌──────────────────┐  ┌──────────────────┐                            │
  │  │ MESSAGE FRAMING  │  │ CHANNEL          │                            │
  │  │                  │  │ SELECTION        │                            │
  │  │ Gain/loss frame  │  │ (iHeart          │                            │
  │  │ from mechanism + │  │ integration)     │                            │
  │  │ regulatory focus │  │                  │                            │
  │  └──────────────────┘  └──────────────────┘                            │
  │          │                                                              │
  │  LEVEL 4 ─────────────────────────────────────────────────────────      │
  │  ┌──────────────────┐                                                   │
  │  │ AD SELECTION     │  Final scoring of ad candidates.                  │
  │  │                  │  Uses bilateral edge dimensions for brand         │
  │  │                  │  compatibility. Mechanism registry for            │
  │  │                  │  evidence-weighted selection.                     │
  │  └──────────────────┘                                                   │
  │                                                                         │
  └─────────────────────────────────────────────────────────────────────────┘


═══════════════════════════════════════════════════════════════════════════════
 LAYER 5: COPY GENERATION (Bilateral Intelligence → Words on Screen)
═══════════════════════════════════════════════════════════════════════════════

  ┌─────────────────────────────────────────────────────────────────────────┐
  │                                                                         │
  │  COPY GENERATION SERVICE                                                │
  │  ──────────────────────                                                 │
  │                                                                         │
  │  Layer 1: EDGE DIMENSIONS → Copy Parameters                             │
  │  ┌────────────────────────────────────────────────────────────────┐     │
  │  │  cognitive_load_tolerance 0.82 → complex arguments allowed     │     │
  │  │  emotional_resonance     0.37 → rational appeal preferred      │     │
  │  │  autonomy_reactance      0.05 → no need to back off pressure   │     │
  │  │  social_proof_sensitivity 0.20 → do NOT use popularity claims  │     │
  │  │  loss_aversion_intensity 0.64 → loss framing effective         │     │
  │  └────────────────────────────────────────────────────────────────┘     │
  │                                                                         │
  │  Layer 2: GRADIENT PRIORITIES → Creative Direction                      │
  │  ┌────────────────────────────────────────────────────────────────┐     │
  │  │  Top gradient: social_proof_sensitivity (+0.48)                │     │
  │  │  → optimizing this dimension has highest conversion lift       │     │
  │  │  → but buyer sps is LOW (0.20) — DON'T use social proof       │     │
  │  │  → instead: authority + evidence (matches buyer's clt=0.82)   │     │
  │  └────────────────────────────────────────────────────────────────┘     │
  │                                                                         │
  │  Layer 3: CONSTRUCT CREATIVE ENGINE → CreativeSpec                      │
  │  ┌────────────────────────────────────────────────────────────────┐     │
  │  │  Graph-inferred construct activations → message_frame, tone,   │     │
  │  │  CTA, imagery, constraints, vulnerability protections          │     │
  │  └────────────────────────────────────────────────────────────────┘     │
  │                                                                         │
  │  Layer 4: CORPUS FUSION → Creative Constraints                          │
  │  ┌────────────────────────────────────────────────────────────────┐     │
  │  │  941M review-derived patterns: what language patterns          │     │
  │  │  correlate with conversion in this category?                   │     │
  │  └────────────────────────────────────────────────────────────────┘     │
  │                                                                         │
  │  Layer 5: BARRIER + NARRATIVE + THEORY → Psychological Prompt           │
  │  ┌────────────────────────────────────────────────────────────────┐     │
  │  │  <bilateral_intelligence>                                      │     │
  │  │    20 dimensions with creative guidance                        │     │
  │  │  <barrier_diagnosis>                                           │     │
  │  │    negativity_block: acknowledge, don't dismiss, counter-      │     │
  │  │    evidence                                                    │     │
  │  │  <narrative_position>                                          │     │
  │  │    Touch 3/5, Chapter 3: RISING ACTION — show path to          │     │
  │  │    resolution                                                  │     │
  │  │  <mechanism>                                                   │     │
  │  │    authority: verifiable evidence, numbers, credentials        │     │
  │  │  → Claude Opus generates headline/body/CTA from COMPLETE      │     │
  │  │    system intelligence (~4,500 char prompt)                    │     │
  │  └────────────────────────────────────────────────────────────────┘     │
  │                                                                         │
  │  OUTPUT: "47,000 executives trust LUXY with their reputation"           │
  │          "Independent audit: 99.7% on-time arrival rate..."             │
  │          [See proof]                                                     │
  │                                                                         │
  └─────────────────────────────────────────────────────────────────────────┘


═══════════════════════════════════════════════════════════════════════════════
 LAYER 6: RESONANCE ENGINE (Trilateral Intelligence)
═══════════════════════════════════════════════════════════════════════════════

  The third dimension: buyer × seller × PAGE.
  The page creates a psychological field that amplifies or dampens
  the bilateral signal.

  ┌─────────────────────────────────────────────────────────────────────────┐
  │                                                                         │
  │  SENSE ──────────────────────────────────────────────────────────       │
  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                  │
  │  │ Page Crawl   │  │ Page         │  │ Browsing     │                  │
  │  │ Scheduler    │  │ Intelligence │  │ Momentum     │                  │
  │  │              │  │              │  │ Tracker      │                  │
  │  │ Bi-daily +   │  │ 15-layer     │  │              │                  │
  │  │ priority     │  │ psychological│  │ Compound     │                  │
  │  │ queue for    │  │ profile per  │  │ priming from │                  │
  │  │ conversion-  │  │ page. 20-dim │  │ multi-page   │                  │
  │  │ triggered    │  │ edge scoring │  │ sessions     │                  │
  │  │ deep crawls  │  │              │  │              │                  │
  │  └──────────────┘  └──────────────┘  └──────────────┘                  │
  │                                                                         │
  │  MODEL ──────────────────────────────────────────────────────────       │
  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                  │
  │  │ Resonance    │  │ Page         │  │ Competitive  │                  │
  │  │ Model        │  │ Gradient     │  │ Displacement │                  │
  │  │              │  │ Fields       │  │ Detector     │                  │
  │  │ Cell-based:  │  │              │  │              │                  │
  │  │ [archetype,  │  │ ∂P/∂page_dim │  │ Mechanism    │                  │
  │  │  mechanism,  │  │ per          │  │ fatigue per  │                  │
  │  │  barrier,    │  │ (mechanism,  │  │ domain.      │                  │
  │  │  touch,      │  │  barrier)    │  │ Open channel │                  │
  │  │  page_cluster│  │              │  │ detection.   │                  │
  │  │ ]            │  │ "Which page  │  │              │                  │
  │  │              │  │ dims CAUSE   │  │ "What's NOT  │                  │
  │  │ Stage A→B→C  │  │ mechanism    │  │ saturated    │                  │
  │  │ progression  │  │ effectiveness│  │ on this      │                  │
  │  │              │  │ ?"           │  │ page?"       │                  │
  │  └──────────────┘  └──────────────┘  └──────────────┘                  │
  │                                                                         │
  │  MATCH ──────────────────────────────────────────────────────────       │
  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                  │
  │  │ Placement    │  │ Congruence/  │  │ Page         │                  │
  │  │ Optimizer    │  │ Contrast     │  │ Similarity   │                  │
  │  │              │  │ Strategy     │  │ Index        │                  │
  │  │ Bid          │  │              │  │              │                  │
  │  │ multipliers  │  │ Dahlén 2005: │  │ Cosine sim   │                  │
  │  │ from         │  │ High-NfC     │  │ on 20-dim    │                  │
  │  │ resonance    │  │ buyers may   │  │ edge space.  │                  │
  │  │ scores.      │  │ respond to   │  │ Finds pages  │                  │
  │  │ 0.3x - 2.5x │  │ CONTRAST,    │  │ similar to   │                  │
  │  │              │  │ not match.   │  │ converters.  │                  │
  │  └──────────────┘  └──────────────┘  └──────────────┘                  │
  │                                                                         │
  │  ADAPT ──────────────────────────────────────────────────────────       │
  │  ┌───────────────────────────────────────────────────────────────┐      │
  │  │ CREATIVE ADAPTATION (<5ms)                                    │      │
  │  │                                                               │      │
  │  │ When ad lands on a page, read the cached profile and          │      │
  │  │ adapt copy parameters WITHOUT regeneration:                   │      │
  │  │                                                               │      │
  │  │ Analytical page → evidence_type: "data"                       │      │
  │  │ Emotional page  → evidence_type: "testimonial"                │      │
  │  │ High autonomy   → urgency: reduced                            │      │
  │  │                                                               │      │
  │  │ Same mechanism, different execution per page context.         │      │
  │  └───────────────────────────────────────────────────────────────┘      │
  │                                                                         │
  └─────────────────────────────────────────────────────────────────────────┘


═══════════════════════════════════════════════════════════════════════════════
 LAYER 7: CAUSAL INTELLIGENCE LOOP (The Learning Engine)
═══════════════════════════════════════════════════════════════════════════════

  This is where the system becomes INTELLIGENT — not just reactive.
  Every conversion triggers a cascade of causal reasoning that
  compounds the system's understanding of WHY things work.

  ┌─────────────────────────────────────────────────────────────────────────┐
  │                                                                         │
  │  CONVERSION EVENT                                                       │
  │       │                                                                 │
  │       ▼                                                                 │
  │  ┌──────────────────────────────────────────────────────────────┐       │
  │  │  OUTCOME HANDLER (20 learning paths)                         │       │
  │  │                                                              │       │
  │  │  1. Thompson Sampling posteriors                             │       │
  │  │  2. Meta-orchestrator strategy                               │       │
  │  │  3. Neo4j outcome attribution edges                          │       │
  │  │  4. Graph rewriter rule effectiveness                        │       │
  │  │  5. Unified Learning Hub (→ all 14 atoms)                    │       │
  │  │  6. ML ensemble weights                                     │       │
  │  │  7. Theory learner (construct-level Bayesian update)         │       │
  │  │  8. DSP impression learning                                 │       │
  │  │  9. Cognitive learning system (alignment matrices)           │       │
  │  │  10. Page-context-conditioned learning                       │       │
  │  │  10b. PAGE GRADIENT ACCUMULATION                             │       │
  │  │  11. Mechanism interaction (portfolio covariance)            │       │
  │  │  12. Bilateral edge evidence update                          │       │
  │  │  13. Therapeutic retargeting posteriors (5-level hierarchy)   │       │
  │  │  14. RESONANCE ENGINE LEARNING                               │       │
  │  │  15. CONVERSION-TRIGGERED PRIORITY CRAWL                     │       │
  │  │  16. COPY EFFECTIVENESS LEARNING                             │       │
  │  │  17. CAUSAL DECOMPOSITION + HYPOTHESIS GENERATION            │       │
  │  │  17b. COUNTERFACTUAL TRACKING                                │       │
  │  │  18. PREDICTION VALIDATION                                   │       │
  │  └──────────────────────┬───────────────────────────────────────┘       │
  │                         │                                               │
  │                         ▼                                               │
  │  ┌─────────────────────────────────────────────────────┐                │
  │  │  CAUSAL DECOMPOSITION ENGINE                         │                │
  │  │                                                      │                │
  │  │  Intersects THREE intelligence sources to isolate    │                │
  │  │  the 3-5 dimensions that were the ACTIVE CAUSAL      │                │
  │  │  INGREDIENTS for this specific conversion:           │                │
  │  │                                                      │                │
  │  │  Source 1: Buyer gradient field                      │                │
  │  │           ∂P/∂buyer_dim → which buyer dims mattered  │                │
  │  │                                                      │                │
  │  │  Source 2: Page gradient field                       │                │
  │  │           ∂P/∂page_dim → which page dims amplified   │                │
  │  │                                                      │                │
  │  │  Source 3: Theory graph                              │                │
  │  │           State→Need→Mechanism → which causal chain  │                │
  │  │                                                      │                │
  │  │  INTERSECTION → CAUSAL RECIPE                        │                │
  │  │  Example: {clt > 0.67, sps < 0.34, ar < 0.2}        │                │
  │  │           + theory: low_uncertainty → need_for_       │                │
  │  │             closure → authority via central route     │                │
  │  └────────────────────────┬────────────────────────────┘                │
  │                           │                                             │
  │                           ▼                                             │
  │  ┌─────────────────────────────────────────────────────┐                │
  │  │  INFERENTIAL HYPOTHESIS ENGINE                       │                │
  │  │                                                      │                │
  │  │  From the causal recipe, generates TRANSFERABLE      │                │
  │  │  hypotheses backed by theory:                        │                │
  │  │                                                      │                │
  │  │  "authority converts when clt > 0.67 AND sps < 0.34  │                │
  │  │   AND ar < 0.2, BECAUSE low_uncertainty_tolerance    │                │
  │  │   → need_for_closure → authority satisfies that      │                │
  │  │   need through central processing route"             │                │
  │  │                                                      │                │
  │  │  Each hypothesis:                                    │                │
  │  │  ├── Conditions (dimensional thresholds)             │                │
  │  │  ├── Prediction (mechanism + effectiveness)          │                │
  │  │  ├── Theory basis (causal chain + citation)          │                │
  │  │  ├── Falsification criteria                          │                │
  │  │  ├── Info value rank (uncertainty × impact ×         │                │
  │  │  │   transferability)                                │                │
  │  │  └── Status: generated → tested → validated/invalid  │                │
  │  │                                                      │                │
  │  │  INFORMATION VALUE RANKING:                          │                │
  │  │  Tests the hypothesis that teaches the MOST about    │                │
  │  │  the causal structure FIRST. Cold-start principle    │                │
  │  │  applied to hypothesis testing.                      │                │
  │  └────────────────────────┬────────────────────────────┘                │
  │                           │                                             │
  │                           ▼                                             │
  │  ┌─────────────────────────────────────────────────────┐                │
  │  │  PREDICTION ENGINE                                   │                │
  │  │                                                      │                │
  │  │  Finds SPECIFIC pages matching hypothesis conditions: │                │
  │  │                                                      │                │
  │  │  → skift.com matches (clt=0.95, sps=0.30, ar=0.15)  │                │
  │  │    Deploy authority, bid 1.2x, track as pred_000001  │                │
  │  │                                                      │                │
  │  │  → travelweekly.com matches (clt=0.85, sps=0.25)    │                │
  │  │    Deploy authority, bid 1.2x, track as pred_000002  │                │
  │  │                                                      │                │
  │  │  ACTIVE TRIGGERING:                                  │                │
  │  │  If no pages match → crawl domains likely to have    │                │
  │  │  matching pages → score → deploy if conditions met   │                │
  │  │                                                      │                │
  │  │  Every prediction is TRACKABLE. Outcomes feed back   │                │
  │  │  through path #18 to validate or invalidate.         │                │
  │  └────────────────────────┬────────────────────────────┘                │
  │                           │                                             │
  │                           ▼                                             │
  │  ┌─────────────────────────────────────────────────────┐                │
  │  │  COMPOUNDING                                         │                │
  │  │                                                      │                │
  │  │  Validated hypotheses:                               │                │
  │  │  ├── Transfer to ALL contexts with same conditions   │                │
  │  │  ├── Strengthen theory graph links                   │                │
  │  │  ├── Generate DERIVED hypotheses                     │                │
  │  │  │   ("if authority works via central route when     │                │
  │  │  │    clt > 0.67, THEN evidence_proof should too")   │                │
  │  │  └── Improve future predictions                      │                │
  │  │                                                      │                │
  │  │  Invalidated hypotheses:                             │                │
  │  │  ├── Narrow conditions                               │                │
  │  │  ├── Weaken theory links                             │                │
  │  │  └── Revise causal model                             │                │
  │  │                                                      │                │
  │  │  After 20 conversions: 6 validated hypotheses        │                │
  │  │  After 50: prediction accuracy measurably improving  │                │
  │  │  After 200: system makes predictions no human could  │                │
  │  └─────────────────────────────────────────────────────┘                │
  │                                                                         │
  └─────────────────────────────────────────────────────────────────────────┘


═══════════════════════════════════════════════════════════════════════════════
 LAYER 8: DATA LAYER
═══════════════════════════════════════════════════════════════════════════════

  ┌─────────────────────────┐     ┌─────────────────────────┐
  │       NEO4J              │     │        REDIS             │
  │                          │     │                          │
  │  6,743,384 edges         │     │  Decision cache          │
  │  3,103 luxury transport  │     │  Buyer profiles          │
  │  20 dims per edge        │     │  Thompson posteriors     │
  │  (Claude-annotated)      │     │  Page intelligence       │
  │                          │     │  Resonance cache         │
  │  Theory graph:           │     │  Session state           │
  │  14 PsychologicalState   │     │                          │
  │  15 PsychologicalNeed    │     │  14 cache domains        │
  │  10 CognitiveMechanism   │     │  All keys with TTL       │
  │  5 ProcessingRoute       │     │  (no infinite TTL leak)  │
  │  49 causal edges         │     │                          │
  │                          │     │  Queue: 10K max          │
  │  474 BayesianPrior nodes │     │  (bounded, non-blocking) │
  │  524 Construct nodes     │     │                          │
  │  Gradient fields         │     │                          │
  │                          │     │                          │
  └─────────────────────────┘     └─────────────────────────┘


═══════════════════════════════════════════════════════════════════════════════
 LAYER 9: HARDENING & OBSERVABILITY
═══════════════════════════════════════════════════════════════════════════════

  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
  │ LATENCY BUDGET   │  │ CIRCUIT BREAKERS │  │ PROMETHEUS       │
  │                  │  │                  │  │ METRICS          │
  │ 120ms SLA        │  │ neo4j: 50ms      │  │                  │
  │ 10ms reserve     │  │ redis: 20ms      │  │ cascade_level    │
  │ Cascade: 60ms    │  │ prefetch: 40ms   │  │ prefetch_sources │
  │ Prefetch: 40ms   │  │                  │  │ mechanism_select │
  │ DAG: 80ms        │  │ Opens after 5    │  │ posterior_mean   │
  │                  │  │ failures.        │  │ budget_usage     │
  │ Graceful         │  │ Half-open 30s.   │  │ circuit_state    │
  │ degradation:     │  │ Auto-recovery.   │  │ prediction_acc   │
  │ L3 → L2 → L1    │  │                  │  │                  │
  └──────────────────┘  └──────────────────┘  └──────────────────┘

  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
  │ THREAD SAFETY    │  │ PERSISTENCE      │  │ AUTH             │
  │                  │  │                  │  │                  │
  │ RLock on prior   │  │ Auto-persist     │  │ X-API-Key header │
  │ manager.         │  │ every 100        │  │ /health exempt   │
  │ Per-sequence     │  │ updates or 60s.  │  │ /metrics exempt  │
  │ asyncio.Lock.    │  │ Neo4j fallback   │  │ HMAC webhook     │
  │ LinUCB lock.     │  │ for decision     │  │ auth             │
  │                  │  │ context.         │  │                  │
  └──────────────────┘  └──────────────────┘  └──────────────────┘


═══════════════════════════════════════════════════════════════════════════════
 LAYER 10: RETARGETING SEQUENCE ENGINE
═══════════════════════════════════════════════════════════════════════════════

  5-touch therapeutic retargeting with barrier-specific interventions:

  ┌──────────────────────────────────────────────────────────────────┐
  │                                                                  │
  │  Touch 1 (Ch.2 Complication) ─► Touch 2 (Ch.2 Evidence) ─►     │
  │  Touch 3 (Ch.3 Rising Action) ─► Touch 4 (Ch.4 Resolution) ─► │
  │  Touch 5 (Ch.5 Epilogue/CTA)                                   │
  │                                                                  │
  │  Each touch:                                                    │
  │  ├── Different mechanism (from retargeting sequence spec)       │
  │  ├── Different copy (narrative-progressive)                     │
  │  ├── Different construal (abstract → concrete)                  │
  │  ├── Different tone (warm → authoritative)                      │
  │  └── Same barrier (diagnosed per archetype)                     │
  │                                                                  │
  │  Suppression controls:                                          │
  │  ├── Max 7 touches (from settings, env-configurable)            │
  │  ├── Reactance ceiling 0.85                                     │
  │  ├── Min 12h between touches                                    │
  │  ├── CTR floor 0.03% (pause 72h if below)                      │
  │  └── Bounded memory (20 turns/seq, 5K max sequences)            │
  │                                                                  │
  │  Claude argument engine: sanitized prompts, XML data tags       │
  │                                                                  │
  └──────────────────────────────────────────────────────────────────┘


═══════════════════════════════════════════════════════════════════════════════
 THE COMPLETE FLOW: Impression → Intelligence → Copy → Outcome → Learning
═══════════════════════════════════════════════════════════════════════════════

  StackAdapt bid request
       │
       ▼
  Segment parsed → archetype + category + ASIN
       │
       ▼
  Bilateral Cascade (L1→L2→L3) → mechanism + 20 edge dimensions
       │
       ▼
  Intelligence Prefetch (11 sources) → ad_context
       │
       ▼
  Atom DAG (14 atoms, 5 levels) → psychological assessment
       │
       ▼
  Copy Generation (5 layers → Claude Opus) → headline + body + CTA
       │
       ▼
  Creative Adaptation (page context → parameter rotation, <5ms)
       │
       ▼
  Response to StackAdapt (mechanism, copy, bid multiplier, domain targeting)
       │
       │  ... impression serves, user sees ad ...
       │
       ▼
  Conversion webhook arrives
       │
       ▼
  Outcome Handler (20 learning paths fire simultaneously)
       │
       ├── Thompson posteriors updated
       ├── Resonance model updated
       ├── Converting page priority-crawled
       ├── Causal recipe decomposed (3-5 ingredients)
       ├── Inferential hypothesis generated (theory-backed)
       ├── Info-value ranked (most informative test first)
       ├── Predictions generated (specific pages to target)
       ├── Counterfactual tracked (what would have worked)
       └── Copy effectiveness recorded (which variant converted)
              │
              ▼
         SYSTEM IS NOW SMARTER
         Next impression benefits from ALL of the above
         Prediction accuracy improves with each cycle
```

---

## Key Numbers

| Metric | Value |
|--------|-------|
| Bilateral edges (luxury transport) | 3,103 |
| Bilateral edges (total corpus) | 6,743,384 |
| Dimensions per edge (Claude-annotated) | 20 |
| Theory graph nodes | 44 (14 states + 15 needs + 10 mechanisms + 5 routes) |
| Theory graph edges | 49 (causal links with academic citations) |
| Gradient fields computed | 4 (3 archetypes + 1 universal) |
| Psychological atoms | 14 (in 5-level DAG) |
| Intelligence sources (prefetch) | 11 |
| Learning paths (outcome handler) | 20 |
| Copy generation prompt layers | 5 |
| Prompt size | ~4,500 characters |
| Pre-seeded hypotheses | 334 |
| Whitelisted domains | 29 |
| Campaign touches | 15 (3 archetypes × 5 touches) |
| Latency SLA | 120ms |
| Circuit breakers | 3 (neo4j, redis, prefetch) |
| Cold-start priors | 941M reviews |

---

## What Makes This Different

**Other systems**: Impression → Score → Serve → Measure → Adjust weight → Repeat
They learn WHAT works through trial and error across millions of impressions.

**INFORMATIV**: Impression → Understand WHY → Form causal hypothesis → Predict where else → Deploy → Validate → Compound → Transfer to ALL similar contexts
It learns WHY things work through causal reasoning, then transfers that understanding without waiting for more data. One conversion teaches about thousands of contexts.

The theory graph is the force multiplier. When a single conversion validates a causal chain (State → Need → Mechanism), that validation propagates to EVERY context where the same causal chain applies.

This is not optimization. This is intelligence.
