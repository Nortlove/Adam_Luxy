# LUXY Ride — StackAdapt Setup Checklist
## Complete operational checklist for campaign launch
## Generated: March 28, 2026

---

## Pre-Setup Requirements

- [ ] StackAdapt advertiser account created (request via sales@stackadapt.com)
- [ ] GraphQL API key obtained (separate from REST API key)
- [ ] LUXY Ride website (luxyride.com) accessible for pixel installation
- [ ] Creative assets produced (images per format specs in luxy_ride_creatives.json)
- [ ] INFORMATIV production server ready (Neo4j + Redis + API running)

---

## Step 1: StackAdapt Account IDs

After creating the account, record these IDs and update `luxy_ride_campaign_config.json`:

| Field | Where to Find | Config Path |
|-------|--------------|-------------|
| Advertiser ID | StackAdapt UI → Advertiser Settings | `meta.stackadapt_account.advertiser_id` |
| GraphQL API Key | Request from StackAdapt team | `meta.stackadapt_account.api_key` |
| Universal Pixel ID | StackAdapt UI → Pixels (format: sa-XXXXXXXX) | `meta.stackadapt_account.universal_pixel_id` |

---

## Step 2: Universal Pixel Installation

Install on ALL pages of luxyride.com:

```html
<script>
!function(s,a,e,v,n,t,z){if(s.saq)return;n=s.saq=function(){
n.callMethod?n.callMethod.apply(n,arguments):n.queue.push(arguments)};
if(!s._saq)s._saq=n;n.push=n;n.loaded=!0;n.version='1.0';
n.queue=[];t=a.createElement(e);t.async=!0;t.src=v;
z=a.getElementsByTagName(e)[0];z.parentNode.insertBefore(t,z)}
(window,document,'script','https://tags.srv.stackadapt.com/events.js');
saq('ts', 'YOUR_UNIVERSAL_PIXEL_ID');
</script>
```

---

## Step 3: Conversion Events (4 pixels)

Create these in StackAdapt UI → Pixels → Conversion Events:

| Event Name | Trigger | Attribution Window | Revenue | Primary? |
|-----------|---------|-------------------|---------|----------|
| `site_visit` | page_url contains luxyride.com | 30 days | No | No |
| `pricing_view` | page_url contains /pricing OR /rates | 14 days | No | No |
| `booking_start` | Custom JS event (see below) | 7 days | No | No |
| `booking_complete` | Custom JS event (see below) | 7 days | Yes | **Yes** |

Add to LUXY Ride booking pages:
```javascript
// On booking form start
saq('conv', 'BOOKING_START_EVENT_ID');

// On booking confirmation
saq('conv', 'BOOKING_COMPLETE_EVENT_ID', {
  'revenue': bookingTotal,
  'order_id': bookingId,
  'currency': 'USD'
});
```

Record Pixel IDs → update `luxy_ride_campaign_config.json` measurement section.

---

## Step 4: Audiences (10 pools)

Create in StackAdapt UI → Audiences:

| # | Name | Type | Rule |
|---|------|------|------|
| 1 | LUXY Ride — All Site Visitors | Retargeting | page_url contains luxyride.com, 30-day lookback |
| 2 | LUXY Ride — Pricing Visitors | Retargeting | page_url contains /pricing OR /rates, 14-day |
| 3 | LUXY Ride — Booking Started | Retargeting | booking_start event AND NOT booking_complete, 7-day |
| 4 | LUXY Ride — Multiple Visits 3+ | Retargeting | frequency ≥ 3, 14-day |
| 5 | LUXY Ride — Converted (EXCLUDE) | Exclusion | booking_complete event, 90-day |
| 6 | Touch 1 Pool | Sequential | All site visitors, no prior exclusion |
| 7 | Touch 2 Pool | Sequential | Touch 1 served AND NOT clicked |
| 8 | Touch 3 Pool | Sequential | Touch 2 served AND NOT clicked |
| 9 | Touch 4 Pool | Sequential | Touch 3 served AND NOT clicked |
| 10 | Touch 5 Pool | Sequential | Touch 4 served AND NOT clicked |

**CRITICAL**: Apply "Converted (EXCLUDE)" to ALL 15 campaigns.

**NOTE**: Touch pools are shared across all 3 archetypes. Each campaign uses archetype-specific creative — StackAdapt's ML optimizes delivery to responsive users.

---

## Step 5: Domain Lists

Upload via StackAdapt UI → Inventory:

- **Whitelist**: Upload `luxy_ride_domain_whitelist.csv` (29 domains)
- **Blacklist**: Upload `luxy_ride_domain_blacklist.csv` (5 domains)

---

## Step 6: Campaign Groups (3)

| Group | Archetype | Daily Budget | Conversion Rate |
|-------|-----------|-------------|----------------|
| LUXY Ride — Careful Truster | careful_truster | $58.50 | 65.0% |
| LUXY Ride — Status Seeker | status_seeker | $84.83 | 94.5% |
| LUXY Ride — Easy Decider | easy_decider | $81.67 | 90.9% |

