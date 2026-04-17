# Questions for Becca — StackAdapt Graph API Integration

**Context:** We need to understand what StackAdapt's Graph API enables
so we can configure the FULL INFORMATIV integration (not a watered-down
static campaign). The system's power comes from real-time decisions per
impression and learning from every conversion. Static campaigns with
fixed creative miss the entire point.

---

## Critical Questions

### 1. Can StackAdapt call an external API on each bid/impression?

**What we need:** When StackAdapt is about to serve an impression for
a LUXY campaign, it calls our server with the segment_id, page_url,
device_type, and buyer_id. We return the creative direction in <120ms.

**Ask Becca:** "Does StackAdapt's Graph API or DCO system support
calling an external REST API to get creative parameters before serving
an impression? Some DSPs call this 'external creative decisioning' or
'dynamic creative API.' If yes, what's the format of the request it
sends and what response format does it expect?"

**If yes:** This is the full integration. Every impression is
psychologically optimized in real-time.

**If no:** We need to pre-compute creative recommendations per segment
and upload them as StackAdapt rules. Less dynamic but still uses our
intelligence.

---

### 2. Can StackAdapt send conversion events to our webhook?

**What we need:** Server-to-server postback when a LUXY conversion
happens. This is how the system learns.

**Ask Becca:** "Can you configure a server-to-server conversion postback
(also called a 'conversion webhook' or 'S2S pixel') that fires to our
URL when a conversion event occurs? We need it to include: event_id,
segment_id, buyer_id (uid), page_url, and revenue amount."

**Our webhook URL:**
`https://focused-encouragement-production.up.railway.app/api/v1/stackadapt/webhook/conversion`

**Signature:** HMAC-SHA256 with header `X-Informativ-Signature`

---

### 3. Can she create custom audience segments in StackAdapt?

**What we need:** 8 audience segments, one per LUXY archetype.

**Ask Becca:** "Can you create custom audience segments in StackAdapt
using the Graph API? We have 8 pre-defined buyer segments with IDs
like `informativ_careful_truster_authority_luxury_transportation_t1`.
Can these be created as named segments in the StackAdapt dashboard?"

**If yes:** She creates 8 segments, each with our segment_id as a
label. Campaigns target these segments. When combined with Q1 above,
each impression for each segment gets real-time creative intelligence.

**If no:** She creates campaigns manually with targeting rules that
approximate each archetype (by domain list, content category, etc.).

---

### 4. What did the previous data insight partners provide technically?

**Ask Becca:** "When you worked with data insight partners before,
what exactly did they give you technically? Was it:
(a) A segment ID you activated in the StackAdapt marketplace?
(b) A CSV/data file you uploaded?
(c) An API endpoint StackAdapt called?
(d) A pixel or tag you installed?"

This tells us which integration pattern StackAdapt already supports
and which Becca is familiar with.

---

### 5. Does StackAdapt support dynamic creative based on external signals?

**Ask Becca:** "Does StackAdapt's DCO (Dynamic Creative Optimization)
support selecting creative variants based on external API signals? For
example: if our API says 'use authority messaging with gain framing for
this impression,' can StackAdapt pick the creative variant that matches?"

**If yes:** We create creative variants per mechanism (authority version,
social proof version, cognitive ease version, etc.) and StackAdapt
selects the right one per impression based on our API response.

**If no:** We select the MOST LIKELY effective creative per segment
upfront, which still works but loses the per-impression optimization.

---

## What We'll Build Based on Her Answers

| If she says... | We build... |
|----------------|-------------|
| API calls supported | Full real-time DCO integration (~2 hours to configure) |
| Webhook supported | Conversion learning loop (already built, just configure URL) |
| Custom segments possible | 8 named segments in StackAdapt dashboard |
| DCO with external signals | Multiple creative variants per segment, API-selected |
| None of the above | Pre-computed static campaign specs (Level 1 fallback) |

---

## The Bottom Line for Becca

"This isn't a traditional data partnership where we hand you a segment
and you run it. We're a real-time intelligence engine that makes your
campaign smarter on every impression. The setup is slightly more involved
than activating a marketplace segment, but the result is a campaign that
optimizes itself — not just on clicks, but on the actual psychological
drivers of luxury transportation purchases. We'll be working alongside
you to set everything up."
