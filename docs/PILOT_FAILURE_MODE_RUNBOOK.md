# LUXY Pilot — Failure-Mode Runbook (v0.1)

**Status**: rehearse Week 4 of flight against synthetic injection
**Owners**: Chris Nocera (technical), Becca (agency operational), LUXY (client)
**Last revised**: 2026-04-29

---

## Why this document exists

When something goes wrong mid-pilot, response time matters. Without a
runbook the team improvises — often with too few facts, under time
pressure, with the wrong escalation path. This document fixes the
response decisions IN ADVANCE for the failure modes simulation
analysis identified.

For each failure mode:
- **Detection signal** — how we notice it
- **Decision tree** — what to do, in order
- **Escalation path** — who decides what
- **Communication template** — what to tell LUXY

Rehearsal Week 4: synthetic-failure injection against a staging
environment so the team has muscle memory before the real failure.

---

## Failure mode 1 — Webhook silence

### Detection signal

- Prometheus counter `adam_outcome_signal_received_total` flatlines or
  significantly under-paces the `adam_decisions_total` counter
- Specifically: outcome-event-to-decision ratio drops below 0.05 over
  any 60-minute window during pilot active hours
- StackAdapt webhook delivery dashboard shows queued or failed
  deliveries

### Why it matters

Without conversion events, the entire learning loop starves silently.
The system continues making decisions but none of them feed back into
TheoryLearner posteriors, PerAtomContributionTracker, or the
attention-inversion test. The pilot's headline number is unreportable.

### Decision tree

1. **First 5 minutes**: confirm the signal is genuine (not a spike-and-
   normalize artifact)
   - Check `adam_decision_grounding_state` counter — are decisions
     actually being made?
   - Check StackAdapt webhook delivery dashboard — any failed deliveries?
   - Check the `adam:atom_outputs:{decision_id}` Redis cache — is the
     write side healthy?

2. **At 5 minutes confirmed**: start triage
   - Curl the webhook endpoint with a synthetic payload
   - Check the webhook handler logs for HMAC validation failures or
     payload parse errors
   - Verify the decision_cache is populating correctly (Neo4j
     `(:DecisionContext)` nodes)

3. **At 15 minutes**: pause the campaign in StackAdapt if root cause
   isn't identified
   - Don't keep accumulating data we can't measure
   - Becca communicates to LUXY: "investigation in progress, campaign
     paused, ETA on resumption: 24h"

4. **At 1 hour**: emergency rollback if root cause is in our code
   - Revert the most recent commit affecting the webhook path
   - Re-deploy
   - Verify outcome events flow before resuming

### Escalation path