Total daily: $225.00

---

## Step 7: Campaigns (15)

Create 5 campaigns per group. Each campaign:
- Targets its touch position's audience pool
- Excludes the Converted audience
- Uses its specific creative (one creative per campaign — no rotation)
- Uses per-archetype frequency caps
- Uses per-archetype dayparting

See `luxy_ride_campaign_config.json` for complete per-campaign settings.

---

## Step 8: Frequency Caps (per archetype)

| Archetype | Max/Day | Max/Week | Min Hours Between |
|-----------|---------|----------|--------------------|
| Careful Truster | 2 | 7 | 8 |
| Status Seeker | 2 | 4 | 16 |
| Easy Decider | 3 | 6 | 6 |

---

## Step 9: Dayparting (per archetype)

See `luxy_ride_dayparting.json` for full schedules. Summary:

| Archetype | Peak Hours | Rationale |
|-----------|-----------|-----------|
| Careful Truster | 7-9AM, 5-7PM weekdays | Corporate commute |
| Status Seeker | 7-11PM weekdays, 9AM-2PM weekends | Leisure browsing |
| Easy Decider | 12-2PM, 7-11PM weekdays, all weekend | Micro-break impulse |

---

## Step 10: Creative Upload

15 creatives (see `luxy_ride_creatives.json`). Each has:
- Headline (max 50 chars)
- Body (max 120 chars)
- CTA (max 10 chars)
- Image assets needed per format spec

**Native format**: 1200x627, 600x600, 800x600 (JPG/PNG, max 2MB)

**NOTE**: Current copy is placeholder. Run `scripts/generate_luxy_copy.py` with Neo4j + Claude API for bilateral-intelligence-backed copy before launch.

---

## Step 11: INFORMATIV Server Setup

| Component | Command/Action | Required? |
|-----------|---------------|-----------|
| Neo4j | Start with LUXY Ride data (3,103 bilateral edges) | Yes |
| Redis | Start on default port | Yes |
| API Keys | `export ADAM_API_KEYS=your-pilot-key-here` | Yes |
| Gradient Fields | `python3 scripts/compute_gradient_fields.py` | Yes |
| Copy Generation | `ANTHROPIC_API_KEY=sk-... python3 scripts/generate_luxy_copy.py` | Recommended |
| Validation | `python3 scripts/validate_campaign_config.py` | Yes (must pass) |

---

## Step 12: Pre-Launch Validation

```bash
# Validate all config placeholders are filled
python3 scripts/validate_campaign_config.py

# Expected output: "Status: READY" (no ERRORS)
```

---

## Step 13: Launch

- [ ] All campaigns set to DRAFT in StackAdapt
- [ ] Review all settings one final time
- [ ] Change all 15 campaigns to ACTIVE
- [ ] Monitor first 24 hours for delivery issues
- [ ] Check INFORMATIV metrics at `/metrics` endpoint

---

## Files in This Package

| File | Purpose |
|------|---------|
| `STACKADAPT_IMPLEMENTATION_GUIDE.md` | Detailed technical implementation guide |
| `STACKADAPT_SETUP_CHECKLIST.md` | This checklist |
| `luxy_ride_campaign_config.json` | Master campaign config (15 campaigns, budgets, targeting) |
| `luxy_ride_audiences.json` | 10 audience pool definitions |
| `luxy_ride_creatives.json` | 15 creative specs with copy + format requirements |
| `luxy_ride_domain_whitelist.csv` | 29 approved domains (CT + SS + ED coverage) |
| `luxy_ride_domain_blacklist.csv` | 5 blocked domains |
| `luxy_ride_site_profiles.json` | Psychological profiles for all 29 domains |
| `luxy_ride_retargeting_rules.json` | Sequential touch logic + mechanism sequences |
| `luxy_ride_frequency_caps.json` | Per-archetype frequency caps |
| `luxy_ride_dayparting.json` | Per-archetype dayparting schedules |
| `luxy_ride_measurement.json` | Conversion pixels + KPI definitions |

---

## Post-Launch Monitoring

### Week 1
- Monitor per-touch conversion rates (hypothesis: each touch should convert higher than previous)
- Check StackAdapt delivery: are all 15 campaigns serving?
- Verify INFORMATIV resonance learning is accumulating (check `/metrics`)
- Review page gradient accumulation count

### Week 2
- First page gradient field computation (daily task runs at 4 AM UTC)
- Copy effectiveness learner begins producing non-default recommendations
- Run similarity index expansion — are new domains being discovered?

### Week 3
- First copy evolution cycle (Sunday 5 AM UTC)
- Review which copy variants underperform — regenerate with learned params
- Assess congruence vs contrast strategy effectiveness per archetype

### Week 4
- Final pilot assessment
- Compare predicted vs actual conversion rates per archetype
- Document learned insights for Phase 2 campaign expansion
