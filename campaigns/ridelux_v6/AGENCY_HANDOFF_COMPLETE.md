# INFORMATIV × LUXY Ride — Agency Handoff
## For: Zero Gravity Marketing (Becca Matyasovsky)
## Date: April 14, 2026

---

## SUMMARY

| Item | Value |
|------|-------|
| Launch audiences | 6 |
| Campaign groups | 6 |
| Total campaigns | 18 |
| Weekly budget | $24,000 |
| Daily budget | $3,428 |
| Optimization cadence | Every 48 hours |

---

## STEP-BY-STEP

### 1. Install two GTM tags on luxyride.com
See AGENCY_BRIEF.md for exact code. Both fire on All Pages.

### 2. Create 6 conversion events
See AGENCY_BRIEF.md for exact names.

### 3. Create 5 audiences
See AGENCY_BRIEF.md. CRITICAL: Apply `luxy_converted_exclude` to ALL 18 campaigns.

### 4. Upload domain lists

| Audience | Whitelist File |
|---|---|
| Travel Arrangers | `stackadapt_whitelist_reliable_cooperator.csv` |
| Travel Managers | `stackadapt_whitelist_dependable_loyalist.csv` |
| Home Market | `stackadapt_whitelist_home_market.csv` |
| Event Planners | `stackadapt_whitelist_prevention_planner.csv` |
| Legal | `stackadapt_whitelist_careful_truster.csv` |
| Life Sciences | `stackadapt_whitelist_careful_truster.csv` |

Blacklist (ALL campaigns): `stackadapt_blacklist_upload.csv`

**After uploading each whitelist:** Run a forecast in StackAdapt to check inventory availability. If inventory is insufficient for a whitelist, add keyword fallback targeting as described in AGENCY_BRIEF.md (Section: Domain Targeting Notes). Report results to INFORMATIV.

### 5. Create 6 campaign groups

| # | Name | Daily Budget |
|---|------|---|
| 1 | LUXY — Travel Arrangers (EA) | $960 |
| 2 | LUXY — Travel Managers | $857 |
| 3 | LUXY — Home Market (CT/NYC) | $617 |
| 4 | LUXY — Event Planners | $411 |
| 5 | LUXY — Legal | $343 |
| 6 | LUXY — Life Sciences | $240 |

### 6. Create 18 campaigns

Campaign IDs: EA-T1..T3, TM-T1..T3, HM-T1..T3, EV-T1..T3, LG-T1..T3, LS-T1..T3

Click URL (ALL campaigns):
```
https://luxyride.com/?sapid={SA_POSTBACK_ID}&cid={CAMPAIGN_ID}&crid={CREATIVE_ID}&domain={DOMAIN}&device={DEVICE_TYPE}&ts={TIMESTAMP}
```

### 7. Set frequency caps and dayparting
Per AGENCY_BRIEF.md.

---

## OPTIMIZATION

Every 48 hours, INFORMATIV delivers specific actions. Agency implements within 24 hours.

---

*6 audiences. 18 campaigns. $24K/week concentrated for maximum learning.*
