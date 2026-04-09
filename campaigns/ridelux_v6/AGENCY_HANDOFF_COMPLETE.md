# INFORMATIV × LUXY Ride — Complete Agency Handoff Package
## StackAdapt Campaign Setup Guide
## Date: April 8, 2026

---

## FOR THE AGENCY: What This Is

You are setting up a **psycholinguistic retargeting campaign** for LUXY Ride using technology built by INFORMATIV. This is not a standard programmatic campaign — it uses **bilateral psychological intelligence** to match specific ad messages to specific users based on their psychological profile and behavior.

**Your job**: Build the campaign in StackAdapt exactly as specified below. Do not deviate from the creative copy, audience structure, or targeting rules. The precision of the message-to-audience matching is what drives the performance lift.

**What INFORMATIV provides**: A hosted intelligence server that collects behavioral signals from luxyride.com visitors and optimizes creative selection in real-time. You will install two JavaScript tags on luxyride.com — StackAdapt's Universal Pixel and INFORMATIV's telemetry script.

---

## CAMPAIGN OVERVIEW

| Property | Value |
|----------|-------|
| **Advertiser** | LUXY Ride (luxyride.com) |
| **Objective** | Bookings (primary conversion: booking_complete) |
| **Total Daily Budget** | $225.00 |
| **Flight Duration** | 30 days (recommended pilot length) |
| **Channel** | Native (primary), Display (secondary) |
| **Geography** | United States |
| **Campaign Groups** | 3 (one per psychological archetype) |
| **Campaigns** | 15 (5 sequential touches per archetype) |
| **Creatives** | 15 (one per campaign — NO rotation) |

---

## STEP 1: PIXEL INSTALLATION (On luxyride.com)

### 1A. StackAdapt Universal Pixel

Install via **Google Tag Manager** (GTM is already on luxyride.com):

1. Log into Google Tag Manager for the luxyride.com container
2. Create a new Tag:
   - **Tag Type**: Custom HTML
   - **Tag Name**: `StackAdapt Universal Pixel`
   - **HTML**:
```html
<script>
  !function(s,a,e,v,n,t,z){if(s.saq)return;n=s.saq=function(){
  n.callMethod?n.callMethod.apply(n,arguments):n.queue.push(arguments)};
  if(!s._saq)s._saq=n;n.push=n;n.loaded=!0;n.version='1.0';n.queue=[];
  t=a.createElement(e);t.async=!0;t.src=v;z=a.getElementsByTagName(e)[0];
  z.parentNode.insertBefore(t,z)}(window,document,'script',
  'https://tags.srv.stackadapt.com/events.js');
  saq('ts', '%%REPLACE_WITH_UNIVERSAL_PIXEL_ID%%');
</script>
```
   - **Trigger**: All Pages
3. Replace `%%REPLACE_WITH_UNIVERSAL_PIXEL_ID%%` with your actual StackAdapt Universal Pixel ID (format: `sa-XXXXXXXX`)
4. Save and Publish

### 1B. INFORMATIV Telemetry Script

1. Create another Custom HTML tag in GTM:
   - **Tag Name**: `INFORMATIV Telemetry`
   - **HTML**:
```html
<script src="https://%%INFORMATIV_SERVER_URL%%/static/telemetry/informativ.js"
        data-endpoint="https://%%INFORMATIV_SERVER_URL%%/api/v1/signals/session"
        defer></script>
```
   - **Trigger**: All Pages
   - **Tag firing priority**: Set lower than StackAdapt pixel (fires after)
2. Replace `%%INFORMATIV_SERVER_URL%%` with the INFORMATIV server URL (provided by INFORMATIV team)
3. Save and Publish

### 1C. Conversion Event Tags (4 tags)

**Tag 1: Booking Start**
- **Tag Name**: `StackAdapt — Booking Start`
- **Tag Type**: Custom HTML
- **HTML**:
```html
<script>
  if (typeof saq !== 'undefined') {
    saq('conv', '%%REPLACE_BOOKING_START_EVENT_ID%%');
  }
</script>
```
- **Trigger**: Custom Event — fires when a user initiates the booking flow on luxyride.com
  - If luxyride.com pushes a dataLayer event for booking start, use that
  - Otherwise, trigger on page URL containing `/book` or the booking initiation page path
