# INFORMATIV × LUXY Ride — Agency Campaign Brief
## For: Zero Gravity Marketing (Becca Matyasovsky)
## Date: April 14, 2026

---

## WHAT THIS IS

INFORMATIV has developed a **psycholinguistic advertising intelligence system** that matches ad creative to the psychological context of the reader. We've analyzed LUXY Ride's actual customer base — corporate travel arrangers, travel managers, event planners, legal ops, pharma compliance, and financial dealmakers — and identified **6 launch audiences** (with 5 more in Phase 2) with **6 distinct creative treatments** for launch.

This brief provides everything you need to run a year-long campaign in StackAdapt for LUXY Ride at approximately **$24,000/week ($96K/month), concentrated for maximum learning velocity**.

**Key insight:** LUXY Ride is a **corporate black car service** integrated with Concur, TripActions, CWT, Amex GBT, CTM, and FCM. The customer is never "a person who likes luxury." The customer is an EA booking for an executive, a travel manager evaluating vendors, an event planner coordinating group arrivals. Every domain, every creative, and every targeting decision in this brief reflects that reality.

---

## HOW THIS WORKS

### You Control (Agency)
- StackAdapt campaign setup, management, and optimization
- Creative production (images — we provide copy and art direction)
- Bid strategy, pacing, and budget allocation
- Day-to-day campaign optimization

### INFORMATIV Provides
- **Campaign strategy**: 11 audiences, creative copy, domain targeting
- **Behavioral intelligence**: Telemetry script on luxyride.com capturing post-click behavior
- **Every-other-day optimization**: Specific StackAdapt changes recommended based on observed data
- **Domain targeting**: Per-audience whitelists verified at the article level

### LUXY Ride Provides
- Google Tag Manager access (one tag to install)

---

## THE 11 AUDIENCES

| # | Audience | Budget | Weekly $ | Campaigns |
|---|---|---|---|---|
| 1 | Corporate Travel Arrangers (EAs) | 28% | $6,719 | EA-T1, EA-T2, EA-T3 |
| 2 | Corporate Travel Managers | 25% | $5,999 | TM-T1, TM-T2, TM-T3 |
| 3 | Home Market (CT/NYC) | 18% | $4,319 | HM-T1, HM-T2, HM-T3 |
| 4 | Event / Meeting / Incentive Planners | 12% | $2,880 | EV-T1, EV-T2, EV-T3 |
| 5 | Legal Vertical (BigLaw) | 10% | $2,400 | LG-T1, LG-T2, LG-T3 |
| 6 | Life Sciences / Pharma | 7% | $1,680 | LS-T1, LS-T2, LS-T3 |

**Total: $24,000/week ($3,428/day) — 18 campaigns**

**Phase 2 audiences (weeks 5+, based on Phase 1 data):**

---

## TAG INSTALLATION

### Tag A: StackAdapt Universal Pixel (All Pages)
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

### Tag B: INFORMATIV Behavioral Intelligence (All Pages)
```html
<script src="https://focused-encouragement-production.up.railway.app/static/telemetry/informativ.js"
        data-endpoint="https://focused-encouragement-production.up.railway.app/api/v1/signals/session"
        defer></script>
```

---

## CONVERSION EVENTS

| # | Name (exact) | Method | Rule | Attribution | Primary |
|---|---|---|---|---|---|
| 1 | `luxy_site_visit` | Page Load | URL contains `luxyride.com` | 30 days | No |
| 2 | `luxy_booking_page` | Page Load | URL contains `/programs/book` | 14 days | No |
| 3 | `luxy_booking_start` | Page Load | Booking trigger | 7 days | No |
| 4 | `luxy_booking_complete` | Custom Event | Confirmation page | 7 days | **YES** |
| 5 | `luxy_corporate_signup` | Page Load | Corporate Program signup | 14 days | No |

---

## AUDIENCES

| # | Name | Type | Rule | Lookback |
|---|---|---|---|---|
| 1 | `luxy_all_visitors` | Retargeting | URL contains luxyride.com | 30 days |
| 2 | `luxy_booking_visitors` | Retargeting | URL contains `/programs/book` | 14 days |
| 3 | `luxy_high_intent` | Retargeting | Visit frequency >= 3 | 14 days |
| 4 | `luxy_converted_exclude` | Exclusion | Event: luxy_booking_complete | 90 days |
| 5 | `luxy_booking_abandoned` | Retargeting | booking_start AND NOT complete | 7 days |

**CRITICAL**: Apply `luxy_converted_exclude` as exclusion to ALL 18 campaigns.

---

## DOMAIN LISTS

