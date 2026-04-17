# INFORMATIV Full-Funnel Psychological Strategy — LUXY Ride

**Status:** Strategic architecture document
**Goal:** Transform the entire LUXY StackAdapt account from standard
programmatic ($1,131 CPA) into a psychologically-designed conversion
engine ($100-200 CPA target)

---

## The Problem (In One Number)

**$1,131 CPA.** $53,151 spent. 47 conversions. No revenue tracking.

The campaigns are structurally sound — 4 audience groups, CTV + Display,
proper retargeting. ZGM did solid media buying work. But the creative
has zero psychological targeting, zero mechanism matching, and zero
understanding of WHY luxury transportation buyers convert.

**A 20% improvement is not a win.** It gets CPA to $900. We need to
get to $100-200 to prove our technology works. That requires rethinking
the ENTIRE funnel, not just the creative copy.

---

## The Insight: It's Not About Better Ads. It's About the Right
Psychological Journey.

From 1,492 bilateral purchase events, we know exactly what separates
a buyer who becomes an evangelist from one who warns others away:

| Dimension | Evangelize | Warn | Delta |
|-----------|-----------|------|-------|
| Trust (brand_trust_fit) | 0.463 | 0.210 | +0.253 |
| Emotional resonance | 0.497 | 0.209 | +0.288 |
| Reactance (resistance) | 0.037 | 0.092 | -0.055 |
| Processing depth | 0.777 | 0.840 | -0.063 |

The winners have HIGH trust and HIGH emotional connection with LOW
reactance. The losers have LOW trust, LOW emotion, and HIGHER
reactance — they felt pushed.

**Every ad, on every channel, in every touchpoint needs to BUILD trust
and emotional connection while NEVER triggering reactance.**

---

## The Architecture: Three Layers Working Together

### Layer 1: CTV → Goal Activation (The Primer)

CTV is not a conversion channel. It's a PRIMING channel. 15-30 seconds
of captive attention plants psychological goal seeds that make display
ads effective hours or days later.

**Current state:** 5 CTV campaigns showing generic "Journeys" video.
Burning budget on awareness without strategic priming.

**INFORMATIV approach:**
Each CTV campaign should activate a SPECIFIC nonconscious goal:

| CTV Campaign | Goal to Activate | Creative Direction |
|---|---|---|
| Corporate Executives | Competence verification | "The standard bearers of ground transport" — frame LUXY as what competent professionals choose |
| Professionals-Kinective | Status signaling | "Your arrival is your first impression" — frame transport as identity expression |
| Professionals | Planning completion | "One decision. Every trip. Handled." — frame booking as completing a task |
| Leisure Travel | Indulgence permission | "You earned this ride" — give psychological permission to spend on luxury |
| Leisure Travel-Kinective | Novelty exploration | "What luxury transport actually feels like" — curiosity about the experience |

The CTV ad doesn't try to convert. It PLANTS A GOAL that the display
ad will fulfill 1-7 days later. This is Bargh's auto-motive model
operationalized: the environment (CTV) activates the goal, the
subsequent ad (display) offers fulfillment, and the click is the
automatic completion of the goal pursuit.

**Measurable impact:** If CTV priming works, we should see display
CTR and conversion rate increase for buyers who received CTV exposure
first. StackAdapt's attribution window (up to 180 days) can measure
this. This becomes a Level 3 theory proposition in our inferential
learning agent.

### Layer 2: Display → Mechanism Deployment (The Persuader)

Display is where mechanism matching creates the conversion leverage.
Different buyer psychologies respond to different persuasion approaches.

**Current state:** 4 Display campaigns with carousel/animated creative.
Same message for everyone.

**INFORMATIV approach:**
Each display campaign gets 3 creative variants with different mechanisms.
StackAdapt's optimization tests them. Our learning systems explain WHY
the winner won.

**Corporate Executives campaign:**
- Variant A — AUTHORITY: "The executive standard. On-time guarantee."
- Variant B — COMMITMENT: "Your company deserves better than rideshare."
- Variant C — COGNITIVE EASE: "One tap. Done."
- Domain target: bloomberg.com, forbes.com, wsj.com, hbr.org
- Prediction: Authority wins (0.688 mechanism score from bilateral evidence)

**Professionals campaign:**
- Variant A — AUTHORITY: "GSA-compliant. Receipt-ready. Professional."
- Variant B — SOCIAL PROOF: "Join 10,000+ professionals who switched."
- Variant C — COMMITMENT: "Dedicated account management. Volume pricing."
- Domain target: businesstravelnews.com, skift.com, phocuswire.com

**Leisure Travel campaign:**
- Variant A — SOCIAL PROOF: "The ride that says you've arrived."
- Variant B — LIKING: "Make your trip unforgettable from the first ride."
- Variant C — CURIOSITY: "What luxury ground transport actually feels like."
- Domain target: cntraveler.com, travelandleisure.com, robbreport.com

**Key principle:** The images stay the same (already produced). Only
headlines, body, and CTAs change. The mechanism is in the WORDS, not
the pictures. This is based on primary metaphor research — specific
word patterns activate specific neural substrates:
- Authority: vertical metaphors (rise, elevate, standard, above)
- Trust: warmth metaphors (genuine, close, warm, reliable)
- Ease: flow metaphors (seamless, smooth, effortless, glide)
- Status: weight metaphors (substantial, significant, distinguished)

