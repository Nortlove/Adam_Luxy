# INFORMATIV × LUXY Ride — Agency Handoff
## For: Zero Gravity Marketing (Becca Matyasovsky)
## Date: April 14, 2026

---

## SUMMARY

| Item | Value |
|------|-------|
| Audiences | 11 (10 demand-side + 1 supply-side) |
| Campaign groups | 11 |
| Total campaigns | 28 |
| Weekly budget | $24,000 |
| Daily budget | $3,428 |
| Optimization cadence | Every 48 hours |

---

## STEP-BY-STEP SETUP

### 1. Install two GTM tags on luxyride.com
See AGENCY_BRIEF.md for exact tag code. Both fire on All Pages.

### 2. Create 6 conversion events
See AGENCY_BRIEF.md for exact names and configuration.

### 3. Create 5 audiences
See AGENCY_BRIEF.md. CRITICAL: Apply `luxy_converted_exclude` to ALL 28 campaigns.

### 4. Upload domain lists
Each audience group gets its own Site Inclusion List. See AGENCY_BRIEF.md for the mapping table. Upload shared blacklist to all campaigns.

### 5. Create 11 campaign groups

| # | Name | Daily Budget |
|---|------|---|
| 1 | LUXY — Travel Arrangers (EA) | $754 |
| 2 | LUXY — Travel Managers | $686 |
| 3 | LUXY — Home Market (CT/NYC) | $514 |
| 4 | LUXY — Event Planners | $343 |
| 5 | LUXY — Legal | $274 |
| 6 | LUXY — Life Sciences | $240 |
| 7 | LUXY — Financial Dealmakers | $206 |
| 8 | LUXY — Supply Partners * | $171 |
| 9 | LUXY — Private Aviation | $103 |
| 10 | LUXY — CFO / T&E | $69 |
| 11 | LUXY — Hotel B2B | $69 |

\* Supply Partners: SEPARATE line item, different landing page, different conversion events.

### 6. Create 28 campaigns
See AGENCY_BRIEF.md for complete copy per campaign. Campaign IDs:
- EA-T1 through EA-T3
- TM-T1 through TM-T3
- HM-T1 through HM-T3
- EV-T1 through EV-T3
- LG-T1 through LG-T3
- LS-T1 through LS-T3
- FI-T1 through FI-T2
- SP-T1 through SP-T2
- PA-T1 through PA-T2
- CF-T1 through CF-T2
- HT-T1 through HT-T2

Click URL for ALL campaigns:
```
https://luxyride.com/?sapid={SA_POSTBACK_ID}&cid={CAMPAIGN_ID}&crid={CREATIVE_ID}&domain={DOMAIN}&device={DEVICE_TYPE}&ts={TIMESTAMP}
```

### 7. Set frequency caps and dayparting
See AGENCY_BRIEF.md for per-audience settings.

---

## OPTIMIZATION

Every 48 hours, INFORMATIV delivers a report with specific actions:
- Budget shifts between audiences (with dollar amounts)
- Domain additions/removals (with performance data)
- Creative refresh recommendations
- User suppression lists

Agency implements within 24 hours.

---

*11 audiences. 28 campaigns. Every domain verified. Every creative matched to context.*
