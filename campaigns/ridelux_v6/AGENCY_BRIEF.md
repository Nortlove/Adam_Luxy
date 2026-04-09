# INFORMATIV × LUXY Ride — Agency Campaign Brief
## For: [Agency Name]
## Date: April 8, 2026

---

## WHAT THIS IS

INFORMATIV has developed a **psycholinguistic advertising intelligence system** that matches ad creative to audience psychology. We've analyzed luxury transportation consumers and identified three distinct psychological profiles. Each profile responds to different messaging strategies.

This brief provides everything you need to run a 30-day pilot campaign in your StackAdapt account for LUXY Ride, optimized by our intelligence system.

---

## HOW THIS WORKS — The Collaboration Model

### You Control (Agency)
- StackAdapt campaign setup, management, and optimization
- Creative production (images — we provide copy and art direction)
- Bid strategy, pacing, and budget allocation
- Day-to-day campaign optimization within StackAdapt
- Standard reporting

### INFORMATIV Provides
- **Campaign strategy**: Audience archetypes, mechanism sequencing, creative copy
- **Behavioral intelligence**: A lightweight script installed on luxyride.com that captures post-click behavior. This is the core of what we're testing.
- **Weekly intelligence reports**: Data-driven recommendations for creative rotation, budget reallocation, and targeting adjustments based on our behavioral analysis
- **Domain targeting**: Psychologically-profiled publisher lists (provided as upload-ready CSVs)

### LUXY Ride Provides
- Google Tag Manager access (one tag to install — we provide the exact code)

### The Data Flow
```
User sees ad on Forbes → clicks → lands on luxyride.com
   ↓
INFORMATIV telemetry captures:
   - Which sections they spend time on (pricing? safety? reviews?)
   - How deep they scroll, how fast
   - Whether they start the booking flow
   - Whether they return organically (without clicking another ad)
   ↓
INFORMATIV analyzes behavioral patterns across all visitors
   ↓
Weekly report to agency:
   "Careful Truster archetype: Touch 3 (evidence_proof) is converting
   at 2.1x Touch 2. Recommend increasing T3 budget by 30% and
   decreasing T1 budget by 15%. Users who engage with the safety
   section convert at 3x — consider safety-focused creative variant."
```

---

## THE THREE AUDIENCE ARCHETYPES

Our analysis identified three psychological profiles among luxury transportation buyers. Each responds to different persuasion mechanisms:

### 1. Careful Truster (26% of audience)
- **Psychology**: High need for evidence, risk-averse, reads reviews extensively
- **What works**: Social proof, data/statistics, safety credentials, testimonials from similar people
- **What fails**: Urgency, scarcity, aggressive CTAs
- **Peak hours**: 5-8 AM (pre-travel anxiety), 5-10 PM (evening research), 10 PM-5 AM (late night anxiety)
- **Budget allocation**: $58.50/day (26% of total)

### 2. Status Seeker (38% of audience)
- **Psychology**: Status-conscious, luxury-oriented, responds to exclusivity and aspiration
- **What works**: Narrative storytelling, aspirational imagery, social proof from high-status peers
- **What fails**: Discount messaging, budget positioning, too much detail
- **Peak hours**: 6-9 AM weekday (commute planning), 9 AM-5 PM (business hours)
- **Budget allocation**: $84.83/day (38% of total)

### 3. Easy Decider (36% of audience)
- **Psychology**: Low deliberation, action-oriented, responds to convenience and friction removal
- **What works**: Loss framing, implementation prompts, micro-commitments, one-click booking
- **What fails**: Long-form content, comparison charts, too many options
- **Peak hours**: Flat throughout day (they convert anytime), slight boost 5-10 PM
- **Budget allocation**: $81.67/day (36% of total)

**Total daily budget: $225.00**

---

## CAMPAIGN STRUCTURE

### Overview
```
3 Campaign Groups (one per archetype)
  × 5 Campaigns each (sequential touches)
  = 15 Campaigns total
  = 15 Creatives (one per campaign — NO rotation)
```

