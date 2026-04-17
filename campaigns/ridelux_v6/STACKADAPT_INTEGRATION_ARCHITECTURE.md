# StackAdapt Integration Architecture — Based on Actual Platform Capabilities

**Date:** April 17, 2026
**Source:** StackAdapt developer stack research + GraphQL API documentation

---

## Key Finding

StackAdapt does NOT support calling an external API per impression.
The integration model is **push, not pull**: we push intelligence INTO
StackAdapt via GraphQL, not StackAdapt pulling from us at bid time.

This changes our architecture from "real-time per-impression decisioning"
to **"pre-computed psychological campaigns with continuous learning."**

This is still very powerful — we're the intelligence brain, StackAdapt
is the execution engine.

---

## Architecture

```
INFORMATIV Server                          StackAdapt Platform
┌────────────────────┐                     ┌─────────────────────────┐
│                    │   GraphQL API        │                         │
│  Campaign Builder  │ ──────────────────► │  8 Campaigns            │
│  (pre-computed     │   Create campaigns,  │  (one per archetype)    │
│   intelligence)    │   creatives, rules   │                         │
│                    │                     │  Multiple creative       │
│                    │                     │  variants per campaign   │
│                    │                     │  (authority, social      │
│                    │                     │   proof, cognitive ease) │
│                    │                     │                         │
│                    │                     │  StackAdapt DCO picks   │
│                    │                     │  best variant by perf   │
│                    │                     │                         │
│  Learning Engine   │ ◄──────────────────│  Conversion Tracker     │
│  (22 systems)      │   S2S Postback      │  (Universal Pixel)      │
│                    │   on conversion      │                         │
│                    │                     │                         │
│  Weekly Optimizer  │ ──────────────────► │  Updated creatives,     │
│  (learns → adapts) │   GraphQL mutations  │  paused losers,         │
│                    │                     │  boosted winners         │
└────────────────────┘                     └─────────────────────────┘
```

---

## Integration Steps

### Step 1: GraphQL Authentication

Becca needs to obtain a **GraphQL API key** from her StackAdapt account
manager. The old REST API key does NOT work. Authentication is via
`X-AUTHORIZATION` header.

```
Endpoint: https://docs.stackadapt.com/graphql
Header: X-AUTHORIZATION: <graphql-api-key>
```

### Step 2: Create Advertiser (if not exists)

```graphql
mutation {
  createAdvertiser(input: {
    name: "LUXY Ride"
    domain: "luxyride.com"
  }) {
    advertiser { id name }
    userErrors { message }
  }
}
```

### Step 3: Create 8 Campaigns (one per archetype)

Each campaign targets a specific buyer psychology. INFORMATIV's
bilateral evidence determines the creative strategy for each.

| Campaign | Archetype | Primary Mechanism | Framing | Key Message |
|----------|-----------|------------------|---------|-------------|
| LUXY-CT | Careful Truster | Authority | Gain | "The executive standard" |
| LUXY-CE | Corporate Executive | Authority | Loss-prevention | "Never miss a flight" |
| LUXY-SS | Status Seeker | Social Proof + Scarcity | Gain | "The ride that says you've arrived" |
| LUXY-SO | Special Occasion | Liking | Gain | "Make your day unforgettable" |
| LUXY-ED | Easy Decider | Cognitive Ease | Gain | "Book in 30 seconds" |
| LUXY-FT | First Timer | Curiosity | Gain | "See what luxury transport is like" |
| LUXY-RL | Repeat Loyal | Commitment | Gain | "Welcome back" |
| LUXY-AA | Airport Anxiety | Authority | Loss-prevention | "Guaranteed airport transfer" |

### Step 4: Create Multiple Creative Variants Per Campaign

This is where our intelligence becomes operational. For each campaign,
create 2-3 creative variants representing different psychological
mechanisms. StackAdapt's built-in optimization (or DCO if product
feed is configured) selects the best-performing variant.

**Example for LUXY-CT (Careful Truster):**

Variant A — Authority (primary, expected winner):
- Headline: "The executive standard in ground transportation"
- CTA: "See why Fortune 500 travel managers choose LUXY"
- Tone: Professional, authoritative

Variant B — Social Proof (secondary test):
- Headline: "Trusted by 10,000+ executive travelers"
- CTA: "Join the professionals who demand reliability"
- Tone: Social validation

Variant C — Cognitive Ease (exploration):
- Headline: "Premium transport. One tap."
- CTA: "Book now"
- Tone: Minimal, effortless

INFORMATIV predicts Variant A wins for this archetype (authority
mechanism scores 0.688 from bilateral evidence). StackAdapt's
optimization validates this prediction with live data.

