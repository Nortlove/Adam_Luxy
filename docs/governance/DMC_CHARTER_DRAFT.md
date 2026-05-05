# Data Monitoring Committee (DMC) Charter — DRAFT

**Document Status:** DRAFT (pre-pilot deliverable per directive §G.1)
**Effective Upon:** Charter ratification by INFORMATIV Group CTO + DMC member sign-off (signature page appended at ratification)
**Activates:** At Gate G3 (LUXY ad-serving begins) when blinding regime takes effect
**Authoring Directive:** `docs/CLAUDE CODE DIRECTIVE v3.1.md` §G.1
**Owner:** Chris Nocera, CTO, INFORMATIV Group

---

## §1 Authority

The Data Monitoring Committee (DMC) is the standing safety-and-efficacy adjudication body for INFORMATIV pilots and platform deployments. The DMC has authority to recommend pause, modification, or termination of any cell × cohort arm based on safety, futility, or efficacy signals observed in the unblinded data stream.

**Decision authority remains with the INFORMATIV CTO.** DMC recommendations are advisory but documented; CTO acceptance, rejection, or modification of any DMC recommendation is recorded in writing, with reasoning, in the DMC meeting minutes and appended to the corresponding pilot's audit trail.

The DMC's scope of authority extends to:

- Recommending pause of any cell × cohort × creative × posture combination on detection of an adverse-outcome signal exceeding the harm boundary (§4).
- Recommending termination of an arm or trial on futility-boundary crossing (§4).
- Recommending early stopping for efficacy on always-valid sequential test boundary crossing (§4).
- Recommending protocol modifications (e.g., ε-randomization rate adjustment, washout-interval extension, mediator-conditioning addition) when post-hoc analyses surface methodological concerns.
- Requesting any unblinded analysis of any subgroup at any time, with written justification.

The DMC does **not** have authority to modify the pre-registered analysis plan unilaterally, override the OSF pre-registration, modify the pharmacovigilance signal thresholds (§4), or override the always-valid sequential testing framework. Those modifications require CTO + OSF amendment + DMC concurrence.

## §2 Composition and Voting Rules

The DMC consists of **three (3) voting members**:

1. **Independent Statistical Methodologist** — credentialed in causal-inference methods (DML, AIPW, conformal prediction, sequential analysis) and Bayesian hierarchical modeling. Selected from outside INFORMATIV's contractor pool. Cannot have current or past financial relationship with INFORMATIV exceeding nominal honoraria.
2. **Independent Advertising-Domain Expert** — practitioner with at least 10 years of programmatic-advertising experience, including direct exposure to bid-time decision systems and conversion-attribution methodology. Cannot be current or recent employee of any DSP, SSP, exchange, or competing platform.
3. **INFORMATIV-Internal but Firewalled Member** — non-CTO INFORMATIV employee with direct knowledge of platform architecture, formally firewalled from day-to-day pilot operations and excluded from the unblinded-data review group on the build side. **Chris Nocera does not sit on the DMC** — the CTO role is the recipient of DMC recommendations, not an adjudicating voice within them.

**Voting:** majority rule. A two-of-three vote constitutes a DMC recommendation. Dissent is recorded with rationale.

**Quorum:** all three voting members must be present (in-person or videoconference) for a binding recommendation. Asynchronous review of routine reports may be conducted by all three independently with written sign-off.

**Term length:** 24 months, staggered (one member rotates per ~8 months) to preserve institutional memory while limiting capture.

**Replacement on conflict:** any member who develops a conflict of interest mid-term per §5 must recuse from the affected adjudication and may be replaced by a CTO-nominated alternate for that adjudication only.

## §3 Blinding Discipline

**The DMC reviews unblinded data; the build team does not.**

Blinding takes effect at **criterion (ii) gate closure** (Gate G1) and persists through the pilot trial period to Gate G7 (v3 Phase 1 close). During the blinded period:

- The build team (Claude Code execution surface, INFORMATIV engineers) sees only outcome-anonymized aggregates, with cell × cohort × creative arm labels replaced by opaque arm identifiers.
- The DMC sees fully unblinded data, including arm-to-treatment mapping, per-cell conversion rates, IPSW-corrected lift estimates, and pharmacovigilance signal scores.
- Any cross-team communication that would inadvertently unblind the build team — for example, a DMC member naming a specific creative variant in correspondence visible to the build team — constitutes a blinding-protocol breach and must be flagged in the next meeting.

**Exception — emergency unblinding:** the CTO may request emergency unblinding of any specific cell on safety grounds. Any such unblinding is logged with timestamp, requesting party, justification, and scope (which cells were unblinded, to whom). Emergency unblinding is reported to the DMC at the next meeting and recorded in the audit trail.

**De-blinding cadence:** scheduled de-blinding events occur at:

- Gate G4 (4-week pilot data accumulated; ADWIN-baseline-stable) — partial de-blinding for cell × cohort interaction analysis.
- Gate G5 (8-week pilot data; cross-tenant infrastructure stable) — partial de-blinding for sequential-test interim analysis.
- Gate G7 (v3 Phase 1 complete) — full de-blinding for OSF-required final analysis.

## §4 Stopping Rules

### 4.1 Harm Boundary

The harm boundary is defined per-cell using the pharmacovigilance schema (§G.3):