### Layer 3: Retargeting → Barrier Resolution (The Closer)

This is where the current campaigns fail most dramatically. The
"General Website RT" campaign shows the same testimonial ad repeatedly.
After 2-3 exposures, the buyer has seen it, processed it, and either
been convinced or not. Showing it again triggers reactance.

**INFORMATIV approach:** Therapeutic retargeting sequence.

After someone visits luxyride.com and doesn't convert, we know their
barrier from their behavior on the site:

| Site Behavior | Inferred Barrier | Resolution Mechanism |
|---|---|---|
| Viewed pricing page, left | Price friction | COGNITIVE EASE: "No surge. No hidden fees. Just premium." |
| Viewed fleet page, left | Quality uncertainty | SOCIAL PROOF: "4.9★ rated by 10,000+ travelers" |
| Viewed about page, left | Trust deficit | AUTHORITY: "Fortune 500 travel managers' choice" |
| Viewed booking, abandoned | Friction/complexity | COGNITIVE EASE: "Book in 30 seconds" |
| Bounced from homepage | Low interest/bad timing | CURIOSITY: "What luxury transport is actually like" |

**The sequence (not repetition):**
- Touch 1 (day 1-2): Address the SPECIFIC barrier detected
- Touch 2 (day 3-5): If no conversion, deploy DIFFERENT mechanism
- Touch 3 (day 6-10): If still no conversion, deploy easiest ask
  (cognitive ease + low commitment CTA like "Learn more")
- After 3 touches: SUPPRESS for 14 days (prevent reactance damage)

**This requires informativ.js on luxyride.com** to detect which pages
the visitor engaged with. The JS captures section dwell time and
page navigation, which maps to barrier inference.

---

## What We Need to Build

### Already Built (Ready Now)
- [x] 30-atom DAG with mechanism scoring
- [x] Creative copy per archetype × mechanism (in stackadapt_graphql.py)
- [x] Domain targeting per archetype
- [x] informativ.js telemetry
- [x] Conversion webhook + 22 learning systems
- [x] Knowledge propagation network
- [x] Inferential learning agent
- [x] Pre-campaign simulation
- [x] Weekly intelligence brief
- [x] Campaign monitoring from StackAdapt API

### Need to Build
- [ ] **CTV creative direction briefs** (video script guidance per goal)
- [ ] **Click URL protocol** — append segment + mechanism to landing URL
      so informativ.js captures which ad brought the visitor
- [ ] **Landing page barrier detector** — analyze informativ.js data to
      classify visitor barrier from page behavior
- [ ] **Retargeting audience builder** — segment visitors by barrier
      type for targeted retargeting

### Need from Becca
- [ ] Revenue pixel fix (add revenue to conversion event)
- [ ] Write permissions on GraphQL API key
- [ ] Install informativ.js on luxyride.com
- [ ] Apply creative variants per campaign group
- [ ] Apply domain targeting per campaign group
- [ ] Configure retargeting sequence (3 touches, frequency cap,
      suppression after 3)

---

## The Measurement Framework

### Week 1: Baseline
- Record current CPA per campaign group before changes
- Set up ROAS tracking (revenue pixel fix)
- Install informativ.js

### Week 2-3: INFORMATIV creative deployed
- Compare CPA: INFORMATIV variants vs original creative
- Compare CTR by mechanism variant
- First learning system outputs

### Week 4-6: Retargeting sequence active
- Therapeutic retargeting conversion rate vs standard retargeting
- Barrier resolution rate by mechanism
- First Level 3 theory propositions from inferential agent

### Month 2-3: Full system learning
- Cross-channel attribution: CTV priming → display conversion
- Per-user personalization from repeated measures
- Goal activation validation: do primed pages actually convert better?
- Budget reallocation from learning system recommendations

### Month 4-6: Compounding advantage
- System discovers interaction effects invisible to theory
- Temporal dynamics: which sequences work, when to switch
- Meta-learning: competitive landscape changes detected
- Fully autonomous campaign evolution

---

## The Win Scenario

| Metric | Current | Target (Month 1) | Target (Month 3) | Target (Month 6) |
|--------|---------|-------------------|-------------------|-------------------|
| CPA | $1,131 | $400-500 | $150-250 | $100-150 |
| CTR (Display) | 0.025% | 0.06-0.10% | 0.10-0.15% | 0.12-0.18% |
| ROAS | 0 (unmeasured) | 1.5-2.0x | 3.0-4.0x | 4.0-6.0x |
| Conversion rate | 7.7% | 10-12% | 12-15% | 15-20% |
| Learning propositions | 0 | 10-15 (L1-L2) | 30-40 (L1-L4) | 50+ (L1-L6) |

If we hit these targets, the story writes itself: "INFORMATIV reduced
LUXY's CPA by 85% and generated a 4-6x ROAS by understanding WHY
luxury transportation buyers convert, not just THAT they click."

That's a story investors fund. That's a story brand partners buy.
That's a story Becca tells to her next 10 clients.