### Why One Creative Per Campaign
Each creative is specifically designed for its position in the retargeting sequence. Touch 1 introduces the story. Touch 2 provides evidence. Touch 3 deepens the argument. Touch 4 resolves objections. Touch 5 drives action. Rotating creatives breaks this sequence and defeats the purpose.

---

## WHAT YOU NEED TO SET UP IN STACKADAPT

### 1. Install Two Tags on luxyride.com (via GTM)

**You need GTM access to the luxyride.com container.** Install two Custom HTML tags:

**Tag A: StackAdapt Universal Pixel**
```html
<script>
  !function(s,a,e,v,n,t,z){if(s.saq)return;n=s.saq=function(){
  n.callMethod?n.callMethod.apply(n,arguments):n.queue.push(arguments)};
  if(!s._saq)s._saq=n;n.push=n;n.loaded=!0;n.version='1.0';n.queue=[];
  t=a.createElement(e);t.async=!0;t.src=v;z=a.getElementsByTagName(e)[0];
  z.parentNode.insertBefore(t,z)}(window,document,'script',
  'https://tags.srv.stackadapt.com/events.js');
  saq('ts', 'YOUR_UNIVERSAL_PIXEL_ID');
</script>
```
- Trigger: **All Pages**
- Replace `YOUR_UNIVERSAL_PIXEL_ID` with your pixel ID from StackAdapt

**Tag B: INFORMATIV Behavioral Intelligence**
```html
<script src="%%INFORMATIV_SERVER_URL%%/static/telemetry/informativ.js"
        data-endpoint="%%INFORMATIV_SERVER_URL%%/api/v1/signals/session"
        defer></script>
```
- Trigger: **All Pages**
- `%%INFORMATIV_SERVER_URL%%` will be provided by INFORMATIV team before launch
- This script is lightweight (<4KB gzipped), async, and does not affect page load speed

**Publish both tags in GTM.**

### 2. Create 4 Conversion Events in StackAdapt

Go to **Pixels** → **Create Conversion Event** and create these exactly:

| # | Name (use exactly) | Pixel Type | Method | Rule | Attribution | Primary? |
|---|-------------------|-----------|--------|------|-------------|----------|
| 1 | `luxy_site_visit` | Universal Pixel | Page Load | URL contains `luxyride.com` | 30 days | No |
| 2 | `luxy_booking_page` | Universal Pixel | Page Load | URL contains `/programs/book` | 14 days | No |
| 3 | `luxy_booking_start` | Universal Pixel | Page Load | URL contains booking confirmation trigger | 7 days | No |
| 4 | `luxy_booking_complete` | Universal Pixel | Custom Event (or Page Load on confirmation URL) | Booking confirmation page | 7 days | **YES** |

**For Event 4**: Enable **Revenue Tracking** if available.

**Note on naming**: Use the exact names above. These names will appear in the reporting data we pull via StackAdapt GraphQL API, and our system maps them to our internal conversion stages.

**After creating each event**: Note the Conversion Event IDs — you'll need them if adding custom JS triggers (see Appendix A).

### 3. Create 5 Audiences

Go to **Audiences** → **Create Audience**:

| # | Name (use exactly) | Type | Rule | Lookback |
|---|-------------------|------|------|----------|
| 1 | `luxy_all_visitors` | Retargeting | URL contains luxyride.com | 30 days |
| 2 | `luxy_booking_visitors` | Retargeting | URL contains `/programs/book` | 14 days |
| 3 | `luxy_high_intent` | Retargeting | Visit frequency ≥ 3 | 14 days |
| 4 | `luxy_converted_exclude` | Exclusion | Event: luxy_booking_complete | 90 days |
| 5 | `luxy_booking_abandoned` | Retargeting | Event: luxy_booking_start AND NOT luxy_booking_complete | 7 days |

**CRITICAL**: Audience #4 (`luxy_converted_exclude`) must be applied as an **exclusion** to ALL 15 campaigns.

### 4. Upload Domain Lists

We provide two upload-ready CSV files (domain only, one per line):

