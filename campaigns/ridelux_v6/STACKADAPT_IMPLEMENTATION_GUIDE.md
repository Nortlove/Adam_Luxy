# LUXY Ride — StackAdapt Implementation Guide
## Complete Step-by-Step Setup for the INFORMATIV Therapeutic Retargeting Campaign
## Generated: March 26, 2026

---

## StackAdapt Campaign Hierarchy

StackAdapt uses this structure:
```
Advertiser (LUXY Ride)
  └── Campaign Group (= Insertion Order / Line Item)
        └── Campaign (one per channel × archetype × touch)
              └── Creative (ad copy + image per campaign)
```

Our INFORMATIV campaign maps as:
```
Advertiser: LUXY Ride
  ├── Campaign Group: Careful Truster Retargeting
  │     ├── Campaign: CT Touch 1 (Native) — social_proof_matched
  │     ├── Campaign: CT Touch 2 (Native) — evidence_proof
  │     ├── Campaign: CT Touch 3 (Native) — evidence_proof
  │     ├── Campaign: CT Touch 4 (Native) — social_proof_matched
  │     └── Campaign: CT Touch 5 (Native) — anxiety_resolution
  ├── Campaign Group: Status Seeker Retargeting
  │     ├── Campaign: SS Touch 1 — narrative_transportation
  │     ├── Campaign: SS Touch 2 — social_proof_matched
  │     ├── Campaign: SS Touch 3 — narrative_transportation
  │     ├── Campaign: SS Touch 4 — social_proof_matched
  │     └── Campaign: SS Touch 5 — claude_argument
  └── Campaign Group: Easy Decider Retargeting
        ├── Campaign: ED Touch 1 — loss_framing
        ├── Campaign: ED Touch 2 — implementation_intention
        ├── Campaign: ED Touch 3 — micro_commitment
        ├── Campaign: ED Touch 4 — ownership_reactivation
        └── Campaign: ED Touch 5 — micro_commitment
```

---

## STEP 1: Account Setup

### Prerequisites
- StackAdapt advertiser account (request via sales@stackadapt.com)
- GraphQL API key (separate from REST API key — request from StackAdapt team)

### Authentication
```
Header: "Authorization": "Bearer <YOUR_GRAPHQL_API_TOKEN>"
Endpoint: https://api.stackadapt.com/graphql
```

### Create Advertiser
In the StackAdapt UI or via GraphQL API, create the advertiser:
- **Advertiser Name**: LUXY Ride
- **Website URL**: https://luxyride.com
- **Industry**: Transportation / Luxury Services
- **Save the Advertiser ID** — needed for all subsequent API calls

---

## STEP 2: Universal Pixel Installation

### What It Does
The Universal Pixel is a single JavaScript tag placed on ALL pages of luxyride.com. It:
- Tracks all site visitors (builds retargeting audience pools)
- Fires conversion events (booking_start, booking_complete)
- Enables lookalike audience creation
- Provides cross-device tracking

