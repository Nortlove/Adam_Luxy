# CTV Creative Direction Briefs — LUXY Ride

**Purpose:** CTV is the PRIMING channel, not the conversion channel.
These 15-30 second spots plant psychological goal seeds that make
display ads effective 1-7 days later. The goal is NOT "book now."
The goal is "activate the right psychological state so the next
ad feels like the answer to something they already want."

**Key principle from research:** Nonconscious goals, once activated,
PERSIST and INTENSIFY when unfulfilled (Chartrand et al., 2008).
A CTV ad that activates a competence goal at 9 AM creates a buyer
who is MORE receptive to an authority-framed display ad at 3 PM —
because the unfulfilled goal has been building all day.

---

## Campaign 1: Corporate Executives
**Goal to activate:** Competence Verification
**Group ID:** 427436

### Script Direction (15s)

**Visual:** Polished executive stepping out of a luxury sedan at a
corporate building. Not flashy — understated, professional.

**Voiceover direction:**
> "The professionals who move markets don't leave their ground
> transport to chance."

**End card:** LUXY Ride logo + "The Executive Standard"

**What this does psychologically:** Activates the competence
verification goal — "Am I operating at the level my position
demands?" The viewer doesn't consciously think about car services.
The goal sits in working memory, and when a display ad appears
later saying "The executive standard in ground transportation,"
it feels like the answer to a question they were already asking.

**Metaphor family:** Vertical (standard, level, above, rise)

### Script Direction (30s)

**Visual (0-10s):** Morning. Executive reviews phone in back seat
of luxury sedan. Calm. Controlled. No urgency.

**Visual (10-20s):** Driver opens door at destination. Executive
steps out looking composed. Building entrance, glass, steel.

**Visual (20-30s):** Meeting room. Same executive, confident.
Cut to: subtle shot of the sedan pulling away.

**Voiceover:**
> "Some things should just work. Your schedule. Your preparation.
> Your arrival. LUXY Ride. For professionals who expect the details
> to be handled."

**End card:** LUXY Ride logo + phone number/URL

**What NOT to do:**
- Don't show pricing (this isn't a conversion ad)
- Don't use urgency language ("book now," "limited time")
- Don't compare to rideshare (activates the wrong comparison frame)
- Don't show multiple people (this is about individual competence)

---

## Campaign 2: Professionals (Standard)
**Goal to activate:** Planning Completion
**Group ID:** 427691

### Script Direction (15s)

**Voiceover direction:**
> "One decision covers every business trip. No apps to compare.
> No surge to monitor. Just... handled."

**End card:** LUXY Ride logo + "Every Trip. Handled."

**Psychological target:** Activates the planning completion goal —
the satisfaction of having a complex logistical problem solved.
The viewer who manages travel for themselves or others feels the
relief of one less thing to manage.

**Metaphor family:** Path/journey (seamless, smooth, direct, handled)

### Script Direction (30s)

**Visual arc:** Multiple scenarios (airport, hotel, office) — same
person in each, always composed, never rushing. Cut between
locations smoothly. The car is the constant.

**Voiceover:**
> "Airport at six. Client lunch at noon. Dinner downtown at seven.
> Different destinations. Same standard. Same driver who knows
> your preferences. LUXY Ride. One decision for every trip."

---

## Campaign 3: Professionals (Kinective)
**Goal to activate:** Status Signaling
**Group ID:** 427691

### Script Direction (15s)

**Voiceover direction:**
> "Your car says something before you do. Make sure it says
> the right thing."

**End card:** LUXY Ride logo + "Arrive Distinguished"

**Psychological target:** Activates status signaling — the awareness
that appearance and presentation create first impressions. Not
ostentatious. Quietly confident.

**Metaphor family:** Weight/substance (distinguished, significant,
carries weight, substantial)

---

## Campaign 4: Leisure Travel
**Goal to activate:** Indulgence Permission
**Group ID:** 427692

### Script Direction (15s)

**Voiceover direction:**
> "You planned the trip. You earned the trip. You deserve the ride
> that matches it."

**End card:** LUXY Ride logo + "You Earned This"

**Psychological target:** Gives permission to spend on luxury.
Many leisure travelers feel guilty about upgrading from a standard
rideshare. This ad reframes the luxury car service as DESERVED —
the natural completion of a trip they already invested in.

**Metaphor family:** Texture/indulgence (luxurious, rich, refined,
earned, deserved)

### Script Direction (30s)

**Visual arc:** Couple on vacation. Airport arrival → hotel →
dinner → scenic drive. The luxury sedan is woven through every
transition. Never the focus. Always present.

**Voiceover:**
> "You spent weeks planning the perfect trip. The restaurants.
> The hotel. The moments you'll remember. Why would you leave
> the ride between them to chance? LUXY Ride. Because every
> part of the trip should feel like the trip."

**What NOT to do:**
- Don't show price comparison (triggers analytical mode)
- Don't emphasize business use (wrong frame for leisure)
- Don't use urgency (leisure is the opposite of urgent)

---

## Campaign 5: Leisure Travel (Kinective)
**Goal to activate:** Novelty Exploration
**Group ID:** 427692

### Script Direction (15s)

**Voiceover direction:**
> "A private car service isn't what you think. No stiffness.
> No pretension. Just... a better way to move."

**End card:** LUXY Ride logo + "See What It's Like"

**Psychological target:** Activates curiosity about the unknown.
Many people have never used a luxury car service and have
preconceptions (stuffy, expensive, pretentious). This ad directly
challenges those assumptions to activate exploration.

**Metaphor family:** Space/openness (discover, explore, open,
experience, what it's like)

---

## Click URL Protocol

When these CTV ads drive to a display companion or when display
ads link to luxyride.com, append attribution parameters:

```
https://luxyride.com/?informativ_segment={ARCHETYPE}&informativ_mechanism={MECHANISM}&sapid={SA_POSTBACK_ID}
```

**Examples:**
```
https://luxyride.com/?informativ_segment=corporate_executive&informativ_mechanism=authority&sapid={SA_POSTBACK_ID}
https://luxyride.com/?informativ_segment=leisure_travel&informativ_mechanism=curiosity&sapid={SA_POSTBACK_ID}
```

informativ.js on the landing page automatically captures these
parameters, persists them in sessionStorage across page navigation,
and includes them in the conversion event so we know which
archetype × mechanism × CTV/display combination drove the booking.

---

## How CTV Priming Is Measured

We can't track CTV "clicks" (TV doesn't click). But we CAN measure:

1. **Lift in display conversion rate** for buyers exposed to CTV
   vs not exposed (StackAdapt's view-through attribution, 180 days)

2. **Goal activation validation:** Do display ads on pages matching
   the CTV-primed goal convert at higher rates? This is a Level 3
   proposition in our inferential learning agent.

3. **Time-delayed conversion patterns:** If CTV priming works,
   conversions should cluster 1-7 days after CTV exposure (the goal
   intensification window from Chartrand et al.).

4. **Cross-channel ROAS:** Total revenue attributed to buyers who
   received CTV + Display vs Display-only. The premium of CTV
   priming should exceed the CTV cost.

These measurements feed directly into our 22 learning systems.
The knowledge propagation network spreads the CTV insights to
budget allocation (increase/decrease CTV spend), creative direction
(which goal activation produced the most downstream conversions),
and sequence planning (optimal delay between CTV and display).