- **`stackadapt_whitelist_upload.csv`** (41 domains) → Upload as **Site Inclusion List**
- **`stackadapt_blacklist_upload.csv`** (21 domains) → Upload as **Site Exclusion List**

These domains are psychologically profiled — each is selected because the content creates a mental state that aligns with one of the three archetypes. Do not add random domains.

### 5. Create 3 Campaign Groups

| # | Name | Daily Budget |
|---|------|-------------|
| 1 | `LUXY — Careful Truster` | $58.50 |
| 2 | `LUXY — Status Seeker` | $84.83 |
| 3 | `LUXY — Easy Decider` | $81.67 |

- **Optimization Goal**: Conversions (luxy_booking_complete)
- **Flight dates**: 30-day pilot window

### 6. Create 15 Campaigns + Upload 15 Creatives

**Click URL for ALL campaigns** (critical — this feeds our intelligence):
```
https://luxyride.com/?sapid={SA_POSTBACK_ID}&cid={CAMPAIGN_ID}&crid={CREATIVE_ID}&domain={DOMAIN}&device={DEVICE_TYPE}&ts={TIMESTAMP}
```
The `{...}` values are StackAdapt macros — do NOT replace them manually.

---

### Careful Truster Campaigns (5)

| Campaign | Creative Copy | Audience | Daily $ | Opt. Goal |
|----------|------|----------|---------|-----------|
| `CT-T1` | **Headline**: "I swore I'd never use a car service again" **Body**: "Sarah, a Fortune 500 exec, faced the same dilemma after multiple disappointing rides. The fear of unprofessionalism." **CTA**: "Her story" | luxy_all_visitors | $17.52 | Clicks |
| `CT-T2` | **Headline**: "We've All Heard The Horror Stories" **Body**: "Late pickups. Rude drivers. Hidden fees. 847 Fortune 500 CEOs still choose us daily. Here's the data they see." **CTA**: "See proof" | luxy_all_visitors | $14.04 | Clicks |
| `CT-T3` | **Headline**: "47,000 executives trust LUXY with their reputation" **Body**: "Independent audit: 99.7% on-time arrival rate. DOT safety rating: Superior. Average driver tenure: 8.2 years." **CTA**: "See proof" | luxy_booking_visitors | $11.70 | Conversions |
| `CT-T4` | **Headline**: "I Was Wrong About Premium Car Services" **Body**: "CFO Sarah Mitchell: 'Thought they were all unreliable until LUXY's driver waited 2 hours for my delayed flight.'" **CTA**: "See proof" | luxy_booking_abandoned | $9.36 | Conversions |
| `CT-T5` | **Headline**: "847,000+ rides completed. Zero security incidents." **Body**: "We know you've heard stories. Here's ours: background-checked drivers, live GPS tracking, 24/7 support team." **CTA**: "Book now" | luxy_high_intent | $5.88 | Conversions |

**Frequency**: Max 3/day, 12/week
**Dayparting**: +30% bid 5-8 AM, +20% bid 5-10 PM, +40% bid 10 PM-5 AM, -20% bid noon-5 PM weekday

---

### Status Seeker Campaigns (5)

| Campaign | Creative Copy | Audience | Daily $ | Opt. Goal |
|----------|------|----------|---------|-----------|
| `SS-T1` | **Headline**: "You've earned success. Where's the service?" **Body**: "Built your empire through precision and excellence. Yet you're stuck with transportation that doesn't match." **CTA**: "See More" | luxy_all_visitors | $25.45 | Clicks |
| `SS-T2` | **Headline**: "I thought luxury cars were just showing off" **Body**: "CEO Sarah M. felt the same way—until missing three deals stuck in traffic while her Uber was late again." **CTA**: "Her story" | luxy_all_visitors | $20.36 | Clicks |
| `SS-T3` | **Headline**: "You've built this life. You deserve this ride." **Body**: "Fortune 500 CEOs choose LUXY for 47% of business travel. Real-time tracking, vetted drivers, transparent rates." **CTA**: "Book now" | luxy_booking_visitors | $16.97 | Conversions |
| `SS-T4` | **Headline**: "Finally, transportation that gets me" **Body**: "Sarah, a Fortune 500 exec: 'LUXY drivers understand my world. No small talk, perfect timing, total discretion.'" **CTA**: "Book now" | luxy_booking_abandoned | $13.57 | Conversions |
| `SS-T5` | **Headline**: "You've Joined the Top 1% Who Choose Differently" **Body**: "847,000 executives trust LUXY because their reputation depends on flawless execution. You understand that standard." **CTA**: "Book Now" | luxy_high_intent | $8.48 | Conversions |

