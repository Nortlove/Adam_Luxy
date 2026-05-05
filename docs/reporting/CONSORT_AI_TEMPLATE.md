# CONSORT-AI Reporting Template

**Document Status:** PRE-FORMATTED TEMPLATE (pre-pilot deliverable per directive §G.4)
**Reporting Standard:** CONSORT-AI extension per Liu, Cruz Rivera, Moher, Calvert, & Denniston (2020), *Nature Medicine* 26:1364–1374.
**Use:** Fill-in-as-data-accumulates. Each pilot/study produces one completed instance of this template, archived in the pilot audit trail and submitted with any peer-reviewed manuscript reporting the pilot.
**Companion:** `docs/reporting/SPIRIT_AI_TEMPLATE.md` (protocol pre-specification, paired with CONSORT-AI for results reporting).

---

## §1 Title and Abstract

| # | Item | Description | Pilot Entry |
|---|------|-------------|-------------|
| 1a | Title | Identification as a randomized trial of an AI intervention. | _<fill>_ |
| 1b | Abstract — AI extension | Structured summary including AI-intervention type, intended use, training/test data sources, and version of AI deployed. | _<fill>_ |

## §2 Introduction

| # | Item | Description | Pilot Entry |
|---|------|-------------|-------------|
| 2a | Background and rationale | Scientific background and rationale for the AI intervention; how it differs from the standard of care. | _<fill>_ |
| 2b | AI-extension specifics | Description of the AI intervention's intended use, target population, decision boundary, expected role in user workflow. | _<fill>_ |

## §3 Methods

### 3.1 Trial Design

| # | Item | Description | Pilot Entry |
|---|------|-------------|-------------|
| 3a | Trial design | Description (e.g., parallel, factorial, within-subject crossover) including allocation ratio. | _<fill>_ |
| 3b | Important changes to methods | Any important changes after trial commencement, with reasons. | _<fill>_ |

### 3.2 Participants

| # | Item | Description | Pilot Entry |
|---|------|-------------|-------------|
| 4a | Eligibility criteria | Eligibility criteria for participants AND for centers/data sources. | _<fill>_ |
| 4b | Settings and locations | Settings and locations where data were collected. | _<fill>_ |
| 4c | AI-extension — input handling | How input data quality was assessed at the time of AI deployment. Include handling of poor-quality inputs (e.g., images, text, sensor data) and the procedures for obtaining new input. | _<fill>_ |

### 3.3 Interventions

| # | Item | Description | Pilot Entry |
|---|------|-------------|-------------|
| 5a | Interventions | Detailed description of each group's intervention with sufficient detail for replication, including the AI intervention's hardware/software dependencies and version. | _<fill>_ |
| 5b | AI-extension — intended use | The intended clinical/operational use, decision boundary, and the role of human users in interpreting AI output. | _<fill>_ |
| 5c | AI-extension — version | The exact version (commit SHA, model checkpoint, training-data snapshot) of the AI deployed during the trial. | _<fill>_ |
| 5d | AI-extension — input + output | Examples of input data and corresponding AI output, including borderline and uncertain cases. | _<fill>_ |
| 5e | AI-extension — integration with workflow | How the AI was integrated into the existing decision pathway. | _<fill>_ |
| 5f | AI-extension — performance error handling | Procedures for handling AI performance errors and the threshold for human override. | _<fill>_ |

### 3.4 Outcomes

| # | Item | Description | Pilot Entry |
|---|------|-------------|-------------|
| 6a | Outcomes | Primary and secondary outcome measures, including how and when they were assessed. | _<fill>_ |
| 6b | Changes to outcomes | Any changes to trial outcomes after commencement, with reasons. | _<fill>_ |

### 3.5 Sample Size

| # | Item | Description | Pilot Entry |
|---|------|-------------|-------------|
| 7a | Sample-size determination | How sample size was determined; include any interim analyses + stopping rules per the always-valid sequential-test framework. | _<fill>_ |
| 7b | Stopping guidelines | When applicable, explanation of any interim analyses + stopping guidelines. | _<fill>_ |

### 3.6 Randomization

| # | Item | Description | Pilot Entry |
|---|------|-------------|-------------|
| 8a | Sequence generation | Method used to generate the random allocation sequence (e.g., ε-randomized first touch with ε=0.15). | _<fill>_ |
| 8b | Allocation concealment | Mechanism used to implement the random allocation sequence. | _<fill>_ |
| 9 | Implementation | Who generated the allocation sequence, who enrolled participants, who assigned to interventions. | _<fill>_ |
| 10 | Blinding | After assignment, who was blinded (participants, care providers, outcome assessors, analysts). | _<fill>_ |