- Detection → Chris (immediate)
- 15-minute pause decision → Chris + Becca (joint)
- LUXY communication → Becca (with Chris's technical brief)
- Code rollback → Chris (technical authorization)

### Communication template

> "We've identified a delivery issue with our outcome-tracking pipeline
> that's preventing us from measuring campaign performance correctly.
> We're pausing the active flight while we resolve. We expect resumption
> within 24 hours. Performance during the paused period is not reportable
> in the pilot's headline analysis but spend is also paused."

### Rehearsal Week 4

Inject a simulated webhook failure (return 500 from webhook endpoint
for 30 min). Confirm: detection within 10 min, decision tree followed,
LUXY communication drafted within 30 min of confirmation.

---

## Failure mode 2 — Audience segment rejected by StackAdapt

### Detection signal

- StackAdapt API returns 4xx on segment push
- "Insufficient match volume" warning on the StackAdapt dashboard
- One or more pre-registered archetype segments not deliverable

### Why it matters

The pre-registered analysis plan locks the archetype priority queue.
A rejected segment means we either swap to the next-priority archetype
(transparent change to the plan) or we drop a planned arm.

### Decision tree

1. **Within 1 hour of rejection**: confirm the rejection is genuine
   - StackAdapt's "insufficient volume" sometimes resolves with a
     wider geo or relaxed daypart
   - Try those before swapping

2. **At 4 hours**: if un-resolvable
   - Swap to the next archetype in the priority queue (per the
     pre-registered analysis plan §5)
   - Log the swap in the analysis-plan amendments section
   - Becca communicates to LUXY: "audience adjustment per pre-registered
     fallback ordering"

3. **At 24 hours**: if multiple segments are rejected
   - This is a structural integration issue, not a one-off
   - Pause the flight, investigate end-to-end with StackAdapt support
   - Update the integration before resuming

### Escalation path

- Detection → Becca (operational owner of StackAdapt console)
- Swap decision → Becca + Chris (joint, references pre-registered queue)
- LUXY communication → Becca
- Multiple-rejection investigation → Chris drives

### Communication template

> "Our pre-registered analysis plan includes a fallback archetype
> ordering for exactly this case. We're activating that fallback. The
> primary endpoint is unaffected because the comparison is between
> bilateral targeting (any priority archetype) and lookalike audience
> on the same creative."

### Rehearsal Week 4

Inject a simulated 4xx response from StackAdapt API on the highest-
priority segment. Confirm: swap decision made within 4h, the next-
priority archetype is correctly substituted, the change is logged.

---

## Failure mode 3 — Creative pulled by agency-of-record or LUXY brand

### Detection signal

- Agency or LUXY copy-approval team flags a creative as off-brand
- StackAdapt creative review status shows "rejected" or "pending"
- Brand safety team raises an alert

### Why it matters

The pilot tests audience selection, not creative. Pulling a creative
shouldn't invalidate the primary endpoint as long as a control-equivalent
creative continues running on the lookalike arm.

### Decision tree

1. **Immediate**: check both arms
   - If the pulled creative is shared (same on both arms): both
     arms pause until the next-rank creative variant is approved.
     Comparison resumes.
   - If the pulled creative is treatment-arm-only: that's a confound
     we cannot recover. Pause the flight; investigate why the creatives
     diverged from the pre-registered "creative held constant"
     specification.

2. **Within 4 hours**: deploy the next-rank creative variant
   - The pre-registered plan should specify variant rank order for
     each arm
   - Any swap is a transparent change

3. **At 24 hours**: if no creative variant survives review
   - Escalate. The pilot may need an extension while creatives are
     re-developed.

### Escalation path

- Detection → Becca (agency owns approval relationship)
- Pause decision → Becca + Chris (joint)
- LUXY communication → Becca (with brand-team details)
- Creative re-development → Becca drives with agency creative team

### Communication template

> "One creative variant was flagged for [reason]. We're swapping to
> the next-rank approved variant. The pre-registered analysis plan's
> primary endpoint is unaffected — both arms run the same creative."

### Rehearsal Week 4

Inject a simulated copy-rejection on a treatment-arm creative.
Confirm: swap decision within 4h, the variant rank is logged, both
arms remain creative-aligned.

---

## Failure mode 4 — CTR drops below benchmark on Day 3

### Detection signal

- Treatment-arm CTR on Day 3 is below 50% of the historical LUXY
  baseline OR the lookalike-arm CTR
- Both arms tracking similarly poor → likely an external shift, not
  ADAM-specific

### Why it matters

Could indicate (a) wrong creative deployed, (b) pixel firing failure
on the landing page, (c) audience targeting misconfiguration, (d) a
genuine signal that the predicted bilateral lift won't manifest.

### Decision tree

1. **First 4 hours of Day 3**: investigate before continuing
   - Verify pixel firing on luxyride.com (synthetic conversion test
     should fire the pixel and return success)
   - Check creative IDs deployed in StackAdapt — match the
     pre-registered list?
   - Check audience segment IDs deployed — match the
     pre-registered list?
   - Compare to historical LUXY display CTR baseline — is this a
     genuine drop or aligned with seasonality?

2. **At 8 hours**: if root cause not identified
   - Pause the flight to prevent budget waste on a likely-broken setup
   - Communicate to LUXY: "Day 3 CTR anomaly under investigation.
     Pausing flight to prevent budget waste on potentially-broken
     setup."

3. **At 24 hours**: resolution decision
   - If a configuration error is found: fix, restart the flight,
     log the gap-day as excluded from primary analysis
   - If no error found and CTR remains low: this is INFORMATION. The
     bilateral targeting may not be producing the predicted lift on
     this campaign. Continue the flight (data is data) but flag that
     the primary endpoint may not show the expected result.
   - If CTR returns to baseline naturally: resume monitoring; gap-day
     impressions excluded from primary analysis

### Escalation path

- Detection → Chris (technical) + Becca (operational dual-detect)
- Pause decision → Chris + Becca (joint, technical-rooted)
- LUXY communication → Becca (with Chris's investigation details)

### Communication template

> "Day 3 CTR is significantly below historical baseline. We're
> investigating four possible causes — pixel issue, creative
> configuration, audience configuration, or genuine signal. Pausing
> the flight while we determine which. Resumption ETA depends on root
> cause; will update within 24 hours."

### Rehearsal Week 4

Inject a synthetic 50%-of-baseline CTR signal on the treatment arm.
Confirm: investigation steps run within 4h, decision is made within
24h, communication is drafted.

---

## Failure mode 5 — StackAdapt inventory change mid-flight

### Detection signal

- StackAdapt platform changelog announces an update affecting:
  - Delivery algorithm
  - Brand-safety policy
  - Inventory composition (publisher set, geo, etc.)
- We notice via direct communication or StackAdapt's release notes

### Why it matters

This is exogenous — neither arm controls it — but it changes the
context the pilot is running in. The pre-registered analysis plan
specifies that primary analysis is run with AND without post-change
impressions; both reported.

### Decision tree

1. **Within 24 hours of detection**: confirm the change applies to
   our pilot
   - Some StackAdapt updates are opt-in or affect only specific
     campaign types
   - Verify against the pilot's actual setup

2. **If applies**: log the moment as a `market_shift_event` in the
   RotationRegistry (per Phase 0.1 commit `9f5a36d`)
   - The mechanism rotation registry's drift tracking handles this

3. **At analysis time**: run primary endpoint twice
   - With all impressions
   - Excluding post-change impressions
   - Both reported in the final analysis. Material divergence
     between the two informs the interpretive claim.

4. **If continued**: don't take new pilot decisions while material
   uncertainty exists about the platform-level change's effect

### Escalation path

- Detection → Becca (StackAdapt relationship owner)
- Logging → Chris (technical, into RotationRegistry)
- Communication → Becca (LUXY context)
- Analysis-time decision → Chris + Becca (joint, with statistical
  reviewer if available)

### Communication template

> "StackAdapt announced a platform update affecting [delivery algorithm
> / brand safety / inventory]. Our pre-registered analysis plan handles
> this — we'll report the primary endpoint with and without post-update
> impressions, and the comparison is informative for the interpretive
> claim. The flight continues."

### Rehearsal Week 4

Simulate a notification of a StackAdapt update. Confirm: market_shift
event logged within 24h, RotationRegistry contains the marker, both-
analysis-runs decision is made.

---

## Failure mode 6 — Market shift detected mid-pilot

### Detection signal

- Becca surfaces a competitor major-campaign launch
- LUXY notifies of a pricing change
- Industry seasonality unexpected shift (e.g., COVID-style disruption)

### Why it matters

This is the broader-than-StackAdapt version of failure mode 5.
Foundation §2.5 case E. The pre-registered plan handles this with
both-runs analysis (with and without post-shift impressions).

### Decision tree

1. **Within 24 hours of Becca surfacing**: confirm the shift is real
   and LUXY-relevant (not anecdote)

2. **At confirmation**: log via the RotationRegistry market_shift
   marker + write a Loop B Claim capturing Becca's interpretation
   - The Claim is HYPOTHESIS at write time (HMT discipline rule 12)
   - Subsequent data tests it

3. **Continued operation**: pilot continues with the shift logged.
   Analysis runs twice (per failure mode 5).

### Escalation path

- Detection → Becca (most likely surface)
- Logging (market_shift + Loop B Claim) → Chris (technical write)
- LUXY communication → Becca + LUXY (joint understanding of the shift)

### Communication template

> "We've identified a [competitor / pricing / seasonal] shift that
> may affect campaign performance. Our pre-registered analysis plan
> includes protocol for this — we report with and without post-shift
> impressions, and the comparison itself is informative. Loop B
> captures Becca's interpretation as a Claim that subsequent data
> tests."

### Rehearsal Week 4

Becca simulates surfacing a competitor launch. Confirm: market_shift
logged within 24h, Loop B Claim captures Becca's hypothesis as
HYPOTHESIS, both-runs decision recorded for analysis time.

---

## Failure mode 7 — A14 calibration-pending coefficient producing
suspect outputs

### Detection signal

- Prometheus counter `adam_a14_flag_active_total` shows abnormal
  concentration on a single flag
- A14 retirement-trigger dashboard (Phase 0.1 commit `fec2c40`) shows
  retirement criterion crossed for a flag whose coefficient looks
  out-of-distribution
- Conversion rates per (mechanism, archetype) cell diverge sharply
  from prior baseline in directions inconsistent with theory

### Why it matters

A14 flags name calibration-pending placeholders. If pilot data
exercises a flag and the placeholder is wrong, we'd be making
decisions on bad coefficients. The retirement-trigger dashboard
exists exactly to catch this.

### Decision tree

1. **Within 1 hour of A14 retirement-trigger crossing**: assess the
   coefficient
   - Read recent decisions where the flag was active
   - Compare actual outcome rates to predicted rates per the
     coefficient's role

2. **At assessment**: decide
   - If the coefficient looks correct: retire the A14 flag (mark the
     coefficient PINNED with the empirical value)
   - If the coefficient looks INCORRECT: flag the affected decisions
     for re-analysis; consider whether to update the coefficient
     mid-pilot or mark the flag as REQUIRES_RECALIBRATION

3. **At analysis time**: any decisions made under an incorrect
   coefficient are flagged in the analysis. The conformal CI
   correctly widens to reflect the additional uncertainty.

### Escalation path

- Detection → Chris (technical, Prometheus + retirement-trigger
  dashboard owner)
- Coefficient decision → Chris + Becca (joint, with statistical
  reviewer if available)
- LUXY communication → Becca (only if material to outcome reporting)

### Communication template

> "Our calibration discipline (A14) flagged [SPECIFIC_FLAG] as having
> crossed its retirement trigger. The coefficient was a pilot-pending
> placeholder; we now have empirical data to set it. The mid-pilot
> impact on decisions is bounded by [analysis] and we'll report the
> bound in the final."

### Rehearsal Week 4

Synthetically cross an A14 retirement trigger via injected data.
Confirm: detection within 1h, assessment runs, decision is made and
logged.

---

## General principles

### When in doubt, pause

The pilot's value is the integrity of the data. A 24-hour pause to
investigate is far cheaper than a contaminated dataset.

### Communication discipline

Every LUXY communication uses the cognitive vocabulary of the
foundation, NOT the programmatic-DSP vocabulary. We don't say "ad
performance" — we say "the inferential signal." We don't say "audience
segment" — we say "archetype-aligned bilateral targeting." This
preserves the differentiator narrative.

### Logging discipline

Every transparent change to the pre-registered plan is logged in the
analysis-plan amendments section. Every market_shift, every A14
retirement, every audience swap, every creative change — logged.
Audit trail is the difference between defensible pilot and unfalsifiable
claims.

### Loop B captures everything

When Becca interprets a situation ("I think this is a competitor
launch"), her interpretation goes into the Dialogue Ledger as a
HYPOTHESIS Claim per HMT discipline rule 12. Subsequent data tests
it. Never let Becca's tacit knowledge become anecdote.

---

## Rehearsal Week 4 schedule

Synthetic injection over 1 day with the team observing. Each failure
mode gets ~30 minutes of live rehearsal.

| Time | Mode | Injection | Detect goal |
|---|---|---|---|
| 09:00 | #1 webhook silence | Return 500 from webhook | Detect ≤10 min, pause ≤15 min |
| 10:00 | #2 segment rejection | StackAdapt 4xx on highest-priority arch | Swap ≤4h |
| 11:00 | #3 creative pulled | Mark a treatment creative rejected | Swap ≤4h |
| 13:00 | #4 CTR drop | Inject 50% baseline CTR on treatment arm | Investigation ≤4h, decision ≤24h |
| 14:00 | #5 inventory change | Simulate StackAdapt update notification | Market_shift event logged ≤24h |
| 15:00 | #6 market shift | Becca surfaces competitor launch | Market_shift + Loop B Claim ≤24h |
| 16:00 | #7 A14 coefficient | Inject A14 retirement trigger | Detect + assess ≤1h |

Each rehearsal logs:
- Time-to-detection
- Time-to-decision
- Communication draft (for LUXY-relevant modes)
- Whether the decision matched the runbook

Drift from the runbook in rehearsal triggers a runbook revision
BEFORE pilot launch.

---

## Amendments log

| Date | Section | Change | Reason | Approver |
|---|---|---|---|---|
| 2026-04-29 | initial | n/a | initial draft | Chris Nocera |

---

## References

- Pre-registered analysis plan: `docs/PILOT_PRE_REGISTERED_ANALYSIS_PLAN.md`
- Phase 0.1 commits: see analysis plan §8
- HMT discipline rule 12 (user self-reports as hypotheses):
  `ADAM_HUMAN_MACHINE_TEAMING_FOUNDATION.md` §A12
- Foundation §2.5 case E (market shift): `ADAM_THEORETICAL_FOUNDATION.md`
- Foundation §7 rule 11 (fitness function IS the ethics): same
