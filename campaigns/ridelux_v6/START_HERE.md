# START HERE — INFORMATIV × LUXY Ride Campaign Package

Hi Becca,

This folder contains everything you need to set up and launch the LUXY Ride pilot campaign in StackAdapt. Here's what each file is and when you'll need it.

---

## Step 1: Read the Brief

**`AGENCY_BRIEF.md`** — This is the master document. It explains:
- The 10 psychological archetypes (7 to target, 3 to suppress)
- All 28 campaigns with complete ad copy (headlines, body, CTAs)
- How to install the two GTM tags (StackAdapt pixel + INFORMATIV telemetry)
- How to create conversion events and audiences in StackAdapt
- Budget allocation, frequency caps, dayparting, and bidding guidance
- Image art direction for each archetype
- The before-launch checklist

**Read this first. Everything else supports it.**

---

## Step 2: Follow the Setup Guide

**`AGENCY_HANDOFF_COMPLETE.md`** — Step-by-step StackAdapt setup instructions. Use this alongside the brief as you build the campaigns. It walks through:
1. Tag installation
2. Conversion events
3. Audiences
4. Domain list uploads
5. Campaign group creation
6. Campaign creation
7. Frequency caps and dayparting

---

## Step 3: Upload Domain Lists

Each of the 7 campaign groups gets its own Site Inclusion List. Upload the matching CSV:

| Campaign Group | File to Upload |
|---|---|
| LUXY — Trusting Loyalist | `stackadapt_whitelist_trusting_loyalist.csv` |
| LUXY — Reliable Cooperator | `stackadapt_whitelist_reliable_cooperator.csv` |
| LUXY — Careful Truster | `stackadapt_whitelist_careful_truster.csv` |
| LUXY — Explorer | `stackadapt_whitelist_explorer.csv` |
| LUXY — Prevention Planner | `stackadapt_whitelist_prevention_planner.csv` |
| LUXY — Dependable Loyalist | `stackadapt_whitelist_dependable_loyalist.csv` |
| LUXY — Consensus Seeker | `stackadapt_whitelist_consensus_seeker.csv` |

**Shared blacklist** — upload to ALL campaigns:
- `stackadapt_blacklist_upload.csv`

---

## Step 4: Create Campaigns + Creatives

The ad copy for all 28 campaigns is in the brief (Section 6). For a machine-readable version:

**`luxy_ride_complete_creatives.json`** — All 28 campaigns with headline, body, CTA, mechanism, archetype, budget, and optimization goal per campaign.

---

## Step 5: Produce Image Creatives

**`IMAGE_CREATIVE_BRIEFS.md`** — Art direction for each archetype: visual style, color palette, mood, and required sizes (1200x627, 600x600, 800x600).

---

## Reference Files (not needed for setup)

- `domain_archetype_mapping.json` — Technical reference showing why each domain was assigned to each archetype (crossover scores). Not needed for StackAdapt setup.

---

## Questions?

Reach out to the INFORMATIV team. We'll provide:
- The exact INFORMATIV server URL for the telemetry tag (before GTM publish)
- Weekly intelligence reports every Wednesday
- Recommendations for budget shifts, creative changes, and targeting adjustments

---

## Quick Reference

| Item | Value |
|---|---|
| Campaign groups | 7 |
| Total campaigns | 28 |
| Total creatives needed | 28 (one per campaign) |
| Daily budget | $240.75 |
| Monthly budget | $7,222.50 |
| Whitelist files | 7 (one per group) |
| Blacklist file | 1 (shared) |
| Image sizes | 1200x627, 600x600, 800x600 |