### Step 5: Configure Conversion Tracker

This is the learning loop — the most critical integration piece.

1. In StackAdapt: **Tracking → Conversion Events → Create New**
2. Set event name: `luxy_booking_confirmed`
3. Set event type: `Purchase`
4. Set attribution window: 30 days click-through, 7 days view-through

**Server-to-Server Postback Configuration:**

The Universal Pixel fires on the LUXY booking confirmation page.
For S2S attribution, configure a postback URL that includes the
StackAdapt postback ID:

```
https://focused-encouragement-production.up.railway.app/api/v1/stackadapt/webhook/conversion?sapid={SA_POSTBACK_ID}
```

**On the LUXY website (luxyride.com):**

Install the Universal Pixel (JavaScript):
```html
<script>
  !function(s,a,e,v,n,t,z)
  {if(s.saq)return;n=s.saq=function(){n.callMethod?
  n.callMethod.apply(n,arguments):n.queue.push(arguments)};
  if(!s._saq)s._saq=n;n.push=n;n.loaded=!0;n.version='1.0';
  n.queue=[];t=a.createElement(e);t.async=!0;
  t.src=v;z=a.getElementsByTagName(e)[0];
  z.parentNode.insertBefore(t,z)}(window,document,'script',
  'https://tags.srv.stackadapt.com/events.js');
  saq('ts', 'YOUR_PIXEL_ID');
</script>
```

On the booking confirmation page, fire the conversion event:
```html
<script>
  saq('conv', 'luxy_booking_confirmed', {
    'revenue': ORDER_TOTAL,
    'order_id': ORDER_ID
  });
</script>
```

### Step 6: Domain Targeting

Apply domain whitelists per campaign to ensure ads appear on pages
where the target archetype's psychological goals are likely activated.

| Campaign | Target Domains (examples) |
|----------|--------------------------|
| LUXY-CT | Bloomberg, Forbes, HBR, WSJ, Financial Times |
| LUXY-CE | Business Traveler, Skift, Corp Travel World |
| LUXY-SS | Robb Report, Departures, Luxury Travel Mag |
| LUXY-ED | TripAdvisor, Google Travel, Kayak |
| LUXY-FT | Condé Nast Traveler, Travel + Leisure |
| LUXY-AA | Airport guides, FlightAware, airline blogs |

### Step 7: The Learning Loop (What Happens After Launch)

This is what makes INFORMATIV different from a static campaign:

**Week 1-2:**
- Conversions flow back via S2S postback
- Our 22 learning systems update on every conversion
- We identify which mechanism variants are winning per archetype
- We detect which archetypes have barrier issues

**Week 3-4:**
- We use GraphQL to pause underperforming creative variants
- We create new variants informed by learning (e.g., "authority works
  for careful_truster but needs loss framing instead of gain")
- We adjust domain targeting based on which page contexts drove
  the highest conversion rates

**Monthly:**
- We analyze the full outcome data across archetypes
- Cross-archetype transfer learning identifies patterns
  (e.g., "authority + abstract construal works across ALL B2B archetypes")
- We produce updated creative briefs informed by 22 learning systems
- We create a performance report comparing our predictions vs actuals

---

## What Becca Needs to Do

1. **Get the GraphQL API key** from her StackAdapt account manager
2. **Create the LUXY Ride advertiser** (if not already exists)
3. **Create 8 campaigns** following the specs above
4. **Upload 2-3 creative variants per campaign** (we provide the copy)
5. **Install the Universal Pixel** on luxyride.com
6. **Configure the conversion event** for booking confirmations
7. **Set up S2S postback** to our webhook URL
8. **Apply domain targeting** per campaign

We'll work alongside her on all of this. Steps 1-3 take about 2 hours.
Steps 4-8 take about 2-3 hours. Half a day total.

---

## What We Do (Ongoing)

1. Monitor conversion data flowing into our server
2. Run the 22 learning systems (automatic)
3. Produce weekly optimization recommendations
4. Push creative updates via GraphQL as we learn
5. Produce monthly performance + psychology reports for LUXY

---

## Future Enhancement: Data Taxonomy API

StackAdapt's **Data Taxonomy API** is how third-party data partners
(Clickagy, 33Across, etc.) provide segments in the marketplace.
If we register as a data partner:

- Our 8 LUXY segments appear in StackAdapt's Third-Party Catalogue
- Becca (and any future agency partner) can activate them with one click
- This is the "deal ID" model she's familiar with
- Requires StackAdapt partnership agreement — conversation with their
  partnerships team

This is the mid-term goal: INFORMATIV segments in the StackAdapt
marketplace, accessible to any agency on the platform.
