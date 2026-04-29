# LUXY Pilot — Pre-Registered Analysis Plan (v0.1 DRAFT)

**Status**: DRAFT for third-party statistical review (task #32)
**Target instrument**: LUXY corporate black-car StackAdapt pilot
**Pre-registration target**: OSF or AsPredicted.org once Chris finalizes
**Last revised**: 2026-04-29

---

## Why this document exists

The pilot's headline number (lift, CPA, conversion rate, etc.) is
defensible only if the analysis plan was committed BEFORE outcomes
were observed. Without pre-registration, a hostile due-diligence
reader (sharp investor, competing DSP, skeptical agency) can question
which numbers count, which segments were chosen, and which metrics
were privileged after the fact.

This document fixes the analysis plan in advance:

  - The primary endpoint (the test that decides "did the pilot
    succeed")
  - The control arm specification (what's being compared)
  - The required N at the chosen power, alpha, and detectable lift δ
  - At least three secondary endpoints designed to win at low N
  - Failure-mode protocols (what to do if observation count comes in
    short, market shifts mid-flight, segment is rejected, etc.)

The document is versioned. Amendments after pilot launch are
discipline failures and must be logged with reason; they do not
retroactively change the pre-registered claims.

---

## Section 1 — Primary endpoint

### 1.1 The hypothesis

**ADAM's bilateral targeting produces a higher conversion rate on
LUXY's StackAdapt impressions than the lookalike-style audience
StackAdapt deploys today.**

### 1.2 The test

Two-proportion z-test on the difference in observed conversion rate
between:

  - **Treatment arm** — impressions delivered against archetypes
    selected by ADAM's bilateral cascade (post-L3 override — Phase 0.1
    commit `bf69274`), with mechanism scoring incorporating
    chain-attestation modulation (commits `cf399d3` + `362dd9f`).
  - **Control arm** — impressions delivered against StackAdapt's
    lookalike audience for the same campaign, run concurrently with
    same creative + same dayparting.

Null: p_treatment - p_control = 0
Alternative (one-sided, pre-registered direction): p_treatment > p_control

### 1.3 Detectable lift target

We commit to detecting a relative lift of **+30%** on the conversion
rate at 80% power, α = 0.05.

### 1.4 Required N

(*To be finalized once LUXY's actual baseline conversion rate is
confirmed by Becca. Placeholders below; replace before publishing.*)

Assuming baseline conversion rate p_C = 0.020 (2%) — typical for
corporate-travel display:

```
n_per_arm ≈ 16 × p × (1 - p) / δ²
          = 16 × 0.020 × 0.980 / (0.020 × 0.30)²
          = 16 × 0.0196 / (0.006)²
          ≈ 8,711 per arm
          ≈ 17,422 total impressions for primary test
```

With baseline p_C = 0.005 (0.5% — closer to display CTR floor):

```
n_per_arm ≈ 16 × 0.005 × 0.995 / (0.005 × 0.30)²
          ≈ 35,378 per arm
          ≈ 70,756 total impressions
```

**Action item before pre-registration is locked**: confirm LUXY's
actual baseline display conversion rate from Becca. Update n_per_arm
accordingly. Update the "detectable lift" if the realistic flight
cannot deliver enough impressions.

### 1.5 Conformal interval reporting

In addition to the z-test p-value, the headline claim reports:

  - Observed relative lift δ̂ = (p̂_T - p̂_C) / p̂_C
  - **Conformal-coverage 95% CI on δ̂** via
    `adam.intelligence.causal_conformal.ConformalLiftWrap` (commit
    `362dd9f`). Calibration set bootstrapped pre-pilot from the
    synthetic A/B simulation (commit `105ee4a`); production calibration
    pairs accumulate as holdout-cell realizations land.

The conformal CI has finite-sample marginal coverage at any N — the
parametric delta-method CI under-covers at moderate N. Both reported;
conformal is the headline figure.

---

## Section 2 — Control arm specification

### 2.1 What we are NOT testing

The pilot is NOT testing "ADAM's creative beats LUXY's existing
creative." Creative is held constant across arms.

The pilot is NOT testing "ADAM's full automation beats human-managed
campaigns." The control arm is StackAdapt's lookalike audience,
which is itself algorithmically managed.

### 2.2 What we ARE testing

The DIFFERENCE between two AUDIENCE-SELECTION strategies on the same
creative + same channel + same dayparting:

  1. ADAM's bilateral targeting (treatment)
  2. StackAdapt lookalike audience (control)

### 2.3 The 2×2 factorial alternative (deferred)

A cleaner factorial would test:

  - audience source (bilateral vs lookalike)
  - creative source (ADAM-suggested vs LUXY's current)

This is 4 arms × N per arm. If LUXY's pilot budget supports the 4×
total impressions needed to power this, we expand. Otherwise we run
the 2-arm primary endpoint and accept the confound (creative held
constant).

**Decision criterion**: if LUXY's budget supports ≥ 4 × n_per_arm
impressions per the §1.4 calculation, we run 2×2 factorial. Otherwise
2-arm.

---

## Section 3 — Secondary endpoints

Designed to win at low N. Each is reported with a conformal CI when
the underlying signal supports it.

### 3.1 Engagement-quality differential

**Hypothesis**: ADAM-targeted impressions produce HIGHER mean
processing depth than lookalike-targeted impressions.

**Measurement**: classify each impression's `processing_depth` per
`adam/retargeting/engines/processing_depth.py`. Compare mean depth
weight across arms via two-sample t-test on the
`processing_depth_weight` field.

Wins at low N because viewability + processing depth signal flows on
EVERY impression, not just conversions. Sample size is impressions,
not conversions. Powered to detect a 5% difference in mean depth at
~5,000 impressions per arm.

### 3.2 Page-context-conditional CTR

**Hypothesis**: ADAM-targeted impressions on page contexts with
matching attentional posture (per
`page_attentional_posture_substrate`) produce HIGHER CTR than ADAM-
targeted impressions on mismatched-posture pages.

**Measurement**: compute CTR per cell of (mechanism_category × page
posture) using the mechanism-taxonomy-runtime accumulator (commit
`6ae506e`). Compare matched-diagonal cells to mismatched cells via
two-sample test.

This is the Foundation §2 attention-inversion test. Wins at low N
because CTR signal is much denser than conversion signal (every
clicked impression contributes).

### 3.3 30-day return rate (multi-horizon adjudication preview)

**Hypothesis**: bilateral-targeted users have HIGHER 30-day return
rate than lookalike-targeted users — bilateral matches deeper
psychological alignment that should drive longer-term engagement,
not just immediate conversion.

**Measurement**: cohort each arm's converters; track return-visit
rate at 30 days post-conversion. Compare via two-proportion z-test.

This catches the scenario where bilateral wins on immediate CPA but
loses on long-horizon equity — a critical scenario per
Foundation §7 rule 11. Multi-horizon adjudication wiring (task #27)
implements this; secondary endpoint reports it explicitly.

### 3.4 Per-archetype lift heterogeneity

**Hypothesis**: bilateral lift VARIES across archetypes. Some
archetypes (e.g., careful_truster) have stronger psychological
signal in LUXY's review corpus; others have weaker. ADAM should
outperform lookalike most on the well-signaled archetypes.

**Measurement**: per-archetype lift via M2 Causal Forests
(`causal_forest.py` substrate) when libs land + sufficient data.
Until then, archetype-stratified two-proportion comparison.

Reported as a HETEROGENEITY result, not a per-archetype p-value
(which would multiply-test). The interpretive claim: "ADAM's lift
shows meaningful variation across archetypes consistent with the
bilateral architecture's per-archetype signal density."

---

## Section 4 — Failure-mode protocols

What to do if specific failure modes manifest mid-flight. Decisions
made now, NOT post-hoc.

### 4.1 Conversion count comes in short

If by Day 14 of the flight, total observed conversions < 50% of the
projected midpoint:

  - DO NOT extend the flight unilaterally. The comparison is fixed-N.
  - Report the under-powered result honestly. The conformal CI will
    correctly widen; the claim becomes "lift is at least X% with 80%
    confidence" rather than "the pilot's primary endpoint succeeded
    at p < 0.05."
  - Renegotiate with Becca + LUXY for an extension or budget
    expansion; if approved, the extension is logged as a transparent
    change to the pre-registered plan.

### 4.2 Market shift mid-flight (Foundation §2.5 case E)

If ANY of the following occur and are LUXY-relevant:
  - Competitor major campaign launch
  - LUXY pricing change
  - Travel-industry seasonality unexpected shift

We:
  1. Mark the day in the analysis as a `market_shift_event` in the
     RotationRegistry (#22 substrate)
  2. Run the primary endpoint analysis with AND without the post-
     shift impressions excluded. Both reported.
  3. If the post-shift period produces materially different
     directional results, that's information — Loop B (HMT) captures
     Becca's tacit knowledge about the shift as a Claim.

### 4.3 Audience segment rejected by StackAdapt

We logged this risk in advance: bilateral segments may be flagged for
"insufficient match volume" by StackAdapt. Response:

  1. Keep the segment definition; submit a debug request to
     StackAdapt
  2. If un-resolvable within 48h, swap to the next-priority archetype
     in the pre-registered queue (priority order published in
     section 5)
  3. The swap is logged as a transparent change

### 4.4 Creative pulled by agency or LUXY

Same arm continues running with the next-rank creative variant.
Logged as a transparent change. The pre-registered analysis plan
controls for creative VERSION but the inferential claim is about
audience selection, not creative — the swap shouldn't invalidate the
primary endpoint.

### 4.5 CTR drops below benchmark Day 3

Investigate before continuing. Possible causes:
  - Wrong creative deployed
  - Pixel firing failure
  - Audience targeting misconfiguration
  - Genuine signal that the predicted bilateral lift won't manifest

Resolution required before continuing the flight; results from before
the resolution are reported, but the claim is bounded by the
discontinuity.

### 4.6 StackAdapt inventory change mid-flight

Any platform-level change StackAdapt makes (delivery algorithm
updates, brand-safety policy changes, inventory composition shifts)
is recorded. Like §4.2 market shifts, primary analysis run with and
without the post-change impressions.

---

## Section 5 — Archetype priority queue

When archetype targeting must be swapped (per §4.3), priority order
based on bilateral signal density in LUXY's review corpus:

1. **careful_truster** (highest signal density per Mar-2026 review pull)
2. **status_seeker**
3. **easy_decider**

Suppression archetypes (low conversion rate per historical):

- skeptical_a (suppress)
- disillusioned (suppress)

This ordering is DERIVED from the bilateral edge corpus; it is fixed
for the pilot. Swapping out of priority order is a discipline failure.

---

## Section 6 — Operational pre-registration check-list

Before pilot launch (Day 0), confirm:

  - [ ] LUXY baseline conversion rate confirmed; n_per_arm finalized
  - [ ] 2-arm or 2×2 factorial decided based on budget
  - [ ] Pixel installed on luxyride.com; conversion event firing
        validated against synthetic events
  - [ ] StackAdapt webhook wired; refund/complaint events flowing to
        OutcomeHandler (negative-outcome instrumentation, task #26)
  - [ ] Conformal calibration set bootstrapped from synthetic A/B sim
        (`build_conformal_lift_wrap`, ~30 subsamples)
  - [ ] Mechanism rotation commitments registered (task #22)
  - [ ] Pre-registered plan published externally (OSF / AsPredicted)
  - [ ] Third-party statistical reviewer signed off (task #32)
  - [ ] Failure-mode runbook (task #35) rehearsed Week 4 of flight

Signed: __________________________________
Reviewer: __________________________________
Date: __________________________________

---

## Section 7 — Amendments log

Every change post-pre-registration must be logged here. Amendments
do not retroactively change the locked plan — the original plan is
preserved; the amendment is added.

| Date | Section | Change | Reason | Approver |
|---|---|---|---|---|
| 2026-04-29 | initial draft | n/a | initial draft | Chris Nocera |

---

## Section 8 — References to Phase 0.1 substrate

Specific commits this analysis plan rests on:

  - `cf399d3` — chain-attestation modulation activates campaign-impact
    path. Mechanism scores reflect bilateral signal at decision time.
  - `bf69274` — L3 override (Foundation §4.1 in code). When cascade
    reaches L3, bilateral evidence is the base for mechanism selection.
  - `3a7109e` — per-atom contribution ingestion producer. Outcomes
    feed PerAtomContributionTracker.
  - `fec2c40` — A14 retirement-trigger Prometheus counter. Tracks
    pilot-pending coefficient exercises.
  - `105ee4a` — synthetic A/B simulation with planted treatment effect.
    Calibration source for conformal CI.
  - `362dd9f` — conformal lift wrap. Provides the headline 95% CI
    with finite-sample marginal coverage.
  - `9f5a36d` — pre-registered mechanism rotation event substrate.
    Mid-flight rotations registered + tracked.
  - `437d055` — construct-chain rendering. Per-recommendation
    inferential-chain artifact for partner-facing reporting.
  - `6ae506e` — mechanism-taxonomy runtime. matched_vs_mismatched
    diagonals power §3.2 secondary endpoint.
  - `968aaab` — per-decision online learning substrate. Cascade reads
    fresh LinkPosteriors at decision time (substrate; wiring is
    follow-up).
  - `dbf3532` — page attentional posture substrate. Categorical labels
    + Author/Pub/Section accumulator power §3.2's page-conditional
    analysis.
  - `d7fbb44` + `6f4f945` + `6fdb76d` — Loop B v0.1 (Dialogue Ledger,
    elicitation generators, Uncertainty Panel, mood probe). Captures
    Becca's tacit knowledge during the pilot for §4.2-related
    market-shift insight.

This analysis plan is the substrate-level commitment. The actual
analysis runs after the flight closes against the data accumulated
through the substrate.