- **EBGM lower 5th percentile (EB05) > 2** for any (creative × cohort × posture × cell) combination on a negative-outcome metric (per directive Slice S5.4 within-subject negative-outcome adapter), per the Almenoff / EFSPI convention for signal localization in pharmacovigilance disproportionality analysis.
- **Tree-based scan-statistic significance** at α=0.001 across the (creative × cohort × posture × cell) hierarchy on negative-outcome rate.

Either condition triggers a DMC pause-arm recommendation. The CTO may either accept the pause, reject with documented justification, or request additional analysis before deciding.

### 4.2 Futility Boundary

The futility boundary uses always-valid sequential testing per the primary endpoint (IPSW-corrected weighted conversion rate, fluid retargeting v0/v1/v2 vs naive frequency-cap baseline):

- **Howard-Ramdas confidence sequence** lower bound on lift falls below pre-registered minimum-detectable-effect (MDE) and stays below for 4 consecutive interim analyses.

Triggers a DMC futility-stop recommendation for the affected arm.

### 4.3 Efficacy Boundary

- **Howard-Ramdas confidence sequence** lower bound on lift exceeds pre-registered MDE and stays above for 4 consecutive interim analyses, AND
- **Johari-Pekelis-Walsh always-valid mixture SPRT** crosses the early-stopping efficacy threshold (α-spent boundary).

Both conditions must hold concurrently. Triggers a DMC efficacy-stop recommendation. The CTO may proceed with full ramp ahead of the original schedule.

### 4.4 Component-Ablation Stopping

The pre-registered factorial (cell-classifier on/off × journey-state on/off × per-user posterior on/off) carries its own stopping rules per cell-arm combination using the same Howard-Ramdas + Johari-Pekelis-Walsh framework. Component-level early stopping does not stop the overall trial unless the integrated arm itself triggers §4.2 or §4.3.

## §5 Conflict-of-Interest Policy

Each DMC member discloses, at appointment and annually thereafter:

- Direct financial interests (equity, paid advisory roles, consulting contracts) in any advertiser, DSP, SSP, exchange, or competing AI-decision platform exceeding USD $5,000 per year or 0.5% equity stake.
- Indirect financial interests via spouse, dependent children, or controlled entities meeting the same thresholds.
- Active research collaborations or grant relationships with INFORMATIV competitors or potential acquirers.
- Pending or anticipated employment offers from any party meeting the above categories.
- Service on advisory boards or technical panels of any of the above.

Disclosures are filed with the INFORMATIV Group CTO and reviewed before each DMC meeting. Members must recuse from any specific adjudication where a disclosed interest could be reasonably perceived as influencing judgment.

Disclosures and recusals are summarized (without exact dollar figures) in the annual DMC report appended to the pilot audit trail.

**Cooling-off period:** members must wait 12 months after DMC tenure ends before accepting any paid role with INFORMATIV competitors named in their disclosure file.

## §6 Meeting Cadence

- **Pre-pilot (G0–G3):** quarterly review of charter compliance, pre-registration alignment, and pharmacovigilance schema readiness. Meetings 60–90 minutes; agenda circulated 7 days in advance.
- **Pilot serve weeks 1–8 (G3–G5):** monthly. First meeting within 7 days of Gate G3. Reviews IPSW-corrected conversion rates, ADWIN drift signals, pharmacovigilance disproportionality metrics, sequential-test interim analyses.
- **Phase 2 ramp (G7–G8):** weekly during the first 4 weeks of ramp; biweekly thereafter through Phase 2 close.
- **Ad-hoc:** any DMC member may request an ad-hoc meeting on a 48-hour notice if they observe a signal warranting expedited review. The CTO may also request ad-hoc meetings.

**Minutes:** every meeting produces minutes recording: attendees, agenda items, recommendations issued, vote tallies, dissents with rationale, action items with owners and deadlines, and a summary of unblinded data reviewed (cell × cohort granularity recorded; per-record raw data not transcribed). Minutes are signed by all attendees and filed in the pilot audit trail.

**Asynchronous review:** routine pharmacovigilance reports (PRR / ROR / IC / EBGM-MGPS / scan-statistic outputs per the §G.3 schema) are circulated weekly to all members for asynchronous review and sign-off. Any member may escalate any item to a synchronous meeting.

---

## Appendix A — Signature Page

To be appended at charter ratification with member names, affiliations, dates of appointment, term-end dates, and signatures. Charter version under signature is the version of record for that DMC tenure.

## Appendix B — References

- DuMouchel, W. (1999). "Bayesian Data Mining in Large Frequency Tables, with an Application to the FDA Spontaneous Reporting System." *American Statistician* 53:170–190.
- Howard, S. R., Ramdas, A., McAuliffe, J., & Sekhon, J. S. (2021). "Time-uniform, nonparametric, nonasymptotic confidence sequences." *Annals of Statistics* 49(2):1055–1080.
- Johari, R., Pekelis, L., & Walsh, D. J. (2017). "Always Valid Inference: Bringing Sequential Analysis to A/B Testing." Stanford OIT working paper.
- Liu, X., Cruz Rivera, S., Moher, D., Calvert, M. J., & Denniston, A. K. (2020). "Reporting guidelines for clinical trial reports for interventions involving artificial intelligence: the CONSORT-AI extension." *Nature Medicine* 26:1364–1374.
- Cruz Rivera, S., Liu, X., Chan, A. W., Denniston, A. K., & Calvert, M. J. (2020). "Guidelines for clinical trial protocols for interventions involving artificial intelligence: the SPIRIT-AI extension." *Nature Medicine* 26:1351–1363.