**Frequency**: Max 2/day, 8/week
**Dayparting**: +30% bid 6-9 AM weekday, +10% bid 9 AM-5 PM weekday, -10% bid 5-8 PM, -30% bid 8-11 PM weekday, -20% to -40% weekend

---

### Easy Decider Campaigns (5)

| Campaign | Creative Copy | Audience | Daily $ | Opt. Goal |
|----------|------|----------|---------|-----------|
| `ED-T1` | **Headline**: "Another delay. Another missed opportunity." **Body**: "While you research options, competitors close deals from luxury cars. Every ride you postpone costs status." **CTA**: "See rates" | luxy_all_visitors | $24.50 | Clicks |
| `ED-T2` | **Headline**: "Your driver is waiting. You're still in line." **Body**: "When your flight lands, you have 90 seconds to decide: rideshare chaos or your reserved LUXY waiting curbside." **CTA**: "Reserve now" | luxy_all_visitors | $19.60 | Clicks |
| `ED-T3` | **Headline**: "Your driver is already in your area" **Body**: "Just check if we serve your route. Takes 10 seconds. No booking required." **CTA**: "Check route" | luxy_booking_visitors | $16.33 | Conversions |
| `ED-T4` | **Headline**: "Your driver is already en route" **Body**: "Open the app. Your usual pickup location is saved. Driver arrives in 4 minutes. Zero friction, maximum comfort." **CTA**: "Open App" | luxy_booking_abandoned | $13.07 | Conversions |
| `ED-T5` | **Headline**: "50,000+ executives choose LUXY for airport runs" **Body**: "Your colleagues already know. Next Tuesday 6am flight? Just open the app, tap your saved airport." **CTA**: "Save mine" | luxy_high_intent | $8.17 | Conversions |

**Frequency**: Max 2/day, 6/week
**Dayparting**: +20% bid 6-9 AM weekday, +10% bid 5-10 PM, flat weekend, -30% bid midnight-6 AM

---

## IMAGE ART DIRECTION

| Archetype | Visual Style | Palette | Mood |
|-----------|-------------|---------|------|
| **Careful Truster** | Clean, professional, reassuring. Driver in uniform. Pristine vehicle exterior. Data overlays showing safety stats. Well-lit, no dramatic shadows. | Navy, white, silver | Competent, safe, reliable |
| **Status Seeker** | Premium, aspirational. City skyline at dusk. Luxury interior leather detail. Executive stepping out. High contrast. | Black, gold, deep burgundy | Exclusive, powerful, deserved |
| **Easy Decider** | Dynamic, action-oriented. Airport curbside pickup. Phone showing app interface. Split-second moment. Fast visual pace. | High contrast, white + brand accent | Easy, fast, done |

**Sizes needed per creative**:
- 1200 × 627 px (primary landscape)
- 600 × 600 px (square)
- 800 × 600 px (alternate)
- Format: JPG or PNG, under 2MB

---

## BIDDING GUIDANCE

| Archetype | Suggested Base CPM | Rationale |
|-----------|-------------------|-----------|
| Status Seeker | $10-12 | Highest lifetime value, premium inventory |
| Easy Decider | $8-10 | High conversion rate, standard inventory |
| Careful Truster | $7-9 | Volume play, boost during research windows |

**Device multipliers**: Desktop 1.0×, Mobile 1.1×, Tablet 0.9×

You have full discretion on bid optimization — these are starting recommendations. Adjust based on delivery and performance.

---