### Installation
1. In StackAdapt, navigate to **Pixels** page
2. Find your **Universal Pixel ID** (format: `sa-XXXXXXXX`)
3. Install the pixel on luxyride.com — options:
   - **Direct**: Add the JavaScript snippet to every page's `<head>`
   - **Google Tag Manager**: Use the [StackAdapt GTM Server-Side Pixel](https://github.com/StackAdapt/stackadapt-gtm-server-side-pixel)
   - **Segment/Freshpaint**: Use the StackAdapt destination integration

### Pixel Code (Direct Installation)
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

Replace `YOUR_UNIVERSAL_PIXEL_ID` with the pixel ID from StackAdapt's Pixels page.

---

## STEP 3: Conversion Event Setup

Create 4 conversion events in StackAdapt:

### Event 1: Site Visit (awareness tracking)
- **Navigate**: Pixels → Create New → Conversion Event
- **Name**: LUXY Ride — Site Visit
- **Install Location**: Website
- **Activation Method**: Page Load
- **Pixel Type**: Universal Pixel
- **URL Rule**: contains "luxyride.com"
- **Attribution Window**: 30 days
- **Save the Conversion Event Unique ID**

### Event 2: Pricing View
- **Name**: LUXY Ride — Pricing View
- **Activation Method**: Page Load
- **URL Rule**: contains "/pricing" OR contains "/rates"
- **Attribution Window**: 14 days

### Event 3: Booking Start
- **Name**: LUXY Ride — Booking Start
- **Activation Method**: Custom Event
- **Custom Event Trigger**: `saq('conv', 'BOOKING_START_EVENT_ID')`
- **Attribution Window**: 7 days

Place this code on the booking initiation page:
```javascript
saq('conv', 'BOOKING_START_EVENT_ID');
```

### Event 4: Booking Complete (PRIMARY CONVERSION)
- **Name**: LUXY Ride — Booking Complete
- **Activation Method**: Custom Event
- **Custom Event Trigger**: `saq('conv', 'BOOKING_COMPLETE_EVENT_ID', { revenue: BOOKING_VALUE })`
- **Revenue Tracking**: Enabled
- **Attribution Window**: 7 days
- **Mark as Primary Conversion**

Place this code on the booking confirmation page:
```javascript
saq('conv', 'BOOKING_COMPLETE_EVENT_ID', {
  revenue: bookingValue,  // Dynamic booking value
  order_id: bookingId     // Unique booking ID for deduplication
});
```

---

## STEP 4: Audience Pool Setup

### Retargeting Audiences (built from Universal Pixel)

| Audience Name | Type | Rule | Lookback |
|---------------|------|------|----------|
| All Site Visitors | Retargeting | URL contains luxyride.com | 30 days |
| Pricing Page Visitors | Retargeting | URL contains /pricing OR /rates | 14 days |
| Booking Started (Not Completed) | Retargeting | Event: booking_start AND NOT booking_complete | 7 days |
| Multiple Visitors (3+) | Retargeting | Visit frequency ≥ 3 within 14 days | 14 days |
| Converted — EXCLUDE | Exclusion | Event: booking_complete | 90 days |

### Sequential Touch Audiences

These are built using StackAdapt's audience pool + impression tracking:

| Pool | Rule | Purpose |
|------|------|---------|
| Touch 1 Pool | All Site Visitors | First retargeting touch (prospecting) |
| Touch 2 Pool | Served Touch 1 AND did NOT click | Users who saw Touch 1 but didn't engage |
| Touch 3 Pool | Served Touch 2 AND did NOT click | Users who saw 2 touches without engaging |
| Touch 4 Pool | Booking Started but NOT Completed | Cart/booking abandoners |
| Touch 5 Pool | Multiple Visitors (3+) NOT Converted | High-intent non-converters |

**Critical**: ALWAYS exclude the "Converted — EXCLUDE" audience from every retargeting campaign.

---

## STEP 5: Creative Specifications

### Native Ads (Primary Channel)
| Spec | Requirement |
|------|-------------|
| **Image** | 1200 × 627 px (landscape), also: 600 × 600, 800 × 600 |
| **Headline** | 50 characters max (recommended) / 55 max (absolute) |
| **Body/Caption** | 120 characters max |
| **Sponsored By** | 25 characters max → "LUXY Ride" |
| **CTA Text** | 10 characters max → "Book Now", "Learn More" |
| **File Format** | JPG, PNG |
| **File Size** | < 2 MB |
| **Landing URL** | https://luxyride.com (with UTM parameters) |

### Display Ads
| Spec | Requirement |
|------|-------------|
| **Sizes** | 300×250, 728×90, 160×600, 320×50 (standard IAB) |
| **File Format** | JPG, PNG, GIF, HTML5 |
| **File Size** | < 150 KB (standard), < 200 KB (rich media) |
| **HTML5** | Use StackAdapt Creative Builder or upload ZIP |

### CTV/Video Ads
| Spec | Requirement |
|------|-------------|
| **Resolution** | 1920×1080 (recommended) |
| **Aspect Ratio** | 16:9 |
| **Duration** | ≤ 30 seconds |
| **Format** | MP4, VAST tag |
| **File Size** | Check with StackAdapt (typically < 50 MB) |

---

## STEP 6: Campaign Creation

For each campaign in `luxy_ride_campaign_config.json`:

### In StackAdapt UI:
1. Select Advertiser: LUXY Ride
2. Create Campaign Group (one per archetype)
3. Within each group, create campaigns (one per touch)
4. Set for each campaign:
   - **Channel**: Native (primary) / Display / CTV
   - **Budget**: Per `budget.daily` in the JSON
   - **Schedule**: Per `schedule.start_date` / `schedule.end_date`
   - **Targeting**:
     - Audience: Select the appropriate Touch Pool
     - Exclude: Converted audience (always)
     - Domains: Upload `luxy_ride_domain_whitelist.csv`
     - Block: Upload `luxy_ride_domain_blacklist.csv`
   - **Frequency Cap**: Per `luxy_ride_frequency_caps.json`
   - **Dayparting**: Per `luxy_ride_dayparting.json`
   - **Optimization Goal**: Clicks (Touch 1-2), Conversions (Touch 3-5)
5. Upload creative for each campaign

### Via GraphQL API:
```graphql
mutation {
  createCampaign(input: {
    advertiserId: "YOUR_ADVERTISER_ID"
    name: "LUXY Ride — Careful Truster — Touch 1"
    campaignGroupId: "YOUR_CAMPAIGN_GROUP_ID"
    type: NATIVE
    budget: { daily: 17.52, total: 525.69, currency: USD }
    schedule: { startDate: "2026-03-27", endDate: "2026-04-26" }
    # ... additional fields per StackAdapt GraphQL schema
  }) {
    id
    name
    status
  }
}
```

Note: Exact GraphQL mutation fields require access to StackAdapt's authenticated API documentation at https://docs.stackadapt.com/graphql. The schema is available after login with your API key.

---

## STEP 7: Domain Targeting

### Upload Whitelist
1. In StackAdapt, navigate to campaign targeting settings
2. Upload `luxy_ride_domain_whitelist.csv` as site inclusion list
3. Contains 12 premium travel/business domains

### Upload Blacklist
1. Upload `luxy_ride_domain_blacklist.csv` as site exclusion list
2. Contains 5 excluded domains

---

## STEP 8: Frequency Capping

Apply per-campaign group:
| Archetype | Max/Day | Max/Week | Min Hours Between |
|-----------|---------|----------|-------------------|
| Careful Truster | 2 | 5 | 12h |
| Status Seeker | 2 | 5 | 12h |
| Easy Decider | 2 | 5 | 12h |

---

## STEP 9: Dayparting

Apply the schedule from `luxy_ride_dayparting.json`:
- **Monday-Friday peak** (7-9am, 5-7pm ET): Bid +30%
- **Monday-Friday standard** (9am-5pm, 7-10pm ET): Bid normal
- **Monday-Friday off-hours** (10pm-7am ET): Bid -50%
- **Weekend peak** (9am-12pm, 4-8pm ET): Bid +20%
- **Weekend off-hours**: Bid -60%

---

## STEP 10: Measurement & Reporting

### Primary KPI
**Cost per Booking** (CPB) = Total Spend / Booking Complete conversions

### Secondary KPIs
- Per-touch conversion rate (should INCREASE from Touch 1 → Touch 5)
- Stage advancement rate (site visit → pricing → booking start → complete)
- Barrier resolution rate (proportion that advance after each touch)

### Reporting Breakdown
In StackAdapt reporting, break down by:
- **Campaign Group** (= archetype)
- **Campaign** (= touch position)
- **Creative** (= mechanism deployed)

### The Hypothesis to Test
> Each subsequent touch should convert at a HIGHER rate than the previous.
> If Touch N converts lower than Touch N-1, the mechanism mapping is
> wrong for that archetype and should be adjusted.

---

## INFORMATIV System Hardening (March 2026)

The following hardening was applied to the INFORMATIV platform to ensure
pilot reliability. These improvements are active for the LUXY Ride campaign.

### Production Safety
- **API Authentication**: Set `ADAM_API_KEYS` environment variable (comma-separated). All production endpoints require `X-API-Key` header. Health/metrics exempt.
- **Latency SLA**: 120ms request budget enforced. Cascade, prefetch, and DAG degrade gracefully if budget exhausted — returns best-available result instead of timing out.
- **Circuit Breakers**: Neo4j unavailability → automatic degradation to L1/L2 archetype priors in <1ms. Auto-recovery after 30 seconds. No manual intervention needed.
- **Thread Safety**: All posterior updates (Thompson Sampling, retargeting hierarchical priors) are lock-protected. No data corruption under concurrent load.
- **Memory Safety**: Redis keys have mandatory TTL (no leaks). Event bus queue bounded to 10K (drops with warning, never blocks hot path).

### Intelligence Pipeline (14-Atom DAG)
- **14 psychological atoms** execute in parallel across 5 levels (was 9 atoms)
- **5 new auxiliary atoms**: CognitiveLoad, DecisionEntropy, InformationAsymmetry, PredictiveError, AmbiguityAttitude — each contributes confidence-weighted mechanism adjustments
- **Evidence-weighted blending**: Mechanism scores blend by `confidence x log(1 + observations)` — high-evidence sources automatically dominate over low-evidence
- **NDF bypass**: When bilateral edge dimensions are available (all LUXY Ride requests with graph data), the 7-dim NDF compression layer is skipped. Full 20-dim bilateral evidence flows directly to mechanism scoring.

### Retargeting Engine Safety
- **Prompt injection protection**: All user-controlled data sanitized before Claude prompt interpolation (truncation, injection pattern stripping, XML data tags)
- **Bounded conversation memory**: 20 turns/sequence max, 5,000 concurrent sequences, 1-hour stale eviction
- **Externalized thresholds**: `max_touches`, `reactance_ceiling`, `ctr_floor` etc. configurable via environment variables (`THRESHOLD_RETARGET_*`)

### Persistence & Learning
- **Decision context durability**: Decision contexts written to Neo4j on every persist. If app restarts between decision and outcome, the webhook recovers context from Neo4j.
- **Auto-persist posteriors**: Retargeting posteriors auto-persist to Neo4j every 100 updates or 60 seconds.
- **Meta-learner fallback chain**: Redis → Neo4j → fresh priors. Warning logged when falling back to fresh priors.

### Copy Generation
- **Bilateral edge dimensions** map directly to copy parameters: `emotional_resonance` → emotional appeal, `autonomy_reactance` → reduced urgency, `loss_aversion_intensity` → loss framing
- **ConstrualLevel** uses proper 4-distance CLT (temporal, social, spatial, hypothetical) backed by bilateral edge dimensions, replacing session-depth proxy

### Observability
- **Prometheus metrics**: cascade_level, prefetch_sources, mechanism_selected, posterior_mean, budget_utilization, circuit_breaker_state, prefetch_empty alerts
- **Drift detection**: Auto-warm-up from first 100 observations. No manual reference window setup needed.

---

## STEP 11: Launch Checklist

- [ ] Advertiser created in StackAdapt (save Advertiser ID)
- [ ] GraphQL API key obtained (if using API)
- [ ] Universal Pixel installed on ALL pages of luxyride.com
- [ ] Universal Pixel ID recorded
- [ ] 4 conversion events created (site_visit, pricing_view, booking_start, booking_complete)
- [ ] Conversion Event IDs recorded and added to luxyride.com pages
- [ ] Revenue tracking enabled on booking_complete event
- [ ] 5 retargeting audiences created from pixel rules
- [ ] 5 sequential touch audiences configured
- [ ] Converted exclusion audience applied to ALL campaigns
- [ ] Domain whitelist CSV uploaded
- [ ] Domain blacklist CSV uploaded
- [ ] 3 Campaign Groups created (one per archetype)
- [ ] 15 Campaigns created (5 per group, sequential)
- [ ] 15 Creatives uploaded (one per campaign)
- [ ] Frequency caps applied per campaign group
- [ ] Dayparting schedule applied
- [ ] All campaigns set to DRAFT status for review
- [ ] INFORMATIV API key set (`ADAM_API_KEYS` env var on production server)
- [ ] Neo4j running and accessible (enables L3/L4 bilateral cascade)
- [ ] Redis running and accessible (enables buyer profile caching)
- [ ] Gradient fields pre-computed (`scripts/compute_gradient_fields.py`)
- [ ] Final review complete → change status to ACTIVE

---

## Files in This Package

| File | StackAdapt Use |
|------|----------------|
| `luxy_ride_campaign_config.json` | Master config — import or reference for all settings |
| `luxy_ride_audiences.json` | Audience definitions — create in StackAdapt Audiences |
| `luxy_ride_creatives.json` | Creative specs — produce creative assets per spec |
| `luxy_ride_domain_whitelist.csv` | Upload as site inclusion list (24 domains, expanded for Easy Decider coverage) |
| `luxy_ride_domain_blacklist.csv` | Upload as site exclusion list |
| `luxy_ride_site_profiles.json` | Psychological profiles for all 24 whitelisted domains — informs creative selection |
| `luxy_ride_retargeting_rules.json` | Sequential touch logic — configure campaign sequencing |
| `luxy_ride_frequency_caps.json` | Apply to campaign group settings (differentiated per archetype) |
| `luxy_ride_dayparting.json` | Apply to campaign scheduling |
| `luxy_ride_measurement.json` | Conversion pixel setup reference |

---

## Key Technical Notes

### StackAdapt API Authentication
- GraphQL API uses Bearer token: `Authorization: Bearer <token>`
- REST API (deprecated) uses: `X-AUTHORIZATION: <key>`
- GraphQL API key is SEPARATE from REST API key
- Request API access at https://docs.stackadapt.com/

### Audience Matching for First-Party Data
If uploading CRM/1st-party data for audience targeting:
- Supported PII fields: email, first_name, last_name, phone, address, city, state, zip
- Minimum valid combinations: email alone, OR first+last+email, OR first+last+phone, OR first+last+zip
- Hashing: SHA-1 algorithm
- Integration via: LiveRamp, Adobe Audience Manager, Salesforce, or direct upload
- Enable "Match Booster" for improved match rates

### Archetype-Audience Mapping (Important)
The 5 Touch Pools are shared across all 3 archetypes — StackAdapt cannot classify users into archetypes from pixel data alone. To handle this correctly:

1. Each of the **15 campaigns** (3 archetypes x 5 touches) targets the **same shared pool** for its touch position
2. Each campaign uses its own **archetype-specific creative** (from `luxy_ride_creatives.json`)
3. StackAdapt's optimization ML will naturally allocate impressions to the users who respond to each creative
4. The **Converted (EXCLUDE)** audience MUST be applied to ALL 15 campaigns to prevent post-conversion waste
5. **Do NOT** use StackAdapt's standard creative rotation — each campaign gets exactly ONE creative

This means all three archetypes compete for the same pool, but their different creatives, dayparting schedules, and frequency caps create natural separation. StackAdapt's algorithm learns which users respond to which creative style.

### Sequential Retargeting Without Live INFORMATIV Integration
Since INFORMATIV is not currently a live StackAdapt integration partner:
1. Audiences are built from PIXEL BEHAVIOR (site visits, events), not INFORMATIV segment IDs
2. Archetype classification happens on INFORMATIV's side; StackAdapt targets by BEHAVIOR
3. Touch sequencing is implemented via CAMPAIGN EXCLUSION RULES:
   - Touch 2 excludes users who engaged with Touch 1
   - Touch 3 excludes users who engaged with Touch 2
   - etc.
4. This approximates archetype-based targeting through behavioral proxies

### Future Integration Path
When INFORMATIV becomes a StackAdapt integration partner:
- INFORMATIV segment IDs can be synced directly to StackAdapt audiences
- Real-time bilateral intelligence can feed creative parameters via API
- The learning loop can receive StackAdapt conversion webhooks directly
- Full closed-loop optimization becomes possible

Sources:
- [StackAdapt API Docs](https://docs.stackadapt.com/)
- [StackAdapt GTM Pixel (GitHub)](https://github.com/StackAdapt/stackadapt-gtm-server-side-pixel)
- [StackAdapt Creative Specs](https://wulver.ca/digital-ad-specs/)
- [StackAdapt Dimensions & Metrics](https://help.funnel.io/en/articles/4579552-stackadapt-dimensions-and-metrics)
- [StackAdapt + Hightouch Audience Sync](https://hightouch.com/docs/destinations/stackadapt)
- [StackAdapt + Freshpaint Pixel Setup](https://documentation.freshpaint.io/integrations/destinations/demand-side-platforms-dsps/stackadapt/stackadapt)
