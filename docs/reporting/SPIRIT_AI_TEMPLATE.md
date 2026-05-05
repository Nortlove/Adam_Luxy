# SPIRIT-AI Reporting Template

**Document Status:** PRE-FORMATTED TEMPLATE (pre-pilot deliverable per directive §G.4)
**Reporting Standard:** SPIRIT-AI extension per Cruz Rivera, Liu, Chan, Denniston, & Calvert (2020), *Nature Medicine* 26:1351–1363.
**Use:** Pre-specification of trial protocol. Filled BEFORE pilot trial commences (Gate G3) and registered with OSF per directive §G.2. Companion to `docs/reporting/CONSORT_AI_TEMPLATE.md` (results reporting filled post-trial).

---

## §1 Administrative Information

| # | Item | Description | Protocol Entry |
|---|------|-------------|----------------|
| 1 | Title | Descriptive title identifying the study design, population, interventions, and trial acronym. | _<fill>_ |
| 2a | Trial registration | Registration number + name of registry (OSF Pre-Registration ID). | _<fill>_ |
| 2b | Trial registration data | Registered against pre-specified data items. | _<fill>_ |
| 3 | Protocol version | Date and version identifier. | _<fill>_ |
| 4 | Funding | Sources and types of financial, material, and other support. | _<fill>_ |
| 5a | Roles and responsibilities — contributorship | Names, affiliations, roles. | _<fill>_ |
| 5b | Sponsor + funders — contact info | Contact information. | _<fill>_ |
| 5c | Sponsor + funders — role | Role in study design, collection, management, analysis, interpretation, manuscript preparation. | _<fill>_ |
| 5d | Composition + reporting structure | Composition, roles, responsibilities of coordinating center, steering committee, endpoint adjudication committee, data management team, and other relevant individuals — including the DMC per `docs/governance/DMC_CHARTER_DRAFT.md`. | _<fill>_ |

## §2 Introduction

| # | Item | Description | Protocol Entry |
|---|------|-------------|----------------|
| 6a | Background and rationale | Description of research question, justification for undertaking the trial, summary of relevant studies. | _<fill>_ |
| 6b | AI-extension — intended use | Detailed description of the intended use of the AI intervention: target population, decision boundary, role in workflow. | _<fill>_ |
| 6c | AI-extension — comparator | Choice of comparators including standard of care, with rationale. | _<fill>_ |
| 7 | Objectives | Specific objectives or hypotheses. | _<fill>_ |
| 8 | Trial design | Description (e.g., parallel, factorial, within-subject crossover) including allocation ratio + framework (e.g., superiority, equivalence, non-inferiority, exploratory). | _<fill>_ |

## §3 Methods — Participants, Interventions, Outcomes

### 3.1 Study Setting

| # | Item | Description | Protocol Entry |
|---|------|-------------|----------------|
| 9 | Study setting | Setting (community, primary care, specialty, outpatient, online platform, etc.) and locations. | _<fill>_ |

### 3.2 Eligibility Criteria

| # | Item | Description | Protocol Entry |
|---|------|-------------|----------------|
| 10 | Eligibility criteria | Inclusion/exclusion criteria for participants. If applicable, eligibility criteria for centers + individuals performing intervention. | _<fill>_ |
| 10a | AI-extension — input handling | Specify the input data + how its quality will be assessed at the point of AI deployment, including handling of poor-quality input. | _<fill>_ |

### 3.3 Interventions

| # | Item | Description | Protocol Entry |
|---|------|-------------|----------------|
| 11a | Intervention | Detailed description of intervention with sufficient detail to allow replication. | _<fill>_ |
| 11b | AI-extension — version | The exact version of the AI intervention used (commit SHA, model checkpoint, training-data snapshot). | _<fill>_ |
| 11c | AI-extension — input + output | Description of inputs and outputs of the AI intervention, including how the output will be communicated/visualised to users. | _<fill>_ |
| 11d | AI-extension — integration with workflow | How the AI will be integrated into the existing care/decision pathway. | _<fill>_ |
| 11e | AI-extension — performance error handling | Procedures for addressing AI performance errors, including the human override pathway. | _<fill>_ |
| 11f | Modifications | Criteria for discontinuing or modifying allocated interventions for an individual. | _<fill>_ |
| 11g | Adherence | Strategies to improve adherence to intervention protocols. | _<fill>_ |
| 11h | Concomitant care | Relevant concomitant care + interventions permitted/prohibited. | _<fill>_ |

