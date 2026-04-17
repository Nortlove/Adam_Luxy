# LUXY Ride Campaign Setup Guide — For Becca

**Last Updated:** April 16, 2026
**Server Status:** LIVE and verified (33/33 tests passing)

---

## Quick Reference

| Item | Value |
|------|-------|
| **Server URL** | `https://focused-encouragement-production.up.railway.app` |
| **API Docs** | `https://focused-encouragement-production.up.railway.app/docs` |
| **API Key** | `informativ-pilot-2026-luxy` |
| **API Key Header** | `X-API-Key` |
| **Webhook URL** | `https://focused-encouragement-production.up.railway.app/api/v1/stackadapt/webhook/conversion` |
| **Webhook Signature Header** | `X-Informativ-Signature` |
| **Webhook Secret** | `informativ-stackadapt-hmac-2026-pilot` |

---

## How This Works (Simple Version)

INFORMATIV analyzes 937 million product reviews to understand **why** people
buy luxury transportation — not just demographics, but the actual
psychological drivers behind purchase decisions.

For each of the 8 buyer types below, we've identified:
- Which **persuasion approach** works best (authority, social proof, etc.)
- How to **frame** the message (gain vs. loss, abstract vs. concrete)
- What **tone** to use
- What **headlines and CTAs** to deploy
- Which **websites** to target (where these buyers are in the right mindset)

All of this comes from analyzing 1,492 real luxury transportation purchase
events across 27 psychological dimensions.

---

## The 8 Buyer Segments

### 1. Corporate Executive → Archetype: Careful Truster

**Who they are:** C-suite and senior executives who need reliable ground
transportation for business travel. Risk-averse, evidence-seeking,
values credibility over flash.

**What works:** Authority messaging with gain framing. Abstract construal
(big-picture benefits, not granular features). Professional, authoritative tone.

| Setting | Value |
|---------|-------|
| Segment ID | `informativ_corporate_executive_social_proof_luxury_transportation_t1` |
| Primary Mechanism | Authority |
| Framing | Gain |
| Tone | Authoritative |
| Headline Strategy | Expert endorsement |
| CTA Style | Professional recommendation |
| Example Headline | "The executive standard in ground transportation" |
| Example CTA | "See why Fortune 500 travel managers choose LUXY" |

**Targeting:** Business publications, productivity tools, executive
education, financial news, corporate travel content.

---

### 2. Airport Anxiety → Archetype: Careful Truster

**Who they are:** Travelers anxious about airport logistics — flight
timing, traffic, reliability. Need guarantees and certainty.

| Setting | Value |
|---------|-------|
| Segment ID | `informativ_airport_anxiety_authority_luxury_transportation_t1` |
| Primary Mechanism | Authority |
| Framing | Loss (prevent the bad outcome) |
| Tone | Reassuring, authoritative |
| Example Headline | "Never miss a flight. Guaranteed." |
| Example CTA | "Book your guaranteed airport transfer" |

**Targeting:** Travel planning, flight booking, airport guides, travel
anxiety content, business travel forums.

---

### 3. Status Seeker → Archetype: Status Seeker

**Who they are:** Image-conscious buyers who see luxury transportation
as a status signal. Responsive to aspirational messaging and social proof.

| Setting | Value |
|---------|-------|
| Segment ID | `informativ_status_seeker_scarcity_luxury_transportation_t1` |
| Primary Mechanism | Social proof + Scarcity |
| Framing | Gain (aspiration) |
| Tone | Premium, exclusive |
| Example Headline | "The ride that says you've arrived" |
| Example CTA | "Join the members who demand excellence" |

**Targeting:** Luxury lifestyle, premium brands, fashion, high-end
real estate, luxury travel editorial.

---

### 4. Special Occasion → Archetype: Status Seeker

**Who they are:** Planning transportation for weddings, anniversaries,
special events. Want memorable, impressive experience.

| Setting | Value |
|---------|-------|
| Segment ID | `informativ_special_occasion_liking_luxury_transportation_t1` |
| Primary Mechanism | Liking |
| Framing | Gain |
| Tone | Warm, celebratory |
| Example Headline | "Make your special day unforgettable — from the first ride" |
| Example CTA | "Plan your event transportation" |

**Targeting:** Wedding planning, event venues, celebration content,
anniversary gift guides.

---

### 5. Easy Decider → Archetype: Easy Decider

**Who they are:** Low-deliberation buyers who want a fast, frictionless
booking experience. Don't want to think hard about the decision.

| Setting | Value |
|---------|-------|
| Segment ID | `informativ_easy_decider_cognitive_ease_luxury_transportation_t1` |
| Primary Mechanism | Cognitive ease |
| Framing | Gain |
| Tone | Simple, direct |
| Example Headline | "Book in 30 seconds. Ride in style." |
| Example CTA | "One tap. Done." |