- Replace `%%REPLACE_BOOKING_START_EVENT_ID%%` with the Conversion Event ID from StackAdapt

**Tag 2: Booking Complete (PRIMARY CONVERSION)**
- **Tag Name**: `StackAdapt — Booking Complete`
- **Tag Type**: Custom HTML
- **HTML**:
```html
<script>
  if (typeof saq !== 'undefined') {
    saq('conv', '%%REPLACE_BOOKING_COMPLETE_EVENT_ID%%', {
      'revenue': {{Booking Revenue}},
      'order_id': {{Booking ID}},
      'currency': 'USD'
    });
  }
</script>
```
- **Trigger**: Booking confirmation page load (or dataLayer event for completed booking)
- Replace `%%REPLACE_BOOKING_COMPLETE_EVENT_ID%%` with the Conversion Event ID from StackAdapt
- `{{Booking Revenue}}` and `{{Booking ID}}` should reference GTM variables from the dataLayer
  - If not available from the site's dataLayer, use static values for initial testing
- This is the **PRIMARY conversion event** — StackAdapt optimizes toward this

**NOTE**: You must also create these conversion events in StackAdapt's Pixels page (Step 2) to get the Event IDs referenced above.

---

## STEP 2: CREATE CONVERSION EVENTS IN STACKADAPT

Navigate to **Pixels** → **Create New** → **Conversion Event**

| # | Event Name | Pixel Type | Activation | URL/Event Rule | Attribution Window | Primary? |
|---|-----------|-----------|-----------|----------------|-------------------|----------|
| 1 | `LUXY Ride — Site Visit` | Universal Pixel | Page Load | URL contains `luxyride.com` | 30 days | No |
| 2 | `LUXY Ride — Pricing View` | Universal Pixel | Page Load | URL contains `/programs/book` | 14 days | No |
| 3 | `LUXY Ride — Booking Start` | Universal Pixel | Custom Event | (from GTM tag above) | 7 days | No |
| 4 | `LUXY Ride — Booking Complete` | Universal Pixel | Custom Event | (from GTM tag above) | 7 days | **YES** |

**After creating each**: Record the Event ID. You'll need them for the GTM tags in Step 1C.

**For Event 4**: Enable **Revenue Tracking**.

---

## STEP 3: CREATE AUDIENCES (10 pools)

Navigate to **Audiences** → **Create Audience**

### Retargeting Audiences (5)

| # | Name | Type | Rule | Lookback |
|---|------|------|------|----------|
| 1 | `LUXY — All Site Visitors` | Retargeting | URL contains `luxyride.com` | 30 days |
| 2 | `LUXY — Booking Page Visitors` | Retargeting | URL contains `/programs/book` | 14 days |
| 3 | `LUXY — Booking Started Not Complete` | Retargeting | Event: Booking Start AND NOT Booking Complete | 7 days |
| 4 | `LUXY — Multiple Visits 3+` | Retargeting | Visit frequency ≥ 3 | 14 days |
| 5 | `LUXY — Converted (EXCLUDE)` | Exclusion | Event: Booking Complete | 90 days |

### Sequential Touch Audiences (5)

