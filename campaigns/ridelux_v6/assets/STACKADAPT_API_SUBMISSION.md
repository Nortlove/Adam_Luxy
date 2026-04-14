# StackAdapt API Submission — Ready-to-Execute
## Complete GraphQL mutations for campaign setup

Replace `<<ADVERTISER_ID>>`, `<<API_TOKEN>>`, and pixel IDs before executing.

---

## 1. Authentication Header

All requests:
```
POST https://api.stackadapt.com/graphql
Authorization: Bearer <<API_TOKEN>>
Content-Type: application/json
```

---

## 2. Create Campaign Groups (3)

### Careful Truster Group
```graphql
mutation {
  createCampaignGroup(input: {
    advertiserId: "<<ADVERTISER_ID>>"
    name: "LUXY Ride — Careful Truster"
    budget: { daily: 58.50, currency: USD }
    startDate: "2026-03-31"
    endDate: "2026-04-29"
    status: DRAFT
  }) {
    id
    name
  }
}
```

### Status Seeker Group
```graphql
mutation {
  createCampaignGroup(input: {
    advertiserId: "<<ADVERTISER_ID>>"
    name: "LUXY Ride — Status Seeker"
    budget: { daily: 84.83, currency: USD }
    startDate: "2026-03-31"
    endDate: "2026-04-29"
    status: DRAFT
  }) {
    id
    name
  }
}
```

### Easy Decider Group
```graphql
mutation {
  createCampaignGroup(input: {
    advertiserId: "<<ADVERTISER_ID>>"
    name: "LUXY Ride — Easy Decider"
    budget: { daily: 81.67, currency: USD }
    startDate: "2026-03-31"
    endDate: "2026-04-29"
    status: DRAFT
  }) {
    id
    name
  }
}
```

---

## 3. Campaign Setup Per Touch

For each of the 15 campaigns, create with these settings:

| Group | Campaign Name | Daily Budget | Optimization |
|-------|-------------|-------------|-------------|
| CT | LUXY — Careful Truster — Touch 1 | $11.70 | Clicks |
| CT | LUXY — Careful Truster — Touch 2 | $11.70 | Clicks |
| CT | LUXY — Careful Truster — Touch 3 | $11.70 | Conversions |
| CT | LUXY — Careful Truster — Touch 4 | $11.70 | Conversions |
| CT | LUXY — Careful Truster — Touch 5 | $11.70 | Conversions |
| SS | LUXY — Status Seeker — Touch 1 | $16.97 | Clicks |
| SS | LUXY — Status Seeker — Touch 2 | $16.97 | Clicks |
| SS | LUXY — Status Seeker — Touch 3 | $16.97 | Conversions |
| SS | LUXY — Status Seeker — Touch 4 | $16.97 | Conversions |
| SS | LUXY — Status Seeker — Touch 5 | $16.97 | Conversions |
| ED | LUXY — Easy Decider — Touch 1 | $16.33 | Clicks |
| ED | LUXY — Easy Decider — Touch 2 | $16.33 | Clicks |
| ED | LUXY — Easy Decider — Touch 3 | $16.33 | Conversions |
| ED | LUXY — Easy Decider — Touch 4 | $16.33 | Conversions |
| ED | LUXY — Easy Decider — Touch 5 | $16.33 | Conversions |

Touch 1-2: Optimize for clicks (awareness/engagement)
Touch 3-5: Optimize for conversions (booking_complete event)

### Example Campaign Creation
```graphql
mutation {
  createCampaign(input: {
    campaignGroupId: "<<CT_GROUP_ID>>"
    name: "LUXY — Careful Truster — Touch 1"
    campaignType: NATIVE
    budget: { daily: 11.70, currency: USD }
    startDate: "2026-03-31"
    endDate: "2026-04-29"
    optimization: CLICKS
    frequencyCap: { impressions: 2, period: DAY }
    status: DRAFT
  }) {
    id
    name
  }
}
```

---

## 4. Audience Targeting

Apply to ALL 15 campaigns:
- **Include**: All Site Visitors (retargeting audience from pixel)
- **Exclude**: Converted audience (booking_complete event, 90-day)

Sequential touch targeting:
- Touch 2 campaigns: Exclude users who engaged with Touch 1
- Touch 3 campaigns: Exclude users who engaged with Touch 2
- (etc.)

---

## 5. Domain Targeting

Upload via StackAdapt UI:
- Whitelist: `luxy_ride_domain_whitelist.csv` (29 domains)
- Blacklist: `luxy_ride_domain_blacklist.csv` (5 domains)

Apply whitelist to ALL 15 campaigns.

---

## 6. Frequency Caps (per Campaign Group)