## MEASUREMENT

### Primary KPI
**Cost per Booking (CPB)** = Total Spend / luxy_booking_complete events

### What We're Testing
> Each subsequent touch (T1 → T2 → T3 → T4 → T5) should convert at a
> **progressively higher rate**. If T3 converts lower than T2 for any
> archetype, the messaging sequence needs adjustment — that's what our
> weekly intelligence reports will flag.

### Reporting We Need From You
- **Weekly**: Campaign-level report exported from StackAdapt (impressions, clicks, conversions, spend by campaign)
- **Format**: CSV or StackAdapt report link
- **Delivery**: Email to INFORMATIV team every Monday

### What We Provide Back
- **Weekly intelligence report** analyzing behavioral data from luxyride.com visitors
- Specific recommendations: budget shifts, creative changes, targeting adjustments
- Delivered every Wednesday (gives us time to process Monday's data)

---

## BEFORE LAUNCH CHECKLIST

### Agency Confirms:
- [ ] Both GTM tags installed and published (StackAdapt pixel + INFORMATIV telemetry)
- [ ] StackAdapt pixel firing confirmed (Pixels page → Last Fired timestamp)
- [ ] 4 conversion events created with exact names from this document
- [ ] 5 audiences created with exact names from this document
- [ ] `luxy_converted_exclude` applied as exclusion to ALL 15 campaigns
- [ ] Whitelist CSV uploaded (41 domains)
- [ ] Blacklist CSV uploaded (21 domains)
- [ ] 3 campaign groups created with correct daily budgets
- [ ] 15 campaigns created with correct audiences and copy
- [ ] Click URLs include StackAdapt macros (copy the template exactly)
- [ ] Frequency caps set per archetype
- [ ] Dayparting bid adjustments set per archetype
- [ ] 15 image creatives produced and uploaded (one per campaign)
- [ ] All campaigns in DRAFT for final review

### INFORMATIV Confirms:
- [ ] Server deployed and healthy (URL provided to agency)
- [ ] Neo4j seeded with bilateral edge data
- [ ] Telemetry endpoint accepting data
- [ ] CORS configured for luxyride.com
- [ ] Pre-flight validation passes (41/41)

### Joint Sign-Off:
- [ ] Both teams review all 15 campaigns together
- [ ] Test click from each campaign → verify luxyride.com loads with URL params
- [ ] Confirm reporting cadence (agency sends Monday, INFORMATIV sends Wednesday)
- [ ] Set all 15 campaigns to **ACTIVE**

---

## FILES PROVIDED

| File | What To Do With It |
|------|-------------------|
| `AGENCY_BRIEF.md` | This document — your guide |
| `stackadapt_whitelist_upload.csv` | Upload to StackAdapt as Site Inclusion List |
| `stackadapt_blacklist_upload.csv` | Upload to StackAdapt as Site Exclusion List |
| `luxy_ride_creatives.json` | Machine-readable creative specs (reference) |

---

## APPENDIX A: Conversion Event JavaScript (If Needed)

If luxyride.com's booking flow doesn't naturally trigger page loads on distinct URLs for each stage, you may need custom JavaScript triggers in GTM:

**Booking Start trigger**:
```html
<script>
  if (typeof saq !== 'undefined') {
    saq('conv', 'YOUR_BOOKING_START_EVENT_ID');
  }
</script>
```
- Trigger: When user initiates booking (button click, form start, etc.)

**Booking Complete trigger**:
```html
<script>
  if (typeof saq !== 'undefined') {
    saq('conv', 'YOUR_BOOKING_COMPLETE_EVENT_ID', {
      'revenue': BOOKING_VALUE,
      'order_id': BOOKING_ID,
      'currency': 'USD'
    });
  }
</script>
```
- Trigger: Booking confirmation page

Replace the event IDs with the ones generated when you create the conversion events in StackAdapt.

---

*This campaign is powered by INFORMATIV bilateral psycholinguistic intelligence — matching ad messages to audience psychology using analysis of 1,492 bilateral psychological edges across luxury transportation consumers.*
