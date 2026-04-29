# INFORMATIV × Index Exchange — Talking Points

**Audience**: Index Exchange (SSP)
**Speaker**: Chris Nocera
**Frame**: exploratory partnership conversation — not a pitch deck

---

## The 30-second frame

INFORMATIV is a privacy-native, content-based, **psychologically-grounded** matching layer that makes display inventory more valuable to advertisers AND more legible to publishers. The matching primitive is bilateral psychological alignment between the page (what it activates), the buyer (what they're seeking), and the creative (what it offers) — annotated at depth across 47M+ alignment edges, 1.9M cognitive-construct nodes, and 6.7M+ bilateral edges in the LUXY corpus alone.

For an SSP like Index Exchange, the partnership shape is **inventory enrichment** — every page in IX's inventory becomes annotatable with a cognitive profile that advertisers / DSPs that "speak INFORMATIV" can target against. Premium tier of IX inventory; cooperative not adversarial; aligned with where the industry is going post-cookie.

---

## Why an SSP, why Index Exchange, why now

### The post-cookie reality forces content-based targeting

Cookie deprecation, Apple ATT, GDPR signal loss — the substrate behavioral targeting depends on is eroding. Contextual targeting is the obvious fallback, but contextual today = topic classification ("luxury travel page"). That's a category label. Inferential systems beyond category labels are where the market is moving. Index Exchange's positioning here matters.

### INFORMATIV is structurally privacy-native

Our matching primitive is **page-level cognitive profile + creative-side cognitive profile + bilateral alignment between them.** No user IDs required. No cookies required. The profile is extracted from the content itself — author, publication, section, language patterns, metaphor density, attentional posture, regulatory-focus orientation. This isn't "content-based targeting with privacy-friendly framing"; it's content-based targeting **by construction**.

### The cooperative frame is non-negotiable for us

Per ADAM's foundation: "publisher relationships are cooperative by design. Better matching makes their inventory more valuable. Privacy concerns that apply to behavioral scraping do not apply here, because the unit of analysis is the page's content, not the user's history." We are NOT a scraper-of-publisher-data play. We are a **make-publisher-inventory-more-valuable** play.

### Why Index Exchange specifically

Index Exchange's reputation for transparent auctions + technical sophistication + premium inventory positions it for the kind of partnership that requires both sides to actually understand what's being matched. We're not asking IX to take our claims on faith; we're asking IX to integrate at a depth that lets publishers and DSPs both VERIFY the match quality.

---

## INFORMATIV's core strengths (the things to surface in the room)

### 1. Bilateral architecture — both sides annotated at psychological depth

Every other ad-tech system annotates ONE side of the transaction (typically the user, via behavioral correlates). INFORMATIV annotates both sides:

- **Buyer side**: 27-dimension psychological profile derived from review-corpus analysis (937M+ verified-purchase reviews; specifically ~941M integrated into cold-start priors with dual-sided annotation depth varying by cell — to-our-knowledge the only system with this dual-sided annotation)
- **Seller side**: 27-dimension alignment profile derived from brand-copy analysis + product semantics
- **Edge**: per-impression bilateral alignment score across 27 psychological dimensions

For an SSP partnership: **the page is the third side.** Pages can be annotated with the same 27-dimension cognitive profile and edge-joined to buyer profiles AND creative profiles. Same primitive; new corpus.

### 2. Theoretical depth that cannot be replicated by an LLM wrapper

The architecture is grounded in 24 years of multi-disciplinary research from Chris's training: John Bargh (Yale, automaticity / priming / auto-motive model), Steven Pinker (Harvard, dual-mechanism theory), plus pharmacology, medicinal chemistry, bioinformatics, biological systems. The 441+ constructs across 20+ domains are research synthesis, not LLM tagging. The cognitive primitives that matter for advertising — automatic evaluation, perception-behavior link, nonconscious goal pursuit, embodied metaphor priming, regulatory focus, construal level — are operationalized AS the architecture, not bolted on.

### 3. Phase 0.1 substrate is in production

Not slideware. Specifically:
- Bilateral cascade with L3 override (cascade uses bilateral edge evidence as the primary signal when reached, not a blend partner with archetype priors)
- Conformal-coverage CI on lift estimates (valid finite-sample marginal coverage at any N; replaces parametric delta-method)
- Multi-horizon adjudication (catches the failure mode where short-horizon CPA wins hide long-horizon brand damage)
- Pre-registered mechanism rotation event substrate (falsifiable Pilot 2 demo artifact)
- Construct-chain rendering (every recommendation comes with its inferential chain, citation-tagged)
- Per-atom contribution measurement (post-pilot decision tree on which cognitive components drove the lift)
- ~409 tests passing across the Phase 0.1+ surface as of today's commit
- HEAD: `2170016`

We can show running code, not concept slides.

### 4. Explainability via construct chains — the differentiator

Every other DSP / SSP shows scores: "authority: 0.82". Trust the number. INFORMATIV shows the cognition that produced the score:

> "Careful Truster on this page activates need-for-closure (Bargh 1990 §3.2) → which authority satisfies (Cialdini 2007 §2.4) → must be substantive because cognitive engagement is high → frame for long temporal horizon because construal level is abstract."

For an SSP: this is what publishers can SHOW their advertisers. Not "your ad was placed against luxury travel content"; instead "your creative was matched to a page whose attentional posture activates [specific construct], which the buyer's psychological profile predicts as a high-yield placement, with the inferential chain available for audit."

### 5. Page intelligence at depth — beyond topic classification

The page profile carries ~15 layers of signal:
- 27-dimension edge profile (matching the bilateral cascade's space)
- Attentional posture (blend-compatible vs vigilance-activating per Foundation §2 attention-inversion)
- Author × Publication × Section hierarchical priors
- Metaphor density across primary metaphor axes (Lakoff/Johnson/Grady, validated by Chris's own published work on cross-linguistic universals)
- Regulatory-focus orientation (promotion vs prevention)
- Construal level (concrete vs abstract)
- Temporal context + content freshness
- Goal-activation profile (which automotive-goals does this page prime?)
- Social-proof signal density
- Attention-competition (DOM-derived: ad slot count, video autoplay, interstitials, scroll depth to content)
- Plus the 5 standard layers (topic, freshness, sentiment, entity, intent)

For an SSP partnership: every URL in IX's inventory becomes annotatable with this profile. Premium-tier inventory with depth no other system can match.

### 6. Privacy-native, cookie-independent, identity-graph-independent

Stating it plainly because it matters:
- We don't need user IDs
- We don't need cookies
- We don't need third-party device graphs
- We don't depend on UID2 / RampID / etc. (we COMPLEMENT them where they exist; we don't FAIL when they don't)

The matching is content × content × creative. Behavioral signal is OPTIONAL ground truth for the learning loop, not REQUIRED for the inferential targeting.

### 7. Active pilot with real data

LUXY pilot is in pre-launch (Q2/Q3 2026). $30K/week budget × 12 weeks. Friendly partner. Pre-registered analysis plan + third-party statistical reviewer + conformal coverage on lift claims. Real outcomes incoming. We're not pitching "we will prove this someday"; we're pitching "we will have public causal-coverage evidence in 12 weeks."

---

## Concrete partnership shapes (three options to surface)

### Option A — Bid-time enrichment (lightest integration)

INFORMATIV provides an API that, given a page URL + creative + bid context, returns a psychological-fit score + construct-chain explanation. IX adds the score as a key-value pair in the bid request. DSPs that consume the score bid higher on aligned impressions.

**Lift hypothesis**: bilateral-aligned impressions show measurably higher conversion rate at the same impression cost. SSPs benefit via higher-value auctions; publishers benefit via higher CPMs; advertisers benefit via better outcomes per dollar.

**Lightest lift**: no header-bidding rewrite, no publisher onboarding change. INFORMATIV is a callout the SSP can choose to make.

### Option B — Annotated inventory tier (medium integration)

INFORMATIV batch-annotates IX inventory at the URL level on a daily/weekly cadence. Annotated URLs become a distinct **curated tier** advertisers / DSPs can opt into via PMP deals or open auctions tagged with the annotation.

**Differentiator**: Index Exchange's curated tier is "URLs annotated by INFORMATIV at psychological depth." Pages with high signal density command premium CPMs.

**Publisher value**: improved yield on the annotated tier, full visibility into the annotation (publishers see what their content's profile is, can improve it strategically).

### Option C — Header-bidding key-value pair (deepest integration)

INFORMATIV's profile becomes a first-class signal in the header-bidding flow. Every bid request from IX-onboarded publishers includes the INFORMATIV cognitive profile as standardized key-value pairs. DSPs query against these in their bidding logic.

**Heaviest lift**: requires header-bidding standard adjustment, publisher SDK update, DSP-side decoder.

**Highest moat**: once INFORMATIV is in the header-bidding standard, it's structural to the IX value proposition.

### What we'd recommend

Start with **Option A (bid-time enrichment)** as a 90-day pilot integration on a subset of IX inventory. If signal density on the annotated impressions matches our pilot data (and we're confident it will), graduate to **Option B (annotated inventory tier)** in Q3-Q4 2026. **Option C** is a 2027 conversation.

---

## Anticipated questions + responses

### "Are you a DSP competitor?"

No. INFORMATIV is an inferential layer that makes both sides of the transaction richer. We can be deployed as a DSP-side capability (advertisers/DSPs use INFORMATIV-aware bidding), an SSP-side capability (this conversation), or an independent middle layer that both DSPs and SSPs subscribe to. Deployment shape is contextual; the technology is one substrate.

### "What's the data scale, honestly?"

- 6.7M bilateral edges in the LUXY corpus (verified, queryable)
- ~47M alignment edges + 1.9M GranularType nodes (production Neo4j)
- ~941M reviews integrated into cold-start priors across 20+ domains
- LUXY pilot will produce ~200-400 conversions across the 12-week flight (small but causally defensible via conformal coverage)

We're honest about scale. The differentiator isn't volume; it's **depth × bilateral**. No one else has both sides annotated at this granularity.

### "How is this different from existing contextual + AI approaches?"

Most contextual is **topic classification**. ADAM-level is **mechanism activation**. The difference matters because topic-level can't tell you why a creative will or won't work; mechanism-level can — and the construct chain is auditable.

LLM-based contextual is statistical-correlation-flavored. INFORMATIV is mechanism-grounded — the constructs come from peer-reviewed research, the chains link causally, and the system embodies the mechanism rather than approximating it. This is the moat: you can't bolt mechanism onto a correlational system; the substrate is incompatible.

### "How do you make money?"

Three revenue shapes, depending on partnership depth:
1. **Per-decision pricing** for API enrichment (Option A)
2. **Revenue share** on premium-tier auctions (Option B) — likely 5-15% of the lift the annotation drives
3. **Subscription** for publishers who want their inventory annotated and the analytics access

For Index Exchange: a revenue-share model on Option A or Option B is probably the right starting frame — aligned incentives, scaling with the value created.

### "Why now? What's the market timing?"

Three vectors converging:
1. **Cookie deprecation forces content-based targeting**. The substrate behavioral targeting depends on is eroding faster than industry alternatives are maturing. Content-based at MECHANISM depth is the right answer; INFORMATIV is built for this.
2. **AI-generated creative + AI-generated content saturates the market**. Surface-level (text-similarity, embedding-distance) targeting fails when creative variability explodes. Mechanism-level targeting holds because it's grounded in the receiver's cognitive substrate, not the surface variation.
3. **Reactance + adblock fatigue**. Users are increasingly hostile to advertising that doesn't fit their state. ADAM's attention-inversion frame (attention as barrier, not path; blend-compatible mechanisms outperform vigilance-activating mechanisms on the same impression pool) is empirically aligned with where the user-experience trend lines point.

The cooperative-publisher framing matters here too — mechanism-level matching makes publisher inventory MORE valuable to advertisers, which is the SSP's core economic interest.

### "What's the integration risk for IX?"

**Option A risk is low**. API callout, ~50ms latency budget, fallback behavior if INFORMATIV unavailable. Standard partner-API integration pattern.

**Option B risk is medium**. Daily batch annotation of inventory + curated-tier delineation in the IX console. Operational overhead but no real-time dependency.

**Option C risk is high**. Header-bidding standard adjustment requires industry coordination. Not a Q2 2026 commitment.

---

## What we'd want from Index Exchange

If the partnership shape resonates, our asks are concrete:

1. **A 90-day Option A pilot** on a subset of IX inventory (publisher consent + scope to be discussed)
2. **Visibility into bid-clearing prices** on annotated vs unannotated impressions in the pilot (so we can causally measure the lift)
3. **Publisher introduction** — let us talk to 1-2 publishers in IX's network to understand their inventory annotation needs from the supply side
4. **Joint case-study commitment** — if the pilot delivers measurable lift, jointly published case study
5. **Optionality on Options B and C** — the 90-day Option A pilot is the first step; Option B / C remain open as graduation paths

---

## What we DON'T have / honest constraints

The discipline rule: don't overclaim. Things to be transparent about if they come up:

1. **The LUXY pilot hasn't launched yet** — pre-launch, Q2/Q3 2026. We have substrate + simulation results + pre-registered analysis plan. Real-data outcomes come in Q3.
2. **6.7M bilateral edges is LUXY-specific** — premium black-car category. Other categories are at earlier corpus-build stages.
3. **Page intelligence is currently strongest on editorial / corporate-travel content** — IX's full inventory diversity is broader; Q3 2026 expansion needed for full coverage.
4. **No third-party benchmark vs major DSPs at this date** — pilot launches within weeks; benchmarks come from pilot data.
5. **A14 calibration-pending flags exist in the architecture** — explicit pilot-pending coefficients tracked via Prometheus dashboard. We're disciplined about what's calibrated vs what's prior. If IX wants to inspect: documented in `docs/PILOT_PRE_REGISTERED_ANALYSIS_PLAN.md`.

The honest framing wins more than the puffed-up framing. INFORMATIV's track record is in the architecture and the discipline, not in finished case studies. Yet.

---

## Closing — the why-INFORMATIV-for-IX summary

**INFORMATIV's bet**: post-cookie display advertising will be won by mechanism-level matching, not topic classification or behavioral lookalike. The substrate that wins is bilateral psychological alignment annotated on both sides, joined by alignment edges, with explainable inferential chains.

**Index Exchange's strategic question**: which inferential layer becomes the standard for content-based premium-tier inventory? Whoever wins this becomes structural to the post-cookie SSP economy.

**The partnership thesis**: a 90-day Option A pilot at modest integration cost validates the inferential lift on IX inventory. If the lift materializes (which we expect based on the LUXY pilot's pre-registered design), it positions IX as the SSP partner of the inferential-targeting wave — and positions INFORMATIV inside the IX standard.

The cooperative framing is the differentiator. Better matching makes inventory more valuable to advertisers, which makes auctions clear higher, which benefits publishers AND IX AND advertisers AND INFORMATIV. Aligned incentives across all four parties; that's a partnership shape that holds.

---

## Quick reference — single-screen recap

- **What**: bilateral cognitive matching layer for display advertising
- **How**: page profile × buyer profile × creative profile with construct-chain explanations
- **Why now**: cookies dying; content-based at mechanism depth wins
- **What's real**: Phase 0.1 substrate live; LUXY pilot launching Q2/Q3 2026; 47M alignment edges in production Neo4j
- **What's pilot-pending**: explicit A14 flags in architecture; pre-registered analysis plan with conformal CI; third-party stat reviewer engaged
- **The ask**: 90-day Option A pilot on a subset of IX inventory
- **The shape**: revenue share on lift; cooperative publisher framing; aligned incentives
- **The why-IX**: technical sophistication + transparent auctions + premium inventory = right SSP for this depth of integration

---

**Document version**: v1, drafted for the Index Exchange meeting. Supersedes any earlier IX talking points. Update post-meeting with what surfaced.