| Audience | Whitelist File |
|---|---|
| Travel Arrangers (EAs) | `stackadapt_whitelist_reliable_cooperator.csv` |
| Travel Managers | `stackadapt_whitelist_dependable_loyalist.csv` |
| Home Market (CT/NYC) | `stackadapt_whitelist_home_market.csv` |
| Event Planners | `stackadapt_whitelist_prevention_planner.csv` |
| Legal Vertical | `stackadapt_whitelist_careful_truster.csv` |
| Life Sciences | `stackadapt_whitelist_careful_truster.csv` (shared with Legal) |

**Shared blacklist**: `stackadapt_blacklist_upload.csv` → ALL campaigns.

---

## CLICK URL (ALL campaigns)

```
https://luxyride.com/?sapid={SA_POSTBACK_ID}&cid={CAMPAIGN_ID}&crid={CREATIVE_ID}&domain={DOMAIN}&device={DEVICE_TYPE}&ts={TIMESTAMP}
```

---

## CAMPAIGN DETAILS

### 1. Corporate Travel Arrangers — EA (22%, $960/day)

| Campaign | Headline | Body | CTA | $/day | Goal |
|---|---|---|---|---|---|
| EA-T1 | "Your executive's next trip, booked in 30 seconds" | LUXY integrates with Concur, TripActions, and every major TMC. Your travelers get professional chauffeurs. You get one-click booking and real-time trip tracking. | See how it works | $480 | Clicks |
| EA-T2 | "The ground transport your travelers actually deserve" | Not all car services are equal. Company-employed drivers. Background checks. Flight monitoring. Your executive's preferences saved from the first ride. | Compare services | $320 | Clicks |
| EA-T3 | "Your booking hub for every airport, every city" | One platform, 100+ cities, integrated with your travel management system. Book for your travelers in seconds. Concierge Dashboard built for travel arrangers. | Start booking | $160 | Conversions |

**Frequency**: 2/day, 7/week | **Dayparting**: +20% 8-10am, +15% 1-3pm

---

### 2. Corporate Travel Managers (20%, $857/day)

| Campaign | Headline | Body | CTA | $/day | Goal |
|---|---|---|---|---|---|
| TM-T1 | "43% of companies don't have a chauffeured contract. Yours?" | BTN 2026 survey: service consistency jumped 0.47 points for preferred partners. LUXY serves 400+ companies through Concur, TripActions, CWT, Amex GBT, CTM, FCM. | See the data | $428 | Clicks |
| TM-T2 | "SOC 2 certified. ISO-aligned. Sunshine Act ready." | Company-employed chauffeurs scored 4.43/5 — highest in BTN survey. Background checks, GPS tracking, 24/7 dispatch. | Request vendor packet | $286 | Clicks |
| TM-T3 | "Add LUXY to your preferred vendor list" | Corporate rates. Policy-compliant booking. Real-time trip-level spend data. 400+ companies onboarded. No minimum commitment. | Start corporate program | $143 | Conversions |

**Frequency**: 2/day, 7/week | **Dayparting**: +20% 9-11am, +15% 2-4pm

---

### 3. Home Market — CT/NYC (15%, $617/day)

| Campaign | Headline | Body | CTA | $/day | Goal |
|---|---|---|---|---|---|
| HM-T1 | "The Connecticut-based car service trusted by 400+ companies" | Stamford to JFK. Greenwich to LaGuardia. New Haven to Newark. Chauffeurs who know your routes, your buildings, your airports. | See local coverage | $309 | Clicks |
| HM-T2 | "Your NYC ground transport, handled" | Midtown to Teterboro in 40 minutes. Wall Street to JFK, door to door. 99.7% on-time across the tri-state. | Check your route | $206 | Clicks |
| HM-T3 | "Your neighbors already ride with us" | 400+ companies in the CT/NYC corridor trust LUXY. Corporate rates, Concur integration, chauffeurs who know the tri-state. | Book your first ride | $103 | Conversions |

**Frequency**: 2/day, 8/week | **Dayparting**: +25% 7-9am, +20% 5-7pm

---

### 4. Event Planners (12%, $411/day)

| Campaign | Headline | Body | CTA | $/day | Goal |
|---|---|---|---|---|---|
| EV-T1 | "Your 200-person airport arrival, handled" | Multi-vehicle coordination across every LUXY city. Backup operators at every location. Real-time manifest tracking. | See group capabilities | $206 | Clicks |
| EV-T2 | "Zero transportation failures at your next event" | Flight monitoring for every attendee. Automatic delay adjustment. Contingency vehicles pre-positioned. | Plan your event | $114 | Clicks |
| EV-T3 | "The event planner's ground transport partner" | Conferences. Incentive trips. Galas. Board retreats. One booking hub, every city, every vehicle class. | Get a group quote | $58 | Conversions |

**Frequency**: 2/day, 7/week | **Dayparting**: +20% 9am-12pm

---

### 5. Legal Vertical (10%, $343/day)

