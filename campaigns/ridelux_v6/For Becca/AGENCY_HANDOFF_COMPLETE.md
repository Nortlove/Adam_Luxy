# INFORMATIV × LUXY Ride — Complete Agency Handoff
## For: Zero Gravity Marketing (Becca Matyasovsky)
## Date: April 13, 2026

---

## CAMPAIGN SUMMARY

| Item | Value |
|------|-------|
| Archetypes (targeting) | 7 |
| Archetypes (suppression) | 3 |
| Campaign groups | 7 |
| Total campaigns | 28 |
| Total creatives | 28 (1 per campaign, NO rotation) |
| Daily budget | $240.75 |
| Monthly budget (30 days) | $7,222.50 |
| Domain targeting | Per-archetype whitelists (7 CSV files) |
| Blacklist | 21 domains (1 shared CSV) |

---

## FILES PROVIDED

| File | Purpose |
|------|---------|
| `AGENCY_BRIEF.md` | Full campaign strategy, creative copy, setup instructions |
| `luxy_ride_complete_creatives.json` | All 28 campaign specs (machine-readable) |
| `luxy_ride_site_profiles_v2.json` | 41 domains scored by goal activation per archetype |
| `domain_archetype_mapping.json` | Per-archetype domain rankings with crossover scores |
| `stackadapt_whitelist_trusting_loyalist.csv` | Domain whitelist for Trusting Loyalist (14 domains) |
| `stackadapt_whitelist_reliable_cooperator.csv` | Domain whitelist for Reliable Cooperator (17 domains) |
| `stackadapt_whitelist_careful_truster.csv` | Domain whitelist for Careful Truster (21 domains) |
| `stackadapt_whitelist_explorer.csv` | Domain whitelist for Explorer (15 domains) |
| `stackadapt_whitelist_prevention_planner.csv` | Domain whitelist for Prevention Planner (17 domains) |
| `stackadapt_whitelist_dependable_loyalist.csv` | Domain whitelist for Dependable Loyalist (20 domains) |
| `stackadapt_whitelist_consensus_seeker.csv` | Domain whitelist for Consensus Seeker (11 domains) |
| `stackadapt_blacklist_upload.csv` | Shared exclusion list (21 domains) |

---

## STEP-BY-STEP SETUP

### 1. Install Tags on luxyride.com (via GTM)

**Tag A: StackAdapt Universal Pixel** — All Pages trigger
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

**Tag B: INFORMATIV Behavioral Intelligence** — All Pages trigger
```html
<script src="https://focused-encouragement-production.up.railway.app/static/telemetry/informativ.js"
        data-endpoint="https://focused-encouragement-production.up.railway.app/api/v1/signals/session"
        defer></script>
```

### 2. Create 4 Conversion Events

| Name (exact) | Method | Rule | Attribution | Primary |
|---|---|---|---|---|
| `luxy_site_visit` | Page Load | URL contains `luxyride.com` | 30 days | No |
| `luxy_booking_page` | Page Load | URL contains `/programs/book` | 14 days | No |
| `luxy_booking_start` | Page Load | Booking trigger | 7 days | No |
| `luxy_booking_complete` | Custom Event / Page Load | Confirmation page | 7 days | **YES** |

### 3. Create 5 Audiences

| Name (exact) | Type | Rule | Lookback |
|---|---|---|---|
| `luxy_all_visitors` | Retargeting | URL contains luxyride.com | 30 days |
| `luxy_booking_visitors` | Retargeting | URL contains `/programs/book` | 14 days |
| `luxy_high_intent` | Retargeting | Visit frequency >= 3 | 14 days |
| `luxy_converted_exclude` | Exclusion | Event: luxy_booking_complete | 90 days |
| `luxy_booking_abandoned` | Retargeting | luxy_booking_start AND NOT complete | 7 days |

**CRITICAL**: Apply `luxy_converted_exclude` as exclusion to ALL 28 campaigns.

### 4. Upload Domain Lists

**Per-archetype whitelists** — each campaign group gets its own Site Inclusion List:

| Campaign Group | Whitelist File | Domains |
|---|---|---|
| Trusting Loyalist | `stackadapt_whitelist_trusting_loyalist.csv` | 14 |
| Reliable Cooperator | `stackadapt_whitelist_reliable_cooperator.csv` | 17 |
| Careful Truster | `stackadapt_whitelist_careful_truster.csv` | 21 |
| Explorer | `stackadapt_whitelist_explorer.csv` | 15 |
| Prevention Planner | `stackadapt_whitelist_prevention_planner.csv` | 17 |
| Dependable Loyalist | `stackadapt_whitelist_dependable_loyalist.csv` | 20 |
| Consensus Seeker | `stackadapt_whitelist_consensus_seeker.csv` | 11 |

**Shared blacklist** — apply `stackadapt_blacklist_upload.csv` (21 domains) to ALL campaigns.

