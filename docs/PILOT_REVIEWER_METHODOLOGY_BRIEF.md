# LUXY Pilot — Methodology Brief for Independent Statistical Review

**Status**: send to reviewer ≥ 1 week before pilot launch
**Engagement**: 2-hour billable engagement
**Reviewer**: applied statistician (NOT psychometrician — that's post-hoc)

---

## Reviewer's task

Confirm the **pre-registered analysis plan**
(`PILOT_PRE_REGISTERED_ANALYSIS_PLAN.md`) is sound. Specifically:

1. Is the **primary endpoint** correctly specified for the hypothesis?
2. Is the **power calculation** valid given the assumed baseline rate
   and the detectable lift δ?
3. Is the **control arm** spec sufficient to support the inferential
   claim?
4. Are the **secondary endpoints** statistically appropriate for
   the small-N regime they target?
5. Are the **failure-mode protocols** sufficient to maintain
   pre-registered discipline if mid-flight events occur?
6. Is anything missing that a hostile due-diligence reader would
   challenge?

Reviewer signs off on the plan before pilot launch. The signed-off
plan is a credibility artifact for the deck.

---

## Background — what the pilot tests

ADAM is a programmatic-advertising platform that targets ads to
audiences using **bilateral psychological alignment** rather than
**behavioral lookalike**. The hypothesis is that bilateral targeting
produces a higher conversion rate on the same impression pool than
lookalike-style audience selection.

The pilot is a 12-week corporate-travel campaign (LUXY Ride, friendly
client) running on StackAdapt. Budget ~$30K/week. Expected total
conversions across the flight: 200–400.

**Treatment arm**: ADAM's bilateral cascade selects audience archetypes
based on ~1.9M GranularType nodes + ~47M alignment edges in the
underlying knowledge graph. The cascade overrides archetype-prior
scoring with bilateral edge evidence when L3 evidence is available
(Phase 0.1 commit `bf69274`).

**Control arm**: StackAdapt's standard lookalike audience for the
same campaign, run concurrently, same creative, same dayparting.

---

## Primary endpoint

**Two-proportion z-test on conversion-rate difference**, one-sided
(treatment > control).

H₀: p_T − p_C = 0
H₁: p_T − p_C > 0

α = 0.05, power = 0.80.

### Required N

(*Placeholder values — finalize once LUXY's actual baseline is
confirmed*)

```
n_per_arm = 16 × p × (1 − p) / δ²
```

For baseline conversion rate p_C = 0.020 (assumed) and target
detectable relative lift = 30% (so absolute δ = 0.006):

```
n_per_arm = 16 × 0.020 × 0.980 / (0.006)² ≈ 8,711
```

So ≥ ~17,400 impressions across both arms for the primary test to
reach the target detectable lift at the assumed p_C.

If actual p_C is 0.005, n_per_arm ≈ 35,400 (≥ ~70,800 total).

### Reviewer questions

1. Is the one-sided test appropriate given the pre-registered
   directional hypothesis?
2. Is the variance approximation correct for small p_C?
3. Should we apply a continuity correction at small n?
4. Is the assumed independence of impressions defensible for
   the LUXY pilot? (Cluster-robust SE if not — see §3.3 of the
   plan; user-clustered).

---

## Conformal coverage on lift estimate

In addition to the parametric z-test, the headline number reports a
**conformal-coverage 95% CI on relative lift** via
`adam.intelligence.causal_conformal.ConformalLiftWrap`
(commit `362dd9f`).

The conformal CI has finite-sample marginal coverage at any N
(distribution-free under exchangeability). The parametric delta-
method CI is known to under-cover at moderate N — the conformal
wrap replaces it.

**Calibration set**: bootstrapped pre-pilot from the
SyntheticABSimulator (commit `105ee4a`). Each subsample is N decisions
drawn from the simulator at the planted lift; observed lift becomes
a calibration pair (planted, observed). 30+ subsamples produces a
calibration set above the min_calibration_size threshold (20).

Calibration is exchangeable by construction (independent seeds, same
DGP). Production replaces synthetic calibration with holdout-cell
realizations as outcomes accumulate during pilot.

### Reviewer questions

1. Is split-conformal sufficient, or should we use jackknife+ /
   full-conformal for sample efficiency? (Vovk-Gammerman-Shafer 2005;
   Lei et al. 2018 JASA.)
2. Is the synthetic calibration set a defensible PRIOR for the
   pilot's actual exchangeability? Pilot data should validate this
   empirically.
3. Should we add Mondrian / locally-adaptive conformal for
   per-archetype-cell intervals? (Romano et al. 2019 CQR.)

---

## Secondary endpoints

Designed to win at low N. Powered by signals denser than conversion.

### S1 — Engagement-quality differential

**Two-sample t-test on mean processing-depth weight**, computed per
`adam/retargeting/engines/processing_depth.py`. Sample size =
**impressions** (every served impression contributes), not conversions
— vastly more power than the primary endpoint.

Powered to detect a 5% difference in mean depth at ~5,000 impressions
per arm.

### S2 — Page-context-conditional CTR

**Foundation §2 attention-inversion test**: matched-vs-mismatched
diagonal cells from `mechanism_taxonomy_runtime.matched_vs_mismatched_
diagonals()`. Two-proportion test on CTR difference.

Powered by CTR signal (much denser than conversion signal).

### S3 — 30-day return rate

**Two-proportion z-test on cohorted return-visit rate** at the 30-day
horizon, using `multi_horizon_adjudication.py` (commit `b07cc5e`).

Catches the failure mode where treatment wins on immediate CPA but
loses on long-horizon brand equity (HMT §9.5; Foundation §7 rule 11).

### S4 — Per-archetype lift heterogeneity

Reported as a HETEROGENEITY result, not per-archetype p-values
(would multiply-test). Interpretive claim: bilateral lift varies
across archetypes consistent with per-archetype review-corpus
signal density.

### Reviewer questions

1. Are the secondary endpoints sufficiently independent of the
   primary that they don't constitute multiple testing requiring
   adjustment?
2. The heterogeneity result (S4) — what's the right reporting form
   if not per-archetype p-values? (Forest plot? Standardized lift
   per archetype with combined I²?)

---

## Control arm caveat

The 2-arm control (bilateral targeting vs lookalike on same creative)
cleanly tests audience-selection difference but holds creative
constant — so the pilot's conclusion is bounded by the creative used.
A 2×2 factorial (audience × creative) would cleanly separate, but
costs 4× impressions.

**Decision criterion**: 2×2 factorial only if LUXY's budget supports
≥ 4 × n_per_arm impressions. Otherwise 2-arm with the bounded claim.

### Reviewer questions

1. If we go 2-arm: is the bounded claim defensibly worded?
2. If we go 2×2: is the factorial design sound, or should we run
   the two confounded effects (audience × creative source) as
   pre-registered comparisons rather than a single ANOVA?

---

## Failure-mode protocols

The pre-registered analysis plan §4 + the failure-mode runbook
(`PILOT_FAILURE_MODE_RUNBOOK.md`) specify pre-decided responses for
seven failure modes:

1. Webhook silence
2. Audience segment rejection
3. Creative pulled
4. CTR drop Day 3
5. StackAdapt inventory change
6. Market shift detected
7. A14 calibration-pending coefficient anomaly

Each has a decision tree with escalation times specified IN ADVANCE,
plus a "transparent change" log section in the analysis plan for any
deviation from the original commitment.

### Reviewer questions

1. Are the rehearsal injection times (Week 4 of flight, ~30 min
   per failure mode) sufficient?
2. Is the "run analysis with AND without post-shift impressions"
   protocol (used for #5 + #6) statistically sound?
3. Is the discordance test in `multi_horizon_adjudication.adjudicate`
   correctly specified for the Foundation §7 rule 11 failure mode?

---

## Data flow + key commits

For reviewer reference, the load-bearing Phase 0.1 commits this
analysis plan rests on:

- **`bf69274`** — L3 override (cascade uses bilateral evidence as
  base when reached, not a 0.6 blend partner)
- **`362dd9f`** — Conformal lift wrap (M2 sibling layer with valid
  finite-sample coverage)
- **`105ee4a`** — Synthetic A/B simulation (calibration source for
  conformal; integration test substrate)
- **`6ae506e`** — Mechanism-taxonomy runtime (Foundation §2 matched/
  mismatched diagonal accumulator)
- **`b07cc5e`** — Multi-horizon adjudication (7/30/60-day cohort
  tracking + discordance detection)
- **`dd00435`** — Agency-facing dashboard aggregator (JSON payload
  contract; consumes all of the above)
- **`e5e6d95`** — Negative-outcome adapter substrate (refund/complaint/
  churn → OutcomeHandler routing)

Tests across the surface: 384+ passing as of session close.

---

## Reviewer engagement scope

**2 hours**, billable.

Deliverable: signed memo confirming the pre-registered plan is
sound, OR identifying specific items to amend before pilot launch.

If amendments are needed:
- Power calc adjustment for actual p_C → re-derive n_per_arm
- Test-correction for multi-comparison (if reviewer flags it as needed)
- Conformal variant change (split → jackknife+ → CQR)
- Failure-mode protocol additions

Chris drives the response to amendments and the re-circulation if
needed.

---

## Practical questions for reviewer

1. **Time to read the full pre-registered plan**: ~30 min
2. **Time to read this brief + key commits' diffs**: ~15-30 min
3. **Time to answer the questions above**: ~60 min
4. **Time to draft the signed memo**: ~30 min

Total: 2-2.5 hours billable.

The brief intentionally hides nothing. The pre-registered plan is
the primary deliverable; this brief is the orientation.

---

## Contact

- **Chris Nocera** — technical lead, drives amendments
- **Becca** — agency-of-record liaison, drives operational integration
- **LUXY** — friendly client, sees the signed-off plan as a
  credibility artifact

---

## Appendix — Foundation references for the platform's claims

The platform's claims rest on a Bargh-lineage cognitive-science
foundation. Reviewer's job is on the STATISTICAL plan, not the
cognitive theory — but for context:

- John Bargh — automaticity / priming / auto-motive model (Yale,
  Chris's primary doctoral advisor)
- Steven Pinker — dual-mechanism theory of language (Harvard, Chris's
  other doctoral advisor)
- Robert Cialdini — influence / persuasion principles
- Foundation document: `ADAM_THEORETICAL_FOUNDATION.md`

The pilot tests an empirically defensible claim — "matching mechanism
to archetype's regulatory focus on aligned page contexts produces
higher conversion than lookalike-style audience selection" — and
reports the result with rigorous statistical machinery. The reviewer
focuses on the rigor.