| Campaign | Headline | Body | CTA | $/day | Goal |
|---|---|---|---|---|---|
| LG-T1 | "On time, every time. Your billable hour is non-negotiable." | A partner billing $1,200/hr cannot afford a 45-minute rideshare delay. Company-employed chauffeurs, flight monitoring, guaranteed pickup. | Learn more | $171 | Clicks |
| LG-T2 | "SOC 2 data handling. Vetted for BigLaw." | Background-checked drivers. GPS tracking. Disbursement-ready receipts. Duty of care for associates in unfamiliar cities. | See credentials | $114 | Clicks |
| LG-T3 | "Depositions. Court appearances. Client visits. Covered." | Courthouse to hotel. Office to airport. 100+ cities, integrated with Amex GBT Legal. | Set up firm account | $57 | Conversions |

**Frequency**: 2/day, 6/week | **Dayparting**: +20% 7-9am, +15% 5-8pm

---

### 6. Life Sciences / Pharma (7%, $240/day)

| Campaign | Headline | Body | CTA | $/day | Goal |
|---|---|---|---|---|---|
| LS-T1 | "Audit-ready ground transport for HCP guest travel" | Every HCP ride is a Sunshine Act transfer of value. LUXY captures booker, passenger, addresses, duration, amount — audit-ready. | See compliance features | $120 | Clicks |
| LS-T2 | "Fewer than half of pharma programs meet a global standard" | BCD benchmarking of 15 global life sciences travel policies found fewer than half meet a consistent standard. 43% have no compliant ground transport. LUXY: one platform, SOC 2 certified, Sunshine Act export built in. | Request compliance demo | $80 | Clicks |
| LS-T3 | "The only ground transport built for regulated verticals" | Sunshine Act. EFPIA. Event tagging. HCP flags. Integrated with BCD, Amex GBT, CWT. Built for pharma. | Start pilot program | $40 | Conversions |

**Frequency**: 2/day, 6/week | **Dayparting**: +20% 9-11am

---

## IMAGE ART DIRECTION

| Audience | Visual Style | Palette |
|---|---|---|
| Travel Arrangers | Clean booking interface, EA at desk, laptop | Navy, white, teal |
| Travel Managers | Data dashboard, compliance badges, professional | Slate, white, green |
| Home Market | NYC skyline, CT suburbs, recognizable landmarks | Warm navy, gold |
| Event Planners | Group arrivals, multiple vehicles, venue exterior | Black, emerald |
| Legal | Courthouse, downtown professional, boardroom | Dark navy, silver |
| Life Sciences | Lab-to-airport, compliance documents | White, blue, trust green |

**Sizes**: 1200x627 (primary), 600x600 (square), 800x600 (alternate). JPG/PNG under 2MB.

---

## OPTIMIZATION CADENCE

**Every other day** — INFORMATIV delivers specific StackAdapt actions:
- Which audiences/domains are converting (with data)
- Budget shift recommendations (with dollar amounts)
- Creative refresh signals
- New domain recommendations
- User suppression list updates

**Agency implements** recommended changes within 24 hours.

---

## BEFORE LAUNCH CHECKLIST

### Agency:
- [ ] Both GTM tags installed and published
- [ ] StackAdapt pixel confirmed firing
- [ ] 6 conversion events created
- [ ] 5 audiences created
- [ ] `luxy_converted_exclude` on ALL 18 campaigns
- [ ] Per-audience whitelists uploaded
- [ ] Shared blacklist on all campaigns
- [ ] 6 campaign groups with correct budgets
- [ ] 18 campaigns with correct copy
- [ ] Click URLs include StackAdapt macros
- [ ] Frequency caps set per audience
- [ ] Dayparting set per audience
- [ ] 18 image creatives uploaded
- [ ] Supply Partner campaigns on SEPARATE line item
- [ ] All campaigns in DRAFT

### INFORMATIV:
- [ ] Server healthy
- [ ] Telemetry endpoint active
- [ ] CORS configured
- [ ] Intelligence report generator tested

### Joint:
- [ ] Review all 18 campaigns
- [ ] Test clicks verified
- [ ] Optimization cadence confirmed (every 48 hours)
- [ ] Set all to ACTIVE

---

## FILES PROVIDED

| File | Purpose |
|---|---|
| `START_HERE.md` | How to use these files |
| `AGENCY_BRIEF.md` | This document |
| `AGENCY_HANDOFF_COMPLETE.md` | Step-by-step setup |
| `luxy_ride_complete_creatives.json` | 28 campaign specs |
| `stackadapt_whitelist_*.csv` (6 files) | Per-audience whitelists |
| `stackadapt_blacklist_upload.csv` | Shared exclusion list |
| `IMAGE_CREATIVE_BRIEFS.md` | Image specifications |

---

*Every domain hand-researched at the article level. Every creative matched to the reader's professional context. Every audience verified against LUXY Ride's actual customer base.*