### 3.4 Outcomes

| # | Item | Description | Protocol Entry |
|---|------|-------------|----------------|
| 12 | Outcomes | Primary, secondary outcome measures, including specific measurement variable, analysis metric, method of aggregation, and time point of measurement. | _<fill>_ |

### 3.5 Participant Timeline

| # | Item | Description | Protocol Entry |
|---|------|-------------|----------------|
| 13 | Participant timeline | Time schedule of enrollment, interventions, assessments, visits. SPIRIT-style figure recommended. | _<fill>_ |

### 3.6 Sample Size

| # | Item | Description | Protocol Entry |
|---|------|-------------|----------------|
| 14 | Sample size | Estimated number of participants needed to achieve study objectives + how it was determined, including assumptions supporting any sample-size calculation. Reference always-valid sequential-test framework (Howard-Ramdas confidence sequences; Johari-Pekelis-Walsh mixture SPRT). | _<fill>_ |

### 3.7 Recruitment

| # | Item | Description | Protocol Entry |
|---|------|-------------|----------------|
| 15 | Recruitment | Strategies for achieving adequate participant enrollment. | _<fill>_ |

## §4 Methods — Assignment of Interventions

### 4.1 Allocation

| # | Item | Description | Protocol Entry |
|---|------|-------------|----------------|
| 16a | Sequence generation | Method of generating the allocation sequence (e.g., ε-randomized first touch with ε=0.15 per directive Slice S9.3). | _<fill>_ |
| 16b | Allocation concealment mechanism | Mechanism (e.g., central randomization). | _<fill>_ |
| 16c | Implementation | Who will generate, enroll, and assign. | _<fill>_ |

### 4.2 Blinding

| # | Item | Description | Protocol Entry |
|---|------|-------------|----------------|
| 17a | Blinding (masking) | Who will be blinded (participants, care providers, outcome assessors, data analysts) and how. Reference DMC blinding regime per `docs/governance/DMC_CHARTER_DRAFT.md` §3. | _<fill>_ |
| 17b | Procedures for unblinding | If applicable, procedures for revealing a participant's allocated intervention during the trial. | _<fill>_ |

## §5 Methods — Data Collection, Management, Analysis

### 5.1 Data Collection

| # | Item | Description | Protocol Entry |
|---|------|-------------|----------------|
| 18a | Data collection methods | Plans for assessment + collection of outcome, baseline, and other trial data. | _<fill>_ |
| 18b | Promote data quality | Plans to promote participant retention and complete follow-up. | _<fill>_ |

### 5.2 Data Management

| # | Item | Description | Protocol Entry |
|---|------|-------------|----------------|
| 19 | Data management | Plans for data entry, coding, security, storage. Reference Iceberg/Parquet persistence per S4.2 + Postgres rollups per S4.4. | _<fill>_ |

### 5.3 Statistical Methods

| # | Item | Description | Protocol Entry |
|---|------|-------------|----------------|
| 20a | Statistical methods — primary | Methods for primary + secondary outcomes. Include IPSW correction at every reported metric per directive §S4.6 + §S7.3. | _<fill>_ |
| 20b | Methods for additional analyses | Subgroup analyses, adjusted analyses, sensitivity analyses. Pre-specify component-ablation factorial: cell-classifier × journey-state × per-user-posterior. | _<fill>_ |
| 20c | Methods for missing data | Methods to handle missing data + sensitivity analyses. | _<fill>_ |

## §6 Methods — Monitoring

### 6.1 Data Monitoring

| # | Item | Description | Protocol Entry |
|---|------|-------------|----------------|
| 21a | Data monitoring | Composition of DMC; summary of its role + reporting structure (reference `docs/governance/DMC_CHARTER_DRAFT.md`). | _<fill>_ |
| 21b | Interim analyses | Description of any interim analyses + stopping guidelines, including who will have access to interim results + decision-making process. Always-valid sequential framework per §G.1 §4. | _<fill>_ |