### 3.7 Statistical Methods

| # | Item | Description | Pilot Entry |
|---|------|-------------|-------------|
| 12a | Statistical methods — primary | Methods used for primary and secondary outcomes, including IPSW correction and any per-user hierarchical-Bayesian pooling. | _<fill>_ |
| 12b | Methods for additional analyses | Subgroup analyses, adjusted analyses, sensitivity analyses. | _<fill>_ |

## §4 Results

### 4.1 Participant Flow

| # | Item | Description | Pilot Entry |
|---|------|-------------|-------------|
| 13a | Participant flow diagram | CONSORT-style flow diagram showing assignment, follow-up, and analysis. | _<fill>_ |
| 13b | Losses and exclusions | Losses and exclusions after randomization, with reasons. | _<fill>_ |

### 4.2 Recruitment

| # | Item | Description | Pilot Entry |
|---|------|-------------|-------------|
| 14a | Recruitment dates | Dates of recruitment and follow-up. | _<fill>_ |
| 14b | Why trial ended | Why the trial ended or was stopped. | _<fill>_ |

### 4.3 Baseline Data

| # | Item | Description | Pilot Entry |
|---|------|-------------|-------------|
| 15 | Baseline characteristics | Table showing baseline demographic and clinical characteristics for each group. | _<fill>_ |

### 4.4 Numbers Analyzed

| # | Item | Description | Pilot Entry |
|---|------|-------------|-------------|
| 16 | Numbers analyzed | Number of participants in each group included in each analysis; whether the analysis was by original assigned groups. | _<fill>_ |

### 4.5 Outcomes and Estimation

| # | Item | Description | Pilot Entry |
|---|------|-------------|-------------|
| 17a | Outcomes — primary + secondary | Results for each primary + secondary outcome with effect size and precision (e.g., 95% CI). | _<fill>_ |
| 17b | Binary outcomes | Both absolute and relative effect sizes recommended. | _<fill>_ |
| 18 | Ancillary analyses | Other analyses performed; distinguish pre-specified from exploratory. | _<fill>_ |

### 4.6 Harms

| # | Item | Description | Pilot Entry |
|---|------|-------------|-------------|
| 19 | Harms | All important harms or unintended effects in each group; reference the pharmacovigilance dashboard EBGM/PRR/IC outputs. | _<fill>_ |
| 19a | AI-extension — harms | Description of any errors in AI predictions and the resulting impact, including downstream actions and harm mitigation. | _<fill>_ |

## §5 Discussion

| # | Item | Description | Pilot Entry |
|---|------|-------------|-------------|
| 20 | Limitations | Trial limitations addressing sources of potential bias, imprecision, multiplicity. | _<fill>_ |
| 21 | Generalizability | Generalizability (external validity, applicability) of the trial findings. | _<fill>_ |
| 22 | Interpretation | Interpretation consistent with results, balancing benefits and harms, considering other relevant evidence. | _<fill>_ |

## §6 Other Information

| # | Item | Description | Pilot Entry |
|---|------|-------------|-------------|
| 23 | Registration | Registration number and registry name (OSF pre-registration ID per directive §G.2). | _<fill>_ |
| 24 | Protocol | Where the full trial protocol can be accessed (cite SPIRIT-AI document). | _<fill>_ |
| 25 | Funding | Sources of funding and other support; role of funders. | _<fill>_ |
| 26 | AI-extension — code + data | Disclosure of AI source code, training data, and model weights as applicable; archival location and access policy. | _<fill>_ |

---

## Notes on Use

- Items 1a–22 are core CONSORT 2010 items; items prefixed "AI-extension" are CONSORT-AI additions.
- Use a separate row entry per group when groups differ on the item.
- For multi-cohort or factorial pilots, complete one CONSORT-AI per primary contrast and append a master cross-reference table.
- Reference the OSF pre-registration ID at item 23 to enforce alignment between pre-specified and reported outcomes; any deviation must be flagged at item 6b ("Changes to outcomes").

## Reference

Liu X, Cruz Rivera S, Moher D, Calvert MJ, Denniston AK. Reporting guidelines for clinical trial reports for interventions involving artificial intelligence: the CONSORT-AI extension. *Nature Medicine*. 2020;26:1364–1374.