**Why per-archetype whitelists?** Each domain was scored by the psychological goals its content activates. A Forbes article primes authority/competence goals — ideal for Dependable Loyalist ads, counterproductive for Prevention Planner ads. Matching the domain to the archetype ensures the page content is already priming the goal that our ad fulfills.

### 5. Create 7 Campaign Groups

| # | Name | Daily Budget | Whitelist |
|---|------|---|---|
| 1 | `LUXY — Trusting Loyalist` | $78.75 | trusting_loyalist CSV |
| 2 | `LUXY — Reliable Cooperator` | $49.50 | reliable_cooperator CSV |
| 3 | `LUXY — Careful Truster` | $40.50 | careful_truster CSV |
| 4 | `LUXY — Explorer` | $27.00 | explorer CSV |
| 5 | `LUXY — Prevention Planner` | $18.00 | prevention_planner CSV |
| 6 | `LUXY — Dependable Loyalist` | $15.75 | dependable_loyalist CSV |
| 7 | `LUXY — Consensus Seeker` | $11.25 | consensus_seeker CSV |

### 6. Create 28 Campaigns

**Click URL for ALL campaigns:**
```
https://luxyride.com/?sapid={SA_POSTBACK_ID}&cid={CAMPAIGN_ID}&crid={CREATIVE_ID}&domain={DOMAIN}&device={DEVICE_TYPE}&ts={TIMESTAMP}
```

See `AGENCY_BRIEF.md` for complete creative copy per campaign and `luxy_ride_complete_creatives.json` for machine-readable specs.

**Campaign IDs follow the pattern: [PREFIX]-T[TOUCH_NUMBER]**
- TL-T1 through TL-T5 (Trusting Loyalist)
- RC-T1 through RC-T5 (Reliable Cooperator)
- CT-T1 through CT-T4 (Careful Truster)
- EX-T1 through EX-T4 (Explorer)
- PP-T1 through PP-T4 (Prevention Planner)
- DL-T1 through DL-T3 (Dependable Loyalist)
- CS-T1 through CS-T3 (Consensus Seeker)

### 7. Frequency Caps and Dayparting

| Archetype | Freq Cap | Dayparting Notes |
|---|---|---|
| Trusting Loyalist | 2/day, 8/week | +20% 6-9am, +15% 5-10pm |
| Reliable Cooperator | 2/day, 7/week | +30% 6-9am, +15% 5-8pm, -20% weekend |
| Careful Truster | 3/day, 12/week | +30% 5-8am, +20% 5-10pm, +40% 10pm-5am |
| Explorer | 2/day, 6/week | +10% 9am-5pm, +20% 7-10pm |
| Prevention Planner | 2/day, 8/week | +30% 5-8am, +20% 8-10pm |
| Dependable Loyalist | 2/day, 7/week | +20% 6-9am, +15% 5-8pm |
| Consensus Seeker | 2/day, 7/week | +15% 5-10pm |

---

## INTELLIGENCE REPORTS

INFORMATIV provides weekly intelligence reports analyzing:
- Which archetype-domain combinations produced highest conversion rates
- Budget reallocation recommendations between archetypes
- Creative refresh suggestions based on mechanism effectiveness trends
- New domain recommendations from our active learning system
- Suppression list updates (users identified as Defensive Skeptic, Anxious Economist, or Vocal Resistor)

**Delivery**: Every Wednesday via email.
**What we need**: Weekly StackAdapt campaign-level export (impressions, clicks, conversions, spend by campaign) every Monday.

---

## BEFORE LAUNCH CHECKLIST

### Agency:
- [ ] Both GTM tags installed and published
- [ ] StackAdapt pixel firing confirmed
- [ ] 4 conversion events created with exact names
- [ ] 5 audiences created with exact names
- [ ] `luxy_converted_exclude` applied to ALL 28 campaigns
- [ ] 7 per-archetype whitelists uploaded (one per campaign group)
- [ ] 1 shared blacklist uploaded to all campaigns
- [ ] 7 campaign groups created with correct budgets
- [ ] 28 campaigns created with correct copy, audiences, and click URLs
- [ ] Frequency caps set per archetype
- [ ] Dayparting bid adjustments set per archetype
- [ ] 28 image creatives produced and uploaded
- [ ] All campaigns in DRAFT for joint review

### INFORMATIV:
- [ ] Server deployed and healthy on Railway
- [ ] Neo4j seeded with bilateral edges + cross-category validation data
- [ ] Goal Activation Model deployed and operational
- [ ] Telemetry endpoint accepting data
- [ ] CORS configured for luxyride.com

### Joint:
- [ ] Review all 28 campaigns together
- [ ] Test click from each campaign group (verify URL params flow)
- [ ] Confirm reporting cadence
- [ ] Set all campaigns to ACTIVE

---

*Powered by INFORMATIV bilateral psycholinguistic intelligence — 16,883 bilateral edges, 10 validated archetypes, nonconscious goal activation targeting.*