### 6.2 Harms

| # | Item | Description | Protocol Entry |
|---|------|-------------|----------------|
| 22 | Harms | Plans for collecting, assessing, reporting, and managing solicited + spontaneously-reported adverse events + other unintended effects of trial interventions or trial conduct. Reference pharmacovigilance schema per `adam/pharmacovigilance/schema.py`. | _<fill>_ |

### 6.3 Auditing

| # | Item | Description | Protocol Entry |
|---|------|-------------|----------------|
| 23 | Auditing | Frequency + procedures for auditing trial conduct, if any, and whether the auditor is independent of investigators + sponsor. | _<fill>_ |

## §7 Ethics + Dissemination

### 7.1 Research Ethics + Approval

| # | Item | Description | Protocol Entry |
|---|------|-------------|----------------|
| 24 | Research ethics approval | Plans for seeking research ethics committee/institutional review board approval. | _<fill>_ |
| 25 | Protocol amendments | Plans for communicating important protocol modifications to relevant parties. | _<fill>_ |

### 7.2 Consent or Assent

| # | Item | Description | Protocol Entry |
|---|------|-------------|----------------|
| 26a | Consent | Who will obtain informed consent + how. | _<fill>_ |
| 26b | Ancillary studies | Additional consent provisions for collection + use of participant data + biological specimens in ancillary studies. | _<fill>_ |

### 7.3 Confidentiality

| # | Item | Description | Protocol Entry |
|---|------|-------------|----------------|
| 27 | Confidentiality | How personal information about potential + enrolled participants will be collected, shared, and maintained to protect confidentiality before, during, after the trial. | _<fill>_ |

### 7.4 Declaration of Interests

| # | Item | Description | Protocol Entry |
|---|------|-------------|----------------|
| 28 | Declaration of interests | Financial + other competing interests for principal investigators for the overall trial + each study site. | _<fill>_ |

### 7.5 Access to Data

| # | Item | Description | Protocol Entry |
|---|------|-------------|----------------|
| 29 | Access to data | Statement of who will have access to the final trial dataset; disclose contractual agreements that limit such access for investigators. | _<fill>_ |

### 7.6 Ancillary + Post-Trial Care

| # | Item | Description | Protocol Entry |
|---|------|-------------|----------------|
| 30 | Ancillary + post-trial care | Provisions, if any, for ancillary + post-trial care + compensation for those who suffer harm from trial participation. | _<fill>_ |

### 7.7 Dissemination Policy

| # | Item | Description | Protocol Entry |
|---|------|-------------|----------------|
| 31a | Dissemination plan | Plans for investigators + sponsor to communicate trial results to participants, professionals, public, and other relevant groups. | _<fill>_ |
| 31b | Authorship eligibility guidelines | Authorship guidelines + any intended use of professional writers. | _<fill>_ |
| 31c | AI-extension — code + data | Plans for granting public access to the AI source code, training data, model weights, and protocol — explicit access policy. | _<fill>_ |
| 31d | Reproducible research | Plans for reproducibility (e.g., checkpoint archival, training-data snapshot policy, deterministic-seed protocol). | _<fill>_ |

## §8 Appendices

### 8.1 Informed Consent Materials
_<placeholder for full consent forms used>_

### 8.2 Biological Specimens
_<placeholder for any biological-specimen plans, if applicable; AI-only studies typically N/A>_

---

## Notes on Use

- Items 1–32 are core SPIRIT 2013 items; items prefixed "AI-extension" are SPIRIT-AI additions.
- Complete BEFORE the trial commences and register with OSF per directive §G.2.
- Where items are not applicable (e.g., biological specimens for an AI-only ad-platform pilot), record "Not applicable" with brief rationale rather than leaving blank.
- The companion CONSORT-AI document (`docs/reporting/CONSORT_AI_TEMPLATE.md`) is filled at the END of the trial. The two documents together comprise the canonical pre-specification + results-reporting bundle.

## Reference

Cruz Rivera S, Liu X, Chan AW, Denniston AK, Calvert MJ. Guidelines for clinical trial protocols for interventions involving artificial intelligence: the SPIRIT-AI extension. *Nature Medicine*. 2020;26:1351–1363.