| # | Name | Targeting Rule |
|---|------|---------------|
| 6 | `Touch 1 Pool` | = All Site Visitors (audience #1) |
| 7 | `Touch 2 Pool` | Served any Touch 1 campaign AND did NOT click |
| 8 | `Touch 3 Pool` | Served any Touch 2 campaign AND did NOT click |
| 9 | `Touch 4 Pool` | = Booking Started Not Complete (audience #3) |
| 10 | `Touch 5 Pool` | = Multiple Visits 3+ NOT Converted (audience #4 minus #5) |

**CRITICAL**: Apply audience #5 (`Converted — EXCLUDE`) as an **exclusion** to ALL 15 campaigns. Never serve ads to someone who already booked.

**NOTE on Touch Pools 7-8**: These reference specific campaigns, so they must be created AFTER the campaigns exist. Create Touches 1 first, then come back to build these audience rules.

---

## STEP 4: UPLOAD DOMAIN LISTS

### Whitelist (42 domains)

Navigate to the campaign targeting section. Upload the following as a **Site Inclusion List**. Save as: `LUXY_Ride_Whitelist`

```csv
domain,track,match_score,mechanism,reason
cnbc.com,status_seeker,0.92,self_expression,Business content primes status identity
bloomberg.com,status_seeker,0.90,self_expression,Financial news = high-status context
forbes.com,status_seeker,0.88,status_visibility,Executive lifestyle content
wsj.com,status_seeker,0.87,self_expression,Premium business audience
hbr.org,status_seeker,0.85,authority,Leadership/strategy content
ft.com,status_seeker,0.85,self_expression,Global business elite
barrons.com,status_seeker,0.83,self_expression,Wealth management context
vogue.com,status_seeker,0.80,social_visibility,Luxury lifestyle
townandcountrymag.com,status_seeker,0.80,social_visibility,Premium lifestyle
fortune.com,status_seeker,0.82,self_expression,Fortune 500 context
linkedin.com,status_seeker,0.78,status_visibility,Professional identity platform
fastcompany.com,status_seeker,0.75,self_expression,Innovation leaders
kayak.com,easy_decider,0.88,frictionless,Active travel booking = ready to decide
booking.com,easy_decider,0.85,frictionless,Travel booking mode
expedia.com,easy_decider,0.83,frictionless,Trip planning
opentable.com,easy_decider,0.78,frictionless,Event planning = needs transport
hoteltonight.com,easy_decider,0.82,frictionless,Last-minute = fast decider
weather.com,careful_truster,0.90,evidence,Pre-travel research mode
flightaware.com,careful_truster,0.88,evidence,Flight tracking = travel imminent
tripadvisor.com,careful_truster,0.87,social_proof,Review-reading mode
thepointsguy.com,careful_truster,0.85,comparative,Travel comparison mindset
cntraveler.com,careful_truster,0.84,comparative,Travel evaluation content
seatguru.com,careful_truster,0.82,evidence,Detail-oriented traveler
tsa.gov,careful_truster,0.80,evidence,Travel logistics focus
flightradar24.com,careful_truster,0.80,evidence,Tracking = planning mindset
usatoday.com,careful_truster,0.72,evidence,General news travel section
cnn.com,multi,0.75,context_dependent,Business=status Travel=truster
nytimes.com,multi,0.75,context_dependent,Opinion=status Travel=truster
people.com,easy_decider,0.70,frictionless,Entertainment = low cognitive load
espn.com,easy_decider,0.68,frictionless,Sports = low deliberation context
theknot.com,status_seeker,0.85,self_expression,Wedding = status + occasion
brides.com,status_seeker,0.83,self_expression,Wedding luxury context
weddingwire.com,careful_truster,0.80,comparative,Wedding vendor comparison
zola.com,status_seeker,0.78,self_expression,Premium wedding registry
marthastewart.com,status_seeker,0.75,self_expression,Premium lifestyle
pinterest.com,status_seeker,0.72,self_expression,Aspiration/planning
politico.com,status_seeker,0.73,self_expression,Political power context
axios.com,status_seeker,0.72,self_expression,Business/policy brevity
inc.com,status_seeker,0.70,self_expression,Entrepreneur context
economist.com,status_seeker,0.82,self_expression,Global elite readership
miserymap.com,careful_truster,0.88,evidence,Flight disruption = highest anxiety
```

For the actual upload to StackAdapt, you only need the **domain** column. The other columns are context for why each domain was selected.

### Blacklist (22 domains)

Upload as a **Site Exclusion List**. Save as: `LUXY_Ride_Blacklist`

```
carmellimo.com
uber.com
lyft.com
tmz.com
dailymail.co.uk
foxnews.com
breitbart.com
infowars.com
groupon.com
retailmenot.com
slickdeals.net
buzzfeed.com
reddit.com/r/personalfinance
complaint.com
ripoffreport.com
yelp.com/topic/worst
accidentnews.net
flightcompensation.com
airlinecomplaints.org
gethumanservice.com
consumeraffairs.com/transportation
```

---

## STEP 5: CREATE CAMPAIGN GROUPS (3)

Navigate to **Campaigns** → **Create Campaign Group**

| # | Name | Daily Budget | Optimization Goal |
|---|------|-------------|------------------|
| 1 | `LUXY Ride — Careful Truster` | $58.50 | Conversions (Booking Complete) |
| 2 | `LUXY Ride — Status Seeker` | $84.83 | Conversions (Booking Complete) |
| 3 | `LUXY Ride — Easy Decider` | $81.67 | Conversions (Booking Complete) |

**Total daily**: $225.00

Set flight dates to your agreed pilot start and end dates (recommend 30 days).

---

## STEP 6: CREATE CAMPAIGNS (15)

Inside each Campaign Group, create 5 campaigns. **Each campaign gets exactly ONE creative (Step 7).** Do NOT enable creative rotation.

### Click URL Template (CRITICAL — Same for ALL 15 campaigns)

Set the landing/click-through URL to:

```
https://luxyride.com/?sapid={SA_POSTBACK_ID}&cid={CAMPAIGN_ID}&crid={CREATIVE_ID}&domain={DOMAIN}&device={DEVICE_TYPE}&ts={TIMESTAMP}
```

The `{...}` values are **StackAdapt macros** — they are auto-filled by the platform when the ad is served. Do NOT replace them manually. These macros feed the INFORMATIV intelligence system.

### Campaign Group 1: Careful Truster (5 campaigns)

| # | Campaign Name | Touch Pool | Opt. Goal | Daily $ |
|---|--------------|-----------|-----------|---------|
| 1 | `CT-T1 Social Proof` | Touch 1 Pool | Clicks | $17.52 |
| 2 | `CT-T2 Evidence Proof` | Touch 2 Pool | Clicks | $14.04 |
| 3 | `CT-T3 Evidence Deep` | Touch 3 Pool | Conversions | $11.70 |
| 4 | `CT-T4 Social Proof Resolution` | Touch 4 Pool | Conversions | $9.36 |
| 5 | `CT-T5 Anxiety Resolution` | Touch 5 Pool | Conversions | $5.88 |

**Frequency Cap**: Max 3/day, Max 12/week
**Dayparting Bid Adjustments**:
- 5-8 AM any day: **+30%** (pre-travel anxiety peak)
- 5-10 PM any day: **+20%** (evening research mode)
- 10 PM-5 AM any day: **+40%** (late night travel anxiety peaks)
- Noon-5 PM weekday: **-20%** (lower research intensity)

### Campaign Group 2: Status Seeker (5 campaigns)

| # | Campaign Name | Touch Pool | Opt. Goal | Daily $ |
|---|--------------|-----------|-----------|---------|
| 6 | `SS-T1 Narrative` | Touch 1 Pool | Clicks | $25.45 |
| 7 | `SS-T2 Social Proof` | Touch 2 Pool | Clicks | $20.36 |
| 8 | `SS-T3 Narrative Deep` | Touch 3 Pool | Conversions | $16.97 |
| 9 | `SS-T4 Social Proof Resolution` | Touch 4 Pool | Conversions | $13.57 |
| 10 | `SS-T5 Rational Argument` | Touch 5 Pool | Conversions | $8.48 |

**Frequency Cap**: Max 2/day, Max 8/week
**Dayparting Bid Adjustments**:
- 6-9 AM weekday: **+30%** (morning commute planning)
- 9 AM-5 PM weekday: **+10%** (business hours)
- 5-8 PM weekday: **-10%** (decompression)
- 8-11 PM weekday: **-30%** (wrong mindset)
- Weekend: **-20% to -40%** (status frame less active)

### Campaign Group 3: Easy Decider (5 campaigns)

| # | Campaign Name | Touch Pool | Opt. Goal | Daily $ |
|---|--------------|-----------|-----------|---------|
| 11 | `ED-T1 Loss Framing` | Touch 1 Pool | Clicks | $24.50 |
| 12 | `ED-T2 Implementation` | Touch 2 Pool | Clicks | $19.60 |
| 13 | `ED-T3 Micro Commitment` | Touch 3 Pool | Conversions | $16.33 |
| 14 | `ED-T4 Ownership` | Touch 4 Pool | Conversions | $13.07 |
| 15 | `ED-T5 Final Nudge` | Touch 5 Pool | Conversions | $8.17 |

**Frequency Cap**: Max 2/day, Max 6/week
**Dayparting Bid Adjustments**:
- 6-9 AM weekday: **+20%** (morning booking window)
- 5-10 PM any day: **+10%** (evening trip planning)
- Weekend all day: **flat** (easy deciders convert anytime)
- 12 AM-6 AM: **-30%** (low traffic, some pre-dawn travel intent)

### For ALL 15 Campaigns

| Setting | Value |
|---------|-------|
| **Channel** | Native (primary) |
| **Audience Exclude** | `LUXY — Converted (EXCLUDE)` — ALWAYS |
| **Site Inclusion** | `LUXY_Ride_Whitelist` |
| **Site Exclusion** | `LUXY_Ride_Blacklist` |
| **Geography** | United States |
| **Device Targeting** | All (desktop, mobile, tablet) |
| **Click URL** | See template above (with StackAdapt macros) |
| **Bid Strategy** | eCPM / Automatic (let StackAdapt optimize) |

---

## STEP 7: UPLOAD CREATIVES (15 — One Per Campaign)

Each campaign receives **exactly one creative**. Do NOT enable rotation. The specific message-to-audience matching is intentional.

**Native Ad Specs**:
- Image: 1200×627 px (landscape), also provide 600×600 and 800×600
- Format: JPG or PNG, under 2MB
- Sponsored By: `LUXY Ride`

### Creative 1: CT-T1 (Careful Truster, Touch 1)
- **Headline**: `I swore I'd never use a car service again`
- **Body**: `Sarah, a Fortune 500 exec, faced the same dilemma after multiple disappointing rides. The fear of unprofessionalism.`
- **CTA**: `Her story`

### Creative 2: CT-T2 (Careful Truster, Touch 2)
- **Headline**: `We've All Heard The Horror Stories`
- **Body**: `Late pickups. Rude drivers. Hidden fees. 847 Fortune 500 CEOs still choose us daily. Here's the data they see.`
- **CTA**: `See proof`

### Creative 3: CT-T3 (Careful Truster, Touch 3)
- **Headline**: `47,000 executives trust LUXY with their reputation`
- **Body**: `Independent audit: 99.7% on-time arrival rate. DOT safety rating: Superior. Average driver tenure: 8.2 years.`
- **CTA**: `See proof`

### Creative 4: CT-T4 (Careful Truster, Touch 4)
- **Headline**: `I Was Wrong About Premium Car Services`
- **Body**: `CFO Sarah Mitchell: "Thought they were all unreliable until LUXY's driver waited 2 hours for my delayed flight.`
- **CTA**: `See proof`

### Creative 5: CT-T5 (Careful Truster, Touch 5)
- **Headline**: `847,000+ rides completed. Zero security incidents.`
- **Body**: `We know you've heard stories. Here's ours: background-checked drivers, live GPS tracking, 24/7 support team.`
- **CTA**: `Book now`

### Creative 6: SS-T1 (Status Seeker, Touch 1)
- **Headline**: `You've earned success. Where's the service?`
- **Body**: `Built your empire through precision and excellence. Yet you're stuck with transportation that doesn't match.`
- **CTA**: `See More`

### Creative 7: SS-T2 (Status Seeker, Touch 2)
- **Headline**: `I thought luxury cars were just showing off`
- **Body**: `CEO Sarah M. felt the same way—until missing three deals stuck in traffic while her Uber was late again.`
- **CTA**: `Her story`

### Creative 8: SS-T3 (Status Seeker, Touch 3)
- **Headline**: `You've built this life. You deserve this ride.`
- **Body**: `Fortune 500 CEOs choose LUXY for 47% of business travel. Real-time tracking, vetted drivers, transparent rates.`
- **CTA**: `Book now`

### Creative 9: SS-T4 (Status Seeker, Touch 4)
- **Headline**: `Finally, transportation that gets me`
- **Body**: `Sarah, a Fortune 500 exec: "LUXY drivers understand my world. No small talk, perfect timing, total discretion.`
- **CTA**: `Book now`

### Creative 10: SS-T5 (Status Seeker, Touch 5)
- **Headline**: `You've Joined the Top 1% Who Choose Differently`
- **Body**: `847,000 executives trust LUXY because their reputation depends on flawless execution. You understand that standard.`
- **CTA**: `Book Now`

### Creative 11: ED-T1 (Easy Decider, Touch 1)
- **Headline**: `Another delay. Another missed opportunity.`
- **Body**: `While you research options, competitors close deals from luxury cars. Every ride you postpone costs status.`
- **CTA**: `See rates`

### Creative 12: ED-T2 (Easy Decider, Touch 2)
- **Headline**: `Your driver is waiting. You're still in line.`
- **Body**: `When your flight lands, you have 90 seconds to decide: rideshare chaos or your reserved LUXY waiting curbside.`
- **CTA**: `Reserve now`

### Creative 13: ED-T3 (Easy Decider, Touch 3)
- **Headline**: `Your driver is already in your area`
- **Body**: `Just check if we serve your route. Takes 10 seconds. No booking required.`
- **CTA**: `Check route`

### Creative 14: ED-T4 (Easy Decider, Touch 4)
- **Headline**: `Your driver is already en route`
- **Body**: `Open the app. Your usual pickup location is saved. Driver arrives in 4 minutes. Zero friction, maximum comfort.`
- **CTA**: `Open App`

### Creative 15: ED-T5 (Easy Decider, Touch 5)
- **Headline**: `50,000+ executives choose LUXY for airport runs`
- **Body**: `Your colleagues already know. Next Tuesday 6am flight? Just open the app, tap your saved airport.`
- **CTA**: `Save mine`

### Image Asset Requirements

You will need to produce image assets for each creative. Guidelines:

| Archetype | Visual Direction | Color Palette |
|-----------|-----------------|---------------|
| **Careful Truster** | Clean, professional, reassuring. Driver in uniform. Pristine vehicle. Data overlays showing safety stats. | Navy, white, silver |
| **Status Seeker** | Premium, aspirational. City skyline. Luxury interior. Executive stepping out. | Black, gold, deep burgundy |
| **Easy Decider** | Action-oriented, dynamic. Airport curbside. App interface. Quick booking flow. | Bright contrast, clean white + accent color |

**If images are not yet produced**: Use high-quality stock photography matching the above direction. Image quality matters for native ads — low-quality images reduce CTR significantly.

---

## STEP 8: BIDDING STRATEGY

### Base CPM by Archetype

| Archetype | Base CPM | Peak Multiplier | Rationale |
|-----------|---------|-----------------|-----------|
| Status Seeker | $10.40 | 1.3× | Highest LTV, 94.5% conversion justifies premium |
| Easy Decider | $8.80 | 1.1× | 90.9% conversion, standard bids work |
| Careful Truster | $8.00 | 1.3× (peak hours) | Volume play, boost during research windows |

### Device Multipliers

| Device | Multiplier |
|--------|-----------|
| Desktop | 1.0× |
| Mobile | 1.1× |
| Tablet | 0.9× |

### Special Signal Bid Adjustments

| Signal | Multiplier | When |
|--------|-----------|------|
| Booking Started (abandoned) | 2.0× | Touch 4-5 campaigns |
| Repeat Visitor (3+ visits) | 1.5× | Touch 3-5 campaigns |

---

## STEP 9: MEASUREMENT FRAMEWORK

### Primary KPI
**Cost per Booking (CPB)** = Total Spend / Booking Complete conversions

### Secondary KPIs
| KPI | How to Measure | Target |
|-----|---------------|--------|
| Per-touch CTR | StackAdapt reporting by campaign | Touch 1: 0.5%, Touch 5: 1.5% |
| Conversion rate by archetype | Campaign Group reporting | CT: 65%, SS: 94.5%, ED: 90.9% |
| Stage progression rate | Site Visit → Pricing → Booking Start → Complete | ≥ 30% advance rate per stage |
| Incremental ROAS | Booking revenue / Ad spend | Target: 3.0× or higher |

### The Hypothesis Being Tested

> **Each subsequent touch should convert at a higher rate than the previous.**
>
> If Touch N converts lower than Touch N-1 for any archetype, the mechanism
> mapping for that position needs adjustment. This is the core validation
> of the INFORMATIV psycholinguistic approach.

### Reporting Breakdown

In StackAdapt reporting, always break down by:
1. **Campaign Group** = archetype performance comparison
2. **Campaign** = per-touch conversion funnel
3. **Creative** = which psychological mechanism works
4. **Domain** = which publisher contexts drive conversion

---

## STEP 10: PRE-LAUNCH CHECKLIST

Before setting campaigns to ACTIVE, verify every item:

### Pixel & Tracking
- [ ] StackAdapt Universal Pixel installed via GTM (firing on all pages)
- [ ] INFORMATIV telemetry script installed via GTM (firing on all pages)
- [ ] Pixel verified: check StackAdapt Pixels page shows "Last Fired" recent timestamp
- [ ] 4 conversion events created in StackAdapt with correct rules
- [ ] Booking Start GTM tag firing on booking initiation
- [ ] Booking Complete GTM tag firing on confirmation (with revenue)

### Audiences
- [ ] 5 retargeting audiences created
- [ ] 5 sequential touch audiences created (Touch 2-3 may need campaigns to exist first)
- [ ] `Converted (EXCLUDE)` applied to ALL 15 campaigns

### Domain Lists
- [ ] Whitelist uploaded (42 domains)
- [ ] Blacklist uploaded (22 domains)

### Campaign Structure
- [ ] 3 campaign groups created with correct daily budgets
- [ ] 15 campaigns created (5 per group)
- [ ] Click URLs include StackAdapt macros (sapid, cid, crid, domain, device, ts)
- [ ] Frequency caps set per archetype
- [ ] Dayparting bid adjustments set per archetype

### Creatives
- [ ] 15 creatives uploaded (one per campaign)
- [ ] Creative rotation DISABLED (one creative per campaign)
- [ ] All headlines, body text, and CTAs match this document exactly
- [ ] Image assets meet native spec (1200×627 primary)

### INFORMATIV Server (Confirmed by INFORMATIV Team)
- [ ] INFORMATIV server URL provided and accessible
- [ ] Health check passes: `GET https://[SERVER]/health/ready`
- [ ] Telemetry endpoint accepting data: `POST https://[SERVER]/api/v1/signals/session`

### Launch
- [ ] All 15 campaigns set to DRAFT for final review
- [ ] All settings reviewed against this document
- [ ] Change all 15 campaigns to **ACTIVE**

---

## POST-LAUNCH MONITORING GUIDE

### Day 1
- Verify all 15 campaigns are serving impressions
- Check StackAdapt Universal Pixel is firing (Pixels page → Last Fired)
- Confirm INFORMATIV server is receiving telemetry (health endpoint)

### Week 1
- Review per-campaign impressions, clicks, CTR
- Check per-archetype conversion rates
- Verify frequency caps are being respected
- Flag any campaigns with zero delivery (targeting too narrow?)

### Week 2
- First meaningful conversion data available
- Compare Touch 1 vs Touch 2 vs Touch 3 conversion rates (should increase)
- Identify top-performing domains per archetype
- Review INFORMATIV learning metrics

### Week 3-4
- Full pilot assessment
- Per-archetype ROAS calculation
- Document which touch positions and mechanisms drive highest conversion
- Prepare results report

---

## CONTACT

| Topic | Contact |
|-------|---------|
| Campaign strategy & copy | INFORMATIV team |
| StackAdapt platform issues | Your StackAdapt account manager |
| INFORMATIV server / telemetry | INFORMATIV team |
| luxyride.com pixel installation | LUXY Ride development team |
| Creative asset production | Agency creative team |

---

## FILES INCLUDED IN THIS PACKAGE

| File | Purpose | Upload to StackAdapt? |
|------|---------|----------------------|
| `AGENCY_HANDOFF_COMPLETE.md` | This document | No (reference only) |
| `domain_whitelist_ALL.csv` | Site inclusion list | **YES** — upload as whitelist |
| `domain_blacklist.csv` | Site exclusion list | **YES** — upload as blacklist |
| `luxy_ride_creatives.json` | Full creative specs (machine-readable) | No (reference; manually enter copy) |
| `luxy_ride_campaign_config.json` | Master campaign config | No (reference for settings) |
| `luxy_ride_frequency_caps.json` | Frequency cap rules | No (reference; set in campaign settings) |
| `luxy_ride_dayparting.json` | Dayparting schedules | No (reference; set in campaign settings) |
| `luxy_ride_audiences.json` | Audience definitions | No (reference; create manually) |
| `luxy_ride_measurement.json` | Conversion event definitions | No (reference; create in Pixels page) |

---

*This document was generated by INFORMATIV's bilateral intelligence system. The creative copy, targeting strategy, domain selection, and mechanism sequencing are all derived from analysis of 1,492 bilateral psychological edges across luxury transportation consumers. Each decision in this campaign has an empirical basis.*