**Targeting:** Productivity content, time-saving tools, convenience-
focused lifestyle, mobile-first placement.

---

### 6. First Timer → Archetype: Easy Decider

**Who they are:** Never used a luxury car service before. Curious but
uncertain. Need low-risk entry point.

| Setting | Value |
|---------|-------|
| Segment ID | `informativ_first_timer_curiosity_luxury_transportation_t1` |
| Primary Mechanism | Curiosity |
| Framing | Gain |
| Tone | Inviting, low-pressure |
| Example Headline | "Curious what a private car service is actually like?" |
| Example CTA | "Try your first ride — see the difference" |

**Targeting:** "Best of" lists, comparison content, new experience
content, lifestyle upgrade articles.

---

### 7. Repeat Loyal → Archetype: Easy Decider

**Who they are:** Existing customers who've used LUXY or similar services
before. Value consistency and relationship.

| Setting | Value |
|---------|-------|
| Segment ID | `informativ_repeat_loyal_commitment_luxury_transportation_t1` |
| Primary Mechanism | Commitment |
| Framing | Gain |
| Tone | Familiar, appreciative |
| Example Headline | "Welcome back. Your ride is ready." |
| Example CTA | "Book your usual" |

**Targeting:** Brand loyalty content, rewards programs, travel management
tools, repeat booking platforms.

---

### 8. Skeptical Analyst → Archetype: Prevention Planner

**Who they are:** Data-driven decision makers who research extensively
before purchasing. Want evidence, comparisons, ROI justification.

| Setting | Value |
|---------|-------|
| Segment ID | `informativ_careful_truster_authority_luxury_transportation_t1` |
| Primary Mechanism | Authority |
| Framing | Mixed (gain + loss prevention) |
| Tone | Evidence-based, analytical |
| Example Headline | "Why companies switching to LUXY save 23% on ground transport" |
| Example CTA | "See the data" |

**Targeting:** Business analytics, ROI calculators, procurement content,
corporate travel management.

---

## Setting Up the Webhook (One-Time)

The webhook is how LUXY Ride conversion events get sent back to our
server so the system can learn and improve over time. This is the
"learning loop" — every conversion makes the next recommendation smarter.

### In StackAdapt:

1. Go to **Tracking & Attribution** settings
2. Add a **Server-to-Server Conversion Pixel** (or postback URL)
3. Set the URL to:
   ```
   https://focused-encouragement-production.up.railway.app/api/v1/stackadapt/webhook/conversion
   ```
4. Set the signature header to `X-Informativ-Signature`
5. Set the shared secret to: `informativ-stackadapt-hmac-2026-pilot`
6. Include these fields in the postback:
   - `event_id` (unique event identifier)
   - `event_type` = "conversion"
   - `segment_id` (which segment the user was in)
   - `uid` (buyer identifier)
   - `url` (the page where conversion happened)
   - In `event_args`: include `decision_id` if available, and `revenue`

---

## Getting Real-Time Creative Intelligence (Optional — Advanced)

If you want to get LIVE creative recommendations from our server
(instead of using the pre-built specs above), you can call our API:

```
POST https://focused-encouragement-production.up.railway.app/api/v1/stackadapt/creative-intelligence

Headers:
  Content-Type: application/json
  X-API-Key: informativ-pilot-2026-luxy

Body:
{
    "segment_id": "informativ_careful_truster_authority_luxury_transportation_t1",
    "product_category": "luxury_transportation",
    "page_url": "https://example.com/article",
    "device_type": "desktop",
    "time_of_day": 14
}
```

The response includes: primary mechanism, framing, construal level, tone,
headline strategy, CTA style, NDF psychological profile, copy guidance
with headline templates, and expected lift estimates.

You can try this in the interactive docs:
**https://focused-encouragement-production.up.railway.app/docs**

---

## What "Deal IDs" Mean in Our Context

Traditional data partners provide **audience segment deal IDs** that you
plug into StackAdapt's UI to activate targeting. Our approach is different
and more powerful:

Instead of just saying "target luxury travel buyers," we tell you
**which psychological approach to use for each buyer type** and **why**.

Our equivalent of deal IDs are the **segment IDs** listed above
(e.g., `informativ_careful_truster_authority_luxury_transportation_t1`).
Each one maps to a specific psychological profile with a specific
creative strategy backed by real purchase evidence.

If StackAdapt's Graph API supports custom segment creation, we can
map these segment IDs directly into the platform so they appear in
your dashboard like any other data partner segment.

---

## Questions?

Contact Chris Nocera: CNocera@rebelliongroup.com