| Group | Max/Day | Max/Week | Min Hours Between |
|-------|---------|----------|--------------------|
| Careful Truster | 2 | 7 | 8 |
| Status Seeker | 2 | 4 | 16 |
| Easy Decider | 3 | 6 | 6 |

---

## 7. Dayparting (per Campaign Group)

Apply via StackAdapt scheduling:

**Careful Truster**: Peak 7-9AM, 5-7PM weekdays (commute hours)
**Status Seeker**: Peak 7-11PM weekdays, 9AM-2PM weekends (leisure)
**Easy Decider**: Peak 12-2PM, 7-11PM weekdays (micro-break + evening scroll)

Full schedules in `luxy_ride_dayparting.json`.

---

## 8. Creative Upload (per Campaign)

Each campaign gets ONE creative (no rotation):

| Campaign | Headline | Body | CTA |
|----------|----------|------|-----|
| CT T1 | I swore I'd never use a car service again | Sarah, a Fortune 500 exec, shares her struggle... | Her story |
| CT T2 | We've All Heard The Horror Stories | 73% of luxury transport complaints stem from... | See proof |
| CT T3 | 47,000 executives trust LUXY with their reputation | Independent audit: 99.7% on-time arrival rate... | See proof |
| CT T4 | I Was Wrong About Premium Car Services | CFO Sarah M.: "Thought they'd overcharge..." | See proof |
| CT T5 | 847,000+ rides completed. Zero security incidents. | We know you've heard stories. Here's ours... | Book now |
| SS T1 | You've earned success. Where's the service? | Built your empire through precision and excellence... | See More |
| SS T2 | I thought luxury cars were just showing off | CEO Sarah M. felt the same way... | Her story |
| SS T3 | You've built this life. You deserve this ride. | Fortune 500 CEOs choose LUXY... | Book now |
| SS T4 | Finally, transportation that gets me | CFO Sarah K.: "LUXY drivers understand..." | Book now |
| SS T5 | You've Joined the Top 1% Who Choose Differently | 847,000 executives trust LUXY... | Book Now |
| ED T1 | Another delay. Another missed opportunity. | While you're circling blocks hunting parking... | See How |
| ED T2 | Your driver is waiting. You're still in line. | When your flight's delayed and ride apps surge... | See Option |
| ED T3 | Your driver is already in your area | Just check if we serve your route... | See rates |
| ED T4 | Your driver is already en route | Open the app. Your usual pickup location... | Open App |
| ED T5 | 50,000+ executives choose LUXY for airport runs | Your colleagues already know... | Save mine |

Full copy in `luxy_ride_creatives.json`.
Image specs in `IMAGE_CREATIVE_BRIEFS.md`.

---

## 9. Conversion Tracking

Create 4 events in StackAdapt Pixels:

| Event | Trigger | Window | Revenue |
|-------|---------|--------|---------|
| site_visit | page_url contains luxyride.com | 30 day | No |
| pricing_view | page_url contains /pricing or /rates | 14 day | No |
| booking_start | Custom JS event | 7 day | No |
| booking_complete | Custom JS event | 7 day | **Yes** |

Set `booking_complete` as PRIMARY conversion for optimization.

---

## 10. Webhook Configuration

Configure StackAdapt to send conversion events to:
```
POST https://your-informativ-server.com/api/v1/stackadapt/webhook
```

This enables the 20-path learning cascade. Without the webhook, the system cannot learn.

---

## Pre-Launch Verification

```bash
# On your INFORMATIV server:
python3 scripts/validate_campaign_config.py
# Must show: Status: READY

# Start the server:
./scripts/start_pilot.sh
```

---

## Files Reference

| File | What to Do |
|------|-----------|
| `luxy_ride_campaign_config.json` | Fill 7 placeholder IDs, reference for all settings |
| `luxy_ride_audiences.json` | Create audiences in StackAdapt |
| `luxy_ride_creatives.json` | Upload copy for each campaign |
| `luxy_ride_domain_whitelist.csv` | Upload as inclusion list |
| `luxy_ride_domain_blacklist.csv` | Upload as exclusion list |
| `luxy_ride_frequency_caps.json` | Apply per campaign group |
| `luxy_ride_dayparting.json` | Apply per campaign group |
| `luxy_ride_measurement.json` | Conversion pixel setup |
| `luxy_ride_retargeting_rules.json` | Sequential touch logic |
| `luxy_ride_site_profiles.json` | Internal reference (psychological profiles) |
| `IMAGE_CREATIVE_BRIEFS.md` | Image production briefs |
| `STACKADAPT_SETUP_CHECKLIST.md` | Step-by-step checklist |
| `STACKADAPT_IMPLEMENTATION_GUIDE.md` | Detailed technical guide |
