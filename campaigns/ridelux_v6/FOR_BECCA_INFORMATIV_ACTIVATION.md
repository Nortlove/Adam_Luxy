# Activating the INFORMATIV Campaign — Step by Step

**For:** Becca (ZGM)
**Campaign:** ZGM-Display-Prospecting-Informativ (currently in draft)
**Date:** April 17, 2026

---

## What INFORMATIV Does (30-Second Version)

We analyzed 1,492 luxury transportation purchase events across 27
psychological dimensions. From that analysis, we know which
**persuasion approach** works best for each buyer type and on which
**types of websites**. The creative specs below aren't guesses — they're
derived from actual purchase psychology.

---

## Step 1: Create Creative Variants

In the draft campaign `ZGM-Display-Prospecting-Informativ`, create
the following ad variants. Each variant uses a different psychological
approach — StackAdapt's optimization will test them and converge on
the winner.

### Variant A — Authority (Predicted Winner)
| Field | Value |
|-------|-------|
| Name | `INFORMATIV-Authority` |
| Headline | The executive standard in ground transportation |
| Body | Trusted by Fortune 500 travel managers. On-time guarantee backed by real-time flight tracking. |
| CTA | See why professionals choose LUXY |
| Brand Name | LUXY Ride |
| Landing URL | https://luxyride.com |

### Variant B — Social Proof
| Field | Value |
|-------|-------|
| Name | `INFORMATIV-SocialProof` |
| Headline | 10,000+ executive travelers trust LUXY |
| Body | Join the professionals who demand reliability and discretion in every ride. |
| CTA | Join the professionals |
| Brand Name | LUXY Ride |
| Landing URL | https://luxyride.com |

### Variant C — Cognitive Ease
| Field | Value |
|-------|-------|
| Name | `INFORMATIV-CogEase` |
| Headline | Premium transport. One tap. |
| Body | No surge pricing. No uncertainty. Just seamless professional transportation. |
| CTA | Book now |
| Brand Name | LUXY Ride |
| Landing URL | https://luxyride.com |

**Image assets:** Use the existing LUXY Ride creative images from
the other campaigns. The mechanism is in the COPY, not the image.

---

## Step 2: Set Domain Targeting

Apply domain whitelist to this campaign. These are websites where
our target buyer's psychological goals are activated — business
publications where competence and status goals are primed.

**Upload as domain whitelist (copy into StackAdapt):**

```
bloomberg.com
forbes.com
wsj.com
hbr.org
ft.com
cnbc.com
businessinsider.com
fortune.com
businesstravelnews.com
skift.com
travelweekly.com
phocuswire.com
wired.com
techcrunch.com
```

The blacklist file `stackadapt_blacklist_upload.csv` (already shared)
should also be applied.

---

## Step 3: Campaign Settings

| Setting | Value | Why |
|---------|-------|-----|
| Budget | $33/day | Based on expected value modeling across 336 cells |
| Goal Type | Conversions | We're optimizing for bookings, not clicks |
| Optimize Creative | ON | Let StackAdapt test our 3 variants and find the winner |
| Frequency Cap | 5 per 24 hours | Our research shows diminishing returns after 5 exposures |
| Campaign Group | Corporate Executives | Primary target archetype |

---

## Step 4: Conversion Tracking

### A. If the Universal Pixel is already on luxyride.com:
Make sure the booking confirmation page fires a conversion event
with revenue:

```javascript
saq('conv', 'luxy_booking_confirmed', {
    'revenue': ORDER_TOTAL
});
```

### B. Server-to-Server Postback (for learning loop):
This sends conversion data to our intelligence server so the system
learns and improves over time.

| Setting | Value |
|---------|-------|
| Postback URL | `https://focused-encouragement-production.up.railway.app/api/v1/stackadapt/webhook/conversion` |
| Method | POST |
| Signature Header | `X-Informativ-Signature` |
| Shared Secret | `informativ-stackadapt-hmac-2026-pilot` |

---

## Step 5: Activate

Once Steps 1-4 are configured, change the campaign status from
Draft to Active.

---

## Step 6 (Optional): Install INFORMATIV Telemetry

For enhanced learning, install our JavaScript tag on luxyride.com.
This measures processing depth (did the user actually read the page?)
which makes the learning system dramatically more accurate.

Add to every page on luxyride.com, before `</body>`:

```html
<script src="https://focused-encouragement-production.up.railway.app/static/telemetry/informativ.js"
        data-endpoint="https://focused-encouragement-production.up.railway.app"
        async></script>
```

---

## What Happens After Launch

1. **Week 1:** StackAdapt tests all 3 variants and starts converging on the winner. Our server receives conversion data and begins learning.

2. **Week 2+:** We provide a weekly intelligence brief with:
   - Which variant is winning and why
   - Recommendations for new variants based on what we learned
   - Domain bid adjustments based on which pages drive the most conversions
   - Performance comparison: INFORMATIV campaign vs standard campaigns

3. **Monthly:** We provide updated creative copy informed by the learning loop, plus a full psychological analysis of what's working and what isn't.

---

## Files Included

| File | Purpose |
|------|---------|
| This document | Step-by-step activation guide |
| `stackadapt_blacklist_upload.csv` | Domain blacklist (upload to StackAdapt) |
| `stackadapt_whitelist_careful_truster.csv` | Domain whitelist for Corporate Executive targeting |
| `LUXY_PIXEL_INSTALLATION_GUIDE.md` | Detailed pixel + telemetry installation for LUXY's web developer |
| `BECCA_CAMPAIGN_SETUP_GUIDE.md` | Full reference with all 8 archetype specs (for future campaign expansion) |

---

## Questions?

Chris Nocera: CNocera@rebelliongroup.com

---

## One Request

**Please request write permissions on the GraphQL API key** from your
StackAdapt account manager. The current key (ID: 194833) has read
access but not write access. With write permissions, we can automate
the weekly campaign evolution — creating new variants, adjusting bids,
and pausing underperformers based on what our learning systems discover.

Without write access, we'll provide the recommendations and you
apply them manually in the StackAdapt UI. Both work — automation
is just faster.
